import os
import sys
import time
import math
import numpy as np
import pandas as pd
from hyperliquid.info import Info
from hyperliquid.utils import constants

sym_a = sys.argv[1] if len(sys.argv) > 1 else "xyz:CL"
sym_b = sys.argv[2] if len(sys.argv) > 2 else "xyz:BRENTOIL"
target_network = sys.argv[3] if len(sys.argv) > 3 else "mainnet"

api_url = constants.MAINNET_API_URL if target_network.lower() == "mainnet" else constants.TESTNET_API_URL
info = Info(api_url, skip_ws=True)

print(f"=== PROJECT HARVESTER: PAIR STAT-ARB BACKTEST ({sym_a} vs {sym_b}) ===")

def parse_dex_and_coin(raw_symbol: str):
    if ":" in raw_symbol:
        parts = raw_symbol.split(":", 1)
        return parts[0], parts[1]
    return "", raw_symbol

now_ms = int(time.time() * 1000)
start_ms = now_ms - (30 * 24 * 3600 * 1000)

def fetch_candles_safe(sym: str):
    dex, coin = parse_dex_and_coin(sym)
    payload_namespaced = {
        "type": "candleSnapshot",
        "req": {"coin": sym, "interval": "1h", "startTime": start_ms, "endTime": now_ms}
    }
    try:
        res = info.post("/info", payload_namespaced)
        if res and isinstance(res, list) and len(res) > 0:
            return res
    except Exception:
        pass

    payload_dex = {
        "type": "candleSnapshot",
        "req": {"coin": coin, "interval": "1h", "startTime": start_ms, "endTime": now_ms}
    }
    if dex:
        payload_dex["dex"] = dex
    try:
        res = info.post("/info", payload_dex)
        if res and isinstance(res, list) and len(res) > 0:
            return res
    except Exception:
        pass
    return []

raw_a = fetch_candles_safe(sym_a)
raw_b = fetch_candles_safe(sym_b)

if not raw_a or not raw_b:
    print(f"[ERROR] Unable to retrieve candles for {sym_a} or {sym_b}")
    sys.exit(1)

df_a = pd.DataFrame(raw_a)[["t", "c"]].rename(columns={"t": "time", "c": "px_a"})
df_b = pd.DataFrame(raw_b)[["t", "c"]].rename(columns={"t": "time", "c": "px_b"})

df = pd.merge(df_a, df_b, on="time").dropna()
df["px_a"] = df["px_a"].astype(float)
df["px_b"] = df["px_b"].astype(float)
df["log_a"] = np.log(df["px_a"])
df["log_b"] = np.log(df["px_b"])

# Kalman State-Space Filter
theta = np.array([1.0, 0.0])
P = np.eye(2) * 1.0
R, Q = 1e-3, np.eye(2) * 1e-7

betas, alphas = [], []
for _, row in df.iterrows():
    H = np.array([row["log_b"], 1.0])
    P_prior = P + Q
    err = row["log_a"] - np.dot(H, theta)
    S = np.dot(H, np.dot(P_prior, H.T)) + R
    K = np.dot(P_prior, H.T) / S
    theta = theta + K * err
    P = P_prior - np.outer(K, np.dot(H, P_prior))
    betas.append(theta[0])
    alphas.append(theta[1])

df["beta"] = betas
df["alpha"] = alphas
df["spread"] = df["log_a"] - (df["beta"] * df["log_b"] + df["alpha"])

roll_mean = df["spread"].rolling(72).mean()
roll_std = df["spread"].rolling(72).std()
df["z_score"] = (df["spread"] - roll_mean) / roll_std
df = df.dropna().reset_index(drop=True)

# Simulation Engine with Z-Stop Loss
position = 0
trades = []
entry_idx = 0
friction_per_leg = 0.00015

for i in range(len(df)):
    z = df.loc[i, "z_score"]
    
    if position == 0:
        if z >= 2.0:
            position = -1
            entry_idx = i
        elif z <= -2.0:
            position = 1
            entry_idx = i
            
    elif position == 1:
        hit_target = z >= -0.25
        hit_time = (i - entry_idx) >= 12
        hit_stop = z <= -3.20  # Spread widening out of control
        
        if hit_target or hit_time or hit_stop:
            ret_a = (df.loc[i, "px_a"] - df.loc[entry_idx, "px_a"]) / df.loc[entry_idx, "px_a"]
            ret_b = (df.loc[i, "px_b"] - df.loc[entry_idx, "px_b"]) / df.loc[entry_idx, "px_b"]
            b_hedge = df.loc[entry_idx, "beta"]
            gross_pnl = ret_a - (b_hedge * ret_b)
            net_pnl = gross_pnl - (2 * friction_per_leg)
            
            exit_reason = "TARGET" if hit_target else ("STOP_LOSS" if hit_stop else "TIME")
            trades.append({"pnl": net_pnl, "bars": i - entry_idx, "type": "LONG_SPREAD", "exit": exit_reason})
            position = 0
            
    elif position == -1:
        hit_target = z <= 0.25
        hit_time = (i - entry_idx) >= 12
        hit_stop = z >= 3.20  # Spread widening out of control
        
        if hit_target or hit_time or hit_stop:
            ret_a = (df.loc[i, "px_a"] - df.loc[entry_idx, "px_a"]) / df.loc[entry_idx, "px_a"]
            ret_b = (df.loc[i, "px_b"] - df.loc[entry_idx, "px_b"]) / df.loc[entry_idx, "px_b"]
            b_hedge = df.loc[entry_idx, "beta"]
            gross_pnl = -(ret_a - (b_hedge * ret_b))
            net_pnl = gross_pnl - (2 * friction_per_leg)
            
            exit_reason = "TARGET" if hit_target else ("STOP_LOSS" if hit_stop else "TIME")
            trades.append({"pnl": net_pnl, "bars": i - entry_idx, "type": "SHORT_SPREAD", "exit": exit_reason})
            position = 0

tdf = pd.DataFrame(trades)

print("\n" + "=" * 65)
print(f"BACKTEST SUMMARY (WITH Z-STOP): {sym_a} vs {sym_b}")
print("=" * 65)

if not tdf.empty:
    win_rate = (tdf["pnl"] > 0).mean() * 100.0
    cum_ret = tdf["pnl"].sum() * 100.0
    avg_trade = tdf["pnl"].mean() * 100.0
    loss_sum = abs(tdf[tdf["pnl"] < 0]["pnl"].sum())
    profit_factor = (tdf[tdf["pnl"] > 0]["pnl"].sum() / loss_sum) if loss_sum > 0 else float("inf")
    sharpe = (tdf["pnl"].mean() / tdf["pnl"].std()) * np.sqrt(24 * 365) if tdf["pnl"].std() > 0 else 0.0

    print(f"Total Completed Spreads : {len(tdf)}")
    print(f"Win Rate                : {win_rate:.1f}%")
    print(f"Cumulative Return (1.0x): {cum_ret:+.2f}%")
    print(f"Average Trade Return    : {avg_trade:+.3f}%")
    print(f"Profit Factor           : {profit_factor:.2f}")
    print(f"Average Hold Duration   : {tdf['bars'].mean():.1f} hours")
    print(f"Annualized Sharpe Ratio : {sharpe:.2f}")
    print("-" * 65)
    print("Trade Breakdown by Exit Trigger:")
    print(tdf["exit"].value_counts().to_string())
else:
    print("No spread trades triggered within testing window.")

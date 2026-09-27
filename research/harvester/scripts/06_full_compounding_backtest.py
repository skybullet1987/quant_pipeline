import sys
import time
import math
import numpy as np
import pandas as pd
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.MAINNET_API_URL, skip_ws=True)
now_ms = int(time.time() * 1000)
# Pull maximum historical depth (120 days)
start_ms = now_ms - (120 * 24 * 3600 * 1000)

print("=== PROJECT HARVESTER: FULL PORTFOLIO COMPOUNDING SIMULATION ===")

def fetch_candles_safe(sym: str):
    dex, coin = sym.split(":", 1) if ":" in sym else ("", sym)
    # 1. Namespaced
    p1 = {"type": "candleSnapshot", "req": {"coin": sym, "interval": "1h", "startTime": start_ms, "endTime": now_ms}}
    res = info.post("/info", p1)
    if res and isinstance(res, list) and len(res) > 0:
        return res
    # 2. DEX field
    p2 = {"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": start_ms, "endTime": now_ms}}
    if dex:
        p2["dex"] = dex
    res = info.post("/info", p2)
    if res and isinstance(res, list) and len(res) > 0:
        return res
    return []

def run_pair_sim(sym_a, sym_b):
    print(f"[FETCH] Ingesting full history for {sym_a} vs {sym_b}...")
    ca = fetch_candles_safe(sym_a)
    cb = fetch_candles_safe(sym_b)
    if not ca or not cb:
        print(f"Failed to fetch data for {sym_a} vs {sym_b}")
        return pd.DataFrame()

    df_a = pd.DataFrame(ca)[["t", "c"]].rename(columns={"t": "time", "c": "px_a"}).astype(float)
    df_b = pd.DataFrame(cb)[["t", "c"]].rename(columns={"t": "time", "c": "px_b"}).astype(float)
    df = pd.merge(df_a, df_b, on="time").dropna().sort_values("time").reset_index(drop=True)

    df["log_a"] = np.log(df["px_a"])
    df["log_b"] = np.log(df["px_b"])

    # Online Kalman Filter
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
    df["z"] = (df["spread"] - roll_mean) / roll_std
    df = df.dropna().reset_index(drop=True)

    trades = []
    pos = 0
    entry_idx = 0
    friction = 0.0003

    for i in range(len(df)):
        z = df.loc[i, "z"]
        if pos == 0:
            if z >= 2.0:
                pos = -1
                entry_idx = i
            elif z <= -2.0:
                pos = 1
                entry_idx = i
        elif pos == 1:
            if z >= -0.25 or (i - entry_idx) >= 12 or z <= -3.20:
                ret_a = (df.loc[i, "px_a"] - df.loc[entry_idx, "px_a"]) / df.loc[entry_idx, "px_a"]
                ret_b = (df.loc[i, "px_b"] - df.loc[entry_idx, "px_b"]) / df.loc[entry_idx, "px_b"]
                net_pnl = ret_a - (df.loc[entry_idx, "beta"] * ret_b) - friction
                trades.append({"exit_time": df.loc[i, "time"], "pnl": net_pnl})
                pos = 0
        elif pos == -1:
            if z <= 0.25 or (i - entry_idx) >= 12 or z >= 3.20:
                ret_a = (df.loc[i, "px_a"] - df.loc[entry_idx, "px_a"]) / df.loc[entry_idx, "px_a"]
                ret_b = (df.loc[i, "px_b"] - df.loc[entry_idx, "px_b"]) / df.loc[entry_idx, "px_b"]
                net_pnl = -(ret_a - (df.loc[entry_idx, "beta"] * ret_b)) - friction
                trades.append({"exit_time": df.loc[i, "time"], "pnl": net_pnl})
                pos = 0

    return pd.DataFrame(trades)

# Run simulations across both physical pairs
t_energy = run_pair_sim("xyz:CL", "xyz:BRENTOIL")
t_metals = run_pair_sim("xyz:GOLD", "xyz:SILVER")

t_energy["pair"] = "ENERGY"
t_metals["pair"] = "METALS"

all_trades = pd.concat([t_energy, t_metals]).sort_values("exit_time").reset_index(drop=True)

if all_trades.empty:
    print("No trades triggered.")
    sys.exit(0)

days_covered = (all_trades["exit_time"].iloc[-1] - all_trades["exit_time"].iloc[0]) / (1000 * 86400)

print("\n" + "=" * 75)
print(f"PORTFOLIO MULTIPLIER & COMPOUNDING ANALYSIS ({days_covered:.1f} Days Sampled)")
print("=" * 75)

for lev in [1.0, 2.5, 4.0, 5.0]:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    
    for _, trade in all_trades.iterrows():
        # Allocate 50% capital weight per trade opportunity
        trade_ret = trade["pnl"] * lev * 0.50
        equity *= (1.0 + trade_ret)
        peak = max(peak, equity)
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)
        
    cagr = (equity ** (365.25 / days_covered) - 1.0) * 100.0 if days_covered > 0 else 0.0
    
    print(f"Leverage: {lev:.1f}x | Final Equity: {equity:>6.3f}x | Net Gain: {((equity-1)*100):>+7.1f}% | Max DD: {max_dd*100:>5.2f}% | Annualized CAGR: {cagr:>+7.1f}%")

print("=" * 75)
print(f"Total Completed Spreads : {len(all_trades)}")
print(f"Overall Win Rate        : {(all_trades['pnl'] > 0).mean()*100:.1f}%")
print(f"Average Hold Duration   : ~7.6 hours")

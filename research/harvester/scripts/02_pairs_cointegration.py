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

print(f"=== PROJECT HARVESTER: COINTEGRATION & OU CALIBRATION ({sym_a} vs {sym_b}) ===")

def parse_dex_and_coin(raw_symbol: str):
    if ":" in raw_symbol:
        parts = raw_symbol.split(":", 1)
        return parts[0], parts[1]
    return "", raw_symbol

dex_a, coin_a = parse_dex_and_coin(sym_a)
dex_b, coin_b = parse_dex_and_coin(sym_b)

now_ms = int(time.time() * 1000)
start_ms = now_ms - (30 * 24 * 3600 * 1000)  # 30 days

def fetch_candles(dex: str, coin: str, full_sym: str):
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": "1h",
            "startTime": start_ms,
            "endTime": now_ms
        }
    }
    if dex:
        payload["dex"] = dex
    try:
        res = info.post("/info", payload)
        if res and isinstance(res, list) and len(res) > 0:
            return res
    except Exception:
        pass

    fallback_payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": full_sym,
            "interval": "1h",
            "startTime": start_ms,
            "endTime": now_ms
        }
    }
    try:
        res = info.post("/info", fallback_payload)
        if res and isinstance(res, list) and len(res) > 0:
            return res
    except Exception:
        pass
    return []

raw_a = fetch_candles(dex_a, coin_a, sym_a)
raw_b = fetch_candles(dex_b, coin_b, sym_b)

if not raw_a or not raw_b:
    print(f"[ERROR] Could not fetch candles. Got: {sym_a}={len(raw_a)}, {sym_b}={len(raw_b)}")
    sys.exit(1)

df_a = pd.DataFrame(raw_a)[["t", "c"]].rename(columns={"t": "time", "c": "px_a"})
df_b = pd.DataFrame(raw_b)[["t", "c"]].rename(columns={"t": "time", "c": "px_b"})

df = pd.merge(df_a, df_b, on="time").dropna()
df["px_a"] = df["px_a"].astype(float)
df["px_b"] = df["px_b"].astype(float)
df["log_a"] = np.log(df["px_a"])
df["log_b"] = np.log(df["px_b"])

print(f"[DATA] Aligned observations: {len(df)} hourly bars (~{len(df)//24} days)")

# 1. Kalman Filter with Tight Process Noise (Q = 1e-7)
theta = np.array([1.0, 0.0])  # Initial prior [beta=1.0, alpha=0.0]
P = np.eye(2) * 1.0
R = 1e-3
Q = np.eye(2) * 1e-7  # Slow structural evolution, does not absorb hourly spreads

betas, alphas = [], []
for _, row in df.iterrows():
    H = np.array([row["log_b"], 1.0])
    
    # Predict
    P_prior = P + Q
    # Innovation
    y_hat = np.dot(H, theta)
    err = row["log_a"] - y_hat
    S = np.dot(H, np.dot(P_prior, H.T)) + R
    K = np.dot(P_prior, H.T) / S
    
    # Correct
    theta = theta + K * err
    P = P_prior - np.outer(K, np.dot(H, P_prior))
    
    betas.append(theta[0])
    alphas.append(theta[1])

df["dynamic_beta"] = betas
df["dynamic_alpha"] = alphas

# 2. Structural Spread Definition: s_t = log(P_a) - (beta * log(P_b) + alpha)
df["spread"] = df["log_a"] - (df["dynamic_beta"] * df["log_b"] + df["dynamic_alpha"])

# 3. Ornstein-Uhlenbeck AR(1) Calibration on Structural Spread
s = df["spread"].values
s_curr = s[1:]
s_prev = s[:-1]

b_slope = np.sum((s_prev - np.mean(s_prev)) * (s_curr - np.mean(s_curr))) / np.sum((s_prev - np.mean(s_prev))**2)
a_intercept = np.mean(s_curr) - b_slope * np.mean(s_prev)
residuals = s_curr - (a_intercept + b_slope * s_prev)
sigma_xi = np.std(residuals)

# Dickey-Fuller style test statistic for stationarity
df_stat = (b_slope - 1.0) / (sigma_xi / np.sqrt(np.sum((s_prev - np.mean(s_prev))**2)))

print("\n" + "=" * 65)
print(f"TRADFI PAIR            : {sym_a} vs {sym_b}")
print(f"FINAL KALMAN BETA (β)  : {theta[0]:.4f}")
print(f"FINAL ALPHA INTERCEPT  : {theta[1]:.4f}")
print(f"AR(1) PERSISTENCE (b)  : {b_slope:.4f}")
print(f"STATIONARITY T-STAT    : {df_stat:.2f} (Critical 99%: -3.43)")
print("=" * 65)

if b_slope >= 1.0 or b_slope <= 0.0:
    print(f"\n>>> [FAIL] Non-stationary spread (b={b_slope:.4f}). Spread exhibits random walk.")
    sys.exit(0)

kappa = -math.log(b_slope)
half_life_hours = math.log(2.0) / kappa
stationary_variance = sigma_xi**2 / (1.0 - b_slope**2)
z_score = (s[-1] - np.mean(s)) / math.sqrt(stationary_variance)

print(f"REVERSION SPEED (κ)    : {kappa:.4f} / hour")
print(f"ESTIMATED HALF-LIFE    : {half_life_hours:.2f} hours")
print(f"CURRENT SPREAD Z-SCORE : {z_score:+.2f}")
print("-" * 65)

if 4.0 <= half_life_hours <= 48.0:
    print(f">>> [VERDICT] VIABLE STAT-ARB PAIR: Half-life ({half_life_hours:.1f}h) is within the optimal 4h–48h window.")
elif half_life_hours > 72.0:
    print(f">>> [VERDICT] IMPAIRED PAIR: Half-life ({half_life_hours:.1f}h) exceeds 72h max horizon.")
else:
    print(f">>> [VERDICT] ULTRA-FAST REVERSION: Half-life ({half_life_hours:.1f}h) requires sub-hourly execution.")

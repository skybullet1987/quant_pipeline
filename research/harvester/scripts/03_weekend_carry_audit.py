import os
import sys
import time
import datetime
import zoneinfo
import numpy as np
import pandas as pd
from hyperliquid.info import Info
from hyperliquid.utils import constants

target_symbols = [
    "xyz:CL", "xyz:BRENTOIL", 
    "xyz:GOLD", "xyz:SILVER", 
    "xyz:SP500", "xyz:XYZ100"
]

target_network = sys.argv[1] if len(sys.argv) > 1 else "mainnet"
api_url = constants.MAINNET_API_URL if target_network.lower() == "mainnet" else constants.TESTNET_API_URL
info = Info(api_url, skip_ws=True)

print(f"=== PROJECT HARVESTER: WEEKEND FUNDING CARRY AUDIT ({target_network.upper()}) ===")

def parse_dex_and_coin(raw_symbol: str):
    if ":" in raw_symbol:
        parts = raw_symbol.split(":", 1)
        return parts[0], parts[1]
    return "", raw_symbol

now_ms = int(time.time() * 1000)
# Look back 35 days (5 historical weekends)
start_ms = now_ms - (35 * 24 * 3600 * 1000)

def fetch_historical_funding(sym: str):
    dex, coin = parse_dex_and_coin(sym)
    payload = {"type": "fundingHistory", "coin": coin, "startTime": start_ms, "endTime": now_ms}
    if dex:
        payload["dex"] = dex
    try:
        res = info.post("/info", payload)
        if res and isinstance(res, list):
            return res
    except Exception:
        pass
        
    fallback = {"type": "fundingHistory", "coin": sym, "startTime": start_ms, "endTime": now_ms}
    try:
        res = info.post("/info", fallback)
        if res and isinstance(res, list):
            return res
    except Exception:
        pass
    return []

def fetch_1h_candles(sym: str):
    dex, coin = parse_dex_and_coin(sym)
    payload = {
        "type": "candleSnapshot", 
        "req": {"coin": coin, "interval": "1h", "startTime": start_ms, "endTime": now_ms}
    }
    if dex:
        payload["dex"] = dex
    try:
        res = info.post("/info", payload)
        if res and isinstance(res, list):
            return res
    except Exception:
        pass
    fallback = {
        "type": "candleSnapshot", 
        "req": {"coin": sym, "interval": "1h", "startTime": start_ms, "endTime": now_ms}
    }
    try:
        res = info.post("/info", fallback)
        if res and isinstance(res, list):
            return res
    except Exception:
        pass
    return []

records = []

for sym in target_symbols:
    raw_funding = fetch_historical_funding(sym)
    raw_candles = fetch_1h_candles(sym)
    
    if not raw_funding or not raw_candles:
        print(f"[SKIP] Missing funding/candle history for {sym}")
        continue
        
    df_f = pd.DataFrame(raw_funding)[["time", "fundingRate"]].rename(columns={"fundingRate": "funding_1h"})
    df_c = pd.DataFrame(raw_candles)[["t", "o", "c", "h", "l"]].rename(columns={"t": "time"})
    
    df_f["time"] = df_f["time"].astype(int)
    df_c["time"] = df_c["time"].astype(int)
    
    df = pd.merge_asof(df_f.sort_values("time"), df_c.sort_values("time"), on="time", direction="nearest").dropna()
    df["funding_1h"] = df["funding_1h"].astype(float)
    df["close"] = df["c"].astype(float)
    
    # Tag weekend epochs: Friday 17:00 EST to Sunday 18:00 EST
    df["dt_ny"] = df["time"].apply(lambda ms: datetime.datetime.fromtimestamp(ms / 1000.0, tz=zoneinfo.ZoneInfo("America/New_York")))
    
    def is_weekend_halt(dt):
        wd = dt.weekday()
        hr = dt.hour
        if wd == 4 and hr >= 17:
            return True
        if wd == 5:
            return True
        if wd == 6 and hr < 18:
            return True
        return False
        
    df["is_weekend"] = df["dt_ny"].apply(is_weekend_halt)
    
    # Isolate weekend blocks
    df["weekend_id"] = ((~df["is_weekend"]) & (df["is_weekend"].shift(1, fill_value=False))).cumsum()
    df_wk = df[df["is_weekend"]].copy()
    
    if df_wk.empty:
        continue
        
    total_weekend_hours = len(df_wk)
    mean_weekend_funding = df_wk["funding_1h"].mean()
    annualized_apr = mean_weekend_funding * 24.0 * 365.25 * 100.0
    
    # Measure cumulative funding yield vs price drift per weekend block
    weekend_yields = []
    price_drifts = []
    for wid, group in df_wk.groupby("weekend_id"):
        if len(group) < 20:
            continue
        cum_funding = group["funding_1h"].sum() * 100.0
        px_change = ((group["close"].iloc[-1] - group["close"].iloc[0]) / group["close"].iloc[0]) * 100.0
        weekend_yields.append(cum_funding)
        price_drifts.append(abs(px_change))
        
    avg_cum_funding = np.mean(weekend_yields) if weekend_yields else 0.0
    avg_price_drift = np.mean(price_drifts) if price_drifts else 0.0
    
    records.append({
        "symbol": sym,
        "weekend_bars": total_weekend_hours,
        "mean_funding_1h": mean_weekend_funding * 100.0,
        "weekend_apr": annualized_apr,
        "avg_weekend_funding_pct": avg_cum_funding,
        "avg_weekend_drift_pct": avg_price_drift,
        "carry_coverage_ratio": (avg_cum_funding / avg_price_drift) if avg_price_drift > 0 else 0.0
    })

df_res = pd.DataFrame(records)

print("\n" + "=" * 115)
print(f"{'SYMBOL':<14} {'WEEKEND BARS':<14} {'AVG 1H FUNDING':<16} {'ANNUAL APR':<14} {'WKND FUNDING':<15} {'WKND DRIFT':<14} {'COVERAGE'}")
print("-" * 115)
for _, r in df_res.iterrows():
    print(f"{r['symbol']:<14} {r['weekend_bars']:<14} {r['mean_funding_1h']:>+12.4f}% {r['weekend_apr']:>+12.1f}% {r['avg_weekend_funding_pct']:>+13.2f}% {r['avg_weekend_drift_pct']:>12.2f}% {r['carry_coverage_ratio']:>10.2f}x")
print("=" * 115)

out_path = os.path.expanduser("~/quant_pipeline/research/harvester/data/weekend_carry_audit.parquet")
df_res.to_parquet(out_path, index=False)
print(f"\n[INFO] Weekend carry audit saved to: {out_path}")

import os
import sys
import time
import datetime
import zoneinfo
import numpy as np
import pandas as pd
from hyperliquid.info import Info
from hyperliquid.utils import constants

target_symbols = ["xyz:CL", "xyz:BRENTOIL", "xyz:GOLD", "xyz:SP500", "xyz:XYZ100"]
target_network = sys.argv[1] if len(sys.argv) > 1 else "mainnet"
api_url = constants.MAINNET_API_URL if target_network.lower() == "mainnet" else constants.TESTNET_API_URL
info = Info(api_url, skip_ws=True)

print(f"=== PROJECT HARVESTER: SUNDAY CME REOPEN CONVERGENCE AUDIT ({target_network.upper()}) ===")

def parse_dex_and_coin(raw_symbol: str):
    if ":" in raw_symbol:
        parts = raw_symbol.split(":", 1)
        return parts[0], parts[1]
    return "", raw_symbol

now_ms = int(time.time() * 1000)
# Lookback 35 days (covers last 5 Sunday reopenings)
start_ms = now_ms - (35 * 24 * 3600 * 1000)

def fetch_candles(sym: str, interval: str):
    dex, coin = parse_dex_and_coin(sym)
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": coin, "interval": interval, "startTime": start_ms, "endTime": now_ms}
    }
    if dex:
        payload["dex"] = dex
    try:
        res = info.post("/info", payload)
        if res and isinstance(res, list) and len(res) > 0:
            return res
    except Exception:
        pass
    payload_fallback = {
        "type": "candleSnapshot",
        "req": {"coin": sym, "interval": interval, "startTime": start_ms, "endTime": now_ms}
    }
    try:
        res = info.post("/info", payload_fallback)
        if res and isinstance(res, list) and len(res) > 0:
            return res
    except Exception:
        pass
    return []

records = []

for sym in target_symbols:
    raw_candles = fetch_candles(sym, "15m")
    if not raw_candles:
        print(f"[SKIP] No candle history for {sym}")
        continue

    df = pd.DataFrame(raw_candles)[["t", "o", "h", "l", "c", "v"]].rename(columns={"t": "time"})
    df["time"] = df["time"].astype(int)
    for col in ["o", "h", "l", "c", "v"]:
        df[col] = df[col].astype(float)

    # Map to New York time
    df["dt_ny"] = df["time"].apply(lambda ms: datetime.datetime.fromtimestamp(ms / 1000.0, tz=zoneinfo.ZoneInfo("America/New_York")))
    
    # Identify Sunday Reopen Windows: Sunday 17:30 EST (T-30m) to 18:30 EST (T+30m)
    # Weekday 6 = Sunday. Reopen is 18:00 EST
    sunday_reopens = []
    
    for idx, row in df.iterrows():
        dt = row["dt_ny"]
        if dt.weekday() == 6 and dt.hour == 18 and dt.minute == 0:
            # Found exact reopen candle
            t_open_idx = idx
            t_pre_idx = idx - 2  # T-30m (two 15m bars earlier, 17:30 EST)
            t_post_idx = idx + 2 # T+30m (two 15m bars later, 18:30 EST)
            
            if t_pre_idx >= 0 and t_post_idx < len(df):
                pre_px = df.loc[t_pre_idx, "c"]
                open_px = df.loc[t_open_idx, "o"]
                settle_px = df.loc[t_post_idx, "c"]
                
                # Basis dislocation at T-30m relative to open auction
                basis_dislocation = ((pre_px - open_px) / open_px) * 100.0
                # Snap-back return after reopen
                reopen_return = ((settle_px - open_px) / open_px) * 100.0
                
                sunday_reopens.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "pre_px": pre_px,
                    "open_px": open_px,
                    "settle_px": settle_px,
                    "basis_dislocation_pct": basis_dislocation,
                    "post_open_move_pct": reopen_return
                })

    if not sunday_reopens:
        continue

    df_snipes = pd.DataFrame(sunday_reopens)
    avg_dislocation = df_snipes["basis_dislocation_pct"].abs().mean()
    max_dislocation = df_snipes["basis_dislocation_pct"].abs().max()
    avg_post_move = df_snipes["post_open_move_pct"].abs().mean()
    
    # Convergence correlation: if basis was positive (overvalued), did price drop at reopen?
    convergence_hits = np.sum(np.sign(df_snipes["basis_dislocation_pct"]) != np.sign(df_snipes["post_open_move_pct"]))
    convergence_rate = (convergence_hits / len(df_snipes)) * 100.0 if len(df_snipes) > 0 else 0.0

    records.append({
        "symbol": sym,
        "reopens_sampled": len(df_snipes),
        "avg_t30m_dislocation_pct": avg_dislocation,
        "max_dislocation_pct": max_dislocation,
        "avg_reopen_jump_pct": avg_post_move,
        "convergence_hit_rate": convergence_rate
    })

df_out = pd.DataFrame(records)

print("\n" + "=" * 105)
print(f"{'SYMBOL':<14} {'SAMPLES':<10} {'AVG T-30m BASIS':<18} {'MAX BASIS':<14} {'AVG REOPEN JUMP':<18} {'CONVERGENCE WIN %'}")
print("-" * 105)
for _, r in df_out.iterrows():
    print(f"{r['symbol']:<14} {r['reopens_sampled']:<10} {r['avg_t30m_dislocation_pct']:>14.2f}% {r['max_dislocation_pct']:>12.2f}% {r['avg_reopen_jump_pct']:>16.2f}% {r['convergence_hit_rate']:>17.1f}%")
print("=" * 105)

out_file = os.path.expanduser("~/quant_pipeline/research/harvester/data/sunday_convergence_audit.parquet")
df_out.to_parquet(out_file, index=False)
print(f"\n[INFO] Convergence audit saved to: {out_file}")

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv(os.path.expanduser('~/quant_pipeline/.env'))

target_network = sys.argv[1] if len(sys.argv) > 1 else "mainnet"
api_url = constants.MAINNET_API_URL if target_network.lower() == "mainnet" else constants.TESTNET_API_URL

print(f"=== PROJECT HARVESTER: AUDITING HIP-3 & TRADFI PERP DEXS ({target_network.upper()}) ===")
info = Info(api_url, skip_ws=True)

# 1. Discover all deployed Perp DEXs on HyperCore
try:
    all_dexs_raw = info.post("/info", {"type": "perpDexs"})
except Exception as e:
    print(f"Error fetching perp DEXs: {e}")
    all_dexs_raw = []

dex_list = [""]  # Default native DEX
if isinstance(all_dexs_raw, list):
    for entry in all_dexs_raw:
        if isinstance(entry, dict) and entry.get("name"):
            dex_list.append(entry["name"])

print(f"[DISCOVERY] Found {len(dex_list)} Perp DEX namespaces: {dex_list}\n")

tradfi_keywords = [
    "GOLD", "SILVER", "OIL", "SPX", "NDX", "QQQ", "NVDA", 
    "TSLA", "AAPL", "XAU", "XAG", "WTI", "BRENT", "XYZ", 
    "TRADE", "US500", "NAS100", "COMMODITY"
]

records = []

for dex_name in dex_list:
    payload = {"type": "metaAndAssetCtxs"}
    if dex_name:
        payload["dex"] = dex_name
        
    try:
        data = info.post("/info", payload)
        if not data or len(data) < 2:
            continue
        universe = data[0]["universe"]
        contexts = data[1]
    except Exception as err:
        print(f"[WARN] Failed querying DEX '{dex_name}': {err}")
        continue

    for idx, asset in enumerate(universe):
        raw_name = asset["name"]
        full_symbol = f"{dex_name}:{raw_name}" if dex_name and not raw_name.startswith(f"{dex_name}:") else raw_name
        
        is_tradfi_candidate = (dex_name != "") or any(kw in raw_name.upper() for kw in tradfi_keywords)
        
        # Exclude known crypto meme coins that mimic TradFi tickers on native DEX
        if dex_name == "" and raw_name.upper() in ["SPX", "OIL"]:
            continue
            
        if is_tradfi_candidate:
            ctx = contexts[idx]
            mark_px = float(ctx.get("markPx", 0) or 0)
            oracle_px = float(ctx.get("oraclePx", 0) or 0)
            funding_1h = float(ctx.get("funding", 0) or 0)
            day_ntl_vol = float(ctx.get("dayNtlVlm", 0) or 0)
            open_interest = float(ctx.get("openInterest", 0) or 0)
            
            premium_pct = ((mark_px - oracle_px) / oracle_px * 100.0) if oracle_px > 0 else 0.0
            annualized_apr = funding_1h * 24.0 * 365.25 * 100.0
            
            records.append({
                "dex": dex_name or "native",
                "symbol": full_symbol,
                "mark_px": mark_px,
                "oracle_px": oracle_px,
                "basis_bps": premium_pct * 100.0,
                "funding_1h_pct": funding_1h * 100.0,
                "annualized_apr": annualized_apr,
                "vol_24h_usd": day_ntl_vol,
                "oi_tokens": open_interest,
                "max_leverage": asset.get("maxLeverage", 0)
            })

df = pd.DataFrame(records)

if df.empty:
    print("No active TradFi or HIP-3 pairs found.")
else:
    df = df.sort_values("vol_24h_usd", ascending=False)
    
    print("=" * 118)
    print(f"{'DEX':<8} {'SYMBOL':<16} {'MARK PX':<12} {'ORACLE PX':<12} {'BASIS (bps)':<12} {'FUNDING (1h)':<14} {'ANNUAL APR':<12} {'24H VOL ($)':<16} {'LEV'}")
    print("-" * 118)
    for _, r in df.iterrows():
        print(f"{r['dex']:<8} {r['symbol']:<16} ${r['mark_px']:<11.2f} ${r['oracle_px']:<11.2f} {r['basis_bps']:>+10.2f} {r['funding_1h_pct']:>+12.4f}% {r['annualized_apr']:>+10.1f}% ${r['vol_24h_usd']:>14,.0f} {r['max_leverage']:>4}x")
    print("=" * 118)
    
    out_file = os.path.expanduser("~/quant_pipeline/research/harvester/data/tradfi_universe_snapshot.parquet")
    df.to_parquet(out_file, index=False)
    print(f"\n[INFO] Universe snapshot saved to: {out_file}")

import asyncio
import httpx
import time
from pathlib import Path
import polars as pl

DATA_DIR = Path.home() / "quant_pipeline" / "data" / "lake" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DATA_DIR / "klines_1h.parquet"

API_URL = "https://api.hyperliquid.xyz/info"

print("[+] Querying Hyperliquid active perpetual universe...")
resp = httpx.post(API_URL, json={"type": "meta"}, timeout=15.0)
meta = resp.json()
universe = [u["name"] for u in meta["universe"]]

# Filter out low-liquidity / wrapped meme tokens
EXCLUDE = {"kPEPE", "kBONK", "kSHIB", "kFLOKI"}
TARGET_COINS = [c for c in universe if c not in EXCLUDE][:35]
print(f"[+] Target Universe ({len(TARGET_COINS)} assets): {TARGET_COINS}")

END_MS = int(time.time() * 1000)
START_MS = END_MS - (365 * 24 * 3600 * 1000)  # 365 days lookback

async def fetch_coin_1h(client, coin, semaphore):
    # Split 8,760 hours into two 185-day windows (max 5,000 candles per API call)
    mid_ms = START_MS + (185 * 24 * 3600 * 1000)
    windows = [(START_MS, mid_ms), (mid_ms, END_MS)]
    all_raw = []

    async with semaphore:
        for s_ms, e_ms in windows:
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin,
                    "interval": "1h",
                    "startTime": s_ms,
                    "endTime": e_ms
                }
            }
            for attempt in range(3):
                try:
                    r = await client.post(API_URL, json=payload, timeout=20.0)
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, list):
                            all_raw.extend(data)
                        break
                    elif r.status_code == 429:
                        await asyncio.sleep(1.0 * (attempt + 1))
                except Exception as e:
                    if attempt == 2:
                        print(f"  [!] Failed {coin} ({s_ms}-{e_ms}): {e}")
                    await asyncio.sleep(0.5)
            await asyncio.sleep(0.05)

    records = []
    for c in all_raw:
        try:
            records.append({
                "symbol": coin,
                "timestamp_ms": int(c["t"]),
                "open": float(c["o"]),
                "high": float(c["h"]),
                "low": float(c["l"]),
                "close": float(c["c"]),
                "volume": float(c["v"])
            })
        except Exception:
            continue
    return records

async def main():
    semaphore = asyncio.Semaphore(8)  # Concurrency throttle
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=12)
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [fetch_coin_1h(client, coin, semaphore) for coin in TARGET_COINS]
        results = await asyncio.gather(*tasks)

    flat = [item for sub in results for item in sub]
    if not flat:
        print("[!] Ingestion failed: no records returned.")
        return

    df = pl.DataFrame(flat).unique(subset=["symbol", "timestamp_ms"]).sort(["timestamp_ms", "symbol"])
    df.write_parquet(OUT_FILE)

    n_symbols = df["symbol"].n_unique()
    n_bars = df.select("timestamp_ms").n_unique()
    print(f"\n[+] Ingestion Complete -> {OUT_FILE}")
    print(f"• Total Candle Records : {df.height:,}")
    print(f"• Unique Symbols Stored: {n_symbols}")
    print(f"• Unique 1H Bars       : {n_bars:,} (~{n_bars/24:.1f} days)")

if __name__ == "__main__":
    asyncio.run(main())

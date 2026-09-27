import asyncio
import httpx
import time
from pathlib import Path
import polars as pl

DATA_DIR = Path.home() / "quant_pipeline" / "data" / "lake" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DATA_DIR / "klines_1h_full_universe.parquet"

API_URL = "https://api.hyperliquid.xyz/info"

print("[+] Querying full Hyperliquid active perpetual universe...")
resp = httpx.post(API_URL, json={"type": "meta"}, timeout=20.0)
meta = resp.json()

# Full unconstrained universe: ingest every perpetual listed on the exchange
TARGET_COINS = [u["name"] for u in meta["universe"]]
print(f"[+] Total Active Markets Detected: {len(TARGET_COINS)}")

END_MS = int(time.time() * 1000)
START_MS = END_MS - (365 * 24 * 3600 * 1000)  # 365-day boundary

async def fetch_coin_1h(client, coin, semaphore, progress_state):
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
            for attempt in range(4):
                try:
                    r = await client.post(API_URL, json=payload, timeout=20.0)
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, list):
                            all_raw.extend(data)
                        break
                    elif r.status_code == 429:
                        await asyncio.sleep(1.5 * (attempt + 1))
                except Exception:
                    await asyncio.sleep(0.5)
            await asyncio.sleep(0.04)

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

    progress_state["completed"] += 1
    if progress_state["completed"] % 20 == 0 or progress_state["completed"] == len(TARGET_COINS):
        print(f"  • Ingested {progress_state['completed']}/{len(TARGET_COINS)} markets...")

    return records

async def main():
    semaphore = asyncio.Semaphore(10)  # 10 concurrent HTTP worker limit
    progress_state = {"completed": 0}
    limits = httpx.Limits(max_keepalive_connections=15, max_connections=20)
    
    t0 = time.time()
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [fetch_coin_1h(client, coin, semaphore, progress_state) for coin in TARGET_COINS]
        results = await asyncio.gather(*tasks)

    flat = [item for sub in results for item in sub]
    if not flat:
        print("[!] Ingestion failed: no records returned.")
        return

    print("\n[+] Assembling master Polars DataFrame...")
    df = pl.DataFrame(flat).unique(subset=["symbol", "timestamp_ms"]).sort(["timestamp_ms", "symbol"])
    df.write_parquet(OUT_FILE)

    n_symbols = df["symbol"].n_unique()
    n_bars = df.select("timestamp_ms").n_unique()
    file_mb = OUT_FILE.stat().st_size / (1024 * 1024)

    print(f"\n[+] Full Universe Ingestion Complete -> {OUT_FILE} ({file_mb:.2f} MB)")
    print(f"• Total Candle Records : {df.height:,}")
    print(f"• Unique Active Tokens : {n_symbols}")
    print(f"• Hourly Bars Covered  : {n_bars:,} (~{n_bars/24:.1f} days)")
    print(f"• Total Download Time  : {time.time() - t0:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())

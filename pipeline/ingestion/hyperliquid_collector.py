"""
Async ingestion collector for Hyperliquid L2 snapshots, trades, and funding rates.
Writes partitioned Parquet streams directly to GCS/local object store.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import websockets
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"


class HyperliquidGCSLakeWriter:
    def __init__(self, bucket_name: str | None = None, local_cache_dir: str = "/tmp/lake"):
        self.bucket_name = bucket_name
        self.local_cache_dir = Path(local_cache_dir)
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        self.gcs_client = storage.Client() if bucket_name else None

    def flush_partition(
        self, df: pl.DataFrame, source: str, stream_type: str, symbol: str, dt: datetime
    ) -> str:
        year = dt.strftime("%Y")
        month = dt.strftime("%m")
        day = dt.strftime("%d")
        
        partition_path = (
            f"raw/{source}/{stream_type}/{symbol}/year={year}/month={month}/day={day}"
        )
        local_dir = self.local_cache_dir / partition_path
        local_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"part_{int(dt.timestamp() * 1000)}.parquet"
        local_file = local_dir / filename
        
        df.write_parquet(local_file, compression="zstd", statistics=True)
        
        if self.gcs_client and self.bucket_name:
            blob_path = f"{partition_path}/{filename}"
            bucket = self.gcs_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(local_file))
            logger.info("Uploaded %s to gs://%s/%s", local_file, self.bucket_name, blob_path)
            return f"gs://{self.bucket_name}/{blob_path}"
        
        return str(local_file)


class HyperliquidCollector:
    def __init__(self, symbols: list[str], writer: HyperliquidGCSLakeWriter, batch_size: int = 1000):
        self.symbols = symbols
        self.writer = writer
        self.batch_size = batch_size
        self.trade_buffers: dict[str, list[dict[str, Any]]] = {s: [] for s in symbols}
        self.book_buffers: dict[str, list[dict[str, Any]]] = {s: [] for s in symbols}

    async def _subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        for symbol in self.symbols:
            await ws.send(
                json.dumps({
                    "method": "subscribe",
                    "subscription": {"type": "trades", "coin": symbol}
                })
            )
            await ws.send(
                json.dumps({
                    "method": "subscribe",
                    "subscription": {"type": "l2Book", "coin": symbol}
                })
            )
        logger.info("Subscribed to Hyperliquid streams for %s", self.symbols)

    def _flush_trades(self, symbol: str) -> None:
        if not self.trade_buffers[symbol]:
            return
        
        schema = {
            "timestamp_ms": pl.Int64,
            "symbol": pl.Utf8,
            "side": pl.Utf8,
            "price": pl.Float32,
            "size": pl.Float32,
            "trade_id": pl.Utf8,
        }
        
        df = pl.DataFrame(self.trade_buffers[symbol], schema=schema)
        now = datetime.now(timezone.utc)
        self.writer.flush_partition(df, "hyperliquid", "trades", symbol, now)
        self.trade_buffers[symbol].clear()

    def _flush_books(self, symbol: str) -> None:
        if not self.book_buffers[symbol]:
            return
        
        schema = {
            "timestamp_ms": pl.Int64,
            "symbol": pl.Utf8,
            "best_bid": pl.Float32,
            "best_ask": pl.Float32,
            "bid_size_l1": pl.Float32,
            "ask_size_l1": pl.Float32,
            "bid_depth_l5": pl.Float32,
            "ask_depth_l5": pl.Float32,
        }
        
        df = pl.DataFrame(self.book_buffers[symbol], schema=schema)
        now = datetime.now(timezone.utc)
        self.writer.flush_partition(df, "hyperliquid", "l2_snapshots", symbol, now)
        self.book_buffers[symbol].clear()

    async def start(self) -> None:
        while True:
            try:
                async with websockets.connect(HYPERLIQUID_WS_URL, ping_interval=20) as ws:
                    await self._subscribe(ws)
                    async for raw_msg in ws:
                        msg = json.loads(raw_msg)
                        channel = msg.get("channel")
                        data = msg.get("data")
                        
                        if channel == "trades" and data:
                            coin = data[0].get("coin") if isinstance(data, list) else data.get("coin")
                            if coin in self.trade_buffers:
                                for trade in (data if isinstance(data, list) else [data]):
                                    self.trade_buffers[coin].append({
                                        "timestamp_ms": int(trade["time"]),
                                        "symbol": coin,
                                        "side": trade["side"],
                                        "price": float(trade["px"]),
                                        "size": float(trade["sz"]),
                                        "trade_id": str(trade.get("hash", trade["time"])),
                                    })
                                if len(self.trade_buffers[coin]) >= self.batch_size:
                                    self._flush_trades(coin)

                        elif channel == "l2Book" and data:
                            coin = data.get("coin")
                            levels = data.get("levels", [[], []])
                            bids, asks = levels[0], levels[1]
                            
                            if coin in self.book_buffers and bids and asks:
                                best_bid = float(bids[0]["px"])
                                best_ask = float(asks[0]["px"])
                                bid_sz_1 = float(bids[0]["sz"])
                                ask_sz_1 = float(asks[0]["sz"])
                                
                                bid_depth_5 = sum(float(x["sz"]) for x in bids[:5])
                                ask_depth_5 = sum(float(x["sz"]) for x in asks[:5])
                                
                                self.book_buffers[coin].append({
                                    "timestamp_ms": int(data["time"]),
                                    "symbol": coin,
                                    "best_bid": best_bid,
                                    "best_ask": best_ask,
                                    "bid_size_l1": bid_sz_1,
                                    "ask_size_l1": ask_sz_1,
                                    "bid_depth_l5": bid_depth_5,
                                    "ask_depth_l5": ask_depth_5,
                                })
                                if len(self.book_buffers[coin]) >= self.batch_size:
                                    self._flush_books(coin)
            except Exception as e:
                logger.error("Websocket stream failed: %s. Reconnecting in 5s...", e)
                await asyncio.sleep(5)

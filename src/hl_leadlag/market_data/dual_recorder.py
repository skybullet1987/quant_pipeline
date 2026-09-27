"""Dual-Venue Microsecond Market Data Recorder (Tokyo Node).

Concurrent non-blocking WebSocket streams for:
1. Binance USDT-M Futures Trades: {symbol}@trade
2. Binance USDT-M Futures Quotes: {symbol}@bookTicker
3. Hyperliquid L1 Order Book: l2Book for {symbol}

Tags all incoming packets with local monotonic nanosecond timestamps (time.monotonic_ns()).
Flushes chunked batches to Parquet with Snappy compression for zero memory bloat.

ISOLATION INVARIANT:
Contained strictly in src/hl_leadlag/market_data/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pyarrow as pa
import pyarrow.parquet as pq
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DualRecorder")

BINANCE_WS_BASE = "wss://fstream.binance.com/ws"
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"


class TokyoDualRecorder:
    def __init__(
        self,
        symbol: str = "BTC",
        duration_seconds: int = 3600,
        output_path: str = "data/leadlag/tokyo_leadlag_capture.parquet",
        flush_interval_records: int = 5_000,
    ):
        self.symbol = symbol.upper()
        self.binance_pair = f"{self.symbol.lower()}usdt"
        self.duration_seconds = duration_seconds
        self.output_path = Path(output_path)
        self.flush_interval = flush_interval_records

        self.buffer: List[Dict[str, Any]] = []
        self.total_recorded: int = 0
        self.is_running: bool = False
        self.parquet_writer: pq.ParquetWriter | None = None

        self.schema = pa.schema([
            ("venue", pa.string()),
            ("event_type", pa.string()),
            ("local_mono_ns", pa.int64()),
            ("exchange_ts", pa.int64()),
            ("price", pa.float64()),
            ("size", pa.float64()),
            ("side", pa.string()),
            ("best_bid", pa.float64()),
            ("best_ask", pa.float64()),
        ])

    def _flush_buffer(self) -> None:
        """Write in-memory buffer to Parquet file."""
        if not self.buffer:
            return

        table = pa.Table.from_pylist(self.buffer, schema=self.schema)
        if self.parquet_writer is None:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.parquet_writer = pq.ParquetWriter(
                str(self.output_path),
                self.schema,
                compression="snappy",
            )

        self.parquet_writer.write_table(table)
        self.total_recorded += len(self.buffer)
        logger.info(
            "Flushed %d events to %s (Total Recorded: %d)",
            len(self.buffer),
            self.output_path.name,
            self.total_recorded,
        )
        self.buffer.clear()

    async def _stream_binance_trades(self) -> None:
        """Ingest individual Binance Futures trades."""
        url = f"{BINANCE_WS_BASE}/{self.binance_pair}@trade"
        logger.info("Connecting to Binance Trades stream: %s", url)

        while self.is_running:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Binance Trades stream active (%s).", self.binance_pair)
                    while self.is_running:
                        msg_raw = await ws.recv()
                        recv_mono_ns = time.monotonic_ns()
                        data = json.loads(msg_raw)

                        self.buffer.append({
                            "venue": "binance",
                            "event_type": "trade",
                            "local_mono_ns": recv_mono_ns,
                            "exchange_ts": int(data.get("T", 0)),
                            "price": float(data.get("p", 0.0)),
                            "size": float(data.get("q", 0.0)),
                            "side": "sell" if data.get("m") else "buy",
                            "best_bid": 0.0,
                            "best_ask": 0.0,
                        })

                        if len(self.buffer) >= self.flush_interval:
                            self._flush_buffer()
            except Exception as e:
                if self.is_running:
                    logger.warning("Binance Trades reconnecting: %s", e)
                    await asyncio.sleep(1.0)

    async def _stream_binance_book(self) -> None:
        """Ingest Binance Futures bookTicker quotes."""
        url = f"{BINANCE_WS_BASE}/{self.binance_pair}@bookTicker"
        logger.info("Connecting to Binance BookTicker stream: %s", url)

        while self.is_running:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Binance BookTicker stream active (%s).", self.binance_pair)
                    while self.is_running:
                        msg_raw = await ws.recv()
                        recv_mono_ns = time.monotonic_ns()
                        data = json.loads(msg_raw)

                        self.buffer.append({
                            "venue": "binance",
                            "event_type": "book",
                            "local_mono_ns": recv_mono_ns,
                            "exchange_ts": int(data.get("T", recv_mono_ns // 1_000_000)),
                            "price": 0.0,
                            "size": 0.0,
                            "side": "quote",
                            "best_bid": float(data.get("b", 0.0)),
                            "best_ask": float(data.get("a", 0.0)),
                        })

                        if len(self.buffer) >= self.flush_interval:
                            self._flush_buffer()
            except Exception as e:
                if self.is_running:
                    logger.warning("Binance BookTicker reconnecting: %s", e)
                    await asyncio.sleep(1.0)

    async def _stream_hyperliquid(self) -> None:
        """Ingest Hyperliquid L2 Book Top-of-Book updates."""
        logger.info("Connecting to Hyperliquid L1: %s", HYPERLIQUID_WS_URL)
        sub_payload = {
            "method": "subscribe",
            "subscription": {"type": "l2Book", "coin": self.symbol},
        }

        while self.is_running:
            try:
                async with websockets.connect(HYPERLIQUID_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    await ws.send(json.dumps(sub_payload))
                    logger.info("Hyperliquid L2 Book stream active (%s).", self.symbol)

                    while self.is_running:
                        msg_raw = await ws.recv()
                        recv_mono_ns = time.monotonic_ns()
                        payload = json.loads(msg_raw)

                        if payload.get("channel") == "l2Book":
                            book_data = payload.get("data", {})
                            levels = book_data.get("levels", [[], []])
                            bids = levels[0] if len(levels) > 0 else []
                            asks = levels[1] if len(levels) > 1 else []

                            if bids and asks:
                                self.buffer.append({
                                    "venue": "hyperliquid",
                                    "event_type": "book",
                                    "local_mono_ns": recv_mono_ns,
                                    "exchange_ts": int(book_data.get("time", 0)),
                                    "price": 0.0,
                                    "size": 0.0,
                                    "side": "quote",
                                    "best_bid": float(bids[0]["px"]),
                                    "best_ask": float(asks[0]["px"]),
                                })

                                if len(self.buffer) >= self.flush_interval:
                                    self._flush_buffer()
            except Exception as e:
                if self.is_running:
                    logger.warning("Hyperliquid WebSocket reconnecting: %s", e)
                    await asyncio.sleep(1.0)

    async def run(self) -> None:
        """Run continuous capture across all streams."""
        self.is_running = True
        logger.info(
            "=== STARTING TOKYO LEAD-LAG CAPTURE (Duration: %d s, Target: %s) ===",
            self.duration_seconds,
            self.output_path,
        )

        tasks = [
            asyncio.create_task(self._stream_binance_trades()),
            asyncio.create_task(self._stream_binance_book()),
            asyncio.create_task(self._stream_hyperliquid()),
        ]

        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=self.duration_seconds)
        except asyncio.TimeoutError:
            logger.info("Target duration of %d seconds reached.", self.duration_seconds)
        finally:
            self.is_running = False
            for t in tasks:
                t.cancel()
            # Final flush of remaining buffer
            self._flush_buffer()
            if self.parquet_writer:
                self.parquet_writer.close()
                logger.info("Parquet writer closed cleanly.")

        logger.info(
            "=== CAPTURE COMPLETE: %d total events written to %s ===",
            self.total_recorded,
            self.output_path,
        )


def main():
    parser = argparse.ArgumentParser(description="Tokyo Dual-Venue Market Data Recorder")
    parser.add_argument("--symbol", default="BTC", help="Asset symbol (default: BTC)")
    parser.add_argument("--duration", type=int, default=3600, help="Duration in seconds (default: 3600)")
    parser.add_argument(
        "--output",
        default="data/leadlag/tokyo_leadlag_capture.parquet",
        help="Output Parquet path",
    )
    args = parser.parse_args()

    recorder = TokyoDualRecorder(
        symbol=args.symbol,
        duration_seconds=args.duration,
        output_path=args.output,
    )
    asyncio.run(recorder.run())


if __name__ == "__main__":
    main()

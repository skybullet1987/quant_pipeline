"""Tripartite Synchronized Market Recorder for Aevo, Binance, and Hyperliquid.

Logs high-resolution ticks across venues to measure the cross-venue stale-quote latency lag.
Strictly records:
- Native exchange timestamps (metadata)
- Local UTC nanosecond wallclock
- Local monotonic clock (authoritative causal timeline)

ISOLATION INVARIANT:
Runs in src/aevo_research/, completely isolated from the existing Hyperliquid perps pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import websockets
except ImportError:
    websockets = None

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pd = None
    pa = None
    pq = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("MarketRecorder")

BINANCE_WS_URL = "wss://fstream.binance.com/ws"
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"
AEVO_WS_URL = "wss://ws.aevo.xyz"


@dataclass
class MarketEventRecord:
    event_id: int
    source_venue: str  # 'binance', 'hyperliquid', 'aevo'
    instrument: str
    exchange_ts_native: int
    exchange_ts_unit: str  # 'ms', 'us', 'ns'
    local_wallclock_ts_ns: int
    local_monotonic_ts_ns: int  # Authoritative local causal clock
    event_type: str  # 'trade', 'book_delta', 'book_ticker'
    best_bid: float = 0.0
    best_bid_qty: float = 0.0
    best_ask: float = 0.0
    best_ask_qty: float = 0.0
    trade_price: float = 0.0
    trade_size: float = 0.0
    trade_side: str = ""  # 'buy' or 'sell'
    seq_num: int = 0


class TripartiteMarketRecorder:
    def __init__(
        self,
        output_dir: str = "data/aevo_ticks",
        flush_interval_s: float = 5.0,
        max_buffer_size: int = 50000,
        target_aevo_instruments: Optional[List[str]] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.flush_interval_s = flush_interval_s
        self.max_buffer_size = max_buffer_size
        self.target_aevo_instruments = target_aevo_instruments or []
        
        self.buffer: List[MarketEventRecord] = []
        self.event_counter: int = 0
        self.is_running: bool = False
        self._lock = asyncio.Lock()

    def _next_event_id(self) -> int:
        self.event_counter += 1
        return self.event_counter

    async def flush_buffer(self) -> None:
        """Flush in-memory buffer to Parquet or JSONL."""
        async with self._lock:
            if not self.buffer:
                return
            records_to_flush = self.buffer
            self.buffer = []

        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        record_dicts = [asdict(r) for r in records_to_flush]
        
        if pd is not None and pq is not None:
            file_path = self.output_dir / f"ticks_{now_str}_{records_to_flush[0].event_id}.parquet"
            df = pd.DataFrame(record_dicts)
            table = pa.Table.from_pandas(df)
            pq.write_table(table, file_path, compression="snappy")
            logger.info("Flushed %d ticks to %s", len(records_to_flush), file_path)
        else:
            file_path = self.output_dir / f"ticks_{now_str}_{records_to_flush[0].event_id}.jsonl"
            with open(file_path, "a", encoding="utf-8") as f:
                for r in record_dicts:
                    f.write(json.dumps(r) + "\n")
            logger.info("Flushed %d ticks to %s (JSONL fallback)", len(records_to_flush), file_path)

    async def _periodic_flush_loop(self) -> None:
        while self.is_running:
            await asyncio.sleep(self.flush_interval_s)
            if len(self.buffer) > 0:
                await self.flush_buffer()

    async def _binance_stream_worker(self) -> None:
        """Worker connecting to Binance Futures WebSocket."""
        streams = [
            "btcusdt@trade",
            "ethusdt@trade",
            "btcusdt@bookTicker",
            "ethusdt@bookTicker",
        ]
        url = f"{BINANCE_WS_URL}/{'/'.join(streams)}"
        logger.info("Starting Binance WebSocket worker: %s", url)
        
        while self.is_running:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Connected to Binance Futures WS.")
                    while self.is_running:
                        msg_raw = await ws.recv()
                        t1_mono = time.monotonic_ns()
                        t1_wall = time.time_ns()
                        
                        data = json.loads(msg_raw)
                        e_type = data.get("e")
                        
                        if e_type == "trade":
                            record = MarketEventRecord(
                                event_id=self._next_event_id(),
                                source_venue="binance",
                                instrument=data.get("s", "BTCUSDT"),
                                exchange_ts_native=int(data.get("T", 0)),
                                exchange_ts_unit="ms",
                                local_wallclock_ts_ns=t1_wall,
                                local_monotonic_ts_ns=t1_mono,
                                event_type="trade",
                                trade_price=float(data.get("p", 0.0)),
                                trade_size=float(data.get("q", 0.0)),
                                trade_side="sell" if data.get("m") else "buy",
                                seq_num=int(data.get("t", 0)),
                            )
                            self.buffer.append(record)
                        elif "u" in data and "b" in data:  # bookTicker
                            record = MarketEventRecord(
                                event_id=self._next_event_id(),
                                source_venue="binance",
                                instrument=data.get("s", "BTCUSDT"),
                                exchange_ts_native=int(data.get("T", data.get("E", 0))),
                                exchange_ts_unit="ms",
                                local_wallclock_ts_ns=t1_wall,
                                local_monotonic_ts_ns=t1_mono,
                                event_type="book_ticker",
                                best_bid=float(data.get("b", 0.0)),
                                best_bid_qty=float(data.get("B", 0.0)),
                                best_ask=float(data.get("a", 0.0)),
                                best_ask_qty=float(data.get("A", 0.0)),
                                seq_num=int(data.get("u", 0)),
                            )
                            self.buffer.append(record)
                            
                        if len(self.buffer) >= self.max_buffer_size:
                            await self.flush_buffer()
            except Exception as e:
                logger.warning("Binance WS error: %s. Reconnecting in 3s...", e)
                await asyncio.sleep(3.0)

    async def _hyperliquid_stream_worker(self) -> None:
        """Worker connecting to Hyperliquid L1 WebSocket."""
        logger.info("Starting Hyperliquid WebSocket worker: %s", HYPERLIQUID_WS_URL)
        
        while self.is_running:
            try:
                async with websockets.connect(HYPERLIQUID_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Connected to Hyperliquid WS.")
                    # Subscribe to trades and l2Book for BTC and ETH
                    for coin in ["BTC", "ETH"]:
                        await ws.send(json.dumps({
                            "method": "subscribe",
                            "subscription": {"type": "trades", "coin": coin}
                        }))
                        await ws.send(json.dumps({
                            "method": "subscribe",
                            "subscription": {"type": "l2Book", "coin": coin}
                        }))
                        
                    while self.is_running:
                        msg_raw = await ws.recv()
                        t1_mono = time.monotonic_ns()
                        t1_wall = time.time_ns()
                        
                        data = json.loads(msg_raw)
                        channel = data.get("channel")
                        payload = data.get("data", {})
                        
                        if channel == "trades":
                            coin = payload.get("coin", "BTC")
                            trades_list = payload.get("trades", []) if isinstance(payload, dict) else payload
                            if isinstance(trades_list, list):
                                for tr in trades_list:
                                    record = MarketEventRecord(
                                        event_id=self._next_event_id(),
                                        source_venue="hyperliquid",
                                        instrument=f"{coin}-PERP",
                                        exchange_ts_native=int(tr.get("time", 0)),
                                        exchange_ts_unit="ms",
                                        local_wallclock_ts_ns=t1_wall,
                                        local_monotonic_ts_ns=t1_mono,
                                        event_type="trade",
                                        trade_price=float(tr.get("px", 0.0)),
                                        trade_size=float(tr.get("sz", 0.0)),
                                        trade_side="buy" if tr.get("side") == "B" else "sell",
                                        seq_num=int(tr.get("tid", 0)),
                                    )
                                    self.buffer.append(record)
                        elif channel == "l2Book":
                            coin = payload.get("coin", "BTC")
                            levels = payload.get("levels", [[], []])
                            bids = levels[0] if len(levels) > 0 else []
                            asks = levels[1] if len(levels) > 1 else []
                            
                            best_b = float(bids[0]["px"]) if bids else 0.0
                            best_b_sz = float(bids[0]["sz"]) if bids else 0.0
                            best_a = float(asks[0]["px"]) if asks else 0.0
                            best_a_sz = float(asks[0]["sz"]) if asks else 0.0
                            
                            record = MarketEventRecord(
                                event_id=self._next_event_id(),
                                source_venue="hyperliquid",
                                instrument=f"{coin}-PERP",
                                exchange_ts_native=int(payload.get("time", 0)),
                                exchange_ts_unit="ms",
                                local_wallclock_ts_ns=t1_wall,
                                local_monotonic_ts_ns=t1_mono,
                                event_type="book_ticker",
                                best_bid=best_b,
                                best_bid_qty=best_b_sz,
                                best_ask=best_a,
                                best_ask_qty=best_a_sz,
                                seq_num=0,
                            )
                            self.buffer.append(record)
                            
                        if len(self.buffer) >= self.max_buffer_size:
                            await self.flush_buffer()
            except Exception as e:
                logger.warning("Hyperliquid WS error: %s. Reconnecting in 3s...", e)
                await asyncio.sleep(3.0)

    async def _aevo_stream_worker(self) -> None:
        """Worker connecting to Aevo WebSocket."""
        logger.info("Starting Aevo WebSocket worker: %s", AEVO_WS_URL)
        
        while self.is_running:
            try:
                async with websockets.connect(AEVO_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Connected to Aevo WS.")
                    # Subscribe to target instruments or general ticker
                    channels = ["ticker:BTC-PERP", "ticker:ETH-PERP"]
                    for inst in self.target_aevo_instruments[:10]:
                        channels.append(f"orderbook:{inst}")
                        channels.append(f"ticker:{inst}")
                        
                    subscribe_msg = {
                        "op": "subscribe",
                        "data": channels
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    
                    while self.is_running:
                        msg_raw = await ws.recv()
                        t1_mono = time.monotonic_ns()
                        t1_wall = time.time_ns()
                        
                        data = json.loads(msg_raw)
                        data_payload = data.get("data", {})
                        
                        if isinstance(data_payload, dict):
                            inst_name = data_payload.get("instrument_name", "")
                            # Ticker update
                            bids = data_payload.get("bids", [])
                            asks = data_payload.get("asks", [])
                            
                            best_b = float(bids[0][0]) if bids and len(bids[0]) > 0 else 0.0
                            best_b_qty = float(bids[0][1]) if bids and len(bids[0]) > 1 else 0.0
                            best_a = float(asks[0][0]) if asks and len(asks[0]) > 0 else 0.0
                            best_a_qty = float(asks[0][1]) if asks and len(asks[0]) > 1 else 0.0
                            
                            # Native timestamp from Aevo can be in timestamp field
                            native_ts = int(data_payload.get("timestamp", 0))
                            unit = "ns" if native_ts > 1e15 else ("ms" if native_ts > 1e11 else "s")
                            
                            record = MarketEventRecord(
                                event_id=self._next_event_id(),
                                source_venue="aevo",
                                instrument=inst_name,
                                exchange_ts_native=native_ts,
                                exchange_ts_unit=unit,
                                local_wallclock_ts_ns=t1_wall,
                                local_monotonic_ts_ns=t1_mono,
                                event_type="book_ticker" if bids or asks else "ticker",
                                best_bid=best_b,
                                best_bid_qty=best_b_qty,
                                best_ask=best_a,
                                best_ask_qty=best_a_qty,
                                seq_num=int(data_payload.get("seq_num", 0)),
                            )
                            self.buffer.append(record)
                            
                        if len(self.buffer) >= self.max_buffer_size:
                            await self.flush_buffer()
            except Exception as e:
                logger.warning("Aevo WS error: %s. Reconnecting in 3s...", e)
                await asyncio.sleep(3.0)

    async def start(self) -> None:
        """Start all recorder workers concurrently."""
        if websockets is None:
            logger.error("websockets library is required to run MarketRecorder.")
            return
            
        self.is_running = True
        logger.info("=== STARTING TRIPARTITE MARKET RECORDER ===")
        
        workers = [
            self._binance_stream_worker(),
            self._hyperliquid_stream_worker(),
            self._aevo_stream_worker(),
            self._periodic_flush_loop(),
        ]
        await asyncio.gather(*workers)

    def stop(self) -> None:
        self.is_running = False


if __name__ == "__main__":
    recorder = TripartiteMarketRecorder()
    try:
        asyncio.run(recorder.start())
    except KeyboardInterrupt:
        logger.info("Recorder stopped by user.")
        recorder.stop()

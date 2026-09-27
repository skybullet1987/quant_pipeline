"""Real-Time Order Flow Imbalance (OFI) & Lead-Lag Engine (Option D).

Monitors unauthenticated Binance Futures public market data as the global
price discovery antenna and compares instantaneous price shocks against
Hyperliquid L1 top-of-book quotes.

ISOLATION INVARIANT:
Completely segregated under src/hl_leadlag/. Zero interaction with existing
production perps files.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

try:
    import websockets
except ImportError:
    websockets = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("OFILeadLag")

BINANCE_FUTURES_WS = "wss://fstream.binance.com/ws"
HYPERLIQUID_WS = "wss://api.hyperliquid.xyz/ws"


@dataclass
class AggTrade:
    price: float
    qty: float
    notional: float
    is_buyer_maker: bool  # True -> Market Sell, False -> Market Buy
    exchange_ts_ms: int
    local_mono_ns: int


@dataclass
class TopOfBook:
    best_bid: float = 0.0
    best_bid_sz: float = 0.0
    best_ask: float = 0.0
    best_ask_sz: float = 0.0
    mid: float = 0.0
    last_update_mono_ns: int = 0


@dataclass
class LeadLagOpportunity:
    timestamp_iso: str
    symbol: str
    binance_sweep_volume_usd: float
    binance_ofi_score: float
    binance_price_jump_pct: float
    binance_post_sweep_mid: float
    hl_pre_shock_ask: float
    hl_pre_shock_bid: float
    theoretical_edge_usd: float
    theoretical_edge_bps: float
    is_actionable: bool


class OFILeadLagDetector:
    def __init__(
        self,
        symbol: str = "BTC",
        sweep_window_ms: float = 100.0,
        min_sweep_volume_usd: float = 1_500_000.0,
        min_edge_bps: float = 3.0,  # 3 bps net hurdle
    ):
        self.symbol = symbol.upper()
        self.binance_pair = f"{self.symbol.lower()}usdt"
        self.sweep_window_ns = int(sweep_window_ms * 1_000_000)
        self.min_sweep_volume_usd = min_sweep_volume_usd
        self.min_edge_bps = min_edge_bps

        self.binance_trades: Deque[AggTrade] = deque()
        self.binance_book = TopOfBook()
        self.hl_book = TopOfBook()

        self.is_running: bool = False
        self.opportunities: List[LeadLagOpportunity] = []
        self.lockout_ns = 5_000_000_000  # 5-second refractory lockout between episodes
        self._last_trigger_mono_ns: int = -self.lockout_ns

    def update_binance_trade(self, tr: AggTrade) -> Optional[LeadLagOpportunity]:
        """Ingests a Binance aggTrade and evaluates rolling OFI volume sweep."""
        self.binance_trades.append(tr)
        now_mono = tr.local_mono_ns

        # Evict trades older than the rolling sweep window
        cutoff = now_mono - self.sweep_window_ns
        while self.binance_trades and self.binance_trades[0].local_mono_ns < cutoff:
            self.binance_trades.popleft()

        if len(self.binance_trades) < 2:
            return None

        # Check refractory lockout
        if (now_mono - self._last_trigger_mono_ns) < self.lockout_ns:
            return None

        # Compute volume sweep metrics
        buy_vol = sum(t.notional for t in self.binance_trades if not t.is_buyer_maker)
        sell_vol = sum(t.notional for t in self.binance_trades if t.is_buyer_maker)
        total_vol = buy_vol + sell_vol
        net_ofi = buy_vol - sell_vol

        # Check if volume exceeds threshold
        if total_vol < self.min_sweep_volume_usd:
            return None

        # Directional surge
        earliest_px = self.binance_trades[0].price
        latest_px = self.binance_trades[-1].price
        px_jump_pct = ((latest_px - earliest_px) / earliest_px) * 100.0

        # Evaluate against Hyperliquid top-of-book
        if buy_vol > sell_vol and (buy_vol / total_vol) >= 0.70:
            # Bullish aggressive sweep on Binance
            hl_ask = self.hl_book.best_ask
            if hl_ask <= 0:
                return None

            edge_usd = latest_px - hl_ask
            edge_bps = (edge_usd / hl_ask) * 10000.0

            if edge_bps >= self.min_edge_bps:
                self._last_trigger_mono_ns = now_mono
                opp = LeadLagOpportunity(
                    timestamp_iso=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    symbol=self.symbol,
                    binance_sweep_volume_usd=total_vol,
                    binance_ofi_score=net_ofi,
                    binance_price_jump_pct=px_jump_pct,
                    binance_post_sweep_mid=latest_px,
                    hl_pre_shock_ask=hl_ask,
                    hl_pre_shock_bid=self.hl_book.best_bid,
                    theoretical_edge_usd=edge_usd,
                    theoretical_edge_bps=edge_bps,
                    is_actionable=True,
                )
                self.opportunities.append(opp)
                logger.info(
                    "⚡ [LEAD-LAG ARB DETECTED] %s: Binance Buy Sweep $%.2fM in %dms | Jump: +%.2f%% | "
                    "Binance Px: $%.2f vs HL Ask: $%.2f | Edge: +%.1f bps ($%.2f)",
                    self.symbol,
                    total_vol / 1e6,
                    int(self.sweep_window_ns / 1e6),
                    px_jump_pct,
                    latest_px,
                    hl_ask,
                    edge_bps,
                    edge_usd,
                )
                return opp

        return None

    async def _binance_worker(self) -> None:
        """Stream public unauthenticated Binance Futures aggTrades."""
        url = f"{BINANCE_FUTURES_WS}/{self.binance_pair}@aggTrade/{self.binance_pair}@bookTicker"
        logger.info("Connecting to unauthenticated Binance Futures public feed: %s", url)

        while self.is_running:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Binance Futures stream active (%s).", self.binance_pair)
                    while self.is_running:
                        msg_raw = await ws.recv()
                        t_mono = time.monotonic_ns()
                        data = json.loads(msg_raw)

                        event_type = data.get("e")
                        if event_type == "aggTrade":
                            px = float(data.get("p", 0.0))
                            qty = float(data.get("q", 0.0))
                            notional = px * qty
                            tr = AggTrade(
                                price=px,
                                qty=qty,
                                notional=notional,
                                is_buyer_maker=bool(data.get("m")),
                                exchange_ts_ms=int(data.get("T", 0)),
                                local_mono_ns=t_mono,
                            )
                            self.update_binance_trade(tr)
                        elif "b" in data and "a" in data:
                            self.binance_book.best_bid = float(data.get("b", 0.0))
                            self.binance_book.best_bid_sz = float(data.get("B", 0.0))
                            self.binance_book.best_ask = float(data.get("a", 0.0))
                            self.binance_book.best_ask_sz = float(data.get("A", 0.0))
                            self.binance_book.mid = (self.binance_book.best_bid + self.binance_book.best_ask) / 2.0
                            self.binance_book.last_update_mono_ns = t_mono
            except Exception as e:
                logger.warning("Binance WS reconnecting: %s", e)
                await asyncio.sleep(2.0)

    async def _hyperliquid_worker(self) -> None:
        """Stream public Hyperliquid l2Book."""
        logger.info("Connecting to public Hyperliquid feed: %s", HYPERLIQUID_WS)

        while self.is_running:
            try:
                async with websockets.connect(HYPERLIQUID_WS, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Hyperliquid stream active (%s).", self.symbol)
                    sub_msg = {
                        "method": "subscribe",
                        "subscription": {"type": "l2Book", "coin": self.symbol}
                    }
                    await ws.send(json.dumps(sub_msg))

                    while self.is_running:
                        msg_raw = await ws.recv()
                        t_mono = time.monotonic_ns()
                        data = json.loads(msg_raw)

                        if data.get("channel") == "l2Book":
                            payload = data.get("data", {})
                            levels = payload.get("levels", [[], []])
                            bids = levels[0] if len(levels) > 0 else []
                            asks = levels[1] if len(levels) > 1 else []

                            if bids and asks:
                                self.hl_book.best_bid = float(bids[0]["px"])
                                self.hl_book.best_bid_sz = float(bids[0]["sz"])
                                self.hl_book.best_ask = float(asks[0]["px"])
                                self.hl_book.best_ask_sz = float(asks[0]["sz"])
                                self.hl_book.mid = (self.hl_book.best_bid + self.hl_book.best_ask) / 2.0
                                self.hl_book.last_update_mono_ns = t_mono
            except Exception as e:
                logger.warning("Hyperliquid WS reconnecting: %s", e)
                await asyncio.sleep(2.0)

    async def run_diagnostic_probe(self, duration_s: float = 30.0) -> Dict[str, Any]:
        """Run real-time probe to observe live book feeds and detect sweeps."""
        if websockets is None:
            logger.error("websockets package required.")
            return {}

        self.is_running = True
        logger.info("=== STARTING %s LEAD-LAG PROBE FOR %.0f SECONDS ===", self.symbol, duration_s)

        tasks = [
            asyncio.create_task(self._binance_worker()),
            asyncio.create_task(self._hyperliquid_worker()),
        ]

        # Wait for data warm-up
        await asyncio.sleep(3.0)

        start_time = time.time()
        while time.time() - start_time < duration_s:
            await asyncio.sleep(1.0)
            if self.binance_book.mid > 0 and self.hl_book.mid > 0:
                spread_diff = self.binance_book.mid - self.hl_book.mid
                diff_bps = (spread_diff / self.hl_book.mid) * 10000.0
                logger.info(
                    "[%s Status] Binance Mid: $%.2f | HL Mid: $%.2f | Basis: %+.1f bps ($%+.2f)",
                    self.symbol,
                    self.binance_book.mid,
                    self.hl_book.mid,
                    diff_bps,
                    spread_diff,
                )

        self.is_running = False
        for t in tasks:
            t.cancel()

        logger.info("=== PROBE COMPLETE: %d Opportunities Detected ===", len(self.opportunities))
        return {
            "symbol": self.symbol,
            "duration_s": duration_s,
            "opportunities_detected": len(self.opportunities),
            "final_binance_mid": self.binance_book.mid,
            "final_hl_mid": self.hl_book.mid,
        }


if __name__ == "__main__":
    detector = OFILeadLagDetector(symbol="BTC", sweep_window_ms=100.0, min_sweep_volume_usd=500_000.0, min_edge_bps=2.0)
    try:
        asyncio.run(detector.run_diagnostic_probe(duration_s=15.0))
    except KeyboardInterrupt:
        detector.is_running = False

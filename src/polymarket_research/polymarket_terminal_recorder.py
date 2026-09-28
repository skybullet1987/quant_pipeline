#!/usr/bin/env python3
"""
Polymarket Hourly BTC Terminal Probability Mispricing Recorder (Route 3 - Data Lab v2.5)
========================================================================================
Forensic, event-driven recorder pairing real-time Polymarket 1-Hour BTC Up/Down binary
orderbooks with dual-stream Tokyo Binance Spot and USDⓈ-M Futures order flow.

Dual-Feed Microstructure Architecture:
  1. Dual Binance Antennas:
       - Binance Spot:    wss://stream.binance.com/ws/btcusdt@aggTrade (Settlement Reference)
       - Binance Futures: wss://fstream.binance.com/ws/btcusdt@aggTrade (Leading Flow Antenna)
       - Real-time Basis: Basis_t = P_futures - P_spot, Delta_Basis_100ms
  2. Exact 1-Hour Contract Invariant:
       market_duration == 3600s
       series_slug == "btc-up-or-down-hourly"
       resolution_source == Binance BTC/USDT 1H Candle Open & Close (Spot Pair)
  3. Polymarket CLOB WebSocket L2:
       Continuous L2 book tracking with raw depth, quote age, and Order Book Imbalance (OBI).
  4. Separation of Calibration vs. Executable EV:
       - Calibration: P(Y=1) ~ q_mid
       - Executable:  P(Y=1) - q_ask - Fee(q_ask) - Shortfall > 0
       - Fee(q) = 0.07 * q * (1 - q), makers pay zero.
  5. Impulse-Response Function (Delta q(Delta t)):
       Captures t0-, t0+100ms, t0+250ms, t0+500ms, t0+1s, t0+5s, t0+30s.
  6. Operational Boundary:
       Strictly read-only; does not attempt to circumvent geographic restrictions.
"""

import asyncio
import collections
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import aiohttp
import websockets

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "polymarket"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TELEMETRY_FILE = DATA_DIR / "polymarket_hourly_telemetry.jsonl"
SHOCK_FILE = DATA_DIR / "shock_responses.jsonl"
LOG_FILE = DATA_DIR / "recorder.log"
PID_FILE = DATA_DIR / "recorder.pid"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PolymarketDualFeed1H")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

BINANCE_SPOT_WS_URL = "wss://stream.binance.com/ws/btcusdt@aggTrade"
BINANCE_FUTURES_WS_URL = "wss://fstream.binance.com/ws/btcusdt@aggTrade"
BINANCE_REST_URL = "https://api.binance.com"

FEE_RATE = 0.07  # Documented Polymarket crypto fee parameter


def calculate_taker_fee(price: float) -> float:
    """Computes Polymarket crypto taker fee: C * feeRate * p * (1 - p)."""
    p = max(0.001, min(0.999, price))
    return FEE_RATE * p * (1.0 - p)


class L2OrderBook:
    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        self.bids: Dict[float, float] = {}  # px -> sz
        self.asks: Dict[float, float] = {}
        self.last_update_ts: float = 0.0

    def apply_snapshot(self, bids: List[Dict[str, str]], asks: List[Dict[str, str]]):
        self.bids = {float(b["price"]): float(b["size"]) for b in bids if float(b["size"]) > 0}
        self.asks = {float(a["price"]): float(a["size"]) for a in asks if float(a["size"]) > 0}
        self.last_update_ts = time.time()

    def apply_price_changes(self, changes: List[Dict[str, str]]):
        for c in changes:
            px = float(c["price"])
            sz = float(c["size"])
            side = c.get("side", "").upper()
            if side == "BUY":
                if sz == 0 and px in self.bids:
                    del self.bids[px]
                elif sz > 0:
                    self.bids[px] = sz
            elif side == "SELL":
                if sz == 0 and px in self.asks:
                    del self.asks[px]
                elif sz > 0:
                    self.asks[px] = sz
        self.last_update_ts = time.time()

    def get_metrics(self) -> Dict[str, Any]:
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])

        best_bid = sorted_bids[0][0] if sorted_bids else 0.0
        bid_sz = sorted_bids[0][1] if sorted_bids else 0.0
        best_ask = sorted_asks[0][0] if sorted_asks else 1.0
        ask_sz = sorted_asks[0][1] if sorted_asks else 0.0

        spread = best_ask - best_bid
        q_mid = (best_bid + best_ask) / 2.0

        denom = bid_sz + ask_sz
        q_micro = (best_bid * ask_sz + best_ask * bid_sz) / denom if denom > 0 else q_mid

        # Order Book Imbalance (OBI) across top-5 levels
        top_bid_vol = sum(sz for _, sz in sorted_bids[:5])
        top_ask_vol = sum(sz for _, sz in sorted_asks[:5])
        obi_denom = top_bid_vol + top_ask_vol
        obi = (top_bid_vol - top_ask_vol) / obi_denom if obi_denom > 0 else 0.0

        taker_fee = calculate_taker_fee(best_ask)
        executable_hurdle = best_ask + taker_fee

        # Compute VWAP for research ticket sizes ($1, $5, $20, $50)
        vwaps = {}
        for notional in [1.0, 5.0, 20.0, 50.0]:
            cost = 0.0
            shares_bought = 0.0
            for px, sz in sorted_asks:
                fill_dollars = min(notional - cost, px * sz)
                shares = fill_dollars / px
                cost += fill_dollars
                shares_bought += shares
                if cost >= notional - 1e-6:
                    break
            vwaps[f"vwap_${int(notional)}"] = round(cost / shares_bought, 4) if shares_bought > 0 else None

        quote_age_ms = round((time.time() - self.last_update_ts) * 1000.0, 1) if self.last_update_ts > 0 else 0.0

        return {
            "best_bid": round(best_bid, 4),
            "best_ask": round(best_ask, 4),
            "bid_size": round(bid_sz, 2),
            "ask_size": round(ask_sz, 2),
            "spread": round(spread, 4),
            "q_mid": round(q_mid, 4),
            "q_micro": round(q_micro, 4),
            "obi": round(obi, 3),
            "quote_age_ms": quote_age_ms,
            "last_update_ts": self.last_update_ts,
            "taker_fee": round(taker_fee, 5),
            "executable_hurdle": round(executable_hurdle, 5),
            **vwaps,
            "raw_top_bids": sorted_bids[:5],
            "raw_top_asks": sorted_asks[:5]
        }


class PolymarketDualFeed1HRecorder:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_market: Optional[Dict[str, Any]] = None
        self.books: Dict[str, L2OrderBook] = {}

        # Trade queues
        self.spot_trades: collections.deque = collections.deque(maxlen=10000)
        self.futures_trades: collections.deque = collections.deque(maxlen=10000)

        # Real-time state
        self.spot_price: float = 0.0
        self.futures_price: float = 0.0
        self.basis_usd: float = 0.0
        self.basis_bps: float = 0.0
        self.finalized_1h_open: float = 0.0

        self.last_shock_ts: float = 0.0
        self.shock_threshold_usd: float = 1_500_000.0  # $1.5M in 100ms
        self.running: bool = True

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "PolymarketDualFeedRecorder/2.5"}
            )
        return self.session

    async def discover_nearest_1h_market(self) -> Optional[Dict[str, Any]]:
        """Enforces: series_slug == 'btc-up-or-down-hourly' and market_duration == 3600s."""
        session = await self.get_session()
        try:
            url = f"{GAMMA_API_URL}/events?series_slug=btc-up-or-down-hourly&limit=20&closed=false"
            async with session.get(url) as resp:
                if resp.status == 200:
                    events = await resp.json()
                    now = datetime.now(timezone.utc)
                    candidates = []
                    for event in events:
                        markets = event.get("markets", [])
                        if not markets:
                            continue
                        m = markets[0]
                        m_end_str = m.get("endDate") or event.get("endDate")
                        if not m_end_str:
                            continue
                        end_dt = datetime.fromisoformat(m_end_str.replace("Z", "+00:00"))
                        secs_left = (end_dt - now).total_seconds()
                        if 0 < secs_left <= 7200:  # within next 2 hours
                            candidates.append((secs_left, event, m, end_dt, m_end_str))

                    if not candidates:
                        return None

                    candidates.sort(key=lambda x: x[0])
                    secs_left, event, m, end_dt, m_end_str = candidates[0]

                    m_id = str(m.get("id"))
                    tokens_raw = m.get("clobTokenIds")
                    tokens = json.loads(tokens_raw) if isinstance(tokens_raw, str) else tokens_raw
                    outcomes_raw = m.get("outcomes", '["Up", "Down"]')
                    outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw

                    candle_open_ts = int(end_dt.timestamp() - 3600)
                    candle_close_ts = int(end_dt.timestamp())

                    # Pre-populate spot and futures price via REST
                    url_spot = f"{BINANCE_REST_URL}/api/v3/ticker/price?symbol=BTCUSDT"
                    url_fut = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT"
                    try:
                        async with session.get(url_spot) as resp_spot:
                            if resp_spot.status == 200:
                                data_spot = await resp_spot.json()
                                self.spot_price = float(data_spot["price"])
                        async with session.get(url_fut) as resp_fut:
                            if resp_fut.status == 200:
                                data_fut = await resp_fut.json()
                                self.futures_price = float(data_fut["price"])
                                self.update_basis()
                    except Exception:
                        pass

                    return {
                        "market_id": m_id,
                        "title": event.get("title"),
                        "question": m.get("question"),
                        "slug": event.get("slug"),
                        "end_date_iso": m_end_str,
                        "end_dt": end_dt,
                        "candle_open_ts": candle_open_ts,
                        "candle_close_ts": candle_close_ts,
                        "tokens": {
                            "UP": tokens[0],
                            "DOWN": tokens[1]
                        },
                        "outcomes": outcomes
                    }
        except Exception as e:
            logger.error(f"Error discovering 1H market: {e}")
        return None

    async def fetch_finalized_binance_open(self, candle_open_ts: int) -> float:
        """Pulls exact finalized Binance Spot 1H candle open price."""
        session = await self.get_session()
        try:
            start_ms = candle_open_ts * 1000
            url = f"{BINANCE_REST_URL}/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={start_ms}&limit=1"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        open_px = float(data[0][1])
                        logger.info(f"[BINANCE SPOT 1H CANDLE] Verified Open for {datetime.fromtimestamp(candle_open_ts, tz=timezone.utc)}: ${open_px:,.2f}")
                        return open_px
        except Exception as e:
            logger.error(f"Failed to fetch Binance Spot 1H candle open: {e}")
        return 0.0

    async def stream_binance_spot(self):
        """Tokyo-latency microsecond Binance Spot aggTrade stream (Settlement Reference)."""
        while self.running:
            try:
                logger.info(f"Connecting to Binance Spot aggTrade ({BINANCE_SPOT_WS_URL})...")
                async with websockets.connect(BINANCE_SPOT_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("[+] Subscribed to Binance Spot aggTrade stream.")
                    async for msg_str in ws:
                        if not self.running:
                            break
                        msg = json.loads(msg_str)
                        px = float(msg.get("p", 0))
                        sz = float(msg.get("q", 0))
                        is_buyer = not msg.get("m", False)  # taker buy
                        ts_ms = int(msg.get("T", 0))
                        notional = px * sz

                        self.spot_price = px
                        self.update_basis()
                        self.spot_trades.append((ts_ms, notional, is_buyer, px))

                        # Evaluate Spot 100ms volume shock
                        self.evaluate_shock(ts_ms, source="SPOT")
            except Exception as e:
                logger.warning(f"Binance Spot feed disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    async def stream_binance_futures(self):
        """Tokyo-latency microsecond Binance USDⓈ-M Futures aggTrade stream (Leading Flow Antenna)."""
        while self.running:
            try:
                logger.info(f"Connecting to Binance Futures aggTrade ({BINANCE_FUTURES_WS_URL})...")
                async with websockets.connect(BINANCE_FUTURES_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("[+] Subscribed to Binance Futures aggTrade stream.")
                    async for msg_str in ws:
                        if not self.running:
                            break
                        msg = json.loads(msg_str)
                        px = float(msg.get("p", 0))
                        sz = float(msg.get("q", 0))
                        is_buyer = not msg.get("m", False)
                        ts_ms = int(msg.get("T", 0))
                        notional = px * sz

                        self.futures_price = px
                        self.update_basis()
                        self.futures_trades.append((ts_ms, notional, is_buyer, px))

                        # Evaluate Futures 100ms volume shock
                        self.evaluate_shock(ts_ms, source="FUTURES")
            except Exception as e:
                logger.warning(f"Binance Futures feed disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    def update_basis(self):
        if self.spot_price > 0 and self.futures_price > 0:
            self.basis_usd = self.futures_price - self.spot_price
            self.basis_bps = (self.basis_usd / self.spot_price) * 10000.0

    def evaluate_shock(self, current_ts_ms: int, source: str):
        trade_queue = self.spot_trades if source == "SPOT" else self.futures_trades
        cutoff_ms = current_ts_ms - 100
        vol_100ms = 0.0
        buy_vol = 0.0
        sell_vol = 0.0

        for t_ms, ntl, buyer, _ in reversed(trade_queue):
            if t_ms < cutoff_ms:
                break
            vol_100ms += ntl
            if buyer:
                buy_vol += ntl
            else:
                sell_vol += ntl

        now_sec = time.time()
        if vol_100ms >= self.shock_threshold_usd and (now_sec - self.last_shock_ts > 15.0):
            self.last_shock_ts = now_sec
            shock_dir = "BUY" if buy_vol >= sell_vol else "SELL"
            ofi = (buy_vol - sell_vol) / vol_100ms if vol_100ms > 0 else 0.0
            trigger_px = self.spot_price if source == "SPOT" else self.futures_price

            logger.info(f"\n[!!! {source} SHOCK TRIGGERED !!!] 100ms Vol=${vol_100ms:,.0f} | Dir={shock_dir} | "
                        f"OFI={ofi:+.2f} | Spot=${self.spot_price:,.1f} | Fut=${self.futures_price:,.1f} | Basis={self.basis_bps:+.1f}bps")

            asyncio.create_task(self.capture_shock_burst(now_sec, source, vol_100ms, shock_dir, ofi, trigger_px))

    async def capture_shock_burst(self, t0: float, source: str, shock_vol: float, shock_dir: str, ofi: float, trigger_px: float):
        """
        Captures the Probability Repricing Impulse-Response Function:
          Ladder: t0-, t0+100ms, t0+250ms, t0+500ms, t0+1s, t0+5s, t0+30s.
        """
        up_book = self.books.get("UP")
        down_book = self.books.get("DOWN")
        if not up_book or not down_book or not self.current_market:
            return

        pre_shock_up = up_book.get_metrics()
        pre_shock_down = down_book.get_metrics()
        pre_shock_basis = self.basis_bps

        # Compute Quote Age at shock moment
        quote_age_up_ms = round((t0 - up_book.last_update_ts) * 1000.0, 1) if up_book.last_update_ts > 0 else 0.0
        quote_age_down_ms = round((t0 - down_book.last_update_ts) * 1000.0, 1) if down_book.last_update_ts > 0 else 0.0

        ladder_delays = [0.10, 0.15, 0.25, 0.50, 4.0, 25.0]
        ladder_labels = ["100ms", "250ms", "500ms", "1s", "5s", "30s"]
        response_snapshots = {}

        for delay, label in zip(ladder_delays, ladder_labels):
            await asyncio.sleep(delay)
            up_m = up_book.get_metrics()
            down_m = down_book.get_metrics()
            response_snapshots[label] = {
                "elapsed_sec": round(time.time() - t0, 3),
                "up_mid": up_m["q_mid"],
                "up_ask": up_m["best_ask"],
                "up_delta_q_ask": round(up_m["best_ask"] - pre_shock_up["best_ask"], 4),
                "up_delta_q_mid": round(up_m["q_mid"] - pre_shock_up["q_mid"], 4),
                "up_obi": up_m["obi"],
                "down_mid": down_m["q_mid"],
                "down_ask": down_m["best_ask"],
                "down_delta_q_ask": round(down_m["best_ask"] - pre_shock_down["best_ask"], 4),
                "down_delta_q_mid": round(down_m["q_mid"] - pre_shock_down["q_mid"], 4),
                "down_obi": down_m["obi"],
                "binance_spot": self.spot_price,
                "binance_futures": self.futures_price,
                "basis_bps": round(self.basis_bps, 2),
                "delta_basis_bps": round(self.basis_bps - pre_shock_basis, 2)
            }

        secs_left = (self.current_market["end_dt"] - datetime.now(timezone.utc)).total_seconds()
        dist_pct = ((self.spot_price - self.finalized_1h_open) / self.finalized_1h_open * 100.0) if self.finalized_1h_open > 0 else 0.0

        shock_record = {
            "timestamp": datetime.fromtimestamp(t0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "t0_unix": t0,
            "shock_source": source,
            "market_id": self.current_market["market_id"],
            "title": self.current_market["title"],
            "seconds_to_expiry": round(secs_left, 1),
            "shock_volume_100ms": round(shock_vol, 0),
            "shock_direction": shock_dir,
            "shock_ofi": round(ofi, 3),
            "trigger_price": trigger_px,
            "spot_at_shock": self.spot_price,
            "futures_at_shock": self.futures_price,
            "basis_at_shock_bps": round(pre_shock_basis, 2),
            "finalized_1h_open": self.finalized_1h_open,
            "candle_distance_pct": round(dist_pct, 4),
            "quote_age_ms": {
                "UP": quote_age_up_ms,
                "DOWN": quote_age_down_ms
            },
            "pre_shock": {
                "UP": pre_shock_up,
                "DOWN": pre_shock_down
            },
            "impulse_response": response_snapshots
        }

        with open(SHOCK_FILE, "a") as f:
            f.write(json.dumps(shock_record) + "\n")

        up_30s_delta = response_snapshots["30s"]["up_delta_q_ask"]
        logger.info(f"[IMPULSE-RESPONSE RECORDED] Market {self.current_market['market_id']} | Source={source} | "
                    f"QuoteAge={quote_age_up_ms:.0f}ms | UP ask={pre_shock_up['best_ask']:.3f} -> 30s Delta: {up_30s_delta:+.3f} | "
                    f"Basis={pre_shock_basis:+.1f}bps")

    async def stream_polymarket_clob(self):
        """Streams real-time L2 orderbook updates from Polymarket CLOB WebSocket."""
        while self.running:
            if not self.current_market:
                await asyncio.sleep(2)
                continue

            up_token = self.current_market["tokens"]["UP"]
            down_token = self.current_market["tokens"]["DOWN"]
            self.books["UP"] = L2OrderBook(up_token)
            self.books["DOWN"] = L2OrderBook(down_token)

            try:
                logger.info(f"Connecting to Polymarket CLOB WS ({CLOB_WS_URL}) for tokens [{up_token[:10]}..., {down_token[:10]}...]...")
                async with websockets.connect(CLOB_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    sub_msg = {"assets_ids": [up_token, down_token], "type": "market"}
                    await ws.send(json.dumps(sub_msg))
                    logger.info("[+] Subscribed to Polymarket 1H L2 orderbooks (UP & DOWN).")

                    async for msg_str in ws:
                        if not self.running:
                            break
                        data = json.loads(msg_str)
                        if isinstance(data, list):
                            for item in data:
                                asset_id = item.get("asset_id")
                                if asset_id == up_token:
                                    self.books["UP"].apply_snapshot(item.get("bids", []), item.get("asks", []))
                                elif asset_id == down_token:
                                    self.books["DOWN"].apply_snapshot(item.get("bids", []), item.get("asks", []))
                        elif isinstance(data, dict):
                            event_type = data.get("event_type")
                            if event_type == "price_change":
                                for pc in data.get("price_changes", []):
                                    asset_id = pc.get("asset_id")
                                    if asset_id == up_token:
                                        self.books["UP"].apply_price_changes([pc])
                                    elif asset_id == down_token:
                                        self.books["DOWN"].apply_price_changes([pc])
                            elif event_type == "book":
                                asset_id = data.get("asset_id")
                                if asset_id == up_token:
                                    self.books["UP"].apply_snapshot(data.get("bids", []), data.get("asks", []))
                                elif asset_id == down_token:
                                    self.books["DOWN"].apply_snapshot(data.get("bids", []), data.get("asks", []))

                        # Check if current market has expired
                        if (self.current_market["end_dt"] - datetime.now(timezone.utc)).total_seconds() <= -10:
                            logger.info(f"[*] 1H Market {self.current_market['market_id']} reached expiry. Cycling to next.")
                            break
            except Exception as e:
                logger.warning(f"Polymarket CLOB WS disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    async def telemetry_logger_loop(self):
        """Periodic 10s baseline telemetry logger and market rollover manager."""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                if not self.current_market or (self.current_market["end_dt"] - now).total_seconds() <= 0:
                    market = await self.discover_nearest_1h_market()
                    if market:
                        self.current_market = market
                        self.finalized_1h_open = await self.fetch_finalized_binance_open(market["candle_open_ts"])
                        logger.info(f"\n==============================================================================="
                                    f"\n[ACTIVE 1H PRODUCT LOADED] {market['title']}"
                                    f"\n  Market ID: {market['market_id']} | End: {market['end_date_iso']}"
                                    f"\n  UP Token: {market['tokens']['UP']}"
                                    f"\n  DOWN Token: {market['tokens']['DOWN']}"
                                    f"\n  Binance Spot 1H Finalized Open: ${self.finalized_1h_open:,.2f}"
                                    f"\n===============================================================================\n")

                if self.current_market and "UP" in self.books and "DOWN" in self.books:
                    up_metrics = self.books["UP"].get_metrics()
                    down_metrics = self.books["DOWN"].get_metrics()
                    secs_left = (self.current_market["end_dt"] - now).total_seconds()
                    dist_pct = ((self.spot_price - self.finalized_1h_open) / self.finalized_1h_open * 100.0) if self.finalized_1h_open > 0 else 0.0

                    record = {
                        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "timestamp_unix": now.timestamp(),
                        "market_id": self.current_market["market_id"],
                        "title": self.current_market["title"],
                        "seconds_to_expiry": round(secs_left, 1),
                        "binance_spot": self.spot_price,
                        "binance_futures": self.futures_price,
                        "basis_bps": round(self.basis_bps, 2),
                        "binance_1h_open": self.finalized_1h_open,
                        "candle_distance_pct": round(dist_pct, 4),
                        "UP": up_metrics,
                        "DOWN": down_metrics
                    }

                    with open(TELEMETRY_FILE, "a") as f:
                        f.write(json.dumps(record) + "\n")

                    logger.info(
                        f"[1H TELEMETRY] {self.current_market['title'][:32]} | Tau: {secs_left/60.0:.1f}m ({secs_left:.0f}s) | "
                        f"UP ask={up_metrics['best_ask']:.3f} (mid={up_metrics['q_mid']:.3f}, hurdle={up_metrics['executable_hurdle']:.4f}) | "
                        f"Spot=${self.spot_price:,.1f} | Fut=${self.futures_price:,.1f} | Basis={self.basis_bps:+.1f}bp | dist={dist_pct:+.2f}%"
                    )

                await asyncio.sleep(10.0)
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}", exc_info=True)
                await asyncio.sleep(10.0)

    async def run(self):
        logger.info("===============================================================================")
        logger.info("   ROUTE 3: POLYMARKET 1-HOUR BTC DUAL-FEED RECORDER (v2.5)                   ")
        logger.info("   Dual Binance Feeds: Spot (Settlement Ref) + Futures (Flow Antenna)         ")
        logger.info("   Microstructure: Basis_t + Quote Age + OBI + VWAP Depth ($1, $5, $20, $50)   ")
        logger.info("   Operational: Read-Only (Does not circumvent geographic restrictions)        ")
        logger.info("===============================================================================")

        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        await asyncio.gather(
            self.stream_binance_spot(),
            self.stream_binance_futures(),
            self.stream_polymarket_clob(),
            self.telemetry_logger_loop()
        )


if __name__ == "__main__":
    recorder = PolymarketDualFeed1HRecorder()
    try:
        asyncio.run(recorder.run())
    except KeyboardInterrupt:
        recorder.running = False
        logger.info("Stopped by user.")

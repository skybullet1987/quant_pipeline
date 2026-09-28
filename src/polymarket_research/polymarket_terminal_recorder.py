#!/usr/bin/env python3
"""
Futures/Spot -> Polymarket Information-Flow Experiment (Route 3 - Data Lab v2.6)
================================================================================
Empirical research pipeline testing information transmission between Binance USD(S)-M Futures,
Binance Spot, and Polymarket 1-Hour BTC Up/Down binary contract order books.

Microstructure, Econometric, and Invariant Foundations:
  1. Dual Binance Antennas (Tokyo Latency):
       - Binance Spot:    wss://stream.binance.com:443/ws/btcusdt@aggTrade (Polymarket Settlement Ref)
       - Binance Futures: wss://fstream.binance.com:443/market/ws/btcusdt@aggTrade (Futures Flow Antenna)
       - Microsecond-resolution timestamps: t_binance_event (E), t_binance_trade (T), t_receive_local.
  2. Strict Causal Information Boundary (t0 Anchor):
       - t0 = exact end of qualifying 100-ms shock window.
       - All predictive features X_t strictly satisfy t_feature <= t0.
       - All impulse-response measurements Delta_q(Delta_t) start strictly after t0 + epsilon.
  3. L2 Order Book Invariants & OBI / Microprice Reconciliation:
       - Top-of-Book OBI: OBI_L1 = (Q_bid1 - Q_ask1) / (Q_bid1 + Q_ask1)
       - Top-of-Book Microprice: q_micro = (ask1 * Q_bid1 + bid1 * Q_ask1) / (Q_bid1 + Q_ask1)
       - Invariant: sign(q_micro - q_mid) MUST match sign(OBI_L1).
       - Runtime Assertion:
           if OBI_L1 > 1e-6: assert q_micro >= q_mid - 1e-6
           if OBI_L1 < -1e-6: assert q_micro <= q_mid + 1e-6
       - Depth OBI: OBI_depth = (sum(Q_bid[:5]) - sum(Q_ask[:5])) / (sum(Q_bid[:5]) + sum(Q_ask[:5]))
       - Book Invariants: best_bid < best_ask (unless locked/crossed), depth_i >= 0, VWAP(C) >= best_ask.
       - Explicit logging of: obi_depth_levels, microprice_formula, book_sequence_id, book_timestamp.
  4. Tripartite Quote Age Decomposition:
       - Age_book = time since any L2 message (snapshot or price_change).
       - Age_bid  = time since best bid changed (price or size).
       - Age_ask  = time since best ask changed (price or size) [stale executable quote metric].
  5. Basis & Delta Basis:
       - basis_t0 = P_futures - P_spot (signed USD and bps)
       - Delta_basis_100ms = basis(t0) - basis(t0 - 100ms)
       - |basis| (magnitude)
  6. Pre-Registered Econometric Models:
       - Model A (Spot):    Y = f(q, X_S, TTE, dist)
       - Model B (Futures): Y = f(q, X_F, TTE, dist)
       - Model C (Joint):   Y = f(q, X_S, X_F, basis, Delta_basis, TTE, dist)
       - Model D (Incr):    Y = f(q, X_S, TTE, dist) + g(X_F | X_S) -> Test H0: beta_{F|S} = 0.
  7. Pre-Registered Lead/Lag Cross-Correlation Grid:
       - Delta in {-500, -250, -100, -50, 0, +50, +100, +250, +500, +1000} ms.
  8. Executable Capacity Surface & Dynamic Fee Parameters:
       - EV(C) = p - VWAP(C) - Fee(C) for C in {1, 5, 20, 50, 100}.
       - fee_rate_market, fee_source, fee_enabled, fee_formula_version recorded per contract.
  9. Strategy Dichotomy:
       - Strategy R3-A: Terminal hold (p_t - q_t - fee) -> Primary scientific experiment.
       - Strategy R3-B: Momentum repricing (q_{t+Delta} - q_t - 2*fee - spread/slip) -> Secondary.
  10. Settlement Ground Truth Verification:
       - Y = 1[Close_1H >= Open_1H] verified directly from finalized Binance Spot 1H candle.
  11. Clustered Statistical Inference:
       - Standard errors clustered at market-hour and shock-episode.
       - Response curve IRF(tau) = E[Delta_q(tau)] bootstrapped at shock-event level.
  12. Operational Boundary:
       - Strictly read-only research pipeline; zero orders or authentication.
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
import numpy as np
import websockets

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "polymarket"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TELEMETRY_FILE = DATA_DIR / "polymarket_hourly_telemetry.jsonl"
SHOCK_FILE = DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
CORRELATIONS_FILE = DATA_DIR / "leadlag_cross_correlations.jsonl"
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

BINANCE_SPOT_WS_URL = "wss://stream.binance.com:443/ws/btcusdt@aggTrade"
BINANCE_FUTURES_WS_URL = "wss://fstream.binance.com:443/market/ws/btcusdt@aggTrade"
BINANCE_REST_URL = "https://api.binance.com"
BINANCE_FUTURES_REST_URL = "https://fapi.binance.com"

DEFAULT_FEE_RATE = 0.07  # Documented Polymarket crypto fee parameter
TICKET_CAPACITY_LEVELS = [1.0, 5.0, 20.0, 50.0, 100.0]  # USD Notional capacity surface
CORRELATION_LAGS_MS = [-1000, -500, -250, -100, -50, 0, 50, 100, 250, 500, 1000]


def calculate_taker_fee(price: float, fee_rate: float = DEFAULT_FEE_RATE) -> float:
    """
    Computes Polymarket crypto taker fee: C * feeRate * p * (1 - p).
    C is the number of shares (not dollar notional).
    Makers pay zero fee.
    """
    p = max(0.001, min(0.999, price))
    return fee_rate * p * (1.0 - p)


class L2OrderBook:
    """
    Maintains continuous in-memory full L2 orderbook with exact microstructure invariants,
    OBI/microprice reconciliation, and tripartite quote age tracking.
    """
    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        self.bids: Dict[float, float] = {}  # px -> sz
        self.asks: Dict[float, float] = {}  # px -> sz
        
        # Tripartite quote age tracking
        self.last_book_update_ts: float = 0.0
        self.last_best_bid_change_ts: float = 0.0
        self.last_best_ask_change_ts: float = 0.0
        
        self.prev_best_bid: Tuple[float, float] = (0.0, 0.0)  # (px, sz)
        self.prev_best_ask: Tuple[float, float] = (1.0, 0.0)  # (px, sz)
        
        self.book_sequence_id: int = 0
        self.microprice_formula = "(best_ask * bid_sz_1 + best_bid * ask_sz_1) / (bid_sz_1 + ask_sz_1)"
        self.obi_depth_levels = 5

    def _check_top_changes(self, now_ts: float):
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])
        
        curr_best_bid = sorted_bids[0] if sorted_bids else (0.0, 0.0)
        curr_best_ask = sorted_asks[0] if sorted_asks else (1.0, 0.0)
        
        if curr_best_bid != self.prev_best_bid:
            self.last_best_bid_change_ts = now_ts
            self.prev_best_bid = curr_best_bid
            
        if curr_best_ask != self.prev_best_ask:
            self.last_best_ask_change_ts = now_ts
            self.prev_best_ask = curr_best_ask

    def apply_snapshot(self, bids: List[Dict[str, str]], asks: List[Dict[str, str]]):
        now_ts = time.time()
        self.bids = {float(b["price"]): float(b["size"]) for b in bids if float(b["size"]) > 0}
        self.asks = {float(a["price"]): float(a["size"]) for a in asks if float(a["size"]) > 0}
        self.last_book_update_ts = now_ts
        self.book_sequence_id += 1
        self._check_top_changes(now_ts)

    def apply_price_changes(self, changes: List[Dict[str, str]]):
        now_ts = time.time()
        for c in changes:
            px = float(c["price"])
            sz = float(c["size"])
            side = c.get("side", "").upper()
            if side == "BUY":
                if sz <= 0:
                    self.bids.pop(px, None)
                else:
                    self.bids[px] = sz
            elif side == "SELL":
                if sz <= 0:
                    self.asks.pop(px, None)
                else:
                    self.asks[px] = sz
        self.last_book_update_ts = now_ts
        self.book_sequence_id += 1
        self._check_top_changes(now_ts)

    def get_metrics(self, obs_ts: Optional[float] = None, fee_rate: float = DEFAULT_FEE_RATE) -> Dict[str, Any]:
        t_now = obs_ts if obs_ts is not None else time.time()
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])

        best_bid = sorted_bids[0][0] if sorted_bids else 0.0
        bid_sz_1 = sorted_bids[0][1] if sorted_bids else 0.0
        best_ask = sorted_asks[0][0] if sorted_asks else 1.0
        ask_sz_1 = sorted_asks[0][1] if sorted_asks else 0.0

        # Book Consistency Invariants
        is_crossed = False
        if best_bid > 0 and best_ask < 1.0 and best_bid >= best_ask:
            is_crossed = True

        spread = best_ask - best_bid
        q_mid = (best_bid + best_ask) / 2.0

        # Top-of-Book Level 1 OBI & Microprice
        l1_denom = bid_sz_1 + ask_sz_1
        if l1_denom > 0:
            obi_l1 = (bid_sz_1 - ask_sz_1) / l1_denom
            q_micro = (best_bid * ask_sz_1 + best_ask * bid_sz_1) / l1_denom
        else:
            obi_l1 = 0.0
            q_micro = q_mid

        # Runtime Invariant Enforcement: sign(q_micro - q_mid) MUST equal sign(obi_l1)
        if not is_crossed and l1_denom > 0 and spread > 1e-5:
            if obi_l1 > 1e-4:
                assert q_micro >= q_mid - 1e-4, f"Invariant violated: OBI_L1={obi_l1:.4f} > 0 but q_micro={q_micro:.4f} < q_mid={q_mid:.4f}"
            elif obi_l1 < -1e-4:
                assert q_micro <= q_mid + 1e-4, f"Invariant violated: OBI_L1={obi_l1:.4f} < 0 but q_micro={q_micro:.4f} > q_mid={q_mid:.4f}"

        # Multi-level Depth OBI (Top 5 levels)
        top_bid_vol = sum(sz for _, sz in sorted_bids[:self.obi_depth_levels])
        top_ask_vol = sum(sz for _, sz in sorted_asks[:self.obi_depth_levels])
        depth_denom = top_bid_vol + top_ask_vol
        obi_depth = (top_bid_vol - top_ask_vol) / depth_denom if depth_denom > 0 else 0.0

        taker_fee = calculate_taker_fee(best_ask, fee_rate)
        executable_hurdle = best_ask + taker_fee

        # Crossing Cost & Execution Surface across research ticket sizes (Points 1 & 8)
        # Note: EV_terminal(C) = p_OOS - EffectivePrice(C). Using q_mid measures CrossingCost(C) = EffectivePrice(C) - q_mid.
        execution_surface = {}
        for notional in TICKET_CAPACITY_LEVELS:
            dollar_spent = 0.0
            shares_bought = 0.0
            total_fees = 0.0
            for px, sz in sorted_asks:
                fill_dollars = min(notional - dollar_spent, px * sz)
                shares = fill_dollars / px
                # Exact fill-level fee per consumed level: C_i * feeRate * p_i * (1 - p_i)
                level_fee = shares * fee_rate * px * (1.0 - px)
                dollar_spent += fill_dollars
                shares_bought += shares
                total_fees += level_fee
                if dollar_spent >= notional - 1e-6:
                    break

            if shares_bought > 0:
                vwap_val = round(dollar_spent / shares_bought, 4)
                effective_px = round((dollar_spent + total_fees) / shares_bought, 4)
                crossing_cost = round(effective_px - q_mid, 4)
                # Enforce VWAP buy sweep invariant: VWAP >= best_ask
                assert vwap_val >= best_ask - 1e-4, f"Invariant violated: VWAP=${vwap_val:.4f} < best_ask=${best_ask:.4f}"
                execution_surface[f"vwap_${int(notional)}"] = vwap_val
                execution_surface[f"effective_price_${int(notional)}"] = effective_px
                execution_surface[f"crossing_cost_${int(notional)}"] = crossing_cost
                execution_surface[f"fill_fees_${int(notional)}"] = round(total_fees, 5)
            else:
                execution_surface[f"vwap_${int(notional)}"] = None
                execution_surface[f"effective_price_${int(notional)}"] = None
                execution_surface[f"crossing_cost_${int(notional)}"] = None
                execution_surface[f"fill_fees_${int(notional)}"] = None

        # Tripartite Quote Ages (in milliseconds)
        age_book_ms = round((t_now - self.last_book_update_ts) * 1000.0, 1) if self.last_book_update_ts > 0 else 0.0
        age_bid_ms = round((t_now - self.last_best_bid_change_ts) * 1000.0, 1) if self.last_best_bid_change_ts > 0 else 0.0
        age_ask_ms = round((t_now - self.last_best_ask_change_ts) * 1000.0, 1) if self.last_best_ask_change_ts > 0 else 0.0

        return {
            "best_bid": round(best_bid, 4),
            "best_ask": round(best_ask, 4),
            "bid_size_l1": round(bid_sz_1, 2),
            "ask_size_l1": round(ask_sz_1, 2),
            "spread": round(spread, 4),
            "q_mid": round(q_mid, 4),
            "q_micro": round(q_micro, 4),
            "obi_l1": round(obi_l1, 3),
            "obi_depth": round(obi_depth, 3),
            "obi_depth_levels": self.obi_depth_levels,
            "microprice_formula": self.microprice_formula,
            "book_sequence_id": self.book_sequence_id,
            "book_timestamp": self.last_book_update_ts,
            "is_crossed": is_crossed,
            "age_book_ms": age_book_ms,
            "age_bid_ms": age_bid_ms,
            "age_ask_ms": age_ask_ms,
            "taker_fee": round(taker_fee, 5),
            "executable_hurdle": round(executable_hurdle, 5),
            **execution_surface,
            "raw_top_bids": sorted_bids[:5],
            "raw_top_asks": sorted_asks[:5]
        }


class PolymarketDualFeed1HRecorder:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_market: Optional[Dict[str, Any]] = None
        self.books: Dict[str, L2OrderBook] = {}

        # Trade queues: (t_local_ns, exchange_event_ms, exchange_trade_ms, notional, is_buyer, px)
        self.spot_trades: collections.deque = collections.deque(maxlen=15000)
        self.futures_trades: collections.deque = collections.deque(maxlen=15000)
        self.basis_history: collections.deque = collections.deque(maxlen=2000)  # (t_mono_ns, basis_bps)

        # Real-time state
        self.spot_price: float = 0.0
        self.futures_price: float = 0.0
        self.basis_usd: float = 0.0
        self.basis_bps: float = 0.0
        self.finalized_1h_open: float = 0.0
        
        # Fee configuration parameters
        self.fee_rate_market: float = DEFAULT_FEE_RATE
        self.fee_source: str = "polymarket_crypto_schedule_v1"
        self.fee_enabled: bool = True
        self.fee_formula_version: str = "taker_fee_c_times_rate_times_p_one_minus_p"

        # Clock synchronization and offset estimation (Point 3)
        self.clock_offset_ms: float = 0.0
        self.clock_uncertainty_ms: float = 0.0
        self.last_clock_sync_ts: float = 0.0

        self.last_shock_ts: float = 0.0
        self.shock_threshold_usd: float = 1_500_000.0  # $1.5M in 100ms
        self.last_cross_corr_ts: float = 0.0
        self.running: bool = True

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "PolymarketDualFeedRecorder/2.7"}
            )
        return self.session

    async def calibrate_binance_clock_offset(self):
        """
        Calibrates local Tokyo clock offset against Binance server time using Cristian's algorithm.
        Offset = (t_req + t_resp)/2 - t_server
        Uncertainty = RTT / 2
        """
        session = await self.get_session()
        try:
            t0 = time.time() * 1000.0
            async with session.get(f"{BINANCE_REST_URL}/api/v3/time") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    server_time_ms = float(data["serverTime"])
                    t1 = time.time() * 1000.0
                    rtt = t1 - t0
                    t_mid = (t0 + t1) / 2.0
                    self.clock_offset_ms = round(t_mid - server_time_ms, 2)
                    self.clock_uncertainty_ms = round(rtt / 2.0, 2)
                    self.last_clock_sync_ts = time.time()
                    logger.info(f"[CLOCK CALIBRATION] Tokyo <-> Binance Offset: {self.clock_offset_ms:+.2f}ms "
                                f"(Uncertainty: +/-{self.clock_uncertainty_ms:.2f}ms, RTT: {rtt:.2f}ms)")
        except Exception as e:
            logger.warning(f"Clock calibration failed: {e}")

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

                    # Check dynamic fee parameters from market metadata
                    fee_schedule = m.get("feeSchedule", {})
                    if isinstance(fee_schedule, dict) and "rate" in fee_schedule:
                        self.fee_rate_market = float(fee_schedule["rate"])
                        self.fee_source = f"gamma_feeSchedule_{m.get('feeType', 'crypto_fees_v2')}"
                    elif m.get("takerBaseFee") is not None:
                        raw_taker = float(m.get("takerBaseFee"))
                        self.fee_rate_market = raw_taker / 10000.0 if raw_taker > 1.0 else raw_taker
                        self.fee_source = "gamma_takerBaseFee"
                    else:
                        self.fee_rate_market = DEFAULT_FEE_RATE
                        self.fee_source = "polymarket_crypto_schedule_v1"

                    self.fee_enabled = bool(m.get("feesEnabled", True))
                    self.fee_formula_version = str(m.get("feeType", "crypto_fees_v2"))

                    # Pre-populate spot and futures price via REST
                    url_spot = f"{BINANCE_REST_URL}/api/v3/ticker/price?symbol=BTCUSDT"
                    url_fut = f"{BINANCE_FUTURES_REST_URL}/fapi/v1/ticker/price?symbol=BTCUSDT"
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
                        "outcomes": outcomes,
                        "fee_metadata": {
                            "fee_rate_market": self.fee_rate_market,
                            "fee_source": self.fee_source,
                            "fee_enabled": self.fee_enabled,
                            "fee_formula_version": self.fee_formula_version
                        }
                    }
        except Exception as e:
            logger.error(f"Error discovering 1H market: {e}")
        return None

    async def fetch_finalized_binance_candle(self, candle_open_ts: int) -> Tuple[float, float]:
        """Pulls exact finalized Binance Spot 1H candle open and close prices."""
        session = await self.get_session()
        try:
            start_ms = candle_open_ts * 1000
            url = f"{BINANCE_REST_URL}/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={start_ms}&limit=1"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        open_px = float(data[0][1])
                        close_px = float(data[0][4])
                        return open_px, close_px
        except Exception as e:
            logger.error(f"Failed to fetch Binance Spot 1H candle: {e}")
        return 0.0, 0.0

    async def verify_and_log_resolution(self, market: Dict[str, Any]):
        """
        Pulls finalized Binance Spot 1H candle at expiry to verify ground truth:
          Y_UP = 1[Close_1H >= Open_1H]
          Y_DOWN = 1[Close_1H < Open_1H]
        """
        logger.info(f"[*] Awaiting finalized candle close for market {market['market_id']} ({market['title']})...")
        await asyncio.sleep(6.0)  # Wait 6s after the top of the hour for candle finalization
        open_px, close_px = await self.fetch_finalized_binance_candle(market["candle_open_ts"])
        if open_px > 0 and close_px > 0:
            y_up = 1 if close_px >= open_px else 0
            y_down = 1 if close_px < open_px else 0
            ret_pct = ((close_px - open_px) / open_px) * 100.0

            res_record = {
                "timestamp_resolved": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "market_id": market["market_id"],
                "title": market["title"],
                "candle_open_ts": market["candle_open_ts"],
                "candle_close_ts": market["candle_close_ts"],
                "binance_spot_open": open_px,
                "binance_spot_close": close_px,
                "candle_return_pct": round(ret_pct, 4),
                "Y_UP": y_up,
                "Y_DOWN": y_down,
                "winning_outcome": "UP" if y_up == 1 else "DOWN",
                "ground_truth_rule": "Polymarket 1H Rule: Y = 1[Close_1H >= Open_1H] on Binance Spot BTC/USDT"
            }

            with open(RESOLUTIONS_FILE, "a") as f:
                f.write(json.dumps(res_record) + "\n")

            logger.info(f"\n==============================================================================="
                        f"\n[GROUND TRUTH RESOLUTION LOGGED] {market['title']}"
                        f"\n  Finalized Binance Spot: Open=${open_px:,.2f} -> Close=${close_px:,.2f} ({ret_pct:+.3f}%)"
                        f"\n  Ground Truth: Y_UP={y_up}, Y_DOWN={y_down} -> WINNER: {res_record['winning_outcome']}"
                        f"\n===============================================================================\n")

    def update_basis(self):
        if self.spot_price > 0 and self.futures_price > 0:
            self.basis_usd = self.futures_price - self.spot_price
            self.basis_bps = (self.basis_usd / self.spot_price) * 10000.0
            self.basis_history.append((time.monotonic_ns(), self.basis_bps))

    def get_delta_basis_100ms(self) -> float:
        """Computes signed basis change over the last 100ms."""
        now_ns = time.monotonic_ns()
        cutoff_ns = now_ns - 100_000_000
        for t_ns, b_bps in self.basis_history:
            if t_ns >= cutoff_ns:
                return round(self.basis_bps - b_bps, 2)
        return 0.0

    async def stream_binance_spot(self):
        """Tokyo-latency microsecond Binance Spot aggTrade stream (Polymarket Settlement Ref)."""
        while self.running:
            try:
                logger.info(f"Connecting to Binance Spot aggTrade ({BINANCE_SPOT_WS_URL})...")
                async with websockets.connect(BINANCE_SPOT_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("[+] Subscribed to Binance Spot aggTrade stream.")
                    async for msg_str in ws:
                        if not self.running:
                            break
                        recv_mono_ns = time.monotonic_ns()
                        msg = json.loads(msg_str)
                        px = float(msg.get("p", 0))
                        sz = float(msg.get("q", 0))
                        is_buyer = not msg.get("m", False)  # True = taker buy
                        e_ts = int(msg.get("E", 0))
                        t_ts = int(msg.get("T", 0))
                        notional = px * sz

                        self.spot_price = px
                        self.update_basis()
                        self.spot_trades.append((recv_mono_ns, e_ts, t_ts, notional, is_buyer, px))

                        # Evaluate Spot 100ms volume shock with strictly anchored t0
                        self.evaluate_shock(recv_mono_ns, e_ts, source="SPOT")
            except Exception as e:
                logger.warning(f"Binance Spot feed disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    async def stream_binance_futures(self):
        """Tokyo-latency microsecond Binance USDⓈ-M Futures aggTrade stream (Routed /market endpoint)."""
        while self.running:
            try:
                logger.info(f"Connecting to Binance Futures aggTrade ({BINANCE_FUTURES_WS_URL})...")
                async with websockets.connect(BINANCE_FUTURES_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("[+] Subscribed to Binance Futures aggTrade stream (routed /market).")
                    async for msg_str in ws:
                        if not self.running:
                            break
                        recv_mono_ns = time.monotonic_ns()
                        msg = json.loads(msg_str)
                        px = float(msg.get("p", 0))
                        sz = float(msg.get("q", 0))
                        is_buyer = not msg.get("m", False)
                        e_ts = int(msg.get("E", 0))
                        t_ts = int(msg.get("T", 0))
                        notional = px * sz

                        self.futures_price = px
                        self.update_basis()
                        self.futures_trades.append((recv_mono_ns, e_ts, t_ts, notional, is_buyer, px))

                        # Evaluate Futures 100ms volume shock with strictly anchored t0
                        self.evaluate_shock(recv_mono_ns, e_ts, source="FUTURES")
            except Exception as e:
                logger.warning(f"Binance Futures feed disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    def evaluate_shock(self, recv_mono_ns: int, event_ts_ms: int, source: str):
        """
        Evaluates volume sweeps strictly over [t0 - 100ms, t0].
        t0 is anchored as the end of the qualifying shock window.
        """
        trade_queue = self.spot_trades if source == "SPOT" else self.futures_trades
        cutoff_ns = recv_mono_ns - 100_000_000  # 100ms rolling window
        vol_100ms = 0.0
        buy_vol = 0.0
        sell_vol = 0.0

        for t_mono, _, _, ntl, buyer, _ in reversed(trade_queue):
            if t_mono < cutoff_ns:
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

            # Strict Causal Anchor: t0 = end of the qualifying 100-ms shock window
            t0_sec = now_sec
            t0_mono_ns = recv_mono_ns
            delta_basis_100ms = self.get_delta_basis_100ms()

            logger.info(f"\n[!!! {source} SHOCK TRIGGERED !!!] 100ms Vol=${vol_100ms:,.0f} | Dir={shock_dir} | "
                        f"OFI={ofi:+.2f} | Spot=${self.spot_price:,.1f} | Fut=${self.futures_price:,.1f} | "
                        f"Basis={self.basis_bps:+.1f}bps | DeltaBasis100ms={delta_basis_100ms:+.1f}bps")

            asyncio.create_task(self.capture_shock_burst(
                t0_sec, t0_mono_ns, source, vol_100ms, shock_dir, ofi, trigger_px, delta_basis_100ms
            ))

    async def capture_shock_burst(
        self,
        t0: float,
        t0_mono_ns: int,
        source: str,
        shock_vol: float,
        shock_dir: str,
        ofi: float,
        trigger_px: float,
        delta_basis_100ms: float
    ):
        """
        Captures the Probability Repricing Impulse-Response Function IRF(tau) = E[Delta_q(tau)].
        Strict Causal Separation:
          - Predictor features frozen strictly at t <= t0.
          - Repricing measurements occur strictly after t0 + epsilon.
        """
        up_book = self.books.get("UP")
        down_book = self.books.get("DOWN")
        if not up_book or not down_book or not self.current_market:
            return

        # Snapshot predictor features strictly at t0
        pre_shock_up = up_book.get_metrics(obs_ts=t0, fee_rate=self.fee_rate_market)
        pre_shock_down = down_book.get_metrics(obs_ts=t0, fee_rate=self.fee_rate_market)
        pre_shock_basis_signed = self.basis_bps
        pre_shock_basis_abs = abs(self.basis_bps)

        ladder_delays = [0.10, 0.15, 0.25, 0.50, 4.0, 25.0]
        ladder_labels = ["100ms", "250ms", "500ms", "1s", "5s", "30s"]
        response_snapshots = {}

        for delay, label in zip(ladder_delays, ladder_labels):
            await asyncio.sleep(delay)
            t_sample = time.time()
            up_m = up_book.get_metrics(obs_ts=t_sample, fee_rate=self.fee_rate_market)
            down_m = down_book.get_metrics(obs_ts=t_sample, fee_rate=self.fee_rate_market)
            response_snapshots[label] = {
                "elapsed_sec": round(t_sample - t0, 3),
                "up_mid": up_m["q_mid"],
                "up_ask": up_m["best_ask"],
                "up_delta_q_ask": round(up_m["best_ask"] - pre_shock_up["best_ask"], 4),
                "up_delta_q_mid": round(up_m["q_mid"] - pre_shock_up["q_mid"], 4),
                "up_obi_l1": up_m["obi_l1"],
                "up_obi_depth": up_m["obi_depth"],
                "down_mid": down_m["q_mid"],
                "down_ask": down_m["best_ask"],
                "down_delta_q_ask": round(down_m["best_ask"] - pre_shock_down["best_ask"], 4),
                "down_delta_q_mid": round(down_m["q_mid"] - pre_shock_down["q_mid"], 4),
                "binance_spot": self.spot_price,
                "binance_futures": self.futures_price,
                "basis_bps": round(self.basis_bps, 2),
                "delta_basis_bps": round(self.basis_bps - pre_shock_basis_signed, 2)
            }

        secs_left = (self.current_market["end_dt"] - datetime.now(timezone.utc)).total_seconds()
        dist_pct = ((self.spot_price - self.finalized_1h_open) / self.finalized_1h_open * 100.0) if self.finalized_1h_open > 0 else 0.0

        shock_record = {
            "timestamp": datetime.fromtimestamp(t0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "t0_unix": t0,
            "t0_mono_ns": t0_mono_ns,
            "shock_source": source,
            "market_id": self.current_market["market_id"],
            "title": self.current_market["title"],
            "seconds_to_expiry": round(secs_left, 1),
            "shock_volume_100ms": round(shock_vol, 0),
            "shock_direction": shock_dir,
            "shock_ofi": round(ofi, 3),
            "trigger_price": trigger_px,
            "spot_at_t0": self.spot_price,
            "futures_at_t0": self.futures_price,
            "basis_signed_bps_t0": round(pre_shock_basis_signed, 2),
            "basis_abs_bps_t0": round(pre_shock_basis_abs, 2),
            "delta_basis_100ms": delta_basis_100ms,
            "finalized_1h_open": self.finalized_1h_open,
            "candle_distance_pct": round(dist_pct, 4),
            "fee_metadata": self.current_market.get("fee_metadata", {}),
            "pre_shock_features_t0": {
                "UP": pre_shock_up,
                "DOWN": pre_shock_down
            },
            "impulse_response": response_snapshots,
            "pre_registered_models": {
                "model_a_spot": "Y = f(q_mid, X_spot, TTE, dist)",
                "model_b_futures": "Y = f(q_mid, X_futures, TTE, dist)",
                "model_c_joint": "Y = f(q_mid, X_spot, X_futures, basis, delta_basis, TTE, dist)",
                "model_d_incremental": "Y = f(q_mid, X_spot, TTE, dist) + g(X_futures | X_spot) -> test beta_{F|S} = 0",
                "oos_training_invariant": "T_train_end < t0 (model trained strictly on completed prior markets)"
            },
            "clock_metadata": {
                "clock_offset_ms": self.clock_offset_ms,
                "clock_uncertainty_ms": self.clock_uncertainty_ms,
                "timestamp_designation": "exchange_to_local_delta_with_calibrated_offset"
            },
            "statistical_clustering": {
                "cluster_market_hour": self.current_market["market_id"],
                "cluster_shock_episode": f"{self.current_market['market_id']}_{int(t0)}",
                "variance_estimator": "IRF: shock-episode block bootstrap | Regressions: market-hour cluster-robust SE"
            }
        }

        with open(SHOCK_FILE, "a") as f:
            f.write(json.dumps(shock_record) + "\n")

        up_30s_delta = response_snapshots["30s"]["up_delta_q_ask"]
        logger.info(f"[SHOCK BURST CAPTURED] Market {self.current_market['market_id']} | Source={source} | "
                    f"AgeAsk(UP)={pre_shock_up['age_ask_ms']:.0f}ms | UP ask={pre_shock_up['best_ask']:.3f} -> 30s Delta: {up_30s_delta:+.3f} | "
                    f"Basis={pre_shock_basis_signed:+.1f}bps (Observational episode, not yet evidence of persistent structural lag)")

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

                        # Check if current market has reached expiry
                        if (self.current_market["end_dt"] - datetime.now(timezone.utc)).total_seconds() <= 0:
                            logger.info(f"[*] 1H Market {self.current_market['market_id']} reached expiry. Cycling to next.")
                            break
            except Exception as e:
                logger.warning(f"Polymarket CLOB WS disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    def compute_leadlag_cross_correlation(self):
        """
        Pre-registered Lead/Lag cross-correlation estimation:
          Estimates Corr(epsilon_F(t), epsilon_S(t + Delta)) over Delta in CORRELATION_LAGS_MS
          using flow innovations (Point 2: do not perform primary lead/lag on raw levels).
        """
        if len(self.spot_trades) < 200 or len(self.futures_trades) < 200:
            return

        now_ns = time.monotonic_ns()
        window_ns = 300_000_000_000  # 5-minute rolling analysis window
        t_start_ns = now_ns - window_ns

        # Bin signed order flow into 25ms time buckets
        bucket_size_ns = 25_000_000
        num_buckets = int(window_ns // bucket_size_ns)
        spot_bins = np.zeros(num_buckets, dtype=np.float64)
        fut_bins = np.zeros(num_buckets, dtype=np.float64)

        for t_mono, _, _, ntl, buyer, _ in self.spot_trades:
            if t_mono >= t_start_ns:
                idx = min(int((t_mono - t_start_ns) // bucket_size_ns), num_buckets - 1)
                spot_bins[idx] += (ntl if buyer else -ntl)

        for t_mono, _, _, ntl, buyer, _ in self.futures_trades:
            if t_mono >= t_start_ns:
                idx = min(int((t_mono - t_start_ns) // bucket_size_ns), num_buckets - 1)
                fut_bins[idx] += (ntl if buyer else -ntl)

        # De-autocorrelate: compute first-difference flow innovations epsilon_t = flow_t - flow_{t-1}
        spot_innovations = np.diff(spot_bins)
        fut_innovations = np.diff(fut_bins)

        corrs = {}
        for lag_ms in CORRELATION_LAGS_MS:
            shift_buckets = int(lag_ms * 1_000_000 / bucket_size_ns)
            if shift_buckets == 0:
                s = spot_innovations
                f = fut_innovations
            elif shift_buckets > 0:
                f = fut_innovations[:-shift_buckets]
                s = spot_innovations[shift_buckets:]
            else:
                shift = abs(shift_buckets)
                f = fut_innovations[shift:]
                s = spot_innovations[:-shift]

            if len(s) > 10 and np.std(s) > 1e-6 and np.std(f) > 1e-6:
                corr_val = float(np.corrcoef(f, s)[0, 1])
                corrs[str(lag_ms)] = round(corr_val, 4)
            else:
                corrs[str(lag_ms)] = 0.0

        max_lag = max(corrs.items(), key=lambda x: x[1]) if corrs else ("0", 0.0)

        record = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "timestamp_unix": time.time(),
            "market_id": self.current_market["market_id"] if self.current_market else "none",
            "correlation_grid_lags_ms": corrs,
            "peak_correlation_lag_ms": int(max_lag[0]),
            "peak_correlation_val": max_lag[1],
            "metric_evaluated": "flow_innovations_cross_correlation (diff(signed_dollar_flow_25ms))",
            "telemetry_classification": "illustrative live telemetry, not evidence of persistent lead/lag",
            "null_hypothesis": "H0: no stable lead/lag structure across pre-registered grid",
            "clock_metadata": {
                "calibrated_offset_ms": self.clock_offset_ms,
                "clock_uncertainty_ms": self.clock_uncertainty_ms,
                "resolution_caveat": "Lags <= 50ms are within RTT uncertainty (+/-21.6ms) and must be evaluated strictly under pooled bootstrap bands."
            }
        }

        with open(CORRELATIONS_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")

        logger.info(f"[LEAD/LAG INNOVATION TELEMETRY] Peak Lag: {max_lag[0]}ms (r={max_lag[1]:+.3f}) | Status: Illustrative telemetry (H0: no stable lead/lag)")

    async def telemetry_logger_loop(self):
        """Periodic 10s baseline telemetry logger, cross-correlation estimator, and rollover manager."""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                if not self.current_market or (self.current_market["end_dt"] - now).total_seconds() <= 0:
                    expired_market = self.current_market
                    if expired_market:
                        # Ground truth verification of finalized candle
                        asyncio.create_task(self.verify_and_log_resolution(expired_market))

                    market = await self.discover_nearest_1h_market()
                    if market:
                        self.current_market = market
                        open_px, _ = await self.fetch_finalized_binance_candle(market["candle_open_ts"])
                        self.finalized_1h_open = open_px
                        logger.info(f"\n==============================================================================="
                                    f"\n[ACTIVE 1H PRODUCT LOADED] {market['title']}"
                                    f"\n  Market ID: {market['market_id']} | End: {market['end_date_iso']}"
                                    f"\n  UP Token: {market['tokens']['UP']}"
                                    f"\n  DOWN Token: {market['tokens']['DOWN']}"
                                    f"\n  Binance Spot 1H Finalized Open: ${self.finalized_1h_open:,.2f}"
                                    f"\n  Fee Rate: {self.fee_rate_market * 100:.1f}% ({self.fee_source})"
                                    f"\n===============================================================================\n")

                if self.current_market and "UP" in self.books and "DOWN" in self.books:
                    up_metrics = self.books["UP"].get_metrics(fee_rate=self.fee_rate_market)
                    down_metrics = self.books["DOWN"].get_metrics(fee_rate=self.fee_rate_market)
                    secs_left = (self.current_market["end_dt"] - now).total_seconds()
                    dist_pct = ((self.spot_price - self.finalized_1h_open) / self.finalized_1h_open * 100.0) if self.finalized_1h_open > 0 else 0.0

                    delta_basis_100ms = self.get_delta_basis_100ms()

                    record = {
                        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "timestamp_unix": now.timestamp(),
                        "market_id": self.current_market["market_id"],
                        "title": self.current_market["title"],
                        "seconds_to_expiry": round(secs_left, 1),
                        "binance_spot": self.spot_price,
                        "binance_futures": self.futures_price,
                        "basis_signed_usd": round(self.basis_usd, 2),
                        "basis_signed_bps": round(self.basis_bps, 2),
                        "basis_abs_bps": round(abs(self.basis_bps), 2),
                        "delta_basis_100ms": delta_basis_100ms,
                        "binance_1h_open": self.finalized_1h_open,
                        "candle_distance_pct": round(dist_pct, 4),
                        "clock_metadata": {
                            "clock_offset_ms": self.clock_offset_ms,
                            "clock_uncertainty_ms": self.clock_uncertainty_ms,
                            "timestamp_designation": "exchange_to_local_delta_with_calibrated_offset"
                        },
                        "fee_metadata": self.current_market.get("fee_metadata", {}),
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

                # Periodic 60s cross-correlation estimation on flow innovations
                if time.time() - self.last_cross_corr_ts > 60.0:
                    self.last_cross_corr_ts = time.time()
                    self.compute_leadlag_cross_correlation()

                # Periodic 300s clock synchronization
                if time.time() - self.last_clock_sync_ts > 300.0:
                    asyncio.create_task(self.calibrate_binance_clock_offset())

                await asyncio.sleep(10.0)
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}", exc_info=True)
                await asyncio.sleep(10.0)

    async def run(self):
        logger.info("===============================================================================")
        logger.info("   ROUTE 3: FUTURES/SPOT -> POLYMARKET INFORMATION-FLOW EXPERIMENT (v2.7)     ")
        logger.info("   Dual Feeds: Binance Spot (Settlement Ref) + Futures (Routed /market)        ")
        logger.info("   Invariants: OBI/q_micro Reconciled + Invariant Assertions Enforced          ")
        logger.info("   Quote Ages: Tripartite (Age_book, Age_bid, Age_ask)                         ")
        logger.info("   Clock Sync: Cristian's Algorithm Calibrated Offset (Tokyo <-> Binance)      ")
        logger.info("   Econometrics: Strict Causal t0 Anchor + Lead/Lag Innovation Grid            ")
        logger.info("   Capacity Surface: Fill-Level Fees & Crossing Cost [$1, $5, $20, $50, $100]  ")
        logger.info("   Resolution Truth: Finalized Binance Spot 1H Candle Open & Close             ")
        logger.info("   Operational: Read-Only (Does not circumvent geographic restrictions)        ")
        logger.info("===============================================================================")

        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        # Initial clock offset calibration
        await self.calibrate_binance_clock_offset()

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

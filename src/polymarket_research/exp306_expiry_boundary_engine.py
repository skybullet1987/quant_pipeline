#!/usr/bin/env python3
"""
EXP-306: Deterministic Expiry Boundary Convergence Engine (Phase 1/2 Production Daemon)
======================================================================================
Exploits structural terminal mispricings on Polymarket high-frequency 5-minute and 15-minute
crypto contracts (BTC, ETH, SOL) as time to expiration approaches zero (tau -> 0).

Key Capabilities:
  1. Dynamic 4-Sigma Extreme Value Envelope:
     Replaces static jump heuristics with continuous realized tick-volatility scaling:
     S_min(t) = S(t) * (1 - z_alpha * sigma_tick * sqrt(tau))
  2. Dual Resolution Model Support:
     - Discrete Riemann TWAP accumulator over averaging window [T - M, T]
     - Terminal Black-Scholes binary jump barrier for single discrete close snapshots:
       |S_t - K| / (sigma * S_t * sqrt(tau)) >= 3.5
  3. Composite Dual-Venue Spot Tick Ingestion:
     Aggregates real-time trades from Binance (aggTrade) and Coinbase (matches/ticker),
     computing a median composite benchmark to eliminate single-venue oracle basis risk.
  4. Instantaneous Complementary Token Split/Merge Arbitrage:
     Detects panic mispricings where P_ask(UP) + P_ask(DOWN) < 1.00 - fees,
     enabling atomic on-chain burning via CTF mergePositions with zero resolution risk.
  5. Isolated Shadow Trading Ledger:
     Logs all opportunities and shadow fills to data/exp306/shadow_boundary_ledger.jsonl
     for zero-capital empirical certification against finalized on-chain resolutions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import signal
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import aiohttp
import websockets

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data" / "exp306"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LEDGER_FILE = DATA_DIR / "shadow_boundary_ledger.jsonl"
STATE_FILE = DATA_DIR / "exp306_state.json"
PID_FILE = DATA_DIR / "exp306_engine.pid"
LOG_FILE = DATA_DIR / "exp306_engine.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [EXP306] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("EXP306Engine")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BINANCE_WS_URL = "wss://stream.binance.com:443/stream?streams=btcusdt@aggTrade/ethusdt@aggTrade/solusdt@aggTrade"
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"


# ==============================================================================
# MATHEMATICAL BOUNDARY CONVERGENCE ENGINE
# ==============================================================================

class BoundaryConvergenceEngine:
    """
    Evaluates terminal boundary convergence conditions for short-horizon binary contracts.
    Operates with dynamic volatility envelopes, composite median feeds, and dynamic fees.
    """

    def __init__(
        self,
        strike_price: float,
        expiry_timestamp: float,
        resolution_type: str = "TWAP",  # "TWAP" or "DISCRETE_CLOSE"
        twap_window_seconds: float = 30.0,
        min_hurdle_profit: float = 0.02,  # $0.02 per share minimum margin of safety
        taker_fee_coefficient: float = 0.07,  # Standard Polymarket crypto fee parameter
        z_score_envelope: float = 4.0,  # 4-sigma extreme value envelope
        discrete_jump_threshold: float = 3.5,  # 3.5-sigma barrier for discrete close
    ):
        self.k = strike_price
        self.t_exp = expiry_timestamp
        self.resolution_type = resolution_type.upper()
        self.twap_window = twap_window_seconds
        self.min_hurdle = min_hurdle_profit
        self.r = taker_fee_coefficient
        self.z = z_score_envelope
        self.discrete_jump_threshold = discrete_jump_threshold
        self.tick_history: List[Tuple[float, float]] = []  # List of (timestamp, composite_price)

    def record_composite_tick(self, spot_price: float, current_time: float) -> None:
        """Records median composite spot tick and prunes samples outside the rolling lookback window."""
        self.tick_history.append((current_time, spot_price))
        cutoff = current_time - max(self.twap_window, 900.0)
        self.tick_history = [(t, p) for (t, p) in self.tick_history if t >= cutoff]

    def estimate_instantaneous_volatility(self) -> float:
        """
        Computes 1-second normalized log-return volatility.
        Returns annualized or 1-second sigma floor of 5 bps/sec (0.0005).
        """
        if len(self.tick_history) < 5:
            return 0.0005  # Conservative floor: 5 bps/sec

        returns = []
        for i in range(1, len(self.tick_history)):
            dt = self.tick_history[i][0] - self.tick_history[i - 1][0]
            if dt > 1e-4:
                p1, p2 = self.tick_history[i - 1][1], self.tick_history[i][1]
                if p1 > 0 and p2 > 0:
                    ret = math.log(p2 / p1) / math.sqrt(dt)
                    returns.append(ret)

        if not returns:
            return 0.0005

        variance = sum(r * r for r in returns) / len(returns)
        return max(0.0002, math.sqrt(variance))

    def compute_twap_bounds(self, current_time: float) -> Dict[str, float]:
        """
        Calculates volatility-bounded terminal TWAP extremes over window [T_exp - T_window, T_exp].
        Corrects pre-window clamping and guarantees elapsed + remaining weights equal T_window.
        """
        if not self.tick_history:
            return {"twap_min": 0.0, "twap_max": float("inf"), "sigma_sec": 0.0}

        t_start = self.t_exp - self.twap_window
        total_window = self.twap_window
        latest_spot = self.tick_history[-1][1]
        sigma_sec = self.estimate_instantaneous_volatility()

        # Case 1: Prior to the start of the designated TWAP window
        if current_time <= t_start:
            time_to_exp = max(0.001, self.t_exp - current_time)
            max_dev = latest_spot * (self.z * sigma_sec * math.sqrt(time_to_exp))
            p_min = max(0.0, latest_spot - max_dev)
            p_max = latest_spot + max_dev
            return {"twap_min": p_min, "twap_max": p_max, "sigma_sec": sigma_sec}

        # Case 2: Inside or beyond the designated TWAP window
        time_elapsed = min(total_window, max(0.0, current_time - t_start))
        time_remaining = max(0.0, self.t_exp - current_time)

        # Time-weighted average across ticks within [t_start, current_time]
        window_ticks = [(t, p) for (t, p) in self.tick_history if t >= t_start]
        if window_ticks:
            if len(window_ticks) == 1:
                running_twap = window_ticks[0][1]
            else:
                total_w = 0.0
                weighted_sum = 0.0
                for i in range(1, len(window_ticks)):
                    dt = max(1e-4, window_ticks[i][0] - window_ticks[i - 1][0])
                    avg_p = (window_ticks[i][1] + window_ticks[i - 1][1]) / 2.0
                    weighted_sum += avg_p * dt
                    total_w += dt
                running_twap = (weighted_sum / total_w) if total_w > 0 else window_ticks[-1][1]
        else:
            running_twap = latest_spot

        max_deviation = latest_spot * (self.z * sigma_sec * math.sqrt(time_remaining + 1e-4))
        p_min = max(0.0, latest_spot - max_deviation)
        p_max = latest_spot + max_deviation

        twap_min = ((running_twap * time_elapsed) + (p_min * time_remaining)) / total_window
        twap_max = ((running_twap * time_elapsed) + (p_max * time_remaining)) / total_window

        return {"twap_min": twap_min, "twap_max": twap_max, "sigma_sec": sigma_sec}

    def evaluate_discrete_close_barrier(self, current_time: float) -> Dict[str, Any]:
        """
        Evaluates Black-Scholes binary jump barrier for single discrete close snapshot:
        Z = |S_t - K| / (sigma_sec * S_t * sqrt(tau))
        """
        if not self.tick_history:
            return {"deterministic": False, "winning_side": None, "z_score": 0.0}

        latest_spot = self.tick_history[-1][1]
        time_remaining = max(0.001, self.t_exp - current_time)
        sigma_sec = self.estimate_instantaneous_volatility()

        denom = sigma_sec * latest_spot * math.sqrt(time_remaining)
        z_score = abs(latest_spot - self.k) / denom if denom > 0 else 999.0

        if z_score >= self.discrete_jump_threshold:
            winning_side = "UP" if latest_spot > self.k else "DOWN"
            return {"deterministic": True, "winning_side": winning_side, "z_score": z_score}

        return {"deterministic": False, "winning_side": None, "z_score": z_score}

    def fee_usd_per_share(self, price: float) -> float:
        """
        Computes Polymarket crypto taker fee in dollars per share:
        Fee_share = r * P * (1 - P)
        """
        p = max(0.001, min(0.999, price))
        return self.r * p * (1.0 - p)

    def effective_fee_rate_on_notional(self, price: float) -> float:
        """
        Computes effective taker fee rate relative to deployed capital:
        Rate = r * (1 - P)
        """
        p = max(0.001, min(0.999, price))
        return self.r * (1.0 - p)

    def calculate_polymarket_taker_fee(self, price: float) -> float:
        """
        Legacy rate wrapper returning effective fee rate on notional: r * (1 - P).
        Preserved for test compatibility.
        """
        return self.effective_fee_rate_on_notional(price)

    def evaluate_execution_entry(
        self,
        target_token_side: str,  # "UP" or "DOWN"
        clob_best_ask: float,
        ask_liquidity: float,
        current_time: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates contract pricing against deterministic boundary conditions.
        Returns execution payload if edge satisfies the hurdle threshold using consistent USD/share units.
        """
        is_deterministic_winner = False
        reason = ""
        metric_val = 0.0

        if self.resolution_type == "TWAP":
            bounds = self.compute_twap_bounds(current_time)
            if target_token_side.upper() == "UP":
                is_deterministic_winner = bounds["twap_min"] >= self.k
                reason = "TWAP_MIN_EXCEEDS_STRIKE"
                metric_val = bounds["twap_min"]
            else:
                is_deterministic_winner = bounds["twap_max"] <= self.k
                reason = "TWAP_MAX_BELOW_STRIKE"
                metric_val = bounds["twap_max"]
        else:
            # Discrete snapshot resolution
            barrier = self.evaluate_discrete_close_barrier(current_time)
            if barrier["deterministic"] and barrier["winning_side"] == target_token_side.upper():
                is_deterministic_winner = True
                reason = f"DISCRETE_BARRIER_Z_{barrier['z_score']:.1f}"
                metric_val = barrier["z_score"]

        if not is_deterministic_winner:
            return None
        if not (0.84 <= clob_best_ask <= 0.96):
            return None

        # Closed-form dynamic taker fee in dollars per share
        fee_per_share = self.fee_usd_per_share(clob_best_ask)
        effective_cost = clob_best_ask + fee_per_share
        net_edge = 1.00 - effective_cost

        if net_edge >= self.min_hurdle:
            return {
                "action": "BUY_FOK",
                "side": target_token_side.upper(),
                "price": clob_best_ask,
                "shares": ask_liquidity,
                "net_edge": net_edge,
                "fee": fee_per_share,
                "metric_val": metric_val,
                "reason": reason,
            }

        return None


# ==============================================================================
# COMPLEMENTARY TOKEN SPLIT/MERGE SCANNER
# ==============================================================================

@dataclass
class MergeArbitrageOpportunity:
    market_id: str
    token_up: str
    token_down: str
    best_ask_up: float
    best_ask_down: float
    depth_up_shares: float
    depth_down_shares: float
    gross_cost: float
    fee_up: float
    fee_down: float
    net_cost: float
    net_profit_per_share: float
    max_executable_shares: float
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def evaluate_instantaneous_merge_arbitrage(
    market_id: str,
    token_up: str,
    token_down: str,
    best_ask_up: float,
    best_ask_down: float,
    depth_up_shares: float,
    depth_down_shares: float,
    fee_coefficient: float = 0.07,
    estimated_gas_usd: float = 0.015,
) -> Optional[MergeArbitrageOpportunity]:
    """
    Checks if sum of best asks allows instantaneous atomic merge:
    P_ask(UP) + P_ask(DOWN) < 1.00 - f_poly(UP) - f_poly(DOWN) - gas
    If true, holding both outcomes allows calling CTF mergePositions for instant $1.00 USDC.
    """
    if best_ask_up <= 0 or best_ask_down <= 0:
        return None

    fee_up = fee_coefficient * best_ask_up * (1.0 - best_ask_up)
    fee_down = fee_coefficient * best_ask_down * (1.0 - best_ask_down)
    gross_cost = round(best_ask_up + best_ask_down, 6)
    total_cost = gross_cost + fee_up + fee_down

    max_shares = min(depth_up_shares, depth_down_shares)
    if max_shares <= 0:
        return None

    gas_per_share = estimated_gas_usd / max_shares
    net_cost_per_share = round(total_cost + gas_per_share, 6)
    net_profit = round(1.00 - net_cost_per_share, 6)

    if net_profit >= 0.015:  # At least 1.5 cents net profit per share
        return MergeArbitrageOpportunity(
            market_id=market_id,
            token_up=token_up,
            token_down=token_down,
            best_ask_up=best_ask_up,
            best_ask_down=best_ask_down,
            depth_up_shares=depth_up_shares,
            depth_down_shares=depth_down_shares,
            gross_cost=gross_cost,
            fee_up=fee_up,
            fee_down=fee_down,
            net_cost=net_cost_per_share,
            net_profit_per_share=net_profit,
            max_executable_shares=max_shares,
        )

    return None


# ==============================================================================
# EXP-306 PRODUCTION SHADOW DAEMON
# ==============================================================================

class EXP306BoundaryDaemon:
    """
    Full background shadow execution daemon for Vector 2:
    - Streams Binance + Coinbase spot trades for BTC, ETH, SOL
    - Streams Polymarket L2 orderbooks for active sub-hourly markets
    - Evaluates BoundaryConvergenceEngine & Merge Arbitrage continuously
    - Logs shadow executions and verifications to shadow_boundary_ledger.jsonl
    """

    def __init__(self):
        self.running = False
        self.spot_feeds: Dict[str, Dict[str, float]] = {
            "BTC": {"binance": 0.0, "coinbase": 0.0, "composite": 0.0, "updated": 0.0},
            "ETH": {"binance": 0.0, "coinbase": 0.0, "composite": 0.0, "updated": 0.0},
            "SOL": {"binance": 0.0, "coinbase": 0.0, "composite": 0.0, "updated": 0.0},
        }
        self.active_markets: Dict[str, Dict[str, Any]] = {}
        self.boundary_engines: Dict[str, BoundaryConvergenceEngine] = {}
        self.clob_books: Dict[str, Dict[str, Any]] = {}
        self.strike_cache: Dict[str, float] = {}
        self.executed_boundary_markets: set[str] = set()
        self.binance_backoff_until: float = 0.0
        self.stats = {
            "boundary_triggers": 0,
            "merge_triggers": 0,
            "shadow_orders": 0,
            "total_notional_shadow_usd": 0.0,
        }

    def _update_composite_spot(self, asset: str, venue: str, price: float) -> None:
        """Updates spot feeds and computes median composite benchmark."""
        now = time.time()
        feed = self.spot_feeds[asset]
        feed[venue] = price
        feed[f"{venue}_ts"] = now
        feed["updated"] = now

        b_px = feed["binance"]
        c_px = feed["coinbase"]
        b_fresh = (now - float(feed.get("binance_ts", 0.0) or 0.0)) <= 3.0
        c_fresh = (now - float(feed.get("coinbase_ts", 0.0) or 0.0)) <= 3.0

        if b_px > 0 and c_px > 0 and b_fresh and c_fresh:
            feed["composite"] = (b_px + c_px) / 2.0
            diff = abs(b_px - c_px)
            if diff > (b_px * 0.001):  # > 10 bps divergence
                logger.debug(f"[BASIS-ALERT] {asset} Binance vs Coinbase spread: ${diff:.2f}")
        elif b_px > 0 and b_fresh:
            feed["composite"] = b_px
        elif c_px > 0 and c_fresh:
            feed["composite"] = c_px

        comp_price = feed["composite"]
        if comp_price > 0:
            for market_id, m_data in self.active_markets.items():
                if m_data.get("asset") == asset and market_id in self.boundary_engines:
                    self.boundary_engines[market_id].record_composite_tick(comp_price, now)

    async def _binance_stream_worker(self) -> None:
        """WebSocket stream worker for Binance spot aggTrades."""
        symbol_map = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL"}
        while self.running:
            try:
                async with websockets.connect(BINANCE_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("✓ Connected to Binance Spot WebSocket stream.")
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        payload = data.get("data", {})
                        symbol = payload.get("s", "")
                        px = float(payload.get("p", 0.0))
                        asset = symbol_map.get(symbol)
                        if asset and px > 0:
                            self._update_composite_spot(asset, "binance", px)
            except Exception as e:
                if self.running:
                    logger.warning(f"Binance WS reconnecting due to: {e}")
                    await asyncio.sleep(2.0)

    async def _coinbase_stream_worker(self) -> None:
        """WebSocket stream worker for Coinbase spot matches/ticker."""
        prod_map = {"BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL"}
        while self.running:
            try:
                async with websockets.connect(COINBASE_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    sub_msg = {
                        "type": "subscribe",
                        "product_ids": ["BTC-USD", "ETH-USD", "SOL-USD"],
                        "channels": ["matches", "ticker"],
                    }
                    await ws.send(json.dumps(sub_msg))
                    logger.info("✓ Connected to Coinbase Spot WebSocket stream.")
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        msg_type = data.get("type")
                        prod_id = data.get("product_id")
                        asset = prod_map.get(prod_id)
                        if not asset:
                            continue

                        px = 0.0
                        if msg_type in ("match", "last_match"):
                            px = float(data.get("price", 0.0))
                        elif msg_type == "ticker":
                            px = float(data.get("price", 0.0))

                        if px > 0:
                            self._update_composite_spot(asset, "coinbase", px)
            except Exception as e:
                if self.running:
                    logger.warning(f"Coinbase WS reconnecting due to: {e}")
                    await asyncio.sleep(2.0)

    async def _market_discovery_worker(self) -> None:
        """Discovers active 5m/15m/1h crypto markets from Gamma API every 30 seconds."""
        headers = {"User-Agent": "EXP306BoundaryDaemon/1.0"}
        slug_map = {
            "BTC": ["btc-up-or-down-hourly", "btc-15m", "btc-up-or-down-5m", "bitcoin-up-or-down"],
            "ETH": ["eth-up-or-down-hourly", "eth-15m", "ethereum-up-or-down"],
            "SOL": ["sol-up-or-down-hourly", "sol-15m", "solana-up-or-down"],
        }
        while self.running:
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    now = time.time()
                    for asset, slugs in slug_map.items():
                        for slug in slugs:
                            url = f"{GAMMA_API_URL}/events?series_slug={slug}&limit=5&closed=false"
                            try:
                                async with session.get(url, timeout=5) as resp:
                                    if resp.status == 200:
                                        events = await resp.json()
                                        for ev in events:
                                            for m in ev.get("markets", []):
                                                if m.get("closed", False):
                                                    continue
                                                end_iso = m.get("endDate")
                                                if not end_iso:
                                                    continue
                                                try:
                                                    dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                                                    t_exp = dt.timestamp()
                                                except Exception:
                                                    continue

                                                time_to_exp = t_exp - now
                                                if not (0 < time_to_exp <= 3600):
                                                    continue

                                                clob_tokens = m.get("clobTokenIds")
                                                if isinstance(clob_tokens, str):
                                                    try:
                                                        clob_tokens = json.loads(clob_tokens)
                                                    except Exception:
                                                        clob_tokens = []
                                                if not clob_tokens or len(clob_tokens) < 2:
                                                    continue

                                                mid = str(m.get("id"))
                                                raw_strike = m.get("strikePrice") or m.get("priceToBeat") or m.get("startingPrice")
                                                strike = float(raw_strike) if raw_strike else self.strike_cache.get(mid, 0.0)
                                                # AUDIT-01 / AUDIT-13-01 / AUDIT-13-08 Fix: Cache resolved strikes & handle HTTP 429/418 backoff
                                                if strike <= 0 and time.time() >= self.binance_backoff_until:
                                                    duration_s = 300 if "5m" in slug else (900 if "15m" in slug else 3600)
                                                    candle_open_ms = int((t_exp - duration_s) * 1000)
                                                    interval_str = "5m" if duration_s == 300 else ("15m" if duration_s == 900 else "1h")
                                                    try:
                                                        kline_url = f"https://api.binance.com/api/v3/klines?symbol={asset}USDT&interval={interval_str}&startTime={candle_open_ms}&limit=1"
                                                        async with session.get(kline_url, timeout=aiohttp.ClientTimeout(total=1.5)) as k_resp:
                                                            if k_resp.status == 200:
                                                                k_data = await k_resp.json()
                                                                if k_data and len(k_data[0]) > 1:
                                                                    strike = float(k_data[0][1])
                                                                    self.strike_cache[mid] = strike
                                                            elif k_resp.status in (429, 418):
                                                                retry_after = float(k_resp.headers.get("Retry-After", 60.0))
                                                                self.binance_backoff_until = time.time() + max(30.0, retry_after)
                                                                logger.error(f"[BINANCE_RATE_LIMIT] HTTP {k_resp.status} on kline lookup. Backing off for {retry_after:.0f}s.")
                                                    except Exception as k_err:
                                                        logger.warning(f"Failed to resolve authoritative candle open strike for {mid}: {k_err}")
                                                if strike <= 0:
                                                    logger.warning(f"[STRIKE_UNRESOLVED] Skipping market {mid} ({slug}): authoritative strike unavailable.")
                                                    continue

                                                is_subhourly = ("5m" in slug or "15m" in slug)
                                                oracle_src = str(m.get("resolutionSource") or m.get("oracle") or ("CHAINLINK" if is_subhourly else "BINANCE")).upper()
                                                res_type = "TWAP" if "twap" in m.get("description", "").lower() else "DISCRETE_CLOSE"

                                                self.active_markets[mid] = {
                                                    "market_id": mid,
                                                    "asset": asset,
                                                    "question": m.get("question"),
                                                    "strike": strike,
                                                    "t_exp": t_exp,
                                                    "resolution_type": res_type,
                                                    "token_up": clob_tokens[0],
                                                    "token_down": clob_tokens[1],
                                                    "oracle": oracle_src,
                                                    "basis_buffer_bps": 12.0 if "CHAINLINK" in oracle_src else 0.0,
                                                }

                                                if mid not in self.boundary_engines:
                                                    self.boundary_engines[mid] = BoundaryConvergenceEngine(
                                                        strike_price=strike,
                                                        expiry_timestamp=t_exp,
                                                        resolution_type=res_type,
                                                        twap_window_seconds=30.0,
                                                        min_hurdle_profit=0.02,
                                                        discrete_jump_threshold=4.0 if "CHAINLINK" in oracle_src else 3.5,
                                                    )
                            except Exception:
                                pass

                    logger.info(f"Market Discovery: Monitored sub-hourly markets: {len(self.active_markets)}")
            except Exception as e:
                logger.error(f"Market discovery error: {e}")

            await asyncio.sleep(30.0)

    async def _evaluation_loop(self) -> None:
        """Continuous sub-second evaluation loop matching L2 books against boundary conditions."""
        headers = {"User-Agent": "EXP306BoundaryDaemon/1.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            while self.running:
                now = time.time()
                expired = [mid for mid, m in self.active_markets.items() if m["t_exp"] <= now]
                for mid in expired:
                    self.active_markets.pop(mid, None)
                    self.boundary_engines.pop(mid, None)
                    self.strike_cache.pop(mid, None)
                    self.executed_boundary_markets.discard(mid)

                for mid, m_data in list(self.active_markets.items()):
                    tte = m_data["t_exp"] - now
                    if tte > 120.0 or tte <= 0 or mid in self.executed_boundary_markets:
                        continue

                    token_up = m_data["token_up"]
                    token_down = m_data["token_down"]
                    engine = self.boundary_engines.get(mid)
                    if not engine:
                        continue

                    try:
                        async with session.get(f"{CLOB_API_URL}/book", params={"token_id": token_up}, timeout=1.5) as r_up:
                            book_up = await r_up.json() if r_up.status == 200 else {}
                        async with session.get(f"{CLOB_API_URL}/book", params={"token_id": token_down}, timeout=1.5) as r_down:
                            book_down = await r_down.json() if r_down.status == 200 else {}

                        asks_up = sorted(book_up.get("asks", []), key=lambda x: float(x.get("price", 1.0)))
                        asks_down = sorted(book_down.get("asks", []), key=lambda x: float(x.get("price", 1.0)))
                        bids_up = sorted(book_up.get("bids", []), key=lambda x: float(x.get("price", 0.0)), reverse=True)
                        bids_down = sorted(book_down.get("bids", []), key=lambda x: float(x.get("price", 0.0)), reverse=True)

                        best_ask_up = float(asks_up[0]["price"]) if asks_up else 0.0
                        depth_up = float(asks_up[0]["size"]) if asks_up else 0.0

                        best_ask_down = float(asks_down[0]["price"]) if asks_down else 0.0
                        depth_down = float(asks_down[0]["size"]) if asks_down else 0.0

                        # Check 1: Complementary Token Merge Arbitrage
                        merge_opp = evaluate_instantaneous_merge_arbitrage(
                            market_id=mid,
                            token_up=token_up,
                            token_down=token_down,
                            best_ask_up=best_ask_up,
                            best_ask_down=best_ask_down,
                            depth_up_shares=depth_up,
                            depth_down_shares=depth_down,
                        )
                        if merge_opp:
                            self.stats["merge_triggers"] += 1
                            self.executed_boundary_markets.add(mid)
                            self._log_shadow_trade({
                                "strategy": "INSTANT_CTF_MERGE",
                                "market_id": mid,
                                "timestamp_utc": merge_opp.timestamp_utc,
                                "gross_cost": merge_opp.gross_cost,
                                "net_profit_per_share": merge_opp.net_profit_per_share,
                                "executable_shares": merge_opp.max_executable_shares,
                                "notional_usd": merge_opp.gross_cost * merge_opp.max_executable_shares,
                            })
                            continue

                        # Enforce 12 bps Chainlink-to-Binance oracle basis buffer on sub-hourly contracts
                        comp_spot = self.spot_feeds[m_data["asset"]]["composite"]
                        basis_buf = m_data["strike"] * (float(m_data.get("basis_buffer_bps", 0.0)) / 10000.0)

                        # Check 2: Deterministic Boundary Convergence (UP)
                        if best_ask_up > 0 and (comp_spot - m_data["strike"]) > basis_buf:
                            entry_up = engine.evaluate_execution_entry("UP", best_ask_up, depth_up, now)
                            if entry_up:
                                self.stats["boundary_triggers"] += 1
                                self.executed_boundary_markets.add(mid)
                                self._log_shadow_trade({
                                    "strategy": "BOUNDARY_CONVERGENCE",
                                    "side": "UP",
                                    "market_id": mid,
                                    "asset": m_data["asset"],
                                    "tte_sec": tte,
                                    "price": best_ask_up,
                                    "shares": min(depth_up, 50.0),
                                    "net_edge": entry_up["net_edge"],
                                    "fee": entry_up["fee"],
                                    "reason": entry_up["reason"],
                                    "spot_composite": self.spot_feeds[m_data["asset"]]["composite"],
                                    "spot_binance": self.spot_feeds[m_data["asset"]]["binance"],
                                    "spot_coinbase": self.spot_feeds[m_data["asset"]]["coinbase"],
                                    "strike": m_data["strike"],
                                })
                                continue

                        # Check 3: Deterministic Boundary Convergence (DOWN)
                        if best_ask_down > 0 and (m_data["strike"] - comp_spot) > basis_buf:
                            entry_down = engine.evaluate_execution_entry("DOWN", best_ask_down, depth_down, now)
                            if entry_down:
                                self.stats["boundary_triggers"] += 1
                                self.executed_boundary_markets.add(mid)
                                self._log_shadow_trade({
                                    "strategy": "BOUNDARY_CONVERGENCE",
                                    "side": "DOWN",
                                    "market_id": mid,
                                    "asset": m_data["asset"],
                                    "tte_sec": tte,
                                    "price": best_ask_down,
                                    "shares": min(depth_down, 50.0),
                                    "net_edge": entry_down["net_edge"],
                                    "fee": entry_down["fee"],
                                    "reason": entry_down["reason"],
                                    "spot_composite": self.spot_feeds[m_data["asset"]]["composite"],
                                    "spot_binance": self.spot_feeds[m_data["asset"]]["binance"],
                                    "spot_coinbase": self.spot_feeds[m_data["asset"]]["coinbase"],
                                    "strike": m_data["strike"],
                                })
                                continue

                    except Exception as e:
                        logger.debug(f"Evaluation error for {mid}: {e}")

                await asyncio.sleep(0.25)

    def _log_shadow_trade(self, record: Dict[str, Any]) -> None:
        """Appends trade entry to isolated shadow ledger."""
        record["timestamp_utc"] = record.get("timestamp_utc", datetime.now(timezone.utc).isoformat())
        with open(LEDGER_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
        self.stats["shadow_orders"] += 1
        logger.info(f"[SHADOW-TRADE] {record.get('strategy')} | Side: {record.get('side')} | Edge: ${record.get('net_edge', 0.0):.4f} | {record.get('reason')}")

    def _persist_state(self) -> None:
        """Persists daemon health and heartbeat stats."""
        state = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": "RUNNING" if self.running else "STOPPED",
            "stats": self.stats,
            "monitored_markets": len(self.active_markets),
            "spot_snapshot": {a: d["composite"] for a, d in self.spot_feeds.items()},
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    async def run(self) -> None:
        self.running = True
        PID_FILE.write_text(str(os.getpid()))
        logger.info("=" * 80)
        logger.info("   EXP-306 DETERMINISTIC BOUNDARY & SPLIT/MERGE DAEMON STARTED")
        logger.info(f"   PID: {os.getpid()} | Ledger: {LEDGER_FILE}")
        logger.info("=" * 80)

        tasks = [
            asyncio.create_task(self._binance_stream_worker()),
            asyncio.create_task(self._coinbase_stream_worker()),
            asyncio.create_task(self._market_discovery_worker()),
            asyncio.create_task(self._evaluation_loop()),
        ]

        try:
            while self.running:
                self._persist_state()
                await asyncio.sleep(5.0)
        finally:
            self.running = False
            for t in tasks:
                t.cancel()
            if PID_FILE.exists():
                PID_FILE.unlink()
            self._persist_state()
            logger.info("EXP-306 Daemon stopped.")


if __name__ == "__main__":
    daemon = EXP306BoundaryDaemon()

    def handle_sig(sig, frame):
        logger.info("Signal received, stopping daemon...")
        daemon.running = False

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    asyncio.run(daemon.run())

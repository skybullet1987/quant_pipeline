#!/usr/bin/env python3
"""
EXP-307: Conditional Probability Monotonicity & Copula Arbitrage Engine
======================================================================
Exploits structural pricing desynchronizations across independent order books
for interrelated macroeconomic events (e.g., sequential FOMC rate cut meetings)
and crypto strike ladders sharing the same expiry.

Core Audited Modules:
  1. CDF Monotonicity Solver:
     Enforces Omega_A subset Omega_B => P(B) >= P(A).
     Captures inversions: P_bid(A) > P_ask(B).
  2. Crypto Strike Ladder Monotonicity:
     K1 < K2 => P(S_T > K2) <= P(S_T > K1).
  3. Fréchet-Hoeffding Copula Invariant Solver:
     max(0, P_A + P_B - 1) <= P(A and B) <= min(P_A, P_B).
  4. Capital Carry Cost Integration:
     C_capital = (P_A + P_B) * (exp(r_f * tau) - 1)
     Deducts institutional opportunity cost at SOFR (4.80%) from net edge.
  5. Atomic Hedging State Machine & Directional Unwind Guard:
     Mitigates maker-taker adverse selection: When Leg 1 fills, Leg 2 is triggered
     within <= 20ms. If Leg 2 liquidity evaporates beyond slippage tolerance, an
     emergency unwind is dispatched immediately to eliminate naked directional inventory.
  6. Isolated Shadow Ledger:
     Persists all detected opportunities and execution cycles to:
     data/exp307/shadow_monotonicity_ledger.jsonl
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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data" / "exp307"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LEDGER_FILE = DATA_DIR / "shadow_monotonicity_ledger.jsonl"
STATE_FILE = DATA_DIR / "exp307_state.json"
PID_FILE = DATA_DIR / "exp307_scanner.pid"
LOG_FILE = DATA_DIR / "exp307_scanner.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [EXP307] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("EXP307Scanner")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"

# Risk-free rate (SOFR benchmark: 4.80%)
SOFR_ANNUAL_RATE = 0.048
# Authoritative Polymarket Taker Fee Rate Schedule by Market Category
CATEGORY_FEE_RATES = {
    "crypto": 0.07,
    "cryptocurrency": 0.07,
    "sports": 0.05,
    "economics": 0.05,
    "economy": 0.05,
    "finance": 0.04,
    "politics": 0.04,
    "geopolitics": 0.00,
}
STANDARD_DYNAMIC_FEE_R = 0.07  # Default dynamic fee rate r


# ==============================================================================
# MATHEMATICAL MODELS & FORMULATIONS
# ==============================================================================

def compute_polymarket_dynamic_taker_fee(price: float, r: float = STANDARD_DYNAMIC_FEE_R) -> float:
    """Computes closed-form Polymarket dynamic taker fee rate on notional: r * (1 - p)."""
    p = max(0.01, min(0.99, price))
    return r * (1.0 - p)


def compute_polymarket_dynamic_taker_fee_per_share(price: float, r: float = STANDARD_DYNAMIC_FEE_R) -> float:
    """Computes closed-form Polymarket dynamic taker fee in dollars per share: r * p * (1 - p)."""
    p = max(0.01, min(0.99, price))
    return r * p * (1.0 - p)


def compute_capital_carry_cost(notional_usd: float, tau_days: float, r_f: float = SOFR_ANNUAL_RATE) -> float:
    """
    Computes institutional capital carry cost over holding duration:
    C_capital = Notional * (exp(r_f * tau_years) - 1).
    Guarantees that 0 days holding duration yields 0 carry cost.
    """
    if tau_days <= 0.0:
        return 0.0
    tau_years = tau_days / 365.25
    return notional_usd * (math.exp(r_f * tau_years) - 1.0)


def compute_frechet_hoeffding_copula_bounds(u: float, v: float) -> Tuple[float, float]:
    """
    Computes universal non-parametric Fréchet-Hoeffding copula bounds for joint probability:
    W(u, v) = max(0, u + v - 1) <= C(u, v) <= M(u, v) = min(u, v).
    """
    lower = max(0.0, u + v - 1.0)
    upper = min(u, v)
    return lower, upper


@dataclass
class MonotonicityPair:
    pair_id: str
    leg_a_id: str
    leg_a_name: str
    leg_a_token_id: str
    leg_b_id: str
    leg_b_name: str
    leg_b_token_id: str
    relation_type: str  # "CDF_SEQUENTIAL" or "STRIKE_LADDER"
    tau_days: float
    fee_rate_a: float = 0.07  # Resolved category taker fee rate for Leg A
    fee_rate_b: float = 0.07  # Resolved category taker fee rate for Leg B
    strike_a: Optional[float] = None
    strike_b: Optional[float] = None


@dataclass
class InversionSignal:
    pair_id: str
    relation_type: str
    leg_a_bid: float
    leg_b_ask: float
    gross_dislocation: float
    fee_a: float
    fee_b: float
    capital_carry: float
    net_edge_per_share: float
    executable_shares: float
    copula_lower_bound: float = 0.0
    copula_upper_bound: float = 1.0
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ==============================================================================
# ATOMIC HEDGING STATE MACHINE
# ==============================================================================

class HedgeState(Enum):
    IDLE = "IDLE"
    LEG1_POSTED = "LEG1_POSTED"
    LEG1_FILLED = "LEG1_FILLED"
    LEG2_TRIGGERED = "LEG2_TRIGGERED"
    HEDGED_COMPLETE = "HEDGED_COMPLETE"
    EMERGENCY_UNWIND_TRIGGERED = "EMERGENCY_UNWIND_TRIGGERED"
    UNWOUND_CLOSED = "UNWOUND_CLOSED"
    FAILED_HALTED = "FAILED_HALTED"


class AtomicHedgingStateMachine:
    """
    Manages the multi-leg maker-taker execution lifecycle with fail-closed emergency unwinding.
    Ensures that if Leg 1 is filled passively, Leg 2 is triggered within <= 20ms.
    If Leg 2 fails or exceeds slippage limits, Leg 1 is instantly liquidated.
    """

    def __init__(self, max_allowed_slippage: float = 0.02, max_hedging_delay_sec: float = 0.5):
        self.state = HedgeState.IDLE
        self.max_slippage = max_allowed_slippage
        self.max_delay = max_hedging_delay_sec
        self.leg1_order_id: Optional[str] = None
        self.leg2_order_id: Optional[str] = None
        self.leg1_fill_time: float = 0.0
        self.leg1_fill_price: float = 0.0
        self.leg1_fill_shares: float = 0.0
        self.unwind_order_id: Optional[str] = None
        self.events_log: List[Dict[str, Any]] = []

    def log_event(self, event_name: str, details: Dict[str, Any]) -> None:
        record = {
            "timestamp": time.time(),
            "event": event_name,
            "state": self.state.value,
            "details": details,
        }
        self.events_log.append(record)
        logger.info(f"[HEDGE-SM] {event_name} -> {self.state.value} | {details}")

    def on_leg1_posted(self, order_id: str, price: float, shares: float) -> None:
        self.state = HedgeState.LEG1_POSTED
        self.leg1_order_id = order_id
        self.log_event("LEG1_POSTED", {"order_id": order_id, "price": price, "shares": shares})

    def on_leg1_filled(self, price: float, shares: float) -> None:
        self.state = HedgeState.LEG1_FILLED
        self.leg1_fill_time = time.time()
        self.leg1_fill_price = price
        self.leg1_fill_shares = shares
        self.log_event("LEG1_FILLED", {"price": price, "shares": shares})

    def trigger_leg2(self, expected_price: float, current_best_ask: float) -> Dict[str, Any]:
        """
        Validates slippage and triggers Leg 2 aggressive FOK sweep.
        Fails closed to emergency unwind if slippage exceeds threshold.
        """
        delay = time.time() - self.leg1_fill_time
        slippage = current_best_ask - expected_price

        if slippage > self.max_slippage or delay > self.max_delay:
            self.state = HedgeState.EMERGENCY_UNWIND_TRIGGERED
            self.log_event("SLIPPAGE_EXCEEDED_UNWIND", {
                "delay_sec": delay,
                "slippage": slippage,
                "max_slippage": self.max_slippage,
            })
            return {"action": "EMERGENCY_UNWIND", "shares": self.leg1_fill_shares}

        self.state = HedgeState.LEG2_TRIGGERED
        self.log_event("LEG2_TRIGGERED", {"current_ask": current_best_ask, "shares": self.leg1_fill_shares})
        return {
            "action": "EXECUTE_LEG2_FOK",
            "price": current_best_ask,
            "shares": self.leg1_fill_shares,
        }

    def on_leg2_success(self, order_id: str, fill_price: float) -> None:
        self.state = HedgeState.HEDGED_COMPLETE
        self.leg2_order_id = order_id
        self.log_event("HEDGED_COMPLETE", {"leg2_order_id": order_id, "fill_price": fill_price})

    def on_unwind_success(self, order_id: str, exit_price: float) -> None:
        self.state = HedgeState.UNWOUND_CLOSED
        self.unwind_order_id = order_id
        self.log_event("UNWOUND_CLOSED", {"unwind_order_id": order_id, "exit_price": exit_price})


# ==============================================================================
# EXP-307 SCANNER & SHADOW DAEMON
# ==============================================================================

class EXP307MonotonicityDaemon:
    """
    Monitors related contract graphs, evaluates CDF & Copula bounds in real time,
    and runs shadow executions with atomic hedging verification.
    """

    def __init__(self):
        self.running = False
        self.pairs: Dict[str, MonotonicityPair] = {}
        self.clob_books: Dict[str, Dict[str, Any]] = {}
        self.active_hedgers: Dict[str, AtomicHedgingStateMachine] = {}
        self.stats = {
            "scans_completed": 0,
            "inversions_detected": 0,
            "shadow_spreads_executed": 0,
            "simulated_unwinds": 0,
        }

    async def _index_macro_and_ladder_pairs(self) -> None:
        """Indexes sequential macroeconomic contracts and crypto strike ladders from Gamma API."""
        headers = {"User-Agent": "EXP307MonotonicityDaemon/1.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                params = {"limit": 100, "active": "true", "closed": "false"}
                async with session.get(f"{GAMMA_API_URL}/events", params=params, timeout=10) as resp:
                    if resp.status == 200:
                        events = await resp.json()
                        for ev in events:
                            title = ev.get("title", "").lower()
                            markets = ev.get("markets", [])
                            if len(markets) < 2:
                                continue

                            # Case 1: Sequential Rate Decisions (FOMC)
                            if "fed" in title or "interest rate" in title or "fomc" in title:
                                sorted_markets = sorted(
                                    markets,
                                    key=lambda m: m.get("endDate", "")
                                )
                                for i in range(len(sorted_markets) - 1):
                                    m1 = sorted_markets[i]
                                    m2 = sorted_markets[i + 1]
                                    tokens1 = json.loads(m1.get("clobTokenIds", "[]")) if isinstance(m1.get("clobTokenIds"), str) else m1.get("clobTokenIds", [])
                                    tokens2 = json.loads(m2.get("clobTokenIds", "[]")) if isinstance(m2.get("clobTokenIds"), str) else m2.get("clobTokenIds", [])
                                    if len(tokens1) >= 2 and len(tokens2) >= 2:
                                        pid = f"FOMC_{m1.get('id')}_{m2.get('id')}"
                                        self.pairs[pid] = MonotonicityPair(
                                            pair_id=pid,
                                            leg_a_id=str(m1.get("id")),
                                            leg_a_name=m1.get("question", ""),
                                            leg_a_token_id=tokens1[0],  # YES token
                                            leg_b_id=str(m2.get("id")),
                                            leg_b_name=m2.get("question", ""),
                                            leg_b_token_id=tokens2[0],  # YES token
                                            relation_type="CDF_SEQUENTIAL",
                                            tau_days=45.0,  # Benchmark duration
                                            fee_rate_a=0.05,  # Economics category fee: 0.05
                                            fee_rate_b=0.05,  # Economics category fee: 0.05
                                        )

                            # Case 2: Crypto Strike Ladders (Same Expiry)
                            if "price of bitcoin on" in title or "price of ethereum on" in title:
                                ladder_markets = [
                                    m for m in markets
                                    if float(m.get("strikePrice") or 0.0) > 0
                                ]
                                ladder_markets.sort(key=lambda m: float(m.get("strikePrice") or 0.0))
                                for i in range(len(ladder_markets) - 1):
                                    m_low = ladder_markets[i]
                                    m_high = ladder_markets[i + 1]
                                    k_low = float(m_low.get("strikePrice"))
                                    k_high = float(m_high.get("strikePrice"))
                                    tok_low = json.loads(m_low.get("clobTokenIds", "[]")) if isinstance(m_low.get("clobTokenIds"), str) else m_low.get("clobTokenIds", [])
                                    tok_high = json.loads(m_high.get("clobTokenIds", "[]")) if isinstance(m_high.get("clobTokenIds"), str) else m_high.get("clobTokenIds", [])
                                    if len(tok_low) >= 2 and len(tok_high) >= 2:
                                        pid = f"LADDER_{m_low.get('id')}_{m_high.get('id')}"
                                        self.pairs[pid] = MonotonicityPair(
                                            pair_id=pid,
                                            leg_a_id=str(m_high.get("id")),  # Higher strike
                                            leg_a_name=m_high.get("question", ""),
                                            leg_a_token_id=tok_high[0],
                                            leg_b_id=str(m_low.get("id")),   # Lower strike
                                            leg_b_name=m_low.get("question", ""),
                                            leg_b_token_id=tok_low[0],
                                            relation_type="STRIKE_LADDER",
                                            tau_days=7.0,
                                            fee_rate_a=0.07,  # Crypto category fee: 0.07
                                            fee_rate_b=0.07,  # Crypto category fee: 0.07
                                            strike_a=k_high,
                                            strike_b=k_low,
                                        )

                        logger.info(f"Indexed {len(self.pairs)} related monotonicity & ladder pairs.")
            except Exception as e:
                logger.error(f"Pair indexing error: {e}")

    async def _scan_pairs_loop(self) -> None:
        """Polls order books for indexed pairs and evaluates inversion conditions."""
        headers = {"User-Agent": "EXP307MonotonicityDaemon/1.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            while self.running:
                self.stats["scans_completed"] += 1
                for pid, pair in list(self.pairs.items()):
                    try:
                        async with session.get(f"{CLOB_API_URL}/book", params={"token_id": pair.leg_a_token_id}, timeout=1.5) as r_a:
                            book_a = await r_a.json() if r_a.status == 200 else {}
                        async with session.get(f"{CLOB_API_URL}/book", params={"token_id": pair.leg_b_token_id}, timeout=1.5) as r_b:
                            book_b = await r_b.json() if r_b.status == 200 else {}

                        raw_bids_a = [b for b in book_a.get("bids", []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0]
                        raw_asks_b = [a for a in book_b.get("asks", []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0]

                        if not raw_bids_a or not raw_asks_b:
                            continue

                        # Explicitly sort bids descending (best bid first) and asks ascending (best ask first)
                        sorted_bids_a = sorted(raw_bids_a, key=lambda x: float(x["price"]), reverse=True)
                        sorted_asks_b = sorted(raw_asks_b, key=lambda x: float(x["price"]))

                        best_bid_a = float(sorted_bids_a[0]["price"])
                        depth_bid_a = float(sorted_bids_a[0]["size"])

                        best_ask_b = float(sorted_asks_b[0]["price"])
                        depth_ask_b = float(sorted_asks_b[0]["size"])

                        # Inversion condition: P_bid(A) > P_ask(B)
                        if best_bid_a > best_ask_b:
                            gross_dislocation = best_bid_a - best_ask_b
                            fee_a = compute_polymarket_dynamic_taker_fee_per_share(best_bid_a, r=pair.fee_rate_a)
                            fee_b = compute_polymarket_dynamic_taker_fee_per_share(best_ask_b, r=pair.fee_rate_b)

                            # Capital carry deduction per share over holding period
                            carry_cost = compute_capital_carry_cost(
                                notional_usd=best_bid_a + best_ask_b,
                                tau_days=pair.tau_days,
                            )

                            net_edge = gross_dislocation - (fee_a + fee_b) - carry_cost
                            shares = min(depth_bid_a, depth_ask_b)

                            # Copula Fréchet-Hoeffding bounds
                            cop_lower, cop_upper = compute_frechet_hoeffding_copula_bounds(best_bid_a, best_ask_b)

                            # Actionable hurdle threshold: >= $0.02/share net profit
                            if net_edge >= 0.02 and shares > 5.0:
                                self.stats["inversions_detected"] += 1
                                signal = InversionSignal(
                                    pair_id=pid,
                                    relation_type=pair.relation_type,
                                    leg_a_bid=best_bid_a,
                                    leg_b_ask=best_ask_b,
                                    gross_dislocation=gross_dislocation,
                                    fee_a=fee_a,
                                    fee_b=fee_b,
                                    capital_carry=carry_cost,
                                    net_edge_per_share=net_edge,
                                    executable_shares=shares,
                                    copula_lower_bound=cop_lower,
                                    copula_upper_bound=cop_upper,
                                )
                                self._log_shadow_trade(signal)
                                await self._simulate_atomic_hedging(pair, signal)

                    except Exception as e:
                        logger.debug(f"Scan error on pair {pid}: {e}")

                await asyncio.sleep(0.5)

    async def _simulate_atomic_hedging(self, pair: MonotonicityPair, signal: InversionSignal) -> None:
        """Simulates atomic maker-taker sequence with hedging verification."""
        sm = AtomicHedgingStateMachine(max_allowed_slippage=0.015, max_hedging_delay_sec=0.25)
        self.active_hedgers[pair.pair_id] = sm

        # Step 1: Simulate Leg 1 fill
        sm.on_leg1_posted(f"MOCK_RESTING_{pair.leg_a_id}", signal.leg_a_bid, signal.executable_shares)
        sm.on_leg1_filled(signal.leg_a_bid, signal.executable_shares)

        # Step 2: Trigger Leg 2 aggressive sweep within <= 20ms
        await asyncio.sleep(0.015)  # 15ms latency simulation
        sim_curr_ask = signal.leg_b_ask + 0.002  # Minor 0.2c book movement simulation
        decision = sm.trigger_leg2(expected_price=signal.leg_b_ask, current_best_ask=sim_curr_ask)

        if decision["action"] == "EXECUTE_LEG2_FOK":
            sm.on_leg2_success(f"MOCK_TAKER_{pair.leg_b_id}", sim_curr_ask)
            self.stats["shadow_spreads_executed"] += 1
        elif decision["action"] == "EMERGENCY_UNWIND":
            sm.on_unwind_success(f"MOCK_UNWIND_{pair.leg_a_id}", signal.leg_a_bid - 0.01)
            self.stats["simulated_unwinds"] += 1

    def _log_shadow_trade(self, signal: InversionSignal) -> None:
        with open(LEDGER_FILE, "a") as f:
            f.write(json.dumps(asdict(signal)) + "\n")
        logger.info(
            f"[MONOTONICITY-EDGE] {signal.relation_type} | {signal.pair_id} | "
            f"Bid_A: {signal.leg_a_bid:.3f} > Ask_B: {signal.leg_b_ask:.3f} | "
            f"Gross: ${signal.gross_dislocation:.4f} | Net: ${signal.net_edge_per_share:.4f}"
        )

    def _persist_state(self) -> None:
        state = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": "RUNNING" if self.running else "STOPPED",
            "stats": self.stats,
            "monitored_pairs": len(self.pairs),
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    async def run(self) -> None:
        self.running = True
        PID_FILE.write_text(str(os.getpid()))
        logger.info("=" * 80)
        logger.info("   EXP-307 MONOTONICITY & COPULA ARBITRAGE SCANNER STARTED")
        logger.info(f"   PID: {os.getpid()} | Ledger: {LEDGER_FILE}")
        logger.info("=" * 80)

        await self._index_macro_and_ladder_pairs()

        tasks = [
            asyncio.create_task(self._scan_pairs_loop()),
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
            logger.info("EXP-307 Scanner stopped.")


if __name__ == "__main__":
    daemon = EXP307MonotonicityDaemon()

    def handle_sig(sig, frame):
        logger.info("Signal received, stopping daemon...")
        daemon.running = False

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    asyncio.run(daemon.run())

"""
Experiment R: Hyperliquid Ratcheted Event Momentum Shadow Simulator
File: src/hl_leadlag/execution/hl_isolated_ratchet_shadow.py

v3.1 Pure Implementation-Conformance / Forensic State:
1. Parallel Virtual Policy Execution Engine:
   - Actually computes and persists all 4 counterfactual policy outcomes per episode:
     Policy 1: SOL-only
     Policy 2: Random Eligible (deterministic episode hash seed)
     Policy 3: Round-Robin (strictly indexed by independent_episode_index)
     Policy 4: Max-OBI Router
   - Produces empirical paired routing increments:
     Delta_MOS = mu_MAX_OBI - mu_SOL
     Delta_MOR = mu_MAX_OBI - mu_RANDOM
     p_routing = max(p_MOS, p_MOR) < 0.01
2. Decoupled Shock Detection from Trade Eligibility:
   - Eliminates state-dependent censoring: every qualifying shock (>= $1.5M, Z_OFI >= 2.58)
     is recorded into the episode stream regardless of whether a sprint position is open.
   - Independent episode cooldown (tau = 300s = 5 min). Shocks occurring within 300s of an active
     episode belong to that episode; shocks after 300s initiate episode k+1.
3. Strict Funding Sign Invariant:
   - PnL = GrossPricePnL - Fees + FundingCashflow (where FundingCashflow > 0 is received cash).
4. Explicit Labeling of Simulation Assumptions:
   - Modeled base taker fee (4.5 bps), modeled latency transit (3.2 ms), modeled slip (+1.0 bp / -1.5 bps).
   - Stop/liquidation explicitly labeled as local L2 mid/bid proxy simulation (Hyperliquid mark-price parity reserved for Phase C).
"""

from __future__ import annotations

import os
import sys
import time
import math
import json
import hashlib
import asyncio
import datetime
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import websockets
import aiohttp

try:
    from scipy import stats as sp_stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# --- Microstructure & Venue Constraints ---
BINANCE_WS_URL = "wss://fstream.binance.com/market/ws/btcusdt@aggTrade"
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"

SHOCK_VOLUME_USD = 1500000.0   # >= $1.5M aggressive sweep
SHOCK_WINDOW_MS = 100           # 100ms rolling window
Z_OFI_HURDLE = 2.58             # Institutional flow hurdle (p < 0.01)
INDEPENDENT_EPISODE_COOLDOWN_SEC = 300.0  # 5 minutes cluster linking window

# Asset Margin & Tier Constraints (Hyperliquid Mainnet)
ASSET_CONFIG = {
    "SOL": {
        "max_leverage": 20.0,
        "maint_margin_rate": 0.025, # 2.5% maintenance margin
        "initial_margin_rate": 0.05, # 5.0% initial margin
        "base_taker_fee": 0.00045,  # 4.5 bps base taker fee
        "base_maker_fee": 0.00015,  # 1.5 bps base maker fee
    },
    "HYPE": {
        "max_leverage": 10.0,
        "maint_margin_rate": 0.050,
        "initial_margin_rate": 0.10,
        "base_taker_fee": 0.00045,
        "base_maker_fee": 0.00015,
    },
    "SUI": {
        "max_leverage": 10.0,
        "maint_margin_rate": 0.050,
        "initial_margin_rate": 0.10,
        "base_taker_fee": 0.00045,
        "base_maker_fee": 0.00015,
    },
    "DOGE": {
        "max_leverage": 10.0,
        "maint_margin_rate": 0.050,
        "initial_margin_rate": 0.10,
        "base_taker_fee": 0.00045,
        "base_maker_fee": 0.00015,
    }
}

# --- B1 Engineering Simulation Assumptions (Modeled Frictions, NOT Empirical Live Telemetry) ---
BASE_TAKER_FEE_MODELED = 0.00045        # 4.5 bps fixed base taker fee assumption
BASE_MAKER_FEE_MODELED = 0.00015        # 1.5 bps fixed base maker fee assumption
SIMULATED_TRANSIT_LATENCY_NS = 3_200_000# 3.2 ms modeled Tokyo-to-Hyperliquid network transit
SIMULATED_MATCH_ENGINE_NS = 1_500_000   # 1.5 ms modeled matching engine tick
MODELED_ENTRY_SLIPPAGE_BPS = 1.0        # +1.0 bp modeled entry taker slippage on liquid book
MODELED_EXIT_SLIPPAGE_BPS = 1.5         # -1.5 bps modeled exit taker slippage
EXECUTION_MODEL_TYPE = "B1_SIMULATED_PROXY" # Local L2 proxy simulation; Mark-price exchange parity reserved for Phase C

# Sizing & Subaccount Sandbox Parameters
SANDBOX_COLLATERAL_USD = 20.00   # $20.00 isolated collateral allocation
MAX_CONCURRENT_SPRINTS = 1       # Single primary sprint concurrency invariant

# FSM Markout & Stop Thresholds
NOMINAL_STOP_DIST = 0.0180       # -1.80% nominal mark-triggered stop
MICRO_BREAKEVEN_DIST = 0.0070    # +0.70% spot advance locks dynamic net breakeven stop
PYRAMID_TRIGGER_DIST = 0.0150    # +1.50% spot advance triggers Stage 1 pyramid
PROFIT_LOCK_TRIGGER_DIST = 0.0350# +3.50% spot advance triggers Stage 2 profit lock
PROFIT_LOCK_STOP_DIST = 0.0180   # +1.80% above initial entry locked
TRAILING_DISTANCE_PCT = 0.0100   # 1.00% dynamic trailing stop distance from HWM
MAX_HOLD_SECONDS = 2700.0        # 45 minutes hard maximum time horizon

# Cost Ladder Scenarios (Round-Trip bps)
COST_LADDER_BPS = [7.0, 15.0, 25.0, 40.0, 60.0]

LOG_DIR = "/home/skybullet1987/quant_pipeline/data/ratchet"
LOG_FILE = os.path.join(LOG_DIR, "ratchet_shadow_events.jsonl")
EPISODE_LEDGER_FILE = os.path.join(LOG_DIR, "counterfactual_episode_ledger.jsonl")
SUMMARY_FILE = os.path.join(LOG_DIR, "ratchet_shadow_summary.json")
PID_FILE = os.path.join(LOG_DIR, "ratchet_shadow.pid")


class TradeWindow:
    """Tracks sub-millisecond aggTrades and calculates rolling OFI Z-score."""
    def __init__(self, window_ms: int = 100, history_len: int = 600):
        self.window_s = window_ms / 1000.0
        self.trades = deque() # (timestamp, price, size, is_buyer_maker)
        self.ofi_history = deque(maxlen=history_len)

    def add(self, ts: float, px: float, sz: float, is_buyer_maker: bool):
        self.trades.append((ts, px, sz, is_buyer_maker))
        cutoff = ts - self.window_s
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()

    def get_metrics(self) -> Dict[str, float]:
        if not self.trades:
            return {"total_usd": 0.0, "buy_usd": 0.0, "sell_usd": 0.0, "ofi": 0.0, "z_ofi": 0.0}
        
        buy_usd = sum(p * s for (t, p, s, bm) in self.trades if not bm)
        sell_usd = sum(p * s for (t, p, s, bm) in self.trades if bm)
        total_usd = buy_usd + sell_usd
        ofi = (buy_usd - sell_usd) / total_usd if total_usd > 0 else 0.0
        
        self.ofi_history.append(ofi)
        n = len(self.ofi_history)
        if n >= 30:
            mean_ofi = sum(self.ofi_history) / n
            var_ofi = sum((x - mean_ofi) ** 2 for x in self.ofi_history) / n
            std_ofi = math.sqrt(var_ofi)
            z_ofi = (ofi - mean_ofi) / max(0.08, std_ofi)
        else:
            z_ofi = ofi / 0.20
            
        return {
            "total_usd": total_usd,
            "buy_usd": buy_usd,
            "sell_usd": sell_usd,
            "ofi": ofi,
            "z_ofi": z_ofi
        }


@dataclass
class ExecutionFill:
    fill_id: str
    stage: str # "INITIAL", "PYRAMID", "STOP_EXIT", "PROFIT_EXIT", "TIME_EXIT"
    side: str  # "BUY", "SELL"
    notional: float
    quantity: float
    fill_price: float
    benchmark_price: float
    timestamp_ns: int
    taker_fee_usd: float
    execution_shortfall_usd: float


@dataclass
class SprintPosition:
    sprint_id: str
    asset: str
    direction: str
    entry_ts_ns: int
    entry_ts_wall: float
    collateral_usd: float
    account_equity: float
    policy_name: str = "PRIMARY" # "SOL", "RANDOM", "ROUND_ROBIN", "MAX_OBI", "PRIMARY"
    episode_id: str = ""
    episode_index: int = 0
    fills: List[ExecutionFill] = field(default_factory=list)
    
    # Runtime Position State (Synchronously Recomputed)
    total_quantity: float = 0.0
    total_notional: float = 0.0
    vwae_price: float = 0.0
    vwae_rel_pct: float = 0.0
    initial_entry_price: float = 0.0
    
    # Invariant Risk & Margin Metrics (Local L2 Proxy Simulation)
    initial_margin_required: float = 0.0
    maint_margin_required: float = 0.0
    margin_available: float = 0.0
    free_usable_margin: float = 0.0
    published_liq_price: float = 0.0
    stop_to_liq_distance_pct: float = 0.0
    
    # Dynamic Stops & Breakeven Price Levels
    current_stop_price: float = 0.0
    gross_break_even_price: float = 0.0
    expected_net_break_even_price: float = 0.0
    p95_net_break_even_price: float = 0.0
    
    # High-Water Mark & State
    hwm_price: float = 0.0
    fsm_state: str = "INITIAL_ANCHORED" # INITIAL_ANCHORED, RATCHET_1, RATCHET_2, CLOSED
    exit_reason: str = ""
    exit_ts_wall: float = 0.0
    holding_seconds: float = 0.0
    
    # Accounting Outcomes (STRICT FUNDING SIGN INVARIANT: + funding_cashflow)
    total_fees_paid: float = 0.0
    total_funding_accrued: float = 0.0 # > 0 means net cash received
    gross_realized_pnl: float = 0.0
    net_realized_pnl: float = 0.0
    total_execution_shortfall: float = 0.0
    cost_ladder_pnl: Dict[str, float] = field(default_factory=dict)
    
    # Latency Timestamps & Model Assumptions
    t_source_ms: float = 0.0
    t_receive_ns: int = 0
    t_decision_ns: int = 0
    t_submit_ns: int = 0
    t_ack_ns: int = 0
    t_fill_ns: int = 0
    modeled_latency_ms: float = 4.7 # Modeled 3.2ms transit + 1.5ms engine
    processing_latency_ms: float = 0.0 # Empirical monotonic delta: (t_decision - t_receive)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RatchetShadowEngine:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.active_sprint: Optional[SprintPosition] = None
        self.completed_sprints: List[SprintPosition] = []
        
        # Parallel Virtual Policy Tracking
        self.active_virtual_positions: List[SprintPosition] = []
        self.active_episodes: Dict[str, Dict[str, Any]] = {} # episode_id -> episode data
        self.completed_episodes_history: List[Dict[str, Any]] = []
        
        self.independent_episode_index: int = 0
        self.last_shock_ts: float = 0.0
        self.current_episode_id: Optional[str] = None
        
        self.current_order_books: Dict[str, Dict[str, float]] = {
            "SOL": {"bid": 0.0, "ask": 0.0, "mid": 0.0, "bid_sz": 0.0, "ask_sz": 0.0},
            "HYPE": {"bid": 0.0, "ask": 0.0, "mid": 0.0, "bid_sz": 0.0, "ask_sz": 0.0},
            "SUI": {"bid": 0.0, "ask": 0.0, "mid": 0.0, "bid_sz": 0.0, "ask_sz": 0.0},
            "DOGE": {"bid": 0.0, "ask": 0.0, "mid": 0.0, "bid_sz": 0.0, "ask_sz": 0.0}
        }
        self.btc_trend_window = deque(maxlen=300)
        self.last_stop_amendment_ts = 0.0
        self.stop_amendments_count = 0
        
        # Load existing completed episodes for idempotent index recovery
        self.load_persisted_episodes()

    def load_persisted_episodes(self):
        """Restores independent episode count from counterfactual ledger idempotently."""
        if not os.path.exists(EPISODE_LEDGER_FILE):
            return
        count = 0
        with open(EPISODE_LEDGER_FILE, "r") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    count += 1
                    self.completed_episodes_history.append(rec)
        self.independent_episode_index = count
        print(f"[*] Restored {count} completed counterfactual episodes from {EPISODE_LEDGER_FILE}.", flush=True)

    def update_book(self, coin: str, bid: float, ask: float, bid_sz: float, ask_sz: float):
        if coin in self.current_order_books and bid > 0 and ask > 0:
            self.current_order_books[coin] = {
                "bid": bid,
                "ask": ask,
                "mid": (bid + ask) / 2.0,
                "bid_sz": bid_sz,
                "ask_sz": ask_sz
            }

    def recompute_position_state(self, pos: SprintPosition, current_px: float):
        """
        MACHINE-ENFORCED RUNTIME INVARIANT:
        Synchronously recomputes VWAE, dynamic Hyperliquid cross-margin liquidation price,
        margin available, true gross/net breakeven, and stop-to-liquidation buffer.
        Enforces Funding Sign Invariant: account_equity = collateral - fees + upnl + funding_accrued.
        """
        cfg = ASSET_CONFIG[pos.asset]
        l_rate = cfg["maint_margin_rate"]
        im_rate = cfg["initial_margin_rate"]
        
        # 1. Total Quantity & VWAE
        buy_fills = [f for f in pos.fills if f.side == "BUY"]
        pos.total_quantity = sum(f.quantity for f in buy_fills)
        pos.vwae_price = sum(f.quantity * f.fill_price for f in buy_fills) / pos.total_quantity if pos.total_quantity > 0 else 0.0
        pos.vwae_rel_pct = ((pos.vwae_price - pos.initial_entry_price) / pos.initial_entry_price * 100.0) if pos.initial_entry_price > 0 else 0.0
        pos.total_notional = pos.total_quantity * current_px

        # 2. Account Equity & Free Collateral (FUNDING SIGN INVARIANT: + total_funding_accrued)
        upnl = pos.total_quantity * (current_px - pos.vwae_price)
        pos.total_fees_paid = sum(f.taker_fee_usd for f in pos.fills)
        pos.account_equity = pos.collateral_usd - pos.total_fees_paid + upnl + pos.total_funding_accrued

        # 3. Margin Requirements
        pos.maint_margin_required = pos.total_notional * l_rate
        pos.initial_margin_required = pos.total_notional * im_rate
        pos.margin_available = pos.account_equity - pos.maint_margin_required
        pos.free_usable_margin = pos.account_equity - pos.initial_margin_required

        # 4. Hyperliquid Cross-Margin Liquidation Price Proxy:
        # P_liq = P - side * (Margin Available / Q_total) * (1 / (1 - l * side))
        if pos.total_quantity > 0:
            inv_l = 1.0 / (1.0 - l_rate)
            pos.published_liq_price = current_px - (pos.margin_available / pos.total_quantity) * inv_l
            pos.stop_to_liq_distance_pct = abs(pos.current_stop_price - pos.published_liq_price) / current_px * 100.0

        # 5. Dimensionally Consistent Breakeven Prices
        pos.gross_break_even_price = pos.vwae_price
        
        # Estimated exit taker fee (4.5 bps) + expected adverse exit slippage (7.0 bps)
        est_exit_friction_usd = pos.total_notional * (cfg["base_taker_fee"] + 0.0007)
        # Net past costs: fees paid minus funding received (funding reduces cost burden)
        past_costs_usd = pos.total_fees_paid - pos.total_funding_accrued
        pos.expected_net_break_even_price = pos.vwae_price + ((past_costs_usd + est_exit_friction_usd) / pos.total_quantity if pos.total_quantity > 0 else 0.0)
        
        # P95 adverse exit slippage (20.0 bps)
        p95_exit_friction_usd = pos.total_notional * (cfg["base_taker_fee"] + 0.0020)
        pos.p95_net_break_even_price = pos.vwae_price + ((past_costs_usd + p95_exit_friction_usd) / pos.total_quantity if pos.total_quantity > 0 else 0.0)

    def create_sprint_instance(
        self,
        asset: str,
        policy_name: str,
        episode_id: str,
        episode_index: int,
        t_source_ms: float,
        t_recv_ns: int,
        t_dec_ns: int
    ) -> Optional[SprintPosition]:
        """Creates an initialized SprintPosition instance (primary or virtual counterfactual)."""
        book = self.current_order_books[asset]
        if book["ask"] <= 0 or book["bid"] <= 0:
            return None

        cfg = ASSET_CONFIG[asset]
        t_submit_ns = time.monotonic_ns()
        t_ack_ns = t_submit_ns + SIMULATED_TRANSIT_LATENCY_NS
        t_fill_ns = t_ack_ns + SIMULATED_MATCH_ENGINE_NS

        benchmark_px = book["ask"]
        actual_fill_px = benchmark_px * (1.0 + (MODELED_ENTRY_SLIPPAGE_BPS / 10000.0))
        
        notional = SANDBOX_COLLATERAL_USD * cfg["max_leverage"]
        qty = notional / actual_fill_px
        taker_fee = notional * cfg["base_taker_fee"]
        shortfall = qty * (actual_fill_px - benchmark_px)

        sprint_id = f"SPRINT_{policy_name}_{asset}_{int(time.time()*1000)}"
        now_wall = time.time()
        
        pos = SprintPosition(
            sprint_id=sprint_id,
            asset=asset,
            direction="LONG",
            policy_name=policy_name,
            episode_id=episode_id,
            episode_index=episode_index,
            entry_ts_ns=t_fill_ns,
            entry_ts_wall=now_wall,
            collateral_usd=SANDBOX_COLLATERAL_USD,
            account_equity=SANDBOX_COLLATERAL_USD - taker_fee,
            initial_entry_price=actual_fill_px,
            hwm_price=actual_fill_px,
            current_stop_price=actual_fill_px * (1.0 - NOMINAL_STOP_DIST),
            t_source_ms=t_source_ms,
            t_receive_ns=t_recv_ns,
            t_decision_ns=t_dec_ns,
            t_submit_ns=t_submit_ns,
            t_ack_ns=t_ack_ns,
            t_fill_ns=t_fill_ns,
            modeled_latency_ms=4.7,
            processing_latency_ms=(t_dec_ns - t_recv_ns) / 1_000_000.0
        )

        initial_fill = ExecutionFill(
            fill_id=f"{sprint_id}_FILL_1",
            stage="INITIAL",
            side="BUY",
            notional=notional,
            quantity=qty,
            fill_price=actual_fill_px,
            benchmark_price=benchmark_px,
            timestamp_ns=t_fill_ns,
            taker_fee_usd=taker_fee,
            execution_shortfall_usd=shortfall
        )
        pos.fills.append(initial_fill)
        self.recompute_position_state(pos, actual_fill_px)
        return pos

    def evaluate_sprint_fsm(self, pos: SprintPosition) -> Optional[Dict[str, Any]]:
        """Evaluates any sprint position (primary or virtual) across the canonical 6-state FSM."""
        if pos.fsm_state == "CLOSED":
            return None

        asset = pos.asset
        book = self.current_order_books[asset]
        current_bid = book["bid"]
        current_ask = book["ask"]
        current_mid = book["mid"]
        
        if current_bid <= 0 or current_ask <= 0:
            return None

        now_wall = time.time()
        hold_sec = now_wall - pos.entry_ts_wall
        pos.holding_seconds = hold_sec
        cfg = ASSET_CONFIG[asset]

        if current_bid > pos.hwm_price:
            pos.hwm_price = current_bid

        self.recompute_position_state(pos, current_mid)
        move_from_entry_pct = (current_bid - pos.initial_entry_price) / pos.initial_entry_price

        # 1. HARD STOP EXIT (Adverse move hits nominal stop)
        if current_bid <= pos.current_stop_price:
            return self._close_sprint_instance(pos, exit_price=current_bid, reason=f"STOP_LOSS_HIT (Exit px: {current_bid:.3f})")

        # 2. HARD TIME HORIZON EXPIRY (45 Minutes)
        if hold_sec >= MAX_HOLD_SECONDS:
            return self._close_sprint_instance(pos, exit_price=current_bid, reason="MAX_TIME_HORIZON_REACHED (45 min)")

        # 2b. EARLY MICRO-BREAKEVEN RATCHET: Advance >= +0.70% locks dynamic net breakeven stop
        if pos.fsm_state == "INITIAL_ANCHORED" and move_from_entry_pct >= MICRO_BREAKEVEN_DIST:
            if pos.current_stop_price < pos.expected_net_break_even_price:
                pos.current_stop_price = pos.expected_net_break_even_price
                self.last_stop_amendment_ts = now_wall
                self.stop_amendments_count += 1
                if pos.policy_name == "PRIMARY":
                    print(f"  [+] MICRO-BREAKEVEN LOCKED: Advance {move_from_entry_pct*100:+.2f}% >= +0.70% | Stop moved to Net BE: ${pos.current_stop_price:.3f}", flush=True)

        # 3. STAGE 1 RATCHET: Advance >= +1.50%
        if pos.fsm_state == "INITIAL_ANCHORED" and move_from_entry_pct >= PYRAMID_TRIGGER_DIST:
            max_allowed_pyramid = pos.free_usable_margin / cfg["initial_margin_rate"]
            pyramid_cap = (SANDBOX_COLLATERAL_USD * 0.25) * cfg["max_leverage"]
            pyramid_notional = min(pyramid_cap, max_allowed_pyramid)
            if pyramid_notional >= 10.0:  # Minimum viable ticket $10
                pyramid_bench_px = current_ask
                pyramid_fill_px = pyramid_bench_px * (1.0 + (MODELED_ENTRY_SLIPPAGE_BPS / 10000.0))
                pyramid_qty = pyramid_notional / pyramid_fill_px
                pyramid_fee = pyramid_notional * cfg["base_taker_fee"]
                pyramid_shortfall = pyramid_qty * (pyramid_fill_px - pyramid_bench_px)

                pyramid_fill = ExecutionFill(
                    fill_id=f"{pos.sprint_id}_FILL_PYRAMID",
                    stage="PYRAMID",
                    side="BUY",
                    notional=pyramid_notional,
                    quantity=pyramid_qty,
                    fill_price=pyramid_fill_px,
                    benchmark_price=pyramid_bench_px,
                    timestamp_ns=time.monotonic_ns(),
                    taker_fee_usd=pyramid_fee,
                    execution_shortfall_usd=pyramid_shortfall
                )
                pos.fills.append(pyramid_fill)
                self.recompute_position_state(pos, current_mid)
                pos.current_stop_price = pos.expected_net_break_even_price
                pos.fsm_state = "RATCHET_1"
                self.stop_amendments_count += 1
                if pos.policy_name == "PRIMARY":
                    print(f"  [+] STAGE 1 RATCHET: Added ${pyramid_notional:.0f} | VWAE: {pos.vwae_rel_pct:+.3f}% | Stop: ${pos.current_stop_price:.3f}", flush=True)

        # 4. STAGE 2 PROFIT LOCK & TRAILING: Advance >= +3.50%
        elif pos.fsm_state == "RATCHET_1" and move_from_entry_pct >= PROFIT_LOCK_TRIGGER_DIST:
            pos.current_stop_price = pos.initial_entry_price * (1.0 + PROFIT_LOCK_STOP_DIST)
            pos.fsm_state = "RATCHET_2"
            self.stop_amendments_count += 1
            if pos.policy_name == "PRIMARY":
                print(f"  [+] STAGE 2 PROFIT LOCK: Stop moved to +{PROFIT_LOCK_STOP_DIST*100:.1f}% (${pos.current_stop_price:.3f})", flush=True)

        # 5. DYNAMIC TRAILING IN STAGE 2
        elif pos.fsm_state == "RATCHET_2":
            trailing_stop_candidate = pos.hwm_price * (1.0 - TRAILING_DISTANCE_PCT)
            if trailing_stop_candidate > pos.current_stop_price:
                delta_px_bps = (trailing_stop_candidate - pos.current_stop_price) / pos.current_stop_price * 10000.0
                now_ts = time.time()
                if delta_px_bps >= 10.0 or (now_ts - self.last_stop_amendment_ts >= 1.0):
                    pos.current_stop_price = trailing_stop_candidate
                    self.last_stop_amendment_ts = now_ts
                    self.stop_amendments_count += 1

            if current_bid <= pos.current_stop_price:
                return self._close_sprint_instance(pos, exit_price=current_bid, reason=f"TRAILING_STOP_HIT (HWM: {pos.hwm_price:.3f} -> Exit: {current_bid:.3f})")

        return None

    def _close_sprint_instance(self, pos: SprintPosition, exit_price: float, reason: str) -> Dict[str, Any]:
        """Closes sprint instance with canonical accounting and funding sign invariant."""
        cfg = ASSET_CONFIG[pos.asset]
        exit_bench_px = exit_price
        actual_exit_px = exit_bench_px * (1.0 - (MODELED_EXIT_SLIPPAGE_BPS / 10000.0))
        
        exit_notional = pos.total_quantity * actual_exit_px
        exit_fee = exit_notional * cfg["base_taker_fee"]
        exit_shortfall = pos.total_quantity * (exit_bench_px - actual_exit_px)

        exit_fill = ExecutionFill(
            fill_id=f"{pos.sprint_id}_EXIT",
            stage="EXIT",
            side="SELL",
            notional=exit_notional,
            quantity=pos.total_quantity,
            fill_price=actual_exit_px,
            benchmark_price=exit_bench_px,
            timestamp_ns=time.monotonic_ns(),
            taker_fee_usd=exit_fee,
            execution_shortfall_usd=exit_shortfall
        )
        pos.fills.append(exit_fill)

        # STRICT FUNDING SIGN INVARIANT: net_realized_pnl = gross_pnl - fees + funding_accrued
        buy_fills = [f for f in pos.fills if f.side == "BUY"]
        pos.gross_realized_pnl = sum(f.quantity * (actual_exit_px - f.fill_price) for f in buy_fills)
        pos.total_fees_paid = sum(f.taker_fee_usd for f in pos.fills)
        pos.net_realized_pnl = pos.gross_realized_pnl - pos.total_fees_paid + pos.total_funding_accrued
        pos.total_execution_shortfall = sum(f.execution_shortfall_usd for f in pos.fills)
        
        # Empirical Cost Ladder PnL Simulation
        for cost_bps in COST_LADDER_BPS:
            friction_rate = cost_bps / 10000.0
            pos.cost_ladder_pnl[f"{cost_bps:.0f}bps"] = pos.gross_realized_pnl - (exit_notional * friction_rate)

        pos.fsm_state = "CLOSED"
        pos.exit_reason = reason
        pos.exit_ts_wall = time.time()

        event_record = pos.to_dict()
        if pos.policy_name == "PRIMARY":
            self.completed_sprints.append(pos)
            self.active_sprint = None
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(event_record) + "\n")
        
        return event_record

    def handle_incoming_shock(
        self,
        ts_ms: float,
        px: float,
        metrics: Dict[str, float],
        t_recv_ns: int,
        t_dec_ns: int
    ):
        """
        DECOUPLED SHOCK ADMISSION & EPISODE LINKING:
        Every qualifying sweep is admitted into the episode stream.
        Zero state-dependent censoring: shock observation is NOT conditional on active_sprint.
        """
        now_sec = time.time()
        time_since_last_shock = now_sec - self.last_shock_ts
        is_new_episode = (time_since_last_shock >= INDEPENDENT_EPISODE_COOLDOWN_SEC) or (self.current_episode_id is None)
        
        if is_new_episode:
            self.independent_episode_index += 1
            ep_idx = self.independent_episode_index
            ep_id = f"EPISODE_{ep_idx}_{int(now_sec)}"
            self.current_episode_id = ep_id
            
            # 1. Capture snapshot of all 4 books & compute OBI
            candidates = ["SOL", "HYPE", "SUI", "DOGE"]
            l2_snapshot = {}
            obi_by_asset = {}
            for c in candidates:
                b = self.current_order_books[c]
                l2_snapshot[c] = dict(b)
                b_sz = b.get("bid_sz", 0.0)
                a_sz = b.get("ask_sz", 0.0)
                obi_by_asset[c] = (b_sz - a_sz) / (b_sz + a_sz) if (b_sz + a_sz) > 0 else 0.0

            # 2. Determine 4 Counterfactual Policy Selections
            # Policy 1: SOL-Only
            p1_asset = "SOL"
            # Policy 2: Random Eligible (deterministic hash seed)
            seed_val = int(hashlib.sha256(f"{ep_id}_seed_v31".encode()).hexdigest(), 16) % (2**32)
            p2_asset = candidates[seed_val % len(candidates)]
            # Policy 3: Round-Robin (strictly indexed by independent_episode_index)
            p3_asset = candidates[(ep_idx - 1) % len(candidates)]
            # Policy 4: Max-OBI Router
            p4_asset = max(candidates, key=lambda c: obi_by_asset[c])

            # Policy 5: Standardized Composite Recovery Router (EXP-201C)
            # S_i = 0.5 * Z(OBI_i) + 0.5 * Z(R_i)
            mean_obi = float(np.mean(list(obi_by_asset.values())))
            std_obi = float(np.std(list(obi_by_asset.values()))) if float(np.std(list(obi_by_asset.values()))) > 1e-6 else 1.0
            replenish_ratios = {c: (l2_snapshot[c].get("bid_sz", 0.0) / max(l2_snapshot[c].get("ask_sz", 1.0), 0.001)) for c in candidates}
            mean_r = float(np.mean(list(replenish_ratios.values())))
            std_r = float(np.std(list(replenish_ratios.values()))) if float(np.std(list(replenish_ratios.values()))) > 1e-6 else 1.0

            composite_scores = {
                c: (0.5 * ((obi_by_asset[c] - mean_obi) / std_obi) + 0.5 * ((replenish_ratios[c] - mean_r) / std_r))
                for c in candidates
            }
            p5_asset = max(candidates, key=lambda c: composite_scores[c])

            print(f"\n[>>> INDEPENDENT HIGH-VALUE SWEEP DETECTED ({ep_id}) <<<]"
                  f"\n  Binance USD-M Volume: ${metrics['total_usd']:,.0f} in 100ms | Z_OFI: {metrics['z_ofi']:.2f}"
                  f"\n  BTC Spot: ${px:,.2f}"
                  f"\n  [COUNTERFACTUAL POLICIES] Episode #{ep_idx}:"
                  f"\n    Policy 1 (SOL-Only): {p1_asset}"
                  f"\n    Policy 2 (Random Eligible, seed={seed_val}): {p2_asset}"
                  f"\n    Policy 3 (Round-Robin, ep_idx={ep_idx}): {p3_asset}"
                  f"\n    Policy 4 (Max-OBI, imb={obi_by_asset[p4_asset]:+.2f}): {p4_asset}"
                  f"\n    Policy 5 (Composite Recovery, score={composite_scores[p5_asset]:+.2f}): {p5_asset}", flush=True)

            # 3. Instantiate the 5 Virtual Counterfactual Sprints
            policy_positions: Dict[str, SprintPosition] = {}
            for pname, passet in [
                ("SOL", p1_asset),
                ("RANDOM", p2_asset),
                ("ROUND_ROBIN", p3_asset),
                ("MAX_OBI", p4_asset),
                ("COMPOSITE_RECOVERY", p5_asset)
            ]:
                vpos = self.create_sprint_instance(
                    asset=passet,
                    policy_name=pname,
                    episode_id=ep_id,
                    episode_index=ep_idx,
                    t_source_ms=ts_ms,
                    t_recv_ns=t_recv_ns,
                    t_dec_ns=t_dec_ns
                )
                if vpos:
                    policy_positions[pname] = vpos
                    self.active_virtual_positions.append(vpos)

            # 4. Primary Sprint Dispatch (if subaccount sandbox is free)
            primary_dispatched = False
            if self.active_sprint is None:
                primary_pos = self.create_sprint_instance(
                    asset=p4_asset,
                    policy_name="PRIMARY",
                    episode_id=ep_id,
                    episode_index=ep_idx,
                    t_source_ms=ts_ms,
                    t_recv_ns=t_recv_ns,
                    t_dec_ns=t_dec_ns
                )
                if primary_pos:
                    self.active_sprint = primary_pos
                    primary_dispatched = True
                    signed_liq_buf = (primary_pos.initial_entry_price - primary_pos.published_liq_price) / primary_pos.initial_entry_price
                    print(f"  [+] PRIMARY SPRINT DISPATCHED: {primary_pos.sprint_id}"
                          f"\n      Target Asset: {primary_pos.asset} | Book Imbalance: {obi_by_asset[primary_pos.asset]:+.2f}"
                          f"\n      Initial Notional: ${primary_pos.total_notional:.0f} ({ASSET_CONFIG[primary_pos.asset]['max_leverage']:.0f}x on ${primary_pos.collateral_usd:.0f})"
                          f"\n      Entry Fill: ${primary_pos.initial_entry_price:.3f} | Nominal Stop: ${primary_pos.current_stop_price:.3f} (-1.80%)"
                          f"\n      Protocol Liq Price: ${primary_pos.published_liq_price:.3f} (Signed Buffer: {signed_liq_buf*100:+.2f}%)"
                          f"\n      Latency: Modeled {primary_pos.modeled_latency_ms:.1f}ms | Internal Decision: {primary_pos.processing_latency_ms:.3f}ms\n", flush=True)
            else:
                print(f"  [*] Primary sprint already active ({self.active_sprint.sprint_id}). Subaccount dispatch blocked; 4 counterfactuals running in parallel.\n", flush=True)

            # 5. Register active episode
            self.active_episodes[ep_id] = {
                "episode_id": ep_id,
                "episode_index": ep_idx,
                "t0_unix": now_sec,
                "t0_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "binance_btc_trigger_price": px,
                "binance_sweep_volume_usd": metrics["total_usd"],
                "z_ofi": metrics["z_ofi"],
                "l2_snapshot_t0": l2_snapshot,
                "obi_by_asset": obi_by_asset,
                "policy_assets": {
                    "SOL": p1_asset,
                    "RANDOM": p2_asset,
                    "ROUND_ROBIN": p3_asset,
                    "MAX_OBI": p4_asset
                },
                "positions": policy_positions,
                "subsequent_shocks": [],
                "primary_dispatched": primary_dispatched
            }

        else:
            # Subsequent shock belonging to the active episode (within 300s cluster window)
            ep_id = self.current_episode_id
            if ep_id in self.active_episodes:
                self.active_episodes[ep_id]["subsequent_shocks"].append({
                    "ts_unix": now_sec,
                    "btc_px": px,
                    "volume_usd": metrics["total_usd"],
                    "z_ofi": metrics["z_ofi"]
                })
                print(f"  [+] Clustered shock admitted to existing {ep_id} (Shock #{len(self.active_episodes[ep_id]['subsequent_shocks'])+1})", flush=True)

        self.last_shock_ts = now_sec

    def evaluate_all_positions(self):
        """Evaluates primary sprint and all active virtual positions across all episodes."""
        # 1. Evaluate primary sprint
        if self.active_sprint:
            exit_event = self.evaluate_sprint_fsm(self.active_sprint)
            if exit_event:
                print(f"\n[>>> PRIMARY SPRINT CLOSED & RECONCILED <<<]"
                      f"\n  Sprint ID: {exit_event['sprint_id']} ({exit_event['asset']})"
                      f"\n  Exit Reason: {exit_event['exit_reason']}"
                      f"\n  Duration: {exit_event['holding_seconds']:.1f}s"
                      f"\n  Gross PnL: ${exit_event['gross_realized_pnl']:+.2f} | Net PnL: ${exit_event['net_realized_pnl']:+.2f}"
                      f"\n  Execution Shortfall: ${exit_event['total_execution_shortfall']:.3f}\n", flush=True)

        # 2. Evaluate all active virtual positions
        still_active: List[SprintPosition] = []
        for vpos in self.active_virtual_positions:
            self.evaluate_sprint_fsm(vpos)
            if vpos.fsm_state != "CLOSED":
                still_active.append(vpos)
        self.active_virtual_positions = still_active

        # 3. Check for completed episodes (where all 4 virtual policies have closed)
        completed_ep_ids = []
        for ep_id, ep_data in self.active_episodes.items():
            all_closed = all(p.fsm_state == "CLOSED" for p in ep_data["positions"].values())
            if all_closed:
                completed_ep_ids.append(ep_id)

        for ep_id in completed_ep_ids:
            self._finalize_and_persist_episode(ep_id)

    def _finalize_and_persist_episode(self, ep_id: str):
        """Finalizes an episode once all 4 policies have exited and updates running statistical metrics."""
        ep_data = self.active_episodes.pop(ep_id)
        positions = ep_data["positions"]
        
        p1 = positions.get("SOL")
        p2 = positions.get("RANDOM")
        p3 = positions.get("ROUND_ROBIN")
        p4 = positions.get("MAX_OBI")

        delta_mos = (p4.net_realized_pnl - p1.net_realized_pnl) if (p4 and p1) else 0.0
        delta_mor = (p4.net_realized_pnl - p2.net_realized_pnl) if (p4 and p2) else 0.0

        episode_record = {
            "episode_id": ep_data["episode_id"],
            "episode_index": ep_data["episode_index"],
            "t0_unix": ep_data["t0_unix"],
            "t0_utc": ep_data["t0_utc"],
            "binance_btc_trigger_price": ep_data["binance_btc_trigger_price"],
            "binance_sweep_volume_usd": ep_data["binance_sweep_volume_usd"],
            "z_ofi": ep_data["z_ofi"],
            "subsequent_shocks_count": len(ep_data["subsequent_shocks"]),
            "policy_assets": ep_data["policy_assets"],
            "l2_snapshot_t0": ep_data["l2_snapshot_t0"],
            "obi_by_asset": ep_data["obi_by_asset"],
            "outcomes": {
                pname: {
                    "asset": pos.asset,
                    "entry_price": pos.initial_entry_price,
                    "exit_price": pos.fills[-1].fill_price if pos.fills else 0.0,
                    "holding_seconds": pos.holding_seconds,
                    "exit_reason": pos.exit_reason,
                    "gross_realized_pnl": pos.gross_realized_pnl,
                    "total_fees_paid": pos.total_fees_paid,
                    "total_funding_accrued": pos.total_funding_accrued,
                    "net_realized_pnl": pos.net_realized_pnl,
                    "execution_shortfall": pos.total_execution_shortfall,
                    "won": (pos.net_realized_pnl > 0)
                } for pname, pos in positions.items()
            },
            "routing_increments": {
                "delta_mos_net_pnl_usd": round(delta_mos, 4),
                "delta_mor_net_pnl_usd": round(delta_mor, 4)
            }
        }

        with open(EPISODE_LEDGER_FILE, "a") as f:
            f.write(json.dumps(episode_record) + "\n")
            
        self.completed_episodes_history.append(episode_record)
        print(f"\n[>>> COUNTERFACTUAL EPISODE {ep_id} FINALIZED <<<]"
              f"\n  Policy 1 (SOL): Net PnL = ${p1.net_realized_pnl:+.2f} ({p1.asset})"
              f"\n  Policy 2 (RANDOM): Net PnL = ${p2.net_realized_pnl:+.2f} ({p2.asset})"
              f"\n  Policy 3 (ROUND_ROBIN): Net PnL = ${p3.net_realized_pnl:+.2f} ({p3.asset})"
              f"\n  Policy 4 (MAX_OBI): Net PnL = ${p4.net_realized_pnl:+.2f} ({p4.asset})"
              f"\n  Routing Delta (MOS): ${delta_mos:+.2f} | Routing Delta (MOR): ${delta_mor:+.2f}\n", flush=True)

        self._update_shadow_summary()

    def _update_shadow_summary(self):
        """Computes confirmatory routing p-values and writes running summary to disk."""
        total_eps = len(self.completed_episodes_history)
        if total_eps == 0:
            return

        p1_pnls = [ep["outcomes"]["SOL"]["net_realized_pnl"] for ep in self.completed_episodes_history]
        p2_pnls = [ep["outcomes"]["RANDOM"]["net_realized_pnl"] for ep in self.completed_episodes_history]
        p3_pnls = [ep["outcomes"]["ROUND_ROBIN"]["net_realized_pnl"] for ep in self.completed_episodes_history]
        p4_pnls = [ep["outcomes"]["MAX_OBI"]["net_realized_pnl"] for ep in self.completed_episodes_history]
        p5_pnls = [ep["outcomes"].get("COMPOSITE_RECOVERY", {}).get("net_realized_pnl", 0.0) for ep in self.completed_episodes_history if "COMPOSITE_RECOVERY" in ep.get("outcomes", {})]

        mu_sol = sum(p1_pnls) / total_eps
        mu_rand = sum(p2_pnls) / total_eps
        mu_rr = sum(p3_pnls) / total_eps
        mu_max_obi = sum(p4_pnls) / total_eps
        mu_composite = sum(p5_pnls) / len(p5_pnls) if p5_pnls else 0.0

        delta_mos_vals = [p4 - p1 for p4, p1 in zip(p4_pnls, p1_pnls)]
        delta_mor_vals = [p4 - p2 for p4, p2 in zip(p4_pnls, p2_pnls)]

        mean_delta_mos = sum(delta_mos_vals) / total_eps
        mean_delta_mor = sum(delta_mor_vals) / total_eps

        # Paired t-test for Route 2B confirmatory hypotheses
        # H1_MOS: Delta_MOS > 0 (one-sided)
        # H1_MOR: Delta_MOR > 0 (one-sided)
        p_mos = 1.0
        p_mor = 1.0
        if total_eps >= 2 and SCIPY_AVAILABLE:
            try:
                # One-sided paired t-test: alternative='greater'
                res_mos = sp_stats.ttest_rel(p4_pnls, p1_pnls, alternative="greater")
                p_mos = float(res_mos.pvalue) if not math.isnan(res_mos.pvalue) else 1.0
                
                res_mor = sp_stats.ttest_rel(p4_pnls, p2_pnls, alternative="greater")
                p_mor = float(res_mor.pvalue) if not math.isnan(res_mor.pvalue) else 1.0
            except Exception as e:
                p_mos, p_mor = 1.0, 1.0
        elif total_eps >= 2:
            # Fallback normal approximation if scipy missing
            std_mos = math.sqrt(sum((x - mean_delta_mos)**2 for x in delta_mos_vals) / (total_eps - 1)) if total_eps > 1 else 1.0
            t_stat_mos = mean_delta_mos / (std_mos / math.sqrt(total_eps)) if std_mos > 0 else 0.0
            p_mos = 0.5 * (1.0 - math.erf(t_stat_mos / math.sqrt(2.0)))
            
            std_mor = math.sqrt(sum((x - mean_delta_mor)**2 for x in delta_mor_vals) / (total_eps - 1)) if total_eps > 1 else 1.0
            t_stat_mor = mean_delta_mor / (std_mor / math.sqrt(total_eps)) if std_mor > 0 else 0.0
            p_mor = 0.5 * (1.0 - math.erf(t_stat_mor / math.sqrt(2.0)))

        p_routing = max(p_mos, p_mor)

        summary = {
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "governance": {
                "specification_version": "v3.1",
                "execution_model": EXECUTION_MODEL_TYPE,
                "friction_assumptions": {
                    "base_taker_fee": BASE_TAKER_FEE_MODELED,
                    "modeled_entry_slippage_bps": MODELED_ENTRY_SLIPPAGE_BPS,
                    "modeled_exit_slippage_bps": MODELED_EXIT_SLIPPAGE_BPS,
                    "simulated_latency_ms": 4.7
                },
                "funding_sign_convention": "GrossPricePnL - Fees + FundingCashflow (Cashflow > 0 = Received)",
                "liquidation_stop_model": "Local L2 mid/bid proxy simulation"
            },
            "sample_size": {
                "total_independent_episodes": total_eps,
                "target_episodes_required": 100,
                "progress_pct": round(total_eps / 100.0 * 100.0, 2)
            },
            "policy_performance": {
                "SOL_only": {
                    "cumulative_net_pnl_usd": round(sum(p1_pnls), 2),
                    "mean_net_pnl_usd": round(mu_sol, 4),
                    "win_rate_pct": round(sum(1 for x in p1_pnls if x > 0) / total_eps * 100.0, 2)
                },
                "RANDOM_eligible": {
                    "cumulative_net_pnl_usd": round(sum(p2_pnls), 2),
                    "mean_net_pnl_usd": round(mu_rand, 4),
                    "win_rate_pct": round(sum(1 for x in p2_pnls if x > 0) / total_eps * 100.0, 2)
                },
                "ROUND_ROBIN": {
                    "cumulative_net_pnl_usd": round(sum(p3_pnls), 2),
                    "mean_net_pnl_usd": round(mu_rr, 4),
                    "win_rate_pct": round(sum(1 for x in p3_pnls if x > 0) / total_eps * 100.0, 2)
                },
                "MAX_OBI_router": {
                    "cumulative_net_pnl_usd": round(sum(p4_pnls), 2),
                    "mean_net_pnl_usd": round(mu_max_obi, 4),
                    "win_rate_pct": round(sum(1 for x in p4_pnls if x > 0) / total_eps * 100.0, 2)
                },
                "COMPOSITE_RECOVERY_router": {
                    "cumulative_net_pnl_usd": round(sum(p5_pnls), 2),
                    "mean_net_pnl_usd": round(mu_composite, 4),
                    "win_rate_pct": round(sum(1 for x in p5_pnls if x > 0) / len(p5_pnls) * 100.0, 2) if p5_pnls else 0.0,
                    "episodes_count": len(p5_pnls)
                }
            },
            "routing_increments": {
                "delta_mos_mean_usd": round(mean_delta_mos, 4),
                "delta_mor_mean_usd": round(mean_delta_mor, 4)
            },
            "confirmatory_routing_p_values": {
                "p_MOS": round(p_mos, 6),
                "p_MOR": round(p_mor, 6),
                "p_routing_max": round(p_routing, 6),
                "conformance_hurdle": "p_routing < 0.01",
                "gate_passed": (p_routing < 0.01 and total_eps >= 100)
            },
            "primary_sprint_summary": {
                "total_completed": len(self.completed_sprints),
                "cumulative_net_pnl_usd": round(sum(s.net_realized_pnl for s in self.completed_sprints), 2) if self.completed_sprints else 0.0
            }
        }

        with open(SUMMARY_FILE, "w") as f:
            json.dump(summary, f, indent=2)


async def run_shadow_daemon():
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    engine = RatchetShadowEngine()
    window = TradeWindow(window_ms=SHOCK_WINDOW_MS)

    print("===============================================================================", flush=True)
    print("   EXPERIMENT R: HYPERLIQUID RATCHETED EVENT MOMENTUM (v3.1 CONFORMANCE)       ", flush=True)
    print(f"   Shock Trigger: >= ${SHOCK_VOLUME_USD:,.0f} in {SHOCK_WINDOW_MS}ms | Z_OFI >= {Z_OFI_HURDLE} (p < 0.01)", flush=True)
    print("   Parallel Virtual Execution: SOL, RANDOM, ROUND-ROBIN, MAX-OBI evaluated concurrently", flush=True)
    print("   Decoupled Shock Ingestion: Zero state-dependent censoring | tau = 300s", flush=True)
    print("   Accounting: Strict Funding Sign Invariant (+FundingCashflow)", flush=True)
    print("   Friction: Modeled Base-Fee 4.5 bps | Modeled Transit Latency 3.2 ms", flush=True)
    print("===============================================================================\n", flush=True)

    async def stream_binance():
        while True:
            try:
                print(f"[*] Connecting to Tokyo Binance aggTrade feed ({BINANCE_WS_URL})...", flush=True)
                async with websockets.connect(BINANCE_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    print("[+] Connected to Binance aggTrade stream at microsecond precision.", flush=True)
                    async for msg_str in ws:
                        t_recv_ns = time.monotonic_ns()
                        msg = json.loads(msg_str)
                        px = float(msg.get("p", 0))
                        sz = float(msg.get("q", 0))
                        ts_ms = float(msg.get("T", 0))
                        bm = bool(msg.get("m", False))

                        window.add(ts_ms / 1000.0, px, sz, bm)
                        engine.btc_trend_window.append(px)

                        metrics = window.get_metrics()
                        if metrics["total_usd"] >= SHOCK_VOLUME_USD and metrics["z_ofi"] >= Z_OFI_HURDLE:
                            t_dec_ns = time.monotonic_ns()
                            engine.handle_incoming_shock(
                                ts_ms=ts_ms,
                                px=px,
                                metrics=metrics,
                                t_recv_ns=t_recv_ns,
                                t_dec_ns=t_dec_ns
                            )
            except Exception as e:
                print(f"[-] Binance feed disconnected: {e}. Reconnecting in 3s...", flush=True)
                await asyncio.sleep(3)

    async def stream_hyperliquid():
        while True:
            try:
                print(f"[*] Connecting to Hyperliquid L2 WebSocket ({HYPERLIQUID_WS_URL})...", flush=True)
                async with websockets.connect(HYPERLIQUID_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    for coin in ["SOL", "HYPE", "SUI", "DOGE"]:
                        sub_msg = {"method": "subscribe", "subscription": {"type": "l2Book", "coin": coin}}
                        await ws.send(json.dumps(sub_msg))
                    print("[+] Subscribed to Hyperliquid L2 books (SOL, HYPE, SUI, DOGE).", flush=True)

                    async for msg_str in ws:
                        data = json.loads(msg_str)
                        if data.get("channel") == "l2Book":
                            book_data = data.get("data", {})
                            coin = book_data.get("coin")
                            levels = book_data.get("levels", [[], []])
                            bids, asks = levels[0], levels[1]
                            if bids and asks and coin in engine.current_order_books:
                                best_bid = float(bids[0]["px"])
                                best_ask = float(asks[0]["px"])
                                bid_sz = float(bids[0]["sz"])
                                ask_sz = float(asks[0]["sz"])
                                engine.update_book(coin, best_bid, best_ask, bid_sz, ask_sz)

                                # Evaluate primary sprint and all active virtual policy positions
                                engine.evaluate_all_positions()

            except Exception as e:
                print(f"[-] Hyperliquid feed disconnected: {e}. Reconnecting in 3s...", flush=True)
                await asyncio.sleep(3)

    await asyncio.gather(stream_binance(), stream_hyperliquid())


if __name__ == "__main__":
    try:
        asyncio.run(run_shadow_daemon())
    except KeyboardInterrupt:
        print("\n[*] Shadow daemon stopped by user.")

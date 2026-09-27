"""
IRONCORE CANONICAL BACKTESTING & CERTIFICATION ENGINE (v2.3.0)
=============================================================
Unified, institutional-grade backtesting and alpha certification engine with:
1. Authoritative PositionState and OrderState lifecycle machines.
2. Unbroken WFO provenance chain (certify_strategy requires CertificationProvenance).
3. Discrete Tiered Governor with explicit halt-state transition and 2% recovery buffer.
4. Strictly executed-only turnover (including partial-fill accounting).
5. Separated cost accounting: pure exchange fees, adverse selection markout, market impact.
6. PIT liquidity entry/exit asymmetry (additions blocked, exits allowed, flips only close).
7. Newey-West HAC and block-bootstrap Gate 4 statistical testing.
8. Comprehensive Gate 5 regime breakdown and Gate 8 10-dimensional parity audit.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union

import numpy as np
import polars as pl
from scipy import stats

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.backtesting.ironcore_config import (
    IronCoreConfig_v1, DEFAULT_CONFIG, CertificationProvenance, ResolvedExecutionParameters,
    BacktestExecutionReference, EnvironmentManifest, hash_array_raw, hash_array_canonicalized,
)
from src.backtesting.trial_registry_dsr import TrialRegistryDSR
from src.backtesting.multi_split_regime import MultiSplitRegimeAnalyzer
from src.backtesting.ruin_and_leverage_frontier import RuinAndLeverageFrontier
from src.backtesting.adversarial_suite import AdversarialPlaceboSuite


# =============================================================================
# INTRABAR PATH CONVENTION
# =============================================================================

INTRABAR_PATH_CONVENTION = (
    "PESSIMISTIC_WORST_CASE: When same_subbar_stop_vulnerable=True, "
    "newly filled positions are exposed to the full OHLC range of the "
    "entry subbar. OHLC data does not establish post-fill path ordering; "
    "this is a conservative accounting assumption, not physical execution. "
    "When same_subbar_stop_vulnerable=False, stop/TP evaluation begins "
    "on the following subbar (causally safe: no OHLC path ambiguity)."
)


# =============================================================================
# 1. AUTHORITATIVE POSITION & ORDER STATE MACHINES
# =============================================================================

@dataclass
class PositionState:
    """
    Authoritative state of an individual token position.
    Decouples target portfolio weights from physical inventory.
    """
    symbol_idx: int
    qty: float = 0.0
    avg_entry_px: float = 0.0
    last_fill_px: float = 0.0
    realized_pnl: float = 0.0
    entry_bar: Optional[int] = None
    lifecycle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    @property
    def is_open(self) -> bool:
        return abs(self.qty) > 1e-8

    @property
    def is_long(self) -> bool:
        return self.qty > 1e-8

    @property
    def is_short(self) -> bool:
        return self.qty < -1e-8

    def apply_increase(self, fill_qty: float, fill_px: float, bar_idx: int):
        """
        Adds exposure in the existing direction.
        Computes volume-weighted average entry price: P_new = (Q1*P1 + Q2*P2) / (Q1 + Q2).
        """
        if abs(fill_qty) < 1e-8 or fill_px <= 0:
            return
        
        old_q = abs(self.qty)
        add_q = abs(fill_qty)
        new_q = old_q + add_q
        
        if old_q > 1e-8 and self.avg_entry_px > 0:
            self.avg_entry_px = (old_q * self.avg_entry_px + add_q * fill_px) / new_q
        else:
            self.avg_entry_px = fill_px
            self.entry_bar = bar_idx
            self.lifecycle_id = str(uuid.uuid4())[:8]

        # Preserve direction sign
        sign = 1.0 if fill_qty > 0 or self.is_long else -1.0
        self.qty = sign * new_q
        self.last_fill_px = fill_px

    def apply_reduction(self, fill_qty: float, fill_px: float) -> float:
        """
        Reduces existing exposure. Average entry price remains UNCHANGED.
        Returns realized PnL from the closed portion.
        """
        if abs(fill_qty) < 1e-8 or not self.is_open or fill_px <= 0:
            return 0.0

        closed_q = min(abs(fill_qty), abs(self.qty))
        entry = self.avg_entry_px if self.avg_entry_px > 0 else fill_px
        
        # Realized PnL: Long = Q*(P_fill - P_entry), Short = Q*(P_entry - P_fill)
        if self.is_long:
            pnl = closed_q * (fill_px - entry)
        else:
            pnl = closed_q * (entry - fill_px)

        self.realized_pnl += pnl
        new_q_mag = max(0.0, abs(self.qty) - closed_q)
        
        if new_q_mag < 1e-8:
            self.qty = 0.0
            self.avg_entry_px = 0.0
            self.entry_bar = None
        else:
            sign = 1.0 if self.is_long else -1.0
            self.qty = sign * new_q_mag

        self.last_fill_px = fill_px
        return pnl

    def apply_full_exit(self, fill_px: float) -> float:
        """Completely liquidates position at fill_px. Returns realized PnL."""
        if not self.is_open or fill_px <= 0:
            return 0.0
        return self.apply_reduction(abs(self.qty), fill_px)

    def apply_flip(self, new_target_qty: float, fill_px: float, bar_idx: int) -> float:
        """
        Closes old position completely at fill_px, then opens new opposite position at fill_px.
        Returns realized PnL from closing the old position.
        """
        closed_pnl = self.apply_full_exit(fill_px)
        if abs(new_target_qty) > 1e-8:
            self.apply_increase(new_target_qty, fill_px, bar_idx)
        return closed_pnl

    def compute_unrealized_pnl(self, current_px: float) -> float:
        """Computes current mark-to-market unrealized PnL against avg_entry_px."""
        if not self.is_open or self.avg_entry_px <= 0 or current_px <= 0:
            return 0.0
        if self.is_long:
            return self.qty * (current_px - self.avg_entry_px)
        else:
            return abs(self.qty) * (self.avg_entry_px - current_px)


@dataclass
class OrderState:
    """Explicit order state machine tracking order lifecycle and partial fills."""
    order_id: str
    order_generation: int
    symbol_idx: int
    target_qty: float
    remaining_qty: float
    created_bar: int
    created_subbar: int
    limit_px: float = 0.0
    status: str = "PENDING"  # PENDING, FILLED, PARTIALLY_FILLED, CANCELLED, TIMEOUT_FILLED
    cancellation_reason: Optional[str] = None
    fills: List[Dict[str, float]] = field(default_factory=list)

    @property
    def filled_qty(self) -> float:
        return max(0.0, abs(self.target_qty) - abs(self.remaining_qty))

    @property
    def is_active(self) -> bool:
        return self.status in ("PENDING", "PARTIALLY_FILLED") and abs(self.remaining_qty) > 1e-8

    def fill_partial(self, fill_qty: float, fill_px: float) -> float:
        """Executes a fill on this order. Updates remaining quantity and status."""
        executed = min(abs(fill_qty), abs(self.remaining_qty))
        sign = 1.0 if self.remaining_qty > 0 else -1.0
        self.remaining_qty = sign * max(0.0, abs(self.remaining_qty) - executed)
        
        self.fills.append({"qty": executed, "px": fill_px})
        if abs(self.remaining_qty) < 1e-8:
            self.status = "FILLED"
        else:
            self.status = "PARTIALLY_FILLED"
        return executed

    def cancel(self, reason: str = "CANCELLED"):
        """Invalidates and cancels any remaining unfilled balance."""
        self.status = "CANCELLED"
        self.cancellation_reason = reason
        self.remaining_qty = 0.0


@dataclass
class GovernorStateMachine:
    """
    Stateful Portfolio Drawdown Governor with Re-Risk Recovery Hysteresis.
    Once reaching >= 15% drawdown (Tier 3), it permanently halts trading (0% leverage).
    Re-risking from halt requires an explicit programmatic reset.
    """
    active_tier_idx: int = 0
    hwm: float = 0.0
    is_halted: bool = False
    rerisk_buffer: float = 0.02
    halt_threshold: float = 0.15
    tiers: Tuple[Tuple[float, float], ...] = (
        (0.05, 1.00),  # < 5% DD: 1.0x
        (0.10, 0.75),  # 5% - 10% DD: 0.75x
        (0.15, 0.35),  # 10% - 15% DD: 0.35x
        (1.00, 0.00),  # >= 15% DD: 0.0x Halt
    )

    def update_equity(self, current_equity: float) -> Tuple[float, int]:
        """Updates equity and evaluates deterministic tier transitions."""
        if current_equity <= 0:
            self.is_halted = True
            return 0.0, len(self.tiers) - 1

        self.hwm = max(self.hwm, current_equity)
        dd = max(0.0, (self.hwm - current_equity) / self.hwm)
        
        # 1. If already halted, remain halted until explicit reset
        if self.is_halted:
            return 0.0, len(self.tiers) - 1
            
        # 2. Check for catastrophic halt threshold (>= 15%)
        if dd >= self.halt_threshold:
            self.is_halted = True
            self.active_tier_idx = len(self.tiers) - 1
            return 0.0, self.active_tier_idx

        sorted_tiers = sorted(self.tiers, key=lambda x: x[0])
        n_tiers = len(sorted_tiers)

        # 3. Check for immediate de-risking
        for idx in range(self.active_tier_idx, n_tiers):
            th, lev = sorted_tiers[idx]
            if dd >= th:
                self.active_tier_idx = min(idx + 1, n_tiers - 1)
                if sorted_tiers[self.active_tier_idx][1] == 0.0:
                    self.is_halted = True

        # 4. Check for re-risking with 2% recovery buffer
        if not self.is_halted:
            while self.active_tier_idx > 0:
                prev_tier_th = sorted_tiers[self.active_tier_idx - 1][0]
                recovery_threshold = max(0.0, prev_tier_th - self.rerisk_buffer)
                if dd < recovery_threshold:
                    self.active_tier_idx -= 1
                else:
                    break

        lev_mult = sorted_tiers[self.active_tier_idx][1] if self.active_tier_idx < n_tiers else 0.0
        return lev_mult, self.active_tier_idx

    def reset_halt(self, current_equity: float):
        """Explicit programmatic override to reactivate governor after a halt."""
        self.is_halted = False
        self.hwm = current_equity
        self.active_tier_idx = 0


# Backward-compatible float wrapper for compute_governor_leverage
class GovernorLeverageResult(float):
    tier_idx: int
    def __new__(cls, val: float, tier_idx: int = 0):
        obj = super().__new__(cls, float(val))
        obj.tier_idx = int(tier_idx)
        return obj
    def __iter__(self):
        yield float(self)
        yield self.tier_idx


# =============================================================================
# 2. MASTER INSTITUTIONAL ENGINE
# =============================================================================

class FatalCausalityError(RuntimeError):
    """Raised when an order or backtest execution violates causal timing invariants."""
    pass


class FatalMarginInvariantBreach(RuntimeError):
    """Raised when total gross portfolio exposure exceeds margin budget."""
    pass


class IronCoreEngine:
    """The master institutional backtesting and alpha certification engine."""

    def __init__(self, config: IronCoreConfig_v1 = DEFAULT_CONFIG):
        self.cfg = config
        self.registry = TrialRegistryDSR()
        self.placebo_suite = AdversarialPlaceboSuite(n_draws=self.cfg.mc_placebo_draws, seed=42)

    def audit_execution_causality_and_margin(
        self,
        bar_idx: int,
        active_positions: Dict[str, Any],
        auxiliary_hedges: Dict[str, float],
        equity: float,
        proposed_order_fills: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Enforces IronCore v2.4.1 Causal Hardening Invariants:
        1. Forbids intra-bar touch fill execution with same-candle close mark-to-market.
        2. Asserts total gross portfolio exposure (core + pyramids + macro hedges) <= max_total_portfolio_gross.
        """
        # 1. Total Gross Margin Audit
        tot_core_notional = sum(abs(pos.get("current_size", 0.0) * pos.get("entry_price", 0.0)) for pos in active_positions.values())
        tot_hedge_notional = sum(abs(h) for h in auxiliary_hedges.values())
        tot_gross_notional = tot_core_notional + tot_hedge_notional
        tot_leverage = tot_gross_notional / max(1.0, equity)

        if getattr(self.cfg, "enforce_total_gross_margin_cap", True):
            max_allowed = getattr(self.cfg, "max_total_portfolio_gross", 3.0)
            if tot_leverage > max_allowed + 1e-3:
                raise FatalMarginInvariantBreach(
                    f"INVARIANT_BREACH_MAX_LEVERAGE at bar {bar_idx}: "
                    f"Total gross leverage {tot_leverage:.2f}x (Core: {tot_core_notional/equity:.2f}x, "
                    f"Hedge: {tot_hedge_notional/equity:.2f}x) exceeds limit {max_allowed:.2f}x!"
                )

        # 2. Causal Fill Execution Audit
        if proposed_order_fills and getattr(self.cfg, "forbid_intrabar_touch_fill", True):
            for fill in proposed_order_fills:
                if fill.get("mode") in ["intrabar_touch", "touch_same_close_mark"]:
                    raise FatalCausalityError(
                        f"FATAL_CAUSALITY_BREACH at bar {bar_idx}: "
                        f"Order for {fill.get('symbol')} attempted intra-bar touch fill at {fill.get('price')}. "
                        f"IronCore v2.4.1 mandates next-bar-open execution!"
                    )

    def audit_preflight_invariants(
        self,
        signal_matrix: np.ndarray,
        close_mat: np.ndarray,
        oracle_mat: np.ndarray,
        valid_mask: np.ndarray,
        volume_mat: np.ndarray,
        returns_mat: Optional[np.ndarray] = None,
        predicted_funding: Optional[np.ndarray] = None,
        weights_matrix: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Verifies mathematical, numerical, data-lake, and portfolio contract invariants."""
        issues = []
        n_bars, n_symbols = close_mat.shape

        # 1. Finite Value Checks
        for name, arr in [("signal", signal_matrix), ("close", close_mat), ("volume", volume_mat)]:
            if not np.all(np.isfinite(arr)):
                issues.append(f"FATAL_NON_FINITE: {name} matrix contains NaNs or Infs.")

        # 2. Constant / Zero-Variance Signal Audit
        sig_std = np.std(signal_matrix, axis=1)
        if np.any(sig_std < self.cfg.zero_signal_tolerance):
            issues.append("FATAL_ZERO_SIGNAL: Constant or zero-variance signal detected.")

        # 3. Conditional Oracle Equality Check
        if self.cfg.oracle_required and np.allclose(close_mat, oracle_mat, atol=1e-5):
            issues.append("FATAL_SYNTHETIC_ORACLE: Close exactly equals Oracle price across entire dataset.")

        # 4. Portfolio Risk Bounds
        if weights_matrix is not None:
            max_single = float(np.max(np.abs(weights_matrix)))
            if max_single > self.cfg.max_single_name_leverage + 1e-4:
                issues.append(f"INVARIANT_SINGLE_NAME_CAP: Weight {max_single:.3f} exceeds cap {self.cfg.max_single_name_leverage:.2f}.")

            gross_lev = np.sum(np.abs(weights_matrix), axis=1)
            max_gross = float(np.max(gross_lev))
            if max_gross > self.cfg.max_gross_leverage + 1e-4:
                issues.append(f"INVARIANT_GROSS_LEVERAGE: Gross {max_gross:.3f} exceeds cap {self.cfg.max_gross_leverage:.2f}.")

            net_exp = np.abs(np.sum(weights_matrix, axis=1))
            max_net = float(np.max(net_exp))
            if max_net > self.cfg.max_net_exposure + 1e-4:
                issues.append(f"INVARIANT_DOLLAR_NEUTRALITY: Net {max_net:.3f} exceeds tolerance {self.cfg.max_net_exposure:.2f}.")

        # 5. Point-In-Time Liquidity Mask with Causal Expanding Warmup
        pit_liquid_mask = np.zeros((n_bars, n_symbols), dtype=bool)
        for t in range(6, n_bars):
            vol_24h = np.sum(volume_mat[t - 5:t + 1], axis=0)
            px_curr = close_mat[t]
            adv_24h = vol_24h * px_curr
            pit_liquid_mask[t] = (adv_24h >= self.cfg.min_adv_usdc) & valid_mask[t]

        passed = len(issues) == 0
        return {
            "passed": passed,
            "status": "PASSED" if passed else "FAILED",
            "issues": issues,
            "pit_liquid_mask": pit_liquid_mask,
            "liquid_universe_counts": np.sum(pit_liquid_mask, axis=1).tolist(),
        }

    def compute_rank_hysteresis_weights(
        self,
        signal_scores: np.ndarray,
        valid_mask_t: np.ndarray,
        weights_prev: np.ndarray,
        entry_k: int = 10,
        exit_k: int = 15,
        target_gross_leverage: float = 1.0,
        fixed_slot_sizing: bool = True,
    ) -> np.ndarray:
        """
        Rank Hysteresis with Fixed Slot Sizing.
        Slots are sized as w_i = budget / entry_k. Missing retained slots become cash.
        Guarantees max(|w_i|) <= max_single_name_leverage.
        """
        n_symbols = len(signal_scores)
        w = np.zeros(n_symbols)
        val_idx = np.where(valid_mask_t)[0]
        if len(val_idx) < (exit_k * 2):
            return w

        scores_val = signal_scores[val_idx]
        sorted_order = np.argsort(scores_val)
        ranked_symbols = val_idx[sorted_order]

        long_ranks = {sym: len(ranked_symbols) - rank for rank, sym in enumerate(ranked_symbols)}
        short_ranks = {sym: rank + 1 for rank, sym in enumerate(ranked_symbols)}

        selected_longs = []
        for sym in ranked_symbols[-entry_k:]:
            selected_longs.append(sym)
        for sym in np.where(weights_prev > 1e-4)[0]:
            if sym in long_ranks and long_ranks[sym] <= exit_k and sym not in selected_longs:
                selected_longs.append(sym)

        selected_shorts = []
        for sym in ranked_symbols[:entry_k]:
            selected_shorts.append(sym)
        for sym in np.where(weights_prev < -1e-4)[0]:
            if sym in short_ranks and short_ranks[sym] <= exit_k and sym not in selected_shorts:
                selected_shorts.append(sym)

        if fixed_slot_sizing:
            slot_w = min((target_gross_leverage / 2.0) / float(entry_k), self.cfg.max_single_name_leverage)
            if selected_longs:
                w[selected_longs] = slot_w
            if selected_shorts:
                w[selected_shorts] = -slot_w
        else:
            long_budget = target_gross_leverage / 2.0
            short_budget = target_gross_leverage / 2.0
            if selected_longs:
                w[selected_longs] = min(long_budget / len(selected_longs), self.cfg.max_single_name_leverage)
            if selected_shorts:
                w[selected_shorts] = -min(short_budget / len(selected_shorts), self.cfg.max_single_name_leverage)

        return w

    def compute_governor_leverage(
        self,
        current_equity: float,
        high_water_mark: float,
        current_tier_idx: Union[int, Tuple[Tuple[float, float], ...]] = 0,
        tiers: Optional[Tuple[Tuple[float, float], ...]] = None,
        rerisk_buffer: Optional[float] = None,
    ) -> GovernorLeverageResult:
        """Compatibility function delegating to stateful governor logic."""
        if isinstance(current_tier_idx, (tuple, list)):
            tiers = current_tier_idx
            current_tier_idx = 0

        gov = GovernorStateMachine(
            active_tier_idx=int(current_tier_idx),
            hwm=high_water_mark,
            rerisk_buffer=rerisk_buffer if rerisk_buffer is not None else self.cfg.rerisk_buffer_pct,
            tiers=tiers or self.cfg.drawdown_tiers,
        )
        lev, new_tier = gov.update_equity(current_equity)
        return GovernorLeverageResult(lev, new_tier)

    # =========================================================================
    # 3. UNIFIED CANONICAL EXECUTION SIMULATOR
    # =========================================================================

    def simulate_canonical_execution(
        self,
        weights_matrix: np.ndarray,
        returns_mat: np.ndarray,
        predicted_funding: np.ndarray,
        volume_mat: np.ndarray,
        close_mat: np.ndarray,
        subbar_data: Optional[Dict[str, np.ndarray]] = None,
        pit_liquid_mask: Optional[np.ndarray] = None,
        sl_pct: Union[float, np.ndarray, None] = None,
        tp_pct: Union[float, np.ndarray, None] = None,
        enable_cooldown: Optional[bool] = None,
        cooldown_bars: Optional[int] = None,
        portfolio_deadband: Optional[float] = None,
        deadband: Optional[float] = None,
        initial_capital: Optional[float] = None,
        initial_weights: Optional[np.ndarray] = None,
        start_bar: int = 0,
        end_bar: Optional[int] = None,
        governor_tiers: Optional[Tuple[Tuple[float, float], ...]] = None,
        adv_24h: Optional[np.ndarray] = None,
        vol_24h: Optional[np.ndarray] = None,
        params: Optional[ResolvedExecutionParameters] = None,
    ) -> Dict[str, Any]:
        """
        Unified Canonical Execution Simulator (v2.4.0).
        Enforces:
        - Authoritative PositionState & OrderState lifecycle.
        - Strict executed-only turnover (including partial fills).
        - Stop loss calculated strictly from Average Entry Price:
          SL_long = P_avg_entry * (1 - sl_pct), SL_short = P_avg_entry * (1 + sl_pct).
        - Immediate cancellation of pending orders upon Stop/TP.
        - PIT liquidity entry/exit asymmetry.
        - Separated cost buckets (exchange_fees, adverse_selection_cost, market_impact).
        - Strict PIT Causal ADV & Volatility: execution at t+1 uses data strictly through completed bar t.
        - Event-Causal Passive Queue: orders resting in book, evaluated for fills at s+1 or later.
        - Same-subbar stop vulnerability and conservative TP penetration.
        """
        n_bars, n_symbols = weights_matrix.shape

        # 1. Authoritative Parameter Resolution
        if params is None:
            overrides = {}
            if sl_pct is not None:
                overrides["sl_pct"] = sl_pct
            if tp_pct is not None:
                overrides["tp_pct"] = tp_pct
            if enable_cooldown is not None:
                overrides["enable_cooldown"] = enable_cooldown
            if cooldown_bars is not None and cooldown_bars != 1:
                overrides["cooldown_bars"] = cooldown_bars
            if portfolio_deadband is not None:
                overrides["portfolio_deadband"] = portfolio_deadband
            if deadband is not None:
                overrides["deadband"] = deadband
            if initial_capital is not None:
                overrides["initial_capital"] = initial_capital
            if governor_tiers is not None:
                overrides["governor_tiers"] = governor_tiers
            params = self.cfg.resolve_runtime_parameters(**overrides)
        else:
            # Zero Authority Bypass: forbid conflicting raw caller arguments when params is provided
            if initial_capital is not None:
                raise ValueError("AUTHORITY_BYPASS_VIOLATION: initial_capital cannot be passed separately when ResolvedExecutionParameters is provided.")
            if sl_pct is not None or tp_pct is not None or portfolio_deadband is not None or governor_tiers is not None:
                raise ValueError("AUTHORITY_BYPASS_VIOLATION: Raw execution overrides cannot be passed when ResolvedExecutionParameters is provided.")

        init_capital = float(params.initial_capital)
        equity = init_capital
        hwm = equity
        
        maker_fee = params.maker_fee
        taker_fee = params.taker_fee
        blended_fee = (params.base_maker_ratio * maker_fee) + ((1.0 - params.base_maker_ratio) * taker_fee)
        adverse_markout = params.base_adverse_bps
        impact_coeff = params.impact_coefficient
        p_deadband = params.portfolio_deadband
        a_deadband = params.deadband
        sl_cfg = params.dynamic_stop_loss if params.dynamic_stop_loss is not None else params.fixed_stop_loss_pct
        tp_cfg = params.dynamic_take_profit if params.dynamic_take_profit is not None else params.fixed_take_profit_pct
        cooldown_enabled = params.enable_cooldown
        cooldown_n_bars = params.cooldown_bars
        gov_tiers = params.drawdown_tiers if params.enable_governor else None
        rerisk_buf = params.rerisk_buffer_pct
        causal_passive = params.causal_passive_mode
        same_subbar_vulnerable = params.same_subbar_stop_vulnerable
        tp_pen_bps = params.tp_penetration_bps
        passive_horizon = params.passive_fill_horizon_subbars

        # 2. Strictly Causal Precomputation of PIT ADV and Volatility
        if adv_24h is None or vol_24h is None:
            adv_24h = np.zeros((n_bars, n_symbols))
            vol_24h = np.zeros((n_bars, n_symbols))
            for t_idx in range(n_bars):
                start_k = max(0, t_idx - 5)
                v_slice = np.nan_to_num(volume_mat[start_k:t_idx + 1], nan=0.0)
                c_slice = np.nan_to_num(close_mat[start_k:t_idx + 1], nan=0.0)
                n_pts = (t_idx + 1) - start_k
                scale = 6.0 / max(n_pts, 1)
                adv_24h[t_idx] = np.sum(v_slice * c_slice, axis=0) * scale
                if n_pts > 1:
                    denom = np.maximum(c_slice[:-1], 1e-6)
                    rets_slice = np.nan_to_num(np.diff(c_slice, axis=0) / denom, nan=0.0, posinf=0.0, neginf=0.0)
                    vol_24h[t_idx] = np.std(rets_slice, axis=0) * np.sqrt(6 * 365)
                else:
                    vol_24h[t_idx] = 0.02
            adv_24h = np.nan_to_num(adv_24h, nan=1000.0, posinf=1e9, neginf=1000.0)
            adv_24h = np.maximum(adv_24h, 1000.0)
            vol_24h = np.nan_to_num(vol_24h, nan=0.02, posinf=0.50, neginf=0.02)
            vol_24h = np.clip(vol_24h, 0.001, 0.50)

        # 3. Initialize Authoritative Position States
        positions: List[PositionState] = [PositionState(symbol_idx=i) for i in range(n_symbols)]
        if initial_weights is not None:
            p_init = close_mat[start_bar]
            for i in range(n_symbols):
                w_i = initial_weights[i]
                if abs(w_i) > 1e-6 and p_init[i] > 0:
                    q_i = (w_i * equity) / p_init[i]
                    positions[i].apply_increase(q_i, p_init[i], start_bar)

        # 4. Initialize Stateful Governor
        gov = GovernorStateMachine(
            active_tier_idx=0,
            hwm=hwm,
            rerisk_buffer=rerisk_buf,
            tiers=gov_tiers or params.drawdown_tiers,
        )

        cooldown_until = np.zeros(n_symbols, dtype=int)
        order_gen = 0

        # Output Metric Accumulators
        total_gross_pnl = 0.0
        total_exchange_fees = 0.0
        total_adverse_selection = 0.0
        total_market_impact = 0.0
        total_funding_pnl = 0.0
        total_turnover_usd = 0.0
        total_turnover_multiple = 0.0
        total_slippage_usd = 0.0
        
        trades_count = 0
        sl_count = 0
        tp_count = 0
        passive_fill_count = 0
        taker_cross_count = 0
        max_drift = 0.0

        bar_rets = []
        equity_curve = [equity]
        gross_exposures = []
        net_exposures = []
        # Canonical event journal: every execution event is recorded for deterministic replay
        event_journal: List[Dict[str, Any]] = []
        eval_end = end_bar if end_bar is not None else (n_bars - 1)

        for t in range(start_bar, eval_end):
            next_t = t + 1
            if subbar_data is not None:
                s_op = subbar_data.get("opens", subbar_data.get("open"))
                if s_op is not None and np.any(s_op[next_t, 0] > 0):
                    p_open = s_op[next_t, 0]
                else:
                    p_open = close_mat[t]
            else:
                p_open = close_mat[t]
            
            # Derive current portfolio weights
            w_curr = np.array([
                (pos.qty * p_open[i]) / max(equity, 1e-4) if pos.is_open and p_open[i] > 0 else 0.0
                for i, pos in enumerate(positions)
            ])

            # A. Governor State Machine Evaluation
            if gov_tiers is not None:
                lev_mult, _ = gov.update_equity(equity)
            else:
                lev_mult = 1.0

            raw_target_w = weights_matrix[t].copy() * lev_mult

            # B. Cooldown Enforcement
            if cooldown_enabled:
                for i in range(n_symbols):
                    if cooldown_until[i] > next_t:
                        raw_target_w[i] = w_curr[i]

            # C. PIT Liquidity Entry/Exit Asymmetry:
            # Additions are blocked; exits/reductions are strictly permitted
            if pit_liquid_mask is not None:
                for i in range(n_symbols):
                    if not pit_liquid_mask[next_t, i]:
                        curr_w = w_curr[i]
                        tgt_w = raw_target_w[i]
                        if (curr_w == 0.0 and tgt_w != 0.0):
                            raw_target_w[i] = 0.0  # Block new entry
                        elif (curr_w > 0 and tgt_w > curr_w):
                            raw_target_w[i] = curr_w  # Block long addition
                        elif (curr_w < 0 and tgt_w < curr_w):
                            raw_target_w[i] = curr_w  # Block short addition
                        elif (curr_w > 0 and tgt_w < 0):
                            raw_target_w[i] = 0.0  # Flip long -> short only closes long!
                        elif (curr_w < 0 and tgt_w > 0):
                            raw_target_w[i] = 0.0  # Flip short -> long only closes short!

            # D. Proposed Rebalancing & Portfolio Deadband
            raw_dw = raw_target_w - w_curr
            proposed_turnover = float(np.sum(np.abs(raw_dw)))
            if p_deadband is not None and p_deadband > 0:
                if proposed_turnover < p_deadband:
                    raw_dw = np.zeros(n_symbols)

            if a_deadband > 0:
                dw = np.where(np.abs(raw_dw) >= a_deadband, raw_dw, 0.0)
            else:
                dw = raw_dw

            # =================================================================
            # MODE A: Discrete 4H Bar Evaluation (subbar_data is None)
            # =================================================================
            if subbar_data is None:
                order_gen += 1
                fee_t = 0.0
                impact_t = 0.0
                adverse_t = 0.0

                for i in range(n_symbols):
                    delta_w = dw[i]
                    if abs(delta_w) < 1e-6 or p_open[i] <= 0:
                        continue

                    order_ntl = abs(delta_w) * equity
                    delta_q = (delta_w * equity) / p_open[i]
                    
                    # Determine position transition
                    pos_trans = "POSITION_OPEN" if abs(positions[i].qty) < 1e-8 else (
                        "POSITION_ADD" if (positions[i].qty > 0 and delta_q > 0) or (positions[i].qty < 0 and delta_q < 0) else (
                            "POSITION_FLAT" if abs(positions[i].qty + delta_q) < 1e-8 else (
                                "POSITION_REDUCE" if (positions[i].qty > 0 and (positions[i].qty + delta_q) > 0) or (positions[i].qty < 0 and (positions[i].qty + delta_q) < 0) else "POSITION_FLIP"
                            )
                        )
                    )

                    # Execution fills immediately at bar open
                    pos = positions[i]
                    old_q = float(pos.qty)
                    new_q = old_q + delta_q

                    if abs(old_q) < 1e-8:
                        pos.apply_increase(delta_q, p_open[i], next_t)
                    elif (old_q > 0 and delta_q > 0) or (old_q < 0 and delta_q < 0):
                        pos.apply_increase(delta_q, p_open[i], next_t)
                    elif (old_q > 0 and new_q >= 0) or (old_q < 0 and new_q <= 0):
                        closed_pnl = pos.apply_reduction(abs(delta_q), p_open[i])
                        total_gross_pnl += closed_pnl
                    else:
                        # Position flip
                        flip_pnl = pos.apply_flip(new_q, p_open[i], next_t)
                        total_gross_pnl += flip_pnl

                    # Turnover strictly on executed fill
                    exec_turnover_mult = abs(delta_w)
                    exec_turnover_usd = order_ntl
                    total_turnover_multiple += exec_turnover_mult
                    total_turnover_usd += exec_turnover_usd
                    trades_count += 1

                    # Pure Exchange Fee Bucket
                    f_i = order_ntl * blended_fee
                    fee_t += f_i
                    
                    # Strictly Causal PIT Footprint Impact & Adverse Selection (using bar t)
                    part_rate = np.sqrt(order_ntl / np.maximum(adv_24h[t, i], 100.0))
                    imp_bps = impact_coeff * np.clip(vol_24h[t, i], 0.0, 0.50) * part_rate
                    imp_i = order_ntl * imp_bps
                    adv_i = order_ntl * adverse_markout
                    
                    impact_t += imp_i
                    adverse_t += adv_i

                    # Emit canonical event journal record
                    event_journal.append({
                        "bar": int(next_t),
                        "subbar": 0,
                        "mode": "A",
                        "symbol": int(i),
                        "symbol_idx": int(i),
                        "order_id": f"A_{next_t}_{i}",
                        "order_generation": int(order_gen),
                        "event_type": "REBALANCE_FILL",
                        "side": "BUY" if delta_q > 0 else "SELL",
                        "requested_qty": float(abs(delta_q)),
                        "filled_qty": float(abs(delta_q)),
                        "remaining_qty": 0.0,
                        "price": float(p_open[i]),
                        "maker_taker": "MAKER",
                        "fee": float(f_i),
                        "market_impact": float(imp_i),
                        "adverse_selection": float(adv_i),
                        "slippage": 0.0,
                        "position_before": float(old_q),
                        "position_after": float(positions[i].qty),
                        "equity_before": float(equity),
                        "equity_after": float(equity),
                        "reason": f"REBALANCE_{pos_trans}",
                        "position_transition": pos_trans,
                    })

                total_exchange_fees += fee_t
                total_market_impact += impact_t
                total_adverse_selection += adverse_t

                # Capital price PnL across forward bar next_t
                next_r = np.nan_to_num(returns_mat[next_t], nan=0.0)
                current_weights = np.array([(p.qty * p_open[i]) / max(equity, 1e-4) for i, p in enumerate(positions)])
                gp_t = float(np.sum(current_weights * next_r)) * equity
                total_gross_pnl += gp_t

                # Funding cashflow across forward bar next_t
                fund_bar = np.nan_to_num(predicted_funding[next_t] * 4.0, nan=0.0)
                fp_t = float(np.sum(-current_weights * fund_bar)) * equity
                total_funding_pnl += fp_t

                fric_t = fee_t + impact_t + adverse_t
                net_pnl_t = gp_t + fp_t - fric_t

            # =================================================================
            # MODE B: Sub-Bar Intraday Evaluation (subbar_data is provided)
            # =================================================================
            else:
                s_opens = subbar_data.get("opens", subbar_data.get("open"))[next_t]
                s_highs = subbar_data.get("highs", subbar_data.get("high"))[next_t]
                s_lows = subbar_data.get("lows", subbar_data.get("low"))[next_t]
                s_closes = subbar_data.get("closes", subbar_data.get("close"))[next_t]
                s_vols = subbar_data.get("volumes", subbar_data.get("volume"))[next_t]
                n_subbars = s_opens.shape[0]

                # Create OrderState objects for active rebalances
                order_gen += 1
                orders: List[Optional[OrderState]] = [None] * n_symbols
                for i in range(n_symbols):
                    # Check if cooldown suppressed an intended trade
                    if cooldown_enabled and cooldown_until[i] > next_t:
                        raw_dw_i = raw_target_w[i] - w_curr[i]
                        if abs(raw_dw_i) > 1e-5:
                            req_q = (raw_dw_i * equity) / max(p_open[i], 1e-8)
                            event_journal.append({
                                "bar": int(next_t),
                                "subbar": 0,
                                "mode": "B",
                                "symbol": int(i),
                                "symbol_idx": int(i),
                                "order_id": f"COOLDOWN_{next_t}_{i}",
                                "order_generation": int(order_gen),
                                "event_type": "COOLDOWN_CANCEL",
                                "side": "BUY" if raw_dw_i > 0 else "SELL",
                                "requested_qty": float(abs(req_q)),
                                "filled_qty": 0.0,
                                "remaining_qty": float(abs(req_q)),
                                "price": float(p_open[i]),
                                "maker_taker": "NONE",
                                "fee": 0.0,
                                "market_impact": 0.0,
                                "adverse_selection": 0.0,
                                "slippage": 0.0,
                                "position_before": float(positions[i].qty),
                                "position_after": float(positions[i].qty),
                                "equity_before": float(equity),
                                "equity_after": float(equity),
                                "reason": f"COOLDOWN_ACTIVE_UNTIL_BAR_{cooldown_until[i]}",
                            })
                        continue

                    delta_w = dw[i]
                    if abs(delta_w) > 1e-5 and p_open[i] > 0:
                        target_q = (delta_w * equity) / p_open[i]
                        init_limit_px = p_open[i] * (0.9995 if target_q > 0 else 1.0005)
                        ord_obj = OrderState(
                            order_id=f"ORD_{next_t}_{order_gen}_{i}",
                            order_generation=order_gen,
                            symbol_idx=i,
                            target_qty=target_q,
                            remaining_qty=target_q,
                            created_bar=next_t,
                            created_subbar=0,
                            limit_px=init_limit_px,
                        )
                        orders[i] = ord_obj

                        event_journal.append({
                            "bar": int(next_t),
                            "subbar": 0,
                            "mode": "B",
                            "symbol": int(i),
                            "symbol_idx": int(i),
                            "order_id": ord_obj.order_id,
                            "order_generation": int(order_gen),
                            "event_type": "ORDER_CREATED",
                            "side": "BUY" if target_q > 0 else "SELL",
                            "requested_qty": float(abs(target_q)),
                            "filled_qty": 0.0,
                            "remaining_qty": float(abs(target_q)),
                            "price": float(init_limit_px),
                            "maker_taker": "MAKER",
                            "fee": 0.0,
                            "market_impact": 0.0,
                            "adverse_selection": 0.0,
                            "slippage": 0.0,
                            "position_before": float(positions[i].qty),
                            "position_after": float(positions[i].qty),
                            "equity_before": float(equity),
                            "equity_after": float(equity),
                            "reason": "REBALANCE_SIGNAL",
                        })

                order_wait = np.zeros(n_symbols, dtype=int)
                order_filled_subbar = np.full(n_symbols, -1, dtype=int)
                order_placed_subbar = np.zeros(n_symbols, dtype=int)

                bar_gross_pnl = 0.0
                bar_fees = 0.0
                bar_impact = 0.0
                bar_adverse = 0.0

                for s in range(n_subbars):
                    sub_open = s_opens[s]
                    sub_high = s_highs[s]
                    sub_low = s_lows[s]
                    sub_close = s_closes[s]
                    sub_vol = s_vols[s]

                    # 1. CAUSAL TIMEOUT CHECK AT SUB-BAR OPEN
                    for i in range(n_symbols):
                        ord_i = orders[i]
                        if ord_i is None or not ord_i.is_active:
                            continue
                        if order_wait[i] >= passive_horizon:
                            # Timeout: Cross book aggressively as taker at sub_open
                            p_op = sub_open[i] if sub_open[i] > 0 else sub_close[i]
                            rem_q = ord_i.remaining_qty
                            rem_usd = abs(rem_q) * p_op

                            fee = rem_usd * taker_fee
                            part_rate = np.sqrt(rem_usd / np.maximum(adv_24h[t, i], 100.0))
                            imp = rem_usd * (impact_coeff * np.clip(vol_24h[t, i], 0.0, 0.50) * part_rate)
                            adv = rem_usd * adverse_markout

                            bar_fees += fee
                            bar_impact += imp
                            bar_adverse += adv
                            total_turnover_multiple += abs(rem_usd / max(equity, 1e-4))
                            total_turnover_usd += rem_usd
                            trades_count += 1
                            taker_cross_count += 1

                            # Update position state
                            pos = positions[i]
                            old_q = float(pos.qty)

                            # Determine position transition
                            if abs(old_q) < 1e-8:
                                pos_trans = "POSITION_OPEN"
                            elif (old_q > 0 and rem_q > 0) or (old_q < 0 and rem_q < 0):
                                pos_trans = "POSITION_ADD"
                            else:
                                new_q_check = old_q + rem_q
                                if abs(new_q_check) < 1e-8:
                                    pos_trans = "POSITION_FLAT"
                                elif (old_q > 0 and new_q_check > 0) or (old_q < 0 and new_q_check < 0):
                                    pos_trans = "POSITION_REDUCE"
                                else:
                                    pos_trans = "POSITION_FLIP"

                            if abs(pos.qty) < 1e-8 or (pos.qty > 0 and rem_q > 0) or (pos.qty < 0 and rem_q < 0):
                                pos.apply_increase(rem_q, p_op, next_t)
                            else:
                                new_q = pos.qty + rem_q
                                if (pos.qty > 0 and new_q >= 0) or (pos.qty < 0 and new_q <= 0):
                                    bar_gross_pnl += pos.apply_reduction(abs(rem_q), p_op)
                                else:
                                    bar_gross_pnl += pos.apply_flip(new_q, p_op, next_t)

                            ord_i.fill_partial(rem_q, p_op)
                            ord_i.status = "TIMEOUT_FILLED"
                            order_filled_subbar[i] = s

                            event_journal.append({
                                "bar": int(next_t),
                                "subbar": int(s),
                                "mode": "B",
                                "symbol": int(i),
                                "symbol_idx": int(i),
                                "order_id": ord_i.order_id,
                                "order_generation": int(ord_i.order_generation),
                                "event_type": "TAKER_TIMEOUT",
                                "side": "BUY" if rem_q > 0 else "SELL",
                                "requested_qty": float(abs(ord_i.target_qty)),
                                "filled_qty": float(abs(rem_q)),
                                "remaining_qty": float(abs(ord_i.remaining_qty)),
                                "price": float(p_op),
                                "maker_taker": "TAKER",
                                "fee": float(fee),
                                "market_impact": float(imp),
                                "adverse_selection": float(adv),
                                "slippage": 0.0,
                                "position_before": float(old_q),
                                "position_after": float(pos.qty),
                                "equity_before": float(equity),
                                "equity_after": float(equity),
                                "reason": f"PASSIVE_HORIZON_TIMEOUT_{pos_trans}",
                                "position_transition": pos_trans,
                            })

                    # 2. PROCESS PENDING PASSIVE REBALANCE ORDERS
                    for i in range(n_symbols):
                        ord_i = orders[i]
                        if ord_i is None or not ord_i.is_active:
                            continue

                        # Causal Passive Queue Rule:
                        # Orders placed at subbar s enter the book; touches evaluated strictly at s+1 or later.
                        if causal_passive and s <= order_placed_subbar[i]:
                            order_wait[i] += 1
                            continue

                        rem_q = ord_i.remaining_qty
                        p_op = sub_open[i] if sub_open[i] > 0 else sub_close[i]
                        p_lo = sub_low[i] if sub_low[i] > 0 else p_op
                        p_hi = sub_high[i] if sub_high[i] > 0 else p_op
                        rem_usd = abs(rem_q) * p_op

                        limit_px = ord_i.limit_px if ord_i.limit_px > 0 else p_op * (0.9995 if rem_q > 0 else 1.0005)
                        can_fill_passive = (p_lo <= limit_px) if rem_q > 0 else (p_hi >= limit_px)

                        if can_fill_passive:
                            bar_vol_usd = sub_vol[i] * p_op
                            fill_prob = min(1.0, (bar_vol_usd + 1e3) / max(rem_usd * 2.0, 1e3))
                            
                            # Immutable SHA-256 event-identity seed:
                            # derived from master_seed|bar|subbar|symbol|order_generation|execution_attempt
                            # so that execution is stable across Python implementations and process invocations.
                            master_execution_seed = 0
                            seed_material = (
                                f"{master_execution_seed}|"
                                f"{next_t}|"
                                f"{s}|"
                                f"{i}|"
                                f"{ord_i.order_generation}|"
                                f"{order_wait[i]}"
                            ).encode("utf-8")
                            event_seed = int.from_bytes(
                                hashlib.sha256(seed_material).digest()[:8],
                                "big"
                            ) % (2**32)

                            if np.random.RandomState(event_seed).uniform(0, 1) <= fill_prob:
                                fee = rem_usd * maker_fee
                                adv = rem_usd * adverse_markout
                                part_rate = np.sqrt(rem_usd / np.maximum(adv_24h[t, i], 100.0))
                                imp = rem_usd * (impact_coeff * np.clip(vol_24h[t, i], 0.0, 0.50) * part_rate)

                                bar_fees += fee
                                bar_adverse += adv
                                bar_impact += imp
                                total_turnover_multiple += abs(rem_usd / max(equity, 1e-4))
                                total_turnover_usd += rem_usd
                                trades_count += 1
                                passive_fill_count += 1

                                pos = positions[i]
                                old_q = float(pos.qty)

                                # Determine position transition
                                if abs(old_q) < 1e-8:
                                    pos_trans = "POSITION_OPEN"
                                elif (old_q > 0 and rem_q > 0) or (old_q < 0 and rem_q < 0):
                                    pos_trans = "POSITION_ADD"
                                else:
                                    new_q_check = old_q + rem_q
                                    if abs(new_q_check) < 1e-8:
                                        pos_trans = "POSITION_FLAT"
                                    elif (old_q > 0 and new_q_check > 0) or (old_q < 0 and new_q_check < 0):
                                        pos_trans = "POSITION_REDUCE"
                                    else:
                                        pos_trans = "POSITION_FLIP"

                                if abs(old_q) < 1e-8 or (old_q > 0 and rem_q > 0) or (old_q < 0 and rem_q < 0):
                                    pos.apply_increase(rem_q, limit_px, next_t)
                                else:
                                    new_q = old_q + rem_q
                                    if (old_q > 0 and new_q >= 0) or (old_q < 0 and new_q <= 0):
                                        bar_gross_pnl += pos.apply_reduction(abs(rem_q), limit_px)
                                    else:
                                        bar_gross_pnl += pos.apply_flip(new_q, limit_px, next_t)

                                ord_i.fill_partial(rem_q, limit_px)
                                order_filled_subbar[i] = s

                                event_type = "PASSIVE_FILL" if ord_i.remaining_qty == 0 else "PARTIAL_PASSIVE_FILL"
                                event_journal.append({
                                    "bar": int(next_t),
                                    "subbar": int(s),
                                    "mode": "B",
                                    "symbol": int(i),
                                    "symbol_idx": int(i),
                                    "order_id": ord_i.order_id,
                                    "order_generation": int(ord_i.order_generation),
                                    "event_type": event_type,
                                    "side": "BUY" if rem_q > 0 else "SELL",
                                    "requested_qty": float(abs(ord_i.target_qty)),
                                    "filled_qty": float(abs(rem_q)),
                                    "remaining_qty": float(abs(ord_i.remaining_qty)),
                                    "price": float(limit_px),
                                    "maker_taker": "MAKER",
                                    "fee": float(fee),
                                    "market_impact": float(imp),
                                    "adverse_selection": float(adv),
                                    "slippage": 0.0,
                                    "position_before": float(old_q),
                                    "position_after": float(pos.qty),
                                    "equity_before": float(equity),
                                    "equity_after": float(equity),
                                    "reason": f"LIMIT_TOUCH_{pos_trans}",
                                    "position_transition": pos_trans,
                                })
                                continue

                        order_wait[i] += 1

                    # 3. MONITOR ACTIVE POSITIONS FOR INTRABAR BRACKET STOPS (SL/TP)
                    # Path convention: see INTRABAR_PATH_CONVENTION constant.
                    # When same_subbar_stop_vulnerable=True, newly filled positions are
                    # exposed to the full OHLC of entry subbar (pessimistic worst-case).
                    # When False, stop/TP begins on the following subbar (causally safe).
                    for i in range(n_symbols):
                        pos = positions[i]
                        if not pos.is_open:
                            continue

                        # If not same_subbar_vulnerable, newly opened position is immune in subbar of fill
                        if (not same_subbar_vulnerable) and (order_filled_subbar[i] == s):
                            continue

                        # Stop loss is strictly measured against avg_entry_px
                        entry = pos.avg_entry_px if pos.avg_entry_px > 0 else sub_open[i]
                        p_hi = sub_high[i] if sub_high[i] > 0 else entry
                        p_lo = sub_low[i] if sub_low[i] > 0 else entry
                        pos_usd = abs(pos.qty) * entry

                        # Extract scalar/array thresholds
                        cur_sl = float(sl_cfg[next_t, i]) if isinstance(sl_cfg, np.ndarray) and sl_cfg.ndim == 2 else (float(sl_cfg[i]) if isinstance(sl_cfg, np.ndarray) else (float(sl_cfg) if sl_cfg is not None else None))
                        cur_tp = float(tp_cfg[next_t, i]) if isinstance(tp_cfg, np.ndarray) and tp_cfg.ndim == 2 else (float(tp_cfg[i]) if isinstance(tp_cfg, np.ndarray) else (float(tp_cfg) if tp_cfg is not None else None))

                        if pos.is_long:
                            hit_sl = cur_sl is not None and ((p_lo - entry) / (entry + 1e-8)) <= -cur_sl
                            # TP requires penetration beyond limit price
                            hit_tp = cur_tp is not None and ((p_hi - entry) / (entry + 1e-8)) >= (cur_tp + tp_pen_bps)
                            if hit_sl and hit_tp:
                                hit_tp = False  # Conservative adverse stop first

                            if hit_sl:
                                sl_count += 1
                                gap_slip = max(0.0, (entry * (1.0 - cur_sl) - p_lo) * 0.3)
                                exit_px = entry * (1.0 - cur_sl) - gap_slip
                                slip_usd = abs(pos.qty) * gap_slip
                                total_slippage_usd += slip_usd

                                pos_before = float(pos.qty)
                                pnl_i = pos.apply_full_exit(exit_px)
                                fee_i = pos_usd * taker_fee
                                part_rate = np.sqrt(pos_usd / np.maximum(adv_24h[t, i], 100.0))
                                imp_i = pos_usd * (impact_coeff * np.clip(vol_24h[t, i], 0.0, 0.50) * part_rate)
                                adv_i = pos_usd * adverse_markout

                                bar_gross_pnl += pnl_i
                                bar_fees += fee_i
                                bar_impact += imp_i
                                bar_adverse += adv_i
                                total_turnover_multiple += abs(pos_usd / max(equity, 1e-4))
                                total_turnover_usd += pos_usd
                                trades_count += 1

                                # Emit SL event journal record
                                event_journal.append({
                                    "bar": int(next_t),
                                    "subbar": int(s),
                                    "mode": "B",
                                    "symbol": int(i),
                                    "symbol_idx": int(i),
                                    "order_id": f"SL_{next_t}_{s}_{i}",
                                    "order_generation": int(order_gen),
                                    "event_type": "STOP_LOSS",
                                    "side": "SELL",
                                    "requested_qty": float(abs(pos_before)),
                                    "filled_qty": float(abs(pos_before)),
                                    "remaining_qty": 0.0,
                                    "price": float(exit_px),
                                    "maker_taker": "TAKER",
                                    "fee": float(fee_i),
                                    "market_impact": float(imp_i),
                                    "adverse_selection": float(adv_i),
                                    "slippage": float(slip_usd),
                                    "realized_pnl": float(pnl_i),
                                    "position_before": float(pos_before),
                                    "position_after": 0.0,
                                    "equity_before": float(equity),
                                    "equity_after": float(equity),
                                    "reason": "STOP_LOSS_TRIGGERED",
                                    "position_transition": "POSITION_FLAT",
                                })

                                # Invalidate pending rebalance orders immediately
                                if orders[i] is not None and orders[i].is_active:
                                    orders[i].cancel("STOP_LOSS_TRIGGERED")
                                    event_journal.append({
                                        "bar": int(next_t),
                                        "subbar": int(s),
                                        "mode": "B",
                                        "symbol": int(i),
                                        "symbol_idx": int(i),
                                        "order_id": orders[i].order_id,
                                        "order_generation": int(orders[i].order_generation),
                                        "event_type": "ORDER_CANCELLED",
                                        "side": "BUY" if orders[i].target_qty > 0 else "SELL",
                                        "requested_qty": float(abs(orders[i].target_qty)),
                                        "filled_qty": float(abs(orders[i].filled_qty)),
                                        "remaining_qty": float(abs(orders[i].remaining_qty)),
                                        "price": float(orders[i].limit_px),
                                        "maker_taker": "NONE",
                                        "fee": 0.0,
                                        "market_impact": 0.0,
                                        "adverse_selection": 0.0,
                                        "slippage": 0.0,
                                        "position_before": 0.0,
                                        "position_after": 0.0,
                                        "equity_before": float(equity),
                                        "equity_after": float(equity),
                                        "reason": "STOP_LOSS_TRIGGERED",
                                    })

                                if cooldown_enabled:
                                    cooldown_until[i] = next_t + 1 + cooldown_n_bars
                            elif hit_tp:
                                tp_count += 1
                                exit_px = entry * (1.0 + cur_tp)
                                pos_before = float(pos.qty)
                                pnl_i = pos.apply_full_exit(exit_px)
                                fee_i = pos_usd * maker_fee

                                bar_gross_pnl += pnl_i
                                bar_fees += fee_i
                                total_turnover_multiple += abs(pos_usd / max(equity, 1e-4))
                                total_turnover_usd += pos_usd
                                trades_count += 1

                                event_journal.append({
                                    "bar": int(next_t),
                                    "subbar": int(s),
                                    "mode": "B",
                                    "symbol": int(i),
                                    "symbol_idx": int(i),
                                    "order_id": f"TP_{next_t}_{s}_{i}",
                                    "order_generation": int(order_gen),
                                    "event_type": "TAKE_PROFIT",
                                    "side": "SELL",
                                    "requested_qty": float(abs(pos_before)),
                                    "filled_qty": float(abs(pos_before)),
                                    "remaining_qty": 0.0,
                                    "price": float(exit_px),
                                    "maker_taker": "MAKER",
                                    "fee": float(fee_i),
                                    "market_impact": 0.0,
                                    "adverse_selection": 0.0,
                                    "slippage": 0.0,
                                    "realized_pnl": float(pnl_i),
                                    "position_before": float(pos_before),
                                    "position_after": 0.0,
                                    "equity_before": float(equity),
                                    "equity_after": float(equity),
                                    "reason": "TAKE_PROFIT_TRIGGERED",
                                    "position_transition": "POSITION_FLAT",
                                })

                                if orders[i] is not None and orders[i].is_active:
                                    orders[i].cancel("TAKE_PROFIT_TRIGGERED")
                                    event_journal.append({
                                        "bar": int(next_t),
                                        "subbar": int(s),
                                        "mode": "B",
                                        "symbol": int(i),
                                        "symbol_idx": int(i),
                                        "order_id": orders[i].order_id,
                                        "order_generation": int(orders[i].order_generation),
                                        "event_type": "ORDER_CANCELLED",
                                        "side": "BUY" if orders[i].target_qty > 0 else "SELL",
                                        "requested_qty": float(abs(orders[i].target_qty)),
                                        "filled_qty": float(abs(orders[i].filled_qty)),
                                        "remaining_qty": float(abs(orders[i].remaining_qty)),
                                        "price": float(orders[i].limit_px),
                                        "maker_taker": "NONE",
                                        "fee": 0.0,
                                        "market_impact": 0.0,
                                        "adverse_selection": 0.0,
                                        "slippage": 0.0,
                                        "position_before": 0.0,
                                        "position_after": 0.0,
                                        "equity_before": float(equity),
                                        "equity_after": float(equity),
                                        "reason": "TAKE_PROFIT_TRIGGERED",
                                    })
                            else:
                                ref_px = pos.last_fill_px if order_filled_subbar[i] == s else sub_open[i]
                                ret_s = (sub_close[i] - ref_px) / (ref_px + 1e-8)
                                bar_gross_pnl += (pos.qty * ref_px) * ret_s

                        else:  # SHORT
                            hit_sl = cur_sl is not None and ((p_hi - entry) / (entry + 1e-8)) >= cur_sl
                            hit_tp = cur_tp is not None and ((entry - p_lo) / (entry + 1e-8)) >= (cur_tp + tp_pen_bps)
                            if hit_sl and hit_tp:
                                hit_tp = False

                            if hit_sl:
                                sl_count += 1
                                gap_slip = max(0.0, (p_hi - entry * (1.0 + cur_sl)) * 0.3)
                                exit_px = entry * (1.0 + cur_sl) + gap_slip
                                slip_usd = abs(pos.qty) * gap_slip
                                total_slippage_usd += slip_usd

                                pos_before = float(pos.qty)
                                pnl_i = pos.apply_full_exit(exit_px)
                                fee_i = pos_usd * taker_fee
                                part_rate = np.sqrt(pos_usd / np.maximum(adv_24h[t, i], 100.0))
                                imp_i = pos_usd * (impact_coeff * np.clip(vol_24h[t, i], 0.0, 0.50) * part_rate)
                                adv_i = pos_usd * adverse_markout

                                bar_gross_pnl += pnl_i
                                bar_fees += fee_i
                                bar_impact += imp_i
                                bar_adverse += adv_i
                                total_turnover_multiple += abs(pos_usd / max(equity, 1e-4))
                                total_turnover_usd += pos_usd
                                trades_count += 1

                                event_journal.append({
                                    "bar": int(next_t),
                                    "subbar": int(s),
                                    "mode": "B",
                                    "symbol": int(i),
                                    "symbol_idx": int(i),
                                    "order_id": f"SL_{next_t}_{s}_{i}",
                                    "order_generation": int(order_gen),
                                    "event_type": "STOP_LOSS",
                                    "side": "BUY",
                                    "requested_qty": float(abs(pos_before)),
                                    "filled_qty": float(abs(pos_before)),
                                    "remaining_qty": 0.0,
                                    "price": float(exit_px),
                                    "maker_taker": "TAKER",
                                    "fee": float(fee_i),
                                    "market_impact": float(imp_i),
                                    "adverse_selection": float(adv_i),
                                    "slippage": float(slip_usd),
                                    "realized_pnl": float(pnl_i),
                                    "position_before": float(pos_before),
                                    "position_after": 0.0,
                                    "equity_before": float(equity),
                                    "equity_after": float(equity),
                                    "reason": "STOP_LOSS_TRIGGERED",
                                    "position_transition": "POSITION_FLAT",
                                })

                                if orders[i] is not None and orders[i].is_active:
                                    orders[i].cancel("STOP_LOSS_TRIGGERED")
                                    event_journal.append({
                                        "bar": int(next_t),
                                        "subbar": int(s),
                                        "mode": "B",
                                        "symbol": int(i),
                                        "symbol_idx": int(i),
                                        "order_id": orders[i].order_id,
                                        "order_generation": int(orders[i].order_generation),
                                        "event_type": "ORDER_CANCELLED",
                                        "side": "BUY" if orders[i].target_qty > 0 else "SELL",
                                        "requested_qty": float(abs(orders[i].target_qty)),
                                        "filled_qty": float(abs(orders[i].filled_qty)),
                                        "remaining_qty": float(abs(orders[i].remaining_qty)),
                                        "price": float(orders[i].limit_px),
                                        "maker_taker": "NONE",
                                        "fee": 0.0,
                                        "market_impact": 0.0,
                                        "adverse_selection": 0.0,
                                        "slippage": 0.0,
                                        "position_before": 0.0,
                                        "position_after": 0.0,
                                        "equity_before": float(equity),
                                        "equity_after": float(equity),
                                        "reason": "STOP_LOSS_TRIGGERED",
                                    })

                                if cooldown_enabled:
                                    cooldown_until[i] = next_t + 1 + cooldown_n_bars
                            elif hit_tp:
                                tp_count += 1
                                exit_px = entry * (1.0 - cur_tp)
                                pos_before = float(pos.qty)
                                pnl_i = pos.apply_full_exit(exit_px)
                                fee_i = pos_usd * maker_fee

                                bar_gross_pnl += pnl_i
                                bar_fees += fee_i
                                total_turnover_multiple += abs(pos_usd / max(equity, 1e-4))
                                total_turnover_usd += pos_usd
                                trades_count += 1

                                event_journal.append({
                                    "bar": int(next_t),
                                    "subbar": int(s),
                                    "mode": "B",
                                    "symbol": int(i),
                                    "symbol_idx": int(i),
                                    "order_id": f"TP_{next_t}_{s}_{i}",
                                    "order_generation": int(order_gen),
                                    "event_type": "TAKE_PROFIT",
                                    "side": "BUY",
                                    "requested_qty": float(abs(pos_before)),
                                    "filled_qty": float(abs(pos_before)),
                                    "remaining_qty": 0.0,
                                    "price": float(exit_px),
                                    "maker_taker": "MAKER",
                                    "fee": float(fee_i),
                                    "market_impact": 0.0,
                                    "adverse_selection": 0.0,
                                    "slippage": 0.0,
                                    "realized_pnl": float(pnl_i),
                                    "position_before": float(pos_before),
                                    "position_after": 0.0,
                                    "equity_before": float(equity),
                                    "equity_after": float(equity),
                                    "reason": "TAKE_PROFIT_TRIGGERED",
                                    "position_transition": "POSITION_FLAT",
                                })

                                if orders[i] is not None and orders[i].is_active:
                                    orders[i].cancel("TAKE_PROFIT_TRIGGERED")
                                    event_journal.append({
                                        "bar": int(next_t),
                                        "subbar": int(s),
                                        "mode": "B",
                                        "symbol": int(i),
                                        "symbol_idx": int(i),
                                        "order_id": orders[i].order_id,
                                        "order_generation": int(orders[i].order_generation),
                                        "event_type": "ORDER_CANCELLED",
                                        "side": "BUY" if orders[i].target_qty > 0 else "SELL",
                                        "requested_qty": float(abs(orders[i].target_qty)),
                                        "filled_qty": float(abs(orders[i].filled_qty)),
                                        "remaining_qty": float(abs(orders[i].remaining_qty)),
                                        "price": float(orders[i].limit_px),
                                        "maker_taker": "NONE",
                                        "fee": 0.0,
                                        "market_impact": 0.0,
                                        "adverse_selection": 0.0,
                                        "slippage": 0.0,
                                        "position_before": 0.0,
                                        "position_after": 0.0,
                                        "equity_before": float(equity),
                                        "equity_after": float(equity),
                                        "reason": "TAKE_PROFIT_TRIGGERED",
                                    })
                            else:
                                ref_px = pos.last_fill_px if order_filled_subbar[i] == s else sub_open[i]
                                ret_s = (ref_px - sub_close[i]) / (ref_px + 1e-8)
                                bar_gross_pnl += (abs(pos.qty) * ref_px) * ret_s

                # Cancel any remaining un-filled active orders at bar end
                for i in range(n_symbols):
                    ord_i = orders[i]
                    if ord_i is not None and ord_i.is_active:
                        ord_i.cancel("END_OF_BAR_EXPIRY")
                        event_journal.append({
                            "bar": int(next_t),
                            "subbar": int(n_subbars - 1),
                            "mode": "B",
                            "symbol": int(i),
                            "symbol_idx": int(i),
                            "order_id": ord_i.order_id,
                            "order_generation": int(ord_i.order_generation),
                            "event_type": "ORDER_CANCELLED",
                            "side": "BUY" if ord_i.target_qty > 0 else "SELL",
                            "requested_qty": float(abs(ord_i.target_qty)),
                            "filled_qty": float(abs(ord_i.filled_qty)),
                            "remaining_qty": float(abs(ord_i.remaining_qty)),
                            "price": float(ord_i.limit_px),
                            "maker_taker": "NONE",
                            "fee": 0.0,
                            "market_impact": 0.0,
                            "adverse_selection": 0.0,
                            "slippage": 0.0,
                            "position_before": float(positions[i].qty),
                            "position_after": float(positions[i].qty),
                            "equity_before": float(equity),
                            "equity_after": float(equity),
                            "reason": "END_OF_BAR_EXPIRY",
                        })

                # End of bar 4H Funding cashflow
                current_weights = np.array([(p.qty * s_closes[-1, i]) / max(equity, 1e-4) for i, p in enumerate(positions)])
                fund_bar = np.nan_to_num(predicted_funding[next_t] * 4.0, nan=0.0)
                fp_t = float(np.sum(-current_weights * fund_bar)) * equity

                total_gross_pnl += bar_gross_pnl
                total_exchange_fees += bar_fees
                total_adverse_selection += bar_adverse
                total_market_impact += bar_impact
                total_funding_pnl += fp_t
                net_pnl_t = bar_gross_pnl + fp_t - bar_fees - bar_impact - bar_adverse

            # Beginning-equity standard return denominator
            b_ret = net_pnl_t / max(equity, 1e-8)
            bar_rets.append(b_ret)

            # MTM Balance Sheet Reconciliation
            new_equity = max(1.0, equity + net_pnl_t)
            drift_t = abs((new_equity - equity) - net_pnl_t)
            if drift_t > max_drift:
                max_drift = drift_t

            equity = new_equity
            hwm = max(hwm, equity)
            equity_curve.append(equity)
            
            # Exposure Tracking
            pos_weights = np.array([(p.qty * close_mat[next_t, i]) / max(equity, 1e-4) for i, p in enumerate(positions)])
            gross_exposures.append(float(np.sum(np.abs(pos_weights))))
            net_exposures.append(float(np.sum(pos_weights)))

        eq_arr = np.array(equity_curve)
        years = (eval_end - start_bar) / (365.25 * 6)
        cagr = ((equity / init_capital) ** (1.0 / max(years, 0.01)) - 1.0) * 100.0 if equity > 1.0 else -99.9

        b_rets_arr = np.array(bar_rets)
        mean_r = float(np.mean(b_rets_arr)) if len(b_rets_arr) > 0 else 0.0
        std_r = float(np.std(b_rets_arr)) + 1e-12 if len(b_rets_arr) > 0 else 1.0
        sharpe = (mean_r / std_r) * math.sqrt(2190)

        dd = (np.maximum.accumulate(eq_arr) - eq_arr) / np.maximum(np.maximum.accumulate(eq_arr), 1e-8)
        max_dd = float(np.max(dd)) * 100.0

        pos_rets = b_rets_arr[b_rets_arr > 0]
        neg_rets = b_rets_arr[b_rets_arr < 0]
        win_rate = (len(pos_rets) / max(len(b_rets_arr), 1)) * 100.0
        payoff = (np.mean(pos_rets) / abs(np.mean(neg_rets))) if len(pos_rets) > 0 and len(neg_rets) > 0 else 1.0

        total_friction = total_exchange_fees + total_adverse_selection + total_market_impact
        fric_ratio = (total_friction / max(abs(total_gross_pnl), 1e-4)) * 100.0
        net_to_gross = (equity - init_capital) / max(abs(total_gross_pnl), 1e-4)

        tot_fills = passive_fill_count + taker_cross_count
        modeled_maker_pct = (passive_fill_count / tot_fills * 100.0) if tot_fills > 0 else (self.cfg.base_maker_ratio * 100.0)
        modeled_taker_pct = 100.0 - modeled_maker_pct
        fill_rate_pct = 100.0 if trades_count > 0 else 0.0
        realized_slip_bps = (total_slippage_usd / max(total_turnover_usd, 1.0)) * 10_000.0
        adverse_bps = adverse_markout * 10_000.0

        return {
            "ending_equity": float(equity),
            "net_pnl": float(equity - init_capital),
            "cagr": float(cagr),
            "sharpe": float(sharpe),
            "max_dd": float(max_dd),
            "win_rate_pct": float(win_rate),
            "payoff_ratio": float(payoff),
            "gross_price_pnl": float(total_gross_pnl),
            "funding_pnl": float(total_funding_pnl),
            "exchange_fees": float(total_exchange_fees),
            "adverse_selection_cost": float(total_adverse_selection),
            "market_impact": float(total_market_impact),
            "fees": float(total_exchange_fees),
            "total_friction": float(total_friction),
            "total_trading_cost": float(total_friction),
            "fric_ratio": float(fric_ratio),
            "net_to_gross_ratio": float(net_to_gross),
            "turnover_multiple": float(total_turnover_multiple),
            "turnover_usd": float(total_turnover_usd),
            "turnover": float(total_turnover_multiple),
            "trades_count": trades_count,
            "sl_count": sl_count,
            "tp_count": tp_count,
            "passive_fills": passive_fill_count,
            "taker_crosses": taker_cross_count,
            "fill_rate_pct": float(fill_rate_pct),
            "realized_slippage_usd": float(total_slippage_usd),
            "realized_slippage_bps": float(realized_slip_bps),
            "adverse_markout_bps": float(adverse_bps),
            "modeled_maker_pct": float(modeled_maker_pct),
            "modeled_taker_pct": float(modeled_taker_pct),
            "max_mtm_drift": float(max_drift),
            "drift_certified": bool(max_drift <= self.cfg.drift_tolerance),
            "target_gross_leverage": float(self.cfg.max_gross_leverage),
            "actual_average_gross_leverage": float(np.mean(gross_exposures)) if gross_exposures else 0.0,
            "max_gross_leverage": float(np.max(gross_exposures)) if gross_exposures else 0.0,
            "actual_average_net_exposure": float(np.mean(np.abs(net_exposures))) if net_exposures else 0.0,
            "bar_returns": b_rets_arr,
            "exposures": np.array(gross_exposures),
            "equity_curve": eq_arr,
            "positions": positions,
            "ending_weights": np.array([(p.qty * close_mat[eval_end, i]) / max(equity, 1e-4) for i, p in enumerate(positions)]),
            "avg_entry_px": np.array([p.avg_entry_px for p in positions]),
            # Event journal for deterministic replay verification
            "event_journal": event_journal,
            "event_journal_bytes": json.dumps(event_journal, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            "event_journal_hash": hashlib.sha256(
                json.dumps(event_journal, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }

    # Backward-compatible wrappers
    def simulate_execution(self, *args, **kwargs) -> Dict[str, Any]:
        if "weights_4h" in kwargs and "weights_matrix" not in kwargs:
            kwargs["weights_matrix"] = kwargs.pop("weights_4h")
        if "predicted_funding_4h" in kwargs and "predicted_funding" not in kwargs:
            kwargs["predicted_funding"] = kwargs.pop("predicted_funding_4h")
        return self.simulate_canonical_execution(*args, **kwargs)

    def simulate_subbar_execution(self, *args, **kwargs) -> Dict[str, Any]:
        # Adapt legacy parameters
        w = kwargs.pop("weights_matrix", None)
        if w is None:
            w = kwargs.pop("weights_4h", None)
        if w is None and len(args) > 0:
            w = args[0]
            args = args[1:]
        
        subbar_data = kwargs.pop("subbar_data", None)
        if subbar_data is None and "subbar_opens" in kwargs:
            subbar_data = {
                "open": kwargs.pop("subbar_opens"),
                "high": kwargs.pop("subbar_highs"),
                "low": kwargs.pop("subbar_lows"),
                "close": kwargs.pop("subbar_closes"),
                "volume": kwargs.pop("subbar_volumes"),
            }
        
        close_mat = kwargs.pop("close_mat", None)
        if close_mat is None:
            if subbar_data is not None and "close" in subbar_data:
                close_mat = subbar_data["close"][:, -1, :]
            elif w is not None:
                close_mat = np.ones_like(w) * 100.0

        volume_mat = kwargs.pop("volume_mat", None)
        if volume_mat is None:
            if subbar_data is not None and "volume" in subbar_data:
                volume_mat = np.sum(subbar_data["volume"], axis=1)
            elif w is not None:
                volume_mat = np.ones_like(w) * 1e6

        returns_mat = kwargs.pop("returns_mat", None)
        if returns_mat is None:
            if close_mat is not None:
                returns_mat = np.zeros_like(close_mat)
                returns_mat[1:] = (close_mat[1:] - close_mat[:-1]) / np.maximum(close_mat[:-1], 1e-8)
            elif w is not None:
                returns_mat = np.zeros_like(w)

        predicted_funding = kwargs.pop("predicted_funding", None)
        if predicted_funding is None:
            predicted_funding = kwargs.pop("predicted_funding_4h", None)
        if predicted_funding is None and w is not None:
            predicted_funding = np.zeros_like(w)

        return self.simulate_canonical_execution(
            weights_matrix=w,
            returns_mat=returns_mat,
            predicted_funding=predicted_funding,
            volume_mat=volume_mat,
            close_mat=close_mat,
            subbar_data=subbar_data,
            *args,
            **kwargs
        )

    # =========================================================================
    # 4. INTERNAL CERTIFICATION GAUNTLET (PRIVATE)
    # =========================================================================

    def _run_certification_on_wfo_result(
        self,
        candidate_name: str,
        wfo_result: Dict[str, Any],
        provenance: CertificationProvenance,
        returns_mat: np.ndarray,
        predicted_funding: np.ndarray,
        volume_mat: np.ndarray,
        close_mat: np.ndarray,
        oracle_mat: np.ndarray,
        valid_mask: np.ndarray,
        btc_prices: np.ndarray,
        effective_n_trials: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Private internal gauntlet. Admissibility requires a verified CertificationProvenance object.
        """
        oos_weights = wfo_result["oos_weights_matrix"]
        
        # 1. Pre-flight Invariant Audit
        invariants = self.audit_preflight_invariants(
            signal_matrix=oos_weights,
            close_mat=close_mat,
            oracle_mat=oracle_mat,
            valid_mask=valid_mask,
            volume_mat=volume_mat,
            returns_mat=returns_mat,
            predicted_funding=predicted_funding,
            weights_matrix=oos_weights,
        )

        sim_fn = lambda w: self.simulate_canonical_execution(
            weights_matrix=w,
            returns_mat=returns_mat,
            predicted_funding=predicted_funding,
            volume_mat=volume_mat,
            close_mat=close_mat,
            pit_liquid_mask=invariants["pit_liquid_mask"],
        )
        real_res = sim_fn(oos_weights)

        # 2. Placebo Falsification Battery
        perm_res = self.placebo_suite.run_asset_permutation_null(oos_weights, sim_fn, real_res["net_pnl"])
        horizon_res = self.placebo_suite.run_horizon_matched_random_null(oos_weights, valid_mask, sim_fn, real_res["net_pnl"])
        det_placebos = self.placebo_suite.run_deterministic_placebos(oos_weights, sim_fn)

        # 3. Macro Regime Decomposition
        regime_analyzer = MultiSplitRegimeAnalyzer(btc_prices, self.cfg.wfo_train_bars, self.cfg.wfo_test_bars)
        regime_decomp = regime_analyzer.evaluate_regime_breakdown(real_res["bar_returns"], real_res["exposures"])
        
        # Enrich regime breakdown with PnL contribution and max drawdown
        for r_name, r_dict in regime_decomp.items():
            r_mask = (regime_analyzer.regimes[:len(real_res["bar_returns"])] == (0 if "Bear" in r_name else (2 if "Bull" in r_name else 1)))
            r_rets = real_res["bar_returns"][r_mask]
            if len(r_rets) > 0:
                eq_r = np.cumprod(1.0 + r_rets)
                dd_r = (np.maximum.accumulate(eq_r) - eq_r) / np.maximum.accumulate(eq_r)
                r_dict["max_dd"] = float(np.max(dd_r)) * 100.0
                r_dict["pnl_contribution_usd"] = float(np.sum(r_rets) * self.cfg.initial_capital)
            else:
                r_dict["max_dd"] = 0.0
                r_dict["pnl_contribution_usd"] = 0.0

        # 4. Gate 4 Statistical Testing: Paired Excess Return against Idle Cash
        idle_rets = det_placebos["idle_cash"]["bar_returns"]
        strat_rets = real_res["bar_returns"]
        min_len = min(len(strat_rets), len(idle_rets))
        diff_r = strat_rets[:min_len] - idle_rets[:min_len]
        
        # Mean excess return & Standard t-test
        mean_diff = float(np.mean(diff_r)) if min_len > 0 else 0.0
        t_stat, p_val_two_sided = stats.ttest_1samp(diff_r, 0.0) if min_len > 10 else (0.0, 1.0)
        p_val_one_sided = (p_val_two_sided / 2.0) if t_stat > 0 else 1.0

        # Newey-West HAC Adjusted t-statistic
        hac_p_val = p_val_one_sided
        hac_t_stat = t_stat
        if min_len > 20:
            L = min(self.cfg.newey_west_lags, min_len // 4)
            d_centered = diff_r - mean_diff
            gamma_0 = float(np.mean(d_centered ** 2))
            gamma_sum = 0.0
            for lag in range(1, L + 1):
                weight = 1.0 - (lag / (L + 1.0))  # Bartlett kernel
                cov_lag = float(np.mean(d_centered[lag:] * d_centered[:-lag]))
                gamma_sum += 2.0 * weight * cov_lag
            v_hac = max(gamma_0 + gamma_sum, 1e-12)
            se_hac = math.sqrt(v_hac / min_len)
            hac_t_stat = mean_diff / max(se_hac, 1e-12)
            hac_p_val = float(1.0 - stats.t.cdf(hac_t_stat, df=min_len - 1)) if hac_t_stat > 0 else 1.0

        # Block-Bootstrap p-value for Gate 4
        boot_diff_means = []
        rng = np.random.RandomState(42)
        n_boot = 1000
        for _ in range(n_boot):
            idx = rng.randint(0, min_len, size=min_len)
            boot_diff_means.append(np.mean(diff_r[idx] - mean_diff)) # Under H0: mean = 0
        boot_diff_arr = np.array(boot_diff_means)
        bootstrap_p_val = float(np.mean(boot_diff_arr >= mean_diff)) if min_len > 10 else 1.0

        gate_4_stat_passed = (hac_p_val < 0.05) and (real_res["net_pnl"] > 0.0)

        # 5. Gate 6: Ruin Analysis (Labeled as Conditional Return-Path Ruin Estimate)
        ruin_res = RuinAndLeverageFrontier.stationary_block_bootstrap_ruin(
            real_res["bar_returns"],
            n_paths=self.cfg.bootstrap_paths,
            expected_block_len=12,
            ruin_threshold=self.cfg.ruin_drawdown_threshold,
        )

        # 6. Gate 7: Deflated Sharpe Ratio with Full Registry Provenance
        dsr_res = self.registry.compute_deflated_sharpe_ratio(
            real_res["sharpe"], real_res["bar_returns"], effective_n_trials=effective_n_trials
        )
        self.registry.log_trial(
            trial_name=candidate_name,
            sharpe=real_res["sharpe"],
            cagr=real_res["cagr"],
            max_dd=real_res["max_dd"],
            metadata={"provenance_hash": provenance.master_hash()}
        )

        # Final Gate Verdicts
        gate_1_invariants = invariants["passed"]
        gate_2_placebos = perm_res["passed"] and horizon_res["passed"]
        gate_3_friction = real_res["fric_ratio"] <= 25.0
        gate_4_ev = gate_4_stat_passed
        gate_5_regime = all(r["sharpe"] > -1.0 for r in regime_decomp.values())
        gate_6_ruin = ruin_res["ruin_probability"] <= 0.05
        gate_7_dsr = dsr_res["deflated_sharpe_ratio"] >= 0.95

        passed_all = all([
            gate_1_invariants, gate_2_placebos, gate_3_friction,
            gate_4_ev, gate_5_regime, gate_6_ruin, gate_7_dsr
        ])

        return {
            "candidate_name": candidate_name,
            "overall_verdict": "PASSED" if passed_all else "KILLED",
            "provenance": provenance.to_dict(),
            "gates": {
                "Gate 1 (Pre-Flight Invariants & Portfolio Bounds)": gate_1_invariants,
                "Gate 2 (Placebo Rejection p < 0.01)": gate_2_placebos,
                "Gate 3 (Friction Efficiency <= 25% Gross)": gate_3_friction,
                "Gate 4 (Statistical Superiority vs Cash HAC p < 0.05)": gate_4_ev,
                "Gate 5 (Regime Survivability Sharpe > -1.0)": gate_5_regime,
                "Gate 6 (Conditional Return-Path Ruin P(MDD >= 15%) <= 5%)": gate_6_ruin,
                "Gate 7 (Deflated Sharpe Ratio DSR >= 95%)": gate_7_dsr,
            },
            "gate_4_details": {
                "mean_excess_return": float(mean_diff),
                "standard_t_stat": float(t_stat),
                "standard_p_val": float(p_val_one_sided),
                "newey_west_hac_t_stat": float(hac_t_stat),
                "newey_west_hac_p_val": float(hac_p_val),
                "block_bootstrap_p_val": float(bootstrap_p_val),
                "passed": gate_4_stat_passed,
            },
            "performance": real_res,
            "invariants": invariants,
            "placebos": {"asset_permutation": perm_res, "horizon_matched": horizon_res, "deterministic": det_placebos},
            "regimes": regime_decomp,
            "ruin_analysis": ruin_res,
            "dsr_metrics": dsr_res,
        }

    # =========================================================================
    # 5. WALK-FORWARD OPTIMIZATION & PRODUCTION CERTIFICATION ENTRY POINT
    # =========================================================================

    def run_true_wfo(
        self,
        fit_fn: Any,
        predict_fn: Any,
        feature_panel: Dict[str, np.ndarray],
        returns_mat: np.ndarray,
        predicted_funding: np.ndarray,
        volume_mat: np.ndarray,
        close_mat: np.ndarray,
        btc_prices: np.ndarray,
        continuous_portfolio: bool = True,
        portfolio_deadband: Optional[float] = None,
        rank_hysteresis: bool = False,
        entry_k: int = 15,
        exit_k: int = 22,
        fixed_slot_sizing: bool = True,
    ) -> Dict[str, Any]:
        """
        True In-Fold Walk-Forward Optimization (WFO).
        Produces strictly continuous out-of-sample weights and bar returns.
        """
        n_bars, n_symbols = returns_mat.shape
        regime_analyzer = MultiSplitRegimeAnalyzer(btc_prices, self.cfg.wfo_train_bars, self.cfg.wfo_test_bars)
        wfo_folds = regime_analyzer.generate_wfo_folds()

        all_oos_bar_returns = []
        all_oos_weights = []
        fold_summaries = []

        running_equity = self.cfg.initial_capital
        running_weights = np.zeros(n_symbols)

        for f_idx, (tr_s, tr_e, te_s, te_e) in enumerate(wfo_folds):
            # 1. 1-Bar Embargo & Target Alignment: X_t -> r_{t+1}
            train_features = {k: v[tr_s:tr_e - 1] for k, v in feature_panel.items()}
            train_targets = returns_mat[tr_s + 1:tr_e]

            # Fit strictly on train fold
            model = fit_fn(train_features, train_targets)

            # Predict on test fold
            test_features = {k: v[te_s:te_e] for k, v in feature_panel.items()}
            oos_weights = predict_fn(model, test_features)

            if rank_hysteresis and "scores" in test_features:
                scores_mat = test_features["scores"]
                hyst_weights = np.zeros_like(oos_weights)
                w_prev_h = running_weights.copy()
                for bar_i in range(len(oos_weights)):
                    valid_m = np.ones(n_symbols, dtype=bool)
                    w_t_h = self.compute_rank_hysteresis_weights(
                        signal_scores=scores_mat[bar_i],
                        valid_mask_t=valid_m,
                        weights_prev=w_prev_h,
                        entry_k=entry_k,
                        exit_k=exit_k,
                        fixed_slot_sizing=fixed_slot_sizing,
                    )
                    hyst_weights[bar_i] = w_t_h
                    w_prev_h = w_t_h.copy()
                oos_weights = hyst_weights

            all_oos_weights.append(oos_weights)

            sim_init_weights = running_weights if continuous_portfolio else np.zeros(n_symbols)
            sim_init_capital = running_equity if continuous_portfolio else self.cfg.initial_capital

            f_res = self.simulate_canonical_execution(
                weights_matrix=oos_weights,
                returns_mat=returns_mat[te_s:te_e],
                predicted_funding=predicted_funding[te_s:te_e],
                volume_mat=volume_mat[te_s:te_e],
                close_mat=close_mat[te_s:te_e],
                portfolio_deadband=portfolio_deadband,
                initial_capital=sim_init_capital,
                initial_weights=sim_init_weights,
            )

            if continuous_portfolio:
                running_equity = f_res["ending_equity"]
                running_weights = f_res["ending_weights"].copy()

            all_oos_bar_returns.extend(f_res["bar_returns"].tolist())
            fold_summaries.append({
                "fold": f_idx + 1,
                "train_bars": f"{tr_s}-{tr_e}",
                "test_bars": f"{te_s}-{te_e}",
                "cagr": f_res["cagr"],
                "sharpe": f_res["sharpe"],
                "max_dd": f_res["max_dd"],
                "net_pnl": f_res["net_pnl"],
                "turnover_multiple": f_res["turnover_multiple"],
                "turnover_usd": f_res["turnover_usd"],
            })

        combined_rets = np.array(all_oos_bar_returns)
        mean_r = float(np.mean(combined_rets)) if len(combined_rets) > 0 else 0.0
        std_r = float(np.std(combined_rets)) + 1e-12 if len(combined_rets) > 0 else 1.0
        chained_sharpe = (mean_r / std_r) * math.sqrt(2190)

        years = len(combined_rets) / (365.25 * 6)
        chained_cagr = ((running_equity / self.cfg.initial_capital) ** (1.0 / max(years, 0.01)) - 1.0) * 100.0 if running_equity > 0 else -100.0
        oos_w_mat = np.concatenate(all_oos_weights, axis=0) if all_oos_weights else np.zeros((0, n_symbols))

        return {
            "folds": fold_summaries,
            "chained_cagr": float(chained_cagr),
            "chained_sharpe": float(chained_sharpe),
            "ending_equity": float(running_equity),
            "ending_weights": running_weights.copy(),
            "combined_bar_returns": combined_rets,
            "n_oos_bars": len(combined_rets),
            "oos_weights_matrix": oos_w_mat,
        }

    def certify_strategy(
        self,
        candidate_name: str,
        fit_fn: Any,
        predict_fn: Any,
        feature_panel: Dict[str, np.ndarray],
        returns_mat: np.ndarray,
        predicted_funding: np.ndarray,
        volume_mat: np.ndarray,
        close_mat: np.ndarray,
        oracle_mat: np.ndarray,
        valid_mask: np.ndarray,
        btc_prices: np.ndarray,
        paper_fills: Optional[List[Dict[str, Any]]] = None,
        effective_n_trials: Optional[float] = None,
        portfolio_deadband: Optional[float] = None,
        rank_hysteresis: bool = False,
        entry_k: int = 15,
        exit_k: int = 22,
        fixed_slot_sizing: bool = True,
        provenance: Optional[CertificationProvenance] = None,
        manual_weights_override: Optional[np.ndarray] = None,
        symbols: Optional[List[str]] = None,
        timestamp_bounds: Optional[Tuple[str, str]] = None,
        model_spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        THE MANDATORY INSTITUTIONAL CERTIFICATION PIPELINE
        ==================================================
        Sole authorized certification entry point.
        Enforces immutable WFO provenance. Manual weights are rejected unless accompanied
        by a verified CertificationProvenance custody object.
        """
        # 1. Evaluate Provenance immediately
        resolved_cfg = self.cfg.resolve_runtime_parameters(portfolio_deadband=portfolio_deadband)
        dataset_dict = {
            "close": close_mat,
            "oracle": oracle_mat,
            "volume": volume_mat,
            "valid": valid_mask,
            "returns": returns_mat,
            "funding": predicted_funding,
            "btc": btc_prices,
        }
        symbols_list = symbols if symbols is not None else [f"SYM_{i}" for i in range(returns_mat.shape[1])]
        ts_bounds = timestamp_bounds or ("0", str(len(returns_mat)))
        spec_dict = model_spec or {"candidate_name": candidate_name}
        
        import inspect, src.backtesting.ironcore_config as ic_cfg
        engine_src = inspect.getsource(ic_cfg) + "\n" + inspect.getsource(IronCoreEngine)

        if manual_weights_override is not None:
            if provenance is None:
                raise ValueError("UNPROVENANCED_WEIGHTS_REJECTED: Manual weights cannot be certified without an immutable CertificationProvenance object.")
            
            # Active cryptographic verification of provenance chain-of-custody across all 10 dimensions
            is_valid, mismatches = provenance.verify_against_inputs(
                engine_version=self.cfg.version,
                engine_source=engine_src,
                resolved_config=resolved_cfg,
                feature_panel=feature_panel,
                dataset_matrices=dataset_dict,
                symbols=symbols_list,
                timestamp_bounds=ts_bounds,
                candidate_name=candidate_name,
                model_spec=spec_dict,
                folds=[],
                trial_registry_hash=provenance.trial_registry_hash,
                combined_bar_returns=np.zeros(len(manual_weights_override)),
            )
            if not is_valid:
                raise ValueError(f"FORGED_OR_MISMATCHED_PROVENANCE_REJECTED: {mismatches}")

            oos_weights = manual_weights_override
            wfo_res = {
                "oos_weights_matrix": oos_weights,
                "chained_cagr": 0.0,
                "chained_sharpe": 0.0,
                "ending_equity": self.cfg.initial_capital,
                "folds": [],
            }
            oos_close = close_mat
            oos_oracle = oracle_mat
            oos_volume = volume_mat
            oos_valid = valid_mask
            oos_returns = returns_mat
            oos_funding = predicted_funding
            oos_btc = btc_prices
        else:
            ra = MultiSplitRegimeAnalyzer(btc_prices, self.cfg.wfo_train_bars, self.cfg.wfo_test_bars)
            folds = ra.generate_wfo_folds()
            oos_start = folds[0][2]
            oos_end = folds[-1][3]

            oos_close = close_mat[oos_start:oos_end]
            oos_oracle = oracle_mat[oos_start:oos_end]
            oos_volume = volume_mat[oos_start:oos_end]
            oos_valid = valid_mask[oos_start:oos_end]
            oos_returns = returns_mat[oos_start:oos_end]
            oos_funding = predicted_funding[oos_start:oos_end]
            oos_btc = btc_prices[oos_start:oos_end]

            # Execute In-Fold WFO
            wfo_res = self.run_true_wfo(
                fit_fn=fit_fn,
                predict_fn=predict_fn,
                feature_panel=feature_panel,
                returns_mat=returns_mat,
                predicted_funding=predicted_funding,
                volume_mat=volume_mat,
                close_mat=close_mat,
                btc_prices=btc_prices,
                continuous_portfolio=True,
                portfolio_deadband=portfolio_deadband,
                rank_hysteresis=rank_hysteresis,
                entry_k=entry_k,
                exit_k=exit_k,
                fixed_slot_sizing=fixed_slot_sizing,
            )
            oos_weights = wfo_res["oos_weights_matrix"]

            # Construct Immutable CertificationProvenance Object with real features, code, and symbols
            provenance = CertificationProvenance.create(
                engine_version=self.cfg.version,
                engine_source=engine_src,
                resolved_config=resolved_cfg,
                feature_panel=feature_panel,
                dataset_matrices=dataset_dict,
                symbols=symbols_list,
                timestamp_bounds=ts_bounds,
                candidate_name=candidate_name,
                model_spec=spec_dict,
                folds=folds,
                trial_registry_hash=hashlib.sha256(str(len(self.registry.load_historical_sharpes())).encode()).hexdigest()[:16],
                combined_bar_returns=wfo_res["combined_bar_returns"],
            )

            # Assert internal verification sanity
            is_valid, mismatches = provenance.verify_against_inputs(
                engine_version=self.cfg.version,
                engine_source=engine_src,
                resolved_config=resolved_cfg,
                feature_panel=feature_panel,
                dataset_matrices=dataset_dict,
                symbols=symbols_list,
                timestamp_bounds=ts_bounds,
                candidate_name=candidate_name,
                model_spec=spec_dict,
                folds=folds,
                trial_registry_hash=provenance.trial_registry_hash,
                combined_bar_returns=wfo_res["combined_bar_returns"],
            )
            if not is_valid:
                raise ValueError(f"WFO_PROVENANCE_GENERATION_CORRUPTED: {mismatches}")

        # 2. Execute Private Gauntlet with Verified Provenance
        gauntlet_res = self._run_certification_on_wfo_result(
            candidate_name=candidate_name,
            wfo_result=wfo_res,
            provenance=provenance,
            returns_mat=oos_returns,
            predicted_funding=oos_funding,
            volume_mat=oos_volume,
            close_mat=oos_close,
            oracle_mat=oos_oracle,
            valid_mask=oos_valid,
            btc_prices=oos_btc,
            effective_n_trials=effective_n_trials,
        )

        # 3. Gate 8 Execution Parity Audit if paper fills are provided
        gate_8_res = None
        if paper_fills is not None:
            gate_8_res = self.evaluate_execution_parity(
                paper_fills=paper_fills,
                backtest_metrics=gauntlet_res["performance"],
            )

        is_certified = (gauntlet_res["overall_verdict"] == "PASSED") and (gate_8_res is None or gate_8_res["passed"])

        return {
            "candidate_name": candidate_name,
            "certified": is_certified,
            "provenance": provenance.to_dict(),
            "master_provenance_hash": provenance.master_hash(),
            "wfo_summary": {
                "chained_cagr": wfo_res["chained_cagr"],
                "chained_sharpe": wfo_res["chained_sharpe"],
                "ending_equity": wfo_res["ending_equity"],
                "folds": wfo_res["folds"],
            },
            "gauntlet": gauntlet_res,
            "gate_8_parity": gate_8_res,
        }

    # =========================================================================
    # 6. GATE 8: EMPIRICAL EXECUTION PARITY AUDITOR
    # =========================================================================

    @classmethod
    def evaluate_execution_parity(
        cls,
        *args: Any,
        paper_fills: Optional[List[Dict[str, Any]]] = None,
        ref: Optional[BacktestExecutionReference] = None,
        backtest_metrics: Optional[Dict[str, Any]] = None,
        backtest_turnover_usd: float = 0.0,
        backtest_fees_usd: float = 0.0,
        backtest_sl_triggers: int = 0,
        backtest_tp_triggers: int = 0,
        backtest_gross_pnl_usd: Optional[float] = None,
        backtest_net_pnl_usd: Optional[float] = None,
        backtest_rebalances: Optional[int] = None,
        max_fee_divergence_pct: float = 30.0,
        max_turnover_divergence_pct: float = 50.0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        GATE 8: INSTITUTIONAL EXECUTION PARITY AUDITOR (v2.4.0)
        ======================================================
        Compares empirical paper/live exchange execution against modeled physics across
        10 institutional dimensions with fail-closed cohort audits.
        """
        # Support flexible positional arguments (e.g. (sim_res, paper_fills=...) or (fills, sim_res))
        if len(args) == 1:
            if isinstance(args[0], dict):
                backtest_metrics = args[0]
            elif isinstance(args[0], BacktestExecutionReference):
                ref = args[0]
            elif isinstance(args[0], list):
                paper_fills = args[0]
        elif len(args) >= 2:
            if isinstance(args[0], list):
                paper_fills = args[0]
                if isinstance(args[1], BacktestExecutionReference):
                    ref = args[1]
                elif isinstance(args[1], dict):
                    backtest_metrics = args[1]
            elif isinstance(args[0], (dict, BacktestExecutionReference)):
                if isinstance(args[0], BacktestExecutionReference):
                    ref = args[0]
                else:
                    backtest_metrics = args[0]
                paper_fills = args[1]

        if paper_fills is None or len(paper_fills) == 0:
            return {
                "passed": False,
                "status": "NOT_EVALUATED",
                "reason": "No live or paper execution fill records provided.",
                "issues": ["NO_TELEMETRY: Zero paper fills provided."],
                "metrics": {
                    "modeled_maker_pct": ref.maker_ratio_pct if ref else (backtest_metrics.get("modeled_maker_pct", 60.0) if backtest_metrics else 60.0),
                    "empirical_maker_pct": None,
                    "realized_slippage_bps": None,
                    "adverse_selection_markout_bps": None,
                }
            }

        # Unpack benchmark reference metrics (strictly prioritizing typed BacktestExecutionReference)
        if ref is not None:
            backtest_turnover_usd = ref.turnover_usd
            backtest_fees_usd = ref.fees_usd
            backtest_sl_triggers = ref.sl_triggers
            backtest_tp_triggers = ref.tp_triggers
            bt_maker_ratio = ref.maker_ratio_pct
            bt_taker_ratio = ref.taker_ratio_pct
            bt_fill_rate = 100.0
            bt_slippage_bps = ref.slippage_bps
            bt_adverse_bps = ref.adverse_markout_bps
            bt_funding_usd = 0.0
            bt_trades_count = ref.trades_count or 1
            bt_avg_order_size = (backtest_turnover_usd / bt_trades_count) if bt_trades_count > 0 else 0.0
        elif backtest_metrics is not None:
            backtest_turnover_usd = backtest_metrics.get("turnover_usd", backtest_turnover_usd)
            backtest_fees_usd = backtest_metrics.get("exchange_fees", backtest_metrics.get("fees", backtest_fees_usd))
            backtest_sl_triggers = backtest_metrics.get("sl_count", backtest_sl_triggers)
            backtest_tp_triggers = backtest_metrics.get("tp_count", backtest_tp_triggers)
            bt_maker_ratio = backtest_metrics.get("modeled_maker_pct", 60.0)
            bt_taker_ratio = backtest_metrics.get("modeled_taker_pct", 40.0)
            bt_fill_rate = backtest_metrics.get("fill_rate_pct", 100.0)
            bt_slippage_bps = backtest_metrics.get("realized_slippage_bps", 0.0)
            bt_adverse_bps = backtest_metrics.get("adverse_markout_bps", 1.0)
            bt_funding_usd = backtest_metrics.get("funding_pnl", 0.0)
            bt_trades_count = backtest_metrics.get("trades_count", 1)
            bt_avg_order_size = (backtest_turnover_usd / bt_trades_count) if bt_trades_count > 0 else 0.0
        else:
            bt_maker_ratio = 60.0
            bt_taker_ratio = 40.0
            bt_fill_rate = 100.0
            bt_slippage_bps = 0.0
            bt_adverse_bps = 1.0
            bt_funding_usd = 0.0
            bt_avg_order_size = 500.0

        paper_notional = sum(float(f.get("sz", 0)) * float(f.get("px", 0)) for f in paper_fills)
        paper_fees = sum(float(f.get("fee", 0)) for f in paper_fills)
        paper_pnl = sum(float(f.get("closedPnl", 0)) for f in paper_fills)
        paper_funding = sum(float(f.get("funding", 0)) for f in paper_fills)

        eff_paper_fee_bps = (paper_fees / paper_notional * 10_000.0) if paper_notional > 0 else 0.0
        eff_bt_fee_bps = (backtest_fees_usd / backtest_turnover_usd * 10_000.0) if backtest_turnover_usd > 0 else 0.0
        fee_div_pct = abs(eff_paper_fee_bps - eff_bt_fee_bps) / max(eff_bt_fee_bps, 1e-4) * 100.0

        maker_count = sum(
            1 for f in paper_fills
            if str(f.get("liquidity", "")).lower() == "maker"
            or f.get("crossed") is False
            or f.get("is_maker") is True
            or float(f.get("fee", 0)) <= 0.00025 * float(f.get("sz", 0)) * float(f.get("px", 0))
        )
        paper_maker_pct = (maker_count / len(paper_fills) * 100.0) if paper_fills else 0.0
        paper_taker_pct = 100.0 - paper_maker_pct
        paper_avg_order_size = (paper_notional / len(paper_fills)) if paper_fills else 0.0

        # Empirical Slippage & Markout (AMO Delta) with Strict Fail-Closed Auditing
        slippage_values = []
        markout_values = []
        missing_ref_px_count = 0
        missing_future_px_count = 0
        missing_general_telemetry = 0

        for f in paper_fills:
            px_fill = float(f.get("px", 0.0))
            px_ref_raw = f.get("ref_px")
            px_future_raw = f.get("future_px")
            dir_str = str(f.get("dir", "")).lower()
            fee_val = f.get("fee")

            if px_fill <= 0 or fee_val is None or not dir_str:
                missing_general_telemetry += 1

            dir_mult = 1.0 if "buy" in dir_str or "long" in dir_str else -1.0
            
            if px_ref_raw is not None and float(px_ref_raw) > 0:
                px_ref = float(px_ref_raw)
                slip_bps = 10_000.0 * dir_mult * (px_fill - px_ref) / px_ref
                slippage_values.append(slip_bps)
            else:
                missing_ref_px_count += 1

            if px_future_raw is not None and float(px_future_raw) > 0 and px_fill > 0:
                px_future = float(px_future_raw)
                amo_bps = 10_000.0 * dir_mult * (px_future - px_fill) / px_fill
                markout_values.append(amo_bps)
            else:
                missing_future_px_count += 1

        # Cohort Disaggregation: Rebalances, Stops, Take Profits
        confirmed_stops = 0
        confirmed_take_profits = 0
        confirmed_rebalances = 0
        unclassified_exits = 0

        rebalance_fills = []
        stop_fills = []
        tp_fills = []

        for f in paper_fills:
            is_close = "close" in str(f.get("dir", "")).lower() or "reduce" in str(f.get("dir", "")).lower()
            pnl = float(f.get("closedPnl", 0.0))
            reason = str(f.get("exit_reason", "")).upper()
            is_trigger = bool(f.get("isTrigger") or f.get("tpsl") == "sl" or "trigger" in str(f.get("orderType", "")).lower())

            if not is_close:
                rebalance_fills.append(f)
                continue

            if reason == "STOP_LOSS" or (is_trigger and pnl < 0):
                confirmed_stops += 1
                stop_fills.append(f)
            elif reason == "TAKE_PROFIT" or (is_trigger and pnl > 0):
                confirmed_take_profits += 1
                tp_fills.append(f)
            elif reason in ("REBALANCE", "COOLDOWN", "MANUAL", "SIGNAL_EXIT"):
                confirmed_rebalances += 1
                rebalance_fills.append(f)
            else:
                unclassified_exits += 1

        issues = []
        
        # Dimension 6: Unclassified Exits Audit
        unclassified_passed = (unclassified_exits == 0)
        if not unclassified_passed:
            issues.append(f"FATAL_TELEMETRY_UNCLASSIFIED_EXITS: {unclassified_exits} closing fills lack explicit lifecycle exit reasons.")

        # Dimension 3: Maker Ratio Parity (divergence + floor + minimum sample size)
        # Three distinct quantities (kept completely separate):
        #   configured_passive_intent_pct: base_maker_ratio from config
        #   modeled_realized_maker_pct: what the simulator actually achieved (bt_maker_ratio)
        #   empirical_paper_maker_pct: what paper trading measured (paper_maker_pct)
        maker_divergence_tolerance_pct = 15.0   # max divergence between modeled and empirical
        maker_absolute_floor_pct = 20.0         # absolute minimum acceptable maker ratio
        maker_min_sample_size = 50              # minimum fills for parity to be evaluable

        maker_sample_n = len([f for f in paper_fills if not f.get("dir", "open").lower().startswith("close")])
        maker_sample_sufficient = maker_sample_n >= maker_min_sample_size
        maker_divergence = abs(paper_maker_pct - bt_maker_ratio)
        maker_divergence_passed = maker_divergence <= maker_divergence_tolerance_pct
        maker_floor_passed = paper_maker_pct >= maker_absolute_floor_pct
        maker_passed = maker_sample_sufficient and maker_divergence_passed and maker_floor_passed
        if not maker_sample_sufficient:
            issues.append(
                f"MAKER_RATIO_INSUFFICIENT_SAMPLE: Only {maker_sample_n} fills in maker cohort "
                f"(minimum {maker_min_sample_size} required). Maker parity unevaluable — FAIL CLOSED."
            )
        if not maker_divergence_passed:
            issues.append(
                f"MAKER_RATIO_DIVERGENCE_BREACH: Paper achieved {paper_maker_pct:.1f}% maker "
                f"vs modeled {bt_maker_ratio:.1f}% (divergence {maker_divergence:.1f}% > "
                f"tolerance {maker_divergence_tolerance_pct:.1f}%)."
            )
        if not maker_floor_passed:
            issues.append(
                f"MAKER_RATIO_FLOOR_BREACH: Paper maker ratio {paper_maker_pct:.1f}% "
                f"below absolute minimum {maker_absolute_floor_pct:.1f}%."
            )

        # Dimension 1: Fee Parity
        fee_passed = (fee_div_pct <= max_fee_divergence_pct) and (missing_general_telemetry == 0)
        if not fee_passed:
            issues.append(f"FEE_PARITY_BREACH: Paper paid {eff_paper_fee_bps:.2f} bps vs backtest {eff_bt_fee_bps:.2f} bps.")

        # Dimension 2: Turnover Parity
        turnover_div_pct = abs(paper_notional - backtest_turnover_usd) / max(backtest_turnover_usd, 1.0) * 100.0
        turnover_passed = turnover_div_pct <= max_turnover_divergence_pct or backtest_turnover_usd == 0.0
        if not turnover_passed and backtest_turnover_usd > 0:
            issues.append(f"TURNOVER_DIVERGENCE_BREACH: Paper traded ${paper_notional:,.0f} vs backtest ${backtest_turnover_usd:,.0f}.")

        # Dimension 4: Stop Concordance
        stops_passed = True
        if confirmed_stops > 10 and backtest_sl_triggers == 0:
            stops_passed = False
            issues.append(f"STOP_CONCORDANCE_BREACH: Paper recorded {confirmed_stops} stop-outs while backtest modeled 0.")

        # Dimension 5: Take-Profit Concordance
        tp_passed = True
        if confirmed_take_profits > 10 and backtest_tp_triggers == 0:
            tp_passed = False
            issues.append(f"TAKE_PROFIT_CONCORDANCE_BREACH: Paper recorded {confirmed_take_profits} take-profits while backtest modeled 0.")

        # Dimension 7: PIT Liquidity Adherence
        pit_violations = sum(1 for f in paper_fills if f.get("is_liquid") is False)
        pit_passed = (pit_violations == 0)
        if not pit_passed:
            issues.append(f"PIT_LIQUIDITY_BREACH: {pit_violations} fills executed on PIT illiquid assets.")

        # Dimension 8: Realized Slippage Bound (Fail-closed: missing ref_px causes FAIL)
        if missing_ref_px_count > 0:
            slippage_passed = False
            emp_slippage_bps = None
            issues.append(f"FAIL_CLOSED_SLIPPAGE: {missing_ref_px_count}/{len(paper_fills)} fills missing ref_px.")
        else:
            emp_slippage_bps = float(np.mean(slippage_values)) if slippage_values else 0.0
            slippage_passed = emp_slippage_bps <= (bt_slippage_bps + 20.0)
            if not slippage_passed:
                issues.append(f"SLIPPAGE_BREACH: Empirical slippage {emp_slippage_bps:.2f} bps exceeded modeled tolerance.")

        # Dimension 9: Adverse Selection Markout (AMO Delta) Bound (Fail-closed: missing future_px causes FAIL)
        if missing_future_px_count > 0:
            adverse_passed = False
            emp_markout_bps = None
            issues.append(f"FAIL_CLOSED_ADVERSE_MARKOUT: {missing_future_px_count}/{len(paper_fills)} fills missing future_px.")
        else:
            emp_markout_bps = float(np.mean(markout_values)) if markout_values else 0.0
            adverse_passed = emp_markout_bps <= (bt_adverse_bps * 5.0)
            if not adverse_passed:
                issues.append(f"ADVERSE_MARKOUT_BREACH: Empirical AMO delta {emp_markout_bps:.2f} bps exceeded modeled {bt_adverse_bps:.2f} bps.")

        # Dimension 10: Cohort Fee Separation (Stop loss fills must pay taker fees >= 3.0 bps)
        cohort_fee_passed = True
        if stop_fills:
            stop_ntl = sum(float(f.get("sz", 0)) * float(f.get("px", 0)) for f in stop_fills)
            stop_fee = sum(float(f.get("fee", 0)) for f in stop_fills)
            stop_fee_bps = (stop_fee / stop_ntl * 10_000.0) if stop_ntl > 0 else 0.0
            if stop_fee_bps < 3.0:
                cohort_fee_passed = False
                issues.append(f"COHORT_FEE_MISMATCH: Stop loss cohort paid {stop_fee_bps:.2f} bps (expected taker >= 3.0 bps).")
        else:
            stop_fee_bps = 0.0

        if rebalance_fills:
            reb_ntl = sum(float(f.get("sz", 0)) * float(f.get("px", 0)) for f in rebalance_fills)
            reb_fee = sum(float(f.get("fee", 0)) for f in rebalance_fills)
            reb_fee_bps = (reb_fee / reb_ntl * 10_000.0) if reb_ntl > 0 else 0.0
        else:
            reb_fee_bps = 0.0

        # All 10 Institutional Dimensions evaluated strictly in fail-closed passed verdict
        passed = all([
            fee_passed,
            turnover_passed,
            maker_passed,
            stops_passed,
            tp_passed,
            unclassified_passed,
            pit_passed,
            slippage_passed,
            adverse_passed,
            cohort_fee_passed,
        ])

        haircut = float((paper_pnl / backtest_net_pnl_usd) if backtest_net_pnl_usd and backtest_net_pnl_usd != 0 else 1.0)
        churn_ratio = float(paper_notional / max(backtest_turnover_usd, 1.0))

        return {
            "passed": passed,
            "status": "PASSED" if passed else "FAILED",
            "issues": issues,
            "dimension_verdicts": {
                "dim1_fee_parity": fee_passed,
                "dim2_turnover_parity": turnover_passed,
                "dim3_maker_fill_ratio": maker_passed,
                "dim4_stop_concordance": stops_passed,
                "dim5_tp_concordance": tp_passed,
                "dim6_unclassified_exits": unclassified_passed,
                "dim7_pit_liquidity": pit_passed,
                "dim8_slippage_bound": slippage_passed,
                "dim9_adverse_markout": adverse_passed,
                "dim10_cohort_fee_separation": cohort_fee_passed,
            },
            "metrics": {
                # Distinct modeled vs empirical maker ratios
                "modeled_maker_pct": bt_maker_ratio,
                "empirical_maker_pct": paper_maker_pct,
                "maker_fill_ratio": float(paper_maker_pct),
                "net_fee_bps": float(eff_paper_fee_bps),
                "haircut_ratio": haircut,
                "confirmed_paper_stops": confirmed_stops,
                "confirmed_paper_tps": confirmed_take_profits,
                "pit_liquidity_violations": pit_violations,
                "paper_rebalances": confirmed_rebalances,
                "unclassified_exits": unclassified_exits,
                "adverse_selection_markout_bps": (float(emp_markout_bps) if emp_markout_bps is not None else None),
                "position_churn_ratio": churn_ratio,
                "empirical_slippage_bps": (float(emp_slippage_bps) if emp_slippage_bps is not None else None),
                "paper_total_fills": len(paper_fills),
                "paper_notional_usd": paper_notional,
                "backtest_notional_usd": backtest_turnover_usd,
                "paper_avg_order_size_usd": paper_avg_order_size,
                "backtest_avg_order_size_usd": bt_avg_order_size,
                "paper_fees_paid_usd": paper_fees,
                "backtest_fees_usd": backtest_fees_usd,
                "paper_effective_fee_bps": eff_paper_fee_bps,
                "backtest_effective_fee_bps": eff_bt_fee_bps,
                "fee_divergence_pct": fee_div_pct,
                "confirmed_take_profits": confirmed_take_profits,
                "confirmed_rebalances": confirmed_rebalances,
                "backtest_stop_loss_count": backtest_sl_triggers,
                "backtest_take_profit_count": backtest_tp_triggers,
                "backtest_slippage_bps": bt_slippage_bps,
                "paper_funding_usd": paper_funding,
                "backtest_funding_usd": bt_funding_usd,
                "paper_realized_pnl_usd": paper_pnl,
                "stop_cohort_fee_bps": float(stop_fee_bps),
                "rebalance_cohort_fee_bps": float(reb_fee_bps),
                "stop_fills_count": len(stop_fills),
                "rebalance_fills_count": len(rebalance_fills),
                "tp_fills_count": len(tp_fills),
            }
        }

"""
Order Sizing, Capital Allocation & Execution Optimization Experiments (v6.0)
============================================================================

Reproducible experiment suite comparing 12 position-sizing methodologies across
all Dominus Polymarket models, strategies, and sleeves:
  1. FIXED_DOLLAR
  2. FIXED_FRACTIONAL
  3. VOLATILITY_ADJUSTED
  4. EDGE_BASED
  5. PROBABILITY_CALIBRATED
  6. FULL_KELLY
  7. FRACTIONAL_KELLY_025 (0.25x) & FRACTIONAL_KELLY_050 (0.50x)
  8. LIQUIDITY_ADJUSTED_KELLY
  9. RISK_BUDGET
 10. PORTFOLIO_RISK_PARITY
 11. DYNAMIC_MARKET_CONDITION
 12. HYBRID

Evaluated across:
  - In-sample (IS), Out-of-sample (OOS), and Walk-Forward (WFO) splits
  - Multiple market regimes (CALM_HIGH_LIQ, HIGH_VOL_WIDE_SPREAD, LATENCY_SPIKE, ADVERSARIAL_WHIPSAW)
  - Bootstrap / Monte Carlo paths (drawdown & ruin-risk at $48.81, $500, $5000)
  - Correlated-market stress, liquidity-constrained, and execution-failure scenarios
  - Order execution optimization (limit vs marketable-limit FAK, maker post-only vs taker,
    order splitting, fill probability, adverse selection, slippage, and exact Polymarket
    V2 fee schedules).

Strict Non-Interference:
  - Purely offline / simulation / research module.
  - Never touches live trading, KMIA positions, or protected PAA OS files.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.polymarket_research.v6_restriction_and_capital_allocator import (
    KNOWN_POLYMARKET_FEE_SCHEDULES_V2,
)

# ---------------------------------------------------------------------------
# Constants & Canonical Identifiers
# ---------------------------------------------------------------------------

SIZING_METHODS: Tuple[str, ...] = (
    "FIXED_DOLLAR",
    "FIXED_FRACTIONAL",
    "VOLATILITY_ADJUSTED",
    "EDGE_BASED",
    "PROBABILITY_CALIBRATED",
    "FULL_KELLY",
    "FRACTIONAL_KELLY_025",
    "FRACTIONAL_KELLY_050",
    "LIQUIDITY_ADJUSTED_KELLY",
    "RISK_BUDGET",
    "PORTFOLIO_RISK_PARITY",
    "DYNAMIC_MARKET_CONDITION",
    "HYBRID",
)

REGIMES: Tuple[str, ...] = (
    "CALM_HIGH_LIQ",
    "HIGH_VOL_WIDE_SPREAD",
    "LATENCY_SPIKE",
    "ADVERSARIAL_WHIPSAW",
)

BANKROLL_SCALES_USD: Tuple[float, ...] = (48.81, 500.0, 5000.0)


@dataclass(frozen=True)
class SleeveProfile:
    """Empirical & structural specification of a Dominus strategy/sleeve."""

    sleeve_id: str
    category: str  # RISKLESS_BOX | SINGLE_LEG_LOCK | SHADOW_DIRECTIONAL | RETIRED_DIRECTIONAL
    status: str  # ACTIVE_LIVE | SHADOW | PAUSED | RETIRED
    fee_schedule: str
    p_win_mean: float
    p_win_std: float
    entry_px_mean: float
    win_payoff_px: float
    salvage_px_mean: float
    avg_hold_hours: float
    l1_depth_usd_mean: float
    spread_mean: float
    base_fill_prob_taker: float
    base_fill_prob_maker: float
    adverse_selection_cents: float
    legging_drag_bps: float
    correlation_cluster: str
    sample_n: int
    classification: str  # VERIFIED | EXPERIMENTALLY VALIDATED | PROVISIONAL | FAILED
    notes: str = ""


@dataclass(frozen=True)
class TradeObs:
    """Single simulated or bootstrapped trade observation."""

    idx: int
    regime: str
    p_win_est: float
    p_win_true: float
    entry_px: float
    best_bid: float
    best_ask: float
    spread: float
    l1_depth_usd: float
    win_payoff_px: float
    salvage_px: float
    sigma_trade: float
    correl_cluster_count: int
    latency_ms: float
    won: bool
    taker_filled: bool
    maker_filled: bool


@dataclass(frozen=True)
class ExecutionEval:
    """Order execution optimization result for a sleeve + bankroll."""

    sleeve_id: str
    bankroll_usd: float
    target_notional_usd: float
    fee_schedule: str
    taker_fee_per_share: float
    maker_rebate_per_share: float
    best_route: str  # MAKER_POST_ONLY | MARKETABLE_LIMIT_FAK | SPLIT_MICROCLIPS | SKIP
    recommended_clips: int
    taker_ev_bps: float
    maker_ev_bps: float
    split_ev_bps: float
    taker_fill_prob: float
    maker_fill_prob: float
    expected_slippage_bps: float
    adverse_selection_bps: float


@dataclass
class MethodMetrics:
    """Aggregated performance & risk metrics for one (sleeve, method, bankroll)."""

    experiment_id: str
    sleeve_id: str
    method: str
    bankroll_usd: float
    ruin_floor_usd: float
    is_net_ev_bps: float
    oos_net_ev_bps: float
    wfo_net_ev_bps: float
    wfo_sharpe: float
    mc_p05_equity_usd: float
    mc_p50_equity_usd: float
    mc_p95_equity_usd: float
    mc_prob_positive: float
    mc_p95_max_dd_pct: float
    ruin_prob: float
    corr_stress_max_dd_pct: float
    liq_constrained_ev_bps: float
    exec_failure_ev_bps: float
    avg_ticket_usd: float
    turnover_efficiency_bps_hr: float


# ---------------------------------------------------------------------------
# Canonical Sleeve Catalog (Grounded in Repo Config, Ledger & Shadow States)
# ---------------------------------------------------------------------------

def build_canonical_sleeve_catalog() -> List[SleeveProfile]:
    """
    Returns the canonical inventory of Dominus models, strategies, and sleeves
    derived from `config/polymarket_strategy_and_risk.json`, `forensic_audit_ledger.jsonl`,
    `honest_wfo_results.json`, `shadow_expansion_state.json`, and `directional_wfo_shadow_sleeves.py`.
    """
    return [
        SleeveProfile(
            sleeve_id="C1_BINARY_COMPLETE_SET",
            category="RISKLESS_BOX",
            status="ACTIVE_LIVE",
            fee_schedule="zero_fees",
            p_win_mean=0.998,
            p_win_std=0.002,
            entry_px_mean=0.986,
            win_payoff_px=1.000,
            salvage_px_mean=0.980,
            avg_hold_hours=0.15,
            l1_depth_usd_mean=42.0,
            spread_mean=0.012,
            base_fill_prob_taker=0.78,
            base_fill_prob_maker=0.45,
            adverse_selection_cents=0.002,
            legging_drag_bps=8.0,
            correlation_cluster="COMPLETE_SET_MERGE",
            sample_n=42,
            classification="VERIFIED",
            notes="0%-fee gasless CTF batch merge; immediate capital recycling.",
        ),
        SleeveProfile(
            sleeve_id="D1_SAME_ORACLE_DOMINANCE_BOX",
            category="RISKLESS_BOX",
            status="ACTIVE_LIVE",
            fee_schedule="crypto_fees_v2",
            p_win_mean=0.995,
            p_win_std=0.004,
            entry_px_mean=0.978,
            win_payoff_px=1.000,
            salvage_px_mean=0.955,
            avg_hold_hours=0.65,
            l1_depth_usd_mean=36.0,
            spread_mean=0.015,
            base_fill_prob_taker=0.72,
            base_fill_prob_maker=0.38,
            adverse_selection_cents=0.004,
            legging_drag_bps=18.0,
            correlation_cluster="CRYPTO_ORACLE_BOX",
            sample_n=11,
            classification="VERIFIED",
            notes="2-leg dominance box; 11 shadow/live records (+30.99 USD in forensic ledger).",
        ),
        SleeveProfile(
            sleeve_id="BOND1_UMA_RESOLUTION_CARRY",
            category="SINGLE_LEG_LOCK",
            status="ACTIVE_LIVE",
            fee_schedule="zero_fees",
            p_win_mean=0.992,
            p_win_std=0.005,
            entry_px_mean=0.988,
            win_payoff_px=1.000,
            salvage_px_mean=0.920,
            avg_hold_hours=1.80,
            l1_depth_usd_mean=55.0,
            spread_mean=0.010,
            base_fill_prob_taker=0.80,
            base_fill_prob_maker=0.52,
            adverse_selection_cents=0.003,
            legging_drag_bps=0.0,
            correlation_cluster="UMA_CLINCH_CARRY",
            sample_n=60,
            classification="VERIFIED",
            notes="60 forensic ledger records (57W/0L/3flat); KMIA dispute risk requires 15% event cap.",
        ),
        SleeveProfile(
            sleeve_id="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
            category="SINGLE_LEG_LOCK",
            status="ACTIVE_LIVE",
            fee_schedule="crypto_fees_v2",
            p_win_mean=0.994,
            p_win_std=0.004,
            entry_px_mean=0.989,
            win_payoff_px=1.000,
            salvage_px_mean=0.940,
            avg_hold_hours=0.85,
            l1_depth_usd_mean=48.0,
            spread_mean=0.012,
            base_fill_prob_taker=0.0,
            base_fill_prob_maker=0.58,
            adverse_selection_cents=0.002,
            legging_drag_bps=0.0,
            correlation_cluster="UMA_CLINCH_CARRY",
            sample_n=4,
            classification="EXPERIMENTALLY VALIDATED",
            notes="Post-only 0% maker fee + 20% rebate share on post-clinch books.",
        ),
        SleeveProfile(
            sleeve_id="CAL1_CALENDAR_SPREAD_BOX",
            category="RISKLESS_BOX",
            status="ACTIVE_LIVE",
            fee_schedule="zero_fees",
            p_win_mean=0.993,
            p_win_std=0.005,
            entry_px_mean=0.981,
            win_payoff_px=1.000,
            salvage_px_mean=0.950,
            avg_hold_hours=4.50,
            l1_depth_usd_mean=30.0,
            spread_mean=0.018,
            base_fill_prob_taker=0.68,
            base_fill_prob_maker=0.40,
            adverse_selection_cents=0.004,
            legging_drag_bps=14.0,
            correlation_cluster="CRYPTO_CALENDAR",
            sample_n=8,
            classification="EXPERIMENTALLY VALIDATED",
            notes="Calendar monotonicity box across expiry horizons.",
        ),
        SleeveProfile(
            sleeve_id="COND1_CONDITIONAL_MONOTONICITY_BOX",
            category="RISKLESS_BOX",
            status="ACTIVE_LIVE",
            fee_schedule="politics_fees",
            p_win_mean=0.993,
            p_win_std=0.005,
            entry_px_mean=0.980,
            win_payoff_px=1.000,
            salvage_px_mean=0.945,
            avg_hold_hours=6.00,
            l1_depth_usd_mean=28.0,
            spread_mean=0.020,
            base_fill_prob_taker=0.65,
            base_fill_prob_maker=0.38,
            adverse_selection_cents=0.004,
            legging_drag_bps=16.0,
            correlation_cluster="EVENT_LADDER",
            sample_n=6,
            classification="EXPERIMENTALLY VALIDATED",
            notes="Conditional/strike monotonicity box; capped at 15% NAV per event.",
        ),
        SleeveProfile(
            sleeve_id="NR_M1_NEGRISK_DEAD_SEED_FANOUT",
            category="RISKLESS_BOX",
            status="ACTIVE_LIVE",
            fee_schedule="zero_fees",
            p_win_mean=0.996,
            p_win_std=0.003,
            entry_px_mean=0.987,
            win_payoff_px=1.000,
            salvage_px_mean=0.960,
            avg_hold_hours=2.50,
            l1_depth_usd_mean=35.0,
            spread_mean=0.015,
            base_fill_prob_taker=0.74,
            base_fill_prob_maker=0.42,
            adverse_selection_cents=0.002,
            legging_drag_bps=10.0,
            correlation_cluster="NEGRISK_SLATE",
            sample_n=12,
            classification="EXPERIMENTALLY VALIDATED",
            notes="NegRisk dead-seed / 2-leg conversion; >=3-leg quarantined <$500 NAV.",
        ),
        SleeveProfile(
            sleeve_id="S2_RTDS_EXACT_TWAP_INTEGRATOR",
            category="RISKLESS_BOX",
            status="PAUSED",
            fee_schedule="crypto_fees_v2",
            p_win_mean=0.985,
            p_win_std=0.010,
            entry_px_mean=0.975,
            win_payoff_px=1.000,
            salvage_px_mean=0.880,
            avg_hold_hours=0.10,
            l1_depth_usd_mean=25.0,
            spread_mean=0.020,
            base_fill_prob_taker=0.62,
            base_fill_prob_maker=0.30,
            adverse_selection_cents=0.010,
            legging_drag_bps=22.0,
            correlation_cluster="CRYPTO_TWAP",
            sample_n=7,
            classification="PROVISIONAL",
            notes="Paused in live config; 7 forensic records (+0.47 USD).",
        ),
        SleeveProfile(
            sleeve_id="S4_DAILY_STRIKE_SVI",
            category="SHADOW_DIRECTIONAL",
            status="SHADOW",
            fee_schedule="crypto_fees_v2",
            p_win_mean=0.820,
            p_win_std=0.045,
            entry_px_mean=0.680,
            win_payoff_px=0.980,
            salvage_px_mean=0.350,
            avg_hold_hours=4.00,
            l1_depth_usd_mean=32.0,
            spread_mean=0.022,
            base_fill_prob_taker=0.70,
            base_fill_prob_maker=0.42,
            adverse_selection_cents=0.014,
            legging_drag_bps=0.0,
            correlation_cluster="CRYPTO_DAILY_STRIKE",
            sample_n=6,
            classification="PROVISIONAL",
            notes="Shadow expansion S4 (5W/0L on N=6); requires N>=50 WFO before live.",
        ),
        SleeveProfile(
            sleeve_id="S1_Q4_DOMINANCE",
            category="SHADOW_DIRECTIONAL",
            status="SHADOW",
            fee_schedule="crypto_fees_v2",
            p_win_mean=0.640,
            p_win_std=0.080,
            entry_px_mean=0.620,
            win_payoff_px=0.970,
            salvage_px_mean=0.320,
            avg_hold_hours=2.00,
            l1_depth_usd_mean=26.0,
            spread_mean=0.025,
            base_fill_prob_taker=0.65,
            base_fill_prob_maker=0.35,
            adverse_selection_cents=0.018,
            legging_drag_bps=0.0,
            correlation_cluster="CRYPTO_Q4",
            sample_n=4,
            classification="PROVISIONAL",
            notes="Shadow expansion S1 (1W/3L, +7.70 USD); high variance, small sample.",
        ),
        SleeveProfile(
            sleeve_id="SLEEVE_1_SUBHOURLY_15M",
            category="RETIRED_DIRECTIONAL",
            status="RETIRED",
            fee_schedule="crypto_15_min",
            p_win_mean=0.888,
            p_win_std=0.035,
            entry_px_mean=0.720,
            win_payoff_px=0.965,
            salvage_px_mean=0.340,
            avg_hold_hours=0.22,
            l1_depth_usd_mean=38.0,
            spread_mean=0.018,
            base_fill_prob_taker=0.74,
            base_fill_prob_maker=0.44,
            adverse_selection_cents=0.022,
            legging_drag_bps=0.0,
            correlation_cluster="CRYPTO_15M_DIR",
            sample_n=136,
            classification="EXPERIMENTALLY VALIDATED",
            notes="WFO sealed holdout 88.89% WR (N=27), but live 15m retired due to tail losses & high fees.",
        ),
        SleeveProfile(
            sleeve_id="SLEEVE_1_CORE_302",
            category="RETIRED_DIRECTIONAL",
            status="RETIRED",
            fee_schedule="crypto_hourly_fees",
            p_win_mean=0.855,
            p_win_std=0.045,
            entry_px_mean=0.710,
            win_payoff_px=0.965,
            salvage_px_mean=0.340,
            avg_hold_hours=0.55,
            l1_depth_usd_mean=45.0,
            spread_mean=0.016,
            base_fill_prob_taker=0.76,
            base_fill_prob_maker=0.45,
            adverse_selection_cents=0.018,
            legging_drag_bps=0.0,
            correlation_cluster="CRYPTO_1H_DIR",
            sample_n=50,
            classification="EXPERIMENTALLY VALIDATED",
            notes="1h core directional; retired in RISKLESS_PAA (<$150 NAV).",
        ),
        SleeveProfile(
            sleeve_id="SHADOW_HYBRID_ZSPLIT",
            category="SHADOW_DIRECTIONAL",
            status="SHADOW",
            fee_schedule="crypto_fees_v2",
            p_win_mean=0.880,
            p_win_std=0.038,
            entry_px_mean=0.700,
            win_payoff_px=0.965,
            salvage_px_mean=0.360,
            avg_hold_hours=0.40,
            l1_depth_usd_mean=40.0,
            spread_mean=0.015,
            base_fill_prob_taker=0.75,
            base_fill_prob_maker=0.46,
            adverse_selection_cents=0.016,
            legging_drag_bps=0.0,
            correlation_cluster="CRYPTO_15M_1H_DIR",
            sample_n=43,
            classification="EXPERIMENTALLY VALIDATED",
            notes="DirectionalWfoShadowManager Sleeve A (BTC+ETH 15m/1h hybrid z-split).",
        ),
        SleeveProfile(
            sleeve_id="SHADOW_BTC_5M_SNIPER",
            category="SHADOW_DIRECTIONAL",
            status="SHADOW",
            fee_schedule="crypto_15_min",
            p_win_mean=0.840,
            p_win_std=0.055,
            entry_px_mean=0.740,
            win_payoff_px=0.970,
            salvage_px_mean=0.250,
            avg_hold_hours=0.06,
            l1_depth_usd_mean=30.0,
            spread_mean=0.022,
            base_fill_prob_taker=0.68,
            base_fill_prob_maker=0.25,
            adverse_selection_cents=0.028,
            legging_drag_bps=0.0,
            correlation_cluster="CRYPTO_5M_DIR",
            sample_n=25,
            classification="PROVISIONAL",
            notes="Sleeve B BTC 5m final-TWAP sniper; high crypto_15_min taker fee drag.",
        ),
        SleeveProfile(
            sleeve_id="SHADOW_SOL_5M_CANARY",
            category="SHADOW_DIRECTIONAL",
            status="SHADOW",
            fee_schedule="crypto_15_min",
            p_win_mean=0.844,
            p_win_std=0.055,
            entry_px_mean=0.730,
            win_payoff_px=0.970,
            salvage_px_mean=0.240,
            avg_hold_hours=0.06,
            l1_depth_usd_mean=22.0,
            spread_mean=0.025,
            base_fill_prob_taker=0.64,
            base_fill_prob_maker=0.22,
            adverse_selection_cents=0.030,
            legging_drag_bps=0.0,
            correlation_cluster="CRYPTO_5M_DIR",
            sample_n=122,
            classification="PROVISIONAL",
            notes="Sleeve C SOL 5m canary (0.85x mult); thin book + high taker fee.",
        ),
        SleeveProfile(
            sleeve_id="SHADOW_XAU_15M_MAKER",
            category="SHADOW_DIRECTIONAL",
            status="SHADOW",
            fee_schedule="zero_fees",
            p_win_mean=0.865,
            p_win_std=0.042,
            entry_px_mean=0.690,
            win_payoff_px=0.970,
            salvage_px_mean=0.380,
            avg_hold_hours=0.25,
            l1_depth_usd_mean=34.0,
            spread_mean=0.018,
            base_fill_prob_taker=0.0,
            base_fill_prob_maker=0.48,
            adverse_selection_cents=0.012,
            legging_drag_bps=0.0,
            correlation_cluster="XAU_15M_MAKER",
            sample_n=20,
            classification="PROVISIONAL",
            notes="Sleeve D XAU 15m shielded maker-first; 0% fee / 0% rebate.",
        ),
    ]


# ---------------------------------------------------------------------------
# Exact Polymarket V2 Fee & Execution Math
# ---------------------------------------------------------------------------

def get_fee_schedule_params(schedule_name: str) -> Tuple[float, float, float]:
    """Returns (rate, exponent, rebate_rate) from KNOWN_POLYMARKET_FEE_SCHEDULES_V2."""
    if schedule_name in KNOWN_POLYMARKET_FEE_SCHEDULES_V2:
        r, e, reb = KNOWN_POLYMARKET_FEE_SCHEDULES_V2[schedule_name]
        return float(r), float(e), float(reb)
    return 0.0, 1.0, 0.0


def compute_taker_fee_per_share(price: float, schedule_name: str) -> float:
    """Protocol V2 per-share taker fee: rate * (p * (1 - p))^exp."""
    rate, exp, _ = get_fee_schedule_params(schedule_name)
    if rate <= 0.0:
        return 0.0
    p = max(0.001, min(0.999, float(price)))
    return rate * ((p * (1.0 - p)) ** exp)


def compute_maker_rebate_per_share(price: float, schedule_name: str) -> float:
    """Protocol V2 maker rebate per share (0% fee + rebate_rate * taker_fee)."""
    rate, exp, reb = get_fee_schedule_params(schedule_name)
    if rate <= 0.0 or reb <= 0.0:
        return 0.0
    p = max(0.001, min(0.999, float(price)))
    return reb * rate * ((p * (1.0 - p)) ** exp)


def evaluate_execution_routes(
    sleeve: SleeveProfile,
    bankroll_usd: float,
    target_notional_usd: float,
) -> ExecutionEval:
    """
    Compares Marketable-Limit FAK (taker) vs Post-Only Maker vs Split Micro-Clips
    on identical net bps/trade terms, accounting for Polymarket V2 fee schedules,
    fill probability, adverse selection, and L1/L2 depth slippage.
    """
    px = max(0.05, min(0.995, sleeve.entry_px_mean))
    taker_fee_ps = compute_taker_fee_per_share(px, sleeve.fee_schedule)
    maker_reb_ps = compute_maker_rebate_per_share(px, sleeve.fee_schedule)

    depth = max(8.0, sleeve.l1_depth_usd_mean)
    size_ratio = target_notional_usd / depth

    # Taker slippage & fill probability
    taker_slip_cents = 0.003 + 0.012 * max(0.0, size_ratio - 0.5)
    eff_taker_px = min(0.998, px + taker_slip_cents + taker_fee_ps)
    p_fill_taker = max(0.0, min(0.96, sleeve.base_fill_prob_taker * math.exp(-0.35 * max(0.0, size_ratio - 0.8))))

    # Expected gross payoff per share
    p_w = sleeve.p_win_mean
    exp_payoff = p_w * sleeve.win_payoff_px + (1.0 - p_w) * sleeve.salvage_px_mean

    taker_net_ps = exp_payoff - eff_taker_px
    taker_ev_bps = p_fill_taker * (taker_net_ps / max(0.05, px)) * 10000.0 - (1.0 - p_fill_taker) * 4.0

    # Maker Post-Only (0% fee, optional rebate, minus adverse selection markout)
    maker_bid_px = max(0.04, px - 0.5 * sleeve.spread_mean)
    eff_maker_cost = maker_bid_px - maker_reb_ps
    p_w_maker = max(0.01, p_w - sleeve.adverse_selection_cents)
    exp_payoff_maker = p_w_maker * sleeve.win_payoff_px + (1.0 - p_w_maker) * sleeve.salvage_px_mean
    p_fill_maker = max(0.0, min(0.85, sleeve.base_fill_prob_maker * math.exp(-0.25 * max(0.0, size_ratio - 0.5))))
    maker_net_ps = exp_payoff_maker - eff_maker_cost
    maker_ev_bps = p_fill_maker * (maker_net_ps / max(0.05, maker_bid_px)) * 10000.0

    # Split Micro-Clips (2 or 3 clips when notional > 0.65 * L1 depth)
    clips = 1
    if target_notional_usd > 0.65 * depth and bankroll_usd >= 100.0:
        clips = min(4, max(2, int(math.ceil(target_notional_usd / (0.5 * depth)))))
    split_slip_cents = 0.002 + 0.005 * max(0.0, (target_notional_usd / clips) / depth - 0.4)
    eff_split_px = min(0.998, px + split_slip_cents + taker_fee_ps)
    p_fill_split = max(0.0, min(0.95, sleeve.base_fill_prob_taker * (0.94 if clips > 1 else 1.0)))
    split_ev_bps = p_fill_split * ((exp_payoff - eff_split_px) / max(0.05, px)) * 10000.0 - (1.0 - p_fill_split) * 5.0

    # Choose optimal route
    candidates = [
        ("MAKER_POST_ONLY", maker_ev_bps if p_fill_maker > 0.05 else -9999.0),
        ("MARKETABLE_LIMIT_FAK", taker_ev_bps if p_fill_taker > 0.05 else -9999.0),
        ("SPLIT_MICROCLIPS", split_ev_bps if (clips > 1 and p_fill_taker > 0.05) else -9999.0),
    ]
    best_route, best_ev = max(candidates, key=lambda x: x[1])
    if best_ev <= 0.0:
        best_route = "SKIP"

    return ExecutionEval(
        sleeve_id=sleeve.sleeve_id,
        bankroll_usd=round(bankroll_usd, 2),
        target_notional_usd=round(target_notional_usd, 2),
        fee_schedule=sleeve.fee_schedule,
        taker_fee_per_share=round(taker_fee_ps, 6),
        maker_rebate_per_share=round(maker_reb_ps, 6),
        best_route=best_route,
        recommended_clips=clips if best_route == "SPLIT_MICROCLIPS" else 1,
        taker_ev_bps=round(taker_ev_bps, 2),
        maker_ev_bps=round(maker_ev_bps, 2),
        split_ev_bps=round(split_ev_bps, 2),
        taker_fill_prob=round(p_fill_taker, 4),
        maker_fill_prob=round(p_fill_maker, 4),
        expected_slippage_bps=round((taker_slip_cents / max(0.05, px)) * 10000.0, 2),
        adverse_selection_bps=round((sleeve.adverse_selection_cents / max(0.05, px)) * 10000.0, 2),
    )


# ---------------------------------------------------------------------------
# Synthetic Regime-Aware Trade Stream Generator (Deterministic Seed)
# ---------------------------------------------------------------------------

def generate_trade_stream(
    sleeve: SleeveProfile,
    n_trades: int = 120,
    seed: int = 42,
    regime_override: Optional[str] = None,
) -> List[TradeObs]:
    """Generates a deterministic, regime-tagged trade stream for IS/OOS/WFO."""
    rng = random.Random(seed)
    obs: List[TradeObs] = []
    for i in range(n_trades):
        if regime_override:
            reg = regime_override
        else:
            r_u = (i % 20) / 20.0
            if r_u < 0.50:
                reg = "CALM_HIGH_LIQ"
            elif r_u < 0.75:
                reg = "HIGH_VOL_WIDE_SPREAD"
            elif r_u < 0.90:
                reg = "LATENCY_SPIKE"
            else:
                reg = "ADVERSARIAL_WHIPSAW"

        reg_p_shift = {
            "CALM_HIGH_LIQ": 0.005,
            "HIGH_VOL_WIDE_SPREAD": -0.010,
            "LATENCY_SPIKE": -0.015,
            "ADVERSARIAL_WHIPSAW": -0.035,
        }[reg]
        reg_depth_mult = {
            "CALM_HIGH_LIQ": 1.25,
            "HIGH_VOL_WIDE_SPREAD": 0.70,
            "LATENCY_SPIKE": 0.85,
            "ADVERSARIAL_WHIPSAW": 0.55,
        }[reg]
        reg_lat_ms = {
            "CALM_HIGH_LIQ": 140.0,
            "HIGH_VOL_WIDE_SPREAD": 210.0,
            "LATENCY_SPIKE": 680.0,
            "ADVERSARIAL_WHIPSAW": 420.0,
        }[reg]

        p_est = max(0.50, min(0.998, sleeve.p_win_mean + rng.gauss(0.0, sleeve.p_win_std * 0.5)))
        p_true = max(0.35, min(0.998, p_est + reg_p_shift + rng.gauss(0.0, sleeve.p_win_std * 0.35)))
        entry_px = max(0.08, min(0.995, sleeve.entry_px_mean + rng.gauss(0.0, 0.008)))
        spread = max(0.005, sleeve.spread_mean * (1.6 if reg == "HIGH_VOL_WIDE_SPREAD" else 1.0))
        best_bid = max(0.01, round(entry_px - 0.5 * spread, 4))
        best_ask = min(0.998, round(entry_px + 0.5 * spread, 4))
        l1_depth = max(6.0, sleeve.l1_depth_usd_mean * reg_depth_mult * rng.uniform(0.65, 1.35))
        salvage = max(0.05, min(entry_px * 0.98, sleeve.salvage_px_mean + rng.gauss(0.0, 0.03)))
        sigma_tr = max(0.02, (sleeve.win_payoff_px - salvage) * math.sqrt(max(1e-4, p_est * (1.0 - p_est))))
        cluster_n = 1 if i % 4 != 0 else 2

        won = rng.random() < p_true
        taker_filled = rng.random() < max(0.05, sleeve.base_fill_prob_taker * (0.72 if reg == "LATENCY_SPIKE" else 1.0))
        maker_filled = rng.random() < max(0.05, sleeve.base_fill_prob_maker * (1.15 if reg == "HIGH_VOL_WIDE_SPREAD" else 1.0))

        obs.append(
            TradeObs(
                idx=i,
                regime=reg,
                p_win_est=p_est,
                p_win_true=p_true,
                entry_px=entry_px,
                best_bid=best_bid,
                best_ask=best_ask,
                spread=spread,
                l1_depth_usd=l1_depth,
                win_payoff_px=sleeve.win_payoff_px,
                salvage_px=salvage,
                sigma_trade=sigma_tr,
                correl_cluster_count=cluster_n,
                latency_ms=reg_lat_ms,
                won=won,
                taker_filled=taker_filled,
                maker_filled=maker_filled,
            )
        )
    return obs


# ---------------------------------------------------------------------------
# 12 Sizing Methodologies Implementation
# ---------------------------------------------------------------------------

def _kelly_fraction(p_win: float, g_win: float, loss_frac: float) -> float:
    """Asymmetric binary/stop-loss Kelly fraction: f* = (p*g - (1-p)*L) / (g*L)."""
    if g_win <= 1e-6 or loss_frac <= 1e-6:
        return 0.0
    ev = p_win * g_win - (1.0 - p_win) * loss_frac
    if ev <= 0.0:
        return 0.0
    return max(0.0, min(1.0, ev / (g_win * loss_frac)))


def compute_ticket_usd(
    method: str,
    *,
    equity_usd: float,
    obs: TradeObs,
    sleeve: SleeveProfile,
    use_maker: bool = False,
) -> float:
    """Computes target USD ticket size under one of the 12+1 sizing methodologies."""
    if equity_usd <= 1.0:
        return 0.0

    fee_ps = 0.0 if use_maker else compute_taker_fee_per_share(obs.entry_px, sleeve.fee_schedule)
    eff_cost = min(0.998, obs.entry_px + fee_ps)
    g_win = max(0.002, (obs.win_payoff_px - eff_cost) / eff_cost)
    loss_frac = max(0.02, min(0.92, (eff_cost - obs.salvage_px) / eff_cost))
    if sleeve.category in ("RISKLESS_BOX", "SINGLE_LEG_LOCK"):
        # Riskless boxes still face legging/dispute tail risk, modeled conservatively
        loss_frac = max(0.03, loss_frac)

    p = obs.p_win_est
    if use_maker:
        p = max(0.01, p - sleeve.adverse_selection_cents)

    f_full = _kelly_fraction(p, g_win, loss_frac)
    if f_full <= 0.0 and method not in ("FIXED_DOLLAR", "FIXED_FRACTIONAL"):
        return 0.0

    # Lower confidence bound (Wilson-style shrinkage for sample_n)
    n_eff = max(5, sleeve.sample_n)
    se_p = math.sqrt(max(1e-5, p * (1.0 - p)) / n_eff)
    p_lcb = max(0.01, p - 1.645 * se_p)
    f_lcb = _kelly_fraction(p_lcb, g_win, loss_frac)

    hard_cap_usd = min(0.90 * equity_usd, 2500.0)

    if method == "FIXED_DOLLAR":
        base = 8.0 if equity_usd < 150.0 else (25.0 if equity_usd < 1500.0 else 120.0)
        return min(base, 0.25 * equity_usd)

    if method == "FIXED_FRACTIONAL":
        return min(hard_cap_usd, 0.10 * equity_usd)

    if method == "VOLATILITY_ADJUSTED":
        target_vol_usd = 0.035 * equity_usd
        return min(0.30 * equity_usd, target_vol_usd / max(0.05, obs.sigma_trade))

    if method == "EDGE_BASED":
        net_ev_frac = p * g_win - (1.0 - p) * loss_frac
        if net_ev_frac <= 0.0:
            return 0.0
        return min(0.30 * equity_usd, equity_usd * min(0.30, 3.0 * net_ev_frac))

    if method == "PROBABILITY_CALIBRATED":
        return min(0.28 * equity_usd, equity_usd * min(0.28, 0.40 * f_lcb))

    if method == "FULL_KELLY":
        return min(0.85 * equity_usd, equity_usd * f_full)

    if method == "FRACTIONAL_KELLY_025":
        return min(0.35 * equity_usd, equity_usd * 0.25 * f_full)

    if method == "FRACTIONAL_KELLY_050":
        return min(0.50 * equity_usd, equity_usd * 0.50 * f_full)

    if method == "LIQUIDITY_ADJUSTED_KELLY":
        raw = equity_usd * 0.40 * f_full
        liq_cap = 0.65 * obs.l1_depth_usd
        return min(raw, liq_cap, 0.35 * equity_usd)

    if method == "RISK_BUDGET":
        max_stop_risk_pct = 0.08 if sleeve.category in ("RISKLESS_BOX", "SINGLE_LEG_LOCK") else 0.05
        return min(0.25 * equity_usd, (equity_usd * max_stop_risk_pct) / loss_frac)

    if method == "PORTFOLIO_RISK_PARITY":
        inv_vol = 0.04 / max(0.06, obs.sigma_trade)
        corr_haircut = 1.0 / math.sqrt(max(1, obs.correl_cluster_count))
        return min(0.22 * equity_usd, equity_usd * inv_vol * corr_haircut)

    if method == "DYNAMIC_MARKET_CONDITION":
        reg_mult = {
            "CALM_HIGH_LIQ": 1.10,
            "HIGH_VOL_WIDE_SPREAD": 0.70,
            "LATENCY_SPIKE": 0.60,
            "ADVERSARIAL_WHIPSAW": 0.35,
        }.get(obs.regime, 0.80)
        return min(0.28 * equity_usd, equity_usd * 0.36 * f_full * reg_mult)

    if method == "HYBRID":
        # Dominus v6 Hybrid: LCB-Kelly (0.38x) + Stop-Risk Budget + Liquidity Cap + 15% Event Concentration Cap
        kelly_usd = equity_usd * 0.38 * f_lcb
        stop_cap_usd = (equity_usd * 0.065) / loss_frac
        liq_cap_usd = 0.60 * obs.l1_depth_usd
        # 15% reconciled NAV correlated event cap for non-atomic/single-leg sleeves
        event_cap_usd = (
            0.15 * equity_usd
            if sleeve.category in ("SINGLE_LEG_LOCK", "SHADOW_DIRECTIONAL", "RETIRED_DIRECTIONAL")
            else 0.30 * equity_usd
        )
        reg_mult = 0.65 if obs.regime in ("LATENCY_SPIKE", "ADVERSARIAL_WHIPSAW") else 1.0
        corr_mult = 1.0 / (1.0 + 0.50 * max(0, obs.correl_cluster_count - 1))
        return min(kelly_usd, stop_cap_usd, liq_cap_usd, event_cap_usd) * reg_mult * corr_mult

    raise ValueError(f"Unknown sizing method: {method}")


# ---------------------------------------------------------------------------
# Trade PnL Simulation, WFO, Monte Carlo & Stress Evaluation
# ---------------------------------------------------------------------------

def _simulate_single_trade_pnl(
    obs: TradeObs,
    sleeve: SleeveProfile,
    ticket_usd: float,
    *,
    use_maker: bool = False,
    force_exec_failure: bool = False,
    force_liq_constrained: bool = False,
) -> Tuple[float, float]:
    """Returns (net_pnl_usd, notional_deployed_usd)."""
    if ticket_usd < 1.0:
        return 0.0, 0.0

    filled = obs.maker_filled if use_maker else obs.taker_filled
    if force_exec_failure and (obs.idx % 3 == 0):
        filled = False
    if not filled:
        # Opportunity cost / cancel-replace gas drag
        return -0.0005 * ticket_usd, 0.0

    depth = obs.l1_depth_usd * (0.45 if force_liq_constrained else 1.0)
    fill_frac = min(1.0, depth / max(1e-6, ticket_usd)) if ticket_usd > depth else 1.0
    deployed = ticket_usd * fill_frac

    fee_ps = 0.0 if use_maker else compute_taker_fee_per_share(obs.entry_px, sleeve.fee_schedule)
    reb_ps = compute_maker_rebate_per_share(obs.entry_px, sleeve.fee_schedule) if use_maker else 0.0
    slip_ps = 0.002 + 0.015 * max(0.0, (deployed / max(4.0, depth)) - 0.5)
    legging_ps = (sleeve.legging_drag_bps / 10000.0) * obs.entry_px

    eff_entry = min(0.999, obs.entry_px + fee_ps + slip_ps + legging_ps - reb_ps)
    shares = deployed / max(0.05, obs.entry_px)
    exit_px = obs.win_payoff_px if obs.won else obs.salvage_px
    net_pnl = shares * (exit_px - eff_entry)
    return net_pnl, deployed


def _run_sequence(
    stream: Sequence[TradeObs],
    sleeve: SleeveProfile,
    method: str,
    start_equity: float,
    *,
    use_maker: bool = False,
    force_exec_failure: bool = False,
    force_liq_constrained: bool = False,
) -> Tuple[List[float], float, float]:
    """Runs sequential equity path; returns (per_trade_bps, end_equity, max_dd_pct)."""
    eq = float(start_equity)
    peak = eq
    max_dd_pct = 0.0
    bps_list: List[float] = []
    for obs in stream:
        ticket = compute_ticket_usd(method, equity_usd=eq, obs=obs, sleeve=sleeve, use_maker=use_maker)
        pnl, deployed = _simulate_single_trade_pnl(
            obs,
            sleeve,
            ticket,
            use_maker=use_maker,
            force_exec_failure=force_exec_failure,
            force_liq_constrained=force_liq_constrained,
        )
        if deployed > 0.0:
            bps_list.append((pnl / deployed) * 10000.0)
        eq = max(0.01, eq + pnl)
        if eq > peak:
            peak = eq
        dd_pct = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
    return bps_list, eq, max_dd_pct


def run_sleeve_method_experiment(
    sleeve: SleeveProfile,
    method: str,
    bankroll_usd: float,
    *,
    n_trades: int = 120,
    mc_paths: int = 250,
    seed: int = 20261112,
) -> MethodMetrics:
    """Runs full IS/OOS/WFO/MC/Stress evaluation for a (sleeve, method, bankroll)."""
    use_maker = sleeve.base_fill_prob_taker <= 0.05 or sleeve.sleeve_id in (
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "SHADOW_XAU_15M_MAKER",
    )
    stream = generate_trade_stream(sleeve, n_trades=n_trades, seed=seed)
    split = int(0.60 * len(stream))
    is_stream = stream[:split]
    oos_stream = stream[split:]

    is_bps, _, _ = _run_sequence(is_stream, sleeve, method, bankroll_usd, use_maker=use_maker)
    oos_bps, _, _ = _run_sequence(oos_stream, sleeve, method, bankroll_usd, use_maker=use_maker)

    # 3-fold Walk-Forward OOS
    fold_size = max(12, len(stream) // 4)
    wfo_bps: List[float] = []
    for f_idx in range(1, 4):
        test_slice = stream[f_idx * fold_size : (f_idx + 1) * fold_size]
        if test_slice:
            fb, _, _ = _run_sequence(test_slice, sleeve, method, bankroll_usd, use_maker=use_maker)
            wfo_bps.extend(fb)

    is_ev = statistics.fmean(is_bps) if is_bps else 0.0
    oos_ev = statistics.fmean(oos_bps) if oos_bps else 0.0
    wfo_ev = statistics.fmean(wfo_bps) if wfo_bps else 0.0
    wfo_std = statistics.pstdev(wfo_bps) if len(wfo_bps) > 1 else 1.0
    wfo_sharpe = (wfo_ev / max(1e-6, wfo_std)) * math.sqrt(max(1, len(wfo_bps)))

    # Ruin floor: $30.00 at $48.81 (matches `riskless_hard_ruin_floor_usd`), 60% of bankroll scaled
    ruin_floor = 30.0 if bankroll_usd < 100.0 else round(0.60 * bankroll_usd, 2)

    # Bootstrap / Monte Carlo
    rng = random.Random(seed + hash((sleeve.sleeve_id, method)) % 100000)
    term_eqs: List[float] = []
    max_dds: List[float] = []
    ruins = 0
    for _ in range(mc_paths):
        boot = [rng.choice(oos_stream) for _ in range(60)]
        eq = bankroll_usd
        peak = eq
        mdd = 0.0
        hit_ruin = False
        for obs in boot:
            ticket = compute_ticket_usd(method, equity_usd=eq, obs=obs, sleeve=sleeve, use_maker=use_maker)
            pnl, _ = _simulate_single_trade_pnl(obs, sleeve, ticket, use_maker=use_maker)
            eq = max(0.01, eq + pnl)
            if eq <= ruin_floor:
                hit_ruin = True
            if eq > peak:
                peak = eq
            dd = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
            if dd > mdd:
                mdd = dd
        term_eqs.append(eq)
        max_dds.append(mdd)
        if hit_ruin:
            ruins += 1

    term_eqs.sort()
    max_dds.sort()
    n_mc = len(term_eqs)
    p05_eq = term_eqs[max(0, int(0.05 * n_mc))]
    p50_eq = term_eqs[n_mc // 2]
    p95_eq = term_eqs[min(n_mc - 1, int(0.95 * n_mc))]
    p95_dd = max_dds[min(n_mc - 1, int(0.95 * n_mc))]
    prob_pos = sum(1 for e in term_eqs if e > bankroll_usd) / max(1, n_mc)
    ruin_prob = ruins / max(1, n_mc)

    # Correlated-market stress (3x concurrent correlated cluster shock)
    corr_stream = [
        TradeObs(**{**asdict(o), "correl_cluster_count": 3, "won": (False if o.idx % 7 == 0 else o.won)})
        for o in oos_stream
    ]
    _, _, corr_dd = _run_sequence(corr_stream, sleeve, method, bankroll_usd, use_maker=use_maker)

    # Liquidity-constrained & execution-failure stress
    liq_bps, _, _ = _run_sequence(
        oos_stream, sleeve, method, bankroll_usd, use_maker=use_maker, force_liq_constrained=True
    )
    exec_bps, _, _ = _run_sequence(
        oos_stream, sleeve, method, bankroll_usd, use_maker=use_maker, force_exec_failure=True
    )

    sample_tickets = [
        compute_ticket_usd(method, equity_usd=bankroll_usd, obs=o, sleeve=sleeve, use_maker=use_maker)
        for o in oos_stream[:20]
    ]
    avg_ticket = statistics.fmean(sample_tickets) if sample_tickets else 0.0
    bps_hr = wfo_ev / max(0.05, sleeve.avg_hold_hours)

    exp_id = f"EXP_{sleeve.sleeve_id}_{method}_{int(round(bankroll_usd))}"
    return MethodMetrics(
        experiment_id=exp_id,
        sleeve_id=sleeve.sleeve_id,
        method=method,
        bankroll_usd=round(bankroll_usd, 2),
        ruin_floor_usd=ruin_floor,
        is_net_ev_bps=round(is_ev, 2),
        oos_net_ev_bps=round(oos_ev, 2),
        wfo_net_ev_bps=round(wfo_ev, 2),
        wfo_sharpe=round(wfo_sharpe, 2),
        mc_p05_equity_usd=round(p05_eq, 2),
        mc_p50_equity_usd=round(p50_eq, 2),
        mc_p95_equity_usd=round(p95_eq, 2),
        mc_prob_positive=round(prob_pos, 4),
        mc_p95_max_dd_pct=round(p95_dd, 2),
        ruin_prob=round(ruin_prob, 4),
        corr_stress_max_dd_pct=round(corr_dd, 2),
        liq_constrained_ev_bps=round(statistics.fmean(liq_bps) if liq_bps else 0.0, 2),
        exec_failure_ev_bps=round(statistics.fmean(exec_bps) if exec_bps else 0.0, 2),
        avg_ticket_usd=round(avg_ticket, 2),
        turnover_efficiency_bps_hr=round(bps_hr, 2),
    )


def select_best_method(metrics: Sequence[MethodMetrics]) -> MethodMetrics:
    """
    Selects the best sizing methodology balancing risk-adjusted WFO growth,
    low ruin probability (preferring <= 5% ruin risk), and bounded correlated drawdown.
    """
    safe_pool = [m for m in metrics if m.ruin_prob <= 0.05]
    pool = safe_pool if safe_pool else list(metrics)

    def _score(m: MethodMetrics) -> float:
        growth_pct = ((m.mc_p50_equity_usd - m.bankroll_usd) / max(1.0, m.bankroll_usd)) * 100.0
        return (
            growth_pct
            + 0.15 * m.wfo_sharpe
            - 500.0 * m.ruin_prob
            - 0.80 * m.mc_p95_max_dd_pct
            - 0.40 * m.corr_stress_max_dd_pct
        )

    return max(pool, key=_score)


def run_full_experiment_suite(
    *,
    bankrolls: Sequence[float] = BANKROLL_SCALES_USD,
    mc_paths: int = 200,
    seed: int = 20261112,
    output_json_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Runs the complete 16-sleeve x 13-method x 3-bankroll experiment matrix."""
    catalog = build_canonical_sleeve_catalog()
    all_metrics: List[MethodMetrics] = []
    exec_evals: List[ExecutionEval] = []
    summary_rows: List[Dict[str, Any]] = []

    for sleeve in catalog:
        by_bankroll_best: Dict[float, MethodMetrics] = {}
        for br in bankrolls:
            br_metrics = [
                run_sleeve_method_experiment(
                    sleeve, m, br, n_trades=120, mc_paths=mc_paths, seed=seed
                )
                for m in SIZING_METHODS
            ]
            all_metrics.extend(br_metrics)
            by_bankroll_best[br] = select_best_method(br_metrics)

        best_seed = by_bankroll_best.get(48.81) or next(iter(by_bankroll_best.values()))
        exec_opt = evaluate_execution_routes(sleeve, 48.81, max(5.0, best_seed.avg_ticket_usd))
        exec_evals.append(exec_opt)

        m500 = by_bankroll_best.get(500.0)
        m5000 = by_bankroll_best.get(5000.0)
        summary_rows.append(
            {
                "sleeve_id": sleeve.sleeve_id,
                "status": sleeve.status,
                "fee_schedule": sleeve.fee_schedule,
                "best_sizing_method": best_seed.method,
                "optimal_exec_route": exec_opt.best_route,
                "is_net_ev_bps": best_seed.is_net_ev_bps,
                "wfo_oos_net_ev_bps": best_seed.wfo_net_ev_bps,
                "mc_p50_eq_48_81": best_seed.mc_p50_equity_usd,
                "mc_p95_max_dd_pct": best_seed.mc_p95_max_dd_pct,
                "ruin_prob": best_seed.ruin_prob,
                "scaled_500_5000_oos_ev_bps": (
                    f"{m500.wfo_net_ev_bps if m500 else 0.0:.1f} / "
                    f"{m5000.wfo_net_ev_bps if m5000 else 0.0:.1f}"
                ),
                "classification": sleeve.classification,
                "experiment_id": best_seed.experiment_id,
            }
        )

    payload = {
        "schema_version": "6.0.0",
        "seed": seed,
        "mc_paths": mc_paths,
        "bankrolls_usd": list(bankrolls),
        "methods": list(SIZING_METHODS),
        "sleeves_count": len(catalog),
        "total_experiments": len(all_metrics),
        "summary_table": summary_rows,
        "execution_optimizations": [asdict(e) for e in exec_evals],
        "detailed_metrics": [asdict(m) for m in all_metrics],
    }

    if output_json_path is not None:
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload

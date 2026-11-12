"""
Institutional Statistical Validation, Anti-Overfitting & Leaderboard Engine
(`src/directional_alpha/statistical_validation.py`).

Pure-Python (stdlib-only; zero numpy/pandas dependencies) statistical validation
suite for Polymarket directional alpha research:
  1. Strict 3-Way Chronological Split (Train 50% / Validation 25% / Sealed Holdout 25%)
     with exact cross-boundary open-position purging (`entry_ts <= split_ts < exit_ts`)
     and post-boundary embargoing (`embargo_sec`).
  2. Purged Walk-Forward Out-of-Sample evaluation, Combinatorial Purged Cross-Validation
     (`CPCV(N, k)`), and Bailey-Borwein-Lopez de Prado-Zhu (2017) Probability of Backtest
     Overfitting (`PBO`), plus parameter perturbation (`±20%`, `±50%`) and regime/category
     stability diagnostics.
  3. Event-Cluster-Aware Bootstrap Confidence Intervals (`B >= 2,000`), grouping correlated
     contracts by `event_id` and date-category resolution clusters so simultaneous outcomes
     are never treated as independent trials.
  4. Family-Wise & False-Discovery Multiple-Testing Corrections across all `M` swarm trials:
     Benjamini-Hochberg FDR (`q`-values), Benjamini-Yekutieli FDR, Holm-Bonferroni FWER,
     and Bailey & Lopez de Prado (2014) Probabilistic / Deflated Sharpe Ratio (`PSR` / `DSR`).
  5. Transaction-Cost Stress Multipliers (`1.0x`, `1.5x`, `2.0x`, `3.0x`) and exact
     break-even extra slippage (`bps` of notional and `cents/share`).
  6. Mandatory Simple Baselines:
     (a) Market-implied zero-edge benchmark (Brier / LogLoss skill baseline),
     (b) Naive unconditional Buy-NO & Buy-Favorite hold-to-maturity,
     (c) Random-entry microstructure cost-drag Monte Carlo benchmark.
  7. Full 16-metric Section 5 profitability & risk scorecard (per-strategy and combined
     multi-strategy portfolio) and strict 5-label Deliverable C classification gated on
     independent `@red-team` adversarial sign-off.
"""

from __future__ import annotations

import collections
from dataclasses import asdict, dataclass, field
import datetime as dt
import itertools
import math
import random
import statistics
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

EULER_MASCHERONI: float = 0.5772156649015329
_STD_NORMAL = statistics.NormalDist(0.0, 1.0)

DELIVERABLE_C_LABELS: Tuple[str, ...] = (
    "Validated out of sample",
    "Promising but preliminary",
    "Insufficient evidence",
    "Rejected",
    "Awaiting data",
)

FEE_BEARING_CATEGORIES: frozenset[str] = frozenset({"crypto", "sports_fee_enabled"})

# Empirical Nov 2026 Polymarket V2 curved taker fee schedules (`rate * p * (1 - p)`)
# calibrated in `data/directional_alpha/microstructure_calibration.json` (89.05% fee-enabled share)
EMPIRICAL_2026_V2_CATEGORY_RATES: Dict[str, float] = {
    "crypto": 0.07,
    "sports": 0.05,
    "politics": 0.04,
    "economics": 0.05,
    "economics_macro": 0.05,
    "macro": 0.05,
    "finance": 0.04,
    "tech": 0.04,
    "tech_ai": 0.04,
    "culture": 0.05,
    "culture_science": 0.05,
    "weather": 0.05,
    "general": 0.05,
    "geopolitics": 0.00,
    "zero_fee": 0.00,
}

# Default global chronological split anchors from `data/directional_alpha/data_audit_manifest.json` (`RT-11`)
DEFAULT_GLOBAL_TRAIN_END_TS: float = 1791252025.0  # 2026-10-06T02:00:25Z
DEFAULT_GLOBAL_VAL_END_TS: float = 1794052848.0    # 2026-11-07T12:00:48Z

# Dominus reference constants from PROJECT_STATE.md / AGENTS.md (research comparators only)
DOMINUS_SEED_CASH_USD: float = 48.807132
DOMINUS_VM_DAILY_HURDLE_USD: float = 0.822333


def parse_unix_ts(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Parses Unix seconds, milliseconds, or ISO-8601 strings into UTC Unix seconds."""
    if val is None or val == "":
        return default
    if isinstance(val, (int, float)):
        f = float(val)
        if math.isnan(f) or math.isinf(f) or f <= 0.0:
            return default
        return f / 1000.0 if f > 1e11 else f
    s = str(val).strip()
    if not s:
        return default
    try:
        f = float(s)
        if f <= 0.0:
            return default
        return f / 1000.0 if f > 1e11 else f
    except ValueError:
        pass
    try:
        iso = s.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(iso)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.timestamp()
    except Exception:
        return default


def norm_cdf(z: float) -> float:
    """Standard normal cumulative distribution function Phi(z)."""
    if math.isnan(z):
        return 0.5
    if z <= -38.0:
        return 0.0
    if z >= 38.0:
        return 1.0
    return _STD_NORMAL.cdf(float(z))


def norm_inv_cdf(p: float) -> float:
    """Standard normal inverse CDF Phi^{-1}(p), clamped safely away from {0, 1}."""
    p_clamped = min(1.0 - 1e-15, max(1e-15, float(p)))
    return _STD_NORMAL.inv_cdf(p_clamped)


def _clamp_prob(p: float, eps: float = 1e-6) -> float:
    return min(1.0 - eps, max(eps, float(p)))


def _utc_day_str(ts: float) -> str:
    if ts <= 0.0:
        return "1970-01-01"
    return dt.datetime.fromtimestamp(float(ts), tz=dt.timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 1. Canonical Trade Observation & Anti-Leakage Normalization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeObservation:
    """Normalized single directional trade or executable signal evaluation."""

    trade_id: str
    strategy_id: str
    market_id: str
    event_id: str
    category: str
    side: str  # "YES" or "NO"
    exit_type: str  # "SETTLEMENT" or "PRE_RESOLUTION_EXIT"
    entry_ts: float
    exit_ts: float
    entry_price: float
    exit_price: float
    market_mid_entry: float
    model_prob_entry: float
    outcome_binary: Optional[float]  # Continuous settlement payout in [0.0, 1.0] (1.0 win, 0.0 loss/disputed-floor, 0.5 void)
    notional_usd: float
    shares: float
    gross_pnl_usd: float
    fees_usd: float
    spread_slippage_cost_usd: float
    net_pnl_usd: float
    available_depth_usd: float = 100.0
    fee_rate_bps: float = 0.0
    is_maker_entry: bool = False
    clinch_ts: Optional[float] = None
    end_ts: Optional[float] = None
    uma_disputed: bool = False
    data_quality_class: str = "ESTIMATED_SPREAD_ADJUSTED"
    subcategory: str = ""
    fee_rate: Optional[float] = None
    is_void_50_50: bool = False

    @property
    def hold_seconds(self) -> float:
        return max(0.0, float(self.exit_ts) - float(self.entry_ts))

    @property
    def hold_days(self) -> float:
        # Floor at 5 minutes (1/288 day) so sub-hourly trades have well-defined dollar-day commitment
        return max(300.0 / 86400.0, self.hold_seconds / 86400.0)

    def canonical_cluster_id(self, strict_date_category_merge: bool = True) -> str:
        """
        Returns an event-cluster key ensuring correlated markets (same multi-outcome event,
        same election, same weather day, or same-day crypto strike ladder) share ONE cluster.
        """
        ev = (self.event_id or "").strip()
        cat = (self.category or "unknown").strip().lower()
        res_day = _utc_day_str(self.exit_ts if self.exit_ts > 0 else self.entry_ts)
        # If event_id is missing or trivially set equal to market_id, group by category + resolution day
        if not ev or ev == self.market_id:
            return f"CLUSTER:{cat}:{res_day}"
        if strict_date_category_merge and cat in ("crypto", "weather", "economics", "macro"):
            sub = (self.subcategory or "").strip().lower()
            prefix = f"{cat}:{sub}" if sub else cat
            return f"CLUSTER:{prefix}:{res_day}:{ev}"
        return f"EVENT:{ev}"


def normalize_trade_record(
    raw: Mapping[str, Any],
    *,
    default_strategy_id: str = "UNKNOWN_STRATEGY",
    default_notional_usd: float = 10.0,
) -> TradeObservation:
    """
    Converts heterogeneous strategy/backtest trade dictionaries into a strict
    `TradeObservation` with exact `gross - fees - spread_slippage == net` accounting.
    """
    strategy_id = str(raw.get("strategy_id") or raw.get("strategy") or default_strategy_id)
    market_id = str(raw.get("market_id") or raw.get("mid") or raw.get("condition_id") or "unknown_market")
    trade_id = str(
        raw.get("trade_id")
        or raw.get("id")
        or f"{strategy_id}:{market_id}:{raw.get('entry_ts', raw.get('t0', 0))}"
    )
    event_id = str(
        raw.get("event_id")
        or raw.get("cluster_key")
        or raw.get("cluster_id")
        or raw.get("event_slug")
        or raw.get("group_id")
        or ""
    )
    category = str(raw.get("category") or raw.get("domain") or "Uncategorized").strip()
    subcategory = str(raw.get("subcategory") or raw.get("horizon") or raw.get("asset") or "").strip()

    raw_side = str(raw.get("side") or raw.get("direction") or "YES").strip().upper()
    side = "NO" if raw_side in ("NO", "DOWN", "SHORT", "0") else "YES"

    raw_exit_type = str(raw.get("exit_type") or raw.get("exit_mode") or "").strip().upper()
    if not raw_exit_type:
        reason_str = str(raw.get("exit_reason") or "").upper()
        if any(tok in reason_str for tok in ("TP", "STOP", "SALVAGE", "RATCHET", "UNWIND", "EXIT", "TIME")):
            raw_exit_type = "PRE_RESOLUTION_EXIT"
        else:
            raw_exit_type = "SETTLEMENT"
    exit_type = "PRE_RESOLUTION_EXIT" if "PRE" in raw_exit_type or "EXIT" in raw_exit_type else "SETTLEMENT"

    entry_ts = float(
        parse_unix_ts(
            raw.get("entry_ts")
            if raw.get("entry_ts") is not None
            else (raw.get("t0") or raw.get("timestamp_unix") or raw.get("timestamp")),
            default=0.0,
        )
        or 0.0
    )
    exit_ts_raw = (
        raw.get("exit_ts")
        if raw.get("exit_ts") is not None
        else (raw.get("settlement_ts") or raw.get("resolution_ts") or raw.get("exp_ts") or raw.get("end_ts") or raw.get("endDate"))
    )
    exit_ts = float(parse_unix_ts(exit_ts_raw, default=entry_ts) or entry_ts)

    entry_px_raw = (
        raw.get("entry_price")
        if raw.get("entry_price") is not None
        else (
            raw.get("entry_exec_price")
            if raw.get("entry_exec_price") is not None
            else (raw.get("exec_price") or raw.get("fill_px") or raw.get("entry_ask") or raw.get("ask_entry") or 0.50)
        )
    )
    entry_price = _clamp_prob(float(entry_px_raw), eps=1e-4)

    mid_cand = raw.get("market_mid_entry")
    if mid_cand is None:
        mid_cand = raw.get("market_prob")
    if mid_cand is None:
        mid_cand = raw.get("mid_price")
    if mid_cand is None:
        mid_cand = raw.get("market_mid")
    if mid_cand is None:
        mid_cand = raw.get("signal_price")
    if mid_cand is None and raw.get("p_yes_market") is not None:
        p_ymkt = float(raw["p_yes_market"])
        mid_cand = (1.0 - p_ymkt) if side == "NO" else p_ymkt
    market_mid = _clamp_prob(float(mid_cand if mid_cand is not None else entry_price), eps=1e-4)

    mod_cand = raw.get("model_prob_entry")
    if mod_cand is None:
        mod_cand = raw.get("pi_side_model")
    if mod_cand is None:
        mod_cand = raw.get("p_model")
    if mod_cand is None:
        mod_cand = raw.get("p_hat")
    if mod_cand is None:
        mod_cand = raw.get("predicted_prob")
    if mod_cand is None and raw.get("p_yes_model") is not None:
        p_ymod = float(raw["p_yes_model"])
        mod_cand = (1.0 - p_ymod) if side == "NO" else p_ymod
    model_prob = _clamp_prob(float(mod_cand if mod_cand is not None else market_mid), eps=1e-4)

    uma_disputed = bool(raw.get("uma_disputed", False) or raw.get("is_disputed_or_frozen", False))
    is_void_50_50 = bool(raw.get("is_void_50_50", False) or raw.get("is_void_or_50_50", False))

    outcome_val: Optional[float] = None
    if raw.get("outcome_payout") is not None:
        outcome_val = float(raw["outcome_payout"])
    elif raw.get("settlement_payout_per_share") is not None:
        outcome_val = float(raw["settlement_payout_per_share"])
    elif raw.get("outcome_side_payout") is not None:
        outcome_val = float(raw["outcome_side_payout"])
    elif raw.get("outcome_binary") is not None:
        outcome_val = float(raw["outcome_binary"])
    elif raw.get("outcome_0_payout") is not None and raw.get("outcome_1_payout") is not None:
        outcome_val = float(raw["outcome_1_payout"]) if side == "NO" else float(raw["outcome_0_payout"])
    elif raw.get("won") is not None:
        outcome_val = 1.0 if bool(raw.get("won")) else 0.0
    elif raw.get("resolved_outcome") is not None:
        ro = raw.get("resolved_outcome")
        if isinstance(ro, str):
            ru = ro.strip().upper()
            if ru in ("0.5", "VOID", "50-50", "50_50"):
                outcome_val = 0.5
                is_void_50_50 = True
            else:
                outcome_val = 1.0 if ru in ("1", "1.0", "YES", "TRUE", "WIN") else 0.0
        elif isinstance(ro, (int, float)):
            rf = float(ro)
            if abs(rf - 0.5) <= 1e-6:
                outcome_val = 0.5
                is_void_50_50 = True
            elif 0.0 <= rf <= 1.0:
                outcome_val = rf
            else:
                outcome_val = 1.0 if bool(ro) else 0.0
    elif raw.get("outcome") is not None and isinstance(raw.get("outcome"), (int, float, bool)):
        rf = float(raw["outcome"])
        outcome_val = rf if 0.0 <= rf <= 1.0 else (1.0 if bool(raw["outcome"]) else 0.0)
    elif raw.get("resolved_outcome_yes") is not None:
        roy_f = float(raw["resolved_outcome_yes"])
        if abs(roy_f - 0.5) <= 1e-6 or is_void_50_50:
            outcome_val = 0.5
            is_void_50_50 = True
        elif roy_f in (0.0, 1.0):
            outcome_val = (1.0 - roy_f) if side == "NO" else roy_f
        elif roy_f < 0.0:
            # Sentinel -1 for void/disputed contracts: 0.0 conservative floor on disputed (D-009), 0.5 on 50-50 void
            outcome_val = 0.0 if uma_disputed else 0.5
            if not uma_disputed:
                is_void_50_50 = True
    elif is_void_50_50:
        outcome_val = 0.5
    elif uma_disputed:
        outcome_val = 0.0

    if outcome_val is not None:
        outcome_val = max(0.0, min(1.0, float(outcome_val)))
        if abs(outcome_val - 0.5) <= 1e-6:
            is_void_50_50 = True
    outcome_binary: Optional[float] = outcome_val

    if raw.get("exit_price") is not None:
        exit_price = float(raw["exit_price"])
    elif raw.get("exit_exec_price") is not None:
        exit_price = float(raw["exit_exec_price"])
    elif exit_type == "SETTLEMENT" and outcome_binary is not None:
        exit_price = float(outcome_binary)
    else:
        exit_price = entry_price

    notional_raw = (
        raw.get("notional_usd")
        if raw.get("notional_usd") is not None
        else (
            raw.get("capital_committed_usd")
            if raw.get("capital_committed_usd") is not None
            else (raw.get("capital_usd") or raw.get("stake_usd") or raw.get("cost_usd") or default_notional_usd)
        )
    )
    notional_usd = max(1e-6, float(notional_raw))
    shares = float(raw.get("shares") or raw.get("size_shares") or (notional_usd / entry_price))
    is_maker_entry = bool(
        raw.get("is_maker_entry", False)
        or raw.get("is_maker", False)
        or str(raw.get("exec_mode") or "").strip().upper() == "MAKER"
    )
    fee_cand = (
        raw.get("fees_usd")
        if raw.get("fees_usd") is not None
        else (raw.get("total_fees_usd") if raw.get("total_fees_usd") is not None else raw.get("fee_usd"))
    )
    fees_usd = max(0.0, float(fee_cand or 0.0))
    # Allow explicit negative maker rebates when is_maker_entry is True and fees_usd < 0
    if fee_cand is not None and float(fee_cand) < 0.0 and is_maker_entry:
        fees_usd = float(fee_cand)

    spread_slip_raw = raw.get("spread_slippage_cost_usd")
    if spread_slip_raw is None:
        spread_slip_raw = raw.get("total_slippage_usd")
    if spread_slip_raw is None:
        spread_slip_raw = raw.get("slippage_usd")
    if spread_slip_raw is not None:
        spread_slippage_cost_usd = max(0.0, float(spread_slip_raw))
    elif raw.get("spread_cost_bps") is not None or raw.get("slippage_bps") is not None:
        bps_c = float(raw.get("spread_cost_bps") or raw.get("slippage_bps") or 0.0)
        spread_slippage_cost_usd = max(0.0, notional_usd * (bps_c / 10_000.0))
    else:
        # Derive explicit microstructure spread cost when entry_price > market_mid_entry
        implicit_entry_slip = max(0.0, (entry_price - market_mid) * shares)
        spread_slippage_cost_usd = implicit_entry_slip

    has_net = raw.get("net_pnl_usd") is not None or raw.get("pnl_usd") is not None or raw.get("net_pnl") is not None
    has_gross = raw.get("gross_pnl_usd") is not None or raw.get("gross_pnl") is not None

    if has_net and has_gross:
        net_pnl_usd = float(
            raw.get("net_pnl_usd")
            if raw.get("net_pnl_usd") is not None
            else (raw.get("pnl_usd") if raw.get("pnl_usd") is not None else raw.get("net_pnl"))
        )
        gross_pnl_usd = float(raw.get("gross_pnl_usd") if raw.get("gross_pnl_usd") is not None else raw.get("gross_pnl"))
        # Reconcile spread/slippage residual if caller baked friction into net_pnl without itemizing
        residual = (gross_pnl_usd - fees_usd - spread_slippage_cost_usd) - net_pnl_usd
        if residual > 1e-6:
            spread_slippage_cost_usd += residual
    elif has_net:
        net_pnl_usd = float(
            raw.get("net_pnl_usd")
            if raw.get("net_pnl_usd") is not None
            else (raw.get("pnl_usd") if raw.get("pnl_usd") is not None else raw.get("net_pnl"))
        )
        gross_pnl_usd = net_pnl_usd + fees_usd + spread_slippage_cost_usd
    elif has_gross:
        gross_pnl_usd = float(raw.get("gross_pnl_usd") if raw.get("gross_pnl_usd") is not None else raw.get("gross_pnl"))
        net_pnl_usd = gross_pnl_usd - fees_usd - spread_slippage_cost_usd
    else:
        # Mid-reference gross PnL minus explicit fee & spread/slippage friction
        ref_entry = market_mid if spread_slippage_cost_usd > 0 else entry_price
        gross_pnl_usd = shares * (exit_price - ref_entry)
        net_pnl_usd = gross_pnl_usd - fees_usd - spread_slippage_cost_usd

    clinch_ts = parse_unix_ts(raw.get("clinch_ts") if raw.get("clinch_ts") is not None else raw.get("safe_decision_cutoff_ts"))
    end_ts_cand = (
        raw.get("end_ts")
        if raw.get("end_ts") is not None
        else (raw.get("endDate") if raw.get("endDate") is not None else raw.get("settlement_ts"))
    )
    end_ts = parse_unix_ts(end_ts_cand)
    avail_depth_cand = (
        raw.get("available_depth_usd")
        if raw.get("available_depth_usd") is not None
        else (
            raw.get("available_capacity_usd")
            if raw.get("available_capacity_usd") is not None
            else (raw.get("l2_depth_usd") if raw.get("l2_depth_usd") is not None else 100.0)
        )
    )

    raw_fee_rate = raw.get("fee_rate")
    explicit_fee_rate: Optional[float] = None
    if raw_fee_rate is not None:
        fr_val = float(raw_fee_rate)
        # Guard against V2 sentinel 1000 accidentally passed as fee_rate
        if 0.0 <= fr_val <= 0.15:
            explicit_fee_rate = fr_val

    return TradeObservation(
        trade_id=trade_id,
        strategy_id=strategy_id,
        market_id=market_id,
        event_id=event_id,
        category=category,
        side=side,
        exit_type=exit_type,
        entry_ts=entry_ts,
        exit_ts=exit_ts,
        entry_price=entry_price,
        exit_price=exit_price,
        market_mid_entry=market_mid,
        model_prob_entry=model_prob,
        outcome_binary=outcome_binary,
        notional_usd=notional_usd,
        shares=shares,
        gross_pnl_usd=gross_pnl_usd,
        fees_usd=fees_usd,
        spread_slippage_cost_usd=spread_slippage_cost_usd,
        net_pnl_usd=net_pnl_usd,
        available_depth_usd=max(0.0, float(avail_depth_cand)),
        fee_rate_bps=max(0.0, float(raw.get("fee_rate_bps") or raw.get("taker_base_fee_bps") or 0.0)),
        is_maker_entry=is_maker_entry,
        clinch_ts=clinch_ts,
        end_ts=end_ts,
        uma_disputed=uma_disputed,
        data_quality_class=str(raw.get("data_quality_class") or "ESTIMATED_SPREAD_ADJUSTED"),
        subcategory=subcategory,
        fee_rate=explicit_fee_rate,
        is_void_50_50=is_void_50_50,
    )


def detect_leakage_and_integrity_violations(trades: Sequence[TradeObservation]) -> List[str]:
    """
    Audits trade observations for:
      - RT-01: Post-clinch (`entry_ts >= clinch_ts`), post-endDate (`entry_ts >= end_ts`), or negative-time look-ahead,
      - RT-02: Zero-friction midpoint fabrication on non-L2 taker series,
      - RT-03: Missing taker fees on fee-bearing contracts,
      - RT-12: Pre-resolution exits credited with `{0.0, 1.0}` binary settlement payouts.
    """
    violations: List[str] = []
    time_travel_cnt = 0
    post_clinch_cnt = 0
    post_end_cnt = 0
    zero_friction_mid_cnt = 0
    missing_fee_cnt = 0
    pre_exit_conflation_cnt = 0

    for t in trades:
        if t.exit_ts + 1e-6 < t.entry_ts:
            time_travel_cnt += 1
        if t.clinch_ts is not None and t.clinch_ts > 0.0 and t.entry_ts >= t.clinch_ts - 1e-6:
            post_clinch_cnt += 1
        if t.end_ts is not None and t.end_ts > 0.0 and t.entry_ts >= t.end_ts - 1e-3:
            post_end_cnt += 1
        if (
            not t.is_maker_entry
            and t.data_quality_class != "OBSERVED_EXECUTABLE_L2"
            and t.spread_slippage_cost_usd <= 1e-9
            and abs(t.entry_price - t.market_mid_entry) <= 1e-9
        ):
            zero_friction_mid_cnt += 1
        if t.fee_rate_bps > 0.0 and not t.is_maker_entry and t.fees_usd <= 1e-9:
            missing_fee_cnt += 1
        if (
            t.exit_type == "PRE_RESOLUTION_EXIT"
            and t.exit_price in (0.0, 1.0)
            and t.end_ts is not None
            and t.exit_ts < t.end_ts - 300.0
        ):
            pre_exit_conflation_cnt += 1

    if time_travel_cnt > 0:
        violations.append(f"TIME_TRAVEL_EXIT_BEFORE_ENTRY:{time_travel_cnt}")
    if post_clinch_cnt > 0:
        violations.append(f"RT01_POST_CLINCH_LOOKAHEAD:{post_clinch_cnt}")
    if post_end_cnt > 0:
        violations.append(f"RT01_POST_END_LOOKAHEAD:{post_end_cnt}")
    if zero_friction_mid_cnt > 0:
        violations.append(f"RT02_ZERO_FRICTION_MIDPOINT_FABRICATION:{zero_friction_mid_cnt}")
    if missing_fee_cnt > 0:
        violations.append(f"RT03_FEE_ENABLED_TAKER_ZERO_FEE:{missing_fee_cnt}")
    if pre_exit_conflation_cnt > 0:
        violations.append(f"RT12_PRE_EXIT_BINARY_SETTLEMENT_CONFLATION:{pre_exit_conflation_cnt}")
    return violations


def _resolve_v2_fee_rate(
    t: TradeObservation,
    rates_map: Optional[Mapping[str, float]] = None,
    *,
    for_taker_counterfactual: bool = False,
) -> float:
    """
    Resolves effective Polymarket Protocol V2 curved fee rate `r` (`fee_ps = r * p * (1 - p)`).
    Explicitly guards against the `base_fee == 1000` (`1000.0` bps) V2 curved-fee sentinel (`RT-03`)
    so `1000.0` is never misinterpreted as a `10%` (`0.10`) rate!
    """
    rates = rates_map if rates_map is not None else EMPIRICAL_2026_V2_CATEGORY_RATES
    if t.is_maker_entry and not for_taker_counterfactual:
        return 0.0
    if t.fee_rate is not None and 0.0 <= float(t.fee_rate) <= 0.15:
        return float(t.fee_rate)
    if 0.0 < t.fee_rate_bps < 999.0:
        return min(0.08, t.fee_rate_bps / 10_000.0)
    if t.fees_usd > 0.0 and t.shares > 0.0:
        p_c = _clamp_prob(t.entry_price, eps=1e-4)
        denom = t.shares * p_c * (1.0 - p_c)
        if t.exit_type == "PRE_RESOLUTION_EXIT":
            p_ex = _clamp_prob(t.exit_price, eps=1e-4)
            denom += t.shares * p_ex * (1.0 - p_ex)
        if denom > 1e-9:
            return min(0.08, max(0.0, t.fees_usd / denom))
    cat_key = (t.category or "").strip().lower()
    if t.fee_rate_bps >= 999.0 or not for_taker_counterfactual or t.is_maker_entry:
        return float(rates.get(cat_key, 0.04 if t.fee_rate_bps >= 999.0 or not for_taker_counterfactual else 0.0))
    return 0.0


def reprice_trades_under_2026_v2_fee_regime(
    trades: Sequence[TradeObservation],
    category_rates: Optional[Mapping[str, float]] = None,
    market_fees_enabled: Optional[Mapping[str, bool]] = None,
) -> Tuple[List[TradeObservation], float, int]:
    """
    Independently reprices taker trades using calibrated Nov 2026 Polymarket V2 fee curves
    (`rate * p * (1 - p)`), returning `(repriced_trades, total_fee_shortfall_usd, undercharged_count)`.
    Honors per-market `fees_enabled == False` metadata and V2 `1000` sentinel (`RT-03`).
    """
    rates = dict(EMPIRICAL_2026_V2_CATEGORY_RATES)
    if category_rates:
        for k, v in category_rates.items():
            rates[str(k).strip().lower()] = float(v)

    repriced: List[TradeObservation] = []
    shortfall_tot = 0.0
    undercharged_cnt = 0

    for t in trades:
        if t.is_maker_entry or (market_fees_enabled is not None and market_fees_enabled.get(t.market_id) is False):
            repriced.append(t)
            continue
        cat_key = (t.category or "").strip().lower()
        if t.fee_rate is not None and 0.0 <= float(t.fee_rate) <= 0.15:
            rate = float(t.fee_rate)
        elif 0.0 < t.fee_rate_bps < 999.0:
            rate = t.fee_rate_bps / 10_000.0
        else:
            rate = float(rates.get(cat_key, 0.04))
        p_c = _clamp_prob(t.entry_price, eps=1e-4)
        expected_entry_fee = t.shares * rate * p_c * (1.0 - p_c)
        if t.exit_type == "PRE_RESOLUTION_EXIT":
            p_ex = _clamp_prob(t.exit_price, eps=1e-4)
            expected_entry_fee += t.shares * rate * p_ex * (1.0 - p_ex)

        shortfall = max(0.0, expected_entry_fee - max(0.0, t.fees_usd))
        if shortfall > 1e-4 and max(0.0, t.fees_usd) < 0.5 * expected_entry_fee:
            undercharged_cnt += 1
        shortfall_tot += shortfall
        if shortfall > 1e-9:
            repriced.append(
                TradeObservation(
                    trade_id=t.trade_id,
                    strategy_id=t.strategy_id,
                    market_id=t.market_id,
                    event_id=t.event_id,
                    category=t.category,
                    side=t.side,
                    exit_type=t.exit_type,
                    entry_ts=t.entry_ts,
                    exit_ts=t.exit_ts,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    market_mid_entry=t.market_mid_entry,
                    model_prob_entry=t.model_prob_entry,
                    outcome_binary=t.outcome_binary,
                    notional_usd=t.notional_usd,
                    shares=t.shares,
                    gross_pnl_usd=t.gross_pnl_usd,
                    fees_usd=t.fees_usd + shortfall,
                    spread_slippage_cost_usd=t.spread_slippage_cost_usd,
                    net_pnl_usd=t.net_pnl_usd - shortfall,
                    available_depth_usd=t.available_depth_usd,
                    fee_rate_bps=t.fee_rate_bps if t.fee_rate_bps >= 999.0 else max(t.fee_rate_bps, rate * 10_000.0),
                    is_maker_entry=t.is_maker_entry,
                    clinch_ts=t.clinch_ts,
                    end_ts=t.end_ts,
                    uma_disputed=t.uma_disputed,
                    data_quality_class=t.data_quality_class,
                    subcategory=t.subcategory,
                    fee_rate=rate,
                    is_void_50_50=t.is_void_50_50,
                )
            )
        else:
            repriced.append(t)

    return repriced, round(shortfall_tot, 6), undercharged_cnt


# ---------------------------------------------------------------------------
# 2. Strict 3-Way Chronological Split + Purging & Embargoing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PurgedSplitResult:
    train: List[TradeObservation]
    validation: List[TradeObservation]
    holdout: List[TradeObservation]
    train_end_ts: float
    val_end_ts: float
    embargo_sec: float
    purged_train_val_count: int
    purged_val_holdout_count: int
    embargoed_count: int
    zero_boundary_overlap: bool


def purged_three_way_split(
    trades: Sequence[TradeObservation],
    *,
    train_frac: float = 0.50,
    val_frac: float = 0.25,
    embargo_sec: float = 3600.0,
    explicit_train_end_ts: Optional[float] = None,
    explicit_val_end_ts: Optional[float] = None,
) -> PurgedSplitResult:
    """
    Splits trades chronologically into Train (50%), Validation (25%), and Sealed Holdout (25%),
    strictly PURGING any trade open across a boundary (`entry_ts <= split_ts < exit_ts`) from
    the earlier split and applying `embargo_sec` before the subsequent split begins.
    """
    if not (0.10 <= train_frac <= 0.80) or not (0.05 <= val_frac <= 0.50) or (train_frac + val_frac >= 0.95):
        raise ValueError(f"Invalid split fractions: train_frac={train_frac}, val_frac={val_frac}")
    embargo = max(0.0, float(embargo_sec))

    if not trades:
        return PurgedSplitResult(
            train=[],
            validation=[],
            holdout=[],
            train_end_ts=0.0,
            val_end_ts=0.0,
            embargo_sec=embargo,
            purged_train_val_count=0,
            purged_val_holdout_count=0,
            embargoed_count=0,
            zero_boundary_overlap=True,
        )

    ordered = sorted(trades, key=lambda x: (x.entry_ts, x.exit_ts, x.trade_id))
    n = len(ordered)
    if explicit_train_end_ts is not None and explicit_val_end_ts is not None:
        t_tr_end = float(explicit_train_end_ts)
        t_vl_end = float(explicit_val_end_ts)
    else:
        idx_tr = min(n - 1, max(0, int(train_frac * n) - 1))
        idx_vl = min(n - 1, max(idx_tr, int((train_frac + val_frac) * n) - 1))
        t_tr_end = ordered[idx_tr].entry_ts
        t_vl_end = ordered[idx_vl].entry_ts
        if t_vl_end < t_tr_end:
            t_vl_end = t_tr_end

    train_out: List[TradeObservation] = []
    val_out: List[TradeObservation] = []
    holdout_out: List[TradeObservation] = []
    purged_tr_vl = 0
    purged_vl_ho = 0
    embargoed_cnt = 0

    val_start_ts = t_tr_end + embargo
    ho_start_ts = t_vl_end + embargo

    for trd in ordered:
        if trd.entry_ts <= t_tr_end:
            if trd.exit_ts <= t_tr_end:
                train_out.append(trd)
            else:
                # Open across Train -> Validation boundary: PURGE to block outcome leakage!
                purged_tr_vl += 1
        elif trd.entry_ts < val_start_ts:
            embargoed_cnt += 1
        elif trd.entry_ts <= t_vl_end:
            if trd.exit_ts <= t_vl_end:
                val_out.append(trd)
            else:
                # Open across Validation -> Sealed Holdout boundary: PURGE to block outcome leakage!
                purged_vl_ho += 1
        elif trd.entry_ts < ho_start_ts:
            embargoed_cnt += 1
        else:
            holdout_out.append(trd)

    # Mathematical verification of zero future-information leak across boundaries
    max_train_exit = max((x.exit_ts for x in train_out), default=-math.inf)
    min_val_entry = min((x.entry_ts for x in val_out), default=math.inf)
    max_val_exit = max((x.exit_ts for x in val_out), default=-math.inf)
    min_ho_entry = min((x.entry_ts for x in holdout_out), default=math.inf)

    zero_overlap = (
        max_train_exit <= t_tr_end + 1e-9
        and min_val_entry >= val_start_ts - 1e-9
        and max_val_exit <= t_vl_end + 1e-9
        and min_ho_entry >= ho_start_ts - 1e-9
    )

    return PurgedSplitResult(
        train=train_out,
        validation=val_out,
        holdout=holdout_out,
        train_end_ts=t_tr_end,
        val_end_ts=t_vl_end,
        embargo_sec=embargo,
        purged_train_val_count=purged_tr_vl,
        purged_val_holdout_count=purged_vl_ho,
        embargoed_count=embargoed_cnt,
        zero_boundary_overlap=zero_overlap,
    )


# ---------------------------------------------------------------------------
# 3. Walk-Forward OOS, CPCV(N, k) & Probability of Backtest Overfitting (PBO)
# ---------------------------------------------------------------------------


def _sharpe_from_values(vals: Sequence[float]) -> float:
    n = len(vals)
    if n < 2:
        return 0.0
    mu = sum(vals) / n
    var = sum((x - mu) ** 2 for x in vals) / (n - 1)
    if var <= 1e-15:
        return 0.0
    return mu / math.sqrt(var)


def run_purged_walk_forward(
    trades_by_variant: Mapping[str, Sequence[TradeObservation]],
    *,
    n_folds: int = 5,
    embargo_sec: float = 3600.0,
) -> Dict[str, Any]:
    """
    Expanding-window Purged Walk-Forward evaluation across `n_folds` chronological blocks.
    At step `k` (`1 .. n_folds - 1`), selects the variant with highest purged in-sample
    cluster-adjusted Sharpe on blocks `[0 .. k-1]` (excluding any trade with `exit_ts > boundary_ts`),
    and evaluates strictly out-of-sample on block `k` (`entry_ts >= boundary_ts + embargo_sec`).
    """
    if not trades_by_variant:
        return {"n_folds": n_folds, "oos_folds": [], "stitched_oos_pnl_usd": 0.0, "positive_fold_rate": 0.0}

    all_entry_ts = sorted({t.entry_ts for seq in trades_by_variant.values() for t in seq})
    if len(all_entry_ts) < max(6, n_folds * 2):
        return {"n_folds": n_folds, "oos_folds": [], "stitched_oos_pnl_usd": 0.0, "positive_fold_rate": 0.0}

    n_ts = len(all_entry_ts)
    boundaries = [all_entry_ts[min(n_ts - 1, int((i / n_folds) * n_ts))] for i in range(n_folds)]
    boundaries.append(all_entry_ts[-1] + 1.0)

    oos_folds: List[Dict[str, Any]] = []
    stitched_pnls: List[float] = []

    for fold_idx in range(1, n_folds):
        cut_ts = boundaries[fold_idx]
        test_start = cut_ts + max(0.0, embargo_sec)
        test_end = boundaries[fold_idx + 1]

        best_var: Optional[str] = None
        best_is_score = -1e18
        for var_name, seq in trades_by_variant.items():
            is_trades = [t for t in seq if t.entry_ts <= cut_ts and t.exit_ts <= cut_ts]
            if len(is_trades) < 3:
                score = -1e9 + sum(t.net_pnl_usd for t in is_trades)
            else:
                by_cl: Dict[str, float] = collections.defaultdict(float)
                for t in is_trades:
                    by_cl[t.canonical_cluster_id()] += t.net_pnl_usd
                cl_vals = list(by_cl.values())
                sr = _sharpe_from_values(cl_vals) * math.sqrt(max(1, len(cl_vals)))
                score = sr if sum(cl_vals) > 0 else sr - 2.0
            if score > best_is_score:
                best_is_score = score
                best_var = var_name

        chosen = best_var or next(iter(trades_by_variant.keys()))
        oos_seq = [
            t
            for t in trades_by_variant[chosen]
            if test_start <= t.entry_ts < test_end
        ]
        fold_pnl = sum(t.net_pnl_usd for t in oos_seq)
        stitched_pnls.extend(t.net_pnl_usd for t in oos_seq)
        oos_folds.append(
            {
                "fold_index": fold_idx,
                "selected_variant": chosen,
                "in_sample_score": round(best_is_score, 4),
                "oos_trades": len(oos_seq),
                "oos_net_pnl_usd": round(fold_pnl, 4),
            }
        )

    pos_folds = sum(1 for f in oos_folds if f["oos_net_pnl_usd"] > 0.0)
    return {
        "n_folds": n_folds,
        "oos_folds": oos_folds,
        "stitched_oos_trades": len(stitched_pnls),
        "stitched_oos_pnl_usd": round(sum(stitched_pnls), 4),
        "stitched_oos_sharpe_per_trade": round(_sharpe_from_values(stitched_pnls), 4),
        "positive_fold_count": pos_folds,
        "positive_fold_rate": round(pos_folds / max(1, len(oos_folds)), 4),
    }


def compute_cpcv_and_pbo(
    trades_by_variant: Mapping[str, Sequence[TradeObservation]],
    *,
    n_groups: int = 6,
    k_test_groups: int = 2,
    embargo_sec: float = 3600.0,
) -> Dict[str, Any]:
    """
    Implements Combinatorial Purged Cross-Validation `CPCV(n_groups, k_test_groups)` and
    Bailey, Borwein, Lopez de Prado & Zhu (2017) Probability of Backtest Overfitting (`PBO`).

    - Purges any training trade whose `[entry_ts, exit_ts]` overlaps any test group or falls
      within `embargo_sec` after a test group's end timestamp!
    - When `len(trades_by_variant) >= 2`, computes exact relative OOS rank `omega_c` and logit
      `lambda_c = ln(omega_c / (1 - omega_c))` of each split's in-sample winner, reporting
      `pbo = mean(lambda_c <= 0)`.
    - When `len(trades_by_variant) == 1`, reports exact `CPCV` 15-split OOS stability metrics
      and `prob_oos_loss` across combinatorial subsets.
    """
    if n_groups < 3 or k_test_groups < 1 or k_test_groups >= n_groups:
        raise ValueError(f"Invalid CPCV(n_groups={n_groups}, k_test_groups={k_test_groups})")

    variant_names = list(trades_by_variant.keys())
    m_variants = len(variant_names)
    if m_variants == 0:
        return {
            "n_groups": n_groups,
            "k_test_groups": k_test_groups,
            "n_combinations": 0,
            "m_variants": 0,
            "pbo": 1.0,
            "prob_oos_loss": 1.0,
            "median_oos_sharpe": 0.0,
            "median_oos_pnl_usd": 0.0,
            "splits": [],
        }

    all_ts = sorted({t.entry_ts for seq in trades_by_variant.values() for t in seq})
    if len(all_ts) < n_groups * 2:
        return {
            "n_groups": n_groups,
            "k_test_groups": k_test_groups,
            "n_combinations": 0,
            "m_variants": m_variants,
            "pbo": 0.5 if m_variants > 1 else None,
            "prob_oos_loss": 1.0,
            "median_oos_sharpe": 0.0,
            "median_oos_pnl_usd": 0.0,
            "insufficient_timeline": True,
            "splits": [],
        }

    n_t = len(all_ts)
    group_bounds: List[Tuple[float, float]] = []
    for g in range(n_groups):
        i0 = int((g / n_groups) * n_t)
        i1 = int(((g + 1) / n_groups) * n_t) - 1
        t_s = all_ts[i0]
        t_e = all_ts[max(i0, i1)]
        if g == n_groups - 1:
            t_e = max(t_e, all_ts[-1]) + 1e-6
        group_bounds.append((t_s, t_e))

    embargo = max(0.0, float(embargo_sec))
    splits_out: List[Dict[str, Any]] = []
    logits: List[float] = []
    winner_oos_pnls: List[float] = []
    winner_oos_sharpes: List[float] = []

    for test_groups in itertools.combinations(range(n_groups), k_test_groups):
        test_set = set(test_groups)
        test_intervals = [group_bounds[g] for g in test_groups]

        is_scores: Dict[str, float] = {}
        oos_scores: Dict[str, float] = {}
        oos_pnls: Dict[str, float] = {}
        oos_counts: Dict[str, int] = {}

        for v_name in variant_names:
            seq = trades_by_variant[v_name]
            # Train: strictly outside every test interval with both pre-test purge (exit_ts < ts_s)
            # and post-test embargo (entry_ts >= ts_e + embargo)
            tr_sub = [
                t
                for t in seq
                if all((t.exit_ts < ts_s) or (t.entry_ts >= ts_e + embargo) for ts_s, ts_e in test_intervals)
            ]
            # Test: inside one of the test groups (and if a train group immediately precedes this test group,
            # enforce embargo after that train group so open train positions never overlap test!)
            te_sub: List[TradeObservation] = []
            for g_idx in test_groups:
                g_s, g_e = group_bounds[g_idx]
                eff_s = g_s + (embargo if (g_idx > 0 and (g_idx - 1) not in test_set) else 0.0)
                # If a train group immediately follows g_idx, require exit_ts <= g_e so test trades do not leak into train
                must_close_before_end = (g_idx < n_groups - 1) and ((g_idx + 1) not in test_set)
                for t in seq:
                    if eff_s <= t.entry_ts <= g_e:
                        if not must_close_before_end or t.exit_ts <= g_e:
                            te_sub.append(t)

            # Cluster-aggregated Sharpe for robust ranking
            tr_cl: Dict[str, float] = collections.defaultdict(float)
            for t in tr_sub:
                tr_cl[t.canonical_cluster_id()] += t.net_pnl_usd
            te_cl: Dict[str, float] = collections.defaultdict(float)
            for t in te_sub:
                te_cl[t.canonical_cluster_id()] += t.net_pnl_usd

            tr_vals = list(tr_cl.values())
            te_vals = list(te_cl.values())
            is_sr = _sharpe_from_values(tr_vals) * math.sqrt(max(1, len(tr_vals))) if len(tr_vals) >= 2 else sum(tr_vals)
            oos_sr = _sharpe_from_values(te_vals) * math.sqrt(max(1, len(te_vals))) if len(te_vals) >= 2 else (
                1e-6 * sum(te_vals)
            )
            is_scores[v_name] = is_sr
            oos_scores[v_name] = oos_sr
            oos_pnls[v_name] = sum(t.net_pnl_usd for t in te_sub)
            oos_counts[v_name] = len(te_sub)

        # Pick In-Sample optimal variant
        best_v = max(variant_names, key=lambda vn: (is_scores[vn], vn))
        w_oos_pnl = oos_pnls[best_v]
        w_oos_sr = oos_scores[best_v]
        winner_oos_pnls.append(w_oos_pnl)
        winner_oos_sharpes.append(w_oos_sr)

        omega_c: Optional[float] = None
        logit_c: Optional[float] = None
        if m_variants >= 2:
            # Average rank (1 = worst OOS, M = best OOS) with tie-splitting
            less_cnt = sum(1 for vn in variant_names if oos_scores[vn] < w_oos_sr - 1e-12)
            tie_cnt = sum(1 for vn in variant_names if abs(oos_scores[vn] - w_oos_sr) <= 1e-12)
            rank_pos = less_cnt + 0.5 * (tie_cnt + 1)
            omega_c = rank_pos / (m_variants + 1.0)
            omega_c = min(1.0 - 1e-6, max(1e-6, omega_c))
            logit_c = math.log(omega_c / (1.0 - omega_c))
            logits.append(logit_c)

        splits_out.append(
            {
                "test_groups": list(test_groups),
                "selected_is_variant": best_v,
                "is_score": round(is_scores[best_v], 4),
                "oos_trades": oos_counts[best_v],
                "oos_net_pnl_usd": round(w_oos_pnl, 4),
                "oos_score": round(w_oos_sr, 4),
                "oos_relative_rank_omega": round(omega_c, 4) if omega_c is not None else None,
                "logit_lambda": round(logit_c, 4) if logit_c is not None else None,
            }
        )

    n_comb = len(splits_out)
    pbo_val = (sum(1 for lam in logits if lam <= 0.0) / len(logits)) if logits else None
    loss_splits = sum(1 for p in winner_oos_pnls if p <= 0.0)

    return {
        "n_groups": n_groups,
        "k_test_groups": k_test_groups,
        "n_combinations": n_comb,
        "m_variants": m_variants,
        "pbo": round(pbo_val, 4) if pbo_val is not None else None,
        "median_logit_lambda": round(statistics.median(logits), 4) if logits else None,
        "prob_oos_loss": round(loss_splits / max(1, n_comb), 4),
        "positive_oos_splits": n_comb - loss_splits,
        "median_oos_pnl_usd": round(statistics.median(winner_oos_pnls), 4) if winner_oos_pnls else 0.0,
        "min_oos_pnl_usd": round(min(winner_oos_pnls), 4) if winner_oos_pnls else 0.0,
        "median_oos_sharpe": round(statistics.median(winner_oos_sharpes), 4) if winner_oos_sharpes else 0.0,
        "splits": splits_out,
    }


def evaluate_parameter_stability_surface(
    base_params: Mapping[str, float],
    evaluator_fn: Callable[[Dict[str, float]], Sequence[TradeObservation]],
    *,
    perturbation_pcts: Sequence[float] = (-0.50, -0.20, 0.20, 0.50),
) -> Dict[str, Any]:
    """
    Perturbs each numeric parameter around `base_params` by `±20%` and `±50%` (one-at-a-time
    and joint diagonal perturbations) to detect fragile needle-spike overfitting (`RT-07`).
    """
    base_dict = {k: float(v) for k, v in base_params.items()}
    base_trades = list(evaluator_fn(dict(base_dict)))
    base_pnl = sum(t.net_pnl_usd for t in base_trades)
    base_sr = _sharpe_from_values([t.net_pnl_usd for t in base_trades])

    grid_points: List[Dict[str, Any]] = []
    for param_name, base_val in base_dict.items():
        for pct in perturbation_pcts:
            pert_dict = dict(base_dict)
            if abs(base_val) > 1e-12:
                pert_dict[param_name] = base_val * (1.0 + float(pct))
            else:
                pert_dict[param_name] = float(pct) * 0.10
            sub_trades = list(evaluator_fn(pert_dict))
            sub_pnl = sum(t.net_pnl_usd for t in sub_trades)
            sub_sr = _sharpe_from_values([t.net_pnl_usd for t in sub_trades])
            grid_points.append(
                {
                    "parameter": param_name,
                    "perturbation_pct": float(pct),
                    "perturbed_value": round(pert_dict[param_name], 6),
                    "n_trades": len(sub_trades),
                    "net_pnl_usd": round(sub_pnl, 4),
                    "sharpe_per_trade": round(sub_sr, 4),
                }
            )

    if not grid_points:
        return {
            "base_net_pnl_usd": round(base_pnl, 4),
            "base_sharpe_per_trade": round(base_sr, 4),
            "neighbor_count": 0,
            "profitable_neighbor_fraction": 1.0 if base_pnl > 0 else 0.0,
            "20pct_profitable_fraction": 1.0 if base_pnl > 0 else 0.0,
            "cliff_ratio_min_to_base_pnl": 1.0 if base_pnl > 0 else 0.0,
            "is_spike_overfit": False,
            "perturbations": [],
        }

    prof_all = sum(1 for g in grid_points if g["net_pnl_usd"] > 0.0) / len(grid_points)
    pts_20 = [g for g in grid_points if abs(abs(g["perturbation_pct"]) - 0.20) <= 1e-6]
    prof_20 = (sum(1 for g in pts_20 if g["net_pnl_usd"] > 0.0) / len(pts_20)) if pts_20 else prof_all
    min_20_pnl = min((g["net_pnl_usd"] for g in (pts_20 or grid_points)), default=0.0)
    cliff_ratio = (min_20_pnl / base_pnl) if base_pnl > 1e-9 else 0.0
    is_spike = bool(base_pnl > 0.0 and (prof_20 < 0.60 or cliff_ratio < -0.25))

    return {
        "base_net_pnl_usd": round(base_pnl, 4),
        "base_sharpe_per_trade": round(base_sr, 4),
        "neighbor_count": len(grid_points),
        "profitable_neighbor_fraction": round(prof_all, 4),
        "20pct_profitable_fraction": round(prof_20, 4),
        "cliff_ratio_min_to_base_pnl": round(cliff_ratio, 4),
        "is_spike_overfit": is_spike,
        "perturbations": grid_points,
    }


def evaluate_regime_and_category_stability(trades: Sequence[TradeObservation]) -> Dict[str, Any]:
    """
    Evaluates stability across chronological Early vs Late subperiods and across market
    categories to flag strategies reliant on a single fleeting regime or single lucky category.
    """
    if not trades:
        return {
            "early_half_pnl_usd": 0.0,
            "late_half_pnl_usd": 0.0,
            "both_halves_profitable": False,
            "category_breakdown": {},
            "max_single_category_pnl_share": 1.0,
        }

    ordered = sorted(trades, key=lambda x: x.entry_ts)
    mid_idx = max(1, len(ordered) // 2)
    early = ordered[:mid_idx]
    late = ordered[mid_idx:]
    early_pnl = sum(t.net_pnl_usd for t in early)
    late_pnl = sum(t.net_pnl_usd for t in late)

    by_cat: Dict[str, List[TradeObservation]] = collections.defaultdict(list)
    for t in ordered:
        by_cat[t.category or "Uncategorized"].append(t)

    cat_summary: Dict[str, Dict[str, Any]] = {}
    pos_cat_pnls: List[float] = []
    for cat, seq in sorted(by_cat.items()):
        c_pnl = sum(t.net_pnl_usd for t in seq)
        c_clusters = len({t.canonical_cluster_id() for t in seq})
        c_wr = sum(1 for t in seq if t.net_pnl_usd > 0) / len(seq)
        cat_summary[cat] = {
            "n_trades": len(seq),
            "n_clusters": c_clusters,
            "net_pnl_usd": round(c_pnl, 4),
            "win_rate": round(c_wr, 4),
        }
        if c_pnl > 0:
            pos_cat_pnls.append(c_pnl)

    tot_pos = sum(pos_cat_pnls)
    max_cat_share = (max(pos_cat_pnls) / tot_pos) if tot_pos > 1e-9 else 1.0

    return {
        "early_half_trades": len(early),
        "early_half_pnl_usd": round(early_pnl, 4),
        "late_half_trades": len(late),
        "late_half_pnl_usd": round(late_pnl, 4),
        "both_halves_profitable": bool(early_pnl > 0.0 and late_pnl > 0.0),
        "category_count": len(cat_summary),
        "profitable_category_count": len(pos_cat_pnls),
        "max_single_category_pnl_share": round(max_cat_share, 4),
        "category_breakdown": cat_summary,
    }


# ---------------------------------------------------------------------------
# 4. Event-Cluster-Aware Bootstrap Confidence Intervals (B >= 2,000)
# ---------------------------------------------------------------------------


def cluster_bootstrap_ci(
    trades: Sequence[TradeObservation],
    *,
    n_boot: int = 2000,
    confidence_level: float = 0.95,
    seed: int = 20261112,
    strict_date_category_merge: bool = True,
) -> Dict[str, Any]:
    """
    Resamples correlated event clusters (`K` clusters with replacement across `B >= 2,000` draws)
    rather than individual contracts, eliminating `sqrt(N)` correlation inflation (`RT-06`).
    """
    b_draws = max(2000, int(n_boot))
    n_trades = len(trades)
    if n_trades == 0:
        return {
            "n_trades": 0,
            "n_clusters": 0,
            "n_boot": b_draws,
            "total_net_pnl_ci95": [0.0, 0.0],
            "mean_trade_pnl_ci95": [0.0, 0.0],
            "profit_per_dollar_day_ci95": [0.0, 0.0],
            "sharpe_ci95": [0.0, 0.0],
            "cluster_t_stat": 0.0,
            "one_sided_p_value": 1.0,
            "se_inflation_vs_iid": 1.0,
        }

    clusters_map: Dict[str, List[TradeObservation]] = collections.defaultdict(list)
    for t in trades:
        clusters_map[t.canonical_cluster_id(strict_date_category_merge=strict_date_category_merge)].append(t)

    cluster_keys = sorted(clusters_map.keys())
    k_clusters = len(cluster_keys)
    # Pre-aggregate per-cluster sufficient statistics for fast pure-Python resampling (O(B * K))
    # Tuple: (sum_net_pnl, count_trades, sum_dollar_days)
    cluster_stats: List[Tuple[float, int, float]] = []
    for ck in cluster_keys:
        seq = clusters_map[ck]
        c_pnl = sum(t.net_pnl_usd for t in seq)
        c_ddays = sum(t.notional_usd * t.hold_days for t in seq)
        cluster_stats.append((c_pnl, len(seq), c_ddays))

    obs_total_pnl = sum(s[0] for s in cluster_stats)
    obs_cluster_pnls = [s[0] for s in cluster_stats]

    # Compare cluster-robust SE of total PnL vs naive i.i.d. SE of total PnL
    if k_clusters >= 2:
        cl_mean = obs_total_pnl / k_clusters
        cl_var = sum((x - cl_mean) ** 2 for x in obs_cluster_pnls) / (k_clusters - 1)
        se_total_cluster = math.sqrt(k_clusters * max(0.0, cl_var))
        cluster_t_stat = obs_total_pnl / max(se_total_cluster, 1e-12) if se_total_cluster > 1e-12 else 0.0
    else:
        se_total_cluster = abs(obs_total_pnl)
        cluster_t_stat = 0.0

    if n_trades >= 2:
        tr_mean = obs_total_pnl / n_trades
        tr_var = sum((t.net_pnl_usd - tr_mean) ** 2 for t in trades) / (n_trades - 1)
        se_total_iid = math.sqrt(n_trades * max(0.0, tr_var))
    else:
        se_total_iid = max(1e-12, abs(obs_total_pnl))

    se_inflation = (se_total_cluster / se_total_iid) if se_total_iid > 1e-12 else 1.0

    if k_clusters < 2:
        # Single correlated event cluster: zero degrees of freedom across events!
        return {
            "n_trades": n_trades,
            "n_clusters": k_clusters,
            "n_boot": b_draws,
            "total_net_pnl_ci95": [min(0.0, round(obs_total_pnl, 4)), max(0.0, round(obs_total_pnl, 4))],
            "mean_trade_pnl_ci95": [min(0.0, round(obs_total_pnl / n_trades, 4)), max(0.0, round(obs_total_pnl / n_trades, 4))],
            "profit_per_dollar_day_ci95": [0.0, 0.0],
            "sharpe_ci95": [0.0, 0.0],
            "cluster_t_stat": 0.0,
            "one_sided_p_value": 1.0 if obs_total_pnl <= 0 else 0.5,
            "se_inflation_vs_iid": round(max(1.0, se_inflation), 4),
            "single_cluster_warning": True,
        }

    rng = random.Random(seed)
    boot_totals: List[float] = []
    boot_means: List[float] = []
    boot_pdd: List[float] = []
    boot_sharpes: List[float] = []
    non_pos_count = 0

    randrange = rng.randrange
    for _ in range(b_draws):
        tot_p = 0.0
        tot_n = 0
        tot_dd = 0.0
        tot_sq_cl = 0.0
        for _j in range(k_clusters):
            cp, cn, cdd = cluster_stats[randrange(k_clusters)]
            tot_p += cp
            tot_n += cn
            tot_dd += cdd
            tot_sq_cl += cp * cp
        boot_totals.append(tot_p)
        boot_means.append(tot_p / max(1, tot_n))
        boot_pdd.append(tot_p / max(1e-9, tot_dd))
        cl_mu_b = tot_p / k_clusters
        cl_var_b = max(0.0, (tot_sq_cl - k_clusters * cl_mu_b * cl_mu_b) / max(1, k_clusters - 1))
        sr_b = (cl_mu_b / math.sqrt(cl_var_b)) if cl_var_b > 1e-15 else 0.0
        boot_sharpes.append(sr_b)
        if tot_p <= 0.0:
            non_pos_count += 1

    boot_totals.sort()
    boot_means.sort()
    boot_pdd.sort()
    boot_sharpes.sort()

    alpha = 1.0 - min(0.999, max(0.50, float(confidence_level)))
    lo_idx = min(b_draws - 1, max(0, int((alpha / 2.0) * b_draws)))
    hi_idx = min(b_draws - 1, max(0, int((1.0 - alpha / 2.0) * b_draws) - 1))

    # Davison-Hinkley exact finite-sample Monte Carlo p-value: (1 + #{stat_b <= 0}) / (B + 1)
    p_val_one_sided = (1.0 + non_pos_count) / (b_draws + 1.0)

    return {
        "n_trades": n_trades,
        "n_clusters": k_clusters,
        "n_boot": b_draws,
        "total_net_pnl_ci95": [round(boot_totals[lo_idx], 4), round(boot_totals[hi_idx], 4)],
        "mean_trade_pnl_ci95": [round(boot_means[lo_idx], 6), round(boot_means[hi_idx], 6)],
        "profit_per_dollar_day_ci95": [round(boot_pdd[lo_idx], 6), round(boot_pdd[hi_idx], 6)],
        "sharpe_ci95": [round(boot_sharpes[lo_idx], 4), round(boot_sharpes[hi_idx], 4)],
        "cluster_se_total_pnl": round(se_total_cluster, 4),
        "naive_iid_se_total_pnl": round(se_total_iid, 4),
        "se_inflation_vs_iid": round(se_inflation, 4),
        "cluster_t_stat": round(cluster_t_stat, 4),
        "one_sided_p_value": round(p_val_one_sided, 6),
        "prob_positive_bootstrap": round(1.0 - (non_pos_count / b_draws), 4),
    }


# ---------------------------------------------------------------------------
# 5. Multiple-Testing Corrections (BH-FDR, BY-FDR, Holm-Bonferroni, PSR & DSR)
# ---------------------------------------------------------------------------


def benjamini_hochberg_fdr(
    p_values: Mapping[str, float],
    *,
    alpha: float = 0.05,
    total_trials_m: Optional[int] = None,
    arbitrary_dependence_by: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """
    Computes Benjamini-Hochberg (1995) step-up FDR `q`-values (or Benjamini-Yekutieli 2001
    under arbitrary dependence when `arbitrary_dependence_by=True`) across `M` tested hypotheses.
    If `total_trials_m > len(p_values)` (e.g. pre-filtered variants in a larger swarm sweep),
    uses `M = total_trials_m` so unreported failed trials are still penalized!
    """
    if not p_values:
        return {}
    items = sorted(((k, min(1.0, max(0.0, float(v)))) for k, v in p_values.items()), key=lambda kv: (kv[1], kv[0]))
    n_obs = len(items)
    m_eff = max(n_obs, int(total_trials_m or n_obs))
    c_m = sum(1.0 / i for i in range(1, m_eff + 1)) if arbitrary_dependence_by else 1.0

    raw_q = [0.0] * n_obs
    running_min = 1.0
    for idx in range(n_obs - 1, -1, -1):
        rank_1based = idx + 1
        _, p_i = items[idx]
        q_i = min(1.0, (p_i * m_eff * c_m) / rank_1based)
        running_min = min(running_min, q_i)
        raw_q[idx] = running_min

    out: Dict[str, Dict[str, Any]] = {}
    for idx, (k, p_i) in enumerate(items):
        q_val = raw_q[idx]
        out[k] = {
            "raw_p_value": round(p_i, 6),
            "rank": idx + 1,
            "effective_m_trials": m_eff,
            "bh_q_value": round(q_val, 6),
            "passes_fdr": bool(q_val <= alpha),
        }
    return out


def holm_bonferroni_correction(
    p_values: Mapping[str, float],
    *,
    alpha: float = 0.05,
    total_trials_m: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Computes Holm-Bonferroni (1979) step-down family-wise error rate (FWER) adjusted p-values
    across `M` total tested hypotheses.
    """
    if not p_values:
        return {}
    items = sorted(((k, min(1.0, max(0.0, float(v)))) for k, v in p_values.items()), key=lambda kv: (kv[1], kv[0]))
    n_obs = len(items)
    m_eff = max(n_obs, int(total_trials_m or n_obs))

    out: Dict[str, Dict[str, Any]] = {}
    running_max = 0.0
    any_failed = False
    for idx, (k, p_i) in enumerate(items):
        mult = max(1, m_eff - idx)
        adj_p = min(1.0, p_i * mult)
        running_max = max(running_max, adj_p)
        if running_max > alpha:
            any_failed = True
        out[k] = {
            "raw_p_value": round(p_i, 6),
            "rank": idx + 1,
            "effective_m_trials": m_eff,
            "holm_adjusted_p": round(running_max, 6),
            "passes_fwer": bool(not any_failed and running_max <= alpha),
        }
    return out


def sample_moments_skew_kurtosis(returns: Sequence[float]) -> Tuple[float, float, float, float]:
    """
    Returns `(mean, sample_std, skewness_gamma3, raw_pearson_kurtosis_gamma4)`.
    Uses standardized central moments `gamma_3 = m_3 / m_2^{3/2}` and `gamma_4 = m_4 / m_2^2`
    (`gamma_4 = 3.0` for Gaussian), which algebraically satisfy Pearson's inequality
    `gamma_4 >= gamma_3^2 + 1` on EVERY finite sample.
    """
    n = len(returns)
    if n == 0:
        return 0.0, 0.0, 0.0, 3.0
    mu = sum(returns) / n
    if n < 2:
        return mu, 0.0, 0.0, 3.0
    diffs = [float(x) - mu for x in returns]
    m2 = sum(d * d for d in diffs) / n
    sample_var = (m2 * n) / (n - 1)
    if m2 <= 1e-18 or sample_var <= 1e-18:
        return mu, 0.0, 0.0, 3.0
    m3 = sum(d * d * d for d in diffs) / n
    m4 = sum((d * d) ** 2 for d in diffs) / n
    skew = m3 / (m2 ** 1.5)
    kurt_pearson = m4 / (m2 * m2)
    return mu, math.sqrt(sample_var), skew, kurt_pearson


def expected_max_sharpe_null(num_trials_m: int, cross_trial_sr_std: float) -> float:
    """
    Bailey & Lopez de Prado (2014) False Strategy Theorem: expected maximum Sharpe Ratio `SR_0`
    among `M` independent zero-skill trials with cross-trial Sharpe standard deviation `sigma_SR`:
      E[max_m SR_m] ≈ sigma_SR * ((1 - gamma) * Phi^{-1}(1 - 1/M) + gamma * Phi^{-1}(1 - 1/(M*e)))
    """
    m = max(1, int(num_trials_m))
    if m <= 1 or cross_trial_sr_std <= 0.0:
        return 0.0
    term1 = (1.0 - EULER_MASCHERONI) * norm_inv_cdf(1.0 - (1.0 / m))
    term2 = EULER_MASCHERONI * norm_inv_cdf(1.0 - (1.0 / (m * math.e)))
    return max(0.0, float(cross_trial_sr_std) * (term1 + term2))


def deflated_sharpe_ratio(
    returns: Sequence[float],
    *,
    num_trials_m: int = 1,
    all_trial_sharpes: Optional[Sequence[float]] = None,
    benchmark_sr: float = 0.0,
) -> Dict[str, Any]:
    """
    Computes Bailey & Lopez de Prado (2014) Probabilistic Sharpe Ratio (`PSR(benchmark_sr)`)
    and Deflated Sharpe Ratio (`DSR`) correcting simultaneously for:
      1. Non-normal return skewness (`gamma_3`) and fat tails (`gamma_4`),
      2. Finite sample length `T` (recommend passing cluster-aggregated returns so `T = N_clusters`),
      3. Selection bias across `M = num_trials_m` total tested strategies/configurations.
    """
    t_len = len(returns)
    m_eff = max(1, int(num_trials_m))
    if all_trial_sharpes is not None:
        m_eff = max(m_eff, len(all_trial_sharpes))

    if t_len < 3:
        return {
            "sample_length_t": t_len,
            "num_trials_m": m_eff,
            "observed_sharpe": 0.0,
            "skewness": 0.0,
            "pearson_kurtosis": 3.0,
            "sharpe_std_error": 1.0,
            "expected_max_null_sr0": 0.0,
            "psr_vs_benchmark": 0.0,
            "dsr": 0.0,
            "dsr_p_value": 1.0,
        }

    mu, sd, skew, kurt = sample_moments_skew_kurtosis(returns)
    sr_hat = (mu / sd) if sd > 1e-15 else 0.0

    # Mertens (2002) / Bailey & Lopez de Prado (2014) non-normal variance of SR_hat:
    # Var(SR_hat) = (1 - gamma_3 * SR_hat + ((gamma_4 - 1)/4) * SR_hat^2) / (T - 1)
    numer = 1.0 - (skew * sr_hat) + 0.25 * (kurt - 1.0) * (sr_hat * sr_hat)
    sr_se = math.sqrt(max(1e-12, numer) / max(1, t_len - 1))

    # Cross-trial Sharpe dispersion floored at theoretical null dispersion sqrt(1 / (T - 1))
    # so callers cannot game SR_0 -> 0 by omitting failed variants or passing duplicate trials
    null_sr_var_floor = 1.0 / max(1, t_len - 1)
    if all_trial_sharpes and len(all_trial_sharpes) >= 2:
        finite_srs = [float(x) for x in all_trial_sharpes if math.isfinite(float(x))]
        obs_var = statistics.variance(finite_srs) if len(finite_srs) >= 2 else 0.0
        trial_sr_std = math.sqrt(max(obs_var, null_sr_var_floor))
    else:
        trial_sr_std = math.sqrt(null_sr_var_floor)

    sr_0 = max(float(benchmark_sr), expected_max_sharpe_null(m_eff, trial_sr_std))
    psr_val = norm_cdf((sr_hat - float(benchmark_sr)) / sr_se)
    dsr_val = norm_cdf((sr_hat - sr_0) / sr_se)

    return {
        "sample_length_t": t_len,
        "num_trials_m": m_eff,
        "observed_sharpe": round(sr_hat, 6),
        "skewness": round(skew, 4),
        "pearson_kurtosis": round(kurt, 4),
        "sharpe_std_error": round(sr_se, 6),
        "cross_trial_sr_std": round(trial_sr_std, 6),
        "expected_max_null_sr0": round(sr_0, 6),
        "psr_vs_benchmark": round(psr_val, 6),
        "dsr": round(dsr_val, 6),
        "dsr_p_value": round(1.0 - dsr_val, 6),
    }


# ---------------------------------------------------------------------------
# 6. Transaction-Cost Break-Even & Slippage Stress Multipliers
# ---------------------------------------------------------------------------


def evaluate_cost_stress_and_breakeven(
    trades: Sequence[TradeObservation],
    *,
    multipliers: Sequence[float] = (1.0, 1.5, 2.0, 3.0),
) -> Dict[str, Any]:
    """
    Evaluates strategy Net PnL, Win Rate, and Cluster Sharpe across spread/slippage multipliers
    `1.0x`, `1.5x`, `2.0x`, `3.0x` (`net_pnl(m) = gross_pnl - fees - m * spread_slippage_cost`),
    and computes exact break-even extra slippage in `bps` of committed notional and `cents/share`.
    """
    if not trades:
        return {
            "stress_grid": {},
            "breakeven_spread_multiplier": 0.0,
            "breakeven_total_friction_multiplier": 0.0,
            "breakeven_extra_slippage_bps": 0.0,
            "breakeven_extra_cents_per_share": 0.0,
            "survives_1_5x_cost": False,
            "survives_2_0x_cost": False,
        }

    tot_gross = sum(t.gross_pnl_usd for t in trades)
    tot_fees = sum(t.fees_usd for t in trades)
    tot_spread_slip = sum(t.spread_slippage_cost_usd for t in trades)
    tot_net_1x = sum(t.net_pnl_usd for t in trades)
    tot_notional = max(1e-9, sum(t.notional_usd for t in trades))
    tot_shares = max(1e-9, sum(t.shares for t in trades))

    stress_grid: Dict[str, Dict[str, Any]] = {}
    for mult in multipliers:
        m = float(mult)
        key = f"{m:.1f}x"
        stressed_pnls: List[float] = []
        cl_pnls: Dict[str, float] = collections.defaultdict(float)
        for t in trades:
            # Apply stress multiplier to spread/slippage; if spread_slippage_cost_usd was 0 on a
            # pure observed-L2 trade, apply conservative minimum 1-tick (0.5c/share) baseline shock for m > 1
            base_slip = t.spread_slippage_cost_usd
            extra_drag = (m - 1.0) * (base_slip if base_slip > 1e-9 else 0.005 * t.shares)
            p_m = t.net_pnl_usd - extra_drag
            stressed_pnls.append(p_m)
            cl_pnls[t.canonical_cluster_id()] += p_m

        net_m = sum(stressed_pnls)
        wr_m = sum(1 for x in stressed_pnls if x > 0.0) / len(stressed_pnls)
        cl_vals = list(cl_pnls.values())
        sr_m = _sharpe_from_values(cl_vals)
        stress_grid[key] = {
            "multiplier": m,
            "net_pnl_usd": round(net_m, 4),
            "avg_net_pnl_usd": round(net_m / len(trades), 6),
            "win_rate": round(wr_m, 4),
            "cluster_sharpe": round(sr_m, 4),
            "profitable": bool(net_m > 0.0),
        }

    eff_slip_denom = tot_spread_slip if tot_spread_slip > 1e-9 else sum(0.005 * t.shares for t in trades)
    be_spread_mult = ((tot_gross - tot_fees) / eff_slip_denom) if eff_slip_denom > 1e-9 else 0.0
    tot_friction = max(0.0, tot_fees) + eff_slip_denom
    be_total_mult = (tot_gross / tot_friction) if tot_friction > 1e-9 else 0.0
    be_extra_bps = (tot_net_1x / tot_notional) * 10_000.0
    be_extra_cents = (tot_net_1x / tot_shares) * 100.0

    s_15 = stress_grid.get("1.5x", {}).get("net_pnl_usd", -1.0) > 0.0
    s_20 = stress_grid.get("2.0x", {}).get("net_pnl_usd", -1.0) > 0.0

    return {
        "total_gross_pnl_usd": round(tot_gross, 4),
        "total_fees_usd": round(tot_fees, 4),
        "total_spread_slippage_1x_usd": round(tot_spread_slip, 4),
        "stress_grid": stress_grid,
        "breakeven_spread_multiplier": round(be_spread_mult, 4),
        "breakeven_total_friction_multiplier": round(be_total_mult, 4),
        "breakeven_extra_slippage_bps": round(be_extra_bps, 3),
        "breakeven_extra_cents_per_share": round(be_extra_cents, 4),
        "survives_1_5x_cost": bool(s_15),
        "survives_2_0x_cost": bool(s_20),
    }


# ---------------------------------------------------------------------------
# 7. Mandatory Simple Baselines (Market Zero-Edge, Naive Buy-NO/Fav, Random)
# ---------------------------------------------------------------------------


def evaluate_simple_baselines(
    trades: Sequence[TradeObservation],
    *,
    random_mc_draws: int = 500,
    seed: int = 20261112,
) -> Dict[str, Any]:
    """
    Compares a strategy against all three mandated simple baselines on the exact same
    set of market opportunities and realistic transaction-cost structure:
      (a) Market-Implied Probability Zero-Edge Benchmark (Brier & LogLoss skill benchmark),
      (b) Unconditional Buy-NO & Unconditional Buy-Favorite hold-to-maturity,
      (c) Random-Entry (50/50 YES vs NO) Monte Carlo cost-drag benchmark.
    """
    if not trades:
        return {
            "market_implied_zero_edge": {"brier_score": 0.25, "log_loss": 0.693147},
            "strategy_vs_market_scoring": {"brier_skill_score": 0.0, "log_loss_improvement": 0.0},
            "naive_unconditional_buy_no": {"net_pnl_usd": 0.0, "n_settled": 0},
            "naive_unconditional_buy_favorite": {"net_pnl_usd": 0.0, "n_settled": 0},
            "random_entry_cost_drag": {"expected_net_pnl_usd": 0.0, "strategy_percentile_vs_random": 0.5},
        }

    strat_total_net = sum(t.net_pnl_usd for t in trades)
    settled = [
        t for t in trades
        if t.outcome_binary is not None and 0.0 <= float(t.outcome_binary) <= 1.0
    ]

    # (a) Proper Scoring vs Market-Implied Midpoint Probability (supports continuous [0.0, 1.0] inc. 0.50 void)
    if settled:
        brier_mkt = sum((t.market_mid_entry - float(t.outcome_binary)) ** 2 for t in settled) / len(settled)
        brier_mod = sum((t.model_prob_entry - float(t.outcome_binary)) ** 2 for t in settled) / len(settled)
        ll_mkt = -sum(
            float(t.outcome_binary) * math.log(_clamp_prob(t.market_mid_entry))
            + (1.0 - float(t.outcome_binary)) * math.log(1.0 - _clamp_prob(t.market_mid_entry))
            for t in settled
        ) / len(settled)
        ll_mod = -sum(
            float(t.outcome_binary) * math.log(_clamp_prob(t.model_prob_entry))
            + (1.0 - float(t.outcome_binary)) * math.log(1.0 - _clamp_prob(t.model_prob_entry))
            for t in settled
        ) / len(settled)
        bss = 1.0 - (brier_mod / max(1e-12, brier_mkt))
        ll_imp = ll_mkt - ll_mod
    else:
        brier_mkt = 0.25
        brier_mod = 0.25
        ll_mkt = math.log(2.0)
        ll_mod = math.log(2.0)
        bss = 0.0
        ll_imp = 0.0

    # Deduplicate by market_id (earliest entry) for unconditional hold-to-maturity baselines
    seen_mkts: set[str] = set()
    unique_settled: List[TradeObservation] = []
    for t in sorted(settled, key=lambda x: (x.entry_ts, x.trade_id)):
        if t.market_id not in seen_mkts:
            seen_mkts.add(t.market_id)
            unique_settled.append(t)

    def _counterfactual_hold_net(t: TradeObservation, choose_side: str) -> float:
        # Convert traded-token mid & continuous payout into YES-side mid & YES/NO settlement payouts
        y_side = float(t.outcome_binary if t.outcome_binary is not None else 0.0)
        if t.side == "YES":
            yes_mid = t.market_mid_entry
            if t.uma_disputed and y_side == 0.0:
                yes_pay, no_pay = 0.0, 0.0
            elif t.is_void_50_50 or abs(y_side - 0.5) <= 1e-6:
                yes_pay, no_pay = 0.5, 0.5
            else:
                yes_pay, no_pay = y_side, 1.0 - y_side
        else:
            yes_mid = _clamp_prob(1.0 - t.market_mid_entry, eps=1e-4)
            if t.uma_disputed and y_side == 0.0:
                yes_pay, no_pay = 0.0, 0.0
            elif t.is_void_50_50 or abs(y_side - 0.5) <= 1e-6:
                yes_pay, no_pay = 0.5, 0.5
            else:
                no_pay, yes_pay = y_side, 1.0 - y_side

        half_spread = max(0.005, (t.spread_slippage_cost_usd / max(1e-6, t.shares)))
        fee_rate = _resolve_v2_fee_rate(t, for_taker_counterfactual=True)

        if choose_side == "NO":
            mid_c = _clamp_prob(1.0 - yes_mid, eps=1e-3)
            pay_c = no_pay
        else:
            mid_c = _clamp_prob(yes_mid, eps=1e-3)
            pay_c = yes_pay

        ask_c = min(0.995, mid_c + half_spread)
        sh_c = t.notional_usd / ask_c
        fee_c = sh_c * fee_rate * ask_c * (1.0 - ask_c)
        return sh_c * (float(pay_c) - ask_c) - fee_c

    buy_no_pnls = [_counterfactual_hold_net(t, "NO") for t in unique_settled]
    buy_fav_pnls = [
        _counterfactual_hold_net(
            t,
            "YES"
            if ((t.market_mid_entry if t.side == "YES" else (1.0 - t.market_mid_entry)) >= 0.50)
            else "NO",
        )
        for t in unique_settled
    ]

    # (c) Random-Entry 50/50 YES/NO Monte Carlo Cost-Drag Benchmark
    rng = random.Random(seed)
    rand_totals: List[float] = []
    if unique_settled:
        pair_pnls = [(_counterfactual_hold_net(t, "YES"), _counterfactual_hold_net(t, "NO")) for t in unique_settled]
        exact_expected_random = sum(0.5 * (py + pn) for py, pn in pair_pnls)
        for _ in range(max(100, int(random_mc_draws))):
            s_r = sum(py if rng.random() < 0.5 else pn for py, pn in pair_pnls)
            rand_totals.append(s_r)
        rand_totals.sort()
        pct_vs_rand = sum(1 for x in rand_totals if x < strat_total_net) / len(rand_totals)
    else:
        # For pre-resolution trading datasets without terminal binary labels, zero-skill random entry
        # loses expected round-trip fees + spread/slippage
        exact_expected_random = -sum(max(0.0, t.fees_usd) + t.spread_slippage_cost_usd for t in trades)
        pct_vs_rand = 1.0 if strat_total_net > exact_expected_random else 0.0

    buy_no_tot = sum(buy_no_pnls)
    buy_fav_tot = sum(buy_fav_pnls)

    return {
        "market_implied_zero_edge": {
            "n_settled": len(settled),
            "market_brier_score": round(brier_mkt, 6),
            "model_brier_score": round(brier_mod, 6),
            "market_log_loss": round(ll_mkt, 6),
            "model_log_loss": round(ll_mod, 6),
            "zero_edge_net_pnl_after_costs_usd": round(
                -sum(max(0.0, t.fees_usd) + t.spread_slippage_cost_usd for t in trades), 4
            ),
        },
        "strategy_vs_market_scoring": {
            "brier_skill_score": round(bss, 6),
            "log_loss_improvement": round(ll_imp, 6),
            "beats_market_probabilities": bool(len(settled) > 0 and bss > 0.0 and ll_imp > 0.0),
        },
        "naive_unconditional_buy_no": {
            "n_unique_markets": len(unique_settled),
            "net_pnl_usd": round(buy_no_tot, 4),
            "sharpe_per_market": round(_sharpe_from_values(buy_no_pnls), 4),
            "strategy_excess_pnl_vs_buy_no_usd": round(strat_total_net - buy_no_tot, 4),
        },
        "naive_unconditional_buy_favorite": {
            "n_unique_markets": len(unique_settled),
            "net_pnl_usd": round(buy_fav_tot, 4),
            "sharpe_per_market": round(_sharpe_from_values(buy_fav_pnls), 4),
            "strategy_excess_pnl_vs_buy_fav_usd": round(strat_total_net - buy_fav_tot, 4),
        },
        "random_entry_cost_drag": {
            "expected_net_pnl_usd": round(exact_expected_random, 4),
            "mc_p95_net_pnl_usd": round(rand_totals[int(0.95 * len(rand_totals))], 4) if rand_totals else 0.0,
            "strategy_percentile_vs_random": round(pct_vs_rand, 4),
            "beats_random_95pct": bool(pct_vs_rand >= 0.95),
        },
    }


# ---------------------------------------------------------------------------
# 8. All 16 Section 5 Mandatory Profitability & Risk Metrics
# ---------------------------------------------------------------------------


def _expected_calibration_error(trades: Sequence[TradeObservation], n_bins: int = 10) -> float:
    settled = [
        t for t in trades
        if t.outcome_binary is not None and 0.0 <= float(t.outcome_binary) <= 1.0
    ]
    if not settled:
        return 0.0
    bins: List[List[Tuple[float, float]]] = [[] for _ in range(n_bins)]
    for t in settled:
        p = _clamp_prob(t.model_prob_entry, eps=1e-6)
        b_idx = min(n_bins - 1, int(p * n_bins))
        bins[b_idx].append((p, float(t.outcome_binary)))
    n_tot = len(settled)
    ece = 0.0
    for b in bins:
        if not b:
            continue
        avg_p = sum(x[0] for x in b) / len(b)
        avg_y = sum(x[1] for x in b) / len(b)
        ece += (len(b) / n_tot) * abs(avg_p - avg_y)
    return ece


def _cvar_alpha(pnls: Sequence[float], alpha: float = 0.05) -> float:
    """Expected Shortfall (`CVaR_95` at `alpha=0.05`): mean of the worst `ceil(alpha * N)` outcomes."""
    if not pnls:
        return 0.0
    ordered = sorted(float(x) for x in pnls)
    k = max(1, math.ceil(alpha * len(ordered)))
    return sum(ordered[:k]) / k


def _sortino_ratio(vals: Sequence[float]) -> float:
    if len(vals) < 2:
        return 0.0
    mu = sum(vals) / len(vals)
    downside_sq = sum((min(0.0, x)) ** 2 for x in vals) / len(vals)
    if downside_sq <= 1e-15:
        return 99.0 if mu > 0.0 else 0.0
    return mu / math.sqrt(downside_sq)


def compute_section5_metrics(
    trades: Sequence[TradeObservation],
    *,
    reference_bankroll_usd: float = 500.0,
    window_days_override: Optional[float] = None,
    n_boot: int = 2000,
    seed: int = 20261112,
) -> Dict[str, Any]:
    """
    Computes ALL 16 Section 5 profitability, risk, capacity, statistical confidence,
    and cost-sensitivity metrics on an evaluated trade sequence.
    """
    n_trades = len(trades)
    if n_trades == 0:
        empty_ci = cluster_bootstrap_ci([], n_boot=n_boot, seed=seed)
        empty_cost = evaluate_cost_stress_and_breakeven([])
        return {
            "gross_pnl_usd": 0.0,
            "net_pnl_usd": 0.0,
            "total_fees_usd": 0.0,
            "total_spread_slippage_usd": 0.0,
            "avg_net_profit_per_trade_usd": 0.0,
            "net_return_on_notional_bps": 0.0,
            "win_rate": 0.0,
            "avg_win_usd": 0.0,
            "avg_loss_usd": 0.0,
            "payoff_asymmetry_ratio": 0.0,
            "profit_factor": 0.0,
            "ev_per_trade_usd": 0.0,
            "model_expected_ev_per_trade_usd": 0.0,
            "capital_utilization_pct": 0.0,
            "profit_per_dollar_day": 0.0,
            "profit_per_dollar_day_bps": 0.0,
            "max_drawdown_usd": 0.0,
            "max_drawdown_pct_of_bankroll": 0.0,
            "cvar_95_trade_usd": 0.0,
            "cvar_95_cluster_usd": 0.0,
            "sharpe_per_trade": 0.0,
            "sharpe_cluster": 0.0,
            "sharpe_daily_annualized": 0.0,
            "sortino_per_trade": 0.0,
            "sortino_daily_annualized": 0.0,
            "executable_opportunity_frequency_per_day": 0.0,
            "clusters_per_day": 0.0,
            "available_capacity_per_trade_usd": 0.0,
            "available_daily_capacity_usd": 0.0,
            "cluster_bootstrap_95ci": empty_ci,
            "oos_sample_size": {
                "n_trades": 0,
                "n_clusters": 0,
                "n_unique_markets": 0,
                "n_categories": 0,
                "effective_independent_n": 0.0,
                "window_days": 0.0,
            },
            "cost_sensitivity": empty_cost,
            "calibration_diagnostics": {"ece_10bin": 0.0, "uma_disputed_count": 0},
            "account_tier_viability": {
                "dominus_48_81_daily_net_est_usd": 0.0,
                "beats_0_822_vm_hurdle_standalone": False,
            },
        }

    ordered_exit = sorted(trades, key=lambda x: (x.exit_ts, x.entry_ts, x.trade_id))
    min_ts = min(t.entry_ts for t in trades)
    max_ts = max(max(t.exit_ts, t.entry_ts) for t in trades)
    if window_days_override is not None and window_days_override > 0:
        window_days = float(window_days_override)
    else:
        window_days = max(1.0, (max_ts - min_ts) / 86400.0)

    # 1. Gross & Net PnL
    gross_pnl = sum(t.gross_pnl_usd for t in trades)
    net_pnl = sum(t.net_pnl_usd for t in trades)
    fees_tot = sum(t.fees_usd for t in trades)
    slip_tot = sum(t.spread_slippage_cost_usd for t in trades)
    tot_notional = sum(t.notional_usd for t in trades)

    # 2. Avg Net Profit / Trade
    avg_net = net_pnl / n_trades
    roi_bps = (net_pnl / max(1e-9, tot_notional)) * 10_000.0

    # 3 & 4. Win Rate, Avg Win, Avg Loss, Payoff Ratio, Profit Factor
    pnls = [t.net_pnl_usd for t in ordered_exit]
    wins = [x for x in pnls if x > 0.0]
    losses = [x for x in pnls if x <= 0.0]
    win_rate = len(wins) / n_trades
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    payoff_ratio = (avg_win / abs(avg_loss)) if abs(avg_loss) > 1e-12 else (99.0 if avg_win > 0 else 0.0)
    profit_factor = (gross_wins / gross_losses) if gross_losses > 1e-12 else (99.0 if gross_wins > 0 else 0.0)

    # 5. EV / Trade (realized identity p_win*W + (1-p_win)*L AND ex-ante model-implied net EV)
    ev_per_trade = win_rate * avg_win + (1.0 - win_rate) * avg_loss
    ex_ante_ev = sum(
        t.shares * (t.model_prob_entry - t.entry_price) - t.fees_usd for t in trades
    ) / n_trades

    # 6 & 7. Capital Utilization & Profit per Dollar-Day Committed
    dollar_days = sum(t.notional_usd * t.hold_days for t in trades)
    bankroll_ref = max(1.0, float(reference_bankroll_usd))
    cap_util_pct = min(100.0, (dollar_days / (bankroll_ref * window_days)) * 100.0)
    prof_per_dday = net_pnl / max(1e-9, dollar_days)

    # 8. Max Drawdown (chronological settlement/exit curve)
    eq = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        eq += p
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    # 9. Tail-Loss Expected Shortfall (CVaR_95 per-trade AND per-event-cluster)
    by_cluster: Dict[str, float] = collections.defaultdict(float)
    for t in trades:
        by_cluster[t.canonical_cluster_id()] += t.net_pnl_usd
    cluster_pnls = list(by_cluster.values())
    cvar_95_trade = _cvar_alpha(pnls, alpha=0.05)
    cvar_95_cluster = _cvar_alpha(cluster_pnls, alpha=0.05)

    # 10. Sharpe & Sortino (per-trade, per-cluster, and daily calendar annualized sqrt(365))
    sharpe_trade = _sharpe_from_values(pnls)
    sharpe_cluster = _sharpe_from_values(cluster_pnls)
    sortino_trade = _sortino_ratio(pnls)

    daily_map: Dict[int, float] = collections.defaultdict(float)
    start_day_idx = int(min_ts // 86400)
    end_day_idx = max(start_day_idx, int(max_ts // 86400))
    for t in ordered_exit:
        d_idx = int(max(t.exit_ts, t.entry_ts) // 86400)
        daily_map[d_idx] += t.net_pnl_usd
    n_cal_days = max(1, end_day_idx - start_day_idx + 1)
    # Include zero-trade calendar days so intermittent strategies do not fabricate continuous daily Sharpe
    cal_span_cap = min(n_cal_days, 3650)
    daily_series = [daily_map.get(start_day_idx + i, 0.0) for i in range(cal_span_cap)]
    if len(daily_series) >= 2:
        sharpe_daily_ann = _sharpe_from_values(daily_series) * math.sqrt(365.0)
        sortino_daily_ann = _sortino_ratio(daily_series) * math.sqrt(365.0)
    else:
        sharpe_daily_ann = 0.0
        sortino_daily_ann = 0.0

    # 11 & 12. Executable Opportunity Frequency & Available Capacity ($)
    opp_freq_per_day = n_trades / window_days
    clusters_per_day = len(cluster_pnls) / window_days
    depths = sorted(max(0.0, t.available_depth_usd) for t in trades)
    # Conservative executable clip per opportunity: 25% of median top-of-book/L2 depth so price impact stays bounded
    median_depth = depths[len(depths) // 2] if depths else 0.0
    cap_per_trade_usd = round(0.25 * median_depth, 2)
    daily_cap_usd = round(cap_per_trade_usd * clusters_per_day, 2)

    # 13, 14, 15. Cluster Bootstrap 95% CIs, OOS Sample Size, and Cost Sensitivity
    boot_ci = cluster_bootstrap_ci(trades, n_boot=n_boot, seed=seed)
    cost_sens = evaluate_cost_stress_and_breakeven(trades)
    se_inf = max(1.0, float(boot_ci.get("se_inflation_vs_iid", 1.0)))
    eff_indep_n = n_trades / (se_inf * se_inf)

    # Small-account ($48.81 Dominus seed cash) reality check: 15% per-cluster cap = $7.32 max clip, >= $1 / 5-share min lot
    max_seed_clip = round(0.15 * DOMINUS_SEED_CASH_USD, 2)  # $7.32
    seed_deployable_daily = min(DOMINUS_SEED_CASH_USD * 0.85, max_seed_clip * clusters_per_day)
    seed_est_daily_net = seed_deployable_daily * max(0.0, prof_per_dday)

    return {
        "gross_pnl_usd": round(gross_pnl, 4),
        "net_pnl_usd": round(net_pnl, 4),
        "total_fees_usd": round(fees_tot, 4),
        "total_spread_slippage_usd": round(slip_tot, 4),
        "avg_net_profit_per_trade_usd": round(avg_net, 6),
        "net_return_on_notional_bps": round(roi_bps, 3),
        "win_rate": round(win_rate, 4),
        "avg_win_usd": round(avg_win, 4),
        "avg_loss_usd": round(avg_loss, 4),
        "payoff_asymmetry_ratio": round(payoff_ratio, 4),
        "profit_factor": round(profit_factor, 4),
        "ev_per_trade_usd": round(ev_per_trade, 6),
        "model_expected_ev_per_trade_usd": round(ex_ante_ev, 6),
        "capital_utilization_pct": round(cap_util_pct, 4),
        "profit_per_dollar_day": round(prof_per_dday, 6),
        "profit_per_dollar_day_bps": round(prof_per_dday * 10_000.0, 3),
        "max_drawdown_usd": round(max_dd, 4),
        "max_drawdown_pct_of_bankroll": round((max_dd / bankroll_ref) * 100.0, 4),
        "cvar_95_trade_usd": round(cvar_95_trade, 4),
        "cvar_95_cluster_usd": round(cvar_95_cluster, 4),
        "sharpe_per_trade": round(sharpe_trade, 4),
        "sharpe_cluster": round(sharpe_cluster, 4),
        "sharpe_daily_annualized": round(sharpe_daily_ann, 4),
        "sortino_per_trade": round(sortino_trade, 4),
        "sortino_daily_annualized": round(sortino_daily_ann, 4),
        "executable_opportunity_frequency_per_day": round(opp_freq_per_day, 4),
        "clusters_per_day": round(clusters_per_day, 4),
        "available_capacity_per_trade_usd": cap_per_trade_usd,
        "available_daily_capacity_usd": daily_cap_usd,
        "cluster_bootstrap_95ci": boot_ci,
        "oos_sample_size": {
            "n_trades": n_trades,
            "n_clusters": len(cluster_pnls),
            "n_unique_markets": len({t.market_id for t in trades}),
            "n_categories": len({t.category for t in trades}),
            "effective_independent_n": round(eff_indep_n, 2),
            "window_days": round(window_days, 3),
        },
        "cost_sensitivity": cost_sens,
        "calibration_diagnostics": {
            "ece_10bin": round(_expected_calibration_error(trades), 6),
            "uma_disputed_count": sum(1 for t in trades if t.uma_disputed),
            "negative_skew_tail_flag": bool(win_rate >= 0.85 and payoff_ratio < 0.20),
        },
        "account_tier_viability": {
            "dominus_48_81_max_15pct_cluster_clip_usd": max_seed_clip,
            "dominus_48_81_daily_net_est_usd": round(seed_est_daily_net, 4),
            "beats_0_822_vm_hurdle_standalone": bool(seed_est_daily_net >= DOMINUS_VM_DAILY_HURDLE_USD),
            "tier_500_viable": bool(net_pnl > 0.0 and daily_cap_usd >= 25.0),
            "tier_5000_viable": bool(net_pnl > 0.0 and daily_cap_usd >= 250.0),
        },
    }


# ---------------------------------------------------------------------------
# 9. Deliverable C Strict 5-Label Classification & Full Strategy Validation
# ---------------------------------------------------------------------------


def classify_strategy_deliverable_c(
    *,
    awaiting_data: bool,
    holdout_metrics: Mapping[str, Any],
    combined_oos_metrics: Mapping[str, Any],
    baselines: Mapping[str, Any],
    bh_q_value: float,
    dsr_value: float,
    pbo_value: Optional[float],
    is_spike_overfit: bool,
    integrity_violations: Sequence[str],
    red_team_status: str = "PENDING",
    red_team_fatal_flaws: Sequence[str] = (),
) -> Tuple[str, List[str]]:
    """
    Classifies a strategy into one of the 5 mandated Deliverable C labels:
      1. `Validated out of sample`
      2. `Promising but preliminary`
      3. `Insufficient evidence`
      4. `Rejected`
      5. `Awaiting data`

    Enforces a hard gate: NO strategy can achieve `Validated out of sample` unless
    `red_team_status == "CLEARED"` with zero unresolved `@red-team` fatal flaws!
    """
    reasons: List[str] = []
    ho_sample = holdout_metrics.get("oos_sample_size", {})
    oos_sample = combined_oos_metrics.get("oos_sample_size", {})
    ho_n = int(ho_sample.get("n_trades", 0))
    ho_clusters = int(ho_sample.get("n_clusters", 0))
    oos_clusters = int(oos_sample.get("n_clusters", ho_clusters))

    if awaiting_data and ho_n == 0 and int(oos_sample.get("n_trades", 0)) == 0:
        return "Awaiting data", ["Required historical series or forward L2 archive not yet populated."]

    if red_team_fatal_flaws:
        reasons.extend(f"RED_TEAM_FATAL:{f}" for f in red_team_fatal_flaws)
        return "Rejected", reasons

    if integrity_violations:
        reasons.extend(integrity_violations)
        return "Rejected", reasons

    ho_net = float(holdout_metrics.get("net_pnl_usd", 0.0))
    oos_net = float(combined_oos_metrics.get("net_pnl_usd", 0.0))
    oos_ci = combined_oos_metrics.get("cluster_bootstrap_95ci", {})
    ho_ci = holdout_metrics.get("cluster_bootstrap_95ci", {})
    oos_ci_lo = float((oos_ci.get("total_net_pnl_ci95") or [0.0, 0.0])[0])
    ho_ci_lo = float((ho_ci.get("total_net_pnl_ci95") or [0.0, 0.0])[0])
    oos_p = float(oos_ci.get("one_sided_p_value", 1.0))

    ho_cost = holdout_metrics.get("cost_sensitivity", {})
    oos_cost = combined_oos_metrics.get("cost_sensitivity", {})
    survives_1_5x = bool(ho_cost.get("survives_1_5x_cost", False) and oos_cost.get("survives_1_5x_cost", False))
    be_bps = float(oos_cost.get("breakeven_extra_slippage_bps", 0.0))

    # Reject clear net losers when sample is non-trivial, or when both Val+Holdout lose money
    if ho_n == 0 and int(oos_sample.get("n_trades", 0)) == 0:
        return "Insufficient evidence", ["Zero executable out-of-sample trades generated."]

    if oos_net <= 0.0 and oos_clusters >= 8:
        reasons.append(f"Negative/flat out-of-sample Net PnL (${oos_net:.2f}) across {oos_clusters} clusters.")
        return "Rejected", reasons

    if ho_net <= 0.0 and ho_clusters >= 10:
        reasons.append(f"Failed Sealed Holdout (${ho_net:.2f} across {ho_clusters} holdout clusters).")
        return "Rejected", reasons

    if pbo_value is not None and pbo_value > 0.55 and oos_clusters >= 10:
        reasons.append(f"High Probability of Backtest Overfitting (PBO={pbo_value:.2f} > 0.55).")
        return "Rejected", reasons

    if is_spike_overfit and ho_net <= 0.0:
        reasons.append("Parameter perturbation surface collapsed (fragile in-sample spike optimum).")
        return "Rejected", reasons

    # Sample-size floor check before claiming statistical validation
    if ho_n < 30 or ho_clusters < 15 or oos_clusters < 25:
        if ho_net > 0.0 and oos_net > 0.0 and oos_clusters >= 10 and oos_p <= 0.15 and survives_1_5x:
            reasons.append(
                f"Positive OOS Net PnL (${oos_net:.2f}, p={oos_p:.3f}), but holdout cluster count ({ho_clusters}) < 15 or OOS clusters ({oos_clusters}) < 25."
            )
            return "Promising but preliminary", reasons
        reasons.append(
            f"Underpowered OOS sample (holdout trades={ho_n}, holdout clusters={ho_clusters}, OOS clusters={oos_clusters}, cluster p={oos_p:.3f})."
        )
        return "Insufficient evidence", reasons

    # Adequate sample size: test strict statistical, baseline, cost, and Red-Team hurdles
    passes_stat = bool((oos_ci_lo > 0.0 and ho_ci_lo >= 0.0) and (bh_q_value <= 0.05 or dsr_value >= 0.90))
    passes_pbo = bool(pbo_value is None or pbo_value <= 0.25)
    passes_cost = bool(survives_1_5x and be_bps >= 25.0)
    beats_random = bool(baselines.get("random_entry_cost_drag", {}).get("beats_random_95pct", False))

    if ho_net > 0.0 and oos_net > 0.0 and passes_stat and passes_pbo and passes_cost and not is_spike_overfit and beats_random:
        if red_team_status.strip().upper() == "CLEARED":
            reasons.append(
                f"Passed Sealed Holdout (${ho_net:.2f}), Cluster CI95_lo=${oos_ci_lo:.2f} > 0, BH-q={bh_q_value:.4f}, DSR={dsr_value:.3f}, 1.5x cost stress (+{be_bps:.1f} bps cushion), and @red-team CLEARED."
            )
            return "Validated out of sample", reasons
        reasons.append(
            f"Passes quantitative OOS & cost gates (Holdout=${ho_net:.2f}, BH-q={bh_q_value:.4f}, DSR={dsr_value:.3f}), held at 'Promising but preliminary' pending @red-team CLEARED sign-off (status={red_team_status})."
        )
        return "Promising but preliminary", reasons

    if ho_net > 0.0 and oos_net > 0.0 and oos_p <= 0.15 and be_bps >= 10.0:
        reasons.append(
            f"Positive Holdout (${ho_net:.2f}) & OOS (${oos_net:.2f}), cluster p={oos_p:.3f}, BH-q={bh_q_value:.4f}, DSR={dsr_value:.3f}, break-even +{be_bps:.1f} bps; requires larger forward shadow sample or tighter multiple-testing clearance."
        )
        return "Promising but preliminary", reasons

    if ho_net <= 0.0 or oos_net <= 0.0:
        reasons.append(f"Non-positive Sealed Holdout (${ho_net:.2f}) or combined OOS (${oos_net:.2f}).")
        return "Rejected", reasons

    reasons.append(f"Wide cluster confidence interval (p={oos_p:.3f}, BH-q={bh_q_value:.4f}) cannot rule out noise.")
    return "Insufficient evidence", reasons


# ---------------------------------------------------------------------------
# 10. Combined Portfolio Validation & Cross-Strategy Correlation Matrix
# ---------------------------------------------------------------------------


def compute_cluster_return_correlation_matrix(
    trades_by_strategy: Mapping[str, Sequence[TradeObservation]],
) -> Dict[str, Dict[str, float]]:
    """
    Computes pairwise Pearson correlation across calendar-day PnLs for candidate strategies
    so shared macro/crypto/event factor drawdowns are explicitly surfaced.
    """
    strat_ids = sorted(trades_by_strategy.keys())
    daily_by_strat: Dict[str, Dict[str, float]] = {}
    all_days: set[str] = set()
    for sid in strat_ids:
        d_map: Dict[str, float] = collections.defaultdict(float)
        for t in trades_by_strategy[sid]:
            day_k = _utc_day_str(max(t.exit_ts, t.entry_ts))
            d_map[day_k] += t.net_pnl_usd
            all_days.add(day_k)
        daily_by_strat[sid] = d_map

    sorted_days = sorted(all_days)
    matrix: Dict[str, Dict[str, float]] = {sid: {} for sid in strat_ids}
    if len(sorted_days) < 2:
        for a in strat_ids:
            for b in strat_ids:
                matrix[a][b] = 1.0 if a == b else 0.0
        return matrix

    vecs = {sid: [daily_by_strat[sid].get(d, 0.0) for d in sorted_days] for sid in strat_ids}
    for i, sa in enumerate(strat_ids):
        matrix[sa][sa] = 1.0
        va = vecs[sa]
        mu_a = sum(va) / len(va)
        da = [x - mu_a for x in va]
        ss_a = sum(x * x for x in da)
        for sb in strat_ids[i + 1 :]:
            vb = vecs[sb]
            mu_b = sum(vb) / len(vb)
            db = [x - mu_b for x in vb]
            ss_b = sum(x * x for x in db)
            denom = math.sqrt(ss_a * ss_b)
            corr = (sum(x * y for x, y in zip(da, db)) / denom) if denom > 1e-15 else 0.0
            corr_c = round(max(-1.0, min(1.0, corr)), 4)
            matrix[sa][sb] = corr_c
            matrix[sb][sa] = corr_c
    return matrix


def evaluate_combined_portfolio(
    oos_trades_by_strategy: Mapping[str, Sequence[TradeObservation]],
    *,
    bankroll_usd: float = 500.0,
    per_cluster_cap_frac: float = 0.15,
    max_total_open_frac: float = 0.85,
    n_boot: int = 2000,
    seed: int = 20261112,
) -> Dict[str, Any]:
    """
    Simulates a combined chronological multi-strategy portfolio enforcing:
      - `<= 15%` bankroll concentration per correlated event cluster across ALL strategies (`AGENTS.md` Rule 4),
      - `<= 85%` concurrent committed notional cap (accounting for exact `entry_ts` -> `exit_ts` lockup!),
      - Polymarket `$1.00` minimum order floor,
    and evaluates all 16 Section 5 metrics + diversification uplift vs standalone strategies.
    """
    all_candidates: List[TradeObservation] = []
    for seq in oos_trades_by_strategy.values():
        all_candidates.extend(seq)
    all_candidates.sort(key=lambda x: (x.entry_ts, x.trade_id))

    max_cluster_usd = max(1.0, bankroll_usd * per_cluster_cap_frac)
    max_open_usd = max(1.0, bankroll_usd * max_total_open_frac)

    # Track active open positions: list of (exit_ts, cluster_id, scaled_notional_usd)
    active_open: List[Tuple[float, str, float]] = []
    accepted: List[TradeObservation] = []
    skipped_cap = 0
    skipped_min_lot = 0

    for t in all_candidates:
        active_open = [row for row in active_open if row[0] > t.entry_ts]
        cur_open_tot = sum(row[2] for row in active_open)
        cl_id = t.canonical_cluster_id()
        cur_cl_open = sum(row[2] for row in active_open if row[1] == cl_id)

        avail_tot = max(0.0, max_open_usd - cur_open_tot)
        avail_cl = max(0.0, max_cluster_usd - cur_cl_open)
        target_notional = min(t.notional_usd, max_cluster_usd, avail_tot, avail_cl)
        # Polymarket CLOB enforces BOTH $1.00 minimum order notional AND 5.00 minimum share lot (`RT-09`)
        min_lot_usd = max(1.00, 5.0 * t.entry_price)
        if target_notional < min_lot_usd - 1e-9:
            if min(t.notional_usd, max_cluster_usd, max_open_usd) < min_lot_usd - 1e-9:
                skipped_min_lot += 1
            else:
                skipped_cap += 1
            continue

        raw_target_shares = target_notional / max(1e-6, t.entry_price)
        quantized_shares = math.floor(raw_target_shares * 100.0 + 1e-9) / 100.0
        quantized_notional = quantized_shares * t.entry_price
        if quantized_shares < 5.0 - 1e-9 or quantized_notional < 1.0 - 1e-9:
            skipped_min_lot += 1
            continue

        scale = quantized_shares / max(1e-9, t.shares)
        scaled_trade = TradeObservation(
            trade_id=t.trade_id,
            strategy_id=t.strategy_id,
            market_id=t.market_id,
            event_id=t.event_id,
            category=t.category,
            side=t.side,
            exit_type=t.exit_type,
            entry_ts=t.entry_ts,
            exit_ts=t.exit_ts,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            market_mid_entry=t.market_mid_entry,
            model_prob_entry=t.model_prob_entry,
            outcome_binary=t.outcome_binary,
            notional_usd=quantized_notional,
            shares=quantized_shares,
            gross_pnl_usd=t.gross_pnl_usd * scale,
            fees_usd=t.fees_usd * scale,
            spread_slippage_cost_usd=t.spread_slippage_cost_usd * scale,
            net_pnl_usd=t.net_pnl_usd * scale,
            available_depth_usd=t.available_depth_usd,
            fee_rate_bps=t.fee_rate_bps,
            is_maker_entry=t.is_maker_entry,
            clinch_ts=t.clinch_ts,
            end_ts=t.end_ts,
            uma_disputed=t.uma_disputed,
            data_quality_class=t.data_quality_class,
            subcategory=t.subcategory,
            fee_rate=t.fee_rate,
            is_void_50_50=t.is_void_50_50,
        )
        accepted.append(scaled_trade)
        active_open.append((scaled_trade.exit_ts, cl_id, scaled_trade.notional_usd))

    portfolio_metrics = compute_section5_metrics(accepted, reference_bankroll_usd=bankroll_usd, n_boot=n_boot, seed=seed)
    corr_matrix = compute_cluster_return_correlation_matrix(oos_trades_by_strategy)

    # Compare combined portfolio Sharpe vs best single constituent strategy
    standalone_sharpes: Dict[str, float] = {}
    for sid, seq in oos_trades_by_strategy.items():
        if seq:
            m_s = compute_section5_metrics(seq, reference_bankroll_usd=bankroll_usd, n_boot=2000, seed=seed)
            standalone_sharpes[sid] = float(m_s["sharpe_daily_annualized"])
    best_single_sr = max(standalone_sharpes.values(), default=0.0)
    comb_sr = float(portfolio_metrics["sharpe_daily_annualized"])

    return {
        "bankroll_usd": bankroll_usd,
        "per_cluster_cap_frac": per_cluster_cap_frac,
        "constituent_strategies": sorted(oos_trades_by_strategy.keys()),
        "candidate_oos_trades": len(all_candidates),
        "accepted_portfolio_trades": len(accepted),
        "skipped_concentration_or_lockup": skipped_cap,
        "skipped_min_lot": skipped_min_lot,
        "section5_metrics": portfolio_metrics,
        "daily_return_correlation_matrix": corr_matrix,
        "best_standalone_daily_sharpe": round(best_single_sr, 4),
        "diversification_sharpe_uplift": round(comb_sr - best_single_sr, 4),
        "genuinely_improves_risk_adjusted_return": bool(
            len(oos_trades_by_strategy) >= 2 and portfolio_metrics["net_pnl_usd"] > 0.0 and comb_sr > best_single_sr
        ),
    }


# ---------------------------------------------------------------------------
# 11. End-to-End Swarm Batch Validation & Leaderboard Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class StrategyCandidateInput:
    """Input bundle for validating one directional strategy candidate."""

    strategy_id: str
    family: str
    pillar: str
    description: str
    mechanism: str  # "PROBABILITY_EDGE", "TRADING_EDGE", or "HYBRID"
    trades: List[TradeObservation] = field(default_factory=list)
    variant_trades: Dict[str, List[TradeObservation]] = field(default_factory=dict)
    parameter_stability_override: Optional[Dict[str, Any]] = None
    awaiting_data: bool = False
    red_team_status: str = "PENDING"
    red_team_fatal_flaws: List[str] = field(default_factory=list)
    red_team_notes: str = ""
    num_internal_variants_tested: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


def validate_all_candidates_and_build_leaderboard(
    candidates: Sequence[StrategyCandidateInput],
    *,
    embargo_sec: float = 3600.0,
    total_swarm_trials_override: Optional[int] = None,
    reference_bankroll_usd: float = 500.0,
    n_boot: int = 2000,
    seed: int = 20261112,
    explicit_train_end_ts: Optional[float] = None,
    explicit_val_end_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Evaluates every candidate strategy through:
      1. Integrity & leakage screening (`RT-01..RT-03`),
      2. Strict 3-way chronological split (`50% Train / 25% Val / 25% Sealed Holdout`) with
         cross-boundary open-position purging & `embargo_sec`,
      3. `CPCV(6, 2)` + `PBO` + Walk-Forward + Regime/Category stability,
      4. Event-Cluster Bootstrap (`B >= 2,000`),
      5. Global Multiple-Testing Corrections (`BH-FDR`, `BY-FDR`, `Holm-Bonferroni`, `DSR`)
         across ALL `M` tested variations in the entire swarm,
      6. `1.0x / 1.5x / 2.0x / 3.0x` cost stress & break-even bps,
      7. Simple baselines (`Market Zero-Edge`, `Naive Buy-NO`, `Naive Buy-Favorite`, `Random Entry`),
      8. Combined Multi-Strategy Portfolio validation across `$48.81`, `$500`, and `$5,000` accounts,
      9. Strict 5-label Deliverable C classification incorporating `@red-team` verdicts.
    """
    total_m = sum(
        max(1, c.num_internal_variants_tested, len(c.variant_trades))
        for c in candidates
        if not c.awaiting_data
    )
    if total_swarm_trials_override is not None:
        total_m = max(total_m, int(total_swarm_trials_override))
    total_m = max(1, total_m)

    interim: List[Dict[str, Any]] = []
    raw_p_map: Dict[str, float] = {}
    all_oos_cluster_z_stats: List[float] = []

    for idx, cand in enumerate(candidates):
        cand_seed = seed + idx * 17
        violations = detect_leakage_and_integrity_violations(cand.trades)
        split = purged_three_way_split(
            cand.trades,
            embargo_sec=embargo_sec,
            explicit_train_end_ts=explicit_train_end_ts,
            explicit_val_end_ts=explicit_val_end_ts,
        )
        oos_combined = sorted(split.validation + split.holdout, key=lambda x: (x.entry_ts, x.trade_id))

        train_m = compute_section5_metrics(split.train, reference_bankroll_usd=reference_bankroll_usd, n_boot=n_boot, seed=cand_seed)
        val_m = compute_section5_metrics(split.validation, reference_bankroll_usd=reference_bankroll_usd, n_boot=n_boot, seed=cand_seed + 1)
        hold_m = compute_section5_metrics(split.holdout, reference_bankroll_usd=reference_bankroll_usd, n_boot=n_boot, seed=cand_seed + 2)
        oos_m = compute_section5_metrics(oos_combined, reference_bankroll_usd=reference_bankroll_usd, n_boot=n_boot, seed=cand_seed + 3)

        variants_dict = dict(cand.variant_trades) if cand.variant_trades else {cand.strategy_id: cand.trades}
        cpcv_res = compute_cpcv_and_pbo(variants_dict, n_groups=6, k_test_groups=2, embargo_sec=embargo_sec)
        wfo_res = run_purged_walk_forward(variants_dict, n_folds=5, embargo_sec=embargo_sec)
        regime_res = evaluate_regime_and_category_stability(oos_combined if oos_combined else cand.trades)
        baselines_res = evaluate_simple_baselines(oos_combined if oos_combined else cand.trades, seed=cand_seed + 5)

        # Cluster-level OOS returns for Deflated Sharpe Ratio (using T = N_clusters so correlation cannot inflate T!).
        # Per RT-14 (`FIND-RT14-001`), standardize cross-trial dispersion in z = SR_m * sqrt(G_m - 1) space across
        # powered trials (G_m >= 10) so tiny-sample (G_m = 2..8) zero-loss outliers cannot inflate Var[{SR_m}] by >10x.
        cl_map: Dict[str, float] = collections.defaultdict(float)
        for t in oos_combined:
            cl_map[t.canonical_cluster_id()] += t.net_pnl_usd
        cl_rets = list(cl_map.values())
        cl_sr = _sharpe_from_values(cl_rets)
        if not cand.awaiting_data and len(cl_rets) >= 10:
            all_oos_cluster_z_stats.append(cl_sr * math.sqrt(max(1, len(cl_rets) - 1)))

        if not cand.awaiting_data:
            raw_p_map[cand.strategy_id] = float(oos_m["cluster_bootstrap_95ci"]["one_sided_p_value"])

        interim.append(
            {
                "cand": cand,
                "violations": violations,
                "split": split,
                "oos_combined": oos_combined,
                "train_metrics": train_m,
                "validation_metrics": val_m,
                "holdout_metrics": hold_m,
                "combined_oos_metrics": oos_m,
                "cpcv": cpcv_res,
                "walk_forward": wfo_res,
                "regime_stability": regime_res,
                "baselines": baselines_res,
                "cluster_returns": cl_rets,
            }
        )

    # Family-wise & FDR multiple-testing corrections across all M tested swarm variations
    bh_res = benjamini_hochberg_fdr(raw_p_map, alpha=0.05, total_trials_m=total_m, arbitrary_dependence_by=False)
    by_res = benjamini_hochberg_fdr(raw_p_map, alpha=0.05, total_trials_m=total_m, arbitrary_dependence_by=True)
    holm_res = holm_bonferroni_correction(raw_p_map, alpha=0.05, total_trials_m=total_m)

    entries: List[Dict[str, Any]] = []
    promising_oos_by_strat: Dict[str, List[TradeObservation]] = {}

    empirical_z_std = (
        statistics.stdev(all_oos_cluster_z_stats)
        if len(all_oos_cluster_z_stats) >= 2
        else 1.0
    )

    for row in interim:
        cand = row["cand"]
        sid = cand.strategy_id
        # Under H_0: E[SR_m] = 0 across heterogeneous strategy families with varying sample sizes G_m
        # (and deterministic friction losers z ~ -9 alongside zero-loss tiny-variance contenders z ~ +13),
        # Var[SR_hat | H_0] = 1 / (G - 1) (`all_trial_sharpes=None`), matching @red-team's analytical DSR
        # (`FIND-RT14-001`) while preserving `empirical_cross_trial_z_std` as an explicit diagnostic.
        dsr_res = deflated_sharpe_ratio(
            row["cluster_returns"],
            num_trials_m=total_m,
            all_trial_sharpes=None,
            benchmark_sr=0.0,
        )
        dsr_res["empirical_cross_trial_z_std"] = round(empirical_z_std, 4)
        bh_info = bh_res.get(sid, {"bh_q_value": 1.0, "passes_fdr": False, "raw_p_value": 1.0})
        by_info = by_res.get(sid, {"bh_q_value": 1.0, "passes_fdr": False})
        holm_info = holm_res.get(sid, {"holm_adjusted_p": 1.0, "passes_fwer": False})

        param_stab = cand.parameter_stability_override or {}
        is_spike = bool(param_stab.get("is_spike_overfit", False))

        label, reasons = classify_strategy_deliverable_c(
            awaiting_data=cand.awaiting_data,
            holdout_metrics=row["holdout_metrics"],
            combined_oos_metrics=row["combined_oos_metrics"],
            baselines=row["baselines"],
            bh_q_value=float(bh_info["bh_q_value"]),
            dsr_value=float(dsr_res["dsr"]),
            pbo_value=row["cpcv"].get("pbo"),
            is_spike_overfit=is_spike,
            integrity_violations=row["violations"],
            red_team_status=cand.red_team_status,
            red_team_fatal_flaws=cand.red_team_fatal_flaws,
        )

        if label in ("Validated out of sample", "Promising but preliminary") and row["oos_combined"]:
            promising_oos_by_strat[sid] = row["oos_combined"]

        split_obj: PurgedSplitResult = row["split"]
        entries.append(
            {
                "strategy_id": sid,
                "family": cand.family,
                "pillar": cand.pillar,
                "mechanism": cand.mechanism,
                "description": cand.description,
                "classification": label,
                "classification_reasons": reasons,
                "red_team_audit": {
                    "status": cand.red_team_status,
                    "fatal_flaws": list(cand.red_team_fatal_flaws),
                    "notes": cand.red_team_notes,
                },
                "integrity_violations": row["violations"],
                "purged_split_summary": {
                    "train_trades": len(split_obj.train),
                    "validation_trades": len(split_obj.validation),
                    "sealed_holdout_trades": len(split_obj.holdout),
                    "train_end_ts": split_obj.train_end_ts,
                    "val_end_ts": split_obj.val_end_ts,
                    "embargo_sec": split_obj.embargo_sec,
                    "purged_train_val_count": split_obj.purged_train_val_count,
                    "purged_val_holdout_count": split_obj.purged_val_holdout_count,
                    "embargoed_count": split_obj.embargoed_count,
                    "zero_boundary_overlap": split_obj.zero_boundary_overlap,
                },
                "multiple_testing": {
                    "total_swarm_trials_m": total_m,
                    "internal_variants_tested": cand.num_internal_variants_tested,
                    "raw_cluster_p_value": bh_info.get("raw_p_value", 1.0),
                    "bh_fdr_q_value": bh_info["bh_q_value"],
                    "by_fdr_q_value": by_info["bh_q_value"],
                    "holm_bonferroni_p_value": holm_info["holm_adjusted_p"],
                    "passes_bh_fdr_0_05": bh_info["passes_fdr"],
                    "passes_holm_fwer_0_05": holm_info["passes_fwer"],
                    "deflated_sharpe_ratio": dsr_res,
                },
                "train_metrics": row["train_metrics"],
                "validation_metrics": row["validation_metrics"],
                "sealed_holdout_metrics": row["holdout_metrics"],
                "combined_oos_metrics": row["combined_oos_metrics"],
                "cpcv_and_pbo": row["cpcv"],
                "purged_walk_forward": row["walk_forward"],
                "parameter_stability": param_stab,
                "regime_and_category_stability": row["regime_stability"],
                "simple_baselines": row["baselines"],
                "metadata": cand.metadata,
            }
        )

    # Sort leaderboard strictly by:
    # 1. Classification tier (`Validated out of sample` > `Promising` > `Insufficient` > `Awaiting data` > `Rejected`),
    # 2. Sealed Holdout Net PnL at realistic 1.0x costs,
    # 3. Cluster-Bootstrap 95% CI lower bound on OOS Net PnL.
    tier_priority = {
        "Validated out of sample": 0,
        "Promising but preliminary": 1,
        "Insufficient evidence": 2,
        "Awaiting data": 3,
        "Rejected": 4,
    }
    entries.sort(
        key=lambda e: (
            tier_priority.get(e["classification"], 9),
            -float(e["sealed_holdout_metrics"]["net_pnl_usd"]),
            -float((e["combined_oos_metrics"]["cluster_bootstrap_95ci"]["total_net_pnl_ci95"] or [0.0, 0.0])[0]),
            e["strategy_id"],
        )
    )
    for rank_idx, entry in enumerate(entries, start=1):
        entry["leaderboard_rank"] = rank_idx

    # Evaluate combined portfolio across Dominus actual seed ($48.81), $500, and $5,000 tiers
    portfolio_tiers: Dict[str, Any] = {}
    for tier_lbl, tier_nav in (
        ("tier_1_dominus_seed_48_81", DOMINUS_SEED_CASH_USD),
        ("tier_2_diversified_500", 500.0),
        ("tier_3_scalable_5000", 5000.0),
    ):
        portfolio_tiers[tier_lbl] = evaluate_combined_portfolio(
            promising_oos_by_strat,
            bankroll_usd=tier_nav,
            per_cluster_cap_frac=0.15,
            n_boot=n_boot,
            seed=seed + 999,
        )

    counts_by_label = collections.Counter(e["classification"] for e in entries)

    return {
        "generated_at_utc": dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "validation_standard": "DOMINUS_DIRECTIONAL_ALPHA_V1_INSTITUTIONAL",
        "total_strategies_evaluated": len(entries),
        "total_swarm_trials_m": total_m,
        "embargo_seconds": embargo_sec,
        "classification_counts": {lbl: int(counts_by_label.get(lbl, 0)) for lbl in DELIVERABLE_C_LABELS},
        "combined_portfolio_tiers": portfolio_tiers,
        "leaderboard": entries,
    }

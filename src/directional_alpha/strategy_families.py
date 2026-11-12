"""Core Multi-Category Directional Strategy Families for Polymarket (Pillars 1–4).

Implements 3 mandatory baselines + 16 modular directional strategy families spanning:
- **Pillar 1 (Price-Based):** Momentum/trend, short-horizon overreaction reversion,
  volatility-expansion breakout, L2 OBI & trade-flow pressure, boundary trend exhaustion.
- **Pillar 2 (Prediction & Information):** Crypto spot/vol Student-t digital & reflection
  barrier model, Weather forecast error & sensor rounding calibration (`D-006`),
  NegRisk multi-outcome slate relative-value divergence, Scheduled macro/sports drift.
- **Pillar 3 (Market-Behavior):** Favorite–longshot bias (`90c–98c` NO carry vs `2c–10c`
  retail YES lottery), TTE-conditioned crowd jump continuation vs reversion, objective
  pre-clinch late-stage convergence (`85c–95c`), temporary liquidity-shock snapback.
- **Pillar 4 (Quantitative ML & Bayesian):** Hierarchical Bayesian Beta + Log-Odds Kalman,
  L2-regularized market-offset Logistic Regression with Platt/PAVA calibration,
  Histogram GBDT + Regime-Conditioned Ensemble, and Causal Contextual Hedge Bandit.

Built-in Adversarial Safeguards (`RT-01` through `RT-10`):
- `sanitize_causal_trajectory`: Enforces strictly causal timestamps before `min(end_ts, clinch_ts)`
  AND strips terminal post-clinch absorption tails so strategies NEVER buy already-decided outcomes.
- `parse_contract_semantics`: Explicitly resolves affirmative vs negated wording (`"Will X NOT..."`),
  `ABOVE`/`BELOW`/`ONE_TOUCH`/`RANGE` strike polarity, `negRiskAugmented` `"Other"` traps, and
  category-calibrated UMA dispute risk (`D-009`).
- `ExecutionAdapter`: Binds dynamically to `@microstructure` (`execution_microstructure.py`) when
  available and enforces conservative non-zero spread + depth impact + stale-quote slippage on all
  historical CLOB series (zero midpoint fill fabrication, `RT-02`), exact dynamic fees (`RT-03`),
  and Polymarket `5`-share / `$1.00` minimum lot rules (`RT-09`).
- Evaluates BOTH **Hold-to-Settlement** AND **Pre-Resolution Dynamic Exit** on every strategy.
"""

from __future__ import annotations

import collections
from dataclasses import asdict, dataclass, field
import importlib
import math
import re
import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.directional_alpha.ml_and_bayesian_models import (
    BayesianBetaCalibrationModel,
    CausalFeaturePreprocessor,
    ContextualHedgeAllocator,
    GradientBoostedProbTrees,
    RegimeConditionedEnsemble,
    RegularizedLogisticRegression,
    SequentialLogOddsKalman,
    clip_prob,
    logit,
    sigmoid,
)
from src.directional_alpha.execution_microstructure import (
    compute_taker_fee_per_share as _micro_taker_fee_ps,
    estimate_historical_taker_execution,
    resolve_fee_schedule,
    resolve_tick_size,
    validate_and_quantize_order_lot,
)
from src.directional_alpha.probability_and_payoff import (
    compute_polymarket_fee_per_share,
    evaluate_hold_to_settlement,
    optimal_dynamic_exit_rule,
    optimal_entry_threshold,
    resolve_side_probability,
    round_price_down_to_tick,
    round_price_up_to_tick,
)


# ==============================================================================
# 1. CANONICAL DATA STRUCTURES & CONTRACT SEMANTICS PARSER (RT-01, RT-04, RT-06)
# ==============================================================================


@dataclass(frozen=True)
class PriceTick:
    """Single chronological observation along a Polymarket contract trajectory."""

    ts: float
    p_mid: float  # YES midpoint or last CLOB price in (0, 1)
    best_bid_yes: Optional[float] = None
    best_ask_yes: Optional[float] = None
    best_bid_no: Optional[float] = None
    best_ask_no: Optional[float] = None
    bid_depth_usd: Optional[float] = None
    ask_depth_usd: Optional[float] = None
    obi_l1: Optional[float] = None
    trade_flow_imbalance: Optional[float] = None
    volume_window_usd: float = 0.0
    external_spot: Optional[float] = None
    external_vol_annual: Optional[float] = None
    weather_forecast_c: Optional[float] = None
    weather_obs_max_c: Optional[float] = None
    weather_has_maintenance_flag: bool = False
    slate_sum_yes_mid: Optional[float] = None
    data_quality_class: str = "OBSERVED_TRADE_OR_CLOB_SERIES"
    is_post_outcome: bool = False


@dataclass
class MarketContractRecord:
    """Canonical multi-category resolved or active Polymarket contract for directional research."""

    market_id: str
    condition_id: str
    event_id: str
    category: str
    subcategory: str
    question: str
    created_ts: float
    end_ts: float
    resolved_outcome_yes: Optional[int]  # 1 = YES won, 0 = NO won, None = 50-50 void / disputed / unresolved
    yes_settlement_payout: Optional[float] = None  # Continuous [0, 1]: 0.5 on 50-50 void, 0.0 on D-009 disputed floor
    no_settlement_payout: Optional[float] = None   # Continuous [0, 1]: 0.5 on 50-50 void, 0.0 on D-009 disputed floor
    resolution_ts: Optional[float] = None
    clinch_ts: Optional[float] = None
    fee_rate: float = 0.0
    fee_exponent: float = 1.0
    maker_rebate_rate: float = 0.0
    tick_size: float = 0.01
    liquidity_usd: float = 500.0
    volume_total_usd: float = 1000.0
    neg_risk: bool = False
    neg_risk_augmented: bool = False
    outcome_label: str = ""
    uma_resolution_status: str = "resolved"
    resolution_source: str = ""
    strike_value: Optional[float] = None
    bucket_low: Optional[float] = None
    bucket_high: Optional[float] = None
    ticks: List[PriceTick] = field(default_factory=list)

    def resolve_side_settlement_payout(self, side: str) -> Optional[float]:
        """Returns continuous per-share settlement payout in [0.0, 1.0] without hiding voids/disputes (`RT-04`)."""
        side_u = side.upper()
        if side_u == "YES" and self.yes_settlement_payout is not None:
            return max(0.0, min(1.0, float(self.yes_settlement_payout)))
        if side_u == "NO" and self.no_settlement_payout is not None:
            return max(0.0, min(1.0, float(self.no_settlement_payout)))
        if self.resolved_outcome_yes in (0, 1):
            return (1.0 if self.resolved_outcome_yes == 1 else 0.0) if side_u == "YES" else (1.0 if self.resolved_outcome_yes == 0 else 0.0)
        uma_l = str(self.uma_resolution_status or "").strip().lower()
        if uma_l in ("void", "50-50", "50_50"):
            return 0.50
        if uma_l in ("disputed", "frozen"):
            return 0.00  # D-009 worst-case guaranteed floor on frozen UMA disputes
        return None


@dataclass(frozen=True)
class ContractSemantics:
    """Parsed semantic structure of a Polymarket contract (`RT-04` protection)."""

    semantics_type: str  # AFFIRMATIVE | NEGATED | ABOVE_STRIKE | BELOW_STRIKE | ONE_TOUCH_UP | ONE_TOUCH_DOWN | RANGE_BUCKET
    question_is_negated: bool
    is_placeholder_or_other: bool
    is_disputed_or_void: bool
    is_objective_oracle: bool
    p_uma_dispute: float
    extracted_strike: Optional[float]
    extracted_range: Optional[Tuple[float, float]]
    cluster_key: str


_NEGATION_RE = re.compile(
    r"\b(?:not|won't|will\s+not|cannot|can't|never|fail\s+to|without|no\s+longer|neither)\b",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(
    r"^\s*(?:other|the\s+field|field|none(?:\s+of\s+the\s+above)?|any\s+other|someone\s+else|another\s+.+|person\s+[a-z0-9])\s*$",
    re.IGNORECASE,
)
_PLACEHOLDER_Q_RE = re.compile(
    r"\b(?:other\s+candidate|another\s+candidate|any\s+other\s+team|person\s+[a-z])\b",
    re.IGNORECASE,
)
_ONE_TOUCH_UP_RE = re.compile(r"\b(?:hit|reach|touch)\b", re.IGNORECASE)
_ONE_TOUCH_DOWN_RE = re.compile(r"\b(?:dip\s+to|drop\s+to|fall\s+to)\b", re.IGNORECASE)
_ABOVE_RE = re.compile(
    r"\b(?:above|over|exceed|more\s+than|greater\s+than|higher\s+than|at\s+least)\b|[>≥↑]",
    re.IGNORECASE,
)
_BELOW_RE = re.compile(
    r"\b(?:below|under|less\s+than|fewer\s+than|lower\s+than|at\s+most|drop\s+below)\b|[<≤↓]",
    re.IGNORECASE,
)
_RANGE_NUM_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*(?:[°º]?[CFcf]|%|k|K)?\s*(?:to|and|-|–)\s*(-?\d+(?:\.\d+)?)\s*(?:[°º]?[CFcf]|%|k|K)?"
)
_DOLLAR_OR_NUM_STRIKE_RE = re.compile(
    r"(?:\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kKmMbB])?)"
    r"|(?:(-?\d+(?:\.\d+)?)\s*(?:[°º]\s*[CF]|[°º][CF]|\bdegrees\b))"
)


def parse_contract_semantics(contract: MarketContractRecord) -> ContractSemantics:
    """Explicitly parses YES/NO polarity, threshold direction, placeholder traps, and UMA risk."""
    q = str(contract.question or "").strip()
    lbl = str(contract.outcome_label or "").strip()
    cat = str(contract.category or "OTHER").strip().upper()

    is_placeholder = bool(
        (lbl and _PLACEHOLDER_RE.match(lbl))
        or _PLACEHOLDER_Q_RE.search(q)
        or (contract.neg_risk_augmented and lbl.lower().startswith("other"))
    )
    uma_stat = str(contract.uma_resolution_status or "").strip().lower()
    is_disputed = uma_stat in ("disputed", "void", "50-50", "cancelled")

    has_neg = bool(_NEGATION_RE.search(q))
    strike = contract.strike_value
    rng: Optional[Tuple[float, float]] = None
    if contract.bucket_low is not None and contract.bucket_high is not None:
        rng = (float(contract.bucket_low), float(contract.bucket_high))

    if strike is None or rng is None:
        m_rng = _RANGE_NUM_RE.search(q) or _RANGE_NUM_RE.search(lbl)
        if m_rng and ("between" in q.lower() or "°" in q or "temp" in q.lower()):
            try:
                lo_v, hi_v = float(m_rng.group(1)), float(m_rng.group(2))
                if lo_v < hi_v and rng is None:
                    rng = (lo_v, hi_v)
            except ValueError:
                pass
        if strike is None:
            m_st = _DOLLAR_OR_NUM_STRIKE_RE.search(q)
            if m_st:
                if m_st.group(1):
                    val = float(m_st.group(1).replace(",", ""))
                    mult = (m_st.group(2) or "").upper()
                    if mult == "K":
                        val *= 1e3
                    elif mult == "M":
                        val *= 1e6
                    elif mult == "B":
                        val *= 1e9
                    strike = val
                elif m_st.group(3):
                    strike = float(m_st.group(3))

    if (
        rng is None
        and strike is not None
        and ("temperature" in q.lower() or "°" in q or "º" in q)
        and not _ABOVE_RE.search(q)
        and not _BELOW_RE.search(q)
    ):
        # Single-degree integer weather bucket: e.g. "Will the highest temperature in Paris be 16°C?" -> [15.5, 16.5]
        rng = (float(strike) - 0.5, float(strike) + 0.5)

    if rng is not None:
        sem_type = "RANGE_BUCKET"
    elif _ONE_TOUCH_DOWN_RE.search(q):
        sem_type = "ONE_TOUCH_DOWN"
    elif _ONE_TOUCH_UP_RE.search(q) and strike is not None:
        sem_type = "ONE_TOUCH_UP"
    elif _BELOW_RE.search(q) and not _ABOVE_RE.search(q):
        sem_type = "BELOW_STRIKE"
    elif _ABOVE_RE.search(q) and strike is not None:
        sem_type = "ABOVE_STRIKE"
    elif has_neg:
        sem_type = "NEGATED"
    else:
        sem_type = "AFFIRMATIVE"

    src_l = (str(contract.resolution_source or "") + " " + q).lower()
    objective_tokens = (
        "binance", "chainlink", "pyth", "coinbase", "official", "associated press",
        "bls", "federal reserve", "fomc", "nba", "nfl", "mlb", "nhl", "fifa", "uefa",
        "noaa", "metar", "aviationweather", "wunderground", "sec",
    )
    is_objective = any(tok in src_l for tok in objective_tokens) or cat in (
        "CRYPTO", "ECONOMICS", "MACRO", "SPORTS", "FINANCE"
    )

    # Calibrated UMA dispute rates grounded in Dominus live telemetry (including KMIA weather dispute)
    if cat == "WEATHER":
        p_disp = 0.0065
    elif is_objective:
        p_disp = 0.0018
    else:
        p_disp = 0.0090

    day_bucket = int(max(0.0, float(contract.end_ts)) // 86400)
    ev_id = str(contract.event_id or "").strip()
    cluster_key = f"EVT:{ev_id}" if ev_id else f"CATDAY:{cat}:{day_bucket}"

    return ContractSemantics(
        semantics_type=sem_type,
        question_is_negated=has_neg,
        is_placeholder_or_other=is_placeholder,
        is_disputed_or_void=is_disputed,
        is_objective_oracle=is_objective,
        p_uma_dispute=p_disp,
        extracted_strike=strike,
        extracted_range=rng,
        cluster_key=cluster_key,
    )


def sanitize_causal_trajectory(
    contract: MarketContractRecord,
    min_seconds_before_cutoff: float = 300.0,
) -> Tuple[List[PriceTick], float]:
    """Filters a contract's price trajectory to strictly causal pre-cutoff ticks (`RT-01` / `RT-05`).

    Returns `(clean_ticks, effective_schedule_cutoff_ts)`.
    1. Drops any tick with `is_post_outcome=True`, `data_quality_class == 'UNAVAILABLE'`,
       or `ts > min(end_ts, resolution_ts, clinch_ts) - min_seconds_before_cutoff`, where
       `clinch_ts` is strictly causal schedule/metadata (NEVER backward future-outcome-peeking!).
    2. Preserves all pre-cutoff interior price moves (including `>= 0.985` and `<= 0.015`) so
       comebacks and `PRE_RESOLUTION_EXIT` target/stop fills are never biased by future outcomes!
    """
    hard_cutoffs = [float(contract.end_ts)]
    if contract.resolution_ts is not None and contract.resolution_ts > 0:
        hard_cutoffs.append(float(contract.resolution_ts))
    if contract.clinch_ts is not None and contract.clinch_ts > 0:
        hard_cutoffs.append(float(contract.clinch_ts))
    eff_end_ts = min(hard_cutoffs)

    valid: List[PriceTick] = []
    last_ts = -1.0
    for tk in sorted(contract.ticks, key=lambda x: float(x.ts)):
        if tk.is_post_outcome or tk.data_quality_class == "UNAVAILABLE":
            continue
        ts_f = float(tk.ts)
        if ts_f < float(contract.created_ts) - 60.0:
            continue
        if ts_f > eff_end_ts - float(min_seconds_before_cutoff):
            continue
        pm = float(tk.p_mid)
        if math.isnan(pm) or pm <= 0.0005 or pm >= 0.9995:
            continue
        if ts_f <= last_ts:
            continue
        valid.append(tk)
        last_ts = ts_f

    return valid, eff_end_ts


# ==============================================================================
# 2. EXECUTION MICROSTRUCTURE ADAPTER & DUAL EXIT LIFECYCLE SIMULATOR
# ==============================================================================


# Empirically grounded category spread & depth defaults used ONLY when observed L2 is absent
_CATEGORY_HALF_SPREAD_DEFAULTS: Dict[str, float] = {
    "CRYPTO": 0.012,
    "SPORTS": 0.014,
    "POLITICS": 0.011,
    "ECONOMICS": 0.012,
    "MACRO": 0.012,
    "FINANCE": 0.014,
    "WEATHER": 0.016,
    "GEOPOLITICS": 0.015,
    "TECH": 0.016,
    "CULTURE": 0.018,
    "SCIENCE": 0.018,
    "OTHER": 0.018,
}


class ExecutionAdapter:
    """Deterministic execution quote, fee, slippage, and lot-sizing adapter.

    Directly delegates historical series execution to `@microstructure`
    (`src.directional_alpha.execution_microstructure.estimate_historical_taker_execution`)
    and `validate_and_quantize_order_lot`, guaranteeing zero midpoint fill fabrication (`RT-02`),
    exact Polymarket Protocol V2 curved fees (`RT-03`), and `5`-share / `$1.00` CLOB minimum lots
    within Dominus's `$48.81` `15%` (`$7.32`) concentration cap (`RT-09`).
    """

    def __init__(self, cost_stress_multiplier: float = 1.0) -> None:
        self.cost_stress_multiplier = max(0.25, float(cost_stress_multiplier))
        self._quote_cache: Dict[Tuple[str, int, int, int, int], Tuple[float, float, float]] = {}

    def estimate_half_spread_and_slippage(
        self,
        contract: MarketContractRecord,
        tick: PriceTick,
        side: str,
        notional_usd: float,
    ) -> Tuple[float, float, float]:
        """Returns `(exec_bid_side, exec_ask_side, extra_slippage_per_share)` for `side` ('YES'|'NO')."""
        side_u = side.upper()
        cat = str(contract.category or "OTHER").upper()
        liq = max(50.0, float(contract.liquidity_usd or 250.0))
        p_side_mid = clip_prob(tick.p_mid if side_u == "YES" else (1.0 - tick.p_mid), 0.005)
        t_sz = resolve_tick_size(p_side_mid, max(0.001, float(contract.tick_size or 0.01)))

        # 1. Observed L2 quotes if present on tick (`OBSERVED_EXECUTABLE_L2`)
        obs_bid: Optional[float] = None
        obs_ask: Optional[float] = None
        if side_u == "YES":
            if tick.best_bid_yes is not None and tick.best_ask_yes is not None:
                obs_bid, obs_ask = float(tick.best_bid_yes), float(tick.best_ask_yes)
        else:
            if tick.best_bid_no is not None and tick.best_ask_no is not None:
                obs_bid, obs_ask = float(tick.best_bid_no), float(tick.best_ask_no)
            elif tick.best_bid_yes is not None and tick.best_ask_yes is not None:
                # Exact complementary Polymarket CLOB book identity: Bid_NO = 1 - Ask_YES, Ask_NO = 1 - Bid_YES
                obs_bid = round(1.0 - float(tick.best_ask_yes), 6)
                obs_ask = round(1.0 - float(tick.best_bid_yes), 6)

        if obs_bid is not None and obs_ask is not None and 0.0 < obs_bid < obs_ask < 1.0:
            mid_obs = 0.5 * (obs_bid + obs_ask)
            half_obs = max(0.5 * t_sz, 0.5 * (obs_ask - obs_bid) * self.cost_stress_multiplier)
            bid_px = max(0.001, min(p_side_mid - 0.25 * t_sz, mid_obs - half_obs))
            ask_px = min(0.999, max(p_side_mid + 0.25 * t_sz, mid_obs + half_obs))
            avail_depth = float(tick.ask_depth_usd or max(35.0, 0.12 * liq))
            depth_impact = 0.005 * (max(1.0, float(notional_usd)) / max(15.0, avail_depth))
            lat_pen = 0.0025 if cat == "CRYPTO" else 0.0010
            slip = min(0.06, (depth_impact + lat_pen) * self.cost_stress_multiplier)
            return round(bid_px, 6), round(ask_px, 6), round(slip, 6)

        # 2. Calibrated `@microstructure` execution estimator for historical CLOB trajectories (`RT-02`)
        req_usd = max(5.50, float(notional_usd))
        cache_key = (
            cat,
            int(round(math.log1p(liq) * 8.0)),
            int(round(p_side_mid * 1000.0)),
            int(round(t_sz * 1000.0)),
            int(round(req_usd * 2.0)),
        )
        cached = self._quote_cache.get(cache_key)
        if cached is not None:
            return cached

        buy_est = estimate_historical_taker_execution(
            p_side_mid,
            side="BUY",
            notional_usd=req_usd,
            category=cat,
            liquidity_usd=liq,
            fee_rate=contract.fee_rate,
            fee_exponent=contract.fee_exponent,
            fees_enabled=(contract.fee_rate > 0.0),
            tick_size=t_sz,
            stress_cost_multiplier=self.cost_stress_multiplier,
            enforce_min_lot=False,
        )
        sell_est = estimate_historical_taker_execution(
            p_side_mid,
            side="SELL",
            notional_usd=req_usd,
            category=cat,
            liquidity_usd=liq,
            fee_rate=contract.fee_rate,
            fee_exponent=contract.fee_exponent,
            fees_enabled=(contract.fee_rate > 0.0),
            tick_size=t_sz,
            stress_cost_multiplier=self.cost_stress_multiplier,
            enforce_min_lot=False,
        )
        if buy_est.fillable and sell_est.fillable:
            ask_px = max(p_side_mid + 0.5 * t_sz, float(buy_est.best_touch_px))
            bid_px = min(p_side_mid - 0.5 * t_sz, float(sell_est.best_touch_px))
            slip_buy = max(0.0005, float(buy_est.effective_exec_px_before_fee) - ask_px)
            res = (round(max(0.001, bid_px), 6), round(min(0.999, ask_px), 6), round(slip_buy, 6))
            self._quote_cache[cache_key] = res
            return res

        # Conservative fallback near extreme boundaries
        base_hs = _CATEGORY_HALF_SPREAD_DEFAULTS.get(cat, 0.016) * self.cost_stress_multiplier
        est_hs = max(0.5 * t_sz, base_hs)
        bid_px = max(0.001, p_side_mid - est_hs)
        ask_px = min(0.999, p_side_mid + est_hs)
        slip = min(0.05, 0.003 * self.cost_stress_multiplier)
        res_fb = (round(bid_px, 6), round(ask_px, 6), round(slip, 6))
        self._quote_cache[cache_key] = res_fb
        return res_fb

    @staticmethod
    def quantize_order_shares(
        desired_notional_usd: float,
        exec_price: float,
        entry_fee_per_share: float = 0.0,
        available_depth_usd: float = 250.0,
        min_shares: float = 5.0,
        min_notional_usd: float = 1.00,
        max_event_cap_usd: float = 7.10,
    ) -> Tuple[float, float, float]:
        """Enforces Polymarket CLOB minimum lot (`>= 5` shares & `>= $1.00`), L2 depth cap, and `15%` Tier-1 cap."""
        cap_notional = min(
            float(desired_notional_usd),
            float(max_event_cap_usd),
            max(2.0, 0.45 * float(available_depth_usd)),
        )
        if exec_price <= 0.0 or cap_notional < min_notional_usd:
            return 0.0, 0.0, 0.0
        lot = validate_and_quantize_order_lot(
            cap_notional,
            exec_price,
            min_order_shares=min_shares,
            min_order_notional_usd=min_notional_usd,
            tick_size=resolve_tick_size(exec_price, 0.01),
            exact_cent_maker_amount=False,
            allow_lot_floor_upsize=True,
            max_lot_upsize_ratio=max(1.0, float(max_event_cap_usd) / max(cap_notional, 1e-6)),
        )
        if not lot.eligible or lot.quantized_shares < min_shares - 1e-6:
            return 0.0, 0.0, 0.0
        shares = float(lot.quantized_shares)
        gross_notional = round(shares * exec_price, 6)
        if gross_notional > float(max_event_cap_usd) + 1e-6:
            return 0.0, 0.0, 0.0
        committed = round(shares * (exec_price + entry_fee_per_share), 6)
        return shares, gross_notional, committed


@dataclass
class DirectionalSignal:
    """Standardized directional trade candidate emitted by any Pillar 1–4 strategy."""

    strategy_id: str
    pillar: str
    market_id: str
    event_id: str
    cluster_key: str
    category: str
    side: str  # "YES" or "NO"
    entry_idx: int
    entry_ts: float
    p_yes_market: float
    p_yes_model: float
    sigma_p: float
    target_price_move: float = 0.06
    stop_price_move: float = 0.08
    max_hold_hours: float = 48.0
    prefer_pre_exit: bool = False
    rationale: str = ""
    features_snapshot: Dict[str, float] = field(default_factory=dict)


@dataclass
class SimulatedTrade:
    """Complete audited record of a simulated directional trade (Hold or Pre-Exit)."""

    strategy_id: str
    pillar: str
    exit_mode: str  # "HOLD_TO_SETTLEMENT" or "PRE_RESOLUTION_EXIT"
    market_id: str
    event_id: str
    cluster_key: str
    category: str
    subcategory: str
    question: str
    semantics_type: str
    side: str
    entry_ts: float
    exit_ts: float
    clinch_ts: float
    settlement_ts: float
    p_yes_market: float
    p_yes_model: float
    pi_side_model: float
    sigma_p: float
    entry_ask: float
    entry_exec_price: float
    entry_fee_per_share: float
    fee_rate: float
    tick_size: float
    shares: float
    notional_usd: float
    capital_committed_usd: float
    exit_exec_price: float
    exit_fee_per_share: float
    exit_reason: str
    resolved_outcome_yes: int  # 1=YES, 0=NO, -1=void/disputed
    settlement_payout_per_share: float  # Continuous [0.0, 1.0]: 0.5 on 50-50 void, 0.0 on D-009 disputed floor
    gross_pnl_usd: float
    total_fees_usd: float
    total_slippage_usd: float
    net_pnl_usd: float
    return_on_capital: float
    hold_days: float
    dollar_days_committed: float
    max_intra_trade_drawdown_pct: float
    available_capacity_usd: float
    data_quality_class: str

    def clone_with(self, **overrides: Any) -> "SimulatedTrade":
        base = asdict(self)
        base.update(overrides)
        return SimulatedTrade(**base)

    def to_dict(self) -> Dict[str, Any]:
        """Emits unified trade dictionary satisfying `@prob-alpha`, `@stat-validator`, and `@red-team`."""
        d = asdict(self)
        side_mid = self.p_yes_market if self.side == "YES" else (1.0 - self.p_yes_market)
        side_payout = max(0.0, min(1.0, float(self.settlement_payout_per_share)))
        is_void = abs(side_payout - 0.5) <= 1e-4
        is_disputed = (self.resolved_outcome_yes < 0) and (not is_void)
        spread_bps = (self.total_slippage_usd / max(1e-9, self.shares * side_mid)) * 10000.0
        d.update(
            {
                "trade_id": f"{self.strategy_id}:{self.exit_mode}:{self.market_id}:{int(self.entry_ts)}",
                "exit_type": self.exit_mode,
                "entry_price": self.entry_exec_price,
                "exit_price": self.exit_exec_price,
                "mid_price": round(side_mid, 6),
                "market_mid_entry": round(side_mid, 6),
                "market_mid": round(side_mid, 6),
                "p_model": round(self.pi_side_model, 6),
                "model_prob_entry": round(self.pi_side_model, 6),
                "p_hat": round(self.pi_side_model, 6),
                "outcome_binary": round(side_payout, 6),
                "outcome_payout": round(side_payout, 6),
                "outcome": round(side_payout, 6),
                "is_void_50_50": is_void,
                "uma_disputed": is_disputed,
                "fees_enabled": self.fee_rate > 0.0,
                "available_depth_usd": self.available_capacity_usd,
                "capital_usd": self.capital_committed_usd,
                "fees_usd": self.total_fees_usd,
                "fee_usd": self.total_fees_usd,
                "spread_slippage_cost_usd": self.total_slippage_usd,
                "spread_cost_bps": round(max(0.01, spread_bps), 2),
                "fee_rate_bps": round(self.fee_rate * 10000.0, 2),
                "end_ts": self.settlement_ts,
                "is_maker_entry": False,
                "is_maker_exit": False,
            }
        )
        return d


def simulate_trade_lifecycle(
    contract: MarketContractRecord,
    semantics: ContractSemantics,
    clean_ticks: Sequence[PriceTick],
    eff_settlement_ts: float,
    signal: DirectionalSignal,
    adapter: ExecutionAdapter,
    exit_mode: str = "HOLD_TO_SETTLEMENT",
    target_notional_usd: float = 6.50,
    r_opp_per_day: float = 0.003,
) -> Optional[SimulatedTrade]:
    """Simulates a directional signal under EITHER Hold-to-Settlement OR Pre-Resolution Exit.

    - `HOLD_TO_SETTLEMENT`: Continuous `[0, 1]` settlement redemption (`1.0`/`0.0` on standard
      resolution, `0.50` on `50-50` void, `0.00` conservative floor on unresolved `disputed` per `D-009` / `RT-04`).
    - `PRE_RESOLUTION_EXIT`: Pure secondary-market dynamic exit strictly before resolution (`exit_price in (0, 1)`),
      paying realistic exit bid spread + slippage + Protocol V2 sell fee (`RT-12` zero conflation!).
    - Never reads any tick before `signal.entry_idx` for execution or after `eff_settlement_ts` (`RT-01`).
    """
    side_u = signal.side.upper()
    settlement_payoff_opt = contract.resolve_side_settlement_payout(side_u)
    if settlement_payoff_opt is None:
        return None
    settlement_payoff_ps = float(settlement_payoff_opt)

    if signal.entry_idx < 0 or signal.entry_idx >= len(clean_ticks):
        return None
    if exit_mode == "PRE_RESOLUTION_EXIT" and signal.entry_idx >= len(clean_ticks) - 1:
        return None

    entry_tick = clean_ticks[signal.entry_idx]
    eff_clinch = float(eff_settlement_ts)
    if float(entry_tick.ts) >= eff_clinch - 1e-3 or float(entry_tick.ts) >= float(contract.end_ts) - 1e-3:
        return None

    entry_side_mid = clip_prob(entry_tick.p_mid if side_u == "YES" else (1.0 - entry_tick.p_mid), 0.002)
    avail_depth = float(entry_tick.ask_depth_usd or max(40.0, 0.20 * float(contract.liquidity_usd or 300.0)))

    _, entry_ask, entry_slip = adapter.estimate_half_spread_and_slippage(
        contract, entry_tick, side_u, target_notional_usd
    )
    eff_tick = resolve_tick_size(entry_side_mid, max(0.001, float(contract.tick_size or 0.01)))
    entry_exec = min(0.992, max(entry_side_mid + max(0.5 * eff_tick, 0.002), entry_ask + entry_slip))
    if entry_exec >= 0.990 or entry_exec <= 0.008:
        return None

    pi_side_mod = clip_prob(signal.p_yes_model if side_u == "YES" else (1.0 - signal.p_yes_model), 0.002)
    # Enforce >= 1-tick structural edge over executable entry price for all non-baseline strategies (`RT-03`)
    if not signal.strategy_id.startswith("B") and (pi_side_mod - entry_exec) < eff_tick:
        return None

    entry_fee_ps = _micro_taker_fee_ps(
        entry_exec,
        fee_rate=contract.fee_rate,
        fee_exponent=contract.fee_exponent,
    )
    cost_ps = entry_exec + entry_fee_ps
    shares, gross_notional_usd, committed_usd = adapter.quantize_order_shares(
        desired_notional_usd=target_notional_usd,
        exec_price=entry_exec,
        entry_fee_per_share=entry_fee_ps,
        available_depth_usd=avail_depth,
    )
    if shares <= 0.0:
        return None

    res_yes_code = int(contract.resolved_outcome_yes) if contract.resolved_outcome_yes in (0, 1) else -1

    # Track worst intra-trade mark-to-bid drawdown across remaining causal trajectory
    worst_bid_ps = entry_exec
    for k in range(signal.entry_idx + 1, len(clean_ticks)):
        b_k, _, _ = adapter.estimate_half_spread_and_slippage(
            contract, clean_ticks[k], side_u, gross_notional_usd
        )
        if b_k < worst_bid_ps:
            worst_bid_ps = b_k

    if exit_mode == "HOLD_TO_SETTLEMENT":
        exit_ts = max(float(entry_tick.ts) + 60.0, float(contract.end_ts))
        hold_days = max(1.0 / 1440.0, (exit_ts - float(entry_tick.ts)) / 86400.0)
        gross_pnl = round(shares * (settlement_payoff_ps - entry_side_mid), 6)
        tot_fees = round(shares * entry_fee_ps, 6)
        tot_slip = round(shares * max(0.0001, entry_exec - entry_side_mid), 6)
        net_pnl = round(gross_pnl - tot_fees - tot_slip, 6)
        if settlement_payoff_ps <= 0.01:
            max_dd_pct = 1.0
        elif settlement_payoff_ps < cost_ps:
            max_dd_pct = max(0.0, (cost_ps - min(worst_bid_ps, settlement_payoff_ps)) / cost_ps)
        else:
            max_dd_pct = max(0.0, (cost_ps - worst_bid_ps) / cost_ps)

        return SimulatedTrade(
            strategy_id=signal.strategy_id,
            pillar=signal.pillar,
            exit_mode="HOLD_TO_SETTLEMENT",
            market_id=contract.market_id,
            event_id=contract.event_id,
            cluster_key=signal.cluster_key,
            category=contract.category.upper(),
            subcategory=str(contract.subcategory or "general"),
            question=contract.question,
            semantics_type=semantics.semantics_type,
            side=side_u,
            entry_ts=float(entry_tick.ts),
            exit_ts=exit_ts,
            clinch_ts=eff_clinch,
            settlement_ts=float(contract.end_ts),
            p_yes_market=float(entry_tick.p_mid),
            p_yes_model=float(signal.p_yes_model),
            pi_side_model=float(pi_side_mod),
            sigma_p=float(signal.sigma_p),
            entry_ask=round(entry_ask, 6),
            entry_exec_price=round(entry_exec, 6),
            entry_fee_per_share=round(entry_fee_ps, 6),
            fee_rate=float(contract.fee_rate),
            tick_size=eff_tick,
            shares=shares,
            notional_usd=gross_notional_usd,
            capital_committed_usd=committed_usd,
            exit_exec_price=settlement_payoff_ps,
            exit_fee_per_share=0.0,
            exit_reason="SETTLEMENT",
            resolved_outcome_yes=res_yes_code,
            settlement_payout_per_share=settlement_payoff_ps,
            gross_pnl_usd=gross_pnl,
            total_fees_usd=tot_fees,
            total_slippage_usd=tot_slip,
            net_pnl_usd=net_pnl,
            return_on_capital=round(net_pnl / committed_usd, 6),
            hold_days=round(hold_days, 6),
            dollar_days_committed=round(committed_usd * hold_days, 6),
            max_intra_trade_drawdown_pct=round(min(1.0, max_dd_pct), 6),
            available_capacity_usd=round(avail_depth, 2),
            data_quality_class=entry_tick.data_quality_class,
        )

    # Mechanism 2: Strictly Causal Pre-Resolution Dynamic Exit (NEVER settles at {0, 1} — `RT-12` clean!)
    target_bid = min(0.985, entry_exec + max(0.02, float(signal.target_price_move)))
    stop_bid = max(0.015, entry_exec - max(0.03, float(signal.stop_price_move)))
    max_hold_sec = max(600.0, float(signal.max_hold_hours) * 3600.0)

    worst_seen_bid = entry_exec
    last_idx = len(clean_ticks) - 1
    for k in range(signal.entry_idx + 1, len(clean_ticks)):
        tk = clean_ticks[k]
        bid_k, _, slip_k = adapter.estimate_half_spread_and_slippage(
            contract, tk, side_u, gross_notional_usd
        )
        if bid_k < worst_seen_bid:
            worst_seen_bid = bid_k
        elapsed_sec = max(1.0, float(tk.ts) - float(entry_tick.ts))
        rem_days = max(1.0 / 1440.0, (float(contract.end_ts) - float(tk.ts)) / 86400.0)

        # Updated causal posterior blends initial model edge (decaying over time) with current market mid
        p_side_mkt_k = clip_prob(tk.p_mid if side_u == "YES" else (1.0 - tk.p_mid), 0.002)
        decay = math.exp(-elapsed_sec / max(1800.0, 0.75 * max_hold_sec))
        post_pi_k = clip_prob(sigmoid(logit(p_side_mkt_k) + decay * (logit(pi_side_mod) - logit(entry_side_mid))))

        exit_reason: Optional[str] = None
        extra_stop_slip = 0.0
        if bid_k >= target_bid:
            exit_reason = "PRE_EXIT_TARGET_CAPTURE"
        elif bid_k <= stop_bid:
            exit_reason = "PRE_EXIT_STOP_LOSS"
            extra_stop_slip = 0.004 * adapter.cost_stress_multiplier
        elif elapsed_sec >= max_hold_sec:
            exit_reason = "PRE_EXIT_TIME_STOP"
        else:
            stop_eval = optimal_dynamic_exit_rule(
                current_bid_price=clip_prob(bid_k, 0.005),
                remaining_days_to_settlement=rem_days,
                posterior_pi_side=post_pi_k,
                posterior_sigma_p=signal.sigma_p,
                sigma_k=0.75,
                exit_slippage_per_share=slip_k,
                fee_rate=contract.fee_rate,
                fee_exponent=contract.fee_exponent,
                p_uma_dispute=semantics.p_uma_dispute,
                r_opp_per_day=r_opp_per_day,
            )
            if stop_eval["should_exit_now"] and bid_k > entry_exec + 0.015:
                exit_reason = f"PRE_EXIT_{stop_eval['decision_reason']}"
            elif k == last_idx:
                exit_reason = "PRE_EXIT_HORIZON_CUTOFF"

        if exit_reason is not None:
            exit_exec = min(
                max(0.002, p_side_mkt_k - 0.001),
                max(0.002, bid_k - slip_k - extra_stop_slip),
            )
            exit_fee_ps = _micro_taker_fee_ps(
                exit_exec,
                fee_rate=contract.fee_rate,
                fee_exponent=contract.fee_exponent,
            )
            gross_pnl = round(shares * (p_side_mkt_k - entry_side_mid), 6)
            tot_fees = round(shares * (entry_fee_ps + exit_fee_ps), 6)
            tot_slip = round(shares * max(0.0002, (entry_exec - entry_side_mid) + (p_side_mkt_k - exit_exec)), 6)
            net_pnl = round(gross_pnl - tot_fees - tot_slip, 6)
            hold_days = max(1.0 / 1440.0, elapsed_sec / 86400.0)
            dd_pct = max(0.0, (cost_ps - min(worst_seen_bid, exit_exec)) / cost_ps)

            return SimulatedTrade(
                strategy_id=signal.strategy_id,
                pillar=signal.pillar,
                exit_mode="PRE_RESOLUTION_EXIT",
                market_id=contract.market_id,
                event_id=contract.event_id,
                cluster_key=signal.cluster_key,
                category=contract.category.upper(),
                subcategory=str(contract.subcategory or "general"),
                question=contract.question,
                semantics_type=semantics.semantics_type,
                side=side_u,
                entry_ts=float(entry_tick.ts),
                exit_ts=float(tk.ts),
                clinch_ts=eff_clinch,
                settlement_ts=float(contract.end_ts),
                p_yes_market=float(entry_tick.p_mid),
                p_yes_model=float(signal.p_yes_model),
                pi_side_model=float(pi_side_mod),
                sigma_p=float(signal.sigma_p),
                entry_ask=round(entry_ask, 6),
                entry_exec_price=round(entry_exec, 6),
                entry_fee_per_share=round(entry_fee_ps, 6),
                fee_rate=float(contract.fee_rate),
                tick_size=eff_tick,
                shares=shares,
                notional_usd=gross_notional_usd,
                capital_committed_usd=committed_usd,
                exit_exec_price=round(exit_exec, 6),
                exit_fee_per_share=round(exit_fee_ps, 6),
                exit_reason=exit_reason,
                resolved_outcome_yes=res_yes_code,
                settlement_payout_per_share=settlement_payoff_ps,
                gross_pnl_usd=gross_pnl,
                total_fees_usd=tot_fees,
                total_slippage_usd=tot_slip,
                net_pnl_usd=net_pnl,
                return_on_capital=round(net_pnl / committed_usd, 6),
                hold_days=round(hold_days, 6),
                dollar_days_committed=round(committed_usd * hold_days, 6),
                max_intra_trade_drawdown_pct=round(min(1.0, dd_pct), 6),
                available_capacity_usd=round(avail_depth, 2),
                data_quality_class=entry_tick.data_quality_class,
            )

    return None


# ==============================================================================
# 3. CAUSAL TRAJECTORY FEATURE EXTRACTOR (SHARED BY ALL PILLARS)
# ==============================================================================


def extract_causal_tick_features(
    contract: MarketContractRecord,
    semantics: ContractSemantics,
    clean_ticks: Sequence[PriceTick],
    idx: int,
    kalman_probs: Optional[Sequence[float]] = None,
    kalman_vels: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    """Computes strictly causal features using ONLY `clean_ticks[0 : idx + 1]`."""
    tk = clean_ticks[idx]
    p_now = clip_prob(tk.p_mid)
    z_now = logit(p_now)
    tte_hours = max(0.05, (float(contract.end_ts) - float(tk.ts)) / 3600.0)
    age_hours = max(0.05, (float(tk.ts) - float(contract.created_ts)) / 3600.0)

    # Short (1-3 steps) vs Medium (4-10 steps) causal history
    idx_s = max(0, idx - 2)
    idx_m = max(0, idx - 6)
    idx_l = max(0, idx - 14)

    p_s = clip_prob(clean_ticks[idx_s].p_mid)
    p_m = clip_prob(clean_ticks[idx_m].p_mid)
    p_l = clip_prob(clean_ticks[idx_l].p_mid)

    dp_short = p_now - p_s
    dp_med = p_now - p_m
    dz_short = z_now - logit(p_s)
    dz_med = z_now - logit(p_m)
    dz_long = z_now - logit(p_l)

    # Rolling causal realized volatility in log-odds & price space
    win_start = max(0, idx - 12)
    dz_diffs: List[float] = []
    dp_diffs: List[float] = []
    for k in range(win_start + 1, idx + 1):
        dz_diffs.append(logit(clean_ticks[k].p_mid) - logit(clean_ticks[k - 1].p_mid))
        dp_diffs.append(clean_ticks[k].p_mid - clean_ticks[k - 1].p_mid)

    vol_short = math.sqrt(sum(d * d for d in dz_diffs[-4:]) / max(1, len(dz_diffs[-4:]))) if dz_diffs else 0.05
    vol_long = math.sqrt(sum(d * d for d in dz_diffs) / max(1, len(dz_diffs))) if dz_diffs else 0.05
    vol_ratio = vol_short / max(0.01, vol_long)

    # Local median anchor for single-tick liquidity shock detection
    prev_slice = [clean_ticks[k].p_mid for k in range(max(0, idx - 4), idx)]
    local_median_prev = statistics.median(prev_slice) if prev_slice else p_now
    shock_dev = p_now - local_median_prev

    k_prob = float(kalman_probs[idx]) if (kalman_probs is not None and idx < len(kalman_probs)) else p_now
    k_vel = float(kalman_vels[idx]) if (kalman_vels is not None and idx < len(kalman_vels)) else 0.0

    spread_obs = None
    if tk.best_bid_yes is not None and tk.best_ask_yes is not None and tk.best_ask_yes > tk.best_bid_yes:
        spread_obs = float(tk.best_ask_yes) - float(tk.best_bid_yes)

    return {
        "entry_ts": float(tk.ts),
        "p_market": p_now,
        "logit_p_market": z_now,
        "abs_dist_from_half": abs(p_now - 0.5),
        "is_longshot_yes": 1.0 if p_now <= 0.10 else 0.0,
        "is_favorite_yes": 1.0 if p_now >= 0.88 else 0.0,
        "tte_hours": tte_hours,
        "log_tte_hours": math.log1p(tte_hours),
        "age_hours": age_hours,
        "dp_short": dp_short,
        "dp_med": dp_med,
        "dz_short": dz_short,
        "dz_med": dz_med,
        "dz_long": dz_long,
        "vol_short": vol_short,
        "vol_long": vol_long,
        "vol_ratio": vol_ratio,
        "shock_dev": shock_dev,
        "kalman_resid": logit(k_prob) - z_now,
        "kalman_vel": k_vel,
        "obi_l1": tk.obi_l1,
        "trade_flow_imbalance": tk.trade_flow_imbalance,
        "spread_obs": spread_obs,
        "slate_overround_excess": (
            (float(tk.slate_sum_yes_mid) - 1.0) if tk.slate_sum_yes_mid is not None else None
        ),
        "log_liquidity_usd": math.log1p(max(0.0, float(contract.liquidity_usd or 0.0))),
        "fee_rate": float(contract.fee_rate or 0.0),
        "neg_risk": 1.0 if contract.neg_risk else 0.0,
        "category": contract.category.upper(),
        "semantics_type": semantics.semantics_type,
    }


# ==============================================================================
# 4. MODULAR STRATEGY INTERFACE & ALL 4 PILLARS + MANDATORY BASELINES
# ==============================================================================


class BaseDirectionalStrategy:
    """Abstract base class for all Pillar 1–4 directional strategy families."""

    strategy_id: str = "BASE"
    pillar: str = "BASELINE"
    description: str = ""
    default_prefer_pre_exit: bool = False

    def fit(self, train_contracts: Sequence[MarketContractRecord]) -> "BaseDirectionalStrategy":
        """Optional Training-split-only parameter/model fit (`RT-07` compliant)."""
        return self

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        raise NotImplementedError

    def evaluate_contract(
        self,
        contract: MarketContractRecord,
        adapter: ExecutionAdapter,
        exit_mode: str = "HOLD_TO_SETTLEMENT",
        target_notional_usd: float = 6.50,
    ) -> List[SimulatedTrade]:
        """Sanitizes trajectory causally, generates signals, and simulates `exit_mode` trades."""
        clean_ticks, eff_cutoff_ts = sanitize_causal_trajectory(contract)
        if len(clean_ticks) < 2:
            return []
        semantics = parse_contract_semantics(contract)
        signals = self.generate_signals(contract, semantics, clean_ticks, adapter)
        trades: List[SimulatedTrade] = []
        for sig in signals:
            tr = simulate_trade_lifecycle(
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                eff_settlement_ts=eff_cutoff_ts,
                signal=sig,
                adapter=adapter,
                exit_mode=exit_mode,
                target_notional_usd=target_notional_usd,
            )
            if tr is not None:
                trades.append(tr)
        return trades

    def evaluate_prepared_both_modes(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        eff_cutoff_ts: float,
        adapter: ExecutionAdapter,
        target_notional_usd: float = 6.50,
    ) -> Tuple[List[SimulatedTrade], List[SimulatedTrade]]:
        """Generates signals once and simulates BOTH `HOLD_TO_SETTLEMENT` and `PRE_RESOLUTION_EXIT`."""
        if len(clean_ticks) < 2:
            return [], []
        signals = self.generate_signals(contract, semantics, clean_ticks, adapter)
        if not signals:
            return [], []
        hold_trades: List[SimulatedTrade] = []
        pre_trades: List[SimulatedTrade] = []
        for sig in signals:
            tr_h = simulate_trade_lifecycle(
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                eff_settlement_ts=eff_cutoff_ts,
                signal=sig,
                adapter=adapter,
                exit_mode="HOLD_TO_SETTLEMENT",
                target_notional_usd=target_notional_usd,
            )
            if tr_h is not None:
                hold_trades.append(tr_h)
            tr_p = simulate_trade_lifecycle(
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                eff_settlement_ts=eff_cutoff_ts,
                signal=sig,
                adapter=adapter,
                exit_mode="PRE_RESOLUTION_EXIT",
                target_notional_usd=target_notional_usd,
            )
            if tr_p is not None:
                pre_trades.append(tr_p)
        return hold_trades, pre_trades

    @staticmethod
    def _gate_and_build_signal(
        *,
        strategy_id: str,
        pillar: str,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        idx: int,
        p_yes_hat: float,
        sigma_p: float,
        adapter: ExecutionAdapter,
        min_net_edge_ps: float = 0.012,
        sigma_k: float = 0.75,
        target_price_move: float = 0.06,
        stop_price_move: float = 0.08,
        max_hold_hours: float = 48.0,
        prefer_pre_exit: bool = False,
        rationale: str = "",
        features_snapshot: Optional[Dict[str, float]] = None,
    ) -> Optional[DirectionalSignal]:
        """Evaluates BOTH YES and NO executable quotes and picks the strictly positive-EV side.

        NOTE (`RT-01` / `RT-04`): NEVER filters on `semantics.is_disputed_or_void`, because
        post-expiry `50-50` voids and UMA disputes are unknown at entry time `t`!
        Enforces strictly causal entry-tick bounds `0.02 <= tk.p_mid <= 0.98`.
        """
        tk = clean_ticks[idx]
        if tk.p_mid < 0.02 or tk.p_mid > 0.98:
            return None
        lock_days = max(1.0 / 1440.0, (float(contract.end_ts) - float(tk.ts)) / 86400.0)
        if prefer_pre_exit:
            eff_eval_days = min(lock_days, max(1.0 / 1440.0, max_hold_hours / 24.0))
        else:
            eff_eval_days = lock_days

        best_side: Optional[str] = None
        best_ev: float = -1.0

        for candidate_side in ("YES", "NO"):
            # Never buy YES on an augmented placeholder ("Other") leg (`RT-04` contract rule known at t=0!)
            if candidate_side == "YES" and semantics.is_placeholder_or_other:
                continue
            _, ask_px, slip_px = adapter.estimate_half_spread_and_slippage(
                contract, tk, candidate_side, notional_usd=6.50
            )
            if ask_px >= 0.985 or ask_px <= 0.012:
                continue
            gate = optimal_entry_threshold(
                p_yes_hat=clip_prob(p_yes_hat),
                sigma_p=sigma_p,
                entry_ask_price=ask_px,
                lockup_days=eff_eval_days,
                side=candidate_side,
                question_is_negated=False,
                sigma_k=sigma_k,
                entry_slippage_per_share=slip_px,
                fee_rate=contract.fee_rate,
                fee_exponent=contract.fee_exponent,
                p_uma_dispute=semantics.p_uma_dispute,
                r_opp_per_day=0.0015,
                min_net_edge_per_share=min_net_edge_ps,
                tick_size=contract.tick_size,
            )
            if gate["passes_entry_gate"] and gate["conservative_ev_econ_per_share"] > best_ev:
                best_ev = float(gate["conservative_ev_econ_per_share"])
                best_side = candidate_side

        if best_side is None:
            return None

        return DirectionalSignal(
            strategy_id=strategy_id,
            pillar=pillar,
            market_id=contract.market_id,
            event_id=contract.event_id,
            cluster_key=semantics.cluster_key,
            category=contract.category.upper(),
            side=best_side,
            entry_idx=idx,
            entry_ts=float(tk.ts),
            p_yes_market=float(tk.p_mid),
            p_yes_model=clip_prob(p_yes_hat),
            sigma_p=float(sigma_p),
            target_price_move=target_price_move,
            stop_price_move=stop_price_move,
            max_hold_hours=max_hold_hours,
            prefer_pre_exit=prefer_pre_exit,
            rationale=rationale,
            features_snapshot=features_snapshot or {},
        )


# ------------------------------------------------------------------------------
# MANDATORY SIMPLE BASELINES
# ------------------------------------------------------------------------------


class NaiveBuyNoBaseline(BaseDirectionalStrategy):
    """Mandatory Baseline B1: Unconditional Buy-NO (`q_mid >= 0.65`) hold-to-maturity benchmark."""

    strategy_id = "B1_NAIVE_BUY_NO"
    pillar = "BASELINE"
    description = "Unconditional Buy-NO whenever NO mid >= 0.65 at mid-trajectory (cost & skew benchmark)."

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 3:
            return []
        idx = len(clean_ticks) // 2
        tk = clean_ticks[idx]
        if (1.0 - tk.p_mid) < 0.65 or (1.0 - tk.p_mid) > 0.97:
            return []
        return [
            DirectionalSignal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                market_id=contract.market_id,
                event_id=contract.event_id,
                cluster_key=semantics.cluster_key,
                category=contract.category.upper(),
                side="NO",
                entry_idx=idx,
                entry_ts=float(tk.ts),
                p_yes_market=float(tk.p_mid),
                p_yes_model=clip_prob(max(0.005, tk.p_mid - 0.03)),
                sigma_p=0.05,
                rationale="Naive unconditional Buy-NO baseline",
            )
        ]


class NaiveBuyFavoriteBaseline(BaseDirectionalStrategy):
    """Mandatory Baseline B2: Unconditional Buy-Favorite (`max(p_yes, p_no) in [0.70, 0.96]`)."""

    strategy_id = "B2_NAIVE_BUY_FAVORITE"
    pillar = "BASELINE"
    description = "Unconditional Buy-Favorite (YES or NO >= 0.70) benchmark."

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 3:
            return []
        idx = len(clean_ticks) // 2
        tk = clean_ticks[idx]
        side = "YES" if tk.p_mid >= 0.5 else "NO"
        fav_p = tk.p_mid if side == "YES" else (1.0 - tk.p_mid)
        if fav_p < 0.70 or fav_p > 0.96:
            return []
        if side == "YES" and semantics.is_placeholder_or_other:
            return []
        naive_p_yes = min(0.995, tk.p_mid + 0.03) if side == "YES" else max(0.005, tk.p_mid - 0.03)
        return [
            DirectionalSignal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                market_id=contract.market_id,
                event_id=contract.event_id,
                cluster_key=semantics.cluster_key,
                category=contract.category.upper(),
                side=side,
                entry_idx=idx,
                entry_ts=float(tk.ts),
                p_yes_market=float(tk.p_mid),
                p_yes_model=clip_prob(naive_p_yes),
                sigma_p=0.05,
                rationale="Naive unconditional Buy-Favorite baseline",
            )
        ]


# ------------------------------------------------------------------------------
# PILLAR 1 — PRICE-BASED STRATEGIES
# ------------------------------------------------------------------------------


class ProbMomentumTrendStrategy(BaseDirectionalStrategy):
    """Pillar 1A: Causal Kalman-filtered probability momentum / gradual information diffusion.

    Captures sustained multi-step drift in `0%`-fee / multi-hour contracts where retail
    updates slowly to accumulating information (explicitly blocking `<4h` high-fee subhourly
    crypto churn per Dominus `SLEEVE_1_SUBHOURLY_15M` post-mortem!).
    """

    strategy_id = "P1_PROB_MOMENTUM_TREND"
    pillar = "PILLAR_1_PRICE"
    description = "Kalman-filtered log-odds trend continuation on >=4h horizons (YES & NO)."
    default_prefer_pre_exit = True

    def __init__(self) -> None:
        self._kalman = SequentialLogOddsKalman(process_var_per_hour=0.04, base_obs_var=0.05)

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 7:
            return []
        ts_arr = [t.ts for t in clean_ticks]
        p_arr = [t.p_mid for t in clean_ticks]
        kp, kv, ksig = self._kalman.filter_trajectory(ts_arr, p_arr)

        for idx in range(6, len(clean_ticks)):
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx, kp, kv)
            # Never churn short-horizon (<4h) or sub-12h high-fee crypto speedbump markets!
            if feats["tte_hours"] < 4.0 or (contract.fee_rate >= 0.07 and feats["tte_hours"] < 12.0):
                continue
            pm = feats["p_market"]
            if not (0.14 <= pm <= 0.86):
                continue
            dz_m = feats["dz_med"]
            dz_s = feats["dz_short"]
            # Require consistent sign across medium, short, and Kalman velocity without parabolic exhaustion
            if abs(dz_m) >= 0.32 and (dz_m * dz_s > 0.0) and (dz_m * kv[idx] > 0.0) and feats["vol_ratio"] <= 1.8:
                continuation_shift = max(-0.38, min(0.38, 0.28 * dz_m))
                p_hat = sigmoid(logit(pm) + continuation_shift)
                sig = self._gate_and_build_signal(
                    strategy_id=self.strategy_id,
                    pillar=self.pillar,
                    contract=contract,
                    semantics=semantics,
                    clean_ticks=clean_ticks,
                    idx=idx,
                    p_yes_hat=p_hat,
                    sigma_p=max(0.025, ksig[idx]),
                    adapter=adapter,
                    min_net_edge_ps=0.015,
                    sigma_k=0.70,
                    target_price_move=0.065,
                    stop_price_move=0.075,
                    max_hold_hours=36.0,
                    prefer_pre_exit=True,
                    rationale=f"Steady log-odds drift dz_med={dz_m:+.3f}, kalman_vel={kv[idx]:+.3f}",
                )
                if sig is not None:
                    return [sig]  # Max 1 independent entry per contract to prevent correlated spam
        return []


class ShortHorizonOverreactionStrategy(BaseDirectionalStrategy):
    """Pillar 1B: Short-horizon retail spike mean reversion (`TTE >= 24h`, `0%`-fee preferred)."""

    strategy_id = "P1_SHORT_OVERREACTION_REVERSION"
    pillar = "PILLAR_1_PRICE"
    description = "Fades abrupt short-window retail overreaction spikes on long-TTE contracts."
    default_prefer_pre_exit = True

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 8:
            return []
        for idx in range(6, len(clean_ticks)):
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx)
            # Only fade spikes when substantial time (>24h) remains so true terminal jumps aren't faded!
            if feats["tte_hours"] < 24.0:
                continue
            pm = feats["p_market"]
            dp_s = feats["dp_short"]
            dz_s = feats["dz_short"]
            prior_drift = feats["dz_long"] - dz_s
            # Abrupt jump (>= 11c in 2 steps) out of a previously calm regime
            if abs(dp_s) >= 0.11 and abs(prior_drift) <= 0.30 and 0.12 <= pm <= 0.88:
                reversion_shift = -0.38 * dz_s
                p_hat = sigmoid(logit(pm) + max(-0.45, min(0.45, reversion_shift)))
                sig = self._gate_and_build_signal(
                    strategy_id=self.strategy_id,
                    pillar=self.pillar,
                    contract=contract,
                    semantics=semantics,
                    clean_ticks=clean_ticks,
                    idx=idx,
                    p_yes_hat=p_hat,
                    sigma_p=0.035,
                    adapter=adapter,
                    min_net_edge_ps=0.016,
                    sigma_k=0.65,
                    target_price_move=0.055,
                    stop_price_move=0.085,
                    max_hold_hours=24.0,
                    prefer_pre_exit=True,
                    rationale=f"Abrupt retail spike dp_short={dp_s:+.3f} on TTE={feats['tte_hours']:.1f}h",
                )
                if sig is not None:
                    return [sig]
        return []


class VolatilityExpansionBreakoutStrategy(BaseDirectionalStrategy):
    """Pillar 1C: Quiet-range compression followed by directional volatility breakout."""

    strategy_id = "P1_VOL_EXPANSION_BREAKOUT"
    pillar = "PILLAR_1_PRICE"
    description = "Trades breakouts out of multi-period low-volatility compression bands."
    default_prefer_pre_exit = True

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 12:
            return []
        for idx in range(10, len(clean_ticks)):
            window_prev = [clean_ticks[k].p_mid for k in range(idx - 9, idx - 1)]
            hi_prev = max(window_prev)
            lo_prev = min(window_prev)
            band_width = hi_prev - lo_prev
            pm = clean_ticks[idx].p_mid
            tte_h = (float(contract.end_ts) - float(clean_ticks[idx].ts)) / 3600.0
            if tte_h < 6.0 or band_width > 0.06 or band_width < 0.005:
                continue
            # Clean breakout >= 3.5c outside prior 8-bar compression box
            if pm >= hi_prev + 0.035 and pm <= 0.85:
                p_hat = min(0.92, pm + 0.055)
            elif pm <= lo_prev - 0.035 and pm >= 0.15:
                p_hat = max(0.08, pm - 0.055)
            else:
                continue
            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_hat,
                sigma_p=0.03,
                adapter=adapter,
                min_net_edge_ps=0.014,
                sigma_k=0.65,
                target_price_move=0.06,
                stop_price_move=0.06,
                max_hold_hours=24.0,
                prefer_pre_exit=True,
                rationale=f"Compression band={band_width:.3f} breakout to p={pm:.3f}",
            )
            if sig is not None:
                return [sig]
        return []


class OrderBookImbalanceFlowStrategy(BaseDirectionalStrategy):
    """Pillar 1D: Observed L2 Order-Book Imbalance & Signed Trade-Flow Pressure.

    Strictly honors Dominus Missing-Feature Hygiene: ONLY fires on ticks carrying genuine
    observed `obi_l1` or `trade_flow_imbalance` (`OBSERVED_EXECUTABLE_L2`), never fabricating
    synthetic orderbook imbalance on historical price-only series!
    """

    strategy_id = "P1_L2_OBI_FLOW_PRESSURE"
    pillar = "PILLAR_1_PRICE"
    description = "Observed L2 depth imbalance + trade-flow pressure (abstains when L2 absent)."
    default_prefer_pre_exit = True

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        for idx, tk in enumerate(clean_ticks):
            if tk.obi_l1 is None and tk.trade_flow_imbalance is None:
                continue
            obi = float(tk.obi_l1 or 0.0)
            tfi = float(tk.trade_flow_imbalance or obi)
            if abs(obi) < 0.35 or (obi * tfi < 0.0):
                continue
            pm = clip_prob(tk.p_mid)
            if not (0.12 <= pm <= 0.88):
                continue
            composite = 0.60 * obi + 0.40 * tfi
            p_hat = sigmoid(logit(pm) + max(-0.35, min(0.35, 0.42 * composite)))
            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_hat,
                sigma_p=0.025,
                adapter=adapter,
                min_net_edge_ps=0.012,
                sigma_k=0.60,
                target_price_move=0.045,
                stop_price_move=0.055,
                max_hold_hours=6.0,
                prefer_pre_exit=True,
                rationale=f"Observed L2 OBI={obi:+.3f}, TFI={tfi:+.3f}",
            )
            if sig is not None:
                return [sig]
        return []


class BoundaryTrendExhaustionStrategy(BaseDirectionalStrategy):
    """Pillar 1E: Parabolic Trend Exhaustion Near `[0, 1]` Boundaries on Long-Horizon Markets.

    When retail momentum pushes a contract with `>= 48h` remaining rapidly into `[0.87, 0.94]`
    or `[0.06, 0.13]`, upside is capped (`+6c..+13c`) while any uncertainty return yields
    convex `2x–4x` repricing on the cheap contrarian token (`NO` at `6c–13c` or `YES` at `6c–13c`).
    """

    strategy_id = "P1_BOUNDARY_TREND_EXHAUSTION"
    pillar = "PILLAR_1_PRICE"
    description = "Convex contrarian fade of parabolic boundary pushes when TTE >= 48h."
    default_prefer_pre_exit = True

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 8:
            return []
        for idx in range(6, len(clean_ticks)):
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx)
            if feats["tte_hours"] < 48.0:
                continue
            pm = feats["p_market"]
            dp_m = feats["dp_med"]
            if 0.87 <= pm <= 0.945 and dp_m >= 0.14:
                # Over-extended near upper ceiling -> convex cheap NO exposure
                p_hat = pm - 0.055
            elif 0.055 <= pm <= 0.13 and dp_m <= -0.14 and not semantics.is_placeholder_or_other:
                # Over-extended panic near zero -> convex cheap YES exposure
                p_hat = pm + 0.055
            else:
                continue
            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_hat,
                sigma_p=0.025,
                adapter=adapter,
                min_net_edge_ps=0.015,
                sigma_k=0.60,
                target_price_move=0.06,
                stop_price_move=0.05,
                max_hold_hours=48.0,
                prefer_pre_exit=True,
                rationale=f"Parabolic boundary exhaustion p={pm:.3f}, dp_med={dp_m:+.3f}, TTE={feats['tte_hours']:.0f}h",
            )
            if sig is not None:
                return [sig]
        return []


# ------------------------------------------------------------------------------
# PILLAR 2 — PREDICTION & INFORMATION STRATEGIES
# ------------------------------------------------------------------------------


def _student_t_nu5_cdf(z: float) -> float:
    """Exact closed-form CDF of standardized Student-t(nu=5) distribution (unit variance).

    Captures heavy crypto log-return tails far more realistically than thin-tailed Gaussian!
    For standard t_5 (Var = 5/(5-2) = 5/3), scale unit-variance `z` by `t = z * sqrt(5/3)`.
    Exact formula for nu=5:
        F(t) = 0.5 + (1/pi) * [ atan(t/sqrt(5)) + (t*sqrt(5))/(5 + t^2) * (1 + 2/(3*(1 + t^2/5))) ]
    """
    t = float(z) * math.sqrt(5.0 / 3.0)
    u = t / math.sqrt(5.0)
    denom = 1.0 + u * u
    term = math.atan(u) + (u / denom) * (1.0 + (2.0 / (3.0 * denom)))
    return clip_prob(0.5 + term / math.pi, 1e-5)


class CryptoSpotVolBarrierModelStrategy(BaseDirectionalStrategy):
    """Pillar 2A: CEX Spot/Vol Empirical Student-t(`nu=5`) Digital & First-Passage Barrier Model.

    Computes structural model probability `p_model` from observed external CEX spot `S_t`,
    annualized realized volatility `sigma_ann`, and contract strike `K` across:
    - `ABOVE_STRIKE` / `BELOW_STRIKE` terminal digitals, AND
    - `ONE_TOUCH_UP` / `ONE_TOUCH_DOWN` continuous barrier reflection (`P_touch ~= 2 * P_digital`
      with jump/wick adjustment per Dominus `barrier_onetouch_svi_engine.py`).
    Requires high net edge above Polymarket's `7%` curved crypto taker fee (`RT-03`).
    """

    strategy_id = "P2_CRYPTO_SPOT_VOL_BARRIER"
    pillar = "PILLAR_2_INFORMATION"
    description = "Student-t(nu=5) CEX spot/vol barrier & strike digital mispricing vs CLOB."

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if contract.category.upper() != "CRYPTO" or semantics.extracted_strike is None:
            return []
        strike = float(semantics.extracted_strike)
        if strike <= 0.0:
            return []

        for idx, tk in enumerate(clean_ticks):
            if tk.external_spot is None or float(tk.external_spot) <= 0.0:
                continue
            spot = float(tk.external_spot)
            vol_ann = float(tk.external_vol_annual or 0.58)
            tte_years = max(1.0 / (365.25 * 24.0), (float(contract.end_ts) - float(tk.ts)) / (365.25 * 86400.0))
            tte_hours = tte_years * 365.25 * 24.0
            # Avoid <2h ultra-short fee trap
            if tte_hours < 2.5:
                continue

            sig_t = max(0.005, vol_ann * math.sqrt(tte_years))
            d_log = (math.log(spot / strike) - 0.5 * (sig_t ** 2)) / sig_t

            if semantics.semantics_type == "ABOVE_STRIKE":
                p_aff = _student_t_nu5_cdf(d_log)
            elif semantics.semantics_type == "BELOW_STRIKE":
                p_aff = _student_t_nu5_cdf(-d_log)
            elif semantics.semantics_type == "ONE_TOUCH_UP":
                p_aff = 0.995 if spot >= strike else min(0.99, 2.08 * _student_t_nu5_cdf(d_log))
            elif semantics.semantics_type == "ONE_TOUCH_DOWN":
                p_aff = 0.995 if spot <= strike else min(0.99, 2.08 * _student_t_nu5_cdf(-d_log))
            else:
                continue

            _, p_yes_mod, _ = resolve_side_probability(
                p_aff, side="YES", question_is_negated=semantics.question_is_negated
            )
            # Blend 70% structural CEX model + 30% market prior for conservative skew calibration
            p_blended = sigmoid(0.70 * logit(p_yes_mod) + 0.30 * logit(tk.p_mid))

            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_blended,
                sigma_p=0.035,
                adapter=adapter,
                min_net_edge_ps=0.022,  # Strict hurdle above 7% crypto fee curve!
                sigma_k=0.75,
                target_price_move=0.08,
                stop_price_move=0.09,
                max_hold_hours=24.0,
                prefer_pre_exit=False,
                rationale=f"Spot={spot:.2f} vs K={strike:.2f}, p_mod={p_blended:.3f} vs mkt={tk.p_mid:.3f}",
            )
            if sig is not None:
                return [sig]
        return []


class WeatherForecastCalibrationStrategy(BaseDirectionalStrategy):
    """Pillar 2B: Weather NWP Forecast Error Calibration + `D-006` Sensor Maintenance Guard.

    Evaluates `0%`-fee weather temperature bucket (`RANGE_BUCKET`) and threshold contracts
    against external Open-Meteo/NOAA forecast `weather_forecast_c` with:
    - Horizon-dependent forecast error `sigma_c = sqrt(0.55^2 + (1.10 + 0.45 * tte_days)^2)`
      incorporating Dominus `D-006` `±0.55°C` sensor rounding interval.
    - Hard block whenever `weather_has_maintenance_flag == True` (ASOS `$` outage lesson!).
    - Truncation of impossible lower brackets when intraday `weather_obs_max_c` already
      exceeds `bucket_high + 0.55°C`.
    """

    strategy_id = "P2_WEATHER_FORECAST_CALIBRATION"
    pillar = "PILLAR_2_INFORMATION"
    description = "NWP forecast error calibration + sensor-rounding cushion on 0%-fee weather."

    @staticmethod
    def _norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x * 0.7071067811865475))

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if contract.category.upper() != "WEATHER":
            return []
        for idx, tk in enumerate(clean_ticks):
            # Binding D-006 Rule: NEVER trade intraday weather with ASOS $ maintenance flag!
            if tk.weather_has_maintenance_flag:
                continue
            if tk.weather_forecast_c is None:
                continue

            fc_c = float(tk.weather_forecast_c)
            tte_days = max(0.05, (float(contract.end_ts) - float(tk.ts)) / 86400.0)
            sigma_c = math.sqrt(0.55 ** 2 + (1.05 + 0.45 * min(7.0, tte_days)) ** 2)

            if semantics.extracted_range is not None:
                lo_b, hi_b = semantics.extracted_range
                # Convert °F contract bounds to °C if forecast is in °C and bounds look like °F (>48)
                if hi_b > 48.0 and fc_c < 45.0:
                    lo_c = (lo_b - 32.0) * (5.0 / 9.0)
                    hi_c = (hi_b - 32.0) * (5.0 / 9.0)
                else:
                    lo_c, hi_c = lo_b, hi_b
                if tk.weather_obs_max_c is not None and float(tk.weather_obs_max_c) > hi_c + 0.55:
                    p_aff = 0.015
                else:
                    p_aff = max(
                        0.005,
                        self._norm_cdf((hi_c + 0.30 - fc_c) / sigma_c)
                        - self._norm_cdf((lo_c - 0.30 - fc_c) / sigma_c),
                    )
            elif semantics.extracted_strike is not None and semantics.semantics_type in (
                "ABOVE_STRIKE",
                "BELOW_STRIKE",
            ):
                st = float(semantics.extracted_strike)
                st_c = ((st - 32.0) * 5.0 / 9.0) if (st > 48.0 and fc_c < 45.0) else st
                if semantics.semantics_type == "BELOW_STRIKE":
                    p_aff = self._norm_cdf((st_c - fc_c) / sigma_c)
                else:
                    p_aff = 1.0 - self._norm_cdf((st_c - fc_c) / sigma_c)
            else:
                continue

            _, p_yes_mod, _ = resolve_side_probability(
                p_aff, side="YES", question_is_negated=semantics.question_is_negated
            )
            p_blended = clip_prob(0.75 * p_yes_mod + 0.25 * tk.p_mid)
            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_blended,
                sigma_p=0.03,
                adapter=adapter,
                min_net_edge_ps=0.018,
                sigma_k=0.80,
                target_price_move=0.07,
                stop_price_move=0.08,
                max_hold_hours=36.0,
                prefer_pre_exit=False,
                rationale=f"Weather fc={fc_c:.1f}C, sigma={sigma_c:.2f}C, p_mod={p_blended:.3f} vs mkt={tk.p_mid:.3f}",
            )
            if sig is not None:
                return [sig]
        return []


class NegRiskSlateRelativeValueStrategy(BaseDirectionalStrategy):
    """Pillar 2C: Multi-Outcome / NegRisk Slate Sum-of-Parts Directional Disagreement.

    When a multi-outcome event slate exhibits substantial YES overround (`slate_sum_yes_mid > 1.05`,
    common on 6–25 outcome Politics, Sports futures, Culture, and Weather slates where retail
    overbids multiple narrative longshots simultaneously), normalizes the implied partition
    distribution `p_norm = p_i / sum_j p_j` (with power-law longshot deflation) to buy
    underpriced `NO` on bloated secondary legs WITHOUT needing N-leg sequential basket execution!
    """

    strategy_id = "P2_NEGRISK_SLATE_RELATIVE_VALUE"
    pillar = "PILLAR_2_INFORMATION"
    description = "Single-leg directional relative value on over-inflated multi-outcome NegRisk slates."

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if not contract.neg_risk and clean_ticks and clean_ticks[0].slate_sum_yes_mid is None:
            return []
        for idx, tk in enumerate(clean_ticks):
            if tk.slate_sum_yes_mid is None:
                continue
            sum_yes = float(tk.slate_sum_yes_mid)
            pm = clip_prob(tk.p_mid)
            # Case 1: Bloated slate overround (sum_yes >= 1.055) -> secondary legs (4c-35c) are overpriced -> Buy NO
            if sum_yes >= 1.055 and 0.04 <= pm <= 0.35:
                # Power-law proportional normalization deflates longshot inflation more than favorites
                p_norm = (pm ** 1.12) / max(1.0, sum_yes)
                p_hat = clip_prob(0.80 * p_norm + 0.20 * (pm / sum_yes))
            # Case 2: Non-augmented slate underround (sum_yes <= 0.945) on leading leg -> Buy YES
            elif sum_yes <= 0.945 and not contract.neg_risk_augmented and not semantics.is_placeholder_or_other and 0.25 <= pm <= 0.80:
                p_hat = clip_prob(pm / max(0.75, sum_yes))
            else:
                continue

            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_hat,
                sigma_p=0.022,
                adapter=adapter,
                min_net_edge_ps=0.014,
                sigma_k=0.75,
                target_price_move=0.05,
                stop_price_move=0.07,
                max_hold_hours=72.0,
                prefer_pre_exit=False,
                rationale=f"Slate sum_yes={sum_yes:.3f}, contract p_mid={pm:.3f} -> normalized p_hat={p_hat:.3f}",
            )
            if sig is not None:
                return [sig]
        return []


class ScheduledMacroSportsDriftStrategy(BaseDirectionalStrategy):
    """Pillar 2D: Pre- vs Event-Window Information Drift in Macro, Politics & Sports.

    Targets `0%`-fee scheduled-catalyst categories (`ECONOMICS`, `MACRO`, `POLITICS`, `FINANCE`,
    `GEOPOLITICS`, `0%`-fee `SPORTS`) entering their `6h–48h` pre-resolution catalyst window
    when informed positioning steadily shifts odds away from stale early retail anchors.
    """

    strategy_id = "P2_SCHEDULED_MACRO_SPORTS_DRIFT"
    pillar = "PILLAR_2_INFORMATION"
    description = "Catalyst-window (6h-48h TTE) informed positioning drift in Macro/Politics/Sports."

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        cat = contract.category.upper()
        if cat not in ("ECONOMICS", "MACRO", "POLITICS", "FINANCE", "GEOPOLITICS", "SPORTS"):
            return []
        if len(clean_ticks) < 6:
            return []

        for idx in range(5, len(clean_ticks)):
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx)
            if not (6.0 <= feats["tte_hours"] <= 48.0):
                continue
            pm = feats["p_market"]
            dz_l = feats["dz_long"]
            dz_m = feats["dz_med"]
            # Informed pre-catalyst drift into [0.62, 0.88] or [0.12, 0.38]
            if pm >= 0.62 and pm <= 0.88 and dz_l >= 0.25 and dz_m >= 0.10:
                p_hat = sigmoid(logit(pm) + 0.24)
            elif pm <= 0.38 and pm >= 0.12 and dz_l <= -0.25 and dz_m <= -0.10:
                p_hat = sigmoid(logit(pm) - 0.24)
            else:
                continue

            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_hat,
                sigma_p=0.025,
                adapter=adapter,
                min_net_edge_ps=0.014,
                sigma_k=0.70,
                target_price_move=0.06,
                stop_price_move=0.08,
                max_hold_hours=36.0,
                prefer_pre_exit=False,
                rationale=f"Catalyst window ({feats['tte_hours']:.1f}h) informed drift dz_long={dz_l:+.3f}",
            )
            if sig is not None:
                return [sig]
        return []


# ------------------------------------------------------------------------------
# PILLAR 3 — MARKET-BEHAVIOR STRATEGIES
# ------------------------------------------------------------------------------


class FavoriteLongshotBiasStrategy(BaseDirectionalStrategy):
    """Pillar 3A: Empirical Favorite–Longshot Bias & Retail YES-Lottery Deflation (`Buy NO`).

    Across prediction markets, retail traders systematically overpay for `2c–10c` "narrative
    YES" longshots (elections, geopolitics headlines, cultural events, extreme targets) while
    underpricing `90c–98c` `NO` carry due to capital lockup & skewness preferences.
    - Fits empirical Beta-shrunk longshot deflation by category STRICTLY on the Train split!
    - Enforces `0%`-fee (or low-fee), `TTE <= 21d` velocity filter (avoiding 6-month dead capital!),
      and explicit UMA dispute haircut (`RT-08` negative-skew awareness).
    """

    strategy_id = "P3_FAVORITE_LONGSHOT_NO_BIAS"
    pillar = "PILLAR_3_BEHAVIORAL"
    description = "Train-calibrated Favorite-Longshot bias harvesting 0%-fee NO carry on <=21d horizons."

    def __init__(self) -> None:
        self._cat_longshot_delta_logit: Dict[str, float] = {}
        self._global_longshot_delta: float = -0.35

    def fit(self, train_contracts: Sequence[MarketContractRecord]) -> "FavoriteLongshotBiasStrategy":
        cat_stats: Dict[str, List[float]] = collections.defaultdict(lambda: [0.0, 0.0, 0.0])  # [sum_y, n, sum_pm]
        g_y = g_n = g_pm = 0.0
        for c in train_contracts:
            if c.resolved_outcome_yes not in (0, 1):
                continue
            ticks, _ = sanitize_causal_trajectory(c)
            if not ticks:
                continue
            tk = ticks[len(ticks) // 2]
            if 0.02 <= tk.p_mid <= 0.12:
                cat = c.category.upper()
                y = float(c.resolved_outcome_yes)
                cat_stats[cat][0] += y
                cat_stats[cat][1] += 1.0
                cat_stats[cat][2] += tk.p_mid
                g_y += y
                g_n += 1.0
                g_pm += tk.p_mid

        if g_n >= 10.0:
            mean_pm = g_pm / g_n
            emp_rate = (20.0 * mean_pm + g_y) / (20.0 + g_n)
            self._global_longshot_delta = max(-0.90, min(0.20, logit(emp_rate) - logit(mean_pm)))

        self._cat_longshot_delta_logit.clear()
        for cat, (sy, sn, spm) in cat_stats.items():
            if sn >= 5.0:
                m_pm = spm / sn
                prior_p = sigmoid(logit(m_pm) + self._global_longshot_delta)
                post_p = (15.0 * prior_p + sy) / (15.0 + sn)
                self._cat_longshot_delta_logit[cat] = max(-1.0, min(0.25, logit(post_p) - logit(m_pm)))
        return self

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if not clean_ticks:
            return []
        cat = contract.category.upper()
        delta_logit = self._cat_longshot_delta_logit.get(cat, self._global_longshot_delta)
        if delta_logit >= -0.08:
            return []

        for idx in range(min(2, len(clean_ticks) - 1), len(clean_ticks)):
            tk = clean_ticks[idx]
            tte_days = (float(contract.end_ts) - float(tk.ts)) / 86400.0
            # Velocity bound: <= 21 days to settlement so dollar-days aren't trapped for months
            if not (0.25 <= tte_days <= 21.0):
                continue
            pm = clip_prob(tk.p_mid)
            if 0.025 <= pm <= 0.11:
                p_hat = sigmoid(logit(pm) + delta_logit)
                sig = self._gate_and_build_signal(
                    strategy_id=self.strategy_id,
                    pillar=self.pillar,
                    contract=contract,
                    semantics=semantics,
                    clean_ticks=clean_ticks,
                    idx=idx,
                    p_yes_hat=p_hat,
                    sigma_p=0.012,
                    adapter=adapter,
                    min_net_edge_ps=0.008,
                    sigma_k=0.80,
                    target_price_move=0.035,
                    stop_price_move=0.12,
                    max_hold_hours=min(504.0, tte_days * 24.0),
                    prefer_pre_exit=False,
                    rationale=f"Longshot YES={pm:.3f} in {cat} (delta_logit={delta_logit:+.2f}) -> Buy NO",
                )
                if sig is not None and sig.side == "NO":
                    return [sig]
        return []


class CrowdJumpRegimeStrategy(BaseDirectionalStrategy):
    """Pillar 3B: TTE-Conditioned Crowd Jump Response (`|dp| >= 0.09`).

    Tests the behavioral hypothesis that:
    - Far from expiry (`TTE > 48h`), sudden `>= 9c` jumps in Politics/Culture/Macro partially
      mean-revert as headline excitement cools (`PRE_EXIT`), WHEREAS
    - Near expiry (`3h <= TTE <= 18h`), `>= 9c` jumps reflect genuine resolving news that
      crowd anchoring *under-reacts* to (`CONTINUATION`).
    """

    strategy_id = "P3_CROWD_JUMP_REGIME"
    pillar = "PILLAR_3_BEHAVIORAL"
    description = "TTE-conditioned crowd jump response: >48h partial reversion vs <=18h continuation."
    default_prefer_pre_exit = True

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 5:
            return []
        for idx in range(3, len(clean_ticks)):
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx)
            dp_s = feats["dp_short"]
            if abs(dp_s) < 0.09:
                continue
            pm = feats["p_market"]
            if not (0.10 <= pm <= 0.90):
                continue
            tte_h = feats["tte_hours"]
            if tte_h >= 48.0:
                # Headline overreaction regime -> partial reversion
                p_hat = clip_prob(pm - 0.35 * dp_s)
                mode_lbl = "LONG_TTE_REVERSION"
                pref_exit = True
            elif 3.0 <= tte_h <= 18.0:
                # Near-resolution news underreaction -> continuation
                p_hat = clip_prob(pm + 0.30 * dp_s)
                mode_lbl = "NEAR_TTE_CONTINUATION"
                pref_exit = False
            else:
                continue

            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_hat,
                sigma_p=0.03,
                adapter=adapter,
                min_net_edge_ps=0.015,
                sigma_k=0.65,
                target_price_move=0.055,
                stop_price_move=0.08,
                max_hold_hours=18.0,
                prefer_pre_exit=pref_exit,
                rationale=f"{mode_lbl}: dp_short={dp_s:+.3f}, TTE={tte_h:.1f}h",
            )
            if sig is not None:
                return [sig]
        return []


class LateStageConvergenceStrategy(BaseDirectionalStrategy):
    """Pillar 3C: Pre-Clinch Objective Late-Stage Probability Convergence (`85c–95c`).

    Targets objective-rule contracts in the final `4h–48h` BEFORE clinch (`sanitize_causal_trajectory`
    guarantees `p < 0.985` pre-absorption!) where capital-locked holders sell `85c–95c` winners
    at a liquidity discount to free collateral. Directly enables clean comparison of
    Hold-to-Settlement vs `$0.975–$0.985` Pre-Resolution Cash Recycling!
    """

    strategy_id = "P3_LATE_CONVERGENCE_OBJECTIVE"
    pillar = "PILLAR_3_BEHAVIORAL"
    description = "Objective-oracle pre-clinch 85c-95c convergence (4h-48h TTE, zero post-clinch leakage)."

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if not semantics.is_objective_oracle or len(clean_ticks) < 5:
            return []
        for idx in range(4, len(clean_ticks)):
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx)
            if not (4.0 <= feats["tte_hours"] <= 48.0):
                continue
            pm = feats["p_market"]
            # Require stable low-volatility convergence toward either 1.0 (YES in 85c-95c) or 0.0 (NO in 85c-95c)
            if 0.85 <= pm <= 0.95 and feats["dp_med"] >= 0.01 and feats["vol_short"] <= 0.25:
                p_hat = min(0.982, pm + 0.038)
            elif 0.05 <= pm <= 0.15 and feats["dp_med"] <= -0.01 and feats["vol_short"] <= 0.25:
                p_hat = max(0.018, pm - 0.038)
            else:
                continue

            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_hat,
                sigma_p=0.014,
                adapter=adapter,
                min_net_edge_ps=0.009,
                sigma_k=0.75,
                target_price_move=0.03,
                stop_price_move=0.10,
                max_hold_hours=min(48.0, feats["tte_hours"]),
                prefer_pre_exit=False,
                rationale=f"Objective late-stage convergence p={pm:.3f}, TTE={feats['tte_hours']:.1f}h",
            )
            if sig is not None:
                return [sig]
        return []


class LiquidityShockDistortionStrategy(BaseDirectionalStrategy):
    """Pillar 3D: Temporary Single-Print / Thin-Book Liquidity Shock Snapback."""

    strategy_id = "P3_LIQUIDITY_SHOCK_SNAPBACK"
    pillar = "PILLAR_3_BEHAVIORAL"
    description = "Captures snapback after abrupt thin-book single-step price dislocations."
    default_prefer_pre_exit = True

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 6:
            return []
        for idx in range(4, len(clean_ticks)):
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx)
            if feats["tte_hours"] < 12.0:
                continue
            shock = feats["shock_dev"]
            pm = feats["p_market"]
            # Sharp single-tick deviation >= 7.5c from trailing 4-tick median
            if abs(shock) >= 0.075 and 0.10 <= pm <= 0.90:
                p_hat = clip_prob(pm - 0.55 * shock)
                sig = self._gate_and_build_signal(
                    strategy_id=self.strategy_id,
                    pillar=self.pillar,
                    contract=contract,
                    semantics=semantics,
                    clean_ticks=clean_ticks,
                    idx=idx,
                    p_yes_hat=p_hat,
                    sigma_p=0.028,
                    adapter=adapter,
                    min_net_edge_ps=0.014,
                    sigma_k=0.65,
                    target_price_move=0.045,
                    stop_price_move=0.075,
                    max_hold_hours=12.0,
                    prefer_pre_exit=True,
                    rationale=f"Liquidity shock dev={shock:+.3f} vs trailing local median",
                )
                if sig is not None:
                    return [sig]
        return []


# ------------------------------------------------------------------------------
# PILLAR 4 — ADVANCED QUANTITATIVE, BAYESIAN & ML STRATEGIES
# ------------------------------------------------------------------------------

ML_NUMERIC_FEATURES: Tuple[str, ...] = (
    "logit_p_market",
    "abs_dist_from_half",
    "is_longshot_yes",
    "is_favorite_yes",
    "log_tte_hours",
    "dp_short",
    "dp_med",
    "dz_short",
    "dz_med",
    "dz_long",
    "vol_short",
    "vol_ratio",
    "shock_dev",
    "kalman_resid",
    "kalman_vel",
    "obi_l1",
    "slate_overround_excess",
    "log_liquidity_usd",
    "fee_rate",
    "neg_risk",
)
ML_CATEGORICAL_FEATURES: Tuple[str, ...] = ("category", "semantics_type")


def _extract_training_panel(
    train_contracts: Sequence[MarketContractRecord],
) -> Tuple[List[Dict[str, Any]], List[int], List[float]]:
    """Extracts leak-free causal feature snapshots + cluster-inverse weights from Train contracts."""
    kalman = SequentialLogOddsKalman()
    rows: List[Dict[str, Any]] = []
    ys: List[int] = []
    cluster_keys: List[str] = []

    for c in train_contracts:
        if c.resolved_outcome_yes not in (0, 1):
            continue
        sem = parse_contract_semantics(c)
        if sem.is_disputed_or_void:
            continue
        ticks, _ = sanitize_causal_trajectory(c)
        if len(ticks) < 3:
            continue
        kp, kv, _ = kalman.filter_trajectory([t.ts for t in ticks], [t.p_mid for t in ticks])
        # Sample up to 2 causal interior points (35% and 70% of pre-clinch trajectory) per contract
        sample_indices = sorted({max(1, int(0.35 * len(ticks))), max(1, int(0.70 * len(ticks)))})
        for idx in sample_indices:
            if idx < len(ticks):
                feats = extract_causal_tick_features(c, sem, ticks, idx, kp, kv)
                rows.append(feats)
                ys.append(int(c.resolved_outcome_yes))
                cluster_keys.append(sem.cluster_key)

    counts = collections.Counter(cluster_keys)
    weights = [1.0 / max(1, counts[ck]) for ck in cluster_keys]
    return rows, ys, weights


class BayesianSequentialUpdaterStrategy(BaseDirectionalStrategy):
    """Pillar 4A: Hierarchical Empirical-Bayes Beta + Sequential Log-Odds Kalman Strategy."""

    strategy_id = "P4_BAYESIAN_SEQUENTIAL_LOGODDS"
    pillar = "PILLAR_4_QUANT_ML"
    description = "Hierarchical Bayesian Beta-Binomial calibration + Kalman trajectory filter."

    def __init__(self) -> None:
        self.bayes = BayesianBetaCalibrationModel(prior_strength=22.0)
        self.kalman = SequentialLogOddsKalman()

    def fit(self, train_contracts: Sequence[MarketContractRecord]) -> "BayesianSequentialUpdaterStrategy":
        rows, ys, ws = _extract_training_panel(train_contracts)
        self.bayes.fit(rows, ys, sample_weights=ws)
        return self

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 3 or not self.bayes.fitted:
            return []
        kp, kv, ksig = self.kalman.filter_trajectory(
            [t.ts for t in clean_ticks], [t.p_mid for t in clean_ticks]
        )
        # Evaluate candidate checkpoints without spamming correlated intra-contract retries
        checkpoints = sorted({len(clean_ticks) // 3, (2 * len(clean_ticks)) // 3, len(clean_ticks) - 1})
        for idx in checkpoints:
            if idx < 1 or idx >= len(clean_ticks):
                continue
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx, kp, kv)
            p_b, sig_b = self.bayes.predict_with_uncertainty(feats)
            # Combine hierarchical category/bin Bayesian calibration with filtered Kalman state
            p_comb = sigmoid(0.70 * logit(p_b) + 0.30 * logit(kp[idx]))
            sig_comb = math.sqrt(0.5 * sig_b * sig_b + 0.5 * ksig[idx] * ksig[idx])
            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_comb,
                sigma_p=sig_comb,
                adapter=adapter,
                min_net_edge_ps=0.011,
                sigma_k=0.80,
                target_price_move=0.05,
                stop_price_move=0.09,
                max_hold_hours=48.0,
                prefer_pre_exit=False,
                rationale=f"Bayes p={p_b:.3f}, Kalman p={kp[idx]:.3f} vs mkt={feats['p_market']:.3f}",
            )
            if sig is not None:
                return [sig]
        return []


class CalibratedLogisticResidualStrategy(BaseDirectionalStrategy):
    """Pillar 4B: L2-Regularized Market-Offset Logistic Regression + Platt Calibration."""

    strategy_id = "P4_CALIBRATED_LOGISTIC_RESIDUAL"
    pillar = "PILLAR_4_QUANT_ML"
    description = "Train-only standardized L2 Logistic residual over logit(p_market) + Platt calibration."

    def __init__(self, l2_lambda: float = 6.0) -> None:
        self.l2_lambda = float(l2_lambda)
        self.prep = CausalFeaturePreprocessor(
            numeric_cols=list(ML_NUMERIC_FEATURES),
            categorical_cols=list(ML_CATEGORICAL_FEATURES),
        )
        self.model = RegularizedLogisticRegression(
            l2_lambda=self.l2_lambda, use_market_offset=True, calibration="platt"
        )
        self.kalman = SequentialLogOddsKalman()

    def fit(self, train_contracts: Sequence[MarketContractRecord]) -> "CalibratedLogisticResidualStrategy":
        rows, ys, ws = _extract_training_panel(train_contracts)
        self.prep.fit(rows, split_tag="TRAIN_ONLY")
        X = self.prep.transform(rows)
        pm = [float(r["p_market"]) for r in rows]
        self.model.fit(X, ys, market_probs=pm, sample_weights=ws)
        return self

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 3 or not self.model.fitted or not self.prep.fitted:
            return []
        kp, kv, _ = self.kalman.filter_trajectory(
            [t.ts for t in clean_ticks], [t.p_mid for t in clean_ticks]
        )
        checkpoints = sorted({len(clean_ticks) // 3, (2 * len(clean_ticks)) // 3, len(clean_ticks) - 1})
        for idx in checkpoints:
            if idx < 1 or idx >= len(clean_ticks):
                continue
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx, kp, kv)
            x_vec = self.prep.transform_one(feats)
            p_hat, sig_p = self.model.predict_with_uncertainty(x_vec, feats["p_market"])
            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=p_hat,
                sigma_p=sig_p,
                adapter=adapter,
                min_net_edge_ps=0.012,
                sigma_k=0.80,
                target_price_move=0.055,
                stop_price_move=0.09,
                max_hold_hours=48.0,
                prefer_pre_exit=False,
                rationale=f"L2-LogReg Platt p_hat={p_hat:.3f} (sigma={sig_p:.3f}) vs mkt={feats['p_market']:.3f}",
            )
            if sig is not None:
                return [sig]
        return []


class GradientBoostedRegimeEnsembleStrategy(BaseDirectionalStrategy):
    """Pillar 4C: Shallow Histogram GBDT + Regime-Conditioned Ensemble (Abstains on High Disagreement)."""

    strategy_id = "P4_GBDT_REGIME_ENSEMBLE"
    pillar = "PILLAR_4_QUANT_ML"
    description = "Regime-weighted ensemble (Market + Bayes + L2-LogReg + Shallow GBDT) with disagreement filter."

    def __init__(self) -> None:
        self.ensemble = RegimeConditionedEnsemble(l2_lambda=6.0, n_trees=28)
        self.kalman = SequentialLogOddsKalman()

    def fit(self, train_contracts: Sequence[MarketContractRecord]) -> "GradientBoostedRegimeEnsembleStrategy":
        rows, ys, ws = _extract_training_panel(train_contracts)
        self.ensemble.fit(
            rows,
            ys,
            numeric_cols=ML_NUMERIC_FEATURES,
            categorical_cols=ML_CATEGORICAL_FEATURES,
            sample_weights=ws,
        )
        return self

    def generate_signals(
        self,
        contract: MarketContractRecord,
        semantics: ContractSemantics,
        clean_ticks: Sequence[PriceTick],
        adapter: ExecutionAdapter,
    ) -> List[DirectionalSignal]:
        if len(clean_ticks) < 3 or not self.ensemble.fitted:
            return []
        kp, kv, _ = self.kalman.filter_trajectory(
            [t.ts for t in clean_ticks], [t.p_mid for t in clean_ticks]
        )
        checkpoints = sorted({len(clean_ticks) // 3, (2 * len(clean_ticks)) // 3, len(clean_ticks) - 1})
        for idx in checkpoints:
            if idx < 1 or idx >= len(clean_ticks):
                continue
            feats = extract_causal_tick_features(contract, semantics, clean_ticks, idx, kp, kv)
            pred = self.ensemble.predict_detailed(feats)
            # Epistemic disagreement abstention filter: skip when base learners strongly conflict!
            if pred["ensemble_disagreement"] > 0.085:
                continue
            sig = self._gate_and_build_signal(
                strategy_id=self.strategy_id,
                pillar=self.pillar,
                contract=contract,
                semantics=semantics,
                clean_ticks=clean_ticks,
                idx=idx,
                p_yes_hat=pred["p_ensemble"],
                sigma_p=pred["sigma_p"],
                adapter=adapter,
                min_net_edge_ps=0.012,
                sigma_k=0.80,
                target_price_move=0.055,
                stop_price_move=0.09,
                max_hold_hours=48.0,
                prefer_pre_exit=False,
                rationale=(
                    f"Ensemble p={pred['p_ensemble']:.3f} "
                    f"(B={pred['p_bayes']:.2f}, L={pred['p_logreg']:.2f}, G={pred['p_gbdt']:.2f}, "
                    f"dis={pred['ensemble_disagreement']:.3f})"
                ),
            )
            if sig is not None:
                return [sig]
        return []


def build_default_strategy_catalog() -> List[BaseDirectionalStrategy]:
    """Instantiates the complete 15-strategy core portfolio + 2 naive benchmarks."""
    return [
        # Mandatory Baselines
        NaiveBuyNoBaseline(),
        NaiveBuyFavoriteBaseline(),
        # Pillar 1: Price-Based
        ProbMomentumTrendStrategy(),
        ShortHorizonOverreactionStrategy(),
        VolatilityExpansionBreakoutStrategy(),
        OrderBookImbalanceFlowStrategy(),
        BoundaryTrendExhaustionStrategy(),
        # Pillar 2: Prediction & Information
        CryptoSpotVolBarrierModelStrategy(),
        WeatherForecastCalibrationStrategy(),
        NegRiskSlateRelativeValueStrategy(),
        ScheduledMacroSportsDriftStrategy(),
        # Pillar 3: Market-Behavior
        FavoriteLongshotBiasStrategy(),
        CrowdJumpRegimeStrategy(),
        LateStageConvergenceStrategy(),
        LiquidityShockDistortionStrategy(),
        # Pillar 4: Quant ML & Bayesian
        BayesianSequentialUpdaterStrategy(),
        CalibratedLogisticResidualStrategy(),
        GradientBoostedRegimeEnsembleStrategy(),
    ]


def run_contextual_bandit_meta_simulation(
    expert_trades_by_strategy: Dict[str, Sequence[SimulatedTrade]],
    eta: float = 0.35,
    top_k_experts_per_context: int = 2,
) -> List[SimulatedTrade]:
    """Pillar 4D: Strictly Causal Contextual Hedge Bandit Meta-Allocator across Pillars 1–4.

    Orders all candidate signals chronologically by `entry_ts`. At each `entry_ts`, updates
    context (`category`) weights ONLY using trades whose `exit_ts <= entry_ts` (`RT-01` safe!),
    and accepts signals emitted by the currently top-weighted experts in that category
    (deduplicating to at most 1 position per `market_id`).
    """
    expert_names = [
        sid for sid in sorted(expert_trades_by_strategy.keys()) if not sid.startswith("B")
    ]
    if not expert_names:
        return []

    allocator = ContextualHedgeAllocator(expert_names=expert_names, eta=eta, forgetting_gamma=0.015)
    all_candidates: List[SimulatedTrade] = []
    for sid in expert_names:
        all_candidates.extend(expert_trades_by_strategy[sid])
    all_candidates.sort(key=lambda tr: (tr.entry_ts, tr.strategy_id, tr.market_id))

    # Queue all expert counterfactual realizations strictly gated by exit_ts
    selected: List[SimulatedTrade] = []
    taken_markets: set[str] = set()

    for cand in all_candidates:
        weights = allocator.get_weights(context_key=cand.category, current_ts=cand.entry_ts)
        # Always enqueue the expert's own counterfactual outcome to mature ONLY at cand.exit_ts!
        allocator.enqueue_trade_outcome(
            expert=cand.strategy_id,
            context_key=cand.category,
            entry_ts=cand.entry_ts,
            exit_ts=cand.exit_ts,
            net_return_on_notional=cand.return_on_capital,
        )
        if cand.market_id in taken_markets:
            continue
        ranked = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
        allowed = {k for k, _ in ranked[: max(1, int(top_k_experts_per_context))]}
        if cand.strategy_id in allowed:
            taken_markets.add(cand.market_id)
            meta_copy = cand.clone_with(
                strategy_id="P4_CONTEXTUAL_BANDIT_META",
                pillar="PILLAR_4_QUANT_ML",
            )
            selected.append(meta_copy)
    return selected

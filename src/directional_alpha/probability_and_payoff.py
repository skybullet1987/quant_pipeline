"""Agent C — Mathematical Alpha, Proper Scoring & Dual Profit-Mechanism Engine.

Explicitly separates and independently quantifies the two distinct profit mechanisms
in binary and multi-outcome prediction markets:

1. **Probability Edge (Hold-to-Settlement)**:
   - Buying YES at executable ask `p_entry_ask`:
       E[Gross PnL_YES] = p_true * (1 - p_entry_ask) - (1 - p_true) * p_entry_ask
                        = p_true - p_entry_ask
   - Buying NO at executable ask `q_entry_ask` (where `q_true = 1 - p_true`):
       E[Gross PnL_NO]  = q_true * (1 - q_entry_ask) - (1 - q_true) * q_entry_ask
                        = q_true - q_entry_ask
   - Net valuation deducts entry fees, L2 slippage, UMA dispute/void haircut and
     extended dispute lockup, plus capital opportunity cost `r_opp * capital * T_days`.

2. **Trading Edge (Pre-Resolution Secondary-Market Exit)**:
   - Models the executable exit price distribution `P_exit(t)` over holding horizons
     `Delta_t < T_settlement` incorporating round-trip spread crossing, passive maker
     exit fill probability with unfilled adverse-selection fallback, round-trip fees,
     and target/stop/timeout barrier probabilities.
   - Strictly forbids applying `{0, 1}` binary settlement payoff formulas to
     pre-resolution exits.

Also provides proper scoring rules (Brier score, Murphy Brier decomposition, Brier
skill score vs market-implied midpoint baseline, Log-Loss cross-entropy, ECE &
reliability curves), epistemic uncertainty (`sigma_p`) confidence intervals,
uncertainty-penalized entry thresholds, dynamic exit stopping rules, and profit per
dollar-day committed (`EV_net / (capital * lockup_days)`).

Pure Python 3.12 stdlib implementation (zero numpy/pandas dependencies).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

MIN_LOCKUP_DAYS: float = 1.0 / 1440.0  # 1 minute floor to avoid division by zero
DEFAULT_LOG_LOSS_EPS: float = 1e-6


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def _logit(p: float, eps: float = 1e-9) -> float:
    pc = _clamp(p, eps, 1.0 - eps)
    return math.log(pc / (1.0 - pc))


def _sigmoid(z: float) -> float:
    if z >= 0.0:
        ez = math.exp(-min(z, 700.0))
        return 1.0 / (1.0 + ez)
    ez = math.exp(max(z, -700.0))
    return ez / (1.0 + ez)


# ==============================================================================
# 1. CONTRACT SEMANTICS & POLYMARKET FEE / TICK MICROSTRUCTURE
# ==============================================================================


def resolve_side_probability(
    p_event_or_yes_true: float,
    side: str = "YES",
    question_is_negated: bool = False,
) -> Tuple[float, float, float]:
    """Resolves `(pi_side_true, p_yes_true, q_no_true)` with explicit negation guard.

    Args:
        p_event_or_yes_true: Probability in `[0, 1]`. When `question_is_negated=False`,
            this is `P(YES resolves to $1)`. When `question_is_negated=True` (e.g.,
            `"Will X NOT happen?"` where the model estimated `P(X happens)`), this flips
            `p_yes_true = 1 - p_event_or_yes_true` so YES/NO semantics are never inverted.
        side: `"YES"` or `"NO"`.
        question_is_negated: True if `p_event_or_yes_true` represents the affirmative
            underlying event while the contract's YES token pays when the event does NOT occur.

    Returns:
        Tuple `(pi_side_true, p_yes_true, q_no_true)`.
    """
    if not (0.0 <= float(p_event_or_yes_true) <= 1.0) or math.isnan(float(p_event_or_yes_true)):
        raise ValueError(f"Probability must be in [0, 1], got {p_event_or_yes_true!r}")
    side_norm = str(side or "").strip().upper()
    if side_norm not in ("YES", "NO"):
        raise ValueError(f"Contract side must be 'YES' or 'NO', got {side!r}")

    p_raw = float(p_event_or_yes_true)
    p_yes = (1.0 - p_raw) if question_is_negated else p_raw
    q_no = 1.0 - p_yes
    pi_side = p_yes if side_norm == "YES" else q_no
    return pi_side, p_yes, q_no


def round_price_up_to_tick(price: float, tick_size: float = 0.01) -> float:
    """Rounds an executable buy price UP to the contract's minimum valid CLOB tick."""
    if tick_size <= 0.0:
        raise ValueError(f"tick_size must be > 0, got {tick_size}")
    steps = math.ceil((float(price) - 1e-12) / float(tick_size))
    return round(_clamp(steps * float(tick_size), float(tick_size), 1.0 - float(tick_size)), 6)


def round_price_down_to_tick(price: float, tick_size: float = 0.01) -> float:
    """Rounds an executable sell price DOWN to the contract's minimum valid CLOB tick."""
    if tick_size <= 0.0:
        raise ValueError(f"tick_size must be > 0, got {tick_size}")
    steps = math.floor((float(price) + 1e-12) / float(tick_size))
    return round(_clamp(steps * float(tick_size), 0.0, 1.0), 6)


def compute_polymarket_fee_per_share(
    price: float,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    is_maker: bool = False,
    maker_rebate_rate: float = 0.0,
    fee_schedule: str = "curved_p_1mp",
) -> float:
    """Computes Polymarket CLOB fee per share (positive = cost, negative = verified rebate).

    - Genuine 0%-fee contracts (`feesEnabled=False`, e.g. ~88.9% of Geopolitics and ~13.6% of
      Politics in Nov 2026 V2 schedule): `fee_rate=0.0` -> `0.0`.
    - Protocol V2 fee-enabled contracts (`89.05%+` of active markets: `crypto_fees_v2` r=0.07,
      `sports_fees_v3` r=0.05, `weather_fees`/`economics_fees`/`culture_fees` r=0.05,
      `politics_fees`/`finance_prices_fees`/`tech_fees` r=0.04):
      * `"curved_p_1mp"` (Protocol V2 curve): `fee_rate * (p * (1 - p)) ** fee_exponent`
      * `"min_prob"`: `fee_rate * min(p, 1 - p)`
      * `"flat_notional"`: `fee_rate * p`
    - Maker (`postOnly`) orders pay `0.0` taker fee; if `maker_rebate_rate > 0` is explicitly
      enabled for sensitivity analysis, returns `-maker_rebate_rate * taker_fee_equivalent`
      (conservative default `maker_rebate_rate=0.0`).
    """
    if float(fee_rate) <= 0.0:
        return 0.0
    p = _clamp(float(price), 0.0001, 0.9999)
    r = max(0.0, float(fee_rate))
    exp = max(0.5, float(fee_exponent))

    if fee_schedule == "curved_p_1mp":
        base_fee = r * ((p * (1.0 - p)) ** exp)
    elif fee_schedule == "min_prob":
        base_fee = r * min(p, 1.0 - p)
    elif fee_schedule == "flat_notional":
        base_fee = r * p
    else:
        raise ValueError(f"Unsupported fee_schedule: {fee_schedule!r}")

    if is_maker:
        rebate_frac = _clamp(float(maker_rebate_rate), 0.0, 1.0)
        return -rebate_frac * base_fee
    return base_fee


# ==============================================================================
# 2. MECHANISM 1 — PROBABILITY EDGE (HOLD-TO-SETTLEMENT VALUATION)
# ==============================================================================


@dataclass(frozen=True)
class HoldToSettlementValuation:
    """Complete net economic valuation for a Hold-to-Settlement directional position."""

    mechanism: str
    side: str
    p_yes_true: float
    q_no_true: float
    pi_side_true: float
    entry_ask_price: float
    entry_exec_price: float
    entry_slippage_per_share: float
    entry_fee_per_share: float
    capital_committed_per_share: float
    gross_probability_edge_per_share: float
    uma_dispute_haircut_per_share: float
    expected_settlement_payout_per_share: float
    ev_cash_per_share: float
    lockup_days_nominal: float
    effective_lockup_days: float
    opportunity_cost_per_share: float
    ev_econ_per_share: float
    roi_cash_per_dollar: float
    roi_econ_per_dollar: float
    profit_per_dollar_day_cash: float
    profit_per_dollar_day_econ: float
    payoff_variance_per_share: float
    payoff_std_per_share: float
    payoff_skewness: float
    cvar_95_per_share: float
    worst_case_loss_per_share: float
    breakeven_pi_side: float
    negative_skew_tail_warning: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_discrete_moments_and_cvar(
    outcomes_and_probs: Sequence[Tuple[float, float]],
    alpha: float = 0.05,
) -> Tuple[float, float, float, float, float]:
    """Computes `(mean, variance, std, skewness, cvar_alpha)` for discrete PnL outcomes."""
    total_p = sum(p for _, p in outcomes_and_probs if p > 0.0)
    if total_p <= 0.0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    norm = [(x, p / total_p) for x, p in outcomes_and_probs if p > 0.0]

    mean = sum(x * p for x, p in norm)
    var = max(0.0, sum(p * ((x - mean) ** 2) for x, p in norm))
    std = math.sqrt(var)
    if std > 1e-12:
        m3 = sum(p * ((x - mean) ** 3) for x, p in norm)
        skew = m3 / (std ** 3)
    else:
        skew = 0.0

    # Exact discrete Expected Shortfall (CVaR) in the worst `alpha` left tail
    sorted_outcomes = sorted(norm, key=lambda item: item[0])
    rem = _clamp(alpha, 1e-6, 1.0)
    tail_weighted_sum = 0.0
    for x, p in sorted_outcomes:
        take = min(rem, p)
        tail_weighted_sum += take * x
        rem -= take
        if rem <= 1e-12:
            break
    cvar = tail_weighted_sum / _clamp(alpha, 1e-6, 1.0)
    return mean, var, std, skew, cvar


def evaluate_hold_to_settlement(
    p_yes_true: float,
    entry_price: float,
    lockup_days: float,
    side: str = "YES",
    question_is_negated: bool = False,
    quote_is_midpoint: bool = False,
    assumed_half_spread: float = 0.0,
    entry_slippage_per_share: float = 0.0,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    is_maker_entry: bool = False,
    maker_rebate_rate: float = 0.0,
    fee_schedule: str = "curved_p_1mp",
    p_uma_dispute: float = 0.002,
    dispute_payout_per_share: float = 0.0,
    dispute_extra_lockup_days: float = 7.0,
    p_void_50_50: float = 0.0,
    r_opp_per_day: float = 0.0,
    tick_size: Optional[float] = None,
) -> HoldToSettlementValuation:
    """Evaluates Mechanism 1: Probability Edge (Hold-to-Settlement).

    Enforces:
      - Exact YES gross formula: `p_true * (1 - p_ask) - (1 - p_true) * p_ask = p_true - p_ask`
      - Exact NO gross formula:  `q_true * (1 - q_ask) - (1 - q_true) * q_ask = q_true - q_ask`
      - Anti-fabrication guard (`RT-02`): if `quote_is_midpoint=True`, `assumed_half_spread` MUST
        be strictly positive to reconstruct an executable ask quote.
      - Explicit UMA dispute haircut (`RT-04` / `D-009` conservative `$0.00` default payout
        under dispute, plus extended lockup days).
    """
    pi_true, p_yes, q_no = resolve_side_probability(
        p_yes_true, side=side, question_is_negated=question_is_negated
    )
    if not (0.0 < float(entry_price) < 1.0):
        raise ValueError(f"entry_price must be in (0, 1), got {entry_price!r}")
    if float(lockup_days) < 0.0:
        raise ValueError(f"lockup_days must be >= 0, got {lockup_days!r}")
    if quote_is_midpoint and float(assumed_half_spread) <= 0.0:
        raise ValueError(
            "Midpoint fill fabrication forbidden (RT-02): when quote_is_midpoint=True, "
            "assumed_half_spread must be > 0."
        )

    entry_ask = float(entry_price) + (float(assumed_half_spread) if quote_is_midpoint else 0.0)
    if tick_size is not None and not is_maker_entry:
        entry_ask = round_price_up_to_tick(entry_ask, tick_size=float(tick_size))
    if entry_ask >= 1.0:
        raise ValueError(
            f"Executable entry_ask={entry_ask:.6f} >= 1.00 after spread/tick adjustment; trade impossible."
        )

    slip = max(0.0, float(entry_slippage_per_share))
    exec_px = _clamp(entry_ask + slip, 0.0001, 0.9999)
    entry_fee = compute_polymarket_fee_per_share(
        exec_px,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=is_maker_entry,
        maker_rebate_rate=maker_rebate_rate,
        fee_schedule=fee_schedule,
    )
    capital_per_share = exec_px + entry_fee

    # Exact gross probability edge identity per contract side
    gross_edge = pi_true * (1.0 - entry_ask) - (1.0 - pi_true) * entry_ask

    p_disp = _clamp(float(p_uma_dispute), 0.0, 0.999)
    p_void = _clamp(float(p_void_50_50), 0.0, max(0.0, 0.999 - p_disp))
    v_disp = _clamp(float(dispute_payout_per_share), 0.0, 1.0)
    p_normal = max(0.0, 1.0 - p_disp - p_void)

    # 4-state settlement distribution: Normal Win ($1), Normal Loss ($0), 50-50 Void ($0.50), UMA Dispute ($v_disp)
    p_win_state = p_normal * pi_true
    p_loss_state = p_normal * (1.0 - pi_true)
    p_void_state = p_void
    p_disp_state = p_disp

    expected_payout = p_win_state * 1.0 + p_void_state * 0.50 + p_disp_state * v_disp
    uma_haircut = pi_true - expected_payout
    ev_cash = expected_payout - capital_per_share

    nom_days = max(0.0, float(lockup_days))
    eff_days = max(MIN_LOCKUP_DAYS, nom_days + p_disp * max(0.0, float(dispute_extra_lockup_days)))
    opp_cost = max(0.0, float(r_opp_per_day)) * capital_per_share * eff_days
    ev_econ = ev_cash - opp_cost

    pnl_states = [
        (1.0 - capital_per_share, p_win_state),
        (0.0 - capital_per_share, p_loss_state),
        (0.50 - capital_per_share, p_void_state),
        (v_disp - capital_per_share, p_disp_state),
    ]
    _, var_s, std_s, skew_s, cvar_95 = _compute_discrete_moments_and_cvar(pnl_states, alpha=0.05)
    worst_loss = min(x for x, p in pnl_states if p > 0.0)

    roi_cash = ev_cash / capital_per_share if capital_per_share > 0.0 else 0.0
    roi_econ = ev_econ / capital_per_share if capital_per_share > 0.0 else 0.0
    ppdd_cash = roi_cash / eff_days
    ppdd_econ = roi_econ / eff_days

    # Solve `p_normal * pi_be + p_void * 0.50 + p_disp * v_disp = capital_per_share + opp_cost`
    breakeven_pi = _clamp(
        (capital_per_share + opp_cost - p_void * 0.50 - p_disp * v_disp) / max(1e-9, p_normal),
        0.0,
        1.0,
    )
    neg_skew_warning = bool(skew_s < -2.0 or (entry_ask >= 0.88 and abs(worst_loss) > 8.0 * max(1e-6, 1.0 - capital_per_share)))

    return HoldToSettlementValuation(
        mechanism="PROBABILITY_EDGE_HOLD_TO_SETTLEMENT",
        side=str(side).strip().upper(),
        p_yes_true=p_yes,
        q_no_true=q_no,
        pi_side_true=pi_true,
        entry_ask_price=entry_ask,
        entry_exec_price=exec_px,
        entry_slippage_per_share=slip,
        entry_fee_per_share=entry_fee,
        capital_committed_per_share=capital_per_share,
        gross_probability_edge_per_share=gross_edge,
        uma_dispute_haircut_per_share=uma_haircut,
        expected_settlement_payout_per_share=expected_payout,
        ev_cash_per_share=ev_cash,
        lockup_days_nominal=nom_days,
        effective_lockup_days=eff_days,
        opportunity_cost_per_share=opp_cost,
        ev_econ_per_share=ev_econ,
        roi_cash_per_dollar=roi_cash,
        roi_econ_per_dollar=roi_econ,
        profit_per_dollar_day_cash=ppdd_cash,
        profit_per_dollar_day_econ=ppdd_econ,
        payoff_variance_per_share=var_s,
        payoff_std_per_share=std_s,
        payoff_skewness=skew_s,
        cvar_95_per_share=cvar_95,
        worst_case_loss_per_share=worst_loss,
        breakeven_pi_side=breakeven_pi,
        negative_skew_tail_warning=neg_skew_warning,
    )


# ==============================================================================
# 3. MECHANISM 2 — TRADING EDGE (PRE-RESOLUTION SECONDARY-MARKET EXIT)
# ==============================================================================


@dataclass(frozen=True)
class ExitScenario:
    """Single scenario in a pre-resolution secondary-market exit price distribution.

    Attributes:
        prob: Probability weight of this exit regime/path (`sum(prob) == 1`).
        exit_bid: Executable secondary-market CLOB best bid at exit time `hold_days`.
            Must lie strictly inside `(0, 1)` — binary `{0, 1}` settlement payoffs are
            forbidden in pre-resolution trading-edge valuation!
        hold_days: Holding duration in days (`Delta_t`) until this exit occurs.
        exit_mid: Optional mid price at exit (for decomposing spread vs directional drift).
        exit_slippage_per_share: L2 depth / impact slippage subtracted when crossing the bid.
        passive_maker_fill_prob: Probability in `[0, 1]` that a passive maker sell order
            at `passive_maker_price` fills before `hold_days`.
        passive_maker_price: Limit price of the passive maker exit order (required if
            `passive_maker_fill_prob > 0`).
        unfilled_fallback_bid: Conditioned executable bid if the passive maker exit fails
            to fill (`<= exit_bid` due to adverse selection: unfilled limit sells occur
            when price drifts downward away from the ask!).
        label: Scenario name (`"target"`, `"stop"`, `"timeout_mid"`, etc.).
    """

    prob: float
    exit_bid: float
    hold_days: float
    exit_mid: Optional[float] = None
    exit_slippage_per_share: float = 0.0
    passive_maker_fill_prob: float = 0.0
    passive_maker_price: Optional[float] = None
    unfilled_fallback_bid: Optional[float] = None
    label: str = "scenario"


@dataclass(frozen=True)
class PreResolutionExitValuation:
    """Complete net economic valuation for a Pre-Resolution Trading-Edge position."""

    mechanism: str
    side: str
    entry_mid_price: float
    entry_ask_price: float
    entry_exec_price: float
    entry_fee_per_share: float
    capital_committed_per_share: float
    expected_exit_mid_price: float
    expected_gross_exit_proceeds_per_share: float
    expected_exit_fee_per_share: float
    expected_net_exit_proceeds_per_share: float
    gross_mid_drift_per_share: float
    round_trip_spread_and_slippage_drag_per_share: float
    round_trip_fee_drag_per_share: float
    adverse_selection_drag_per_share: float
    ev_cash_per_share: float
    expected_hold_days: float
    opportunity_cost_per_share: float
    ev_econ_per_share: float
    roi_cash_per_dollar: float
    roi_econ_per_dollar: float
    profit_per_dollar_day_cash: float
    profit_per_dollar_day_econ: float
    pnl_variance_per_share: float
    pnl_std_per_share: float
    pnl_skewness: float
    cvar_95_per_share: float
    worst_case_loss_per_share: float
    win_probability: float
    scenario_breakdown: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_pre_resolution_exit(
    entry_ask_price: float,
    exit_scenarios: Sequence[ExitScenario],
    side: str = "YES",
    entry_mid_price: Optional[float] = None,
    entry_slippage_per_share: float = 0.0,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    is_maker_entry: bool = False,
    maker_rebate_rate: float = 0.0,
    fee_schedule: str = "curved_p_1mp",
    r_opp_per_day: float = 0.0,
    tick_size: Optional[float] = None,
) -> PreResolutionExitValuation:
    """Evaluates Mechanism 2: Trading Edge (Pre-Resolution Exit) over `P_exit(Delta_t)`.

    NEVER applies `{0, 1}` binary settlement payoff formulas: raises `ValueError` if any
    scenario passes binary `{0.0, 1.0}` settlement endpoints as secondary-market bids.
    Explicitly decomposes gross mid-price drift vs round-trip spread/slippage, round-trip
    fees, and passive-maker unfilled adverse selection.
    """
    side_norm = str(side or "").strip().upper()
    if side_norm not in ("YES", "NO"):
        raise ValueError(f"Contract side must be 'YES' or 'NO', got {side!r}")
    if not (0.0 < float(entry_ask_price) < 1.0):
        raise ValueError(f"entry_ask_price must be in (0, 1), got {entry_ask_price!r}")
    if not exit_scenarios:
        raise ValueError("exit_scenarios must be non-empty.")

    prob_sum = sum(float(s.prob) for s in exit_scenarios)
    if abs(prob_sum - 1.0) > 1e-4:
        raise ValueError(f"exit_scenarios probabilities must sum to 1.0, got {prob_sum:.6f}")

    eff_entry_ask = float(entry_ask_price)
    if tick_size is not None and not is_maker_entry:
        eff_entry_ask = round_price_up_to_tick(eff_entry_ask, float(tick_size))
    entry_mid = float(entry_mid_price) if entry_mid_price is not None else eff_entry_ask
    if entry_mid > eff_entry_ask + 1e-9 and not is_maker_entry:
        raise ValueError(
            f"entry_mid_price ({entry_mid}) cannot exceed executable entry_ask_price ({eff_entry_ask})."
        )

    entry_slip = max(0.0, float(entry_slippage_per_share))
    entry_exec = _clamp(eff_entry_ask + entry_slip, 0.0001, 0.9999)
    entry_fee = compute_polymarket_fee_per_share(
        entry_exec,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=is_maker_entry,
        maker_rebate_rate=maker_rebate_rate,
        fee_schedule=fee_schedule,
    )
    capital_per_share = entry_exec + entry_fee

    discrete_pnls: List[Tuple[float, float]] = []
    breakdown: List[Dict[str, Any]] = []

    exp_exit_mid = 0.0
    exp_gross_exit = 0.0
    exp_exit_fee = 0.0
    exp_net_exit = 0.0
    exp_hold_days = 0.0
    adverse_sel_drag = 0.0
    win_prob = 0.0

    for sc in exit_scenarios:
        w = float(sc.prob) / prob_sum
        if w < 0.0:
            raise ValueError(f"Scenario probability cannot be negative: {sc}")
        if w == 0.0:
            continue
        if sc.exit_bid <= 0.0 or sc.exit_bid >= 1.0:
            raise ValueError(
                f"Settlement payoff boundary exit_bid={sc.exit_bid!r} forbidden in "
                f"evaluate_pre_resolution_exit (scenario={sc.label!r}). Pre-resolution exits "
                "must model executable CLOB bids in (0, 1)."
            )
        if sc.hold_days < 0.0:
            raise ValueError(f"Scenario hold_days must be >= 0, got {sc.hold_days}")

        bid_px = float(sc.exit_bid)
        if tick_size is not None:
            bid_px = round_price_down_to_tick(bid_px, float(tick_size))
        sc_mid = float(sc.exit_mid) if sc.exit_mid is not None else bid_px
        exit_slip = max(0.0, float(sc.exit_slippage_per_share))

        taker_exec_bid = _clamp(bid_px - exit_slip, 0.0001, 0.9999)
        taker_exit_fee = compute_polymarket_fee_per_share(
            taker_exec_bid,
            fee_rate=fee_rate,
            fee_exponent=fee_exponent,
            is_maker=False,
            fee_schedule=fee_schedule,
        )
        taker_net_proceeds = taker_exec_bid - taker_exit_fee

        phi = _clamp(float(sc.passive_maker_fill_prob), 0.0, 1.0)
        if phi > 0.0:
            if sc.passive_maker_price is None or not (0.0 < float(sc.passive_maker_price) < 1.0):
                raise ValueError(
                    f"passive_maker_price in (0, 1) required when passive_maker_fill_prob > 0 ({sc.label})"
                )
            maker_px = float(sc.passive_maker_price)
            maker_exit_fee = compute_polymarket_fee_per_share(
                maker_px,
                fee_rate=fee_rate,
                fee_exponent=fee_exponent,
                is_maker=True,
                maker_rebate_rate=maker_rebate_rate,
                fee_schedule=fee_schedule,
            )
            maker_net_proceeds = maker_px - maker_exit_fee
            maker_pnl = maker_net_proceeds - capital_per_share

            fb_bid = float(sc.unfilled_fallback_bid) if sc.unfilled_fallback_bid is not None else bid_px
            if fb_bid > bid_px + 1e-9:
                raise ValueError(
                    f"unfilled_fallback_bid ({fb_bid}) cannot exceed unconditional exit_bid ({bid_px})."
                )
            fb_exec = _clamp(fb_bid - exit_slip, 0.0001, 0.9999)
            fb_fee = compute_polymarket_fee_per_share(
                fb_exec,
                fee_rate=fee_rate,
                fee_exponent=fee_exponent,
                is_maker=False,
                fee_schedule=fee_schedule,
            )
            fb_net_proceeds = fb_exec - fb_fee
            fb_pnl = fb_net_proceeds - capital_per_share

            # Record both sub-branches in the discrete PnL distribution so tail risk is exact!
            discrete_pnls.append((maker_pnl, w * phi))
            if 1.0 - phi > 1e-12:
                discrete_pnls.append((fb_pnl, w * (1.0 - phi)))

            sc_gross_proceeds = phi * maker_px + (1.0 - phi) * fb_exec
            sc_exit_fee = phi * maker_exit_fee + (1.0 - phi) * fb_fee
            sc_net_proceeds = phi * maker_net_proceeds + (1.0 - phi) * fb_net_proceeds
            adverse_sel_drag += w * (1.0 - phi) * max(0.0, bid_px - fb_bid)
            if maker_pnl > 0.0:
                win_prob += w * phi
            if fb_pnl > 0.0:
                win_prob += w * (1.0 - phi)
        else:
            taker_pnl = taker_net_proceeds - capital_per_share
            discrete_pnls.append((taker_pnl, w))
            sc_gross_proceeds = taker_exec_bid
            sc_exit_fee = taker_exit_fee
            sc_net_proceeds = taker_net_proceeds
            if taker_pnl > 0.0:
                win_prob += w

        exp_exit_mid += w * sc_mid
        exp_gross_exit += w * sc_gross_proceeds
        exp_exit_fee += w * sc_exit_fee
        exp_net_exit += w * sc_net_proceeds
        exp_hold_days += w * float(sc.hold_days)

        breakdown.append(
            {
                "label": sc.label,
                "prob": round(w, 6),
                "hold_days": round(float(sc.hold_days), 6),
                "exit_bid": round(bid_px, 6),
                "net_proceeds_per_share": round(sc_net_proceeds, 6),
                "net_pnl_per_share": round(sc_net_proceeds - capital_per_share, 6),
            }
        )

    ev_cash = exp_net_exit - capital_per_share
    eff_hold_days = max(MIN_LOCKUP_DAYS, exp_hold_days)
    opp_cost = max(0.0, float(r_opp_per_day)) * capital_per_share * eff_hold_days
    ev_econ = ev_cash - opp_cost

    gross_mid_drift = exp_exit_mid - entry_mid
    rt_fee_drag = entry_fee + exp_exit_fee
    # Identity: ev_cash == gross_mid_drift - rt_spread_slip_drag - rt_fee_drag
    # (where passive maker price improvement can reduce rt_spread_slip_drag, while
    # unfilled fallback adverse selection increases it)
    rt_spread_slip_drag = (entry_exec - entry_mid) + (exp_exit_mid - exp_gross_exit)

    _, var_s, std_s, skew_s, cvar_95 = _compute_discrete_moments_and_cvar(discrete_pnls, alpha=0.05)
    worst_loss = min(x for x, p in discrete_pnls if p > 0.0)

    roi_cash = ev_cash / capital_per_share if capital_per_share > 0.0 else 0.0
    roi_econ = ev_econ / capital_per_share if capital_per_share > 0.0 else 0.0

    return PreResolutionExitValuation(
        mechanism="TRADING_EDGE_PRE_RESOLUTION_EXIT",
        side=side_norm,
        entry_mid_price=entry_mid,
        entry_ask_price=eff_entry_ask,
        entry_exec_price=entry_exec,
        entry_fee_per_share=entry_fee,
        capital_committed_per_share=capital_per_share,
        expected_exit_mid_price=exp_exit_mid,
        expected_gross_exit_proceeds_per_share=exp_gross_exit,
        expected_exit_fee_per_share=exp_exit_fee,
        expected_net_exit_proceeds_per_share=exp_net_exit,
        gross_mid_drift_per_share=gross_mid_drift,
        round_trip_spread_and_slippage_drag_per_share=rt_spread_slip_drag,
        round_trip_fee_drag_per_share=rt_fee_drag,
        adverse_selection_drag_per_share=adverse_sel_drag,
        ev_cash_per_share=ev_cash,
        expected_hold_days=eff_hold_days,
        opportunity_cost_per_share=opp_cost,
        ev_econ_per_share=ev_econ,
        roi_cash_per_dollar=roi_cash,
        roi_econ_per_dollar=roi_econ,
        profit_per_dollar_day_cash=roi_cash / eff_hold_days,
        profit_per_dollar_day_econ=roi_econ / eff_hold_days,
        pnl_variance_per_share=var_s,
        pnl_std_per_share=std_s,
        pnl_skewness=skew_s,
        cvar_95_per_share=cvar_95,
        worst_case_loss_per_share=worst_loss,
        win_probability=win_prob,
        scenario_breakdown=breakdown,
    )


def evaluate_barrier_trading_edge(
    entry_ask_price: float,
    half_spread: float,
    target_exit_bid: float,
    stop_exit_bid: float,
    timeout_expected_bid: float,
    timeout_bid_std: float,
    p_target_hit: float,
    p_stop_hit: float,
    hold_days_target: float,
    hold_days_stop: float,
    hold_days_timeout: float,
    side: str = "YES",
    entry_slippage_per_share: float = 0.0,
    exit_slippage_per_share: float = 0.0,
    stop_extra_slippage_per_share: float = 0.005,
    passive_maker_target_prob: float = 0.0,
    passive_maker_target_price: Optional[float] = None,
    unfilled_target_fallback_bid: Optional[float] = None,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    is_maker_entry: bool = False,
    maker_rebate_rate: float = 0.0,
    r_opp_per_day: float = 0.0,
    tick_size: Optional[float] = None,
) -> PreResolutionExitValuation:
    """Structured 3-barrier (Target / Stop-Loss / Horizon Timeout) Pre-Resolution Exit model.

    Models timeout dispersion with a 3-point Gauss-Hermite-like discrete matching
    (`mu - std`, `mu`, `mu + std` with weights `1/6, 2/3, 1/6`) bounded inside `(0.005, 0.995)`
    so horizon volatility and stop-loss extra slippage are captured accurately.
    """
    p_tgt = _clamp(float(p_target_hit), 0.0, 1.0)
    p_stp = _clamp(float(p_stop_hit), 0.0, 1.0)
    if p_tgt + p_stp > 1.0 + 1e-9:
        raise ValueError(f"p_target_hit + p_stop_hit cannot exceed 1.0 ({p_tgt} + {p_stp})")
    p_to = max(0.0, 1.0 - p_tgt - p_stp)

    hs = max(0.0, float(half_spread))
    entry_mid = _clamp(float(entry_ask_price) - hs, 0.001, 0.999)

    scenarios: List[ExitScenario] = []
    if p_tgt > 0.0:
        scenarios.append(
            ExitScenario(
                prob=p_tgt,
                exit_bid=_clamp(float(target_exit_bid), 0.002, 0.998),
                exit_mid=_clamp(float(target_exit_bid) + hs, 0.002, 0.999),
                hold_days=max(MIN_LOCKUP_DAYS, float(hold_days_target)),
                exit_slippage_per_share=exit_slippage_per_share,
                passive_maker_fill_prob=passive_maker_target_prob,
                passive_maker_price=passive_maker_target_price,
                unfilled_fallback_bid=unfilled_target_fallback_bid,
                label="target_hit",
            )
        )
    if p_stp > 0.0:
        scenarios.append(
            ExitScenario(
                prob=p_stp,
                exit_bid=_clamp(float(stop_exit_bid), 0.002, 0.998),
                exit_mid=_clamp(float(stop_exit_bid) + hs, 0.002, 0.999),
                hold_days=max(MIN_LOCKUP_DAYS, float(hold_days_stop)),
                exit_slippage_per_share=exit_slippage_per_share + max(0.0, float(stop_extra_slippage_per_share)),
                label="stop_hit",
            )
        )
    if p_to > 0.0:
        mu_b = _clamp(float(timeout_expected_bid), 0.005, 0.995)
        sd_b = max(0.0, float(timeout_bid_std))
        if sd_b <= 1e-6:
            scenarios.append(
                ExitScenario(
                    prob=p_to,
                    exit_bid=mu_b,
                    exit_mid=_clamp(mu_b + hs, 0.002, 0.999),
                    hold_days=max(MIN_LOCKUP_DAYS, float(hold_days_timeout)),
                    exit_slippage_per_share=exit_slippage_per_share,
                    label="timeout_flat",
                )
            )
        else:
            # 3-point symmetric moment-matching quadrature (weights 1/6, 4/6, 1/6 at +/- sqrt(3)*sd)
            delta = math.sqrt(3.0) * sd_b
            for sub_label, w_sub, offset in (
                ("timeout_down", p_to / 6.0, -delta),
                ("timeout_center", p_to * (4.0 / 6.0), 0.0),
                ("timeout_up", p_to / 6.0, +delta),
            ):
                b_pt = _clamp(mu_b + offset, 0.002, 0.998)
                scenarios.append(
                    ExitScenario(
                        prob=w_sub,
                        exit_bid=b_pt,
                        exit_mid=_clamp(b_pt + hs, 0.002, 0.999),
                        hold_days=max(MIN_LOCKUP_DAYS, float(hold_days_timeout)),
                        exit_slippage_per_share=exit_slippage_per_share,
                        label=sub_label,
                    )
                )

    return evaluate_pre_resolution_exit(
        entry_ask_price=entry_ask_price,
        exit_scenarios=scenarios,
        side=side,
        entry_mid_price=entry_mid,
        entry_slippage_per_share=entry_slippage_per_share,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker_entry=is_maker_entry,
        maker_rebate_rate=maker_rebate_rate,
        r_opp_per_day=r_opp_per_day,
        tick_size=tick_size,
    )


# ==============================================================================
# 4. PROPER SCORING RULES & CALIBRATION DIAGNOSTICS
# ==============================================================================


def _valid_prob_and_outcome(pf: float, yf: float) -> bool:
    return (
        not math.isnan(pf)
        and not math.isnan(yf)
        and (0.0 <= pf <= 1.0)
        and (0.0 <= yf <= 1.0)
    )


def brier_score(
    probs: Sequence[float],
    outcomes: Sequence[int | float],
    weights: Optional[Sequence[float]] = None,
) -> float:
    """Computes proper quadratic Brier Score `1/N * sum_i (p_i - y_i)^2` (lower is better).

    Accepts binary `{0, 1}` as well as continuous `[0, 1]` settlement payouts (such as `0.50`
    on `50-50` voided Polymarket contracts so OOS scoring never drops voided entries — `RT-04`).
    """
    if len(probs) != len(outcomes) or len(probs) == 0:
        raise ValueError("probs and outcomes must have equal non-zero length.")
    if weights is None:
        total = 0.0
        for p, y in zip(probs, outcomes):
            pf, yf = float(p), float(y)
            if not _valid_prob_and_outcome(pf, yf):
                raise ValueError(f"Invalid probability/outcome pair: ({pf}, {yf})")
            total += (pf - yf) ** 2
        return total / len(probs)

    if len(weights) != len(probs):
        raise ValueError("weights must match probs length.")
    w_sum = 0.0
    total = 0.0
    for p, y, w in zip(probs, outcomes, weights):
        pf, yf, wf = float(p), float(y), float(w)
        if wf < 0.0 or not _valid_prob_and_outcome(pf, yf):
            raise ValueError(f"Invalid weighted scoring tuple: ({pf}, {yf}, {wf})")
        w_sum += wf
        total += wf * ((pf - yf) ** 2)
    if w_sum <= 0.0:
        raise ValueError("Sum of weights must be > 0.")
    return total / w_sum


def brier_skill_score(
    model_probs: Sequence[float],
    market_mid_probs: Sequence[float],
    outcomes: Sequence[int | float],
    weights: Optional[Sequence[float]] = None,
) -> float:
    """Brier Skill Score `BSS = 1 - BS_model / BS_market` vs Polymarket midpoint baseline.

    - `BSS > 0`: Model has strictly superior probability accuracy over the market consensus.
    - `BSS == 0`: Model adds zero calibration/resolution skill beyond the market midpoint.
    - `BSS < 0`: Model is less accurate than the market midpoint.
    """
    bs_model = brier_score(model_probs, outcomes, weights=weights)
    bs_mkt = brier_score(market_mid_probs, outcomes, weights=weights)
    if bs_mkt <= 1e-12:
        return 0.0 if bs_model <= 1e-12 else -float("inf")
    return 1.0 - (bs_model / bs_mkt)


def log_loss(
    probs: Sequence[float],
    outcomes: Sequence[int | float],
    eps: float = DEFAULT_LOG_LOSS_EPS,
    weights: Optional[Sequence[float]] = None,
) -> float:
    """Computes binary Cross-Entropy (Log-Loss) in nats per contract (strictly proper)."""
    if len(probs) != len(outcomes) or len(probs) == 0:
        raise ValueError("probs and outcomes must have equal non-zero length.")
    clip_eps = _clamp(float(eps), 1e-15, 0.05)

    if weights is None:
        total = 0.0
        for p, y in zip(probs, outcomes):
            pf = _clamp(float(p), clip_eps, 1.0 - clip_eps)
            yf = float(y)
            if not (0.0 <= yf <= 1.0) or math.isnan(yf):
                raise ValueError(f"Outcome must be in [0, 1], got {yf}")
            total -= yf * math.log(pf) + (1.0 - yf) * math.log(1.0 - pf)
        return total / len(probs)

    if len(weights) != len(probs):
        raise ValueError("weights must match probs length.")
    w_sum = 0.0
    total = 0.0
    for p, y, w in zip(probs, outcomes, weights):
        wf = float(w)
        if wf < 0.0:
            raise ValueError(f"Negative weight: {wf}")
        pf = _clamp(float(p), clip_eps, 1.0 - clip_eps)
        yf = float(y)
        if not (0.0 <= yf <= 1.0) or math.isnan(yf):
            raise ValueError(f"Outcome must be in [0, 1], got {yf}")
        w_sum += wf
        total -= wf * (yf * math.log(pf) + (1.0 - yf) * math.log(1.0 - pf))
    if w_sum <= 0.0:
        raise ValueError("Sum of weights must be > 0.")
    return total / w_sum


def log_loss_skill_score(
    model_probs: Sequence[float],
    market_mid_probs: Sequence[float],
    outcomes: Sequence[int | float],
    eps: float = DEFAULT_LOG_LOSS_EPS,
    weights: Optional[Sequence[float]] = None,
) -> Dict[str, float]:
    """Computes Log-Loss Skill Score and information gain (in nats and bits) vs market mid."""
    ll_model = log_loss(model_probs, outcomes, eps=eps, weights=weights)
    ll_mkt = log_loss(market_mid_probs, outcomes, eps=eps, weights=weights)
    info_gain_nats = ll_mkt - ll_model
    info_gain_bits = info_gain_nats / math.log(2.0)
    skill = 1.0 - (ll_model / ll_mkt) if ll_mkt > 1e-12 else 0.0
    return {
        "log_loss_model": ll_model,
        "log_loss_market": ll_mkt,
        "log_loss_skill_score": skill,
        "info_gain_nats": info_gain_nats,
        "info_gain_bits": info_gain_bits,
    }


def expected_calibration_error(
    probs: Sequence[float],
    outcomes: Sequence[int | float],
    n_bins: int = 10,
    strategy: str = "uniform",
) -> Dict[str, Any]:
    """Computes Expected Calibration Error (ECE), Max Calibration Error (MCE), Murphy
    Brier decomposition (`reliability`, `resolution`, `uncertainty`), and reliability bins.
    """
    n = len(probs)
    if n != len(outcomes) or n == 0:
        raise ValueError("probs and outcomes must have equal non-zero length.")
    if n_bins < 2:
        raise ValueError(f"n_bins must be >= 2, got {n_bins}")

    pairs: List[Tuple[float, float]] = []
    for p, y in zip(probs, outcomes):
        pf, yf = float(p), float(y)
        if not _valid_prob_and_outcome(pf, yf):
            raise ValueError(f"Invalid (prob, outcome): ({pf}, {yf})")
        pairs.append((pf, yf))

    base_rate = sum(y for _, y in pairs) / n
    uncertainty = sum((y - base_rate) ** 2 for _, y in pairs) / n

    bins_data: List[List[Tuple[float, float]]] = [[] for _ in range(n_bins)]
    bin_edges: List[Tuple[float, float]] = []

    if strategy == "uniform":
        for k in range(n_bins):
            bin_edges.append((k / n_bins, (k + 1) / n_bins))
        for pf, yf in pairs:
            idx = min(n_bins - 1, int(math.floor(pf * n_bins)))
            bins_data[idx].append((pf, yf))
    elif strategy == "quantile":
        sorted_pairs = sorted(pairs, key=lambda item: item[0])
        for k in range(n_bins):
            lo_idx = int(round(k * n / n_bins))
            hi_idx = int(round((k + 1) * n / n_bins))
            chunk = sorted_pairs[lo_idx:hi_idx]
            bins_data[k] = chunk
            if chunk:
                bin_edges.append((chunk[0][0], chunk[-1][0]))
            else:
                bin_edges.append((0.0, 0.0))
    else:
        raise ValueError(f"Unsupported binning strategy: {strategy!r}")

    ece = 0.0
    mce = 0.0
    reliability = 0.0
    resolution = 0.0
    reliability_curve: List[Dict[str, Any]] = []

    for k in range(n_bins):
        chunk = bins_data[k]
        lo_edge, hi_edge = bin_edges[k]
        cnt = len(chunk)
        if cnt == 0:
            reliability_curve.append(
                {
                    "bin_index": k,
                    "bin_lower": round(lo_edge, 6),
                    "bin_upper": round(hi_edge, 6),
                    "count": 0,
                    "mean_predicted_prob": None,
                    "empirical_frequency": None,
                    "abs_calibration_gap": None,
                    "binomial_std_err": None,
                }
            )
            continue

        mean_pred = sum(p for p, _ in chunk) / cnt
        emp_freq = sum(y for _, y in chunk) / cnt
        gap = abs(mean_pred - emp_freq)
        weight = cnt / n

        ece += weight * gap
        mce = max(mce, gap)
        reliability += weight * ((mean_pred - emp_freq) ** 2)
        resolution += weight * ((emp_freq - base_rate) ** 2)
        se = math.sqrt(max(0.0, emp_freq * (1.0 - emp_freq)) / cnt)

        reliability_curve.append(
            {
                "bin_index": k,
                "bin_lower": round(lo_edge, 6),
                "bin_upper": round(hi_edge, 6),
                "count": cnt,
                "mean_predicted_prob": round(mean_pred, 6),
                "empirical_frequency": round(emp_freq, 6),
                "abs_calibration_gap": round(gap, 6),
                "binomial_std_err": round(se, 6),
            }
        )

    return {
        "n_samples": n,
        "base_rate": base_rate,
        "ece": ece,
        "mce": mce,
        "murphy_reliability": reliability,
        "murphy_resolution": resolution,
        "murphy_uncertainty": uncertainty,
        "brier_from_decomposition": reliability - resolution + uncertainty,
        "reliability_bins": reliability_curve,
    }


def evaluate_forecast_calibration(
    model_probs: Sequence[float],
    market_mid_probs: Sequence[float],
    outcomes: Sequence[int | float],
    n_bins: int = 10,
) -> Dict[str, Any]:
    """Comprehensive one-call proper scoring & calibration comparison vs market midpoint."""
    bs_mod = brier_score(model_probs, outcomes)
    bs_mkt = brier_score(market_mid_probs, outcomes)
    bss = brier_skill_score(model_probs, market_mid_probs, outcomes)
    ll_dict = log_loss_skill_score(model_probs, market_mid_probs, outcomes)
    cal_mod = expected_calibration_error(model_probs, outcomes, n_bins=n_bins, strategy="uniform")
    cal_mkt = expected_calibration_error(market_mid_probs, outcomes, n_bins=n_bins, strategy="uniform")

    return {
        "n_observations": len(outcomes),
        "brier_model": bs_mod,
        "brier_market": bs_mkt,
        "brier_skill_score": bss,
        **ll_dict,
        "ece_model": cal_mod["ece"],
        "ece_market": cal_mkt["ece"],
        "mce_model": cal_mod["mce"],
        "murphy_reliability_model": cal_mod["murphy_reliability"],
        "murphy_resolution_model": cal_mod["murphy_resolution"],
        "beats_market_on_BOTH_brier_and_logloss": bool(bss > 0.0 and ll_dict["info_gain_nats"] > 0.0),
        "reliability_bins_model": cal_mod["reliability_bins"],
    }


# ==============================================================================
# 5. EPISTEMIC UNCERTAINTY (`sigma_p`), OPTIMAL ENTRY & DYNAMIC EXIT RULES
# ==============================================================================


@dataclass(frozen=True)
class EpistemicProbabilityEstimate:
    """Point forecast `p_hat` paired with epistemic standard error `sigma_p` and logit CI."""

    p_hat: float
    sigma_p: float
    variance_p: float
    ci_lower_95: float
    ci_upper_95: float
    effective_sample_size: float

    def lower_bound(self, sigma_k: float = 1.0) -> float:
        """Conservative probability lower bound `max(0, p_hat - sigma_k * sigma_p)`."""
        return _clamp(self.p_hat - max(0.0, float(sigma_k)) * self.sigma_p, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def estimate_epistemic_uncertainty(
    p_hat: float,
    effective_n_clusters: float = 30.0,
    ensemble_predictions: Optional[Sequence[float]] = None,
    calibration_rmse_floor: float = 0.015,
    prior_strength: float = 2.0,
) -> EpistemicProbabilityEstimate:
    """Quantifies epistemic uncertainty `sigma_p` around `p_hat` so noisy forecasts shrink.

    Combines three orthogonal epistemic error sources in quadrature:
      1. Finite-cluster Beta-Binomial posterior variance `p*(1-p) / (N_eff + prior_strength + 1)`
         (using `effective_n_clusters` rather than raw correlated contract count — `RT-06`).
      2. Empirical out-of-fold calibration error floor `calibration_rmse_floor^2`.
      3. Model/feature ensemble dispersion `Var(ensemble_predictions)` when provided.

    Constructs 95% confidence bounds in logit space (via delta method) so intervals near
    `0` and `1` stay strictly inside `(0, 1)`.
    """
    p = _clamp(float(p_hat), 1e-6, 1.0 - 1e-6)
    n_eff = max(1.0, float(effective_n_clusters))
    pr = max(0.5, float(prior_strength))

    # Posterior mean shrunk slightly toward 0.5 under tiny sample sizes (Jeffreys/Laplace shrinkage)
    alpha_post = p * n_eff + 0.5 * pr
    beta_post = (1.0 - p) * n_eff + 0.5 * pr
    denom = alpha_post + beta_post
    var_sampling = (alpha_post * beta_post) / ((denom ** 2) * (denom + 1.0))

    var_cal = max(0.0, float(calibration_rmse_floor)) ** 2

    var_ens = 0.0
    if ensemble_predictions and len(ensemble_predictions) >= 2:
        ens = [_clamp(float(v), 0.0, 1.0) for v in ensemble_predictions]
        m_ens = sum(ens) / len(ens)
        var_ens = sum((v - m_ens) ** 2 for v in ens) / (len(ens) - 1)

    total_var = min(0.25, var_sampling + var_cal + var_ens)
    sigma_p = math.sqrt(total_var)

    # Delta-method standard error in logit space: sigma_logit = sigma_p / (p * (1 - p))
    denom_p = max(0.02, p * (1.0 - p))
    sigma_logit = min(6.0, sigma_p / denom_p)
    z0 = _logit(p)
    ci_lo = _sigmoid(z0 - 1.959964 * sigma_logit)
    ci_hi = _sigmoid(z0 + 1.959964 * sigma_logit)

    return EpistemicProbabilityEstimate(
        p_hat=p,
        sigma_p=sigma_p,
        variance_p=total_var,
        ci_lower_95=ci_lo,
        ci_upper_95=ci_hi,
        effective_sample_size=n_eff,
    )


def optimal_entry_threshold(
    p_yes_hat: float,
    sigma_p: float,
    entry_ask_price: float,
    lockup_days: float,
    side: str = "YES",
    question_is_negated: bool = False,
    sigma_k: float = 1.0,
    entry_slippage_per_share: float = 0.0,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    is_maker_entry: bool = False,
    maker_rebate_rate: float = 0.0,
    p_uma_dispute: float = 0.002,
    dispute_payout_per_share: float = 0.0,
    dispute_extra_lockup_days: float = 7.0,
    r_opp_per_day: float = 0.0,
    min_net_edge_per_share: float = 0.005,
    tick_size: Optional[float] = 0.01,
) -> Dict[str, Any]:
    """Evaluates the uncertainty-penalized entry condition:
        `pi_true_LCB = pi_hat - sigma_k * sigma_p > p_ask + fee + slippage + dispute_haircut + opp_cost`

    Returns exact required threshold `min_pi_hat_required`, conservative net EV, and
    profit per dollar-day committed.
    """
    pi_hat, _, _ = resolve_side_probability(
        p_yes_hat, side=side, question_is_negated=question_is_negated
    )
    sig = max(0.0, float(sigma_p))
    sk = max(0.0, float(sigma_k))
    pi_lcb = _clamp(pi_hat - sk * sig, 0.0, 1.0)

    # Reconstruct equivalent conservative p_yes for hold-to-settlement evaluation
    side_norm = str(side).strip().upper()
    p_yes_lcb = pi_lcb if side_norm == "YES" else (1.0 - pi_lcb)
    p_yes_point = pi_hat if side_norm == "YES" else (1.0 - pi_hat)

    val_point = evaluate_hold_to_settlement(
        p_yes_true=p_yes_point,
        entry_price=entry_ask_price,
        lockup_days=lockup_days,
        side=side_norm,
        question_is_negated=False,
        entry_slippage_per_share=entry_slippage_per_share,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker_entry=is_maker_entry,
        maker_rebate_rate=maker_rebate_rate,
        p_uma_dispute=p_uma_dispute,
        dispute_payout_per_share=dispute_payout_per_share,
        dispute_extra_lockup_days=dispute_extra_lockup_days,
        r_opp_per_day=r_opp_per_day,
        tick_size=tick_size,
    )
    val_lcb = evaluate_hold_to_settlement(
        p_yes_true=p_yes_lcb,
        entry_price=entry_ask_price,
        lockup_days=lockup_days,
        side=side_norm,
        question_is_negated=False,
        entry_slippage_per_share=entry_slippage_per_share,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker_entry=is_maker_entry,
        maker_rebate_rate=maker_rebate_rate,
        p_uma_dispute=p_uma_dispute,
        dispute_payout_per_share=dispute_payout_per_share,
        dispute_extra_lockup_days=dispute_extra_lockup_days,
        r_opp_per_day=r_opp_per_day,
        tick_size=tick_size,
    )

    min_pi_lcb = val_lcb.breakeven_pi_side + max(0.0, float(min_net_edge_per_share)) / max(
        1e-9, 1.0 - _clamp(p_uma_dispute, 0.0, 0.999)
    )
    min_pi_hat_required = _clamp(min_pi_lcb + sk * sig, 0.0, 1.0)
    passes = bool(val_lcb.ev_econ_per_share >= float(min_net_edge_per_share) and pi_hat >= min_pi_hat_required)

    return {
        "passes_entry_gate": passes,
        "side": side_norm,
        "pi_hat": pi_hat,
        "sigma_p": sig,
        "sigma_k": sk,
        "pi_lcb": pi_lcb,
        "entry_ask_exec": val_lcb.entry_ask_price,
        "all_in_cost_per_share": val_lcb.capital_committed_per_share,
        "breakeven_pi_no_uncertainty": val_lcb.breakeven_pi_side,
        "min_pi_hat_required": min_pi_hat_required,
        "point_ev_econ_per_share": val_point.ev_econ_per_share,
        "conservative_ev_econ_per_share": val_lcb.ev_econ_per_share,
        "point_profit_per_dollar_day": val_point.profit_per_dollar_day_econ,
        "conservative_profit_per_dollar_day": val_lcb.profit_per_dollar_day_econ,
        "negative_skew_tail_warning": val_lcb.negative_skew_tail_warning,
    }


def optimal_dynamic_exit_rule(
    current_bid_price: float,
    remaining_days_to_settlement: float,
    posterior_pi_side: float,
    posterior_sigma_p: float = 0.0,
    sigma_k: float = 1.0,
    exit_slippage_per_share: float = 0.0,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    p_uma_dispute: float = 0.002,
    dispute_payout_per_share: float = 0.0,
    dispute_extra_lockup_days: float = 7.0,
    r_opp_per_day: float = 0.005,
    replacement_signal_ppdd: float = 0.0,
) -> Dict[str, Any]:
    """Optimal stopping / early-exit rule for an already-held directional position.

    Compares immediate secondary-market liquidation proceeds `V_liq(t)` against the
    uncertainty-penalized continuation value `V_hold(t)` over `remaining_days_to_settlement`.

    Triggers `should_exit_now = True` when ANY of the following holds:
      1. `REVERSAL_OR_TARGET_CONVERGED`: `V_hold_LCB <= V_liq` (e.g., bid reached `98.5c`
         on a `99c` posterior, or thesis invalidated so posterior dropped below current bid).
      2. `BELOW_OPPORTUNITY_OR_REPLACEMENT_VELOCITY`: remaining edge per dollar-day locked in
         `V_liq` is strictly below `max(r_opp_per_day, replacement_signal_ppdd)`.
    """
    if not (0.0 < float(current_bid_price) < 1.0):
        raise ValueError(f"current_bid_price must be in (0, 1), got {current_bid_price!r}")

    bid_exec = _clamp(float(current_bid_price) - max(0.0, float(exit_slippage_per_share)), 0.0001, 0.9999)
    exit_fee = compute_polymarket_fee_per_share(
        bid_exec,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=False,
    )
    v_liq = max(0.0001, bid_exec - exit_fee)

    pi_lcb = _clamp(float(posterior_pi_side) - max(0.0, float(sigma_k)) * max(0.0, float(posterior_sigma_p)), 0.0, 1.0)
    p_disp = _clamp(float(p_uma_dispute), 0.0, 0.999)
    v_disp = _clamp(float(dispute_payout_per_share), 0.0, 1.0)

    v_hold_lcb = (1.0 - p_disp) * pi_lcb + p_disp * v_disp
    rem_edge = v_hold_lcb - v_liq

    eff_rem_days = max(
        MIN_LOCKUP_DAYS,
        max(0.0, float(remaining_days_to_settlement)) + p_disp * max(0.0, float(dispute_extra_lockup_days)),
    )
    rem_edge_ppdd = rem_edge / (v_liq * eff_rem_days)
    hurdle_ppdd = max(0.0, float(r_opp_per_day), float(replacement_signal_ppdd))

    if float(posterior_pi_side) < v_liq:
        reason = "THESIS_REVERSAL_POSTERIOR_BELOW_NET_BID"
        exit_now = True
    elif rem_edge <= 0.0:
        reason = "PRICE_CONVERGED_ZERO_REMAINING_EDGE"
        exit_now = True
    elif rem_edge_ppdd < hurdle_ppdd:
        reason = "REMAINING_VELOCITY_BELOW_OPPORTUNITY_COST"
        exit_now = True
    else:
        reason = "HOLD_CONTINUATION_OPTIMAL"
        exit_now = False

    return {
        "should_exit_now": exit_now,
        "decision_reason": reason,
        "net_liquidation_value_per_share": v_liq,
        "continuation_value_lcb_per_share": v_hold_lcb,
        "remaining_net_edge_per_share": rem_edge,
        "effective_remaining_days": eff_rem_days,
        "remaining_profit_per_dollar_day": rem_edge_ppdd,
        "required_hurdle_per_dollar_day": hurdle_ppdd,
    }


def compare_hold_vs_exit(
    hold_valuation: HoldToSettlementValuation,
    exit_valuation: PreResolutionExitValuation,
) -> Dict[str, Any]:
    """Directly compares Hold-to-Settlement vs Pre-Resolution Trading Exit on the same entry."""
    hold_ppdd = hold_valuation.profit_per_dollar_day_econ
    exit_ppdd = exit_valuation.profit_per_dollar_day_econ
    hold_ev = hold_valuation.ev_econ_per_share
    exit_ev = exit_valuation.ev_econ_per_share

    if max(hold_ev, exit_ev) <= 0.0:
        optimal_mode = "ABSTAIN_NEGATIVE_NET_EV"
    elif exit_ev > 0.0 and exit_ppdd > hold_ppdd:
        optimal_mode = "PRE_RESOLUTION_EXIT"
    else:
        optimal_mode = "HOLD_TO_SETTLEMENT"

    return {
        "optimal_execution_mechanism": optimal_mode,
        "hold_ev_econ_per_share": hold_ev,
        "exit_ev_econ_per_share": exit_ev,
        "hold_profit_per_dollar_day_econ": hold_ppdd,
        "exit_profit_per_dollar_day_econ": exit_ppdd,
        "velocity_ratio_exit_over_hold": (exit_ppdd / hold_ppdd) if abs(hold_ppdd) > 1e-12 else None,
        "hold_cvar_95_per_share": hold_valuation.cvar_95_per_share,
        "exit_cvar_95_per_share": exit_valuation.cvar_95_per_share,
    }

"""Agent G — Multi-Strategy Portfolio Optimization, Uncertainty-Penalized Kelly & Scale Engine.

Implements:
1. **Uncertainty-Penalized Fractional Kelly Sizing (`uncertainty_penalized_kelly_*`)**:
   - Solves exact concave expected log-wealth maximization over binary settlement (including
     3-state UMA dispute risk) and arbitrary pre-resolution secondary-market exit scenarios.
   - Shrinks Kelly fraction monotonically by epistemic estimation variance `Var(p_hat) = sigma_p^2`
     via both conservative lower-confidence-bound drift (`p_hat - z_amb * sigma_p`) and
     Baker-McHale empirical-Bayes parameter-error shrinkage `e^2 / (e^2 + eta * sigma_p^2)`.

2. **Polymarket Lot-Size Quantization (`5` shares / `$1.00`) & L2 Depth Impact Concavity**:
   - Proves mathematically and via continuous-time capital-lockup simulation what happens across:
     * **Tier 1 (`$48.81` actual Dominus liquid cash; `$0.8223/day` = `168.48 bps/day` VM hurdle)**
     * **Tier 2 (`$500.00` diversified small-quant account)**
     * **Tier 3 (`$5,000.00` & `$25,000.00` depth-constrained scalable accounts)**
   - Solves exact marginal-zero dollar capacity ceilings `Q_cap* = argmax_Q NetEV(Q)` where
     concave L2 order-book impact saturates alpha.

3. **Multi-Strategy Correlation, Hidden Shared-Factor Tail Risk & OOS Portfolio Combiner**:
   - Fits cluster- and uncertainty-penalized convex QP weights strictly on Train/Validation
     splits (zero out-of-sample peeking) and tests empirically on Out-of-Sample trade logs
     whether combining directional strategies genuinely improves Sharpe, Sortino, `CVaR_95`,
     Calmar/MaxDD, and net `$/day` vs standalone strategies and `DOMINUS RISKLESS` (`BOND1`/`D1`).

Pure Python 3.12 stdlib implementation (zero numpy/pandas dependencies).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import random
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from src.directional_alpha.probability_and_payoff import (
        MIN_LOCKUP_DAYS,
        compute_polymarket_fee_per_share,
        resolve_side_probability,
    )
except ImportError:
    from directional_alpha.probability_and_payoff import (
        MIN_LOCKUP_DAYS,
        compute_polymarket_fee_per_share,
        resolve_side_probability,
    )

# Authoritative Dominus v5.2 Reconciled Baseline Constants (`DEPLOYMENT_STATUS.md` / `PROJECT_STATE.md`)
DOMINUS_TIER1_CASH_USD: float = 48.81  # $48.807132 settled pUSD post-Wave-3.1
DOMINUS_TIER2_CASH_USD: float = 500.00
DOMINUS_TIER3_CASH_USD: float = 5000.00
DOMINUS_TIER3B_CASH_USD: float = 25000.00

DOMINUS_VM_MONTHLY_USD: float = 24.67
DOMINUS_VM_DAILY_USD: float = 24.67 / 30.0  # $0.822333/day

POLYMARKET_MIN_SHARES: float = 5.0
POLYMARKET_MIN_ORDER_USD: float = 1.00
DEFAULT_EVENT_CAP_FRAC: float = 0.15  # D-007 <= 15% reconciled NAV per correlated event
DEFAULT_CATEGORY_CAP_FRAC: float = 0.35

# Conservative realized + live quoting benchmark for DOMINUS RISKLESS (`D1` + `BOND1` + `MKR_LOCK1`)
DOMINUS_RISKLESS_DAILY_YIELD_CONSERVATIVE: float = 0.0085  # +85 bps/day conservative net velocity
DOMINUS_RISKLESS_CAPACITY_SOFT_CAP_USD: float = 3500.0  # single-venue fast-box / post-clinch soft depth


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def _norm_inv_approx(u: float) -> float:
    """Rational Acklam-style inverse standard normal CDF accurate to ~4e-4 across (0, 1)."""
    p = _clamp(u, 1e-9, 1.0 - 1e-9)
    # Beasley-Springer-Moro rational approximation
    a = (-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.3577518672690, -30.66479806614716, 2.506628277459239)
    b = (-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572)
    c = (-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783)
    d = (0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416)
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
        )
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
    )


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(float(z) / math.sqrt(2.0)))


# ==============================================================================
# 1. UNCERTAINTY-PENALIZED FRACTIONAL KELLY SIZING
# ==============================================================================


@dataclass(frozen=True)
class KellySizingResult:
    """Exact and uncertainty-penalized Kelly sizing diagnostics."""

    plugin_full_kelly_fraction: float
    lcb_full_kelly_fraction: float
    bayesian_shrinkage_factor: float
    fractional_kelly_multiplier: float
    recommended_fraction: float
    capped_fraction: float
    expected_return_per_dollar_point: float
    expected_return_per_dollar_lcb: float
    epistemic_return_std: float
    expected_log_growth_plugin_under_uncertainty: float
    expected_log_growth_recommended_under_uncertainty: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def solve_exact_discrete_kelly(
    returns_and_probs: Sequence[Tuple[float, float]],
    max_fraction: float = 0.99,
) -> float:
    """Maximizes exact expected log-wealth `G(f) = sum_i p_i * ln(1 + f * R_i)` via bisection.

    Unlike quadratic `mu / sigma^2` Gaussian approximations, exact discrete optimization
    strictly respects fat negative tails (`R_i = -1.0` full loss on binary or gapped stops)
    and never recommends `f >= 1 / |R_min|`.
    """
    valid = [(float(r), float(p)) for r, p in returns_and_probs if float(p) > 0.0]
    if not valid:
        return 0.0
    p_sum = sum(p for _, p in valid)
    norm = [(r, p / p_sum) for r, p in valid]

    # First derivative at f = 0 is E[R]
    mu = sum(r * p for r, p in norm)
    if mu <= 1e-12:
        return 0.0

    worst_loss = min(r for r, _ in norm)
    if worst_loss >= 0.0:
        return _clamp(max_fraction, 0.0, 1.0)

    upper_singularity = (1.0 / abs(worst_loss)) * 0.9999
    hi = min(float(max_fraction), upper_singularity)
    if hi <= 0.0:
        return 0.0

    def grad(f: float) -> float:
        return sum((p * r) / (1.0 + f * r) for r, p in norm)

    if grad(hi) >= 0.0:
        return hi

    lo = 0.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if grad(mid) > 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-11:
            break
    return 0.5 * (lo + hi)


# Exact 7-point Gauss-Hermite nodes (for standard normal Z ~ N(0, 1)) and weights
_GH7_Z_AND_W: Tuple[Tuple[float, float], ...] = (
    (-3.750439717725742, 0.000548268855972),
    (-2.366759410734541, 0.030757123967586),
    (-1.154405394739968, 0.240123178605013),
    (0.0, 0.457142857142857),
    (1.154405394739968, 0.240123178605013),
    (2.366759410734541, 0.030757123967586),
    (3.750439717725742, 0.000548268855972),
)


def _expected_log_growth_rule_under_prob_error(
    pi_true_anchor: float,
    sigma_p: float,
    all_in_cost: float,
    sizing_rule: str,
    kelly_multiplier: float = 0.25,
    ambiguity_z: float = 1.0,
    shrinkage_eta: float = 1.0,
    max_fraction_cap: float = 0.99,
    p_uma_dispute: float = 0.0,
    dispute_payout: float = 0.0,
) -> float:
    """Exact 7-point Gauss-Hermite expectation `E_{eps ~ N(0, sigma_p^2)}[G(f(pi + eps); pi)]`.

    Proves without Taylor approximation how noisy point estimates `pi_obs = pi + eps` cause
    plug-in Full Kelly (`sizing_rule="plugin"`) to over-bet `f > 2 * f*` into negative
    geometric growth, whereas Uncertainty-Penalized Kelly (`sizing_rule="upk"`) preserves
    positive out-of-sample compounding.
    """
    c = _clamp(all_in_cost, 1e-4, 0.9999)
    r_win = (1.0 - c) / c
    r_loss = -1.0
    r_disp = (dispute_payout - c) / c
    p_d = _clamp(p_uma_dispute, 0.0, 0.999)
    pi_true = _clamp(pi_true_anchor, 0.0001, 0.9999)
    p_w_true = (1.0 - p_d) * pi_true
    p_l_true = (1.0 - p_d) * (1.0 - pi_true)

    def _g_realized(f_bet: float) -> float:
        if f_bet <= 1e-12:
            return 0.0
        if 1.0 + f_bet * r_loss <= 1e-12 or 1.0 + f_bet * r_disp <= 1e-12:
            return -50.0
        return (
            p_w_true * math.log(1.0 + f_bet * r_win)
            + p_l_true * math.log(1.0 + f_bet * r_loss)
            + p_d * math.log(1.0 + f_bet * r_disp)
        )

    def _rule_f(pi_obs: float) -> float:
        dist_obs = [
            (r_win, (1.0 - p_d) * pi_obs),
            (r_loss, (1.0 - p_d) * (1.0 - pi_obs)),
            (r_disp, p_d),
        ]
        if sizing_rule == "plugin":
            return solve_exact_discrete_kelly(dist_obs, max_fraction=0.99)
        pi_lcb = _clamp(pi_obs - max(0.0, ambiguity_z) * sigma_p, 0.0, 1.0)
        dist_lcb = [
            (r_win, (1.0 - p_d) * pi_lcb),
            (r_loss, (1.0 - p_d) * (1.0 - pi_lcb)),
            (r_disp, p_d),
        ]
        f_l = solve_exact_discrete_kelly(dist_lcb, max_fraction=0.99)
        mu_obs = sum(r * p for r, p in dist_obs)
        sigma_mu = ((1.0 - p_d) / c) * sigma_p
        if mu_obs <= 0.0 or f_l <= 0.0:
            return 0.0
        sh = 1.0 if sigma_mu <= 1e-12 else (mu_obs ** 2) / ((mu_obs ** 2) + max(0.0, shrinkage_eta) * (sigma_mu ** 2))
        return min(max_fraction_cap, kelly_multiplier * f_l * sh)

    if sigma_p <= 1e-12:
        return _g_realized(_rule_f(pi_true))

    total_g = 0.0
    for z_node, w_node in _GH7_Z_AND_W:
        pi_obs = _clamp(pi_true + sigma_p * z_node, 0.001, 0.999)
        total_g += w_node * _g_realized(_rule_f(pi_obs))
    return total_g


def uncertainty_penalized_kelly_binary(
    p_yes_hat: float,
    sigma_p: float,
    entry_ask_price: float,
    side: str = "YES",
    question_is_negated: bool = False,
    entry_slippage_per_share: float = 0.0,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    is_maker_entry: bool = False,
    maker_rebate_rate: float = 0.0,
    p_uma_dispute: float = 0.002,
    dispute_payout_per_share: float = 0.0,
    kelly_multiplier: float = 0.25,
    ambiguity_z: float = 1.0,
    shrinkage_eta: float = 1.0,
    max_fraction_cap: float = 0.15,
) -> KellySizingResult:
    """Computes Uncertainty-Penalized Fractional Kelly for a Hold-to-Settlement binary trade.

    Guarantees:
      1. Recovers exact `kelly_multiplier * f_star` when `sigma_p == 0`.
      2. Strictly monotonically decreasing in `Var(p_hat) = sigma_p^2`.
      3. Shrinks cleanly to `0.0` whenever `pi_hat - ambiguity_z * sigma_p <= breakeven`.
    """
    pi_hat, _, _ = resolve_side_probability(
        p_yes_hat, side=side, question_is_negated=question_is_negated
    )
    sig = max(0.0, float(sigma_p))
    exec_px = _clamp(float(entry_ask_price) + max(0.0, float(entry_slippage_per_share)), 0.0001, 0.9999)
    fee = compute_polymarket_fee_per_share(
        exec_px,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=is_maker_entry,
        maker_rebate_rate=maker_rebate_rate,
    )
    c = _clamp(exec_px + fee, 0.0001, 0.9999)
    p_disp = _clamp(float(p_uma_dispute), 0.0, 0.999)
    v_disp = _clamp(float(dispute_payout_per_share), 0.0, 1.0)

    r_win = (1.0 - c) / c
    r_loss = -1.0
    r_disp = (v_disp - c) / c

    def _build_dist(pi_val: float) -> List[Tuple[float, float]]:
        return [
            (r_win, (1.0 - p_disp) * pi_val),
            (r_loss, (1.0 - p_disp) * (1.0 - pi_val)),
            (r_disp, p_disp),
        ]

    dist_point = _build_dist(pi_hat)
    pi_lcb = _clamp(pi_hat - max(0.0, float(ambiguity_z)) * sig, 0.0, 1.0)
    dist_lcb = _build_dist(pi_lcb)

    f_plugin = solve_exact_discrete_kelly(dist_point, max_fraction=0.99)
    f_lcb = solve_exact_discrete_kelly(dist_lcb, max_fraction=0.99)

    mu_point = sum(r * p for r, p in dist_point)
    mu_lcb = sum(r * p for r, p in dist_lcb)
    # Epistemic standard error of per-dollar return: d(E[R])/dpi = (1 - p_disp) / c
    sigma_mu = ((1.0 - p_disp) / c) * sig

    if mu_point <= 0.0 or f_lcb <= 0.0:
        shrink = 0.0
    elif sig <= 1e-12:
        shrink = 1.0
    else:
        edge_sq = mu_point ** 2
        shrink = edge_sq / (edge_sq + max(0.0, float(shrinkage_eta)) * (sigma_mu ** 2))

    gamma = _clamp(float(kelly_multiplier), 0.0, 1.0)
    f_rec = gamma * f_lcb * shrink
    f_cap = min(f_rec, max(0.0, float(max_fraction_cap)))

    g_plugin = _expected_log_growth_rule_under_prob_error(
        pi_hat,
        sig,
        c,
        sizing_rule="plugin",
        p_uma_dispute=p_disp,
        dispute_payout=v_disp,
    )
    g_rec = _expected_log_growth_rule_under_prob_error(
        pi_hat,
        sig,
        c,
        sizing_rule="upk",
        kelly_multiplier=gamma,
        ambiguity_z=float(ambiguity_z),
        shrinkage_eta=float(shrinkage_eta),
        max_fraction_cap=max(0.0, float(max_fraction_cap)),
        p_uma_dispute=p_disp,
        dispute_payout=v_disp,
    )

    return KellySizingResult(
        plugin_full_kelly_fraction=f_plugin,
        lcb_full_kelly_fraction=f_lcb,
        bayesian_shrinkage_factor=shrink,
        fractional_kelly_multiplier=gamma,
        recommended_fraction=f_rec,
        capped_fraction=f_cap,
        expected_return_per_dollar_point=mu_point,
        expected_return_per_dollar_lcb=mu_lcb,
        epistemic_return_std=sigma_mu,
        expected_log_growth_plugin_under_uncertainty=g_plugin,
        expected_log_growth_recommended_under_uncertainty=g_rec,
    )


def uncertainty_penalized_kelly_scenarios(
    pnl_per_share_and_probs: Sequence[Tuple[float, float]],
    capital_committed_per_share: float,
    epistemic_edge_std_per_share: float = 0.0,
    kelly_multiplier: float = 0.25,
    ambiguity_z: float = 1.0,
    shrinkage_eta: float = 1.0,
    max_fraction_cap: float = 0.15,
) -> KellySizingResult:
    """Computes Uncertainty-Penalized Fractional Kelly for Pre-Resolution Exit distributions."""
    c = max(1e-4, float(capital_committed_per_share))
    sig_edge = max(0.0, float(epistemic_edge_std_per_share))
    sigma_mu = sig_edge / c

    returns_point = [(_clamp(pnl / c, -1.0, 100.0), float(w)) for pnl, w in pnl_per_share_and_probs if float(w) > 0.0]
    shift = max(0.0, float(ambiguity_z)) * sigma_mu
    returns_lcb = [(_clamp(r - shift, -1.0, 100.0), w) for r, w in returns_point]

    f_plugin = solve_exact_discrete_kelly(returns_point, max_fraction=0.99)
    f_lcb = solve_exact_discrete_kelly(returns_lcb, max_fraction=0.99)

    p_sum = sum(w for _, w in returns_point) or 1.0
    mu_point = sum(r * w for r, w in returns_point) / p_sum
    mu_lcb = sum(r * w for r, w in returns_lcb) / p_sum

    if mu_point <= 0.0 or f_lcb <= 0.0:
        shrink = 0.0
    elif sigma_mu <= 1e-12:
        shrink = 1.0
    else:
        shrink = (mu_point ** 2) / ((mu_point ** 2) + max(0.0, float(shrinkage_eta)) * (sigma_mu ** 2))

    gamma = _clamp(float(kelly_multiplier), 0.0, 1.0)
    f_rec = gamma * f_lcb * shrink
    f_cap = min(f_rec, max(0.0, float(max_fraction_cap)))

    def _eval_g(f_val: float) -> float:
        if f_val <= 1e-12:
            return 0.0
        g0 = 0.0
        curv = 0.0
        for r, w in returns_point:
            wn = w / p_sum
            if 1.0 + f_val * r <= 1e-12:
                return -float("inf")
            g0 += wn * math.log(1.0 + f_val * r)
            curv += wn * ((r / (1.0 + f_val * r)) ** 2)
        ratio = min(2.0, f_val / max(1e-6, f_plugin)) if f_plugin > 0 else 0.0
        # Sensitivity df/dmu ~ 1 / Var(R)
        var_r = max(1e-4, sum((w / p_sum) * ((r - mu_point) ** 2) for r, w in returns_point))
        var_f = ((ratio / var_r) ** 2) * (sigma_mu ** 2)
        return g0 - 0.5 * curv * var_f

    return KellySizingResult(
        plugin_full_kelly_fraction=f_plugin,
        lcb_full_kelly_fraction=f_lcb,
        bayesian_shrinkage_factor=shrink,
        fractional_kelly_multiplier=gamma,
        recommended_fraction=f_rec,
        capped_fraction=f_cap,
        expected_return_per_dollar_point=mu_point,
        expected_return_per_dollar_lcb=mu_lcb,
        epistemic_return_std=sigma_mu,
        expected_log_growth_plugin_under_uncertainty=_eval_g(f_plugin),
        expected_log_growth_recommended_under_uncertainty=_eval_g(f_cap),
    )


# ==============================================================================
# 2. MINIMUM LOT QUANTIZATION (`5` SHARES / `$1`) & L2 DEPTH IMPACT CONCAVITY
# ==============================================================================


def estimate_l2_depth_slippage_per_share(
    order_notional_usd: float,
    entry_ask_price: float,
    l1_depth_usd: float = 35.0,
    book_depth_scale_usd: float = 250.0,
    linear_impact_coeff: float = 0.015,
    sqrt_impact_coeff: float = 0.025,
    l2_ask_levels: Optional[Sequence[Tuple[float, float]]] = None,
) -> Tuple[float, float]:
    """Returns `(slippage_per_share, max_fillable_notional_usd)` for an order of size `Q`.

    If explicit `l2_ask_levels = [(price, size_shares), ...]` are provided, walks the exact
    CLOB book rungs. Otherwise uses a two-regime L1 top-of-book + concave square-root/linear
    depth exhaustion curve calibrated to Polymarket order books.
    """
    q = max(0.0, float(order_notional_usd))
    p0 = _clamp(float(entry_ask_price), 0.001, 0.999)
    if q <= 0.0:
        return 0.0, 0.0

    if l2_ask_levels:
        sorted_lvls = sorted(
            [(float(px), float(sz)) for px, sz in l2_ask_levels if float(px) > 0.0 and float(sz) > 0.0],
            key=lambda item: item[0],
        )
        if not sorted_lvls:
            return 0.0, 0.0
        best_ask = sorted_lvls[0][0]
        max_usd = sum(px * sz for px, sz in sorted_lvls)
        rem_usd = min(q, max_usd)
        total_shares = 0.0
        spent_usd = 0.0
        for px, sz in sorted_lvls:
            lvl_usd = px * sz
            take_usd = min(rem_usd, lvl_usd)
            total_shares += take_usd / px
            spent_usd += take_usd
            rem_usd -= take_usd
            if rem_usd <= 1e-9:
                break
        vwap = (spent_usd / total_shares) if total_shares > 0.0 else best_ask
        # Unfilled remainder beyond visible book incurs severe walk-the-book penalty
        if q > max_usd:
            excess_ratio = (q - max_usd) / max(25.0, max_usd)
            vwap = min(0.999, vwap + 0.04 * excess_ratio + 0.03 * math.sqrt(excess_ratio))
        return max(0.0, vwap - best_ask), max_usd

    d1 = max(1.0, float(l1_depth_usd))
    d_scale = max(10.0, float(book_depth_scale_usd))
    if q <= d1:
        return 0.0, d1 + 4.0 * d_scale

    excess = (q - d1) / d_scale
    slip = float(linear_impact_coeff) * excess + float(sqrt_impact_coeff) * math.sqrt(excess)
    return min(max(0.0, 0.999 - p0), slip), d1 + 4.0 * d_scale


@dataclass(frozen=True)
class QuantizedOrderDecision:
    """Executable order decision after Polymarket 5-share/$1 min-lot, 15% cap, and L2 impact."""

    executable: bool
    reject_reason: str
    bankroll_usd: float
    target_kelly_usd: float
    event_cap_usd: float
    min_legal_order_usd: float
    final_notional_usd: float
    final_shares: float
    entry_ask_price: float
    estimated_slippage_per_share: float
    all_in_cost_per_share: float
    quantization_overbet_ratio: float
    expected_net_profit_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def quantize_and_cap_order(
    bankroll_usd: float,
    free_cash_usd: float,
    kelly_result: KellySizingResult,
    pi_side_lcb: float,
    entry_ask_price: float,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    is_maker_entry: bool = False,
    maker_rebate_rate: float = 0.0,
    p_uma_dispute: float = 0.002,
    dispute_payout_per_share: float = 0.0,
    l1_depth_usd: float = 35.0,
    book_depth_scale_usd: float = 250.0,
    event_cap_frac: float = DEFAULT_EVENT_CAP_FRAC,
    existing_event_exposure_usd: float = 0.0,
    min_shares: float = POLYMARKET_MIN_SHARES,
    min_order_usd: float = POLYMARKET_MIN_ORDER_USD,
    allow_min_lot_round_up: bool = False,
    max_round_up_over_plugin_kelly: float = 0.85,
    precomputed_optimal_clip_usd: Optional[float] = None,
) -> QuantizedOrderDecision:
    """Applies Polymarket 5-share / $1.00 minimum lot, 15% event cap, cash headroom, and L2 impact."""
    nav = max(0.0, float(bankroll_usd))
    cash = max(0.0, float(free_cash_usd))
    p_ask = _clamp(float(entry_ask_price), 0.001, 0.999)

    base_fee = compute_polymarket_fee_per_share(
        p_ask,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=is_maker_entry,
        maker_rebate_rate=maker_rebate_rate,
    )
    unit_cost_0 = p_ask + base_fee
    min_legal_usd = max(float(min_order_usd), float(min_shares) * unit_cost_0)
    event_cap_total = nav * _clamp(float(event_cap_frac), 0.01, 1.0)
    event_headroom = max(0.0, event_cap_total - max(0.0, float(existing_event_exposure_usd)))
    target_usd = nav * kelly_result.recommended_fraction

    if kelly_result.recommended_fraction <= 1e-9 or target_usd <= 0.0:
        return QuantizedOrderDecision(
            executable=False,
            reject_reason="ZERO_POSITIVE_KELLY_EDGE",
            bankroll_usd=nav,
            target_kelly_usd=0.0,
            event_cap_usd=event_headroom,
            min_legal_order_usd=min_legal_usd,
            final_notional_usd=0.0,
            final_shares=0.0,
            entry_ask_price=p_ask,
            estimated_slippage_per_share=0.0,
            all_in_cost_per_share=unit_cost_0,
            quantization_overbet_ratio=0.0,
            expected_net_profit_usd=0.0,
        )

    desired_usd = min(target_usd, event_headroom, cash)
    overbet_ratio = 1.0

    if desired_usd < min_legal_usd - 1e-9:
        if not allow_min_lot_round_up:
            reason = (
                "INSUFFICIENT_FREE_CASH_FOR_MIN_LOT"
                if cash < min_legal_usd
                else (
                    "EVENT_CAP_BELOW_POLYMARKET_MIN_LOT"
                    if event_headroom < min_legal_usd
                    else "KELLY_SIZE_BELOW_POLYMARKET_5SH_MIN_LOT"
                )
            )
            return QuantizedOrderDecision(
                executable=False,
                reject_reason=reason,
                bankroll_usd=nav,
                target_kelly_usd=target_usd,
                event_cap_usd=event_headroom,
                min_legal_order_usd=min_legal_usd,
                final_notional_usd=0.0,
                final_shares=0.0,
                entry_ask_price=p_ask,
                estimated_slippage_per_share=0.0,
                all_in_cost_per_share=unit_cost_0,
                quantization_overbet_ratio=min_legal_usd / max(1e-6, target_usd),
                expected_net_profit_usd=0.0,
            )
        # Check if rounding up to min lot breaches cash, event cap, or safe Full-Kelly ceiling
        if cash < min_legal_usd or event_headroom < min_legal_usd:
            return QuantizedOrderDecision(
                executable=False,
                reject_reason="MIN_LOT_EXCEEDS_CASH_OR_15PCT_EVENT_CAP",
                bankroll_usd=nav,
                target_kelly_usd=target_usd,
                event_cap_usd=event_headroom,
                min_legal_order_usd=min_legal_usd,
                final_notional_usd=0.0,
                final_shares=0.0,
                entry_ask_price=p_ask,
                estimated_slippage_per_share=0.0,
                all_in_cost_per_share=unit_cost_0,
                quantization_overbet_ratio=min_legal_usd / max(1e-6, target_usd),
                expected_net_profit_usd=0.0,
            )
        full_kelly_usd = nav * kelly_result.lcb_full_kelly_fraction
        if min_legal_usd > max(0.0, float(max_round_up_over_plugin_kelly)) * full_kelly_usd:
            return QuantizedOrderDecision(
                executable=False,
                reject_reason="MIN_LOT_ROUNDUP_BREACHES_FULL_KELLY_RUIN_BOUND",
                bankroll_usd=nav,
                target_kelly_usd=target_usd,
                event_cap_usd=event_headroom,
                min_legal_order_usd=min_legal_usd,
                final_notional_usd=0.0,
                final_shares=0.0,
                entry_ask_price=p_ask,
                estimated_slippage_per_share=0.0,
                all_in_cost_per_share=unit_cost_0,
                quantization_overbet_ratio=min_legal_usd / max(1e-6, target_usd),
                expected_net_profit_usd=0.0,
            )
        desired_usd = min_legal_usd
        overbet_ratio = desired_usd / max(1e-6, target_usd)

    # Evaluate L2 market-impact concavity and ensure we never exceed marginal-zero capacity!
    if precomputed_optimal_clip_usd is not None:
        opt_clip_usd = float(precomputed_optimal_clip_usd)
    else:
        cap_curve = compute_strategy_capacity_curve(
            pi_side_lcb=pi_side_lcb,
            entry_ask_price=p_ask,
            fee_rate=fee_rate,
            fee_exponent=fee_exponent,
            is_maker_entry=is_maker_entry,
            maker_rebate_rate=maker_rebate_rate,
            p_uma_dispute=p_uma_dispute,
            dispute_payout_per_share=dispute_payout_per_share,
            l1_depth_usd=l1_depth_usd,
            book_depth_scale_usd=book_depth_scale_usd,
        )
        opt_clip_usd = cap_curve["optimal_clip_usd"]
    if opt_clip_usd < min_legal_usd:
        return QuantizedOrderDecision(
            executable=False,
            reject_reason="DEPTH_IMPACT_WIPES_EDGE_AT_MIN_LOT",
            bankroll_usd=nav,
            target_kelly_usd=target_usd,
            event_cap_usd=event_headroom,
            min_legal_order_usd=min_legal_usd,
            final_notional_usd=0.0,
            final_shares=0.0,
            entry_ask_price=p_ask,
            estimated_slippage_per_share=0.0,
            all_in_cost_per_share=unit_cost_0,
            quantization_overbet_ratio=overbet_ratio,
            expected_net_profit_usd=0.0,
        )

    final_usd = min(desired_usd, opt_clip_usd)
    slip_sh, _ = estimate_l2_depth_slippage_per_share(
        final_usd,
        entry_ask_price=p_ask,
        l1_depth_usd=l1_depth_usd,
        book_depth_scale_usd=book_depth_scale_usd,
    )
    exec_px = _clamp(p_ask + slip_sh, 0.001, 0.999)
    eff_fee = compute_polymarket_fee_per_share(
        exec_px,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=is_maker_entry,
        maker_rebate_rate=maker_rebate_rate,
    )
    all_in_sh = exec_px + eff_fee
    # Quantize shares to 0.01 share increments while keeping >= min_shares
    raw_shares = final_usd / all_in_sh
    shares = math.floor(raw_shares * 100.0 + 1e-9) / 100.0
    if shares < float(min_shares):
        if cash >= float(min_shares) * all_in_sh and event_headroom >= float(min_shares) * all_in_sh and allow_min_lot_round_up:
            shares = float(min_shares)
        else:
            return QuantizedOrderDecision(
                executable=False,
                reject_reason="POST_SLIPPAGE_SHARES_BELOW_5SH_MINIMUM",
                bankroll_usd=nav,
                target_kelly_usd=target_usd,
                event_cap_usd=event_headroom,
                min_legal_order_usd=min_legal_usd,
                final_notional_usd=0.0,
                final_shares=0.0,
                entry_ask_price=p_ask,
                estimated_slippage_per_share=slip_sh,
                all_in_cost_per_share=all_in_sh,
                quantization_overbet_ratio=overbet_ratio,
                expected_net_profit_usd=0.0,
            )

    committed_usd = shares * all_in_sh
    p_disp = _clamp(float(p_uma_dispute), 0.0, 0.999)
    exp_payout_sh = (1.0 - p_disp) * _clamp(float(pi_side_lcb), 0.0, 1.0) + p_disp * _clamp(float(dispute_payout_per_share), 0.0, 1.0)
    ev_usd = shares * (exp_payout_sh - all_in_sh)

    if ev_usd <= 0.0:
        return QuantizedOrderDecision(
            executable=False,
            reject_reason="NEGATIVE_EV_AFTER_SLIPPAGE_AND_FEES",
            bankroll_usd=nav,
            target_kelly_usd=target_usd,
            event_cap_usd=event_headroom,
            min_legal_order_usd=min_legal_usd,
            final_notional_usd=0.0,
            final_shares=0.0,
            entry_ask_price=p_ask,
            estimated_slippage_per_share=slip_sh,
            all_in_cost_per_share=all_in_sh,
            quantization_overbet_ratio=overbet_ratio,
            expected_net_profit_usd=ev_usd,
        )

    return QuantizedOrderDecision(
        executable=True,
        reject_reason="",
        bankroll_usd=nav,
        target_kelly_usd=target_usd,
        event_cap_usd=event_headroom,
        min_legal_order_usd=min_legal_usd,
        final_notional_usd=committed_usd,
        final_shares=shares,
        entry_ask_price=p_ask,
        estimated_slippage_per_share=slip_sh,
        all_in_cost_per_share=all_in_sh,
        quantization_overbet_ratio=committed_usd / max(1e-6, target_usd),
        expected_net_profit_usd=ev_usd,
    )


def compute_strategy_capacity_curve(
    pi_side_lcb: float,
    entry_ask_price: float,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    is_maker_entry: bool = False,
    maker_rebate_rate: float = 0.0,
    p_uma_dispute: float = 0.002,
    dispute_payout_per_share: float = 0.0,
    l1_depth_usd: float = 35.0,
    book_depth_scale_usd: float = 250.0,
    opportunities_per_day: float = 2.0,
    lockup_days: float = 1.0,
    l2_ask_levels: Optional[Sequence[Tuple[float, float]]] = None,
) -> Dict[str, Any]:
    """Solves exact concave net dollar profit `Pi(Q)` and true dollar capacity ceiling `Q_cap*`.

    Because L2 slippage `s(Q)` increases with clip size `Q`, total dollar profit
    `Pi(Q) = Q * net_roi(Q)` is strictly concave beyond `l1_depth_usd`:
      - `optimal_clip_usd` (`Q_cap*`) is where marginal dollar alpha `dPi/dQ == 0`.
      - `breakeven_clip_usd` (`Q_be`) is where average dollar alpha `Pi(Q) == 0`.
    """
    p_ask = _clamp(float(entry_ask_price), 0.001, 0.999)
    p_disp = _clamp(float(p_uma_dispute), 0.0, 0.999)
    exp_payout = (1.0 - p_disp) * _clamp(float(pi_side_lcb), 0.0, 1.0) + p_disp * _clamp(float(dispute_payout_per_share), 0.0, 1.0)

    def net_ev_for_clip(q_usd: float) -> float:
        if q_usd <= 0.0:
            return 0.0
        slip, _ = estimate_l2_depth_slippage_per_share(
            q_usd,
            entry_ask_price=p_ask,
            l1_depth_usd=l1_depth_usd,
            book_depth_scale_usd=book_depth_scale_usd,
            l2_ask_levels=l2_ask_levels,
        )
        exec_px = _clamp(p_ask + slip, 0.001, 0.9995)
        fee = compute_polymarket_fee_per_share(
            exec_px,
            fee_rate=fee_rate,
            fee_exponent=fee_exponent,
            is_maker=is_maker_entry,
            maker_rebate_rate=maker_rebate_rate,
        )
        cost_sh = exec_px + fee
        shares = q_usd / cost_sh
        return shares * (exp_payout - cost_sh)

    if net_ev_for_clip(1.0) <= 0.0:
        return {
            "optimal_clip_usd": 0.0,
            "max_expected_profit_per_clip_usd": 0.0,
            "breakeven_clip_usd": 0.0,
            "daily_strategy_capacity_usd": 0.0,
            "steady_state_capital_capacity_usd": 0.0,
            "daily_max_net_profit_usd": 0.0,
            "curve_samples": [],
        }

    # Find bracket [0, hi] where net_ev_for_clip(hi) <= 0
    hi = max(float(l1_depth_usd) * 2.0, 50.0)
    while net_ev_for_clip(hi) > 0.0 and hi < 1_000_000.0:
        hi *= 2.0

    # Bisection for breakeven clip Q_be (where Pi(Q) crosses 0)
    lo_be, hi_be = 1.0, hi
    for _ in range(50):
        mid = 0.5 * (lo_be + hi_be)
        if net_ev_for_clip(mid) > 0.0:
            lo_be = mid
        else:
            hi_be = mid
    q_breakeven = 0.5 * (lo_be + hi_be)

    # Golden-section search on [1.0, q_breakeven] for unimodal maximum Q_cap* = argmax Pi(Q)
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = 1.0, q_breakeven
    c_pt = b - gr * (b - a)
    d_pt = a + gr * (b - a)
    fc = net_ev_for_clip(c_pt)
    fd = net_ev_for_clip(d_pt)
    for _ in range(60):
        if fc > fd:
            b = d_pt
            d_pt = c_pt
            fd = fc
            c_pt = b - gr * (b - a)
            fc = net_ev_for_clip(c_pt)
        else:
            a = c_pt
            c_pt = d_pt
            fc = fd
            d_pt = a + gr * (b - a)
            fd = net_ev_for_clip(d_pt)
    q_opt = 0.5 * (a + b)
    pi_opt = max(0.0, net_ev_for_clip(q_opt))

    opp_day = max(0.0, float(opportunities_per_day))
    eff_lock = max(MIN_LOCKUP_DAYS, float(lockup_days))
    daily_vol_cap = opp_day * q_opt
    steady_capital_cap = daily_vol_cap * eff_lock
    daily_max_pnl = opp_day * pi_opt

    sample_grid = [5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0]
    samples = []
    for q_s in sample_grid:
        ev_s = net_ev_for_clip(q_s)
        slip_s, _ = estimate_l2_depth_slippage_per_share(
            q_s, p_ask, l1_depth_usd=l1_depth_usd, book_depth_scale_usd=book_depth_scale_usd, l2_ask_levels=l2_ask_levels
        )
        samples.append(
            {
                "clip_usd": q_s,
                "slippage_bps": round(slip_s * 10000.0, 2),
                "net_ev_usd": round(ev_s, 4),
                "net_roi_bps": round((ev_s / q_s) * 10000.0, 2),
            }
        )

    return {
        "optimal_clip_usd": q_opt,
        "max_expected_profit_per_clip_usd": pi_opt,
        "breakeven_clip_usd": q_breakeven,
        "daily_strategy_capacity_usd": daily_vol_cap,
        "steady_state_capital_capacity_usd": steady_capital_cap,
        "daily_max_net_profit_usd": daily_max_pnl,
        "curve_samples": samples,
    }


# ==============================================================================
# 3. CONTINUOUS-TIME CAPITAL-LOCKUP & CORRELATED-CLUSTER TIER SIMULATOR
# ==============================================================================


@dataclass(frozen=True)
class StrategyArchetypeSpec:
    """Parameterized or empirically calibrated directional strategy family for scale simulation."""

    strategy_id: str
    category: str
    mechanism: str  # "PROBABILITY_EDGE" or "TRADING_EDGE"
    true_win_prob: float
    model_sigma_p: float
    entry_ask_price: float
    win_net_payoff_per_share: float  # 1.0 for settlement; e.g. 0.64 net proceeds for trading exit
    loss_net_payoff_per_share: float  # 0.0 for settlement; e.g. 0.41 net stop proceeds for trading exit
    fee_rate: float
    is_maker_entry: bool
    lockup_days: float
    opportunities_per_day: float
    l1_depth_usd: float
    book_depth_scale_usd: float
    intra_cluster_correlation: float = 0.35
    macro_factor_loading: float = 0.25
    contracts_per_event_cluster: int = 2
    p_uma_dispute: float = 0.002
    p_void_50_50: float = 0.0
    maker_fill_prob: float = 1.0
    maker_adverse_selection_prob_haircut: float = 0.0


def simulate_account_tier_monte_carlo(
    initial_bankroll_usd: float,
    strategies: Sequence[StrategyArchetypeSpec],
    horizon_days: int = 60,
    n_paths: int = 400,
    kelly_multiplier: float = 0.25,
    event_cap_frac: float = DEFAULT_EVENT_CAP_FRAC,
    allow_min_lot_round_up: bool = False,
    ruin_floor_frac: float = 0.60,
    daily_vm_infra_usd: float = DOMINUS_VM_DAILY_USD,
    riskless_daily_yield: float = DOMINUS_RISKLESS_DAILY_YIELD_CONSERVATIVE,
    seed: int = 20261112,
) -> Dict[str, Any]:
    """Simulates multi-strategy portfolio evolution with exact lockup queues, 5-share min lots,
    correlated Gaussian-copula event clusters, L2 depth saturation, and VM infra hurdle.
    """
    rng = random.Random(seed)
    nav0 = float(initial_bankroll_usd)
    ruin_floor_usd = nav0 * _clamp(float(ruin_floor_frac), 0.0, 0.99)

    terminal_navs: List[float] = []
    net_pnls_pre_vm: List[float] = []
    net_pnls_post_vm: List[float] = []
    max_drawdowns_pct: List[float] = []
    daily_returns_all_paths: List[float] = []
    ruin_count = 0

    total_candidates = 0
    executed_trades = 0
    quantization_skips = 0
    lockup_cash_skips = 0
    cluster_cap_skips = 0
    maker_unfilled_skips = 0
    total_dollar_days_locked = 0.0
    total_available_nav_days = 0.0

    # Memoize Kelly & capacity ceiling by (strategy_id, quantized_prob_half_pct) for >1000x MC speed
    _cap_cache: Dict[Tuple[str, int], float] = {}
    _kelly_cache: Dict[Tuple[str, int], KellySizingResult] = {}

    for _ in range(max(1, int(n_paths))):
        free_cash = nav0
        # Active locks: list of (unlock_day_float, committed_usd, realized_proceeds_usd, cluster_key)
        active_locks: List[Tuple[float, float, float, str]] = []
        hwm = nav0
        max_dd = 0.0
        hit_ruin = False
        prev_nav = nav0

        for day in range(int(horizon_days)):
            # 1. Settle unlocked positions up to start of `day`
            still_locked: List[Tuple[float, float, float, str]] = []
            for u_day, comm_usd, proc_usd, c_key in active_locks:
                if u_day <= float(day) + 1e-9:
                    free_cash += proc_usd
                else:
                    still_locked.append((u_day, comm_usd, proc_usd, c_key))
            active_locks = still_locked

            locked_principal = sum(item[1] for item in active_locks)
            cur_nav = free_cash + locked_principal
            total_available_nav_days += max(0.0, cur_nav)
            if cur_nav <= ruin_floor_usd:
                hit_ruin = True

            # Shared daily macro Gaussian factor Z_macro ~ N(0, 1)
            z_macro = _norm_inv_approx(rng.random())

            # Rank strategies by expected velocity (edge / lockup) so scarce cash goes to highest PPDD first
            daily_arrivals: List[Tuple[float, StrategyArchetypeSpec, str, float]] = []
            for st in strategies:
                # Poisson-like arrival count via integer part + Bernoulli fractional arrival
                lam = max(0.0, float(st.opportunities_per_day))
                n_events = int(math.floor(lam)) + (1 if rng.random() < (lam - math.floor(lam)) else 0)
                for ev_idx in range(n_events):
                    z_cluster = _norm_inv_approx(rng.random())
                    cluster_key = f"{st.category}:{day}:{ev_idx}"
                    n_legs = max(1, int(st.contracts_per_event_cluster))
                    for _leg in range(n_legs):
                        t_intra = float(day) + rng.random() * 0.85
                        daily_arrivals.append((t_intra, st, cluster_key, z_cluster))

            daily_arrivals.sort(key=lambda x: x[0])

            for t_now, st, cluster_key, z_cluster in daily_arrivals:
                # Settle any intraday locks that matured before `t_now`
                rem_intraday: List[Tuple[float, float, float, str]] = []
                for u_day, comm_usd, proc_usd, c_key in active_locks:
                    if u_day <= t_now:
                        free_cash += proc_usd
                    else:
                        rem_intraday.append((u_day, comm_usd, proc_usd, c_key))
                active_locks = rem_intraday

                locked_principal = sum(item[1] for item in active_locks)
                cur_nav = free_cash + locked_principal
                if cur_nav <= ruin_floor_usd:
                    hit_ruin = True
                    continue

                total_candidates += 1

                # Noisy model forecast `p_hat` around `st.true_win_prob`
                p_hat = _clamp(
                    st.true_win_prob + st.model_sigma_p * _norm_inv_approx(rng.random()),
                    0.01,
                    0.99,
                )

                # Build general 2- or 3-state scenario per share for exact UPK sizing (memoized to 0.25% p_hat grid)
                p_grid_idx = int(round(p_hat * 400.0))
                p_quant = _clamp(p_grid_idx / 400.0, 0.01, 0.99)
                k_cache_key = (st.strategy_id, p_grid_idx)
                kelly_res = _kelly_cache.get(k_cache_key)
                p_d = _clamp(st.p_uma_dispute, 0.0, 0.99) if st.mechanism == "PROBABILITY_EDGE" else 0.0
                p_v = _clamp(st.p_void_50_50, 0.0, 0.99 - p_d) if st.mechanism == "PROBABILITY_EDGE" else 0.0
                adv_hc = max(0.0, float(st.maker_adverse_selection_prob_haircut)) if st.is_maker_entry else 0.0
                p_quant_net = _clamp(p_quant - adv_hc, 0.005, 0.995)
                if kelly_res is None:
                    entry_fee_0 = compute_polymarket_fee_per_share(
                        st.entry_ask_price, fee_rate=st.fee_rate, is_maker=st.is_maker_entry
                    )
                    c0 = st.entry_ask_price + entry_fee_0
                    pnl_win = st.win_net_payoff_per_share - c0
                    pnl_loss = st.loss_net_payoff_per_share - c0
                    pnl_void = 0.50 - c0
                    pnl_disp = 0.0 - c0
                    p_clean = max(0.0, 1.0 - p_d - p_v)
                    scen = [
                        (pnl_win, p_clean * p_quant_net),
                        (pnl_loss, p_clean * (1.0 - p_quant_net)),
                    ]
                    if p_v > 0.0:
                        scen.append((pnl_void, p_v))
                    if p_d > 0.0:
                        scen.append((pnl_disp, p_d))

                    kelly_res = uncertainty_penalized_kelly_scenarios(
                        pnl_per_share_and_probs=scen,
                        capital_committed_per_share=c0,
                        epistemic_edge_std_per_share=st.model_sigma_p * (st.win_net_payoff_per_share - st.loss_net_payoff_per_share),
                        kelly_multiplier=kelly_multiplier,
                        ambiguity_z=0.75,
                        shrinkage_eta=1.0,
                        max_fraction_cap=event_cap_frac,
                    )
                    _kelly_cache[k_cache_key] = kelly_res

                existing_cluster_usd = sum(item[1] for item in active_locks if item[3] == cluster_key)
                # Map general payoff to equivalent binary LCB payout for capacity/quantization check
                p_lcb = _clamp(p_hat - adv_hc - 0.75 * st.model_sigma_p, 0.0, 1.0)
                p_clean_lcb = max(0.0, 1.0 - p_d - p_v)
                equiv_payout_lcb = (
                    p_clean_lcb * (p_lcb * st.win_net_payoff_per_share + (1.0 - p_lcb) * st.loss_net_payoff_per_share)
                    + p_v * 0.50
                )
                cache_k = (st.strategy_id, int(round(equiv_payout_lcb * 200.0)))
                opt_clip_cached = _cap_cache.get(cache_k)
                if opt_clip_cached is None:
                    opt_clip_cached = compute_strategy_capacity_curve(
                        pi_side_lcb=equiv_payout_lcb,
                        entry_ask_price=st.entry_ask_price,
                        fee_rate=st.fee_rate,
                        is_maker_entry=st.is_maker_entry,
                        p_uma_dispute=0.0,
                        l1_depth_usd=st.l1_depth_usd,
                        book_depth_scale_usd=st.book_depth_scale_usd,
                    )["optimal_clip_usd"]
                    _cap_cache[cache_k] = opt_clip_cached

                q_dec = quantize_and_cap_order(
                    bankroll_usd=cur_nav,
                    free_cash_usd=free_cash,
                    kelly_result=kelly_res,
                    pi_side_lcb=equiv_payout_lcb,
                    entry_ask_price=st.entry_ask_price,
                    fee_rate=st.fee_rate,
                    is_maker_entry=st.is_maker_entry,
                    p_uma_dispute=0.0,  # already folded into equiv_payout_lcb
                    l1_depth_usd=st.l1_depth_usd,
                    book_depth_scale_usd=st.book_depth_scale_usd,
                    event_cap_frac=event_cap_frac,
                    existing_event_exposure_usd=existing_cluster_usd,
                    allow_min_lot_round_up=allow_min_lot_round_up,
                    precomputed_optimal_clip_usd=opt_clip_cached,
                )

                if not q_dec.executable:
                    if "MIN_LOT" in q_dec.reject_reason or "5SH" in q_dec.reject_reason:
                        if "CASH" in q_dec.reject_reason:
                            lockup_cash_skips += 1
                        else:
                            quantization_skips += 1
                    elif "EVENT_CAP" in q_dec.reject_reason:
                        cluster_cap_skips += 1
                    continue

                if q_dec.final_notional_usd > free_cash + 1e-9:
                    lockup_cash_skips += 1
                    continue

                # Passive maker resting queue fill probability (`RT-02`: maker orders don't auto-fill 100%)
                if st.is_maker_entry and float(st.maker_fill_prob) < 1.0:
                    if rng.random() > _clamp(float(st.maker_fill_prob), 0.0, 1.0):
                        maker_unfilled_skips += 1
                        continue

                # Execute simulated order and draw correlated outcome via Gaussian copula!
                free_cash -= q_dec.final_notional_usd
                executed_trades += 1
                eff_hold = max(MIN_LOCKUP_DAYS, float(st.lockup_days))
                total_dollar_days_locked += q_dec.final_notional_usd * eff_hold

                w_macro = _clamp(st.macro_factor_loading, 0.0, 0.85)
                w_clust = _clamp(st.intra_cluster_correlation, 0.0, 0.95 - w_macro)
                w_idio = math.sqrt(max(0.0, 1.0 - w_macro - w_clust))
                z_idio = _norm_inv_approx(rng.random())
                z_lat = math.sqrt(w_macro) * z_macro + math.sqrt(w_clust) * z_cluster + w_idio * z_idio
                u_corr = _norm_cdf(z_lat)
                eff_win_p = _clamp(st.true_win_prob - adv_hc, 0.0, 1.0)

                u_non_clean = rng.random() if (p_d > 0.0 or p_v > 0.0) else 1.0
                if p_d > 0.0 and u_non_clean < p_d:
                    payoff_sh = 0.0
                    eff_hold += 7.0
                elif p_v > 0.0 and u_non_clean < (p_d + p_v):
                    payoff_sh = 0.50
                elif u_corr < eff_win_p:
                    payoff_sh = st.win_net_payoff_per_share
                else:
                    payoff_sh = st.loss_net_payoff_per_share

                proceeds_usd = q_dec.final_shares * payoff_sh
                active_locks.append((t_now + eff_hold, q_dec.final_notional_usd, proceeds_usd, cluster_key))

            # End-of-day mark-to-cost + realized cash check for drawdown & daily return
            eod_nav = free_cash + sum(item[1] for item in active_locks)
            hwm = max(hwm, eod_nav)
            dd = (hwm - eod_nav) / max(1e-6, hwm)
            max_dd = max(max_dd, dd)
            if eod_nav <= ruin_floor_usd:
                hit_ruin = True
            daily_ret = (eod_nav - prev_nav) / max(1e-6, prev_nav)
            daily_returns_all_paths.append(daily_ret)
            prev_nav = eod_nav

        # Liquidate/settle remaining locks at horizon end for terminal accounting
        final_nav = free_cash + sum(item[2] for item in active_locks)
        hwm = max(hwm, final_nav)
        max_dd = max(max_dd, (hwm - final_nav) / max(1e-6, hwm))
        if final_nav <= ruin_floor_usd:
            hit_ruin = True
        if hit_ruin:
            ruin_count += 1

        pnl_pre_vm = final_nav - nav0
        vm_cost_total = float(horizon_days) * float(daily_vm_infra_usd)
        pnl_post_vm = pnl_pre_vm - vm_cost_total

        terminal_navs.append(final_nav)
        net_pnls_pre_vm.append(pnl_pre_vm)
        net_pnls_post_vm.append(pnl_post_vm)
        max_drawdowns_pct.append(max_dd)

    n_p = len(terminal_navs)
    mean_pnl_pre = sum(net_pnls_pre_vm) / n_p
    mean_pnl_post = sum(net_pnls_post_vm) / n_p
    mean_daily_usd_pre = mean_pnl_pre / max(1, horizon_days)
    mean_daily_usd_post = mean_pnl_post / max(1, horizon_days)

    sorted_pnls = sorted(net_pnls_pre_vm)
    tail_n = max(1, int(math.floor(0.05 * n_p)))
    cvar_95_pnl_usd = sum(sorted_pnls[:tail_n]) / tail_n

    # Daily Sharpe & Sortino across pooled path-days
    n_dr = max(1, len(daily_returns_all_paths))
    mu_dr = sum(daily_returns_all_paths) / n_dr
    var_dr = sum((r - mu_dr) ** 2 for r in daily_returns_all_paths) / max(1, n_dr - 1)
    sd_dr = math.sqrt(max(0.0, var_dr))
    downside_sq = sum((min(0.0, r) ** 2) for r in daily_returns_all_paths) / n_dr
    downside_sd = math.sqrt(max(0.0, downside_sq))

    sharpe_ann = (mu_dr / sd_dr) * math.sqrt(365.0) if sd_dr > 1e-12 else 0.0
    sortino_ann = (mu_dr / downside_sd) * math.sqrt(365.0) if downside_sd > 1e-12 else 0.0

    # Benchmark: DOMINUS RISKLESS (`D1`/`BOND1`) soft-capped at `DOMINUS_RISKLESS_CAPACITY_SOFT_CAP_USD`
    eff_riskless_cap = min(nav0, DOMINUS_RISKLESS_CAPACITY_SOFT_CAP_USD)
    riskless_daily_usd_pre = eff_riskless_cap * float(riskless_daily_yield)
    riskless_pnl_pre = riskless_daily_usd_pre * horizon_days
    riskless_pnl_post = riskless_pnl_pre - (horizon_days * float(daily_vm_infra_usd))

    avg_util = min(1.0, total_dollar_days_locked / max(1e-6, total_available_nav_days))
    avg_ppdd = mean_pnl_pre / max(1e-6, total_dollar_days_locked / n_p) if (total_dollar_days_locked / n_p) > 0 else 0.0
    ruin_prob = ruin_count / n_p

    return {
        "initial_bankroll_usd": nav0,
        "horizon_days": horizon_days,
        "n_paths": n_p,
        "allow_min_lot_round_up": allow_min_lot_round_up,
        "kelly_multiplier": kelly_multiplier,
        "vm_hurdle_daily_usd": round(daily_vm_infra_usd, 4),
        "vm_hurdle_bps_per_day": round((daily_vm_infra_usd / max(1e-6, nav0)) * 10000.0, 2),
        "avg_trades_executed_per_path": round(executed_trades / n_p, 2),
        "candidate_rejection_rates": {
            "min_lot_quantization_skip_pct": round(100.0 * quantization_skips / max(1, total_candidates), 2),
            "lockup_cash_starvation_skip_pct": round(100.0 * lockup_cash_skips / max(1, total_candidates), 2),
            "event_cluster_cap_skip_pct": round(100.0 * cluster_cap_skips / max(1, total_candidates), 2),
            "maker_unfilled_skip_pct": round(100.0 * maker_unfilled_skips / max(1, total_candidates), 2),
        },
        "capital_utilization_pct": round(100.0 * avg_util, 2),
        "profit_per_dollar_day_committed": round(avg_ppdd, 6),
        "expected_net_pnl_pre_vm_usd": round(mean_pnl_pre, 4),
        "expected_net_pnl_post_vm_usd": round(mean_pnl_post, 4),
        "expected_daily_net_usd_pre_vm": round(mean_daily_usd_pre, 4),
        "expected_daily_net_usd_post_vm": round(mean_daily_usd_post, 4),
        "clears_vm_infra_hurdle": bool(mean_daily_usd_post > 0.0),
        "beats_riskless_expected_pnl": bool(mean_pnl_pre > riskless_pnl_pre),
        "beats_dominus_riskless_benchmark": bool(
            mean_pnl_pre > riskless_pnl_pre and ruin_prob <= 0.05 and cvar_95_pnl_usd > -0.25 * nav0
        ),
        "zero_ruin_paths": bool(ruin_count == 0),
        "dominus_riskless_benchmark_daily_usd_pre_vm": round(riskless_daily_usd_pre, 4),
        "dominus_riskless_benchmark_pnl_pre_vm_usd": round(riskless_pnl_pre, 4),
        "dominus_riskless_benchmark_pnl_post_vm_usd": round(riskless_pnl_post, 4),
        "ruin_or_floor_breach_prob_pct": round(100.0 * ruin_prob, 2),
        "mean_max_drawdown_pct": round(100.0 * (sum(max_drawdowns_pct) / n_p), 2),
        "p95_max_drawdown_pct": round(
            100.0 * sorted(max_drawdowns_pct)[min(n_p - 1, int(0.95 * n_p))], 2
        ),
        "cvar_95_horizon_pnl_usd": round(cvar_95_pnl_usd, 4),
        "annualized_sharpe": round(sharpe_ann, 3),
        "annualized_sortino": round(sortino_ann, 3),
    }


# ==============================================================================
# 4. MULTI-STRATEGY CORRELATION, SHARED-FACTOR TAIL RISK & OOS COMBINER
# ==============================================================================


def _pearson_corr(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n != len(ys) or n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 1e-15 or vy <= 1e-15:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return _clamp(cov / math.sqrt(vx * vy), -1.0, 1.0)


def compute_unconditional_and_tail_correlations(
    strategy_daily_returns: Dict[str, Sequence[float]],
    tail_quantile: float = 0.20,
) -> Dict[str, Any]:
    """Computes unconditional correlation matrix AND downside tail correlation matrix.

    Conditioning on the worst `tail_quantile` days of the equal-weight aggregate exposes
    hidden shared macro/crypto/time factors where strategies that appear uncorrelated in
    calm periods suffer simultaneous drawdowns.
    """
    names = sorted(strategy_daily_returns.keys())
    if not names:
        return {"strategies": [], "unconditional_corr": {}, "downside_tail_corr": {}, "max_tail_corr_jump": 0.0}

    n_days = min(len(strategy_daily_returns[k]) for k in names)
    if n_days < 3:
        ident = {a: {b: (1.0 if a == b else 0.0) for b in names} for a in names}
        return {"strategies": names, "unconditional_corr": ident, "downside_tail_corr": ident, "max_tail_corr_jump": 0.0}

    agg_series = [
        sum(float(strategy_daily_returns[k][t]) for k in names) / len(names)
        for t in range(n_days)
    ]
    sorted_idx = sorted(range(n_days), key=lambda i: agg_series[i])
    k_tail = max(3, int(math.ceil(_clamp(tail_quantile, 0.05, 0.50) * n_days)))
    tail_indices = sorted_idx[:k_tail]

    uncond: Dict[str, Dict[str, float]] = {a: {} for a in names}
    tail_c: Dict[str, Dict[str, float]] = {a: {} for a in names}
    max_jump = 0.0

    for a in names:
        xa = [float(strategy_daily_returns[a][t]) for t in range(n_days)]
        xa_tail = [xa[t] for t in tail_indices]
        for b in names:
            if a == b:
                uncond[a][b] = 1.0
                tail_c[a][b] = 1.0
                continue
            xb = [float(strategy_daily_returns[b][t]) for t in range(n_days)]
            xb_tail = [xb[t] for t in tail_indices]
            c_all = _pearson_corr(xa, xb)
            c_tl = _pearson_corr(xa_tail, xb_tail)
            uncond[a][b] = round(c_all, 4)
            tail_c[a][b] = round(c_tl, 4)
            max_jump = max(max_jump, c_tl - c_all)

    return {
        "strategies": names,
        "n_days": n_days,
        "n_tail_days": k_tail,
        "unconditional_corr": uncond,
        "downside_tail_corr": tail_c,
        "max_tail_corr_jump": round(max_jump, 4),
    }


def optimize_strategy_weights_qp(
    expected_returns: Sequence[float],
    cov_matrix: Sequence[Sequence[float]],
    epistemic_variances: Optional[Sequence[float]] = None,
    risk_aversion: float = 4.0,
    max_single_weight: float = 0.45,
    total_leverage_cap: float = 1.0,
    n_iters: int = 300,
) -> List[float]:
    """Pure-Python projected gradient solver for Uncertainty-Penalized Multi-Strategy Kelly QP:

        max_{w >= 0, w_i <= max_single_weight, sum(w) <= total_leverage_cap}
            w^T mu - 0.5 * risk_aversion * w^T (Sigma + diag(epistemic_variances)) w
    """
    m = len(expected_returns)
    if m == 0:
        return []
    mu = [float(x) for x in expected_returns]
    ep_var = [max(0.0, float(v)) for v in (epistemic_variances or [0.0] * m)]
    lam = max(1e-4, float(risk_aversion))
    w_max = _clamp(float(max_single_weight), 0.01, float(total_leverage_cap))
    tot_cap = max(0.01, float(total_leverage_cap))

    # Build regularized SPD matrix Q = lam * (Sigma + diag(ep_var) + 1e-6 * I)
    q_mat: List[List[float]] = []
    lip = 0.0
    for i in range(m):
        row: List[float] = []
        row_norm = 0.0
        for j in range(m):
            val = float(cov_matrix[i][j])
            if i == j:
                val = max(0.0, val) + ep_var[i] + 1e-6
            q_ij = lam * val
            row.append(q_ij)
            row_norm += abs(q_ij)
        q_mat.append(row)
        lip = max(lip, row_norm)

    step = 1.0 / max(1e-6, lip)

    def _project_capped_simplex(v: List[float]) -> List[float]:
        clipped = [_clamp(x, 0.0, w_max) for x in v]
        if sum(clipped) <= tot_cap + 1e-12:
            return clipped
        # Bisection on Lagrange multiplier tau: sum_i clamp(v_i - tau, 0, w_max) == tot_cap
        lo_t = min(v) - w_max
        hi_t = max(v)
        for _ in range(50):
            mid_t = 0.5 * (lo_t + hi_t)
            s = sum(_clamp(x - mid_t, 0.0, w_max) for x in v)
            if s > tot_cap:
                lo_t = mid_t
            else:
                hi_t = mid_t
        tau = 0.5 * (lo_t + hi_t)
        return [_clamp(x - tau, 0.0, w_max) for x in v]

    w = _project_capped_simplex([max(0.0, x) for x in mu])
    if sum(max(0.0, x) for x in mu) <= 1e-12:
        return [0.0] * m

    for _ in range(max(20, int(n_iters))):
        # Gradient of objective: mu - Q w
        grad = [mu[i] - sum(q_mat[i][j] * w[j] for j in range(m)) for i in range(m)]
        w_next = _project_capped_simplex([w[i] + step * grad[i] for i in range(m)])
        diff = max(abs(w_next[i] - w[i]) for i in range(m))
        w = w_next
        if diff < 1e-10:
            break
    return w


def compute_return_series_metrics(
    daily_returns: Sequence[float],
    bankroll_usd: float = DOMINUS_TIER2_CASH_USD,
    daily_vm_usd: float = DOMINUS_VM_DAILY_USD,
) -> Dict[str, float]:
    """Computes Sharpe, Sortino, `CVaR_95`, Max Drawdown, Calmar, and Net `$/day` on a return series."""
    rets = [float(r) for r in daily_returns]
    n = len(rets)
    if n == 0:
        return {
            "n_days": 0,
            "total_return_pct": 0.0,
            "net_pnl_usd_pre_vm": 0.0,
            "net_pnl_usd_post_vm": 0.0,
            "net_usd_per_day_pre_vm": 0.0,
            "net_usd_per_day_post_vm": 0.0,
            "annualized_sharpe": 0.0,
            "annualized_sortino": 0.0,
            "max_drawdown_pct": 0.0,
            "calmar_ratio": 0.0,
            "cvar_95_daily_pct": 0.0,
        }

    equity = float(bankroll_usd)
    hwm = equity
    max_dd = 0.0
    for r in rets:
        equity *= max(0.0, 1.0 + r)
        hwm = max(hwm, equity)
        if hwm > 0.0:
            max_dd = max(max_dd, (hwm - equity) / hwm)

    pnl_pre = equity - float(bankroll_usd)
    pnl_post = pnl_pre - n * float(daily_vm_usd)

    mu = sum(rets) / n
    var = sum((r - mu) ** 2 for r in rets) / max(1, n - 1)
    sd = math.sqrt(max(0.0, var))
    down_sq = sum((min(0.0, r) ** 2) for r in rets) / n
    down_sd = math.sqrt(max(0.0, down_sq))

    sharpe = (mu / sd) * math.sqrt(365.0) if sd > 1e-12 else 0.0
    sortino = (mu / down_sd) * math.sqrt(365.0) if down_sd > 1e-12 else 0.0
    # Use arithmetic annualized return (consistent with annualized Sharpe) so short 5-37d OOS windows
    # are never distorted by (equity/nav)^(365/n) exponential extrapolation.
    ann_ret = mu * 365.0
    calmar = _clamp((ann_ret / max_dd), -999.0, 999.0) if max_dd > 1e-6 else (99.0 if ann_ret > 0 else 0.0)

    sorted_r = sorted(rets)
    k_tail = max(1, int(math.ceil(0.05 * n)))
    cvar_95 = sum(sorted_r[:k_tail]) / k_tail

    return {
        "n_days": n,
        "total_return_pct": round(((equity / float(bankroll_usd)) - 1.0) * 100.0, 4),
        "net_pnl_usd_pre_vm": round(pnl_pre, 4),
        "net_pnl_usd_post_vm": round(pnl_post, 4),
        "net_usd_per_day_pre_vm": round(pnl_pre / n, 4),
        "net_usd_per_day_post_vm": round(pnl_post / n, 4),
        "annualized_sharpe": round(sharpe, 4),
        "annualized_sortino": round(sortino, 4),
        "max_drawdown_pct": round(max_dd * 100.0, 4),
        "calmar_ratio": round(calmar, 4),
        "cvar_95_daily_pct": round(cvar_95 * 100.0, 4),
    }


def evaluate_oos_multi_strategy_combination(
    train_daily_returns: Dict[str, Sequence[float]],
    oos_daily_returns: Dict[str, Sequence[float]],
    bankroll_usd: float = DOMINUS_TIER2_CASH_USD,
    risk_aversion: float = 4.0,
    max_single_weight: float = 0.45,
) -> Dict[str, Any]:
    """Tests empirically (fitting strictly on `train_daily_returns`, evaluating on `oos_daily_returns`)
    whether combining candidate directional strategies genuinely improves OOS Sharpe, Sortino,
    `CVaR_95`, Calmar/MaxDD, and net `$/day`, OR suffers hidden tail correlation drag.
    """
    names = sorted(set(train_daily_returns.keys()) & set(oos_daily_returns.keys()))
    if not names:
        raise ValueError("train_daily_returns and oos_daily_returns must share >= 1 strategy key.")

    n_tr = min(len(train_daily_returns[k]) for k in names)
    n_oos = min(len(oos_daily_returns[k]) for k in names)
    if n_tr < 3 or n_oos < 2:
        raise ValueError(f"Insufficient train ({n_tr}) or OOS ({n_oos}) days.")

    # 1. Fit parameters strictly on Train (zero OOS peeking!)
    mu_tr: List[float] = []
    ep_var_tr: List[float] = []
    tr_centered: List[List[float]] = []

    for k in names:
        s_tr = [float(train_daily_returns[k][t]) for t in range(n_tr)]
        m_k = sum(s_tr) / n_tr
        v_k = sum((x - m_k) ** 2 for x in s_tr) / max(1, n_tr - 1)
        # Shrink mean by standard error LCB (0.5 * SE)
        se_sq = v_k / n_tr
        mu_tr.append(m_k - 0.5 * math.sqrt(se_sq))
        ep_var_tr.append(se_sq)
        tr_centered.append([x - m_k for x in s_tr])

    # Blend unconditional train covariance with train downside-tail covariance (50/50) to penalize hidden tail corr!
    agg_tr = [sum(float(train_daily_returns[k][t]) for k in names) / len(names) for t in range(n_tr)]
    tail_idx = sorted(range(n_tr), key=lambda i: agg_tr[i])[: max(2, int(math.ceil(0.25 * n_tr)))]

    cov_blend: List[List[float]] = []
    for i in range(len(names)):
        row: List[float] = []
        xi_tl = [float(train_daily_returns[names[i]][t]) for t in tail_idx]
        mi_tl = sum(xi_tl) / len(xi_tl)
        for j in range(len(names)):
            cov_all = sum(tr_centered[i][t] * tr_centered[j][t] for t in range(n_tr)) / max(1, n_tr - 1)
            xj_tl = [float(train_daily_returns[names[j]][t]) for t in tail_idx]
            mj_tl = sum(xj_tl) / len(xj_tl)
            cov_tl = sum((xi_tl[u] - mi_tl) * (xj_tl[u] - mj_tl) for u in range(len(tail_idx))) / max(1, len(tail_idx) - 1)
            row.append(0.5 * cov_all + 0.5 * cov_tl)
        cov_blend.append(row)

    w_upk_raw = optimize_strategy_weights_qp(
        expected_returns=mu_tr,
        cov_matrix=cov_blend,
        epistemic_variances=ep_var_tr,
        risk_aversion=risk_aversion,
        max_single_weight=max_single_weight,
        total_leverage_cap=1.0,
    )
    # Normalize active weights onto 1.0 capital comparison basis when positive strategies exist
    sum_upk = sum(w_upk_raw)
    w_upk_norm = [w / sum_upk for w in w_upk_raw] if sum_upk > 1e-9 else [0.0] * len(names)

    # Positive-train-expectancy Equal Weight & Inverse Volatility baselines
    pos_mask = [1.0 if m > 0.0 else 0.0 for m in mu_tr]
    n_pos = sum(pos_mask)
    w_eq = [p / n_pos for p in pos_mask] if n_pos > 0 else [1.0 / len(names)] * len(names)

    inv_vols = [
        (1.0 / math.sqrt(max(1e-10, cov_blend[i][i]))) if mu_tr[i] > 0.0 else 0.0
        for i in range(len(names))
    ]
    sum_iv = sum(inv_vols)
    w_iv = [v / sum_iv for v in inv_vols] if sum_iv > 0.0 else list(w_eq)

    # 2. Evaluate strictly on Out-of-Sample (`oos_daily_returns`)
    standalone_oos: Dict[str, Dict[str, float]] = {}
    for k in names:
        standalone_oos[k] = compute_return_series_metrics(
            [float(oos_daily_returns[k][t]) for t in range(n_oos)], bankroll_usd=bankroll_usd
        )

    def _combine_oos(weights: Sequence[float]) -> List[float]:
        return [
            sum(weights[i] * float(oos_daily_returns[names[i]][t]) for i in range(len(names)))
            for t in range(n_oos)
        ]

    metrics_eq = compute_return_series_metrics(_combine_oos(w_eq), bankroll_usd=bankroll_usd)
    metrics_iv = compute_return_series_metrics(_combine_oos(w_iv), bankroll_usd=bankroll_usd)
    metrics_upk = compute_return_series_metrics(_combine_oos(w_upk_norm), bankroll_usd=bankroll_usd)

    corr_oos = compute_unconditional_and_tail_correlations(
        {k: [float(oos_daily_returns[k][t]) for t in range(n_oos)] for k in names}
    )

    # Best train-selected single strategy evaluated OOS (honest single-champion benchmark!)
    best_train_idx = max(range(len(names)), key=lambda i: mu_tr[i] / math.sqrt(max(1e-10, cov_blend[i][i])))
    best_train_single_name = names[best_train_idx]
    best_single_oos = standalone_oos[best_train_single_name]

    improves_sharpe = metrics_upk["annualized_sharpe"] > best_single_oos["annualized_sharpe"]
    improves_cvar_or_dd = (
        metrics_upk["cvar_95_daily_pct"] >= best_single_oos["cvar_95_daily_pct"]
        and metrics_upk["max_drawdown_pct"] <= best_single_oos["max_drawdown_pct"] + 1e-6
    )

    return {
        "strategies": names,
        "train_days": n_tr,
        "oos_days": n_oos,
        "weights_upk_normalized": {names[i]: round(w_upk_norm[i], 4) for i in range(len(names))},
        "weights_upk_unlevered": {names[i]: round(w_upk_raw[i], 4) for i in range(len(names))},
        "weights_equal_positive_train": {names[i]: round(w_eq[i], 4) for i in range(len(names))},
        "weights_inverse_vol_train": {names[i]: round(w_iv[i], 4) for i in range(len(names))},
        "best_train_single_strategy": best_train_single_name,
        "standalone_oos_metrics": standalone_oos,
        "combined_oos_metrics": {
            "uncertainty_penalized_kelly_qp": metrics_upk,
            "equal_weight_positive_train": metrics_eq,
            "inverse_vol_positive_train": metrics_iv,
        },
        "oos_correlation_diagnostics": corr_oos,
        "genuinely_improves_oos_sharpe_over_train_champion": bool(improves_sharpe),
        "reduces_oos_tail_and_drawdown_vs_train_champion": bool(improves_cvar_or_dd),
        "hidden_tail_correlation_warning": bool(corr_oos["max_tail_corr_jump"] > 0.25),
    }

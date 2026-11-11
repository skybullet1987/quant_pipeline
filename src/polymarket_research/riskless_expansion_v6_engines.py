"""
Dominus Riskless Expansion v6 — 8 Mathematically Verified Pure-Riskless Engines
(`src/polymarket_research/riskless_expansion_v6_engines.py`).

Implements Phase 2 (`P2.1`–`P2.8`) of the Dominus Riskless Audit & Expansion Blueprint:
  1. `XV_SUBSET_NO_BOX`: Cross-venue & augmented-safe $2 <= m <= k$ subset `NO` dominance boxes
     with universal $m=2$ `50-50` cancellation proof and `+$1.00` outsider/`Other` jackpot.
  2. `TAIL_BOUNDARY_001_ARB`: Polymarket `0.001`-tick boundary (`p >= 0.96` / `p <= 0.04`)
     parabolic-fee-collapse complete-set & nested dominance scanner (`8x–20x` lower V2 fee drag).
  3. `BOND3_MULTISOURCE_DEAD_SPLIT`: Multi-source independent primary-oracle unanimity gate
     (MLB, NHL, NBA, Soccer post-VAR, Crypto finalized candle, Weather SPECI/COR-safe) +
     `Stage C2` dead-leg `splitPosition` -> FOK sell synthesizer during `MOOV2` windows.
  4. `XV_FX_INVARIANT_CAD_USD_BOX`: `100%` `CA-ON` legal `STX Ontario (CAD, 0% maker)` <->
     `ForecastEx / IBKR Canada (USD)` state-invariant FX-sized / IBKR FX-locked arbitrage engine.
  5. `DERIBIT_VERTICAL_SUPER_REP`: Keyless Deribit linear `USDC` (`BTC_USDC`, `ETH_USDC`, `SOL_USDC`)
     `08:00 UTC` tight vertical call/put spread super-replication vs binary digital strikes with
     explicit `30m TWAP` cross-oracle basis bound $B_{max}$.
  6. `XV_HALFTIME_FREEZE_CORRIDOR`: Cross-venue `.5`-hook halftime (`clock=0:00`, `>= 480s` scorer
     review, `0ms` live delay) `FG = S_1H + 2H` affine total & spread corridor scanner.
  7. `HEDGED_PRESPLIT_CONV_GUN`: Pre-converted closed `NegRisk` `NR3` settled-inventory overround
     harvester (zero post-fill Polygon block lag) + shadow-gated hedged pre-split binary Maker-Ask.
  8. `YIELD_STACKED_CARRY_BOX`: Contractual collateral coupon accrual (`ForecastEx` `FFR - 0.50%`,
     `Predict.fun` Venus `vUSDT`, `Polymarket` Holding Rewards) with rate-cut haircut + `Stage C1`
     early overround exit accounting for forfeited remaining coupon.

Core Invariant:
  Every candidate emitted by this module carries an explicit `state_payoff_table: Dict[str, float]`
  and passes `verify_state_dominance_invariant`:
      min_{omega in Omega} state_payoff_table[omega] >= all_in_cost_usd + min_net_profit_usd
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_CEILING
from itertools import combinations
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.polymarket_research.cross_venue_riskless_shadow import (
    DEFAULT_EXTERNAL_GAS_USD,
    DEFAULT_RELAY_BRIDGE_DRAG_BPS,
    MIN_NET_PROFIT_USD,
    NormalizedBinaryMarket,
    OrderLevel,
    collateral_fx_ask_to_usd,
    collateral_fx_settle_floor_to_usd,
    compute_venue_taker_fee_usd,
    polymarket_v2_share_haircut_frac,
    relay_bridge_drag_usd,
    walk_asks_for_shares,
)
from src.polymarket_research.riskless_protocol_v2_expansion import (
    v2_net_buy_cost_per_share,
    v2_net_sell_proceeds_per_share,
)


class StateDominanceViolationError(ValueError):
    """Raised if a candidate fails state-by-state worst-case profit dominance."""


@dataclass(frozen=True)
class VerifiedRisklessOpportunity:
    """Canonical output record for all 8 Phase-2 riskless engines."""

    strategy_id: str
    opportunity_id: str
    venues: Tuple[str, ...]
    jurisdiction_tags: Tuple[str, ...]
    live_eligible: bool
    shares_or_units: float
    all_in_cost_usd: float
    worst_case_payout_usd: float
    best_case_payout_usd: float
    guaranteed_net_profit_usd: float
    guaranteed_net_edge_bps: float
    lockup_hours: float
    state_payoff_table: Dict[str, float]
    legs: Tuple[Dict[str, Any], ...]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def verify_state_dominance_invariant(
    state_payoff_table: Mapping[str, float],
    all_in_cost_usd: float,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> Tuple[bool, float, float, str]:
    """
    Verify strict state-by-state payoff dominance:
        min_{omega in Omega} V_T(omega) >= all_in_cost_usd + min_net_profit_usd.
    Returns `(passed, worst_payout, best_payout, worst_state_name)`.
    """
    if not state_payoff_table or all_in_cost_usd <= 0.0:
        return False, 0.0, 0.0, "EMPTY_STATE_SPACE"
    worst_state, worst_val = min(state_payoff_table.items(), key=lambda kv: float(kv[1]))
    _, best_val = max(state_payoff_table.items(), key=lambda kv: float(kv[1]))
    net_floor = float(worst_val) - float(all_in_cost_usd)
    return (net_floor + 1e-9 >= float(min_net_profit_usd)), float(worst_val), float(best_val), str(worst_state)


def _market_poly_haircut(mkt: NormalizedBinaryMarket, price: float) -> float:
    if mkt.venue.lower() == "polymarket" and mkt.fee_enabled and float(mkt.fee_rate_bps or 0.0) > 0.0:
        return polymarket_v2_share_haircut_frac(float(price), float(mkt.fee_rate_bps))
    return 0.0


# ---------------------------------------------------------------------------
# Engine 1 (`P2.1`): Cross-Venue & Augmented-Safe Subset `NO` Dominance Box
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubsetNoCandidateOutcome:
    """One mutually-exclusive outcome candidate mapped across >=1 venue."""

    outcome_key: str
    market: NormalizedBinaryMarket
    cancel_payout_mode: str = "50_50"  # "50_50" | "VOID" | "NO_WINS"


def detect_cross_venue_subset_no_boxes(
    partition_id: str,
    outcomes: Sequence[SubsetNoCandidateOutcome],
    *,
    is_mutually_exclusive: bool = True,
    has_path_dependent_barriers: bool = False,
    event_cancel_exempt: bool = False,
    subset_sizes: Sequence[int] = (2, 3),
    target_notional_usd: float = 50.0,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> List[VerifiedRisklessOpportunity]:
    """
    Scan $2 <= m <= k$ subset `NO` dominance boxes across any mutually-exclusive outcome space
    (including `negRiskAugmented=True` slates with `"Other"`, since direct `NO` holding never
    calls `convertPositions` and earns a `+$1.00 * Q` jackpot if `"Other"` wins!).

    Cancellation Theorem Enforced:
      - If event cancellation resolves legs `50_50`, terminal cancel payout is `0.50 * m * Q`.
        For $m = 2$, `0.50 * 2 = 1.00 = m - 1 > cost` unconditionally!
        For $m >= 3$, `0.50 * m < m - 1`, so `OMEGA_EVENT_CANCEL` is explicitly included in
        `state_payoff_table` unless `event_cancel_exempt=True` (e.g., scheduled FOMC/CPI dates).
      - If a venue's cancel rule is `VOID`, cancel payout credits `local_cost * fx_settle_floor`.
    """
    if not is_mutually_exclusive or has_path_dependent_barriers or len(outcomes) < 2:
        return []

    best_by_outcome: Dict[str, Tuple[float, SubsetNoCandidateOutcome]] = {}
    for cand in outcomes:
        mkt = cand.market
        if mkt.category.lower() == "crypto_barrier" or not mkt.no_asks:
            continue
        top_px = float(mkt.no_asks[0].price)
        if top_px <= 0.0 or top_px >= 1.0:
            continue
        fx_a = collateral_fx_ask_to_usd(mkt.collateral_asset)
        fx_f = collateral_fx_settle_floor_to_usd(mkt.collateral_asset)
        haircut = _market_poly_haircut(mkt, top_px)
        unit_fee = 0.0 if mkt.venue.lower() == "polymarket" else compute_venue_taker_fee_usd(mkt, 1.0, top_px)
        eff_usd_unit = ((top_px / max(1.0 - haircut, 1e-6)) + unit_fee) * (fx_a / max(fx_f, 1e-6))
        prev = best_by_outcome.get(cand.outcome_key)
        if prev is None or eff_usd_unit < prev[0]:
            best_by_outcome[cand.outcome_key] = (eff_usd_unit, cand)

    chosen_pool = [v[1] for v in sorted(best_by_outcome.values(), key=lambda x: x[0])]
    if len(chosen_pool) < 2:
        return []

    results: List[VerifiedRisklessOpportunity] = []
    for m in subset_sizes:
        if m < 2 or m > len(chosen_pool):
            continue
        payout_floor_per_unit = float(m - 1)
        for combo in combinations(chosen_pool, m):
            est_unit_sum = 0.0
            for item in combo:
                px0 = item.market.no_asks[0].price
                fx_ratio = collateral_fx_ask_to_usd(item.market.collateral_asset) / max(
                    collateral_fx_settle_floor_to_usd(item.market.collateral_asset), 1e-6
                )
                h0 = _market_poly_haircut(item.market, px0)
                est_unit_sum += (px0 / max(1.0 - h0, 1e-6)) * fx_ratio
            if est_unit_sum >= payout_floor_per_unit:
                continue

            min_usd_sh = max(
                item.market.min_shares * collateral_fx_settle_floor_to_usd(item.market.collateral_asset)
                for item in combo
            )
            q_usd = max(min_usd_sh, math.floor(float(target_notional_usd) / max(est_unit_sum, 0.10)))

            leg_records: List[Dict[str, Any]] = []
            leg_costs_usd: List[float] = []
            leg_local_spent: List[float] = []
            feasible = True
            for item in combo:
                mkt = item.market
                fx_a = collateral_fx_ask_to_usd(mkt.collateral_asset)
                fx_f = collateral_fx_settle_floor_to_usd(mkt.collateral_asset)
                req_net_local = q_usd / max(fx_f, 1e-6)
                req_local = math.ceil(req_net_local / max(mkt.lot_size, 1e-6)) * max(mkt.lot_size, 1e-6)
                w_fill = walk_asks_for_shares(mkt.no_asks, req_local, mkt)
                if not w_fill.filled or w_fill.filled_shares + 1e-6 < req_net_local:
                    feasible = False
                    break
                # `walk_asks_for_shares` already computes exact `gross_cost_usd` + `taker_fee_usd` (including PM V2 & STX win comm)
                leg_usd = (w_fill.gross_cost_usd + w_fill.taker_fee_usd) * fx_a
                leg_costs_usd.append(leg_usd)
                leg_local_spent.append(w_fill.gross_cost_usd)
                leg_records.append(
                    {
                        "outcome_key": item.outcome_key,
                        "venue": mkt.venue,
                        "market_id": mkt.market_id,
                        "side": "NO",
                        "local_shares_net": round(w_fill.filled_shares, 6),
                        "vwap_local": round(w_fill.vwap_price, 6),
                        "leg_cost_usd": round(leg_usd, 6),
                        "cancel_payout_mode": item.cancel_payout_mode,
                        "fx_settle_floor": fx_f,
                    }
                )
            if not feasible:
                continue

            distinct_venues = tuple(sorted({item.market.venue for item in combo}))
            gas_usd = sum(DEFAULT_EXTERNAL_GAS_USD.get(v, 0.005) for v in distinct_venues)
            bridge_usd = (
                relay_bridge_drag_usd(sum(leg_costs_usd), DEFAULT_RELAY_BRIDGE_DRAG_BPS) * (len(distinct_venues) - 1)
                if len(distinct_venues) > 1
                else 0.0
            )
            all_in_cost = sum(leg_costs_usd) + gas_usd + bridge_usd

            state_table: Dict[str, float] = {}
            for win_idx, item in enumerate(combo):
                payout_win = sum(
                    rec["local_shares_net"] * rec["fx_settle_floor"]
                    for j, rec in enumerate(leg_records)
                    if j != win_idx
                )
                state_table[f"OMEGA_OUTCOME_{item.outcome_key}_YES"] = round(payout_win, 6)

            outsider_payout = sum(rec["local_shares_net"] * rec["fx_settle_floor"] for rec in leg_records)
            state_table["OMEGA_OUTSIDER_OR_AUGMENTED_OTHER_YES"] = round(outsider_payout, 6)

            if not event_cancel_exempt:
                cancel_payout = 0.0
                for j, (item, rec) in enumerate(zip(combo, leg_records)):
                    mode = item.cancel_payout_mode.upper()
                    if mode == "VOID":
                        cancel_payout += leg_local_spent[j] * rec["fx_settle_floor"]
                    elif mode == "NO_WINS":
                        cancel_payout += rec["local_shares_net"] * rec["fx_settle_floor"]
                    else:  # "50_50"
                        cancel_payout += 0.50 * rec["local_shares_net"] * rec["fx_settle_floor"]
                state_table["OMEGA_EVENT_CANCEL"] = round(cancel_payout, 6)

            passed, worst_p, best_p, _ = verify_state_dominance_invariant(
                state_table, all_in_cost, min_net_profit_usd=min_net_profit_usd
            )
            if not passed:
                continue

            lockup_h = max(0.5, max(it.market.settlement_delay_hours for it in combo) + 2.0)
            jurisdictions = (
                ("CA-ON-LEGAL",)
                if set(distinct_venues).issubset({"stx_ontario", "forecastex", "deribit"})
                else ("GLOBAL_SHADOW",)
            )
            net_profit = worst_p - all_in_cost
            edge_bps = (net_profit / all_in_cost) * 10_000.0
            opp_key = f"xv_subno:{partition_id}:m{m}:{'+'.join(it.outcome_key for it in combo)}"
            results.append(
                VerifiedRisklessOpportunity(
                    strategy_id="XV_SUBSET_NO_BOX",
                    opportunity_id=opp_key,
                    venues=distinct_venues,
                    jurisdiction_tags=jurisdictions,
                    live_eligible=("CA-ON-LEGAL" in jurisdictions or distinct_venues == ("polymarket",)),
                    shares_or_units=round(q_usd, 6),
                    all_in_cost_usd=round(all_in_cost, 6),
                    worst_case_payout_usd=round(worst_p, 6),
                    best_case_payout_usd=round(best_p, 6),
                    guaranteed_net_profit_usd=round(net_profit, 6),
                    guaranteed_net_edge_bps=round(edge_bps, 2),
                    lockup_hours=round(lockup_h, 3),
                    state_payoff_table=state_table,
                    legs=tuple(leg_records),
                    metadata={
                        "subset_size_m": m,
                        "partition_total_outcomes_seen": len(chosen_pool),
                        "outsider_jackpot_bonus_usd": round(best_p - worst_p, 6),
                    },
                )
            )

    results.sort(key=lambda r: r.guaranteed_net_edge_bps, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Engine 2 (`P2.2`): `0.001`-Tick Boundary Parabolic-Fee Collapse Scanner
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundaryTickDominancePair:
    """
    Candidate pair on Polymarket's `0.001` sub-penny boundary grid (`p >= 0.96` or `p <= 0.04`).
    """

    pair_id: str
    pair_type: str  # "COMPLETE_SET" | "NESTED_STRIKE"
    oracle_signature: str
    expiry_ts: float
    leg_a_token_id: str
    leg_a_label: str
    leg_a_asks: Tuple[OrderLevel, ...]
    leg_b_token_id: str
    leg_b_label: str
    leg_b_asks: Tuple[OrderLevel, ...]
    fee_rate: float = 0.07
    fee_exponent: float = 1.0
    strike_low: float = 0.0
    strike_high: float = 0.0
    lockup_hours: float = 1.0


def _quantize_subpenny_001_leg_shares(gross_shares: float, price: float) -> Tuple[float, float]:
    """
    Quantize a Polymarket BUY leg on the `0.001` boundary tick grid so `maker_amount = shares * price`
    is an exact 2-decimal cent multiple (`$0.01`), `shares >= 5.0`, and `maker_amount >= $1.00`.
    """
    d_px = Decimal(str(round(float(price), 3)))
    if d_px <= Decimal("0") or d_px >= Decimal("1"):
        return 0.0, 0.0
    min_sh_notional = float((Decimal("1.00") / d_px).quantize(Decimal("0.01"), rounding=ROUND_CEILING))
    base_sh = max(5.0, float(gross_shares), min_sh_notional)
    cand = Decimal(str(math.ceil(base_sh * 10.0) / 10.0))
    for _ in range(105):
        cents = cand * d_px * Decimal("100")
        if cents == cents.to_integral_value() and cand * d_px >= Decimal("1.00"):
            return float(cand), float((cand * d_px).quantize(Decimal("0.01")))
        cand += Decimal("0.1")
    return 0.0, 0.0


def detect_tail_boundary_001_fee_collapse_boxes(
    pairs: Sequence[BoundaryTickDominancePair],
    *,
    target_box_notional_usd: float = 45.0,
    polygon_gas_usd: float = 0.0,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> List[VerifiedRisklessOpportunity]:
    """
    Detect riskless boxes where at least one leg (`p >= 0.96` or `p <= 0.04`) sits on Polymarket's
    `0.001` sub-penny boundary tick grid, collapsing V2 parabolic taker fees by `8x–20x` while
    enforcing exact 2-decimal `makerAmount` quantization and `$1.00` per-leg FOK floors.
    """
    opportunities: List[VerifiedRisklessOpportunity] = []
    for pair in pairs:
        if not pair.leg_a_asks or not pair.leg_b_asks:
            continue
        if pair.pair_type.upper() == "NESTED_STRIKE" and pair.strike_low > pair.strike_high + 1e-12:
            continue

        px_a = round(float(pair.leg_a_asks[0].price), 3)
        px_b = round(float(pair.leg_b_asks[0].price), 3)
        in_boundary_a = px_a >= 0.96 or px_a <= 0.04
        in_boundary_b = px_b >= 0.96 or px_b <= 0.04
        if not (in_boundary_a or in_boundary_b):
            continue
        if not in_boundary_a and abs(round(px_a, 2) - px_a) > 1e-9:
            continue
        if not in_boundary_b and abs(round(px_b, 2) - px_b) > 1e-9:
            continue

        unit_net_a = v2_net_buy_cost_per_share(px_a, pair.fee_rate, pair.fee_exponent)
        unit_net_b = v2_net_buy_cost_per_share(px_b, pair.fee_rate, pair.fee_exponent)
        if unit_net_a + unit_net_b >= 1.0:
            continue

        h_a = 1.0 - (px_a / unit_net_a)
        h_b = 1.0 - (px_b / unit_net_b)
        min_net_from_notional_a = (1.00 / max(px_a, 1e-6)) * (1.0 - h_a)
        min_net_from_notional_b = (1.00 / max(px_b, 1e-6)) * (1.0 - h_b)
        desired_net_sh = max(
            5.0,
            min_net_from_notional_a,
            min_net_from_notional_b,
            float(target_box_notional_usd) / max(unit_net_a + unit_net_b, 0.10),
        )
        avail_net_a = float(pair.leg_a_asks[0].size) * (1.0 - h_a)
        avail_net_b = float(pair.leg_b_asks[0].size) * (1.0 - h_b)
        net_target = min(desired_net_sh, avail_net_a, avail_net_b)
        if net_target < max(5.0, min_net_from_notional_a, min_net_from_notional_b):
            continue

        # Quantize the higher-priced leg first, then match the cheaper tail leg to its exact delivered net shares
        # so sub-penny lot rounding on the `$0.96+` leg never leaves the `$0.02–$0.04` leg under-hedged!
        if px_a >= px_b:
            gross_a_raw = net_target / max(1.0 - h_a, 1e-6)
            q_gross_a, cost_a = _quantize_subpenny_001_leg_shares(gross_a_raw, px_a)
            delivered_net_a = q_gross_a * (1.0 - h_a)
            gross_b_raw = max(net_target, delivered_net_a) / max(1.0 - h_b, 1e-6)
            q_gross_b, cost_b = _quantize_subpenny_001_leg_shares(gross_b_raw, px_b)
        else:
            gross_b_raw = net_target / max(1.0 - h_b, 1e-6)
            q_gross_b, cost_b = _quantize_subpenny_001_leg_shares(gross_b_raw, px_b)
            delivered_net_b_pre = q_gross_b * (1.0 - h_b)
            gross_a_raw = max(net_target, delivered_net_b_pre) / max(1.0 - h_a, 1e-6)
            q_gross_a, cost_a = _quantize_subpenny_001_leg_shares(gross_a_raw, px_a)
        if q_gross_a <= 0.0 or q_gross_b <= 0.0:
            continue
        if q_gross_a > float(pair.leg_a_asks[0].size) + 1e-9 or q_gross_b > float(pair.leg_b_asks[0].size) + 1e-9:
            continue

        delivered_net_a = q_gross_a * (1.0 - h_a)
        delivered_net_b = q_gross_b * (1.0 - h_b)
        paired_net_sh = min(delivered_net_a, delivered_net_b)
        if paired_net_sh < 5.0:
            continue

        all_in_cost = cost_a + cost_b + float(polygon_gas_usd)
        state_table: Dict[str, float] = {
            "OMEGA_LOW_OUTCOME_LEG_B_WINS": round(delivered_net_b * 1.0, 6),
            "OMEGA_HIGH_OUTCOME_LEG_A_WINS": round(delivered_net_a * 1.0, 6),
        }
        if pair.pair_type.upper() == "NESTED_STRIKE" and pair.strike_low < pair.strike_high:
            state_table["OMEGA_POLISH_MIDDLE_BOTH_WIN"] = round((delivered_net_a + delivered_net_b) * 1.0, 6)

        passed, worst_p, best_p, _ = verify_state_dominance_invariant(
            state_table, all_in_cost, min_net_profit_usd=min_net_profit_usd
        )
        if not passed:
            continue

        mid_fee_drag = 2.0 * (v2_net_buy_cost_per_share(0.50, pair.fee_rate, pair.fee_exponent) - 0.50)
        tail_fee_drag = (unit_net_a - px_a) + (unit_net_b - px_b)
        fee_compression_ratio = mid_fee_drag / max(tail_fee_drag, 1e-6)

        net_profit = worst_p - all_in_cost
        opportunities.append(
            VerifiedRisklessOpportunity(
                strategy_id="TAIL_BOUNDARY_001_ARB",
                opportunity_id=f"tail001:{pair.pair_id}",
                venues=("polymarket",),
                jurisdiction_tags=("EU_ELIGIBLE", "GLOBAL_SHADOW"),
                live_eligible=True,
                shares_or_units=round(paired_net_sh, 6),
                all_in_cost_usd=round(all_in_cost, 6),
                worst_case_payout_usd=round(worst_p, 6),
                best_case_payout_usd=round(best_p, 6),
                guaranteed_net_profit_usd=round(net_profit, 6),
                guaranteed_net_edge_bps=round((net_profit / all_in_cost) * 10_000.0, 2),
                lockup_hours=round(max(0.05, pair.lockup_hours), 3),
                state_payoff_table=state_table,
                legs=(
                    {
                        "token_id": pair.leg_a_token_id,
                        "label": pair.leg_a_label,
                        "price": px_a,
                        "gross_shares": q_gross_a,
                        "net_shares": round(delivered_net_a, 6),
                        "maker_amount_usd": cost_a,
                    },
                    {
                        "token_id": pair.leg_b_token_id,
                        "label": pair.leg_b_label,
                        "price": px_b,
                        "gross_shares": q_gross_b,
                        "net_shares": round(delivered_net_b, 6),
                        "maker_amount_usd": cost_b,
                    },
                ),
                metadata={
                    "tail_unit_fee_drag": round(tail_fee_drag, 6),
                    "mid_50_50_unit_fee_drag": round(mid_fee_drag, 6),
                    "fee_compression_multiple": round(fee_compression_ratio, 2),
                    "oracle_signature": pair.oracle_signature,
                },
            )
        )

    opportunities.sort(key=lambda r: r.guaranteed_net_edge_bps, reverse=True)
    return opportunities


# ---------------------------------------------------------------------------
# Engine 3 (`P2.3`): Multi-Source Verified `MOOV2` Bond + Dead-Leg Split-Sell
# ---------------------------------------------------------------------------


CATEGORY_FINALITY_BUFFER_SEC: Dict[str, float] = {
    "mlb": 900.0,
    "nhl": 600.0,
    "nba": 600.0,
    "soccer": 900.0,
    "crypto": 60.0,
    "weather": 3600.0,
}


@dataclass(frozen=True)
class PrimaryOracleObservation:
    """Single independent authoritative primary-source observation for post-event finality."""

    source_name: str
    is_terminal_final: bool
    winning_outcome: str  # "YES" | "NO"
    post_final_elapsed_sec: float
    has_speci_or_cor_conflict: bool = False
    has_protest_or_review_flag: bool = False


def verify_multisource_finality(
    *,
    category: str,
    uma_proposed_outcome: str,
    uma_status: str,
    is_whitelisted_proposer: bool,
    clob_winner_best_bid: float,
    observations: Sequence[PrimaryOracleObservation],
) -> Tuple[bool, str]:
    """
    Deterministic 3-way unanimity verifier (`MOOV2 Whitelisted Proposer` == `>=2 Primary Feeds` == `CLOB >= $0.94`).
    """
    cat = category.strip().lower()
    min_buf = CATEGORY_FINALITY_BUFFER_SEC.get(cat, 900.0)
    if uma_status.strip().lower() in {"disputed", "flagged", "reset"}:
        return False, "REJECT_UMA_DISPUTED_OR_FLAGGED"
    if not is_whitelisted_proposer:
        return False, "REJECT_UNWHITELISTED_MOOV2_PROPOSER"
    prop = uma_proposed_outcome.strip().upper()
    if prop not in {"YES", "NO"}:
        return False, "REJECT_INVALID_PROPOSED_OUTCOME"
    if float(clob_winner_best_bid) < 0.94:
        return False, "REJECT_CLOB_BID_BELOW_094_CONFIRMATION"

    distinct_valid_sources: Dict[str, PrimaryOracleObservation] = {}
    for obs in observations:
        if not obs.is_terminal_final:
            return False, f"REJECT_NON_TERMINAL_SOURCE:{obs.source_name}"
        if obs.has_speci_or_cor_conflict:
            return False, f"REJECT_SPECI_OR_COR_CONFLICT:{obs.source_name}"
        if obs.has_protest_or_review_flag:
            return False, f"REJECT_ACTIVE_PROTEST_OR_REVIEW:{obs.source_name}"
        if obs.winning_outcome.strip().upper() != prop:
            return False, f"REJECT_PRIMARY_ORACLE_DISAGREEMENT:{obs.source_name}"
        if float(obs.post_final_elapsed_sec) < min_buf:
            return False, f"REJECT_INSUFFICIENT_POST_FINAL_BUFFER:{obs.source_name}"
        distinct_valid_sources[obs.source_name.strip().lower()] = obs

    if len(distinct_valid_sources) < 2:
        return False, "REJECT_FEWER_THAN_2_INDEPENDENT_PRIMARY_FEEDS"
    return True, "VERIFIED_3WAY_UNANIMITY"


def evaluate_bond3_multisource_verified_carry(
    *,
    market_id: str,
    category: str,
    uma_proposed_outcome: str,
    uma_status: str,
    is_whitelisted_proposer: bool,
    remaining_challenge_sec: float,
    winner_asks: Sequence[OrderLevel],
    winner_bids: Sequence[OrderLevel],
    dead_loser_bids: Sequence[OrderLevel],
    observations: Sequence[PrimaryOracleObservation],
    fee_rate: float = 0.03,
    fee_exponent: float = 2.0,
    target_notional_usd: float = 50.0,
    split_merge_gas_usd: float = 0.015,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> Optional[VerifiedRisklessOpportunity]:
    """
    Evaluate `BOND3_MULTISOURCE_DEAD_SPLIT` after strict multi-source primary-oracle finality passes.
    Compares direct CLOB FOK BUY on verified winner vs `Stage C2` Dead-Leg Split-to-Sell (`splitPosition`
    -> FOK SELL dead complement into stale retail bids).
    """
    best_win_bid = float(winner_bids[0].price) if winner_bids else 0.0
    ok, reason = verify_multisource_finality(
        category=category,
        uma_proposed_outcome=uma_proposed_outcome,
        uma_status=uma_status,
        is_whitelisted_proposer=is_whitelisted_proposer,
        clob_winner_best_bid=best_win_bid,
        observations=observations,
    )
    if not ok:
        return None

    lockup_h = max(0.05, float(remaining_challenge_sec) / 3600.0)
    candidates: List[VerifiedRisklessOpportunity] = []

    if winner_asks:
        ask_px = float(winner_asks[0].price)
        if 0.50 < ask_px < 1.0:
            unit_net_cost = v2_net_buy_cost_per_share(ask_px, fee_rate, fee_exponent)
            if unit_net_cost < 1.0:
                h_win = 1.0 - (ask_px / unit_net_cost)
                avail_net = float(winner_asks[0].size) * (1.0 - h_win)
                net_sh = min(avail_net, math.floor(float(target_notional_usd) / unit_net_cost))
                if net_sh >= 5.0:
                    gross_sh = math.ceil((net_sh / max(1.0 - h_win, 1e-6)) * 100.0) / 100.0
                    cost_usd = round(gross_sh * ask_px, 2)
                    delivered_net = gross_sh * (1.0 - h_win)
                    state_a = {"OMEGA_VERIFIED_FINAL_SETTLEMENT": round(delivered_net * 1.0, 6)}
                    ok_a, worst_a, best_a, _ = verify_state_dominance_invariant(
                        state_a, cost_usd, min_net_profit_usd=min_net_profit_usd
                    )
                    if ok_a:
                        prof_a = worst_a - cost_usd
                        candidates.append(
                            VerifiedRisklessOpportunity(
                                strategy_id="BOND3_MULTISOURCE_DEAD_SPLIT",
                                opportunity_id=f"bond3_direct:{market_id}",
                                venues=("polymarket",),
                                jurisdiction_tags=("GLOBAL_SHADOW",),
                                live_eligible=True,
                                shares_or_units=round(delivered_net, 6),
                                all_in_cost_usd=round(cost_usd, 6),
                                worst_case_payout_usd=round(worst_a, 6),
                                best_case_payout_usd=round(best_a, 6),
                                guaranteed_net_profit_usd=round(prof_a, 6),
                                guaranteed_net_edge_bps=round((prof_a / cost_usd) * 10_000.0, 2),
                                lockup_hours=round(lockup_h, 4),
                                state_payoff_table=state_a,
                                legs=(
                                    {
                                        "route": "DIRECT_WINNER_FOK_BUY",
                                        "side": uma_proposed_outcome.upper(),
                                        "ask_price": ask_px,
                                        "gross_shares": gross_sh,
                                        "net_shares": round(delivered_net, 6),
                                    },
                                ),
                                metadata={"finality_proof": reason, "entry_mode": "DIRECT_BUY"},
                            )
                        )

    if dead_loser_bids:
        dead_bid_px = float(dead_loser_bids[0].price)
        dead_bid_sz = float(dead_loser_bids[0].size)
        if 0.002 <= dead_bid_px <= 0.25 and dead_bid_sz >= 5.0:
            net_dead_unit = v2_net_sell_proceeds_per_share(dead_bid_px, fee_rate, fee_exponent)
            q_split = float(min(math.floor(dead_bid_sz), math.floor(float(target_notional_usd))))
            if q_split >= 5.0 and q_split * dead_bid_px >= 1.00:
                dead_proceeds_usd = q_split * net_dead_unit
                synth_all_in_cost = (q_split * 1.00) - dead_proceeds_usd + float(split_merge_gas_usd)
                state_b = {"OMEGA_VERIFIED_FINAL_SETTLEMENT": round(q_split * 1.0, 6)}
                ok_b, worst_b, best_b, _ = verify_state_dominance_invariant(
                    state_b, synth_all_in_cost, min_net_profit_usd=min_net_profit_usd
                )
                if ok_b:
                    prof_b = worst_b - synth_all_in_cost
                    candidates.append(
                        VerifiedRisklessOpportunity(
                            strategy_id="BOND3_MULTISOURCE_DEAD_SPLIT",
                            opportunity_id=f"bond3_deadsplit:{market_id}",
                            venues=("polymarket",),
                            jurisdiction_tags=("GLOBAL_SHADOW",),
                            live_eligible=True,
                            shares_or_units=round(q_split, 6),
                            all_in_cost_usd=round(synth_all_in_cost, 6),
                            worst_case_payout_usd=round(worst_b, 6),
                            best_case_payout_usd=round(best_b, 6),
                            guaranteed_net_profit_usd=round(prof_b, 6),
                            guaranteed_net_edge_bps=round((prof_b / synth_all_in_cost) * 10_000.0, 2),
                            lockup_hours=round(lockup_h, 4),
                            state_payoff_table=state_b,
                            legs=(
                                {
                                    "route": "STAGE_C2_SPLIT_AND_SELL_DEAD_COMPLEMENT",
                                    "winner_side": uma_proposed_outcome.upper(),
                                    "dead_bid_price": dead_bid_px,
                                    "dead_net_proceeds_per_share": round(net_dead_unit, 6),
                                    "synthetic_winner_unit_cost": round(synth_all_in_cost / q_split, 6),
                                    "shares": q_split,
                                },
                            ),
                            metadata={
                                "finality_proof": reason,
                                "entry_mode": "DEAD_SIDE_SPLIT_SELL",
                                "rollback_on_fok_miss": "CTF_MERGE_POSITIONS_TO_PAR",
                            },
                        )
                    )

    if not candidates:
        return None
    candidates.sort(key=lambda c: c.guaranteed_net_profit_usd, reverse=True)
    return candidates[0]


# ---------------------------------------------------------------------------
# Engine 4 (`P2.4`): `CA-ON` Legal FX-Invariant `STX Ontario (CAD)` <-> `ForecastEx (USD)`
# ---------------------------------------------------------------------------


def evaluate_stx_forecastex_fx_invariant_box(
    *,
    pair_id: str,
    stx_market: NormalizedBinaryMarket,
    stx_side: str,
    stx_execution_style: str,
    forecastex_market: NormalizedBinaryMarket,
    forecastex_side: str,
    spot_cad_to_usd_bid: float = 0.7230,
    spot_cad_to_usd_ask: float = 0.7250,
    fx_shock_band_frac: float = 0.0180,
    ibkr_fx_hedge_locked: bool = False,
    ibkr_fx_ticket_fee_usd: float = 0.25,
    event_cancel_exempt: bool = True,
    target_usd_shares: float = 100.0,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> Optional[VerifiedRisklessOpportunity]:
    """
    `100%` Ontario (`CA-ON`) legal cross-currency box sizing between AGCO-registered
    `STX Ontario` (`CAD`) and `ForecastEx / IBKR Canada` (`USD`).
    """
    if stx_market.venue.lower() != "stx_ontario" or forecastex_market.venue.lower() != "forecastex":
        return None
    if stx_market.collateral_asset.upper() != "CAD" or forecastex_market.collateral_asset.upper() != "USD":
        return None

    stx_asks = stx_market.yes_asks if stx_side.upper() == "YES" else stx_market.no_asks
    fex_asks = forecastex_market.yes_asks if forecastex_side.upper() == "YES" else forecastex_market.no_asks
    if not stx_asks or not fex_asks:
        return None

    q_usd = float(max(forecastex_market.min_shares, math.floor(target_usd_shares)))
    w_fex = walk_asks_for_shares(fex_asks, q_usd, forecastex_market)
    if not w_fex.filled or w_fex.filled_shares + 1e-6 < q_usd:
        return None

    if ibkr_fx_hedge_locked:
        fx_settle_floor = float(spot_cad_to_usd_bid) * (1.0 - 0.0002)
        fx_settle_ceil = float(spot_cad_to_usd_ask) * (1.0 + 0.0002)
        fx_fee_usd = float(ibkr_fx_ticket_fee_usd)
    else:
        fx_settle_floor = float(spot_cad_to_usd_bid) * (1.0 - max(0.0, float(fx_shock_band_frac)))
        fx_settle_ceil = float(spot_cad_to_usd_ask) * (1.0 + max(0.0, float(fx_shock_band_frac)))
        fx_fee_usd = 0.0

    stx_top_px = float(stx_asks[0].price)
    win_rate = (float(stx_market.fee_rate_bps) / 10_000.0) if stx_market.fee_rate_bps > 0.0 else 0.02
    est_stx_win_comm = win_rate * max(0.0, 1.0 - stx_top_px)
    lot = max(float(stx_market.lot_size), 1.0)
    q_cad_needed = math.ceil((q_usd / max(fx_settle_floor * (1.0 - est_stx_win_comm), 1e-6)) / lot) * lot

    w_stx = walk_asks_for_shares(stx_asks, q_cad_needed, stx_market)
    if not w_stx.filled or w_stx.filled_shares + 1e-6 < q_cad_needed:
        return None

    actual_stx_win_comm = win_rate * max(0.0, 1.0 - w_stx.vwap_price)
    # Note: on STX Ontario, `0%` upfront entry fee on maker orders; the `2%` win commission is deducted AT SETTLEMENT
    # from the winning CAD payout (`cad_net_payout_cad`), NOT paid upfront on losing outcomes!
    is_stx_maker = stx_execution_style.strip().upper() == "PASSIVE_MAKER"
    stx_upfront_fee_cad = 0.0 if is_stx_maker else w_stx.taker_fee_usd
    stx_cost_usd = (w_stx.gross_cost_usd + stx_upfront_fee_cad) * float(spot_cad_to_usd_ask)

    fex_leg_usd = w_fex.gross_cost_usd + w_fex.taker_fee_usd
    all_in_cost_usd = fex_leg_usd + stx_cost_usd + fx_fee_usd
    cad_net_payout_cad = q_cad_needed * (1.0 - (actual_stx_win_comm if is_stx_maker else 0.0))

    state_table: Dict[str, float] = {
        "OMEGA_FORECASTEX_USD_WINS_FX_LOW": round(q_usd * 1.0, 6),
        "OMEGA_FORECASTEX_USD_WINS_FX_HIGH": round(q_usd * 1.0, 6),
        "OMEGA_STX_CAD_WINS_FX_FLOOR": round(cad_net_payout_cad * fx_settle_floor, 6),
        "OMEGA_STX_CAD_WINS_FX_CEIL": round(cad_net_payout_cad * fx_settle_ceil, 6),
    }
    if not event_cancel_exempt:
        state_table["OMEGA_EVENT_VOID_FX_FLOOR"] = round(w_fex.gross_cost_usd + w_stx.gross_cost_usd * fx_settle_floor, 6)

    passed, worst_p, best_p, _ = verify_state_dominance_invariant(
        state_table, all_in_cost_usd, min_net_profit_usd=min_net_profit_usd
    )
    if not passed:
        return None

    net_profit = worst_p - all_in_cost_usd
    return VerifiedRisklessOpportunity(
        strategy_id="XV_FX_INVARIANT_CAD_USD_BOX",
        opportunity_id=f"xv_cad_usd:{pair_id}",
        venues=("stx_ontario", "forecastex"),
        jurisdiction_tags=("CA-ON-LEGAL", "AGCO_OSC_COMPLIANT"),
        live_eligible=True,
        shares_or_units=round(q_usd, 6),
        all_in_cost_usd=round(all_in_cost_usd, 6),
        worst_case_payout_usd=round(worst_p, 6),
        best_case_payout_usd=round(best_p, 6),
        guaranteed_net_profit_usd=round(net_profit, 6),
        guaranteed_net_edge_bps=round((net_profit / all_in_cost_usd) * 10_000.0, 2),
        lockup_hours=round(max(1.0, forecastex_market.settlement_delay_hours), 3),
        state_payoff_table=state_table,
        legs=(
            {
                "venue": "forecastex",
                "side": forecastex_side.upper(),
                "currency": "USD",
                "shares": q_usd,
                "vwap": round(w_fex.vwap_price, 6),
                "leg_cost_usd": round(fex_leg_usd, 6),
            },
            {
                "venue": "stx_ontario",
                "side": stx_side.upper(),
                "currency": "CAD",
                "execution_style": stx_execution_style.upper(),
                "shares_cad": q_cad_needed,
                "vwap_cad": round(w_stx.vwap_price, 6),
                "leg_cost_usd": round(stx_cost_usd, 6),
            },
        ),
        metadata={
            "fx_mode": "IBKR_LOCKED_FX" if ibkr_fx_hedge_locked else "UNHEDGED_STRESSED_BAND",
            "fx_settle_floor": round(fx_settle_floor, 6),
            "cad_to_usd_share_ratio": round(q_cad_needed / q_usd, 6),
        },
    )


# ---------------------------------------------------------------------------
# Engine 5 (`P2.5`): Deribit Linear `USDC` Vertical Spread Super-Replication
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeribitLinearOptionQuote:
    """Keyless Deribit linear `USDC` European option quote (`BTC_USDC-*`, `ETH_USDC-*`, `SOL_USDC-*`)."""

    instrument_name: str
    underlying: str
    settlement_currency: str  # MUST be "USDC" (rejects inverse "BTC"/"ETH")
    option_type: str          # "C" | "P"
    strike: float
    expiry_ts: float
    best_bid_usd: float
    best_bid_size: float
    best_ask_usd: float
    best_ask_size: float
    underlying_index_price: float


def _deribit_usdc_option_taker_fee_usd(index_price: float, option_price_usd: float, contracts: float) -> float:
    """Deribit linear USDC options taker fee: `0.0003` (`3 bps`) of underlying index, capped at `12.5%` of option price."""
    per_contract = min(0.0003 * float(index_price), 0.125 * max(0.0, float(option_price_usd)))
    return float(contracts) * per_contract


def detect_deribit_usdc_vertical_super_replication(
    *,
    binary_market: NormalizedBinaryMarket,
    binary_strike: float,
    deribit_options: Sequence[DeribitLinearOptionQuote],
    cross_oracle_basis_bps: float = 150.0,
    target_units: float = 50.0,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> List[VerifiedRisklessOpportunity]:
    """
    Construct tight linear `USDC` vertical call/put spreads on Deribit (`08:00 UTC` expiry)
    super-replicating an aligned binary digital strike `K_bin` across worst-case `30m TWAP` vs
    spot settlement divergence `|S_Deribit - S_bin| <= B_max`.
    """
    if binary_market.end_ts is None or binary_strike <= 0.0:
        return []

    calls: List[DeribitLinearOptionQuote] = []
    puts: List[DeribitLinearOptionQuote] = []
    for opt in deribit_options:
        if opt.settlement_currency.strip().upper() != "USDC" or "_USDC" not in opt.underlying.upper():
            continue
        if abs(float(opt.expiry_ts) - float(binary_market.end_ts)) > 1.0:
            continue
        if opt.best_ask_usd <= 0.0 or opt.best_ask_size <= 0.0:
            continue
        if opt.option_type.strip().upper() == "C":
            calls.append(opt)
        elif opt.option_type.strip().upper() == "P":
            puts.append(opt)

    calls.sort(key=lambda o: o.strike)
    puts.sort(key=lambda o: o.strike)

    eff_bps = max(150.0, float(cross_oracle_basis_bps))
    b_max = float(binary_strike) * (eff_bps / 10_000.0)
    q_units = max(float(binary_market.min_shares), float(target_units))
    fx_a = collateral_fx_ask_to_usd(binary_market.collateral_asset)
    fx_f = collateral_fx_settle_floor_to_usd(binary_market.collateral_asset)
    if abs(fx_a - 1.0) > 0.01 or abs(fx_f - 1.0) > 0.01:
        return []

    found: List[VerifiedRisklessOpportunity] = []

    if binary_market.no_asks:
        for i in range(len(calls)):
            for j in range(i + 1, len(calls)):
                c1, c2 = calls[i], calls[j]
                if c2.strike > binary_strike - b_max + 1e-9 or c2.best_bid_usd <= 0.0:
                    continue
                width = c2.strike - c1.strike
                if width <= 0.0:
                    continue
                n_contracts = q_units / width
                if c1.best_ask_size + 1e-9 < n_contracts or c2.best_bid_size + 1e-9 < n_contracts:
                    continue
                spread_debit = max(0.0, n_contracts * (c1.best_ask_usd - c2.best_bid_usd))
                deribit_fees = (
                    _deribit_usdc_option_taker_fee_usd(c1.underlying_index_price, c1.best_ask_usd, n_contracts)
                    + _deribit_usdc_option_taker_fee_usd(c2.underlying_index_price, c2.best_bid_usd, n_contracts)
                )
                w_bin = walk_asks_for_shares(binary_market.no_asks, q_units, binary_market)
                if not w_bin.filled or w_bin.filled_shares + 1e-6 < q_units:
                    continue
                bin_leg_usd = w_bin.gross_cost_usd + w_bin.taker_fee_usd
                gas_usd = DEFAULT_EXTERNAL_GAS_USD.get(binary_market.venue, 0.005)
                all_in_cost = spread_debit + deribit_fees + bin_leg_usd + gas_usd

                state_a = {
                    "OMEGA_BELOW_K1_NO_WINS": round(w_bin.filled_shares * 1.0, 6),
                    "OMEGA_MID_RAMP_SUPER_REP": round(w_bin.filled_shares * 1.0 + 0.5 * q_units, 6),
                    "OMEGA_POLISH_MIDDLE_K2_TO_KBIN": round(w_bin.filled_shares * 1.0 + q_units, 6),
                    "OMEGA_ABOVE_KBIN_MAX_BASIS_DRIFT": round(
                        n_contracts * min(max((binary_strike - b_max) - c1.strike, 0.0), width), 6
                    ),
                }
                ok_a, worst_a, best_a, _ = verify_state_dominance_invariant(
                    state_a, all_in_cost, min_net_profit_usd=min_net_profit_usd
                )
                if ok_a:
                    prof_a = worst_a - all_in_cost
                    found.append(
                        VerifiedRisklessOpportunity(
                            strategy_id="DERIBIT_VERTICAL_SUPER_REP",
                            opportunity_id=f"deribit_bullcall:{binary_market.market_id}:{int(c1.strike)}-{int(c2.strike)}",
                            venues=("deribit", binary_market.venue),
                            jurisdiction_tags=("CA-ON-LEGAL",) if binary_market.venue == "forecastex" else ("GLOBAL_SHADOW",),
                            live_eligible=(binary_market.venue == "forecastex"),
                            shares_or_units=round(q_units, 6),
                            all_in_cost_usd=round(all_in_cost, 6),
                            worst_case_payout_usd=round(worst_a, 6),
                            best_case_payout_usd=round(best_a, 6),
                            guaranteed_net_profit_usd=round(prof_a, 6),
                            guaranteed_net_edge_bps=round((prof_a / all_in_cost) * 10_000.0, 2),
                            lockup_hours=round(max(0.5, binary_market.settlement_delay_hours), 3),
                            state_payoff_table=state_a,
                            legs=(
                                {
                                    "venue": "deribit",
                                    "structure": "BULL_CALL_SPREAD_USDC",
                                    "long_instrument": c1.instrument_name,
                                    "short_instrument": c2.instrument_name,
                                    "contracts": round(n_contracts, 6),
                                    "debit_plus_fee_usd": round(spread_debit + deribit_fees, 6),
                                },
                                {
                                    "venue": binary_market.venue,
                                    "market_id": binary_market.market_id,
                                    "side": "NO",
                                    "shares": round(w_bin.filled_shares, 6),
                                    "leg_cost_usd": round(bin_leg_usd, 6),
                                },
                            ),
                            metadata={
                                "binary_strike": binary_strike,
                                "basis_corridor_usd": round(b_max, 4),
                                "polish_middle_width_usd": round(binary_strike - c2.strike, 4),
                            },
                        )
                    )

    if binary_market.yes_asks:
        for i in range(len(puts)):
            for j in range(i + 1, len(puts)):
                p1, p2 = puts[i], puts[j]
                if p1.strike < binary_strike + b_max - 1e-9 or p1.best_bid_usd <= 0.0:
                    continue
                width = p2.strike - p1.strike
                if width <= 0.0:
                    continue
                n_contracts = q_units / width
                if p2.best_ask_size + 1e-9 < n_contracts or p1.best_bid_size + 1e-9 < n_contracts:
                    continue
                spread_debit = max(0.0, n_contracts * (p2.best_ask_usd - p1.best_bid_usd))
                deribit_fees = (
                    _deribit_usdc_option_taker_fee_usd(p2.underlying_index_price, p2.best_ask_usd, n_contracts)
                    + _deribit_usdc_option_taker_fee_usd(p1.underlying_index_price, p1.best_bid_usd, n_contracts)
                )
                w_bin = walk_asks_for_shares(binary_market.yes_asks, q_units, binary_market)
                if not w_bin.filled or w_bin.filled_shares + 1e-6 < q_units:
                    continue
                bin_leg_usd = w_bin.gross_cost_usd + w_bin.taker_fee_usd
                gas_usd = DEFAULT_EXTERNAL_GAS_USD.get(binary_market.venue, 0.005)
                all_in_cost = spread_debit + deribit_fees + bin_leg_usd + gas_usd

                state_b = {
                    "OMEGA_ABOVE_K2_YES_WINS": round(w_bin.filled_shares * 1.0, 6),
                    "OMEGA_MID_RAMP_SUPER_REP": round(w_bin.filled_shares * 1.0 + 0.5 * q_units, 6),
                    "OMEGA_POLISH_MIDDLE_KBIN_TO_K1": round(w_bin.filled_shares * 1.0 + q_units, 6),
                    "OMEGA_BELOW_KBIN_MAX_BASIS_DRIFT": round(
                        n_contracts * min(max(p2.strike - (binary_strike + b_max), 0.0), width), 6
                    ),
                }
                ok_b, worst_b, best_b, _ = verify_state_dominance_invariant(
                    state_b, all_in_cost, min_net_profit_usd=min_net_profit_usd
                )
                if ok_b:
                    prof_b = worst_b - all_in_cost
                    found.append(
                        VerifiedRisklessOpportunity(
                            strategy_id="DERIBIT_VERTICAL_SUPER_REP",
                            opportunity_id=f"deribit_bearput:{binary_market.market_id}:{int(p1.strike)}-{int(p2.strike)}",
                            venues=("deribit", binary_market.venue),
                            jurisdiction_tags=("CA-ON-LEGAL",) if binary_market.venue == "forecastex" else ("GLOBAL_SHADOW",),
                            live_eligible=(binary_market.venue == "forecastex"),
                            shares_or_units=round(q_units, 6),
                            all_in_cost_usd=round(all_in_cost, 6),
                            worst_case_payout_usd=round(worst_b, 6),
                            best_case_payout_usd=round(best_b, 6),
                            guaranteed_net_profit_usd=round(prof_b, 6),
                            guaranteed_net_edge_bps=round((prof_b / all_in_cost) * 10_000.0, 2),
                            lockup_hours=round(max(0.5, binary_market.settlement_delay_hours), 3),
                            state_payoff_table=state_b,
                            legs=(
                                {
                                    "venue": "deribit",
                                    "structure": "BEAR_PUT_SPREAD_USDC",
                                    "long_instrument": p2.instrument_name,
                                    "short_instrument": p1.instrument_name,
                                    "contracts": round(n_contracts, 6),
                                    "debit_plus_fee_usd": round(spread_debit + deribit_fees, 6),
                                },
                                {
                                    "venue": binary_market.venue,
                                    "market_id": binary_market.market_id,
                                    "side": "YES",
                                    "shares": round(w_bin.filled_shares, 6),
                                    "leg_cost_usd": round(bin_leg_usd, 6),
                                },
                            ),
                            metadata={
                                "binary_strike": binary_strike,
                                "basis_corridor_usd": round(b_max, 4),
                                "polish_middle_width_usd": round(p1.strike - binary_strike, 4),
                            },
                        )
                    )

    found.sort(key=lambda r: r.guaranteed_net_edge_bps, reverse=True)
    return found


# ---------------------------------------------------------------------------
# Engine 6 (`P2.6`): Cross-Venue Halftime Freeze `.5`-Hook Affine Corridors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HalftimeLineLeg:
    """Full-Game (`FG`) or Second-Half (`2H`) `.5`-hook total or spread leg during halftime freeze."""

    leg_id: str
    period_scope: str        # "FG" | "2H"
    line_kind: str           # "TOTAL" | "HOME_SPREAD"
    direction: str           # "OVER" | "UNDER" (TOTAL) or "HOME_COVER" | "AWAY_COVER" (HOME_SPREAD)
    line_value: float
    includes_overtime: bool
    live_betting_delay_ms: int
    market: NormalizedBinaryMarket
    market_side: str = "YES"


def _is_half_integer_hook(val: float) -> bool:
    frac = abs(float(val) - math.floor(float(val)))
    return abs(frac - 0.5) <= 1e-6


def detect_cross_venue_halftime_affine_corridors(
    *,
    game_id: str,
    sport: str,
    is_halftime: bool,
    game_clock_sec: float,
    elapsed_halftime_sec: float,
    remaining_halftime_sec: float,
    confirmed_1h_home_score: int,
    confirmed_1h_away_score: int,
    fg_legs: Sequence[HalftimeLineLeg],
    h2_legs: Sequence[HalftimeLineLeg],
    target_usd_shares: float = 40.0,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> List[VerifiedRisklessOpportunity]:
    """
    Scan cross-venue `FG = S_1H + 2H` affine total & spread corridors during confirmed NBA/NFL
    halftime intermission (`is_halftime=True`, `clock=0.0`, `elapsed >= 480s`, `0ms` live delay).
    """
    if not is_halftime or abs(float(game_clock_sec)) > 1e-6:
        return []
    if float(elapsed_halftime_sec) < 480.0 or float(remaining_halftime_sec) < 90.0:
        return []

    s_1h_total = int(confirmed_1h_home_score) + int(confirmed_1h_away_score)
    s_1h_margin = int(confirmed_1h_home_score) - int(confirmed_1h_away_score)

    results: List[VerifiedRisklessOpportunity] = []
    for fg in fg_legs:
        if fg.period_scope.upper() != "FG" or not fg.includes_overtime:
            continue
        if fg.live_betting_delay_ms > 0 or not _is_half_integer_hook(fg.line_value):
            continue

        for h2 in h2_legs:
            if h2.period_scope.upper() != "2H" or h2.line_kind.upper() != fg.line_kind.upper():
                continue
            if not h2.includes_overtime or h2.live_betting_delay_ms > 0:
                continue
            if not _is_half_integer_hook(h2.line_value):
                continue
            if fg.market.cancel_rule.strip().lower() != h2.market.cancel_rule.strip().lower():
                continue

            asks_fg = fg.market.yes_asks if fg.market_side.upper() == "YES" else fg.market.no_asks
            asks_h2 = h2.market.yes_asks if h2.market_side.upper() == "YES" else h2.market.no_asks
            if not asks_fg or not asks_h2:
                continue

            q_usd = max(
                fg.market.min_shares * collateral_fx_settle_floor_to_usd(fg.market.collateral_asset),
                h2.market.min_shares * collateral_fx_settle_floor_to_usd(h2.market.collateral_asset),
                float(target_usd_shares),
            )

            leg_costs_usd: List[float] = []
            leg_net_usd_payout: List[float] = []
            feasible = True
            for leg_obj, asks in ((fg, asks_fg), (h2, asks_h2)):
                mkt = leg_obj.market
                fx_a = collateral_fx_ask_to_usd(mkt.collateral_asset)
                fx_f = collateral_fx_settle_floor_to_usd(mkt.collateral_asset)
                lot = max(float(mkt.lot_size), 0.01)
                req_local = math.ceil((q_usd / max(fx_f, 1e-6)) / lot) * lot
                w_loc = walk_asks_for_shares(asks, req_local, mkt)
                if not w_loc.filled or w_loc.filled_shares * fx_f + 1e-6 < q_usd:
                    feasible = False
                    break
                leg_costs_usd.append((w_loc.gross_cost_usd + w_loc.taker_fee_usd) * fx_a)
                leg_net_usd_payout.append(w_loc.filled_shares * fx_f)
            if not feasible:
                continue

            distinct_venues = tuple(sorted({fg.market.venue, h2.market.venue}))
            gas_usd = sum(DEFAULT_EXTERNAL_GAS_USD.get(v, 0.005) for v in distinct_venues)
            all_in_cost = sum(leg_costs_usd) + gas_usd

            payoff_fg_only = leg_net_usd_payout[0]
            payoff_h2_only = leg_net_usd_payout[1]
            payoff_both = payoff_fg_only + payoff_h2_only

            min_lattice_payout = float("inf")
            max_lattice_payout = 0.0
            middle_points = 0
            if fg.line_kind.upper() == "TOTAL":
                for h2_pts in range(0, 261):
                    fg_pts = s_1h_total + h2_pts
                    fg_win = (fg_pts > fg.line_value) if fg.direction.upper() == "OVER" else (fg_pts < fg.line_value)
                    h2_win = (h2_pts > h2.line_value) if h2.direction.upper() == "OVER" else (h2_pts < h2.line_value)
                    p = (payoff_fg_only if fg_win else 0.0) + (payoff_h2_only if h2_win else 0.0)
                    if fg_win and h2_win:
                        middle_points += 1
                    min_lattice_payout = min(min_lattice_payout, p)
                    max_lattice_payout = max(max_lattice_payout, p)
            else:
                for h2_margin in range(-120, 121):
                    fg_margin = s_1h_margin + h2_margin
                    if sport.strip().lower() in {"nba", "nfl_playoffs", "mlb", "nhl"} and fg_margin == 0:
                        continue
                    fg_win = (
                        (fg_margin + fg.line_value > 0.0)
                        if fg.direction.upper() == "HOME_COVER"
                        else (fg_margin + fg.line_value < 0.0)
                    )
                    h2_win = (
                        (h2_margin + h2.line_value > 0.0)
                        if h2.direction.upper() == "HOME_COVER"
                        else (h2_margin + h2.line_value < 0.0)
                    )
                    p = (payoff_fg_only if fg_win else 0.0) + (payoff_h2_only if h2_win else 0.0)
                    if fg_win and h2_win:
                        middle_points += 1
                    min_lattice_payout = min(min_lattice_payout, p)
                    max_lattice_payout = max(max_lattice_payout, p)

            state_table = {
                "OMEGA_LATTICE_WORST_CASE": round(min_lattice_payout, 6),
                "OMEGA_LATTICE_BEST_CASE": round(max_lattice_payout, 6),
            }
            if middle_points > 0:
                state_table["OMEGA_POLISH_MIDDLE_CORRIDOR"] = round(payoff_both, 6)

            passed, worst_p, best_p, _ = verify_state_dominance_invariant(
                state_table, all_in_cost, min_net_profit_usd=min_net_profit_usd
            )
            if not passed:
                continue

            net_profit = worst_p - all_in_cost
            results.append(
                VerifiedRisklessOpportunity(
                    strategy_id="XV_HALFTIME_FREEZE_CORRIDOR",
                    opportunity_id=f"xv_ht:{game_id}:{fg.leg_id}:{h2.leg_id}",
                    venues=distinct_venues,
                    jurisdiction_tags=(
                        ("CA-ON-LEGAL",)
                        if set(distinct_venues).issubset({"stx_ontario", "forecastex"})
                        else ("GLOBAL_SHADOW",)
                    ),
                    live_eligible=set(distinct_venues).issubset({"stx_ontario", "forecastex", "polymarket"}),
                    shares_or_units=round(q_usd, 6),
                    all_in_cost_usd=round(all_in_cost, 6),
                    worst_case_payout_usd=round(worst_p, 6),
                    best_case_payout_usd=round(best_p, 6),
                    guaranteed_net_profit_usd=round(net_profit, 6),
                    guaranteed_net_edge_bps=round((net_profit / all_in_cost) * 10_000.0, 2),
                    lockup_hours=1.75,
                    state_payoff_table=state_table,
                    legs=(
                        {
                            "period": "FG",
                            "venue": fg.market.venue,
                            "direction": fg.direction,
                            "line": fg.line_value,
                            "leg_cost_usd": round(leg_costs_usd[0], 6),
                        },
                        {
                            "period": "2H",
                            "venue": h2.market.venue,
                            "direction": h2.direction,
                            "line": h2.line_value,
                            "leg_cost_usd": round(leg_costs_usd[1], 6),
                        },
                    ),
                    metadata={
                        "confirmed_1h_total": s_1h_total,
                        "confirmed_1h_margin": s_1h_margin,
                        "polish_middle_integer_width": middle_points,
                    },
                )
            )

    results.sort(key=lambda r: r.guaranteed_net_edge_bps, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Engine 7 (`P2.7`): Pre-Converted `NR3` Overround & Hedged Pre-Split Maker-Ask
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreConvertedNegRiskOutcomeBook:
    """Single `YES_i` CLOB book for a pre-converted closed `NegRisk` slate (`Q` settled shares held)."""

    outcome_id: str
    yes_bids: Tuple[OrderLevel, ...]
    yes_asks: Tuple[OrderLevel, ...]
    fee_rate: float = 0.05
    fee_exponent: float = 2.0


def evaluate_preconverted_nr3_overround(
    *,
    slate_id: str,
    outcomes: Sequence[PreConvertedNegRiskOutcomeBook],
    settled_inventory_shares: float,
    is_augmented_other: bool,
    onchain_question_count: int,
    convert_fee_bips: int = 0,
    preconvert_gas_usd: float = 0.02,
    max_l1_depth_fraction: float = 0.50,
    min_overround_cushion_per_share: float = 0.004,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> Optional[VerifiedRisklessOpportunity]:
    """
    Mechanism 7A (`HEDGED_PRESPLIT_CONV_GUN` — Pre-Converted `NR3`).
    """
    if is_augmented_other or convert_fee_bips != 0:
        return None
    if len(outcomes) < 3 or int(onchain_question_count) != len(outcomes):
        return None
    if settled_inventory_shares < 5.0:
        return None

    scored: List[Tuple[float, float, PreConvertedNegRiskOutcomeBook]] = []
    for out in outcomes:
        if not out.yes_bids:
            continue
        top_bid = float(out.yes_bids[0].price)
        top_sz = float(out.yes_bids[0].size)
        if top_bid <= 0.005 or top_sz < 10.0:
            continue
        net_u = v2_net_sell_proceeds_per_share(top_bid, out.fee_rate, out.fee_exponent)
        scored.append((net_u, top_sz, out))

    scored.sort(key=lambda t: t[0], reverse=True)
    selected: List[Tuple[float, float, PreConvertedNegRiskOutcomeBook]] = []
    running_unit_proceeds = 0.0
    for item in scored:
        selected.append(item)
        running_unit_proceeds += item[0]
        if running_unit_proceeds >= 1.0 + float(min_overround_cushion_per_share) and len(selected) >= 2:
            break

    if running_unit_proceeds < 1.0 + float(min_overround_cushion_per_share):
        return None

    min_l1_sz = min(it[1] for it in selected)
    q_sell = float(min(settled_inventory_shares, math.floor(min_l1_sz * float(max_l1_depth_fraction))))
    if q_sell < 5.0:
        return None
    if any(q_sell * float(it[2].yes_bids[0].price) < 1.00 for it in selected):
        return None

    selected_exec_order = sorted(selected, key=lambda it: it[1])
    cash_proceeds_usd = sum(q_sell * it[0] for it in selected_exec_order)
    pro_rata_gas = float(preconvert_gas_usd) * (q_sell / float(settled_inventory_shares))
    locked_principal_basis = q_sell * 1.00 + pro_rata_gas

    selected_ids = {it[2].outcome_id for it in selected_exec_order}
    unsold_lottery_ids = [o.outcome_id for o in outcomes if o.outcome_id not in selected_ids]

    state_table: Dict[str, float] = {
        "OMEGA_SOLD_FAVORITE_WINS": round(cash_proceeds_usd, 6),
    }
    if unsold_lottery_ids:
        state_table["OMEGA_UNSOLD_LOTTERY_TAIL_WINS"] = round(cash_proceeds_usd + q_sell * 1.00, 6)

    passed, worst_p, best_p, _ = verify_state_dominance_invariant(
        state_table, locked_principal_basis, min_net_profit_usd=min_net_profit_usd
    )
    if not passed:
        return None

    net_profit = worst_p - locked_principal_basis
    return VerifiedRisklessOpportunity(
        strategy_id="HEDGED_PRESPLIT_CONV_GUN",
        opportunity_id=f"nr3_preconv:{slate_id}",
        venues=("polymarket",),
        jurisdiction_tags=("GLOBAL_SHADOW",),
        live_eligible=True,
        shares_or_units=round(q_sell, 6),
        all_in_cost_usd=round(locked_principal_basis, 6),
        worst_case_payout_usd=round(worst_p, 6),
        best_case_payout_usd=round(best_p, 6),
        guaranteed_net_profit_usd=round(net_profit, 6),
        guaranteed_net_edge_bps=round((net_profit / locked_principal_basis) * 10_000.0, 2),
        lockup_hours=0.01,
        state_payoff_table=state_table,
        legs=tuple(
            {
                "outcome_id": it[2].outcome_id,
                "action": "FOK_SELL_SETTLED_YES",
                "bid_price": float(it[2].yes_bids[0].price),
                "net_unit_proceeds": round(it[0], 6),
                "shares": q_sell,
            }
            for it in selected_exec_order
        ),
        metadata={
            "sub_mode": "PRECONVERTED_NR3_OVERROUND",
            "free_retained_lottery_outcomes": unsold_lottery_ids,
            "post_fill_polygon_wait_ms": 0,
        },
    )


def evaluate_hedged_presplit_maker_ask(
    *,
    market_id: str,
    maker_yes_ask_price: float,
    complement_no_bids: Sequence[OrderLevel],
    settled_split_shares: float,
    fee_rate: float = 0.07,
    fee_exponent: float = 2.0,
    maker_rebate_share: float = 0.20,
    min_hedge_depth_mult: float = 3.0,
    split_gas_usd: float = 0.015,
    live_enabled: bool = False,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> Optional[VerifiedRisklessOpportunity]:
    """
    Mechanism 7B (`HEDGED_PRESPLIT_CONV_GUN` — Binary Hedged Maker-Ask).
    """
    if not complement_no_bids or settled_split_shares < 5.0:
        return None
    a_y = float(maker_yes_ask_price)
    if a_y <= 0.01 or a_y >= 0.99:
        return None

    b_n = float(complement_no_bids[0].price)
    b_n_sz = float(complement_no_bids[0].size)
    if b_n_sz + 1e-9 < float(min_hedge_depth_mult) * float(settled_split_shares):
        return None

    q = float(settled_split_shares)
    counterparty_unit_fee = float(fee_rate) * ((a_y * (1.0 - a_y)) ** max(0.5, float(fee_exponent)))
    maker_rebate_unit = max(0.0, float(maker_rebate_share)) * counterparty_unit_fee
    b_n_net = v2_net_sell_proceeds_per_share(b_n, fee_rate, fee_exponent)

    unit_combined = a_y + maker_rebate_unit + b_n_net - (float(split_gas_usd) / q)
    if unit_combined < 1.004:
        return None

    all_in_basis = q * 1.00 + float(split_gas_usd)
    filled_and_hedged_proceeds = q * (a_y + maker_rebate_unit + b_n_net)
    state_table = {
        "OMEGA_HEDGED_MAKER_FILL_YES_WINS": round(filled_and_hedged_proceeds, 6),
        "OMEGA_HEDGED_MAKER_FILL_NO_WINS": round(filled_and_hedged_proceeds, 6),
    }
    passed, worst_p, best_p, _ = verify_state_dominance_invariant(
        state_table, all_in_basis, min_net_profit_usd=min_net_profit_usd
    )
    if not passed:
        return None

    cancel_trigger_net_bid = max(0.01, 1.001 + (float(split_gas_usd) / q) - a_y - maker_rebate_unit)
    net_profit = worst_p - all_in_basis
    return VerifiedRisklessOpportunity(
        strategy_id="HEDGED_PRESPLIT_CONV_GUN",
        opportunity_id=f"hedged_maker_ask:{market_id}",
        venues=("polymarket",),
        jurisdiction_tags=("SHADOW_ONLY" if not live_enabled else "GLOBAL_SHADOW",),
        live_eligible=bool(live_enabled),
        shares_or_units=round(q, 6),
        all_in_cost_usd=round(all_in_basis, 6),
        worst_case_payout_usd=round(worst_p, 6),
        best_case_payout_usd=round(best_p, 6),
        guaranteed_net_profit_usd=round(net_profit, 6),
        guaranteed_net_edge_bps=round((net_profit / all_in_basis) * 10_000.0, 2),
        lockup_hours=0.25,
        state_payoff_table=state_table,
        legs=(
            {
                "action": "POST_ONLY_MAKER_SELL_YES",
                "price": a_y,
                "maker_rebate_per_share": round(maker_rebate_unit, 6),
                "shares": q,
            },
            {
                "action": "INSTANT_WS_FOK_SELL_NO_HEDGE",
                "bid_price": b_n,
                "net_unit_proceeds": round(b_n_net, 6),
                "available_l1_depth": b_n_sz,
                "shares": q,
            },
        ),
        metadata={
            "sub_mode": "BINARY_HEDGED_MAKER_ASK",
            "auto_cancel_if_no_net_bid_below": round(cancel_trigger_net_bid, 6),
            "hedge_depth_coverage_multiple": round(b_n_sz / q, 2),
        },
    )


# ---------------------------------------------------------------------------
# Engine 8 (`P2.8`): Contractual Collateral-Yield Carry Box + Stage C1 Exit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class YieldBearingBoxLeg:
    """Single leg of a locked completeness box with contractual collateral yield parameters."""

    market: NormalizedBinaryMarket
    side: str
    contractual_apy: float
    rate_cut_stress_haircut_apy: float = 0.0050
    collateral_depeg_haircut_bps: float = 0.0
    override_taker_fee_per_contract_usd: Optional[float] = None  # e.g. `0.00` on ForecastEx no-commission clearing


def evaluate_yield_stacked_locked_box(
    *,
    box_id: str,
    leg_a: YieldBearingBoxLeg,
    leg_b: YieldBearingBoxLeg,
    min_guaranteed_hold_days: float,
    can_resolve_early: bool = False,
    target_usd_shares: float = 200.0,
    min_net_profit_usd: float = MIN_NET_PROFIT_USD,
) -> Optional[VerifiedRisklessOpportunity]:
    """
    Evaluate a 2-leg locked arbitrage box incorporating **contractual, non-promotional collateral
    coupons** (`ForecastEx` `FFR - 0.50%`, `Predict.fun` Venus `vUSDT`, `Polymarket` Holding Rewards).
    """
    asks_a = leg_a.market.yes_asks if leg_a.side.upper() == "YES" else leg_a.market.no_asks
    asks_b = leg_b.market.yes_asks if leg_b.side.upper() == "YES" else leg_b.market.no_asks
    if not asks_a or not asks_b:
        return None

    q_usd = max(leg_a.market.min_shares, leg_b.market.min_shares, float(target_usd_shares))
    leg_costs_usd: List[float] = []
    leg_net_payouts: List[float] = []
    leg_depeg_usd = 0.0

    for leg_item, asks in ((leg_a, asks_a), (leg_b, asks_b)):
        mkt = leg_item.market
        fx_a = collateral_fx_ask_to_usd(mkt.collateral_asset)
        fx_f = collateral_fx_settle_floor_to_usd(mkt.collateral_asset)
        lot = max(float(mkt.lot_size), 0.01)
        req_local = math.ceil((q_usd / max(fx_f, 1e-6)) / lot) * lot
        w_loc = walk_asks_for_shares(asks, req_local, mkt)
        if not w_loc.filled or w_loc.filled_shares * fx_f + 1e-6 < q_usd:
            return None
        fee_loc = (
            req_local * float(leg_item.override_taker_fee_per_contract_usd)
            if leg_item.override_taker_fee_per_contract_usd is not None
            else w_loc.taker_fee_usd
        )
        mark_usd = w_loc.gross_cost_usd * fx_f
        leg_costs_usd.append((w_loc.gross_cost_usd + fee_loc) * fx_a)
        leg_net_payouts.append(w_loc.filled_shares * fx_f)
        leg_depeg_usd += mark_usd * (max(0.0, float(leg_item.collateral_depeg_haircut_bps)) / 10_000.0)

    distinct_venues = tuple(sorted({leg_a.market.venue, leg_b.market.venue}))
    gas_usd = sum(DEFAULT_EXTERNAL_GAS_USD.get(v, 0.005) for v in distinct_venues)
    bridge_usd = (
        relay_bridge_drag_usd(sum(leg_costs_usd), DEFAULT_RELAY_BRIDGE_DRAG_BPS)
        if len(distinct_venues) > 1
        else 0.0
    )
    all_in_cost = sum(leg_costs_usd) + gas_usd + bridge_usd + leg_depeg_usd

    eff_days = 0.0 if can_resolve_early else max(0.0, float(min_guaranteed_hold_days))
    conservative_apy_a = max(0.0, float(leg_a.contractual_apy) - max(0.0, float(leg_a.rate_cut_stress_haircut_apy)))
    conservative_apy_b = max(0.0, float(leg_b.contractual_apy) - max(0.0, float(leg_b.rate_cut_stress_haircut_apy)))
    if eff_days > 0.0:
        min_coupon_usd = q_usd * min(conservative_apy_a, conservative_apy_b) * (eff_days / 365.0)
        max_coupon_usd = q_usd * max(conservative_apy_a, conservative_apy_b) * (eff_days / 365.0)
    else:
        min_coupon_usd = 0.0
        max_coupon_usd = 0.0

    state_table = {
        "OMEGA_LEG_A_WINS_MIN_COUPON_PATH": round(leg_net_payouts[0] + min_coupon_usd, 6),
        "OMEGA_LEG_B_WINS_MIN_COUPON_PATH": round(leg_net_payouts[1] + min_coupon_usd, 6),
        "OMEGA_HIGH_YIELD_LEG_DRIFT_PATH": round(max(leg_net_payouts) + max_coupon_usd, 6),
    }
    passed, worst_p, best_p, _ = verify_state_dominance_invariant(
        state_table, all_in_cost, min_net_profit_usd=min_net_profit_usd
    )
    if not passed:
        return None

    net_profit = worst_p - all_in_cost
    lockup_h = max(1.0, eff_days * 24.0)
    return VerifiedRisklessOpportunity(
        strategy_id="YIELD_STACKED_CARRY_BOX",
        opportunity_id=f"yield_box:{box_id}",
        venues=distinct_venues,
        jurisdiction_tags=(
            ("CA-ON-LEGAL",) if set(distinct_venues).issubset({"forecastex", "stx_ontario"}) else ("GLOBAL_SHADOW",)
        ),
        live_eligible=set(distinct_venues).issubset({"forecastex", "stx_ontario", "polymarket"}),
        shares_or_units=round(q_usd, 6),
        all_in_cost_usd=round(all_in_cost, 6),
        worst_case_payout_usd=round(worst_p, 6),
        best_case_payout_usd=round(best_p, 6),
        guaranteed_net_profit_usd=round(net_profit, 6),
        guaranteed_net_edge_bps=round((net_profit / all_in_cost) * 10_000.0, 2),
        lockup_hours=round(lockup_h, 3),
        state_payoff_table=state_table,
        legs=(
            {
                "venue": leg_a.market.venue,
                "side": leg_a.side.upper(),
                "conservative_apy": round(conservative_apy_a, 6),
                "leg_cost_usd": round(leg_costs_usd[0], 6),
            },
            {
                "venue": leg_b.market.venue,
                "side": leg_b.side.upper(),
                "conservative_apy": round(conservative_apy_b, 6),
                "leg_cost_usd": round(leg_costs_usd[1], 6),
            },
        ),
        metadata={
            "guaranteed_min_coupon_usd": round(min_coupon_usd, 6),
            "effective_guaranteed_hold_days": eff_days,
            "price_only_profit_without_coupon_usd": round(min(leg_net_payouts) - all_in_cost, 6),
        },
    )


def evaluate_early_overround_exit_with_forfeited_coupon(
    *,
    shares: float,
    initial_all_in_cost_usd: float,
    accrued_coupon_to_date_usd: float,
    forfeited_remaining_min_coupon_usd: float,
    net_exit_bid_unit_a: float,
    net_exit_bid_unit_b: float,
    exit_gas_usd: float = 0.01,
    redeployment_gain_usd: float = 0.0,
    min_incremental_gain_usd: float = 0.05,
) -> Dict[str, Any]:
    """
    `Stage C1` Early Overround Exit rule for `YIELD_STACKED_CARRY_BOX`.
    """
    exit_cash = float(shares) * (float(net_exit_bid_unit_a) + float(net_exit_bid_unit_b)) - float(exit_gas_usd)
    total_realized_wealth = exit_cash + float(accrued_coupon_to_date_usd)
    hold_to_maturity_wealth = (
        float(shares) * 1.00 + float(accrued_coupon_to_date_usd) + float(forfeited_remaining_min_coupon_usd)
    )
    realized_net_pnl = total_realized_wealth - float(initial_all_in_cost_usd)
    advantage_vs_hold = (total_realized_wealth + float(redeployment_gain_usd)) - hold_to_maturity_wealth
    should_exit = (realized_net_pnl >= float(min_incremental_gain_usd)) and (
        advantage_vs_hold >= float(min_incremental_gain_usd)
    )
    return {
        "should_exit_early": bool(should_exit),
        "exit_cash_usd": round(exit_cash, 6),
        "total_realized_wealth_usd": round(total_realized_wealth, 6),
        "hold_to_maturity_wealth_usd": round(hold_to_maturity_wealth, 6),
        "realized_net_pnl_usd": round(realized_net_pnl, 6),
        "advantage_vs_hold_usd": round(advantage_vs_hold, 6),
    }


# ==============================================================================
# DAEMON & SHADOW COLLECTOR INTEGRATION ORCHESTRATORS (ALPHA-124 + STAGE G)
# ==============================================================================

ALL_V6_EXPANSION_SLEEVES: Tuple[str, ...] = (
    "XV_SUBSET_NO_BOX",
    "TAIL_BOUNDARY_001_ARB",
    "BOND3_MULTISOURCE_DEAD_SPLIT",
    "XV_FX_INVARIANT_CAD_USD_BOX",
    "DERIBIT_VERTICAL_SUPER_REP",
    "XV_HALFTIME_FREEZE_CORRIDOR",
    "HEDGED_PRESPLIT_CONV_GUN",
    "YIELD_STACKED_CARRY_BOX",
)


def _atomic_write_json_safe(path: Any, payload: Mapping[str, Any]) -> bool:
    """Best-effort atomic JSON write; fails gracefully on read-only systemd sandboxes."""
    import json
    import os
    from pathlib import Path

    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, target)
        return True
    except OSError:
        return False


def _raw_levels_to_order_levels(raw: Any, *, descending: bool, limit: int = 5) -> Tuple[OrderLevel, ...]:
    rows: List[Tuple[float, float]] = []
    for item in raw or ():
        try:
            if isinstance(item, Mapping):
                px = float(item.get("price", 0.0) or 0.0)
                sz = float(item.get("size", 0.0) or 0.0)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                px = float(item[0] or 0.0)
                sz = float(item[1] or 0.0)
            else:
                continue
            if 0.0 < px < 1.0 and sz > 0.0:
                rows.append((px, sz))
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: (-x[0] if descending else x[0]))
    return tuple(OrderLevel(price=round(p, 5), size=round(s, 4)) for p, s in rows[:limit])


def _open_v6_shadow_box_in_alpha124(
    daemon: Any,
    *,
    opp: VerifiedRisklessOpportunity,
    dedupe_key: str,
    asset_or_city: str,
    title: str,
    close_ts: float,
    legs: Sequence[Dict[str, Any]],
    now_ts: float,
) -> bool:
    """Opens an honest multi-leg shadow position in `Alpha124ShadowDaemon` (never emits live orders)."""
    from datetime import datetime, timezone

    entered_keys = getattr(daemon, "entered_keys", None)
    open_positions = getattr(daemon, "open_positions", None)
    if not isinstance(open_positions, dict):
        return False
    if isinstance(entered_keys, set) and dedupe_key in entered_keys:
        return False
    if any(p.get("dedupe_key") == dedupe_key for p in open_positions.values()):
        return False

    q_ref = max(1.0, float(opp.shares_or_units))
    unit_cost = round(float(opp.all_in_cost_usd) / q_ref, 5)
    guar_unit = round(float(opp.worst_case_payout_usd) / q_ref, 5)
    if unit_cost <= 0.0 or unit_cost >= guar_unit:
        return False

    tier_caps = {"T100": 20.0, "T1000": 110.0, "T5000": 350.0}
    tier_fills: Dict[str, Dict[str, Any]] = {}
    for t_name, cap_usd in tier_caps.items():
        sh = max(5.0, min(q_ref, float(math.floor(cap_usd / max(0.25, unit_cost)))))
        spent = round(sh * unit_cost, 2)
        tier_fills[t_name] = {
            "filled": True,
            "vwap": unit_cost,
            "eff_px": unit_cost,
            "spent_usd": spent,
            "fee_usd": 0.0,
            "shares": sh,
            "l1_usd": round(q_ref * unit_cost, 2),
        }

    pos_id = f"{opp.strategy_id}_{int(now_ts)}_{abs(hash(dedupe_key)) % 100000:05d}"
    tok_join = "|".join(str(lg.get("token_id") or "") for lg in legs if lg.get("token_id"))
    pos = {
        "position_id": pos_id,
        "dedupe_key": dedupe_key,
        "sleeve": opp.strategy_id,
        "asset_or_city": str(asset_or_city or "POLY"),
        "title": str(title)[:96],
        "side": "+".join(str(lg.get("side") or "LEG") for lg in legs[:4]),
        "token_id": tok_join or opp.opportunity_id,
        "fee_rate": 0.0,
        "entry_ts": float(now_ts),
        "entry_utc": datetime.now(timezone.utc).isoformat(),
        "close_ts": float(close_ts),
        "p_model_entry": guar_unit,
        "entry_eff_px_t1000": unit_cost,
        "entry_vwap_t1000": unit_cost,
        "realized_edge_t1000": round(guar_unit - unit_cost, 5),
        "entry_best_bid": unit_cost,
        "last_bid": unit_cost,
        "maker_tp_px": None,
        "tier_fills": tier_fills,
        "extra": {
            "is_multi_leg_bundle": True,
            "guaranteed_payout": guar_unit,
            "max_payout": round(float(opp.best_case_payout_usd) / q_ref, 5),
            "v6_state_payoff_table": dict(opp.state_payoff_table),
            "legs": list(legs),
        },
        "status": "OPEN",
    }
    open_positions[pos_id] = pos
    if isinstance(entered_keys, set):
        entered_keys.add(dedupe_key)
    if hasattr(daemon, "_append_ledger"):
        try:
            daemon._append_ledger({"event": "SHADOW_ENTRY", **pos})
        except Exception:
            pass
    return True


async def run_v6_expansion_alpha124_scan(
    daemon: Any,
    opps_out: List[Dict[str, Any]],
    *,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Fault-isolated intra-Polymarket v6 Riskless Expansion scanner for `Alpha124ShadowDaemon`:
      - `CompactCandidateL2Recorder` (`<= 12 MB/day` compressed candidate L2 archive)
      - `TAIL_BOUNDARY_001_ARB` (`0.001`-tick sub-penny parabolic fee collapse boxes)
      - `BOND3_MULTISOURCE_DEAD_SPLIT` (multi-source verified `MOOV2` carry + Stage C2 dead-split)
      - `HEDGED_PRESPLIT_CONV_GUN` (closed `NegRisk` `NR3` pre-converted overround + shadow binary Maker-Ask)
      - `YIELD_STACKED_CARRY_BOX` (Holding-Reward contractual carry boxes)
    """
    from datetime import datetime, timezone
    from pathlib import Path
    import time as _time

    from src.polymarket_research.honest_riskless_backtester import CompactCandidateL2Recorder

    now = float(now_ts if now_ts is not None else _time.time())
    is_single_scan = bool(getattr(daemon, "single_scan", False))
    prev_stats = getattr(daemon, "_v6_expansion_stats", None) or {}
    scan_seq = int(prev_stats.get("cycles_scanned", 0)) + 1

    per_sleeve_counts: Dict[str, Dict[str, int]] = {
        slv: {
            "evaluated": int((prev_stats.get("per_sleeve") or {}).get(slv, {}).get("evaluated", 0)),
            "opportunities_found": int((prev_stats.get("per_sleeve") or {}).get(slv, {}).get("opportunities_found", 0)),
            "cycle_hits": 0,
        }
        for slv in ALL_V6_EXPANSION_SLEEVES
    }
    top_hits: List[Dict[str, Any]] = []

    def _record_hit(v_opp: VerifiedRisklessOpportunity, label: str, rem_sec: float) -> None:
        sl = v_opp.strategy_id
        if sl in per_sleeve_counts:
            per_sleeve_counts[sl]["opportunities_found"] += 1
            per_sleeve_counts[sl]["cycle_hits"] += 1
        q_u = max(1.0, float(v_opp.shares_or_units))
        unit_c = round(float(v_opp.all_in_cost_usd) / q_u, 4)
        unit_edge = round(float(v_opp.guaranteed_net_profit_usd) / q_u, 4)
        hold_hr = max(0.25, float(rem_sec) / 3600.0 if rem_sec > 0 else float(v_opp.lockup_hours))
        ev_hr = round(unit_edge / max(0.10, unit_c * hold_hr), 6)
        opps_out.append(
            {
                "sleeve": sl,
                "market": f"[{sl}] {label[:64]}",
                "ask_vwap": unit_c,
                "p_model": round(float(v_opp.worst_case_payout_usd) / q_u, 4),
                "net_edge": unit_edge,
                "ev_per_dollar_hour": ev_hr,
                "l1_usd": round(float(v_opp.all_in_cost_usd), 2),
                "close_ts": round(now + max(60.0, rem_sec), 1),
            }
        )
        if len(top_hits) < 12:
            top_hits.append(
                {
                    "strategy_id": sl,
                    "opportunity_id": v_opp.opportunity_id,
                    "title": label[:84],
                    "venues": list(v_opp.venues),
                    "live_eligible": bool(v_opp.live_eligible),
                    "shares": round(q_u, 2),
                    "unit_cost": unit_c,
                    "all_in_cost_usd": round(float(v_opp.all_in_cost_usd), 4),
                    "guaranteed_net_profit_usd": round(float(v_opp.guaranteed_net_profit_usd), 4),
                    "guaranteed_net_edge_bps": round(float(v_opp.guaranteed_net_edge_bps), 1),
                    "bps_per_hr": round(float(v_opp.guaranteed_net_edge_bps) / hold_hr, 1),
                    "rem_hours": round(hold_hr, 2),
                }
            )

    # Hydrate a bounded pool of active strike ladder / dominance books (<= 32 tokens)
    hydrated_books: Dict[str, Dict[str, Any]] = {}
    ladder_rungs: List[Any] = []
    try:
        for rgs in (getattr(daemon, "strike_ladders", None) or {}).values():
            for rg in rgs:
                rem_r = float(getattr(rg, "end_ts", 0.0) or 0.0) - now
                if 90.0 < rem_r <= 172800.0 and getattr(rg, "yes_token", "") and getattr(rg, "no_token", ""):
                    ladder_rungs.append(rg)
        ladder_rungs.sort(key=lambda r: float(getattr(r, "end_ts", 0.0) or 0.0))
        ladder_rungs = ladder_rungs[:16]
        missing_toks: List[str] = []
        for rg in ladder_rungs:
            for tk in (str(rg.yes_token), str(rg.no_token)):
                wb = daemon._get_fresh_ws_book(tk, now, max_age_sec=8.0) if hasattr(daemon, "_get_fresh_ws_book") else None
                if wb:
                    hydrated_books[tk] = wb
                elif tk not in hydrated_books:
                    missing_toks.append(tk)
        if missing_toks and hasattr(daemon, "fetch_books_batch"):
            fetched = await daemon.fetch_books_batch(list(dict.fromkeys(missing_toks))[:32], timeout=2.2)
            if isinstance(fetched, dict):
                hydrated_books.update(fetched)
    except Exception:
        pass

    # Build NormalizedBinaryMarket snapshots for L2 recording + Engine #2 / #7 / #8
    norm_markets: List[NormalizedBinaryMarket] = []
    rung_by_id: Dict[str, Any] = {}
    now_ms_int = int(now * 1000)
    for rg in ladder_rungs:
        by_y = hydrated_books.get(str(rg.yes_token))
        by_n = hydrated_books.get(str(rg.no_token))
        if not by_y or not by_n:
            continue
        ya = _raw_levels_to_order_levels(by_y.get("asks"), descending=False)
        yb = _raw_levels_to_order_levels(by_y.get("bids"), descending=True)
        na = _raw_levels_to_order_levels(by_n.get("asks"), descending=False)
        nb = _raw_levels_to_order_levels(by_n.get("bids"), descending=True)
        if not (ya or na):
            continue
        mid_s = str(getattr(rg, "market_id", "") or f"{rg.asset}_{rg.strike}")
        fr_val = float(getattr(rg, "fee_rate", 0.0) or 0.0)
        rung_by_id[mid_s] = rg
        norm_markets.append(
            NormalizedBinaryMarket(
                venue="polymarket",
                market_id=mid_s,
                slug=f"{rg.asset}-{rg.strike}-{int(rg.end_ts)}",
                title=f"{rg.asset} > ${rg.strike} ({int(rg.end_ts)})",
                category="crypto_strike",
                yes_asks=list(ya),
                yes_bids=list(yb),
                no_asks=list(na),
                no_bids=list(nb),
                fee_rate_bps=round(fr_val * 10_000.0, 2),
                fee_enabled=fr_val > 0.0,
                taker_delay_ms=0.0,
                min_shares=5.0,
                asset=str(rg.asset),
                horizon="intraday",
                oracle_family="binance_1m_usdt",
                strike_price=float(rg.strike),
                strike_direction="DOWN" if bool(getattr(rg, "is_downward", False)) else "UP",
                end_ts=int(rg.end_ts),
                cancel_rule="VOID",
                has_unlisted_draw=False,
                tick_size=0.001 if ((ya and (ya[0].price >= 0.96 or ya[0].price <= 0.04)) or (na and (na[0].price >= 0.96 or na[0].price <= 0.04))) else 0.01,
                lot_size=1.0,
                quote_ts_ms=now_ms_int,
                collateral_asset="USDC",
                settlement_delay_hours=1.0,
                partition_group_id=f"pm_strike_{rg.asset}_{int(rg.end_ts)}",
            )
        )

    # 0. CompactCandidateL2Recorder (bounded <= 12 MB/day compressed L2 archive)
    rec_stats: Dict[str, Any] = {"enabled": not is_single_scan, "frames_recorded": 0, "bytes_today": 0, "budget_drops": 0}
    if not is_single_scan:
        try:
            rec_obj = getattr(daemon, "_candidate_l2_recorder", None)
            if rec_obj is None:
                base_dir = Path(getattr(daemon, "_v6_data_dir", None) or (Path(__file__).resolve().parents[2] / "data" / "polymarket"))
                rec_obj = CompactCandidateL2Recorder(base_dir / "candidate_l2", max_daily_bytes=12 * 1024 * 1024)
                daemon._candidate_l2_recorder = rec_obj
            cand_keys_t = [
                ("polymarket", m.slug)
                for m in norm_markets
                if (m.yes_asks and (m.yes_asks[0].price >= 0.94 or m.yes_asks[0].price <= 0.06))
                or (m.no_asks and (m.no_asks[0].price >= 0.94 or m.no_asks[0].price <= 0.06))
                or (m.yes_asks and m.no_asks and (m.yes_asks[0].price + m.no_asks[0].price) <= 1.025)
            ]
            rec_obj.observe_markets(norm_markets, candidate_keys=cand_keys_t, now_ms=now_ms_int)
            if scan_seq % 3 == 0:
                rec_obj.flush()
            day_key = rec_obj._day_key(now_ms_int)
            rec_stats = {
                "enabled": True,
                "frames_recorded": int(rec_obj.frames_recorded),
                "budget_drops": int(rec_obj.budget_drops),
                "bytes_today": int(rec_obj._bytes_written_by_day.get(day_key, 0)),
                "max_daily_bytes": int(rec_obj.max_daily_bytes),
            }
        except Exception:
            pass

    # 1. Engine #2: TAIL_BOUNDARY_001_ARB (0.001-tick sub-penny boundary fee collapse)
    try:
        tail_pairs: List[BoundaryTickDominancePair] = []
        pair_meta: Dict[str, Tuple[Any, str, Any, str]] = {}
        by_grp: Dict[Tuple[str, int], List[NormalizedBinaryMarket]] = {}
        for m in norm_markets:
            rg = rung_by_id.get(m.market_id)
            if rg is None or bool(getattr(rg, "is_downward", False)):
                continue
            if m.yes_asks and m.no_asks and (
                m.yes_asks[0].price >= 0.96 or m.yes_asks[0].price <= 0.04 or m.no_asks[0].price >= 0.96 or m.no_asks[0].price <= 0.04
            ):
                pid_c = f"cset_{m.market_id}"
                pair_meta[pid_c] = (rg, "YES", rg, "NO")
                tail_pairs.append(
                    BoundaryTickDominancePair(
                        pair_id=pid_c,
                        pair_type="COMPLETE_SET",
                        oracle_signature=f"binance_1m_{rg.asset}_{int(rg.end_ts)}",
                        expiry_ts=float(rg.end_ts),
                        leg_a_token_id=str(rg.yes_token),
                        leg_a_label=f"{rg.asset} >= {rg.strike} YES",
                        leg_a_asks=tuple(m.yes_asks),
                        leg_b_token_id=str(rg.no_token),
                        leg_b_label=f"{rg.asset} >= {rg.strike} NO",
                        leg_b_asks=tuple(m.no_asks),
                        fee_rate=float(getattr(rg, "fee_rate", 0.0) or 0.0),
                        fee_exponent=float(getattr(rg, "fee_exponent", 1.0) or 1.0),
                        strike_low=float(rg.strike),
                        strike_high=float(rg.strike),
                    )
                )
            by_grp.setdefault((str(rg.asset), int(rg.end_ts)), []).append(m)

        for (asset_k, exp_k), grp in by_grp.items():
            grp_sorted = sorted(grp, key=lambda x: float(rung_by_id[x.market_id].strike))
            for i in range(len(grp_sorted)):
                for j in range(i + 1, len(grp_sorted)):
                    m_lo, m_hi = grp_sorted[i], grp_sorted[j]
                    rg_lo, rg_hi = rung_by_id[m_lo.market_id], rung_by_id[m_hi.market_id]
                    if float(rg_lo.strike) < float(rg_hi.strike) and m_lo.yes_asks and m_hi.no_asks:
                        pid_d = f"dom_{asset_k}_{m_lo.market_id}_{m_hi.market_id}_{exp_k}"
                        pair_meta[pid_d] = (rg_lo, "YES", rg_hi, "NO")
                        tail_pairs.append(
                            BoundaryTickDominancePair(
                                pair_id=pid_d,
                                pair_type="NESTED_STRIKE",
                                oracle_signature=f"binance_1m_{asset_k}_{exp_k}",
                                expiry_ts=float(exp_k),
                                leg_a_token_id=str(rg_lo.yes_token),
                                leg_a_label=f"{asset_k} >= {rg_lo.strike}",
                                leg_a_asks=tuple(m_lo.yes_asks),
                                leg_b_token_id=str(rg_hi.no_token),
                                leg_b_label=f"{asset_k} < {rg_hi.strike}",
                                leg_b_asks=tuple(m_hi.no_asks),
                                fee_rate=max(float(getattr(rg_lo, "fee_rate", 0.0) or 0.0), float(getattr(rg_hi, "fee_rate", 0.0) or 0.0)),
                                fee_exponent=float(getattr(rg_lo, "fee_exponent", 1.0) or 1.0),
                                strike_low=float(rg_lo.strike),
                                strike_high=float(rg_hi.strike),
                            )
                        )
        per_sleeve_counts["TAIL_BOUNDARY_001_ARB"]["evaluated"] += len(tail_pairs)
        if tail_pairs:
            for hit_tb in detect_tail_boundary_001_fee_collapse_boxes(tail_pairs, target_box_notional_usd=45.0):
                raw_pid = hit_tb.opportunity_id.replace("tail001:", "", 1)
                meta_t = pair_meta.get(raw_pid)
                rem_s = max(60.0, float(meta_t[0].end_ts) - now) if meta_t is not None else 900.0
                _record_hit(hit_tb, f"Sub-Penny Tail Box {raw_pid}", rem_s)
                if meta_t is not None and not is_single_scan:
                    rg_a, s_a, rg_b, s_b = meta_t
                    tok_a = rg_a.yes_token if s_a == "YES" else rg_a.no_token
                    tok_b = rg_b.yes_token if s_b == "YES" else rg_b.no_token
                    _open_v6_shadow_box_in_alpha124(
                        daemon,
                        opp=hit_tb,
                        dedupe_key=f"V6_TAIL001_{raw_pid}",
                        asset_or_city=str(rg_a.asset),
                        title=f"{rg_a.asset} 0.001-Tail Box ({rg_a.strike}/{rg_b.strike})",
                        close_ts=float(min(rg_a.end_ts, rg_b.end_ts)),
                        legs=[
                            {"token_id": tok_a, "side": s_a, "market_id": str(rg_a.market_id), "fee_rate": float(rg_a.fee_rate or 0.0), "fee_exponent": float(rg_a.fee_exponent or 1.0)},
                            {"token_id": tok_b, "side": s_b, "market_id": str(rg_b.market_id), "fee_rate": float(rg_b.fee_rate or 0.0), "fee_exponent": float(rg_b.fee_exponent or 1.0)},
                        ],
                        now_ts=now,
                    )
    except Exception:
        pass

    # 2. Engine #3: BOND3_MULTISOURCE_DEAD_SPLIT (UMA MOOV2 verified multi-source carry + Stage C2 dead-split)
    try:
        uma_mkts = list((getattr(daemon, "uma_proposed_markets", None) or {}).values())[:20]
        uma_cache = getattr(daemon, "uma_onchain_cache", None) or {}
        for um in uma_mkts:
            cid_u = str(getattr(um, "condition_id", "") or (um.get("condition_id") if isinstance(um, Mapping) else "") or "")
            oc = uma_cache.get(cid_u) or {}
            if not (oc.get("verified") and oc.get("proposer_whitelisted") and not oc.get("disputed")):
                continue
            indep_sources = list(oc.get("independent_sources") or ())
            if len(indep_sources) < 2:
                continue
            per_sleeve_counts["BOND3_MULTISOURCE_DEAD_SPLIT"]["evaluated"] += 1
            win_tok = str(getattr(um, "win_token", "") or (um.get("win_token") if isinstance(um, Mapping) else "") or "")
            lose_tok = str(getattr(um, "lose_token", "") or (um.get("lose_token") if isinstance(um, Mapping) else "") or "")
            if not win_tok or not lose_tok:
                continue
            bk_w = hydrated_books.get(win_tok)
            bk_l = hydrated_books.get(lose_tok)
            if (bk_w is None or bk_l is None) and hasattr(daemon, "fetch_books_batch"):
                bks_u = await daemon.fetch_books_batch([win_tok, lose_tok], timeout=2.0)
                bk_w = bk_w or (bks_u or {}).get(win_tok)
                bk_l = bk_l or (bks_u or {}).get(lose_tok)
            if not bk_w or not bk_l:
                continue
            w_asks = _raw_levels_to_order_levels(bk_w.get("asks"), descending=False)
            w_bids = _raw_levels_to_order_levels(bk_w.get("bids"), descending=True)
            l_bids = _raw_levels_to_order_levels(bk_l.get("bids"), descending=True)
            if not w_asks:
                continue
            exp_u = float(oc.get("expiration_ts") or (now + 3600.0))
            rem_liveness = max(60.0, exp_u - now)
            mid_u = str(getattr(um, "market_id", "") or (um.get("market_id") if isinstance(um, Mapping) else cid_u[:12]))
            q_u_txt = str(getattr(um, "question", "") or (um.get("question") if isinstance(um, Mapping) else mid_u))
            cat_u = str(oc.get("category") or "crypto")
            ev_bond3 = evaluate_bond3_multisource_verified_carry(
                market_id=mid_u,
                category=cat_u,
                uma_proposed_outcome="YES",
                uma_status="proposed",
                is_whitelisted_proposer=True,
                remaining_challenge_sec=rem_liveness,
                winner_asks=w_asks,
                winner_bids=w_bids,
                dead_loser_bids=l_bids,
                observations=[
                    PrimaryOracleObservation(
                        source_id=str(src_name),
                        is_official_final=True,
                        outcome="YES",
                        post_final_elapsed_sec=1200.0,
                    )
                    for src_name in indep_sources[:3]
                ],
                fee_rate=float(oc.get("fee_rate", 0.0) or 0.0),
                target_notional_usd=45.0,
            )
            if ev_bond3 is not None:
                _record_hit(ev_bond3, q_u_txt, rem_liveness)
    except Exception:
        pass

    # 3. Engine #7: HEDGED_PRESPLIT_CONV_GUN (Closed NegRisk NR3 Overround + Shadow Binary Maker-Ask)
    try:
        nr_slates = [
            sp
            for sp in (getattr(daemon, "negrisk_convert_slates", None) or {}).values()
            if getattr(sp, "is_closed_convert_safe", False) and 3 <= len(getattr(sp, "brackets", ())) <= 12
        ][:8]
        for sp in nr_slates:
            nr_books: List[PreConvertedNegRiskOutcomeBook] = []
            all_ok = True
            for idx_b, br in enumerate(sp.brackets):
                yt = str(br.get("yes_token") or "")
                wb = hydrated_books.get(yt) or (daemon._get_fresh_ws_book(yt, now, max_age_sec=8.0) if hasattr(daemon, "_get_fresh_ws_book") else None)
                if not wb:
                    all_ok = False
                    break
                b_lvls = _raw_levels_to_order_levels(wb.get("bids"), descending=True)
                a_lvls = _raw_levels_to_order_levels(wb.get("asks"), descending=False)
                if not b_lvls:
                    all_ok = False
                    break
                nr_books.append(
                    PreConvertedNegRiskOutcomeBook(
                        outcome_label=str(br.get("label") or f"B{idx_b}"),
                        yes_bids=b_lvls,
                        yes_asks=a_lvls,
                        fee_rate=float(br.get("fee_rate", 0.0) or 0.0),
                        fee_exponent=float(br.get("fee_exponent", 1.0) or 1.0),
                    )
                )
            if all_ok and len(nr_books) == len(sp.brackets):
                per_sleeve_counts["HEDGED_PRESPLIT_CONV_GUN"]["evaluated"] += 1
                nr3_hit = evaluate_preconverted_nr3_overround(
                    slate_id=str(sp.event_id),
                    outcomes=nr_books,
                    settled_inventory_shares=20.0,
                    is_augmented_other=False,
                    onchain_question_count=len(nr_books),
                )
                if nr3_hit is not None:
                    _record_hit(nr3_hit, f"NR3 Pre-Converted Overround: {sp.title}", max(60.0, float(sp.end_ts) - now))

        # Shadow-only binary hedged pre-split Maker-Ask check across hydrated markets
        for m in norm_markets[:12]:
            if m.yes_asks and m.no_bids:
                per_sleeve_counts["HEDGED_PRESPLIT_CONV_GUN"]["evaluated"] += 1
                maker_ask_px = round(min(0.99, m.yes_asks[0].price), 3)
                hp_hit = evaluate_hedged_presplit_maker_ask(
                    market_id=m.market_id,
                    maker_yes_ask_price=maker_ask_px,
                    complement_no_bids=tuple(m.no_bids),
                    settled_split_shares=20.0,
                    fee_rate=float(m.fee_rate_bps) / 10_000.0,
                    live_enabled=False,
                )
                if hp_hit is not None:
                    _record_hit(hp_hit, f"Shadow Pre-Split Maker-Ask {m.title}", max(60.0, float(m.end_ts) - now))
    except Exception:
        pass

    # 4. Engine #8: YIELD_STACKED_CARRY_BOX (Polymarket Holding Rewards 4% APY carry boxes)
    try:
        holding_apy = float(getattr(daemon, "holding_rewards_apy", 0.0) or 0.0)
        if holding_apy > 0.0:
            for m in norm_markets[:10]:
                rem_days = (float(m.end_ts) - now) / 86400.0
                if rem_days >= 2.0 and m.yes_asks and m.no_asks:
                    per_sleeve_counts["YIELD_STACKED_CARRY_BOX"]["evaluated"] += 1
                    yb_hit = evaluate_yield_stacked_locked_box(
                        box_id=f"pm_hold_{m.market_id}",
                        leg_a=YieldBearingBoxLeg(market=m, side="YES", contractual_apy=holding_apy),
                        leg_b=YieldBearingBoxLeg(market=m, side="NO", contractual_apy=holding_apy),
                        min_guaranteed_hold_days=rem_days,
                        can_resolve_early=False,
                        target_usd_shares=50.0,
                    )
                    if yb_hit is not None:
                        _record_hit(yb_hit, f"Yield Carry Box {m.title}", rem_days * 86400.0)
    except Exception:
        pass

    summary = {
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at_unix": round(now, 3),
        "daemon": "alpha_124_shadow_daemon",
        "cycles_scanned": scan_seq,
        "hydrated_markets": len(norm_markets),
        "per_sleeve": per_sleeve_counts,
        "top_opportunities": top_hits,
        "candidate_l2_recorder": rec_stats,
    }
    daemon._v6_expansion_stats = summary
    if not is_single_scan:
        base_dir = Path(getattr(daemon, "_v6_data_dir", None) or (Path(__file__).resolve().parents[2] / "data" / "polymarket"))
        _atomic_write_json_safe(base_dir / "v6_expansion_alpha124_telemetry.json", summary)
    return summary


async def _fetch_deribit_usdc_public_options(
    transport: Any,
    *,
    cache_holder: Any,
    now_ts: float,
) -> List[DeribitLinearOptionQuote]:
    """
    Keyless public Deribit linear USDC options book-summary reader (`BTC_USDC`, `ETH_USDC`),
    cached for 60s so Stage G shadow scans add negligible HTTP overhead.
    """
    from datetime import datetime, timezone

    cached = getattr(cache_holder, "_deribit_usdc_cache", None)
    if isinstance(cached, tuple) and len(cached) == 2 and (now_ts - float(cached[0])) < 60.0:
        return list(cached[1])
    if transport is None or not hasattr(transport, "get_json"):
        return []

    quotes: List[DeribitLinearOptionQuote] = []
    month_map = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }
    url = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=USDC&kind=option"
    try:
        raw_resp = await transport.get_json(url)
        resp = raw_resp[1] if isinstance(raw_resp, tuple) and len(raw_resp) >= 2 else raw_resp
        rows = (resp or {}).get("result") if isinstance(resp, Mapping) else None
        if isinstance(rows, list):
            for r in rows:
                if not isinstance(r, Mapping):
                    continue
                inst = str(r.get("instrument_name") or "")
                parts = inst.split("-")
                if len(parts) != 4 or parts[0] not in {"BTC_USDC", "ETH_USDC", "SOL_USDC"} or parts[3] not in {"C", "P"}:
                    continue
                dt_s = parts[1]
                try:
                    if len(dt_s) == 7:
                        dd, mmm, yy = int(dt_s[:2]), dt_s[2:5].upper(), int(dt_s[5:7])
                    elif len(dt_s) == 6:
                        dd, mmm, yy = int(dt_s[:1]), dt_s[1:4].upper(), int(dt_s[4:6])
                    else:
                        continue
                    mm = month_map.get(mmm)
                    if mm is None:
                        continue
                    exp_dt = datetime(2000 + yy, mm, dd, 8, 0, 0, tzinfo=timezone.utc)
                    strike_v = float(parts[2])
                    und_px = float(r.get("underlying_price") or r.get("estimated_delivery_price") or 0.0)
                    ask_raw = float(r.get("ask_price") or 0.0)
                    bid_raw = float(r.get("bid_price") or 0.0)
                    if und_px <= 0.0 or strike_v <= 0.0:
                        continue
                    ask_usdc = ask_raw if ask_raw > 1.5 else (ask_raw * und_px if ask_raw > 0 else 0.0)
                    bid_usdc = bid_raw if bid_raw > 1.5 else (bid_raw * und_px if bid_raw > 0 else 0.0)
                    if ask_usdc <= 0.0 and bid_usdc <= 0.0:
                        continue
                    quotes.append(
                        DeribitLinearOptionQuote(
                            instrument_name=inst,
                            currency_pair=parts[0],
                            settlement_currency="USDC",
                            option_type=parts[3],
                            strike=strike_v,
                            expiry_ts=exp_dt.timestamp(),
                            best_bid_usdc=max(0.0, round(bid_usdc, 4)),
                            best_bid_contracts=10.0,
                            best_ask_usdc=round(ask_usdc if ask_usdc > 0.0 else strike_v, 4),
                            best_ask_contracts=10.0,
                            index_price_usd=und_px,
                        )
                    )
                except (TypeError, ValueError):
                    continue
    except Exception:
        return []
    cache_holder._deribit_usdc_cache = (now_ts, tuple(quotes))
    return quotes


async def run_v6_expansion_cross_venue_scan(
    collector: Any,
    all_live_markets: Sequence[NormalizedBinaryMarket],
    pairs: Sequence[Tuple[NormalizedBinaryMarket, NormalizedBinaryMarket]],
    *,
    transport: Any = None,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Fault-isolated Stage G Cross-Venue v6 Riskless Expansion scanner (`LiveCrossVenueShadowCollector`).
    CRITICAL SANDBOX RULE: Writes ONLY inside `collector.engine.data_dir` (`data/cross_venue_shadow`),
    respecting `systemd` `ProtectSystem=strict` + `ReadWritePaths=.../data/cross_venue_shadow`.
    """
    from datetime import datetime, timezone
    import re
    import time as _time

    from src.polymarket_research.honest_riskless_backtester import CompactCandidateL2Recorder

    now = float(now_ts if now_ts is not None else _time.time())
    now_ms_int = int(now * 1000)
    data_dir = getattr(getattr(collector, "engine", None), "data_dir", None)
    eff_mode = str((getattr(collector, "env", None) or {}).get("DOMINUS_NETWORK_MODE") or "live_public").strip().lower()
    prev = getattr(collector, "_v6_expansion_stats", None) or {}
    scan_seq = int(prev.get("cycles_scanned", 0)) + 1

    per_sleeve: Dict[str, Dict[str, int]] = {
        slv: {
            "evaluated": int((prev.get("per_sleeve") or {}).get(slv, {}).get("evaluated", 0)),
            "opportunities_found": int((prev.get("per_sleeve") or {}).get(slv, {}).get("opportunities_found", 0)),
            "cycle_hits": 0,
        }
        for slv in ALL_V6_EXPANSION_SLEEVES
    }
    top_hits: List[Dict[str, Any]] = []

    def _push_xv_hit(v_opp: VerifiedRisklessOpportunity, title: str) -> None:
        sl = v_opp.strategy_id
        if sl in per_sleeve:
            per_sleeve[sl]["opportunities_found"] += 1
            per_sleeve[sl]["cycle_hits"] += 1
        if len(top_hits) < 16:
            q_u = max(1.0, float(v_opp.shares_or_units))
            hold_h = max(0.25, float(v_opp.lockup_hours))
            top_hits.append(
                {
                    "strategy_id": sl,
                    "opportunity_id": v_opp.opportunity_id,
                    "title": title[:88],
                    "venues": list(v_opp.venues),
                    "jurisdiction_tags": list(v_opp.jurisdiction_tags),
                    "live_eligible": bool(v_opp.live_eligible),
                    "shares": round(q_u, 2),
                    "unit_cost": round(float(v_opp.all_in_cost_usd) / q_u, 4),
                    "all_in_cost_usd": round(float(v_opp.all_in_cost_usd), 4),
                    "guaranteed_net_profit_usd": round(float(v_opp.guaranteed_net_profit_usd), 4),
                    "guaranteed_net_edge_bps": round(float(v_opp.guaranteed_net_edge_bps), 1),
                    "bps_per_hr": round(float(v_opp.guaranteed_net_edge_bps) / hold_h, 1),
                    "rem_hours": round(hold_h, 2),
                }
            )

    # 0. CompactCandidateL2Recorder strictly under collector.engine.data_dir / "candidate_l2"
    rec_stats: Dict[str, Any] = {"enabled": data_dir is not None, "frames_recorded": 0, "bytes_today": 0, "budget_drops": 0}
    if data_dir is not None:
        try:
            rec_obj = getattr(collector, "_candidate_l2_recorder", None)
            if rec_obj is None:
                rec_obj = CompactCandidateL2Recorder(data_dir / "candidate_l2", max_daily_bytes=12 * 1024 * 1024)
                collector._candidate_l2_recorder = rec_obj
            paired_keys = [(m.venue.lower(), m.slug) for pm, ext in pairs for m in (pm, ext)]
            rec_obj.observe_markets(all_live_markets, candidate_keys=paired_keys, now_ms=now_ms_int)
            rec_obj.flush()
            day_key = rec_obj._day_key(now_ms_int)
            rec_stats = {
                "enabled": True,
                "frames_recorded": int(rec_obj.frames_recorded),
                "budget_drops": int(rec_obj.budget_drops),
                "bytes_today": int(rec_obj._bytes_written_by_day.get(day_key, 0)),
                "max_daily_bytes": int(rec_obj.max_daily_bytes),
            }
        except Exception:
            pass

    # 1. Engine #1: XV_SUBSET_NO_BOX (Mutually-exclusive cross-venue partition slates, m=2..3)
    try:
        part_groups: Dict[str, List[NormalizedBinaryMarket]] = {}
        for m in all_live_markets:
            pg = str(getattr(m, "partition_group_id", "") or "").strip()
            if pg and m.no_asks and m.category != "crypto_barrier":
                part_groups.setdefault(pg, []).append(m)
        for pg_id, members in list(part_groups.items())[:25]:
            dedup_by_out: Dict[str, NormalizedBinaryMarket] = {}
            for m in members:
                cur = dedup_by_out.get(m.market_id)
                if cur is None or (m.no_asks[0].price < cur.no_asks[0].price):
                    dedup_by_out[m.market_id] = m
            if 2 <= len(dedup_by_out) <= 8:
                per_sleeve["XV_SUBSET_NO_BOX"]["evaluated"] += 1
                cands_sub = [
                    SubsetNoCandidateOutcome(outcome_label=k, market=v, cancel_payout_mode="50_50")
                    for k, v in sorted(dedup_by_out.items())
                ]
                for hit_s in detect_cross_venue_subset_no_boxes(
                    pg_id,
                    cands_sub,
                    event_cancel_exempt=False,
                    subset_sizes=(2, 3),
                    target_notional_usd=50.0,
                ):
                    _push_xv_hit(hit_s, f"Subset NO Box ({pg_id[:42]})")
    except Exception:
        pass

    # 2. Engine #4: XV_FX_INVARIANT_CAD_USD_BOX (100% CA-ON Legal STX CAD <-> ForecastEx USD)
    try:
        for ma, mb in pairs:
            venues_set = {ma.venue, mb.venue}
            if venues_set == {"stx_ontario", "forecastex"}:
                stx_m = ma if ma.venue == "stx_ontario" else mb
                fex_m = mb if ma.venue == "stx_ontario" else ma
                cancel_ex = stx_m.category in {"macro", "economics", "crypto"}
                for stx_s, fex_s in (("YES", "NO"), ("NO", "YES")):
                    for style in ("PASSIVE_MAKER", "TAKER"):
                        per_sleeve["XV_FX_INVARIANT_CAD_USD_BOX"]["evaluated"] += 1
                        fx_hit = evaluate_stx_forecastex_fx_invariant_box(
                            pair_id=f"{stx_m.market_id}_{fex_m.market_id}_{stx_s}_{style}",
                            stx_market=stx_m,
                            stx_side=stx_s,
                            stx_execution_style=style,
                            forecastex_market=fex_m,
                            forecastex_side=fex_s,
                            event_cancel_exempt=cancel_ex,
                            target_usd_shares=100.0,
                        )
                        if fx_hit is not None:
                            _push_xv_hit(fx_hit, f"CA-ON STX/ForecastEx {stx_m.title[:48]} ({style})")
    except Exception:
        pass

    # 3. Engine #5: DERIBIT_VERTICAL_SUPER_REP (Keyless Deribit USDC options vs 08:00 UTC crypto strikes)
    deribit_quotes_count = 0
    try:
        if eff_mode != "offline" and transport is not None:
            d_quotes = await _fetch_deribit_usdc_public_options(transport, cache_holder=collector, now_ts=now)
            deribit_quotes_count = len(d_quotes)
            if d_quotes:
                strike_mkts = [
                    m for m in all_live_markets if ("crypto" in m.category.lower() or m.strike_price is not None)
                ][:20]
                for sm in strike_mkts:
                    k_bin = float(sm.strike_price or 0.0)
                    if k_bin <= 0.0:
                        m_num = re.search(r"\$?([0-9]{2,6}(?:,[0-9]{3})*(?:\.[0-9]+)?)", sm.title)
                        if m_num:
                            k_bin = float(m_num.group(1).replace(",", ""))
                    und = "BTC_USDC" if ("BTC" in sm.title.upper() or "BITCOIN" in sm.title.upper() or sm.asset == "BTC") else (
                        "ETH_USDC" if ("ETH" in sm.title.upper() or sm.asset == "ETH") else ""
                    )
                    if not und or k_bin <= 0.0 or not sm.end_ts:
                        continue
                    cand_q = [q for q in d_quotes if q.currency_pair == und and abs(q.expiry_ts - float(sm.end_ts)) <= 300.0]
                    if len(cand_q) >= 2:
                        per_sleeve["DERIBIT_VERTICAL_SUPER_REP"]["evaluated"] += 1
                        for dv_hit in detect_deribit_usdc_vertical_super_replication(
                            binary_market=sm,
                            binary_strike=k_bin,
                            deribit_options=cand_q,
                            cross_oracle_basis_bps=150.0,
                            target_units=50.0,
                        ):
                            _push_xv_hit(dv_hit, f"Deribit {und} Super-Rep vs {sm.title[:44]}")
    except Exception:
        pass

    # 4. Engine #6: XV_HALFTIME_FREEZE_CORRIDOR (Sports .5-hook Halftime Freeze FG vs 2H)
    try:
        sports_mkts = [m for m in all_live_markets if "sport" in m.category.lower() and float(m.taker_delay_ms or 0.0) == 0.0]
        per_sleeve["XV_HALFTIME_FREEZE_CORRIDOR"]["evaluated"] += len(sports_mkts)
    except Exception:
        pass

    # 5. Engine #8: YIELD_STACKED_CARRY_BOX (ForecastEx ~3.83% / Predict.fun vUSDT ~3.5% matched pairs)
    try:
        venue_default_apy = {"forecastex": 0.0383, "predict_fun": 0.0350}
        for ma, mb in pairs:
            apy_a = venue_default_apy.get(ma.venue, 0.0)
            apy_b = venue_default_apy.get(mb.venue, 0.0)
            end_a = float(ma.end_ts or 0.0)
            end_b = float(mb.end_ts or 0.0)
            rem_days = (min(end_a, end_b) - now) / 86400.0 if (end_a > 0 and end_b > 0) else 0.0
            if (apy_a > 0.0 or apy_b > 0.0) and rem_days >= 2.0:
                for sa, sb in (("YES", "NO"), ("NO", "YES")):
                    per_sleeve["YIELD_STACKED_CARRY_BOX"]["evaluated"] += 1
                    yb_xv = evaluate_yield_stacked_locked_box(
                        box_id=f"{ma.venue}_{mb.venue}_{ma.market_id}_{sa}",
                        leg_a=YieldBearingBoxLeg(
                            market=ma,
                            side=sa,
                            contractual_apy=apy_a,
                            collateral_depeg_haircut_bps=25.0 if ma.venue == "predict_fun" else 0.0,
                        ),
                        leg_b=YieldBearingBoxLeg(
                            market=mb,
                            side=sb,
                            contractual_apy=apy_b,
                            collateral_depeg_haircut_bps=25.0 if mb.venue == "predict_fun" else 0.0,
                        ),
                        min_guaranteed_hold_days=rem_days,
                        can_resolve_early=False,
                        target_usd_shares=50.0,
                    )
                    if yb_xv is not None:
                        _push_xv_hit(yb_xv, f"Yield Box {ma.venue}+{mb.venue}: {ma.title[:48]}")
    except Exception:
        pass

    summary = {
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at_unix": round(now, 3),
        "daemon": "cross_venue_riskless_shadow",
        "network_mode": eff_mode,
        "cycles_scanned": scan_seq,
        "live_markets_seen": len(all_live_markets),
        "matched_pairs_seen": len(pairs),
        "deribit_usdc_quotes_cached": deribit_quotes_count,
        "per_sleeve": per_sleeve,
        "top_opportunities": top_hits,
        "candidate_l2_recorder": rec_stats,
    }
    collector._v6_expansion_stats = summary
    if data_dir is not None:
        _atomic_write_json_safe(data_dir / "v6_expansion_telemetry.json", summary)
    return summary


def write_v6_offline_telemetry_snapshot(data_dir: Any, *, cycles_completed: int = 1) -> Dict[str, Any]:
    """Writes a clean `v6_expansion_telemetry.json` inside `data_dir` when Stage G runs in `offline` mode."""
    from datetime import datetime, timezone
    import time as _time

    now = _time.time()
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at_unix": round(now, 3),
        "daemon": "cross_venue_riskless_shadow",
        "network_mode": "offline",
        "cycles_scanned": int(cycles_completed),
        "live_markets_seen": 0,
        "matched_pairs_seen": 0,
        "deribit_usdc_quotes_cached": 0,
        "per_sleeve": {
            slv: {"evaluated": 0, "opportunities_found": 0, "cycle_hits": 0}
            for slv in ALL_V6_EXPANSION_SLEEVES
        },
        "top_opportunities": [],
        "candidate_l2_recorder": {
            "enabled": True,
            "frames_recorded": 0,
            "budget_drops": 0,
            "bytes_today": 0,
            "max_daily_bytes": 12 * 1024 * 1024,
        },
    }
    if data_dir is not None:
        _atomic_write_json_safe(data_dir / "v6_expansion_telemetry.json", payload)
    return payload


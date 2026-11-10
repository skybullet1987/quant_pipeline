"""
Real Level-2 Execution Simulator, Multi-Leg (2–6 Leg) Complete-Basket Scanner,
General Pairwise Cross-Venue Matcher, and Capital-Efficiency Ranking Engine
(`src/polymarket_research/cross_venue_l2_and_baskets.py`).

Implements Sections 4 & 5 of the Dominus Stage G Production Mandate:
  1. Tick/lot quantized, multi-level L2 execution simulation incorporating partial fills,
     queue-ahead assumptions, market impact, stale-quote rejection, cross-venue wire/speed-bump
     book depletion, cancel/requote unwind bleed, settlement lockup carry, and collateral/FX basis.
  2. Strict separation of `theoretical`, `simulated_executable`, and `observed` execution tiers.
  3. Multi-leg (2–6 leg) exhaustive outcome baskets & Negative-Risk (`NegRisk`) NO-conversion slates
     with strict completeness validation (rejects incomplete partitions and false-positive arbs).
  4. General all-venue pairwise equivalence matching (`Polymarket`, `SX Bet`, `Limitless`,
     `Predict.fun`, `ForecastEx`, `STX Ontario`) + full Capital-Efficiency & Risk Ranking.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import math
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.polymarket_research.cross_venue_riskless_shadow import (
     CrossVenueRuleVerifier,
    DEFAULT_EXTERNAL_GAS_USD,
    DEFAULT_RELAY_BRIDGE_DRAG_BPS,
    DEFAULT_WIRE_LATENCY_MS,
    MIN_NET_PROFIT_USD,
    NormalizedBinaryMarket,
    OrderLevel,
    RuleVerificationResult,
    compute_venue_taker_fee_usd,
    relay_bridge_drag_usd,
    walk_bids_for_unwind,
)

# Conservative stablecoin / FX / yield-token basis haircuts (in bps of notional)
COLLATERAL_BASIS_HAIRCUT_BPS: Dict[str, float] = {
    "USD": 0.0,
    "USDC": 0.0,
    "USDC.E": 1.0,    # Bridged Polygon USDC.e vs native Circle USDC
    "USDT": 3.0,      # BNB/Tether peg dispersion buffer
    "VUSDT": 8.0,     # Venus yield-bearing vUSDT utilization/redemption buffer
    "CAD": 25.0,      # CAD/USD FX conversion & spread buffer on STX Ontario
}


# ---------------------------------------------------------------------------
# 1. Tick / Lot Quantization & Multi-Level L2 Book Simulation
# ---------------------------------------------------------------------------

def quantize_price_ceil(price: float, tick_size: float = 0.001) -> float:
    """Rounds buy limit price UP to valid venue tick (`(0, 1)`) using exact `Decimal` math."""
    tk = Decimal(str(max(0.0001, float(tick_size or 0.001))))
    px = Decimal(str(price))
    ticks = (px / tk).to_integral_value(rounding=ROUND_CEILING)
    out = float(ticks * tk)
    return min(0.9999, max(0.0001, round(out, 6)))


def quantize_shares_floor(shares: float, lot_size: float = 0.01) -> float:
    """Rounds order quantity DOWN to valid venue lot step using exact `Decimal` math."""
    if shares <= 0.0:
        return 0.0
    lt = Decimal(str(max(0.0001, float(lot_size or 0.01))))
    sh = Decimal(str(shares))
    lots = (sh / lt).to_integral_value(rounding=ROUND_FLOOR)
    return max(0.0, round(float(lots * lt), 6))


@dataclass(frozen=True)
class LegSpec:
    market: NormalizedBinaryMarket
    side: str                   # "YES" or "NO"
    execution_style: str = "TAKER"  # "TAKER" | "PASSIVE_MAKER"
    limit_price: Optional[float] = None


@dataclass(frozen=True)
class LegL2Simulation:
    venue: str
    market_slug: str
    side: str
    requested_shares: float
    filled_shares: float
    fill_ratio: float
    fully_filled: bool
    partially_filled: bool
    levels_consumed: int
    top_ask_price: float
    vwap_price: float
    quantized_limit_price: float
    worst_fill_price: float
    slippage_bps: float
    market_impact_usd: float
    gross_cost_usd: float
    fee_usd: float
    quote_age_ms: int
    stale_rejected: bool
    available_book_shares: float
    available_book_usd: float


def simulate_leg_l2_fill(
    leg: LegSpec,
    requested_shares: float,
    *,
    now_ms: Optional[int] = None,
    max_quote_age_ms: int = 45_000,
    top_level_depletion_frac: float = 0.0,
    queue_ahead_fraction: float = 0.50,
    observed_trade_through_shares: Optional[float] = None,
) -> LegL2Simulation:
    """
    Simulates multi-level L2 execution on a single leg with:
      - Stale-quote rejection (`quote_age_ms > max_quote_age_ms` when `quote_ts_ms > 0`)
      - Suspended / expired market rejection
      - Tick & lot quantization
      - Adverse top-of-book liquidity depletion during wire latency (`top_level_depletion_frac`)
      - Partial-fill tracking when book liquidity < `requested_shares`
      - Queue-ahead FIFO survival for `PASSIVE_MAKER` orders.
    """
    mkt = leg.market
    cur_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    age_ms = max(0, cur_ms - int(mkt.quote_ts_ms)) if mkt.quote_ts_ms > 0 else 0
    stale = bool(mkt.quote_ts_ms > 0 and age_ms > max_quote_age_ms)

    q_shares = quantize_shares_floor(requested_shares, mkt.lot_size)
    if stale or mkt.suspended or mkt.expired or q_shares + 1e-9 < mkt.min_shares:
        return LegL2Simulation(
            venue=mkt.venue,
            market_slug=mkt.slug,
            side=leg.side,
            requested_shares=requested_shares,
            filled_shares=0.0,
            fill_ratio=0.0,
            fully_filled=False,
            partially_filled=False,
            levels_consumed=0,
            top_ask_price=1.0,
            vwap_price=1.0,
            quantized_limit_price=1.0,
            worst_fill_price=1.0,
            slippage_bps=0.0,
            market_impact_usd=0.0,
            gross_cost_usd=0.0,
            fee_usd=0.0,
            quote_age_ms=age_ms,
            stale_rejected=stale,
            available_book_shares=0.0,
            available_book_usd=0.0,
        )

    asks = mkt.yes_asks if leg.side.upper() == "YES" else mkt.no_asks
    bids = mkt.yes_bids if leg.side.upper() == "YES" else mkt.no_bids
    clean_asks = sorted(
        [lvl for lvl in asks if 0.0001 < lvl.price < 0.9999 and lvl.size > 1e-6],
        key=lambda x: x.price,
    )
    avail_sh = sum(x.size for x in clean_asks)
    avail_usd = sum(x.price * x.size for x in clean_asks)

    if leg.execution_style.upper() == "PASSIVE_MAKER":
        best_bid = bids[0].price if bids else (clean_asks[0].price - mkt.tick_size if clean_asks else 0.50)
        best_bid_sz = bids[0].size if bids else mkt.min_shares
        raw_px = leg.limit_price if leg.limit_price is not None else min(
            (clean_asks[0].price - mkt.tick_size) if clean_asks else 0.99,
            best_bid + mkt.tick_size,
        )
        q_px = quantize_price_ceil(raw_px, mkt.tick_size)
        queue_ahead = max(0.0, float(queue_ahead_fraction)) * best_bid_sz if abs(q_px - best_bid) < 1e-6 else 0.0
        flow = float(observed_trade_through_shares) if observed_trade_through_shares is not None else 0.0
        fillable = max(0.0, min(q_shares, flow - queue_ahead))
        fillable = quantize_shares_floor(fillable, mkt.lot_size)
        cost = fillable * q_px
        return LegL2Simulation(
            venue=mkt.venue,
            market_slug=mkt.slug,
            side=leg.side,
            requested_shares=q_shares,
            filled_shares=fillable,
            fill_ratio=(fillable / q_shares) if q_shares > 0 else 0.0,
            fully_filled=abs(fillable - q_shares) <= 1e-6 and q_shares > 0,
            partially_filled=(0.0 < fillable < q_shares - 1e-6),
            levels_consumed=1 if fillable > 0 else 0,
            top_ask_price=clean_asks[0].price if clean_asks else q_px,
            vwap_price=q_px,
            quantized_limit_price=q_px,
            worst_fill_price=q_px,
            slippage_bps=0.0,
            market_impact_usd=0.0,
            gross_cost_usd=round(cost, 6),
            fee_usd=0.0,  # Passive maker fee = 0% across Polymarket/Limitless/Predict.fun/SX Bet
            quote_age_ms=age_ms,
            stale_rejected=False,
            available_book_shares=round(avail_sh, 4),
            available_book_usd=round(avail_usd, 4),
        )

    if not clean_asks:
        return LegL2Simulation(
            venue=mkt.venue,
            market_slug=mkt.slug,
            side=leg.side,
            requested_shares=q_shares,
            filled_shares=0.0,
            fill_ratio=0.0,
            fully_filled=False,
            partially_filled=False,
            levels_consumed=0,
            top_ask_price=1.0,
            vwap_price=1.0,
            quantized_limit_price=1.0,
            worst_fill_price=1.0,
            slippage_bps=0.0,
            market_impact_usd=0.0,
            gross_cost_usd=0.0,
            fee_usd=0.0,
            quote_age_ms=age_ms,
            stale_rejected=False,
            available_book_shares=0.0,
            available_book_usd=0.0,
        )

    # Apply adverse top-of-book depletion during cross-venue latency flight
    depl = min(0.95, max(0.0, float(top_level_depletion_frac)))
    effective_levels: List[OrderLevel] = []
    for idx, lvl in enumerate(clean_asks):
        factor = (1.0 - depl) if idx == 0 else (1.0 - 0.35 * depl if idx == 1 else 1.0)
        adj_sz = lvl.size * max(0.0, factor)
        if adj_sz > 1e-6:
            effective_levels.append(OrderLevel(quantize_price_ceil(lvl.price, mkt.tick_size), adj_sz))

    top_px = clean_asks[0].price
    max_limit = quantize_price_ceil(leg.limit_price, mkt.tick_size) if leg.limit_price is not None else 0.9999
    rem = q_shares
    cost = 0.0
    fees = 0.0
    worst = top_px
    levels_used = 0

    for lvl in effective_levels:
        if lvl.price > max_limit + 1e-9:
            break
        take = min(rem, lvl.size)
        if take <= 1e-7:
            continue
        levels_used += 1
        cost += take * lvl.price
        fees += compute_venue_taker_fee_usd(mkt, take, lvl.price)
        worst = lvl.price
        rem -= take
        if rem <= 1e-7:
            break

    filled_raw = max(0.0, q_shares - max(0.0, rem))
    filled = quantize_shares_floor(filled_raw, mkt.lot_size)
    if filled < filled_raw and filled_raw > 0:
        scale = filled / filled_raw
        cost *= scale
        fees *= scale

    vwap = (cost / filled) if filled > 0 else 1.0
    impact_usd = max(0.0, (vwap - top_px) * filled)
    slip_bps = max(0.0, (vwap - top_px) / max(top_px, 0.01) * 10_000.0) if filled > 0 else 0.0
    full = abs(filled - q_shares) <= 1e-6 and q_shares > 0
    partial = 0.0 < filled < q_shares - 1e-6

    return LegL2Simulation(
        venue=mkt.venue,
        market_slug=mkt.slug,
        side=leg.side,
        requested_shares=q_shares,
        filled_shares=filled,
        fill_ratio=round((filled / q_shares) if q_shares > 0 else 0.0, 6),
        fully_filled=full,
        partially_filled=partial,
        levels_consumed=levels_used,
        top_ask_price=round(top_px, 6),
        vwap_price=round(vwap, 6),
        quantized_limit_price=round(quantize_price_ceil(worst, mkt.tick_size), 6),
        worst_fill_price=round(worst, 6),
        slippage_bps=round(slip_bps, 2),
        market_impact_usd=round(impact_usd, 6),
        gross_cost_usd=round(cost, 6),
        fee_usd=round(fees, 6),
        quote_age_ms=age_ms,
        stale_rejected=False,
        available_book_shares=round(avail_sh, 4),
        available_book_usd=round(avail_usd, 4),
    )


# ---------------------------------------------------------------------------
# 2. Three-Tier Basket Simulation & Capital-Efficiency Ranking
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TheoreticalEdgeTier:
    payout_per_unit_usd: float
    top_of_book_unit_cost_usd: float
    gross_theoretical_edge_usd: float
    gross_theoretical_edge_bps: float
    fee_adjusted_l1_edge_usd: float


@dataclass(frozen=True)
class SimulatedExecutableTier:
    executable: bool
    status: str
    leg_simulations: Tuple[LegL2Simulation, ...]
    hedged_shares: float
    unhedged_excess_shares: float
    gross_cost_usd: float
    fees_usd: float
    slippage_and_impact_usd: float
    gas_usd: float
    bridge_drag_usd: float
    settlement_carry_drag_usd: float
    collateral_basis_haircut_usd: float
    cancel_requote_unwind_bleed_usd: float
    guaranteed_payout_usd: float
    net_executable_edge_usd: float
    net_executable_edge_bps: float


@dataclass(frozen=True)
class ObservedExecutionTier:
    observation_status: str   # "OBSERVED_LIVE_POST_DELAY" | "PENDING_LIVE_OBSERVATION" | "SYNTHETIC_OFFLINE_REPLAY"
    live_verified: bool
    survived_post_delay: Optional[bool]
    observed_locked_shares: float
    observed_unwind_bleed_usd: float
    observed_net_pnl_usd: Optional[float]


@dataclass(frozen=True)
class CapitalEfficiencyProfile:
    gross_theoretical_edge_usd: float
    gross_theoretical_edge_bps: float
    fees_usd: float
    slippage_usd: float
    available_executable_shares: float
    capital_requirement_usd: float
    lockup_duration_hours: float
    net_expected_edge_usd: float
    net_expected_edge_bps: float
    rodc_pct: float
    annualized_return_pct: Optional[float]    # None if lockup < 1.0h so ultra-short clips are not distorted
    execution_risk_score: float               # [0.0, 1.0]
    settlement_basis_risk_score: float        # [0.0, 1.0]
    risk_classification: str                  # Never "ZERO_RISK" pre-execution unless single-tx atomic
    efficiency_rank_score: float


@dataclass(frozen=True)
class ThreeTierBasketEvaluation:
    basket_id: str
    basket_type: str                          # "COMPLETE_SET_2LEG" | "CROSS_VENUE_2LEG" | "MULTI_LEG_YES_PARTITION" | "NEGRISK_NO_CONVERSION"
    leg_count: int
    venues: Tuple[str, ...]
    theoretical: TheoreticalEdgeTier
    simulated_executable: SimulatedExecutableTier
    observed: ObservedExecutionTier
    capital_efficiency: CapitalEfficiencyProfile


class Level2ExecutionSimulator:
    """
    Order-book-aware multi-leg execution simulator producing strictly separated
    `theoretical`, `simulated_executable`, and `observed` results.
    """

    def __init__(
        self,
        *,
        wire_latency_ms: Optional[Mapping[str, float]] = None,
        bridge_drag_bps: float = DEFAULT_RELAY_BRIDGE_DRAG_BPS,
        annual_funding_cost_apy: float = 0.05,
        max_quote_age_ms: int = 45_000,
        latency_depletion_rate_per_sec: float = 0.18,
    ) -> None:
        self.wire_latency_ms: Dict[str, float] = dict(DEFAULT_WIRE_LATENCY_MS)
        self.wire_latency_ms.setdefault("forecastex", 65.0)
        self.wire_latency_ms.setdefault("stx_ontario", 35.0)
        if wire_latency_ms:
            for k, v in wire_latency_ms.items():
                self.wire_latency_ms[k] = float(v)
        self.bridge_drag_bps = float(bridge_drag_bps)
        self.annual_funding_cost_apy = max(0.0, float(annual_funding_cost_apy))
        self.max_quote_age_ms = max(1_000, int(max_quote_age_ms))
        self.latency_depletion_rate_per_sec = max(0.0, float(latency_depletion_rate_per_sec))

    def evaluate_basket(
        self,
        *,
        basket_id: str,
        basket_type: str,
        legs: Sequence[LegSpec],
        target_notional_usd: float,
        unit_payout_usd: float = 1.0,
        post_delay_legs: Optional[Sequence[Optional[NormalizedBinaryMarket]]] = None,
        now_ms: Optional[int] = None,
        queue_ahead_fraction: float = 0.50,
        observed_trade_through_shares: Optional[float] = None,
    ) -> ThreeTierBasketEvaluation:
        cur_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        cur_s = cur_ms / 1000.0
        n_legs = len(legs)
        venues = tuple(lg.market.venue for lg in legs)
        distinct_venues = set(venues)

        # --- TIER 1: Theoretical Top-of-Book ---
        l1_prices: List[float] = []
        for lg in legs:
            asks = lg.market.yes_asks if lg.side.upper() == "YES" else lg.market.no_asks
            px = lg.limit_price if lg.limit_price is not None else (asks[0].price if asks else 1.0)
            l1_prices.append(px)
        l1_unit_cost = sum(l1_prices)
        min_sh_floor = max(lg.market.min_shares for lg in legs) if legs else 5.0
        est_shares = max(min_sh_floor, math.floor(float(target_notional_usd) / max(l1_unit_cost, 0.10)))
        l1_fees = sum(
            0.0
            if lg.execution_style.upper() == "PASSIVE_MAKER"
            else compute_venue_taker_fee_usd(lg.market, est_shares, px)
            for lg, px in zip(legs, l1_prices)
        )
        gross_theo_usd = (unit_payout_usd - l1_unit_cost) * est_shares
        gross_theo_bps = ((unit_payout_usd - l1_unit_cost) / max(l1_unit_cost, 1e-6)) * 10_000.0
        theoretical = TheoreticalEdgeTier(
            payout_per_unit_usd=round(unit_payout_usd, 6),
            top_of_book_unit_cost_usd=round(l1_unit_cost, 6),
            gross_theoretical_edge_usd=round(gross_theo_usd, 6),
            gross_theoretical_edge_bps=round(gross_theo_bps, 2),
            fee_adjusted_l1_edge_usd=round(gross_theo_usd - l1_fees, 6),
        )

        # --- TIER 2: Simulated Executable L2 ---
        leg_sims: List[LegL2Simulation] = []
        max_leg_delay_ms = 0.0
        for lg in legs:
            leg_delay = self.wire_latency_ms.get(lg.market.venue, 110.0) + (
                0.0 if lg.execution_style.upper() == "PASSIVE_MAKER" else lg.market.taker_delay_ms
            )
            max_leg_delay_ms = max(max_leg_delay_ms, leg_delay)
            depl = min(0.60, self.latency_depletion_rate_per_sec * (leg_delay / 1000.0))
            sim = simulate_leg_l2_fill(
                lg,
                est_shares,
                now_ms=cur_ms,
                max_quote_age_ms=self.max_quote_age_ms,
                top_level_depletion_frac=depl,
                queue_ahead_fraction=queue_ahead_fraction,
                observed_trade_through_shares=observed_trade_through_shares,
            )
            leg_sims.append(sim)

        any_stale = any(s.stale_rejected for s in leg_sims)
        hedged_sh = min((s.filled_shares for s in leg_sims), default=0.0)
        max_filled_sh = max((s.filled_shares for s in leg_sims), default=0.0)
        unhedged_excess = max(0.0, max_filled_sh - hedged_sh)

        # Calculate cancel/requote unwind bleed for any excess filled shares on faster legs when a slower leg partially fills or fails
        unwind_bleed = 0.0
        if unhedged_excess > 1e-6:
            for lg, sim in zip(legs, leg_sims):
                excess_i = max(0.0, sim.filled_shares - hedged_sh)
                if excess_i > 1e-6:
                    bids = lg.market.yes_bids if lg.side.upper() == "YES" else lg.market.no_bids
                    proceeds, _ = walk_bids_for_unwind(bids, excess_i, lg.market)
                    paid = excess_i * sim.vwap_price + (sim.fee_usd * (excess_i / max(sim.filled_shares, 1e-9)))
                    unwind_bleed += max(0.0, paid - proceeds)

        # Pro-rate hedged portion of costs & fees
        hedged_gross_cost = 0.0
        hedged_fees = 0.0
        slippage_usd = 0.0
        for sim in leg_sims:
            if hedged_sh > 0 and sim.filled_shares > 0:
                frac = hedged_sh / sim.filled_shares
                hedged_gross_cost += sim.gross_cost_usd * frac
                hedged_fees += sim.fee_usd * frac
                slippage_usd += sim.market_impact_usd * frac

        gas_usd = sum(DEFAULT_EXTERNAL_GAS_USD.get(v, 0.005) for v in distinct_venues)
        bridge_usd = (
            relay_bridge_drag_usd(hedged_gross_cost, self.bridge_drag_bps) * max(1, len(distinct_venues) - 1)
            if len(distinct_venues) > 1
            else 0.0
        )

        # Lockup duration & carry drag + collateral basis haircut
        lockup_hours = 2.0
        end_candidates = [lg.market.end_ts for lg in legs if lg.market.end_ts]
        max_settle_delay = max((lg.market.settlement_delay_hours for lg in legs), default=2.0)
        if end_candidates:
            horizon_h = max(0.0, (max(end_candidates) - cur_s) / 3600.0)
            lockup_hours = max(0.0833, horizon_h + max_settle_delay)
        else:
            lockup_hours = max(1.0, max_settle_delay)

        carry_drag = hedged_gross_cost * self.annual_funding_cost_apy * (lockup_hours / 8760.0)
        basis_haircut = 0.0
        for lg, sim in zip(legs, leg_sims):
            if hedged_sh > 0 and sim.filled_shares > 0:
                col_key = (lg.market.collateral_asset or "USDC").upper()
                bps = COLLATERAL_BASIS_HAIRCUT_BPS.get(col_key, 5.0)
                leg_notional = (sim.gross_cost_usd / sim.filled_shares) * hedged_sh
                basis_haircut += leg_notional * (bps / 10_000.0)

        guaranteed_payout = hedged_sh * unit_payout_usd
        total_friction = (
            hedged_fees + gas_usd + bridge_usd + carry_drag + basis_haircut + unwind_bleed
        )
        net_exec_edge = guaranteed_payout - hedged_gross_cost - total_friction
        cap_req = hedged_gross_cost + hedged_fees + gas_usd
        net_exec_bps = (net_exec_edge / max(cap_req, 1e-6)) * 10_000.0 if hedged_sh > 0 else -10_000.0

        if any_stale:
            sim_status = "REJECTED_STALE_QUOTE"
            exec_ok = False
        elif hedged_sh + 1e-9 < min_sh_floor:
            sim_status = "REJECTED_INSUFFICIENT_L2_DEPTH"
            exec_ok = False
        elif unhedged_excess > 1e-6 and net_exec_edge < MIN_NET_PROFIT_USD:
            sim_status = "REJECTED_PARTIAL_FILL_UNWIND_BLEED"
            exec_ok = False
        elif net_exec_edge < MIN_NET_PROFIT_USD:
            sim_status = "REJECTED_NEGATIVE_NET_EXECUTABLE_EDGE"
            exec_ok = False
        else:
            sim_status = "EXECUTABLE_L2_VERIFIED"
            exec_ok = True

        sim_tier = SimulatedExecutableTier(
            executable=exec_ok,
            status=sim_status,
            leg_simulations=tuple(leg_sims),
            hedged_shares=round(hedged_sh, 6),
            unhedged_excess_shares=round(unhedged_excess, 6),
            gross_cost_usd=round(hedged_gross_cost, 6),
            fees_usd=round(hedged_fees, 6),
            slippage_and_impact_usd=round(slippage_usd, 6),
            gas_usd=round(gas_usd, 6),
            bridge_drag_usd=round(bridge_usd, 6),
            settlement_carry_drag_usd=round(carry_drag, 6),
            collateral_basis_haircut_usd=round(basis_haircut, 6),
            cancel_requote_unwind_bleed_usd=round(unwind_bleed, 6),
            guaranteed_payout_usd=round(guaranteed_payout, 6),
            net_executable_edge_usd=round(net_exec_edge, 6),
            net_executable_edge_bps=round(net_exec_bps, 2),
        )

        # --- TIER 3: Actually Observed Post-Latency Result ---
        all_live_origin = all(lg.market.data_origin == "LIVE_VERIFIED" for lg in legs)
        if post_delay_legs is None:
            obs_tier = ObservedExecutionTier(
                observation_status="PENDING_LIVE_OBSERVATION" if all_live_origin else "SYNTHETIC_OFFLINE_REPLAY",
                live_verified=False,
                survived_post_delay=None,
                observed_locked_shares=0.0,
                observed_unwind_bleed_usd=0.0,
                observed_net_pnl_usd=None,
            )
        else:
            if any(pm is None for pm in post_delay_legs):
                obs_tier = ObservedExecutionTier(
                    observation_status="OBSERVED_LIVE_POST_DELAY" if all_live_origin else "SYNTHETIC_OFFLINE_REPLAY",
                    live_verified=all_live_origin,
                    survived_post_delay=False,
                    observed_locked_shares=0.0,
                    observed_unwind_bleed_usd=0.0,
                    observed_net_pnl_usd=0.0,
                )
            else:
                post_sims = [
                    simulate_leg_l2_fill(
                        LegSpec(market=pm, side=lg.side, execution_style=lg.execution_style, limit_price=lg.limit_price),  # type: ignore[arg-type]
                        est_shares,
                        now_ms=cur_ms,
                        max_quote_age_ms=self.max_quote_age_ms * 2,
                        top_level_depletion_frac=0.0,
                        queue_ahead_fraction=queue_ahead_fraction,
                        observed_trade_through_shares=observed_trade_through_shares,
                    )
                    for lg, pm in zip(legs, post_delay_legs)
                ]
                obs_hedged = min((ps.filled_shares for ps in post_sims), default=0.0)
                obs_max = max((ps.filled_shares for ps in post_sims), default=0.0)
                obs_bleed = 0.0
                if obs_max - obs_hedged > 1e-6:
                    for lg, pm, ps in zip(legs, post_delay_legs, post_sims):
                        ex = max(0.0, ps.filled_shares - obs_hedged)
                        if ex > 1e-6 and pm is not None:
                            bids_p = pm.yes_bids if lg.side.upper() == "YES" else pm.no_bids
                            proc_p, _ = walk_bids_for_unwind(bids_p, ex, pm)
                            obs_bleed += max(0.0, ex * ps.vwap_price - proc_p)
                obs_cost = sum(
                    (ps.gross_cost_usd * (obs_hedged / ps.filled_shares)) if ps.filled_shares > 0 else 0.0
                    for ps in post_sims
                )
                obs_fees = sum(
                    (ps.fee_usd * (obs_hedged / ps.filled_shares)) if ps.filled_shares > 0 else 0.0
                    for ps in post_sims
                )
                obs_bridge = (
                    relay_bridge_drag_usd(obs_cost, self.bridge_drag_bps) * max(1, len(distinct_venues) - 1)
                    if len(distinct_venues) > 1 and obs_hedged > 0
                    else 0.0
                )
                obs_net = (obs_hedged * unit_payout_usd) - (obs_cost + obs_fees + (gas_usd if obs_hedged > 0 else 0.0) + obs_bridge) - obs_bleed
                obs_live = all_live_origin and all(pm is not None and pm.data_origin == "LIVE_VERIFIED" for pm in post_delay_legs)
                obs_tier = ObservedExecutionTier(
                    observation_status="OBSERVED_LIVE_POST_DELAY" if obs_live else "SYNTHETIC_OFFLINE_REPLAY",
                    live_verified=obs_live,
                    survived_post_delay=(obs_hedged >= min_sh_floor and obs_net > 0.0),
                    observed_locked_shares=round(obs_hedged, 6),
                    observed_unwind_bleed_usd=round(obs_bleed, 6),
                    observed_net_pnl_usd=round(obs_net, 6),
                )

        # --- Capital-Efficiency & Risk Ranking ---
        avail_max_sh = min((s.available_book_shares for s in leg_sims), default=0.0)
        rodc_pct = (net_exec_edge / cap_req * 100.0) if (cap_req > 1e-6 and hedged_sh > 0) else 0.0
        ann_pct: Optional[float] = (
            round(rodc_pct * (8760.0 / lockup_hours), 2) if (lockup_hours >= 1.0 and exec_ok) else None
        )

        # Execution risk [0, 1]: multi-leg complexity + speed-bump/wire delay + thin book ratio
        depth_ratio = (avail_max_sh / max(est_shares, 1.0)) if est_shares > 0 else 0.0
        exec_risk = min(
            1.0,
            0.08 * max(0, n_legs - 1)
            + min(0.45, max_leg_delay_ms / 1000.0)
            + (0.25 if depth_ratio < 2.0 else (0.10 if depth_ratio < 4.0 else 0.02))
            + (0.12 if len(distinct_venues) > 1 else 0.0),
        )
        # Settlement/basis risk [0, 1]: cross-oracle, heterogeneous collaterals, cancel-rule differences, clarifications
        oracles = {lg.market.oracle_family for lg in legs if lg.market.oracle_family}
        collats = {(lg.market.collateral_asset or "USDC").upper() for lg in legs}
        cancels = {lg.market.cancel_rule for lg in legs}
        clarifs = sum(lg.market.clarification_count for lg in legs)
        settle_risk = min(
            1.0,
            (0.20 if len(oracles) > 1 else 0.02)
            + (0.08 * max(0, len(collats) - 1))
            + (0.10 if len(cancels) > 1 else 0.0)
            + min(0.30, 0.10 * clarifs),
        )

        is_single_venue_atomic = len(distinct_venues) == 1 and all(lg.market.supports_split_merge for lg in legs)
        risk_cls = (
            "ATOMIC_SINGLE_CHAIN_COMPLETE_SET_POST_FILL"
            if is_single_venue_atomic and n_legs == 2
            else "PAYOFF_BOUNDED_SUBJECT_TO_EXECUTION_AND_SETTLEMENT_BASIS"
        )
        # Risk-adjusted capital efficiency score (penalizes lockup duration, execution risk, and basis risk)
        hourly_rodc_bps = (net_exec_bps / max(lockup_hours, 0.25)) if exec_ok else -10_000.0
        rank_score = hourly_rodc_bps * max(0.05, 1.0 - 0.5 * exec_risk - 0.5 * settle_risk)

        cap_profile = CapitalEfficiencyProfile(
            gross_theoretical_edge_usd=round(gross_theo_usd, 6),
            gross_theoretical_edge_bps=round(gross_theo_bps, 2),
            fees_usd=round(hedged_fees, 6),
            slippage_usd=round(slippage_usd, 6),
            available_executable_shares=round(avail_max_sh, 4),
            capital_requirement_usd=round(cap_req, 4),
            lockup_duration_hours=round(lockup_hours, 4),
            net_expected_edge_usd=round(net_exec_edge, 6),
            net_expected_edge_bps=round(net_exec_bps, 2),
            rodc_pct=round(rodc_pct, 4),
            annualized_return_pct=ann_pct,
            execution_risk_score=round(exec_risk, 4),
            settlement_basis_risk_score=round(settle_risk, 4),
            risk_classification=risk_cls,
            efficiency_rank_score=round(rank_score, 4),
        )

        return ThreeTierBasketEvaluation(
            basket_id=basket_id,
            basket_type=basket_type,
            leg_count=n_legs,
            venues=venues,
            theoretical=theoretical,
            simulated_executable=sim_tier,
            observed=obs_tier,
            capital_efficiency=cap_profile,
        )


# ---------------------------------------------------------------------------
# 3. General All-Venue Pairwise Matcher & 2–6 Leg Multi-Outcome Basket Engine
# ---------------------------------------------------------------------------

class MultiVenueArbitrageAnalyzer:
    """
    Extends opportunity detection across all 6 venues:
      - General `Venue_i <-> Venue_j` pairwise matching (including `SX Bet <-> STX Ontario`,
        `Limitless <-> Predict.fun`, `Polymarket <-> ForecastEx`, etc.)
      - 2–6 leg exhaustive partition complete baskets (`MULTI_LEG_YES_PARTITION`)
      - 3–6 leg `NegRisk` `NO`-conversion slates (`NEGRISK_NO_CONVERSION`)
      - Capital-efficiency & risk ranking.
    """

    def __init__(
        self,
        *,
        simulator: Optional[Level2ExecutionSimulator] = None,
        rule_verifier: Optional[CrossVenueRuleVerifier] = None,
        clip_notional_usd: float = 25.0,
    ) -> None:
        self.simulator = simulator or Level2ExecutionSimulator()
        self.verifier = rule_verifier or CrossVenueRuleVerifier()
        self.clip_notional_usd = max(5.0, float(clip_notional_usd))

    @staticmethod
    def pair_all_venues(
        markets: Sequence[NormalizedBinaryMarket],
    ) -> List[Tuple[NormalizedBinaryMarket, NormalizedBinaryMarket]]:
        """
        Deterministically pairs economically candidate markets across ANY two distinct venues
        by exact `condition_id`, `external_slug`, `(rules_hash, canonical_title)` parity,
        canonical sports `asset` matchup, or `(asset, horizon, end_ts)` crypto signature.
        """
        def _canonical_title_key(text: str) -> str:
            cleaned = re.sub(r"[^a-z0-9.%$]+", " ", (text or "").lower())
            return re.sub(r"\s+", " ", cleaned).strip()

        by_slug: Dict[str, List[NormalizedBinaryMarket]] = {}
        by_cond: Dict[str, List[NormalizedBinaryMarket]] = {}
        by_rules_and_title: Dict[Tuple[str, str], List[NormalizedBinaryMarket]] = {}
        by_sports: Dict[str, List[NormalizedBinaryMarket]] = {}
        by_sports_teams: Dict[str, List[NormalizedBinaryMarket]] = {}
        by_crypto: Dict[Tuple[str, str, int], List[NormalizedBinaryMarket]] = {}

        for m in markets:
            if m.suspended or m.expired:
                continue
            if m.slug:
                by_slug.setdefault(m.slug, []).append(m)
            if m.condition_id:
                by_cond.setdefault(m.condition_id.lower(), []).append(m)
            t_key = _canonical_title_key(m.title)
            if m.rules_hash and t_key:
                by_rules_and_title.setdefault((m.rules_hash, t_key), []).append(m)
            if m.category == "sports" and m.asset:
                by_sports.setdefault(m.asset, []).append(m)
                bare_teams = m.asset.split("@", 1)[0]
                if bare_teams:
                    by_sports_teams.setdefault(bare_teams, []).append(m)
            if m.category == "crypto" and m.asset and m.horizon and m.end_ts:
                by_crypto.setdefault((m.asset, m.horizon, int(m.end_ts)), []).append(m)

        seen_pairs: set[Tuple[str, str]] = set()
        out_pairs: List[Tuple[NormalizedBinaryMarket, NormalizedBinaryMarket]] = []

        def _add_pair(a: NormalizedBinaryMarket, b: NormalizedBinaryMarket) -> None:
            if a.venue == b.venue:
                return
            # Enforce 1-to-1 cryptographic conditionId link whenever declared on multi-strike series
            if a.venue == "polymarket" and a.condition_id and b.polymarket_condition_ids:
                if a.condition_id.lower() not in {c.lower() for c in b.polymarket_condition_ids}:
                    return
            if b.venue == "polymarket" and b.condition_id and a.polymarket_condition_ids:
                if b.condition_id.lower() not in {c.lower() for c in a.polymarket_condition_ids}:
                    return
            if a.polymarket_condition_ids and b.polymarket_condition_ids:
                if not ({c.lower() for c in a.polymarket_condition_ids} & {c.lower() for c in b.polymarket_condition_ids}):
                    return
            ka = f"{a.venue}:{a.slug}"
            kb = f"{b.venue}:{b.slug}"
            # Put Polymarket first when present for deterministic orientation
            if b.venue == "polymarket" and a.venue != "polymarket":
                a, b = b, a
                ka, kb = kb, ka
            elif a.venue != "polymarket" and b.venue != "polymarket" and ka > kb:
                a, b = b, a
                ka, kb = kb, ka
            pair_k = (ka, kb)
            if pair_k not in seen_pairs:
                seen_pairs.add(pair_k)
                out_pairs.append((a, b))

        for m in markets:
            if m.suspended or m.expired:
                continue
            if m.external_slug and m.external_slug in by_slug:
                for other in by_slug[m.external_slug]:
                    _add_pair(m, other)
            m_ts = re.search(r"-(\d{10})$", m.slug)
            if m_ts and m.asset and m.horizon in ("5m", "15m"):
                p_slug = f"{m.asset.lower()}-updown-{m.horizon}-{m_ts.group(1)}"
                for other in by_slug.get(p_slug, ()):
                    _add_pair(m, other)
            for cid in m.polymarket_condition_ids:
                for other in by_cond.get(cid.lower(), ()):
                    _add_pair(m, other)
            t_key = _canonical_title_key(m.title)
            if m.rules_hash and t_key:
                for other in by_rules_and_title.get((m.rules_hash, t_key), ()):
                    _add_pair(m, other)
            if m.category == "sports" and m.asset:
                for other in by_sports.get(m.asset, ()):
                    _add_pair(m, other)
                bare_teams = m.asset.split("@", 1)[0]
                for other in by_sports_teams.get(bare_teams, ()):
                    if not m.end_ts or not other.end_ts or abs(int(m.end_ts) - int(other.end_ts)) <= 36 * 3600:
                        _add_pair(m, other)
            if m.category == "crypto" and m.asset and m.horizon and m.end_ts:
                for other in by_crypto.get((m.asset, m.horizon, int(m.end_ts)), ()):
                    _add_pair(m, other)

        return out_pairs

    def scan_multi_leg_complete_baskets(
        self,
        markets: Sequence[NormalizedBinaryMarket],
        *,
        now_ms: Optional[int] = None,
    ) -> Tuple[List[ThreeTierBasketEvaluation], List[Dict[str, Any]]]:
        """
        Scans `2 <= k <= 6` leg exhaustive partition slates (`MULTI_LEG_YES_PARTITION` and
        `NEGRISK_NO_CONVERSION`).

        Strict Anti-False-Positive Completeness Rules:
          1. `partition_group_id` must be non-empty.
          2. `2 <= partition_expected_legs <= 6` must be explicitly declared and satisfied
             (`len(distinct_outcomes) == partition_expected_legs`). Incomplete partitions
             (e.g. missing Draw or "Other" bracket) are HARD-REJECTED!
          3. Every leg in the partition must share identical `oracle_family` and matching
             `end_ts` cutoff (`<= 60s` skew) with `0` UMA clarification drift.
        """
        groups: Dict[str, List[NormalizedBinaryMarket]] = {}
        for m in markets:
            if m.partition_group_id and not m.suspended and not m.expired:
                groups.setdefault(m.partition_group_id, []).append(m)

        evaluations: List[ThreeTierBasketEvaluation] = []
        rejections: List[Dict[str, Any]] = []

        for gid, grp in groups.items():
            # Deduplicate per canonical partition_label choosing the lowest YES ask across venues!
            by_label_best_yes: Dict[str, NormalizedBinaryMarket] = {}
            by_label_best_no: Dict[str, NormalizedBinaryMarket] = {}
            expected_legs_set = {m.partition_expected_legs for m in grp if m.partition_expected_legs > 0}

            if len(expected_legs_set) != 1:
                rejections.append({"group_id": gid, "reason": "AMBIGUOUS_OR_UNDECLARED_PARTITION_CARDINALITY"})
                continue
            expected_k = next(iter(expected_legs_set))
            if not (2 <= expected_k <= 6):
                rejections.append({"group_id": gid, "reason": f"UNSUPPORTED_LEG_COUNT({expected_k})"})
                continue

            oracles = {m.oracle_family for m in grp if m.oracle_family}
            if len(oracles) != 1:
                rejections.append({"group_id": gid, "reason": "PARTITION_ORACLE_MISMATCH"})
                continue

            end_times = [int(m.end_ts) for m in grp if m.end_ts]
            if end_times and (max(end_times) - min(end_times)) > 60:
                rejections.append({"group_id": gid, "reason": "PARTITION_CUTOFF_TIMESTAMP_SKEW"})
                continue

            if any(m.clarification_count > 0 for m in grp):
                rejections.append({"group_id": gid, "reason": "PARTITION_CLARIFICATION_DRIFT"})
                continue

            for m in grp:
                lbl = (m.partition_label or m.slug).strip().lower()
                if not lbl:
                    continue
                if m.yes_asks:
                    cur_y = by_label_best_yes.get(lbl)
                    if cur_y is None or m.yes_asks[0].price < cur_y.yes_asks[0].price:
                        by_label_best_yes[lbl] = m
                if m.no_asks and m.neg_risk:
                    cur_n = by_label_best_no.get(lbl)
                    if cur_n is None or m.no_asks[0].price < cur_n.no_asks[0].price:
                        by_label_best_no[lbl] = m

            if len(by_label_best_yes) != expected_k:
                rejections.append(
                    {
                        "group_id": gid,
                        "reason": f"INCOMPLETE_OUTCOME_PARTITION(have={len(by_label_best_yes)},expected={expected_k})",
                    }
                )
                continue

            # (A) k-Leg Complete YES Partition (`sum(YES_i) < $1.00`)
            ordered_yes = [by_label_best_yes[k] for k in sorted(by_label_best_yes.keys())]
            yes_l1_sum = sum(m.yes_asks[0].price for m in ordered_yes)
            if yes_l1_sum < 1.0:
                ev_yes = self.simulator.evaluate_basket(
                    basket_id=f"ML_YES::{gid}::{expected_k}L",
                    basket_type="MULTI_LEG_YES_PARTITION",
                    legs=[LegSpec(market=m, side="YES") for m in ordered_yes],
                    target_notional_usd=self.clip_notional_usd,
                    unit_payout_usd=1.0,
                    now_ms=now_ms,
                )
                if ev_yes.simulated_executable.executable:
                    evaluations.append(ev_yes)
                else:
                    rejections.append({"group_id": gid, "reason": ev_yes.simulated_executable.status})

            # (B) k-Leg NegRisk NO-Conversion Basket (`sum(NO_i) < $(k - 1)`, k >= 3)
            if expected_k >= 3 and len(by_label_best_no) == expected_k:
                ordered_no = [by_label_best_no[k] for k in sorted(by_label_best_no.keys())]
                # Require single-venue NegRisk market group for atomic/deterministic NO conversion
                if len({m.venue for m in ordered_no}) == 1:
                    no_l1_sum = sum(m.no_asks[0].price for m in ordered_no)
                    payout_units = float(expected_k - 1)
                    if no_l1_sum < payout_units:
                        ev_no = self.simulator.evaluate_basket(
                            basket_id=f"ML_NEGRISK_NO::{gid}::{expected_k}L",
                            basket_type="NEGRISK_NO_CONVERSION",
                            legs=[LegSpec(market=m, side="NO") for m in ordered_no],
                            target_notional_usd=self.clip_notional_usd * payout_units,
                            unit_payout_usd=payout_units,
                            now_ms=now_ms,
                        )
                        if ev_no.simulated_executable.executable:
                            evaluations.append(ev_no)
                        else:
                            rejections.append({"group_id": gid, "reason": ev_no.simulated_executable.status})

        evaluations.sort(key=lambda e: e.capital_efficiency.efficiency_rank_score, reverse=True)
        return (evaluations, rejections)

    @staticmethod
    def rank_opportunities(
        evaluations: Sequence[ThreeTierBasketEvaluation],
    ) -> List[ThreeTierBasketEvaluation]:
        """Ranks opportunities strictly by risk-adjusted capital efficiency (`efficiency_rank_score`)."""
        return sorted(
            evaluations,
            key=lambda e: (
                1 if e.simulated_executable.executable else 0,
                e.capital_efficiency.efficiency_rank_score,
                e.capital_efficiency.net_expected_edge_usd,
            ),
            reverse=True,
        )

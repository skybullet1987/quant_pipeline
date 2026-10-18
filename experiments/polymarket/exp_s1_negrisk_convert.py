#!/usr/bin/env python3
"""
Experiment S1: Categorical NegRisk convertPositions Arbitrage (exp_s1_negrisk_convert.py)
========================================================================================
Institutional Arbitrage & Valuation Engine for Polymarket NegRisk Categorical Markets.

Mathematical Specification:
  In an N-outcome mutually exclusive NegRisk event (N >= 4 outcomes, e.g. elections, awards):
  Holding a bundle of M distinct NO positions (2 <= |M| <= N) in quantity Q allows calling:
      NegRiskAdapter.convertPositions(marketId, indexSet, Q)   [at 0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296]
  This burns the M * Q NO tokens and mints:
      1. Immediate Risk-Free USDC Cash Collateral: (|M| - 1) * Q
      2. Residual Complementary YES Tokens: Q units of YES_j for every unselected outcome j not in M.

  Arbitrage Condition:
      Sum_{i in M} P_ask(NO_i) < (|M| - 1) + Sum_{j not in M} P_bid(YES_j) - C_fees_gas

  Pure Negative-Cost Condition:
      Sum_{i in M} P_ask(NO_i) < (|M| - 1)
      -> Immediate cash unlocked ALONE exceeds the entire cost of the NO bundle!
      -> The residual YES_j shares (j not in M) have a strictly negative cost basis (free tail lotteries).

Execution & Sizing:
  - Caps order size Q to <= 50% of top-of-book ask depth across all i in M.
  - Simulates batch client.postOrders execution with transit latency.
  - Simulates on-chain NegRiskAdapter.convertPositions calls.
  - Tracks legging failure rates and fallback partial subset conversion (M' < M).
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import math
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import httpx

logger = logging.getLogger("ExpS1NegRisk")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [S1-NEGRISK] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
NEGRISK_ADAPTER_ADDRESS = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
NEGRISK_EXCHANGE_ADDRESS = "0xC5d563A36AE78145C45a50134d48A1215220f80a"

STANDARD_GAS_ESTIMATE_USD = 0.02  # Polygon PoS gas cost
DEFAULT_TAKER_FEE_RATE = 0.00     # Politics / Geopolitics 0.00; Crypto 0.07


# ==============================================================================
# 1. DATA CONTRACTS
# ==============================================================================

@dataclass
class NegRiskOutcome:
    """Represents a single candidate/outcome in an N-way NegRisk event."""
    outcome_index: int
    title: str
    condition_id: str
    yes_token_id: str
    no_token_id: str
    best_bid_yes: float = 0.0
    best_ask_yes: float = 0.0
    depth_bid_yes: float = 0.0
    depth_ask_yes: float = 0.0
    best_bid_no: float = 0.0
    best_ask_no: float = 0.0
    depth_bid_no: float = 0.0
    depth_ask_no: float = 0.0


@dataclass
class NegRiskMarketBundle:
    """Represents a multi-outcome categorical event with negRisk: true."""
    event_id: str
    title: str
    neg_risk_market_id: str
    outcomes: List[NegRiskOutcome]
    category: str = "politics"
    taker_fee_rate: float = DEFAULT_TAKER_FEE_RATE


@dataclass
class SubsetArbitrageOpportunity:
    """Discovered NegRisk subset conversion opportunity."""
    event_id: str
    market_title: str
    subset_indices: List[int]       # M in {0, ..., N-1}
    subset_titles: List[str]
    unselected_indices: List[int]   # j not in M
    unselected_titles: List[str]
    num_legs: int                   # |M|
    sum_no_ask: float               # Sum_{i in M} P_ask(NO_i)
    unlocked_cash_per_share: float  # |M| - 1
    sum_residual_yes_bid: float     # Sum_{j not in M} P_bid(YES_j)
    est_fees_usd: float
    net_edge_per_share: float
    is_pure_negative_cost: bool     # Sum P_ask(NO) < |M| - 1
    max_executable_qty: float       # <= 50% min ask depth
    immediate_cash_profit_usd: float# (|M| - 1) * Q - Cost(NO)
    residual_lottery_shares: Dict[str, float]
    timestamp_mono: float = field(default_factory=time.monotonic)


@dataclass
class ExecutionSimulationResult:
    """Execution telemetry for batch orders + convertPositions on-chain call."""
    opportunity: SubsetArbitrageOpportunity
    submitted_qty: float
    filled_qty: float
    legs_attempted: List[int]
    legs_filled: List[int]
    legs_missed: List[int]
    is_full_bundle_fill: bool
    converted_subset: List[int]
    cash_unlocked_usd: float
    actual_purchase_cost_usd: float
    net_immediate_cash_profit_usd: float
    residual_yes_shares: Dict[str, float]
    residual_yes_mtm_value_usd: float
    legging_failed: bool
    fallback_subset_salvaged: bool
    execution_latency_ms: float
    polygon_tx_hash: str


# ==============================================================================
# 2. CORE NEGRISK CONVERT ARBITRAGE ENGINE
# ==============================================================================

class NegRiskConvertArbitrageEngine:
    """
    Evaluates, sizes, and simulates NegRisk convertPositions arbitrage.
    """

    def __init__(
        self,
        depth_cap_ratio: float = 0.50,
        min_order_notional_usd: float = 5.0,
        estimated_gas_usd: float = STANDARD_GAS_ESTIMATE_USD,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.depth_cap_ratio: float = depth_cap_ratio
        self.min_order_notional: float = min_order_notional_usd
        self.gas_fee: float = estimated_gas_usd
        self._client: Optional[httpx.AsyncClient] = client
        self._owns_client: bool = False

        # Active tracked market bundles
        self.bundles: Dict[str, NegRiskMarketBundle] = {}

        # Telemetry counters
        self.total_bundles_scanned: int = 0
        self.total_evaluations: int = 0
        self.opportunities_found: List[SubsetArbitrageOpportunity] = []
        self.simulated_executions: List[ExecutionSimulationResult] = []

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
            self._owns_client = True
        return self._client

    # --------------------------------------------------------------------------
    # GAMMA API MARKET DISCOVERY
    # --------------------------------------------------------------------------

    async def fetch_active_negrisk_events(
        self,
        min_outcomes: int = 4,
        limit: int = 50,
    ) -> List[NegRiskMarketBundle]:
        """
        Queries Gamma API for all active, open categorical events with negRisk: true.
        Filters for multi-outcome events with N >= min_outcomes (mutually exclusive).
        """
        client = await self._get_client()
        url = f"{GAMMA_API_BASE}/events?active=true&closed=false&limit={limit}"
        logger.info(f"Querying Gamma API for active NegRisk events (min_outcomes={min_outcomes})...")

        discovered: List[NegRiskMarketBundle] = []
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                events_data = resp.json()
                for event in events_data:
                    if not event.get("negRisk", False):
                        continue

                    markets = event.get("markets", [])
                    if len(markets) < min_outcomes:
                        continue

                    event_id = str(event.get("id"))
                    title = event.get("title", f"NegRisk Event {event_id}")
                    category = event.get("category", "politics").lower()

                    outcomes: List[NegRiskOutcome] = []
                    for idx, m in enumerate(markets):
                        clob_tokens = m.get("clobTokenIds", [])
                        if isinstance(clob_tokens, str):
                            try:
                                clob_tokens = json.loads(clob_tokens)
                            except Exception:
                                clob_tokens = []

                        yes_id = clob_tokens[0] if len(clob_tokens) > 0 else f"{m.get('id')}_YES"
                        no_id = clob_tokens[1] if len(clob_tokens) > 1 else f"{m.get('id')}_NO"

                        outcome_title = (
                            m.get("groupItemTitle")
                            or m.get("question")
                            or f"Outcome {idx + 1}"
                        )
                        outcomes.append(
                            NegRiskOutcome(
                                outcome_index=idx,
                                title=outcome_title,
                                condition_id=m.get("conditionId", ""),
                                yes_token_id=yes_id,
                                no_token_id=no_id,
                            )
                        )

                    fee_rate = 0.07 if "crypto" in category else 0.00
                    bundle = NegRiskMarketBundle(
                        event_id=event_id,
                        title=title,
                        neg_risk_market_id=event.get("negRiskMarketID", NEGRISK_ADAPTER_ADDRESS),
                        outcomes=outcomes,
                        category=category,
                        taker_fee_rate=fee_rate,
                    )
                    discovered.append(bundle)
                    self.bundles[event_id] = bundle

        except Exception as e:
            logger.warning(f"Gamma API query encountered issue: {e}")

        self.total_bundles_scanned += len(discovered)
        logger.info(f"Discovered {len(discovered)} active NegRisk multi-outcome events.")
        return discovered

    # --------------------------------------------------------------------------
    # SUBSET ARBITRAGE MATHEMATICAL EVALUATOR
    # --------------------------------------------------------------------------

    def evaluate_bundle_subsets(
        self,
        bundle: NegRiskMarketBundle,
        max_subset_size: Optional[int] = None,
    ) -> List[SubsetArbitrageOpportunity]:
        """
        Evaluates all subsets M in {0, ..., N-1} (2 <= |M| <= N) where:
            Sum_{i in M} P_ask(NO_i) < (|M| - 1) + Sum_{j not in M} P_bid(YES_j) - C_fees_gas

        Identifies 'Pure Negative-Cost' subsets:
            Sum_{i in M} P_ask(NO_i) < |M| - 1
        """
        n = len(bundle.outcomes)
        if n < 2:
            return []

        self.total_evaluations += 1
        opportunities: List[SubsetArbitrageOpportunity] = []

        # Filter out outcomes with missing or invalid book quotes
        valid_outcomes = [
            (i, o) for i, o in enumerate(bundle.outcomes)
            if o.best_ask_no > 0 and o.depth_ask_no > 0
        ]
        if len(valid_outcomes) < 2:
            return []

        limit_k = max_subset_size or n
        # Evaluate subset sizes from 2 up to min(n, limit_k)
        # Note: When N <= 12, we can evaluate full powerset.
        # For large N, we evaluate all pairs, triplets, and the top-K cheapest NO outcomes.
        size_range = range(2, min(len(valid_outcomes) + 1, limit_k + 1))

        for m_size in size_range:
            # If total combinations exceed 2000, sort greedily by cheapest NO ask
            if math.comb(len(valid_outcomes), m_size) > 2000:
                sorted_by_no_ask = sorted(valid_outcomes, key=lambda x: x[1].best_ask_no)
                candidate_combos = [sorted_by_no_ask[:m_size]]
            else:
                candidate_combos = itertools.combinations(valid_outcomes, m_size)

            for combo in candidate_combos:
                m_indices = [idx for idx, _ in combo]
                unselected_indices = [i for i in range(n) if i not in m_indices]

                sum_no_ask = sum(bundle.outcomes[i].best_ask_no for i in m_indices)
                unlocked_cash = float(m_size - 1)

                sum_residual_yes_bid = sum(
                    bundle.outcomes[j].best_bid_yes for j in unselected_indices
                )

                # Fee calculation: taker fee on NO purchases and optional YES sales
                taker_fee = bundle.taker_fee_rate * sum_no_ask
                total_friction = taker_fee + self.gas_fee

                # Core arbitrage condition:
                # Sum P_ask(NO) < (|M| - 1) + Sum P_bid(YES) - friction
                total_proceeds = unlocked_cash + sum_residual_yes_bid
                net_edge = total_proceeds - sum_no_ask - total_friction

                # Pure Negative-Cost condition:
                # Sum P_ask(NO) < (|M| - 1)
                is_pure_neg = (sum_no_ask < unlocked_cash)

                if net_edge > 0.005 or is_pure_neg:  # At least 0.5 cents edge or pure negative-cost
                    # Bottleneck depth: 50% of the smallest ask depth among selected NO legs
                    min_ask_depth = min(bundle.outcomes[i].depth_ask_no for i in m_indices)
                    executable_q = min_ask_depth * self.depth_cap_ratio

                    # Immediate cash profit unlocked from conversion alone:
                    # (|M| - 1) * Q - Cost(NO)
                    immediate_cash = (unlocked_cash * executable_q) - (sum_no_ask * executable_q)

                    residual_shares = {
                        bundle.outcomes[j].title: executable_q
                        for j in unselected_indices
                    }

                    opp = SubsetArbitrageOpportunity(
                        event_id=bundle.event_id,
                        market_title=bundle.title,
                        subset_indices=m_indices,
                        subset_titles=[bundle.outcomes[i].title for i in m_indices],
                        unselected_indices=unselected_indices,
                        unselected_titles=[bundle.outcomes[j].title for j in unselected_indices],
                        num_legs=m_size,
                        sum_no_ask=round(sum_no_ask, 4),
                        unlocked_cash_per_share=unlocked_cash,
                        sum_residual_yes_bid=round(sum_residual_yes_bid, 4),
                        est_fees_usd=round(total_friction, 4),
                        net_edge_per_share=round(net_edge, 4),
                        is_pure_negative_cost=is_pure_neg,
                        max_executable_qty=round(executable_q, 2),
                        immediate_cash_profit_usd=round(immediate_cash, 2),
                        residual_lottery_shares=residual_shares,
                    )
                    opportunities.append(opp)
                    self.opportunities_found.append(opp)

        # Sort opportunities descending by net edge per share
        opportunities.sort(key=lambda o: (o.is_pure_negative_cost, o.net_edge_per_share), reverse=True)
        return opportunities

    # --------------------------------------------------------------------------
    # BATCH ORDER & CONVERTPOSITIONS EXECUTION SIMULATION
    # --------------------------------------------------------------------------

    def simulate_execution(
        self,
        opp: SubsetArbitrageOpportunity,
        target_qty: Optional[float] = None,
        latency_ms: float = 80.0,
        leg_miss_probability: float = 0.05,
    ) -> ExecutionSimulationResult:
        """
        Simulates:
          1. Concurrent batch dispatch of NO orders via CLOB client.postOrders.
          2. Realistic transit latency (50-120ms).
          3. Legging failure (e.g. 1 leg misses or slips due to book movement).
          4. On-chain NegRiskAdapter.convertPositions call on Polygon (0xd91E80...).
          5. Fallback conversion on remaining partial subset M' if >= 2 legs filled.
        """
        qty = target_qty if target_qty is not None else opp.max_executable_qty
        bundle = self.bundles.get(opp.event_id)
        taker_fee_rate = bundle.taker_fee_rate if bundle else 0.0

        legs_attempted = list(opp.subset_indices)
        legs_filled: List[int] = []
        legs_missed: List[int] = []

        # Simulate fills across each leg
        for leg_idx in legs_attempted:
            # Deterministic/probabilistic leg miss simulation
            if random.random() < leg_miss_probability:
                legs_missed.append(leg_idx)
            else:
                legs_filled.append(leg_idx)

        is_full_fill = (len(legs_missed) == 0)
        legging_failed = not is_full_fill

        # Polygon NegRiskAdapter.convertPositions requires |M'| >= 2
        fallback_salvaged = False
        converted_subset: List[int] = []
        cash_unlocked = 0.0

        if len(legs_filled) >= 2:
            converted_subset = legs_filled
            # Burning |M'| NO tokens of size Q returns (|M'| - 1) * Q base collateral
            m_prime = len(converted_subset)
            cash_unlocked = (m_prime - 1) * qty
            fallback_salvaged = legging_failed

        # Actual purchase cost of filled NO legs
        actual_cost = sum(
            (bundle.outcomes[i].best_ask_no * qty * (1.0 + taker_fee_rate))
            for i in legs_filled
        ) if bundle else (opp.sum_no_ask * qty)

        net_immediate_cash = cash_unlocked - actual_cost

        # Residual YES shares received from convertPositions
        # When converting M', you receive YES shares for all outcomes not in M'
        residual_yes: Dict[str, float] = {}
        residual_mtm = 0.0
        if bundle and len(converted_subset) >= 2:
            converted_set = set(converted_subset)
            for idx, out in enumerate(bundle.outcomes):
                if idx not in converted_set:
                    residual_yes[out.title] = qty
                    residual_mtm += qty * out.best_bid_yes

        result = ExecutionSimulationResult(
            opportunity=opp,
            submitted_qty=qty,
            filled_qty=qty if is_full_fill else (qty * len(legs_filled) / len(legs_attempted)),
            legs_attempted=legs_attempted,
            legs_filled=legs_filled,
            legs_missed=legs_missed,
            is_full_bundle_fill=is_full_fill,
            converted_subset=converted_subset,
            cash_unlocked_usd=round(cash_unlocked, 2),
            actual_purchase_cost_usd=round(actual_cost, 2),
            net_immediate_cash_profit_usd=round(net_immediate_cash, 2),
            residual_yes_shares=residual_yes,
            residual_yes_mtm_value_usd=round(residual_mtm, 2),
            legging_failed=legging_failed,
            fallback_subset_salvaged=fallback_salvaged,
            execution_latency_ms=latency_ms,
            polygon_tx_hash=f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}",
        )

        self.simulated_executions.append(result)
        return result

    # --------------------------------------------------------------------------
    # TELEMETRY & AUDIT SUMMARY
    # --------------------------------------------------------------------------

    def get_audit_summary(self) -> Dict[str, Any]:
        """Computes aggregate performance, legging failure rates, and PnL."""
        total_execs = len(self.simulated_executions)
        legging_misses = sum(1 for e in self.simulated_executions if e.legging_failed)
        pure_neg_count = sum(1 for o in self.opportunities_found if o.is_pure_negative_cost)

        total_cash_unlocked = sum(e.cash_unlocked_usd for e in self.simulated_executions)
        total_cost = sum(e.actual_purchase_cost_usd for e in self.simulated_executions)
        total_immediate_pnl = sum(e.net_immediate_cash_profit_usd for e in self.simulated_executions)
        total_residual_mtm = sum(e.residual_yes_mtm_value_usd for e in self.simulated_executions)

        return {
            "total_bundles_scanned": self.total_bundles_scanned,
            "total_evaluations": self.total_evaluations,
            "opportunities_found": len(self.opportunities_found),
            "pure_negative_cost_opportunities": pure_neg_count,
            "total_simulated_executions": total_execs,
            "legging_miss_count": legging_misses,
            "legging_failure_rate_pct": round((legging_misses / total_execs * 100.0), 2) if total_execs > 0 else 0.0,
            "total_cash_unlocked_usd": round(total_cash_unlocked, 2),
            "total_cost_usd": round(total_cost, 2),
            "net_immediate_cash_profit_usd": round(total_immediate_pnl, 2),
            "total_residual_yes_mtm_value_usd": round(total_residual_mtm, 2),
            "total_combined_economic_value_usd": round(total_immediate_pnl + total_residual_mtm, 2),
        }

    async def aclose(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()

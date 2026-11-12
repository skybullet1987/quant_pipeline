"""
Comprehensive `unittest.TestCase` suite for Agents 7 & 8 (`@micro-portfolio`):
`src/polymarket_research/detectors_microstructure_and_portfolio.py`.

Covers:
  - Programmatic audit of existing carry, maker, and velocity sizing (`LIM-01`..`LIM-04`)
  - Exact 13-schedule `FeeScheduleSpec` parsing (including quadratic `crypto_15_min` and
    ignoring Gamma `takerBaseFee=1000` ceiling when `feeSchedule` is present)
  - Family K (`NearResolutionSettlementCarryDetector`): strict non-`CLASS_A/B` cap on
    unfinalized UMA `proposed` carry, premature proposal `CLASS_D` downgrade, `D-001`
    `KMIA` freeze quarantine, and `K1` complete-set settlement boxes
  - Family L (`MakerTakerLiquidityDetector`): strict separation of `L1A` prelocked
    inventory completion (`CLASS_A` with `$0.00` uncertain rebate in guaranteed floor),
    `L1B` resting passive completion (`CLASS_C`), `L2` fee-asymmetry maker+taker (`CLASS_C`),
    and `L3` speculative reward/rebate market making (`CLASS_C/E`)
  - Family M (`MultiLegComponentDetector` & `PortfolioArbitrageOptimizer`): closed 3-leg
    NegRisk partition + `D-007` `< $500` quarantine, 2-leg `NR2` cash convert, augmented
    placeholder blocking, transitive `A => B => C` implication chain, book-equity clamping,
    `15%` correlated-event cap, `D-001` `KMIA` zero-headroom block, shared L2 depth
    non-double-counting, and 2-opt simultaneous velocity superiority over naive greedy
  - Family N (`MechanismAndStructureScanner` & `ResearchBacklog`): `cumulativeMarkets`,
    quadratic boundary fee boxes, schema-drift detector, and formal proof/counterexamples.
"""

from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent

from src.polymarket_research.detectors_microstructure_and_portfolio import (
    AUTHORITATIVE_BOOK_EQUITY_FORBIDDEN_FOR_SIZING_USD,
    AUTHORITATIVE_LIVE_CASH_PUSD,
    AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD,
    FeeScheduleSpec,
    LIVE_INFRA_HURDLE_BPS_PER_HR,
    MakerTakerLiquidityDetector,
    MarginalDepthTranche,
    MechanismAndStructureScanner,
    MicroPortfolioCandidate,
    MicrostructureAndPortfolioSuite,
    MultiLegComponentDetector,
    NearResolutionSettlementCarryDetector,
    PortfolioArbitrageOptimizer,
    audit_existing_carry_maker_and_velocity_sizing,
    compute_canonical_concentration_keys,
    is_d001_frozen_kmia_entity,
)
from src.polymarket_research.universal_arb_verifier import (
    ArbitrageProofObject,
    BookLevel,
    FourValueMetrics,
    InstrumentOrderBook,
    InventoryHolding,
    OpportunityClass,
    UniversalArbVerifier,
    VerificationConfig,
)


def _raw_book(
    token_id: str,
    *,
    bids: list[tuple[float, float]],
    asks: list[tuple[float, float]],
    min_order_size: float = 5.0,
    tick_size: float = 0.01,
) -> Dict[str, Any]:
    # Deliberately pass unsorted/CLOB-style ascending bids & descending asks to verify sorting!
    return {
        "asset_id": token_id,
        "bids": [{"price": str(px), "size": str(sz)} for px, sz in sorted(bids, key=lambda r: r[0])],
        "asks": [{"price": str(px), "size": str(sz)} for px, sz in sorted(asks, key=lambda r: -r[0])],
        "min_order_size": str(min_order_size),
        "tick_size": str(tick_size),
    }


class TestDetectorsMicrostructureAndPortfolio(unittest.TestCase):
    NOW_TS = 1_794_420_000.0  # Fixed deterministic reference epoch

    def test_01_audit_existing_carry_maker_and_velocity_sizing(self) -> None:
        audit = audit_existing_carry_maker_and_velocity_sizing()
        vb = audit["verified_live_baseline"]
        self.assertAlmostEqual(vb["liquid_pusd_cash_usd"], AUTHORITATIVE_LIVE_CASH_PUSD, places=4)
        self.assertAlmostEqual(vb["d007_15pct_event_cap_usd"], round(AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD * 0.15, 4), places=3)
        self.assertAlmostEqual(vb["infra_hurdle_bps_per_hr"], round(LIVE_INFRA_HURDLE_BPS_PER_HR, 4), places=3)
        lim_ids = [item["id"] for item in audit["identified_limitations"]]
        self.assertEqual(lim_ids, ["LIM-01", "LIM-02", "LIM-03", "LIM-04"])

    def test_02_fee_schedule_spec_curves_and_taker_base_fee_ceiling_guard(self) -> None:
        mkt_quad = {
            "id": "m_quad",
            "feesEnabled": True,
            "feeType": "crypto_15_min",
            "takerBaseFee": 1000,  # Protocol ceiling — MUST NOT be treated as 10% linear fee!
            "feeSchedule": {"rate": 0.25, "exponent": 2, "takerOnly": True, "rebateRate": 0.20},
        }
        spec_q = FeeScheduleSpec.from_market(mkt_quad)
        self.assertTrue(spec_q.fees_enabled)
        self.assertAlmostEqual(spec_q.rate, 0.25, places=6)
        self.assertAlmostEqual(spec_q.exponent, 2.0, places=6)
        self.assertAlmostEqual(spec_q.rebate_rate, 0.20, places=6)
        # At p = 0.90: 0.25 * (0.90 * 0.10)^2 = 0.25 * 0.0081 = 0.002025/sh (vs 0.09 if takerBaseFee=1000 were misread!)
        self.assertAlmostEqual(spec_q.taker_fee_per_gross_share(0.90), 0.002025, places=6)
        net_mkr, _, fee_mkr = spec_q.net_buy_cost_per_share(0.90, is_maker=True)
        self.assertAlmostEqual(fee_mkr, 0.0, places=8)
        self.assertAlmostEqual(net_mkr, 0.90, places=6)

        mkt_zero = {"id": "m_zero", "feesEnabled": False, "takerBaseFee": 1000}
        spec_z = FeeScheduleSpec.from_market(mkt_zero)
        self.assertFalse(spec_z.fees_enabled)
        self.assertAlmostEqual(spec_z.taker_fee_per_gross_share(0.50), 0.0, places=8)

    def test_03_family_k_unfinalized_uma_proposed_never_class_a_or_b(self) -> None:
        det_k = NearResolutionSettlementCarryDetector(reconciled_nav_usd=48.70)
        mkt_prop = {
            "id": "mkt_uma_prop_1",
            "event_id": "ev_uma_1",
            "question": "Will City Council pass Ordinance 42 on Nov 10?",
            "slug": "city-council-ordinance-42",
            "clobTokenIds": json.dumps(["TOK_PROP_Y", "TOK_PROP_N"]),
            "umaResolutionStatus": "proposed",
            "umaResolutionStatuses": json.dumps(["proposed"]),
            "endDate": "2026-11-11T10:00:00Z",  # Past endDate, legitimate proposal in 2h liveness
            "feesEnabled": False,
        }
        books = {
            "TOK_PROP_Y": _raw_book("TOK_PROP_Y", bids=[(0.96, 50.0)], asks=[(0.97, 40.0)]),
            "TOK_PROP_N": _raw_book("TOK_PROP_N", bids=[(0.002, 50.0)], asks=[(0.04, 40.0)]),
        }
        cands = det_k.scan_markets([mkt_prop], books, now_ts=self.NOW_TS)
        carry_cands = [c for c in cands if c.sub_type == "K2_UMA_PROPOSED_DIRECTIONAL_CARRY"]
        self.assertEqual(len(carry_cands), 1)
        c = carry_cands[0]
        self.assertNotIn(c.opportunity_class, {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value})
        self.assertEqual(c.opportunity_class, OpportunityClass.CLASS_C.value)
        self.assertLess(c.min_state_net_payoff_usd, 0.0)
        self.assertGreater(c.expected_net_payoff_usd, 0.0)
        self.assertGreaterEqual(c.worst_case_lockup_hours, 96.0)

    def test_04_family_k_premature_proposal_downgraded_and_kmia_d001_quarantined(self) -> None:
        det_k = NearResolutionSettlementCarryDetector(reconciled_nav_usd=48.70)
        # Premature UMA proposal 1 year before endDate -> strictly CLASS_D (never CLASS_A/B/C!)
        mkt_premature = {
            "id": "mkt_premature_2027",
            "event_id": "ev_prem_1",
            "question": "Will candidate X win the 2027 election?",
            "clobTokenIds": json.dumps(["PREM_Y", "PREM_N"]),
            "umaResolutionStatus": "proposed",
            "umaResolutionStatuses": json.dumps(["proposed"]),
            "endDate": "2027-11-05T00:00:00Z",
            "feesEnabled": False,
        }
        # Frozen D-001 KMIA market (`6707503`) -> quarantined untouched with 0 optimal shares
        mkt_kmia = {
            "id": "6707503",
            "event_id": "ev_kmia_nov7",
            "question": "Will the highest temperature in Miami (KMIA) be 86F or higher on November 7?",
            "clobTokenIds": json.dumps(["KMIA_Y", "KMIA_N"]),
            "umaResolutionStatus": "disputed",
            "endDate": "2026-11-07T23:59:00Z",
        }
        books = {
            "PREM_Y": _raw_book("PREM_Y", bids=[(0.94, 50.0)], asks=[(0.95, 50.0)]),
            "PREM_N": _raw_book("PREM_N", bids=[(0.02, 50.0)], asks=[(0.06, 50.0)]),
            "KMIA_Y": _raw_book("KMIA_Y", bids=[(0.002, 100.0)], asks=[(0.95, 100.0)]),
            "KMIA_N": _raw_book("KMIA_N", bids=[(0.003, 100.0)], asks=[(0.95, 100.0)]),
        }
        cands = det_k.scan_markets([mkt_premature, mkt_kmia], books, now_ts=self.NOW_TS)
        prem_carry = [c for c in cands if c.market_ids == ("mkt_premature_2027",) and c.sub_type == "K2_UMA_PROPOSED_DIRECTIONAL_CARRY"][0]
        self.assertIn(prem_carry.opportunity_class, {OpportunityClass.CLASS_D.value, OpportunityClass.CLASS_E.value})
        self.assertNotIn(prem_carry.opportunity_class, {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value, OpportunityClass.CLASS_C.value})
        self.assertIn("PREMATURE_UMA_PROPOSAL_BEFORE_END_DATE", prem_carry.disqualifiers)

        kmia_q = [c for c in cands if c.market_ids == ("6707503",)][0]
        self.assertTrue(kmia_q.d001_kmia_frozen_blocked)
        self.assertEqual(kmia_q.optimal_shares, 0.0)
        self.assertIn("WXSTATION:KMIA", kmia_q.canonical_event_keys)
        self.assertTrue(is_d001_frozen_kmia_entity(mkt_kmia))

    def test_05_family_k_hedged_complete_set_box_class_b_and_preheld_class_a(self) -> None:
        det_k = NearResolutionSettlementCarryDetector(reconciled_nav_usd=48.70)
        mkt_box = {
            "id": "mkt_near_box",
            "event_id": "ev_near_box",
            "question": "Will BTC close above $95,000 today?",
            "clobTokenIds": json.dumps(["BOX_Y", "BOX_N"]),
            "umaResolutionStatus": "proposed",
            "endDate": "2026-11-11T16:00:00Z",
            "feesEnabled": False,
        }
        books = {
            "BOX_Y": _raw_book("BOX_Y", bids=[(0.51, 30.0)], asks=[(0.52, 20.0)]),
            "BOX_N": _raw_book("BOX_N", bids=[(0.44, 30.0)], asks=[(0.46, 20.0)]),
        }
        # Without inventory -> 2-leg sequential CLOB complete set (`CLASS_B`)
        cands_2leg = det_k.scan_markets([mkt_box], books, now_ts=self.NOW_TS)
        k1_2leg = [c for c in cands_2leg if c.sub_type == "K1_SETTLEMENT_HEDGED_COMPLETE_BOX"][0]
        self.assertEqual(k1_2leg.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertGreater(k1_2leg.min_state_net_payoff_usd, 0.0)

        # With non-frozen pre-held inventory on BOX_Y -> 1-leg FOK + CTF_MERGE (`CLASS_A`)
        holdings = {
            "BOX_Y": InventoryHolding(
                instrument_id="BOX_Y",
                shares=10.0,
                cost_basis_per_share=0.51,
                market_id="mkt_near_box",
            )
        }
        cands_1leg = det_k.scan_markets([mkt_box], books, holdings_by_token=holdings, now_ts=self.NOW_TS)
        k1_1leg = [c for c in cands_1leg if c.sub_type == "K1_SETTLEMENT_HEDGED_COMPLETE_BOX"][0]
        self.assertEqual(k1_1leg.opportunity_class, OpportunityClass.CLASS_A.value)
        self.assertTrue(k1_1leg.is_atomic_or_inventory_locked)
        self.assertGreater(k1_1leg.min_state_net_payoff_usd, 0.0)

    def test_06_family_l_strict_separation_and_zero_uncertain_rebate_in_floor(self) -> None:
        det_l = MakerTakerLiquidityDetector(reconciled_nav_usd=48.70)
        mkt_fee = {
            "id": "mkt_wx_fee",
            "event_id": "ev_wx_nyc",
            "question": "Will NYC Central Park exceed 65F tomorrow?",
            "clobTokenIds": json.dumps(["L_YES", "L_NO"]),
            "feesEnabled": True,
            "feeType": "weather_fees",
            "feeSchedule": {"rate": 0.05, "exponent": 1, "takerOnly": True, "rebateRate": 0.25},
            "rewardsMaxSpread": 3.5,
            "rewardsMinSize": 10.0,
        }
        # Ask_Y = 0.50 (taker net ~0.5128), Ask_N = 0.49 (taker net ~0.5028) -> Taker+Taker = 1.0156 > 1.00 (no taker arb!),
        # while Bid_Y = 0.48 (0-fee maker = 0.49 inside spread) + Ask_N_taker (0.5028) = 0.9928 < 1.00 (`L2` positive gross spread!)
        books = {
            "L_YES": _raw_book("L_YES", bids=[(0.48, 25.0)], asks=[(0.50, 40.0)]),
            "L_NO": _raw_book("L_NO", bids=[(0.47, 25.0)], asks=[(0.49, 40.0)]),
        }
        holdings = {
            "L_YES": InventoryHolding(
                instrument_id="L_YES",
                shares=10.0,
                cost_basis_per_share=0.47,  # 0.47 + 0.5028 taker NO = 0.9728 < 1.00 (`L1A` CLASS_A!)
                market_id="mkt_wx_fee",
            )
        }
        cands = det_l.scan_markets([mkt_fee], books, holdings_by_token=holdings, now_ts=self.NOW_TS)
        by_sub = {c.sub_type: c for c in cands}

        self.assertIn("L1A_FILLED_MAKER_ANCHOR_PRELOCKED_COMPLETION", by_sub)
        c_l1a = by_sub["L1A_FILLED_MAKER_ANCHOR_PRELOCKED_COMPLETION"]
        self.assertEqual(c_l1a.opportunity_class, OpportunityClass.CLASS_A.value)
        self.assertEqual(c_l1a.opportunity_class, c_l1a.proof.opportunity_class)
        self.assertGreater(c_l1a.uncertain_rebate_or_reward_usd, 0.0)
        # Verify uncertain maker rebate is strictly excluded from `min_state_net_payoff_usd`!
        _, _, _ = FeeScheduleSpec.from_market(mkt_fee).net_buy_cost_per_share(0.49, is_maker=False)
        self.assertLess(c_l1a.min_state_net_payoff_usd, 10.0 * (1.0 - (0.47 + 0.49)))

        self.assertIn("L1B_RESTING_PASSIVE_INVENTORY_MAKER_COMPLETION", by_sub)
        c_l1b = by_sub["L1B_RESTING_PASSIVE_INVENTORY_MAKER_COMPLETION"]
        self.assertEqual(c_l1b.opportunity_class, OpportunityClass.CLASS_C.value)

        self.assertIn("L2_FEE_ASYMMETRY_MAKER_HEDGE_PAIR", by_sub)
        c_l2 = by_sub["L2_FEE_ASYMMETRY_MAKER_HEDGE_PAIR"]
        self.assertNotIn(c_l2.opportunity_class, {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value})
        self.assertLess(c_l2.min_state_net_payoff_usd, 0.0)

        self.assertIn("L3_SPECULATIVE_REWARD_OR_REBATE_MM", by_sub)
        c_l3 = by_sub["L3_SPECULATIVE_REWARD_OR_REBATE_MM"]
        self.assertIn(c_l3.opportunity_class, {OpportunityClass.CLASS_C.value, OpportunityClass.CLASS_E.value})
        self.assertLess(c_l3.min_state_net_payoff_usd, 0.0)

    def test_07_family_m_closed_partition_nr2_convert_augmented_trap_and_implication_chain(self) -> None:
        det_m = MultiLegComponentDetector(reconciled_nav_usd=48.70)

        # Event 1: Closed 3-outcome NegRisk partition with YES sum = 0.30 + 0.32 + 0.34 = 0.96 < 1.00,
        # AND 2-NO sum = 0.47 + 0.48 = 0.95 < 1.00 (`M2_NEGRISK_2NO_CASH_CONVERT`)
        ev_closed = {
            "id": "ev_nr_closed",
            "title": "Match Winner (1X2)",
            "negRisk": True,
            "negRiskAugmented": False,
            "markets": [
                {"id": "m_home", "groupItemTitle": "Arsenal", "question": "Will Arsenal win?", "clobTokenIds": json.dumps(["H_Y", "H_N"]), "feesEnabled": False},
                {"id": "m_draw", "groupItemTitle": "Draw", "question": "Will the match end in a draw?", "clobTokenIds": json.dumps(["D_Y", "D_N"]), "feesEnabled": False},
                {"id": "m_away", "groupItemTitle": "Chelsea", "question": "Will Chelsea win?", "clobTokenIds": json.dumps(["A_Y", "A_N"]), "feesEnabled": False},
            ],
        }
        # Event 2: Augmented NegRisk slate with "Person A" placeholder -> MUST NOT reach CLASS_A or CLASS_B!
        ev_aug = {
            "id": "ev_nr_aug",
            "title": "Next Minister",
            "negRisk": True,
            "negRiskAugmented": True,
            "markets": [
                {"id": "ma_1", "groupItemTitle": "Alice", "question": "Will Alice be appointed?", "clobTokenIds": json.dumps(["AY1", "AN1"]), "feesEnabled": False},
                {"id": "ma_2", "groupItemTitle": "Bob", "question": "Will Bob be appointed?", "clobTokenIds": json.dumps(["AY2", "AN2"]), "feesEnabled": False},
                {"id": "ma_3", "groupItemTitle": "Person A", "question": "Will Person A be appointed?", "clobTokenIds": json.dumps(["AY3", "AN3"]), "feesEnabled": False},
            ],
        }
        # Event 3: Transitive 3-deadline implication strip (`June => Sept => Dec`) where `NO_June (0.44) + YES_Dec (0.52) = 0.96 < 1.00`
        ev_chain = {
            "id": "ev_chain_1",
            "title": "Starship Orbital Refueling Deadlines",
            "negRisk": False,
            "markets": [
                {
                    "id": "mc_jun",
                    "question": "Will SpaceX complete orbital refueling by June 30, 2027?",
                    "description": "Resolves Yes per official SpaceX launch telemetry by June 30, 2027 11:59 PM ET.",
                    "resolutionSource": "https://www.spacex.com",
                    "endDate": "2027-06-30T23:59:00Z",
                    "clobTokenIds": json.dumps(["CJ_Y", "CJ_N"]),
                    "feesEnabled": False,
                },
                {
                    "id": "mc_sep",
                    "question": "Will SpaceX complete orbital refueling by September 30, 2027?",
                    "description": "Resolves Yes per official SpaceX launch telemetry by September 30, 2027 11:59 PM ET.",
                    "resolutionSource": "https://www.spacex.com",
                    "endDate": "2027-09-30T23:59:00Z",
                    "clobTokenIds": json.dumps(["CS_Y", "CS_N"]),
                    "feesEnabled": False,
                },
                {
                    "id": "mc_dec",
                    "question": "Will SpaceX complete orbital refueling by December 31, 2027?",
                    "description": "Resolves Yes per official SpaceX launch telemetry by December 31, 2027 11:59 PM ET.",
                    "resolutionSource": "https://www.spacex.com",
                    "endDate": "2027-12-31T23:59:00Z",
                    "clobTokenIds": json.dumps(["CD_Y", "CD_N"]),
                    "feesEnabled": False,
                },
            ],
        }
        books = {
            "H_Y": _raw_book("H_Y", bids=[(0.29, 40.0)], asks=[(0.30, 30.0)]),
            "H_N": _raw_book("H_N", bids=[(0.46, 40.0)], asks=[(0.47, 30.0)]),
            "D_Y": _raw_book("D_Y", bids=[(0.31, 40.0)], asks=[(0.32, 30.0)]),
            "D_N": _raw_book("D_N", bids=[(0.47, 40.0)], asks=[(0.48, 30.0)]),
            "A_Y": _raw_book("A_Y", bids=[(0.33, 40.0)], asks=[(0.34, 30.0)]),
            "A_N": _raw_book("A_N", bids=[(0.64, 40.0)], asks=[(0.65, 30.0)]),
            "AY1": _raw_book("AY1", bids=[(0.28, 40.0)], asks=[(0.29, 30.0)]),
            "AN1": _raw_book("AN1", bids=[(0.68, 40.0)], asks=[(0.70, 30.0)]),
            "AY2": _raw_book("AY2", bids=[(0.28, 40.0)], asks=[(0.29, 30.0)]),
            "AN2": _raw_book("AN2", bids=[(0.68, 40.0)], asks=[(0.70, 30.0)]),
            "AY3": _raw_book("AY3", bids=[(0.28, 40.0)], asks=[(0.29, 30.0)]),
            "AN3": _raw_book("AN3", bids=[(0.68, 40.0)], asks=[(0.70, 30.0)]),
            "CJ_Y": _raw_book("CJ_Y", bids=[(0.54, 40.0)], asks=[(0.56, 30.0)]),
            "CJ_N": _raw_book("CJ_N", bids=[(0.42, 40.0)], asks=[(0.44, 30.0)]),
            "CS_Y": _raw_book("CS_Y", bids=[(0.49, 40.0)], asks=[(0.51, 30.0)]),
            "CS_N": _raw_book("CS_N", bids=[(0.47, 40.0)], asks=[(0.49, 30.0)]),
            "CD_Y": _raw_book("CD_Y", bids=[(0.50, 40.0)], asks=[(0.52, 30.0)]),
            "CD_N": _raw_book("CD_N", bids=[(0.46, 40.0)], asks=[(0.48, 30.0)]),
        }
        cands = det_m.scan_events_and_graph([ev_closed, ev_aug, ev_chain], books, now_ts=self.NOW_TS)

        m1 = [c for c in cands if c.event_id == "ev_nr_closed" and c.sub_type == "M1_CLOSED_PARTITION_MULTI_OUTCOME_BUY_ALL"][0]
        self.assertEqual(m1.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertTrue(m1.d007_sub500_multileg_quarantine)
        self.assertEqual(m1.execution_mode_gate, "QUARANTINED_D007_LT_500_NAV_MODE_2_SHADOW")

        m2 = [c for c in cands if c.event_id == "ev_nr_closed" and c.sub_type == "M2_NEGRISK_2NO_CASH_CONVERT"][0]
        self.assertEqual(m2.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertEqual(m2.sequential_clob_legs, 2)
        self.assertFalse(m2.d007_sub500_multileg_quarantine)

        aug_cands = [c for c in cands if c.event_id == "ev_nr_aug"]
        for ac in aug_cands:
            self.assertNotIn(ac.opportunity_class, {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value})

        chains = [c for c in cands if c.sub_type == "M3_TRANSITIVE_IMPLICATION_DOMINANCE_CHAIN" and c.market_ids == ("mc_jun", "mc_dec")]
        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0].opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertGreater(chains[0].min_state_net_payoff_usd, 0.0)

    def test_08_portfolio_optimizer_constraints_book_equity_clamp_shared_depth_and_2opt(self) -> None:
        # 1. Passing `$99.21` book equity while KMIA is disputed MUST auto-clamp to reconciled NAV (`~$48.83`)!
        opt = PortfolioArbitrageOptimizer(
            available_liquid_pusd=AUTHORITATIVE_LIVE_CASH_PUSD,
            reconciled_nav_usd=AUTHORITATIVE_BOOK_EQUITY_FORBIDDEN_FOR_SIZING_USD,
            settlement_reserve_pct=0.05,
        )
        self.assertLess(opt.reconciled_nav_usd, 50.0)

        # Construct competing candidates testing:
        #   - `CAND_KMIA_NEW`: new Miami weather market (`WXSTATION:KMIA`) -> blocked by existing `$50.51` frozen KMIA concentration!
        #   - `CAND_3LEG_SEQ`: 3-leg sequential CLOB bundle -> quarantined below `$500` NAV (`D-007`)!
        #   - `CAND_CLASS_C`: `CLASS_C` UMA carry -> blocked under `strict_riskless_only=True`!
        #   - `CAND_SHARED_1` & `CAND_SHARED_2`: two `CLASS_B` boxes sharing `SHARED_TOK_X` with only `10.0` ask shares on book!
        #   - `CAND_SLOW` (`24h` lockup) vs `CAND_FAST` (`0.25h` lockup): fast velocity box allocated first!
        books = {
            "SHARED_TOK_X": InstrumentOrderBook("SHARED_TOK_X", asks=(BookLevel(0.45, 10.0),), bids=(BookLevel(0.44, 10.0),)),
            "TOK_Y1": InstrumentOrderBook("TOK_Y1", asks=(BookLevel(0.50, 50.0),), bids=(BookLevel(0.49, 50.0),)),
            "TOK_Y2": InstrumentOrderBook("TOK_Y2", asks=(BookLevel(0.51, 50.0),), bids=(BookLevel(0.50, 50.0),)),
            "FAST_A": InstrumentOrderBook("FAST_A", asks=(BookLevel(0.47, 50.0),), bids=(BookLevel(0.46, 50.0),)),
            "FAST_B": InstrumentOrderBook("FAST_B", asks=(BookLevel(0.48, 50.0),), bids=(BookLevel(0.47, 50.0),)),
        }

        def _mk_cand(
            cid: str,
            cls_v: str,
            keys: tuple[str, ...],
            consumed: tuple[tuple[str, str, float], ...],
            legs: int,
            shares: float,
            cap: float,
            prof: float,
            lock_h: float,
        ) -> MicroPortfolioCandidate:
            return MicroPortfolioCandidate(
                candidate_id=cid,
                family="A",
                sub_type="TEST_BOX",
                opportunity_class=cls_v,
                execution_mode_gate="MODE_2_SHADOW",
                event_id=keys[0],
                canonical_event_keys=keys,
                market_ids=(cid,),
                token_ids=tuple(t for t, _, _ in consumed),
                consumed_book_sides=consumed,
                sequential_clob_legs=legs,
                is_atomic_or_inventory_locked=(legs == 1),
                d007_sub500_multileg_quarantine=(legs >= 3),
                d001_kmia_frozen_blocked=False,
                min_order_shares=5.0,
                optimal_shares=shares,
                capital_required_usd=cap,
                gross_edge_bps=300.0,
                net_executable_edge_bps=250.0,
                min_state_net_payoff_usd=prof,
                expected_net_payoff_usd=prof,
                expected_lockup_hours=lock_h,
                worst_case_lockup_hours=lock_h,
                net_bps_per_hour_expected=round((prof / cap) * 10_000.0 / lock_h, 2),
                net_bps_per_hour_worst_case=round((prof / cap) * 10_000.0 / lock_h, 2),
                dispute_probability=0.0,
                partial_fill_prob=0.0,
                adverse_selection_cost_usd=0.0,
                uncertain_rebate_or_reward_usd=0.0,
                dormant_near_miss=False,
                four_value_ledger=FourValueMetrics(prof, prof, prof, 0.0),
            )

        candidates = [
            _mk_cand("CAND_KMIA_NEW", "CLASS_A", ("WXSTATION:KMIA",), (("FAST_A", "ASK", 1.0),), 1, 5.0, 4.80, 0.20, 0.25),
            _mk_cand("CAND_3LEG_SEQ", "CLASS_B", ("EVT:3LEG",), (("FAST_A", "ASK", 1.0),), 3, 5.0, 4.80, 0.20, 0.25),
            _mk_cand("CAND_CLASS_C", "CLASS_C", ("EVT:CARRY",), (("FAST_A", "ASK", 1.0),), 1, 5.0, 4.80, 0.25, 2.0),
            _mk_cand("CAND_SLOW_SINK", "CLASS_B", ("EVT:SLOW",), (("FAST_B", "ASK", 1.0),), 2, 10.0, 9.60, 0.12, 24.0),
            _mk_cand("CAND_SHARED_1", "CLASS_B", ("EVT:SH1",), (("SHARED_TOK_X", "ASK", 1.0), ("TOK_Y1", "ASK", 1.0)), 2, 10.0, 9.50, 0.50, 0.25),
            _mk_cand("CAND_SHARED_2", "CLASS_B", ("EVT:SH2",), (("SHARED_TOK_X", "ASK", 1.0), ("TOK_Y2", "ASK", 1.0)), 2, 10.0, 9.60, 0.40, 0.25),
            _mk_cand("CAND_FAST_A", "CLASS_A", ("EVT:FASTA",), (("FAST_A", "ASK", 1.0),), 1, 5.0, 4.75, 0.25, 0.10),
        ]

        res = opt.optimize_portfolio(candidates, books_by_token=books)
        self.assertTrue(res.d001_kmia_untouched_verified)
        self.assertTrue(res.d007_concentration_verified)
        self.assertTrue(res.d007_sub500_multileg_quarantine_verified)

        alloc_by_id = {s.candidate_id: s for s in res.allocated_slices}
        self.assertNotIn("CAND_KMIA_NEW", alloc_by_id)
        self.assertNotIn("CAND_3LEG_SEQ", alloc_by_id)
        self.assertNotIn("CAND_CLASS_C", alloc_by_id)
        self.assertIn("CAND_FAST_A", alloc_by_id)

        # Verify shared L2 book (`SHARED_TOK_X` has only 10.0 shares total) is NEVER double-counted!
        shared_sh_total = sum(
            s.allocated_shares for cid, s in alloc_by_id.items() if cid in {"CAND_SHARED_1", "CAND_SHARED_2"}
        )
        self.assertLessEqual(shared_sh_total, 10.0 + 1e-6)

        # Verify per-event concentration cap (`<= 15%` of `$48.70` = `~$7.30`) is respected on every allocated slice!
        for sl in res.allocated_slices:
            self.assertLessEqual(sl.allocated_capital_usd, res.per_event_cap_usd + 1e-6)

        # Verify 2-opt swap: with tight `$6.50` budget (0% reserve), a smaller lower-rate slice (`$4.80`, `$0.05/hr`)
        # is swapped out for a lumpy higher-total-profit-per-hr slice (`$6.20`, `$0.40/hr`)!
        opt_tight = PortfolioArbitrageOptimizer(
            available_liquid_pusd=6.50,
            reconciled_nav_usd=60.0,
            settlement_reserve_pct=0.0,
            existing_positions=(),
        )
        c_small = MicroPortfolioCandidate(
            candidate_id="SMALL_HIGH_MARGINAL_LOW_TOTAL",
            family="A",
            sub_type="TEST",
            opportunity_class="CLASS_B",
            execution_mode_gate="MODE_2_SHADOW",
            event_id="E1",
            canonical_event_keys=("EVT:E1",),
            market_ids=("m1",),
            token_ids=("T1",),
            consumed_book_sides=(),
            sequential_clob_legs=2,
            is_atomic_or_inventory_locked=False,
            d007_sub500_multileg_quarantine=False,
            d001_kmia_frozen_blocked=False,
            min_order_shares=5.0,
            optimal_shares=5.0,
            capital_required_usd=2.50,
            gross_edge_bps=200.0,
            net_executable_edge_bps=200.0,
            min_state_net_payoff_usd=0.06,
            expected_net_payoff_usd=0.06,
            expected_lockup_hours=1.0,
            worst_case_lockup_hours=1.0,
            net_bps_per_hour_expected=240.0,
            net_bps_per_hour_worst_case=240.0,
            dispute_probability=0.0,
            partial_fill_prob=0.0,
            adverse_selection_cost_usd=0.0,
            uncertain_rebate_or_reward_usd=0.0,
            dormant_near_miss=False,
            four_value_ledger=FourValueMetrics(0.06, 0.06, 0.06, 0.0),
            marginal_tranches=(MarginalDepthTranche(0, 5.0, 2.50, 0.06, 0.06, 240.0),),
        )
        c_lumpy = MicroPortfolioCandidate(
            candidate_id="LUMPY_SUPERIOR_DOLLAR_PER_HR",
            family="A",
            sub_type="TEST",
            opportunity_class="CLASS_B",
            execution_mode_gate="MODE_2_SHADOW",
            event_id="E2",
            canonical_event_keys=("EVT:E2",),
            market_ids=("m2",),
            token_ids=("T2",),
            consumed_book_sides=(),
            sequential_clob_legs=2,
            is_atomic_or_inventory_locked=False,
            d007_sub500_multileg_quarantine=False,
            d001_kmia_frozen_blocked=False,
            min_order_shares=6.0,
            optimal_shares=6.0,
            capital_required_usd=6.00,
            gross_edge_bps=180.0,
            net_executable_edge_bps=180.0,
            min_state_net_payoff_usd=0.11,
            expected_net_payoff_usd=0.11,
            expected_lockup_hours=1.0,
            worst_case_lockup_hours=1.0,
            net_bps_per_hour_expected=183.33,
            net_bps_per_hour_worst_case=183.33,
            dispute_probability=0.0,
            partial_fill_prob=0.0,
            adverse_selection_cost_usd=0.0,
            uncertain_rebate_or_reward_usd=0.0,
            dormant_near_miss=False,
            four_value_ledger=FourValueMetrics(0.11, 0.11, 0.11, 0.0),
            marginal_tranches=(MarginalDepthTranche(0, 6.0, 6.00, 0.11, 0.11, 183.33),),
        )
        res_2opt = opt_tight.optimize_portfolio([c_small, c_lumpy])
        self.assertEqual([s.candidate_id for s in res_2opt.allocated_slices], ["LUMPY_SUPERIOR_DOLLAR_PER_HR"])
        self.assertAlmostEqual(res_2opt.portfolio_realizable_profit_per_hour_usd, 0.11, places=5)

    def test_09_family_n_mechanism_scanner_backlog_and_counterexample_suite(self) -> None:
        scanner = MechanismAndStructureScanner(reconciled_nav_usd=48.70)
        events = [
            {
                "id": "ev_cum_n",
                "title": "Cumulative Strike Strip",
                "cumulativeMarkets": True,
                "experimentalNewGammaFlag": True,  # Unrecognized key -> detected!
                "markets": [
                    {
                        "id": "mn_1",
                        "question": "Will event happen by May 1, 2027?",
                        "endDate": "2027-05-01T00:00:00Z",
                        "clobTokenIds": json.dumps(["MN1_Y", "MN1_N"]),
                        "feesEnabled": False,
                        "comboStatus": "enabled",
                        "holdingRewardsEnabled": True,
                        "brandNewMarketField": "v2",
                    },
                    {
                        "id": "mn_2",
                        "question": "Will event happen by August 1, 2027?",
                        "endDate": "2027-08-01T00:00:00Z",
                        "clobTokenIds": json.dumps(["MN2_Y", "MN2_N"]),
                        "feesEnabled": False,
                        "customLiveness": 900,
                    },
                ],
            },
            {
                "id": "ev_quad_n",
                "title": "BTC 15m Up or Down",
                "markets": [
                    {
                        "id": "mn_quad",
                        "question": "BTC Up or Down 15m?",
                        "clobTokenIds": json.dumps(["MQ_Y", "MQ_N"]),
                        "feesEnabled": True,
                        "feeType": "crypto_15_min",
                        "feeSchedule": {"rate": 0.25, "exponent": 2, "takerOnly": True, "rebateRate": 0.20},
                    }
                ],
            },
        ]
        books = {
            "MN1_Y": _raw_book("MN1_Y", bids=[(0.55, 30.0)], asks=[(0.57, 30.0)]),
            "MN1_N": _raw_book("MN1_N", bids=[(0.41, 30.0)], asks=[(0.43, 30.0)]),
            "MN2_Y": _raw_book("MN2_Y", bids=[(0.50, 30.0)], asks=[(0.52, 30.0)]),  # 0.43 + 0.52 = 0.95 < 1.00!
            "MN2_N": _raw_book("MN2_N", bids=[(0.46, 30.0)], asks=[(0.48, 30.0)]),
            "MQ_Y": _raw_book("MQ_Y", bids=[(0.89, 30.0)], asks=[(0.90, 30.0)]),
            "MQ_N": _raw_book("MQ_N", bids=[(0.06, 30.0)], asks=[(0.07, 30.0)]),  # 0.90 + 0.07 + tiny quad fee < 1.00!
        }
        cands, backlog, catalog = scanner.scan_universe_mechanisms(events, books, now_ts=self.NOW_TS)
        self.assertTrue(catalog["proof_and_counterexample_suite"]["all_counterexamples_verified"])
        self.assertIn("experimentalNewGammaFlag", catalog["unrecognized_gamma_event_keys"])
        self.assertIn("brandNewMarketField", catalog["unrecognized_gamma_market_keys"])
        self.assertEqual(len(backlog), 7)
        self.assertGreaterEqual(backlog[0].priority_rank_score, backlog[-1].priority_rank_score)
        sub_types = {c.sub_type for c in cands if c.opportunity_class == OpportunityClass.CLASS_B.value}
        self.assertIn("N5_CUMULATIVE_EVENT_MONOTONE_LADDER", sub_types)
        self.assertIn("N1_QUADRATIC_FEE_CURVE_COMPLETE_SET", sub_types)

    def test_10_unified_suite_end_to_end_with_peer_candidates(self) -> None:
        suite = MicrostructureAndPortfolioSuite()
        events = [
            {
                "id": "ev_suite_1",
                "title": "Test Binary Closing Soon",
                "markets": [
                    {
                        "id": "ms_1",
                        "question": "Will test proposition resolve Yes?",
                        "endDate": "2026-11-11T16:30:00Z",
                        "umaResolutionStatus": "proposed",
                        "clobTokenIds": json.dumps(["MS_Y", "MS_N"]),
                        "feesEnabled": False,
                    }
                ],
            }
        ]
        books = {
            "MS_Y": _raw_book("MS_Y", bids=[(0.47, 25.0)], asks=[(0.48, 25.0)]),
            "MS_N": _raw_book("MS_N", bids=[(0.48, 25.0)], asks=[(0.49, 25.0)]),
        }
        peer_cand = {
            "candidate_id": "PEER_A_C1_BOX_1",
            "family": "A",
            "sub_type": "C1_COMPLETE_SET",
            "opportunity_class": "CLASS_B",
            "event_id": "ev_peer_a",
            "market_ids": ("m_peer_a",),
            "token_ids": ("PA_Y", "PA_N"),
            "sequential_clob_legs": 2,
            "optimal_shares": 6.0,
            "capital_required_usd": 5.82,
            "min_state_net_payoff_usd": 0.18,
            "expected_net_payoff_usd": 0.16,
            "expected_lockup_hours": 0.10,
            "worst_case_lockup_hours": 0.25,
        }
        out = suite.run_all(events, books, peer_candidates_a_to_j=[peer_cand], now_ts=self.NOW_TS)
        self.assertIn("portfolio_optimization_live_48_70", out)
        self.assertIn("LIVE_CASH_BASELINE_48_70", out["portfolio_shadow_budget_curve"])
        self.assertIn("SHADOW_BUDGET_500", out["portfolio_shadow_budget_curve"])
        live_opt = out["portfolio_optimization_live_48_70"]
        self.assertGreater(live_opt.total_allocated_capital_usd, 0.0)
        self.assertTrue(live_opt.d001_kmia_untouched_verified)

    def test_11_closed_sibling_negrisk_and_negated_cumulative_trap_blocked(self) -> None:
        det_m = MultiLegComponentDetector(reconciled_nav_usd=48.70)
        ev_partial_closed = {
            "id": "ev_partial_closed",
            "title": "Partial Closed Slate",
            "negRisk": True,
            "negRiskAugmented": False,
            "markets": [
                {"id": "pc_1", "groupItemTitle": "A", "question": "A?", "clobTokenIds": json.dumps(["PC1_Y", "PC1_N"]), "feesEnabled": False},
                {"id": "pc_2", "groupItemTitle": "B", "question": "B?", "clobTokenIds": json.dumps(["PC2_Y", "PC2_N"]), "feesEnabled": False},
                {"id": "pc_3", "groupItemTitle": "C", "question": "C?", "clobTokenIds": json.dumps(["PC3_Y", "PC3_N"]), "feesEnabled": False},
                {"id": "pc_4_won", "groupItemTitle": "D", "question": "D?", "closed": True, "clobTokenIds": json.dumps(["PC4_Y", "PC4_N"]), "feesEnabled": False},
            ],
        }
        books = {
            "PC1_Y": _raw_book("PC1_Y", bids=[(0.20, 30.0)], asks=[(0.22, 30.0)]),
            "PC1_N": _raw_book("PC1_N", bids=[(0.40, 30.0)], asks=[(0.42, 30.0)]),
            "PC2_Y": _raw_book("PC2_Y", bids=[(0.20, 30.0)], asks=[(0.22, 30.0)]),
            "PC2_N": _raw_book("PC2_N", bids=[(0.40, 30.0)], asks=[(0.42, 30.0)]),
            "PC3_Y": _raw_book("PC3_Y", bids=[(0.20, 30.0)], asks=[(0.22, 30.0)]),
            "PC3_N": _raw_book("PC3_N", bids=[(0.70, 30.0)], asks=[(0.72, 30.0)]),
        }
        cands_m = det_m.scan_events_and_graph([ev_partial_closed], books, now_ts=self.NOW_TS)
        for c in cands_m:
            self.assertNotIn(c.opportunity_class, {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value})

        scanner = MechanismAndStructureScanner(reconciled_nav_usd=48.70)
        ev_negated_cum = {
            "id": "ev_neg_cum",
            "cumulativeMarkets": True,
            "markets": [
                {
                    "id": "nc_1",
                    "question": "Will the Fed not cut rates by May 1, 2027?",
                    "endDate": "2027-05-01T00:00:00Z",
                    "clobTokenIds": json.dumps(["NC1_Y", "NC1_N"]),
                    "feesEnabled": False,
                },
                {
                    "id": "nc_2",
                    "question": "Will the Fed not cut rates by August 1, 2027?",
                    "endDate": "2027-08-01T00:00:00Z",
                    "clobTokenIds": json.dumps(["NC2_Y", "NC2_N"]),
                    "feesEnabled": False,
                },
            ],
        }
        bks_nc = {
            "NC1_Y": _raw_book("NC1_Y", bids=[(0.55, 30.0)], asks=[(0.57, 30.0)]),
            "NC1_N": _raw_book("NC1_N", bids=[(0.40, 30.0)], asks=[(0.42, 30.0)]),
            "NC2_Y": _raw_book("NC2_Y", bids=[(0.48, 30.0)], asks=[(0.50, 30.0)]),
            "NC2_N": _raw_book("NC2_N", bids=[(0.48, 30.0)], asks=[(0.50, 30.0)]),
        }
        cands_n, _, _ = scanner.scan_universe_mechanisms([ev_negated_cum], bks_nc, now_ts=self.NOW_TS)
        self.assertEqual(len(cands_n), 0)

    def test_12_over_under_polarity_map_mismatch_and_yearless_deadline_inversion_blocked(self) -> None:
        det_m = MultiLegComponentDetector(reconciled_nav_usd=48.70)
        events_traps = [
            {
                "id": "ev_ou_trap",
                "title": "Esports Totals",
                "negRisk": False,
                "markets": [
                    {
                        "id": "6950562",
                        "question": "Total Kills Over/Under 50.5 in Game 1?",
                        "outcomes": json.dumps(["Over", "Under"]),
                        "endDate": "2026-11-12T00:00:00Z",
                        "clobTokenIds": json.dumps(["OU50_O", "OU50_U"]),
                        "feesEnabled": False,
                    },
                    {
                        "id": "6967460",
                        "question": "Total Kills Over/Under 55.5 in Game 1?",
                        "outcomes": json.dumps(["Over", "Under"]),
                        "endDate": "2026-11-12T00:00:00Z",
                        "clobTokenIds": json.dumps(["OU55_O", "OU55_U"]),
                        "feesEnabled": False,
                    },
                    {
                        "id": "6962550",
                        "question": "Map 2 Total Rounds: Over/Under 24.5",
                        "outcomes": json.dumps(["Over", "Under"]),
                        "endDate": "2026-11-12T00:00:00Z",
                        "clobTokenIds": json.dumps(["M2_O", "M2_U"]),
                        "feesEnabled": False,
                    },
                    {
                        "id": "6964023",
                        "question": "Map 3 Total Rounds: Over/Under 21.5",
                        "outcomes": json.dumps(["Over", "Under"]),
                        "endDate": "2026-11-12T00:00:00Z",
                        "clobTokenIds": json.dumps(["M3_O", "M3_U"]),
                        "feesEnabled": False,
                    },
                ],
            },
            {
                "id": "ev_year_wrap_trap",
                "title": "US imports Russian diesel",
                "negRisk": False,
                "markets": [
                    {
                        "id": "6438437",
                        "question": "US imports Russian diesel by March 31?",
                        "endDate": "2027-03-31T23:59:00Z",  # 2027!
                        "clobTokenIds": json.dumps(["RD_MAR_Y", "RD_MAR_N"]),
                        "feesEnabled": False,
                    },
                    {
                        "id": "6301107",
                        "question": "US imports Russian diesel by November 15?",
                        "endDate": "2026-11-15T23:59:00Z",  # 2026!
                        "clobTokenIds": json.dumps(["RD_NOV_Y", "RD_NOV_N"]),
                        "feesEnabled": False,
                    },
                ],
            },
        ]
        bks = {
            t: _raw_book(t, bids=[(0.20, 40.0)], asks=[(0.21, 40.0)])
            for t in ("OU50_O", "OU50_U", "OU55_O", "OU55_U", "M2_O", "M2_U", "M3_O", "M3_U", "RD_MAR_Y", "RD_MAR_N", "RD_NOV_Y", "RD_NOV_N")
        }
        cands = det_m.scan_events_and_graph(events_traps, bks, now_ts=self.NOW_TS)
        for c in cands:
            if c.sub_type == "M3_TRANSITIVE_IMPLICATION_DOMINANCE_CHAIN":
                self.assertNotIn(c.opportunity_class, {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value})

    def test_13_bug_mp1_shared_l1_rung_no_double_counting_and_gross_haircut(self) -> None:
        # Two competing K1 boxes sharing `T_SHARED` whose ask book has `10 @ $0.40` + unwalked `500 @ $0.99`!
        det_k = NearResolutionSettlementCarryDetector(reconciled_nav_usd=200.0)
        mkts = [
            {
                "id": "m_share_1",
                "event_id": "ev_sh_1",
                "question": "Shared token box 1?",
                "endDate": "2026-11-11T17:00:00Z",
                "clobTokenIds": json.dumps(["T_SHARED", "T_COMP_1"]),
                "feesEnabled": False,
            },
            {
                "id": "m_share_2",
                "event_id": "ev_sh_2",
                "question": "Shared token box 2?",
                "endDate": "2026-11-11T17:00:00Z",
                "clobTokenIds": json.dumps(["T_SHARED", "T_COMP_2"]),
                "feesEnabled": False,
            },
        ]
        bks = {
            "T_SHARED": _raw_book("T_SHARED", bids=[(0.38, 20.0)], asks=[(0.40, 10.0), (0.99, 500.0)]),
            "T_COMP_1": _raw_book("T_COMP_1", bids=[(0.50, 50.0)], asks=[(0.52, 50.0)]),
            "T_COMP_2": _raw_book("T_COMP_2", bids=[(0.51, 50.0)], asks=[(0.53, 50.0)]),
        }
        k_cands = [
            c
            for c in det_k.scan_markets(mkts, bks, now_ts=self.NOW_TS)
            if c.sub_type == "K1_SETTLEMENT_HEDGED_COMPLETE_BOX"
        ]
        self.assertEqual(len(k_cands), 2)

        opt = PortfolioArbitrageOptimizer(
            available_liquid_pusd=100.0,
            reconciled_nav_usd=200.0,
            settlement_reserve_pct=0.0,
            existing_positions=(),
        )
        # 1) With `books_by_token=bks`: `$0.99` rung must NOT subsidize double-allocation of `10 @ $0.40`!
        res_with_books = opt.optimize_portfolio(k_cands, books_by_token=bks)
        tot_sh_with_books = sum(s.allocated_shares for s in res_with_books.allocated_slices)
        self.assertLessEqual(tot_sh_with_books, 10.0 + 1e-6)
        self.assertGreaterEqual(tot_sh_with_books, 5.0)

        # 2) With `books_by_token=None`: must NEVER default to `1e9`!
        res_no_books = opt.optimize_portfolio(k_cands, books_by_token=None)
        tot_sh_no_books = sum(s.allocated_shares for s in res_no_books.allocated_slices)
        self.assertLessEqual(tot_sh_no_books, 10.0 + 1e-6)

        # 3) Protocol V2 buy-share fee haircut (`gross_shares > net_shares`) tracked in `consumed_book_sides`
        scanner = MechanismAndStructureScanner(reconciled_nav_usd=200.0)
        ev_fee = [
            {
                "id": "ev_v2_haircut",
                "markets": [
                    {
                        "id": "m_v2_hc",
                        "question": "Crypto 5m Up or Down?",
                        "clobTokenIds": json.dumps(["V2_Y", "V2_N"]),
                        "feesEnabled": True,
                        "feeType": "crypto_15_min",
                        "feeSchedule": {"rate": 0.25, "exponent": 2, "takerOnly": True, "rebateRate": 0.20},
                    }
                ],
            }
        ]
        bks_fee = {
            "V2_Y": _raw_book("V2_Y", bids=[(0.48, 20.0)], asks=[(0.50, 10.0)]),
            "V2_N": _raw_book("V2_N", bids=[(0.42, 20.0)], asks=[(0.44, 20.0)]),
        }
        cands_n, _, _ = scanner.scan_universe_mechanisms(ev_fee, bks_fee, now_ts=self.NOW_TS)
        n1_cands = [c for c in cands_n if c.sub_type == "N1_QUADRATIC_FEE_CURVE_COMPLETE_SET"]
        self.assertEqual(len(n1_cands), 1)
        mult_map = {tok: mult for tok, _, mult in n1_cands[0].consumed_book_sides}
        self.assertGreater(mult_map["V2_Y"], 1.01)  # V2 haircut at p=0.50 requires > 1.015 gross shares per net share!
        res_v2 = opt.optimize_portfolio(n1_cands, books_by_token=bks_fee)
        tot_v2_net_sh = sum(s.allocated_shares for s in res_v2.allocated_slices)
        self.assertLess(tot_v2_net_sh, 10.0)  # 10.0 gross ask shares on `V2_Y` yields strictly < 10.0 net shares!

    def test_14_bug_mp2_dual_import_proof_coercion_and_token_concentration_cap(self) -> None:
        from dataclasses import dataclass as _dc

        verifier = UniversalArbVerifier(
            VerificationConfig(max_budget_usd=20.0, reconciled_nav_usd=48.70, now_ts=self.NOW_TS)
        )
        bk_y = InstrumentOrderBook(
            "SAME_TOK_Y",
            market_id="mkt_same_mp2",
            condition_id="0xcond_mp2",
            asks=(BookLevel(0.47, 50.0),),
            bids=(BookLevel(0.46, 50.0),),
            book_timestamp_sec=self.NOW_TS,
        )
        bk_n = InstrumentOrderBook(
            "SAME_TOK_N",
            market_id="mkt_same_mp2",
            condition_id="0xcond_mp2",
            asks=(BookLevel(0.49, 50.0),),
            bids=(BookLevel(0.48, 50.0),),
            book_timestamp_sec=self.NOW_TS,
        )
        p1 = verifier.verify_binary_complete_set(
            candidate_id="PROOF_DUP_1",
            yes_book=bk_y,
            no_book=bk_n,
            merge_immediately=True,
        )
        p2 = verifier.verify_binary_complete_set(
            candidate_id="PROOF_DUP_2",
            yes_book=bk_y,
            no_book=bk_n,
            merge_immediately=True,
        )

        # Simulate dual-import (`polymarket_research.*` vs `src.polymarket_research.*`) foreign class identity!
        @_dc(frozen=True)
        class ForeignModuleProofClone:
            candidate_id: str
            family: str
            opportunity_class: str
            is_mathematically_proven_arb: bool
            is_atomic_or_prelocked: bool
            d007_sub500_multileg_quarantine: bool
            execution_mode_cap: str
            optimal_executable_quantity: float
            gross_top_of_book_edge_per_unit: float
            net_executable_edge_per_unit: float
            min_state_net_payoff_usd: float
            max_state_net_payoff_usd: float
            expected_net_payoff_usd: float
            worst_state_id: str
            capital_efficiency_bps_per_hr: float
            four_value_ledger: object
            cost_breakdown: object
            leg_executions: tuple
            proof_sha256: str
            counterexample_states: tuple = ()
            disqualifiers: tuple = ()

        foreign_p1 = ForeignModuleProofClone(
            candidate_id=p1.candidate_id,
            family=p1.family,
            opportunity_class=p1.opportunity_class,
            is_mathematically_proven_arb=p1.is_mathematically_proven_arb,
            is_atomic_or_prelocked=p1.is_atomic_or_prelocked,
            d007_sub500_multileg_quarantine=p1.d007_sub500_multileg_quarantine,
            execution_mode_cap=p1.execution_mode_cap,
            optimal_executable_quantity=p1.optimal_executable_quantity,
            gross_top_of_book_edge_per_unit=p1.gross_top_of_book_edge_per_unit,
            net_executable_edge_per_unit=p1.net_executable_edge_per_unit,
            min_state_net_payoff_usd=p1.min_state_net_payoff_usd,
            max_state_net_payoff_usd=p1.max_state_net_payoff_usd,
            expected_net_payoff_usd=p1.expected_net_payoff_usd,
            worst_state_id=p1.worst_state_id,
            capital_efficiency_bps_per_hr=p1.capital_efficiency_bps_per_hr,
            four_value_ledger=p1.four_value_ledger,
            cost_breakdown=p1.cost_breakdown,
            leg_executions=p1.leg_executions,
            proof_sha256=p1.proof_sha256,
            counterexample_states=p1.counterexample_states,
            disqualifiers=p1.disqualifiers,
        )
        self.assertFalse(isinstance(foreign_p1, ArbitrageProofObject))

        opt = PortfolioArbitrageOptimizer(
            available_liquid_pusd=48.70,
            reconciled_nav_usd=48.70,
            settlement_reserve_pct=0.0,
            existing_positions=(),
        )
        # Both with `books_by_token` AND with `books_by_token=None`:
        # `foreign_p1` must be accepted (`> $0` allocated), AND `foreign_p1 + p2` combined must NEVER exceed `15%` (`$7.305`)!
        res_b = opt.optimize_portfolio([foreign_p1, p2], books_by_token={"SAME_TOK_Y": bk_y, "SAME_TOK_N": bk_n})
        self.assertGreater(res_b.total_allocated_capital_usd, 0.0)
        self.assertLessEqual(res_b.total_allocated_capital_usd, 48.70 * 0.15 + 1e-4)

        res_nb = opt.optimize_portfolio([foreign_p1, p2], books_by_token=None)
        self.assertGreater(res_nb.total_allocated_capital_usd, 0.0)
        self.assertLessEqual(res_nb.total_allocated_capital_usd, 48.70 * 0.15 + 1e-4)

    def test_15_bug_mp3_tranche_gas_and_lockup_cost_deduction(self) -> None:
        from src.polymarket_research.detectors_microstructure_and_portfolio import _build_two_leg_ask_tranches

        verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=30.0,
                reconciled_nav_usd=100.0,
                default_relayer_gas_usd=0.08,
                settlement_gas_usd=0.05,
                lockup_opportunity_cost_bps_per_hour=10.0,
                now_ts=self.NOW_TS,
            )
        )
        bk_a = InstrumentOrderBook(
            "GAS_Y",
            market_id="m_gas",
            asks=(BookLevel(0.47, 20.0),),
            bids=(BookLevel(0.46, 20.0),),
            book_timestamp_sec=self.NOW_TS,
        )
        bk_b = InstrumentOrderBook(
            "GAS_N",
            market_id="m_gas",
            asks=(BookLevel(0.49, 20.0),),
            bids=(BookLevel(0.48, 20.0),),
            book_timestamp_sec=self.NOW_TS,
        )
        proof = verifier.verify_binary_complete_set(
            candidate_id="GAS_BOX_MP3",
            yes_book=bk_a,
            no_book=bk_b,
            merge_immediately=False,
            expected_lockup_hours=2.0,
            worst_case_lockup_hours=4.0,
        )
        self.assertGreater(proof.min_state_net_payoff_usd, 0.0)
        tranches = _build_two_leg_ask_tranches(
            bk_a,
            bk_b,
            max_shares=proof.optimal_executable_quantity,
            lockup_hours=4.0,
            proof=proof,
        )
        self.assertGreater(len(tranches), 0)
        sum_tr_min = sum(t.guaranteed_min_profit_usd for t in tranches)
        self.assertLessEqual(sum_tr_min, proof.min_state_net_payoff_usd + 1e-6)
        self.assertGreater(tranches[0].guaranteed_min_profit_usd, 0.0)

    def test_16_bug_mp4_cumulative_trailing_clause_and_description_divergence_blocked(self) -> None:
        scanner = MechanismAndStructureScanner(reconciled_nav_usd=48.70)
        events = [
            {
                "id": "ev_treaty_trap",
                "title": "Leader Visit Cumulative Strip",
                "cumulativeMarkets": True,
                "markets": [
                    {
                        "id": "m_visit_only",
                        "question": "Will Leader X visit Country Y by June 30, 2027?",
                        "endDate": "2027-06-30T23:59:00Z",
                        "clobTokenIds": json.dumps(["VIS_Y", "VIS_N"]),
                        "feesEnabled": False,
                    },
                    {
                        "id": "m_visit_plus_treaty",
                        "question": "Will Leader X visit Country Y by December 31, 2027 and sign a formal treaty?",
                        "endDate": "2027-12-31T23:59:00Z",
                        "clobTokenIds": json.dumps(["TRT_Y", "TRT_N"]),
                        "feesEnabled": False,
                    },
                ],
            },
            {
                "id": "ev_desc_div_trap",
                "title": "Bill Passage Strip",
                "cumulativeMarkets": True,
                "markets": [
                    {
                        "id": "m_bill_1",
                        "question": "Will Bill Z pass Congress by June 30, 2027?",
                        "description": "Resolves Yes if Bill Z passes House and Senate by June 30, 2027.",
                        "endDate": "2027-06-30T23:59:00Z",
                        "clobTokenIds": json.dumps(["BL1_Y", "BL1_N"]),
                        "feesEnabled": False,
                    },
                    {
                        "id": "m_bill_2",
                        "question": "Will Bill Z pass Congress by December 31, 2027?",
                        "description": "Resolves Yes if Bill Z passes House and Senate by December 31, 2027 AND survives judicial review.",
                        "endDate": "2027-12-31T23:59:00Z",
                        "clobTokenIds": json.dumps(["BL2_Y", "BL2_N"]),
                        "feesEnabled": False,
                    },
                ],
            },
        ]
        books = {
            t: _raw_book(t, bids=[(0.25, 30.0)], asks=[(0.26, 30.0)])
            for t in ("VIS_Y", "VIS_N", "TRT_Y", "TRT_N", "BL1_Y", "BL1_N", "BL2_Y", "BL2_N")
        }
        cands, _, _ = scanner.scan_universe_mechanisms(events, books, now_ts=self.NOW_TS)
        for c in cands:
            if c.sub_type == "N5_CUMULATIVE_EVENT_MONOTONE_LADDER":
                self.assertNotIn(
                    c.opportunity_class,
                    {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value},
                    msg=f"False N5 CLASS_A/B leak: {c.candidate_id}",
                )
        # Specifically verify `m_visit_only` + `m_visit_plus_treaty` were NOT paired at all!
        paired_ids = {c.candidate_id for c in cands}
        self.assertNotIn("FAM_N5_CUMULATIVE_m_visit_only_m_visit_plus_treaty", paired_ids)

    def test_17_wave2_certified_2leg_full_throttle_gate_and_rejections(self) -> None:
        import types
        from src.polymarket_research.stage_c_zero_loss_velocity import (
            FULL_THROTTLE_CERTIFIED_2LEG_SLEEVES,
            check_strict_pure_riskless_candidate_gate,
            is_verified_full_throttle_2leg_box,
        )

        harv = types.SimpleNamespace(
            enforce_pure_riskless_mode=True,
            enforce_multileg_3plus_nav_gate=True,
            dry_run=False,
            _last_known_collateral=48.70,
            active_positions={},
            pending_entry_intents={},
        )
        rb_cfg = {
            "strict_pure_riskless_mode": True,
            "enable_event_slot_diversification": True,
            "max_correlated_oracle_event_nav_pct": 0.15,
            "multileg_3plus_min_reconciled_nav_usd": 500.0,
            "certified_multileg_3plus_live_enabled": False,
        }
        tok1 = "1" * 24
        tok2 = "2" * 24
        opp1 = "3" * 24
        opp2 = "4" * 24

        base_2l = {
            "opportunity_class": "CLASS_A",
            "rule_verified": True,
            "min_state_net_payoff_usd": 0.18,
            "leg_count": 2,
            "box_cost_net": 0.982,
            "max_box_cost_net": 0.992,
            "leg_a_token_id": tok1,
            "leg_a_opp_token_id": opp1,
            "leg_a_market_id": "900101",
            "leg_a_condition_id": "0x" + "a" * 64,
            "leg_b_token_id": tok2,
            "leg_b_opp_token_id": opp2,
            "leg_b_market_id": "900102",
            "leg_b_condition_id": "0x" + "b" * 64,
        }
        sample_by_sleeve = {
            "C1_BINARY_COMPLETE_SET": {
                **base_2l,
                "box_type": "COMPLETE_SET",
                "sleeve_source": "C1_BINARY_COMPLETE_SET",
                "leg_b_market_id": "900101",
                "leg_b_condition_id": "0x" + "a" * 64,
            },
            "C1_SPLIT_AND_SELL_OVERROUND": {
                "box_type": "CTF_OVERROUND",
                "sleeve_source": "C1_SPLIT_AND_SELL_OVERROUND",
                "opportunity_class": "CLASS_A",
                "rule_verified": True,
                "min_state_net_payoff_usd": 0.14,
                "leg_count": 2,
                "condition_id": "0x" + "c" * 64,
                "leg_a_market_id": "900103",
                "yes_token_id": tok1,
                "no_token_id": tok2,
                "fee_rate": 0.02,
                "fee_exponent": 1.0,
            },
            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                **base_2l,
                "box_type": "DOMINANCE",
                "sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "k_low": 90000.0,
                "k_high": 90500.0,
            },
            "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": {
                **base_2l,
                "box_type": "LADDER_MONO",
                "sleeve_source": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                "opportunity_class": "CLASS_B",
                "leg_a_fee_rate": 0.02,
                "leg_b_fee_rate": 0.02,
            },
            "COND1_MACRO_PARTITION_BOX": {
                **base_2l,
                "box_type": "MACRO_DOMINANCE",
                "sleeve_source": "COND1_MACRO_PARTITION_BOX",
                "opportunity_class": "CLASS_B",
                "leg_a_fee_rate": 0.02,
                "leg_b_fee_rate": 0.02,
            },
            "NR2_2LEG_CONVERT_NO_SUBSET_ARB": {
                "box_type": "NEGRISK_CONVERT",
                "convert_mode": "NR2_PURE_CASH_CONVERT",
                "sleeve_source": "NR2_2LEG_CONVERT_NO_SUBSET_ARB",
                "opportunity_class": "CLASS_A",
                "rule_verified": True,
                "min_state_net_payoff_usd": 0.22,
                "leg_count": 2,
                "box_cost_net": 0.978,
                "neg_risk_market_id": "0x" + "d" * 64,
                "no_legs": [{"market_id": "900201", "token_id": tok1}, {"market_id": "900202", "token_id": tok2}],
            },
            "FT_DUP1_EXACT_CROSS_EVENT_BOX": {
                **base_2l,
                "box_type": "MACRO_DOMINANCE",
                "sleeve_source": "FT_DUP1_EXACT_CROSS_EVENT_BOX",
                "opportunity_class": "CLASS_B",
            },
            "FT_STRIKE1_VERIFIED_DOMINANCE_BOX": {
                **base_2l,
                "box_type": "LADDER_MONO",
                "sleeve_source": "FT_STRIKE1_VERIFIED_DOMINANCE_BOX",
                "opportunity_class": "CLASS_B",
                "k_low": 3.0,
                "k_high": 4.0,
            },
            "XV_SUBSET_NO_2LEG_BOX": {
                **base_2l,
                "box_type": "NEGRISK_2LEG",
                "sleeve_source": "XV_SUBSET_NO_2LEG_BOX",
                "opportunity_class": "CLASS_B",
            },
        }
        self.assertEqual(set(sample_by_sleeve.keys()), set(FULL_THROTTLE_CERTIFIED_2LEG_SLEEVES))
        for sl_nm, cand in sample_by_sleeve.items():
            self.assertTrue(is_verified_full_throttle_2leg_box(cand), msg=sl_nm)
            self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv, cand, rb_cfg), msg=sl_nm)

        # Rejections: unverified rule, non-positive floor, CLASS_C/D/E, >=3 legs < $500 NAV, KMIA D-001, >15% concentration
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                harv, {**sample_by_sleeve["FT_DUP1_EXACT_CROSS_EVENT_BOX"], "rule_verified": False}, rb_cfg
            )
        )
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                harv, {**sample_by_sleeve["FT_DUP1_EXACT_CROSS_EVENT_BOX"], "min_state_net_payoff_usd": 0.0}, rb_cfg
            )
        )
        for bad_cls in ("CLASS_C", "CLASS_D", "CLASS_E"):
            veto_c = check_strict_pure_riskless_candidate_gate(
                harv, {**sample_by_sleeve["FT_DUP1_EXACT_CROSS_EVENT_BOX"], "opportunity_class": bad_cls}, rb_cfg
            )
            self.assertIn("PURE_RISKLESS_OPPORTUNITY_CLASS_BLOCKED", str(veto_c))
        veto_3l = check_strict_pure_riskless_candidate_gate(
            harv,
            {
                **sample_by_sleeve["FT_DUP1_EXACT_CROSS_EVENT_BOX"],
                "leg_count": 3,
                "legs": [{"token_id": "a"}, {"token_id": "b"}, {"token_id": "c"}],
            },
            rb_cfg,
        )
        self.assertIn("BELOW_500_NAV", str(veto_3l))
        for kmia_mid in ("6707503", "6707502"):
            veto_k = check_strict_pure_riskless_candidate_gate(
                harv, {**sample_by_sleeve["FT_DUP1_EXACT_CROSS_EVENT_BOX"], "leg_a_market_id": kmia_mid}, rb_cfg
            )
            self.assertIn("D001_DISPUTED_KMIA_MARKET_BLOCKED", str(veto_k))

        # Event concentration cap (15% of $48.70 = $7.305 -> $4.00 open leaves $3.305 < $4.50 min headroom)
        harv_conc = types.SimpleNamespace(
            enforce_pure_riskless_mode=True,
            enforce_multileg_3plus_nav_gate=True,
            dry_run=False,
            _last_known_collateral=44.70,
            risk_config={"max_concurrent_per_event": 3},
            active_positions={
                "OPEN_EVT_1": {
                    "trade_id": "OPEN_EVT_1",
                    "status": "POSITION_CONFIRMED",
                    "event_id": "EVT_CONC_99",
                    "market_id": "900999",
                    "notional_usd": 4.00,
                }
            },
            pending_entry_intents={},
        )
        veto_conc = check_strict_pure_riskless_candidate_gate(
            harv_conc,
            {**sample_by_sleeve["FT_DUP1_EXACT_CROSS_EVENT_BOX"], "event_id": "EVT_CONC_99"},
            {**rb_cfg, "max_concurrent_per_event": 3},
        )
        self.assertIn(veto_conc, {"MAX_CONCURRENT_PER_EVENT_REACHED", "MAX_EVENT_NOTIONAL_CAP_REACHED"})

    def test_18_wave2_harvester_ft_execution_and_24h_lkg_cache_across_restart(self) -> None:
        import os as _os
        import tempfile
        import types
        from unittest.mock import patch
        from src.polymarket_research import polymarket_live_harvester as plh
        from src.polymarket_research.stage_c_zero_loss_velocity import load_alpha124_graduation_maps_with_lkg_cache

        now_u = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            st_f = tmp_p / "alpha124_shadow_state.json"
            st_f.write_text(
                json.dumps(
                    {
                        "by_sleeve": {
                            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                                "closed": 10,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 25.0,
                            }
                        },
                        "by_d1_asset": {"BTC": {"closed": 10, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 25.0}},
                    }
                ),
                encoding="utf-8",
            )
            h_warm = types.SimpleNamespace()
            sl_0, _, err_0 = load_alpha124_graduation_maps_with_lkg_cache(h_warm, tmp_p, tmp_p, now_ts=now_u)
            self.assertIsNone(err_0)
            self.assertIn("D1_SAME_ORACLE_DOMINANCE_BOX", sl_0 or {})
            self.assertTrue((tmp_p / "alpha124_graduation_lkg_cache.json").exists())

            # Cold Harvester restart while alpha124_shadow_state.json is mid-unlink/restart (<24h): LKG sidecar rescues!
            st_f.unlink()
            h_cold = types.SimpleNamespace()
            sl_1, _, err_1 = load_alpha124_graduation_maps_with_lkg_cache(h_cold, tmp_p, tmp_p, now_ts=now_u + 3600.0)
            self.assertIsNone(err_1)
            self.assertIn("D1_SAME_ORACLE_DOMINANCE_BOX", sl_1 or {})

            # Past 24h (>86,400s): MUST fail closed
            h_stale = types.SimpleNamespace()
            sl_exp, _, err_exp = load_alpha124_graduation_maps_with_lkg_cache(h_stale, tmp_p, tmp_p, now_ts=now_u + 90000.0)
            self.assertIsNone(sl_exp)
            self.assertEqual(err_exp, "NO_ALPHA124_STATE")

            # Execute certified 2-leg FT_DUP1 micro-clip ($6.00 on $48.70 cash) via maybe_execute_graduated_d1_box
            tok_a = "5" * 24
            tok_b = "6" * 24
            opp_a = "7" * 24
            opp_b = "8" * 24
            h = plh.PolymarketLiveHarvester(dry_run=True)
            h.dry_run = False
            h._startup_reconciled = True
            h._last_known_collateral = 48.70
            h.active_positions = {}
            h.closed_positions = []
            h.pending_entry_intents = {}
            h.executor.auth_mode = "LIVE"
            h.executor.get_collateral_balance = lambda: 48.70
            books = {
                tok_a: {"asks": [{"price": "0.48", "size": "15"}], "bids": [{"price": "0.47", "size": "15"}]},
                tok_b: {"asks": [{"price": "0.49", "size": "15"}], "bids": [{"price": "0.48", "size": "15"}]},
                opp_a: {"asks": [{"price": "0.53", "size": "15"}], "bids": [{"price": "0.51", "size": "15"}]},
                opp_b: {"asks": [{"price": "0.52", "size": "15"}], "bids": [{"price": "0.50", "size": "15"}]},
            }
            h.executor.get_market_book = lambda tid: books[tid]
            h.executor.execute_atomic_dominance_box = lambda **kw: {
                "success": True,
                "leg_1": {
                    "filled": True,
                    "orderID": "O1",
                    "token_id": kw["leg_a_token_id"],
                    "label": kw.get("leg_a_label", "LEG_A"),
                    "matched_shares": kw.get("leg_a_shares", kw["shares"]),
                    "shares": kw.get("leg_a_shares", kw["shares"]),
                    "price": kw["leg_a_limit_price"],
                    "fee_usd": 0.0,
                },
                "leg_2": {
                    "filled": True,
                    "orderID": "O2",
                    "token_id": kw["leg_b_token_id"],
                    "label": kw.get("leg_b_label", "LEG_B"),
                    "matched_shares": kw.get("leg_b_shares", kw["shares"]),
                    "shares": kw.get("leg_b_shares", kw["shares"]),
                    "price": kw["leg_b_limit_price"],
                    "fee_usd": 0.0,
                },
            }
            h._wallet_token_balance = lambda _t: (0.0, True)
            h.save_state = lambda *a, **kw: None
            cand_ft = {
                "box_id": "FT_DUP1_MICRO_CLIP_1",
                "dedupe_key": "FT_DUP1_MICRO_1",
                "box_type": "DOMINANCE_BOX",
                "sleeve_source": "FT_DUP1_EXACT_CROSS_EVENT_BOX",
                "opportunity_class": "CLASS_B",
                "rule_verified": True,
                "min_state_net_payoff_usd": 0.18,
                "leg_count": 2,
                "asset": "MACRO",
                "event_id": "EVT_FT_DUP1",
                "ts_unix": time.time(),
                "expiry_ts": time.time() + 14400.0,
                "shares": 6,
                "box_cost_net": 0.970,
                "max_box_cost_net": 0.992,
                "leg_a_token_id": tok_a,
                "leg_a_opp_token_id": opp_a,
                "leg_a_side": "YES",
                "leg_a_market_id": "910001",
                "leg_a_condition_id": "0x" + "1" * 64,
                "leg_a_limit_price": 0.48,
                "leg_a_fee_rate": 0.0,
                "leg_a_neg_risk": False,
                "leg_b_token_id": tok_b,
                "leg_b_opp_token_id": opp_b,
                "leg_b_side": "NO",
                "leg_b_market_id": "910002",
                "leg_b_condition_id": "0x" + "2" * 64,
                "leg_b_limit_price": 0.49,
                "leg_b_fee_rate": 0.0,
                "leg_b_neg_risk": False,
            }
            with patch.object(plh, "DATA_DIR", tmp_p), patch.object(plh, "PIPELINE_ROOT", tmp_p):
                out_exec = h.maybe_execute_graduated_d1_box(cand_ft)
            self.assertTrue(out_exec.get("executed"), msg=str(out_exec))

    def test_19_wave2_config_friction_removal_15bps_zerofee_24h_75bps_and_micro_clips(self) -> None:
        from src.polymarket_research.holistic_strategy_governance import (
            HotReloadConfigManager,
            passes_capital_velocity_hurdle,
        )
        from src.polymarket_research.riskless_protocol_v2_expansion import maybe_emit_recorder_fast_riskless_ipc

        cfg_path = REPO_ROOT / "config" / "polymarket_strategy_and_risk.json"
        mgr = HotReloadConfigManager(config_path=cfg_path)
        self.assertEqual(mgr.rejected_reload_count, 0)
        snap = mgr.snapshot
        self.assertTrue(snap["directional"]["riskless_only_mode"])
        rb = snap["riskless_boxes"]
        self.assertAlmostEqual(float(rb["zerofee1_min_net_edge_bps"]), 15.0, places=2)
        self.assertAlmostEqual(float(rb["seed_max_lockup_hours"]), 24.0, places=2)
        self.assertAlmostEqual(float(rb["seed_min_bps_per_hour"]), 7.5, places=2)
        self.assertEqual(int(rb["ws_clinch_watchlist_max_tokens"]), 900)

        # 16h lockup with 140 bps edge (8.75 bps/hr >= 7.5 bps/hr > 7.04 bps/hr Finland VM hurdle) passes!
        ok_16h, _ = passes_capital_velocity_hurdle(
            box_type="MACRO_DOMINANCE",
            sleeve_src="FT_DUP1_EXACT_CROSS_EVENT_BOX",
            collat_usd=48.70,
            rem_tte_sec=16.0 * 3600.0,
            box_cost_net=0.986,
            cfg=snap,
        )
        self.assertTrue(ok_16h)

        # 16h lockup with 96 bps edge (6.0 bps/hr < 7.5 bps/hr) fails!
        ok_slow, rsn_slow = passes_capital_velocity_hurdle(
            box_type="MACRO_DOMINANCE",
            sleeve_src="FT_DUP1_EXACT_CROSS_EVENT_BOX",
            collat_usd=48.70,
            rem_tte_sec=16.0 * 3600.0,
            box_cost_net=0.9904,
            cfg=snap,
        )
        self.assertFalse(ok_slow)
        self.assertIn("LOW_CAPITAL_VELOCITY_LONG_TTE", rsn_slow)

        # Micro-clip (6.0 shares @ $0.9980 = 20 bps >= 15 bps zero-fee C1) accepted by recorder fast IPC!
        import types

        now_r = time.time()
        rec_stub = types.SimpleNamespace(
            asset="XAU",
            current_market={"market_id": "998801", "condition_id": "0x" + "9" * 64, "end_dt": types.SimpleNamespace(timestamp=lambda: now_r + 600.0)},
            market_15m=None,
            market_5m=None,
        )
        snap_r = {
            "UP": {"token_id": "u" * 24, "best_ask": 0.499, "best_bid": 0.490, "ask_size_l1": 6.0, "age_book_ms": 20.0, "is_crossed": False},
            "DOWN": {"token_id": "d" * 24, "best_ask": 0.499, "best_bid": 0.490, "ask_size_l1": 6.0, "age_book_ms": 20.0, "is_crossed": False},
        }
        sink: list = []
        rec_stub._test_cand_sink = sink
        emitted_n = maybe_emit_recorder_fast_riskless_ipc(rec_stub, snap_r, now_ts=now_r)
        self.assertEqual(emitted_n, 1)
        self.assertGreaterEqual(int(sink[0]["shares"]), 5)

        # BUG-W2-MP-2 regression: sharded WS watchlist scales up to 900+ tokens while unsharded caps at <= 490
        from src.polymarket_research.riskless_protocol_v2_expansion import desired_market_ws_tokens_impl

        watch_600 = {
            f"tok_a_{i:04d}": {
                "leg_a_token_id": f"tok_a_{i:04d}",
                "leg_a_opp_token_id": f"tok_b_{i:04d}",
                "expiry_ts": now_r + 3600.0,
                "registered_ts": now_r,
            }
            for i in range(600)
        }
        harv_sharded = types.SimpleNamespace(
            active_positions={},
            pending_entry_intents={},
            _clinched_ws_watchlist=dict(watch_600),
            _pos_market_ws=types.SimpleNamespace(num_shards=4, max_tokens=1940),
        )
        toks_sharded = desired_market_ws_tokens_impl(harv_sharded, now_ts=now_r)
        self.assertGreaterEqual(len(toks_sharded), 900)
        harv_single = types.SimpleNamespace(
            active_positions={},
            pending_entry_intents={},
            _clinched_ws_watchlist=dict(watch_600),
            _pos_market_ws=types.SimpleNamespace(num_shards=1, max_tokens=490),
        )
        toks_single = desired_market_ws_tokens_impl(harv_single, now_ts=now_r)
        self.assertLessEqual(len(toks_single), 490)

    def test_20_wave2_zero_trust_permission_gate_envelope_and_diff_clean(self) -> None:
        import copy
        from src.paa_os.permissions import PermissionGate

        cfg_path = REPO_ROOT / "config" / "polymarket_strategy_and_risk.json"
        cand_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        base_cfg = copy.deepcopy(cand_cfg)
        base_cfg["riskless_boxes"]["zerofee1_min_net_edge_bps"] = 45.0
        base_cfg["riskless_boxes"]["seed_max_lockup_hours"] = 8.0
        base_cfg["riskless_boxes"]["seed_min_bps_per_hour"] = 15.0
        base_cfg["riskless_boxes"]["ws_clinch_watchlist_max_tokens"] = 450

        gate = PermissionGate()
        env_ok, env_viol = gate.inspect_config_envelope(base_cfg, cand_cfg)
        self.assertEqual((env_ok, env_viol), (True, []))

        owned_files = [
            "src/polymarket_research/polymarket_live_harvester.py",
            "src/polymarket_research/stage_c_zero_loss_velocity.py",
            "src/polymarket_research/riskless_protocol_v2_expansion.py",
            "src/polymarket_research/holistic_strategy_governance.py",
            "config/polymarket_strategy_and_risk.json",
        ]
        diff_ok, diff_viol = gate.inspect_candidate_diff(
            owned_files, "", baseline_cfg=base_cfg, candidate_cfg=cand_cfg
        )
        self.assertEqual((diff_ok, diff_viol), (True, []))

    def test_21_bug_w2_mp_3a_and_3b_inventory_sll_and_bond1_r02_reachability(self) -> None:
        import types
        from src.polymarket_research.stage_c_zero_loss_velocity import (
            check_strict_pure_riskless_candidate_gate,
            is_verified_full_throttle_2leg_box,
        )

        rb_cfg = {"strict_pure_riskless_mode": True}
        tok_buy = "1" * 24
        tok_opp = "2" * 24
        fam_j_sll = {
            "box_type": "SINGLE_LEG_LOCK",
            "sleeve_source": "C1_BINARY_COMPLETE_SET",
            "full_throttle_bridge": True,
            "opportunity_class": "CLASS_A",
            "rule_verified": True,
            "min_state_net_payoff_usd": 0.24,
            "leg_count": 1,
            "shares": 8.0,
            "box_cost_net": 0.47,
            "verified_wallet_inventory": {tok_opp: 8.0},
            "leg_a_token_id": tok_buy,
            "leg_a_opp_token_id": tok_opp,
            "leg_a_market_id": "920101",
            "leg_a_condition_id": "0x" + "f" * 64,
        }
        self.assertTrue(is_verified_full_throttle_2leg_box(fam_j_sll))

        # Spoofed wallet inventory (0 on-chain & 0 active_positions) MUST be blocked
        harv_empty = types.SimpleNamespace(
            enforce_pure_riskless_mode=True,
            dry_run=False,
            _last_known_collateral=48.70,
            active_positions={},
            pending_entry_intents={},
            executor=types.SimpleNamespace(get_onchain_erc1155_balance=lambda _tid: 0.0),
        )
        veto_spoof = check_strict_pure_riskless_candidate_gate(harv_empty, fam_j_sll, rb_cfg)
        self.assertIn("PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY", str(veto_spoof))

        # Executor-verified ERC-1155 wallet inventory >= shares passes cleanly
        harv_verified = types.SimpleNamespace(
            enforce_pure_riskless_mode=True,
            dry_run=False,
            _last_known_collateral=48.70,
            active_positions={},
            pending_entry_intents={},
            executor=types.SimpleNamespace(
                get_onchain_erc1155_balance=lambda tid: 8.0 if tid == tok_opp else 0.0
            ),
        )
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv_verified, fam_j_sll, rb_cfg))

        # BUG-W2-MP-3B: BOND1 carrying rule_verified=True AND novel R-02 state-space proven candidate remain reachable!
        bond1_cand = {
            "box_type": "SINGLE_LEG_LOCK",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "rule_verified": True,
            "p_model": 0.999,
            "box_cost_net": 0.992,
            "leg_a_token_id": tok_buy,
            "leg_a_opp_token_id": tok_opp,
            "leg_a_market_id": "920102",
        }
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv_empty, bond1_cand, rb_cfg))

        r02_novel = {
            "box_type": "MACRO_DOMINANCE",
            "sleeve_source": "R02_CUSTOM_STATE_SPACE_PROVEN_BOX",
            "opportunity_class": "CLASS_B",
            "rule_verified": True,
            "min_state_net_payoff_usd": 0.30,
            "box_cost_net": 0.970,
            "leg_a_token_id": tok_buy,
            "leg_a_market_id": "920201",
            "leg_b_token_id": tok_opp,
            "leg_b_market_id": "920202",
        }
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv_empty, r02_novel, rb_cfg))


if __name__ == "__main__":
    unittest.main()

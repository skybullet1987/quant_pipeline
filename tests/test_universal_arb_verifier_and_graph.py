"""
Comprehensive Unit & Adversarial Proof-Breaking Suite for:
  - `src/polymarket_research/universal_arb_verifier.py` (Sections 5 & 6)
  - `src/polymarket_research/market_proposition_graph.py` (Section 7)

Run locally on Windows via:
  & "C:\\Program Files\\LibreOffice\\program\\python.exe" -m unittest tests/test_universal_arb_verifier_and_graph.py -v
"""

from __future__ import annotations

import json
import time
import unittest

from src.polymarket_research.market_proposition_graph import (
    EdgeType,
    MarketPropositionGraph,
    PropositionEdge,
    RelationKind,
    ResolutionSpec,
)
from src.polymarket_research.universal_arb_verifier import (
    ActionLeg,
    ActionType,
    BookLevel,
    CandidateStructure,
    FROZEN_DISPUTED_MARKET_IDS,
    InstrumentOrderBook,
    InventoryHolding,
    OpportunityClass,
    StateSpaceBuilder,
    StateSpec,
    UniversalArbVerifier,
    VerificationConfig,
    compute_net_buy_cost_per_delivered_share,
    compute_net_sell_proceeds_per_share,
    compute_polymarket_taker_fee_per_gross_share,
    compute_v2_buy_share_haircut_frac,
    infer_polymarket_tick_size,
    normalize_fee_rate,
    quantize_clob_fok_order,
    quantize_polymarket_price,
)


class TestPolymarketMicrostructureMath(unittest.TestCase):
    """Tests exact Polymarket fee curves, Protocol V2 share haircuts, ticks, and lot constraints."""

    def test_zero_bps_and_dynamic_parabolic_fee_curve(self) -> None:
        self.assertEqual(normalize_fee_rate(fee_rate_bps=0.0), 0.0)
        self.assertAlmostEqual(normalize_fee_rate(fee_rate_bps=175.0), 0.0175, places=8)
        self.assertAlmostEqual(normalize_fee_rate(fee_rate=700.0), 0.07, places=8)
        self.assertAlmostEqual(normalize_fee_rate(fee_rate=0.07), 0.07, places=8)

        # 0-bps market has zero taker fee and zero share haircut everywhere
        self.assertEqual(compute_polymarket_taker_fee_per_gross_share(0.50, fee_rate_bps=0.0), 0.0)
        self.assertEqual(compute_v2_buy_share_haircut_frac(0.50, fee_rate_bps=0.0), 0.0)

        # Parabolic fee curve r * p * (1 - p) peaks at p = 0.50 and shrinks in tails
        fee_mid = compute_polymarket_taker_fee_per_gross_share(0.50, fee_rate_bps=700.0, fee_exponent=1.0)
        fee_tail = compute_polymarket_taker_fee_per_gross_share(0.05, fee_rate_bps=700.0, fee_exponent=1.0)
        self.assertAlmostEqual(fee_mid, 0.07 * 0.25, places=8)
        self.assertAlmostEqual(fee_tail, 0.07 * 0.05 * 0.95, places=8)
        self.assertGreater(fee_mid, fee_tail * 5.0)

        # Maker orders pay 0% taker fee
        self.assertEqual(
            compute_polymarket_taker_fee_per_gross_share(0.50, fee_rate_bps=700.0, is_maker=True),
            0.0,
        )

    def test_protocol_v2_share_haircut_exceeds_naive_additive_fee(self) -> None:
        # At p = 0.50, r = 700 bps (0.07): h(0.50) = 0.0175 / 0.50 = 0.035
        # Delivering 1.0 net share requires 1 / (1 - 0.035) = 1.03626943 gross shares,
        # costing 0.50 / 0.965 = $0.518134715 > naive additive $0.5175!
        h = compute_v2_buy_share_haircut_frac(0.50, fee_rate_bps=700.0)
        self.assertAlmostEqual(h, 0.035, places=8)
        tot_v2, pure_v2, fee_v2 = compute_net_buy_cost_per_delivered_share(
            0.50,
            fee_rate_bps=700.0,
            fee_deduction_mode="V2_SHARE_HAIRCUT",
        )
        tot_add, _, _ = compute_net_buy_cost_per_delivered_share(
            0.50,
            fee_rate_bps=700.0,
            fee_deduction_mode="USDC_ADDITIVE",
        )
        self.assertAlmostEqual(pure_v2, 0.50, places=8)
        self.assertAlmostEqual(tot_v2, 0.50 / 0.965, places=8)
        self.assertAlmostEqual(fee_v2, tot_v2 - 0.50, places=8)
        self.assertGreater(tot_v2, tot_add)

        # Taker sell deducts fee from cash proceeds
        net_sell, gross_sell, sell_fee = compute_net_sell_proceeds_per_share(0.50, fee_rate_bps=700.0)
        self.assertAlmostEqual(gross_sell, 0.50, places=8)
        self.assertAlmostEqual(sell_fee, 0.0175, places=8)
        self.assertAlmostEqual(net_sell, 0.4825, places=8)

    def test_tick_boundaries_and_order_quantization(self) -> None:
        # Exact inclusive boundary check at p = 0.04 and p = 0.96 -> 0.001 tick
        self.assertEqual(infer_polymarket_tick_size(0.04), 0.001)
        self.assertEqual(infer_polymarket_tick_size(0.96), 0.001)
        self.assertEqual(infer_polymarket_tick_size(0.005), 0.001)
        self.assertEqual(infer_polymarket_tick_size(0.992), 0.001)
        self.assertEqual(infer_polymarket_tick_size(0.041), 0.01)
        self.assertEqual(infer_polymarket_tick_size(0.959), 0.01)

        # Taker BUY rounds UP; Taker SELL rounds DOWN
        q_buy, t_buy = quantize_polymarket_price(0.423, "BUY", is_maker=False)
        q_sell, t_sell = quantize_polymarket_price(0.428, "SELL", is_maker=False)
        self.assertEqual((q_buy, t_buy), (0.43, 0.01))
        self.assertEqual((q_sell, t_sell), (0.42, 0.01))

        # $1.00 minimum marketable buy notional rejection on sub-$1 tail buy (10 sh @ $0.05 = $0.50 < $1.00)
        sub_notional = quantize_clob_fok_order(10.0, 0.05, side="BUY", min_order_size=5.0)
        self.assertFalse(sub_notional["valid"])
        self.assertEqual(sub_notional["reason"], "BELOW_MIN_MARKETABLE_BUY_NOTIONAL_USD")

        # Valid 25-share buy @ $0.05 = $1.25 >= $1.00 and >= 15 min_order_size
        ok_order = quantize_clob_fok_order(25.0, 0.05, side="BUY", min_order_size=15.0)
        self.assertTrue(ok_order["valid"])
        self.assertGreaterEqual(ok_order["maker_amount_usd"], 1.25)


class TestDepthAwareL2SimulatorAndFiveTierVerifier(unittest.TestCase):
    """Tests L2 marginal depth walking (`q*`), 4-value separation, edge states, and `CLASS_A..E`."""

    def setUp(self) -> None:
        self.now_ts = 1_794_400_000.0
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=100.0,
                reconciled_nav_usd=48.70,
                now_ts=self.now_ts,
                max_book_age_sec=120.0,
            )
        )

    def test_l2_marginal_depth_walk_stops_at_exact_optimal_rung(self) -> None:
        # YES asks: 10 @ 0.46, 15 @ 0.48, 50 @ 0.53
        # NO asks:  25 @ 0.49, 50 @ 0.52
        # Rung 1 (0..10):  cost 0.46 + 0.49 = 0.95 -> marginal +$0.05/sh (+$0.50)
        # Rung 2 (10..25): cost 0.48 + 0.49 = 0.97 -> marginal +$0.03/sh (+$0.45; cumulative +$0.95)
        # Rung 3 (>25):    cost 0.53 + 0.52 = 1.05 -> marginal -$0.05/sh (DILUTIVE!)
        yes_bk = InstrumentOrderBook(
            instrument_id="YES_M1",
            market_id="M1",
            asks=(BookLevel(0.46, 10.0), BookLevel(0.48, 15.0), BookLevel(0.53, 50.0)),
            bids=(BookLevel(0.44, 30.0),),
            fee_rate_bps=0.0,
            book_timestamp_sec=self.now_ts - 5.0,
        )
        no_bk = InstrumentOrderBook(
            instrument_id="NO_M1",
            market_id="M1",
            asks=(BookLevel(0.49, 25.0), BookLevel(0.52, 50.0)),
            bids=(BookLevel(0.47, 30.0),),
            fee_rate_bps=0.0,
            book_timestamp_sec=self.now_ts - 5.0,
        )
        proof = self.verifier.verify_binary_complete_set(
            candidate_id="TEST_L2_MARGINAL_OPT",
            yes_book=yes_bk,
            no_book=no_bk,
            direction="BUY_AND_MERGE",
            merge_immediately=True,
        )
        self.assertEqual(proof.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertTrue(proof.is_mathematically_proven_arb)
        self.assertFalse(proof.is_atomic_or_prelocked)
        self.assertAlmostEqual(proof.optimal_executable_quantity, 25.0, places=4)
        self.assertAlmostEqual(proof.min_state_net_payoff_usd, 0.95, places=5)

        # 4-value tracking strictly ordered: theoretical_top_of_book > executable_l2 > attainable_risk_adjusted, realized == 0
        fv = proof.four_value_ledger
        self.assertAlmostEqual(fv.theoretical_top_of_book_usd, 1.25, places=5)  # 25 * (1 - 0.95)
        self.assertAlmostEqual(fv.executable_l2_net_usd, 0.95, places=5)
        self.assertLess(fv.attainable_risk_adjusted_usd, fv.executable_l2_net_usd)
        self.assertGreater(fv.attainable_risk_adjusted_usd, 0.0)
        self.assertEqual(fv.realized_net_usd, 0.0)

        # Determinism check: re-running produces identical SHA-256 digest
        proof_repeat = self.verifier.verify_binary_complete_set(
            candidate_id="TEST_L2_MARGINAL_OPT",
            yes_book=yes_bk,
            no_book=no_bk,
            direction="BUY_AND_MERGE",
            merge_immediately=True,
        )
        self.assertEqual(proof.proof_sha256, proof_repeat.proof_sha256)
        self.assertEqual(len(proof.proof_sha256), 64)

    def test_budget_constrained_binary_search_inside_wide_rung(self) -> None:
        tight_verifier = UniversalArbVerifier(
            VerificationConfig(max_budget_usd=9.50, reconciled_nav_usd=48.70, now_ts=self.now_ts)
        )
        yes_bk = InstrumentOrderBook(
            instrument_id="YES_B",
            market_id="MB",
            asks=(BookLevel(0.45, 100.0),),
            bids=(BookLevel(0.44, 100.0),),
            book_timestamp_sec=self.now_ts,
        )
        no_bk = InstrumentOrderBook(
            instrument_id="NO_B",
            market_id="MB",
            asks=(BookLevel(0.50, 100.0),),
            bids=(BookLevel(0.49, 100.0),),
            book_timestamp_sec=self.now_ts,
        )
        # Unit cost = $0.95 -> $9.50 budget buys exactly 10.00 bundles for +$0.50 net profit
        proof = tight_verifier.verify_binary_complete_set(
            candidate_id="TEST_BUDGET_CAP",
            yes_book=yes_bk,
            no_book=no_bk,
        )
        self.assertEqual(proof.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertAlmostEqual(proof.optimal_executable_quantity, 10.0, places=2)
        self.assertAlmostEqual(proof.cost_breakdown.capital_required_usd, 9.50, places=2)
        self.assertAlmostEqual(proof.min_state_net_payoff_usd, 0.50, places=4)

    def test_class_a_inventory_completion_and_atomic_negrisk_convert(self) -> None:
        # Case 1: Pre-held YES inventory (mark_bid=0.44) + 1-leg FOK BUY NO @ 0.51 + immediate CTF_MERGE
        # Total economic cost = 0.44 + 0.51 = 0.95 < 1.00, only 1 CLOB leg -> CLASS_A!
        holding = InventoryHolding(
            instrument_id="YES_INV",
            shares=20.0,
            market_id="M_CLEAN",
            cost_basis_per_share=0.45,
            mark_bid_per_share=0.44,
            uma_resolution_status="none",
        )
        held_bk = InstrumentOrderBook(
            instrument_id="YES_INV",
            market_id="M_CLEAN",
            asks=(BookLevel(0.47, 50.0),),
            bids=(BookLevel(0.44, 50.0),),
            book_timestamp_sec=self.now_ts,
        )
        comp_bk = InstrumentOrderBook(
            instrument_id="NO_INV",
            market_id="M_CLEAN",
            asks=(BookLevel(0.51, 30.0),),
            bids=(BookLevel(0.49, 30.0),),
            book_timestamp_sec=self.now_ts,
        )
        proof_inv = self.verifier.verify_inventory_completion(
            candidate_id="TEST_CLASS_A_INV",
            holding=holding,
            held_book=held_bk,
            complement_book=comp_bk,
            merge_immediately=True,
        )
        self.assertEqual(proof_inv.opportunity_class, OpportunityClass.CLASS_A.value)
        self.assertTrue(proof_inv.is_atomic_or_prelocked)
        self.assertAlmostEqual(proof_inv.optimal_executable_quantity, 20.0, places=4)
        self.assertAlmostEqual(proof_inv.min_state_net_payoff_usd, 1.00, places=5)
        self.assertIn("VENUE_CUSTODY_AND_SMART_CONTRACT", proof_inv.residual_risks)

        # Case 2: Pure atomic on-chain NEGRISK_CONVERT of 3 pre-held NO tokens across an exhaustive 3-outcome slate
        outcomes = [
            {"yes_token_id": "Y1", "no_token_id": "N1", "label": "Cand1"},
            {"yes_token_id": "Y2", "no_token_id": "N2", "label": "Cand2"},
            {"yes_token_id": "Y3", "no_token_id": "N3", "label": "Cand3"},
        ]
        states = StateSpaceBuilder.multi_outcome_partition_states(
            outcomes, is_mutually_exclusive=True, is_exhaustive=True, is_negrisk=True
        )
        # Burn N1, N2, N3 (m=3) with 100 bps (1%) conversion fee -> releases (3-1)*(1-0.01) = $1.98 net cash!
        # Opportunity cost of N1, N2, N3 = 0.60 * 3 = $1.80 -> +$0.18/unit guaranteed atomic profit!
        cand_conv = CandidateStructure(
            candidate_id="TEST_ATOMIC_CONVERT",
            family="C",
            legs=(
                ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id="N1"),
                ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id="N2"),
                ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id="N3"),
                ActionLeg(
                    action_type=ActionType.NEGRISK_CONVERT,
                    burned_no_instrument_ids=("N1", "N2", "N3"),
                    minted_yes_instrument_ids=(),
                    negrisk_fee_bips=100,
                    gas_cost_usd=0.02,
                ),
            ),
            states=states,
            requires_exhaustive_partition=True,
            is_exhaustive_partition=True,
            is_mutually_exclusive=True,
        )
        inv_map = {
            "N1": InventoryHolding("N1", 10.0, mark_bid_per_share=0.60),
            "N2": InventoryHolding("N2", 10.0, mark_bid_per_share=0.60),
            "N3": InventoryHolding("N3", 10.0, mark_bid_per_share=0.60),
        }
        proof_conv = self.verifier.verify_and_simulate(cand_conv, {}, holdings=inv_map)
        self.assertEqual(proof_conv.opportunity_class, OpportunityClass.CLASS_A.value)
        self.assertTrue(proof_conv.is_atomic_or_prelocked)
        # 10 units * ($2.00 gross - $0.02 conv fee - $1.80 inv basis) - $0.02 gas = $1.78
        self.assertAlmostEqual(proof_conv.min_state_net_payoff_usd, 1.78, places=5)
        self.assertAlmostEqual(proof_conv.cost_breakdown.conversion_costs_usd, 0.20, places=5)

    def test_split_and_sell_and_d007_three_leg_quarantine_stay_class_b(self) -> None:
        # Split $1.00 into YES + NO and sell into bids 0.54 + 0.50 = $1.04 -> CLASS_B (never CLASS_A!)
        yes_bk = InstrumentOrderBook(
            instrument_id="Y_OV",
            market_id="M_OV",
            asks=(BookLevel(0.56, 20.0),),
            bids=(BookLevel(0.54, 20.0),),
            book_timestamp_sec=self.now_ts,
        )
        no_bk = InstrumentOrderBook(
            instrument_id="N_OV",
            market_id="M_OV",
            asks=(BookLevel(0.52, 20.0),),
            bids=(BookLevel(0.50, 20.0),),
            book_timestamp_sec=self.now_ts,
        )
        proof_split = self.verifier.verify_binary_complete_set(
            candidate_id="TEST_SPLIT_SELL",
            yes_book=yes_bk,
            no_book=no_bk,
            direction="SPLIT_AND_SELL",
        )
        self.assertEqual(proof_split.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertFalse(proof_split.is_atomic_or_prelocked)
        self.assertAlmostEqual(proof_split.min_state_net_payoff_usd, 0.80, places=5)  # 20 * 0.04

        # 3-leg sequential CLOB complete-set at $48.70 NAV (< $500) triggers D-007 quarantine!
        outcomes = [
            {"yes_token_id": "Y_A", "no_token_id": "N_A", "label": "A"},
            {"yes_token_id": "Y_B", "no_token_id": "N_B", "label": "B"},
            {"yes_token_id": "Y_C", "no_token_id": "N_C", "label": "C"},
        ]
        states_3 = StateSpaceBuilder.multi_outcome_partition_states(outcomes, is_negrisk=True)
        books_3 = {
            tid: InstrumentOrderBook(
                instrument_id=tid,
                market_id=f"M_{tid}",
                asks=(BookLevel(0.31, 20.0),),
                bids=(BookLevel(0.29, 20.0),),
                book_timestamp_sec=self.now_ts,
            )
            for tid in ("Y_A", "Y_B", "Y_C")
        }
        cand_3 = CandidateStructure(
            candidate_id="TEST_3LEG_D007",
            family="B",
            legs=tuple(ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=t) for t in ("Y_A", "Y_B", "Y_C")),
            states=states_3,
            requires_exhaustive_partition=True,
        )
        proof_3_seed = self.verifier.verify_and_simulate(cand_3, books_3)
        self.assertEqual(proof_3_seed.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertTrue(proof_3_seed.d007_sub500_multileg_quarantine)
        self.assertEqual(proof_3_seed.execution_mode_cap, "MODE_2_SHADOW")

        high_nav_verifier = UniversalArbVerifier(
            VerificationConfig(max_budget_usd=100.0, reconciled_nav_usd=600.0, now_ts=self.now_ts)
        )
        proof_3_high = high_nav_verifier.verify_and_simulate(cand_3, books_3)
        self.assertFalse(proof_3_high.d007_sub500_multileg_quarantine)

    def test_class_c_uma_proposed_carry_and_passive_maker_never_promoted(self) -> None:
        # Unfinalized UMA `proposed` bond at $0.98 with 1% dispute flip -> EV > 0, min_state < 0 -> CLASS_C!
        uma_bk = InstrumentOrderBook(
            instrument_id="YES_UMA",
            market_id="M_UMA",
            asks=(BookLevel(0.98, 25.0),),
            bids=(BookLevel(0.97, 25.0),),
            book_timestamp_sec=self.now_ts,
        )
        proof_uma = self.verifier.verify_uma_carry(
            candidate_id="TEST_UMA_PROPOSED",
            book=uma_bk,
            uma_status="proposed",
            p_dispute_flip=0.005,
        )
        self.assertEqual(proof_uma.opportunity_class, OpportunityClass.CLASS_C.value)
        self.assertFalse(proof_uma.is_mathematically_proven_arb)
        self.assertLess(proof_uma.min_state_net_payoff_usd, -20.0)
        self.assertGreater(proof_uma.expected_net_payoff_usd, 0.0)
        self.assertIn("UNFINALIZED_UMA_PROPOSAL_CARRY_NOT_CLASS_A_OR_B", proof_uma.disqualifiers)

        # Passive maker leg even on complete set -> CLASS_C (never CLASS_A or CLASS_B)
        yes_bk = InstrumentOrderBook(
            instrument_id="YM",
            market_id="MM",
            asks=(BookLevel(0.49, 20.0),),
            bids=(BookLevel(0.46, 20.0),),
            book_timestamp_sec=self.now_ts,
        )
        no_bk = InstrumentOrderBook(
            instrument_id="NM",
            market_id="MM",
            asks=(BookLevel(0.50, 20.0),),
            bids=(BookLevel(0.47, 20.0),),
            book_timestamp_sec=self.now_ts,
        )
        cand_maker = CandidateStructure(
            candidate_id="TEST_PASSIVE_MAKER",
            family="L",
            legs=(
                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="YM", is_maker=True, maker_price=0.46),
                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="NM", is_maker=False),
            ),
            states=StateSpaceBuilder.binary_complete_set_states("YM", "NM"),
        )
        proof_maker = self.verifier.verify_and_simulate(cand_maker, {"YM": yes_bk, "NM": no_bk})
        self.assertEqual(proof_maker.opportunity_class, OpportunityClass.CLASS_C.value)
        self.assertIn("PASSIVE_MAKER_FILL_UNCERTAINTY_NOT_CLASS_A_OR_B", proof_maker.disqualifiers)

    def test_class_d_disqualifiers_augmented_placeholder_rule_mismatches_and_stale_crossed_books(self) -> None:
        ya = InstrumentOrderBook("YA", "MA", asks=(BookLevel(0.40, 20.0),), bids=(BookLevel(0.38, 20.0),), book_timestamp_sec=self.now_ts)
        na = InstrumentOrderBook("NA", "MA", asks=(BookLevel(0.45, 20.0),), bids=(BookLevel(0.43, 20.0),), book_timestamp_sec=self.now_ts)
        yb = InstrumentOrderBook("YB", "MB", asks=(BookLevel(0.45, 20.0),), bids=(BookLevel(0.43, 20.0),), book_timestamp_sec=self.now_ts)
        nb = InstrumentOrderBook("NB", "MB", asks=(BookLevel(0.57, 20.0),), bids=(BookLevel(0.55, 20.0),), book_timestamp_sec=self.now_ts)

        # 1. Valid proven A => B (`NO_A + YES_B` = 0.45 + 0.45 = 0.90 <= $1.00 in all states incl. 50-50 void!) -> CLASS_B
        proof_valid = self.verifier.verify_logical_implication_pair(
            candidate_id="VALID_IMP",
            family="D",
            yes_book_a=ya,
            no_book_a=na,
            yes_book_b=yb,
            no_book_b=nb,
            relation="A_IMPLIES_B",
        )
        self.assertEqual(proof_valid.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertAlmostEqual(proof_valid.min_state_net_payoff_usd, 2.00, places=4)  # 20 * $0.10

        # 2. Sports 90-minute regulation vs overtime mismatch -> CLASS_D with counterexample state!
        proof_ot = self.verifier.verify_logical_implication_pair(
            candidate_id="OT_MISMATCH",
            family="H",
            yes_book_a=ya,
            no_book_a=na,
            yes_book_b=yb,
            no_book_b=nb,
            relation="A_IMPLIES_B",
            has_overtime_mismatch=True,
        )
        self.assertEqual(proof_ot.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertEqual(proof_ot.four_value_ledger.executable_l2_net_usd, 0.0)
        self.assertEqual(proof_ot.four_value_ledger.attainable_risk_adjusted_usd, 0.0)
        self.assertTrue(any("OMEGA_OVERTIME_MISMATCH_A1_B0" in c for c in proof_ot.counterexample_states))

        # 3. Touch-anytime vs close-at-cutoff mismatch -> CLASS_D
        proof_touch = self.verifier.verify_logical_implication_pair(
            candidate_id="TOUCH_CLOSE_MISMATCH",
            family="F",
            yes_book_a=ya,
            no_book_a=na,
            yes_book_b=yb,
            no_book_b=nb,
            relation="A_IMPLIES_B",
            touch_vs_close_mismatch=True,
        )
        self.assertEqual(proof_touch.opportunity_class, OpportunityClass.CLASS_D.value)

        # 4. Non-exhaustive multi-outcome set + augmented placeholder risk -> CLASS_D
        outcomes_inc = [
            {"yes_token_id": "YI1", "no_token_id": "NI1", "label": "Cand1"},
            {"yes_token_id": "YI2", "no_token_id": "NI2", "label": "Person A", "is_placeholder": True},
        ]
        states_inc = StateSpaceBuilder.multi_outcome_partition_states(
            outcomes_inc,
            is_exhaustive=False,
            is_negrisk=True,
            is_augmented_negrisk=True,
            has_unnamed_placeholder=True,
            has_other_outcome=False,
        )
        cand_inc = CandidateStructure(
            candidate_id="AUG_PLACEHOLDER",
            family="B",
            legs=(
                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="YI1"),
                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="YI2"),
            ),
            states=states_inc,
            requires_exhaustive_partition=True,
            is_exhaustive_partition=False,
            has_augmented_placeholder_risk=True,
        )
        bks_inc = {
            "YI1": InstrumentOrderBook("YI1", "MI1", asks=(BookLevel(0.40, 20.0),), book_timestamp_sec=self.now_ts),
            "YI2": InstrumentOrderBook("YI2", "MI2", asks=(BookLevel(0.40, 20.0),), is_placeholder=True, book_timestamp_sec=self.now_ts),
        }
        proof_inc = self.verifier.verify_and_simulate(cand_inc, bks_inc)
        self.assertEqual(proof_inc.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("NON_EXHAUSTIVE_MULTI_OUTCOME_SET", proof_inc.disqualifiers)
        self.assertIn("AUGMENTED_NEGRISK_PLACEHOLDER_HAZARD", proof_inc.disqualifiers)

        # 5. Stale book & crossed book -> CLASS_D
        stale_yes = InstrumentOrderBook("YS", "MS", asks=(BookLevel(0.45, 20.0),), book_timestamp_sec=self.now_ts - 600.0)
        fresh_no = InstrumentOrderBook("NS", "MS", asks=(BookLevel(0.45, 20.0),), book_timestamp_sec=self.now_ts)
        proof_stale = self.verifier.verify_binary_complete_set(
            candidate_id="STALE_BK", yes_book=stale_yes, no_book=fresh_no
        )
        self.assertEqual(proof_stale.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("STALE_ORDER_BOOK:YS", proof_stale.disqualifiers)

        crossed_yes = InstrumentOrderBook(
            "YC", "MC", asks=(BookLevel(0.45, 20.0),), bids=(BookLevel(0.46, 20.0),), book_timestamp_sec=self.now_ts
        )
        proof_crossed = self.verifier.verify_binary_complete_set(
            candidate_id="CROSSED_BK", yes_book=crossed_yes, no_book=fresh_no
        )
        self.assertEqual(proof_crossed.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("CROSSED_OR_INVALID_BOOK:YC", proof_crossed.disqualifiers)

    def test_adversarial_traps_converse_implication_standalone_void_and_d001_kmia_veto(self) -> None:
        # Trap 1: Converse implication error — buying YES_A + NO_B when A => B loses 100% in valid state (A=0, B=1)!
        ya = InstrumentOrderBook("YA", "MA", asks=(BookLevel(0.35, 20.0),), book_timestamp_sec=self.now_ts)
        na = InstrumentOrderBook("NA", "MA", asks=(BookLevel(0.67, 20.0),), book_timestamp_sec=self.now_ts)
        yb = InstrumentOrderBook("YB", "MB", asks=(BookLevel(0.67, 20.0),), book_timestamp_sec=self.now_ts)
        nb = InstrumentOrderBook("NB", "MB", asks=(BookLevel(0.35, 20.0),), book_timestamp_sec=self.now_ts)
        proof_converse = self.verifier.verify_logical_implication_pair(
            candidate_id="WRONG_CONVERSE_LEG_DIRECTION",
            family="D",
            yes_book_a=ya,
            no_book_a=na,
            yes_book_b=yb,
            no_book_b=nb,
            relation="A_IMPLIES_B",
            buy_legs=(("YA", 1.0), ("NB", 1.0)),  # BUGGY legs: pays $0 in OMEGA_A0_B1!
        )
        self.assertNotIn(
            proof_converse.opportunity_class,
            (OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value),
        )
        self.assertLess(proof_converse.min_state_net_payoff_usd, 0.0)
        self.assertTrue(any("OMEGA_A0_B1" in c for c in proof_converse.counterexample_states))

        # Trap 2: Standalone 4-outcome multi-NO 50-50 void cancellation loss!
        # Buying 4 standalone (non-NegRisk) NO tokens @ $0.70 each costs $2.80.
        # If an outcome wins, 3 NOs pay $3.00 (+$0.20), BUT if the event cancels 50-50, 4 * $0.50 = $2.00 (-$0.80 loss!).
        outs_4 = [{"yes_token_id": f"Y_{i}", "no_token_id": f"N_{i}", "label": f"Opt{i}"} for i in range(4)]
        states_standalone = StateSpaceBuilder.multi_outcome_partition_states(
            outs_4, is_exhaustive=True, is_mutually_exclusive=True, is_negrisk=False, include_void_50_50_if_standalone=True
        )
        books_4 = {
            f"N_{i}": InstrumentOrderBook(f"N_{i}", f"M_{i}", asks=(BookLevel(0.70, 20.0),), book_timestamp_sec=self.now_ts)
            for i in range(4)
        }
        cand_void_trap = CandidateStructure(
            candidate_id="STANDALONE_4NO_VOID_TRAP",
            family="B",
            legs=tuple(ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=f"N_{i}") for i in range(4)),
            states=states_standalone,
            requires_exhaustive_partition=True,
        )
        proof_void = self.verifier.verify_and_simulate(cand_void_trap, books_4)
        self.assertEqual(proof_void.opportunity_class, OpportunityClass.CLASS_E.value)
        self.assertEqual(proof_void.worst_state_id, "OMEGA_STANDALONE_VOID_50_50")
        self.assertAlmostEqual(proof_void.min_state_net_payoff_usd, -4.0, places=4)  # 5.0 min_q * -$0.80/unit

        # Trap 3: Insufficient depth below min_order_size (only 3.0 shares available vs 5.0 min) -> CLASS_E
        thin_y = InstrumentOrderBook("TY", "MT", asks=(BookLevel(0.45, 3.0),), min_order_size=5.0, book_timestamp_sec=self.now_ts)
        thin_n = InstrumentOrderBook("TN", "MT", asks=(BookLevel(0.45, 20.0),), min_order_size=5.0, book_timestamp_sec=self.now_ts)
        proof_thin = self.verifier.verify_binary_complete_set(candidate_id="THIN_DEPTH", yes_book=thin_y, no_book=thin_n)
        self.assertEqual(proof_thin.opportunity_class, OpportunityClass.CLASS_E.value)

        # Trap 4: Disabled order book -> CLASS_E
        dis_y = InstrumentOrderBook("DY", "MD", asks=(BookLevel(0.45, 20.0),), enable_order_book=False, book_timestamp_sec=self.now_ts)
        proof_dis = self.verifier.verify_binary_complete_set(candidate_id="DISABLED_OB", yes_book=dis_y, no_book=thin_n)
        self.assertEqual(proof_dis.opportunity_class, OpportunityClass.CLASS_E.value)
        self.assertIn("ORDERBOOK_DISABLED:DY", proof_dis.disqualifiers)

        # Trap 5: D-001 Frozen KMIA non-interference hard veto (markets 6707503 and 6707502)
        for frozen_mid in FROZEN_DISPUTED_MARKET_IDS:
            kmia_hold = InventoryHolding(
                instrument_id="KMIA_NO_TOK",
                shares=17.0,
                market_id=frozen_mid,
                trade_id="WS_SNIPE_Miami_KMIA_242960",
                uma_resolution_status="disputed",
            )
            kmia_bk = InstrumentOrderBook("KMIA_NO_TOK", frozen_mid, asks=(BookLevel(0.10, 50.0),), book_timestamp_sec=self.now_ts)
            kmia_comp = InstrumentOrderBook("KMIA_YES_TOK", frozen_mid, asks=(BookLevel(0.10, 50.0),), book_timestamp_sec=self.now_ts)
            proof_kmia = self.verifier.verify_inventory_completion(
                candidate_id=f"FORBIDDEN_KMIA_{frozen_mid}",
                holding=kmia_hold,
                held_book=kmia_bk,
                complement_book=kmia_comp,
            )
            self.assertEqual(proof_kmia.opportunity_class, OpportunityClass.CLASS_E.value)
            self.assertEqual(proof_kmia.optimal_executable_quantity, 0.0)
            self.assertTrue(any("D001_FROZEN_DISPUTED" in d for d in proof_kmia.disqualifiers))

    def test_dynamic_fee_curve_and_lockup_opportunity_cost_kill_illusory_gross_edges(self) -> None:
        # 1. Gross $0.49 + $0.49 = $0.98 (+200 bps gross!) on a 700-bps dynamic fee market:
        # V2 share haircut costs ~363 bps total -> net executable payoff is NEGATIVE -> CLASS_E!
        fee_y = InstrumentOrderBook(
            "FY", "MF", asks=(BookLevel(0.49, 30.0),), fee_rate_bps=700.0, book_timestamp_sec=self.now_ts
        )
        fee_n = InstrumentOrderBook(
            "FN", "MF", asks=(BookLevel(0.49, 30.0),), fee_rate_bps=700.0, book_timestamp_sec=self.now_ts
        )
        proof_fee = self.verifier.verify_binary_complete_set(
            candidate_id="FEE_KILLS_GROSS_ARB",
            yes_book=fee_y,
            no_book=fee_n,
        )
        self.assertEqual(proof_fee.opportunity_class, OpportunityClass.CLASS_E.value)
        self.assertLess(proof_fee.min_state_net_payoff_usd, 0.0)

        # 2a. 60-day (1440h) lockup at 0.30 bps/hr opportunity cost (4.32% hurdle) on A_IMPLIES_B ($0.98 cost):
        # Worst states pay $1.00 (net < 0 -> demoted out of CLASS_B!), while middle state (0,1) pays $2.00 (EV > 0 -> CLASS_C)
        hurdle_verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=50.0,
                reconciled_nav_usd=48.70,
                now_ts=self.now_ts,
                lockup_opportunity_cost_bps_per_hour=0.30,
            )
        )
        ya = InstrumentOrderBook("LYA", "LMA", asks=(BookLevel(0.55, 20.0),), book_timestamp_sec=self.now_ts)
        na = InstrumentOrderBook("LNA", "LMA", asks=(BookLevel(0.49, 20.0),), book_timestamp_sec=self.now_ts)
        yb = InstrumentOrderBook("LYB", "LMB", asks=(BookLevel(0.49, 20.0),), book_timestamp_sec=self.now_ts)
        nb = InstrumentOrderBook("LNB", "LMB", asks=(BookLevel(0.55, 20.0),), book_timestamp_sec=self.now_ts)
        proof_lock_imp = hurdle_verifier.verify_logical_implication_pair(
            candidate_id="LONG_LOCKUP_DRAG_IMPLICATION",
            family="E",
            yes_book_a=ya,
            no_book_a=na,
            yes_book_b=yb,
            no_book_b=nb,
            relation="A_IMPLIES_B",
            expected_lockup_hours=1440.0,
            worst_case_lockup_hours=1440.0,
        )
        self.assertEqual(proof_lock_imp.opportunity_class, OpportunityClass.CLASS_C.value)
        self.assertLess(proof_lock_imp.min_state_net_payoff_usd, 0.0)
        self.assertGreater(proof_lock_imp.expected_net_payoff_usd, 0.0)

        # 2b. Same 60-day lockup on EQUIVALENT duplicate ($1.00 payout in EVERY state) makes both min < 0 and EV < 0 -> CLASS_E!
        proof_lock_eq = hurdle_verifier.verify_logical_implication_pair(
            candidate_id="LONG_LOCKUP_DRAG_EQUIVALENT",
            family="I",
            yes_book_a=ya,
            no_book_a=na,
            yes_book_b=yb,
            no_book_b=nb,
            relation="EQUIVALENT",
            expected_lockup_hours=1440.0,
            worst_case_lockup_hours=1440.0,
        )
        self.assertEqual(proof_lock_eq.opportunity_class, OpportunityClass.CLASS_E.value)
        self.assertLess(proof_lock_eq.min_state_net_payoff_usd, 0.0)
        self.assertLess(proof_lock_eq.expected_net_payoff_usd, 0.0)


class TestMarketPropositionGraph(unittest.TestCase):
    """Tests `MarketPropositionGraph` typed edges, rule checks, pruning, incremental updates & `D-001`."""

    def test_four_edge_provenance_tiers_and_connected_component_pruning(self) -> None:
        graph = MarketPropositionGraph()
        chainlink_rules = (
            "This market resolves to Yes if Bitcoin closing price on https://data.chain.link/streams/btc-usd "
            "at 2026-12-31 23:59:59 UTC is at or above the strike."
        )
        binance_rules = (
            "This market resolves to Yes if Bitcoin closing price on Binance BTC/USDT 1m candle "
            "at 2026-12-31 23:59:59 UTC is at or above the strike."
        )
        touch_rules = (
            "This market resolves to Yes if Bitcoin touches or hits the target price at any point before "
            "2026-12-31 23:59:59 UTC on https://data.chain.link/streams/btc-usd."
        )

        events = [
            # 1. Official closed 3-outcome NegRisk event -> OFFICIAL_CONTRACTUAL
            {
                "id": "ev_nr_closed",
                "slug": "mayor-election-closed",
                "title": "Closed Mayor Election",
                "category": "politics",
                "negRisk": True,
                "negRiskMarketID": "0xnr_closed_01",
                "negRiskAugmented": False,
                "markets": [
                    {
                        "id": "m_nr_1",
                        "conditionId": "0xc_nr_1",
                        "question": "Will Alice win the election?",
                        "groupItemTitle": "Alice",
                        "description": "Official certified election winner.",
                        "clobTokenIds": json.dumps(["tok_y_nr1", "tok_n_nr1"]),
                        "outcomes": json.dumps(["Yes", "No"]),
                        "negRisk": True,
                        "negRiskMarketID": "0xnr_closed_01",
                    },
                    {
                        "id": "m_nr_2",
                        "conditionId": "0xc_nr_2",
                        "question": "Will Bob win the election?",
                        "groupItemTitle": "Bob",
                        "description": "Official certified election winner.",
                        "clobTokenIds": json.dumps(["tok_y_nr2", "tok_n_nr2"]),
                        "outcomes": json.dumps(["Yes", "No"]),
                        "negRisk": True,
                        "negRiskMarketID": "0xnr_closed_01",
                    },
                    {
                        "id": "m_nr_3",
                        "conditionId": "0xc_nr_3",
                        "question": "Will Carol win the election?",
                        "groupItemTitle": "Carol",
                        "description": "Official certified election winner.",
                        "clobTokenIds": json.dumps(["tok_y_nr3", "tok_n_nr3"]),
                        "outcomes": json.dumps(["Yes", "No"]),
                        "negRisk": True,
                        "negRiskMarketID": "0xnr_closed_01",
                    },
                ],
            },
            # 2. Augmented NegRisk event with unnamed placeholder "Person A" -> SUSPECTED_REQUIRES_PROOF
            {
                "id": "ev_nr_aug",
                "slug": "nominee-augmented",
                "title": "Augmented Nominee",
                "category": "politics",
                "negRisk": True,
                "negRiskMarketID": "0xnr_aug_02",
                "negRiskAugmented": True,
                "markets": [
                    {
                        "id": "m_aug_1",
                        "conditionId": "0xc_aug_1",
                        "question": "Will Smith be nominated?",
                        "groupItemTitle": "Smith",
                        "description": "Official nomination rules.",
                        "clobTokenIds": ["tok_y_a1", "tok_n_a1"],
                        "negRisk": True,
                        "negRiskMarketID": "0xnr_aug_02",
                        "negRiskAugmented": True,
                    },
                    {
                        "id": "m_aug_2",
                        "conditionId": "0xc_aug_2",
                        "question": "Will Person A be nominated?",
                        "groupItemTitle": "Person A",
                        "description": "Placeholder slot.",
                        "clobTokenIds": ["tok_y_a2", "tok_n_a2"],
                        "negRisk": True,
                        "negRiskMarketID": "0xnr_aug_02",
                        "negRiskAugmented": True,
                    },
                ],
            },
        ]

        standalone = [
            # 3. BTC Chainlink strike ladder + range bracket -> VERIFIED_MATHEMATICAL
            {
                "id": "m_btc_90k",
                "conditionId": "0xbtc90",
                "question": "Will Bitcoin close above $90k on Dec 31?",
                "description": chainlink_rules,
                "endDate": "2026-12-31T23:59:59Z",
                "clobTokenIds": ["y_btc90", "n_btc90"],
                "feeRateBps": 175,
            },
            {
                "id": "m_btc_95k",
                "conditionId": "0xbtc95",
                "question": "Will Bitcoin close above $95k on Dec 31?",
                "description": chainlink_rules,
                "endDate": "2026-12-31T23:59:59Z",
                "clobTokenIds": ["y_btc95", "n_btc95"],
                "feeRateBps": 175,
            },
            {
                "id": "m_btc_rng_95_100",
                "conditionId": "0xbtcrng",
                "question": "Will Bitcoin close between $95k and $100k on Dec 31?",
                "description": chainlink_rules,
                "endDate": "2026-12-31T23:59:59Z",
                "clobTokenIds": ["y_btcrng", "n_btcrng"],
                "feeRateBps": 175,
            },
            # 4. BTC Touch-anytime $105k vs Close-at-cutoff $95k -> SUSPECTED_REQUIRES_PROOF
            {
                "id": "m_btc_touch_105k",
                "conditionId": "0xbtctouch",
                "question": "Will Bitcoin touch $105k at any point?",
                "description": touch_rules,
                "endDate": "2026-12-31T23:59:59Z",
                "clobTokenIds": ["y_btctouch", "n_btctouch"],
            },
            # 5. BTC Binance $110k vs BTC Chainlink -> STATISTICAL_CORRELATION_ONLY
            {
                "id": "m_btc_binance_110k",
                "conditionId": "0xbtcbin",
                "question": "Will Bitcoin close above $110k on Dec 31?",
                "description": binance_rules,
                "endDate": "2026-12-31T23:59:59Z",
                "clobTokenIds": ["y_btcbin", "n_btcbin"],
            },
            # 6. Temporal deadline ladder -> VERIFIED_MATHEMATICAL (`by June 30, 2026` => `by December 31, 2026`)
            {
                "id": "m_rate_jun",
                "conditionId": "0xrate_jun",
                "question": "Will the ECB cut rates by June 30, 2026?",
                "description": "Resolves Yes per official ECB Governing Council statement in UTC.",
                "endDate": "2026-06-30T23:59:59Z",
                "clobTokenIds": ["y_rjun", "n_rjun"],
            },
            {
                "id": "m_rate_dec",
                "conditionId": "0xrate_dec",
                "question": "Will the ECB cut rates by December 31, 2026?",
                "description": "Resolves Yes per official ECB Governing Council statement in UTC.",
                "endDate": "2026-12-31T23:59:59Z",
                "clobTokenIds": ["y_rdec", "n_rdec"],
            },
            # 7. Unrelated singleton market (must be pruned from multi-market components!)
            {
                "id": "m_isolated_oscar",
                "conditionId": "0xoscar",
                "question": "Will Film X win Best Picture?",
                "description": "Official Academy Awards announcement.",
                "endDate": "2027-03-01T04:00:00Z",
                "clobTokenIds": ["y_osc", "n_osc"],
            },
        ]

        delta = graph.ingest_events_and_markets(events=events, standalone_markets=standalone)
        self.assertEqual(len(delta.upserted_market_ids), 13)

        # Verify closed NegRisk edges are OFFICIAL_CONTRACTUAL
        nr_edges = [e for e in graph.get_edges_for_market("m_nr_1") if e.relation_kind == RelationKind.NEGRISK_CLOSED_SLATE]
        self.assertEqual(len(nr_edges), 2)
        self.assertTrue(all(e.edge_type == EdgeType.OFFICIAL_CONTRACTUAL for e in nr_edges))

        # Verify augmented NegRisk edges with "Person A" are quarantined to SUSPECTED_REQUIRES_PROOF
        aug_edges = [e for e in graph.get_edges_for_market("m_aug_1") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(aug_edges), 1)
        self.assertEqual(aug_edges[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertIn("UNNAMED_PLACEHOLDER_OUTCOME_PRESENT", aug_edges[0].disqualifiers)

        # Verify BTC >95k => >90k and [95k,100k] => >90k (strict 90k < 95k!) are VERIFIED_MATHEMATICAL
        btc95_edges = graph.get_edges_for_market("m_btc_95k")
        imp_95_90 = [e for e in btc95_edges if e.source_market_id == "m_btc_95k" and e.target_market_id == "m_btc_90k"]
        self.assertEqual(len(imp_95_90), 1)
        self.assertEqual(imp_95_90[0].edge_type, EdgeType.VERIFIED_MATHEMATICAL)

        btc90_edges = graph.get_edges_for_market("m_btc_90k")
        rng_imp = [e for e in btc90_edges if e.source_market_id == "m_btc_rng_95_100" and e.target_market_id == "m_btc_90k"]
        self.assertEqual(len(rng_imp), 1)
        self.assertEqual(rng_imp[0].edge_type, EdgeType.VERIFIED_MATHEMATICAL)

        # Verify touch-vs-close mismatch is SUSPECTED_REQUIRES_PROOF
        touch_edges = [e for e in graph.get_edges_for_market("m_btc_touch_105k") if e.source_market_id != e.target_market_id]
        self.assertTrue(any(e.edge_type == EdgeType.SUSPECTED_REQUIRES_PROOF for e in touch_edges))

        # Verify Chainlink vs Binance is STATISTICAL_CORRELATION_ONLY
        bin_edges = [e for e in graph.get_edges_for_market("m_btc_binance_110k") if e.source_market_id != e.target_market_id]
        self.assertTrue(all(e.edge_type == EdgeType.STATISTICAL_CORRELATION_ONLY for e in bin_edges))

        # Verify deadline ladder `m_rate_jun => m_rate_dec` is VERIFIED_MATHEMATICAL
        jun_edges = [e for e in graph.get_edges_for_market("m_rate_jun") if e.target_market_id == "m_rate_dec"]
        self.assertEqual(len(jun_edges), 1)
        self.assertEqual(jun_edges[0].edge_type, EdgeType.VERIFIED_MATHEMATICAL)

        # Verify connected-component pruning isolates only OFFICIAL_CONTRACTUAL + VERIFIED_MATHEMATICAL multi-market clusters
        comps = graph.get_connected_components(
            allowed_edge_types=(EdgeType.OFFICIAL_CONTRACTUAL, EdgeType.VERIFIED_MATHEMATICAL),
            include_single_market_binaries=False,
        )
        comp_mkt_sets = [set(c.market_ids) for c in comps]
        self.assertIn({"m_nr_1", "m_nr_2", "m_nr_3"}, comp_mkt_sets)
        self.assertIn({"m_btc_90k", "m_btc_95k", "m_btc_rng_95_100"}, comp_mkt_sets)
        self.assertIn({"m_rate_jun", "m_rate_dec"}, comp_mkt_sets)
        for s in comp_mkt_sets:
            self.assertNotIn("m_isolated_oscar", s)
            self.assertNotIn("m_btc_touch_105k", s)
            self.assertNotIn("m_btc_binance_110k", s)
            self.assertNotIn("m_aug_2", s)

    def test_incremental_updates_and_d001_portfolio_holding_quarantine(self) -> None:
        graph = MarketPropositionGraph()
        rules = "Resolves Yes if ETH closes above strike at 2026-12-31 23:59:59 UTC on https://data.chain.link/streams/eth-usd."
        graph.ingest_events_and_markets(
            standalone_markets=[
                {
                    "id": "eth_3k",
                    "conditionId": "0xeth3k",
                    "question": "Will Ethereum close above $3k?",
                    "description": rules,
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["y_e3", "n_e3"],
                },
                {
                    "id": "eth_4k",
                    "conditionId": "0xeth4k",
                    "question": "Will Ethereum close above $4k?",
                    "description": rules,
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["y_e4", "n_e4"],
                },
                {
                    "id": "6707503",
                    "conditionId": "0xkmia_disp_1",
                    "question": "Miami KMIA temperature Nov 7",
                    "description": "METAR KMIA",
                    "clobTokenIds": ["y_kmia1", "n_kmia1"],
                    "umaResolutionStatus": "disputed",
                },
            ]
        )
        # Incremental upsert of $3.5k strike inserts cleanly between $3k and $4k: 4k => 3.5k => 3k
        upd = graph.incremental_update(
            updated_markets=[
                {
                    "id": "eth_3500",
                    "conditionId": "0xeth35",
                    "question": "Will Ethereum close above $3.5k?",
                    "description": rules,
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["y_e35", "n_e35"],
                }
            ]
        )
        self.assertIn("eth_3500", upd.upserted_market_ids)
        e35_edges = [e for e in graph.get_edges_for_market("eth_3500") if e.source_market_id != e.target_market_id]
        pairs = {(e.source_market_id, e.target_market_id) for e in e35_edges}
        self.assertIn(("eth_4k", "eth_3500"), pairs)
        self.assertIn(("eth_3500", "eth_3k"), pairs)

        # Incremental removal of eth_3500 reconnects eth_4k => eth_3k directly
        rem = graph.incremental_update(removed_market_ids=["eth_3500"])
        self.assertEqual(rem.removed_market_ids, ("eth_3500",))
        e4_edges = [e for e in graph.get_edges_for_market("eth_4k") if e.source_market_id != e.target_market_id]
        self.assertEqual([(e.source_market_id, e.target_market_id) for e in e4_edges], [("eth_4k", "eth_3k")])

        # Portfolio holdings attachment: 4 disputed KMIA positions + 1 clean ETH position
        harvester_state = {
            "active_positions": {
                "WS_SNIPE_Miami_KMIA_242960": {
                    "market_id": "6707503",
                    "token_id": "n_kmia1",
                    "remaining_shares": 20.0,
                    "notional_usd": 19.54,
                    "umaResolutionStatus": "disputed",
                },
                "WS_SNIPE_Miami_KMIA_688670": {
                    "market_id": "6707503",
                    "token_id": "n_kmia1",
                    "remaining_shares": 10.0,
                    "notional_usd": 9.77,
                    "umaResolutionStatus": "disputed",
                },
                "WS_SNIPE_Miami_KMIA_837595": {
                    "market_id": "6707503",
                    "token_id": "n_kmia1",
                    "remaining_shares": 5.0,
                    "notional_usd": 4.88,
                    "umaResolutionStatus": "disputed",
                },
                "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                    "market_id": "6707502",
                    "token_id": "y_kmia2",
                    "remaining_shares": 17.0,
                    "notional_usd": 16.32,
                    "umaResolutionStatus": "disputed",
                },
                "CLEAN_ETH_HOLDING_1": {
                    "market_id": "eth_3k",
                    "token_id": "y_e3",
                    "remaining_shares": 12.0,
                    "notional_usd": 5.40,
                    "umaResolutionStatus": "none",
                },
            }
        }
        recyclable_n, frozen_n = graph.load_portfolio_holdings(harvester_state)
        self.assertEqual(recyclable_n, 1)
        self.assertEqual(frozen_n, 4)
        self.assertEqual([h.holding_id for h in graph.get_recyclable_holdings()], ["CLEAN_ETH_HOLDING_1"])
        self.assertEqual(len(graph.get_frozen_holdings()), 4)
        # Ensure zero PORTFOLIO_INVENTORY_LINK edges were created on 6707503
        kmia_edges = [
            e for e in graph.get_edges_for_market("6707503") if e.relation_kind == RelationKind.PORTFOLIO_INVENTORY_LINK
        ]
        self.assertEqual(len(kmia_edges), 0)

    def test_subquadratic_scaling_on_synthetic_multi_bucket_universe(self) -> None:
        graph = MarketPropositionGraph()
        mkts = []
        rules = "Resolves Yes per https://data.chain.link/streams/sol-usd at 2026-12-31 23:59:59 UTC."
        # 50 SOL strikes + 250 unrelated singletons = 300 markets (300*299/2 = 44,850 naive pairs)
        for k in range(50):
            strike = 100 + k * 5
            mkts.append(
                {
                    "id": f"sol_{strike}",
                    "conditionId": f"0xsol_{strike}",
                    "question": f"Will Solana close above ${strike} on Dec 31?",
                    "description": rules,
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": [f"y_sol_{strike}", f"n_sol_{strike}"],
                }
            )
        for u in range(250):
            mkts.append(
                {
                    "id": f"unrel_{u}",
                    "conditionId": f"0xunrel_{u}",
                    "question": f"Will Municipality {u} pass local ordinance {u}?",
                    "description": f"Unique municipal clerk certification #{u}.",
                    "endDate": "2026-11-30T23:59:59Z",
                    "clobTokenIds": [f"y_u_{u}", f"n_u_{u}"],
                }
            )
        t0 = time.perf_counter()
        graph.ingest_events_and_markets(standalone_markets=mkts)
        elapsed = time.perf_counter() - t0
        metrics = graph.summary_metrics()
        self.assertLess(elapsed, 1.0)
        self.assertEqual(metrics["total_markets"], 300)
        # Chain ladder creates 49 cross-market edges (O(m)), NOT 50*49/2 = 1,225 or 44,850!
        self.assertEqual(metrics["cross_market_edges"], 49)
        self.assertEqual(metrics["verified_multi_market_components"], 1)

    def test_intervening_cross_oracle_strike_sports_ot_and_duplicates(self) -> None:
        graph = MarketPropositionGraph()
        cl_rules = "Resolves Yes per https://data.chain.link/streams/btc-usd closing price at 2026-12-31 23:59:59 UTC."
        bn_rules = "Resolves Yes per Binance BTC/USDT closing price at 2026-12-31 23:59:59 UTC."
        graph.ingest_events_and_markets(
            standalone_markets=[
                {"id": "cl_90", "conditionId": "0x1", "question": "Will BTC close above $90k?", "description": cl_rules, "endDate": "2026-12-31T23:59:59Z", "clobTokenIds": ["y1", "n1"]},
                {"id": "bn_92", "conditionId": "0x2", "question": "Will BTC close above $92k?", "description": bn_rules, "endDate": "2026-12-31T23:59:59Z", "clobTokenIds": ["y2", "n2"]},
                {"id": "cl_95", "conditionId": "0x3", "question": "Will BTC close above $95k?", "description": cl_rules, "endDate": "2026-12-31T23:59:59Z", "clobTokenIds": ["y3", "n3"]},
                # Sports 90m regulation vs overtime advance
                {"id": "sp_reg", "conditionId": "0x4", "question": "Arsenal vs Chelsea: Arsenal win?", "description": "Resolves on 90 minutes regulation time only, excludes overtime.", "endDate": "2026-11-20T22:00:00Z", "clobTokenIds": ["ys1", "ns1"]},
                {"id": "sp_ot", "conditionId": "0x5", "question": "Arsenal vs Chelsea: Arsenal to advance?", "description": "Resolves including extra time and shootout.", "endDate": "2026-11-20T22:00:00Z", "clobTokenIds": ["ys2", "ns2"]},
                # Exact duplicate pair with identical rules -> VERIFIED_MATHEMATICAL
                {"id": "dup_1", "conditionId": "0x6", "question": "Will SpaceX launch Starship Flight 12 in November 2026?", "description": "Official FAA/SpaceX liftoff confirmation in UTC.", "endDate": "2026-11-30T23:59:59Z", "clobTokenIds": ["yd1", "nd1"]},
                {"id": "dup_2", "conditionId": "0x7", "question": "Will SpaceX launch Starship Flight 12 in November 2026?", "description": "Official FAA/SpaceX liftoff confirmation in UTC.", "endDate": "2026-11-30T23:59:59Z", "clobTokenIds": ["yd2", "nd2"]},
            ]
        )
        # Intervening bn_92 MUST NOT break cl_95 => cl_90 VERIFIED_MATHEMATICAL edge!
        cl95_edges = [e for e in graph.get_edges_for_market("cl_95") if e.target_market_id == "cl_90"]
        self.assertEqual(len(cl95_edges), 1)
        self.assertEqual(cl95_edges[0].edge_type, EdgeType.VERIFIED_MATHEMATICAL)

        # Sports regulation vs overtime flagged as SUSPECTED_REQUIRES_PROOF
        sp_edges = [e for e in graph.get_edges_for_market("sp_reg") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(sp_edges), 1)
        self.assertEqual(sp_edges[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertIn("SPORTS_REGULATION_VS_OVERTIME_MISMATCH", sp_edges[0].disqualifiers)

        # Exact duplicate with matching rules is VERIFIED_MATHEMATICAL EQUIVALENT
        dup_edges = [e for e in graph.get_edges_for_market("dup_1") if e.relation_kind == RelationKind.EQUIVALENT]
        self.assertEqual(len(dup_edges), 1)
        self.assertEqual(dup_edges[0].edge_type, EdgeType.VERIFIED_MATHEMATICAL)

    # -----------------------------------------------------------------------
    # Adversarial Regression Tests for BUG-MV-1 through BUG-MV-6
    # -----------------------------------------------------------------------

    def test_regression_bug_mv1_strict_vs_inclusive_boundary_and_equal_strike(self) -> None:
        graph = MarketPropositionGraph()
        wx_rules = "Resolves Yes per official Weather Underground daily high at KJFK on 2026-11-20 UTC."
        graph.ingest_events_and_markets(
            standalone_markets=[
                {"id": "wx_74_75", "conditionId": "0xwx1", "question": "Will KJFK high temp be between 74°F and 75°F?", "description": wx_rules, "endDate": "2026-11-20T23:59:59Z", "clobTokenIds": ["yw1", "nw1"]},
                {"id": "wx_over_74", "conditionId": "0xwx2", "question": "Will KJFK high temp be over 74°F?", "description": wx_rules, "endDate": "2026-11-20T23:59:59Z", "clobTokenIds": ["yw2", "nw2"]},
            ]
        )
        # [74, 75] vs strict `over 74` (T > 74): at T=74°F, [74,75] is YES while `over 74` is NO!
        # Must NEVER emit VERIFIED_MATHEMATICAL!
        e_74_75 = [e for e in graph.get_edges_for_market("wx_74_75") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(e_74_75), 1)
        self.assertEqual(e_74_75[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertIn("STRICT_BOUNDARY_EXCLUSION_AT_LOWER_ENDPOINT", e_74_75[0].disqualifiers)

        # Adding weak `at least 74°F` (T >= 74) + `under 75°F` (T < 75) + `at most 75°F` (T <= 75):
        # - `wx_over_74` (T > 74) => `wx_ge_74` (T >= 74) IS VERIFIED_MATHEMATICAL (and never converse!)
        # - `wx_74_75` ([74, 75]) => `wx_ge_74` (T >= 74) IS VERIFIED_MATHEMATICAL
        # - `wx_lt_75` (T < 75) => `wx_le_75` (T <= 75) IS VERIFIED_MATHEMATICAL (and never converse!)
        # - `wx_74_75` ([74, 75]) => `wx_le_75` (T <= 75) IS VERIFIED_MATHEMATICAL (never `wx_lt_75`!)
        graph.incremental_update(
            updated_markets=[
                {"id": "wx_ge_74", "conditionId": "0xwx3", "question": "Will KJFK high temp be at least 74°F?", "description": wx_rules, "endDate": "2026-11-20T23:59:59Z", "clobTokenIds": ["yw3", "nw3"]},
                {"id": "wx_lt_75", "conditionId": "0xwx4", "question": "Will KJFK high temp be under 75°F?", "description": wx_rules, "endDate": "2026-11-20T23:59:59Z", "clobTokenIds": ["yw4", "nw4"]},
                {"id": "wx_le_75", "conditionId": "0xwx5", "question": "Will KJFK high temp be at most 75°F?", "description": wx_rules, "endDate": "2026-11-20T23:59:59Z", "clobTokenIds": ["yw5", "nw5"]},
            ]
        )
        verified_pairs = {
            (e.source_market_id, e.target_market_id)
            for e in graph.edges.values()
            if e.edge_type == EdgeType.VERIFIED_MATHEMATICAL and e.source_market_id != e.target_market_id
        }
        self.assertIn(("wx_over_74", "wx_ge_74"), verified_pairs)
        self.assertNotIn(("wx_ge_74", "wx_over_74"), verified_pairs)
        self.assertIn(("wx_74_75", "wx_ge_74"), verified_pairs)
        self.assertNotIn(("wx_74_75", "wx_over_74"), verified_pairs)
        self.assertIn(("wx_lt_75", "wx_le_75"), verified_pairs)
        self.assertNotIn(("wx_le_75", "wx_lt_75"), verified_pairs)
        self.assertIn(("wx_74_75", "wx_le_75"), verified_pairs)
        self.assertNotIn(("wx_74_75", "wx_lt_75"), verified_pairs)

    def test_regression_bug_mv2_negated_threshold_and_deadline_blindness(self) -> None:
        graph = MarketPropositionGraph()
        cl_rules = "Resolves Yes per https://data.chain.link/streams/btc-usd closing price at 2026-12-31 23:59:59 UTC."
        fed_rules = "Resolves Yes per official FOMC statement in UTC."
        graph.ingest_events_and_markets(
            standalone_markets=[
                {"id": "btc_95k", "conditionId": "0xb1", "question": "Will Bitcoin close above $95k on Dec 31?", "description": cl_rules, "endDate": "2026-12-31T23:59:59Z", "clobTokenIds": ["yb1", "nb1"]},
                {"id": "btc_not_90k", "conditionId": "0xb2", "question": "Will Bitcoin not close above $90k on Dec 31?", "description": cl_rules, "endDate": "2026-12-31T23:59:59Z", "clobTokenIds": ["yb2", "nb2"]},
                {"id": "fed_not_jun", "conditionId": "0xf1", "question": "Will the Fed not cut rates by June 30, 2027?", "description": fed_rules, "endDate": "2027-06-30T23:59:59Z", "clobTokenIds": ["yf1", "nf1"]},
                {"id": "fed_not_dec", "conditionId": "0xf2", "question": "Will the Fed not cut rates by December 31, 2027?", "description": fed_rules, "endDate": "2027-12-31T23:59:59Z", "clobTokenIds": ["yf2", "nf2"]},
            ]
        )
        # Zero VERIFIED_MATHEMATICAL cross-market edges may exist for negated thresholds or negated deadlines!
        verified_cross = [
            e for e in graph.edges.values()
            if e.edge_type == EdgeType.VERIFIED_MATHEMATICAL and e.source_market_id != e.target_market_id
        ]
        self.assertEqual(verified_cross, [])
        neg_btc_edges = [e for e in graph.get_edges_for_market("btc_not_90k") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(neg_btc_edges), 1)
        self.assertEqual(neg_btc_edges[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertIn("NEGATED_THRESHOLD_PROPOSITION", neg_btc_edges[0].disqualifiers)

        neg_fed_edges = [e for e in graph.get_edges_for_market("fed_not_jun") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(neg_fed_edges), 1)
        self.assertEqual(neg_fed_edges[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertIn("NEGATED_DEADLINE_MONOTONICITY_REVERSAL", neg_fed_edges[0].disqualifiers)

    def test_regression_bug_mv3_dup_norm_signs_and_group_item_title(self) -> None:
        graph = MarketPropositionGraph()
        rules = "Resolves per official NBA box score in UTC."
        graph.ingest_events_and_markets(
            standalone_markets=[
                {"id": "lak_minus", "conditionId": "0xl1", "question": "Will Lakers cover -3.5 on Nov 15?", "description": rules, "endDate": "2026-11-15T23:59:59Z", "clobTokenIds": ["yl1", "nl1"]},
                {"id": "lak_plus", "conditionId": "0xl2", "question": "Will Lakers cover +3.5 on Nov 15?", "description": rules, "endDate": "2026-11-15T23:59:59Z", "clobTokenIds": ["yl2", "nl2"]},
                {"id": "tpl_alice", "conditionId": "0xt1", "question": "Will this candidate win the runoff?", "groupItemTitle": "Alice", "description": rules, "endDate": "2026-11-15T23:59:59Z", "clobTokenIds": ["yt1", "nt1"]},
                {"id": "tpl_bob", "conditionId": "0xt2", "question": "Will this candidate win the runoff?", "groupItemTitle": "Bob", "description": rules, "endDate": "2026-11-15T23:59:59Z", "clobTokenIds": ["yt2", "nt2"]},
            ]
        )
        self.assertNotEqual(
            graph.markets["lak_minus"].proposition.duplicate_stem_key,
            graph.markets["lak_plus"].proposition.duplicate_stem_key,
        )
        self.assertNotEqual(
            graph.markets["tpl_alice"].proposition.duplicate_stem_key,
            graph.markets["tpl_bob"].proposition.duplicate_stem_key,
        )
        equiv_edges = [e for e in graph.edges.values() if e.relation_kind == RelationKind.EQUIVALENT]
        self.assertEqual(equiv_edges, [])

    def test_regression_bug_mv4_partial_or_closed_member_negrisk_slate(self) -> None:
        graph = MarketPropositionGraph()
        graph.ingest_events_and_markets(
            events=[
                {
                    "id": "ev_partial_nr",
                    "slug": "partial-negrisk",
                    "title": "Partial NegRisk Slate",
                    "negRisk": True,
                    "negRiskMarketID": "0xnr_partial",
                    "marketCount": 3,
                    "markets": [
                        {
                            "id": "nr_alice",
                            "conditionId": "0xca",
                            "question": "Will Alice win?",
                            "groupItemTitle": "Alice",
                            "questionIndex": 0,
                            "closed": False,
                            "negRisk": True,
                            "negRiskMarketID": "0xnr_partial",
                            "clobTokenIds": ["ya", "na"],
                        },
                        {
                            "id": "nr_charlie",
                            "conditionId": "0xcc",
                            "question": "Will Charlie win?",
                            "groupItemTitle": "Charlie",
                            "questionIndex": 2,
                            "closed": True,
                            "negRisk": True,
                            "negRiskMarketID": "0xnr_partial",
                            "clobTokenIds": ["yc", "nc"],
                        },
                    ],
                }
            ]
        )
        cross_edges = [e for e in graph.get_edges_for_market("nr_alice") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(cross_edges), 1)
        self.assertEqual(cross_edges[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertEqual(cross_edges[0].relation_kind, RelationKind.NEGRISK_AUGMENTED_OR_INCOMPLETE)
        self.assertIn("CLOSED_OR_RESOLVED_SLATE_MEMBER_PRESENT", cross_edges[0].disqualifiers)
        self.assertIn("INCOMPLETE_OR_GAPPED_NEGRISK_QUESTION_INDICES", cross_edges[0].disqualifiers)
        self.assertIn("PARTIAL_EVENT_MARKET_SLATE_INGESTED", cross_edges[0].disqualifiers)

    def test_regression_bug_mv5_question_timezone_and_before_date_24h_boundary(self) -> None:
        graph = MarketPropositionGraph()
        graph.ingest_events_and_markets(
            standalone_markets=[
                {
                    "id": "m_before_apr2_et",
                    "conditionId": "0xm1",
                    "question": "Will Merger X close before April 2, 2027 ET?",
                    "description": "Resolves Yes per official press release.",
                    "clobTokenIds": ["ym1", "nm1"],
                },
                {
                    "id": "m_by_apr2_et",
                    "conditionId": "0xm2",
                    "question": "Will Merger X close by April 2, 2027 ET?",
                    "description": "Resolves Yes per official press release.",
                    "clobTokenIds": ["ym2", "nm2"],
                },
                {
                    "id": "m_tz_conflict",
                    "conditionId": "0xm3",
                    "question": "Will Merger X close by May 1, 2027 ET?",
                    "description": "Resolves Yes per official press release in UTC.",
                    "clobTokenIds": ["ym3", "nm3"],
                },
            ]
        )
        m_bef = graph.markets["m_before_apr2_et"]
        m_by = graph.markets["m_by_apr2_et"]
        m_conf = graph.markets["m_tz_conflict"]

        self.assertEqual(m_bef.resolution.timezone_name, "America/New_York")
        self.assertEqual(m_bef.proposition.deadline_ts, 1806623999)  # Apr 1, 2027 23:59:59 UTC
        self.assertEqual(m_by.proposition.deadline_ts, 1806710399)   # Apr 2, 2027 23:59:59 UTC
        self.assertTrue(m_conf.resolution.timezone_name.startswith("CONFLICT:"))

        # `before April 2` (1806623999) => `by April 2` (1806710399) is VERIFIED_MATHEMATICAL!
        bef_edges = [e for e in graph.get_edges_for_market("m_before_apr2_et") if e.target_market_id == "m_by_apr2_et"]
        self.assertEqual(len(bef_edges), 1)
        self.assertEqual(bef_edges[0].edge_type, EdgeType.VERIFIED_MATHEMATICAL)

        # `by April 2 ET` -> `by May 1 (ET vs UTC conflict)` is quarantined to SUSPECTED_REQUIRES_PROOF!
        conf_edges = [e for e in graph.get_edges_for_market("m_tz_conflict") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(conf_edges), 1)
        self.assertEqual(conf_edges[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertTrue(any("INTERNAL_TIMEZONE_CONFLICT" in d for d in conf_edges[0].disqualifiers))

    def test_regression_bug_mv6_use_inventory_cash_budget_and_fixed_gas_cap(self) -> None:
        now_ts = 1_794_400_000.0
        verifier = UniversalArbVerifier(
            VerificationConfig(max_budget_usd=10.00, reconciled_nav_usd=48.70, now_ts=now_ts)
        )
        # 6a: 20 held shares @ $0.60 mark_bid ($12.00 value) + $0.35 complement ask + $0.02 merge gas
        # Needs only 20 * $0.35 + $0.02 = $7.02 liquid pUSD cash <= $10.00 budget -> full 20.0 shares!
        holding = InventoryHolding(
            instrument_id="YES_HELD",
            shares=20.0,
            market_id="M_INV_BUDGET",
            cost_basis_per_share=0.60,
            mark_bid_per_share=0.60,
        )
        held_bk = InstrumentOrderBook("YES_HELD", "M_INV_BUDGET", asks=(BookLevel(0.62, 50.0),), bids=(BookLevel(0.60, 50.0),), book_timestamp_sec=now_ts)
        comp_bk = InstrumentOrderBook("NO_COMP", "M_INV_BUDGET", asks=(BookLevel(0.35, 30.0),), bids=(BookLevel(0.33, 30.0),), book_timestamp_sec=now_ts)
        proof_inv = verifier.verify_inventory_completion(
            candidate_id="BUG_MV_6A",
            holding=holding,
            held_book=held_bk,
            complement_book=comp_bk,
            merge_immediately=True,
            gas_cost_usd=0.02,
        )
        self.assertEqual(proof_inv.opportunity_class, OpportunityClass.CLASS_A.value)
        self.assertAlmostEqual(proof_inv.optimal_executable_quantity, 20.0, places=4)
        self.assertAlmostEqual(proof_inv.cost_breakdown.capital_required_usd, 7.02, places=4)
        self.assertAlmostEqual(proof_inv.cost_breakdown.acquisition_costs_usd, 19.00, places=4)
        self.assertAlmostEqual(proof_inv.min_state_net_payoff_usd, 0.98, places=4)

        # 6b: Binary complete-set ($0.45 + $0.45 = $0.90/unit) with max_budget_usd=$9.00 and gas=$0.09:
        # capital_required_usd MUST NOT exceed $9.00 (q* = ($9.00 - $0.09) / $0.90 = 9.90, NOT 10.00!)
        verifier_9 = UniversalArbVerifier(
            VerificationConfig(max_budget_usd=9.00, reconciled_nav_usd=48.70, now_ts=now_ts)
        )
        yb = InstrumentOrderBook("Y_GAS", "M_GAS", asks=(BookLevel(0.45, 50.0),), bids=(BookLevel(0.43, 50.0),), book_timestamp_sec=now_ts)
        nb = InstrumentOrderBook("N_GAS", "M_GAS", asks=(BookLevel(0.45, 50.0),), bids=(BookLevel(0.43, 50.0),), book_timestamp_sec=now_ts)
        proof_gas = verifier_9.verify_binary_complete_set(
            candidate_id="BUG_MV_6B",
            yes_book=yb,
            no_book=nb,
            gas_cost_usd=0.09,
        )
        self.assertEqual(proof_gas.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertLessEqual(proof_gas.cost_breakdown.capital_required_usd, 9.00 + 1e-6)
        self.assertAlmostEqual(proof_gas.optimal_executable_quantity, 9.90, places=4)
        self.assertAlmostEqual(proof_gas.cost_breakdown.capital_required_usd, 9.00, places=4)

    # -----------------------------------------------------------------------
    # Live Gamma Edge Pattern Regressions (#14 / #15):
    #   (a) Over/Under `outcomes=["Over","Under"]` orientation (`6950562/6967460`)
    #   (b) `Map 3` vs `Map 2` sub-period & stat-stem separation (`6964023/6962550`)
    #   (c) Yearless `"by March 31?"` [2027] vs `"by November 15?"` [2026] (`6438437/6301107`)
    # -----------------------------------------------------------------------

    def test_live_gamma_pattern_over_under_outcome_polarity_orientation(self) -> None:
        graph = MarketPropositionGraph()
        nfl_rules = "Resolves per official NFL box score including overtime in UTC."
        graph.ingest_events_and_markets(
            standalone_markets=[
                # Live Gamma O/U convention: outcomes=["Over", "Under"], toks[0] == Over!
                {
                    "id": "6950562",
                    "conditionId": "0xou_505",
                    "question": "Ravens vs Bengals: Over/Under 50.5",
                    "description": nfl_rules,
                    "endDate": "2026-11-15T21:00:00Z",
                    "clobTokenIds": json.dumps(["tok_over_505", "tok_under_505"]),
                    "outcomes": json.dumps(["Over", "Under"]),
                },
                {
                    "id": "6967460",
                    "conditionId": "0xou_485",
                    "question": "Ravens vs Bengals: O/U 48.5",
                    "description": nfl_rules,
                    "endDate": "2026-11-15T21:00:00Z",
                    "clobTokenIds": json.dumps(["tok_over_485", "tok_under_485"]),
                    "outcomes": json.dumps(["Over", "Under"]),
                },
                # Ambiguous O/U market lacking Over/Under outcome labels -> must quarantine!
                {
                    "id": "m_ou_ambig",
                    "conditionId": "0xou_amb",
                    "question": "Ravens vs Bengals: Over/Under 46.5",
                    "description": nfl_rules,
                    "endDate": "2026-11-15T21:00:00Z",
                    "clobTokenIds": ["tok_y_465", "tok_n_465"],
                    "outcomes": ["Yes", "No"],
                },
                # Inverted ["Under", "Over"] market pair on a different match -> Under 42.5 => Under 45.5!
                {
                    "id": "m_uo_425",
                    "conditionId": "0xuo_425",
                    "question": "Bills vs Chiefs: Over/Under 42.5",
                    "description": nfl_rules,
                    "endDate": "2026-11-15T21:00:00Z",
                    "clobTokenIds": ["tok_u_425", "tok_o_425"],
                    "outcomes": ["Under", "Over"],
                },
                {
                    "id": "m_uo_455",
                    "conditionId": "0xuo_455",
                    "question": "Bills vs Chiefs: Over/Under 45.5",
                    "description": nfl_rules,
                    "endDate": "2026-11-15T21:00:00Z",
                    "clobTokenIds": ["tok_u_455", "tok_o_455"],
                    "outcomes": ["Under", "Over"],
                },
                # Inverted ["No", "Yes"] polarity trap on standard threshold question -> must quarantine!
                {
                    "id": "m_inv_ny_1",
                    "conditionId": "0xny1",
                    "question": "Will Gold close above $2800 on Dec 31?",
                    "description": "Resolves per official LBMA fix in UTC.",
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["tok_no_first_1", "tok_yes_second_1"],
                    "outcomes": ["No", "Yes"],
                },
                {
                    "id": "m_inv_ny_2",
                    "conditionId": "0xny2",
                    "question": "Will Gold close above $2900 on Dec 31?",
                    "description": "Resolves per official LBMA fix in UTC.",
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["tok_no_first_2", "tok_yes_second_2"],
                    "outcomes": ["No", "Yes"],
                },
            ]
        )

        self.assertEqual(graph.markets["6950562"].proposition.outcome_polarity_mode, "OVER_UNDER")
        self.assertEqual(graph.markets["6950562"].proposition.predicate_type, "THRESHOLD_GE")
        self.assertAlmostEqual(graph.markets["6950562"].proposition.threshold_low or 0.0, 50.5, places=4)
        self.assertEqual(graph.markets["6967460"].proposition.predicate_type, "THRESHOLD_GE")
        self.assertAlmostEqual(graph.markets["6967460"].proposition.threshold_low or 0.0, 48.5, places=4)

        verified_pairs = {
            (e.source_market_id, e.target_market_id)
            for e in graph.edges.values()
            if e.edge_type == EdgeType.VERIFIED_MATHEMATICAL and e.source_market_id != e.target_market_id
        }
        # Over 50.5 => Over 48.5 is VERIFIED_MATHEMATICAL; NEVER Over 48.5 => Over 50.5!
        self.assertIn(("6950562", "6967460"), verified_pairs)
        self.assertNotIn(("6967460", "6950562"), verified_pairs)

        # Under 42.5 => Under 45.5 when outcomes == ["Under", "Over"]
        self.assertIn(("m_uo_425", "m_uo_455"), verified_pairs)
        self.assertNotIn(("m_uo_455", "m_uo_425"), verified_pairs)

        # Ambiguous O/U with ["Yes","No"] and inverted ["No","Yes"] emit ZERO VERIFIED_MATHEMATICAL edges
        for mid_q in ("m_ou_ambig", "m_inv_ny_1", "m_inv_ny_2"):
            v_q = [
                e
                for e in graph.get_edges_for_market(mid_q)
                if e.edge_type == EdgeType.VERIFIED_MATHEMATICAL and e.source_market_id != e.target_market_id
            ]
            self.assertEqual(v_q, [])

    def test_live_gamma_pattern_sub_period_map_and_stat_stem_separation(self) -> None:
        graph = MarketPropositionGraph()
        cs_rules = "Resolves per official HLTV match statistics in UTC."
        soc_rules = "Resolves per official Premier League Opta match statistics in UTC."
        graph.ingest_events_and_markets(
            standalone_markets=[
                # Live pair 6964023 (Map 3) vs 6962550 (Map 2) + second Map 2 line (6962551)
                {
                    "id": "6964023",
                    "conditionId": "0xmap3_285",
                    "question": "Team Liquid vs G2 Esports - Map 3: Total Kills Over/Under 28.5",
                    "description": cs_rules,
                    "endDate": "2026-11-14T19:00:00Z",
                    "clobTokenIds": ["y_m3_285", "n_m3_285"],
                    "outcomes": ["Over", "Under"],
                },
                {
                    "id": "6962550",
                    "conditionId": "0xmap2_265",
                    "question": "Team Liquid vs G2 Esports - Map 2: Total Kills Over/Under 26.5",
                    "description": cs_rules,
                    "endDate": "2026-11-14T19:00:00Z",
                    "clobTokenIds": ["y_m2_265", "n_m2_265"],
                    "outcomes": ["Over", "Under"],
                },
                {
                    "id": "6962551",
                    "conditionId": "0xmap2_295",
                    "question": "Team Liquid vs G2 Esports - Map 2: Total Kills Over/Under 29.5",
                    "description": cs_rules,
                    "endDate": "2026-11-14T19:00:00Z",
                    "clobTokenIds": ["y_m2_295", "n_m2_295"],
                    "outcomes": ["Over", "Under"],
                },
                # Same Map 2, DIFFERENT stat (Total Rounds vs Total Kills) -> must NOT link as VERIFIED_MATHEMATICAL!
                {
                    "id": "6962552",
                    "conditionId": "0xmap2_rnd",
                    "question": "Team Liquid vs G2 Esports - Map 2: Total Rounds Over/Under 22.5",
                    "description": cs_rules,
                    "endDate": "2026-11-14T19:00:00Z",
                    "clobTokenIds": ["y_m2_r225", "n_m2_r225"],
                    "outcomes": ["Over", "Under"],
                },
                # 1st Half O/U vs Full Match O/U + Team A Total vs Team B Total -> must NOT link!
                {
                    "id": "soc_1h_ou15",
                    "conditionId": "0xsoc_1h",
                    "question": "Arsenal vs Chelsea: 1st Half Over/Under 1.5",
                    "description": soc_rules,
                    "endDate": "2026-11-16T16:30:00Z",
                    "clobTokenIds": ["y_s1h", "n_s1h"],
                    "outcomes": ["Over", "Under"],
                },
                {
                    "id": "soc_full_ou25",
                    "conditionId": "0xsoc_full",
                    "question": "Arsenal vs Chelsea: Over/Under 2.5",
                    "description": soc_rules,
                    "endDate": "2026-11-16T16:30:00Z",
                    "clobTokenIds": ["y_sfull", "n_sfull"],
                    "outcomes": ["Over", "Under"],
                },
                {
                    "id": "soc_ars_ou15",
                    "conditionId": "0xsoc_ars",
                    "question": "Arsenal vs Chelsea: Arsenal Goals Over/Under 1.5",
                    "description": soc_rules,
                    "endDate": "2026-11-16T16:30:00Z",
                    "clobTokenIds": ["y_sars", "n_sars"],
                    "outcomes": ["Over", "Under"],
                },
                {
                    "id": "soc_che_ou05",
                    "conditionId": "0xsoc_che",
                    "question": "Arsenal vs Chelsea: Chelsea Goals Over/Under 0.5",
                    "description": soc_rules,
                    "endDate": "2026-11-16T16:30:00Z",
                    "clobTokenIds": ["y_sche", "n_sche"],
                    "outcomes": ["Over", "Under"],
                },
            ]
        )

        self.assertEqual(graph.markets["6964023"].proposition.scope_key, "MAP_3")
        self.assertEqual(graph.markets["6962550"].proposition.scope_key, "MAP_2")
        self.assertEqual(graph.markets["soc_1h_ou15"].proposition.scope_key, "HALF_1")
        self.assertEqual(graph.markets["soc_full_ou25"].proposition.scope_key, "")

        verified_pairs = {
            (e.source_market_id, e.target_market_id)
            for e in graph.edges.values()
            if e.edge_type == EdgeType.VERIFIED_MATHEMATICAL and e.source_market_id != e.target_market_id
        }
        # ONLY same-map, same-stat dominance (Map 2 Kills O/U 29.5 => Map 2 Kills O/U 26.5) is VERIFIED_MATHEMATICAL!
        self.assertEqual(verified_pairs, {("6962551", "6962550")})

    def test_live_gamma_pattern_yearless_deadline_disambiguation_via_enddate(self) -> None:
        graph = MarketPropositionGraph()
        proto_rules = "Resolves Yes per official mainnet genesis block announcement in UTC."
        graph.ingest_events_and_markets(
            standalone_markets=[
                # Live pattern 6438437 ("by March 31?" -> endDate 2027-03-31) vs 6301107 ("by November 15?" -> endDate 2026-11-15)
                {
                    "id": "6438437",
                    "conditionId": "0xdead_mar27",
                    "question": "Will Protocol Z launch mainnet by March 31?",
                    "description": proto_rules,
                    "endDate": "2027-03-31T23:59:59Z",
                    "clobTokenIds": ["y_mar27", "n_mar27"],
                },
                {
                    "id": "6301107",
                    "conditionId": "0xdead_nov26",
                    "question": "Will Protocol Z launch mainnet by November 15?",
                    "description": proto_rules,
                    "endDate": "2026-11-15T23:59:59Z",
                    "clobTokenIds": ["y_nov26", "n_nov26"],
                },
                # Yearless deadline pair sharing a far-future umbrella endDate (2028-12-31) -> year is ambiguous, MUST quarantine!
                {
                    "id": "m_amb_mar",
                    "conditionId": "0xamb_mar",
                    "question": "Will Country Q join Treaty W by March 31?",
                    "description": proto_rules,
                    "endDate": "2028-12-31T23:59:59Z",
                    "clobTokenIds": ["y_am1", "n_am1"],
                },
                {
                    "id": "m_amb_nov",
                    "conditionId": "0xamb_nov",
                    "question": "Will Country Q join Treaty W by November 15?",
                    "description": proto_rules,
                    "endDate": "2028-12-31T23:59:59Z",
                    "clobTokenIds": ["y_am2", "n_am2"],
                },
                # Explicit year contradicted by inverted endDate -> MUST quarantine!
                {
                    "id": "m_inv_end_early",
                    "conditionId": "0xinv_e1",
                    "question": "Will Satellite V launch by June 30, 2027?",
                    "description": proto_rules,
                    "endDate": "2027-12-31T23:59:59Z",
                    "clobTokenIds": ["y_ie1", "n_ie1"],
                },
                {
                    "id": "m_inv_end_late",
                    "conditionId": "0xinv_e2",
                    "question": "Will Satellite V launch by September 30, 2027?",
                    "description": proto_rules,
                    "endDate": "2027-07-15T23:59:59Z",
                    "clobTokenIds": ["y_ie2", "n_ie2"],
                },
            ]
        )

        self.assertFalse(graph.markets["6301107"].proposition.deadline_year_ambiguous)
        self.assertFalse(graph.markets["6438437"].proposition.deadline_year_ambiguous)
        self.assertLess(
            int(graph.markets["6301107"].proposition.deadline_ts or 0),
            int(graph.markets["6438437"].proposition.deadline_ts or 0),
        )

        verified_pairs = {
            (e.source_market_id, e.target_market_id)
            for e in graph.edges.values()
            if e.edge_type == EdgeType.VERIFIED_MATHEMATICAL and e.source_market_id != e.target_market_id
        }
        # ONLY `6301107` (Nov 15, 2026) => `6438437` (Mar 31, 2027) is VERIFIED_MATHEMATICAL!
        # NEVER `6438437 => 6301107`, and ZERO VERIFIED_MATHEMATICAL edges on ambiguous/inverted endDate pairs!
        self.assertEqual(verified_pairs, {("6301107", "6438437")})

        amb_edges = [e for e in graph.get_edges_for_market("m_amb_mar") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(amb_edges), 1)
        self.assertEqual(amb_edges[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertIn("AMBIGUOUS_YEARLESS_DEADLINE", amb_edges[0].disqualifiers)

        inv_edges = [e for e in graph.get_edges_for_market("m_inv_end_early") if e.source_market_id != e.target_market_id]
        self.assertEqual(len(inv_edges), 1)
        self.assertEqual(inv_edges[0].edge_type, EdgeType.SUSPECTED_REQUIRES_PROOF)
        self.assertIn("DEADLINE_VS_ENDDATE_ORDER_INVERSION", inv_edges[0].disqualifiers)

    def test_live_gamma_pattern_path_dependent_hit_reach_touch_barrier_quarantine(self) -> None:
        graph = MarketPropositionGraph()
        rules_trump_mkt_creation_le = (
            "This market will resolve to “Yes” if Donald Trump’s approval rating according to Silver Bulletin "
            "is equal to or below the listed value for any date between market creation and December 31, 2026."
        )
        rules_trump_jan1_le = (
            "This market will resolve to “Yes” if Donald Trump’s approval rating according to Silver Bulletin "
            "is equal to or below the listed value for any date between January 1 and December 31, 2026."
        )
        rules_fdv_hyperbeat = (
            "This market will resolve to \"Yes\" if the Fully Diluted Valuation of Hyperbeat's token is greater "
            "than the value specified in the title 1 day after launch."
        )
        rules_fdv_standx = (
            "This market will resolve to \"Yes\" if the Fully Diluted Valuation of StandX's token is greater "
            "than the value specified in the title 1 day after launch."
        )

        graph.ingest_events_and_markets(
            events=[
                # Live Event 73128: `"hit 36%"` / `"hit 34%"` / `"hit 35%"` / `"hit 25%"` path-dependent barrier traps
                {
                    "id": "73128",
                    "slug": "how-low-high-will-trumps-approval-rating-go-in-2026",
                    "title": "How low/high will Trump's approval rating go in 2026?",
                    "category": "politics",
                    "negRisk": False,
                    "markets": [
                        {
                            "market_id": "4804046",
                            "condition_id": "0xtrump_hit36",
                            "question": "Will Trump's approval rating hit 36% in 2026?",
                            "group_item_title": "36%",
                            "rule_summary": rules_trump_mkt_creation_le,
                            "description_rule_hash": "hash_mkt_creation_le",
                            "end_date_iso": "2026-12-31T23:59:59Z",
                            "token_ids_json": json.dumps(["y_t36", "n_t36"]),
                            "outcomes_json": json.dumps(["Yes", "No"]),
                        },
                        {
                            "market_id": "4804032",
                            "condition_id": "0xtrump_hit34",
                            "question": "Will Trump's approval rating hit 34% in 2026?",
                            "group_item_title": "34%",
                            "rule_summary": rules_trump_mkt_creation_le,
                            "description_rule_hash": "hash_mkt_creation_le",
                            "end_date_iso": "2026-12-31T23:59:59Z",
                            "token_ids_json": json.dumps(["y_t34", "n_t34"]),
                            "outcomes_json": json.dumps(["Yes", "No"]),
                        },
                        {
                            "market_id": "665369",
                            "condition_id": "0xtrump_hit35",
                            "question": "Will Trump's approval rating hit 35% in 2026?",
                            "group_item_title": "35%",
                            "rule_summary": rules_trump_jan1_le,
                            "description_rule_hash": "hash_jan1_le",
                            "end_date_iso": "2026-12-31T23:59:59Z",
                            "token_ids_json": json.dumps(["y_t35", "n_t35"]),
                            "outcomes_json": json.dumps(["Yes", "No"]),
                        },
                        {
                            "market_id": "665371",
                            "condition_id": "0xtrump_hit25",
                            "question": "Will Trump's approval rating hit 25% in 2026?",
                            "group_item_title": "25%",
                            "rule_summary": rules_trump_jan1_le,
                            "description_rule_hash": "hash_jan1_le",
                            "end_date_iso": "2026-12-31T23:59:59Z",
                            "token_ids_json": json.dumps(["y_t25", "n_t25"]),
                            "outcomes_json": json.dumps(["Yes", "No"]),
                        },
                    ],
                },
                # Live Terminal FDV Snapshot Ladder (`690594` above $400M => `690593` above $300M) -> MUST stay VERIFIED_MATHEMATICAL!
                {
                    "id": "ev_hyperbeat_fdv",
                    "slug": "hyperbeat-fdv-above-one-day-after-launch",
                    "title": "Hyperbeat FDV above ___ one day after launch?",
                    "category": "crypto",
                    "negRisk": False,
                    "markets": [
                        {
                            "id": "690594",
                            "conditionId": "0xhb_400m",
                            "question": "Hyperbeat FDV above $400M one day after launch?",
                            "groupItemTitle": ">$400M",
                            "description": rules_fdv_hyperbeat,
                            "endDate": "2026-12-31T23:59:59Z",
                            "clobTokenIds": ["y_hb400", "n_hb400"],
                            "outcomes": ["Yes", "No"],
                        },
                        {
                            "id": "690593",
                            "conditionId": "0xhb_300m",
                            "question": "Hyperbeat FDV above $300M one day after launch?",
                            "groupItemTitle": ">$300M",
                            "description": rules_fdv_hyperbeat,
                            "endDate": "2026-12-31T23:59:59Z",
                            "clobTokenIds": ["y_hb300", "n_hb300"],
                            "outcomes": ["Yes", "No"],
                        },
                    ],
                },
            ],
            standalone_markets=[
                # Standalone Terminal FDV Snapshot Ladder (`676518` above $1B => `2831225` above $50M) -> MUST be VERIFIED_MATHEMATICAL!
                {
                    "id": "676518",
                    "conditionId": "0xstx_1b",
                    "question": "StandX FDV above $1B one day after launch?",
                    "description": rules_fdv_standx,
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["y_stx1b", "n_stx1b"],
                },
                {
                    "id": "2831225",
                    "conditionId": "0xstx_50m",
                    "question": "StandX FDV above $50M one day after launch?",
                    "description": rules_fdv_standx,
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["y_stx50m", "n_stx50m"],
                },
                # Standalone Crypto `"reach"` / `"dip to"` barriers WITHOUT rules text -> MUST ALSO quarantine!
                {
                    "id": "m_eth_reach_5k",
                    "conditionId": "0xeth_r5k",
                    "question": "Will Ethereum reach $5,000 in 2026?",
                    "description": "",
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["y_er5k", "n_er5k"],
                },
                {
                    "id": "m_eth_reach_4k",
                    "conditionId": "0xeth_r4k",
                    "question": "Will Ethereum reach $4,000 in 2026?",
                    "description": "",
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["y_er4k", "n_er4k"],
                },
                {
                    "id": "m_eth_dip_2k",
                    "conditionId": "0xeth_d2k",
                    "question": "Will Ethereum dip to $2,000 in 2026?",
                    "description": "",
                    "endDate": "2026-12-31T23:59:59Z",
                    "clobTokenIds": ["y_ed2k", "n_ed2k"],
                },
            ],
        )

        # 1. All Event 73128 `"hit <K>%"` markets & ETH `"reach"`/`"dip to"` markets are flagged `is_path_dependent_barrier == True`
        for mid_bar in ("4804046", "4804032", "665369", "665371", "m_eth_reach_5k", "m_eth_reach_4k", "m_eth_dip_2k"):
            self.assertTrue(graph.markets[mid_bar].proposition.is_path_dependent_barrier, msg=mid_bar)

        # 2. Terminal FDV snapshot inequalities are NOT path-dependent barriers
        for mid_fdv in ("690594", "690593", "676518", "2831225"):
            self.assertFalse(graph.markets[mid_fdv].proposition.is_path_dependent_barrier, msg=mid_fdv)

        verified_pairs = {
            (e.source_market_id, e.target_market_id)
            for e in graph.edges.values()
            if e.edge_type == EdgeType.VERIFIED_MATHEMATICAL and e.source_market_id != e.target_market_id
        }
        # ONLY the terminal snapshot FDV ladders (`690594 => 690593` and `676518 => 2831225`) are VERIFIED_MATHEMATICAL!
        # ZERO `VERIFIED_MATHEMATICAL` edges on Event 73128 (`4804046`, `4804032`, `665369`, `665371`) or ETH `reach`/`dip to`!
        self.assertEqual(verified_pairs, {("690594", "690593"), ("676518", "2831225")})

        # 3. Event 73128 cross-market edges exist ONLY as `SUSPECTED_REQUIRES_PROOF` (both event-sibling `EVT:` and
        #    subject-ladder `SUBJ:` groups), with explicit barrier + creation-window + polarity disqualifiers on `SUBJ:`
        ev73128_cross = [
            e
            for mid in ("4804046", "4804032", "665369", "665371")
            for e in graph.get_edges_for_market(mid)
            if e.source_market_id != e.target_market_id
        ]
        self.assertGreaterEqual(len(ev73128_cross), 3)
        self.assertTrue(all(e.edge_type == EdgeType.SUSPECTED_REQUIRES_PROOF for e in ev73128_cross))
        subj_ev73128 = [e for e in ev73128_cross if e.group_key.startswith("SUBJ:")]
        self.assertGreaterEqual(len(subj_ev73128), 3)
        self.assertTrue(
            all("PATH_DEPENDENT_BARRIER_REQUIRES_SPOT_AND_WINDOW_PROOF" in e.disqualifiers for e in subj_ev73128)
        )
        e_4804 = [e for e in subj_ev73128 if {e.source_market_id, e.target_market_id} == {"4804046", "4804032"}]
        self.assertEqual(len(e_4804), 2)  # Both endpoints index the same undirected quarantine edge
        self.assertIn("MARKET_CREATION_RELATIVE_WINDOW_REQUIRES_TIMESTAMP_PROOF", e_4804[0].disqualifiers)
        self.assertIn("AMBIGUOUS_OR_NON_STANDARD_OUTCOME_POLARITY:CONFLICT_DESC_LE_VS_TITLE_GE", e_4804[0].disqualifiers)


if __name__ == "__main__":
    unittest.main()

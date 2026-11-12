"""
Unit & Adversarial Verification Suite for `detectors_complete_set_and_negrisk.py`
(`tests/test_detectors_complete_set_and_negrisk.py`).

Uses Python stdlib `unittest.TestCase` exclusively (`D-010` compliant).
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.polymarket_research.detectors_complete_set_and_negrisk import (
    CompleteSetAndNegRiskDetectorSuite,
    audit_existing_complete_set_and_negrisk_gaps,
    detect_family_a_binary_complete_sets,
    detect_family_b_multi_outcome_complete_sets,
    detect_family_c_negrisk_conversions,
    detect_family_j_inventory_recycling,
    extract_market_fee_params,
    is_d001_frozen_position,
    partition_portfolio_positions_d001,
    prove_multi_outcome_partition_completeness,
)
from src.polymarket_research.universal_arb_verifier import (
    OpportunityClass,
    VerificationConfig,
)


NOW_FIXED = 1_794_400_000.0


def _make_book(asks, bids, *, ts=NOW_FIXED, tick="0.01", min_size="5"):
    return {
        "timestamp": str(int(ts * 1000)),
        "tick_size": tick,
        "min_order_size": min_size,
        "asks": [{"price": str(p), "size": str(s)} for p, s in asks],
        "bids": [{"price": str(p), "size": str(s)} for p, s in bids],
    }


def _make_closed_negrisk_event(
    event_id: str,
    labels: list[str],
    *,
    augmented: bool = False,
    fee_bips: int = 0,
    include_other: bool = False,
    closed_indices: set[int] | None = None,
    q_indices: list[int] | None = None,
) -> dict:
    closed_set = closed_indices or set()
    markets = []
    for idx, lbl in enumerate(labels):
        qi = q_indices[idx] if q_indices is not None else idx
        qid = f"0x{'ab' * 30}{qi:04x}"
        is_oth = bool(include_other and lbl.strip().lower() == "other")
        markets.append(
            {
                "id": f"{event_id}_m{idx}",
                "conditionId": f"0xcond_{event_id}_{idx}",
                "questionID": qid,
                "question": f"Will {lbl} win {event_id}?",
                "groupItemTitle": lbl,
                "outcomes": ["Yes", "No"],
                "clobTokenIds": [f"{event_id}_yes_{idx}", f"{event_id}_no_{idx}"],
                "active": True,
                "closed": idx in closed_set,
                "enableOrderBook": True,
                "negRisk": True,
                "negRiskAugmented": augmented,
                "negRiskOther": is_oth,
                "feesEnabled": False,
                "endDate": "2026-12-31T23:59:59Z",
            }
        )
    return {
        "id": event_id,
        "title": f"Who wins {event_id}?",
        "negRisk": True,
        "enableNegRisk": True,
        "negRiskAugmented": augmented,
        "negRiskFeeBips": fee_bips,
        "markets": markets,
    }


class TestDetectorsCompleteSetAndNegRisk(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg_live_nav = VerificationConfig(
            max_budget_usd=48.70,
            reconciled_nav_usd=48.70,
            d007_multileg_nav_floor_usd=500.0,
            now_ts=NOW_FIXED,
            enforce_min_marketable_notional=True,
        )
        self.cfg_high_nav = VerificationConfig(
            max_budget_usd=1000.0,
            reconciled_nav_usd=1000.0,
            d007_multileg_nav_floor_usd=500.0,
            now_ts=NOW_FIXED,
            enforce_min_marketable_notional=True,
        )

    def test_01_existing_codebase_gap_audit_and_fee_parser(self) -> None:
        audit = audit_existing_complete_set_and_negrisk_gaps()
        gap_ids = {g["gap_id"] for g in audit["identified_gaps"]}
        for expected_id in ("GAP-AB-01", "GAP-AB-02", "GAP-AB-03", "GAP-B-04", "GAP-C-05", "GAP-C-06", "GAP-J-07"):
            self.assertIn(expected_id, gap_ids)

        # Verify `takerBaseFee=1000` (10% protocol ceiling) does NOT override explicit `feeSchedule.rate`!
        mkt_sched = {
            "feesEnabled": True,
            "takerBaseFee": 1000,
            "feeSchedule": {"rate": 0.04, "exponent": 1},
        }
        rate, bps, exp = extract_market_fee_params(mkt_sched)
        self.assertAlmostEqual(rate, 0.04, places=6)
        self.assertEqual(bps, 400)
        self.assertEqual(exp, 1)

        mkt_zero = {"feesEnabled": False, "takerBaseFee": 1000}
        r0, b0, _ = extract_market_fee_params(mkt_zero)
        self.assertEqual(r0, 0.0)
        self.assertEqual(b0, 0)

    def test_02_family_a_binary_buy_merge_and_split_sell_l2_q_star(self) -> None:
        # Include `negRisk: True` child binary + unsorted CLOB `/books` (`asks` desc, `bids` asc)
        mkt = {
            "id": "m_bin_1",
            "conditionId": "0xcond_bin_1",
            "question": "Will Team Alpha win Game 1?",
            "outcomes": ["Yes", "No"],
            "clobTokenIds": ["tok_y1", "tok_n1"],
            "active": True,
            "closed": False,
            "enableOrderBook": True,
            "negRisk": True,
            "feesEnabled": False,
            "endDate": "2026-11-12T00:00:00Z",
        }
        # Unsorted asks: best is `20 @ 0.46` + `20 @ 0.48` = `0.94` (`+$0.06/sh` = `+$1.20` on 20 sh);
        # deeper rung `100 @ 0.55` + `100 @ 0.55` = `1.10` (`-$0.10/sh` marginal loss -> `q*` MUST stop at 20.0!)
        books = {
            "tok_y1": _make_book(
                asks=[(0.55, 100.0), (0.46, 20.0)],
                bids=[(0.30, 50.0), (0.44, 20.0)],
            ),
            "tok_n1": _make_book(
                asks=[(0.55, 100.0), (0.48, 20.0)],
                bids=[(0.31, 50.0), (0.45, 20.0)],
            ),
        }
        res = detect_family_a_binary_complete_sets([mkt], books, config=self.cfg_live_nav)
        a1 = [c for c in res if c.subfamily == "A1_BINARY_BUY_AND_MERGE"]
        self.assertEqual(len(a1), 1)
        self.assertEqual(a1[0].opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertAlmostEqual(a1[0].optimal_shares_q, 20.0, places=4)
        self.assertAlmostEqual(a1[0].min_state_net_payoff_usd, 1.20, places=4)
        self.assertFalse(a1[0].d007_sub500_multileg_quarantine)  # 2-leg binary allowed < $500 NAV!

        # Test A2 Split-and-Sell (`bid(YES)=0.54 + bid(NO)=0.52 = 1.06 > $1.00`) on dynamic fee market (`rate=0.04`)
        mkt_fee = {
            **mkt,
            "id": "m_bin_fee",
            "clobTokenIds": ["tok_yf", "tok_nf"],
            "feesEnabled": True,
            "feeSchedule": {"rate": 0.04, "exponent": 1},
        }
        books_fee = {
            "tok_yf": _make_book(asks=[(0.58, 30.0)], bids=[(0.54, 25.0)]),
            "tok_nf": _make_book(asks=[(0.56, 30.0)], bids=[(0.52, 25.0)]),
        }
        res_fee = detect_family_a_binary_complete_sets([mkt_fee], books_fee, config=self.cfg_live_nav)
        a2 = [c for c in res_fee if c.subfamily == "A2_BINARY_SPLIT_AND_SELL"]
        self.assertEqual(len(a2), 1)
        self.assertEqual(a2[0].opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertGreater(a2[0].taker_fees_usd, 0.0)
        self.assertGreater(a2[0].min_state_net_payoff_usd, 0.50)

    def test_03_family_a_crossed_book_and_dormant_near_arb_detection(self) -> None:
        mkt_crossed = {
            "id": "m_crossed",
            "conditionId": "0xcond_crossed",
            "question": "Crossed market?",
            "outcomes": ["Yes", "No"],
            "clobTokenIds": ["cy", "cn"],
            "active": True,
            "closed": False,
            "enableOrderBook": True,
            "feesEnabled": False,
        }
        books_crossed = {
            "cy": _make_book(asks=[(0.48, 20.0)], bids=[(0.50, 20.0)]),  # crossed!
            "cn": _make_book(asks=[(0.48, 20.0)], bids=[(0.45, 20.0)]),
        }
        res_cr = detect_family_a_binary_complete_sets([mkt_crossed], books_crossed, config=self.cfg_live_nav)
        self.assertTrue(all(c.opportunity_class == OpportunityClass.CLASS_D.value for c in res_cr))

        # Dormant near-arb: `ask(YES)=0.50 + ask(NO)=0.51 = 1.01` (`-100 bps` = within `50-250 bps` band)
        mkt_dorm = {**mkt_crossed, "id": "m_dorm", "clobTokenIds": ["dy", "dn"]}
        books_dorm = {
            "dy": _make_book(asks=[(0.50, 50.0)], bids=[(0.49, 50.0)]),
            "dn": _make_book(asks=[(0.51, 50.0)], bids=[(0.49, 50.0)]),
        }
        res_d = detect_family_a_binary_complete_sets([mkt_dorm], books_dorm, config=self.cfg_live_nav)
        self.assertEqual(len(res_d), 2)
        self.assertTrue(all(c.opportunity_class == OpportunityClass.CLASS_E.value and c.is_dormant_near_arb for c in res_d))
        self.assertAlmostEqual(res_d[0].distance_to_breakeven_bps, 100.0, places=1)

    def test_04_family_b_valid_closed_negrisk_vs_standalone_50_50_void_and_d007(self) -> None:
        ev = _make_closed_negrisk_event("ev_nr3", ["Alice", "Bob", "Carol"])
        # Uncrossed books (`bid < ask`) for B1 Buy-All-YES (`0.30 + 0.31 + 0.32 = 0.93 < $1.00`)
        books_b1 = {
            "ev_nr3_yes_0": _make_book(asks=[(0.30, 30.0)], bids=[(0.28, 30.0)]),
            "ev_nr3_no_0": _make_book(asks=[(0.72, 30.0)], bids=[(0.68, 30.0)]),
            "ev_nr3_yes_1": _make_book(asks=[(0.31, 30.0)], bids=[(0.29, 30.0)]),
            "ev_nr3_no_1": _make_book(asks=[(0.71, 30.0)], bids=[(0.67, 30.0)]),
            "ev_nr3_yes_2": _make_book(asks=[(0.32, 30.0)], bids=[(0.30, 30.0)]),
            "ev_nr3_no_2": _make_book(asks=[(0.70, 30.0)], bids=[(0.66, 30.0)]),
        }
        # Uncrossed books (`bid < ask`) for B2 Split/Convert-Sell-All-YES (`0.36 + 0.35 + 0.35 = 1.06 > $1.00`)
        books_b2 = {
            "ev_nr3_yes_0": _make_book(asks=[(0.38, 30.0)], bids=[(0.36, 30.0)]),
            "ev_nr3_no_0": _make_book(asks=[(0.65, 30.0)], bids=[(0.62, 30.0)]),
            "ev_nr3_yes_1": _make_book(asks=[(0.37, 30.0)], bids=[(0.35, 30.0)]),
            "ev_nr3_no_1": _make_book(asks=[(0.66, 30.0)], bids=[(0.63, 30.0)]),
            "ev_nr3_yes_2": _make_book(asks=[(0.37, 30.0)], bids=[(0.35, 30.0)]),
            "ev_nr3_no_2": _make_book(asks=[(0.66, 30.0)], bids=[(0.63, 30.0)]),
        }
        # At `$48.70` live NAV, 3-leg sequential CLOB arbs are `CLASS_B` with `d007_sub500_multileg_quarantine == True`
        res_low = detect_family_b_multi_outcome_complete_sets([ev], books_b1, config=self.cfg_live_nav)
        b1_low = [c for c in res_low if c.subfamily == "B1_MULTI_OUTCOME_BUY_ALL_YES"][0]
        self.assertEqual(b1_low.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertTrue(b1_low.d007_sub500_multileg_quarantine)
        self.assertEqual(b1_low.execution_mode_cap, "MODE_2_SHADOW")

        # At `$1,000` NAV (`>= $500`), `d007_sub500_multileg_quarantine` is `False`
        res_hi_b1 = detect_family_b_multi_outcome_complete_sets([ev], books_b1, config=self.cfg_high_nav)
        b1 = [c for c in res_hi_b1 if c.subfamily == "B1_MULTI_OUTCOME_BUY_ALL_YES"][0]
        res_hi_b2 = detect_family_b_multi_outcome_complete_sets([ev], books_b2, config=self.cfg_high_nav)
        b2 = [c for c in res_hi_b2 if c.subfamily == "B2_MULTI_OUTCOME_SPLIT_CONVERT_SELL_ALL"][0]
        self.assertFalse(b1.d007_sub500_multileg_quarantine)
        self.assertAlmostEqual(b1.min_state_net_payoff_usd, 30.0 * 0.07, places=3)  # 1.00 - (0.30+0.31+0.32) = 0.07
        self.assertAlmostEqual(b2.min_state_net_payoff_usd, 30.0 * 0.06, places=3)  # (0.36+0.35+0.35) - 1.00 = 0.06
        # Verify peak intra-tx split collateral on `B2` (`2x split` = `2.0 * 30 = $60.00`)
        self.assertAlmostEqual(b2.peak_intratx_collateral_usd, 60.0, places=3)

        # Standalone non-NegRisk verified 3-way 1X2 event: `B2` (`Split $3 -> Sell All YES, Hold All NO`)
        # MUST be downgraded to `CLASS_C` because `50-50` cancellation pays `0.50 * 3 = $1.50 < $3.00 - $1.06 = $1.94`!
        ev_standalone = {
            "id": "ev_std",
            "title": "Match 1X2 regulation?",
            "negRisk": False,
            "verified_exhaustive_non_negrisk": True,
            "markets": [
                {
                    "id": f"std_{i}",
                    "conditionId": f"0xstd_{i}",
                    "question": f"Outcome {lbl}?",
                    "groupItemTitle": lbl,
                    "outcomes": ["Yes", "No"],
                    "clobTokenIds": [f"ev_nr3_yes_{i}", f"ev_nr3_no_{i}"],
                    "active": True,
                    "closed": False,
                    "enableOrderBook": True,
                    "negRisk": False,
                    "feesEnabled": False,
                }
                for i, lbl in enumerate(["Home Win", "Draw", "Away Win"])
            ],
        }
        res_std = detect_family_b_multi_outcome_complete_sets([ev_standalone], books_b2, config=self.cfg_high_nav)
        b2_std = [c for c in res_std if c.subfamily == "B2_MULTI_OUTCOME_SPLIT_CONVERT_SELL_ALL"][0]
        self.assertIn(b2_std.opportunity_class, (OpportunityClass.CLASS_C.value, OpportunityClass.CLASS_E.value))
        self.assertNotIn(b2_std.opportunity_class, (OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value))
        self.assertLess(b2_std.min_state_net_payoff_usd, 0.0)

    def test_05_family_b_adversarial_non_exhaustive_and_partial_slate_rejections(self) -> None:
        cheap_books = {}
        for i in range(4):
            cheap_books[f"ty_{i}"] = _make_book(asks=[(0.20, 50.0)], bids=[(0.19, 50.0)])
            cheap_books[f"tn_{i}"] = _make_book(asks=[(0.80, 50.0)], bids=[(0.79, 50.0)])

        def _mk_std(ev_id: str, title: str, items: list[tuple[str, str]], *, desc: str = "") -> dict:
            return {
                "id": ev_id,
                "title": title,
                "description": desc,
                "negRisk": False,
                "markets": [
                    {
                        "id": f"{ev_id}_{i}",
                        "conditionId": f"0x{ev_id}_{i}",
                        "question": q_txt,
                        "groupItemTitle": g_txt,
                        "description": desc,
                        "outcomes": ["Yes", "No"],
                        "clobTokenIds": [f"ty_{i}", f"tn_{i}"],
                        "active": True,
                        "closed": False,
                        "enableOrderBook": True,
                        "negRisk": False,
                        "feesEnabled": False,
                    }
                    for i, (g_txt, q_txt) in enumerate(items)
                ],
            }

        # 1. Non-exhaustive candidate list (`sum ask = $0.60 < $1.00`, no catch-all!)
        ev_cands = _mk_std(
            "trap_cands",
            "Next CEO of MegaCorp?",
            [("Alice", "Will Alice be next CEO?"), ("Bob", "Will Bob be next CEO?"), ("Carol", "Will Carol be next CEO?")],
        )
        # 2. Cumulative deadline series (`by June 30`, `by Dec 31`)
        ev_cum = _mk_std(
            "trap_cum",
            "Rate cut timing?",
            [("June 30", "Rate cut by June 30, 2027?"), ("December 31", "Rate cut by December 31, 2027?")],
        )
        # 3. Unilateral threshold ladder (`> $90k`, `> $100k`)
        ev_thr = _mk_std(
            "trap_thr",
            "BTC milestones",
            [("> $90k", "Will BTC reach above $90,000?"), ("> $100k", "Will BTC reach above $100,000?")],
        )
        # 4. Sports multi-prop bundle (`Moneyline`, `Spread -3.5`, `Over/Under 220.5`)
        ev_sports = _mk_std(
            "trap_sports",
            "Lakers vs Celtics",
            [("Moneyline", "Lakers win?"), ("Spread -3.5", "Lakers Spread -3.5?"), ("O/U 220.5", "Over/Under 220.5?")],
        )
        # 5. Conditional IPO valuation slate without `"No IPO"` catch-all
        ev_ipo = _mk_std(
            "trap_ipo",
            "Stripe IPO valuation?",
            [("< $50B", "IPO under $50B?"), ("$50B-$80B", "IPO $50B to $80B?"), ("Other > $80B", "IPO over $80B?")],
            desc="If Stripe does not IPO by Dec 31, 2026, this market resolves to No.",
        )
        # 6. Partial NegRisk slate with a closed child (`BUG-MV-4`) and gapped `question_index`
        ev_closed_slot = _make_closed_negrisk_event("trap_closed_nr", ["A", "B", "C"], closed_indices={2})
        ev_gapped_idx = _make_closed_negrisk_event("trap_gap_nr", ["A", "B"], q_indices=[0, 2])
        for i in range(3):
            cheap_books[f"trap_closed_nr_yes_{i}"] = _make_book(asks=[(0.25, 50.0)], bids=[(0.24, 50.0)])
            cheap_books[f"trap_closed_nr_no_{i}"] = _make_book(asks=[(0.75, 50.0)], bids=[(0.74, 50.0)])
            if i < 2:
                cheap_books[f"trap_gap_nr_yes_{i}"] = _make_book(asks=[(0.25, 50.0)], bids=[(0.24, 50.0)])
                cheap_books[f"trap_gap_nr_no_{i}"] = _make_book(asks=[(0.75, 50.0)], bids=[(0.74, 50.0)])

        traps = [ev_cands, ev_cum, ev_thr, ev_sports, ev_ipo, ev_closed_slot, ev_gapped_idx]
        for trap_ev in traps:
            p = prove_multi_outcome_partition_completeness(trap_ev)
            self.assertFalse(p.is_valid_complete_set, msg=f"Failed to reject {trap_ev['id']}")
            self.assertGreater(len(p.counterexample_states), 0, msg=f"Missing counterexample on {trap_ev['id']}")

        res_b = detect_family_b_multi_outcome_complete_sets(traps, cheap_books, config=self.cfg_high_nav)
        self.assertGreaterEqual(len(res_b), 7)
        for cand in res_b:
            self.assertEqual(cand.opportunity_class, OpportunityClass.CLASS_D.value, msg=cand.candidate_id)

    def test_06_family_c_negrisk_m1_subset_allno_synthetic_and_augmented_block(self) -> None:
        # 4-outcome closed NegRisk slate (`negRiskFeeBips = 100` -> `1%` conversion fee)
        ev = _make_closed_negrisk_event("ev_c4", ["North", "South", "East", "West"], fee_bips=100)
        books = {
            # `NO_0` @ $0.25 converts into `0.99 * (YES_1 + YES_2 + YES_3)` sold @ `0.28 + 0.28 + 0.28 = 0.84 * 0.99 = 0.8316`!
            "ev_c4_no_0": _make_book(asks=[(0.25, 40.0)], bids=[(0.23, 40.0)]),
            "ev_c4_yes_0": _make_book(asks=[(0.76, 40.0)], bids=[(0.72, 40.0)]),
            "ev_c4_no_1": _make_book(asks=[(0.68, 40.0)], bids=[(0.65, 40.0)]),
            "ev_c4_yes_1": _make_book(asks=[(0.35, 40.0)], bids=[(0.28, 40.0)]),
            "ev_c4_no_2": _make_book(asks=[(0.68, 40.0)], bids=[(0.65, 40.0)]),
            "ev_c4_yes_2": _make_book(asks=[(0.35, 40.0)], bids=[(0.28, 40.0)]),
            "ev_c4_no_3": _make_book(asks=[(0.68, 40.0)], bids=[(0.65, 40.0)]),
            "ev_c4_yes_3": _make_book(asks=[(0.35, 40.0)], bids=[(0.28, 40.0)]),
        }
        res_c = detect_family_c_negrisk_conversions([ev], books, config=self.cfg_high_nav)
        by_sub = {c.subfamily: c for c in res_c}

        # Verify `C2` (`m = 1` single-NO fanout), `C1` (`m >= 2` subset), `C3` (`m = N` pure cash), `C4` (synth YES), `C6` (freeroll)
        self.assertIn("C2_NEGRISK_M1_FANOUT_CONVERT", by_sub)
        self.assertEqual(by_sub["C2_NEGRISK_M1_FANOUT_CONVERT"].opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertGreater(by_sub["C2_NEGRISK_M1_FANOUT_CONVERT"].min_state_net_payoff_usd, 15.0)

        self.assertIn("C3_NEGRISK_PURE_ALL_NO_CASH_CONVERT", by_sub)
        self.assertEqual(by_sub["C3_NEGRISK_PURE_ALL_NO_CASH_CONVERT"].opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertGreater(by_sub["C3_NEGRISK_PURE_ALL_NO_CASH_CONVERT"].conversion_fee_usd, 0.0)

        self.assertIn("C4_NEGRISK_SYNTHETIC_YES_VS_CLOB", by_sub)
        self.assertEqual(by_sub["C4_NEGRISK_SYNTHETIC_YES_VS_CLOB"].opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertGreater(by_sub["C4_NEGRISK_SYNTHETIC_YES_VS_CLOB"].synthetic_vs_direct_ask_savings_per_share or 0.0, 0.10)

        self.assertIn("C6_NEGRISK_FREEROLL_CONVERT", by_sub)
        self.assertEqual(by_sub["C6_NEGRISK_FREEROLL_CONVERT"].opportunity_class, OpportunityClass.CLASS_B.value)

        # Verify `C5` (`Synthetic NO_i` via complement `{YES_{j != i}}` bundle vs `bid(NO_i)`)
        books_c5 = {
            **books,
            "ev_c4_no_0": _make_book(asks=[(0.92, 40.0)], bids=[(0.90, 40.0)]),
            "ev_c4_yes_1": _make_book(asks=[(0.25, 40.0)], bids=[(0.23, 40.0)]),
            "ev_c4_yes_2": _make_book(asks=[(0.25, 40.0)], bids=[(0.23, 40.0)]),
            "ev_c4_yes_3": _make_book(asks=[(0.25, 40.0)], bids=[(0.23, 40.0)]),
        }
        res_c5 = detect_family_c_negrisk_conversions([ev], books_c5, config=self.cfg_high_nav)
        c5 = [c for c in res_c5 if c.subfamily == "C5_NEGRISK_SYNTHETIC_NO_VS_CLOB"][0]
        self.assertEqual(c5.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertAlmostEqual(c5.net_executable_edge_per_unit, 0.15, places=3)  # 0.90 - (0.25*3) = 0.15

        # CRITICAL SAFETY: Augmented NegRisk (`negRiskAugmented=True`, `Person A`, mutable `"Other"`)
        # MUST NEVER emit `CLASS_A` or `CLASS_B` even with identical ultra-profitable order books!
        ev_aug = _make_closed_negrisk_event(
            "ev_aug",
            ["Candidate Alpha", "Person AB", "Other"],
            augmented=True,
            include_other=True,
        )
        aug_books = {
            f"ev_aug_{side}_{i}": _make_book(asks=[(0.48, 50.0)], bids=[(0.45, 50.0)])
            for i in range(3)
            for side in ("yes", "no")
        }
        res_aug_c = detect_family_c_negrisk_conversions([ev_aug], aug_books, config=self.cfg_high_nav)
        self.assertGreater(len(res_aug_c), 0)
        for cand in res_aug_c:
            self.assertEqual(cand.opportunity_class, OpportunityClass.CLASS_D.value)
            self.assertTrue(
                "AUGMENTED_NEGRISK_OPEN_UNIVERSE" in cand.partition_proof.disqualifiers
                or "UNNAMED_OR_INACTIVE_PLACEHOLDER_OUTCOME_PRESENT" in cand.partition_proof.disqualifiers
                or "MUTABLE_OTHER_OUTCOME_SEMANTIC_SHIFT_RISK" in cand.partition_proof.disqualifiers
            )

    def test_07_family_j_d001_kmia_freeze_and_inventory_wealth_delta(self) -> None:
        # Check real `live_harvester_state.json` hermetic partition invariants if available on disk
        real_state_path = Path(__file__).resolve().parents[1] / "data" / "polymarket" / "live_harvester_state.json"
        if real_state_path.exists():
            real_state = json.loads(real_state_path.read_text(encoding="utf-8"))
            part_real = partition_portfolio_positions_d001(real_state)
            raw_active = (
                real_state.get("active_positions")
                if real_state.get("active_positions") is not None
                else (
                    real_state.get("open_positions")
                    if real_state.get("open_positions") is not None
                    else (real_state.get("positions") or {})
                )
            )
            for fp in part_real["frozen_positions"]:
                self.assertTrue(is_d001_frozen_position(fp)[0])
            for ep in part_real["eligible_positions"]:
                self.assertFalse(is_d001_frozen_position(ep)[0])
            self.assertLessEqual(
                len(part_real["frozen_positions"]) + len(part_real["eligible_positions"]),
                len(raw_active),
            )

        # Construct mixed portfolio with:
        #   (a) Frozen `6707503` & `6707502` `KMIA` disputed positions (even if someone placed tempting books on them!)
        #   (b) Eligible `m_j1` where BOTH `YES` and `NO` (`15` shares each) are held -> `J1` `CLASS_A` atomic merge!
        #   (c) Eligible `m_j2_win` (`20` `YES` shares @ `$0.55` cost, `bid=$0.56`, complement `NO ask=$0.35`)
        #       with tight liquid cash budget `max_budget_usd = $7.50`, `merge_gas = $0.50` -> `20 * 0.35 + 0.50 = $7.50`
        #       exact `q* == 20.0` `CLASS_A` lock (`BUG-MV-6` liquid cash isolation verified!)
        #   (d) Eligible `m_j2_underwater` (`20` `YES` shares @ `$0.80` cost, `bid=$0.30`, complement `NO ask=$0.65`)
        #       -> synthetic merge exit recovers `$0.35 > $0.30` bid (`+$0.05/sh` vs liq), `-45c/sh` vs cost -> `CLASS_C`, NEVER `CLASS_A`!
        #   (e) Eligible `ev_j3` closed 3-slot NegRisk where wallet holds `NO_0` (`12 sh @ $0.40`) + `NO_1` (`12 sh @ $0.42`)
        #       -> `J3` `CLASS_A` pure on-chain convert (`(2-1)*$1.00 = $1.00 > $0.82` cost!)
        portfolio = {
            "open_positions": {
                "WS_SNIPE_Miami_KMIA_242960": {
                    "market_id": "6707503",
                    "token_id": "kmia_tok_1",
                    "shares": 35.0,
                    "entry_price": 0.968,
                    "cost_usd": 33.88,
                    "umaResolutionStatus": "disputed",
                },
                "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                    "market_id": "6707502",
                    "token_id": "kmia_tok_2",
                    "shares": 17.0,
                    "entry_price": 0.978,
                    "cost_usd": 16.63,
                    "umaResolutionStatus": "disputed",
                },
                "ELIG_PAIR_Y": {"market_id": "m_j1", "token_id": "j1_y", "shares": 15.0, "entry_price": 0.47},
                "ELIG_PAIR_N": {"market_id": "m_j1", "token_id": "j1_n", "shares": 15.0, "entry_price": 0.48},
                "ELIG_SINGLE_WIN": {"market_id": "m_j2_win", "token_id": "j2w_y", "shares": 20.0, "entry_price": 0.55},
                "ELIG_SINGLE_UW": {"market_id": "m_j2_uw", "token_id": "j2u_y", "shares": 20.0, "entry_price": 0.80},
                "ELIG_NR_NO0": {"market_id": "ev_j3_m0", "token_id": "ev_j3_no_0", "shares": 12.0, "entry_price": 0.40},
                "ELIG_NR_NO1": {"market_id": "ev_j3_m1", "token_id": "ev_j3_no_1", "shares": 12.0, "entry_price": 0.42},
            }
        }
        bin_mkts = [
            # Tempting fake book on frozen KMIA `6707503` — MUST be 100% ignored per D-001!
            {
                "id": "6707503",
                "conditionId": "0xkmia",
                "question": "KMIA Nov 7 disputed?",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["kmia_comp", "kmia_tok_1"],
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "feesEnabled": False,
            },
            {
                "id": "m_j1",
                "conditionId": "0xmj1",
                "question": "Held complete pair?",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["j1_y", "j1_n"],
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "feesEnabled": False,
            },
            {
                "id": "m_j2_win",
                "conditionId": "0xmj2w",
                "question": "Profitable single-leg lock?",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["j2w_y", "j2w_n"],
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "feesEnabled": False,
            },
            {
                "id": "m_j2_uw",
                "conditionId": "0xmj2u",
                "question": "Underwater spread-saving exit?",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["j2u_y", "j2u_n"],
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "feesEnabled": False,
            },
        ]
        ev_j3 = _make_closed_negrisk_event("ev_j3", ["Opt0", "Opt1", "Opt2"])
        books = {
            "kmia_comp": _make_book(asks=[(0.01, 100.0)], bids=[(0.005, 100.0)]),
            "kmia_tok_1": _make_book(asks=[(0.02, 100.0)], bids=[(0.003, 100.0)]),
            "j1_y": _make_book(asks=[(0.52, 30.0)], bids=[(0.46, 30.0)]),
            "j1_n": _make_book(asks=[(0.52, 30.0)], bids=[(0.47, 30.0)]),
            "j2w_y": _make_book(asks=[(0.62, 30.0)], bids=[(0.56, 30.0)]),
            "j2w_n": _make_book(asks=[(0.35, 30.0)], bids=[(0.33, 30.0)]),
            "j2u_y": _make_book(asks=[(0.40, 30.0)], bids=[(0.30, 30.0)]),
            "j2u_n": _make_book(asks=[(0.65, 30.0)], bids=[(0.60, 30.0)]),
            "ev_j3_no_0": _make_book(asks=[(0.45, 30.0)], bids=[(0.38, 30.0)]),
            "ev_j3_yes_0": _make_book(asks=[(0.62, 30.0)], bids=[(0.55, 30.0)]),
            "ev_j3_no_1": _make_book(asks=[(0.45, 30.0)], bids=[(0.40, 30.0)]),
            "ev_j3_yes_1": _make_book(asks=[(0.60, 30.0)], bids=[(0.55, 30.0)]),
            "ev_j3_no_2": _make_book(asks=[(0.90, 30.0)], bids=[(0.85, 30.0)]),
            "ev_j3_yes_2": _make_book(asks=[(0.18, 30.0)], bids=[(0.15, 30.0)]),
        }

        cfg_tight = VerificationConfig(
            max_budget_usd=15.00,
            reconciled_nav_usd=48.70,
            now_ts=NOW_FIXED,
            enforce_min_marketable_notional=True,
        )
        opps_j, audit = detect_family_j_inventory_recycling(
            portfolio,
            bin_mkts,
            [ev_j3],
            books,
            config=cfg_tight,
            merge_gas_usd=0.50,
            convert_gas_usd=0.10,
        )

        # 1. Verify D-001 KMIA non-interference (`0` candidates touch `6707503` or `6707502`)
        self.assertEqual(audit["d001_frozen_position_count"], 2)
        self.assertAlmostEqual(audit["d001_frozen_cost_basis_usd"], 50.51, places=2)
        for c in opps_j:
            self.assertNotIn("6707503", c.market_ids)
            self.assertNotIn("6707502", c.market_ids)

        by_id = {c.candidate_id: c for c in opps_j}

        # 2. `J1`: Held complete pair merge -> `CLASS_A` (`0` CLOB legs!)
        j1 = by_id["FAM_J1_HELD_PAIR_MERGE_m_j1"]
        self.assertEqual(j1.opportunity_class, OpportunityClass.CLASS_A.value)
        self.assertEqual(j1.clob_leg_count, 0)
        self.assertAlmostEqual(j1.optimal_shares_q, 15.0, places=4)
        self.assertAlmostEqual(j1.capital_required_usd, 0.50, places=4)  # gas only!

        # 3. `J2` profitable lock -> `CLASS_A` (`1` FOK CLOB leg, `20 * 0.35 + 0.50 = $7.50 <= $15.00` liquid cash)
        j2w = by_id["FAM_J2_SINGLE_LEG_LOCK_m_j2_win_Yes"]
        self.assertEqual(j2w.opportunity_class, OpportunityClass.CLASS_A.value)
        self.assertAlmostEqual(j2w.optimal_shares_q, 20.0, places=4)
        self.assertAlmostEqual(j2w.capital_required_usd, 7.50, places=4)
        self.assertAlmostEqual(j2w.delta_wealth_vs_cost_basis_usd or 0.0, 1.50, places=4)  # 20*(1 - 0.55 - 0.35) - 0.50

        # 4. `J2B` underwater spread-saving exit -> `CLASS_C` (NEVER `CLASS_A`!)
        j2u = by_id["FAM_J2B_SPREAD_SAVING_MERGE_EXIT_m_j2_uw_Yes"]
        self.assertEqual(j2u.opportunity_class, OpportunityClass.CLASS_C.value)
        self.assertLess(j2u.delta_wealth_vs_cost_basis_usd or 0.0, 0.0)
        self.assertGreater(j2u.delta_wealth_vs_liquidation_mark_usd or 0.0, 0.0)

        # 5. `J3A` pure on-chain held-NO convert (`0` CLOB legs -> `CLASS_A`)
        j3a = by_id["FAM_J3A_HELD_NO_PURE_CONVERT_ev_j3"]
        self.assertEqual(j3a.opportunity_class, OpportunityClass.CLASS_A.value)
        self.assertAlmostEqual(j3a.optimal_shares_q, 12.0, places=4)
        self.assertGreater(j3a.delta_wealth_min_usd, 2.0)

    def test_08_unified_suite_scan_all_contract(self) -> None:
        ev = _make_closed_negrisk_event("ev_suite", ["Alpha", "Beta"])
        books = {
            "ev_suite_yes_0": _make_book(asks=[(0.44, 25.0)], bids=[(0.42, 25.0)]),
            "ev_suite_no_0": _make_book(asks=[(0.45, 25.0)], bids=[(0.43, 25.0)]),
            "ev_suite_yes_1": _make_book(asks=[(0.46, 25.0)], bids=[(0.44, 25.0)]),
            "ev_suite_no_1": _make_book(asks=[(0.45, 25.0)], bids=[(0.43, 25.0)]),
        }
        suite = CompleteSetAndNegRiskDetectorSuite(config=self.cfg_live_nav)
        bundle = suite.scan_all(events=[ev], books_by_token=books)
        self.assertGreater(len(bundle["all_candidates"]), 0)
        self.assertEqual(len(bundle["proofs"]), len(bundle["all_candidates"]))
        self.assertTrue(bundle["d001_inventory_audit"]["d001_non_interference_verified"])
        for cand in bundle["all_candidates"]:
            self.assertTrue(len(cand.canonical_event_keys) >= 1)
            self.assertEqual(len(cand.proof_sha256), 64)

    def test_09_bounded_numeric_negrisk_missing_tail_blocked(self) -> None:
        ev_missing_tail = _make_closed_negrisk_event(
            "ev_num_no_tail",
            ["10% to 20%", "20% to 30%", "30% to 40%"],
        )
        books = {
            f"ev_num_no_tail_{side}_{i}": _make_book(asks=[(0.25, 40.0)], bids=[(0.22, 40.0)])
            for i in range(3)
            for side in ("yes", "no")
        }
        proof = prove_multi_outcome_partition_completeness(ev_missing_tail)
        self.assertFalse(proof.is_valid_complete_set)
        self.assertIn("NUMERIC_BRACKET_SLATE_MISSING_UNBOUNDED_TAIL", proof.disqualifiers)
        res = detect_family_b_multi_outcome_complete_sets([ev_missing_tail], books, config=self.cfg_high_nav)
        self.assertEqual(res[0].opportunity_class, OpportunityClass.CLASS_D.value)

    def test_10_family_j4_presplit_overround_exit_and_j3b_convert_sweep(self) -> None:
        portfolio = {
            "active_positions": {
                "PS_Y": {"market_id": "m_ps", "token_id": "ps_y", "shares": 25.0, "entry_price": 0.50},
                "PS_N": {"market_id": "m_ps", "token_id": "ps_n", "shares": 25.0, "entry_price": 0.50},
                "NR_SINGLE_NO": {"market_id": "ev_j3b_m0", "token_id": "ev_j3b_no_0", "shares": 15.0, "entry_price": 0.30},
            }
        }
        mkt_ps = {
            "id": "m_ps",
            "conditionId": "0xmps",
            "question": "Pre-split overround market?",
            "outcomes": ["Yes", "No"],
            "clobTokenIds": ["ps_y", "ps_n"],
            "active": True,
            "closed": False,
            "enableOrderBook": True,
            "feesEnabled": False,
        }
        ev_j3b = _make_closed_negrisk_event("ev_j3b", ["Alpha", "Bravo", "Charlie"])
        books = {
            "ps_y": _make_book(asks=[(0.56, 30.0)], bids=[(0.54, 30.0)]),
            "ps_n": _make_book(asks=[(0.55, 30.0)], bids=[(0.53, 30.0)]),
            "ev_j3b_no_0": _make_book(asks=[(0.35, 30.0)], bids=[(0.28, 30.0)]),
            "ev_j3b_yes_0": _make_book(asks=[(0.72, 30.0)], bids=[(0.65, 30.0)]),
            "ev_j3b_no_1": _make_book(asks=[(0.85, 30.0)], bids=[(0.80, 30.0)]),
            "ev_j3b_yes_1": _make_book(asks=[(0.22, 30.0)], bids=[(0.19, 30.0)]),
            "ev_j3b_no_2": _make_book(asks=[(0.85, 30.0)], bids=[(0.80, 30.0)]),
            "ev_j3b_yes_2": _make_book(asks=[(0.22, 30.0)], bids=[(0.19, 30.0)]),
        }
        opps, _ = detect_family_j_inventory_recycling(portfolio, [mkt_ps], [ev_j3b], books, config=self.cfg_high_nav)
        by_id = {c.candidate_id: c for c in opps}
        self.assertIn("FAM_J4_PRESPLIT_OVERROUND_SELL_m_ps", by_id)
        j4 = by_id["FAM_J4_PRESPLIT_OVERROUND_SELL_m_ps"]
        self.assertEqual(j4.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertAlmostEqual(j4.min_state_net_payoff_usd, 25.0 * 0.07, places=3)  # (0.54 + 0.53) - 1.00 = 0.07

        self.assertIn("FAM_J3B_HELD_NO_CONVERT_SELL_YES_ev_j3b", by_id)
        j3b = by_id["FAM_J3B_HELD_NO_CONVERT_SELL_YES_ev_j3b"]
        self.assertEqual(j3b.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertAlmostEqual(j3b.delta_wealth_vs_cost_basis_usd or 0.0, 15.0 * (0.38 - 0.30), places=3)

    def test_11_family_c_single_no_j_synthetic_yes_strip_route(self) -> None:
        ev = _make_closed_negrisk_event("ev_strip", ["TargetA", "SeedB", "StripC"])
        books = {
            "ev_strip_yes_0": _make_book(asks=[(0.65, 30.0)], bids=[(0.55, 30.0)]),
            "ev_strip_no_0": _make_book(asks=[(0.48, 30.0)], bids=[(0.42, 30.0)]),
            # `NO_1` is cheap (`$0.22`), while `NO_2` is expensive (`$0.95`), forcing `M_1_SINGLE_NO_J_STRIP`!
            "ev_strip_yes_1": _make_book(asks=[(0.80, 30.0)], bids=[(0.75, 30.0)]),
            "ev_strip_no_1": _make_book(asks=[(0.22, 30.0)], bids=[(0.19, 30.0)]),
            "ev_strip_yes_2": _make_book(asks=[(0.26, 30.0)], bids=[(0.22, 30.0)]),
            "ev_strip_no_2": _make_book(asks=[(0.95, 30.0)], bids=[(0.88, 30.0)]),
        }
        res = detect_family_c_negrisk_conversions([ev], books, config=self.cfg_high_nav)
        c4 = [c for c in res if c.subfamily == "C4_NEGRISK_SYNTHETIC_YES_VS_CLOB"][0]
        self.assertEqual(c4.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertEqual(c4.metadata.get("synthesis_route"), "M_1_SINGLE_NO_J_STRIP")
        # `NO_1` ($0.22) -> `YES_0 + YES_2`; sell `YES_2` @ $0.22 -> net synthetic `YES_0` cost = `$0.00` vs `$0.65` ask!
        self.assertAlmostEqual(c4.synthetic_vs_direct_ask_savings_per_share or 0.0, 0.65, places=3)


if __name__ == "__main__":
    unittest.main()

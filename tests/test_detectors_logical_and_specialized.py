"""
Comprehensive Adversarial & Mathematical Unit Tests for Opportunity Families D, E, F, G, H & I
(`tests/test_detectors_logical_and_specialized.py`).

Tests every contractual structure, microstructure fee/L2 edge case, safety invariant (`D-001`, `D-006`,
`D-007`), and `@qa-auditor` proof-breaking trap across `detectors_logical_and_specialized.py`.
Runs cleanly on pure stdlib Python 3.12 (`unittest.TestCase`).
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List, Optional, Tuple

from src.polymarket_research.detectors_logical_and_specialized import (
    D006_UNVERIFIED_SENSOR_CUSHION_C,
    LogicalSpecializedScanner,
    MetarObservationSnapshot,
    audit_existing_logical_specialized_scanners,
    build_instrument_order_books,
    collect_candidate_token_ids_d_to_i,
    detect_family_d_logical_arbitrage,
    detect_family_e_temporal_deadline_arbitrage,
    detect_family_f_price_strike_ladders,
    detect_family_g_sports_structures,
    detect_family_h_weather_measurable,
    detect_family_i_duplicate_markets,
    evaluate_explicit_logical_pair,
    normalize_universe_to_canonical_markets,
)
from src.polymarket_research.universal_arb_verifier import (
    InventoryHolding,
    OpportunityClass,
    UniversalArbVerifier,
    VerificationConfig,
)


NOW_TS: float = 1_794_400_000.0  # Fixed deterministic epoch (`2026-11-11 UTC` window)


def _mk_market(
    mid: str,
    question: str,
    *,
    event_id: str = "ev_1",
    event_title: str = "",
    event_slug: str = "",
    group_item_title: str = "",
    description: str = "This market resolves according to Associated Press by 11:59 PM ET.",
    resolution_source: str = "https://apnews.com",
    resolved_by: str = "0xuma_standard_adapter",
    outcomes: Tuple[str, str] = ("Yes", "No"),
    neg_risk: bool = False,
    neg_risk_augmented: bool = False,
    uma_status: str = "",
    fee_rate_bps: float = 0.0,
    fee_exponent: float = 1.0,
    end_date: str = "2026-12-31T23:59:59Z",
    start_date: str = "2026-01-01T00:00:00Z",
    sports_market_type: str = "",
    line: Optional[float] = None,
    tags: Tuple[str, ...] = (),
) -> Dict[str, Any]:
    return {
        "id": mid,
        "conditionId": f"cond_{mid}",
        "event_id": event_id,
        "event_title": event_title or question,
        "event_slug": event_slug,
        "question": question,
        "groupItemTitle": group_item_title,
        "description": description,
        "resolutionSource": resolution_source,
        "resolvedBy": resolved_by,
        "clobTokenIds": [f"tok_{mid}_0", f"tok_{mid}_1"],
        "outcomes": list(outcomes),
        "negRisk": neg_risk,
        "negRiskAugmented": neg_risk_augmented,
        "umaResolutionStatus": uma_status,
        "fee_rate_bps": fee_rate_bps,
        "fee_exponent": fee_exponent,
        "feesEnabled": fee_rate_bps > 0,
        "enableOrderBook": True,
        "acceptingOrders": True,
        "active": True,
        "closed": False,
        "archived": False,
        "orderMinSize": 5.0,
        "endDate": end_date,
        "startDate": start_date,
        "sportsMarketType": sports_market_type,
        "line": line,
        "tags": list(tags),
    }


def _mk_book(ask_px: float, ask_sz: float = 200.0, bid_px: Optional[float] = None, ts: float = NOW_TS) -> Dict[str, Any]:
    b_px = round(max(0.001, ask_px - 0.02), 3) if bid_px is None else bid_px
    # Deliberately supply unsorted multi-rung raw CLOB levels (matching live CLOB `/books` descending asks!)
    return {
        "asks": [
            {"price": str(min(0.99, round(ask_px + 0.03, 3))), "size": "500"},
            {"price": str(ask_px), "size": str(ask_sz)},
        ],
        "bids": [
            {"price": "0.001", "size": "500"},
            {"price": str(b_px), "size": "200"},
        ],
        "timestamp": str(int(ts * 1000)),
    }


def _verifier() -> UniversalArbVerifier:
    return UniversalArbVerifier(config=VerificationConfig(reconciled_nav_usd=48.70, now_ts=NOW_TS))


class TestExistingScannerAudit(unittest.TestCase):
    def test_step1_audit_covers_all_six_families(self) -> None:
        audit = audit_existing_logical_specialized_scanners()
        self.assertEqual(audit["total_families_audited"], 6)
        fams = set(audit["families"].keys())
        self.assertEqual(
            fams,
            {
                "D_cross_market_logical",
                "E_temporal_deadline",
                "F_price_threshold_strike_ladders",
                "G_sports_outcome_structures",
                "H_weather_measurable",
                "I_duplicate_near_duplicate_markets",
            },
        )
        for entry in audit["families"].values():
            self.assertGreaterEqual(len(entry["missed_opportunities"]), 1)
            self.assertGreaterEqual(len(entry["rule_vulnerabilities_identified"]), 1)


class TestFamilyDCrossMarketLogical(unittest.TestCase):
    def test_valid_implication_and_inventory_promotion_vs_converse_and_nl_trap(self) -> None:
        # `m_joint`: Popular Vote AND Presidency => `m_pres`: Presidency (`1 NO_joint + 1 YES_pres`)
        m_joint = _mk_market(
            "d_joint",
            "Will Jane Doe win both the popular vote and the presidential election in 2028?",
            event_id="ev_pop",
            end_date="2028-11-15T23:59:59Z",
        )
        m_pres = _mk_market(
            "d_pres",
            "Will Jane Doe win the 2028 US presidential election?",
            event_id="ev_pres",
            end_date="2028-11-15T23:59:59Z",
        )
        mkts = normalize_universe_to_canonical_markets([m_joint, m_pres])
        raw_books = {
            "tok_d_joint_0": _mk_book(0.55),
            "tok_d_joint_1": _mk_book(0.42),  # NO_A = 0.42
            "tok_d_pres_0": _mk_book(0.51),   # YES_B = 0.51 -> sum = 0.93 < 1.00!
            "tok_d_pres_1": _mk_book(0.50),
        }
        books = build_instrument_order_books(mkts, raw_books, default_fetch_ts=NOW_TS)
        opps, _ = detect_family_d_logical_arbitrage(mkts, books, verifier=_verifier())
        self.assertEqual(len(opps), 1)
        op = opps[0]
        self.assertEqual(op.proof.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertGreater(op.proof.net_executable_edge_per_unit, 0.06)

        # With pre-existing unlocked inventory on `NO_A`, only 1 CLOB leg remains -> promotes to `CLASS_A`!
        holdings = {
            "tok_d_joint_1": InventoryHolding(
                instrument_id="tok_d_joint_1",
                market_id="d_joint",
                shares=25.0,
                cost_basis_per_share=0.40,
            )
        }
        opps_inv, _ = detect_family_d_logical_arbitrage(mkts, books, verifier=_verifier(), holdings=holdings)
        self.assertEqual(opps_inv[0].proof.opportunity_class, OpportunityClass.CLASS_A.value)

        # Adversarial Check 1: Converse `B_IMPLIES_A` (`NO_pres + YES_joint` = 0.50 + 0.55 = 1.05, and NOT implied!)
        # Even if `NO_pres + YES_joint` were priced at 0.80, without formal proof `has_formal_rule_proof=False` -> CLASS_D!
        cheap_converse_books = build_instrument_order_books(
            mkts,
            {
                "tok_d_joint_0": _mk_book(0.35),
                "tok_d_joint_1": _mk_book(0.65),
                "tok_d_pres_0": _mk_book(0.65),
                "tok_d_pres_1": _mk_book(0.35),
            },
            default_fetch_ts=NOW_TS,
        )
        nl_trap = evaluate_explicit_logical_pair(
            mkts[0], mkts[1], cheap_converse_books,
            claimed_relation="B_IMPLIES_A",
            has_formal_rule_proof=False,
            verifier=_verifier(),
        )
        self.assertEqual(nl_trap.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("NATURAL_LANGUAGE_SIMILARITY_ONLY_NO_RULE_PROOF", nl_trap.divergence_or_rejection_reasons)

    def test_unverified_candidate_party_and_asymmetric_void_rejected_to_class_d(self) -> None:
        # Candidate mentions "Republican" loosely in description WITHOUT `(R)` / `Republican nominee` ballot clause
        m_cand = _mk_market(
            "d_cand_unv",
            "Will John Maverick win the 2028 presidential election?",
            event_id="ev_c1",
            description="John Maverick, formerly a Republican governor, resolves Yes per Associated Press.",
            neg_risk=False,  # standalone 50-50 void!
        )
        m_pty = _mk_market(
            "d_pty_rep",
            "Will the Republican Party win the 2028 presidential election?",
            event_id="ev_p1",
            description="Resolves Yes if the Republican candidate wins per Associated Press.",
            neg_risk=True,   # NegRisk NO void!
        )
        mkts = normalize_universe_to_canonical_markets([m_cand, m_pty])
        books = build_instrument_order_books(
            mkts,
            {
                "tok_d_cand_unv_0": _mk_book(0.55),
                "tok_d_cand_unv_1": _mk_book(0.40),
                "tok_d_pty_rep_0": _mk_book(0.50),
                "tok_d_pty_rep_1": _mk_book(0.52),
            },
            default_fetch_ts=NOW_TS,
        )
        opps, rej = detect_family_d_logical_arbitrage(mkts, books, verifier=_verifier())
        self.assertTrue(any(o.proof.opportunity_class == OpportunityClass.CLASS_D.value for o in opps))
        self.assertIn("UNVERIFIED_PARTY_BALLOT_RULE", rej)
        self.assertIn("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO", rej)


class TestFamilyETemporalDeadline(unittest.TestCase):
    def test_valid_temporal_implication_and_survival_reversal_and_timezone_trap(self) -> None:
        desc_et = "Resolves Yes according to official Federal Reserve announcement (federalreserve.gov) by 11:59 PM ET."
        m_q1 = _mk_market(
            "e_mar",
            "Will OpenAI release GPT-6 by March 31, 2027?",
            event_id="ev_gpt_1",
            description=desc_et,
            resolution_source="https://openai.com",
            end_date="2027-04-01T03:59:59Z",
        )
        m_q2 = _mk_market(
            "e_jun",
            "Will OpenAI release GPT-6 by June 30, 2027?",
            event_id="ev_gpt_2",
            description=desc_et,
            resolution_source="https://openai.com",
            end_date="2027-07-01T03:59:59Z",
        )
        # Timezone mismatch market (`UTC` instead of `ET`)
        m_utc_bad = _mk_market(
            "e_sep_utc",
            "Will OpenAI release GPT-6 by September 30, 2027?",
            event_id="ev_gpt_3",
            description="Resolves Yes according to official Federal Reserve announcement (federalreserve.gov) by 23:59 UTC.",
            resolution_source="https://openai.com",
            end_date="2027-09-30T23:59:59Z",
        )
        # Survival pair (`remain in office through T2 => remain in office through T1` -> `NO_T2 + YES_T1`!)
        desc_surv = "Resolves Yes per Associated Press if leader remains in office through 11:59 PM ET on the date."
        m_surv_early = _mk_market(
            "e_surv_1",
            "Will Leader X remain in office through March 31, 2027?",
            event_id="ev_sv1",
            description=desc_surv,
            end_date="2027-04-01T03:59:59Z",
        )
        m_surv_late = _mk_market(
            "e_surv_2",
            "Will Leader X remain in office through December 31, 2027?",
            event_id="ev_sv2",
            description=desc_surv,
            end_date="2028-01-01T04:59:59Z",
        )

        mkts = normalize_universe_to_canonical_markets([m_q1, m_q2, m_utc_bad, m_surv_early, m_surv_late])
        books = build_instrument_order_books(
            mkts,
            {
                "tok_e_mar_0": _mk_book(0.55),
                "tok_e_mar_1": _mk_book(0.43),  # NO_early = 0.43
                "tok_e_jun_0": _mk_book(0.51),  # YES_late = 0.51 -> 0.94 < 1.00!
                "tok_e_jun_1": _mk_book(0.49),
                "tok_e_sep_utc_0": _mk_book(0.45),
                "tok_e_sep_utc_1": _mk_book(0.55),
                # Survival: `NO_late (0.44) + YES_early (0.50) = 0.94 < 1.00`!
                "tok_e_surv_1_0": _mk_book(0.50),
                "tok_e_surv_1_1": _mk_book(0.52),
                "tok_e_surv_2_0": _mk_book(0.58),
                "tok_e_surv_2_1": _mk_book(0.44),
            },
            default_fetch_ts=NOW_TS,
        )
        opps, rej = detect_family_e_temporal_deadline_arbitrage(mkts, books, verifier=_verifier(), now_ts=NOW_TS)
        by_sub = {(o.sub_type, o.market_ids): o for o in opps}

        # 1. Valid first-passage `e_mar => e_jun` is CLASS_B
        valid_fp = [o for o in opps if set(o.market_ids) == {"e_mar", "e_jun"}][0]
        self.assertEqual(valid_fp.proof.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertEqual(valid_fp.structure.legs[0].instrument_id, "tok_e_mar_1")
        self.assertEqual(valid_fp.structure.legs[1].instrument_id, "tok_e_jun_0")

        # 2. Timezone mismatch `e_jun (ET)` vs `e_sep_utc (UTC)` is strictly CLASS_D!
        tz_bad = [o for o in opps if "e_sep_utc" in o.market_ids][0]
        self.assertEqual(tz_bad.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("TIMEZONE_MISMATCH", rej)

        # 3. Survival pair reverses implication direction (`NO_late + YES_early`) -> CLASS_B!
        surv_op = [o for o in opps if set(o.market_ids) == {"e_surv_1", "e_surv_2"}][0]
        self.assertEqual(surv_op.proof.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertEqual(surv_op.relationship_type, "B_IMPLIES_A")
        self.assertEqual(surv_op.structure.legs[0].instrument_id, "tok_e_surv_2_1")  # NO_late!
        self.assertEqual(surv_op.structure.legs[1].instrument_id, "tok_e_surv_1_0")  # YES_early!


class TestFamilyFPriceStrikeLadders(unittest.TestCase):
    def test_upward_dominance_fdv_scaling_and_touch_vs_close_mismatch(self) -> None:
        desc_bin_close = "Resolves to Yes based on Binance BTC/USDT 1m candle close price at 11:59 PM ET on December 31, 2026."
        m_100k = _mk_market(
            "f_btc_100",
            "Will Bitcoin price be at least $100,000 on December 31, 2026?",
            description=desc_bin_close,
            resolution_source="https://www.binance.com/en/trade/BTC_USDT",
            end_date="2027-01-01T04:59:59Z",
            fee_rate_bps=1000.0,  # Crypto taker fee enabled!
        )
        m_110k = _mk_market(
            "f_btc_110",
            "Will Bitcoin price be at least $110,000 on December 31, 2026?",
            description=desc_bin_close,
            resolution_source="https://www.binance.com/en/trade/BTC_USDT",
            end_date="2027-01-01T04:59:59Z",
            fee_rate_bps=1000.0,
        )
        # Touch-anytime contract on same date (`hit $120,000`) -> must be rejected against Close-at-expiry!
        m_120k_touch = _mk_market(
            "f_btc_120_touch",
            "Will Bitcoin reach $120,000 by December 31, 2026?",
            description="Resolves Yes if any Binance BTC/USDT 1-minute candle high hits $120,000 by 11:59 PM ET.",
            resolution_source="https://www.binance.com/en/trade/BTC_USDT",
            end_date="2027-01-01T04:59:59Z",
        )
        # FDV `$900B` vs `$1.2T` scaling test
        desc_fdv = "Resolves Yes based on CoinGecko FDV closing snapshot at 11:59 PM ET on December 31, 2026."
        m_fdv_900b = _mk_market(
            "f_fdv_900b",
            "Will MegaChain FDV be at least $900B on December 31, 2026?",
            description=desc_fdv,
            resolution_source="https://coingecko.com",
            end_date="2027-01-01T04:59:59Z",
        )
        m_fdv_1_2t = _mk_market(
            "f_fdv_1_2t",
            "Will MegaChain FDV be at least $1.2T on December 31, 2026?",
            description=desc_fdv,
            resolution_source="https://coingecko.com",
            end_date="2027-01-01T04:59:59Z",
        )

        mkts = normalize_universe_to_canonical_markets([m_100k, m_110k, m_120k_touch, m_fdv_900b, m_fdv_1_2t])
        books = build_instrument_order_books(
            mkts,
            {
                "tok_f_btc_100_0": _mk_book(0.44),  # YES_100k = 0.44
                "tok_f_btc_100_1": _mk_book(0.56),
                "tok_f_btc_110_0": _mk_book(0.55),
                "tok_f_btc_110_1": _mk_book(0.45),  # NO_110k = 0.45 -> even after V2 1000bps fee (~2.5c/leg), 0.44+0.45+0.05 = 0.94 < 1.00!
                "tok_f_btc_120_touch_0": _mk_book(0.60),
                "tok_f_btc_120_touch_1": _mk_book(0.35),
                "tok_f_fdv_900b_0": _mk_book(0.45),
                "tok_f_fdv_900b_1": _mk_book(0.55),
                "tok_f_fdv_1_2t_0": _mk_book(0.56),
                "tok_f_fdv_1_2t_1": _mk_book(0.46),
            },
            default_fetch_ts=NOW_TS,
        )
        opps, rej = detect_family_f_price_strike_ladders(mkts, books, verifier=_verifier(), now_ts=NOW_TS)

        btc_valid = [o for o in opps if set(o.market_ids) == {"f_btc_110", "f_btc_100"}][0]
        self.assertEqual(btc_valid.proof.opportunity_class, OpportunityClass.CLASS_B.value)
        self.assertGreater(btc_valid.proof.cost_breakdown.taker_fees_usd, 0.0)

        fdv_valid = [o for o in opps if set(o.market_ids) == {"f_fdv_1_2t", "f_fdv_900b"}][0]
        self.assertEqual(fdv_valid.proof.opportunity_class, OpportunityClass.CLASS_B.value)

        touch_traps = [o for o in opps if "f_btc_120_touch" in o.market_ids]
        self.assertTrue(len(touch_traps) >= 1)
        for tr in touch_traps:
            self.assertEqual(tr.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("TOUCH_VS_CLOSE_OBSERVATION_MISMATCH", rej)

    def test_interval_cover_half_open_valid_vs_discrete_gap_and_closed_overlap_trap(self) -> None:
        # Case A: Clean half-open `[90000, 100000)` + `>= 100000` vs `>= 90000`
        desc_half_open = "Resolves Yes if Binance ETH/USDT close at 12:00 PM ET on Dec 31, 2026 is at least $90,000 and strictly less than $100,000."
        desc_close = "Resolves Yes if Binance ETH/USDT close at 12:00 PM ET on Dec 31, 2026 satisfies the strike."
        m_rg = _mk_market("f_rg_ok", "Will BTC close between $90,000 and $100,000 on Dec 31, 2026?", description=desc_half_open, end_date="2026-12-31T17:00:00Z")
        m_ge90 = _mk_market("f_ge_90", "Will BTC close at least $90,000 on Dec 31, 2026?", description=desc_close, end_date="2026-12-31T17:00:00Z")
        m_ge100 = _mk_market("f_ge_100", "Will BTC close at least $100,000 on Dec 31, 2026?", description=desc_close, end_date="2026-12-31T17:00:00Z")

        mkts_ok = normalize_universe_to_canonical_markets([m_rg, m_ge90, m_ge100])
        books_ok = build_instrument_order_books(
            mkts_ok,
            {
                "tok_f_rg_ok_0": _mk_book(0.22),    # YES([90k, 100k)) = 0.22
                "tok_f_rg_ok_1": _mk_book(0.78),
                "tok_f_ge_100_0": _mk_book(0.30),   # YES(>= 100k) = 0.30
                "tok_f_ge_100_1": _mk_book(0.70),
                "tok_f_ge_90_0": _mk_book(0.62),
                "tok_f_ge_90_1": _mk_book(0.39),    # NO(>= 90k) = 0.39 -> sum = 0.91 < 1.00!
            },
            default_fetch_ts=NOW_TS,
        )
        opps_ok, _ = detect_family_f_price_strike_ladders(mkts_ok, books_ok, verifier=_verifier(), now_ts=NOW_TS)
        long_cov = [o for o in opps_ok if o.sub_type == "INTERVAL_COVER_LONG"][0]
        self.assertEqual(long_cov.proof.opportunity_class, OpportunityClass.CLASS_B.value)
        # `D-007`: 3 sequential CLOB legs at `$48.70 < $500` NAV must carry quarantine flag!
        self.assertTrue(long_cov.proof.d007_sub500_multileg_quarantine)

        # Case B: Discrete gap `[$90,000, $99,000]` inclusive + `>= $100,000` leaves `$99,500` uncovered!
        desc_closed_gap = "Resolves Yes if Binance BTC/USDT close at 12:00 PM ET on Dec 31, 2026 is between $90,000 and $99,000 inclusive."
        m_rg_gap = _mk_market("f_rg_gap", "Will BTC close between $90,000 and $99,000 on Dec 31, 2026?", description=desc_closed_gap, end_date="2026-12-31T17:00:00Z")
        mkts_gap = normalize_universe_to_canonical_markets([m_rg_gap, m_ge90, m_ge100])
        books_gap = build_instrument_order_books(
            mkts_gap,
            {
                "tok_f_rg_gap_0": _mk_book(0.20),
                "tok_f_rg_gap_1": _mk_book(0.80),
                "tok_f_ge_100_0": _mk_book(0.30),
                "tok_f_ge_100_1": _mk_book(0.70),
                "tok_f_ge_90_0": _mk_book(0.62),
                "tok_f_ge_90_1": _mk_book(0.38),
            },
            default_fetch_ts=NOW_TS,
        )
        opps_gap, rej_gap = detect_family_f_price_strike_ladders(mkts_gap, books_gap, verifier=_verifier(), now_ts=NOW_TS)
        long_gap = [o for o in opps_gap if o.sub_type == "INTERVAL_COVER_LONG"][0]
        self.assertEqual(long_gap.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("INTERVAL_GAP_BETWEEN_RANGE_AND_TAIL", rej_gap)


class TestFamilyGSportsStructures(unittest.TestCase):
    def test_soccer_dc_valid_vs_reg_ot_mismatch_and_3no_void_trap(self) -> None:
        desc_90m = "Resolves based on 90 minutes plus stoppage time. Extra time and penalties do not count. If abandoned, resolves 50-50."
        m_ars = _mk_market("g_ars", "Will Arsenal win on 2026-11-20?", event_id="ev_soc", event_title="Arsenal vs. Chelsea", description=desc_90m, tags=("soccer", "epl"), end_date="2026-11-20T22:00:00Z")
        m_drw = _mk_market("g_drw", "Will Arsenal vs. Chelsea end in a draw?", event_id="ev_soc", event_title="Arsenal vs. Chelsea", description=desc_90m, tags=("soccer", "epl"), end_date="2026-11-20T22:00:00Z")
        m_che = _mk_market("g_che", "Will Chelsea win on 2026-11-20?", event_id="ev_soc", event_title="Arsenal vs. Chelsea", description=desc_90m, tags=("soccer", "epl"), end_date="2026-11-20T22:00:00Z")
        m_dc_1x = _mk_market("g_dc1x", "Arsenal or Draw?", event_id="ev_soc_dc", event_title="Arsenal vs. Chelsea Double Chance", group_item_title="Arsenal or Draw", description=desc_90m, tags=("soccer", "epl"), end_date="2026-11-20T22:00:00Z")
        m_adv = _mk_market("g_adv", "Will Arsenal advance to the Semifinals?", event_id="ev_soc_adv", event_title="Arsenal vs. Chelsea Cup Tie", description="Includes extra time and penalties.", tags=("soccer",), end_date="2026-11-20T22:00:00Z")

        mkts = normalize_universe_to_canonical_markets([m_ars, m_drw, m_che, m_dc_1x, m_adv])
        books = build_instrument_order_books(
            mkts,
            {
                # `1X (0.58) + Chelsea 90m (0.35) = 0.93 < 1.00` (and on 50-50 void: `0.50 + 0.50 = 1.00 > 0.93`!)
                "tok_g_dc1x_0": _mk_book(0.58),
                "tok_g_dc1x_1": _mk_book(0.42),
                "tok_g_che_0": _mk_book(0.35),
                "tok_g_che_1": _mk_book(0.58),  # Notice 3x NO = 0.58 + 0.58 + 0.58 = 1.74 (< 2.00, EXCEPT void pays 1.50!)
                "tok_g_ars_0": _mk_book(0.42),
                "tok_g_ars_1": _mk_book(0.58),
                "tok_g_drw_0": _mk_book(0.28),
                "tok_g_drw_1": _mk_book(0.58),
                "tok_g_adv_0": _mk_book(0.50),
                "tok_g_adv_1": _mk_book(0.50),
            },
            default_fetch_ts=NOW_TS,
        )
        opps, rej = detect_family_g_sports_structures(mkts, books, verifier=_verifier())

        dc_op = [o for o in opps if o.sub_type == "SOCCER_DOUBLE_CHANCE_COVER"][0]
        self.assertEqual(dc_op.proof.opportunity_class, OpportunityClass.CLASS_B.value)

        # `3 NO` at `3 * 0.58 = $1.74` looks like `+$0.26` arb vs `$2.00`, EXCEPT `50-50` abandonment pays `$1.50` -> `-$0.24` loss -> CLASS_D!
        no3_op = [o for o in opps if o.sub_type == "SOCCER_3WAY_NO_BUNDLE"][0]
        self.assertEqual(no3_op.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertLess(no3_op.proof.min_state_net_payoff_usd, 0.0)
        self.assertIn("STANDALONE_50_50_VOID_CAPS_3NO_PAYOUT_AT_1_50", rej)

        # `Arsenal Advance (incl. OT)` + `Chelsea 90m` -> CLASS_D (`Draw in 90m -> Chelsea wins PKs` pays $0.00!)
        reg_ot_trap = [o for o in opps if o.sub_type == "REGULATION_VS_ADVANCE_MISMATCH"][0]
        self.assertEqual(reg_ot_trap.proof.opportunity_class, OpportunityClass.CLASS_D.value)

    def test_nba_moneyline_spread_totals_corridor_and_tournament_advancement(self) -> None:
        desc_nba = "Includes overtime. Official NBA boxscore. If postponed beyond 48h, resolves 50-50."
        m_ml = _mk_market(
            "g_nba_ml", "Celtics vs. Lakers", event_id="ev_nba", event_title="Celtics vs. Lakers",
            outcomes=("Celtics", "Lakers"), sports_market_type="moneyline", description=desc_nba, tags=("nba",), end_date="2026-11-22T03:00:00Z",
        )
        m_sp = _mk_market(
            "g_nba_sp", "Spread: Celtics (-4.5)", event_id="ev_nba", event_title="Celtics vs. Lakers",
            outcomes=("Celtics", "Lakers"), sports_market_type="spreads", line=-4.5, description=desc_nba, tags=("nba",), end_date="2026-11-22T03:00:00Z",
        )
        m_ou_lo = _mk_market(
            "g_ou_218", "Celtics vs. Lakers: O/U 218.5", event_id="ev_nba", event_title="Celtics vs. Lakers",
            outcomes=("Over", "Under"), sports_market_type="totals", line=218.5, description=desc_nba, tags=("nba",), end_date="2026-11-22T03:00:00Z",
        )
        m_ou_hi = _mk_market(
            "g_ou_223", "Celtics vs. Lakers: O/U 223.5", event_id="ev_nba", event_title="Celtics vs. Lakers",
            outcomes=("Over", "Under"), sports_market_type="totals", line=223.5, description=desc_nba, tags=("nba",), end_date="2026-11-22T03:00:00Z",
        )
        m_champ = _mk_market(
            "g_bos_champ", "Will the Boston Celtics win the 2027 NBA Finals?", event_id="ev_nba_ch",
            description="Official NBA rules.", tags=("nba",), end_date="2027-06-25T04:00:00Z",
        )
        m_east = _mk_market(
            "g_bos_east", "Will the Boston Celtics win the 2027 Eastern Conference?", event_id="ev_nba_ec",
            description="Official NBA rules.", tags=("nba",), end_date="2027-06-05T04:00:00Z",
        )

        mkts = normalize_universe_to_canonical_markets([m_ml, m_sp, m_ou_lo, m_ou_hi, m_champ, m_east])
        books = build_instrument_order_books(
            mkts,
            {
                "tok_g_nba_ml_0": _mk_book(0.46),   # Celtics ML = 0.46
                "tok_g_nba_ml_1": _mk_book(0.56),
                "tok_g_nba_sp_0": _mk_book(0.55),
                "tok_g_nba_sp_1": _mk_book(0.47),   # Lakers +4.5 = 0.47 -> 0.46 + 0.47 = 0.93 < 1.00!
                "tok_g_ou_218_0": _mk_book(0.45),   # Over 218.5 = 0.45
                "tok_g_ou_218_1": _mk_book(0.55),
                "tok_g_ou_223_0": _mk_book(0.55),
                "tok_g_ou_223_1": _mk_book(0.47),   # Under 223.5 = 0.47 -> 0.45 + 0.47 = 0.92 < 1.00!
                "tok_g_bos_champ_0": _mk_book(0.25),
                "tok_g_bos_champ_1": _mk_book(0.60),  # NO Champ = 0.60
                "tok_g_bos_east_0": _mk_book(0.34),   # YES East = 0.34 -> 0.94 < 1.00!
                "tok_g_bos_east_1": _mk_book(0.66),
            },
            default_fetch_ts=NOW_TS,
        )
        opps, _ = detect_family_g_sports_structures(mkts, books, verifier=_verifier())
        class_b_subs = {o.sub_type for o in opps if o.proof.opportunity_class == OpportunityClass.CLASS_B.value}
        self.assertIn("MONEYLINE_VS_SPREAD_POLISH_MIDDLE", class_b_subs)
        self.assertIn("TOTALS_OVER_UNDER_CORRIDOR", class_b_subs)
        self.assertIn("TOURNAMENT_CHAMPION_IMPLIES_CONF_FINAL", class_b_subs)


class TestFamilyHWeatherAndD001D006(unittest.TestCase):
    def test_d001_kmia_quarantine_station_mismatch_contractual_box_and_d006_metar(self) -> None:
        # 1. `D-001` Disputed `KMIA` market IDs `6707503` and `6707502` MUST be completely quarantined!
        m_kmia_1 = _mk_market(
            "6707503",
            "Will the highest temperature in Miami be 82°F or higher on November 7, 2026?",
            description="Wunderground KMIA station.",
            resolution_source="https://www.wunderground.com/history/daily/us/fl/miami/KMIA",
            uma_status="disputed",
        )
        m_kmia_2 = _mk_market(
            "6707502",
            "Will the highest temperature in Miami be between 80°F and 81°F on November 7, 2026?",
            description="Wunderground KMIA station.",
            resolution_source="https://www.wunderground.com/history/daily/us/fl/miami/KMIA",
            uma_status="disputed",
        )

        # 2. Contractual `Daily High >= 70°F + Daily Low <= 72°F` on exact same station `KLGA` -> `CLASS_B`!
        desc_klga = "Resolves per Weather Underground daily summary for LaGuardia Airport (KLGA) in whole degrees."
        m_klga_hi = _mk_market(
            "h_klga_hi70",
            "Will the highest temperature in NYC be 70°F or higher on November 15, 2026?",
            description=desc_klga,
            resolution_source="https://www.wunderground.com/history/daily/us/ny/new-york-city/KLGA",
            end_date="2026-11-16T04:59:59Z",
        )
        m_klga_lo = _mk_market(
            "h_klga_lo72",
            "Will the lowest temperature in NYC be 72°F or lower on November 15, 2026?",
            description=desc_klga,
            resolution_source="https://www.wunderground.com/history/daily/us/ny/new-york-city/KLGA",
            end_date="2026-11-16T04:59:59Z",
        )
        # 3. Cross-station trap: `KJFK` vs `KLGA` on same NYC date -> `CLASS_D`!
        m_kjfk_hi = _mk_market(
            "h_kjfk_hi72",
            "Will the highest temperature in NYC be 72°F or higher on November 15, 2026?",
            description="Resolves per Weather Underground daily summary for JFK Airport (KJFK).",
            resolution_source="https://www.wunderground.com/history/daily/us/ny/new-york-city/KJFK",
            end_date="2026-11-16T04:59:59Z",
        )
        # 4. Celsius market on `EGLC` for `D-006` METAR tests (`<= 14°C`)
        m_eglc_14 = _mk_market(
            "h_eglc_14c",
            "Will the highest temperature in London be 14°C or lower on November 15, 2026?",
            description="Resolves per Weather Underground London City Airport (EGLC) in whole degrees.",
            resolution_source="https://www.wunderground.com/history/daily/gb/london/EGLC",
            end_date="2026-11-15T23:59:59Z",
        )
        m_kord_60 = _mk_market(
            "h_kord_60f",
            "Will the highest temperature in Chicago be 60°F or lower on November 15, 2026?",
            description="Resolves per Weather Underground Chicago O'Hare (KORD) in whole degrees.",
            resolution_source="https://www.wunderground.com/history/daily/us/il/chicago/KORD",
            end_date="2026-11-16T05:59:59Z",
        )
        m_ksea_50 = _mk_market(
            "h_ksea_50f",
            "Will the highest temperature in Seattle be 50°F or lower on November 15, 2026?",
            description="Resolves per Weather Underground Seattle (KSEA) in whole degrees.",
            resolution_source="https://www.wunderground.com/history/daily/us/wa/seattle/KSEA",
            end_date="2026-11-16T07:59:59Z",
        )

        mkts = normalize_universe_to_canonical_markets(
            [m_kmia_1, m_kmia_2, m_klga_hi, m_klga_lo, m_kjfk_hi, m_eglc_14, m_kord_60, m_ksea_50]
        )
        books = build_instrument_order_books(
            mkts,
            {
                "tok_6707503_0": _mk_book(0.01),
                "tok_6707503_1": _mk_book(0.01),
                "tok_6707502_0": _mk_book(0.01),
                "tok_6707502_1": _mk_book(0.01),
                "tok_h_klga_hi70_0": _mk_book(0.45),
                "tok_h_klga_hi70_1": _mk_book(0.55),
                "tok_h_klga_lo72_0": _mk_book(0.48),  # 0.45 + 0.48 = 0.93 < 1.00!
                "tok_h_klga_lo72_1": _mk_book(0.52),
                "tok_h_kjfk_hi72_0": _mk_book(0.50),
                "tok_h_kjfk_hi72_1": _mk_book(0.40),
                "tok_h_eglc_14c_0": _mk_book(0.20),
                "tok_h_eglc_14c_1": _mk_book(0.75),
                "tok_h_kord_60f_0": _mk_book(0.20),
                "tok_h_kord_60f_1": _mk_book(0.75),
                "tok_h_ksea_50f_0": _mk_book(0.10),
                "tok_h_ksea_50f_1": _mk_book(0.85),
            },
            default_fetch_ts=NOW_TS,
        )

        observations = [
            # EGLC: unverified METAR (no T-group) observed `14.8°C` -> `14.8 - 0.55 = 14.25 <= 14.499` -> MUST BLOCK via `D-006` cushion!
            MetarObservationSnapshot(
                station_icao="EGLC",
                local_date_iso="2026-11-15",
                observed_high=14.8,
                unit="C",
                has_exact_tenths_t_group=False,
                has_dollar_maintenance_flag=False,
            ),
            # KORD: raw METAR ends with `$` ASOS maintenance indicator -> MUST HARD-BLOCK (`CLASS_D`)!
            MetarObservationSnapshot(
                station_icao="KORD",
                local_date_iso="2026-11-15",
                observed_high=68.0,
                unit="F",
                raw_metar="METAR KORD 151951Z 24012KT 10SM CLR 20/05 A2992 RMK AO2 T02000050 $",
                has_exact_tenths_t_group=True,
            ),
            # KSEA: clean verified `T`-group exceedance (`58.0°F > 50°F`) -> MUST cap at `CLASS_C` (NEVER `CLASS_A/B`!)
            MetarObservationSnapshot(
                station_icao="KSEA",
                local_date_iso="2026-11-15",
                observed_high=58.0,
                unit="F",
                raw_metar="METAR KSEA 152053Z 18008KT 10SM FEW045 14/07 A3004 RMK AO2 T01440072",
                has_exact_tenths_t_group=True,
                has_dollar_maintenance_flag=False,
            ),
        ]

        opps, rej = detect_family_h_weather_measurable(
            mkts, books, verifier=_verifier(), observations=observations
        )

        # Verify `D-001`: ZERO candidates touch `6707503` or `6707502`!
        all_touched_mids = {mid for o in opps for mid in o.market_ids}
        self.assertNotIn("6707503", all_touched_mids)
        self.assertNotIn("6707502", all_touched_mids)
        self.assertEqual(rej.get("D001_DISPUTED_KMIA_QUARANTINED"), 2)
        self.assertAlmostEqual(D006_UNVERIFIED_SENSOR_CUSHION_C, 0.55)

        # Verify contractual `KLGA` High/Low box -> `CLASS_B`
        hl_op = [o for o in opps if o.sub_type == "DAILY_HIGH_GTE_DAILY_LOW_PHYSICAL_COVER"][0]
        self.assertEqual(hl_op.proof.opportunity_class, OpportunityClass.CLASS_B.value)

        # Verify `KLGA` vs `KJFK` station mismatch -> `CLASS_D`
        st_mis = [o for o in opps if "h_kjfk_hi72" in o.market_ids][0]
        self.assertEqual(st_mis.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("WEATHER_STATION_ICAO_MISMATCH", rej)

        # Verify `D-006` cushion block on `EGLC` -> `CLASS_D`
        eglc_op = [o for o in opps if "h_eglc_14c" in o.market_ids][0]
        self.assertEqual(eglc_op.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("D006_ROUNDING_CUSHION_BLOCK", rej)

        # Verify `D-006` `$` maintenance block on `KORD` -> `CLASS_D`
        kord_op = [o for o in opps if "h_kord_60f" in o.market_ids][0]
        self.assertEqual(kord_op.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("D006_ASOS_DOLLAR_MAINTENANCE_BLOCK", rej)

        # Verify clean `KSEA` METAR prune is strictly `CLASS_C` (never `CLASS_A/B`)!
        ksea_op = [o for o in opps if "h_ksea_50f" in o.market_ids][0]
        self.assertEqual(ksea_op.proof.opportunity_class, OpportunityClass.CLASS_C.value)


class TestFamilyIDuplicateMarketsAndUnifiedScanner(unittest.TestCase):
    def test_exact_duplicate_class_b_vs_near_duplicate_class_c_and_d(self) -> None:
        desc_exact = (
            "This market resolves to Yes according to official Federal Reserve statement "
            "at federalreserve.gov by December 31, 2026, 11:59 PM ET."
        )
        # Pair 1: Provably state-identical duplicate across two events -> `CLASS_B`
        m_dup1 = _mk_market(
            "i_dup_1",
            "Will the Federal Reserve pause interest rates at the December 2026 meeting?",
            event_id="ev_fed_a",
            description=desc_exact,
            resolution_source="https://www.federalreserve.gov",
            end_date="2026-12-31T23:59:59Z",
        )
        m_dup2 = _mk_market(
            "i_dup_2",
            "Will the Federal Reserve pause interest rates at the December 2026 meeting?",
            event_id="ev_fed_b",
            description=desc_exact,
            resolution_source="https://www.federalreserve.gov",
            end_date="2026-12-31T23:59:59Z",
        )

        # Pair 2: Soft near-duplicate (same timestamp & TZ, different news authority `Reuters` vs `AP`, L1 sum < 1.00) -> `CLASS_C`
        m_nd1 = _mk_market(
            "i_nd_1",
            "Will Acme Corp complete acquisition of Beta Labs in 2027?",
            event_id="ev_ma_1",
            description="Resolves Yes per official Reuters report by December 31, 2027, 11:59 PM ET.",
            resolution_source="https://reuters.com",
            end_date="2027-12-31T23:59:59Z",
        )
        m_nd2 = _mk_market(
            "i_nd_2",
            "Will Acme Corp complete the acquisition of Beta Labs in 2027?",
            event_id="ev_ma_2",
            description="Resolves Yes per official Bloomberg report by December 31, 2027, 11:59 PM ET.",
            resolution_source="https://bloomberg.com",
            end_date="2027-12-31T23:59:59Z",
        )

        # Pair 3: Structural near-duplicate break (`ET` vs `UTC` + `48h` cutoff gap) -> `CLASS_D`
        m_bad1 = _mk_market(
            "i_bad_1",
            "Will SpaceX launch Starship Flight 15 in 2027?",
            event_id="ev_spx_1",
            description="Resolves Yes per Associated Press by December 29, 2027, 11:59 PM ET.",
            end_date="2027-12-30T04:59:59Z",
        )
        m_bad2 = _mk_market(
            "i_bad_2",
            "Will SpaceX launch Starship Flight 15 in 2027?",
            event_id="ev_spx_2",
            description="Resolves Yes per Associated Press by December 31, 2027, 23:59 UTC.",
            end_date="2027-12-31T23:59:59Z",
        )

        # Non-duplicate distinct numbers (`Flight 15` vs `Flight 16`) must NOT pair!
        m_other_num = _mk_market(
            "i_flight_16",
            "Will SpaceX launch Starship Flight 16 in 2027?",
            event_id="ev_spx_3",
            description="Resolves Yes per Associated Press by December 31, 2027, 23:59 UTC.",
            end_date="2027-12-31T23:59:59Z",
        )

        # Dormant near-miss exact duplicate (`YES_1 + NO_2 = 0.51 + 0.51 = 1.02` -> 200 bps deficit <= 350 bps)
        m_dorm1 = _mk_market(
            "i_dorm_1",
            "Will Rivian deliver 100,000 vehicles in 2027?",
            event_id="ev_riv_1",
            description=desc_exact,
            resolution_source="https://www.federalreserve.gov",
            end_date="2027-12-31T23:59:59Z",
        )
        m_dorm2 = _mk_market(
            "i_dorm_2",
            "Will Rivian deliver 100,000 vehicles in 2027?",
            event_id="ev_riv_2",
            description=desc_exact,
            resolution_source="https://www.federalreserve.gov",
            end_date="2027-12-31T23:59:59Z",
        )

        raw_list = [m_dup1, m_dup2, m_nd1, m_nd2, m_bad1, m_bad2, m_other_num, m_dorm1, m_dorm2]
        mkts = normalize_universe_to_canonical_markets(raw_list)
        raw_books = {
            "tok_i_dup_1_0": _mk_book(0.44),
            "tok_i_dup_1_1": _mk_book(0.56),
            "tok_i_dup_2_0": _mk_book(0.57),
            "tok_i_dup_2_1": _mk_book(0.48),  # YES_1 (0.44) + NO_2 (0.48) = 0.92 < 1.00!
            "tok_i_nd_1_0": _mk_book(0.42),
            "tok_i_nd_1_1": _mk_book(0.58),
            "tok_i_nd_2_0": _mk_book(0.60),
            "tok_i_nd_2_1": _mk_book(0.45),   # YES_1 (0.42) + NO_2 (0.45) = 0.87 < 1.00 with cross-oracle divergence -> CLASS_C!
            "tok_i_bad_1_0": _mk_book(0.40),
            "tok_i_bad_1_1": _mk_book(0.60),
            "tok_i_bad_2_0": _mk_book(0.60),
            "tok_i_bad_2_1": _mk_book(0.45),
            "tok_i_flight_16_0": _mk_book(0.20),
            "tok_i_flight_16_1": _mk_book(0.20),
            "tok_i_dorm_1_0": _mk_book(0.51),
            "tok_i_dorm_1_1": _mk_book(0.51),
            "tok_i_dorm_2_0": _mk_book(0.51),
            "tok_i_dorm_2_1": _mk_book(0.51),
        }
        books = build_instrument_order_books(mkts, raw_books, default_fetch_ts=NOW_TS)
        opps, _ = detect_family_i_duplicate_markets(mkts, books, verifier=_verifier())

        exact_op = [o for o in opps if set(o.market_ids) == {"i_dup_1", "i_dup_2"}][0]
        self.assertEqual(exact_op.proof.opportunity_class, OpportunityClass.CLASS_B.value)

        nd_c = [o for o in opps if set(o.market_ids) == {"i_nd_1", "i_nd_2"}][0]
        self.assertEqual(nd_c.proof.opportunity_class, OpportunityClass.CLASS_C.value)
        self.assertTrue(any("AUTHORITY_DIVERGENCE" in n for n in nd_c.divergence_or_rejection_reasons))

        bad_d = [o for o in opps if set(o.market_ids) == {"i_bad_1", "i_bad_2"}][0]
        self.assertEqual(bad_d.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertTrue(any("CUTOFF_TIMESTAMP_DIVERGENCE" in n for n in bad_d.divergence_or_rejection_reasons))
        self.assertTrue(any("TIMEZONE_DIVERGENCE" in n for n in bad_d.divergence_or_rejection_reasons))

        # Verify `Flight 16` was never paired with `Flight 15`
        self.assertFalse(any("i_flight_16" in o.market_ids for o in opps))

        # Verify dormant near-miss (`1.02` L1 sum -> `gap_to_breakeven_bps == 200.0`)
        dorm_op = [o for o in opps if set(o.market_ids) == {"i_dorm_1", "i_dorm_2"}][0]
        self.assertEqual(dorm_op.proof.opportunity_class, OpportunityClass.CLASS_E.value)
        self.assertTrue(dorm_op.is_dormant_near_miss)
        self.assertAlmostEqual(dorm_op.gap_to_breakeven_bps, 200.0, places=1)

        # Verify unified `LogicalSpecializedScanner` + `collect_candidate_token_ids_d_to_i`
        tok_map = collect_candidate_token_ids_d_to_i(mkts, now_ts=NOW_TS)
        self.assertIn("tok_i_dup_1_0", tok_map["I"])
        scanner = LogicalSpecializedScanner(reconciled_nav_usd=48.70, now_ts=NOW_TS)
        rep = scanner.scan_all_families(raw_list, raw_books, default_book_fetch_ts=NOW_TS)
        summary = rep.to_summary_dict()
        self.assertGreaterEqual(summary["executable_class_a_b_count"], 1)
        self.assertGreaterEqual(summary["dormant_near_miss_count"], 1)


class TestRedTeamAdversarialVectors(unittest.TestCase):
    def test_spot_vs_futures_oracle_mismatch_double_touch_and_endpoint_overlap_traps(self) -> None:
        # 1. Spot Gold (`XAU/USD`) vs CME GC Futures -> `SPOT_VS_FUTURES_BASIS_MISMATCH` (`CLASS_D`)
        m_gold_spot = _mk_market(
            "adv_xau_spot",
            "Will Gold price be at least $3,000 on December 31, 2026?",
            description="Resolves Yes per LBMA / XAU/USD spot gold closing price at 12:00 PM ET on December 31, 2026.",
            resolution_source="https://www.tradingview.com/symbols/XAUUSD",
            end_date="2026-12-31T17:00:00Z",
        )
        m_gold_fut = _mk_market(
            "adv_gc_fut",
            "Will Gold price be at least $3,050 on December 31, 2026?",
            description="Resolves Yes per CME Group COMEX front-month futures contract settlement price at 12:00 PM ET on December 31, 2026.",
            resolution_source="https://www.cmegroup.com",
            end_date="2026-12-31T17:00:00Z",
        )

        # 2. Touch-anytime `>= $110k` + Touch-down `<= $80k` -> BOTH can hit in same window -> `CLASS_D`!
        m_touch_up = _mk_market(
            "adv_eth_up",
            "Will Ethereum reach $5,000 by December 31, 2026?",
            description="Resolves Yes if Binance ETH/USDT 1m candle high hits $5,000 by 11:59 PM ET.",
            resolution_source="https://binance.com",
            end_date="2027-01-01T04:59:59Z",
        )
        m_touch_dn = _mk_market(
            "adv_eth_dn",
            "Will Ethereum dip to $2,500 by December 31, 2026?",
            description="Resolves Yes if Binance ETH/USDT 1m candle low drops to $2,500 by 11:59 PM ET.",
            resolution_source="https://binance.com",
            end_date="2027-01-01T04:59:59Z",
        )

        # 3. Closed-endpoint overlap `[90000, 100000]` inclusive + `>= 100000` breaks short cover at `S = $100,000`!
        desc_closed = "Resolves Yes if Coinbase BTC/USD official close at 12:00 PM ET on Dec 31, 2026 is inclusive."
        m_rg_cl = _mk_market("adv_rg_cl", "Will BTC close between $90,000 and $100,000 on Dec 31, 2026?", description=desc_closed, resolution_source="https://coinbase.com", end_date="2026-12-31T17:00:00Z")
        m_ge90_cb = _mk_market("adv_ge90_cb", "Will BTC close at least $90,000 on Dec 31, 2026?", description=desc_closed, resolution_source="https://coinbase.com", end_date="2026-12-31T17:00:00Z")
        m_ge100_cb = _mk_market("adv_ge100_cb", "Will BTC close at least $100,000 on Dec 31, 2026?", description=desc_closed, resolution_source="https://coinbase.com", end_date="2026-12-31T17:00:00Z")

        mkts = normalize_universe_to_canonical_markets([m_gold_spot, m_gold_fut, m_touch_up, m_touch_dn, m_rg_cl, m_ge90_cb, m_ge100_cb])
        books = build_instrument_order_books(
            mkts,
            {
                "tok_adv_xau_spot_0": _mk_book(0.45),
                "tok_adv_xau_spot_1": _mk_book(0.55),
                "tok_adv_gc_fut_0": _mk_book(0.55),
                "tok_adv_gc_fut_1": _mk_book(0.44),
                "tok_adv_eth_up_0": _mk_book(0.60),
                "tok_adv_eth_up_1": _mk_book(0.40),
                "tok_adv_eth_dn_0": _mk_book(0.60),
                "tok_adv_eth_dn_1": _mk_book(0.40),
                # Short cover cost `0.60 + 0.60 + 0.60 = $1.80 < $2.00`, EXCEPT at `S_T = $100,000` payout = `0 + 0 + 1 = $1.00`!
                "tok_adv_rg_cl_0": _mk_book(0.40),
                "tok_adv_rg_cl_1": _mk_book(0.60),
                "tok_adv_ge100_cb_0": _mk_book(0.40),
                "tok_adv_ge100_cb_1": _mk_book(0.60),
                "tok_adv_ge90_cb_0": _mk_book(0.60),
                "tok_adv_ge90_cb_1": _mk_book(0.40),
            },
            default_fetch_ts=NOW_TS,
        )
        opps, rej = detect_family_f_price_strike_ladders(mkts, books, verifier=_verifier(), now_ts=NOW_TS)

        gold_op = [o for o in opps if set(o.market_ids) == {"adv_xau_spot", "adv_gc_fut"}][0]
        self.assertEqual(gold_op.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("SPOT_VS_FUTURES_BASIS_MISMATCH", rej)

        eth_tails = [o for o in opps if set(o.market_ids) == {"adv_eth_up", "adv_eth_dn"}][0]
        self.assertEqual(eth_tails.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("TOUCH_ANYTIME_BOTH_TAILS_POSSIBLE", rej)

        short_ov = [o for o in opps if o.sub_type == "INTERVAL_COVER_SHORT" and "adv_rg_cl" in o.market_ids][0]
        self.assertEqual(short_ov.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertLess(short_ov.proof.min_state_net_payoff_usd, 0.0)
        self.assertIn("ENDPOINT_OVERLAP_DOUBLE_YES_AT_K2", rej)

    def test_tennis_retirement_dnb_and_two_legged_aggregate_sports_traps(self) -> None:
        # 1. Tennis retirement rule mismatch (`50-50 void` vs `player who advances resolves to Yes`)
        m_ten_ml = _mk_market(
            "adv_ten_ml", "Alcaraz vs. Sinner", event_id="ev_ten_1", event_title="Alcaraz vs. Sinner",
            outcomes=("Alcaraz", "Sinner"), sports_market_type="moneyline",
            description="ATP Wimbledon. Player who advances to the next round resolves to Yes.",
            tags=("tennis", "atp"), end_date="2026-11-20T18:00:00Z",
        )
        m_ten_sp = _mk_market(
            "adv_ten_sp", "Spread: Alcaraz (-1.5)", event_id="ev_ten_2", event_title="Alcaraz vs. Sinner",
            outcomes=("Alcaraz", "Sinner"), sports_market_type="spreads", line=-1.5,
            description="ATP Wimbledon. Must complete all sets; if a player retires, market resolves 50-50.",
            tags=("tennis", "atp"), end_date="2026-11-20T18:00:00Z",
        )
        # 2. Two-legged Champions League aggregate tie (`Win 90m` does NOT imply `Advance` on aggregate!)
        m_ucl_90 = _mk_market(
            "adv_ucl_90", "Will Real Madrid win on 2026-11-25?", event_id="ev_ucl", event_title="Real Madrid vs. Bayern Munich",
            description="90 minutes regulation time only, 2nd leg of two-legged tie.", tags=("soccer", "ucl"), end_date="2026-11-25T22:00:00Z",
        )
        m_ucl_adv = _mk_market(
            "adv_ucl_adv", "Will Real Madrid advance to the Finals?", event_id="ev_ucl_a", event_title="Real Madrid vs. Bayern Munich",
            description="Based on two-legged aggregate score including extra time and penalties.", tags=("soccer", "ucl"), end_date="2026-11-25T22:00:00Z",
        )

        mkts = normalize_universe_to_canonical_markets([m_ten_ml, m_ten_sp, m_ucl_90, m_ucl_adv])
        books = build_instrument_order_books(
            mkts,
            {
                "tok_adv_ten_ml_0": _mk_book(0.45),
                "tok_adv_ten_ml_1": _mk_book(0.55),
                "tok_adv_ten_sp_0": _mk_book(0.55),
                "tok_adv_ten_sp_1": _mk_book(0.45),
                "tok_adv_ucl_90_0": _mk_book(0.55),
                "tok_adv_ucl_90_1": _mk_book(0.44),
                "tok_adv_ucl_adv_0": _mk_book(0.45),
                "tok_adv_ucl_adv_1": _mk_book(0.55),
            },
            default_fetch_ts=NOW_TS,
        )
        opps, rej = detect_family_g_sports_structures(mkts, books, verifier=_verifier())
        for o in opps:
            self.assertNotIn(o.proof.opportunity_class, {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value})
        self.assertIn("TENNIS_RETIREMENT_RULE_MISMATCH", rej)
        self.assertIn("TWO_LEGGED_AGGREGATE_WIN_90M_DOES_NOT_IMPLY_ADVANCE", rej)

    def test_stale_book_blocks_promotion_to_class_a_or_b(self) -> None:
        m_a = _mk_market("st_a", "Will Jane Doe win both the popular vote and the presidential election in 2028?", event_id="ev_1")
        m_b = _mk_market("st_b", "Will Jane Doe win the 2028 US presidential election?", event_id="ev_2")
        mkts = normalize_universe_to_canonical_markets([m_a, m_b])
        stale_ts = NOW_TS - 900.0  # 15 minutes old (> 120s freshness threshold)
        raw_books = {
            "tok_st_a_0": {"asks": [{"price": "0.50", "size": "100"}], "bids": [{"price": "0.48", "size": "100"}], "book_timestamp_sec": stale_ts},
            "tok_st_a_1": {"asks": [{"price": "0.40", "size": "100"}], "bids": [{"price": "0.38", "size": "100"}], "book_timestamp_sec": stale_ts},
            "tok_st_b_0": {"asks": [{"price": "0.45", "size": "100"}], "bids": [{"price": "0.43", "size": "100"}], "book_timestamp_sec": stale_ts},
            "tok_st_b_1": {"asks": [{"price": "0.55", "size": "100"}], "bids": [{"price": "0.53", "size": "100"}], "book_timestamp_sec": stale_ts},
        }
        books = build_instrument_order_books(mkts, raw_books)
        opps, _ = detect_family_d_logical_arbitrage(mkts, books, verifier=_verifier())
        self.assertEqual(opps[0].proof.opportunity_class, OpportunityClass.CLASS_D.value)

    def test_negated_deadlines_negated_strikes_signed_duplicates_and_before_date_tz(self) -> None:
        # 1. Negated deadline: `"Will the Fed NOT cut rates by December 31, 2027?"` => `"Will the Fed NOT cut rates by June 30, 2027?"`
        #    Must route to `SURVIVAL` (`B_IMPLIES_A`, buying `NO_dec + YES_jun`), NEVER `A_IMPLIES_B` (`NO_jun + YES_dec`)!
        m_not_jun = _mk_market(
            "neg_fed_jun", "Will the Fed not cut interest rates by June 30, 2027?", event_id="ev_nf1",
            description="Official Federal Reserve FOMC statement by June 30, 2027 ET.",
            end_date="2027-06-30T23:59:59-04:00",
        )
        m_not_dec = _mk_market(
            "neg_fed_dec", "Will the Fed not cut interest rates by December 31, 2027?", event_id="ev_nf2",
            description="Official Federal Reserve FOMC statement by December 31, 2027 ET.",
            end_date="2027-12-31T23:59:59-05:00",
        )
        # 2. `"before April 2, 2027 ET?"` (TZ in question, no `11:59 PM` override) == `2027-04-01 23:59:59 ET`!
        m_bef_apr2 = _mk_market(
            "tz_bef_apr2", "Will SpaceX launch Starship to Mars before April 2, 2027 ET?", event_id="ev_sp1",
            description="Resolves via official SpaceX confirmation.",
            end_date="2027-04-02T03:59:59Z",
        )
        m_by_apr2 = _mk_market(
            "tz_by_apr2", "Will SpaceX launch Starship to Mars by April 2, 2027?", event_id="ev_sp2",
            description="Resolves via official SpaceX confirmation by 11:59 PM ET.",
            end_date="2027-04-03T03:59:59Z",
        )
        # 3. Negated close strike (`not close above $90,000` => `LTE $90,000`, NEVER `GT $90,000`) & Negated touch strike (`not hit $90,000` => rejected)
        m_btc_not_close = _mk_market(
            "neg_btc_close", "Will Bitcoin not close above $90,000 on November 30, 2026?", event_id="ev_nb1",
            description="Binance BTC/USDT 1m candle close at 11:59 PM ET.",
            end_date="2026-12-01T04:59:59Z",
        )
        m_btc_not_hit = _mk_market(
            "neg_btc_hit", "Will Bitcoin not hit $90,000 before December 2026?", event_id="ev_nb2",
            description="Binance BTC/USDT 1m candle high anytime before 11:59 PM ET.",
            end_date="2026-12-01T04:59:59Z",
        )
        # 4. Signed spread / temperature non-duplicates (`-3.5` vs `+3.5` must NEVER match as duplicates!)
        m_minus = _mk_market(
            "dup_minus", "Will the Lakers cover -3.5 on November 20, 2026?", event_id="ev_dm1",
            description="Official NBA box score ET.", end_date="2026-11-21T04:00:00Z",
        )
        m_plus = _mk_market(
            "dup_plus", "Will the Lakers cover +3.5 on November 20, 2026?", event_id="ev_dm2",
            description="Official NBA box score ET.", end_date="2026-11-21T04:00:00Z",
        )

        mkts = normalize_universe_to_canonical_markets(
            [m_not_jun, m_not_dec, m_bef_apr2, m_by_apr2, m_btc_not_close, m_btc_not_hit, m_minus, m_plus]
        )
        books = build_instrument_order_books(
            mkts,
            {
                "tok_neg_fed_jun_0": _mk_book(0.45),  # YES_jun = 0.45
                "tok_neg_fed_jun_1": _mk_book(0.40),
                "tok_neg_fed_dec_0": _mk_book(0.40),
                "tok_neg_fed_dec_1": _mk_book(0.45),  # NO_dec = 0.45 (`NO_dec + YES_jun = 0.90 < $1.00`!)
                "tok_tz_bef_apr2_0": _mk_book(0.55),
                "tok_tz_bef_apr2_1": _mk_book(0.44),
                "tok_tz_by_apr2_0": _mk_book(0.48),
                "tok_tz_by_apr2_1": _mk_book(0.52),
                "tok_dup_minus_0": _mk_book(0.40),
                "tok_dup_minus_1": _mk_book(0.40),
                "tok_dup_plus_0": _mk_book(0.40),
                "tok_dup_plus_1": _mk_book(0.40),
            },
            default_fetch_ts=NOW_TS,
        )

        opps_e, _ = detect_family_e_temporal_deadline_arbitrage(mkts, books, verifier=_verifier())
        fed_op = [o for o in opps_e if set(o.market_ids) == {"neg_fed_jun", "neg_fed_dec"}][0]
        self.assertEqual(fed_op.relationship_type, "B_IMPLIES_A")
        self.assertEqual(fed_op.proof.opportunity_class, OpportunityClass.CLASS_B.value)
        leg_ids = {lg.instrument_id for lg in fed_op.structure.legs}
        self.assertEqual(leg_ids, {"tok_neg_fed_dec_1", "tok_neg_fed_jun_0"})

        sp_ops = [o for o in opps_e if set(o.market_ids) == {"tz_bef_apr2", "tz_by_apr2"}]
        self.assertEqual(len(sp_ops), 1)
        self.assertEqual(sp_ops[0].proof.opportunity_class, OpportunityClass.CLASS_B.value)

        from src.polymarket_research.detectors_logical_and_specialized import parse_strike_contract
        by_id = {m.market_id: m for m in mkts}
        ps_close = parse_strike_contract(by_id["neg_btc_close"])
        self.assertIsNotNone(ps_close)
        self.assertEqual(ps_close.comparator, "LTE")
        self.assertIsNone(parse_strike_contract(by_id["neg_btc_hit"]))

        opps_i, _ = detect_family_i_duplicate_markets(mkts, books, verifier=_verifier())
        self.assertEqual([o for o in opps_i if set(o.market_ids) == {"dup_minus", "dup_plus"}], [])

    def test_live_polymarket_quirks_before_year_spx_low_player_props_and_ordinals(self) -> None:
        # 1. Live Gamma Quirk #1 (`692299` vs `6597785`): `"before 2027?"` whose rules state `"by Dec 31, 2026, 11:59 PM ET"`
        #    MUST parse to `2026-12-31 23:59:59 ET` (BEFORE `June 30, 2027`), NEVER `2027-12-31`!
        m_bef_2027 = _mk_market(
            "lv_bef_27", "Will J.D. Vance announce a presidential run before 2027?", event_id="ev_jd1",
            description="Resolves Yes per consensus of credible reporting by December 31, 2026, 11:59 PM ET.",
            end_date="2027-01-01T04:59:00Z",
        )
        m_by_jun27 = _mk_market(
            "lv_jun_27", "Will J.D. Vance announce a presidential run by June 30, 2027?", event_id="ev_jd2",
            description="Resolves Yes per consensus of credible reporting by June 30, 2027, 11:59 PM ET.",
            end_date="2027-07-01T03:59:00Z",
        )

        # 2. Live Gamma Quirk #2 (`6280832` vs `6280833`): `"Ukraine agrees not to join NATO by ..."`
        #    Embedded infinitive `"agrees not to join"` is a positive act of agreement (`FIRST_PASSAGE`: `A_IMPLIES_B`, NEVER `SURVIVAL` `B_IMPLIES_A`!)
        m_nato_jun = _mk_market(
            "lv_nato_jun", "Ukraine agrees not to join NATO by June 30, 2027?", event_id="ev_na1",
            description="Resolves Yes per official announcement by June 30, 2027, 11:59 PM ET.",
            end_date="2027-07-01T03:59:00Z",
        )
        m_nato_dec = _mk_market(
            "lv_nato_dec", "Ukraine agrees not to join NATO by December 31, 2027?", event_id="ev_na2",
            description="Resolves Yes per official announcement by December 31, 2027, 11:59 PM ET.",
            end_date="2028-01-01T04:59:00Z",
        )

        # 3. Live Gamma Quirk #3 (`3565797` vs `1125396`): `"Will S&P 500 (SPX) hit $7,200 (LOW) in December?"` (`↓ $7,200`)
        #    MUST parse as `TOUCH_DOWN_ANYTIME` + `LTE` (`<= 4500 => <= 7200`: `NO_4500 + YES_7200`), NEVER `GTE` (`NO_7200 + YES_4500`)!
        m_spx_low_7200 = _mk_market(
            "lv_spx_7200", "Will S&P 500 (SPX) hit $7,200 (LOW) in December?", group_item_title="↓ $7,200",
            event_id="ev_spx_l", description="Yahoo Finance SPX intraday low in December 2026 ET.", end_date="2026-12-31T21:00:00Z",
        )
        m_spx_low_4500 = _mk_market(
            "lv_spx_4500", "Will S&P 500 (SPX) hit $4,500 (LOW) in December?", group_item_title="↓ $4,500",
            event_id="ev_spx_l", description="Yahoo Finance SPX intraday low in December 2026 ET.", end_date="2026-12-31T21:00:00Z",
        )

        # 4. Live Gamma Quirk #4 (`6958415` vs `6967152`): Player prop `Jayson Tatum: Points O/U 39.5` vs `1Q O/U 44.5` (`q1_totals`)
        m_tatum_pts = _mk_market(
            "lv_tatum", "Jayson Tatum: Points O/U 39.5", group_item_title="Jayson Tatum: Points O/U 39.5",
            event_id="ev_cel", event_title="Celtics vs. Raptors", outcomes=("Over", "Under"),
            sports_market_type="points", line=39.5, tags=("nba",), end_date="2026-11-12T00:00:00Z",
        )
        m_cel_1q = _mk_market(
            "lv_cel_1q", "Celtics vs. Raptors: 1Q O/U 44.5", group_item_title="1Q O/U 44.5",
            event_id="ev_cel", event_title="Celtics vs. Raptors", outcomes=("Over", "Under"),
            sports_market_type="q1_totals", line=44.5, tags=("nba",), end_date="2026-11-12T00:00:00Z",
        )
        m_cel_full = _mk_market(
            "lv_cel_full", "Celtics vs. Raptors: O/U 224.5", group_item_title="O/U 224.5",
            event_id="ev_cel", event_title="Celtics vs. Raptors", outcomes=("Over", "Under"),
            sports_market_type="totals", line=224.5, tags=("nba",), end_date="2026-11-12T00:00:00Z",
        )

        # 5. Live Gamma Quirk #5 (`5621936` vs `5622453` & `5685419` vs `5686242`):
        #    `most votes` vs `second-most votes` and `Best Actress` vs `Best Supporting Actress` MUST NEVER be `CLASS_B` duplicates!
        m_lepen_1 = _mk_market(
            "lv_lp_1", "Will Marine Le Pen win the most votes in the first round of the 2027 French presidential election?",
            event_id="ev_fr1", description="Consensus of credible reporting ET.", end_date="2027-04-30T23:59:00Z",
        )
        m_lepen_2 = _mk_market(
            "lv_lp_2", "Will Marine Le Pen win the second-most votes in the first round of the 2027 French presidential election?",
            event_id="ev_fr2", description="Consensus of credible reporting ET.", end_date="2027-04-30T23:59:00Z",
        )

        # 6. Live Gamma Quirk #6 (`5401115` vs `4640849`):
        #    `"Perim Island no longer under Houthi control by November 30?"` vs `"...by December 31?"`
        #    Reversible status (`"no longer under control"`) without `"at any point"` can revert between Nov 30 and Dec 31 -> `CLASS_D`!
        m_perim_nov = _mk_market(
            "lv_perim_nov", "Perim Island no longer under Houthi control by November 30?",
            event_id="ev_perim", description="Yes if Perim Island is no longer under Houthi control by the specified date, 11:59 PM ET. Consensus of credible reporting.",
            end_date="2026-11-30T23:59:00Z",
        )
        m_perim_dec = _mk_market(
            "lv_perim_dec", "Perim Island no longer under Houthi control by December 31?",
            event_id="ev_perim", description="Yes if Perim Island is no longer under Houthi control by the specified date, 11:59 PM ET. Consensus of credible reporting.",
            end_date="2026-12-31T23:59:00Z",
        )

        mkts = normalize_universe_to_canonical_markets(
            [m_bef_2027, m_by_jun27, m_nato_jun, m_nato_dec, m_spx_low_7200, m_spx_low_4500, m_tatum_pts, m_cel_1q, m_cel_full, m_lepen_1, m_lepen_2, m_perim_nov, m_perim_dec]
        )
        books = build_instrument_order_books(
            mkts,
            {
                # Make reversed `NO_jun + YES_bef27` look "cheap" (`0.40 + 0.40 = 0.80`) while true `NO_bef27 + YES_jun` is `0.45 + 0.46 = 0.91`!
                "tok_lv_bef_27_0": _mk_book(0.40),
                "tok_lv_bef_27_1": _mk_book(0.45),
                "tok_lv_jun_27_0": _mk_book(0.46),
                "tok_lv_jun_27_1": _mk_book(0.40),
                "tok_lv_nato_jun_0": _mk_book(0.55),
                "tok_lv_nato_jun_1": _mk_book(0.44),
                "tok_lv_nato_dec_0": _mk_book(0.46),
                "tok_lv_nato_dec_1": _mk_book(0.40),
                # SPX LOW: `NO(4500) + YES(7200) = 0.44 + 0.46 = 0.90` valid; wrong `NO(7200) + YES(4500)` is `0.10 + 0.10 = 0.20`!
                "tok_lv_spx_7200_0": _mk_book(0.46),
                "tok_lv_spx_7200_1": _mk_book(0.10),
                "tok_lv_spx_4500_0": _mk_book(0.10),
                "tok_lv_spx_4500_1": _mk_book(0.44),
                "tok_lv_tatum_0": _mk_book(0.10),
                "tok_lv_tatum_1": _mk_book(0.10),
                "tok_lv_cel_1q_0": _mk_book(0.10),
                "tok_lv_cel_1q_1": _mk_book(0.10),
                "tok_lv_cel_full_0": _mk_book(0.10),
                "tok_lv_cel_full_1": _mk_book(0.10),
                "tok_lv_lp_1_0": _mk_book(0.10),
                "tok_lv_lp_1_1": _mk_book(0.10),
                "tok_lv_lp_2_0": _mk_book(0.10),
                "tok_lv_lp_2_1": _mk_book(0.10),
                "tok_lv_perim_nov_0": _mk_book(0.05),
                "tok_lv_perim_nov_1": _mk_book(0.05),
                "tok_lv_perim_dec_0": _mk_book(0.05),
                "tok_lv_perim_dec_1": _mk_book(0.05),
            },
            default_fetch_ts=NOW_TS,
        )

        opps_e, rej_e = detect_family_e_temporal_deadline_arbitrage(mkts, books, verifier=_verifier(), now_ts=NOW_TS)
        jd_op = [o for o in opps_e if set(o.market_ids) == {"lv_bef_27", "lv_jun_27"}][0]
        self.assertEqual(jd_op.relationship_type, "A_IMPLIES_B")
        self.assertEqual({lg.instrument_id for lg in jd_op.structure.legs}, {"tok_lv_bef_27_1", "tok_lv_jun_27_0"})

        nato_op = [o for o in opps_e if set(o.market_ids) == {"lv_nato_jun", "lv_nato_dec"}][0]
        self.assertEqual(nato_op.relationship_type, "A_IMPLIES_B")
        self.assertEqual({lg.instrument_id for lg in nato_op.structure.legs}, {"tok_lv_nato_jun_1", "tok_lv_nato_dec_0"})

        perim_op = [o for o in opps_e if set(o.market_ids) == {"lv_perim_nov", "lv_perim_dec"}][0]
        self.assertEqual(perim_op.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("RESET_WINDOW_NON_CONTAINMENT", rej_e)

        opps_f, _ = detect_family_f_price_strike_ladders(mkts, books, verifier=_verifier(), now_ts=NOW_TS)
        spx_op = [o for o in opps_f if set(o.market_ids) == {"lv_spx_7200", "lv_spx_4500"}][0]
        self.assertEqual(spx_op.sub_type, "DOWNWARD_STRIKE_DOMINANCE")
        self.assertEqual({lg.instrument_id for lg in spx_op.structure.legs}, {"tok_lv_spx_4500_1", "tok_lv_spx_7200_0"})

        # Also verify description-defined downward barrier (`"hit K"` where rules say `"equal to or below the listed value"`, board #20)
        m_dn_36 = _mk_market(
            "lv_dn_36", "Will the 10-year Treasury yield hit 3.60% in December?",
            event_id="ev_10y_dn",
            description="Resolves Yes if the Treasury 10-year yield is equal to or below the listed value for any date in December 2026 (home.treasury.gov Daily Treasury Par Yield).",
            end_date="2026-12-31T23:59:00Z",
        )
        m_dn_34 = _mk_market(
            "lv_dn_34", "Will the 10-year Treasury yield hit 3.40% in December?",
            event_id="ev_10y_dn",
            description="Resolves Yes if the Treasury 10-year yield is equal to or below the listed value for any date in December 2026 (home.treasury.gov Daily Treasury Par Yield).",
            end_date="2026-12-31T23:59:00Z",
        )
        mkts_dn = normalize_universe_to_canonical_markets([m_dn_36, m_dn_34])
        books_dn = build_instrument_order_books(
            mkts_dn,
            {
                # Valid downward `<= 3.40% => <= 3.60%` buys `NO(3.40%) + YES(3.60%) = 0.44 + 0.46 = 0.90`; wrong upward `NO(3.60%) + YES(3.40%) = 0.15 + 0.15`!
                "tok_lv_dn_36_0": _mk_book(0.46),
                "tok_lv_dn_36_1": _mk_book(0.15),
                "tok_lv_dn_34_0": _mk_book(0.15),
                "tok_lv_dn_34_1": _mk_book(0.44),
            },
            default_fetch_ts=NOW_TS,
        )
        opps_dn, _ = detect_family_f_price_strike_ladders(mkts_dn, books_dn, verifier=_verifier(), now_ts=NOW_TS)
        dn_op = [o for o in opps_dn if set(o.market_ids) == {"lv_dn_36", "lv_dn_34"}][0]
        self.assertEqual(dn_op.sub_type, "DOWNWARD_STRIKE_DOMINANCE")
        self.assertEqual({lg.instrument_id for lg in dn_op.structure.legs}, {"tok_lv_dn_34_1", "tok_lv_dn_36_0"})

        opps_g, rej_g = detect_family_g_sports_structures(mkts, books, verifier=_verifier())
        self.assertFalse(any("lv_tatum" in o.market_ids for o in opps_g))
        for o in opps_g:
            self.assertNotIn(o.proof.opportunity_class, {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value})
        self.assertIn("SUBPERIOD_VS_FULL_GAME_MISMATCH", rej_g)

        opps_i, rej_i = detect_family_i_duplicate_markets(mkts, books, verifier=_verifier())
        for o in [x for x in opps_i if set(x.market_ids) == {"lv_lp_1", "lv_lp_2"}]:
            self.assertEqual(o.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("ASYMMETRIC_PROPOSITION_TOKENS", rej_i)

    def test_qa_auditor_adversarial_probes_bug_ls_1_to_5(self) -> None:
        # `BUG-LS-1`: Unsigned `"Will Bitcoin hit/reach/touch $95,000?"` vs `"$90,000?"` with NO `(HIGH)`/`(LOW)`/`↑`/`↓`
        # and NO directional inequality in `description` (`"touches the target price"`) MUST quarantine to `CLASS_D` (`UNSPECIFIED_OBS`)!
        m_hit95 = _mk_market(
            "qa_hit95", "Will Bitcoin hit $95,000 by December 31, 2026?", event_id="ev_qa_hit",
            description="Resolves Yes if Bitcoin touches the target price on Binance by December 31, 2026, 11:59 PM ET.",
            resolution_source="https://binance.com", end_date="2027-01-01T04:59:59Z",
        )
        m_hit90 = _mk_market(
            "qa_hit90", "Will Bitcoin hit $90,000 by December 31, 2026?", event_id="ev_qa_hit",
            description="Resolves Yes if Bitcoin touches the target price on Binance by December 31, 2026, 11:59 PM ET.",
            resolution_source="https://binance.com", end_date="2027-01-01T04:59:59Z",
        )
        mkts_ls1 = normalize_universe_to_canonical_markets([m_hit95, m_hit90])
        books_ls1 = build_instrument_order_books(
            mkts_ls1,
            {"tok_qa_hit95_0": _mk_book(0.40), "tok_qa_hit95_1": _mk_book(0.40), "tok_qa_hit90_0": _mk_book(0.40), "tok_qa_hit90_1": _mk_book(0.40)},
            default_fetch_ts=NOW_TS,
        )
        opps_ls1, rej_ls1 = detect_family_f_price_strike_ladders(mkts_ls1, books_ls1, verifier=_verifier(), now_ts=NOW_TS)
        for o in opps_ls1:
            self.assertEqual(o.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("OBSERVATION_MODE_UNSPECIFIED", rej_ls1)

        # `BUG-LS-2`: Multi-party seat/count ranges (`"Labour Party win 35-39 seats"` + `"National Party win 35-39 seats"`)
        # MUST NOT be classified as `MUTUAL_EXCLUSION` (`CLASS_B`), because BOTH parties can win `35-39` seats!
        m_nz_lab = _mk_market(
            "qa_nz_lab", "Will the Labour Party win 35-39 seats in the NZ House of Representatives?", event_id="ev_nz1",
            description="Official Electoral Commission results.", end_date="2026-12-15T23:59:59Z",
        )
        m_nz_nat = _mk_market(
            "qa_nz_nat", "Will the National Party win 35-39 seats in the NZ House of Representatives?", event_id="ev_nz2",
            description="Official Electoral Commission results.", end_date="2026-12-15T23:59:59Z",
        )
        mkts_ls2 = normalize_universe_to_canonical_markets([m_nz_lab, m_nz_nat])
        books_ls2 = build_instrument_order_books(
            mkts_ls2,
            {"tok_qa_nz_lab_0": _mk_book(0.60), "tok_qa_nz_lab_1": _mk_book(0.35), "tok_qa_nz_nat_0": _mk_book(0.60), "tok_qa_nz_nat_1": _mk_book(0.35)},
            default_fetch_ts=NOW_TS,
        )
        opps_ls2, _ = detect_family_d_logical_arbitrage(mkts_ls2, books_ls2, verifier=_verifier())
        self.assertFalse(any(o.proof.opportunity_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value} for o in opps_ls2))

        # `BUG-LS-3`: Subject-object reversal (`"Will OpenAI acquire Anthropic before 2027?"` vs `"Will Anthropic acquire OpenAI before 2027?"`)
        # MUST reject as `WORD_ORDER_SUBJECT_OBJECT_INVERSION` (`CLASS_D`), while voice-only `"Anthropic acquired before 2027?"`
        # vs `"Will Anthropic be acquired before 2027?"` (`stem1 == stem2`) remains `CLASS_B`!
        desc_acq = "Resolves Yes per consensus of credible reporting by December 31, 2026, 11:59 PM ET."
        m_oa_ant = _mk_market("qa_oa_ant", "Will OpenAI acquire Anthropic before 2027?", event_id="ev_acq1", description=desc_acq, end_date="2027-01-01T04:59:00Z")
        m_ant_oa = _mk_market("qa_ant_oa", "Will Anthropic acquire OpenAI before 2027?", event_id="ev_acq2", description=desc_acq, end_date="2027-01-01T04:59:00Z")
        m_ant_v1 = _mk_market("qa_ant_v1", "Anthropic acquired before 2027?", event_id="ev_acq3", description=desc_acq, end_date="2027-01-01T04:59:00Z")
        m_ant_v2 = _mk_market("qa_ant_v2", "Will Anthropic be acquired before 2027?", event_id="ev_acq4", description=desc_acq, end_date="2027-01-01T04:59:00Z")
        mkts_ls3 = normalize_universe_to_canonical_markets([m_oa_ant, m_ant_oa, m_ant_v1, m_ant_v2])
        books_ls3 = build_instrument_order_books(
            mkts_ls3,
            {
                "tok_qa_oa_ant_0": _mk_book(0.40), "tok_qa_oa_ant_1": _mk_book(0.40),
                "tok_qa_ant_oa_0": _mk_book(0.40), "tok_qa_ant_oa_1": _mk_book(0.40),
                "tok_qa_ant_v1_0": _mk_book(0.44), "tok_qa_ant_v1_1": _mk_book(0.56),
                "tok_qa_ant_v2_0": _mk_book(0.56), "tok_qa_ant_v2_1": _mk_book(0.44),
            },
            default_fetch_ts=NOW_TS,
        )
        opps_ls3, rej_ls3 = detect_family_i_duplicate_markets(mkts_ls3, books_ls3, verifier=_verifier())
        inv_ops = [o for o in opps_ls3 if set(o.market_ids) == {"qa_oa_ant", "qa_ant_oa"}]
        self.assertTrue(len(inv_ops) >= 1)
        for o in inv_ops:
            self.assertEqual(o.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("WORD_ORDER_SUBJECT_OBJECT_INVERSION", rej_ls3)
        valid_dup = [o for o in opps_ls3 if set(o.market_ids) == {"qa_ant_v1", "qa_ant_v2"} and o.proof.opportunity_class == OpportunityClass.CLASS_B.value]
        self.assertEqual(len(valid_dup), 1)

        # `BUG-LS-4`: Unrelated early `8:30 AM` in background prose (`"BLS releases reports at 8:30 AM ET. Resolves Yes if confirmed by Nov 30, 2026, 11:59 PM ET."`)
        # MUST NOT create a fake intra-day `08:30 => 23:59` `TEMPORAL_DEADLINE_IMPLICATION` `CLASS_B` against another `Nov 30, 11:59 PM ET` market!
        m_bls_a = _mk_market(
            "qa_bls_a", "Will US CPI report show deflation by November 30, 2026?", event_id="ev_bls_a",
            description="BLS releases reports at 8:30 AM ET. Resolves Yes if confirmed by BLS by November 30, 2026, 11:59 PM ET.",
            resolution_source="https://bls.gov", end_date="2026-12-01T04:59:59Z",
        )
        m_bls_b = _mk_market(
            "qa_bls_b", "Will US CPI report show deflation by November 30, 2026?", event_id="ev_bls_b",
            description="Resolves Yes if confirmed by BLS by November 30, 2026, 11:59 PM ET.",
            resolution_source="https://bls.gov", end_date="2026-12-01T04:59:59Z",
        )
        mkts_ls4 = normalize_universe_to_canonical_markets([m_bls_a, m_bls_b])
        books_ls4 = build_instrument_order_books(
            mkts_ls4,
            {"tok_qa_bls_a_0": _mk_book(0.40), "tok_qa_bls_a_1": _mk_book(0.40), "tok_qa_bls_b_0": _mk_book(0.40), "tok_qa_bls_b_1": _mk_book(0.40)},
            default_fetch_ts=NOW_TS,
        )
        opps_ls4, _ = detect_family_e_temporal_deadline_arbitrage(mkts_ls4, books_ls4, verifier=_verifier(), now_ts=NOW_TS)
        self.assertEqual(opps_ls4, [])

        # `BUG-LS-5`: Bare `"Chicago"` (no ICAO/airport facility -> `station_explicit=False`) vs `"Chicago (KORD)"` (or another bare `"Chicago"`)
        # MUST NEVER promote to `CLASS_B` (`WEATHER_STATION_ICAO_UNSPECIFIED` -> `CLASS_D`)!
        m_chi_bare = _mk_market(
            "qa_chi_bare", "Will the highest temperature in Chicago be 55°F or higher on November 20, 2026?", event_id="ev_chi1",
            description="Resolves per official weather station in whole degrees.", end_date="2026-11-21T05:59:59Z",
        )
        m_chi_kord = _mk_market(
            "qa_chi_kord", "Will the highest temperature in Chicago be 50°F or higher on November 20, 2026?", event_id="ev_chi2",
            description="Resolves per Weather Underground Chicago O'Hare (KORD) in whole degrees.",
            resolution_source="https://www.wunderground.com/history/daily/us/il/chicago/KORD", end_date="2026-11-21T05:59:59Z",
        )
        m_chi_bare2 = _mk_market(
            "qa_chi_bare2", "Will the highest temperature in Chicago be 50°F or higher on November 20, 2026?", event_id="ev_chi3",
            description="Resolves per official weather station in whole degrees.", end_date="2026-11-21T05:59:59Z",
        )
        mkts_ls5 = normalize_universe_to_canonical_markets([m_chi_bare, m_chi_kord, m_chi_bare2])
        books_ls5 = build_instrument_order_books(
            mkts_ls5,
            {
                "tok_qa_chi_bare_0": _mk_book(0.40), "tok_qa_chi_bare_1": _mk_book(0.40),
                "tok_qa_chi_kord_0": _mk_book(0.40), "tok_qa_chi_kord_1": _mk_book(0.40),
                "tok_qa_chi_bare2_0": _mk_book(0.40), "tok_qa_chi_bare2_1": _mk_book(0.40),
            },
            default_fetch_ts=NOW_TS,
        )
        opps_ls5, rej_ls5 = detect_family_h_weather_measurable(mkts_ls5, books_ls5, verifier=_verifier())
        self.assertTrue(len(opps_ls5) >= 1)
        for o in opps_ls5:
            self.assertEqual(o.proof.opportunity_class, OpportunityClass.CLASS_D.value)
        self.assertIn("WEATHER_STATION_ICAO_UNSPECIFIED", rej_ls5)


if __name__ == "__main__":
    unittest.main()

"""
Adversarial & End-to-End Unit Tests for `full_throttle_pipeline.py`,
`run_dominus_full_throttle.py`, and `generate_full_throttle_dashboard.py`.

Owned exclusively by `@pipeline-shadow`.
Uses Python 3.12 stdlib `unittest.TestCase` only (`D-010` swapless-safe).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_full_throttle_dashboard import (
    generate_dashboard_files,
    render_full_throttle_dashboard_markdown,
)
from src.polymarket_research.full_throttle_pipeline import (
    AUTHORITATIVE_LIVE_WALLET_BASELINE,
    FAMILY_CODES,
    PIPELINE_STAGES_ORDERED,
    ExecutionMode,
    ExecutionModeController,
    ExecutionModeGateConfig,
    FullThrottlePipeline,
    LiveExecutionHardLockError,
    OperatingCycleType,
    PipelineConfig,
    get_process_rss_mib,
    normalize_family_code,
)


def _make_book(
    asset_id: str,
    market_id: str,
    asks: list[tuple[float, float]],
    bids: list[tuple[float, float]],
    *,
    min_size: float = 5.0,
    tick_size: float = 0.01,
) -> dict:
    return {
        "asset_id": asset_id,
        "market": market_id,
        "asks": [{"price": str(p), "size": str(s)} for p, s in asks],
        "bids": [{"price": str(p), "size": str(s)} for p, s in bids],
        "min_order_size": str(min_size),
        "tick_size": str(tick_size),
    }


def _build_synthetic_universe_and_books_seq() -> tuple[list[dict], list[dict], dict]:
    """
    Constructs a rich multi-event synthetic Polymarket universe exercising:
      - Family A: Binary Buy-Merge arb (`m_bin_arb`) + near-miss dormant market (`m_dormant`)
      - Family B/C: 3-way closed NegRisk slate (`ev_nr_3way`, `>= 3` sequential legs -> `D-007` quarantined below `$500` NAV!)
      - Family B/C Trap: Augmented NegRisk slate with placeholder (`ev_aug_trap` -> must NEVER be `CLASS_A/B`!)
      - Family E: Temporal deadline pair (`by June 30, 2027 UTC` => `by Dec 31, 2027 UTC`)
      - Family F: Strike ladder pair (`Bitcoin above $120,000` => `Bitcoin above $100,000` on Dec 31, 2027)
      - Family J: Recyclable pre-held inventory completion (`m_inv_ok` -> `CLASS_A`!) + Frozen disputed `KMIA` (`6707503` -> `D-001` blocked!)
      - Family K/L/N: UMA `proposed` market (`m_uma_prop` -> `CLASS_C`, never `CLASS_A/B`!) + quadratic fee market (`crypto_15_min`)
    """
    events = [
        {
            "id": "ev_bin_1",
            "slug": "macro-rate-decision",
            "title": "Macro Rate Decision Binary",
            "category": "economics",
            "negRisk": False,
            "markets": [
                {
                    "id": "m_bin_arb",
                    "question": "Will central bank hold rates steady at Q3 meeting?",
                    "conditionId": "0xcond_bin_arb",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_bin_yes", "tok_bin_no"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                    "orderMinSize": 5,
                    "orderPriceMinTickSize": 0.01,
                    "endDate": "2027-09-30T23:59:59Z",
                    "description": "Resolves Yes per official central bank statement UTC.",
                },
                {
                    "id": "m_dormant",
                    "question": "Will Q3 GDP growth exceed 2.5% annualized?",
                    "conditionId": "0xcond_dormant",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_dorm_yes", "tok_dorm_no"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                    "orderMinSize": 5,
                    "orderPriceMinTickSize": 0.01,
                    "endDate": "2027-10-30T23:59:59Z",
                    "description": "Resolves per BEA advance estimate.",
                },
                {
                    "id": "m_disabled_ob",
                    "question": "Disabled orderbook market check",
                    "conditionId": "0xcond_dis",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_dis_y", "tok_dis_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "enableOrderBook": False,
                },
            ],
        },
        {
            "id": "ev_inv_and_kmia",
            "slug": "inventory-and-kmia-check",
            "title": "Inventory Completion & KMIA Freeze Test",
            "category": "weather",
            "negRisk": False,
            "markets": [
                {
                    "id": "m_inv_ok",
                    "question": "Will station KBOS record rain on Nov 20, 2027?",
                    "conditionId": "0xcond_inv_ok",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_inv_yes", "tok_inv_no"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                    "orderMinSize": 5,
                    "orderPriceMinTickSize": 0.01,
                    "endDate": "2027-11-20T23:59:59Z",
                    "description": "Resolves per NWS KBOS daily climate report.",
                },
                {
                    "id": "6707503",
                    "question": "Highest temperature in Miami KMIA on Nov 7?",
                    "conditionId": "0xcond_kmia_disputed",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_kmia_y", "tok_kmia_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "umaResolutionStatus": "disputed",
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                },
            ],
        },
        {
            "id": "ev_nr_3way",
            "slug": "mayor-election-closed-slate",
            "title": "Closed 3-Way NegRisk Election",
            "category": "politics",
            "negRisk": True,
            "enableNegRisk": True,
            "negRiskMarketID": "0xnr_closed_3way",
            "negRiskAugmented": False,
            "markets": [
                {
                    "id": "m_nr_1",
                    "question": "Will Alice win the election?",
                    "groupItemTitle": "Alice",
                    "questionIndex": 0,
                    "conditionId": "0xc_nr1",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_nr1_y", "tok_nr1_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "negRisk": True,
                    "negRiskMarketID": "0xnr_closed_3way",
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                    "orderMinSize": 5,
                },
                {
                    "id": "m_nr_2",
                    "question": "Will Bob win the election?",
                    "groupItemTitle": "Bob",
                    "questionIndex": 1,
                    "conditionId": "0xc_nr2",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_nr2_y", "tok_nr2_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "negRisk": True,
                    "negRiskMarketID": "0xnr_closed_3way",
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                    "orderMinSize": 5,
                },
                {
                    "id": "m_nr_3",
                    "question": "Will Carol win the election?",
                    "groupItemTitle": "Carol",
                    "questionIndex": 2,
                    "conditionId": "0xc_nr3",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_nr3_y", "tok_nr3_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "negRisk": True,
                    "negRiskMarketID": "0xnr_closed_3way",
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                    "orderMinSize": 5,
                },
            ],
        },
        {
            "id": "ev_aug_trap",
            "slug": "augmented-negrisk-trap",
            "title": "Augmented NegRisk With Placeholder",
            "category": "politics",
            "negRisk": True,
            "enableNegRisk": True,
            "negRiskAugmented": True,
            "enableNegRiskOther": True,
            "markets": [
                {
                    "id": "m_aug_1",
                    "question": "Will Candidate Alpha win?",
                    "groupItemTitle": "Candidate Alpha",
                    "questionIndex": 0,
                    "conditionId": "0xc_aug1",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_aug1_y", "tok_aug1_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "negRisk": True,
                    "negRiskAugmented": True,
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                },
                {
                    "id": "m_aug_2",
                    "question": "Will Person A win?",
                    "groupItemTitle": "Person A",
                    "questionIndex": 1,
                    "conditionId": "0xc_aug2",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_aug2_y", "tok_aug2_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "negRisk": True,
                    "negRiskAugmented": True,
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                },
            ],
        },
        {
            "id": "ev_temporal_and_uma",
            "slug": "temporal-and-uma-carry",
            "title": "Temporal Monotonicity & UMA Carry",
            "category": "tech",
            "negRisk": False,
            "cumulativeMarkets": True,
            "markets": [
                {
                    "id": "m_temp_early",
                    "question": "Will Starship reach orbit by June 30, 2027?",
                    "conditionId": "0xc_temp_1",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_te_y", "tok_te_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                    "endDate": "2027-06-30T23:59:59Z",
                    "description": "Resolves Yes per official FAA/SpaceX confirmation by June 30, 2027 11:59 PM UTC.",
                },
                {
                    "id": "m_temp_late",
                    "question": "Will Starship reach orbit by December 31, 2027?",
                    "conditionId": "0xc_temp_2",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_tl_y", "tok_tl_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "feeType": "zero_fees",
                    "endDate": "2027-12-31T23:59:59Z",
                    "description": "Resolves Yes per official FAA/SpaceX confirmation by December 31, 2027 11:59 PM UTC.",
                },
                {
                    "id": "m_uma_prop",
                    "question": "Did Q4 earnings beat consensus?",
                    "conditionId": "0xc_uma_prop",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_uma_y", "tok_uma_n"]',
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "umaResolutionStatus": "proposed",
                    "feesEnabled": True,
                    "feeType": "crypto_15_min",
                    "feeSchedule": {"rate": 0.25, "exponent": 2, "takerOnly": True, "rebateRate": 0.20},
                    "endDate": "2026-11-10T23:59:59Z",
                    "description": "Resolves per company 8-K.",
                },
            ],
        },
    ]

    # Cycle 1 books:
    # - `m_bin_arb`: ask(YES)=0.46, ask(NO)=0.49 => sum=0.95 -> net +$0.05/sh `CLASS_B`!
    # - `m_dormant`: ask(YES)=0.51, ask(NO)=0.50 => sum=1.01 -> `100 bps` near-miss stored in `DormantOpportunityStore`!
    # - `m_inv_ok`: pre-held 10 shares of `tok_inv_yes` (cost 0.45, mark_bid 0.46) + `tok_inv_no` ask=0.48 => 0.46+0.48=0.94 < 1.00 -> 1-leg FOK `CLASS_A`!
    # - `6707503` (KMIA disputed): even with enticing asks 0.20 + 0.20, MUST be `D-001` blocked (`CLASS_E`)!
    # - `ev_nr_3way`: 3-leg YES sum = 0.30 + 0.31 + 0.32 = 0.93 -> `CLASS_B` but `>=3` sequential legs quarantined under `D-007` at `$48.70 < $500`!
    # - `ev_aug_trap`: asks 0.30 + 0.30 = 0.60, but augmented placeholder -> MUST be `CLASS_D`, NEVER `CLASS_A/B`!
    # - `m_temp_early` / `m_temp_late`: `NO_early` ask=0.45 + `YES_late` ask=0.49 = 0.94 < 1.00 -> `CLASS_B` temporal arb!
    # - `m_uma_prop`: `tok_uma_y` ask=0.985 on `proposed` UMA -> `CLASS_C` carry (NEVER `CLASS_A/B`)!
    books_cycle_1 = {
        "tok_bin_yes": _make_book("tok_bin_yes", "m_bin_arb", [(0.46, 20.0)], [(0.44, 20.0)]),
        "tok_bin_no": _make_book("tok_bin_no", "m_bin_arb", [(0.49, 20.0)], [(0.47, 20.0)]),
        "tok_dorm_yes": _make_book("tok_dorm_yes", "m_dormant", [(0.51, 25.0)], [(0.48, 25.0)]),
        "tok_dorm_no": _make_book("tok_dorm_no", "m_dormant", [(0.50, 25.0)], [(0.47, 25.0)]),
        "tok_inv_yes": _make_book("tok_inv_yes", "m_inv_ok", [(0.54, 15.0)], [(0.46, 15.0)]),
        "tok_inv_no": _make_book("tok_inv_no", "m_inv_ok", [(0.48, 15.0)], [(0.45, 15.0)]),
        "tok_kmia_y": _make_book("tok_kmia_y", "6707503", [(0.20, 50.0)], [(0.01, 50.0)]),
        "tok_kmia_n": _make_book("tok_kmia_n", "6707503", [(0.20, 50.0)], [(0.01, 50.0)]),
        "tok_nr1_y": _make_book("tok_nr1_y", "m_nr_1", [(0.30, 20.0)], [(0.28, 20.0)]),
        "tok_nr1_n": _make_book("tok_nr1_n", "m_nr_1", [(0.71, 20.0)], [(0.68, 20.0)]),
        "tok_nr2_y": _make_book("tok_nr2_y", "m_nr_2", [(0.31, 20.0)], [(0.29, 20.0)]),
        "tok_nr2_n": _make_book("tok_nr2_n", "m_nr_2", [(0.70, 20.0)], [(0.67, 20.0)]),
        "tok_nr3_y": _make_book("tok_nr3_y", "m_nr_3", [(0.32, 20.0)], [(0.30, 20.0)]),
        "tok_nr3_n": _make_book("tok_nr3_n", "m_nr_3", [(0.69, 20.0)], [(0.66, 20.0)]),
        "tok_aug1_y": _make_book("tok_aug1_y", "m_aug_1", [(0.30, 20.0)], [(0.28, 20.0)]),
        "tok_aug1_n": _make_book("tok_aug1_n", "m_aug_1", [(0.70, 20.0)], [(0.68, 20.0)]),
        "tok_aug2_y": _make_book("tok_aug2_y", "m_aug_2", [(0.30, 20.0)], [(0.28, 20.0)]),
        "tok_aug2_n": _make_book("tok_aug2_n", "m_aug_2", [(0.70, 20.0)], [(0.68, 20.0)]),
        "tok_te_y": _make_book("tok_te_y", "m_temp_early", [(0.56, 20.0)], [(0.54, 20.0)]),
        "tok_te_n": _make_book("tok_te_n", "m_temp_early", [(0.45, 20.0)], [(0.43, 20.0)]),
        "tok_tl_y": _make_book("tok_tl_y", "m_temp_late", [(0.49, 20.0)], [(0.47, 20.0)]),
        "tok_tl_n": _make_book("tok_tl_n", "m_temp_late", [(0.53, 20.0)], [(0.51, 20.0)]),
        "tok_uma_y": _make_book("tok_uma_y", "m_uma_prop", [(0.985, 40.0)], [(0.980, 40.0)], tick_size=0.001),
        "tok_uma_n": _make_book("tok_uma_n", "m_uma_prop", [(0.020, 40.0)], [(0.015, 40.0)], tick_size=0.001),
    }

    # Cycle 2 books: `tok_dorm_yes` shifts from `0.51` down to `0.47` (`0.47 + 0.50 = 0.97 < 1.00`!),
    # waking `m_dormant` from `DormantOpportunityStore` and promoting it to `CLASS_B`!
    books_cycle_2 = dict(books_cycle_1)
    books_cycle_2["tok_dorm_yes"] = _make_book("tok_dorm_yes", "m_dormant", [(0.47, 25.0)], [(0.45, 25.0)])

    portfolio_state = {
        "live_bankroll": 48.695132,
        "reconciled_nav_usd": 48.695132,
        "active_positions": {
            "REC_HOLDING_KBOS_1": {
                "trade_id": "REC_HOLDING_KBOS_1",
                "market_id": "m_inv_ok",
                "condition_id": "0xcond_inv_ok",
                "token_id": "tok_inv_yes",
                "side": "YES",
                "remaining_shares": 10.0,
                "notional_usd": 4.50,
                "best_bid": 0.46,
                "umaResolutionStatus": "none",
                "is_frozen_disputed": False,
            },
            "WS_SNIPE_Miami_KMIA_242960": {
                "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                "market_id": "6707503",
                "token_id": "tok_kmia_n",
                "side": "NO",
                "remaining_shares": 35.0,
                "notional_usd": 34.19,
                "umaResolutionStatus": "disputed",
                "is_frozen_disputed": True,
            },
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898",
                "market_id": "6707502",
                "token_id": "tok_kmia_6707502_y",
                "side": "YES",
                "remaining_shares": 17.0,
                "notional_usd": 16.32,
                "umaResolutionStatus": "disputed",
                "is_frozen_disputed": True,
            },
        },
    }
    return events, [books_cycle_1, books_cycle_2, books_cycle_2], portfolio_state


class TestFullThrottlePipelineAndDashboard(unittest.TestCase):
    def test_01_mode_3_live_hard_locked_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            # 1. Default `MODE_2_SHADOW` succeeds and blocks live order dispatch
            shadow_ctrl = ExecutionModeController(
                ExecutionModeGateConfig(mode=ExecutionMode.MODE_2_SHADOW, jurisdiction_code="CA-ON")
            )
            self.assertFalse(shadow_ctrl.allows_live_orders)
            with self.assertRaises(LiveExecutionHardLockError):
                shadow_ctrl.assert_no_live_order_dispatch("place_clob_order")

            # 2. `MODE_3_LIVE` in `CA-ON` without regulated venue or approval JSON MUST raise `LiveExecutionHardLockError`
            with self.assertRaises(LiveExecutionHardLockError) as ctx_jur:
                ExecutionModeController(
                    ExecutionModeGateConfig(
                        mode=ExecutionMode.MODE_3_LIVE,
                        jurisdiction_code="CA-ON",
                        approvals_dir=tmp_p / "approvals",
                    )
                )
            self.assertIn("D008_JURISDICTION_GATE_BLOCKED:CA-ON", str(ctx_jur.exception))
            self.assertIn("D002_PROPOSAL_ONLY_LIVE_PROMOTION_MISSING_HUMAN_APPROVAL_JSON", str(ctx_jur.exception))

            # 3. Even with non-restricted jurisdiction + valid human approval JSON, `PAA_MASTER_STOP` blocks `MODE_3_LIVE`
            app_dir = tmp_p / "approvals"
            app_dir.mkdir(parents=True)
            app_file = app_dir / "owner_live_approval.json"
            app_file.write_text(
                json.dumps(
                    {
                        "approved": True,
                        "approval_scope": "MODE_3_LIVE_EXECUTION",
                        "approved_by_human_owner": "Anton",
                    }
                ),
                encoding="utf-8",
            )
            stop_file = tmp_p / "PAA_MASTER_STOP"
            stop_file.write_text("STOP", encoding="utf-8")
            with self.assertRaises(LiveExecutionHardLockError) as ctx_stop:
                ExecutionModeController(
                    ExecutionModeGateConfig(
                        mode=ExecutionMode.MODE_3_LIVE,
                        jurisdiction_code="IE",
                        approvals_dir=app_dir,
                        master_stop_path=stop_file,
                        accounting_safeguard_path=tmp_p / "NO_SAFEGUARD.json",
                    )
                )
            self.assertIn("PAA_MASTER_STOP_ACTIVE", str(ctx_stop.exception))

    def test_02_family_normalization_and_rss_guard(self) -> None:
        self.assertEqual(len(FAMILY_CODES), 14)
        self.assertEqual(normalize_family_code("FAMILY_E_TEMPORAL_DEADLINE"), "E")
        self.assertEqual(normalize_family_code("a"), "A")
        self.assertEqual(normalize_family_code("FAMILY_M_MULTILEG_PORTFOLIO"), "M")
        rss = get_process_rss_mib()
        self.assertGreaterEqual(rss, 0.0)
        self.assertLess(rss, 180.0)

    def test_03_end_to_end_10_stage_multi_cycle_dormant_wakeup_and_dashboard(self) -> None:
        events, books_seq, port_state = _build_synthetic_universe_and_books_seq()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "pipeline_out"
            md_path = Path(tmp) / "FULL_THROTTLE_DASHBOARD.md"
            cfg = PipelineConfig(
                output_dir=out_dir,
                mode_gate=ExecutionModeGateConfig(mode=ExecutionMode.MODE_2_SHADOW, jurisdiction_code="CA-ON"),
                reconciled_nav_usd=48.695132,
                available_liquid_pusd=48.695132,
            )
            pipe = FullThrottlePipeline(config=cfg)
            payload = pipe.run_multi_cycle_campaign(
                discovery_sweeps=1,
                fast_cycles_per_sweep=1,
                include_research_cycle=True,
                inter_cycle_pause_sec=0.0,
                synthetic_events=events,
                synthetic_raw_books_sequence=books_seq,
                portfolio_state=port_state,
            )

            # 1. Verify all 3 operating cycles executed (`DISCOVERY_CYCLE`, `FAST_CYCLE`, `RESEARCH_CYCLE`)
            camp = payload["campaign_summary"]
            self.assertEqual(camp["total_cycles_executed"], 3)
            self.assertEqual(
                camp["cycle_types_executed"],
                ["DISCOVERY_CYCLE", "FAST_CYCLE", "RESEARCH_CYCLE"],
            )
            for cyc in payload["cycle_by_cycle_telemetry"]:
                self.assertEqual(tuple(cyc["stage_timings_ms"].keys()), PIPELINE_STAGES_ORDERED)

            # 2. Verify all 14 Opportunity Families `A..N` appear in detector coverage
            det_cov = payload["section_1c_detector_coverage_by_family"]
            for fc in FAMILY_CODES:
                self.assertIn(fc, det_cov)

            # 3. Verify `D-001` Frozen `KMIA` non-interference (`2` frozen holdings quarantined, `6707503` never executed)
            ucov = payload["section_1_universe_coverage"]
            self.assertEqual(ucov["d001_frozen_kmia_holdings_quarantined"], 2)
            self.assertEqual(ucov["recyclable_holdings_count"], 1)
            for top_op in payload["top_executable_opportunities"]:
                self.assertNotIn("6707503", top_op["market_ids"])
                self.assertNotIn("6707502", top_op["market_ids"])
                # Augmented NegRisk placeholder trap & UMA `proposed` carry MUST NEVER enter `CLASS_A/B`!
                self.assertNotIn("m_aug_1", top_op["market_ids"])
                self.assertNotIn("m_uma_prop", top_op["market_ids"])

            # 4. Verify `CLASS_A` (1-leg FOK inventory completion on `m_inv_ok`) vs `CLASS_B` (2-leg sequential `m_bin_arb`)
            top_by_mkt = {tuple(op["market_ids"]): op for op in payload["top_executable_opportunities"]}
            self.assertIn(("m_inv_ok",), top_by_mkt)
            self.assertEqual(top_by_mkt[("m_inv_ok",)]["opportunity_class"], "CLASS_A")
            self.assertIn(("m_bin_arb",), top_by_mkt)
            self.assertEqual(top_by_mkt[("m_bin_arb",)]["opportunity_class"], "CLASS_B")

            # 5. Verify `DormantOpportunityStore` stored `m_dormant` in Cycle 1 and promoted it on Cycle 2 book shift!
            dorm = payload["section_2c_dormant_opportunity_store"]
            self.assertGreaterEqual(dorm["total_rescans_triggered"], 1)
            self.assertGreaterEqual(dorm["total_promotions_to_executable"], 1)
            self.assertIn(("m_dormant",), top_by_mkt)

            # 6. Verify non-hindsight forward validation (`Cycle 1 -> Cycle 2` re-evaluated against fresh books)
            pers = payload["section_2b_persistence_and_forward_validation"]
            self.assertGreaterEqual(pers["forward_validations_completed"], 1)
            self.assertGreaterEqual(pers["forward_validations_survived"], 1)
            self.assertGreater(pers["forward_validated_net_pnl_usd"], 0.0)

            # 7. Verify `D-007` (`<= 15%` event concentration cap `$7.30` & `< $500` NAV `>= 3`-leg sequential quarantine)
            port = payload["section_3b_portfolio_allocation_48_70_pusd"]
            event_cap = round(48.695132 * 0.15, 6)
            for sl in port["allocated_slices"]:
                self.assertLessEqual(sl["allocated_capital_usd"], event_cap + 1e-5)
                # 3-leg sequential `ev_nr_3way` MUST NOT receive live-reference allocation below `$500` NAV
                self.assertNotIn("nr_3way", sl["candidate_id"])

            # 8. Verify Strict 3-Column Economic Segregation (`shadow_realized_wallet_cash_usd == 0.0` vs `$48.695132`)
            econ = payload["section_3_segregated_economics"]
            self.assertEqual(econ["column_2_realistic_forward_shadow"]["shadow_realized_wallet_cash_usd"], 0.0)
            self.assertAlmostEqual(
                econ["column_3_verified_live_wallet_cash"]["liquid_pusd_cash_usd"],
                AUTHORITATIVE_LIVE_WALLET_BASELINE["liquid_pusd_cash_usd"],
                places=6,
            )
            self.assertEqual(
                econ["column_3_verified_live_wallet_cash"]["new_live_orders_placed_by_full_throttle_runner"],
                0,
            )

            # 9. Verify checkpoint crash-recovery & durable files (`opportunity_ledger.jsonl`, `dormant_opportunities.json`)
            self.assertTrue(pipe.ledger_path.exists())
            self.assertTrue(pipe.dormant_path.exists())
            self.assertTrue(pipe.checkpoint_path.exists())
            self.assertTrue(pipe.dashboard_json_path.exists())

            recovered_pipe = FullThrottlePipeline(config=cfg)
            self.assertTrue(recovered_pipe.load_checkpoint())
            self.assertEqual(recovered_pipe.cycle_counter, 3)

            # 10. Verify Markdown Dashboard Generator (`FULL_THROTTLE_DASHBOARD.md`)
            rendered_path = generate_dashboard_files(
                dashboard_json_path=pipe.dashboard_json_path,
                markdown_out_path=md_path,
            )
            md_txt = rendered_path.read_text(encoding="utf-8")
            self.assertIn("DOMINUS — RISKLESS FULL THROTTLE", md_txt)
            self.assertIn("Strictly Segregated Economic Accounting", md_txt)
            self.assertIn("$48.695132", md_txt)
            self.assertIn("$24.67/month", md_txt)
            self.assertNotIn("\r\n", rendered_path.read_bytes().decode("utf-8"))

    def test_04_shared_orderbook_depth_never_double_counted(self) -> None:
        """Two competing `CLASS_B` candidates sharing `tok_shared_yes` (`10` shares total depth) cannot both claim `10` shares."""
        from scripts.run_dominus_full_throttle import main as cli_main  # ensure CLI module imports cleanly

        self.assertTrue(callable(cli_main))
        with tempfile.TemporaryDirectory() as tmp:
            cfg = PipelineConfig(
                output_dir=Path(tmp) / "out",
                reconciled_nav_usd=48.695132,
                available_liquid_pusd=48.695132,
            )
            pipe = FullThrottlePipeline(config=cfg)
            from src.polymarket_research.universal_arb_verifier import (
                ActionLeg,
                ActionType,
                CandidateStructure,
                InstrumentOrderBook,
                StateSpaceBuilder,
                UniversalArbVerifier,
                VerificationConfig,
            )
            from src.polymarket_research.full_throttle_pipeline import coerce_to_pipeline_record

            typed_books = {
                "tok_shared_y": InstrumentOrderBook.from_raw(
                    "tok_shared_y", _make_book("tok_shared_y", "m_sh_1", [(0.44, 10.0)], [(0.42, 10.0)])
                ),
                "tok_no_1": InstrumentOrderBook.from_raw(
                    "tok_no_1", _make_book("tok_no_1", "m_sh_1", [(0.48, 20.0)], [(0.46, 20.0)])
                ),
                "tok_no_2": InstrumentOrderBook.from_raw(
                    "tok_no_2", _make_book("tok_no_2", "m_sh_2", [(0.49, 20.0)], [(0.47, 20.0)])
                ),
            }
            ver = UniversalArbVerifier(config=VerificationConfig(max_budget_usd=48.70, reconciled_nav_usd=48.70))
            st1 = StateSpaceBuilder.binary_complete_set_states("tok_shared_y", "tok_no_1")
            st2 = StateSpaceBuilder.binary_complete_set_states("tok_shared_y", "tok_no_2")
            c1 = CandidateStructure(
                candidate_id="COMP_SHARED_1",
                family="A",
                legs=(
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_shared_y", market_id="m_sh_1"),
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_no_1", market_id="m_sh_1"),
                    ActionLeg(action_type=ActionType.CTF_MERGE, related_instrument_ids=("tok_shared_y", "tok_no_1"), market_id="m_sh_1"),
                ),
                states=st1,
                expected_lockup_hours=0.05,
                worst_case_lockup_hours=0.05,
            )
            c2 = CandidateStructure(
                candidate_id="COMP_SHARED_2",
                family="D",
                legs=(
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_shared_y", market_id="m_sh_2"),
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_no_2", market_id="m_sh_2"),
                ),
                states=st2,
                expected_lockup_hours=0.50,
                worst_case_lockup_hours=0.50,
            )
            r1 = coerce_to_pipeline_record(c1, verifier=ver, books=typed_books)
            r2 = coerce_to_pipeline_record(c2, verifier=ver, books=typed_books)
            alloc_summary = pipe._apply_portfolio_allocation([r1, r2], typed_books, {})
            total_shared_y_shares = sum(
                sl["allocated_shares"] for sl in alloc_summary["allocated_slices"]
            )
            self.assertLessEqual(total_shared_y_shares, 10.0 + 1e-6)
            self.assertEqual(r2.portfolio_rejection_reason, "SHARED_BOOK_DEPTH_OR_MIN_LOT_EXHAUSTED")

    def test_05_cli_live_mode_hard_lock_rejects_immediately(self) -> None:
        from scripts.run_dominus_full_throttle import main as cli_main

        with self.assertRaises(LiveExecutionHardLockError):
            cli_main(["--mode", "live", "--jurisdiction", "CA-ON"])

    def test_06_zero_trust_permission_gate_and_lf_hygiene(self) -> None:
        from src.paa_os.permissions import PermissionGate

        owned_files = [
            REPO_ROOT / "SYSTEM_AUDIT_BASELINE.md",
            REPO_ROOT / "src" / "polymarket_research" / "full_throttle_pipeline.py",
            REPO_ROOT / "scripts" / "run_dominus_full_throttle.py",
            REPO_ROOT / "scripts" / "generate_full_throttle_dashboard.py",
            REPO_ROOT / "scripts" / "deploy_polymarket_live.py",
            REPO_ROOT / "systemd" / "polymarket-full-throttle-sweep.service",
            REPO_ROOT / "systemd" / "polymarket-full-throttle-sweep.timer",
            REPO_ROOT / "tests" / "test_full_throttle_pipeline_and_dashboard.py",
        ]
        if (REPO_ROOT / "FULL_THROTTLE_DASHBOARD.md").exists():
            owned_files.append(REPO_ROOT / "FULL_THROTTLE_DASHBOARD.md")

        # Verify systemd swapless (`D-010`) and secret-free (`D-003`) invariants
        svc_txt = (REPO_ROOT / "systemd" / "polymarket-full-throttle-sweep.service").read_text(encoding="utf-8")
        tmr_txt = (REPO_ROOT / "systemd" / "polymarket-full-throttle-sweep.timer").read_text(encoding="utf-8")
        self.assertIn("MemoryMax=220M", svc_txt)
        self.assertIn("MemorySwapMax=0", svc_txt)
        self.assertIn("MALLOC_ARENA_MAX=2", svc_txt)
        self.assertIn("--cycles 2 --emit-harvester-candidates", svc_txt)
        self.assertNotIn("EnvironmentFile", svc_txt)
        self.assertIn("OnCalendar=*:02,17,32,47:15", tmr_txt)

        from scripts.deploy_polymarket_live import DEPLOY_MANIFEST

        for req_manifest in (
            "src/polymarket_research/full_throttle_pipeline.py",
            "src/polymarket_research/full_universe_discovery.py",
            "src/polymarket_research/universal_arb_verifier.py",
            "src/polymarket_research/market_proposition_graph.py",
            "src/polymarket_research/detectors_complete_set_and_negrisk.py",
            "src/polymarket_research/detectors_logical_and_specialized.py",
            "src/polymarket_research/detectors_microstructure_and_portfolio.py",
            "scripts/run_dominus_full_throttle.py",
            "scripts/generate_full_throttle_dashboard.py",
            "systemd/polymarket-full-throttle-sweep.service",
            "systemd/polymarket-full-throttle-sweep.timer",
        ):
            self.assertIn(req_manifest, DEPLOY_MANIFEST)

        diff_chunks: list[str] = []
        for fp in owned_files:
            self.assertTrue(fp.exists(), f"Missing owned file: {fp}")
            raw_b = fp.read_bytes()
            self.assertNotIn(b"\r\n", raw_b, f"CRLF detected in {fp}")
            rel = fp.relative_to(REPO_ROOT).as_posix()
            added_lines = "\n".join("+" + ln for ln in raw_b.decode("utf-8").splitlines())
            diff_chunks.append(f"diff --git a/{rel} b/{rel}\n--- /dev/null\n+++ b/{rel}\n@@ -0,0 +1 @@\n{added_lines}")

        gate = PermissionGate()
        rel_paths = [fp.relative_to(REPO_ROOT).as_posix() for fp in owned_files]
        ok, violations = gate.inspect_candidate_diff(rel_paths, "\n".join(diff_chunks))
        self.assertTrue(ok, f"PermissionGate violations: {violations}")
        self.assertEqual(violations, [])

    def test_07_per_rung_l2_depth_and_bare_proof_d007_cap(self) -> None:
        from src.polymarket_research.full_throttle_pipeline import coerce_to_pipeline_record
        from src.polymarket_research.universal_arb_verifier import (
            ActionLeg,
            ActionType,
            CandidateStructure,
            InstrumentOrderBook,
            StateSpaceBuilder,
            StateSpec,
            UniversalArbVerifier,
            VerificationConfig,
        )

        with tempfile.TemporaryDirectory() as tmp:
            pipe = FullThrottlePipeline(
                PipelineConfig(
                    output_dir=Path(tmp),
                    reconciled_nav_usd=48.70,
                    available_liquid_pusd=48.70,
                )
            )
            # `tok_l1_trap` has 10 shares @ $0.40 AND 500 unprofitable junk shares @ $0.99!
            typed_books = {
                "tok_l1_trap": InstrumentOrderBook.from_raw(
                    "tok_l1_trap",
                    _make_book("tok_l1_trap", "m_trap_1", [(0.40, 10.0), (0.99, 500.0)], []),
                    market_id="m_trap_1",
                    condition_id="0xcond_trap",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_n_a": InstrumentOrderBook.from_raw(
                    "tok_n_a",
                    _make_book("tok_n_a", "m_trap_1", [(0.45, 50.0)], []),
                    market_id="m_trap_1",
                    condition_id="0xcond_trap",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_n_b": InstrumentOrderBook.from_raw(
                    "tok_n_b",
                    _make_book("tok_n_b", "m_trap_2", [(0.46, 50.0)], []),
                    market_id="m_trap_2",
                    condition_id="0xcond_trap_2",
                    book_timestamp_sec=1794400000.0,
                ),
            }
            ver = UniversalArbVerifier(VerificationConfig(max_budget_usd=48.70, now_ts=1794400000.0))
            st_a = StateSpaceBuilder.binary_complete_set_states("tok_l1_trap", "tok_n_a")
            st_b = StateSpaceBuilder.binary_complete_set_states("tok_l1_trap", "tok_n_b")
            p_a = ver.verify_and_simulate(
                CandidateStructure(
                    candidate_id="BARE_PROOF_A",
                    family="A",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_l1_trap"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_n_a"),
                    ),
                    states=st_a,
                    expected_lockup_hours=0.2,
                ),
                typed_books,
            )
            p_b = ver.verify_and_simulate(
                CandidateStructure(
                    candidate_id="BARE_PROOF_B",
                    family="D",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_l1_trap"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_n_b"),
                    ),
                    states=st_b,
                    expected_lockup_hours=0.5,
                ),
                typed_books,
            )
            # Coerce BARE `ArbitrageProofObject`s directly (no `event_id` or `market_ids` on the proof itself)
            rec_a = coerce_to_pipeline_record(p_a, verifier=ver, books=typed_books)
            rec_b = coerce_to_pipeline_record(p_b, verifier=ver, books=typed_books)
            self.assertIn("MKT:m_trap_1", rec_a.canonical_event_keys)
            self.assertIn("COND:0xcond_trap", rec_a.canonical_event_keys)

            alloc = pipe._apply_portfolio_allocation([rec_a, rec_b], typed_books, {})
            # Must NEVER double-count the 10-share $0.40 rung via the 500-share $0.99 rung!
            tot_sh = sum(s["allocated_shares"] for s in alloc["allocated_slices"])
            self.assertLessEqual(tot_sh, 10.0 + 1e-6)

            # Two bare proofs on the SAME market `m_trap_1` must NEVER bypass `D-007` 15% ($7.305) cap!
            p_a2 = ver.verify_and_simulate(
                CandidateStructure(
                    candidate_id="BARE_PROOF_A_DUP",
                    family="I",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_l1_trap"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_n_a"),
                    ),
                    states=st_a,
                    expected_lockup_hours=0.2,
                ),
                typed_books,
            )
            rec_a1 = coerce_to_pipeline_record(p_a, verifier=ver, books=typed_books)
            rec_a2 = coerce_to_pipeline_record(p_a2, verifier=ver, books=typed_books)
            alloc_same = pipe._apply_portfolio_allocation([rec_a1, rec_a2], typed_books, {})
            self.assertLessEqual(alloc_same["total_allocated_capital_usd"], 48.70 * 0.15 + 1e-4)

    def test_08_ambiguous_hit_barrier_guard_and_negative_shadow_ev_rejection(self) -> None:
        """
        Verifies:
          1. Unsigned path-dependent numerical barrier pairs (`hit 36%` vs `hit 34%`, `#20`) are
             demoted to `CLASS_D` (`AMBIGUOUS_BARRIER_HIT_DIRECTION_REQUIRES_INITIAL_SPOT_PROOF`),
             whereas genuine terminal inequality (`above $1B` vs `above $50M`) and temporal
             monotonicity (`reach orbit by June` vs `reach orbit by December`) remain valid!
          2. Portfolio allocator rejects candidates whose post-latency risk-adjusted shadow net
             payoff is `<= 0` (`POST_LATENCY_RISK_ADJUSTED_NET_NON_POSITIVE`).
        """
        from src.polymarket_research.full_throttle_pipeline import (
            ForwardShadowValidationTracker,
            coerce_to_pipeline_record,
            has_ambiguous_numeric_barrier_direction,
        )
        from src.polymarket_research.universal_arb_verifier import (
            ActionLeg,
            ActionType,
            CandidateStructure,
            InstrumentOrderBook,
            StateSpaceBuilder,
            StateSpec,
            UniversalArbVerifier,
            VerificationConfig,
        )

        # 1. Unit checks on `has_ambiguous_numeric_barrier_direction`
        self.assertTrue(
            has_ambiguous_numeric_barrier_direction(
                [
                    "Will Trump's approval rating hit 36% in 2026?",
                    "Will Trump's approval rating hit 34% in 2026?",
                ]
            )
        )
        self.assertTrue(
            has_ambiguous_numeric_barrier_direction(
                [
                    "Will Bitcoin reach $100,000 in 2026?",
                    "Will Bitcoin reach $90,000 in 2026?",
                ]
            )
        )
        # Explicit terminal inequality ("above") -> NOT ambiguous
        self.assertFalse(
            has_ambiguous_numeric_barrier_direction(
                [
                    "StandX FDV above $1B one day after launch?",
                    "StandX FDV above $50M one day after launch?",
                ]
            )
        )
        # Non-numeric event ("reach orbit") across dates -> NOT ambiguous
        self.assertFalse(
            has_ambiguous_numeric_barrier_direction(
                [
                    "Will Starship reach orbit by June 30, 2027?",
                    "Will Starship reach orbit by December 31, 2027?",
                ]
            )
        )
        # Same numeric barrier (`36%`) across two deadlines -> temporal monotonicity, NOT ambiguous
        self.assertFalse(
            has_ambiguous_numeric_barrier_direction(
                [
                    "Will approval hit 36% by June 30, 2026?",
                    "Will approval hit 36% by December 31, 2026?",
                ]
            )
        )

        # 2. End-to-end Stage 5 & Stage 8 checks inside `FullThrottlePipeline`
        with tempfile.TemporaryDirectory() as tmp:
            pipe = FullThrottlePipeline(
                PipelineConfig(
                    output_dir=Path(tmp),
                    reconciled_nav_usd=48.70,
                    available_liquid_pusd=48.70,
                )
            )
            hit_events = [
                {
                    "id": "ev_hit_trap",
                    "slug": "approval-rating-barriers",
                    "title": "Approval Rating Hit Barriers",
                    "category": "politics",
                    "negRisk": False,
                    "markets": [
                        {
                            "id": "m_hit_36",
                            "question": "Will Trump's approval rating hit 36% in 2026?",
                            "conditionId": "0xc_hit36",
                            "outcomes": '["Yes", "No"]',
                            "clobTokenIds": '["tok_h36_y", "tok_h36_n"]',
                            "active": True,
                            "closed": False,
                            "archived": False,
                            "acceptingOrders": True,
                            "enableOrderBook": True,
                            "feesEnabled": False,
                            "feeType": "zero_fees",
                            "endDate": "2026-12-31T23:59:59Z",
                            "description": "Resolves Yes if polling average hits 36%.",
                        },
                        {
                            "id": "m_hit_34",
                            "question": "Will Trump's approval rating hit 34% in 2026?",
                            "conditionId": "0xc_hit34",
                            "outcomes": '["Yes", "No"]',
                            "clobTokenIds": '["tok_h34_y", "tok_h34_n"]',
                            "active": True,
                            "closed": False,
                            "archived": False,
                            "acceptingOrders": True,
                            "enableOrderBook": True,
                            "feesEnabled": False,
                            "feeType": "zero_fees",
                            "endDate": "2026-12-31T23:59:59Z",
                            "description": "Resolves Yes if polling average hits 34%.",
                        },
                    ],
                }
            ]
            hit_books = {
                "tok_h36_y": _make_book("tok_h36_y", "m_hit_36", [(0.80, 30.0)], [(0.75, 30.0)]),
                "tok_h36_n": _make_book("tok_h36_n", "m_hit_36", [(0.25, 30.0)], [(0.20, 30.0)]),
                "tok_h34_y": _make_book("tok_h34_y", "m_hit_34", [(0.55, 30.0)], [(0.50, 30.0)]),
                "tok_h34_n": _make_book("tok_h34_n", "m_hit_34", [(0.50, 30.0)], [(0.45, 30.0)]),
            }
            rep = pipe.run_cycle(
                OperatingCycleType.DISCOVERY_CYCLE,
                synthetic_events=hit_events,
                synthetic_raw_books=hit_books,
            )
            # Zero `CLASS_A` or `CLASS_B` false-positive arbs may survive on `m_hit_36` <-> `m_hit_34`!
            self.assertEqual(rep["opportunity_summary"]["class_counts"]["CLASS_A"], 0)
            self.assertEqual(rep["opportunity_summary"]["class_counts"]["CLASS_B"], 0)
            self.assertEqual(rep["opportunity_summary"]["mathematically_valid_proofs"], 0)
            self.assertEqual(rep["top_executable_opportunities"], [])

            # Explicit `BUG-PS-1` probe: inject a peer `CLASS_B` candidate on `m_hit_36` <-> `m_hit_34`
            # and verify Stage 5 demotes it to `CLASS_D`, clears `is_mathematically_proven_arb=False`,
            # and prevents any leak into `mathematically_valid_proofs` or `top_executable_opportunities`!
            typed_hit_books = {
                "tok_h36_n": InstrumentOrderBook.from_raw(
                    "tok_h36_n", hit_books["tok_h36_n"], market_id="m_hit_36"
                ),
                "tok_h34_y": InstrumentOrderBook.from_raw(
                    "tok_h34_y", hit_books["tok_h34_y"], market_id="m_hit_34"
                ),
            }
            ver_hit = UniversalArbVerifier(VerificationConfig(max_budget_usd=48.70, now_ts=1794400000.0))
            fake_hit_proof = ver_hit.verify_and_simulate(
                CandidateStructure(
                    candidate_id="FAKE_HIT_BARRIER_CLASS_B",
                    family="M",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_h36_n", market_id="m_hit_36"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_h34_y", market_id="m_hit_34"),
                    ),
                    states=StateSpaceBuilder.binary_complete_set_states("tok_h36_n", "tok_h34_y"),
                    expected_lockup_hours=1.0,
                ),
                typed_hit_books,
            )
            fake_hit_rec = coerce_to_pipeline_record(fake_hit_proof, verifier=ver_hit, books=typed_hit_books)
            self.assertEqual(fake_hit_rec.opportunity_class, "CLASS_B")
            self.assertTrue(fake_hit_rec.is_mathematically_proven_arb)

            orig_k2n = pipe.peer_bridge.run_microstructure_and_portfolio
            pipe.peer_bridge.run_microstructure_and_portfolio = lambda *a, **kw: ([fake_hit_rec], {})
            try:
                rep_demoted = pipe.run_cycle(
                    OperatingCycleType.FAST_CYCLE,
                    synthetic_events=hit_events,
                    synthetic_raw_books=hit_books,
                )
            finally:
                pipe.peer_bridge.run_microstructure_and_portfolio = orig_k2n
            self.assertEqual(fake_hit_rec.opportunity_class, "CLASS_D")
            self.assertFalse(fake_hit_rec.is_mathematically_proven_arb)
            self.assertFalse(fake_hit_rec.is_dormant_near_miss)
            self.assertEqual(rep_demoted["opportunity_summary"]["class_counts"]["CLASS_B"], 0)
            self.assertEqual(rep_demoted["opportunity_summary"]["mathematically_valid_proofs"], 0)
            self.assertEqual(rep_demoted["top_executable_opportunities"], [])

            # `BUG-PS-2` probe: signed `forward_validated_net_pnl_usd` never clamps decayed losses to 0.0
            tracker = ForwardShadowValidationTracker()
            tracker.completed_validations = [
                {"survived_next_snapshot": True, "post_delay_net_usd": 1.00},
                {"survived_next_snapshot": False, "post_delay_net_usd": -0.40},
            ]
            ps = tracker.persistence_summary(current_cycle=2)
            self.assertAlmostEqual(ps["forward_validated_net_pnl_usd"], 0.60, places=6)

            # 3. Portfolio allocator rejects candidate with `executable_l2_net_usd > 0`
            #    when `forward_shadow_risk_adjusted_usd <= 0`!
            typed_b = {
                "t1": InstrumentOrderBook.from_raw("t1", _make_book("t1", "m1", [(0.45, 20.0)], []), market_id="m1"),
                "t2": InstrumentOrderBook.from_raw("t2", _make_book("t2", "m2", [(0.49, 20.0)], []), market_id="m2"),
            }
            ver = UniversalArbVerifier(VerificationConfig(max_budget_usd=48.70, now_ts=1794400000.0))
            p_thin = ver.verify_and_simulate(
                CandidateStructure(
                    candidate_id="THIN_NEGATIVE_RA_ARB",
                    family="M",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="t1"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="t2"),
                    ),
                    states=StateSpaceBuilder.binary_complete_set_states("t1", "t2"),
                    expected_lockup_hours=1.0,
                ),
                typed_b,
            )
            rec_thin = coerce_to_pipeline_record(p_thin, verifier=ver, books=typed_b)
            rec_thin.forward_shadow_risk_adjusted_usd = -0.05
            alloc_thin = pipe._apply_portfolio_allocation([rec_thin], typed_b, {})
            self.assertEqual(alloc_thin["allocated_positions_count"], 0)
            self.assertEqual(rec_thin.portfolio_rejection_reason, "POST_LATENCY_RISK_ADJUSTED_NET_NON_POSITIVE")

    def test_09_harvester_candidate_bridge_schema_dedupe_d001_d007_and_velocity(self) -> None:
        """
        Verifies `HarvesterCandidateBridge`:
          1. Emits valid `d1_live_box_candidates.jsonl` rows for `CLASS_A` (`SINGLE_LEG_LOCK`) and
             `<= 2`-leg `CLASS_B` (`LADDER_MONO` / `COMPLETE_SET`) with `rule_verified=True`,
             `min_state_net_payoff_usd > 0`, `leg_count <= 2`.
          2. Enforces `D-007` `<= 15%` reconciled floor NAV (`$48.70 * 0.15 = $7.305`), NEVER sizing
             off `$99.21` `total_account_equity`!
          3. Deduplicates repeated candidates within `45s` TTL (`DEDUPE_TTL_ACTIVE`) and re-emits
             after TTL expiry.
          4. Blocks `D-001` `KMIA` (`6707503`), `>= 3` sequential CLOB legs below `$500` NAV,
             `CLASS_C` / `CLASS_D`, `is_maker=True`, and `< 7.5 bps/hr` non-mergeable locks.
        """
        from src.polymarket_research.full_throttle_pipeline import (
            HarvesterCandidateBridge,
            coerce_to_pipeline_record,
        )
        from src.polymarket_research.universal_arb_verifier import (
            ActionLeg,
            ActionType,
            CandidateStructure,
            InstrumentOrderBook,
            InventoryHolding,
            StateSpaceBuilder,
            StateSpec,
            UniversalArbVerifier,
            VerificationConfig,
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            cand_jsonl = tmp_dir / "d1_live_box_candidates.jsonl"
            dedupe_json = tmp_dir / "bridge_dedupe.json"
            fake_harvester_state = tmp_dir / "live_harvester_state.json"
            # Write harvester state with `$99.21` book equity vs `$48.70` liquid floor cash
            fake_harvester_state.write_text(
                json.dumps(
                    {
                        "live_bankroll": 48.695132,
                        "reconciled_nav_usd": 48.695132,
                        "total_account_equity": 99.205132,
                    }
                ),
                encoding="utf-8",
            )
            bridge = HarvesterCandidateBridge(
                candidates_jsonl_path=cand_jsonl,
                dedupe_state_path=dedupe_json,
                dedupe_ttl_sec=45.0,
                min_velocity_bps_per_hr=7.5,
                live_harvester_state_path=fake_harvester_state,
            )
            self.assertAlmostEqual(bridge.resolve_reconciled_floor_nav_usd(99.21), 48.695132, places=5)

            typed_books = {
                "tok_e1_y": InstrumentOrderBook.from_raw(
                    "tok_e1_y",
                    _make_book("tok_e1_y", "m_cal_jun", [(0.42, 40.0)], [(0.40, 40.0)]),
                    market_id="m_cal_jun",
                    condition_id="0xcond_jun",
                    outcome_label="YES",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_e2_n": InstrumentOrderBook.from_raw(
                    "tok_e2_n",
                    _make_book("tok_e2_n", "m_cal_dec", [(0.48, 40.0)], [(0.46, 40.0)]),
                    market_id="m_cal_dec",
                    condition_id="0xcond_dec",
                    outcome_label="NO",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_sll_n": InstrumentOrderBook.from_raw(
                    "tok_sll_n",
                    _make_book("tok_sll_n", "m_sll_1", [(0.44, 30.0)], [(0.42, 30.0)]),
                    market_id="m_sll_1",
                    condition_id="0xcond_sll",
                    outcome_label="NO",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_kmia_y": InstrumentOrderBook.from_raw(
                    "tok_kmia_y",
                    _make_book("tok_kmia_y", "6707503", [(0.40, 20.0)], [(0.38, 20.0)]),
                    market_id="6707503",
                    condition_id="0xcond_kmia",
                    outcome_label="YES",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_kmia_n": InstrumentOrderBook.from_raw(
                    "tok_kmia_n",
                    _make_book("tok_kmia_n", "6707503", [(0.40, 20.0)], [(0.38, 20.0)]),
                    market_id="6707503",
                    condition_id="0xcond_kmia",
                    outcome_label="NO",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_nr_1": InstrumentOrderBook.from_raw(
                    "tok_nr_1",
                    _make_book("tok_nr_1", "m_nr_1", [(0.28, 30.0)], [(0.26, 30.0)]),
                    market_id="m_nr_1",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_nr_2": InstrumentOrderBook.from_raw(
                    "tok_nr_2",
                    _make_book("tok_nr_2", "m_nr_2", [(0.28, 30.0)], [(0.26, 30.0)]),
                    market_id="m_nr_2",
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_nr_3": InstrumentOrderBook.from_raw(
                    "tok_nr_3",
                    _make_book("tok_nr_3", "m_nr_3", [(0.28, 30.0)], [(0.26, 30.0)]),
                    market_id="m_nr_3",
                    book_timestamp_sec=1794400000.0,
                ),
            }
            holdings = {
                "tok_sll_y": InventoryHolding(
                    instrument_id="tok_sll_y",
                    shares=10.0,
                    market_id="m_sll_1",
                    condition_id="0xcond_sll",
                    cost_basis_per_share=0.45,
                    mark_bid_per_share=0.44,
                )
            }
            ver = UniversalArbVerifier(
                VerificationConfig(max_budget_usd=48.695132, reconciled_nav_usd=48.695132, now_ts=1794400000.0)
            )

            # 1. Valid 2-leg `CLASS_B` Calendar Dominance (`0.42 + 0.48 = 0.90 < 1.00`, `2.0h` lockup -> `~555 bps/hr`)
            dom_states = (
                StateSpec("s_both_true", {"tok_e2_n": 1.0}),
                StateSpec("s_only_later_true", {"tok_e1_y": 1.0, "tok_e2_n": 1.0}),
                StateSpec("s_neither_true", {"tok_e1_y": 1.0}),
            )
            rec_cal = coerce_to_pipeline_record(
                CandidateStructure(
                    candidate_id="BRIDGE_CAL1_VALID",
                    family="E",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_e1_y", market_id="m_cal_jun", label="NO"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_e2_n", market_id="m_cal_dec", label="YES"),
                    ),
                    states=dom_states,
                    expected_lockup_hours=2.0,
                    worst_case_lockup_hours=2.0,
                    rule_verified=True,
                ),
                verifier=ver,
                books=typed_books,
            )
            # 2. Valid 1-leg `CLASS_A` Inventory-Backed Single-Leg Lock (`SINGLE_LEG_LOCK`)
            rec_sll = coerce_to_pipeline_record(
                CandidateStructure(
                    candidate_id="BRIDGE_SLL_CLASS_A",
                    family="J",
                    legs=(
                        ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id="tok_sll_y", market_id="m_sll_1", label="YES"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_sll_n", market_id="m_sll_1", label="NO"),
                        ActionLeg(action_type=ActionType.CTF_MERGE, related_instrument_ids=("tok_sll_y", "tok_sll_n"), market_id="m_sll_1"),
                    ),
                    states=StateSpaceBuilder.binary_complete_set_states("tok_sll_y", "tok_sll_n"),
                    expected_lockup_hours=0.05,
                    worst_case_lockup_hours=0.05,
                    rule_verified=True,
                ),
                verifier=ver,
                books=typed_books,
                holdings=holdings,
            )
            # 3. Blocked `D-001` `KMIA` (`6707503`)
            rec_kmia = coerce_to_pipeline_record(
                CandidateStructure(
                    candidate_id="BRIDGE_KMIA_BLOCKED",
                    family="A",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_kmia_y", market_id="6707503"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_kmia_n", market_id="6707503"),
                    ),
                    states=StateSpaceBuilder.binary_complete_set_states("tok_kmia_y", "tok_kmia_n"),
                    expected_lockup_hours=0.1,
                ),
                verifier=ver,
                books=typed_books,
            )
            # 4. Blocked `D-007` 3-leg sequential bundle below `$500` NAV
            rec_3leg = coerce_to_pipeline_record(
                CandidateStructure(
                    candidate_id="BRIDGE_3LEG_QUARANTINED",
                    family="B",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_nr_1", market_id="m_nr_1"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_nr_2", market_id="m_nr_2"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_nr_3", market_id="m_nr_3"),
                    ),
                    states=(
                        StateSpec("s1", {"tok_nr_1": 1.0}),
                        StateSpec("s2", {"tok_nr_2": 1.0}),
                        StateSpec("s3", {"tok_nr_3": 1.0}),
                    ),
                    expected_lockup_hours=1.0,
                ),
                verifier=ver,
                books=typed_books,
            )
            # 5. Blocked slow `< 7.5 bps/hr` non-mergeable lock (`expected_lockup_hours = 500h` -> `~2.2 bps/hr`)
            rec_slow = coerce_to_pipeline_record(
                CandidateStructure(
                    candidate_id="BRIDGE_SLOW_LOCKUP",
                    family="E",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_e1_y", market_id="m_cal_jun", label="NO"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_e2_n", market_id="m_cal_dec", label="YES"),
                    ),
                    states=dom_states,
                    expected_lockup_hours=500.0,
                    worst_case_lockup_hours=500.0,
                    rule_verified=True,
                ),
                verifier=ver,
                books=typed_books,
            )

            res1 = bridge.emit_verified_candidates(
                [rec_cal, rec_sll, rec_kmia, rec_3leg, rec_slow],
                typed_books,
                holdings=holdings,
                market_meta_by_id={
                    "m_cal_jun": {"conditionId": "0xcond_jun", "endDate": "2026-11-12T00:00:00Z"},
                    "m_cal_dec": {"conditionId": "0xcond_dec", "endDate": "2026-11-12T02:00:00Z"},
                    "m_sll_1": {"conditionId": "0xcond_sll", "endDate": "2026-11-12T00:00:00Z"},
                },
                fallback_reconciled_nav_usd=48.695132,
                now_ts=1794400000.0,
            )
            self.assertEqual(res1["candidates_emitted_this_cycle"], 2)
            self.assertGreaterEqual(res1["skipped_by_reason"].get("D001_KMIA_QUARANTINED", 0), 1)
            self.assertGreaterEqual(res1["skipped_by_reason"].get("D007_MULTILEG_3PLUS_QUARANTINED", 0), 1)
            self.assertGreaterEqual(res1["skipped_by_reason"].get("BELOW_VELOCITY_HURDLE_7_5_BPS_HR", 0), 1)

            rows = [json.loads(ln) for ln in cand_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual(len(rows), 2)
            by_bt = {r["box_type"]: r for r in rows}
            self.assertIn("LADDER_MONO", by_bt)
            self.assertIn("SINGLE_LEG_LOCK", by_bt)

            cal_row = by_bt["LADDER_MONO"]
            self.assertEqual(cal_row["sleeve_source"], "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX")
            self.assertTrue(cal_row["rule_verified"])
            self.assertEqual(cal_row["leg_count"], 2)
            self.assertGreater(cal_row["min_state_net_payoff_usd"], 0.0)
            # `unit_cap = 0.90`, `15%` of `$48.695132 = $7.30427` -> `floor(7.30427 / 0.90) = 8` shares (`$7.20 <= $7.305`! Never `16` shares from `$99.21`!)
            self.assertEqual(cal_row["shares"], 8)
            self.assertLessEqual(cal_row["shares"] * cal_row["box_cost_net"], 48.695132 * 0.15 + 1e-4)

            # Second emit 10s later (`< 45s` TTL) must suppress both via `DEDUPE_TTL_ACTIVE`
            res2 = bridge.emit_verified_candidates(
                [rec_cal, rec_sll],
                typed_books,
                holdings=holdings,
                fallback_reconciled_nav_usd=48.695132,
                now_ts=1794400010.0,
            )
            self.assertEqual(res2["candidates_emitted_this_cycle"], 0)
            self.assertEqual(res2["skipped_by_reason"].get("DEDUPE_TTL_ACTIVE"), 2)

            # Third emit 50s later (`> 45s` TTL) re-emits cleanly
            res3 = bridge.emit_verified_candidates(
                [rec_cal],
                typed_books,
                holdings=holdings,
                fallback_reconciled_nav_usd=48.695132,
                now_ts=1794400055.0,
            )
            self.assertEqual(res3["candidates_emitted_this_cycle"], 1)

    def test_10_hedged_maker_shadow_quoter_forward_fill_adverse_jump_and_cli_cycles(self) -> None:
        """
        Verifies `HedgedMakerShadowQuoter`:
          1. Posts passive `0 bps` `postOnly` quotes (`L1A`/`L1B`) on Cycle `t`.
          2. Records hedged lock + `20%` dynamic-fee maker rebate telemetry on Cycle `t+1` when
             `best_ask <= quote_bid_px` and the hedge leg ask stays valid, while keeping
             `shadow_realized_wallet_cash_usd == 0.0` (`strictly_segregated_from_locked_cash == True`).
          3. Records signed adverse-selection unwind bleed when the hedge leg jumps above `1 - quote_bid_px`.
          4. Persists/restores via `checkpoint_state.json` and supports CLI `--cycles 2 --emit-harvester-candidates`.
        """
        from scripts.run_dominus_full_throttle import main as cli_main
        from src.polymarket_research.full_throttle_pipeline import (
            HedgedMakerShadowQuoter,
            coerce_to_pipeline_record,
        )
        from src.polymarket_research.universal_arb_verifier import (
            ActionLeg,
            ActionType,
            CandidateStructure,
            InstrumentOrderBook,
            StateSpaceBuilder,
            StateSpec,
            UniversalArbVerifier,
            VerificationConfig,
        )

        quoter = HedgedMakerShadowQuoter()
        # Cycle 1 books: dynamic crypto fee market (`250 bps`, `exp=2` -> `20%` maker rebate share)
        # `tok_m_y`: bid=0.47, ask=0.51; `tok_m_n`: bid=0.47, ask=0.50 (`ask_Y + ask_N = 1.01`, near-miss)
        books_t0 = {
            "tok_m_y": InstrumentOrderBook.from_raw(
                "tok_m_y",
                _make_book("tok_m_y", "m_dyn_1", [(0.51, 25.0)], [(0.47, 5.0)]),
                market_id="m_dyn_1",
                fee_rate_bps=250.0,
                fee_exponent=2.0,
                tick_size=0.01,
                book_timestamp_sec=1794400000.0,
            ),
            "tok_m_n": InstrumentOrderBook.from_raw(
                "tok_m_n",
                _make_book("tok_m_n", "m_dyn_1", [(0.50, 40.0)], [(0.47, 15.0)]),
                market_id="m_dyn_1",
                fee_rate_bps=250.0,
                fee_exponent=2.0,
                tick_size=0.01,
                book_timestamp_sec=1794400000.0,
            ),
        }
        ver = UniversalArbVerifier(VerificationConfig(max_budget_usd=48.70, now_ts=1794400000.0))
        near_rec = coerce_to_pipeline_record(
            CandidateStructure(
                candidate_id="NEAR_MKR_DYN_1",
                family="A",
                legs=(
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_m_y", market_id="m_dyn_1"),
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_m_n", market_id="m_dyn_1"),
                ),
                states=StateSpaceBuilder.binary_complete_set_states("tok_m_y", "tok_m_n"),
                expected_lockup_hours=0.5,
                rule_verified=True,
            ),
            verifier=ver,
            books=books_t0,
        )
        posted = quoter.ingest_cycle_candidates([near_rec], books_t0, cycle_index=1, now_ts=1794400000.0)
        self.assertEqual(posted, 1)
        self.assertEqual(len(quoter.resting_quotes), 1)
        q_obj = next(iter(quoter.resting_quotes.values()))
        self.assertAlmostEqual(q_obj.rebate_share_frac, 0.20, places=4)
        self.assertGreater(q_obj.est_maker_rebate_ps, 0.0)

        # Checkpoint round-trip
        ckpt = quoter.to_checkpoint_dict()
        quoter2 = HedgedMakerShadowQuoter()
        quoter2.load_checkpoint_dict(ckpt)
        self.assertEqual(len(quoter2.resting_quotes), 1)

        # Cycle 2A (Hedged Fill): `maker_token_id` ask trades through `quote_bid_px`, while `hedge_token_id` stays cheap!
        books_t1_fill = dict(books_t0)
        books_t1_fill[q_obj.maker_token_id] = InstrumentOrderBook.from_raw(
            q_obj.maker_token_id,
            _make_book(
                q_obj.maker_token_id,
                "m_dyn_1",
                [(max(0.02, round(q_obj.quote_bid_px - 0.01, 2)), 20.0)],
                [(max(0.01, round(q_obj.quote_bid_px - 0.02, 2)), 20.0)],
            ),
            market_id="m_dyn_1",
            fee_rate_bps=250.0,
            fee_exponent=2.0,
            tick_size=0.01,
            book_timestamp_sec=1794400015.0,
        )
        val_fill = quoter2.validate_resting_quotes(books_t1_fill, cycle_index=2, now_ts=1794400015.0)
        self.assertEqual(val_fill["fills_this_cycle"], 1)
        self.assertEqual(val_fill["events"][0]["outcome"], "HEDGED_MAKER_LOCK")
        m_sum = quoter2.summary_metrics()
        self.assertEqual(m_sum["filled_hedged_locks_count"], 1)
        self.assertGreater(m_sum["locked_spread_shadow_pnl_ex_rebate_usd"], 0.0)
        self.assertGreater(m_sum["estimated_maker_rebate_15_to_25pct_usd"], 0.0)
        self.assertTrue(m_sum["strictly_segregated_from_locked_cash"])

        # Cycle 2B (Adverse Jump): `maker_token_id` fills ONLY because `hedge_token_id` jumped to `$0.85`!
        books_t1_adv = dict(books_t1_fill)
        books_t1_adv[q_obj.hedge_token_id] = InstrumentOrderBook.from_raw(
            q_obj.hedge_token_id,
            _make_book(q_obj.hedge_token_id, "m_dyn_1", [(0.85, 20.0)], [(0.83, 20.0)]),
            market_id="m_dyn_1",
            fee_rate_bps=250.0,
            fee_exponent=2.0,
            tick_size=0.01,
            book_timestamp_sec=1794400015.0,
        )
        val_adv = quoter.validate_resting_quotes(books_t1_adv, cycle_index=2, now_ts=1794400015.0)
        self.assertEqual(val_adv["adverse_this_cycle"], 1)
        self.assertEqual(val_adv["events"][0]["outcome"], "ADVERSE_JUMP_UNWOUND")
        self.assertEqual(quoter.adverse_selected_fills_count, 1)
        self.assertGreater(quoter.adverse_unwind_bleed_usd, 0.0)

        # Verify CLI `--cycles 2 --emit-harvester-candidates` with mocked network client
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            out_dir = tmp_p / "pipe_out"
            md_out = tmp_p / "DASH.md"
            cand_out = tmp_p / "d1_cands.jsonl"
            syn_ev, syn_bks, _ = _build_synthetic_universe_and_books_seq()
            from unittest.mock import patch

            with (
                patch(
                    "src.polymarket_research.full_throttle_pipeline.PublicPolymarketScannerClient.sweep_gamma_events_keyset",
                    return_value=(syn_ev, {"pages_fetched": 1, "events_fetched": len(syn_ev), "sweep_wall_time_sec": 0.01}),
                ),
                patch(
                    "src.polymarket_research.full_throttle_pipeline.PublicPolymarketScannerClient.fetch_clob_books_batched",
                    side_effect=[(syn_bks[0], {"book_poll_wall_sec": 0.01}), (syn_bks[1], {"book_poll_wall_sec": 0.01})],
                ),
            ):
                rc = cli_main(
                    [
                        "--cycles",
                        "2",
                        "--inter-cycle-pause",
                        "0.0",
                        "--emit-harvester-candidates",
                        "--harvester-candidates-path",
                        str(cand_out),
                        "--output-dir",
                        str(out_dir),
                        "--dashboard-md",
                        str(md_out),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertTrue(cand_out.exists())
            self.assertTrue(md_out.exists())
            dash_txt = md_out.read_text(encoding="utf-8")
            self.assertIn("HedgedMakerShadowQuoter", dash_txt)
            self.assertIn("HarvesterCandidateBridge", dash_txt)

    def test_11_wave3_generalized_structural_retention_and_priority_book_polling(self) -> None:
        """
        Verifies Wave 3 Track 5 coverage & scheduler upgrades:
          1. `sweep_gamma_events_keyset` retains `Family D` (logical/political hierarchies),
             `Family H` (weather station ICAO & `°F` brackets, while quarantining `D-001` `KMIA`),
             `Family G` (`sportsMarketType` multi-line slates & tournament advancement),
             `Family I` (cross-event duplicate title stems across separate pages), and
             `Family K` (`umaResolutionStatus == "proposed"` quiet `BOND1` carry) over generic filler.
          2. `_collect_graph_cross_market_edge_tokens` & `select_tokens_for_cycle` poll 100% of
             BOTH `OFFICIAL_CONTRACTUAL` and `VERIFIED_MATHEMATICAL` graph edges, non-disputed
             `umaResolutionStatus == "proposed"` tokens, and `<=50 bps` dormant near-arbs FIRST.
        """
        from unittest.mock import MagicMock, patch
        from src.polymarket_research.full_throttle_pipeline import (
            ExecutionMode,
            ExecutionModeGateConfig,
            FullThrottlePipeline,
            OperatingCycleType,
            PipelineConfig,
            PublicPolymarketScannerClient,
        )
        from src.polymarket_research.market_proposition_graph import (
            EdgeType,
            PropositionEdge,
            RelationKind,
        )
        from src.polymarket_research.universal_arb_verifier import (
            ActionLeg,
            ActionType,
            CandidateStructure,
            InstrumentOrderBook,
            StateSpaceBuilder,
            StateSpec,
            UniversalArbVerifier,
            VerificationConfig,
        )

        def _mk_ev(eid: str, title: str, mkts: list, **extra):
            return {
                "id": eid,
                "slug": title.lower().replace(" ", "-"),
                "title": title,
                "active": True,
                "closed": False,
                "markets": mkts,
                **extra,
            }

        def _mk_m(mid: str, q: str, t0: str, t1: str, liq: float = 20.0, **extra):
            return {
                "id": mid,
                "question": q,
                "conditionId": f"0xcond_{mid}",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.50", "0.50"]',
                "clobTokenIds": json.dumps([t0, t1]),
                "active": True,
                "closed": False,
                "archived": False,
                "enableOrderBook": True,
                "feesEnabled": extra.pop("feesEnabled", True),
                "liquidityClob": liq,
                "volume24hr": liq,
                **extra,
            }

        # Build 2 Gamma pages with structural targets + 30 generic filler events that exceed tight cap
        page1_events = [
            _mk_ev(
                "ev_dup_1",
                "Will Gold close above 3200 in November 2026?",
                [_mk_m("m_dup_1", "Will Gold close above 3200 in November 2026?", "tok_dup1_y", "tok_dup1_n", liq=12.0)],
            ),
            _mk_ev(
                "ev_fam_d_1",
                "2026 Balance of Power: Trifecta or Divided Government?",
                [_mk_m("m_d1", "Democratic Sweep / Trifecta?", "tok_d1_y", "tok_d1_n", liq=8.0)],
            ),
            _mk_ev(
                "ev_fam_h_1",
                "Highest temperature in Chicago (KORD) on Nov 12?",
                [
                    _mk_m("m_h1", "45°F to 49°F", "tok_h1_y", "tok_h1_n", liq=5.0, groupItemTitle="45°F-49°F"),
                    _mk_m("m_h2", "50°F or higher", "tok_h2_y", "tok_h2_n", liq=5.0, groupItemTitle=">=50°F"),
                ],
                negRisk=True,
            ),
            _mk_ev(
                "ev_kmia_frozen",
                "Highest temperature in Miami (KMIA) on Nov 7?",
                [_mk_m("6707503", "KMIA Nov 7", "tok_kmia_y", "tok_kmia_n", liq=0.0, umaResolutionStatus="disputed")],
            ),
        ]
        for idx in range(25):
            page1_events.append(
                _mk_ev(
                    f"ev_noise_{idx}",
                    f"Generic celebrity gossip question number {idx}?",
                    [_mk_m(f"m_noise_{idx}", f"Noise {idx}?", f"tok_nz_{idx}_y", f"tok_nz_{idx}_n", liq=250.0)],
                )
            )

        page2_events = [
            _mk_ev(
                "ev_dup_2",
                "Will Gold close above 3200 in November 2026?",
                [_mk_m("m_dup_2", "Will Gold close above 3200 in November 2026?", "tok_dup2_y", "tok_dup2_n", liq=15.0)],
            ),
            _mk_ev(
                "ev_uma_bond1",
                "Daily Esports Match Settling Soon",
                [
                    _mk_m(
                        "m_uma_prop",
                        "Team Alpha wins Map 1?",
                        "tok_uma_y",
                        "tok_uma_n",
                        liq=0.0,
                        feesEnabled=False,
                        umaResolutionStatus="proposed",
                        customLiveness=7200,
                    )
                ],
            ),
            _mk_ev(
                "ev_sports_g",
                "Arsenal vs. Chelsea",
                [
                    _mk_m("m_sp_ml", "Arsenal Moneyline", "tok_sp1_y", "tok_sp1_n", liq=200.0, sportsMarketType="moneyline"),
                    _mk_m("m_sp_sp", "Arsenal -1.5 Spread", "tok_sp2_y", "tok_sp2_n", liq=200.0, sportsMarketType="spreads", line=-1.5),
                    _mk_m("m_sp_ou", "Over/Under 2.5 Goals", "tok_sp3_y", "tok_sp3_n", liq=200.0, sportsMarketType="totals", line=2.5),
                ],
            ),
        ]

        client = PublicPolymarketScannerClient()
        fake_resp = MagicMock()
        fake_resp.status = 200
        with (
            patch("http.client.HTTPSConnection") as mock_conn_cls,
            patch.object(
                client,
                "_read_gzip_json",
                side_effect=[
                    {"events": page1_events, "next_cursor": "cur_p2"},
                    {"events": page2_events, "next_cursor": None},
                ],
            ),
        ):
            mock_conn_cls.return_value.getresponse.return_value = fake_resp
            retained, meta = client.sweep_gamma_events_keyset(
                page_limit=35,
                max_pages=5,
                compact_fields=True,
                max_retained_active_markets=12,
            )

        retained_ids = {e["id"] for e in retained}
        self.assertIn("ev_fam_d_1", retained_ids)
        self.assertIn("ev_fam_h_1", retained_ids)
        self.assertIn("ev_dup_1", retained_ids)
        self.assertIn("ev_dup_2", retained_ids)
        self.assertIn("ev_uma_bond1", retained_ids)
        self.assertIn("ev_sports_g", retained_ids)
        # Verify `sportsMarketType` and `line` were preserved in compact market dicts
        sp_ev = next(e for e in retained if e["id"] == "ev_sports_g")
        self.assertEqual(sp_ev["markets"][1].get("sportsMarketType"), "spreads")
        self.assertEqual(sp_ev["markets"][1].get("line"), -1.5)
        self.assertGreaterEqual(meta["full_universe_census"]["skip_reasons"].get("UMA_DISPUTED_QUARANTINED", 0), 1)

        # Verify `OFFICIAL_CONTRACTUAL` + `VERIFIED_MATHEMATICAL` graph edges & `<=50 bps` dormant priority polling
        with tempfile.TemporaryDirectory() as tmp:
            cfg = PipelineConfig(
                output_dir=Path(tmp) / "p_out",
                mode_gate=ExecutionModeGateConfig(mode=ExecutionMode.MODE_2_SHADOW, jurisdiction_code="CA-ON"),
                max_book_tokens_discovery=24,
                cold_layer_rotation_tokens=4,
            )
            pipe = FullThrottlePipeline(config=cfg)
            pipe.graph.ingest_events_and_markets(events=retained)
            # Inject an explicit `OFFICIAL_CONTRACTUAL` cross-market edge between `m_dup_1` and `m_dup_2`
            pipe.graph.edges["edge_off_dup"] = PropositionEdge(
                edge_id="edge_off_dup",
                edge_type=EdgeType.OFFICIAL_CONTRACTUAL,
                relation_kind=RelationKind.EQUIVALENT,
                source_market_id="m_dup_1",
                target_market_id="m_dup_2",
                source_token_id="tok_dup1_y",
                target_token_id="tok_dup2_n",
                notes="Exact identical oracle rule",
            )
            edge_toks = pipe._collect_graph_cross_market_edge_tokens(max_tokens=100)
            for req_t in ("tok_dup1_y", "tok_dup1_n", "tok_dup2_y", "tok_dup2_n"):
                self.assertIn(req_t, edge_toks)

            # Seed a `<= 50 bps` dormant near-arb (`30 bps` gap) vs a `250 bps` wider dormant entry
            ver = UniversalArbVerifier(VerificationConfig(max_budget_usd=48.70, now_ts=1794400000.0))
            bks_d = {
                "tok_d1_y": InstrumentOrderBook.from_raw(
                    "tok_d1_y",
                    _make_book("tok_d1_y", "m_d1", [(0.502, 20.0)], [(0.49, 20.0)]),
                    market_id="m_d1",
                    fee_rate_bps=0.0,
                    tick_size=0.001,
                    book_timestamp_sec=1794400000.0,
                ),
                "tok_d1_n": InstrumentOrderBook.from_raw(
                    "tok_d1_n",
                    _make_book("tok_d1_n", "m_d1", [(0.501, 20.0)], [(0.49, 20.0)]),
                    market_id="m_d1",
                    fee_rate_bps=0.0,
                    tick_size=0.001,
                    book_timestamp_sec=1794400000.0,
                ),
            }
            from src.polymarket_research.full_throttle_pipeline import coerce_to_pipeline_record

            rec_30bps = coerce_to_pipeline_record(
                CandidateStructure(
                    candidate_id="DORM_30BPS",
                    family="A",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_d1_y", market_id="m_d1"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_d1_n", market_id="m_d1"),
                    ),
                    states=StateSpaceBuilder.binary_complete_set_states("tok_d1_y", "tok_d1_n"),
                    rule_verified=True,
                ),
                verifier=ver,
                books=bks_d,
            )
            pipe.dormant_store.update_from_pipeline_records([rec_30bps], bks_d, now_ts=1794400000.0)
            self.assertEqual(
                pipe.dormant_store.get_watch_instrument_ids(max_tokens=10, max_gap_bps=50.0),
                ["tok_d1_y", "tok_d1_n"],
            )

            selected, plan = pipe.select_tokens_for_cycle(
                retained, cycle_type=OperatingCycleType.DISCOVERY_CYCLE, now_ts=1794400000.0
            )
            for must_poll in ("tok_dup1_y", "tok_dup1_n", "tok_dup2_y", "tok_dup2_n", "tok_uma_y", "tok_uma_n", "tok_d1_y", "tok_d1_n"):
                self.assertIn(must_poll, selected)
            self.assertGreaterEqual(plan["uma_proposed_tokens"], 2)
            self.assertGreaterEqual(plan["dormant_50bps_tokens"], 2)

    def test_12_wave3_harvester_bridge_jit_reverify_opp_tokens_and_uma_maker_lock(self) -> None:
        """
        Verifies Wave 3 `HarvesterCandidateBridge` real-trading fixes (`#63` + `#64`):
          1. Populates `20+`-digit `leg_a_opp_token_id` & `leg_b_opp_token_id` + 4-token `ws_books`
             on cross-market 2-leg boxes (`LADDER_MONO`, `BARRIER_MONO`, etc.).
          2. Re-polls fresh `/books` via `jit_book_fetcher` right before appending, stamping fresh
             `ts_unix == ws_books_ts` when the arb survives, and rejecting with
             `JIT_BOOK_REVERIFY_EDGE_DECAYED` when the ask moves above breakeven!
          3. Rejects corrupted complement books with `JIT_ANTI_BOX_COMPLEMENT_VETO`.
          4. Emits verified passive `0 bps` `SINGLE_LEG_MAKER_LOCK` (`BOND1_UMA_RESOLUTION_CARRY`)
             on non-disputed `0%`-fee `umaResolutionStatus == "proposed"` (`<=2h`) markets while
             strictly quarantining `D-001` `KMIA` (`6707503`, `6707502`).
        """
        from src.polymarket_research.full_throttle_pipeline import (
            HarvesterCandidateBridge,
            coerce_to_pipeline_record,
        )
        from src.polymarket_research.universal_arb_verifier import (
            ActionLeg,
            ActionType,
            CandidateStructure,
            InstrumentOrderBook,
            StateSpaceBuilder,
            StateSpec,
            UniversalArbVerifier,
            VerificationConfig,
        )

        t_jun_y = "100000000000000000001"
        t_jun_n = "100000000000000000002"
        t_dec_y = "200000000000000000001"
        t_dec_n = "200000000000000000002"
        t_uma_y = "300000000000000000001"
        t_uma_n = "300000000000000000002"
        t_subj_y = "400000000000000000001"
        t_subj_n = "400000000000000000002"

        raw_initial = {
            t_jun_y: _make_book(t_jun_y, "m_jun", [(0.55, 30.0)], [(0.52, 30.0)]),
            t_jun_n: _make_book(t_jun_n, "m_jun", [(0.46, 30.0)], [(0.43, 30.0)]),
            t_dec_y: _make_book(t_dec_y, "m_dec", [(0.44, 30.0)], [(0.41, 30.0)]),
            t_dec_n: _make_book(t_dec_n, "m_dec", [(0.59, 30.0)], [(0.55, 30.0)]),
            t_uma_y: _make_book(t_uma_y, "m_uma_ok", [(0.997, 40.0)], [(0.990, 25.0)]),
            t_uma_n: _make_book(t_uma_n, "m_uma_ok", [(0.010, 40.0)], [(0.002, 25.0)]),
            t_subj_y: _make_book(t_subj_y, "m_uma_subj", [(0.997, 40.0)], [(0.990, 25.0)]),
            t_subj_n: _make_book(t_subj_n, "m_uma_subj", [(0.010, 40.0)], [(0.002, 25.0)]),
        }
        books = {
            tid: InstrumentOrderBook.from_raw(
                tid,
                rb,
                market_id=rb["market"],
                condition_id=f"0x_{rb['market']}",
                outcome_label=("YES" if tid.endswith("1") else "NO"),
                fee_rate_bps=0.0,
                tick_size=(0.001 if rb["market"] in ("m_uma_ok", "m_uma_subj") else 0.01),
                book_timestamp_sec=1794400000.0,
            )
            for tid, rb in raw_initial.items()
        }

        ver = UniversalArbVerifier(
            VerificationConfig(max_budget_usd=48.695132, reconciled_nav_usd=48.695132, now_ts=1794400000.0)
        )
        # Calendar survival box: buy `t_jun_n` (`$0.46`) + buy `t_dec_y` (`$0.44` after shift) -> let's make `t_dec_y` ask `$0.44`!
        raw_initial[t_dec_y] = _make_book(t_dec_y, "m_dec", [(0.44, 30.0)], [(0.41, 30.0)])
        raw_initial[t_dec_n] = _make_book(t_dec_n, "m_dec", [(0.59, 30.0)], [(0.55, 30.0)])
        books[t_dec_y] = InstrumentOrderBook.from_raw(
            t_dec_y, raw_initial[t_dec_y], market_id="m_dec", condition_id="0x_m_dec", outcome_label="YES", fee_rate_bps=0.0, book_timestamp_sec=1794400000.0
        )
        books[t_dec_n] = InstrumentOrderBook.from_raw(
            t_dec_n, raw_initial[t_dec_n], market_id="m_dec", condition_id="0x_m_dec", outcome_label="NO", fee_rate_bps=0.0, book_timestamp_sec=1794400000.0
        )

        # States for `Jun -> Dec` implication (`(Jun=1, Dec=0)` impossible): buying `t_jun_n` + `t_dec_y` pays `>= $1.00` in all 3 valid states!
        states_cal = (
            StateSpec("s_both_true", {t_dec_y: 1.0}),
            StateSpec("s_only_dec_true", {t_jun_n: 1.0, t_dec_y: 1.0}),
            StateSpec("s_neither_true", {t_jun_n: 1.0}),
        )
        rec_cal = coerce_to_pipeline_record(
            CandidateStructure(
                candidate_id="CAL_JIT_LIVE_1",
                family="E",
                legs=(
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=t_jun_n, market_id="m_jun", label="NO"),
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=t_dec_y, market_id="m_dec", label="YES"),
                ),
                states=states_cal,
                expected_lockup_hours=1.0,
                rule_verified=True,
            ),
            verifier=ver,
            books=books,
        )
        self.assertIn(rec_cal.opportunity_class, ("CLASS_A", "CLASS_B"))

        mkt_meta = {
            "m_jun": {"conditionId": "0x_m_jun", "clobTokenIds": [t_jun_y, t_jun_n], "endDate": "2026-11-12T01:00:00Z"},
            "m_dec": {"conditionId": "0x_m_dec", "clobTokenIds": [t_dec_y, t_dec_n], "endDate": "2026-11-12T02:00:00Z"},
        }
        uma_events = [
            {
                "id": "ev_uma_1",
                "title": "Clean Proposed UMA Carry",
                "markets": [
                    {
                        "id": "m_uma_ok",
                        "conditionId": "0x_m_uma_ok",
                        "questionID": "0x" + ("ab" * 32),
                        "resolvedBy": "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7",
                        "sportsMarketType": "moneyline",
                        "question": "Did Celtics beat Lakers?",
                        "description": "Official final score per nba.com.",
                        "outcomes": '["Yes", "No"]',
                        "clobTokenIds": json.dumps([t_uma_y, t_uma_n]),
                        "active": True,
                        "closed": False,
                        "acceptingOrders": True,
                        "enableOrderBook": True,
                        "feesEnabled": False,
                        "umaResolutionStatus": "proposed",
                        "umaResolutionStatuses": '["proposed"]',
                        "customLiveness": 3600,
                        "volume24hr": 1500.0,
                    },
                    {
                        "id": "m_uma_subj",
                        "conditionId": "0x_m_uma_subj",
                        "questionID": "0x" + ("cd" * 32),
                        "resolvedBy": "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7",
                        "question": 'Will Trump say "Tariff" during his speech?',
                        "description": "Resolves Yes if said verbatim.",
                        "outcomes": '["Yes", "No"]',
                        "clobTokenIds": json.dumps([t_subj_y, t_subj_n]),
                        "active": True,
                        "closed": False,
                        "acceptingOrders": True,
                        "enableOrderBook": True,
                        "feesEnabled": False,
                        "umaResolutionStatus": "proposed",
                        "umaResolutionStatuses": '["proposed"]',
                        "customLiveness": 3600,
                        "volume24hr": 1500.0,
                    },
                    {
                        "id": "6707503",
                        "conditionId": "0x_kmia",
                        "question": "KMIA Nov 7 Disputed",
                        "outcomes": '["Yes", "No"]',
                        "clobTokenIds": '["900000000000000000001", "900000000000000000002"]',
                        "active": True,
                        "closed": False,
                        "enableOrderBook": True,
                        "feesEnabled": False,
                        "umaResolutionStatus": "proposed",
                        "customLiveness": 3600,
                    },
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            cand_jsonl = tmp_p / "d1_live_box_candidates.jsonl"
            bridge = HarvesterCandidateBridge(
                candidates_jsonl_path=cand_jsonl,
                dedupe_state_path=tmp_p / "dedupe.json",
                live_harvester_state_path=tmp_p / "no_state.json",
            )

            # 1. JIT Re-Verify DECAYED case: Leg B (`t_dec_y`) ask jumped from `0.44` -> `0.62`!
            jit_calls: list = []

            def _jit_decayed(tids):
                jit_calls.append(tuple(tids))
                dec = dict(raw_initial)
                dec[t_dec_y] = _make_book(t_dec_y, "m_dec", [(0.62, 30.0)], [(0.59, 30.0)])
                return ({k: dec[k] for k in tids if k in dec}, {"fetch_timestamp_sec": 1794400009.5})

            res_dec = bridge.emit_verified_candidates(
                [rec_cal],
                books,
                market_meta_by_id=mkt_meta,
                events=[],
                jit_book_fetcher=_jit_decayed,
                verifier=ver,
                enable_passive_maker_bridge=False,
                fallback_reconciled_nav_usd=48.695132,
                now_ts=1794400009.5,
            )
            self.assertEqual(res_dec["candidates_emitted_this_cycle"], 0)
            self.assertEqual(res_dec["jit_rejected_this_cycle"], 1)
            self.assertEqual(res_dec["skipped_by_reason"].get("JIT_BOOK_REVERIFY_EDGE_DECAYED"), 1)
            self.assertFalse(cand_jsonl.exists())
            # Confirm all 4 tokens (`t_jun_n`, `t_dec_y` + opp tokens `t_jun_y`, `t_dec_n`) were polled!
            self.assertEqual(set(jit_calls[0]), {t_jun_y, t_jun_n, t_dec_y, t_dec_n})

            # 2. JIT Anti-Box Complement Parity Veto (`ask_a + bid_oa = 0.46 + 0.65 = 1.11 > 1.015`)
            def _jit_bad_opp(tids):
                bad = dict(raw_initial)
                bad[t_jun_y] = _make_book(t_jun_y, "m_jun", [(0.70, 30.0)], [(0.65, 30.0)])
                return ({k: bad[k] for k in tids if k in bad}, {"fetch_timestamp_sec": 1794400010.5})

            res_veto = bridge.emit_verified_candidates(
                [rec_cal],
                books,
                market_meta_by_id=mkt_meta,
                events=[],
                jit_book_fetcher=_jit_bad_opp,
                verifier=ver,
                enable_passive_maker_bridge=False,
                fallback_reconciled_nav_usd=48.695132,
                now_ts=1794400010.5,
            )
            self.assertEqual(res_veto["candidates_emitted_this_cycle"], 0)
            self.assertEqual(res_veto["skipped_by_reason"].get("JIT_ANTI_BOX_COMPLEMENT_VETO"), 1)

            # 3. JIT Re-Verify SURVIVING case + Passive UMA `SINGLE_LEG_MAKER_LOCK` emission!
            def _jit_valid(tids):
                return ({k: raw_initial[k] for k in tids if k in raw_initial}, {"fetch_timestamp_sec": 1794400012.345})

            res_ok = bridge.emit_verified_candidates(
                [rec_cal],
                books,
                market_meta_by_id=mkt_meta,
                events=uma_events,
                jit_book_fetcher=_jit_valid,
                verifier=ver,
                enable_passive_maker_bridge=True,
                fallback_reconciled_nav_usd=48.695132,
                now_ts=1794400012.345,
            )
            self.assertEqual(res_ok["candidates_emitted_this_cycle"], 2)
            self.assertEqual(res_ok["taker_boxes_emitted_this_cycle"], 1)
            self.assertEqual(res_ok["maker_locks_emitted_this_cycle"], 1)
            self.assertEqual(res_ok["jit_reverified_this_cycle"], 2)
            self.assertEqual(res_ok["skipped_by_reason"].get("UMA_NON_OBJECTIVE_VETOED"), 1)

            emitted = [json.loads(ln) for ln in cand_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
            by_type = {r["box_type"]: r for r in emitted}
            cal_em = by_type["LADDER_MONO"]
            self.assertEqual(cal_em["leg_a_token_id"], t_jun_n)
            self.assertEqual(cal_em["leg_a_opp_token_id"], t_jun_y)
            self.assertEqual(cal_em["leg_b_token_id"], t_dec_y)
            self.assertEqual(cal_em["leg_b_opp_token_id"], t_dec_n)
            self.assertTrue(cal_em["leg_a_opp_token_id"].isdigit() and len(cal_em["leg_a_opp_token_id"]) >= 20)
            self.assertTrue(cal_em["leg_b_opp_token_id"].isdigit() and len(cal_em["leg_b_opp_token_id"]) >= 20)
            self.assertEqual(set(cal_em["ws_books"].keys()), {t_jun_y, t_jun_n, t_dec_y, t_dec_n})
            self.assertAlmostEqual(cal_em["ts_unix"], 1794400012.345, places=3)
            self.assertAlmostEqual(cal_em["ws_books_ts"], 1794400012.345, places=3)

            sll_mkr = by_type["SINGLE_LEG_MAKER_LOCK"]
            self.assertEqual(sll_mkr["sleeve_source"], "BOND1_UMA_RESOLUTION_CARRY")
            self.assertEqual(sll_mkr["leg_a_market_id"], "m_uma_ok")
            self.assertEqual(sll_mkr["leg_a_token_id"], t_uma_y)
            self.assertEqual(sll_mkr["leg_a_opp_token_id"], t_uma_n)
            self.assertAlmostEqual(sll_mkr["leg_a_limit_price"], 0.991, places=4)
            self.assertLessEqual(sll_mkr["shares"] * sll_mkr["box_cost_net"], 48.695132 * 0.15 + 1e-4)
            self.assertNotEqual(sll_mkr["leg_a_market_id"], "6707503")


if __name__ == "__main__":
    unittest.main()

import dataclasses
import http.client
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.full_throttle_pipeline import (
    DormantOpportunityEntry,
    DormantOpportunityStore,
    HarvesterCandidateBridge,
    PublicPolymarketScannerClient,
    coerce_to_pipeline_record,
    load_dormant_fast_rescan_tokens,
)
from src.polymarket_research.stage_c_zero_loss_velocity import (
    check_strict_pure_riskless_candidate_gate,
    is_verified_full_throttle_2leg_box,
    verify_multileg_atomicity_or_inventory_cover,
)
from src.polymarket_research.universal_arb_verifier import (
    ActionLeg,
    ActionType,
    CandidateStructure,
    InstrumentOrderBook,
    InventoryHolding,
    StateSpec,
    StateSpaceBuilder,
    UniversalArbVerifier,
    VerificationConfig,
)
from src.polymarket_research.v6_restriction_and_capital_allocator import (
    DynamicMarginalCapitalAllocator,
    ExecutionMode,
    OpportunityClass,
    PortfolioCandidateSpec,
)


def _make_book(
    token_id: str,
    market_id: str,
    asks,
    bids,
    *,
    condition_id: str = "",
    outcome_label: str = "YES",
    min_order_size: float = 5.0,
    tick_size: float = 0.01,
    fee_rate_bps: float = 0.0,
    now_ts: float = 1794400000.0,
) -> InstrumentOrderBook:
    raw = {
        "asset_id": token_id,
        "market": market_id,
        "asks": [{"price": str(p), "size": str(s)} for p, s in asks],
        "bids": [{"price": str(p), "size": str(s)} for p, s in bids],
        "min_order_size": str(min_order_size),
        "tick_size": str(tick_size),
    }
    return InstrumentOrderBook.from_raw(
        token_id,
        raw,
        market_id=market_id,
        condition_id=condition_id or f"0xcond_{market_id}",
        outcome_label=outcome_label,
        fee_rate_bps=fee_rate_bps,
        tick_size=tick_size,
        min_order_size=min_order_size,
        book_timestamp_sec=now_ts,
    )


def _live_harvester_stub(*, collateral: float = 48.70, executor=None):
    return SimpleNamespace(
        _last_known_collateral=collateral,
        active_positions={},
        enforce_pure_riskless_mode=True,
        get_market_book=lambda *a, **kw: {},
        execute_snipe_order=lambda *a, **kw: None,
        execute_snipe_order_async=lambda *a, **kw: None,
        post_maker_entry_order=lambda *a, **kw: None,
        executor=executor,
    )


class TestV62StageCAndBridgeUpgrades(unittest.TestCase):
    def test_stage_c_negrisk_augmented_2no_vs_convert_and_ctf_overround(self) -> None:
        nr2_aug_box = {
            "box_type": "NEGRISK_2LEG",
            "sleeve_source": "XV_SUBSET_NO_2LEG_BOX",
            "opportunity_class": "CLASS_A",
            "rule_verified": True,
            "min_state_net_payoff_usd": 0.45,
            "box_cost_net": 0.94,
            "leg_count": 2,
            "neg_risk_augmented": True,
            "leg_a_market_id": "m_nr_a",
            "leg_b_market_id": "m_nr_b",
            "leg_a_token_id": "tok_no_a",
            "leg_b_token_id": "tok_no_b",
        }
        self.assertTrue(is_verified_full_throttle_2leg_box(nr2_aug_box))

        # Augmented NegRisk converts MUST still remain strictly blocked
        nr2_convert_aug = {
            "box_type": "NEGRISK_CONVERT",
            "sleeve_source": "NR2_2LEG_CONVERT_NO_SUBSET_ARB",
            "convert_mode": "NR2_PURE_CASH_CONVERT",
            "rule_verified": True,
            "min_state_net_payoff_usd": 0.50,
            "box_cost_net": 0.92,
            "leg_count": 2,
            "neg_risk_augmented": True,
            "no_legs": [{"market_id": "m1"}, {"market_id": "m2"}],
        }
        self.assertFalse(is_verified_full_throttle_2leg_box(nr2_convert_aug))

        harv = _live_harvester_stub()
        rb = {"strict_pure_riskless_mode": True}

        ctf_verified = {
            "box_type": "CTF_OVERROUND",
            "sleeve_source": "C1_SPLIT_AND_SELL_OVERROUND",
            "opportunity_class": "CLASS_A",
            "rule_verified": True,
            "atomic_split_sell_rollback_verified": True,
            "min_state_net_payoff_usd": 0.35,
            "box_cost_net": 1.04,
            "leg_count": 2,
            "condition_id": "0xcond_c1",
            "leg_a_token_id": "tok_yes",
            "leg_b_token_id": "tok_no",
        }
        self.assertTrue(is_verified_full_throttle_2leg_box(ctf_verified))
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv, ctf_verified, rb))

        # NegRisk CTF_OVERROUND MUST be blocked (finish_protocol_v2_special_box_sync splits/merges with neg_risk=False)
        ctf_negrisk = {**ctf_verified, "neg_risk": True}
        self.assertFalse(is_verified_full_throttle_2leg_box(ctf_negrisk))
        self.assertIsNotNone(check_strict_pure_riskless_candidate_gate(harv, ctf_negrisk, rb))

        # Legacy unverified mint-sell MUST stay blocked
        ctf_legacy_blocked = {
            "box_type": "CTF_OVERROUND",
            "sleeve_source": "CTF_OVERROUND_MINT_SELL",
            "condition_id": "0xcond_c1",
            "leg_a_token_id": "tok_yes",
            "leg_b_token_id": "tok_no",
            "min_state_net_payoff_usd": 0.35,
            "rule_verified": True,
        }
        self.assertIn("PURE_RISKLESS", check_strict_pure_riskless_candidate_gate(harv, ctf_legacy_blocked, rb) or "")

    def test_stage_c_nr3_real_executor_symbols_and_closed_partition_gate(self) -> None:
        real_exec = SimpleNamespace(
            signature_type=3,
            _dispatch_funder_calls_locked=lambda *a, **kw: "0xtx",
            execute_nr3_synthetic_all_yes_overround=lambda *a, **kw: {"ok": True},
        )
        harv_real = _live_harvester_stub(executor=real_exec)

        nr3_box = {
            "box_type": "NEGRISK_CONVERT",
            "sleeve_source": "NR3_SYNTHETIC_ALL_YES_OVERROUND",
            "convert_mode": "NR3_SYNTHETIC_ALL_YES_OVERROUND",
            "neg_risk_augmented": False,
            "atomic_onchain_execution": True,
            "atomic_router_verified": True,
            "sequential_clob_legs": False,
            "min_state_net_payoff_usd": 0.40,
            "yes_sell_legs": [{"market_id": "m1"}, {"market_id": "m2"}, {"market_id": "m3"}],
        }
        self.assertTrue(verify_multileg_atomicity_or_inventory_cover(harv_real, nr3_box))

        # Blocked when enable_nr3_synthetic_overround is False
        res_off = check_strict_pure_riskless_candidate_gate(
            harv_real, nr3_box, {"strict_pure_riskless_mode": True, "enable_nr3_synthetic_overround": False}
        )
        self.assertIsNotNone(res_off)
        self.assertIn("NR3_SYNTHETIC_ALL_YES_OVERROUND", res_off)

        # Allowed when explicitly enabled + closed partition + real atomic executor symbols
        res_on = check_strict_pure_riskless_candidate_gate(
            harv_real, nr3_box, {"strict_pure_riskless_mode": True, "enable_nr3_synthetic_overround": True}
        )
        self.assertIsNone(res_on)

        # Augmented NegRisk NR3 must ALWAYS stay blocked
        nr3_aug = {**nr3_box, "neg_risk_augmented": True}
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                harv_real, nr3_aug, {"strict_pure_riskless_mode": True, "enable_nr3_synthetic_overround": True}
            )
        )

        # Sequential CLOB NR3 must ALWAYS stay blocked below $500
        nr3_seq = {**nr3_box, "atomic_onchain_execution": False, "sequential_clob_legs": True}
        self.assertFalse(verify_multileg_atomicity_or_inventory_cover(harv_real, nr3_seq))
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                harv_real, nr3_seq, {"strict_pure_riskless_mode": True, "enable_nr3_synthetic_overround": True}
            )
        )

    def test_l1_inventory_maker_completion_and_fees_enabled_passive_maker_and_utilization_hurdle(self) -> None:
        now_ts = 1794400000.0
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cand_jsonl = tmp / "d1_live_box_candidates.jsonl"
            dedupe_p = tmp / "dedupe.json"
            state_p = tmp / "live_harvester_state.json"
            state_p.write_text(
                json.dumps(
                    {
                        "reconciled_nav_usd": 48.70,
                        "live_bankroll": 48.70,
                        "active_positions": {},
                        "pending_entry_intents": {},
                    }
                ),
                encoding="utf-8",
            )

            bridge = HarvesterCandidateBridge(
                candidates_jsonl_path=cand_jsonl,
                dedupe_state_path=dedupe_p,
                live_harvester_state_path=state_p,
                utilization_aware_velocity_hurdle=True,
            )

            books = {
                "tok_held_y": _make_book("tok_held_y", "m_l1", [(0.52, 20.0)], [(0.50, 20.0)], outcome_label="YES", fee_rate_bps=700.0),
                "tok_comp_n": _make_book("tok_comp_n", "m_l1", [(0.50, 20.0)], [(0.45, 20.0)], outcome_label="NO", fee_rate_bps=700.0),
                "tok_slow_a": _make_book("tok_slow_a", "m_s1", [(0.42, 40.0)], [(0.40, 40.0)], outcome_label="NO"),
                "tok_slow_b": _make_book("tok_slow_b", "m_s2", [(0.48, 40.0)], [(0.46, 40.0)], outcome_label="YES"),
                "tok_slow_a_opp": _make_book("tok_slow_a_opp", "m_s1", [(0.60, 40.0)], [(0.58, 40.0)], outcome_label="YES"),
                "tok_slow_b_opp": _make_book("tok_slow_b_opp", "m_s2", [(0.54, 40.0)], [(0.52, 40.0)], outcome_label="NO"),
                "tok_fee_win": _make_book("tok_fee_win", "m_fee_uma", [(0.992, 40.0)], [(0.980, 40.0)], outcome_label="YES", tick_size=0.001, fee_rate_bps=500.0),
                "tok_fee_opp": _make_book("tok_fee_opp", "m_fee_uma", [(0.008, 40.0)], [(0.004, 40.0)], outcome_label="NO", tick_size=0.001, fee_rate_bps=500.0),
            }
            holdings = {
                "tok_held_y": InventoryHolding(
                    instrument_id="tok_held_y",
                    shares=10.0,
                    market_id="m_l1",
                    condition_id="0xcond_m_l1",
                    cost_basis_per_share=0.48,
                    mark_bid_per_share=0.50,
                )
            }
            ver = UniversalArbVerifier(VerificationConfig(max_budget_usd=48.70, reconciled_nav_usd=48.70, now_ts=now_ts))

            # 1. L1_LOCKED_INVENTORY_MAKER_COMPLETION (`postOnly` BUY NO @ 0.47 against held YES @ 0.48 -> $0.05 edge)
            rec_l1_mkr = coerce_to_pipeline_record(
                CandidateStructure(
                    candidate_id="L1_LOCKED_INVENTORY_MAKER_COMPLETION_m_l1",
                    family="L",
                    legs=(
                        ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id="tok_held_y", market_id="m_l1", label="YES"),
                        ActionLeg(
                            action_type=ActionType.BUY_CLOB,
                            instrument_id="tok_comp_n",
                            is_maker=True,
                            maker_price=0.47,
                            market_id="m_l1",
                            label="NO",
                        ),
                        ActionLeg(action_type=ActionType.CTF_MERGE, related_instrument_ids=("tok_held_y", "tok_comp_n"), market_id="m_l1"),
                    ),
                    states=StateSpaceBuilder.binary_complete_set_states("tok_held_y", "tok_comp_n"),
                    expected_lockup_hours=0.25,
                    worst_case_lockup_hours=0.50,
                    rule_verified=True,
                ),
                verifier=ver,
                books=books,
                holdings=holdings,
            )

            # 2. Non-L1 resting maker leg (`family="E"`) MUST STILL be excluded even if flagged CLASS_B
            rec_non_l1_mkr = dataclasses.replace(
                coerce_to_pipeline_record(
                    CandidateStructure(
                        candidate_id="NON_L1_MAKER_TEST",
                        family="E",
                        legs=(
                            ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_slow_a", is_maker=True, maker_price=0.41, market_id="m_s1"),
                            ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_slow_b", is_maker=False, market_id="m_s2"),
                        ),
                        states=(
                            StateSpec("s1", {"tok_slow_b": 1.0}),
                            StateSpec("s2", {"tok_slow_a": 1.0, "tok_slow_b": 1.0}),
                            StateSpec("s3", {"tok_slow_a": 1.0}),
                        ),
                        expected_lockup_hours=2.0,
                        worst_case_lockup_hours=2.0,
                        rule_verified=True,
                    ),
                    verifier=ver,
                    books=books,
                ),
                opportunity_class="CLASS_B",
                is_mathematically_proven_arb=True,
                disqualifiers=(),
            )

            # 3. Medium-lockup 3.0 bps/hr box (`expected_lockup_hours=370h` -> ~3.003 bps/hr)
            # Admitted at u=0.0 (`lambda=0.50 bps/hr`), rejected at u=0.90 (`lambda=14.675 bps/hr`)
            rec_med = coerce_to_pipeline_record(
                CandidateStructure(
                    candidate_id="MED_VEL_CAL_BOX",
                    family="E",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_slow_a", market_id="m_s1", label="NO"),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="tok_slow_b", market_id="m_s2", label="YES"),
                    ),
                    states=(
                        StateSpec("s1", {"tok_slow_b": 1.0}),
                        StateSpec("s2", {"tok_slow_a": 1.0, "tok_slow_b": 1.0}),
                        StateSpec("s3", {"tok_slow_a": 1.0}),
                    ),
                    expected_lockup_hours=370.0,
                    worst_case_lockup_hours=370.0,
                    rule_verified=True,
                ),
                verifier=ver,
                books=books,
            )

            events = [
                {
                    "id": "ev_fee_uma",
                    "title": "Objective UMA market with feesEnabled",
                    "slug": "obj-uma-fee-test",
                    "markets": [
                        {
                            "id": "m_fee_uma",
                            "conditionId": "0xcond_m_fee_uma",
                            "questionID": "0x" + ("ab" * 32),
                            "resolvedBy": "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7",
                            "sportsMarketType": "moneyline",
                            "question": "Did Celtics beat Lakers?",
                            "description": "Official final score per nba.com.",
                            "umaResolutionStatus": "proposed",
                            "umaResolutionStatuses": '["proposed"]',
                            "acceptingOrders": True,
                            "feesEnabled": True,
                            "enableOrderBook": True,
                            "customLiveness": 900,
                            "clobTokenIds": json.dumps(["tok_fee_win", "tok_fee_opp"]),
                            "outcomes": json.dumps(["YES", "NO"]),
                            "volume24hr": 1500.0,
                        }
                    ],
                }
            ]
            mkt_meta = {
                "m_l1": {"conditionId": "0xcond_m_l1", "endDate": "2026-11-12T00:00:00Z"},
                "m_s1": {"conditionId": "0xcond_m_s1", "endDate": "2026-11-28T00:00:00Z"},
                "m_s2": {"conditionId": "0xcond_m_s2", "endDate": "2026-11-29T00:00:00Z"},
            }

            res_idle = bridge.emit_verified_candidates(
                [rec_l1_mkr, rec_non_l1_mkr, rec_med],
                books,
                holdings=holdings,
                market_meta_by_id=mkt_meta,
                events=events,
                enable_passive_maker_bridge=True,
                fallback_reconciled_nav_usd=48.70,
                utilization_frac=0.0,
                now_ts=now_ts,
            )
            self.assertAlmostEqual(res_idle["effective_min_velocity_bps_per_hr"], 0.5, places=4)
            self.assertGreaterEqual(res_idle["skipped_by_reason"].get("RESTING_MAKER_LEG_EXCLUDED_FROM_TAKER_BRIDGE", 0), 1)

            rows = [json.loads(ln) for ln in cand_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
            by_bt = {r["box_type"]: r for r in rows}
            self.assertIn("SINGLE_LEG_MAKER_LOCK", by_bt)
            self.assertIn("LADDER_MONO", by_bt)

            # Verify L1 maker candidate passes Stage C live gate
            l1_rows = [r for r in rows if r.get("sleeve_source") == "C1_BINARY_COMPLETE_SET"]
            self.assertEqual(len(l1_rows), 1)
            l1_row = l1_rows[0]
            self.assertEqual(l1_row["box_type"], "SINGLE_LEG_MAKER_LOCK")
            self.assertEqual(l1_row["leg_a_fee_rate"], 0.0)
            self.assertTrue(l1_row["post_only"])
            self.assertTrue(l1_row["inventory_backed_completion"])
            real_inv_harv = _live_harvester_stub(
                executor=SimpleNamespace(get_onchain_erc1155_balance=lambda tid: 10.0 if tid == "tok_held_y" else 0.0)
            )
            self.assertIsNone(
                check_strict_pure_riskless_candidate_gate(
                    real_inv_harv,
                    l1_row,
                    {
                        "strict_pure_riskless_mode": True,
                        "enable_single_leg_maker_bond1": True,
                        "enable_inventory_backed_maker_completion": True,
                    },
                    is_maker=True,
                )
            )

            # Verify feesEnabled=True passive maker lock emitted with leg_a_fee_rate == 0.0
            bond_rows = [r for r in rows if r.get("sleeve_source") == "BOND1_UMA_RESOLUTION_CARRY"]
            self.assertEqual(len(bond_rows), 1)
            self.assertTrue(bond_rows[0]["market_fees_enabled"])
            self.assertEqual(bond_rows[0]["leg_a_fee_rate"], 0.0)
            self.assertTrue(bond_rows[0]["post_only"])

            # At high utilization (u=0.90 -> hurdle ~14.675 bps/hr), 3.0 bps/hr MED_VEL_CAL_BOX MUST be skipped!
            res_high_u = bridge.emit_verified_candidates(
                [rec_med],
                books,
                holdings=holdings,
                market_meta_by_id=mkt_meta,
                enable_passive_maker_bridge=False,
                fallback_reconciled_nav_usd=48.70,
                utilization_frac=0.90,
                now_ts=now_ts + 120.0,
            )
            self.assertGreater(res_high_u["effective_min_velocity_bps_per_hr"], 14.0)
            self.assertEqual(res_high_u["candidates_emitted_this_cycle"], 0)
            self.assertGreaterEqual(res_high_u["skipped_by_reason"].get("BELOW_VELOCITY_HURDLE_7_5_BPS_HR", 0), 1)

    def test_dormant_fast_rescan_export_and_loader_and_kmia_filter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            store = DormantOpportunityStore(tmp / "dormant.json")
            now_ts = 1794400000.0
            store.entries["d_clean_close"] = DormantOpportunityEntry(
                candidate_id="CLEAN_NEAR_ARB",
                family_code="D",
                sub_type="SUBSET_NO",
                title_summary="Clean near arb",
                market_ids=("m1", "m2"),
                event_ids=("e1",),
                instrument_ids=("tok_fast_1", "tok_fast_2"),
                dormant_reason="NEAR_ARB",
                gap_to_breakeven_bps=22.0,
                best_gap_to_breakeven_bps=22.0,
                book_top_signature={},
                structure_dict=None,
                first_stored_ts=now_ts,
                last_checked_ts=now_ts,
                status="DORMANT",
            )
            store.entries["d_kmia"] = DormantOpportunityEntry(
                candidate_id="KMIA_FROZEN_ENTRY",
                family_code="A",
                sub_type="COMPLETE_SET",
                title_summary="Miami KMIA temperature",
                market_ids=("6707503",),
                event_ids=("e_kmia",),
                instrument_ids=("tok_kmia_should_skip",),
                dormant_reason="NEAR_ARB",
                gap_to_breakeven_bps=10.0,
                best_gap_to_breakeven_bps=10.0,
                book_top_signature={},
                structure_dict=None,
                first_stored_ts=now_ts,
                last_checked_ts=now_ts,
                status="DORMANT",
            )
            store.entries["d_too_wide"] = DormantOpportunityEntry(
                candidate_id="TOO_WIDE",
                family_code="D",
                sub_type="SUBSET_NO",
                title_summary="Wide near arb",
                market_ids=("m3",),
                event_ids=("e3",),
                instrument_ids=("tok_wide_skip",),
                dormant_reason="NEAR_ARB",
                gap_to_breakeven_bps=120.0,
                best_gap_to_breakeven_bps=120.0,
                book_top_signature={},
                structure_dict=None,
                first_stored_ts=now_ts,
                last_checked_ts=now_ts,
                status="DORMANT",
            )
            out_path = tmp / "dormant_fast_rescan_tokens.json"
            exported = store.export_fast_rescan_tokens(out_path, max_tokens=100, max_gap_bps=50.0, now_ts=now_ts)
            self.assertEqual(exported, ["tok_fast_1", "tok_fast_2"])

            loaded_fresh = load_dormant_fast_rescan_tokens(1800.0, path=out_path, now_ts=now_ts + 60.0)
            self.assertEqual(loaded_fresh, ["tok_fast_1", "tok_fast_2"])

            loaded_stale = load_dormant_fast_rescan_tokens(1800.0, path=out_path, now_ts=now_ts + 1805.0)
            self.assertEqual(loaded_stale, [])

    def test_fetch_jit_bridge_books_reuses_keep_alive_connection(self) -> None:
        client = PublicPolymarketScannerClient(timeout_sec=3.0)
        created_conns = []

        class _FakeResp:
            status = 200
            will_close = False

            def getheader(self, name, default=""):
                return ""

            def read(self):
                return json.dumps(
                    [
                        {
                            "asset_id": "tok_a",
                            "market": "m_a",
                            "asks": [{"price": "0.49", "size": "20"}],
                            "bids": [{"price": "0.47", "size": "20"}],
                        }
                    ]
                ).encode("utf-8")

        class _FakeConn:
            def __init__(self, host, timeout=None, context=None):
                self.requests = 0
                self.last_headers = {}
                created_conns.append(self)

            def request(self, method, url, body=None, headers=None):
                self.requests += 1
                self.last_headers = dict(headers or {})

            def getresponse(self):
                return _FakeResp()

            def close(self):
                pass

        with patch.object(http.client, "HTTPSConnection", _FakeConn):
            out1, _ = client.fetch_jit_bridge_books(["tok_a"])
            out2, _ = client.fetch_jit_bridge_books(["tok_a"])

        self.assertEqual(len(created_conns), 1)
        self.assertEqual(created_conns[0].requests, 2)
        self.assertEqual(created_conns[0].last_headers.get("Connection"), "keep-alive")
        self.assertIn("tok_a", out1)
        self.assertIn("tok_a", out2)

    def test_custom_liveness_inverse_lockup_weighting_and_strategy_json(self) -> None:
        alloc = DynamicMarginalCapitalAllocator(max_cluster_nav_pct=0.50)
        fast_900s = PortfolioCandidateSpec(
            candidate_id="BOND_900S",
            family_code="K",
            sleeve_name="BOND1_UMA_RESOLUTION_CARRY",
            opportunity_class=OpportunityClass.CLASS_B,
            cluster_keys=("c_fast",),
            instrument_ids=("tok_fast",),
            max_executable_shares=15.0,
            capital_per_share_usd=0.98,
            worst_case_net_payoff_per_share_usd=0.02,
            expected_net_payoff_per_share_usd=0.02,
            fees_and_conversion_per_share_usd=0.0,
            nominal_maturity_hours=0.0,
            settlement_or_merge_hours=2.0,
            custom_liveness_hours=0.25,
        )
        slow_2h = PortfolioCandidateSpec(
            candidate_id="BOND_2H",
            family_code="K",
            sleeve_name="BOND1_UMA_RESOLUTION_CARRY",
            opportunity_class=OpportunityClass.CLASS_B,
            cluster_keys=("c_slow",),
            instrument_ids=("tok_slow",),
            max_executable_shares=15.0,
            capital_per_share_usd=0.98,
            worst_case_net_payoff_per_share_usd=0.02,
            expected_net_payoff_per_share_usd=0.02,
            fees_and_conversion_per_share_usd=0.0,
            nominal_maturity_hours=0.0,
            settlement_or_merge_hours=2.0,
        )

        self.assertAlmostEqual(alloc.effective_lockup_hours(fast_900s), 0.25, places=6)
        self.assertAlmostEqual(alloc.effective_lockup_hours(slow_2h), 2.0, places=6)
        self.assertAlmostEqual(alloc.lockup_velocity_weight(fast_900s), 4.0, places=6)

        res = alloc.allocate(
            [slow_2h, fast_900s],
            mode=ExecutionMode.LIVE,
            deployable_liquid_cash_usd=16.0,
            reconciled_nav_usd=48.70,
        )
        by_id = {d.candidate_id: d for d in res.decisions}
        self.assertTrue(by_id["BOND_900S"].accepted)
        self.assertFalse(by_id["BOND_2H"].accepted)
        self.assertGreater(by_id["BOND_900S"].recycling_compounding_bonus_usd, 0.0)
        self.assertGreater(by_id["BOND_900S"].realizable_bps_per_hour, by_id["BOND_2H"].realizable_bps_per_hour * 7.0)

        cfg = json.loads((REPO_ROOT / "config" / "polymarket_strategy_and_risk.json").read_text(encoding="utf-8"))
        self.assertEqual(float(cfg["riskless_boxes"]["ft_funnel_persist_interval_sec"]), 60.0)

    def test_stage_c_sp1_nba_zero_fee_and_nr2_free_tail_pure_cash_gates(self) -> None:
        from src.polymarket_research.stage_c_zero_loss_velocity import is_verified_full_throttle_2leg_box

        harv = _live_harvester_stub()
        rb = {"strict_pure_riskless_mode": True}
        sp1_ok = {
            "sleeve_source": "SP1_NBA_ZERO_FEE_BOX",
            "box_type": "NBA_DOMINANCE",
            "leg_a_market_id": "m_nba_ml",
            "leg_b_market_id": "m_nba_sp",
            "leg_a_token_id": "t_ml",
            "leg_b_token_id": "t_sp",
            "leg_a_fee_rate": 0.0,
            "leg_b_fee_rate": 0.0,
            "box_cost_net": 0.991,
        }
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv, sp1_ok, rb))
        self.assertTrue(is_verified_full_throttle_2leg_box({**sp1_ok, "rule_verified": True, "min_state_net_payoff_usd": 0.09}))

        sp1_fee_bad = {**sp1_ok, "leg_a_fee_rate": 0.02}
        self.assertFalse(is_verified_full_throttle_2leg_box({**sp1_fee_bad, "rule_verified": True, "min_state_net_payoff_usd": 0.09}))
        self.assertIn("PURE_RISKLESS_SP1_REQUIRES_ZERO_FEE", str(check_strict_pure_riskless_candidate_gate(harv, sp1_fee_bad, rb)))

        nr2_pure_tail = {
            "sleeve_source": "NR2_CONVERT_NO_SUBSET_ARB",
            "box_type": "NEGRISK_CONVERT",
            "convert_mode": "NR2_SUBSET_CONVERT_FREE_TAIL",
            "no_legs": [{"token_id": "n1"}, {"token_id": "n2"}],
            "liquid_yes_sells": [],
            "box_cost_net": 0.991,
            "fee_bips": 0.0,
        }
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv, nr2_pure_tail, rb))
        self.assertTrue(is_verified_full_throttle_2leg_box({**nr2_pure_tail, "rule_verified": True, "min_state_net_payoff_usd": 0.09}))

        nr2_risky_sell = {**nr2_pure_tail, "liquid_yes_sells": [{"token_id": "y3"}]}
        self.assertFalse(is_verified_full_throttle_2leg_box({**nr2_risky_sell, "rule_verified": True, "min_state_net_payoff_usd": 0.09}))
        self.assertIn("PURE_RISKLESS", str(check_strict_pure_riskless_candidate_gate(harv, nr2_risky_sell, rb)))

    def test_alpha124_d1_parity_antibox_depth_fallback_and_quiet_book_cap(self) -> None:
        import asyncio
        from unittest import mock
        from src.polymarket_research import alpha_124_shadow_daemon as a124

        d = a124.Alpha124ShadowDaemon(single_scan=True)
        d.closed_positions = [
            {
                "sleeve": "D1_QUIET_BOOK_BOX",
                "won": True,
                "entry_eff_px_t1000": 0.985,
                "tier_pnls_usd": {"T1000": 1.0},
                "legging_adjusted_tier_pnls_usd": {"T1000": 0.8},
            }
            for _ in range(8)
        ]
        self.assertTrue(d.is_sleeve_grad8_ready("D1_QUIET_BOOK_BOX"))

        # Empty opp_b bid + valid primary bk_tb & opp_a bid (e.g. 15M_UP + 4H_DOWN) passes parity check
        leg_a = {"token_id": "ta", "opp_token_id": "oa", "label": "15M_UP", "side": "YES", "horizon": "15m", "market_id": "m15", "condition_id": "c15", "strike": 100.0, "fee_rate": 0.0, "fee_exponent": 1.0, "neg_risk": False}
        leg_b = {"token_id": "tb", "opp_token_id": "ob", "label": "4H_DOWN", "side": "NO", "horizon": "4h", "market_id": "m4h", "condition_id": "c4h", "strike": 102.0, "fee_rate": 0.0, "fee_exponent": 1.0, "neg_risk": False}
        bks_pass = {
            "ta": {"bids": [{"price": "0.35", "size": "50"}], "asks": [{"price": "0.36", "size": "50"}]},
            "tb": {"bids": [{"price": "0.58", "size": "50"}], "asks": [{"price": "0.59", "size": "50"}]},
            "oa": {"bids": [{"price": "0.64", "size": "50"}], "asks": [{"price": "0.65", "size": "50"}]},
            "ob": {"bids": [], "asks": [{"price": "0.99", "size": "50"}]},
        }
        self.assertTrue(asyncio.run(d._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_pass)))

        # Inverted OTM+OTM anti-box MUST remain vetoed even with primary books present
        bks_bad = {
            **bks_pass,
            "tb": {"bids": [{"price": "0.20", "size": "50"}], "asks": [{"price": "0.21", "size": "50"}]},
        }
        self.assertFalse(asyncio.run(d._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_bad)))

        # Thin depth on fee-bearing D1: $24 takes 20 sh at 1.0x depth ratio (drag <= 0), $10 fallback takes 10 sh at 2.0x (> 0)
        leg_a_fee = {**leg_a, "fee_rate": 0.0625}
        leg_b_fee = {**leg_b, "fee_rate": 0.0625}
        bk_a_thin = {"bids": [{"price": "0.45", "size": "30"}], "asks": [{"price": "0.478", "size": "20"}]}
        bk_b_thin = {"bids": [{"price": "0.45", "size": "30"}], "asks": [{"price": "0.478", "size": "20"}]}
        w_fb = d._walk_d1_live_clip_with_fallback(
            bk_a_thin, bk_b_thin, leg_a_fee, leg_b_fee,
            primary_budget_usd=24.0, max_box_cost_net=0.989, is_4h_mixed=True,
        )
        self.assertTrue(w_fb.get("filled"))
        self.assertLessEqual(int(w_fb["shares"]), 12)

        with tempfile.TemporaryDirectory() as td:
            cand_p = Path(td) / "cands.jsonl"
            now_ts = 1794500000.0
            m15 = SimpleNamespace(asset="BTC", horizon="15m", market_id="m15", end_ts=now_ts + 300.0)
            m5 = SimpleNamespace(asset="BTC", horizon="5m", market_id="m5", end_ts=now_ts + 120.0)
            dom_info = {"regime": "15M_UP+4H_DOWN", "k_low": 100.0, "k_high": 102.0, "corridor_bps": 200.0, "leg_a": leg_a_fee, "leg_b": leg_b_fee}
            with mock.patch.object(a124, "D1_LIVE_CANDIDATES_FILE", cand_p):
                ok_emit = d.emit_live_d1_box_candidate(
                    m15, m5, dom_info, w_fb, now_ts, is_quiet_book=True, sleeve_source="D1_QUIET_BOOK_BOX"
                )
            self.assertTrue(ok_emit)
            row = json.loads(cand_p.read_text(encoding="utf-8").strip())
            self.assertGreaterEqual(float(row["max_box_cost_net"]), 0.989)
            self.assertEqual(row["sleeve_source"], "D1_QUIET_BOOK_BOX")

    def test_alpha124_two_leg_emissions_and_restart_state_persistence(self) -> None:
        from unittest import mock
        from src.polymarket_research import alpha_124_shadow_daemon as a124

        harv = _live_harvester_stub()
        rb = {"strict_pure_riskless_mode": True}
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cand_p = tmp / "cands.jsonl"
            state_p = tmp / "state.json"
            mirror_p = tmp / "mirror.json"
            ledger_p = tmp / "ledger.jsonl"
            now_ts = 1794500000.0

            d = a124.Alpha124ShadowDaemon(single_scan=True)
            d.closed_positions = [
                {
                    "sleeve": sl_g,
                    "won": True,
                    "entry_eff_px_t1000": 0.985,
                    "tier_pnls_usd": {"T1000": 1.0},
                    "legging_adjusted_tier_pnls_usd": {"T1000": 1.0},
                }
                for sl_g in ("COND1_MACRO_PARTITION_BOX", "D1_SAME_ORACLE_DOMINANCE_BOX", "SP1_NBA_ZERO_FEE_BOX")
                for _ in range(8)
            ]
            # Inject 2 pre-fix anti-box D1 rows (<0.900) and verify is_sleeve_grad8_ready keeps parity with write_state_files
            d.closed_positions.extend([
                {"sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX", "won": True, "entry_eff_px_t1000": 0.45, "tier_pnls_usd": {"T1000": 2.0}}
                for _ in range(2)
            ])
            self.assertTrue(d.is_sleeve_grad8_ready("D1_SAME_ORACLE_DOMINANCE_BOX"))

            with mock.patch.object(a124, "D1_LIVE_CANDIDATES_FILE", cand_p), \
                 mock.patch.object(a124, "STATE_FILE", state_p), \
                 mock.patch.object(a124, "LIVE_ALPHA124_STATE_MIRROR_FILE", mirror_p), \
                 mock.patch.object(a124, "LEDGER_FILE", ledger_p):
                # 1) Fee-bearing CAL1 with k_low=0.0 (gross 0.92 + 0.04 fee_rate < 0.992)
                la_cal = {"token_id": "cal_a", "opp_token_id": "cal_oa", "market_id": "m_cal_a", "condition_id": "c_cal_a", "side": "YES", "label": "CAL_A", "fee_rate": 0.04, "fee_exponent": 1.0, "neg_risk": False, "strike": 0.0}
                lb_cal = {"token_id": "cal_b", "opp_token_id": "cal_ob", "market_id": "m_cal_b", "condition_id": "c_cal_b", "side": "NO", "label": "CAL_B", "fee_rate": 0.04, "fee_exponent": 1.0, "neg_risk": False, "strike": 100.0}
                bk_46 = {"bids": [{"price": "0.45", "size": "50"}], "asks": [{"price": "0.46", "size": "50"}]}
                bk_49 = {"bids": [{"price": "0.48", "size": "50"}], "asks": [{"price": "0.49", "size": "50"}]}
                bk_48 = {"bids": [{"price": "0.47", "size": "50"}], "asks": [{"price": "0.48", "size": "50"}]}
                self.assertTrue(d.emit_live_two_leg_box_candidate(
                    sleeve_source="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                    box_type="MACRO_DOMINANCE", asset="MACRO", dedupe_key="CAL_0_TEST",
                    leg_a=la_cal, leg_b=lb_cal, bk_a=bk_46, bk_b=bk_46,
                    close_ts=now_ts + 86400.0, now_ts=now_ts, k_low=0.0, k_high=100.0,
                ))
                # 2) COND1 72h (<= 7d at <= 0.988)
                la_cnd = {**la_cal, "token_id": "cnd_a", "market_id": "m_cnd_a", "fee_rate": 0.0, "strike": 100.0}
                lb_cnd = {**lb_cal, "token_id": "cnd_b", "market_id": "m_cnd_b", "fee_rate": 0.0, "strike": 101.0}
                self.assertTrue(d.emit_live_two_leg_box_candidate(
                    sleeve_source="COND1_MACRO_PARTITION_BOX",
                    box_type="MACRO_DOMINANCE", asset="MACRO", dedupe_key="COND_72H_TEST",
                    leg_a=la_cnd, leg_b=lb_cnd, bk_a=bk_49, bk_b=bk_48,
                    close_ts=now_ts + 72.0 * 3600.0, now_ts=now_ts, k_low=100.0, k_high=101.0,
                ))
                # 3) SP1_NBA_ZERO_FEE_BOX at <= 0.992
                bk_495 = {"bids": [{"price": "0.49", "size": "50"}], "asks": [{"price": "0.495", "size": "50"}]}
                bk_496 = {"bids": [{"price": "0.49", "size": "50"}], "asks": [{"price": "0.496", "size": "50"}]}
                self.assertTrue(d.emit_live_two_leg_box_candidate(
                    sleeve_source="SP1_NBA_ZERO_FEE_BOX",
                    box_type="NBA_DOMINANCE", asset="NBA", dedupe_key="SP1_TEST",
                    leg_a={**la_cnd, "token_id": "nba_a", "market_id": "m_nba_a"},
                    leg_b={**lb_cnd, "token_id": "nba_b", "market_id": "m_nba_b"},
                    bk_a=bk_495, bk_b=bk_496, close_ts=now_ts + 7200.0, now_ts=now_ts, max_box_cost_override=0.992,
                ))
                # 4) C1_BINARY_COMPLETE_SET 0% fee at <= 0.996
                la_c1 = {**la_cnd, "token_id": "c1_y", "market_id": "m_c1", "condition_id": "cid_c1", "side": "YES", "label": "YES"}
                lb_c1 = {**lb_cnd, "token_id": "c1_n", "market_id": "m_c1", "condition_id": "cid_c1", "side": "NO", "label": "NO"}
                self.assertTrue(d.emit_live_two_leg_box_candidate(
                    sleeve_source="C1_BINARY_COMPLETE_SET",
                    box_type="COMPLETE_SET", asset="WEATHER", dedupe_key="C1_TEST",
                    leg_a=la_c1, leg_b=lb_c1, bk_a=bk_495, bk_b=bk_496,
                    close_ts=now_ts + 7200.0, now_ts=now_ts, max_box_cost_override=0.996,
                ))
                d.cycle_count = 39
                d.write_state_files([])

                rows = [json.loads(ln) for ln in cand_p.read_text(encoding="utf-8").splitlines() if ln.strip()]
                self.assertEqual(len(rows), 4)
                for r in rows:
                    self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv, r, rb), msg=r.get("sleeve_source"))
                self.assertTrue(rows[0]["rule_verified"])
                self.assertGreater(rows[0]["min_state_net_payoff_usd"], 0.0)

                st_saved = json.loads(state_p.read_text(encoding="utf-8"))
                self.assertEqual(st_saved["by_sleeve"]["D1_SAME_ORACLE_DOMINANCE_BOX"]["settled"], 8)
                self.assertEqual(st_saved["by_sleeve"]["D1_SAME_ORACLE_DOMINANCE_BOX"]["excluded_anti_box"], 2)
                self.assertEqual(st_saved["live_bridge_telemetry"]["emitted_total"], 4)

                # Restart onto fresh daemon without ledger file: __init__ runs _hydrate_state() automatically
                d2 = a124.Alpha124ShadowDaemon(single_scan=True)
                self.assertEqual(d2.cycle_count, 39)
                self.assertEqual(d2._live_bridge_emits_total, 4)
                self.assertEqual(d2._live_bridge_emits_by_sleeve.get("SP1_NBA_ZERO_FEE_BOX"), 1)
                self.assertTrue(d2.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX"))
                self.assertTrue(d2.is_sleeve_grad8_ready("D1_SAME_ORACLE_DOMINANCE_BOX"))
                d2.write_state_files([])
                st_after = json.loads(state_p.read_text(encoding="utf-8"))
                self.assertEqual(st_after["by_sleeve"]["COND1_MACRO_PARTITION_BOX"]["closed"], 8)
                self.assertEqual(st_after["by_sleeve"]["COND1_MACRO_PARTITION_BOX"]["settled"], 8)
                self.assertTrue(st_after["by_sleeve"]["COND1_MACRO_PARTITION_BOX"]["grad8_live_promoted"])


if __name__ == "__main__":
    unittest.main()

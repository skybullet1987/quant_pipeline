"""
Adversarial & End-to-End Regression Suite for DOMINUS v6.0 Restriction Reassessment (`R-01`..`R-44`)
and Portfolio-Level Dynamic Marginal Capital Allocator (`MRNV`).
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

import scripts.paa_cli as paa_cli
from scripts.run_v6_counterfactual_opportunity_audit import run_counterfactual_audit
from src.paa_os.permissions import PermissionGate
from src.polymarket_research.holistic_strategy_governance import passes_capital_velocity_hurdle
from src.polymarket_research.stage_c_zero_loss_velocity import (
    check_strict_pure_riskless_candidate_gate,
    load_alpha124_graduation_maps_with_lkg_cache,
)
from src.polymarket_research.v6_restriction_and_capital_allocator import (
    DynamicMarginalCapitalAllocator,
    ExecutionMode,
    ExposurePositionSpec,
    LossCauseAwareCapitalController,
    OpportunityClass,
    PortfolioCandidateSpec,
    assess_r26_to_r32_venue_restrictions,
    evaluate_correlated_worst_case_exposure,
    evaluate_decoupled_certification_and_fresh_state,
    evaluate_disputed_inventory_recovery_options,
    evaluate_evidence_based_venue_readiness,
    evaluate_mode_specific_eligibility,
    reconcile_infrastructure_expenses,
    validate_wallet_split_merge_capabilities,
    verify_exact_polymarket_fee_and_rounding,
    verify_independent_payoff_admission,
)


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestV60RestrictionReassessmentAndAllocator(unittest.TestCase):
    def test_01_mode_specific_separation_and_non_overridable_legal_gates(self) -> None:
        res_verdict = evaluate_mode_specific_eligibility(
            ExecutionMode.RESEARCH,
            jurisdiction="CA-ON",
            venue_live_authorized_for_jurisdiction=False,
            touches_d001_disputed_kmia=True,
            opportunity_class=OpportunityClass.CLASS_C,
            sequential_clob_legs=4,
            is_atomic_or_inventory_locked=False,
            reconciled_liquid_nav_usd=48.70,
            live_promotion_approved=False,
        )
        self.assertTrue(res_verdict.allowed)

        sh_kmia = evaluate_mode_specific_eligibility(
            ExecutionMode.SHADOW,
            jurisdiction="CA-ON",
            touches_d001_disputed_kmia=True,
            opportunity_class=OpportunityClass.CLASS_B,
        )
        self.assertFalse(sh_kmia.allowed)
        self.assertIn("D001", sh_kmia.reason)

        sh_tos = evaluate_mode_specific_eligibility(
            ExecutionMode.SHADOW,
            api_license_and_rate_limit_ok=False,
        )
        self.assertFalse(sh_tos.allowed)

        sh_multileg = evaluate_mode_specific_eligibility(
            ExecutionMode.SHADOW,
            jurisdiction="CA-ON",
            venue_live_authorized_for_jurisdiction=False,
            touches_d001_disputed_kmia=False,
            opportunity_class=OpportunityClass.CLASS_C,
            sequential_clob_legs=4,
            reconciled_liquid_nav_usd=48.70,
            live_promotion_approved=False,
        )
        self.assertTrue(sh_multileg.allowed)

        # LIVE NEVER allows CA-ON bypass even when corporate incorporation / remote FI host is claimed!
        live_bypass_attempt = evaluate_mode_specific_eligibility(
            ExecutionMode.LIVE,
            jurisdiction="CA-ON",
            venue_live_authorized_for_jurisdiction=False,
            claims_incorporation_or_remote_host_bypass=True,
            live_promotion_approved=True,
        )
        self.assertFalse(live_bypass_attempt.allowed)
        self.assertIn("BYPASS_ASSUMPTION", live_bypass_attempt.reason)

        # LIVE blocks >=3 sequential legs below $500 NAV (D-007)
        live_seq3 = evaluate_mode_specific_eligibility(
            ExecutionMode.LIVE,
            jurisdiction="FI_AUTHORIZED_TEST",
            venue_live_authorized_for_jurisdiction=True,
            sequential_clob_legs=3,
            is_atomic_or_inventory_locked=False,
            reconciled_liquid_nav_usd=253.00,
            live_promotion_approved=True,
        )
        self.assertFalse(live_seq3.allowed)
        self.assertIn("D007", live_seq3.reason)

    def test_02_r01_loss_cause_controller_and_r44_kmia_dominance_proof(self) -> None:
        ctrl = LossCauseAwareCapitalController()

        # 1. Full $50.51 -> $0.00 KMIA UMA write-off drops book equity $99.21 -> $48.70: MUST NOT HALT!
        v_kmia = ctrl.evaluate(
            liquid_pusd_usd=48.695132,
            quarantined_disputed_cost_usd=0.0,
            quarantined_disputed_bid_usd=0.0,
            post_baseline_closed_riskless_pnls_usd=(0.18, 0.24),
        )
        self.assertFalse(v_kmia.halted)
        self.assertAlmostEqual(v_kmia.quarantined_dispute_writeoff_delta_usd, -50.51, places=2)

        # 2. A -$1.65 unexpected loss on a NEW supposedly riskless box leaves cash at $47.05 (WELL above the
        #    arbitrary $30.00 v5 floor!), yet LossCauseAwareCapitalController IMMEDIATELY halts!
        v_bleed = ctrl.evaluate(
            liquid_pusd_usd=47.05,
            quarantined_disputed_cost_usd=50.51,
            quarantined_disputed_bid_usd=0.139,
            post_baseline_closed_riskless_pnls_usd=(-1.65,),
        )
        self.assertTrue(v_bleed.halted)
        self.assertTrue(any("RISKLESS_LOSS_ANOMALY" in r for r in v_bleed.halt_reasons))

        # 3. R-44 KMIA recovery option evaluation proves p* = 0.344% breakeven -> HOLD_TOUCH_NOTHING_D001
        kmia_eval = evaluate_disputed_inventory_recovery_options()
        self.assertEqual(kmia_eval["recommended_policy"], "HOLD_TOUCH_NOTHING_D001")
        self.assertTrue(kmia_eval["d001_live_execution_prohibited"])
        self.assertLess(kmia_eval["breakeven_dvm_win_probability"], 0.005)
        self.assertGreater(kmia_eval["ev_advantage_of_holding_usd"], 15.0)

    def test_03_r02_independent_payoff_proof_and_r03_cold_boot_lkg_protection(self) -> None:
        live_h = SimpleNamespace(enforce_pure_riskless_mode=True)
        rb_cfg = {"strict_pure_riskless_mode": True}

        cal_box_ok = {
            "sleeve_source": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
            "box_type": "BARRIER_MONO",
            "leg_a_fee_rate": 0.04,
            "leg_b_fee_rate": 0.04,
            "rule_verified": True,
            "min_state_net_payoff_usd": 0.014,
            "box_cost_net": 0.986,
            "t_early_ts": 1762900000.0,
            "t_late_ts": 1762986400.0,
            "leg_a_market_id": "m_early",
            "leg_b_market_id": "m_late",
            "leg_a_token_id": "tok_early_yes",
            "leg_b_token_id": "tok_late_no",
        }
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(live_h, cal_box_ok, rb_cfg))

        cal_inverted = dict(cal_box_ok, t_early_ts=1763000000.0, t_late_ts=1762900000.0)
        self.assertIn(
            "INVERTED_CALENDAR_DEADLINES",
            str(check_strict_pure_riskless_candidate_gate(live_h, cal_inverted, rb_cfg)),
        )

        w_proxy = {
            "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
            "box_type": "SINGLE_LEG_LOCK",
            "p_model": 0.9995,
            "dual_source_wu_metar_verified": False,
        }
        self.assertIn(
            "SINGLE_SOURCE_PROXY_BLOCKED",
            str(check_strict_pure_riskless_candidate_gate(live_h, w_proxy, rb_cfg)),
        )

        dup_proven = {
            "sleeve_source": "FT_I_PROVEN_DUPLICATE_EQUIVALENCE",
            "box_type": "EXACT_EQUIVALENCE",
            "rule_verified": True,
            "min_state_net_payoff_usd": 0.012,
            "box_cost_net": 0.988,
            "neg_risk_augmented": False,
            "leg_a_market_id": "m_dup_1",
            "leg_b_market_id": "m_dup_2",
            "leg_a_token_id": "tok_dup_1",
            "leg_b_token_id": "tok_dup_2",
        }
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(live_h, dup_proven, rb_cfg))

        aug_proof = verify_independent_payoff_admission(
            {
                "structure_type": "NEGRISK_PARTITION",
                "negRiskAugmented": True,
                "legs": [{"ask_price": 0.45}, {"ask_price": 0.45}],
            }
        )
        self.assertFalse(aug_proof.admitted)
        self.assertIn("AUGMENTED", aug_proof.reason)

        # R-03 Cold-Boot LKG Preservation Test:
        with tempfile.TemporaryDirectory() as td:
            dd = pathlib.Path(td)
            now_u = time.time()
            grad_state = {
                "cycles": 450,
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 12, "losses": 0, "win_rate_pct": 100.0},
                    "C1_BINARY_COMPLETE_SET": {"closed": 8, "losses": 0, "win_rate_pct": 100.0},
                },
                "by_d1_asset": {"BTC": {"closed": 12, "losses": 0, "win_rate_pct": 100.0}},
            }
            st_file = dd / "alpha124_shadow_state.json"
            st_file.write_text(json.dumps(grad_state), encoding="utf-8")
            harv = SimpleNamespace(_a124_lkg_grad_snapshot=None, _d1_grad_cache="UNSET", _a124_grad_cache_mtime=0.0)
            sl1, _, err1 = load_alpha124_graduation_maps_with_lkg_cache(harv, dd, dd, now_ts=now_u)
            self.assertIsNone(err1)
            self.assertEqual(sl1["D1_SAME_ORACLE_DOMINANCE_BOX"]["closed"], 12)
            self.assertTrue((dd / "alpha124_graduation_lkg_cache.json").exists())

            cold_boot_state = {
                "cycles": 0,
                "by_sleeve": {
                    f"SLEEVE_{i}": {"closed": 0, "losses": 0, "win_rate_pct": 0.0} for i in range(84)
                }
                | {"D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 0, "losses": 0, "win_rate_pct": 0.0}},
                "by_d1_asset": {"BTC": {"closed": 0, "losses": 0, "win_rate_pct": 0.0}},
            }
            time.sleep(0.02)
            st_file.write_text(json.dumps(cold_boot_state), encoding="utf-8")
            harv2 = SimpleNamespace(_a124_lkg_grad_snapshot=None, _d1_grad_cache="UNSET", _a124_grad_cache_mtime=0.0)
            sl2, da2, err2 = load_alpha124_graduation_maps_with_lkg_cache(harv2, dd, dd, now_ts=now_u + 5.0)
            self.assertIsNone(err2)
            self.assertEqual(sl2["D1_SAME_ORACLE_DOMINANCE_BOX"]["closed"], 12)
            self.assertEqual(da2["BTC"]["closed"], 12)

            loss_state = {
                "cycles": 3,
                "by_sleeve": {"D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 1, "losses": 1, "win_rate_pct": 0.0}},
                "by_d1_asset": {},
            }
            time.sleep(0.02)
            st_file.write_text(json.dumps(loss_state), encoding="utf-8")
            harv3 = SimpleNamespace(_a124_lkg_grad_snapshot=None, _d1_grad_cache="UNSET", _a124_grad_cache_mtime=0.0)
            sl3, _, _ = load_alpha124_graduation_maps_with_lkg_cache(harv3, dd, dd, now_ts=now_u + 10.0)
            self.assertEqual(sl3["D1_SAME_ORACLE_DOMINANCE_BOX"]["losses"], 1)

        dec = evaluate_decoupled_certification_and_fresh_state(
            is_contractual_identity_arb=True,
            cached_sleeve_record={"closed": 0, "losses": 0},
            lkg_sleeve_record=None,
            book_age_sec=12.0,
            max_book_age_sec=5.0,
            uma_resolution_status="none",
            accepting_orders=True,
            reconciled_liquid_cash_usd=48.70,
            required_capital_usd=10.0,
        )
        self.assertTrue(dec.structural_cert_ok)
        self.assertFalse(dec.fresh_market_and_account_ok)
        self.assertFalse(dec.overall_live_ok)

    def test_04_r04_r41_correlated_worst_case_exposure_cwce(self) -> None:
        existing = [
            ExposurePositionSpec(
                position_id="W_KORD_1",
                cluster_keys=("STATION:KORD", "FRONT:MIDWEST_20261111"),
                capital_committed_usd=5.00,
                is_same_condition_mergeable_box=False,
            )
        ]
        cand_block = ExposurePositionSpec(
            position_id="W_KMDW_2",
            cluster_keys=("STATION:KMDW", "FRONT:MIDWEST_20261111"),
            capital_committed_usd=3.00,
        )
        v_blk = evaluate_correlated_worst_case_exposure(cand_block, existing, reconciled_nav_usd=48.834132)
        self.assertFalse(v_blk.allowed)
        self.assertEqual(v_blk.binding_cluster_key, "FRONT:MIDWEST_20261111")

        cand_c1 = ExposurePositionSpec(
            position_id="C1_SAME_COND",
            cluster_keys=("FRONT:MIDWEST_20261111",),
            capital_committed_usd=15.00,
            is_same_condition_mergeable_box=True,
            partial_leg_unwind_risk_usd=0.20,
        )
        v_c1 = evaluate_correlated_worst_case_exposure(cand_c1, existing, reconciled_nav_usd=48.834132)
        self.assertTrue(v_c1.allowed)

    def test_05_r05_r08_paa_cli_approvals_selective_cancel_and_safeguard_resume(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            data_dir = root / "data" / "polymarket"
            (data_dir / "paa" / "approvals").mkdir(parents=True, exist_ok=True)
            (data_dir / "paa" / "logs").mkdir(parents=True, exist_ok=True)

            # 1. Selective CLOB cancel preserves active exit order while cancelling BUY entry anchors!
            state_path = data_dir / "live_harvester_state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "active_positions": {
                            "T_ACTIVE_1": {
                                "trade_id": "T_ACTIVE_1",
                                "status": "POSITION_CONFIRMED",
                                "exit_order_id": "OID_EXIT_PROTECTED",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            canceled_ids: list[str] = []

            class _FakeSelectiveExec:
                def get_open_orders(self) -> list[dict[str, str]]:
                    return [
                        {"id": "OID_EXIT_PROTECTED", "side": "SELL"},
                        {"id": "OID_ENTRY_ANCHOR_1", "side": "BUY"},
                        {"id": "OID_ENTRY_ANCHOR_2", "side": "BUY"},
                    ]

                def cancel_order(self, oid: str) -> dict[str, object]:
                    canceled_ids.append(oid)
                    return {"canceled": oid}

                def cancel_all_orders(self) -> dict[str, object]:
                    raise AssertionError("Must NOT call blanket cancel_all_orders when exit order exists!")

            res_sel = paa_cli._cancel_open_clob_orders_out_of_band(
                data_dir,
                force_cancel_exits=False,
                executor_factory=lambda: _FakeSelectiveExec(),
            )
            self.assertTrue(res_sel["attempted"])
            self.assertTrue(res_sel["ok"])
            self.assertEqual(canceled_ids, ["OID_ENTRY_ANCHOR_1", "OID_ENTRY_ANCHOR_2"])
            self.assertEqual(res_sel["preserved_exit_order_ids"], ["OID_EXIT_PROTECTED"])

            # 2. Resume --include-trading MUST fail closed when ACCOUNTING_SAFEGUARD_ACTIVE.json exists!
            ks_path = data_dir / "KILL_SWITCH"
            ks_path.write_text("{}", encoding="utf-8")
            sg_path = data_dir / "paa" / "ACCOUNTING_SAFEGUARD_ACTIVE.json"
            sg_path.write_text(json.dumps({"active": True, "reason": "DRIFT_TEST"}), encoding="utf-8")

            with mock.patch.object(paa_cli, "PIPELINE_ROOT", root):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc_blocked = paa_cli.cmd_resume(
                        SimpleNamespace(include_trading=True, force_override_safeguard=False)
                    )
                self.assertEqual(rc_blocked, 2)
                self.assertTrue(ks_path.exists())

            # 3. Approvals CLI: blocks worker subprocesses (`PAA_SIGNING_DISABLED=1`), allows human TTY
            with mock.patch.object(paa_cli, "PIPELINE_ROOT", root), mock.patch.dict(
                os.environ, {"PAA_SIGNING_DISABLED": "1"}, clear=False
            ):
                buf_w = io.StringIO()
                with redirect_stdout(buf_w):
                    rc_worker = paa_cli.cmd_approvals(
                        SimpleNamespace(
                            approval_action="grant",
                            scope="LIVE_SERVICE_REDEPLOY",
                            approved_by="bot",
                            ttl_hours=2.0,
                            reason="bad",
                        )
                    )
                self.assertEqual(rc_worker, 3)

            with mock.patch.object(paa_cli, "PIPELINE_ROOT", root), mock.patch.dict(
                os.environ, {"PAA_SIGNING_DISABLED": "0", "PAA_WORKER_ROLE": ""}, clear=False
            ):
                buf_g = io.StringIO()
                with redirect_stdout(buf_g):
                    rc_grant = paa_cli.cmd_approvals(
                        SimpleNamespace(
                            approval_action="grant",
                            scope="LIVE_SERVICE_REDEPLOY",
                            approved_by="Anton",
                            ttl_hours=4.0,
                            reason="Verified flat redeploy",
                            _interactive_tty_verified=True,
                        )
                    )
                    self.assertEqual(rc_grant, 0)
                    ap_file = data_dir / "paa" / "approvals" / "LIVE_SERVICE_REDEPLOY.json"
                    self.assertTrue(ap_file.exists())

                    rc_cons = paa_cli.cmd_approvals(
                        SimpleNamespace(
                            approval_action="consume",
                            scope="LIVE_SERVICE_REDEPLOY",
                            release_id="REL_V60_TEST",
                            _interactive_tty_verified=True,
                        )
                    )
                    self.assertEqual(rc_cons, 0)
                    self.assertEqual(
                        json.loads(ap_file.read_text(encoding="utf-8")).get("consumed_by_release_id"),
                        "REL_V60_TEST",
                    )

                    rc_rev = paa_cli.cmd_approvals(
                        SimpleNamespace(
                            approval_action="revoke",
                            scope="LIVE_SERVICE_REDEPLOY",
                            reason="Done",
                            _interactive_tty_verified=True,
                        )
                    )
                    self.assertEqual(rc_rev, 0)
                    self.assertTrue(json.loads(ap_file.read_text(encoding="utf-8")).get("revoked"))

    def test_06_r09_r43_r10_r15_dynamic_allocator_and_infra_reconciliation(self) -> None:
        audit = run_counterfactual_audit()
        t_48 = audit["allocator_before_vs_after_by_nav"]["live_cash_48_70"]
        t_500 = audit["allocator_before_vs_after_by_nav"]["multileg_unlock_500_00"]

        self.assertGreater(t_48["v6_live_rnv_usd"], t_48["legacy_v5_live_rnv_usd"] * 2.5)
        self.assertNotIn("CAND_0_TRAP_30D_DOM", t_48["v6_live_accepted_ids"])
        self.assertNotIn("CAND_5_SUB500_3LEG_SEQ", t_48["v6_live_accepted_ids"])
        self.assertIn("CAND_5_SUB500_3LEG_SEQ", t_500["v6_live_accepted_ids"])
        self.assertEqual(len(t_48["v6_shadow_accepted_ids"]), 6)
        self.assertEqual(len(t_48["v6_research_accepted_ids"]), 6)

        ok_legacy, _ = passes_capital_velocity_hurdle(
            box_type="DOMINANCE",
            collat_usd=48.70,
            rem_tte_sec=720.0 * 3600.0,
            box_cost_net=0.9970,
            use_dynamic_opportunity_cost=False,
        )
        self.assertTrue(ok_legacy)
        ok_v6, rsn_v6 = passes_capital_velocity_hurdle(
            box_type="DOMINANCE",
            collat_usd=48.70,
            rem_tte_sec=720.0 * 3600.0,
            box_cost_net=0.9970,
            use_dynamic_opportunity_cost=True,
            utilization_frac=0.5,
        )
        self.assertFalse(ok_v6)
        self.assertIn("BELOW_DYNAMIC_OPPORTUNITY_COST", rsn_v6)

        ok_idle_26h, _ = passes_capital_velocity_hurdle(
            box_type="MACRO_DOMINANCE",
            collat_usd=48.70,
            rem_tte_sec=26.0 * 3600.0,
            box_cost_net=0.9714,
            use_dynamic_opportunity_cost=True,
            utilization_frac=0.0,
        )
        self.assertTrue(ok_idle_26h)

        econ = reconcile_infrastructure_expenses(
            window_hours=336.0,
            realized_trading_net_pnl_usd=18.246110,
            clips_executed_in_window=79,
            legacy_intraday_vm_hours_reported=7.27,
        )
        self.assertAlmostEqual(econ.true_marginal_trading_profit_usd, 18.246110, places=5)
        self.assertAlmostEqual(econ.sunk_fixed_vm_cost_usd, 11.512704, places=4)
        self.assertAlmostEqual(econ.full_cost_net_economic_profit_usd, 6.733406, places=4)
        self.assertGreater(econ.double_counted_error_eliminated_usd, 11.0)

    def test_07_r21_wallet_capabilities_and_r23_protocol_v2_fees_and_rounding(self) -> None:
        f_zero = verify_exact_polymarket_fee_and_rounding(
            {"feesEnabled": False, "takerBaseFee": 1000},
            price=0.50,
            requested_shares=10.0,
        )
        self.assertEqual(f_zero.rate, 0.0)
        self.assertEqual(f_zero.taker_fee_usd, 0.0)
        self.assertTrue(f_zero.two_decimal_usdc_invariant_ok)

        f_c15 = verify_exact_polymarket_fee_and_rounding(
            {"feesEnabled": True, "fee_schedule_name": "crypto_15_min"},
            price=0.50,
            requested_shares=20.0,
        )
        self.assertAlmostEqual(f_c15.taker_fee_usd, 20.0 * 0.25 * (0.25 ** 2), places=5)
        self.assertLess(f_c15.net_delivered_shares_on_buy, 20.0)
        self.assertTrue(f_c15.two_decimal_usdc_invariant_ok)

        f_lot = verify_exact_polymarket_fee_and_rounding(
            {"feesEnabled": False, "minimum_tick_size": 0.01},
            price=0.37,
            requested_shares=10.13,
        )
        self.assertTrue(f_lot.two_decimal_usdc_invariant_ok)
        self.assertEqual(f_lot.quantized_gross_shares, 10.0)

        cap_s3_pusd = validate_wallet_split_merge_capabilities(
            signature_type=3,
            protocol_generation="CTF_V1_PUSD",
        )
        self.assertTrue(cap_s3_pusd.merge_supported)
        self.assertTrue(cap_s3_pusd.batch_merge_supported)
        self.assertEqual(cap_s3_pusd.verified_constraints_and_defects, ())

        cap_v2_pm = validate_wallet_split_merge_capabilities(
            signature_type=3,
            protocol_generation="PROTOCOL_V2_POSITION_MANAGER",
        )
        self.assertFalse(cap_v2_pm.merge_supported)
        self.assertTrue(len(cap_v2_pm.verified_constraints_and_defects) >= 1)

    def test_08_r42_evidence_based_venue_readiness_vs_empty_wall_clock(self) -> None:
        empty_200h = evaluate_evidence_based_venue_readiness(
            venue_or_sleeve="EMPTY_CLOCK_VENUE",
            uncontaminated_live_l2_samples=5000,
            distinct_liquidity_regimes_observed=1,
            observed_live_hours=200.0,
            uptime_pct=99.8,
            api_error_rate_pct=0.2,
            p99_latency_ms=250.0,
            double_zero_or_clause_incidents=0,
            post_delay_simulated_trades=0,
            post_delay_net_executable_pnl_usd=0.0,
            settlement_and_custody_lifecycle_tested=False,
        )
        self.assertFalse(empty_200h.ready_for_owner_canary_proposal)

        proven_72h = evaluate_evidence_based_venue_readiness(
            venue_or_sleeve="PROVEN_CANARY_VENUE",
            uncontaminated_live_l2_samples=4800,
            distinct_liquidity_regimes_observed=4,
            observed_live_hours=72.0,
            uptime_pct=99.9,
            api_error_rate_pct=0.1,
            p99_latency_ms=180.0,
            double_zero_or_clause_incidents=0,
            post_delay_simulated_trades=52,
            post_delay_net_executable_pnl_usd=19.25,
            settlement_and_custody_lifecycle_tested=True,
        )
        self.assertTrue(proven_72h.ready_for_owner_canary_proposal)
        self.assertEqual(proven_72h.evidence_score_pct, 100.0)

    def test_09_zero_trust_permission_gate_and_lf_hygiene_all_v6_deliverables(self) -> None:
        pg = PermissionGate()
        v6_paths = [
            "src/polymarket_research/v6_restriction_and_capital_allocator.py",
            "src/polymarket_research/stage_c_zero_loss_velocity.py",
            "src/polymarket_research/holistic_strategy_governance.py",
            "scripts/paa_cli.py",
            "scripts/run_v6_counterfactual_opportunity_audit.py",
            "tests/test_v60_restriction_reassessment_and_allocator.py",
            "paa_staging/proposals/v60_restriction_remediation_package/APPLY_AND_ROLLBACK.md",
            "RESTRICTION_REGISTER_V6.md",
            "RESTRICTION_REMEDIATION_ROADMAP.md",
            "CAPITAL_EFFICIENCY_REASSESSMENT.md",
            "FULL_UNIVERSE_OPPORTUNITY_COST_REPORT.md",
            "RESTRICTION_CHANGE_QA_REPORT.md",
        ]
        existing_rel: list[str] = []
        diff_chunks: list[str] = []
        for rel in v6_paths:
            p = REPO_ROOT / rel
            if not p.exists():
                continue
            existing_rel.append(rel)
            raw = p.read_bytes()
            self.assertNotIn(b"\r\n", raw, f"CRLF detected in {rel}")
            self.assertGreater(len(raw), 0, f"Zero-byte file {rel}")
            txt = raw.decode("utf-8")
            diff_chunks.append(f"--- a/{rel}\n+++ b/{rel}\n@@ -0,0 +1,{txt.count(chr(10)) + 1} @@\n")
            for ln in txt.splitlines():
                diff_chunks.append(f"+{ln}\n")

        # Also verify LF hygiene + PermissionGate on newly added D-008..D-011 section of DECISIONS.md
        dec_raw = (REPO_ROOT / "DECISIONS.md").read_bytes()
        self.assertNotIn(b"\r\n", dec_raw, "CRLF detected in DECISIONS.md")
        dec_lines = dec_raw.decode("utf-8").splitlines()
        existing_rel.append("DECISIONS.md")
        diff_chunks.append("--- a/DECISIONS.md\n+++ b/DECISIONS.md\n@@ -45,0 +46,30 @@\n")
        for ln in dec_lines[45:]:
            diff_chunks.append(f"+{ln}\n")

        ok, violations = pg.inspect_candidate_diff(existing_rel, "".join(diff_chunks))
        self.assertTrue(ok, f"Zero-Trust PermissionGate violations: {violations}")
        self.assertEqual(violations, [])

    def test_10_owner_sovereignty_r26_to_r32_verified_vs_assumed_and_single_pass_execution(self) -> None:
        # 1. Verify R-26..R-32 registry distinguishes verified external gates from assumptions & never silently disables
        reg = assess_r26_to_r32_venue_restrictions(operator_jurisdiction="CA-ON", server_region="FI", nav_usd=48.83)
        self.assertEqual(set(reg.keys()), {"R-26", "R-27", "R-28", "R-29", "R-30", "R-31", "R-32"})
        for rid, rep in reg.items():
            self.assertFalse(rep.silent_disable_permitted, f"{rid} must never permit silent disabling")
            self.assertTrue(len(rep.verified_facts) >= 1, f"{rid} missing verified facts")
            self.assertTrue(len(rep.non_binding_assumptions_or_heuristics) >= 1, f"{rid} missing assumption separation")
            self.assertTrue(len(rep.lawful_remedies) >= 1, f"{rid} missing lawful remedies")

        # 2. Explicit Owner authorization overrides AI discretionary thresholds ($500 multileg, $150 CLASS_C, proposal gate, 25% cap) in ONE pass
        owner_live = evaluate_mode_specific_eligibility(
            ExecutionMode.LIVE,
            jurisdiction="CA-ON",
            venue_id="polymarket",
            venue_live_authorized_for_jurisdiction=True,
            owner_explicitly_authorized=True,
            opportunity_class=OpportunityClass.CLASS_C,
            sequential_clob_legs=3,
            is_atomic_or_inventory_locked=False,
            reconciled_liquid_nav_usd=48.70,
            directional_wfo_certified=False,
            live_promotion_approved=False,
        )
        self.assertTrue(owner_live.allowed)
        self.assertEqual(owner_live.reason, "LIVE_OWNER_AUTHORIZED_SINGLE_PASS")
        self.assertIn("LIVE_PROPOSAL_APPROVAL_GATE", owner_live.overridden_discretionary_gates)
        self.assertIn("LIVE_SUB500_MULTILEG_DEFAULT", owner_live.overridden_discretionary_gates)
        self.assertIn("LIVE_SUB150_CLASS_C_DEFAULT", owner_live.overridden_discretionary_gates)

        # Allocator respects Owner's explicit max_cluster_nav_pct=0.60 and CLASS_C authorization in a single pass
        alloc_owner = DynamicMarginalCapitalAllocator(max_cluster_nav_pct=0.60)
        self.assertAlmostEqual(alloc_owner.max_cluster_nav_pct, 0.60, places=4)
        cand_c = PortfolioCandidateSpec(
            candidate_id="OWNER_AUTH_CLASS_C_3LEG",
            family_code="CARRY",
            sleeve_name="OWNER_DIRECTED_CARRY",
            opportunity_class=OpportunityClass.CLASS_C,
            cluster_keys=("EVT:OWNER_CHOICE",),
            instrument_ids=("TOK_OWN_1", "TOK_OWN_2", "TOK_OWN_3"),
            capital_per_share_usd=0.80,
            worst_case_net_payoff_per_share_usd=0.0,
            expected_net_payoff_per_share_usd=0.08,
            fees_and_conversion_per_share_usd=0.005,
            max_executable_shares=25.0,
            nominal_maturity_hours=2.0,
            settlement_or_merge_hours=0.5,
            can_instant_merge_or_recycle=False,
            sequential_clob_legs=3,
            is_atomic_or_inventory_locked=False,
        )
        res_owner = alloc_owner.allocate(
            [cand_c],
            mode=ExecutionMode.LIVE,
            deployable_liquid_cash_usd=48.70,
            reconciled_nav_usd=48.83,
            jurisdiction="CA-ON",
            venue_id="polymarket",
            venue_live_authorized=True,
            live_promotion_approved=False,
            owner_explicitly_authorized=True,
        )
        self.assertTrue(res_owner.decisions[0].accepted)
        self.assertGreater(res_owner.deployed_cash_usd, 15.0)

        # 3. When an external restriction genuinely blocks (e.g. STX Ontario FI IP geofence, R-30), report exact blocker + lawful remedies (no silent disable)
        ext_blocked = alloc_owner.allocate(
            [cand_c],
            mode=ExecutionMode.LIVE,
            deployable_liquid_cash_usd=48.70,
            reconciled_nav_usd=48.83,
            jurisdiction="CA-ON",
            venue_id="stx_ontario",
            venue_live_authorized=False,
            owner_explicitly_authorized=True,
        )
        dec_blk = ext_blocked.decisions[0]
        self.assertFalse(dec_blk.accepted)
        self.assertIsNotNone(dec_blk.external_blocker_report)
        assert dec_blk.external_blocker_report is not None
        self.assertEqual(dec_blk.external_blocker_report.restriction_id, "R-30")
        self.assertFalse(dec_blk.external_blocker_report.silent_disable_permitted)
        self.assertTrue(any("Ontario" in r for r in dec_blk.external_blocker_report.lawful_remedies))

        # 4. Single-pass CLI bundle (`--all-owner-scopes`) grants all 4 governance scopes at once for human Owner, blocked for isolated workers
        with tempfile.TemporaryDirectory() as td:
            td_path = pathlib.Path(td)
            with mock.patch.object(paa_cli, "PIPELINE_ROOT", td_path):
                buf = io.StringIO()
                with mock.patch.dict(os.environ, {"PAA_SIGNING_DISABLED": "0", "PAA_WORKER_ROLE": ""}, clear=False), redirect_stdout(buf):
                    rc_bundle = paa_cli.cmd_approvals(
                        SimpleNamespace(
                            approval_action="grant",
                            scope="",
                            all_owner_scopes=True,
                            ttl_hours=4.0,
                            release_id="v60_single_pass",
                            git_sha=None,
                            approved_by="Anton",
                            reason="Owner single-pass authorization",
                            _interactive_tty_verified=True,
                        )
                    )
                self.assertEqual(rc_bundle, 0)
                payload = json.loads(buf.getvalue())
                self.assertEqual(payload["status"], "GRANTED_SINGLE_PASS_BUNDLE")
                self.assertEqual(len(payload["records"]), 4)


if __name__ == "__main__":
    unittest.main()

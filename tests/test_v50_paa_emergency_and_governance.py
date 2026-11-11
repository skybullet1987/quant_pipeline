"""
Regression & Security Verification Suite for DOMINUS v5.0 PAA Emergency Controls,
UMA-Frozen Restart Alignment, Staged Protected-File Proposals & Continuity Invariants
(`tests/test_v50_paa_emergency_and_governance.py`).

Pure stdlib `unittest` suite (zero `pytest` dependency; runs locally in <1s via
`"C:\\Program Files\\LibreOffice\\program\\python.exe" -m unittest tests/test_v50_paa_emergency_and_governance.py -v`).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import audit_losing_trades as alt
import scripts.paa_cli as paa_cli
from paa_staging.proposals.v50_owner_control_package import apply_or_rollback_owner_package as owner_pkg
from src.paa_os.permissions import PermissionGate


def _build_four_kmia_disputed_positions() -> Dict[str, Dict[str, Any]]:
    """Exact 4-position disputed `KMIA` Nov 7 production snapshot (`$50.51` cost, `exit_order_id=None`)."""
    return {
        "WS_SNIPE_Miami_KMIA_242960": {
            "box_type": "SINGLE_LEG_LOCK",
            "is_single_leg_lock": True,
            "is_dominance_box": False,
            "hold_to_maturity_lock": True,
            "is_legged_out_residual": None,
            "exit_order_status": "HOLD_TO_MATURITY_LOCK",
            "exit_order_id": None,
            "unwind_order_id": None,
            "is_liquidating": False,
            "candle_expiry_ts": 1794113999.0,
            "entry_ts": 1794085242.97,
            "umaResolutionStatus": "disputed",
        },
        "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
            "box_type": "MULTI_LEG_RESIDUAL",
            "is_single_leg_lock": True,
            "is_dominance_box": False,
            "hold_to_maturity_lock": False,
            "is_legged_out_residual": None,
            "exit_order_status": "EXIT_RECOVERY_REQUIRED",
            "exit_order_id": None,
            "unwind_order_id": None,
            "is_liquidating": False,
            "candle_expiry_ts": 1794113999.0,
            "entry_ts": 1794111898.51,
            "umaResolutionStatus": "disputed",
        },
        "WS_SNIPE_Miami_KMIA_688670": {
            "box_type": "SINGLE_LEG_LOCK",
            "is_single_leg_lock": True,
            "is_dominance_box": False,
            "hold_to_maturity_lock": True,
            "is_legged_out_residual": None,
            "exit_order_status": "HOLD_TO_MATURITY_LOCK",
            "exit_order_id": None,
            "unwind_order_id": None,
            "is_liquidating": False,
            "candle_expiry_ts": 1794113999.0,
            "entry_ts": 1794113688.67,
            "umaResolutionStatus": "disputed",
        },
        "WS_SNIPE_Miami_KMIA_837595": {
            "box_type": "SINGLE_LEG_LOCK",
            "is_single_leg_lock": True,
            "is_dominance_box": False,
            "hold_to_maturity_lock": True,
            "is_legged_out_residual": None,
            "exit_order_status": "HOLD_TO_MATURITY_LOCK",
            "exit_order_id": None,
            "unwind_order_id": None,
            "is_liquidating": False,
            "candle_expiry_ts": 1794113999.0,
            "entry_ts": 1794113837.66,
            "umaResolutionStatus": "disputed",
        },
    }


class TestPAAEmergencyStopAndResume(unittest.TestCase):
    """Verifies `POL-26` / `R-08` fixes in `scripts/paa_cli.py`."""

    def test_01_emergency_stop_autonomy_only_leaves_trading_and_kill_switch_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_root = Path(td)
            calls: List[List[str]] = []

            def fake_run(cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                calls.append(list(cmd))
                return subprocess.CompletedProcess(cmd, 0, stdout="inactive\n", stderr="")

            parser = paa_cli.build_parser()
            args = parser.parse_args(["emergency-stop", "--reason", "Pause LLM timers only"])
            buf = io.StringIO()
            with (
                mock.patch.object(paa_cli, "PIPELINE_ROOT", tmp_root),
                mock.patch.object(paa_cli.sys, "platform", "linux"),
                mock.patch.object(paa_cli, "_ensure_systemd_user_env"),
                mock.patch.object(paa_cli.subprocess, "run", side_effect=fake_run),
                redirect_stdout(buf),
            ):
                rc = paa_cli.cmd_emergency_stop(args)

            self.assertEqual(rc, 0)
            out = json.loads(buf.getvalue())
            self.assertTrue((tmp_root / "data/polymarket/paa/PAA_MASTER_STOP").exists())
            self.assertFalse((tmp_root / "data/polymarket/KILL_SWITCH").exists())
            self.assertIsNone(out["kill_switch_file"])
            self.assertFalse(out["clob_order_cancel"]["attempted"])
            stopped_svcs = [c[-1] for c in calls if len(c) >= 4 and c[2] == "stop"]
            self.assertIn("polymarket-paa-director.service", stopped_svcs)
            self.assertNotIn("polymarket-live-harvester.service", stopped_svcs)

    def test_02_emergency_stop_include_trading_writes_kill_switch_stops_cross_venue_and_cancels_orders(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_root = Path(td)
            data_dir = tmp_root / "data" / "polymarket"
            data_dir.mkdir(parents=True, exist_ok=True)
            # Populate exact 4 disputed KMIA positions (zero resting exit orders)
            (data_dir / "live_harvester_state.json").write_text(
                json.dumps({"active_positions": _build_four_kmia_disputed_positions()}),
                encoding="utf-8",
            )
            calls: List[List[str]] = []
            cancel_invocations = {"count": 0}

            class FakeExecutor:
                def cancel_all_orders(self) -> Dict[str, Any]:
                    cancel_invocations["count"] += 1
                    return {"canceled": ["0xmaker_bond1_order"]}

            def fake_run(cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                calls.append(list(cmd))
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            parser = paa_cli.build_parser()
            args = parser.parse_args(["emergency-stop", "--include-trading", "--reason", "Full halt test"])
            setattr(args, "_executor_factory", FakeExecutor)
            buf = io.StringIO()
            with (
                mock.patch.object(paa_cli, "PIPELINE_ROOT", tmp_root),
                mock.patch.object(paa_cli.sys, "platform", "linux"),
                mock.patch.object(paa_cli, "_ensure_systemd_user_env"),
                mock.patch.object(paa_cli.subprocess, "run", side_effect=fake_run),
                redirect_stdout(buf),
            ):
                rc = paa_cli.cmd_emergency_stop(args)

            self.assertEqual(rc, 0)
            out = json.loads(buf.getvalue())
            self.assertTrue((data_dir / "KILL_SWITCH").exists())
            self.assertEqual(cancel_invocations["count"], 1)
            self.assertTrue(out["clob_order_cancel"]["attempted"])
            self.assertTrue(out["clob_order_cancel"]["ok"])
            stopped_svcs = [c[-1] for c in calls if len(c) >= 4 and c[2] == "stop"]
            for unit in paa_cli.PAA_TRADING_AND_SHADOW_UNITS:
                self.assertIn(unit, stopped_svcs)

    def test_03_emergency_stop_protects_resting_exit_orders_unless_forced(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            (data_dir / "live_harvester_state.json").write_text(
                json.dumps(
                    {
                        "active_positions": {
                            "POS_WITH_TP": {"exit_order_id": "0xtp_order_123", "unwind_order_id": None}
                        }
                    }
                ),
                encoding="utf-8",
            )
            called = {"n": 0}

            class FakeExecutor:
                def cancel_all_orders(self) -> Dict[str, Any]:
                    called["n"] += 1
                    return {"canceled_all": True}

            res_skip = paa_cli._cancel_open_clob_orders_out_of_band(data_dir, executor_factory=FakeExecutor)
            self.assertFalse(res_skip["attempted"])
            self.assertEqual(res_skip["skipped_reason"], "ACTIVE_POSITION_EXIT_ORDER_PRESENT")
            self.assertEqual(called["n"], 0)

            res_force = paa_cli._cancel_open_clob_orders_out_of_band(
                data_dir, force_cancel_exits=True, executor_factory=FakeExecutor
            )
            self.assertTrue(res_force["attempted"])
            self.assertEqual(called["n"], 1)

    def test_04_resume_warns_when_kill_switch_active_and_clears_only_with_include_trading(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_root = Path(td)
            data_dir = tmp_root / "data" / "polymarket"
            paa_dir = data_dir / "paa"
            paa_dir.mkdir(parents=True, exist_ok=True)
            (paa_dir / "PAA_MASTER_STOP").write_text("{}", encoding="utf-8")
            (data_dir / "KILL_SWITCH").write_text("{}", encoding="utf-8")

            def fake_run_inactive(cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                if "is-active" in cmd:
                    return subprocess.CompletedProcess(cmd, 3, stdout="inactive\n", stderr="")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            parser = paa_cli.build_parser()
            args_autonomy = parser.parse_args(["resume"])
            buf1 = io.StringIO()
            with (
                mock.patch.object(paa_cli, "PIPELINE_ROOT", tmp_root),
                mock.patch.object(paa_cli.sys, "platform", "linux"),
                mock.patch.object(paa_cli, "_ensure_systemd_user_env"),
                mock.patch.object(paa_cli.subprocess, "run", side_effect=fake_run_inactive),
                redirect_stdout(buf1),
            ):
                paa_cli.cmd_resume(args_autonomy)

            out1 = json.loads(buf1.getvalue())
            self.assertFalse((paa_dir / "PAA_MASTER_STOP").exists())
            self.assertTrue((data_dir / "KILL_SWITCH").exists())
            self.assertTrue(out1["kill_switch_active"])
            self.assertIn("warning", out1)

            def fake_run_active(cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                if "is-active" in cmd:
                    return subprocess.CompletedProcess(cmd, 0, stdout="active\n", stderr="")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            args_full = parser.parse_args(["resume", "--include-trading"])
            buf2 = io.StringIO()
            with (
                mock.patch.object(paa_cli, "PIPELINE_ROOT", tmp_root),
                mock.patch.object(paa_cli.sys, "platform", "linux"),
                mock.patch.object(paa_cli, "_ensure_systemd_user_env"),
                mock.patch.object(paa_cli.subprocess, "run", side_effect=fake_run_active),
                redirect_stdout(buf2),
            ):
                paa_cli.cmd_resume(args_full)

            out2 = json.loads(buf2.getvalue())
            self.assertFalse((data_dir / "KILL_SWITCH").exists())
            self.assertTrue(out2["kill_switch_cleared"])
            self.assertFalse(out2["kill_switch_active"])
            self.assertEqual(out2["status"], "AUTONOMY_AND_TRADING_RESUMED")


class TestUMAFrozenRestartSafetyAlignment(unittest.TestCase):
    """Verifies `POL-07` / `R-06` restart safety across `audit_losing_trades.py`."""

    def test_05_four_kmia_disputed_positions_are_restart_safe_when_no_inflight_taker_orders(self) -> None:
        now_ts = 1794390000.0  # >72h after Nov 7 KMIA expiry 1794113999.0
        st = {
            "active_positions_count": 4,
            "active_position_ids": list(_build_four_kmia_disputed_positions().keys()),
            "active_positions": _build_four_kmia_disputed_positions(),
            "pre_split_inventory_state": {"active": False},
            "pending_entry_intents": {
                "MKR_6916999": {"live_maker_anchor_inflight": True, "notional_usd": 8.919}
            },
        }
        ok, blocking = alt.is_harvester_state_restart_safe(st, now_ts=now_ts)
        self.assertTrue(ok, f"Expected KMIA disputed locks to allow safe restart, got blocking={blocking}")
        self.assertEqual(blocking, [])

    def test_06_blocks_pre_expiry_liquidating_non_maker_intent_or_missing_details(self) -> None:
        now_ts = 1794390000.0
        # 1. Pre-expiry active position blocks restart
        pos_live = dict(_build_four_kmia_disputed_positions()["WS_SNIPE_Miami_KMIA_242960"])
        pos_live["candle_expiry_ts"] = now_ts + 900.0
        ok1, blk1 = alt.is_harvester_state_restart_safe(
            {"active_positions_count": 1, "active_positions": {"LIVE_PRE_EXP": pos_live}},
            now_ts=now_ts,
        )
        self.assertFalse(ok1)
        self.assertIn("LIVE_PRE_EXP", blk1)

        # 2. Non-maker in-flight entry intent blocks restart
        ok2, blk2 = alt.is_harvester_state_restart_safe(
            {
                "active_positions_count": 4,
                "active_positions": _build_four_kmia_disputed_positions(),
                "pending_entry_intents": {"D1_BOX_INFLIGHT": {"live_maker_anchor_inflight": False}},
            },
            now_ts=now_ts,
        )
        self.assertFalse(ok2)
        self.assertIn("PENDING_ENTRY_INTENT:D1_BOX_INFLIGHT", blk2)

        # 3. Missing `active_positions` dict when `active_positions_count > 0` fails closed
        with mock.patch.object(
            alt,
            "fetch_kraken_live_state",
            return_value={"service_status": "active", "state": {"active_positions_count": 2, "active_position_ids": ["X1", "X2"]}},
        ):
            with self.assertRaises(RuntimeError):
                alt.redeploy_daemon(force=False)


class TestStagedOwnerControlPackageAndPermissionGate(unittest.TestCase):
    """Verifies Zero-Trust `PermissionGate` compliance and staged `v50_owner_control_package` behavior."""

    def test_07_live_working_tree_protected_files_untouched_and_permission_gate_passes(self) -> None:
        gate = PermissionGate()
        ver = owner_pkg.verify_package_in_memory(repo_root=REPO_ROOT)
        self.assertTrue(ver["verified"])

        slice_files = [
            "AGENTS.md",
            "scripts/paa_cli.py",
            "audit_losing_trades.py",
            "tests/test_v50_paa_emergency_and_governance.py",
            "paa_staging/proposals/v50_owner_control_package/proposal_manifest.json",
            "paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py",
            "paa_staging/proposals/v50_owner_control_package/APPLY_AND_ROLLBACK.md",
            "paa_staging/proposals/v50_owner_control_package/01_permissions_pol05_scope_ttl_and_binary_guard.patch",
            "paa_staging/proposals/v50_owner_control_package/02_builder_and_deployer_pol07_uma_restart.patch",
            "paa_staging/proposals/v50_owner_control_package/03_autonomy_config_and_budget_pol10_vm_cost.patch",
        ]
        for r2_doc in (
            "POLICY_AUDIT.md",
            "RESTRICTION_REGISTER.md",
            "OWNER_CONTROL_MATRIX.md",
            "POLICY_PROFIT_IMPACT.md",
            "POLICY_REMEDIATION_PLAN.md",
        ):
            r2_fp = REPO_ROOT / r2_doc
            self.assertTrue(r2_fp.exists(), f"Missing R2 deliverable: {r2_doc}")
            self.assertEqual(r2_fp.read_bytes().count(b"\r\n"), 0, f"CRLF detected in {r2_doc}")
        synth_diff_lines: List[str] = []
        for rel in slice_files:
            fp = REPO_ROOT / rel
            self.assertTrue(fp.exists(), f"Missing expected deliverable: {rel}")
            raw = fp.read_bytes()
            self.assertEqual(raw.count(b"\r\n"), 0, f"CRLF detected in {rel}")
            synth_diff_lines.append(f"+++ b/{rel}")
            for ln in raw.decode("utf-8").splitlines():
                synth_diff_lines.append(f"+{ln}")

        ok, violations = gate.inspect_candidate_diff(slice_files, "\n".join(synth_diff_lines))
        self.assertTrue(ok, f"PermissionGate rejected slice with violations: {violations}")
        self.assertEqual(violations, [])

    def test_08_staged_owner_package_apply_scope_ttl_security_and_rollback_in_isolated_copy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_repo = Path(td)
            live_bkp_root = REPO_ROOT / "data" / "polymarket" / "paa" / "live_backups" / "v50_owner_control_package"
            manifest = json.loads(
                (REPO_ROOT / "paa_staging/proposals/v50_owner_control_package/proposal_manifest.json").read_text(encoding="utf-8")
            )
            base_sha_by_rel = {e["repo_path"]: e["baseline_lf_sha256"] for e in manifest["files"]}
            for rel in (
                "src/paa_os/permissions.py",
                "src/paa_os/builder_and_deployer.py",
                "src/paa_os/budget.py",
                "config/paa_autonomy_config.json",
            ):
                dst = tmp_repo / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                repo_src = REPO_ROOT / rel
                cur_sha = hashlib.sha256(repo_src.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                bkp_src = live_bkp_root / rel
                if cur_sha != base_sha_by_rel[rel] and bkp_src.exists():
                    shutil.copy2(bkp_src, dst)
                else:
                    shutil.copy2(repo_src, dst)

            # 1. Worker isolation guard MUST block `--apply` when PAA_SIGNING_DISABLED=1
            with mock.patch.dict(os.environ, {"PAA_SIGNING_DISABLED": "1"}, clear=False):
                with self.assertRaises(SystemExit) as ctx:
                    owner_pkg.apply_package(repo_root=tmp_repo)
                self.assertEqual(ctx.exception.code, 77)

            # 2. Human session applies cleanly and can roll back byte-for-byte
            orig_digests = {
                rel: hashlib.sha256((tmp_repo / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                for rel in ("src/paa_os/permissions.py", "src/paa_os/builder_and_deployer.py", "config/paa_autonomy_config.json", "src/paa_os/budget.py")
            }
            with mock.patch.dict(os.environ, {"PAA_SIGNING_DISABLED": "0", "PAA_WORKER_ROLE": ""}, clear=False):
                res_apply = owner_pkg.apply_package(repo_root=tmp_repo)
                self.assertEqual(res_apply["status"], "APPLIED")

                # Execute patched permissions.py in isolated namespace to verify POL-05 & POL-08
                patched_perm_ns: Dict[str, Any] = {"__file__": str(tmp_repo / "src/paa_os/permissions.py")}
                exec(
                    compile((tmp_repo / "src/paa_os/permissions.py").read_text(encoding="utf-8"), "permissions.py", "exec"),
                    patched_perm_ns,
                )
                PatchedGate = patched_perm_ns["PermissionGate"]
                approvals_dir = tmp_repo / "approvals"
                approvals_dir.mkdir(parents=True, exist_ok=True)
                pg = PatchedGate(
                    autonomy_cfg=json.loads((tmp_repo / "config/paa_autonomy_config.json").read_text(encoding="utf-8")),
                    approvals_dir=approvals_dir,
                )

                # Wildcard "*" without expires_at_utc on privileged scope MUST be rejected
                (approvals_dir / "wildcard_no_ttl.json").write_text(
                    json.dumps(
                        {
                            "approved": True,
                            "approved_by": "anton",
                            "target_id": "*",
                            "scopes": ["NEW_LIVE_TRADING_ACTIVATION"],
                        }
                    ),
                    encoding="utf-8",
                )
                rc_ok = {
                    "hard_ruin_floor_usd": 42.0,
                    "max_daily_directional_loss_usd": 16.57,
                    "max_consecutive_directional_losses": 4,
                }
                b_cfg = {"risk_controller": rc_ok, "riskless_boxes": {"paused_riskless_sleeves": ["CAL1", "SOC2"]}}
                c_cfg = {"risk_controller": rc_ok, "riskless_boxes": {"paused_riskless_sleeves": ["SOC2"]}}
                ok_no_ttl, _ = pg.inspect_config_envelope(b_cfg, c_cfg, release_id="rel_001")
                self.assertFalse(ok_no_ttl)

                # Target-bound single-scope NEW_LIVE_TRADING_ACTIVATION with valid TTL clears unpause ONLY (fixes AND-scope bug!)
                fut_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
                (approvals_dir / "single_scope_valid.json").write_text(
                    json.dumps(
                        {
                            "approved": True,
                            "approved_by": "anton",
                            "target_id": "rel_001",
                            "expires_at_utc": fut_iso,
                            "scopes": ["NEW_LIVE_TRADING_ACTIVATION"],
                        }
                    ),
                    encoding="utf-8",
                )
                ok_single, v_single = pg.inspect_config_envelope(b_cfg, c_cfg, release_id="rel_001")
                self.assertTrue(ok_single, f"Single-scope approval should clear sleeve unpause, got {v_single}")

                # Same NEW_LIVE_TRADING_ACTIVATION approval MUST NOT clear a RISK_FLOOR_WEAKENED or EXPOSURE_INCREASED violation!
                ok_floor, _ = pg.inspect_config_envelope(
                    {"risk_controller": rc_ok},
                    {"risk_controller": {**rc_ok, "hard_ruin_floor_usd": 35.0}},
                    release_id="rel_001",
                )
                self.assertFalse(ok_floor)
                ok_exp_blocked, _ = pg.inspect_config_envelope(
                    {"risk_controller": rc_ok},
                    {"risk_controller": {**rc_ok, "max_daily_directional_loss_usd": 25.0}},
                    release_id="rel_001",
                )
                self.assertFalse(ok_exp_blocked)

                # Non-overridable SELF_APPROVAL_TAMPERING_FORBIDDEN remains 100% blocked even with all scopes approved!
                (approvals_dir / "all_scopes.json").write_text(
                    json.dumps(
                        {
                            "approved": True,
                            "approved_by": "anton",
                            "target_id": "rel_001",
                            "expires_at_utc": fut_iso,
                            "scopes": [
                                "INCREASE_CAPITAL_EXPOSURE",
                                "NEW_LIVE_TRADING_ACTIVATION",
                                "CREDENTIAL_OR_PERMISSION_EXPANSION",
                                "LIVE_PRODUCTION_PROMOTION",
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                ok_tamper, v_tamper = pg.inspect_candidate_diff(
                    ["data/polymarket/paa/approvals/forged.json"],
                    "+{}",
                    release_id="rel_001",
                )
                self.assertFalse(ok_tamper)
                self.assertTrue(any(v.startswith("SELF_APPROVAL_TAMPERING_FORBIDDEN:") for v in v_tamper))

                # Rollback restores exact baseline digests
                res_rb = owner_pkg.rollback_package(repo_root=tmp_repo)
                self.assertEqual(res_rb["status"], "ROLLED_BACK")
                for rel, exp_sha in orig_digests.items():
                    cur_sha = hashlib.sha256((tmp_repo / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                    self.assertEqual(cur_sha, exp_sha, f"Rollback digest mismatch on {rel}")


if __name__ == "__main__":
    unittest.main()

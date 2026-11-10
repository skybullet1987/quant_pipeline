"""
Action #4 Independent Deployment Gate, Secret-Free Credential Validation,
Systemd Hardening, and Network-Disabled Service Startup Integration Suite
(`tests/test_action4_shadow_service_and_gates.py`).

Executes 100% offline (`0` external network calls, `0` credentials).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

for _opt_net_mod in ("requests", "aiohttp"):
    try:
        __import__(_opt_net_mod)
    except ImportError:
        _stub = types.ModuleType(_opt_net_mod)
        _stub.Session = object  # type: ignore[attr-defined]
        _stub.ClientSession = object  # type: ignore[attr-defined]
        sys.modules[_opt_net_mod] = _stub

from src.polymarket_research.cross_venue_riskless_shadow import (
    HonestCrossVenueShadowEngine,
    LiveCrossVenueShadowCollector,
    ReadOnlyHttpClient,
)
from src.polymarket_research.cross_venue_shadow_deployment_gates import (
    EX_CONFIG,
    evaluate_all_venues_authorization,
    run_offline_shadow_cycle,
    validate_python_runtime_dependencies,
    validate_shadow_env_dict,
    validate_shadow_env_file,
    validate_systemd_unit_text,
)


class TestAction4ShadowServiceAndGates(unittest.TestCase):
    def test_01_systemd_unit_and_env_template_audit(self) -> None:
        unit_path = REPO_ROOT / "systemd" / "polymarket-cross-venue-shadow.service"
        self.assertTrue(unit_path.exists())
        unit_rep = validate_systemd_unit_text(unit_path.read_text(encoding="utf-8"), str(unit_path))
        self.assertTrue(unit_rep.valid, msg=f"Systemd unit audit failed: {unit_rep.errors}")

        tpl_path = REPO_ROOT / "systemd" / "polymarket-shadow.env.template"
        self.assertTrue(tpl_path.exists())
        parsed, env_rep = validate_shadow_env_file(tpl_path, enforce_posix_0600=False)
        self.assertTrue(env_rep.valid, msg=f"Template validation failed: {env_rep.errors}")
        self.assertEqual(parsed.get("DOMINUS_NETWORK_MODE"), "offline")
        self.assertEqual(parsed.get("PREDICT_FUN_API_KEY"), "")
        self.assertEqual(parsed.get("SX_BET_API_KEY"), "")

        deps = validate_python_runtime_dependencies()
        self.assertTrue(deps["stdlib_ready"])

    def test_02_secret_free_env_validator_blocks_private_keys_secrets_and_revoked_digests(self) -> None:
        # 1. Signing/wallet secrets MUST fail closed without echoing secret content
        fake_secret = "SYNTHETIC_TEST_SECRET_VALUE_DO_NOT_ECHO_999"
        rep_priv = validate_shadow_env_dict(
            {
                "POLY_PRIVATE_KEY": fake_secret,
                "LIMITLESS_API_SECRET": fake_secret,
            }
        )
        self.assertFalse(rep_priv.valid)
        self.assertIn("FORBIDDEN_SIGNING_SECRET_IN_SHADOW_ENV:POLY_PRIVATE_KEY", rep_priv.errors)
        self.assertIn("FORBIDDEN_SIGNING_SECRET_IN_SHADOW_ENV:LIMITLESS_API_SECRET", rep_priv.errors)
        for err in rep_priv.errors:
            self.assertNotIn(fake_secret, err)

        # 2. Raw 64-hex private key accidentally dropped into a read-only variable MUST fail closed
        rep_hex = validate_shadow_env_dict({"SX_BET_API_KEY": "0x" + "ab" * 32})
        self.assertFalse(rep_hex.valid)
        self.assertIn("SUSPECTED_RAW_HEX_PRIVATE_KEY_IN:SX_BET_API_KEY", rep_hex.errors)

        # 3. Placeholder values and revoked SHA-256 digests MUST fail closed
        rep_ph = validate_shadow_env_dict({"PREDICT_FUN_API_KEY": "YOUR_KEY_HERE_12345"})
        self.assertFalse(rep_ph.valid)
        self.assertIn("PLACEHOLDER_CREDENTIAL_REJECTED:PREDICT_FUN_API_KEY", rep_ph.errors)

        synthetic_revoked = "SyntheticTestReadOnlyKey_RevokedToken987654"
        revoked_sha = hashlib.sha256(synthetic_revoked.encode("utf-8")).hexdigest()
        rep_rev = validate_shadow_env_dict(
            {
                "SX_BET_API_KEY": synthetic_revoked,
                "DOMINUS_REVOKED_KEY_SHA256_LIST": revoked_sha,
            }
        )
        self.assertFalse(rep_rev.valid)
        self.assertIn("REVOKED_CREDENTIAL_SHA256_REJECTED:SX_BET_API_KEY", rep_rev.errors)
        for err in rep_rev.errors:
            self.assertNotIn(synthetic_revoked, err)

        rep_bad_sha = validate_shadow_env_dict({"DOMINUS_REVOKED_KEY_SHA256_LIST": "not_a_sha256"})
        self.assertFalse(rep_bad_sha.valid)
        self.assertIn("INVALID_REVOKED_SHA256_DIGEST_ENTRY", rep_bad_sha.errors)

        # 4. Insecure file permissions (`permissions_ok=False`) MUST fail closed
        rep_perm = validate_shadow_env_dict(
            {"DOMINUS_NETWORK_MODE": "offline"},
            permissions_ok=False,
            observed_mode_octal="0o644",
        )
        self.assertFalse(rep_perm.valid)
        self.assertIn("INSECURE_FILE_PERMISSIONS:0o644_EXPECTED_0600", rep_perm.errors)

    def test_03_per_venue_authorization_matrix_separates_public_data_trading_and_credentials(self) -> None:
        # Case A: CA-ON operator + FI server in `live_public`:
        # - Polymarket, Limitless, SX Bet (keyless public OBv3 REST), & ForecastEx (CFTC portal): PUBLIC_DATA_AUTHORIZED!
        # - STX Ontario: RESTRICTED from FI server (`iGO` requires direct CA-ON presence unless STX Apps Data token)
        ca_on_fi = evaluate_all_venues_authorization(
            {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                "DOMINUS_SERVER_REGION": "FI",
                "DOMINUS_WORKSTATION_GEOBLOCKED": "1",
            }
        )
        for pub_ok in ("polymarket", "limitless", "sx_bet", "forecastex"):
            self.assertTrue(ca_on_fi[pub_ok].effective_authorized, msg=pub_ok)
            self.assertEqual(ca_on_fi[pub_ok].public_data_state, "PUBLIC_DATA_AUTHORIZED", msg=pub_ok)
        self.assertEqual(ca_on_fi["polymarket"].trading_state, "RESTRICTED")
        self.assertEqual(ca_on_fi["polymarket"].authenticated_account_state, "RESTRICTED")
        self.assertEqual(ca_on_fi["limitless"].trading_state, "RESTRICTED")
        self.assertEqual(ca_on_fi["limitless"].authenticated_account_state, "RESTRICTED")
        self.assertEqual(ca_on_fi["sx_bet"].market_data_access, "AUTHORIZED_REST_ONLY")
        self.assertEqual(ca_on_fi["sx_bet"].shadow_research_access, "AUTHORIZED_LIVE")
        self.assertEqual(ca_on_fi["sx_bet"].live_trading_access, "RESTRICTED")
        self.assertEqual(ca_on_fi["sx_bet"].authenticated_account_state, "RESTRICTED")

        self.assertTrue(ca_on_fi["stx_ontario"].effective_authorized)
        self.assertEqual(ca_on_fi["stx_ontario"].public_data_state, "PUBLIC_DATA_AUTHORIZED")
        self.assertEqual(ca_on_fi["stx_ontario"].readonly_api_state, "CREDENTIALS_REQUIRED")
        self.assertEqual(ca_on_fi["stx_ontario"].market_data_access, "AUTHORIZED_LIVE")
        self.assertEqual(ca_on_fi["stx_ontario"].live_trading_access, "RESTRICTED")
        self.assertEqual(ca_on_fi["stx_ontario"].capability_flags["PUBLIC_DATA"], "AUTHORIZED_LIVE")
        self.assertEqual(ca_on_fi["stx_ontario"].capability_flags["REALTIME_DATA"], "AUTHORIZED_LIVE")
        self.assertEqual(ca_on_fi["stx_ontario"].capability_flags["AUTHENTICATED_DATA"], "CREDENTIALS_PENDING")
        self.assertEqual(ca_on_fi["stx_ontario"].capability_flags["LIVE_ORDER_EXECUTION"], "RESTRICTED")
        self.assertEqual(ca_on_fi["stx_ontario"].venue_classification, "PARTIALLY_ACTIVE")

        # Predict.fun in CA-ON + FI without key: CREDENTIALS_REQUIRED for read-only Content Features; trading RESTRICTED
        self.assertFalse(ca_on_fi["predict_fun"].effective_authorized)
        self.assertEqual(ca_on_fi["predict_fun"].public_data_state, "CREDENTIALS_REQUIRED")
        self.assertEqual(ca_on_fi["predict_fun"].readonly_api_state, "CREDENTIALS_REQUIRED")
        self.assertEqual(ca_on_fi["predict_fun"].market_data_access, "CREDENTIALS_REQUIRED")
        self.assertEqual(ca_on_fi["predict_fun"].live_trading_access, "RESTRICTED")

        # Case A2: Predict.fun in CA-ON + FI WITH `PREDICT_FUN_API_KEY` unlocks read-only Content Features (`MARKET_DATA_ACCESS`)
        #          with ZERO fake `PREDICT_FUN_DATA_LICENSE_ID` required, while keeping `LIVE_TRADING_ACCESS` & wallet JWT RESTRICTED!
        pf_mainnet_ca_on = evaluate_all_venues_authorization(
            {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                "DOMINUS_SERVER_REGION": "FI",
                "PREDICT_FUN_ENV": "mainnet",
                "PREDICT_FUN_API_KEY": "pred_sk_test_readonly_content_token_123456",
            }
        )
        self.assertTrue(pf_mainnet_ca_on["predict_fun"].effective_authorized)
        self.assertEqual(pf_mainnet_ca_on["predict_fun"].verified_outcome_state, "AUTHORIZED_LIVE")
        self.assertEqual(pf_mainnet_ca_on["predict_fun"].market_data_access, "AUTHORIZED_LIVE")
        self.assertEqual(pf_mainnet_ca_on["predict_fun"].shadow_research_access, "AUTHORIZED_LIVE")
        self.assertEqual(pf_mainnet_ca_on["predict_fun"].live_trading_access, "RESTRICTED")
        self.assertEqual(pf_mainnet_ca_on["predict_fun"].authenticated_account_state, "RESTRICTED")
        self.assertEqual(pf_mainnet_ca_on["predict_fun"].trading_state, "RESTRICTED")

        # Case B: Predict.fun `PREDICT_FUN_ENV=testnet` activates unauthenticated `TESTNET_SANDBOX` while mainnet stays `CREDENTIALS_PENDING`
        pf_tn = evaluate_all_venues_authorization(
            {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                "DOMINUS_SERVER_REGION": "FI",
                "PREDICT_FUN_ENV": "testnet",
            }
        )
        self.assertTrue(pf_tn["predict_fun"].effective_authorized)
        self.assertEqual(pf_tn["predict_fun"].status_code, "AUTHORIZED_TESTNET_SANDBOX_ONLY")
        self.assertEqual(pf_tn["predict_fun"].public_data_state, "PUBLIC_DATA_AUTHORIZED")
        self.assertEqual(pf_tn["predict_fun"].readonly_api_state, "CREDENTIALS_REQUIRED")
        self.assertEqual(pf_tn["predict_fun"].market_data_access, "AUTHORIZED_SANDBOX_ONLY")
        self.assertEqual(pf_tn["predict_fun"].trading_state, "RESTRICTED")

        # Case C: STX Ontario in `CA-ON` direct MUST NOT treat a bare `STX_API_KEY_ID` without a `0600` Ed25519 key file as authorized!
        from src.polymarket_research.cross_venue_connectors import generate_stx_ed25519_keypair

        with tempfile.TemporaryDirectory() as tmp_k:
            key_file = Path(tmp_k) / "stx_ed25519.pem"
            generate_stx_ed25519_keypair(key_file)
            stx_key_id_only = evaluate_all_venues_authorization(
                {
                    "DOMINUS_NETWORK_MODE": "live_public",
                    "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                    "DOMINUS_SERVER_REGION": "CA-ON",
                    "STX_API_KEY_ID": "stx_key_id_without_private_key",
                }
            )
            self.assertFalse(stx_key_id_only["stx_ontario"].effective_authorized)
            self.assertEqual(stx_key_id_only["stx_ontario"].readonly_api_state, "CREDENTIALS_REQUIRED")
            self.assertTrue(stx_key_id_only["stx_ontario"].status_code.startswith("CREDENTIALS_REQUIRED"))

            stx_complete = evaluate_all_venues_authorization(
                {
                    "DOMINUS_NETWORK_MODE": "live_public",
                    "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                    "DOMINUS_SERVER_REGION": "CA-ON",
                    "STX_API_KEY_ID": "stx_key_id_complete",
                    "STX_ED25519_KEY_FILE": str(key_file),
                }
            )
            self.assertTrue(stx_complete["stx_ontario"].effective_authorized)
            self.assertEqual(stx_complete["stx_ontario"].readonly_api_state, "READONLY_API_AUTHORIZED")

        # Case D: Written SX Bet market-data license (`SX_BET_WRITTEN_DATA_LICENSE_ID`) selectively unblocks read-only SX Bet while keeping trading RESTRICTED
        sx_lic = evaluate_all_venues_authorization(
            {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                "DOMINUS_SERVER_REGION": "FI",
                "SX_BET_WRITTEN_DATA_LICENSE_ID": "SX-DATA-LIC-2026-001",
            }
        )
        self.assertTrue(sx_lic["sx_bet"].effective_authorized)
        self.assertEqual(sx_lic["sx_bet"].public_data_state, "PUBLIC_DATA_AUTHORIZED")
        self.assertEqual(sx_lic["sx_bet"].trading_state, "RESTRICTED")

        # Case E: Eligible operator (`SE`) + `DOMINUS_ENABLED_VENUES` selective filter
        se_fi = evaluate_all_venues_authorization(
            {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "SE",
                "DOMINUS_SERVER_REGION": "FI",
                "DOMINUS_WORKSTATION_GEOBLOCKED": "0",
                "DOMINUS_ENABLED_VENUES": "polymarket,sx_bet,limitless",
            }
        )
        self.assertTrue(se_fi["polymarket"].effective_authorized)
        self.assertTrue(se_fi["sx_bet"].effective_authorized)
        self.assertTrue(se_fi["limitless"].effective_authorized)
        self.assertFalse(se_fi["predict_fun"].effective_authorized)
        self.assertEqual(se_fi["predict_fun"].status_code, "DISABLED_BY_CONFIG")

    def test_04_network_disabled_http_fence_and_collector_venue_isolation(self) -> None:
        async def _check_fence() -> None:
            async with ReadOnlyHttpClient(network_disabled=True) as client:
                with self.assertRaises(RuntimeError):
                    await client.get_json("https://api.limitless.exchange/markets/active?limit=25")

        asyncio.run(_check_fence())

        with tempfile.TemporaryDirectory() as tmp:
            eng = HonestCrossVenueShadowEngine(clip_notional_usd=25.0, data_dir=Path(tmp))
            col = LiveCrossVenueShadowCollector(
                eng,
                authorized_venues=set(),
                blocked_venue_reasons={
                    "polymarket": "TEST_BLOCK_POLY",
                    "limitless": "TEST_BLOCK_LIM",
                    "sx_bet": "TEST_BLOCK_SX",
                    "predict_fun": "TEST_BLOCK_PRED",
                },
            )
            res = asyncio.run(col.run_single_cycle())
            self.assertEqual(res["matched_cross_venue_pairs"], 0)
            self.assertEqual(eng.venue_health["limitless"]["status"], "AUTH_BLOCKED")
            self.assertEqual(eng.venue_health["sx_bet"]["reason"], "TEST_BLOCK_SX")

    def test_05_cli_offline_startup_and_fail_closed_ex_config_78(self) -> None:
        from scripts.shadow_cross_venue_riskless_probe import main as shadow_probe_main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            # 1. CLI startup in `--network-disabled` mode must ingest L2 fixtures, lock boxes, and write SHA-256 health
            buf_ok = io.StringIO()
            with mock.patch.dict(os.environ, {"DOMINUS_NETWORK_MODE": "offline"}, clear=False):
                with contextlib.redirect_stdout(buf_ok):
                    rc_ok = shadow_probe_main(
                        [
                            "--network-disabled",
                            "--once",
                            "--json",
                            "--data-dir",
                            str(tmp_dir),
                        ]
                    )
            self.assertEqual(rc_ok, 0)
            summary = json.loads(buf_ok.getvalue())
            self.assertEqual(summary["network_mode"], "offline")
            self.assertEqual(summary["network_calls_made"], 0)
            self.assertGreaterEqual(summary["matched_cross_venue_pairs"], 4)
            self.assertGreaterEqual(summary["graduation_report"]["locked_complete_baskets"], 1)
            self.assertEqual(summary["graduation_report"]["double_zero_incidents"], 0)

            report_file = tmp_dir / "shadow_graduation_report.json"
            funnel_file = tmp_dir / "cross_venue_funnel.jsonl"
            health_file = tmp_dir / "shadow_service_health.json"
            self.assertTrue(report_file.exists())
            self.assertTrue(funnel_file.exists())
            self.assertTrue(health_file.exists())

            health_json = json.loads(health_file.read_text(encoding="utf-8"))
            rep_json = json.loads(report_file.read_text(encoding="utf-8"))
            expected_sha = hashlib.sha256(json.dumps(rep_json, sort_keys=True).encode("utf-8")).hexdigest()
            self.assertEqual(health_json["graduation_report_sha256"], expected_sha)
            self.assertTrue(health_json["service_healthy"])

            # 2. CLI startup in `--enforce-venue-auth` live mode when all enabled venues are RESTRICTED MUST exit 78 (`EX_CONFIG`) cleanly
            blocked_dir = tmp_dir / "blocked_run"
            blocked_env = {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                "DOMINUS_SERVER_REGION": "FI",
                "DOMINUS_ENABLED_VENUES": "predict_fun,stx_ontario",
                "PREDICT_FUN_ENV": "mainnet",
                "STX_API_KEY_ID": "incomplete_key_id_without_ed25519_file",
            }
            with mock.patch.dict(os.environ, blocked_env, clear=False):
                rc_blk = shadow_probe_main(
                    [
                        "--enforce-venue-auth",
                        "--once",
                        "--data-dir",
                        str(blocked_dir),
                    ]
                )
            self.assertEqual(rc_blk, EX_CONFIG)
            blk_health = json.loads((blocked_dir / "shadow_service_health.json").read_text(encoding="utf-8"))
            self.assertFalse(blk_health["venue_authorization"]["predict_fun"]["effective_authorized"])
            self.assertFalse(blk_health["venue_authorization"]["stx_ontario"]["effective_authorized"])

    def test_06_seven_scope_authorization_and_five_verified_outcome_states(self) -> None:
        from src.polymarket_research.cross_venue_shadow_deployment_gates import (
            AUTHORIZATION_SCOPES,
            VERIFIED_OUTCOME_STATES,
            evaluate_all_venues_authorization,
        )

        self.assertEqual(
            AUTHORIZATION_SCOPES,
            (
                "PUBLIC_REST",
                "PUBLIC_WEBSOCKET",
                "AUTHENTICATED_READONLY",
                "ACCOUNT_PRIVATE",
                "TRADING",
                "INSTITUTIONAL_DATA_LICENSE",
                "SERVER_HOSTING",
            ),
        )

        # 1. Production CA-ON + FI shadow baseline (with PREDICT_FUN_ENV=testnet sandbox)
        base_env = {
            "DOMINUS_NETWORK_MODE": "live_public",
            "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
            "DOMINUS_SERVER_REGION": "FI",
            "DOMINUS_WORKSTATION_GEOBLOCKED": "1",
            "PREDICT_FUN_ENV": "testnet",
            "FORECASTEX_PUBLIC_PORTAL_AUTHORIZED": "1",
        }
        decs = evaluate_all_venues_authorization(base_env)
        for v, dec in decs.items():
            self.assertIn(dec.verified_outcome_state, VERIFIED_OUTCOME_STATES, msg=v)
            self.assertEqual(set(dec.scope_permissions.keys()), set(AUTHORIZATION_SCOPES), msg=v)

        # Limitless: PUBLIC_REST + PUBLIC_WEBSOCKET + SERVER_HOSTING are AUTHORIZED_LIVE; trading/HMAC RESTRICTED
        lim = decs["limitless"]
        self.assertEqual(lim.verified_outcome_state, "AUTHORIZED_LIVE")
        self.assertEqual(lim.scope_permissions["PUBLIC_REST"], "AUTHORIZED_LIVE")
        self.assertEqual(lim.scope_permissions["PUBLIC_WEBSOCKET"], "AUTHORIZED_LIVE")
        self.assertEqual(lim.scope_permissions["SERVER_HOSTING"], "AUTHORIZED_LIVE")
        self.assertEqual(lim.scope_permissions["AUTHENTICATED_READONLY"], "RESTRICTED")
        self.assertEqual(lim.scope_permissions["TRADING"], "RESTRICTED")

        # Predict.fun: TESTNET_SANDBOX MUST NEVER report verified_outcome_state == AUTHORIZED_LIVE!
        pf = decs["predict_fun"]
        self.assertEqual(pf.verified_outcome_state, "CREDENTIALS_PENDING")
        self.assertEqual(pf.scope_permissions["PUBLIC_REST"], "RESTRICTED")
        self.assertEqual(pf.scope_permissions["SERVER_HOSTING"], "AUTHORIZED_LIVE")
        self.assertEqual(pf.market_data_access, "AUTHORIZED_SANDBOX_ONLY")
        self.assertEqual(pf.live_trading_access, "RESTRICTED")

        # Pending inquiry transitions Predict.fun (without key) to AUTHORIZATION_PENDING; SX Bet public REST is already AUTHORIZED_REST_ONLY
        pend_decs = evaluate_all_venues_authorization(
            {
                **base_env,
                "PREDICT_FUN_BUILDER_APP_ID": "PF-INQ-2026-01",
                "SX_BET_DATA_INQUIRY_ID": "SX-INQ-2026-01",
            }
        )
        self.assertEqual(pend_decs["predict_fun"].verified_outcome_state, "AUTHORIZATION_PENDING")
        self.assertEqual(pend_decs["sx_bet"].verified_outcome_state, "AUTHORIZED_REST_ONLY")
        self.assertEqual(pend_decs["sx_bet"].scope_permissions["PUBLIC_REST"], "AUTHORIZED_LIVE")
        self.assertEqual(pend_decs["sx_bet"].scope_permissions["AUTHENTICATED_READONLY"], "CREDENTIALS_PENDING")
        self.assertEqual(pend_decs["sx_bet"].scope_permissions["TRADING"], "RESTRICTED")

        # 2. Eligible non-restricted operator (SE + FI): SX Bet needs ZERO written license!
        se_keyless = evaluate_all_venues_authorization(
            {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "SE",
                "DOMINUS_SERVER_REGION": "FI",
                "DOMINUS_WORKSTATION_GEOBLOCKED": "0",
                "PREDICT_FUN_ENV": "mainnet",
            }
        )
        self.assertEqual(se_keyless["sx_bet"].verified_outcome_state, "AUTHORIZED_REST_ONLY")
        self.assertTrue(se_keyless["sx_bet"].effective_authorized)
        self.assertEqual(se_keyless["sx_bet"].scope_permissions["PUBLIC_REST"], "AUTHORIZED_LIVE")
        self.assertEqual(se_keyless["predict_fun"].verified_outcome_state, "CREDENTIALS_PENDING")

        se_with_keys = evaluate_all_venues_authorization(
            {
                "DOMINUS_NETWORK_MODE": "live_authenticated",
                "DOMINUS_OPERATOR_JURISDICTION": "SE",
                "DOMINUS_SERVER_REGION": "FI",
                "DOMINUS_WORKSTATION_GEOBLOCKED": "0",
                "PREDICT_FUN_ENV": "mainnet",
                "PREDICT_FUN_API_KEY": "pf_fresh_readonly_test_token_9999",
                "SX_BET_API_KEY": "sx_fresh_readonly_test_token_9999",
            }
        )
        self.assertEqual(se_with_keys["sx_bet"].verified_outcome_state, "AUTHORIZED_LIVE")
        self.assertEqual(se_with_keys["predict_fun"].verified_outcome_state, "AUTHORIZED_LIVE")


if __name__ == "__main__":
    unittest.main()

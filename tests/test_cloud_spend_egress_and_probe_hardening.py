#!/usr/bin/env python3
"""
Regression & safety tests for Cloud Spend Egress & Probe Hardening (Ideas 1 & 2):
  1. Alpha-124 Shadow Daemon (`alpha_124_shadow_daemon.py`):
     - Trusts verified CLOB WebSocket books on live shards (`<= 5.0s` shard heartbeat) up to `120s`
       quiet age with `0` redundant `POST /books` calls, without mutating `ws_entry[0]` (`ws_books_ts`).
     - Falls back to REST reconciliation when shard silence `> 5.0s`, token is `_ws_rest_seeded`,
       or quiet age `> 120s`, then suppresses repeat REST calls via `_ws_last_reconciled_ts`.
     - Caches unsubscribed REST `/books` responses (`12s` TTL) and empty/delisted tokens (`20s` TTL).
  2. Command Center (`scripts/dominus_command_center.py`):
     - Reuses `_PERSIST` across persistent SSH probe iterations (`0` `PolymarketLiveExecutor` leaks,
       `PM_ENABLE_TLS_KEEPALIVE=0`, `PM_ENABLE_USER_WS=0`, `Connection: close`).
     - Pauses background browser polling when `document.hidden` is true and refreshes on `visibilitychange`.
     - Passes Zero-Trust `PermissionGate().inspect_candidate_diff(...)`.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import time
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_alpha124_daemon_cls() -> Any:
    added_shims: List[str] = []
    for mod_name in ("requests", "aiohttp"):
        try:
            __import__(mod_name)
        except ModuleNotFoundError:
            shim = types.ModuleType(mod_name)
            if mod_name == "aiohttp":
                shim.ClientTimeout = lambda **kw: kw  # type: ignore[attr-defined]
                shim.ClientSession = object  # type: ignore[attr-defined]
                shim.TCPConnector = object  # type: ignore[attr-defined]
            sys.modules[mod_name] = shim
            added_shims.append(mod_name)
    try:
        from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon

        return Alpha124ShadowDaemon
    except Exception:
        for mod_name in added_shims:
            sys.modules.pop(mod_name, None)
        raise


class _FakeResp:
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")

    async def read(self) -> bytes:
        return self._raw

    async def __aenter__(self) -> "_FakeResp":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


class _FakeSession:
    def __init__(self, responses: List[List[Dict[str, Any]]]) -> None:
        self.responses = list(responses)
        self.post_calls: List[Any] = []

    def post(self, url: str, **kwargs: Any) -> _FakeResp:
        self.post_calls.append((url, kwargs))
        rows = self.responses.pop(0) if self.responses else []
        return _FakeResp(200, rows)


class TestCloudSpendEgressAndProbeHardening(unittest.TestCase):
    def test_ws_healthy_shard_suppresses_redundant_books_post_and_preserves_wire_ts(self) -> None:
        Alpha124ShadowDaemon = _load_alpha124_daemon_cls()

        dm = Alpha124ShadowDaemon.__new__(Alpha124ShadowDaemon)
        dm.single_scan = False
        now = time.time()
        orig_wire_ts = now - 42.0
        book_payload = {
            "bids": [{"price": "0.51", "size": "100"}],
            "asks": [{"price": "0.52", "size": "100"}],
        }
        dm._ws_books = {"tok_live": (orig_wire_ts, dict(book_payload))}
        dm._ws_raw_levels = {"tok_live": ({0.51: 100.0}, {0.52: 100.0})}
        dm._ws_subscribed_tokens = {"tok_live"}
        dm._ws_rest_seeded = set()

        # Without shard liveness metadata, >5s old book is still treated as stale (backwards-compatible)
        self.assertIsNone(dm._get_fresh_ws_book("tok_live", now, max_age_sec=5.0))

        # With active shard heartbeat (1.1s ago), 42s-quiet book is authoritative with 0 HTTP calls
        dm._ws_shard_tokens = {0: {"tok_live"}}
        dm._ws_shard_last_rx_ts = {0: now - 1.1}
        dm._ws_last_reconciled_ts = {}
        self.assertTrue(dm._is_ws_book_live_on_healthy_shard("tok_live", orig_wire_ts, now))
        self.assertIsNotNone(dm._get_fresh_ws_book("tok_live", now, max_age_sec=5.0))

        fake_sess = _FakeSession([])

        async def _fake_get_session() -> Any:
            return fake_sess

        dm.get_session = _fake_get_session  # type: ignore[method-assign]
        res = asyncio.run(dm.fetch_books_batch(["tok_live"]))
        self.assertIn("tok_live", res)
        self.assertEqual(len(fake_sess.post_calls), 0)
        # Wire delta timestamp must remain untouched
        self.assertEqual(dm._ws_books["tok_live"][0], orig_wire_ts)

        # If shard goes silent (>5.0s), fail-closed back to REST reconciliation
        dm._ws_shard_last_rx_ts[0] = now - 8.5
        self.assertFalse(dm._is_ws_book_live_on_healthy_shard("tok_live", orig_wire_ts, now))

    def test_quiet_ws_reconciliation_and_unsubscribed_rest_ttl_cache(self) -> None:
        Alpha124ShadowDaemon = _load_alpha124_daemon_cls()

        dm = Alpha124ShadowDaemon.__new__(Alpha124ShadowDaemon)
        dm.single_scan = False
        now = time.time()
        dm._ws_books = {
            "tok_quiet": (
                now - 180.0,
                {"bids": [{"price": "0.40", "size": "50"}], "asks": [{"price": "0.42", "size": "50"}]},
            )
        }
        dm._ws_raw_levels = {"tok_quiet": ({0.40: 50.0}, {0.42: 50.0})}
        dm._ws_subscribed_tokens = {"tok_quiet"}
        dm._ws_rest_seeded = set()
        dm._ws_shard_tokens = {1: {"tok_quiet"}}
        dm._ws_shard_last_rx_ts = {1: now - 0.5}
        dm._ws_last_reconciled_ts = {}

        fake_sess = _FakeSession(
            [
                [
                    {
                        "asset_id": "tok_quiet",
                        "minimum_tick_size": "0.01",
                        "bids": [{"price": "0.40", "size": "50"}],
                        "asks": [{"price": "0.42", "size": "50"}],
                    },
                    {
                        "asset_id": "tok_unsub",
                        "minimum_tick_size": "0.01",
                        "bids": [{"price": "0.60", "size": "80"}],
                        "asks": [{"price": "0.61", "size": "80"}],
                    },
                ]
            ]
        )

        async def _fake_get_session() -> Any:
            return fake_sess

        dm.get_session = _fake_get_session  # type: ignore[method-assign]

        # Call 1: tok_quiet (>120s quiet), tok_unsub (unsubscribed), tok_dead (empty) -> 1 batched POST
        out1 = asyncio.run(dm.fetch_books_batch(["tok_quiet", "tok_unsub", "tok_dead"]))
        self.assertEqual(len(fake_sess.post_calls), 1)
        self.assertIn("tok_quiet", out1)
        self.assertIn("tok_unsub", out1)
        self.assertNotIn("tok_dead", out1)
        # Aligned quiet book must NOT be marked REST-seeded
        self.assertNotIn("tok_quiet", dm._ws_rest_seeded)

        # Call 2 immediately after: all 3 served/suppressed from WS + 12s REST cache + 20s empty cache -> 0 POSTs!
        dm._ws_shard_last_rx_ts[1] = time.time()
        out2 = asyncio.run(dm.fetch_books_batch(["tok_quiet", "tok_unsub", "tok_dead"]))
        self.assertEqual(len(fake_sess.post_calls), 1)
        self.assertIn("tok_quiet", out2)
        self.assertIn("tok_unsub", out2)
        self.assertNotIn("tok_dead", out2)

    def test_command_center_persistent_state_visibility_throttle_and_zero_trust(self) -> None:
        from scripts import dominus_command_center as dcc
        from src.paa_os.permissions import PermissionGate

        compile(dcc.REMOTE_PROBE_PY, "<remote_probe_cloud_spend>", "exec")
        daemon_src = dcc._build_persistent_daemon_py("print('{\"ok\": true}')")
        compile(daemon_src, "<daemon_wrapper>", "exec")
        self.assertIn("os.environ['PM_ENABLE_TLS_KEEPALIVE'] = '0'", daemon_src)
        self.assertIn("os.environ['PM_ENABLE_USER_WS'] = '0'", daemon_src)
        self.assertIn("os.environ['PM_DISABLE_FAST_V2_SIGNER'] = '1'", daemon_src)
        self.assertIn("_PERSIST = {}", daemon_src)
        self.assertIn("'_PERSIST': _PERSIST", daemon_src)
        self.assertIn("if (!document.hidden) refreshNow(false);", dcc.HTML_PAGE)
        self.assertIn("visibilitychange", dcc.HTML_PAGE)
        self.assertIn('"Connection": "close"', dcc.REMOTE_PROBE_PY)

        gate = PermissionGate()
        changed_files = [
            "src/polymarket_research/alpha_124_shadow_daemon.py",
            "scripts/dominus_command_center.py",
            "scripts/launch_finland_browser.ps1",
            "scripts/gcp_nl_cost_and_latency_cutover.sh",
            "tests/test_cloud_spend_egress_and_probe_hardening.py",
        ]
        git_bin = shutil.which("git")
        if git_bin and (REPO_ROOT / ".git").exists():
            diff_proc = subprocess.run(
                [git_bin, "diff", "--", *changed_files],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
            diff_text = diff_proc.stdout
        else:
            synth_lines = []
            for rel in changed_files:
                txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
                synth_lines.extend("+" + ln for ln in txt.splitlines())
            diff_text = "\n".join(synth_lines)
        ok_diff, violations = gate.inspect_candidate_diff(changed_files, diff_text)
        self.assertTrue(ok_diff, f"Cloud-spend hardening violated Zero-Trust PermissionGate: {violations}")


if __name__ == "__main__":
    unittest.main()

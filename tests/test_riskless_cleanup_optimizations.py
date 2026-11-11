"""Regression tests for the Riskless-Only Cleanup & Optimization Plan (Phases 2-4)."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_recorder_riskless_bus_only_caps_memory_and_preserves_shm_tick(tmp_path: Path) -> None:
    from src.polymarket_research.polymarket_terminal_recorder import PolymarketDualFeed1HRecorder

    rec = PolymarketDualFeed1HRecorder(asset="BTC", riskless_bus_only=True)
    assert rec.riskless_bus_only is True
    assert rec.spot_trades.maxlen == 64
    assert rec.futures_trades.maxlen == 64
    assert rec.basis_history.maxlen == 128
    assert rec._vol_buckets.maxlen == 16
    # S2 60s USD TWAP histories must remain full-resolution
    assert rec._cl_proxy_history.maxlen == 1200
    assert rec._raw_usd_history.maxlen == 1500

    rec.fast_tick_file = tmp_path / "pm_fast_tick_BTC.json"
    rec._fast_tick_enabled = True
    rec.spot_price = 94500.25
    rec.futures_price = 94512.50
    rec.spot_price_ts = time.time()
    rec.futures_price_ts = rec.spot_price_ts

    with patch.object(rec, "_run_exp306_realtime_eval") as mock_exp306:
        assert rec._maybe_write_fast_tick(force=True) is True
        # Immediate non-forced call within 100ms is throttled in riskless_bus_only mode
        assert rec._maybe_write_fast_tick(force=False) is False
        mock_exp306.assert_not_called()

    snap = json.loads(rec.fast_tick_file.read_text(encoding="utf-8"))
    assert snap["asset"] == "BTC"
    assert snap["spot_price"] == pytest.approx(94500.25)

    with patch("src.polymarket_research.polymarket_terminal_recorder._dispatch_trigger_fast") as mock_trig:
        rec._maybe_emit_boundary_lock_trigger()
        mock_trig.assert_not_called()


def test_alpha124_evict_stale_caches_and_riskless_bridge_only_preserves_grad8(tmp_path: Path) -> None:
    from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon

    with patch.object(Alpha124ShadowDaemon, "_hydrate_state", lambda self: None):
        daemon = Alpha124ShadowDaemon(single_scan=True, riskless_bridge_only=True)

    assert daemon.riskless_bridge_only is True
    now = 1_800_000_000.0
    daemon._ws_subscribed_tokens = {"tok_subscribed"}
    daemon.open_positions["pos_live"] = {"token_id": "tok_open_pos", "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX"}

    for tok in ("tok_subscribed", "tok_open_pos", "tok_stale_1", "tok_stale_2"):
        daemon._ws_raw_levels[tok] = ({0.48: 25.0}, {0.50: 25.0})
        dict.__setitem__(daemon._ws_books, tok, (now - 10.0, {"bids": [], "asks": []}))
        daemon._ws_rest_seeded.add(tok)

    daemon.uma_onchain_cache["old_uma"] = (now - 7200.0, {"state": 1})
    daemon.uma_onchain_cache["fresh_uma"] = (now - 30.0, {"state": 2})
    daemon.nba_boxscore_cache["old_game"] = (now - 5000.0, {})
    daemon.chainlink_open_cache["old_candle"] = (now - 9000.0, 90000.0)
    daemon.chainlink_open_cache["active_candle"] = (now + 300.0, 91000.0)
    daemon._instant_arb_cooldown_until["old_cd"] = now - 900.0
    daemon._instant_arb_cooldown_until["fresh_cd"] = now + 30.0

    for idx in range(6200):
        daemon.entered_keys.add(f"ephemeral_key_{idx}")
    daemon.entered_keys.add("pos_live")

    for i in range(8):
        k_cl = f"d1_win_{i}"
        daemon.entered_keys.add(k_cl)
        daemon.closed_positions.append(
            {
                "position_id": k_cl,
                "dedupe_key": k_cl,
                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "won": True,
                "closed_ts": now - 60.0 + i,
                "tier_pnls_usd": {"T100": 1.25, "T1000": 12.50},
                "legging_adjusted_tier_pnls_usd": {"T100": 1.20, "T1000": 12.00},
            }
        )

    stats = daemon._evict_stale_caches(now_ts=now)
    assert stats["evicted_books"] >= 2
    assert "tok_subscribed" in daemon._ws_raw_levels
    assert "tok_open_pos" in daemon._ws_raw_levels
    assert "tok_stale_1" not in daemon._ws_raw_levels
    assert "tok_stale_2" not in dict.keys(daemon._ws_books)
    assert "old_uma" not in daemon.uma_onchain_cache
    assert "fresh_uma" in daemon.uma_onchain_cache
    assert "old_candle" not in daemon.chainlink_open_cache
    assert "active_candle" in daemon.chainlink_open_cache
    assert "old_cd" not in daemon._instant_arb_cooldown_until
    assert "fresh_cd" in daemon._instant_arb_cooldown_until
    assert len(daemon.entered_keys) < 100
    assert "pos_live" in daemon.entered_keys
    assert "d1_win_7" in daemon.entered_keys
    assert daemon.is_sleeve_grad8_ready("D1_SAME_ORACLE_DOMINANCE_BOX") is True

    telem_file = tmp_path / "alpha124_market_telemetry.jsonl"
    with patch("src.polymarket_research.alpha_124_shadow_daemon.MARKET_TELEMETRY_FILE", telem_file):
        daemon._record_market_telemetry("test_k", 0.0, {"type": "TEST"}, now_ts=now)
    assert not telem_file.exists()


def test_executor_hot_async_bridge_batch_fok_from_worker_thread() -> None:
    import base64
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    captured: list[tuple[str, dict, bytes]] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        captured.append((str(request.url), dict(request.headers), request.content))
        return httpx.Response(
            200,
            json=[
                {"orderID": "oid_leg_1", "status": "matched", "takingAmount": "10", "makingAmount": "4.8"},
                {"orderID": "oid_leg_2", "status": "matched", "takingAmount": "10", "makingAmount": "4.9"},
            ],
        )

    ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
    ex.dry_run = False
    ex._fast_l2_ready = True
    ex._force_native_async_post = True
    ex._fast_l2_secret_bytes = base64.urlsafe_b64encode(b"0" * 32)
    ex._fast_l2_signer_addr = "0x1111111111111111111111111111111111111111"
    ex._fast_l2_api_key = "test-api-key"
    ex._fast_l2_passphrase = "test-pass"
    ex.CLOB_HOST = "https://clob.polymarket.com"
    ex.client = MagicMock()
    ex.client.host = "https://clob.polymarket.com"
    ex.client.use_server_time = False
    ex.client._is_order_version_mismatch.return_value = False

    loop = asyncio.new_event_loop()
    ready = threading.Event()

    def _run_loop() -> None:
        asyncio.set_event_loop(loop)
        cli = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
        ex._hot_order_async_loop = loop
        ex._hot_order_async_client = cli
        ready.set()
        loop.run_forever()
        if hasattr(cli, "aclose"):
            res_cl = cli.aclose()
            if asyncio.iscoroutine(res_cl):
                loop.run_until_complete(res_cl)

    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()
    assert ready.wait(timeout=5.0)
    try:
        assert ex._can_use_hot_async_bridge() is True
        payload = [
            {"order": {"salt": 1}, "owner": "test-api-key", "orderType": "FOK", "deferExec": True, "postOnly": False},
            {"order": {"salt": 2}, "owner": "test-api-key", "orderType": "FOK", "deferExec": True, "postOnly": False},
        ]
        res = ex._post_json_hot_async_bridge("/orders", payload)
        assert isinstance(res, list) and len(res) == 2
        assert res[0]["orderID"] == "oid_leg_1"
        assert len(captured) == 1
        url_hit, hdrs, raw_body = captured[0]
        assert url_hit == "https://clob.polymarket.com/orders"
        assert hdrs.get("poly_api_key") == "test-api-key"
        assert hdrs.get("poly_signature")
        assert json.loads(raw_body.decode("utf-8")) == payload
    finally:
        loop.call_soon_threadsafe(loop.stop)
        t.join(timeout=5.0)
        loop.close()

    # Once loop stops, _can_use_hot_async_bridge cleanly returns False for fallback
    assert ex._can_use_hot_async_bridge() is False


def test_governance_riskless_only_and_systemd_lean_flags() -> None:
    cfg = json.loads((REPO_ROOT / "config" / "polymarket_strategy_and_risk.json").read_text(encoding="utf-8"))
    assert cfg["directional"]["riskless_only_mode"] is True
    assert cfg["shadow_governance"]["enable_hybrid_zsplit_shadow"] is False
    assert cfg["shadow_governance"]["enable_xau_15m_maker_shadow"] is False
    assert cfg["riskless_boxes"]["enable_graduated_d1_box"] is True
    assert cfg["riskless_boxes"]["gatling_enabled"] is True

    rec_unit = (REPO_ROOT / "systemd" / "polymarket-recorder.service").read_text(encoding="utf-8")
    assert "--riskless-bus-only" in rec_unit
    assert "--asset BTC" in rec_unit

    sh_unit = (REPO_ROOT / "systemd" / "polymarket-alpha124-shadow.service").read_text(encoding="utf-8")
    assert "--riskless-bridge-only" in sh_unit
    assert "KillSignal=SIGTERM" in sh_unit

    dir_unit = (REPO_ROOT / "systemd" / "polymarket-paa-director.service").read_text(encoding="utf-8")
    assert "--no-ai" in dir_unit
    assert "--no-proactive-research" in dir_unit

    import tempfile
    import scripts.paa_autonomous_controller as pac_mod
    from scripts.paa_autonomous_controller import _is_riskless_only_config, check_operational_status

    assert _is_riskless_only_config() is True
    with tempfile.TemporaryDirectory() as _td_pac:
        _fresh_a124 = Path(_td_pac) / "alpha124_shadow_state.json"
        _fresh_a124.write_text("{}", encoding="utf-8")
        with patch("scripts.paa_autonomous_controller.sys.platform", "linux"), patch.object(
            pac_mod, "DATA_PM", Path(_td_pac)
        ), patch.object(
            pac_mod, "DATA_A124", Path(_td_pac)
        ), patch(
            "scripts.paa_autonomous_controller._sh", return_value=(0, "active")
        ) as mock_sh:
            op_rl, inc_rl = check_operational_status(auto_recover_safe=True, riskless_only=True)
            checked_cmds = [c.args[0] for c in mock_sh.call_args_list]
            assert not any("polymarket-trader.service" in cmd for cmd in checked_cmds)
            assert not any("apex-perp.service" in cmd for cmd in checked_cmds)
            assert op_rl["all_core_units_active"] is True
            assert inc_rl == []

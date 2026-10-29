#!/usr/bin/env python3
"""
Regression Test Suite for Zero-Trust Adversarial Forensic Code Audit (Categories 1-7).
Run via: venv/bin/pytest tests/test_zero_trust_forensic_audit.py -v
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
    calculate_taker_fee,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.polymarket_paper_trader import PolymarketForwardPaperTrader
from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook


@pytest.fixture(autouse=True)
def _offline_clob(monkeypatch):
    """#8: the whole suite runs 100% offline - the CLOB client + credentials are mocked, so constructing a
    live-mode PolymarketLiveExecutor never calls https://clob.polymarket.com (no api-key derivation, no latency)."""
    import src.polymarket_research.polymarket_live_executor as ex

    monkeypatch.setattr(ex, "ClobClient", MagicMock(name="OfflineClobClient"))
    monkeypatch.setattr(ex, "PY_CLOB_AVAILABLE", True)
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
    monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "3")


def test_cat1_cross_asset_direction_vocabulary_alignment():
    """Verifies BUG-1.1 fix: 'BUY' on BTC and 'UP' on ETH are recognized as aligned, not rejected."""
    passed, z_joint, reason = PolymarketLiveExecutor.validate_cross_asset_lead_lag(
        target_asset="ETH",
        target_direction="UP",
        btc_direction="BUY",
        z_alt=2.20,
        z_btc=1.90,
    )
    assert passed is True
    assert reason == "CROSS_ASSET_CONFIRMED"
    assert abs(z_joint - (0.70 * 2.20 + 0.30 * 1.90)) < 1e-6

    # Test counter-trend rejection
    passed_ct, _, reason_ct = PolymarketLiveExecutor.validate_cross_asset_lead_lag(
        target_asset="ETH",
        target_direction="UP",
        btc_direction="SELL",
        z_alt=2.20,
        z_btc=-1.90,
    )
    assert passed_ct is False
    assert "REJECT_BTC_COUNTER_TREND" in reason_ct


def test_cat1_paper_telemetry_binance_spot_preserves_salvage_timer(tmp_path, monkeypatch):
    """Verifies BUG-1.2 fix: 'binance_spot' in telemetry advances rather than resets the 90s salvage timer."""
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.DEV_LEDGER_FILE", tmp_path / "dev.jsonl")
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl")
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.STATE_FILE", tmp_path / "state.json")

    paper = PolymarketForwardPaperTrader(paper_latency_ms=0)
    m_id = "MKT_TELEM_SALVAGE"
    t0 = 1792400000.0
    paper.open_trades[m_id] = [{
        "trade_id": "T_SALVAGE_TELEM",
        "market_id": m_id,
        "title": "ETH 1H Down",
        "target_token": "DOWN",
        "entry_unix": t0 - 200.0,
        "candle_open_spot": 2500.0,
        "strike_price": 2500.0,
        "shares_bought": 50.0,
        "notional_usd": 37.50,
        "taker_fee_usd": 0.39,
        "status": "OPEN",
    }]

    # Tick 1: Telemetry uses 'binance_spot' (2506.0 -> +0.24% wrong side for DOWN)
    telem1 = {
        "market_id": m_id,
        "timestamp_unix": t0,
        "binance_spot": 2506.0,
        "binance_1h_open": 2500.0,
        "seconds_to_expiry": 900.0,
        "DOWN": {"best_bid": 0.24, "best_ask": 0.26},
    }
    closed1 = paper.check_maker_tp_fills(m_id, telem1)
    assert len(closed1) == 0
    assert paper.open_trades[m_id][0].get("opposite_breakout_start_ts") == t0

    # Tick 2: 92s later via 'binance_spot' -> must trigger CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE
    telem2 = {
        "market_id": m_id,
        "timestamp_unix": t0 + 92.0,
        "binance_spot": 2505.5,
        "binance_1h_open": 2500.0,
        "seconds_to_expiry": 808.0,
        "DOWN": {"best_bid": 0.20, "best_ask": 0.22},
    }
    closed2 = paper.check_maker_tp_fills(m_id, telem2)
    assert len(closed2) == 1
    assert closed2[0]["exit_reason"] == "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE"


def test_cat2_verified_shm_book_filtering(tmp_path, monkeypatch):
    """Verifies BUG-2.2 fix: _get_verified_shm_book strictly filters by market_id, token_id, and max age."""
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    harvester = PolymarketLiveHarvester(dry_run=True)

    pos = {
        "asset": "BTC",
        "market_id": "12345",
        "token_id": "0xTOKEN_UP",
        "target_token": "UP",
    }

    # Write a test fast tick to tmp shm path
    test_shm = tmp_path / "pm_fast_tick_BTC.json"
    now_ts = time.time()
    payload = {
        "markets": {
            "12345": {
                "market_id": "12345",
                "timestamp_unix": now_ts,
                "UP": {
                    "token_id": "0xTOKEN_UP",
                    "raw_top_bids": [[0.70, 100]],
                    "raw_top_asks": [[0.72, 100]],
                },
            },
            "99999": {
                "market_id": "99999",
                "timestamp_unix": now_ts,
                "UP": {
                    "token_id": "0xOTHER_TOKEN",
                    "raw_top_bids": [[0.50, 100]],
                    "raw_top_asks": [[0.52, 100]],
                },
            },
        }
    }
    test_shm.write_text(json.dumps(payload), encoding="utf-8")

    with patch("src.polymarket_research.polymarket_live_harvester.Path") as MockPath:
        # Route Path("/dev/shm/pm_fast_tick_BTC.json") to test_shm
        MockPath.side_effect = lambda p: test_shm if "pm_fast_tick_BTC.json" in str(p) else Path(p)

        book = harvester._get_verified_shm_book(pos)
        assert book is not None
        assert book["bids"][0]["price"] == "0.7"

        # Stale timestamp (> 1.5s) must be rejected
        payload["markets"]["12345"]["timestamp_unix"] = now_ts - 2.0
        test_shm.write_text(json.dumps(payload), encoding="utf-8")
        stale_book = harvester._get_verified_shm_book(pos)
        assert stale_book is None

        # Token mismatch must be rejected
        payload["markets"]["12345"]["timestamp_unix"] = now_ts
        payload["markets"]["12345"]["UP"]["token_id"] = "0xWRONG_TOKEN"
        test_shm.write_text(json.dumps(payload), encoding="utf-8")
        mismatch_book = harvester._get_verified_shm_book(pos)
        assert mismatch_book is None


def test_cat2_prewarm_hourly_opens_skips_subhourly(tmp_path, monkeypatch):
    """Verifies BUG-2.4 fix: _prewarm_hourly_opens skips sub-hourly triggers (15m, 5m)."""
    trigger_file = tmp_path / "live_shock_triggers.jsonl"
    t0 = 1792400000.0
    h_idx = int(t0 // 3600)
    lines = [
        # Sub-hourly 15m trigger
        json.dumps({
            "asset": "BTC",
            "t0_unix": t0,
            "horizon": "15m",
            "candle_interval": "15m",
            "finalized_1h_open": 64500.0,
            "candle_open_spot": 64500.0,
        }),
        # Sub-hourly title trigger
        json.dumps({
            "asset": "BTC",
            "t0_unix": t0 + 100,
            "title": "Bitcoin Up or Down 15m",
            "finalized_1h_open": 64600.0,
            "candle_open_spot": 64600.0,
        }),
        # True 1-hour trigger
        json.dumps({
            "asset": "BTC",
            "t0_unix": t0 + 200,
            "horizon": "1h",
            "title": "Bitcoin Up or Down: October 20, 4:00AM ET",
            "finalized_1h_open": 64000.0,
            "candle_open_spot": 64000.0,
        }),
    ]
    trigger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.DATA_DIR", tmp_path)
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.hourly_candle_opens.clear()
    harvester._prewarm_hourly_opens()

    # Must contain 64000.0 (the 1h trigger), not 64500.0 or 64600.0
    assert harvester.hourly_candle_opens["BTC"].get(h_idx) == 64000.0


def test_cat3_wallet_token_balance_defers_on_non_onchain_zero(tmp_path, monkeypatch):
    """Verifies BUG-3.1 fix: For winning positions, non-onchain 0.0 balance defers resolution rather than recording phantom loss."""
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "state.json")
    harvester = PolymarketLiveHarvester(dry_run=False)
    harvester.executor = MagicMock()
    harvester.save_state = MagicMock()

    tid = "T_WINNING_RESOLUTION"
    pos = {
        "trade_id": tid,
        "market_id": "123",
        "token_id": "0xWIN_TOK",
        "target_token": "UP",
        "entry_price": 0.80,
        "entry_shares": 100.0,
        "remaining_shares": 100.0,
        "notional_usd": 80.0,
        "status": ExecutionStatus.POSITION_CONFIRMED,
    }
    harvester.active_positions[tid] = pos

    # Simulate Polygon RPC timeout -> fallback to CLOB API returning (0.0, "CLOB_BALANCE_API")
    harvester._wallet_token_balance = MagicMock(return_value=(0.0, "CLOB_BALANCE_API"))
    harvester._close_position = MagicMock()

    res_record = {
        "market_id": "123",
        "winning_outcome": "UP",
        "Y_UP": 1,
        "Y_DOWN": 0,
    }

    # Run resolution
    asyncio.run(harvester._apply_market_resolution(tid, pos, res_record))

    # _close_position should NOT have been called; position remains open awaiting RPC recovery
    assert harvester._close_position.call_count == 0
    assert tid in harvester.active_positions


def test_cat3_l2_book_metrics_no_assert_cross():
    """Verifies BUG-3.3 fix: crossed books or floating point anomalies log warning instead of crashing."""
    book = L2OrderBook(asset_id="0xTEST")
    # Apply crossed book
    book.apply_snapshot(
        bids=[{"price": "0.55", "size": "100"}],
        asks=[{"price": "0.54", "size": "100"}],
    )
    # Must not raise AssertionError
    metrics = book.get_metrics(obs_ts=time.time())
    assert metrics["is_crossed"] is True
    assert metrics["best_bid"] == 0.55
    assert metrics["best_ask"] == 0.54


def test_cat4_canceled_partial_fill_does_not_reset_to_resting(tmp_path, monkeypatch):
    """Verifies BUG-4.1 fix: A canceled order whose partial fill is still mining never resets to RESTING."""
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "state.json")
    harvester = PolymarketLiveHarvester(dry_run=False)
    harvester.executor = MagicMock()
    harvester.save_state = MagicMock()

    tid = "LIVE_PARTIAL_STOP_1"
    pos = {
        "trade_id": tid,
        "market_id": "5799999",
        "token_id": "0xTOK_STOP",
        "target_token": "UP",
        "entry_price": 0.80,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 40.0,
        "exit_order_id": "0xOID_CANCELED_PARTIAL",
        "pending_canceled_order_id": "0xOID_CANCELED_PARTIAL",
        "exit_order_status": "FILL_RECONCILIATION_REQUIRED",
        "stop_triggered_ts": time.time() - 5.0,
        "target_exit_price": 0.99,
    }
    harvester.active_positions[tid] = pos

    # Simulate canceled order with 10 shares matched, still mining on Polygon (resting=False, terminal=False)
    harvester.executor.get_order_fill_summary.return_value = {
        "order_id": "0xOID_CANCELED_PARTIAL",
        "status": "CANCELED",
        "resting": False,
        "is_matched": True,
        "is_settled": False,
        "terminal": False,
        "original_size": 50.0,
        "matched": 10.0,
        "cash": 9.90,
        "cash_is_estimated": True,
        "limit_price": 0.99,
        "trade_ids": ["TR_1"],
        "transactions_hashes": [],
        "fill_ids": ["TR_1:0xOID_CANCELED_PARTIAL"],
    }

    resolved = harvester._resolve_fill_reconciliation(tid, pos)
    assert resolved is False
    assert pos["exit_order_status"] == "FILL_RECONCILIATION_REQUIRED"


def test_cat4_atomic_replace_maker_exit(tmp_path, monkeypatch):
    """Verifies BUG-4.2 fix: _atomic_replace_maker_exit reconciles partial fill and releases reservation before new post."""
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "state.json")
    harvester = PolymarketLiveHarvester(dry_run=False)
    harvester.executor = MagicMock()
    harvester.save_state = MagicMock()

    tid = "T_REPLACE"
    pos = {
        "trade_id": tid,
        "market_id": "123",
        "token_id": "0xTOK",
        "exit_order_id": "0xOLD_OID",
        "remaining_shares": 50.0,
        "entry_shares": 50.0,
        "entry_price": 0.80,
        "target_exit_price": 0.98,
        "exit_order_status": "RESTING",
    }
    harvester.active_positions[tid] = pos

    harvester.executor.cancel_order.return_value = {"is_canceled": True}
    harvester.executor.get_order_fill_summary.return_value = {
        "order_id": "0xOLD_OID",
        "status": "CANCELED",
        "resting": False,
        "matched": 10.0,
        "terminal": True,
    }
    harvester.executor.post_maker_exit_order.return_value = {
        "success": True,
        "orderID": "0xNEW_OID",
        "price": 0.97,
        "status": "LIVE",
    }

    posted = asyncio.run(harvester._atomic_replace_maker_exit(tid, pos, 0.97))
    assert posted is True
    # Verify old reservation was explicitly released
    harvester.executor.release_inventory.assert_called_with(reservation_id="0xOLD_OID")
    # Verify new post at 0.97 for remaining 40.0 shares
    assert pos["target_exit_price"] == 0.97
    assert pos["exit_order_id"] == "0xNEW_OID"


def test_cat5_and_cat6_base_fee_bps_and_unclamped_depth_sizing(tmp_path):
    """Verifies BUG-5.1 and BUG-6.1 fixes: 15m base fee 1800 bps is preserved and tickets > $75 are not clamped."""
    executor = PolymarketLiveExecutor(dry_run=True, ledger_path=str(tmp_path / "orders.jsonl"))
    book = {
        "asks": [{"price": "0.75", "size": "500.0"}],
        "bids": [{"price": "0.74", "size": "500.0"}],
    }
    passed, ratio, best_px, adj_notional = executor.verify_pre_trade_depth(
        book,
        target_notional_usd=120.0,
        side="BUY",
        depth_hurdle_ratio=1.50,
        max_price_ceiling=0.88,
        return_adjusted=True,
        max_ticket_size=250.0,
    )
    assert passed is True
    assert adj_notional == 120.0, f"Expected full $120.00 ticket, got clamped to ${adj_notional:.2f}"


def test_cat5_calculate_taker_fee_formula():
    """Verifies BUG-5.2 fix: calculate_taker_fee does not multiply by price twice."""
    notional = 100.0
    price = 0.80
    fee_rate = 0.07  # 7%
    eff_rate, fee_usd = calculate_taker_fee(notional, price, fee_rate=fee_rate, fee_exponent=1.0)
    # Correct formula: fee = notional * fee_rate * (1 - price) = 100 * 0.07 * 0.20 = $1.40
    assert abs(fee_usd - 1.40) < 1e-4
    assert abs(eff_rate - 0.014) < 1e-4


def test_cat7_ordered_seen_shock_ids(tmp_path, monkeypatch):
    """Verifies BUG-7.1 fix: _record_seen_shock_id maintains insertion order and bounds to 2000 entries."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    for i in range(2100):
        harvester._record_seen_shock_id(f"SHOCK_{i}")

    assert len(harvester.seen_shock_ids) <= 2000
    assert "SHOCK_0" not in harvester.seen_shock_ids
    assert "SHOCK_2099" in harvester.seen_shock_ids


# =====================================================================================================
# v3.5 OPERATIONS HARDENING: centralized risk config, stale-recorder watchdog, alerting, graceful SIGTERM,
# safe reload, deterministic replay, bundle sync
# =====================================================================================================
import importlib.util
import os
import signal
import subprocess
import sys

import src.polymarket_research.polymarket_live_harvester as hv_mod
from src.polymarket_research.polymarket_live_executor import (
    OrderResult,
    load_risk_config,
    RISK_CONFIG_PATH,
)

ROOT = Path(__file__).resolve().parent.parent


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_v35_central_risk_config_wiring(tmp_path, monkeypatch):
    """#1/#6: a real PolymarketLiveHarvester takes floor / daily-loss / exposure from config/polymarket_risk_config.json."""
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    cfg = json.loads(RISK_CONFIG_PATH.read_text())
    assert cfg["min_equity_floor"] == 66.67 and cfg["max_daily_loss"] == 20.00 and cfg["max_exposure"] == 35.00

    harvester = PolymarketLiveHarvester(dry_run=False)
    assert harvester.risk_controller.min_equity_floor_usd == 66.67
    assert harvester.risk_controller.max_daily_loss_usd == 20.00
    assert harvester.max_exposure == 35.00
    assert harvester.max_concurrent_positions == cfg["max_concurrent_positions"] == 2
    assert harvester.ticket_notional == cfg["ticket_notional"] == 16.50
    assert harvester.effective_risk_pct(91.67) == 0.18
    assert harvester.effective_risk_pct(109.99) == 0.18
    assert harvester.effective_risk_pct(110.00) == 0.22


def test_v35_config_loader_fails_safe(tmp_path):
    """A missing / corrupt / nonsensical config can only fall back to the conservative built-in defaults."""
    assert load_risk_config(tmp_path / "nope.json")["min_equity_floor"] == 66.67
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert load_risk_config(bad)["max_exposure"] == 35.00
    weird = tmp_path / "weird.json"
    weird.write_text(json.dumps({"max_exposure": -5, "max_daily_loss": "lots", "min_equity_floor": 70.0}))
    cfg = load_risk_config(weird)
    assert cfg["max_exposure"] == 35.00 and cfg["max_daily_loss"] == 20.00 and cfg["min_equity_floor"] == 70.0


def test_v35_18pct_ticket_ramp_and_correlated_second_ticket():
    """#11: $16.50 first ticket, ~$8.9 correlated second ticket -> ~$25.4 total, well inside the $35 exposure cap."""
    eq = 91.67
    pct = 0.18
    t1 = hv_mod.compute_correlated_truncated_kelly_size(
        live_equity=eq, p_win=0.95, entry_px=0.65, kelly_multiplier=1.0, active_positions={},
        cand_expiry_ts=1_800_000_000.0, cand_direction="UP", min_lot_usd=8.0,
        max_ticket_cap=round(pct * eq, 2), default_sizing_pct=pct,
    )
    assert t1 == 16.50
    active = {"A": {"status": "FILLED", "candle_expiry_ts": 1_800_000_000.0, "target_token": "UP", "remaining_shares": 20.0}}
    t2 = hv_mod.compute_correlated_truncated_kelly_size(
        live_equity=eq, p_win=0.95, entry_px=0.65, kelly_multiplier=1.0, active_positions=active,
        cand_expiry_ts=1_800_000_000.0, cand_direction="UP", min_lot_usd=8.0,
        max_ticket_cap=round(pct * eq, 2), default_sizing_pct=pct,
    )
    assert 8.5 <= t2 <= 9.5
    assert t1 + t2 <= 35.00


def test_v35_stale_recorder_watchdog(tmp_path, monkeypatch):
    """#3: fast tick must be <=15s old (or JSONL telemetry <=30s) else entries are refused."""
    tick_dir, tele_dir = tmp_path / "shm", tmp_path / "tele"
    tick_dir.mkdir()
    tele_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tick_dir))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tele_dir))
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    harvester = PolymarketLiveHarvester(dry_run=True)
    now = time.time()

    ok, age, why = harvester.check_recorder_freshness("BTC", now)
    assert ok is False and age == float("inf")  # nothing on the bus at all

    tick = tick_dir / "pm_fast_tick_BTC.json"
    tick.write_text("{}")
    os.utime(tick, (now - 5.0, now - 5.0))
    ok, age, _ = harvester.check_recorder_freshness("BTC", now)
    assert ok is True and 4.5 <= age <= 5.5

    os.utime(tick, (now - 20.0, now - 20.0))  # tick stale, no telemetry -> refuse
    ok, age, why = harvester.check_recorder_freshness("BTC", now)
    assert ok is False and "fast_tick_age" in why

    tele = tele_dir / "polymarket_hourly_telemetry.jsonl"  # fresh JSONL telemetry rescues a stale tick (<=30s)
    tele.write_text("{}\n")
    os.utime(tele, (now - 10.0, now - 10.0))
    assert harvester.check_recorder_freshness("BTC", now)[0] is True
    os.utime(tele, (now - 45.0, now - 45.0))
    assert harvester.check_recorder_freshness("BTC", now)[0] is False

    # ETH is judged on its own files, independent of BTC
    assert harvester.check_recorder_freshness("ETH", now)[0] is False


def _live_harvester_with_mock_clob(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=False, hold_to_maturity=False, max_concurrent=2)
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **k: 91.67
    h._last_known_collateral = 91.67
    h.executor.get_market_book_async = AsyncMock(return_value={
        "asks": [{"price": "0.65", "size": "400.0"}], "bids": [{"price": "0.64", "size": "400.0"}],
    })
    executed, maker_exits = [], []

    async def mock_snipe(**kw):
        executed.append(kw)
        notional = float(kw.get("notional_usd") or 0.0)
        return OrderResult(
            success=True, order_id=f"OID_{len(executed)}", trade_id=kw.get("trade_id", "T"),
            token_id=kw.get("token_id", "0xTOK_X"), target_token=kw.get("target_token", "UP"), side="BUY",
            price=0.65, size=round(notional / 0.65, 2), notional_usd=notional, fee_usd=0.05, latency_ms=1.0,
            mode="LIVE_PRODUCTION", execution_status=ExecutionStatus.POSITION_CONFIRMED, confirmed_onchain=True,
        )

    h.executor.execute_snipe_order_async = mock_snipe
    h.executor.post_maker_exit_order = MagicMock(
        side_effect=lambda **kw: maker_exits.append(kw) or {"success": True, "orderID": f"EXIT_{len(maker_exits)}"}
    )

    def make_shock(idx, title="BTC 1h Up", tte=600.0):
        return {
            "event_id": f"EVT_{idx}", "market_id": f"MKT_REPLAY_{idx}", "t0_unix": time.time(), "title": title,
            "asset": "BTC", "shock_direction": "BUY", "seconds_to_expiry": tte, "candle_distance_pct": 0.45,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {"UP": {"token_id": f"0xTOK_REPLAY_{idx}", "raw_top_asks": [[0.65, 400.0]],
                                              "effective_price_$50": 0.65, "vwap_$50": 0.65}},
        }

    return h, executed, maker_exits, make_shock


def test_v35_stale_guard_blocks_live_entry_then_allows_when_fresh(tmp_path, monkeypatch):
    """The watchdog is wired into the real entry path (not just a helper)."""
    tick_dir, tele_dir = tmp_path / "shm", tmp_path / "tele"
    tick_dir.mkdir()
    tele_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tick_dir))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tele_dir))
    h, executed, _, make_shock = _live_harvester_with_mock_clob(tmp_path, monkeypatch)

    asyncio.run(h.evaluate_shock_and_execute(make_shock(1)))
    assert executed == [], "stale/missing recorder feed must refuse the entry"

    # `ts: 0` keeps read_fast_tick() from treating this fixture as a real book, while mtime proves liveness.
    (tick_dir / "pm_fast_tick_BTC.json").write_text(json.dumps({"ts": 0}))
    asyncio.run(h.evaluate_shock_and_execute(make_shock(2)))
    assert len(executed) == 1


def test_v35_deterministic_replay_entry_exit_sizing_and_risk(tmp_path, monkeypatch):
    """#9: deterministic shock replay through the real harvester (mocked executor/CLOB): sized entries, maker exits,
    exposure/concurrency caps and risk-state updates."""
    monkeypatch.setenv("POLYMARKET_ALERTS_FILE", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setattr(hv_mod, "_ALERT_LAST_SENT", {})
    h, executed, maker_exits, make_shock = _live_harvester_with_mock_clob(tmp_path, monkeypatch)

    asyncio.run(h.evaluate_shock_and_execute(make_shock(1, "BTC 1h Up", 600.0)))
    assert len(executed) == 1 and len(h.active_positions) == 1
    assert executed[0]["notional_usd"] <= 20.17 + 0.01
    assert len(maker_exits) >= 1  # maker exit posted immediately for the confirmed fill

    asyncio.run(h.evaluate_shock_and_execute(make_shock(2, "BTC 15m Up", 300.0)))
    assert len(executed) == 2 and len(h.active_positions) == 2
    assert executed[1]["notional_usd"] < executed[0]["notional_usd"], "2nd same-window ticket carries the correlation haircut"
    total = sum(float(p.get("notional_usd") or 0.0) for p in h.active_positions.values())
    assert total <= h.max_exposure + 1e-6

    asyncio.run(h.evaluate_shock_and_execute(make_shock(3, "BTC 1h Up", 900.0)))
    assert len(executed) == 2, "max concurrent positions / exposure caps must reject the third entry"

    # risk-state evolution: two ~$5.28 salvage losses do not halt; the third trips the loss-streak breaker.
    rc = h.risk_controller
    rc.record_trade_pnl(-5.28)
    rc.record_trade_pnl(-5.28)
    assert not rc.is_halted() and abs(rc.daily_realized_loss - 10.56) < 1e-9
    rc.record_trade_pnl(-5.28)
    assert rc.is_halted() and "consecutive" in rc.halt_reason.lower()
    lines = [json.loads(l) for l in (tmp_path / "alerts.jsonl").read_text().splitlines()]
    assert any(l["event_type"] == "KILL_SWITCH_TRIPPED" for l in lines)

    # the 20-dollar daily budget is real (the legacy silent >=$65 override is gone)
    h2 = PolymarketLiveHarvester(dry_run=True)
    h2.risk_controller.record_trade_pnl(-12.0)
    h2.risk_controller.record_trade_pnl(5.0)
    h2.risk_controller.record_trade_pnl(-13.5)
    assert h2.risk_controller.is_halted() and "daily loss" in h2.risk_controller.halt_reason.lower()


def test_v35_alert_ledger_rate_limit_and_nonblocking_push(tmp_path, monkeypatch):
    """#2: JSONL ledger always written; push is on a daemon thread, rate-limited, never blocks the caller."""
    ledger = tmp_path / "critical_alerts.jsonl"
    monkeypatch.setenv("POLYMARKET_ALERTS_FILE", str(ledger))
    monkeypatch.setattr(hv_mod, "_ALERT_LAST_SENT", {})
    assert hv_mod.send_operational_alert("TEST_EVT", "first", "WARNING", rate_limit_sec=300.0) is True
    assert hv_mod.send_operational_alert("TEST_EVT", "dup", "WARNING", rate_limit_sec=300.0) is False
    rec = [json.loads(l) for l in ledger.read_text().splitlines()]
    assert len(rec) == 1 and rec[0]["event_type"] == "TEST_EVT" and rec[0]["severity"] == "WARNING"

    calls = []

    class _Resp:
        def read(self):
            return b"{}"

    def slow_urlopen(req, timeout=None):
        time.sleep(0.4)
        calls.append((req.full_url, timeout))
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", slow_urlopen)
    monkeypatch.setenv("POLYMARKET_ALERTS_FORCE_HTTP", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    t0 = time.time()
    assert hv_mod.send_operational_alert("PUSH_EVT", "hello", "CRITICAL") is True
    assert time.time() - t0 < 0.3, "alert dispatch must not stall the hot loop"
    hv_mod.flush_operational_alerts(3.0)
    assert calls and calls[0][0] == "https://api.telegram.org/bot123:ABC/sendMessage" and calls[0][1] == 2.5


def test_v35_stale_recorder_monitor_alerts_once_per_window(tmp_path, monkeypatch):
    tick_dir, tele_dir = tmp_path / "shm", tmp_path / "tele"
    tick_dir.mkdir()
    tele_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tick_dir))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tele_dir))
    monkeypatch.setenv("POLYMARKET_ALERTS_FILE", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setattr(hv_mod, "_ALERT_LAST_SENT", {})
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=True)
    h.monitor_recorder_staleness(time.time())
    h.monitor_recorder_staleness(time.time())  # rate-limited (5 min)
    events = [json.loads(l) for l in (tmp_path / "alerts.jsonl").read_text().splitlines()]
    stale = [e for e in events if e["event_type"] == "STALE_RECORDER_FEED"]
    assert len(stale) == 2 and {e["message"].split()[0] for e in stale} == {"BTC", "ETH"}  # one per asset, not per call


def test_v35_sigterm_triggers_graceful_state_flush_and_clean_exit(tmp_path, monkeypatch):
    """#4/#5: a real SIGTERM makes run() flush state atomically (STOPPED_GRACEFULLY) and return (exit code 0 path)."""
    for name in ("TRIGGER_FILE", "SHOCK_FILE", "RESOLUTIONS_FILE", "PID_FILE", "STATE_FILE"):
        monkeypatch.setattr(hv_mod, name, tmp_path / f"{name.lower()}{'.json' if name == 'STATE_FILE' else ''}")
    h = PolymarketLiveHarvester(dry_run=True)
    h.reconcile_with_exchange = lambda: None
    h._prewarm_active_market_tokens = lambda: None

    async def drive():
        asyncio.get_running_loop().call_later(0.4, os.kill, os.getpid(), signal.SIGTERM)
        await asyncio.wait_for(h.run(), timeout=15.0)

    asyncio.run(drive())
    state = json.loads((tmp_path / "state_file.json").read_text())
    assert state["status"] == "STOPPED_GRACEFULLY"
    assert h._shutdown_requested is True


def test_v35_reload_script_graceful_terminate_and_position_guard(tmp_path, monkeypatch):
    """#5: SIGTERM-first stops (SIGKILL only for stragglers) and refusal to reload with open positions."""
    reload_mod = _load_script("reload_production_daemons")

    p = subprocess.Popen(["sleep", "30"])
    reload_mod.terminate_gracefully([p.pid], timeout=3.0)
    assert p.wait(timeout=3) == -signal.SIGTERM  # exited on SIGTERM, never needed SIGKILL

    stubborn = subprocess.Popen(
        [sys.executable, "-c", "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print('r',flush=True);time.sleep(30)"],
        stdout=subprocess.PIPE, text=True,
    )
    assert stubborn.stdout.readline().strip() == "r"
    reload_mod.terminate_gracefully([stubborn.pid], timeout=1.0)
    assert stubborn.wait(timeout=3) == -signal.SIGKILL  # last-resort escalation only

    live = tmp_path / "live_state.json"
    live.write_text(json.dumps({"active_positions_count": 1, "active_positions": {"POS_1": {}}}))
    monkeypatch.setattr(reload_mod, "LIVE_STATE", live)
    monkeypatch.setattr(reload_mod, "PAPER_STATE", tmp_path / "no_paper_state.json")
    with pytest.raises(SystemExit) as ei:
        reload_mod.check_active_positions(force=False)
    assert ei.value.code == 1
    reload_mod.check_active_positions(force=True)  # --force overrides

    live.write_text(json.dumps({"active_positions_count": 0, "active_positions": {}}))
    reload_mod.check_active_positions(force=False)  # flat book -> safe


def test_v35_systemd_units_are_uniform_and_graceful():
    """#4: all core + secondary daemons have clean unit files with graceful SIGTERM handling."""
    for unit in (
        "polymarket-recorder",
        "polymarket-recorder-eth",
        "polymarket-recorder-sol",
        "polymarket-recorder-xrp",
        "polymarket-trader",
        "polymarket-live-harvester",
    ):
        text = (ROOT / "systemd" / f"{unit}.service").read_text()
        assert "Restart=on-failure" in text and "RestartSec=3" in text and "KillSignal=SIGTERM" in text, unit
    for sec_rec, sym in (("polymarket-recorder-sol", "SOL"), ("polymarket-recorder-xrp", "XRP")):
        r_txt = (ROOT / "systemd" / f"{sec_rec}.service").read_text()
        assert f"--asset {sym}" in r_txt and "CPUWeight=250" in r_txt and "IOWeight=250" in r_txt, sec_rec
    a124_txt = (ROOT / "systemd" / "polymarket-alpha124-shadow.service").read_text()
    assert "KillSignal=SIGTERM" in a124_txt and "TimeoutStopSec=15s" in a124_txt
    harv = "\n".join(
        ln for ln in (ROOT / "systemd" / "polymarket-live-harvester.service").read_text().splitlines()
        if not ln.lstrip().startswith("#")
    )
    assert "polymarket-recorder-sol.service" in harv and "polymarket-recorder-xrp.service" in harv
    assert "--reset-risk" not in harv, "auto-restarts must never silently clear a tripped circuit breaker"
    assert "--lot-size" not in harv and "--max-exposure" not in harv, "limits must come from the central config"
    assert "--asset BTC" in (ROOT / "systemd" / "polymarket-recorder.service").read_text()
    assert "--asset ETH" in (ROOT / "systemd" / "polymarket-recorder-eth.service").read_text()


def test_v35_bundle_in_sync_with_sources_and_under_1mb():
    """#10: polymarket_all_in_one.py must contain the exact current text of every bundled source and stay < 1 MB."""
    bundler = _load_script("bundle_polymarket_all_in_one")
    bundle_path = ROOT / "polymarket_all_in_one.py"
    bundle_text = bundle_path.read_text(encoding="utf-8")
    assert bundle_path.stat().st_size < 1_000_000
    drifted = []
    for rel_path, _desc in bundler.MODULES:
        code = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if bundler.transform_module(rel_path, code) not in bundle_text:
            drifted.append(rel_path)
    assert not drifted, f"Bundle out of sync for {drifted}. Run: venv/bin/python3 scripts/bundle_polymarket_all_in_one.py"
    compile(bundle_text, "polymarket_all_in_one.py", "exec")  # must remain valid Python

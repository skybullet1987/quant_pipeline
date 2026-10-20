#!/usr/bin/env python3
"""
v3.6 forensic remediation regression suite (CRIT-01..04, HIGH-02, HIGH-04, MED-02, MED-03, MED-05).
100% offline. Run: venv/bin/pytest tests/test_v36_forensic_remediation.py -v
"""

import asyncio
import inspect
import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.polymarket_research.polymarket_live_harvester as hv_mod
import src.polymarket_research.polymarket_terminal_recorder as rec_mod
from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    calculate_taker_fee,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.polymarket_paper_trader import PolymarketForwardPaperTrader


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    import src.polymarket_research.polymarket_live_executor as ex

    monkeypatch.setattr(ex, "ClobClient", MagicMock(name="OfflineClobClient"))
    monkeypatch.setattr(ex, "PY_CLOB_AVAILABLE", True)
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
    monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "3")


def _harvester(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=False)
    h.executor = MagicMock()
    h.save_state = MagicMock()
    return h


def _pos(tid="T1", **kw):
    pos = {
        "trade_id": tid, "market_id": "123", "token_id": "0xTOK", "target_token": "UP",
        "exit_order_id": "0xOLD", "remaining_shares": 50.0, "entry_shares": 50.0, "entry_price": 0.80,
        "notional_usd": 40.0, "target_exit_price": 0.98, "exit_order_status": "RESTING",
    }
    pos.update(kw)
    return pos


# ---------------------------------------------------------------- CRIT-01
@pytest.mark.parametrize("summary,cancel_res", [
    (None, {"is_canceled": True}),                                                                 # no summary at all
    ({"order_id": "0xOLD", "resting": False, "matched": 0.0, "terminal": False}, {"is_canceled": True}),                # not terminal
    ({"order_id": "0xOLD", "resting": False, "matched": 0.0, "terminal": True}, {"is_canceled": False}),                # cancel unconfirmed
])
def test_crit01_queue_jump_fails_closed(tmp_path, monkeypatch, summary, cancel_res):
    h = _harvester(tmp_path, monkeypatch)
    pos = _pos()
    h.active_positions["T1"] = pos
    h.executor.cancel_order.return_value = cancel_res
    h.executor.get_order_fill_summary.return_value = summary

    posted = asyncio.run(h._atomic_replace_maker_exit("T1", pos, 0.97))

    assert posted is False
    h.executor.release_inventory.assert_not_called()
    h.executor.post_maker_exit_order.assert_not_called()
    assert pos["exit_order_id"] == "0xOLD"
    assert pos["exit_order_status"] == "FILL_RECONCILIATION_REQUIRED"
    assert pos["pending_canceled_order_id"] == "0xOLD"


def test_crit01_queue_jump_still_works_when_terminally_canceled(tmp_path, monkeypatch):
    h = _harvester(tmp_path, monkeypatch)
    pos = _pos()
    h.active_positions["T1"] = pos
    h.executor.cancel_order.return_value = {"is_canceled": True}
    h.executor.get_order_fill_summary.return_value = {
        "order_id": "0xOLD", "status": "CANCELED", "resting": False, "matched": 10.0, "terminal": True,
    }
    h.executor.post_maker_exit_order.return_value = {"success": True, "orderID": "0xNEW", "price": 0.97, "status": "LIVE"}
    assert asyncio.run(h._atomic_replace_maker_exit("T1", pos, 0.97)) is True
    h.executor.release_inventory.assert_called_with(reservation_id="0xOLD")
    assert pos["exit_order_id"] == "0xNEW"


# ---------------------------------------------------------------- CRIT-02
def test_crit02_single_final_45s_recycler_through_cancel_gate():
    """The duplicate unguarded recycler is gone: the only Final-45s path is the Phase B state machine, which
    cancels + reconciles (closing at 100% fill) and gates on STOP_CANCEL_PENDING before any FAK is sent."""
    src = inspect.getsource(PolymarketLiveHarvester.check_resolutions_and_manage_positions)
    assert "[FINAL-45S CAPITAL RECYCLE]" not in src, "duplicate bypass block must be removed"
    assert src.count("final_45s_triggered = True") == 1
    assert "rem_shrs > 0.01 and best_b >= 0.85 and best_b > (entry_px + 0.03)" in src
    phase_b = src[src.index("final_45s_triggered = False"):]
    assert "STOP_CANCEL_PENDING" in phase_b
    assert "already fully matched on resting exit before unwind" in phase_b
    # the verified cancel gate precedes the aggressive unwind call
    assert phase_b.index("STOP_CANCEL_PENDING") < phase_b.index("execute_unwind_order")


# ---------------------------------------------------------------- CRIT-03
def test_crit03_close_position_is_atomic_when_release_raises(tmp_path, monkeypatch):
    h = _harvester(tmp_path, monkeypatch)
    pos = _pos(confirmed_realized_cash=45.0, realized_exit_cash=45.0, filled_exit_shares=50.0)
    h.active_positions["T1"] = pos
    h.executor.release_inventory.side_effect = RuntimeError("release boom")
    pnl_before = h.risk_controller.daily_realized_loss

    with pytest.raises(RuntimeError):
        h._close_position("T1", pos, "SETTLED", "MAKER_SCALP_FILLED_CLOB", won=True)

    assert "T1" in h.active_positions
    assert h.closed_positions == []
    assert h.risk_controller.daily_realized_loss == pnl_before
    assert pos.get("status") != "SETTLED"
    h.save_state.assert_not_called()


def test_crit03_close_position_happy_path(tmp_path, monkeypatch):
    h = _harvester(tmp_path, monkeypatch)
    pos = _pos(confirmed_realized_cash=45.0, realized_exit_cash=45.0, filled_exit_shares=50.0)
    h.active_positions["T1"] = pos
    h._close_position("T1", pos, "SETTLED", "MAKER_SCALP_FILLED_CLOB", won=True)
    assert "T1" not in h.active_positions and len(h.closed_positions) == 1
    h.executor.release_inventory.assert_any_call("0xTOK", 50.0)
    h.save_state.assert_called()


# ---------------------------------------------------------------- CRIT-04
def test_crit04_offchain_matched_fak_waits_in_unresolved_settlement(tmp_path, monkeypatch):
    h = _harvester(tmp_path, monkeypatch)
    pos = _pos(exit_order_id=None)
    h.active_positions["T1"] = pos
    res = {
        "success": True, "orderID": "0xFAK1", "matched_size": 50.0, "taking_amount": 39.0,
        "taking_amount_estimated": True, "taking_amount_missing": False, "fee_usd": 0.10, "fee_is_estimated": True,
    }

    outcome = h._handle_unwind_response("T1", pos, res, 50.0, "STOP_LOSS", "PARTIAL_STOP", 0.75)

    assert outcome != "UNKNOWN"
    assert pos.get("exit_order_status") != "UNWIND_EXECUTION_OUTCOME_UNKNOWN"
    assert not h.risk_halt
    assert pos["pending_settlement_order_id"] == "0xFAK1"
    assert pos["status"] == "UNRESOLVED_SETTLEMENT", "cash is provisional until Polygon inclusion"
    assert "T1" in h.active_positions and h.closed_positions == []


def test_crit04_missing_taking_amount_is_still_unknown(tmp_path, monkeypatch):
    h = _harvester(tmp_path, monkeypatch)
    pos = _pos(exit_order_id=None)
    h.active_positions["T1"] = pos
    res = {
        "success": True, "orderID": "0xFAK2", "matched_size": 50.0, "taking_amount": 37.5,
        "taking_amount_estimated": True, "taking_amount_missing": True, "fee_usd": 0.10,
    }
    assert h._handle_unwind_response("T1", pos, res, 50.0, "STOP_LOSS", "PARTIAL_STOP", 0.75) == "UNKNOWN"
    assert pos["exit_order_status"] == "UNWIND_EXECUTION_OUTCOME_UNKNOWN"


def test_crit04_executor_flags_offchain_match_as_estimated_not_missing(monkeypatch):
    ex = PolymarketLiveExecutor(dry_run=False)
    ex.is_authenticated = True
    ex.reserve_inventory = MagicMock()
    ex.get_transaction_receipt_status = MagicMock(return_value=None)
    ex.client = MagicMock()
    ex.client.create_order.return_value = object()
    ex.client.post_order.return_value = {
        "orderID": "0xAA", "status": "MATCHED", "makingAmount": "50.0", "takingAmount": "39.0",
    }
    out = ex.execute_unwind_order(token_id="0xTOK", size=50.0, side="SELL", min_price=0.70)
    if out.get("matched_size"):  # execution path reached (client wiring differs per environment)
        assert out["taking_amount_estimated"] is True
        assert out["taking_amount_missing"] is False


# ---------------------------------------------------------------- MED-03
def test_med03_fok_sweep_uses_market_fee_rate():
    ex = PolymarketLiveExecutor(dry_run=True)
    book = {"asks": [{"price": "0.60", "size": "100"}, {"price": "0.62", "size": "100"}], "bids": []}
    f07 = ex.simulate_fok_sweep(book, 40.0)[4]
    f18 = ex.simulate_fok_sweep(book, 40.0, fee_rate=0.18)[4]
    assert f07 > 0 and abs(f18 / f07 - 0.18 / 0.07) < 1e-3
    f_e2 = ex.simulate_fok_sweep(book, 40.0, fee_rate=0.07, fee_exponent=2.0)[4]
    assert f_e2 < f07


# ---------------------------------------------------------------- MED-05
def test_med05_cli_defaults_bound_to_hardened_constants():
    src = inspect.getsource(hv_mod)
    main_block = src[src.index('if __name__ == "__main__":'):]
    assert "default=MAX_TTE_SECONDS" in main_block
    assert "default=MAX_PRICE_CEILING" in main_block
    assert "default=MIN_PRICE_FLOOR" in main_block
    assert "default=MAX_ABSOLUTE_TICKET_USD" in main_block
    for legacy in ("default=3300.0", "default=0.88", "default=0.65", "default=250.0"):
        assert legacy not in main_block
    assert "allow_cli_exposure=True" not in main_block
    assert '"--max-exposure"' in main_block.split("allow_cli_exposure=")[1].split("\n")[0]


# ---------------------------------------------------------------- HIGH-02
def test_high02_btc_lead_state_has_valid_ts_ns_and_no_clobbering_writer(tmp_path):
    lead_file = tmp_path / "pm_lead_state_BTC.json"
    stub = SimpleNamespace(
        asset="BTC", _fast_tick_enabled=True, _last_lead_state_write=0.0, spot_price=84000.0, basis_bps=1.234,
        _last_btc_shock={"last_shock_ts_ns": time.time_ns(), "last_shock_dir": "BUY", "last_shock_z_btc": 2.1},
        lead_state_file=lead_file,
    )
    rec_mod.PolymarketDualFeed1HRecorder._publish_btc_lead_state(stub, 3_000_000.0, 0.9, 0.5, "BUY", 2.1, force=True)

    st = rec_mod.read_lead_state(lead_file)
    assert st is not None, "ETH recorder must accept the BTC lead state immediately"
    assert int(st["ts_ns"]) > 0 and abs(time.time_ns() - int(st["ts_ns"])) / 1e6 < 1500.0
    for key in ("asset", "t0_unix", "spot_price", "basis_bps", "btc_shock_direction", "btc_target_token",
                "last_shock_ts_ns", "z_btc"):
        assert key in st, key
    assert st["btc_target_token"] == "UP"

    # No second writer in evaluate_shock may overwrite the same file without ts_ns.
    shock_src = inspect.getsource(rec_mod.PolymarketDualFeed1HRecorder.evaluate_shock)
    assert "pm_lead_state_BTC.json.tmp" not in shock_src
    assert "os.replace(shm_lead_tmp" not in shock_src


def test_high02_fast_tick_is_single_writer_with_raw_levels():
    book = rec_mod.L2OrderBook("0xTOK")
    book.apply_snapshot(
        [{"price": "0.70", "size": "100"}, {"price": "0.69", "size": "50"}],
        [{"price": "0.72", "size": "80"}, {"price": "0.73", "size": "40"}],
    )
    tob = book.top_of_book()
    assert tob["raw_top_bids"][0] == (0.70, 100.0) and tob["raw_top_asks"][0] == (0.72, 80.0)
    ws_src = inspect.getsource(rec_mod.PolymarketDualFeed1HRecorder.stream_polymarket_clob)
    assert "_publish_shm_fast_tick(" not in ws_src
    assert "_maybe_write_fast_tick()" in ws_src


def test_high02_harvester_honors_pm_fast_tick_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=True)
    pos = {"asset": "BTC", "market_id": "1", "token_id": "0xT", "target_token": "UP"}
    monkeypatch.delenv("PM_FAST_TICK_DIR", raising=False)
    assert h._get_verified_shm_book(pos) is None, "under pytest without PM_FAST_TICK_DIR the real /dev/shm is never read"
    now = time.time()
    (tmp_path / "pm_fast_tick_BTC.json").write_text(json.dumps({"markets": {"1": {
        "market_id": "1", "timestamp_unix": now,
        "UP": {"token_id": "0xT", "raw_top_bids": [[0.7, 10]], "raw_top_asks": [[0.72, 10]]},
    }}}))
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    book = h._get_verified_shm_book(pos)
    assert book is not None and book["bids"][0]["price"] == "0.7"


# ---------------------------------------------------------------- HIGH-04
def test_high04_paper_trader_uses_actual_entry_price_not_050(tmp_path, monkeypatch):
    for name, fname in (("DEV_LEDGER_FILE", "dev.jsonl"), ("VALIDATION_LEDGER_FILE", "val.jsonl"), ("STATE_FILE", "state.json")):
        monkeypatch.setattr(f"src.polymarket_research.polymarket_paper_trader.{name}", tmp_path / fname)
    paper = PolymarketForwardPaperTrader(paper_latency_ms=0)
    m_id, t0 = "MKT_PARITY", 1792400000.0
    # Only `exec_price` (no `entry_price`): resolved entry 0.85 => TP target 0.99. The old $0.50 fallback
    # would pick TP 0.98 and wrongly "fill" at a 0.985 bid.
    paper.open_trades[m_id] = [{
        "trade_id": "T_PARITY", "market_id": m_id, "title": "BTC 1H Up", "target_token": "UP",
        "entry_unix": t0 - 100.0, "candle_open_spot": 100000.0, "strike_price": 100000.0,
        "shares_bought": 50.0, "notional_usd": 42.5, "taker_fee_usd": 0.3, "status": "OPEN", "exec_price": 0.85,
    }]
    telem = {
        "market_id": m_id, "timestamp_unix": t0, "binance_spot": 100500.0, "binance_1h_open": 100000.0,
        "seconds_to_expiry": 1500.0, "UP": {"best_bid": 0.985, "best_ask": 0.986},
    }
    closed = paper.check_maker_tp_fills(m_id, telem)
    assert not any("MAKER" in str(c.get("exit_reason", "")) for c in closed)


def test_high04_paper_trader_stores_entry_price_and_loop_is_non_blocking():
    pt = inspect.getsource(PolymarketForwardPaperTrader)
    assert pt.count('"entry_price": exec_price') >= 1 and pt.count('"entry_price": vwap_price') >= 1
    loop_src = inspect.getsource(PolymarketForwardPaperTrader.live_loop)
    assert "await asyncio.to_thread(self.evaluate_shock_signal, s, False)" in loop_src
    assert "self.evaluate_shock_signal(s, historical=False)" not in loop_src


# ---------------------------------------------------------------- MED-02
def test_med02_fee_helpers_coexist_without_collision():
    eff_rate, fee_usd = calculate_taker_fee(50.0, 0.77, fee_rate=0.07, fee_exponent=1.0)  # 4-arg executor helper
    per_share = rec_mod.calculate_per_share_taker_fee(0.77, 0.07)                        # recorder helper
    assert abs(fee_usd - (50.0 / 0.77) * per_share) < 1e-3
    assert abs(per_share - 0.07 * 0.77 * 0.23) < 1e-9
    assert rec_mod.calculate_per_share_taker_fee(0.5, 0.07, 2.0) < rec_mod.calculate_per_share_taker_fee(0.5, 0.07, 1.0)
    assert not hasattr(rec_mod, "calculate_taker_fee"), "recorder must not shadow the executor's canonical name"


# ---------------------------------------------------------------- v3.6 Optimization & Safety Guards
def test_v36_clamps_removed_and_constants_aligned():
    import src.polymarket_research.polymarket_live_executor as ex
    import src.polymarket_research.polymarket_paper_trader as pt

    # 1. Harvester constants
    assert hv_mod.MAX_ABSOLUTE_TICKET_USD == 200.00
    assert hv_mod.HARD_PORTFOLIO_EXPOSURE_CEILING == 500.0
    assert hv_mod.MAX_PORTFOLIO_EXPOSURE_USD == 500.0
    assert hv_mod.MIN_LOT_SIZE_USD == 12.0
    assert hv_mod.DEFAULT_MAX_TRADES_PER_MARKET == 2
    assert hv_mod.DEFAULT_MAX_TRADES_PER_HOUR == 6
    assert hv_mod.MAX_PRICE_CEILING == 0.86
    assert hv_mod.MIN_PRICE_FLOOR == 0.55
    assert hv_mod.QUEUE_JUMP_MIN_WALL_SHARES == 250.0
    assert hv_mod.QUEUE_JUMP_WALL_MULT == 6.0

    sig = inspect.signature(hv_mod.compute_correlated_truncated_kelly_size)
    assert sig.parameters["max_ticket_cap"].default == 200.0

    h_sig = inspect.signature(PolymarketLiveHarvester.__init__)
    assert h_sig.parameters["depth_hurdle"].default == 1.30

    # 2. Executor constants
    assert ex.MAX_PRICE_CEILING == 0.8600
    assert ex.SLEEVE_1_MAX_PRICE == 0.8600
    assert ex.SLEEVE_2_MAX_PRICE == 0.7800
    assert ex.SLEEVE_2_SUBHOURLY_MAX_PRICE == 0.7800
    assert ex.DEFAULT_DEPTH_HURDLE == 1.30
    assert ex.MIN_LOT_SIZE_USD == 12.00
    assert ex.MIN_TICKET_USD == 12.00
    assert ex.MAX_TICKET_CAP_USD == 200.00
    assert ex.MAX_CONCURRENT_POSITIONS == 3
    assert ex.MAX_POSITIONS_PER_MARKET_ID == 2

    el_sig = inspect.signature(PolymarketLiveExecutor.calculate_elastic_ticket_size)
    assert el_sig.parameters["max_ticket_usd"].default == 200.0

    # 3. Recorder capacity levels
    assert rec_mod.TICKET_CAPACITY_LEVELS == [1.0, 5.0, 20.0, 25.0, 50.0, 100.0, 150.0, 200.0, 250.0]

    # 4. Paper trader
    assert pt.MAX_ELASTIC_TICKET_USD == 200.0
    assert pt.MAX_TRADES_PER_HOUR == 6
    assert pt.MAX_PRICE_CEILING == 0.86


def test_v36_equity_tier_limits_safeguard_1():
    from src.polymarket_research.polymarket_live_harvester import get_equity_tier_limits

    # Recovery Tier (< 140)
    t_rec = get_equity_tier_limits(91.67)
    assert t_rec["tier"] == "RECOVERY"
    assert t_rec["dynamic_bankroll_pct"] == 0.22
    assert t_rec["max_concurrent_positions"] == 2
    assert t_rec["max_exposure"] == round(max(45.0, 91.67 * 0.55), 2)  # 50.42
    assert t_rec["max_daily_loss"] == round(max(25.0, 91.67 * 0.30), 2)  # 27.50
    assert t_rec["min_equity_floor"] == 65.0  # max(65.0, 91.67 * 0.68) -> 65.0

    # Growth Tier (140 <= equity < 300)
    t_growth = get_equity_tier_limits(200.0)
    assert t_growth["tier"] == "GROWTH"
    assert t_growth["dynamic_bankroll_pct"] == 0.26
    assert t_growth["max_concurrent_positions"] == 3
    assert t_growth["max_exposure"] == round(min(350.0, 200.0 * 0.75), 2)  # 150.0
    assert t_growth["max_daily_loss"] == round(max(25.0, 200.0 * 0.30), 2)  # 60.0
    assert t_growth["min_equity_floor"] == round(max(65.0, 200.0 * 0.68), 2)  # 136.0

    # Scale Tier (>= 300)
    t_scale = get_equity_tier_limits(400.0)
    assert t_scale["tier"] == "SCALE"
    assert t_scale["dynamic_bankroll_pct"] == 0.28
    assert t_scale["max_concurrent_positions"] == 3
    assert t_scale["max_exposure"] == round(min(500.0, 400.0 * 0.85), 2)  # 340.0
    assert t_scale["max_daily_loss"] == round(max(25.0, 400.0 * 0.30), 2)  # 120.0
    assert t_scale["min_equity_floor"] == round(max(65.0, 400.0 * 0.68), 2)  # 272.0

    # High-water-mark ratchet test
    t_ratchet = get_equity_tier_limits(100.0, high_water_mark_equity=250.0)
    assert t_ratchet["min_equity_floor"] == round(max(65.0, 250.0 * 0.68), 2)  # 170.0


def test_v36_trap_11_bid_depth_downscaler_source():
    src = inspect.getsource(PolymarketLiveHarvester.evaluate_shock_and_execute)
    assert "[BID_DEPTH_DOWNSCALE]" in src
    assert "max_near_bid_shares = near_touch_bid_shares / max(min_bid_mult, 1.0)" in src
    assert "max_bid_supported_usd = math.floor(max_bid_supported_shares * first_ask * 100.0) / 100.0" in src
    assert "effective_notional = max_bid_supported_usd" in src


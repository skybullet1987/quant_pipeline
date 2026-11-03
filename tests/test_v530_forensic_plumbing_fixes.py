"""
Zero-Parameter Forensic Plumbing Regression Suite (v5.3.0 + Kaizen #1-#4 + Track A)
===================================================================================
Verifies all deterministic PLUMBING_0_PARAM fixes without altering any Purged-WFO
strategy parameters:
  1. [P0-1] PM_ENFORCE_V5_TIER_SLOTS=1 enforces v5.3.0 tiered directional slots (2->3->4)
            and portfolio_exposure_pct (0.88x-0.92x) over legacy unlimited_slots=99/$100.
  2. [P0-2] evaluate_shock_and_execute cleans pending_entry_intents on unwired exceptions /
            CancelledError (zero permanent halt), while flagging needs_runtime_recovery if wired.
  3. [P0-3] cancel_order flags read_replica_stale_live on 300-600ms CLOB replica lag and
            partially-filled CANCELED Maker SELL orders settle via ERC-1155 balance proof.
  4. [P0-4] Partial-exit proceeds are preserved on MARKET_RESOLVED_LOSS (never wiped to $0),
            and 2 winning slots on the same condition_id share a single redemption tx cleanly.
  5. [P0-5] L2OrderBook resets age_ask_ms on upward ask sweeps while preserving birth age on
            <25% micro-nibbles; empty-ask 1.0 sentinel never false-vetoes refilled books.
  6. [P0-6] Recorder build_fast_tick_snapshot exports spot_ts, Harvester ignores stale SHM
            spot_ts, and get_delta_basis_100ms reverse-scans accurately.
  7. [P0-7/P0-8] D1 asymmetric excess leg ("shares" key) registers >=5.0 residual shares, and
            non-directional PnL does not contaminate directional consecutive_losses/daily_loss.
  8. [P1-1/P1-2/P1-4] 3-asset (18-token) PreSignedOrderLadderCache preserves active 1h tokens,
            prewarm_order_ladder covers $0.52-$0.76 + $0.90-$0.94, 15m Surgical Taker is NOT
            haircutted by 0.80x subordinate_15m_maker_size_mult, and 99c recycle preserves 0.001 ticks.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import src.polymarket_research.polymarket_live_harvester as hv_mod
from src.polymarket_research.holistic_strategy_governance import (
    GLOBAL_GOVERNANCE_MANAGER,
    HotReloadConfigManager,
    compute_stop_risk_fractional_kelly_ticket,
)
from src.polymarket_research.latency_trace import classify_shock_attempt
from src.polymarket_research.polymarket_live_executor import (
    ExecutionStatus,
    OrderResult,
    PolymarketLiveExecutor,
)
from src.polymarket_research.polymarket_live_harvester import (
    EmergencyRiskController,
    PolymarketLiveHarvester,
)
from src.polymarket_research.polymarket_terminal_recorder import (
    L2OrderBook,
    PolymarketDualFeed1HRecorder,
)


def _make_live_harvester(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PolymarketLiveHarvester:
    monkeypatch.setattr(hv_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "live_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    h = PolymarketLiveHarvester(
        dry_run=True,
        dynamic_sizing=True,
        hold_to_maturity=False,
        exit_policy="hold_98",
        ticket_notional=16.50,
        max_price_ceiling=0.76,
        min_price_floor=0.52,
        max_concurrent=99,
        allow_cli_concurrency=True,
        allowed_assets={"BTC", "ETH", "SOL"},
    )
    h.dry_run = False
    h._startup_reconciled = True
    h.executor.dry_run = False
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.client = object()
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.check_recorder_freshness = lambda *a, **kw: (True, 0.02, "OK")
    return h


def test_p0_1_v530_tiered_slot_cap_and_exposure_enforcement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    svc_txt = (Path(__file__).resolve().parents[1] / "systemd" / "polymarket-live-harvester.service").read_text(encoding="utf-8")
    assert 'Environment="PM_ENFORCE_V5_TIER_SLOTS=1"' in svc_txt

    monkeypatch.setenv("PM_ENFORCE_V5_TIER_SLOTS", "1")
    h = _make_live_harvester(tmp_path, monkeypatch)

    # SEED ($83.39 < $100): 4 directional slots, 0.96x exposure ($80.05)
    h._last_known_collateral = 83.39
    h.high_water_mark_equity = 83.39
    h._update_equity_tier(83.39)
    assert h._is_unlimited_slots_active() is False
    assert h.max_concurrent_positions == 4
    assert h._effective_directional_slot_cap() == 4
    assert h.max_exposure == pytest.approx(round(83.39 * 0.96, 2))

    # RECOVERY ($150.00): 4 directional slots, 0.96x exposure ($144.00, NOT $350.00!)
    h._last_known_collateral = 150.0
    h.high_water_mark_equity = 150.0
    h._update_equity_tier(150.0)
    assert h.max_concurrent_positions == 4
    assert h._effective_directional_slot_cap() == 4
    assert h.max_exposure == pytest.approx(144.0)

    # GROWTH ($320.00): 4 directional slots, 0.96x exposure ($307.20)
    h._last_known_collateral = 320.0
    h.high_water_mark_equity = 320.0
    h._update_equity_tier(320.0)
    assert h.max_concurrent_positions == 4
    assert h._effective_directional_slot_cap() == 4
    assert h.max_exposure == pytest.approx(307.2)


def test_p0_2_pending_entry_intents_cleaned_on_unwired_exception_and_cancelled_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    h = _make_live_harvester(tmp_path, monkeypatch)
    h._last_known_collateral = 120.0
    h.high_water_mark_equity = 120.0
    h.executor.get_collateral_balance = lambda *a, **kw: 120.0
    h.executor.get_conditional_balance = lambda *a, **kw: 0.0

    async def _unwired_cancel(**_kw):
        raise asyncio.CancelledError()

    h.executor.execute_snipe_order_async = _unwired_cancel

    now_u = time.time()
    shock = {
        "event_id": "SHK_CANCEL_UNWIRED",
        "market_id": "77001",
        "condition_id": "0x77001",
        "t0_unix": now_u,
        "title": "Bitcoin Up or Down - 4PM ET",
        "asset": "BTC",
        "horizon": "1h",
        "shock_direction": "BUY",
        "seconds_to_expiry": 500.0,
        "spot_at_t0": 80250.0,
        "trigger_price": 80250.0,
        "candle_open_spot": 80000.0,
        "twap_60s_open": 80000.0,
        "candle_distance_pct": 0.3125,
        "candle_sigma": 0.0018,
        "shock_volume_100ms": 2_200_000.0,
        "shock_ofi": 0.90,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x77001"},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "1" * 30,
                "best_ask": 0.66,
                "best_bid": 0.65,
                "raw_top_asks": [[0.66, 150.0]],
                "raw_top_bids": [[0.65, 150.0]],
                "effective_price_$25": 0.66,
                "vwap_$25": 0.66,
                "age_ask_ms": 300.0,
                "obi_l1": 0.25,
                "age_book_ms": 15.0,
                "book_timestamp": now_u,
            }
        },
    }
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(h.evaluate_shock_and_execute(shock))

    assert h.pending_entry_intents == {}
    assert h._global_halt_reasons() == []
    assert "77001" not in getattr(h, "_inflight_eval_markets", set())

    # Sub-case 2b: CancelledError AFTER wire bytes transmitted MUST retain intent with needs_runtime_recovery=True
    async def _wired_cancel(**kw):
        h.executor.__dict__.setdefault("_wire_submitted_trade_ids", set()).add(str(kw["trade_id"]))
        raise asyncio.CancelledError()

    h.executor.execute_snipe_order_async = _wired_cancel
    shock_wired = dict(
        shock,
        event_id="SHK_CANCEL_WIRED",
        market_id="77002",
        condition_id="0x77002",
        fee_metadata={"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x77002"},
    )
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(h.evaluate_shock_and_execute(shock_wired))

    assert len(h.pending_entry_intents) == 1
    retained_intent = next(iter(h.pending_entry_intents.values()))
    assert retained_intent.get("needs_runtime_recovery") is True


def test_p0_3_cancel_order_stale_live_and_partial_canceled_maker_settlement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    mock_client = MagicMock()
    mock_client.cancel_orders.return_value = {"canceled": ["0xSTALE_OID"], "not_canceled": {}}
    ex.client = mock_client
    ex.get_order_status = lambda _oid: {"id": "0xSTALE_OID", "status": "LIVE", "size_matched": "0", "original_size": "20"}

    cres = ex.cancel_order("0xSTALE_OID")
    assert cres["is_canceled"] is True
    assert cres.get("read_replica_stale_live") is True

    # Partially-filled CANCELED Maker SELL order (10 of 20 shares matched, CLOB /trades empty, 10 shares left on-chain)
    ex.get_order_status = lambda _oid: {
        "id": "0xPART_MKR_TP",
        "status": "CANCELED",
        "side": "SELL",
        "order_type": "GTC",
        "price": "0.98",
        "original_size": "20",
        "size_matched": "10",
        "asset_id": "TOK_PART",
    }
    ex.get_order_fills = lambda _oid, token_id=None: []
    ex.get_onchain_erc1155_balance = lambda _tok: 10.0

    fsum = ex.get_order_fill_summary("0xPART_MKR_TP", "TOK_PART")
    assert fsum is not None
    assert fsum["terminal"] is True
    assert fsum["cash_is_estimated"] is False
    assert fsum["matched"] == pytest.approx(10.0)
    assert fsum["cash"] == pytest.approx(9.80)

    h = _make_live_harvester(tmp_path, monkeypatch)
    h.executor.get_onchain_erc1155_balance = lambda _tok: 10.0
    pos = {"token_id": "TOK_PART", "entry_shares": 20.0, "remaining_shares": 10.0}
    assert h._exit_fill_settled_onchain(pos, fsum) is True


def test_p0_4_partial_exit_cash_preserved_on_otm_resolution_and_multislot_redemption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    h = _make_live_harvester(tmp_path, monkeypatch)
    h._last_known_collateral = 80.0

    # 4a. Partial exit ($9.50 estimated cash on 10/20 shares) + OTM resolution MUST NOT wipe $9.50 to $0!
    pos_part = {
        "trade_id": "T_PART_OTM",
        "token_id": "TOK_P",
        "entry_shares": 20.0,
        "remaining_shares": 10.0,
        "filled_exit_shares": 10.0,
        "notional_usd": 13.0,
        "fee_usd": 0.20,
        "confirmed_realized_cash": 0.0,
        "estimated_exit_cash": 9.50,
        "exit_cash_estimated": True,
        "realized_exit_cash": 9.50,
        "realized_exit_fee": 0.10,
        "status": "EXIT_RESTING",
    }
    h.active_positions["T_PART_OTM"] = pos_part
    res_pnl = h._close_position("T_PART_OTM", pos_part, ExecutionStatus.SETTLED, "MARKET_RESOLVED_LOSS", won=False)
    assert res_pnl is None
    assert pos_part["status"] == "UNRESOLVED_SETTLEMENT"
    assert pos_part["estimated_exit_cash"] == pytest.approx(9.50)
    assert pos_part["exit_cash_estimated"] is True

    # 4b. Two winning positions (15 sh + 15 sh) on same condition_id share one $30.00 redemption tx cleanly!
    h.executor.find_redemption_payouts = lambda cond_id, from_block=None, tx_hash=None: [
        {"transaction_hash": "0xSHARED_REDEEM_TX", "payout_usd": 30.0}
    ]
    for idx in (1, 2):
        tid = f"T_WIN_{idx}"
        h.active_positions[tid] = {
            "trade_id": tid,
            "condition_id": "0xSAME_COND",
            "token_id": "TOK_W",
            "entry_shares": 15.0,
            "remaining_shares": 15.0,
            "winning_shares_held": 15.0,
            "notional_usd": 10.0,
            "fee_usd": 0.15,
            "realized_exit_cash": 0.0,
            "realized_exit_fee": 0.0,
            "status": "AWAITING_ONCHAIN_SETTLEMENT",
        }
    assert h.confirm_onchain_redemption("T_WIN_1") is True
    assert "0xSHARED_REDEEM_TX" not in h.redeemed_tx_hashes
    assert h.redeemed_tx_consumed_usd["0xSHARED_REDEEM_TX"] == pytest.approx(15.0)

    assert h.confirm_onchain_redemption("T_WIN_2") is True
    assert "0xSHARED_REDEEM_TX" in h.redeemed_tx_hashes
    assert "0xSHARED_REDEEM_TX" not in h.redeemed_tx_consumed_usd
    closed_by_id = {c["trade_id"]: c for c in h.closed_positions}
    assert closed_by_id["T_WIN_1"]["payout_usd"] == pytest.approx(15.0)
    assert closed_by_id["T_WIN_2"]["payout_usd"] == pytest.approx(15.0)


def test_p0_5_upward_ask_sweep_resets_age_ask_ms_and_empty_ask_sentinel_not_collapsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    book = L2OrderBook("TOK_SWEEP")
    book.apply_snapshot(
        bids=[{"price": "0.60", "size": "100"}],
        asks=[{"price": "0.62", "size": "100"}, {"price": "0.73", "size": "100"}],
    )
    old_ts = time.time() - 30.0
    book.last_best_ask_change_ts = old_ts
    book._ask_birth_ts[0.62] = old_ts
    book._ask_birth_ts[0.73] = old_ts

    # Sweeping $0.62 -> $0.73 MUST reset best-ask age to fresh (<100ms), NOT inherit 30,000ms!
    book.apply_price_changes([{"price": "0.62", "size": "0", "side": "SELL"}])
    metrics = book.get_metrics()
    assert metrics["best_ask"] == pytest.approx(0.73)
    assert metrics["age_ask_ms"] < 150.0

    # Empty-ask 1.0 sentinel at t0 followed by $0.71 REST refill MUST NOT false-veto as ADVERSE_ASK_COLLAPSE!
    h = _make_live_harvester(tmp_path, monkeypatch)
    h._last_known_collateral = 120.0
    h.high_water_mark_equity = 120.0
    h.executor.get_collateral_balance = lambda *a, **kw: 120.0
    h.executor.get_conditional_balance = lambda *a, **kw: 0.0

    async def _rest_refill_book(_tok):
        return {"bids": [{"price": "0.70", "size": "120"}], "asks": [{"price": "0.71", "size": "120"}]}

    h.executor.get_market_book_async = _rest_refill_book
    snipe_calls = []

    async def _ok_snipe(**kw):
        snipe_calls.append(kw)
        return OrderResult(
            success=True, order_id="0xREF_OK", trade_id=kw["trade_id"], token_id=kw["token_id"],
            target_token=kw["target_token"], side="BUY", price=0.71, size=18.0, notional_usd=12.78,
            fee_usd=0.18, latency_ms=20.0, mode="LIVE_CLOB", execution_status=ExecutionStatus.FILLED,
            confirmed_onchain=True,
        )

    h.executor.execute_snipe_order_async = _ok_snipe
    h.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "0xEX_REF"}

    now_u = time.time()
    shock_empty_t0 = {
        "event_id": "SHK_EMPTY_T0",
        "market_id": "77009",
        "condition_id": "0x77009",
        "t0_unix": now_u,
        "title": "Bitcoin Up or Down - 5PM ET",
        "asset": "BTC",
        "horizon": "1h",
        "shock_direction": "BUY",
        "seconds_to_expiry": 420.0,
        "spot_at_t0": 80300.0,
        "trigger_price": 80300.0,
        "candle_open_spot": 80000.0,
        "twap_60s_open": 80000.0,
        "candle_distance_pct": 0.375,
        "candle_sigma": 0.0018,
        "shock_volume_100ms": 2_500_000.0,
        "shock_ofi": 0.90,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x77009"},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "2" * 30,
                "best_ask": 1.0,
                "best_bid": 0.70,
                "raw_top_asks": [],
                "raw_top_bids": [[0.70, 100.0]],
                "age_ask_ms": 200.0,
                "empty_ask_ms": 12.0,
                "obi_l1": 0.30,
                "age_book_ms": 10.0,
                "book_timestamp": now_u,
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_empty_t0))
    assert len(snipe_calls) == 1
    assert snipe_calls[0]["expected_best_price"] is None

    # latency_trace classification check on REPRICED BY MM & empty_ask_ms
    cls_mm = classify_shock_attempt(
        {"stage_outcome": "GATE_REJECT", "gate_code": "COMPOSITE_EDGE_VETO", "gate_detail": "Ask freshly repriced by MM (age=12ms < 25ms)", "t0_ask": 0.71}
    )
    assert cls_mm["speed_verdict"] == "TOO_SLOW_PRE_EVAL"
    cls_emp = classify_shock_attempt(
        {"stage_outcome": "GATE_REJECT", "gate_code": "PRICE_BAND_REJECT", "empty_ask_ms": 45.0, "t0_ask": 1.0, "eval_ask": 1.0}
    )
    assert cls_emp["speed_verdict"] == "TOO_SLOW_PRE_EVAL"


def test_p0_6_recorder_spot_ts_and_reverse_delta_basis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    rec = PolymarketDualFeed1HRecorder(asset="BTC")
    now_s = time.time()
    now_ns = time.monotonic_ns()
    for i in range(500):
        rec.basis_history.append((now_ns - 500_000_000 + i * 1_000_000, 2.0 + i * 0.01))
    rec.basis_bps = 9.50
    rec.basis_history.append((now_ns, 9.50))
    db = rec.get_delta_basis_100ms()
    assert math.isfinite(db) and db > 2.0

    # Stale spot_ts on SHM must force get_reference_spot_price to skip SHM and hit REST fallback
    h = _make_live_harvester(tmp_path, monkeypatch)
    shm_file = tmp_path / "pm_fast_tick_BTC.json"
    shm_file.write_text(
        json.dumps({"ts": now_s, "spot_ts": now_s - 20.0, "spot": 77777.0}),
        encoding="utf-8",
    )
    rest_resp = MagicMock(status_code=200)
    rest_resp.json.return_value = {"price": "81234.50"}
    h.executor._sync_session = MagicMock()
    h.executor._sync_session.get.return_value = rest_resp
    assert h.get_reference_spot_price("BTC") == pytest.approx(81234.50)


def test_p0_7_and_p0_8_d1_excess_shares_key_and_risk_controller_decoupling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    h = _make_live_harvester(tmp_path, monkeypatch)
    h.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "0xEX_D1"}
    cand = {
        "asset": "BTC",
        "box_type": "DOMINANCE",
        "expiry_ts": time.time() + 600.0,
        "shares": 12.0,
        "leg_a_token_id": "TOK_A",
        "leg_b_token_id": "TOK_B",
        "leg_a_limit_price": 0.48,
        "leg_b_limit_price": 0.49,
        "leg_a_fee_rate": 0.0,
        "leg_b_fee_rate": 0.0,
    }
    res_box = {
        "shares": 12.0,
        "leg_1": {"token_id": "TOK_A", "price": 0.48, "matched_shares": 18.0, "orderID": "0xL1", "is_maker_anchor": True},
        "leg_2": {"token_id": "TOK_B", "price": 0.49, "matched_shares": 12.0, "orderID": "0xL2", "is_maker_anchor": False},
        # Executor emits key "shares" (not "excess_shares")
        "excess_leg": {"token_id": "TOK_A", "shares": 6.0, "price": 0.48, "label": "UP", "is_maker_anchor": True},
    }
    h._register_live_d1_box_positions("BOX_TEST", cand, res_box, 0.0, 0.0)
    assert "BOX_TEST_EXCESS_LEG_RESID" in h.active_positions
    assert h.active_positions["BOX_TEST_EXCESS_LEG_RESID"]["entry_shares"] == pytest.approx(6.0)

    # Risk controller decoupling: box wins do NOT wipe directional consecutive_losses; box scratches do NOT halt directional!
    rc = EmergencyRiskController(max_daily_loss_usd=20.0, max_consecutive_losses=3)
    rc.record_trade_pnl(-4.0, is_non_directional=False)
    rc.record_trade_pnl(-4.0, is_non_directional=False)
    assert rc.consecutive_losses == 2
    assert rc.daily_realized_loss == pytest.approx(8.0)

    rc.record_trade_pnl(+0.25, is_non_directional=True)
    assert rc.consecutive_losses == 2
    assert rc.daily_realized_loss == pytest.approx(8.0)

    for _ in range(4):
        rc.record_trade_pnl(-0.08, is_non_directional=True)
    assert rc.consecutive_losses == 2
    assert rc.halted is False


def test_p1_1_and_p1_2_presign_3asset_eviction_price_grid_and_15m_surgical_taker_sizing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    h = _make_live_harvester(tmp_path, monkeypatch)
    now_u = time.time()

    # Register 6 active 15m + 6 active 1h + 6 upcoming 15m tokens (18 total <= 24 cap: ZERO active 1h tokens evicted!)
    active_1h_tokens = [f"TOK_1H_{i}" for i in range(6)]
    for i in range(6):
        h._register_active_warmed_token(f"TOK_15M_CUR_{i}", now_u + 120.0)
    for tok_1h in active_1h_tokens:
        h._register_active_warmed_token(tok_1h, now_u + 1800.0)
    for i in range(6):
        h._register_active_warmed_token(f"TOK_15M_NXT_{i}", now_u + 1020.0)

    reg = h._active_warmed_token_expiries
    assert len(reg) == 18
    for tok_1h in active_1h_tokens:
        assert tok_1h in reg

    # Overflow past 24 evicts distant future Gamma candles (+7200s+) first, preserving all 18 active 15m/1h tokens!
    for i in range(10):
        h._register_active_warmed_token(f"TOK_DISTANT_FUT_{i}", now_u + 7200.0 + i * 300.0)
    assert len(reg) == 24
    for tok_1h in active_1h_tokens:
        assert tok_1h in reg
    for i in range(6):
        assert f"TOK_15M_CUR_{i}" in reg
        assert f"TOK_15M_NXT_{i}" in reg

    # 15m Surgical Taker (is_maker=False) MUST NOT be penalized by 0.80x subordinate_15m_maker_size_mult!
    tkr_15m = compute_stop_risk_fractional_kelly_ticket(
        live_equity=250.0,
        p_win=0.84,
        entry_px=0.64,
        fee_rate=0.0,
        is_maker=False,
        is_subhourly_15m=True,
        asset="BTC",
    )
    mkr_15m = compute_stop_risk_fractional_kelly_ticket(
        live_equity=250.0,
        p_win=0.84,
        entry_px=0.64,
        fee_rate=0.0,
        is_maker=True,
        is_subhourly_15m=True,
        asset="BTC",
    )
    assert tkr_15m > mkr_15m
    assert mkr_15m == pytest.approx(round(tkr_15m * 0.80, 2), abs=0.05)

    # HotReloadConfigManager: corrupted partial write must NOT latch st_mtime_ns
    cfg_p = tmp_path / "gov_test.json"
    cfg_p.write_text(json.dumps({"schema_version": "5.3.0"}), encoding="utf-8")
    mgr = HotReloadConfigManager(config_path=cfg_p, poll_interval_sec=0.0)
    orig_mtime = mgr._last_mtime_ns
    cfg_p.write_text("{truncated_json", encoding="utf-8")
    changed, _ = mgr.maybe_reload(force=True)
    assert changed is False
    assert mgr._last_mtime_ns == orig_mtime


def test_p0_10_async_tick_cross_stepdown_ws_burst_drain_and_deep_itm_classifier():
    from collections import deque
    import socket
    from types import SimpleNamespace
    from src.polymarket_research.polymarket_terminal_recorder import (
        PolymarketDualFeed1HRecorder,
        _drain_ws_frames,
        _enable_ws_nodelay,
    )

    # 1. Classifier: deep ITM ($0.94 >= $0.88) static ask with MM size refresh -> ALREADY_PRICED_IN
    cls_deep = classify_shock_attempt(
        {
            "stage_outcome": "GATE_REJECT",
            "gate_code": "COMPOSITE_EDGE_VETO",
            "gate_detail": "MM Ask Reload Veto (age_ask=11ms < 25ms, obi_l1=-0.42)",
            "horizon": "1h",
            "t0_ask": 0.94,
            "eval_ask": 0.94,
            "cap_px": 0.76,
        }
    )
    assert cls_deep["speed_verdict"] == "ALREADY_PRICED_IN"
    assert cls_deep["is_speed_miss"] is False

    # True jump ($0.71 -> $0.92) still classified as TOO_SLOW_PRE_EVAL
    cls_jump = classify_shock_attempt(
        {
            "stage_outcome": "GATE_REJECT",
            "gate_code": "COMPOSITE_EDGE_VETO",
            "gate_detail": "Ask freshly repriced by MM (age=9ms < 25ms)",
            "horizon": "1h",
            "t0_ask": 0.71,
            "eval_ask": 0.92,
            "cap_px": 0.76,
        }
    )
    assert cls_jump["speed_verdict"] == "TOO_SLOW_PRE_EVAL"
    assert cls_jump["is_speed_miss"] is True

    # 2. _enable_ws_nodelay & _drain_ws_frames across websockets v16 Assembler and legacy deque
    sock_calls = []
    fake_sock = SimpleNamespace(setsockopt=lambda lvl, opt, val: sock_calls.append((lvl, opt, val)))
    fake_ws_v16 = SimpleNamespace(
        transport=SimpleNamespace(get_extra_info=lambda k: fake_sock if k == "socket" else None),
        recv_messages=SimpleNamespace(
            frames=SimpleNamespace(
                queue=deque([SimpleNamespace(fin=True, data=b"m2"), SimpleNamespace(fin=True, data=b"m3")])
            )
        ),
    )

    async def _recv_v16():
        fr = fake_ws_v16.recv_messages.frames.queue.popleft()
        return fr.data.decode()

    fake_ws_v16.recv = _recv_v16
    assert _enable_ws_nodelay(fake_ws_v16) is True
    assert sock_calls == [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)]
    assert _enable_ws_nodelay(SimpleNamespace()) is False
    drained = asyncio.run(_drain_ws_frames(fake_ws_v16, "m1", max_batch=64))
    assert drained == ["m1", "m2", "m3"]

    # Volume conservation check across coalesced burst vs single-frame evaluate_shock
    rec_burst = PolymarketDualFeed1HRecorder(asset="BTC")
    now_s = 1_775_000_100.0
    now_ns = time.monotonic_ns()
    for idx, ntl in enumerate((1000.0, 2000.0, 3000.0)):
        rec_burst.spot_trades.append((now_ns, int(now_s * 1000), int(now_s * 1000), ntl, True, 85000.0))
        if idx == 2:
            rec_burst.evaluate_shock(now_ns, int(now_s * 1000), source="SPOT")
        else:
            rec_burst._record_volume(ntl)
    total_recorded = sum(v for _, v in rec_burst._vol_buckets)
    assert total_recorded == pytest.approx(6000.0)

    # 3. Async post_maker_entry_order_async: 0.991 tick 400 -> 0.99 crosses book -> 0.98 clean step-down + collateral cache invalidation
    class _Poly400(Exception):
        def __init__(self, msg):
            super().__init__(str(msg))
            self.status_code = 400
            self.error_message = {"error": msg}

    ex = PolymarketLiveExecutor(dry_run=False)
    ex.is_authenticated = True
    ex.auth_mode = "MOCK_LIVE"
    ex._can_use_native_async_post_order = lambda: True
    tok = "777" * 25
    ex.client = SimpleNamespace(
        _ClobClient__tick_sizes={tok: "0.001"},
        get_tick_size=lambda _t: "0.001",
        get_neg_risk=lambda _t: False,
    )
    ex.get_market_book = lambda _t: {"bids": [{"price": "0.98", "size": "100"}], "asks": [{"price": "0.99", "size": "50"}]}
    zh_hist = []

    async def _zh(t_id, px, sh, side, ot, create_options=None, stage=None, max_notional_usd=None, post_only=False):
        zh_hist.append((px, getattr(create_options, "tick_size", None)))
        if stage is not None:
            stage["submitted"] = True
            stage["signed_shares"] = sh
        if len(zh_hist) == 1:
            raise _Poly400("price 0.991 breaks minimum tick size rule 0.01")
        if len(zh_hist) == 2:
            raise _Poly400("invalid post-only order: order crosses book")
        return {"post_resp": {"orderID": "0xASYNC_STEP_98"}, "post_ms": 38.0, "sign_ms": 0.2}

    ex._sign_and_post_async_zero_hop = _zh
    res_step = asyncio.run(
        ex.post_maker_entry_order_async(
            token_id=tok, price=0.991, notional_usd=50.0, side="BUY",
            neg_risk=False, min_price_floor=0.94, max_price_ceiling=0.995,
        )
    )
    assert res_step["success"] is True
    assert res_step["orderID"] == "0xASYNC_STEP_98"
    assert res_step["price"] == pytest.approx(0.98)
    assert len(zh_hist) == 3

    # Balance/allowance 400 invalidates collateral cache immediately
    invalidated = []
    ex.invalidate_collateral_cache = lambda: invalidated.append(True)

    async def _zh_bal(*_a, **_kw):
        raise _Poly400("not enough balance / allowance")

    ex._sign_and_post_async_zero_hop = _zh_bal
    res_bal = asyncio.run(
        ex.post_maker_entry_order_async(
            token_id=tok, price=0.98, notional_usd=50.0, side="BUY",
            neg_risk=False, min_price_floor=0.94, max_price_ceiling=0.995,
        )
    )
    assert res_bal["success"] is False
    assert len(invalidated) == 1


def test_p0_11_feed_ipc_lag_quiet_book_refresh_and_pinned_short_circuit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from unittest.mock import AsyncMock
    from src.polymarket_research import latency_trace as lt_mod
    from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook, PolymarketDualFeed1HRecorder

    # 1. Recorder _refresh_quiet_books_batch refreshes age_book_ms (<50ms) WITHOUT resetting age_ask_ms (45s)!
    rec = PolymarketDualFeed1HRecorder(asset="SOL")
    tok_up = "5" * 30
    bk = L2OrderBook(tok_up)
    bk.apply_snapshot([{"price": "0.63", "size": "120"}], [{"price": "0.64", "size": "150"}])
    t_past = time.time() - 45.0
    bk.last_book_update_ts = t_past
    bk._ask_birth_ts[0.64] = t_past
    bk.last_best_ask_change_ts = t_past
    rec.books["UP"] = bk

    class _FakeResp:
        status = 200
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def json(self):
            return [{"asset_id": tok_up, "bids": [{"price": "0.63", "size": "120"}], "asks": [{"price": "0.64", "size": "150"}]}]

    class _FakeSess:
        def post(self, *_a, **_kw):
            return _FakeResp()

    async def _get_sess():
        return _FakeSess()

    rec.get_session = _get_sess
    n_up = asyncio.run(rec._refresh_quiet_books_batch([tok_up], {tok_up: "UP"}))
    assert n_up == 1
    metrics = rec.books["UP"].get_metrics(compact=True)
    assert metrics["age_book_ms"] < 250.0
    assert metrics["age_ask_ms"] >= 44_500.0

    # 2. Classifier: $0.999 STALE_RECORDER_GUARD & re-classified historical $1.00 row -> ALREADY_PRICED_IN (not FEED / IPC LAG)
    c_sol999 = classify_shock_attempt({
        "asset": "SOL", "horizon": "1h", "side": "UP", "path_type": "PRE_EVAL",
        "gate_code": "STALE_RECORDER_GUARD", "gate_detail": "Stale REST book age 95.7s > 60s",
        "t0_ask": 0.999, "exch_lag_ms": 125.2, "ipc_ms": 5.39,
    })
    assert c_sol999["speed_verdict"] == "ALREADY_PRICED_IN"
    assert c_sol999["is_speed_miss"] is False

    # Re-classification idempotency on historical JSONL row with diagnosis only (no gate_detail key)
    c_hist = classify_shock_attempt({
        "asset": "BTC", "horizon": "15m", "side": "UP", "path_type": "PRE_EVAL",
        "gate_code": "COMPOSITE_EDGE_VETO", "speed_verdict": "TOO_SLOW_FEED_LAG",
        "t0_ask": 1.0, "exch_lag_ms": 156.2, "ipc_ms": 2.48,
        "diagnosis": "Feed/IPC lag blocked entry (Exch 156ms, IPC 2.5ms): Missing live microstructure telemetry: ['age_ask_ms']",
    })
    assert c_hist["speed_verdict"] == "ALREADY_PRICED_IN"
    assert c_hist["is_speed_miss"] is False

    # Genuine mid-band ($0.72) feed lag & EXCHANGE_LAG_REJECT MUST stay TOO_SLOW_FEED_LAG
    c_real_lag = classify_shock_attempt({
        "asset": "SOL", "horizon": "1h", "side": "UP", "path_type": "PRE_EVAL",
        "gate_code": "EXCHANGE_LAG_REJECT", "gate_detail": "exchange_lag=1420ms > 1000ms",
        "t0_ask": 0.999, "exch_lag_ms": 1420.0,
    })
    assert c_real_lag["speed_verdict"] == "TOO_SLOW_FEED_LAG"

    # 3. Harvester: pinned $0.999 ask (dist=+0.92%) short-circuits in 0 HTTP /book calls as ALREADY_PRICED_IN!
    forensic_out = tmp_path / "sf_p011.jsonl"
    monkeypatch.setenv("PM_SHOCK_ATTEMPT_FILE", str(forensic_out))
    h = _make_live_harvester(tmp_path, monkeypatch)
    h.allowed_assets = {"BTC", "ETH", "SOL"}
    rest_calls = []
    h.executor.get_market_book_async = AsyncMock(side_effect=lambda t: rest_calls.append(t) or {})
    now_u = time.time()
    shk_999 = {
        "shock_id": "SOL_1H_999_QUIET",
        "market_id": "6436179",
        "asset": "SOL",
        "horizon": "1h",
        "title": "Solana Up or Down - November 1, 6PM ET",
        "t0_unix": now_u - 0.005,
        "exchange_event_ts_ms": int((now_u - 0.125) * 1000),
        "clob_ws_connected": True,
        "seconds_to_expiry": 480.0,
        "shock_direction": "BUY",
        "shock_ofi": 0.95,
        "spot_at_t0": 181.65,
        "finalized_1h_open": 180.00,
        "candle_open_spot": 180.00,
        "candle_distance_pct": 0.917,
        "candle_sigma": 0.0016,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x999"},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "6" * 30,
                "best_bid": 0.998,
                "best_ask": 0.999,
                "age_book_ms": 95600.0,
                "age_ask_ms": 290400.0,
                "obi_l1": 0.854,
                "book_timestamp": now_u - 95.6,
                "raw_top_bids": [[0.998, 500.0]],
                "raw_top_asks": [[0.999, 100.0]],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shk_999))
    lt_mod.flush(2.0)
    assert len(rest_calls) == 0, "Pinned $0.998/$0.999 deep-ITM book must short-circuit before HTTP /book!"
    emitted = [json.loads(x) for x in forensic_out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert any(r["shock_id"] == "SOL_1H_999_QUIET" and r["speed_verdict"] == "ALREADY_PRICED_IN" for r in emitted)



#!/usr/bin/env python3
"""Unit & integration tests for `DirectionalWfoShadowManager` (Candidate A Hybrid z-Split + Candidate B BTC-Only 5m Sniper)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import src.polymarket_research.polymarket_paper_trader as paper_mod
from src.polymarket_research.directional_wfo_shadow_sleeves import DirectionalWfoShadowManager


def _write_fast_tick(shm_dir: Path, asset: str, market_id: str, horizon: str, spot: float, cl_spot: float, auth_cl_open: float, bid: float, ask: float, ask_sz: float = 40.0, ts: float | None = None) -> None:
    now = ts if ts is not None else time.time()
    up_book = {
        "best_bid": bid,
        "best_ask": ask,
        "bid_size_l1": 50.0,
        "ask_size_l1": ask_sz,
        "raw_top_bids": [[bid, 50.0]],
        "raw_top_asks": [[ask, ask_sz]],
        "is_crossed": False,
    }
    dn_book = {
        "best_bid": round(max(0.01, 1.0 - ask - 0.01), 2),
        "best_ask": round(min(0.99, 1.0 - bid + 0.01), 2),
        "bid_size_l1": 50.0,
        "ask_size_l1": 50.0,
        "raw_top_bids": [[round(max(0.01, 1.0 - ask - 0.01), 2), 50.0]],
        "raw_top_asks": [[round(min(0.99, 1.0 - bid + 0.01), 2), 50.0]],
        "is_crossed": False,
    }
    snap_key = "m5" if horizon == "5m" else ("m15" if horizon == "15m" else "h1")
    payload = {
        "ts": now,
        "timestamp_unix": now,
        "asset": asset,
        "spot_price": spot,
        "spot": spot,
        "chainlink_proxy_spot": cl_spot,
        "chainlink_twap_60s": cl_spot,
        "markets": {
            str(market_id): {
                "market_id": str(market_id),
                "asset": asset,
                "horizon": horizon,
                "timestamp_unix": now,
                "spot_price": spot,
                "UP": up_book,
                "DOWN": dn_book,
            }
        },
    }
    if snap_key in ("m5", "m15"):
        payload[snap_key] = {
            "market_id": str(market_id),
            "horizon": horizon,
            "authoritative_chainlink_open": auth_cl_open,
            "UP": up_book,
            "DOWN": dn_book,
        }
    (shm_dir / f"pm_fast_tick_{asset.upper()}.json").write_text(json.dumps(payload), encoding="utf-8")


def _make_shock(market_id: str, spot: float, open_sp: float, ask_t0: float = 0.72, bid_t0: float = 0.70, tte: float = 240.0, t0: float | None = None) -> dict:
    now = t0 if t0 is not None else time.time()
    return {
        "market_id": market_id,
        "title": "Bitcoin Up or Down - 15m Window",
        "asset": "BTC",
        "horizon": "15m",
        "t0_unix": now,
        "seconds_to_expiry": tte,
        "shock_direction": "BUY",
        "shock_ofi": 0.85,
        "spot_at_t0": spot,
        "candle_open_spot": open_sp,
        "twap_60s_open": open_sp,
        "chainlink_proxy_usd_spot": spot - 25.0,
        "authoritative_chainlink_open": open_sp - 25.0,
        "candle_sigma": 0.0025,  # -> sigma_1h = 0.0050, sigma_rem(240s) ~= 0.001291
        "pre_shock_features_t0": {
            "UP": {
                "best_bid": bid_t0,
                "best_ask": ask_t0,
                "ask_size_l1": 40.0,
                "raw_top_bids": [[bid_t0, 40.0]],
                "raw_top_asks": [[ask_t0, 40.0]],
            }
        },
    }


def test_candidate_a_shielded_maker_shield_and_zero_fee_tp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shm_dir = tmp_path / "shm"
    shm_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(shm_dir))
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")

    mgr = DirectionalWfoShadowManager(tmp_path, latency_sec=0.0)
    now = time.time()

    # 0. Verify 5m shock is strictly rejected by Candidate A while 15m shock is accepted
    s_5m = dict(_make_shock("mkt_5m_skip", spot=100120.0, open_sp=100000.0, t0=now), horizon="5m", title="Bitcoin Up or Down - 5m Window")
    assert mgr.on_shock_signal(s_5m) is False

    # 1. Moderate z_strike (~0.93 in [0.78, 1.20)) -> routes to SHIELDED_MAKER_FIRST; shield cancels if cushion decays >50%
    s1 = _make_shock("mkt_hz_shield", spot=100120.0, open_sp=100000.0, ask_t0=0.72, bid_t0=0.70, t0=now)
    assert mgr.on_shock_signal(s1) is True
    assert mgr.hz_funnel["maker_branch_queued"] == 1
    assert mgr.hz_funnel["taker_branch_queued"] == 0

    # Cushion drops from +120 (+12 bps) to +40 (+4 bps, >50% decay) -> shield immediately cancels!
    _write_fast_tick(shm_dir, "BTC", "mkt_hz_shield", "15m", spot=100040.0, cl_spot=99975.0 + 40.0, auth_cl_open=99975.0, bid=0.69, ask=0.71, ts=now + 0.1)
    mgr.poll_tick()
    assert mgr.hz_funnel["shield_canceled"] == 1
    assert "mkt_hz_shield" not in mgr.hz_pending
    assert "mkt_hz_shield" not in mgr.hz_open

    # 2. Second signal holds cushion -> posts resting maker at $0.71 -> fills passively at 0% fee -> exits via hold_98 Maker TP
    s2 = _make_shock("mkt_hz_fill", spot=100120.0, open_sp=100000.0, ask_t0=0.72, bid_t0=0.70, t0=now)
    assert mgr.on_shock_signal(s2) is True
    _write_fast_tick(shm_dir, "BTC", "mkt_hz_fill", "15m", spot=100125.0, cl_spot=100100.0, auth_cl_open=99975.0, bid=0.70, ask=0.73, ts=now + 0.2)
    mgr.poll_tick()
    assert mgr.hz_pending["mkt_hz_fill"]["phase"] == "RESTING_MAKER"
    assert mgr.hz_pending["mkt_hz_fill"]["maker_px"] == 0.71

    # Passive maker fill when ask touches $0.71 while spot cushion remains intact
    _write_fast_tick(shm_dir, "BTC", "mkt_hz_fill", "15m", spot=100130.0, cl_spot=100105.0, auth_cl_open=99975.0, bid=0.70, ask=0.71, ts=now + 0.6)
    mgr.poll_tick()
    assert mgr.hz_funnel["maker_filled"] == 1
    pos = mgr.hz_open["mkt_hz_fill"]
    assert pos["is_maker_entry"] is True
    assert pos["entry_price"] == 0.71
    assert pos["taker_fee_usd"] == 0.0
    assert pos["maker_rebate_20pct_est_usd"] > 0.0

    # Rally to best_bid = 0.98 after >=4.0s settlement guard -> MAKER_TP_98_FILLED with 0% exit fee
    _write_fast_tick(shm_dir, "BTC", "mkt_hz_fill", "15m", spot=100250.0, cl_spot=100225.0, auth_cl_open=99975.0, bid=0.98, ask=0.99, ts=now + 5.5)
    mgr.poll_tick()
    assert "mkt_hz_fill" not in mgr.hz_open
    assert len(mgr.hz_trades) == 1
    closed = mgr.hz_trades[0]
    assert closed["exit_reason"] == "MAKER_TP_98_FILLED"
    assert closed["exit_fee_usd"] == 0.0
    assert closed["net_pnl_usd"] > 5.0


def test_candidate_a_high_z_phase3a_rescue_and_3zone_salvage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shm_dir = tmp_path / "shm"
    shm_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(shm_dir))
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")

    mgr = DirectionalWfoShadowManager(tmp_path, latency_sec=0.0)
    now = time.time()

    # High z_strike (~1.55 >= 1.20) at ask_t0 = 0.80 -> TAKER_PLUS_P3A
    # If ask_now jumps to 0.82 (> 0.81 Smart FAK cap), transitions to STEP4_PHASE3A_MAKER_RESCUE instead of paying 82c taker!
    s_p3a = _make_shock("mkt_p3a", spot=100200.0, open_sp=100000.0, ask_t0=0.80, bid_t0=0.79, t0=now)
    assert mgr.on_shock_signal(s_p3a) is True
    assert mgr.hz_funnel["taker_branch_queued"] == 1
    _write_fast_tick(shm_dir, "BTC", "mkt_p3a", "15m", spot=100205.0, cl_spot=100180.0, auth_cl_open=99975.0, bid=0.80, ask=0.82, ts=now + 0.1)
    mgr.poll_tick()
    assert mgr.hz_pending["mkt_p3a"]["phase"] == "RESTING_MAKER"
    assert mgr.hz_pending["mkt_p3a"]["branch_step_tag"] == "STEP4_PHASE3A_MAKER_RESCUE"
    assert mgr.hz_pending["mkt_p3a"]["maker_px"] == 0.80

    # Passive rescue fill at $0.80 -> 0% taker fee
    _write_fast_tick(shm_dir, "BTC", "mkt_p3a", "15m", spot=100205.0, cl_spot=100180.0, auth_cl_open=99975.0, bid=0.79, ask=0.80, ts=now + 0.5)
    mgr.poll_tick()
    assert mgr.hz_funnel["phase3a_rescue_filled"] == 1
    assert mgr.hz_open["mkt_p3a"]["taker_fee_usd"] == 0.0

    # Simulate 3-Zone `spot_only_9bps_18s` salvage: mid-TTE (220s > 180s) requires >=11 bps arm, >=9 bps sustain for >=18s
    mgr.on_telemetry_tick("mkt_p3a", {
        "timestamp_unix": now + 2.0,
        "seconds_to_expiry": 220.0,
        "binance_spot": 99880.0,  # -12 bps wrong-side (>= 11 bps arm)
        "chainlink_proxy_usd_spot": 99855.0,
        "UP": {"best_bid": 0.34, "best_ask": 0.36, "raw_top_bids": [[0.34, 60.0]], "raw_top_asks": [[0.36, 60.0]]},
    })
    assert "mkt_p3a" in mgr.hz_open  # armed, not yet 18s
    mgr.on_telemetry_tick("mkt_p3a", {
        "timestamp_unix": now + 20.5,
        "seconds_to_expiry": 201.5,
        "binance_spot": 99905.0,  # -9.5 bps wrong-side (>= 9 bps sustain after 18.5s)
        "chainlink_proxy_usd_spot": 99880.0,
        "UP": {"best_bid": 0.32, "best_ask": 0.34, "raw_top_bids": [[0.32, 60.0]], "raw_top_asks": [[0.34, 60.0]]},
    })
    assert "mkt_p3a" not in mgr.hz_open
    assert mgr.hz_trades[-1]["exit_reason"] == "SALVAGE_SPOT_ONLY_3ZONE"


def test_candidate_b_btc_5m_only_dual_oracle_and_paper_trader_wiring(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shm_dir = tmp_path / "shm"
    shm_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(shm_dir))
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")

    monkeypatch.setattr(paper_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(paper_mod, "STATE_FILE", tmp_path / "paper_trader_state.json")
    monkeypatch.setattr(paper_mod, "SOL_SHADOW_STATE_FILE", tmp_path / "sol_state.json")
    monkeypatch.setattr(paper_mod, "XRP_SHADOW_STATE_FILE", tmp_path / "xrp_state.json")

    trader = paper_mod.PolymarketForwardPaperTrader()
    trader.wfo_shadow.latency_sec = 0.0
    now = time.time()

    b5_path = tmp_path / "polymarket_5m_telemetry_btc.jsonl"
    rows = [
        # 1. ETH 5m & SOL 5m rows MUST be hard-ignored
        {
            "timestamp_unix": now,
            "market_id": "eth_5m_ignored",
            "asset": "ETH",
            "horizon": "5m",
            "seconds_to_expiry": 120.0,
            "binance_spot": 2510.0,
            "binance_open": 2500.0,
            "UP": {"best_bid": 0.72, "best_ask": 0.74, "ask_size_l1": 40.0},
        },
        {
            "timestamp_unix": now,
            "market_id": "sol_5m_ignored",
            "asset": "SOL",
            "horizon": "5m",
            "seconds_to_expiry": 120.0,
            "binance_spot": 182.0,
            "binance_open": 180.0,
            "UP": {"best_bid": 0.72, "best_ask": 0.74, "ask_size_l1": 40.0},
        },
        # 2. Cross-currency basis trap: Binance USDT is UP (+8 bps), but Chainlink USD is DOWN (-2 bps) -> MUST reject!
        {
            "timestamp_unix": now,
            "market_id": "btc_5m_basis_trap",
            "asset": "BTC",
            "horizon": "5m",
            "seconds_to_expiry": 120.0,
            "binance_spot": 100080.0,
            "binance_open": 100000.0,
            "twap_60s_open": 100000.0,
            "chainlink_proxy_usd_spot": 99950.0,
            "authoritative_chainlink_open": 99970.0,
            "UP": {"best_bid": 0.72, "best_ask": 0.74, "ask_size_l1": 40.0},
            "DOWN": {"best_bid": 0.25, "best_ask": 0.27, "ask_size_l1": 40.0},
        },
        # 3. Clean BTC 5m Sniper setup: both USDT and USD Chainlink cushions >= +10 bps, z >= 0.80, TTE=120s
        {
            "timestamp_unix": now,
            "market_id": "btc_5m_valid",
            "asset": "BTC",
            "horizon": "5m",
            "title": "Bitcoin Up or Down - 5m",
            "seconds_to_expiry": 120.0,
            "binance_spot": 100110.0,
            "binance_open": 100000.0,
            "twap_60s_open": 100005.0,
            "chainlink_proxy_usd_spot": 100085.0,
            "authoritative_chainlink_open": 99975.0,
            "UP": {"best_bid": 0.74, "best_ask": 0.76, "ask_size_l1": 35.0},
            "DOWN": {"best_bid": 0.23, "best_ask": 0.25, "ask_size_l1": 35.0},
        },
    ]
    b5_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    _write_fast_tick(shm_dir, "BTC", "btc_5m_valid", "5m", spot=100112.0, cl_spot=100087.0, auth_cl_open=99975.0, bid=0.74, ask=0.76, ts=now + 0.5)

    trader.wfo_shadow.poll_tick()
    assert trader.wfo_shadow.b5_funnel["ticks_scanned"] == 2  # Only the 2 BTC 5m rows!
    assert trader.wfo_shadow.b5_funnel["candidates_queued"] == 1
    assert trader.wfo_shadow.b5_funnel["taker_filled"] == 1
    assert "btc_5m_valid" in trader.wfo_shadow.b5_open

    # Verify open-position persistence across restart and resolution settlement via PolymarketForwardPaperTrader.settle_market
    reloaded_trader = paper_mod.PolymarketForwardPaperTrader()
    assert "btc_5m_valid" in reloaded_trader.wfo_shadow.b5_open

    reloaded_trader.settle_market("btc_5m_valid", {"market_id": "btc_5m_valid", "winning_outcome": "UP"}, historical=False)
    assert "btc_5m_valid" not in reloaded_trader.wfo_shadow.b5_open
    assert len(reloaded_trader.wfo_shadow.b5_trades) == 1
    settled = reloaded_trader.wfo_shadow.b5_trades[0]
    assert settled["exit_reason"] == "RESOLVED_WIN"
    assert settled["won"] is True
    assert (tmp_path / "state_shadow_btc_5m.json").exists()
    assert (tmp_path / "state_shadow_hybrid_zsplit.json").exists()


def test_v395_sleeve1_deep_research_bugfixes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verifies all 6 deterministic v3.9.5 Deep Research bug fixes:
      1. `SLEEVE_HYBRID_ZSPLIT_SHADOW` parses standard 15m interval titles ("2:00PM-2:15PM ET") when `horizon` is None.
      2. `validate_cross_asset_directional_conflict` enforces true settlement interval overlap (non-overlapping 15m windows pass).
      3. `validate_cross_asset_lead_lag` & `evaluate_coinbase_venue_veto` extend to SOL with 0-DOF sigma scaling.
      4. `_attempt_live_phase3a_maker_rescue` compares instantaneous `chainlink_proxy_spot` (not lagging 60s TWAP) for TTE > 60s.
      5. `SLEEVE_SOL_V392_SHADOW` multiplies 15m `candle_sigma * 2.0`, pairs USD-to-USD strike, caps ask <= $0.81, and gates graduation on >=30 v3.9.5 trades.
    """
    import asyncio
    from unittest.mock import MagicMock
    import src.polymarket_research.polymarket_paper_trader as paper_mod
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        evaluate_coinbase_venue_veto,
    )

    shm_dir = tmp_path / "shm_v395"
    shm_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(shm_dir))
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")

    # 1. Hybrid z-Split 15m range-title parsing without explicit `horizon` or `series_slug`
    mgr = DirectionalWfoShadowManager(data_dir=tmp_path, latency_sec=0.0)
    now = 1790800500.0
    ok_rng = mgr.on_shock_signal(
        {
            "market_id": "mkt_15m_title_only",
            "title": "Bitcoin Up or Down - October 30, 2:00PM-2:15PM ET",
            "t0_unix": now,
            "seconds_to_expiry": 300.0,
            "shock_direction": "BUY",
            "shock_ofi": 0.85,
            "spot_at_t0": 100120.0,
            "candle_open_spot": 100000.0,
            "candle_sigma": 0.0025,
            "pre_shock_features_t0": {"UP": {"best_bid": 0.72, "best_ask": 0.74, "ask_size_l1": 40.0}},
        }
    )
    assert ok_rng is True
    assert mgr.hz_pending["mkt_15m_title_only"]["horizon"] == "15m"
    assert mgr.hz_funnel["signals_seen"] == 1

    # 5m range title ("2:00PM-2:05PM ET") must be rejected from 15m/1h Hybrid shadow
    assert mgr.on_shock_signal(
        {
            "market_id": "mkt_5m_title_only",
            "title": "Bitcoin Up or Down - October 30, 2:00PM-2:05PM ET",
            "t0_unix": now,
            "seconds_to_expiry": 180.0,
            "shock_direction": "BUY",
            "shock_ofi": 0.85,
            "spot_at_t0": 100120.0,
            "candle_open_spot": 100000.0,
            "candle_sigma": 0.0015,
            "pre_shock_features_t0": {"UP": {"best_bid": 0.72, "best_ask": 0.74, "ask_size_l1": 40.0}},
        }
    ) is False

    # 2. Cross-Asset Directional Conflict: sequential non-overlapping 15m candles MUST NOT block each other!
    active_btc_15m = [{"asset": "BTC", "target_token": "UP", "candle_expiry_ts": 1000900.0, "is_subhourly": True, "candle_duration_s": 900.0}]
    ok_next_15m, _ = PolymarketLiveExecutor.validate_cross_asset_directional_conflict(
        candidate_asset="ETH",
        candidate_direction="DOWN",
        candidate_expiry_ts=1001800.0,  # Next 15m candle [1000900, 1001800] vs [1000000, 1000900] -> 0s overlap!
        active_positions=active_btc_15m,
        max_expiry_window_delta=2700.0,
        candidate_duration_s=900.0,
    )
    assert ok_next_15m is True
    ok_same_15m, _ = PolymarketLiveExecutor.validate_cross_asset_directional_conflict(
        candidate_asset="SOL",
        candidate_direction="DOWN",
        candidate_expiry_ts=1000900.0,  # Same 15m candle -> MUST block opposing direction!
        active_positions=active_btc_15m,
        max_expiry_window_delta=2700.0,
        candidate_duration_s=900.0,
    )
    assert ok_same_15m is False

    # 3. Lead-lag check for SOL + 0-DOF sigma-scaled Coinbase veto
    passed_sol_ll, _, _ = PolymarketLiveExecutor.validate_cross_asset_lead_lag(
        target_asset="SOL", target_direction="UP", btc_direction="DOWN", z_alt=1.2, z_btc=-1.1
    )
    assert passed_sol_ll is False
    # -5.0 bps 2s Coinbase move vetoes BTC (threshold -4.0 bps), but passes SOL (0.0085/0.0050 = 1.70x -> -6.8 bps)
    assert evaluate_coinbase_venue_veto({"asset": "BTC", "coinbase_spot": 70000.0, "coinbase_move_bps_2s": -5.0}, "UP")[0] is True
    assert evaluate_coinbase_venue_veto({"asset": "SOL", "coinbase_spot": 180.0, "coinbase_move_bps_2s": -5.0}, "UP")[0] is False

    # 4. Phase 3A Maker shield uses instantaneous `chainlink_proxy_spot` (not lagging `chainlink_twap_60s`) for TTE > 60s
    monkeypatch.setenv("PM_LIVE_PHASE3A_TTL_SEC", "0.20")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "harv_p3a.json")
    h = PolymarketLiveHarvester(dry_run=False)
    h.enable_live_phase3a_maker_fallback = True
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.place_passive_maker_entry = MagicMock(return_value={"success": True, "orderID": "OID_P3A_INST"})
    h.executor.cancel_order = MagicMock(return_value={"is_canceled": True, "outcome": "FILLED"})
    h.executor.get_order_fill_summary = MagicMock(return_value={"matched": 20.0, "avg_price": 0.78, "terminal": True})
    # Instantaneous USD spot jumped to 100120 (+12 bps over 100000 open), while lagging 60s TWAP is still 100020 (+2 bps < 75% of +12 bps!)
    (shm_dir / "pm_fast_tick_BTC.json").write_text(
        json.dumps({
            "timestamp_unix": time.time(),
            "spot_price": 100150.0,
            "chainlink_proxy_spot": 100118.0,
            "chainlink_twap_60s": 100020.0,
            "UP": {"best_bid": 0.77, "best_ask": 0.79, "bids": [[0.77, 100.0]], "asks": [[0.79, 100.0]]},
        }),
        encoding="utf-8",
    )
    res_p3a = asyncio.run(
        h._attempt_live_phase3a_maker_rescue(
            trade_id="T_P3A_INST",
            token_id="123456789012345678901234",
            target_token="UP",
            asset_str="BTC",
            effective_notional=16.0,
            first_ask=0.79,
            first_bid=0.77,
            min_allowed_price=0.55,
            max_allowed_price=0.82,
            open_spot=100000.0,
            entry_spot_ref=100120.0,
            spot_denom="USD",
            tte=300.0,
            pre_cond_bal=0.0,
            book_snapshot={"bids": [{"price": "0.77", "size": "100"}], "asks": [{"price": "0.79", "size": "100"}]},
            is_subhourly=True,
        )
    )
    assert res_p3a is not None and res_p3a.success is True and res_p3a.mode == "LIVE_PHASE3A_MAKER_IN"

    # 5. SLEEVE_SOL_V392_SHADOW: 15m sigma * 2.0, USD-to-USD strike, <= $0.81 cap, and v395 graduation gate
    for attr, fn in (
        ("DATA_DIR", tmp_path),
        ("STATE_FILE", tmp_path / "pt_state.json"),
        ("DEV_LEDGER_FILE", tmp_path / "pt_dev.jsonl"),
        ("VALIDATION_LEDGER_FILE", tmp_path / "pt_val.jsonl"),
        ("SOL_SHADOW_LEDGER_FILE", tmp_path / "sol_v395.jsonl"),
        ("SOL_SHADOW_STATE_FILE", tmp_path / "sol_v395_state.json"),
    ):
        monkeypatch.setattr(paper_mod, attr, fn)
    pt = paper_mod.PolymarketForwardPaperTrader()
    # Pre-seed 35 legacy (pre-v395) winning trades: must NOT trigger ready_for_live_graduation!
    pt.sol_shadow_trades = [{"trade_id": f"LEG_{i}", "net_pnl_usd": 3.0, "won": True} for i in range(35)]
    pt.save_sol_shadow_state()
    sol_st = json.loads((tmp_path / "sol_v395_state.json").read_text(encoding="utf-8"))
    assert sol_st["ready_for_live_graduation"] is False
    assert sol_st["v395_clean_trades_settled"] == 0

    # Low z_strike setup that previously snuck through because 15m candle_sigma (0.0045) wasn't multiplied by 2.0!
    assert pt._evaluate_sol_shadow_sleeve(
        {
            "market_id": "sol_low_z",
            "title": "Solana Up or Down - October 30, 2:00PM-2:15PM ET",
            "horizon": "15m",
            "t0_unix": now,
            "seconds_to_expiry": 360.0,
            "shock_direction": "BUY",
            "shock_volume_100ms": 200000.0,
            "shock_ofi": 0.80,
            "authoritative_chainlink_open": 180.00,
            "chainlink_proxy_spot": 180.23,  # +0.128% cushion; with sigma_1h=0.0090 & TTE=360s -> sigma_rem=0.285% -> z=0.45 < 0.78!
            "twap_60s_open": 179.50,         # USDT open would have falsely inflated cushion to +0.40% if mixed!
            "spot_at_t0": 180.35,
            "candle_sigma": 0.0045,
            "pre_shock_features_t0": {"UP": {"best_bid": 0.72, "best_ask": 0.74, "raw_top_asks": [[0.74, 40.0]], "raw_top_bids": [[0.72, 40.0]]}},
        }
    ) is False


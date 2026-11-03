#!/usr/bin/env python3
"""
Comprehensive Unit & Integration Suite for v3.9.5 Sleeve 1 All 3 Tracks:
  - Track A: 0-DOF Plumbing Bug Fixes & Riskless Structural Locks (Traps #1-#6)
  - Track B: Purged WFO & Simulator Upgrades (`unit_var_t4`, Kemna-Vorst bridge, Complement Shield, 5m split)
  - Track C: Shadow Sleeves (`SOL 5m` canary, `XAU 15m` 3-decimal USD Maker, Complement Shield, Micro-Batch Tournament)
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from scripts.honest_purged_wfo_optimizer import infer_asset_and_horizon
from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon
from src.polymarket_research.directional_wfo_shadow_sleeves import (
    DirectionalWfoShadowManager,
    compute_synthetic_xau_usd_anchor,
    is_xau_cme_blackout_or_inactive_session,
)
from src.polymarket_research.exact_twap_lock_engine import (
    compute_kemna_vorst_twap_sigma_rem,
    compute_unit_variance_student_t_cdf,
    should_suppress_final60s_twap_salvage,
    student_t_df4_cdf,
)
from src.polymarket_research.net_alpha_opportunity_engine import (
    evaluate_d1_15m_to_5m_corridor_conversion,
    evaluate_guarded_complement_merge,
    rank_microbatch_shock_tournament,
)
from src.polymarket_research.orderflow_wfo_simulators import (
    compute_v395_pricing_and_twap_gate,
    simulate_microclip_cascade_entry,
)
from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    compute_composite_edge_score,
    compute_correlated_truncated_kelly_size,
    compute_max_acceptable_ask,
)
from src.polymarket_research.polymarket_terminal_recorder import (
    L2OrderBook,
    PolymarketDualFeed1HRecorder,
)


def test_track_a_svi_continuity_and_5m_vol_scaling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PM_SVI_DISABLE_BG_REFRESH", "1")
    low = compute_max_acceptable_ask(
        asset="BTC",
        dist_pct=0.0899,
        tte_sec=240.0,
        shock_ofi=0.90,
        shock_vol_usd=1_800_000.0,
        age_ask_ms=300.0,
        is_subhourly_15m=True,
        candle_sigma=0.0025,
    )
    high = compute_max_acceptable_ask(
        asset="BTC",
        dist_pct=0.0901,
        tte_sec=240.0,
        shock_ofi=0.90,
        shock_vol_usd=1_800_000.0,
        age_ask_ms=300.0,
        is_subhourly_15m=True,
        candle_sigma=0.0025,
    )
    # C^0 continuity across 0.09%: zero 5-cent discontinuity cliff
    assert abs(high["p_max"] - low["p_max"]) < 0.005
    assert high["p_max"] >= low["p_max"]

    # Verify 5m uses sqrt(12) hourly vol scaling vs 15m 2.0x scaling
    m5 = compute_max_acceptable_ask(
        asset="BTC",
        dist_pct=0.12,
        tte_sec=120.0,
        shock_ofi=0.85,
        shock_vol_usd=1_500_000.0,
        age_ask_ms=250.0,
        is_5m=True,
        candle_sigma=0.0018,  # 0.0018 * sqrt(12) = 0.006235 > 0.0035 floor
    )
    m15 = compute_max_acceptable_ask(
        asset="BTC",
        dist_pct=0.12,
        tte_sec=120.0,
        shock_ofi=0.85,
        shock_vol_usd=1_500_000.0,
        age_ask_ms=250.0,
        is_subhourly_15m=True,
        candle_sigma=0.0018,  # 0.0018 * 2.0 = 0.0036
    )
    ratio = m5["sigma_rem_pct"] / m15["sigma_rem_pct"]
    assert math.isclose(ratio, math.sqrt(12.0) / 2.0, rel_tol=1e-2)

    edge_5m = compute_composite_edge_score(
        {"asset": "BTC", "horizon": "5m", "candle_sigma": 0.0018, "candle_distance_pct": 0.10, "seconds_to_expiry": 120.0, "shock_ofi": 0.9},
    )
    assert isinstance(edge_5m, dict)


def test_track_a_kelly_monotonicity_no_step_inversion() -> None:
    sizes = [
        compute_correlated_truncated_kelly_size(
            live_equity=200.0,
            entry_px=0.72,
            p_win=pw,
            kelly_multiplier=1.0,
            min_lot_usd=8.0,
            max_ticket_cap=48.0,
            default_sizing_pct=0.24,
        )
        for pw in (0.66, 0.68, 0.70, 0.72, 0.74, 0.76, 0.78, 0.80, 0.84)
    ]
    positive_sizes = [s for s in sizes if s > 0.0]
    assert len(positive_sizes) >= 5
    for prev_s, next_s in zip(sizes, sizes[1:]):
        assert next_s >= prev_s - 1e-6, f"Kelly inversion detected: {sizes}"


def test_track_a_l2_orderbook_per_level_birth_timestamps() -> None:
    book = L2OrderBook("tok_test")
    book.apply_snapshot(
        bids=[{"price": "0.69", "size": "100"}],
        asks=[{"price": "0.72", "size": "100"}, {"price": "0.73", "size": "150"}],
    )
    time.sleep(0.045)

    # Trap #5: $3.60 retail micro-nibble at $0.72 (`100 -> 95` shares) MUST NOT reset `age_ask_ms` to 0ms!
    book.apply_price_changes([{"price": "0.72", "size": "95", "side": "SELL"}])
    snap_flicker = book.top_of_book()
    assert snap_flicker["best_ask"] == 0.72
    assert snap_flicker["age_ask_ms"] is not None and snap_flicker["age_ask_ms"] >= 35.0

    # Downward ask step-in to $0.70 resets `age_ask_ms` near 0ms
    book.apply_price_changes([{"price": "0.70", "size": "80", "side": "SELL"}])
    snap_stepin = book.top_of_book()
    assert snap_stepin["best_ask"] == 0.70
    assert snap_stepin["age_ask_ms"] is not None and snap_stepin["age_ask_ms"] < 20.0

    # Let $0.70 age, then test >= 25% institutional size reload (`80 -> 110` shares) resets birth timestamp
    time.sleep(0.045)
    assert book.top_of_book()["age_ask_ms"] >= 35.0
    book.apply_price_changes([{"price": "0.70", "size": "110", "side": "SELL"}])
    assert book.top_of_book()["age_ask_ms"] < 20.0


def test_track_a_kemna_vorst_c1_bridge_and_final60s_salvage_shield() -> None:
    # C^0 + C^1 continuity at tau = 60.0s
    eps = 1e-3
    s_left = compute_kemna_vorst_twap_sigma_rem(0.0060, 60.0 - eps)
    s_at = compute_kemna_vorst_twap_sigma_rem(0.0060, 60.0)
    s_right = compute_kemna_vorst_twap_sigma_rem(0.0060, 60.0 + eps)
    assert abs(s_right - s_left) < 1e-7
    d_left = (s_at - compute_kemna_vorst_twap_sigma_rem(0.0060, 60.0 - 0.05)) / 0.05
    d_right = (compute_kemna_vorst_twap_sigma_rem(0.0060, 60.0 + 0.05) - s_at) / 0.05
    assert math.isclose(d_left, d_right, rel_tol=2e-2)

    # Recorder settlement TWAP slice
    rec = PolymarketDualFeed1HRecorder.__new__(PolymarketDualFeed1HRecorder)
    now = 1_760_000_085.0
    end_ts = 1_760_000_100.0  # rem = 15s -> 75% banked
    rec._cl_proxy_history = [(end_ts - 55.0 + i * 5.0, 100_120.0) for i in range(9)]
    tw_mean, tw_wt = rec.get_settlement_twap_slice(end_ts, now=now)
    assert math.isclose(tw_mean, 100_120.0, rel_tol=1e-6)
    assert math.isclose(tw_wt, 0.75, abs_tol=1e-4)
    assert rec.get_settlement_twap_slice(end_ts, now=end_ts - 75.0) == (0.0, 0.0)

    # Transient spot wick below strike (`99,990 < 100,000`) at 15s left while 75% banked TWAP is `100,120`:
    # Projected settlement TWAP = `0.75 * 100120 + 0.25 * 99990 = 100,087.50 >> 100,000` -> suppress false dump!
    suppressed, z_tw = should_suppress_final60s_twap_salvage(
        side="UP",
        strike_open=100_000.0,
        current_spot=99_990.0,
        twap_locked_mean=tw_mean,
        tte_sec=15.0,
        sigma_1h=0.0050,
        twap_locked_weight=tw_wt,
    )
    assert suppressed is True
    assert z_tw >= 1.25

    # Genuine OTM TWAP (`99,900 < 100,000`) -> must NOT suppress salvage!
    suppressed_bad, _ = should_suppress_final60s_twap_salvage(
        side="UP",
        strike_open=100_000.0,
        current_spot=99_910.0,
        twap_locked_mean=99_900.0,
        tte_sec=15.0,
        sigma_1h=0.0050,
        twap_locked_weight=0.75,
    )
    assert suppressed_bad is False


def test_track_a_trap6_guarded_complement_merge_and_atomic_sequence(tmp_path: Path) -> None:
    # Trap #6: 20-share position vs $0.01 OPP ask requires buying 100 OPP shares ($1.00 floor) -> $0.9465/sh < $0.9820/sh!
    bad = evaluate_guarded_complement_merge(rem_shares=20.0, opp_ask=0.01, opp_ask_size=200.0)
    assert bad["approved"] is False
    assert bad["reason"] == "OVERBUY_DILUTION_BELOW_MAKER_98_HURDLE"
    assert bad["net_proceeds_ps"] < 0.95

    # 100-share position vs $0.01 OPP ask -> zero excess over-buy, net ~$0.9893/sh >= $0.9820/sh, 0.001 tick size
    good = evaluate_guarded_complement_merge(rem_shares=100.0, opp_ask=0.01, opp_ask_size=150.0)
    assert good["approved"] is True
    assert good["tick_size"] == "0.001"
    assert good["excess_unmerged_shares"] == 0.0
    assert good["net_proceeds_ps"] >= 0.989
    assert good["atomic_sequence"] == (
        "FAK_BUY_OPP",
        "CONFIRM_OPP_FILL",
        "CANCEL_RESTING_MAKER_TP",
        "MERGE_CTF_POSITIONS",
    )

    # Verify atomic sequence in `PolymarketLiveHarvester._execute_guarded_complement_merge`:
    # If Step 1 (`buy_complement_leg_fak`) fails, Step 3 (`cancel_order` on resting $0.98 Maker TP) MUST NOT execute!
    harv = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    harv.dry_run = False
    harv.active_positions = {}
    harv.closed_positions = []
    harv.save_state = MagicMock()
    harv._close_position = MagicMock()
    harv.record_fill_and_update_position = MagicMock(
        side_effect=lambda pos, *_a, **_kw: pos.update(remaining_shares=0.0)
    )
    exec_mock = MagicMock()
    exec_mock.buy_complement_leg_fak.return_value = {"success": False, "matched_shares": 0.0}
    harv.executor = exec_mock

    pos = {
        "condition_id": "0xabc123",
        "token_id": "tok_up",
        "exit_order_id": "oid_maker_98",
        "remaining_shares": 100.0,
        "target_exit_price": 0.98,
        "neg_risk": False,
    }
    harv.active_positions["tid_1"] = pos
    ok_fail = asyncio.run(harv._execute_guarded_complement_merge("tid_1", pos, "tok_dn", good, time.time()))
    assert ok_fail is False
    exec_mock.cancel_order.assert_not_called()
    assert pos["exit_order_id"] == "oid_maker_98"

    # Now Step 1 fills 100 shares -> Step 3 cancels Maker TP -> Step 4 merges on-chain -> closes position
    exec_mock.buy_complement_leg_fak.return_value = {"success": True, "matched_shares": 100.0, "cost_usd": 1.07}
    exec_mock.cancel_order.return_value = {"is_canceled": True}
    exec_mock.get_order_fill_summary.return_value = None
    exec_mock.attempt_onchain_complete_set_merge.return_value = ("0xdeadbeef", 100.0)
    ok_pass = asyncio.run(harv._execute_guarded_complement_merge("tid_1", pos, "tok_dn", good, time.time()))
    assert ok_pass is True
    exec_mock.cancel_order.assert_called_once_with("oid_maker_98")
    exec_mock.attempt_onchain_complete_set_merge.assert_called_once()
    harv._close_position.assert_called_once()


def test_track_a_d1_15m_to_5m_corridor_and_unanchored_5m_pruning() -> None:
    now = 1_760_000_000.0
    pos_15m = {
        "target_token": "UP",
        "remaining_shares": 20.0,
        "entry_price": 0.62,
        "fee_usd": 0.33,
        "candle_open_spot": 100_000.0,
        "candle_expiry_ts": now + 180.0,
    }
    snap_5m = {
        "market_id": "mkt_5m_child",
        "authoritative_chainlink_open": 100_045.0,  # +4.5 bps corridor (`K_5 > K_15`)
        "DOWN": {"best_ask": 0.31, "ask_size_l1": 35.0, "token_id": "tok_5m_down"},
    }
    conv = evaluate_d1_15m_to_5m_corridor_conversion(pos_15m, snap_5m, now_ts=now)
    assert conv["eligible"] is True
    assert conv["opp_side_5m"] == "DOWN"
    assert conv["total_box_cost_ps"] <= 0.975
    assert conv["locked_floor_pnl_usd"] > 0.35

    # Reject inverted strike (`K_5 <= K_15` has no guaranteed $1.00 floor!)
    bad_snap = dict(snap_5m, authoritative_chainlink_open=99_980.0)
    assert evaluate_d1_15m_to_5m_corridor_conversion(pos_15m, bad_snap, now_ts=now)["eligible"] is False

    # Verify `discover_s5m_candles` never polls unanchored `BNB` or `HYPE`
    daemon = Alpha124ShadowDaemon.__new__(Alpha124ShadowDaemon)
    daemon.s5m_candles = {}
    daemon.dominance_pairs = {}
    daemon.twap_candles = {}
    polled_urls: list[str] = []

    async def _fake_fetch(url: str, timeout: float = 3.5):
        polled_urls.append(url)
        return []

    daemon.fetch_json = _fake_fetch
    # Pick `now_ts` with `rem_5m = 120s` inside `[35s, 185s]`
    asyncio.run(daemon.discover_s5m_candles(1_760_000_280.0))
    assert polled_urls
    assert all("bnb" not in u.lower() and "hype" not in u.lower() for u in polled_urls)


def test_track_b_unit_variance_student_t_and_hybrid_cascade_simulator() -> None:
    # Trap #1: Unit-variance Student-t(df=4) avoids raw Var(t_4)=2 under-confidence at moderate z
    # while preserving fat tails relative to Gaussian at extreme z!
    p_raw_t4 = student_t_df4_cdf(1.35)
    p_unit_t4 = compute_unit_variance_student_t_cdf(1.35, df=4.0)
    p_gauss = compute_unit_variance_student_t_cdf(1.35, df=0.0)
    assert p_unit_t4 > p_raw_t4 + 0.03
    assert compute_unit_variance_student_t_cdf(3.2, df=4.0) < compute_unit_variance_student_t_cdf(3.2, df=0.0)

    z_adj, p_gate = compute_v395_pricing_and_twap_gate(
        {"hz": "15m", "cushion_oracle": 0.0012, "sigma_rem": 0.00062, "tte": 55.0},
        df=4.0,
        jump_vol_mult=1.25,
        use_kemna_vorst=True,
    )
    assert z_adj > 0.0 and 0.5 < p_gate < 1.0

    # Verify 5m vs 15m title inference in `honest_purged_wfo_optimizer.py`
    assert infer_asset_and_horizon({"title": "Bitcoin Up or Down - October 30, 12:00PM-12:05PM ET"}) == ("BTC", "5m")
    assert infer_asset_and_horizon({"title": "Solana Up or Down - October 30, 12:00PM-12:15PM ET"}) == ("SOL", "15m")

    # Verify Hybrid z-Split + 20% Maker rebate + Queue-Depth Cap + Complement-Book Shield in simulator
    base_cand = {
        "ask_t0": 0.72,
        "bid_t0": 0.70,
        "opp_bid_t0": 0.27,  # 1 - 0.27 = 0.73 > 0.71
        "l1_ask_usd": 40.0,
        "l1_bid_usd": 25.0,
        "cushion_oracle": 0.0012,
        "z_oracle": 0.95,  # < 1.20 -> routes to `HYBRID_MAKER_FIRST`
        "tte": 210.0,
        "micro_clips": [
            (0.10, 0.0012, 0.70, 0.72, 0.27),
            (0.55, 0.0012, 0.70, 0.72, 0.27),
            (1.20, 0.0012, 0.70, 0.71, 0.29),  # legitimate seller hits our $0.71 maker bid!
        ],
    }
    cfg = {
        "hybrid_z_split": True,
        "z_taker_cut": 1.20,
        "include_maker_rebate": True,
        "use_complement_shield": True,
        "max_maker_join_queue_usd": 45.0,
    }
    res_ok = simulate_microclip_cascade_entry(base_cand, cfg, latency_mode="500ms")
    assert res_ok is not None
    fill_px, fee_ps, _, _, step_tag = res_ok
    assert step_tag == "HYBRID_MAKER_FIRST"
    assert fill_px == 0.71
    assert fee_ps < 0.0  # 20% maker rebate reduces effective cost!

    # Reject 1-tick back-of-queue join when `l1_bid_usd > $45` (spread = 1c so maker_px == bid_reb == 0.71)
    deep_queue_cand = dict(
        base_cand,
        bid_t0=0.71,
        l1_bid_usd=85.0,
        micro_clips=[
            (0.55, 0.0012, 0.71, 0.72, 0.27),
            (1.20, 0.0012, 0.70, 0.71, 0.29),
        ],
    )
    assert simulate_microclip_cascade_entry(deep_queue_cand, cfg, latency_mode="500ms") is None

    # Complement-Book HFT Repricing Shield cancels BEFORE toxic sweep when `opp_bid` jumps to `0.30` (`1 - 0.30 = 0.70 < 0.71`)
    toxic_comp_cand = dict(
        base_cand,
        micro_clips=[
            (0.55, 0.0012, 0.70, 0.72, 0.27),
            (0.90, 0.0012, 0.70, 0.72, 0.29),  # HFT lead reprices DOWN bid to $0.29 while UP ask is still $0.72 -> cancel!
            (1.20, 0.0001, 0.68, 0.70, 0.30),
        ],
    )
    assert simulate_microclip_cascade_entry(toxic_comp_cand, cfg, latency_mode="500ms") is None


def test_track_c_microbatch_tournament_and_sol5m_xau15m_shadow_sleeves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 1. 60ms Micro-Batch Cross-Asset Tournament ranks higher-EV BTC shock ahead of marginal SOL shock
    s_sol = {
        "asset": "SOL",
        "horizon": "15m",
        "shock_direction": "BUY",
        "candle_distance_pct": 0.08,
        "seconds_to_expiry": 300.0,
        "shock_ofi": 0.75,
        "pre_shock_features_t0": {"UP": {"best_ask": 0.79, "age_ask_ms": 120.0}},
    }
    s_btc = {
        "asset": "BTC",
        "horizon": "15m",
        "shock_direction": "BUY",
        "candle_distance_pct": 0.22,
        "seconds_to_expiry": 200.0,
        "shock_ofi": 0.95,
        "pre_shock_features_t0": {"UP": {"best_ask": 0.66, "age_ask_ms": 400.0}},
    }
    ranked = rank_microbatch_shock_tournament([s_sol, s_btc])
    assert ranked[0]["asset"] == "BTC"

    # 2. XAU/USD currency-matched 3-decimal anchor + CME maintenance / session filter
    assert compute_synthetic_xau_usd_anchor(2750.123, 0.0)["valid"] is False
    assert compute_synthetic_xau_usd_anchor(2750.123, 1.0000, swissquote_bid=2752.0, swissquote_ask=2752.4)["reason"] == "SWISSQUOTE_BASIS_DIVERGENCE"
    ok_anchor = compute_synthetic_xau_usd_anchor(2750.126, 0.9998, swissquote_bid=2749.40, swissquote_ask=2749.70)
    assert ok_anchor["valid"] is True
    assert ok_anchor["xau_usd"] == round(2750.126 * 0.9998, 3)

    ny = ZoneInfo("America/New_York")
    cme_maint_ts = datetime(2026, 10, 28, 17, 15, tzinfo=ny).timestamp()  # Wed 17:15 ET
    comex_open_ts = datetime(2026, 10, 28, 9, 30, tzinfo=ny).timestamp()  # Wed 09:30 ET
    assert is_xau_cme_blackout_or_inactive_session(cme_maint_ts)[0] is True
    assert is_xau_cme_blackout_or_inactive_session(comex_open_ts)[0] is False

    # 3. `DirectionalWfoShadowManager`: isolated `SOL 5m` canary + `XAU 15m` 0%-fee/0%-rebate Maker sleeve
    shm_dir = tmp_path / "shm"
    shm_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(shm_dir))
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")

    mgr = DirectionalWfoShadowManager(tmp_path, latency_sec=0.0)

    # 3a. Candidate A (`SLEEVE_HYBRID_ZSPLIT_SHADOW`): Queue-depth cap (`>$45`) + Complement-Book Shield (`1 - opp_bid <= maker_px`)
    now_hz = time.time()
    hz_shock = {
        "market_id": "mkt_hz_qcap",
        "title": "Bitcoin Up or Down - 15m Window",
        "asset": "BTC",
        "horizon": "15m",
        "t0_unix": now_hz,
        "seconds_to_expiry": 240.0,
        "shock_direction": "BUY",
        "shock_ofi": 0.85,
        "spot_at_t0": 100_120.0,
        "candle_open_spot": 100_000.0,
        "twap_60s_open": 100_000.0,
        "chainlink_proxy_usd_spot": 100_095.0,
        "authoritative_chainlink_open": 99_975.0,
        "candle_sigma": 0.0025,
        "pre_shock_features_t0": {"UP": {"best_bid": 0.71, "best_ask": 0.72, "ask_size_l1": 40.0}},
    }
    assert mgr.on_shock_signal(hz_shock) is True
    # Write SHM tick where L1 bid queue is 100 sh @ $0.71 = $71.0 > $45.0 cap (`maker_px = 0.71 == bid_now`)
    (shm_dir / "pm_fast_tick_BTC.json").write_text(
        json.dumps({
            "ts": now_hz + 0.1,
            "timestamp_unix": now_hz + 0.1,
            "asset": "BTC",
            "spot_price": 100_122.0,
            "chainlink_proxy_spot": 100_097.0,
            "markets": {
                "mkt_hz_qcap": {
                    "market_id": "mkt_hz_qcap",
                    "asset": "BTC",
                    "horizon": "15m",
                    "timestamp_unix": now_hz + 0.1,
                    "spot_price": 100_122.0,
                    "UP": {"best_bid": 0.71, "best_ask": 0.72, "bid_size_l1": 600.0, "ask_size_l1": 40.0, "is_crossed": False},
                    "DOWN": {"best_bid": 0.27, "best_ask": 0.29, "bid_size_l1": 40.0, "ask_size_l1": 40.0, "is_crossed": False},
                }
            },
        }),
        encoding="utf-8",
    )
    mgr.poll_tick()
    assert mgr.hz_funnel["queue_depth_rejected"] == 1

    hz_comp = dict(hz_shock, market_id="mkt_hz_comp", pre_shock_features_t0={"UP": {"best_bid": 0.70, "best_ask": 0.72, "ask_size_l1": 40.0}})
    assert mgr.on_shock_signal(hz_comp) is True
    (shm_dir / "pm_fast_tick_BTC.json").write_text(
        json.dumps({
            "ts": now_hz + 0.2,
            "timestamp_unix": now_hz + 0.2,
            "asset": "BTC",
            "spot_price": 100_122.0,
            "chainlink_proxy_spot": 100_097.0,
            "markets": {
                "mkt_hz_comp": {
                    "market_id": "mkt_hz_comp",
                    "asset": "BTC",
                    "horizon": "15m",
                    "timestamp_unix": now_hz + 0.2,
                    "spot_price": 100_122.0,
                    "UP": {"best_bid": 0.70, "best_ask": 0.73, "bid_size_l1": 30.0, "ask_size_l1": 40.0, "is_crossed": False},
                    "DOWN": {"best_bid": 0.29, "best_ask": 0.31, "bid_size_l1": 40.0, "ask_size_l1": 40.0, "is_crossed": False},
                }
            },
        }),
        encoding="utf-8",
    )
    mgr.poll_tick()
    assert mgr.hz_funnel["complement_shield_canceled"] == 1

    # 3b. SOL 5m telemetry populates `s5_open` ONLY, leaving `b5_open` untouched!
    sol_t0 = comex_open_ts
    sol_tick_1 = {
        "timestamp_unix": sol_t0,
        "asset": "SOL",
        "horizon": "5m",
        "market_id": "mkt_sol_5m_1",
        "title": "Solana Up or Down - 5m",
        "seconds_to_expiry": 120.0,
        "binance_spot": 180.45,
        "binance_open": 180.00,
        "twap_60s_open": 180.00,
        "chainlink_proxy_usd_spot": 180.42,
        "authoritative_chainlink_open": 179.98,
        "candle_sigma": 0.0018,
        "UP": {"best_bid": 0.68, "best_ask": 0.70, "ask_size_l1": 35.0, "raw_top_asks": [[0.70, 35.0]]},
        "DOWN": {"best_bid": 0.29, "best_ask": 0.31, "ask_size_l1": 35.0},
    }
    sol_tick_2 = dict(sol_tick_1, timestamp_unix=sol_t0 + 0.5)
    (tmp_path / "polymarket_5m_telemetry_sol.jsonl").write_text(
        json.dumps(sol_tick_1) + "\n" + json.dumps(sol_tick_2) + "\n",
        encoding="utf-8",
    )
    mgr.poll_tick()
    mgr.poll_tick()
    assert "mkt_sol_5m_1" in mgr.s5_open
    assert len(mgr.b5_open) == 0
    assert mgr.s5_state_file.exists()

    # 3c. XAU 15m blocks CME maintenance, then queues & fills valid COMEX 09:30 ET Maker order ($12 clip, 0% fee, 0% rebate)
    xau_maint_tick = {
        "timestamp_unix": cme_maint_ts,
        "asset": "XAU",
        "horizon": "15m",
        "market_id": "mkt_xau_maint",
        "seconds_to_expiry": 240.0,
        "binance_xau_usdt": 2752.50,
        "coinbase_usdt_usd": 1.0000,
        "authoritative_chainlink_open": 2750.000,
        "UP": {"best_bid": 0.69, "best_ask": 0.71, "ask_size_l1": 100.0, "bid_size_l1": 20.0},
        "DOWN": {"best_bid": 0.28, "best_ask": 0.30, "ask_size_l1": 100.0},
    }
    xau_open_tick = dict(xau_maint_tick, timestamp_unix=comex_open_ts, market_id="mkt_xau_ok")
    xau_fill_tick = dict(
        xau_open_tick,
        timestamp_unix=comex_open_ts + 0.4,
        UP={"best_bid": 0.69, "best_ask": 0.70, "ask_size_l1": 100.0, "bid_size_l1": 20.0},
        DOWN={"best_bid": 0.29, "best_ask": 0.31, "ask_size_l1": 100.0},
    )
    (tmp_path / "polymarket_15m_telemetry_xau.jsonl").write_text(
        json.dumps(xau_maint_tick) + "\n" + json.dumps(xau_open_tick) + "\n",
        encoding="utf-8",
    )
    mgr.poll_tick()
    assert mgr.xau_funnel["cme_or_session_blocked"] == 1
    assert "mkt_xau_ok" in mgr.xau_pending
    assert mgr.xau_pending["mkt_xau_ok"]["maker_px"] == 0.70

    with open(tmp_path / "polymarket_15m_telemetry_xau.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(xau_fill_tick) + "\n")
    mgr.poll_tick()
    assert "mkt_xau_ok" in mgr.xau_open
    xau_pos = mgr.xau_open["mkt_xau_ok"]
    assert xau_pos["notional_usd"] == 12.0
    assert xau_pos["taker_fee_usd"] == 0.0
    assert xau_pos["maker_rebate_20pct_est_usd"] == 0.0

#!/usr/bin/env python3
"""
APEX v5.2 Adversarial QA: WebSocket L2 Cache, Queue-Aware ALO Pricing,
Flat-Only Deadman Switch, EXP-506b Shadow Arena & Mainnet Canary Pre-Flight
===========================================================================
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from scripts.apex_mainnet_canary_preflight import evaluate_canary_readiness
from src.execution.exchange_gateway import HyperliquidGateway
from src.execution.ws_market_cache import (
    HyperliquidWsMarketCache,
    compute_l2_microstructure,
    select_queue_aware_alo_price,
)
from src.research.apex_champion_challenger import record_shadow_competition_step
from src.strategy.apex_v5_kernel import compute_apex_v5_raw_unit_weights


def test_ws_l2_microstructure_and_decay_obi5():
    assert compute_l2_microstructure([], [], tick_sz=0.1) is None

    bids = [
        {"px": "100.0", "sz": "15.0"},
        {"px": "99.9", "sz": "10.0"},
        {"px": "99.8", "sz": "8.0"},
    ]
    asks = [
        {"px": "100.4", "sz": "3.0"},
        {"px": "100.5", "sz": "2.0"},
        {"px": "100.6", "sz": "1.0"},
    ]
    ms = compute_l2_microstructure(bids, asks, tick_sz=0.1)
    assert ms is not None
    assert ms["best_bid"] == pytest.approx(100.0)
    assert ms["best_ask"] == pytest.approx(100.4)
    assert ms["mid"] == pytest.approx(100.2)
    assert ms["spread_ticks"] == pytest.approx(4.0)
    # Ask top size is smaller than bid top size -> microprice leans toward best_ask (> mid)
    assert ms["microprice"] > ms["mid"]
    assert 0.50 < ms["obi_5"] <= 1.0


def test_queue_aware_alo_pennying_and_adverse_retreat_never_crosses():
    # 1. Wide spread (4 ticks) + strong supporting buy queue -> PENNY_INSIDE (+1 tick, strictly < best_ask)
    px_b, mode_b = select_queue_aware_alo_price(
        is_buy=True, best_bid=100.0, best_ask=100.4, tick_sz=0.1, obi_5=0.55
    )
    assert mode_b == "PENNY_INSIDE"
    assert px_b == pytest.approx(100.1)
    assert px_b < 100.4

    # 2. Wide spread (4 ticks) + strong supporting sell queue -> PENNY_INSIDE (-1 tick, strictly > best_bid)
    px_s, mode_s = select_queue_aware_alo_price(
        is_buy=False, best_bid=100.0, best_ask=100.4, tick_sz=0.1, obi_5=-0.55
    )
    assert mode_s == "PENNY_INSIDE"
    assert px_s == pytest.approx(100.3)
    assert px_s > 100.0

    # 3. Tight 1-tick spread -> JOIN_BBO (never crosses into best_ask!)
    px_tight, mode_tight = select_queue_aware_alo_price(
        is_buy=True, best_bid=100.0, best_ask=100.1, tick_sz=0.1, obi_5=0.90
    )
    assert mode_tight == "JOIN_BBO"
    assert px_tight == pytest.approx(100.0)

    # 4. Toxic opposing queue imbalance -> ADVERSE_RETREAT (-1 tick behind BBO)
    px_ret_b, mode_ret_b = select_queue_aware_alo_price(
        is_buy=True, best_bid=100.0, best_ask=100.2, tick_sz=0.1, obi_5=-0.75
    )
    assert mode_ret_b == "ADVERSE_RETREAT"
    assert px_ret_b == pytest.approx(99.9)

    px_ret_s, mode_ret_s = select_queue_aware_alo_price(
        is_buy=False, best_bid=100.0, best_ask=100.2, tick_sz=0.1, obi_5=0.75
    )
    assert mode_ret_s == "ADVERSE_RETREAT"
    assert px_ret_s == pytest.approx(100.3)


def test_ws_market_cache_staleness_and_disconnect_invalidation():
    cache = HyperliquidWsMarketCache(
        "https://api.hyperliquid-testnet.xyz",
        initial_coins=["BTC", "ETH"],
        l2_staleness_sec=0.25,
        ctx_staleness_sec=0.25,
        mid_staleness_sec=0.25,
        auto_start=False,
    )
    assert cache.ws_url == "wss://api.hyperliquid-testnet.xyz/ws"

    cache._on_message(
        None,
        json.dumps({
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "levels": [
                    [{"px": "80100.0", "sz": "1.2"}],
                    [{"px": "80110.0", "sz": "0.8"}],
                ],
            },
        }),
    )
    cache._on_message(
        None,
        json.dumps({
            "channel": "activeAssetCtx",
            "data": {
                "coin": "BTC",
                "ctx": {"oraclePx": "80095.5", "markPx": "80105.0", "midPx": "80105.0", "funding": "0.0001"},
            },
        }),
    )
    cache._on_message(
        None,
        json.dumps({"channel": "allMids", "data": {"mids": {"ETH": "2520.5", "#100": "0.5"}}}),
    )

    assert cache.get_fresh_l2_levels("BTC") is not None
    assert cache.get_fresh_oracle_price("BTC") == pytest.approx(80095.5)
    assert cache.get_fresh_mid("ETH") == pytest.approx(2520.5)
    assert cache.ws_hits_l2 == 1
    assert cache.ws_hits_oracle == 1
    assert cache.ws_hits_mid == 1

    # Age past staleness window -> must return None so gateway falls back to REST
    time.sleep(0.30)
    assert cache.get_fresh_l2_levels("BTC") is None
    assert cache.get_fresh_oracle_price("BTC") is None
    assert cache.get_fresh_mid("ETH") is None

    # Re-populate then trigger socket close -> must invalidate immediately
    cache._on_message(
        None,
        json.dumps({"channel": "allMids", "data": {"mids": {"ETH": "2530.0"}}}),
    )
    assert cache.get_fresh_mid("ETH") == pytest.approx(2530.0)
    cache._on_close(None, 1006, "CloudFlare reset")
    assert cache.get_fresh_mid("ETH") is None
    assert cache.get_stats()["connected"] is False


def test_gateway_ws_first_with_seamless_rest_fallback_and_mock_safety():
    gw = HyperliquidGateway.__new__(HyperliquidGateway)
    gw.sz_decimals = {"BTC": 5}
    gw._universe_idx = {"BTC": 0}
    gw.meta = {"universe": [{"name": "BTC", "szDecimals": 5}]}
    gw._ctx_cache_ts = 0.0
    gw._ctx_cache_data = None

    # Create a class literally named "Info" to emulate real SDK Info vs MagicMock
    FakeInfoCls = type("Info", (), {})
    fake_info = FakeInfoCls()
    rest_calls = {"l2": 0, "ctx": 0}

    def _l2_snap(_sym):
        rest_calls["l2"] += 1
        return {"levels": [[{"px": "79900.0", "sz": "1.0"}], [{"px": "79910.0", "sz": "1.0"}]]}

    def _meta_ctxs():
        rest_calls["ctx"] += 1
        return gw.meta, [{"oraclePx": "79890.0"}]

    fake_info.l2_snapshot = _l2_snap
    fake_info.meta_and_asset_ctxs = _meta_ctxs
    gw.info = fake_info

    cache = HyperliquidWsMarketCache("https://api.hyperliquid-testnet.xyz", auto_start=False)
    gw.ws_cache = cache

    # 1. Cold WS cache -> seamlessly falls back to REST
    b, a, m = gw.get_bbo_and_mid("BTC")
    opx = gw.get_oracle_price("BTC")
    assert (b, a, m) == pytest.approx((79900.0, 79910.0, 79905.0))
    assert opx == pytest.approx(79890.0)
    assert rest_calls["l2"] == 1
    assert rest_calls["ctx"] == 1

    # 2. Warm WS cache -> serves in <0.1ms with ZERO new REST calls!
    cache._on_message(
        None,
        json.dumps({
            "channel": "l2Book",
            "data": {"coin": "BTC", "levels": [[{"px": "80500.0", "sz": "2.0"}], [{"px": "80510.0", "sz": "1.0"}]]},
        }),
    )
    cache._on_message(
        None,
        json.dumps({"channel": "activeAssetCtx", "data": {"coin": "BTC", "ctx": {"oraclePx": "80502.0"}}}),
    )
    b2, a2, m2 = gw.get_bbo_and_mid("BTC")
    opx2 = gw.get_oracle_price("BTC")
    assert (b2, a2, m2) == pytest.approx((80500.0, 80510.0, 80505.0))
    assert opx2 == pytest.approx(80502.0)
    assert rest_calls["l2"] == 1
    assert rest_calls["ctx"] == 1

    # 3. Replacing gw.info with MagicMock bypasses WS cache automatically
    mock_info = MagicMock()
    mock_info.l2_snapshot.return_value = {"levels": [[{"px": "70000.0", "sz": "1.0"}], [{"px": "70010.0", "sz": "1.0"}]]}
    gw.info = mock_info
    assert gw.get_bbo_and_mid("BTC")[0] == pytest.approx(70000.0)


def test_deadman_switch_p0_never_arms_when_positions_open():
    gw = HyperliquidGateway.__new__(HyperliquidGateway)
    gw.exchange = MagicMock()
    gw.exchange.schedule_cancel.return_value = {"status": "ok"}

    # P0 Safety Invariant: must NEVER arm scheduleCancel when positions are open (protects L1 SL/TP brackets!)
    res_blocked = gw.arm_flat_deadman_switch_if_safe(open_positions_count=12, timeout_sec=240)
    assert res_blocked == {"skipped": "OPEN_POSITIONS_PROTECTED_BY_L1_TRIGGERS"}
    gw.exchange.schedule_cancel.assert_not_called()

    # Allowed when account is completely flat (0 positions)
    res_flat = gw.arm_flat_deadman_switch_if_safe(open_positions_count=0, timeout_sec=180)
    assert res_flat == {"status": "ok"}
    assert gw.exchange.schedule_cancel.call_count == 1


def test_exp506b_kernel_backward_compat_and_4track_shadow_arena(tmp_path: Path):
    rng = np.random.default_rng(77)
    n_bars, n_syms = 200, 16
    syms = ["BTC", "ETH"] + [f"ALT{i}" for i in range(14)]
    # Construct low-ER choppy paths so EXP-506b activates when enabled
    steps = rng.normal(0.0, 0.015, (n_bars, n_syms))
    # Alternate signs to keep 14d Kaufman Efficiency Ratio < 0.14
    steps[::2] = -steps[::2] * 0.92
    close_mat = 100.0 * np.exp(np.cumsum(steps, axis=0))
    vol_mat = np.full((n_bars, n_syms), 5_000_000.0)
    valid_mask = np.ones((n_bars, n_syms), dtype=bool)
    fund = np.zeros(n_syms, dtype=np.float64)

    rw_v51, betas, _, _, _, _ = compute_apex_v5_raw_unit_weights(
        close_mat, valid_mask, fund, syms, 0, 1, vol_mat=vol_mat,
        regime_adaptive_routing=True, er_gate_tsmom=True, fast_tsmom_blend=True,
        fip_quality_weight=0.05, vol_accel_weight=0.05, chop_eth_30d_dispersion=False,
    )
    rw_506b, betas2, _, _, _, _ = compute_apex_v5_raw_unit_weights(
        close_mat, valid_mask, fund, syms, 0, 1, vol_mat=vol_mat,
        regime_adaptive_routing=True, er_gate_tsmom=True, fast_tsmom_blend=True,
        fip_quality_weight=0.05, vol_accel_weight=0.05, chop_eth_30d_dispersion=True,
    )
    assert np.all(np.isfinite(rw_506b))
    assert float(np.sum(np.abs(rw_506b))) <= 1.0 + 1e-9
    assert not np.allclose(rw_v51, rw_506b)

    shadow_file = tmp_path / "shadow.json"
    st = record_shadow_competition_step(
        decision_ts_ms=1761696000000,
        close_mat=close_mat,
        vol_mat=vol_mat,
        valid_mask=valid_mask,
        funding_rates_1h=fund,
        symbols=syms,
        btc_idx=0,
        eth_idx=1,
        current_equity=613.98,
        historical_hwm=613.98,
        shadow_path=shadow_file,
    )
    assert set(st["tracks"].keys()) == {
        "v5_0_baseline_vt25",
        "v5_1_adaptive_vt25_isovol",
        "v5_1_production_vt35",
        "v5_2_challenger_exp506b_vt35",
    }


def test_canary_preflight_blocks_until_post_v51_fills_and_collateral(tmp_path: Path, monkeypatch):
    (tmp_path / "data").mkdir(parents=True)
    state_obj = {
        "version": "v5.2.0-ws-queue-adaptive-majors",
        "circuit_breaker": "RUNNING",
        "accounting_ledger": {"reconciliation_status": "EXACT"},
        "ws_market_cache": {"connected": True, "messages_received": 42},
    }
    (tmp_path / "data" / "papertrade_state.json").write_text(json.dumps(state_obj), encoding="utf-8")
    # Write 20 pre-v5.1 fills and 5 post-v5.1 fills
    j_lines = []
    for i in range(20):
        j_lines.append(json.dumps({
            "event_type": "IMPLEMENTATION_AUDIT_RECORD",
            "payload": {"timestamp_utc": "2026-10-25T12:00:00Z", "order_type": "RESTING_ALO", "total_shortfall_bps": 1.2},
        }))
    for i in range(5):
        j_lines.append(json.dumps({
            "event_type": "IMPLEMENTATION_AUDIT_RECORD",
            "payload": {"timestamp_utc": "2026-10-29T04:01:00Z", "order_type": "RESTING_ALO", "total_shortfall_bps": 1.1},
        }))
    (tmp_path / "data" / "papertrade_journal.jsonl").write_text("\n".join(j_lines) + "\n", encoding="utf-8")

    monkeypatch.setenv("HYPERLIQUID_ACCOUNT_ADDRESS", "")
    res = evaluate_canary_readiness(repo_root=tmp_path, target_post_v51_fills=100, min_canary_usdc=250.0)
    assert res["post_v51_fills"] == 5
    assert res["total_gate2_fills"] == 25
    assert res["ready_for_mainnet_canary"] is False

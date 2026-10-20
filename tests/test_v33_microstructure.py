"""
Unit tests for Polymarket v3.3 Institutional Microstructure & Alpha Upgrade.
Covers all 5 Deep Research Pillars:
- Pillar 1: Composite Edge & Stale-Quote scoring, hard vetoes, Tier A+ / Tier B / Tier C.
- Pillar 2: Salvage-adjusted continuous maximum-ask pricing model, expected salvage payoff, TTE 30s-120s unlock.
- Pillar 3: 15s spot velocity tracking, Anti-Wick Rebound Guard, Fast Breakdown Acceleration, trailing profit ratchet, and 3s passive maker unwind.
- Pillar 4: Truncated-salvage Kelly fraction & same-hour BTC+ETH correlation haircut (46% reduction for Pos 2).
- Pillar 5A: Global TCP_NODELAY and PreSignedOrderLadderCache.
"""

import math
import os
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.polymarket_research.polymarket_live_harvester import (
    compute_composite_edge_score,
    compute_max_acceptable_ask,
    compute_modified_salvage_kelly_fraction,
    compute_correlated_truncated_kelly_size,
    PolymarketLiveHarvester,
)
from src.polymarket_research.polymarket_live_executor import (
    PreSignedOrderLadderCache,
    PolymarketLiveExecutor,
    enable_tcp_nodelay_globally,
)


# ==============================================================================
# Pillar 1 Tests: Composite Edge & Stale-Quote Scoring
# ==============================================================================

def test_composite_edge_score_tier_a_plus():
    """Verify Tier A+ Stale Snipe: e_score >= 70 and age_ask_ms >= 250 -> 1.15x Kelly, 0.02 FAK buffer."""
    shock = {
        "asset": "BTC",
        "shock_direction": "UP",
        "shock_ofi": 0.95,
        "shock_volume_100ms": 2_500_000.0,
        "delta_basis_100ms": 1.5,
        "basis_signed_bps_t0": 4.0,
        "is_40ms_fast_track": True,
        "pre_shock_features_t0": {
            "UP": {
                "age_ask_ms": 450.0,
                "age_bid_ms": 120.0,
                "obi_l1": 0.40,
                "obi_depth": 0.50,
                "q_micro": 0.655,
                "q_mid": 0.650,
                "spread": 0.010,
                "vwap_cost_25usd": 0.652,
                "best_ask": 0.650,
                "best_bid": 0.640,
            },
            "DOWN": {
                "age_bid_ms": 300.0,
                "best_bid": 0.350,
            }
        }
    }
    result = compute_composite_edge_score(shock)
    assert not result["is_vetoed"]
    assert result["tier"] == "TIER_A_PLUS_STALE_SNIPE"
    assert result["kelly_multiplier"] == 1.15
    assert result["fak_price_buffer"] == 0.020
    assert result["e_score"] >= 70.0


def test_composite_edge_score_tier_b_standard():
    """Verify Tier B Standard: 50 <= e_score < 70 -> 1.00x Kelly, 0.015 FAK buffer."""
    shock = {
        "asset": "BTC",
        "shock_direction": "UP",
        "shock_ofi": 0.85,
        "shock_volume_100ms": 1_500_000.0,
        "delta_basis_100ms": 0.0,
        "basis_signed_bps_t0": 1.0,
        "is_40ms_fast_track": False,
        "pre_shock_features_t0": {
            "UP": {
                "age_ask_ms": 220.0,  # < 250.0 ensures Tier B rather than Tier A+
                "age_bid_ms": 100.0,
                "obi_l1": 0.20,
                "obi_depth": 0.20,
                "q_micro": 0.652,
                "q_mid": 0.650,
                "spread": 0.012,
                "vwap_cost_25usd": 0.654,
                "best_ask": 0.650,
                "best_bid": 0.638,
            },
            "DOWN": {
                "age_bid_ms": 120.0,
                "best_bid": 0.350,
            }
        }
    }
    result = compute_composite_edge_score(shock)
    assert not result["is_vetoed"]
    assert result["tier"] == "TIER_B_STANDARD"
    assert result["kelly_multiplier"] == 1.00
    assert result["fak_price_buffer"] == 0.015
    assert 50.0 <= result["e_score"] < 70.0


def test_composite_edge_score_hard_vetoes():
    """Verify all 3 institutional hard vetoes in Pillar 1."""
    # Hard Veto 1: abs(shock_ofi) < 0.60
    shock_low_ofi = {
        "shock_direction": "UP",
        "shock_ofi": 0.45,
        "shock_volume_100ms": 1_500_000.0,
        "delta_basis_100ms": 0.5,
        "pre_shock_features_t0": {
            "UP": {"age_ask_ms": 300.0, "spread": 0.01, "vwap_cost_25usd": 0.65, "best_ask": 0.65}
        }
    }
    res1 = compute_composite_edge_score(shock_low_ofi)
    assert res1["is_vetoed"]
    assert "0.60" in res1["veto_reason"]

    # Hard Veto 2: directional delta_basis_100ms < -2.0 bps
    shock_basis_drag = {
        "shock_direction": "UP",
        "shock_ofi": 0.85,
        "shock_volume_100ms": 1_500_000.0,
        "delta_basis_100ms": -2.5,
        "pre_shock_features_t0": {
            "UP": {"age_ask_ms": 300.0, "spread": 0.01, "vwap_cost_25usd": 0.65, "best_ask": 0.65}
        }
    }
    res2 = compute_composite_edge_score(shock_basis_drag)
    assert res2["is_vetoed"]
    assert "-2.0" in res2["veto_reason"]

    # Hard Veto 3: MM Reprice (age_ask_ms < 50.0 AND obi_l1 < -0.50)
    shock_mm_reprice = {
        "shock_direction": "UP",
        "shock_ofi": 0.90,
        "shock_volume_100ms": 1_500_000.0,
        "delta_basis_100ms": 1.0,
        "pre_shock_features_t0": {
            "UP": {
                "age_ask_ms": 35.0,
                "obi_l1": -0.65,
                "spread": 0.01,
                "vwap_cost_25usd": 0.65,
                "best_ask": 0.65
            }
        }
    }
    res3 = compute_composite_edge_score(shock_mm_reprice)
    assert res3["is_vetoed"]
    assert "repriced" in res3["veto_reason"]


def test_composite_edge_score_default_age_ask_ms_for_synthetic_fixtures():
    """Verify synthetic test fixtures without age_ask_ms default cleanly to 400.0ms."""
    shock = {
        "shock_direction": "UP",
        "shock_ofi": 0.85,
        "shock_volume_100ms": 1_500_000.0,
        "delta_basis_100ms": 0.5,
        "pre_shock_features_t0": {
            "UP": {
                "spread": 0.01,
                "best_ask": 0.65,
                "vwap_cost_25usd": 0.652,
                "q_mid": 0.645,
            }
        }
    }
    res = compute_composite_edge_score(shock)
    assert not res["is_vetoed"]
    assert res["sub_scores"]["S_stale"] > 0.0


# ==============================================================================
# Pillar 2 Tests: Salvage-Adjusted Continuous Maximum-Ask Pricing Model
# ==============================================================================

def test_compute_max_acceptable_ask_mid_hour_no_starvation():
    """
    CRITICAL CATCH: Verify that mid-hour trades (TTE 1200s–2400s) with prices in $0.62–$0.72
    do NOT get starved because Expected Salvage Value (1-P_true)(1-q_tail)s_net is included.
    p_max should land between $0.68 and $0.76.
    """
    # Mid-hour (TTE = 1800s, 30m left), cushion = 0.25%, solid flow
    res = compute_max_acceptable_ask(
        dist_pct=0.25,
        tte_sec=1800.0,
        asset="BTC",
        shock_ofi=0.90,
        shock_vol_usd=1_800_000.0,
        delta_basis_bps=0.8,
        age_ask_ms=350.0,
    )
    p_max = res["p_max"]
    assert 0.68 <= p_max <= 0.78, f"p_max={p_max} outside expected mid-hour range [0.68, 0.78]"
    assert res["expected_payoff"] > 0.75
    assert res["p_true"] > 0.70

    # Test an ask of $0.68 passes
    ask_candidate = 0.68
    assert ask_candidate <= p_max, "A profitable $0.68 mid-hour trade must not be blocked!"


def test_compute_max_acceptable_ask_late_hour():
    """Late-hour setups (TTE = 600s, 10m left) should have p_max in $0.75–$0.84 range."""
    res = compute_max_acceptable_ask(
        dist_pct=0.20,
        tte_sec=600.0,
        asset="BTC",
        shock_ofi=0.95,
        shock_vol_usd=2_000_000.0,
        delta_basis_bps=1.0,
        age_ask_ms=300.0,
    )
    p_max = res["p_max"]
    assert 0.75 <= p_max <= 0.84, f"p_max={p_max} outside expected late-hour range [0.75, 0.84]"


def test_compute_max_acceptable_ask_blocks_low_ev_overpayment():
    """Adverse cushion with poor flow should give p_max = 0.0 or reject overpayment."""
    res = compute_max_acceptable_ask(
        dist_pct=0.01,
        tte_sec=2700.0,
        asset="BTC",
        shock_ofi=0.10,
        shock_vol_usd=200_000.0,
        delta_basis_bps=-2.0,
        age_ask_ms=50.0,
    )
    assert res["p_max"] < 0.60 or res["p_true"] <= 0.55


def test_compute_max_acceptable_ask_late_expiry_unlock():
    """Verify high-certainty setups with z_eff >= 2.2 unlock at 30s <= TTE < 120s."""
    res = compute_max_acceptable_ask(
        dist_pct=0.35,
        tte_sec=45.0,  # 45s to expiry
        asset="BTC",
        shock_ofi=0.98,
        shock_vol_usd=2_000_000.0,
        delta_basis_bps=1.5,
    )
    assert res["z_eff"] >= 2.2
    assert res["p_true"] >= 0.985
    assert res["p_max"] >= 0.80


# ==============================================================================
# Pillar 3 Tests: Spot Velocity, Anti-Wick Guard, and Breakdown Acceleration
# ==============================================================================

@pytest.fixture
def mock_harvester(tmp_path):
    with patch("src.polymarket_research.polymarket_live_harvester.DATA_DIR", tmp_path), \
         patch("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "live_harvester_state.json"):
        h = PolymarketLiveHarvester(dry_run=True)
        h.state_file = tmp_path / "live_harvester_state.json"
        h.active_positions = {}
        return h


@pytest.mark.anyio
async def test_anti_wick_rebound_guard_pauses_salvage(mock_harvester):
    """
    Pillar 3: If v_spot_15s_pct >= +0.03% (spot rebounding in favor of the position),
    salvage is PAUSED so the algorithm never dumps the bottom of a wick!
    """
    now_ts = 1700000000.0
    mock_harvester.active_positions = {
        "POS_WICK": {
            "trade_id": "POS_WICK",
            "market_id": "MKT_WICK",
            "token_id": "TOK_UP",
            "target_token": "UP",
            "asset": "BTC",
            "entry_price": 0.65,
            "entry_shares": 30.0,
            "remaining_shares": 30.0,
            "candle_open_spot": 60000.0,
            "candle_expiry_ts": now_ts + 600.0,  # Zone 2 (TTE = 600s, base duration 18s)
            "exit_order_id": "order_tp_wick",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
            "opposite_breakout_start_ts": now_ts - 25.0,  # 25s elapsed (> 18s threshold!)
            # Spot was at 59900.0 (-0.167% wrong side) 15s ago, but has rebounded to 59940.0 (+0.067% rebound)
            "spot_vel_history": [
                [now_ts - 15.0, 59900.0],
                [now_ts - 8.0, 59920.0],
            ]
        }
    }
    # Current spot at 59940.0 (rebounding upward by +40 / 60000 = +0.067% >= +0.03%)
    mock_harvester.get_reference_spot_price = MagicMock(return_value=59940.0)
    mock_harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.40", "size": "100"}]})
    mock_harvester.executor.cancel_order = MagicMock()

    with patch("time.time", return_value=now_ts):
        await mock_harvester.check_resolutions_and_manage_positions()

    # Even though 25s > 18s, anti-wick rebound guard MUST prevent salvage unwind!
    mock_harvester.executor.cancel_order.assert_not_called()
    assert mock_harvester.active_positions["POS_WICK"]["status"] == "EXIT_RESTING"


@pytest.mark.anyio
async def test_fast_breakdown_acceleration_halves_duration(mock_harvester):
    """
    Pillar 3: Fast Breakdown Acceleration:
    If v_spot_15s_pct <= -0.08% and best_b <= 0.42, cut required duration by 50%
    (Zone 1: 20s, Zone 2: 9s, Zone 3: 4s).
    """
    now_ts = 1700000000.0
    mock_harvester.active_positions = {
        "POS_ACCEL": {
            "trade_id": "POS_ACCEL",
            "market_id": "MKT_ACCEL",
            "token_id": "TOK_UP",
            "target_token": "UP",
            "asset": "BTC",
            "entry_price": 0.65,
            "entry_shares": 30.0,
            "remaining_shares": 30.0,
            "candle_open_spot": 60000.0,
            "candle_expiry_ts": now_ts + 600.0,  # Zone 2 (base 18s -> accelerated to 9s!)
            "exit_order_id": "order_tp_accel",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
            "opposite_breakout_start_ts": now_ts - 10.0,  # 10s elapsed (10s < 18s base, but > 9s accelerated!)
            # 15s ago spot was 59950.0; now it has crashed to 59880.0 (change: -70/60000 = -0.117% <= -0.08%)
            "spot_vel_history": [
                [now_ts - 15.0, 59950.0],
            ]
        }
    }
    # Current spot crashed to 59880.0, best_b = 0.38 <= 0.42
    mock_harvester.get_reference_spot_price = MagicMock(return_value=59880.0)
    mock_harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.38", "size": "100"}]})
    mock_harvester.executor.cancel_order = MagicMock()
    mock_harvester.executor.execute_unwind_order = MagicMock(
        return_value={"order_id": "unwind_accel_123", "status": "FILLED", "filled_shares": 30.0, "avg_fill_price": 0.38}
    )

    with patch("time.time", return_value=now_ts):
        await mock_harvester.check_resolutions_and_manage_positions()

    # Fast breakdown triggered at 10s (halved threshold 9.0s)!
    mock_harvester.executor.cancel_order.assert_called_once_with("order_tp_accel")
    mock_harvester.executor.execute_unwind_order.assert_called_once()


# ==============================================================================
# Pillar 4 Tests: Correlated Truncated-Payoff Kelly Sizing
# ==============================================================================

def test_correlated_truncated_kelly_sizing():
    """
    Pillar 4:
    - Base bankroll: $91.67
    - Standalone Position 1: sizes at ~$22.00–$22.80 (~24% of equity).
    - Correlated Position 2 in same hour (BTC + ETH): receives 46% haircut (multiplier ~0.54),
      sizing at ~$12.50–$15.00 (~13.5%–16% of equity) with min_lot_usd = 12.0.
    """
    bankroll = 91.67
    p_true = 0.74
    entry_price = 0.65
    now_ts = 1700000000.0
    cand_expiry_ts = now_ts + 1800.0  # 30m to expiry

    # Position 1: No active correlated positions
    pos1_size = compute_correlated_truncated_kelly_size(
        bankroll_usd=bankroll,
        p_true=p_true,
        entry_price=entry_price,
        cand_expiry_ts=cand_expiry_ts,
        active_positions={},
        cand_direction="UP",
        kelly_multiplier=1.15,  # Tier A+
        min_lot_usd=12.0,
    )
    # v3.3 audit: base cap = 24% of bankroll ($22.00), A+ multiplier 1.15 applied after the cap (~$25.30).
    assert 24.0 <= pos1_size <= 26.0, f"Position 1 size {pos1_size} outside expected range [24.0, 26.0]"

    # Position 2: Position 1 already active in same hour expiry and same direction
    active_positions = {
        "POS_BTC": {
            "asset": "BTC",
            "target_token": "UP",
            "candle_expiry_ts": cand_expiry_ts + 10.0,  # Same hour window (|delta| < 900s)
            "remaining_shares": 33.0,
        }
    }
    pos2_size = compute_correlated_truncated_kelly_size(
        bankroll_usd=bankroll,
        p_true=p_true,
        entry_price=entry_price,
        cand_expiry_ts=cand_expiry_ts,
        active_positions=active_positions,
        cand_direction="UP",
        kelly_multiplier=1.15,
        min_lot_usd=12.0,
    )
    assert 12.0 <= pos2_size <= 15.0, f"Correlated Position 2 size {pos2_size} outside expected range [12.0, 15.0]"
    # Confirm correlation haircut was ~46% (ratio ~ 0.54)
    haircut_ratio = pos2_size / pos1_size
    assert 0.50 <= haircut_ratio <= 0.65, f"Haircut ratio {haircut_ratio} outside expected range [0.50, 0.65]"


# ==============================================================================
# Pillar 5A Tests: Global TCP_NODELAY & PreSignedOrderLadderCache
# ==============================================================================

def test_tcp_nodelay_globally():
    """Verify TCP_NODELAY and SO_KEEPALIVE are added to urllib3 socket options."""
    import socket
    from urllib3.connection import HTTPConnection

    enable_tcp_nodelay_globally()
    options = HTTPConnection.default_socket_options
    nodelay_set = any(opt[0] == socket.IPPROTO_TCP and opt[1] == socket.TCP_NODELAY and opt[2] == 1 for opt in options)
    keepalive_set = any(opt[0] == socket.SOL_SOCKET and opt[1] == socket.SO_KEEPALIVE and opt[2] == 1 for opt in options)
    assert nodelay_set, "TCP_NODELAY must be active"
    assert keepalive_set, "SO_KEEPALIVE must be active"


def test_presigned_order_ladder_cache():
    """Verify caching, retrieval, TTL expiry, and clearing of PreSignedOrderLadderCache."""
    cache = PreSignedOrderLadderCache(ttl_seconds=2.0)
    token_id = "0x1234567890abcdef"

    # Store dummy signed order
    mock_order = {"salt": 12345, "signature": "0xabc"}
    cache.store_presigned_order(token_id=token_id, price_cents=65, shares=40, signed_order=mock_order)

    # Retrieval hit
    hit = cache.get_presigned_order(token_id=token_id, price_cents=65, shares=40)
    assert hit == mock_order

    # Retrieval miss on different price or shares
    assert cache.get_presigned_order(token_id=token_id, price_cents=66, shares=40) is None
    assert cache.get_presigned_order(token_id=token_id, price_cents=65, shares=50) is None

    # TTL expiry
    with patch("time.time", return_value=time.time() + 5.0):
        assert cache.get_presigned_order(token_id=token_id, price_cents=65, shares=40) is None


def test_presigned_cache_ttl_expiry_on_fresh_entry():
    cache = PreSignedOrderLadderCache(ttl_seconds=2.0)
    cache.store_presigned_order(token_id="T", price=0.65, shares=40, signed_order={"s": 1})
    with patch("time.time", return_value=time.time() + 5.0):
        assert cache.get_presigned_order("T", 0.65, 40) is None


def test_presigned_cache_single_use_and_exact_match():
    cache = PreSignedOrderLadderCache(ttl_seconds=300.0)
    assert cache.store_presigned_order("T", 0.65, 33, {"s": 1}) is True
    # Fractional shares / sub-cent prices are never stored nor served
    assert cache.store_presigned_order("T", 0.65, 33.85, {"s": 2}) is False
    assert cache.store_presigned_order("T", 0.655, 33, {"s": 3}) is False
    assert cache.get_presigned_order("T", 0.65, 33.4) is None
    assert cache.has_fresh("T", 0.65, 33)
    assert cache.get_presigned_order("T", 0.65, 33) == {"s": 1}
    # Single-use: a signed order can never be re-posted
    assert cache.get_presigned_order("T", 0.65, 33) is None
    assert len(cache) == 0


def test_correlated_kelly_opposite_direction_same_window_is_zero():
    now_ts = 1700000000.0
    active = {"P": {"asset": "BTC", "target_token": "UP", "candle_expiry_ts": now_ts + 1800.0, "remaining_shares": 30.0}}
    size = compute_correlated_truncated_kelly_size(
        bankroll_usd=91.67, p_true=0.74, entry_price=0.65, cand_expiry_ts=now_ts + 1800.0,
        active_positions=active, cand_direction="DOWN", kelly_multiplier=1.15, min_lot_usd=12.0,
    )
    assert size == 0.0


def test_single_hop_presubmit_error_never_posts():
    from src.polymarket_research.polymarket_live_executor import _sign_and_post_single_hop, PreSubmitError
    client = MagicMock()
    client.create_order.side_effect = RuntimeError("sign boom")
    stage = {}
    with pytest.raises(PreSubmitError):
        _sign_and_post_single_hop(client, None, "T", 0.65, 10.0, "BUY", "FAK", None, stage)
    assert stage["submitted"] is False
    client.post_order.assert_not_called()


def test_single_hop_uses_presigned_cache_hit():
    from src.polymarket_research.polymarket_live_executor import _sign_and_post_single_hop
    client = MagicMock()
    client.post_order.return_value = {"success": True, "orderID": "0x1"}
    cache = PreSignedOrderLadderCache()
    cache.store_presigned_order("T", 0.65, 33, {"presigned": True})
    stage = {}
    out = _sign_and_post_single_hop(client, cache, "T", 0.65, 33.0, "BUY", "FAK", None, stage)
    assert out["cache_hit"] is True
    assert stage["submitted"] is True
    client.create_order.assert_not_called()
    client.post_order.assert_called_once_with({"presigned": True}, "FAK", False, True)


def test_read_fast_tick_and_book_for_token(tmp_path, monkeypatch):
    import json as _json
    from src.polymarket_research.polymarket_live_harvester import read_fast_tick, fast_tick_book_for_token
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    now = time.time()
    snap = {
        "ts": now,
        "UP": {"token_id": "U1", "best_bid": 0.62, "best_ask": 0.64, "bid_size_l1": 50, "ask_size_l1": 40},
        "DOWN": {"token_id": "D1", "best_bid": 0.0, "best_ask": 0.38},
        "m15": {"UP": {"token_id": "U15", "best_bid": 0.51, "best_ask": 0.53}},
    }
    (tmp_path / "pm_fast_tick_BTC.json").write_text(_json.dumps(snap))
    got = read_fast_tick("BTC", now=now + 0.1)
    assert got is not None
    assert read_fast_tick("BTC", now=now + 2.0) is None  # stale
    assert read_fast_tick("ETH", now=now) is None  # missing
    book = fast_tick_book_for_token(got, "U1")
    assert float(book["asks"][0]["price"]) == 0.64 and float(book["bids"][0]["price"]) == 0.62
    assert fast_tick_book_for_token(got, "D1") is None  # one-sided -> REST fallback
    assert fast_tick_book_for_token(got, "U15") is not None


def test_coinbase_venue_veto():
    from src.polymarket_research.polymarket_live_harvester import evaluate_coinbase_venue_veto
    # Fail-open without Coinbase data
    assert evaluate_coinbase_venue_veto({}, "UP")[0] is False
    # UP shock, Binance 20bps above Coinbase, Coinbase falling -> veto
    assert evaluate_coinbase_venue_veto({"coinbase_spot": 60000, "venue_divergence_bps": 20.0, "coinbase_move_bps_2s": -1.0}, "UP")[0] is True
    # Same divergence but Coinbase confirming -> no veto
    assert evaluate_coinbase_venue_veto({"coinbase_spot": 60000, "venue_divergence_bps": 20.0, "coinbase_move_bps_2s": 2.0}, "UP")[0] is False
    # DOWN shock mirrored
    assert evaluate_coinbase_venue_veto({"coinbase_spot": 60000, "venue_divergence_bps": -20.0, "coinbase_move_bps_2s": 1.0}, "DOWN")[0] is True
    assert evaluate_coinbase_venue_veto({"coinbase_spot": 60000, "venue_divergence_bps": 10.0, "coinbase_move_bps_2s": -1.0}, "UP")[0] is False


# ===========================================================================
# v3.4 UNIT TESTS: QUEUE PRIORITY, FAST CONFIRM, LEAD-STATE, ADAPTIVE THRESHOLD
# ===========================================================================

def test_compute_queue_priority_maker_price():
    from src.polymarket_research.polymarket_live_harvester import compute_queue_priority_maker_price

    # 30 shares, wall of 500 shares at 0.98, best_bid = 0.96 -> jumps to 0.97
    asks = [{"price": "0.98", "size": "500.0"}]
    bids = [{"price": "0.96", "size": "100.0"}]
    jump = compute_queue_priority_maker_price(
        entry_price=0.70, rem_shares=30.0, valid_bids=bids, valid_asks=asks, current_target_px=0.98
    )
    assert jump == 0.97

    # Wall too small (< max(300, 12 * 30 = 360)) -> returns None
    small_wall_asks = [{"price": "0.98", "size": "200.0"}]
    assert compute_queue_priority_maker_price(
        entry_price=0.70, rem_shares=30.0, valid_bids=bids, valid_asks=small_wall_asks, current_target_px=0.98
    ) is None

    # Bid too far away (< 0.98 - 0.03 = 0.95) -> returns None
    distant_bids = [{"price": "0.94", "size": "100.0"}]
    assert compute_queue_priority_maker_price(
        entry_price=0.70, rem_shares=30.0, valid_bids=distant_bids, valid_asks=asks, current_target_px=0.98
    ) is None

    # High entry price requires higher TP floor: entry = 0.83 -> min_tp = 0.83 + 0.14 = 0.97 -> 0.97 >= 0.97 ok
    assert compute_queue_priority_maker_price(
        entry_price=0.83, rem_shares=30.0, valid_bids=bids, valid_asks=asks, current_target_px=0.98
    ) == 0.97

    # Entry = 0.84 -> min_tp = 0.84 + 0.14 = 0.98 -> candidate 0.97 < 0.98 floor -> returns None
    assert compute_queue_priority_maker_price(
        entry_price=0.84, rem_shares=30.0, valid_bids=bids, valid_asks=asks, current_target_px=0.98
    ) is None


def test_fast_settlement_recheck_delay():
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    now = 1000.0
    harvester = PolymarketLiveHarvester(dry_run=True)
    # Entry within last 12s -> 0.20s fast recheck
    pos_recent = {"entry_ts": now - 3.0}
    assert harvester._settlement_recheck_delay(pos_recent, now) == 0.20
    # Entry older than 12s -> 5.0s standard backoff
    pos_old = {"entry_ts": now - 20.0}
    assert harvester._settlement_recheck_delay(pos_old, now) == 5.0


def test_fast_confirm_and_post_maker_exit_loop():
    import asyncio
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester, ExecutionStatus
    harvester = PolymarketLiveHarvester(dry_run=True)
    tid = "trade_test_fast_confirm"
    pos = {
        "trade_id": tid,
        "token_id": "tok_1",
        "entry_ts": time.time(),
        "status": ExecutionStatus.MATCHED_PENDING_SETTLEMENT,
        "exit_order_status": "AWAITING_DELTA_SETTLEMENT",
        "entry_shares": 20.0,
        "remaining_shares": 20.0,
        "notional_usd": 15.0,
    }
    harvester.active_positions[tid] = pos

    call_count = 0
    def mock_attempt(trade_id, p):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            p["exit_order_id"] = "exit_oid_123"
            return True
        return False

    harvester._attempt_maker_exit_post = mock_attempt
    posted = asyncio.run(harvester._fast_confirm_and_post_maker_exit(tid))
    assert posted is True
    assert call_count >= 2
    assert pos.get("exit_order_id") == "exit_oid_123"


def test_btc_lead_state_bridge_and_sympathy(tmp_path):
    from src.polymarket_research.polymarket_terminal_recorder import (
        write_lead_state,
        read_lead_state,
        evaluate_btc_sympathy,
    )
    p = tmp_path / "pm_lead_state_BTC.json"
    now_ns = time.time_ns()
    state = {
        "ts_ns": now_ns,
        "last_shock_ts_ns": now_ns - 100_000_000,  # 100ms ago
        "last_shock_vol_100ms": 2_500_000.0,
        "last_shock_ofi_100ms": 0.92,
        "last_shock_dir": "BUY",
        "last_shock_z_btc": 1.5,
    }
    assert write_lead_state(state, path=p) is True
    read_back = read_lead_state(path=p, max_age_ms=1500.0, now_ns=now_ns)
    assert read_back is not None
    assert read_back["last_shock_vol_100ms"] == 2_500_000.0

    # Stale lead state check (> 1500ms)
    assert read_lead_state(path=p, max_age_ms=1500.0, now_ns=now_ns + 2_000_000_000) is None

    # Sympathy evaluation: same dir (BUY), stale ETH ask (350ms) -> True
    assert evaluate_btc_sympathy(read_back, eth_flow_dir="BUY", eth_target_age_ask_ms=350.0, now_ns=now_ns) is True

    # Sympathy evaluation: diverging dir (SELL vs BUY) -> False
    assert evaluate_btc_sympathy(read_back, eth_flow_dir="SELL", eth_target_age_ask_ms=350.0, now_ns=now_ns) is False

    # Sympathy evaluation: fresh ETH ask (100ms < 300ms) -> False
    assert evaluate_btc_sympathy(read_back, eth_flow_dir="BUY", eth_target_age_ask_ms=100.0, now_ns=now_ns) is False

    # Sympathy evaluation: BTC shock too old (> 500ms) -> False
    assert evaluate_btc_sympathy(read_back, eth_flow_dir="BUY", eth_target_age_ask_ms=350.0, now_ns=now_ns + 600_000_000) is False


def test_adaptive_shock_threshold():
    from src.polymarket_research.polymarket_terminal_recorder import compute_adaptive_shock_threshold
    base = 1_500_000.0
    # No baseline -> returns base
    assert compute_adaptive_shock_threshold(base, None) == base
    assert compute_adaptive_shock_threshold(base, 0.0) == base

    # Quiet Asian hours: 100ms vol = $40,000 -> 18 * 40k = $720,000 -> clamped to 0.65 * base = $975,000
    assert compute_adaptive_shock_threshold(base, 40_000.0) == 0.65 * base

    # Noisy US hours: 100ms vol = $150,000 -> 18 * 150k = $2,700,000 -> clamped to 1.35 * base = $2,025,000
    assert compute_adaptive_shock_threshold(base, 150_000.0) == 1.35 * base

    # Midday hours: 100ms vol = $70,000 -> 18 * 70k = $1,260,000 (between 975k and 2,025k)
    assert compute_adaptive_shock_threshold(base, 70_000.0) == 1_260_000.0


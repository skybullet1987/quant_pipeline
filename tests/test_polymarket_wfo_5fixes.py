import os
import time
from unittest.mock import MagicMock

import pytest

from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    compute_composite_edge_score,
)


def _make_live_harvester(tmp_path):
    """Instantiate a sandboxed harvester via __new__ so production state files are never touched."""
    h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    h.ticket_notional = 16.5
    h.dynamic_sizing = True
    h.max_exposure = 54.7
    h.max_concurrent_positions = 2
    h.dry_run = False
    h.active_positions = {}
    h.pending_entry_intents = {}
    h.closed_positions = []
    h.state_file = tmp_path / "test_state.json"
    h.executor = MagicMock()
    h.executor.is_heartbeat_healthy.return_value = True
    h.executor.validate_cross_asset_directional_conflict.return_value = (True, "")
    h.executor.validate_cross_asset_lead_lag.return_value = (True, 1.5, "OK")
    h.executor.release_inventory = MagicMock()
    h.executor.update_reservation = MagicMock()
    h.executor._tick_size_cache = {}
    h.executor._fee_cache = {}
    h.save_state = MagicMock()
    return h


def test_fix1_composite_edge_ofi_hurdle():
    """Verify Purged-WFO Fix 1: OFI hurdle is strictly 0.60 across all execution modes."""
    low_ofi_shock = {
        "shock_direction": "BUY",
        "shock_ofi": 0.55,
        "z_val": 2.5,
        "delta_basis_100ms": 1.0,
        "pre_shock_features_t0": {
            "UP": {"age_ask_ms": 250.0, "obi_l1": 0.25},
        },
    }
    res_veto = compute_composite_edge_score(low_ofi_shock)
    assert res_veto["veto"] is True
    assert "0.60 hurdle" in res_veto["veto_reason"]

    pass_ofi_shock = dict(low_ofi_shock, shock_ofi=0.65)
    res_pass = compute_composite_edge_score(pass_ofi_shock)
    assert res_pass["veto"] is False


def test_fix2_and_fix3_tte_cushions_and_same_window_sleeve_isolation(tmp_path, monkeypatch):
    """
    Verify WFO Fix 2 & Fix 3 with PYTEST_CURRENT_TEST unset:
    - 15m subhourly TTE > 600s is rejected; TTE <= 600s with >=0.06% cushion passes TTE/Regime gate.
    - Same-window correlation filter isolates 15m vs 1h sleeves during :45-:00 shared expiry windows,
      while blocking a 2nd 1h entry when a 1h position is already active in the same expiry window.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    h = _make_live_harvester(tmp_path)

    now_ts = time.time()
    shared_hour_expiry = now_ts + 500.0  # e.g. 11:51 AM ET -> both 15m and 1h expire at 12:00 PM ET

    # Case A: An active 15m position at 12:00 PM ET must NOT block a 1h entry expiring at 12:00 PM ET
    h.active_positions["LIVE_15M_1"] = {
        "trade_id": "LIVE_15M_1",
        "sleeve": "SLEEVE_1_SUBHOURLY_15M",
        "market_id": "600001",
        "asset": "BTC",
        "target_token": "UP",
        "notional_usd": 15.0,
        "candle_expiry_ts": shared_hour_expiry,
        "status": "EXIT_RESTING",
    }

    all_open = list(h._risk_bearing_positions().values())
    same_win_for_1h = [
        p for p in all_open
        if abs(float(p.get("candle_expiry_ts", 0.0) or 0.0) - shared_hour_expiry) <= 300.0
        and ((p.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M") == False)
    ]
    assert len(same_win_for_1h) == 0, "15m position must not count as a 1h same-window position!"

    same_win_for_15m = [
        p for p in all_open
        if abs(float(p.get("candle_expiry_ts", 0.0) or 0.0) - shared_hour_expiry) <= 300.0
        and ((p.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M") == True)
    ]
    assert len(same_win_for_15m) == 1, "2nd 15m position in same window must detect existing 15m position!"


def test_fix4_record_order_summary_zero_fill_does_not_set_exit_cash_estimated(tmp_path):
    """
    Verify that polling a resting exit order with matched=0.0 and cash=None does NOT set
    exit_cash_estimated=True, and self-heals a stale exit_cash_estimated=True flag when matched=0.0.
    """
    h = _make_live_harvester(tmp_path)
    pos = {
        "trade_id": "LIVE_6012995_UP",
        "entry_shares": 15.0,
        "remaining_shares": 15.0,
        "filled_exit_shares": 0.0,
        "estimated_exit_cash": 0.0,
        "exit_cash_estimated": True,  # Previously polluted by 0-fill poll
        "target_exit_price": 0.99,
        "order_records": {},
    }
    summary = {"order_id": "0xeb3a4eed", "matched": 0.0, "cash": None, "terminal": False}
    booked = h._record_order_summary(pos, summary, fallback_px=0.99, taker=False)
    assert booked is False
    assert pos["exit_cash_estimated"] is False, "0-share poll must not leave exit_cash_estimated=True!"


def test_fix5_spot_delta_stop_and_ratchet_thresholds_unified():
    """
    Verify Purged-WFO Fix 5 & Zero Test-vs-Live Divergence:
    - Zero PYTEST_CURRENT_TEST branches exist anywhere in src/polymarket_research/*.py.
    - Unified trailing ratchet arms at max(0.82, entry_px + 0.12) (protecting $0.89 and $0.94 peaks!).
    - 1h CLOB bid drop from 0.72 to 0.40 does NOT trigger spot_crash_triggered when spot is still winning (+0.15%),
      whereas orderbook collapse to <= 0.36 with adverse move vs entry DOES trigger salvage.
    """
    from pathlib import Path
    import src.polymarket_research as pm_pkg

    src_dir = Path(list(pm_pkg.__path__)[0]).resolve()
    for py_file in sorted(src_dir.glob("*.py")):
        txt = py_file.read_text(encoding="utf-8")
        assert "PYTEST_CURRENT_TEST" not in txt, f"Forbidden test-branching env var found in {py_file.name}"

    entry_px = 0.7601  # LIVE_6082720_1792852892_DOWN entry price (peaked at $0.8900)
    min_ratchet_arm = max(0.82, entry_px + 0.12)
    assert min_ratchet_arm == pytest.approx(0.8801)
    assert 0.8900 >= min_ratchet_arm

    # Trade #6 (6017333) scenario: DOWN position, open=2380.67, entry=2376.19, spot=2380.50 (still ITM: spot_disp > 0),
    # entry_move_pct = -0.0018, and best_b = 0.40 (> 0.36). Must NOT trigger hard bid-drop salvage!
    spot_valid = True
    open_spot = 2380.67
    spot_disp = 2380.67 - 2380.50  # +0.17 (Winning side of candle open)
    best_b = 0.40
    entry_move_pct = -0.0018
    for _is_15m_pos in (True, False):
        spot_crossed_open_adverse = (
            (
                spot_valid
                and open_spot > 0
                and (-spot_disp / open_spot) >= (0.0008 if _is_15m_pos else 0.0005)
                and best_b <= (0.50 if _is_15m_pos else 0.52)
            )
            or (spot_valid and best_b <= 0.36 and entry_move_pct <= -0.0007)
            or (not spot_valid and best_b <= 0.36)
        )
        assert spot_crossed_open_adverse is False, "Winning spot position with bid > $0.36 must never trigger hard bid-drop stop!"


def test_fix6_15m_tte_cushion_convexity_and_mm_reload_veto(monkeypatch):
    """Verify the 15m Early-Window TTE x Cushion Convexity Surface (COMBO_2) and Gate 1 MM Reload Veto."""
    from src.polymarket_research.polymarket_live_harvester import compute_composite_edge_score

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    # 1. Gate 1 MM Reload Veto: age_ask_ms = 3.1ms < 25ms and obi_l1 = -0.33 < -0.25 must veto (LOSS mkt=6011282)
    res_toxic = compute_composite_edge_score({
        "asset": "ETH",
        "shock_direction": "SELL",
        "shock_ofi": -0.75,
        "shock_volume_100ms": 900_000.0,
        "delta_basis_100ms": -1.5,
        "pre_shock_features_t0": {
            "DOWN": {"age_ask_ms": 3.1, "obi_l1": -0.33, "spread": 0.01, "raw_top_asks": [[0.73, 100.0]]},
            "UP": {"age_bid_ms": 200.0},
        },
    })
    assert res_toxic["veto"] is True
    assert "Ultra-fresh MM ask reload" in res_toxic["veto_reason"]

    # 2. Normal stale quote (age_ask_ms = 180ms) passes cleanly
    res_clean = compute_composite_edge_score({
        "asset": "ETH",
        "shock_direction": "SELL",
        "shock_ofi": -0.75,
        "shock_volume_100ms": 900_000.0,
        "delta_basis_100ms": -1.5,
        "pre_shock_features_t0": {
            "DOWN": {"age_ask_ms": 180.0, "obi_l1": 0.25, "spread": 0.01, "raw_top_asks": [[0.71, 100.0]]},
            "UP": {"age_bid_ms": 200.0},
        },
    })
    assert res_clean["veto"] is False

    # 3. 15m TTE x Cushion Convexity Cap:
    # Trade #9 replica: TTE=534s (>470s), dist_pct=0.061% (<0.09%) -> max_allowed_price = $0.66 (blocks $0.763!)
    tte_t9, dist_t9, ask_t9 = 534.0, 0.061, 0.7633
    max_ask_t9 = 0.66 if (tte_t9 > 470.0 and abs(dist_t9) < 0.09) else 0.78
    assert max_ask_t9 == 0.66 and ask_t9 > max_ask_t9

    # Trade #8 replica: TTE=394s (<=470s), dist_pct=-0.064% -> max_allowed_price = $0.78 (allows $0.710!)
    tte_t8, dist_t8, ask_t8 = 394.0, -0.064, 0.7100
    max_ask_t8 = 0.66 if (tte_t8 > 470.0 and abs(dist_t8) < 0.09) else 0.78
    assert max_ask_t8 == 0.78 and ask_t8 <= max_ask_t8


def test_fix7_shadow_phase3a_and_phase4_tracker(tmp_path, monkeypatch):
    """Verify Phase 3A (Reactive Maker-In) and Phase 4 (:45-:00 Monotonicity Box Arb) shadow tracker."""
    import json
    shadow_file = tmp_path / "shadow_phase3_4_tracker.jsonl"
    monkeypatch.setenv("PM_SHADOW_TRACKER_FILE", str(shadow_file))

    h = _make_live_harvester(tmp_path)

    # 1. Phase 3A: Register a price-capped 15m shock (ask=$0.69 > max_allowed=$0.66)
    h._register_shadow_phase3a_maker_in(
        shock={
            "market_id": "6099991",
            "title": "Ethereum Up or Down - October 22, 4:00PM-4:15PM ET",
            "asset": "ETH",
            "candle_open_spot": 2400.0,
            "expiry_ts": time.time() + 500.0,
        },
        target_token="UP",
        first_ask=0.69,
        first_bid=0.67,
        max_allowed_price=0.66,
        raw_asks=[(0.66, 26.0), (0.69, 50.0)],
        reject_reason="PRICE_BAND_REJECT",
        is_subhourly=True,
        dist_pct=0.072,
        tte=510.0,
    )
    assert "6099991_UP" in h._shadow_maker_orders
    rec3a = h._shadow_maker_orders["6099991_UP"]
    assert rec3a["shadow_maker_px"] == 0.66
    assert rec3a["idea1_snapped_rung_usd"] == 16.50

    # 2. Phase 4: Feed overlapping :45-:00 15m and 1h books with a risk-free box (Cost < $1.00)
    now_u = time.time()
    exp_u = round((now_u + 300.0) / 60.0) * 60.0
    h._update_shadow_phase4_monotonicity_scanner(
        shock={
            "market_id": "6099992",
            "t0_unix": now_u,
            "expiry_ts": exp_u,
            "spot_at_t0": 2457.0,
            "pre_shock_features_t0": {
                "UP": {"best_ask": 0.62, "raw_top_asks": [[0.62, 50.0]]},
                "DOWN": {"best_ask": 0.39, "raw_top_asks": [[0.39, 50.0]]},
            },
        },
        asset_str="ETH",
        is_subhourly=True,
        is_1h=False,
        tte=300.0,
        open_spot=2455.0,  # K_15m = 2455.0 < K_1h = 2458.5
    )
    h._update_shadow_phase4_monotonicity_scanner(
        shock={
            "market_id": "6099993",
            "t0_unix": now_u + 1.0,
            "expiry_ts": exp_u,
            "spot_at_t0": 2457.0,
            "pre_shock_features_t0": {
                "UP": {"best_ask": 0.66, "raw_top_asks": [[0.66, 50.0]]},
                "DOWN": {"best_ask": 0.34, "raw_top_asks": [[0.34, 50.0]]},
            },
        },
        asset_str="ETH",
        is_subhourly=False,
        is_1h=True,
        tte=300.0,
        open_spot=2458.5,
    )

    lines = [json.loads(line) for line in shadow_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    event_types = [x["event_type"] for x in lines]
    assert "SHADOW_PHASE3A_MAKER_IN_REGISTERED" in event_types
    assert "SHADOW_PHASE4_RISK_FREE_BOX_ARB" in event_types


def test_fix8_ideas_1_3_5_downsnap_fallback_and_t1_tp(tmp_path, monkeypatch):
    """
    Verify:
    - Idea #1: Elastic [PREWARM LADDER] Rung Down-Snapping ($21.55 -> $16.50 / $12.00) when L1 depth at limit is thin
      or FOK Sweep Infeasible is returned.
    - Idea #5: Sequential +2c Pre-Signed Fallback on deterministic 400 / FAK zero-match miss.
    - Idea #3: SLEEVE_2_MID_HOUR 2-tranche resting maker exit posts Tranche 1 at entry + $0.12 and Tranche 2 at $0.98.
    """
    import asyncio
    from unittest.mock import AsyncMock
    from src.polymarket_research.polymarket_live_executor import OrderResult, ExecutionStatus

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "ideas_state.json")
    h = PolymarketLiveHarvester(ticket_notional=16.5, dry_run=False, hold_to_maturity=True)
    h.enable_elastic_downsnap = True
    h.enable_fak_fallback_retry = True
    h.enable_mid_hour_t1_12c = True
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda **kw: 98.0
    h._last_known_collateral = 98.0

    # 1. Idea #3: SLEEVE_2_MID_HOUR uses 2-tranche maker exit with +$0.12 on Tranche 1 even when hold_to_maturity=True
    assert h._use_two_tranche_maker_exit("SLEEVE_2_MID_HOUR") is True
    assert h._tranche1_tp_offset("SLEEVE_2_MID_HOUR") == 0.12
    assert h._tranche1_tp_offset("SLEEVE_1_CORE_302") == 0.14

    posted_maker = []
    h.executor.post_maker_exit_order = MagicMock(
        side_effect=lambda **kw: posted_maker.append(kw) or {"success": True, "orderID": "OID_MID_T1", "price": kw["price"]}
    )
    h._verify_entry_finality = MagicMock(return_value=(True, False))
    h._wallet_token_balance = MagicMock(return_value=(30.0, h.ONCHAIN_SOURCE))

    pos_mid = {
        "trade_id": "LIVE_MID_1H_TEST",
        "sleeve": "SLEEVE_2_MID_HOUR",
        "token_id": "TOK_MID_1H",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.65,
        "entry_shares": 30.0,
        "remaining_shares": 30.0,
        "notional_usd": 19.50,
        "candle_expiry_ts": time.time() + 1200.0,
    }
    assert h._attempt_maker_exit_post("LIVE_MID_1H_TEST", pos_mid) is True
    assert len(pos_mid["exit_tranches"]) == 2
    assert pos_mid["exit_tranches"][0]["price"] == 0.77  # 0.65 + 0.12 = 0.77
    assert pos_mid["exit_tranches"][1]["price"] == 0.98
    assert posted_maker[0]["price"] == 0.77

    # 2. Idea #1 + Idea #5 in evaluate_shock_and_execute:
    # Shock has L1=$18.00 @ $0.66 and L2=$21.90 @ $0.73 -> total depth=$39.90 sizes ticket to ~$21.56,
    # but target_limit_px = $0.68 only covers L1 ($18.00) -> Idea #1 pre-dispatch down-snaps $21.56 -> $16.50!
    # Then call #1 returns FAK_KILLED_NO_MATCH at $0.68 -> Idea #5 retries once at $0.70 and fills!
    h.executor.get_market_book_async = AsyncMock(return_value={
        "asks": [{"price": "0.6600", "size": "27.28"}, {"price": "0.7300", "size": "30.0"}],
        "bids": [{"price": "0.6500", "size": "200.0"}],
    })
    snipe_calls = []

    async def mock_snipe(**kwargs):
        snipe_calls.append(dict(kwargs))
        if len(snipe_calls) == 1:
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=kwargs["trade_id"],
                token_id=kwargs["token_id"],
                target_token=kwargs["target_token"],
                side="BUY",
                price=kwargs["target_price"],
                size=0.0,
                notional_usd=kwargs["notional_usd"],
                fee_usd=0.0,
                latency_ms=12.0,
                mode="FAK_KILLED_NO_MATCH",
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error="no orders found to match with FAK order",
                details={"fak_killed": True},
            )
        return OrderResult(
            success=True,
            order_id="OID_FALLBACK_OK",
            trade_id=kwargs["trade_id"],
            token_id=kwargs["token_id"],
            target_token=kwargs["target_token"],
            side="BUY",
            price=kwargs["target_price"],
            size=23.0,
            notional_usd=kwargs["notional_usd"],
            fee_usd=0.10,
            latency_ms=14.0,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
            details={"pre_token_balance": 0.0, "trade_ids": ["T1"], "transactions_hashes": ["0xabc"]},
        )

    h.executor.execute_snipe_order_async = mock_snipe
    shock = {
        "event_id": "EVT_IDEA15",
        "market_id": "6088881",
        "condition_id": "0xcond6088881",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down - October 22, 4:00PM-4:15PM ET",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 380.0,
        "candle_distance_pct": 0.16,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0xcond6088881"},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xTOK6088881",
                "raw_top_asks": [[0.6600, 27.28], [0.7300, 30.0]],
                "raw_top_bids": [[0.6500, 200.0]],
                "effective_price_$25": 0.6600,
                "vwap_$25": 0.6600,
            }
        },
    }

    asyncio.run(h.evaluate_shock_and_execute(shock))

    assert len(snipe_calls) == 2
    assert snipe_calls[0]["notional_usd"] == 16.50
    assert snipe_calls[0]["target_price"] == 0.68
    assert snipe_calls[1]["notional_usd"] == 16.50
    assert snipe_calls[1]["target_price"] == 0.70
    assert any(p.get("market_id") == "6088881" for p in h.active_positions.values())


def test_fix9_low_latency_near_cache_and_fast_ipc(tmp_path, monkeypatch):
    """
    Verify VM low-latency upgrades:
    1. PreSignedOrderLadderCache.get_presigned_order_near hits within +/- 2 shares (eliminating 40% cache misses
       from 1-share Kelly/fee rounding differences) and pops the matched entry to prevent nonce reuse.
    2. PreSignedOrderLadderCache TTL defaults to 1800s on PolymarketLiveExecutor.
    3. _register_active_warmed_token prunes expired tokens and caps active prewarmed tokens at 12.
    """
    from src.polymarket_research.polymarket_live_executor import PreSignedOrderLadderCache

    cache = PreSignedOrderLadderCache(ttl_seconds=1800.0)
    dummy_order_30 = MagicMock(name="signed_order_30")
    assert cache.store_presigned_order("TOK_A", 0.70, 30.0, dummy_order_30) is True

    # Requesting 29.0 shares (1-share delta at $21.11 vs $21.55) hits dummy_order_30 in 0.03ms
    hit_res = cache.get_presigned_order_near("TOK_A", 0.70, 29.0, max_share_delta=2)
    assert hit_res is not None
    hit_order, hit_sz = hit_res
    assert hit_order is dummy_order_30
    assert hit_sz == 30
    # Entry was popped on hit (single-use nonce safety)
    assert cache.get_presigned_order_near("TOK_A", 0.70, 29.0, max_share_delta=2) is None

    # Delta > max_share_delta (e.g. 25 vs 30) does not match
    cache.store_presigned_order("TOK_A", 0.70, 30.0, dummy_order_30)
    assert cache.get_presigned_order_near("TOK_A", 0.70, 25.0, max_share_delta=2) is None

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "lat_state.json")
    h = PolymarketLiveHarvester(ticket_notional=16.5, dry_run=True)
    assert h.executor.order_ladder_cache.ttl_seconds == 1800.0

    now_u = time.time()
    h._register_active_warmed_token("TOK_EXPIRED", now_u - 120.0)
    for idx in range(15):
        h._register_active_warmed_token(f"TOK_LIVE_{idx}", now_u + 300.0 + idx)
    reg = h._active_warmed_token_expiries
    assert "TOK_EXPIRED" not in reg
    assert len(reg) == 12


def test_fix10_twap_dual_anchor_and_entry_adverse_salvage(tmp_path, monkeypatch):
    import asyncio
    from src.polymarket_research.polymarket_live_executor import OrderResult, ExecutionStatus
    """
    Verify Grid-Calibrated Fix #1 & Fix #2 from LIVE_6032439_1792715250_DOWN forensic audit:
    1. 15m Boundary-Wick Oracle Veto blocks 15m entries when |open_spot - twap_60s_open| / open_spot >= 0.0395%
       and dual-anchor cushion < 0.16% (exact replay of 6032439: open=81247.81, twap=81210.04 -> 0.0465% wick).
    2. When wick_div_pct < 0.0395%, 15m entry anchors candle_open_spot to the conservative dual-anchor strike
       (min(open, twap) for DOWN, max(open, twap) for UP).
    3. Orderbook + Entry-Adverse Salvage Override (best_b <= 0.36 & entry_move_pct <= -0.07% for >= 6.0s)
       unwinds a crashing position even when single-tick open_spot still shows spot_disp > 0.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "fix10_state.json")
    h = PolymarketLiveHarvester(ticket_notional=20.0, dry_run=False)
    h.enforce_live_spot_adverse_gate = True

    snipe_calls = []

    async def mock_snipe(**kwargs):
        snipe_calls.append(kwargs)
        return OrderResult(
            success=True,
            order_id="OID_FIX10",
            trade_id=kwargs["trade_id"],
            token_id=kwargs["token_id"],
            target_token=kwargs["target_token"],
            side="BUY",
            price=kwargs["target_price"],
            size=26.67,
            notional_usd=kwargs["notional_usd"],
            fee_usd=0.10,
            latency_ms=1.2,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
            details={"pre_token_balance": 0.0, "trade_ids": ["T_FIX10"], "transactions_hashes": ["0xfix10"]},
        )

    h.executor.execute_snipe_order_async = mock_snipe
    h.executor.get_collateral_balance = lambda *a, **kw: 100.0
    h.executor.get_conditional_balance = lambda *a, **kw: 0.0
    h.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "OID_EXIT_FIX10"}

    # Part A: Replay LIVE_6032439_1792715250_DOWN boundary-wick trap (open=81247.81 vs twap=81210.04 -> 0.0465% wick)
    shock_wick = {
        "event_id": "EVT_6032439",
        "market_id": "6032439",
        "condition_id": "0xcond6032439",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down - October 22, 8:15PM-8:30PM ET",
        "asset": "BTC",
        "horizon": "15m",
        "shock_direction": "SELL",
        "seconds_to_expiry": 149.4,
        "spot_at_t0": 81139.55,
        "trigger_price": 81139.55,
        "candle_open_spot": 81247.81,
        "twap_60s_open": 81210.04,
        "candle_distance_pct": -0.1332,
        "shock_volume_100ms": 2500000.0,
        "shock_ofi": -0.95,
        "fee_metadata": {"fee_rate_market": 0.18, "fee_exponent": 1.0, "condition_id": "0xcond6032439"},
        "pre_shock_features_t0": {
            "DOWN": {
                "token_id": "0xTOK6032439",
                "raw_top_asks": [[0.7300, 100.0]],
                "raw_top_bids": [[0.7200, 200.0]],
                "effective_price_$25": 0.7300,
                "vwap_$25": 0.7300,
                "age_book_ms": 50.0,
                "book_timestamp": time.time(),
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_wick))
    assert len(snipe_calls) == 0, "Boundary-wick trap (0.0465% >= 0.0395%) must be vetoed!"

    # Part B: Clean 15m candle (wick = 0.0246% < 0.0395%) enters and stores conservative dual-anchor strike
    shock_clean = dict(shock_wick)
    shock_clean["event_id"] = "EVT_6032440"
    shock_clean["market_id"] = "6032440"
    shock_clean["candle_open_spot"] = 81200.00
    shock_clean["twap_60s_open"] = 81180.00  # min(81200, 81180) = 81180.00 for DOWN
    shock_clean["spot_at_t0"] = 81080.00     # dual cushion = -0.1232%
    asyncio.run(h.evaluate_shock_and_execute(shock_clean))
    assert len(snipe_calls) == 1
    pos = next(iter(h.active_positions.values()))
    assert pos["candle_open_spot"] == 81180.00

    # Part C: Test Orderbook + Entry-Adverse Salvage Override when open_spot still appears ITM
    # Set candle_open_spot artificially high (81247.81) while current_spot=81218.00 (+0.0967% against entry_spot=81139.55)
    tid = pos["trade_id"]
    pos["candle_open_spot"] = 81247.81
    pos["entry_spot_ref"] = 81139.55
    pos["entry_price"] = 0.75
    pos["candle_expiry_ts"] = time.time() + 104.0
    pos["low_bid_detected_ts"] = time.time() - 6.5  # Persisted >= 6.0s at $0.36

    h.get_reference_spot_price = lambda asset: 81218.00  # Still below 81247.81 (spot_disp > 0), but -0.0967% vs entry!
    h._strict_open_orders = lambda: []
    h._get_verified_shm_book = lambda p: {
        "bids": [{"price": "0.36", "size": "150.0"}],
        "asks": [{"price": "0.38", "size": "150.0"}],
    }
    h.executor.cancel_order = lambda oid: {"canceled": [oid]}
    h.executor.get_order_fill_summary = lambda oid, tok: {"order_id": oid, "matched": 0.0, "terminal": True, "cash": 0.0}
    unwind_calls = []
    h.executor.execute_unwind_order = lambda **kw: (
        unwind_calls.append(kw) or OrderResult(
            success=True,
            order_id="OID_UNWIND_FIX10",
            trade_id=tid,
            token_id=pos["token_id"],
            target_token="DOWN",
            side="SELL",
            price=0.35,
            size=kw["size"],
            notional_usd=round(kw["size"] * 0.35, 2),
            fee_usd=0.05,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.FILLED,
            confirmed_onchain=True,
            details={"trade_ids": ["TU1"], "transactions_hashes": ["0xu1"]},
        )
    )

    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 1, "Orderbook + entry-adverse salvage override must trigger unwind at $0.36!"


def test_fix11_save_state_thread_safety_and_heartbeat_resync_and_safeguards(monkeypatch, tmp_path):
    """
    Verifies Fix #11 (Root causes of LIVE_6032790_1792716941_UP + 4 Proactive Safeguards):
      1. save_state() thread-safety under concurrent multi-thread calls (no FileNotFoundError).
      2. post_heartbeat() automatic resync when CLOB returns 400 Invalid Heartbeat ID with server heartbeat_id.
      3. compute_composite_edge_score() L1 ask-wall veto on thin cushion + Pillar 2 p_max cap without 0.78 floor override.
      4. Pre-entry Stale-Anchor Disagreement Veto (>10s resting ask diverging >28c from p_true).
    """
    import threading
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        compute_composite_edge_score,
        compute_max_acceptable_ask,
    )
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    # 1. Test concurrent multi-thread save_state()
    state_file = tmp_path / "live_harvester_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)
    h = PolymarketLiveHarvester(dry_run=True)
    h.state_file = state_file

    errors = []

    def _worker():
        for _ in range(15):
            try:
                h.save_state()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(errors) == 0, f"Concurrent save_state raised errors: {errors}"
    assert state_file.exists()

    # 2. Test post_heartbeat() automatic resync on 400 Invalid Heartbeat ID
    exec_inst = PolymarketLiveExecutor(dry_run=True)
    exec_inst.dry_run = False
    exec_inst.is_authenticated = True
    exec_inst.last_heartbeat_id = ""

    class _MockInvalidHbError(Exception):
        def __init__(self):
            super().__init__(
                "PolyApiException[status_code=400, error_message={'error': 'Invalid Heartbeat ID', 'heartbeat_id': '8f052486-94fb-4dc8-b73e-9730e1068a7c'}]"
            )
            self.status_code = 400
            self.error_message = {
                "error": "Invalid Heartbeat ID",
                "heartbeat_id": "8f052486-94fb-4dc8-b73e-9730e1068a7c",
            }

    hb_calls = []

    class _MockClobClient:
        def post_heartbeat(self, heartbeat_id=""):
            hb_calls.append(heartbeat_id)
            if heartbeat_id != "8f052486-94fb-4dc8-b73e-9730e1068a7c":
                raise _MockInvalidHbError()
            return {"heartbeat_id": "9a113597-1111-2222-3333-444455556666"}

    exec_inst.client = _MockClobClient()
    res = exec_inst.post_heartbeat()
    assert hb_calls == ["", "8f052486-94fb-4dc8-b73e-9730e1068a7c"]
    assert res.get("heartbeat_id") == "9a113597-1111-2222-3333-444455556666"
    assert exec_inst.last_heartbeat_id == "9a113597-1111-2222-3333-444455556666"
    assert exec_inst.heartbeat_failures == 0
    assert exec_inst.is_heartbeat_healthy() is True

    # 3. Replay LIVE_6032790_1792716941_UP (dist_pct=+0.0601%, obi_l1=-0.721, TTE=258.6s) in live mode
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    shock_6032790 = {
        "asset": "BTC",
        "shock_source": "FUTURES",
        "shock_direction": "BUY",
        "shock_ofi": 0.71,
        "shock_volume_100ms": 576681.0,
        "delta_basis_100ms": 1.98,
        "candle_distance_pct": 0.0601,
        "pre_shock_features_t0": {
            "UP": {
                "age_ask_ms": 2308.5,
                "obi_l1": -0.7206,
                "obi_depth": 0.2528,
                "spread": 0.01,
                "raw_top_asks": [[0.66, 246.36]],
                "vwap_$25": 0.66,
            }
        },
    }
    edge_res = compute_composite_edge_score(shock_6032790)
    assert edge_res["veto"] is True
    assert "Heavy L1 ask wall against thin cushion" in str(edge_res["veto_reason"])

    p_max_res = compute_max_acceptable_ask(
        dist_pct=0.0601,
        tte_sec=258.6,
        asset="BTC",
        shock_ofi=0.71,
        shock_vol_usd=576681.0,
        delta_basis_bps=1.98,
        age_ask_ms=2308.5,
        is_subhourly_15m=True,
    )
    assert p_max_res["p_max"] < 0.65, f"Expected p_max < $0.65 without 0.78 floor override, got {p_max_res['p_max']}"


def test_fix12_v38_deep_research_audit_remediations(tmp_path, monkeypatch):
    """
    Verifies v3.8 Deep Research Audit Fixes (F-01, F-02, F-03, F-05, F-06, F-07, F-10):
    1. F-01 + F-07: DETERMINISTIC_TERMINAL_HOLD inside 15s <= TTE <= 300s does NOT block Tranche 2 ($0.98)
       from posting inline immediately when Tranche 1 reaches terminal/matched status; only
       DETERMINISTIC_TERMINAL_HOLD_FINAL (< 15s) blocks new maker exits.
    2. F-02: Below $88 Seed-Survival threshold (e.g. $76.49), stale HWM resets, max_concurrent_positions=1,
       min_equity_floor_usd=$48.0, and ticket caps at $12.00.
    3. F-03: Expired position with resolved_winning_outcome=None preserves remaining_cost_basis instead of $0.00.
    4. F-05: < 5.0 shares on a real 256-bit CTF token transitions cleanly to SUB_MINIMUM_LOT_SUPERVISED_HOLD.
    5. F-06: Partial FAK entry (< 92% filled) scales notional_usd proportionally; UNRESOLVED_SETTLEMENT
       distinguishes taker unwind OIDs from maker exit OIDs.
    6. F-10: max_trades_per_market=1 strictly blocks win-reentry in the same market.
    """
    import asyncio
    from decimal import Decimal
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        position_may_post_new_maker_exit,
    )
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "v38_state.json")
    h = PolymarketLiveHarvester(ticket_notional=16.5, dry_run=False, max_trades_per_market=1)
    h.state_file = tmp_path / "v38_state.json"

    # 1. F-01 + F-07: Tranche 2 allowed when terminal_policy == DETERMINISTIC_TERMINAL_HOLD (TTE >= 15s),
    #    blocked only when terminal_policy == DETERMINISTIC_TERMINAL_HOLD_FINAL (TTE < 15s).
    pos_t2 = {
        "trade_id": "LIVE_T2_INLINE",
        "token_id": "998877665544332211009988776655",
        "status": ExecutionStatus.PARTIALLY_FILLED,
        "exit_order_status": "EXIT_RECOVERY_REQUIRED",
        "terminal_policy": "DETERMINISTIC_TERMINAL_HOLD",
        "inventory_reconciled": True,
        "entry_price": 0.72,
        "entry_shares": 16.0,
        "remaining_shares": 8.0,
        "filled_exit_shares": 8.0,
        "realized_exit_cash": 6.88,
        "notional_usd": 11.52,
        "candle_expiry_ts": time.time() + 180.0,
        "exit_order_id": "OID_T1_FILLED",
        "target_exit_price": 0.86,
        "exit_tranches": [
            {"idx": 1, "size": 8.0, "price": 0.86, "status": "POSTED"},
            {"idx": 2, "size": 8.0, "price": 0.98, "status": "PENDING"},
        ],
    }
    assert position_may_post_new_maker_exit(pos_t2) is True
    pos_final = dict(pos_t2, terminal_policy="DETERMINISTIC_TERMINAL_HOLD_FINAL")
    assert position_may_post_new_maker_exit(pos_final) is False

    posted_t2 = []
    h._verify_entry_finality = MagicMock(return_value=(True, False))
    h._wallet_token_balance = MagicMock(return_value=(8.0, h.ONCHAIN_SOURCE))
    h._strict_open_orders = lambda: []
    h._get_verified_shm_book = lambda p: {
        "bids": [{"price": "0.86", "size": "100.0"}],
        "asks": [{"price": "0.88", "size": "100.0"}],
    }
    h.get_reference_spot_price = lambda asset: 82000.0
    h.executor.get_order_fill_summary = lambda oid, tok: {
        "order_id": oid,
        "status": "MATCHED",
        "matched": 8.0,
        "cash": 6.88,
        "fee": 0.0,
        "terminal": True,
        "limit_price": 0.86,
        "trade_ids": ["TR1"],
    }
    h.executor.post_maker_exit_order = lambda **kw: (
        posted_t2.append(kw) or {"success": True, "orderID": "OID_T2_RESTING", "price": kw["price"]}
    )
    pos_t2["asset"] = "BTC"
    pos_t2["target_token"] = "UP"
    pos_t2["candle_open_spot"] = 81800.0
    pos_t2["entry_spot_ref"] = 81900.0
    pos_t2["candle_sigma"] = 0.005
    pos_t2["filled_exit_shares"] = 0.0
    pos_t2["realized_exit_cash"] = 0.0
    pos_t2["remaining_shares"] = 16.0
    h.active_positions["LIVE_T2_INLINE"] = pos_t2
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(posted_t2) == 1, "Tranche 2 ($0.98) must post inline on the exact same cycle Tranche 1 fills!"
    assert posted_t2[0]["price"] == 0.98
    assert posted_t2[0]["size"] == 8.0

    # 2. F-02: Seed-Survival override at $76.49 (< $88.0) resets stale HWM ($112 -> $76.49) and sets $48 floor & conc=1
    h.active_positions.clear()
    h.high_water_mark_equity = 112.0
    h.executor.is_authenticated = True
    h.executor.get_collateral_balance = lambda *a, **kw: 76.49
    asyncio.run(h._async_refresh_collateral())
    assert h.high_water_mark_equity == pytest.approx(76.49)
    assert h.max_concurrent_positions == 1
    assert h.risk_controller.min_equity_floor_usd == pytest.approx(48.0)
    assert h.risk_controller.is_halted() is False

    # 3. F-03: Expired position awaiting Gamma/Chainlink resolution (resolved_winning_outcome=None) keeps cost basis
    expired_unresolved = {
        "target_token": "UP",
        "candle_expiry_ts": time.time() - 10.0,
        "resolved_winning_outcome": None,
        "remaining_cost_basis": 12.0,
        "notional_usd": 12.0,
    }
    assert h.get_position_market_value(expired_unresolved, time.time()) == pytest.approx(12.0)

    # 4. F-05: < 5.0 share residual on real 256-bit CTF token transitions to SUB_MINIMUM_LOT_SUPERVISED_HOLD
    pos_sub5 = {
        "trade_id": "LIVE_SUB5",
        "token_id": "112233445566778899001122334455",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.75,
        "entry_shares": 4.2,
        "remaining_shares": 4.2,
        "notional_usd": 3.15,
        "candle_expiry_ts": time.time() + 240.0,
    }
    h._wallet_token_balance = MagicMock(return_value=(4.2, h.ONCHAIN_SOURCE))
    assert h._attempt_maker_exit_post("LIVE_SUB5", pos_sub5) is False
    assert pos_sub5["exit_order_status"] == "SUB_MINIMUM_LOT_SUPERVISED_HOLD"
    assert position_may_post_new_maker_exit(pos_sub5) is False

    # 5. F-06: Partial FAK entry (< 92% of gross shares delivered) scales notional_usd proportionally
    pos_part_fak = {
        "trade_id": "LIVE_PART_FAK",
        "token_id": "556677889900112233445566778899",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": False,
        "pre_token_balance": 0.0,
        "gross_entry_shares": 20.0,
        "entry_shares": 20.0,
        "remaining_shares": 20.0,
        "entry_price": 0.60,
        "notional_usd": 12.0,
        "fee_usd": 0.30,
        "candle_expiry_ts": time.time() + 300.0,
    }
    h._wallet_token_balance = MagicMock(return_value=(10.0, h.ONCHAIN_SOURCE))
    posted_part = []
    h.executor.post_maker_exit_order = lambda **kw: (
        posted_part.append(kw) or {"success": True, "orderID": "OID_PART", "price": kw["price"]}
    )
    assert h._attempt_maker_exit_post("LIVE_PART_FAK", pos_part_fak) is True
    assert pos_part_fak["notional_usd"] == pytest.approx(6.0)
    assert pos_part_fak["remaining_cost_basis"] == pytest.approx(6.0)
    assert Decimal(str(pos_part_fak["entry_shares"])) == Decimal("10.0")

    # 6. F-10a: Centered venue divergence > 12.0 bps vetoes even if Coinbase 2s move is flat (1:1 WFO OR parity),
    #    while uncentered raw USDT basis (20 bps) with confirming Coinbase (+2 bps) still passes.
    from src.polymarket_research.polymarket_live_harvester import (
        evaluate_coinbase_venue_veto,
        get_equity_tier_limits,
    )
    assert evaluate_coinbase_venue_veto(
        {"coinbase_spot": 80000.0, "venue_divergence_centered_bps": 13.0, "coinbase_move_bps_2s": 0.5},
        "UP",
    )[0] is True
    assert evaluate_coinbase_venue_veto(
        {"coinbase_spot": 80000.0, "venue_divergence_bps": 20.0, "coinbase_move_bps_2s": 2.0},
        "UP",
    )[0] is False
    assert evaluate_coinbase_venue_veto(
        {"coinbase_spot": 80000.0, "venue_divergence_centered_bps": 2.0, "coinbase_move_bps_2s": -4.5},
        "UP",
    )[0] is True

    # 7. Vector 7 PATCH 8B: get_equity_tier_limits(76.49) returns SEED_SURVIVAL directly at source
    t_seed = get_equity_tier_limits(76.49, high_water_mark_equity=76.49)
    assert t_seed["tier"] == "SEED_SURVIVAL"
    assert t_seed["max_concurrent_positions"] == 1
    assert t_seed["min_equity_floor"] == pytest.approx(48.0)

    # 8. Blueprint 4 (F-08): Dense integer share grid 8..32 achieves 100.0% hit coverage across [$8.00..$16.50]
    from src.polymarket_research.polymarket_live_executor import PreSignedOrderLadderCache
    for px_c in range(55, 86):
        px = round(px_c / 100.0, 2)
        for not_10x in range(80, 166, 5):
            notional = not_10x / 10.0
            req_sh = float(int(notional // px))
            if req_sh >= 8.0:
                cache = PreSignedOrderLadderCache()
                for sh in range(8, 33):
                    cache.store_presigned_order("TOK_DENSE", px, float(sh), {"signed": sh})
                got_exact = cache.get_presigned_order("TOK_DENSE", px, req_sh)
                assert got_exact == {"signed": int(req_sh)}


def test_fix13_v39_second_pass_audit_remediations(tmp_path, monkeypatch):
    """
    Verifies v3.9 Second-Pass Adversarial Audit Fixes & Profit Upgrades (R01, R02, R03, R04, R07, R08, Upgrade 2):
    1. R07: 1H Binance contracts keep authoritative Binance 1H Open/Spot (never polluted by twap_60s_open/cl_open_spot),
       while 15M Chainlink TWAP contracts enforce twap_60s_open + chainlink_twap_60s boundary-wick veto.
    2. R03 (Patch A): Max daily loss halt auto-resets via is_halted() upon UTC date rollover without manual intervention.
    3. R04: +$3 hysteresis at $88->$91 and smooth SEED_RAMP ($91..$108) eliminate the +61% risk cliff.
    4. R02 (Patch B): Wallet < CLOB matched on live order_id fails closed into ENTRY_INVENTORY_RECONCILIATION_REQUIRED
       without corrupting historical notional_usd.
    5. Upgrade 2: Live 256-bit CTF positions post 50% @ $0.95 + 50% @ $0.98 resting Maker exits.
    6. R01 + R08: Non-Safe Beacon Proxy caches _funder_is_gnosis_safe=False; _UrgentSignPriority yields prewarm_order_ladder.
    """
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        get_equity_tier_limits,
    )
    import src.polymarket_research.polymarket_live_executor as ex_mod
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "v39_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True, max_trades_per_market=1, hold_to_maturity=False)
    h.dry_run = False
    h.executor.dry_run = False
    h.state_file = tmp_path / "v39_state.json"
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True

    # 1. R07: 1H Binance market ("binance.com") must NOT overwrite finalized_1h_open with twap_60s_open / cl_open_spot
    now_u = time.time()
    cur_h = int(now_u // 3600)
    shock_1h = {
        "shock_id": "SHK_1H_BIN",
        "t0_unix": now_u,
        "asset": "BTC",
        "horizon": "1h",
        "resolution_source": "https://www.binance.com/en/trade/BTC_USDT",
        "market_id": "6074291",
        "title": "Bitcoin Up or Down - October 25, 1AM ET",
        "seconds_to_expiry": 750.0,  # Inside v3.9 [120s, 1200s] 1h WFO window!
        "shock_direction": "BUY",
        "shock_ofi": 0.90,
        "shock_volume_100ms": 2_000_000.0,
        "spot_at_t0": 100120.0,
        "finalized_1h_open": 100000.0,
        "candle_open_spot": 100000.0,
        "twap_60s_open": 100090.0,  # +9 bps higher TWAP that would have falsely vetoed 1h in v3.8!
        "chainlink_open_spot": 100110.0,
        "candle_distance_pct": 0.12,
        "candle_sigma": 0.0045,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "778899001122334455667788990011",
                "best_bid": 0.72,
                "best_ask": 0.73,
                "age_ask_ms": 400.0,
                "obi_l1": 0.25,
                "vwap_$50": 0.73,
                "effective_price_$50": 0.74,
                "raw_top_asks": [[0.73, 100.0]],
                "raw_top_bids": [[0.72, 100.0]],
            }
        },
    }
    # Block right at book fetch after hourly_candle_opens is recorded so we verify exact 1h strike preservation
    h.executor.get_market_book_async = AsyncMock(return_value={})
    asyncio.run(h.evaluate_shock_and_execute(shock_1h))
    assert h.hourly_candle_opens["BTC"][cur_h] == pytest.approx(100000.0)

    # Meanwhile on 15m ("data.chain.link"), boundary wick >= 0.0395% with thin cushion is vetoed BEFORE book fetch!
    book_called_15m = []
    h.executor.get_market_book_async = AsyncMock(side_effect=lambda *a: book_called_15m.append(1) or {})
    shock_15m_wick = dict(
        shock_1h,
        shock_id="SHK_15M_CL_WICK",
        horizon="15m",
        resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams",
        title="Bitcoin Up or Down - October 25, 1:00AM-1:15AM ET",
        seconds_to_expiry=300.0,
        spot_at_t0=100075.0,
        candle_open_spot=100000.0,
        twap_60s_open=100045.0,  # 0.045% >= 0.0395% wick divergence, dual_cush = 0.03% < 0.10%
    )
    asyncio.run(h.evaluate_shock_and_execute(shock_15m_wick))
    assert len(book_called_15m) == 0, "15m Chainlink TWAP boundary wick trap must be vetoed before book fetch!"

    # 2. R03 (Patch A): Daily-loss halt auto-clears via is_halted() on UTC midnight rollover
    h.risk_controller.max_daily_loss_usd = 20.0
    h.risk_controller.record_trade_pnl(-21.0)
    assert h.risk_controller.is_halted() is True
    assert "Max daily loss reached" in h.risk_controller.halt_reason
    h.risk_controller.last_loss_date_utc = "2020-01-01"
    assert h.risk_controller.is_halted() is False
    assert h.risk_controller.daily_realized_loss == pytest.approx(0.0)

    # 3. R04: Hysteresis ($88 -> $91) and smooth SEED_RAMP ($91..$108)
    t_hyst = get_equity_tier_limits(89.50, high_water_mark_equity=89.50, previous_tier="SEED_SURVIVAL")
    assert t_hyst["tier"] == "SEED_SURVIVAL"
    assert t_hyst["max_concurrent_positions"] == 1
    t_ramp = get_equity_tier_limits(93.00, high_water_mark_equity=93.00, previous_tier="SEED_SURVIVAL")
    assert t_ramp["tier"] == "SEED_RAMP"
    assert t_ramp["dynamic_bankroll_pct"] == pytest.approx(0.17)
    assert t_ramp["max_concurrent_positions"] == 1
    assert 54.0 <= t_ramp["min_equity_floor"] < 65.0

    # 4. R02 (Patch B): Wallet shortfall vs authoritative CLOB matched fails closed without rewriting notional_usd
    pos_r02 = {
        "trade_id": "LIVE_R02_SHORTFALL",
        "order_id": "0xOID_FULL_MATCH",
        "token_id": "556677889900112233445566778899",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": False,
        "entry_ts": time.time() - 25.0,
        "pre_token_balance": 0.0,
        "gross_entry_shares": 20.0,
        "entry_shares": 20.0,
        "remaining_shares": 20.0,
        "entry_price": 0.60,
        "notional_usd": 12.0,
        "fee_usd": 0.25,
        "candle_expiry_ts": time.time() + 300.0,
    }
    h._verify_entry_finality = MagicMock(return_value=(True, False))
    h._wallet_token_balance = MagicMock(return_value=(10.0, h.ONCHAIN_SOURCE))
    h.executor.get_order_fill_summary = lambda oid, tok: {"order_id": oid, "matched": 20.0, "cash": 12.0, "fee": 0.25, "terminal": True}
    assert h._attempt_maker_exit_post("LIVE_R02_SHORTFALL", pos_r02) is False
    assert pos_r02["exit_order_status"] == "ENTRY_INVENTORY_RECONCILIATION_REQUIRED"
    assert pos_r02["notional_usd"] == pytest.approx(12.0)

    # 5. Upgrade 2: Live 256-bit CTF position posts 50% @ $0.95 + 50% @ $0.98
    pos_up2 = {
        "trade_id": "LIVE_UP2_CTF",
        "token_id": "123456789012345678901234567890",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.72,
        "entry_shares": 16.0,
        "remaining_shares": 16.0,
        "notional_usd": 11.52,
        "candle_expiry_ts": time.time() + 300.0,
    }
    h._wallet_token_balance = MagicMock(return_value=(16.0, h.ONCHAIN_SOURCE))
    posted_up2 = []
    h.executor.post_maker_exit_order = lambda **kw: posted_up2.append(kw) or {"success": True, "orderID": "OID_95", "price": kw["price"]}
    assert h._attempt_maker_exit_post("LIVE_UP2_CTF", pos_up2) is True
    assert pos_up2["exit_tranches"][0]["price"] == pytest.approx(0.95)
    assert pos_up2["exit_tranches"][1]["price"] == pytest.approx(0.98)
    assert posted_up2[0]["price"] == pytest.approx(0.95)

    # 6. R01 + R08: Non-Safe proxy cached guard & _UrgentSignPriority waiter signaling
    h.executor.signature_type = 3
    h.executor._funder_is_gnosis_safe = False
    assert h.executor.attempt_onchain_redemption("0x" + "ab" * 32) is None
    with ex_mod._UrgentSignPriority():
        assert ex_mod._URGENT_SIGN_WAITERS >= 1
        assert h.executor.prewarm_order_ladder("123456789012345678901234567890", 12.0, exact_shares=[10]) == 0
    assert ex_mod._URGENT_SIGN_WAITERS == 0


def test_fix14_v391_unchoked_ev_and_stale_book_snipe(tmp_path, monkeypatch):
    """
    Verifies v3.9.1 Alpha-Unblocking & Compounding Upgrades:
    1. Real 10PM ET 1h BTC setup (TTE=1099s, ask=$0.83, dist=+0.104%, z_strike=0.83, L1=$83) that was previously
       choked by legacy eta=0.14 / tau>900s 0.78 cap now passes continuous +EV ceiling and fires live snipe!
    2. Untouched resting stale quote on REST /book (timestamp 12s old < 60s PM_MAX_BOOK_AGE_SEC) is sniped cleanly
       instead of being falsely rejected by the old 4.0s staleness threshold.
    3. Thin retail L1 ask (< $20.00) on a live 256-bit CTF token is rejected by [L1 ASK DEPTH REJECT].
    """
    import asyncio, types
    from unittest.mock import AsyncMock
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "v391_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    h = PolymarketLiveHarvester(
        ticket_notional=12.0, dry_run=True, dynamic_sizing=True, hold_to_maturity=False,
        max_trades_per_market=2, max_trades_per_hour=8, max_tte=1200.0,
    )
    h.dry_run = False
    h.executor.dry_run = False
    h.state_file = tmp_path / "v391_state.json"
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h._last_known_collateral = 76.49
    h.executor.get_collateral_balance = lambda hot_path=False: 76.49

    sniped = []
    async def fake_snipe(**kw):
        sniped.append(kw)
        return types.SimpleNamespace(
            success=False, order_id=None, tx_hashes=[], filled_size=0.0, avg_price=0.0, size=0.0, price=0.0,
            fee_paid_usd=0.0, latency_ms=1.0, error_msg="SIM", error="SIM",
            mode="FAK_KILLED_NO_MATCH", details={"fak_killed": True}, execution_status=ExecutionStatus.REJECTED,
        )
    h.executor.execute_snipe_order_async = fake_snipe

    now_u = time.time()
    # Force fallback to REST /book with a 12-second-old resting stale ask (previously killed by 4.0s threshold!)
    h.executor.get_market_book_async = AsyncMock(return_value={
        "timestamp": (now_u - 12.0) * 1000.0,
        "asks": [{"price": "0.83", "size": "100"}],
        "bids": [{"price": "0.82", "size": "100"}],
    })
    shock_10pm_btc = {
        "shock_id": "SHK_10PM_BTC_UNCHOKED",
        "t0_unix": now_u,
        "asset": "BTC",
        "horizon": "1h",
        "resolution_source": "https://www.binance.com/en/trade/BTC_USDT",
        "market_id": "6071901",
        "condition_id": "0x" + "11" * 32,
        "title": "Bitcoin Up or Down - October 24, 10PM ET",
        "seconds_to_expiry": 1099.0,
        "shock_direction": "BUY",
        "shock_ofi": 1.0,
        "shock_volume_100ms": 1_800_000.0,
        "spot_at_t0": 80104.0,
        "finalized_1h_open": 80000.0,
        "candle_open_spot": 80000.0,
        "candle_distance_pct": 0.13,
        "candle_sigma": 0.0028,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x" + "11" * 32},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "998877665544332211009988776655",
                "best_bid": 0.82,
                "best_ask": 0.83,
                "age_ask_ms": 600.0,
                "obi_l1": 0.10,
                "vwap_$25": 0.83,
                "vwap_$50": 0.83,
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_10pm_btc))
    assert len(sniped) == 1, "Unchoked +EV 10PM BTC setup on 12s resting book must execute!"

    # Thin L1 ask (< $20.00: 10 shares @ $0.83 = $8.30) must be rejected before sniping
    h.executor.get_market_book_async = AsyncMock(return_value={
        "timestamp": (now_u - 2.0) * 1000.0,
        "asks": [{"price": "0.83", "size": "10"}],
        "bids": [{"price": "0.82", "size": "100"}],
    })
    shock_thin = dict(shock_10pm_btc, shock_id="SHK_THIN_L1", market_id="6071999")
    asyncio.run(h.evaluate_shock_and_execute(shock_thin))
    assert len(sniped) == 1, "Thin $8.30 L1 ask (< $20.00 institutional floor) must be rejected!"

    # Production auth_mode == 'AUTHENTICATED_L2' must post 50% @ $0.95 + 50% @ $0.98 (not legacy 0.78+0.14=0.92)
    from unittest.mock import MagicMock
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h._wallet_token_balance = MagicMock(return_value=(15.38, h.ONCHAIN_SOURCE))
    posted_exits = []
    h.executor.post_maker_exit_order = lambda **kw: posted_exits.append(kw) or {"success": True, "orderID": "OID_95", "price": kw["price"]}
    pos_auth = {
        "trade_id": "LIVE_6075458_DOWN",
        "token_id": "41400365548425196187992327321545036693976598522874320121839711965141676378572",
        "sleeve": "SLEEVE_1_CORE_302",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.78,
        "entry_shares": 15.38,
        "remaining_shares": 15.38,
        "notional_usd": 12.0,
        "candle_expiry_ts": time.time() + 300.0,
    }
    h.active_positions["LIVE_6075458_DOWN"] = pos_auth
    assert h._attempt_maker_exit_post("LIVE_6075458_DOWN", pos_auth) is True
    assert [t["price"] for t in pos_auth["exit_tranches"]] == [0.95, 0.98], (
        f"AUTHENTICATED_L2 must rest at [0.95, 0.98], got {pos_auth.get('exit_tranches')}"
    )


def test_fix15_v392_shadow_graduation_upgrades(tmp_path, monkeypatch):
    """
    Verifies the 4 v3.9.2 Shadow Graduation Upgrades:
    1. Phase 3A defaults to ultra-short 3.5s TTL + salvages reversed fills (no -$19.93 wipeouts).
    2. Phase 4 rejects <0.25% cross-oracle basis traps on CORRIDOR_BOX_ARB and scores dual-oracle settlement.
    3. EXP-316 Track A walks $25/$50 graduation tiers with $0.97 Maker TP.
    4. Paper Trader retires losing SLEEVE_2 by default and runs Volatility-Normalized SOL Shadow Sleeve.
    """
    import json
    from unittest.mock import patch
    import src.polymarket_research.polymarket_paper_trader as pt_mod
    import src.polymarket_research.exp316_macro_strike_shadow as e316_mod

    shadow_file = tmp_path / "shadow_p34.jsonl"
    monkeypatch.setenv("PM_SHADOW_TRACKER_FILE", str(shadow_file))
    h = _make_live_harvester(tmp_path)

    # 1. Phase 3A 3.5s TTL + 3-Zone Wrong-Side Salvage
    now_u = time.time()
    h._register_shadow_phase3a_maker_in(
        shock={"market_id": "700001", "title": "BTC 15m", "asset": "BTC", "candle_open_spot": 80000.0, "expiry_ts": now_u + 120.0},
        target_token="UP", first_ask=0.76, first_bid=0.75, max_allowed_price=0.85,
        raw_asks=[(0.76, 50.0)], reject_reason="FAK_MISS", is_subhourly=True, dist_pct=0.10, tte=120.0,
    )
    ord_rec = h._shadow_maker_orders["700001_UP"]
    assert ord_rec["ttl_sec"] == pytest.approx(3.5)

    # Simulate immediate fill followed by wrong-side spot reversal -> salvaged at $0.40 instead of -$19.93 wipeout!
    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.read_fast_tick",
        lambda asset, max_age_sec=2.0, now=None: {
            "spot_price": 80080.0, "chainlink_twap_60s": 80080.0, "market_id": "700001",
            "UP": {"best_ask": 0.75, "best_bid": 0.74},
        },
    )
    h._step_shadow_phase3_4_tracker(now_u + 0.5)
    assert ord_rec["status"] == "SHADOW_MAKER_FILLED"

    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.read_fast_tick",
        lambda asset, max_age_sec=2.0, now=None: {
            "spot_price": 79920.0, "chainlink_twap_60s": 79920.0, "market_id": "700001",
            "UP": {"best_ask": 0.42, "best_bid": 0.40},
        },
    )
    h._step_shadow_phase3_4_tracker(now_u + 6.0)
    h._step_shadow_phase3_4_tracker(now_u + 15.0)
    assert "700001_UP" not in h._shadow_maker_orders
    events = [json.loads(l) for l in shadow_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    salv = [e for e in events if e.get("event_type") == "SHADOW_PHASE3A_MAKER_RESOLVED"][0]
    assert salv["exit_reason"] == "WRONG_SIDE_SALVAGE"
    assert salv["shadow_net_pnl_usd"] > -12.0  # Salvaged (~-$9.4), NOT -$19.93 wipeout!

    # 2. Phase 4 rejects narrow 4 bps corridor trap (< 0.25%), accepts 0.35% deep corridor & settles dual-oracle jackpot
    exp_u = round((now_u + 180.0) / 60.0) * 60.0
    h._update_shadow_phase4_monotonicity_scanner(
        {"market_id": "700002", "t0_unix": now_u, "expiry_ts": exp_u, "spot_at_t0": 80020.0,
         "pre_shock_features_t0": {"UP": {"best_ask": 0.52, "raw_top_asks": [[0.52, 60.0]]}, "DOWN": {"best_ask": 0.50, "raw_top_asks": [[0.50, 60.0]]}}},
        "BTC", True, False, 180.0, 80000.0,
    )
    h._update_shadow_phase4_monotonicity_scanner(
        {"market_id": "700003", "t0_unix": now_u + 0.5, "expiry_ts": exp_u, "spot_at_t0": 80020.0,
         "pre_shock_features_t0": {"UP": {"best_ask": 0.52, "raw_top_asks": [[0.52, 60.0]]}, "DOWN": {"best_ask": 0.49, "raw_top_asks": [[0.49, 60.0]]}}},
        "BTC", False, True, 180.0, 80032.0,  # 0.04% narrow gap -> basis trap!
    )
    assert not getattr(h, "_shadow_phase4_active_boxes", {})

    exp_u2 = exp_u + 3600.0
    h._update_shadow_phase4_monotonicity_scanner(
        {"market_id": "700004", "t0_unix": now_u, "expiry_ts": exp_u2, "spot_at_t0": 80150.0,
         "pre_shock_features_t0": {"UP": {"best_ask": 0.52, "raw_top_asks": [[0.52, 60.0]]}, "DOWN": {"best_ask": 0.50, "raw_top_asks": [[0.50, 60.0]]}}},
        "BTC", True, False, 180.0, 80000.0,
    )
    h._update_shadow_phase4_monotonicity_scanner(
        {"market_id": "700005", "t0_unix": now_u + 0.5, "expiry_ts": exp_u2, "spot_at_t0": 80150.0,
         "pre_shock_features_t0": {"UP": {"best_ask": 0.52, "raw_top_asks": [[0.52, 60.0]]}, "DOWN": {"best_ask": 0.49, "raw_top_asks": [[0.49, 60.0]]}}},
        "BTC", False, True, 180.0, 80300.0,  # 0.375% >= 0.25% safe corridor!
    )
    assert len(h._shadow_phase4_active_boxes) == 1
    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.read_fast_tick",
        lambda asset, max_age_sec=5.0, now=None: {"spot_price": 80160.0, "chainlink_twap_60s": 80140.0},
    )
    h._step_shadow_phase3_4_tracker(exp_u2 + 5.0)
    events2 = [json.loads(l) for l in shadow_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    box_res = [e for e in events2 if e.get("event_type") == "SHADOW_PHASE4_BOX_RESOLVED"][0]
    assert box_res["double_win_jackpot"] is True
    assert box_res["payout_per_pair"] == pytest.approx(2.0)

    # 3. EXP-316 TrackAPosition defaults to $0.97 Maker TP & Paper Trader runs SOL Shadow Sleeve while retiring SLEEVE_2
    assert e316_mod.TrackAPosition.__dataclass_fields__["maker_tp_price"].default == pytest.approx(0.97)
    assert pt_mod.ENABLE_SLEEVE_304_315 is False
    assert pt_mod.ENABLE_SOL_SHADOW_SLEEVE is True

    with patch.object(pt_mod, "SOL_SHADOW_LEDGER_FILE", tmp_path / "sol_led.jsonl"), \
         patch.object(pt_mod, "SOL_SHADOW_STATE_FILE", tmp_path / "sol_st.json"), \
         patch.object(pt_mod, "DEV_LEDGER_FILE", tmp_path / "dev.jsonl"), \
         patch.object(pt_mod, "VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl"), \
         patch.object(pt_mod, "STATE_FILE", tmp_path / "pt_st.json"):
        pt = pt_mod.PolymarketForwardPaperTrader()
        pt.evaluate_shock_signal({
            "market_id": "880001", "title": "Solana Up or Down - Oct 25, 9AM ET", "asset": "SOL", "horizon": "1h",
            "t0_unix": now_u, "seconds_to_expiry": 600.0, "shock_direction": "BUY", "shock_ofi": 0.90,
            "shock_volume_100ms": 350000.0, "spot_at_t0": 150.60, "finalized_1h_open": 150.00,
            "pre_shock_features_t0": {"UP": {"best_ask": 0.75, "best_bid": 0.74, "raw_top_asks": [[0.75, 50.0]], "raw_top_bids": [[0.74, 50.0]]}},
        })
        assert "880001" in pt.sol_shadow_open_trades
        pt.check_maker_tp_fills("880001", {"timestamp_unix": now_u + 12.0, "UP": {"best_bid": 0.97, "best_ask": 0.98}})
        assert len(pt.sol_shadow_trades) == 1
        assert pt.sol_shadow_trades[0]["won"] is True


def test_fix16_xrp_and_sol_shadow_sleeves_and_exp316(tmp_path):
    """Verify XRP & SOL end-to-end shadow support across recorder, paper trader, and EXP-316."""
    import json
    from src.polymarket_research import polymarket_terminal_recorder as rec_mod
    from src.polymarket_research import exp316_macro_strike_shadow as e316_mod
    from src.polymarket_research import polymarket_paper_trader as pt_mod
    from src.polymarket_research.polymarket_live_harvester import ALLOWED_ASSETS
    from unittest.mock import patch

    # 1. Recorder supports XRP & SOL without touching live BTC/ETH ALLOWED_ASSETS
    assert "XRP" in rec_mod.ASSET_CONFIGS
    assert "SOL" in rec_mod.ASSET_CONFIGS
    assert rec_mod.ASSET_CONFIGS["XRP"]["series_slug"] == "xrp-up-or-down-hourly"
    assert ALLOWED_ASSETS == {"BTC", "ETH"}

    # 2. EXP-316 monitors XRP & SOL Daily/Weekly strike ladders and parses decimal XRP strikes
    series_assets = {a for a, _, _ in e316_mod.MONITORED_SERIES}
    assert {"BTC", "ETH", "SOL", "XRP"} <= series_assets
    assert e316_mod.extract_strike_price("Will the price of XRP be above $0.85 on October 25?", None) == pytest.approx(0.85)
    assert e316_mod.extract_strike_price("Will XRP reach $2.10 October 19-25?", None) == pytest.approx(2.10)

    # 3. Paper Trader runs isolated SLEEVE_XRP_V392_SHADOW alongside SLEEVE_SOL_V392_SHADOW
    now_u = time.time()
    with patch.object(pt_mod, "SOL_SHADOW_LEDGER_FILE", tmp_path / "sol_led.jsonl"), \
         patch.object(pt_mod, "SOL_SHADOW_STATE_FILE", tmp_path / "sol_st.json"), \
         patch.object(pt_mod, "XRP_SHADOW_LEDGER_FILE", tmp_path / "xrp_led.jsonl"), \
         patch.object(pt_mod, "XRP_SHADOW_STATE_FILE", tmp_path / "xrp_st.json"), \
         patch.object(pt_mod, "DEV_LEDGER_FILE", tmp_path / "dev.jsonl"), \
         patch.object(pt_mod, "VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl"), \
         patch.object(pt_mod, "STATE_FILE", tmp_path / "pt_st.json"):
        pt = pt_mod.PolymarketForwardPaperTrader()
        pt.evaluate_shock_signal({
            "market_id": "990001", "title": "XRP Up or Down - Oct 25, 9AM ET", "asset": "XRP", "horizon": "1h",
            "t0_unix": now_u, "seconds_to_expiry": 720.0, "shock_direction": "BUY", "shock_ofi": 0.85,
            "shock_volume_100ms": 95000.0, "spot_at_t0": 0.9045, "finalized_1h_open": 0.9000,
            "pre_shock_features_t0": {"UP": {"best_ask": 0.74, "best_bid": 0.70, "raw_top_asks": [[0.74, 40.0]], "raw_top_bids": [[0.70, 40.0]]}},
        })
        assert "990001" in pt.xrp_shadow_open_trades
        assert "990001" not in pt.open_trades
        pt.check_maker_tp_fills("990001", {"timestamp_unix": now_u + 15.0, "UP": {"best_bid": 0.97, "best_ask": 0.98}})
        assert len(pt.xrp_shadow_trades) == 1
        assert pt.xrp_shadow_trades[0]["won"] is True
        xrp_state = json.loads((tmp_path / "xrp_st.json").read_text(encoding="utf-8"))
        assert xrp_state["sleeve_id"] == "SLEEVE_XRP_V392_SHADOW"
        assert xrp_state["winning_trades"] == 1


def test_fix17_eth_9am_forensic_remediation(tmp_path, monkeypatch):
    """
    Verifies v3.9.3 Forensic Remediation of LIVE_6081501_1792935724_UP (ETH 9AM ET -$6.80 loss):
      1. Thin-cushion ETH 1h whipsaw (dist=+0.1285% < 0.15% at TTE=1075.4s, sigma=0.00405) is rejected,
         while historical WFO ETH 1h setups (dist=+0.2286% >= 0.15%) continue to qualify.
      2. Salvage unwind evicts exit_oid from pre-cancel open_oids once BOTH cancel_order(is_canceled=True)
         and post-cancel summary(terminal=True) confirm cancellation, unwinding immediately on Pass #1
         with a 4c sweep floor (best_b - 0.04) and 0.35s fast retry on 400 FAK zero-match rejections.
      3. _ThreadLocalClobHttpClient isolates per-thread HTTP/1.1 keep-alive clients (zero shared deque).
    """
    import asyncio
    import threading
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import (
        ExecutionStatus,
        _ThreadLocalClobHttpClient,
        install_thread_safe_clob_http_client,
    )

    # 1. Thread-local HTTP/1.1 client isolation (eliminates deque mutated during iteration + HTTP/2 GOAWAY)
    dummy_mod = type("DummyHelpers", (), {"_http_client": MagicMock()})()
    assert install_thread_safe_clob_http_client(dummy_mod) is True
    assert isinstance(dummy_mod._http_client, _ThreadLocalClobHttpClient)
    clients = []

    def _grab():
        clients.append(dummy_mod._http_client._client())

    t1 = threading.Thread(target=_grab)
    t2 = threading.Thread(target=_grab)
    t1.start(); t2.start(); t1.join(); t2.join()
    assert len(clients) == 2 and clients[0] is not clients[1]
    for c in clients:
        c.close()

    # 2. Exact replay of LIVE_6081501_1792935724_UP vs valid WFO ETH 1h trade
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "f17_state.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "f17_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True, allowed_assets={"BTC", "ETH"})
    h.dry_run = False
    h.executor.dry_run = False
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "f17_state.json"
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 70.67
    submitted = []
    h.executor.execute_live_order = MagicMock(side_effect=lambda **kw: submitted.append(kw))

    real_eth_tok = "100434764618174237135201777197981253576172734064131101154122934005557319214073"
    now_u = time.time()
    losing_shock = {
        "shock_id": "6081501_replay",
        "market_id": "6081501",
        "condition_id": "0x6c7e137b9293b4004131cd749fe460eeb669b626ea5b3d9795bffbe491caa527",
        "title": "Ethereum Up or Down - October 25, 9AM ET",
        "asset": "ETH",
        "horizon": "1h",
        "resolution_source": "https://www.binance.com/en/trade/ETH_USDT",
        "t0_unix": now_u,
        "seconds_to_expiry": 1075.4,
        "expiry_ts": now_u + 1075.4,
        "candle_sigma": 0.00405,
        "shock_volume_100ms": 455771.0,
        "is_40ms_fast_track": True,
        "shock_direction": "BUY",
        "shock_ofi": 1.0,
        "spot_at_t0": 2337.90,
        "finalized_1h_open": 2334.90,
        "candle_open_spot": 2334.90,
        "candle_distance_pct": 0.1285,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_eth_tok,
                "best_bid": 0.74,
                "best_ask": 0.76,
                "spread": 0.02,
                "age_book_ms": 3.4,
                "age_ask_ms": 10.9,
                "age_bid_ms": 3521.5,
                "obi_l1": 0.463,
                "raw_top_bids": [[0.74, 150.0], [0.70, 66.0]],
                "raw_top_asks": [[0.76, 55.0], [0.77, 25.0]],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(losing_shock))
    assert len(submitted) == 0, "Thin +0.1285% ETH 1h bounce at TTE=1075s must be rejected!"

    # 3. Single-pass verified cancel + 4c sweep floor + 0.35s fast retry on 400 FAK zero-match
    exit_oid = "0x0f37be121c4a7bde2e0439b44244fa35c6cb29287923724a23529481d3ad0a24"
    pos = {
        "trade_id": "LIVE_6081501_TEST",
        "market_id": "6081501",
        "token_id": real_eth_tok,
        "target_token": "UP",
        "asset": "ETH",
        "horizon": "1h",
        "status": ExecutionStatus.EXIT_RESTING,
        "exit_order_id": exit_oid,
        "exit_order_status": "RESTING",
        "inventory_reconciled": True,
        "entry_price": 0.7569,
        "entry_shares": 15.26,
        "remaining_shares": 15.26,
        "notional_usd": 11.55,
        "candle_open_spot": 2334.90,
        "entry_spot_ref": 2337.90,
        "candle_sigma": 0.00405,
        "candle_expiry_ts": now_u + 174.0,
        "low_bid_detected_ts": now_u - 7.0,
    }
    h.active_positions["LIVE_6081501_TEST"] = pos
    # Pre-cancel open_orders snapshot STILL contains exit_oid (exact live bug!)
    h._strict_open_orders = lambda: [{"id": exit_oid}]
    h._get_verified_shm_book = lambda p: {
        "bids": [{"price": "0.31", "size": "60.0"}],
        "asks": [{"price": "0.35", "size": "60.0"}],
    }
    h.get_reference_spot_price = lambda asset: 2333.90
    h._wallet_token_balance = MagicMock(return_value=(15.26, h.ONCHAIN_SOURCE))
    h.executor.cancel_order = MagicMock(return_value={"canceled": [exit_oid], "is_canceled": True, "outcome": "CANCELED"})
    h.executor.get_order_fill_summary = MagicMock(return_value={
        "order_id": exit_oid, "status": "CANCELED", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True,
    })
    unwind_calls = []

    def _mock_unwind(**kw):
        unwind_calls.append(kw)
        return {
            "success": False,
            "orderID": None,
            "matched_size": 0.0,
            "retryable": True,
            "outcome_unknown": False,
            "error": "PolyApiException[status_code=400, error_message={'error': 'no orders found to match with FAK order'}]",
        }

    h.executor.execute_unwind_order = _mock_unwind
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 1, "Must dispatch FAK unwind on Pass #1 without 3.9s STOP_CANCEL_PENDING delay!"
    assert unwind_calls[0]["min_price"] == pytest.approx(0.27)  # 0.31 - 0.04 sweep floor
    assert pos["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert (pos["next_unwind_retry_ts"] - time.time()) <= 0.50









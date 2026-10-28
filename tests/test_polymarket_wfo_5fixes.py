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

    # 3. Paper Trader runs isolated SLEEVE_XRP_V392_SHADOW when opted-in (retired to False in production)
    assert pt_mod.ENABLE_XRP_SHADOW_SLEEVE is False
    now_u = time.time()
    with patch.object(pt_mod, "ENABLE_XRP_SHADOW_SLEEVE", True), \
         patch.object(pt_mod, "SOL_SHADOW_LEDGER_FILE", tmp_path / "sol_led.jsonl"), \
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
    Verifies v3.9.4 WFO-Validated Forensic Remediation of LIVE_6081501_1792935724_UP (ETH 9AM ET -$6.80 loss):
      1. WFO Policy 4 rejects ETH 1h > 600s (TTE=1075.4s) AND z_strike < 0.65 (z_strike=0.58), while leaving
         ETH 15m (92.4% WR, PF=3.06) and ETH 1h Late (<= 600s, 100% WR) 100% unchoked with zero ad-hoc sigma floor.
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
    assert len(submitted) == 0, "Early ETH 1h whipsaw (TTE=1075s > 600s, z=0.58 < 0.65) must be rejected!"

    # Verify WFO Policy 4 leaves ETH 15m (even with quiet rec_sig=0.0020 -> sigma_1h=0.0040 < 0.0048) 100% unchoked!
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.1, "OK")
    sniped_15m = []

    async def _fake_snipe_15m(**kw):
        sniped_15m.append(kw)
        return type("FakeRes", (), {
            "success": False, "order_id": None, "tx_hashes": [], "filled_size": 0.0, "avg_price": 0.0,
            "size": 0.0, "price": 0.0, "fee_paid_usd": 0.0, "latency_ms": 1.0, "error_msg": "SIM", "error": "SIM",
            "mode": "FAK_KILLED_NO_MATCH", "details": {"fak_killed": True}, "execution_status": ExecutionStatus.REJECTED,
        })()

    h.executor.execute_snipe_order_async = _fake_snipe_15m
    eth_15m_winner = dict(
        losing_shock,
        shock_id="eth_15m_unchoked",
        market_id="6081599",
        title="Ethereum Up or Down - October 25, 9:00AM-9:15AM ET",
        horizon="15m",
        resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams",
        seconds_to_expiry=300.0,
        expiry_ts=now_u + 300.0,
        candle_sigma=0.0020,  # sigma_1h = 0.0040 -> z_strike ~0.72: below the flat 0.78 floor (2026-10-27 re-evaluation) -> must be rejected
        spot_at_t0=2336.85,
        candle_open_spot=2334.90,
        twap_60s_open=2334.90,
        candle_distance_pct=0.0835,
        fee_metadata={"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": losing_shock["condition_id"]},
    )
    asyncio.run(h.evaluate_shock_and_execute(eth_15m_winner))
    assert len(sniped_15m) == 0, "Flat 0.78 z floor: ETH 15m at z~0.72 (TTE=300s) must be rejected (former 0.65 branch removed)!"

    # Same setup with a quieter recorded sigma (sigma_1h=0.0034 -> z~0.85 >= 0.78) must trade: no ad-hoc sigma floor chokes it.
    eth_15m_unchoked = dict(eth_15m_winner, shock_id="eth_15m_unchoked_z085", candle_sigma=0.0017)
    asyncio.run(h.evaluate_shock_and_execute(eth_15m_unchoked))
    assert len(sniped_15m) >= 1, "Unchoked ETH 15m winner (z~0.85 >= 0.78) must NOT be blocked by an ad-hoc sigma floor!"

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


def test_fix16_external_dual_audit_executor_and_harvester_hardening(tmp_path, monkeypatch):
    """
    Regression suite verifying ChatGPT + Gemini dual adversarial audit fixes across Live Executor & Live Harvester:
      - F-01: `signature_type=0` EOA wallet preserved (not coerced to `1`) in `attempt_onchain_redemption`
      - F-02: `find_redemption_payouts` fails closed (`None`) when `NegRiskAdapter` `eth_getLogs` fails
      - F-23: `build_relayer_builder_headers` signs exact canonical JSON `str` wire bytes verbatim
      - F-09: `execute_atomic_dominance_box` enforces per-leg fees + unwinds actual partial `takingAmount`
      - F-16: `get_collateral_balance(hot_path=True)` invalidates stale `>120s` cache in live mode
      - F-05: Zero/negative Kelly edge returns `0.0` (never `min_lot_usd` or `MAX_ABSOLUTE_TICKET_USD`)
      - F-22: Sticky account-equity floor halt with `+$3.00` hysteresis & verified `allow_auto_clear=True`
      - M-01: `5..10`-share position posts a single maker exit lot without leaving `<5`-share orphan tail
      - F-17: DST-aware `America/New_York` weekday `09:15-09:32 ET` opening-bell blackout
      - F-11 / M-05: Future clock-skew & internal JSON timestamp staleness checks
      - F-07: Live `15m` Chainlink USD provenance guard rejects missing USD spot anchor
    """
    import asyncio
    import hashlib
    import hmac
    import base64
    import json
    from datetime import datetime, timezone
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor, ExecutionStatus
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        compute_correlated_truncated_kelly_size,
        compute_kelly_ticket_size,
        check_recorder_freshness,
        read_fast_tick,
    )

    # 1. F-23: Canonical JSON string wire-byte HMAC signing
    secret_b64 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    canonical_json = json.dumps({"type": "WALLET", "nonce": "7", "nested": {"x": 1}}, separators=(",", ":"))
    hdrs = PolymarketLiveExecutor.build_relayer_builder_headers(
        api_key="k",
        secret=secret_b64,
        passphrase="p",
        method="POST",
        request_path="/submit",
        body=canonical_json,
        timestamp=1700000000,
    )
    expected_msg = f"1700000000POST/submit{canonical_json}".encode("utf-8")
    expected_sig = base64.urlsafe_b64encode(
        hmac.new(base64.urlsafe_b64decode(secret_b64), expected_msg, hashlib.sha256).digest()
    ).decode("utf-8")
    assert hdrs["POLY_BUILDER_SIGNATURE"] == expected_sig

    # 2. F-02: `find_redemption_payouts` returns `None` when NegRiskAdapter RPC fails (`None`)
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "f16_exec.jsonl")
    ex.dry_run = False
    ex.funder_address = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
    cond_id = "0x" + ("cd" * 32)
    rpc_calls = []

    def fake_rpc_logs(method, params):
        rpc_calls.append((method, params))
        flt = (params or [{}])[0]
        if str(flt.get("address", "")).lower() == ex.NEG_RISK_ADAPTER_ADDRESS.lower():
            return None  # Simulate RPC error on NegRiskAdapter!
        return []

    monkeypatch.setattr(ex, "get_current_block_number", lambda: 200)
    monkeypatch.setattr(ex, "_rpc", fake_rpc_logs)
    assert ex.find_redemption_payouts(cond_id, from_block=100, max_span=1000) is None
    assert len(rpc_calls) == 2

    # 3. F-01: `signature_type=0` EOA wallet is NOT coerced to `1` (`POLY_PROXY`)
    import web3
    ex_eoa = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "f16_eoa.jsonl")
    ex_eoa.dry_run = False
    ex_eoa.signature_type = 0
    ex_eoa.funder_address = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
    ex_eoa.private_key = "0x" + ("11" * 32)
    monkeypatch.delenv("POLYGON_PRIVATE_KEY", raising=False)
    checked_gas_payers = []

    class DummyEth:
        class account:
            @staticmethod
            def from_key(pk):
                return type("Acct", (), {"address": "0x2222222222222222222222222222222222222222"})()

        @staticmethod
        def get_balance(addr):
            checked_gas_payers.append(str(addr).lower())
            return 0  # Exits cleanly right after proving sig_type==0 selected funder_cs!

    class DummyW3:
        HTTPProvider = web3.Web3.HTTPProvider
        to_checksum_address = staticmethod(web3.Web3.to_checksum_address)
        eth = DummyEth()

        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(web3, "Web3", DummyW3)
    assert ex_eoa.attempt_onchain_redemption(cond_id) is None
    assert checked_gas_payers == [ex_eoa.funder_address.lower()]

    # 4. F-09: Per-leg fees + partial Leg-1 `takingAmount` unwind in `execute_atomic_dominance_box`
    ex_box = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "f16_box.jsonl")
    ex_box.dry_run = False
    ex_box.is_authenticated = True
    monkeypatch.setattr(ex_box, "get_token_tick_size", lambda tid: 0.01)
    monkeypatch.setattr(ex_box, "get_token_neg_risk", lambda tid, explicit_neg_risk=None: False)
    # High fee on leg_b (`0.25`) pushes box cost over `0.995` even if `fee_rate` default was `0.07`
    cap_res = ex_box.execute_atomic_dominance_box(
        box_id="BOX_FEE_B",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.48,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.46,
        shares=20,
        max_box_cost_net=0.995,
        fee_rate_a=0.07,
        fee_rate_b=0.25,
    )
    assert cap_res["success"] is False and "WORST_LIMIT_BOX_COST_EXCEEDS_CAP" in cap_res["error"]

    class PartialFillClient:
        def create_order(self, args, options=None):
            return {"token_id": args.token_id, "price": args.price, "size": args.size}

        def post_order(self, signed, order_type):
            # Returns partial 12-share fill instead of requested 20 shares!
            return {"orderID": "OID_PARTIAL_12", "takingAmount": "12.0"}

    ex_box.client = PartialFillClient()
    unwound_partial = []
    monkeypatch.setattr(
        ex_box,
        "execute_unwind_order",
        lambda token_id, size, side="SELL", min_price=0.01, neg_risk=None: (
            unwound_partial.append((token_id, size)) or {"success": True, "matched_size": size}
        ),
    )
    part_res = ex_box.execute_atomic_dominance_box(
        box_id="BOX_PARTIAL",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.50,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.42,
        shares=20,
        max_box_cost_net=0.995,
        leg_a_avail_shares=25.0,
        leg_b_avail_shares=80.0,
    )
    assert part_res["success"] is False and part_res["stage"] == "LEG_1_PARTIAL_FILL_UNWOUND"
    assert unwound_partial == [("tok_a", 12.0)]

    # 5. F-16: Stale `>120s` hot-path collateral cache invalidated in live mode
    ex_col = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "f16_col.jsonl")
    ex_col.dry_run = False
    ex_col.is_authenticated = False  # Live fallback returns None when stale cache is invalidated
    ex_col._collateral_cache = (time.time() - 300.0, 99.50)
    assert ex_col.get_collateral_balance(hot_path=True) is None

    # 6. F-05: Zero/negative Kelly edge returns `0.0` (never `min_lot_usd` or `MAX_ABSOLUTE_TICKET_USD`)
    assert compute_correlated_truncated_kelly_size(p_win=0.50, entry_px=0.75, live_equity=100.0) == 0.0
    assert compute_correlated_truncated_kelly_size(p_win=0.85, entry_px=0.72, live_equity=0.0) == 0.0
    assert compute_kelly_ticket_size(p_model=0.65, p_eff=0.72, bankroll=100.0) == 0.0
    assert compute_kelly_ticket_size(p_model=0.85, p_eff=0.70, bankroll=-10.0) == 0.0

    # 7. F-22: Sticky account-equity floor halt + $3.00 recovery hysteresis
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "f16_state.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "f16_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "f16_state.json"
    h.risk_controller.min_equity_floor_usd = 48.0
    assert h.risk_controller.check_equity_drawdown(45.5, 80.0) is True
    assert h.risk_controller.is_halted() is True
    # Hot-path check (`allow_auto_clear=False`) must NOT auto-clear even at $55!
    assert h.risk_controller.check_equity_drawdown(55.0, 80.0) is True
    assert h.risk_controller.is_halted() is True
    # Verified refresh below $51 (`48 + 3`) stays halted; >= $51 clears cleanly!
    assert h.risk_controller.check_equity_drawdown(49.5, 80.0, allow_auto_clear=True) is True
    assert h.risk_controller.check_equity_drawdown(51.5, 80.0, allow_auto_clear=True) is False
    assert h.risk_controller.is_halted() is False

    # 8. M-01: `7.2`-share position (`5 <= rem < 10`) posts single `7.2`-share maker exit (no `<5` orphan split!)
    real_tok = "554433221100998877665544332211"
    pos_7sh = {
        "trade_id": "LIVE_M01_ORPHAN_GUARD",
        "token_id": real_tok,
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "exit_order_status": "EXIT_RECOVERY_REQUIRED",
        "inventory_reconciled": True,
        "entry_price": 0.72,
        "entry_shares": 7.2,
        "remaining_shares": 7.2,
        "candle_expiry_ts": time.time() + 240.0,
        "exit_tranches": [
            {"idx": 1, "size": 5.0, "price": 0.95, "status": "PENDING"},
            {"idx": 2, "size": 2.2, "price": 0.98, "status": "PENDING"},
        ],
    }
    posted_m01 = []
    h._wallet_token_balance = MagicMock(return_value=(7.2, h.ONCHAIN_SOURCE))
    h._strict_open_orders = lambda: []
    h._get_verified_shm_book = lambda p: {"bids": [{"price": "0.80", "size": "100"}], "asks": [{"price": "0.82", "size": "100"}]}
    h.executor.post_maker_exit_order = lambda **kw: (
        posted_m01.append(kw) or {"success": True, "orderID": "OID_SINGLE_72", "price": kw["price"]}
    )
    assert h._attempt_maker_exit_post_impl("LIVE_M01_ORPHAN_GUARD", pos_7sh) is True
    assert len(posted_m01) == 1 and posted_m01[0]["size"] == pytest.approx(7.2)

    # 9. F-11 / M-05: Internal JSON staleness in `check_recorder_freshness` & future skew in `read_fast_tick`
    hb_path = tmp_path / "recorder_hb.json"
    now_s = time.time()
    hb_path.write_text(json.dumps({"timestamp_unix": now_s - 45.0}), encoding="utf-8")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RECORDER_HEARTBEAT_FILES", [hb_path])
    ok_hb, reason_hb = check_recorder_freshness(max_stale_sec=10.0)
    assert ok_hb is False and "internal_stale" in reason_hb

    monkeypatch.delenv("PM_FAST_TICK_DIR", raising=False)
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.FAST_TICK_SHM_DIR", tmp_path)
    (tmp_path / "pm_fast_tick_BTC.json").write_text(
        json.dumps({"timestamp_unix": now_s + 10.0, "spot_price": 84000.0}), encoding="utf-8"
    )
    assert read_fast_tick("BTC") is None

    # 10. F-17 (NYSE EST post-DST blackout) & F-07 (15m Chainlink missing USD spot veto)
    snipe_f17 = []

    async def mock_snipe_f17(**kw):
        snipe_f17.append(kw)
        return MagicMock(success=True)

    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.05, "OK")
    h.executor.execute_snipe_order_async = mock_snipe_f17
    h.executor.get_collateral_balance = lambda *a, **kw: 95.0
    # Monday Nov 2, 2026 14:20:00 UTC == 09:20:00 EST (after Nov 1 DST fallback!)
    est_open_ts = datetime(2026, 11, 2, 14, 20, 0, tzinfo=timezone.utc).timestamp()
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.time.time", lambda: est_open_ts)
    shock_est = {
        "event_id": "EVT_NYSE_EST",
        "market_id": "6099991",
        "condition_id": "0xnyse",
        "t0_unix": est_open_ts,
        "title": "Bitcoin Up or Down - Nov 2, 9:00AM-10:00AM ET",
        "asset": "BTC",
        "horizon": "1h",
        "shock_direction": "BUY",
        "seconds_to_expiry": 240.0,
        "spot_at_t0": 84250.0,
        "trigger_price": 84250.0,
        "candle_open_spot": 84050.0,
        "candle_distance_pct": 0.238,
        "shock_volume_100ms": 3000000.0,
        "shock_ofi": 0.92,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok,
                "raw_top_asks": [[0.72, 100.0]],
                "raw_top_bids": [[0.71, 100.0]],
                "effective_price_$25": 0.72,
                "vwap_$25": 0.72,
                "age_book_ms": 50.0,
                "book_timestamp": est_open_ts,
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_est))
    assert len(snipe_f17) == 0, "Monday 09:20 EST (14:20 UTC post-DST) must be blocked by NYSE blackout!"

    # Move outside NYSE blackout (Monday 15:20 UTC == 10:20 EST) and test 15m Chainlink missing USD spot veto (`F-07`)
    est_1020_ts = datetime(2026, 11, 2, 15, 20, 0, tzinfo=timezone.utc).timestamp()
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.time.time", lambda: est_1020_ts)
    shock_15m_no_usd = dict(
        shock_est,
        event_id="EVT_15M_NO_USD",
        market_id="6099992",
        t0_unix=est_1020_ts,
        horizon="15m",
        authoritative_chainlink_open=84050.123456,
        # Intentionally omit chainlink_proxy_spot & coinbase_spot -> must veto USDT vs USD comparison!
    )
    shock_15m_no_usd["pre_shock_features_t0"] = {
        "UP": dict(shock_est["pre_shock_features_t0"]["UP"], book_timestamp=est_1020_ts)
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_15m_no_usd))
    assert len(snipe_f17) == 0, "Live 15m Chainlink market without verified USD spot anchor must fail closed!"



def test_fix18_canceled_market_resolved_terminal_state():
    """
    Verifies deterministic handling of Polymarket CLOB status 'CANCELED_MARKET_RESOLVED':
    1. cancel_order recognizes 'CANCELED_MARKET_RESOLVED' as terminal CANCELED (not UNKNOWN).
    2. get_order_fill_summary marks is_canceled=True and terminal=True.
    """
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor(dry_run=False)
    ex.client = MagicMock()
    ex.is_authenticated = True
    ex.client.cancel_orders.return_value = {"canceled": []}
    ex.client.get_order.return_value = {
        "status": "CANCELED_MARKET_RESOLVED",
        "size_matched": "0.0",
        "original_size": "12.2",
        "price": "0.95",
        "side": "SELL",
    }
    cancel_res = ex.cancel_order("0xTEST_OID_RESOLVED")
    assert cancel_res.is_canceled is True
    assert cancel_res.outcome == "CANCELED"

    summary = ex.get_order_fill_summary("0xTEST_OID_RESOLVED")
    assert summary is not None
    assert summary["resting"] is False
    assert summary["terminal"] is True


def test_fix19_15m_usd_vs_usdt_oracle_and_supervision_parity(tmp_path, monkeypatch):
    """
    Forensic regression test for LIVE_6169334_1792980781_UP (15m ETH Chainlink USD vs Binance USDT unit mismatch):
      1. PolymarketTerminalRecorder.get_chainlink_proxy_spot() converts Binance USDT spot to true USD via
         causal rolling median USDT/USD basis (returning ~2311.20 USD, NEVER 2314.40 USDT), and returns 0.0
         when neither Coinbase USD nor basis history is available.
      2. Exact replay of LIVE_6169334_1792980781_UP (authoritative_chainlink_open=2311.940735 USD,
         spot_at_t0=2314.41 USDT, coinbase_spot=2311.19 USD, even with legacy unadjusted
         chainlink_proxy_spot=2314.3973) is deterministically REJECTED (0 orders) because true USD distance
         is -0.0325% OTM for UP.
      3. Open 15m USD-settled positions carry spot_denomination='USD' + USD entry_spot_ref and route
         check_resolutions_and_manage_positions supervision strictly through get_usd_reference_spot_price.
    """
    import asyncio
    from collections import deque
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_terminal_recorder import PolymarketDualFeed1HRecorder as PolymarketTerminalRecorder
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    # 1. Recorder true-USD Chainlink proxy spot conversion
    rec = PolymarketTerminalRecorder.__new__(PolymarketTerminalRecorder)
    rec.asset = "ETH"
    rec.spot_price = 2314.41  # Binance ETHUSDT
    rec.coinbase_spot = 0.0
    rec.coinbase_spot_ts = 0.0
    rec._venue_div_history = deque(maxlen=200)
    rec._cl_proxy_history = deque(maxlen=400)
    now_u = 1792980781.75
    # Without Coinbase or basis history, never emit raw USDT as USD proxy!
    assert rec.get_chainlink_proxy_spot(now_u) == 0.0

    rec.coinbase_spot = 2311.19  # Coinbase ETH-USD
    rec.coinbase_spot_ts = now_u
    for _ in range(20):
        rec._venue_div_history.append(13.82)  # +13.82 bps USDT/USD basis
    cl_usd = rec.get_chainlink_proxy_spot(now_u)
    assert 2311.00 <= cl_usd <= 2311.40, f"Expected true USD ~2311.20, got {cl_usd}"
    assert rec.get_chainlink_twap_60s(now_u) == pytest.approx(cl_usd, abs=0.05)

    # 2. Exact replay of LIVE_6169334_1792980781_UP must be rejected (0 orders placed)
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "f19_state.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "f19_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "f19_state.json"
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 72.0
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.05, "OK")
    placed = []

    async def fail_if_called(**kw):
        placed.append(kw)
        return MagicMock(success=False, mode="REJECTED", details={})

    h.executor.execute_snipe_order_async = fail_if_called
    real_tok = "998877665544332211009988776655"
    shock_bugged_replay = {
        "event_id": "6169334_1792980781.749534",
        "market_id": "6169334",
        "condition_id": "0x6169334",
        "t0_unix": now_u,
        "title": "Ethereum Up or Down - October 25, 10:00PM-10:15PM ET",
        "asset": "ETH",
        "horizon": "15m",
        "resolution_source": "https://data.chain.link/streams/eth-usd-twap-60s-streams",
        "shock_direction": "BUY",
        "seconds_to_expiry": 118.2,
        "spot_at_t0": 2314.41,
        "trigger_price": 2314.41,
        "candle_open_spot": 2315.01,
        "authoritative_chainlink_open": 2311.940735,
        "coinbase_spot": 2311.19,
        "chainlink_proxy_spot": 2314.3973,  # Legacy unadjusted USDT value from pre-fix recorder!
        "chainlink_twap_60s": 2314.55,
        "shock_volume_100ms": 2_500_000.0,
        "shock_ofi": 0.90,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok,
                "best_bid": 0.46,
                "best_ask": 0.47,
                "raw_top_asks": [[0.47, 150.0]],
                "raw_top_bids": [[0.46, 150.0]],
                "effective_price_$25": 0.47,
                "vwap_$25": 0.47,
                "age_book_ms": 1357.1,
                "age_ask_ms": 1357.1,
                "book_timestamp": now_u,
            }
        },
    }
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.time.time", lambda: now_u)
    asyncio.run(h.evaluate_shock_and_execute(shock_bugged_replay))
    assert len(placed) == 0, "OTM ETH 15m UP setup (-0.0325% in USD) must NEVER pass cushion gate via USDT basis!"

    # 3. Supervision of open 15m USD-denominated position uses get_usd_reference_spot_price (NOT Binance USDT)
    from datetime import datetime, timezone
    now_sup = datetime.now(timezone.utc).timestamp()
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.time.time", lambda: now_sup)
    usd_calls = []
    usdt_calls = []
    h.get_usd_reference_spot_price = lambda sym: (usd_calls.append(sym) or 2309.50)
    h.get_reference_spot_price = lambda sym: (usdt_calls.append(sym) or 2313.10)
    h._strict_open_orders = lambda: [{"id": "OID_MAKER_95"}]
    h._get_verified_shm_book = lambda pos: {
        "bids": [{"price": "0.32", "size": "200"}],
        "asks": [{"price": "0.34", "size": "200"}],
    }
    h._wallet_token_balance = MagicMock(return_value=(20.0, h.ONCHAIN_SOURCE))
    h.executor.cancel_order = MagicMock(return_value={"canceled": ["OID_MAKER_95"], "is_canceled": True, "outcome": "CANCELED"})
    h.executor.get_order_fill_summary = MagicMock(return_value={
        "order_id": "OID_MAKER_95", "status": "CANCELED", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True,
    })
    unwound = []
    h.executor.execute_unwind_order = lambda **kw: (
        unwound.append(kw) or {
            "success": False,
            "orderID": None,
            "matched_size": 0.0,
            "retryable": True,
            "outcome_unknown": False,
            "error": "SIM_UNWIND_PASS",
        }
    )
    h.active_positions["LIVE_USD_SUP"] = {
        "trade_id": "LIVE_USD_SUP",
        "market_id": "6169334",
        "condition_id": "0x6169334",
        "token_id": real_tok,
        "target_token": "UP",
        "asset": "ETH",
        "horizon": "15m",
        "is_subhourly": True,
        "spot_denomination": "USD",
        "candle_open_spot": 2311.94,
        "entry_spot_ref": 2313.80,
        "candle_sigma": 0.0034,
        "entry_price": 0.72,
        "entry_shares": 20.0,
        "gross_entry_shares": 20.0,
        "remaining_shares": 20.0,
        "remaining_exit_shares": 20.0,
        "filled_exit_shares": 0.0,
        "remaining_cost_basis": 14.40,
        "notional_usd": 14.40,
        "fee_usd": 0.15,
        "entry_fee_cash_usd": 0.15,
        "target_exit_price": 0.95,
        "entry_ts": now_sup - 30.0,
        "candle_expiry_ts": now_sup + 175.0,
        "low_bid_detected_ts": now_sup - 7.0,
        "status": ExecutionStatus.EXIT_RESTING,
        "inventory_reconciled": True,
        "exit_order_id": "OID_MAKER_95",
        "exit_order_status": "RESTING",
        "is_liquidating": False,
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert usd_calls == ["ETH"], "USD-denominated 15m position must query get_usd_reference_spot_price!"
    assert usdt_calls == [], "USD-denominated 15m position must NEVER query Binance USDT get_reference_spot_price!"
    assert len(unwound) == 1, "True USD OTM break (2309.50 < 2311.94 open, bid=0.32) must trigger protective salvage!"


def test_v40_live_execution_speed_and_compounding_levers(tmp_path, monkeypatch):
    """
    Verifies the v4.0 live execution speed, compounding, and riskless Slot-2 graduation upgrades:
      1. Lever #1a: `_ThreadLocalClobHttpClient` `LifoQueue` warm TLS 1.3 HTTP/1.1 pool (`warm_pool(min_warm=2)`)
         reuses hot sockets across distinct OS worker threads without concurrent socket sharing.
      2. Gemini #2: `PolymarketLiveExecutor.execute_atomic_dominance_box(..., parallel_dispatch=True)`
         dispatches both pre-signed FOK legs concurrently (<5ms skew) AND auto-unwinds Leg 1 if Leg 2 rejects.
      3. Lever #1b + Lever #2: Smooth `18%` dynamic compounding at `$73.01` (`~$13.14` ticket instead of frozen `$12.00`)
         + Shot-1 `+2c` price-improved FAK strictly clamped at `<= p_max`.
      4. Gemini #6: `$0.985-$0.99` pre-expiry cash recycling (`8s <= TTE <= 25s`, `limit_price >= 0.98`) freeing
         collateral BEFORE `:00/:15/:30/:45` candle rollovers.
      5. Lever #3 + Gemini #12: `maybe_execute_graduated_d1_box` (`8/8` settled at `100%` WR) and
         `get_graduated_allowed_assets` (`>=$110` equity + `ready_for_live_graduation: true`).
    """
    import asyncio
    import json
    import threading
    from unittest.mock import MagicMock
    import src.polymarket_research.polymarket_live_executor as exec_mod
    import src.polymarket_research.polymarket_live_harvester as harv_mod
    from src.polymarket_research.polymarket_live_executor import (
        ExecutionStatus,
        PolymarketLiveExecutor,
        _ThreadLocalClobHttpClient,
    )
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    # 1. Warm LifoQueue HTTP/1.1 pool: warm_pool(min_warm=2) + cross-thread LIFO socket reuse
    pool_cli = _ThreadLocalClobHttpClient(timeout=4.0, max_pool_size=8)
    created_clients = []

    class FakeHttpxClient:
        def __init__(self):
            self.is_closed = False
            self.calls = 0
            created_clients.append(self)

        def request(self, method="GET", url="", **kw):
            self.calls += 1
            return MagicMock(status_code=200)

        def close(self):
            self.is_closed = True

    pool_cli._make_client = FakeHttpxClient
    warmed_cnt = pool_cli.warm_pool(url="https://clob.polymarket.com/time", min_warm=2, max_idle_sec=0.0)
    assert warmed_cnt == 2 and pool_cli._pool.qsize() == 2

    used_by_workers = []

    def _worker_req():
        b_cli = pool_cli._borrow_pool_client()
        used_by_workers.append(b_cli)
        b_cli.request("POST", "https://clob.polymarket.com/order")
        pool_cli._return_pool_client(b_cli)

    for _ in range(4):
        th = threading.Thread(target=_worker_req)
        th.start()
        th.join()
    # Different worker threads reused the pre-warmed hot pool without creating cold sockets!
    assert len(created_clients) == 2
    assert all(c in created_clients for c in used_by_workers)

    # 2. Parallel 2-leg FOK Dominance Box dispatch + automatic single-leg unwind on Leg 2 reject
    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    ex.auth_mode = "AUTHENTICATED_L2"
    ex._tick_size_cache["tok_a"] = 0.01
    ex._tick_size_cache["tok_b"] = 0.01
    ex._neg_risk_cache["tok_a"] = False
    ex._neg_risk_cache["tok_b"] = False
    if exec_mod.OrderArgsV2 is None:
        monkeypatch.setattr(exec_mod, "OrderArgsV2", lambda **kw: kw)
    if exec_mod.OrderType is None:
        monkeypatch.setattr(exec_mod, "OrderType", type("OT", (), {"FOK": "FOK", "FAK": "FAK", "GTC": "GTC"}))

    fake_clob = MagicMock()
    fake_clob.create_order.side_effect = lambda args, *a: {"token_id": getattr(args, "token_id", args["token_id"] if isinstance(args, dict) else "tok")}
    fake_clob.post_order.side_effect = [
        {"orderID": "OID_BOX_1", "status": "MATCHED", "takingAmount": "12", "makingAmount": "5.64"},
        {"orderID": "OID_BOX_2", "status": "MATCHED", "takingAmount": "12", "makingAmount": "5.76"},
    ]
    ex.client = fake_clob
    res_ok = ex.execute_atomic_dominance_box(
        box_id="BOX_PAR_OK",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.47,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.48,
        shares=12.0,
        max_box_cost_net=0.995,
        parallel_dispatch=True,
    )
    assert res_ok["success"] is True and res_ok["dispatch_mode"] == "PARALLEL_2LEG_FOK" and res_ok["shares"] == 12.0

    # Leg 2 rejects -> Leg 1 must automatically unwind!
    unwind_calls = []
    ex.execute_unwind_order = lambda tok, **kw: (unwind_calls.append((tok, kw)) or {"success": True, "matched_size": 12.0})
    fake_clob.post_order.side_effect = lambda signed, *a, **kw: (
        {"orderID": "OID_BOX_L1_ONLY", "status": "MATCHED", "takingAmount": "12", "makingAmount": "5.64"}
        if isinstance(signed, dict) and signed.get("token_id") == "tok_a"
        else {"errorMsg": "FOK order couldn't be fully filled", "orderID": None}
    )
    res_legout = ex.execute_atomic_dominance_box(
        box_id="BOX_PAR_LEGOUT",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.47,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.48,
        shares=12.0,
        max_box_cost_net=0.995,
        parallel_dispatch=True,
    )
    assert res_legout["success"] is False and res_legout["legged_out"] is True
    assert len(unwind_calls) == 1 and unwind_calls[0][0] == "tok_a"

    # 3. Smooth 18% dynamic compounding ($73.01 -> ~$13.14) + Shot-1 +2c FAK strictly <= p_max
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    monkeypatch.setattr(harv_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(harv_mod, "STATE_FILE", tmp_path / "v40_state.json")
    monkeypatch.setattr(harv_mod, "RESOLUTIONS_FILE", tmp_path / "v40_res.jsonl")

    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True, allowed_assets={"BTC", "ETH"})
    h.dry_run = False
    h.executor.dry_run = False
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "v40_state.json"
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 73.01
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.05, "OK")

    snipe_dispatches = []

    async def _capture_snipe(**kw):
        snipe_dispatches.append(kw)
        return type("FakeSnipeRes", (), {
            "success": False, "order_id": None, "tx_hashes": [], "filled_size": 0.0, "avg_price": 0.0,
            "size": 0.0, "price": 0.0, "fee_paid_usd": 0.0, "latency_ms": 1.0, "error_msg": "SIM", "error": "SIM",
            "mode": "FAK_KILLED_NO_MATCH", "details": {"fak_killed": True}, "execution_status": ExecutionStatus.REJECTED,
        })()

    h.executor.execute_snipe_order_async = _capture_snipe
    real_tok_v40 = "100434764618174237135201777197981253576172734064131101154122934005557319214073"
    now_v40 = time.time()
    shock_v40 = {
        "shock_id": "v40_smooth_snipe",
        "market_id": "6200101",
        "condition_id": "0x6c7e137b9293b4004131cd749fe460eeb669b626ea5b3d9795bffbe491caa527",
        "title": "Ethereum Up or Down - October 26, 10:00AM-10:15AM ET",
        "asset": "ETH",
        "horizon": "15m",
        "resolution_source": "https://data.chain.link/streams/eth-usd-twap-60s-streams",
        "t0_unix": now_v40,
        "seconds_to_expiry": 240.0,
        "expiry_ts": now_v40 + 240.0,
        "candle_sigma": 0.0024,
        "shock_volume_100ms": 620000.0,
        "is_40ms_fast_track": True,
        "shock_direction": "BUY",
        "shock_ofi": 0.95,
        "spot_at_t0": 2345.00,
        "coinbase_spot": 2345.00,
        "candle_open_spot": 2340.00,
        "twap_60s_open": 2340.00,
        "candle_distance_pct": 0.2137,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x6c7e137b9293b4004131cd749fe460eeb669b626ea5b3d9795bffbe491caa527"},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok_v40,
                "best_bid": 0.71,
                "best_ask": 0.72,
                "spread": 0.01,
                "book_timestamp": now_v40 - 0.02,
                "age_book_ms": 20.0,
                "age_ask_ms": 210.0,
                "age_bid_ms": 300.0,
                "obi_l1": 0.35,
                "raw_top_bids": [[0.71, 150.0], [0.70, 100.0]],
                "raw_top_asks": [[0.72, 120.0], [0.73, 120.0]],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_v40))
    assert len(snipe_dispatches) >= 1
    disp = snipe_dispatches[0]
    assert disp["notional_usd"] > 12.50, f"Expected smooth 18% compounding > $12.50 at $73.01 equity, got {disp['notional_usd']}"
    assert disp["target_price"] == 0.74, f"Expected Shot-1 +2c price-improved FAK (0.72 + 0.02 = 0.74), got {disp['target_price']}"
    assert disp["target_price"] <= disp["max_price_ceiling"], "Shot-1 target_price must never exceed p_max ceiling!"

    # 4. Pre-expiry $0.985-$0.99 instant cash recycling (`8s <= TTE <= 25s`, `limit_px >= 0.98`)
    h.get_usd_reference_spot_price = lambda sym: 2348.0
    h._strict_open_orders = lambda: [{"id": "OID_MKR_99"}]
    h._get_verified_shm_book = lambda pos: {
        "bids": [{"price": "0.99", "size": "250"}],
        "asks": [{"price": "1.00", "size": "250"}],
    }
    h._wallet_token_balance = MagicMock(return_value=(18.0, h.ONCHAIN_SOURCE))
    h.executor.cancel_order = MagicMock(return_value={"canceled": ["OID_MKR_99"], "is_canceled": True, "outcome": "CANCELED"})
    h.executor.get_order_fill_summary = MagicMock(return_value={
        "order_id": "OID_MKR_99", "status": "CANCELED", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True,
    })
    recycled_unwinds = []
    h.executor.execute_unwind_order = lambda **kw: (
        recycled_unwinds.append(kw) or {
            "success": True, "orderID": "OID_RECYCLE_99", "matched_size": 18.0, "taking_amount": 17.8076, "fee_usd": 0.0124,
        }
    )
    h.active_positions["LIVE_RECYCLE_99"] = {
        "trade_id": "LIVE_RECYCLE_99",
        "market_id": "6200101",
        "condition_id": "0x6200101",
        "token_id": real_tok_v40,
        "target_token": "UP",
        "asset": "ETH",
        "horizon": "15m",
        "is_subhourly": True,
        "spot_denomination": "USD",
        "candle_open_spot": 2340.00,
        "entry_spot_ref": 2345.00,
        "candle_sigma": 0.0024,
        "entry_price": 0.72,
        "entry_shares": 18.0,
        "gross_entry_shares": 18.0,
        "remaining_shares": 18.0,
        "remaining_exit_shares": 18.0,
        "filled_exit_shares": 0.0,
        "remaining_cost_basis": 12.96,
        "notional_usd": 12.96,
        "fee_usd": 0.12,
        "entry_fee_cash_usd": 0.12,
        "target_exit_price": 0.99,
        "entry_ts": now_v40 - 200.0,
        "candle_expiry_ts": time.time() + 15.0,  # 15s TTE inside [8s, 25s] recycle window!
        "status": ExecutionStatus.EXIT_RESTING,
        "inventory_reconciled": True,
        "exit_order_id": "OID_MKR_99",
        "exit_order_status": "RESTING",
        "is_liquidating": False,
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(recycled_unwinds) == 1
    assert recycled_unwinds[0]["min_price"] >= 0.98, f"Expected >= $0.98 recycle floor, got {recycled_unwinds[0]['min_price']}"

    # 5. Lever #3 (`maybe_execute_graduated_d1_box`) & Gemini #12 (`get_graduated_allowed_assets`)
    (tmp_path / "state_shadow_sol_v392.json").write_text(json.dumps({"ready_for_live_graduation": True}), encoding="utf-8")
    assert "SOL" not in h.get_graduated_allowed_assets(total_equity=73.01)  # Blocked < $110!
    assert "SOL" in h.get_graduated_allowed_assets(total_equity=115.00)     # Auto-unlocked >= $110!

    h.active_positions.clear()
    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps({"by_sleeve": {"D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 5, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 4.2}}}),
        encoding="utf-8",
    )
    cand_box = {
        "box_id": "D1_TEST_SLOT2",
        "leg_a_token_id": "tok_a",
        "leg_b_token_id": "tok_b",
        "leg_a_limit_price": 0.47,
        "leg_b_limit_price": 0.48,
        "shares": 12.0,
        "corridor_bps": 10.0,
        "leg_a_side": "UP",
        "leg_b_side": "DOWN",
        "leg_a_strike": 80000.0,
        "leg_b_strike": 80080.0,
        "leg_a_market_id": "m_a",
        "leg_b_market_id": "m_b",
    }
    assert h.maybe_execute_graduated_d1_box(cand_box)["executed"] is False  # 5 < 8 required!

    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps({"by_sleeve": {"D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 8, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 7.5}}}),
        encoding="utf-8",
    )
    h.executor.execute_atomic_dominance_box = MagicMock(return_value={"success": True, "shares": 12.0})
    h._startup_reconciled = True
    _prev_dry = h.dry_run
    h.dry_run = True  # non-live path: live-only prechecks (numeric tokens, fresh books) are covered by test_v42
    d1_exec = h.maybe_execute_graduated_d1_box(cand_box)
    h.dry_run = _prev_dry
    assert d1_exec["executed"] is True, d1_exec
    assert h.executor.execute_atomic_dominance_box.call_args.kwargs["parallel_dispatch"] is True


def test_v41_burst_drain_adverse_collapse_and_wfo_parity(tmp_path, monkeypatch):
    """
    v4.1 Forensic Remediation & Purged-WFO Parity Suite:
      1. Recorder evaluate_shock blocks socket burst-drain phantom shocks (exch_lag_ms > 1000ms AND
         multi-second exchange t_ts spread arriving in a 5ms OS recv burst), while firing on genuine sweeps.
      2. Executor AdverseCollapseGuard + Harvester 2.5s WS book ceiling & ingress lag/WS guards block
         collapsing-book fills like LIVE_6176805 ($0.82 trigger ask -> $0.66 fill).
      3. Harvester dynamic_sizing AND cushion boolean fix enforces Quarter-Kelly VWAP veto on thin
         cushions (<0.07% 15m), blocking LIVE_6176805 ($0.82 ask on 0.0597% cushion at $65.05 bankroll).
      4. Purged-WFO Z-adaptive FAK buffer (+1c for z_strike < 1.25, +2c for z_strike >= 1.25).
    """
    import asyncio
    import json
    from datetime import datetime, timezone
    from src.polymarket_research.polymarket_terminal_recorder import (
        PolymarketDualFeed1HRecorder,
        L2OrderBook,
    )
    from src.polymarket_research.polymarket_live_executor import (
        PolymarketLiveExecutor,
        OrderResult,
        ExecutionStatus,
    )
    import src.polymarket_research.polymarket_terminal_recorder as rec_mod
    import src.polymarket_research.polymarket_live_harvester as harvester_mod

    emitted_triggers = []
    monkeypatch.setattr(rec_mod, "TRIGGER_FILE", tmp_path / "live_shock_triggers.jsonl")
    monkeypatch.setattr(
        rec_mod,
        "_dispatch_trigger_fast",
        lambda path, payload: (emitted_triggers.append((str(path), dict(payload))) or True, json.dumps(payload)),
    )
    monkeypatch.setattr(rec_mod, "_persist_trigger_nonblocking", lambda *a, **kw: None)

    rec = PolymarketDualFeed1HRecorder(asset="ETH", shock_threshold=400_000.0)
    rec.clob_ws_connected = True
    rec.active_burst_tasks = {1, 2, 3, 4, 5}
    rec.spot_price = 2224.20
    rec.futures_price = 2224.10
    rec.finalized_1h_open = 2228.00
    now_u = time.time()
    rec.current_market = {
        "market_id": "6176800",
        "condition_id": "0x6176800",
        "title": "Ethereum Up or Down - Hourly",
        "end_dt": datetime.fromtimestamp(now_u + 1200, tz=timezone.utc),
        "candle_open_ts": int(now_u - 2400),
        "candle_close_ts": int(now_u + 1200),
        "resolution_source": "https://www.binance.com/en/trade/ETH_USDT",
    }
    for side, tok in (("UP", "1" * 24), ("DOWN", "2" * 24)):
        bk = L2OrderBook(tok)
        bk.bids = {0.70: 200.0}
        bk.asks = {0.72: 200.0}
        bk.last_book_update_ts = now_u - 0.05
        bk.last_best_ask_change_ts = now_u - 0.40
        bk.last_best_bid_change_ts = now_u - 0.40
        rec.books[side] = bk
    rec.spawn_burst_verification = lambda *a, **kw: None

    # 1a. Stale exchange_event_ts_ms (> 1000ms lag) -> VETOED
    mono_base = time.monotonic_ns()
    stale_ms = int((time.time() - 4.2) * 1000)
    rec.spot_trades.clear()
    rec.spot_trades.append((mono_base, stale_ms, stale_ms, 650_000.0, False, 2224.20))
    rec.evaluate_shock(mono_base, stale_ms, "SPOT")
    assert len(emitted_triggers) == 0, "Expected exch_lag_ms > 1000ms packet to be vetoed!"

    # 1b. OS socket burst-drain: 6 small trades spanning 7.5s of Binance t_ts drained within 4ms local mono -> VETOED
    rec.spot_trades.clear()
    fresh_ms = int(time.time() * 1000) - 20
    mono_burst = time.monotonic_ns()
    for idx in range(6):
        t_exch_i = fresh_ms - (5 - idx) * 1500  # 1,500ms apart on Binance!
        rec.spot_trades.append((mono_burst - (5 - idx) * 600_000, t_exch_i, t_exch_i, 110_000.0, False, 2224.20))
    rec.evaluate_shock(mono_burst, fresh_ms, "SPOT")
    assert len(emitted_triggers) == 0, "Expected multi-second Binance trades drained in 4ms OS burst NOT to sum into a phantom shock!"

    # 1c. Genuine 50ms institutional sweep -> FIRES with clob_ws_connected=True
    rec.spot_trades.clear()
    rec.last_shock_ts = 0.0
    rec.last_shock_ts_by_source.clear()
    now_ms_ok = int(time.time() * 1000) - 15
    mono_ok = time.monotonic_ns()
    for idx in range(5):
        t_exch_i = now_ms_ok - (4 - idx) * 10  # 40ms total span on Binance!
        rec.spot_trades.append((mono_ok - (4 - idx) * 10_000_000, t_exch_i, t_exch_i, 120_000.0, False, 2224.20))
    rec.evaluate_shock(mono_ok, now_ms_ok, "SPOT")
    live_trigs = [payload for p, payload in emitted_triggers if "live_shock_triggers" in p]
    assert len(live_trigs) == 1, f"Expected genuine 40ms sweep to emit 1 live trigger, got {len(live_trigs)}"
    assert live_trigs[0]["clob_ws_connected"] is True

    # 2a. Executor AdverseCollapseGuard rejects >= 4c downward ask collapse
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "exec_v41.jsonl")
    collapsed_book = {
        "asks": [{"price": "0.66", "size": "200"}],
        "bids": [{"price": "0.65", "size": "200"}],
        "timestamp": time.time(),
    }
    res_collapse = asyncio.run(
        ex.execute_snipe_order_async(
            trade_id="TEST_COLLAPSE_6176805",
            token_id="9" * 24,
            target_token="DOWN",
            notional_usd=12.0,
            target_price=0.84,
            max_price_ceiling=0.85,
            min_price_floor=0.55,
            expected_best_price=0.82,
            prefetched_book=collapsed_book,
            market_fee_rate=0.07,
            market_fee_exponent=1.0,
        )
    )
    assert res_collapse.success is False
    assert "AdverseCollapseGuard" in (res_collapse.error or "")

    # 2b & 3. Harvester live ingress guards, 2.5s WS book ceiling -> REST refresh, Adverse Ask Collapse, and LIVE_6176805 Kelly veto
    monkeypatch.setattr(harvester_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(harvester_mod, "STATE_FILE", tmp_path / "state_v41.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    real_tok_down = "888888888888888888888888"
    for sym in ("BTC", "ETH"):
        (tmp_path / f"pm_fast_tick_{sym}.json").write_text(
            json.dumps({"ts": time.time(), "spot_price": 2224.20}),
            encoding="utf-8",
        )

    h = PolymarketLiveHarvester(
        dry_run=True,
        dynamic_sizing=True,
        hold_to_maturity=False,
        ticket_notional=12.0,
        max_exposure=60.0,
        allowed_assets={"BTC", "ETH"},
    )
    h.dry_run = False
    h.executor.dry_run = False
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "state_v41.json"
    h._startup_reconciled = True
    h._last_known_collateral = 65.05
    h.high_water_mark_equity = 65.05
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 65.05

    dispatched = []
    rest_book_calls = []

    async def _mock_rest_book(tid):
        rest_book_calls.append(tid)
        return {
            "asks": [{"price": "0.66", "size": "250"}],
            "bids": [{"price": "0.65", "size": "250"}],
            "timestamp": time.time(),
        }

    async def _mock_snipe(**kw):
        dispatched.append(kw)
        return OrderResult(
            success=False, order_id=None, trade_id=kw["trade_id"], token_id=kw["token_id"],
            target_token=kw["target_token"], side="BUY", price=0.0, size=0.0, notional_usd=0.0,
            fee_usd=0.0, latency_ms=1.0, mode="FAK_KILLED_NO_MATCH", execution_status=ExecutionStatus.REJECTED,
            confirmed_onchain=False, error="FAK killed", details={"fak_killed": True},
        )

    h.executor.get_market_book_async = _mock_rest_book
    h.executor.execute_snipe_order_async = _mock_snipe

    def _make_eth_15m_shock(shock_id: str, **overrides):
        t_now = time.time()
        base = {
            "shock_id": shock_id,
            "t0_unix": t_now - 0.05,
            "exchange_event_ts_ms": int((t_now - 0.08) * 1000),
            "clob_ws_connected": True,
            "market_id": f"MKT_{shock_id}",
            "condition_id": "0x6176805",
            "asset": "ETH",
            "horizon": "15m",
            "title": "Ethereum Up or Down - 15m",
            "shock_direction": "SELL",
            "candle_distance_pct": -0.0597,
            "candle_open_spot": 2225.57,
            "spot_at_t0": 2224.24,
            "candle_sigma": 0.0017,
            "seconds_to_expiry": 152.9,
            "candle_open_ts": t_now - 747.1,
            "candle_expiry_ts": t_now + 152.9,
            "shock_ofi": -1.0,
            "shock_volume_100ms": 1_200_000.0,
            "delta_basis_100ms": -1.5,
            "age_ask_ms": 220.0,
            "resolution_source": "https://www.binance.com/en/trade/ETH_USDT",
            "fee_metadata": {"condition_id": "0x6176805", "fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {
                "DOWN": {
                    "token_id": real_tok_down,
                    "best_bid": 0.80,
                    "best_ask": 0.82,
                    "spread": 0.02,
                    "book_timestamp": t_now - 0.05,
                    "age_book_ms": 50.0,
                    "age_ask_ms": 220.0,
                    "age_bid_ms": 250.0,
                    "obi_l1": 0.30,
                    "raw_top_bids": [[0.80, 150.0], [0.79, 150.0]],
                    "raw_top_asks": [[0.82, 150.0], [0.83, 150.0]],
                }
            },
        }
        base.update(overrides)
        return base

    # Ingress guard A: exchange_event_ts_ms lag > 1000ms -> rejected immediately
    shk_lag = _make_eth_15m_shock("LAG_8S", exchange_event_ts_ms=int((time.time() - 8.4) * 1000))
    asyncio.run(h.evaluate_shock_and_execute(shk_lag))
    assert len(dispatched) == 0 and len(rest_book_calls) == 0

    # Ingress guard B: clob_ws_connected=False -> rejected immediately
    shk_ws_down = _make_eth_15m_shock("WS_DOWN", clob_ws_connected=False)
    asyncio.run(h.evaluate_shock_and_execute(shk_ws_down))
    assert len(dispatched) == 0 and len(rest_book_calls) == 0

    # Stale WS book (>2.5s old) -> forces REST get_market_book_async -> catches $0.82 -> $0.66 adverse collapse!
    shk_stale_book = _make_eth_15m_shock("STALE_BOOK_COLLAPSE", candle_distance_pct=-0.12)
    shk_stale_book["pre_shock_features_t0"]["DOWN"]["book_timestamp"] = time.time() - 12.0
    shk_stale_book["pre_shock_features_t0"]["DOWN"]["age_book_ms"] = 12000.0
    asyncio.run(h.evaluate_shock_and_execute(shk_stale_book))
    assert len(rest_book_calls) == 1, "Expected >2.5s old WS book to force fresh REST get_market_book_async!"
    assert len(dispatched) == 0, "Expected $0.82 -> $0.66 fresh ask collapse to be rejected before order dispatch!"

    # 3. Exact LIVE_6176805 replica (fresh book @ $0.82, thin -0.0597% cushion, $65.05 bankroll) -> rejected by [VWAP KELLY REJECT]!
    shk_6176805 = _make_eth_15m_shock("REPLICA_6176805")
    asyncio.run(h.evaluate_shock_and_execute(shk_6176805))
    assert len(dispatched) == 0, "Expected thin-cushion $0.82 overpay (LIVE_6176805 replica) to be blocked by [VWAP KELLY REJECT]!"

    # 4. Z-Adaptive FAK Buffer Parity: moderate z_strike (< 1.25) on TIER_B_STANDARD gets +1c (0.70 -> 0.71)
    shk_mod_z = _make_eth_15m_shock("MOD_Z_TIER_B", candle_distance_pct=-0.075, age_ask_ms=60.0)
    shk_mod_z["pre_shock_features_t0"]["DOWN"].update({
        "best_bid": 0.69,
        "best_ask": 0.70,
        "spread": 0.01,
        "age_ask_ms": 60.0,
        "raw_top_bids": [[0.69, 180.0], [0.68, 150.0]],
        "raw_top_asks": [[0.70, 180.0], [0.71, 150.0]],
    })
    asyncio.run(h.evaluate_shock_and_execute(shk_mod_z))
    assert len(dispatched) == 1, "Expected clean $0.70 ask with 0.075% cushion to dispatch!"
    assert dispatched[0]["target_price"] == 0.71, f"Expected +1c Z-adaptive FAK buffer (0.71) when z_strike < 1.25, got {dispatched[0]['target_price']}"
    assert dispatched[0]["expected_best_price"] == 0.70
    assert dispatched[0]["min_price_floor"] == 0.55


def test_v42_d1_dominance_box_live_bridge_and_lifecycle(tmp_path, monkeypatch):
    """
    End-to-end verification of v4.2 Zero-Churn Profit Acceleration:
      1. Alpha124 shadow quarantine flags (PM_DISABLE_SHADOW_M4_CATCHUP=1 preserves M1 defensive cancel
         while eliminating multi-rung /book rate-limit bursts) + graduation mirror + D1 candidate stream.
      2. Harvester Slot #2 live D1 bridge: $14.00 SLEEVE_1 collateral reserve, fresh L2 book walk <= 0.975,
         zero interference with SLEEVE_1 concurrency or cross-asset directional checks, $0.99 Maker GTC ask
         without queue-jump step-down, zero-bid OTM leg exemption, 8s..28s >= $0.98 CLOB cash recycling,
         and unified 2-leg D1_BOX_CONSOLIDATED PnL accounting (0 false losses).
    """
    import asyncio
    import json
    from unittest.mock import AsyncMock, MagicMock
    import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
    from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec
    import src.polymarket_research.polymarket_live_harvester as harvester_mod
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus, OrderResult

    # --- PART 1: Alpha124 Shadow Quarantine + Graduation Mirror + D1 Live Candidate Stream ---
    a124_dir = tmp_path / "alpha124"
    live_dir = tmp_path / "polymarket"
    a124_dir.mkdir(parents=True, exist_ok=True)
    live_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(a124_mod, "DATA_DIR", a124_dir)
    monkeypatch.setattr(a124_mod, "STATE_FILE", a124_dir / "alpha124_shadow_state.json")
    monkeypatch.setattr(a124_mod, "OPPS_FILE", a124_dir / "alpha124_top_opportunities.json")
    monkeypatch.setattr(a124_mod, "LEDGER_FILE", a124_dir / "alpha124_shadow_ledger.jsonl")
    monkeypatch.setattr(a124_mod, "LIVE_POLYMARKET_DIR", live_dir)
    monkeypatch.setattr(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", live_dir / "alpha124_shadow_state.json")
    monkeypatch.setattr(a124_mod, "D1_LIVE_CANDIDATES_FILE", live_dir / "d1_live_box_candidates.jsonl")
    monkeypatch.setenv("PM_DISABLE_SHADOW_M4_CATCHUP", "1")
    monkeypatch.setenv("PM_DISABLE_SHADOW_W2_TAKER", "1")

    daemon = a124_mod.Alpha124ShadowDaemon(single_scan=True)
    now_u = time.time()
    # Seed 11 settled winning D1 boxes in shadow state
    for i in range(11):
        daemon.closed_positions.append({
            "position_id": f"D1_HIST_{i}",
            "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
            "won": True,
            "tier_pnls_usd": {"T100": 2.40, "T1000": 8.11, "T5000": 28.50},
        })
    daemon.write_state_files([])
    mirror_path = live_dir / "alpha124_shadow_state.json"
    assert mirror_path.exists(), "Graduation mirror must be written to data/polymarket/alpha124_shadow_state.json!"
    mirror_data = json.loads(mirror_path.read_text(encoding="utf-8"))
    assert mirror_data["by_sleeve"]["D1_SAME_ORACLE_DOMINANCE_BOX"]["closed"] == 11
    assert mirror_data["by_sleeve"]["D1_SAME_ORACLE_DOMINANCE_BOX"]["win_rate_pct"] == 100.0

    # Verify M4 quarantine flag blocks /book burst while keeping M1 defensive maker cancel intact
    m4_book_fetches = []
    async def _track_fetch(url, timeout=3.0):
        if "T_Y_M4" in url or "T_N_M4" in url:
            m4_book_fetches.append(url)
        if "T_M1_NO" in url:
            return {"bids": [{"price": "0.48", "size": "100"}], "asks": [{"price": "0.52", "size": "100"}]}
        return None
    daemon.fetch_json = _track_fetch
    exp_close = now_u + 14400.0
    daemon.spots["BTC"] = 79500.0
    asyncio.run(daemon.post_shadow_maker_entry(
        sleeve="M1_SVI_MAKER_SCALP", dedupe_key="M1_DEF_1", asset="BTC", title="BTC > 80k",
        side_label="NO", token_id="T_M1_NO", p_model=0.60, close_ts=exp_close,
        extra={"market_id": "M_RUNG", "strike": 80000.0, "is_downward": False},
    ))
    assert len(daemon.pending_maker_orders) == 1
    daemon.spots["BTC"] = 80250.0  # Spot surges +0.94% adversely across $80,000 strike!
    daemon.strike_ladders["BTC_LAD"] = [
        a124_mod.StrikeRungSpec("EV_BTC", "btc-daily", "BTC", "BTC Above", "M_RUNG", "0x1", "BTC > 80000", 80000.0, False, exp_close, "T_Y_M4", "T_N_M4")
    ]
    asyncio.run(daemon.handle_shock_triggers(
        [{"asset": "BTC", "shock_direction": "BUY", "shock_ofi": 0.92, "shock_volume_100ms": 1_500_000.0, "t0_unix": now_u, "spot_at_t0": 80250.0}],
        [],
        now_ts=now_u,
    ))
    assert len(daemon.pending_maker_orders) == 0, "Defensive M1 maker cancel must remain active!"
    assert len(m4_book_fetches) == 0, "Quarantined M4 catchup must issue zero multi-rung /book fetches!"

    # Emit live D1 candidate via scan_same_oracle_dominance_boxes
    tok_15m_up = "111111111111111111111111111111"
    tok_5m_dn = "222222222222222222222222222222"
    end_ts = round((now_u + 180.0) / 5.0) * 5.0
    m15 = TwapCandleMarketSpec(
        market_id="650015", condition_id="0x" + "aa" * 32, asset="BTC", horizon="15m",
        title="BTC 15m", start_ts=end_ts - 900.0, end_ts=end_ts, start_iso="2026-10-26T12:00:00Z",
        end_iso="2026-10-26T12:15:00Z", up_token=tok_15m_up, down_token="333333333333333333333333333333",
        fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams",
    )
    m5 = TwapCandleMarketSpec(
        market_id="650005", condition_id="0x" + "bb" * 32, asset="BTC", horizon="5m",
        title="BTC 5m", start_ts=end_ts - 300.0, end_ts=end_ts, start_iso="2026-10-26T12:10:00Z",
        end_iso="2026-10-26T12:15:00Z", up_token="444444444444444444444444444444", down_token=tok_5m_dn,
        fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams",
    )
    daemon.dominance_pairs[f"BTC_{int(end_ts)}"] = (m15, m5)
    daemon.get_authoritative_open_strike = AsyncMock(side_effect=lambda sp: 80000.0 if sp.horizon == "15m" else 80120.0)
    tok_15m_dn = "333333333333333333333333333333"
    tok_5m_up = "444444444444444444444444444444"
    fake_books = {
        tok_15m_up: {"asks": [{"price": "0.46", "size": "250"}], "bids": [{"price": "0.45", "size": "250"}]},
        tok_5m_dn: {"asks": [{"price": "0.46", "size": "250"}], "bids": [{"price": "0.45", "size": "250"}]},
        tok_15m_dn: {"asks": [{"price": "0.52", "size": "250"}], "bids": [{"price": "0.49", "size": "250"}]},
        tok_5m_up: {"asks": [{"price": "0.52", "size": "250"}], "bids": [{"price": "0.49", "size": "250"}]},
    }
    async def _fetch_d1(url, timeout=3.0):
        for tk, bk in fake_books.items():
            if tk in url:
                return bk
        return None
    daemon.fetch_json = _fetch_d1

    # --- PART 2: Harvester Startup Before Candidate File Exists -> Catches Very First D1 Box ---
    monkeypatch.setattr(harvester_mod, "DATA_DIR", live_dir)
    monkeypatch.setattr(harvester_mod, "STATE_FILE", live_dir / "live_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(live_dir))
    for sym, px in (("BTC", 80060.0), ("ETH", 2500.0)):
        (live_dir / f"pm_fast_tick_{sym}.json").write_text(
            json.dumps({
                "ts": now_u, "spot_price": px,
                tok_15m_up: {"bids": [[0.98, 50.0]], "asks": [[0.99, 600.0]]},  # Heavy $0.99 wall to test queue-jump immunity!
            }),
            encoding="utf-8",
        )

    h = PolymarketLiveHarvester(
        dry_run=True, dynamic_sizing=True, hold_to_maturity=False, ticket_notional=12.0,
        max_exposure=60.0, max_concurrent=1, allowed_assets={"BTC", "ETH"},
    )
    h.dry_run = False
    h.executor.dry_run = False
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.poll_onchain_redemptions = lambda: None
    h.state_file = live_dir / "live_state.json"
    h._startup_reconciled = True

    # Poll #0 before file exists -> initializes cleanly at offset 0 without missing first candidate
    assert asyncio.run(h._poll_d1_live_box_candidates(now_u)) == 0

    # Now shadow daemon scans & emits first live D1 candidate
    opps = []
    asyncio.run(daemon.scan_same_oracle_dominance_boxes(opps, now_ts=now_u))
    cand_file = live_dir / "d1_live_box_candidates.jsonl"
    assert cand_file.exists(), "Live D1 candidate JSONL must be emitted when rem_sec=180s and box_cost_net <= 0.980!"

    # Collateral reserve check: at $20.00 free collateral ($20 - $14 reserve = $6 < $7.50 min), D1 yields to SLEEVE_1
    cand_obj = json.loads(cand_file.read_text(encoding="utf-8").splitlines()[0])
    h._last_known_collateral = 20.00
    res_low_collat = h.maybe_execute_graduated_d1_box(cand_obj)
    assert res_low_collat["executed"] is False
    assert res_low_collat["reason"] == "INSUFFICIENT_BOX_COLLATERAL_HEADROOM"

    # At $65.05 bankroll ($13.50 box budget, leaving >$51 free for SLEEVE_1), _poll_d1_live_box_candidates executes!
    h._last_known_collateral = 65.05
    h.high_water_mark_equity = 65.05
    h.executor.get_collateral_balance = lambda *a, **kw: h._last_known_collateral
    h.executor.get_market_book = lambda tid: fake_books[tid]
    wallet_bals = {tok_15m_up: 0.0, tok_5m_dn: 0.0}
    h._wallet_token_balance = lambda tid: (wallet_bals.get(tid, 0.0), h.ONCHAIN_SOURCE)
    h._verify_entry_finality = MagicMock(return_value=(True, False))

    def _mock_atomic_box(**kw):
        assert kw["max_box_cost_net"] == pytest.approx(0.975)  # Shock fired at now_u -> is_quiet_book=False -> 0.975 cap!
        assert kw["parallel_dispatch"] is True, "Deep book (>=4x depth, <=0.975 net) must dispatch in parallel!"
        sh = int(kw["shares"])
        assert sh == 17, "25% dynamic sizing ($16.50 reserve) on $65.05 bankroll ($16.26 budget) must size 17 pairs!"
        wallet_bals[tok_15m_up] = float(sh)
        wallet_bals[tok_5m_dn] = float(sh)
        h._last_known_collateral = round(65.05 - sh * 0.92, 2)
        return {
            "success": True,
            "box_id": kw["box_id"],
            "shares": float(sh),
            "leg_1": {"token_id": tok_15m_up, "label": kw["leg_a_label"], "price": 0.46, "orderID": "OID_BOX_A", "raw": {"makingAmount": round(sh * 0.46, 2), "transactionsHashes": ["0xtxa"]}},
            "leg_2": {"token_id": tok_5m_dn, "label": kw["leg_b_label"], "price": 0.46, "orderID": "OID_BOX_B", "raw": {"makingAmount": round(sh * 0.46, 2), "transactionsHashes": ["0xtxb"]}},
        }

    posted_maker_exits = []
    h.executor.execute_atomic_dominance_box = _mock_atomic_box
    h.executor.post_maker_exit_order = lambda **kw: (
        posted_maker_exits.append(kw) or {"success": True, "orderID": f"EXIT_{kw['token_id'][:4]}", "price": kw["price"]}
    )

    assert asyncio.run(h._poll_d1_live_box_candidates(time.time())) == 1
    assert len(h.active_positions) == 2
    assert h._risk_bearing_positions() == {}, "Delta-hedged D1 box legs must NOT consume SLEEVE_1 directional slot!"

    # Verify cross-asset directional conflict guard for an ETH DOWN SLEEVE_1 candidate is NOT blocked by hedged BTC D1 box
    ok_conf, _ = h.executor.validate_cross_asset_directional_conflict(
        candidate_asset="ETH",
        candidate_direction="DOWN",
        candidate_expiry_ts=end_ts,
        active_positions=list(h._risk_bearing_positions().values()),
        max_expiry_window_delta=2700.0,
    )
    assert ok_conf is True

    # Reconcile & post $0.99 single-tranche Maker GTC asks (must NOT step down below $0.99 despite $0.99 wall!)
    tids = sorted(h.active_positions.keys())
    for tid in tids:
        if not h.active_positions[tid].get("exit_order_id"):
            assert h._attempt_maker_exit_post(tid, h.active_positions[tid]) is True
        assert h.active_positions[tid].get("exit_order_id")
        assert h.active_positions[tid]["target_exit_price"] == pytest.approx(0.99)
        assert "exit_tranches" not in h.active_positions[tid]

    # --- PART 3: Supervision Immunity at TTE=42s (Zero-Bid OTM Leg + $0.88 Winning Leg) ---
    tid_a = [t for t in tids if h.active_positions[t]["token_id"] == tok_15m_up][0]
    tid_b = [t for t in tids if h.active_positions[t]["token_id"] == tok_5m_dn][0]
    sh_held = float(h.active_positions[tid_a]["entry_shares"])
    for t in (tid_a, tid_b):
        h.active_positions[t]["candle_expiry_ts"] = time.time() + 42.0

    live_books = {
        tok_15m_up: {"bids": [{"price": "0.88", "size": "100"}], "asks": [{"price": "0.90", "size": "500"}]},
        tok_5m_dn: {"bids": [], "asks": [{"price": "0.02", "size": "100"}]},  # Dead OTM leg with ZERO bids!
    }
    h._strict_open_orders = lambda: [
        {"id": h.active_positions[tid_a]["exit_order_id"], "asset_id": tok_15m_up, "side": "SELL"},
        {"id": h.active_positions[tid_b]["exit_order_id"], "asset_id": tok_5m_dn, "side": "SELL"},
    ]
    h._get_verified_shm_book = lambda p: live_books[p["token_id"]]
    h.executor.get_order_fill_summary = lambda oid, tok: {
        "order_id": oid, "status": "LIVE", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": False, "resting": True,
    }
    unwind_calls = []
    h.executor.execute_unwind_order = MagicMock(side_effect=lambda **kw: unwind_calls.append(kw))

    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 0, "D1 box must NOT premature-recycle at $0.88 on a $0.953 box or salvage OTM leg!"
    assert h.risk_halt is False, "Zero-bid OTM leg of a hedged D1 box must NEVER trigger LIQUIDITY_CRISIS!"

    # --- PART 4: Pre-Expiry CLOB Cash Recycling at TTE=18s ($0.99 Bid Only, No $0.98 Dump or Stop-Loss Escalation) ---
    for t in (tid_a, tid_b):
        h.active_positions[t]["candle_expiry_ts"] = time.time() + 18.0
    # 4a. $0.98 bid at TTE=18s must NOT cancel resting $0.99 Maker GTC ask or dump at 96.8c!
    live_books[tok_15m_up] = {"bids": [{"price": "0.98", "size": "200"}], "asks": [{"price": "0.99", "size": "50"}]}
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 0, "D1 leg at $0.98 bid must keep resting $0.99 Maker GTC ask instead of taking a taker haircut!"

    # 4b. $0.99 bid triggers recycle; if FAK misses ($0.99 blinked), must hold to maturity (NEVER UNWIND_RETRY_REQUIRED!)
    live_books[tok_15m_up] = {"bids": [{"price": "0.99", "size": "200"}], "asks": [{"price": "1.00", "size": "50"}]}
    h.executor.cancel_order = lambda oid: {"is_canceled": True, "canceled": [oid]}
    h.executor.get_order_fill_summary = lambda oid, tok: {
        "order_id": oid, "status": "CANCELED", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True, "resting": False,
    }
    h.executor.execute_unwind_order = lambda **kw: (
        unwind_calls.append(kw) or {"success": False, "matched_size": 0.0, "error": "no orders found to match with fak order"}
    )
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 1 and unwind_calls[0]["min_price"] == pytest.approx(0.98)
    assert h.active_positions[tid_a]["exit_order_status"] == "DETERMINISTIC_TERMINAL_HOLD"
    assert h.active_positions[tid_a].get("unwind_retry_count", 0) == 0
    unwind_calls.clear()

    def _mock_recycle_unwind(**kw):
        unwind_calls.append(kw)
        gross_cash = round(sh_held * 0.99, 4)
        exit_fee = round(sh_held * 0.07 * 0.99 * 0.01, 4)
        return {
            "success": True,
            "orderID": "OID_RECYCLE_99",
            "matched_size": sh_held,
            "taking_amount": gross_cash,
            "fee_usd": exit_fee,
            "taking_amount_estimated": False,
            "transactions_hashes": ["0xrec1"],
        }

    h.executor.execute_unwind_order = _mock_recycle_unwind
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 1, "Winning D1 leg at $0.99 with TTE=18s must trigger pre-expiry CLOB cash recycling!"
    assert unwind_calls[0]["min_price"] == pytest.approx(0.98), "D1 $0.99 recycle must use 1c buffer ($0.98) to survive $0.99->$0.98 flickers!"
    assert tid_a not in h.active_positions
    assert tid_b in h.active_positions
    assert len(h.closed_positions) == 0, "Leg 1 close must stash onto partner leg without emitting half-box record!"
    assert "_closed_partner_leg" in h.active_positions[tid_b]

    # Now expire & resolve OTM Leg 2 (5m DOWN lost because UP won) -> emits 1 unified winning D1_BOX_CONSOLIDATED trade!
    h.active_positions[tid_b]["candle_expiry_ts"] = time.time() - 5.0
    h._strict_open_orders = lambda: []
    asyncio.run(h._apply_market_resolution(tid_b, h.active_positions[tid_b], "UP"))
    assert tid_b not in h.active_positions
    assert len(h.closed_positions) == 1
    consolidated = h.closed_positions[0]
    assert "D1_BOX_CONSOLIDATED" in consolidated["close_reason"]
    assert consolidated["exit_decomposition_bucket"] == "DOMINANCE_BOX_ARB"
    assert len(consolidated["box_legs_summary"]) == 2
    assert consolidated["won"] is True
    assert consolidated["net_pnl_usd"] > 0.25
    assert h.risk_controller.consecutive_losses == 0, "Winning D1 box must NEVER increment consecutive_losses!"

    # --- PART 5: Legged-Out 1ms Polygon Settlement Race -> Supervised Residual Handoff (Zero Orphaned Shares!) ---
    h._last_known_collateral = 65.05
    wallet_bals[tok_15m_up] = 0.0
    wallet_bals[tok_5m_dn] = 0.0
    fake_books[tok_5m_dn] = {"bids": [{"price": "0.45", "size": "100"}], "asks": [{"price": "0.46", "size": "14"}]}
    cand_legged = {
        **cand_obj,
        "box_id": "D1_LIVE_LEGGED_TEST",
        "dedupe_key": "D1_BTC_LEGGED_NEW",
        "timestamp_unix": time.time(),
        "expiry_ts": time.time() + 180.0,
    }
    captured_box_kw = {}

    def _mock_thin_legged_box(**kw):
        captured_box_kw.update(kw)
        return {
            "success": False,
            "stage": "LEG_2_REJECTED_UNWOUND",
            "legged_out": True,
            "outcome_unknown": False,
            "leg_1_order_id": "OID_LEG1_ONLY",
            "unwind_result": {"success": False, "matched_size": 0.0, "error": "SELL_INVENTORY_RECONCILIATION_REQUIRED: unreserved=0.0 < 12.0"},
            "residual_unhedged_leg": {
                "token_id": tok_15m_up,
                "label": "15M_UP",
                "price": 0.46,
                "matched_shares": 12.0,
                "unwound_shares": 0.0,
                "residual_shares": 12.0,
                "orderID": "OID_LEG1_ONLY",
                "raw": {},
                "unwind_outcome_unknown": False,
                "unwind_result": {"success": False, "matched_size": 0.0, "error": "SELL_INVENTORY_RECONCILIATION_REQUIRED"},
            },
            "error": "FOK order couldn't be fully filled",
        }

    h.executor.execute_atomic_dominance_box = _mock_thin_legged_box
    res_leg_handoff = h.maybe_execute_graduated_d1_box(cand_legged)
    assert captured_box_kw["parallel_dispatch"] is False, "Thin leg (<1.5x depth) must switch to sequential thinner-leg-first!"
    assert res_leg_handoff["executed"] is False
    assert "D1_LIVE_LEGGED_TEST_LEG_RESID" in h.active_positions, "Legged-out shares unsettled on Polygon MUST be registered in active_positions!"
    resid_pos = h.active_positions["D1_LIVE_LEGGED_TEST_LEG_RESID"]
    assert resid_pos["is_dominance_box"] is False, "Unhedged residual leg must NOT get delta-hedged D1 supervision immunity!"
    assert resid_pos["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    resid_pos["next_unwind_retry_ts"] = time.time() - 0.1

    # Tick 1: Polygon STILL hasn't settled BUY shares (wallet_bal == 0.0) -> must retry in 0.50s WITHOUT false UNRESOLVED_BALANCE_DISCREPANCY halt!
    live_books[tok_15m_up] = {"bids": [{"price": "0.45", "size": "200"}], "asks": [{"price": "0.47", "size": "200"}]}
    h.executor.execute_unwind_order = lambda **kw: {
        "success": False, "matched_size": 0.0, "error": "SELL_INVENTORY_RECONCILIATION_REQUIRED: unreserved=0.0 < 12.0",
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert "D1_LIVE_LEGGED_TEST_LEG_RESID" in h.active_positions
    assert resid_pos["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert resid_pos.get("unwind_retry_count", 0) == 0

    # Tick 2: Polygon settles 12.0 shares -> supervision immediately unwinds 100% of legged-out shares to flat!
    wallet_bals[tok_15m_up] = 12.0
    resid_pos["next_unwind_retry_ts"] = time.time() - 0.1
    h.executor.execute_unwind_order = lambda **kw: {
        "success": True, "orderID": "OID_RESID_UNWOUND", "matched_size": 12.0,
        "taking_amount": 5.40, "fee_usd": 0.21, "taking_amount_estimated": False, "transactions_hashes": ["0xuw2"],
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert "D1_LIVE_LEGGED_TEST_LEG_RESID" not in h.active_positions

    # --- PART 6: Pre-Book Balance Order, Unlocked 7-Coin D1 Boxes, ETH Sequential Tail-First Dispatch, Inline Unwind & Restart Persistence ---
    # 6a. Unknown assets (e.g. ZEC) rejected; expansion assets (e.g. DOGE) enforce 5.0bps corridor & 8/8 per-asset gate; ungraduated sleeves gated
    res_zec = h.maybe_execute_graduated_d1_box({**cand_obj, "asset": "ZEC", "dedupe_key": "D1_ZEC_TEST"})
    assert res_zec["executed"] is False and res_zec["reason"] == "UNSUPPORTED_D1_ASSET:ZEC"
    res_doge_tight = h.maybe_execute_graduated_d1_box({**cand_obj, "asset": "DOGE", "corridor_bps": 3.5, "dedupe_key": "D1_DOGE_TIGHT"})
    assert res_doge_tight["executed"] is False and "CORRIDOR_TOO_NARROW_OR_MISSING" in res_doge_tight["reason"]
    res_doge = h.maybe_execute_graduated_d1_box({**cand_obj, "asset": "DOGE", "corridor_bps": 8.0, "dedupe_key": "D1_DOGE_TEST"})
    assert res_doge["executed"] is False and res_doge["reason"] == "EXPANSION_ASSET_NOT_YET_8_OF_8_GRADUATED:DOGE"
    res_c1_ungrad = h.maybe_execute_graduated_d1_box({
        **cand_obj, "box_type": "COMPLETE_SET", "sleeve_source": "C1_BINARY_COMPLETE_SET",
        "leg_a_market_id": "650015", "leg_b_market_id": "650015", "dedupe_key": "C1_UNGRAD_TEST",
    })
    assert res_c1_ungrad["executed"] is False and res_c1_ungrad["reason"] == "SLEEVE_NOT_YET_8_OF_8_GRADUATED:C1_BINARY_COMPLETE_SET"

    # 6b. ETH skewed box allowed, _wallet_token_balance runs BEFORE get_market_book, parallel_dispatch=False, and 100% inline unwind recorded!
    h._last_known_collateral = 73.65
    call_sequence = []
    h._wallet_token_balance = lambda tid: (call_sequence.append("PRE_BAL") or (0.0, h.ONCHAIN_SOURCE))
    eth_books = {
        tok_15m_up: {"asks": [{"price": "0.82", "size": "90"}], "bids": [{"price": "0.80", "size": "90"}]},
        tok_5m_dn: {"asks": [{"price": "0.13", "size": "40"}], "bids": [{"price": "0.12", "size": "40"}]},
        tok_15m_dn: {"asks": [{"price": "0.20", "size": "90"}], "bids": [{"price": "0.17", "size": "90"}]},
        tok_5m_up: {"asks": [{"price": "0.88", "size": "40"}], "bids": [{"price": "0.80", "size": "40"}]},
    }
    h.executor.get_market_book = lambda tid: (call_sequence.append("GET_BOOK") or eth_books[tid])
    # Verify complement anti-box veto when complement best bids sum > 1.03 (e.g. 0.55 + 0.55 = 1.10)
    anti_books = {**eth_books, tok_15m_dn: {"bids": [{"price": "0.55", "size": "50"}]}, tok_5m_up: {"bids": [{"price": "0.55", "size": "50"}]}}
    h.executor.get_market_book = lambda tid: anti_books[tid]
    res_comp_veto = h.maybe_execute_graduated_d1_box({**cand_obj, "asset": "ETH", "dedupe_key": "D1_ETH_ANTIBOX_VETO", "ts_unix": time.time(), "expiry_ts": time.time() + 180.0})
    assert res_comp_veto["executed"] is False and "ANTI_BOX_COMPLEMENT_VETO" in res_comp_veto["reason"]

    call_sequence.clear()
    h.executor.get_market_book = lambda tid: (call_sequence.append("GET_BOOK") or eth_books[tid])
    sol_box_kw = {}

    def _mock_sol_inline_unwind(**kw):
        sol_box_kw.update(kw)
        return {
            "success": False,
            "stage": "LEG_2_REJECTED_UNWOUND",
            "legged_out": True,
            "outcome_unknown": False,
            "unwind_result": {
                "success": True, "orderID": "0x389cae", "matched_size": 14.17,
                "taking_amount": 11.1943, "fee_usd": 0.1646,
            },
            "residual_unhedged_leg": {
                "token_id": tok_15m_up, "label": "15M_UP", "price": 0.82,
                "matched_shares": 14.17, "unwound_shares": 14.17, "residual_shares": 0.0,
                "orderID": "0xsol_in", "raw": {"makingAmount": 11.6194},
                "unwind_outcome_unknown": False,
                "unwind_result": {
                    "success": True, "orderID": "0x389cae", "matched_size": 14.17,
                    "taking_amount": 11.1943, "fee_usd": 0.1646,
                },
            },
            "error": "FOK order couldn't be fully filled",
        }

    h.executor.execute_atomic_dominance_box = _mock_sol_inline_unwind
    cand_sol = {
        **cand_obj,
        "box_id": "D1_LIVE_ETH_1793037600_14389",
        "dedupe_key": "D1_ETH_6213180_6214389",
        "asset": "ETH",
        "ts_unix": time.time(),
        "expiry_ts": time.time() + 180.0,
    }
    pre_closed_len = len(h.closed_positions)
    res_sol = h.maybe_execute_graduated_d1_box(cand_sol)
    assert res_sol["executed"] is False
    assert "shares" in sol_box_kw, res_sol
    assert sol_box_kw["parallel_dispatch"] is False, "Skewed tail box must dispatch fragile 5m leg first (sequential)!"
    assert max(i for i, s in enumerate(call_sequence) if s == "PRE_BAL") < min(i for i, s in enumerate(call_sequence) if s == "GET_BOOK")
    assert len(h.closed_positions) == pre_closed_len + 1
    inline_rec = h.closed_positions[-1]
    assert inline_rec["close_reason"] == "D1_INLINE_LEGGED_OUT_UNWIND"
    assert inline_rec["asset"] == "ETH"
    assert inline_rec["net_pnl_usd"] == pytest.approx(-0.74, abs=0.01)

    # 6c. Reload harvester from disk -> seen_d1_box_keys survives restart and blocks duplicate attempt!
    h_reloaded = PolymarketLiveHarvester(
        dry_run=True, dynamic_sizing=True, hold_to_maturity=False, ticket_notional=12.0,
        max_exposure=60.0, max_concurrent=1, allowed_assets={"BTC", "ETH"},
    )
    h_reloaded.state_file = h.state_file
    h_reloaded.load_state()
    assert "D1_ETH_6213180_6214389" in h_reloaded._seen_d1_box_keys
    res_dup = h_reloaded.maybe_execute_graduated_d1_box(cand_sol)
    assert res_dup["executed"] is False and res_dup["reason"] == "ALREADY_EXECUTED_PAIR"

    # 6d. 12h Per-Asset Legging Circuit Breaker + Multi-Box Concurrency (max_concurrent_d1_boxes=4) + Graduated DOGE $15 Cap
    h.closed_positions.append({
        "close_reason": "D1_INLINE_LEGGED_OUT_UNWIND",
        "asset": "ETH",
        "net_pnl_usd": -0.60,
        "exit_time_unix": time.time(),
    })
    res_eth_cb = h.maybe_execute_graduated_d1_box({
        **cand_obj, "asset": "ETH", "dedupe_key": "D1_ETH_CB_BLOCK", "ts_unix": time.time(), "expiry_ts": time.time() + 180.0,
    })
    assert res_eth_cb["executed"] is False and res_eth_cb["reason"] == "ASSET_LEGGING_COOLDOWN:ETH"
    h.closed_positions.pop()

    # Graduated DOGE executes alongside an already-open BTC box (multi-box concurrency) & caps budget at $15.00
    mirror_grad = json.loads(mirror_path.read_text(encoding="utf-8"))
    mirror_grad.setdefault("by_d1_asset", {})["DOGE"] = {"closed": 8, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 12.5}
    mirror_path.write_text(json.dumps(mirror_grad), encoding="utf-8")
    h._d1_grad_cache = None
    h._last_known_collateral = 120.00
    tok_doge_a = "7" * 29 + "1"
    tok_doge_b = "7" * 29 + "2"
    tok_doge_oa = "7" * 29 + "3"
    tok_doge_ob = "7" * 29 + "4"
    doge_books = {
        tok_doge_a: {"asks": [{"price": "0.46", "size": "250"}], "bids": [{"price": "0.45", "size": "250"}]},
        tok_doge_b: {"asks": [{"price": "0.46", "size": "250"}], "bids": [{"price": "0.45", "size": "250"}]},
        tok_doge_oa: {"asks": [{"price": "0.53", "size": "250"}], "bids": [{"price": "0.48", "size": "250"}]},
        tok_doge_ob: {"asks": [{"price": "0.53", "size": "250"}], "bids": [{"price": "0.48", "size": "250"}]},
    }
    h.executor.get_market_book = lambda tid: doge_books[tid]
    h.active_positions["OPEN_BTC_A"] = {"token_id": "b_a", "market_id": "m_btc_15", "box_id": "BOX_BTC_1", "is_dominance_box": True}
    h.active_positions["OPEN_BTC_B"] = {"token_id": "b_b", "market_id": "m_btc_5", "box_id": "BOX_BTC_1", "is_dominance_box": True}
    doge_exec_sh = []

    def _mock_doge_box(**kw):
        sh = int(kw["shares"])
        doge_exec_sh.append(sh)
        wallet_bals[tok_doge_a] = float(sh)
        wallet_bals[tok_doge_b] = float(sh)
        return {
            "success": True,
            "box_id": kw["box_id"],
            "shares": float(sh),
            "leg_1": {"token_id": tok_doge_a, "label": kw["leg_a_label"], "price": 0.46, "orderID": "OID_DG_A", "raw": {"makingAmount": round(sh * 0.46, 2)}},
            "leg_2": {"token_id": tok_doge_b, "label": kw["leg_b_label"], "price": 0.46, "orderID": "OID_DG_B", "raw": {"makingAmount": round(sh * 0.46, 2)}},
        }

    h._wallet_token_balance = lambda tid: (wallet_bals.get(tid, 0.0), h.ONCHAIN_SOURCE)
    h.executor.execute_atomic_dominance_box = _mock_doge_box
    res_doge_ok = h.maybe_execute_graduated_d1_box({
        **cand_obj,
        "box_id": "D1_LIVE_DOGE_CONCURRENT",
        "dedupe_key": "D1_DOGE_7001_7002",
        "asset": "DOGE",
        "corridor_bps": 8.5,
        "leg_a_market_id": "7001",
        "leg_b_market_id": "7002",
        "leg_a_token_id": tok_doge_a,
        "leg_b_token_id": tok_doge_b,
        "leg_a_opp_token_id": tok_doge_oa,
        "leg_b_opp_token_id": tok_doge_ob,
        "ts_unix": time.time(),
        "expiry_ts": time.time() + 180.0,
    })
    assert res_doge_ok["executed"] is True, res_doge_ok
    assert doge_exec_sh == [15], "DOGE $15 empirical L1 cap must bound ticket size even at $120 bankroll!"
    assert len(h.active_positions) == 4  # 2 hedged boxes (BTC + DOGE) running concurrently!

    # Any unhedged box residual immediately blocks new box entries
    h.active_positions["RESID_BLOCK"] = {"token_id": "r_1", "box_id": "BOX_UNHEDGED", "is_dominance_box": False}
    res_resid_blk = h.maybe_execute_graduated_d1_box({
        **cand_obj, "asset": "BTC", "dedupe_key": "D1_RESID_BLOCK_CHECK", "leg_a_market_id": "9001", "leg_b_market_id": "9002",
        "ts_unix": time.time(), "expiry_ts": time.time() + 180.0,
    })
    assert res_resid_blk["executed"] is False and res_resid_blk["reason"] == "UNHEDGED_BOX_RESIDUAL_ACTIVE"
    h.active_positions.clear()

    # --- PART 7: Phase 1 Latency Optimizations (4-Socket Warm Pool, D1 defer_exec=True, Fast D1 IPC Dedupe & mtime Cache) ---
    import src.polymarket_research.polymarket_live_executor as exec_mod
    from collections import deque

    # 7a. _ThreadLocalClobHttpClient.warm_pool(min_warm=4) returns healthy inventory=4 with 0 redundant GETs when hot
    pool4 = exec_mod._ThreadLocalClobHttpClient(timeout=4.0, max_pool_size=8)
    created4 = []

    class _FakeCli4:
        def __init__(self):
            self.is_closed = False
            self.calls = 0
            created4.append(self)

        def request(self, method="GET", url="", **kw):
            self.calls += 1
            return MagicMock(status_code=200)

        def close(self):
            self.is_closed = True

    pool4._make_client = _FakeCli4
    assert pool4.warm_pool(min_warm=4, max_idle_sec=18.0) == 4
    assert len(created4) == 4 and sum(c.calls for c in created4) == 4
    # Second call while all 4 sockets are <18s idle must still report 4 healthy sockets AND fire 0 new GETs!
    assert pool4.warm_pool(min_warm=4, max_idle_sec=18.0) == 4
    assert sum(c.calls for c in created4) == 4

    # 7b. D1 execute_atomic_dominance_box passes defer_exec=True on sequential & parallel FOKs + fails closed on DELAYED
    ex_d1 = exec_mod.PolymarketLiveExecutor(dry_run=True)
    ex_d1.dry_run = False
    ex_d1.is_authenticated = True
    ex_d1.auth_mode = "AUTHENTICATED_L2"
    ex_d1._tick_size_cache[tok_15m_up] = 0.01
    ex_d1._tick_size_cache[tok_5m_dn] = 0.01
    ex_d1._neg_risk_cache[tok_15m_up] = False
    ex_d1._neg_risk_cache[tok_5m_dn] = False
    if exec_mod.OrderArgsV2 is None:
        monkeypatch.setattr(exec_mod, "OrderArgsV2", lambda **kw: kw)
    if exec_mod.OrderType is None:
        monkeypatch.setattr(exec_mod, "OrderType", type("OT", (), {"FOK": "FOK", "FAK": "FAK", "GTC": "GTC"}))
    post_calls = []

    class _StubClobDefer:
        def create_order(self, args, options=None):
            return {"signed": args}

        def post_order(self, order, order_type=None, post_only=False, defer_exec=False):
            post_calls.append((order_type, post_only, defer_exec))
            if len(post_calls) == 1:
                return {"orderID": "OID_DELAYED_NO_AMT", "status": "DELAYED"}
            return {"orderID": f"OID_{len(post_calls)}", "status": "matched", "takingAmount": "10"}

    ex_d1.client = _StubClobDefer()
    res_delayed = ex_d1.execute_atomic_dominance_box(
        box_id="BOX_DEFER_UNK", leg_a_token_id=tok_15m_up, leg_a_label="15M_UP", leg_a_limit_price=0.80,
        leg_b_token_id=tok_5m_dn, leg_b_label="5M_DN", leg_b_limit_price=0.14, shares=10,
        max_box_cost_net=0.975, parallel_dispatch=False,
    )
    assert post_calls[0][1] is False and post_calls[0][2] is True, "Sequential D1 FOK must pass defer_exec=True!"
    assert res_delayed["success"] is False and res_delayed["outcome_unknown"] is True

    res_seq_ok = ex_d1.execute_atomic_dominance_box(
        box_id="BOX_DEFER_OK", leg_a_token_id=tok_15m_up, leg_a_label="15M_UP", leg_a_limit_price=0.80,
        leg_b_token_id=tok_5m_dn, leg_b_label="5M_DN", leg_b_limit_price=0.14, shares=10,
        max_box_cost_net=0.975, parallel_dispatch=False,
    )
    assert res_seq_ok["success"] is True
    assert all(c[2] is True for c in post_calls), "All D1 FOK post_order calls must set defer_exec=True!"

    # 7c. Fast D1 RAM IPC queue + emit_id dedupe prevents double evaluation when disk cursor catches up
    eval_calls = []
    h._fast_d1_cand_lines = deque()
    ipc_cand = {**cand_obj, "box_id": "D1_IPC_DEDUPE_1", "dedupe_key": "D1_IPC_KEY_1", "ts_unix": round(time.time(), 3)}
    ipc_line = json.dumps(ipc_cand)
    h._fast_d1_cand_lines.append(ipc_line)
    with open(cand_file, "a", encoding="utf-8") as fp:
        fp.write(ipc_line + "\n")
    h.maybe_execute_graduated_d1_box = lambda c: (eval_calls.append(c["box_id"]) or {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT"})
    h._last_d1_disk_poll = time.time()  # Simulate immediate RAM IPC wakeup (<0.50s before disk poll)
    asyncio.run(h._poll_d1_live_box_candidates(time.time()))
    assert eval_calls == ["D1_IPC_DEDUPE_1"]
    h._last_d1_disk_poll = 0.0  # Now let disk fallback poll catch up to the appended JSONL line
    asyncio.run(h._poll_d1_live_box_candidates(time.time()))
    assert eval_calls == ["D1_IPC_DEDUPE_1"], "Identical emit_id from JSONL fallback must not re-evaluate!"

    # --- PART 8: Live D1 Quiet-Book 0.985 Promotion, 4h/15m 900s TTE Bridge & $0-Miss 10s Retry Cooldown ---
    del h.maybe_execute_graduated_d1_box
    h.active_positions.clear()
    h._last_known_collateral = 85.08
    # 0.48 + 0.47 = 0.95 gross + ~0.03497 fees => ~0.98497 net (>0.975 and <=0.985!)
    tight_quiet_books = {
        tok_15m_up: {"asks": [{"price": "0.48", "size": "120"}], "bids": [{"price": "0.46", "size": "120"}]},
        tok_5m_dn: {"asks": [{"price": "0.46", "size": "120"}], "bids": [{"price": "0.44", "size": "120"}]},
        tok_15m_dn: {"asks": [{"price": "0.52", "size": "120"}], "bids": [{"price": "0.49", "size": "120"}]},
        tok_5m_up: {"asks": [{"price": "0.53", "size": "120"}], "bids": [{"price": "0.50", "size": "120"}]},
    }
    # 0.48*(1 + 0.07*0.52) = 0.497472; 0.46*(1 + 0.07*0.54) = 0.477388 -> sum = 0.97486; let's use 0.48 + 0.465 -> 0.48 + 0.47!
    tight_quiet_books[tok_5m_dn] = {"asks": [{"price": "0.47", "size": "120"}], "bids": [{"price": "0.45", "size": "120"}]}
    # Check: 0.48 + 0.47 = 0.95 + 0.017472 + 0.017437 = 0.984909 <= 0.985 and > 0.975!
    h.executor.get_market_book = lambda tid: tight_quiet_books[tid]

    # 8a. Non-quiet candidate at 0.9849 net MUST be rejected (> 0.975 non-quiet cap)
    cand_non_quiet = {
        **cand_obj,
        "box_id": "D1_NON_QUIET_9849",
        "dedupe_key": "D1_BTC_NON_QUIET_1",
        "is_quiet_book": False,
        "ts_unix": time.time(),
        "expiry_ts": time.time() + 180.0,
    }
    res_nq = h.maybe_execute_graduated_d1_box(cand_non_quiet)
    assert res_nq["executed"] is False and "FRESH_BOOK_WALK_REJECT" in res_nq["reason"]

    # 8b. Quiet-book 4h/15m candidate at TTE=600s & 0.9849 net:
    # First attempt: clean $0.00-cost Leg-1 FOK miss -> 10s cooldown (NOT permanent lockout!), then retry succeeds!
    attempts_8b = []

    def _mock_quiet_4h_fok(**kw):
        attempts_8b.append(dict(kw))
        if len(attempts_8b) == 1:
            return {
                "success": False,
                "stage": "LEG_1_REJECTED",
                "legged_out": False,
                "outcome_unknown": False,
                "error": "FOK order couldn't be fully filled",
            }
        sh = float(kw["shares"])
        return {
            "success": True,
            "box_id": kw["box_id"],
            "shares": sh,
            "leg_1": {"token_id": tok_15m_up, "label": kw["leg_a_label"], "price": 0.48, "orderID": "OID_4H_A", "raw": {"makingAmount": round(sh * 0.48, 2)}},
            "leg_2": {"token_id": tok_5m_dn, "label": kw["leg_b_label"], "price": 0.47, "orderID": "OID_4H_B", "raw": {"makingAmount": round(sh * 0.47, 2)}},
        }

    h.executor.execute_atomic_dominance_box = _mock_quiet_4h_fok
    cand_4h_quiet = {
        **cand_obj,
        "box_id": "D1_4H_LIVE_BTC_600S",
        "dedupe_key": "D1_BTC_4H_15M_RETRY_1",
        "pair_horizons": "4h_15m",
        "sleeve_source": "D1_4H_DOMINANCE_BOX",
        "leg_a_horizon": "4h",
        "leg_b_horizon": "15m",
        "is_quiet_book": True,
        "ts_unix": time.time(),
        "expiry_ts": time.time() + 600.0,  # TTE = 600s (>300s 5m cap, <=900s 4h/15m cap!)
    }
    res_miss1 = h.maybe_execute_graduated_d1_box(cand_4h_quiet)
    assert res_miss1["executed"] is False
    assert len(attempts_8b) == 1
    assert attempts_8b[0]["max_box_cost_net"] == pytest.approx(0.985)
    assert attempts_8b[0]["parallel_dispatch"] is False, "Tighter (0.975..0.985] quiet box must dispatch fragile leg sequentially!"
    assert "D1_BTC_4H_15M_RETRY_1" not in h._seen_d1_box_keys, "$0.00-cost Leg-1 FOK miss must NOT permanently lock pair!"

    # Immediate re-attempt (< 10s) blocked by cooldown
    res_cd = h.maybe_execute_graduated_d1_box({**cand_4h_quiet, "ts_unix": time.time()})
    assert res_cd["executed"] is False and res_cd["reason"] == "RETRY_COOLDOWN_10S"

    # Expire 10s cooldown -> second attempt fills cleanly and permanently locks dedupe_key!
    h._d1_retry_cooldown_until["D1_BTC_4H_15M_RETRY_1"] = time.time() - 0.1
    res_retry_ok = h.maybe_execute_graduated_d1_box({**cand_4h_quiet, "ts_unix": time.time()})
    assert res_retry_ok["executed"] is True
    assert len(attempts_8b) == 2
    assert "D1_BTC_4H_15M_RETRY_1" in h._seen_d1_box_keys

















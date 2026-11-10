#!/usr/bin/env python3
"""
tests/test_v531_qa_audit_fixes.py
=================================
Regression verification suite for v5.3.1 Full-Codebase QA & Forensic Audit fixes:
  1. Share-deducted BUY taker fee math & gross-up parity across:
     - `same_oracle_dominance_box.py` (`walk_equal_shares_dominance_box`, `net_unit_buy_cost`)
     - `tradfi_sports_zero_fee_engine.py` (`_net_ask`)
     - `barrier_onetouch_svi_engine.py` (`detect_barrier_monotonicity_boxes`)
     - `polymarket_live_executor.py` (`execute_atomic_dominance_box` `leg_a_shares`/`leg_b_shares`, `execute_negrisk_subset_convert_arb`)
  2. Frontier v3 & v4 Structural & Oracle Safety Guards:
     - Intra-city derby disambiguation (`LA Clippers` vs `LA Lakers`, `AC Milan` vs `Inter Milan`, `NY Giants` vs `NY Jets`)
     - `AFF1` `"overtime is not included"` veto + subperiod `Race to X` exclusion
     - `SOC2` Extra-Time (`period > 2`) veto on dead-score `NO` locks
     - `NFL_PRP1` non-offensive TD veto + Anytime TD DNP `"50-50"` veto
     - `CRY_INC1` `0s` overhang veto (`cr.close_ts > hr.end_ts`)
  3. Harvester, Executor, WS Streams, Recorder & Governance Plumbing:
     - `_apply_governance_hot_reload` (`max_consecutive_directional_losses` + non-ratcheting `max_price_ceiling` + `"riskless_boxes"` section)
     - `_sign_and_post_async_zero_hop` `_hot_async_inflight` invariance on retry `RequestError`
     - `_wire_submitted_trade_ids` FIFO eviction instead of `.clear()`
     - `PolymarketUserWsCache` `/ws/user` `trade` event idempotent `size_matched` lower-bound & `"xau/usd"` Chainlink mapping
     - `XAU` `USDT-USD` peg / Binance `1m` kline calibration & causal `<= 5s` anchor in `get_delta_basis_100ms`
     - `audit_losing_trades.py` `0`-free-parameter guard enforcement even when `--classification PLUMBING_0_PARAM` is passed explicitly
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections import deque
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import audit_losing_trades as alt
from src.polymarket_research.barrier_onetouch_svi_engine import detect_barrier_monotonicity_boxes
from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.polymarket_terminal_recorder import PolymarketDualFeed1HRecorder
from src.polymarket_research.polymarket_ws_streams import CHAINLINK_SYMBOL_MAP, PolymarketUserWsCache
from src.polymarket_research.riskless_frontier_v3_engine import LiveMultiSportGame, ScoreConfirmationTracker
from src.polymarket_research.riskless_frontier_v4_engine import (
    BarrierRungSpec,
    CryptoCloseRungSpec,
    detect_cry_inc1_binance_inclusion_boxes,
    evaluate_soc2_dead_score_no_locks,
    link_and_parse_soc2_exact_score_lattices,
    parse_affine_game_bundle,
    parse_espn_nfl_summary,
)
from src.polymarket_research.same_oracle_dominance_box import _net_unit_cost_buy, walk_equal_shares_dominance_box
from src.polymarket_research.tradfi_sports_zero_fee_engine import _net_unit_ask


def test_share_deducted_buy_fee_math_and_box_gross_up():
    # At p = 0.50, fr = 0.07, fe = 1.0:
    # fee_ps = 0.07 * 0.25 = 0.0175 => share haircut h = 0.0175 / 0.50 = 0.035
    # Exact cost per 1.00 net delivered share = 0.50 / (1 - 0.035) = 0.5181347... > cash-additive 0.5175!
    exact_cost = 0.50 / (1.0 - 0.035)
    assert math.isclose(_net_unit_cost_buy(0.50, 0.07, 1.0), exact_cost, rel_tol=1e-9)
    assert math.isclose(_net_unit_ask(0.50, 0.07, 1.0), exact_cost, rel_tol=1e-9)

    # Walk 20 net pairs at $0.47 + $0.47 with 7% crypto_fees_v2:
    w = walk_equal_shares_dominance_box(
        [{"price": "0.47", "size": "100"}],
        [{"price": "0.47", "size": "100"}],
        target_budget_usd=20.0,
        fee_rate_a=0.07,
        fee_rate_b=0.07,
        max_box_cost_net=0.985,
    )
    assert w["filled"] is True
    net_sh = int(w["net_paired_shares"])
    assert net_sh >= 5
    # Verify gross shares after 3.71% share-deducted fee deliver >= net_sh on BOTH legs!
    h_47 = 0.07 * (1.0 - 0.47)
    assert math.floor(w["leg_a_gross_shares"] * (1.0 - h_47) * 100.0 + 1e-9) / 100.0 >= net_sh
    assert math.floor(w["leg_b_gross_shares"] * (1.0 - h_47) * 100.0 + 1e-9) / 100.0 >= net_sh

    # Barrier monotonicity box must also reject share-deducted net > cap
    q_edge = [
        {"market_id": "m1", "condition_id": "c1", "strike": 100000.0, "direction": "UP", "yes_token": "by1", "no_token": "bn1", "best_ask_yes": 0.48, "best_ask_no": 0.55, "l1_yes_usd": 50.0, "l1_no_usd": 50.0, "fee_rate": 0.05, "fee_exponent": 1.0},
        {"market_id": "m2", "condition_id": "c2", "strike": 105000.0, "direction": "UP", "yes_token": "by2", "no_token": "bn2", "best_ask_yes": 0.45, "best_ask_no": 0.48, "l1_yes_usd": 50.0, "l1_no_usd": 50.0, "fee_rate": 0.05, "fee_exponent": 1.0},
    ]
    # 2 * (0.48 / (1 - 0.05*0.52)) = 0.9856 > 0.9852 (whereas cash-additive 0.98496 would have falsely passed 0.9852!)
    assert detect_barrier_monotonicity_boxes(q_edge, max_box_cost_net=0.9852) == []


def test_executor_atomic_box_gross_shares_and_inflight_retry_and_fifo(monkeypatch):
    import src.polymarket_research.polymarket_live_executor as ex_mod

    monkeypatch.setattr(ex_mod, "ClobClient", MagicMock(name="OfflineClob"))
    monkeypatch.setattr(ex_mod, "PY_CLOB_AVAILABLE", True)
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
    monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "3")

    ex = PolymarketLiveExecutor(dry_run=False)
    ex.is_authenticated = True
    ex.auth_mode = "LIVE"
    signed_sizes = []
    ex.client = MagicMock()
    ex.client.create_order = lambda args, opts=None: signed_sizes.append((args.token_id, args.size)) or {"tok": args.token_id, "sz": args.size}
    ex.client.post_order = lambda signed, *a, **kw: {"orderID": f"OID_{signed['tok']}", "status": "matched", "takingAmount": str(signed["sz"])}
    ex.get_token_tick_size = lambda tok, **kw: 0.01
    ex.get_token_neg_risk = lambda tok, nr=None: False

    # 10 net pairs @ $0.47 (7% fee -> h=0.0371 -> gross 10.39 shares)
    res = ex.execute_atomic_dominance_box(
        box_id="BOX_GROSS_1",
        leg_a_token_id="TOK_A",
        leg_a_label="15m_UP",
        leg_a_limit_price=0.47,
        leg_b_token_id="TOK_B",
        leg_b_label="5m_DOWN",
        leg_b_limit_price=0.47,
        shares=10.0,
        max_box_cost_net=0.985,
        fee_rate_a=0.07,
        fee_rate_b=0.07,
        parallel_dispatch=False,
        leg_a_shares=10.39,
        leg_b_shares=10.39,
    )
    assert res["success"] is True
    assert res["shares"] == 10.0
    assert res["net_paired_shares"] == 10.0
    assert res["leg_1"]["gross_shares"] == 10.39
    assert res["leg_1"]["entry_fee_asset"] == "SHARES"
    assert ("TOK_A", 10.39) in signed_sizes and ("TOK_B", 10.39) in signed_sizes

    # Verify _wire_submitted_trade_ids uses FIFO eviction rather than .clear() when >2048 trades wire-submit
    ex._sign_and_post_single_hop = None
    with patch.object(
        ex_mod,
        "_sign_and_post_single_hop",
        side_effect=lambda *a, **kw: (a[8].__setitem__("submitted", True) or {"post_resp": {"orderID": "OID_1", "status": "matched", "takingAmount": "10"}, "sign_ms": 0.1, "post_ms": 1.0, "t_post_end": time.perf_counter(), "signed_shares": 10.0}),
    ):
        ex._wire_submitted_trade_ids = {f"T_{i}" for i in range(2048)}
        ex._wire_submitted_trade_order = [f"T_{i}" for i in range(2048)]
        ex.get_market_book = lambda _t: {"asks": [{"price": "0.60", "size": "500"}], "bids": [{"price": "0.59", "size": "500"}]}
        ex.get_collateral_balance = lambda *a, **kw: 500.0
        ex.get_conditional_balance = lambda *a, **kw: 0.0
        ex.execute_snipe_order(
            trade_id="T_2048", token_id="TOK_FIFO", target_token="UP", notional_usd=10.0, target_price=0.60,
            market_fee_rate=0.07, market_fee_exponent=1.0,
        )
        # FIFO eviction drops oldest 512 (T_0..T_511) and preserves recent trades (T_2047, T_2048) instead of wiping to 0!
        assert "T_0" not in ex._wire_submitted_trade_ids
        assert "T_2047" in ex._wire_submitted_trade_ids
        assert "T_2048" in ex._wire_submitted_trade_ids
        assert len(ex._wire_submitted_trade_ids) == 1537

    # Verify _sign_and_post_async_zero_hop keeps _hot_async_inflight == 0 after RequestError on retry
    import httpx
    from types import SimpleNamespace
    ex.order_ladder_cache = SimpleNamespace(
        get_presigned_order=lambda *a, **kw: {"order": {"salt": 1, "maker": "0x22"}, "signature": "0xsig", "orderType": "FAK"},
        get_presigned_order_near=lambda *a, **kw: None,
    )
    ex._fast_l2_api_key = "test_key"
    ex._build_fast_l2_headers = lambda *a, **kw: {"POLY_API_KEY": "test_key"}

    class _FailTwiceClient:
        async def post(self, *a, **kw):
            raise httpx.ConnectError("simulated transient reset")

    ex.get_hot_order_async_client = lambda: _FailTwiceClient()
    ex._retire_hot_async_client = AsyncMock()
    ex._hot_async_inflight = 0
    with patch("py_clob_client_v2.client._is_v2_order", return_value=True), patch(
        "py_clob_client_v2.client.order_to_json_v2", return_value={"order": {"salt": 1}}
    ):
        with pytest.raises(Exception):
            asyncio.run(
                ex._sign_and_post_async_zero_hop(
                    token_id="TOK_Z", price=0.60, size=10.0, side="BUY", order_type="FAK",
                )
            )
    assert ex._hot_async_inflight == 0


def test_frontier_v4_derby_aff1_soc2_nfl_cry_inc1_guards():
    # 1. Intra-city derby disambiguation (Clippers vs Lakers & AC Milan vs Inter Milan)
    ev_derby = {
        "id": "derby_la",
        "slug": "nba-lac-lal-2026-11-08",
        "title": "Los Angeles Clippers vs. Los Angeles Lakers",
        "startTime": "2026-11-08T23:00:00Z",
        "markets": [
            {
                "id": "m_sp_la", "conditionId": "0xc_la", "question": "1H Spread: Los Angeles Clippers (-3.5)",
                "outcomes": json.dumps(["Los Angeles Clippers", "Los Angeles Lakers"]),
                "clobTokenIds": json.dumps(["lac_0", "lal_1"]),
                "sportsMarketType": "first_half_spreads", "line": -3.5,
                "feesEnabled": True, "feeType": "sports_fees_v3", "acceptingOrders": True,
                "endDate": "2026-11-09T04:00:00Z",
            },
            {
                "id": "m_fg_no_ot", "conditionId": "0xc_noot", "question": "Total O/U 224.5",
                "description": "Resolves on regulation score; overtime is not included.",
                "outcomes": json.dumps(["Over", "Under"]),
                "clobTokenIds": json.dumps(["noot_o", "noot_u"]),
                "sportsMarketType": "totals", "line": 224.5,
                "feesEnabled": True, "feeType": "sports_fees_v3", "acceptingOrders": True,
                "endDate": "2026-11-09T04:00:00Z",
            },
            {
                "id": "m_r_2h", "conditionId": "0xc_r2h", "question": "2H Race to 15 Points",
                "outcomes": json.dumps(["Los Angeles Clippers", "Los Angeles Lakers"]),
                "clobTokenIds": json.dumps(["r2h_0", "r2h_1"]),
                "sportsMarketType": "basketball_game_race_to_points",
                "feesEnabled": True, "feeType": "sports_fees_v3", "acceptingOrders": True,
                "endDate": "2026-11-09T04:00:00Z",
            },
        ],
    }
    bundles = parse_affine_game_bundle([ev_derby])
    assert len(bundles) == 1
    bnd = bundles[0]
    assert bnd.away_team != bnd.home_team
    # Regulation-only FG total and 2H subperiod Race-to-15 must both be excluded!
    assert all(m.market_id != "m_fg_no_ot" for m in bnd.markets)
    assert len(bnd.first_passage_markets) == 0

    # 2. SOC2 Extra-Time (`period=3`) must NEVER lock 90m regulation dead scores!
    ex_mkts = []
    idx = 0
    for h in range(6):
        for a in range(6):
            ex_mkts.append({
                "id": f"s_{h}_{a}", "conditionId": f"0xs_{h}_{a}", "questionID": f"0x{'0'*62}{idx:02x}",
                "question": f"AC Milan vs. Inter Milan {h}-{a}?", "groupItemTitle": f"{h}-{a}",
                "outcomes": json.dumps(["Yes", "No"]), "clobTokenIds": json.dumps([f"sy_{h}_{a}", f"sn_{h}_{a}"]),
                "feesEnabled": True, "feeType": "sports_fees_v3", "negRisk": True, "acceptingOrders": True,
                "endDate": "2026-11-10T22:00:00Z",
            })
            idx += 1
    ex_mkts.append({
        "id": "s_oth", "conditionId": "0xs_oth", "questionID": f"0x{'0'*62}24",
        "question": "Any Other Score?", "groupItemTitle": "Any Other",
        "outcomes": json.dumps(["Yes", "No"]), "clobTokenIds": json.dumps(["sy_oth", "sn_oth"]),
        "feesEnabled": True, "feeType": "sports_fees_v3", "negRisk": True, "acceptingOrders": True,
        "endDate": "2026-11-10T22:00:00Z",
    })
    lats = link_and_parse_soc2_exact_score_lattices([{
        "id": "soc_milan", "gameId": "milan_1", "slug": "sea-acm-int-2026-11-10-exact-score",
        "title": "AC Milan vs. Inter Milan - Exact Score", "startTime": "2026-11-10T19:45:00Z",
        "negRisk": True, "negRiskMarketID": "0x" + "cd" * 32, "enableNegRisk": True,
        "negRiskAugmented": False, "markets": ex_mkts,
    }], now_ts=1_793_580_000.0)
    assert "milan_1" in lats
    lat = lats["milan_1"]
    assert lat.home_team != lat.away_team
    tr = ScoreConfirmationTracker()
    et_game = [LiveMultiSportGame(
        sport="SOCCER", game_id="g_milan", start_ts=lat.end_ts, state="in",
        completed=False, is_halftime=False, period=3, clock_sec=300.0,
        home_name="AC Milan", away_name="Inter Milan", home_score=2, away_score=1,
    )]
    evaluate_soc2_dead_score_no_locks(lat, et_game, tr, 1000.0)
    assert evaluate_soc2_dead_score_no_locks(lat, et_game, tr, 1300.0) == []

    # 3. NFL ESPN kickReturnTouchdowns must NOT increment offensive rush_rec_tds
    espn_kr = {
        "header": {"competitions": [{"id": "401", "status": {"period": 2, "type": {"state": "in", "completed": False}}}]},
        "boxscore": {"players": [{"team": {"id": "1"}, "statistics": [{
            "name": "kickReturns",
            "keys": ["kickReturns", "kickReturnYards", "kickReturnTouchdowns"],
            "athletes": [{"athlete": {"displayName": "KaVontae Turpin"}, "didNotPlay": False, "stats": ["2", "98", "1"]}],
        }]}]},
    }
    p_kr = parse_espn_nfl_summary(espn_kr)
    assert p_kr["players"].get("kavontae turpin", {}).get("rush_rec_tds", 0) == 0

    # 4. CRY_INC1 strict 0s overhang: cr.close_ts > hr.end_ts must be vetoed!
    t_end = 1_794_000_000.0
    hr = BarrierRungSpec(
        event_id="e1", series_slug="btc-hit", horizon_group="WEEKLY", asset="BTC",
        market_id="hm1", condition_id="hc1", question="Reach $100k", group_label="↑ $100k",
        strike=100000.0, direction="UP", start_ts=t_end - 86400.0, end_ts=t_end,
        yes_token="hy1", no_token="hn1", fee_rate=0.05, fee_exponent=1.0,
    )
    cr_overhang = CryptoCloseRungSpec(
        event_id="ce1", slug="btc-close", market_id="cm1", condition_id="cc1",
        asset="BTC", strike=100000.0, direction="UP", close_ts=t_end + 60.0,  # 60s AFTER barrier expiry!
        yes_token="cy1", no_token="cn1", fee_rate=0.07, fee_exponent=1.0, question="Above 100k?",
    )
    assert detect_cry_inc1_binance_inclusion_boxes(
        [hr], [cr_overhang], {"cn1": 0.40, "hy1": 0.40}, now_ts=t_end - 3600.0, max_box_cost_net=0.992
    ) == []


def test_ws_trade_event_idempotency_xau_recorder_and_governance_hot_reload(tmp_path, monkeypatch):
    # 1. Chainlink XAU symbol map + User WS trade fill idempotency
    assert CHAINLINK_SYMBOL_MAP.get("xau/usd") == "XAU"
    cache = PolymarketUserWsCache("test_k", "test_s", "test_p")
    cache._connected = True
    cache._seeded_since_connect = True
    cache.process_ws_payload({
        "event_type": "order", "id": "0xORD1", "asset_id": "TOK1",
        "original_size": "20", "size_matched": "0", "price": "0.62", "type": "PLACEMENT",
    })
    # Duplicate trade events with same trade_id must NOT double-count size_matched!
    for _ in range(2):
        cache.process_ws_payload({
            "event_type": "trade", "id": "TRD_1", "status": "MATCHED",
            "maker_orders": [{"order_id": "0xORD1", "matched_amount": "12", "price": "0.62"}],
        })
    snap = cache.get_order_snapshot("0xORD1", max_age_sec=5.0)
    assert snap is not None
    assert snap["size_matched"] == pytest.approx(12.0)

    # Second distinct trade completes the 20-share order -> transitions status to MATCHED
    cache.process_ws_payload({
        "event_type": "trade", "id": "TRD_2", "status": "MATCHED",
        "maker_orders": [{"order_id": "0xORD1", "matched_amount": "8", "price": "0.62"}],
    })
    snap2 = cache.get_order_snapshot("0xORD1", max_age_sec=5.0)
    assert snap2 is not None
    assert snap2["size_matched"] == pytest.approx(20.0)
    assert snap2["status"] == "MATCHED"

    # 2. Recorder XAU volatility prior + causal <= 5s pre-window basis anchor
    monkeypatch.setattr("src.polymarket_research.polymarket_terminal_recorder.DATA_DIR", tmp_path)
    rec = PolymarketDualFeed1HRecorder(asset="XAU")
    assert rec._rolling_sigma_1h == pytest.approx(0.0022)
    now_ns = time.monotonic_ns()
    rec.basis_bps = 10.0
    rec.basis_history = deque([
        (now_ns - 500_000_000, 2.0),   # Causal pre-100ms-window anchor (500ms ago <= 5s)
        (now_ns - 80_000_000, 9.0),    # Already post-shock inside 100ms window!
        (now_ns - 5_000_000, 10.0),    # Current basis -> true 100ms jump is +8.0 bps, NOT +1.0 bps!
    ])
    with patch("time.monotonic_ns", return_value=now_ns):
        assert rec.get_delta_basis_100ms() == pytest.approx(8.0)

    # 3. Harvester governance hot-reload: max_consecutive_directional_losses + non-ratcheting max_price_ceiling
    import src.polymarket_research.polymarket_live_harvester as hv_mod
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "gov_state.json")
    h = PolymarketLiveHarvester(dry_run=True)
    snap_1 = {
        "directional": {"max_taker_price_1h": 0.72, "max_maker_price_1h": 0.74, "min_entry_price": 0.54},
        "risk_controller": {"max_daily_directional_loss_usd": 19.5, "hard_ruin_floor_usd": 45.0, "max_consecutive_directional_losses": 2},
    }
    monkeypatch.setattr(hv_mod.GLOBAL_GOVERNANCE_MANAGER, "maybe_reload", lambda *a, **kw: (True, snap_1))
    assert asyncio.run(h._apply_governance_hot_reload(time.time())) is True
    assert h.risk_controller.max_consecutive_losses == 2
    assert h.max_price_ceiling == pytest.approx(0.74)
    # Raising governance cap back to 0.78 must lift max_price_ceiling back up without one-way downward ratcheting!
    snap_2 = {
        "directional": {"max_taker_price_1h": 0.74, "max_maker_price_1h": 0.78, "min_entry_price": 0.52},
        "risk_controller": {"max_daily_directional_loss_usd": 20.72, "hard_ruin_floor_usd": 42.0, "max_consecutive_directional_losses": 3},
    }
    monkeypatch.setattr(hv_mod.GLOBAL_GOVERNANCE_MANAGER, "maybe_reload", lambda *a, **kw: (True, snap_2))
    assert asyncio.run(h._apply_governance_hot_reload(time.time())) is True
    assert h.risk_controller.max_consecutive_losses == 3
    assert h.max_price_ceiling == pytest.approx(0.78)

    # 4. audit_losing_trades 0-free-parameter guard blocks parameter tuning even with explicit --classification PLUMBING_0_PARAM
    monkeypatch.setattr(alt, "DATA_DIR", tmp_path)
    monkeypatch.setattr(alt, "AUDIT_STATE_FILE", tmp_path / "audit_state.json")
    monkeypatch.setattr(alt, "AUDIT_LEDGER_FILE", tmp_path / "audit_ledger.jsonl")
    with pytest.raises(ValueError, match="GOVERNANCE_VIOLATION"):
        alt.mark_audited(
            trade_id="LIVE_TEST_TUNE_BLOCK",
            verdict="BUG_FIXED",
            notes="Tighten dist_pct threshold from 0.08 to 0.12",
            classification="PLUMBING_0_PARAM",
        )


def test_v540_wfo_parity_unchoke_and_fok_2dec_box_quantizer(tmp_path, monkeypatch):
    """
    Verifies the v5.4.0 Live Unchoke & Purged-WFO Parity fixes across all 3 bottlenecks:
      1. Closed-form FOK BUY 2-decimal USDC makerAmount quantizer (`quantize_fok_buy_box_legs`)
         eliminates HTTP 400 on fractional-fee D1_QUIET_BOOK_BOX (`29.2528 * $0.47 = $13.7488`)
         and sub-cent 0.001-tick (`$0.035`) boxes while preserving <= max_box_cost_net.
      2. `compute_composite_edge_score(..., v5_wfo_parity=True)` strips uncalibrated `e_score<50`,
         `OFI<0.60` (down to WFO `0.20`), and `<25/50ms` MM-reload vetoes while preserving
         `dir_delta_basis` and thin-cushion `obi_l1 < -0.55` ask-wall protection.
      3. `evaluate_shock_and_execute` in `_v5_live_strict` opens 15m Taker Slot #2 up to `$0.82`
         with Z-adaptive FAK headroom (`+1c` for `0.90 <= z < 1.25`, `+2c` capped at `$0.82` for `z >= 1.25`).
      4. `maybe_execute_graduated_d1_box` caps Seed (`$69.61`) `D1_QUIET_BOOK_BOX` <= `$28.00`,
         trims `QUIET_DEPTH_THINNED` down to executable shares instead of aborting, preserves
         `sleeve == "D1_QUIET_BOOK_BOX"`, and allows `<= 24h` `COND1_MACRO_PARTITION_BOX` velocity.
      5. `prewarm_order_ladder` pre-signs `$0.52-$0.82` rungs for 0.33ms O(1) Taker lookup.
    """
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_executor import (
        ExecutionStatus,
        OrderResult,
        quantize_fok_buy_box_legs,
    )
    from src.polymarket_research.polymarket_live_harvester import (
        compute_composite_edge_score,
        passes_capital_velocity_hurdle,
    )

    # 1a. Exact reproduction of live failure D1_LIVE_BTC_1793667600_56890 ($0.47 + $0.47, fr=0.07 -> h=0.0371)
    q_d1 = quantize_fok_buy_box_legs(
        shares_net=28.0,
        px_a=0.47,
        px_b=0.47,
        h_a=0.0371,
        h_b=0.0371,
        max_box_cost_net=0.985,
        max_budget_usd=28.0,
    )
    assert q_d1 is not None
    assert (int(round(q_d1["leg_a_gross_shares"] * 100)) * int(round(0.47 * 10000))) % 10000 == 0
    assert (int(round(q_d1["leg_b_gross_shares"] * 100)) * int(round(0.47 * 10000))) % 10000 == 0
    assert q_d1["eff_box_cost_net"] <= 0.985
    assert q_d1["total_cost_usd"] <= 28.0
    assert q_d1["net_paired_shares"] >= 20.0

    # 1b. Sub-cent 0.001-tick ($0.945 + $0.035, zero fee): step_cents = 200 (2.0 shares) & leg >= $1.00 -> 30.0 shares!
    q_sub = quantize_fok_buy_box_legs(
        shares_net=31.0, px_a=0.945, px_b=0.035, h_a=0.0, h_b=0.0, max_box_cost_net=0.985
    )
    assert q_sub is not None
    assert q_sub["leg_a_gross_shares"] == pytest.approx(30.0)
    assert q_sub["leg_b_gross_shares"] == pytest.approx(30.0)
    assert (int(round(q_sub["leg_a_gross_shares"] * 100)) * 9450) % 10000 == 0
    assert (int(round(q_sub["leg_b_gross_shares"] * 100)) * 350) % 10000 == 0

    # 2. Composite edge score WFO parity vs legacy default
    base_shk = {
        "shock_direction": "BUY",
        "candle_distance_pct": 0.14,
        "shock_ofi": 0.28,
        "shock_volume_100ms": 600_000.0,
        "delta_basis_100ms": 0.5,
        "pre_shock_features_t0": {"UP": {"age_ask_ms": 17.0, "obi_l1": 0.05}},
    }
    assert compute_composite_edge_score(base_shk, v5_wfo_parity=False)["veto"] is True
    res_wfo = compute_composite_edge_score(base_shk, v5_wfo_parity=True)
    assert res_wfo["veto"] is False
    # True WFO-proven vetoes remain active under v5_wfo_parity=True
    assert compute_composite_edge_score({**base_shk, "shock_ofi": 0.15}, v5_wfo_parity=True)["veto"] is True
    assert compute_composite_edge_score({**base_shk, "delta_basis_100ms": -5.0}, v5_wfo_parity=True)["veto"] is True
    assert compute_composite_edge_score(
        {**base_shk, "candle_distance_pct": 0.05, "pre_shock_features_t0": {"UP": {"age_ask_ms": 120.0, "obi_l1": -0.65}}},
        v5_wfo_parity=True,
    )["veto"] is True

    # 3. Live v5.4.0 15m Taker Slot #2 @ $0.80 ask with OFI=0.28, age_ask_ms=17ms, thin bid depth -> Z-adaptive +1c / +2c (cap $0.82)
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "v540_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    monkeypatch.setenv("PM_ENFORCE_V5_TIER_SLOTS", "1")
    monkeypatch.setattr(plh, "read_fast_tick", lambda *a, **kw: None)

    h = PolymarketLiveHarvester(
        dry_run=True, dynamic_sizing=True, hold_to_maturity=False, exit_policy="hold_98",
        ticket_notional=15.0, max_price_ceiling=0.82, max_concurrent=99, allow_cli_concurrency=True,
        allowed_assets={"BTC", "ETH", "SOL"},
    )
    h.dry_run = False
    h.holistic_v5_live_mode = True
    h._startup_reconciled = True
    h.executor.dry_run = False
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.client = object()
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.check_recorder_freshness = lambda *a, **kw: (True, 0.05, "OK")
    h._last_known_collateral = 54.61
    h.high_water_mark_equity = 69.61
    h.executor.get_collateral_balance = lambda *a, **kw: h._last_known_collateral
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    # Existing open 1h position occupies Slot #1 ($15.00), so 15m shock enters Slot #2 on $69.61 Seed equity!
    h.active_positions["SLOT_1_OPEN"] = {
        "trade_id": "SLOT_1_OPEN", "market_id": "1001", "asset": "BTC", "horizon": "1h",
        "token_id": "1" * 30, "notional_usd": 15.0, "remaining_shares": 20.0, "entry_price": 0.75,
    }
    h._update_equity_tier(69.61)

    snipe_calls = []

    async def _fake_snipe_async(**kw):
        snipe_calls.append(kw)
        sh = round(float(kw["notional_usd"]) / 0.80, 2)
        return OrderResult(
            success=True,
            order_id=f"0xFAK_{len(snipe_calls)}",
            trade_id=str(kw.get("trade_id") or f"T_{len(snipe_calls)}"),
            token_id=kw["token_id"],
            target_token=str(kw.get("target_token") or "UP"),
            side="BUY",
            price=0.80,
            size=sh,
            notional_usd=float(kw["notional_usd"]),
            fee_usd=0.25,
            latency_ms=42.0,
            mode="LIVE_CLOB",
            execution_status=ExecutionStatus.FILLED,
            confirmed_onchain=True,
            details={"trade_ids": [f"TF_{len(snipe_calls)}"], "tx_hashes": [f"0xtx_{len(snipe_calls)}"]},
        )

    h.executor.execute_snipe_order_async = _fake_snipe_async
    h.executor.get_order_fill_summary = lambda oid, tok: {
        "matched": 16.0, "avg_price": 0.80, "terminal": True, "resting": False,
        "trade_ids": [f"TF_{oid}"], "tx_hashes": [f"0xtx_{oid}"],
    }
    h.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "0xTP98"}
    now_u = time.time()
    # 3a. Marginal 15m (z ~ 1.12 < 1.20, ask=$0.80 > $0.78) is strictly rejected under v5.4.1!
    shk_15m_marg = {
        "event_id": "V541_15M_MARG_REJECT", "market_id": "2000", "condition_id": "0x2000", "t0_unix": now_u,
        "title": "Ethereum Up or Down - 15m", "asset": "ETH", "horizon": "15m", "shock_direction": "BUY",
        "btc_shock_direction": "BUY", "seconds_to_expiry": 180.0,
        "spot_at_t0": 2501.25, "trigger_price": 2501.25, "candle_open_spot": 2500.0, "twap_60s_open": 2500.0,
        "candle_distance_pct": 0.05, "candle_sigma": 0.0010,
        "shock_volume_100ms": 600_000.0, "shock_ofi": 0.28, "delta_basis_100ms": 0.5,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x2000"},
        "pre_shock_features_t0": {"UP": {
            "token_id": "8" * 30, "best_ask": 0.80, "best_bid": 0.79,
            "raw_top_asks": [[0.80, 120.0]], "raw_top_bids": [[0.79, 8.0]],
            "effective_price_$25": 0.80, "vwap_$25": 0.80, "age_ask_ms": 17.0, "obi_l1": 0.05,
            "age_book_ms": 15.0, "book_timestamp": now_u,
        }},
    }
    asyncio.run(h.evaluate_shock_and_execute(shk_15m_marg))
    assert len(snipe_calls) == 0

    # 3b. Moderate Z (~1.12 in [1.00, 1.25)) on 1h at $0.79 ask -> +1c ($0.80 <= $0.81)!
    shk_z_low = {
        **shk_15m_marg,
        "event_id": "V541_1H_Z112", "market_id": "2001", "condition_id": "0x2001",
        "title": "Ethereum Up or Down - 1h", "horizon": "1h", "seconds_to_expiry": 180.0,
        "candle_sigma": 0.0020,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x2001"},
        "pre_shock_features_t0": {"UP": {
            "token_id": "2" * 30, "best_ask": 0.79, "best_bid": 0.78,
            "raw_top_asks": [[0.79, 120.0]], "raw_top_bids": [[0.78, 8.0]],  # thin bid (8 sh) would fail legacy 2.0x bid gate!
            "effective_price_$25": 0.79, "vwap_$25": 0.79, "age_ask_ms": 17.0, "obi_l1": 0.05,
            "age_book_ms": 15.0, "book_timestamp": now_u,
        }},
    }
    asyncio.run(h.evaluate_shock_and_execute(shk_z_low))
    assert len(snipe_calls) == 1
    assert snipe_calls[0]["target_price"] == pytest.approx(0.80)  # +1c headroom for 1.00 <= z < 1.25

    # 3c. High Z (>= 1.25) on SOL 15m at $0.80 ask -> +2c headroom capped strictly at $0.81 (v5.4.2 WFO cap)!
    _popped_slot1 = h.active_positions.pop("SLOT_1_OPEN", None)
    if isinstance(_popped_slot1, dict) and getattr(h, "_last_known_collateral", None) is not None:
        h._last_known_collateral = round(float(h._last_known_collateral) + float(_popped_slot1.get("notional_usd", 15.0) or 15.0), 2)
    shk_z_high = dict(
        shk_15m_marg,
        event_id="V541_15M_Z220", market_id="2002", condition_id="0x2002",
        asset="SOL", title="Solana Up or Down - 15m",
        spot_at_t0=2503.0, trigger_price=2503.0, candle_distance_pct=0.12,
    )
    shk_z_high["fee_metadata"] = {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x2002"}
    shk_z_high["pre_shock_features_t0"] = {"UP": {
        **shk_15m_marg["pre_shock_features_t0"]["UP"],
        "token_id": "3" * 30, "best_ask": 0.80, "best_bid": 0.79,
        "raw_top_asks": [[0.80, 120.0]], "raw_top_bids": [[0.79, 8.0]],
        "effective_price_$25": 0.80, "vwap_$25": 0.80,
    }}
    asyncio.run(h.evaluate_shock_and_execute(shk_z_high))
    assert len(snipe_calls) == 2
    assert snipe_calls[1]["target_price"] == pytest.approx(0.81)  # Capped strictly at $0.81!

    # 4. D1_QUIET_BOOK_BOX Seed cap (<= $28), QUIET_DEPTH_THINNED share-trimming, 2-dec FOK quantization & COND1 <=24h velocity
    ok_vel, _ = passes_capital_velocity_hurdle(
        collat_usd=69.61, rem_tte_sec=72000.0, box_cost_net=0.985,
        box_type="COMPLETE_SET", sleeve_src="COND1_MACRO_PARTITION_BOX", fast_recycle_eligible=True,
    )
    assert ok_vel is True
    (tmp_path / "alpha124_shadow_state.json").write_text(json.dumps({
        "by_sleeve": {
            "D1_QUIET_BOOK_BOX": {"closed": 15, "wins": 15, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 74.03, "legging_adjusted_pnl_t1000_usd": 74.03, "quarantined": False, "grad8_live_promoted": True},
            "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 33, "wins": 33, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 173.60, "legging_adjusted_pnl_t1000_usd": 173.60, "quarantined": False, "grad8_live_promoted": True},
        },
        "by_d1_asset": {"BTC": {"closed": 20, "wins": 20, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 90.0, "legging_adjusted_pnl_t1000_usd": 90.0, "net_pnl_t1000_usd": 90.0}},
    }), encoding="utf-8")
    h.active_positions.clear()
    h._last_known_collateral = 69.61
    tok_qa, tok_qb, opp_qa, opp_qb = "4" * 32, "5" * 32, "6" * 32, "7" * 32
    # Available L1 depth is 18 shares (< 28 * 1.50 = 42 shares -> triggers QUIET_DEPTH_THINNED trim to floor(18/1.5)=12 net shares!)
    q_books = {
        tok_qa: {"asks": [{"price": "0.47", "size": "18"}], "bids": [{"price": "0.46", "size": "50"}]},
        tok_qb: {"asks": [{"price": "0.47", "size": "18"}], "bids": [{"price": "0.46", "size": "50"}]},
        opp_qa: {"asks": [{"price": "0.54", "size": "50"}], "bids": [{"price": "0.52", "size": "50"}]},
        opp_qb: {"asks": [{"price": "0.54", "size": "50"}], "bids": [{"price": "0.52", "size": "50"}]},
    }
    h.executor.get_market_book = lambda tid: q_books[tid]
    h.executor.prewarm_token_market_cache = lambda **kw: None
    h.executor.invalidate_collateral_cache = lambda: None
    d1_captured = []

    def _fake_q_exec(**kw):
        d1_captured.append(kw)
        sh = float(kw["shares"])
        return {
            "success": True, "shares": sh,
            "leg_1": {"token_id": tok_qa, "price": 0.47, "matched_shares": sh, "orderID": "0xQA"},
            "leg_2": {"token_id": tok_qb, "price": 0.47, "matched_shares": sh, "orderID": "0xQB"},
        }

    h.executor.execute_atomic_dominance_box = _fake_q_exec
    q_res = h.maybe_execute_graduated_d1_box({
        "box_id": "D1_QUIET_TEST", "box_type": "DOMINANCE", "sleeve_source": "D1_QUIET_BOOK_BOX",
        "dedupe_key": "D1Q_BTC_1", "asset": "BTC", "corridor_bps": 15.0,
        "leg_a_strike": 79000.0, "leg_b_strike": 79150.0, "leg_a_side": "UP", "leg_b_side": "DOWN",
        "shares": 60.0, "box_cost_net": 0.978,
        "leg_a_market_id": "8801", "leg_b_market_id": "8802",
        "leg_a_token_id": tok_qa, "leg_b_token_id": tok_qb,
        "leg_a_opp_token_id": opp_qa, "leg_b_opp_token_id": opp_qb,
        "leg_a_limit_price": 0.47, "leg_b_limit_price": 0.47,
        "leg_a_fee_rate": 0.07, "leg_b_fee_rate": 0.07,
        "expiry_ts": time.time() + 240.0, "ts_unix": time.time(),
    })
    assert q_res["executed"] is True
    assert len(d1_captured) == 1
    assert d1_captured[0]["shares"] <= 13.0  # Trimmed from 60 -> <=28 Seed cap -> <=12 depth-trimmed net shares!
    assert (int(round(d1_captured[0]["leg_a_shares"] * 100)) * 4700) % 10000 == 0
    assert (int(round(d1_captured[0]["leg_b_shares"] * 100)) * 4700) % 10000 == 0
    assert any(p.get("sleeve") == "D1_QUIET_BOOK_BOX" for p in h.active_positions.values())

    # 5. Pre-signed ladder includes $0.77-$0.82 rungs
    ex_lad = PolymarketLiveExecutor(dry_run=True)
    ex_lad.dry_run = False
    ex_lad.is_authenticated = True
    ex_lad.client = MagicMock()
    ex_lad.client.create_order.side_effect = lambda oa, opts=None: {"price": oa.price, "size": oa.size}
    ex_lad.prewarm_token_market_cache(token_id="9" * 30, tick_size="0.01", neg_risk=False, fee_rate_bps=700, condition_id="0x99", fee_rate=0.07, fee_exponent=1.0)
    built = ex_lad.prewarm_order_ladder(token_id="9" * 30, ticket_notional=15.0, exact_shares=[20], neg_risk=False, pace_sleep_sec=0.0)
    assert built >= 31
    for px_chk in (0.52, 0.77, 0.78, 0.79, 0.80, 0.81, 0.82):
        assert ex_lad.order_ladder_cache.has_fresh("9" * 30, px_chk, 20.0, tick_size="0.01", neg_risk=False) is True


def test_v541_quadruple_check_forensic_fixes(tmp_path, monkeypatch):
    import math
    import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_executor import (
        ExecutionStatus,
        PolymarketLiveExecutor,
        quantize_fok_buy_box_legs,
        quantize_fok_buy_leg_size,
    )

    # 1. Exact IEEE-754 dyadic-25 + 2-decimal USDC makerAmount invariant across 0.001-tick locks & trap prices
    for px, raw_sz, exp_sz in ((0.995, 25.0, 24.0), (0.993, 25.0, 20.0), (0.992, 26.0, 25.0), (0.025, 20.4, 20.0)):
        q_sz = quantize_fok_buy_leg_size(raw_sz, px, round_up=False, prefer_integer_on_cent_tick=True)
        assert q_sz == pytest.approx(exp_sz)
        c_floor = math.floor(q_sz * 100.0)
        assert c_floor == int(round(q_sz * 100.0))  # Never hits py_clob_client floor(20.4*100)=2039 IEEE-754 bug!
        assert (c_floor * int(round(px * 10000))) % 10000 == 0
    q_box_trap = quantize_fok_buy_box_legs(shares_net=20.4, px_a=0.45, px_b=0.52, max_box_cost_net=0.985)
    assert q_box_trap is not None
    assert math.floor(q_box_trap["leg_a_gross_shares"] * 100.0) == int(round(q_box_trap["leg_a_gross_shares"] * 100.0))

    # 2. Alpha-124 dead-book $0.00-bid rejection on MKR_LOCK1 even when target_bid_px is supplied
    cand_file = tmp_path / "d1_live_cands.jsonl"
    monkeypatch.setattr(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_file)
    dmn = a124_mod.Alpha124ShadowDaemon(single_scan=True)
    ok_dead = dmn.emit_live_single_leg_maker_lock_candidate(
        sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        asset="NFL", dedupe_key="MKR_DEAD_1", pair_dedupe_key="LOCK_DEAD_1",
        token_id="A" * 32, opp_token_id="B" * 32, market_id="77001", condition_id="0x77001",
        side_label="NO", display_label="Backup RB 100+ yds NO",
        bk_win={"bids": [], "asks": [{"price": "0.995", "size": "100"}]},
        bk_opp={"bids": [], "asks": [{"price": "0.01", "size": "100"}]},
        neg_risk=False, close_ts=time.time() + 1800.0, now_ts=time.time(),
        min_resting_bid=0.960, max_resting_bid=0.991, target_bid_px=0.980,
    )
    assert ok_dead is False and not cand_file.exists()

    # 3. Harvester MKR_LOCK1 dead-book veto, <= $22 / 32% cap, <= 1 concurrency cap, and BOND1 preemption
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "v541_harv_state.json")
    (tmp_path / "alpha124_shadow_state.json").write_text(json.dumps({
        "by_sleeve": {
            "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 33, "wins": 33, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 173.60, "legging_adjusted_pnl_t1000_usd": 173.60},
            "BOND1_UMA_RESOLUTION_CARRY": {"closed": 4, "wins": 4, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 8.0, "legging_adjusted_pnl_t1000_usd": 8.0},
            "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": {"closed": 2, "wins": 2, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 3.0, "legging_adjusted_pnl_t1000_usd": 3.0},
        },
    }), encoding="utf-8")
    h = plh.PolymarketLiveHarvester(dry_run=True, allowed_assets={"BTC", "ETH", "SOL"})
    h.dry_run = False
    h._startup_reconciled = True
    h.holistic_v5_live_mode = True
    h._last_known_collateral = 69.61
    h.executor.auth_mode = "LIVE"
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.invalidate_collateral_cache = lambda: None
    h.executor.get_collateral_balance = lambda *a, **kw: 69.61

    wtok, ltok = "C" * 32, "D" * 32
    # 3a. Dead $0.00-bid book is strictly vetoed in harvester too!
    h.executor.get_market_book = lambda tid: ({"bids": [], "asks": [{"price": "0.995", "size": "100"}]} if tid == wtok else {"bids": [], "asks": []})
    dead_res = asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock({
        "box_id": "MKR_DEAD_HARV", "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "dedupe_key": "MLK_DEAD", "pair_dedupe_key": "LK_DEAD",
        "asset": "NFL", "leg_a_market_id": "88001", "leg_a_condition_id": "0x88001",
        "leg_a_token_id": wtok, "leg_a_opp_token_id": ltok, "leg_a_side": "NO",
        "anchor_bid_px": 0.980, "min_resting_bid": 0.960, "max_box_cost_net": 0.991, "max_opp_bid": 0.008,
        "p_model": 0.999, "expiry_ts": time.time() + 1800.0, "ts_unix": time.time(),
    }))
    assert dead_res["executed"] is False and "DUAL_BOOK_CONSENSUS_VETO" in dead_res["reason"]

    # 3b. Live liquid MKR_LOCK1 caps budget <= $22.00 (<= 22 shares @ $0.98) and BOND1 preempts it immediately!
    live_bks = {
        wtok: {"bids": [{"price": "0.980", "size": "100"}], "asks": [{"price": "0.995", "size": "100"}]},
        ltok: {"bids": [{"price": "0.002", "size": "100"}], "asks": [{"price": "0.015", "size": "100"}]},
    }
    h.executor.get_market_book = lambda tid: live_bks[tid]
    posted_mkr = []
    h.executor.post_maker_entry_order = lambda **kw: (
        posted_mkr.append(kw)
        or {"success": True, "orderID": f"0xMLK_{len(posted_mkr)}", "price": kw["price"], "shares": float(int(kw["notional_usd"] // kw["price"]))}
    )
    h.executor.cancel_order = lambda oid: (
        {"is_canceled": True, "outcome": "CANCELED", "matched": 0.0}
        if oid == "0xMLK_1"
        else {"is_canceled": False, "outcome": "FILLED", "matched": 54.0}
    )
    h.executor.get_order_fill_summary = lambda oid, tid: (
        {"matched": 0.0, "avg_price": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True}
        if oid == "0xMLK_1"
        else {"matched": 54.0, "avg_price": 0.990, "cash": 53.46, "fee": 0.0, "terminal": True}
    )
    if isinstance(getattr(h, "risk_config", None), dict):
        monkeypatch.setitem(h.risk_config, "bond1_maker_ttl_sec", 0.25)
    monkeypatch.setitem(plh.RISK_CONFIG, "bond1_maker_ttl_sec", 0.25)

    async def _test_mlk1_cap_and_bond1_preempt():
        t_mlk = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock({
            "box_id": "MKR_LIQ_1", "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "dedupe_key": "MLK_LIQ_1", "pair_dedupe_key": "LK_LIQ_1",
            "asset": "NFL", "leg_a_market_id": "88002", "leg_a_condition_id": "0x88002",
            "leg_a_token_id": wtok, "leg_a_opp_token_id": ltok, "leg_a_side": "NO",
            "anchor_bid_px": 0.980, "min_resting_bid": 0.960, "max_box_cost_net": 0.991, "max_opp_bid": 0.008,
            "p_model": 0.999, "expiry_ts": time.time() + 1800.0, "ts_unix": time.time(),
        }))
        for _ in range(20):
            if len(posted_mkr) >= 1:
                break
            await asyncio.sleep(0.01)
        assert len(posted_mkr) == 1
        assert posted_mkr[0]["notional_usd"] <= 22.50  # <= $22.00 cap (~31.6% of $69.61, NOT $51.99!)
        # Second concurrent MKR_LOCK1 is blocked by MKR_LOCK1_CONCURRENT_CAP_1
        res_mlk2 = await h.maybe_execute_graduated_single_leg_maker_lock({
            "box_id": "MKR_LIQ_2", "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "dedupe_key": "MLK_LIQ_2", "pair_dedupe_key": "LK_LIQ_2",
            "asset": "NFL", "leg_a_market_id": "88003", "leg_a_condition_id": "0x88003",
            "leg_a_token_id": wtok, "leg_a_opp_token_id": ltok, "leg_a_side": "NO",
            "anchor_bid_px": 0.980, "min_resting_bid": 0.960, "max_box_cost_net": 0.991, "max_opp_bid": 0.008,
            "p_model": 0.999, "expiry_ts": time.time() + 1800.0, "ts_unix": time.time(),
        })
        assert res_mlk2["executed"] is False and res_mlk2["reason"] == "MKR_LOCK1_CONCURRENT_CAP_1"
        # Arriving BOND1 preempts MKR_LOCK1 #1 and gets full $59.17 (85% of $69.61) budget!
        res_b1 = await h.maybe_execute_graduated_single_leg_maker_lock({
            "box_id": "BOND1_PREEMPT_MLK", "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "dedupe_key": "BOND1_MKR_88004", "pair_dedupe_key": "BOND1_88004",
            "asset": "SPORTS_TOTALS", "leg_a_market_id": "88004", "leg_a_condition_id": "0x88004",
            "leg_a_token_id": wtok, "leg_a_opp_token_id": ltok, "leg_a_side": "YES",
            "anchor_bid_px": 0.990, "min_resting_bid": 0.940, "max_box_cost_net": 0.994, "max_opp_bid": 0.008,
            "expiry_ts": time.time() + 1800.0, "ts_unix": time.time(),
        })
        out_mlk1 = await t_mlk
        assert out_mlk1["executed"] is False and out_mlk1["reason"] == "BOND1_MAKER_PREEMPTED"
        assert res_b1["executed"] is True
        assert posted_mkr[1]["notional_usd"] >= 53.0

    asyncio.run(_test_mlk1_cap_and_bond1_preempt())

    # 4. 0%-fee WTI CM_B3_PYTH_BARRIER_BOX unwind preserves $0.00 fee even if executor._fee_cache was cleared on restart
    h_zf = plh.PolymarketLiveHarvester(dry_run=True)
    h_zf.executor._fee_cache.clear()
    pos_wti = {
        "trade_id": "BARRIER_WTI_RESTART", "is_dominance_box": True, "box_type": "BARRIER_MONO",
        "sleeve": "CM_B3_PYTH_BARRIER_BOX", "token_id": "E" * 32, "entry_shares": 16.0, "remaining_shares": 16.0,
        "notional_usd": 7.84, "fee_usd": 0.0, "fee_rate_applied": 0.0, "fee_exponent_applied": 1.0,
        "status": ExecutionStatus.POSITION_CONFIRMED,
    }
    h_zf.active_positions["BARRIER_WTI_RESTART"] = pos_wti
    out_uw = h_zf._handle_unwind_response(
        "BARRIER_WTI_RESTART", pos_wti,
        {"success": True, "orderID": "0xWTI_UW", "matched_size": 16.0, "taking_amount": 8.80, "fee_usd": 0.2772, "fee_is_estimated": True},
        16.0, "BARRIER_EARLY_PROFIT_HARVEST", "PARTIAL", 0.55,
    )
    assert out_uw == "CLOSED"
    assert h_zf.closed_positions[-1]["net_pnl_usd"] == pytest.approx(0.96)  # $8.80 - $7.84 - $0.00 fee (zero phantom 7% fee!)


def test_v531_mint_maker_attribution_and_unexecuted_zero_fill_guard(tmp_path, monkeypatch):
    """
    Verifies Gap 1a:
      1. `get_account_fills` / `extract_account_fills` attributes `MatchType.MINT` maker fills
         by `maker_address == funder_address` + `asset_id == token_id` + `side` even when `order_id=None`
         and falls back to asset-unfiltered `get_trades()` when CLOB indexes the MINT trade under the
         opposite outcome token.
      2. Unexecuted `ENTRY_OUTCOME_UNKNOWN` + `inventory_reconciled=False` 0-fill maker/taker positions
         NEVER book `-notional_usd` into `closed_positions` or `non_directional_realized_pnl` even when `won=False`.
      3. Single-leg lock entry persists `trade_ids` and `transactions_hashes`.
    """
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_executor import (
        ExecutionStatus,
        OrderResult,
        PolymarketLiveExecutor,
    )

    funder = "0x11c72ca19854132a4f5433b9aa9746159a4a6354"
    win_tok = "102991566039815573634495392488635789304041380501887303505995890983596993640413"
    opp_tok = "999999999999999999999999999999999999999999999999999999999999999999999999999999"
    mint_tx = "0xf875447100000000000000000000000000000000000000000000000000000067"

    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.funder_address = funder
    ex.signer_address = "0x2222222222222222222222222222222222222222"

    calls = []

    class _FakeClob:
        def get_trades(self, params=None):
            aid = getattr(params, "asset_id", None) if params is not None else None
            calls.append(aid)
            if aid == win_tok:
                # Simulate CLOB indexing MatchType.MINT trade under opposite outcome token
                return []
            return [
                {
                    "id": "MINT_TRADE_67",
                    "type": "MINT",
                    "status": "CONFIRMED",
                    "asset_id": opp_tok,
                    "side": "BUY",
                    "trader_side": "TAKER",
                    "maker_address": "0xdeadbeef00000000000000000000000000000001",
                    "size": "18",
                    "price": "0.008",
                    "match_time": "1793831468",
                    "transaction_hash": mint_tx,
                    "maker_orders": [
                        {
                            "order_id": "0xOTHER_MAKER",
                            "maker_address": "0xdeadbeef00000000000000000000000000000002",
                            "asset_id": opp_tok,
                            "side": "BUY",
                            "matched_amount": "18",
                            "price": "0.008",
                        },
                        {
                            "order_id": "0xOUR_MAKER_67",
                            "maker_address": funder.upper(),
                            "asset_id": win_tok,
                            "side": "BUY",
                            "matched_amount": "18",
                            "price": "0.992",
                            "fee_rate_bps": "0",
                        },
                    ],
                }
            ]

    ex.is_authenticated = True
    ex.client = _FakeClob()
    res_fills = ex.get_account_fills(token_id=win_tok, after_ts=1793831400, side="BUY", order_id=None)
    assert calls == [win_tok, None]
    assert res_fills is not None and len(res_fills) == 1
    assert res_fills[0]["size"] == pytest.approx(18.0)
    assert res_fills[0]["cash"] == pytest.approx(17.856)
    assert res_fills[0]["price"] == pytest.approx(0.992)
    assert res_fills[0]["transaction_hash"] == mint_tx
    assert res_fills[0]["trade_id"] == "MINT_TRADE_67"

    # Empty trades edge case returns clean empty list []
    ex.client = type("_EmptyClob", (), {"get_trades": lambda self, params=None: []})()
    empty_fills = ex.get_account_fills(token_id=win_tok, after_ts=1793831400, side="BUY", order_id=None)
    assert empty_fills == []

    # 2. Harvester unexecuted 0-fill ENTRY_OUTCOME_UNKNOWN firewall on won=False AND _close_position
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_state.json")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.executor.client = object()
    h.executor.is_authenticated = True
    h.risk_controller.non_directional_realized_pnl = 9.47
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.get_account_fills = lambda *a, **kw: []
    h.executor.get_order_fill_summary = lambda *a, **kw: None
    h.executor.find_redemption_payouts = lambda *a, **kw: []
    h._resolve_lifecycle = lambda *a, **kw: False

    tid_44 = "MKR_LOCK1_LIVE_SPORTS_MONEYLINE_1793692777_61815"
    h.active_positions[tid_44] = {
        "trade_id": tid_44,
        "market_id": "61815",
        "condition_id": "0x" + "44" * 32,
        "token_id": "4" * 40,
        "target_token": "YES",
        "asset": "SPORTS_MONEYLINE",
        "is_dominance_box": True,
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "entry_price": 0.96,
        "entry_shares": 52.70,
        "remaining_shares": 52.70,
        "notional_usd": 50.592,
        "remaining_cost_basis": 50.592,
        "fee_usd": 0.0,
        "entry_order_id": "0xEXPIRED_NO_FILL_44",
        "status": "ENTRY_OUTCOME_UNKNOWN",
        "exit_order_status": "RESOLUTION_CANCEL_UNCONFIRMED",
        "inventory_reconciled": False,
        "entry_ts": 1793690000.0,
    }
    # Resolve with won=False ("NO" wins while target_token="YES") -> MUST close as NOT_EXECUTED with $0.00 PnL!
    asyncio.run(h._apply_market_resolution(tid_44, h.active_positions[tid_44], "NO"))
    assert tid_44 not in h.active_positions
    rec_44 = h.closed_positions[-1]
    assert rec_44["status"] == "NOT_EXECUTED"
    assert rec_44["close_reason"] == "UNFILLED_MAKER_EXPIRED_NO_FILL"
    assert rec_44["net_pnl_usd"] == pytest.approx(0.0)
    assert rec_44.get("realized_pnl_usd", 0.0) == pytest.approx(0.0)
    assert rec_44["notional_usd"] == pytest.approx(0.0)
    assert rec_44["remaining_cost_basis"] == pytest.approx(0.0)
    assert h.risk_controller.non_directional_realized_pnl == pytest.approx(9.47)

    # Direct _close_position firewall check for ENTRY_OUTCOME_UNKNOWN 0-fill
    tid_44b = "MKR_LOCK1_DIRECT_CLOSE_GUARD"
    h.active_positions[tid_44b] = {
        "trade_id": tid_44b, "token_id": "5" * 40, "target_token": "YES",
        "is_dominance_box": True, "box_type": "SINGLE_LEG_MAKER_LOCK",
        "entry_shares": 20.0, "remaining_shares": 20.0, "notional_usd": 19.20, "remaining_cost_basis": 19.20,
        "status": "ENTRY_OUTCOME_UNKNOWN", "inventory_reconciled": False,
    }
    h._close_position(tid_44b, h.active_positions[tid_44b], ExecutionStatus.SETTLED, "MARKET_RESOLVED_LOSS", won=False)
    assert h.closed_positions[-1]["status"] == "NOT_EXECUTED"
    assert h.closed_positions[-1]["net_pnl_usd"] == pytest.approx(0.0)
    assert h.risk_controller.non_directional_realized_pnl == pytest.approx(9.47)

    # Contrast: genuinely filled position (inventory_reconciled=True) that loses MUST book real loss
    tid_real = "REAL_CONFIRMED_LOSS"
    h.active_positions[tid_real] = {
        "trade_id": tid_real, "condition_id": "0x" + "55" * 32, "token_id": "6" * 40, "target_token": "YES",
        "is_dominance_box": True, "box_type": "SINGLE_LEG_LOCK",
        "entry_shares": 18.0, "remaining_shares": 18.0, "notional_usd": 17.856, "remaining_cost_basis": 17.856,
        "status": ExecutionStatus.POSITION_CONFIRMED, "inventory_reconciled": True,
    }
    asyncio.run(h._apply_market_resolution(tid_real, h.active_positions[tid_real], "NO"))
    assert h.closed_positions[-1]["net_pnl_usd"] == pytest.approx(-17.86)
    assert h.risk_controller.non_directional_realized_pnl == pytest.approx(9.47 - 17.86)

    # 3. _finish_single_leg_lock persists trade_ids and transactions_hashes
    res_1leg = OrderResult(
        success=True, order_id="0xORD_1L", trade_id="SLK_PERSIST_1", token_id=win_tok,
        target_token="YES", side="BUY", price=0.985, size=18.0, notional_usd=17.73,
        fee_usd=0.0, latency_ms=15.0, mode="LIVE_CLOB", execution_status=ExecutionStatus.FILLED,
        details={"trade_ids": ["MINT_TRADE_67"], "transactions_hashes": [mint_tx]},
    )
    h._last_known_collateral = 100.0
    h.executor.execute_snipe_order = lambda **kw: res_1leg
    bk_win_1l = {"asks": [{"price": 0.985, "size": 25.0}], "bids": [{"price": 0.980, "size": 25.0}]}
    bk_opp_1l = {"asks": [{"price": 0.05, "size": 25.0}], "bids": [{"price": 0.004, "size": 20.0}]}
    h.executor.get_market_book = lambda tk: bk_win_1l if tk == win_tok else bk_opp_1l
    now_1l = time.time()
    cand_1leg = {
        "box_id": "SLK_PERSIST_1", "box_type": "SINGLE_LEG_LOCK", "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
        "asset": "NBA", "dedupe_key": "BOND1_991", "pair_dedupe_key": "BOND1_991",
        "leg_a_token_id": win_tok, "leg_a_opp_token_id": opp_tok, "leg_a_side": "YES",
        "leg_a_market_id": "991", "leg_a_condition_id": "0x" + "99" * 32,
        "leg_a_fee_rate": 0.0, "leg_a_fee_exponent": 1.0, "leg_a_neg_risk": False, "leg_a_tick_size": 0.001,
        "max_box_cost_net": 0.992, "max_opp_bid": 0.008, "hold_to_maturity": True,
        "ts_unix": now_1l, "expiry_ts": now_1l + 1800.0,
    }
    out_1leg = h._finish_single_leg_lock(
        cand_1leg, "BOND1_UMA_RESOLUTION_CARRY", win_tok, "991", "BOND1_991", {}, now_1l, {},
    )
    assert out_1leg["executed"] is True
    assert h.active_positions["SLK_PERSIST_1"]["transactions_hashes"] == [mint_tx]
    assert h.active_positions["SLK_PERSIST_1"]["trade_ids"] == ["MINT_TRADE_67"]


def test_v531_autoredeemer_receipt_decoding_and_rpc_403_fallback(monkeypatch):
    """
    Verifies Gap 1b against the exact Polygon `AutoRedeemer` receipt payload of `#67`
    (tx `0xa806795a06fcb654e5369d8269704cc0f8c15db9e4352ff1289af3172c336a3d`, `LOG[10]`,
    `data = 0x...0112a880` = $18.00 USDC.e) plus `AUTO_REDEEM_NEGRISK_TOPIC0` and `_rpc`
    fallback to `https://polygon-bor-rpc.publicnode.com` on HTTP 403.
    """
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    funder = "0x013a2474454fbd8738cff6a7f204ef1bc377f4e9"
    cond_67 = "0x76199f57cefa19c432f09e23baea25b6b7180b598ef06a0c17a95ab49effcb7c"
    tx_67 = "0xa806795a06fcb654e5369d8269704cc0f8c15db9e4352ff1289af3172c336a3d"
    pad_funder = "0x" + "0" * 24 + funder[2:].lower()
    # Exact on-chain LOG[10] data word: uint256(18_000_000) == 0x0112a880 ($18.00 USDC.e)
    data_67 = "0x" + f"{0x0112a880:064x}"

    log_67 = {
        "address": PolymarketLiveExecutor.AUTOREDEEMER_ADDRESS,
        "topics": [PolymarketLiveExecutor.AUTO_REDEEM_CTF_TOPIC0, pad_funder, cond_67],
        "data": data_67,
        "transactionHash": tx_67,
        "blockNumber": hex(96_750_702),
        "logIndex": "0xa",
    }

    ex = PolymarketLiveExecutor(dry_run=True)
    ex.funder_address = funder

    # NegRisk AutoRedeemer event variant (also uint256 payout in data[0:64])
    cond_nr = "0x" + "ab" * 32
    data_nr = "0x" + f"{25_500_000:064x}"
    log_nr = {
        "address": PolymarketLiveExecutor.AUTOREDEEMER_ADDRESS,
        "topics": [PolymarketLiveExecutor.AUTO_REDEEM_NEGRISK_TOPIC0, pad_funder, cond_nr],
        "data": data_nr,
        "transactionHash": "0x" + "77" * 32,
        "blockNumber": hex(96_750_710),
        "logIndex": "0x1",
    }
    decoded_nr = ex.parse_payout_redemption_logs([log_nr], cond_nr)
    assert len(decoded_nr) == 1 and decoded_nr[0]["payout_usd"] == pytest.approx(25.5)

    # Full RPC fallback test: custom POLYGON_RPC_URL returns HTTP 403 -> falls back to polygon-bor-rpc.publicnode.com
    monkeypatch.setenv("POLYGON_RPC_URL", "https://custom-403-rpc.example.invalid")
    rpc_urls_hit = []
    getlogs_calls = []

    class _FakeResp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class _FakeSession:
        def post(self, url, json=None, timeout=4.0):
            rpc_urls_hit.append(url)
            if "custom-403-rpc" in url:
                return _FakeResp(403, {"error": "forbidden"})
            method = (json or {}).get("method")
            if method == "eth_blockNumber":
                return _FakeResp(200, {"jsonrpc": "2.0", "id": 1, "result": hex(96_765_000)})
            if method == "eth_getLogs":
                flt = (json or {}).get("params", [{}])[0]
                getlogs_calls.append(flt)
                if (
                    str(flt.get("address", "")).lower() == PolymarketLiveExecutor.AUTOREDEEMER_ADDRESS.lower()
                    and int(flt["fromBlock"], 16) <= 96_750_702 <= int(flt["toBlock"], 16)
                ):
                    return _FakeResp(200, {"jsonrpc": "2.0", "id": 1, "result": [log_67]})
                return _FakeResp(200, {"jsonrpc": "2.0", "id": 1, "result": []})
            return _FakeResp(200, {"jsonrpc": "2.0", "id": 1, "result": None})

    ex._sync_session = _FakeSession()
    ex.dry_run = False
    events = ex.find_redemption_payouts(cond_67)
    assert any("custom-403-rpc" in u for u in rpc_urls_hit)
    assert any("polygon-bor-rpc.publicnode.com" in u for u in rpc_urls_hit)
    # Verify default 15,000-block lookback span and contract query sequence (CTF -> NegRisk -> AutoRedeemer per chunk)
    queried_addrs = [str(c.get("address", "")).lower() for c in getlogs_calls[:3]]
    assert queried_addrs == [
        PolymarketLiveExecutor.CTF_ADDRESS.lower(),
        PolymarketLiveExecutor.NEG_RISK_ADAPTER_ADDRESS.lower(),
        PolymarketLiveExecutor.AUTOREDEEMER_ADDRESS.lower(),
    ]
    total_span = int(getlogs_calls[-1]["toBlock"], 16) - int(getlogs_calls[0]["fromBlock"], 16)
    assert total_span == 15000
    assert events is not None and len(events) == 1
    assert events[0]["payout_usd"] == pytest.approx(18.0)
    assert events[0]["transaction_hash"] == tx_67
    assert events[0]["block_number"] == 96_750_702


def test_v531_polybolt_v2_chainlink_stream_and_recorder_fast_tick(tmp_path, monkeypatch):
    """
    Verifies Gap 2a:
      1. `PolymarketChainlinkLiveStream` authenticates against PolyBolt V2 using nested L2 `auth`,
         ingests 120s 1Hz `snapshot` + live 1Hz `tick` frames with unscaled decimal `full_accuracy_value`,
         ignores `dropped > 0` frames, and warms `get_rolling_twap_60s` immediately at `t=0ms`.
      2. `PolymarketDualFeed1HRecorder.build_fast_tick_snapshot` emits `chainlink_source="polybolt_v2"`,
         `chainlink_spot`, `chainlink_proxy_spot`, and warm 1Hz `chainlink_twap_60s`.
      3. Missing L2 credentials cleanly return `None` from `resolve_polybolt_l2_creds` so RTDS fallback activates.
    """
    import websockets
    from aiohttp import web
    import src.polymarket_research.polymarket_ws_streams as pws
    import src.polymarket_research.polymarket_terminal_recorder as ptr

    async def _run_polybolt_e2e():
        auth_frames = []
        sub_frames = []
        t0_ms = int(time.time() * 1000)

        async def _ws_handler(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            msg_auth = await ws.receive_json()
            auth_frames.append(msg_auth)
            await ws.send_json({"op": "authed", "rid": msg_auth.get("rid", "a1")})
            for _ in range(len(pws.POLYBOLT_CRYPTO_SYMBOLS)):
                sub = await ws.receive_json()
                sub_frames.append(sub)
                sym = sub["subscriptions"][0]["filter"]["symbol"]
                await ws.send_json({"op": "subscribed", "rid": sub["rid"], "channel": "price.crypto"})
                if sym.lower() == "btcusd":
                    pts = [
                        {"timestamp": t0_ms - (65 - i) * 1000, "value": 80500.25, "full_accuracy_value": "80500.250000000000"}
                        for i in range(65)
                    ]
                    await ws.send_json({
                        "v": 2, "channel": "price.crypto", "snapshot": True,
                        "payload": {"symbol": "btcusd", "source": "chainlink", "data": pts},
                    })
                    # Dropped > 0 frame MUST be rejected
                    await ws.send_json({
                        "v": 2, "channel": "price.crypto", "dropped": 2,
                        "payload": {"symbol": "btcusd", "timestamp": t0_ms - 500, "full_accuracy_value": "99999.99"},
                    })
                    # Valid live 1Hz tick
                    await ws.send_json({
                        "v": 2, "channel": "price.crypto", "dropped": 0,
                        "payload": {"symbol": "btcusd", "source": "chainlink", "timestamp": t0_ms, "full_accuracy_value": "80560.250000000000"},
                    })
            await asyncio.sleep(0.25)
            await ws.close()
            return ws

        app = web.Application()
        app.router.add_get("/ws", _ws_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]

        ws_test_url = f"ws://127.0.0.1:{port}/ws"
        monkeypatch.setattr(pws, "POLYBOLT_V2_WS_URL", ws_test_url)
        stop_flag = False
        stream = pws.PolymarketChainlinkLiveStream(
            ws_url=ws_test_url, prefer_polybolt_v2=True, l2_creds=("pb_k", "pb_s", "pb_p")
        )
        task = asyncio.create_task(
            stream._stream_polybolt_v2_once(websockets, ("pb_k", "pb_s", "pb_p"), stop_check=lambda: stop_flag)
        )
        try:
            for _ in range(40):
                if stream.get_latest_spot("BTC") == pytest.approx(80560.25):
                    break
                await asyncio.sleep(0.02)
            assert auth_frames and auth_frames[0]["op"] == "auth"
            assert auth_frames[0]["auth"] == {"apiKey": "pb_k", "secret": "pb_s", "passphrase": "pb_p"}
            assert stream.active_source == "polybolt_v2"
            assert stream._dropped_frames == 2
            assert stream.get_latest_spot("BTC") == pytest.approx(80560.25)
            twap = stream.get_rolling_twap_60s("BTC", max_age_sec=10.0)
            assert twap is not None and 80500.0 < twap < 80561.0

            monkeypatch.setattr(ptr, "DATA_DIR", tmp_path)
            rec = ptr.PolymarketDualFeed1HRecorder(asset="BTC")
            rec.chainlink_stream = stream
            rec.spot_price = 80580.0
            rec.spot_price_ts = time.time()
            snap = rec.build_fast_tick_snapshot()
            assert snap["chainlink_source"] == "polybolt_v2"
            assert snap["chainlink_basis_anchored"] is True
            assert snap["chainlink_spot"] == pytest.approx(80560.25)
            assert snap["chainlink_proxy_spot"] == pytest.approx(80560.25)
            assert snap["chainlink_twap_60s"] == pytest.approx(twap, rel=1e-6)
        finally:
            stop_flag = True
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await runner.cleanup()

    asyncio.run(_run_polybolt_e2e())

    # RTDS credential fallback check when no API key or private key is configured
    for k in (
        "POLY_API_KEY", "CLOB_API_KEY", "POLY_SECRET", "POLY_API_SECRET", "CLOB_SECRET",
        "POLY_PASSPHRASE", "POLY_API_PASSPHRASE", "CLOB_PASS_PHRASE",
        "POLYGON_PRIVATE_KEY", "POLY_PRIVATE_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("PM_DISABLE_POLYBOLT_CRED_DERIVE", "1")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: False)
    pws._CACHED_POLYBOLT_CREDS = None
    assert pws.resolve_polybolt_l2_creds() is None


def test_v531_clob_ws_tick_size_change_sub_ms_sync(tmp_path):
    """
    Verifies Gap 2b:
      1. `PolymarketClobMarketWsTracker` handles `tick_size_change` (`0.01 -> 0.001`) in sub-millisecond
         memory and pushes directly into `PolymarketLiveExecutor.update_ws_tick_size` (`_tick_size_cache`).
      2. `emit_single_leg_maker_lock_cand_impl` immediately uses `_token_tick_sizes[tok] == "0.001"`
         to emit `leg_a_tick_size == 0.001` and step `resting_bid` by `+$0.001`.
    """
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker
    from src.polymarket_research.riskless_protocol_v2_expansion import emit_single_leg_maker_lock_cand_impl

    ex = PolymarketLiveExecutor(dry_run=True)
    tok = "777777777777777777777777777777777777777777"
    opp = "888888888888888888888888888888888888888888"
    ex._tick_size_cache[tok] = 0.01

    cb_events = []
    tracker = PolymarketClobMarketWsTracker(
        on_tick_size_change=lambda aid, tk: (cb_events.append((aid, tk)), ex.update_ws_tick_size(aid, tk))
    )
    tracker.set_desired_tokens([tok])
    tracker.process_ws_payload({"event_type": "book", "asset_id": tok, "tick_size": "0.01", "bids": [{"price": "0.95", "size": "50"}], "asks": [{"price": "0.96", "size": "50"}]})
    assert tracker.get_tick_size(tok) == pytest.approx(0.01)
    cb_events.clear()
    tracker.process_ws_payload({"event_type": "tick_size_change", "asset_id": tok, "old_tick_size": "0.01", "new_tick_size": "0.001"})
    assert cb_events == [(tok, pytest.approx(0.001))]
    assert tracker.get_tick_size(tok) == pytest.approx(0.001)
    assert ex._tick_size_cache[tok] == pytest.approx(0.001)
    assert ex.get_token_tick_size(tok) == pytest.approx(0.001)

    cand_file = tmp_path / "cands.jsonl"
    state_file = tmp_path / "st.json"

    class _MockDaemon:
        single_scan = True
        _last_d1_live_emit_ts = {}
        _token_tick_sizes = {tok: "0.001"}

    ok = emit_single_leg_maker_lock_cand_impl(
        _MockDaemon(),
        sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        asset="NBA",
        dedupe_key="MKR_TK_TEST",
        pair_dedupe_key="PAIR_TK_TEST",
        token_id=tok,
        opp_token_id=opp,
        market_id="55101",
        condition_id="0x" + "51" * 32,
        side_label="YES",
        display_label="Celtics vs Knicks",
        bk_win={"minimum_tick_size": "0.01", "bids": [{"price": "0.95", "size": "40"}], "asks": [{"price": "0.96", "size": "40"}]},
        bk_opp={"bids": [{"price": "0.004", "size": "20"}], "asks": [{"price": "0.05", "size": "40"}]},
        neg_risk=False,
        close_ts=time.time() + 1800.0,
        now_ts=time.time(),
        min_resting_bid=0.940,
        max_resting_bid=0.991,
        min_maker_edge=0.006,
        max_opp_bid=0.008,
        hold_to_maturity=True,
        p_model=0.999,
        target_bid_px=None,
        maker_rebate_ps=0.0,
        extract_best_bid_fn=lambda bids: (float(bids[0]["price"]), float(bids[0]["price"]) * float(bids[0]["size"])) if bids else (0.0, 0.0),
        cand_file=cand_file,
        default_cand_path=tmp_path / "default_cands.jsonl",
        state_file=state_file,
        default_state_path=state_file,
    )
    assert ok is True
    emitted = json.loads(cand_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert emitted["leg_a_tick_size"] == pytest.approx(0.001)
    assert emitted["anchor_bid_px"] == pytest.approx(0.951)


def test_v531_dispute_guards_and_weather_station_oracle_regimes():
    """
    Verifies Gap 2c:
      1. `classify_market_rule_dispute_risk` & `passes_uma_bond_dispute_guard` enforce `proposal_age_sec >= 1800`
         on `BOND1` and `veto_pre_final_clinch=True` on pre-final `MKR_LOCK1` for walkover/forfeit/retirement/LFMP
         and Soccer 90m regulation markets, without false-positiving on standard NBA games or career-retirement props.
      2. `classify_weather_station_oracle_rule` + `detect_w_prune1_metar_slate_arb` distinguish
         `WUNDERGROUND_INTEGER_METAR` (`EGLC`, `LFPG`, `RKSI`, `SBGR`), `US_ASOS_01C_BEFORE_ROUNDING` (`KLGA`),
         `US_NWS_CLI_01C_BEFORE_ROUNDING` (vetoing `W_SOLAR1_POST_2351_LOCK`), and `HKO_OFFICIAL_01C`.
    """
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        classify_market_rule_dispute_risk,
        classify_weather_station_oracle_rule,
        compute_running_metar_extrema,
        detect_w_prune1_metar_slate_arb,
        passes_uma_bond_dispute_guard,
    )

    # 1a. Soccer 90m regulation market
    soc_mkt = {
        "question": "Will Arsenal win vs Chelsea?",
        "description": "This market refers only to the outcome within the first 90 minutes of regular play plus stoppage time, excluding extra time and penalties.",
    }
    r_soc = classify_market_rule_dispute_risk(soc_mkt)
    assert r_soc["dispute_risk"] is True and r_soc["veto_pre_final_clinch"] is True
    assert passes_uma_bond_dispute_guard(soc_mkt, {"proposal_age_sec": 1200.0}) is False
    assert passes_uma_bond_dispute_guard(soc_mkt, {"eff_liveness_sec": 7200.0, "rem_challenge_sec": 6000.0}) is False
    assert passes_uma_bond_dispute_guard(soc_mkt, {"proposal_age_sec": 1805.0}) is True

    # 1b. Tennis/UFC/Esports walkover / mid-match retirement / LFMP
    ten_mkt = {"question": "Alcaraz vs Sinner", "rules_text": "If a player retires mid-match or walkover occurs, resolves 50-50 or LFMP."}
    assert classify_market_rule_dispute_risk(ten_mkt)["dispute_risk"] is True
    assert passes_uma_bond_dispute_guard(ten_mkt, {"proposal_age_sec": 600.0}) is False
    assert passes_uma_bond_dispute_guard(ten_mkt, {"proposal_age_sec": 1800.0}) is True

    # 1c. Standard NBA & career-retirement prop -> NO false-positive veto
    nba_mkt = {"question": "Lakers vs Warriors", "description": "Resolves to the official NBA game winner including overtime."}
    career_mkt = {"question": "Will Novak Djokovic announce his retirement before 2027?", "description": "Official announcement."}
    assert classify_market_rule_dispute_risk(nba_mkt)["dispute_risk"] is False
    assert classify_market_rule_dispute_risk(career_mkt)["dispute_risk"] is False
    assert passes_uma_bond_dispute_guard(nba_mkt, {"proposal_age_sec": 60.0}) is True

    # 2a. International Wunderground integer METAR stations (EGLC, LFPG, RKSI, SBGR) -> exact integer C (unc_c=0.0)
    for st in ("EGLC", "LFPG", "RKSI", "SBGR"):
        assert classify_weather_station_oracle_rule(st, unit="C")["oracle_regime"] == "WUNDERGROUND_INTEGER_METAR"
    ext_eglc = compute_running_metar_extrema(
        ["METAR EGLC 041450Z 24008KT 9999 FEW035 14/08 Q1018"], unit="C", station_icao="EGLC"
    )
    assert ext_eglc is not None
    assert ext_eglc["confirmed_running_high_floor"] == 14 and ext_eglc["confirmed_running_high_ceil"] == 14

    # 2b. US ASOS station KLGA (even with wunderground URL in rules) preserves 0.1C T-group BEFORE rounding
    klga_rules = "Resolves via https://www.wunderground.com/history/daily/us/ny/new-york-city/KLGA"
    assert classify_weather_station_oracle_rule("KLGA", unit="F", rules_text=klga_rules)["oracle_regime"] == "US_ASOS_01C_BEFORE_ROUNDING"
    # T02060100 == 20.6C == 69.08F -> 69F (whereas body 21/10 would wrongly give 70F!)
    ext_klga = compute_running_metar_extrema(
        ["METAR KLGA 041951Z 18010KT 10SM CLR 21/10 A3002 RMK AO2 SLP165 T02060100"],
        unit="F", station_icao="KLGA", rules_text=klga_rules,
    )
    assert ext_klga is not None
    assert ext_klga["confirmed_running_high_floor"] == 69 and ext_klga["confirmed_running_high_ceil"] == 69

    # 2c. US NWS CLI rule allows dead NO pruning while blocking W_SOLAR1_POST_2351_LOCK
    nws_rules = "Resolves to the NWS Daily Climate Report (NWS CLI) for Central Park."
    brackets = [
        {"condition_id": "c_68", "low": 67, "high": 68, "yes_token_id": "y68", "no_token_id": "n68", "yes_ask": 0.02, "yes_ask_size": 30.0, "no_ask": 0.985, "no_ask_size": 30.0},
        {"condition_id": "c_69", "low": 69, "high": 70, "yes_token_id": "y69", "no_token_id": "n69", "yes_ask": 0.96, "yes_ask_size": 30.0, "no_ask": 0.05, "no_ask_size": 30.0},
    ]
    hits_nws = detect_w_prune1_metar_slate_arb(
        brackets,
        ["METAR KLGA 041951Z 18010KT 10SM CLR 21/10 A3002 RMK AO2 SLP165 T02060100"],
        station_icao="KLGA",
        unit="F",
        metric="HIGH",
        local_hour_minute=(23, 55),
        rules_text=nws_rules,
    )
    sleeves_nws = {h["sleeve"] for h in hits_nws}
    assert "W_PRUNE1_DEAD_NO_BOND" in sleeves_nws
    assert "W_SOLAR1_POST_2351_LOCK" not in sleeves_nws


def test_v531_resolved_market_purged_live_zombie_order_reconciled(tmp_path, monkeypatch):
    """
    Verifies live production edge case (6569621 / 0x991211b7...):
      When Polymarket's matching engine purges a resting GTC order upon market resolution
      (`not_canceled_reason = "order can't be found - already canceled or matched"`), while
      CLOB read-replicas still return `status="LIVE", size_matched="0"`, `_resolve_unknown_entry`
      proves `RESOLVED_MARKET_PURGED_ORDER_ZERO_FILL` ONLY when market_resolved=True, age>=60s,
      res_age>=15s, on-chain ERC-1155 delta==0, account fills==[], and redemption_payouts==[].
    """
    import src.polymarket_research.polymarket_live_harvester as plh

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_zombie.json")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.executor.client = object()
    h.executor.is_authenticated = True
    tok_z = "31596117058364164399296761298835839440526505927441436111226506604372106010643"
    cond_z = "0x5c9e93ab2c4bc7a0994fcda158774602fb98689001dddb1abe02c515ad21319e"
    oid_z = "0x991211b7a3c24c4f74b954b6277b99e65c15ef0d2d68201675230ca364a8d4a8"
    tid_z = "MKR_LOCK1_LIVE_VERIFIED_PRIMARY_ORACLE_1793859013_69621"
    now_ts = time.time()

    h._wallet_token_balance = lambda _tk: (0.0, h.ONCHAIN_SOURCE)
    h.executor.get_account_fills = lambda *_a, **_kw: []
    h.executor.get_order_status = lambda _oid: {
        "id": oid_z, "status": "LIVE", "size_matched": "0", "original_size": "23", "associate_trades": [],
    }
    h.executor.cancel_order = lambda _oid: {
        "is_canceled": False, "outcome": "UNKNOWN", "matched": 0.0,
        "not_canceled_reason": "order can't be found - already canceled or matched",
    }

    # 1. Fail-closed if AutoRedeemer payout exists (never misclassify a redeemed winner as NOT_EXECUTED!)
    h.executor.redemption_payouts = lambda _cid, _ts: [{"payout_usd": 23.0, "transaction_hash": "0x" + "aa" * 32}]
    cls_redeemed = h._classify_entry(
        tok_z, 0.0, now_ts - 600.0, oid_z, tid_z,
        market_resolved=True, condition_id=cond_z, resolution_seen_at_ts=now_ts - 120.0,
    )
    assert cls_redeemed["verdict"] == "UNKNOWN"

    # 2. Fail-closed if market is NOT resolved yet
    h.executor.redemption_payouts = lambda _cid, _ts: []
    cls_live = h._classify_entry(
        tok_z, 0.0, now_ts - 600.0, oid_z, tid_z,
        market_resolved=False, condition_id=cond_z, resolution_seen_at_ts=0.0,
    )
    assert cls_live["verdict"] == "UNKNOWN"

    # 3. Resolved market + 0 on-chain delta + 0 fills + 0 redemptions + purged from matching engine -> NOT_EXECUTED ($0 PnL)
    h.active_positions[tid_z] = {
        "trade_id": tid_z, "market_id": "6569621", "condition_id": cond_z, "token_id": tok_z,
        "target_token": "NO", "is_single_leg_lock": True, "box_type": "SINGLE_LEG_MAKER_LOCK",
        "entry_price": 0.992, "entry_shares": 23.0, "remaining_shares": 23.0,
        "notional_usd": 22.816, "remaining_cost_basis": 22.816, "pre_token_balance": 0.0,
        "order_id": oid_z, "entry_order_id": oid_z,
        "status": "ENTRY_OUTCOME_UNKNOWN", "exit_order_status": "ENTRY_OUTCOME_UNKNOWN",
        "inventory_reconciled": False,
        "submitted_at_ts": now_ts - 600.0, "entry_ts": now_ts - 580.0,
        "resolved_winning_outcome": "NO", "resolution_seen_at_ts": now_ts - 120.0,
    }
    assert h._resolve_unknown_entry(tid_z, h.active_positions[tid_z]) is True
    assert tid_z not in h.active_positions
    rec_z = h.closed_positions[-1]
    assert rec_z["status"] == "NOT_EXECUTED"
    assert rec_z["close_reason"] == "ENTRY_NOT_EXECUTED_VERIFIED"
    assert rec_z["non_execution_proof"] == "RESOLVED_MARKET_PURGED_ORDER_ZERO_FILL"
    assert rec_z["net_pnl_usd"] == pytest.approx(0.0)
    assert rec_z["notional_usd"] == pytest.approx(0.0)


def test_v531_mixed_normal_and_self_laddered_mint_fills_plus_trade_ids_persistence(tmp_path, monkeypatch):
    """
    Verifies adversarial review fixes (Bugs 2, 3, 6):
      1. `get_account_fills` merges direct `MatchType.NORMAL` fills with opposite-token `MatchType.MINT` fills
         even when a partial direct fill exists, AND preserves all self-laddered `maker_orders[]` for our funder
         even when `order_id` is omitted (`""`) on multiple maker orders in the same sweep.
      2. `_apply_market_resolution` persists `trade_id` from `get_account_fills` into `pos["trade_ids"]`
         (fixing `f.get("trade_id") or f.get("id")`).
      3. `find_redemption_payouts` clamps ancient `from_block` values to `head - 50000`.
    """
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus, PolymarketLiveExecutor

    funder = "0x11c72ca19854132a4f5433b9aa9746159a4a6354"
    win_tok = "102991566039815573634495392488635789304041380501887303505995890983596993640413"
    opp_tok = "999999999999999999999999999999999999999999999999999999999999999999999999999999"

    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    ex.funder_address = funder

    norm_trade = {
        "id": "NORM_TR_1",
        "status": "CONFIRMED",
        "asset_id": win_tok,
        "side": "SELL",
        "match_time": "1793831468",
        "transaction_hash": "0x" + "11" * 32,
        "maker_orders": [
            {
                "order_id": "0xLADDER_A",
                "maker_address": funder,
                "asset_id": win_tok,
                "side": "BUY",
                "matched_amount": "6",
                "price": "0.991",
            }
        ],
    }
    mint_sweep_trade = {
        "id": "MINT_SWEEP_2",
        "type": "MINT",
        "status": "CONFIRMED",
        "asset_id": opp_tok,
        "side": "BUY",
        "match_time": "1793831469",
        "transaction_hash": "0x" + "22" * 32,
        "maker_orders": [
            {
                "order_id": "",
                "maker_address": funder.upper(),
                "asset_id": win_tok,
                "side": "BUY",
                "matched_amount": "7",
                "price": "0.992",
            },
            {
                "order_id": "",
                "maker_address": funder,
                "asset_id": win_tok,
                "side": "BUY",
                "matched_amount": "5",
                "price": "0.993",
            },
        ],
    }

    class _MixedClob:
        def get_trades(self, params=None):
            aid = getattr(params, "asset_id", None) if params is not None else None
            if aid == win_tok:
                return [norm_trade]
            return [norm_trade, mint_sweep_trade]

    ex.client = _MixedClob()
    fills = ex.get_account_fills(token_id=win_tok, after_ts=1793831400, side="BUY", order_id=None)
    assert fills is not None and len(fills) == 3
    assert sum(f["size"] for f in fills) == pytest.approx(18.0)
    assert {f["trade_id"] for f in fills} == {"NORM_TR_1", "MINT_SWEEP_2"}

    # Verify _apply_market_resolution persists recovered `trade_id`s into closed_positions
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_tids.json")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h.executor = ex
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    ex.get_order_fill_summary = lambda *_a, **_kw: None
    ex.get_current_block_number = lambda: 96_800_000
    ex.find_redemption_payouts = lambda *_a, **_kw: [{"payout_usd": 18.0, "transaction_hash": "0x" + "aa" * 32}]

    tid_w = "MKR_LOCK1_TRADE_IDS_TEST"
    h.active_positions[tid_w] = {
        "trade_id": tid_w, "market_id": "59042", "condition_id": "0x" + "67" * 32,
        "token_id": win_tok, "target_token": "YES",
        "is_dominance_box": True, "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "entry_price": 0.992, "entry_shares": 18.0, "remaining_shares": 18.0,
        "notional_usd": 17.856, "remaining_cost_basis": 17.856, "fee_usd": 0.0,
        "entry_ts": 1793831460.0, "trade_ids": [], "transactions_hashes": [],
        "status": ExecutionStatus.POSITION_CONFIRMED, "inventory_reconciled": True,
    }
    asyncio.run(h._apply_market_resolution(tid_w, h.active_positions[tid_w], "YES"))
    closed_w = h.closed_positions[-1]
    assert closed_w["won"] is True
    assert closed_w["trade_ids"] == ["NORM_TR_1", "MINT_SWEEP_2"]
    assert len(closed_w["transactions_hashes"]) == 2

    # Verify ancient from_block clamp in find_redemption_payouts
    ex_blk = PolymarketLiveExecutor(dry_run=True)
    ex_blk.dry_run = False
    ex_blk.funder_address = funder
    queried_from = []
    ex_blk._rpc = lambda method, params: (
        hex(96_800_000)
        if method == "eth_blockNumber"
        else (queried_from.append(int(params[0]["fromBlock"], 16)) or [])
    )
    out_ev = ex_blk.find_redemption_payouts("0x" + "67" * 32, from_block=96_000_000)
    assert out_ev == []
    assert queried_from[0] == 96_800_000 - 50_000


def test_v531_ws_tick_precedence_over_stale_rest_book_and_ladder_eviction(tmp_path):
    """
    Verifies adversarial review fixes (Bugs 1A & 1B):
      1. `update_ws_tick_size(tok, 0.001)` evicts stale `"0.01"` pre-signed ladder orders while keeping `"0.001"` orders.
      2. Live WS tick size (`0.001`) beats stale REST `/book` `"minimum_tick_size": "0.01"` in `resolve_harvester_sll_tick_size`.
      3. Non-WS heuristic `leg_a_tick_size` (`0.01`) does NOT set `leg_a_ws_tick_size` or poison
         `get_token_tick_size(..., price_hint=0.965)` dynamic `>=0.96` boundary re-verification.
    """
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        emit_single_leg_maker_lock_cand_impl,
        resolve_harvester_sll_tick_size,
    )

    ex = PolymarketLiveExecutor(dry_run=True)
    tok = "7171717171717171717171717171717171717171"
    opp = "8181818181818181818181818181818181818181"
    now_s = time.time()
    ex.order_ladder_cache._cache[(tok, 96, 18, "0.01", False)] = (now_s, "SIGNED_OLD_001")
    ex.order_ladder_cache._cache[(tok, 96, 18, "0.001", False)] = (now_s, "SIGNED_NEW_0001")

    tracker = PolymarketClobMarketWsTracker(on_tick_size_change=ex.update_ws_tick_size)
    tracker.set_desired_tokens([tok])
    tracker.process_ws_payload({"event_type": "tick_size_change", "asset_id": tok, "old_tick_size": "0.01", "new_tick_size": "0.001"})

    assert ex.order_ladder_cache.get_presigned_order(tok, price=0.96, shares=18, tick_size="0.01") is None
    assert ex.order_ladder_cache.get_presigned_order(tok, price=0.96, shares=18, tick_size="0.001") == "SIGNED_NEW_0001"

    # Stale REST `/book` still says "0.01", but WS tracker has 0.001 -> WS 0.001 MUST win!
    resolved_tk = resolve_harvester_sll_tick_size(
        ex, tok, {"leg_a_tick_size": 0.01},
        bk_win={"minimum_tick_size": "0.01"}, mkt_ws=tracker, real_clob=True, price_hint=0.962,
    )
    assert resolved_tk == pytest.approx(0.001)

    # Non-WS candidate (empty `_token_tick_sizes`) must NOT emit `leg_a_ws_tick_size` or block `>=0.96` dynamic recheck
    cand_file = tmp_path / "no_ws_cands.jsonl"
    state_file = tmp_path / "st_nows.json"

    class _NoWsDaemon:
        single_scan = True
        _last_d1_live_emit_ts = {}
        _token_tick_sizes = {}

    ok = emit_single_leg_maker_lock_cand_impl(
        _NoWsDaemon(),
        sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        asset="NBA",
        dedupe_key="MKR_NO_WS_TK",
        pair_dedupe_key="PAIR_NO_WS_TK",
        token_id=tok,
        opp_token_id=opp,
        market_id="55102",
        condition_id="0x" + "52" * 32,
        side_label="YES",
        display_label="Lakers vs Celtics",
        bk_win={"minimum_tick_size": "0.01", "bids": [{"price": "0.94", "size": "40"}], "asks": [{"price": "0.96", "size": "40"}]},
        bk_opp={"bids": [{"price": "0.004", "size": "20"}], "asks": [{"price": "0.05", "size": "40"}]},
        neg_risk=False,
        close_ts=now_s + 1800.0,
        now_ts=now_s,
        min_resting_bid=0.940,
        max_resting_bid=0.991,
        min_maker_edge=0.006,
        max_opp_bid=0.008,
        hold_to_maturity=True,
        p_model=0.999,
        target_bid_px=None,
        maker_rebate_ps=0.0,
        extract_best_bid_fn=lambda bids: (float(bids[0]["price"]), float(bids[0]["price"]) * float(bids[0]["size"])) if bids else (0.0, 0.0),
        cand_file=cand_file,
        default_cand_path=tmp_path / "default_nows.jsonl",
        state_file=state_file,
        default_state_path=state_file,
    )
    assert ok is True
    emitted = json.loads(cand_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert "leg_a_ws_tick_size" not in emitted

    ex2 = PolymarketLiveExecutor(dry_run=True)
    ex2.update_ws_tick_size(tok, 0.01)
    sdk_calls = []
    ex2.client = type("_TickSdk", (), {"get_tick_size": lambda self, tid: (sdk_calls.append(tid), "0.001")[1]})()
    assert ex2.get_token_tick_size(tok, price_hint=0.965) == pytest.approx(0.001)
    assert sdk_calls == [tok]


def test_v531_harvester_dispute_guard_and_polybolt_mid_session_401_failover(tmp_path, monkeypatch):
    """
    Verifies adversarial review fixes (Bugs 4, 5A, 5B) + prior untested edge cases:
      1. Harvester `_finish_single_leg_lock` and `maybe_execute_graduated_single_leg_maker_lock` enforce
         `proposal_age_sec >= 1800` on `BOND1` and veto pre-final `MKR_LOCK1` clinches on Tennis/Esports/90m-Soccer,
         while allowing seasoned `BOND1` (`>=1800s`), `FINAL` clinches, and NBA/NFL/MLB/NHL markets.
      2. `PolymarketChainlinkLiveStream.run_forever` survives a mid-session PolyBolt V2 `401` auth rejection by
         failing over immediately to RTDS (handling unscaled decimal RTDS `full_accuracy_value` without `1e18` corruption),
         refreshing rotated L2 credentials, and reconnecting to PolyBolt V2 without stalling `get_rolling_twap_60s`.
    """
    from aiohttp import web
    import src.polymarket_research.polymarket_live_harvester as plh
    import src.polymarket_research.polymarket_ws_streams as pws

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_disp.json")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    h = plh.PolymarketLiveHarvester(dry_run=True)
    now_u = time.time()

    # 1a. Harvester _finish_single_leg_lock blocks unseasoned (<1800s) BOND1 with 90m Soccer rule text
    unseasoned_b1 = {
        "box_id": "B1_UNSEASONED_SOC", "box_type": "SINGLE_LEG_LOCK",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "asset": "SOCCER",
        "leg_a_token_id": "1" * 40, "leg_a_opp_token_id": "2" * 40,
        "leg_a_market_id": "9001", "leg_a_condition_id": "0x" + "91" * 32,
        "rules_text": "Resolves to 90 minutes of regular play plus stoppage time, excluding extra time and penalties.",
        "proposal_age_sec": 600.0, "ts_unix": now_u, "expiry_ts": now_u + 1800.0,
    }
    rej_b1 = h._finish_single_leg_lock(unseasoned_b1, "BOND1_UMA_RESOLUTION_CARRY", "1" * 40, "9001", "DK_B1_SOC", {}, now_u, {})
    assert rej_b1["executed"] is False and "DISPUTE_RULE_PROPOSAL_UNSEASONED" in rej_b1["reason"]

    # 1b. Harvester maybe_execute_graduated_single_leg_maker_lock blocks pre-final MKR_LOCK1 with walkover/retirement clause
    prefinal_mkr = {
        "box_id": "MLK_TENNIS_PRE", "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "dedupe_key": "DK_MLK_TEN", "pair_dedupe_key": "PK_MLK_TEN",
        "asset": "TENNIS", "mode": "SET_CLINCH_IN_PLAY",
        "rules_text": "If a player retires mid-match or walkover occurs before completion, resolves 50-50.",
        "leg_a_token_id": "1" * 40, "leg_a_opp_token_id": "2" * 40, "leg_a_market_id": "9002",
        "anchor_bid_px": 0.985, "p_model": 0.999, "ts_unix": now_u, "expiry_ts": now_u + 1800.0,
    }
    rej_mkr = asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock(prefinal_mkr))
    assert rej_mkr["executed"] is False and rej_mkr["reason"] == "DISPUTE_RULE_PRE_FINAL_CLINCH_VETO"

    # 2. PolyBolt V2 mid-session 401 -> immediate RTDS failover (unscaled decimal) -> credential refresh -> PolyBolt V2 recovery
    async def _run_failover_and_cred_refresh():
        pb_auths = []
        rtds_hits = []
        t0_ms = int(time.time() * 1000)
        pb_conn_idx = 0

        async def _pb_handler(request):
            nonlocal pb_conn_idx
            pb_conn_idx += 1
            c_no = pb_conn_idx
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            msg = await ws.receive_json()
            ak = (msg.get("auth") or {}).get("apiKey")
            pb_auths.append(ak)
            if c_no == 1:
                await ws.send_json({"op": "authed", "rid": "a1"})
                for _ in range(len(pws.POLYBOLT_CRYPTO_SYMBOLS)):
                    sub = await ws.receive_json()
                    sym = sub["subscriptions"][0]["filter"]["symbol"]
                    await ws.send_json({"op": "subscribed", "rid": sub["rid"], "channel": "price.crypto"})
                    if sym.lower() == "btcusd":
                        pts = [
                            {"timestamp": t0_ms - (65 - i) * 1000, "value": 80500.0, "full_accuracy_value": "80500.00"}
                            for i in range(65)
                        ]
                        await ws.send_json({
                            "v": 2, "channel": "price.crypto", "snapshot": True,
                            "payload": {"symbol": "btcusd", "source": "chainlink", "data": pts},
                        })
                # Rotate env creds while connected, then close session to force mid-session reconnect
                monkeypatch.setenv("POLY_API_KEY", "rotated_k2")
                await ws.close()
                return ws
            if ak != "rotated_k2":
                # Simulate HTTP 401 / auth rejection on stale cached credentials
                await ws.send_json({"op": "error", "code": 401, "message": "401 Unauthorized: invalid api key"})
                await ws.close()
                return ws
            await ws.send_json({"op": "authed", "rid": "a2"})
            for _ in range(len(pws.POLYBOLT_CRYPTO_SYMBOLS)):
                sub = await ws.receive_json()
                sym = sub["subscriptions"][0]["filter"]["symbol"]
                await ws.send_json({"op": "subscribed", "rid": sub["rid"], "channel": "price.crypto"})
                if sym.lower() == "btcusd":
                    await ws.send_json({
                        "v": 2, "channel": "price.crypto", "dropped": 0,
                        "payload": {"symbol": "btcusd", "source": "chainlink", "timestamp": t0_ms + 2000, "full_accuracy_value": "80610.50"},
                    })
            await asyncio.sleep(0.15)
            await ws.close()
            return ws

        async def _rtds_handler(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            _ = await ws.receive_json()
            rtds_hits.append(True)
            # Send unscaled decimal string on RTDS fallback to ensure no 1e18 underflow!
            await ws.send_json({
                "topic": "crypto_prices_chainlink",
                "payload": {"symbol": "btc/usd", "timestamp": t0_ms + 1000, "full_accuracy_value": "80575.25", "value": 80575.25},
            })
            await asyncio.sleep(0.05)
            await ws.close()
            return ws

        app = web.Application()
        app.router.add_get("/pb", _pb_handler)
        app.router.add_get("/rtds", _rtds_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]

        pb_url = f"ws://127.0.0.1:{port}/pb"
        rtds_url = f"ws://127.0.0.1:{port}/rtds"
        monkeypatch.setattr(pws, "POLYBOLT_V2_WS_URL", pb_url)
        monkeypatch.setattr(pws, "LIVE_DATA_WS_URL", rtds_url)
        monkeypatch.setenv("POLY_API_KEY", "initial_k1")
        monkeypatch.setenv("POLY_SECRET", "sec_1")
        monkeypatch.setenv("POLY_PASSPHRASE", "pass_1")
        pws.invalidate_polybolt_l2_creds()

        stop_ev = False
        stream = pws.PolymarketChainlinkLiveStream(ws_url=pb_url, prefer_polybolt_v2=True, l2_creds=None)
        task = asyncio.create_task(stream.run_forever(stop_check=lambda: stop_ev))
        try:
            for _ in range(80):
                if stream.get_latest_spot("BTC") == pytest.approx(80610.50):
                    break
                await asyncio.sleep(0.05)
            assert rtds_hits, "Stream must fail over to RTDS immediately after PolyBolt disconnect/401"
            assert "initial_k1" in pb_auths and "rotated_k2" in pb_auths
            assert stream.get_latest_spot("BTC") == pytest.approx(80610.50)
            twap = stream.get_rolling_twap_60s("BTC", max_age_sec=10.0)
            assert twap is not None and 80500.0 <= twap <= 80611.0
        finally:
            stop_ev = True
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await runner.cleanup()

    asyncio.run(_run_failover_and_cred_refresh())


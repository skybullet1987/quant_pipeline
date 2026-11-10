#!/usr/bin/env python3
"""
Regression Test Suite for v6 Live Production QA & Forensic Audit Fixes:
  - [EXEC-1/2/3/4/5] Executor pre-signed order cache safety, IEEE-754 exact 2-decimal sell lot preservation,
    _ClobClient__fee_rates prewarm, and 2-stage aggressive legged-out unwind aggregation.
  - [HARV-2/4/5/6c/6d] Harvester single-leg-lock maker preemption ordering, split-leg box maturity equity floor,
    atomic overround asymmetric-fill demotion, V2 FeeModuleV2 pUSD cash-fee upgrade on 100%-gross settlement,
    and inline legged-out SHARES-fee accounting.
  - [A124-1/2] Alpha-124 7d zero-loss mathematical TTE window and MKR_LOCK1 rebate payload emission.
  - [PROJ-1/2] Daily projections exact cash-conserving equity & locked box floor reconstruction + box_id grouping.
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import scripts.polymarket_daily_projections as dp
import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon
from src.polymarket_research.polymarket_live_executor import (
    OrderType,
    PolymarketLiveExecutor,
    PreSignedOrderLadderCache,
    _sign_and_post_single_hop,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester


@pytest.fixture(autouse=True)
def _offline_clob(monkeypatch):
    """Run 100% offline with mocked ClobClient and deterministic test credentials."""
    import src.polymarket_research.polymarket_live_executor as ex

    monkeypatch.setattr(ex, "ClobClient", MagicMock(name="OfflineClobClient"))
    monkeypatch.setattr(ex, "PY_CLOB_AVAILABLE", True)
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
    monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "2")


def test_exec_exact_two_decimal_sell_not_shaved():
    """Verifies [EXEC-2]: exact 2-decimal lots like 14.10 (14.10*100 == 1409.9999999999998 in IEEE-754) are never shaved by 0.01."""
    ex = PolymarketLiveExecutor(dry_run=False)
    ex.is_authenticated = True
    ex.auth_mode = "LIVE"
    ex.client = MagicMock()
    ex.prewarm_token_market_cache("10001", tick_size="0.01", neg_risk=False, fee_rate_bps=500, fee_rate=0.05)
    ex.get_unreserved_conditional_balance = MagicMock(return_value=14.10)

    captured_sizes = []

    def _fake_create_order(order_args, opts=None):
        captured_sizes.append(float(order_args.size))
        return {"signed": True, "size": float(order_args.size), "price": float(order_args.price)}

    ex.client.create_order.side_effect = _fake_create_order
    ex.client.post_order.return_value = {"orderID": "0xEXIT1410", "status": "live"}

    res_mkr = ex.post_maker_exit_order(token_id="10001", price=0.99, size=14.10, side="SELL", neg_risk=False)
    assert res_mkr["success"] is True
    assert captured_sizes[-1] == pytest.approx(14.10, abs=1e-9)

    ex.client.post_order.return_value = {
        "orderID": "0xUNW1410",
        "status": "matched",
        "takingAmount": "9.87",
        "makingAmount": "14.10",
    }
    res_unw = ex.execute_unwind_order(token_id="10001", size=14.10, side="SELL", min_price=0.70, neg_risk=False)
    assert res_unw["success"] is True
    assert captured_sizes[-1] == pytest.approx(14.10, abs=1e-9)


def test_exec_prewarm_populates_fee_rates_when_tick_already_cached():
    """Verifies [EXEC-3]: prewarm_token_market_cache populates _ClobClient__fee_rates even if _ClobClient__tick_sizes already had token_id."""
    ex = PolymarketLiveExecutor(dry_run=False)
    ex.client = MagicMock()
    ex.client._ClobClient__tick_sizes = {"TOK_PRE": "0.01"}
    ex.client._ClobClient__neg_risk = {"TOK_PRE": False}
    ex.client._ClobClient__fee_rates = {}
    ex.client._ClobClient__token_condition_map = {}
    ex.client._ClobClient__fee_infos = {}

    ex.prewarm_token_market_cache(
        "TOK_PRE",
        tick_size="0.01",
        neg_risk=False,
        fee_rate_bps=500,
        condition_id="0x" + "ab" * 32,
        fee_rate=0.05,
        fee_exponent=1.0,
    )
    assert ex.client._ClobClient__fee_rates["TOK_PRE"] == 500
    assert ex._fee_cache["TOK_PRE"] == (0.05, 1.0)


def test_exec_presigned_ladder_near_respects_max_notional_and_order_type():
    """Verifies [EXEC-1]: _sign_and_post_single_hop enforces max_notional_usd on near-rung lookup and preserves requested OrderType."""
    cache = PreSignedOrderLadderCache(ttl_seconds=180.0)
    cache.store_presigned_order("TOK_LAD", price=0.75, shares=21, signed_order={"rung": 21}, tick_size="0.01", neg_risk=False)
    cache.store_presigned_order("TOK_LAD", price=0.75, shares=19, signed_order={"rung": 19}, tick_size="0.01", neg_risk=False)

    client = MagicMock()
    client.post_order.return_value = {"orderID": "0xFAK19", "status": "matched"}
    opts = type("Opts", (), {"tick_size": "0.01", "neg_risk": False})()
    stage = {}

    # 21 * 0.75 = $15.75 > max_notional_usd=$15.10, so near lookup MUST pick 19 shares ($14.25), not 21!
    out = _sign_and_post_single_hop(
        client=client,
        ladder_cache=cache,
        token_id="TOK_LAD",
        price=0.75,
        size=20.0,
        side="BUY",
        order_type=OrderType.FAK,
        create_options=opts,
        stage=stage,
        max_notional_usd=15.10,
    )
    assert out["cache_hit"] is True
    assert out["signed_shares"] == 19.0
    posted_signed, posted_ot, post_only_flag, defer_flag = client.post_order.call_args[0]
    assert posted_signed == {"rung": 19}
    assert posted_ot == OrderType.FAK
    assert post_only_flag is False
    assert defer_flag is True


def test_harv_single_leg_lock_preempts_resting_maker_before_busy_check(tmp_path, monkeypatch):
    """Verifies [HARV-2]: _finish_single_leg_lock preempts a resting maker anchor on mid_a BEFORE checking busy markets."""
    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.STATE_FILE",
        tmp_path / "harv_state.json",
    )
    harv = PolymarketLiveHarvester(dry_run=True)
    mid = "MKT_BOND1_SELF_PREEMPT"
    intent_id = "MKR_SLL_BOND1_TEST"
    ev = asyncio.Event()

    harv.pending_entry_intents[intent_id] = {
        "trade_id": intent_id,
        "market_id": mid,
        "inflight_key": f"KEY_{mid}",
        "live_maker_anchor_inflight": True,
        "notional_usd": 12.0,
    }
    harv._maker_anchor_preempt_events = {f"KEY_{mid}": ev}

    orig_preempt = harv._preempt_resting_maker_anchors

    def _preempt_and_clear(*args, **kwargs):
        n = orig_preempt(*args, **kwargs)
        if ev.is_set():
            harv.pending_entry_intents.pop(intent_id, None)
        return n

    harv._preempt_resting_maker_anchors = _preempt_and_clear
    harv.executor.get_market_book = MagicMock(
        side_effect=lambda tok: (
            {"asks": [{"price": "0.990", "size": "50"}], "bids": [{"price": "0.988", "size": "50"}]}
            if tok == "TOK_WIN"
            else {"asks": [{"price": "0.012", "size": "50"}], "bids": [{"price": "0.002", "size": "50"}]}
        )
    )

    now_ts = time.time()
    cand = {
        "box_id": "SLL_TEST_1",
        "box_type": "SINGLE_LEG_LOCK",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
        "leg_a_market_id": mid,
        "leg_a_condition_id": "0x" + "33" * 32,
        "leg_a_token_id": "TOK_WIN",
        "leg_a_opp_token_id": "TOK_OPP",
        "leg_a_side": "YES",
        "leg_a_fee_rate": 0.0,
        "leg_a_fee_exponent": 1.0,
        "max_box_cost_net": 0.995,
        "max_opp_bid": 0.010,
        "ts_unix": now_ts,
        "expiry_ts": now_ts + 3600.0,
    }
    res = harv._finish_single_leg_lock(
        cand=cand,
        sleeve_src="BOND1_UMA_RESOLUTION_CARRY",
        tok_a="TOK_WIN",
        mid_a=mid,
        dedupe_k=f"BOND1_{mid}",
        retry_cd={},
        now_ts=now_ts,
        _rcfg={},
        own_grad=True,
    )
    assert ev.is_set() is True
    assert res.get("reason") != "MARKET_ALREADY_OCCUPIED"
    assert res.get("executed") is True


def test_harv_get_position_market_value_split_box_floor():
    """Verifies [HARV-4]: surviving dominance-box leg whose partner resolved at $0 is valued at guaranteed box payout floor."""
    now_ts = 1793800000.0
    surviving_leg = {
        "trade_id": "SOC2_L1",
        "is_dominance_box": True,
        "entry_shares": 54.0,
        "expected_terminal_payout_usd": 54.0,
        "notional_usd": 35.10,
        "remaining_cost_basis": 35.10,
        "candle_expiry_ts": now_ts - 30.0,
        "status": "AWAITING_ONCHAIN_SETTLEMENT",
        "resolved_winning_outcome": None,
        "_closed_partner_leg": {
            "trade_id": "SOC2_L2",
            "notional_usd": 17.05,
            "payout_usd": 0.0,
        },
    }
    assert PolymarketLiveHarvester.get_position_market_value(surviving_leg, now_ts) == pytest.approx(54.0, abs=1e-6)

    unresolved_box_leg = {
        "trade_id": "BOX_UNRES_1",
        "is_dominance_box": True,
        "entry_shares": 20.0,
        "notional_usd": 12.40,
        "remaining_cost_basis": 12.40,
        "candle_expiry_ts": now_ts + 600.0,
        "status": "UNRESOLVED_SETTLEMENT",
        "resolved_winning_outcome": None,
    }
    assert PolymarketLiveHarvester.get_position_market_value(unresolved_box_leg, now_ts) == pytest.approx(12.40, abs=1e-6)


def test_harv_atomic_overround_asymmetric_fill_demotes_survivor(tmp_path, monkeypatch):
    """Verifies [HARV-5]: asymmetric 1-leg fill in _try_atomic_box_overround_unwind demotes survivor to supervised residual unwind."""
    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.STATE_FILE",
        tmp_path / "ovr_state.json",
    )
    harv = PolymarketLiveHarvester(dry_run=False)
    now_ts = time.time()
    harv.active_positions = {
        "BOX_A": {
            "trade_id": "BOX_A",
            "box_id": "BOX_OVR_1",
            "box_partner_trade_id": "BOX_B",
            "is_dominance_box": True,
            "has_double_payout_corridor": False,
            "box_cost_net": 0.985,
            "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
            "market_id": "M1",
            "token_id": "TOK_A",
            "target_token": "NO",
            "asset": "SOC2",
            "entry_price": 0.65,
            "entry_shares": 10.0,
            "gross_entry_shares": 10.0,
            "remaining_shares": 10.0,
            "remaining_exit_shares": 10.0,
            "filled_exit_shares": 0.0,
            "remaining_cost_basis": 6.50,
            "notional_usd": 6.50,
            "fee_usd": 0.0,
            "fee_rate_applied": 0.0,
            "fee_exponent_applied": 1.0,
            "inventory_reconciled": True,
            "candle_expiry_ts": now_ts + 1800.0,
            "entry_ts": now_ts - 60.0,
            "exit_order_id": None,
            "status": "POSITION_CONFIRMED",
        },
        "BOX_B": {
            "trade_id": "BOX_B",
            "box_id": "BOX_OVR_1",
            "box_partner_trade_id": "BOX_A",
            "is_dominance_box": True,
            "has_double_payout_corridor": False,
            "box_cost_net": 0.985,
            "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
            "market_id": "M2",
            "token_id": "TOK_B",
            "target_token": "YES",
            "asset": "SOC2",
            "entry_price": 0.33,
            "entry_shares": 10.0,
            "gross_entry_shares": 10.0,
            "remaining_shares": 10.0,
            "remaining_exit_shares": 10.0,
            "filled_exit_shares": 0.0,
            "remaining_cost_basis": 3.30,
            "notional_usd": 3.30,
            "fee_usd": 0.0,
            "fee_rate_applied": 0.0,
            "fee_exponent_applied": 1.0,
            "inventory_reconciled": True,
            "candle_expiry_ts": now_ts + 1800.0,
            "entry_ts": now_ts - 60.0,
            "exit_order_id": None,
            "status": "POSITION_CONFIRMED",
        },
    }

    async def _mock_book_async(tok):
        if tok == "TOK_A":
            return {"bids": [{"price": "0.68", "size": "25"}], "asks": [{"price": "0.70", "size": "25"}]}
        return {"bids": [{"price": "0.34", "size": "25"}], "asks": [{"price": "0.36", "size": "25"}]}

    harv.executor.get_market_book_async = _mock_book_async
    harv.executor.execute_atomic_box_overround_unwind = MagicMock(
        return_value={
            "success": False,
            "leg_a": {
                "filled": True,
                "orderID": "0xSELL_A",
                "matched_size": 10.0,
                "taking_amount": 6.80,
                "fee_usd": 0.0,
                "avg_px": 0.68,
            },
            "leg_b": {
                "filled": False,
                "outcome_unknown": False,
                "error": "FOK_NOT_FILLED",
            },
        }
    )

    asyncio.run(harv._try_atomic_box_overround_unwind(now_ts, set()))

    assert "BOX_A" not in harv.active_positions
    assert "BOX_B" in harv.active_positions
    surv = harv.active_positions["BOX_B"]
    assert surv["is_dominance_box"] is False
    assert surv["is_legged_out_residual"] is True
    assert surv["exit_order_status"] == "UNWIND_RETRY_REQUIRED"


def test_harv_v2_pusd_cash_fee_upgrade_on_100pct_gross_settlement(tmp_path, monkeypatch):
    """Verifies [HARV-6d]: when Polymarket V2 settles 100% of gross_entry_shares on a SHARES-tagged leg, fee_usd upgrades to exact V2 pUSD cash fee."""
    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.STATE_FILE",
        tmp_path / "v2_fee_state.json",
    )
    harv = PolymarketLiveHarvester(dry_run=False)
    harv.executor.is_authenticated = True
    harv.executor.auth_mode = "LIVE"
    harv._wallet_token_balance = MagicMock(return_value=(54.0, harv.ONCHAIN_SOURCE))
    harv.executor.post_maker_exit_order = MagicMock(
        return_value={"success": True, "orderID": "0xREST99", "post_only": True}
    )

    now_ts = time.time()
    tid = "SOC2_V2_L1"
    pos = {
        "trade_id": tid,
        "box_id": "SPORTS_CORRIDOR_LIVE_SOCCER_22386",
        "is_dominance_box": True,
        "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
        "market_id": "6022412",
        "token_id": "99887766554433221100112233",
        "target_token": "NO",
        "asset": "SOC2",
        "entry_price": 0.65,
        "entry_shares": 53.38,
        "gross_entry_shares": 54.0,
        "remaining_shares": 53.38,
        "remaining_exit_shares": 53.38,
        "remaining_cost_basis": 35.10,
        "notional_usd": 35.10,
        "fee_usd": 0.0,
        "entry_fee_cash_usd": 0.0,
        "entry_fee_asset": "SHARES",
        "fee_source": "sports_fees_v2",
        "fee_rate_applied": 0.05,
        "fee_exponent_applied": 1.0,
        "pre_token_balance": 0.0,
        "inventory_reconciled": False,
        "target_exit_price": 0.99,
        "candle_expiry_ts": now_ts + 3600.0,
        "entry_ts": now_ts - 5.0,
        "status": "POSITION_CONFIRMED",
    }
    harv.active_positions[tid] = pos

    posted = harv._attempt_maker_exit_post_impl(tid, pos)
    assert posted is True
    assert pos["inventory_reconciled"] is True
    assert pos["entry_shares"] == pytest.approx(54.0, abs=1e-6)
    assert pos["entry_fee_asset"] == "USDC"
    # 54.0 * 0.05 * (0.65 * 0.35) = 0.61425 -> 0.6142
    assert pos["fee_usd"] == pytest.approx(0.6142, abs=2e-4)
    assert pos["entry_fee_cash_usd"] == pytest.approx(0.6142, abs=2e-4)


def test_harv_inline_legged_out_close_shares_fee_no_double_charge(tmp_path, monkeypatch):
    """Verifies [HARV-6c]: _record_inline_d1_legged_out_close does not subtract fee_in cash when entry_fee_asset == 'SHARES'."""
    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.STATE_FILE",
        tmp_path / "inline_lo_state.json",
    )
    harv = PolymarketLiveHarvester(dry_run=True)
    cand = {
        "asset": "BTC",
        "leg_a_token_id": "TOK_A",
        "leg_a_market_id": "MKT_A",
        "leg_a_limit_price": 0.50,
        "leg_a_fee_rate": 0.07,
        "leg_a_fee_exponent": 1.0,
        "shares": 20.0,
    }
    resid = {
        "token_id": "TOK_A",
        "label": "UP",
        "price": 0.50,
        "matched_shares": 19.65,
        "entry_fee_asset": "SHARES",
        "raw": {"makingAmount": "10.00"},
        "unwind_result": {"matched_size": 19.65, "taking_amount": 9.80, "fee_usd": 0.17},
    }
    tid = harv._record_inline_d1_legged_out_close("BOX_LO_1", cand, resid, {"unwind_result": resid["unwind_result"]})
    rec = next(r for r in harv.closed_positions if r["trade_id"] == tid)
    # Spend was $10.00 (makingAmount); proceeds net = 9.80 - 0.17 = 9.63 -> net_pnl = -0.37 (NOT -0.37 - 0.34 = -0.71!)
    assert rec["net_pnl_usd"] == pytest.approx(-0.37, abs=0.01)


def test_projections_compute_live_equity_and_rates_live_soc2_snapshot():
    """Verifies [PROJ-1/2]: exact cash-conserving equity ($69.61) & locked floor ($70.26) on live SOC2 + resting BOND1 state, plus box_id grouping."""
    live_st = {
        "live_bankroll": 16.26,
        "total_account_equity": 68.41,
        "high_water_mark_equity": 69.61,
        "collateral_source": "ONCHAIN_POLYGON_USDC",
        "collateral_includes_resting_maker": True,
        "pending_entry_intents": {
            "MKR_SLL_BOND1_1": {
                "live_maker_anchor_inflight": True,
                "notional_usd": 11.904,
                "entry_order_id": "0xBOND1",
            }
        },
        "active_positions": {
            "SOC2_L1": {
                "trade_id": "SOC2_L1",
                "box_id": "SPORTS_CORRIDOR_LIVE_SOCCER_1793736000_22386",
                "is_dominance_box": True,
                "notional_usd": 35.10,
                "remaining_cost_basis": 35.10,
                "entry_shares": 54.0,
                "gross_entry_shares": 54.0,
                "remaining_shares": 54.0,
                "fee_usd": 0.0,
                "entry_fee_asset": "SHARES",
                "fee_rate_applied": 0.05,
                "fee_exponent_applied": 1.0,
                "inventory_reconciled": True,
            },
            "SOC2_L2": {
                "trade_id": "SOC2_L2",
                "box_id": "SPORTS_CORRIDOR_LIVE_SOCCER_1793736000_22386",
                "is_dominance_box": True,
                "notional_usd": 17.05,
                "remaining_cost_basis": 17.05,
                "entry_shares": 55.0,
                "gross_entry_shares": 55.0,
                "remaining_shares": 55.0,
                "fee_usd": 0.0,
                "entry_fee_asset": "SHARES",
                "fee_rate_applied": 0.05,
                "fee_exponent_applied": 1.0,
                "inventory_reconciled": True,
            },
        },
        "closed_positions": [
            {
                "trade_id": "PREV_BOX_L1",
                "box_id": "PREV_BOX_1",
                "is_dominance_box": True,
                "net_pnl_usd": 18.40,
                "won": True,
            },
            {
                "trade_id": "PREV_BOX_L2",
                "box_id": "PREV_BOX_1",
                "is_dominance_box": True,
                "net_pnl_usd": -17.65,
                "won": False,
            },
            {
                "trade_id": "BOND1_1",
                "is_dominance_box": False,
                "net_pnl_usd": 0.14,
                "won": True,
            },
        ],
    }

    stats = dp.compute_live_equity_and_rates(live_st, fallback_equity=69.61)
    # 16.26 + 35.10 + 0.6142 + 17.05 + 0.5882 = 69.6124 (resting maker NOT double-counted on Polygon ERC-20!)
    assert stats["live_equity"] == pytest.approx(69.6124, abs=0.01)
    # Locked payout floor: 16.26 + min(54.0, 55.0)*$1.00 = $70.26!
    assert stats["locked_floor_equity"] == pytest.approx(70.26, abs=0.01)
    assert stats["closed_legs_count"] == 3
    assert stats["economic_trades_count"] == 2
    assert stats["economic_wins"] == 2
    assert stats["economic_win_rate_pct"] == 100.0


def test_alpha124_zero_loss_7d_tte_and_mkr_lock1_rebate_emission(tmp_path, monkeypatch):
    """Verifies [A124-1/2]: 7d (604800s) TTE allowed for LP2/CAL1/LP1_NFL zero-loss math sleeves and MKR_LOCK1 rebate fields emitted."""
    state_p = tmp_path / "alpha124_shadow_state.json"
    cand_p = tmp_path / "d1_live_box_candidates.jsonl"
    monkeypatch.setattr(a124_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124_mod, "STATE_FILE", state_p)
    monkeypatch.setattr(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_p)

    daemon = Alpha124ShadowDaemon(single_scan=False)
    daemon.is_sleeve_grad8_ready = lambda sl: sl == "D1_SAME_ORACLE_DOMINANCE_BOX"

    now_ts = time.time()
    # 5 days out (432,000s > 36h, <= 7d): LP2 & CAL1 must be permitted; 8 days out must be rejected
    assert daemon._can_emit_zero_loss_math_live(
        "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG", now_ts + 432000.0, now_ts, p_model=1.0
    ) is True
    assert daemon._can_emit_zero_loss_math_live(
        "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX", now_ts + 432000.0, now_ts, p_model=1.0
    ) is True
    assert daemon._can_emit_zero_loss_math_live(
        "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG", now_ts + 700000.0, now_ts, p_model=1.0
    ) is False

    emitted = daemon.emit_live_single_leg_maker_lock_candidate(
        sleeve_source="MKR_LOCK1_ZERO_FEE_MAKER_REBATE_LOCK",
        asset="BTC",
        dedupe_key="MKR_LOCK1_TEST_1",
        pair_dedupe_key="LOCK1_TEST_1",
        token_id="TOK_YES_96",
        opp_token_id="TOK_NO_04",
        market_id="MKT_LOCK1",
        condition_id="0x" + "44" * 32,
        side_label="YES",
        display_label="BTC > 90k",
        bk_win={"bids": [{"price": "0.96", "size": "50"}], "asks": [{"price": "0.98", "size": "50"}]},
        bk_opp={"bids": [{"price": "0.002", "size": "50"}], "asks": [{"price": "0.03", "size": "50"}]},
        neg_risk=False,
        close_ts=now_ts + 1800.0,
        now_ts=now_ts,
        min_resting_bid=0.94,
        max_resting_bid=0.992,
        min_maker_edge=0.005,
        max_opp_bid=0.008,
        maker_rebate_ps=0.0015,
    )
    assert emitted is True
    rows = [json.loads(line) for line in cand_p.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["min_maker_edge"] == pytest.approx(0.005)
    assert rows[0]["maker_rebate_ps"] == pytest.approx(0.0015)


def test_audit_losing_trades_groups_winning_dominance_box(tmp_path, monkeypatch):
    """Verifies [AUDIT-1]: audit_losing_trades.py auto-clears both legs of a net-profitable dominance box instead of flagging the $0 leg."""
    import audit_losing_trades as alt

    monkeypatch.setattr(alt, "DATA_DIR", tmp_path)
    monkeypatch.setattr(alt, "AUDIT_STATE_FILE", tmp_path / "forensic_audit_state.json")
    monkeypatch.setattr(alt, "AUDIT_LEDGER_FILE", tmp_path / "forensic_audit_ledger.jsonl")
    monkeypatch.setattr(
        alt,
        "fetch_kraken_live_state",
        lambda: {
            "service_status": "active",
            "state": {
                "status": "RUNNING",
                "risk_halt": False,
                "live_bankroll": 70.26,
                "total_account_equity": 70.26,
                "active_positions_count": 0,
                "active_position_ids": [],
                "active_positions": {},
                "closed_positions_count": 2,
                "closed_positions": [
                    {
                        "trade_id": "SOC2_WIN_L1",
                        "box_id": "SOC2_BOX_22386",
                        "is_dominance_box": True,
                        "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
                        "asset": "SOC2",
                        "net_pnl_usd": 18.29,
                        "won": True,
                    },
                    {
                        "trade_id": "SOC2_HEDGE_L2",
                        "box_id": "SOC2_BOX_22386",
                        "is_dominance_box": True,
                        "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
                        "asset": "SOC2",
                        "net_pnl_usd": -17.64,
                        "won": False,
                    },
                ],
            },
        },
    )

    res = alt.scan_trades()
    assert res["status"] == "ALL_GOOD"
    assert res["uninspected_losses_count"] == 0
    assert res["newly_cleared_wins"] == 2


def test_soc2_rejects_first_half_and_second_half_btts_subperiods():
    """Verifies [SOC2-SUBPERIOD-1]: 1H/2H BTTS and sub-period markets are strictly vetoed from Full-Match 83-state SOC2 lattices."""
    from src.polymarket_research.riskless_frontier_v4_engine import (
        detect_soc2_lattice_boxes_and_converts,
        link_and_parse_soc2_exact_score_lattices,
    )

    now_ts = 1793700000.0
    ev_exact = {
        "id": "ev_vil_psg_exact",
        "slug": "ucl-vil-psg-2026-11-03-exact-score",
        "title": "Villarreal CF vs. Paris Saint-Germain FC - Exact Score",
        "gameId": "ucl_vil_psg_20261103",
        "startTime": "2026-11-03T20:00:00Z",
        "negRisk": True,
        "markets": [
            {
                "id": "6022000",
                "conditionId": "0x" + "a0" * 32,
                "question": "Will Villarreal CF vs. Paris Saint-Germain FC end 0-0?",
                "groupItemTitle": "0-0",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["tok_cs00_y", "tok_cs00_n"],
                "acceptingOrders": True,
            }
        ],
    }
    ev_more = {
        "id": "ev_vil_psg_more",
        "slug": "ucl-vil-psg-2026-11-03-more-markets",
        "title": "Villarreal CF vs. Paris Saint-Germain FC - More Markets",
        "gameId": "ucl_vil_psg_20261103",
        "startTime": "2026-11-03T20:00:00Z",
        "markets": [
            # Exact live Gamma bug reproduction: 2H BTTS + 1H BTTS + unlabeled 1H BTTS + 1H Total
            {
                "id": "6022412",
                "conditionId": "0x" + "b2" * 32,
                "question": "Villarreal CF vs. Paris Saint-Germain FC: Both Teams to Score in Second Half",
                "groupItemTitle": "Both Teams to Score in Second Half",
                "sportsMarketType": "both_teams_to_score_second_half",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["tok_2h_btts_y", "tok_2h_btts_n"],
                "acceptingOrders": True,
            },
            {
                "id": "6022386",
                "conditionId": "0x" + "b1" * 32,
                "question": "Villarreal CF vs. Paris Saint-Germain FC: Both Teams to Score in First Half",
                "groupItemTitle": "Both Teams to Score in First Half",
                "sportsMarketType": "both_teams_to_score_first_half",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["tok_1h_btts_y", "tok_1h_btts_n"],
                "acceptingOrders": True,
            },
            {
                "id": "6022387",
                "conditionId": "0x" + "b3" * 32,
                "question": "Villarreal CF vs. Paris Saint-Germain FC: Both Teams to Score in 1st Half",
                "groupItemTitle": "1H Both Teams to Score",
                "sportsMarketType": "",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["tok_1h_unlabeled_y", "tok_1h_unlabeled_n"],
                "acceptingOrders": True,
            },
            {
                "id": "6022388",
                "conditionId": "0x" + "b4" * 32,
                "question": "Villarreal CF vs. Paris Saint-Germain FC: First Half O/U 1.5",
                "groupItemTitle": "First Half O/U 1.5",
                "sportsMarketType": "totals",
                "line": 1.5,
                "outcomes": ["Over", "Under"],
                "clobTokenIds": ["tok_1h_ov15", "tok_1h_un15"],
                "acceptingOrders": True,
            },
            # Genuine Full-Match 90m BTTS market MUST still be parsed cleanly
            {
                "id": "6022350",
                "conditionId": "0x" + "bf" * 32,
                "question": "Villarreal CF vs. Paris Saint-Germain FC: Both Teams to Score",
                "groupItemTitle": "Both Teams to Score",
                "sportsMarketType": "both_teams_to_score",
                "outcomes": ["Yes", "No"],
                "clobTokenIds": ["tok_ft_btts_y", "tok_ft_btts_n"],
                "acceptingOrders": True,
            },
        ],
    }

    lattices = link_and_parse_soc2_exact_score_lattices([ev_exact, ev_more], now_ts=now_ts)
    assert "ucl_vil_psg_20261103" in lattices
    lat = lattices["ucl_vil_psg_20261103"]
    parsed_mids = {lg["market_id"] for lg in lat.matrix_legs}
    assert "6022412" not in parsed_mids
    assert "6022386" not in parsed_mids
    assert "6022387" not in parsed_mids
    assert "6022388" not in parsed_mids
    assert parsed_mids == {"6022000", "6022350"}

    # Even if 2H NO ($0.65) + 1H YES ($0.31) = $0.96, zero false boxes can form
    res = detect_soc2_lattice_boxes_and_converts(
        lat,
        books_by_token={},
        best_asks={
            "tok_2h_btts_n": 0.65,
            "tok_1h_btts_y": 0.31,
            "tok_1h_unlabeled_y": 0.31,
            "tok_ft_btts_y": 0.56,
            "tok_ft_btts_n": 0.46,
        },
        max_2leg_cost_net=0.990,
    )
    assert res["matrix_boxes"] == []


def test_harv_live_blocks_ungraduated_v3_and_enforces_true_sports_velocity_and_bond1_shield(tmp_path, monkeypatch):
    """
    Verifies [GOV-UNGRAD-1/2/3]:
      1. In LIVE v5 mode (dry_run=False, holistic_v5_live_mode=True), ungraduated _v3_g8 sleeves (e.g. SOC2 at 3W/0L)
         MUST NOT bypass _GRAD8 via v3_math_ok!
      2. Even once a sports sleeve graduates 8/8, an 18.7h lockup at $0.986 (7.49 bps/hr < 8.0 bps/hr) MUST NOT
         spoof a 4.0h hold time via fast_recycle_sl and is rejected by passes_capital_velocity_hurdle.
      3. Ungraduated d1_zf_bridge boxes (e.g. intraday SP3 at 0W/0L) MUST NOT preempt unrelated resting BOND1 orders
         and are capped <= 28% of Seed equity (~$19 on $68.11) rather than draining 90%+ of cash!
    """
    import src.polymarket_research.polymarket_live_harvester as plh

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "live_gov_state.json")

    now_ts = time.time()
    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {
                        "closed": 33,
                        "wins": 33,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 171.72,
                        "legging_adjusted_pnl_t1000_usd": 171.72,
                        "grad8_live_promoted": True,
                    },
                    "SOC2_EXACT_SCORE_2D_LATTICE": {
                        "closed": 3,
                        "wins": 3,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 9.50,
                        "legging_adjusted_pnl_t1000_usd": 9.50,
                        "grad8_live_promoted": False,
                    },
                    "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX": {
                        "closed": 3,
                        "wins": 3,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 13.82,
                        "legging_adjusted_pnl_t1000_usd": 13.82,
                        "grad8_live_promoted": False,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    harv = PolymarketLiveHarvester(dry_run=True)
    harv.dry_run = False
    harv.holistic_v5_live_mode = True
    harv._startup_reconciled = True
    harv.executor.dry_run = False
    harv.executor.auth_mode = "LIVE"
    harv.executor.is_authenticated = True
    harv.executor.is_heartbeat_healthy = lambda: True
    harv.executor.prewarm_token_market_cache = lambda **kw: None
    harv.executor.invalidate_collateral_cache = lambda: None
    harv._last_known_collateral = 68.11
    harv._wallet_token_balance = lambda _tok: (0.0, harv.ONCHAIN_SOURCE)

    tok_a = "1" * 28
    tok_b = "2" * 28
    opp_a = "3" * 28
    opp_b = "4" * 28
    books_4 = {
        tok_a: {"asks": [{"price": "0.64", "size": "100"}], "bids": [{"price": "0.57", "size": "100"}]},
        tok_b: {"asks": [{"price": "0.31", "size": "100"}], "bids": [{"price": "0.28", "size": "100"}]},
        opp_a: {"asks": [{"price": "0.43", "size": "100"}], "bids": [{"price": "0.36", "size": "100"}]},
        opp_b: {"asks": [{"price": "0.72", "size": "100"}], "bids": [{"price": "0.68", "size": "100"}]},
    }
    harv.executor.get_market_book = lambda tid: books_4[tid]

    # 1. Ungraduated SOC2 (3W/0L) in LIVE mode MUST be rejected at the _GRAD8 wall!
    soc2_cand = {
        "box_id": "SOC2_UNGRAD_LIVE",
        "dedupe_key": "DK_SOC2_UNGRAD",
        "box_type": "SPORTS_CORRIDOR",
        "sleeve_source": "SOC2_EXACT_SCORE_2D_LATTICE",
        "asset": "SOCCER",
        "ts_unix": now_ts,
        "expiry_ts": now_ts + 18.7 * 3600.0,
        "shares": 54,
        "box_cost_net": 0.986,
        "max_box_cost_net": 0.988,
        "leg_a_token_id": tok_a,
        "leg_a_opp_token_id": opp_a,
        "leg_a_market_id": "6022412",
        "leg_a_condition_id": "0x" + "a1" * 32,
        "leg_a_limit_price": 0.64,
        "leg_a_fee_rate": 0.05,
        "leg_a_fee_exponent": 1.0,
        "leg_b_token_id": tok_b,
        "leg_b_opp_token_id": opp_b,
        "leg_b_market_id": "6022386",
        "leg_b_condition_id": "0x" + "b2" * 32,
        "leg_b_limit_price": 0.31,
        "leg_b_fee_rate": 0.05,
        "leg_b_fee_exponent": 1.0,
    }
    # 0. Under default strict_pure_riskless_mode=True, evaluate_strict_pure_riskless_candidate hard-blocks SOC2!
    from src.polymarket_research.stage_c_zero_loss_velocity import evaluate_strict_pure_riskless_candidate

    plh.GLOBAL_GOVERNANCE_MANAGER.maybe_reload(force=True)
    ok_pure_soc2, why_pure_soc2 = evaluate_strict_pure_riskless_candidate(soc2_cand, plh.GLOBAL_GOVERNANCE_MANAGER.snapshot)
    assert ok_pure_soc2 is False
    assert "PURE_RISKLESS_SLEEVE_BLOCKED:SOC2_EXACT_SCORE_2D_LATTICE" in why_pure_soc2

    # Now isolate inner defense-in-depth layers (_GRAD8 wall, 18.7h velocity hurdle, and 28% canary cap):
    rb_inner = dict(plh.GLOBAL_GOVERNANCE_MANAGER._snapshot["riskless_boxes"])
    rb_inner["strict_pure_riskless_mode"] = False
    rb_inner["seed_max_lockup_hours"] = 24.0
    rb_inner["seed_min_bps_per_hour"] = 8.0
    rb_inner["enable_ungraduated_v3_math_live"] = False
    rb_inner["paused_riskless_sleeves"] = [
        s for s in rb_inner.get("paused_riskless_sleeves", [])
        if s not in {"SOC2_EXACT_SCORE_2D_LATTICE", "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX"}
    ]
    monkeypatch.setitem(plh.GLOBAL_GOVERNANCE_MANAGER._snapshot, "riskless_boxes", rb_inner)
    monkeypatch.setitem(harv.risk_config, "enable_ungraduated_v3_math_live", False)
    harv.enable_ungraduated_v3_math_live = False

    # 1. Ungraduated SOC2 (3W/0L) in LIVE mode MUST be rejected at the _GRAD8 wall!
    rej_ungrad = harv.maybe_execute_graduated_d1_box({**soc2_cand, "dedupe_key": "DK_SOC2_UNGRAD_INNER"})
    assert rej_ungrad["executed"] is False
    assert rej_ungrad["reason"] == "SLEEVE_NOT_YET_8_OF_8_GRADUATED:SOC2_EXACT_SCORE_2D_LATTICE"

    # 2. Even if SOC2 were 8/8 graduated, an 18.7h lockup at $0.986 (7.49 bps/hr < 8.0 bps/hr) MUST fail velocity!
    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {
                        "closed": 33,
                        "wins": 33,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 171.72,
                        "legging_adjusted_pnl_t1000_usd": 171.72,
                    },
                    "SOC2_EXACT_SCORE_2D_LATTICE": {
                        "closed": 8,
                        "wins": 8,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 35.0,
                        "legging_adjusted_pnl_t1000_usd": 35.0,
                    },
                    "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX": {
                        "closed": 3,
                        "wins": 3,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 13.82,
                        "legging_adjusted_pnl_t1000_usd": 13.82,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    harv._a124_grad_cache_mtime = -1.0
    rej_vel = harv.maybe_execute_graduated_d1_box({**soc2_cand, "dedupe_key": "DK_SOC2_SLOW18H"})
    assert rej_vel["executed"] is False
    assert rej_vel["reason"].startswith("LOW_CAPITAL_VELOCITY_LONG_TTE:")

    # 3. Ungraduated intraday SP3 (2.0h) MUST NOT preempt unrelated resting BOND1 orders and caps <= 28% ($19.07)!
    bond1_ev = asyncio.Event()
    harv.pending_entry_intents["MKR_BOND1_OTHER"] = {
        "trade_id": "MKR_BOND1_OTHER",
        "market_id": "MKT_UNRELATED_BOND1",
        "inflight_key": "KEY_UNRELATED_BOND1",
        "live_maker_anchor_inflight": True,
        "heartbeat_ts": time.time(),
        "notional_usd": 12.0,
    }
    harv._inflight_maker_anchor_keys = {"KEY_UNRELATED_BOND1"}
    harv._maker_anchor_preempt_events = {"KEY_UNRELATED_BOND1": bond1_ev}

    captured_budgets = []

    def _capture_exec(**kw):
        captured_budgets.append(float(kw["shares"]) * (float(kw["leg_a_limit_price"]) + float(kw["leg_b_limit_price"])))
        sh = float(kw["shares"])
        return {
            "success": True,
            "shares": sh,
            "leg_1": {"token_id": tok_a, "price": 0.64, "matched_shares": sh, "orderID": "0xSP3A"},
            "leg_2": {"token_id": tok_b, "price": 0.31, "matched_shares": sh, "orderID": "0xSP3B"},
        }

    harv.executor.execute_atomic_dominance_box = _capture_exec
    harv.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "0xTP99"}
    sp3_fast = {
        **soc2_cand,
        "box_id": "SP3_FAST_CANARY",
        "dedupe_key": "DK_SP3_FAST2H",
        "sleeve_source": "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
        "expiry_ts": now_ts + 2.0 * 3600.0,
        "box_cost_net": 0.985,
    }
    res_sp3 = harv.maybe_execute_graduated_d1_box(sp3_fast)
    assert bond1_ev.is_set() is False, "Ungraduated canary box MUST NOT preempt resting BOND1 on unrelated market!"
    assert res_sp3["executed"] is True
    assert captured_budgets[-1] <= 68.11 * 0.28 + 0.50


def test_paa_phase1_zero_loss_resolution_and_platform_discovery_fixes(monkeypatch, tmp_path):
    """
    Verifies PAA Phase 1 deterministic 0-parameter fixes:
      1. Unfilled `ENTRY_OUTCOME_UNKNOWN` Maker entry at market resolution settles as `NOT_EXECUTED`
         (`net_pnl_usd == 0.0`, `record_pnl=False`) even when CLOB purges `/data/order/{oid}` and `/data/orders` degrades.
      2. `evaluate_locked_market_reward_carry` accepts V2 `fees_enabled` (`fee_rate > 0.0`) markets (`0%` Maker fee!).
      3. `discover_uma_proposed_markets` extracts nested child markets from Gamma `/events` (propagating `negRisk`).
      4. `STATION_CATALOG` & `_SERIES_TO_ICAO` parse Polymarket's new `Jinan` (`ZSJN`) & `Zhengzhou` (`ZHCC`) METAR series.
    """
    import asyncio
    import time
    import pytest
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.macro_counting_ctf_engine import evaluate_locked_market_reward_carry
    from src.polymarket_research.weather_metar_engine import STATION_CATALOG, _SERIES_TO_ICAO
    import src.polymarket_research.alpha_124_shadow_daemon as a124_mod

    # 1. Unfilled ENTRY_OUTCOME_UNKNOWN Maker entry at resolution -> $0.00 PnL (never -$11.90 phantom loss!)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "live_harvester_state.json")
    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h.executor.auth_mode = "LIVE"
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.get_account_fills = lambda *a, **kw: []
    h.executor.get_order_status = lambda _oid: None  # Purged by CLOB on closed market
    h.executor.get_open_orders = lambda **kw: None   # Transient CLOB /data/orders timeout

    tid_unk = "MKR_LOCK1_LIVE_SPORTS_MONEYLINE_1793692777_61815"
    pos_unk = h._make_single_leg_lock_pos(
        tid_unk, "SINGLE_LEG_MAKER_LOCK", "BOND1_UMA_RESOLUTION_CARRY", "SPORTS_MONEYLINE", "maker_lock_1leg",
        "6561815", "0xbefc992acc53f275d9b49d85e23e312d68afc0d8fe6c82b4281feeab34d1b663",
        "9" * 30, "NO", False, 12.0, 11.904, 0.0, 0.0, 1.0,
        "maker_post_only_0pct", time.time() - 60.0, time.time() - 900.0, 0.0, "0x50b550a5", True, unk=True,
        sub_ts=time.time() - 1800.0,
    )
    h.active_positions[tid_unk] = pos_unk
    asyncio.run(h._apply_market_resolution(tid_unk, pos_unk, "NO"))
    assert tid_unk not in h.active_positions
    closed_unk = h.closed_positions[-1]
    assert closed_unk["status"] == "NOT_EXECUTED"
    assert closed_unk["close_reason"] == "ENTRY_NOT_EXECUTED_VERIFIED"
    assert closed_unk["net_pnl_usd"] == pytest.approx(0.0)
    assert closed_unk["non_execution_proof"] == "RESOLVED_MARKET_ONCHAIN_ZERO_AND_NO_FILLS"

    # 2. V2 fees_enabled Maker reward carry (`0.00%` post_only Maker fee!)
    rw_v2 = evaluate_locked_market_reward_carry(1.0, 0.975, 0.990, 20.0, 3.0, fee_rate=0.05)
    assert rw_v2["eligible"] is True
    assert 0.975 <= rw_v2["resting_bid"] <= 0.985

    # 3. Event child market extraction for BOND1 UMA discovery
    monkeypatch.setattr(a124_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124_mod, "STATE_FILE", tmp_path / "a124_state.json")
    d = a124_mod.Alpha124ShadowDaemon(single_scan=True)

    async def _fake_gamma_fetch(url: str, timeout: float = 5.0):
        if "/events?" in url and "offset=0" in url and "end_date_max" not in url:
            return [{
                "id": "ev_esports_1",
                "negRisk": True,
                "markets": [{
                    "id": "6500854",
                    "question": "Jay Clarke vs. Federico Bondioli: Total Sets O/U 2.5",
                    "sportsMarketType": "totals",
                    "active": True,
                    "closed": False,
                    "acceptingOrders": True,
                    "umaResolutionStatus": "proposed",
                    "umaResolutionStatuses": '["proposed"]',
                    "resolvedBy": "0x69c47de9d4d3dad79590d61b9e05918e03775f24",
                    "negRiskRequestID": "0x" + ("a" * 64),
                    "outcomes": '["Over 2.5", "Under 2.5"]',
                    "clobTokenIds": '["111111111111111111111", "222222222222222222222"]',
                }],
            }]
        return []

    d.fetch_json = _fake_gamma_fetch
    asyncio.run(d.discover_uma_proposed_markets(time.time()))
    assert "6500854" in d.uma_proposed_markets
    assert d.uma_proposed_markets["6500854"]["negRisk"] is True

    # 4. Jinan & Zhengzhou ICAO stations registered
    assert STATION_CATALOG["ZSJN"][3] == "Jinan"
    assert STATION_CATALOG["ZHCC"][3] == "Zhengzhou"
    assert _SERIES_TO_ICAO["jinan-daily-weather"] == "ZSJN"
    assert _SERIES_TO_ICAO["zhengzhou-daily-weather"] == "ZHCC"


def test_paa_phase2_bond1_repeg_prekickoff_ladder_and_reward_cap(monkeypatch, tmp_path):
    """
    Verifies PAA Phase 2 authorized live automation upgrades:
      1. BOND1 outbid repeg (`_bond1_repost_count > 0`) bypasses stale WS cache ($0.9910) and preserves
         `_rp_px_target` ($0.9940) above competing bid ($0.9930).
      2. PAA_Q2 unhedged `SPORTS_CORRIDOR` executes T-30m ($0.59) -> T-15m ($0.56) Maker step-down and
         hard T-5m FAK flatten (`limit_px = best_b - 0.03`) before kickoff.
      3. PAA_Q3 `MKR_REWARD_LOCKED_CARRY` enforces 8/8 `_GRAD8` gate + `$12.00` live budget cap, and
         `parse_weather_event` preserves `negRisk`, `rewardsMinSize`, and `rewardsMaxSpread`.
    """
    import asyncio
    import json
    import time
    import pytest
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.weather_metar_engine import parse_weather_event

    # --- 1. WeatherBucket neg_risk + clobRewards metadata ---
    ev_w = {
        "id": "ev_nyc_1",
        "slug": "highest-temperature-in-nyc-on-november-3-2026",
        "title": "Highest temperature in NYC on November 3?",
        "description": "Routine (METAR) and special (SPECI) reports from LaGuardia (KLGA) on November 3, 2026.",
        "seriesSlug": "nyc-daily-weather",
        "endDate": "2026-11-04T04:00:00Z",
        "negRisk": True,
        "markets": [
            {
                "id": f"m_{i}",
                "conditionId": f"0xcond{i}",
                "groupItemTitle": lbl,
                "question": f"NYC {lbl}",
                "clobTokenIds": json.dumps([f"100{i}", f"200{i}"]),
                "outcomes": '["Yes", "No"]',
                "rewardsMinSize": 20,
                "rewardsMaxSpread": 3.5,
            }
            for i, lbl in enumerate(["55°F or below", "56-57°F", "58-59°F", "60°F or higher"])
        ],
    }
    sp_w = parse_weather_event(ev_w)
    assert sp_w is not None
    assert sp_w.buckets[0].neg_risk is True
    assert sp_w.buckets[0].rewards_min_size == pytest.approx(20.0)
    assert sp_w.buckets[0].rewards_max_spread == pytest.approx(3.5)

    # --- 2. BOND1 Outbid Repeg Fix + PAA_Q3 $12.00 Live Cap ---
    a124_state = tmp_path / "alpha124_shadow_state.json"
    a124_state.write_text(json.dumps({
        "by_sleeve": {
            "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 32, "wins": 32, "losses": 0, "win_rate_pct": 100.0},
            "BOND1_UMA_RESOLUTION_CARRY": {"closed": 23, "wins": 23, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 10.80},
            "MKR_REWARD_LOCKED_CARRY": {"closed": 8, "wins": 8, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 4.20},
        }
    }), encoding="utf-8")
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_state.json")

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h.enforce_bond1_smart_queue = True
    h.executor.auth_mode = "LIVE"
    h._last_known_collateral = 60.0
    h.executor.get_collateral_balance = lambda: 60.0
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)

    class _StaleWS:
        def subscribe_tokens_immediate(self, _toks):
            pass

        def get_book(self, tok, max_age_sec=1.5):
            # Stale WS snapshot still at $0.9910 even though competitor bid $0.9930!
            if tok == "tok_win":
                return {"bids": [{"price": "0.991", "size": "100"}], "asks": [{"price": "0.999", "size": "100"}], "minimum_tick_size": "0.001"}
            return {"bids": [{"price": "0.001", "size": "100"}], "asks": []}

    h._pos_market_ws = _StaleWS()

    def _fresh_rest_book(tok):
        if tok == "tok_win":
            return {"bids": [{"price": "0.993", "size": "50"}], "asks": [{"price": "0.999", "size": "100"}], "minimum_tick_size": "0.001"}
        return {"bids": [{"price": "0.001", "size": "50"}], "asks": []}

    # Attach via class/type wrapper so `"get_market_book" not in h.executor.__dict__` matches production!
    monkeypatch.setattr(type(h.executor), "get_market_book", lambda _self, tok: _fresh_rest_book(tok))
    posted_entries = []

    def _capture_post(self_ex, token_id, price, notional_usd=0.0, **kw):
        posted_entries.append((token_id, price, notional_usd))
        return {"success": False, "error": "abort_after_capture"}

    monkeypatch.setattr(type(h.executor), "post_maker_entry_order", _capture_post)

    now = time.time()
    cand_repeg = {
        "box_id": "B1_REPEG_1",
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
        "dedupe_key": "DK_B1_REPEG",
        "pair_dedupe_key": "PK_B1_REPEG",
        "leg_a_market_id": "6599156",
        "leg_a_condition_id": "0xcond_b1",
        "leg_a_token_id": "tok_win",
        "leg_a_opp_token_id": "tok_opp",
        "leg_a_side": "NO",
        "leg_a_neg_risk": True,
        "anchor_bid_px": 0.994,
        "min_resting_bid": 0.985,
        "max_box_cost_net": 0.994,
        "min_maker_edge": 0.004,
        "max_opp_bid": 0.008,
        "p_model": 0.999,
        "expiry_ts": now + 3600.0,
        "ts_unix": now,
        "_bond1_repost_count": 1,
    }
    asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock(cand_repeg))
    assert len(posted_entries) == 1
    assert posted_entries[0][1] == pytest.approx(0.994), "Outbid repeg MUST post at $0.9940, never regress to $0.9920!"

    # Test PAA_Q3 $12.00 live cap on graduated MKR_REWARD_LOCKED_CARRY
    posted_entries.clear()
    h._pos_market_ws = None
    cand_rw = {
        **cand_repeg,
        "box_id": "RW_LOCK_1",
        "sleeve_source": "MKR_REWARD_LOCKED_CARRY",
        "dedupe_key": "DK_RW_1",
        "pair_dedupe_key": "PK_RW_1",
        "leg_a_market_id": "777001",
        "anchor_bid_px": 0.980,
        "min_resting_bid": 0.940,
        "max_box_cost_net": 0.990,
        "expiry_ts": now + 21600.0,
        "_bond1_repost_count": 0,
    }
    monkeypatch.setattr(type(h.executor), "get_market_book", lambda _self, tok: (
        {"bids": [{"price": "0.979", "size": "50"}], "asks": [{"price": "0.992", "size": "100"}], "minimum_tick_size": "0.001"}
        if tok == "tok_win" else {"bids": [{"price": "0.005", "size": "50"}], "asks": []}
    ))
    asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock(cand_rw))
    assert len(posted_entries) == 1
    _, rw_px, rw_notional = posted_entries[0]
    assert rw_notional <= 12.01, f"Live MKR_REWARD_LOCKED_CARRY notional must obey $12.00 cap (got {rw_notional:.2f})!"

    # --- 3. PAA_Q2 Unhedged SPORTS_CORRIDOR Step-Down & Hard T-5m Pre-Kickoff Flatten ---
    monkeypatch.setattr(plh, "RESOLUTIONS_FILE", tmp_path / "no_res.jsonl")
    h2 = plh.PolymarketLiveHarvester(dry_run=True)
    h2.dry_run = False
    h2.executor.auth_mode = "LIVE"
    h2.get_reference_spot_price = lambda _a: 0.0
    h2.poll_onchain_redemptions = lambda *_a, **_kw: None
    tid_sc = "SPORTS_CORRIDOR_LIVE_SOCCER_1793736000_22386_L1"
    kickoff_ts = time.time() + 1500.0  # T-25m (inside T-30m step-down window)
    pos_sc = {
        "trade_id": tid_sc,
        "market_id": "6022412",
        "condition_id": "0xsc1",
        "token_id": "999888777666555444333222111",
        "target_token": "NO",
        "asset": "SOCCER",
        "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
        "box_type": "SPORTS_CORRIDOR",
        "box_partner_trade_id": "",
        "is_dominance_box": True,
        "hold_to_maturity_lock": False,
        "inventory_reconciled": True,
        "status": plh.ExecutionStatus.POSITION_CONFIRMED,
        "exit_order_id": "0x6780edcd",
        "exit_order_status": "RESTING",
        "target_exit_price": 0.62,
        "entry_price": 0.65,
        "entry_shares": 54.0,
        "remaining_shares": 54.0,
        "remaining_exit_shares": 54.0,
        "remaining_cost_basis": 35.10,
        "notional_usd": 35.10,
        "candle_expiry_ts": kickoff_ts,
        "entry_ts": time.time() - 3600.0,
    }
    open_set = {"0x6780edcd"}
    h2.active_positions[tid_sc] = pos_sc
    h2.executor.get_open_orders = lambda **kw: [{"id": oid, "price": str(pos_sc["target_exit_price"]), "original_size": "54", "size_matched": "0"} for oid in open_set]
    h2.executor.get_order_fill_summary = lambda oid, tok: {"order_id": oid, "matched": 0.0, "cash": 0.0, "fee_usd": 0.0, "terminal": (oid not in open_set)}
    h2._pos_market_ws = None

    async def _sc_book(_tok):
        return {"bids": [{"price": "0.55", "size": "120"}], "asks": [{"price": str(pos_sc["target_exit_price"]), "size": "54"}]}

    h2.executor.get_market_book_async = _sc_book
    stepdowns = []

    async def _fake_replace(tid_in, pos_in, new_px):
        stepdowns.append(new_px)
        open_set.clear()
        pos_in["target_exit_price"] = new_px
        pos_in["exit_order_id"] = f"oid_{new_px:.2f}"
        open_set.add(pos_in["exit_order_id"])
        return True

    h2._atomic_replace_maker_exit = _fake_replace
    asyncio.run(h2.check_resolutions_and_manage_positions())
    assert stepdowns == [pytest.approx(0.59)]
    assert pos_sc["custom_maker_exit_price"] == pytest.approx(0.59)

    # Advance to T-10m (600s) and expire 180s stepdown cooldown -> steps down to $0.56 (best_b + 0.01)
    pos_sc["candle_expiry_ts"] = time.time() + 600.0
    pos_sc["_sc_step_ts"] = time.time() - 200.0
    asyncio.run(h2.check_resolutions_and_manage_positions())
    assert stepdowns[-1] == pytest.approx(0.56)

    # Advance to T-3m (180s, inside T-5m flatten window) -> cancels Maker ask and FAK-unwinds 100% pre-kickoff!
    pos_sc["candle_expiry_ts"] = time.time() + 180.0
    canceled_oids = []
    unwinds = []

    def _cancel_sc(oid):
        canceled_oids.append(oid)
        open_set.discard(oid)
        return {"canceled": [oid], "is_canceled": True}

    def _unwind_sc(token_id, size, side="SELL", min_price=0.01):
        unwinds.append((token_id, size, min_price))
        return {"success": True, "orderID": "0xfak_sc", "matched_size": size, "taking_amount": round(size * 0.55, 4), "fee_usd": 0.0}

    h2.executor.cancel_order = _cancel_sc
    h2.executor.execute_unwind_order = _unwind_sc
    asyncio.run(h2.check_resolutions_and_manage_positions())
    if not unwinds:
        asyncio.run(h2.check_resolutions_and_manage_positions())
    assert len(canceled_oids) == 1
    assert len(unwinds) == 1
    assert unwinds[0][1] == pytest.approx(54.0)
    assert unwinds[0][2] == pytest.approx(0.52)  # best_b ($0.55) - 0.03 sweep buffer
    assert tid_sc not in h2.active_positions






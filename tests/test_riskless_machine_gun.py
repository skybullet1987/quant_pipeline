#!/usr/bin/env python3
"""
Zero-Trust Unit & Integration Suite for the Polymarket Riskless Machine-Gun Architecture (Phase 0-3)
====================================================================================================
Covers:
  1. Multi-RPC Polygon Failover Pool (`PolygonRpcFailoverPool`, `POLYGON_RPC_URL` priority, failure demotion).
  2. Authoritative Exit Fee Rate Resolution (`resolve_authoritative_exit_fee_rate`), Anti-Box-Breaking Lock Guard
     (`is_locked_arbitrage_box_leg`), `SOC2` Non-Exhaustive Lattice Quarantine (`is_soc2_exhaustive_lattice_safe`),
     and Sports Dead-Ball Filter (`is_sports_dead_ball_safe`).
  3. Maker-Anchor `< $0.900` Deep-Discount Bug Fix (`execute_maker_anchor_hedge_or_unwind` at `$0.82` box cost).
  4. Multi-Clip Dedupe Unlock (`release_recycled_box_dedupe_keys`), Spot-Aware Dynamic Box Unwind Hurdle
     (`compute_dynamic_box_unwind_hurdle`), and Cross-Condition Complement-Pair Merge (`$2.00/pair` instant recycle).
  5. Batch `PostOrdersV2` (`m <= 15` `batch_post_fok_orders`), Atomic 1-Tx `NR3_SYNTHETIC_ALL_YES_OVERROUND`
     (`2x splitPosition + convertPositions(0b11)` + `2x` intra-tx collateral guard + `negRiskAugmented` rejection).
  6. `$12` `PreSplitInventoryGun` (split -> overround sweep, dual maker asks, `TTE <= 75s` `mergePositions`) and
     `20%` Crypto Maker Rebate Anchor (`evaluate_d1_maker_rebate_anchor` + `<350ms` spot guard).
  7. `Alpha124ShadowDaemon` `:45-:55` `4h/15m` overlap wakeup (`is_in_same_oracle_overlap_window`), 3-shard
     `600`-token CLOB WebSocket matrix (`_partition_ws_shards`), `NR0` `m <= 15`, and `SOC2` live gate.
"""

from __future__ import annotations

import asyncio
import collections
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.riskless_machine_gun_engine import (
    PreSplitInventoryGun,
    PolygonRpcFailoverPool,
    batch_post_fok_orders,
    build_nr3_atomic_mint_all_yes_calls,
    compute_crypto_maker_rebate_per_share,
    compute_dynamic_box_unwind_hurdle,
    detect_nr3_synthetic_all_yes_overround,
    evaluate_cross_condition_complement_merge,
    evaluate_d1_maker_rebate_anchor,
    execute_cross_condition_complement_merge,
    execute_nr3_synthetic_all_yes_overround,
    finish_nr3_convert_arb,
    is_locked_arbitrage_box_leg,
    is_soc2_exhaustive_lattice_safe,
    is_sports_dead_ball_safe,
    release_recycled_box_dedupe_keys,
    resolve_authoritative_exit_fee_rate,
)


def test_polygon_rpc_failover_pool_ranking_and_demotion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLYGON_RPC_URL", "https://custom-fast-rpc.example")
    pool = PolygonRpcFailoverPool(["https://slow.example", "https://fast.example"])
    cands = pool.candidate_urls()
    assert cands[0] == "https://custom-fast-rpc.example"
    assert "https://fast.example" in cands

    # Demote custom endpoint on failure -> healthy endpoint rises to #0
    pool._latencies_ms["https://fast.example"] = 15.0
    pool._latencies_ms["https://slow.example"] = 180.0
    pool._last_probe_ts = time.monotonic()
    pool.report_failure("https://custom-fast-rpc.example")
    ranked = pool.ordered_failover_urls()
    assert ranked[0] == "https://fast.example"


def test_phase0_safety_guards_exit_fee_box_lock_soc2_and_dead_ball() -> None:
    # 1. Authoritative exit fee lookup on live cache miss
    calls: List[str] = []

    class LiveExecStub:
        dry_run = False
        auth_mode = "AUTHENTICATED_L2"
        _fee_rate_cache: Dict[str, Any] = {}

        def get_market_fee_rate(self, token_id: str):
            calls.append(token_id)
            return (0.02, 1.0)

    ex = LiveExecStub()
    pos_cm = {"token_id": "1234567890123456789012345", "sleeve": "CM_B3", "asset": "COUNTING"}
    fr = resolve_authoritative_exit_fee_rate(ex, pos_cm)
    assert abs(fr - 0.02) < 1e-9
    assert calls == ["1234567890123456789012345"]
    assert abs( pos_cm["fee_rate_applied"] - 0.02 ) < 1e-9

    # 2. Anti-box-breaking lock guard: active paired box legs are locked; isolated single legs are not
    active = {
        "L1": {"trade_id": "L1", "is_dominance_box": True, "box_partner_trade_id": "L2"},
        "L2": {"trade_id": "L2", "is_dominance_box": True, "box_partner_trade_id": "L1"},
        "ISO": {"trade_id": "ISO", "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE"},
    }
    assert is_locked_arbitrage_box_leg(active["L1"], active) is True
    assert is_locked_arbitrage_box_leg(active["ISO"], active) is False

    # 3. SOC2 non-exhaustive 83-state lattice quarantine
    assert is_soc2_exhaustive_lattice_safe({"sleeve_source": "SOC2_EXACT_SCORE_2D_LATTICE"}) is False
    assert (
        is_soc2_exhaustive_lattice_safe(
            {"sleeve_source": "SOC2_EXACT_SCORE_2D_LATTICE", "exhaustive_partition_verified": True}
        )
        is True
    )
    assert is_soc2_exhaustive_lattice_safe({"sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX"}) is True

    # 4. Dead-ball sports filter
    assert is_sports_dead_ball_safe({"box_type": "SPORTS_CORRIDOR", "game_in_progress": True, "is_dead_ball": False}) is False
    assert is_sports_dead_ball_safe({"box_type": "SPORTS_CORRIDOR", "game_in_progress": True, "period_status": "HALFTIME"}) is True
    assert is_sports_dead_ball_safe({"box_type": "SPORTS_CORRIDOR", "game_in_progress": False}) is True


def test_maker_anchor_deep_discount_sub_90c_no_longer_aborts(tmp_path: Path) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "mkr_deep.jsonl")
    # Previously `worst_box_cost_net < 0.900` triggered `MAKER_ANCHOR_BOX_COST_OUTSIDE_CAP` and dumped the leg!
    res = ex.execute_maker_anchor_hedge_or_unwind(
        box_id="DEEP_ARB_82C",
        anchor_token_id="111111111111111111111",
        anchor_label="15M_UP",
        anchor_price=0.42,
        anchor_matched_shares=20.0,
        anchor_order_id="OID_ANC_1",
        hedge_token_id="222222222222222222222",
        hedge_label="5M_DOWN",
        hedge_limit_price=0.38,
        max_box_cost_net=0.990,
        hedge_fee_rate=0.07,
        hedge_fee_exponent=1.0,
    )
    assert res["success"] is True
    assert res["worst_box_cost_net"] < 0.85
    assert res["guaranteed_min_profit_usd"] > 3.0


def test_multiclip_dedupe_unlock_dynamic_corridor_hurdle_and_complement_merge() -> None:
    # 1. Multi-clip dedupe unlock + 2s cooldown
    harv = SimpleNamespace(
        _seen_d1_box_keys={"D1_BTC_1", "D1_PAIR_1"},
        _seen_d1_box_order=collections.deque(["D1_BTC_1", "D1_PAIR_1"]),
        _d1_retry_cooldown_until={},
    )
    p_a = {"dedupe_key": "D1_BTC_1", "pair_dedupe_key": "D1_PAIR_1"}
    released = release_recycled_box_dedupe_keys(harv, p_a, cooldown_sec=2.0)
    assert set(released) == {"D1_BTC_1", "D1_PAIR_1"}
    assert len(harv._seen_d1_box_keys) == 0
    assert len(harv._seen_d1_box_order) == 0
    assert harv._d1_retry_cooldown_until["D1_BTC_1"] > time.time()

    # 2. Spot-aware dynamic corridor unwind hurdle
    pos = {"box_cost_net": 0.985, "k_low": 84000.0, "k_high": 84250.0, "sigma_1h": 0.008}
    partner = {"box_cost_net": 0.985, "k_low": 84000.0, "k_high": 84250.0}
    hurdle_inside = compute_dynamic_box_unwind_hurdle(pos, partner, tte_rem=120.0, current_spot=84125.0)
    hurdle_outside = compute_dynamic_box_unwind_hurdle(pos, partner, tte_rem=120.0, current_spot=85600.0)
    assert hurdle_inside > 1.060  # Protects rich 2x corridor double-payout EV when spot sits mid-corridor!
    assert 0.992 <= hurdle_outside <= 1.006  # Immediately unlocks capital recycling once spot exits corridor!

    # 3. Cross-Condition Complement-Pair Merge ($2.00/pair instant recycle)
    pos_c = {
        "trade_id": "T_A",
        "box_id": "BOX_CC_1",
        "token_id": "tok_15_up",
        "opp_token_id": "tok_15_dn",
        "condition_id": "0x" + "11" * 32,
        "box_cost_net": 0.980,
        "fee_rate_applied": 0.0,
        "fee_exponent_applied": 1.0,
        "remaining_shares": 10.0,
        "k_low": 84000.0,
        "k_high": 84050.0,
    }
    part_c = {
        "trade_id": "T_B",
        "box_id": "BOX_CC_1",
        "token_id": "tok_5_dn",
        "opp_token_id": "tok_5_up",
        "condition_id": "0x" + "22" * 32,
        "box_cost_net": 0.980,
        "fee_rate_applied": 0.0,
        "fee_exponent_applied": 1.0,
        "remaining_shares": 10.0,
        "k_low": 84000.0,
        "k_high": 84050.0,
    }
    bk_opp_a = {"asks": [{"price": "0.48", "size": "50"}]}
    bk_opp_b = {"asks": [{"price": "0.49", "size": "50"}]}
    plan = evaluate_cross_condition_complement_merge(
        pos_c, part_c, bk_opp_a, bk_opp_b, pairs=10.0, tte_rem=90.0, current_spot=85500.0
    )
    assert plan is not None
    assert abs(plan["comp_cost_ps"] - 0.97) < 1e-6
    assert plan["recycle_edge_ps"] >= 0.045

    closed_ids: List[str] = []

    class ExecCCStub:
        def cancel_orders_batch(self, oids):
            return {o: {"is_canceled": True} for o in oids}

        def release_inventory(self, reservation_id: str) -> None:
            pass

        def execute_atomic_dominance_box(self, **kw):
            return {
                "success": True,
                "shares": 10.0,
                "leg_1": {"matched_shares": 10.0, "gross_shares": 10.0, "price": 0.48},
                "leg_2": {"matched_shares": 10.0, "gross_shares": 10.0, "price": 0.49},
            }

        def attempt_onchain_complete_set_merge(self, cid, min_pairs=5.0, max_pairs=None, neg_risk=None):
            return (f"0xmerge_{cid[:8]}", 10.0)

        def invalidate_collateral_cache(self) -> None:
            pass

    class HarvCCStub:
        dry_run = False
        executor = ExecCCStub()
        _seen_d1_box_keys = {"DK_CC"}
        _seen_d1_box_order = collections.deque(["DK_CC"])
        _d1_retry_cooldown_until: Dict[str, float] = {}
        _pending_collateral_refresh = False

        def record_fill_and_update_position(self, p, oid, sh, cash, fee, cash_is_estimated=False):
            p["remaining_shares"] = max(0.0, float(p["remaining_shares"]) - sh)

        def _close_position(self, tid, p, st, reason, won=True):
            closed_ids.append(tid)

        def save_state(self) -> None:
            pass

    pos_c["dedupe_key"] = "DK_CC"
    ok_cc = asyncio.run(execute_cross_condition_complement_merge(HarvCCStub(), "T_A", pos_c, "T_B", part_c, plan, set(), time.time()))
    assert ok_cc is True
    assert closed_ids == ["T_A", "T_B"]


def test_batch_post_orders_v2_and_nr3_synthetic_all_yes_overround(tmp_path: Path) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    # 1. Batch PostOrdersV2 dispatches 10 legs in 1 single HTTP call
    batch_calls: List[int] = []

    class BatchClientStub:
        def post_orders(self, args_list, post_only=False, defer_exec=True):
            batch_calls.append(len(args_list))
            return [{"orderID": f"B_{i}", "status": "MATCHED"} for i in range(len(args_list))]

    ex_stub = SimpleNamespace(client=BatchClientStub())
    res_10 = batch_post_fok_orders(
        ex_stub,
        [{"leg": i} for i in range(10)],
        "FOK",
        post_one_fallback=lambda sg: ({"orderID": "FALLBACK"}, None),
    )
    assert len(res_10) == 10
    assert batch_calls == [10]

    # 2. NR3 atomic 3-call calldata builder (2x splitPosition + convertPositions(0b11))
    calls = build_nr3_atomic_mint_all_yes_calls(
        "0x" + "ab" * 32,
        "0x" + "01" * 32,
        "0x" + "02" * 32,
        0,
        1,
        15.0,
    )
    assert len(calls) == 3
    assert calls[0][1].startswith("0xa3d7da1d")  # NegRiskAdapter.splitPosition(bytes32,uint256)
    assert calls[1][1].startswith("0xa3d7da1d")  # NegRiskAdapter.splitPosition(bytes32,uint256)
    assert calls[2][1].startswith("0xc64748c4")  # convertPositions

    # 3. NR3 detector + augmented slate rejection + dry-run execution + 2x peak collateral check
    brackets = [
        {"yes_token": f"y_{i}", "no_token": f"n_{i}", "market_id": f"m_{i}", "condition_id": f"0x{i+1:064x}", "question_index": i, "label": f"B{i}", "fee_rate": 0.0, "fee_exponent": 1.0}
        for i in range(4)
    ]
    books = {f"y_{i}": {"bids": [{"price": "0.26", "size": "100"}]} for i in range(4)}  # Sum YES bids = $1.04!
    spec_safe = SimpleNamespace(
        neg_risk_market_id="0x" + "cd" * 32,
        event_id="ev_nr3",
        title="Closed 4-Way Election",
        is_closed_convert_safe=True,
        neg_risk_augmented=False,
        enable_neg_risk_other=False,
        total_market_count=4,
        brackets=brackets,
    )
    spec_aug = SimpleNamespace(**{**spec_safe.__dict__, "neg_risk_augmented": True})
    assert detect_nr3_synthetic_all_yes_overround(spec_aug, books) is None
    hit = detect_nr3_synthetic_all_yes_overround(spec_safe, books, target_budget_usd=20.0, min_net_edge_per_set=0.01)
    assert hit is not None
    assert hit["shares"] == 20
    assert abs(hit["net_edge_per_share"] - 0.04) < 1e-5

    ex_dry = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "nr3.jsonl")
    r_nr3 = execute_nr3_synthetic_all_yes_overround(
        ex_dry,
        convert_id="NR3_TEST_1",
        neg_risk_market_id=hit["neg_risk_market_id"],
        split_cond_0=hit["split_cond_0"],
        split_cond_1=hit["split_cond_1"],
        split_q_idx_0=hit["split_q_idx_0"],
        split_q_idx_1=hit["split_q_idx_1"],
        yes_sell_legs=hit["yes_sell_legs"],
        shares=15,
    )
    assert r_nr3["success"] is True and r_nr3["atomic_calls_count"] == 3 and abs(r_nr3["net_profit_usd"] - 0.60) < 1e-4

    # 2x peak collateral check in live harvester wrapper: $9.00 wallet (< 5 * 2.02 = $10.10) must reject cleanly!
    harv_low = SimpleNamespace(dry_run=False, executor=ex_dry, closed_positions=[], _seen_d1_box_keys=set(), _seen_d1_box_order=collections.deque(), _d1_retry_cooldown_until={})
    rej = finish_nr3_convert_arb(
        harv_low,
        {"convert_mode": "NR3_SYNTHETIC_ALL_YES_OVERROUND", **hit},
        sleeve_src="NR2_CONVERT_NO_SUBSET_ARB",
        nrm_id=hit["neg_risk_market_id"],
        dedupe_k="DK_NR3",
        budget=15.0,
        collat_f=9.0,
        fee_bips=0,
        now_ts=time.time(),
    )
    assert rej["executed"] is False and rej["reason"] == "INSUFFICIENT_NR3_2X_PEAK_COLLATERAL"


def test_pre_split_inventory_gun_and_20pct_crypto_maker_rebate(tmp_path: Path) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    # 1. 20% Crypto Maker Rebate formula + <350ms spot freshness guard
    reb = compute_crypto_maker_rebate_per_share(0.50, fee_rate=0.07, fee_exponent=1.0)
    assert abs(reb - (0.20 * 0.07 * 0.25)) < 1e-9  # +0.35c/share at p=0.50!
    ev_stale = evaluate_d1_maker_rebate_anchor(
        anchor_bid_px=0.49, anchor_ask_px=0.51, hedge_ask_px=0.48, hedge_avail_shares=60.0, req_shares=12.0, spot_age_ms=500.0
    )
    assert ev_stale["eligible"] is False and ev_stale["reason"] == "STALE_SPOT_FEED"
    ev_ok = evaluate_d1_maker_rebate_anchor(
        anchor_bid_px=0.49, anchor_ask_px=0.51, hedge_ask_px=0.48, hedge_avail_shares=60.0, req_shares=12.0, spot_age_ms=80.0
    )
    assert ev_ok["eligible"] is True and ev_ok["net_rebated_box_cost"] <= 0.992

    # 2. PreSplitInventoryGun lifecycle: Split $12 -> Overround Sweep -> Auto-Merge at TTE <= 75s
    ex_dry = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "psg.jsonl")
    ex_dry.attempt_onchain_complete_set_merge = lambda cid, min_pairs=5.0, max_pairs=None, neg_risk=False: (
        "0xdry_merge_psg",
        float(max_pairs or min_pairs),
    )
    gun = PreSplitInventoryGun(cap_usd=12.0, min_free_cash_usd=36.0)
    now = 1793760000.0
    exp = now + 400.0
    up_tok = "111111111111111111111111"
    dn_tok = "222222222222222222222222"
    books_ovr = {
        up_tok: {"bids": [{"price": "0.53", "size": "50"}], "asks": [{"price": "0.54", "size": "50"}]},
        dn_tok: {"bids": [{"price": "0.52", "size": "50"}], "asks": [{"price": "0.53", "size": "50"}]},
    }

    class HarvGunStub:
        dry_run = False
        _startup_reconciled = True
        global_halt_active = False
        executor = ex_dry
        active_positions: Dict[str, Any] = {}
        closed_positions: List[Dict[str, Any]] = []
        pre_split_inventory_state: Dict[str, Any] = {}
        _last_known_collateral = 61.0
        _pending_collateral_refresh = False

        def save_state(self) -> None:
            pass

    harv_g = HarvGunStub()
    shm_tick = {
        "asset": "BTC",
        "timestamp_unix": now,
        "condition_id": "0x" + "aa" * 32,
        "market_id": "mkt_btc_15m",
        "up_token_id": up_tok,
        "down_token_id": dn_tok,
        "candle_expiry_ts": exp,
        "spot_price": 84100.0,
        "candle_open_spot": 84000.0,
        "books": books_ovr,
    }
    # Tick 1: Mints 12 UP + 12 DOWN complete sets
    r1 = asyncio.run(gun.tick(harv_g, now_ts=now, fast_tick_reader=lambda _a: shm_tick))
    assert r1 == "ARMED"
    assert harv_g.pre_split_inventory_state["initial_shares"] == 12.0

    # Tick 2: Instant overround sweep (`0.53 + 0.52 = 1.05` gross > fees + `$1.004`)
    shm_tick["timestamp_unix"] = now + 1.0
    r2 = asyncio.run(gun.tick(harv_g, now_ts=now + 1.0, fast_tick_reader=lambda _a: shm_tick))
    assert r2 == "PRE_SPLIT_OVERROUND_SWEEP"
    assert len(harv_g.closed_positions) == 1
    assert harv_g.closed_positions[-1]["net_pnl_usd"] > 0.10

    # Tick 3 + 4: Re-split on next candle and verify TTE <= 75s automatic `mergePositions` zero-exposure exit
    books_normal = {
        up_tok: {"bids": [{"price": "0.49", "size": "50"}], "asks": [{"price": "0.51", "size": "50"}]},
        dn_tok: {"bids": [{"price": "0.48", "size": "50"}], "asks": [{"price": "0.50", "size": "50"}]},
    }
    shm_tick2 = {
        **shm_tick,
        "timestamp_unix": now + 5.0,
        "condition_id": "0x" + "bb" * 32,
        "market_id": "mkt_btc_15m_2",
        "candle_expiry_ts": now + 350.0,
        "books": books_normal,
    }
    r3 = asyncio.run(gun.tick(harv_g, now_ts=now + 5.0, fast_tick_reader=lambda _a: shm_tick2))
    assert r3 == "ARMED"
    shm_tick2["timestamp_unix"] = now + 290.0
    r4 = asyncio.run(gun.tick(harv_g, now_ts=now + 290.0, fast_tick_reader=lambda _a: shm_tick2))
    assert r4 == "PRE_SPLIT_PRE_EXPIRY_MERGED"
    assert not harv_g.pre_split_inventory_state.get("active")


def test_alpha124_4h_overlap_wakeup_and_3shard_600_token_ws_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import src.polymarket_research.alpha_124_shadow_daemon as a124

    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "st_ws.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "lg_ws.jsonl")

    # 1. `:45-:55` 4h/15m overlap window (`rem_4h = 600s`, `rem_15m = 600s`) now wakes `is_in_same_oracle_overlap_window`!
    t_4h_end = 14400.0 * 125000  # Exact 4h boundary
    assert a124.Alpha124ShadowDaemon.is_in_same_oracle_overlap_window(t_4h_end - 600.0) is True  # :50 (10m before 4h close!)
    assert a124.Alpha124ShadowDaemon.is_in_same_oracle_overlap_window(t_4h_end - 1400.0) is False  # :36:40 (outside both 4h & 15m/5m overlaps)

    # 2. 3-shard 600-token WebSocket partitioning
    d = a124.Alpha124ShadowDaemon(single_scan=True)
    now = time.time()
    for idx in range(60):
        d.negrisk_zero_slates[f"ev_{idx}"] = SimpleNamespace(
            event_id=f"ev_{idx}",
            end_ts=now + 3600.0,
            brackets=[
                {"no_token": f"tok_no_{idx}_{j}", "yes_token": f"tok_yes_{idx}_{j}"}
                for j in range(6)
            ],
        )
    shards = d._partition_ws_shards(now)
    assert len(shards) == 3
    assert len(shards[0]) == 200
    assert len(shards[1]) == 200
    assert len(shards[2]) == 200
    assert len(set(shards[0]) | set(shards[1]) | set(shards[2])) == 600
    assert len(d._ws_nr_priority_tokens) == 600


def test_production_shm_subdict_pre_split_zero_loss_and_dead_no_reward_bridge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    from src.polymarket_research.riskless_machine_gun_engine import is_reward_locked_carry_live_ready

    # 1. Production `/dev/shm/pm_fast_tick_BTC.json` (`m15` subdict) skips idle split until overround >= $1.004,
    #    NEVER posts naked 1-leg maker asks under `riskless_only_mode`, and sweeps overround cleanly.
    ex_dry = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "psg_shm.jsonl")
    maker_exit_calls: List[Any] = []
    ex_dry.post_maker_exit_order = lambda **kw: (maker_exit_calls.append(kw) or {"success": True, "orderID": "BAD_NAKED_ASK"})
    ex_dry.attempt_onchain_complete_set_merge = lambda cid, min_pairs=5.0, max_pairs=None, neg_risk=False: (
        "0xdry_merge_shm",
        float(max_pairs or min_pairs),
    )

    gun = PreSplitInventoryGun(cap_usd=12.0)
    gun._cid_cache["6624916"] = "0x" + "cc" * 32
    now = 1793767000.0
    up_tok = "101047705223554566556690137231700604189599157098181477001735400979375505855882"
    dn_tok = "31007079463241544411876302509175691935057850031139968483533287340779867204003"

    class HarvProdStub:
        dry_run = False
        _startup_reconciled = True
        global_halt_active = False
        executor = ex_dry
        active_positions: Dict[str, Any] = {}
        pending_entry_intents: Dict[str, Any] = {"B1": {"notional_usd": 40.0}}
        closed_positions: List[Dict[str, Any]] = []
        pre_split_inventory_state: Dict[str, Any] = {}
        _last_known_collateral = 61.01  # $21.01 free cash after $40 BOND1 intent (>= $18.0 min_free_cash_usd!)
        _pending_collateral_refresh = False

        def save_state(self) -> None:
            pass

    harv_p = HarvProdStub()
    shm_normal = {
        "ts": now,
        "timestamp_unix": now,
        "asset": "BTC",
        "spot_price": 76642.0,
        "m15": {
            "market_id": "6624916",
            "horizon": "15m",
            "expiry_ts": now + 500.0,
            "authoritative_chainlink_open": 76600.0,
            "UP": {"token_id": up_tok, "raw_top_bids": [[0.49, 80.0]], "raw_top_asks": [[0.51, 80.0]]},
            "DOWN": {"token_id": dn_tok, "raw_top_bids": [[0.49, 80.0]], "raw_top_asks": [[0.51, 80.0]]},
        },
    }
    # Normal book (`0.49 + 0.49 = 0.98 < 1.004`) -> $0 split, $0 gas, $0 capital locked!
    assert asyncio.run(gun.tick(harv_p, now_ts=now, fast_tick_reader=lambda _a: shm_normal)) is None
    assert not harv_p.pre_split_inventory_state.get("active")

    # Overround book (`0.53 + 0.52 = 1.05` gross -> net > 1.004) -> splits $12 on Tick 1, sweeps on Tick 2, 0 naked maker asks!
    shm_ovr = {
        **shm_normal,
        "timestamp_unix": now + 1.0,
        "m15": {
            **shm_normal["m15"],
            "UP": {"token_id": up_tok, "raw_top_bids": [[0.53, 80.0]], "raw_top_asks": [[0.54, 80.0]]},
            "DOWN": {"token_id": dn_tok, "raw_top_bids": [[0.52, 80.0]], "raw_top_asks": [[0.53, 80.0]]},
        },
    }
    assert asyncio.run(gun.tick(harv_p, now_ts=now + 1.0, fast_tick_reader=lambda _a: shm_ovr)) == "ARMED"
    # Even if book normalizes mid-candle, supervision NEVER posts naked 1-leg maker asks under riskless_only_mode!
    shm_mid = {**shm_normal, "timestamp_unix": now + 2.0}
    assert asyncio.run(gun.tick(harv_p, now_ts=now + 2.0, fast_tick_reader=lambda _a: shm_mid)) == "SUPERVISED"
    assert maker_exit_calls == []
    # Next overround spike sweeps both legs atomically!
    shm_ovr["timestamp_unix"] = now + 3.0
    assert asyncio.run(gun.tick(harv_p, now_ts=now + 3.0, fast_tick_reader=lambda _a: shm_ovr)) == "PRE_SPLIT_OVERROUND_SWEEP"
    assert len(harv_p.closed_positions) == 1 and harv_p.closed_positions[-1]["net_pnl_usd"] > 0.10

    # 2. Dead-NO `MKR_REWARD_LOCKED_CARRY` live bridge gate (`p_model == 1.0` unlocked, `p_model == 0.998` gated)
    fake_daemon = SimpleNamespace(
        is_sleeve_grad8_ready=lambda sl: sl == "D1_SAME_ORACLE_DOMINANCE_BOX",
        closed_positions=[],
    )
    assert is_reward_locked_carry_live_ready(fake_daemon, 1.0) is True
    assert is_reward_locked_carry_live_ready(fake_daemon, 0.998) is False
    fake_daemon.closed_positions.append({"sleeve": "MKR_REWARD_LOCKED_CARRY", "won": False})
    assert is_reward_locked_carry_live_ready(fake_daemon, 1.0) is False


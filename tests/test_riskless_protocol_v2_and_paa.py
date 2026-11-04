from __future__ import annotations

import asyncio
import copy
import json
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.polymarket_research.holistic_strategy_governance import (
    DEFAULT_HOLISTIC_CONFIG,
    passes_capital_velocity_hurdle,
)
from src.polymarket_research.polymarket_ws_streams import (
    CHAINLINK_SYMBOL_MAP,
    PolymarketChainlinkLiveStream,
)
from src.polymarket_research.riskless_machine_gun_engine import PreSplitInventoryGun
from src.polymarket_research.riskless_protocol_v2_expansion import (
    PROTOCOL_V2_ADDRESSES,
    CompleteSetRewardShield,
    RebootPostOnlyModeGuard,
    compute_running_metar_extrema,
    detect_b1_intraday_onetouch_noon_box,
    detect_d1_telescoping_candle_bridge,
    detect_dc1_double_chance_1x2_parity,
    detect_eq1_pyth_equity_dominance_box,
    detect_halftime_freeze_offset_box,
    detect_lp_comp1_sports_triangles,
    detect_mention1_cumulative_ladder_box,
    detect_nr4_nr5_optimal_tail_convert,
    detect_nr6_cross_slate_surjection_box,
    detect_w_prune1_metar_slate_arb,
    evaluate_s2_rtds_exact_twap_integrator,
    execute_binary_ctf_overround_mint_sell,
    execute_multi_leg_all_yes_bundle,
    get_cached_negrisk_fee_bips,
    has_us_overtime_inequality,
    is_protocol_v2_market,
    parse_routine_metar_temp_c,
    quantize_dynamic_tick_price,
    scan_full_universe_c1_and_ctf_overround,
    score_uma_ready1_liveness_priority,
    verify_v2_negrisk_other_partition,
)
from src.paa_os.accountant import PAAAccountant
from src.paa_os.budget import BudgetManager
from src.paa_os.monitor import PAAMonitor
from src.paa_os.optimizer import PAAOptimizer, group_closed_positions_by_box
from src.paa_os.permissions import PermissionGate
from src.paa_os.task_db import PAATaskDB


def test_protocol_v2_registry_partition_tick_and_reboot_guard() -> None:
    assert PROTOCOL_V2_ADDRESSES["ExchangeV3"] == "0xe3333700cA9d93003F00f0F71f8515005F6c00Aa"
    assert PROTOCOL_V2_ADDRESSES["PositionManager"] == "0x006F54F7f9A22e0000CC2AB60031000000ae9fEF"
    assert PROTOCOL_V2_ADDRESSES["Router"] == "0x12121212006e4CD160D18e3f00711DA5c3372600"
    assert PROTOCOL_V2_ADDRESSES["AutoRedeemer"] == "0xa1200000d0002264C9a1698e001292D00E1b00af"

    assert is_protocol_v2_market({"exchangeAddress": PROTOCOL_V2_ADDRESSES["ExchangeV3"].lower()}) is True
    assert is_protocol_v2_market({"protocolVersion": "v1"}) is False

    # Augmented NegRisk without "Other" MUST be rejected
    bad_aug = [
        {"label": "Candidate A", "enableOrderBook": True},
        {"label": "Candidate B", "enableOrderBook": True},
        {"label": "Candidate C", "enableOrderBook": True},
    ]
    ok_bad, info_bad = verify_v2_negrisk_other_partition(bad_aug, event_meta={"enableNegRisk": True, "augmentedNegRisk": True})
    assert ok_bad is False
    assert "MISSING" in info_bad["reason"] or "OTHER" in info_bad["reason"]

    # Augmented NegRisk with tradable "Other" passes; unnamed placeholder fails
    good_aug = bad_aug + [{"label": "Other", "enableOrderBook": True}]
    ok_good, _ = verify_v2_negrisk_other_partition(good_aug, event_meta={"augmentedNegRisk": True})
    assert ok_good is True

    ok_ph, info_ph = verify_v2_negrisk_other_partition(
        bad_aug + [{"label": "Player X", "enableOrderBook": True}, {"label": "Other", "enableOrderBook": True}],
        event_meta={"augmentedNegRisk": True},
    )
    assert ok_ph is False
    assert info_ph["reason"] == "UNNAMED_PLACEHOLDER_OUTCOME_PRESENT"

    # Dynamic 0.001 tick boundary quantizer & 5-share minimum
    q_hi, t_hi, ok_sh = quantize_dynamic_tick_price(0.9944, "BUY", shares=5.0, mode="maker")
    assert t_hi == 0.001
    assert q_hi == 0.994
    assert ok_sh is True
    _, _, ok_small = quantize_dynamic_tick_price(0.50, "BUY", shares=4.9, mode="taker")
    assert ok_small is False

    # Cached NegRisk getFeeBips with deterministic offline fallback
    bips = get_cached_negrisk_fee_bips("0x" + "ab" * 32, rpc_url="", fallback_bips=25)
    assert bips == 25

    # REBOOT1 HTTP 425 post-only mode catcher
    guard = RebootPostOnlyModeGuard(window_ttl_sec=30.0)
    assert guard.observe_response(425, "Too Early: matching engine in post_only_mode", now_ts=1000.0) is True
    assert guard.should_suppress_taker(now_ts=1015.0) is True
    assert guard.should_suppress_taker(now_ts=1035.0) is False
    quotes = guard.build_reboot_post_only_quotes("tok_y", "tok_n", 0.52, max_pair_bid_sum=0.980, shares=6.0)
    assert quotes is not None
    assert quotes["post_only"] is True
    assert quotes["pair_bid_sum"] <= 0.980


def test_nr4_optimal_channel_nr5_freeroll_and_nr6_surjection() -> None:
    outcomes = [
        {"label": "Fav 1", "yes_token_id": "y0", "no_token_id": "n0", "no_ask": 0.48, "no_ask_size": 20, "yes_bid": 0.54, "yes_bid_size": 25},
        {"label": "Fav 2", "yes_token_id": "y1", "no_token_id": "n1", "no_ask": 0.65, "no_ask_size": 20, "yes_bid": 0.36, "yes_bid_size": 25},
        {"label": "Mid 3", "yes_token_id": "y2", "no_token_id": "n2", "no_ask": 0.91, "no_ask_size": 20, "yes_bid": 0.06, "yes_bid_size": 25},
        {"label": "Tail 4", "yes_token_id": "y3", "no_token_id": "n3", "no_ask": 0.962, "no_ask_size": 20, "yes_bid": 0.015, "yes_bid_size": 20},
        {"label": "Other", "yes_token_id": "y4", "no_token_id": "n4", "no_ask": 0.971, "no_ask_size": 20, "yes_bid": 0.005, "yes_bid_size": 20},
    ]
    # Buying NO on Mid 3 (0.91) + Tail 4 (0.962) + Other (0.971) = 2.843
    # Conversion yields (3 - 1) = $2.00 cash + YES(Fav 1) + YES(Fav 2); selling Fav 1 (0.54) + Fav 2 (0.36) = $0.90 -> $2.90 total!
    # Even better: if Tail 4 is left in S^c (`m=2`: NO(Mid3=0.91)+NO(Other=0.971)=1.881 -> $1.00 cash + sell Fav1(0.54)+Fav2(0.36)=$0.90 -> $1.900 > $1.881 while keeping FREE Tail 4 YES!)
    hits = detect_nr4_nr5_optimal_tail_convert(
        outcomes,
        event_id="ev_nr",
        neg_risk_market_id="0x" + "11" * 32,
        event_meta={"augmentedNegRisk": True},
        fee_bips=0,
        min_net_edge_usd=0.005,
        min_freeroll_cash_usd=0.005,
    )
    sleeves = {h["sleeve"]: h for h in hits}
    assert "NR4_OPTIMAL_CHANNEL_CONVERT" in sleeves
    assert "NR5_LOTTERY_FREEROLL_CONVERT" in sleeves
    assert sleeves["NR5_LOTTERY_FREEROLL_CONVERT"]["freeroll_ticket_count"] >= 1
    assert sleeves["NR5_LOTTERY_FREEROLL_CONVERT"]["net_edge_per_share"] > 0.0

    # NR6 Cross-Slate Surjection: A1 \sqcup A2 \subseteq B -> NO(A1) + NO(A2) + YES(B) pays >= $2.00
    nr6 = detect_nr6_cross_slate_surjection_box(
        fine_legs=[
            {"no_token_id": "na1", "no_ask": 0.72, "no_ask_size": 10},
            {"no_token_id": "na2", "no_ask": 0.78, "no_ask_size": 10},
        ],
        coarse_leg={"yes_token_id": "yb", "yes_ask": 0.46, "yes_ask_size": 10},
        relation="DISJOINT_SUBSET_OF_COARSE",
        same_oracle_verified=True,
    )
    assert nr6 is not None
    assert nr6["guaranteed_payout_per_share"] == 2.0
    assert nr6["net_edge_per_share"] >= 0.03


def test_s2_rtds_d1_telescoping_b1_noon_and_eq1_pyth() -> None:
    now_ts = 1_800_000_050.0
    expiry_ts = 1_800_000_060.0  # 10s left in 60s TWAP window (50 ticks banked!)
    ticks = [(expiry_ts - 60.0 + i, 95_250.0 + (i % 3) * 1.5) for i in range(51)]
    s2 = evaluate_s2_rtds_exact_twap_integrator(
        asset="BTC",
        open_price=95_000.0,
        expiry_ts=expiry_ts,
        rtds_ticks=ticks,
        up_ask=0.91,
        down_ask=0.12,
        now_ts=now_ts,
        official_twap_60s=95_251.5,
    )
    assert s2 is not None
    assert s2["direction"] == "UP"
    assert s2["p_model"] >= 0.995

    # Reject if official `crypto_prices_twap_sixty` diverges from local accumulator
    assert (
        evaluate_s2_rtds_exact_twap_integrator(
            asset="BTC",
            open_price=95_000.0,
            expiry_ts=expiry_ts,
            rtds_ticks=ticks,
            up_ask=0.91,
            down_ask=0.12,
            now_ts=now_ts,
            official_twap_60s=94_000.0,
        )
        is None
    )

    d1 = detect_d1_telescoping_candle_bridge(
        asset="XAG",
        outer_horizon="1h",
        inner_horizon="15m",
        outer_expiry_ts=expiry_ts,
        inner_expiry_ts=expiry_ts,
        outer_open=32.10,
        inner_open=32.35,
        outer_up_ask=0.47,
        outer_down_ask=0.55,
        inner_up_ask=0.54,
        inner_down_ask=0.45,
        outer_up_token="ou",
        outer_down_token="od",
        inner_up_token="iu",
        inner_down_token="id",
        now_ts=expiry_ts - 120.0,
        fee_rate_outer=0.07,
        fee_rate_inner=0.07,
    )
    assert d1 is not None
    assert d1["asset"] == "XAG"
    assert d1["net_edge_per_share"] > 0.02

    # B1 Noon vs OneTouch: identical oracle passes; mismatched oracle rejected
    assert (
        detect_b1_intraday_onetouch_noon_box(
            asset="BTC",
            strike=100_000.0,
            direction="ABOVE",
            oracle_touch="binance_btcusdt_1m",
            oracle_noon="chainlink_btc_usd",
            touch_yes_ask=0.45,
            noon_no_ask=0.50,
            touch_yes_token="ty",
            noon_no_token="nn",
            et_hour_float=11.0,
        )
        is None
    )
    b1 = detect_b1_intraday_onetouch_noon_box(
        asset="BTC",
        strike=100_000.0,
        direction="ABOVE",
        oracle_touch="binance_btcusdt_1m",
        oracle_noon="binance_btcusdt_1m",
        touch_yes_ask=0.45,
        noon_no_ask=0.52,
        touch_yes_token="ty",
        noon_no_token="nn",
        et_hour_float=11.25,
    )
    assert b1 is not None
    assert b1["net_edge_per_share"] >= 0.025

    eq1 = detect_eq1_pyth_equity_dominance_box(
        [
            {"strike": 200.0, "yes_token_id": "nv200y", "no_token_id": "nv200n", "yes_ask": 0.51, "yes_ask_size": 10, "no_ask": 0.52, "no_ask_size": 10},
            {"strike": 205.0, "yes_token_id": "nv205y", "no_token_id": "nv205n", "yes_ask": 0.35, "yes_ask_size": 10, "no_ask": 0.46, "no_ask_size": 10},
        ],
        ticker="NVDA",
        et_hour_float=15.0,
        corporate_action_flag=False,
    )
    assert len(eq1) == 1
    assert eq1[0]["net_edge_per_share"] >= 0.025


def test_weather_metar_speci_guard_ratchet_and_solar_lock() -> None:
    # SPECI must be rejected!
    assert parse_routine_metar_temp_c("SPECI KLGA 041832Z 18012KT 10SM BKN040 26/14 A2992 RMK AO2 T02610139") is None
    p = parse_routine_metar_temp_c("METAR KLGA 041851Z 18010KT 10SM FEW050 24/12 A2994 RMK AO2 T02440122")
    assert p is not None
    assert p["temp_c"] == 24.4
    assert p["confirmed_floor_int_f"] == 76

    ext = compute_running_metar_extrema(
        [
            "SPECI KLGA 041832Z 18012KT 10SM BKN040 29/14 A2992 RMK AO2 T02900139",
            "METAR KLGA 041851Z 18010KT 10SM FEW050 24/12 A2994 RMK AO2 T02440122",
        ],
        unit="F",
    )
    assert ext is not None
    assert ext["confirmed_running_high_floor"] == 76

    brackets = [
        {"label": "73F or below", "low": None, "high": 73, "yes_token_id": "y0", "no_token_id": "n0", "yes_ask": 0.01, "yes_ask_size": 20, "no_ask": 0.985, "no_ask_size": 20},
        {"label": "74-75F", "low": 74, "high": 75, "yes_token_id": "y1", "no_token_id": "n1", "yes_ask": 0.02, "yes_ask_size": 20, "no_ask": 0.980, "no_ask_size": 20},
        {"label": "76-77F", "low": 76, "high": 77, "yes_token_id": "y2", "no_token_id": "n2", "yes_ask": 0.62, "yes_ask_size": 20, "no_ask": 0.40, "no_ask_size": 20},
        {"label": "78F or higher", "low": 78, "high": None, "yes_token_id": "y3", "no_token_id": "n3", "yes_ask": 0.35, "yes_ask_size": 20, "no_ask": 0.66, "no_ask_size": 20},
    ]
    sigs = detect_w_prune1_metar_slate_arb(
        brackets,
        ["METAR KLGA 042353Z 18010KT 10SM FEW050 24/12 A2994 RMK AO2 T02440122"],
        station_icao="KLGA",
        unit="F",
        local_hour_minute=(23, 54),
    )
    by_sl = {s["sleeve"] for s in sigs}
    assert "W_PRUNE1_DEAD_NO_BOND" in by_sl
    assert "W_PRUNE1_NR0_BASKET" in by_sl
    assert "W_SOLAR1_POST_2351_LOCK" in by_sl


def test_sports_dc1_lp_comp1_halftime_ot_and_mention1() -> None:
    assert has_us_overtime_inequality("Team A wins (including overtime)", "Regulation 90 minutes only") is True
    assert has_us_overtime_inequality("90 minutes regulation only", "Regulation time only (excludes extra time)") is False

    dc = detect_dc1_double_chance_1x2_parity(
        one_x2={
            "home": {"yes_token_id": "h_y", "yes_ask": 0.42, "yes_ask_size": 15},
            "draw": {"yes_token_id": "d_y", "yes_ask": 0.28, "yes_ask_size": 15},
            "away": {"yes_token_id": "a_y", "yes_ask": 0.31, "yes_ask_size": 15},
        },
        double_chance={
            "X2": {"yes_token_id": "x2_y", "yes_ask": 0.55, "yes_ask_size": 15},
        },
        rules_text_1x2="90 minutes regulation only",
        rules_text_dc="90 minutes regulation only",
    )
    assert len(dc) >= 1
    assert dc[0]["identity"] == "YES_HOME_PLUS_YES_X2"

    tri = detect_lp_comp1_sports_triangles(
        draw={"no_token_id": "d_no", "no_ask": 0.26, "no_ask_size": 12},
        btts={"yes_token_id": "btts_y", "yes_ask": 0.44, "yes_ask_size": 12},
        under_1_5={"yes_token_id": "u15_y", "yes_ask": 0.27, "yes_ask_size": 12},
    )
    assert len(tri) == 1
    assert tri[0]["guaranteed_payout_per_share"] == 1.0
    assert tri[0]["net_edge_per_share"] >= 0.025

    ht = detect_halftime_freeze_offset_box(
        is_halftime=True,
        halftime_total_goals=1,
        fulltime_line=2.5,
        second_half_line=1.5,
        ft_market={"yes_token_id": "ft_y", "no_token_id": "ft_n", "yes_ask": 0.48, "yes_ask_size": 10, "no_ask": 0.54, "no_ask_size": 10},
        h2_market={"yes_token_id": "h2_y", "no_token_id": "h2_n", "yes_ask": 0.53, "yes_ask_size": 10, "no_ask": 0.49, "no_ask_size": 10},
    )
    assert ht is not None
    assert ht["net_edge_per_share"] >= 0.025

    m1 = detect_mention1_cumulative_ladder_box(
        [
            {"term": "tariff", "min_count": 2, "yes_token_id": "m2y", "no_token_id": "m2n", "yes_ask": 0.58, "yes_ask_size": 15},
            {"term": "tariff", "min_count": 5, "yes_token_id": "m5y", "no_token_id": "m5n", "no_ask": 0.39, "no_ask_size": 15},
        ]
    )
    assert len(m1) == 1
    assert m1[0]["net_edge_per_share"] >= 0.025


def test_c1_ctf_overround_rollback_uma_ready1_and_reward_shield() -> None:
    hits = scan_full_universe_c1_and_ctf_overround(
        [
            {
                "condition_id": "cond_under",
                "yes_token_id": "yu",
                "no_token_id": "nu",
                "yes_ask": 0.47,
                "yes_ask_size": 20,
                "no_ask": 0.51,
                "no_ask_size": 20,
                "enableOrderBook": True,
            },
            {
                "condition_id": "cond_over",
                "yes_token_id": "yo",
                "no_token_id": "no",
                "yes_bid": 0.53,
                "yes_bid_size": 20,
                "no_bid": 0.49,
                "no_bid_size": 20,
                "enableOrderBook": True,
            },
        ]
    )
    assert {h["sleeve"] for h in hits} == {"C1_BINARY_COMPLETE_SET", "CTF_OVERROUND_MINT_SELL"}

    class _DummyExec:
        def __init__(self, fail_second_leg: bool = False) -> None:
            self.fail_second_leg = fail_second_leg
            self.splits: List[float] = []
            self.merges: List[float] = []
            self.orders: List[Any] = []

        def split_collateral_to_complete_set(self, condition_id: str, amount_usd: float, neg_risk: bool = False) -> Dict[str, Any]:
            self.splits.append(amount_usd)
            return {"success": True}

        def merge_complete_set_to_collateral(self, condition_id: str, shares: float, neg_risk: bool = False) -> Dict[str, Any]:
            self.merges.append(shares)
            return {"success": True}

        def place_fok_order(self, token_id: str, side: str, shares: float, price: float, **kwargs: Any) -> Dict[str, Any]:
            self.orders.append((token_id, side, shares, price))
            if self.fail_second_leg and len(self.orders) >= 2:
                return {"success": False, "reason": "FOK_KILLED"}
            return {"success": True, "taking_amount": shares * price, "making_amount": shares * price, "fee_usd": 0.0}

        def get_best_bid_ask(self, token_id: str) -> Dict[str, float]:
            return {"best_bid": 0.30, "best_ask": 0.32}

    # Happy path mint-sell
    ex_ok = _DummyExec(fail_second_leg=False)
    res_ok = asyncio.run(
        execute_binary_ctf_overround_mint_sell(
            ex_ok, condition_id="c1", yes_token_id="yo", no_token_id="no", yes_min_bid=0.53, no_min_bid=0.49, shares=10.0
        )
    )
    assert res_ok["success"] is True
    assert res_ok["net_pnl_usd"] > 0.15

    # Reject rollback path: if NO leg FOK fails before YES leg matched -> merges full complete set back!
    class _RejectBothExec(_DummyExec):
        def place_fok_order(self, token_id: str, side: str, shares: float, price: float, **kwargs: Any) -> Dict[str, Any]:
            return {"success": False, "reason": "NO_MATCH"}

    ex_rb = _RejectBothExec()
    res_rb = asyncio.run(
        execute_binary_ctf_overround_mint_sell(
            ex_rb, condition_id="c2", yes_token_id="yo", no_token_id="no", yes_min_bid=0.53, no_min_bid=0.49, shares=8.0
        )
    )
    assert res_rb["success"] is False
    assert ex_rb.merges == [8.0]

    # Multi-leg All-YES bundle unwinds filled leg if subsequent leg FOK rejects
    ex_ml = _DummyExec(fail_second_leg=True)
    res_ml = asyncio.run(
        execute_multi_leg_all_yes_bundle(
            ex_ml,
            [
                {"token_id": "t1", "ask_px": 0.31, "ask_size": 10},
                {"token_id": "t2", "ask_px": 0.32, "ask_size": 10},
                {"token_id": "t3", "ask_px": 0.33, "ask_size": 10},
            ],
            shares=6.0,
        )
    )
    assert res_ml["success"] is False
    assert any(o[1] == "SELL" for o in ex_ml.orders)

    uma = score_uma_ready1_liveness_priority(ask_price=0.993, remaining_liveness_sec=600.0, disputed=False)
    assert uma is not None
    assert uma["priority_boost"] == 3.0

    shield = CompleteSetRewardShield(scaling_c=3.0)
    pair = shield.build_hedged_reward_pair(
        yes_token_id="ry",
        no_token_id="rn",
        mid_yes=0.50,
        max_incentive_spread=0.04,
        min_incentive_size=5.0,
        shares=10.0,
        max_pair_bid_sum=0.990,
    )
    assert pair is not None
    assert pair["reward_multiplier_vs_single_sided"] >= 2.99


def test_live_bottleneck_fixes_and_riskless_paa_box_grouping(tmp_path: Path) -> None:
    # 1. XAG Chainlink + Official 60s TWAP stream support
    assert CHAINLINK_SYMBOL_MAP["xag/usd"] == "XAG"
    stream = PolymarketChainlinkLiveStream()
    stream._ingest_official_twap("xag/usd", 32.456, time.time() * 1000.0)
    tw = stream.get_latest_official_twap_60s("XAG")
    assert tw is not None and abs(float(tw) - 32.456) < 1e-6

    # 2. PreSplitInventoryGun lowered to $14 min cash & includes XAG/XAU
    gun = PreSplitInventoryGun()
    assert gun.min_free_cash_usd == 14.0

    # 3. Capital velocity hurdle exempts COMPLETE_SET / CTF_OVERROUND / MULTI_LEG_BUNDLE
    assert (
        passes_capital_velocity_hurdle(
            box_type="COMPLETE_SET",
            collat_usd=61.01,
            rem_tte_sec=86400.0 * 14,
            box_cost_net=0.992,
            cfg=DEFAULT_HOLISTIC_CONFIG,
        )[0]
        is True
    )
    assert (
        passes_capital_velocity_hurdle(
            box_type="CTF_OVERROUND",
            collat_usd=61.01,
            rem_tte_sec=86400.0 * 14,
            box_cost_net=0.992,
            cfg=DEFAULT_HOLISTIC_CONFIG,
        )[0]
        is True
    )

    # 4. Riskless PAA: group_closed_positions_by_box prevents false P0 breach on $0.00 hedge leg!
    closed_legs = [
        {
            "trade_id": "t_leg_lose",
            "box_id": "BOX_BTC_1",
            "is_dominance_box": True,
            "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
            "notional_usd": 4.80,
            "payout_usd": 0.0,
            "net_pnl_usd": -4.80,
            "won": False,
            "entry_time_utc": "2026-11-04T03:00:00Z",
            "exit_ts": 1000.0,
        },
        {
            "trade_id": "t_leg_win",
            "box_id": "BOX_BTC_1",
            "is_dominance_box": True,
            "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
            "notional_usd": 4.95,
            "payout_usd": 10.0,
            "net_pnl_usd": 5.05,
            "won": True,
            "entry_time_utc": "2026-11-04T03:00:00Z",
            "exit_ts": 1001.0,
        },
        # Partial box whose partner leg is STILL OPEN in `active_positions` -> withheld until partner settles!
        {
            "trade_id": "t_partial_leg1",
            "box_id": "BOX_ETH_OPEN",
            "is_dominance_box": True,
            "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
            "notional_usd": 4.70,
            "payout_usd": 0.0,
            "net_pnl_usd": -4.70,
            "won": False,
            "entry_time_utc": "2026-11-04T03:05:00Z",
            "exit_ts": 1002.0,
        },
    ]
    active_legs = {
        "tok_partner": {
            "box_id": "BOX_ETH_OPEN",
            "is_dominance_box": True,
            "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
            "notional_usd": 5.00,
        }
    }
    grouped = group_closed_positions_by_box(closed_legs, active_legs)
    assert len(grouped) == 1
    assert grouped[0]["box_id"] == "BOX_BTC_1"
    assert abs(float(grouped[0]["net_pnl_usd"]) - 0.25) < 1e-6
    assert grouped[0]["won"] is True

    # Verify PAAMonitor raises ZERO P0 RISKLESS_ZERO_LOSS_BREACH alerts on that live state!
    repo = tmp_path / "repo"
    (repo / "data" / "polymarket" / "paa").mkdir(parents=True)
    (repo / "data" / "alpha124").mkdir(parents=True)
    (repo / "config").mkdir(parents=True)
    strat_cfg = json.loads((Path(__file__).resolve().parents[1] / "config" / "polymarket_strategy_and_risk.json").read_text(encoding="utf-8"))
    (repo / "config" / "polymarket_strategy_and_risk.json").write_text(json.dumps(strat_cfg), encoding="utf-8")
    (repo / "config" / "autonomy_config.json").write_text(
        json.dumps({"monitoring": {"max_shm_tick_age_sec": 999999, "max_alpha124_state_age_sec": 999999}}),
        encoding="utf-8",
    )
    (repo / "data" / "polymarket" / "live_harvester_state.json").write_text(
        json.dumps({"risk_halt": False, "active_positions": active_legs, "closed_positions": closed_legs}),
        encoding="utf-8",
    )
    (repo / "data" / "alpha124" / "alpha124_shadow_state.json").write_text(
        json.dumps({"open_positions_count": 0, "by_sleeve": {}}),
        encoding="utf-8",
    )
    db = PAATaskDB(repo / "data" / "polymarket" / "paa" / "paa.db")
    bud = BudgetManager(db=db, autonomy_cfg={"budget": {}})
    acc = PAAAccountant(db=db, budget=bud, data_dir=repo / "data" / "polymarket")
    mon = PAAMonitor(
        db=db,
        accountant=acc,
        budget=bud,
        data_dir=repo / "data" / "polymarket",
        autonomy_cfg={"monitoring": {"max_shm_tick_age_sec": 999999, "max_alpha124_state_age_sec": 999999}},
    )
    snap = mon.run_monitor_cycle(live_rpc_check=False, auto_recover_safe=False, check_network=False)
    breaches = [a for a in (snap.get("anomalies") or []) if "ZERO_LOSS_BREACH" in str(a)]
    assert breaches == []

    # Verify PAAOptimizer runs cleanly
    opt = PAAOptimizer(repo_root=repo)
    opt_res = opt.run_hourly_optimization()
    assert opt_res["riskless_only_mode_verified"] is True
    assert opt_res["box_grouped_closed_count"] == 1

    # Verify PermissionGate blocks weakening min_live_equity_for_unhedged_directional_usd
    pg = PermissionGate(approvals_dir=repo / "data" / "polymarket" / "paa" / "approvals")
    cand_bad = copy.deepcopy(strat_cfg)
    cand_bad["directional"]["min_live_equity_for_unhedged_directional_usd"] = 10.0
    ok_env, viols = pg.inspect_config_envelope(strat_cfg, cand_bad)
    assert ok_env is False
    assert any("min_live_equity_for_unhedged_directional_usd" in v for v in viols)


def test_gatling_high_vol_machine_gun_s2_live_panel_a_panel_b_xau_d1_and_bundles(tmp_path, monkeypatch):
    """
    End-to-end verification of:
      1. Panel A Micro-Level Physics (`evaluate_s2_rtds_exact_twap_integrator` in `live_lock_mode=True`):
         - Exact `(elapsed_sec / rem_sec) * elapsed_cushion_bps` matching `75 / 125 / 165 / 275 bps` curves!
         - Rejects `XAU`/`XAG` spot-settled assets (`twap_lookback_sec=0`) from `S2` 60s-TWAP!
         - Rejects outside `4.5s <= rem_sec <= 16.0s` or when `official_twap_60s` diverges > 20 bps!
      2. Panel B Macro-Level Bankroll Trajectory (`$60.92` starting NAV, `90 clips/d`, `$22/clip`, `+58 bps`, `0.65` depth factor):
         - Exact Day 1 `+$11.48 (+18.85%/d)`, 30d Linear `$405.44`, 30d Scaled-Compounded `~$1,953` (`32.1x` NAV)!
         - `compute_gatling_clip_budget_usd` yields `$22.00` (`D1`/`S2`/`CTF_OVERROUND`), `$20.00` (`NEGRISK_CONVERT`/`MULTI_LEG_BUNDLE`), `$18.50` (bridged 0-fee math) at `$60.92` NAV and scales as `(NAV / 60.92) ** 0.65`.
      3. `XAU`/`XAG` `1h/15m` Same-Oracle Dominance (`parse_metal_forex_candle_event` + `verify_same_oracle_pair`)
         while strictly blocking `BTC` `1h` (Binance) vs `15m` (Chainlink).
      4. Live `PolymarketLiveHarvester` execution of `S2_EXACT_TWAP_LOCK` (`s2_live_bridge`, `TTE=9.0s`, `$22.00` Gatling clip)
         AND `MULTI_LEG_BUNDLE` (`neg_risk=False` for pre-match Sports `LP_COMP1` + full `active_positions` schema).
    """
    from types import SimpleNamespace
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        compute_gatling_clip_budget_usd,
        compute_gatling_trajectory_projection,
        evaluate_s2_rtds_exact_twap_integrator,
        finish_protocol_v2_special_box_sync,
    )
    from src.polymarket_research.same_oracle_dominance_box import (
        parse_metal_forex_candle_event,
        parse_twap_candle_event,
        verify_same_oracle_pair,
    )

    # 1. Panel A Physics: +25 bps elapsed cushion at 15s (-75 bps), 10s (-125 bps), 5s (-275 bps); +15 bps at 5s (-165 bps)
    strike = 100_000.0
    for rem_s, cush_bps, expected_req_bps in (
        (15.0, 25.0, 75.0),
        (10.0, 25.0, 125.0),
        (5.0, 25.0, 275.0),
        (10.0, 15.0, 75.0),
        (5.0, 15.0, 165.0),
    ):
        exp_t = 2_000_000.0
        now_t = exp_t - rem_s
        spot_c = strike * (1.0 + cush_bps / 10000.0)
        pts = [(exp_t - 60.0 + float(k), spot_c) for k in range(int(60.0 - rem_s) + 1)]
        s2_ok = evaluate_s2_rtds_exact_twap_integrator(
            asset="BTC",
            open_price=strike,
            expiry_ts=exp_t,
            now_ts=now_t,
            rtds_ticks=pts,
            official_twap_60s=spot_c,
            up_ask=0.950,
            down_ask=0.060,
            live_lock_mode=True,
            min_net_edge=0.008,
            min_lock_prob=0.9990,
        )
        assert s2_ok is not None, f"Expected lock at rem={rem_s}s cush={cush_bps}bps"
        assert abs(float(s2_ok["req_adverse_avg_move_bps"]) - expected_req_bps) < 0.25
        assert float(s2_ok["p_model"]) >= 0.9990

    # Spot-settled XAU MUST be rejected by 60s-TWAP S2 integrator
    assert (
        evaluate_s2_rtds_exact_twap_integrator(
            asset="XAU",
            open_price=2700.0,
            expiry_ts=2_000_000.0,
            now_ts=1_999_990.0,
            rtds_ticks=[(1_999_940.0 + k, 2710.0) for k in range(51)],
            up_ask=0.94,
            down_ask=0.07,
            live_lock_mode=True,
        )
        is None
    )

    # 2. Panel B Trajectory & Gatling Concave Clip Sizing
    proj = compute_gatling_trajectory_projection(
        starting_nav_usd=60.92, clips_per_day=90.0, base_clip_usd=22.0, net_edge_bps=58.0, depth_exp=0.65, days=30
    )
    assert proj["day1_linear_profit_usd"] == 11.48
    assert proj["day1_yield_pct"] == 18.85
    assert proj["linear_30d_nav_usd"] == 405.44
    assert 1940.0 <= proj["scaled_comp_30d_nav_usd"] <= 1965.0
    assert 31.8 <= proj["nav_multiple_30d"] <= 32.3

    assert compute_gatling_clip_budget_usd(live_equity=60.92, free_cash=60.92, box_type="DOMINANCE", sleeve_src="D1_SAME_ORACLE_DOMINANCE_BOX", reserve_usd=0.0) == 22.0
    assert compute_gatling_clip_budget_usd(live_equity=60.92, free_cash=60.92, box_type="SINGLE_LEG_LOCK", sleeve_src="S2_EXACT_TWAP_LOCK", own_grad=False, reserve_usd=0.0) == 22.0
    assert compute_gatling_clip_budget_usd(live_equity=60.92, free_cash=60.92, box_type="BARRIER_MONO", sleeve_src="EQ1_PYTH_EQUITY_DOMINANCE_BOX", own_grad=False, reserve_usd=0.0) == 18.5
    # At 4x NAV ($243.68), 0.65 exponent scales $22 -> $22 * 4**0.65 = $54.17 (bounded well below 4x linear $88!)
    scaled_4x = compute_gatling_clip_budget_usd(live_equity=243.68, free_cash=243.68, box_type="DOMINANCE", reserve_usd=0.0)
    assert 53.5 <= scaled_4x <= 55.0

    # 3. XAU 1h vs 15m Same-Oracle Dominance passes while BTC 1h (Binance) vs 15m (Chainlink) is blocked
    xau_1h = parse_metal_forex_candle_event(
        {
            "id": "ev_xau_1h",
            "slug": "xau-updown-1h-1793772000",
            "markets": [
                {
                    "id": "910001",
                    "conditionId": "0x" + "a" * 64,
                    "eventStartTime": "2026-11-04T05:00:00Z",
                    "endDate": "2026-11-04T06:00:00Z",
                    "resolutionSource": "https://data.chain.link/streams/xau-usd-forexprice-streams",
                    "outcomes": '["Up","Down"]',
                    "clobTokenIds": '["11111111111111111111111111","22222222222222222222222222"]',
                }
            ],
        },
        "XAU",
        "1h",
    )
    xau_15m = parse_metal_forex_candle_event(
        {
            "id": "ev_xau_15m",
            "slug": "xau-updown-15m-1793774700",
            "markets": [
                {
                    "id": "910002",
                    "conditionId": "0x" + "b" * 64,
                    "eventStartTime": "2026-11-04T05:45:00Z",
                    "endDate": "2026-11-04T06:00:00Z",
                    "resolutionSource": "https://data.chain.link/streams/xau-usd-forexprice-streams",
                    "outcomes": '["Up","Down"]',
                    "clobTokenIds": '["33333333333333333333333333","44444444444444444444444444"]',
                }
            ],
        },
        "XAU",
        "15m",
    )
    assert xau_1h is not None and xau_15m is not None
    assert xau_1h.twap_lookback_sec == 0 and xau_15m.twap_lookback_sec == 0
    assert verify_same_oracle_pair(xau_1h, xau_15m) is True

    # 4. Live Harvester S2_EXACT_TWAP_LOCK (`TTE=9.0s`, `$22.00` Gatling clip) & MULTI_LEG_BUNDLE (`neg_risk=False`)
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_state.json")
    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {
                        "closed": 32,
                        "wins": 32,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 173.60,
                        "legging_adjusted_pnl_t1000_usd": 170.10,
                    },
                    "S2_EXACT_TWAP_LOCK": {"closed": 0, "wins": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                },
                "by_d1_asset": {},
            }
        ),
        encoding="utf-8",
    )
    h = PolymarketLiveHarvester(dry_run=True, allowed_assets={"BTC", "ETH", "SOL"})
    h.dry_run = False
    h.holistic_v5_live_mode = True
    h.enforce_gatling_sizing = True
    h._startup_reconciled = True
    h._last_known_collateral = 61.01
    h.executor.auth_mode = "LIVE"
    h.executor.get_collateral_balance = lambda *a, **kw: 61.01
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.get_token_tick_size = lambda _tok, price_hint=None: 0.001 if (price_hint or 0.0) >= 0.96 else 0.01
    h.executor.prewarm_token_market_cache = lambda **kw: None
    h.executor.invalidate_collateral_cache = lambda: None

    wtok, ltok = "7" * 28, "8" * 28
    h.executor.get_market_book = lambda tid: (
        {"asks": [{"price": "0.965", "size": "80"}], "bids": [{"price": "0.960", "size": "80"}]}
        if tid == wtok
        else {"asks": [{"price": "0.040", "size": "80"}], "bids": [{"price": "0.015", "size": "80"}]}
    )
    snipe_calls = []

    def _mock_snipe(**kw):
        snipe_calls.append(kw)
        sh = round(float(kw["notional_usd"]) / float(kw["target_price"]), 4)
        return SimpleNamespace(
            success=True,
            execution_status="FILLED",
            size=sh,
            price=float(kw["target_price"]),
            notional_usd=float(kw["notional_usd"]),
            fee_usd=0.0,
            order_id="0xS2LOCK",
            error="",
            details={},
        )

    h.executor.execute_snipe_order = _mock_snipe
    now_s2 = time.time()
    res_s2 = h.maybe_execute_graduated_d1_box(
        {
            "box_id": "LOCK1_LIVE_BTC_S2",
            "dedupe_key": "S2_BTC_TEST_1",
            "box_type": "SINGLE_LEG_LOCK",
            "sleeve_source": "S2_EXACT_TWAP_LOCK",
            "asset": "BTC",
            "ts_unix": now_s2,
            "expiry_ts": now_s2 + 9.0,
            "p_model": 0.9994,
            "box_cost_net": 0.967,
            "max_box_cost_net": 0.985,
            "max_opp_bid": 0.035,
            "hold_to_maturity": True,
            "leg_a_token_id": wtok,
            "leg_a_opp_token_id": ltok,
            "leg_a_market_id": "990011",
            "leg_a_condition_id": "0x" + "c" * 64,
            "leg_a_side": "UP",
            "leg_a_fee_rate": 0.07,
            "leg_a_fee_exponent": 1.0,
            "leg_a_neg_risk": False,
        }
    )
    assert res_s2["executed"] is True, res_s2
    assert len(snipe_calls) == 1
    # Gatling caps live S2 clip to <= $22.00 on $61.01 NAV (leaving ~$39 free for 2 more clips!)
    assert 18.0 <= float(snipe_calls[0]["notional_usd"]) <= 22.05

    # Now test 3-leg pre-match Sports MULTI_LEG_BUNDLE (`neg_risk=False`) registration & PAA schema
    t1, t2, t3 = "3" * 28, "4" * 28, "5" * 28
    bundle_books = {
        t1: {"asks": [{"price": "0.31", "size": "60"}], "bids": [{"price": "0.30", "size": "60"}]},
        t2: {"asks": [{"price": "0.33", "size": "60"}], "bids": [{"price": "0.32", "size": "60"}]},
        t3: {"asks": [{"price": "0.34", "size": "60"}], "bids": [{"price": "0.33", "size": "60"}]},
    }
    h.executor.get_market_book = lambda tid: bundle_books[tid]
    snipe_calls.clear()
    res_ml = finish_protocol_v2_special_box_sync(
        h,
        {
            "box_id": "MLBOX_LP_COMP1_1",
            "box_type": "MULTI_LEG_BUNDLE",
            "sleeve_source": "LP_COMP1_SPORTS_TRIANGLES",
            "asset": "SOCCER",
            "neg_risk": False,
            "expiry_ts": now_s2 + 7200.0,
            "max_box_cost_net": 0.990,
            "legs": [
                {"token_id": t1, "market_id": "7701", "condition_id": "0x" + "1" * 64, "side": "NO", "neg_risk": False},
                {"token_id": t2, "market_id": "7702", "condition_id": "0x" + "2" * 64, "side": "YES", "neg_risk": False},
                {"token_id": t3, "market_id": "7703", "condition_id": "0x" + "3" * 64, "side": "YES", "neg_risk": False},
            ],
        },
        dedupe_k="LP_COMP1_TEST_1",
        retry_cd={},
        now_ts=now_s2,
        rcfg={},
        own_grad=False,
    )
    assert res_ml["executed"] is True, res_ml
    assert len(snipe_calls) == 3
    assert all(c["neg_risk"] is False for c in snipe_calls)
    for tid_ml in res_ml["leg_trade_ids"]:
        pos_ml = h.active_positions[tid_ml]
        assert pos_ml["is_dominance_box"] is True
        assert pos_ml["hold_to_maturity_lock"] is True
        assert pos_ml["box_id"] == "MLBOX_LP_COMP1_1"
        assert pos_ml["candle_expiry_ts"] > now_s2
        assert pos_ml["entry_shares"] == pos_ml["remaining_shares"] > 0


def test_gatling_fast_gun_reserve_cap_and_3leg_consolidation() -> None:
    from types import SimpleNamespace
    from src.paa_os.optimizer import group_closed_positions_by_box
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        cap_bond1_maker_for_gatling_reserve,
        consolidate_any_box_leg_close,
    )

    rb_cfg = {
        "gatling_enabled": True,
        "gatling_fast_gun_reserve_usd": 22.50,
    }
    mock_h = SimpleNamespace(dry_run=False, enforce_gatling_fast_gun_reserve=True)
    # On $61.01 NAV with $0 resting BOND1, per-market seed cap is round((61.01 - 22.50) * 0.55, 2) = $21.18
    b1_cap1 = cap_bond1_maker_for_gatling_reserve(mock_h, 54.91, 61.01, 0.0, rb_cfg)
    assert b1_cap1 == pytest.approx(21.18, abs=0.02)

    # Once $38.51 is already in BOND1 (`collat_f=22.50`, `sll_used_u=38.51`), remaining BOND1 budget is $0.00 so $22.50 stays 100% free!
    b1_cap2 = cap_bond1_maker_for_gatling_reserve(mock_h, 54.91, 22.50, 38.51, rb_cfg)
    assert b1_cap2 == pytest.approx(0.0, abs=0.01)

    # 3-leg MULTI_LEG_BUNDLE consolidation: 2 losing legs ($0 payout) + 1 winning leg ($20 payout) -> 1 net WIN (+$0.80), 0 losses!
    harv = SimpleNamespace(
        active_positions={
            "L1": {"trade_id": "L1", "box_id": "MLBOX_3", "is_dominance_box": True, "box_expected_legs": 3, "notional_usd": 6.20, "sleeve": "LP_COMP1_SPORTS_TRIANGLES"},
            "L2": {"trade_id": "L2", "box_id": "MLBOX_3", "is_dominance_box": True, "box_expected_legs": 3, "notional_usd": 6.40, "sleeve": "LP_COMP1_SPORTS_TRIANGLES"},
            "L3": {"trade_id": "L3", "box_id": "MLBOX_3", "is_dominance_box": True, "box_expected_legs": 3, "notional_usd": 6.60, "sleeve": "LP_COMP1_SPORTS_TRIANGLES"},
        },
        closed_positions=[],
        _pending_collateral_refresh=False,
        save_state=lambda: None,
    )
    handled1, _ = consolidate_any_box_leg_close(harv, "L1", harv.active_positions["L1"], 0.0, 0.0, -6.20, "OTM_LEG_1", True)
    assert handled1 is True
    assert "L1" not in harv.active_positions

    handled2, _ = consolidate_any_box_leg_close(harv, "L2", harv.active_positions["L2"], 0.0, 0.0, -6.40, "OTM_LEG_2", True)
    assert handled2 is True
    assert "L2" not in harv.active_positions

    # Also verify PAA optimizer holds back partial 2-of-3 legs if L3 is still open
    leg_c1 = {"trade_id": "L1", "box_id": "MLBOX_3", "is_dominance_box": True, "box_expected_legs": 3, "notional_usd": 6.20, "net_pnl_usd": -6.20}
    leg_c2 = {"trade_id": "L2", "box_id": "MLBOX_3", "is_dominance_box": True, "box_expected_legs": 3, "notional_usd": 6.40, "net_pnl_usd": -6.40}
    assert group_closed_positions_by_box([leg_c1, leg_c2], {"L3": {"box_id": "MLBOX_3", "box_expected_legs": 3}}) == []

    pos_l3 = harv.active_positions.pop("L3")
    handled3, tot_pnl = consolidate_any_box_leg_close(harv, "L3", pos_l3, 20.00, 0.0, 13.40, "WIN_LEG_3", True)
    assert handled3 is False
    assert tot_pnl == pytest.approx(0.80, abs=1e-4)
    assert pos_l3["won"] is True
    assert pos_l3["net_pnl_usd"] == pytest.approx(0.80, abs=1e-4)
    assert len(pos_l3["box_legs_summary"]) == 3


def test_s2_rtds_rolling_twap_and_ctf_overround_partial_unwind_registration() -> None:
    from types import SimpleNamespace
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        evaluate_s2_rtds_exact_twap_integrator,
        execute_binary_ctf_overround_mint_sell,
        finish_protocol_v2_special_box_sync,
    )

    # Smooth 20 bps/10s rally across 113s (`1.8 bps/s` realistic 1Hz step, no jump spike):
    # At `rem_sec = 15.0s` (`45s` elapsed in settlement window vs `60s` rolling official TWAP),
    # `rolling_60` differs from `mean_obs` by > 20 bps yet matches `official_twap_60s` with 0 drift!
    b_ts = 1_762_000_200.0
    now_t = b_ts - 15.0
    ticks_120 = [(b_ts - 120.0 + i, 98_200.0 + i * 28.0) for i in range(106)]
    rolling_60_vals = [p for t, p in ticks_120 if (now_t - 60.5) <= t <= (now_t + 1.0)]
    official_60 = sum(rolling_60_vals) / len(rolling_60_vals)
    s2 = evaluate_s2_rtds_exact_twap_integrator(
        asset="BTC",
        open_price=100_000.0,
        expiry_ts=b_ts,
        now_ts=now_t,
        rtds_ticks=ticks_120,
        official_twap_60s=official_60,
        live_lock_mode=True,
        up_ask=0.955,
        down_ask=0.04,
        fee_rate=0.07,
        fee_exponent=1.0,
    )
    assert s2 is not None
    assert s2["direction"] == "UP"
    assert s2["net_edge_per_share"] >= 0.010

    # Partial unwind registration test: YES fills 10sh, NO FOK rejects, unwind fails -> 10sh NO residual registered!
    class _PartialUnwindExec:
        def split_collateral_to_complete_set(self, condition_id: str, amount_usd: float, neg_risk: bool = False) -> Dict[str, Any]:
            return {"success": True}

        def merge_complete_set_to_collateral(self, condition_id: str, shares: float, neg_risk: bool = False) -> Dict[str, Any]:
            return {"success": False}

        def execute_atomic_box_overround_unwind(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {
                "success": False,
                "partial_leg_unwind": True,
                "leg_a": {"filled": True, "success": True, "taking_amount": 5.40, "fee_usd": 0.0},
                "leg_b": {"filled": False, "success": False},
            }

        def execute_unwind_order(self, token_id: str, size: float, side: str = "SELL", **kwargs: Any) -> Dict[str, Any]:
            return {"success": False}

        def get_market_book(self, token_id: str) -> Dict[str, Any]:
            return {"bids": [{"price": "0.54", "size": "40"}], "asks": [{"price": "0.56", "size": "40"}]}

        def invalidate_collateral_cache(self) -> None:
            pass

    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    h_async = SimpleNamespace(active_positions={})
    res_pu = asyncio.run(
        execute_binary_ctf_overround_mint_sell(
            _PartialUnwindExec(),
            condition_id="0x" + "d" * 64,
            yes_token_id="9" * 28,
            no_token_id="8" * 28,
            yes_min_bid=0.53,
            no_min_bid=0.49,
            shares=10.0,
            harvester=h_async,
            expiry_ts=now_t + 3600.0,
        )
    )
    assert res_pu["success"] is False
    assert res_pu["reason"] == "OVERROUND_PARTIAL_LEG_UNWOUND"
    assert len(h_async.active_positions) == 1

    h_pu = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    h_pu.dry_run = False
    h_pu.active_positions = {}
    h_pu.closed_positions = []
    h_pu.pending_entry_intents = {}
    h_pu._executed_d1_box_keys = set()
    h_pu._last_known_collateral = 60.0
    h_pu._pending_collateral_refresh = False
    h_pu.max_exposure = 100.0
    h_pu.executor = _PartialUnwindExec()
    h_pu.save_state = lambda: None
    h_pu.risk_controller = SimpleNamespace(record_trade_pnl=lambda *a, **k: None)

    out_pu = finish_protocol_v2_special_box_sync(
        h_pu,
        {
            "box_id": "CTF_PU_TEST",
            "box_type": "CTF_OVERROUND",
            "sleeve_source": "CTF_OVERROUND_MINT_SELL",
            "asset": "POLY",
            "condition_id": "0x" + "d" * 64,
            "yes_token_id": "9" * 28,
            "no_token_id": "8" * 28,
            "yes_bid": 0.54,
            "no_bid": 0.54,
            "max_fillable_shares": 10.0,
            "expiry_ts": now_t + 3600.0,
        },
        dedupe_k="CTF_PU_1",
        retry_cd={},
        now_ts=now_t,
        rcfg={},
        own_grad=False,
    )
    assert out_pu["executed"] is False
    assert len(h_pu.active_positions) == 1
    res_pos = next(iter(h_pu.active_positions.values()))
    assert res_pos["token_id"] == "8" * 28
    assert res_pos["remaining_shares"] >= 5.0


def test_alpha124_ws_book_helper_and_protocol_v2_daemon_scan_qa_guards() -> None:
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon, BANKROLL_TICKETS
    from src.polymarket_research.riskless_protocol_v2_expansion import run_protocol_v2_daemon_scan

    for req_sl in (
        "NR4_OPTIMAL_CHANNEL_CONVERT",
        "NR5_LOTTERY_FREEROLL_CONVERT",
        "CTF_OVERROUND_MINT_SELL",
        "C1_BINARY_COMPLETE_SET",
    ):
        assert req_sl in BANKROLL_TICKETS["T1000"]

    # Choose timestamp inside 15:00 ET (19:00 UTC in EDT / 20:00 UTC in EST) so EQ1 window is active;
    # we also test B1 at 11:00 ET separately.
    now_eq = datetime(2026, 11, 4, 20, 0, 0, tzinfo=timezone.utc).timestamp()  # 15:00 EST
    now_b1 = datetime(2026, 11, 4, 16, 0, 0, tzinfo=timezone.utc).timestamp()  # 11:00 EST

    dm = Alpha124ShadowDaemon.__new__(Alpha124ShadowDaemon)
    dm._ws_rest_seeded = {"tok_rest_seeded"}
    dm._ws_books = {
        "tok_fresh": (now_eq - 0.8, {"bids": [{"price": 0.54, "size": 30}], "asks": [{"price": 0.56, "size": 30}]}),
        "tok_stale": (now_eq - 9.0, {"bids": [{"price": 0.54, "size": 30}], "asks": [{"price": 0.56, "size": 30}]}),
        "tok_rest_seeded": (now_eq - 0.2, {"bids": [{"price": 0.54, "size": 30}], "asks": [{"price": 0.56, "size": 30}]}),
    }
    bk_f = dm._get_fresh_ws_book("tok_fresh", now_eq, max_age_sec=5.0)
    assert bk_f is not None and bk_f["bids"][0]["price"] == 0.54
    assert dm._get_fresh_ws_book("tok_stale", now_eq, max_age_sec=5.0) is None
    assert dm._get_fresh_ws_book("tok_rest_seeded", now_eq, max_age_sec=5.0) is None
    assert dm._get_fresh_ws_book("tok_missing", now_eq, max_age_sec=5.0) is None

    # Verify QA guards inside `run_protocol_v2_daemon_scan`:
    #   1) EQ1 ignores `is_downward=True` strikes (`NVDA < $200`)
    #   2) DC1 blocks live in-play (`kickoff_ts = end_ts - 9000 < now + 300`) while allowing pre-match (`now + 3600`)
    eq_down_1 = SimpleNamespace(asset="NVDA", end_ts=now_eq + 3600.0, strike=200.0, is_downward=True, yes_token="d1y", no_token="d1n", market_id="1", condition_id="c1", fee_rate=0.0, fee_exponent=1.0)
    eq_down_2 = SimpleNamespace(asset="NVDA", end_ts=now_eq + 3600.0, strike=210.0, is_downward=True, yes_token="d2y", no_token="d2n", market_id="2", condition_id="c2", fee_rate=0.0, fee_exponent=1.0)
    live_inplay_tree = SimpleNamespace(
        game_id="ev_live",
        title="Arsenal vs Chelsea",
        end_ts=now_eq + 3600.0,  # kickoff_ts = end_ts - 9000 = now_eq - 5400 (in-play -> MUST BLOCK!)
        home_leg={"yes_token": "lh", "no_token": "lhn", "market_id": "11", "condition_id": "lc1", "fee_rate": 0.0},
        draw_leg={"yes_token": "ld", "no_token": "ldn", "market_id": "12", "condition_id": "lc2", "fee_rate": 0.0},
        away_leg={"yes_token": "la", "no_token": "lan", "market_id": "13", "condition_id": "lc3", "fee_rate": 0.0},
        btts_leg=None,
        totals=[],
    )
    prematch_tree = SimpleNamespace(
        game_id="ev_pre",
        title="Real Madrid vs Barcelona",
        end_ts=now_eq + 12600.0,  # kickoff_ts = now_eq + 3600 (+60m pre-match -> ALLOWED!)
        home_leg={"yes_token": "ph", "no_token": "phn", "market_id": "21", "condition_id": "pc1", "fee_rate": 0.0},
        draw_leg={"yes_token": "pd", "no_token": "pdn", "market_id": "22", "condition_id": "pc2", "fee_rate": 0.0},
        away_leg={"yes_token": "pa", "no_token": "pan", "market_id": "23", "condition_id": "pc3", "fee_rate": 0.0},
        btts_leg=None,
        totals=[],
    )
    ws_map = {
        "d1y": {"asks": [{"price": 0.45, "size": 30}], "bids": [{"price": 0.44, "size": 30}]},
        "d1n": {"asks": [{"price": 0.45, "size": 30}], "bids": [{"price": 0.44, "size": 30}]},
        "d2y": {"asks": [{"price": 0.45, "size": 30}], "bids": [{"price": 0.44, "size": 30}]},
        "d2n": {"asks": [{"price": 0.45, "size": 30}], "bids": [{"price": 0.44, "size": 30}]},
        "lh": {"asks": [{"price": 0.40, "size": 30}], "bids": [{"price": 0.39, "size": 30}]},
        "lhn": {"asks": [{"price": 0.54, "size": 30}], "bids": [{"price": 0.53, "size": 30}]},
        "ld": {"asks": [{"price": 0.28, "size": 30}], "bids": [{"price": 0.27, "size": 30}]},
        "ldn": {"asks": [{"price": 0.70, "size": 30}], "bids": [{"price": 0.69, "size": 30}]},
        "la": {"asks": [{"price": 0.30, "size": 30}], "bids": [{"price": 0.29, "size": 30}]},
        "lan": {"asks": [{"price": 0.68, "size": 30}], "bids": [{"price": 0.67, "size": 30}]},
        "ph": {"asks": [{"price": 0.40, "size": 30}], "bids": [{"price": 0.39, "size": 30}]},
        "phn": {"asks": [{"price": 0.54, "size": 30}], "bids": [{"price": 0.53, "size": 30}]},
        "pd": {"asks": [{"price": 0.28, "size": 30}], "bids": [{"price": 0.27, "size": 30}]},
        "pdn": {"asks": [{"price": 0.70, "size": 30}], "bids": [{"price": 0.69, "size": 30}]},
        "pa": {"asks": [{"price": 0.30, "size": 30}], "bids": [{"price": 0.29, "size": 30}]},
        "pan": {"asks": [{"price": 0.68, "size": 30}], "bids": [{"price": 0.67, "size": 30}]},
    }

    async def _mock_fetch_batch(toks: List[str], timeout: float = 2.5) -> Dict[str, Any]:
        return {t: ws_map[t] for t in toks if t in ws_map}

    def _best_ask_sz(bk: Dict[str, Any]) -> Tuple[float, float]:
        asks = sorted([(float(a["price"]), float(a["size"])) for a in (bk.get("asks") or [])], key=lambda x: x[0])
        return asks[0] if asks else (1.0, 0.0)

    emitted_2l: List[Dict[str, Any]] = []
    scan_dm = SimpleNamespace(
        single_scan=True,
        pyth_close_ladders={"NVDA": [eq_down_1, eq_down_2]},
        barrier_rungs={},
        strike_ladders={},
        negrisk_convert_slates={},
        soccer_trees={"ev_live": live_inplay_tree, "ev_pre": prematch_tree},
        pyth_daily_markets={},
        daily_updown_markets={},
        _ws_books={},
        fetch_books_batch=_mock_fetch_batch,
        _best_ask_sz=_best_ask_sz,
        _get_fresh_ws_book=lambda tid, nt, max_age_sec=5.0: ws_map.get(tid),
        emit_live_two_leg_box_candidate=lambda **kw: emitted_2l.append(kw) or True,
    )
    opps: List[Dict[str, Any]] = []
    asyncio.run(run_protocol_v2_daemon_scan(scan_dm, opps, now_ts=now_eq))
    sleeves_found = [o["sleeve"] for o in opps]
    assert "EQ1_PYTH_EQUITY_DOMINANCE_BOX" not in sleeves_found
    assert set(sleeves_found) == {"DC1_DOUBLE_CHANCE_1X2_PARITY"}
    assert all("Real Madrid" in o["market"] for o in opps)

    # Also verify B1 downward barrier (`direction="DOWN"`) is rejected at 11:00 ET
    b1_down = SimpleNamespace(asset="BTC", strike=90_000.0, direction="DOWN", end_ts=now_b1 + 7200.0, yes_token="bdy", no_token="bdn", market_id="3", condition_id="c3", fee_rate=0.0)
    b1_snap = SimpleNamespace(asset="BTC", strike=90_000.0, is_downward=False, end_ts=now_b1 + 3600.0, yes_token="bsy", no_token="bsn", market_id="4", condition_id="c4", fee_rate=0.0)
    ws_map.update({
        "bdy": {"asks": [{"price": 0.40, "size": 30}], "bids": [{"price": 0.39, "size": 30}]},
        "bdn": {"asks": [{"price": 0.58, "size": 30}], "bids": [{"price": 0.57, "size": 30}]},
        "bsy": {"asks": [{"price": 0.52, "size": 30}], "bids": [{"price": 0.51, "size": 30}]},
        "bsn": {"asks": [{"price": 0.45, "size": 30}], "bids": [{"price": 0.44, "size": 30}]},
    })
    scan_dm.pyth_close_ladders = {}
    scan_dm.soccer_trees = {}
    scan_dm.barrier_rungs = {"b1d": b1_down}
    scan_dm.strike_ladders = {"btc": [b1_snap]}
    opps_b1: List[Dict[str, Any]] = []
    asyncio.run(run_protocol_v2_daemon_scan(scan_dm, opps_b1, now_ts=now_b1))
    assert opps_b1 == []


def test_paa_accountant_readonly_safeguard_preservation_and_presplit_flat_guard(tmp_path: Path) -> None:
    from scripts.paa_flat_harvester_redeploy_once import _safe_to_restart
    from src.paa_os.accountant import PAAAccountant
    from src.paa_os.budget import BudgetManager
    from src.paa_os.permissions import load_autonomy_config
    from src.paa_os.task_db import PAATaskDB

    assert _safe_to_restart({"active_positions": {}, "pre_split_inventory_state": {"active": True}}) is False
    assert _safe_to_restart({"active_positions": {}, "pre_split_inventory_state": {"active": False}}) is True

    cfg = load_autonomy_config()
    db = PAATaskDB(tmp_path / "paa_tasks.db")
    budget = BudgetManager(db, autonomy_cfg=cfg)
    acct = PAAAccountant(db, budget, autonomy_cfg=cfg, data_dir=tmp_path)

    # Active PreSplitInventoryGun with $5.20 realized mid-cycle cash must NOT trigger false CASH_LEDGER_MISMATCH
    st_ps = {
        "live_bankroll": 50.0,
        "active_positions": {},
        "pending_entry_intents": {},
        "pre_split_inventory_state": {"active": True, "cost_usd": 10.0, "realized_cash_usd": 5.20, "up_rem": 0.0, "dn_rem": 10.0},
    }
    ok_ps, disc_ps, anom_ps = acct.verify_accounting_integrity({"free_cash_pusd": 55.20, "open_positions": []}, state_override=st_ps)
    assert ok_ps is True, anom_ps
    assert disc_ps < 0.05

    # Read-only fallback (`POLYGON_RPC_READONLY_FALLBACK_TO_STATE`) must NOT clear an active accounting safeguard!
    acct.enforce_accounting_safeguard(4.0, ["CASH_LEDGER_MISMATCH:test"])
    assert acct.safeguard_file.exists()
    acct.measure_and_record(
        live_rpc_check=False,
        ledger_override={
            "free_cash_pusd": 50.0,
            "open_positions": [],
            "watchdog_alerts": ["POLYGON_RPC_READONLY_FALLBACK_TO_STATE"],
        },
        state_override={"live_bankroll": 50.0, "active_positions": {}, "pending_entry_intents": {}},
    )
    assert acct.safeguard_file.exists(), "Read-only RPC fallback must never clear ACCOUNTING_SAFEGUARD_ACTIVE.json!"

    # Genuine live RPC reconciliation with 0 discrepancy clears the safeguard cleanly
    acct.measure_and_record(
        live_rpc_check=True,
        ledger_override={
            "free_cash_pusd": 50.0,
            "open_positions": [],
            "watchdog_alerts": [],
        },
        state_override={"live_bankroll": 50.0, "active_positions": {}, "pending_entry_intents": {}},
    )
    assert not acct.safeguard_file.exists()


def test_gatling_4_barrel_unblocking_nr4_s2_bond1_lpcomp1_presplit(tmp_path: Path) -> None:
    from types import SimpleNamespace
    from src.polymarket_research.riskless_machine_gun_engine import PreSplitInventoryGun
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        emit_single_leg_lock_cand_impl,
        emit_single_leg_maker_lock_cand_impl,
        maybe_emit_s2_live_locks,
        run_protocol_v2_daemon_scan,
    )

    now_t = 1_760_000_288.0  # 12.0s remaining to 1_760_000_300.0 (5m boundary)
    exp_5m = 1_760_000_300.0

    # 1. NR4/NR5 live daemon scan with REST batch fallback + non-contiguous question_index + LP_COMP1 2-leg corridor
    nr_slate = SimpleNamespace(
        event_id="ev_nr4",
        title="Closed NegRisk 3-Outcome Slate",
        neg_risk_market_id="0x" + "1" * 64,
        is_closed_convert_safe=True,
        end_ts=now_t + 7200.0,
        brackets=[
            {"question_index": 0, "label": "Out0", "market_id": "m0", "condition_id": "c0", "yes_token": "y0", "no_token": "n0", "fee_rate": 0.0, "fee_exponent": 1.0},
            {"question_index": 2, "label": "Out2", "market_id": "m2", "condition_id": "c2", "yes_token": "y2", "no_token": "n2", "fee_rate": 0.0, "fee_exponent": 1.0},
            {"question_index": 5, "label": "Out5", "market_id": "m5", "condition_id": "c5", "yes_token": "y5", "no_token": "n5", "fee_rate": 0.0, "fee_exponent": 1.0},
        ],
    )
    soc_tree = SimpleNamespace(
        game_id="g_lp",
        title="Liverpool vs Man City",
        start_ts=now_t + 3600.0,
        end_ts=now_t + 10800.0,
        home_leg={"yes_token": "sh", "no_token": "shn", "market_id": "sm1", "condition_id": "sc1", "fee_rate": 0.0},
        draw_leg={"yes_token": "sd", "no_token": "sdn", "market_id": "sm2", "condition_id": "sc2", "fee_rate": 0.0},
        away_leg={"yes_token": "sa", "no_token": "san", "market_id": "sm3", "condition_id": "sc3", "fee_rate": 0.0},
        btts_leg={"yes_token": "by", "no_token": "bn", "market_id": "sm4", "condition_id": "sc4", "fee_rate": 0.0},
        totals=[{"line": 1.5, "over_token": "o15", "under_token": "u15", "market_id": "sm5", "condition_id": "sc5", "fee_rate": 0.0}],
    )
    rest_books = {
        "y0": {"asks": [{"price": 0.65, "size": 30}], "bids": [{"price": 0.63, "size": 30}]},
        "n0": {"asks": [{"price": 0.37, "size": 30}], "bids": [{"price": 0.35, "size": 30}]},
        "y2": {"asks": [{"price": 0.25, "size": 30}], "bids": [{"price": 0.24, "size": 30}]},
        "n2": {"asks": [{"price": 0.60, "size": 30}], "bids": [{"price": 0.58, "size": 30}]},
        "y5": {"asks": [{"price": 0.20, "size": 30}], "bids": [{"price": 0.19, "size": 30}]},
        "n5": {"asks": [{"price": 0.62, "size": 30}], "bids": [{"price": 0.60, "size": 30}]},
        "sh": {"asks": [{"price": 0.45, "size": 30}], "bids": [{"price": 0.44, "size": 30}]},
        "shn": {"asks": [{"price": 0.56, "size": 30}], "bids": [{"price": 0.55, "size": 30}]},
        "sd": {"asks": [{"price": 0.28, "size": 30}], "bids": [{"price": 0.27, "size": 30}]},
        "sdn": {"asks": [{"price": 0.73, "size": 30}], "bids": [{"price": 0.72, "size": 30}]},
        "sa": {"asks": [{"price": 0.30, "size": 30}], "bids": [{"price": 0.29, "size": 30}]},
        "san": {"asks": [{"price": 0.71, "size": 30}], "bids": [{"price": 0.70, "size": 30}]},
        "by": {"asks": [{"price": 0.52, "size": 30}], "bids": [{"price": 0.51, "size": 30}]},
        "bn": {"asks": [{"price": 0.42, "size": 30}], "bids": [{"price": 0.41, "size": 30}]},
        "o15": {"asks": [{"price": 0.55, "size": 30}], "bids": [{"price": 0.54, "size": 30}]},
        "u15": {"asks": [{"price": 0.45, "size": 30}], "bids": [{"price": 0.44, "size": 30}]},
    }

    async def _fetch_batch(toks, timeout=2.5):
        return {t: rest_books[t] for t in toks if t in rest_books}

    def _best_ask_sz(bk):
        asks = sorted([(float(a["price"]), float(a["size"])) for a in (bk.get("asks") or [])], key=lambda x: x[0])
        return asks[0] if asks else (1.0, 0.0)

    nr_emits, lp_2l_emits = [], []
    dm_v2 = SimpleNamespace(
        single_scan=True,
        pyth_close_ladders={},
        barrier_rungs={},
        strike_ladders={},
        negrisk_convert_slates={"ev_nr4": nr_slate},
        soccer_trees={"g_lp": soc_tree},
        weather_events={},
        pyth_daily_markets={},
        daily_updown_markets={},
        _ws_books={},
        fetch_books_batch=_fetch_batch,
        _best_ask_sz=_best_ask_sz,
        _get_fresh_ws_book=lambda tid, nt, max_age_sec=8.0: None,  # Force REST fallback!
        emit_live_negrisk_convert_candidate=lambda **kw: nr_emits.append(kw) or True,
        emit_live_two_leg_box_candidate=lambda **kw: lp_2l_emits.append(kw) or True,
        emit_live_special_v2_box_candidate=lambda **kw: True,
    )
    opps_v2 = []
    asyncio.run(run_protocol_v2_daemon_scan(dm_v2, opps_v2, now_ts=now_t))
    assert len(nr_emits) >= 1
    assert nr_emits[0]["arb_hit"]["no_legs"][0]["bracket"]["question_index"] in {2, 5}
    assert any(e["sleeve_source"] == "LP_COMP1_SPORTS_TRIANGLES" and e["leg_a"]["market_id"] != e["leg_b"]["market_id"] for e in lp_2l_emits)

    # 2. S2 Dual-Mode: Taker at $0.993 AND Final-22s Post-Only Maker Lock when ask == $0.999
    ticks_s2 = [(exp_5m - 60.0 + i, 100_250.0) for i in range(49)]
    s2_spec = SimpleNamespace(
        asset="BTC",
        horizon="5m",
        market_id="m_s2",
        condition_id="0x" + "2" * 64,
        up_token="s2_up",
        down_token="s2_dn",
        end_ts=exp_5m,
        twap_lookback_sec=60.0,
        fee_rate=0.07,
        fee_exponent=1.0,
        neg_risk=False,
    )
    tkr_s2, mkr_s2 = [], []
    dm_s2 = SimpleNamespace(
        _best_ask_sz=_best_ask_sz,
        emit_live_single_leg_lock_candidate=lambda **kw: tkr_s2.append(kw) or True,
        emit_live_single_leg_maker_lock_candidate=lambda **kw: mkr_s2.append(kw) or True,
    )
    bk_s2_tkr = {"asks": [{"price": 0.993, "size": 30}], "bids": [{"price": 0.991, "size": 30}]}
    bk_s2_opp = {"asks": [{"price": 0.010, "size": 30}], "bids": [{"price": 0.005, "size": 30}]}
    maybe_emit_s2_live_locks(
        dm_s2, spec=s2_spec, k_open=100_000.0, eval_now=now_t, rem_sec=12.0, samples=ticks_s2,
        off_twap_60=100_250.0, win_side="UP", tok="s2_up", opp_token="s2_dn" if False else None,
        opp_tok="s2_dn", bk=bk_s2_tkr, bk_opp=bk_s2_opp, bks_s2={"s2_up": bk_s2_tkr, "s2_dn": bk_s2_opp},
    ) if False else maybe_emit_s2_live_locks(
        dm_s2, spec=s2_spec, k_open=100_000.0, eval_now=now_t, rem_sec=12.0, samples=ticks_s2,
        off_twap_60=100_250.0, win_side="UP", tok="s2_up", opp_tok="s2_dn",
        bk=bk_s2_tkr, bk_opp=bk_s2_opp, bks_s2={"s2_up": bk_s2_tkr, "s2_dn": bk_s2_opp},
    )
    assert len(tkr_s2) == 1 and tkr_s2[0]["max_lock_eff_px"] >= 0.9935

    bk_s2_mkr = {"asks": [{"price": 0.999, "size": 30}], "bids": [{"price": 0.992, "size": 20}]}
    maybe_emit_s2_live_locks(
        dm_s2, spec=s2_spec, k_open=100_000.0, eval_now=now_t, rem_sec=12.0, samples=ticks_s2,
        off_twap_60=100_250.0, win_side="UP", tok="s2_up", opp_tok="s2_dn",
        bk=bk_s2_mkr, bk_opp=bk_s2_opp, bks_s2={"s2_up": bk_s2_mkr, "s2_dn": bk_s2_opp},
        logger_obj=SimpleNamespace(info=lambda *a, **k: None),
    )
    assert len(mkr_s2) == 1 and mkr_s2[0]["max_resting_bid"] == 0.994

    # 3. BOND1 $0.9980 Maker + $0.9975 Taker candidate emission
    cand_out = tmp_path / "cands.jsonl"
    st_out = tmp_path / "state.json"
    dm_emit = SimpleNamespace(
        single_scan=True,
        _last_d1_live_emit_ts={},
        _ws_books={},
        _best_ask_sz=_best_ask_sz,
        _get_fresh_ws_book=lambda *a, **k: None,
    )

    def _extr_b(bids):
        if not bids:
            return 0.0, 0.0
        b0 = max(bids, key=lambda x: float(x["price"]))
        return float(b0["price"]), float(b0["price"]) * float(b0["size"])

    def _walk_1l(asks, ref_n, t100_n, fee_rate=0.0, max_slip_cents=0.01, min_l1_usd=10.0, max_ask_px=0.9985, fee_exponent=1.0):
        px, sz = float(asks[0]["price"]), float(asks[0]["size"])
        if px > max_ask_px or px * sz < min_l1_usd:
            return {"filled": False}
        return {"filled": True, "eff_px": px, "shares": sz, "best_ask": px, "worst_px": px}

    ok_tkr_997 = emit_single_leg_lock_cand_impl(
        dm_emit, sleeve_source="BOND1_UMA_RESOLUTION_CARRY", asset="SPORTS", dedupe_key="B1_TKR_997",
        token_id="tw", opp_token_id="tl", market_id="m_b1", condition_id="c_b1", side_label="YES", display_label="Test BOND1",
        bk_win={"asks": [{"price": 0.997, "size": 25}], "bids": [{"price": 0.996, "size": 25}]},
        bk_opp={"bids": [{"price": 0.002, "size": 25}], "asks": [{"price": 0.004, "size": 25}]},
        fee_rate=0.0, fee_exponent=1.0, neg_risk=False, close_ts=now_t + 1800.0, now_ts=now_t,
        max_lock_eff_px=0.9975, max_opp_bid=0.008, hold_to_maturity=True, p_model=1.0,
        extract_best_bid_fn=_extr_b, walk_l2_fn=_walk_1l,
        cand_file=cand_out, default_cand_path=cand_out, state_file=st_out, default_state_path=st_out,
    )
    assert ok_tkr_997 is True

    ok_mkr_998 = emit_single_leg_maker_lock_cand_impl(
        dm_emit, sleeve_source="BOND1_UMA_RESOLUTION_CARRY", asset="SPORTS", dedupe_key="B1_MKR_998", pair_dedupe_key="B1_TKR_997",
        token_id="tw", opp_token_id="tl", market_id="m_b1", condition_id="c_b1", side_label="YES", display_label="Test BOND1 MKR",
        bk_win={"asks": [{"price": 0.999, "size": 25}], "bids": [{"price": 0.997, "size": 25}]},
        bk_opp={"bids": [{"price": 0.001, "size": 25}], "asks": [{"price": 0.003, "size": 25}]},
        neg_risk=False, close_ts=now_t + 1800.0, now_ts=now_t,
        min_resting_bid=0.940, max_resting_bid=0.9980, min_maker_edge=0.0020, max_opp_bid=0.008,
        hold_to_maturity=True, p_model=1.0, target_bid_px=None, maker_rebate_ps=0.0,
        extract_best_bid_fn=_extr_b, cand_file=cand_out, default_cand_path=cand_out, state_file=st_out, default_state_path=st_out,
    )
    assert ok_mkr_998 is True

    # 4. PreSplitInventoryGun arms on 0%-fee XAU nested SHM with overround 1.005 (>= 1.003) and passes up/down token IDs
    import src.polymarket_research.riskless_machine_gun_engine as rmg_mod
    split_calls = []
    orig_split = rmg_mod.attempt_onchain_split_position
    rmg_mod.attempt_onchain_split_position = lambda ex, cid, amt, neg_risk=False, **kw: split_calls.append((cid, amt, kw)) or {"success": True, "tx_hash": "0xabc"}
    try:
        ps_gun = PreSplitInventoryGun(cap_usd=10.0)
        up_xau = "3" * 24
        dn_xau = "4" * 24
        harv_ps = SimpleNamespace(
            dry_run=False,
            _startup_reconciled=True,
            global_halt_active=False,
            active_positions={},
            pending_entry_intents={},
            closed_positions=[],
            pre_split_inventory_state={},
            _last_known_collateral=60.0,
            _pending_collateral_refresh=False,
            executor=SimpleNamespace(
                execute_atomic_box_overround_unwind=lambda *a, **k: {
                    "success": True,
                    "leg_a": {"filled": True, "taking_amount": 5.03, "fee_usd": 0.0},
                    "leg_b": {"filled": True, "taking_amount": 5.02, "fee_usd": 0.0},
                },
                invalidate_collateral_cache=lambda: None,
            ),
            save_state=lambda: None,
            risk_controller=None,
        )
        shm_xau = {
            "timestamp_unix": now_t,
            "spot_price": 4040.0,
            "m15": {
                "market_id": "xau_m15",
                "condition_id": "0x" + "9" * 64,
                "fee_rate": 0.0,
                "fee_exponent": 1.0,
                "expiry_ts": now_t + 300.0,
                "finalized_open": 4038.0,
                "UP": {"token_id": up_xau, "best_bid": 0.503, "bid_depth_1c_shares": 25.0, "best_ask": 0.510, "ask_depth_1c_shares": 25.0},
                "DOWN": {"token_id": dn_xau, "best_bid": 0.502, "bid_depth_1c_shares": 25.0, "best_ask": 0.510, "ask_depth_1c_shares": 25.0},
            },
        }
        r_xau1 = asyncio.run(ps_gun.tick(harv_ps, now_t, fast_tick_reader=lambda a: shm_xau if a == "XAU" else None))
        assert r_xau1 == "ARMED"
        assert len(split_calls) == 1
        assert split_calls[0][2]["up_token_id"] == up_xau and split_calls[0][2]["down_token_id"] == dn_xau
        shm_xau["timestamp_unix"] = now_t + 0.5
        r_xau2 = asyncio.run(ps_gun.tick(harv_ps, now_t + 0.5, fast_tick_reader=lambda a: shm_xau if a == "XAU" else None))
        assert r_xau2 == "PRE_SPLIT_OVERROUND_SWEEP"
    finally:
        rmg_mod.attempt_onchain_split_position = orig_split


def test_gatling_burst_v56_shm_step_hold_s2_and_carry_recycle(tmp_path):
    from types import SimpleNamespace
    import asyncio
    import time
    from src.polymarket_research.polymarket_live_executor import load_risk_config
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        evaluate_s2_rtds_exact_twap_integrator,
        maybe_emit_s2_live_locks,
        compute_sll_and_carry_gatling_budget,
        maybe_early_profit_recycle_htm_lock,
        emit_negrisk_convert_cand_impl,
    )
    from src.polymarket_research.riskless_machine_gun_engine import PreSplitInventoryGun
    import src.polymarket_research.riskless_machine_gun_engine as rmg_mod

    # 1. load_risk_config() preserves enable_ungraduated_v3_math_live from config/polymarket_risk_config.json
    rcfg = load_risk_config()
    assert rcfg.get("enable_ungraduated_v3_math_live") is True

    # 2. Step-hold 1Hz S2 integrator on sparse 6-tick Chainlink window + auto-direction Taker ($0.65) & Maker ($0.996 -> 0.997 cap)
    end_ts = 1793805000.0
    now_f = end_ts - 9.5
    k_open = 78000.0
    sparse_pts = [
        (end_ts - 65.0, 78180.0),
        (end_ts - 52.0, 78182.0),
        (end_ts - 38.0, 78185.0),
        (end_ts - 25.0, 78184.0),
        (end_ts - 14.0, 78188.0),
        (now_f - 0.5, 78190.0),
    ]
    ev_s2 = evaluate_s2_rtds_exact_twap_integrator(
        asset="BTC", open_price=k_open, samples_last_60s=sparse_pts, now_ts=now_f, expiry_ts=end_ts,
        live_lock_mode=True, up_ask=0.65, fee_rate=0.072, fee_exponent=1.0, min_net_edge=0.0028,
    )
    assert ev_s2 is not None
    assert ev_s2["direction"] == "UP"
    assert ev_s2["p_model"] >= 0.999

    tkr_calls, mkr_calls = [], []
    dm_s2 = SimpleNamespace(
        _best_ask_sz=lambda b: ((float(b["asks"][0]["price"]), float(b["asks"][0]["size"])) if (b and b.get("asks")) else (1.0, 0.0)),
        emit_live_single_leg_lock_candidate=lambda **kw: tkr_calls.append(kw) or True,
        emit_live_single_leg_maker_lock_candidate=lambda **kw: mkr_calls.append(kw) or True,
    )
    spec_s2 = SimpleNamespace(
        asset="BTC", horizon="5m", twap_lookback_sec=60, market_id="m_s2", condition_id="c_s2",
        up_token="up_t", down_token="dn_t", fee_rate=0.072, fee_exponent=1.0, neg_risk=False, end_ts=end_ts,
    )
    maybe_emit_s2_live_locks(
        dm_s2, spec=spec_s2, k_open=k_open, eval_now=now_f, rem_sec=9.5, samples=sparse_pts, off_twap_60=None,
        bks_s2={
            "up_t": {"asks": [{"price": 0.65, "size": 30.0}], "bids": [{"price": 0.64, "size": 30.0}]},
            "dn_t": {"bids": [{"price": 0.002, "size": 30.0}], "asks": [{"price": 0.35, "size": 30.0}]},
        },
        logger_obj=SimpleNamespace(info=lambda *a, **k: None),
    )
    assert len(tkr_calls) == 1 and tkr_calls[0]["side_label"] == "UP"

    maybe_emit_s2_live_locks(
        dm_s2, spec=spec_s2, k_open=k_open, eval_now=now_f, rem_sec=9.5, samples=sparse_pts, off_twap_60=None,
        bks_s2={
            "up_t": {"asks": [{"price": 0.999, "size": 30.0}], "bids": [{"price": 0.996, "size": 30.0}]},
            "dn_t": {"bids": [{"price": 0.001, "size": 30.0}], "asks": [{"price": 0.004, "size": 30.0}]},
        },
        logger_obj=SimpleNamespace(info=lambda *a, **k: None),
    )
    assert len(mkr_calls) == 1 and mkr_calls[0]["min_resting_bid"] == 0.80 and mkr_calls[0]["max_resting_bid"] == 0.997
    maybe_emit_s2_live_locks(
        dm_s2, spec=spec_s2, k_open=k_open, eval_now=now_f, rem_sec=9.5, samples=sparse_pts, off_twap_60=None,
        bks_s2={
            "up_t": {"asks": [{"price": 0.999, "size": 30.0}], "bids": [{"price": 0.64, "size": 30.0}]},
            "dn_t": {"bids": [{"price": 0.001, "size": 30.0}], "asks": [{"price": 0.36, "size": 30.0}]},
        },
        logger_obj=SimpleNamespace(info=lambda *a, **k: None),
    )
    assert len(mkr_calls) == 2 and mkr_calls[1]["min_resting_bid"] == 0.50

    # 3. compute_sll_and_carry_gatling_budget separates slow passive carry vs fast Gatling locks
    rb_cfg = {"gatling_enabled": True, "gatling_fast_gun_reserve_usd": 22.50}
    harv_b = SimpleNamespace(
        dry_run=False, enforce_gatling_sizing=True, max_exposure=100.0, pending_entry_intents={},
        active_positions={"p1": {"sleeve": "BOND1_UMA_RESOLUTION_CARRY", "notional_usd": 44.58, "candle_expiry_ts": now_f + 3600.0, "status": "POSITION_CONFIRMED"}},
        _is_v5_unleashed_active=lambda: True,
    )
    # Slow BOND1 blocked when free_cash=$16.34 (< $22.50 reserve) AND when slow_used=$44.58 (> 38% of $60.92 NAV)
    assert compute_sll_and_carry_gatling_budget(harv_b, 16.0, 16.34, 44.58, "SINGLE_LEG_LOCK", "BOND1_UMA_RESOLUTION_CARRY", True, rb_cfg, rem_tte_sec=3000.0, now_ts=now_f) == 0.0
    assert compute_sll_and_carry_gatling_budget(harv_b, 20.0, 40.0, 44.58, "SINGLE_LEG_MAKER_LOCK", "BOND1_UMA_RESOLUTION_CARRY", True, rb_cfg, rem_tte_sec=3600.0, now_ts=now_f) == 0.0
    # Fast S2 / MKR_LOCK1 / W_PRUNE1 overrides legacy sll_pool_rem=0.0 and consumes free cash down to $0.50 reserve ($15.84)
    s2_bud = compute_sll_and_carry_gatling_budget(harv_b, 0.0, 16.34, 44.58, "SINGLE_LEG_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR", False, rb_cfg, rem_tte_sec=10.0, now_ts=now_f)
    assert s2_bud == 15.84

    # 4. maybe_early_profit_recycle_htm_lock harvests undisputed BOND1 at $0.998 with positive net PnL
    closed_recs = []
    harv_r = SimpleNamespace(
        dry_run=False,
        active_positions={
            "b1_pos": {
                "sleeve": "BOND1_UMA_RESOLUTION_CARRY", "hold_to_maturity_lock": True, "inventory_reconciled": True,
                "status": "POSITION_CONFIRMED", "token_id": "tok_b1", "side": "YES", "market_id": "m_b1", "condition_id": "c_b1",
                "entry_shares": 25.0, "remaining_shares": 25.0, "notional_usd": 24.825, "entry_fee_cash_usd": 0.0,
                "entry_price": 0.993, "fee_rate_applied": 0.0, "fee_exponent": 1.0, "neg_risk": False, "candle_expiry_ts": now_f + 2400.0,
            }
        },
        _last_known_collateral=16.0,
        _pending_collateral_refresh=False,
        executor=SimpleNamespace(
            execute_unwind_order=lambda **kw: SimpleNamespace(success=True, price=0.998, size=25.0, notional_usd=24.95, fee_usd=0.0),
            invalidate_collateral_cache=lambda: None,
        ),
        calculate_realized_cash_pnl=lambda p, gross, fee: round(float(gross) - float(fee) - float(p["notional_usd"]), 6),
        _handle_unwind_response=lambda tid, p, ures, sh, rsn, st, px: closed_recs.append((tid, round(24.95 - float(p["notional_usd"]), 6))) or "CLOSED",
        save_state=lambda: None,
    )
    assert asyncio.run(maybe_early_profit_recycle_htm_lock(harv_r, "b1_pos", harv_r.active_positions["b1_pos"], {"bids": [{"price": 0.997, "size": 30.0}]}, now_f)) is False
    assert asyncio.run(maybe_early_profit_recycle_htm_lock(harv_r, "b1_pos", harv_r.active_positions["b1_pos"], {"bids": [{"price": 0.998, "size": 30.0}]}, now_f)) is True
    assert len(closed_recs) == 1 and closed_recs[0][1] == 0.125

    # 5. NR4/NR5 mode-aware edge floors & adaptive PreSplitInventoryGun at $15.00 free cash
    cand_nr = tmp_path / "nr_cands.jsonl"
    st_nr = tmp_path / "nr_st.json"
    st_nr.write_text('{"closed_positions": []}', encoding="utf-8")
    dm_nr = SimpleNamespace(single_scan=True, _last_d1_live_emit_ts={})
    spec_nr = SimpleNamespace(end_ts=now_f + 3600.0, is_closed_convert_safe=True, event_id="ev5", neg_risk_market_id="0x" + "1" * 64)
    arb_nr5 = {
        "mode": "NR5_NEGATIVE_COST_FREEROLL",
        "net_edge_per_share": 0.0025,
        "shares": 10.0,
        "no_legs": [
            {"token_id": "n1", "bracket": {"market_id": "m1", "condition_id": "c1", "question_index": 0, "label": "A"}, "walk": {"worst_px": 0.498}},
            {"token_id": "n2", "bracket": {"market_id": "m2", "condition_id": "c2", "question_index": 1, "label": "B"}, "walk": {"worst_px": 0.499}},
        ],
        "yes_sell_legs": [{"token_id": "y3", "bracket": {"market_id": "m3", "label": "C"}, "walk": {"worst_px": 0.006}}],
        "retained_free_yes_brackets": [{"yes_token": "y4", "market_id": "m4", "question_index": 3, "label": "D"}],
    }
    assert emit_negrisk_convert_cand_impl(
        dm_nr, sleeve_source="NR2_CONVERT_NO_SUBSET_ARB", spec=spec_nr, dedupe_key="NR5_TEST",
        arb_hit=arb_nr5, books_by_token={}, now_ts=now_f, fee_bips=0,
        cand_file=cand_nr, default_cand_path=cand_nr, state_file=st_nr, default_state_path=st_nr,
    ) is True

    split_sz = []
    orig_sp = rmg_mod.attempt_onchain_split_position
    rmg_mod.attempt_onchain_split_position = lambda ex, cid, amt, neg_risk=False, **kw: split_sz.append(amt) or {"success": True, "tx_hash": "0x1"}
    try:
        ps15 = PreSplitInventoryGun(cap_usd=15.0)
        harv15 = SimpleNamespace(
            dry_run=False, _startup_reconciled=True, global_halt_active=False, active_positions={}, pending_entry_intents={},
            closed_positions=[], pre_split_inventory_state={}, _last_known_collateral=15.0, _pending_collateral_refresh=False,
            executor=SimpleNamespace(invalidate_collateral_cache=lambda: None), save_state=lambda: None, risk_controller=None,
        )
        shm15 = {"timestamp_unix": now_f, "spot_price": 78000.0, "m15": {"market_id": "m15_btc", "condition_id": "0x" + "2" * 64, "fee_rate": 0.0, "fee_exponent": 1.0, "expiry_ts": now_f + 300.0, "finalized_open": 78000.0, "UP": {"token_id": "1" * 24, "best_bid": 0.504, "bid_depth_1c_shares": 25.0, "best_ask": 0.51, "ask_depth_1c_shares": 25.0}, "DOWN": {"token_id": "2" * 24, "best_bid": 0.503, "bid_depth_1c_shares": 25.0, "best_ask": 0.51, "ask_depth_1c_shares": 25.0}}}
        assert asyncio.run(ps15.tick(harv15, now_f, fast_tick_reader=lambda a: shm15 if a == "BTC" else None)) == "ARMED"
        assert split_sz == [12.0]
    finally:
        rmg_mod.attempt_onchain_split_position = orig_sp






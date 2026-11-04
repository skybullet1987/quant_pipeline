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


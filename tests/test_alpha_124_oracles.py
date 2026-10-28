#!/usr/bin/env python3
"""
Unit Tests for Polymarket Alpha-124 Oracle Parsers & Pricing Kernels
====================================================================
Verifies bit-for-bit parity against every official Polymarket contract example:
  1. Weather METAR parser (`SPECI` exclusion, 8-digit T-group tenths of °C,
     body integer °C fallback, °C -> °F conversion, and half-up rounding).
  2. One-Touch Barrier First-Passage monotonicity (`P_touch >= P_terminal`,
     `P_touch(K1) > P_touch(K2)` for `S < K1 < K2`).
  3. Multi-Strike SVI Breeden-Litzenberger digital probability & monotonicity box detector.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.barrier_onetouch_svi_engine import (
    first_passage_touch_prob,
    parse_barrier_direction,
    parse_strike_from_text,
)
from src.polymarket_research.multistrike_svi_scalper import (
    detect_ladder_monotonicity_boxes,
    evaluate_svi_digital_fair_value,
)
from src.polymarket_research.weather_metar_engine import (
    celsius_to_market_int,
    parse_bucket_bounds,
    parse_metar_line,
    round_half_up_polymarket,
)


def test_polymarket_weather_rounding_spec_examples() -> None:
    # Exact examples from Polymarket RJTT Tokyo spec:
    # "13.9°C counts as 14°C; 17.4°C counts as 17°C; 16.5°C counts as 17°C;
    #  −1.7°C counts as −2°C; −8.5°C counts as −8°C."
    assert round_half_up_polymarket(13.9) == 14
    assert round_half_up_polymarket(17.4) == 17
    assert round_half_up_polymarket(16.5) == 17
    assert round_half_up_polymarket(-1.7) == -2
    assert round_half_up_polymarket(-8.5) == -8

    # Exact examples from Polymarket KHOU Houston (°F) spec:
    # "18.3°C is 64.94°F and counts as 65°F; 17.8°C is 64.04°F and counts as 64°F;
    #  19°C is 66.2°F and counts as 66°F; −22.5°C is exactly −8.5°F and counts as −8°F."
    assert celsius_to_market_int(18.3, "F") == 65
    assert celsius_to_market_int(17.8, "F") == 64
    assert celsius_to_market_int(19.0, "F") == 66
    assert celsius_to_market_int(-22.5, "F") == -8


def test_metar_parser_speci_and_t_remark() -> None:
    ref = datetime(2026, 10, 25, 16, 0, tzinfo=timezone.utc)

    # 1. SPECI must be strictly excluded
    speci = parse_metar_line(
        "SPECI RJTT 251545Z 08010KT 9999 SCT015 24/20 Q1016 RMK T02440200",
        "RJTT",
        ref,
        "Asia/Tokyo",
    )
    assert speci is None

    # 2. Routine METAR with 8-digit T-remark (T01390133 = 13.9°C, T10171022 = -1.7°C)
    m_pos = parse_metar_line(
        "METAR KHOU 251253Z 12005KT 10SM FEW033 14/13 A3002 RMK AO2 T01390133",
        "KHOU",
        ref,
        "America/Chicago",
    )
    assert m_pos is not None and m_pos.has_t_remark and abs(m_pos.temp_c - 13.9) < 1e-6

    m_neg = parse_metar_line(
        "KORD 251051Z 29012KT 10SM CLR M02/M02 A3015 RMK AO2 T10171022",
        "KORD",
        ref,
        "America/Chicago",
    )
    assert m_neg is not None and m_neg.has_t_remark and abs(m_neg.temp_c - (-1.7)) < 1e-6

    # 3. Routine METAR without T-remark falls back to body whole °C (18/12 -> 18°C, M11/M17 -> -11°C)
    m_body = parse_metar_line(
        "METAR RJTT 250600Z 08007KT 9999 FEW020 18/12 Q1017 NOSIG",
        "RJTT",
        ref,
        "Asia/Tokyo",
    )
    assert m_body is not None and (not m_body.has_t_remark) and abs(m_body.temp_c - 18.0) < 1e-6

    m_body_neg = parse_metar_line(
        "METAR UUWW 250300Z 18004KT 9999 OVC015 M11/M17 Q1021",
        "UUWW",
        ref,
        "Europe/Moscow",
    )
    assert m_body_neg is not None and abs(m_body_neg.temp_c - (-11.0)) < 1e-6


def test_bucket_bounds_parser() -> None:
    assert parse_bucket_bounds("16°C or below") == ("C", float("-inf"), 16.0)
    assert parse_bucket_bounds("17°C") == ("C", 17.0, 17.0)
    assert parse_bucket_bounds("26°C or higher") == ("C", 26.0, float("inf"))
    assert parse_bucket_bounds("72-73°F") == ("F", 72.0, 73.0)


def test_barrier_and_svi_monotonicity() -> None:
    assert parse_barrier_direction("Will Bitcoin reach $88,000 on October 25?", "↑ 88,000") == "UP"
    assert parse_barrier_direction("Will Bitcoin dip to $76,000 on October 25?", "↓ 76,000") == "DOWN"
    assert parse_strike_from_text("Will Bitcoin reach $88,000 on October 25?") == 88000.0

    p_84k = first_passage_touch_prob(82000.0, 84000.0, 86400.0, 0.45, "UP", wick_vol_multiplier=1.0)
    p_86k = first_passage_touch_prob(82000.0, 86000.0, 86400.0, 0.45, "UP", wick_vol_multiplier=1.0)
    sv_84k = evaluate_svi_digital_fair_value("BTC", 82000.0, 84000.0, 86400.0, dvol_annual_override=0.45)

    assert p_84k > p_86k > 0.0
    # First-passage touch probability must strictly exceed terminal digital probability
    assert p_84k > sv_84k["p_yes"] * 1.6

    # Monotonicity box detector
    arbs = detect_ladder_monotonicity_boxes([
        {"strike": 80000.0, "is_downward": False, "market_id": "1", "yes_token": "ty1", "no_token": "tn1", "ask_yes": 0.55, "ask_no": 0.46},
        {"strike": 82000.0, "is_downward": False, "market_id": "2", "yes_token": "ty2", "no_token": "tn2", "ask_yes": 0.62, "ask_no": 0.39},
    ])
    assert len(arbs) == 1 and arbs[0]["box_cost_net"] < 0.996


def test_svi_sticky_delta_no_butterfly_arb_on_sol_and_xrp() -> None:
    from src.polymarket_research.deribit_svi_surface import (
        SVIParams,
        compute_breeden_litzenberger_digital,
        scale_svi_sticky_delta,
    )

    t_5d = 5.0 / 365.25
    # Realistic Deribit BTC 5-day SVI slice (~44% ATM IV, moderate downside skew)
    w_atm = (0.44 ** 2) * t_5d
    btc_svi = SVIParams(
        a=w_atm * 0.82,
        b=w_atm * 0.42,
        rho=-0.18,
        m=0.0,
        sigma=0.06,
        t_years=t_5d,
        forward_price=84000.0,
        calibrated_at=1000.0,
    )
    sol_svi = scale_svi_sticky_delta(btc_svi, 1.75, 103.5)
    xrp_svi = scale_svi_sticky_delta(btc_svi, 1.85, 2.15)

    # ATM vol must scale linearly by mult
    assert abs(sol_svi.implied_vol(0.0) - btc_svi.implied_vol(0.0) * 1.75) < 1e-6
    assert abs(xrp_svi.implied_vol(0.0) - btc_svi.implied_vol(0.0) * 1.85) < 1e-6

    # SOL > $100 at Spot=$103.5 over 5 days (~3.4% ITM at ~77% annual vol) must NEVER inflate to 0.82!
    p_sol_100 = compute_breeden_litzenberger_digital(103.5, 100.0, t_5d, sol_svi)
    assert 0.50 <= p_sol_100 <= 0.68, f"Expected realistic SOL > $100 digital prob, got {p_sol_100}"


def test_kmia_convective_rain_cold_pool_bias_guard() -> None:
    from datetime import date, timedelta
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        compute_weather_probabilities,
    )

    eval_utc = datetime(2026, 10, 25, 17, 0, tzinfo=timezone.utc)  # 13:00 EDT midday shower
    kmia_rain = parse_metar_line(
        "METAR KMIA 251653Z 07009KT 6SM RA SCT025CB BKN050 OVC110 25/21 A3004 RMK AO2 SLP173 CB OHD MOV SW P0004 T02500211",
        "KMIA",
        eval_utc,
        "America/New_York",
    )
    assert kmia_rain is not None and kmia_rain.has_convective_precip is True

    buckets = [
        WeatherBucket("m1", "c1", "78-79°F", "78-79°F", "y1", "n1", "F", 78.0, 79.0),
        WeatherBucket("m2", "c2", "80-81°F", "80-81°F", "y2", "n2", "F", 80.0, 81.0),
        WeatherBucket("m3", "c3", "82-83°F", "82-83°F", "y3", "n3", "F", 82.0, 83.0),
        WeatherBucket("m4", "c4", "84°F or higher", "84°F+", "y4", "n4", "F", 84.0, float("inf")),
    ]
    spec = WeatherEventSpec(
        event_id="ev_mia",
        slug="miami-oct-25",
        series_slug="miami-daily-weather",
        title="Highest temperature in Miami on October 25?",
        icao="KMIA",
        city="Miami",
        lat=25.7959,
        lon=-80.2870,
        tz_name="America/New_York",
        obs_date=date(2026, 10, 25),
        metric="HIGH",
        unit="F",
        fee_type="zero_fees",
        end_date_iso="2026-10-26T04:00:00Z",
        buckets=buckets,
    )
    # 60-member ensemble forecasting sunny post-shower rebound to 28.3°C (83°F) at 19Z-20Z
    base_hr = int(datetime(2026, 10, 25, 17, 0, tzinfo=timezone.utc).timestamp())
    ens_hourly = {
        base_hr + h * 3600: [27.3 + (0.9 if h in (2, 3) else 0.2) + (m - 30) * 0.02 for m in range(60)]
        for h in range(0, 10)
    }
    res = compute_weather_probabilities(spec, eval_utc, [kmia_rain], ens_hourly)
    assert res["convective_cold_pool"] is True
    assert res["bias_c"] >= -0.50
    assert res["ensemble_member_count"] == 60
    # 78-79°F must NOT be inflated to 92.6% by the transient midday shower!
    assert res["probs"][0] < 0.35


def test_anchored_strike_regex_ignores_dates() -> None:
    from src.polymarket_research.multistrike_svi_scalper import _extract_threshold_strike

    assert parse_strike_from_text("Will Bitcoin hit a new high on October 30, 2026?", "") is None
    assert parse_strike_from_text("Will Bitcoin reach 105k on October 30?", "") == 105000.0
    assert _extract_threshold_strike("Will Solana close higher on October 30, 2026?", "October 30") is None
    assert _extract_threshold_strike("Will Solana be above $105 on October 30?", "$105") == 105.0


def test_alpha124_l2_depth_maker_queue_and_gamma_404_settlement(tmp_path: Path, monkeypatch) -> None:
    import asyncio
    import src.polymarket_research.alpha_124_shadow_daemon as a124

    # 1. Thin L1 depth ($11) and <98% partial fill must be strictly rejected
    thin = a124.walk_l2_book_asks([{"price": "0.22", "size": "50"}], notional_usd=50.0, fee_rate=0.0)
    assert thin["filled"] is False and thin["reason"] == "THIN_L1_DEPTH"

    partial = a124.walk_l2_book_asks([{"price": "0.50", "size": "60"}], notional_usd=50.0, fee_rate=0.0)
    assert partial["filled"] is False and partial["reason"] == "INSUFFICIENT_DEPTH"

    good = a124.walk_l2_book_asks([{"price": "0.50", "size": "250"}], notional_usd=50.0, fee_rate=0.0)
    assert good["filled"] is True and good["fill_ratio"] == 1.0

    # 2. Resting Maker queue + Gamma 404 settlement
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "opps.json")

    async def _run_sim() -> None:
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        d.spots["BTC"] = 84000.0
        books = {
            "tok_m1": {"bids": [{"price": "0.48", "size": "200"}], "asks": [{"price": "0.50", "size": "200"}]},
        }

        async def fake_fetch_json(url: str, timeout: float = 5.0):
            if "/book?token_id=tok_m1" in url:
                return books["tok_m1"]
            if "/book?token_id=tok_w1_closed" in url:
                return None  # Simulates 404 on closed Polymarket Weather market
            if "/markets/mkt_w1" in url:
                return {
                    "id": "mkt_w1",
                    "closed": True,
                    "umaResolutionStatus": "resolved",
                    "clobTokenIds": '["tok_w1_closed", "tok_w1_no"]',
                    "outcomePrices": '["1", "0"]',
                }
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch_json)
        posted = await d.post_shadow_maker_entry(
            sleeve="M1_SVI_MAKER_SCALP",
            dedupe_key="M1_test_YES",
            asset="BTC",
            title="BTC above $84,000?",
            side_label="YES",
            token_id="tok_m1",
            p_model=0.58,
            close_ts=1999999999.0,
            extra={"market_id": "m_btc", "strike": 84000.0, "is_downward": False},
        )
        assert posted is True
        assert len(d.pending_maker_orders) == 1
        assert len(d.open_positions) == 0  # Must NOT fill immediately!

        # Age order 15s while ask is still 0.50 (> resting_bid 0.49) -> still resting
        oid = next(iter(d.pending_maker_orders))
        d.pending_maker_orders[oid]["created_ts"] -= 15.0
        monkeypatch.setattr(
            a124,
            "evaluate_svi_digital_fair_value",
            lambda *args, **kwargs: {"p_yes": 0.58, "p_no": 0.42, "iv_annual": 0.45, "z_sigma": 0.5, "source": "TEST"},
        )
        await d.manage_pending_maker_orders()
        assert len(d.pending_maker_orders) == 1 and len(d.open_positions) == 0

        # Now trade through resting_bid (best_ask drops to 0.49 while SVI edge remains valid) -> passive Maker fill!
        books["tok_m1"] = {"bids": [{"price": "0.48", "size": "200"}], "asks": [{"price": "0.49", "size": "150"}]}
        await d.manage_pending_maker_orders()
        assert len(d.pending_maker_orders) == 0 and len(d.open_positions) == 1

        # Add closed Weather position whose /book returns 404 -> settles via Gamma /markets/mkt_w1!
        d.open_positions["W1_test"] = {
            "position_id": "W1_test",
            "dedupe_key": "W1_ev_mkt_w1",
            "sleeve": "W1_SOLAR_PEAK_LOCK",
            "asset_or_city": "Tokyo_RJTT",
            "title": "Tokyo 21°C",
            "side": "YES",
            "token_id": "tok_w1_closed",
            "fee_rate": 0.0,
            "entry_ts": 1000.0,
            "close_ts": 2000.0,
            "p_model_entry": 0.92,
            "entry_eff_px_t1000": 0.80,
            "entry_vwap_t1000": 0.80,
            "maker_tp_px": 0.98,
            "tier_fills": {"T1000": {"spent_usd": 100.0, "fee_usd": 0.0, "shares": 125.0}},
            "extra": {"market_id": "mkt_w1"},
            "status": "OPEN",
        }
        await d.manage_open_positions()
        assert "W1_test" not in d.open_positions
        settled_w1 = [p for p in d.closed_positions if p["position_id"] == "W1_test"]
        assert len(settled_w1) == 1 and settled_w1[0]["won"] is True and settled_w1[0]["tier_pnls_usd"]["T1000"] == 25.0

    asyncio.run(_run_sim())


def test_live_executor_min_price_floor_zero_fees_neg_risk_and_maker_entry(tmp_path: Path) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "dry.jsonl")
    # 1. Verify custom min_price_floor=0.20 + zero_fees (rate=0.0, exp=0.0) + neg_risk=True succeeds
    book_25c = {"asks": [{"price": "0.25", "size": "500"}], "bids": [{"price": "0.24", "size": "500"}]}
    res = ex.execute_snipe_order(
        token_id="12345678901234567890",
        target_token="YES",
        notional_usd=25.0,
        target_price=0.25,
        trade_id="TEST_W2_ZERO_FEE",
        market_fee_rate=0.0,
        market_fee_exponent=0.0,
        min_price_floor=0.15,
        max_price_ceiling=0.65,
        prefetched_book=book_25c,
        neg_risk=True,
    )
    assert res.success is True and res.fee_usd == 0.0
    assert ex.get_token_neg_risk("12345678901234567890") is True

    # 2. Verify passive Maker entry dry-run quantization and >=5 share lot enforcement
    m_res = ex.post_maker_entry_order(
        token_id="12345678901234567890",
        price=0.42,
        notional_usd=25.0,
        neg_risk=True,
    )
    assert m_res["success"] is True and m_res["shares"] == 59.0 and m_res["post_only"] is True


def test_same_oracle_dominance_box_math_equal_shares_and_strike_guard() -> None:
    from src.polymarket_research.same_oracle_dominance_box import (
        compute_dominance_box_payout_from_close,
        determine_dominance_legs,
        parse_authoritative_open_price,
        parse_twap_candle_event,
        walk_equal_shares_dominance_box,
    )

    ev_15m = {
        "title": "Ethereum Up or Down - 7:00PM-7:15PM ET",
        "markets": [
            {
                "id": "6033093",
                "conditionId": "0xc15",
                "question": "Ethereum Up or Down - 7:00PM-7:15PM ET",
                "eventStartTime": "2026-10-25T23:00:00Z",
                "endDate": "2026-10-25T23:15:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["tok_15m_up", "tok_15m_dn"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.07, "exponent": 1.0},
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "resolutionSource": "https://data.chain.link/streams/eth-usd-twap-60s-streams",
            }
        ],
    }
    ev_5m = {
        "title": "Ethereum Up or Down - 7:10PM-7:15PM ET",
        "markets": [
            {
                "id": "6033145",
                "conditionId": "0xc5",
                "question": "Ethereum Up or Down - 7:10PM-7:15PM ET",
                "eventStartTime": "2026-10-25T23:10:00Z",
                "endDate": "2026-10-25T23:15:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["tok_5m_up", "tok_5m_dn"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.07, "exponent": 1.0},
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "resolutionSource": "https://data.chain.link/streams/eth-usd-twap-60s-streams",
            }
        ],
    }
    m15 = parse_twap_candle_event(ev_15m, "ETH", "15m")
    m5 = parse_twap_candle_event(ev_5m, "ETH", "5m")
    assert m15 is not None and m5 is not None

    # Non-TWAP (e.g. Binance spot) must be rejected
    ev_bad = {"markets": [{**ev_5m["markets"][0], "cryptoMarketConfig": {"twapEnabled": False}, "resolutionSource": "binance"}]}
    assert parse_twap_candle_event(ev_bad, "ETH", "5m") is None

    # Authoritative 60s-TWAP guard strictly rejects legacy crypto-price spot payloads and unclosed Gamma events
    assert parse_authoritative_open_price({"openPrice": 2393.534264, "completed": False, "cached": True}) is None
    assert parse_authoritative_open_price([{"closed": False, "eventMetadata": {"finalPrice": 2393.534264}}]) is None
    assert parse_authoritative_open_price([{"closed": True, "eventMetadata": {"finalPrice": 2393.534264}}]) == 2393.534264

    # Case 1: K_15m > K_5m -> 5M_UP + 15M_DOWN
    dom = determine_dominance_legs(m15, 2393.5343, m5, 2392.8455)
    assert dom is not None and dom["regime"] == "5M_UP_PLUS_15M_DOWN"
    assert dom["leg_a"]["token_id"] == "tok_5m_up" and dom["leg_b"]["token_id"] == "tok_15m_dn"

    # Payout across all 3 regions of R must be >= $1.00 (and $2.00 inside [K_low, K_high))
    assert compute_dominance_box_payout_from_close(2389.55, dom["k_low"], dom["k_high"]) == 1.0
    assert compute_dominance_box_payout_from_close(2393.10, dom["k_low"], dom["k_high"]) == 2.0
    assert compute_dominance_box_payout_from_close(2399.00, dom["k_low"], dom["k_high"]) == 1.0

    # Equal-share L2 walk caps to thinner leg (45 shares) and includes both 7% p(1-p) taker fees
    w_box = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.35", "size": "45"}],
        asks_b_raw=[{"price": "0.56", "size": "200"}],
        target_budget_usd=100.0,
        max_box_cost_net=0.995,
    )
    assert w_box["filled"] is True
    assert w_box["shares"] == 45
    assert w_box["leg_a_walk"]["shares"] == 45 and w_box["leg_b_walk"]["shares"] == 45
    assert w_box["box_cost_net"] < 0.95 and w_box["guaranteed_min_profit_usd"] > 2.0

    # Expensive box (> $0.995) is rejected
    w_exp = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.52", "size": "200"}],
        asks_b_raw=[{"price": "0.47", "size": "200"}],
        target_budget_usd=100.0,
        max_box_cost_net=0.995,
    )
    assert w_exp["filled"] is False

    # Regression (SOL D1_QUIET_BOOK_BOX 23:56 UTC): 11 shares @ $0.90 + 138 @ $0.91 with Leg B @ $0.07 ($13.50 budget, 0.985 cap)
    # 11 x $0.07 = $0.77 Leg B is below Polymarket's $1 marketable-BUY minimum -> must reject (would leave a naked leg).
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    w_sol_sub1 = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.90", "size": "11"}, {"price": "0.91", "size": "138.36"}],
        asks_b_raw=[{"price": "0.07", "size": "66.7"}],
        target_budget_usd=13.50,
        max_box_cost_net=0.985,
        min_shares=8,
        min_box_notional_usd=7.0,
    )
    assert w_sol_sub1["filled"] is False
    assert w_sol_sub1["reason"] == "LEG_BELOW_1USD_MIN"

    # Same trim geometry with a >= $1 Leg B: must trim to the 11 L1 shares so worst_px never breaches 0.985.
    w_sol_trim = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.86", "size": "11"}, {"price": "0.88", "size": "138.36"}],
        asks_b_raw=[{"price": "0.10", "size": "66.7"}],
        target_budget_usd=13.50,
        max_box_cost_net=0.985,
        min_shares=8,
        min_box_notional_usd=7.0,
    )
    assert w_sol_trim["filled"] is True
    assert w_sol_trim["shares"] == 11
    assert w_sol_trim["leg_a_walk"]["worst_px"] == 0.86
    assert w_sol_trim["leg_b_walk"]["worst_px"] == 0.10
    assert w_sol_trim["box_cost_net"] <= 0.985
    ex_dry = PolymarketLiveExecutor(dry_run=True)
    r_exec_trim = ex_dry.execute_atomic_dominance_box(
        box_id="D1_SOL_TRIM_TEST",
        leg_a_token_id="tok_sol_15m_up",
        leg_a_label="15M_UP",
        leg_a_limit_price=w_sol_trim["leg_a_walk"]["worst_px"],
        leg_b_token_id="tok_sol_5m_dn",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=w_sol_trim["leg_b_walk"]["worst_px"],
        shares=w_sol_trim["shares"],
        max_box_cost_net=0.985,
    )
    assert r_exec_trim["success"] is True

    # If L1 has < min_shares (e.g. only 4 shares @ $0.90) and L2 worst_px breaches 0.985, walker cleanly rejects
    w_sol_too_thin = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.90", "size": "4"}, {"price": "0.91", "size": "138.36"}],
        asks_b_raw=[{"price": "0.07", "size": "66.7"}],
        target_budget_usd=13.50,
        max_box_cost_net=0.985,
        min_shares=8,
        min_box_notional_usd=7.0,
    )
    assert w_sol_too_thin["filled"] is False and w_sol_too_thin["reason"] == "WORST_LIMIT_COST_ABOVE_CAP"


def test_alpha124_d1_same_oracle_dominance_box_entry_and_settlement(tmp_path: Path, monkeypatch) -> None:
    import asyncio
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec

    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "state_d1.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ledger_d1.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "opps_d1.json")

    async def _sim_d1() -> None:
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_sim = 1792970000.0
        end_sim = now_sim + 180.0
        m15 = TwapCandleMarketSpec(
            asset="ETH", horizon="15m", market_id="6033093", condition_id="0xc15",
            title="ETH 15m", start_iso="2026-10-25T23:00:00Z", end_iso="2026-10-25T23:15:00Z",
            start_ts=end_sim - 900.0, end_ts=end_sim, up_token="tok_15m_up", down_token="tok_15m_dn",
            fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
            resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams",
        )
        m5 = TwapCandleMarketSpec(
            asset="ETH", horizon="5m", market_id="6033145", condition_id="0xc5",
            title="ETH 5m", start_iso="2026-10-25T23:10:00Z", end_iso="2026-10-25T23:15:00Z",
            start_ts=end_sim - 300.0, end_ts=end_sim, up_token="tok_5m_up", down_token="tok_5m_dn",
            fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
            resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams",
        )
        d.dominance_pairs[f"ETH_{int(end_sim)}"] = (m15, m5)

        prev_15m_slug = f"slug=eth-updown-5m-{int(round(m15.start_ts)) - 300}"
        prev_5m_slug = f"slug=eth-updown-5m-{int(round(m5.start_ts)) - 300}"

        async def fake_fetch(url: str, timeout: float = 5.0):
            if prev_15m_slug in url:
                return [{"slug": url.split("slug=", 1)[1], "closed": True, "eventMetadata": {"finalPrice": 2390.00}}]
            if prev_5m_slug in url:
                return [{"slug": url.split("slug=", 1)[1], "closed": True, "eventMetadata": {"finalPrice": 2394.00}}]
            if "token_id=tok_15m_up" in url:
                return {"bids": [{"price": "0.52", "size": "150"}], "asks": [{"price": "0.54", "size": "150"}]}
            if "token_id=tok_5m_dn" in url:
                return {"bids": [{"price": "0.38", "size": "150"}], "asks": [{"price": "0.40", "size": "150"}]}
            if "token_id=tok_15m_dn" in url or "token_id=tok_5m_up" in url:
                return {"bids": [{"price": "0.47", "size": "150"}], "asks": [{"price": "0.50", "size": "150"}]}
            if "/markets/6033093" in url:
                # Corridor finish (e.g. 2392.00): 15m UP wins ($1) AND 5m DOWN wins ($1) -> 2X double payout!
                return {
                    "id": "6033093", "closed": True, "umaResolutionStatus": "resolved",
                    "clobTokenIds": '["tok_15m_up", "tok_15m_dn"]', "outcomePrices": '["1", "0"]',
                }
            if "/markets/6033145" in url:
                return {
                    "id": "6033145", "closed": True, "umaResolutionStatus": "resolved",
                    "clobTokenIds": '["tok_5m_up", "tok_5m_dn"]', "outcomePrices": '["0", "1"]',
                }
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch)
        opps: list = []
        await d.scan_same_oracle_dominance_boxes(opps, now_ts=now_sim)
        assert len(d.open_positions) == 1
        pos = next(iter(d.open_positions.values()))
        assert pos["sleeve"] == "D1_SAME_ORACLE_DOMINANCE_BOX"
        assert pos["entry_eff_px_t1000"] < 0.995

        # Expire box and verify 2X corridor settlement
        pos["close_ts"] = 1000.0
        await d.manage_open_positions()
        assert len(d.open_positions) == 0 and len(d.closed_positions) == 1
        closed = d.closed_positions[0]
        assert closed["status"] == "SETTLED_DOMINANCE_DOUBLE_2X"
        assert closed["net_payout_per_share"] == 2.0
        assert closed["tier_pnls_usd"]["T1000"] > 100.0

    asyncio.run(_sim_d1())


def test_live_executor_atomic_dominance_box_and_legging_unwind(tmp_path: Path, monkeypatch) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "box.jsonl")
    # 1. Dry-run: thinner leg (leg_b_avail=30 < leg_a_avail=120) must dispatch first
    r_ok = ex.execute_atomic_dominance_box(
        box_id="BOX_ETH_1",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.54,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.40,
        shares=25,
        max_box_cost_net=0.995,
        leg_a_avail_shares=120.0,
        leg_b_avail_shares=30.0,
    )
    assert r_ok["success"] is True and r_ok["leg_1"]["label"] == "5M_DOWN"

    # 2. Pre-flight cap guard rejects box whose limit prices + fees > 0.995
    r_cap = ex.execute_atomic_dominance_box(
        box_id="BOX_EXP",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.55,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.44,
        shares=25,
        max_box_cost_net=0.995,
    )
    assert r_cap["success"] is False and "WORST_LIMIT_BOX_COST_EXCEEDS_CAP" in r_cap["error"]

    # 3. Live mocked legging failure: Leg 1 fills, Leg 2 FOK rejects -> immediate Leg 1 unwind!
    ex.dry_run = False
    ex.is_authenticated = True

    class FakeClient:
        def __init__(self) -> None:
            self.posts = 0

        def create_order(self, args, options=None):
            return {"token_id": args.token_id, "price": args.price, "size": args.size}

        def post_order(self, signed, order_type):
            self.posts += 1
            if self.posts == 1:
                return {"orderID": "OID_LEG1_FILLED"}
            return {"errorMsg": "FOK order couldn't be fully filled"}

    ex.client = FakeClient()
    monkeypatch.setattr(ex, "get_token_tick_size", lambda tid: 0.01)
    monkeypatch.setattr(ex, "get_token_neg_risk", lambda tid, explicit_neg_risk=None: False)
    unwind_calls: list = []

    def fake_unwind(token_id: str, size: float, side: str = "SELL", min_price: float = 0.01, neg_risk=None):
        unwind_calls.append((token_id, size, side, min_price))
        return {"success": True, "orderID": "OID_UNWIND_1", "matched_size": size}

    monkeypatch.setattr(ex, "execute_unwind_order", fake_unwind)
    r_leg = ex.execute_atomic_dominance_box(
        box_id="BOX_LEG_FAIL",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.54,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.40,
        shares=20,
        max_box_cost_net=0.995,
        leg_a_avail_shares=25.0,
        leg_b_avail_shares=100.0,
    )
    assert r_leg["success"] is False
    assert r_leg["stage"] == "LEG_2_REJECTED_UNWOUND"
    assert r_leg["legged_out"] is True
    assert len(unwind_calls) == 1 and unwind_calls[0][0] == "tok_a" and unwind_calls[0][1] == 20.0


def test_exact_twap_lock_engine_math_and_whipsaw_guard() -> None:
    import math
    from src.polymarket_research.exact_twap_lock_engine import (
        compute_exact_twap_lock_probability,
        student_t_df5_cdf,
    )

    assert abs(student_t_df5_cdf(0.0) - 0.5) < 1e-12
    assert abs(student_t_df5_cdf(2.5) + student_t_df5_cdf(-2.5) - 1.0) < 1e-12
    normal_3 = 0.5 * (1.0 + math.erf(3.0 / math.sqrt(2.0)))
    assert 0.96 < student_t_df5_cdf(3.0) < normal_3  # Fat tails strictly more conservative than Gaussian

    end_ts = 1792970300.0
    now_ts = end_ts - 18.0  # 18s remaining => 42s (70%) of 60s TWAP already banked!
    samples = [(end_ts - 60.0 + i, 2404.50) for i in range(43)]

    lock = compute_exact_twap_lock_probability(
        asset="ETH",
        open_price=2400.123456789012,
        current_usd_spot=2404.60,
        rem_seconds=18.0,
        now_ts=now_ts,
        end_ts=end_ts,
        spot_samples=samples,
        iv_annual=0.65,
        usd_direct_feed=True,
    )
    assert lock["eligible"] is True
    assert lock["side"] == "UP"
    assert lock["eff_alpha"] > 0.65
    assert lock["p_lock"] >= 0.975

    # Whipsaw guard: banked mean above K_open (mu_twap > K_open) while current_usd_spot crashed below K_open
    whipsaw = compute_exact_twap_lock_probability(
        asset="ETH",
        open_price=2400.123456789012,
        current_usd_spot=2399.50,
        rem_seconds=18.0,
        now_ts=now_ts,
        end_ts=end_ts,
        spot_samples=samples,
        iv_annual=0.65,
        usd_direct_feed=True,
    )
    assert whipsaw["eligible"] is False and whipsaw["reason"] == "WHIPSAW_SPLIT_ACROSS_STRIKE"

    # Out-of-window (> 45s) rejected
    early = compute_exact_twap_lock_probability(
        asset="ETH",
        open_price=2400.0,
        current_usd_spot=2405.0,
        rem_seconds=52.0,
        now_ts=end_ts - 52.0,
        end_ts=end_ts,
        spot_samples=[],
    )
    assert early["eligible"] is False


def test_r01_relayer_hmac_deposit_wallet_eip712_and_negrisk_payout_logs(tmp_path: Path) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    # 1. Exact py_clob_client / py-builder-signing-sdk HMAC signature parity
    hdrs = PolymarketLiveExecutor.build_relayer_builder_headers(
        api_key="test-api-key",
        secret="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        passphrase="test-passphrase",
        method="POST",
        request_path="/orders",
        body={"hash": "0x123"},
        timestamp=1000000,
    )
    assert hdrs["POLY_BUILDER_SIGNATURE"] == "wdXSC4akzPKG0yFk9FJrIb7-rg73v_M7QDxIBp-P1CQ="
    assert hdrs["POLY_BUILDER_TIMESTAMP"] == "1000000"
    try:
        from py_clob_client.signing.hmac import build_hmac_signature
        assert hdrs["POLY_BUILDER_SIGNATURE"] == build_hmac_signature(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", "1000000", "POST", "/orders", {"hash": "0x123"}
        )
    except ImportError:
        pass

    # 2. DepositWallet EIP-712 batch payload & NegRiskAdapter PayoutRedemption log parsing
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "r01.jsonl")
    ex.funder_address = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
    cond_id = "0x" + ("ab" * 32)
    me_topic = "0x" + ex.funder_address.lower().replace("0x", "").rjust(64, "0")

    try:
        import eth_account  # noqa: F401
        import eth_utils  # noqa: F401
        import web3  # noqa: F401

        test_pk = "0x" + ("11" * 32)
        batch = PolymarketLiveExecutor.build_deposit_wallet_relayer_batch(
            private_key=test_pk,
            wallet_address=ex.funder_address,
            nonce=7,
            deadline=1900000000,
            calls=[{"target": PolymarketLiveExecutor.CTF_ADDRESS, "value": "0", "data": "0x12345678"}],
            chain_id=137,
        )
        assert batch["type"] == "WALLET"
        assert batch["nonce"] == "7"
        assert batch["signature"].startswith("0x") and len(batch["signature"]) == 132
        assert batch["depositWalletParams"]["depositWallet"].lower() == ex.funder_address.lower()

        ctf_log = {
            "address": PolymarketLiveExecutor.CTF_ADDRESS,
            "topics": [PolymarketLiveExecutor._payout_redemption_topic(), me_topic, "0x" + ("00" * 32)],
            "data": "0x" + ("ab" * 32) + ("00" * 32) + f"{25_500_000:064x}",
            "transactionHash": "0xtx_ctf",
            "blockNumber": "0x100",
        }
        nr_log = {
            "address": PolymarketLiveExecutor.NEG_RISK_ADAPTER_ADDRESS,
            "topics": [PolymarketLiveExecutor._neg_risk_payout_redemption_topic(), me_topic, cond_id],
            "data": "0x" + ("00" * 32) + f"{42_250_000:064x}",
            "transactionHash": "0xtx_nr",
            "blockNumber": "0x101",
        }
        parsed = ex.parse_payout_redemption_logs([ctf_log, nr_log], cond_id)
        assert len(parsed) == 2
        assert abs(parsed[0]["payout_usd"] - 25.50) < 1e-6
        assert abs(parsed[1]["payout_usd"] - 42.25) < 1e-6
    except ImportError:
        pass


def test_alpha124_w2_maker_overround_m4_shock_wakeup_and_s2_twap_lock(tmp_path: Path, monkeypatch) -> None:
    import asyncio
    import json
    import time
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.multistrike_svi_scalper import StrikeRungSpec
    from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec

    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "state_all.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ledger_all.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "opps_all.json")
    shock_file = tmp_path / "live_shock_triggers.jsonl"
    shock_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(a124, "SHOCK_TRIGGER_FILE", shock_file)

    async def _sim_new_sleeves() -> None:
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_sim = time.time()

        books = {
            "tok_w2m": {"bids": [{"price": "0.26", "size": "150"}], "asks": [{"price": "0.30", "size": "150"}]},
            "tok_m1_yes": {"bids": [{"price": "0.49", "size": "200"}], "asks": [{"price": "0.51", "size": "200"}]},
            "tok_m4_no": {"bids": [{"price": "0.46", "size": "250"}], "asks": [{"price": "0.48", "size": "250"}]},
            "tok_s2_up": {"bids": [{"price": "0.86", "size": "250"}], "asks": [{"price": "0.88", "size": "250"}]},
        }

        async def fake_fetch(url: str, timeout: float = 5.0):
            for tid, bk in books.items():
                if f"token_id={tid}" in url:
                    return bk
            if "slug=eth-updown-5m-1792969800" in url:
                return [{"slug": url.split("slug=", 1)[1], "closed": True, "eventMetadata": {"finalPrice": 2405.80}}]
            if "slug=eth-updown-5m-" in url:
                return [{"slug": url.split("slug=", 1)[1], "closed": True, "eventMetadata": {"finalPrice": 2400.123456789012}}]
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch)

        # 1. W2_MAKER_OVERROUND: post resting 0%-fee bid inside 0.26 / 0.30 spread -> resting_bid = 0.27
        ok_w2m = await d.post_shadow_maker_entry(
            sleeve="W2_MAKER_OVERROUND",
            dedupe_key="W2M_ev1_m1",
            asset="Miami_KMIA",
            title="Miami 82-83°F",
            side_label="YES",
            token_id="tok_w2m",
            p_model=0.40,
            close_ts=now_sim + 28800.0,
            extra={"event_id": "ev1", "market_id": "m1", "icao": "KMIA", "obs_date": "2026-10-25"},
        )
        assert ok_w2m is True
        oid_w2m = next(iter(d.pending_maker_orders))
        assert d.pending_maker_orders[oid_w2m]["resting_bid"] == 0.27
        d.pending_maker_orders[oid_w2m]["created_ts"] -= 15.0
        books["tok_w2m"] = {"bids": [{"price": "0.26", "size": "150"}], "asks": [{"price": "0.27", "size": "150"}]}
        await d.manage_pending_maker_orders()
        assert any(p["sleeve"] == "W2_MAKER_OVERROUND" for p in d.open_positions.values())

        # 2. M4_SHOCK_STRIKE_CATCHUP + <250ms Adverse M1 Maker Cancel
        d.spots["BTC"] = 84000.0
        await d.post_shadow_maker_entry(
            sleeve="M1_SVI_MAKER_SCALP",
            dedupe_key="M1_btc_84k_YES",
            asset="BTC",
            title="BTC above $84,000?",
            side_label="YES",
            token_id="tok_m1_yes",
            p_model=0.58,
            close_ts=now_sim + 43200.0,
            extra={"market_id": "m_btc_84k", "strike": 84000.0, "is_downward": False},
        )
        assert len(d.pending_maker_orders) == 1
        d.strike_ladders["BTC_ev"] = [
            StrikeRungSpec(
                asset="BTC",
                series_slug="btc-multi-strikes",
                event_id="ev_btc",
                market_id="m_btc_84k",
                condition_id="0xc_btc",
                title="Bitcoin above ___ on Oct 25?",
                question="Bitcoin above $84,000 on Oct 25?",
                strike=84000.0,
                is_downward=False,
                end_ts=now_sim + 43200.0,
                yes_token="tok_m1_yes",
                no_token="tok_m4_no",
            )
        ]
        monkeypatch.setattr(
            a124,
            "evaluate_svi_digital_fair_value",
            lambda *args, **kwargs: {"p_yes": 0.38, "p_no": 0.62, "iv_annual": 0.45, "z_sigma": 0.8, "source": "TEST"},
        )
        # Append a fresh -35 bps SELL shock (84000 -> 83700) to live_shock_triggers.jsonl
        shock_payload = {
            "shock_id": "SHK_BTC_1",
            "t0_unix": time.time(),
            "shock_source": "FUTURES",
            "asset": "BTC",
            "shock_direction": "SELL",
            "shock_ofi": -0.88,
            "shock_volume_100ms": 3200000.0,
            "spot_at_t0": 83700.0,
        }
        with open(shock_file, "a", encoding="utf-8") as sf:
            sf.write(json.dumps(shock_payload) + "\n")

        shocks = d.poll_fresh_shock_triggers()
        assert len(shocks) == 1
        s_opps: list = []
        await d.handle_shock_triggers(shocks, s_opps)
        # Resting YES maker order must be cancelled BEFORE passive fill, and M4 NO snipe opened!
        assert len(d.pending_maker_orders) == 0
        assert any(p["sleeve"] == "M4_SHOCK_STRIKE_CATCHUP" and p["side"] == "NO" for p in d.open_positions.values())

        # 3. S2_EXACT_TWAP_LOCK: final-18s 5m ETH candle lock + authoritative Chainlink TWAP settlement
        end_5m = now_sim + 18.0
        sp5 = TwapCandleMarketSpec(
            asset="ETH",
            horizon="5m",
            market_id="6055555",
            condition_id="0xc_s2",
            title="ETH Up or Down 5m",
            start_iso="2026-10-25T23:10:00Z",
            end_iso="2026-10-25T23:15:00Z",
            start_ts=end_5m - 300.0,
            end_ts=end_5m,
            up_token="tok_s2_up",
            down_token="tok_s2_dn",
            fee_rate=0.07,
            fee_exponent=1.0,
            neg_risk=False,
            twap_lookback_sec=60,
            resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams",
        )
        d.twap_candles[f"ETH_5m_{int(end_5m)}"] = sp5
        d.spots["ETH"] = 2406.00
        d.usd_direct_flags["ETH"] = True
        for i in range(43):
            d.usd_spot_hist["ETH"].append((end_5m - 60.0 + i, 2405.80))
        monkeypatch.setattr(a124, "get_wing_implied_vol", lambda *args, **kwargs: (0.65, "TEST"))

        tw_opps: list = []
        await d.scan_exact_twap_locks(tw_opps, now_ts=now_sim)
        s2_positions = [p for p in d.open_positions.values() if p["sleeve"] == "S2_EXACT_TWAP_LOCK"]
        assert len(s2_positions) == 1
        s2_pos = s2_positions[0]
        assert s2_pos["side"] == "UP" and s2_pos["p_model_entry"] >= 0.97

        # Settle S2 via authoritative Chainlink closePrice fallback
        s2_pos["close_ts"] = now_sim - 200.0
        await d.manage_open_positions()
        settled_s2 = [p for p in d.closed_positions if p["sleeve"] == "S2_EXACT_TWAP_LOCK"]
        assert len(settled_s2) == 1 and settled_s2[0]["won"] is True
        assert settled_s2[0]["status"] == "SETTLED_ORACLE_TWAP_WIN"

    asyncio.run(_sim_new_sleeves())


def test_live_daily_projections_working_capital_and_monotonicity():
    """
    Verifies the live day-by-day projection engine enforces:
      1. Exact 3-tier `v3.9.3` sizing (`<$88 -> $12`, `$88..$110 -> 18%`, `>=$110 -> 22%`)
      2. Strict scenario monotonicity (`P25 < P50 < P75`) on every day D1..D30
      3. Working-capital partition + L2 depth slippage decay (`_depth_decay`)
    """
    from scripts.polymarket_daily_projections import (
        _depth_decay,
        build_live_projections,
        compute_v393_ticket_size,
    )

    assert compute_v393_ticket_size(60.00) == 12.0
    assert compute_v393_ticket_size(73.01) == 13.14
    assert compute_v393_ticket_size(76.80) == 13.82
    assert compute_v393_ticket_size(95.00) == 17.10
    assert compute_v393_ticket_size(120.00) == 26.40
    assert _depth_decay(15.0) == 1.0
    assert 0.58 <= _depth_decay(150.0) < 0.85

    proj = build_live_projections(days=30, fallback_equity=76.80)
    rows = proj["day_by_day_schedule"]
    assert len(rows) == 30
    quarantined_check = {
        "B1_CONVEX_TAIL_YES",
        "M4_SHOCK_STRIKE_CATCHUP",
        "W2_ENSEMBLE_VALUE",
        "W2_MAKER_OVERROUND",
        "M1_SVI_MAKER_SCALP",
        "M2_STRIKE_CONVERGENCE",
        "P1_PREOPEN_MAKER_STRADDLE",
        "SLEEVE_XRP_V392_SHADOW",
    }
    assert all(g["sleeve"] not in quarantined_check for g in proj["sleeve_graduation_live_tracker"])
    for r in rows:
        assert r["p25_end_equity_usd"] < r["p50_end_equity_usd"] < r["p75_end_equity_usd"]
        assert r["p50_daily_pnl_usd"] > 0
        for bad_k in ("B1_convex_barrier_tails", "W2_weather_maker_and_mos", "M1_M4_svi_maker_and_shock"):
            assert bad_k not in r["p50_sleeve_pnl_breakdown_usd"]


def test_external_dual_audit_alpha124_and_oracle_regressions(tmp_path: Path, monkeypatch) -> None:
    """
    Regression suite covering ChatGPT + Gemini dual adversarial audit findings across Alpha-124:
      - F-08: METAR missing-dewpoint 8-digit T-group remarks (`T0023////`, `T1017////`)
      - M-02: `COR` amended METAR priority + deterministic ensemble alignment
      - H-02: Local 23:00-23:59 observation window does NOT prematurely lock day-end at 100%
      - F-12: Weather `feeSchedule` dynamic fee parsing (`fees_enabled` vs `zero_fees`)
      - H-01 / F-11 / H-06 / F-15: Strict USD `/dev/shm` anchor, clock-skew guard, & trapezoidal TWAP integral
      - F-18: `verify_same_oracle_pair` rejects empty `resolution_source`
      - H-04: `fetch_binance_window_extremes_sync` stitches initial partial-hour `1m` klines
      - C-02 / F-10 / F-03 / M-04 / F-19: `inflight_keys` race guard, cancel-window adverse fill, corrupt JSONL skip
    """
    import asyncio
    import json
    import time
    from datetime import date
    from zoneinfo import ZoneInfo

    import src.polymarket_research.alpha_124_shadow_daemon as a124
    import src.polymarket_research.barrier_onetouch_svi_engine as b_eng
    import src.polymarket_research.exact_twap_lock_engine as etwap
    from src.polymarket_research.same_oracle_dominance_box import (
        TwapCandleMarketSpec,
        verify_same_oracle_pair,
    )
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        compute_weather_probabilities,
        parse_weather_event,
    )

    ref = datetime(2026, 10, 25, 16, 0, tzinfo=timezone.utc)

    # 1. F-08 + M-02: Missing-dewpoint T-remarks (`T0023////`) and `COR` METAR flag
    m_slash_pos = parse_metar_line(
        "METAR RJTT 250600Z 08007KT 9999 FEW020 02/// Q1017 RMK AO2 T0023////",
        "RJTT",
        ref,
        "Asia/Tokyo",
    )
    assert m_slash_pos is not None and m_slash_pos.has_t_remark is True and abs(m_slash_pos.temp_c - 2.3) < 1e-6

    m_slash_neg = parse_metar_line(
        "METAR KORD 251051Z 29012KT 10SM CLR M02/// A3015 RMK AO2 T1017//// SLP210",
        "KORD",
        ref,
        "America/Chicago",
    )
    assert m_slash_neg is not None and m_slash_neg.has_t_remark is True and abs(m_slash_neg.temp_c - (-1.7)) < 1e-6

    m_cor = parse_metar_line(
        "METAR COR RJTT 250600Z 08007KT 9999 FEW020 19/12 Q1017 RMK AO2 T01940120",
        "RJTT",
        ref,
        "Asia/Tokyo",
    )
    assert m_cor is not None and m_cor.is_corrected is True and abs(m_cor.temp_c - 19.4) < 1e-6

    # 2. H-02: 23:30 local time must NOT deterministically lock day-end before 23:53-23:59 METAR!
    tz_ny = ZoneInfo("America/New_York")
    obs_2253 = parse_metar_line(
        "METAR KLGA 260251Z 31012KT 10SM CLR 15/06 A3012 RMK AO2 T01500061",
        "KLGA",
        datetime(2026, 10, 26, 3, 0, tzinfo=timezone.utc),
        "America/New_York",
    )
    assert obs_2253 is not None and obs_2253.local_dt.date() == date(2026, 10, 25)
    low_buckets = [
        WeatherBucket("b1", "c1", "14°C or below", "14°C-", "y1", "n1", "C", float("-inf"), 14.0),
        WeatherBucket("b2", "c2", "15°C", "15°C", "y2", "n2", "C", 15.0, 15.0),
        WeatherBucket("b3", "c3", "16°C", "16°C", "y3", "n3", "C", 16.0, 16.0),
        WeatherBucket("b4", "c4", "17°C or higher", "17°C+", "y4", "n4", "C", 17.0, float("inf")),
    ]
    low_spec = WeatherEventSpec(
        event_id="ev_klga_low",
        slug="nyc-low",
        series_slug="nyc-daily-weather",
        title="Lowest temperature in NYC on October 25?",
        icao="KLGA",
        city="NYC",
        lat=40.7769,
        lon=-73.8740,
        tz_name="America/New_York",
        obs_date=date(2026, 10, 25),
        metric="LOW",
        unit="C",
        fee_type="zero_fees",
        end_date_iso="2026-10-26T05:00:00Z",
        buckets=low_buckets,
    )
    eval_2330_local = datetime(2026, 10, 25, 23, 30, tzinfo=tz_ny).astimezone(timezone.utc)
    midnight_utc_ts = int(datetime(2026, 10, 26, 0, 0, tzinfo=tz_ny).astimezone(timezone.utc).timestamp())
    ens_cold_midnight = {midnight_utc_ts: [12.0] * 30}
    res_2330 = compute_weather_probabilities(low_spec, eval_2330_local, [obs_2253], ens_cold_midnight)
    assert res_2330["rem_hours_count"] == 1
    assert res_2330["probs"][0] > 0.50  # <=14°C reflects plunging 23:54 forecast instead of false 15°C lock!

    eval_0005_next = datetime(2026, 10, 26, 0, 5, tzinfo=tz_ny).astimezone(timezone.utc)
    res_after_midnight = compute_weather_probabilities(low_spec, eval_0005_next, [obs_2253], ens_cold_midnight)
    assert res_after_midnight["probs"][1] > 0.99  # After 00:00 local, 15°C deterministically locks!

    # 3. F-12: Weather `feeSchedule` parsed dynamically if Polymarket enables fees
    w_ev_fees = {
        "id": "ev_fee_test",
        "title": "Highest temperature in Tokyo on October 26?",
        "endDate": "2026-10-26T15:00:00Z",
        "markets": [
            {
                "id": f"m_{idx}",
                "conditionId": f"0xc_{idx}",
                "groupItemTitle": lbl,
                "description": "Resolves via https://aviationweather.gov/api/data/metar?ids=RJTT excluding SPECI on 26 Oct '26.",
                "clobTokenIds": f'["y_{idx}", "n_{idx}"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.05, "exponent": 1.0},
            }
            for idx, lbl in enumerate(["18°C or below", "19°C", "20°C", "21°C or higher"])
        ],
    }
    parsed_fee_ev = parse_weather_event(w_ev_fees)
    assert parsed_fee_ev is not None and parsed_fee_ev.fee_type == "fees_enabled"
    assert all(abs(b.fee_rate - 0.05) < 1e-9 for b in parsed_fee_ev.buckets)

    # 4. H-01 + F-11 + H-06: Strict USD `/dev/shm` anchor & trapezoidal TWAP integration
    monkeypatch.setattr(etwap, "SHM_DIR", tmp_path)
    now_u = 1792975000.0
    shm_btc = tmp_path / "pm_fast_tick_BTC.json"
    # USDT-only payload must NOT be accepted as USD anchor (`H-01`)
    shm_btc.write_text(json.dumps({"timestamp_unix": now_u, "spot_price": 84100.0}), encoding="utf-8")
    assert etwap.read_shm_usd_anchor("BTC", now_u)["usd_spot"] is None
    # Future clock skew > 1.5s rejected (`F-11`)
    shm_btc.write_text(json.dumps({"timestamp_unix": now_u + 4.0, "chainlink_proxy_spot": 84050.0}), encoding="utf-8")
    assert etwap.read_shm_usd_anchor("BTC", now_u)["usd_spot"] is None
    # Verified Chainlink USD proxy accepted
    shm_btc.write_text(json.dumps({"timestamp_unix": now_u - 0.5, "chainlink_proxy_spot": 84050.0}), encoding="utf-8")
    assert etwap.read_shm_usd_anchor("BTC", now_u)["usd_spot"] == 84050.0

    # Bursty uneven samples + >12s `shm_twap_60s` contamination check (`H-06`)
    end_tw = now_u + 30.0
    no_bank = etwap.compute_exact_twap_lock_probability(
        asset="ETH",
        open_price=2400.0,
        current_usd_spot=2403.0,
        rem_seconds=30.0,
        now_ts=now_u,
        end_ts=end_tw,
        spot_samples=[],
        shm_twap_60s=2415.0,
        usd_direct_feed=True,
    )
    assert no_bank["eff_alpha"] == 0.0  # Rolling 60s TWAP rejected at rem=30s (50% pre-window contamination!)

    # 5. F-18: `verify_same_oracle_pair` rejects missing/empty `resolution_source`
    m15_empty = TwapCandleMarketSpec(
        "ETH", "15m", "1", "0x1", "ETH 15m", "2026-10-25T23:00:00Z", "2026-10-25T23:15:00Z",
        100.0, 1000.0, "u1", "d1", 0.07, 1.0, False, 60, "",
    )
    m5_empty = TwapCandleMarketSpec(
        "ETH", "5m", "2", "0x2", "ETH 5m", "2026-10-25T23:10:00Z", "2026-10-25T23:15:00Z",
        700.0, 1000.0, "u2", "d2", 0.07, 1.0, False, 60, "",
    )
    assert verify_same_oracle_pair(m15_empty, m5_empty) is False

    # 6. H-04: `fetch_binance_window_extremes_sync` stitches initial partial-hour `1m` klines
    st_mid_hr = 1792931400.0  # 12:30:00 UTC (mid-hour!)
    en_48h = st_mid_hr + 48 * 3600.0

    def fake_klines(sym: str, st_ms: int, en_ms: int, interval: str, timeout: float):
        if interval == "1m" and st_ms == int(st_mid_hr * 1000):
            # Wick to 89,500 at 12:40 UTC during initial partial hour!
            return [[st_ms, "84000", "89500", "83900", "84100", "10", st_ms + 60_000]]
        return [[int((st_mid_hr + 3600) * 1000), "84100", "85000", "83500", "84200", "100", int(en_48h * 1000)]]

    monkeypatch.setattr(b_eng, "_fetch_finalized_klines", fake_klines)
    ext_res = b_eng.fetch_binance_window_extremes_sync("BTC", st_mid_hr, en_48h, "1m")
    assert ext_res is not None and ext_res[0] == 89500.0

    # 7. C-02 / F-10 / F-03 / M-04 / F-19: Concurrency race, cancel-window adverse fill, corrupt JSONL skip
    state_p = tmp_path / "a124_race_state.json"
    ledger_p = tmp_path / "a124_race_ledger.jsonl"
    opps_p = tmp_path / "a124_race_opps.json"
    # Pre-seed ledger with a truncated/corrupt line + a valid open entry (`F-19`)
    ledger_p.write_text(
        '{"event": "SHADOW_ENTRY", "corrupt_json": \n'
        + json.dumps({
            "event": "SHADOW_ENTRY",
            "position_id": "S2_VALID_HYDRATE",
            "dedupe_key": "S2_BTC_5m_1",
            "sleeve": "S2_EXACT_TWAP_LOCK",
            "asset_or_city": "BTC",
            "title": "BTC 5m",
            "side": "UP",
            "token_id": "tok_h",
            "fee_rate": 0.07,
            "entry_ts": 1000.0,
            "close_ts": 2000.0,
            "tier_fills": {"T1000": {"spent_usd": 100.0, "fee_usd": 0.5, "shares": 115.0}},
            "extra": {},
            "status": "OPEN",
        })
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(a124, "STATE_FILE", state_p)
    monkeypatch.setattr(a124, "LEDGER_FILE", ledger_p)
    monkeypatch.setattr(a124, "OPPS_FILE", opps_p)

    async def _sim_concurrency_and_adverse_fill() -> None:
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        assert "S2_VALID_HYDRATE" in d.open_positions

        books = {
            "tok_race": {"bids": [{"price": "0.84", "size": "300"}], "asks": [{"price": "0.85", "size": "300"}]},
            "tok_adv": {"bids": [{"price": "0.49", "size": "200"}], "asks": [{"price": "0.51", "size": "200"}]},
        }

        async def fake_fetch(url: str, timeout: float = 5.0):
            await asyncio.sleep(0.01)
            for tid, bk in books.items():
                if f"token_id={tid}" in url:
                    return bk
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch)
        # Concurrent duplicate calls with identical dedupe_key must open strictly 1 position (`C-02` / `F-10`)
        r1, r2 = await asyncio.gather(
            d.open_shadow_position(
                "W1_SOLAR_PEAK_LOCK", "W1_RACE_KEY", "Tokyo_RJTT", "Tokyo 20°C",
                "YES", "tok_race", 0.0, 0.94, time.time() + 7200.0, {"event_id": "ev_r"},
            ),
            d.open_shadow_position(
                "W1_SOLAR_PEAK_LOCK", "W1_RACE_KEY", "Tokyo_RJTT", "Tokyo 20°C",
                "YES", "tok_race", 0.0, 0.94, time.time() + 7200.0, {"event_id": "ev_r"},
            ),
        )
        assert (r1, r2) in ((True, False), (False, True))
        assert sum(1 for p in d.open_positions.values() if p.get("dedupe_key") == "W1_RACE_KEY") == 1

        # Cancel-latency adverse fill (`F-03` / `M-04`): spot crashes -40 bps AND fast taker already swept ask to 0.49 <= 0.50
        d.spots["BTC"] = 84000.0
        ok_m = await d.post_shadow_maker_entry(
            "M1_SVI_MAKER_SCALP", "M1_ADV_RACE", "BTC", "BTC > 84k", "YES",
            "tok_adv", 0.58, time.time() + 43200.0, {"market_id": "m_adv", "strike": 84000.0, "is_downward": False},
        )
        assert ok_m is True
        oid_adv = next(iter(d.pending_maker_orders))
        d.pending_maker_orders[oid_adv]["created_ts"] -= 2.0  # Rested 2s >= 0.35s
        d.spots["BTC"] = 83650.0  # -41.7 bps adverse shock!
        books["tok_adv"] = {"bids": [{"price": "0.48", "size": "200"}], "asks": [{"price": "0.49", "size": "250"}]}
        monkeypatch.setattr(
            a124,
            "evaluate_svi_digital_fair_value",
            lambda *a, **kw: {"p_yes": 0.36, "p_no": 0.64, "iv_annual": 0.45, "z_sigma": 0.9, "source": "TEST"},
        )
        await d.manage_pending_maker_orders()
        adv_pos = [p for p in d.open_positions.values() if p.get("dedupe_key") == "M1_ADV_RACE"]
        assert len(adv_pos) == 1 and adv_pos[0]["extra"].get("adverse_fill_during_cancel_window") is True

    asyncio.run(_sim_concurrency_and_adverse_fill())


def test_v40_profit_maximization_upgrades(tmp_path: Path, monkeypatch) -> None:
    """
    Comprehensive v4.0 test suite verifying all 20 profit-maximization upgrades:
      - ChatGPT #9: Explicit missing-feature hygiene on real 20+-digit CTF tokens (zero optimistic defaults)
      - ChatGPT #1: Calibrated event-time quote-survival & net-alpha scorer + ledger calibration
      - ChatGPT #2 + Gemini #9: Adaptive Maker/Taker/Skip router + 3.5s reactive `post_only` M4 maker quote
      - ChatGPT #3 + Gemini #6 + Gemini #13: Optimal-stopping `$0.985-$0.99` pre-expiry cash recycling,
        complementary opposite-outcome merge dominance, and OBI maker step-down
      - ChatGPT #4: `C1_BINARY_COMPLETE_SET` same-market binary `YES+NO <= $0.994` scanner & shadow execution
      - ChatGPT #6: Probabilistic cross-oracle basis box expectancy (`PROBABILISTIC_CROSS_ORACLE_RV`)
      - Gemini #15 + ChatGPT #10: `/dev/shm/pm_global_positions.json` bus + capital-efficiency auction (`EV/($*hr)`)
      - Gemini #14 + ChatGPT #8: Deribit SVI `index_price` carry drift + PAVA monotone strike-ladder projection
      - ChatGPT #7: `first_passage_touch_prob` forward drift & `realized_vol_ratio` regime-switching jump weight + `evaluate_barrier_no_net_ev`
      - Gemini #11 + Gemini #10 + ChatGPT #5: 10s station-release METAR TTL, TAF `TX`/`TN` parser, and `W3_WEATHER_SLATE_ARB`
      - Gemini #8: `M3_LADDER_MONO_BOX` cross-strike monotonicity box execution & settlement
    """
    import asyncio
    import time
    from datetime import date
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.net_alpha_opportunity_engine import (
        estimate_quote_survival_and_net_alpha,
        evaluate_cross_oracle_basis_box_ev,
        evaluate_optimal_stopping_exit,
        fit_quote_survival_from_ledger,
        inspect_microstructure_feature_completeness,
        publish_global_positions_shm,
        rank_opportunities_capital_auction,
        read_global_positions_shm,
        scan_binary_complete_set_arb,
        select_maker_taker_skip_route,
    )
    from src.polymarket_research.deribit_svi_surface import (
        DeribitSVISurfaceEngine,
        SVIParams,
        enforce_monotone_ladder_probabilities,
    )
    from src.polymarket_research.multistrike_svi_scalper import (
        StrikeRungSpec,
        evaluate_coherent_strike_ladder,
    )
    from src.polymarket_research.barrier_onetouch_svi_engine import (
        evaluate_barrier_no_net_ev,
        first_passage_touch_prob,
    )
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        compute_adaptive_metar_poll_ttl,
        evaluate_weather_event_slate,
        parse_taf_temperature_extremes,
        verify_weather_slate_partition,
    )

    real_ctf_tok = "100434764618174237135201777197981253576172734064131101154122934005557319214073"

    # 1. Explicit missing-feature hygiene (ChatGPT #9)
    inc_age = inspect_microstructure_feature_completeness(
        {"fee_metadata": {"fee_rate_market": 0.07}, "shock_ofi": 0.9, "pre_shock_features_t0": {"UP": {"token_id": real_ctf_tok, "age_ask_ms": None, "obi_l1": 0.2}}},
        "UP",
        real_ctf_tok,
    )
    assert inc_age["hard_veto_live"] is True and "age_ask_ms" in inc_age["missing_fields"]
    inc_ofi = inspect_microstructure_feature_completeness(
        {"fee_metadata": {"fee_rate_market": 0.07}, "shock_ofi": None, "pre_shock_features_t0": {"UP": {"token_id": real_ctf_tok, "age_ask_ms": 180.0, "obi_l1": 0.2}}},
        "UP",
        real_ctf_tok,
    )
    assert inc_ofi["hard_veto_live"] is True and "shock_ofi" in inc_ofi["missing_fields"]

    # 2. Event-time quote-survival & +2c price-improved FAK net alpha (ChatGPT #1)
    surv_base = estimate_quote_survival_and_net_alpha(
        p_win=0.90, ask_price=0.74, limit_price=0.74, p_max=0.80, clob_rtt_ms=260.0, age_ask_ms=280.0
    )
    surv_impr = estimate_quote_survival_and_net_alpha(
        p_win=0.90, ask_price=0.74, limit_price=0.76, p_max=0.80, clob_rtt_ms=260.0, age_ask_ms=280.0
    )
    assert surv_impr["p_fill"] > surv_base["p_fill"]
    assert surv_impr["eff_limit_px"] == 0.76 <= 0.80
    assert surv_impr["eligible"] is True and surv_impr["ev_net_usd"] > 0.0

    cal = fit_quote_survival_from_ledger(
        [
            {"mode": "LIVE_CLOB", "success": True, "latency_ms": 210.0},
            {"mode": "LIVE_CLOB", "success": True, "latency_ms": 225.0},
            {"mode": "FAK_KILLED_NO_MATCH", "success": False, "latency_ms": 280.0},
            {"mode": "LIVE_CLOB", "success": True, "latency_ms": 195.0},
            {"mode": "FAK_KILLED_NO_MATCH", "success": False, "latency_ms": 265.0},
        ]
    )
    assert cal["sample_count"] == 5 and abs(cal["empirical_fill_rate"] - 0.6) < 1e-6

    # 3. Maker / Taker / Skip Router (ChatGPT #2 + Gemini #9)
    r_taker = select_maker_taker_skip_route(p_win=0.92, best_bid=0.73, best_ask=0.74, p_max=0.81, clob_rtt_ms=190.0)
    assert r_taker["route"] == "TAKER_PRICE_IMPROVED_FAK" and r_taker["taker_limit_px"] == 0.76
    r_maker = select_maker_taker_skip_route(p_win=0.77, best_bid=0.69, best_ask=0.75, p_max=0.74, clob_rtt_ms=280.0)
    assert r_maker["route"] == "MAKER_POST_ONLY_3P5S" and r_maker["maker_bid_px"] == 0.70
    r_skip = select_maker_taker_skip_route(p_win=0.60, best_bid=0.68, best_ask=0.70, p_max=0.58)
    assert r_skip["route"] == "SKIP"

    # 4. Optimal-stopping exit controller: $0.99 recycle, complement merge, and OBI step-down (ChatGPT #3 + Gemini #6/#13)
    ex_rec = evaluate_optimal_stopping_exit(
        entry_px=0.74, rem_shares=18.0, best_bid=0.99, best_ask=1.00, curr_target_px=0.99, tte_sec=15.0
    )
    assert ex_rec["action"] == "PRE_EXPIRY_99C_RECYCLE" and ex_rec["taker_fee_ps"] < 0.001

    ex_comp = evaluate_optimal_stopping_exit(
        entry_px=0.70, rem_shares=18.0, best_bid=0.84, best_ask=0.93, curr_target_px=0.95, tte_sec=30.0, opp_ask_complement=0.09
    )
    assert ex_comp["action"] == "SYNTHETIC_COMPLEMENT_MERGE" and ex_comp["net_proceeds_ps"] > 0.90

    ex_obi = evaluate_optimal_stopping_exit(
        entry_px=0.74, rem_shares=18.0, best_bid=0.92, best_ask=0.95, curr_target_px=0.95, tte_sec=90.0, obi_l1=-0.65, v_spot_15s_pct=-0.02
    )
    assert ex_obi["action"] == "OBI_MAKER_STEP_DOWN" and ex_obi["target_px"] == 0.93

    # 5. Same-market binary complete-set scanner (`C1`) & Cross-oracle probabilistic basis EV (ChatGPT #4 & #6)
    c1 = scan_binary_complete_set_arb(
        market_id="m_c1",
        condition_id="0xc1",
        yes_token="tok_y_c1",
        no_token="tok_n_c1",
        asks_yes_raw=[{"price": "0.47", "size": "60"}],
        asks_no_raw=[{"price": "0.48", "size": "60"}],
        target_budget_usd=30.0,
        fee_rate=0.07,
        max_complete_set_cost=0.994,
    )
    assert c1["filled"] is True and c1["box_cost_net"] < 0.994 and c1["guaranteed_min_profit_usd"] > 0.0

    basis_ev = evaluate_cross_oracle_basis_box_ev(
        spot_px=84100.0, k_low=84000.0, k_high=84200.0, c_taker_net=0.975, tte_sec=600.0
    )
    assert basis_ev["classification"] == "PROBABILISTIC_CROSS_ORACLE_RV" and basis_ev["is_riskless"] is False

    # 6. Cross-daemon `/dev/shm` position bus & Capital-efficiency opportunity auction (Gemini #15 + ChatGPT #10)
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    now_bus = time.time()
    assert publish_global_positions_shm(
        "live_harvester",
        [{"trade_id": "T1", "sleeve": "LIVE", "asset": "BTC", "target_token": "UP", "candle_open_spot": 84000.0, "candle_expiry_ts": now_bus + 600.0, "notional_usd": 14.0}],
    ) is True
    bus_state = read_global_positions_shm()
    glob_pos = bus_state["daemons"]["live_harvester"]["positions"]
    assert len(glob_pos) == 1 and glob_pos[0]["asset"] == "BTC"

    ranked = rank_opportunities_capital_auction(
        [
            {"sleeve": "W2", "asset": "NYC", "side": "YES", "ask_vwap": 0.50, "net_edge": 0.05, "tte_sec": 36000.0, "expiry_ts": now_bus + 36000.0},
            {"sleeve": "S2", "asset": "BTC", "side": "DOWN", "strike": 84250.0, "ask_vwap": 0.85, "net_edge": 0.04, "tte_sec": 300.0, "expiry_ts": now_bus + 600.0},
        ],
        active_global_positions=glob_pos,
    )
    assert ranked[0]["sleeve"] == "S2" and ranked[0].get("synthetic_corridor_completion") is True

    # 7. Deribit SVI carry drift + PAVA monotone ladder projection + Barrier jump/EV gate (Gemini #14 + ChatGPT #7/#8)
    eng = DeribitSVISurfaceEngine()
    eng._cache["BTC"] = SVIParams(
        a=0.0004, b=0.0002, rho=-0.15, m=0.0, sigma=0.05,
        t_years=30.0 / 365.25, forward_price=86000.0, index_price=84000.0, calibrated_at=time.time(),
    )
    assert eng._cache["BTC"].implied_forward_drift_rate() > 0.15
    p_carry = eng.evaluate_strike_probability("BTC", spot=84000.0, strike=85000.0, tte_seconds=14 * 86400.0, allow_sync_fetch=False)
    eng._cache["BTC"].index_price = 86000.0  # zero carry basis
    p_flat = eng.evaluate_strike_probability("BTC", spot=84000.0, strike=85000.0, tte_seconds=14 * 86400.0, allow_sync_fetch=False)
    assert p_carry["p_above_strike"] > p_flat["p_above_strike"]

    mono = enforce_monotone_ladder_probabilities([(80000.0, 0.72), (82000.0, 0.55), (84000.0, 0.61), (86000.0, 0.30)])
    assert mono["probs"] == sorted(mono["probs"], reverse=True)
    assert all(iv >= 0.0 for iv in mono["interval_probs"]) and mono["max_adjustment"] > 0.0

    rungs_test = [
        StrikeRungSpec("ev1", "btc-daily", "BTC", "BTC Daily", f"m_{k}", f"0x{k}", f"BTC > {k}", float(k), False, now_bus + 7200.0, f"ty_{k}", f"tn_{k}")
        for k in (82000, 84000, 86000)
    ]
    coh = evaluate_coherent_strike_ladder("BTC", 84000.0, rungs_test, 7200.0, now_ts=now_bus)
    assert coh["probs"][0] >= coh["probs"][1] >= coh["probs"][2]

    pt_calm = first_passage_touch_prob(84000.0, 88000.0, 86400.0, 0.50, "UP", realized_vol_ratio=1.0, forward_drift_annual=0.0)
    pt_stress = first_passage_touch_prob(84000.0, 88000.0, 86400.0, 0.50, "UP", realized_vol_ratio=2.2, forward_drift_annual=0.12)
    assert pt_stress > pt_calm
    assert evaluate_barrier_no_net_ev(p_touch=0.04, ask_no=0.88)["eligible"] is True
    assert evaluate_barrier_no_net_ev(p_touch=0.01, ask_no=0.95)["eligible"] is False  # 19x loss/gain asymmetry vetoed!

    # 8. Weather 10s release-window TTL, TAF `TX`/`TN` parser, and `W3_WEATHER_SLATE_ARB` (Gemini #10/#11 + ChatGPT #5)
    assert compute_adaptive_metar_poll_ttl("KLGA", None, datetime(2026, 10, 26, 14, 52, tzinfo=timezone.utc)) == 10.0
    assert compute_adaptive_metar_poll_ttl("KLGA", None, datetime(2026, 10, 26, 14, 25, tzinfo=timezone.utc)) == 300.0

    taf_parsed = parse_taf_temperature_extremes(
        "TAF KLGA 261130Z 2612/2718 30012KT P6SM FEW050 TX19/2619Z TNM02/2710Z",
        "KLGA",
        datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
        "America/New_York",
    )
    assert taf_parsed[date(2026, 10, 26)]["HIGH"] == 19.0
    assert taf_parsed[date(2026, 10, 27)]["LOW"] == -2.0

    w_spec = WeatherEventSpec(
        event_id="ev_w3",
        slug="tokyo-w3",
        series_slug="tokyo-daily-weather",
        title="Highest temperature in Tokyo on October 26?",
        icao="RJTT",
        city="Tokyo",
        lat=35.5494,
        lon=139.7798,
        tz_name="Asia/Tokyo",
        obs_date=date(2026, 10, 26),
        metric="HIGH",
        unit="C",
        fee_type="zero_fees",
        end_date_iso="2026-10-26T20:00:00Z",
        buckets=[
            WeatherBucket("wb1", "0xwb1", "18°C or below", "18°C or below", "wy1", "wn1", "C", float("-inf"), 18.0),
            WeatherBucket("wb2", "0xwb2", "19°C", "19°C", "wy2", "wn2", "C", 19.0, 19.0),
            WeatherBucket("wb3", "0xwb3", "20°C or higher", "20°C or higher", "wy3", "wn3", "C", 20.0, float("inf")),
        ],
    )
    assert verify_weather_slate_partition(w_spec) is True
    slate_eval = evaluate_weather_event_slate(
        w_spec,
        [0.20, 0.50, 0.30],
        {
            "wb1": {"ask_yes": 0.19, "ask_yes_shares": 40.0},
            "wb2": {"ask_yes": 0.46, "ask_yes_shares": 40.0},
            "wb3": {"ask_yes": 0.31, "ask_yes_shares": 40.0},
        },
        target_budget_usd=10.0,
    )
    assert slate_eval["full_slate_arb"] is not None
    assert abs(slate_eval["full_slate_arb"]["sum_asks"] - 0.96) < 1e-6

    # 9. Shadow daemon end-to-end execution & settlement for `M3`, `C1`, `W3`, and `M4` 3.5s Maker
    async def _sim_v40_sleeves() -> None:
        monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "a124_v40_state.json")
        monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "a124_v40_ledger.jsonl")
        monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "a124_v40_opps.json")
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        d.spots["BTC"] = 84500.0

        books_v40 = {
            "tok_c1_y": {"bids": [{"price": "0.46", "size": "80"}], "asks": [{"price": "0.47", "size": "80"}]},
            "tok_c1_n": {"bids": [{"price": "0.47", "size": "80"}], "asks": [{"price": "0.48", "size": "80"}]},
            "tok_m3_lo": {"bids": [{"price": "0.52", "size": "80"}], "asks": [{"price": "0.53", "size": "80"}]},
            "tok_m3_hi": {"bids": [{"price": "0.41", "size": "80"}], "asks": [{"price": "0.42", "size": "80"}]},
            "tok_m4_mkr": {"bids": [{"price": "0.50", "size": "60"}], "asks": [{"price": "0.54", "size": "60"}]},
        }

        async def fake_fetch_v40(url: str, timeout: float = 5.0):
            if "/book?token_id=" in url:
                return books_v40.get(url.split("token_id=")[1])
            if "/markets/m_c1" in url:
                return {"closed": True, "outcomePrices": '["1", "0"]'}
            if "/markets/m_lo" in url:
                return {"closed": True, "outcomePrices": '["1", "0"]'}
            if "/markets/m_hi" in url:
                return {"closed": True, "outcomePrices": '["0", "1"]'}  # Lands inside corridor -> $2.00 DOUBLE WIN!
            if "/markets/wb2" in url:
                return {"closed": True, "outcomePrices": '["1", "0"]'}
            if "/markets/wb1" in url or "/markets/wb3" in url:
                return {"closed": True, "outcomePrices": '["0", "1"]'}
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch_v40)

        # Open C1 complete set, M3 ladder monotonicity box, and W3 weather full-slate arb
        ok_c1 = await d.open_shadow_two_leg_box(
            sleeve="C1_BINARY_COMPLETE_SET",
            dedupe_key="C1_TEST_1",
            asset="BTC",
            title="BTC > 84k [YES+NO Complete Set]",
            leg_a={"token_id": "tok_c1_y", "side": "YES", "market_id": "m_c1", "fee_rate": 0.07},
            leg_b={"token_id": "tok_c1_n", "side": "NO", "market_id": "m_c1", "fee_rate": 0.07},
            bk_a=books_v40["tok_c1_y"],
            bk_b=books_v40["tok_c1_n"],
            close_ts=time.time() - 60.0,
            max_box_cost_net=0.994,
            extra={"market_id": "m_c1"},
        )
        ok_m3 = await d.open_shadow_two_leg_box(
            sleeve="M3_LADDER_MONO_BOX",
            dedupe_key="M3_TEST_1",
            asset="BTC",
            title="BTC Ladder Box [84000..85000]",
            leg_a={"token_id": "tok_m3_lo", "side": "YES", "market_id": "m_lo", "fee_rate": 0.07},
            leg_b={"token_id": "tok_m3_hi", "side": "NO", "market_id": "m_hi", "fee_rate": 0.07},
            bk_a=books_v40["tok_m3_lo"],
            bk_b=books_v40["tok_m3_hi"],
            close_ts=time.time() - 60.0,
            max_box_cost_net=0.995,
            extra={"low_market_id": "m_lo", "high_market_id": "m_hi", "low_strike": 84000.0, "high_strike": 85000.0},
        )
        ok_w3 = await d.open_shadow_weather_slate(w_spec, slate_eval["full_slate_arb"], close_ts=time.time() - 60.0)
        assert ok_c1 is True and ok_m3 is True and ok_w3 is True

        # Settle all 3 riskless box/slate positions!
        await d.manage_open_positions()
        by_slv = {p["sleeve"]: p for p in d.closed_positions}
        assert by_slv["C1_BINARY_COMPLETE_SET"]["won"] is True and by_slv["C1_BINARY_COMPLETE_SET"]["tier_pnls_usd"]["T1000"] > 0.0
        assert by_slv["M3_LADDER_MONO_BOX"]["won"] is True and by_slv["M3_LADDER_MONO_BOX"]["status"] == "SETTLED_DOMINANCE_DOUBLE_2X"
        assert by_slv["W3_WEATHER_SLATE_ARB"]["won"] is True and by_slv["W3_WEATHER_SLATE_ARB"]["tier_pnls_usd"]["T1000"] > 0.0

        # Verify 3.5s reactive M4 post_only Maker quote fills passively at 1.0s and auto-cancels after 3.5s
        ok_m4m = await d.post_shadow_maker_entry(
            sleeve="M4_SHOCK_STRIKE_CATCHUP",
            dedupe_key="M4MKR_TEST",
            asset="BTC",
            title="BTC > 84500",
            side_label="YES",
            token_id="tok_m4_mkr",
            p_model=0.62,
            close_ts=time.time() + 7200.0,
            extra={"market_id": "m_m4", "strike": 84500.0, "is_downward": False},
            prefetched_book=books_v40["tok_m4_mkr"],
            ttl_override_sec=3.5,
        )
        assert ok_m4m is True
        oid_m4 = next(iter(d.pending_maker_orders))
        d.pending_maker_orders[oid_m4]["created_ts"] -= 1.2  # 1.2s >= 0.5s min_rest_sec and < 3.5s TTL
        books_v40["tok_m4_mkr"] = {"bids": [{"price": "0.50", "size": "60"}], "asks": [{"price": "0.51", "size": "80"}]}
        monkeypatch.setattr(
            a124,
            "evaluate_svi_digital_fair_value",
            lambda *a, **kw: {"p_yes": 0.62, "p_no": 0.38, "iv_annual": 0.45, "z_sigma": 0.5, "source": "TEST"},
        )
        await d.manage_pending_maker_orders()
        assert any(p["sleeve"] == "M4_SHOCK_STRIKE_CATCHUP" for p in d.open_positions.values())
        d.write_state_files([{"sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX", "ask_vwap": 0.98, "net_edge": 0.02, "tte_sec": 180.0}])
        assert "alpha124_shadow" in read_global_positions_shm()["daemons"]

    asyncio.run(_sim_v40_sleeves())


def test_v42_seven_new_shadow_additions_and_quarantine(tmp_path, monkeypatch):
    """
    Verifies all 7 new Shadow Trading Additions + Production Quarantine (`PM_QUARANTINE_LOSING_SLEEVES=1`):
      1. `D1_4H_DOMINANCE_BOX`: 4h (`variant=fourhour`) vs 15m/5m Same-Oracle Chainlink 60s-TWAP Boxes.
      2. `D1_QUIET_BOOK_BOX`: Quiet-book spread/impulse filter blocking toxic sweeps while passing calm books.
      3. `S5M_CHAINLINK_SNIPER`: Standalone 5m BTC & ETH directional sniper (`$0.96` Maker TP + `fiveminute` fallback).
      4. `N1_NEGRISK_CROSS_BOX`: NegRisk bracket (`72,000-74,000`) vs Multi-Strike (`Above $72k/$74k`) 2-leg & 3-leg boxes.
      5. `P1_PREOPEN_MAKER_STRADDLE`: Pre-open `$0.48 + $0.48 = $0.96` Maker pair (both 2-leg lock AND 1-leg scratch!).
      6. `U1_DAILY_UPDOWN_LOCK`: Daily BTC/ETH Up-or-Down final-90m convergence lock.
      7. `HIGH_VOLUME_WEATHER_SERIES`: Chengdu (`ZUUU`), Beijing (`ZBAA`), Seoul (`RKSI`) 0%-fee Asian METAR mapping.
      8. Production Quarantine (`PM_QUARANTINE_LOSING_SLEEVES=1`) blocks `M4`, `W2`, `W2_MAKER`, `M1`, `M2`.
    """
    import asyncio
    import time
    from src.polymarket_research import alpha_124_shadow_daemon as a124
    from src.polymarket_research.multistrike_svi_scalper import (
        build_negrisk_cross_box_bundles,
        parse_daily_updown_event,
        parse_multistrike_event,
        parse_negrisk_bracket_event,
    )
    from src.polymarket_research.same_oracle_dominance_box import (
        build_crypto_price_query_url,
        determine_dominance_legs,
        parse_twap_candle_event,
        verify_same_oracle_pair,
        walk_equal_shares_multi_leg_box,
    )
    from src.polymarket_research.weather_metar_engine import HIGH_VOLUME_WEATHER_SERIES, parse_weather_event

    # 1. Verify Production Quarantine blocks all 6 retired negative-EV sleeves (including P1_PREOPEN_MAKER_STRADDLE)
    monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES", "1")
    for sl_q in (
        "M4_SHOCK_STRIKE_CATCHUP",
        "W2_ENSEMBLE_VALUE",
        "W2_MAKER_OVERROUND",
        "M1_SVI_MAKER_SCALP",
        "M2_STRIKE_CONVERGENCE",
        "P1_PREOPEN_MAKER_STRADDLE",
    ):
        assert a124.is_shadow_sleeve_quarantined(sl_q) is True
    for sl_ok in (
        "W1_SOLAR_PEAK_LOCK",
        "D1_4H_DOMINANCE_BOX",
        "D1_QUIET_BOOK_BOX",
        "S5M_CHAINLINK_SNIPER",
        "N1_NEGRISK_CROSS_BOX",
        "U1_DAILY_UPDOWN_LOCK",
    ):
        assert a124.is_shadow_sleeve_quarantined(sl_ok) is False

    # 2. Verify Asian Daily Weather (`ZUUU`, `ZBAA`, `RKSI`) 0%-fee METAR parsing
    assert {"chengdu-daily-weather", "beijing-daily-weather", "seoul-daily-weather"} <= set(HIGH_VOLUME_WEATHER_SERIES)
    zuuu_desc = (
        "This market will resolve to the highest temperature recorded at Chengdu Shuangliu International Airport "
        "according to https://aviationweather.gov/api/data/metar?ids=ZUUU on 27 Oct '26 (SPECI reports excluded)."
    )
    ev_zuuu = {
        "id": "ev_chengdu",
        "title": "Highest temperature in Chengdu on October 27?",
        "seriesSlug": "chengdu-daily-weather",
        "description": zuuu_desc,
        "markets": [
            {"id": "m_zuuu_1", "conditionId": "0xc1", "groupItemTitle": "19°C or below", "question": "19°C or below?", "description": zuuu_desc, "endDate": "2026-10-27T16:00:00Z", "clobTokenIds": '["tok_z1_y", "tok_z1_n"]'},
            {"id": "m_zuuu_2", "conditionId": "0xc2", "groupItemTitle": "20°C", "question": "20°C?", "description": zuuu_desc, "endDate": "2026-10-27T16:00:00Z", "clobTokenIds": '["tok_z2_y", "tok_z2_n"]'},
            {"id": "m_zuuu_3", "conditionId": "0xc3", "groupItemTitle": "21°C", "question": "21°C?", "description": zuuu_desc, "endDate": "2026-10-27T16:00:00Z", "clobTokenIds": '["tok_z3_y", "tok_z3_n"]'},
            {"id": "m_zuuu_4", "conditionId": "0xc4", "groupItemTitle": "22°C or higher", "question": "22°C or higher?", "description": zuuu_desc, "endDate": "2026-10-27T16:00:00Z", "clobTokenIds": '["tok_z4_y", "tok_z4_n"]'},
        ],
    }
    w_zuuu = parse_weather_event(ev_zuuu, series_slug_hint="chengdu-daily-weather")
    assert w_zuuu is not None and w_zuuu.icao == "ZUUU" and w_zuuu.unit == "C"

    # 3. Verify 4h (`variant=fourhour`) vs 15m Same-Oracle Dominance Box math & URL
    ev_4h = {
        "id": "ev_btc_4h",
        "title": "Bitcoin Up or Down - Oct 26, 8:00AM-12:00PM ET",
        "endDate": "2026-10-26T16:00:00Z",
        "markets": [
            {
                "id": "m_btc_4h",
                "conditionId": "0x4h",
                "eventStartTime": "2026-10-26T12:00:00Z",
                "endDate": "2026-10-26T16:00:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["tok_4h_up", "tok_4h_dn"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.072, "exponent": 1},
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "resolutionSource": "https://data.chain.link/streams/btc-usd",
            }
        ],
    }
    ev_15m = {
        "id": "ev_btc_15m",
        "title": "Bitcoin Up or Down - Oct 26, 11:45AM-12:00PM ET",
        "endDate": "2026-10-26T16:00:00Z",
        "markets": [
            {
                "id": "m_btc_15m",
                "conditionId": "0x15m",
                "eventStartTime": "2026-10-26T15:45:00Z",
                "endDate": "2026-10-26T16:00:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["tok_15m_up", "tok_15m_dn"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.072, "exponent": 1},
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "resolutionSource": "https://data.chain.link/streams/btc-usd",
            }
        ],
    }
    sp_4h = parse_twap_candle_event(ev_4h, "BTC", "4h")
    sp_15m = parse_twap_candle_event(ev_15m, "BTC", "15m")
    assert sp_4h is not None and sp_15m is not None
    u_4h = build_crypto_price_query_url(sp_4h)
    assert "variant=fourhour" in u_4h and "twapEnabled=true&twapLookbackSeconds=60" in u_4h
    assert verify_same_oracle_pair(sp_4h, sp_15m) is True
    dom_4h = determine_dominance_legs(sp_4h, 80000.0, sp_15m, 80500.0)
    assert dom_4h is not None and dom_4h["regime"] == "4H_UP_PLUS_15M_DOWN"

    # 4. Verify NegRisk Bracket (`bitcoin-neg-risk-weekly`) vs Multi-Strike (`btc-multi-strikes-weekly`) 2-leg & 3-leg bundles
    ev_ms = {
        "id": "ev_ms",
        "title": "Bitcoin above ___ on Oct 26?",
        "endDate": "2026-10-26T16:00:00Z",
        "markets": [
            {"id": "ms_72", "conditionId": "0xms72", "question": "Will the price of Bitcoin be above $72,000 on Oct 26?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["ms72_y", "ms72_n"]'},
            {"id": "ms_74", "conditionId": "0xms74", "question": "Will the price of Bitcoin be above $74,000 on Oct 26?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["ms74_y", "ms74_n"]'},
        ],
    }
    ev_nr = {
        "id": "ev_nr",
        "title": "Bitcoin price on Oct 26?",
        "endDate": "2026-10-26T16:00:00Z",
        "markets": [
            {"id": "nr_lt72", "conditionId": "0xnr1", "groupItemTitle": "<72,000", "question": "Will BTC be less than $72,000?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["nr_lt72_y", "nr_lt72_n"]'},
            {"id": "nr_72_74", "conditionId": "0xnr2", "groupItemTitle": "72,000-74,000", "question": "Will BTC be between $72,000 and $74,000?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["nr_7274_y", "nr_7274_n"]'},
            {"id": "nr_gt74", "conditionId": "0xnr3", "groupItemTitle": ">74,000", "question": "Will BTC be greater than $74,000?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["nr_gt74_y", "nr_gt74_n"]'},
        ],
    }
    ms_rungs = parse_multistrike_event(ev_ms, "BTC", "btc-multi-strikes-weekly")
    nr_brackets = parse_negrisk_bracket_event(ev_nr, "BTC", "bitcoin-neg-risk-weekly")
    bundles = build_negrisk_cross_box_bundles(ms_rungs, nr_brackets)
    # 2 lower tail + 2 interior (partition $1 + complement $2) + 2 upper tail = 6 deterministic bundles!
    assert len(bundles) == 6
    part_b = [b for b in bundles if b["guaranteed_payout"] == 1.0 and len(b["legs"]) == 3][0]
    w_3leg = walk_equal_shares_multi_leg_box(
        [
            {"asks": [{"price": "0.28", "size": "80"}], "fee_rate": 0.07, "fee_exponent": 1.0},
            {"asks": [{"price": "0.30", "size": "80"}], "fee_rate": 0.07, "fee_exponent": 1.0},
            {"asks": [{"price": "0.31", "size": "80"}], "fee_rate": 0.07, "fee_exponent": 1.0},
        ],
        target_budget_usd=100.0,
        guaranteed_payout_per_bundle=part_b["guaranteed_payout"],
        max_bundle_cost_net=0.992,
    )
    assert w_3leg["filled"] is True and w_3leg["guaranteed_min_profit_usd"] > 3.0

    # 5. Verify Daily Up-or-Down parser (`U1_DAILY_UPDOWN_LOCK`)
    ev_u1 = {
        "id": "ev_u1",
        "title": "Bitcoin Up or Down on October 27?",
        "endDate": "2026-10-27T16:00:00Z",
        "markets": [
            {
                "id": "m_u1",
                "conditionId": "0xu1",
                "eventStartTime": "2026-10-26T16:00:00Z",
                "endDate": "2026-10-27T16:00:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["u1_up", "u1_dn"]',
            }
        ],
    }
    sp_u1 = parse_daily_updown_event(ev_u1, "BTC", "btc-up-or-down-daily")
    assert sp_u1 is not None and sp_u1.up_token == "u1_up" and sp_u1.down_token == "u1_dn"

    # 6. End-to-end async simulation of P1 Pre-Open Maker Straddle (both 2-leg lock & 1-leg scratch!) + S5M Sniper
    async def _sim_new_sleeves() -> None:
        monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "a124_v42_state.json")
        monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "a124_v42_ledger.jsonl")
        monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "a124_v42_opps.json")
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_t = 1793026680.0  # 120s before next 15m boundary 1793026800.0!
        d.spots["BTC"] = 84000.0
        d.spots["ETH"] = 2500.0

        sp_pre_btc = a124.TwapCandleMarketSpec(
            asset="BTC", horizon="15m", market_id="m_pre_btc", condition_id="0xpreb",
            title="BTC PreOpen 15m", start_iso="2026-10-26T15:00:00Z", end_iso="2026-10-26T15:15:00Z",
            start_ts=1793026800.0, end_ts=1793027700.0,
            up_token="p1_btc_up", down_token="p1_btc_dn", fee_rate=0.072, fee_exponent=1.0, neg_risk=False,
            twap_lookback_sec=60, resolution_source="https://data.chain.link/streams/btc-usd",
        )
        sp_pre_eth = a124.TwapCandleMarketSpec(
            asset="ETH", horizon="15m", market_id="m_pre_eth", condition_id="0xpree",
            title="ETH PreOpen 15m", start_iso="2026-10-26T15:00:00Z", end_iso="2026-10-26T15:15:00Z",
            start_ts=1793026800.0, end_ts=1793027700.0,
            up_token="p1_eth_up", down_token="p1_eth_dn", fee_rate=0.072, fee_exponent=1.0, neg_risk=False,
            twap_lookback_sec=60, resolution_source="https://data.chain.link/streams/eth-usd",
        )
        d.preopen_15m_candles = {"BTC_pre15m_1793026800": sp_pre_btc, "ETH_pre15m_1793026800": sp_pre_eth}

        books = {
            "p1_btc_up": {"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.51", "size": "100"}]},
            "p1_btc_dn": {"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.51", "size": "100"}]},
            "p1_eth_up": {"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.51", "size": "100"}]},
            "p1_eth_dn": {"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.51", "size": "100"}]},
            "s5m_btc_up": {"bids": [{"price": "0.78", "size": "600"}], "asks": [{"price": "0.80", "size": "600"}]},
        }

        async def fake_fetch(url: str, timeout: float = 5.0):
            if "/book?token_id=" in url:
                return books.get(url.split("token_id=")[1])
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch)

        # Under PM_QUARANTINE_LOSING_SLEEVES=1, P1 must be blocked completely
        opps_p1 = []
        await d.scan_and_manage_preopen_maker_straddles(opps_p1, now_ts=now_t)
        assert len(d.pending_preopen_straddles) == 0

        # Disable quarantine in isolated test mode to verify P1 2-leg lock & 1-leg scratch accounting
        monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES", "0")
        await d.scan_and_manage_preopen_maker_straddles(opps_p1, now_ts=now_t)
        assert len(d.pending_preopen_straddles) == 2

        # BTC fills BOTH legs -> locks $0.96 -> $1.00 complete set; ETH fills ONLY UP leg -> scratches at T-8s!
        books["p1_btc_up"]["asks"] = [{"price": "0.48", "size": "100"}]
        books["p1_btc_dn"]["asks"] = [{"price": "0.48", "size": "100"}]
        books["p1_eth_up"]["asks"] = [{"price": "0.48", "size": "100"}]
        books["p1_eth_up"]["bids"] = [{"price": "0.47", "size": "100"}]
        await d.scan_and_manage_preopen_maker_straddles([], now_ts=1793026792.0)  # T-8s cutoff!

        assert any(p["sleeve"] == "P1_PREOPEN_MAKER_STRADDLE" for p in d.open_positions.values())
        scratches = [c for c in d.closed_positions if c["status"] == "PREOPEN_ONE_LEG_SCRATCH"]
        assert len(scratches) == 1 and scratches[0]["tier_pnls_usd"]["T1000"] < 0.0

        # Test S5M_CHAINLINK_SNIPER entry at TTE=90s (requires verified direct USD flag — never unverified USDT!)
        sp_5m = a124.TwapCandleMarketSpec(
            asset="BTC", horizon="5m", market_id="m_s5m", condition_id="0xs5m",
            title="BTC 5m", start_iso="2026-10-26T14:55:00Z", end_iso="2026-10-26T15:00:00Z",
            start_ts=1793026500.0, end_ts=1793026800.0,
            up_token="s5m_btc_up", down_token="s5m_btc_dn", fee_rate=0.072, fee_exponent=1.0, neg_risk=False,
            twap_lookback_sec=60, resolution_source="https://data.chain.link/streams/btc-usd",
        )
        d.s5m_candles = {"BTC_5m_1793026800": sp_5m}
        d.chainlink_open_cache[f"BTC_5m_{int(sp_5m.start_ts)}"] = (sp_5m.end_ts, 83800.0)  # +23.8 bps cushion!
        d.usd_direct_flags["BTC"] = False
        await d.scan_s5m_chainlink_sniper([], now_ts=1793026710.0)
        assert not any(p["sleeve"] == "S5M_CHAINLINK_SNIPER" for p in d.open_positions.values())
        d.usd_direct_flags["BTC"] = True
        await d.scan_s5m_chainlink_sniper([], now_ts=1793026710.0)
        assert any(p["sleeve"] == "S5M_CHAINLINK_SNIPER" for p in d.open_positions.values())

        # Regression: get_return_bps must NEVER self-compare hist[-1] -> 0.0 bps when scan cadence > 5.0s!
        d.spot_hist["ETH"].clear()
        d.usd_spot_hist["ETH"].clear()
        d.spot_hist["ETH"].append((100.0, 2306.50))
        d.spot_hist["ETH"].append((110.0, 2309.50))  # 10.0s gap (> 5.0s lookback), +13.007 bps surge!
        ret_eth = d.get_return_bps("ETH", 5.0)
        assert ret_eth > 12.5
        w_q_stub = {"shares": 13, "avail_a_shares": 100.0, "avail_b_shares": 100.0, "leg_a_walk": {"best_ask": 0.80}, "leg_b_walk": {"best_ask": 0.16}}
        bk_q_a = {"bids": [{"price": "0.78", "size": "100"}], "asks": [{"price": "0.80", "size": "100"}]}
        bk_q_b = {"bids": [{"price": "0.14", "size": "100"}], "asks": [{"price": "0.16", "size": "100"}]}
        assert d._passes_quiet_book_filter("ETH", bk_q_a, bk_q_b, w_q_stub, 110.0) is False

    asyncio.run(_sim_new_sleeves())


def test_oct27_0655_strike_inversion_and_antibox_veto(tmp_path: Path) -> None:
    """
    Exact production regression test for 2026-10-27 10:55 UTC (06:55 AM ET, window 1793098800):
      1. Rejects legacy `crypto-price` spot (`99.964442` vs `99.951949`) and resolves exact closed
         `prev_5m` Gamma `eventMetadata.finalPrice` (`99.8571312195911` < `99.97149156931644`),
         selecting `15M_UP + 5M_DOWN` (`$2.00` double corridor winner at `99.90631053937364`).
      2. Deterministically vetoes inverted anti-boxes (`< $0.900` net) in both `walk_equal_shares_dominance_box`
         and `execute_atomic_dominance_box`, plus 4-token complement-bid sums `> 1.03`.
      3. Dispatches thinner-depth leg (`173` shares) BEFORE deeper tail leg (`442` shares @ `$0.24`).
    """
    from src.polymarket_research.same_oracle_dominance_box import (
        TwapCandleMarketSpec,
        build_prev_5m_gamma_event_url,
        compute_dominance_box_payout_from_close,
        determine_dominance_legs,
        parse_authoritative_open_price,
        walk_equal_shares_dominance_box,
    )
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    m15_sol = TwapCandleMarketSpec(
        asset="SOL", horizon="15m", market_id="6247248", condition_id="0xsol15",
        title="SOL 6:45-7:00AM ET", start_iso="2026-10-27T10:45:00Z", end_iso="2026-10-27T11:00:00Z",
        start_ts=1793097900.0, end_ts=1793098800.0, up_token="sol_15m_up", down_token="sol_15m_dn",
        fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/sol-usd-twap-60s-streams",
    )
    m5_sol = TwapCandleMarketSpec(
        asset="SOL", horizon="5m", market_id="6247315", condition_id="0xsol5",
        title="SOL 6:55-7:00AM ET", start_iso="2026-10-27T10:55:00Z", end_iso="2026-10-27T11:00:00Z",
        start_ts=1793098500.0, end_ts=1793098800.0, up_token="sol_5m_up", down_token="sol_5m_dn",
        fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/sol-usd-twap-60s-streams",
    )
    assert build_prev_5m_gamma_event_url(m15_sol).endswith("slug=sol-updown-5m-1793097600")
    assert build_prev_5m_gamma_event_url(m5_sol).endswith("slug=sol-updown-5m-1793098200")

    # Legacy spot payloads (missing twapEnabled=true&twapLookbackSeconds=60 URL) MUST return None
    assert parse_authoritative_open_price({"openPrice": 99.9644420334347, "completed": False, "cached": True}) is None
    assert parse_authoritative_open_price(
        {"openPrice": 99.9644420334347, "completed": False, "cached": True},
        request_url="https://polymarket.com/api/crypto/crypto-price?symbol=SOL&variant=fifteen",
    ) is None

    # Exact twapEnabled=true&twapLookbackSeconds=60 URL AND closed prev_5m Gamma TWAP finalPrice both resolve 14-digit TWAP!
    from src.polymarket_research.same_oracle_dominance_box import build_crypto_price_query_url, parse_closed_gamma_event_settlement
    u15_twap = build_crypto_price_query_url(m15_sol)
    u5_twap = build_crypto_price_query_url(m5_sol)
    assert "twapEnabled=true&twapLookbackSeconds=60" in u15_twap
    assert parse_authoritative_open_price({"openPrice": 99.8571312195911, "completed": False, "cached": True}, request_url=u15_twap) == 99.8571312195911
    assert parse_authoritative_open_price({"openPrice": 99.97149156931644, "completed": False, "cached": True}, request_url=u5_twap) == 99.97149156931644
    k15_true = parse_authoritative_open_price([{"closed": True, "eventMetadata": {"finalPrice": 99.8571312195911}}])
    k5_true = parse_authoritative_open_price([{"closed": True, "eventMetadata": {"finalPrice": 99.97149156931644}}])
    assert k15_true == 99.8571312195911 and k5_true == 99.97149156931644
    # Verify honest per-leg Gamma settlement records $0.00 on inverted legs (never fake 1x/2x)
    ev_sol15_closed = [{"closed": True, "eventMetadata": {"priceToBeat": 99.8571312195911, "finalPrice": 99.90631053937364}}]
    ev_sol5_closed = [{"closed": True, "eventMetadata": {"priceToBeat": 99.97149156931644, "finalPrice": 99.90631053937364}}]
    assert parse_closed_gamma_event_settlement(ev_sol15_closed, "DOWN") == 0.0
    assert parse_closed_gamma_event_settlement(ev_sol5_closed, "UP") == 0.0
    assert parse_closed_gamma_event_settlement(ev_sol15_closed, "UP") + parse_closed_gamma_event_settlement(ev_sol5_closed, "DOWN") == 2.0
    dom_sol = determine_dominance_legs(m15_sol, k15_true, m5_sol, k5_true, min_corridor_bps=3.0)
    assert dom_sol is not None and dom_sol["regime"] == "15M_UP_PLUS_5M_DOWN"
    assert dom_sol["leg_a"]["opp_token_id"] == "sol_15m_dn" and dom_sol["leg_b"]["opp_token_id"] == "sol_5m_up"
    assert compute_dominance_box_payout_from_close(99.90631053937364, dom_sol["k_low"], dom_sol["k_high"]) == 2.0

    # Orderbook anti-box veto blocks 6:55 AM inverted asks ($0.195 + $0.574 = $0.793 net < $0.900)
    w_anti = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.195", "size": "100"}],
        asks_b_raw=[{"price": "0.574", "size": "100"}],
        target_budget_usd=60.0,
        max_box_cost_net=0.985,
    )
    assert w_anti["filled"] is False and w_anti["reason"] == "SUSPECT_INVERTED_ANTI_BOX"

    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "antibox.jsonl")
    r_anti_exec = ex.execute_atomic_dominance_box(
        box_id="ANTI_BOX_VETO_TEST", leg_a_token_id="tok_a", leg_a_label="15M_DOWN", leg_a_limit_price=0.22,
        leg_b_token_id="tok_b", leg_b_label="5M_UP", leg_b_limit_price=0.48, shares=25, max_box_cost_net=0.985,
    )
    assert r_anti_exec["success"] is False and "ANTI_BOX_COST_FLOOR_VETO" in r_anti_exec["error"]

    # Thinner-leg-first dispatch: Leg A @ $0.24 (442 avail) vs Leg B @ $0.70 (173 avail) MUST send thinner Leg B first!
    r_thin_first = ex.execute_atomic_dominance_box(
        box_id="ETH_THINNER_FIRST", leg_a_token_id="eth_15m", leg_a_label="15M_LEG", leg_a_limit_price=0.24,
        leg_b_token_id="eth_5m", leg_b_label="5M_LEG", leg_b_limit_price=0.70, shares=25, max_box_cost_net=0.985,
        leg_a_avail_shares=442.0, leg_b_avail_shares=173.0,
    )
    assert r_thin_first["success"] is True and r_thin_first["leg_1"]["label"] == "5M_LEG"

    # Slug-echo guard: a closed Gamma event for the WRONG slug must never be accepted as a strike
    g_url = build_prev_5m_gamma_event_url(m15_sol)
    ev_ok = [{"slug": "sol-updown-5m-1793097600", "closed": True, "eventMetadata": {"finalPrice": 99.8571312195911}}]
    ev_wrong = [{"slug": "sol-updown-5m-1793097300", "closed": True, "eventMetadata": {"finalPrice": 99.0}}]
    assert parse_authoritative_open_price(ev_ok, request_url=g_url) == 99.8571312195911
    assert parse_authoritative_open_price(ev_wrong, request_url=g_url) is None

    # Complement anti-box check FAILS CLOSED (missing opp tokens / missing books / empty bids / sum > 1.0)
    import asyncio
    import src.polymarket_research.alpha_124_shadow_daemon as a124_fc
    monkey_state = tmp_path / "fc_state.json"
    a124_fc.STATE_FILE = monkey_state
    d_fc = a124_fc.Alpha124ShadowDaemon(single_scan=True)
    books_fc = {}

    async def _fc_fetch(url: str, timeout: float = 5.0):
        for tk, bk in books_fc.items():
            if f"token_id={tk}" in url:
                return bk
        return None

    d_fc.fetch_json = _fc_fetch
    la = {"opp_token_id": "oa", "label": "A"}
    lb = {"opp_token_id": "ob", "label": "B"}
    assert asyncio.run(d_fc._passes_complement_anti_box_check({"label": "A"}, {"label": "B"})) is False
    assert asyncio.run(d_fc._passes_complement_anti_box_check(la, lb)) is False
    books_fc["oa"] = {"bids": [{"price": "0.40", "size": "50"}]}
    books_fc["ob"] = {"bids": []}
    assert asyncio.run(d_fc._passes_complement_anti_box_check(la, lb)) is False
    books_fc["ob"] = {"bids": [{"price": "0.55", "size": "50"}]}
    assert asyncio.run(d_fc._passes_complement_anti_box_check(la, lb)) is True
    books_fc["ob"] = {"bids": [{"price": "0.61", "size": "50"}]}
    assert asyncio.run(d_fc._passes_complement_anti_box_check(la, lb)) is False


def test_riskless_expansion_7coins_b3_w3no_pyth_and_maker_anchor(tmp_path):
    """Verify 7-coin D1 expansion, t+35s Gamma strike fallback, B3 barrier boxes, W3 ALL_BUCKETS_NO, Pyth 0%-fee, and D1_MAKER_ANCHOR_BOX."""
    import asyncio
    import time
    from datetime import date
    import src.polymarket_research.alpha_124_shadow_daemon as a124_exp
    from src.polymarket_research.same_oracle_dominance_box import (
        DOMINANCE_ASSETS,
        MIN_CORRIDOR_BPS_BY_ASSET,
        build_crypto_price_query_url,
        determine_dominance_legs,
        parse_twap_candle_event,
    )
    from src.polymarket_research.barrier_onetouch_svi_engine import detect_barrier_monotonicity_boxes
    from src.polymarket_research.multistrike_svi_scalper import ZERO_FEE_PYTH_DAILY_SERIES
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        evaluate_weather_event_slate,
    )

    # 1. 7-coin Dominance catalog (BNB, DOGE, HYPE) + 5.0 bps expansion corridor guard
    assert set(DOMINANCE_ASSETS) == {"BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "HYPE"}
    assert len(ZERO_FEE_PYTH_DAILY_SERIES) == 8
    specs_exp = {}
    for sym, slug_p, stream in (
        ("BNB", "bnb", "bnb-usd"),
        ("DOGE", "doge", "doge-usd"),
        ("HYPE", "hype", "hype-usd"),
    ):
        ev15 = {
            "slug": f"{slug_p}-updown-15m-1793100000",
            "endDate": "2026-10-27T11:15:00Z",
            "markets": [{
                "id": f"m15_{sym}", "conditionId": "0x" + "11" * 32, "question": f"{sym} Up or Down 15m",
                "eventStartTime": "2026-10-27T11:00:00Z", "endDate": "2026-10-27T11:15:00Z",
                "resolutionSource": f"https://data.chain.link/streams/{stream}-twap-60s-streams",
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "outcomes": '["Up", "Down"]', "clobTokenIds": f'["{sym}_15_up", "{sym}_15_dn"]',
                "orderMinSize": 5, "feesEnabled": True, "feeSchedule": {"rate": 0.07, "exponent": 1},
            }],
        }
        ev5 = {
            "slug": f"{slug_p}-updown-5m-1793100600",
            "endDate": "2026-10-27T11:15:00Z",
            "markets": [{
                "id": f"m5_{sym}", "conditionId": "0x" + "22" * 32, "question": f"{sym} Up or Down 5m",
                "eventStartTime": "2026-10-27T11:10:00Z", "endDate": "2026-10-27T11:15:00Z",
                "resolutionSource": f"https://data.chain.link/streams/{stream}-twap-60s-streams",
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "outcomes": '["Up", "Down"]', "clobTokenIds": f'["{sym}_5_up", "{sym}_5_dn"]',
                "orderMinSize": 5, "feesEnabled": True, "feeSchedule": {"rate": 0.07, "exponent": 1},
            }],
        }
        s15 = parse_twap_candle_event(ev15, sym, "15m")
        s5 = parse_twap_candle_event(ev5, sym, "5m")
        assert s15 is not None and s5 is not None and s15.asset == sym
        assert f"symbol={sym}" in build_crypto_price_query_url(s15)
        specs_exp[sym] = (s15, s5)

    dg15, dg5 = specs_exp["DOGE"]
    assert determine_dominance_legs(dg15, 0.20000, dg5, 0.20007, min_corridor_bps=MIN_CORRIDOR_BPS_BY_ASSET["DOGE"]) is None
    assert determine_dominance_legs(dg15, 0.20000, dg5, 0.20014, min_corridor_bps=MIN_CORRIDOR_BPS_BY_ASSET["DOGE"]) is not None

    # 2. Proactive t+35s prev_5m Gamma eventMetadata.finalPrice strike recovery when crypto-price returns HTTP 429 (None)
    a124_exp.STATE_FILE = tmp_path / "exp_state.json"
    a124_exp.LEDGER_FILE = tmp_path / "exp_ledger.jsonl"
    a124_exp.LIVE_ALPHA124_STATE_MIRROR_FILE = tmp_path / "exp_mirror.json"
    a124_exp.D1_LIVE_CANDIDATES_FILE = tmp_path / "exp_d1_cands.jsonl"
    d_exp = a124_exp.Alpha124ShadowDaemon(single_scan=False)
    prev_slug = f"doge-updown-5m-{int(dg15.start_ts) - 300}"

    async def _fetch_429_fallback(url: str, timeout: float = 5.0):
        if "crypto-price" in url:
            return None  # Simulated Chainlink HTTP 429
        if prev_slug in url:
            return [{"slug": prev_slug, "closed": True, "eventMetadata": {"finalPrice": 0.21456}}]
        return None

    d_exp.fetch_json = _fetch_429_fallback
    orig_time = a124_exp.time.time
    try:
        a124_exp.time.time = lambda: dg15.start_ts + 45.0
        k_rec = asyncio.run(d_exp.get_authoritative_open_strike(dg15))
        assert k_rec == 0.21456
    finally:
        a124_exp.time.time = orig_time

    # 3. B3_BARRIER_MONO_BOX monotonicity detector (UP & DOWN barriers)
    b3_rows = [
        {"direction": "UP", "strike": 100000.0, "ask_yes": 0.50, "ask_no": 0.52, "market_id": "m_lo", "condition_id": "0x1", "yes_token": "t_lo_y", "no_token": "t_lo_n", "end_ts": time.time() + 3600},
        {"direction": "UP", "strike": 105000.0, "ask_yes": 0.58, "ask_no": 0.43, "market_id": "m_hi", "condition_id": "0x2", "yes_token": "t_hi_y", "no_token": "t_hi_n", "end_ts": time.time() + 3600},
        {"direction": "DOWN", "strike": 80000.0, "ask_yes": 0.58, "ask_no": 0.44, "market_id": "m_dlo", "condition_id": "0x3", "yes_token": "t_dlo_y", "no_token": "t_dlo_n", "end_ts": time.time() + 3600},
        {"direction": "DOWN", "strike": 85000.0, "ask_yes": 0.50, "ask_no": 0.52, "market_id": "m_dhi", "condition_id": "0x4", "yes_token": "t_dhi_y", "no_token": "t_dhi_n", "end_ts": time.time() + 3600},
    ]
    b3_found = detect_barrier_monotonicity_boxes(b3_rows, fee_rate=0.07, max_box_cost_net=0.985)
    assert len(b3_found) == 2
    assert {b["direction"] for b in b3_found} == {"UP", "DOWN"}

    # 4. W3_WEATHER_SLATE_ARB ALL_BUCKETS_NO ($2.00 guaranteed payout on 3-bucket slate) + settlement
    b1 = WeatherBucket("w1", "c1", "<=69F", "NYC <= 69F", "w1_y", "w1_n", "F", -float("inf"), 69.0)
    b2 = WeatherBucket("w2", "c2", "70-71F", "NYC 70-71F", "w2_y", "w2_n", "F", 70.0, 71.0)
    b3 = WeatherBucket("w3", "c3", ">=72F", "NYC >= 72F", "w3_y", "w3_n", "F", 72.0, float("inf"))
    sp_w = WeatherEventSpec(
        "W_EV_NO", "nyc-oct-27", "nyc-daily-weather", "NYC High", "KLGA", "NYC",
        40.77, -73.87, "America/New_York", date(2026, 10, 27), "HIGH", "F",
        "zero_fees", "2026-10-28T04:00:00Z", [b1, b2, b3],
    )
    w_res = evaluate_weather_event_slate(
        sp_w,
        [0.34, 0.33, 0.33],
        {
            "w1": {"ask_yes": 0.42, "ask_yes_shares": 50.0, "ask_no": 0.62, "ask_no_shares": 60.0},
            "w2": {"ask_yes": 0.42, "ask_yes_shares": 50.0, "ask_no": 0.62, "ask_no_shares": 60.0},
            "w3": {"ask_yes": 0.42, "ask_yes_shares": 50.0, "ask_no": 0.62, "ask_no_shares": 60.0},
        },
        target_budget_usd=35.0,
    )
    full_arb = w_res["full_slate_arb"]
    assert full_arb is not None and full_arb["mode"] == "FULL_SLATE_NO_COMPLEMENT_ARB"
    assert full_arb["guaranteed_payout_per_set"] == 2.0
    assert asyncio.run(d_exp.open_shadow_weather_slate(sp_w, full_arb, time.time() - 60.0)) is True

    async def _fetch_w_closed(url: str, timeout: float = 5.0):
        if "/markets/w1" in url:
            return {"id": "w1", "closed": True, "umaResolutionStatus": "resolved", "clobTokenIds": '["w1_y","w1_n"]', "outcomePrices": '["1","0"]'}
        if "/markets/w2" in url:
            return {"id": "w2", "closed": True, "umaResolutionStatus": "resolved", "clobTokenIds": '["w2_y","w2_n"]', "outcomePrices": '["0","1"]'}
        if "/markets/w3" in url:
            return {"id": "w3", "closed": True, "umaResolutionStatus": "resolved", "clobTokenIds": '["w3_y","w3_n"]', "outcomePrices": '["0","1"]'}
        return None

    d_exp.fetch_json = _fetch_w_closed
    asyncio.run(d_exp.manage_open_positions())
    w_closed = [c for c in d_exp.closed_positions if c["sleeve"] == "W3_WEATHER_SLATE_ARB"]
    assert len(w_closed) == 1 and w_closed[0]["won"] is True and w_closed[0]["status"] == "SETTLED_WEATHER_SLATE_NX"
    assert w_closed[0]["tier_pnls_usd"]["T100"] > 0.0

    # 5. Tier-2 D1_MAKER_ANCHOR_BOX: passive fill -> atomic hedge in open_positions, and cancel-on-thinning (<2x depth)
    from dataclasses import replace as dc_replace
    now_ma = time.time()
    dg15 = dc_replace(dg15, end_ts=now_ma + 180.0)
    dg5 = dc_replace(dg5, end_ts=now_ma + 180.0)
    dom_dg = determine_dominance_legs(dg15, 0.20000, dg5, 0.20020, min_corridor_bps=5.0)
    assert dom_dg is not None
    tok_anc = dom_dg["leg_a"]["token_id"]
    tok_hdg = dom_dg["leg_b"]["token_id"]
    ma_books = {
        tok_anc: {"bids": [{"price": "0.50", "size": "80"}], "asks": [{"price": "0.53", "size": "80"}]},
        tok_hdg: {"bids": [{"price": "0.45", "size": "220"}], "asks": [{"price": "0.46", "size": "220"}]},
    }

    async def _fetch_ma(url: str, timeout: float = 5.0):
        for tk, bk in ma_books.items():
            if tk in url:
                return bk
        return None

    d_exp.fetch_json = _fetch_ma
    assert d_exp.post_maker_anchor_candidate(dg15, dg5, dom_dg, ma_books[tok_anc], ma_books[tok_hdg], now_ts=now_ma - 2.0) is True
    assert len(d_exp.pending_maker_anchors) == 1
    # Simulate trade through passive anchor bid ($0.51 >= ask $0.51) while hedge ask $0.46 has 220 shares (>=3x) -> hedged box!
    ma_books[tok_anc] = {"bids": [{"price": "0.50", "size": "80"}], "asks": [{"price": "0.51", "size": "40"}]}
    asyncio.run(d_exp.manage_pending_maker_anchors(now_ts=now_ma))
    assert len(d_exp.pending_maker_anchors) == 0
    ma_open = [p for p in d_exp.open_positions.values() if p["sleeve"] == "D1_MAKER_ANCHOR_BOX"]
    assert len(ma_open) == 1 and ma_open[0]["extra"]["is_maker_anchor_box"] is True

    # Cancel-on-thinning when opposite hedge leg depth drops below 2.0x
    bnb15, bnb5 = specs_exp["BNB"]
    bnb15 = dc_replace(bnb15, end_ts=now_ma + 180.0)
    bnb5 = dc_replace(bnb5, end_ts=now_ma + 180.0)
    dom_bnb = determine_dominance_legs(bnb15, 600.0, bnb5, 600.6, min_corridor_bps=5.0)
    assert dom_bnb is not None
    tok_b_anc = dom_bnb["leg_a"]["token_id"]
    tok_b_hdg = dom_bnb["leg_b"]["token_id"]
    ma_books[tok_b_anc] = {"bids": [{"price": "0.50", "size": "80"}], "asks": [{"price": "0.53", "size": "80"}]}
    ma_books[tok_b_hdg] = {"bids": [{"price": "0.45", "size": "220"}], "asks": [{"price": "0.46", "size": "220"}]}
    assert d_exp.post_maker_anchor_candidate(bnb15, bnb5, dom_bnb, ma_books[tok_b_anc], ma_books[tok_b_hdg], now_ts=now_ma - 2.0) is True
    assert len(d_exp.pending_maker_anchors) == 1
    ma_books[tok_b_hdg] = {"bids": [{"price": "0.45", "size": "5"}], "asks": [{"price": "0.46", "size": "5"}]}  # Thinned < 2x!
    asyncio.run(d_exp.manage_pending_maker_anchors(now_ts=now_ma))
    assert len(d_exp.pending_maker_anchors) == 0

    # Verify continuous history/SHM recorder covers all 7 DOMINANCE_ASSETS + 5m/15m/1h/4h files + corridor/slate telemetry
    import json as _json_t
    from src.polymarket_research.polymarket_terminal_recorder import ASSET_CONFIGS, PolymarketDualFeed1HRecorder
    for sym in DOMINANCE_ASSETS:
        assert sym in ASSET_CONFIGS
        rec_i = PolymarketDualFeed1HRecorder(asset=sym)
        assert rec_i.coinbase_product == f"{sym}-USD"
        assert rec_i.telemetry_5m_file.name == f"polymarket_5m_telemetry_{sym.lower()}.jsonl"
        assert rec_i.telemetry_15m_file.name == f"polymarket_15m_telemetry_{sym.lower()}.jsonl"
        assert rec_i.telemetry_4h_file.name == f"polymarket_4h_telemetry_{sym.lower()}.jsonl"
    assert ASSET_CONFIGS["HYPE"].get("futures_only_ref") is True
    assert ASSET_CONFIGS["DOGE"]["series_slug"] == "doge-up-or-down-hourly"
    assert ASSET_CONFIGS["BNB"]["series_slug"] == "bnb-up-or-down-hourly"

    d_exp._record_d1_corridor_telemetry(
        "15m_5m",
        bnb15,
        bnb5,
        dom_bnb,
        {"bids": [{"price": "0.50", "size": "80"}], "asks": [{"price": "0.53", "size": "80"}]},
        {"bids": [{"price": "0.45", "size": "80"}], "asks": [{"price": "0.49", "size": "80"}]},
        now_ma,
    )
    t_file = tmp_path / "alpha124_market_telemetry.jsonl"
    assert t_file.exists()
    t_rows = [_json_t.loads(ln) for ln in t_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert any(r["type"] == "D1_CORRIDOR" and r["asset"] == "BNB" and r["gross_box_l1"] == 1.02 for r in t_rows)


def test_telemetry_compact_encoding_delta_dedupe_and_inode_safe_gzip_compactor(tmp_path: Path, monkeypatch) -> None:
    import json as _json_c
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from scripts.honest_purged_wfo_optimizer import iter_jsonl_lines_with_archives
    from scripts.polymarket_telemetry_compactor import compact_jsonl_file, is_protected_path
    from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook, _dumps_compact

    # 1. Layer 1: L2OrderBook compact=True vs compact=False backward compatibility & byte savings
    bk = L2OrderBook("tok_test")
    bk.apply_snapshot(
        bids=[{"price": str(round(0.49 - 0.01 * i, 2)), "size": "120"} for i in range(15)],
        asks=[{"price": str(round(0.51 + 0.01 * i, 2)), "size": "120"} for i in range(15)],
    )
    t_obs = bk.last_book_update_ts + 0.5
    full_m = bk.get_metrics(obs_ts=t_obs, compact=False)
    comp_m = bk.get_metrics(obs_ts=t_obs, compact=True)
    assert "microprice_formula" in full_m and "vwap_$250" in full_m and len(full_m["raw_top_bids"]) == 15
    assert "microprice_formula" not in comp_m and "vwap_$250" not in comp_m and len(comp_m["raw_top_bids"]) == 10
    for k in ("best_bid", "best_ask", "q_mid", "q_micro", "obi_l1", "obi_depth", "vwap_$20", "vwap_$25", "vwap_$50", "effective_price_$50", "fill_fees_$50"):
        assert comp_m[k] == full_m[k]
    raw_bytes_full = len(_json_c.dumps({"UP": full_m, "DOWN": full_m}).encode("utf-8"))
    raw_bytes_comp = len(_dumps_compact({"UP": comp_m, "DOWN": comp_m}).encode("utf-8"))
    assert raw_bytes_comp < 0.45 * raw_bytes_full

    # 2. Layer 2b: Delta deduplication in _record_market_telemetry
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "st.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ldg.jsonl")
    monkeypatch.setattr(a124, "MARKET_TELEMETRY_FILE", tmp_path / "m_telem.jsonl")
    d_t = a124.Alpha124ShadowDaemon(single_scan=True)
    d_t._record_market_telemetry("W_SLATE_1", 10.0, {"type": "WEATHER_SLATE", "sum_yes_l1": 1.02}, now_ts=1000.0, sig=(1.02,))
    d_t._record_market_telemetry("W_SLATE_1", 10.0, {"type": "WEATHER_SLATE", "sum_yes_l1": 1.02}, now_ts=1025.0, sig=(1.02,))  # unchanged -> skipped!
    d_t._record_market_telemetry("W_SLATE_1", 10.0, {"type": "WEATHER_SLATE", "sum_yes_l1": 0.99}, now_ts=1040.0, sig=(0.99,))  # changed -> logged!
    m_lines = (tmp_path / "m_telem.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(m_lines) == 2

    # 3. Layer 3 & 4: Protected ledgers + lossless inode-safe gzip compaction + sibling stem isolation + WFO streaming
    assert is_protected_path(tmp_path / "live_orders.jsonl") is True
    assert is_protected_path(tmp_path / "finalized_market_resolutions.jsonl") is True
    assert is_protected_path(tmp_path / "alpha124_shadow_ledger.jsonl") is True
    assert is_protected_path(tmp_path / "d1_live_box_candidates.jsonl") is True
    assert is_protected_path(tmp_path / "polymarket_hourly_telemetry.jsonl") is False
    assert is_protected_path(tmp_path / "alpha124_market_telemetry.jsonl") is False
    assert is_protected_path(tmp_path / "counterfactual_candidates.jsonl") is False

    pm_dir = tmp_path / "polymarket"
    pm_dir.mkdir(parents=True, exist_ok=True)
    hot_btc = pm_dir / "polymarket_hourly_telemetry.jsonl"
    hot_eth = pm_dir / "polymarket_hourly_telemetry_eth.jsonl"
    expected_btc_ids = [f"btc_{i}" for i in range(400)]
    hot_btc.write_text(
        "".join(_dumps_compact({"seq": i, "id": f"btc_{i}", "UP": comp_m}) + "\n" for i in range(400)),
        encoding="utf-8",
    )
    hot_eth.write_text(
        "".join(_dumps_compact({"seq": i, "id": f"eth_{i}", "UP": comp_m}) + "\n" for i in range(400)),
        encoding="utf-8",
    )

    res_btc = compact_jsonl_file(hot_btc, hot_threshold_bytes=20_000, keep_tail_bytes=15_000, min_archive_bytes=10_000)
    res_eth = compact_jsonl_file(hot_eth, hot_threshold_bytes=20_000, keep_tail_bytes=15_000, min_archive_bytes=10_000)
    assert res_btc["status"] == "COMPACTED" and res_btc["inode_preserved"] is True and res_btc["compression_ratio_x"] > 3.0
    assert res_eth["status"] == "COMPACTED"
    assert hot_btc.stat().st_size < 25_000

    # Stream back BTC archive + hot tail and verify 100% lossless order with zero ETH cross-contamination!
    streamed_btc = [_json_c.loads(ln)["id"] for ln in iter_jsonl_lines_with_archives(pm_dir, "polymarket_hourly_telemetry.jsonl") if ln.strip()]
    assert streamed_btc == expected_btc_ids


def test_multi_vertical_zero_fee_expansion_sleeves(tmp_path: Path, monkeypatch) -> None:
    """
    Verifies all new zero-lookahead expansion sleeves:
      1. Weather v2: `HKO` Hong Kong Observatory CSV parsing (isolating HK Observatory from Chek Lap Kok airport)
         + `W1_LOW` morning post-sunrise trough lock & evening cold-front veto.
      2. TradFi Pyth `0%`-Fee: NYSE (`6.5h/day`) & CME (`23h/day`) session variance clocks, `CM_B3` calendar
         inclusion (`NO_Week + YES_Month`) and `Close ⊂ Hit` path-vs-terminal dominance boxes.
      3. Sports `SP1_NBA_ZERO_FEE_BOX`: Full-game Polish Middle (`ML + underdog spread`), spread monotonicity,
         totals O/U middle, and strict rejection of anti-boxes (`-4.5 + -1.5`), 1H markets, and push lines.
      4. `NR0_ZERO_FEE_SLATE_ARB` early-`NO` bracket handling & `B4_TOUCHED_BARRIER_WICK_LOCK` finalized-1m sweep.
    """
    import asyncio
    import time
    from datetime import date
    from zoneinfo import ZoneInfo

    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.barrier_onetouch_svi_engine import BarrierRungSpec
    from src.polymarket_research.tradfi_sports_zero_fee_engine import (
        compute_effective_trading_hours,
        detect_nba_dominance_boxes,
        detect_pyth_calendar_inclusion_boxes,
        detect_pyth_close_vs_hit_boxes,
        parse_nba_zero_fee_event,
        parse_zero_fee_negrisk_slate,
    )
    from src.polymarket_research.weather_metar_engine import (
        MetarObservation,
        WeatherBucket,
        WeatherEventSpec,
        compute_weather_probabilities,
        parse_hko_csv_observations,
        parse_weather_event,
    )

    # 1A. HKO parser must extract `HK Observatory` (26.3C max / 24.8C min / 26.2C cur) and ignore Chek Lap Kok (28.7C)!
    csv_1m = "Date time,Automatic Weather Station,Air Temperature(degree Celsius)\n202610281020,Chek Lap Kok,28.7\n202610281020,HK Observatory,26.2\n"
    csv_mm = "Date time,Automatic Weather Station,Max,Min\n202610281020,Chek Lap Kok,28.7,26.0\n202610281020,HK Observatory,26.3,24.8\n"
    hko_obs = parse_hko_csv_observations(csv_1m, csv_mm, date(2026, 10, 28))
    assert len(hko_obs) == 3
    assert max(o.temp_c for o in hko_obs) == 26.3
    assert min(o.temp_c for o in hko_obs) == 24.8
    assert hko_obs[-1].temp_c == 26.2

    hko_ev = {
        "id": "ev_hko_1",
        "title": "Highest temperature in Hong Kong on October 28?",
        "endDate": "2026-10-28T16:00:00Z",
        "markets": [
            {
                "id": f"hk_{i}",
                "conditionId": f"0xhk_{i}",
                "groupItemTitle": lbl,
                "description": "Resolves to highest temperature recorded by the Hong Kong Observatory on 28 Oct '26 via https://www.weather.gov.hk/en/cis/climat.htm",
                "clobTokenIds": f'["hy_{i}", "hn_{i}"]',
                "feeType": "zero_fees",
                "feesEnabled": True,
                "feeSchedule": {"rate": 0},
            }
            for i, lbl in enumerate(["25°C or below", "26°C", "27°C", "28°C or higher"])
        ],
    }
    sp_hko = parse_weather_event(hko_ev)
    assert sp_hko is not None and sp_hko.icao == "HKO" and sp_hko.fee_type == "zero_fees"

    # 1B. W1_LOW morning trough lock + strict evening cold-front veto
    tz_ny = ZoneInfo("America/New_York")
    low_buckets = [
        WeatherBucket("b0", "c0", "9°C or below", "9-", "y0", "n0", "C", float("-inf"), 9.0),
        WeatherBucket("b1", "c1", "10°C", "10", "y1", "n1", "C", 10.0, 10.0),
        WeatherBucket("b2", "c2", "11°C", "11", "y2", "n2", "C", 11.0, 11.0),
        WeatherBucket("b3", "c3", "12°C or higher", "12+", "y3", "n3", "C", 12.0, float("inf")),
    ]
    sp_low = WeatherEventSpec(
        "ev_low", "nyc-low", "nyc-daily-lowest-temperature", "Lowest temperature in NYC on October 28?",
        "KLGA", "NYC", 40.7769, -73.8740, "America/New_York", date(2026, 10, 28), "LOW", "C", "zero_fees",
        "2026-10-29T04:00:00Z", low_buckets,
    )
    dt_06 = datetime(2026, 10, 28, 6, 0, tzinfo=tz_ny)
    dt_11 = datetime(2026, 10, 28, 11, 0, tzinfo=tz_ny)
    obs_low = [
        MetarObservation("KLGA", dt_06.astimezone(timezone.utc), dt_06, 10.1, True, "T0101"),
        MetarObservation("KLGA", dt_11.astimezone(timezone.utc), dt_11, 14.5, True, "T0145"),
    ]
    # Warm evening ensemble (all 20 members >= 13.0C through midnight -> +2.9C above 10.1C morning trough) -> LOCKS!
    ens_warm = {
        int(datetime(2026, 10, 28, h, 0, tzinfo=tz_ny).astimezone(timezone.utc).timestamp()): [13.5] * 20
        for h in range(12, 24)
    }
    ens_warm[int(datetime(2026, 10, 29, 0, 0, tzinfo=tz_ny).astimezone(timezone.utc).timestamp())] = [13.2] * 20
    r_warm = compute_weather_probabilities(sp_low, dt_11.astimezone(timezone.utc), obs_low, ens_warm)
    assert r_warm["is_solar_lock"] is True and r_warm["locked_bucket_idx"] == 1

    # Cold-front evening ensemble (drops to 10.8C at 23:00 < 10.1 + 1.8 = 11.9C) -> MUST VETO morning lock!
    ens_front = dict(ens_warm)
    ens_front[int(datetime(2026, 10, 28, 23, 0, tzinfo=tz_ny).astimezone(timezone.utc).timestamp())] = [10.8] * 20
    r_front = compute_weather_probabilities(sp_low, dt_11.astimezone(timezone.utc), obs_low, ens_front)
    assert r_front["is_solar_lock"] is False

    # 2. NYSE (`6.5h/day`) & CME (`23h/day`) session variance clocks + Pyth `CM_B3` inclusion boxes
    fri_15_et = datetime(2026, 10, 30, 15, 0, tzinfo=tz_ny).timestamp()
    mon_1030_et = datetime(2026, 11, 2, 10, 30, tzinfo=tz_ny).timestamp()
    # Fri 15:00->16:00 (1.0h) + Sat/Sun (0.0h) + Mon 09:30->10:30 (1.0h) = exactly 2.0h RTH!
    assert abs(compute_effective_trading_hours(fri_15_et, mon_1030_et, "EQUITY_RTH") - 2.0) < 1e-6

    cal_boxes = detect_pyth_calendar_inclusion_boxes([
        {"asset": "WTI", "direction": "UP", "strike": 105.0, "fee_rate": 0.0, "start_ts": 1000.0, "end_ts": 50000.0, "ask_yes": 0.45, "ask_no": 0.56, "market_id": "w1", "condition_id": "cw1", "yes_token": "wy", "no_token": "wn"},
        {"asset": "WTI", "direction": "UP", "strike": 105.0, "fee_rate": 0.0, "start_ts": 900.0, "end_ts": 200000.0, "ask_yes": 0.42, "ask_no": 0.59, "market_id": "m1", "condition_id": "cm1", "yes_token": "my", "no_token": "mn"},
    ])
    assert len(cal_boxes) == 1 and abs(cal_boxes[0]["box_cost_net"] - 0.98) < 1e-6

    cvh_boxes = detect_pyth_close_vs_hit_boxes(
        close_rows=[{"asset": "SPY", "strike": 775.0, "is_downward": False, "fee_rate": 0.0, "end_ts": 5000.0, "ask_no": 0.55, "market_id": "c1", "condition_id": "cc1", "yes_token": "cy", "no_token": "cn"}],
        hit_rows=[{"asset": "SPY", "strike": 775.0, "direction": "UP", "fee_rate": 0.0, "start_ts": 1000.0, "end_ts": 9000.0, "ask_yes": 0.43, "market_id": "h1", "condition_id": "ch1", "yes_token": "hy", "no_token": "hn"}],
        now_ts=2000.0,
    )
    assert len(cvh_boxes) == 1 and abs(cvh_boxes[0]["box_cost_net"] - 0.98) < 1e-6

    # 3. NBA Zero-Fee Polish Middle & Dominance Box invariants (and rejection of anti-boxes & 1H markets)
    nba_ev = {
        "id": "nba_1",
        "slug": "nba-bkn-bos",
        "title": "Nets vs. Celtics",
        "endDate": "2026-10-28T23:30:00Z",
        "markets": [
            {"id": "ml", "conditionId": "c_ml", "sportsMarketType": "moneyline", "question": "Nets vs. Celtics", "outcomes": '["Nets", "Celtics"]', "clobTokenIds": '["t_nets_ml", "t_bos_ml"]', "feeType": "zero_fees", "feesEnabled": True, "feeSchedule": {"rate": 0}},
            {"id": "sp_bos", "conditionId": "c_sp1", "sportsMarketType": "spreads", "question": "Spread: Celtics (-4.5)", "outcomes": '["Celtics", "Nets"]', "line": -4.5, "clobTokenIds": '["t_bos_m45", "t_nets_p45"]', "feeType": "zero_fees", "feesEnabled": True, "feeSchedule": {"rate": 0}},
            {"id": "sp_1h", "conditionId": "c_1h", "sportsMarketType": "first_half_spreads", "question": "1H Spread: Celtics (-2.5)", "outcomes": '["Celtics", "Nets"]', "line": -2.5, "clobTokenIds": '["t_1h_a", "t_1h_b"]', "feeType": "zero_fees"},
            {"id": "tot_lo", "conditionId": "c_tl", "sportsMarketType": "totals", "question": "Nets vs. Celtics: O/U 215.5", "outcomes": '["Over", "Under"]', "line": 215.5, "clobTokenIds": '["t_ov_215", "t_un_215"]', "feeType": "zero_fees"},
            {"id": "tot_hi", "conditionId": "c_th", "sportsMarketType": "totals", "question": "Nets vs. Celtics: O/U 220.5", "outcomes": '["Over", "Under"]', "line": 220.5, "clobTokenIds": '["t_ov_220", "t_un_220"]', "feeType": "zero_fees"},
        ],
    }
    sp_nba = parse_nba_zero_fee_event(nba_ev, now_ts=1793220000.0)
    assert sp_nba is not None
    # 1H spread must be strictly excluded!
    assert all("1h" not in lg.token_id for lg in sp_nba.margin_legs)
    nba_arbs = detect_nba_dominance_boxes(
        sp_nba,
        {
            "t_bos_ml": 0.56,      # Celtics ML (M < 0)
            "t_nets_p45": 0.425,   # Nets +4.5 (M > -4.5) -> Celtics ML + Nets +4.5 = $0.985 Polish Middle (wins $2 if BOS wins by 1..4)!
            "t_bos_m45": 0.58,     # Celtics -4.5 (anti-box with Nets ML must NOT pair!)
            "t_nets_ml": 0.40,     # Nets ML + Celtics -4.5 = $0.98 ANTI-BOX (loses if BOS wins by 1..4) -> MUST BE REJECTED!
            "t_ov_215": 0.52,
            "t_un_220": 0.465,     # Over 215.5 + Under 220.5 = $0.985 Total Middle!
        },
        max_box_cost_net=0.994,
    )
    labels = {a["label"] for a in nba_arbs}
    assert "Nets +4.5 + Celtics ML" in labels
    assert "Over 215.5 + Under 220.5" in labels
    assert not any("Nets ML" in lbl and "Celtics -4.5" in lbl for lbl in labels), "Anti-box must never be emitted!"

    # 4. Zero-Fee NegRisk Slate early-NO bracket acceptance vs YES-resolved rejection
    nr_ev = {
        "id": "nr_elon",
        "title": "Elon tweets 48h?",
        "negRisk": True,
        "endDate": "2026-10-30T16:00:00Z",
        "markets": [
            {"id": "e0", "closed": True, "outcomePrices": '["0", "1"]'},  # <40 already resolved NO -> safe!
            {"id": "e1", "conditionId": "ce1", "groupItemTitle": "40-64", "clobTokenIds": '["ey1","en1"]', "feeType": "zero_fees"},
            {"id": "e2", "conditionId": "ce2", "groupItemTitle": "65-89", "clobTokenIds": '["ey2","en2"]', "feeType": "zero_fees"},
            {"id": "e3", "conditionId": "ce3", "groupItemTitle": "90+", "clobTokenIds": '["ey3","en3"]', "feeType": "zero_fees"},
        ],
    }
    assert parse_zero_fee_negrisk_slate(nr_ev, "elon-tweets-48h") is not None
    nr_ev["markets"][0]["outcomePrices"] = '["1", "0"]'
    assert parse_zero_fee_negrisk_slate(nr_ev, "elon-tweets-48h") is None

    # 5. B4_TOUCHED_BARRIER_WICK_LOCK finalized-1m sweep in Alpha124ShadowDaemon
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "b4_st.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "b4_ldg.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "b4_opps.json")

    async def _run_b4():
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_b4 = time.time()
        d.spots["BTC"] = 84200.0
        d.barrier_rungs["m_b4"] = BarrierRungSpec(
            asset="BTC", horizon_group="WEEK", series_slug="btc-hit", event_id="ev_b4", market_id="m_b4",
            condition_id="0xcb4", group_label="↑ 85,000", question="Will BTC hit $85,000?", strike=85000.0,
            direction="UP", start_ts=now_b4 - 7200.0, end_ts=now_b4 + 86400.0, yes_token="t_b4_y", no_token="t_b4_n", fee_rate=0.07,
        )
        # Newly minted mid-month rung with low $0.085 ask must NEVER be falsely swept by B4!
        d.barrier_rungs["m_b4_stale"] = BarrierRungSpec(
            asset="BTC", horizon_group="MONTH", series_slug="btc-hit", event_id="ev_b4", market_id="m_b4_stale",
            condition_id="0xcst", group_label="↑ 85,000", question="Will BTC reach $85,000 in Oct?", strike=85000.0,
            direction="UP", start_ts=now_b4 - 600.0, end_ts=now_b4 + 86400.0, yes_token="t_b4_stale_y", no_token="t_b4_stale_n", fee_rate=0.07,
        )
        # Finalized 1m candle already wicked to $85,120 (>= 85000 * 1.0005), then spot faded to $84,200!
        d.barrier_ext_cache["ev_b4"] = (now_b4, (85120.0, 83900.0, 84200.0))

        async def fake_batch(toks, timeout=3.0):
            return {
                "t_b4_y": {"bids": [{"price": "0.95", "size": "200"}], "asks": [{"price": "0.97", "size": "200"}]},
                "t_b4_stale_y": {"bids": [{"price": "0.07", "size": "200"}], "asks": [{"price": "0.085", "size": "200"}]},
            }

        monkeypatch.setattr(d, "fetch_books_batch", fake_batch)
        opps_b4: list = []
        await d.scan_barrier_markets(opps_b4)
        assert any(p["sleeve"] == "B4_TOUCHED_BARRIER_WICK_LOCK" and p["dedupe_key"] == "B4_m_b4" for p in d.open_positions.values())
        assert not any(p["dedupe_key"] == "B4_m_b4_stale" for p in d.open_positions.values())

    asyncio.run(_run_b4())

    # 6. Per-market mid-month `m.startDate` isolation + `is_same_continuous_session` earnings-gap veto
    from src.polymarket_research.barrier_onetouch_svi_engine import parse_hit_event
    from src.polymarket_research.tradfi_sports_zero_fee_engine import is_same_continuous_session

    mid_ev = {
        "id": "ev_oct",
        "startDate": "2026-10-01T05:00:00Z",
        "endDate": "2026-11-01T03:59:59Z",
        "markets": [
            {
                "id": "m_init", "conditionId": "c1", "question": "Will ETH reach $3,000 in October?",
                "groupItemTitle": "↑ 3,000", "clobTokenIds": '["y1","n1"]', "startDate": "2026-10-01T05:00:00Z",
            },
            {
                "id": "m_minted", "conditionId": "c2", "question": "Will ETH reach $2,600 in October?",
                "groupItemTitle": "↑ 2,600", "clobTokenIds": '["y2","n2"]', "startDate": "2026-10-22T16:18:20Z",
                "description": "from the creation of this market through 11:59 PM ET",
            },
        ],
    }
    parsed_hit = {r.market_id: r for r in parse_hit_event(mid_ev, "ETH", "MONTHLY", "ethereum-hit-price-monthly")}
    assert parsed_hit["m_minted"].start_ts > parsed_hit["m_init"].start_ts + 15 * 86400.0
    ny_tz = ZoneInfo("America/New_York")
    t_tue_after = a124.datetime(2026, 10, 27, 23, 0, tzinfo=ny_tz).timestamp()
    t_fri_aft = a124.datetime(2026, 10, 30, 14, 0, tzinfo=ny_tz).timestamp()
    t_fri_close = a124.datetime(2026, 10, 30, 16, 0, tzinfo=ny_tz).timestamp()
    assert not is_same_continuous_session(t_tue_after, t_fri_close, "EQUITY_RTH"), "Multi-day / overnight earnings gap must be vetoed!"
    assert is_same_continuous_session(t_fri_aft, t_fri_close, "EQUITY_RTH"), "Friday same-session RTH final 2h must pass!"


def test_phase2_macro_counting_ctf_aaa_and_maker_anchors(monkeypatch, tmp_path) -> None:
    """Verifies Phase-2 roadmap sleeves (`TW1`, `FED1`, `COND1`, `CTF_OVR`, `GAS1`, `CM_SHOCK`, `AI1`, `D2`, `ZF_MAKER`)."""
    import asyncio
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from src.polymarket_research import alpha_124_shadow_daemon as a124
    from src.polymarket_research.macro_counting_ctf_engine import (
        ALL_FOMC_MASK,
        ALL_OIL_SENATE_MASK,
        build_fomc_truth_table_legs,
        build_oil_senate_truth_table_legs,
        detect_counting_subwindow_boxes,
        detect_d2_12pm_binance_boxes,
        evaluate_ai_elo_ci_lock,
        evaluate_counting_dead_no_locks,
        evaluate_locked_market_reward_carry,
        evaluate_pyth_catalyst_shock,
        find_cross_event_bitmask_boxes,
        parse_aaa_gas_html,
        parse_counting_slate_event,
        walk_equal_shares_overround_bids,
    )
    from src.polymarket_research.redeem_settled_positions import (
        encode_ctf_merge_or_split_calldata,
        inspect_mergeable_complete_set,
    )

    # 1. `TW1`: Counting truncation (`max(gamma_closed_floor, xtracker_total)`) + `48h ⊂ 7d` sub-window box
    ev_7d = {
        "id": "ev_elon_7d",
        "slug": "elon-musk-of-tweets-october-27-november-3",
        "title": "Elon Musk # tweets October 27 - November 3, 2026?",
        "endDate": "2026-11-03T17:00:00Z",
        "description": "from October 27, 2026, 12:00 PM ET to November 3, 2026, 12:00 PM ET",
        "markets": [
            {"id": "c7_0", "closed": True, "groupItemTitle": "<40", "outcomePrices": '["0","1"]'},
            {"id": "c7_1", "conditionId": "0xc71", "groupItemTitle": "40-64", "clobTokenIds": '["t7_y1","t7_n1"]', "feeType": "zero_fees", "rewardsMinSize": 50, "rewardsMaxSpread": 3.5},
            {"id": "c7_2", "conditionId": "0xc72", "groupItemTitle": "65-89", "clobTokenIds": '["t7_y2","t7_n2"]', "feeType": "zero_fees"},
            {"id": "c7_3", "conditionId": "0xc73", "groupItemTitle": "140+", "clobTokenIds": '["t7_yup","t7_nup"]', "feeType": "zero_fees"},
        ],
    }
    ev_48h = {
        "id": "ev_elon_48h",
        "slug": "elon-musk-of-tweets-october-29-october-31",
        "title": "Elon Musk # tweets October 29 - October 31, 2026?",
        "endDate": "2026-10-31T16:00:00Z",
        "description": "from October 29, 2026, 12:00 PM ET to October 31, 2026, 12:00 PM ET",
        "markets": [
            {"id": "c2_0", "conditionId": "0xc20", "groupItemTitle": "<40", "clobTokenIds": '["t2_ylo","t2_nlo"]', "feeType": "zero_fees"},
            {"id": "c2_1", "conditionId": "0xc21", "groupItemTitle": "40-89", "clobTokenIds": '["t2_ym","t2_nm"]', "feeType": "zero_fees"},
            {"id": "c2_2", "conditionId": "0xc22", "groupItemTitle": "90+", "clobTokenIds": '["t2_yup","t2_nup"]', "feeType": "zero_fees"},
        ],
    }
    s7 = parse_counting_slate_event(ev_7d, "elon-tweets", "elonmusk")
    s2 = parse_counting_slate_event(ev_48h, "elon-tweets-48h", "elonmusk")
    assert s7 is not None and s2 is not None and s7.gamma_closed_floor == 40
    xt_map = {
        s7.slug: {"total": 68, "hourly": [(s7.window_start_ts + 3600.0, 55)]},
    }
    v_floor, dead = evaluate_counting_dead_no_locks(s7, xt_map, safety_post_buffer=2)
    assert v_floor == 68 and [b.market_id for b in dead] == ["c7_1"]
    rw = evaluate_locked_market_reward_carry(1.0, 0.975, 0.990, 50.0, 3.5, 0.0)
    assert rw["eligible"] is True and 0.975 <= rw["resting_bid"] <= 0.985
    # With 55 banked posts prior to 48h start, 48h `90+` implies 7d `>= 145 >= 140+`!
    tw_boxes = detect_counting_subwindow_boxes([s7, s2], {"t2_nup": 0.44, "t7_yup": 0.54}, {"elonmusk": xt_map}, max_box_cost_net=0.99)
    assert any(b["box_kind"] == "TW1_UPPER_SUBWINDOW" and abs(b["box_cost_net"] - 0.98) < 1e-6 for b in tw_boxes)

    # 2. `FED1`: Exact 125-state FOMC vs `fed-3-parlay` bitmask dominance
    fomc_evs = [
        {"slug": "fed-decision-in-october-2026", "endDate": "2026-10-29T18:00:00Z", "markets": [
            {"id": "fo_p", "conditionId": "0xfop", "groupItemTitle": "No change", "clobTokenIds": '["fop_y","fop_n"]', "feeType": "zero_fees"},
        ]},
    ]
    par_evs = [
        {"slug": "fed-decisions-oct-jan", "endDate": "2027-01-29T19:00:00Z", "markets": [
            {"id": "fp_1", "conditionId": "0xfp1", "groupItemTitle": "Pause-Pause-Pause", "clobTokenIds": '["fp1_y","fp1_n"]', "feeType": "zero_fees"},
            {"id": "fp_2", "conditionId": "0xfp2", "groupItemTitle": "Hike-Pause-Pause", "clobTokenIds": '["fp2_y","fp2_n"]', "feeType": "zero_fees"},
            {"id": "fp_o", "conditionId": "0xfpo", "groupItemTitle": "Other", "clobTokenIds": '["fpo_y","fpo_n"]', "feeType": "zero_fees"},
        ]},
    ]
    f_legs = build_fomc_truth_table_legs(fomc_evs, par_evs)
    # `YES(OCT:PAUSE)` + `NO(PARLAY:Pause-Pause-Pause)` covers 100% of 125 states (`Pause-Pause-Pause` is a strict subset of `OCT:PAUSE`)!
    f_boxes = find_cross_event_bitmask_boxes(f_legs, {"fop_y": 0.88, "fp1_n": 0.105}, ALL_FOMC_MASK, max_2leg_cost=0.995)
    assert len(f_boxes) == 1 and f_boxes[0]["n_legs"] == 2 and f_boxes[0]["box_cost_net"] == 0.985

    # 3. `COND1`: Exact 9-state Oil x Senate 3-leg partition & `$80` vs `$85` 2-leg dominance
    os_evs = {
        "which-party-will-win-the-senate-in-2026": {"endDate": "2026-11-04T00:00:00Z", "markets": [
            {"id": "sm_d", "conditionId": "0xsmd", "groupItemTitle": "Democratic Party", "clobTokenIds": '["smd_y","smd_n"]', "feeType": "zero_fees"},
        ]},
        "who-wins-the-senate-pending-oil-above-or-below-80-before-the-midterms": {"endDate": "2026-11-04T00:00:00Z", "markets": [
            {"id": "s80_ld", "conditionId": "0x80ld", "groupItemTitle": "Oil < $80; D Senate", "clobTokenIds": '["o80ld_y","o80ld_n"]', "feeType": "zero_fees"},
            {"id": "s80_gd", "conditionId": "0x80gd", "groupItemTitle": "Oil ≥ $80; D Senate", "clobTokenIds": '["o80gd_y","o80gd_n"]', "feeType": "zero_fees"},
        ]},
        "who-wins-the-senate-pending-oil-below-85-before-the-midterms": {"endDate": "2026-11-04T00:00:00Z", "markets": [
            {"id": "s85_ld", "conditionId": "0x85ld", "groupItemTitle": "Oil < $85; D Senate", "clobTokenIds": '["o85ld_y","o85ld_n"]', "feeType": "zero_fees"},
        ]},
    }
    os_legs = build_oil_senate_truth_table_legs(os_evs)
    os_boxes = find_cross_event_bitmask_boxes(
        os_legs,
        {"o80ld_y": 0.01, "o80gd_y": 0.64, "smd_n": 0.335, "o80ld_n": 0.97, "o85ld_y": 0.015},
        ALL_OIL_SENATE_MASK,
        max_2leg_cost=0.995,
        max_3leg_cost=0.995,
    )
    assert any(b["n_legs"] == 3 and abs(b["box_cost_net"] - 0.985) < 1e-6 for b in os_boxes)
    assert any(b["n_legs"] == 2 and abs(b["box_cost_net"] - 0.985) < 1e-6 for b in os_boxes)

    # 4. `CTF_OVERROUND_MINT_SELL` & Polygon CTF Merge/Split ABI selectors
    ovr = walk_equal_shares_overround_bids(
        [
            {"bids": [{"price": "0.52", "size": "50"}], "fee_rate": 0.0, "fee_exponent": 1.0},
            {"bids": [{"price": "0.49", "size": "50"}], "fee_rate": 0.0, "fee_exponent": 1.0},
        ],
        target_mint_budget_usd=40.0,
        min_net_proceeds_per_set=1.004,
    )
    assert ovr["filled"] is True and ovr["net_proceeds_per_set"] == 1.01
    cid_hex = "0x" + "ab" * 32
    from src.polymarket_research import redeem_settled_positions as rsp
    _, cd_m_std = encode_ctf_merge_or_split_calldata(cid_hex, 25.0, is_split=False, neg_risk=False)
    _, cd_s_std = encode_ctf_merge_or_split_calldata(cid_hex, 25.0, is_split=True, neg_risk=False)
    _, cd_m_nr = encode_ctf_merge_or_split_calldata(cid_hex, 25.0, is_split=False, neg_risk=True)
    _, cd_s_nr = encode_ctf_merge_or_split_calldata(cid_hex, 25.0, is_split=True, neg_risk=True)
    assert cd_m_std[:10] == "0x9e7212ad" and cd_s_std[:10] == "0x72ce4275"
    assert cd_m_nr[:10] == "0xb10c5c17" and cd_s_nr[:10] == "0xa3d7da1d"
    monkeypatch.setattr(rsp, "get_token_balance_onchain", lambda addr, tok: 12.5 if tok == "tok_y" else 15.0)
    assert inspect_mergeable_complete_set("0x1111111111111111111111111111111111111111", "tok_y", "tok_n") == 12.5

    # 5. `GAS1`, `CM_SHOCK`, `AI1` staleness guard, `D2_12PM_BINANCE_BOX` & `ZERO_FEE_MAKER_ANCHOR_BOX`
    aaa_html = '<div>Price as of 10/27/26</div><td>$4.2661</td><td>$4.2661</td><td>$4.7966</td><td>$5.1822</td><td>$5.5656</td><td>$3.2856</td><td>$4.2602</td>'
    aaa_p = parse_aaa_gas_html(aaa_html)
    assert aaa_p == {"as_of_date": "2026-10-27", "current_regular": 4.2661, "yesterday_regular": 4.2602}

    # Pre-listed named-month guard: `"in November?"` listed Oct 25 must NOT start before Nov 1 ET
    from src.polymarket_research.tradfi_sports_zero_fee_engine import detect_pyth_calendar_inclusion_boxes, parse_pyth_hit_event
    nov_ev = {"id": "ev_nov", "startDate": "2026-10-25T04:02:00Z", "endDate": "2026-12-01T04:59:59Z", "markets": [{"id": "6172752", "conditionId": "0xnov", "question": "Will WTI Crude Oil (WTI) hit (HIGH) $100 in November?", "groupItemTitle": "↑ $100", "clobTokenIds": '["ny","nn"]', "feeType": "zero_fees", "description": "during a trading session of November 2026, any Pyth 1-minute candle"}]}
    nov_r = parse_pyth_hit_event(nov_ev, "WTI", "MONTHLY", "wti-hit")
    oct28_ts = datetime(2026, 10, 28, 12, 0, tzinfo=ZoneInfo("America/New_York")).timestamp()
    assert len(nov_r) == 1 and nov_r[0].start_ts > oct28_ts
    assert detect_pyth_calendar_inclusion_boxes([{"asset": "WTI", "direction": "UP", "strike": 100.0, "start_ts": oct28_ts - 86400.0, "end_ts": oct28_ts + 86400.0, "ask_no": 0.4, "ask_yes": 0.6, "fee_rate": 0.0}, {"asset": "WTI", "direction": "UP", "strike": 100.0, "start_ts": nov_r[0].start_ts, "end_ts": nov_r[0].end_ts, "ask_no": 0.5, "ask_yes": 0.5, "fee_rate": 0.0}], now_ts=oct28_ts) == []

    ny = ZoneInfo("America/New_York")
    t_eia = datetime(2026, 10, 28, 10, 31, tzinfo=ny).timestamp()  # Wed 10:31 AM ET EIA Crude
    t_off = datetime(2026, 10, 28, 11, 30, tzinfo=ny).timestamp()
    sh_ok = evaluate_pyth_catalyst_shock("WTI", 69.0, 70.2, 71.0, "UP", 3.0, 0.35, t_eia)
    sh_no = evaluate_pyth_catalyst_shock("WTI", 69.0, 70.2, 71.0, "UP", 3.0, 0.35, t_off)
    assert sh_ok["eligible"] is True and sh_ok["catalyst"] == "EIA_1030_PETROLEUM" and sh_ok["side"] == "YES"
    assert sh_no["eligible"] is False

    rows_ai = [{"organization": "Google", "rating": 1395, "rating_q025": 1388, "rating_q975": 1402}, {"organization": "OpenAI", "rating": 1372, "rating_q025": 1365, "rating_q975": 1379}]
    assert evaluate_ai_elo_ci_lock(rows_ai, 1000.0, 50000.0, 36000.0)["eligible"] is False, "Stale >6h snapshot must be rejected!"
    assert evaluate_ai_elo_ci_lock(rows_ai, 48000.0, 50000.0, 36000.0)["eligible"] is True

    d2 = detect_d2_12pm_binance_boxes(
        {"asset": "BTC", "market_id": "h1", "condition_id": "0xh1", "end_ts": 1793203200.0, "up_token": "h_up", "down_token": "h_dn", "fee_rate": 0.07},
        83800.0,
        [{"market_id": "d1", "condition_id": "0xd1", "end_ts": 1793203200.0, "strike": 84400.0, "is_downward": False, "yes_token": "d_y", "no_token": "d_n", "fee_rate": 0.07}],
    )
    assert len(d2) == 1 and d2[0]["leg_a"]["token_id"] == "h_up" and d2[0]["leg_b"]["token_id"] == "d_n"

    # End-to-end `ZERO_FEE_MAKER_ANCHOR_BOX` hedged fill + unhedged scratch in Alpha124ShadowDaemon
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "zfa_st.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "zfa_ldg.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "zfa_opps.json")

    async def _run_zfa():
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_z = 1793220000.0
        la = {"token_id": "za1", "opp_token_id": "za2", "condition_id": "0x1", "side": "YES", "label": "Nets +4.5", "market_id": "m1", "fee_rate": 0.0}
        lb = {"token_id": "zb1", "opp_token_id": "zb2", "condition_id": "0x2", "side": "YES", "label": "Celtics ML", "market_id": "m2", "fee_rate": 0.0}
        bk_a0 = {"bids": [{"price": "0.41", "size": "200"}], "asks": [{"price": "0.45", "size": "200"}]}
        bk_b0 = {"bids": [{"price": "0.54", "size": "300"}], "asks": [{"price": "0.56", "size": "300"}]}
        ok = d.post_zero_fee_maker_anchor_box("SP1_NBA", "NBA", "ZFA_TEST_1", la, lb, bk_a0, bk_b0, now_z + 7200.0, "Nets vs Celtics", now_z)
        assert ok is True and d.pending_zero_fee_maker_anchors["ZFA_TEST_1"]["bid_px"] == 0.42

        async def fake_bks_fill(toks, timeout=3.0):
            return {
                "za1": {"bids": [{"price": "0.41", "size": "200"}], "asks": [{"price": "0.42", "size": "200"}]},
                "zb1": {"bids": [{"price": "0.54", "size": "300"}], "asks": [{"price": "0.56", "size": "300"}]},
            }

        monkeypatch.setattr(d, "fetch_books_batch", fake_bks_fill)
        await d.manage_pending_zero_fee_maker_anchors(now_z + 2.0)
        assert any(p["sleeve"] == "ZERO_FEE_MAKER_ANCHOR_BOX" and p["entry_eff_px_t1000"] == 0.98 for p in d.open_positions.values())

    asyncio.run(_run_zfa())


if __name__ == "__main__":
    test_polymarket_weather_rounding_spec_examples()
    test_metar_parser_speci_and_t_remark()
    test_bucket_bounds_parser()
    test_barrier_and_svi_monotonicity()
    test_exact_twap_lock_engine_math_and_whipsaw_guard()
    print("ALL ALPHA-124 ORACLE & PRICING UNIT TESTS PASSED!")

"""
Comprehensive Adversarial & Regression Proof Suite (`tests/test_riskless_remediation_and_8_new_engines.py`)
covering:
  - Phase 0 (`P0.1`–`P0.5`): Deterministic `0`-parameter riskless integrity remediations & live locks.
  - Phase 1 (`P1.1`–`P1.4`): `CompactCandidateL2Recorder`, `MakerQueueTradeThroughTracker`,
    `HonestClobExecutionKernel` (`FRAGILE_FIRST` vs `3.5s` `deferExec`), and `ZeroLookaheadBacktestHarness`.
  - Phase 2 (`P2.1`–`P2.8`): All 8 net-new mathematically verified riskless profit engines, asserting
    `min_{omega in Omega} V_T(omega) > all_in_cost_usd` across every state AND asserting adversarial
    trap rejection (cancel wipeouts, FX shocks, `SPECI` spikes, non-OT 2H, inverse options, early-resolve carry).
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from src.polymarket_research.cross_venue_connectors import ForecastExIBKRConnector
from src.polymarket_research.cross_venue_l2_and_baskets import (
    LegSpec,
    Level2ExecutionSimulator,
)
from src.polymarket_research.cross_venue_riskless_shadow import (
    CrossVenueRuleVerifier,
    NormalizedBinaryMarket,
    OrderLevel,
    parse_polymarket_gamma_market,
    parse_stx_ontario_market,
    parse_sx_bet_summary_fixture,
)
from src.polymarket_research.honest_riskless_backtester import (
    BacktestEvent,
    CompactCandidateL2Recorder,
    HonestClobExecutionKernel,
    LookaheadViolationError,
    MakerQueueTradeThroughTracker,
    SurvivorshipBiasError,
    ZeroLookaheadBacktestHarness,
)
from src.polymarket_research.macro_counting_ctf_engine import (
    OIL_SENATE_STATES,
    detect_d2_12pm_binance_boxes,
)
from src.polymarket_research.multistrike_svi_scalper import (
    NegRiskBracketSpec,
    StrikeRungSpec,
    build_negrisk_cross_box_bundles,
)
from src.polymarket_research.riskless_expansion_v6_engines import (
    BoundaryTickDominancePair,
    DeribitLinearOptionQuote,
    HalftimeLineLeg,
    PreConvertedNegRiskOutcomeBook,
    PrimaryOracleObservation,
    SubsetNoCandidateOutcome,
    YieldBearingBoxLeg,
    detect_cross_venue_halftime_affine_corridors,
    detect_cross_venue_subset_no_boxes,
    detect_deribit_usdc_vertical_super_replication,
    detect_tail_boundary_001_fee_collapse_boxes,
    evaluate_bond3_multisource_verified_carry,
    evaluate_early_overround_exit_with_forfeited_coupon,
    evaluate_hedged_presplit_maker_ask,
    evaluate_preconverted_nr3_overround,
    evaluate_stx_forecastex_fx_invariant_box,
    evaluate_yield_stacked_locked_box,
)
from src.polymarket_research.riskless_frontier_v4_engine import (
    SubperiodFreezeTracker,
    evaluate_aff1_frozen_subperiod_opportunities,
    parse_affine_game_bundle,
)
from src.polymarket_research.riskless_protocol_v2_expansion import (
    compute_running_metar_extrema,
    detect_dc1_double_chance_1x2_parity,
    detect_w_prune1_metar_slate_arb,
    v2_net_buy_cost_per_share,
)
from src.polymarket_research.same_oracle_dominance_box import walk_equal_shares_dominance_box
from src.polymarket_research.stage_c_zero_loss_velocity import (
    POST_CLINCH_SINGLE_LEG_SLEEVES,
    check_strict_pure_riskless_candidate_gate,
)


def _make_norm_market(
    *,
    venue: str,
    market_id: str,
    title: str = "Will Fed hold rates in December 2026?",
    category: str = "macro",
    collateral_asset: str = "USD",
    yes_asks: tuple[OrderLevel, ...] = (OrderLevel(0.47, 500.0),),
    no_asks: tuple[OrderLevel, ...] = (OrderLevel(0.47, 500.0),),
    yes_bids: tuple[OrderLevel, ...] = (OrderLevel(0.45, 500.0),),
    no_bids: tuple[OrderLevel, ...] = (OrderLevel(0.45, 500.0),),
    end_ts: int = 1_800_000_000,
    quote_ts_ms: int = 1_799_900_000_000,
    fee_rate_bps: float = 0.0,
    fee_enabled: bool = True,
    taker_delay_ms: float = 0.0,
    cancel_rule: str = "VOID",
    oracle_family: str = "federal_reserve_fomc",
    asset: str = "FOMC",
    horizon: str = "event",
    strike_price: float | None = None,
    strike_direction: str = "",
    has_unlisted_draw: bool = False,
    partition_group_id: str = "",
) -> NormalizedBinaryMarket:
    return NormalizedBinaryMarket(
        venue=venue,
        market_id=market_id,
        slug=market_id,
        title=title,
        category=category,
        yes_asks=list(yes_asks),
        yes_bids=list(yes_bids),
        no_asks=list(no_asks),
        no_bids=list(no_bids),
        fee_rate_bps=fee_rate_bps,
        fee_enabled=fee_enabled,
        taker_delay_ms=taker_delay_ms,
        min_shares=5.0,
        asset=asset,
        horizon=horizon,
        oracle_family=oracle_family,
        strike_price=strike_price,
        strike_direction=strike_direction,
        end_ts=end_ts,
        cancel_rule=cancel_rule,
        has_unlisted_draw=has_unlisted_draw,
        tick_size=0.01,
        lot_size=1.0,
        quote_ts_ms=quote_ts_ms,
        collateral_asset=collateral_asset,
        settlement_delay_hours=2.0,
        partition_group_id=partition_group_id,
    )


class TestPhase0DeterministicRemediations(unittest.TestCase):
    """Verifies `P0.1`–`P0.5` riskless integrity remediations."""

    def test_p0_1_stage_c_blocks_non_invariant_single_legs_and_allows_2leg_hook_sp4(self) -> None:
        self.assertNotIn("W1_LOW_TROUGH_LOCK", POST_CLINCH_SINGLE_LEG_SLEEVES)
        self.assertNotIn("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", POST_CLINCH_SINGLE_LEG_SLEEVES)

        harv = SimpleNamespace(enforce_pure_riskless_mode=True)
        rb_cfg = {"strict_pure_riskless_mode": True, "enable_single_leg_maker_bond1": True}

        rej_w1 = check_strict_pure_riskless_candidate_gate(
            harv,
            {"box_type": "SINGLE_LEG_CLINCH", "sleeve_source": "W1_LOW_TROUGH_LOCK", "p_model": 0.9999},
            rb_cfg,
        )
        self.assertIsNotNone(rej_w1)

        rej_sp4_single = check_strict_pure_riskless_candidate_gate(
            harv,
            {
                "box_type": "SINGLE_LEG_CLINCH",
                "sleeve_source": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                "p_model": 0.9999,
            },
            rb_cfg,
        )
        self.assertIsNotNone(rej_sp4_single)

        ok_sp4_corridor = check_strict_pure_riskless_candidate_gate(
            harv,
            {
                "box_type": "DOMINANCE",
                "sleeve_source": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                "k_low": 54.5,
                "k_high": 56.5,
                "token_a": "tok_over_54_5",
                "token_b": "tok_under_56_5",
            },
            rb_cfg,
        )
        self.assertIsNone(ok_sp4_corridor)

    def test_p0_2_dominance_box_min_5_net_shares_and_n1_exact_strike_pin_bridge(self) -> None:
        res_thin = walk_equal_shares_dominance_box(
            [{"price": "0.46", "size": "4.8"}],
            [{"price": "0.46", "size": "100.0"}],
            25.0,
            0.07,
            0.07,
        )
        self.assertFalse(res_thin["filled"])

        rungs = [
            StrikeRungSpec(
                event_id="ev_ms",
                series_slug="btc-multi-strikes-weekly",
                asset="BTC",
                title="BTC Multi Strikes",
                market_id="m_90k",
                condition_id="cond_90k",
                question="Bitcoin above $90,000?",
                strike=90000.0,
                is_downward=False,
                end_ts=1_800_000_000.0,
                yes_token="y90",
                no_token="n90",
                fee_rate=0.07,
            )
        ]
        brackets_no_bridge = [
            NegRiskBracketSpec(
                event_id="ev_nr",
                series_slug="btc-price-brackets",
                asset="BTC",
                title="BTC Brackets",
                market_id="nr_lt90",
                condition_id="cond_lt90",
                question="Bitcoin less than $90,000?",
                bracket_kind="LOWER_TAIL",
                k_low=None,
                k_high=90000.0,
                end_ts=1_800_000_000.0,
                yes_token="nr_y_lt90",
                no_token="nr_n_lt90",
                fee_rate=0.07,
                resolution_source="binance",
            )
        ]
        unbridged = build_negrisk_cross_box_bundles(rungs, brackets_no_bridge, spot=90000.0)
        # `TAIL_LOW_NO` (`NR_NO<90k + MS_NO>90k`) pays $2.00 at `S == 90000` (pin-free),
        # whereas `TAIL_LOW_YES` (`NR_YES<90k + MS_YES>90k`) would pay `$0.00` at `S == 90000` and MUST be blocked!
        self.assertEqual([b for b in unbridged if "TAIL_LOW_YES" in b["bundle_id"]], [])

        brackets_bridged = brackets_no_bridge + [
            NegRiskBracketSpec(
                event_id="ev_nr",
                series_slug="btc-price-brackets",
                asset="BTC",
                title="BTC Brackets",
                market_id="nr_90_92",
                condition_id="cond_90_92",
                question="Bitcoin between $90,000 and $92,000?",
                bracket_kind="RANGE",
                k_low=90000.0,
                k_high=92000.0,
                end_ts=1_800_000_000.0,
                yes_token="nr_y_90_92",
                no_token="nr_n_90_92",
                fee_rate=0.07,
                resolution_source="binance",
            )
        ]
        bridged = build_negrisk_cross_box_bundles(rungs, brackets_bridged, spot=90500.0)
        safe_bridges = [b for b in bridged if "TAIL_LOW_PIN_SAFE_BRIDGE" in b["bundle_id"]]
        self.assertEqual(len(safe_bridges), 1)
        self.assertTrue(safe_bridges[0]["pin_free_verified"])

    def test_p0_3_oil_18_states_d2_60s_gap_aff1_480s_speci_and_dc1_cancel_guards(self) -> None:
        self.assertEqual(len(OIL_SENATE_STATES), 18)
        self.assertIn(("LT80", "GE85", "DEM"), OIL_SENATE_STATES)

        # 1h Up/Down market (`end_ts = 1_700_000_000`, offset `+0s` -> fixes at `11:59:59.999` / `end_ts`),
        # vs 12:00 PM `1m`-close market (`end_ts = 1_700_000_000`, offset `+60s` -> fixes `60s` later!) MUST be blocked!
        hourly_wrong = {
            "asset": "BTC",
            "market_id": "h1",
            "condition_id": "ch1",
            "end_ts": 1_700_000_000.0,
            "up_token": "h_up",
            "down_token": "h_dn",
            "rules_text": "Resolves based on the 1h BTCUSDT candle from 11:00 to 12:00 ET.",
        }
        term_wrong = [
            {
                "market_id": "t1",
                "condition_id": "ct1",
                "strike": 95500.0,
                "end_ts": 1_700_000_000.0,
                "yes_token": "t_y",
                "no_token": "t_n",
                "rules_text": "Resolves based on the Binance 1 minute candle for 12:00 PM ET.",
            }
        ]
        self.assertEqual(detect_d2_12pm_binance_boxes(hourly_wrong, 95000.0, term_wrong), [])

        aff_ev = {
            "id": "ev_nba_1",
            "slug": "nba-bos-nyk-2026-11-10",
            "title": "Celtics vs. Knicks",
            "startTime": "2026-11-10T23:00:00Z",
            "markets": [
                {
                    "id": "m_ht_narrow",
                    "question": "1H Total O/U 110.5",
                    "outcomes": json.dumps(["Over", "Under"]),
                    "clobTokenIds": json.dumps(["y_ht", "n_ht"]),
                    "sportsMarketType": "first_half_totals",
                    "line": 110.5,
                    "active": True,
                    "closed": False,
                }
            ],
        }
        aff_bundle = parse_affine_game_bundle([aff_ev])[0]
        ft = SubperiodFreezeTracker()
        ht_summary = {
            "state": "in",
            "completed": False,
            "is_halftime": True,
            "period": 2,
            "away_score": 56,
            "home_score": 56,
            "linescores": {"away": {1: 28, 2: 28}, "home": {1: 28, 2: 28}},
        }
        # First observation at t=1000s, second at t=1180s (`180s < 480s` Secaucus review window for narrow 1.5pt margin!)
        evaluate_aff1_frozen_subperiod_opportunities(aff_bundle, ht_summary, {"y_ht": 0.92, "n_ht": 0.08}, ft, 1000.0, espn_game_id="g_ht")
        res_180 = evaluate_aff1_frozen_subperiod_opportunities(aff_bundle, ht_summary, {"y_ht": 0.92, "n_ht": 0.08}, ft, 1180.0, espn_game_id="g_ht")
        self.assertEqual(res_180["single_leg_locks"], [])

        metars = [
            "METAR KJFK 101851Z 18010KT 10SM CLR 20/10 A3000 RMK AO2 T02000100",
            "SPECI KJFK 101920Z 18012KT 10SM CLR 24/10 A2999 RMK AO2 T02390100",
            "METAR KJFK 102351Z 18008KT 10SM CLR 18/09 A3002 RMK AO2 T01780089",
        ]
        ext = compute_running_metar_extrema(metars, unit="F", station_icao="KJFK")
        self.assertIsNotNone(ext)
        assert ext is not None
        self.assertGreaterEqual(ext["speci_running_high_ceil"], 75)
        brackets = [
            {
                "market_id": "b_68_69",
                "low": 68.0,
                "high": 69.0,
                "yes_token_id": "y68",
                "no_token_id": "n68",
                "yes_ask": 0.90,
                "yes_ask_size": 100.0,
                "no_ask": 0.12,
                "no_ask_size": 100.0,
            }
        ]
        pruned = detect_w_prune1_metar_slate_arb(
            brackets,
            metars,
            station_icao="KJFK",
            unit="F",
            metric="HIGH",
            local_hour_minute=(23, 55),
        )
        solar_locks = [p for p in pruned if p.get("sleeve") == "W_SOLAR1_POST_2351_LOCK"]
        self.assertEqual(solar_locks, [])

        dc_res = detect_dc1_double_chance_1x2_parity(
            one_x2={
                "HOME": {"yes_token_id": "h_y", "no_token_id": "h_n", "yes_ask": 0.44, "yes_ask_size": 100.0, "neg_risk": True},
                "DRAW": {"yes_token_id": "d_y", "no_token_id": "d_n", "yes_ask": 0.28, "yes_ask_size": 100.0, "neg_risk": True},
                "AWAY": {"yes_token_id": "a_y", "no_token_id": "a_n", "yes_ask": 0.28, "yes_ask_size": 100.0, "neg_risk": True},
            },
            double_chance={
                "X2": {"yes_token_id": "x2_y", "no_token_id": "x2_n", "yes_ask": 0.48, "yes_ask_size": 100.0, "neg_risk": False},
            },
        )
        self.assertEqual(dc_res, [])

        v2_c = v2_net_buy_cost_per_share(0.50, 0.07, 1.0)
        self.assertAlmostEqual(v2_c, 0.50 / (1.0 - 0.07 * 0.50), places=6)

    def test_p0_4_cross_venue_sxbet_draw_stx_cad_fx_deribit_corridor_and_forecastex_csv(self) -> None:
        nhl_sx = parse_sx_bet_summary_fixture(
            {
                "teamOneName": "Maple Leafs",
                "teamTwoName": "Bruins",
                "leagueLabel": "NHL",
                "gameTime": 1_800_000_000,
                "markets": [
                    {
                        "marketHash": "0xsx_nhl_reg",
                        "type": 1,
                        "outcomeOneName": "Maple Leafs",
                        "outcomeTwoName": "Bruins",
                        "bestOddsOutcomeOne": str(int(0.45 * (10**20))),
                        "bestOddsOutcomeTwo": str(int(0.45 * (10**20))),
                    }
                ],
            },
            sport_label="Ice Hockey",
        )
        self.assertEqual(len(nhl_sx), 1)
        self.assertTrue(nhl_sx[0].has_unlisted_draw)

        stx_m = parse_stx_ontario_market(
            {
                "id": "stx_nba_1",
                "team_a": "Raptors",
                "team_b": "Celtics",
                "sport": "nba",
                "end_ts": 1_800_000_000,
                "yes_asks": [[0.49, 200.0]],
                "no_asks": [[0.49, 200.0]],
            }
        )
        self.assertIsNotNone(stx_m)
        assert stx_m is not None
        self.assertEqual(stx_m.collateral_asset, "CAD")
        fex_m = _make_norm_market(
            venue="forecastex",
            market_id="fex_fed_1",
            yes_asks=(OrderLevel(0.50, 200.0),),
            no_asks=(OrderLevel(0.50, 200.0),),
            quote_ts_ms=stx_m.quote_ts_ms,
        )
        sim = Level2ExecutionSimulator()
        eval_false = sim.evaluate_basket(
            basket_id="false_cad_eq_usd",
            basket_type="BINARY_PAIR",
            legs=(LegSpec(fex_m, "YES"), LegSpec(stx_m, "NO")),
            target_notional_usd=50.0,
            now_ms=stx_m.quote_ts_ms,
        )
        self.assertFalse(eval_false.simulated_executable.executable)

        # Deribit 30m TWAP vs spot binary enforces >= 150 bps strike corridor (`50 bps` rejected!)
        der_m = _make_norm_market(
            venue="deribit",
            market_id="der_btc_100k",
            title="BTC above 100000 at 08:00 UTC",
            category="crypto",
            asset="BTC",
            horizon="daily",
            oracle_family="deribit_30m_twap",
            strike_price=100_000.0,
            strike_direction="ABOVE",
        )
        lim_m = _make_norm_market(
            venue="limitless",
            market_id="lim_btc_100500",
            title="BTC above 100500 at 08:00 UTC",
            category="crypto",
            asset="BTC",
            horizon="daily",
            oracle_family="pyth_spot",
            strike_price=100_500.0,
            strike_direction="ABOVE",
        )
        ver = CrossVenueRuleVerifier().verify_pair(der_m, lim_m, side_a="NO", side_b="YES", price_a=0.45, price_b=0.45)
        self.assertFalse(ver.passed)

        # ForecastEx `YXLBT` touch-barrier classified as `crypto_barrier` & cumulative strikes clear `partition_group_id`
        summary_csv = (
            "product_id,product_name,product_category\n"
            "YXLBT,Bitcoin Low Touch Barrier,Cryptocurrency\n"
            "FEDDEC,Fed Funds Target Rate,Economic Indicators\n"
        )
        prices_csv = (
            "event_contract,subtype,expiration_date,settlement_price,open_interest\n"
            "YXLBT_20261231_80000,YES,2026-12-31T16:00:00Z,0.35,500\n"
            "YXLBT_20261231_80000,NO,2026-12-31T16:00:00Z,0.65,500\n"
            "FEDDEC_20261218_4.00,YES,2026-12-18T19:00:00Z,0.60,800\n"
            "FEDDEC_20261218_4.00,NO,2026-12-18T19:00:00Z,0.40,800\n"
        )
        parsed_fex, _, _ = ForecastExIBKRConnector.parse_public_portal_csvs(
            summary_csv=summary_csv,
            prices_csv=prices_csv,
            now_s=1_790_000_000,
        )
        barrier_mkts = [m for m in parsed_fex if "YXLBT" in m.market_id]
        self.assertTrue(barrier_mkts and all(m.category == "crypto_barrier" for m in barrier_mkts))
        fed_mkts = [m for m in parsed_fex if "FEDDEC" in m.market_id]
        self.assertTrue(fed_mkts and all(m.partition_group_id == "" for m in fed_mkts))

        pm_weather = parse_polymarket_gamma_market(
            {
                "id": "pm_w_1",
                "question": "Highest temperature in NYC on Nov 12?",
                "category": "weather",
                "clobTokenIds": '["tok_y", "tok_n"]',
                "outcomePrices": '["0.50", "0.50"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.05, "exponent": 2},
                "endDate": "2026-11-12T23:59:00Z",
            }
        )
        self.assertIsNotNone(pm_weather)
        assert pm_weather is not None
        self.assertGreaterEqual(pm_weather.fee_rate_bps, 500.0)

    def test_p0_5_zero_pytest_current_test_branches_and_live_safety_locks_intact(self) -> None:
        src_dir = Path(__file__).resolve().parents[1] / "src" / "polymarket_research"
        offending = [
            p.name for p in sorted(src_dir.glob("*.py")) if "PYTEST_CURRENT_TEST" in p.read_text(encoding="utf-8")
        ]
        self.assertEqual(offending, [], f"Forbidden PYTEST_CURRENT_TEST found in: {offending}")

        cfg_path = Path(__file__).resolve().parents[1] / "config" / "polymarket_strategy_and_risk.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        rb = cfg.get("riskless_boxes", cfg)
        self.assertTrue(rb.get("strict_pure_riskless_mode"))
        self.assertTrue(rb.get("strict_zero_legging_pre_split_lock"))
        self.assertFalse(rb.get("enable_pre_split_overround_gun"))


class TestPhase1HonestBacktesterAndRecorder(unittest.TestCase):
    """Verifies `P1.1`–`P1.4` honest event-driven backtester & candidate-triggered recorder."""

    def test_compact_candidate_l2_recorder_ring_buffer_and_disk_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rec = CompactCandidateL2Recorder(
                Path(tmp),
                trigger_gross_box_max=1.035,
                pre_trigger_ring_max_frames=4,
                post_trigger_capture_ms=30_000,
                flush_batch_frames=8,
                max_daily_bytes=65_536,
            )
            m_wide = _make_norm_market(
                venue="polymarket",
                market_id="m_cand",
                collateral_asset="USDC",
                yes_asks=(OrderLevel(0.55, 100.0),),
                no_asks=(OrderLevel(0.55, 100.0),),
                yes_bids=(OrderLevel(0.44, 100.0),),
                no_bids=(OrderLevel(0.44, 100.0),),
                quote_ts_ms=1_700_000_000_000,
            )
            self.assertEqual(rec.observe_markets([m_wide], now_ms=1_700_000_000_000), 0)

            rec.record_trade_print(
                venue="polymarket",
                market_slug="m_cand",
                side="YES",
                price=0.49,
                shares=25.0,
                ts_ms=1_700_000_000_500,
            )
            m_trig = _make_norm_market(
                venue="polymarket",
                market_id="m_cand",
                collateral_asset="USDC",
                yes_asks=(OrderLevel(0.49, 100.0),),
                no_asks=(OrderLevel(0.52, 100.0),),
                yes_bids=(OrderLevel(0.47, 100.0),),
                no_bids=(OrderLevel(0.47, 100.0),),
                quote_ts_ms=1_700_000_001_000,
            )
            emitted = rec.observe_markets([m_trig], now_ms=1_700_000_001_000)
            self.assertEqual(emitted, 2)  # 1 pre-trigger ring frame + 1 triggered frame!
            out_file = rec.flush()
            self.assertIsNotNone(out_file)
            assert out_file is not None
            frames = CompactCandidateL2Recorder.load_frames(out_file)
            self.assertEqual(len(frames), 2)
            self.assertEqual(len(frames[1].recent_trades), 1)

    def test_maker_queue_trade_through_tracker_fifo_and_post_only_guard(self) -> None:
        tracker = MakerQueueTradeThroughTracker()
        mkt = _make_norm_market(
            venue="stx_ontario",
            market_id="m1",
            collateral_asset="CAD",
            yes_bids=(OrderLevel(0.48, 50.0),),
            yes_asks=(OrderLevel(0.50, 50.0),),
        )
        # Crossing best ask (`0.50`) returns `None` (`postOnly` rejection)
        self.assertIsNone(
            tracker.place_maker_bid(
                order_id="bad_cross",
                market=mkt,
                side="YES",
                bid_price=0.50,
                order_shares=20.0,
                placed_ts_ms=1000,
            )
        )

        ord_ok = tracker.place_maker_bid(
            order_id="ord_1",
            market=mkt,
            side="YES",
            bid_price=0.48,
            order_shares=20.0,
            placed_ts_ms=1000,
        )
        self.assertIsNotNone(ord_ok)
        # 40 shares trade at `0.48` -> clears 40 of 50 queue_ahead -> 0 shares filled for us!
        fills_1 = tracker.observe_trade_print(
            venue="stx_ontario",
            market_slug="m1",
            outcome_side="YES",
            trade_price=0.48,
            trade_shares=40.0,
            ts_ms=1200,
        )
        self.assertEqual(fills_1, {})
        st1 = tracker.get_order("ord_1")
        assert st1 is not None
        self.assertAlmostEqual(st1.remaining_queue_ahead_shares, 10.0)

        # Next 35 shares trade at `0.48` -> clears remaining 10 queue_ahead + fills all 20 of our shares!
        fills_2 = tracker.observe_trade_print(
            venue="stx_ontario",
            market_slug="m1",
            outcome_side="YES",
            trade_price=0.48,
            trade_shares=35.0,
            ts_ms=1500,
        )
        self.assertAlmostEqual(fills_2["ord_1"], 20.0)
        self.assertTrue(st1.is_fully_filled)

    def test_honest_execution_kernel_fragile_first_zero_bleed_vs_parallel_defer_exec_bleed(self) -> None:
        m_solid = _make_norm_market(
            venue="polymarket",
            market_id="pm_solid",
            collateral_asset="USDC",
            yes_asks=(OrderLevel(0.46, 200.0),),
            yes_bids=(OrderLevel(0.44, 200.0),),
            fee_rate_bps=700.0,
            taker_delay_ms=0.0,
        )
        m_fragile = _make_norm_market(
            venue="sx_bet",
            market_id="sx_fragile",
            collateral_asset="USDC",
            no_asks=(OrderLevel(0.46, 200.0),),
            no_bids=(OrderLevel(0.44, 200.0),),
            taker_delay_ms=3000.0,  # 3.0s live speed-bump!
        )
        m_fragile_raced = NormalizedBinaryMarket(**{**m_fragile.__dict__, "no_asks": [OrderLevel(0.58, 200.0)]})
        m_solid_post_defer = NormalizedBinaryMarket(**{**m_solid.__dict__, "yes_bids": [OrderLevel(0.35, 200.0)]})

        def lookup(venue: str, slug: str, ts_ms: int) -> NormalizedBinaryMarket | None:
            if slug == "sx_fragile":
                return m_fragile_raced if ts_ms >= 2000 else m_fragile
            if slug == "pm_solid":
                return m_solid_post_defer if ts_ms >= 4000 else m_solid
            return None

        kernel = HonestClobExecutionKernel(defer_exec_settlement_ms=3500)
        # FRAGILE_FIRST dispatches slower `sx_fragile` first -> FOK kills cleanly -> `$0.00` unwind bleed!
        res_ff = kernel.execute_two_leg_taker_box(
            decision_ts_ms=1000,
            leg_a_venue="polymarket",
            leg_a_slug="pm_solid",
            leg_a_side="YES",
            leg_a_limit_px=0.47,
            leg_b_venue="sx_bet",
            leg_b_slug="sx_fragile",
            leg_b_side="NO",
            leg_b_limit_px=0.47,
            target_net_shares=20.0,
            unit_guaranteed_payout_usd=1.0,
            book_lookup_fn=lookup,
            dispatch_mode="FRAGILE_FIRST",
        )
        self.assertEqual(res_ff.status, "LEG1_FOK_KILLED_CLEANLY")
        self.assertEqual(res_ff.unwind_bleed_usd, 0.0)

        # PARALLEL fills `pm_solid` at `t=1050ms`, misses `sx_fragile` at `t=4110ms`, waits `3,500ms` `deferExec`, and bleeds!
        res_par = kernel.execute_two_leg_taker_box(
            decision_ts_ms=1000,
            leg_a_venue="polymarket",
            leg_a_slug="pm_solid",
            leg_a_side="YES",
            leg_a_limit_px=0.47,
            leg_b_venue="sx_bet",
            leg_b_slug="sx_fragile",
            leg_b_side="NO",
            leg_b_limit_px=0.47,
            target_net_shares=20.0,
            unit_guaranteed_payout_usd=1.0,
            book_lookup_fn=lookup,
            dispatch_mode="PARALLEL",
        )
        self.assertEqual(res_par.status, "LEG2_MISSED_DEFER_EXEC_UNWOUND")
        self.assertGreater(res_par.unwind_bleed_usd, 2.0)

    def test_zero_lookahead_harness_enforces_causality_and_blocks_survivorship_bias(self) -> None:
        with self.assertRaises(SurvivorshipBiasError):
            ZeroLookaheadBacktestHarness.validate_dataset_no_survivorship_bias(
                [{"market_id": f"m{i}", "umaResolutionStatus": "resolved"} for i in range(6)]
            )

        harness = ZeroLookaheadBacktestHarness()
        m1 = _make_norm_market(venue="polymarket", market_id="m_t", collateral_asset="USDC", quote_ts_ms=1000)
        events = [
            BacktestEvent(visible_ts_ms=1000, source_event_ts_ms=980, event_type="BOOK_SNAPSHOT", payload=m1, seq_no=1),
            BacktestEvent(
                visible_ts_ms=1500,
                source_event_ts_ms=1490,
                event_type="SCOREBOARD_UPDATE",
                payload={"matchup_key": "NBA_BOS_NYK", "is_halftime": True, "clock_sec": 0.0, "halftime_started_ts_ms": 1200, "scheduled_intermission_sec": 900.0},
                seq_no=2,
            ),
        ]

        def strat(h: ZeroLookaheadBacktestHarness, ts_ms: int, books: object) -> list[dict]:
            with self.assertRaises(LookaheadViolationError):
                h.get_visible_book("polymarket", "m_t", ts_ms + 250)
            if ts_ms == 1500:
                self.assertTrue(h.verify_halftime_state_confirmed("NBA_BOS_NYK"))
            return []

        rep = harness.run(events, strat)
        self.assertTrue(rep.zero_lookahead_verified)
        self.assertEqual(rep.events_processed, 2)


class TestPhase2AllEightNewRisklessEngines(unittest.TestCase):
    """Proves state-by-state payoff dominance AND trap rejection for all 8 net-new riskless engines (`P2.1`–`P2.8`)."""

    def _assert_strict_dominance(self, opp: object) -> None:
        table = getattr(opp, "state_payoff_table")
        cost = getattr(opp, "all_in_cost_usd")
        self.assertTrue(table)
        for state_name, payout in table.items():
            self.assertGreater(
                payout,
                cost,
                f"State {state_name} payout {payout} failed strict dominance over cost {cost}",
            )

    def test_engine_1_xv_subset_no_box_m2_universal_cancel_proof_and_m3_cancel_trap_guard(self) -> None:
        cands = [
            SubsetNoCandidateOutcome(
                "FAV_A",
                _make_norm_market(venue="forecastex", market_id="fa", no_asks=(OrderLevel(0.45, 300.0),)),
                cancel_payout_mode="50_50",
            ),
            SubsetNoCandidateOutcome(
                "FAV_B",
                _make_norm_market(
                    venue="polymarket",
                    market_id="fb",
                    collateral_asset="USDC",
                    no_asks=(OrderLevel(0.46, 300.0),),
                    fee_rate_bps=400.0,
                ),
                cancel_payout_mode="50_50",
            ),
            SubsetNoCandidateOutcome(
                "CAND_C",
                _make_norm_market(venue="forecastex", market_id="fc", no_asks=(OrderLevel(0.82, 300.0),)),
                cancel_payout_mode="50_50",
            ),
        ]
        opps = detect_cross_venue_subset_no_boxes(
            "partition_election",
            cands,
            event_cancel_exempt=False,
            subset_sizes=(2, 3),
            target_notional_usd=50.0,
        )
        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0].metadata["subset_size_m"], 2)
        self._assert_strict_dominance(opps[0])
        self.assertGreater(opps[0].best_case_payout_usd - opps[0].worst_case_payout_usd, 40.0)

    def test_engine_2_tail_boundary_001_arb_parabolic_fee_collapse_and_notional_floor(self) -> None:
        pair = BoundaryTickDominancePair(
            pair_id="btc_deep_itm_corridor",
            pair_type="NESTED_STRIKE",
            oracle_signature="chainlink_btc_usd_15m",
            expiry_ts=1_800_000_900.0,
            leg_a_token_id="tok_yes_94k",
            leg_a_label="BTC >= 94000",
            leg_a_asks=(OrderLevel(0.966, 200.0),),
            leg_b_token_id="tok_no_94500",
            leg_b_label="BTC < 94500",
            leg_b_asks=(OrderLevel(0.025, 200.0),),
            fee_rate=0.07,
            fee_exponent=1.0,
            strike_low=94_000.0,
            strike_high=94_500.0,
        )
        opps = detect_tail_boundary_001_fee_collapse_boxes([pair], target_box_notional_usd=45.0)
        self.assertEqual(len(opps), 1)
        opp = opps[0]
        self._assert_strict_dominance(opp)
        self.assertGreater(opp.metadata["fee_compression_multiple"], 7.5)
        self.assertGreaterEqual(opp.legs[1]["maker_amount_usd"], 1.00)

    def test_engine_3_bond3_multisource_dead_split_unlocks_swept_winner_and_blocks_speci_conflict(self) -> None:
        obs_ok = [
            PrimaryOracleObservation("mlb_statsapi", True, "YES", post_final_elapsed_sec=1200.0),
            PrimaryOracleObservation("espn_official", True, "YES", post_final_elapsed_sec=1180.0),
        ]
        opp = evaluate_bond3_multisource_verified_carry(
            market_id="mlb_ws_g7",
            category="mlb",
            uma_proposed_outcome="YES",
            uma_status="proposed",
            is_whitelisted_proposer=True,
            remaining_challenge_sec=2400.0,
            winner_asks=(OrderLevel(0.999, 500.0),),
            winner_bids=(OrderLevel(0.985, 500.0),),
            dead_loser_bids=(OrderLevel(0.020, 80.0),),
            observations=obs_ok,
            fee_rate=0.03,
            target_notional_usd=60.0,
        )
        self.assertIsNotNone(opp)
        assert opp is not None
        self.assertEqual(opp.metadata["entry_mode"], "DEAD_SIDE_SPLIT_SELL")
        self._assert_strict_dominance(opp)

        opp_bad = evaluate_bond3_multisource_verified_carry(
            market_id="nyc_temp",
            category="weather",
            uma_proposed_outcome="YES",
            uma_status="proposed",
            is_whitelisted_proposer=True,
            remaining_challenge_sec=1800.0,
            winner_asks=(OrderLevel(0.97, 200.0),),
            winner_bids=(OrderLevel(0.96, 200.0),),
            dead_loser_bids=(OrderLevel(0.03, 100.0),),
            observations=[
                PrimaryOracleObservation("aviationweather", True, "YES", 4000.0, has_speci_or_cor_conflict=True),
                PrimaryOracleObservation("iem_asos", True, "YES", 4000.0),
            ],
        )
        self.assertIsNone(opp_bad)

    def test_engine_4_xv_fx_invariant_cad_usd_box_ca_on_legal_and_void_fx_trap_guard(self) -> None:
        stx = _make_norm_market(
            venue="stx_ontario",
            market_id="stx_boc_cut",
            collateral_asset="CAD",
            yes_asks=(OrderLevel(0.45, 500.0),),
        )
        fex = _make_norm_market(
            venue="forecastex",
            market_id="fex_boc_cut",
            collateral_asset="USD",
            no_asks=(OrderLevel(0.50, 500.0),),
        )
        opp = evaluate_stx_forecastex_fx_invariant_box(
            pair_id="boc_dec_2026",
            stx_market=stx,
            stx_side="YES",
            stx_execution_style="PASSIVE_MAKER",
            forecastex_market=fex,
            forecastex_side="NO",
            event_cancel_exempt=True,
            target_usd_shares=100.0,
        )
        self.assertIsNotNone(opp)
        assert opp is not None
        self.assertIn("CA-ON-LEGAL", opp.jurisdiction_tags)
        self.assertGreater(opp.metadata["cad_to_usd_share_ratio"], 1.38)
        self._assert_strict_dominance(opp)

        opp_void_trap = evaluate_stx_forecastex_fx_invariant_box(
            pair_id="cancelable_friendly_match",
            stx_market=_make_norm_market(
                venue="stx_ontario", market_id="stx_fr", collateral_asset="CAD", yes_asks=(OrderLevel(0.46, 500.0),)
            ),
            stx_side="YES",
            stx_execution_style="PASSIVE_MAKER",
            forecastex_market=_make_norm_market(
                venue="forecastex", market_id="fex_fr", collateral_asset="USD", no_asks=(OrderLevel(0.51, 500.0),)
            ),
            forecastex_side="NO",
            fx_shock_band_frac=0.08,
            event_cancel_exempt=False,
            target_usd_shares=100.0,
        )
        self.assertIsNone(opp_void_trap)

    def test_engine_5_deribit_usdc_vertical_super_replication_and_inverse_rejection(self) -> None:
        exp_ts = 1_800_000_000
        bin_mkt = _make_norm_market(
            venue="forecastex",
            market_id="fex_btc_100k_08utc",
            category="crypto",
            collateral_asset="USD",
            no_asks=(OrderLevel(0.45, 300.0),),
            yes_asks=(OrderLevel(0.56, 300.0),),
            end_ts=exp_ts,
        )
        opts = [
            DeribitLinearOptionQuote("BTC_USDC-97000-C", "BTC_USDC", "USDC", "C", 97_000.0, float(exp_ts), 2100.0, 5.0, 2110.0, 5.0, 99_000.0),
            DeribitLinearOptionQuote("BTC_USDC-98000-C", "BTC_USDC", "USDC", "C", 98_000.0, float(exp_ts), 1650.0, 5.0, 1665.0, 5.0, 99_000.0),
            DeribitLinearOptionQuote("BTC-97000-C", "BTC_USD", "BTC", "C", 97_000.0, float(exp_ts), 100.0, 5.0, 110.0, 5.0, 99_000.0),
        ]
        opps = detect_deribit_usdc_vertical_super_replication(
            binary_market=bin_mkt,
            binary_strike=100_000.0,
            deribit_options=opts,
            cross_oracle_basis_bps=150.0,
            target_units=50.0,
        )
        self.assertEqual(len(opps), 1)
        self._assert_strict_dominance(opps[0])
        self.assertEqual(opps[0].metadata["polish_middle_width_usd"], 2000.0)

    def test_engine_6_xv_halftime_freeze_affine_corridor_and_non_ot_2h_trap_guard(self) -> None:
        fg_leg = HalftimeLineLeg(
            leg_id="fg_o220_5",
            period_scope="FG",
            line_kind="TOTAL",
            direction="OVER",
            line_value=220.5,
            includes_overtime=True,
            live_betting_delay_ms=0,
            market=_make_norm_market(venue="forecastex", market_id="fg_tot", yes_asks=(OrderLevel(0.46, 200.0),)),
        )
        h2_ok = HalftimeLineLeg(
            leg_id="h2_u112_5",
            period_scope="2H",
            line_kind="TOTAL",
            direction="UNDER",
            line_value=112.5,
            includes_overtime=True,
            live_betting_delay_ms=0,
            market=_make_norm_market(venue="stx_ontario", market_id="h2_tot", collateral_asset="CAD", yes_asks=(OrderLevel(0.45, 400.0),)),
        )
        opps = detect_cross_venue_halftime_affine_corridors(
            game_id="nba_bos_nyk",
            sport="nba",
            is_halftime=True,
            game_clock_sec=0.0,
            elapsed_halftime_sec=500.0,
            remaining_halftime_sec=300.0,
            confirmed_1h_home_score=58,
            confirmed_1h_away_score=52,
            fg_legs=[fg_leg],
            h2_legs=[h2_ok],
            target_usd_shares=40.0,
        )
        self.assertEqual(len(opps), 1)
        self._assert_strict_dominance(opps[0])
        self.assertEqual(opps[0].metadata["polish_middle_integer_width"], 2)

        h2_no_ot = HalftimeLineLeg(**{**h2_ok.__dict__, "includes_overtime": False})
        self.assertEqual(
            detect_cross_venue_halftime_affine_corridors(
                game_id="nba_bos_nyk",
                sport="nba",
                is_halftime=True,
                game_clock_sec=0.0,
                elapsed_halftime_sec=500.0,
                remaining_halftime_sec=300.0,
                confirmed_1h_home_score=58,
                confirmed_1h_away_score=52,
                fg_legs=[fg_leg],
                h2_legs=[h2_no_ot],
            ),
            [],
        )

    def test_engine_7_preconverted_nr3_and_hedged_presplit_maker_ask(self) -> None:
        outcomes = [
            PreConvertedNegRiskOutcomeBook("BRACKET_A", yes_bids=(OrderLevel(0.56, 80.0),), yes_asks=(OrderLevel(0.58, 80.0),), fee_rate=0.04),
            PreConvertedNegRiskOutcomeBook("BRACKET_B", yes_bids=(OrderLevel(0.47, 60.0),), yes_asks=(OrderLevel(0.49, 60.0),), fee_rate=0.04),
            PreConvertedNegRiskOutcomeBook("TAIL_LOTTERY_C", yes_bids=(OrderLevel(0.02, 50.0),), yes_asks=(OrderLevel(0.04, 50.0),), fee_rate=0.04),
        ]
        opp_nr3 = evaluate_preconverted_nr3_overround(
            slate_id="closed_fomc_slate",
            outcomes=outcomes,
            settled_inventory_shares=20.0,
            is_augmented_other=False,
            onchain_question_count=3,
        )
        self.assertIsNotNone(opp_nr3)
        assert opp_nr3 is not None
        self._assert_strict_dominance(opp_nr3)
        self.assertEqual(opp_nr3.metadata["free_retained_lottery_outcomes"], ["TAIL_LOTTERY_C"])

        self.assertIsNone(
            evaluate_preconverted_nr3_overround(
                slate_id="aug_slate",
                outcomes=outcomes,
                settled_inventory_shares=20.0,
                is_augmented_other=True,
                onchain_question_count=3,
            )
        )

        opp_mkr = evaluate_hedged_presplit_maker_ask(
            market_id="btc_15m_candle",
            maker_yes_ask_price=0.53,
            complement_no_bids=(OrderLevel(0.495, 60.0),),
            settled_split_shares=15.0,
            fee_rate=0.07,
            live_enabled=False,
        )
        self.assertIsNotNone(opp_mkr)
        assert opp_mkr is not None
        self.assertFalse(opp_mkr.live_eligible)
        self._assert_strict_dominance(opp_mkr)

    def test_engine_8_yield_stacked_carry_box_and_early_overround_exit_forfeited_coupon_guard(self) -> None:
        # Gross box costs `$1.004` (`0.502 + 0.502`, `$0.00` direct ForecastEx exchange fee), negative on price alone (`-$0.405`),
        # while 120-day contractual `FFR - 0.50%` (`3.83%` -> `3.33%` after 50 bps rate-cut stress) adds `+$1.095` coupon -> `+$0.69` net!
        fex_yes = YieldBearingBoxLeg(
            market=_make_norm_market(venue="forecastex", market_id="fex_y", yes_asks=(OrderLevel(0.502, 500.0),)),
            side="YES",
            contractual_apy=0.0383,
            rate_cut_stress_haircut_apy=0.0050,
            override_taker_fee_per_contract_usd=0.0,
        )
        fex_no = YieldBearingBoxLeg(
            market=_make_norm_market(venue="forecastex", market_id="fex_y", no_asks=(OrderLevel(0.502, 500.0),)),
            side="NO",
            contractual_apy=0.0383,
            rate_cut_stress_haircut_apy=0.0050,
            override_taker_fee_per_contract_usd=0.0,
        )
        opp = evaluate_yield_stacked_locked_box(
            box_id="fex_120d_rate_carry",
            leg_a=fex_yes,
            leg_b=fex_no,
            min_guaranteed_hold_days=120.0,
            can_resolve_early=False,
            target_usd_shares=100.0,
        )
        self.assertIsNotNone(opp)
        assert opp is not None
        self.assertLess(opp.metadata["price_only_profit_without_coupon_usd"], 0.0)
        self._assert_strict_dominance(opp)

        self.assertIsNone(
            evaluate_yield_stacked_locked_box(
                box_id="early_resolvable_series",
                leg_a=fex_yes,
                leg_b=fex_no,
                min_guaranteed_hold_days=120.0,
                can_resolve_early=True,
                target_usd_shares=100.0,
            )
        )

        hold_decision = evaluate_early_overround_exit_with_forfeited_coupon(
            shares=100.0,
            initial_all_in_cost_usd=100.41,
            accrued_coupon_to_date_usd=0.30,
            forfeited_remaining_min_coupon_usd=0.80,
            net_exit_bid_unit_a=0.501,
            net_exit_bid_unit_b=0.502,
        )
        self.assertFalse(hold_decision["should_exit_early"])

        exit_decision = evaluate_early_overround_exit_with_forfeited_coupon(
            shares=100.0,
            initial_all_in_cost_usd=100.41,
            accrued_coupon_to_date_usd=0.30,
            forfeited_remaining_min_coupon_usd=0.80,
            net_exit_bid_unit_a=0.506,
            net_exit_bid_unit_b=0.506,
        )
        self.assertTrue(exit_decision["should_exit_early"])

    def test_daemon_orchestrators_alpha124_and_cross_venue_sandbox_isolation(self) -> None:
        import asyncio
        from src.polymarket_research.riskless_expansion_v6_engines import (
            ALL_V6_EXPANSION_SLEEVES,
            run_v6_expansion_alpha124_scan,
            run_v6_expansion_cross_venue_scan,
        )

        self.assertEqual(len(ALL_V6_EXPANSION_SLEEVES), 8)
        now_u = 1_799_990_000.0

        with tempfile.TemporaryDirectory() as tmp_dir:
            a124_dir = Path(tmp_dir) / "polymarket"
            xv_dir = Path(tmp_dir) / "cross_venue_shadow"
            xv_dir.mkdir(parents=True, exist_ok=True)

            # 1. Alpha-124 intra-Polymarket v6 orchestrator test (TAIL_BOUNDARY_001_ARB + L2 Recorder)
            rg_lo = SimpleNamespace(
                asset="BTC",
                strike=94000.0,
                end_ts=now_u + 3600.0,
                yes_token="tok_y_lo",
                no_token="tok_n_lo",
                market_id="m_lo",
                fee_rate=0.07,
                fee_exponent=1.0,
                is_downward=False,
            )
            rg_hi = SimpleNamespace(
                asset="BTC",
                strike=94500.0,
                end_ts=now_u + 3600.0,
                yes_token="tok_y_hi",
                no_token="tok_n_hi",
                market_id="m_hi",
                fee_rate=0.07,
                fee_exponent=1.0,
                is_downward=False,
            )
            bks = {
                "tok_y_lo": {"asks": [{"price": 0.966, "size": 250.0}], "bids": [{"price": 0.962, "size": 200.0}]},
                "tok_n_lo": {"asks": [{"price": 0.038, "size": 250.0}], "bids": [{"price": 0.033, "size": 200.0}]},
                "tok_y_hi": {"asks": [{"price": 0.972, "size": 250.0}], "bids": [{"price": 0.968, "size": 200.0}]},
                "tok_n_hi": {"asks": [{"price": 0.025, "size": 250.0}], "bids": [{"price": 0.021, "size": 200.0}]},
            }

            async def _fake_batch(toks: list[str], timeout: float = 2.0) -> dict[str, dict]:
                return {t: bks[t] for t in toks if t in bks}

            mock_daemon = SimpleNamespace(
                single_scan=False,
                _v6_data_dir=a124_dir,
                strike_ladders={"btc_1h": [rg_lo, rg_hi]},
                uma_proposed_markets={},
                uma_onchain_cache={},
                negrisk_convert_slates={},
                holding_rewards_apy=0.0,
                open_positions={},
                entered_keys=set(),
                fetch_books_batch=_fake_batch,
            )
            opps_out: list[dict] = []
            a124_res = asyncio.run(run_v6_expansion_alpha124_scan(mock_daemon, opps_out, now_ts=now_u))
            self.assertGreaterEqual(a124_res["per_sleeve"]["TAIL_BOUNDARY_001_ARB"]["opportunities_found"], 1)
            self.assertGreaterEqual(len(opps_out), 1)
            self.assertGreaterEqual(len(mock_daemon.open_positions), 1)
            self.assertTrue((a124_dir / "v6_expansion_alpha124_telemetry.json").exists())

            # 2. Stage G Cross-Venue v6 orchestrator test (strictly inside xv_dir!)
            stx_m = _make_norm_market(
                venue="stx_ontario",
                market_id="stx_boc",
                category="macro",
                collateral_asset="CAD",
                yes_asks=(OrderLevel(0.45, 500.0),),
                end_ts=int(now_u + 86400 * 30),
            )
            fex_m = _make_norm_market(
                venue="forecastex",
                market_id="fex_boc",
                category="macro",
                collateral_asset="USD",
                no_asks=(OrderLevel(0.50, 500.0),),
                end_ts=int(now_u + 86400 * 30),
            )
            mock_collector = SimpleNamespace(
                engine=SimpleNamespace(data_dir=xv_dir),
                env={"DOMINUS_NETWORK_MODE": "offline"},
            )
            xv_res = asyncio.run(
                run_v6_expansion_cross_venue_scan(
                    mock_collector,
                    [stx_m, fex_m],
                    [(stx_m, fex_m)],
                    transport=None,
                    now_ts=now_u,
                )
            )
            self.assertGreaterEqual(xv_res["per_sleeve"]["XV_FX_INVARIANT_CAD_USD_BOX"]["opportunities_found"], 1)
            self.assertTrue((xv_dir / "v6_expansion_telemetry.json").exists())
            self.assertTrue((xv_dir / "candidate_l2").exists())


if __name__ == "__main__":
    unittest.main()

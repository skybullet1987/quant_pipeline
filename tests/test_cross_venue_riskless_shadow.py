"""
Unit & Integration Tests for Stage G Read-Only Multi-Venue Pure-Riskless Shadow Probe
(`tests/test_cross_venue_riskless_shadow.py`).

Verifies:
  1. Exact venue fee & bridge equations (`Polymarket` dynamic `fee_rate_bps`, `Predict.fun`
     `FeeModuleV2` linear tent `1.8 bps` @ `$0.99` + unsettled maker rebate quarantine,
     `Limitless` `0.05*p*(1-p)` + `10^6` share units, `SX Bet` `0.00%` + `10^20` complement
     translation invariant `o1 + o2 < 1` -> `ask_1 + ask_2 > 1`).
  2. All 5 Programmatic "Double-Zero" Verification Gates (`CrossVenueRuleVerifier`):
       - Gate 1: Rejects Chainlink 60s-TWAP vs Binance 1m spot candle mismatch; accepts identical stream URLs.
       - Gate 2: Rejects `K_A == K_B` across distinct indices; accepts `dK >= B_max` strike dominance corridor.
       - Gate 3: Rejects buying favorite (`$0.75`) on `50-50` Polymarket vs `VOID` SX Bet; accepts buying
                 underdog (`<= $0.48`) on Polymarket with guaranteed `>= +$0.02/sh` cancel windfall;
                 rejects unhedged 3-way Soccer regulation draw partitions.
       - Gate 4: Rejects pre-Set-2 Tennis (`ONE_BALL` vs `ONE_SET` when `completed_sets == 0`);
                 unlocks when `completed_sets >= 1`.
       - Gate 5: Rejects pre-game player props & MLB listed pitchers until `game_live` & `player_participated`.
  3. Honest post-latency (`RTT + takerDelayMs`) execution, queue-ahead trade-through maker fills,
     raced-hedge unwind bleed accounting, competitor-decay bucket tracking, and the 5 Graduation Gates (`G1`–`G5`).
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.cross_venue_riskless_shadow import (
    CrossVenueRuleVerifier,
    HonestCrossVenueShadowEngine,
    LiveCrossVenueShadowCollector,
    NormalizedBinaryMarket,
    OrderLevel,
    limitless_taker_fee_usd,
    parse_limitless_market,
    parse_predict_fun_market,
    parse_sx_bet_summary_fixture,
    polymarket_taker_fee_usd,
    predict_fun_est_maker_rebate_usd,
    predict_fun_taker_fee_usd,
    relay_bridge_drag_usd,
    sx_bet_taker_fee_usd,
)


class TestCrossVenueFeeAndAdapterMath(unittest.TestCase):
    def test_exact_multi_venue_fee_equations(self) -> None:
        # 1. Predict.fun FeeModuleV2 linear tent at $0.99 with 10% invite discount = 1.8 bps ($0.00018/sh)
        pf_tail = predict_fun_taker_fee_usd(100.0, 0.99, fee_rate_bps=200.0, invite_discount=True)
        self.assertAlmostEqual(pf_tail, 100.0 * 0.018 * 0.01, places=8)
        self.assertAlmostEqual(pf_tail, 0.018, places=8)

        # At $0.50 peak: 100 * 0.018 * 0.50 = $0.90
        pf_mid = predict_fun_taker_fee_usd(100.0, 0.50, fee_rate_bps=200.0, invite_discount=True)
        self.assertAlmostEqual(pf_mid, 0.90, places=8)

        # Predict.fun 25% crypto maker rebate (tracked as unsettled estimate only)
        reb = predict_fun_est_maker_rebate_usd(100.0, 0.50, fee_rate_bps=200.0, is_crypto_updown=True)
        self.assertAlmostEqual(reb, 0.25 * (100.0 * 0.02 * 0.50), places=8)

        # 2. Polymarket dynamic per-token fee_rate_bps (0 bps on NBA/macro vs 700 bps parabolic on crypto)
        self.assertEqual(polymarket_taker_fee_usd(100.0, 0.50, fee_rate_bps=0.0), 0.0)
        self.assertAlmostEqual(polymarket_taker_fee_usd(100.0, 0.50, fee_rate_bps=700.0), 1.75, places=8)

        # 3. Limitless new COLLATERAL fee module: 0.05 * shares * p * (1 - p)
        self.assertAlmostEqual(limitless_taker_fee_usd(100.0, 0.50, fee_enabled=True), 1.25, places=8)
        self.assertEqual(limitless_taker_fee_usd(100.0, 0.50, fee_enabled=False), 0.0)

        # 4. SX Bet 0.00% Maker & 0.00% Taker single sports fee
        self.assertEqual(sx_bet_taker_fee_usd(250.0, 0.44), 0.0)

        # 5. Relay.link 2.75 bps ($0.055 per $200 rebalance)
        self.assertAlmostEqual(relay_bridge_drag_usd(200.0, bridge_bps=2.75), 0.055, places=8)

    def test_sx_bet_obv3_complement_invariant_blocks_phantom_arbs(self) -> None:
        # Real live SX Bet sample: Milwaukee Bucks vs Boston Celtics [MONEY_LINE]
        # o1 = 0.13375, o2 = 0.86125 -> o1 + o2 = 0.9950 < 1.00 (maker bids!)
        # Taker asks MUST translate to (1 - o2) = 0.13875 and (1 - o1) = 0.86625 -> sum = 1.0050 (> 1.00!)
        fixture = {
            "id": "L999",
            "leagueLabel": "NBA",
            "gameTime": "2026-11-09T01:00:00.000Z",
            "teamOne": "Milwaukee Bucks",
            "teamTwo": "Boston Celtics",
            "status": 1,
            "markets": [
                {
                    "marketHash": "0xabc123",
                    "marketType": "MONEY_LINE",
                    "betGroup": "game-lines",
                    "outcomeOneName": "Milwaukee Bucks",
                    "outcomeTwoName": "Boston Celtics",
                    "bestOddsOutcomeOne": str(int(0.13375 * 10**20)),
                    "bestOddsOutcomeTwo": str(int(0.86125 * 10**20)),
                }
            ],
        }
        parsed = parse_sx_bet_summary_fixture(fixture, sport_label="Basketball", league_label="NBA")
        self.assertEqual(len(parsed), 1)
        m = parsed[0]
        # Mascot canonicalization: "bucks" < "celtics" -> Milwaukee Bucks = YES, Boston Celtics = NO across all 3 venues!
        self.assertEqual(m.yes_label, "Milwaukee Bucks")
        self.assertEqual(m.no_label, "Boston Celtics")
        self.assertAlmostEqual(m.yes_asks[0].price, 1.0 - 0.86125, places=6)
        self.assertAlmostEqual(m.no_asks[0].price, 1.0 - 0.13375, places=6)
        self.assertAlmostEqual(m.yes_asks[0].price + m.no_asks[0].price, 1.0050, places=6)
        self.assertEqual(m.cancel_rule, "VOID")

        # Verify Limitless "Celtics vs Bucks" canonicalizes identically (`bucks` = YES, `celtics` = NO)!
        lim_sports = parse_limitless_market(
            {
                "id": 999,
                "slug": "celtics-vs-bucks-1794013539833",
                "title": "Celtics vs Bucks",
                "description": "NBA matchup",
                "expirationTimestamp": 1794186000000,
                "categories": ["Sports"],
                "tradeType": "clob",
                "tokens": {"yes": "tok_celtics", "no": "tok_bucks"},
                "metadata": {"fee": False, "isPolyArbitrage": True, "externalSlug": "nba-bos-mil-2026-11-08"},
            },
            {"asks": [{"price": 0.87, "size": 50_000_000}], "bids": [{"price": 0.85, "size": 50_000_000}]},
        )
        assert lim_sports is not None
        self.assertEqual(lim_sports.yes_label, "Bucks")
        self.assertEqual(lim_sports.no_label, "Celtics")
        # Since Celtics bid was 0.85, Bucks implied ask (`1 - 0.85 = 0.15`) becomes `yes_asks[0]`!
        self.assertAlmostEqual(lim_sports.yes_asks[0].price, 0.15, places=6)
        self.assertAlmostEqual(lim_sports.no_asks[0].price, 0.87, places=6)

    def test_limitless_and_predict_fun_parsers(self) -> None:
        lim_raw = {
            "id": 458386,
            "slug": "bnb-up-or-down-hourly-p-1794168331845",
            "title": "BNB Up or Down Hourly",
            "description": "Binance https://www.binance.com/en/trade/BNB_USDT 1H candle",
            "expirationTimestamp": 1794182400000,
            "categories": ["Crypto", "Hourly"],
            "tradeType": "clob",
            "tokens": {"yes": "111", "no": "222"},
            "venue": {"feeModuleType": "COLLATERAL"},
            "settings": {"minSize": "50000000", "takerDelayMs": 500},
            "metadata": {
                "fee": True,
                "isPolyArbitrage": True,
                "externalSlug": "bnb-up-or-down-november-8-2026-6pm-et",
                "externalRulesWatch": {"rulesHash": "deadbeef", "clarificationIds": []},
            },
        }
        lim_ob = {
            "asks": [{"price": 0.62, "size": 25_000_000}],
            "bids": [{"price": 0.58, "size": 40_000_000}],
        }
        lm = parse_limitless_market(lim_raw, lim_ob)
        self.assertIsNotNone(lm)
        assert lm is not None
        self.assertTrue(lm.is_poly_arbitrage)
        self.assertEqual(lm.external_slug, "bnb-up-or-down-november-8-2026-6pm-et")
        self.assertEqual(lm.taker_delay_ms, 500.0)
        self.assertAlmostEqual(lm.yes_asks[0].size, 25.0)
        self.assertAlmostEqual(lm.no_asks[0].price, 0.42)
        self.assertAlmostEqual(lm.no_asks[0].size, 40.0)

        pf_raw = {
            "id": 437,
            "question": "BTC Up or Down - 15 Min",
            "description": "Chainlink https://data.chain.link/streams/btc-usd-twap-60s-streams",
            "tradingStatus": "OPEN",
            "feeRateBps": 200,
            "isYieldBearing": True,
            "polymarketConditionIds": ["0x70537144"],
            "outcomes": [{"name": "Yes", "indexSet": 1}, {"name": "No", "indexSet": 2}],
        }
        pf_ob = {"data": {"asks": [[0.54, 120.0]], "bids": [[0.51, 80.0]]}}
        pm = parse_predict_fun_market(pf_raw, pf_ob)
        self.assertIsNotNone(pm)
        assert pm is not None
        self.assertEqual(pm.oracle_family, "chainlink_60s_twap")
        self.assertEqual(pm.polymarket_condition_ids, ["0x70537144"])
        self.assertAlmostEqual(pm.no_asks[0].price, 0.49)
        self.assertAlmostEqual(pm.no_asks[0].size, 80.0)


class TestFiveDoubleZeroVerificationGates(unittest.TestCase):
    def setUp(self) -> None:
        self.verifier = CrossVenueRuleVerifier()

    def test_gate1_blocks_chainlink_twap_vs_binance_spot_mismatch(self) -> None:
        poly_15m = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="1",
            slug="btc-updown-15m-1794181500",
            title="BTC 15m",
            category="crypto",
            asset="BTC",
            horizon="15m",
            oracle_family="chainlink_60s_twap",
            oracle_stream_url="https://data.chain.link/streams/btc-usd-twap-60s-streams",
            end_ts=1794182400,
        )
        wrong_binance = NormalizedBinaryMarket(
            venue="limitless",
            market_id="2",
            slug="btc-15m-binance",
            title="BTC 15m Binance",
            category="crypto",
            asset="BTC",
            horizon="15m",
            oracle_family="binance_spot_candle",
            end_ts=1794182400,
        )
        res_bad = self.verifier.verify_pair(
            poly_15m, wrong_binance, side_a="YES", side_b="NO", price_a=0.45, price_b=0.50
        )
        self.assertFalse(res_bad.passed)
        self.assertTrue(any("CROSS_ORACLE" in f for f in res_bad.gate_failures))

        exact_twin = NormalizedBinaryMarket(
            venue="limitless",
            market_id="3",
            slug="btc-up-or-down-15-min-1794181500",
            title="BTC 15m Twin",
            category="crypto",
            asset="BTC",
            horizon="15m",
            oracle_family="chainlink_60s_twap",
            oracle_stream_url="https://data.chain.link/streams/btc-usd-twap-60s-streams",
            end_ts=1794182400,
        )
        res_ok = self.verifier.verify_pair(
            poly_15m, exact_twin, side_a="YES", side_b="NO", price_a=0.45, price_b=0.50
        )
        self.assertTrue(res_ok.passed)

    def test_gate2_enforces_cross_oracle_strike_dominance_corridor(self) -> None:
        poly_cl = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="p1",
            slug="btc-above-80000",
            title="BTC > 80000",
            category="crypto",
            asset="BTC",
            horizon="daily",
            oracle_family="chainlink_60s_twap",
            spot_reference_usd=80_000.0,
            strike_price=80_000.0,
            end_ts=1794200000,
        )
        # Same strike $80,000 on BRTI must be rejected (0 < 0.50% * $80,000 = $400 corridor)
        ext_same_k = NormalizedBinaryMarket(
            venue="predict_fun",
            market_id="e1",
            slug="btc-brti-80000",
            title="BTC > 80000 BRTI",
            category="crypto",
            asset="BTC",
            horizon="daily",
            oracle_family="cf_brti_60s",
            spot_reference_usd=80_000.0,
            strike_price=80_000.0,
            end_ts=1794200000,
        )
        r_same = self.verifier.verify_pair(
            poly_cl, ext_same_k, side_a="YES", side_b="NO", price_a=0.48, price_b=0.48
        )
        self.assertFalse(r_same.passed)
        self.assertTrue(any("GATE2_INSUFFICIENT_ORACLE_CORRIDOR" in f for f in r_same.gate_failures))

        # $500 corridor (`YES > $80,000` + `NO < $80,500`, dK = $500 >= $400 B_max) passes!
        ext_corridor = NormalizedBinaryMarket(
            venue="predict_fun",
            market_id="e2",
            slug="btc-brti-80500",
            title="BTC > 80500 BRTI",
            category="crypto",
            asset="BTC",
            horizon="daily",
            oracle_family="cf_brti_60s",
            spot_reference_usd=80_000.0,
            strike_price=80_500.0,
            end_ts=1794200000,
        )
        r_ok = self.verifier.verify_pair(
            poly_cl, ext_corridor, side_a="YES", side_b="NO", price_a=0.48, price_b=0.47
        )
        self.assertTrue(r_ok.passed)
        self.assertAlmostEqual(r_ok.corridor_width_usd, 500.0)

    def test_gate3_walkover_50_50_windfall_and_soccer_draw_guard(self) -> None:
        poly_nba = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="pnba",
            slug="nba-bos-mil",
            title="Celtics vs Bucks",
            category="sports",
            asset="boston celtics::milwaukee bucks@20766",
            sport="nba",
            cancel_rule="50_50",
        )
        sx_nba = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="sxnba",
            slug="0x111",
            title="Celtics vs Bucks",
            category="sports",
            asset="boston celtics::milwaukee bucks@20766",
            sport="nba",
            cancel_rule="VOID",
        )
        # Buying favorite ($0.80) on Polymarket 50-50 loses -$0.30 if game cancels -> MUST REJECT!
        bad_fav = self.verifier.verify_pair(
            poly_nba, sx_nba, side_a="YES", side_b="NO", price_a=0.80, price_b=0.16
        )
        self.assertFalse(bad_fav.passed)
        self.assertTrue(any("GATE3_50_50_WALKOVER_FAVORITE_EXPOSURE" in f for f in bad_fav.gate_failures))

        # Buying underdog ($0.20 <= $0.48) on Polymarket + favorite ($0.76) on SX Bet VOID
        # earns +$0.30/share windfall if canceled -> MUST PASS!
        good_dog = self.verifier.verify_pair(
            poly_nba, sx_nba, side_a="NO", side_b="YES", price_a=0.20, price_b=0.76
        )
        self.assertTrue(good_dog.passed)
        self.assertAlmostEqual(good_dog.cancel_windfall_per_share, 0.30)

        # Unhedged 3-way Soccer regulation draw partition -> MUST REJECT!
        sx_soccer = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="sxsoc",
            slug="0x222",
            title="Arsenal vs Chelsea",
            category="sports",
            asset="arsenal::chelsea@20766",
            sport="soccer",
            cancel_rule="VOID",
            has_unlisted_draw=True,
        )
        poly_soccer = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="psoc",
            slug="epl-ars-che",
            title="Arsenal vs Chelsea",
            category="sports",
            asset="arsenal::chelsea@20766",
            sport="soccer",
            cancel_rule="50_50",
        )
        soc_res = self.verifier.verify_pair(
            poly_soccer, sx_soccer, side_a="YES", side_b="NO", price_a=0.40, price_b=0.55
        )
        self.assertFalse(soc_res.passed)
        self.assertTrue(any("GATE3_UNHEDGED_REGULATION_DRAW_PARTITION" in f for f in soc_res.gate_failures))

    def test_gate4_tennis_set2_and_gate5_live_prop_participation(self) -> None:
        poly_ten = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="pt",
            slug="atp-sinner-alcaraz",
            title="Sinner vs Alcaraz",
            category="sports",
            asset="carlos alcaraz::jannik sinner@20766",
            sport="tennis",
            cancel_rule="50_50",
            tennis_retirement_rule="ONE_BALL",
            completed_sets=0,
        )
        sx_ten = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="sxt",
            slug="0xten",
            title="Sinner vs Alcaraz",
            category="sports",
            asset="carlos alcaraz::jannik sinner@20766",
            sport="tennis",
            cancel_rule="VOID",
            tennis_retirement_rule="ONE_SET",
            completed_sets=0,
        )
        # Set 1 / Pre-match blocked
        self.assertFalse(
            self.verifier.verify_pair(poly_ten, sx_ten, side_a="YES", side_b="NO", price_a=0.44, price_b=0.52).passed
        )
        # Set 2+ (`completed_sets = 1`) unlocked!
        poly_ten.completed_sets = 1
        sx_ten.completed_sets = 1
        self.assertTrue(
            self.verifier.verify_pair(poly_ten, sx_ten, side_a="YES", side_b="NO", price_a=0.44, price_b=0.52).passed
        )

        # Gate 5: Pre-game player prop blocked until `game_live` and `player_participated`
        poly_prop = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="pp",
            slug="nba-lebron-25pts",
            title="LeBron 25+ pts",
            category="sports",
            asset="lebron_25pts",
            cancel_rule="50_50",
            is_player_prop=True,
            game_live=False,
            player_participated=False,
        )
        sx_prop = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="sxp",
            slug="0xprop",
            title="LeBron 25+ pts",
            category="sports",
            asset="lebron_25pts",
            cancel_rule="VOID",
            is_player_prop=True,
            game_live=False,
            player_participated=False,
        )
        self.assertFalse(
            self.verifier.verify_pair(poly_prop, sx_prop, side_a="YES", side_b="NO", price_a=0.42, price_b=0.53).passed
        )
        poly_prop.game_live = sx_prop.game_live = True
        poly_prop.player_participated = sx_prop.player_participated = True
        self.assertTrue(
            self.verifier.verify_pair(poly_prop, sx_prop, side_a="YES", side_b="NO", price_a=0.42, price_b=0.53).passed
        )


class TestHonestShadowEngineAndGraduationGates(unittest.TestCase):
    def test_end_to_end_shadow_scan_latency_survival_unwind_and_graduation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = HonestCrossVenueShadowEngine(clip_notional_usd=40.0, data_dir=Path(tmp))
            engine.latency_samples_ms.extend([75.0, 92.0, 118.0, 140.0])

            poly_m = NormalizedBinaryMarket(
                venue="polymarket",
                market_id="pm1",
                slug="nba-celtics-bucks",
                title="Celtics vs Bucks",
                category="sports",
                asset="boston celtics::milwaukee bucks@20766",
                sport="nba",
                fee_rate_bps=0.0,
                cancel_rule="50_50",
                # Underdog NO on Poly @ $0.36 (passes Gate 3 <= $0.48!), deep anchor book ($400 > 4x clip)
                yes_asks=[OrderLevel(0.66, 600.0)],
                yes_bids=[OrderLevel(0.64, 600.0)],
                no_asks=[OrderLevel(0.36, 1200.0)],
                no_bids=[OrderLevel(0.34, 1200.0)],
            )
            sx_m = NormalizedBinaryMarket(
                venue="sx_bet",
                market_id="sx1",
                slug="0xsx1",
                title="Celtics vs Bucks",
                category="sports",
                asset="boston celtics::milwaukee bucks@20766",
                sport="nba",
                fee_rate_bps=0.0,
                cancel_rule="VOID",
                # Favorite YES on SX Bet @ $0.60 -> Poly NO ($0.36) + SX YES ($0.60) = $0.96 (< $1.00, 0% fees!)
                yes_asks=[OrderLevel(0.60, 500.0)],
                yes_bids=[OrderLevel(0.56, 500.0)],
                no_asks=[OrderLevel(0.44, 500.0)],
                no_bids=[OrderLevel(0.40, 500.0)],
            )

            pairs = LiveCrossVenueShadowCollector.match_pairs([poly_m], [sx_m])
            self.assertEqual(len(pairs), 1)

            cands = engine.scan_cross_venue_pairs(pairs)
            taker_cands = [c for c in cands if c.family == "XV_TAKER_BOX_OR_CORRIDOR"]
            maker_cands = [c for c in cands if c.family == "XV_PASSIVE_MAKER_ANCHOR"]
            self.assertEqual(len(taker_cands), 1)
            self.assertEqual(len(maker_cands), 1)

            # Simulate 6 clean post-delay survivals -> locks net riskless profit > $1.40 each
            for _ in range(6):
                out = engine.simulate_honest_execution(
                    taker_cands[0],
                    post_delay_market_a=poly_m,
                    post_delay_market_b=sx_m,
                )
                self.assertTrue(out.locked_complete_basket)
                self.assertGreater(out.realized_shadow_net_pnl_usd, 1.40)
                engine.record_settled_box_payout(1.0)

            # Simulate passive maker queue fill with enough trade-through flow
            m_out = engine.simulate_honest_execution(
                maker_cands[0],
                post_delay_market_a=poly_m,
                post_delay_market_b=sx_m,
                observed_trade_through_shares=150.0,
                queue_ahead_shares=50.0,
            )
            self.assertTrue(m_out.locked_complete_basket)

            # Next cycle: arb clears on SX Bet (`yes_asks` moves to $0.66) -> records Competitor Decay event!
            sx_cleared = NormalizedBinaryMarket(
                venue="sx_bet",
                market_id="sx1",
                slug="0xsx1",
                title="Celtics vs Bucks",
                category="sports",
                asset="boston celtics::milwaukee bucks@20766",
                sport="nba",
                cancel_rule="VOID",
                yes_asks=[OrderLevel(0.66, 500.0)],
                no_asks=[OrderLevel(0.44, 500.0)],
            )
            engine.scan_cross_venue_pairs([(poly_m, sx_cleared)])
            self.assertEqual(sum(engine.competitor_decay_buckets.values()), 1)

            # Evaluate 7-Day Graduation Report (simulated 7.0 days -> ~+$10/7d > +$0.50/d net after $0.25/d VM delta)
            rep = engine.build_graduation_report(simulated_days=7.0)
            self.assertTrue(rep.gates["G1_shadow_fill_realism_ge_85pct"])
            self.assertTrue(rep.gates["G2_zero_double_zero_incidents"])
            self.assertTrue(rep.gates["G3_unwind_bleed_le_8pct_of_gross"])
            self.assertTrue(rep.gates["G4_p99_cancel_latency_lt_350ms"])
            self.assertTrue(rep.gates["G5_net_daily_gain_gt_0_50_usd"])
            self.assertTrue(rep.overall_graduated)

            # Verify JSONL funnel events written cleanly
            lines = (Path(tmp) / "cross_venue_funnel.jsonl").read_text(encoding="utf-8").strip().splitlines()
            stages = {json.loads(line)["stage"] for line in lines}
            self.assertIn("GROSS_ARB_SEEN", stages)
            self.assertIn("EXECUTABLE_NET_L2", stages)
            self.assertIn("COMPLETE_BASKET_LOCKED", stages)
            self.assertIn("COMPETITOR_DECAY_OBSERVED", stages)


if __name__ == "__main__":
    unittest.main()

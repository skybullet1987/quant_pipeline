"""
Regression Tests for Dominus v5.0 Cross-Venue Double-Zero, Pairing & Telemetry Audit Fixes
(`tests/test_v50_cross_venue_double_zero_and_mof_fixes.py`).

Covers all concrete production defects uncovered during the Stage G `kraken-finland` SQLite audit:
  1. Esports/sports sub-game (`-game1`, `-game2`, `-map-1-winner`) vs full-match moneyline Double-Zero
     + Best-of-2 (`BO2`, `-dh2-`) 1-1 unhedged draw partition guard.
  2. `5m` vs `15-min` crypto candle horizon mismatch even under misconfigured `externalSlug`.
  3. Relative `up-or-down` crypto candles (`metadata.openPrice` populated post-open) vs fixed-strike
     barrier contracts (`bitcoin-above-84k`), while preserving valid post-open `updown` <-> `up-or-down` pairs.
  4. Consecutive-day NBA/NHL back-to-back sports timestamp skew (`<= 6h` tip-off vs tip-off; asymmetric
     `[-1h, +16h]` unlinked expiration vs tip-off; `<= 36h` when explicitly slug-linked).
  5. `is_poly_arbitrage=True` strict target-slug binding (`external_slug == poly.slug`).
  6. Blocking keyless `is_synthetic_depth=True` placeholder books from `LIVE_VERIFIED` `arbitrage_signals`
     + accurate `rule_passed` recording in `pairing_candidates` + SQLite quarantine of `-game1` / `sx_bet` rows.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.cross_venue_connectors import ResilientReadOnlyTransport
from src.polymarket_research.cross_venue_l2_and_baskets import (
    LegSpec,
    Level2ExecutionSimulator,
    MultiVenueArbitrageAnalyzer,
)
from src.polymarket_research.cross_venue_riskless_shadow import (
    CrossVenueRuleVerifier,
    HonestCrossVenueShadowEngine,
    LiveCrossVenueShadowCollector,
    NormalizedBinaryMarket,
    OrderLevel,
    parse_limitless_market,
    parse_polymarket_gamma_market,
    parse_sx_bet_summary_fixture,
)


class TestV50CrossVenueDoubleZeroAndMofFixes(unittest.TestCase):
    def setUp(self) -> None:
        self.verifier = CrossVenueRuleVerifier()
        self.analyzer = MultiVenueArbitrageAnalyzer()

    def test_01_dota2_subgame_and_esports_bo2_draw_double_zero_blocked(self) -> None:
        poly_game1 = parse_polymarket_gamma_market(
            {
                "id": "dota_g1",
                "slug": "dota2-heroic-aurora-2026-11-10-game1",
                "question": "Dota 2: Heroic vs Aurora (BO3) - Game 1 Winner",
                "description": "Resolves to the winner of Game 1.",
                "active": True,
                "closed": False,
                "gameStartTime": "2026-11-10T18:00:00Z",
                "clobTokenIds": json.dumps(["t_heroic", "t_aurora"]),
                "outcomes": json.dumps(["Heroic", "Aurora"]),
                "outcomePrices": json.dumps(["0.42", "0.58"]),
            }
        )
        assert poly_game1 is not None
        self.assertEqual(poly_game1.horizon, "spread_or_period")
        self.assertTrue(poly_game1.asset.startswith("DERIVATIVE::"))

        sx_series = parse_sx_bet_summary_fixture(
            {
                "id": "sx_dota_match",
                "leagueLabel": "Dota 2",
                "gameTime": "2026-11-10T18:00:00Z",
                "teamOne": "Heroic",
                "teamTwo": "Aurora",
                "status": 1,
                "markets": [
                    {
                        "marketHash": "0xdotafull",
                        "marketType": "MONEY_LINE",
                        "outcomeOneName": "Heroic",
                        "outcomeTwoName": "Aurora",
                        "bestOddsOutcomeOne": str(int(0.65 * 10**20)),
                        "bestOddsOutcomeTwo": str(int(0.33 * 10**20)),
                    }
                ],
            }
        )[0]
        self.assertEqual(sx_series.horizon, "match")

        # Must neither pair in `pair_all_venues` nor pass `CrossVenueRuleVerifier`
        self.assertEqual(self.analyzer.pair_all_venues([poly_game1, sx_series]), [])
        rc = self.verifier.verify_pair(
            poly_game1, sx_series, side_a="YES", side_b="NO", price_a=0.30, price_b=0.60
        )
        self.assertFalse(rc.passed)
        self.assertTrue(any("GATE1_SPORTS_LINE_TYPE_MISMATCH" in f for f in rc.gate_failures))

        # Limitless esports Map 1 derivative (categorized under Gaming/Esports) also gets `spread_or_period`
        lim_map1 = parse_limitless_market(
            {
                "id": 771,
                "slug": "legacy-vs-furia-map-1-winner-1793930580857",
                "title": "Legacy vs FURIA - Map 1 Winner",
                "description": "CS2 Map 1",
                "expirationTimestamp": 1793960000000,
                "categories": ["Esports"],
                "tradeType": "clob",
                "tokens": {"yes": "y1", "no": "n1"},
                "metadata": {"isPolyArbitrage": True, "externalSlug": "cs2-lgc-furia-2026-11-10"},
            },
            {"asks": [{"price": 0.45, "size": 50_000_000}], "bids": [{"price": 0.42, "size": 50_000_000}]},
        )
        assert lim_map1 is not None
        self.assertEqual(lim_map1.horizon, "spread_or_period")

        # Best-of-2 (`BO2`) series flags `has_unlisted_draw=True` and fails Gate 3
        poly_bo2 = parse_polymarket_gamma_market(
            {
                "id": "dota_bo2",
                "slug": "dota2-liquid-gg-2026-11-10-bo2",
                "question": "Dota 2: Team Liquid vs Gaimin Gladiators (BO2)",
                "description": "Best of 2 series.",
                "active": True,
                "closed": False,
                "gameStartTime": "2026-11-10T20:00:00Z",
                "clobTokenIds": json.dumps(["t_liq", "t_gg"]),
                "outcomes": json.dumps(["Team Liquid", "Gaimin Gladiators"]),
                "outcomePrices": json.dumps(["0.40", "0.60"]),
            }
        )
        assert poly_bo2 is not None
        self.assertTrue(poly_bo2.has_unlisted_draw)

    def test_02_crypto_5m_vs_15min_horizon_mismatch_blocked_even_on_bad_external_slug(self) -> None:
        pm_5m = parse_polymarket_gamma_market(
            {
                "id": "pm5",
                "slug": "btc-updown-5m-1794241800",
                "question": "Bitcoin Up or Down - 5m",
                "description": "Chainlink https://data.chain.link/streams/btc-usd-twap-60s-streams",
                "active": True,
                "closed": False,
                "endDate": "2026-11-09T16:35:00Z",
                "clobTokenIds": json.dumps(["t_up", "t_down"]),
                "outcomes": json.dumps(["Up", "Down"]),
                "outcomePrices": json.dumps(["0.49", "0.51"]),
            }
        )
        lim_15m_bad_ext = parse_limitless_market(
            {
                "id": "lim15",
                "slug": "btc-up-or-down-15-min-1794241800",
                "title": "BTC Up or Down 15-min",
                "description": "Chainlink https://data.chain.link/streams/btc-usd-twap-60s-streams",
                "expirationTimestamp": 1794242100000,
                "categories": ["Crypto"],
                "tradeType": "clob",
                "tokens": {"yes": "y", "no": "n"},
                "metadata": {
                    "isPolyArbitrage": True,
                    "externalSlug": "btc-updown-5m-1794241800",  # Bad upstream metadata pointing 15m -> 5m!
                },
            },
            {"asks": [{"price": 0.48, "size": 50_000_000}], "bids": [{"price": 0.45, "size": 50_000_000}]},
        )
        assert pm_5m is not None and lim_15m_bad_ext is not None
        self.assertEqual(pm_5m.horizon, "5m")
        self.assertEqual(lim_15m_bad_ext.horizon, "15m")
        self.assertEqual(self.analyzer.pair_all_venues([pm_5m, lim_15m_bad_ext]), [])

        rc = self.verifier.verify_pair(
            pm_5m, lim_15m_bad_ext, side_a="YES", side_b="NO", price_a=0.45, price_b=0.45
        )
        self.assertFalse(rc.passed)
        self.assertTrue(any("GATE1_HORIZON_MISMATCH" in f for f in rc.gate_failures))

    def test_03_relative_up_or_down_candle_never_pairs_with_fixed_strike_barrier(self) -> None:
        pm_fixed_84k = parse_polymarket_gamma_market(
            {
                "id": "pm84k",
                "slug": "bitcoin-above-84k-on-november-9-2026",
                "question": "Will Bitcoin be above $84k on November 9, 2026?",
                "description": "Binance BTCUSDT 1m candle close.",
                "active": True,
                "closed": False,
                "endDate": "2026-11-09T17:00:00Z",
                "clobTokenIds": json.dumps(["t_y", "t_n"]),
                "outcomes": json.dumps(["Yes", "No"]),
                "outcomePrices": json.dumps(["0.30", "0.70"]),
            }
        )
        lim_daily_updown = parse_limitless_market(
            {
                "id": "lim_daily",
                "slug": "btc-up-or-down-daily-p-1794146724552",
                "title": "BTC Up or Down Daily",
                "description": "Binance BTCUSDT daily candle.",
                "expirationTimestamp": int(pm_fixed_84k.end_ts) * 1000 if pm_fixed_84k and pm_fixed_84k.end_ts else 1794243600000,
                "categories": ["Crypto"],
                "tradeType": "clob",
                "tokens": {"yes": "y", "no": "n"},
                "metadata": {"openPrice": 76500.0},
            },
            {"asks": [{"price": 0.52, "size": 50_000_000}], "bids": [{"price": 0.48, "size": 50_000_000}]},
        )
        assert pm_fixed_84k is not None and lim_daily_updown is not None
        self.assertEqual(pm_fixed_84k.strike_price, 84_000.0)
        self.assertIsNone(lim_daily_updown.strike_price)
        self.assertEqual(self.analyzer.pair_all_venues([pm_fixed_84k, lim_daily_updown]), [])

        for sa, sb in (("YES", "NO"), ("NO", "YES")):
            rc = self.verifier.verify_pair(
                pm_fixed_84k, lim_daily_updown, side_a=sa, side_b=sb, price_a=0.40, price_b=0.50
            )
            self.assertFalse(rc.passed)
            self.assertTrue(
                any("GATE1_RELATIVE_CANDLE_VS_FIXED_STRIKE_MISMATCH" in f for f in rc.gate_failures)
            )

        # Meanwhile, a genuine Polymarket Up/Down daily market STILL pairs cleanly after openPrice populates!
        pm_daily_updown = parse_polymarket_gamma_market(
            {
                "id": "pm_daily_ud",
                "slug": "bitcoin-up-or-down-on-november-9-2026",
                "question": "Bitcoin Up or Down on November 9, 2026?",
                "description": "Binance BTCUSDT daily candle.",
                "active": True,
                "closed": False,
                "endDate": "2026-11-09T17:00:00Z",
                "clobTokenIds": json.dumps(["t_up", "t_dn"]),
                "outcomes": json.dumps(["Up", "Down"]),
                "outcomePrices": json.dumps(["0.50", "0.50"]),
            }
        )
        assert pm_daily_updown is not None
        rc_valid = self.verifier.verify_pair(
            pm_daily_updown, lim_daily_updown, side_a="YES", side_b="NO", price_a=0.45, price_b=0.48
        )
        self.assertTrue(rc_valid.passed)

    def test_04_consecutive_day_back_to_back_sports_skew_blocked_while_same_night_24h_preserved(self) -> None:
        from src.polymarket_research.cross_venue_riskless_shadow import parse_stx_ontario_market

        # 1. Genuine same-night unlinked Limitless NBA (`exp_ts = tip_ts + 86_400`) vs STX Ontario (`tip_ts`) MUST PASS!
        tip_mia_utah = 1794362400  # 2026-11-11T02:00:00Z (Nov 10 9:00 PM ET)
        lim_mia_utah = parse_limitless_market(
            {
                "id": 458621,
                "slug": "heat-vs-jazz-1794300000000",
                "title": "Heat vs Jazz",
                "description": "NBA official game result including overtime.",
                "expirationTimestamp": (tip_mia_utah + 86_400) * 1000,  # +24.0h post-tip settlement window
                "categories": ["Sports", "NBA"],
                "tradeType": "clob",
                "tokens": {"yes": "lim_mia", "no": "lim_utah"},
                "settings": {"takerDelayMs": 1500},
                "metadata": {"fee": False},
            },
            {"asks": [{"price": 0.44, "size": 200_000_000}], "bids": [{"price": 0.42, "size": 200_000_000}]},
        )
        stx_mia_utah = parse_stx_ontario_market(
            {
                "market_id": "STXNBA-26NOV102100MIAUTAH-GAMEUTAH",
                "symbol": "STXNBA-26NOV102100MIAUTAH-GAMEUTAH",
                "home_team": "Jazz",
                "away_team": "Heat",
                "sport": "nba",
                "game_ts": tip_mia_utah,
                "ob": {"o": [[54, 50000]], "b": [[52, 50000]]},
            }
        )
        assert lim_mia_utah is not None and stx_mia_utah is not None
        self.assertEqual(lim_mia_utah.asset, stx_mia_utah.asset)
        self.assertEqual(len(self.analyzer.pair_all_venues([lim_mia_utah, stx_mia_utah])), 1)
        self.assertTrue(
            self.verifier.verify_pair(lim_mia_utah, stx_mia_utah, side_a="YES", side_b="NO", price_a=0.44, price_b=0.48).passed
        )

        # 2. Live adversarial back-to-back hazard: Night-1 Limitless (`T1_tip + 24h`) vs Night-2 SX Bet / STX (`T2_tip ≈ T1_tip + 24h`,
        #    where raw `exp_ts - tip_ts == -3600s` or `0s`!) MUST BE HARD-REJECTED!
        t1_tip = 1794366000  # Nov 10 10:00 PM ET
        t2_tip = 1794456000  # Nov 11 11:00 PM ET (+25h later)
        lim_night1 = parse_limitless_market(
            {
                "id": 458701,
                "slug": "thunder-vs-trail-blazers-night1",
                "title": "Thunder vs Trail Blazers",
                "description": "NBA official game result.",
                "expirationTimestamp": (t1_tip + 86_400) * 1000,  # 1794452400 -> raw delta vs t2_tip is -3600s!
                "categories": ["Sports", "NBA"],
                "tradeType": "clob",
                "tokens": {"yes": "t_okc", "no": "t_por"},
                "metadata": {"fee": False},
            },
            {"asks": [{"price": 0.40, "size": 200_000_000}], "bids": [{"price": 0.38, "size": 200_000_000}]},
        )
        sx_night2 = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="0xthunder_night2",
            slug="0xthunder_night2",
            title="Thunder vs Trail Blazers",
            category="sports",
            yes_label="Thunder",
            no_label="Trail Blazers",
            asset="thunder::trail blazers@20769",
            horizon="match",
            oracle_family="official_boxscore",
            end_ts=t2_tip,
            cancel_rule="VOID",
            sport="nba",
        )
        stx_night2 = parse_stx_ontario_market(
            {
                "market_id": "STXNBA-26NOV112300OKCPOR-GAMEPOR",
                "symbol": "STXNBA-26NOV112300OKCPOR-GAMEPOR",
                "home_team": "Trail Blazers",
                "away_team": "Thunder",
                "sport": "nba",
                "game_ts": t1_tip + 86_400,  # Exact 0s raw delta vs lim_night1.end_ts!
                "ob": {"o": [[45, 50000]], "b": [[43, 50000]]},
            }
        )
        lim_night2 = NormalizedBinaryMarket(
            venue="limitless",
            market_id="lim_night2",
            slug="thunder-vs-trail-blazers-night2",
            title="Thunder vs Trail Blazers",
            category="sports",
            yes_label="Thunder",
            no_label="Trail Blazers",
            asset="thunder::trail blazers@20769",
            horizon="match",
            oracle_family="official_boxscore",
            end_ts=t2_tip + 86_400,
            cancel_rule="50_50",
            sport="nba",
        )
        sx_night1 = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="0xthunder_night1",
            slug="0xthunder_night1",
            title="Thunder vs Trail Blazers",
            category="sports",
            yes_label="Thunder",
            no_label="Trail Blazers",
            asset="thunder::trail blazers@20768",
            horizon="match",
            oracle_family="official_boxscore",
            end_ts=t1_tip,
            cancel_rule="VOID",
            sport="nba",
        )
        assert lim_night1 is not None and stx_night2 is not None
        self.assertEqual(self.analyzer.pair_all_venues([lim_night1, sx_night2]), [])
        self.assertEqual(self.analyzer.pair_all_venues([lim_night1, stx_night2]), [])
        self.assertEqual(self.analyzer.pair_all_venues([lim_night2, sx_night1]), [])
        self.assertFalse(
            self.verifier.verify_pair(lim_night1, sx_night2, side_a="YES", side_b="NO", price_a=0.40, price_b=0.55).passed
        )
        self.assertFalse(
            self.verifier.verify_pair(lim_night1, stx_night2, side_a="YES", side_b="NO", price_a=0.40, price_b=0.55).passed
        )
        self.assertFalse(
            self.verifier.verify_pair(lim_night2, sx_night1, side_a="YES", side_b="NO", price_a=0.40, price_b=0.55).passed
        )

    def test_05_is_poly_arbitrage_requires_matching_target_slug(self) -> None:
        pm_other = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="p_other",
            slug="another-fed-rate-hike-in-2026",
            title="Another Fed rate hike in 2026?",
            category="macro",
            rules_hash="hash_poly_a",
            end_ts=1798761600,
        )
        lim_wrong_target = NormalizedBinaryMarket(
            venue="limitless",
            market_id="l_wrong",
            slug="fed-cut-in-2026",
            title="Fed rate cut in 2026?",
            category="macro",
            is_poly_arbitrage=True,
            external_slug="fed-rate-cut-in-2026",  # Points to a DIFFERENT Polymarket slug!
            rules_hash="hash_lim_b",
            end_ts=1798761600,
        )
        rc_bad = self.verifier.verify_pair(
            pm_other, lim_wrong_target, side_a="YES", side_b="NO", price_a=0.45, price_b=0.45
        )
        self.assertFalse(rc_bad.passed)
        self.assertIn("GATE1_UNVERIFIED_NON_CRYPTO_RULES", rc_bad.gate_failures)

    def test_06_unhydrated_synthetic_depth_blocked_from_live_signals_and_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            eng = HonestCrossVenueShadowEngine(clip_notional_usd=25.0, data_dir=data_dir)
            collector = LiveCrossVenueShadowCollector(
                eng,
                authorized_venues={"polymarket", "sx_bet"},
                env={"DOMINUS_NETWORK_MODE": "live_public"},
                transport=ResilientReadOnlyTransport(raw_requester=lambda *a, **k: None),
            )
            try:
                pm_nhl = NormalizedBinaryMarket(
                    venue="polymarket",
                    market_id="pm_nhl_1",
                    slug="nhl-nj-wpg-2026-11-10",
                    title="Devils vs Jets",
                    category="sports",
                    yes_label="Devils",
                    no_label="Jets",
                    yes_asks=[OrderLevel(0.35, 200.0)],
                    yes_bids=[OrderLevel(0.34, 200.0)],
                    no_asks=[OrderLevel(0.66, 200.0)],
                    no_bids=[OrderLevel(0.65, 200.0)],
                    asset="devils::jets@20768",
                    horizon="match",
                    oracle_family="official_boxscore",
                    end_ts=1794358800,
                    cancel_rule="50_50",
                    sport="nhl",
                    data_origin="LIVE_VERIFIED",
                    is_synthetic_depth=False,
                )
                sx_unhydrated = NormalizedBinaryMarket(
                    venue="sx_bet",
                    market_id="0xsx_nhl_1",
                    slug="0xsx_nhl_1",
                    title="Devils vs Jets",
                    category="sports",
                    yes_label="Devils",
                    no_label="Jets",
                    yes_asks=[OrderLevel(0.45, 100.0)],
                    yes_bids=[OrderLevel(0.42, 100.0)],
                    no_asks=[OrderLevel(0.55, 100.0)],  # 0.35 + 0.55 = 0.90 < 1.00, but synthetic 100-sh placeholder!
                    no_bids=[OrderLevel(0.52, 100.0)],
                    asset="devils::jets@20768",
                    horizon="match",
                    oracle_family="official_boxscore",
                    end_ts=1794358800,
                    cancel_rule="VOID",
                    sport="nhl",
                    data_origin="LIVE_VERIFIED",
                    is_synthetic_depth=True,
                )

                async def _fake_poll(venue: str, tr, *, hint_markets=()):
                    if venue == "polymarket":
                        return [pm_nhl]
                    if venue == "sx_bet":
                        return [sx_unhydrated]
                    return []

                collector._poll_connector_isolated = _fake_poll  # type: ignore[method-assign]
                asyncio.run(collector.run_single_cycle())

                import contextlib
                store = eng.telemetry_store
                with contextlib.closing(sqlite3.connect(store.db_path)) as con:
                    sig_cnt = con.execute("SELECT COUNT(*) FROM arbitrage_signals").fetchone()[0]
                    rej_cnt = con.execute(
                        "SELECT COUNT(*) FROM rejected_opportunities WHERE reason = 'UNHYDRATED_SYNTHETIC_DEPTH_NON_EXECUTABLE'"
                    ).fetchone()[0]
                self.assertEqual(sig_cnt, 0)
                self.assertGreaterEqual(rej_cnt, 1)

                # Also verify `quarantine_contaminated_sports_and_recompute` catches synthetic `100.0`-share SX Bet rows
                # while preserving real keyless OBv3 SX Bet L2 rows (`509.12` shares) even when the other leg has `100.0` shares!
                sim = Level2ExecutionSimulator()
                ev_synth_sx = sim.evaluate_basket(
                    basket_id="XV::polymarket:nhl-nj-wpg-2026-11-10:YES__vs__sx_bet:0xnhl_synth:NO",
                    basket_type="CROSS_VENUE_2LEG",
                    legs=[LegSpec(market=pm_nhl, side="YES"), LegSpec(market=sx_unhydrated, side="NO")],
                    target_notional_usd=25.0,
                    post_delay_legs=[pm_nhl, sx_unhydrated],
                )
                sx_real_l2 = NormalizedBinaryMarket(
                    venue="sx_bet",
                    market_id="0xsx_real_obv3",
                    slug="0xsx_real_obv3",
                    title="Devils vs Jets",
                    category="sports",
                    yes_label="Devils",
                    no_label="Jets",
                    yes_asks=[OrderLevel(0.45, 509.12)],
                    yes_bids=[OrderLevel(0.42, 509.12)],
                    no_asks=[OrderLevel(0.55, 509.12)],
                    no_bids=[OrderLevel(0.52, 509.12)],
                    asset="devils::jets@20768",
                    horizon="match",
                    oracle_family="official_boxscore",
                    end_ts=1794358800,
                    cancel_rule="VOID",
                    sport="nhl",
                    data_origin="LIVE_VERIFIED",
                    is_synthetic_depth=False,
                )
                stx_100sh = NormalizedBinaryMarket(
                    venue="stx_ontario",
                    market_id="stx_nhl_100",
                    slug="stx_nhl_100",
                    title="Devils vs Jets",
                    category="sports",
                    yes_label="Devils",
                    no_label="Jets",
                    yes_asks=[OrderLevel(0.35, 100.0)],
                    yes_bids=[OrderLevel(0.34, 100.0)],
                    no_asks=[OrderLevel(0.66, 100.0)],
                    no_bids=[OrderLevel(0.65, 100.0)],
                    asset="devils::jets@20768",
                    horizon="match",
                    oracle_family="official_boxscore",
                    end_ts=1794358800,
                    cancel_rule="VOID",
                    sport="nhl",
                    collateral_asset="CAD",
                    data_origin="LIVE_VERIFIED",
                    is_synthetic_depth=False,
                )
                ev_real_sx = sim.evaluate_basket(
                    basket_id="XV::sx_bet:0xsx_real_obv3:NO__vs__stx_ontario:stx_nhl_100:YES",
                    basket_type="CROSS_VENUE_2LEG",
                    legs=[LegSpec(market=sx_real_l2, side="NO"), LegSpec(market=stx_100sh, side="YES")],
                    target_notional_usd=25.0,
                    post_delay_legs=[sx_real_l2, stx_100sh],
                )
                store.record_signal(ev_synth_sx, data_origin="LIVE_VERIFIED", now_unix=1000.0)
                store.record_signal(ev_real_sx, data_origin="LIVE_VERIFIED", now_unix=1005.0)
                q_rep = store.quarantine_contaminated_sports_and_recompute(fix_ts_unix=1500.0)
                self.assertEqual(q_rep["newly_marked_contaminated_rows"], 1)
                with contextlib.closing(sqlite3.connect(store.db_path)) as con:
                    clean_cnt = con.execute(
                        "SELECT COUNT(*) FROM arbitrage_signals WHERE COALESCE(contaminated, 0) = 0"
                    ).fetchone()[0]
                self.assertEqual(clean_cnt, 1)
            finally:
                asyncio.run(collector.aclose())
                if eng.telemetry_store is not None:
                    eng.telemetry_store.close()

    def test_07_sqlite_f04_growth_throttling_l2_compaction_and_single_pass_empty_cleanup(self) -> None:
        from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowTelemetryStore

        with tempfile.TemporaryDirectory() as tmp:
            store = ShadowTelemetryStore(Path(tmp))
            try:
                now = 1_800_000_000.0
                mkt_base = NormalizedBinaryMarket(
                    venue="polymarket",
                    market_id="m_f04",
                    slug="f04-test",
                    title="F04 Test",
                    category="crypto",
                    yes_asks=[OrderLevel(0.48, 500.0)],
                    yes_bids=[OrderLevel(0.47, 500.0)],
                    no_asks=[OrderLevel(0.53, 500.0)],
                    no_bids=[OrderLevel(0.52, 500.0)],
                    data_origin="LIVE_VERIFIED",
                )
                # 1. Sub-2% size flicker with unchanged spread within 600s is deduplicated; spread jump records immediately
                self.assertEqual(store.ingest_markets([mkt_base], now_unix=now), 1)
                mkt_flicker = NormalizedBinaryMarket(
                    venue="polymarket",
                    market_id="m_f04",
                    slug="f04-test",
                    title="F04 Test",
                    category="crypto",
                    yes_asks=[OrderLevel(0.48, 500.5)],  # +$0.24 depth flicker (<2%), spread unchanged
                    yes_bids=[OrderLevel(0.47, 500.0)],
                    no_asks=[OrderLevel(0.53, 500.0)],
                    no_bids=[OrderLevel(0.52, 500.0)],
                    data_origin="LIVE_VERIFIED",
                )
                self.assertEqual(store.ingest_markets([mkt_flicker], now_unix=now + 15.0), 0)
                mkt_spread_jump = NormalizedBinaryMarket(
                    venue="polymarket",
                    market_id="m_f04",
                    slug="f04-test",
                    title="F04 Test",
                    category="crypto",
                    yes_asks=[OrderLevel(0.49, 500.5)],  # Spread jumped +100 bps -> must record immediately!
                    yes_bids=[OrderLevel(0.47, 500.0)],
                    no_asks=[OrderLevel(0.53, 500.0)],
                    no_bids=[OrderLevel(0.52, 500.0)],
                    data_origin="LIVE_VERIFIED",
                )
                self.assertEqual(store.ingest_markets([mkt_spread_jump], now_unix=now + 30.0), 1)

                # 1b. Parallel +20c BBO shift with unchanged 200 bps spread width & tiny size flicker MUST persist immediately!
                mkt_parallel_base = NormalizedBinaryMarket(
                    venue="polymarket",
                    market_id="m_bbo_shift",
                    slug="bbo-shift",
                    title="BBO Shift",
                    category="crypto",
                    yes_bids=[OrderLevel(0.47, 100.0)],
                    yes_asks=[OrderLevel(0.49, 100.0)],
                    no_bids=[OrderLevel(0.51, 100.0)],
                    no_asks=[OrderLevel(0.53, 100.0)],
                    data_origin="LIVE_VERIFIED",
                )
                mkt_parallel_shifted = NormalizedBinaryMarket(
                    venue="polymarket",
                    market_id="m_bbo_shift",
                    slug="bbo-shift",
                    title="BBO Shift",
                    category="crypto",
                    yes_bids=[OrderLevel(0.67, 100.5)],  # +20c parallel BBO shift, spread width still 200 bps!
                    yes_asks=[OrderLevel(0.69, 100.5)],
                    no_bids=[OrderLevel(0.31, 100.5)],
                    no_asks=[OrderLevel(0.33, 100.5)],
                    data_origin="LIVE_VERIFIED",
                )
                self.assertEqual(store.ingest_markets([mkt_parallel_base], now_unix=now + 40.0), 1)
                self.assertEqual(store.ingest_markets([mkt_parallel_shifted], now_unix=now + 55.0), 1)

                # 1c. Cumulative +$4 depth drift ($100 -> $104 -> $108) must compare against last PERSISTED baseline ($100),
                #     skipping tick 1 (+$4 < $5) and persisting tick 2 (+$8 >= $5)!
                def _depth_mkt(total_usd: float) -> NormalizedBinaryMarket:
                    # yes_bid=0.50, yes_ask=0.50, no_bid=0.50, no_ask=0.50 -> total_depth_usd = 2.0 * sz
                    sz = total_usd / 2.0
                    return NormalizedBinaryMarket(
                        venue="polymarket",
                        market_id="m_cum_drift",
                        slug="cum-drift",
                        title="Cum Drift",
                        category="crypto",
                        yes_bids=[OrderLevel(0.50, sz)],
                        yes_asks=[OrderLevel(0.50, sz)],
                        no_bids=[OrderLevel(0.50, sz)],
                        no_asks=[OrderLevel(0.50, sz)],
                        data_origin="LIVE_VERIFIED",
                    )

                self.assertEqual(store.ingest_markets([_depth_mkt(100.0)], now_unix=now + 60.0), 1)
                self.assertEqual(store.ingest_markets([_depth_mkt(104.0)], now_unix=now + 75.0), 0)
                self.assertEqual(store.ingest_markets([_depth_mkt(108.0)], now_unix=now + 90.0), 1)

                # 2. Identical rejections within a 300s bucket deduplicate instead of bloating 4x/min
                r1 = store.record_rejection(
                    candidate_key="pf_thin_1",
                    stage="L2_SIMULATOR",
                    reason="REJECTED_INSUFFICIENT_L2_DEPTH",
                    venues=["polymarket", "predict_fun"],
                    gross_edge_bps=85.0,
                    data_origin="LIVE_VERIFIED",
                    now_unix=1_800_000_010.0,
                )
                r2 = store.record_rejection(
                    candidate_key="pf_thin_1",
                    stage="L2_SIMULATOR",
                    reason="REJECTED_INSUFFICIENT_L2_DEPTH",
                    venues=["polymarket", "predict_fun"],
                    gross_edge_bps=85.0,
                    data_origin="LIVE_VERIFIED",
                    now_unix=1_800_000_025.0,
                )
                self.assertTrue(r1)
                self.assertFalse(r2)

                # 3. `prune_expired_telemetry` strips `l2_json` older than 48h while keeping 7d/14d row counts intact
                old_3d = NormalizedBinaryMarket(
                    venue="limitless",
                    market_id="m_3d",
                    slug="lim-3d",
                    title="Lim 3d",
                    category="crypto",
                    yes_asks=[OrderLevel(0.50, 200.0)],
                    yes_bids=[OrderLevel(0.48, 200.0)],
                    no_asks=[OrderLevel(0.52, 200.0)],
                    no_bids=[OrderLevel(0.50, 200.0)],
                    data_origin="LIVE_VERIFIED",
                )
                store.ingest_markets([old_3d], now_unix=now - 3 * 86_400)
                deleted = store.prune_expired_telemetry(now_unix=now, retention_sec=15 * 86_400)
                self.assertEqual(deleted, 0)
                self.assertTrue(getattr(store, "_legacy_empty_snapshots_cleaned", False))
                import contextlib
                with contextlib.closing(sqlite3.connect(store.db_path)) as con:
                    l2_val = con.execute(
                        "SELECT l2_json FROM orderbook_snapshots WHERE market_id = 'm_3d'"
                    ).fetchone()[0]
                    self.assertEqual(l2_val, "{}")
                win = store.build_campaign_window_summaries(now_unix=now + 100.0)
                self.assertEqual(win["7d"]["live_snapshots_ingested"], 7)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()

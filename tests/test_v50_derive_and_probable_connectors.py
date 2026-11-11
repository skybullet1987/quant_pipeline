"""
Offline deterministic unit tests (`unittest`) for the v5.0 6-venue international
Rabby-native read-only shadow expansion:
  - `DeriveOptionsConnector`, `DeriveV3OptionsWsState`, `build_derive_dominance_markets`,
    `derive_xyz_taker_fee_usd`, intra-venue butterfly convexity, and Gate 2 `derive_30m_twap` corridor.
  - `ProbableMarketsConnector`, `parse_probable_market`, `probable_markets_taker_fee_usd`,
    and cross-venue `MultiVenueArbitrageAnalyzer` pairing.
  - `SXBetOBv3Connector` `hint_markets` overlap prioritization and accurate `l2_books_hydrated` counting.
  - `evaluate_extended_venues_authorization` & `hot_reload_extended_venue_collector` (`DOMINUS_ENABLED_VENUES`
    6-venue international allowlist, `CA-ON` venue parking, offline fence, and `TRADING="RESTRICTED"`).
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Dict, Mapping, Tuple
import unittest
import urllib.parse

from src.polymarket_research.cross_venue_connectors import (
    DeriveOptionsConnector,
    DeriveV3OptionsWsState,
    EXTENDED_SHADOW_VENUES,
    ProbableMarketsConnector,
    ResilientReadOnlyTransport,
    SXBetOBv3Connector,
    evaluate_extended_venues_authorization,
    hot_reload_extended_venue_collector,
)
from src.polymarket_research.cross_venue_l2_and_baskets import MultiVenueArbitrageAnalyzer
from src.polymarket_research.cross_venue_riskless_shadow import (
    CrossVenueRuleVerifier,
    HonestCrossVenueShadowEngine,
    LiveCrossVenueShadowCollector,
    NormalizedBinaryMarket,
    OrderLevel,
    PROBABLE_CLOB_API_URL,
    PROBABLE_MARKET_API_URL,
    SX_BET_API_URL,
    build_derive_dominance_markets,
    compute_venue_taker_fee_usd,
    derive_xyz_taker_fee_usd,
    parse_polymarket_gamma_market,
    parse_probable_market,
    probable_markets_taker_fee_usd,
)


def _derive_call_inst(currency: str, expiry: int, strike: int, tag: str = "20261225") -> Dict[str, object]:
    return {
        "instrument_name": f"{currency}-{tag}-{strike}-C",
        "instrument_type": "option",
        "is_active": True,
        "base_currency": currency,
        "quote_currency": "USDC",
        "taker_fee_rate": "0.0003",
        "maker_fee_rate": "0.0001",
        "minimum_amount": "0.01",
        "amount_step": "0.01",
        "tick_size": "0.1",
        "option_details": {
            "expiry": expiry,
            "strike": str(strike),
            "option_type": "C",
            "settlement_price": None,
        },
    }


class TestDeriveDominanceConnectorAndGates(unittest.IsolatedAsyncioTestCase):
    def test_ws_state_perp_spot_and_bounded_lru_cache(self) -> None:
        ws = DeriveV3OptionsWsState(max_cached_books=24)
        perp_frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "subscription",
                "params": {
                    "channel": "orderbook.BTC-PERP.1.10",
                    "data": {
                        "instrument_name": "BTC-PERP",
                        "bids": [["99990.0", "2.5"]],
                        "asks": [["100010.0", "1.8"]],
                        "timestamp": 1798000000000,
                    },
                },
            }
        )
        iname = ws.apply_frame(perp_frame)
        self.assertEqual(iname, "BTC-PERP")
        self.assertAlmostEqual(ws.spot_by_currency["BTC"], 100000.0, places=4)

        for idx in range(30):
            opt_name = f"BTC-20261225-{80000 + idx * 1000}-C"
            ws.apply_frame(
                {
                    "method": "subscription",
                    "params": {
                        "channel": f"orderbook.{opt_name}.1.10",
                        "data": {
                            "instrument_name": opt_name,
                            "bids": [["500.0", "1.0"]],
                            "asks": [["520.0", "1.0"]],
                            "timestamp": 1798000000000 + idx,
                        },
                    },
                }
            )
        self.assertLessEqual(len(ws.books_by_instrument), 24)
        self.assertNotIn("BTC-20261225-80000-C", ws.books_by_instrument)
        self.assertIn("BTC-20261225-109000-C", ws.books_by_instrument)

    async def test_dual_call_spread_dominance_math_and_mock_connector(self) -> None:
        exp = 1798185600  # 2026-12-25T08:00:00Z
        now_s = exp - 86400
        insts = [
            _derive_call_inst("BTC", exp, 98000),
            _derive_call_inst("BTC", exp, 100000),
            _derive_call_inst("BTC", exp, 102000),
        ]
        # Width_L = 2000, Width_R = 2000
        # YES ask = (Ask(98k) - Bid(100k)) / 2000 = (2600 - 1500) / 2000 = 0.55, sh = min(0.5, 0.8)*2000 = 1000
        # YES bid = (Bid(98k) - Ask(100k)) / 2000 = (2500 - 1600) / 2000 = 0.45, sh = min(0.6, 0.4)*2000 = 800
        # NO ask  = 1 - (Bid(100k) - Ask(102k)) / 2000 = 1 - (1500 - 600)/2000 = 0.55, sh = min(0.8, 0.3)*2000 = 600
        # NO bid  = 1 - (Ask(100k) - Bid(102k)) / 2000 = 1 - (1600 - 500)/2000 = 0.45, sh = min(0.4, 0.7)*2000 = 800
        books = {
            "BTC-20261225-98000-C": {"bids": [["2500.0", "0.6"]], "asks": [["2600.0", "0.5"]]},
            "BTC-20261225-100000-C": {"bids": [["1500.0", "0.8"]], "asks": [["1600.0", "0.4"]]},
            "BTC-20261225-102000-C": {"bids": [["500.0", "0.7"]], "asks": [["600.0", "0.3"]]},
        }
        conn = DeriveOptionsConnector(
            enable_realtime_ws=False,
            mock_instruments=insts,
            mock_books=books,
            mock_spot_by_currency={"BTC": 100000.0},
        )
        transport = ResilientReadOnlyTransport(network_disabled=True)
        mkts = await conn.poll_markets(transport, now_ts=now_s)
        self.assertEqual(len(mkts), 1)
        m = mkts[0]
        self.assertEqual(m.venue, "derive_xyz")
        self.assertEqual(m.oracle_family, "derive_30m_twap")
        self.assertEqual(m.strike_price, 100000.0)
        self.assertEqual(m.strike_direction, "ABOVE")
        self.assertFalse(m.supports_split_merge)
        self.assertFalse(m.is_synthetic_depth)
        self.assertAlmostEqual(m.yes_asks[0].price, 0.55, places=6)
        self.assertAlmostEqual(m.yes_asks[0].size, 1000.0, places=4)
        self.assertAlmostEqual(m.yes_bids[0].price, 0.45, places=6)
        self.assertAlmostEqual(m.no_asks[0].price, 0.55, places=6)
        self.assertAlmostEqual(m.no_asks[0].size, 600.0, places=4)
        self.assertAlmostEqual(m.no_bids[0].price, 0.45, places=6)
        # 2 * 0.0003 * 100000 / 2000 * 10000 = 300 bps
        self.assertAlmostEqual(m.fee_rate_bps, 300.0, places=4)
        self.assertEqual(conn.snapshot.health_state, "HEALTHY")

    def test_intra_venue_butterfly_convexity_hurdle_and_detection(self) -> None:
        exp = 1798185600
        now_s = exp - 3600
        insts = [
            _derive_call_inst("BTC", exp, 98000),
            _derive_call_inst("BTC", exp, 100000),
            _derive_call_inst("BTC", exp, 102000),
        ]
        # Construct super-replicating butterfly dislocation:
        # YES ask = (2400 - 1500)/2000 = 0.45; NO ask = 1 - (1500 - 400)/2000 = 0.45 -> sum = 0.90 (< 1.00!)
        tiny_books = {
            "BTC-20261225-98000-C": {"bids": [["2350", "0.01"]], "asks": [["2400", "0.01"]]},
            "BTC-20261225-100000-C": {"bids": [["1500", "0.01"]], "asks": [["1550", "0.01"]]},
            "BTC-20261225-102000-C": {"bids": [["350", "0.01"]], "asks": [["400", "0.01"]]},
        }
        deep_books = {
            "BTC-20261225-98000-C": {"bids": [["2350", "0.50"]], "asks": [["2400", "0.50"]]},
            "BTC-20261225-100000-C": {"bids": [["1500", "0.50"]], "asks": [["1550", "0.50"]]},
            "BTC-20261225-102000-C": {"bids": [["350", "0.50"]], "asks": [["400", "0.50"]]},
        }
        tiny_mkts = build_derive_dominance_markets(
            insts, tiny_books, spot_by_currency={"BTC": 100000.0}, now_ts=now_s
        )
        deep_mkts = build_derive_dominance_markets(
            insts, deep_books, spot_by_currency={"BTC": 100000.0}, now_ts=now_s
        )
        with tempfile.TemporaryDirectory() as tmp:
            eng_small = HonestCrossVenueShadowEngine(
                clip_notional_usd=18.0,
                data_dir=Path(tmp) / "s",
                enable_durable_store=False,
            )
            eng_deep = HonestCrossVenueShadowEngine(
                clip_notional_usd=150.0,
                data_dir=Path(tmp) / "d",
                enable_durable_store=False,
            )
            # 20 shares ($18 cost): gross $2.00 < $2.10 two-leg base fee + gas + 600bps option taker fees -> rejected
            self.assertEqual(eng_small.scan_intra_venue_complete_sets(tiny_mkts), [])
            # Deep book ($150 clip -> ~166 shares): gross ~$16.60 >> $2.10 base fee + taker fees -> certified!
            opps = eng_deep.scan_intra_venue_complete_sets(deep_mkts)
            self.assertEqual(len(opps), 1)
            self.assertEqual(opps[0].venue_a, "derive_xyz")
            self.assertEqual(opps[0].market_a_slug, deep_mkts[0].slug)
            self.assertGreater(opps[0].expected_net_profit_usd, 3.0)

    def test_gate2_derive_30m_twap_corridor_enforcement(self) -> None:
        exp = 1798185600
        verifier = CrossVenueRuleVerifier()
        derive_mkt = NormalizedBinaryMarket(
            venue="derive_xyz",
            market_id="DERIVE::BTC-100000",
            slug="derive-btc-100000",
            title="BTC >= $100,000",
            category="crypto",
            yes_label="YES",
            no_label="NO",
            yes_asks=[OrderLevel(0.45, 500.0)],
            yes_bids=[],
            no_asks=[OrderLevel(0.58, 500.0)],
            no_bids=[],
            fee_rate_bps=150.0,
            fee_enabled=True,
            taker_delay_ms=0.0,
            min_shares=5.0,
            supports_split_merge=False,
            asset="BTC",
            horizon="daily",
            oracle_family="derive_30m_twap",
            spot_reference_usd=100000.0,
            strike_price=100000.0,
            strike_direction="ABOVE",
            end_ts=exp,
        )
        poly_narrow = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="PM::BTC-100800",
            slug="btc-above-100800",
            title="Will Bitcoin be above $100,800?",
            category="crypto",
            yes_label="Yes",
            no_label="No",
            yes_asks=[OrderLevel(0.52, 500.0)],
            yes_bids=[],
            no_asks=[OrderLevel(0.45, 500.0)],
            no_bids=[],
            fee_rate_bps=0.0,
            fee_enabled=False,
            taker_delay_ms=0.0,
            min_shares=5.0,
            supports_split_merge=True,
            asset="BTC",
            horizon="daily",
            oracle_family="binance_spot_candle",
            spot_reference_usd=100000.0,
            strike_price=100800.0,
            strike_direction="ABOVE",
            end_ts=exp,
        )
        # 0.80% corridor ($800 < 1.50% * $100,800 = $1,512) -> MUST FAIL Gate 2
        res_fail = verifier.verify_pair(
            derive_mkt, poly_narrow, side_a="YES", side_b="NO", price_a=0.45, price_b=0.45
        )
        self.assertFalse(res_fail.passed)
        self.assertTrue(any("GATE2_INSUFFICIENT_ORACLE_CORRIDOR" in f for f in res_fail.gate_failures))

        # 2.00% corridor ($102,100 - $100,000 = $2,100 >= 1.50% * $102,100 = $1,531.50) -> PASSES all 5 gates!
        poly_wide = NormalizedBinaryMarket(
            **{**poly_narrow.__dict__, "strike_price": 102100.0, "slug": "btc-above-102100"}
        )
        res_ok = verifier.verify_pair(
            derive_mkt, poly_wide, side_a="YES", side_b="NO", price_a=0.45, price_b=0.45
        )
        self.assertTrue(res_ok.passed, msg=f"Unexpected failures: {res_ok.gate_failures}")
        self.assertAlmostEqual(res_ok.corridor_width_usd, 2100.0, places=2)


class TestProbableMarketsConnectorAndPairing(unittest.IsolatedAsyncioTestCase):
    def test_probable_fee_math_and_status_filters(self) -> None:
        # At p=0.50, 175 bps parabolic fee -> 0.0175 * 4 * 0.5 * 0.5 = 0.0175 per dollar notional
        fee_mid = probable_markets_taker_fee_usd(100.0, 0.50, 175.0)
        self.assertAlmostEqual(fee_mid, 100.0 * 0.50 * 0.0175, places=6)
        prob_sample = parse_probable_market(
            {
                "id": "10",
                "market_slug": "prob-sample",
                "question": "Sample?",
                "outcomes": '["Yes","No"]',
                "clobTokenIds": '["t_y","t_n"]',
                "takerFeeBps": 175,
            }
        )
        assert prob_sample is not None
        self.assertAlmostEqual(
            compute_venue_taker_fee_usd(prob_sample, 100.0, 0.50),
            fee_mid,
            places=6,
        )
        self.assertAlmostEqual(derive_xyz_taker_fee_usd(50.0, 0.40, 300.0), 50.0 * 0.03, places=6)

        for bad_flag in ("closed", "archived", "resolved", "disputed"):
            self.assertIsNone(
                parse_probable_market(
                    {
                        "id": "99",
                        "market_slug": "test-flag",
                        "question": "Test?",
                        "outcomes": '["Yes","No"]',
                        "clobTokenIds": '["111","222"]',
                        bad_flag: True,
                    }
                )
            )

    async def test_probable_connector_l2_hydration_and_cross_venue_pairing(self) -> None:
        rules_txt = "This market resolves to Yes if the Boston Celtics defeat the Milwaukee Bucks in regulation or OT."
        end_iso = "2026-12-20T00:30:00Z"
        prob_markets_payload = {
            "markets": [
                {
                    "id": "501",
                    "market_slug": "nba-bos-mil-2026-12-20",
                    "question": "Celtics vs. Bucks",
                    "description": rules_txt,
                    "outcomes": '["Celtics","Bucks"]',
                    "clobTokenIds": '["tok_bos_yes","tok_mil_no"]',
                    "endDate": end_iso,
                    "active": True,
                    "closed": False,
                    "volume24hr": 42000.0,
                    "tags": [{"slug": "nba"}],
                },
                {
                    "id": "502",
                    "market_slug": "stale-resolved-mkt",
                    "question": "Old market?",
                    "outcomes": '["Yes","No"]',
                    "clobTokenIds": '["t1","t2"]',
                    "resolved": True,
                },
            ],
            "pagination": {"hasMore": False},
        }
        books_payload = {
            "tok_bos_yes": {
                "bids": [{"price": "0.51", "size": "250"}],
                "asks": [{"price": "0.53", "size": "300"}],
                "tick_size": "0.01",
                "min_order_size": "5",
                "neg_risk": False,
            },
            "tok_mil_no": {
                "bids": [{"price": "0.46", "size": "220"}],
                "asks": [{"price": "0.48", "size": "280"}],
                "tick_size": "0.01",
                "min_order_size": "5",
                "neg_risk": False,
            },
        }

        async def _mock_http(url: str, headers: Mapping[str, str], timeout_s: float) -> Tuple[int, str, Dict[str, str], float]:
            if url.startswith(f"{PROBABLE_MARKET_API_URL}/markets"):
                return (200, json.dumps(prob_markets_payload), {}, 12.0)
            if url.startswith(f"{PROBABLE_CLOB_API_URL}/book"):
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                tid = (qs.get("token_id") or [""])[0]
                if tid in books_payload:
                    return (200, json.dumps(books_payload[tid]), {}, 9.0)
            return (404, "{}", {}, 5.0)

        transport = ResilientReadOnlyTransport(raw_requester=_mock_http)
        conn = ProbableMarketsConnector(max_pages=1, max_hydrated_markets=8)
        out = await conn.poll_markets(transport, now_ts=1797000000)
        self.assertEqual(len(out), 1)
        pm_prob = out[0]
        self.assertEqual(pm_prob.venue, "probable_markets")
        self.assertEqual(pm_prob.collateral_asset, "USDT")
        self.assertFalse(pm_prob.is_synthetic_depth)
        self.assertEqual(conn.snapshot.l2_books_hydrated, 1)
        self.assertEqual(conn.snapshot.suspended_or_expired_filtered, 1)

        poly_mkt = parse_polymarket_gamma_market(
            {
                "id": "pm-901",
                "slug": "nba-bos-mil-2026-12-20",
                "question": "Celtics vs. Bucks",
                "description": rules_txt,
                "outcomes": '["Celtics","Bucks"]',
                "clobTokenIds": '["p_bos","p_mil"]',
                "gameStartTime": end_iso,
                "active": True,
                "closed": False,
            },
            yes_book={"bids": [{"price": "0.56", "size": "400"}], "asks": [{"price": "0.58", "size": "400"}]},
            no_book={"bids": [{"price": "0.41", "size": "400"}], "asks": [{"price": "0.43", "size": "400"}]},
        )
        assert poly_mkt is not None
        analyzer = MultiVenueArbitrageAnalyzer()
        pairs = analyzer.pair_all_venues([poly_mkt, pm_prob])
        self.assertEqual(len(pairs), 1)
        ver = CrossVenueRuleVerifier().verify_pair(
            pairs[0][0], pairs[0][1], side_a="YES", side_b="NO", price_a=0.43, price_b=0.48
        )
        self.assertTrue(ver.passed, msg=f"Sports pair failed gates: {ver.gate_failures}")


class TestSXBetHydrationAndExtendedAuthorization(unittest.IsolatedAsyncioTestCase):
    async def test_sx_bet_hint_overlap_prioritization_and_hydrated_counter(self) -> None:
        end_ts = 1797500000
        poly_hint = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="pm-nba-1",
            slug="nba-lal-gsw-2026-12-17",
            title="Lakers vs. Warriors",
            category="sports",
            yes_label="Lakers",
            no_label="Warriors",
            yes_asks=[OrderLevel(0.52, 100.0)],
            yes_bids=[],
            no_asks=[OrderLevel(0.49, 100.0)],
            no_bids=[],
            fee_rate_bps=0.0,
            fee_enabled=False,
            taker_delay_ms=0.0,
            min_shares=5.0,
            supports_split_merge=True,
            asset=f"lakers::warriors@{end_ts // 86400}",
            horizon="match",
            oracle_family="official_boxscore",
            end_ts=end_ts,
            sport="nba",
        )
        # Create 30 active SX markets where only hash_29 matches `poly_hint` (beyond the 24-market snapshot cap)
        sx_markets = []
        for i in range(30):
            is_target = i == 29
            sx_markets.append(
                {
                    "marketHash": f"0xhash_{i:02d}",
                    "status": "ACTIVE",
                    "type": 226,
                    "sportLabel": "Basketball",
                    "leagueLabel": "NBA",
                    "teamOneName": "Lakers" if is_target else f"AlphaTeam{i}",
                    "teamTwoName": "Warriors" if is_target else f"BetaTeam{i}",
                    "outcomeOneName": "Lakers" if is_target else f"AlphaTeam{i}",
                    "outcomeTwoName": "Warriors" if is_target else f"BetaTeam{i}",
                    "gameTime": end_ts,
                }
            )
        queried_orders_hashes = []

        async def _mock_sx(url: str, headers: Mapping[str, str], timeout_s: float) -> Tuple[int, str, Dict[str, str], float]:
            if "/metadata/obv3" in url:
                return (200, json.dumps({"data": {"executorAddress": "0xexec", "takerFees": {}}}), {}, 5.0)
            if "/markets/active" in url:
                return (200, json.dumps({"data": {"markets": sx_markets, "nextKey": None}}), {}, 8.0)
            if "/orders-v3" in url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                mhs = (qs.get("marketHashes") or [""])[0].split(",")
                queried_orders_hashes.extend(mhs)
                rows = []
                if "0xhash_29" in mhs:
                    rows.append(
                        {
                            "marketHash": "0xhash_29",
                            "isMakerBettingOutcomeOne": True,
                            "percentageOdds": "52000000000000000000",
                            "totalBetSize": "250000000",
                            "fillAmount": "0",
                        }
                    )
                return (200, json.dumps({"data": rows}), {}, 7.0)
            if "/orderbook-v3/snapshot/market" in url:
                return (200, json.dumps({"data": {"asks": [], "bids": []}}), {}, 6.0)
            return (200, json.dumps({"data": []}), {}, 5.0)

        conn = SXBetOBv3Connector(
            env={"SX_BET_API_KEY": "test_ro_key_64_chars", "DOMINUS_NETWORK_MODE": "live_public"},
            enable_realtime_ws=False,
        )
        mkts = await conn.poll_markets(
            ResilientReadOnlyTransport(raw_requester=_mock_sx),
            hint_markets=[poly_hint],
            now_ts=end_ts - 3600,
        )
        self.assertEqual(len(mkts), 1)
        self.assertEqual(queried_orders_hashes[0], "0xhash_29")
        self.assertEqual(conn.snapshot.l2_books_hydrated, 1)
        self.assertFalse(mkts[0].is_synthetic_depth)

    def test_extended_6_venue_international_authorization_and_hot_reload(self) -> None:
        env = {
            "DOMINUS_NETWORK_MODE": "live_public",
            "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
            "DOMINUS_SERVER_REGION": "FI",
            "DOMINUS_ENABLED_VENUES": "polymarket,predict_fun,sx_bet,limitless,derive_xyz,probable_markets",
            "PREDICT_FUN_API_KEY": "pf_ro_key",
            "SX_BET_API_KEY": "sx_ro_key",
            "POLYMARKET_PUBLIC_DATA_TOS_ATTESTED": "true",
            "LIMITLESS_PUBLIC_DATA_TOS_ATTESTED": "true",
            "SX_BET_API_TOS_ATTESTED": "true",
            "PREDICT_FUN_API_TOS_ATTESTED": "true",
        }
        self.assertEqual(len(EXTENDED_SHADOW_VENUES), 8)
        decs = evaluate_extended_venues_authorization(env)
        for v_on in ("polymarket", "predict_fun", "sx_bet", "limitless", "derive_xyz", "probable_markets"):
            self.assertTrue(decs[v_on].effective_authorized, msg=f"{v_on} should be authorized: {decs[v_on]}")
            self.assertEqual(decs[v_on].scope_permissions["TRADING"], "RESTRICTED")
            self.assertEqual(decs[v_on].scope_permissions["ACCOUNT_PRIVATE"], "RESTRICTED")
        for v_parked in ("forecastex", "stx_ontario"):
            self.assertFalse(decs[v_parked].effective_authorized)
            self.assertEqual(decs[v_parked].status_code, "DISABLED_BY_CONFIG")

        # Verify fail-closed missing jurisdiction, offline fence, and sanctions block on new connectors
        decs_no_jur = evaluate_extended_venues_authorization({**env, "DOMINUS_OPERATOR_JURISDICTION": ""})
        self.assertFalse(decs_no_jur["derive_xyz"].effective_authorized)
        self.assertEqual(decs_no_jur["probable_markets"].status_code, "BLOCKED_MISSING_JURISDICTION_ATTESTATION")

        decs_off = evaluate_extended_venues_authorization({**env, "DOMINUS_NETWORK_MODE": "offline"})
        self.assertFalse(decs_off["derive_xyz"].effective_authorized)
        self.assertEqual(decs_off["probable_markets"].status_code, "OFFLINE_NETWORK_DISABLED")

        decs_us = evaluate_extended_venues_authorization({**env, "DOMINUS_SERVER_REGION": "US"})
        self.assertFalse(decs_us["derive_xyz"].effective_authorized)

        with tempfile.TemporaryDirectory() as tmp:
            eng = HonestCrossVenueShadowEngine(data_dir=Path(tmp), enable_durable_store=False)
            collector = LiveCrossVenueShadowCollector(
                eng,
                env=env,
                transport=ResilientReadOnlyTransport(network_disabled=True),
                authorized_venues={v for v, d in decs.items() if d.effective_authorized},
                blocked_venue_reasons={v: d.status_code for v, d in decs.items() if not d.effective_authorized},
            )
            res_hr = hot_reload_extended_venue_collector(collector, "derive_xyz", env)
            self.assertTrue(res_hr["reloaded"])
            self.assertTrue(res_hr["effective_authorized"])
            res_hr_off = hot_reload_extended_venue_collector(
                collector, "probable_markets", {**env, "DOMINUS_ENABLED_VENUES": "polymarket"}
            )
            self.assertFalse(res_hr_off["effective_authorized"])
            self.assertNotIn("probable_markets", collector.authorized_venues)


if __name__ == "__main__":
    unittest.main()

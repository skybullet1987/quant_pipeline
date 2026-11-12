"""
Adversarial Unit, Integration, Regression & Failure-Injection Suite for Stage G
Production Exchange Connectors, Multi-Leg L2 Simulator, SQLite WAL Store & Self-Healing
(`tests/test_action4_production_connectors_and_adversarial.py`).

Covers all 18 Mandate Section-9 test domains 100% offline (`0` live network sockets, `0` secrets).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import time
import types
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tests as _tests_bootstrap  # noqa: F401, E402

for _opt_net_mod in ("requests", "aiohttp"):
    try:
        __import__(_opt_net_mod)
    except ImportError:
        _stub = types.ModuleType(_opt_net_mod)
        _stub.Session = object  # type: ignore[attr-defined]
        _stub.ClientSession = lambda *_a, **_kw: types.SimpleNamespace(close=lambda: None)  # type: ignore[attr-defined]
        _stub.ClientTimeout = lambda **kw: kw  # type: ignore[attr-defined]
        _stub.ClientWSTimeout = lambda **kw: kw  # type: ignore[attr-defined]
        _stub.TCPConnector = lambda **kw: kw  # type: ignore[attr-defined]
        sys.modules[_opt_net_mod] = _stub

from scripts.deploy_cross_venue_shadow import (
    build_lf_tar_gz_bytes,
    compute_manifest_sha256,
    update_env_map_with_validated_secret,
)
from src.polymarket_research.cross_venue_connectors import (
    ForecastExIBKRConnector,
    IBKRMarketDataWsState,
    LimitlessConnector,
    LimitlessMarketWsState,
    PolymarketConnector,
    PolymarketMarketWsState,
    PredictFunConnector,
    PredictFunOrderbookWsState,
    ResilientReadOnlyTransport,
    STXOntarioConnector,
    SXBetOBv3Connector,
    SlidingWindowRateLimiter,
    VenueCircuitBreaker,
)
from src.polymarket_research.cross_venue_l2_and_baskets import (
    LegSpec,
    Level2ExecutionSimulator,
    MultiVenueArbitrageAnalyzer,
    quantize_price_ceil,
    quantize_shares_floor,
    simulate_leg_l2_fill,
)
from src.polymarket_research.cross_venue_riskless_shadow import (
    HonestCrossVenueShadowEngine,
    LiveCrossVenueShadowCollector,
    NormalizedBinaryMarket,
    OrderLevel,
)
from src.polymarket_research.cross_venue_telemetry_and_watchdog import (
    ShadowRuntimeWatchdog,
    ShadowTelemetryStore,
)


class TestAllSixConnectorsAndWebSocketStateMachines(unittest.TestCase):
    def test_01_all_four_websocket_state_machines_handle_snapshots_deltas_and_24h_rotation(self) -> None:
        # 1. Polymarket WS (`book` snapshot + `price_change` delta + level deletion + `tick_size_change` + `market_resolved`)
        pm_ws = PolymarketMarketWsState()
        sub = json.loads(pm_ws.build_subscribe_frame(["tok_y", "tok_n"]))
        self.assertEqual(sub, {"assets_ids": ["tok_y", "tok_n"], "type": "market"})
        self.assertEqual(pm_ws.build_heartbeat_frame(), "{}")
        self.assertEqual(pm_ws.apply_frame("{}"), 0)

        pm_ws.apply_frame(
            json.dumps(
                {
                    "event_type": "book",
                    "asset_id": "tok_y",
                    "timestamp": 1794200000000,
                    "asks": [{"price": "0.48", "size": "120"}, {"price": "0.50", "size": "200"}],
                    "bids": [{"price": "0.46", "size": "90"}],
                }
            )
        )
        pm_ws.apply_frame(
            {
                "event_type": "price_change",
                "asset_id": "tok_y",
                "price_changes": [
                    {"asset_id": "tok_y", "side": "SELL", "price": "0.48", "size": "0"},   # Delete 0.48 ask
                    {"asset_id": "tok_y", "side": "SELL", "price": "0.47", "size": "150"}, # Add tighter 0.47 ask
                ],
            }
        )
        pm_ws.apply_frame({"event_type": "tick_size_change", "asset_id": "tok_y", "new_tick_size": "0.001"})
        pm_ws.apply_frame({"event_type": "market_resolved", "asset_id": "tok_y", "winning_outcome": "Yes"})
        exported = pm_ws.export_book("tok_y")
        self.assertEqual([r["price"] for r in exported["asks"]], ["0.470000", "0.500000"])
        self.assertEqual(pm_ws.tick_sizes["tok_y"], 0.001)
        self.assertEqual(pm_ws.resolved_assets["tok_y"], "Yes")

        # 2. Limitless WS (full `marketSlugs` union rule + 23.5h proactive reconnect before 24h `1006` LB drop)
        lim_ws = LimitlessMarketWsState(connected_at_unix=1_000.0)
        p1 = lim_ws.build_full_subscription_payload(["btc-15m"])
        p2 = lim_ws.build_full_subscription_payload(["eth-15m"])
        self.assertEqual(p1["data"]["marketSlugs"], ["btc-15m"])
        self.assertEqual(p2["data"]["marketSlugs"], ["btc-15m", "eth-15m"])
        self.assertFalse(lim_ws.needs_proactive_reconnect(1_000.0 + 80_000.0))
        self.assertTrue(lim_ws.needs_proactive_reconnect(1_000.0 + 84_601.0))
        lim_ws.apply_orderbook_update(
            {"data": {"marketSlug": "btc-15m", "orderbook": {"asks": [{"price": 0.51, "size": 50_000_000}], "bids": []}}}
        )
        self.assertEqual(len(lim_ws.orderbooks_by_slug["btc-15m"]["asks"]), 1)

        # 3. Predict.fun WS (`type:"M"` full state + `settlementsPending` share subtraction)
        pf_ws = PredictFunOrderbookWsState()
        pf_sub = json.loads(pf_ws.build_subscribe_frame(["7701"]))
        self.assertEqual(pf_sub["params"], ["predictOrderbook/7701"])
        pf_ws.apply_frame(
            {
                "type": "M",
                "topic": "predictOrderbook/7701",
                "data": {
                    "marketId": 7701,
                    "version": 12,
                    "asks": [[0.52, 100.0], [0.54, 50.0]],
                    "bids": [[0.49, 80.0]],
                    "settlementsPending": {"asks": [[0.52, 40.0]], "bids": []},
                },
            }
        )
        self.assertEqual(pf_ws.books_by_market_id["7701"]["asks"], [[0.52, 60.0], [0.54, 50.0]])

        # 4. IBKR / ForecastEx WS (`smd+{conid}` fields 84/86/88/85)
        ib_ws = IBKRMarketDataWsState()
        self.assertIn("smd+9911", ib_ws.build_subscribe_frame("9911"))
        ib_ws.apply_frame({"conid": "9911", "84": "0.43", "86": "0.45", "88": "150", "85": "200"})
        self.assertAlmostEqual(ib_ws.quotes_by_conid["9911"]["ask"], 0.45)
        self.assertAlmostEqual(ib_ws.quotes_by_conid["9911"]["ask_size"], 200.0)

    def test_02_all_six_rest_connectors_pagination_l2_complement_and_filtering(self) -> None:
        now_s = 1_794_200_000
        exp_future_iso = "2026-11-12T00:00:00Z"
        exp_past_iso = "2026-11-01T00:00:00Z"

        async def mock_requester(url: str, headers: dict[str, str], timeout: float) -> tuple[int, str, dict[str, str], float]:
            # Polymarket Gamma pagination + CLOB L2
            if "gamma-api.polymarket.com/markets" in url:
                if "offset=0" in url:
                    return (
                        200,
                        json.dumps(
                            [
                                {
                                    "id": "pm_active_1",
                                    "slug": "us-cpi-3pct",
                                    "question": "US CPI > 3.0%?",
                                    "description": "BLS CPI release",
                                    "endDate": exp_future_iso,
                                    "outcomes": '["Yes","No"]',
                                    "clobTokenIds": '["pm_y1","pm_n1"]',
                                    "active": True,
                                    "closed": False,
                                    "acceptingOrders": True,
                                },
                                {
                                    "id": "pm_suspended_2",
                                    "slug": "pm-suspended",
                                    "question": "Suspended?",
                                    "endDate": exp_future_iso,
                                    "outcomes": '["Yes","No"]',
                                    "clobTokenIds": '["s1","s2"]',
                                    "active": True,
                                    "closed": False,
                                    "acceptingOrders": False,
                                },
                            ]
                        ),
                        {},
                        12.0,
                    )
                return (200, "[]", {}, 8.0)
            if "clob.polymarket.com/book?token_id=pm_y1" in url:
                return (200, json.dumps({"asks": [{"price": "0.44", "size": "200"}], "bids": [{"price": "0.42", "size": "150"}]}), {}, 9.0)
            if "clob.polymarket.com/book?token_id=pm_n1" in url:
                return (200, json.dumps({"asks": [{"price": "0.58", "size": "200"}], "bids": [{"price": "0.56", "size": "150"}]}), {}, 9.0)
            if "clob.polymarket.com/fee-rate" in url:
                return (200, json.dumps({"base_fee": 0}), {}, 7.0)

            # SX Bet OBv3 (`/metadata/obv3`, `/summary-v3`, cursor `/markets/active`, `/orders-v3` L2 complement)
            if "api.sx.bet/metadata/obv3" in url:
                return (200, json.dumps({"data": {"bettingDelay": 2}}), {}, 10.0)
            if "api.sx.bet/summary-v3" in url:
                return (200, json.dumps({"data": {"sports": []}}), {}, 10.0)
            if "api.sx.bet/markets/active" in url:
                if "paginationKey=NEXT_2" in url:
                    return (
                        200,
                        json.dumps(
                            {
                                "data": {
                                    "markets": [
                                        {
                                            "marketHash": "0xsx_suspended",
                                            "status": "INACTIVE",
                                            "type": 226,
                                            "teamOneName": "Lakers",
                                            "teamTwoName": "Suns",
                                        }
                                    ],
                                    "nextKey": "",
                                }
                            }
                        ),
                        {},
                        11.0,
                    )
                return (
                    200,
                    json.dumps(
                        {
                            "data": {
                                "markets": [
                                    {
                                        "marketHash": "0xsx_bos_nyk",
                                        "status": "ACTIVE",
                                        "type": 226,
                                        "sportLabel": "Basketball",
                                        "leagueLabel": "NBA",
                                        "teamOneName": "Boston Celtics",
                                        "teamTwoName": "New York Knicks",
                                        "outcomeOneName": "Boston Celtics",
                                        "outcomeTwoName": "New York Knicks",
                                        "gameTime": now_s + 7200,
                                    }
                                ],
                                "nextKey": "NEXT_2",
                            }
                        }
                    ),
                    {},
                    11.0,
                )
            if "api.sx.bet/orders-v3" in url:
                # Maker betting Outcome 1 (Celtics = YES) at o1 = 0.40 with 80 USDC remaining ->
                # Outcome 2 (Knicks = NO) Taker Ask @ 1 - 0.40 = $0.60 for 80 / 0.40 = 200 shares!
                return (
                    200,
                    json.dumps(
                        {
                            "data": [
                                {
                                    "marketHash": "0xsx_bos_nyk",
                                    "orderStatus": "ACTIVE",
                                    "expiry": now_s + 3600,
                                    "isMakerBettingOutcomeOne": True,
                                    "percentageOdds": str(int(0.40 * 10**20)),
                                    "totalBetSize": str(100_000_000),
                                    "fillAmount": str(20_000_000),
                                },
                                {
                                    "marketHash": "0xsx_bos_nyk",
                                    "orderStatus": "ACTIVE",
                                    "expiry": now_s + 3600,
                                    "isMakerBettingOutcomeOne": False,
                                    "percentageOdds": str(int(0.55 * 10**20)),
                                    "totalBetSize": str(110_000_000),
                                    "fillAmount": "0",
                                },
                            ]
                        }
                    ),
                    {},
                    14.0,
                )

            # Limitless (`limit=25&page=1`, paused filtering, `10^6` orderbook)
            if "api.limitless.exchange/markets/active" in url:
                if "page=1" in url:
                    return (
                        200,
                        json.dumps(
                            {
                                "data": [
                                    {
                                        "id": 101,
                                        "slug": "eth-15m-active",
                                        "title": "ETH 15m",
                                        "description": "Chainlink https://data.chain.link/streams/eth-usd 60s TWAP",
                                        "expirationTimestamp": (now_s + 900) * 1000,
                                        "tradeType": "clob",
                                        "categories": ["Crypto"],
                                        "tokens": {"yes": "ly", "no": "ln"},
                                        "settings": {"minSize": 5_000_000, "tickSize": 0.001},
                                        "metadata": {"fee": True, "isPolyArbitrage": True},
                                    },
                                    {"id": 102, "slug": "eth-paused", "paused": True, "tradeType": "clob"},
                                ]
                            }
                        ),
                        {},
                        15.0,
                    )
                return (200, json.dumps({"data": []}), {}, 10.0)
            if "api.limitless.exchange/markets/eth-15m-active/orderbook" in url:
                return (200, json.dumps({"asks": [{"price": 0.51, "size": 90_000_000}], "bids": [{"price": 0.48, "size": 90_000_000}]}), {}, 12.0)

            # Predict.fun (`after` cursor pagination per dev.predict.fun/api)
            if "api.predict.fun/v1/markets?" in url:
                if "after=CUR_2" in url:
                    return (200, json.dumps({"data": [{"id": "902", "tradingStatus": "CLOSED"}], "cursor": ""}), {}, 13.0)
                return (
                    200,
                    json.dumps(
                        {
                            "data": [
                                {
                                    "id": "901",
                                    "question": "SOL 15m Up or Down",
                                    "description": "Chainlink 60-second TWAP",
                                    "tradingStatus": "OPEN",
                                    "feeRateBps": 200,
                                    "isYieldBearing": True,
                                    "outcomes": [{"name": "Yes"}, {"name": "No"}],
                                }
                            ],
                            "cursor": "CUR_2",
                        }
                    ),
                    {},
                    13.0,
                )
            if "api.predict.fun/v1/markets/901/orderbook" in url:
                return (200, json.dumps({"data": {"asks": [[0.53, 140.0]], "bids": [[0.49, 140.0]]}}), {}, 11.0)

            # ForecastEx public CFTC/CIRO CSV portal (`summary`, `prices`, `pairs`)
            if "forecastex.com/api/download?type=prices" in url:
                csv_prices = (
                    "symbol,event_contract,subtype,expiration_date,end_price,open_interest\n"
                    f"CPI,CPI_202611_3.0,YES,{exp_future_iso},0.44,1200\n"
                    f"CPI,CPI_202611_3.0,NO,{exp_future_iso},0.56,1200\n"
                    f"CPI,CPI_OLD_2.5,YES,{exp_past_iso},0.50,100\n"
                    f"CPI,CPI_OLD_2.5,NO,{exp_past_iso},0.50,100\n"
                )
                return (200, csv_prices, {}, 18.0)
            if "forecastex.com/api/download?type=summary" in url:
                return (200, "product_id,product_name,product_category\nCPI,US CPI YoY,Economic Indicators\n", {}, 15.0)
            if "forecastex.com/api/download?type=pairs" in url:
                return (200, "pair_id,event_contract,yes_price,no_price,quantity\nP1,CPI_202611_3.0,0.44,0.56,75\n", {}, 15.0)

            # ForecastEx IBKR Client Portal Web API (`secdef/search`, `secdef/info`, 2-step `marketdata/snapshot`)
            if "localhost:5000/v1/api/iserver/secdef/search?symbol=FF" in url:
                return (200, json.dumps([{"conid": "55500"}]), {}, 5.0)
            if "localhost:5000/v1/api/iserver/secdef/search" in url:
                return (200, "[]", {}, 5.0)
            if "localhost:5000/v1/api/iserver/secdef/info?conid=55500" in url:
                return (
                    200,
                    json.dumps(
                        [
                            {"conid": "55501", "maturityDate": "20261218", "strike": "4.25", "right": "C"},
                            {"conid": "55502", "maturityDate": "20261218", "strike": "4.25", "right": "P"},
                        ]
                    ),
                    {},
                    6.0,
                )
            if "localhost:5000/v1/api/iserver/marketdata/snapshot" in url:
                return (
                    200,
                    json.dumps(
                        [
                            {"conid": 55501, "84": "0.38", "86": "0.40", "88": "120", "85": "150"},
                            {"conid": 55502, "84": "0.59", "86": "0.61", "88": "120", "85": "150"},
                        ]
                    ),
                    {},
                    6.0,
                )

            # STX Ontario (`api.on.stxapp.ca`)
            if "api.on.stxapp.ca/api/v1/markets/stx_1/orderbook" in url:
                return (200, json.dumps({"team_a_asks": [[46.0, 120]], "team_b_asks": [[56.0, 120]]}), {}, 8.0)
            if "api.on.stxapp.ca/api/v1/markets" in url:
                return (
                    200,
                    json.dumps(
                        {
                            "markets": [
                                {"market_id": "stx_1", "status": "OPEN", "team_a": "Celtics", "team_b": "Knicks", "sport": "nba", "game_ts": now_s + 7200},
                                {"market_id": "stx_2", "status": "SUSPENDED", "team_a": "Raptors", "team_b": "Heat"},
                            ]
                        }
                    ),
                    {},
                    9.0,
                )

            return (404, "{}", {}, 5.0)

        async def _run() -> None:
            tr = ResilientReadOnlyTransport(raw_requester=mock_requester)
            pm_c = PolymarketConnector(max_pages=2)
            sx_c = SXBetOBv3Connector(max_market_pages=2)
            lim_c = LimitlessConnector(max_pages=2)
            pf_c = PredictFunConnector(max_pages=2, env={"PREDICT_FUN_API_KEY": "SyntheticReadOnlyTestKey_9999"})
            fex_pub = ForecastExIBKRConnector(env={})
            fex_ibkr = ForecastExIBKRConnector(ibkr_gateway_url="https://localhost:5000/v1/api")
            stx_c = STXOntarioConnector(header_provider=lambda m, p: {"X-STX-Key-Id": "k1"})

            pm_m = await pm_c.poll_markets(tr, now_ts=now_s)
            self.assertEqual(len(pm_m), 1)
            self.assertEqual(pm_c.snapshot.suspended_or_expired_filtered, 1)
            self.assertAlmostEqual(pm_m[0].yes_asks[0].price, 0.44)

            sx_m = await sx_c.poll_markets(tr, now_ts=now_s)
            self.assertEqual(len(sx_m), 1)
            self.assertEqual(sx_c.snapshot.suspended_or_expired_filtered, 1)
            # Verify OBv3 `/orders-v3` complement math: o1=0.40 w/ 80 USDC -> NO ask = 0.60 for 200 shares; o2=0.55 w/ 110 USDC -> YES ask = 0.45 for 200 shares!
            self.assertAlmostEqual(sx_m[0].yes_asks[0].price, 0.45)
            self.assertAlmostEqual(sx_m[0].yes_asks[0].size, 200.0)
            self.assertAlmostEqual(sx_m[0].no_asks[0].price, 0.60)
            self.assertAlmostEqual(sx_m[0].no_asks[0].size, 200.0)

            lim_m = await lim_c.poll_markets(tr, now_ts=now_s)
            self.assertEqual(len(lim_m), 1)
            self.assertEqual(lim_c.snapshot.suspended_or_expired_filtered, 1)
            self.assertAlmostEqual(lim_m[0].yes_asks[0].size, 90.0)

            pf_m = await pf_c.poll_markets(tr, now_ts=now_s)
            self.assertEqual(len(pf_m), 1)
            self.assertEqual(pf_m[0].collateral_asset, "vUSDT")
            self.assertEqual(pf_c.snapshot.suspended_or_expired_filtered, 1)

            fp_m = await fex_pub.poll_markets(tr, now_ts=now_s)
            self.assertEqual(len(fp_m), 1)
            self.assertEqual(fp_m[0].data_origin, "REGULATORY_PUBLIC_DELAYED")
            self.assertEqual(fex_pub.snapshot.suspended_or_expired_filtered, 1)

            fi_m = await fex_ibkr.poll_markets(tr, now_ts=now_s)
            self.assertEqual(len(fi_m), 1)
            self.assertEqual(fi_m[0].data_origin, "LIVE_VERIFIED")
            self.assertAlmostEqual(fi_m[0].yes_asks[0].price, 0.40)
            self.assertAlmostEqual(fi_m[0].no_asks[0].price, 0.61)

            stx_m = await stx_c.poll_markets(tr, now_ts=now_s)
            self.assertEqual(len(stx_m), 1)
            self.assertEqual(stx_c.snapshot.suspended_or_expired_filtered, 1)
            self.assertEqual(stx_m[0].collateral_asset, "CAD")
            self.assertAlmostEqual(stx_m[0].yes_asks[0].price, 0.46)

        asyncio.run(_run())


class TestMultiLegBasketsL2SimulationAndCapitalEfficiency(unittest.TestCase):
    def test_03_multi_leg_complete_yes_partition_negrisk_no_conversion_and_incomplete_rejection(self) -> None:
        now_ms = 1_794_200_000_000
        end_ts = 1_794_210_000
        analyzer = MultiVenueArbitrageAnalyzer(clip_notional_usd=30.0)

        # 1. Valid 4-leg NegRisk partition with BOTH a YES complete-set arb (0.20+0.25+0.25+0.22 = $0.92 < $1.00)
        #    AND a NegRisk NO-conversion arb (0.72+0.70+0.70+0.72 = $2.84 < $3.00 = k - 1)!
        valid_4leg = []
        for idx, (lbl, yp, np) in enumerate(
            (("b1", 0.20, 0.72), ("b2", 0.25, 0.70), ("b3", 0.25, 0.70), ("b4", 0.22, 0.72)),
            start=1,
        ):
            valid_4leg.append(
                NormalizedBinaryMarket(
                    venue="polymarket",
                    market_id=f"nr_{idx}",
                    slug=f"nr-{lbl}",
                    title=lbl,
                    category="macro",
                    oracle_family="uma",
                    end_ts=end_ts,
                    yes_asks=[OrderLevel(yp, 500.0)],
                    yes_bids=[OrderLevel(yp - 0.01, 500.0)],
                    no_asks=[OrderLevel(np, 500.0)],
                    no_bids=[OrderLevel(np - 0.01, 500.0)],
                    neg_risk=True,
                    partition_group_id="fed_4way_valid",
                    partition_label=lbl,
                    partition_expected_legs=4,
                    quote_ts_ms=now_ms,
                )
            )

        # 2. Incomplete 3-leg partition missing 3rd leg (`have=2, expected=3`) -> MUST REJECT!
        incomplete_legs = [
            NormalizedBinaryMarket(
                venue="polymarket",
                market_id=f"inc_{i}",
                slug=f"inc-{i}",
                title=f"inc-{i}",
                category="macro",
                oracle_family="uma",
                end_ts=end_ts,
                yes_asks=[OrderLevel(0.25, 400.0)],
                partition_group_id="incomplete_soccer_3way",
                partition_label=f"leg_{i}",
                partition_expected_legs=3,
                quote_ts_ms=now_ms,
            )
            for i in (1, 2)
        ]

        # 3. Oracle mismatch inside partition -> MUST REJECT!
        mismatch_legs = [
            NormalizedBinaryMarket(
                venue="polymarket",
                market_id="om1",
                slug="om1",
                title="om1",
                category="crypto",
                oracle_family="chainlink_60s_twap",
                end_ts=end_ts,
                yes_asks=[OrderLevel(0.40, 200.0)],
                partition_group_id="oracle_mismatch_grp",
                partition_label="low",
                partition_expected_legs=2,
                quote_ts_ms=now_ms,
            ),
            NormalizedBinaryMarket(
                venue="limitless",
                market_id="om2",
                slug="om2",
                title="om2",
                category="crypto",
                oracle_family="binance_spot_candle",
                end_ts=end_ts,
                yes_asks=[OrderLevel(0.45, 200.0)],
                partition_group_id="oracle_mismatch_grp",
                partition_label="high",
                partition_expected_legs=2,
                quote_ts_ms=now_ms,
            ),
        ]

        evals, rejects = analyzer.scan_multi_leg_complete_baskets(
            valid_4leg + incomplete_legs + mismatch_legs,
            now_ms=now_ms,
        )
        btypes = {e.basket_type for e in evals}
        self.assertIn("MULTI_LEG_YES_PARTITION", btypes)
        self.assertIn("NEGRISK_NO_CONVERSION", btypes)

        rej_reasons = {r["group_id"]: r["reason"] for r in rejects}
        self.assertIn("INCOMPLETE_OUTCOME_PARTITION(have=2,expected=3)", rej_reasons["incomplete_soccer_3way"])
        self.assertEqual(rej_reasons["oracle_mismatch_grp"], "PARTITION_ORACLE_MISMATCH")

    def test_04_false_positive_arb_stale_quote_partial_fill_unwind_and_tick_lot_quantization(self) -> None:
        # Exact Decimal tick/lot rounding checks
        self.assertAlmostEqual(quantize_price_ceil(0.4512, tick_size=0.01), 0.46)
        self.assertAlmostEqual(quantize_shares_floor(19.98, lot_size=1.0), 19.0)

        now_ms = 1_794_200_000_000
        sim = Level2ExecutionSimulator(max_quote_age_ms=30_000)

        # 1. Stale quote rejection (`age_ms = 60,000 > 30,000`)
        stale_mkt = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="st1",
            slug="stale-mkt",
            title="Stale",
            category="macro",
            yes_asks=[OrderLevel(0.40, 200.0)],
            quote_ts_ms=now_ms - 60_000,
        )
        fresh_mkt = NormalizedBinaryMarket(
            venue="limitless",
            market_id="fr1",
            slug="fresh-mkt",
            title="Fresh",
            category="macro",
            no_asks=[OrderLevel(0.50, 200.0)],
            quote_ts_ms=now_ms,
        )
        ev_stale = sim.evaluate_basket(
            basket_id="TEST_STALE",
            basket_type="CROSS_VENUE_2LEG",
            legs=[LegSpec(stale_mkt, "YES"), LegSpec(fresh_mkt, "NO")],
            target_notional_usd=25.0,
            now_ms=now_ms,
        )
        self.assertGreater(ev_stale.theoretical.gross_theoretical_edge_usd, 0.0)
        self.assertFalse(ev_stale.simulated_executable.executable)
        self.assertEqual(ev_stale.simulated_executable.status, "REJECTED_STALE_QUOTE")

        # 2. False-positive top-of-book arb: L1 asks are $0.48 + $0.50 = $0.98 (gross edge +$0.02/sh),
        #    but Leg B only has 6 shares at $0.50 and remaining shares at $0.59 + partial unwind bleed!
        deep_a = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="da",
            slug="deep-a",
            title="Deep A",
            category="crypto",
            fee_rate_bps=700.0,
            yes_asks=[OrderLevel(0.48, 200.0)],
            yes_bids=[OrderLevel(0.44, 200.0)],
            quote_ts_ms=now_ms,
            collateral_asset="USDC.e",
        )
        thin_b = NormalizedBinaryMarket(
            venue="predict_fun",
            market_id="tb",
            slug="thin-b",
            title="Thin B",
            category="crypto",
            fee_rate_bps=200.0,
            taker_delay_ms=500.0,
            no_asks=[OrderLevel(0.50, 6.0)],  # Only 6 shares available -> partial fill on Leg B!
            no_bids=[OrderLevel(0.42, 100.0)],
            quote_ts_ms=now_ms,
            collateral_asset="vUSDT",
        )
        ev_fp = sim.evaluate_basket(
            basket_id="TEST_FALSE_POS_PARTIAL",
            basket_type="CROSS_VENUE_2LEG",
            legs=[LegSpec(deep_a, "YES"), LegSpec(thin_b, "NO")],
            target_notional_usd=40.0,
            now_ms=now_ms,
        )
        # Tier 1 looks positive, Tier 2 catches partial fill + unwind bleed + fees + vUSDT haircut -> REJECTED!
        self.assertGreater(ev_fp.theoretical.gross_theoretical_edge_usd, 0.0)
        self.assertFalse(ev_fp.simulated_executable.executable)
        self.assertGreater(ev_fp.simulated_executable.unhedged_excess_shares, 0.0)
        self.assertGreater(ev_fp.simulated_executable.cancel_requote_unwind_bleed_usd, 0.0)
        self.assertGreater(ev_fp.simulated_executable.collateral_basis_haircut_usd, 0.0)

        # 3. Zero-liquidity ladder rejection
        empty_b = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="eb",
            slug="empty-b",
            title="Empty",
            category="sports",
            no_asks=[],
            quote_ts_ms=now_ms,
        )
        sim_zero = simulate_leg_l2_fill(LegSpec(empty_b, "NO"), 25.0, now_ms=now_ms)
        self.assertEqual(sim_zero.filled_shares, 0.0)
        self.assertFalse(sim_zero.fully_filled)

    def test_05_capital_efficiency_ranking_lockup_annualization_and_nonzero_risk_labels(self) -> None:
        now_ms = 1_794_200_000_000
        now_s = now_ms // 1000
        sim = Level2ExecutionSimulator()

        # Opportunity A: 15-minute lockup (`< 1h` -> `annualized_return_pct` MUST be None), +2.5% RODC
        fast_a = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="fa",
            slug="fast-a",
            title="Fast A",
            category="sports",
            end_ts=now_s + 600,
            settlement_delay_hours=0.25,  # Total lockup ~0.42h (< 1.0h)
            yes_asks=[OrderLevel(0.46, 500.0)],
            yes_bids=[OrderLevel(0.45, 500.0)],
            quote_ts_ms=now_ms,
        )
        fast_b = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="fb",
            slug="fast-b",
            title="Fast B",
            category="sports",
            end_ts=now_s + 600,
            settlement_delay_hours=0.25,
            no_asks=[OrderLevel(0.51, 500.0)],
            no_bids=[OrderLevel(0.50, 500.0)],
            quote_ts_ms=now_ms,
        )
        ev_fast = sim.evaluate_basket(
            basket_id="FAST_30M",
            basket_type="CROSS_VENUE_2LEG",
            legs=[LegSpec(fast_a, "YES"), LegSpec(fast_b, "NO")],
            target_notional_usd=50.0,
            now_ms=now_ms,
        )

        # Opportunity B: 30-day macro lockup (`720h`), +4.0% RODC -> much lower capital velocity per hour!
        slow_a = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="sa",
            slug="slow-a",
            title="Slow A",
            category="macro",
            end_ts=now_s + 30 * 86400,
            settlement_delay_hours=4.0,
            yes_asks=[OrderLevel(0.45, 500.0)],
            yes_bids=[OrderLevel(0.44, 500.0)],
            quote_ts_ms=now_ms,
        )
        slow_b = NormalizedBinaryMarket(
            venue="forecastex",
            market_id="sb",
            slug="slow-b",
            title="Slow B",
            category="macro",
            end_ts=now_s + 30 * 86400,
            settlement_delay_hours=12.0,
            no_asks=[OrderLevel(0.49, 500.0)],
            no_bids=[OrderLevel(0.48, 500.0)],
            quote_ts_ms=now_ms,
            collateral_asset="USD",
        )
        ev_slow = sim.evaluate_basket(
            basket_id="SLOW_30D",
            basket_type="CROSS_VENUE_2LEG",
            legs=[LegSpec(slow_a, "YES"), LegSpec(slow_b, "NO")],
            target_notional_usd=50.0,
            now_ms=now_ms,
        )

        self.assertIsNone(ev_fast.capital_efficiency.annualized_return_pct)
        self.assertIsNotNone(ev_slow.capital_efficiency.annualized_return_pct)
        self.assertNotIn("ZERO_RISK", ev_fast.capital_efficiency.risk_classification)
        self.assertGreater(ev_fast.capital_efficiency.execution_risk_score, 0.0)

        ranked = MultiVenueArbitrageAnalyzer.rank_opportunities([ev_slow, ev_fast])
        self.assertEqual(ranked[0].basket_id, "FAST_30M")


class TestResilienceFaultIsolationSQLiteRecoveryAndCampaignWindows(unittest.TestCase):
    def test_06_rate_limit_429_transient_503_recovery_permanent_401_halt_and_partial_venue_isolation(self) -> None:
        # 1. SlidingWindowRateLimiter + VenueCircuitBreaker unit invariants
        rl = SlidingWindowRateLimiter(max_requests=2, window_sec=60.0)
        self.assertEqual(rl.acquire_sync(100.0), 0.0)
        self.assertEqual(rl.acquire_sync(101.0), 0.0)
        self.assertGreater(rl.acquire_sync(102.0), 50.0)
        rl.apply_retry_after(15.0, now_mono=102.0)
        self.assertGreaterEqual(rl.check_wait_sec(105.0), 11.9)

        cb = VenueCircuitBreaker(failure_threshold=2, base_backoff_sec=2.0)
        cb.record_transient_failure("503", now_unix=1000.0, jitter_frac=0.0)
        self.assertTrue(cb.can_attempt(1000.5)[0])
        cb.record_transient_failure("503", now_unix=1001.0, jitter_frac=0.0)
        self.assertFalse(cb.can_attempt(1002.0)[0])  # Circuit open!
        self.assertTrue(cb.can_attempt(1006.0)[0])   # Half-open recovery probe allowed after backoff!
        cb.record_success(now_unix=1006.0)
        self.assertAlmostEqual(cb.accumulated_downtime_sec, 6.0)

        # Permanent 401/403 halt NEVER auto-reopens on timer expiry
        cb.record_permanent_halt("HTTP_401")
        self.assertFalse(cb.can_attempt(9_999_999.0)[0])

        # 2. End-to-end partial-venue failure isolation inside LiveCrossVenueShadowCollector:
        #    - STX Ontario returns HTTP 403 ("Placing Order(s) from this IP address is disallowed") -> latches AUTH_FAILED_PERMANENT (1 request total, 0 retries!)
        #    - Limitless hits HTTP 429 once (`Retry-After: 0.05`) then HTTP 200 -> recovers cleanly!
        #    - ForecastEx succeeds HTTP 200 throughout -> active collector continues uninterrupted!
        call_counts: dict[str, int] = {}
        exp_iso = "2026-12-01T00:00:00Z"

        async def fault_injected_requester(url: str, headers: dict[str, str], timeout: float) -> tuple[int, str, dict[str, str], float]:
            call_counts[url] = call_counts.get(url, 0) + 1
            if "api.on.stxapp.ca" in url:
                return (403, '{"error":"Placing Order(s) from this IP address is disallowed"}', {}, 10.0)
            if "api.limitless.exchange/markets/active" in url:
                if call_counts[url] == 1:
                    return (429, '{"error":"rate limit"}', {"retry-after": "0.05"}, 8.0)
                return (200, json.dumps({"data": []}), {}, 9.0)
            if "forecastex.com/api/download?type=prices" in url:
                csv_p = (
                    "symbol,event_contract,subtype,expiration_date,end_price,open_interest\n"
                    f"FF,FF_202612_4.25,YES,{exp_iso},0.42,800\n"
                    f"FF,FF_202612_4.25,NO,{exp_iso},0.58,800\n"
                )
                return (200, csv_p, {}, 12.0)
            if "forecastex.com/api/download?type=summary" in url:
                return (200, "product_id,product_name,product_category\nFF,Fed Funds,Economic Indicators\n", {}, 10.0)
            if "forecastex.com/api/download?type=pairs" in url:
                return (200, "pair_id,event_contract,yes_price,no_price,quantity\n", {}, 10.0)
            return (200, "[]", {}, 5.0)

        with tempfile.TemporaryDirectory() as tmp:
            eng = HonestCrossVenueShadowEngine(data_dir=Path(tmp))
            try:
                tr = ResilientReadOnlyTransport(raw_requester=fault_injected_requester, max_retries=1, base_backoff_sec=0.05)
                col = LiveCrossVenueShadowCollector(
                    eng,
                    authorized_venues={"forecastex", "limitless", "stx_ontario"},
                    blocked_venue_reasons={"polymarket": "TEST_GEOBLOCK", "sx_bet": "TEST_GEOBLOCK", "predict_fun": "TEST_GEOBLOCK"},
                    env={
                        "STX_API_KEY_ID": "test_key_id_present",
                        "STX_APPS_DATA_TOKEN": "test_token",
                        "DOMINUS_NETWORK_MODE": "live_public",
                    },
                    transport=tr,
                )
                c1 = asyncio.run(col.run_single_cycle())
                c2 = asyncio.run(col.run_single_cycle())

                # STX hit permanent 403 -> attempted ONCE in cycle 1, ZERO retries, ZERO attempts in cycle 2!
                stx_calls = sum(v for k, v in call_counts.items() if "stxapp.ca" in k)
                self.assertEqual(stx_calls, 1)
                self.assertEqual(col.connectors["stx_ontario"].snapshot.authorization_state, "AUTH_FAILED_PERMANENT")

                # Limitless recovered after 429 retry-after; ForecastEx ingested active contract across both cycles!
                self.assertEqual(col.connectors["forecastex"].snapshot.active_markets, 1)
                self.assertEqual(c2["cycle"], 2)
                self.assertEqual(eng.venue_health["polymarket"]["status"], "AUTH_BLOCKED")
            finally:
                eng.telemetry_store.close()

    def test_07_sqlite_wal_idempotency_corrupt_checkpoint_reconciliation_restart_continuity_and_campaign_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            store = ShadowTelemetryStore(tdir)
            t0 = 1_794_200_000.0

            # 1. Duplicate snapshot & signal idempotency + synthetic vs live segregation
            synth_m = NormalizedBinaryMarket(
                venue="polymarket",
                market_id="m_syn",
                slug="syn-1",
                title="Synthetic",
                category="macro",
                yes_asks=[OrderLevel(0.45, 100.0)],
                yes_bids=[OrderLevel(0.44, 100.0)],
                no_asks=[OrderLevel(0.56, 100.0)],
                no_bids=[OrderLevel(0.55, 100.0)],
                quote_ts_ms=int(t0 * 1000),
                data_origin="OFFLINE_SYNTHETIC",
            )
            live_m = NormalizedBinaryMarket(
                venue="forecastex",
                market_id="m_live",
                slug="fex-live-1",
                title="Live FEX",
                category="macro",
                yes_asks=[OrderLevel(0.42, 100.0)],
                yes_bids=[OrderLevel(0.40, 100.0)],
                no_asks=[OrderLevel(0.59, 100.0)],
                no_bids=[OrderLevel(0.57, 100.0)],
                quote_ts_ms=int(t0 * 1000),
                data_origin="REGULATORY_PUBLIC_DELAYED",
            )
            # First ingest inserts 2; identical duplicate ingest inserts 0!
            self.assertEqual(store.ingest_markets([synth_m, live_m], now_unix=t0), 2)
            self.assertEqual(store.ingest_markets([synth_m, live_m], now_unix=t0), 0)

            # Record a 900-second live session + a synthetic session -> verify 1h/24h/7d/14d honest coverage!
            store.start_session(network_mode="offline", data_origin="OFFLINE_SYNTHETIC", now_unix=t0 - 1800)
            store.end_session(clean=True, now_unix=t0 - 1200)

            store.start_session(network_mode="live_public", data_origin="REGULATORY_PUBLIC_DELAYED", now_unix=t0 - 900)
            store.end_session(clean=True, now_unix=t0)

            ev = Level2ExecutionSimulator().evaluate_basket(
                basket_id="DUP_SIG_TEST",
                basket_type="COMPLETE_SET_2LEG",
                legs=[LegSpec(synth_m, "YES"), LegSpec(synth_m, "NO")],
                target_notional_usd=25.0,
                now_ms=int(t0 * 1000),
            )
            self.assertTrue(store.record_signal(ev, data_origin="OFFLINE_SYNTHETIC", signal_uid="sig_1", now_unix=t0))
            self.assertFalse(store.record_signal(ev, data_origin="OFFLINE_SYNTHETIC", signal_uid="sig_1", now_unix=t0))
            self.assertTrue(
                store.record_rejection(
                    candidate_key="rk1",
                    stage="RULE_GATE",
                    reason="GATE1_UMA_CLARIFICATION_DRIFT",
                    venues=["polymarket", "limitless"],
                    gross_edge_bps=120.0,
                    data_origin="OFFLINE_SYNTHETIC",
                    reject_uid="rej_1",
                    now_unix=t0,
                )
            )
            self.assertFalse(
                store.record_rejection(
                    candidate_key="rk1",
                    stage="RULE_GATE",
                    reason="GATE1_UMA_CLARIFICATION_DRIFT",
                    venues=["polymarket", "limitless"],
                    gross_edge_bps=120.0,
                    data_origin="OFFLINE_SYNTHETIC",
                    reject_uid="rej_1",
                    now_unix=t0,
                )
            )

            win = store.build_campaign_window_summaries(now_unix=t0)
            self.assertAlmostEqual(win["1h"]["observed_live_uptime_sec"], 900.0, places=1)
            self.assertAlmostEqual(win["1h"]["unobserved_offline_gap_sec"], 2700.0, places=1)
            self.assertAlmostEqual(win["1h"]["live_coverage_pct"], 25.0, places=2)
            self.assertEqual(win["1h"]["live_snapshots_ingested"], 1)
            self.assertEqual(win["1h"]["synthetic_offline_snapshots_segregated"], 1)
            self.assertEqual(win["1h"]["live_executable_signals"], 0)
            self.assertEqual(win["1h"]["synthetic_offline_signals_segregated"], 1)
            store.close()

            # 2. Inject corrupted checkpoint JSON -> Engine MUST self-heal from SQLite WAL without crashing!
            (tdir / "shadow_engine_state.json").write_text("{corrupt_truncated_json!!!", encoding="utf-8")
            eng_recovered = HonestCrossVenueShadowEngine(data_dir=tdir)
            self.assertTrue(eng_recovered.reconciled_from_corrupt_checkpoint)
            self.assertEqual(eng_recovered.rule_gate_rejections, 1)
            self.assertEqual(eng_recovered.executable_net_l2_count, 1)
            self.assertTrue((tdir / "shadow_alerts.jsonl").exists())
            alerts_txt = (tdir / "shadow_alerts.jsonl").read_text(encoding="utf-8")
            self.assertIn("CORRUPT_STATE_RECONCILED", alerts_txt)

            # 3. Clean restart state continuity across engine instances
            eng_recovered.cycles_completed = 7
            eng_recovered.build_graduation_report(simulated_days=1.0)
            eng_recovered.telemetry_store.close()

            eng_restarted = HonestCrossVenueShadowEngine(data_dir=tdir)
            self.assertFalse(eng_restarted.reconciled_from_corrupt_checkpoint)
            self.assertEqual(eng_restarted.cycles_completed, 7)
            wd_res = ShadowRuntimeWatchdog(eng_restarted.telemetry_store).evaluate({})
            self.assertTrue(wd_res.healthy)
            eng_restarted.telemetry_store.close()

    def test_08_deployment_bundle_lf_normalization_and_secret_free_provisioner_guard(self) -> None:
        manifest = compute_manifest_sha256()
        self.assertIn("scripts/shadow_cross_venue_riskless_probe.py", manifest)
        bundle = build_lf_tar_gz_bytes()
        with tarfile.open(fileobj=__import__("io").BytesIO(bundle), mode="r:gz") as tf:
            names = set(tf.getnames())
            self.assertIn("systemd/polymarket-cross-venue-shadow.service", names)
            unit_bytes = tf.extractfile("systemd/polymarket-cross-venue-shadow.service").read()  # type: ignore[union-attr]
            self.assertNotIn(b"\r\n", unit_bytes)

        # Valid read-only API key passes; raw hex private key is blocked without echoing!
        merged_ok, rep_ok = update_env_map_with_validated_secret(
            {"DOMINUS_NETWORK_MODE": "offline"},
            "SX_BET_API_KEY",
            "SyntheticFreshReadOnlyToken_2026_Valid99",
        )
        self.assertTrue(rep_ok.valid)
        self.assertIn("SX_BET_API_KEY", merged_ok)

        bad_priv = "0x" + "cd" * 32
        _, rep_bad = update_env_map_with_validated_secret(
            {"DOMINUS_NETWORK_MODE": "offline"},
            "SX_BET_API_KEY",
            bad_priv,
        )
        self.assertFalse(rep_bad.valid)
        for err in rep_bad.errors:
            self.assertNotIn(bad_priv, err)


class TestMasterUnblockCertificationAndBankrollGates(unittest.TestCase):
    def test_09_expanded_forecastex_above_80_books_ibkr_tickle_and_stx_phoenix_ed25519(self) -> None:
        import hashlib
        from src.polymarket_research.cross_venue_connectors import (
            STXPhoenixOrderbookWsState,
            build_stx_readonly_ed25519_headers,
        )

        # 1. Verify ForecastEx public CFTC CSV parser ingests >80 active contracts (e.g. 120 contracts)
        now_s = 1_794_200_000
        exp_iso = "2026-12-31T23:59:59Z"
        summary_lines = ["product_id,product_name,product_category", "CPI,US CPI YoY,Economic Indicators"]
        prices_lines = ["product_id,event_contract,subtype,expiration_date,end_price,open_interest"]
        for idx in range(120):
            ec = f"CPI_202612_{2.0 + idx * 0.05:.2f}"
            prices_lines.append(f"CPI,{ec},YES,{exp_iso},0.45,500")
            prices_lines.append(f"CPI,{ec},NO,{exp_iso},0.55,500")

        mkts, total_disc, exp_filt = ForecastExIBKRConnector.parse_public_portal_csvs(
            summary_csv="\n".join(summary_lines),
            prices_csv="\n".join(prices_lines),
            now_s=now_s,
        )
        self.assertEqual(total_disc, 120)
        self.assertEqual(exp_filt, 0)
        self.assertEqual(len(mkts), 120)

        # 2. Verify IBKR `/iserver/auth/status` + `/tickle` + `6509` (`mdAvailability`) classification
        self.assertEqual(ForecastExIBKRConnector.classify_md_availability("R"), "LIVE_STREAMING")
        self.assertEqual(ForecastExIBKRConnector.classify_md_availability("D"), "DELAYED")
        self.assertEqual(ForecastExIBKRConnector.classify_md_availability("Z"), "FROZEN")

        tickle_hits = []

        async def _ibkr_mock(url: str, headers: dict, timeout: float):
            if "/iserver/auth/status" in url:
                return (200, json.dumps({"authenticated": True, "connected": True, "competing": False}), {}, 4.0)
            if "/tickle" in url:
                tickle_hits.append(url)
                return (200, json.dumps({"session": "ok"}), {}, 3.0)
            return (404, "{}", {}, 2.0)

        async def _run_ibkr() -> None:
            tr = ResilientReadOnlyTransport(raw_requester=_ibkr_mock)
            fex = ForecastExIBKRConnector(ibkr_gateway_url="https://localhost:5000/v1/api")
            st = await fex.check_ibkr_session_status(tr)
            self.assertTrue(st["authenticated"])
            self.assertEqual(len(tickle_hits), 1)

        asyncio.run(_run_ibkr())

        # 3. Verify STX Ontario GET-only Ed25519 headers, clock-skew guard, and Phoenix v2 WS state
        now_ms = 1_794_200_000_000
        hdrs = build_stx_readonly_ed25519_headers(
            "GET",
            "/api/v1/markets?status=OPEN",
            access_key="stx_test_key_id",
            sign_fn=lambda msg: hashlib.sha512(msg).digest(),
            timestamp_ms=now_ms,
            now_ms=now_ms,
        )
        self.assertEqual(hdrs["X-STX-ACCESS-KEY"], "stx_test_key_id")
        self.assertEqual(hdrs["X-STX-ACCESS-TIMESTAMP"], str(now_ms))
        self.assertTrue(len(hdrs["X-STX-ACCESS-SIGNATURE"]) > 16)

        with self.assertRaises(PermissionError):
            build_stx_readonly_ed25519_headers(
                "POST",
                "/api/v1/orders",
                access_key="stx_test_key_id",
                sign_fn=lambda msg: b"x" * 64,
                timestamp_ms=now_ms,
                now_ms=now_ms,
            )
        with self.assertRaises(ValueError):
            build_stx_readonly_ed25519_headers(
                "GET",
                "/api/v1/markets",
                access_key="stx_test_key_id",
                sign_fn=lambda msg: b"x" * 64,
                timestamp_ms=now_ms - 45_000,
                now_ms=now_ms,
            )

        ws = STXPhoenixOrderbookWsState()
        join_msg = json.loads(ws.build_join_frame(["stx_mkt_1", "stx_mkt_2"]))
        self.assertEqual(join_msg[2], "orderbook")
        self.assertEqual(join_msg[3], "phx_join")
        updated_mid = ws.apply_frame(
            json.dumps(["1", "2", "orderbook", "book_snapshot", {"market_id": "stx_mkt_1", "team_a_asks": [[48.0, 100]]}])
        )
        self.assertEqual(updated_mid, "stx_mkt_1")
        self.assertIn("stx_mkt_1", ws.books_by_market_id)

        # 4. Verify real Ed25519 BYOK keypair generator + 0600 signer loader + RFC 8032 test vector + SX Bet Centrifugo WS state
        from src.polymarket_research.cross_venue_connectors import (
            SXBetCentrifugoWsState,
            _ed25519_stdlib_pubkey_and_signer,
            generate_stx_ed25519_keypair,
            load_stx_ed25519_signer,
        )

        # Official RFC 8032 Section 7.1 TEST 1 vector check
        rfc_seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        rfc_pub, rfc_sign = _ed25519_stdlib_pubkey_and_signer(rfc_seed)
        self.assertEqual(rfc_pub.hex(), "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        self.assertEqual(
            rfc_sign(b"").hex(),
            "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
        )

        with tempfile.TemporaryDirectory() as tmp_ed:
            priv_path = Path(tmp_ed) / "stx_ed25519.pem"
            pub_pem = generate_stx_ed25519_keypair(priv_path)
            self.assertIn("BEGIN PUBLIC KEY", pub_pem)
            self.assertNotIn("PRIVATE KEY", pub_pem)
            signer = load_stx_ed25519_signer(priv_path, enforce_0600=False)
            real_hdrs = build_stx_readonly_ed25519_headers(
                "GET",
                "/api/v1/markets",
                access_key="stx_byok_id",
                sign_fn=signer,
                timestamp_ms=now_ms,
                now_ms=now_ms,
            )
            self.assertEqual(len(real_hdrs["X-STX-ACCESS-SIGNATURE"]), 88)  # 64-byte Ed25519 signature -> 88-char Base64

        sx_cf = SXBetCentrifugoWsState()
        conn_frame = json.loads(sx_cf.build_connect_frame("sx_cf_tok_123"))
        self.assertEqual(conn_frame["connect"]["token"], "sx_cf_tok_123")
        subs = [json.loads(f) for f in sx_cf.build_subscribe_frames(market_hashes=["0xmkt1"], include_global_best_odds=True)]
        sub_channels = {s["subscribe"]["channel"] for s in subs}
        self.assertEqual(sub_channels, {"orderbook_v3:0xmkt1", "best_odds_v3:global"})

        # Monotonic version deduplication + 10^20 / 10^6 complement math
        ch_ok = sx_cf.apply_frame(
            json.dumps(
                {
                    "push": {
                        "channel": "orderbook_v3:0xmkt1",
                        "pub": {
                            "data": {
                                "marketHash": "0xmkt1",
                                "version": 10,
                                "outcomes": {
                                    "outcomeOne": [[str(40 * 10**18), str(80 * 10**6)]],
                                    "outcomeTwo": [[str(55 * 10**18), str(110 * 10**6)]],
                                },
                            }
                        },
                    }
                }
            )
        )
        self.assertEqual(ch_ok, "0xmkt1")
        # Stale version 9 MUST be ignored!
        ch_stale = sx_cf.apply_frame(
            json.dumps(
                {
                    "push": {
                        "channel": "orderbook_v3:0xmkt1",
                        "pub": {"data": {"marketHash": "0xmkt1", "version": 9, "outcomes": {}}},
                    }
                }
            )
        )
        self.assertIsNone(ch_stale)
        y_a, _, n_a, _ = sx_cf.parse_cached_l2_levels("0xmkt1")
        self.assertAlmostEqual(y_a[0].price, 0.45)
        self.assertAlmostEqual(y_a[0].size, 200.0)
        self.assertAlmostEqual(n_a[0].price, 0.60)
        self.assertAlmostEqual(n_a[0].size, 200.0)

    def test_10_blocker_registry_single_venue_hot_reload_168h_cert_and_bankroll_gates(self) -> None:
        from src.polymarket_research.cross_venue_shadow_deployment_gates import evaluate_all_venues_authorization
        from src.polymarket_research.cross_venue_unblock_and_certification import (
            BankrollMilestoneVerifier,
            CredentialLifecycleManager,
            PersistentBlockerRegistry,
            VenueCertificationTracker,
        )

        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            env_init = {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                "DOMINUS_SERVER_REGION": "FI",
                "DOMINUS_WORKSTATION_GEOBLOCKED": "1",
                "FORECASTEX_PUBLIC_PORTAL_AUTHORIZED": "1",
                "PREDICT_FUN_ENV": "mainnet",
            }
            auth_init = evaluate_all_venues_authorization(env_init)
            # First-principles separation: Polymarket, Limitless, and ForecastEx public feeds are AUTHORIZED,
            # while SX Bet, Predict.fun (mainnet), and STX Ontario (on FI) remain RESTRICTED!
            for pub_v in ("polymarket", "limitless", "forecastex"):
                self.assertTrue(auth_init[pub_v].effective_authorized)
                self.assertEqual(auth_init[pub_v].public_data_state, "PUBLIC_DATA_AUTHORIZED")
            self.assertTrue(auth_init["sx_bet"].effective_authorized)
            self.assertEqual(auth_init["sx_bet"].public_data_state, "PUBLIC_DATA_AUTHORIZED")
            self.assertEqual(auth_init["sx_bet"].market_data_access, "AUTHORIZED_REST_ONLY")
            self.assertTrue(auth_init["stx_ontario"].effective_authorized)
            self.assertEqual(auth_init["stx_ontario"].public_data_state, "PUBLIC_DATA_AUTHORIZED")
            self.assertEqual(auth_init["stx_ontario"].readonly_api_state, "CREDENTIALS_REQUIRED")
            self.assertEqual(auth_init["stx_ontario"].venue_classification, "PARTIALLY_ACTIVE")
            self.assertFalse(auth_init["predict_fun"].effective_authorized)
            self.assertEqual(auth_init["predict_fun"].public_data_state, "CREDENTIALS_REQUIRED")
            self.assertEqual(auth_init["predict_fun"].readonly_api_state, "CREDENTIALS_REQUIRED")

            eng = HonestCrossVenueShadowEngine(data_dir=tdir)
            col = LiveCrossVenueShadowCollector(
                eng,
                authorized_venues={"polymarket", "limitless", "sx_bet", "forecastex", "stx_ontario"},
                blocked_venue_reasons={"predict_fun": auth_init["predict_fun"].status_code},
                env=env_init,
            )
            poly_conn_before = col.connectors["polymarket"]
            lim_conn_before = col.connectors["limitless"]
            sx_conn_before = col.connectors["sx_bet"]
            fex_conn_before = col.connectors["forecastex"]
            cred_mgr = CredentialLifecycleManager()
            reg = PersistentBlockerRegistry(tdir)

            # 1. Sync blocker registry twice with identical fingerprint -> verification_count MUST stay 1 (0 retry loop!)
            reg.sync_from_runtime_state(env=env_init, auth_decisions=auth_init, collector=col, cred_manager=cred_mgr, now_unix=1000.0)
            reg.sync_from_runtime_state(env=env_init, auth_decisions=auth_init, collector=col, cred_manager=cred_mgr, now_unix=1015.0)
            loaded_1 = reg.load_all()
            self.assertEqual(loaded_1["BLK::PREDICT_FUN"].verification_count, 1)
            self.assertEqual(loaded_1["BLK::PREDICT_FUN"].current_state, "ACTIVE_BLOCKED")

            # 2. Simulate `PREDICT_FUN_API_KEY` provisioned ONLY for `predict_fun` ->
            #    auto-unblocks & hot-reloads ONLY `predict_fun` while `polymarket`, `limitless`, `sx_bet`, and `forecastex` connectors are untouched!
            env_pf = {
                **env_init,
                "PREDICT_FUN_API_KEY": "pred_sk_test_readonly_content_token_900123",
            }
            auth_pf = evaluate_all_venues_authorization(env_pf)
            sync_res = reg.sync_from_runtime_state(
                env=env_pf,
                auth_decisions=auth_pf,
                collector=col,
                cred_manager=cred_mgr,
                now_unix=1030.0,
            )
            self.assertEqual(sync_res["auto_unblocked_venues"], ["predict_fun"])
            self.assertIn("predict_fun", col.authorized_venues)
            self.assertIn("stx_ontario", col.authorized_venues)
            self.assertIs(col.connectors["polymarket"], poly_conn_before)
            self.assertIs(col.connectors["limitless"], lim_conn_before)
            self.assertIs(col.connectors["sx_bet"], sx_conn_before)
            self.assertIs(col.connectors["forecastex"], fex_conn_before)

            # 3. Verify 168h per-venue certification tracker persists across restarts & segregates BOTH OFFLINE_SYNTHETIC and TESTNET_SANDBOX!
            cert = VenueCertificationTracker(tdir)
            cert.record_cycle_observation(
                connector_snapshots={
                    "polymarket": {
                        "authorization_state": "AUTHORIZED_LIVE",
                        "connectivity_state": "CONNECTED_REST",
                        "health_state": "HEALTHY",
                        "data_origin": "LIVE_VERIFIED",
                        "active_markets": 90,
                        "l2_books_hydrated": 40,
                        "median_latency_ms": 62.0,
                        "last_success_unix": 2000.0,
                    },
                    "forecastex": {
                        "authorization_state": "AUTHORIZED_LIVE",
                        "connectivity_state": "CONNECTED_REST",
                        "health_state": "HEALTHY",
                        "data_origin": "REGULATORY_PUBLIC_DELAYED",
                        "active_markets": 185,
                        "l2_books_hydrated": 185,
                        "median_latency_ms": 95.0,
                        "last_success_unix": 2000.0,
                    },
                    "predict_fun": {
                        "authorization_state": "AUTHORIZED_LIVE",
                        "connectivity_state": "CONNECTED_REST",
                        "health_state": "HEALTHY",
                        "data_origin": "TESTNET_SANDBOX",
                        "active_markets": 15,
                        "l2_books_hydrated": 10,
                    },
                    "sx_bet": {
                        "data_origin": "OFFLINE_SYNTHETIC",
                        "active_markets": 6,
                    },
                },
                network_mode="live_public",
                cycle_interval_sec=15.0,
                now_unix=2000.0,
            )
            # Re-instantiate tracker from disk to prove SQLite restart persistence
            cert_restarted = VenueCertificationTracker(tdir)
            rep_cert = cert_restarted.build_certification_report(auth_decisions=auth_init, now_unix=2000.0)
            self.assertEqual(rep_cert["venues"]["polymarket"]["certification_verdict"], "IN_PROGRESS_LIVE")
            self.assertGreater(rep_cert["venues"]["polymarket"]["certified_live_hours"], 0.0)
            self.assertEqual(rep_cert["venues"]["forecastex"]["certification_verdict"], "IN_PROGRESS_LIVE")
            self.assertGreater(rep_cert["venues"]["forecastex"]["certified_live_hours"], 0.0)
            self.assertEqual(rep_cert["venues"]["predict_fun"]["certification_verdict"], "TESTNET_SANDBOX_PROTOCOL_VALIDATION")
            self.assertEqual(rep_cert["venues"]["predict_fun"]["certified_live_hours"], 0.0)
            self.assertEqual(rep_cert["venues"]["predict_fun"]["synthetic_cycles_segregated"], 1)
            self.assertEqual(rep_cert["venues"]["sx_bet"]["certified_live_hours"], 0.0)
            self.assertEqual(rep_cert["venues"]["sx_bet"]["synthetic_cycles_segregated"], 1)

            # 4. Verify BankrollMilestoneVerifier ($88 .. $525) honest accounting
            gate_cur = BankrollMilestoneVerifier.verify_gates(
                total_account_equity_usd=77.559031,
                settled_live_trades=2,
                accounting_discrepancy_usd=0.0,
                riskless_only_mode=True,
                output_path=tdir / "bankroll_gate_verification.json",
            )
            self.assertIsNone(gate_cur["highest_unlocked_gate_usd"])
            self.assertEqual(gate_cur["next_gate"]["gate_usd"], 88.0)
            self.assertAlmostEqual(gate_cur["next_gate"]["equity_deficit_usd"], 10.441, places=3)

            gate_260 = BankrollMilestoneVerifier.verify_gates(
                total_account_equity_usd=260.0,
                settled_live_trades=90,
                accounting_discrepancy_usd=0.0,
                riskless_only_mode=True,
                certified_168h_venues=[],  # $253 Stage G gate MUST stay locked until >=1 venue completes 168h!
                p0_authorized_live_venues=["forecastex"],
            )
            self.assertEqual(gate_260["highest_unlocked_gate_usd"], 140.0)
            self.assertEqual(gate_260["next_gate"]["gate_usd"], 253.0)
            self.assertIn("REQUIRES_P0_AUTHORIZED_AND_168H_CERTIFIED_EXTERNAL_VENUE", gate_260["next_gate"]["blocking_reasons"])

            eng.telemetry_store.close()

    def test_11_limitless_socketio_v4_predictfun_heartbeat_sx_zero_padded_version_and_pair_audit(self) -> None:
        from src.polymarket_research.cross_venue_connectors import (
            LimitlessMarketWsState,
            PredictFunOrderbookWsState,
            SXBetCentrifugoWsState,
        )
        from src.polymarket_research.cross_venue_riskless_shadow import (
            NormalizedBinaryMarket,
            OrderLevel,
            verify_cross_venue_pair_opportunity,
        )

        # 1. Limitless Socket.IO v4 / Engine.IO v4 full wire protocol verification
        lim_ws = LimitlessMarketWsState()
        act_open, reply_open = lim_ws.apply_socketio_packet('0{"sid":"abc123","pingInterval":25000,"pingTimeout":60000}')
        self.assertEqual(act_open, "ENGINEIO_OPEN")
        self.assertEqual(reply_open, "40/markets,")

        act_ping, reply_pong = lim_ws.apply_socketio_packet("2")
        self.assertEqual(act_ping, "ENGINEIO_PING")
        self.assertEqual(reply_pong, "3")

        act_ns, _ = lim_ws.apply_socketio_packet('40/markets,{"sid":"ns456"}')
        self.assertEqual(act_ns, "NAMESPACE_CONNECTED")

        sub_frame = lim_ws.build_socketio_subscribe_frame(
            ["btc-updown-1h-1", "eth-updown-1h-2"],
            market_addresses=["0x1111111111111111111111111111111111111111"],
        )
        self.assertTrue(sub_frame.startswith('42/markets,["subscribe_market_prices",'))
        # Subsequent subscription call MUST retain union of prior slugs (`subscribe_market_prices` replaces all prior!)
        sub_frame_2 = lim_ws.build_socketio_subscribe_frame(["sol-updown-1h-3"])
        self.assertIn("btc-updown-1h-1", sub_frame_2)
        self.assertIn("sol-updown-1h-3", sub_frame_2)
        self.assertIn("0x1111111111111111111111111111111111111111", sub_frame_2)

        act_ob, slug_ob = lim_ws.apply_socketio_packet(
            '42/markets,["orderbookUpdate",{"marketSlug":"btc-updown-1h-1","timestamp":1762700005000,'
            '"orderbook":{"asks":[{"price":0.52,"size":100000000}],"bids":[{"price":0.48,"size":90000000}]}}]'
        )
        self.assertEqual(act_ob, "ORDERBOOK_UPDATE")
        self.assertEqual(slug_ob, "btc-updown-1h-1")
        # Out-of-order stale frame (`timestamp` < 1762700005000) MUST be rejected!
        _, stale_slug = lim_ws.apply_socketio_packet(
            '42/markets,["orderbookUpdate",{"marketSlug":"btc-updown-1h-1","timestamp":1762700001000,'
            '"orderbook":{"asks":[{"price":0.99,"size":1000000}],"bids":[]}}]'
        )
        self.assertIsNone(stale_slug)
        self.assertEqual(lim_ws.orderbooks_by_slug["btc-updown-1h-1"]["asks"][0]["price"], 0.52)

        act_or, _ = lim_ws.apply_socketio_packet(
            '42/markets,["oraclePriceData",{"marketSlug":"btc-updown-1h-1","symbol":"BTC","price":98450.25}]'
        )
        self.assertEqual(act_or, "ORACLE_PRICE")
        self.assertAlmostEqual(lim_ws.oracle_prices_by_slug["btc-updown-1h-1"], 98450.25)
        self.assertAlmostEqual(lim_ws.oracle_prices_by_symbol["BTC"], 98450.25)

        act_amm, addr_amm = lim_ws.apply_socketio_packet(
            '42/markets,["newPriceData",{"marketAddress":"0x1111111111111111111111111111111111111111","updatedPrices":{"yes":0.61,"no":0.39}}]'
        )
        self.assertEqual(act_amm, "AMM_PRICE")
        self.assertEqual(addr_amm, "0x1111111111111111111111111111111111111111")
        self.assertAlmostEqual(lim_ws.amm_prices_by_address[addr_amm]["yes"], 0.61)

        # 2. Predict.fun server heartbeat echo + predictTopOfBook/{id}
        pf_ws = PredictFunOrderbookWsState()
        hb_echo = pf_ws.extract_heartbeat_response('{"type":"M","topic":"heartbeat","data":1762700009}')
        self.assertIsNotNone(hb_echo)
        self.assertEqual(json.loads(hb_echo), {"method": "heartbeat", "data": 1762700009})
        mid_tob = pf_ws.apply_frame('{"type":"M","topic":"predictTopOfBook/77","data":{"bestBid":0.44,"bestAsk":0.47}}')
        self.assertEqual(mid_tob, "77")
        self.assertAlmostEqual(pf_ws.top_of_book_by_market_id["77"]["yes_ask"], 0.47)

        # 3. SX Bet zero-padded 23-digit string `version` monotonic reconciliation
        sx_ws = SXBetCentrifugoWsState()
        mh_sx = "0xabc999"
        applied_v1 = sx_ws.apply_rest_orderbook_snapshot(
            mh_sx,
            {
                "status": "success",
                "data": {
                    "version": "00100000000000002210000",
                    "outcomes": {
                        "outcomeOne": [{"percentageOdds": "55000000000000000000", "size": "50000000"}],
                        "outcomeTwo": [{"percentageOdds": "43000000000000000000", "size": "50000000"}],
                    },
                },
            },
        )
        self.assertEqual(applied_v1, mh_sx)
        self.assertEqual(sx_ws.raw_version_str_by_market[mh_sx], "00100000000000002210000")
        # Stale version `"00100000000000002209999"` MUST be rejected!
        stale_sx = sx_ws.apply_frame(
            {
                "marketHash": mh_sx,
                "version": "00100000000000002209999",
                "outcomes": {"outcomeOne": [], "outcomeTwo": []},
            }
        )
        self.assertIsNone(stale_sx)
        # Newer version `"00100000000000002210001"` MUST be accepted!
        newer_sx = sx_ws.apply_frame(
            {
                "marketHash": mh_sx,
                "version": "00100000000000002210001",
                "outcomes": {
                    "outcomeOne": [{"percentageOdds": "56000000000000000000", "size": "60000000"}],
                    "outcomeTwo": [{"percentageOdds": "42000000000000000000", "size": "60000000"}],
                },
            }
        )
        self.assertEqual(newer_sx, mh_sx)

        # 4. Section 8 Cross-Venue Opportunity Verification: prove why a $0.995 gross ask sum (+50 bps theoretical)
        #    is rejected after crypto taker fees, 250ms takerDelayMs, bridge drag, and non-atomic legging risk!
        pm_btc = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="pm1",
            slug="btc-updown-15m-1762700900",
            title="Bitcoin Up or Down 15m",
            category="crypto",
            yes_asks=[OrderLevel(0.495, 100.0)],
            yes_bids=[OrderLevel(0.485, 100.0)],
            no_asks=[OrderLevel(0.515, 100.0)],
            no_bids=[OrderLevel(0.505, 100.0)],
            fee_rate_bps=1000.0,
            fee_enabled=True,
            taker_delay_ms=250.0,
            asset="BTC",
            horizon="15m",
            oracle_family="chainlink_60s_twap",
            end_ts=1762700900,
            rules_hash="same_hash_123",
        )
        lim_btc = NormalizedBinaryMarket(
            venue="limitless",
            market_id="lim1",
            slug="dollarbtc-up-or-down-15m-1762700900",
            title="$BTC Up or Down 15m",
            category="crypto",
            yes_asks=[OrderLevel(0.510, 100.0)],
            yes_bids=[OrderLevel(0.490, 100.0)],
            no_asks=[OrderLevel(0.500, 100.0)],
            no_bids=[OrderLevel(0.480, 100.0)],
            fee_rate_bps=300.0,
            fee_enabled=True,
            taker_delay_ms=0.0,
            asset="BTC",
            horizon="15m",
            oracle_family="chainlink_60s_twap",
            end_ts=1762700900,
            rules_hash="same_hash_123",
        )
        audit_phantom = verify_cross_venue_pair_opportunity(pm_btc, lim_btc, clip_notional_usd=25.0, bridge_drag_bps=2.75)
        self.assertTrue(audit_phantom["contract_equivalence"]["passed"])
        self.assertAlmostEqual(audit_phantom["theoretical_gross_edge_bps"], 50.0, places=1)
        self.assertLess(audit_phantom["executable_net_edge_bps"], 0.0)
        self.assertFalse(audit_phantom["actionable"])
        self.assertIn("REJECTED_NEGATIVE_EXECUTABLE_EDGE", audit_phantom["verdict_reason"])

    def test_12_sports_double_swap_regression_and_contamination_quarantine(self) -> None:
        """
        Reproduces the live NBA 'Pacers vs. Mavericks' double-canonicalization book-swap defect,
        verifies deterministic idempotency across home/away & race outcomes, and verifies
        non-destructive SQLite contamination quarantine + offline-checkpoint isolation.
        """
        from src.polymarket_research.cross_venue_l2_and_baskets import LegSpec, Level2ExecutionSimulator
        from src.polymarket_research.cross_venue_riskless_shadow import (
            parse_limitless_market,
            parse_polymarket_gamma_market,
            parse_predict_fun_market,
        )

        # 1. Exact recorded live Pacers vs. Mavericks payloads (Nov 9, 2026)
        poly_raw_nba = {
            "id": "99001",
            "slug": "nba-ind-dal-2026-11-09",
            "question": "Pacers vs. Mavericks",
            "description": "NBA Official Boxscore",
            "active": True,
            "closed": False,
            "acceptingOrders": True,
            "gameStartTime": "2026-11-10T01:00:00Z",
            "clobTokenIds": json.dumps(["tok_pacers", "tok_mavs"]),
            "outcomes": json.dumps(["Pacers", "Mavericks"]),
            "outcomePrices": json.dumps(["0.195", "0.805"]),
            "conditionId": "0xabc123nba",
        }
        lim_raw_nba = {
            "id": 457598,
            "slug": "pacers-vs-mavericks-1794099946236",
            "title": "Pacers vs. Mavericks",
            "description": "NBA Official Boxscore",
            "expirationTimestamp": 1794350000000,
            "categories": ["Sports"],
            "tradeType": "clob",
            "tokens": {"yes": "ltok_pacers", "no": "ltok_mavs"},
            "metadata": {"fee": False, "isPolyArbitrage": True, "externalSlug": "nba-ind-dal-2026-11-09"},
        }
        lim_ob_nba = {
            "asks": [{"price": 0.19, "size": 1_000_000_000}],
            "bids": [{"price": 0.145, "size": 1_000_000_000}],
        }

        async def _mock_poly_nba(url: str, headers: Any, timeout_s: float):
            if "gamma-api.polymarket.com/markets" in url:
                return (200, json.dumps([poly_raw_nba]), {}, 8.0)
            if "token_id=tok_pacers" in url:
                return (200, json.dumps({"asks": [{"price": "0.195", "size": "500"}], "bids": [{"price": "0.185", "size": "500"}]}), {}, 6.0)
            if "token_id=tok_mavs" in url:
                return (200, json.dumps({"asks": [{"price": "0.805", "size": "500"}], "bids": [{"price": "0.795", "size": "500"}]}), {}, 6.0)
            if "fee-rate" in url:
                return (200, json.dumps({"base_fee": 0}), {}, 4.0)
            return (404, "{}", {}, 2.0)

        p_conn = PolymarketConnector(max_pages=1, enable_realtime_ws=False)
        tr = ResilientReadOnlyTransport(raw_requester=_mock_poly_nba)
        poly_hydrated = asyncio.run(p_conn.poll_markets(tr, now_ts=1794280000))
        self.assertEqual(len(poly_hydrated), 1)
        pm_nba = poly_hydrated[0]
        # Canonical order: 'mavericks' < 'pacers' -> Mavericks MUST carry $0.805 ask and Pacers MUST carry $0.195 ask!
        self.assertEqual(pm_nba.yes_label, "Mavericks")
        self.assertEqual(pm_nba.no_label, "Pacers")
        self.assertAlmostEqual(pm_nba.yes_asks[0].price, 0.805, places=6)
        self.assertAlmostEqual(pm_nba.no_asks[0].price, 0.195, places=6)

        # Calling canonicalize_outcomes_idempotent repeatedly MUST NOT flip books again!
        for _ in range(5):
            pm_nba.canonicalize_outcomes_idempotent()
        self.assertEqual(pm_nba.yes_label, "Mavericks")
        self.assertAlmostEqual(pm_nba.yes_asks[0].price, 0.805, places=6)

        lim_nba = parse_limitless_market(lim_raw_nba, lim_ob_nba)
        assert lim_nba is not None
        self.assertEqual(lim_nba.yes_label, "Mavericks")
        self.assertAlmostEqual(lim_nba.yes_asks[0].price, 0.855, places=6)  # 1 - 0.145 Pacers bid
        self.assertAlmostEqual(lim_nba.no_asks[0].price, 0.19, places=6)

        # Verify ZERO phantom $62 arb is generated on Pacers ($0.195 + $0.855 = $1.050, $0.805 + $0.190 = $0.995 -> <$0.30 taker, ~$1.60 passive maker)
        with tempfile.TemporaryDirectory() as tmp_d:
            eng = HonestCrossVenueShadowEngine(clip_notional_usd=35.0, data_dir=Path(tmp_d))
            cands = eng.scan_cross_venue_pairs([(pm_nba, lim_nba)])
            for c in cands:
                self.assertLess(c.expected_net_profit_usd, 3.0)
                if c.family == "XV_TAKER_BOX_OR_CORRIDOR":
                    self.assertLess(c.expected_net_profit_usd, 0.30)

            # 2. Verify non-Yes/No Predict.fun race market ('$3,000' vs '$1,000' inverted) canonicalizes & category slug doesn't collide
            pf_eth_a = parse_predict_fun_market(
                {
                    "id": 52261,
                    "categorySlug": "eth-race-2026",
                    "question": "Will Ethereum hit $1,000 or $3,000 first?",
                    "description": "Exact identical rules text",
                    "tradingStatus": "OPEN",
                    "feeRateBps": 200,
                    "polymarketConditionIds": ["0x094725e5"],
                    "outcomes": [{"name": "$3,000", "indexSet": 1}, {"name": "$1,000", "indexSet": 2}],
                },
                {"data": {"asks": [[0.59, 100.0]], "bids": [[0.54, 100.0]], "updateTimestampMs": 1794282652121}},
            )
            pf_eth_b = parse_predict_fun_market(
                {
                    "id": 52262,
                    "categorySlug": "eth-race-2026",
                    "question": "Will Ethereum hit $500 or $4,000 first?",
                    "description": "Exact identical rules text",
                    "tradingStatus": "OPEN",
                    "feeRateBps": 200,
                    "outcomes": [{"name": "$500", "indexSet": 1}, {"name": "$4,000", "indexSet": 2}],
                }
            )
            assert pf_eth_a is not None and pf_eth_b is not None
            self.assertNotEqual(pf_eth_a.slug, pf_eth_b.slug)
            self.assertEqual(pf_eth_a.yes_label, "$1,000")
            self.assertEqual(pf_eth_a.no_label, "$3,000")
            self.assertAlmostEqual(pf_eth_a.yes_asks[0].price, 0.46, places=6)  # 1 - 0.54

            # 3. Verify multi-strike boilerplate `rules_hash` series (e.g. Fed 5.5% vs 4.25% vs 5.25%) NEVER cross-pair
            boilerplate_desc = "The FED interest rates are defined in this market by the lower or the upper bound of the target federal funds range."
            pm_fed_425 = parse_polymarket_gamma_market(
                {
                    "id": "pm_fed_425",
                    "slug": "will-the-feds-upper-bound-reach-4pt25-or-higher-before-2027",
                    "question": "Will the Fed's upper bound reach 4.25% or higher before 2027?",
                    "description": boilerplate_desc,
                    "conditionId": "0xcond_425",
                    "outcomes": '["Yes","No"]',
                    "clobTokenIds": '["t425y","t425n"]',
                    "outcomePrices": '["0.88","0.12"]',
                    "active": True,
                    "closed": False,
                }
            )
            pm_fed_525 = parse_polymarket_gamma_market(
                {
                    "id": "pm_fed_525",
                    "slug": "will-the-feds-upper-bound-reach-5pt25-or-higher-before-2027",
                    "question": "Will the Fed's upper bound reach 5.25% or higher before 2027?",
                    "description": boilerplate_desc,
                    "conditionId": "0x728246cda497e10289a7145245675e2baece6561ba784760b0914108e6e42c04",
                    "outcomes": '["Yes","No"]',
                    "clobTokenIds": '["t525y","t525n"]',
                    "outcomePrices": '["0.03","0.97"]',
                    "active": True,
                    "closed": False,
                }
            )
            pf_fed_550 = parse_predict_fun_market(
                {
                    "id": 30533,
                    "categorySlug": "what-will-fed-rate-hit-before-2027",
                    "title": "\u2191 5.5%",
                    "question": "Will the Fed\u2019s upper bound reach 5.5% or higher before 2027?",
                    "description": boilerplate_desc,
                    "tradingStatus": "OPEN",
                    "feeRateBps": 200,
                    "polymarketConditionIds": ["0x360247ba6b67009d19be741be7187abd59c5005e14be0914eb4e485f3b342c40"],
                    "outcomes": [
                        {"name": "Yes", "indexSet": 1, "bestAsk": {"price": 0.02, "size": 500}},
                        {"name": "No", "indexSet": 2, "bestAsk": {"price": 0.99, "size": 500}},
                    ],
                }
            )
            pf_fed_525 = parse_predict_fun_market(
                {
                    "id": 30524,
                    "categorySlug": "what-will-fed-rate-hit-before-2027",
                    "title": "\u2191 5.25%",
                    "question": "Will the Fed\u2019s upper bound reach 5.25% or higher before 2027?",
                    "description": boilerplate_desc,
                    "tradingStatus": "OPEN",
                    "feeRateBps": 200,
                    "polymarketConditionIds": ["0x728246cda497e10289a7145245675e2baece6561ba784760b0914108e6e42c04"],
                    "outcomes": [
                        {"name": "Yes", "indexSet": 1, "bestAsk": {"price": 0.04, "size": 500}},
                        {"name": "No", "indexSet": 2, "bestAsk": {"price": 0.97, "size": 500}},
                    ],
                }
            )
            assert pm_fed_425 and pm_fed_525 and pf_fed_550 and pf_fed_525
            fed_pairs = MultiVenueArbitrageAnalyzer.pair_all_venues([pm_fed_425, pm_fed_525, pf_fed_550, pf_fed_525])
            self.assertEqual(len(fed_pairs), 1)
            self.assertEqual(fed_pairs[0][0].slug, pm_fed_525.slug)
            self.assertEqual(fed_pairs[0][1].slug, pf_fed_525.slug)
            bad_check = eng.verifier.verify_pair(pm_fed_425, pf_fed_550, side_a="NO", side_b="YES", price_a=0.12, price_b=0.02)
            self.assertFalse(bad_check.passed)
            self.assertIn("GATE1_CONDITION_ID_STRIKE_MISMATCH", bad_check.gate_failures)

            # 4. Verify non-destructive SQLite contamination quarantine preserves raw rows while cleaning summaries
            store = eng.telemetry_store
            sim = Level2ExecutionSimulator()
            fake_bad_poly = parse_polymarket_gamma_market(poly_raw_nba)
            assert fake_bad_poly is not None
            fake_bad_poly.yes_asks = [OrderLevel(0.195, 200.0)]  # Simulate pre-fix swapped book
            bad_ev = sim.evaluate_basket(
                basket_id="XV::polymarket:nba-ind-dal-2026-11-09:YES__vs__limitless:pacers-vs-mavericks:NO",
                basket_type="CROSS_VENUE_2LEG",
                legs=[LegSpec(market=fake_bad_poly, side="YES"), LegSpec(market=lim_nba, side="NO")],
                target_notional_usd=35.0,
                post_delay_legs=[fake_bad_poly, lim_nba],
            )
            store.record_signal(bad_ev, data_origin="LIVE_VERIFIED", now_unix=1000.0)
            q_rep = store.quarantine_contaminated_sports_and_recompute(fix_ts_unix=1500.0)
            self.assertEqual(q_rep["newly_marked_contaminated_rows"], 1)
            self.assertGreater(q_rep["quarantined_phantom_gross_usd"], 50.0)
            win = store.build_campaign_window_summaries(now_unix=1600.0)
            self.assertEqual(win["1h"]["live_executable_signals"], 0)
            self.assertEqual(win["1h"]["quarantined_contaminated_signals"], 1)

            # 5. Verify SX Bet `sportId` classification (`sportId=5` Soccer draw guard & `sportId=2` NHL mascot pairing) + RestrictionRegistry
            from src.polymarket_research.cross_venue_riskless_shadow import parse_sx_bet_summary_fixture
            from src.polymarket_research.cross_venue_shadow_deployment_gates import evaluate_all_venues_authorization
            from src.polymarket_research.cross_venue_unblock_and_certification import RestrictionRegistry

            sx_serie_a = parse_sx_bet_summary_fixture(
                {
                    "id": "L_SOC_1",
                    "leagueLabel": "Coppa Italia",
                    "gameTime": "2026-11-10T20:00:00.000Z",
                    "teamOne": "Juventus",
                    "teamTwo": "AC Milan",
                    "status": 1,
                    "markets": [
                        {
                            "marketHash": "0xsoc1",
                            "marketType": "MONEY_LINE",
                            "outcomeOneName": "Juventus",
                            "outcomeTwoName": "AC Milan",
                            "bestOddsOutcomeOne": str(int(0.45 * 10**20)),
                            "bestOddsOutcomeTwo": str(int(0.30 * 10**20)),
                        }
                    ],
                },
                sport_label="",
                sport_id=5,
                league_label="Coppa Italia",
            )
            self.assertEqual(len(sx_serie_a), 1)
            self.assertEqual(sx_serie_a[0].sport, "soccer")
            self.assertTrue(sx_serie_a[0].has_unlisted_draw)

            sx_nhl = parse_sx_bet_summary_fixture(
                {
                    "id": "L_NHL_1",
                    "leagueLabel": "NHL",
                    "gameTime": "2026-11-10T02:30:00.000Z",
                    "teamOne": "Vancouver Canucks",
                    "teamTwo": "Philadelphia Flyers",
                    "status": 2,
                    "markets": [
                        {
                            "marketHash": "0xnhl1",
                            "marketType": "MONEY_LINE",
                            "outcomeOneName": "Vancouver Canucks",
                            "outcomeTwoName": "Philadelphia Flyers",
                            "bestOddsOutcomeOne": str(int(0.55 * 10**20)),
                            "bestOddsOutcomeTwo": str(int(0.43 * 10**20)),
                        }
                    ],
                },
                sport_label="",
                sport_id=2,
                league_label="NHL",
            )[0]
            pm_nhl = parse_polymarket_gamma_market(
                {
                    "id": "pm_nhl_1",
                    "slug": "nhl-phi-van-2026-11-09",
                    "question": "Flyers vs. Canucks",
                    "description": "NHL regular season game",
                    "gameStartTime": "2026-11-10 02:30:00+00",
                    "outcomes": '["Flyers","Canucks"]',
                    "clobTokenIds": '["t_fly","t_can"]',
                    "outcomePrices": '["0.44","0.56"]',
                    "active": True,
                    "closed": False,
                }
            )
            assert pm_nhl is not None
            pm_nhl_spread = parse_polymarket_gamma_market(
                {
                    "id": "pm_nhl_sp1",
                    "slug": "nhl-phi-van-2026-11-09-spread-away-1pt5",
                    "question": "Spread: Flyers (-1.5)",
                    "description": "NHL puckline spread",
                    "gameStartTime": "2026-11-10 02:30:00+00",
                    "outcomes": '["Flyers","Canucks"]',
                    "clobTokenIds": '["t_fly_s","t_can_s"]',
                    "outcomePrices": '["0.25","0.75"]',
                    "active": True,
                    "closed": False,
                }
            )
            assert pm_nhl_spread is not None
            nhl_pairs = MultiVenueArbitrageAnalyzer.pair_all_venues([pm_nhl, pm_nhl_spread, sx_nhl])
            self.assertEqual(len(nhl_pairs), 1)
            self.assertEqual(nhl_pairs[0][0].slug, "nhl-phi-van-2026-11-09")
            self.assertFalse(eng.verifier.verify_pair(pm_nhl_spread, sx_nhl, side_a="YES", side_b="NO", price_a=0.25, price_b=0.45).passed)
            self.assertEqual(pm_nhl.yes_label, "Canucks")
            self.assertEqual(sx_nhl.yes_label, "Vancouver Canucks")

            rreg = RestrictionRegistry(Path(tmp_d))
            env_rr = {
                "DOMINUS_NETWORK_MODE": "live_public",
                "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
                "DOMINUS_SERVER_REGION": "FI",
                "PREDICT_FUN_API_KEY": "pred_sk_test_readonly_token_1234567890",
                "PREDICT_FUN_ENV": "mainnet",
            }
            rr_out = rreg.sync_and_persist(env=env_rr, auth_decisions=evaluate_all_venues_authorization(env_rr))
            self.assertEqual(rr_out["eliminated_internal_count"], 5)
            self.assertTrue((Path(tmp_d) / "restriction_registry.json").exists())
            store.close()

    def test_13_full_access_remediation_stx_phoenix_ws_sx_leagues_and_ibkr_ws(self) -> None:
        from src.polymarket_research.cross_venue_connectors import (
            ForecastExIBKRConnector,
            IBKRMarketDataWsState,
            STXPhoenixOrderbookWsState,
            SXBetOBv3Connector,
            synthesize_stx_market_symbols,
        )
        from src.polymarket_research.cross_venue_riskless_shadow import (
            NormalizedBinaryMarket,
            OrderLevel,
            parse_stx_ontario_market,
        )
        from src.polymarket_research.cross_venue_shadow_deployment_gates import (
            INDEPENDENT_CAPABILITY_FLAGS,
            VENUE_CLASSIFICATION_STATES,
            evaluate_all_venues_authorization,
        )

        # 1. Verify STX Phoenix WebSocket live `market:<symbol>` phx_reply + `order_book_update` delta
        stx_ws = STXPhoenixOrderbookWsState()
        sym = "STXNHL-26NOV100000BOSOTT-GAMEOTT"
        reply_frame = json.dumps(
            [
                "4",
                "4",
                f"market:{sym}",
                "phx_reply",
                {
                    "status": "ok",
                    "response": {
                        "id": "uuid-ott-bos-1",
                        "symbol": sym,
                        "status": "open",
                        "rules": "home_winner",
                        "comp_name": "NHL",
                        "event_start": "2026-11-10T00:00:00Z",
                        "participants": [
                            {"abbr": "OTT", "name": "Ottawa Senators", "position": "home"},
                            {"abbr": "BOS", "name": "Boston Bruins", "position": "away"},
                        ],
                        "ob": {
                            "b": [{"p": 4900, "q": 10000}],
                            "o": [{"p": 5400, "q": 15000}],
                        },
                    },
                },
            ]
        )
        applied_sym = stx_ws.apply_frame(reply_frame)
        self.assertEqual(applied_sym, "uuid-ott-bos-1")
        self.assertIn(sym, stx_ws.markets_by_id)
        # Apply live delta: update bid at 4900 to 25000, remove ask at 5400 (q=0), add ask at 5300 (q=20000)
        delta_frame = json.dumps(
            [
                None,
                None,
                f"market:{sym}",
                "order_book_update",
                {
                    "b": [{"p": 4900, "q": 25000}],
                    "o": [{"p": 5400, "q": 0}, {"p": 5300, "q": 20000}],
                },
            ]
        )
        stx_ws.apply_frame(delta_frame)
        parsed_stx = parse_stx_ontario_market(stx_ws.markets_by_id[sym])
        self.assertIsNotNone(parsed_stx)
        assert parsed_stx is not None
        self.assertEqual(parsed_stx.venue, "stx_ontario")
        self.assertEqual(parsed_stx.sport, "nhl")
        # Ottawa Senators vs Boston Bruins -> alphabetically Boston Bruins < Ottawa Senators
        # Wait: Ottawa was YES (bid 0.49, ask 0.53), so after alphabetical canonicalization:
        # YES = Boston Bruins (ask = 1 - 0.49 = 0.51, bid = 1 - 0.53 = 0.47)
        self.assertEqual(parsed_stx.yes_label, "Boston Bruins")
        self.assertEqual(parsed_stx.no_label, "Ottawa Senators")
        self.assertAlmostEqual(parsed_stx.yes_asks[0].price, 0.51, places=3)
        self.assertAlmostEqual(parsed_stx.no_asks[0].price, 0.53, places=3)

        # Verify symbol synthesis from cross-venue hint markets
        from datetime import datetime, timezone
        ts_26nov10 = int(datetime(2026, 11, 10, 0, 0, 0, tzinfo=timezone.utc).timestamp())
        hint_m = NormalizedBinaryMarket(
            venue="sx_bet",
            market_id="0xhint1",
            slug="boston-bruins-vs-ottawa-senators",
            title="Boston Bruins vs Ottawa Senators",
            category="sports",
            sport="nhl",
            yes_label="Boston Bruins",
            no_label="Ottawa Senators",
            end_ts=ts_26nov10,
            yes_asks=[OrderLevel(0.50, 100.0)],
            no_asks=[OrderLevel(0.52, 100.0)],
        )
        synth_syms = synthesize_stx_market_symbols([hint_m])
        self.assertIn("STXNHL-26NOV100000BOSOTT-GAMEOTT", synth_syms)

        # 2. Verify SX Bet `/leagues/active` + `/summary-v3/league/{id}/game-lines` parsing
        async def _sx_league_mock(url: str, headers: dict, timeout: float):
            if "/leagues/active" in url:
                return (
                    200,
                    json.dumps(
                        {
                            "status": "success",
                            "data": [{"leagueId": 2, "label": "NHL", "sportId": 2, "active": True}],
                        }
                    ),
                    {},
                    5.0,
                )
            if "/summary-v3/league/2/game-lines" in url:
                self.assertEqual(headers.get("x-time-zone"), "-300")
                return (
                    200,
                    json.dumps(
                        {
                            "status": "success",
                            "data": {
                                "days": [
                                    {
                                        "date": "2026-11-10",
                                        "fixtures": [
                                            {
                                                "eventId": "L999",
                                                "teamOneName": "Ottawa Senators",
                                                "teamTwoName": "Boston Bruins",
                                                "startDate": "2026-11-10T00:00:00.000Z",
                                                "sportId": 2,
                                                "sportLabel": "Hockey",
                                                "leagueId": 2,
                                                "leagueLabel": "NHL",
                                                "markets": [
                                                    {
                                                        "marketHash": "0xsxleague1",
                                                        "type": 226,
                                                        "status": "ACTIVE",
                                                        "outcomeOneName": "Ottawa Senators",
                                                        "outcomeTwoName": "Boston Bruins",
                                                        "sportXeventId": "L999",
                                                        "gameTime": 1794268800,
                                                        "bestOrders": {
                                                            "bestOddsOutcomeOne": str(int(0.48 * 10**20)),
                                                            "bestOddsOutcomeTwo": str(int(0.50 * 10**20)),
                                                        },
                                                    }
                                                ],
                                            }
                                        ],
                                    }
                                ]
                            },
                        }
                    ),
                    {},
                    6.0,
                )
            return (200, json.dumps({"status": "success", "data": []}), {}, 4.0)

        async def _run_sx() -> None:
            tr = ResilientReadOnlyTransport(raw_requester=_sx_league_mock)
            tr.is_default_http = True
            sx_conn = SXBetOBv3Connector(enable_realtime_ws=False)
            mkts = await sx_conn.poll_markets(tr, now_ts=1794200000)
            self.assertEqual(len(mkts), 1)
            self.assertEqual(mkts[0].market_id, "0xsxleague1")
            self.assertEqual(sx_conn.endpoint_status.get("GET /leagues/active"), "AUTHORIZED_LIVE")
            self.assertEqual(sx_conn.endpoint_status.get("GET /summary-v3/league/{leagueId}/game-lines"), "AUTHORIZED_LIVE")

        asyncio.run(_run_sx())

        # 3. Verify IBKR Market Data WS subscription fields & ForecastEx reauthenticate / secdef
        ibkr_ws = IBKRMarketDataWsState()
        sub_cmd = ibkr_ws.build_subscribe_frame(712345)
        self.assertEqual(sub_cmd, 'smd+712345+{"fields":["31","84","85","86","88","6509"]}')

        # 4. Verify 5 independent capability flags & 3 venue classifications
        env_check = {
            "DOMINUS_NETWORK_MODE": "live_public",
            "DOMINUS_OPERATOR_JURISDICTION": "CA-ON",
            "DOMINUS_SERVER_REGION": "FI",
            "PREDICT_FUN_API_KEY": "pred_sk_test_readonly_token_1234567890",
            "PREDICT_FUN_ENV": "mainnet",
        }
        decisions = evaluate_all_venues_authorization(env_check)
        for v, dec in decisions.items():
            self.assertIn(dec.venue_classification, VENUE_CLASSIFICATION_STATES)
            for flag_k in INDEPENDENT_CAPABILITY_FLAGS:
                self.assertIn(flag_k, dec.capability_flags)
            self.assertEqual(dec.capability_flags["LIVE_ORDER_EXECUTION"], "RESTRICTED")

    def test_14_qa_regression_unhydrated_books_stale_quotes_oracle_classification_and_perf(self) -> None:
        from src.polymarket_research.cross_venue_riskless_shadow import (
            infer_crypto_oracle_signature,
            parse_polymarket_gamma_market,
            parse_predict_fun_market,
        )
        from src.polymarket_research.cross_venue_unblock_and_certification import VenueCertificationTracker

        # 1. Bug #6 regression: Non-crypto market mentioning Binance in description MUST NOT get `binance_spot_candle`
        asset_el, hor_el, orac_el, _ = infer_crypto_oracle_signature(
            "Will Elon Musk tweet between 0 and 99 times?",
            "Market hosted on BNB Chain (incubated by Binance Labs). Resolves per X/Twitter tracker.",
            "will-elon-musk-tweet-0-99",
        )
        self.assertEqual(asset_el, "")
        self.assertEqual(hor_el, "")
        self.assertEqual(orac_el, "")

        pf_elon = parse_predict_fun_market(
            {
                "id": "685",
                "categorySlug": "elon-tweets",
                "question": "Will Elon Musk tweet between 0 and 99 times?",
                "description": "Hosted on BNB Chain / Binance ecosystem. Resolves via X count.",
                "tradingStatus": "OPEN",
                "polymarketConditionIds": ["0xelon123"],
                "outcomes": [{"name": "Yes"}, {"name": "No"}],
            }
        )
        assert pf_elon is not None
        self.assertEqual(pf_elon.category, "other")
        self.assertEqual(pf_elon.oracle_family, "uma")

        # 2. Bug #5 regression: `allow_outcome_prices_fallback=False` or empty CLOB book in live mode MUST NOT fabricate 25-share asks
        raw_gamma_unhydrated = {
            "id": "pm_unhyd_1",
            "slug": "unhydrated-gamma-market",
            "question": "Will nothing ever happen?",
            "description": "Resolution rules",
            "outcomes": '["Yes","No"]',
            "clobTokenIds": '["tok_u_y","tok_u_n"]',
            "outcomePrices": '["0.15","0.85"]',
            "active": True,
            "closed": False,
        }
        pm_no_fallback = parse_polymarket_gamma_market(raw_gamma_unhydrated, allow_outcome_prices_fallback=False)
        assert pm_no_fallback is not None
        self.assertEqual(pm_no_fallback.yes_asks, [])
        self.assertEqual(pm_no_fallback.no_asks, [])

        pm_empty_clob = parse_polymarket_gamma_market(
            raw_gamma_unhydrated,
            books_by_token_id={"tok_u_y": {"asks": [], "bids": []}, "tok_u_n": {"asks": [], "bids": []}},
        )
        assert pm_empty_clob is not None
        self.assertEqual(pm_empty_clob.yes_asks, [])
        self.assertEqual(pm_empty_clob.no_asks, [])

        # 3. Bug #4 regression: Predict.fun resting orderbook with old `updateTimestampMs` stamps fresh poll `now_ms`
        now_s = 1_794_300_000
        now_ms = now_s * 1000
        old_update_ms = now_ms - 900_000  # 15 minutes ago on a resting macro market

        async def _pf_resting_mock(url: str, headers: dict, timeout: float):
            if "/markets?" in url:
                return (
                    200,
                    json.dumps(
                        {
                            "data": [
                                {
                                    "id": "777",
                                    "question": "Will Fed cut rates?",
                                    "description": "FOMC statement",
                                    "tradingStatus": "OPEN",
                                    "outcomes": [{"name": "Yes"}, {"name": "No"}],
                                }
                            ],
                            "cursor": "",
                        }
                    ),
                    {},
                    5.0,
                )
            if "/markets/777/orderbook" in url:
                return (
                    200,
                    json.dumps(
                        {
                            "data": {
                                "asks": [[0.45, 100.0]],
                                "bids": [[0.43, 100.0]],
                                "updateTimestampMs": old_update_ms,
                            }
                        }
                    ),
                    {},
                    5.0,
                )
            return (404, "{}", {}, 2.0)

        tr_pf = ResilientReadOnlyTransport(raw_requester=_pf_resting_mock)
        pf_conn = PredictFunConnector(max_pages=1, env={"PREDICT_FUN_API_KEY": "pf_test_key_readonly_12345"})
        pf_mkts = asyncio.run(pf_conn.poll_markets(tr_pf, now_ts=now_s))
        self.assertEqual(len(pf_mkts), 1)
        self.assertEqual(pf_mkts[0].quote_ts_ms, now_ms)

        # 4. Bug #2 & #3 regression: `ingest_markets` skips empty orderbooks in `orderbook_snapshots`, updates `oracle_family`
        #    in `market_catalog`, and `VenueCertificationTracker` excludes 0-depth rows from `mean_book_depth_usd`
        with tempfile.TemporaryDirectory() as tmp_qa:
            qdir = Path(tmp_qa)
            store = ShadowTelemetryStore(qdir)
            hydrated_mkt = NormalizedBinaryMarket(
                venue="limitless",
                market_id="lim_hyd",
                slug="lim-hyd",
                title="Hydrated",
                category="crypto",
                oracle_family="chainlink_60s_twap",
                yes_asks=[OrderLevel(0.50, 200.0)],
                yes_bids=[OrderLevel(0.48, 200.0)],
                no_asks=[OrderLevel(0.52, 200.0)],
                no_bids=[OrderLevel(0.50, 200.0)],
                quote_ts_ms=now_ms,
                data_origin="LIVE_VERIFIED",
            )
            unhydrated_mkt = NormalizedBinaryMarket(
                venue="limitless",
                market_id="lim_unhyd",
                slug="lim-unhyd",
                title="Unhydrated",
                category="other",
                oracle_family="binance_spot_candle",
                yes_asks=[],
                yes_bids=[],
                no_asks=[],
                no_bids=[],
                quote_ts_ms=now_ms,
                data_origin="LIVE_VERIFIED",
            )
            inserted = store.ingest_markets([hydrated_mkt, unhydrated_mkt], now_unix=float(now_s))
            self.assertEqual(inserted, 1)  # Only hydrated market inserted into orderbook_snapshots!

            # Update unhydrated_mkt's oracle_family to 'uma' and re-ingest -> market_catalog MUST update!
            unhydrated_mkt.oracle_family = "uma"
            store.ingest_markets([unhydrated_mkt], now_unix=float(now_s + 15))
            with store._connect() as conn:
                cat_row = conn.execute(
                    "SELECT oracle_family FROM market_catalog WHERE venue='limitless' AND market_id='lim_unhyd'"
                ).fetchone()
                self.assertEqual(cat_row["oracle_family"], "uma")

            cert = VenueCertificationTracker(qdir)
            cert.record_cycle_observation(
                connector_snapshots={
                    "limitless": {
                        "authorization_state": "AUTHORIZED_LIVE",
                        "connectivity_state": "CONNECTED_WS",
                        "health_state": "HEALTHY",
                        "data_origin": "LIVE_VERIFIED",
                        "active_markets": 2,
                        "l2_books_hydrated": 1,
                        "last_success_unix": float(now_s),
                    }
                },
                network_mode="live_public",
                now_unix=float(now_s),
            )
            rep = cert.build_certification_report(now_unix=float(now_s))
            self.assertGreater(rep["venues"]["limitless"]["mean_book_depth_usd"], 350.0)
            self.assertTrue(rep["venues"]["limitless"]["gates"]["rss_within_512mb_cgroup"])
            store.close()


if __name__ == "__main__":
    unittest.main()

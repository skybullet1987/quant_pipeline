import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.cross_venue_connectors import (
    KalshiPublicConnector,
    PolymarketMarketWsState,
)
from src.polymarket_research.polymarket_direct_feeds import (
    _get_conditional_json_sync,
    compute_adaptive_sports_poll_interval_sec,
    parse_atp_wta_scoreboard,
)
from src.polymarket_research.polymarket_terminal_recorder import (
    L2OrderBook,
    PolymarketDualFeed1HRecorder,
    _fast_resp_json,
)
from src.polymarket_research.polymarket_ws_streams import (
    POLYBOLT_CRYPTO_SYMBOLS,
    PolymarketChainlinkLiveStream,
    PolymarketClobMarketWsTracker,
    PolymarketShardedClobMarketWsTracker,
)
from src.polymarket_research.riskless_fast_feeds import (
    DEFAULT_PYTH_FEED_IDS,
    DeribitPublicWs,
    FROZEN_KMIA_MARKET_IDS,
    HyperliquidCoinbaseWs,
    MacroEventFeedClient,
    PolygonScopedLogsWs,
    PythHermesStream,
    TOPIC_CTF_CONDITION_RESOLUTION,
    TOPIC_OO_DISPUTE_PRICE,
    TOPIC_OO_PROPOSE_PRICE,
    fetch_live_cad_usd_sync,
    fetch_pyth_hermes_latest_sync,
    keccak256_hex,
)
from src.polymarket_research.weather_metar_engine import (
    MetarObservation,
    check_neighbor_station_temp_anomaly,
    parse_nws_dsm_or_cli_text,
)


class _DummyResponse:
    def __init__(self, status_code: int = 200, content: bytes = b"{}", headers=None, text: str = "") -> None:
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = text or content.decode("utf-8", errors="ignore")

    def json(self):
        return json.loads(self.content.decode("utf-8"))


class _DummyAsyncResponse:
    def __init__(self, payload_bytes: bytes) -> None:
        self._raw = payload_bytes

    async def read(self) -> bytes:
        return self._raw


class TestV62RisklessFastFeeds(unittest.TestCase):
    def test_pyth_hermes_stream_and_sync_fetch(self) -> None:
        stream = PythHermesStream(["XAU", "NVDA", "USDCAD"])
        xau_id = DEFAULT_PYTH_FEED_IDS["XAU"]
        sse_line = (
            "data: "
            + json.dumps(
                {
                    "parsed": [
                        {
                            "id": xau_id,
                            "price": {
                                "price": "265012345",
                                "conf": "45000",
                                "expo": -5,
                                "publish_time": int(time.time()),
                            },
                        }
                    ]
                }
            )
        )
        n = stream.process_payload(sse_line)
        self.assertEqual(n, 1)
        q = stream.get_latest("XAUUSD")
        self.assertIsNotNone(q)
        self.assertAlmostEqual(q["price"], 2650.12345, places=5)
        self.assertAlmostEqual(q["conf"], 0.45, places=5)

        class _Sess:
            def get(self, url, **kwargs):
                self.url = url
                return _DummyResponse(
                    200,
                    json.dumps(
                        {
                            "parsed": [
                                {
                                    "id": DEFAULT_PYTH_FEED_IDS["NVDA"],
                                    "price": {
                                        "price": "14250",
                                        "conf": "5",
                                        "expo": -2,
                                        "publish_time": int(time.time()),
                                    },
                                }
                            ]
                        }
                    ).encode("utf-8"),
                )

        res = fetch_pyth_hermes_latest_sync(["NVDA"], session=_Sess())
        self.assertAlmostEqual(res["NVDA"]["price"], 142.50, places=4)

    def test_polygon_scoped_logs_and_d001_kmia_quarantine(self) -> None:
        # Standard keccak-256 test vector check (`PayoutRedemption` & `ConditionResolution`)
        self.assertEqual(
            keccak256_hex("Transfer(address,address,uint256)"),
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
        )
        self.assertTrue(TOPIC_CTF_CONDITION_RESOLUTION.startswith("0x") and len(TOPIC_CTF_CONDITION_RESOLUTION) == 66)

        ws = PolygonScopedLogsWs(funder_address="0x013A2474454fBd8738cff6a7f204eF1bc377F4e9")
        subs = ws.build_subscribe_payloads()
        self.assertEqual(len(subs), 2)
        self.assertEqual(subs[0]["params"][0], "logs")
        self.assertEqual(subs[1]["params"][1]["topics"][1], "0x" + "013a2474454fbd8738cff6a7f204ef1bc377f4e9".zfill(64))

        # KMIA frozen market_id (`6707503`) must NEVER surface in drain_events()
        kmia_hex = "0x" + b"q: market_id: 6707503, title: KMIA".hex()
        evt_kmia = ws.process_ws_message(
            {
                "method": "eth_subscription",
                "params": {
                    "result": {
                        "address": "0x2c0367a9db231ddebd88a94b4f6461a6e47c58b1",
                        "topics": [TOPIC_OO_DISPUTE_PRICE],
                        "data": kmia_hex,
                        "blockNumber": "0x100",
                        "transactionHash": "0xdead",
                    }
                },
            }
        )
        self.assertIsNotNone(evt_kmia)
        self.assertTrue(evt_kmia["quarantined_d001"])
        self.assertEqual(ws.drain_events(), [])

        # Non-KMIA proposal passes cleanly
        ok_hex = "0x" + b"q: market_id: 9876543, title: Normal".hex()
        evt_ok = ws.process_ws_message(
            {
                "method": "eth_subscription",
                "params": {
                    "result": {
                        "address": "0x2c0367a9db231ddebd88a94b4f6461a6e47c58b1",
                        "topics": [TOPIC_OO_PROPOSE_PRICE],
                        "data": ok_hex,
                        "blockNumber": "0x101",
                        "transactionHash": "0xbeef",
                    }
                },
            }
        )
        self.assertFalse(evt_ok["quarantined_d001"])
        drained = ws.drain_events()
        self.assertEqual(len(drained), 1)
        self.assertEqual(ws.get_market_oo_status("9876543")["status"], "PROPOSED")
        self.assertIn("6707503", FROZEN_KMIA_MARKET_IDS)
        self.assertIn("6707502", FROZEN_KMIA_MARKET_IDS)

    def test_hyperliquid_coinbase_deribit_macro_and_fx(self) -> None:
        hl_cb = HyperliquidCoinbaseWs(hl_coins=("HYPE", "BTC"), coinbase_products=("BTC-USD", "ZEC-USD"))
        self.assertEqual(hl_cb.process_hyperliquid_message({"channel": "allMids", "data": {"mids": {"HYPE": "24.85"}}}), 1)
        self.assertAlmostEqual(hl_cb.get_price("HYPE", venue="hyperliquid"), 24.85)
        self.assertEqual(
            hl_cb.process_coinbase_message({"channel": "ticker", "events": [{"tickers": [{"product_id": "ZEC-USD", "price": "41.2"}]}]}),
            1,
        )
        self.assertAlmostEqual(hl_cb.get_price("ZEC", venue="coinbase"), 41.2)

        der = DeribitPublicWs(["BTC-29NOV26-90000-C"])
        self.assertIn("ticker.BTC-29NOV26-90000-C.100ms", DeribitPublicWs.build_subscribe_frame(["BTC-29NOV26-90000-C"]))
        ok_d = der.process_ws_message(
            {
                "method": "subscription",
                "params": {
                    "data": {
                        "instrument_name": "BTC-29NOV26-90000-C",
                        "best_bid_price": 0.041,
                        "best_ask_price": 0.043,
                        "underlying_price": 91200.0,
                    }
                },
            }
        )
        self.assertTrue(ok_d)
        self.assertAlmostEqual(der.get_option_quote("BTC-29NOV26-90000-C")["best_ask_price"], 0.043)

        macro = MacroEventFeedClient()
        self.assertEqual(macro.fetch_fed_rss_sync(in_window=False), [])
        items = macro.parse_fed_rss_xml(
            "<rss><channel><item><title>FOMC Statement</title><link>https://federalreserve.gov</link></item></channel></rss>"
        )
        self.assertEqual(items[0]["title"], "FOMC Statement")

        fx_ibkr = fetch_live_cad_usd_sync(ibkr_quote={"bid": 0.7240, "ask": 0.7244, "ts": time.time()})
        self.assertEqual(fx_ibkr["source"], "ibkr_idealpro")
        self.assertFalse(fx_ibkr["stale"])
        self.assertFalse(fx_ibkr["is_daily_ref"])


class TestV62WsWeatherSportsConnectorsRecorder(unittest.TestCase):
    def test_ws_streams_custom_features_rtds_lazy_sort_and_kmia_guard(self) -> None:
        self.assertIn("xagusd", POLYBOLT_CRYPTO_SYMBOLS)
        cl = PolymarketChainlinkLiveStream()
        now_ms = int(time.time() * 1000)
        self.assertTrue(cl.process_ws_message({"topic": "crypto_prices", "payload": {"symbol": "btcusd", "value": 91000.5, "timestamp": now_ms}}))
        self.assertTrue(cl.process_ws_message({"topic": "equity_prices", "payload": {"symbol": "SPY", "value": 599.25, "timestamp": now_ms}}))
        self.assertAlmostEqual(cl.get_latest_spot("SPY"), 599.25)

        t1 = "1" * 20
        sh = PolymarketShardedClobMarketWsTracker(num_shards=2)
        sh.set_desired_tokens([t1])
        self.assertTrue(
            sh.process_ws_payload(
                {
                    "asset_id": t1,
                    "bids": [{"price": "0.45", "size": "10"}],
                    "asks": [{"price": "0.48", "size": "12"}],
                }
            )
        )
        # Delta price_change sets dirty lazily -> both numeric & dict view must reflect updated state
        sh.process_ws_payload(
            {
                "event_type": "price_change",
                "price_changes": [{"asset_id": t1, "price": "0.46", "size": "20", "side": "BUY"}],
            }
        )
        nb = sh.get_numeric_book(t1)
        self.assertIsNotNone(nb)
        self.assertEqual(nb["bids"][0], (0.46, 20.0))
        db = sh.get_book(t1)
        self.assertEqual(db["bids"][0]["price"], "0.4600")

        # Lifecycle events (`market_resolved`, `new_market`) quarantine D-001 KMIA
        sh.process_ws_payload({"event_type": "market_resolved", "market": "6707503", "asset_id": t1})
        sh.process_ws_payload({"event_type": "new_market", "market": "7777777", "assets_ids": [t1]})
        lc = sh.drain_lifecycle_events()
        self.assertEqual(len(lc), 1)
        self.assertEqual(lc[0]["market"], "7777777")

        # Confirm subscribe payload includes custom_feature_enabled
        sub_txt = PolymarketMarketWsState.build_subscribe_frame([t1])
        self.assertTrue(json.loads(sub_txt)["custom_feature_enabled"])
        self.assertIn('"custom_feature_enabled": True', Path(REPO_ROOT / "src/polymarket_research/polymarket_ws_streams.py").read_text(encoding="utf-8"))

    def test_weather_cli_and_neighbor_anomaly(self) -> None:
        cli = parse_nws_dsm_or_cli_text("TEMPERATURE (F)\n MAXIMUM 84 315 PM\n MINIMUM 68 520 AM\n", product_type="CLI")
        self.assertIsNotNone(cli)
        self.assertEqual(cli["max_temp_f"], 84.0)
        self.assertTrue(cli["is_final_cli"])

        dt = datetime(2026, 11, 13, 14, 0, tzinfo=timezone.utc)
        p_bad = MetarObservation(
            icao="KMIA", utc_dt=dt, local_dt=dt, temp_c=40.0, has_t_remark=False,
            raw_line="KMIA 1400Z 40/20 $", has_maintenance_indicator=True,
        )
        p_outlier = MetarObservation(
            icao="KMIA", utc_dt=dt, local_dt=dt, temp_c=40.0, has_t_remark=False,
            raw_line="KMIA 1400Z 40/20", has_maintenance_indicator=False,
        )
        n1 = MetarObservation(
            icao="KOPF", utc_dt=dt, local_dt=dt, temp_c=26.0, has_t_remark=False,
            raw_line="KOPF 1400Z 26/18", has_maintenance_indicator=False,
        )
        n2 = MetarObservation(
            icao="KFLL", utc_dt=dt, local_dt=dt, temp_c=25.0, has_t_remark=False,
            raw_line="KFLL 1400Z 25/18", has_maintenance_indicator=False,
        )
        self.assertTrue(check_neighbor_station_temp_anomaly(p_bad, [n1, n2])[0])
        is_anom, reason = check_neighbor_station_temp_anomaly(p_outlier, [n1, n2])
        self.assertTrue(is_anom)
        self.assertIn("SPATIAL_SENSOR_ANOMALY", reason)

    def test_direct_feeds_adaptive_etag_and_tennis(self) -> None:
        self.assertAlmostEqual(compute_adaptive_sports_poll_interval_sec(is_endgame_or_halftime=True), 0.75)
        self.assertAlmostEqual(compute_adaptive_sports_poll_interval_sec(is_endgame_or_halftime=False, has_live_games=False), 60.0)

        class _FakeSess:
            def __init__(self) -> None:
                self.calls = 0

            def get(self, url, headers=None, timeout=2.5):
                self.calls += 1
                if self.calls == 1:
                    return _DummyResponse(200, b'{"ok": 1}', headers={"ETag": '"v1"'})
                self.assert_hdr = (headers or {}).get("If-None-Match")
                return _DummyResponse(304, b"")

        sess = _FakeSess()
        with patch("src.polymarket_research.polymarket_direct_feeds._get_keepalive_session", return_value=sess):
            d1 = _get_conditional_json_sync("https://example.test/sb.json")
            d2 = _get_conditional_json_sync("https://example.test/sb.json")
        self.assertEqual(d1, {"ok": 1})
        self.assertEqual(d2, {"ok": 1})
        self.assertEqual(sess.assert_hdr, '"v1"')

        tennis = parse_atp_wta_scoreboard(
            {
                "events": [
                    {
                        "id": "t1",
                        "competitions": [
                            {
                                "id": "c1",
                                "status": {"type": {"state": "in", "detail": "2nd Set", "completed": False}},
                                "competitors": [
                                    {"athlete": {"displayName": "Player A"}, "linescores": [{"winner": True}], "winner": False},
                                    {"athlete": {"displayName": "Player B"}, "linescores": [{"winner": False}], "winner": False},
                                ],
                            }
                        ],
                    }
                ]
            },
            tour="atp",
        )
        self.assertEqual(len(tennis), 1)
        self.assertEqual(tennis[0]["completed_sets"], 1)
        self.assertFalse(tennis[0]["retired_or_walkover"])

    def test_kalshi_readonly_connector_and_recorder_l2_cache(self) -> None:
        conn = KalshiPublicConnector()
        self.assertTrue(conn.execution_blocked)
        self.assertEqual(conn.jurisdiction, "CA_ON_PROHIBITED")
        mkt = conn.parse_public_market(
            {"ticker": "KXBTC-100K", "title": "BTC > 100k", "status": "open"},
            {"orderbook": {"yes": [[42, 10]], "no": [[55, 8]]}},
        )
        self.assertIsNotNone(mkt)
        self.assertAlmostEqual(mkt.yes_bids[0].price, 0.42)
        self.assertAlmostEqual(mkt.no_asks[0].price, 0.58)
        self.assertAlmostEqual(mkt.yes_asks[0].price, 0.45)

        rec_src = (REPO_ROOT / "src/polymarket_research/polymarket_terminal_recorder.py").read_text(encoding="utf-8")
        self.assertNotIn("await resp.json()", rec_src)
        self.assertNotIn("await resp_spot.json()", rec_src)
        self.assertIn('"custom_feature_enabled": True', rec_src)

        parsed_async = asyncio.run(_fast_resp_json(_DummyAsyncResponse(b'{"hello": 123}')))
        self.assertEqual(parsed_async["hello"], 123)

        bk = L2OrderBook("tok_test")
        bk.apply_snapshot(
            [{"price": "0.45", "size": "10"}, {"price": "0.42", "size": "15"}],
            [{"price": "0.48", "size": "12"}, {"price": "0.52", "size": "20"}],
        )
        self.assertAlmostEqual(bk.prev_best_bid[0], 0.45)
        self.assertAlmostEqual(bk.prev_best_ask[0], 0.48)
        # Interior update keeps O(1) best levels unchanged
        bk.apply_price_changes([{"price": "0.43", "size": "50", "side": "BUY"}])
        self.assertAlmostEqual(bk.prev_best_bid[0], 0.45)
        # Removing best bid triggers exact recompute to 0.43
        bk.apply_price_changes([{"price": "0.45", "size": "0", "side": "BUY"}])
        self.assertAlmostEqual(bk.prev_best_bid[0], 0.43)

    def test_ws_quiet_live_book_freshness_and_best_bid_ask_snapshot_guard(self) -> None:
        tok_snap = "10000000000000000001"
        tok_nosnap = "10000000000000000002"
        tracker = PolymarketClobMarketWsTracker()
        tracker.set_desired_tokens([tok_snap, tok_nosnap])
        # Seed a real book snapshot for tok_snap
        tracker.process_ws_payload(
            [
                {
                    "event_type": "book",
                    "asset_id": tok_snap,
                    "bids": [{"price": "0.48", "size": "12"}],
                    "asks": [{"price": "0.52", "size": "10"}],
                },
                {
                    "event_type": "best_bid_ask",
                    "asset_id": tok_nosnap,
                    "best_bid": "0.40",
                    "best_ask": "0.60",
                },
            ]
        )
        # Un-snapshotted token must NOT have _last_rx_by_aid poisoned by best_bid_ask
        self.assertNotIn(tok_nosnap, tracker._last_rx_by_aid)
        self.assertIsNone(tracker.get_book(tok_nosnap, max_age_sec=10.0))

        # Simulate 10s quiet period for tok_snap
        now_m = time.monotonic()
        tracker._last_rx_by_aid[tok_snap] = now_m - 10.0

        # Disconnected: strict max_age_sec applies -> expired
        tracker._ws_connected = False
        self.assertIsNone(tracker.get_book(tok_snap, max_age_sec=0.65))
        self.assertIsNone(tracker.get_numeric_book(tok_snap, max_age_sec=0.65))

        # Connected with healthy WS traffic within 15s and snapshot after connect -> quiet live book stays fresh
        tracker._ws_connected = True
        tracker._connected_since_mono = now_m - 30.0
        tracker._last_ws_rx_mono = now_m - 1.0
        bk = tracker.get_book(tok_snap, max_age_sec=0.65)
        nbk = tracker.get_numeric_book(tok_snap, max_age_sec=0.65)
        self.assertIsNotNone(bk)
        self.assertIsNotNone(nbk)
        self.assertAlmostEqual(float(bk["asks"][0]["price"]), 0.52)
        self.assertAlmostEqual(nbk["asks"][0][0], 0.52)

        # Stale socket (_last_ws_rx_mono > 15s ago) -> falls back to strict max_age_sec -> expired
        tracker._last_ws_rx_mono = now_m - 20.0
        self.assertIsNone(tracker.get_book(tok_snap, max_age_sec=0.65))
        self.assertIsNone(tracker.get_numeric_book(tok_snap, max_age_sec=0.65))

    def test_ws_sharded_noop_guard_and_inplace_unsubscribe(self) -> None:
        tok_a = "10000000000000000011"
        tok_b = "10000000000000000012"
        tok_c = "10000000000000000013"
        sharded = PolymarketShardedClobMarketWsTracker(num_shards=2)
        sharded.set_desired_tokens([tok_a, tok_b])
        calls = []
        for idx, shard in enumerate(sharded._shards):
            orig = shard.set_desired_tokens

            def _wrapped(tokens, _orig=orig, _idx=idx):
                calls.append((_idx, list(tokens)))
                return _orig(tokens)

            shard.set_desired_tokens = _wrapped  # type: ignore[method-assign]

        # Identical desired set and already-subscribed urgent token must be no-ops
        sharded.set_desired_tokens([tok_b, tok_a])
        sharded.subscribe_tokens_immediate([tok_a])
        self.assertEqual(calls, [])

        # Adding a truly new token dispatches to its shard
        sharded.subscribe_tokens_immediate([tok_c])
        self.assertGreaterEqual(len(calls), 1)

        # Verify in-place unsubscribe + _snapshot_tokens clear on reconnect in source
        ws_src = (REPO_ROOT / "src/polymarket_research/polymarket_ws_streams.py").read_text(encoding="utf-8")
        self.assertIn('"operation": "unsubscribe"', ws_src)
        self.assertIn("self._snapshot_tokens.clear()", ws_src)

    def test_recorder_xau_xag_price_to_beat_l2_tob_cache_and_nonblocking_clob(self) -> None:
        self.assertAlmostEqual(
            PolymarketDualFeed1HRecorder._extract_event_price_to_beat({"eventMetadata": {"priceToBeat": "3884.625"}}),
            3884.625,
        )
        self.assertAlmostEqual(
            PolymarketDualFeed1HRecorder._extract_event_price_to_beat({"eventMetadata": '{"openPrice": 49.1064}'}),
            49.1064,
        )
        self.assertEqual(PolymarketDualFeed1HRecorder._extract_event_price_to_beat({}), 0.0)

        bk = L2OrderBook("tok_cache")
        bk.apply_snapshot(
            [{"price": "0.41", "size": "10"}],
            [{"price": "0.59", "size": "15"}],
        )
        t1 = bk.top_of_book(obs_ts=100.0)
        t1["best_bid"] = 0.99  # Mutating returned dict must not corrupt internal cache
        t2 = bk.top_of_book(obs_ts=101.0)
        self.assertAlmostEqual(t2["best_bid"], 0.41)
        self.assertAlmostEqual(t2["best_ask"], 0.59)

        bk.apply_price_changes([{"price": "0.55", "size": "8", "side": "SELL"}])
        t3 = bk.top_of_book(obs_ts=102.0)
        self.assertAlmostEqual(t3["best_ask"], 0.55)

        rec_src = (REPO_ROOT / "src/polymarket_research/polymarket_terminal_recorder.py").read_text(encoding="utf-8")
        self.assertIn("gold-up-or-down-", rec_src)
        self.assertIn("silver-up-or-down-", rec_src)
        self.assertIn("_quiet_refresh_task", rec_src)
        self.assertIn("_drain_ws_frames", rec_src)
        self.assertIn("_last_shm_write_sig", rec_src)


if __name__ == "__main__":
    unittest.main()

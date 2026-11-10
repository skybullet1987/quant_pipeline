#!/usr/bin/env python3
"""
Unit Tests for v5.8.0 Pure-Riskless Scaling & P0 Live Capital Recovery Suite:
  1. Governance v5.8.0 keys, bounds, and pure-riskless safety invariants.
  2. Polymarket V2 `pUSD` (`0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB`) wrapper encoding,
     `V2_ADAPTER_REDEMPTION_TOPIC0` (`0x1daec0b1...`) receipt parsing on `CTF_ADAPTER_V2` &
     `NEG_RISK_ADAPTER_V2`, and `wrap_pusd` Relayer V2 recycle-slot priority.
  3. 4-Shard `PolymarketShardedClobMarketWsTracker` (`4 x 485 = 1,940` live tokens, sticky
     shard placement across watchlist churn, and Harvester `_desired_market_ws_tokens` expansion).
  4. Sub-2ms `D1FAST` Cross-Horizon Dominance IPC (`15m vs 5m` crypto + `1h vs 15m` metals)
     and `PolymarketDualFeed1HRecorder._has_urgent_c1_arb_raw` 25ms fast-tick detection.
  5. Same-`conditionId` `NegRisk` & `>24h` `0%`-fee `COMPLETE_SET` instant merge gate +
     `Alpha124ShadowDaemon.extract_zerofee_general_binaries` `negRisk` binary extraction.
  6. `$0/mo` Official NBA/NHL/MLB `liveData` Push Adapters & Dual-Source Conservative Reconcilers.
  7. Multi-Asset `PreSplitInventoryGun` Pool (`<= 3` slots at `>= $140 / $220 / $360` equity,
     strictly gated off at `$76.81`) + Stockholm `check_polymarket_region_latency.py` probe helpers.
"""

from __future__ import annotations

import asyncio
import copy
import json
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestV580ShardedWsD1FastPusdAndDirectFeeds(unittest.TestCase):
    def test_v580_governance_keys_bounds_and_riskless_invariants(self) -> None:
        from src.polymarket_research.holistic_strategy_governance import (
            DEFAULT_HOLISTIC_CONFIG,
            HotReloadConfigManager,
            _deep_merge_validated,
        )

        cfg_path = PROJECT_ROOT / "config" / "polymarket_strategy_and_risk.json"
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        mgr = HotReloadConfigManager(config_path=cfg_path)
        validated = mgr.snapshot

        # Non-negotiable pure-riskless invariants
        self.assertEqual(raw["schema_version"], "5.5.0")
        self.assertTrue(validated["directional"]["riskless_only_mode"])
        rb = validated["riskless_boxes"]
        self.assertFalse(rb["enable_two_leg_maker_anchor_boxes"])
        self.assertFalse(rb["enable_d1_rebate_maker_canary"])
        self.assertEqual(int(rb["ws_clinch_watchlist_max_tokens"]), 450)

        # v5.8.0 keys
        self.assertEqual(int(rb["ws_market_num_shards"]), 4)
        self.assertTrue(bool(rb["enable_recorder_d1fast_ipc"]))
        self.assertTrue(bool(rb["enable_official_league_direct_feeds"]))
        self.assertTrue(bool(rb["enable_auto_wrap_legacy_usdce_to_pusd"]))
        self.assertEqual(int(rb["pre_split_max_concurrent_slots"]), 3)

        # Bounds checks
        for bad_override in (
            {"ws_market_num_shards": 9},
            {"ws_market_num_shards": 0},
            {"pre_split_max_concurrent_slots": 5},
            {"pre_split_max_concurrent_slots": 0},
        ):
            with self.assertRaises(ValueError):
                _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, {"riskless_boxes": bad_override})

    def test_v2_adapter_redemption_logs_and_pusd_wrap_encoding(self) -> None:
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        from src.polymarket_research.riskless_machine_gun_engine import (
            POLYMARKET_V2_COLLATERAL_WRAPPER,
            V2_ADAPTER_REDEMPTION_TOPIC0,
            encode_v2_collateral_wrap_call,
        )

        self.assertEqual(
            POLYMARKET_V2_COLLATERAL_WRAPPER.lower(),
            PolymarketLiveExecutor.PUSD_WRAPPER_ADDRESS.lower(),
        )
        self.assertEqual(
            V2_ADAPTER_REDEMPTION_TOPIC0.lower(),
            PolymarketLiveExecutor.V2_ADAPTER_REDEMPTION_TOPIC0.lower(),
        )

        funder = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
        wrap_tgt, wrap_data = encode_v2_collateral_wrap_call(
            PolymarketLiveExecutor.USDC_E_ADDRESS,
            funder,
            11_000_000,
        )
        self.assertEqual(wrap_tgt.lower(), PolymarketLiveExecutor.PUSD_WRAPPER_ADDRESS.lower())
        self.assertTrue(wrap_data.startswith("0x62355638"))
        self.assertTrue(wrap_data.endswith(f"{11_000_000:064x}"))

        ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex.funder_address = funder
        cond_id = "0x" + "ab" * 32
        me_topic = "0x" + funder.lower().replace("0x", "").rjust(64, "0")
        other_topic = "0x" + ("99" * 20).rjust(64, "0")
        # V2 PositionsRedeemed data: [indexSets offset (32B), payout (32B), ...]
        payout_11_hex = f"{11_000_000:064x}"
        payout_20_hex = f"{20_000_000:064x}"
        data_11 = "0x" + ("00" * 31 + "40") + payout_11_hex
        data_20 = "0x" + ("00" * 31 + "40") + payout_20_hex

        logs = [
            {
                "address": PolymarketLiveExecutor.CTF_ADAPTER_V2_ADDRESS,
                "topics": [PolymarketLiveExecutor.V2_ADAPTER_REDEMPTION_TOPIC0, me_topic, cond_id],
                "data": data_11,
                "transactionHash": "0x" + "11" * 32,
                "blockNumber": "0x100",
                "logIndex": "0x1",
            },
            {
                "address": PolymarketLiveExecutor.NEG_RISK_ADAPTER_V2_ADDRESS,
                "topics": [PolymarketLiveExecutor.V2_ADAPTER_REDEMPTION_TOPIC0, me_topic, cond_id],
                "data": data_20,
                "transactionHash": "0x" + "22" * 32,
                "blockNumber": "0x101",
                "logIndex": "0x2",
            },
            # Different funder -> ignored
            {
                "address": PolymarketLiveExecutor.CTF_ADAPTER_V2_ADDRESS,
                "topics": [PolymarketLiveExecutor.V2_ADAPTER_REDEMPTION_TOPIC0, other_topic, cond_id],
                "data": data_20,
                "transactionHash": "0x" + "33" * 32,
                "blockNumber": "0x102",
                "logIndex": "0x3",
            },
        ]
        try:
            import eth_utils  # noqa: F401

            parsed = ex.parse_payout_redemption_logs(logs, cond_id)
        except ImportError:
            with patch.object(PolymarketLiveExecutor, "_payout_redemption_topic", return_value="0x" + "aa" * 32), patch.object(
                PolymarketLiveExecutor, "_neg_risk_payout_redemption_topic", return_value="0x" + "bb" * 32
            ):
                parsed = ex.parse_payout_redemption_logs(logs, cond_id)

        self.assertEqual(len(parsed), 2)
        self.assertAlmostEqual(parsed[0]["payout_usd"], 11.0, places=6)
        self.assertAlmostEqual(parsed[1]["payout_usd"], 20.0, places=6)

    def test_sharded_clob_market_ws_tracker_sticky_routing_and_1940_cap(self) -> None:
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.polymarket_ws_streams import PolymarketShardedClobMarketWsTracker

        callbacks = []
        ws_pool = PolymarketShardedClobMarketWsTracker(
            num_shards=4,
            per_shard_max=485,
            on_book_change=lambda t, _bk: callbacks.append(t),
        )
        self.assertEqual(ws_pool.max_tokens, 1940)

        toks_initial = [f"{100000 + i:024d}" for i in range(1200)]
        ws_pool.set_desired_tokens(toks_initial)
        counts_1 = ws_pool.shard_token_counts()
        self.assertEqual(sum(counts_1), 1200)
        self.assertTrue(all(c == 300 for c in counts_1))

        # Sticky assignment check: keep first 900 tokens, replace tail 300 with 400 new tokens
        old_mapping = {t: ws_pool._token_to_shard[t] for t in toks_initial[:900]}
        toks_next = toks_initial[:900] + [f"{500000 + i:024d}" for i in range(400)]
        ws_pool.set_desired_tokens(toks_next)
        for t_keep, prev_sh in old_mapping.items():
            self.assertEqual(ws_pool._token_to_shard[t_keep], prev_sh)
        self.assertEqual(sum(ws_pool.shard_token_counts()), 1300)

        # Seed book, tick size change, and live WS payload routing
        t_sample = toks_next[0]
        self.assertTrue(
            ws_pool.seed_book(
                t_sample,
                {"bids": [{"price": "0.97", "size": "50"}], "asks": [{"price": "0.98", "size": "40"}]},
            )
        )
        bk0 = ws_pool.get_book(t_sample, max_age_sec=5.0)
        self.assertIsNotNone(bk0)
        self.assertAlmostEqual(float(bk0["asks"][0]["price"]), 0.98)

        ws_frame = json.dumps(
            {
                "event_type": "tick_size_change",
                "asset_id": t_sample,
                "new_tick_size": "0.001",
            }
        )
        self.assertTrue(ws_pool.process_ws_payload(ws_frame))
        self.assertAlmostEqual(ws_pool.get_tick_size(t_sample) or 0.0, 0.001)

        # Harvester _desired_market_ws_tokens expands past 490 up to <= 1,940 when 4-sharded
        now_ts = time.time()
        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.active_positions = {"ACT_1": {"token_id": f"{990001:024d}"}}
        h.pending_entry_intents = {}
        h._clinched_ws_watchlist = {}
        h._seen_d1_box_keys = set()
        h._d1_retry_cooldown_until = {}
        for idx in range(600):
            h.register_clinched_ws_watch_cand(
                {
                    "box_type": "CLINCH_WATCHLIST_REG",
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "asset": "BTC",
                    "dedupe_key": f"SHARD_W_{idx}",
                    "leg_a_token_id": f"{700000 + idx:024d}",
                    "leg_a_opp_token_id": f"{800000 + idx:024d}",
                    "leg_a_market_id": f"M_SH_{idx}",
                    "expiry_ts": now_ts + 1800.0,
                    "max_box_cost_net": 0.994,
                    "max_opp_bid": 0.020,
                    "p_model": 0.9995,
                },
                now_ts=now_ts,
            )
        # Unsharded default: strictly <= 490
        h._pos_market_ws = None
        self.assertLessEqual(len(h._desired_market_ws_tokens(now_ts=now_ts)), 490)
        # 4-sharded pool attached: scales cleanly to all 1,201 tokens (<= 1,940)!
        h._pos_market_ws = ws_pool
        desired_sharded = h._desired_market_ws_tokens(now_ts=now_ts)
        self.assertEqual(len(desired_sharded), 1201)
        self.assertEqual(desired_sharded[0], f"{990001:024d}")

    def test_recorder_d1fast_cross_horizon_dominance_ipc_and_urgent_tick(self) -> None:
        from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook, PolymarketDualFeed1HRecorder
        from src.polymarket_research.riskless_protocol_v2_expansion import maybe_emit_recorder_fast_riskless_ipc

        now_ts = 1_762_550_000.0
        exp_ts = now_ts + 120.0
        sink: list = []
        rec = SimpleNamespace(
            asset="BTC",
            _test_cand_sink=sink,
            market_15m={
                "market_id": "M15_BTC",
                "condition_id": "0x" + "15" * 32,
                "expiry_ts": exp_ts,
                "authoritative_chainlink_open": 90_000.0,
                "fee_metadata": {"fee_rate_market": 0.072},
            },
            market_5m={
                "market_id": "M5_BTC",
                "condition_id": "0x" + "05" * 32,
                "expiry_ts": exp_ts,
                "authoritative_chainlink_open": 90_090.0,  # +10.0 bps corridor -> 15m UP + 5m DOWN
                "fee_metadata": {"fee_rate_market": 0.072},
            },
        )
        snap = {
            "asset": "BTC",
            "m15": {
                "market_id": "M15_BTC",
                "condition_id": "0x" + "15" * 32,
                "expiry_ts": exp_ts,
                "authoritative_chainlink_open": 90_000.0,
                "UP": {
                    "token_id": "1515" * 6,
                    "best_bid": 0.45,
                    "best_ask": 0.47,
                    "ask_size_l1": 30.0,
                    "age_book_ms": 40.0,
                    "raw_top_bids": [[0.45, 30.0]],
                    "raw_top_asks": [[0.47, 30.0]],
                },
                "DOWN": {
                    "token_id": "1500" * 6,
                    "best_bid": 0.52,
                    "best_ask": 0.54,
                    "ask_size_l1": 30.0,
                    "age_book_ms": 40.0,
                },
            },
            "m5": {
                "market_id": "M5_BTC",
                "condition_id": "0x" + "05" * 32,
                "expiry_ts": exp_ts,
                "authoritative_chainlink_open": 90_090.0,
                "UP": {
                    "token_id": "0515" * 6,
                    "best_bid": 0.51,
                    "best_ask": 0.53,
                    "ask_size_l1": 30.0,
                    "age_book_ms": 35.0,
                },
                "DOWN": {
                    "token_id": "0500" * 6,
                    "best_bid": 0.44,
                    "best_ask": 0.46,
                    "ask_size_l1": 30.0,
                    "age_book_ms": 35.0,
                    "raw_top_bids": [[0.44, 30.0]],
                    "raw_top_asks": [[0.46, 30.0]],
                },
            },
        }
        cnt = maybe_emit_recorder_fast_riskless_ipc(rec, snap, now_ts)
        self.assertEqual(cnt, 1)
        cand = sink[0]
        self.assertEqual(cand["box_type"], "DOMINANCE")
        self.assertEqual(cand["sleeve_source"], "D1_SAME_ORACLE_DOMINANCE_BOX")
        self.assertTrue(cand["dedupe_key"].startswith("D1FAST_"))
        self.assertEqual(cand["regime"], "CORRIDOR_15m_UP_5m_DOWN")
        self.assertEqual(cand["leg_a_token_id"], "1515" * 6)
        self.assertEqual(cand["leg_b_token_id"], "0500" * 6)
        self.assertLessEqual(cand["box_cost_net"], 0.9925)

        # Narrow corridor (< 3.0 bps) -> strictly vetoed
        sink_narrow: list = []
        rec_narrow = copy.deepcopy(rec)
        rec_narrow._test_cand_sink = sink_narrow
        rec_narrow._last_c1_ipc_ts = {}
        snap_narrow = copy.deepcopy(snap)
        snap_narrow["m5"]["authoritative_chainlink_open"] = 90_010.0  # 1.11 bps < 3.0 bps
        rec_narrow.market_5m["authoritative_chainlink_open"] = 90_010.0
        self.assertEqual(maybe_emit_recorder_fast_riskless_ipc(rec_narrow, snap_narrow, now_ts + 5.0), 0)

        # Live role-keyed _has_urgent_c1_arb_raw drops recorder throttle to 25ms on cross-horizon D1!
        r_live = PolymarketDualFeed1HRecorder.__new__(PolymarketDualFeed1HRecorder)
        r_live.riskless_bus_only = True
        end_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
        r_live.market_15m = {"market_id": "M15", "end_dt": end_dt}
        r_live.market_5m = {"market_id": "M5", "end_dt": end_dt}
        r_live.current_market = None
        bu15, bd15 = L2OrderBook("u15"), L2OrderBook("d15")
        bu5, bd5 = L2OrderBook("u5"), L2OrderBook("d5")
        bu15.prev_best_ask = (0.47, 25.0)
        bd15.prev_best_ask = (0.54, 25.0)
        bu5.prev_best_ask = (0.54, 25.0)
        bd5.prev_best_ask = (0.45, 25.0)
        r_live.books = {"UP_15M": bu15, "DOWN_15M": bd15, "UP_5M": bu5, "DOWN_5M": bd5}
        self.assertTrue(r_live._has_urgent_c1_arb_raw())
        self.assertAlmostEqual(r_live._fast_tick_throttle_sec(now_ts), 0.025)

    def test_negrisk_same_condition_zerofee_merge_gate_and_extraction(self) -> None:
        from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon

        raw_markets = [
            {
                "id": "NR_SUB_1",
                "conditionId": "0x" + "cd" * 32,
                "question": "Will Candidate A win the election?",
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "feesEnabled": False,
                "negRisk": True,
                "clobTokenIds": json.dumps(["1111111111111111111111", "2222222222222222222222"]),
                "outcomes": json.dumps(["Yes", "No"]),
                "endDate": "2027-01-15T00:00:00Z",
                "volume24hr": 50000,
            },
            # Fee-enabled market must be excluded from ZEROFEE1
            {
                "id": "FEE_MKT_2",
                "conditionId": "0x" + "ef" * 32,
                "question": "BTC Up or Down?",
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "feesEnabled": True,
                "takerBaseFee": 720,
                "negRisk": False,
                "clobTokenIds": json.dumps(["3333333333333333333333", "4444444444444444444444"]),
                "outcomes": json.dumps(["Up", "Down"]),
                "endDate": "2026-12-01T00:00:00Z",
                "volume24hr": 90000,
            },
        ]
        raw_events = [
            {
                "slug": "election-2027",
                "negRisk": True,
                "closed": False,
                "markets": raw_markets,
            }
        ]
        extracted = Alpha124ShadowDaemon.extract_zerofee_general_binaries(
            raw_events, now_ts=1_762_550_000.0, max_markets=50
        )
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["market_id"], "NR_SUB_1")
        self.assertTrue(extracted[0]["neg_risk"])
        self.assertEqual(extracted[0]["condition_id"], "0x" + "cd" * 32)
        self.assertEqual(
            len(
                Alpha124ShadowDaemon.extract_zerofee_general_binaries(
                    raw_events, now_ts=1_762_550_000.0, max_markets=50, include_neg_risk_subconditions=False
                )
            ),
            0,
        )

    def test_official_league_direct_feeds_and_dual_source_reconciler(self) -> None:
        from src.polymarket_research.polymarket_direct_feeds import (
            parse_mlb_statsapi_scoreboard,
            parse_nba_cdn_scoreboard,
            parse_nhl_official_scoreboard,
            reconcile_multisport_dual_source_boards,
            reconcile_nba_dual_source_boards,
        )
        from src.polymarket_research.uma_nba_endgame_engine import LiveNbaGameState

        nba_payload = {
            "scoreboard": {
                "games": [
                    {
                        "gameId": "0022600123",
                        "gameStatus": 3,
                        "period": 4,
                        "gameClock": "PT00M00.00S",
                        "gameTimeUTC": "2026-11-07T00:00:00Z",
                        "homeTeam": {"teamName": "Celtics", "teamTricode": "BOS", "score": 114},
                        "awayTeam": {"teamName": "Lakers", "teamTricode": "LAL", "score": 108},
                    }
                ]
            }
        }
        cdn_board = parse_nba_cdn_scoreboard(nba_payload)
        self.assertEqual(len(cdn_board), 1)
        self.assertTrue(cdn_board[0].completed)
        self.assertEqual((cdn_board[0].home_score, cdn_board[0].away_score), (114, 108))

        # Case 1: NBA CDN already Final while ESPN lags at Q4 12.0s -> upgrades cleanly to post/completed!
        espn_lagging = [
            LiveNbaGameState(
                game_id="ESPN_1",
                start_ts=1_762_473_600.0,
                state="in",
                completed=False,
                period=4,
                clock_sec=12.0,
                home_name="Boston Celtics",
                home_abbr="BOS",
                home_score=112,
                away_name="Los Angeles Lakers",
                away_abbr="LAL",
                away_score=108,
                source="espn",
            )
        ]
        rec_final = reconcile_nba_dual_source_boards(espn_lagging, cdn_board)
        self.assertTrue(rec_final[0].completed)
        self.assertEqual(rec_final[0].source, "nba_cdn_final")
        self.assertEqual((rec_final[0].home_score, rec_final[0].away_score), (114, 108))

        # Case 2: Conflicting Final scores -> downgraded to completed=False (min-score safety)!
        espn_conflict = [
            LiveNbaGameState(
                game_id="ESPN_1",
                start_ts=1_762_473_600.0,
                state="post",
                completed=True,
                period=4,
                clock_sec=0.0,
                home_name="Boston Celtics",
                home_abbr="BOS",
                home_score=110,
                away_name="Los Angeles Lakers",
                away_abbr="LAL",
                away_score=112,
                source="espn",
            )
        ]
        rec_conflict = reconcile_nba_dual_source_boards(espn_conflict, cdn_board)
        self.assertFalse(rec_conflict[0].completed)
        self.assertEqual((rec_conflict[0].home_score, rec_conflict[0].away_score), (110, 108))

        # NHL & MLB parsers + multisport reconciler
        nhl_board = parse_nhl_official_scoreboard(
            {
                "games": [
                    {
                        "id": 2026020222,
                        "gameState": "LIVE",
                        "startTimeUTC": "2026-11-07T00:00:00Z",
                        "periodDescriptor": {"number": 2},
                        "clock": {"secondsRemaining": 420, "inIntermission": False},
                        "homeTeam": {"commonName": {"default": "Bruins"}, "abbrev": "BOS", "score": 4},
                        "awayTeam": {"commonName": {"default": "Maple Leafs"}, "abbrev": "TOR", "score": 2},
                    }
                ]
            }
        )
        self.assertEqual(len(nhl_board), 1)
        self.assertEqual((nhl_board[0].home_score, nhl_board[0].away_score), (4, 2))

        espn_nhl = [copy.deepcopy(nhl_board[0])]
        espn_nhl[0].game_id = "ESPN_NHL_99"
        espn_nhl[0].home_score = 3  # ESPN hasn't confirmed 4th goal yet -> conservative min keeps 3!
        merged_nhl = reconcile_multisport_dual_source_boards("NHL", espn_nhl, nhl_board)
        self.assertEqual(merged_nhl[0].game_id, "ESPN_NHL_99")
        self.assertEqual(merged_nhl[0].home_score, 3)

        mlb_board = parse_mlb_statsapi_scoreboard(
            {
                "dates": [
                    {
                        "games": [
                            {
                                "gamePk": 777111,
                                "gameDate": "2026-08-10T23:05:00Z",
                                "status": {"abstractGameState": "Final", "detailedState": "Final"},
                                "linescore": {"currentInning": 9, "innings": [{"num": 1, "home": {"runs": 2}, "away": {"runs": 0}}]},
                                "teams": {
                                    "home": {"team": {"teamName": "Yankees"}, "score": 5},
                                    "away": {"team": {"teamName": "Red Sox"}, "score": 3},
                                },
                            },
                            {
                                "gamePk": 777112,
                                "gameDate": "2026-08-10T23:05:00Z",
                                "status": {"abstractGameState": "Final", "detailedState": "Postponed"},
                                "teams": {
                                    "home": {"team": {"teamName": "Mets"}, "score": 0},
                                    "away": {"team": {"teamName": "Braves"}, "score": 0},
                                },
                            },
                        ]
                    }
                ]
            }
        )
        self.assertEqual(len(mlb_board), 1)
        self.assertTrue(mlb_board[0].completed)

    def test_multi_asset_presplit_pool_and_region_latency_helpers(self) -> None:
        from scripts.check_polymarket_region_latency import summarize_rtt_samples
        from src.polymarket_research.riskless_machine_gun_engine import PreSplitInventoryGun

        rtt_stats = summarize_rtt_samples([14.2, 11.8, 12.5, 13.0, 19.4])
        self.assertAlmostEqual(rtt_stats["min_ms"], 11.8)
        self.assertAlmostEqual(rtt_stats["p50_ms"], 13.0)
        self.assertAlmostEqual(rtt_stats["p95_ms"], 19.4)

        now_ts = 1_762_550_000.0
        up_btc = "1" * 24
        dn_btc = "2" * 24
        up_eth = "3" * 24
        dn_eth = "4" * 24

        def _ft_reader(sym: str):
            if sym == "BTC":
                return {
                    "timestamp_unix": now_ts + 2.0,
                    "condition_id": "0x" + "b1" * 32,
                    "up_token_id": up_btc,
                    "down_token_id": dn_btc,
                    "candle_expiry_ts": now_ts + 420.0,
                    "candle_open_spot": 90000.0,
                    "fee_rate": 0.0,
                    "books": {
                        up_btc: {"bids": [{"price": "0.52", "size": "120"}], "asks": [{"price": "0.53", "size": "120"}]},
                        dn_btc: {"bids": [{"price": "0.49", "size": "120"}], "asks": [{"price": "0.50", "size": "120"}]},
                    },
                }
            if sym == "ETH":
                return {
                    "timestamp_unix": now_ts + 2.0,
                    "condition_id": "0x" + "e2" * 32,
                    "up_token_id": up_eth,
                    "down_token_id": dn_eth,
                    "candle_expiry_ts": now_ts + 420.0,
                    "candle_open_spot": 3200.0,
                    "fee_rate": 0.0,
                    "books": {
                        up_eth: {"bids": [{"price": "0.51", "size": "120"}], "asks": [{"price": "0.52", "size": "120"}]},
                        dn_eth: {"bids": [{"price": "0.50", "size": "120"}], "asks": [{"price": "0.51", "size": "120"}]},
                    },
                }
            return None

        ex = MagicMock()
        ex.dry_run = False
        ex.get_available_collateral.return_value = 76.81
        harv_small = SimpleNamespace(
            executor=ex,
            dry_run=False,
            risk_halt=False,
            global_halt_active=False,
            _startup_reconciled=True,
            active_positions={},
            pending_entry_intents={},
            closed_positions=[],
            _last_known_collateral=76.81,
            save_state=lambda: None,
        )
        gun = PreSplitInventoryGun()
        # At $76.81 equity (< $140 gate), PreSplitInventoryGun MUST stay strictly gated off!
        res_small = asyncio.run(gun.tick(harv_small, now_ts=now_ts, fast_tick_reader=_ft_reader))
        self.assertIsNone(res_small)

        # At $250.00 equity (>= $220 2-slot gate), arms Slot 1 (BTC) and then Slot 2 (ETH) in extra_slots!
        ex.get_available_collateral.return_value = 250.0
        harv_250 = SimpleNamespace(
            executor=ex,
            dry_run=False,
            risk_halt=False,
            global_halt_active=False,
            _startup_reconciled=True,
            active_positions={},
            pending_entry_intents={},
            closed_positions=[],
            _last_known_collateral=250.0,
            save_state=lambda: None,
        )
        with patch(
            "src.polymarket_research.riskless_machine_gun_engine.attempt_onchain_split_position",
            return_value={"success": True, "tx_hash": "0xsplit123"},
        ), patch.object(gun, "_supervise_active_inventory", return_value="SUPERVISED"):
            r1 = asyncio.run(gun.tick(harv_250, now_ts=now_ts + 0.5, fast_tick_reader=_ft_reader))
            self.assertEqual(r1, "ARMED")
            self.assertEqual(harv_250.pre_split_inventory_state["asset"], "BTC")
            ex.get_available_collateral.return_value = harv_250._last_known_collateral
            r2 = asyncio.run(gun.tick(harv_250, now_ts=now_ts + 1.0, fast_tick_reader=_ft_reader))
            self.assertEqual(r2, "ARMED")
            self.assertIn("ETH", harv_250.pre_split_inventory_state.get("extra_slots", {}))
            self.assertTrue(harv_250.pre_split_inventory_state["extra_slots"]["ETH"]["active"])

    def test_stale_collat_drop_surplus_expiry_and_honest_live_equity(self) -> None:
        from scripts.polymarket_daily_projections import compute_live_equity_and_rates
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            pending_intents_synced_equity_usd,
            release_sll_pending_intent,
            update_sll_intent_partial_fill,
        )

        now_ts = 1_794_097_926.0
        intents = {
            "MKR_1": {
                "trade_id": "MKR_1",
                "live_maker_anchor_inflight": True,
                "posted_shares": 8.0,
                "anchor_bid_px": 0.992,
                "posted_notional_usd": 7.936,
                "notional_usd": 7.936,
                "matched_notional_usd": 0.0,
                "collat_drop_usd": 6.923,
                "ts": now_ts - 480.0,
                "heartbeat_ts": now_ts - 5.0,
                "_last_persist_ts": now_ts - 35.0,
            },
            "MKR_2": {
                "trade_id": "MKR_2",
                "live_maker_anchor_inflight": True,
                "posted_shares": 8.0,
                "anchor_bid_px": 0.991,
                "posted_notional_usd": 7.928,
                "notional_usd": 7.928,
                "matched_notional_usd": 0.0,
                "collat_drop_usd": 0.0,
                "ts": now_ts - 240.0,
                "heartbeat_ts": now_ts - 5.0,
                "_last_persist_ts": now_ts - 10.0,
            },
        }
        live_st = {
            "live_bankroll": 57.252101,
            "total_account_equity": 83.715101,
            "high_water_mark_equity": 62.326961,
            "active_positions": {
                "WS_SNIPE_Miami_KMIA_242960": {
                    "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                    "box_type": "SINGLE_LEG_LOCK",
                    "is_single_leg_lock": True,
                    "entry_shares": 20.0,
                    "remaining_shares": 20.0,
                    "notional_usd": 19.54,
                    "remaining_cost_basis": 19.54,
                }
            },
            "pending_entry_intents": copy.deepcopy(intents),
            "closed_positions": [],
        }
        # Projections immediately strip the stale unverified $6.923 surplus -> exact $76.79 equity / $77.25 floor!
        eq_stats = compute_live_equity_and_rates(live_st, fallback_equity=75.84)
        self.assertAlmostEqual(eq_stats["live_equity"], 76.792101, places=4)
        self.assertAlmostEqual(eq_stats["locked_floor_equity"], 77.252101, places=4)

        # Harvester heartbeat decays stale unverified `collat_drop_usd` once >= 25s grace elapses with 0 matched shares
        changed = update_sll_intent_partial_fill(intents, "MKR_1", 8.0, 0.992, 0.0, now_ts)
        self.assertTrue(changed)
        self.assertEqual(intents["MKR_1"]["collat_drop_usd"], 0.0)
        self.assertEqual(pending_intents_synced_equity_usd(intents), 0.0)

        # Releasing a stale intent never hot-potatoes phantom surplus onto other resting intents
        intents["MKR_1"]["collat_drop_usd"] = 6.923
        release_sll_pending_intent(intents, "MKR_1", final_matched_usd=0.0)
        self.assertEqual(intents["MKR_2"]["collat_drop_usd"], 0.0)

    def test_preempt_makers_for_instant_taker_arb_with_active_and_receivable_positions(self) -> None:
        import src.polymarket_research.riskless_protocol_v2_expansion as rpv2

        self.assertTrue(callable(rpv2.position_is_settlement_receivable))
        self.assertTrue(callable(rpv2.get_unleashed_v5_tier_profile))
        self.assertFalse(rpv2.position_is_settlement_receivable({"status": "POSITION_CONFIRMED"}))
        self.assertTrue(rpv2.position_is_settlement_receivable({"status": "AWAITING_ONCHAIN_SETTLEMENT"}))

        now_ts = 1_794_107_000.0
        ev_cross = asyncio.Event()
        ev_fifo = asyncio.Event()
        harv = SimpleNamespace(
            dry_run=False,
            active_positions={
                "WS_SNIPE_Miami_KMIA_242960": {
                    "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                    "status": "POSITION_CONFIRMED",
                    "notional_usd": 19.54,
                },
                "SETTLED_RECV_1": {
                    "trade_id": "SETTLED_RECV_1",
                    "status": "AWAITING_ONCHAIN_SETTLEMENT",
                    "notional_usd": 8.00,
                },
            },
            pending_entry_intents={
                "MKR_CROSS_LOW": {
                    "inflight_key": "IK_CROSS_LOW",
                    "market_id": "MKT_OTHER_1",
                    "live_maker_anchor_inflight": True,
                    "notional_usd": 15.88,
                    "fifo_rank1_verified": False,
                    "velocity_bps_hr": 12.0,
                    "order_id": "0xorder_low",
                },
                "MKR_CROSS_FIFO1": {
                    "inflight_key": "IK_CROSS_FIFO1",
                    "market_id": "MKT_OTHER_2",
                    "live_maker_anchor_inflight": True,
                    "notional_usd": 15.86,
                    "fifo_rank1_verified": True,
                    "velocity_bps_hr": 45.0,
                    "order_id": "0xorder_fifo",
                },
            },
            _maker_anchor_preempt_events={
                "IK_CROSS_LOW": ev_cross,
                "IK_CROSS_FIFO1": ev_fifo,
            },
            executor=SimpleNamespace(auth_mode="DRY_RUN", client=None),
        )
        # Non-fat (<200 bps) candidate with non-empty active_positions + cross_mkt_list -> 0 preemptions, no TypeError!
        cnt_thin, keys_thin = rpv2.preempt_makers_for_instant_taker_arb(
            harv,
            reason="SINGLE_LEG_LOCK_THIN",
            target_market_ids={"MKT_TARGET"},
            cand_net_cost=0.992,
            free_cash_hint=25.0,
            now_ts=now_ts,
        )
        self.assertEqual(cnt_thin, 0)
        self.assertEqual(keys_thin, set())
        self.assertFalse(ev_cross.is_set())

        # Fat (>=200 bps) candidate when free_cash_hint < target_arb_cash_usd -> preempts only non-FIFO intent needed to hit budget!
        cnt_fat, keys_fat = rpv2.preempt_makers_for_instant_taker_arb(
            harv,
            reason="SINGLE_LEG_LOCK_FAT",
            target_market_ids={"MKT_TARGET"},
            cand_net_cost=0.975,
            free_cash_hint=32.0,
            target_arb_cash_usd=45.0,
            now_ts=now_ts,
        )
        self.assertEqual(cnt_fat, 1)
        self.assertEqual(keys_fat, {"IK_CROSS_LOW"})
        self.assertTrue(ev_cross.is_set())
        self.assertFalse(ev_fifo.is_set())


if __name__ == "__main__":
    unittest.main()

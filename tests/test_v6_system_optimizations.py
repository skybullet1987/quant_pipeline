"""
Regression & benchmark tests for Dominus v6 system-wide computational and
infrastructure optimizations (`@sys-opt`).
"""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from src.polymarket_research.cross_venue_riskless_shadow import (
    NormalizedBinaryMarket,
    OrderLevel,
)
from src.polymarket_research.cross_venue_telemetry_and_watchdog import (
    ShadowTelemetryStore,
)
from src.polymarket_research.full_throttle_pipeline import (
    FullThrottlePipeline,
    OperatingCycleType,
    PipelineConfig,
    _KNOWN_FEE_SCHEDULES,
    _extract_market_fee_spec,
    _parse_json_list_safe,
)
from src.polymarket_research.full_universe_discovery import (
    FullUniverseRegistry,
    NormalizedBookSnapshot,
    NormalizedEvent,
    NormalizedInstrument,
    NormalizedMarket,
    SkipReason,
)
from src.polymarket_research.polymarket_terminal_recorder import (
    L2OrderBook,
    TICKET_CAPACITY_LEVELS,
)


def _make_sample_binary_market(
    idx: int,
    *,
    yes_ask: float = 0.47,
    yes_bid: float = 0.45,
    quote_ts_ms: int = 1_700_000_000_000,
    fee_bps: float = 0.0,
) -> NormalizedBinaryMarket:
    return NormalizedBinaryMarket(
        venue="polymarket",
        market_id=f"mkt_{idx}",
        slug=f"slug-{idx}",
        title=f"Market {idx}",
        category="crypto",
        oracle_family="UMA",
        rules_hash=f"hash_{idx}",
        end_ts=1_800_000_000.0,
        collateral_asset="USDC",
        suspended=False,
        expired=False,
        data_origin="LIVE_VERIFIED",
        yes_bids=[OrderLevel(yes_bid, 100.0 + j) for j in range(5)],
        yes_asks=[OrderLevel(round(yes_ask + 0.01 * j, 4), 100.0) for j in range(5)],
        no_bids=[OrderLevel(0.52, 100.0 + j) for j in range(5)],
        no_asks=[OrderLevel(round(0.55 + 0.01 * j, 4), 100.0) for j in range(5)],
        quote_ts_ms=quote_ts_ms,
        fee_rate_bps=fee_bps,
    )


class TestV6SystemOptimizations(unittest.TestCase):
    def test_shadow_telemetry_ingest_batched_and_bbo_skip_parity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = ShadowTelemetryStore(Path(td))
            now = 1_700_000_000.0
            mkts = [_make_sample_binary_market(i, quote_ts_ms=int(now * 1000)) for i in range(40)]

            ins_1 = store.ingest_markets(mkts, now_unix=now)
            self.assertEqual(ins_1, 40)
            self.assertEqual(len(store._catalog_meta_cache), 40)

            # Second ingest 30s later with 35/40 unchanged BBO -> only 5 should insert
            for i, m in enumerate(mkts):
                m.quote_ts_ms = int((now + 30.0) * 1000)
                if i < 5:
                    m.yes_asks[0] = OrderLevel(0.49, 100.0)
            ins_2 = store.ingest_markets(mkts, now_unix=now + 30.0)
            self.assertEqual(ins_2, 5)

            with store._connect() as conn:
                cat_cnt = conn.execute("SELECT COUNT(*) FROM market_catalog").fetchone()[0]
                snap_cnt = conn.execute("SELECT COUNT(*) FROM orderbook_snapshots").fetchone()[0]
            self.assertEqual(cat_cnt, 40)
            self.assertEqual(snap_cnt, 45)
            store.close()

    def test_shadow_telemetry_single_pass_window_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = ShadowTelemetryStore(Path(td))
            now = 1_700_000_000.0
            sid = store.start_session(
                network_mode="MODE_2_SHADOW",
                data_origin="LIVE_VERIFIED",
                now_unix=now - 1_800.0,
            )
            store.heartbeat_session(now_unix=now - 60.0)
            store.end_session(clean=True, now_unix=now - 60.0)

            store.record_api_event(
                venue="polymarket",
                event_type="TIMEOUT",
                fault_class="TIMEOUT",
                downtime_sec=4.5,
                detail="timeout",
                now_unix=now - 500.0,
            )
            store.record_resolution(
                candidate_key="polymarket:m1",
                winning_outcome="YES",
                settled_unit_payout_usd=1.0,
                simulated_realized_pnl_usd=3.25,
                data_origin="LIVE_VERIFIED",
                resolution_uid="r1",
                now_unix=now - 5_000.0,
            )
            with store._connect() as conn:
                # 1 live signal within 1h, 1 quarantined within 24h (outside 1h), 1 synthetic within 7d
                conn.execute(
                    """
                    INSERT INTO arbitrage_signals(
                        signal_uid, ts_unix, basket_id, basket_type, leg_count, venues_csv, data_origin,
                        gross_theo_edge_usd, sim_exec_edge_usd, obs_net_pnl_usd,
                        rodc_pct, lockup_hours, exec_risk, settle_risk,
                        theoretical_json, simulated_json, observed_json, cap_eff_json, contaminated
                    ) VALUES
                    ('s1', ?, 'b1', 'COMPLETE_SET', 2, 'polymarket,kalshi', 'LIVE_VERIFIED', 1.5, 1.2, 1.1, 10.0, 2.0, 0.0, 0.0, '{}', '{}', '{}', '{}', 0),
                    ('s2', ?, 'b2', 'COMPLETE_SET', 2, 'polymarket,kalshi', 'LIVE_VERIFIED', 9.0, 8.0, -2.0, 10.0, 2.0, 0.0, 0.0, '{}', '{}', '{}', '{}', 1),
                    ('s3', ?, 'b3', 'COMPLETE_SET', 2, 'polymarket,kalshi', 'OFFLINE_SYNTHETIC', 2.0, 1.8, 1.8, 10.0, 2.0, 0.0, 0.0, '{}', '{}', '{}', '{}', 0)
                    """,
                    (now - 300.0, now - 7_200.0, now - 100_000.0),
                )

            summaries = store.build_campaign_window_summaries(now_unix=now)
            self.assertEqual(summaries["1h"]["live_executable_signals"], 1)
            self.assertAlmostEqual(summaries["1h"]["live_simulated_executable_edge_usd"], 1.2, places=4)
            self.assertEqual(summaries["1h"]["quarantined_contaminated_signals"], 0)
            self.assertEqual(summaries["1h"]["api_error_events"], 1)
            self.assertAlmostEqual(summaries["1h"]["connection_downtime_sec"], 4.5, places=2)
            self.assertEqual(summaries["1h"]["live_resolutions_tracked"], 0)

            self.assertEqual(summaries["24h"]["quarantined_contaminated_signals"], 1)
            self.assertAlmostEqual(summaries["24h"]["quarantined_phantom_gross_usd"], 9.0, places=4)
            self.assertEqual(summaries["24h"]["live_resolutions_tracked"], 1)
            self.assertAlmostEqual(summaries["24h"]["live_resolution_realized_pnl_usd"], 3.25, places=4)
            self.assertEqual(summaries["7d"]["synthetic_offline_signals_segregated"], 1)
            store.close()

    def test_l2_orderbook_single_pass_execution_surface_and_cache(self) -> None:
        bk = L2OrderBook("tok_test")
        bids = [{"price": f"{0.48 - 0.01 * i:.2f}", "size": f"{40 + 10 * i}"} for i in range(15)]
        asks = [{"price": f"{0.50 + 0.01 * i:.2f}", "size": f"{30 + 15 * i}"} for i in range(15)]
        bk.apply_snapshot(bids, asks)

        t0 = bk.last_book_update_ts + 0.5
        m_full = bk.get_metrics(obs_ts=t0, fee_rate=0.01, compact=False)
        m_compact = bk.get_metrics(obs_ts=t0, fee_rate=0.01, compact=True)

        # Verify single-pass execution surface matches naive per-notional sweep
        sorted_asks = sorted(bk.asks.items(), key=lambda x: x[0])
        q_mid = (sorted_asks[0][0] + max(bk.bids)) / 2.0
        for notional in TICKET_CAPACITY_LEVELS:
            spent = 0.0
            shares = 0.0
            fees = 0.0
            for px, sz in sorted_asks:
                fd = min(notional - spent, px * sz)
                sh = fd / px
                fees += sh * 0.01 * px * (1.0 - px)
                spent += fd
                shares += sh
                if spent >= notional - 1e-6:
                    break
            exp_vwap = round(spent / shares, 4)
            exp_eff = round((spent + fees) / shares, 4)
            exp_cross = round(exp_eff - q_mid, 4)
            self.assertEqual(m_full[f"vwap_${int(notional)}"], exp_vwap)
            self.assertEqual(m_full[f"effective_price_${int(notional)}"], exp_eff)
            self.assertEqual(m_full[f"crossing_cost_${int(notional)}"], exp_cross)
            self.assertAlmostEqual(m_full[f"fill_fees_${int(notional)}"], round(fees, 5), delta=2e-5)

        self.assertEqual(m_compact["vwap_$50"], m_full["vwap_$50"])
        self.assertEqual(m_compact["effective_price_$50"], m_full["effective_price_$50"])

        # Cache hit must still advance quote-age timestamps
        m_later = bk.get_metrics(obs_ts=t0 + 2.0, fee_rate=0.01, compact=False)
        self.assertAlmostEqual(m_later["age_book_ms"] - m_full["age_book_ms"], 2000.0, delta=0.5)

        # Delta invalidates cache
        bk.apply_price_changes([{"price": "0.50", "size": "120", "side": "SELL"}])
        m_after = bk.get_metrics(obs_ts=t0 + 2.5, fee_rate=0.01, compact=False)
        self.assertEqual(m_after["ask_size_l1"], 120.0)
        self.assertGreater(m_after["book_sequence_id"], m_full["book_sequence_id"])

        # Micro-benchmark: 500x cached get_metrics should be fast (< 25ms)
        t_b0 = time.perf_counter()
        for k in range(500):
            bk.get_metrics(obs_ts=t0 + 3.0 + 0.01 * k)
        elapsed_ms = (time.perf_counter() - t_b0) * 1000.0
        self.assertLess(elapsed_ms, 25.0)

    def test_full_universe_registry_skips_noop_market_updates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reg = FullUniverseRegistry(Path(td) / "registry.sqlite3")
            try:
                raw_ev = {
                    "id": "e0",
                    "slug": "e0-slug",
                    "ticker": "E0",
                    "title": "Event 0",
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "enableOrderBook": True,
                    "negRisk": False,
                    "markets": [
                        {
                            "id": "m0",
                            "conditionId": "0x" + "1" * 64,
                            "questionID": "q0",
                            "slug": "m0-slug",
                            "question": "Test?",
                            "outcomes": '["Yes", "No"]',
                            "clobTokenIds": '["t0", "t1"]',
                            "outcomePrices": '["0.5", "0.5"]',
                            "active": True,
                            "closed": False,
                            "archived": False,
                            "acceptingOrders": True,
                            "enableOrderBook": True,
                            "feesEnabled": False,
                            "orderPriceMinTickSize": 0.01,
                            "orderMinSize": 5.0,
                            "volume24hr": 100.0,
                            "liquidityClob": 100.0,
                        }
                    ],
                }
                reg.ingest_events([raw_ev], now_ts=1000.0)

                # Update with two-sided healthy books -> market skip_codes remains ()
                healthy = {
                    "t0": NormalizedBookSnapshot(
                        token_id="t0",
                        bids=((0.49, 100.0),),
                        asks=((0.51, 100.0),),
                        best_bid=0.49,
                        best_bid_size=100.0,
                        best_ask=0.51,
                        best_ask_size=100.0,
                        resting_bid_depth_usd=50.0,
                        resting_ask_depth_usd=50.0,
                        tick_size=0.01,
                        min_order_size=5.0,
                        fetched_ts=1010.0,
                    ),
                    "t1": NormalizedBookSnapshot(
                        token_id="t1",
                        bids=((0.49, 100.0),),
                        asks=((0.51, 100.0),),
                        best_bid=0.49,
                        best_bid_size=100.0,
                        best_ask=0.51,
                        best_ask_size=100.0,
                        resting_bid_depth_usd=50.0,
                        resting_ask_depth_usd=50.0,
                        tick_size=0.01,
                        min_order_size=5.0,
                        fetched_ts=1010.0,
                    ),
                }
                res1 = reg.update_books_from_snapshots(healthy, now_ts=1010.0)
                self.assertEqual(res1["two_sided_healthy"], 2)
                self.assertEqual(reg.get_market("m0").skip_codes, ())

                # Transition to empty books -> market skip_codes must update to ZERO_RESTING_DEPTH
                empty = {
                    "t0": NormalizedBookSnapshot(
                        token_id="t0",
                        bids=(),
                        asks=(),
                        best_bid=0.0,
                        best_bid_size=0.0,
                        best_ask=0.0,
                        best_ask_size=0.0,
                        resting_bid_depth_usd=0.0,
                        resting_ask_depth_usd=0.0,
                        tick_size=0.01,
                        min_order_size=5.0,
                        fetched_ts=1020.0,
                    ),
                    "t1": NormalizedBookSnapshot(
                        token_id="t1",
                        bids=(),
                        asks=(),
                        best_bid=0.0,
                        best_bid_size=0.0,
                        best_ask=0.0,
                        best_ask_size=0.0,
                        resting_bid_depth_usd=0.0,
                        resting_ask_depth_usd=0.0,
                        tick_size=0.01,
                        min_order_size=5.0,
                        fetched_ts=1020.0,
                    ),
                }
                res2 = reg.update_books_from_snapshots(empty, now_ts=1020.0)
                self.assertEqual(res2["zero_depth_marked"], 2)
                self.assertEqual(reg.get_market("m0").skip_codes, (SkipReason.ZERO_RESTING_DEPTH.value,))
            finally:
                reg.close()

    def test_full_throttle_helpers_and_cycle_parity(self) -> None:
        self.assertEqual(_parse_json_list_safe('["a", "b"]'), ["a", "b"])
        self.assertEqual(_parse_json_list_safe("not-json"), [])
        self.assertIn("crypto_15_min", _KNOWN_FEE_SCHEDULES)
        self.assertEqual(_extract_market_fee_spec({"feeType": "crypto_15_min"}), (2500.0, 2.0))
        self.assertEqual(_extract_market_fee_spec({"feesEnabled": False}), (0.0, 1.0))

        events = []
        raw_books = {}
        for i in range(25):
            t0, t1 = f"t_{i}_0", f"t_{i}_1"
            events.append(
                {
                    "id": f"ev_{i}",
                    "slug": f"ev-{i}",
                    "title": f"Event {i}",
                    "active": True,
                    "closed": False,
                    "negRisk": False,
                    "markets": [
                        {
                            "id": f"m_{i}",
                            "conditionId": f"0x{i:064x}",
                            "question": f"Will {i} happen?",
                            "outcomes": '["Yes", "No"]',
                            "clobTokenIds": json.dumps([t0, t1]),
                            "outcomePrices": '["0.48", "0.52"]',
                            "active": True,
                            "closed": False,
                            "archived": False,
                            "enableOrderBook": True,
                            "feesEnabled": False,
                            "liquidityClob": 1000.0,
                            "volume24hr": 1000.0,
                        }
                    ],
                }
            )
            if i < 5:
                raw_books[t0] = {"asks": [{"price": "0.49", "size": "100"}], "bids": [{"price": "0.47", "size": "100"}]}
                raw_books[t1] = {"asks": [{"price": "0.50", "size": "100"}], "bids": [{"price": "0.48", "size": "100"}]}

        with tempfile.TemporaryDirectory() as td:
            cfg = PipelineConfig(output_dir=Path(td), harvester_candidates_path=Path(td) / "cand.jsonl")
            pipe = FullThrottlePipeline(config=cfg)
            res = pipe.run_cycle(
                OperatingCycleType.DISCOVERY_CYCLE,
                synthetic_events=events,
                synthetic_raw_books=raw_books,
            )
            self.assertEqual(res["universe_coverage"]["fresh_l2_book_markets_this_cycle"], 5)
            self.assertEqual(res["universe_coverage"]["unresolved_or_ineligible_skip_counts"]["COLD_LAYER_AWAITING_ROTATION"], 20)
            res2 = pipe.run_cycle(
                OperatingCycleType.FAST_CYCLE,
                synthetic_events=events,
                synthetic_raw_books=raw_books,
            )
            self.assertEqual(res2["universe_coverage"]["fresh_l2_book_markets_this_cycle"], 5)


if __name__ == "__main__":
    unittest.main()

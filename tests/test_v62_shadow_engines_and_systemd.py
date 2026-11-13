"""
Phase 2 tests for shadow engines, Protocol V2 fast paths, data-feed wiring,
and systemd resource alignment (`@engines-systemd`).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
import time
import types
import unittest
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Allow tests on stdlib-only Windows Python even if optional `requests` package is absent.
if "requests" not in sys.modules:
    try:
        import requests  # noqa: F401
    except ImportError:
        stub_req = types.ModuleType("requests")

        class _DummySession:
            def __init__(self) -> None:
                self.headers = {}

            def post(self, *args, **kwargs):
                raise RuntimeError("offline_dummy_session")

            def get(self, *args, **kwargs):
                raise RuntimeError("offline_dummy_session")

        stub_req.Session = _DummySession  # type: ignore[attr-defined]
        sys.modules["requests"] = stub_req


class TestSystemdUnitAlignments(unittest.TestCase):
    def test_v62_systemd_units_resource_and_allocator_alignment(self) -> None:
        from tests.test_zero_trust_forensic_audit import test_v35_systemd_units_are_uniform_and_graceful

        test_v35_systemd_units_are_uniform_and_graceful()

        harv_txt = (ROOT / "systemd" / "polymarket-live-harvester.service").read_text(encoding="utf-8")
        self.assertIn("Environment=MALLOC_ARENA_MAX=2", harv_txt)
        self.assertIn("Nice=-10", harv_txt)
        self.assertIn("CPUWeight=1000", harv_txt)
        self.assertIn("IOWeight=1000", harv_txt)
        self.assertIn("OOMScoreAdjust=-900", harv_txt)

        rec_txt = (ROOT / "systemd" / "polymarket-recorder.service").read_text(encoding="utf-8")
        self.assertIn("Environment=MALLOC_ARENA_MAX=2", rec_txt)
        self.assertIn("CPUWeight=80", rec_txt)
        self.assertIn("IOWeight=80", rec_txt)
        self.assertIn("MemoryHigh=650M", rec_txt)
        self.assertIn("MemoryMax=750M", rec_txt)
        self.assertIn("MemorySwapMax=0", rec_txt)

        a124_txt = (ROOT / "systemd" / "polymarket-alpha124-shadow.service").read_text(encoding="utf-8")
        self.assertIn("Environment=MALLOC_ARENA_MAX=2", a124_txt)
        self.assertIn("CPUWeight=50", a124_txt)
        self.assertIn("MemoryHigh=950M", a124_txt)
        self.assertIn("MemoryMax=1100M", a124_txt)
        self.assertIn("MemorySwapMax=0", a124_txt)


class TestUniversalArbVerifierFastPaths(unittest.TestCase):
    def test_integer_micro_quantizer_parity_with_decimal(self) -> None:
        from src.polymarket_research.universal_arb_verifier import (
            ActionLeg,
            ActionType,
            BookLevel,
            CandidateStructure,
            InstrumentOrderBook,
            StateSpec,
            UniversalArbVerifier,
            VerificationConfig,
            quantize_clob_fok_order,
            quantize_polymarket_price,
        )

        def ref_quant(raw_p: float, tick: float, side: str, is_maker: bool) -> float:
            p_cl = min(0.999999, max(0.000001, float(raw_p)))
            d_p = Decimal(str(round(p_cl, 6)))
            d_t = Decimal(str(tick))
            if (side.upper() == "BUY" and is_maker) or (side.upper() == "SELL" and not is_maker):
                steps = (d_p / d_t).quantize(Decimal("1"), rounding=ROUND_FLOOR)
            else:
                steps = (d_p / d_t).quantize(Decimal("1"), rounding=ROUND_CEILING)
            return float(min(Decimal("1") - d_t, max(d_t, steps * d_t)))

        for px in (0.0014, 0.0399, 0.04, 0.505, 0.96, 0.9924, 0.9995):
            for tick in (0.01, 0.001, 0.005):
                for side in ("BUY", "SELL"):
                    for is_maker in (True, False):
                        q_px, q_tk = quantize_polymarket_price(px, side=side, explicit_tick_size=tick, is_maker=is_maker)
                        self.assertAlmostEqual(q_px, ref_quant(px, q_tk, side, is_maker), places=6)

        fok = quantize_clob_fok_order(6.123456, 0.555, side="BUY", explicit_tick_size=0.01, min_order_size=5.0)
        self.assertTrue(fok["valid"])
        self.assertAlmostEqual(float(fok["quantized_price"]), 0.56, places=6)
        self.assertGreaterEqual(float(fok["gross_shares"]), 5.0)

        fok_sell = quantize_clob_fok_order(7.5, 0.444, side="SELL", explicit_tick_size=0.01, min_order_size=5.0)
        self.assertTrue(fok_sell["valid"])
        self.assertAlmostEqual(float(fok_sell["quantized_price"]), 0.44, places=6)

        v = UniversalArbVerifier(VerificationConfig(max_budget_usd=45.0, lot_step_shares=0.01))
        cand = CandidateStructure(
            candidate_id="c1",
            family="C1",
            legs=(ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="t0", market_id="m0", weight=1.0),),
            states=(StateSpec(state_id="yes", instrument_payouts={"t0": 1.0}),),
        )
        book = InstrumentOrderBook(
            instrument_id="t0",
            market_id="m0",
            asks=(BookLevel(0.45, 10.0), BookLevel(0.46, 15.0)),
            bids=(),
            tick_size=0.01,
            min_order_size=5.0,
        )
        min_q, max_q, grid = v._collect_candidate_quantities(cand, {"t0": book}, {}, 0.0, 0.0)
        self.assertGreaterEqual(min_q, 5.0)
        self.assertAlmostEqual(max_q, 25.0, places=6)
        self.assertIn(10.0, grid)
        self.assertIn(25.0, grid)

        sample = {"b": [1, 2], "a": {"z": True, "x": 3.5}}
        ref_sha = hashlib.sha256(json.dumps(sample, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(UniversalArbVerifier._compute_canonical_sha256(sample), ref_sha)


class TestTradfiPythAndPolyBolt(unittest.TestCase):
    def test_fetch_pyth_intraday_or_spot_blends_streams_and_90s_yahoo_fallback(self) -> None:
        from src.polymarket_research.tradfi_sports_zero_fee_engine import fetch_pyth_intraday_or_spot_sync

        now = 1_794_600_000.0
        cached_yahoo = {"spot": 599.5, "sigma_session": 0.31, "bars": [(1, 2)], "fetched_ts": now - 20.0}

        class FakePythStream:
            def get_latest(self, sym: str, max_age_sec: float = 4.0):
                self.last_sym = sym
                return {"price": 601.25, "conf": 0.12, "rx_ts": now - 0.5, "publish_time": now - 0.5, "source": "pyth_hermes_sse"}

        class FakePolyBoltStream:
            def get_latest_spot(self, sym: str, now_ts: float = 0.0, max_age_sec: float = 4.0):
                return (601.55, now - 0.1)

        with mock.patch.dict(os.environ, {"DOMINUS_NETWORK_MODE": "offline"}):
            r1 = fetch_pyth_intraday_or_spot_sync(
                "SPY",
                "SPY",
                0.22,
                pyth_stream=FakePythStream(),
                cached_yahoo=cached_yahoo,
                now_ts=now,
            )
            self.assertIsNotNone(r1)
            self.assertAlmostEqual(r1["spot"], 601.25, places=4)
            self.assertAlmostEqual(r1["conf"], 0.12, places=4)
            self.assertAlmostEqual(r1["sigma_session"], 0.31, places=4)
            self.assertEqual(r1["spot_source"], "pyth_hermes_sse")

            class OlderPyth:
                def get_latest(self, sym: str, max_age_sec: float = 4.0):
                    return {"price": 600.80, "conf": 0.10, "rx_ts": now - 2.0, "source": "pyth_hermes_sse"}

            r2 = fetch_pyth_intraday_or_spot_sync(
                "SPY",
                "SPY",
                0.22,
                pyth_stream=OlderPyth(),
                chainlink_stream=FakePolyBoltStream(),
                cached_yahoo=cached_yahoo,
                now_ts=now,
            )
            self.assertIsNotNone(r2)
            self.assertAlmostEqual(r2["spot"], 601.55, places=4)
            self.assertEqual(r2["spot_source"], "polybolt_price_equity")

            r3 = fetch_pyth_intraday_or_spot_sync(
                "SPY",
                "SPY",
                0.22,
                cached_yahoo=cached_yahoo,
                now_ts=now,
            )
            self.assertIsNotNone(r3)
            self.assertAlmostEqual(r3["spot"], 599.5, places=4)
            self.assertEqual(r3["spot_source"], "yahoo_1m_fallback")


class TestUmaAndMacroUpgrades(unittest.TestCase):
    def test_uma_verify_ws_fast_path_dispute_veto_and_d001_guard(self) -> None:
        from src.polymarket_research.uma_nba_endgame_engine import verify_uma_onchain_proposal_sync

        class FakeWsDisputed:
            def get_market_oo_status(self, mid: str, max_age_sec: float = 3600.0):
                return {"status": "DISPUTED", "event_kind": "DisputePrice"}

        mkt = {
            "id": "991234",
            "conditionId": "0x" + "1" * 64,
            "questionID": "0x" + "2" * 64,
            "question": "Will Boston Celtics win vs Lakers?",
            "outcomes": '["Yes","No"]',
            "clobTokenIds": '["tok_y","tok_n"]',
            "umaResolutionStatus": "proposed",
            "resolvedBy": "0x6a9d222616c90fca5754cd1333cfd9b7fb6a4f74",
            "umaResolutionAdapter": "0x6a9d222616c90fca5754cd1333cfd9b7fb6a4f74",
            "enableOrderBook": True,
            "acceptingOrders": True,
            "closed": False,
            "active": True,
        }
        with mock.patch("src.polymarket_research.uma_nba_endgame_engine._rpc_post") as m_rpc:
            res = verify_uma_onchain_proposal_sync(mkt, scoped_logs_ws=FakeWsDisputed())
            self.assertFalse(res["verified"])
            self.assertEqual(res["reason"], "WS_DISPUTE_PRICE_VETO")
            m_rpc.assert_not_called()

        res_kmia = verify_uma_onchain_proposal_sync({**mkt, "id": "6707503"})
        self.assertFalse(res_kmia["verified"])
        self.assertEqual(res_kmia["reason"], "D001_DISPUTED_KMIA_QUARANTINED")

    def test_macro_catalyst_feeds_dormant_outside_and_active_inside_window(self) -> None:
        import src.polymarket_research.macro_counting_ctf_engine as mc_mod
        from src.polymarket_research.macro_counting_ctf_engine import (
            evaluate_pyth_catalyst_shock,
            poll_macro_catalyst_feeds_sync,
        )

        mc_mod._MACRO_FEED_CACHE = (0.0, "", None)
        fake_client = mock.MagicMock()
        fake_client.fetch_fed_rss_sync.return_value = [{"title": "FOMC Rate Statement", "source": "fed_rss"}]

        with mock.patch("src.polymarket_research.macro_counting_ctf_engine._get_macro_event_feed_client", return_value=fake_client):
            with mock.patch("src.polymarket_research.macro_counting_ctf_engine.is_in_scheduled_macro_catalyst_window", return_value=(False, "")):
                out_dormant = poll_macro_catalyst_feeds_sync(now_ts=1_794_600_000.0)
                self.assertFalse(out_dormant["in_window"])
                self.assertTrue(out_dormant["dormant"])
                fake_client.fetch_fed_rss_sync.assert_not_called()

            with mock.patch("src.polymarket_research.macro_counting_ctf_engine.is_in_scheduled_macro_catalyst_window", return_value=(True, "FOMC_1400ET")):
                out_active = poll_macro_catalyst_feeds_sync(now_ts=1_794_600_100.0)
                self.assertTrue(out_active["in_window"])
                self.assertFalse(out_active["dormant"])
                self.assertEqual(out_active["catalyst"], "FOMC_1400ET")
                fake_client.fetch_fed_rss_sync.assert_called_once()
                ev = evaluate_pyth_catalyst_shock(
                    "SPY",
                    prev_spot=596.0,
                    cur_spot=599.5,
                    strike=601.0,
                    direction="above",
                    eff_session_hours=2.0,
                    sigma_session=0.22,
                    now_ts=1_794_600_100.0,
                )
                self.assertEqual(ev["official_macro_feed"]["fed_release_count"], 1)
                self.assertEqual(ev["official_macro_feed"]["catalyst"], "FOMC_1400ET")


class TestV6EnginesUpgrades(unittest.TestCase):
    def test_live_cad_usd_wire_and_stale_fallback(self) -> None:
        import src.polymarket_research.riskless_expansion_v6_engines as v6
        from src.polymarket_research.riskless_expansion_v6_engines import (
            OrderLevel,
            NormalizedBinaryMarket,
            evaluate_stx_forecastex_fx_invariant_box,
        )

        stx_m = NormalizedBinaryMarket(
            venue="stx_ontario",
            market_id="stx_1",
            slug="stx-1",
            title="Bank of Canada hold?",
            category="macro",
            yes_asks=[OrderLevel(0.42, 300.0)],
            no_asks=[OrderLevel(0.54, 300.0)],
            yes_bids=[OrderLevel(0.40, 300.0)],
            no_bids=[OrderLevel(0.52, 300.0)],
            fee_rate_bps=200.0,
            fee_enabled=True,
            collateral_asset="CAD",
            lot_size=1.0,
            min_shares=5.0,
        )
        fex_m = NormalizedBinaryMarket(
            venue="forecastex",
            market_id="fex_1",
            slug="fex-1",
            title="Bank of Canada hold?",
            category="macro",
            yes_asks=[OrderLevel(0.35, 300.0)],
            no_asks=[OrderLevel(0.66, 300.0)],
            yes_bids=[OrderLevel(0.33, 300.0)],
            no_bids=[OrderLevel(0.64, 300.0)],
            fee_rate_bps=50.0,
            fee_enabled=True,
            collateral_asset="USD",
            lot_size=1.0,
            min_shares=5.0,
            settlement_delay_hours=2.0,
        )

        v6._FX_CAD_USD_CACHE = None
        with mock.patch("src.polymarket_research.riskless_fast_feeds.fetch_live_cad_usd_sync") as m_fx:
            m_fx.return_value = {"bid": 0.7295, "ask": 0.7305, "mid": 0.7300, "ts": time.time(), "source": "pyth_usdcad", "stale": False, "is_daily_ref": False}
            with mock.patch.dict(os.environ, {"DOMINUS_NETWORK_MODE": "online"}):
                opp = evaluate_stx_forecastex_fx_invariant_box(
                    pair_id="p_live",
                    stx_market=stx_m,
                    stx_side="NO",
                    stx_execution_style="PASSIVE_MAKER",
                    forecastex_market=fex_m,
                    forecastex_side="YES",
                    target_usd_shares=50.0,
                )
            self.assertIsNotNone(opp)
            self.assertEqual(opp.metadata["fx_source"], "pyth_usdcad")
            self.assertFalse(opp.metadata["fx_stale"])
            self.assertFalse(opp.metadata["is_daily_ref"])

            v6._FX_CAD_USD_CACHE = None
            m_fx.return_value = {"bid": 0.7100, "ask": 0.7120, "mid": 0.7110, "ts": time.time(), "source": "boc_daily", "stale": False, "is_daily_ref": True}
            with mock.patch.dict(os.environ, {"DOMINUS_NETWORK_MODE": "online"}):
                opp_fb = evaluate_stx_forecastex_fx_invariant_box(
                    pair_id="p_boc",
                    stx_market=stx_m,
                    stx_side="NO",
                    stx_execution_style="PASSIVE_MAKER",
                    forecastex_market=fex_m,
                    forecastex_side="YES",
                    target_usd_shares=50.0,
                )
            self.assertIsNotNone(opp_fb)
            self.assertTrue(opp_fb.metadata["fx_stale"])
            self.assertFalse(opp_fb.metadata["is_daily_ref"])

    def test_deribit_ws_cache_used_before_rest_and_subset_no_2leg_tag(self) -> None:
        from src.polymarket_research.riskless_expansion_v6_engines import (
            NormalizedBinaryMarket,
            OrderLevel,
            SubsetNoCandidateOutcome,
            _fetch_deribit_usdc_public_options,
            detect_cross_venue_subset_no_boxes,
        )

        class FakeDeribitWs:
            def get_quotes_by_currency(self, ccy: str, max_age_sec: float = 5.0):
                if ccy != "BTC_USDC":
                    return {}
                return {
                    "BTC_USDC-29DEC26-90000-C": {
                        "instrument_name": "BTC_USDC-29DEC26-90000-C",
                        "best_bid_price": 1200.0,
                        "best_bid_amount": 3.0,
                        "best_ask_price": 1250.0,
                        "best_ask_amount": 3.0,
                        "underlying_price": 91000.0,
                    }
                }

        class ExplodingTransport:
            async def get_json(self, url: str):
                raise AssertionError("REST must not be hit when DeribitPublicWs cache is populated")

        holder = types.SimpleNamespace(_deribit_public_ws=FakeDeribitWs())
        quotes = asyncio.run(_fetch_deribit_usdc_public_options(ExplodingTransport(), cache_holder=holder, now_ts=1_794_600_000.0))
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].instrument_name, "BTC_USDC-29DEC26-90000-C")
        self.assertAlmostEqual(quotes[0].best_ask_usd, 1250.0, places=3)

        mkts = [
            SubsetNoCandidateOutcome(
                outcome_key=f"out_{i}",
                market=NormalizedBinaryMarket(
                    venue="polymarket",
                    market_id=f"m{i}",
                    slug=f"m-{i}",
                    title=f"Outcome {i}",
                    category="general",
                    yes_asks=[OrderLevel(0.75, 100.0)],
                    no_asks=[OrderLevel(0.28, 100.0)],
                    yes_bids=[OrderLevel(0.70, 100.0)],
                    no_bids=[OrderLevel(0.26, 100.0)],
                    partition_group_id="evt_99",
                ),
                cancel_payout_mode="50_50",
            )
            for i in range(2)
        ]
        opps = detect_cross_venue_subset_no_boxes("evt_99", mkts, subset_sizes=(2,), target_notional_usd=20.0)
        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0].metadata.get("box_type"), "NEGRISK_2LEG")


class TestProtocolV2Upgrades(unittest.TestCase):
    def test_quantize_dynamic_tick_price_integer_micro_parity(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import quantize_dynamic_tick_price

        for px in (0.0014, 0.0399, 0.505, 0.96, 0.9924):
            for tick in (0.01, 0.001):
                for side in ("BUY", "SELL"):
                    for mode in ("maker", "taker", "nearest"):
                        q_px, q_tick, ok = quantize_dynamic_tick_price(px, side=side, mode=mode, explicit_tick_size=tick, shares=6.0)
                        self.assertTrue(ok)
                        d_p = Decimal(str(round(min(0.999999, max(0.000001, px)), 6)))
                        d_t = Decimal(str(q_tick))
                        if mode == "nearest":
                            steps = (d_p / d_t).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                        elif (side == "BUY" and mode == "maker") or (side == "SELL" and mode == "taker"):
                            steps = (d_p / d_t).quantize(Decimal("1"), rounding=ROUND_FLOOR)
                        else:
                            steps = (d_p / d_t).quantize(Decimal("1"), rounding=ROUND_CEILING)
                        ref = float(min(Decimal("1") - d_t, max(d_t, steps * d_t)))
                        self.assertAlmostEqual(q_px, ref, places=6)

    def test_polygon_oo_poll_ws_fast_path_and_d001_quarantine(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import _poll_polygon_oo_proposal_and_dispute_mids_sync

        class FakeLogsWs:
            def is_healthy(self, max_silence_sec: float = 12.0):
                return True

            def drain_events(self, max_items: int = 128):
                return [
                    {"event_kind": "ProposePrice", "market_ids": ["888111", "6707503"], "block_number": 70000123, "quarantined_d001": False},
                    {"event_kind": "DisputePrice", "market_ids": ["888222"], "block_number": 70000124, "quarantined_d001": False},
                ]

        bn, prop, disp = _poll_polygon_oo_proposal_and_dispute_mids_sync(70000100, scoped_logs_ws=FakeLogsWs())
        self.assertEqual(bn, 70000124)
        self.assertEqual(prop, ["888111"])
        self.assertEqual(disp, ["888222"])

    def test_desired_market_ws_tokens_includes_dormant_fast_rescan_tokens(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import desired_market_ws_tokens_impl

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dormant_fast_rescan_tokens.json"
            p.write_text(
                json.dumps({"updated_at_unix": time.time(), "token_ids": ["tok_dorm_1", "tok_dorm_2"]}),
                encoding="utf-8",
            )
            harv = types.SimpleNamespace(
                active_positions={"p1": {"token_id": "tok_active_1"}},
                pending_entry_intents={},
                dry_run=False,
                dormant_fast_rescan_path=p,
                _stage_b_decay_tracker=types.SimpleNamespace(watched_token_ids=lambda limit=64: []),
                _pos_market_ws=types.SimpleNamespace(num_shards=1, max_tokens=10),
            )
            toks = desired_market_ws_tokens_impl(harv)
            self.assertEqual(toks, ["tok_active_1", "tok_dorm_1", "tok_dorm_2"])

    def test_rb_n5_native_cumulative_markets_cal1_exposure(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            detect_rb_n5_cumulative_cal1_opportunities,
            extract_rb_n5_cumulative_cal1_candidates,
        )

        now = 1_794_600_000.0
        evts = [
            {
                "id": "ev_cum_1",
                "title": "Fed rate cut deadline",
                "cumulativeMarkets": True,
                "markets": [
                    {
                        "id": "m_early",
                        "conditionId": "0xc1",
                        "question": "Will Fed cut by May 2027?",
                        "endDate": "2027-05-01T00:00:00Z",
                        "clobTokenIds": ["y_early", "n_early"],
                        "feesEnabled": False,
                    },
                    {
                        "id": "m_late",
                        "conditionId": "0xc2",
                        "question": "Will Fed cut by Nov 2027?",
                        "endDate": "2027-11-01T00:00:00Z",
                        "clobTokenIds": ["y_late", "n_late"],
                        "feesEnabled": False,
                    },
                ],
            },
            {
                "id": "ev_non_cum",
                "title": "Non-cumulative control",
                "cumulativeMarkets": False,
                "markets": [
                    {"id": "m3", "question": "A in May 2027?", "endDate": "2027-05-01T00:00:00Z", "clobTokenIds": ["y3", "n3"]},
                    {"id": "m4", "question": "A in Nov 2027?", "endDate": "2027-11-01T00:00:00Z", "clobTokenIds": ["y4", "n4"]},
                ],
            },
        ]
        cands = extract_rb_n5_cumulative_cal1_candidates(evts, now_ts=now)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["event_id"], "ev_cum_1")
        books = {
            "y_early": {"asks": [{"price": "0.45", "size": "20"}]},
            "n_late": {"asks": [{"price": "0.52", "size": "20"}]},
        }
        hits = detect_rb_n5_cumulative_cal1_opportunities(cands, books, now_ts=now)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["sleeve"], "CAL1_RB_N5_CUMULATIVE_BOX")
        self.assertAlmostEqual(hits[0]["cost_per_share"], 0.97, places=5)

    def test_80_199_bps_carry_recycling_round_ceiling_net_positive_gate(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import try_recycle_open_carry_for_fast_arb_v2

        now = 1_794_600_000.0
        fake_cands = [
            {
                "pos_key": "carry_1",
                "bid_px": 0.985,
                "min_sell_px": 0.984,
                "shares": 25.0,
                "notional_usd": 24.50,
                "cost_per_share": 0.980,
                "market_id": "m_carry",
            }
        ]
        ex = mock.MagicMock()
        ex.execute_unwind_order.return_value = {"filled": True, "proceeds_usd": 24.625, "filled_shares": 25.0, "avg_price": 0.985}
        ex.get_collateral_balance.return_value = 30.0

        def _make_harv():
            return types.SimpleNamespace(
                executor=ex,
                active_positions={
                    "carry_1": {"market_id": "m_carry", "token_id": "tok_carry", "shares": 25.0, "maker_tp_order_id": "tp_1"}
                },
                closed_trades=[],
                _last_known_collateral=5.0,
            )

        with mock.patch("src.polymarket_research.stage_c_zero_loss_velocity.find_recyclable_zero_loss_open_carries", return_value=fake_cands):
            h_ok = _make_harv()
            res_ok = try_recycle_open_carry_for_fast_arb_v2(
                h_ok,
                needed_cash_gap_usd=18.0,
                challenger_net_cost=0.988,
                challenger_rem_tte_sec=120.0,
                challenger_sleeve="C1_BINARY_COMPLETE_SET",
                exit_spread_slippage_bps=40.0,
                lost_rebate_bps=10.0,
                safety_buffer_bps=5.0,
                now_ts=now,
            )
            self.assertEqual(res_ok["recycled_count"], 1)
            self.assertGreater(res_ok["freed_cash_usd"], 20.0)

            ex.reset_mock()
            h_veto = _make_harv()
            res_veto = try_recycle_open_carry_for_fast_arb_v2(
                h_veto,
                needed_cash_gap_usd=18.0,
                challenger_net_cost=0.988,
                challenger_rem_tte_sec=120.0,
                challenger_sleeve="C1_BINARY_COMPLETE_SET",
                exit_spread_slippage_bps=120.0,
                lost_rebate_bps=2.0,
                safety_buffer_bps=5.0,
                now_ts=now,
            )
            self.assertEqual(res_veto["recycled_count"], 0)
            self.assertEqual(res_veto["reason"], "CEILING_HURDLE_VETO")
            ex.execute_unwind_order.assert_not_called()


class TestAlpha124Grad8AndFeedWiring(unittest.TestCase):
    def test_grad8_promotion_rules_and_nav_gates(self) -> None:
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod

        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            st_file = tp / "state.json"
            mir_file = tp / "mirror.json"
            opps_file = tp / "opps.json"
            with (
                mock.patch.object(a124_mod, "STATE_FILE", st_file),
                mock.patch.object(a124_mod, "DATA_DIR", tp),
                mock.patch.object(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", mir_file),
                mock.patch.object(a124_mod, "OPPS_FILE", opps_file),
            ):
                d = a124_mod.Alpha124ShadowDaemon(single_scan=True)
                now = time.time()

                def _win(sl: str, idx: int, extra=None):
                    return {
                        "sleeve": sl,
                        "status": "CLOSED",
                        "won": True,
                        "asset_or_city": "POLY",
                        "tier_pnls_usd": {"T1000": 1.25},
                        "extra": extra or {},
                        "close_ts": now - idx,
                    }

                d.closed_positions = (
                    [_win("TAIL_BOUNDARY_001_ARB", i) for i in range(8)]
                    + [_win("BOND3_MULTISOURCE_DEAD_SPLIT", i) for i in range(8)]
                    + [_win("XV_SUBSET_NO_BOX", i, {"box_type": "NEGRISK_2LEG", "neg_risk_augmented": False, "legs": [{}, {}]}) for i in range(8)]
                    + [_win("XV_FX_INVARIANT_CAD_USD_BOX", i) for i in range(8)]
                    + [_win("DERIBIT_VERTICAL_SUPER_REP", i) for i in range(8)]
                )
                d.open_positions = {}
                d.write_state_files([])
                state = json.loads(st_file.read_text(encoding="utf-8"))
                by_sl = state["by_sleeve"]
                self.assertTrue(by_sl["TAIL_BOUNDARY_001_ARB"]["grad8_live_promoted"])
                self.assertTrue(by_sl["BOND3_MULTISOURCE_DEAD_SPLIT"]["grad8_live_promoted"])
                self.assertTrue(by_sl["XV_SUBSET_NO_BOX"]["grad8_live_promoted"])
                self.assertFalse(by_sl["XV_FX_INVARIANT_CAD_USD_BOX"]["grad8_live_promoted"])
                self.assertFalse(by_sl["DERIBIT_VERTICAL_SUPER_REP"]["grad8_live_promoted"])

                d.closed_positions = [
                    _win("XV_SUBSET_NO_BOX", i, {"box_type": "NEGRISK_2LEG", "neg_risk_augmented": True, "legs": [{}, {}]})
                    for i in range(8)
                ]
                d.write_state_files([])
                state_aug = json.loads(st_file.read_text(encoding="utf-8"))
                self.assertFalse(state_aug["by_sleeve"]["XV_SUBSET_NO_BOX"]["grad8_live_promoted"])

    def test_alpha124_get_pyth_intraday_uses_pyth_and_polybolt(self) -> None:
        from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon

        d = Alpha124ShadowDaemon(single_scan=True)
        now = time.time()
        d.pyth_intraday_cache["SPY"] = (now - 10.0, {"spot": 599.0, "sigma_session": 0.28, "bars": [], "fetched_ts": now - 10.0})
        d._pyth_hermes_stream = types.SimpleNamespace(
            get_latest=lambda sym, max_age_sec=4.0: {"price": 602.5, "conf": 0.08, "rx_ts": now - 0.3, "source": "pyth_hermes_sse"}
        )
        with mock.patch.dict(os.environ, {"DOMINUS_NETWORK_MODE": "offline"}):
            res = asyncio.run(d._get_pyth_intraday("SPY", now))
        self.assertIsNotNone(res)
        self.assertAlmostEqual(res["spot"], 602.5, places=4)
        self.assertAlmostEqual(res["sigma_session"], 0.28, places=4)

    def test_desired_d1_ws_tokens_accepts_counting_bracket_dataclasses(self) -> None:
        from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon
        from src.polymarket_research.macro_counting_ctf_engine import CountingBracket, CountingSlateSpec

        d = Alpha124ShadowDaemon(single_scan=True)
        now = time.time()
        cb = CountingBracket(
            market_id="m_cnt_1",
            condition_id="0xcnt1",
            label="100-119",
            low_count=100,
            high_count=119,
            yes_token="tok_cnt_yes",
            no_token="tok_cnt_no",
        )
        d.counting_slates = {
            "ev_cnt_1": CountingSlateSpec(
                event_id="ev_cnt_1",
                slug="cnt-1",
                series_slug="cnt-series",
                handle="@elonmusk",
                title="Count?",
                window_start_ts=now - 3600.0,
                window_end_ts=now + 3600.0,
                gamma_closed_floor=0,
                brackets=[cb],
            )
        }
        toks = d._desired_d1_ws_tokens(now, max_cap=100)
        self.assertIn("tok_cnt_no", toks)
        self.assertIn("tok_cnt_yes", toks)

    def test_projections_full_throttle_telemetry_and_empirical_runrate(self) -> None:
        from datetime import datetime, timedelta, timezone
        from scripts import polymarket_daily_projections as pdp

        now = time.time()
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            cov_p = tdp / "universe_coverage.json"
            ftd_p = tdp / "full_throttle_dashboard.json"
            cov_p.write_text(
                json.dumps(
                    {
                        "universe_summary": {
                            "total_events": 19633,
                            "total_markets": 365805,
                            "active_orderbook_markets": 173244,
                            "total_tokens": 346488,
                        }
                    }
                ),
                encoding="utf-8",
            )
            ftd_p.write_text(
                json.dumps(
                    {
                        "schema": "dominus_full_throttle_dashboard_v1",
                        "section_1b_proposition_graph": {"total_edges": 5547},
                        "section_2_opportunity_metrics": {"rule_mismatch_rejections_prevented": 21208},
                        "section_2c_dormant_opportunity_store": {"active_dormant_count": 1200},
                        "section_2d_hedged_maker_shadow_quoter": {"net_post_adverse_shadow_pnl_ex_rebate_usd": 537.68},
                    }
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(pdp, "UNIVERSE_COVERAGE_FILE", cov_p),
                mock.patch.object(pdp, "FULL_THROTTLE_DASHBOARD_FILE", ftd_p),
            ):
                tel = pdp._load_full_throttle_telemetry()
                self.assertEqual(tel["total_events"], 19633)
                self.assertEqual(tel["total_markets"], 365805)
                self.assertEqual(tel["proposition_graph_edges"], 5547)
                self.assertEqual(tel["rule_trap_blocks"], 21208)
                self.assertEqual(tel["dormant_near_arbs"], 1200)
                self.assertAlmostEqual(tel["family_l_shadow_pnl_usd"], 537.68, places=2)

        now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
        live_st = {
            "live_bankroll": 42.12,
            "open_positions": {},
            "closed_positions": [
                {
                    "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                    "status": "SETTLED",
                    "settled_at_utc": (now_dt - timedelta(hours=3)).isoformat(),
                    "net_pnl_usd": 0.25,
                    "notional_usd": 10.0,
                    "fee_usd": 0.0,
                },
                {
                    "sleeve": "D1_LIVE_2LEG_MERGE",
                    "status": "SETTLED",
                    "resolution_seen_at_ts": now - 3 * 86400.0,
                    "net_pnl_usd": 1.75,
                    "notional_usd": 40.0,
                    "fee_usd": 0.0,
                },
                {
                    "sleeve": "SLEEVE_1_SUBHOURLY_15M",
                    "status": "SETTLED",
                    "settled_at_utc": (now_dt - timedelta(hours=2)).isoformat(),
                    "net_pnl_usd": -25.00,
                    "notional_usd": 25.0,
                    "fee_usd": 0.50,
                },
                {
                    "sleeve": "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
                    "status": "NOT_EXECUTED",
                    "settled_at_utc": (now_dt - timedelta(hours=1)).isoformat(),
                    "net_pnl_usd": 0.0,
                    "notional_usd": 0.0,
                },
            ],
        }
        emp = pdp.compute_empirical_realized_runrate(live_st, 49.12, now_ts=now)
        self.assertEqual(emp["window_24h"]["closed_records"], 1)
        self.assertAlmostEqual(emp["window_24h"]["realized_pnl_usd"], 0.25, places=4)
        self.assertFalse(emp["window_24h"]["clears_vm_hurdle"])
        self.assertEqual(emp["window_7d"]["closed_records"], 2)
        self.assertAlmostEqual(emp["window_7d"]["realized_pnl_usd"], 2.00, places=4)
        self.assertIn("day_30", emp["status_quo_linear_30d_baseline"])

        payload = pdp.build_live_projections(days=30, riskless_only=True, live_state_override=live_st)
        self.assertFalse(payload["row2_s2_twap_enabled"])
        self.assertIn("empirical_realized_runrate", payload)
        d30 = payload["day_by_day_schedule"][29]
        self.assertIn("vm_cost_cum_usd", d30)
        self.assertIn("p50_net_after_vm_usd", d30)

    def test_alpha124_resolve_gatling_starting_nav_uses_live_reconciled_nav(self) -> None:
        from src.polymarket_research import alpha_124_shadow_daemon as a124_mod

        d = a124_mod.Alpha124ShadowDaemon(single_scan=True)
        d.live_account_equity_usd = 49.12
        self.assertAlmostEqual(d._resolve_gatling_starting_nav_usd(), 49.12, places=2)

        d.live_account_equity_usd = 0.0
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            st_file = tdp / "state.json"
            mir_file = tdp / "mirror.json"
            opps_file = tdp / "opps.json"
            lh_file = tdp / "live_harvester_state.json"
            lh_file.write_text(
                json.dumps({"reconciled_nav_usd": 49.12, "live_bankroll": 42.12, "total_account_equity": 99.60}),
                encoding="utf-8",
            )
            with (
                mock.patch.object(a124_mod, "LIVE_POLYMARKET_DIR", tdp),
                mock.patch.object(a124_mod, "DATA_DIR", tdp),
                mock.patch.object(a124_mod, "STATE_FILE", st_file),
                mock.patch.object(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", mir_file),
                mock.patch.object(a124_mod, "OPPS_FILE", opps_file),
            ):
                d2 = a124_mod.Alpha124ShadowDaemon(single_scan=True)
                d2.live_account_equity_usd = 0.0
                d2.closed_positions = []
                d2.open_positions = {}
                resolved = d2._resolve_gatling_starting_nav_usd()
                self.assertAlmostEqual(resolved, 49.12, places=2)
                d2.write_state_files([])
                written = json.loads(st_file.read_text(encoding="utf-8"))
                gp = written.get("gatling_projection", {})
                self.assertAlmostEqual(gp.get("starting_nav_usd", 0.0), 49.12, places=2)

    def test_permission_gate_zero_violations_across_all_owned_files(self) -> None:
        from src.paa_os.permissions import PermissionGate

        gate = PermissionGate()
        owned = [
            "systemd/polymarket-live-harvester.service",
            "systemd/polymarket-recorder.service",
            "systemd/polymarket-alpha124-shadow.service",
            "scripts/polymarket_daily_projections.py",
            "src/polymarket_research/universal_arb_verifier.py",
            "src/polymarket_research/uma_nba_endgame_engine.py",
            "src/polymarket_research/macro_counting_ctf_engine.py",
            "src/polymarket_research/tradfi_sports_zero_fee_engine.py",
            "src/polymarket_research/riskless_expansion_v6_engines.py",
            "src/polymarket_research/riskless_protocol_v2_expansion.py",
            "src/polymarket_research/alpha_124_shadow_daemon.py",
            "tests/test_v62_shadow_engines_and_systemd.py",
        ]
        ok, reasons = gate.inspect_candidate_diff(owned, diff_text="")
        self.assertTrue(ok, f"PermissionGate rejected owned paths: {reasons}")
        for rel in ("tests/test_v62_shadow_engines_and_systemd.py",):
            ok_d, r_d = gate.inspect_candidate_diff([rel], diff_text=(ROOT / rel).read_text(encoding="utf-8"))
            self.assertTrue(ok_d, f"Forbidden pattern in {rel}: {r_d}")


if __name__ == "__main__":
    unittest.main()

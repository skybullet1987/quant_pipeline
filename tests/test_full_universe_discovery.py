"""
Comprehensive Unit & Integration Tests for Exhaustive Universe Discovery,
Incremental SQLite Registry & Two-Layer Surveillance (`tests/test_full_universe_discovery.py`).

Run locally on Windows via stdlib unittest (`D-010`):
  & "C:\\Program Files\\LibreOffice\\program\\python.exe" -m unittest tests/test_full_universe_discovery.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from src.polymarket_research.full_universe_discovery import (  # noqa: E402
    CLOB_BOOKS_MAX_BATCH_SIZE,
    FullUniverseRegistry,
    NormalizedBookSnapshot,
    PersistentJsonHttpClient,
    RateLimitBudget,
    SkipReason,
    TwoLayerSurveillanceScheduler,
    fetch_clob_books_batched,
    get_process_rss_mib,
    normalize_gamma_event,
    normalize_gamma_market,
)


def _hex_cid(idx: int) -> str:
    return "0x" + f"{idx:064x}"


def _make_raw_market(
    idx: int,
    *,
    question: Optional[str] = None,
    group_item_title: str = "",
    active: bool = True,
    closed: bool = False,
    archived: bool = False,
    enable_order_book: bool = True,
    accepting_orders: bool = True,
    neg_risk: bool = False,
    neg_risk_augmented: bool = False,
    neg_risk_other: bool = False,
    fees_enabled: bool = True,
    taker_base_fee: int = 1000,
    uma_status: str = "",
    end_date: str = "2027-06-01T00:00:00Z",
    vol_24h: float = 1200.0,
    liq_usd: float = 4500.0,
    market_id_override: Optional[str] = None,
    condition_id_override: Optional[str] = None,
    token_ids_override: Optional[List[str]] = None,
) -> Dict[str, Any]:
    mid = market_id_override if market_id_override is not None else str(900000 + idx)
    cid = condition_id_override if condition_id_override is not None else _hex_cid(idx)
    tids = token_ids_override if token_ids_override is not None else [f"tok_{idx}_yes", f"tok_{idx}_no"]
    return {
        "id": mid,
        "conditionId": cid,
        "questionID": "0x" + f"{idx + 50000:064x}",
        "slug": f"sample-market-{idx}",
        "question": question or f"Will sample proposition {idx} occur by June 2027?",
        "groupItemTitle": group_item_title,
        "outcomes": json.dumps(["Yes", "No"]),
        "clobTokenIds": json.dumps(tids),
        "outcomePrices": json.dumps(["0.48", "0.52"]),
        "active": active,
        "closed": closed,
        "archived": archived,
        "enableOrderBook": enable_order_book,
        "acceptingOrders": accepting_orders,
        "negRisk": neg_risk,
        "negRiskAugmented": neg_risk_augmented,
        "negRiskOther": neg_risk_other,
        "feesEnabled": fees_enabled,
        "takerBaseFee": taker_base_fee if fees_enabled else 0,
        "makerBaseFee": 0,
        "feeType": "politics_fees" if fees_enabled else "",
        "feeSchedule": (
            {"exponent": 1, "rate": 0.04, "takerOnly": True, "rebateRate": 0.25} if fees_enabled else {}
        ),
        "orderPriceMinTickSize": 0.01,
        "orderMinSize": 5,
        "umaResolutionStatus": uma_status,
        "resolutionSource": "Official Source",
        "description": f"Resolves Yes if proposition {idx} happens before cutoff.",
        "startDate": "2026-01-01T00:00:00Z",
        "endDate": end_date,
        "volume24hr": vol_24h,
        "volumeNum": vol_24h * 5.0,
        "liquidityNum": liq_usd,
    }


class TestFullUniverseDiscovery(unittest.TestCase):
    """Tests normalization, skip-code eligibility separation, SQLite diffing, and 2-layer surveillance."""

    FIXED_NOW_TS = 1794400000.0  # ~Nov 2026 epoch reference

    def test_normalization_binary_and_clob_overlay_reconciliation(self) -> None:
        raw_mkt = _make_raw_market(1, fees_enabled=True, taker_base_fee=1000)
        raw_ev = {
            "id": "ev_1",
            "slug": "us-senate-control-2026",
            "ticker": "ussenate",
            "title": "US Senate Control",
            "tags": [{"slug": "politics"}, {"slug": "elections"}],
            "active": True,
            "closed": False,
            "archived": False,
            "enableOrderBook": True,
            "negRisk": False,
            "volume24hr": 25000.0,
            "volume": 150000.0,
            "liquidity": 40000.0,
            "markets": [raw_mkt],
        }
        clob_ov = {
            _hex_cid(1): {
                "condition_id": _hex_cid(1),
                "minimum_tick_size": 0.001,
                "minimum_order_size": 15,
                "taker_base_fee": 1000,
                "maker_base_fee": 0,
                "accepting_orders": True,
                "enable_order_book": True,
                "is_50_50_outcome": True,
            }
        }
        nev = normalize_gamma_event(raw_ev, clob_by_condition=clob_ov, now_ts=self.FIXED_NOW_TS)
        self.assertEqual(nev.structure_kind, "SINGLE_BINARY")
        self.assertEqual(nev.category, "politics")
        self.assertEqual(nev.active_market_count, 1)
        self.assertEqual(nev.tradable_market_count, 1)

        nm = nev.markets[0]
        self.assertTrue(nm.discovery_complete)
        self.assertTrue(nm.execution_eligible)
        self.assertEqual(nm.skip_codes, ())
        self.assertTrue(nm.is_binary)
        self.assertFalse(nm.is_zero_fee)
        self.assertEqual(nm.fee_rate_bps, 1000.0)
        self.assertEqual(nm.maker_fee_bps, 0.0)
        self.assertAlmostEqual(nm.fee_schedule_rate, 0.04)
        self.assertAlmostEqual(nm.tick_size, 0.001)
        self.assertAlmostEqual(nm.min_order_size, 15.0)
        self.assertTrue(nm.is_50_50_outcome)
        self.assertEqual(nm.discovered_sources, ("gamma_events", "clob_sampling"))
        self.assertEqual(nm.yes_token_id, "tok_1_yes")
        self.assertEqual(nm.no_token_id, "tok_1_no")
        self.assertEqual(nm.instruments[0].complement_token_id, "tok_1_no")
        self.assertEqual(nm.instruments[1].complement_token_id, "tok_1_yes")

        # Verify zero-fee binary classification
        zf_mkt = normalize_gamma_market(
            _make_raw_market(2, fees_enabled=False, taker_base_fee=0),
            now_ts=self.FIXED_NOW_TS,
        )
        self.assertTrue(zf_mkt.is_zero_fee)
        self.assertEqual(zf_mkt.fee_rate_bps, 0.0)
        self.assertTrue(zf_mkt.execution_eligible)

    def test_discovery_completeness_vs_execution_eligibility_skip_codes(self) -> None:
        # Build an augmented NegRisk event + edge-case markets covering all mandatory skip codes
        m_named = _make_raw_market(10, group_item_title="Alice Smith", neg_risk=True, neg_risk_augmented=True)
        m_placeholder = _make_raw_market(
            11,
            question="Will Person A win the nomination?",
            group_item_title="Person A",
            neg_risk=True,
            neg_risk_augmented=True,
        )
        m_other = _make_raw_market(
            12,
            question="Will Other win the nomination?",
            group_item_title="Other",
            neg_risk=True,
            neg_risk_augmented=True,
            neg_risk_other=True,
        )
        m_disabled_ob = _make_raw_market(13, enable_order_book=False)
        m_not_accepting = _make_raw_market(14, accepting_orders=False)
        m_missing_toks = _make_raw_market(15, token_ids_override=[])
        m_bad_cid = _make_raw_market(16, condition_id_override="bad_hex")
        m_closed = _make_raw_market(17, closed=True, active=False)
        m_paused = _make_raw_market(18, active=False, closed=False)
        m_disputed = _make_raw_market(19, uma_status="disputed")
        m_kmia_d001 = _make_raw_market(20, market_id_override="6707503", uma_status="disputed")
        m_proposed_past = _make_raw_market(
            21,
            uma_status="proposed",
            end_date="2026-01-15T00:00:00Z",
        )

        ev = normalize_gamma_event(
            {
                "id": "ev_aug",
                "slug": "who-wins-nomination",
                "title": "Who wins the nomination?",
                "active": True,
                "closed": False,
                "archived": False,
                "enableOrderBook": True,
                "negRisk": True,
                "negRiskAugmented": True,
                "markets": [
                    m_named,
                    m_placeholder,
                    m_other,
                    m_disabled_ob,
                    m_not_accepting,
                    m_missing_toks,
                    m_bad_cid,
                    m_closed,
                    m_paused,
                    m_disputed,
                    m_kmia_d001,
                    m_proposed_past,
                ],
            },
            now_ts=self.FIXED_NOW_TS,
        )

        # 100% Discovery Completeness: all 12 child markets are retained!
        self.assertEqual(len(ev.markets), 12)
        self.assertTrue(all(m.discovery_complete for m in ev.markets))
        self.assertEqual(ev.structure_kind, "MULTI_OUTCOME_AUGMENTED_NEGRISK")
        self.assertTrue(ev.has_other_outcome)
        self.assertGreaterEqual(ev.placeholder_market_count, 1)

        by_id = {m.market_id: m for m in ev.markets}

        # Named standard outcome is execution eligible
        self.assertTrue(by_id["900010"].execution_eligible)

        # Placeholder outcome is retained in discovery, blocked from execution
        self.assertFalse(by_id["900011"].execution_eligible)
        self.assertIn(SkipReason.AUGMENTED_PLACEHOLDER_OUTCOME.value, by_id["900011"].skip_codes)

        # Augmented "Other" outcome carries explicit mutable-other caution code
        self.assertIn(SkipReason.AUGMENTED_OTHER_MUTABLE_OUTCOME.value, by_id["900012"].skip_codes)
        self.assertTrue(by_id["900012"].neg_risk_other)

        # Disabled orderbook, not accepting orders, missing tokens, bad conditionId, closed, paused
        self.assertFalse(by_id["900013"].execution_eligible)
        self.assertIn(SkipReason.ORDERBOOK_DISABLED.value, by_id["900013"].skip_codes)

        self.assertFalse(by_id["900014"].execution_eligible)
        self.assertIn(SkipReason.NOT_ACCEPTING_ORDERS.value, by_id["900014"].skip_codes)

        self.assertFalse(by_id["900015"].execution_eligible)
        self.assertIn(SkipReason.MISSING_TOKEN_IDS.value, by_id["900015"].skip_codes)

        self.assertFalse(by_id["900016"].execution_eligible)
        self.assertIn(SkipReason.MISSING_CONDITION_ID.value, by_id["900016"].skip_codes)

        self.assertFalse(by_id["900017"].execution_eligible)
        self.assertIn(SkipReason.CLOSED_OR_ARCHIVED.value, by_id["900017"].skip_codes)

        self.assertFalse(by_id["900018"].execution_eligible)
        self.assertIn(SkipReason.INACTIVE_OR_PAUSED.value, by_id["900018"].skip_codes)

        # Disputed & D-001 KMIA locked markets MUST be blocked from execution
        self.assertFalse(by_id["900019"].execution_eligible)
        self.assertIn(SkipReason.UMA_DISPUTED_FROZEN.value, by_id["900019"].skip_codes)

        self.assertTrue(by_id["6707503"].is_kmia_frozen_d001)
        self.assertFalse(by_id["6707503"].execution_eligible)
        self.assertIn(SkipReason.KMIA_D001_PROTECTED_LOCK.value, by_id["6707503"].skip_codes)
        self.assertIn(SkipReason.UMA_DISPUTED_FROZEN.value, by_id["6707503"].skip_codes)

        # UMA proposed & past end date unresolved carries explicit settlement-stage codes
        self.assertIn(SkipReason.UMA_PROPOSED_SETTLEMENT_STAGE.value, by_id["900021"].skip_codes)
        self.assertIn(SkipReason.PAST_END_DATE_UNRESOLVED.value, by_id["900021"].skip_codes)

    def test_sqlite_registry_persistence_and_incremental_diff_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rss_before = get_process_rss_mib()
            db_path = Path(tmpdir) / "registry.sqlite3"
            snap_path = Path(tmpdir) / "snapshot.json"
            reg = FullUniverseRegistry(db_path=db_path, snapshot_path=snap_path)
            try:
                ev1 = {
                    "id": "ev_100",
                    "slug": "btc-above-100k",
                    "title": "Bitcoin above $100k?",
                    "tags": ["crypto", "bitcoin"],
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "enableOrderBook": True,
                    "markets": [
                        _make_raw_market(100, fees_enabled=False, taker_base_fee=0),
                        _make_raw_market(101, fees_enabled=True, taker_base_fee=1000),
                    ],
                }
                clob_only = [
                    {
                        "condition_id": _hex_cid(999),
                        "question_id": "999999",
                        "market_slug": "clob-standalone-market",
                        "question": "Standalone CLOB market?",
                        "active": True,
                        "closed": False,
                        "archived": False,
                        "accepting_orders": True,
                        "enable_order_book": True,
                        "taker_base_fee": 0,
                        "maker_base_fee": 0,
                        "minimum_tick_size": 0.01,
                        "minimum_order_size": 5,
                        "tokens": [
                            {"token_id": "tok_999_yes", "outcome": "Yes"},
                            {"token_id": "tok_999_no", "outcome": "No"},
                        ],
                    }
                ]

                # Pass 1: Initial populate
                d1 = reg.ingest_events([ev1], clob_markets=clob_only, now_ts=self.FIXED_NOW_TS)
                self.assertEqual(d1.added_events, 2)
                self.assertEqual(d1.added_markets, 3)
                self.assertEqual(d1.unchanged_markets, 0)
                self.assertEqual(d1.newly_closed_or_missing_markets, 0)

                # Pass 2: Identical re-ingest -> 100% unchanged
                d2 = reg.ingest_events([ev1], clob_markets=clob_only, now_ts=self.FIXED_NOW_TS + 10.0)
                self.assertEqual(d2.added_markets, 0)
                self.assertEqual(d2.updated_markets, 0)
                self.assertEqual(d2.unchanged_markets, 3)
                self.assertEqual(d2.newly_closed_or_missing_markets, 0)

                # Pass 3: Mutate market 100, drop market 101, add market 102 (omit clob_only -> closed)
                ev1_mut = {
                    **ev1,
                    "markets": [
                        _make_raw_market(100, fees_enabled=False, taker_base_fee=0, uma_status="proposed"),
                        _make_raw_market(102, fees_enabled=True, taker_base_fee=1000),
                    ],
                }
                d3 = reg.ingest_events([ev1_mut], clob_markets=(), now_ts=self.FIXED_NOW_TS + 20.0)
                self.assertEqual(d3.added_markets, 1)
                self.assertEqual(d3.updated_markets, 1)
                self.assertEqual(d3.newly_closed_or_missing_markets, 2)  # mkt 101 + clob 999999

                # Verify dropped market 101 is STILL retained in SQLite with CLOSED_OR_ARCHIVED
                dropped = reg.get_market("900101")
                self.assertIsNotNone(dropped)
                assert dropped is not None
                self.assertTrue(dropped.closed)
                self.assertFalse(dropped.execution_eligible)
                self.assertIn(SkipReason.CLOSED_OR_ARCHIVED.value, dropped.skip_codes)

                # Verify condition lookup & zero-fee iterator
                m_by_cid = reg.get_market_by_condition(_hex_cid(100))
                self.assertIsNotNone(m_by_cid)
                assert m_by_cid is not None
                self.assertEqual(m_by_cid.uma_resolution_status, "proposed")

                zf_active = list(reg.iter_markets(active_only=True, zero_fee_only=True))
                self.assertEqual([m.market_id for m in zf_active], ["900100"])

                summary = reg.count_summary()
                self.assertEqual(summary["markets_total"], 4)
                self.assertEqual(summary["markets_active"], 2)
                rss_now = get_process_rss_mib()
                self.assertGreater(rss_now, 1.0)
                self.assertLess(rss_now - rss_before, 40.0)
                self.assertLess(rss_now, 180.0)
            finally:
                reg.close()

    def test_mocked_full_keyset_sweep_beyond_offset_2100_and_host_allowlist(self) -> None:
        # Simulate 3 Gamma `/events/keyset` pages using `after_cursor` + CLOB `/sampling-markets` -> `LTE=`
        pages = {
            "": {
                "events": [
                    {
                        "id": "ev_p1",
                        "slug": "weather-nyc-temp",
                        "title": "Highest temperature in NYC?",
                        "tags": ["weather"],
                        "active": True,
                        "closed": False,
                        "enableOrderBook": True,
                        "negRisk": True,
                        "volume24hr": 8000.0,
                        "markets": [
                            _make_raw_market(201, neg_risk=True, fees_enabled=False, taker_base_fee=0),
                            _make_raw_market(202, neg_risk=True, fees_enabled=False, taker_base_fee=0),
                        ],
                    }
                ],
                "next_cursor": "CUR_PAGE_2",
            },
            "CUR_PAGE_2": {
                "events": [
                    {
                        "id": "ev_p2",
                        "slug": "nba-lakers-vs-celtics",
                        "title": "Lakers vs Celtics",
                        "tags": ["sports", "nba"],
                        "active": True,
                        "closed": False,
                        "enableOrderBook": True,
                        "negRisk": False,
                        "volume24hr": 50000.0,
                        "markets": [_make_raw_market(203, fees_enabled=True, taker_base_fee=1000)],
                    }
                ],
                "next_cursor": "CUR_PAGE_3",
            },
            "CUR_PAGE_3": {
                "events": [
                    {
                        "id": "ev_p3",
                        "slug": "quiet-tail-market",
                        "title": "Will obscure bill pass?",
                        "tags": ["politics"],
                        "active": True,
                        "closed": False,
                        "enableOrderBook": True,
                        "negRisk": False,
                        "volume24hr": 0.0,
                        "markets": [_make_raw_market(204, vol_24h=0.0, liq_usd=10.0, fees_enabled=True)],
                    }
                ],
                "next_cursor": None,
            },
        }

        def _fake_http(method: str, url: str, body: Optional[bytes]) -> Tuple[int, Any]:
            parsed = urllib.parse.urlsplit(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if parsed.path == "/sampling-markets":
                cur = qs.get("next_cursor", [""])[0]
                if not cur:
                    return 200, {
                        "data": [
                            {
                                "condition_id": _hex_cid(203),
                                "question_id": "900203",
                                "market_slug": "sample-market-203",
                                "active": True,
                                "closed": False,
                                "accepting_orders": True,
                                "enable_order_book": True,
                                "taker_base_fee": 1000,
                                "maker_base_fee": 0,
                                "minimum_order_size": 5,
                                "minimum_tick_size": 0.01,
                            }
                        ],
                        "next_cursor": "LTE=",
                    }
                return 200, {"data": [], "next_cursor": "LTE="}
            if parsed.path == "/events/keyset":
                ac = qs.get("after_cursor", [""])[0]
                return 200, pages[ac]
            if parsed.path == "/events":
                off = int(qs.get("offset", ["0"])[0])
                if off >= 2500:
                    return 422, {"type": "validation error", "error": "offset too large, use /events/keyset"}
                return 200, [{"id": "sample", "deploying": True}]
            return 404, {}

        client = PersistentJsonHttpClient(requester_override=_fake_http)
        # Verify host allowlist blocks any external or private endpoint
        with self.assertRaises(ValueError):
            client.request_json("GET", "https://example.com/private")

        with tempfile.TemporaryDirectory() as tmpdir:
            reg = FullUniverseRegistry(
                db_path=Path(tmpdir) / "reg.sqlite3",
                snapshot_path=Path(tmpdir) / "cov.json",
            )
            try:
                snap = reg.sweep_full_universe(http_client=client)
                self.assertEqual(snap["diff_stats"]["gamma_pages_fetched"], 3)
                self.assertEqual(snap["universe_totals"]["active_unclosed_events"], 3)
                self.assertEqual(snap["universe_totals"]["active_unclosed_markets"], 4)
                self.assertEqual(snap["universe_totals"]["tradable_outcome_token_ids"], 8)
                self.assertEqual(snap["boundary_and_pagination_probes"]["gamma_offset_3000_http_status"], 422)
                self.assertTrue((Path(tmpdir) / "cov.json").exists())
            finally:
                reg.close()
                client.close()

    def test_two_layer_surveillance_scheduler_batching_cursor_wrap_and_depth_skips(self) -> None:
        # 12 tradable markets (24 tradable tokens) + 1 disabled-orderbook market (2 non-tradable tokens)
        raw_mkts = [
            _make_raw_market(300 + i, fees_enabled=(i >= 2), vol_24h=float(1000 - i * 20))
            for i in range(12)
        ]
        raw_mkts.append(_make_raw_market(399, enable_order_book=False))
        ev = {
            "id": "ev_surv",
            "slug": "surveillance-test-suite",
            "title": "Surveillance Test Suite",
            "active": True,
            "closed": False,
            "enableOrderBook": True,
            "markets": raw_mkts,
        }

        batches_observed: List[int] = []
        empty_tokens = {"tok_305_yes", "tok_305_no"}
        one_sided_tokens = {"tok_306_yes"}

        def _fake_books_http(method: str, url: str, body: Optional[bytes]) -> Tuple[int, Any]:
            self.assertEqual(method, "POST")
            self.assertTrue(url.endswith("/books"))
            assert body is not None
            items = json.loads(body.decode("utf-8"))
            self.assertLessEqual(len(items), CLOB_BOOKS_MAX_BATCH_SIZE)
            batches_observed.append(len(items))
            resp: List[Dict[str, Any]] = []
            for it in items:
                tid = it["token_id"]
                if tid in empty_tokens:
                    resp.append({"asset_id": tid, "bids": [], "asks": [], "tick_size": "0.01", "min_order_size": "5"})
                elif tid in one_sided_tokens:
                    resp.append(
                        {
                            "asset_id": tid,
                            "bids": [{"price": "0.44", "size": "25"}],
                            "asks": [],
                            "tick_size": "0.01",
                            "min_order_size": "5",
                        }
                    )
                else:
                    resp.append(
                        {
                            "asset_id": tid,
                            "bids": [{"price": "0.47", "size": "50"}, {"price": "0.46", "size": "100"}],
                            "asks": [{"price": "0.51", "size": "40"}, {"price": "0.52", "size": "80"}],
                            "tick_size": "0.01",
                            "min_order_size": "5",
                        }
                    )
            return 200, resp

        client = PersistentJsonHttpClient(requester_override=_fake_books_http)
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = FullUniverseRegistry(
                db_path=Path(tmpdir) / "surv.sqlite3",
                snapshot_path=Path(tmpdir) / "surv_cov.json",
            )
            try:
                reg.ingest_events([ev], now_ts=self.FIXED_NOW_TS)
                sched = TwoLayerSurveillanceScheduler(
                    reg,
                    layer_b_tokens_per_cycle=4,
                    layer_a_tokens_per_cycle=7,
                    clob_batch_size=5,
                    hot_freshness_sla_sec=30.0,
                    sweep_freshness_sla_sec=600.0,
                )
                # Pin a low-volume token into Layer B priority
                sched.register_priority_tokens(["tok_311_yes"], reason="dormant_near_arb")

                # Run 4 cycles -> Layer A (7 tokens/cycle) + Layer B (4 tokens/cycle) MUST cover 100% of 24 tradable tokens and wrap around!
                for step in range(4):
                    res = sched.execute_poll_cycle(
                        http_client=client,
                        now_ts=self.FIXED_NOW_TS + step * 20.0,
                    )
                    if step == 0:
                        self.assertIn("tok_311_yes", sched._hot_books_lru)

                # Verify batching cap (`<= 5` per configured `clob_batch_size=5`)
                self.assertTrue(all(sz <= 5 for sz in batches_observed))

                # Verify 100% of tradable tokens (24/24) were polled and disabled tokens (`tok_399_*`) were NEVER polled
                staleness = sched.get_staleness_report(now_ts=self.FIXED_NOW_TS + 70.0)
                self.assertEqual(staleness["tradable_tokens_total"], 24)
                self.assertEqual(staleness["never_polled_tokens"], 0)
                self.assertGreaterEqual(staleness["layer_a_full_wraps"], 1)

                inst_disabled = reg.get_instrument("tok_399_yes")
                assert inst_disabled is not None
                self.assertEqual(inst_disabled.last_book_ts, 0.0)

                # Verify ZERO_RESTING_DEPTH & ONE_SIDED_BOOK skip codes refined onto markets & instruments
                m_empty = reg.get_market("900305")
                assert m_empty is not None
                self.assertIn(SkipReason.ZERO_RESTING_DEPTH.value, m_empty.skip_codes)

                m_one = reg.get_market("900306")
                assert m_one is not None
                self.assertIn(SkipReason.ONE_SIDED_BOOK.value, m_one.skip_codes)

                # When liquidity returns on `tok_305_*`, `ZERO_RESTING_DEPTH` clears automatically
                empty_tokens.clear()
                snaps_refill, _ = fetch_clob_books_batched(
                    ["tok_305_yes", "tok_305_no"],
                    http_client=client,
                    batch_size=5,
                    now_ts=self.FIXED_NOW_TS + 90.0,
                )
                reg.update_books_from_snapshots(snaps_refill, now_ts=self.FIXED_NOW_TS + 90.0)
                m_refilled = reg.get_market("900305")
                assert m_refilled is not None
                self.assertNotIn(SkipReason.ZERO_RESTING_DEPTH.value, m_refilled.skip_codes)

                # Verify fresh book export
                exported = sched.export_fresh_clob_books_dict(now_ts=self.FIXED_NOW_TS + 70.0)
                self.assertGreaterEqual(len(exported), 20)
                sample_bk = NormalizedBookSnapshot.from_clob_dict(next(iter(exported.values())))
                self.assertGreater(sample_bk.best_bid, 0.0)
            finally:
                reg.close()
                client.close()

    def test_rate_limit_budget_sliding_window_throttling(self) -> None:
        clock = [100.0]
        sleeps: List[float] = []

        def _now() -> float:
            return clock[0]

        def _sleep(dt: float) -> None:
            sleeps.append(dt)
            clock[0] += dt

        budget = RateLimitBudget(max_requests_per_window=3, window_sec=2.0, min_interval_sec=0.1)
        for _ in range(4):
            budget.acquire(now_fn=_now, sleep_fn=_sleep)

        self.assertEqual(budget.total_requests, 4)
        # 2nd & 3rd calls sleep 0.1s each (`t=100.2`), 4th call waits until `t > 102.0`
        self.assertGreaterEqual(clock[0], 102.0)
        self.assertGreater(budget.throttled_sleep_sec_total, 1.8)


class TestWave2Alpha124DiscoveryUpgrades(unittest.TestCase):
    """Wave 2 (`/boost` Track 1) unit tests for `Alpha124ShadowDaemon` discovery & surveillance."""

    def test_wave2_01_fetch_books_batch_400_chunking_and_lossless_50_subchunk_fallback(self) -> None:
        import asyncio
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod

        post_batch_sizes: List[int] = []
        single_book_hits: List[str] = []
        poisoned_tok = "tok_bad_65"

        class _FakeResp:
            def __init__(self, status: int, body: bytes) -> None:
                self.status = status
                self._body = body

            async def __aenter__(self) -> "_FakeResp":
                return self

            async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
                return False

            async def read(self) -> bytes:
                return self._body

        class _FakeSess:
            def post(self, url: str, **kwargs: Any) -> _FakeResp:
                raw_items = kwargs.get("json")
                if raw_items is None and kwargs.get("data") is not None:
                    raw_items = json.loads(kwargs["data"])
                tids = [str(it["token_id"]) for it in (raw_items or [])]
                post_batch_sizes.append(len(tids))
                if poisoned_tok in tids:
                    return _FakeResp(400, b'{"error":"invalid token"}')
                rows = [
                    {
                        "asset_id": tid,
                        "minimum_tick_size": "0.01",
                        "bids": [{"price": "0.48", "size": "25"}],
                        "asks": [{"price": "0.51", "size": "25"}],
                    }
                    for tid in tids
                ]
                return _FakeResp(200, json.dumps(rows).encode("utf-8"))

        async def _run() -> None:
            d = a124_mod.Alpha124ShadowDaemon(single_scan=True, riskless_bridge_only=True)
            fake_sess = _FakeSess()

            async def _get_sess() -> Any:
                return fake_sess

            async def _fake_single_book(url: str, timeout: float = 2.0) -> Any:
                tid = url.split("token_id=")[-1]
                single_book_hits.append(tid)
                if tid == poisoned_tok:
                    return None
                return {
                    "asset_id": tid,
                    "minimum_tick_size": "0.01",
                    "bids": [{"price": "0.47", "size": "15"}],
                    "asks": [{"price": "0.52", "size": "15"}],
                }

            d.get_session = _get_sess  # type: ignore[method-assign]
            # Bind `fetch_json` on class proxy via monkeypatch only inside fallback without triggering `"fetch_json" in d.__dict__`
            orig_cls_fj = a124_mod.Alpha124ShadowDaemon.fetch_json
            a124_mod.Alpha124ShadowDaemon.fetch_json = staticmethod(_fake_single_book)  # type: ignore[assignment]
            try:
                # Part A: 900 healthy tokens -> 3 batches of [400, 400, 100] (not 18 batches of 50)
                healthy_900 = [f"tok_ok_{i}" for i in range(900)]
                res_900 = await d.fetch_books_batch(healthy_900, timeout=2.0)
                self.assertEqual(len(res_900), 900)
                self.assertEqual(sorted(post_batch_sizes), [100, 400, 400])
                self.assertEqual(len(single_book_hits), 0)

                # Part B: 120 tokens with 1 poisoned token at index 65 ->
                # 1x 120-token POST fails -> retries 3 sub-chunks [50, 50, 20] ->
                # sub-chunks 0 and 2 succeed via POST /books (70 tokens), sub-chunk 1 (50 tokens)
                # falls back losslessly to `/book?token_id=...` recovering all 49 valid tokens (119/119 total!)
                post_batch_sizes.clear()
                mixed_120 = [poisoned_tok if i == 65 else f"tok_m_{i}" for i in range(120)]
                res_120 = await d.fetch_books_batch(mixed_120, timeout=2.0)
                self.assertEqual(len(res_120), 119)
                self.assertNotIn(poisoned_tok, res_120)
                self.assertIn(120, post_batch_sizes)
                self.assertEqual(sorted(post_batch_sizes), [20, 50, 50, 120])
                self.assertEqual(len(single_book_hits), 50)
            finally:
                a124_mod.Alpha124ShadowDaemon.fetch_json = orig_cls_fj  # type: ignore[assignment]
                st_ex = d.__dict__.pop("_state_io_executor", None)
                if st_ex is not None:
                    st_ex.shutdown(wait=True)

        asyncio.run(_run())

    def test_wave2_02_discover_uma_proposed_closes_offset_100_hole_and_ingests_sqlite_registry(self) -> None:
        import asyncio
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod

        now_ts = 1_794_420_000.0
        requested_urls: List[str] = []

        def _mk_uma_mkt(mid: str, qid_byte: str) -> Dict[str, Any]:
            return {
                "id": mid,
                "conditionId": "0x" + (qid_byte * 64),
                "questionID": "0x" + (qid_byte * 64),
                "slug": f"cs2-team-a-vs-team-b-{mid}",
                "question": f"CS2: Team A vs Team B ({mid}) winner?",
                "description": "Resolves per official HLTV match page https://hltv.org.",
                "outcomes": '["Team A", "Team B"]',
                "clobTokenIds": f'["tok_{mid}_a", "tok_{mid}_b"]',
                "outcomePrices": '["0.992", "0.008"]',
                "acceptingOrders": True,
                "enableOrderBook": True,
                "closed": False,
                "archived": False,
                "umaResolutionStatus": "proposed",
                "resolvedBy": "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7",
                "endDate": "2026-11-11T12:00:00Z",
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "market_registry.sqlite3"
            reg = FullUniverseRegistry(db_path=db_path, snapshot_path=Path(tmpdir) / "snap.json")
            try:
                reg.ingest_events(
                    [
                        {
                            "id": "77001",
                            "slug": "cs2-sqlite-proposed",
                            "title": "CS2 SQLite Proposed",
                            "active": True,
                            "closed": False,
                            "markets": [
                                _mk_uma_mkt("880701", "a"),
                                {
                                    **_mk_uma_mkt("6707503", "b"),
                                    "slug": "kmia-frozen-d001",
                                },
                                {
                                    **_mk_uma_mkt("880702", "c"),
                                    "question": "Will celebrity tweet a meme tonight?",
                                    "description": "Subjective tweet mention market.",
                                },
                            ],
                        }
                    ],
                    now_ts=now_ts,
                )
            finally:
                reg.close()

            async def _run() -> None:
                d = a124_mod.Alpha124ShadowDaemon(single_scan=True, riskless_bridge_only=True)
                d._universe_registry_db_path = str(db_path)

                async def _mock_fetch_json(url: str, timeout: float = 5.0) -> Any:
                    requested_urls.append(url)
                    if "/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=100&offset=100" in url:
                        return [_mk_uma_mkt("880150", "d")]
                    if "/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=100&offset=700" in url:
                        return [_mk_uma_mkt("880750", "e")]
                    return []

                d.fetch_json = _mock_fetch_json  # type: ignore[method-assign]
                try:
                    await d.discover_uma_proposed_markets(now_ts)
                    # Verify no clamped `limit=200` requests remain and `offset=0..800` by 100 is queried
                    self.assertFalse(any("limit=200" in u for u in requested_urls))
                    for off in range(0, 900, 100):
                        self.assertTrue(
                            any(f"/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=100&offset={off}" in u for u in requested_urls),
                            f"Missing /markets offset={off}",
                        )
                    # Market at offset=100 (previously blind!), offset=700, and SQLite registry `880701` are all discovered
                    self.assertIn("880150", d.uma_proposed_markets)
                    self.assertIn("880750", d.uma_proposed_markets)
                    self.assertIn("880701", d.uma_proposed_markets)
                    # Verify BUG-W2-DISC-2 fix: registry UMA market carries indicative `bestBid`/`bestAsk` (`0.992`) for Cycle-1 `tradeable_score`
                    self.assertAlmostEqual(float(d.uma_proposed_markets["880701"].get("bestBid") or 0.0), 0.992, places=4)
                    self.assertAlmostEqual(float(d.uma_proposed_markets["880701"].get("bestAsk") or 0.0), 0.992, places=4)
                    # Subjective market & D-001 frozen KMIA 6707503 are strictly excluded
                    self.assertNotIn("880702", d.uma_proposed_markets)
                    self.assertNotIn("6707503", d.uma_proposed_markets)
                finally:
                    st_ex = d.__dict__.pop("_state_io_executor", None)
                    if st_ex is not None:
                        st_ex.shutdown(wait=True)

            asyncio.run(_run())

    def test_wave2_03_extract_zerofee_general_binaries_1200_cap_quiet_liq_and_fee_binaries(self) -> None:
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod

        now_ts = 1_794_420_000.0
        end_iso = "2026-11-20T12:00:00Z"
        mkts: List[Dict[str, Any]] = []
        # 420 zero-fee binaries including `< $500` quiet resting-depth arbs (`liquidityNum = 35.0`)
        for i in range(420):
            cid_hex = f"0x{i + 1:064x}"
            mkts.append(
                {
                    "id": f"910{i:04d}",
                    "conditionId": cid_hex,
                    "question": f"Zero fee binary #{i}",
                    "clobTokenIds": f'["zf_y_{i}", "zf_n_{i}"]',
                    "outcomes": '["Yes", "No"]',
                    "feesEnabled": False,
                    "enableOrderBook": True,
                    "active": True,
                    "closed": False,
                    "liquidityNum": 35.0 if i < 50 else 800.0,
                    "volume24hr": 10.0 if i < 50 else 600.0,
                    "endDate": end_iso,
                }
            )
        # Fee-enabled binary #1: wide interior spread (`bestBid=0.45, bestAsk=0.52` -> `ask_sum = 1.07 > 1.005`) -> EXCLUDED
        mkts.append(
            {
                "id": "920001",
                "conditionId": f"0x{5001:064x}",
                "question": "Wide interior fee binary",
                "clobTokenIds": '["fb_wide_y", "fb_wide_n"]',
                "outcomePrices": '["0.485", "0.515"]',
                "bestBid": 0.45,
                "bestAsk": 0.52,
                "feesEnabled": True,
                "takerBaseFee": 200,
                "enableOrderBook": True,
                "active": True,
                "closed": False,
                "endDate": end_iso,
            }
        )
        # Fee-enabled binary #2: tight `<= 1.005` ask sum (`bestBid=0.498, bestAsk=0.501` -> `ask_sum = 1.003 <= 1.005`) -> INCLUDED with exact fee_rate!
        mkts.append(
            {
                "id": "920002",
                "conditionId": f"0x{5002:064x}",
                "question": "Tight spread fee binary",
                "clobTokenIds": '["fb_tight_y", "fb_tight_n"]',
                "outcomePrices": '["0.4995", "0.5005"]',
                "bestBid": 0.498,
                "bestAsk": 0.501,
                "feesEnabled": True,
                "takerBaseFee": 150,
                "enableOrderBook": True,
                "active": True,
                "closed": False,
                "endDate": end_iso,
            }
        )
        # Fee-enabled binary #3: tail price `p >= 0.94` (`outcomePrices=["0.965","0.035"]`, `feeSchedule` parabolic) -> INCLUDED with exact fee_rate & exponent!
        mkts.append(
            {
                "id": "920003",
                "conditionId": f"0x{5003:064x}",
                "question": "Tail fee collapse binary",
                "clobTokenIds": '["fb_tail_y", "fb_tail_n"]',
                "outcomePrices": '["0.965", "0.035"]',
                "bestBid": 0.955,
                "bestAsk": 0.975,
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.072, "exponent": 2.0},
                "enableOrderBook": True,
                "active": True,
                "closed": False,
                "endDate": end_iso,
            }
        )
        # D-001 frozen KMIA `6707502` -> EXCLUDED even if zero-fee!
        mkts.append(
            {
                "id": "6707502",
                "conditionId": f"0x{5004:064x}",
                "question": "KMIA disputed",
                "clobTokenIds": '["kmia_y", "kmia_n"]',
                "feesEnabled": False,
                "enableOrderBook": True,
                "active": True,
                "closed": False,
                "endDate": end_iso,
            }
        )

        extracted = a124_mod.Alpha124ShadowDaemon.extract_zerofee_general_binaries(
            [{"id": "ev_mix", "slug": "macro-mix", "closed": False, "markets": mkts}],
            now_ts=now_ts,
        )
        by_mid = {r["market_id"]: r for r in extracted}
        # Default `max_markets=1200` retains all 420 zero-fee + 2 qualified fee binaries = 422 (> old 340 cap!)
        self.assertEqual(len(extracted), 422)
        # Quiet `$35` liquidity binary (`9100000`) is retained
        self.assertIn("9100000", by_mid)
        self.assertEqual(by_mid["9100000"]["fee_rate"], 0.0)
        # Wide interior fee binary excluded; tight & tail fee binaries retained with exact `fee_rate` > 0!
        self.assertNotIn("920001", by_mid)
        self.assertIn("920002", by_mid)
        self.assertAlmostEqual(by_mid["920002"]["fee_rate"], 0.015, places=6)
        self.assertTrue(by_mid["920002"]["fees_enabled"])
        self.assertIn("920003", by_mid)
        self.assertAlmostEqual(by_mid["920003"]["fee_rate"], 0.072, places=6)
        self.assertAlmostEqual(by_mid["920003"]["fee_exponent"], 2.0, places=4)
        # D-001 frozen KMIA strictly excluded
        self.assertNotIn("6707502", by_mid)

    def test_wave2_04_ws_5x250_shards_dormant_pinning_and_180_negrisk_convert_cap(self) -> None:
        import inspect
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod

        now_ts = 1_794_420_000.0
        # Verify `negrisk_convert_slates` `[:180]` cap and `_run_clob_d1_ws_loop` `range(5)` in source
        disc_src = inspect.getsource(a124_mod.Alpha124ShadowDaemon.discover_all_markets)
        self.assertIn(")[:180]", disc_src)
        self.assertIn("max_markets=1200", disc_src)
        ws_loop_src = inspect.getsource(a124_mod.Alpha124ShadowDaemon._run_clob_d1_ws_loop)
        self.assertIn("range(5)", ws_loop_src)

        with tempfile.TemporaryDirectory() as tmpdir:
            dorm_file = Path(tmpdir) / "dormant_opportunities.json"
            entries = [
                {
                    "candidate_id": f"FAM_C_{i}",
                    "family_code": "C" if i < 20 else "A",
                    "market_ids": [f"950{i:04d}"],
                    "instrument_ids": [f"dorm_tok_{i}_a", f"dorm_tok_{i}_b"],
                    "gap_to_breakeven_bps": float(i % 45),
                }
                for i in range(650)
            ]
            # Add >50 bps dormant entry (must not be pinned) and D-001 KMIA 6707502 entry (must be blocked)
            entries.append(
                {
                    "candidate_id": "FAM_A_WIDE",
                    "family_code": "A",
                    "market_ids": ["999001"],
                    "instrument_ids": ["dorm_wide_85bps"],
                    "gap_to_breakeven_bps": 85.0,
                }
            )
            entries.append(
                {
                    "candidate_id": "FAM_KMIA_FROZEN",
                    "family_code": "A",
                    "market_ids": ["6707502"],
                    "instrument_ids": ["kmia_tok_forbidden"],
                    "gap_to_breakeven_bps": 0.0,
                }
            )
            dorm_file.write_text(json.dumps({"entries": entries}), encoding="utf-8")

            d = a124_mod.Alpha124ShadowDaemon(single_scan=True, riskless_bridge_only=True)
            try:
                d._dormant_opps_path = str(dorm_file)
                shards = d._partition_ws_shards(now_ts)
                self.assertEqual(len(shards), 5)
                for sh in shards:
                    self.assertEqual(len(sh), 250)
                flat = [t for sh in shards for t in sh]
                self.assertEqual(len(flat), 1250)
                self.assertEqual(len(set(flat)), 1250)
                self.assertIn("dorm_tok_0_a", flat)
                self.assertIn("dorm_tok_0_a", d._ws_nr_priority_tokens)
                self.assertNotIn("dorm_wide_85bps", flat)
                self.assertNotIn("kmia_tok_forbidden", flat)
            finally:
                st_ex = d.__dict__.pop("_state_io_executor", None)
                if st_ex is not None:
                    st_ex.shutdown(wait=True)

    def test_wave2_05_zerofee1_15bps_unclamped_in_ws_and_emit_live_two_leg_box(self) -> None:
        import inspect
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod

        ws_nr_src = inspect.getsource(a124_mod.Alpha124ShadowDaemon._scan_ws_reactive_negrisk_arbs)
        emit_src = inspect.getsource(a124_mod.Alpha124ShadowDaemon.emit_live_two_leg_box_candidate)
        self.assertIn('max(0.0010, float(_rb_ws.get("zerofee1_min_net_edge_bps", 15.0)', ws_nr_src)
        self.assertNotIn('max(0.0025, float(_rb_ws.get("zerofee1_min_net_edge_bps"', ws_nr_src)
        self.assertIn('max(0.0010, float(_rb_c1_gov.get("zerofee1_min_net_edge_bps", 15.0)', emit_src)
        self.assertIn("min(0.9990 if _zf_c1_merge_emit else max_cap", emit_src)
        self.assertNotIn("min(0.9965 if _zf_c1_merge_emit", emit_src)


if __name__ == "__main__":
    unittest.main()

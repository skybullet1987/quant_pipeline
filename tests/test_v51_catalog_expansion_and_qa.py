"""
DOMINUS v5.1 — Riskless Catalog Expansion, Safety Guards, & Full-Repo QA Suite.

Validates:
  1. `P0a`: Trillion (`$1.8T` / `trillion`) valuation strike parsing, `<STRIKE>` stem parity,
     and strict non-backtracking on unknown suffixes (`$1.8Q`, `$1.8X`, `1.8.5`).
  2. `P0b`: Conditional NegRisk IPO/M&A/deal slates missing a `"No IPO / None / Other"` catch-all
     are blocked for `ALL_YES` / `is_closed_convert_safe` while keeping 2-leg `NO_i + NO_j` boxes open.
  3. `P1a`: Objective UMA expansion (`OFFICIAL_LEAGUE_POST_DEADLINE`, `OFFICIAL_LEAGUE_ELIMINATED_NO`,
     and official `.gov`/sports oracle domains) while strictly vetoing pop-culture, pre-2028 elections,
     and subjective geopolitics.
  4. `P1b`: Yearless `"December 31"` and cross-year `"December 28–January 3"` rollover in `CAL1`
     deadline ladders even when child `endDate` is `2027-01-01T04:59:00Z` or shared `2027-04-01Z`.
  5. `P1c`: Volume-first `0%`-fee general binary discovery (`max_markets=340`) & expanded WS caps.
  6. `P2`: Tail-leg pre-filter (`s >= 8.0 and p * s >= 1.05`), Windows-safe `load_state()` immediate
     file-handle release during migration `save_state()`, KMIA-haircutted `UNLEASHED_LAUNCH` tier &
     `15%` concentration cap (`reconciled_nav_usd`), `safe_zoneinfo` tzdata-free fallback, and
     `ResilientReadOnlyTransport.__aexit__` sync/async session close safety.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts.benchmark_polymarket_13stage_latency import _install_minimal_offline_stubs_if_needed

_install_minimal_offline_stubs_if_needed()

from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon
from src.polymarket_research.cross_venue_connectors import ResilientReadOnlyTransport
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.riskless_frontier_v3_engine import (
    _canon_clause_stem,
    _parse_group_label_date_ts,
    _parse_scalar_strike,
    detect_cal1_monotonic_boxes,
    parse_cal1_monotonic_ladder_event,
)
from src.polymarket_research.riskless_protocol_v2_expansion import (
    is_conditional_negrisk_missing_catchall,
    safe_zoneinfo,
    verify_v2_negrisk_other_partition,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    detect_negrisk_no_pair_boxes,
    parse_negrisk_convert_event,
)
from src.polymarket_research.uma_nba_endgame_engine import (
    VERIFIED_UMA_ADAPTERS,
    is_objective_uma_market,
)


def _mk_tok_pair(seed: int) -> str:
    return json.dumps([f"{seed}00000000000000000001", f"{seed}00000000000000000002"])


def _mk_cid(seed: int) -> str:
    return "0x" + f"{seed:064x}"


class TestV51CatalogExpansionAndQA(unittest.TestCase):
    def test_01_p0a_trillion_strike_and_non_backtracking_guard(self) -> None:
        self.assertAlmostEqual(_parse_scalar_strike("$1.8T") or 0.0, 1.8e12, places=2)
        self.assertAlmostEqual(_parse_scalar_strike("1.8 trillion") or 0.0, 1.8e12, places=2)
        self.assertAlmostEqual(_parse_scalar_strike("$750B") or 0.0, 7.5e11, places=2)
        self.assertAlmostEqual(_parse_scalar_strike("$500M") or 0.0, 5.0e8, places=2)

        # Unknown suffixes or version-like strings MUST NOT backtrack to `1.8` or `1`!
        self.assertIsNone(_parse_scalar_strike("$1.8Q"))
        self.assertIsNone(_parse_scalar_strike("$1.8X"))
        self.assertIsNone(_parse_scalar_strike("1.8.5"))

        # Stem parity across B and T rungs so `parse_cal1_monotonic_ladder_event` groups them cleanly
        s_750b = _canon_clause_stem("Will OpenAI IPO valuation exceed $750B?", "$750B+")
        s_18t = _canon_clause_stem("Will OpenAI IPO valuation exceed $1.8T?", "$1.8T+")
        self.assertEqual(s_750b, s_18t)

        now_ts = 1794355200.0  # 2026-11-11 UTC
        ev_ipo_val = {
            "id": "ev_openai_val",
            "slug": "openai-ipo-valuation-threshold",
            "title": "OpenAI IPO valuation above X?",
            "endDate": "2027-06-30T23:59:59Z",
            "markets": [
                {
                    "id": "m_500b",
                    "question": "Will OpenAI IPO valuation exceed $500B?",
                    "description": "This market resolves to Yes if OpenAI completes an IPO at an official initial valuation above $500B USD.",
                    "groupItemTitle": "$500B+",
                    "outcomes": '["Yes", "No"]',
                    "conditionId": _mk_cid(101),
                    "clobTokenIds": _mk_tok_pair(101),
                    "active": True,
                    "closed": False,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "endDate": "2027-06-30T23:59:59Z",
                },
                {
                    "id": "m_750b",
                    "question": "Will OpenAI IPO valuation exceed $750B?",
                    "description": "This market resolves to Yes if OpenAI completes an IPO at an official initial valuation above $750B USD.",
                    "groupItemTitle": "$750B+",
                    "outcomes": '["Yes", "No"]',
                    "conditionId": _mk_cid(102),
                    "clobTokenIds": _mk_tok_pair(102),
                    "active": True,
                    "closed": False,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "endDate": "2027-06-30T23:59:59Z",
                },
                {
                    "id": "m_18t",
                    "question": "Will OpenAI IPO valuation exceed $1.8T?",
                    "description": "This market resolves to Yes if OpenAI completes an IPO at an official initial valuation above $1.8T USD.",
                    "groupItemTitle": "$1.8T+",
                    "outcomes": '["Yes", "No"]',
                    "conditionId": _mk_cid(103),
                    "clobTokenIds": _mk_tok_pair(103),
                    "active": True,
                    "closed": False,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "endDate": "2027-06-30T23:59:59Z",
                },
            ],
        }
        specs = parse_cal1_monotonic_ladder_event(ev_ipo_val, now_ts=now_ts)
        self.assertEqual(len(specs), 1)
        sp = specs[0]
        self.assertEqual(sp.ladder_kind, "SCALAR_ABOVE")
        self.assertEqual([r.market_id for r in sp.rungs], ["m_500b", "m_750b", "m_18t"])
        self.assertLess(sp.rungs[1].order_val, sp.rungs[2].order_val)

        # Verify normal pricing ($750B YES=0.45/NO=0.56, $1.8T YES=0.15/NO=0.86) does NOT trigger a false box,
        # while a genuine inversion ($1.8T YES=0.48 > $750B YES -> $1.8T NO=0.50 + $750B YES=0.48 = 0.98) DOES!
        normal_asks = {
            sp.rungs[0].yes_token: 0.70, sp.rungs[0].no_token: 0.31,
            sp.rungs[1].yes_token: 0.45, sp.rungs[1].no_token: 0.56,
            sp.rungs[2].yes_token: 0.15, sp.rungs[2].no_token: 0.86,
        }
        self.assertEqual(detect_cal1_monotonic_boxes(sp, normal_asks, max_box_cost_net=0.995), [])

        inverted_asks = dict(normal_asks)
        inverted_asks[sp.rungs[1].yes_token] = 0.46
        inverted_asks[sp.rungs[2].no_token] = 0.51
        boxes = detect_cal1_monotonic_boxes(sp, inverted_asks, max_box_cost_net=0.995)
        self.assertEqual(len(boxes), 1)
        self.assertAlmostEqual(boxes[0]["box_cost_net"], 0.97, places=4)

    def test_02_p0b_conditional_negrisk_missing_catchall_guard(self) -> None:
        ev_meta_incomplete = {
            "id": "ev_anth_ipo",
            "slug": "anthropic-ipo-percentage-of-shares-offered",
            "title": "Anthropic IPO: % of shares offered",
            "negRisk": True,
            "negRiskAugmented": False,
            "endDate": "2027-06-30T23:59:59Z",
        }
        outcomes_incomplete = [
            {
                "id": f"m_anth_{i}",
                "question": f"Will Anthropic offer {lbl} of shares in its IPO?",
                "groupItemTitle": lbl,
                "conditionId": _mk_cid(200 + i),
                "clobTokenIds": _mk_tok_pair(200 + i),
                "negRisk": True,
                "negRiskMarketID": "0x" + "aa" * 32,
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "feesEnabled": False,
                "endDate": "2027-06-30T23:59:59Z",
            }
            for i, lbl in enumerate(["<5%", "5-10%", "10-15%", "15%+"])
        ]
        self.assertTrue(
            is_conditional_negrisk_missing_catchall(
                ev_meta_incomplete["title"],
                [o["groupItemTitle"] for o in outcomes_incomplete],
            )
        )
        ok_part, info = verify_v2_negrisk_other_partition(outcomes_incomplete, event_meta=ev_meta_incomplete)
        self.assertFalse(ok_part)
        self.assertEqual(info["reason"], "CONDITIONAL_EVENT_MISSING_NO_EVENT_CATCHALL")
        self.assertFalse(info["safe_for_all_yes_basket"])

        ev_full_obj = {**ev_meta_incomplete, "markets": outcomes_incomplete}
        conv_sp = parse_negrisk_convert_event(ev_full_obj)
        self.assertIsNotNone(conv_sp)
        assert conv_sp is not None
        self.assertFalse(conv_sp.is_closed_convert_safe)
        # 2-leg `NO_i + NO_j` mutual-exclusion box MUST remain active (`<= 1 YES` even if no IPO happens!)
        no_asks = {b["no_token"]: (0.48 if idx < 2 else 0.92) for idx, b in enumerate(conv_sp.brackets)}
        pair_boxes = detect_negrisk_no_pair_boxes(conv_sp, no_asks, max_box_cost_net=0.99)
        self.assertTrue(len(pair_boxes) >= 1)
        self.assertAlmostEqual(pair_boxes[0]["box_cost_net"], 0.96, places=4)

        # Adding an explicit `"No IPO"` catch-all makes the partition exhaustive (`ok_part == True`)
        outcomes_complete = outcomes_incomplete + [
            {
                "id": "m_anth_none",
                "question": "Will Anthropic not complete an IPO before July 2027?",
                "groupItemTitle": "No IPO",
                "conditionId": _mk_cid(299),
                "clobTokenIds": _mk_tok_pair(299),
                "negRisk": True,
                "negRiskMarketID": "0x" + "aa" * 32,
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "feesEnabled": False,
                "endDate": "2027-06-30T23:59:59Z",
            }
        ]
        ok_complete, _ = verify_v2_negrisk_other_partition(outcomes_complete, event_meta=ev_meta_incomplete)
        self.assertTrue(ok_complete)

    def test_03_p1a_uma_objective_league_whitelist_and_subjective_vetoes(self) -> None:
        uma_base = {
            "closed": False,
            "archived": False,
            "acceptingOrders": True,
            "umaResolutionStatus": "proposed",
            "umaResolutionStatuses": '["proposed"]',
            "resolvedBy": sorted(VERIFIED_UMA_ADAPTERS)[0],
            "questionID": "0x" + "11" * 32,
            "outcomes": '["Yes", "No"]',
            "clobTokenIds": _mk_tok_pair(501),
        }
        # 1. Official-league post-deadline NFL roster market (`endDate` in the past) -> ACCEPTED
        nfl_post_deadline = {
            **uma_base,
            "id": "m_jt_colts",
            "slug": "pro-football-jonathan-taylor-next-team-2026-colts",
            "_ev_slug": "pro-football-jonathan-taylor-next-team-2026",
            "question": "Will Jonathan Taylor's next team be the Indianapolis Colts?",
            "description": "This market resolves according to official NFL transaction wire records.",
            "endDate": "2020-11-10T04:59:00Z",
            "outcomePrices": '["0.01", "0.99"]',
        }
        ok_nfl, dom_nfl = is_objective_uma_market(nfl_post_deadline)
        self.assertTrue(ok_nfl, f"Got domain: {dom_nfl}")
        self.assertEqual(dom_nfl, "OFFICIAL_LEAGUE_POST_DEADLINE")

        # 2. Official-league offseason eliminated-NO market (`NO >= 0.94`) -> ACCEPTED
        val_elim = {
            **uma_base,
            "id": "m_val_crashies",
            "slug": "valorant-offseason-crashies-next-team-fnatic",
            "_ev_slug": "valorant-offseason-crashies-next-team",
            "question": "Will crashies join Fnatic in the VCT offseason?",
            "description": "Resolves YES if official VCT team announcement confirms roster signing.",
            "endDate": "2099-02-01T00:00:00Z",
            "outcomePrices": '["0.005", "0.995"]',
        }
        ok_val, dom_val = is_objective_uma_market(val_elim)
        self.assertTrue(ok_val, f"Got domain: {dom_val}")
        self.assertEqual(dom_val, "OFFICIAL_LEAGUE_ELIMINATED_NO")

        # 3. Official .gov statistical agency domain -> ACCEPTED
        gov_mkt = {
            **uma_base,
            "id": "m_bea_gdp",
            "question": "Will Q3 US GDP advance estimate exceed 2.5%?",
            "description": "Resolution source: https://www.bea.gov/data/gdp/gross-domestic-product",
            "endDate": "2026-10-30T13:00:00Z",
        }
        ok_gov, _ = is_objective_uma_market(gov_mkt)
        self.assertTrue(ok_gov)

        # 4. Subjective pop-culture / streamer / reality TV / 2028 election / geopolitics -> HARD BLOCKED
        for bad_mkt in (
            {
                **uma_base,
                "slug": "kai-cenat-gta-6-marathon-hours",
                "question": "Will Kai Cenat complete his GTA marathon on Twitch?",
                "description": "Resolves based on livestream footage.",
                "endDate": "2020-11-01T00:00:00Z",
                "outcomePrices": '["0.01", "0.99"]',
            },
            {
                **uma_base,
                "slug": "dancing-with-the-stars-season-35-winner",
                "question": "Will contestant X win Dancing With The Stars?",
                "description": "Official ABC broadcast elimination results.",
                "endDate": "2020-11-01T00:00:00Z",
                "outcomePrices": '["0.01", "0.99"]',
            },
            {
                **uma_base,
                "slug": "presidential-election-winner-2028",
                "question": "Will Candidate Y win the 2028 US Presidential Election?",
                "description": "Official election results.",
                "endDate": "2028-11-07T00:00:00Z",
                "outcomePrices": '["0.01", "0.99"]',
            },
            {
                **uma_base,
                "slug": "russia-ukraine-ceasefire-2026",
                "question": "Will Russia and Ukraine agree to a ceasefire before December?",
                "description": "Consensus of credible news reporting.",
                "endDate": "2020-11-01T00:00:00Z",
                "outcomePrices": '["0.01", "0.99"]',
            },
        ):
            ok_bad, dom_bad = is_objective_uma_market(bad_mkt)
            self.assertFalse(ok_bad, f"Expected veto for {bad_mkt['slug']}, got {dom_bad}")

    def test_04_p1b_december_31_and_cross_year_deadline_ladder_parsing(self) -> None:
        now_ts = datetime(2026, 11, 11, 6, 0, tzinfo=timezone.utc).timestamp()
        # Case A: child `"December 31"` has `endDate = 2027-01-01T04:59:00Z` (11:59 PM ET Dec 31, 2026)
        ref_jan1_utc = datetime(2027, 1, 1, 4, 59, tzinfo=timezone.utc).timestamp()
        ts_dec31 = _parse_group_label_date_ts("December 31", ref_jan1_utc)
        self.assertIsNotNone(ts_dec31)
        dt_dec31 = datetime.fromtimestamp(float(ts_dec31), tz=timezone.utc)
        self.assertEqual((dt_dec31.year, dt_dec31.month, dt_dec31.day), (2026, 12, 31))

        # Case B: Cross-year range `"December 28-January 3"` around Jan 3, 2027
        ref_jan4_utc = datetime(2027, 1, 4, 0, 0, tzinfo=timezone.utc).timestamp()
        ts_range = _parse_group_label_date_ts("December 28 - January 3", ref_jan4_utc)
        self.assertIsNotNone(ts_range)
        dt_range = datetime.fromtimestamp(float(ts_range), tz=timezone.utc)
        self.assertEqual((dt_range.year, dt_range.month, dt_range.day), (2027, 1, 3))

        # Case C: Full 3-rung cumulative deadline event sharing parent `endDate = 2027-04-01T00:00:00Z`
        ev_deadline = {
            "id": "ev_ceasefire_dl",
            "slug": "event-by-deadline-ladder",
            "title": "Event X by...?",
            "endDate": "2027-04-01T00:00:00Z",
            "markets": [
                {
                    "id": "m_nov30",
                    "question": "Will Event X happen by November 30?",
                    "description": "This market will resolve to Yes if Event X officially occurs by November 30, 11:59 PM ET, between market creation and the specified date.",
                    "groupItemTitle": "November 30",
                    "outcomes": '["Yes", "No"]',
                    "conditionId": _mk_cid(301),
                    "clobTokenIds": _mk_tok_pair(301),
                    "active": True,
                    "closed": False,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "endDate": "2027-04-01T00:00:00Z",
                },
                {
                    "id": "m_dec31",
                    "question": "Will Event X happen by December 31?",
                    "description": "This market will resolve to Yes if Event X officially occurs by December 31, 11:59 PM ET, between market creation and the specified date.",
                    "groupItemTitle": "December 31",
                    "outcomes": '["Yes", "No"]',
                    "conditionId": _mk_cid(302),
                    "clobTokenIds": _mk_tok_pair(302),
                    "active": True,
                    "closed": False,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "endDate": "2027-01-01T04:59:00Z",
                },
                {
                    "id": "m_mar31",
                    "question": "Will Event X happen by March 31, 2027?",
                    "description": "This market will resolve to Yes if Event X officially occurs by March 31, 2027, 11:59 PM ET, between market creation and the specified date.",
                    "groupItemTitle": "March 31, 2027",
                    "outcomes": '["Yes", "No"]',
                    "conditionId": _mk_cid(303),
                    "clobTokenIds": _mk_tok_pair(303),
                    "active": True,
                    "closed": False,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "endDate": "2027-04-01T00:00:00Z",
                },
            ],
        }
        cal_specs = parse_cal1_monotonic_ladder_event(ev_deadline, now_ts=now_ts)
        self.assertEqual(len(cal_specs), 1)
        self.assertEqual([r.market_id for r in cal_specs[0].rungs], ["m_nov30", "m_dec31", "m_mar31"])

    def test_05_p1c_zerofee_general_binaries_volume_ranking(self) -> None:
        now_ts = 1794355200.0
        events = [
            {
                "id": "ev_dead_soon",
                "slug": "obscure-soon-binary",
                "closed": False,
                "negRisk": False,
                "markets": [
                    {
                        "id": "m_dead_soon",
                        "question": "Low volume binary expiring tomorrow?",
                        "conditionId": _mk_cid(401),
                        "clobTokenIds": _mk_tok_pair(401),
                        "active": True,
                        "closed": False,
                        "enableOrderBook": True,
                        "feesEnabled": False,
                        "liquidityNum": 520.0,
                        "volume24hr": 0.0,
                        "endDate": datetime.fromtimestamp(now_ts + 86400.0, tz=timezone.utc).isoformat(),
                    }
                ],
            },
            {
                "id": "ev_high_vol",
                "slug": "geopolitics-major-summit",
                "closed": False,
                "negRisk": False,
                "markets": [
                    {
                        "id": "m_high_vol",
                        "question": "High volume 0%-fee binary expiring in 20 days?",
                        "conditionId": _mk_cid(402),
                        "clobTokenIds": _mk_tok_pair(402),
                        "active": True,
                        "closed": False,
                        "enableOrderBook": True,
                        "feesEnabled": False,
                        "liquidityNum": 85000.0,
                        "volume24hr": 240000.0,
                        "endDate": datetime.fromtimestamp(now_ts + 20 * 86400.0, tz=timezone.utc).isoformat(),
                    }
                ],
            },
        ]
        out = Alpha124ShadowDaemon.extract_zerofee_general_binaries(events, now_ts)
        self.assertEqual([r["market_id"] for r in out], ["m_high_vol", "m_dead_soon"])

    def test_06_p2_harvester_load_state_windows_save_and_kmia_tier_haircut(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            st_path = Path(td) / "live_harvester_state.json"
            now_ts = 1794355200.0
            kmia_pos = {
                "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                "market_id": "6707503",
                "event_id": "kmia_nov7",
                "asset": "KMIA",
                "token_id": "1234567890",
                "target_token": "NO",
                "entry_price": 0.971,
                "entry_shares": 35.0,
                "remaining_shares": 35.0,
                "notional_usd": 50.51,
                "remaining_cost_basis": 50.51,
                "best_bid": 0.004,
                "candle_expiry_ts": now_ts - 4 * 86400.0,
                "umaResolutionStatus": "disputed",
                "hold_to_maturity_lock": True,
                "is_single_leg_lock": True,
                "status": "POSITION_CONFIRMED",
            }
            subcent_cp = {
                "trade_id": "SUBCENT_WIN_1",
                "market_id": "999111",
                "target_token": "YES",
                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "is_dominance_box": True,
                "status": "SETTLED",
                "close_reason": "ONCHAIN_REDEMPTION",
                "notional_usd": 9.996,
                "entry_fee_cash_usd": 0.0,
                "confirmed_realized_cash": 10.00,
                "realized_exit_cash": 10.00,
                "realized_exit_fee": 0.0,
                "net_pnl_usd": 0.0,
                "won": False,
            }
            seed_state = {
                "state_version": "2.0.0",
                "live_bankroll": 48.57,
                "total_account_equity": 99.08,
                "high_water_mark_equity": 110.22,
                "current_equity_tier": "HYPER_GROWTH",
                "equity_tier": "HYPER_GROWTH",
                "active_positions": {"WS_SNIPE_Miami_KMIA_242960": kmia_pos},
                "closed_positions": [subcent_cp],
                "pending_entry_intents": {},
                "risk_state": {"halted": False, "halt_reason": ""},
            }
            st_path.write_text(json.dumps(seed_state), encoding="utf-8")

            with mock.patch("src.polymarket_research.polymarket_live_harvester.STATE_FILE", st_path):
                h = PolymarketLiveHarvester(dry_run=True)
                h._is_v5_live_strict = lambda: True  # type: ignore[method-assign]
                h.load_state()
                h.save_state()

            saved = json.loads(st_path.read_text(encoding="utf-8"))
            # 1. Sub-cent migration triggered `self.save_state()` inside `load_state()` without WinError 5!
            self.assertTrue(saved["closed_positions"][0]["won"])
            # 2. Book equity preserved for PAAAccountant (`$99.08`), while tier & caps haircut disputed KMIA!
            self.assertAlmostEqual(float(saved["total_account_equity"]), 99.08, places=2)
            self.assertAlmostEqual(float(saved["reconciled_nav_usd"]), 48.71, places=2)
            self.assertEqual(saved["current_equity_tier"], "UNLEASHED_LAUNCH")
            dyn_caps = saved["live_riskless_funnel"]["dynamic_tier_caps"]
            self.assertLess(float(dyn_caps["max_correlated_oracle_event_notional_usd"]), 7.50)
            self.assertAlmostEqual(float(dyn_caps["max_correlated_oracle_event_notional_usd"]), 48.71 * 0.15, places=3)

    def test_07_p2_safe_zoneinfo_and_transport_aexit(self) -> None:
        with mock.patch("zoneinfo.ZoneInfo", side_effect=Exception("No tzdata installed")):
            for tz_nm in (
                "America/New_York",
                "America/Chicago",
                "America/Toronto",
                "Europe/London",
                "Asia/Tokyo",
                "Asia/Seoul",
                "America/Sao_Paulo",
                "UTC",
            ):
                tz_obj = safe_zoneinfo(tz_nm)
                dt = datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc).astimezone(tz_obj)
                self.assertIsNotNone(dt.tzinfo)

        class _SyncCloseSession:
            def __init__(self) -> None:
                self.closed = False

            def close(self) -> None:
                self.closed = True
                return None

        async def _check_close() -> bool:
            tr = ResilientReadOnlyTransport()
            sess = _SyncCloseSession()
            tr._session = sess  # type: ignore[assignment]
            await tr.__aexit__(None, None, None)
            return sess.closed and tr._session is None

        self.assertTrue(asyncio.run(_check_close()))


if __name__ == "__main__":
    unittest.main()

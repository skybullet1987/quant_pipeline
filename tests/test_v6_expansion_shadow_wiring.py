"""
End-to-End Regression Suite (`tests/test_v6_expansion_shadow_wiring.py`)
verifying that all 8 v6 Riskless Expansion sleeves (`ALL_V6_EXPANSION_SLEEVES`):
  1. Execute cleanly without hidden `TypeError`s in both `run_v6_expansion_alpha124_scan`
     and `run_v6_expansion_cross_venue_scan` (`last_error` absent on all 8 sleeves).
  2. Open honest shadow positions in `Alpha124ShadowDaemon` (`open_positions`) and
     Stage G Cross-Venue (`v6_expansion_shadow_ledger.json` -> `by_sleeve`), never
     emitting unauthorized live orders (`grad8_live_promoted == False`).
  3. Settle matured shadow boxes conservatively at worst-case guaranteed floor or
     verified Gamma payout, updating `wins`, `closed`, and `realized_pnl_t1000_usd`.
  4. Enforce queue-crossing fill discipline on passive `BINARY_HEDGED_MAKER_ASK`
     (never instant-filling resting asks without bid crossing) and preserve `D-001`
     non-interference on disputed `KMIA` market IDs `6707502` / `6707503`.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from src.polymarket_research.cross_venue_riskless_shadow import (
    NormalizedBinaryMarket,
    OrderLevel,
)
from src.polymarket_research.riskless_expansion_v6_engines import (
    ALL_V6_EXPANSION_SLEEVES,
    _fetch_deribit_usdc_public_options,
    run_v6_expansion_alpha124_scan,
    run_v6_expansion_cross_venue_scan,
)


def _mk_market(
    *,
    venue: str,
    market_id: str,
    title: str,
    category: str = "macro",
    collateral_asset: str = "USD",
    yes_asks: tuple[OrderLevel, ...] = (OrderLevel(0.48, 400.0),),
    no_asks: tuple[OrderLevel, ...] = (OrderLevel(0.48, 400.0),),
    yes_bids: tuple[OrderLevel, ...] = (OrderLevel(0.46, 400.0),),
    no_bids: tuple[OrderLevel, ...] = (OrderLevel(0.46, 400.0),),
    end_ts: int = 1_800_000_000,
    partition_group_id: str = "",
    neg_risk: bool = False,
    strike_price: float | None = None,
    asset: str = "BTC",
    cancel_rule: str = "VOID",
) -> NormalizedBinaryMarket:
    return NormalizedBinaryMarket(
        venue=venue,
        market_id=market_id,
        slug=market_id,
        title=title,
        category=category,
        yes_asks=list(yes_asks),
        yes_bids=list(yes_bids),
        no_asks=list(no_asks),
        no_bids=list(no_bids),
        fee_rate_bps=0.0,
        fee_enabled=True,
        taker_delay_ms=0.0,
        min_shares=5.0,
        asset=asset,
        horizon="daily",
        oracle_family="official",
        strike_price=strike_price,
        strike_direction="UP" if strike_price else "",
        end_ts=end_ts,
        cancel_rule=cancel_rule,
        has_unlisted_draw=False,
        tick_size=0.01,
        lot_size=1.0,
        quote_ts_ms=(end_ts - 3600) * 1000,
        collateral_asset=collateral_asset,
        settlement_delay_hours=1.0,
        neg_risk=neg_risk,
        partition_group_id=partition_group_id,
    )


class TestV6ExpansionShadowWiring(unittest.TestCase):
    """End-to-end verification of all 8 v6 shadow scanners, ledgers, and settlement hooks."""

    def test_alpha124_v6_scan_wires_all_intra_polymarket_engines_and_blocks_kmia(self) -> None:
        exp_dt = datetime(2026, 11, 15, 8, 0, 0, tzinfo=timezone.utc)
        exp_ts = exp_dt.timestamp()
        now_u = exp_ts - 7200.0

        rg_lo = SimpleNamespace(
            asset="BTC",
            strike=94000.0,
            end_ts=exp_ts,
            yes_token="tok_y_lo",
            no_token="tok_n_lo",
            market_id="m_lo",
            fee_rate=0.07,
            fee_exponent=1.0,
            is_downward=False,
        )
        rg_hi = SimpleNamespace(
            asset="BTC",
            strike=100000.0,
            end_ts=exp_ts,
            yes_token="tok_y_hi",
            no_token="tok_n_hi",
            market_id="m_hi",
            fee_rate=0.07,
            fee_exponent=1.0,
            is_downward=False,
        )
        # Disputed KMIA market MUST be ignored unconditionally (`D-001`)
        rg_kmia = SimpleNamespace(
            asset="BTC",
            strike=95000.0,
            end_ts=exp_ts,
            yes_token="tok_kmia_y",
            no_token="tok_kmia_n",
            market_id="6707503",
            fee_rate=0.0,
            fee_exponent=1.0,
            is_downward=False,
        )

        # Closed NegRisk slate for NR3 (`HEDGED_PRESPLIT_CONV_GUN`) AND augmented slate for `XV_SUBSET_NO_BOX`
        nr_closed = SimpleNamespace(
            event_id="ev_nr3_closed",
            slug="closed-fomc-slate",
            title="Closed FOMC Rate Decision",
            is_closed_convert_safe=True,
            end_ts=now_u + 86400.0,
            brackets=[
                {"market_id": "nr_a", "label": "Hold", "yes_token": "nr_ya", "no_token": "nr_na", "fee_rate": 0.04, "fee_exponent": 2.0},
                {"market_id": "nr_b", "label": "Cut25", "yes_token": "nr_yb", "no_token": "nr_nb", "fee_rate": 0.04, "fee_exponent": 2.0},
                {"market_id": "nr_c", "label": "Cut50", "yes_token": "nr_yc", "no_token": "nr_nc", "fee_rate": 0.04, "fee_exponent": 2.0},
            ],
        )
        nr_aug = SimpleNamespace(
            event_id="ev_subno_aug",
            slug="aug-election-slate",
            title="Augmented Winner Slate",
            is_closed_convert_safe=False,
            end_ts=now_u + 43200.0,
            brackets=[
                {"market_id": "sub_1", "label": "Cand1", "yes_token": "s_y1", "no_token": "s_n1", "fee_rate": 0.0, "fee_exponent": 1.0},
                {"market_id": "sub_2", "label": "Cand2", "yes_token": "s_y2", "no_token": "s_n2", "fee_rate": 0.0, "fee_exponent": 1.0},
                {"market_id": "sub_3", "label": "Cand3", "yes_token": "s_y3", "no_token": "s_n3", "fee_rate": 0.0, "fee_exponent": 1.0},
            ],
        )

        # Holding-Reward general binary (`YIELD_STACKED_CARRY_BOX`) + Maker-Ask candidate (`HEDGED_PRESPLIT_CONV_GUN`)
        gen_bins = [
            {
                "market_id": "m_hold_120d",
                "condition_id": "0x" + "a" * 64,
                "yes_token": "hy_1",
                "no_token": "hn_1",
                "fee_rate": 0.0,
                "fee_exponent": 1.0,
                "fees_enabled": False,
                "holding_rewards_enabled": True,
                "neg_risk": False,
                "end_ts": now_u + 120.0 * 86400.0,
                "asset": "MACRO",
                "title": "Long-Dated Holding Rewards Rate Box",
            },
            {
                "market_id": "m_mkr_ask",
                "condition_id": "0x" + "b" * 64,
                "yes_token": "my_1",
                "no_token": "mn_1",
                "fee_rate": 0.07,
                "fee_exponent": 2.0,
                "fees_enabled": True,
                "holding_rewards_enabled": False,
                "neg_risk": False,
                "end_ts": now_u + 3600.0,
                "asset": "BTC",
                "title": "BTC 15m Hedged Maker Ask Binary",
            },
        ]

        # UMA BOND3 market with `uma_onchain_cache` `(ts, ver_dict)` tuple keyed by `mid` (exact Alpha-124 format!)
        uma_mkts = {
            "m_uma_final": {
                "id": "m_uma_final",
                "conditionId": "0x" + "c" * 64,
                "question": "Will Bitcoin close above $80,000 on Nov 12?",
            }
        }
        uma_cache = {
            "m_uma_final": (
                now_u - 10.0,
                {
                    "verified": True,
                    "oo_state": 2,
                    "win_index": 0,
                    "win_label": "YES",
                    "win_token": "uma_w",
                    "lose_token": "uma_l",
                    "proposal_age_sec": 1800.0,
                    "rem_challenge_sec": 2400.0,
                    "fee_rate": 0.03,
                    "fee_exponent": 2.0,
                },
            )
        }

        bks = {
            "tok_y_lo": {"asks": [{"price": 0.966, "size": 250.0}], "bids": [{"price": 0.962, "size": 200.0}]},
            "tok_n_lo": {"asks": [{"price": 0.038, "size": 250.0}], "bids": [{"price": 0.033, "size": 200.0}]},
            "tok_y_hi": {"asks": [{"price": 0.560, "size": 300.0}], "bids": [{"price": 0.540, "size": 200.0}]},
            "tok_n_hi": {"asks": [{"price": 0.025, "size": 300.0}], "bids": [{"price": 0.021, "size": 200.0}]},
            "nr_ya": {"bids": [{"price": 0.56, "size": 80.0}], "asks": [{"price": 0.58, "size": 80.0}]},
            "nr_yb": {"bids": [{"price": 0.47, "size": 60.0}], "asks": [{"price": 0.49, "size": 60.0}]},
            "nr_yc": {"bids": [{"price": 0.02, "size": 50.0}], "asks": [{"price": 0.04, "size": 50.0}]},
            "s_n1": {"asks": [{"price": 0.46, "size": 200.0}], "bids": [{"price": 0.44, "size": 100.0}]},
            "s_n2": {"asks": [{"price": 0.46, "size": 200.0}], "bids": [{"price": 0.44, "size": 100.0}]},
            "s_n3": {"asks": [{"price": 0.85, "size": 200.0}], "bids": [{"price": 0.82, "size": 100.0}]},
            "hy_1": {"asks": [{"price": 0.501, "size": 300.0}], "bids": [{"price": 0.495, "size": 200.0}]},
            "hn_1": {"asks": [{"price": 0.501, "size": 300.0}], "bids": [{"price": 0.495, "size": 200.0}]},
            "my_1": {"asks": [{"price": 0.530, "size": 100.0}], "bids": [{"price": 0.510, "size": 100.0}]},
            "mn_1": {"asks": [{"price": 0.510, "size": 100.0}], "bids": [{"price": 0.495, "size": 100.0}]},
            "uma_w": {"asks": [{"price": 0.999, "size": 500.0}], "bids": [{"price": 0.985, "size": 400.0}]},
            "uma_l": {"asks": [{"price": 0.030, "size": 100.0}], "bids": [{"price": 0.020, "size": 80.0}]},
        }

        async def _fake_batch(toks: list[str], timeout: float = 2.0) -> dict[str, dict]:
            self.assertNotIn("tok_kmia_y", toks)
            self.assertNotIn("tok_kmia_n", toks)
            return {t: bks[t] for t in toks if t in bks}

        async def _fake_fetch_json(url: str, timeout: float = 5.0) -> dict:
            if "deribit.com" in url:
                return {
                    "result": [
                        {
                            "instrument_name": "BTC_USDC-15NOV26-97000-C",
                            "quote_currency": "USDC",
                            "underlying_price": 99000.0,
                            "bid_price": 2100.0,
                            "ask_price": 2110.0,
                            "bid_size": 5.0,
                            "ask_size": 5.0,
                        },
                        {
                            "instrument_name": "BTC_USDC-15NOV26-98000-C",
                            "quote_currency": "USDC",
                            "underlying_price": 99000.0,
                            "bid_price": 1650.0,
                            "ask_price": 1665.0,
                            "bid_size": 5.0,
                            "ask_size": 5.0,
                        },
                    ]
                }
            return {}

        with tempfile.TemporaryDirectory() as tmp_dir:
            daemon = SimpleNamespace(
                single_scan=False,
                _v6_data_dir=Path(tmp_dir),
                strike_ladders={"btc": [rg_lo, rg_hi, rg_kmia]},
                zerofee_general_binaries=gen_bins,
                uma_proposed_markets=uma_mkts,
                uma_onchain_cache=uma_cache,
                spots={"BTC": 88000.0},
                negrisk_convert_slates={"ev_nr3_closed": nr_closed, "ev_subno_aug": nr_aug},
                holding_rewards_apy=0.0,
                open_positions={},
                entered_keys=set(),
                fetch_books_batch=_fake_batch,
                fetch_json=_fake_fetch_json,
            )

            opps_out: list[dict] = []
            res1 = asyncio.run(run_v6_expansion_alpha124_scan(daemon, opps_out, now_ts=now_u))

            for slv in ALL_V6_EXPANSION_SLEEVES:
                self.assertNotIn("last_error", res1["per_sleeve"][slv], f"Unexpected error in {slv}: {res1['per_sleeve'][slv]}")

            opened_sleeves = {p["sleeve"] for p in daemon.open_positions.values()}
            self.assertIn("XV_SUBSET_NO_BOX", opened_sleeves)
            self.assertIn("TAIL_BOUNDARY_001_ARB", opened_sleeves)
            self.assertIn("BOND3_MULTISOURCE_DEAD_SPLIT", opened_sleeves)
            self.assertIn("DERIBIT_VERTICAL_SUPER_REP", opened_sleeves)
            self.assertIn("HEDGED_PRESPLIT_CONV_GUN", opened_sleeves)
            self.assertIn("YIELD_STACKED_CARRY_BOX", opened_sleeves)

            # Resting Maker-Ask (`m_mkr_ask`) must be staged in `_pending_v6_maker_asks` on scan 1 (NOT instant-filled!)
            self.assertIn("m_mkr_ask", daemon._pending_v6_maker_asks)
            self.assertFalse(any("V6_HP_MKR_m_mkr_ask" in p["dedupe_key"] for p in daemon.open_positions.values()))

            # Scan 2: Cross `my_1` best_bid >= 0.530 -> pending Maker-Ask fills honestly!
            bks["my_1"] = {"asks": [{"price": 0.535, "size": 100.0}], "bids": [{"price": 0.531, "size": 100.0}]}
            asyncio.run(run_v6_expansion_alpha124_scan(daemon, [], now_ts=now_u + 15.0))
            self.assertTrue(any("V6_HP_MKR_m_mkr_ask" in p["dedupe_key"] for p in daemon.open_positions.values()))

    def test_cross_venue_v6_scan_fixes_subset_deribit_halftime_and_settles_ledger(self) -> None:
        exp_dt = datetime(2026, 11, 15, 8, 0, 0, tzinfo=timezone.utc)
        exp_ts = int(exp_dt.timestamp())
        now_u = float(exp_ts - 3600)

        # 1. Cross-venue Subset NO partition (`XV_SUBSET_NO_BOX`)
        pm_a = _mk_market(
            venue="polymarket",
            market_id="pm_cand_a",
            title="Election Winner Candidate A",
            collateral_asset="USDC",
            no_asks=(OrderLevel(0.45, 250.0),),
            end_ts=exp_ts,
            partition_group_id="grp_election_2026",
            neg_risk=True,
            cancel_rule="50_50",
        )
        pm_b = _mk_market(
            venue="polymarket",
            market_id="pm_cand_b",
            title="Election Winner Candidate B",
            collateral_asset="USDC",
            no_asks=(OrderLevel(0.46, 250.0),),
            end_ts=exp_ts,
            partition_group_id="grp_election_2026",
            neg_risk=True,
            cancel_rule="50_50",
        )

        # 2. CA-ON STX + ForecastEx FX-Invariant Box (`XV_FX_INVARIANT_CAD_USD_BOX`) & Yield Box (`YIELD_STACKED_CARRY_BOX`)
        stx_m = _mk_market(
            venue="stx_ontario",
            market_id="stx_boc",
            title="BoC Rate Hold Dec 2026",
            category="macro",
            collateral_asset="CAD",
            yes_asks=(OrderLevel(0.45, 500.0),),
            end_ts=int(now_u + 86400 * 60),
        )
        fex_m = _mk_market(
            venue="forecastex",
            market_id="fex_boc",
            title="BoC Rate Hold Dec 2026",
            category="macro",
            collateral_asset="USD",
            no_asks=(OrderLevel(0.50, 500.0),),
            end_ts=int(now_u + 86400 * 60),
        )
        pf_m = _mk_market(
            venue="predict_fun",
            market_id="pf_macro",
            title="US Macro Hold 120d",
            category="macro",
            collateral_asset="USDT",
            yes_asks=(OrderLevel(0.495, 500.0),),
            end_ts=int(now_u + 86400 * 120),
        )
        fex_y = _mk_market(
            venue="forecastex",
            market_id="fex_macro",
            title="US Macro Hold 120d",
            category="macro",
            collateral_asset="USD",
            no_asks=(OrderLevel(0.495, 500.0),),
            end_ts=int(now_u + 86400 * 120),
        )

        # 3. Deribit 08:00 UTC BTC Strike (`DERIBIT_VERTICAL_SUPER_REP`) via `ResilientReadOnlyTransport.get(...)`
        fex_btc = _mk_market(
            venue="forecastex",
            market_id="fex_btc_100k",
            title="Bitcoin above $100,000 at 08:00 UTC",
            category="crypto",
            collateral_asset="USD",
            no_asks=(OrderLevel(0.45, 300.0),),
            yes_asks=(OrderLevel(0.56, 300.0),),
            end_ts=exp_ts + 60,  # +60s offset within <=300s 08:00 UTC tolerance!
            strike_price=100_000.0,
            asset="BTC",
        )

        # 4. Sports .5-hook Halftime FG + 2H Corridor (`XV_HALFTIME_FREEZE_CORRIDOR`)
        fg_spt = _mk_market(
            venue="forecastex",
            market_id="fg_bos_nyk",
            title="Celtics vs Knicks Full Game Total Over/Under 220.5",
            category="sports_nba",
            collateral_asset="USD",
            yes_asks=(OrderLevel(0.46, 300.0),),
            no_asks=(OrderLevel(0.56, 300.0),),
            end_ts=exp_ts,
            partition_group_id="nba_bos_nyk_fg",
        )
        h2_spt = _mk_market(
            venue="stx_ontario",
            market_id="h2_bos_nyk",
            title="Celtics vs Knicks 2nd Half Total Over/Under 112.5",
            category="sports_nba",
            collateral_asset="CAD",
            yes_asks=(OrderLevel(0.58, 400.0),),
            no_asks=(OrderLevel(0.45, 400.0),),
            end_ts=exp_ts,
            partition_group_id="nba_bos_nyk_2h",
        )

        class _FakeResilientTransport:
            network_disabled = False

            async def get(self, venue: str, url: str, *, timeout_sec: float = 6.0) -> object:
                return SimpleNamespace(
                    status=200,
                    data={
                        "result": [
                            {
                                "instrument_name": "BTC_USDC-15NOV26-97000-C",
                                "quote_currency": "USDC",
                                "underlying_price": 99000.0,
                                "bid_price": 2100.0,
                                "ask_price": 2110.0,
                            },
                            {
                                "instrument_name": "BTC_USDC-15NOV26-98000-C",
                                "quote_currency": "USDC",
                                "underlying_price": 99000.0,
                                "bid_price": 1650.0,
                                "ask_price": 1665.0,
                            },
                            # OTM <$1.50 USDC option MUST remain $0.85 USDC, NOT 0.85 * 99000!
                            {
                                "instrument_name": "BTC_USDC-15NOV26-125000-C",
                                "quote_currency": "USDC",
                                "underlying_price": 99000.0,
                                "bid_price": 0.65,
                                "ask_price": 0.85,
                            },
                        ]
                    },
                )

        with tempfile.TemporaryDirectory() as tmp_dir:
            xv_dir = Path(tmp_dir)
            collector = SimpleNamespace(
                engine=SimpleNamespace(data_dir=xv_dir),
                env={"DOMINUS_NETWORK_MODE": "live_public"},
                _halftime_scoreboards={
                    "nba_bos_nyk": {
                        "sport": "nba",
                        "is_halftime": True,
                        "game_clock_sec": 0.0,
                        "elapsed_halftime_sec": 510.0,
                        "remaining_halftime_sec": 300.0,
                        "confirmed_1h_home_score": 58,
                        "confirmed_1h_away_score": 52,
                    }
                },
            )
            tr = _FakeResilientTransport()

            d_quotes = asyncio.run(_fetch_deribit_usdc_public_options(tr, cache_holder=SimpleNamespace(), now_ts=now_u))
            otm_q = [q for q in d_quotes if q.strike == 125000.0][0]
            self.assertAlmostEqual(otm_q.best_ask_usd, 0.85, places=4)

            xv_res = asyncio.run(
                run_v6_expansion_cross_venue_scan(
                    collector,
                    [pm_a, pm_b, stx_m, fex_m, pf_m, fex_y, fex_btc, fg_spt, h2_spt],
                    [(stx_m, fex_m), (pf_m, fex_y)],
                    transport=tr,
                    now_ts=now_u,
                )
            )

            for slv in ALL_V6_EXPANSION_SLEEVES:
                self.assertNotIn("last_error", xv_res["per_sleeve"][slv])

            self.assertGreaterEqual(xv_res["per_sleeve"]["XV_SUBSET_NO_BOX"]["opportunities_found"], 1)
            self.assertGreaterEqual(xv_res["per_sleeve"]["XV_FX_INVARIANT_CAD_USD_BOX"]["opportunities_found"], 1)
            self.assertGreaterEqual(xv_res["per_sleeve"]["DERIBIT_VERTICAL_SUPER_REP"]["opportunities_found"], 1)
            self.assertGreaterEqual(xv_res["per_sleeve"]["XV_HALFTIME_FREEZE_CORRIDOR"]["opportunities_found"], 1)
            self.assertGreaterEqual(xv_res["per_sleeve"]["YIELD_STACKED_CARRY_BOX"]["opportunities_found"], 1)

            self.assertGreaterEqual(xv_res["by_sleeve"]["XV_SUBSET_NO_BOX"]["open"], 1)
            self.assertGreaterEqual(xv_res["by_sleeve"]["DERIBIT_VERTICAL_SUPER_REP"]["open"], 1)
            self.assertGreaterEqual(xv_res["by_sleeve"]["XV_HALFTIME_FREEZE_CORRIDOR"]["open"], 1)

            # Advance past `exp_ts` -> open shadow boxes settle cleanly at guaranteed floor with 0 losses & positive T1000 PnL!
            xv_settled = asyncio.run(
                run_v6_expansion_cross_venue_scan(
                    collector,
                    [],
                    [],
                    transport=tr,
                    now_ts=float(exp_ts + 120),
                )
            )
            self.assertEqual(xv_settled["by_sleeve"]["XV_SUBSET_NO_BOX"]["open"], 0)
            self.assertGreaterEqual(xv_settled["by_sleeve"]["XV_SUBSET_NO_BOX"]["wins"], 1)
            self.assertEqual(xv_settled["by_sleeve"]["XV_SUBSET_NO_BOX"]["losses"], 0)
            self.assertGreater(xv_settled["by_sleeve"]["XV_SUBSET_NO_BOX"]["realized_pnl_t1000_usd"], 0.0)
            self.assertFalse(xv_settled["by_sleeve"]["XV_SUBSET_NO_BOX"]["grad8_live_promoted"])
            self.assertTrue((xv_dir / "v6_expansion_shadow_ledger.json").exists())

    def test_xv_subset_no_blocks_non_negrisk_cs2_maps_and_purges_legacy_false_positive(self) -> None:
        import json

        exp_ts = 1_794_565_800
        now_u = float(exp_ts - 7200)

        # Exact live false-positive fixture: CS2 G2 vs Falcons Map 1 Winner + Map 2 Winner (negRisk=False)
        cs2_map1 = _mk_market(
            venue="polymarket",
            market_id="6987909",
            title="Counter-Strike: G2 vs Team Falcons - Map 1 Winner",
            category="sports",
            collateral_asset="USDC",
            no_asks=(OrderLevel(0.41, 250.0),),
            end_ts=exp_ts,
            partition_group_id="cs2-g2-fal2-2026-11-13",
            neg_risk=False,
        )
        cs2_map2 = _mk_market(
            venue="polymarket",
            market_id="6987910",
            title="Counter-Strike: G2 vs Team Falcons - Map 2 Winner",
            category="sports",
            collateral_asset="USDC",
            no_asks=(OrderLevel(0.42, 250.0),),
            end_ts=exp_ts,
            partition_group_id="cs2-g2-fal2-2026-11-13",
            neg_risk=False,
        )
        # Even if neg_risk were misflagged True, Map 1 / Map 2 sub-period regex must still hard-reject!
        cs2_map1_misflagged = _mk_market(
            venue="polymarket",
            market_id="6987911",
            title="Counter-Strike: G2 vs Team Falcons - Map 1 Winner",
            category="sports",
            collateral_asset="USDC",
            no_asks=(OrderLevel(0.41, 250.0),),
            end_ts=exp_ts,
            partition_group_id="cs2-misflagged",
            neg_risk=True,
        )
        cs2_map2_misflagged = _mk_market(
            venue="polymarket",
            market_id="6987912",
            title="Counter-Strike: G2 vs Team Falcons - Map 2 Winner",
            category="sports",
            collateral_asset="USDC",
            no_asks=(OrderLevel(0.42, 250.0),),
            end_ts=exp_ts,
            partition_group_id="cs2-misflagged",
            neg_risk=True,
        )

        with tempfile.TemporaryDirectory() as tmpd:
            xv_dir = Path(tmpd)
            # Pre-seed contaminated pre-v6.1.2 open entry lacking verified_mutual_exclusion
            contaminated_ledger = {
                "open_positions": {
                    "XV_XV_SUBSET_NO_BOX_1794534374_47312": {
                        "position_id": "XV_XV_SUBSET_NO_BOX_1794534374_47312",
                        "dedupe_key": "XV6_xv_subno:cs2-g2-fal2-2026-11-13:m2:6987909+6987910",
                        "sleeve": "XV_SUBSET_NO_BOX",
                        "close_ts": float(exp_ts),
                        "extra": {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0},
                        "status": "OPEN",
                    }
                },
                "closed_positions": [],
                "entered_keys": ["XV6_xv_subno:cs2-g2-fal2-2026-11-13:m2:6987909+6987910"],
            }
            (xv_dir / "v6_expansion_shadow_ledger.json").write_text(
                json.dumps(contaminated_ledger), encoding="utf-8"
            )

            collector = SimpleNamespace(
                network_mode="offline",
                engine=SimpleNamespace(data_dir=xv_dir),
            )
            res = asyncio.run(
                run_v6_expansion_cross_venue_scan(
                    collector,
                    [cs2_map1, cs2_map2, cs2_map1_misflagged, cs2_map2_misflagged],
                    [],
                    transport=None,
                    now_ts=now_u,
                )
            )
            self.assertEqual(res["per_sleeve"]["XV_SUBSET_NO_BOX"]["evaluated"], 0)
            self.assertEqual(res["per_sleeve"]["XV_SUBSET_NO_BOX"]["opportunities_found"], 0)
            self.assertEqual(res["by_sleeve"]["XV_SUBSET_NO_BOX"]["open"], 0)
            persisted = json.loads((xv_dir / "v6_expansion_shadow_ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(len(persisted["open_positions"]), 0)
            self.assertEqual(persisted["purged_false_positives"], 1)


if __name__ == "__main__":
    unittest.main()

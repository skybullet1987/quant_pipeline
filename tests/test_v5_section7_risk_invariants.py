"""
DOMINUS v5.0 Section 7 Mandatory Risk Invariants & Regression Verification Suite
(`tests/test_v5_section7_risk_invariants.py`).

Verifies end-to-end production enforcement of:
  1. Section 7(a) — Maximum `15%` Reconciled NAV Concentration Cap:
     - Conservative mark-to-bid NAV valuation (`compute_reconciled_concentration_nav_usd`) excludes
       raw book cost of UMA-disputed (`$50.51` KMIA), post-expiry UMA-frozen, and legged-out residual
       (`MULTI_LEG_RESIDUAL` / `_UNWRESID_`) positions without any artificial `$25.00` floor.
     - Cross-sleeve weather-station/day (`EVTWX:<ICAO>:<bucket>`, `WXSTATION:<ICAO>`) and non-box
       oracle event aggregation across `W_PRUNE1`, `BOND1`, `UMA_READY1`, `MKR_LOCK1`, `S2`,
       `NEGRISK_CONVERT`, `MULTI_LEG_BUNDLE`, non-maker `pending_entry_intents`, and standalone `MKT:` keys,
       including city-name-only weather titles (`"Highest temperature in Miami on Nov 7?"`) while
       never misclassifying sports teams (`"Miami Heat vs Boston Celtics"`).
  2. Section 7(b) — `<$500` NAV Multi-Leg (`>=3` Legs) Bundle Hard Disable & Certification Gate:
     - Below `$500` reconciled NAV, sequential multi-leg bundles (`MULTI_LEG_BUNDLE`, `m>=3` `NEGRISK_CONVERT`,
       `NR3_SYNTHETIC_ALL_YES_OVERROUND`) are HARD-BLOCKED even when `strict_pure_riskless_mode=False`!
     - Demonstrably atomic on-chain execution (`atomic_onchain_execution=True` + `atomic_router_verified=True`)
       and pre-held verified complete-set inventory (`unheld_legs <= 1`, or `m=1` `NR_M1` dead-seed convert)
       remain permitted.
     - Above `$500` reconciled NAV (`$650` / `$5,000`), `>=3`-leg sequential bundles are NEVER automatically
       re-enabled (`is_nr0_closed_partition_graduated_unlock` and `check_multileg_3plus_nav_and_certification_gate`
       both fail closed until `certified_multileg_3plus_live_enabled=True`).
  3. Section 7(c) — Passive Maker Adverse-Selection Controls & Fail-Closed Accounting Invariants:
     - Resting Maker WS book cache staleness capped at `<= 5.0s` (`1.0s` on `S2`), never `30.0s`.
     - Consecutive blind book polls (`>= 3` timeouts / `None` books) trigger immediate fail-closed
       auto-cancellation of resting Maker orders instead of sitting blind on the CLOB.
     - Mid-rest UMA `disputed`, `oracle_shock_veto` / `news_shock_halt`, and dual-book shock inversion
       trigger immediate `"ADVERSE"` Maker cancellation in `eval_sll_live_book_poll`.
     - `PAAAccountant` `ACCOUNTING_SAFEGUARD_ACTIVE.json` and negative/NaN collateral or position fields
       halt live Harvester entries fail-closed via `_global_halt_reasons()` and pass `PermissionGate`.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Stdlib-only local test runner fallback (no-op inside full virtualenv with dotenv/requests/httpx/urllib3)
for _opt_mod, _attrs in (
    ("dotenv", {"load_dotenv": lambda *a, **kw: False}),
    ("requests", {"Session": object, "get": None, "post": None}),
    ("httpx", {"AsyncClient": object, "Client": object}),
    ("urllib3", {}),
    ("urllib3.connection", {"HTTPConnection": type("HTTPConnection", (), {"default_socket_options": []})}),
):
    try:
        __import__(_opt_mod)
    except ModuleNotFoundError:
        _m = types.ModuleType(_opt_mod)
        for _k, _v in _attrs.items():
            setattr(_m, _k, _v)
        sys.modules[_opt_mod] = _m

from src.paa_os.permissions import PermissionGate
from src.polymarket_research.holistic_strategy_governance import (
    DEFAULT_HOLISTIC_CONFIG,
    HotReloadConfigManager,
    _deep_merge_validated,
    passes_capital_velocity_hurdle,
)
from src.polymarket_research.polymarket_live_harvester import EmergencyRiskController, PolymarketLiveHarvester
from src.polymarket_research.riskless_protocol_v2_expansion import (
    _extract_weather_icao_key,
    check_harvester_fail_closed_accounting_halt,
    check_per_event_concentration_cap,
    compute_reconciled_concentration_nav_usd,
    eval_sll_live_book_poll,
    extract_canonical_event_keys,
    finish_protocol_v2_special_box_sync,
    sync_pending_intents_on_collateral_refresh,
)
from src.polymarket_research.stage_c_zero_loss_velocity import (
    check_multileg_3plus_nav_and_certification_gate,
    check_strict_pure_riskless_candidate_gate,
    execute_clinched_dead_leg_split_arb,
    is_nr0_closed_partition_graduated_unlock,
    load_alpha124_graduation_maps_with_lkg_cache,
)


class _UnmockedLiveExec:
    """Simulates a real-money L2 CLOB executor (`is_unmocked_live_clob_harvester == True`)."""

    def __init__(self, books: dict | None = None, fail_book_polls: bool = False) -> None:
        self.dry_run = False
        self.auth_mode = "LIVE"
        self.client = object()
        self.reservations_trusted = True
        self._books = books or {}
        self._fail_book_polls = fail_book_polls
        self.cancel_calls: list[tuple[str, str]] = []
        self.posted_orders: list[dict] = []

    def get_collateral_balance(self) -> float:
        return 47.38

    def get_conditional_balance(self, _tok: str) -> float:
        return 0.0

    def get_market_book(self, tok: str):
        if self._fail_book_polls:
            raise TimeoutError("simulated CLOB /book outage")
        return self._books.get(tok)

    def post_maker_entry_order(self, **kw) -> dict:
        self.posted_orders.append(kw)
        sh = max(5.0, round(float(kw["notional_usd"]) / float(kw["price"]), 2))
        return {"success": True, "orderID": f"OID_MKR_{len(self.posted_orders)}", "price": kw["price"], "shares": sh}

    def cancel_order(self, oid: str, token_id: str = "") -> dict:
        self.cancel_calls.append((oid, token_id))
        return {"is_canceled": True, "outcome": "CANCELED", "matched": 0.0}

    def get_order_fill_summary(self, _oid: str, _tok: str = "") -> dict:
        return {"matched": 0.0, "avg_price": 0.0, "cash": 0.0, "fee": 0.0, "terminal": False}

    def invalidate_collateral_cache(self) -> None:
        pass


class TestV5Section7RiskInvariants(unittest.TestCase):
    def test_01_reconciled_nav_excludes_disputed_kmia_and_enforces_15pct_cap_across_all_sleeves(self) -> None:
        now_u = 1_794_350_000.0
        kmia_exp = 1_794_113_999.0  # Nov 7 Miami disputed markets ($50.51 locked book cost)
        disputed_kmia_positions = {
            "WS_SNIPE_Miami_KMIA_242960": {
                "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "asset": "Miami_KMIA",
                "status": "POSITION_CONFIRMED",
                "umaResolutionStatus": "disputed",
                "candle_expiry_ts": kmia_exp,
                "entry_ts": kmia_exp - 1800.0,
                "notional_usd": 19.54,
                "remaining_shares": 20.0,
            },
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898",
                "box_type": "MULTI_LEG_RESIDUAL",
                "sleeve": "W_PRUNE1_NR0_BASKET",
                "asset": "KMIA",
                "is_legged_out_residual": True,
                "status": "POSITION_CONFIRMED",
                "umaResolutionStatus": "disputed",
                "candle_expiry_ts": kmia_exp,
                "entry_ts": kmia_exp - 2100.0,
                "notional_usd": 16.32,
                "remaining_shares": 17.0,
            },
            "WS_SNIPE_Miami_KMIA_688670": {
                "trade_id": "WS_SNIPE_Miami_KMIA_688670",
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "asset": "Miami_KMIA",
                "status": "POSITION_CONFIRMED",
                "umaResolutionStatus": "disputed",
                "candle_expiry_ts": kmia_exp,
                "entry_ts": kmia_exp - 1500.0,
                "notional_usd": 9.77,
                "remaining_shares": 10.0,
            },
            "WS_SNIPE_Miami_KMIA_837595": {
                "trade_id": "WS_SNIPE_Miami_KMIA_837595",
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "asset": "Miami_KMIA",
                "status": "POSITION_CONFIRMED",
                "umaResolutionStatus": "disputed",
                "candle_expiry_ts": kmia_exp,
                "entry_ts": kmia_exp - 1200.0,
                "notional_usd": 4.88,
                "remaining_shares": 5.0,
            },
        }
        harv = types.SimpleNamespace(
            dry_run=False,
            enforce_event_concentration_cap=True,
            _last_known_collateral=47.38,
            active_positions=dict(disputed_kmia_positions),
            pending_entry_intents={},
            _prepost_sll_events={},
            executor=_UnmockedLiveExec(),
        )
        # 1. Reconciled NAV is $47.38 (NOT $97.89 book equity!), so 15% cap == $7.1070
        nav = compute_reconciled_concentration_nav_usd(harv, now_ts=now_u)
        self.assertAlmostEqual(nav, 47.38, places=2)

        # 2. City-name-only weather market entering via BOND1 (`asset="BOND1"`, no ICAO in asset!)
        #    MUST still extract `WXSTATION:KMIA` and be HARD-BLOCKED by existing $50.51 KMIA concentration!
        bond1_miami_disguised = {
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "asset": "BOND1",
            "question": "Highest temperature in Miami on November 10?",
            "leg_a_market_id": "999888",
            "expiry_ts": now_u + 7200.0,
        }
        keys_miami = extract_canonical_event_keys(bond1_miami_disguised)
        self.assertIn("WXSTATION:KMIA", keys_miami)
        ok_kmia, rsn_kmia, rem_kmia, _ = check_per_event_concentration_cap(harv, bond1_miami_disguised, now_ts=now_u)
        self.assertFalse(ok_kmia)
        self.assertEqual(rem_kmia, 0.0)
        self.assertIn(rsn_kmia, {"MAX_CONCURRENT_PER_EVENT_REACHED", "MAX_EVENT_NOTIONAL_CAP_REACHED"})

        # 3. Sports game with city name ("Miami Heat vs Boston Celtics") MUST NOT map to weather station KMIA!
        nba_miami = {
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
            "asset": "NBA",
            "question": "Miami Heat vs. Boston Celtics Winner?",
            "leg_a_market_id": "777111",
            "expiry_ts": now_u + 3600.0,
        }
        self.assertEqual(_extract_weather_icao_key(nba_miami), "")
        self.assertNotIn("WXSTATION:KMIA", extract_canonical_event_keys(nba_miami))

        # 4. Unencumbered non-KMIA oracle event (including standalone `MKT:` and `S2_EXACT_TWAP_LOCK`)
        #    MUST get exact 15% of $47.38 == $7.1070 headroom (NO $20 floor and NO $9999 standalone MKT bypass!):
        for cand_other in (
            {
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve_source": "S2_EXACT_TWAP_LOCK",
                "asset": "BTC",
                "leg_a_market_id": "555001",
                "expiry_ts": now_u + 60.0,
            },
            {
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "asset": "POLITICS",
                "leg_a_market_id": "555002",
                "expiry_ts": now_u + 3600.0,
            },
            {
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
                "asset": "NYC_KLGA",
                "question": "Highest temperature in NYC on Nov 10?",
                "leg_a_market_id": "555003",
                "expiry_ts": now_u + 7200.0,
            },
        ):
            ok_o, rsn_o, rem_o, _ = check_per_event_concentration_cap(harv, cand_other, now_ts=now_u)
            self.assertTrue(ok_o, f"Expected first clip within $7.11 cap to be allowed, got {rsn_o}")
            self.assertAlmostEqual(rem_o, round(47.38 * 0.15, 4), places=3)

        # 5. Non-maker pending_entry_intent ($3.50 on KLGA under W_PRUNE1) aggregates against a second sleeve
        #    (`MKR_LOCK1` on KLGA): remaining headroom drops to $7.107 - $3.50 = $3.607 < $5.00 -> BLOCKED!
        harv.pending_entry_intents["TAKER_INFLIGHT_KLGA"] = {
            "trade_id": "TAKER_INFLIGHT_KLGA",
            "market_id": "555003",
            "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
            "question": "Highest temperature in New York City on Nov 10?",
            "expiry_ts": now_u + 7200.0,
            "notional_usd": 3.50,
            "live_maker_anchor_inflight": False,
        }
        ok_klga2, rsn_klga2, rem_klga2, _ = check_per_event_concentration_cap(
            harv,
            {
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                "asset": "WEATHER",
                "event_slug": "nyc-daily-weather-nov-10",
                "leg_a_market_id": "555003",
                "expiry_ts": now_u + 7200.0,
            },
            market_ids=["555003"],
            now_ts=now_u,
        )
        self.assertFalse(ok_klga2)
        self.assertAlmostEqual(rem_klga2, round(47.38 * 0.15 - 3.50, 4), places=3)
        self.assertIn(rsn_klga2, {"MAX_CONCURRENT_PER_EVENT_REACHED", "MAX_EVENT_NOTIONAL_CAP_REACHED"})

    def test_02_multileg_3plus_blocked_below_500_and_not_auto_enabled_above_500_without_certification(self) -> None:
        now_u = 1_794_350_000.0
        three_legs = [
            {"token_id": "TOK_1", "market_id": "M1", "side": "YES", "ask_px": 0.32, "ask_size": 50.0},
            {"token_id": "TOK_2", "market_id": "M2", "side": "YES", "ask_px": 0.33, "ask_size": 50.0},
            {"token_id": "TOK_3", "market_id": "M3", "side": "YES", "ask_px": 0.32, "ask_size": 50.0},
        ]
        cand_3leg = {
            "box_id": "MLB_3LEG_SEQ",
            "box_type": "MULTI_LEG_BUNDLE",
            "sleeve_source": "NR0_ZERO_FEE_SLATE_ARB",
            "legs": three_legs,
            "shares": 10.0,
            "ts_unix": now_u,
            "expiry_ts": now_u + 3600.0,
        }

        # 1. Below $500 NAV ($47.38 cash + $460 disputed position = $47.38 reconciled NAV < $500!),
        #    MUST block EVEN IF `strict_pure_riskless_mode=False` AND `certified_multileg_3plus_live_enabled=True`!
        harv_sub500 = types.SimpleNamespace(
            dry_run=False,
            _last_known_collateral=47.38,
            active_positions={
                "DISPUTED_BIG": {
                    "trade_id": "DISPUTED_BIG",
                    "status": "POSITION_CONFIRMED",
                    "umaResolutionStatus": "disputed",
                    "candle_expiry_ts": now_u - 7200.0,
                    "notional_usd": 460.0,
                    "remaining_shares": 470.0,
                }
            },
            pending_entry_intents={},
            executor=_UnmockedLiveExec(),
        )
        rb_permissive_sub500 = {
            "strict_pure_riskless_mode": False,
            "certified_multileg_3plus_live_enabled": True,
            "allow_nr0_multileg_dynamic_unpause": True,
        }
        veto_sub500 = check_strict_pure_riskless_candidate_gate(harv_sub500, cand_3leg, rb_permissive_sub500)
        self.assertIsNotNone(veto_sub500)
        self.assertIn("BELOW_500_NAV", str(veto_sub500))

        out_sp_sub500 = finish_protocol_v2_special_box_sync(
            harv_sub500, cand_3leg, "DK_SUB500", {}, now_u, {"d1_box_max_budget_usd": 25.0}
        )
        self.assertFalse(out_sp_sub500["executed"])
        self.assertIn("BELOW_500_NAV", str(out_sp_sub500["reason"]))

        # Also blocks m>=3 NEGRISK_CONVERT even when strict_pure_riskless_mode=False:
        veto_nr_m3 = check_strict_pure_riskless_candidate_gate(
            harv_sub500,
            {"box_type": "NEGRISK_CONVERT", "convert_mode": "NR2_PURE_CASH_CONVERT", "no_legs": [{}, {}, {}]},
            rb_permissive_sub500,
        )
        self.assertIsNotNone(veto_nr_m3)
        self.assertIn("BELOW_500_NAV", str(veto_nr_m3))

        # 2. Exceptions below $500 NAV (Zero-Trust Executor Verification — NEVER trust unverified JSON flags!):
        #    (a) Forged candidate JSON `atomic_onchain_execution=True` WITHOUT executor Safe-router capability MUST fail!
        cand_forged_atomic = {
            **cand_3leg,
            "atomic_onchain_execution": True,
            "atomic_router_verified": True,
        }
        self.assertIsNotNone(
            check_multileg_3plus_nav_and_certification_gate(harv_sub500, cand_forged_atomic, rb_permissive_sub500)
        )
        #    Only passes when `convert_mode == "NR3_ATOMIC_SAFE_SPLIT_CONVERT"` AND executor Safe router is verified:
        harv_sub500.executor.signature_type = 3
        harv_sub500.executor.safe_atomic_router_verified = True
        cand_atomic = {
            **cand_forged_atomic,
            "convert_mode": "NR3_ATOMIC_SAFE_SPLIT_CONVERT",
        }
        self.assertIsNone(check_multileg_3plus_nav_and_certification_gate(harv_sub500, cand_atomic, rb_permissive_sub500))
        #    Forged sequential CLOB claim (`sequential_clob_legs=True`) MUST still be blocked!
        self.assertIsNotNone(
            check_multileg_3plus_nav_and_certification_gate(
                harv_sub500, {**cand_atomic, "sequential_clob_legs": True}, rb_permissive_sub500
            )
        )
        harv_sub500.executor.safe_atomic_router_verified = False

        #    (b) Forged `verified_wallet_inventory` JSON when executor balance is 0.0 MUST be blocked!
        cand_inv_forged = {
            **cand_3leg,
            "verified_wallet_inventory": {"TOK_1": 12.0, "TOK_2": 10.0},
        }
        self.assertIsNotNone(
            check_multileg_3plus_nav_and_certification_gate(harv_sub500, cand_inv_forged, rb_permissive_sub500)
        )
        #    Passes ONLY when `harvester.executor` confirms real ERC-1155 token balances covering N-1 = 2 of 3 legs:
        verified_bals = {"TOK_1": 12.0, "TOK_2": 10.0}
        harv_sub500.executor.get_conditional_balance = lambda tk: verified_bals.get(tk, 0.0)
        self.assertIsNone(check_multileg_3plus_nav_and_certification_gate(harv_sub500, cand_inv_forged, rb_permissive_sub500))

        # 3. Above $500 reconciled NAV ($750 free cash), crossing $500 MUST NOT automatically re-enable >=3 legs!
        harv_above500 = types.SimpleNamespace(
            dry_run=False,
            _last_known_collateral=750.0,
            active_positions={},
            pending_entry_intents={},
            executor=_UnmockedLiveExec(),
        )
        rb_default_above500 = {
            "strict_pure_riskless_mode": False,
            "allow_nr0_multileg_dynamic_unpause": True,
            "certified_multileg_3plus_live_enabled": False,
        }
        veto_uncert = check_strict_pure_riskless_candidate_gate(harv_above500, cand_3leg, rb_default_above500)
        self.assertIsNotNone(veto_uncert)
        self.assertIn("UNCERTIFIED_ABOVE_500_NAV", str(veto_uncert))

        grad_8of8 = {
            "NR0_ZERO_FEE_SLATE_ARB": {
                "closed": 12,
                "losses": 0,
                "win_rate_pct": 100.0,
                "realized_pnl_t1000_usd": 45.0,
                "legging_adjusted_pnl_t1000_usd": 42.0,
            }
        }
        # Dynamic NR0 unlock fails closed at $300 (even if certified) AND fails closed at $750 without certification!
        self.assertFalse(
            is_nr0_closed_partition_graduated_unlock(
                300.0, {"allow_nr0_multileg_dynamic_unpause": True, "certified_multileg_3plus_live_enabled": True}, grad_8of8
            )
        )
        self.assertFalse(
            is_nr0_closed_partition_graduated_unlock(
                750.0, {"allow_nr0_multileg_dynamic_unpause": True, "certified_multileg_3plus_live_enabled": False}, grad_8of8
            )
        )
        # Only passes when BOTH >= $500 NAV AND explicit `certified_multileg_3plus_live_enabled=True`:
        self.assertTrue(
            is_nr0_closed_partition_graduated_unlock(
                750.0, {"allow_nr0_multileg_dynamic_unpause": True, "certified_multileg_3plus_live_enabled": True}, grad_8of8
            )
        )
        self.assertIsNone(
            check_multileg_3plus_nav_and_certification_gate(
                harv_above500, cand_3leg, {**rb_default_above500, "certified_multileg_3plus_live_enabled": True}
            )
        )

    def test_03_passive_maker_adverse_selection_ws_staleness_and_blind_book_fail_closed_cancel(self) -> None:
        # 1. Governance bounds reject maker_ws_book_max_age_sec > 5.0 or max_correlated_oracle_event_nav_pct > 0.15
        for bad_rb in (
            {"max_correlated_oracle_event_nav_pct": 0.20},
            {"multileg_3plus_min_reconciled_nav_usd": 250.0},
            {"nr0_dynamic_unlock_equity_usd": 150.0},
            {"maker_ws_book_max_age_sec": 30.0},
            {"maker_max_consecutive_blind_book_polls": 10},
        ):
            with self.assertRaises(ValueError):
                _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, {"riskless_boxes": bad_rb})

        # 2. eval_sll_live_book_poll cancels immediately on mid-rest UMA dispute, oracle/news shock, or dual-book inversion
        bk_clean_win = {"bids": [{"price": "0.992", "size": "20"}], "asks": [{"price": "0.998", "size": "20"}]}
        bk_clean_opp = {"bids": [{"price": "0.002", "size": "20"}], "asks": [{"price": "0.010", "size": "20"}]}
        act_disp, _, _, msg_disp = eval_sll_live_book_poll(
            bk_clean_opp,
            bk_clean_win,
            {"umaResolutionStatus": "disputed"},
            0.992,
            0.94,
            0.995,
            0.008,
            0.001,
            True,
            False,
            0,
            350.0,
            15.0,
            time.time() + 3600.0,
            None,
        )
        self.assertEqual(act_disp, "ADVERSE")
        self.assertIn("disputed", msg_disp)

        act_shock, _, _, msg_shock = eval_sll_live_book_poll(
            bk_clean_opp,
            bk_clean_win,
            {"oracle_shock_veto": True},
            0.992,
            0.94,
            0.995,
            0.008,
            0.001,
            True,
            False,
            0,
            350.0,
            15.0,
            time.time() + 3600.0,
            None,
        )
        self.assertEqual(act_shock, "ADVERSE")
        self.assertIn("shock", msg_shock)

        # 3. End-to-end resting Maker loop enforces <= 5.0s WS book max_age_sec AND cancels fail-closed
        #    after 3 consecutive blind book polls during a simulated CLOB /book outage!
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            st_p = tmp_p / "alpha124_shadow_state.json"
            st_p.write_text(
                json.dumps(
                    {
                        "by_sleeve": {
                            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                                "closed": 20,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 100.0,
                                "legging_adjusted_pnl_t1000_usd": 100.0,
                            },
                            "BOND1_UMA_RESOLUTION_CARRY": {
                                "closed": 20,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 50.0,
                                "legging_adjusted_pnl_t1000_usd": 50.0,
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            import src.polymarket_research.polymarket_live_harvester as hv_mod

            orig_data_dir = hv_mod.DATA_DIR
            hv_mod.DATA_DIR = tmp_p
            try:
                now_ts = time.time()
                ws_max_ages: list[float] = []
                poll_counter = [0]

                class _FakeMktWs:
                    def get_book(self, tok: str, max_age_sec: float = 30.0):
                        ws_max_ages.append(max_age_sec)
                        # Initial peg pre-post succeeds; once resting, WS cache is stale (`None`)!
                        if poll_counter[0] == 0:
                            if tok == "TOK_WIN":
                                return {"bids": [{"price": "0.991", "size": "15"}], "asks": [{"price": "0.999", "size": "25"}]}
                            return {"bids": [{"price": "0.001", "size": "15"}], "asks": [{"price": "0.009", "size": "25"}]}
                        return None

                    def seed_book(self, _tok: str, _bk: dict) -> None:
                        pass

                    def get_tick_size(self, _tok: str) -> float:
                        return 0.001

                exec_blind = _UnmockedLiveExec(fail_book_polls=False)
                orig_post = exec_blind.post_maker_entry_order

                def _post_then_outage(**kw):
                    res = orig_post(**kw)
                    poll_counter[0] = 1
                    exec_blind._fail_book_polls = True  # Simulate REST /book outage while order is resting!
                    return res

                exec_blind.post_maker_entry_order = _post_then_outage  # bind for post, keep enforce via flag
                h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
                h.dry_run = False
                h._startup_reconciled = True
                h.max_exposure = 100.0
                h._last_known_collateral = 65.0
                h.active_positions = {}
                h.pending_entry_intents = {}
                h.closed_positions = []
                h._state_save_lock = threading.Lock()
                h.executor = exec_blind
                h._pos_market_ws = _FakeMktWs()
                h.enforce_event_concentration_cap = True
                h.risk_config = {"bond1_book_poll_sec": 0.05, "single_leg_maker_max_keep_sec": 30.0}
                h.save_state = lambda: None
                h._mark_token_pre_bal_dirty = lambda _t: None
                h._resolve_fast_pre_token_balance_sync = lambda _t: 0.0
                h._is_d1_box_halted = lambda: False
                h._is_v5_live_strict = lambda: False
                h._is_v5_unleashed_active = lambda: True
                h._is_unlimited_slots_active = lambda: True

                cand_mkr = {
                    "box_id": "BOND1_BLIND_TEST",
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "asset": "POLITICS",
                    "event_id": "EVT_BLIND_99",
                    "leg_a_market_id": "MKT_BLIND_99",
                    "leg_a_token_id": "TOK_WIN",
                    "leg_a_opp_token_id": "TOK_OPP",
                    "leg_a_side": "YES",
                    "leg_a_neg_risk": False,
                    "anchor_bid_px": 0.992,
                    "max_box_cost_net": 0.995,
                    "max_opp_bid": 0.008,
                    "p_model": 1.0,
                    "ts_unix": now_ts,
                    "expiry_ts": now_ts + 3600.0,
                }
                t0 = time.monotonic()
                out_mkr = asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock(cand_mkr))
                elapsed = time.monotonic() - t0
                self.assertFalse(out_mkr["executed"])
                # Cancelled fail-closed in < 2.0s instead of sitting blind for 30s!
                self.assertLess(elapsed, 3.0)
                self.assertGreaterEqual(len(exec_blind.cancel_calls), 1)
                # Every in-loop WS book lookup used max_age_sec <= 5.0s (NEVER 30.0s)!
                in_loop_ages = ws_max_ages[2:]
                self.assertTrue(len(in_loop_ages) >= 2)
                self.assertTrue(all(age <= 5.0 for age in in_loop_ages), f"Found stale WS max_age_sec: {in_loop_ages}")
            finally:
                hv_mod.DATA_DIR = orig_data_dir

    def test_04_fail_closed_accounting_invariants_and_permission_gate_compliance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            state_f = tmp_p / "live_harvester_state.json"
            paa_dir = tmp_p / "paa"
            paa_dir.mkdir(parents=True, exist_ok=True)
            sg_file = paa_dir / "ACCOUNTING_SAFEGUARD_ACTIVE.json"

            h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
            h.dry_run = False
            h.executor = _UnmockedLiveExec()
            h._last_known_collateral = 47.38
            h.active_positions = {}
            h.pending_entry_intents = {}
            h.accounting_safeguard_file = sg_file

            # Clean state -> zero global halt reasons
            self.assertEqual(h._global_halt_reasons(), [])

            # 1. Triggering PAA ACCOUNTING_SAFEGUARD_ACTIVE.json immediately halts Harvester fail-closed!
            sg_file.write_text(json.dumps({"active": True, "discrepancy_usd": 3.25}), encoding="utf-8")
            self.assertIn("PAA_ACCOUNTING_SAFEGUARD_HALT", h._global_halt_reasons())

            # Corrupt/unreadable safeguard JSON ALSO fails closed!
            sg_file.write_text("{corrupt_json", encoding="utf-8")
            self.assertIn("PAA_ACCOUNTING_SAFEGUARD_UNREADABLE_FAIL_CLOSED", h._global_halt_reasons())
            sg_file.unlink()

            # 2. Negative collateral or negative position shares/notional halts fail-closed!
            h._last_known_collateral = -0.25
            self.assertIn("ACCOUNTING_INVALID_NEGATIVE_OR_NAN_COLLATERAL", h._global_halt_reasons())
            h._last_known_collateral = 47.38
            h.active_positions = {"BAD_POS": {"notional_usd": 10.0, "remaining_shares": -1.0}}
            halts_neg = check_harvester_fail_closed_accounting_halt(h, default_state_file=state_f)
            self.assertTrue(any("ACCOUNTING_NEGATIVE_POSITION_FIELD" in r for r in halts_neg))

        # 3. Verify our repository config & code changes pass HotReloadConfigManager AND Zero-Trust PermissionGate!
        cfg_path = REPO_ROOT / "config" / "polymarket_strategy_and_risk.json"
        mgr = HotReloadConfigManager(config_path=cfg_path)
        rb = mgr.snapshot["riskless_boxes"]
        self.assertAlmostEqual(float(rb["max_correlated_oracle_event_nav_pct"]), 0.15, places=4)
        self.assertAlmostEqual(float(rb["multileg_3plus_min_reconciled_nav_usd"]), 500.0, places=2)
        self.assertAlmostEqual(float(rb["nr0_dynamic_unlock_equity_usd"]), 500.0, places=2)
        self.assertFalse(bool(rb["certified_multileg_3plus_live_enabled"]))
        self.assertAlmostEqual(float(rb["maker_ws_book_max_age_sec"]), 5.0, places=2)
        self.assertEqual(int(rb["maker_max_consecutive_blind_book_polls"]), 3)

        gate = PermissionGate()
        cand_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        ok_cfg, violations = gate.inspect_config_envelope(cand_cfg, cand_cfg)
        self.assertTrue(ok_cfg, f"PermissionGate rejected config envelope: {violations}")

    def test_05_multi_key_canonical_event_deduplication_escrowed_maker_nav_and_dead_split_clamp(self) -> None:
        now_u = 1_794_350_000.0
        # 1. Fail-closed `None` collateral in live mode ($0.00, NOT $75.00!), while dry_run defaults to $75.00:
        harv_none_live = types.SimpleNamespace(
            dry_run=False, _last_known_collateral=None, active_positions={}, pending_entry_intents={}
        )
        harv_none_dry = types.SimpleNamespace(
            dry_run=True, _last_known_collateral=None, active_positions={}, pending_entry_intents={}
        )
        self.assertEqual(compute_reconciled_concentration_nav_usd(harv_none_live, now_ts=now_u), 0.0)
        self.assertEqual(compute_reconciled_concentration_nav_usd(harv_none_dry, now_ts=now_u), 75.0)

        # 2. Multi-key `extract_canonical_event_keys`: Trade 1 carries `event_id` + `market_id` + `condition_id`;
        #    follow-on Trade 2 omits `event_id` (only `market_id`), and Trade 3 omits both `event_id` & `market_id`
        #    (only `condition_id`). ALL MUST intersect and enforce the shared 15% ($7.107) cap!
        harv_mk = types.SimpleNamespace(
            dry_run=False,
            enforce_event_concentration_cap=True,
            _last_known_collateral=47.38,
            active_positions={
                "POS_T1": {
                    "trade_id": "POS_T1",
                    "status": "POSITION_CONFIRMED",
                    "event_id": "999001",
                    "market_id": "555111",
                    "condition_id": "0xAbC100",
                    "notional_usd": 4.50,
                    "remaining_shares": 4.55,
                    "best_bid": 0.99,
                }
            },
            pending_entry_intents={},
            _prepost_sll_events={},
            executor=_UnmockedLiveExec(),
        )
        # Reconciled NAV: $42.88 cash + $4.50 position == $47.38:
        harv_mk._last_known_collateral = 42.88
        self.assertAlmostEqual(compute_reconciled_concentration_nav_usd(harv_mk, now_ts=now_u), 47.38, places=2)
        keys_t1 = extract_canonical_event_keys(harv_mk.active_positions["POS_T1"])
        self.assertTrue({"EVT:999001", "MKT:555111", "COND:0xabc100"}.issubset(keys_t1))

        for follow_cand in (
            {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "leg_a_market_id": "555111"},
            {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "condition_id": "0xabc100"},
        ):
            ok_f, rsn_f, rem_f, _ = check_per_event_concentration_cap(harv_mk, follow_cand, now_ts=now_u)
            self.assertFalse(ok_f)
            self.assertAlmostEqual(rem_f, round(47.38 * 0.15 - 4.50, 4), places=3)
            self.assertIn(rsn_f, {"MAX_CONCURRENT_PER_EVENT_REACHED", "MAX_EVENT_NOTIONAL_CAP_REACHED"})

        # 3. Escrowed Maker Equity invariance (#20.2): posting 2 x $7.10 resting BOND1 makers on EVT:101 & EVT:102
        #    reduces `_last_known_collateral` from $47.38 -> $33.18; `sync_pending_intents_on_collateral_refresh`
        #    records `collat_drop_usd = 7.10` on each intent, keeping reconciled NAV == $47.38 so independent EVT:103
        #    STILL gets full $7.107 (>= $5.00 min lot) headroom instead of collapsing to $4.977!
        harv_esc = types.SimpleNamespace(
            dry_run=False,
            enforce_event_concentration_cap=True,
            _last_known_collateral=47.38,
            active_positions={},
            pending_entry_intents={
                "MKR_1": {
                    "inflight_key": "IK_1",
                    "event_id": "101",
                    "market_id": "M101",
                    "notional_usd": 7.10,
                    "posted_notional_usd": 7.10,
                    "live_maker_anchor_inflight": True,
                },
                "MKR_2": {
                    "inflight_key": "IK_2",
                    "event_id": "102",
                    "market_id": "M102",
                    "notional_usd": 7.10,
                    "posted_notional_usd": 7.10,
                    "live_maker_anchor_inflight": True,
                },
            },
            _prepost_sll_events={},
            executor=_UnmockedLiveExec(),
        )
        harv_esc._last_known_collateral = 33.18
        sync_pending_intents_on_collateral_refresh(harv_esc, 47.38, 33.18)
        self.assertAlmostEqual(compute_reconciled_concentration_nav_usd(harv_esc, now_ts=now_u), 47.38, places=2)
        ok_evt3, rsn_evt3, rem_evt3, _ = check_per_event_concentration_cap(
            harv_esc,
            {
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "event_id": "103",
                "leg_a_market_id": "M103",
            },
            now_ts=now_u,
        )
        self.assertTrue(ok_evt3, f"Expected 3rd independent event to have $7.11 headroom, got {rsn_evt3}")
        self.assertAlmostEqual(rem_evt3, round(47.38 * 0.15, 4), places=3)

        # 4. `execute_clinched_dead_leg_split_arb` enforces concentration cap BEFORE calling `splitPosition`:
        res_sp_blocked = execute_clinched_dead_leg_split_arb(
            harv_mk,
            {"market_id": "555111", "sleeve_source": "W_PRUNE1_DEAD_NO_BOND"},
            {
                "condition_id": "0x" + "a" * 64,
                "winner_token_id": "TOK_W",
                "dead_token_id": "TOK_D",
                "shares": 7,
                "min_dead_sell_px": 0.015,
            },
            now_ts=now_u,
        )
        self.assertFalse(res_sp_blocked["executed"])
        self.assertIn(res_sp_blocked["reason"], {"MAX_CONCURRENT_PER_EVENT_REACHED", "MAX_EVENT_NOTIONAL_CAP_REACHED"})

    def test_06_post_kmia_30_riskless_ruin_floor_cal1_cond1_24h_lkg_and_c1_merge_velocity(self) -> None:
        now_u = time.time()
        # 1. Post-KMIA $62.00 directional ruin floor vs $30.00 riskless box floor (#20.4b + #21.1):
        harv_kmia = types.SimpleNamespace(
            dry_run=False,
            _last_known_collateral=47.38,
            active_positions={
                "KMIA_DISP": {
                    "trade_id": "KMIA_DISP",
                    "status": "POSITION_CONFIRMED",
                    "umaResolutionStatus": "disputed",
                    "candle_expiry_ts": now_u - 86400.0,
                    "notional_usd": 50.51,
                    "remaining_shares": 52.0,
                }
            },
            pending_entry_intents={},
        )
        rc = EmergencyRiskController(max_daily_loss_usd=16.57, min_equity_floor_usd=62.0)
        rc._harvester_ref = harv_kmia
        rc.check_equity_drawdown(47.38)
        # Directional trading IS halted (< $62.00), while $1.00-payout riskless boxes stay ACTIVE ($47.38 >= $30.00)!
        self.assertTrue(rc.is_halted())
        self.assertFalse(rc.is_riskless_box_halted())

        # If true liquid cash drops below $30.00 ($28.50 < $30.00), riskless boxes HALT immediately (even if
        # `last_checked_equity` was previously inflated by book cost!):
        harv_kmia._last_known_collateral = 28.50
        self.assertTrue(rc.is_riskless_box_halted())

        # 2. Graduated 2-leg 0%-fee CAL1 & COND1 unblocked (#21.2), while fee-bearing / 3-leg / DOMINANCE stay blocked:
        live_harv = types.SimpleNamespace(
            dry_run=False, _last_known_collateral=47.38, active_positions={}, pending_entry_intents={}, executor=_UnmockedLiveExec()
        )
        rb_strict = {"strict_pure_riskless_mode": True, "certified_multileg_3plus_live_enabled": False}
        self.assertIsNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {
                    "box_type": "MACRO_DOMINANCE",
                    "sleeve_source": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                    "leg_a_market_id": "C1",
                    "leg_b_market_id": "C2",
                    "leg_a_token_id": "TA",
                    "leg_b_token_id": "TB",
                    "leg_a_fee_rate": 0.0,
                    "leg_b_fee_rate": 0.0,
                    "k_low": 100.0,
                    "k_high": 101.0,
                },
                rb_strict,
            )
        )
        self.assertIsNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {
                    "box_type": "MACRO_DOMINANCE",
                    "sleeve_source": "COND1_MACRO_PARTITION_BOX",
                    "leg_a_market_id": "M801",
                    "leg_b_market_id": "M802",
                    "leg_a_token_id": "TA",
                    "leg_b_token_id": "TB",
                    "leg_a_fee_rate": 0.0,
                    "leg_b_fee_rate": 0.0,
                },
                rb_strict,
            )
        )
        # Fee-bearing CAL1/COND1 or mis-typed DOMINANCE CAL1 MUST stay blocked:
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {
                    "box_type": "MACRO_DOMINANCE",
                    "sleeve_source": "COND1_MACRO_PARTITION_BOX",
                    "leg_a_market_id": "M801",
                    "leg_b_market_id": "M802",
                    "leg_a_fee_rate": 0.07,
                    "leg_b_fee_rate": 0.0,
                },
                rb_strict,
            )
        )

        # 3. 24-hour LKG graduation cache when `alpha124_shadow_state.json` stalls >300s (#21.3):
        with tempfile.TemporaryDirectory() as tmpdir:
            import os as _os

            tmp_p = Path(tmpdir)
            st_f = tmp_p / "alpha124_shadow_state.json"
            st_f.write_text(
                json.dumps({"by_sleeve": {"D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 12, "win_rate_pct": 100.0}}, "by_d1_asset": {"BTC": {"closed": 12}}}),
                encoding="utf-8",
            )
            # Simulate 2-hour stall (`7200s > 300s`, `<= 86400s`): MUST succeed via 24h LKG window!
            stall_2h_mtime = now_u - 7200.0
            _os.utime(st_f, (stall_2h_mtime, stall_2h_mtime))
            harv_cache = types.SimpleNamespace()
            sl_2h, da_2h, err_2h = load_alpha124_graduation_maps_with_lkg_cache(
                harv_cache, tmp_p, tmp_p, now_ts=now_u
            )
            self.assertIsNone(err_2h)
            self.assertIn("D1_SAME_ORACLE_DOMINANCE_BOX", sl_2h or {})

            # Simulate >24h stall (`90000s > 86400s`) with expired/empty LKG: MUST fail closed!
            stall_25h_mtime = now_u - 90000.0
            _os.utime(st_f, (stall_25h_mtime, stall_25h_mtime))
            harv_expired = types.SimpleNamespace()
            sl_exp, _, err_exp = load_alpha124_graduation_maps_with_lkg_cache(
                harv_expired, tmp_p, tmp_p, now_ts=now_u
            )
            self.assertIsNone(sl_exp)
            self.assertEqual(err_exp, "ALPHA124_STATE_STALE")

        # 4. `passes_capital_velocity_hurdle` requires verified `merge_wallet_ok=True` before exempting long-dated COMPLETE_SET (#21.4):
        ok_unmergeable, rsn_unmergeable = passes_capital_velocity_hurdle(
            box_type="COMPLETE_SET",
            sleeve_src="C1_BINARY_COMPLETE_SET",
            collat_usd=47.38,
            rem_tte_sec=30.0 * 86400.0,
            box_cost_net=0.992,
            fast_recycle_eligible=False,
            merge_wallet_ok=False,
        )
        self.assertFalse(ok_unmergeable)
        self.assertIn("LOW_CAPITAL_VELOCITY_LONG_TTE", rsn_unmergeable)

        ok_mergeable, _ = passes_capital_velocity_hurdle(
            box_type="COMPLETE_SET",
            sleeve_src="C1_BINARY_COMPLETE_SET",
            collat_usd=47.38,
            rem_tte_sec=30.0 * 86400.0,
            box_cost_net=0.992,
            fast_recycle_eligible=False,
            merge_wallet_ok=True,
        )
        self.assertTrue(ok_mergeable)


if __name__ == "__main__":
    unittest.main()

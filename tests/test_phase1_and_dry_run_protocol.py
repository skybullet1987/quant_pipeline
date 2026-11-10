"""
Offline Unit & Regression Suite for Phase I Local Hardening (Actions #1, #2, #3, #5),
`P0 Gate 0` Jurisdiction Compliance Lock, and Ontario-Licensed Read-Only Adapters
(`tests/test_phase1_and_dry_run_protocol.py`).

Runs 100% offline with zero network calls and zero API credentials.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
import os
from pathlib import Path
import sys
import types
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Allow offline stdlib-only Python test runners to import modules that only use `requests`/`aiohttp` on live HTTP calls
for _opt_net_mod in ("requests", "aiohttp"):
    try:
        __import__(_opt_net_mod)
    except ImportError:
        _stub = types.ModuleType(_opt_net_mod)
        _stub.Session = object  # type: ignore[attr-defined]
        _stub.ClientSession = object  # type: ignore[attr-defined]
        sys.modules[_opt_net_mod] = _stub

import scripts.polymarket_daily_projections as daily_proj
import src.polymarket_research.alpha_124_shadow_daemon as a124
from src.polymarket_research.cross_venue_dry_run_protocol import (
    DRY_RUN_ONLY,
    JWTExpiryGuard,
    P0Gate0ComplianceError,
    evaluate_forecastex_coupon_bond_carry,
    evaluate_venus_vusdt_liquidity_guard,
    quantize_predict_1e18_order_amounts,
    verify_p0_gate_0_jurisdiction,
    verify_relay_rebalance_quote,
)
from src.polymarket_research.cross_venue_riskless_shadow import (
    compute_venue_taker_fee_usd,
    parse_forecastex_contract,
    parse_stx_ontario_market,
)
from src.polymarket_research.holistic_strategy_governance import HotReloadConfigManager, STRATEGY_CONFIG_PATH
from src.polymarket_research.stage_c_zero_loss_velocity import (
    PURE_RISKLESS_BLOCKED_SLEEVES,
    check_strict_pure_riskless_candidate_gate,
    resolve_dynamic_paused_riskless_sleeves,
)


class TestPhase1LocalActionsAndDryRunProtocol(unittest.TestCase):
    def test_action1_b4_wick_lock_quarantined_across_all_4_layers(self) -> None:
        os.environ.pop("PM_UNQUARANTINE_B4_WICK_LOCK", None)
        os.environ.pop("PM_QUARANTINE_LOSING_SLEEVES", None)
        self.assertIn("B4_TOUCHED_BARRIER_WICK_LOCK", a124.QUARANTINED_SHADOW_SLEEVES)
        self.assertTrue(a124.is_shadow_sleeve_quarantined("B4_TOUCHED_BARRIER_WICK_LOCK"))
        self.assertIn("B4_TOUCHED_BARRIER_WICK_LOCK", daily_proj.QUARANTINED_SLEEVES)
        self.assertFalse(
            any(g.get("sleeve") == "B4_TOUCHED_BARRIER_WICK_LOCK" for g in daily_proj.GRADUATION_SPECS)
        )
        self.assertIn("B4_TOUCHED_BARRIER_WICK_LOCK", PURE_RISKLESS_BLOCKED_SLEEVES)
        mgr = HotReloadConfigManager(config_path=STRATEGY_CONFIG_PATH)
        self.assertIn("B4_TOUCHED_BARRIER_WICK_LOCK", mgr.snapshot["riskless_boxes"]["paused_riskless_sleeves"])

    def test_action2_full_lifecycle_4h_candle_discovery_and_caching(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import resolve_active_4h_target_end_ts

        # Pick a timestamp ~2.5 hours (`9,000s`) before the next 4h ET close (well outside the final 15m window!)
        base_ts = 1794190000.0
        target_end_ts, rem_4h = resolve_active_4h_target_end_ts(base_ts)
        if rem_4h <= 1800.0:
            base_ts -= 5400.0
            target_end_ts, rem_4h = resolve_active_4h_target_end_ts(base_ts)
        self.assertGreater(rem_4h, 905.0)

        daemon = a124.Alpha124ShadowDaemon(single_scan=True)
        calls: list[str] = []
        end_iso = a124.datetime.fromtimestamp(target_end_ts, tz=a124.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        start_iso = a124.datetime.fromtimestamp(target_end_ts - 14400, tz=a124.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        async def _fake_fetch(url: str, timeout: float = 4.0):
            calls.append(url)
            if "btc-up-or-down-4h" in url:
                return [
                    {
                        "id": "ev4_early",
                        "slug": f"btc-updown-4h-{target_end_ts - 14400}",
                        "endDate": end_iso,
                        "markets": [
                            {
                                "id": "m4_early",
                                "conditionId": "0x" + "a" * 64,
                                "outcomes": '["Up","Down"]',
                                "clobTokenIds": '["u4e","d4e"]',
                                "eventStartTime": start_iso,
                                "endDate": end_iso,
                                "resolutionSource": "https://data.chain.link/streams/btc-usd",
                                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                                "feesEnabled": True,
                            }
                        ],
                    }
                ]
            return []

        daemon.fetch_json = _fake_fetch  # type: ignore[assignment]
        asyncio.run(daemon.discover_4h_dominance_pairs(base_ts))
        self.assertIn(f"BTC_4h_{target_end_ts}", daemon.s4h_candles)
        # Terminal 4h/15m dominance pairs must NOT be populated outside the final 15m window
        self.assertEqual(len(daemon.dominance_4h_pairs), 0)
        # Second call for cached BTC 4h candle should skip redundant BTC Gamma fetch
        prev_btc_calls = sum(1 for u in calls if "btc-up-or-down-4h" in u)
        asyncio.run(daemon.discover_4h_dominance_pairs(base_ts + 10.0))
        after_btc_calls = sum(1 for u in calls if "btc-up-or-down-4h" in u)
        self.assertEqual(prev_btc_calls, after_btc_calls)

    def test_action3_graduation_and_equity_gated_nr0_auto_unpause(self) -> None:
        rb_cfg = {
            "strict_pure_riskless_mode": True,
            "paused_riskless_sleeves": ["NR0_ZERO_FEE_SLATE_ARB", "B4_TOUCHED_BARRIER_WICK_LOCK"],
        }
        ungrad_map = {
            "NR0_ZERO_FEE_SLATE_ARB": {
                "closed": 4,
                "losses": 0,
                "win_rate_pct": 100.0,
                "realized_pnl_t1000_usd": 42.5,
                "legging_adjusted_pnl_t1000_usd": 41.0,
            }
        }
        grad_map = {
            "NR0_ZERO_FEE_SLATE_ARB": {
                "closed": 8,
                "losses": 0,
                "win_rate_pct": 100.0,
                "realized_pnl_t1000_usd": 88.0,
                "legging_adjusted_pnl_t1000_usd": 84.5,
            }
        }
        # Under strict_pure_riskless_mode default, multi-leg NR0 stays locked OFF even at >= $150!
        self.assertIn("NR0_ZERO_FEE_SLATE_ARB", resolve_dynamic_paused_riskless_sleeves(rb_cfg, 89.0, grad_map))
        self.assertIn("NR0_ZERO_FEE_SLATE_ARB", resolve_dynamic_paused_riskless_sleeves(rb_cfg, 165.0, ungrad_map))
        self.assertIn("NR0_ZERO_FEE_SLATE_ARB", resolve_dynamic_paused_riskless_sleeves(rb_cfg, 165.0, grad_map))
        # Explicit opt-in (`allow_nr0_multileg_dynamic_unpause=True`) + >= $150 + 8/8 0-loss graduated unpauses NR0 while keeping B4 paused
        rb_optin = dict(rb_cfg, allow_nr0_multileg_dynamic_unpause=True)
        eff = resolve_dynamic_paused_riskless_sleeves(rb_optin, 165.0, grad_map)
        self.assertNotIn("NR0_ZERO_FEE_SLATE_ARB", eff)
        self.assertIn("B4_TOUCHED_BARRIER_WICK_LOCK", eff)

        harv = types.SimpleNamespace(enforce_pure_riskless_mode=True)
        ok_cand = {
            "box_type": "MULTI_LEG_BUNDLE",
            "sleeve_source": "NR0_ZERO_FEE_SLATE_ARB",
            "nr0_graduated_unlock_verified": True,
            "neg_risk_augmented": False,
            "legs": [{"token_id": f"t{i}"} for i in range(4)],
        }
        # Blocked by default under strict_pure_riskless_mode; allowed only with explicit opt-in and closed <=6-leg partition
        self.assertIsNotNone(check_strict_pure_riskless_candidate_gate(harv, ok_cand, rb_cfg))
        self.assertIsNone(check_strict_pure_riskless_candidate_gate(harv, ok_cand, rb_optin))
        aug_cand = dict(ok_cand, neg_risk_augmented=True)
        self.assertIsNotNone(check_strict_pure_riskless_candidate_gate(harv, aug_cand, rb_optin))
        big_cand = dict(ok_cand, legs=[{"token_id": f"t{i}"} for i in range(8)])
        self.assertIsNotNone(check_strict_pure_riskless_candidate_gate(harv, big_cand, rb_optin))

    def test_action5_dry_run_protocol_precision_and_p0_gate_0_lock(self) -> None:
        self.assertTrue(DRY_RUN_ONLY)
        # P0 Gate 0 hard-blocks Ontario (`CA-ON`) non-dry-run on restricted offshore venues
        for restricted in ("polymarket", "predict_fun", "sx_bet", "limitless"):
            self.assertTrue(verify_p0_gate_0_jurisdiction(restricted, "CA-ON", dry_run=True))
            with self.assertRaises(P0Gate0ComplianceError):
                verify_p0_gate_0_jurisdiction(restricted, "CA-ON", dry_run=False)
        # Ontario-licensed venues (`forecastex`, `stx_ontario`) pass cleanly
        self.assertTrue(verify_p0_gate_0_jurisdiction("forecastex", "CA-ON", dry_run=False))
        self.assertTrue(verify_p0_gate_0_jurisdiction("stx_ontario", "CA-ON", dry_run=False))

        # Exact 10^18 FeeModuleV2 quantization (`100` sh @ `$0.99` w/ 10% invite discount -> `0.018` USD = `1.8e16` wei)
        q = quantize_predict_1e18_order_amounts(side="BUY", shares=Decimal("100"), price=Decimal("0.99"), fee_rate_bps=200)
        self.assertEqual(q.shares_1e18, 100 * 10**18)
        self.assertEqual(q.maker_amount_wei, 99 * 10**18)
        self.assertEqual(q.taker_fee_wei, 18 * 10**15)
        self.assertEqual(q.maker_fee_wei, 0)

        # 23h JWT rotation guard
        jwt_g = JWTExpiryGuard(issued_at_ts=1_000_000.0)
        self.assertFalse(jwt_g.needs_rotation(1_000_000.0 + 82_700.0))
        self.assertTrue(jwt_g.needs_rotation(1_000_000.0 + 82_800.0))

        # Venus vUSDT liquidity guard (`>85%` utilization blocked)
        self.assertTrue(
            evaluate_venus_vusdt_liquidity_guard(
                total_cash_usd=2_000_000.0, total_borrows_usd=5_000_000.0, clip_notional_usd=100.0
            ).safe_for_yield_collateral
        )
        self.assertFalse(
            evaluate_venus_vusdt_liquidity_guard(
                total_cash_usd=500_000.0, total_borrows_usd=5_000_000.0, clip_notional_usd=100.0
            ).safe_for_yield_collateral
        )

        # Relay.link quote guard (`<= 8 bps` & `>= 3x` arb gain)
        ok_q = verify_relay_rebalance_quote(
            amount_in_usd=200.0,
            amount_out_usd=199.95,
            origin_gas_usd=0.005,
            expected_recipient="0xAbCd1234",
            quoted_recipient="0xabcd1234",
            expected_arb_gain_usd=0.50,
        )
        self.assertTrue(ok_q.approved)
        self.assertAlmostEqual(ok_q.all_in_drag_bps, 2.75, places=2)
        bad_recipient = verify_relay_rebalance_quote(
            amount_in_usd=200.0,
            amount_out_usd=199.95,
            origin_gas_usd=0.005,
            expected_recipient="0xAbCd1234",
            quoted_recipient="0x99999999",
            expected_arb_gain_usd=0.50,
        )
        self.assertFalse(bad_recipient.approved)

    def test_ontario_licensed_forecastex_and_stx_adapters(self) -> None:
        fx = parse_forecastex_contract(
            {
                "conid": "FX-BOC-DEC26",
                "title": "Bank of Canada rate cut in Dec 2026",
                "yes_asks": [{"price": 0.97, "size": 50}],
                "no_asks": [{"price": 0.04, "size": 50}],
            }
        )
        self.assertIsNotNone(fx)
        assert fx is not None
        self.assertAlmostEqual(compute_venue_taker_fee_usd(fx, 10.0, 0.97), 0.10, places=4)
        carry = evaluate_forecastex_coupon_bond_carry(shares=100.0, entry_price=0.97, hold_days=14.0)
        self.assertTrue(carry["pure_riskless_profitable"])
        self.assertGreater(float(carry["net_profit_usd"]), 2.10)

        stx = parse_stx_ontario_market(
            {
                "market_id": "stx-raptors-celtics",
                "team_a": "Toronto Raptors",
                "team_b": "Boston Celtics",
                "game_ts": 1794200000,
                "sport": "nba",
                "team_a_asks": [(60.0, 40.0)],
                "team_b_asks": [(41.0, 40.0)],
            }
        )
        self.assertIsNotNone(stx)
        assert stx is not None
        # Canonicalized: Celtics (`YES`) < Raptors (`NO`)
        self.assertEqual(stx.yes_label, "Boston Celtics")
        self.assertAlmostEqual(stx.yes_asks[0].price, 0.41, places=4)
        # 2% winning-leg commission on 10 shares @ $0.41 -> 10 * 0.59 * 0.02 = $0.118
        self.assertAlmostEqual(compute_venue_taker_fee_usd(stx, 10.0, 0.41), 0.118, places=4)

    def test_d1_4h_dominance_box_deep_itm_complement_and_shadow_entry(self) -> None:
        import asyncio
        import tempfile
        from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon, TwapCandleMarketSpec, determine_dominance_legs

        with tempfile.TemporaryDirectory() as tmp:
            daemon = Alpha124ShadowDaemon(single_scan=True)
            daemon.open_positions.clear()
            daemon.entered_keys.clear()
            daemon._append_ledger = lambda *a, **kw: None  # type: ignore[method-assign]

            end_ts = 1_794_201_600.0
            m4 = TwapCandleMarketSpec(
                asset="BTC",
                horizon="4h",
                market_id="m4_btc_test",
                condition_id="0x" + "aa" * 32,
                title="Bitcoin Up or Down - 4h",
                start_ts=end_ts - 14400.0,
                end_ts=end_ts,
                start_iso="2026-11-09T08:00:00Z",
                end_iso="2026-11-09T12:00:00Z",
                up_token="tok_4h_up",
                down_token="tok_4h_down",
                fee_rate=0.07,
                fee_exponent=1.0,
                neg_risk=False,
                twap_lookback_sec=60,
                resolution_source="https://data.chain.link/streams/btc-usd",
            )
            m5 = TwapCandleMarketSpec(
                asset="BTC",
                horizon="5m",
                market_id="m5_btc_test",
                condition_id="0x" + "bb" * 32,
                title="Bitcoin Up or Down - 5m",
                start_ts=end_ts - 300.0,
                end_ts=end_ts,
                start_iso="2026-11-09T11:55:00Z",
                end_iso="2026-11-09T12:00:00Z",
                up_token="tok_5m_up",
                down_token="tok_5m_down",
                fee_rate=0.07,
                fee_exponent=1.0,
                neg_risk=False,
                twap_lookback_sec=60,
                resolution_source="https://data.chain.link/streams/btc-usd",
            )
            # 4h strike = $92,000, 5m strike = $90,500 -> corridor [90500, 92000]: 5M_UP + 4H_DOWN dominates!
            dom = determine_dominance_legs(m4, 92_000.0, m5, 90_500.0, min_corridor_bps=3.0)
            self.assertIsNotNone(dom)
            assert dom is not None
            leg_a, leg_b = dom["leg_a"], dom["leg_b"]

            # Exact live failure book state from kraken-finland (meeting Polymarket >= $1.00 per-leg CLOB minimum):
            # 5M_UP ask=0.060 (bid=0.050, opp 5M_DOWN bid=0.935, ask=0.945)
            # 4H_DOWN ask=0.922, bid=0.910 (deep ITM >= 0.88 -> dead complement 4H_UP has 0 bids & stale 0.990 ask,
            # which previously gave opp_ub_sum = 0.945 + 0.990 = 1.935 > 1.180 false-positive ANTI-BOX VETO!)
            books = {
                "tok_5m_up": {"bids": [{"price": "0.050", "size": "80"}], "asks": [{"price": "0.060", "size": "80"}]},
                "tok_5m_down": {"bids": [{"price": "0.935", "size": "80"}], "asks": [{"price": "0.945", "size": "80"}]},
                "tok_4h_down": {"bids": [{"price": "0.910", "size": "65"}], "asks": [{"price": "0.922", "size": "65"}]},
                "tok_4h_up": {"bids": [], "asks": [{"price": "0.990", "size": "10"}]},
            }

            async def _verify() -> None:
                ok_deep = await daemon._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=books)
                self.assertTrue(ok_deep, "Deep-ITM 4H_DOWN + 5M_UP box should pass CTF mirror anti-box check")

                # Verify genuine wrong-direction OTM+OTM anti-box (`5M_UP` + `4H_UP` both OTM) STILL fails closed!
                bad_leg_b = {**leg_b, "token_id": "tok_4h_up", "opp_token_id": "tok_4h_down", "label": "4H_UP"}
                ok_antibox = await daemon._passes_complement_anti_box_check(leg_a, bad_leg_b, prefetched_books=books)
                self.assertFalse(ok_antibox, "Genuine OTM+OTM anti-box must remain 100% blocked")

                # Verify T100 ($20) depth-capped shadow entry opens cleanly when $100 T1000 exceeds 35-share 4h depth
                opened = await daemon.open_shadow_dominance_box(
                    "BTC",
                    m4,
                    m5,
                    dom,
                    prefetched_books=(books[leg_a["token_id"]], books[leg_b["token_id"]]),
                    sleeve_override="D1_4H_DOMINANCE_BOX",
                    max_box_cost_override=0.995,
                )
                self.assertTrue(opened)
                self.assertEqual(len(daemon.open_positions), 1)

            asyncio.run(_verify())


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Unit & Adversarial Poison-Pill Test Suite for Red Team Audit (`tests/test_directional_alpha_red_team.py`).

Tests all 15 mandated failure modes (`RT-01` .. `RT-15`) using deterministic synthetic poison-pill
fixtures AND verifies live Dominus `RT-10` production isolation (`226/226` DEPLOY_MANIFEST SHA-256
parity, `KMIA` non-interference, and `PermissionGate.inspect_candidate_diff == (True, [])`).
"""

from __future__ import annotations

import math
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.directional_alpha.red_team_audit_suite import (
    DOMINUS_ACTUAL_CASH_USD,
    DOMINUS_GCP_VM_DAILY_COST_USD,
    audit_historical_sqlite_database,
    audit_shadow_sqlite_database,
    audit_thin_book_vbounce_microstructure,
    audit_trade_list_for_adversarial_flaws,
    benjamini_hochberg_fdr,
    detect_backward_terminal_censorship_bias,
    detect_post_clinch_price_tail,
    independent_cluster_bootstrap_and_dsr,
    independent_hold_to_settlement_net_pnl_per_share,
    independent_polymarket_tick_size,
    independent_pre_exit_net_pnl_per_share,
    independent_proper_scoring_metrics,
    independent_taker_fee_per_share,
    norm_cdf,
    norm_ppf,
    recompute_cost_stress_and_scoring,
    resolve_independent_v2_fee_rate,
    scan_python_ast_for_leakage_and_safety,
    simulate_tier1_48usd_realistic_account,
    split_trades_with_purging,
    verify_production_isolation_and_permission_gate,
)


class TestRedTeamAdversarialDetectors(unittest.TestCase):
    """Tests all 15 adversarial detectors (`RT-01` .. `RT-15`) and independent math engines."""

    def test_norm_ppf_and_cdf_analytical_inversion(self) -> None:
        for p in (0.001, 0.01, 0.025, 0.05, 0.25, 0.50, 0.75, 0.95, 0.975, 0.99, 0.999):
            z = norm_ppf(p)
            p_back = norm_cdf(z)
            self.assertAlmostEqual(p, p_back, places=7)
        self.assertAlmostEqual(norm_ppf(0.975), 1.95996398, places=6)

    def test_rt01_post_clinch_and_post_end_timestamp_leakage(self) -> None:
        # Game clinches at t=1000 (jumps 0.52 -> 0.992 and stays >= 0.99 until end_ts=5000)
        pts = [
            (100.0, 0.50),
            (500.0, 0.54),
            (1000.0, 0.992),
            (2000.0, 0.995),
            (3500.0, 0.998),
            (5200.0, 0.999),  # post-endDate tail point (> 5000 + 60)
        ]
        diag = detect_post_clinch_price_tail(pts, end_ts=5000.0, resolved_yes=1.0)
        self.assertTrue(diag["has_early_clinch"])
        self.assertEqual(diag["clinch_ts"], 1000.0)
        self.assertEqual(diag["post_end_points"], 1)

        # Trade entering at t=2500 (after clinch_ts=1000) and another at t=5100 (after end_ts=5000)
        trades = [
            {"market_id": "m1", "entry_ts": 2500.0, "end_ts": 5000.0, "entry_price": 0.994, "mid_price": 0.991, "fee_usd": 0.01, "net_pnl_usd": 0.03},
            {"market_id": "m1", "entry_ts": 5100.0, "end_ts": 5000.0, "entry_price": 0.998, "mid_price": 0.995, "fee_usd": 0.01, "net_pnl_usd": 0.01},
        ]
        rep = audit_trade_list_for_adversarial_flaws(trades, market_clinch_map={"m1": 1000.0})
        self.assertEqual(rep["rt01_post_clinch_entries"], 2)
        self.assertEqual(rep["rt01_post_end_entries"], 1)

    def test_rt02_midpoint_fill_and_unpenalized_maker_fabrication(self) -> None:
        trades = [
            # Poison pill 1: Taker fill at exact midpoint with 0 spread/slippage
            {"market_id": "m_taker", "entry_ts": 100.0, "end_ts": 900.0, "is_maker": False, "mid_price": 0.50, "entry_price": 0.50, "slippage_bps": 0.0, "fee_usd": 0.10},
            # Poison pill 2: Maker fill assuming 100% fill probability & 0 adverse selection
            {"market_id": "m_maker", "entry_ts": 100.0, "end_ts": 900.0, "is_maker": True, "fill_probability": 1.0, "adverse_selection_bps": 0.0, "entry_price": 0.49},
        ]
        rep = audit_trade_list_for_adversarial_flaws(trades)
        self.assertEqual(rep["rt02_zero_slippage_midpoint_taker_fills"], 1)
        self.assertEqual(rep["rt02_unpenalized_100pct_maker_fills"], 1)

    def test_rt03_dynamic_2026_fees_share_haircut_and_tick_quantization(self) -> None:
        # Crypto V2 fee at p=0.50: 0.07 * 0.5 * 0.5 = 0.0175/sh
        f_crypto = independent_taker_fee_per_share(0.50, 0.07, 1.0)
        self.assertAlmostEqual(f_crypto, 0.0175, places=6)
        # Crypto 15m parabolic exponent=2 fee at p=0.50: 0.25 * (0.25)^2 = 0.015625/sh
        f_15m = independent_taker_fee_per_share(0.50, 0.25, 2.0)
        self.assertAlmostEqual(f_15m, 0.015625, places=6)

        # Protocol V2 share-haircut settlement PnL: buying at p=0.50 with r=0.07 delivers 1 - 0.0175/0.50 = 0.965 shares!
        # Winning settlement proceeds = 0.965 -> Net PnL = 0.965 - 0.50 = +0.465 (NOT +0.4825!)
        win_pnl = independent_hold_to_settlement_net_pnl_per_share(
            entry_ask=0.50, resolved_payout=1.0, fee_schedule_rate=0.07, fee_exponent=1.0
        )
        self.assertAlmostEqual(win_pnl, 0.465, places=6)

        # Tick size rule: 0.01 in interior, 0.001 in tails <=0.04 or >=0.96
        self.assertEqual(independent_polymarket_tick_size(0.50), 0.01)
        self.assertEqual(independent_polymarket_tick_size(0.96), 0.001)
        self.assertEqual(independent_polymarket_tick_size(0.04), 0.001)

        # Trade omitting 2026 weather_fees (r=0.05) and claiming 0.4c edge on 0.01 tick
        trades = [
            {
                "market_id": "wx1",
                "category": "weather",
                "entry_ts": 100.0,
                "end_ts": 900.0,
                "entry_price": 0.50,
                "mid_price": 0.49,
                "p_model": 0.504,  # 0.4c < 1c tick!
                "shares": 20.0,
                "notional_usd": 10.0,
                "fee_usd": 0.0,  # Omitted 5% weather fee!
                "net_pnl_usd": 0.15,
            }
        ]
        rep = audit_trade_list_for_adversarial_flaws(trades)
        self.assertEqual(rep["rt03_undercharged_2026_fee_trades"], 1)
        self.assertEqual(rep["rt03_subtick_edge_trades"], 1)
        self.assertLess(rep["rt03_recomputed_2026_total_net_pnl_usd"], 0.0)

    def test_rt04_negative_semantics_and_placeholder_detection(self) -> None:
        trades = [
            {
                "market_id": "neg1",
                "question": "Will the Fed NOT cut rates in December?",
                "group_item_title": "Candidate B",
                "entry_ts": 100.0,
                "end_ts": 900.0,
                "entry_price": 0.45,
                "mid_price": 0.44,
                "fee_usd": 0.10,
            }
        ]
        rep = audit_trade_list_for_adversarial_flaws(trades)
        self.assertEqual(rep["rt04_negative_polarity_questions_traded"], 1)
        self.assertEqual(rep["rt04_augmented_placeholder_trades"], 1)

    def test_rt05_and_rt13_sqlite_provenance_and_survivorship_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_p = Path(tmp) / "poison_hist.sqlite3"
            conn = sqlite3.connect(str(db_p))
            conn.execute(
                "CREATE TABLE markets (market_id TEXT, category TEXT, volume_total REAL, resolved_outcome INTEGER, end_ts REAL, data_quality_class TEXT)"
            )
            conn.execute(
                "CREATE TABLE price_history (market_id TEXT, ts REAL, price REAL, data_quality_class TEXT)"
            )
            # Only high-volume markets + 1 post-endDate unflagged row
            conn.execute("INSERT INTO markets VALUES ('m1', 'politics', 250000.0, 1, 1000.0, 'OBSERVED_TRADE_OR_CLOB_SERIES')")
            conn.execute("INSERT INTO price_history VALUES ('m1', 500.0, 0.60, 'OBSERVED_TRADE_OR_CLOB_SERIES')")
            conn.execute("INSERT INTO price_history VALUES ('m1', 1500.0, 0.99, 'OBSERVED_TRADE_OR_CLOB_SERIES')")
            conn.commit()
            conn.close()

            res = audit_historical_sqlite_database(db_p)
            self.assertTrue(res["exists"])
            self.assertEqual(res["unflagged_post_end_price_rows"], 1)
            self.assertEqual(res["low_volume_lt_5k_count"], 0)

    def test_rt06_cluster_correlation_sqrt_n_inflation_exposed(self) -> None:
        # 50 correlated strikes across ONLY 5 BTC days (10 identical trades per BTC day):
        # 4 winning BTC days (+1.0 per trade) and 1 losing BTC day (-2.5 per trade)
        trades = []
        day_pnls = [1.0, 1.0, 1.0, 1.0, -2.5]
        for day_idx, pnl in enumerate(day_pnls):
            ts = 1760000000.0 + day_idx * 86400.0
            for k in range(20):
                trades.append(
                    {
                        "market_id": f"btc_d{day_idx}_k{k}",
                        "event_id": f"ev_btc_{day_idx}",
                        "category": "crypto",
                        "question": f"Will BTC close above {90000 + k*500}?",
                        "entry_ts": ts,
                        "resolution_ts": ts + 3600.0,
                        "net_pnl_usd": pnl,
                    }
                )
        stats_rep = independent_cluster_bootstrap_and_dsr(trades, total_trials_m=30, n_bootstrap=1000)
        self.assertEqual(stats_rep["n_trades"], 100)
        self.assertEqual(stats_rep["n_clusters"], 5)
        # Naive i.i.d. t-stat (>2.1) falsely claims p<0.05 significance over true 5-cluster t-stat (~0.43)!
        self.assertGreater(stats_rep["iid_t_stat"], 2.0)
        self.assertLess(stats_rep["cluster_t_stat"], 1.0)
        self.assertGreater(stats_rep["t_stat_inflation_ratio"], 4.0)
        # True 95% cluster bootstrap CI includes negative PnL!
        self.assertLess(stats_rep["cluster_ci95_total_pnl"][0], 0.0)

    def test_rt07_multiple_testing_fdr_and_ast_peeking_scanner(self) -> None:
        pvals = {f"null_{i}": 0.04 + 0.02 * i for i in range(20)}
        pvals["marginally_lucky"] = 0.012  # Would pass naive p<0.05, MUST fail BH-FDR across M=21!
        fdr = benjamini_hochberg_fdr(pvals, alpha=0.05)
        self.assertFalse(fdr["marginally_lucky"]["passes_bh_fdr_05"])
        self.assertFalse(fdr["marginally_lucky"]["passes_holm_05"])

        with tempfile.TemporaryDirectory() as tmp:
            bad_py = Path(tmp) / "leaky_model.py"
            bad_py.write_text(
                "import statistics\nx_mu = statistics.mean(full_sample_rows)\n",
                encoding="utf-8",
            )
            ast_rep = scan_python_ast_for_leakage_and_safety(bad_py)
            self.assertEqual(len(ast_rep["suspicious_peeking_lines"]), 1)

    def test_rt08_negative_skew_tail_blindness_and_uma_wipeout(self) -> None:
        # 19 wins of +$0.04 buying 96c contracts (+$0.76) vs 1 loss of -$0.96 -> Net -$0.20 despite 95% WR!
        trades = [
            {"event_id": f"e_{i}", "entry_ts": 1000.0 + i * 100, "resolution_ts": 1050.0 + i * 100, "entry_price": 0.96, "notional_usd": 9.60, "net_pnl_usd": 0.40}
            for i in range(19)
        ] + [
            {"event_id": "e_19", "entry_ts": 3000.0, "resolution_ts": 3050.0, "entry_price": 0.96, "notional_usd": 9.60, "net_pnl_usd": -9.60}
        ]
        rep = independent_cluster_bootstrap_and_dsr(trades, total_trials_m=10)
        self.assertAlmostEqual(rep["win_rate"], 0.95, places=4)
        self.assertLess(rep["total_net_pnl_usd"], 0.0)
        self.assertAlmostEqual(rep["loss_to_win_ratio"], 24.0, places=2)

    def test_rt09_tier1_48usd_lot_quantization_lockup_and_vm_hurdle(self) -> None:
        # 20 overlapping 14-day locked trades ($3.00 min lot each = $60 > $48.81 cash) -> locks cash & earns way below $0.8223/day VM cost!
        trades = [
            {
                "event_id": f"slow_{i}",
                "entry_ts": 1000.0 + i * 60.0,
                "exit_ts": 1000.0 + 14 * 86400.0,
                "entry_price": 0.60,
                "shares": 5.0,
                "notional_usd": 3.0,
                "net_pnl_usd": 0.15,
            }
            for i in range(20)
        ]
        sim = simulate_tier1_48usd_realistic_account(trades, starting_cash_usd=DOMINUS_ACTUAL_CASH_USD)
        self.assertGreater(sim["skipped_cash_locked_count"], 0)
        self.assertFalse(sim["clears_vm_hurdle_0822_per_day"])
        self.assertLess(sim["net_economic_pnl_after_vm_usd"], 0.0)
        self.assertAlmostEqual(DOMINUS_GCP_VM_DAILY_COST_USD, 0.8223, places=4)

    def test_rt11_rt12_rt14_boundary_straddle_pre_exit_and_brier_math(self) -> None:
        # RT-11 + RT-12 check
        trades = [
            {
                "market_id": "m_straddle",
                "entry_ts": 900.0,
                "exit_ts": 1100.0,
                "end_ts": 5000.0,
                "exit_reason": "STOP_OR_TP_PRE_EXIT",
                "exit_price": 1.0,  # Bogus settlement 1.0 used on early pre-resolution exit!
                "entry_price": 0.55,
                "mid_price": 0.54,
                "fee_usd": 0.15,
            }
        ]
        flaws = audit_trade_list_for_adversarial_flaws(trades, split_boundaries_ts=[1000.0])
        self.assertEqual(flaws["rt11_split_boundary_straddles"], 1)
        self.assertEqual(flaws["rt12_pre_exit_settlement_conflations"], 1)

        # Pre-exit round-trip PnL check (taker buy @ 0.50, taker sell @ 0.55 on r=0.04 politics_fees)
        rt_pnl = independent_pre_exit_net_pnl_per_share(
            entry_ask=0.50, exit_bid=0.55, fee_schedule_rate=0.04, fee_exponent=1.0
        )
        # Entry fee_ps=0.01 -> net_shares = 1 - 0.02 = 0.98; Exit fee_ps = 0.04*0.55*0.45 = 0.0099 -> net_exit = 0.5401
        # Proceeds = 0.98 * 0.5401 = 0.529298 -> Net PnL = +0.029298 (41.4% of gross 5c move eaten by 2-way taker fees!)
        self.assertAlmostEqual(rt_pnl, 0.029298, places=6)

        # RT-14 Proper scoring rules check
        cal_rows = [
            {"p_model": 0.75, "p_market": 0.50, "y_outcome": 1.0},
            {"p_model": 0.25, "p_market": 0.50, "y_outcome": 0.0},
        ]
        sc = independent_proper_scoring_metrics(cal_rows)
        self.assertAlmostEqual(sc["brier_model"], 0.0625, places=6)
        self.assertAlmostEqual(sc["brier_market"], 0.25, places=6)
        self.assertAlmostEqual(sc["brier_skill_score"], 0.75, places=6)
        self.assertLess(sc["logloss_model"], sc["logloss_market"])

    def test_rt01_backward_terminal_absorption_censorship_bias_detector(self) -> None:
        # Synthetic poison-pill matching FIND-RT01-001: pre-cutoff <=0.015 ticks censored on y=0 (leak_free=0)
        # while retained on y=1 comeback (leak_free=1)!
        poison_trajs = [
            {
                "market_id": f"loser_{i}",
                "safe_decision_cutoff_ts": 2000.0,
                "outcome_0_payout": 0.0,
                "points": [(500.0, 0.25, 1), (1000.0, 0.012, 0), (1500.0, 0.008, 0)],
            }
            for i in range(4)
        ] + [
            {
                "market_id": "comeback_1",
                "safe_decision_cutoff_ts": 2000.0,
                "outcome_0_payout": 1.0,
                "points": [(500.0, 0.25, 1), (1000.0, 0.012, 1), (1800.0, 0.99, 1)],
            }
        ]
        chk = detect_backward_terminal_censorship_bias(poison_trajs)
        self.assertTrue(chk["has_outcome_conditioned_censorship"])
        self.assertAlmostEqual(chk["censor_rate_y0"], 1.0, places=5)
        self.assertAlmostEqual(chk["censor_rate_y1"], 0.0, places=5)

        # Verify live remediated historical_dataset.sqlite3 has 0.0% outcome-conditioned censorship!
        live_hist = REPO_ROOT / "data" / "directional_alpha" / "historical_dataset.sqlite3"
        if live_hist.exists():
            db_res = audit_historical_sqlite_database(live_hist)
            self.assertFalse(db_res["backward_censorship_check"]["has_outcome_conditioned_censorship"])
            self.assertEqual(db_res["unflagged_post_end_price_rows"], 0)
            self.assertEqual(db_res["maker_base_fee_nonzero_count"], 0)
            self.assertGreater(db_res["void_50_50_count"], 100)
            self.assertGreater(db_res["disputed_or_frozen_count"], 15)

    def test_rt03_v2_1000_sentinel_fee_resolution_and_zero_fee_override(self) -> None:
        # base_fee=1000.0 is the V2 sentinel -> must resolve category curve (e.g. 0.04 politics), NEVER 0.10!
        r_pol = resolve_independent_v2_fee_rate(
            fee_rate_explicit=None, taker_base_fee_bps=1000.0, fees_enabled=True, category="politics"
        )
        self.assertAlmostEqual(r_pol, 0.04, places=6)
        r_zero = resolve_independent_v2_fee_rate(
            fee_rate_explicit=0.04, taker_base_fee_bps=1000.0, fees_enabled=False, category="politics"
        )
        self.assertEqual(r_zero, 0.0)

    def test_rt04_continuous_50_50_void_and_uma_dispute_payouts(self) -> None:
        # Buying NO at 0.90 on a 50-50 voided market loses -0.40/share (before fee)!
        void_pnl = independent_hold_to_settlement_net_pnl_per_share(
            entry_ask=0.90, resolved_payout=0.50, fee_schedule_rate=0.04, fee_exponent=1.0, is_maker_entry=True
        )
        self.assertAlmostEqual(void_pnl, -0.40, places=6)
        # Disputed conservative floor payout = 0.00 -> loses -0.90/share!
        disp_pnl = independent_hold_to_settlement_net_pnl_per_share(
            entry_ask=0.90, resolved_payout=0.00, fee_schedule_rate=0.04, fee_exponent=1.0, is_maker_entry=True
        )
        self.assertAlmostEqual(disp_pnl, -0.90, places=6)
        # Continuous Brier & LogLoss at y = 0.50
        sc_void = independent_proper_scoring_metrics([{"p_model": 0.50, "p_market": 0.90, "y_outcome": 0.50}])
        self.assertAlmostEqual(sc_void["brier_model"], 0.0, places=6)
        self.assertAlmostEqual(sc_void["brier_market"], 0.16, places=6)

    def test_rt10_shadow_sqlite_database_swapless_ram_and_kmia_audit(self) -> None:
        sh_path = REPO_ROOT / "data" / "directional_alpha" / "shadow_research.sqlite3"
        if sh_path.exists():
            sh_res = audit_shadow_sqlite_database(sh_path)
            self.assertTrue(sh_res["within_60mib_swapless_budget"], f"RSS exceeded 60 MiB: {sh_res}")
            self.assertTrue(sh_res["isolation_verified_flag"])
            self.assertEqual(sh_res["kmia_d001_shadow_touches"], 0)
            self.assertEqual(sh_res["nav_floor_le_mtb_violations"], 0)

    def test_rt11_and_rt15_purged_split_and_cost_stress_recomputation(self) -> None:
        raw_stream = [
            {"trade_id": "t1", "entry_ts": 500.0, "exit_ts": 800.0, "net_pnl_usd": 1.0},
            {"trade_id": "t_straddle", "entry_ts": 950.0, "exit_ts": 1050.0, "net_pnl_usd": 5.0},  # MUST BE PURGED!
            {"trade_id": "t_val", "entry_ts": 1100.0, "exit_ts": 1500.0, "entry_price": 0.50, "shares": 10.0, "notional_usd": 5.0, "spread_slippage_cost_usd": 0.20, "net_pnl_usd": 0.50, "model_prob_entry": 0.65, "market_mid_entry": 0.49, "outcome_binary": 1.0},
            {"trade_id": "t_hold", "entry_ts": 2100.0, "exit_ts": 2500.0, "entry_price": 0.50, "shares": 10.0, "notional_usd": 5.0, "spread_slippage_cost_usd": 0.20, "net_pnl_usd": 0.40, "model_prob_entry": 0.62, "market_mid_entry": 0.49, "outcome_binary": 1.0},
        ]
        sp = split_trades_with_purging(raw_stream, train_end_ts=1000.0, val_end_ts=2000.0)
        self.assertEqual(len(sp["train"]), 1)
        self.assertEqual(len(sp["oos_combined"]), 2)
        self.assertEqual(len(sp["holdout"]), 1)
        self.assertEqual(sp["purged_straddlers"][0]["count"], 1)

        stress = recompute_cost_stress_and_scoring(sp["oos_combined"])
        self.assertAlmostEqual(stress["net_pnl_1_0x_usd"], 0.90, places=4)
        self.assertAlmostEqual(stress["net_pnl_1_5x_usd"], 0.70, places=4)
        self.assertAlmostEqual(stress["net_pnl_2_0x_usd"], 0.50, places=4)
        self.assertTrue(stress["survives_2_0x_cost"])

    def test_rt10_live_production_manifest_and_permission_gate_clean(self) -> None:
        iso = verify_production_isolation_and_permission_gate(REPO_ROOT)
        self.assertTrue(iso["manifest_zero_diff"], f"Manifest drifted: {iso}")
        self.assertTrue(iso["riskless_only_mode_true"])
        self.assertTrue(iso["kmia_untouched_ok"])
        self.assertTrue(
            iso["permission_gate_ok"],
            f"PermissionGate failed across swarm files: {iso['permission_gate_violations']} | hits={iso['per_file_forbidden_pattern_hits']}",
        )

    def test_rt02_vbounce_quote_pull_and_thin_book_detector(self) -> None:
        price_series = {
            "mkt_vbounce": [
                (1000.0, 0.525),
                (4600.0, 0.185),  # 1-bar quote cancellation V-bounce (-34c jump)
                (8200.0, 0.515),  # immediate +33c snapback
            ]
        }
        trades = [
            {
                "trade_id": f"vb_{i}",
                "market_id": "mkt_vbounce",
                "event_id": f"ev_vb_{i}",
                "entry_ts": 4600.0,
                "exit_ts": 8200.0,
                "exit_type": "PRE_EXIT",
                "side": "YES",
                "entry_price": 0.195,
                "exit_price": 0.505,
                "shares": 25.0,
                "notional_usd": 4.875,
                "spread_slippage_cost_usd": 0.50,
                "net_pnl_usd": 7.75,
            }
            for i in range(12)
        ] + [
            {
                "trade_id": f"real_{i}",
                "market_id": f"mkt_real_{i}",
                "event_id": f"ev_real_{i}",
                "entry_ts": 5000.0,
                "exit_ts": 9000.0,
                "exit_type": "PRE_EXIT",
                "side": "YES",
                "entry_price": 0.50,
                "exit_price": 0.47,
                "shares": 10.0,
                "notional_usd": 5.0,
                "spread_slippage_cost_usd": 0.20,
                "net_pnl_usd": -0.30,
            }
            for i in range(20)
        ]
        vol_map = {"mkt_vbounce": 503.0, **{f"mkt_real_{i}": 20000.0 for i in range(20)}}
        rep = audit_thin_book_vbounce_microstructure(
            trades,
            price_series_by_mkt=price_series,
            market_vol_map=vol_map,
            total_trials_m=100,
        )
        self.assertEqual(rep["vbounce_1bar_count"], 12)
        self.assertEqual(rep["no_vbounce_count"], 20)
        self.assertLess(rep["no_vbounce_net_pnl_usd"], 0.0)
        self.assertLess(rep["thin_book_adjusted_net_pnl_usd"], 0.0)
        self.assertTrue(rep["is_vbounce_fragile"])

    def test_phase2_finland_shadow_deployment_unit_and_signal_isolation(self) -> None:
        from scripts.directional_alpha.deploy_directional_shadow_finland import (
            verify_local_isolation_and_gates,
        )
        from src.directional_alpha.live_shadow_signals import (
            LOCKED_SLEEVE_IDS,
            LiveDirectionalSignalSuite,
            LiveSignalConfig,
        )
        from src.paa_os.permissions import PermissionGate

        # 1. Verify isolated deployer manifest overlap == 0, CRLF == 0, PermissionGate == (True, [])
        iso_gate = verify_local_isolation_and_gates(normalize_lf=False)
        self.assertTrue(iso_gate["local_isolation_ok"])
        self.assertEqual(iso_gate["overlap_with_production_manifest"], 0)
        self.assertEqual(iso_gate["overlap_with_protected_files"], 0)
        self.assertEqual(iso_gate["crlf_bytes_total"], 0)
        self.assertTrue(iso_gate["permission_gate_clean"])

        # 2. Verify systemd unit swapless cgroup fence & zero EnvironmentFile
        unit_path = REPO_ROOT / "systemd" / "polymarket-directional-alpha-shadow.service"
        self.assertTrue(unit_path.exists())
        raw_unit = unit_path.read_bytes()
        self.assertNotIn(b"\r\n", raw_unit)
        unit_txt = raw_unit.decode("utf-8")
        self.assertNotIn("EnvironmentFile", unit_txt)
        for req_directive in (
            "Environment=PAA_SIGNING_DISABLED=1",
            "Environment=MALLOC_ARENA_MAX=2",
            "MemoryHigh=110M",
            "MemoryMax=140M",
            "MemorySwapMax=0",
            "OOMScoreAdjust=600",
            "ProtectSystem=strict",
            "ProtectHome=read-only",
            "ReadWritePaths=/home/skybullet1987/quant_pipeline/data/directional_alpha",
        ):
            self.assertIn(req_directive, unit_txt)

        # 3. Verify 7 locked sleeves & D-001 KMIA block in LiveDirectionalSignalSuite
        self.assertEqual(len(LOCKED_SLEEVE_IDS), 7)
        suite = LiveDirectionalSignalSuite(LiveSignalConfig(virtual_bankroll_usd=500.0))
        kmia_mkt = {
            "market_id": "6707503",
            "question": "Highest temperature in Miami (KMIA) on November 7?",
            "category": "weather",
            "volume_usd": 50000.0,
            "fees_enabled": False,
        }
        kmia_book = {
            "bids": [{"price": 0.45, "size": 500.0}],
            "asks": [{"price": 0.46, "size": 500.0}],
            "tick_size": 0.01,
        }
        for fn in suite.as_strategy_functions():
            intents = fn(kmia_mkt, kmia_book)
            self.assertEqual(intents, [])

        # 4. Verify ALL directional_alpha files (incl. systemd unit & FINLAND_SHADOW_DEPLOYMENT_AUDIT.md) pass PermissionGate
        pg = PermissionGate()
        all_files = []
        diff_parts = []
        for sub in (
            sorted((REPO_ROOT / "src" / "directional_alpha").glob("*.py")),
            sorted((REPO_ROOT / "scripts" / "directional_alpha").glob("*.py")),
            sorted((REPO_ROOT / "tests").glob("test_directional_alpha_*.py")),
            sorted((REPO_ROOT / "docs" / "directional_alpha").glob("*.md")),
            [unit_path],
        ):
            for fp in sub:
                if fp.exists():
                    rel = fp.relative_to(REPO_ROOT).as_posix()
                    all_files.append(rel)
                    added = "\n".join("+" + ln for ln in fp.read_text(encoding="utf-8").splitlines())
                    diff_parts.append(f"--- /dev/null\n+++ b/{rel}\n{added}\n")
        ok_pg, viols = pg.inspect_candidate_diff(all_files, "".join(diff_parts))
        self.assertTrue(ok_pg, f"PermissionGate violations across directional_alpha files: {viols}")
        self.assertEqual(viols, [])


if __name__ == "__main__":
    unittest.main()

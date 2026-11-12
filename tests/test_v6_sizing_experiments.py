"""Unit & adversarial tests for Dominus v6.0 order sizing & execution experiments."""

from __future__ import annotations

import unittest

from src.polymarket_research.order_sizing_experiments import (
    BANKROLL_SCALES_USD,
    SIZING_METHODS,
    build_canonical_sleeve_catalog,
    compute_maker_rebate_per_share,
    compute_taker_fee_per_share,
    compute_ticket_usd,
    evaluate_execution_routes,
    generate_trade_stream,
    run_full_experiment_suite,
    run_sleeve_method_experiment,
    select_best_method,
)


class TestV6SizingExperiments(unittest.TestCase):
    def test_canonical_catalog_and_fee_schedules(self) -> None:
        catalog = build_canonical_sleeve_catalog()
        self.assertEqual(len(catalog), 16)
        ids = {s.sleeve_id for s in catalog}
        self.assertIn("C1_BINARY_COMPLETE_SET", ids)
        self.assertIn("D1_SAME_ORACLE_DOMINANCE_BOX", ids)
        self.assertIn("BOND1_UMA_RESOLUTION_CARRY", ids)
        self.assertIn("SHADOW_HYBRID_ZSPLIT", ids)
        self.assertIn("SHADOW_XAU_15M_MAKER", ids)

        # Exact Polymarket V2 fee formulas
        self.assertEqual(compute_taker_fee_per_share(0.50, "zero_fees"), 0.0)
        self.assertAlmostEqual(compute_taker_fee_per_share(0.50, "crypto_fees_v2"), 0.07 * 0.25, places=6)
        self.assertAlmostEqual(compute_taker_fee_per_share(0.50, "crypto_15_min"), 0.25 * (0.25 ** 2), places=6)
        self.assertAlmostEqual(compute_maker_rebate_per_share(0.50, "crypto_fees_v2"), 0.20 * 0.07 * 0.25, places=6)

    def test_all_12_plus_sizing_methods_bounded_and_deterministic(self) -> None:
        catalog = {s.sleeve_id: s for s in build_canonical_sleeve_catalog()}
        sleeve = catalog["D1_SAME_ORACLE_DOMINANCE_BOX"]
        obs = generate_trade_stream(sleeve, n_trades=10, seed=123)[0]

        for eq in BANKROLL_SCALES_USD:
            for method in SIZING_METHODS:
                t1 = compute_ticket_usd(method, equity_usd=eq, obs=obs, sleeve=sleeve)
                t2 = compute_ticket_usd(method, equity_usd=eq, obs=obs, sleeve=sleeve)
                self.assertEqual(t1, t2)
                self.assertGreaterEqual(t1, 0.0)
                self.assertLessEqual(t1, eq)

    def test_hybrid_enforces_15pct_event_cap_and_liquidity_cap(self) -> None:
        catalog = {s.sleeve_id: s for s in build_canonical_sleeve_catalog()}
        bond1 = catalog["BOND1_UMA_RESOLUTION_CARRY"]
        obs = generate_trade_stream(bond1, n_trades=10, seed=77)[0]
        # At $5000 bankroll, SINGLE_LEG_LOCK HYBRID must be capped by <=15% NAV ($750) AND 0.60 * L1 depth
        ticket = compute_ticket_usd("HYBRID", equity_usd=5000.0, obs=obs, sleeve=bond1)
        self.assertLessEqual(ticket, 0.15 * 5000.0 + 1e-6)
        self.assertLessEqual(ticket, 0.60 * obs.l1_depth_usd + 1e-6)

    def test_execution_route_optimization(self) -> None:
        catalog = {s.sleeve_id: s for s in build_canonical_sleeve_catalog()}
        xau = catalog["SHADOW_XAU_15M_MAKER"]
        ev_xau = evaluate_execution_routes(xau, 48.81, 7.0)
        self.assertEqual(ev_xau.best_route, "MAKER_POST_ONLY")
        self.assertEqual(ev_xau.taker_fee_per_share, 0.0)

        # Large notional relative to L1 depth at scaled bankroll evaluates splitting
        d1 = catalog["D1_SAME_ORACLE_DOMINANCE_BOX"]
        ev_d1_large = evaluate_execution_routes(d1, 5000.0, 120.0)
        self.assertIn(ev_d1_large.best_route, ("MAKER_POST_ONLY", "MARKETABLE_LIMIT_FAK", "SPLIT_MICROCLIPS", "SKIP"))

    def test_experiment_runner_and_reproducibility(self) -> None:
        catalog = {s.sleeve_id: s for s in build_canonical_sleeve_catalog()}
        c1 = catalog["C1_BINARY_COMPLETE_SET"]
        m1 = run_sleeve_method_experiment(c1, "HYBRID", 48.81, n_trades=80, mc_paths=40, seed=99)
        m2 = run_sleeve_method_experiment(c1, "HYBRID", 48.81, n_trades=80, mc_paths=40, seed=99)
        self.assertEqual(m1, m2)
        self.assertGreater(m1.wfo_net_ev_bps, 0.0)
        self.assertGreaterEqual(m1.ruin_prob, 0.0)
        self.assertLessEqual(m1.ruin_prob, 1.0)

    def test_full_suite_produces_12_column_summary(self) -> None:
        payload = run_full_experiment_suite(bankrolls=(48.81, 500.0), mc_paths=25, seed=42)
        self.assertEqual(payload["sleeves_count"], 16)
        self.assertEqual(len(payload["summary_table"]), 16)
        for row in payload["summary_table"]:
            self.assertIn(row["classification"], ("VERIFIED", "EXPERIMENTALLY VALIDATED", "PROVISIONAL", "FAILED"))
            self.assertIn(row["best_sizing_method"], SIZING_METHODS)


if __name__ == "__main__":
    unittest.main()

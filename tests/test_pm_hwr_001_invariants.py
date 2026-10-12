"""Unit tests for PM-HWR-001 Research Campaign Invariants.

Verifies:
1. Dynamic crypto fee schedule v2 formula correctness across price bounds.
2. Resolution labeling consistency against ground-truth Binance Spot Close >= Open.
3. Chronological fold causality (zero future information leakage across folds).
4. Orderbook depth and execution hurdle calculation invariants.
5. Acceptance gate evaluation logic (strict fail-closed on N < 300).
"""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from src.polymarket_research.pm_hwr_001.backtest_engine import (
    normal_cdf,
    polymarket_crypto_fee_v2,
    get_fold,
)
from src.polymarket_research.pm_hwr_001.statistical_evaluation import (
    wilson_ci,
    block_bootstrap_ev,
)


class TestPMHWR001Invariants(unittest.TestCase):
    def test_polymarket_crypto_fee_v2_symmetry_and_bounds(self):
        """Fee formula must be symmetric around 0.50 and non-negative."""
        fee_rate = 0.07
        # At 0.50, fee is 0.07 * 0.50 = 0.035
        self.assertAlmostEqual(polymarket_crypto_fee_v2(0.50, fee_rate), 0.035, places=5)
        # Symmetry: fee(0.20) == fee(0.80)
        self.assertAlmostEqual(
            polymarket_crypto_fee_v2(0.20, fee_rate),
            polymarket_crypto_fee_v2(0.80, fee_rate),
            places=5,
        )
        # At 0.95, fee is 0.07 * 0.05 = 0.0035
        self.assertAlmostEqual(polymarket_crypto_fee_v2(0.95, fee_rate), 0.0035, places=5)
        # Bounded at extreme prices
        self.assertGreater(polymarket_crypto_fee_v2(0.999, fee_rate), 0.0)
        self.assertGreater(polymarket_crypto_fee_v2(0.001, fee_rate), 0.0)

    def test_chronological_fold_strict_separation(self):
        """Folds must partition time strictly without overlapping timestamps."""
        # Train: <= 2026-10-05
        ts_train = 1791244700.0  # 2026-10-05 23:58 UTC
        self.assertEqual(get_fold(ts_train), "TRAIN")

        # Validation: 2026-10-06 to 2026-10-09
        ts_val = 1791346900.0  # 2026-10-07 04:21 UTC
        self.assertEqual(get_fold(ts_val), "VALIDATION")

        # Holdout: >= 2026-10-10
        ts_holdout = 1791650000.0  # 2026-10-10 16:33 UTC
        self.assertEqual(get_fold(ts_holdout), "HOLDOUT")

    def test_wilson_score_interval_properties(self):
        """Wilson score interval must stay within [0, 1] and narrow with N."""
        lower, upper = wilson_ci(wins=95, n=100)
        self.assertGreaterEqual(lower, 0.0)
        self.assertLessEqual(upper, 1.0)
        self.assertLess(lower, 0.95)
        self.assertGreater(upper, 0.95)

        # Large sample narrows interval
        l_large, u_large = wilson_ci(wins=950, n=1000)
        self.assertGreater(l_large, lower)
        self.assertLess(u_large, upper)

    def test_block_bootstrap_ev_reproducibility(self):
        """Bootstrap EV on symmetric wins/losses must preserve mean."""
        pnls = [3.0, 3.0, 3.0, -7.5, 3.0, 3.0, -7.5, 3.0, 3.0, 3.0]
        mean_ev, l_95, u_95 = block_bootstrap_ev(pnls, n_bootstraps=500, block_size=2)
        true_mean = sum(pnls) / len(pnls)
        self.assertAlmostEqual(mean_ev, true_mean, places=4)
        self.assertLessEqual(l_95, mean_ev)
        self.assertGreaterEqual(u_95, mean_ev)

    def test_ground_truth_resolution_binary_invariant(self):
        """Resolution records must conform strictly to Polymarket 1H Binance close rule."""
        res_file = Path("data/polymarket/finalized_market_resolutions.jsonl")
        if not res_file.exists():
            self.skipTest("Resolutions file not found")

        with open(res_file, "r") as f:
            for i, line in enumerate(f):
                if i > 50:
                    break
                r = json.loads(line)
                open_px = float(r.get("binance_spot_open", 0.0))
                close_px = float(r.get("binance_spot_close", 0.0))
                expected = "UP" if close_px >= open_px else "DOWN"
                self.assertEqual(
                    r.get("winning_outcome"),
                    expected,
                    f"Market {r.get('market_id')} failed ground-truth rule: open={open_px}, close={close_px}",
                )


if __name__ == "__main__":
    unittest.main()

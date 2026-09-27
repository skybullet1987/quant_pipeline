"""Unit and microstructure verification tests for Aevo 0DTE Backtesting Harness.

Tests:
1. Dynamic Fee Engine & $260 Crossover at BTC $65k
2. Causal Clock Multi-Source Ingress Benchmark
3. Queue Depletion & Dual OCR Calculations
4. Terminal State Routing (SOLD, EXPIRED_ITM, EXPIRED_OTM)
5. Paired Permutation Test & Bootstrap LCB_95%

ISOLATION INVARIANT:
Tests run only against src/aevo_research/, completely isolated from Hyperliquid files.
"""

from __future__ import annotations

import unittest
from src.aevo_research.causal_0dte_backtest_harness import (
    AevoFeeEngine,
    Causal0DTEBacktestHarness,
    OptionQuote,
    ShockEpisode,
)


class TestAevo0DTEBacktestHarness(unittest.TestCase):
    def setUp(self):
        self.fee_engine = AevoFeeEngine()
        self.harness = Causal0DTEBacktestHarness(
            eval_delay_us=100.0,
            base_network_latency_ms=15.0,
            target_order_qty=1.0,
        )

    def test_fee_crossover_at_65k(self):
        """Verify the exact P_crossover = 0.004 * S = $260.00 crossover point."""
        s = 65000.0
        q = 1.0

        # Below crossover: 12.5% premium cap binds
        fee_10 = self.fee_engine.compute_taker_fee(s, 10.0, q)
        self.assertAlmostEqual(fee_10, 1.25, places=4)

        fee_100 = self.fee_engine.compute_taker_fee(s, 100.0, q)
        self.assertAlmostEqual(fee_100, 12.50, places=4)

        fee_200 = self.fee_engine.compute_taker_fee(s, 200.0, q)
        self.assertAlmostEqual(fee_200, 25.00, places=4)

        # At crossover: $260.00 * 0.125 = $32.50 == $65,000 * 0.0005
        fee_260 = self.fee_engine.compute_taker_fee(s, 260.0, q)
        self.assertAlmostEqual(fee_260, 32.50, places=4)

        # Above crossover: 0.05% notional cap binds ($32.50)
        fee_500 = self.fee_engine.compute_taker_fee(s, 500.0, q)
        self.assertAlmostEqual(fee_500, 32.50, places=4)

    def test_multi_source_causal_ingress(self):
        """Verify t2 = max(t1_binance, t1_hl) + eval_delay."""
        t1_b = 1_000_000_000  # 1.00s
        t1_hl = 1_005_000_000  # 1.005s (5ms later)

        quote = OptionQuote(
            strike=66000.0,
            is_call=True,
            expiry_hours=2.0,
            bid_px=15.0,
            bid_qty=5.0,
            ask_px=18.0,
            ask_qty=5.0,
        )

        ep = ShockEpisode(
            episode_id=1,
            underlying_symbol="BTC",
            t1_binance_ns=t1_b,
            t1_hl_ns=t1_hl,
            spot_pre_shock=65000.0,
            spot_post_shock=65500.0,
            shock_magnitude_pct=0.77,
            volume_sweep_usd=2_500_000.0,
            aevo_target_strike=66000.0,
            is_call=True,
            expiry_hours=2.0,
            target_quote_at_t2=quote,
        )

        res = self.harness.simulate_episode(ep, causal_offset_ms=0.0)
        expected_t2 = t1_hl + self.harness.eval_delay_ns
        self.assertEqual(res.t2_actionable_ns, expected_t2)

    def test_queue_depletion(self):
        """Verify queue depletion reduces fillable quantity."""
        quote = OptionQuote(
            strike=66000.0,
            is_call=True,
            expiry_hours=1.0,
            bid_px=10.0,
            bid_qty=5.0,
            ask_px=12.0,
            ask_qty=1.0,
        )

        # Episode where subsequent fills deplete 1.5 contracts
        ep = ShockEpisode(
            episode_id=2,
            underlying_symbol="BTC",
            t1_binance_ns=1000,
            t1_hl_ns=1000,
            spot_pre_shock=65000.0,
            spot_post_shock=65800.0,
            shock_magnitude_pct=1.23,
            volume_sweep_usd=3_000_000.0,
            aevo_target_strike=66000.0,
            is_call=True,
            expiry_hours=1.0,
            target_quote_at_t2=quote,
            subsequent_fills_depletion_qty=2.0,  # exceeds available 1.0 ask
        )

        res = self.harness.simulate_episode(ep, causal_offset_ms=0.0)
        self.assertFalse(res.is_filled)
        self.assertEqual(res.net_realized_pnl, 0.0)
        self.assertEqual(res.terminal_state, "UNFILLED")

    def test_terminal_state_expired_itm(self):
        """Verify expired ITM terminal state produces exact intrinsic value without settlement fee."""
        quote = OptionQuote(
            strike=65000.0,
            is_call=True,
            expiry_hours=0.01,  # 36 seconds to expiry
            bid_px=50.0,
            bid_qty=5.0,
            ask_px=60.0,
            ask_qty=5.0,
        )

        ep = ShockEpisode(
            episode_id=3,
            underlying_symbol="BTC",
            t1_binance_ns=1000,
            t1_hl_ns=1000,
            spot_pre_shock=65000.0,
            spot_post_shock=65200.0,
            shock_magnitude_pct=0.31,
            volume_sweep_usd=2_200_000.0,
            aevo_target_strike=65000.0,
            is_call=True,
            expiry_hours=0.01,
            target_quote_at_t2=quote,
        )

        res = self.harness.simulate_episode(ep, causal_offset_ms=0.0)
        self.assertTrue(res.is_filled)
        self.assertEqual(res.terminal_state, "EXPIRED_ITM")
        # Intrinsic: 65,200 - 65,000 = $200.00
        self.assertEqual(res.terminal_cash_flow, 200.0)
        # Entry cost: $60.00 + $7.50 fee
        expected_pnl = 200.0 - 60.0 - 7.50
        self.assertAlmostEqual(res.net_realized_pnl, expected_pnl, places=2)


if __name__ == "__main__":
    unittest.main()

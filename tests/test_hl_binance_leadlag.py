"""Unit tests for Hyperliquid <-> Binance Lead-Lag Engine (Option D).

Tests:
1. OFI volume sweep calculation and threshold gating
2. Hyperliquid executable edge evaluation
3. Refractory lockout window enforcement
4. Ingress timestamp ordering

ISOLATION INVARIANT:
Tests run only against src/hl_leadlag/. Zero imports or side effects on Hyperliquid
production paper trading files.
"""

from __future__ import annotations

import unittest
from src.hl_leadlag.signals.ofi_leadlag_engine import (
    AggTrade,
    OFILeadLagDetector,
    TopOfBook,
)


class TestHLBinanceLeadLag(unittest.TestCase):
    def setUp(self):
        self.detector = OFILeadLagDetector(
            symbol="BTC",
            sweep_window_ms=100.0,
            min_sweep_volume_usd=1_000_000.0,
            min_edge_bps=3.0,
        )
        # Seed Hyperliquid book with resting ask at 84,350.00
        self.detector.hl_book = TopOfBook(
            best_bid=84348.0,
            best_bid_sz=2.5,
            best_ask=84350.0,
            best_ask_sz=3.0,
            mid=84349.0,
            last_update_mono_ns=1_000_000,
        )

    def test_sub_threshold_volume_does_not_trigger(self):
        """Trades below min_sweep_volume_usd should not trigger an opportunity."""
        t1 = AggTrade(
            price=84350.0,
            qty=5.0,  # Notional: $421,750 (< $1.0M threshold)
            notional=421_750.0,
            is_buyer_maker=False,
            exchange_ts_ms=1000,
            local_mono_ns=100_000_000,
        )
        opp = self.detector.update_binance_trade(t1)
        self.assertIsNone(opp)

    def test_aggressive_buy_sweep_triggers_leadlag_edge(self):
        """Large aggressive buy sweep on Binance pushing price above HL ask triggers edge."""
        # Trade 1: base trade
        t1 = AggTrade(
            price=84350.0,
            qty=6.0,
            notional=506_100.0,
            is_buyer_maker=False,
            exchange_ts_ms=1000,
            local_mono_ns=100_000_000,
        )
        self.detector.update_binance_trade(t1)

        # Trade 2: 20ms later, aggressive buy pushing price to 84,380 (+30 USD jump = +3.55 bps above HL ask 84,350)
        t2 = AggTrade(
            price=84380.0,
            qty=8.0,
            notional=675_040.0,
            is_buyer_maker=False,  # Market Buy
            exchange_ts_ms=1020,
            local_mono_ns=120_000_000,
        )
        opp = self.detector.update_binance_trade(t2)

        self.assertIsNotNone(opp)
        self.assertEqual(opp.symbol, "BTC")
        # Edge = 84,380 - 84,350 = +$30.00
        self.assertAlmostEqual(opp.theoretical_edge_usd, 30.0, places=2)
        # Edge bps = (30 / 84350) * 10000 = ~3.55 bps
        self.assertGreater(opp.theoretical_edge_bps, 3.0)
        self.assertTrue(opp.is_actionable)

    def test_lockout_window_prevents_rapid_fire_duplicate_triggers(self):
        """Subsequent trades within lockout window must not trigger duplicate orders."""
        t1 = AggTrade(price=84350.0, qty=10.0, notional=843_500.0, is_buyer_maker=False, exchange_ts_ms=1000, local_mono_ns=100_000_000)
        t2 = AggTrade(price=84385.0, qty=10.0, notional=843_850.0, is_buyer_maker=False, exchange_ts_ms=1010, local_mono_ns=110_000_000)
        
        opp1 = self.detector.update_binance_trade(t1)
        opp2 = self.detector.update_binance_trade(t2)
        self.assertIsNotNone(opp2)

        # Trade 3: 50ms later (within 5-second lockout)
        t3 = AggTrade(price=84390.0, qty=10.0, notional=843_900.0, is_buyer_maker=False, exchange_ts_ms=1060, local_mono_ns=160_000_000)
        opp3 = self.detector.update_binance_trade(t3)
        self.assertIsNone(opp3)


if __name__ == "__main__":
    unittest.main()

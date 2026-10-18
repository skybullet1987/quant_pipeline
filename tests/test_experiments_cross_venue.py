"""
Unit and Microstructure Integration Tests for Cross-Venue Experiments (S9, S8, S7)
==================================================================================
Tests:
  - Experiment S9: Deribit SVI Breeden-Litzenberger vs Polymarket/Kalshi Strike Ladders
  - Experiment S8: Pyth Lazer / Hermes CI_Ratio & Pull-Oracle Lag Monitor
  - Experiment S7: Whales Market 4-Hour TGE Escrow Squeeze Tracker
"""

import math
import time
import pytest

from experiments.cross_venue.exp_s9_svi_digital_arb import (
    BreedenLitzenbergerCalculator,
    ExpS9DigitalArbEngine,
    ExpiryInterpolatedSurface,
    SVIFitter,
    SVIParameters,
    black_scholes_call,
)
from experiments.cross_venue.exp_s8_pyth_ci_arb import (
    DEXBookSummary,
    ExpS8PythCIArbEngine,
    PositionState,
    PythPriceUpdate,
    S8Config,
)
from experiments.cross_venue.exp_s7_whales_tge_squeeze import (
    ExpS7WhalesTGESqueezeEngine,
    S7SqueezePosition,
    SqueezeState,
    WhalesMarketEscrowContract,
)


# ==============================================================================
# EXPERIMENT S9 TESTS: DERIBIT SVI BREEDEN-LITZENBERGER VS POLYMARKET
# ==============================================================================

class TestExperimentS9SVIDigitalArb:

    def test_svi_total_variance_formula(self):
        """Verifies Gatheral's SVI total variance w(k) = a + b * [rho*(k - m) + sqrt((k - m)^2 + sigma^2)]."""
        svi = SVIParameters(a=0.04, b=0.10, rho=-0.25, m=0.0, sigma=0.10)
        # At k = 0 (ATM):
        # term = sqrt(0 + 0.01) = 0.10
        # w(0) = 0.04 + 0.10 * [ -0.25 * 0 + 0.10 ] = 0.04 + 0.01 = 0.05
        w_atm = svi.total_variance(0.0)
        assert math.isclose(w_atm, 0.05, rel_tol=1e-5)

        # Implied vol for T = 1 year: sqrt(0.05 / 1.0) ~ 22.36%
        iv_atm = svi.implied_vol(0.0, t_years=1.0)
        assert math.isclose(iv_atm, math.sqrt(0.05), rel_tol=1e-5)

    def test_svi_arbitrage_free_constraints(self):
        """Verifies no-arbitrage bounds (slope bound, positive variance)."""
        # Valid parameters for T = 0.1 years (approx 36 days)
        svi_ok = SVIParameters(a=0.04, b=0.10, rho=-0.30, m=0.0, sigma=0.05)
        assert svi_ok.is_arbitrage_free(t_years=0.1) is True

        # Invalid: b < 0
        svi_neg_b = SVIParameters(a=0.04, b=-0.10, rho=-0.30, m=0.0, sigma=0.05)
        assert svi_neg_b.is_arbitrage_free(t_years=0.1) is False

        # Invalid: |rho| >= 1.0
        svi_bad_rho = SVIParameters(a=0.04, b=0.10, rho=1.05, m=0.0, sigma=0.05)
        assert svi_bad_rho.is_arbitrage_free(t_years=0.1) is False

    def test_breeden_litzenberger_digital_and_density(self):
        """
        Verifies Breeden-Litzenberger risk-neutral survival probability:
          P(S_T > K) = -e^(rT) * dC/dK
        """
        F = 100.0
        T = 0.25
        svi = SVIParameters(a=0.04, b=0.08, rho=-0.2, m=0.0, sigma=0.1)

        # For deep OTM strike (K = 140), P(S_T > K) must be small (< 0.10)
        p_otm, dens_otm = BreedenLitzenbergerCalculator.compute_digital_call_price(
            F=F, K=140.0, T=T, svi=svi
        )
        assert 0.0 < p_otm < 0.10
        assert dens_otm >= 0.0

        # For ATM strike (K = 100), P(S_T > K) should be near ~0.45 - 0.55
        p_atm, dens_atm = BreedenLitzenbergerCalculator.compute_digital_call_price(
            F=F, K=100.0, T=T, svi=svi
        )
        assert 0.40 < p_atm < 0.60
        assert dens_atm > 0.0

    def test_expiry_interpolated_surface_10h_offset(self):
        """Verifies forward total variance interpolation across the 10-hour offset between 08:00 and next 08:00 UTC."""
        f1 = 95_000.0
        f2 = 95_200.0
        svi1 = SVIParameters(a=0.02, b=0.10, rho=-0.3, m=0.0, sigma=0.08)
        svi2 = SVIParameters(a=0.04, b=0.12, rho=-0.3, m=0.0, sigma=0.08)

        # T1 = 0 hours, T2 = 24 hours, T_poly = 10 hours
        # alpha = 10 / 24 = 0.41667
        surface = ExpiryInterpolatedSurface(
            f1=f1, svi1=svi1, t1_years=0.0,
            f2=f2, svi2=svi2, t2_years=24.0 / 8760.0,
            t_poly_years=10.0 / 8760.0,
        )
        poly_svi = surface.get_interpolated_svi_for_poly()

        # a should be intermediate between 0.02 and 0.04
        assert 0.02 < poly_svi.a < 0.04
        assert poly_svi.a == pytest.approx(0.02 + (10.0 / 24.0) * (0.04 - 0.02), rel=1e-3)

    def test_s9_tail_arbitrage_and_pin_risk_unwind(self):
        """Tests tail bucket mispricing detection (>5c edge) and automated 18:00:05 UTC pin-risk unwind."""
        engine = ExpS9DigitalArbEngine()
        t0 = time.time()

        svi1 = SVIParameters(a=0.02, b=0.10, rho=-0.3, m=0.0, sigma=0.08)
        svi2 = SVIParameters(a=0.04, b=0.12, rho=-0.3, m=0.0, sigma=0.08)

        # Test strike where Poly is 0.12, but RND is ~0.33 => delta -0.21 > 0.05
        opp = engine.evaluate_strike_mispricing(
            symbol="BTC",
            strike=100_000.0,
            poly_price=0.12,
            f1=95_000.0, svi1=svi1, t1_hours=0.0,
            f2=95_200.0, svi2=svi2, t2_hours=24.0,
            t_poly_hours=10.0,
            current_ts=t0,
        )
        assert opp is not None
        assert opp.net_arb_edge >= 0.05
        assert opp.unwound is False

        # Execute shadow trade and pin-risk unwind
        engine.execute_and_unwind_trade(opp)
        assert opp.unwound is True
        assert opp.poly_order_id is not None
        assert len(opp.deribit_order_ids) == 2


# ==============================================================================
# EXPERIMENT S8 TESTS: PYTH CI_RATIO & PULL-ORACLE LAG MONITOR
# ==============================================================================

class TestExperimentS8PythCIArb:

    def test_pyth_price_update_ci_ratio(self):
        """Verifies CI_Ratio = conf / price and ci_bps calculation."""
        update = PythPriceUpdate(symbol="SOL", price=200.0, conf=0.80, publish_time=1000.0)
        # CI_Ratio = 0.80 / 200.0 = 0.0040 (40 bps)
        assert math.isclose(update.ci_ratio, 0.0040)
        assert math.isclose(update.ci_bps, 40.0)

    def test_pyth_kill_switch_outlier_print(self):
        """Trips kill-switch when CI_Ratio >= 3% (outlier print)."""
        engine = ExpS8PythCIArbEngine()
        t0 = 1000.0

        # Outlier feed: conf = 10.0 on price = 200.0 => 5% > 3%
        bad_update = PythPriceUpdate(symbol="SOL", price=200.0, conf=10.0, publish_time=t0)
        engine.update_pyth_feed(bad_update)
        engine.update_dex_book("hyperliquid", "SOL", best_bid=200.0, best_ask=200.02, timestamp=t0)

        is_opp, reason, _ = engine.evaluate_opportunity("SOL", "apex_omni", current_ts=t0)
        assert is_opp is False
        assert reason == "KILLED_OUTLIER_CI"

    def test_pyth_kill_switch_stale_feed(self):
        """Trips kill-switch when publish_time is > 5s old."""
        engine = ExpS8PythCIArbEngine()
        t0 = 1000.0

        # Stale feed: published at 1000.0, current_ts is 1006.0 (6s age > 5s)
        stale_update = PythPriceUpdate(symbol="SOL", price=200.0, conf=0.80, publish_time=t0)
        engine.update_pyth_feed(stale_update)
        engine.update_dex_book("hyperliquid", "SOL", best_bid=200.0, best_ask=200.02, timestamp=t0 + 6.0)

        is_opp, reason, _ = engine.evaluate_opportunity("SOL", "apex_omni", current_ts=t0 + 6.0)
        assert is_opp is False
        assert reason == "KILLED_STALE_ORACLE"

    def test_pyth_ci_arb_trigger_and_hedging(self):
        """Verifies entry when CI_Ratio > 40 bps and Hyperliquid spread < 3 bps."""
        engine = ExpS8PythCIArbEngine()
        t0 = 1000.0

        # Pyth: CI = 50 bps (conf = 1.0 on price = 200)
        update = PythPriceUpdate(symbol="SOL", price=200.0, conf=1.0, publish_time=t0)
        engine.update_pyth_feed(update)

        # Hyperliquid spread: 1.0 bps (< 3 bps)
        engine.update_dex_book("hyperliquid", "SOL", best_bid=200.0, best_ask=200.02, timestamp=t0)

        pos = engine.execute_ci_dislocation_arb(
            symbol="SOL",
            dex_venue="apex_omni",
            trade_size=50.0,
            current_ts=t0,
        )
        assert pos is not None
        assert pos.state == PositionState.HEDGED
        assert pos.dex_price == 199.0  # 200 - 1.0 * CI
        assert pos.hl_hedge_price == 200.0  # Sold at HL best bid

    def test_pyth_ci_arb_mean_reversion_exit(self):
        """Verifies position closes with profit when CI collapses < 5 bps."""
        engine = ExpS8PythCIArbEngine()
        t0 = 1000.0

        update = PythPriceUpdate(symbol="SOL", price=200.0, conf=1.0, publish_time=t0)
        engine.update_pyth_feed(update)
        engine.update_dex_book("hyperliquid", "SOL", best_bid=200.0, best_ask=200.02, timestamp=t0)

        pos = engine.execute_ci_dislocation_arb("SOL", "apex_omni", 50.0, current_ts=t0)
        assert pos is not None

        # CI collapses to 3 bps (conf = 0.06 on price = 200.0)
        collapsed = PythPriceUpdate(symbol="SOL", price=200.0, conf=0.06, publish_time=t0 + 3.0)
        engine.update_pyth_feed(collapsed)

        closed = engine.check_position_exit(pos.position_id, current_ts=t0 + 3.0)
        assert closed is True
        assert pos.state == PositionState.CLOSED_PROFIT
        # Bought at 199, exit at 200 => +1/unit * 50 = $50 profit
        assert pos.realized_pnl_usd > 0


# ==============================================================================
# EXPERIMENT S7 TESTS: WHALES MARKET 4-HOUR TGE ESCROW SQUEEZE
# ==============================================================================

class TestExperimentS7WhalesTGESqueeze:

    def test_whales_capped_forward_payoff(self):
        """Verifies buyer payoff = min(S_T - K, K) and rational default above 2K."""
        escrow = WhalesMarketEscrowContract(
            symbol="ZRO",
            strike_k=1.00,
            total_volume_matched=1_000_000.0,
            delivered_volume=0.0,
            t_settle_start=1000.0,
        )
        # Below strike: payoff is negative (S_T - K)
        assert escrow.buyer_payoff(0.80) == pytest.approx(-0.20)
        # Between K and 2K: payoff is S_T - K
        assert escrow.buyer_payoff(1.50) == pytest.approx(0.50)
        # Above 2K: payoff is capped at K = 1.00 (seller default)
        assert escrow.buyer_payoff(2.50) == pytest.approx(1.00)

    def test_forced_delivery_zone_bounds(self):
        """Verifies Forced Delivery Zone (0.3K < S_t < 1.85K) and Default Zone (S_t >= 1.85K)."""
        escrow = WhalesMarketEscrowContract("ZRO", strike_k=2.00, total_volume_matched=100_000.0, delivered_volume=0.0, t_settle_start=0.0)

        # Inside zone: 0.3 * 2.0 = 0.60 to 1.85 * 2.0 = 3.70
        assert escrow.is_forced_delivery_zone(1.50) is True
        assert escrow.is_forced_delivery_zone(3.50) is True
        # Below zone (< 0.60)
        assert escrow.is_forced_delivery_zone(0.50) is False
        # In default zone (>= 3.70)
        assert escrow.is_forced_delivery_zone(3.80) is False
        assert escrow.is_default_zone(3.80) is True

    def test_minute_150_squeeze_trigger(self):
        """Verifies entry trigger at Minute 150 when undelivered > 40% and inside forced zone."""
        engine = ExpS7WhalesTGESqueezeEngine()
        t0 = 1000.0
        escrow = WhalesMarketEscrowContract(
            symbol="ZRO",
            strike_k=1.00,
            total_volume_matched=1_000_000.0,
            delivered_volume=300_000.0,  # 70% undelivered > 40%
            t_settle_start=t0,
        )
        engine.register_escrow(escrow)

        # At Minute 150 (t = t0 + 150 * 60) and price = $1.25 (inside [0.30, 1.85])
        t150 = t0 + 150 * 60.0
        is_trig, reason, telem = engine.evaluate_minute_150_trigger("ZRO", 1.25, t150)
        assert is_trig is True
        assert reason == "ARM_MINUTE_150_SQUEEZE"

        pos = engine.execute_squeeze_entry("ZRO", 1.25, trade_size=10_000.0, current_ts=t150)
        assert pos is not None
        assert pos.state == SqueezeState.LONG_ACTIVE

    def test_minute_238_hard_flat_exit(self):
        """Verifies position closes at Minute 238 before Minute 240 window expires."""
        engine = ExpS7WhalesTGESqueezeEngine()
        t0 = 1000.0
        escrow = WhalesMarketEscrowContract(
            symbol="ZRO",
            strike_k=1.00,
            total_volume_matched=1_000_000.0,
            delivered_volume=300_000.0,
            t_settle_start=t0,
        )
        engine.register_escrow(escrow)

        t150 = t0 + 150 * 60.0
        pos = engine.execute_squeeze_entry("ZRO", 1.25, trade_size=10_000.0, current_ts=t150)

        # Advance to Minute 238
        t238 = t0 + 238 * 60.0
        closed = engine.update_position_and_check_exits(pos.position_id, spot_price=1.65, current_ts=t238)
        assert closed is True
        assert pos.state == SqueezeState.EXITED_M238
        assert pos.realized_pnl_usd == (1.65 - 1.25) * 10_000.0  # $4,000 profit

    def test_kill_switch_on_default_spike(self):
        """Immediate abort if spot price spikes into default zone (S_t > 1.85K)."""
        engine = ExpS7WhalesTGESqueezeEngine()
        t0 = 1000.0
        escrow = WhalesMarketEscrowContract(
            symbol="ZRO",
            strike_k=1.00,
            total_volume_matched=1_000_000.0,
            delivered_volume=300_000.0,
            t_settle_start=t0,
        )
        engine.register_escrow(escrow)

        t150 = t0 + 150 * 60.0
        pos = engine.execute_squeeze_entry("ZRO", 1.25, trade_size=10_000.0, current_ts=t150)

        # Price spikes to $1.90 > 1.85K at Minute 180
        t180 = t0 + 180 * 60.0
        closed = engine.update_position_and_check_exits(pos.position_id, spot_price=1.90, current_ts=t180)
        assert closed is True
        assert pos.state == SqueezeState.KILLED_DEFAULT_SPIKE

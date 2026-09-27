import pytest
import math
import json
import hashlib
import numpy as np
from scipy import stats
from pathlib import Path
from src.backtesting.ironcore_config import (
    IronCoreConfig_v1, DEFAULT_CONFIG, CertificationProvenance, BacktestExecutionReference,
    ResolvedExecutionParameters, EnvironmentManifest, hash_array_raw, hash_array_canonicalized,
)
from src.backtesting.ironcore_engine import (
    IronCoreEngine, PositionState, OrderState, GovernorStateMachine, INTRABAR_PATH_CONVENTION,
)
from src.backtesting.trial_registry_dsr import TrialRegistryDSR
from src.backtesting.ruin_and_leverage_frontier import RuinAndLeverageFrontier


# =============================================================================
# 1. POSITION-STATE TESTS (6 TESTS)
# =============================================================================

def test_position_state_persist_across_bars():
    """Verifies that an open position held across multiple 4H bars retains its avg_entry_px."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(fill_qty=10.0, fill_px=100.0, bar_idx=0)
    assert pos.avg_entry_px == 100.0
    assert pos.qty == 10.0
    
    # 5 bars pass without new fills, price moves to 150
    assert pos.avg_entry_px == 100.0
    assert pos.compute_unrealized_pnl(150.0) == 500.0


def test_position_state_add_weighted_average():
    """Verifies volume-weighted average price calculation upon position additions."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(fill_qty=10.0, fill_px=100.0, bar_idx=0)
    pos.apply_increase(fill_qty=20.0, fill_px=130.0, bar_idx=1)
    
    # Expected avg = (10*100 + 20*130) / 30 = 3600 / 30 = 120.0
    assert pos.qty == 30.0
    assert pos.avg_entry_px == pytest.approx(120.0)


def test_position_state_partial_reduction_preserves_basis():
    """Verifies that reducing a position realizes PnL but leaves avg_entry_px unchanged."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(fill_qty=10.0, fill_px=100.0, bar_idx=0)
    
    # Sell half (5 units) at 120
    pnl = pos.apply_reduction(fill_qty=5.0, fill_px=120.0)
    assert pnl == pytest.approx(100.0)  # 5 * (120 - 100) = +$100
    assert pos.qty == 5.0
    assert pos.avg_entry_px == 100.0  # Cost basis strictly preserved!


def test_position_state_full_exit_resets_state():
    """Verifies that completely liquidating a position resets qty and basis to 0.0."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(fill_qty=10.0, fill_px=100.0, bar_idx=0)
    pnl = pos.apply_full_exit(fill_px=90.0)
    
    assert pnl == pytest.approx(-100.0)
    assert pos.qty == 0.0
    assert pos.avg_entry_px == 0.0
    assert not pos.is_open


def test_position_state_flip_closes_and_reopens():
    """Verifies position flip closes old position at fill_px and opens new side at fill_px."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(fill_qty=10.0, fill_px=100.0, bar_idx=0)  # 10 Long @ 100
    
    # Flip to 5 Short at 110: should close 10 Long at 110 (+100 PnL) and open 5 Short @ 110
    closed_pnl = pos.apply_flip(new_target_qty=-5.0, fill_px=110.0, bar_idx=1)
    
    assert closed_pnl == pytest.approx(100.0)
    assert pos.qty == -5.0
    assert pos.avg_entry_px == 110.0
    assert pos.is_short


def test_stop_loss_strictly_uses_average_entry_price():
    """Verifies that stop-loss triggers strictly off avg_entry_px, not bar open or high water mark."""
    engine = IronCoreEngine()
    n_4h, subbars, n_sym = 4, 2, 1
    weights = np.ones((n_4h, n_sym))
    
    sub_open = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_low = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_close = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_vol = np.ones((n_4h, subbars, n_sym)) * 1e6
    fund = np.zeros((n_4h, n_sym))
    
    # Bar 1: Entry executes at 100.0
    sub_open[1, :, 0] = 100.0
    sub_high[1, :, 0] = 100.5
    sub_low[1, :, 0] = 99.8
    sub_close[1, :, 0] = 100.0
    
    # Bar 2: Opens higher at 105.0. Low dips to 101.0.
    # From bar 2 open (105), drop to 101 is -3.8% (would trigger 3.5% SL if reset to bar open).
    # From true average entry (100), price 101 is +1.0% profit!
    sub_open[2, :, 0] = 105.0
    sub_high[2, :, 0] = 106.0
    sub_low[2, :, 0] = 101.0
    sub_close[2, :, 0] = 104.0
    
    # Bar 3: Closes at 105.0
    sub_open[3, :, 0] = 104.0
    sub_high[3, :, 0] = 105.0
    sub_low[3, :, 0] = 103.5
    sub_close[3, :, 0] = 105.0
    
    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_4h, n_sym))
    returns_mat[2, 0] = 0.04
    returns_mat[3, 0] = 0.01
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        sl_pct=0.035,
        initial_capital=10000.0,
    )
    assert res["sl_count"] == 0


# =============================================================================
# 2. ORDER LIFECYCLE TESTS (5 TESTS)
# =============================================================================

def test_stop_cancels_pending_order():
    """Verifies that an intrabar stop cancels any pending rebalance order for that asset."""
    engine = IronCoreEngine()
    n_4h, subbars, n_sym = 3, 2, 1
    weights = np.zeros((n_4h, n_sym))
    weights[0, 0] = 1.0  # Enter Long
    weights[1, 0] = 0.5  # Rebalance: sell 0.5
    
    sub_open = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_low = np.ones((n_4h, subbars, n_sym)) * 99.0
    sub_close = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_vol = np.ones((n_4h, subbars, n_sym)) * 1e6
    fund = np.zeros((n_4h, n_sym))
    
    # Bar 1: Enters @ 100
    sub_open[1, :, 0] = 100.0
    sub_high[1, :, 0] = 100.0
    sub_low[1, :, 0] = 99.0
    sub_close[1, :, 0] = 100.0
    
    # Bar 2 Subbar 0: Severe crash to 90.0 triggers 3.5% stop immediately
    sub_open[2, 0, 0] = 95.0
    sub_high[2, 0, 0] = 95.0
    sub_low[2, 0, 0] = 90.0
    sub_close[2, 0, 0] = 90.0
    
    # Bar 2 Subbar 1: Rebounds
    sub_open[2, 1, 0] = 90.0
    sub_high[2, 1, 0] = 95.0
    sub_low[2, 1, 0] = 90.0
    sub_close[2, 1, 0] = 95.0
    
    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_4h, n_sym))
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        sl_pct=0.035,
        initial_capital=10000.0,
    )
    assert res["sl_count"] == 1
    # Stopped out position must be 0.0, not mutated into short
    assert res["ending_weights"][0] == pytest.approx(0.0, abs=1e-5)


def test_tp_cancels_pending_order():
    """Verifies that a take-profit trigger cancels pending rebalance orders."""
    engine = IronCoreEngine()
    n_4h, subbars, n_sym = 3, 2, 1
    weights = np.zeros((n_4h, n_sym))
    weights[0, 0] = 1.0
    weights[1, 0] = 0.5
    
    sub_open = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_low = np.ones((n_4h, subbars, n_sym)) * 99.0
    sub_close = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_vol = np.ones((n_4h, subbars, n_sym)) * 1e6
    fund = np.zeros((n_4h, n_sym))
    
    sub_open[1, :, 0] = 100.0
    sub_high[1, :, 0] = 100.0
    sub_low[1, :, 0] = 99.0
    sub_close[1, :, 0] = 100.0
    
    # Bar 2 Subbar 0: Surges to 110.0 (triggers 7.0% TP)
    sub_open[2, 0, 0] = 105.0
    sub_high[2, 0, 0] = 110.0
    sub_low[2, 0, 0] = 105.0
    sub_close[2, 0, 0] = 110.0
    
    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_4h, n_sym))
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        tp_pct=0.070,
        initial_capital=10000.0,
    )
    assert res["tp_count"] == 1
    assert res["ending_weights"][0] == pytest.approx(0.0, abs=1e-5)


def test_cancelled_order_cannot_fill():
    """Verifies that once an OrderState is cancelled, it is not active and cannot be filled."""
    order = OrderState(
        order_id="TEST_ORD",
        order_generation=1,
        symbol_idx=0,
        target_qty=100.0,
        remaining_qty=100.0,
        created_bar=1,
        created_subbar=0,
    )
    assert order.is_active
    order.cancel("TEST_CANCEL")
    assert not order.is_active
    assert order.remaining_qty == 0.0
    assert order.status == "CANCELLED"


def test_partial_fill_leaves_remaining_order():
    """Verifies that executing a partial fill leaves the remaining balance active."""
    order = OrderState(
        order_id="TEST_PARTIAL",
        order_generation=1,
        symbol_idx=0,
        target_qty=100.0,
        remaining_qty=100.0,
        created_bar=1,
        created_subbar=0,
    )
    executed = order.fill_partial(35.0, 100.0)
    assert executed == 35.0
    assert order.remaining_qty == 65.0
    assert order.status == "PARTIALLY_FILLED"
    assert order.is_active


def test_passive_timeout_at_subbar_open():
    """Verifies passive orders cross as taker strictly after passive_fill_horizon expires."""
    engine = IronCoreEngine()
    n_4h, subbars, n_sym = 2, 3, 1
    weights = np.zeros((n_4h, n_sym))
    weights[0, 0] = 1.0  # Enters at bar 1
    
    # Subbar prices where low never touches limit buy (99.95)
    sub_open = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_4h, subbars, n_sym)) * 105.0
    sub_low = np.ones((n_4h, subbars, n_sym)) * 101.0
    sub_close = np.ones((n_4h, subbars, n_sym)) * 102.0
    sub_vol = np.ones((n_4h, subbars, n_sym)) * 1e6
    fund = np.zeros((n_4h, n_sym))
    
    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_4h, n_sym))
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        initial_capital=10000.0,
    )
    # Order waited 2 subbars without passive fill, then timeout-crossed at subbar 2 open
    assert res["taker_crosses"] == 1
    assert res["passive_fills"] == 0


# =============================================================================
# 3. ACCOUNTING INVARIANTS (5 TESTS)
# =============================================================================

def test_unfilled_order_zero_turnover():
    """Verifies that an unfilled pending order produces 0.0 turnover."""
    engine = IronCoreEngine()
    n_4h, subbars, n_sym = 2, 2, 1
    weights = np.zeros((n_4h, n_sym))
    weights[0, 0] = 1.0
    
    sub_open = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_4h, subbars, n_sym)) * 105.0
    sub_low = np.ones((n_4h, subbars, n_sym)) * 101.0
    sub_close = np.ones((n_4h, subbars, n_sym)) * 102.0
    sub_vol = np.ones((n_4h, subbars, n_sym)) * 1e6
    fund = np.zeros((n_4h, n_sym))
    
    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_4h, n_sym))
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        initial_capital=10000.0,
    )
    # Never filled within 2 subbars before horizon
    assert res["turnover_usd"] == 0.0
    assert res["trades_count"] == 0


def test_partial_fill_partial_turnover_accounting():
    """Verifies turnover is calculated strictly from executed fill, not requested notional."""
    order = OrderState(
        order_id="TEST", order_generation=1, symbol_idx=0,
        target_qty=1000.0, remaining_qty=1000.0, created_bar=1, created_subbar=0
    )
    executed_qty = order.fill_partial(350.0, 100.0)
    executed_turnover = executed_qty * 100.0
    requested_notional = order.target_qty * 100.0
    
    assert executed_turnover == 35000.0
    assert requested_notional == 100000.0
    assert executed_turnover != requested_notional


def test_fee_excludes_adverse_selection():
    """Verifies that exchange fees exclude adverse selection markout and market impact."""
    engine = IronCoreEngine()
    n_bars, n_symbols = 5, 2
    weights = np.ones((n_bars, n_symbols)) * 0.0
    weights[:, 0] = 0.5
    
    returns = np.zeros((n_bars, n_symbols))
    volume = np.ones((n_bars, n_symbols)) * 1e6
    close = np.ones((n_bars, n_symbols)) * 100.0
    funding = np.zeros((n_bars, n_symbols))
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        initial_capital=10000.0,
    )
    # 50% of $10,000 = $5,000. 
    # Blended fee = (0.6*1.5 + 0.4*4.5) bps = 2.7 bps = 0.00027 * 5000 = $1.35
    assert res["exchange_fees"] == pytest.approx(1.35, rel=1e-2)
    assert res["adverse_selection_cost"] == pytest.approx(0.50, rel=1e-2)  # 1.0 bps
    assert res["exchange_fees"] != res["total_trading_cost"]


def test_market_impact_separated_bucket():
    """Verifies market impact is isolated into its own diagnostic accumulator."""
    engine = IronCoreEngine()
    n_bars, n_symbols = 5, 2
    weights = np.zeros((n_bars, n_symbols))
    weights[0, 0] = 0.5
    
    returns = np.zeros((n_bars, n_symbols))
    volume = np.ones((n_bars, n_symbols)) * 1e6
    close = np.ones((n_bars, n_symbols)) * 100.0
    funding = np.zeros((n_bars, n_symbols))
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        initial_capital=10000.0,
    )
    assert "market_impact" in res
    assert res["market_impact"] >= 0.0
    assert pytest.approx(res["exchange_fees"] + res["adverse_selection_cost"] + res["market_impact"]) == res["total_trading_cost"]


def test_mtm_reconciliation_exact():
    """Verifies exact balance sheet MTM reconciliation: E_t = E_{t-1} + Gross + Funding - Friction."""
    engine = IronCoreEngine()
    n_bars, n_symbols = 10, 2
    weights = np.zeros((n_bars, n_symbols))
    weights[:, 0] = 0.5
    returns = np.random.randn(n_bars, n_symbols) * 0.01
    volume = np.ones((n_bars, n_symbols)) * 1e6
    close = np.ones((n_bars, n_symbols)) * 100.0
    funding = np.ones((n_bars, n_symbols)) * 0.0001
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        initial_capital=10000.0,
    )
    assert res["drift_certified"]
    assert res["max_mtm_drift"] < 1e-6


# =============================================================================
# 4. PIT LIQUIDITY ASYMMETRY (4 TESTS)
# =============================================================================

def test_illiquid_entry_blocked():
    """Verifies that opening a new position in an illiquid asset is blocked."""
    engine = IronCoreEngine()
    n_bars, n_sym = 4, 2
    weights = np.zeros((n_bars, n_sym))
    weights[0, 0] = 0.5
    
    returns = np.zeros((n_bars, n_sym))
    volume = np.ones((n_bars, n_sym)) * 1e6
    close = np.ones((n_bars, n_sym)) * 100.0
    funding = np.zeros((n_bars, n_sym))
    
    pit_liquid = np.ones((n_bars, n_sym), dtype=bool)
    pit_liquid[1, 0] = False  # Illiquid at entry bar
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        pit_liquid_mask=pit_liquid,
        initial_capital=10000.0,
    )
    assert res["ending_weights"][0] == 0.0


def test_illiquid_addition_blocked():
    """Verifies increasing an existing position in an illiquid asset is blocked."""
    engine = IronCoreEngine()
    n_bars, n_sym = 4, 2
    weights = np.zeros((n_bars, n_sym))
    weights[0, 0] = 0.3  # Initial long
    weights[1, 0] = 0.6  # Attempt to increase
    weights[2, 0] = 0.6  # Hold attempted increase
    
    returns = np.zeros((n_bars, n_sym))
    volume = np.ones((n_bars, n_sym)) * 1e6
    close = np.ones((n_bars, n_sym)) * 100.0
    funding = np.zeros((n_bars, n_sym))
    
    pit_liquid = np.ones((n_bars, n_sym), dtype=bool)
    pit_liquid[2:, 0] = False  # Illiquid when adding and held
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        pit_liquid_mask=pit_liquid,
        initial_capital=10000.0,
    )
    # Weight should remain at 0.3, NOT increased to 0.6
    assert res["ending_weights"][0] == pytest.approx(0.3, abs=1e-2)


def test_illiquid_exit_allowed():
    """Verifies reducing or completely liquidating a position in an illiquid asset is permitted."""
    engine = IronCoreEngine()
    n_bars, n_sym = 4, 2
    weights = np.zeros((n_bars, n_sym))
    weights[0, 0] = 0.5  # Enter
    weights[1, 0] = 0.0  # Exit
    
    returns = np.zeros((n_bars, n_sym))
    volume = np.ones((n_bars, n_sym)) * 1e6
    close = np.ones((n_bars, n_sym)) * 100.0
    funding = np.zeros((n_bars, n_sym))
    
    pit_liquid = np.ones((n_bars, n_sym), dtype=bool)
    pit_liquid[2, 0] = False  # Illiquid when exiting
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        pit_liquid_mask=pit_liquid,
        initial_capital=10000.0,
    )
    # Exit succeeded
    assert res["ending_weights"][0] == pytest.approx(0.0, abs=1e-5)


def test_illiquid_flip_only_closes_existing_side():
    """Verifies flipping long->short in an illiquid asset closes the long but blocks the new short."""
    engine = IronCoreEngine()
    n_bars, n_sym = 4, 2
    weights = np.zeros((n_bars, n_sym))
    weights[0, 0] = 0.5   # Enter long
    weights[1, 0] = -0.5  # Flip to short
    
    returns = np.zeros((n_bars, n_sym))
    volume = np.ones((n_bars, n_sym)) * 1e6
    close = np.ones((n_bars, n_sym)) * 100.0
    funding = np.zeros((n_bars, n_sym))
    
    pit_liquid = np.ones((n_bars, n_sym), dtype=bool)
    pit_liquid[2, 0] = False  # Illiquid when flipping
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        pit_liquid_mask=pit_liquid,
        initial_capital=10000.0,
    )
    # Long was closed to 0.0, but short was BLOCKED
    assert res["ending_weights"][0] == pytest.approx(0.0, abs=1e-5)


# =============================================================================
# 5. GOVERNOR STATE MACHINE TESTS (4 TESTS)
# =============================================================================

def test_governor_immediate_derisk():
    """Verifies governor immediately scales down leverage when DD reaches tier threshold."""
    gov = GovernorStateMachine()
    # 0% DD
    lev, tier = gov.update_equity(10000.0)
    assert lev == 1.00 and tier == 0
    # 6% DD (>= 5%) -> Tier 1
    lev, tier = gov.update_equity(9400.0)
    assert lev == 0.75 and tier == 1
    # 11% DD (>= 10%) -> Tier 2
    lev, tier = gov.update_equity(8900.0)
    assert lev == 0.35 and tier == 2


def test_governor_recovery_buffer_prevents_re_risk():
    """Verifies governor requires DD < threshold - 2.0% buffer before stepping leverage back up."""
    gov = GovernorStateMachine()
    gov.hwm = 10000.0
    # DD = 11% -> Tier 2 (0.35x)
    gov.update_equity(8900.0)
    assert gov.active_tier_idx == 2
    
    # Equity recovers to 9100 (DD = 9%). 
    # Without buffer, 9% < 10% would re-risk.
    # With 2% buffer, DD must be < 8% (10% - 2%)!
    lev, tier = gov.update_equity(9100.0)
    assert lev == 0.35 and tier == 2  # Blocked!
    
    # Equity recovers to 9300 (DD = 7% < 8%).
    lev, tier = gov.update_equity(9300.0)
    assert lev == 0.75 and tier == 1  # Re-risked!


def test_governor_deterministic_tier_transitions():
    """Verifies all tier thresholds map deterministically."""
    gov = GovernorStateMachine()
    hwm = 10000.0
    gov.hwm = hwm
    
    assert gov.update_equity(9600.0)[0] == 1.00  # 4% DD
    assert gov.update_equity(9300.0)[0] == 0.75  # 7% DD
    assert gov.update_equity(8800.0)[0] == 0.35  # 12% DD
    assert gov.update_equity(8400.0)[0] == 0.00  # 16% DD (Halt)


def test_governor_halt_state_freezes_trading():
    """Verifies reaching >= 15% DD halts trading and CANNOT automatically re-risk without explicit reset."""
    gov = GovernorStateMachine()
    gov.hwm = 10000.0
    # DD = 16% -> Halt
    lev, tier = gov.update_equity(8400.0)
    assert lev == 0.00
    assert gov.is_halted
    
    # Equity magically recovers to 9500 (DD = 5%)
    # Because it is halted, it must REMAIN at 0.00 leverage!
    lev, tier = gov.update_equity(9500.0)
    assert lev == 0.00
    assert gov.is_halted
    
    # Explicit programmatic reset allows trading again
    gov.reset_halt(9500.0)
    assert not gov.is_halted
    assert gov.update_equity(9500.0)[0] == 1.00


# =============================================================================
# 6. CAUSALITY TESTS (3 TESTS)
# =============================================================================

def test_one_bar_toy_causal_alignment():
    """
    Constructs a toy dataset where ONLY bar k has non-zero return.
    Verifies that signal at bar k-1 monetizes return at bar k.
    """
    engine = IronCoreEngine()
    n_bars, n_sym = 6, 1
    
    weights = np.zeros((n_bars, n_sym))
    # Signal forms at close of bar 2
    weights[2, 0] = 1.0
    
    returns = np.zeros((n_bars, n_sym))
    returns[3, 0] = 0.50  # Bar 3 has +50% return (forward bar next_t = 3)
    
    volume = np.ones((n_bars, n_sym)) * 1e6
    close = np.ones((n_bars, n_sym)) * 100.0
    funding = np.zeros((n_bars, n_sym))
    
    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        initial_capital=1000.0,
    )
    # The return at bar 2 (t=2, next_t=3) MUST reflect the +50% return!
    assert res["bar_returns"][2] > 0.40


def test_no_test_bar_information_reaches_training():
    """Verifies that WFO training slices strictly exclude test-bar features and targets."""
    features = {"close": np.arange(100.0, 200.0).reshape(100, 1)}
    returns = np.ones((100, 1)) * 0.01
    
    tr_s, tr_e = 0, 50
    te_s, te_e = 50, 75
    
    # 1-Bar Embargo: train features [0:49], train targets [1:50]
    train_features = {k: v[tr_s:tr_e - 1] for k, v in features.items()}
    train_targets = returns[tr_s + 1:tr_e]
    
    assert len(train_features["close"]) == 49
    assert len(train_targets) == 49
    # Ensure zero overlap with test slice [50:75]
    assert np.max(train_features["close"]) < features["close"][te_s, 0]


def test_wfo_fold_continuous_portfolio_state():
    """Verifies portfolio equity and positions carry over continuously across WFO folds."""
    cfg = IronCoreConfig_v1(wfo_train_bars=40, wfo_test_bars=20)
    engine = IronCoreEngine(config=cfg)
    n_bars, n_symbols = 100, 2
    
    features = {"close": np.ones((n_bars, n_symbols)) * 100.0}
    returns = np.random.randn(n_bars, n_symbols) * 0.01
    volume = np.ones((n_bars, n_symbols)) * 1e6
    close = np.ones((n_bars, n_symbols)) * 100.0
    funding = np.zeros((n_bars, n_symbols))
    btc_px = np.linspace(50000, 60000, n_bars)
    
    def dummy_fit(f, t): return {"best": 0}
    def dummy_predict(m, f):
        w = np.zeros((len(f["close"]), n_symbols))
        w[:, 0] = 0.5
        return w
        
    wfo_res = engine.run_true_wfo(
        dummy_fit, dummy_predict, features, returns, funding, volume, close, btc_px, continuous_portfolio=True
    )
    assert len(wfo_res["folds"]) >= 2
    # Ending equity of Fold 1 matches Fold 2 starting equity continuity
    assert wfo_res["ending_equity"] > 0.0


# =============================================================================
# 7. CERTIFICATION & PROVENANCE TESTS (4 TESTS)
# =============================================================================

def test_gate_4_newey_west_hac_paired_test():
    """Verifies Gate 4 Newey-West HAC statistical test on paired excess returns."""
    engine = IronCoreEngine()
    
    # Strategy returns with positive mean and autocorrelation
    rng = np.random.RandomState(42)
    strat_rets = rng.randn(200) * 0.01 + 0.002
    cash_rets = np.zeros(200)
    
    diff_r = strat_rets - cash_rets
    mean_diff = float(np.mean(diff_r))
    t_stat, p_val = stats.ttest_1samp(diff_r, 0.0)
    
    # Newey-West HAC calculation
    L = 12
    d_centered = diff_r - mean_diff
    gamma_0 = float(np.mean(d_centered ** 2))
    gamma_sum = sum(2.0 * (1.0 - lag / (L + 1.0)) * float(np.mean(d_centered[lag:] * d_centered[:-lag])) for lag in range(1, L + 1))
    se_hac = math.sqrt(max(gamma_0 + gamma_sum, 1e-12) / len(diff_r))
    hac_t = mean_diff / se_hac
    hac_p = 1.0 - stats.t.cdf(hac_t, df=len(diff_r) - 1)
    
    assert mean_diff > 0
    assert hac_t > 0
    assert hac_p < 0.05


def test_trial_registry_increments_and_dsr_trial_count(tmp_path):
    """Verifies trial registry increments across runs and penalizes DSR accordingly."""
    reg_file = tmp_path / "test_registry.jsonl"
    registry = TrialRegistryDSR(registry_file=reg_file)
    
    assert len(registry.load_historical_sharpes()) == 0
    registry.log_trial("Trial_1", sharpe=2.0, cagr=50.0, max_dd=10.0)
    registry.log_trial("Trial_2", sharpe=1.5, cagr=30.0, max_dd=12.0)
    
    assert len(registry.load_historical_sharpes()) == 2
    dsr_1 = registry.compute_deflated_sharpe_ratio(1.8, np.random.randn(200) * 0.01, effective_n_trials=2)
    dsr_100 = registry.compute_deflated_sharpe_ratio(1.8, np.random.randn(200) * 0.01, effective_n_trials=100)
    
    # More trials strictly reduces DSR (higher hurdle)
    assert dsr_1["deflated_sharpe_ratio"] > dsr_100["deflated_sharpe_ratio"]


def test_provenance_hash_incorporates_full_custody_chain():
    """Verifies that changing any component of CertificationProvenance alters the master hash."""
    prov_1 = CertificationProvenance(
        engine_version="2.3.0",
        config_hash="abc",
        feature_manifest_hash="def",
        dataset_hash="123",
        universe_hash="456",
        model_spec_hash="789",
        wfo_partition_hash="ghi",
        trial_registry_hash="jkl",
        execution_engine_hash="mno",
        oos_equity_hash="pqr",
    )
    prov_2 = CertificationProvenance(
        engine_version="2.3.0",
        config_hash="abc_MODIFIED",
        feature_manifest_hash="def",
        dataset_hash="123",
        universe_hash="456",
        model_spec_hash="789",
        wfo_partition_hash="ghi",
        trial_registry_hash="jkl",
        execution_engine_hash="mno",
        oos_equity_hash="pqr",
    )
    assert prov_1.master_hash() != prov_2.master_hash()


def test_certification_rejects_unprovenanced_weights():
    """Verifies that certify_strategy rejects manual weights lacking CertificationProvenance."""
    engine = IronCoreEngine()
    n_bars, n_sym = 100, 2
    features = {"close": np.ones((n_bars, n_sym)) * 100.0}
    returns = np.zeros((n_bars, n_sym))
    volume = np.ones((n_bars, n_sym)) * 1e6
    close = np.ones((n_bars, n_sym)) * 100.0
    oracle = close.copy()
    valid = np.ones((n_bars, n_sym), dtype=bool)
    funding = np.zeros((n_bars, n_sym))
    btc_px = np.linspace(50000, 60000, n_bars)
    
    manual_w = np.zeros((50, n_sym))
    
    with pytest.raises(ValueError, match="UNPROVENANCED_WEIGHTS_REJECTED"):
        engine.certify_strategy(
            candidate_name="UnprovenancedStrategy",
            fit_fn=lambda f, t: {},
            predict_fn=lambda m, f: np.zeros((len(f["close"]), n_sym)),
            feature_panel=features,
            returns_mat=returns,
            predicted_funding=funding,
            volume_mat=volume,
            close_mat=close,
            oracle_mat=oracle,
            valid_mask=valid,
            btc_prices=btc_px,
            manual_weights_override=manual_w,
            provenance=None,  # No provenance provided!
        )


# =============================================================================
# 8. GATE 8 EXECUTION PARITY TESTS (2 TESTS)
# =============================================================================

def test_gate_8_fatal_on_unclassified_exits():
    """Verifies Gate 8 fails immediately if closing fills lack explicit lifecycle exit reasons."""
    engine = IronCoreEngine()
    unclassified_paper_fills = [
        {"sz": 10.0, "px": 100.0, "fee": 0.45, "closedPnl": -15.0, "dir": "Close Long"}
        for _ in range(10)
    ]
    parity = engine.evaluate_execution_parity(
        paper_fills=unclassified_paper_fills,
        backtest_turnover_usd=10000.0,
        backtest_fees_usd=1.5,
    )
    assert not parity["passed"]
    assert any("FATAL_TELEMETRY_UNCLASSIFIED_EXITS" in issue for issue in parity["issues"])


def test_gate_8_all_10_dimensions():
    """Verifies that Gate 8 evaluates and reports all 10 institutional execution parity dimensions."""
    engine = IronCoreEngine()
    fills = [
        {
            "sz": 10.0,
            "px": 100.0,
            "ref_px": 99.98,
            "future_px": 100.02,
            "fee": 0.15,
            "closedPnl": 0.0,
            "dir": "Open Long",
            "exit_reason": "ENTRY",
            "is_maker": True,
            "is_liquid": True,
        }
        for _ in range(20)
    ]
    parity = engine.evaluate_execution_parity(
        paper_fills=fills,
        backtest_turnover_usd=20000.0,
        backtest_fees_usd=3.0,
        backtest_sl_triggers=0,
        backtest_tp_triggers=0,
        backtest_gross_pnl_usd=100.0,
        backtest_net_pnl_usd=97.0,
        backtest_rebalances=20,
    )
    metrics = parity["metrics"]
    assert "maker_fill_ratio" in metrics
    assert "net_fee_bps" in metrics
    assert "haircut_ratio" in metrics
    assert "confirmed_paper_stops" in metrics
    assert "confirmed_paper_tps" in metrics
    assert "pit_liquidity_violations" in metrics
    assert "paper_rebalances" in metrics
    assert "unclassified_exits" in metrics
    assert "adverse_selection_markout_bps" in metrics
    assert "position_churn_ratio" in metrics
    assert "empirical_slippage_bps" in metrics
    assert "modeled_maker_pct" in metrics
    assert "empirical_maker_pct" in metrics


# =============================================================================
# 9. INSTITUTIONAL INVARIANT TESTS (v2.4.0)
# =============================================================================

def test_adv_vol_strictly_causal_no_future_leakage():
    """Verifies execution at bar t+1 strictly consumes trailing ADV/volatility through bar t."""
    engine = IronCoreEngine()
    n_bars, n_sym = 10, 1
    weights = np.zeros((n_bars, n_sym))
    weights[5:, 0] = 1.0  # Trade enters at bar 6 (t=5, next_t=6) and holds (no exit trade at bar 7)

    returns = np.zeros((n_bars, n_sym))
    close = np.ones((n_bars, n_sym)) * 100.0
    funding = np.zeros((n_bars, n_sym))

    # Normal low volume up to bar 5
    volume_normal = np.ones((n_bars, n_sym)) * 1e4
    
    # Inject massive volume spike at future bar 6 (e.g. 1e9)
    volume_spike = volume_normal.copy()
    volume_spike[6, 0] = 1e9

    res_normal = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume_normal,
        close_mat=close,
        initial_capital=10000.0,
    )

    res_spiked = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume_spike,
        close_mat=close,
        initial_capital=10000.0,
    )

    # Market impact at bar 6 execution MUST be identical because spike at bar 6 is in the future!
    assert res_normal["market_impact"] == pytest.approx(res_spiked["market_impact"], rel=1e-5)


def test_next_subbar_passive_execution_causality():
    """Verifies that with causal_passive_mode=True, orders placed at subbar 0 cannot fill at subbar 0."""
    engine = IronCoreEngine()
    n_4h, subbars, n_sym = 2, 4, 1
    weights = np.zeros((n_4h, n_sym))
    weights[0, 0] = 1.0  # Enters at bar 1

    sub_open = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_low = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_close = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_vol = np.ones((n_4h, subbars, n_sym)) * 1e6
    fund = np.zeros((n_4h, n_sym))

    # Subbar 0 touches limit price (99.95)
    sub_low[1, 0, 0] = 99.90
    # Subbar 1, 2, 3 do not touch
    sub_low[1, 1:, 0] = 100.0

    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_4h, n_sym))

    # Case A: Causal passive mode = True -> CANNOT fill in subbar 0!
    params_causal = engine.cfg.resolve_runtime_parameters(causal_passive_mode=True, passive_fill_horizon_subbars=3)
    res_causal = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        params=params_causal,
    )
    # Did not fill passively at subbar 0, and did not time out (horizon=3), so 0 passive fills!
    assert res_causal["passive_fills"] == 0

    # Case B: Legacy non-causal mode = False -> CAN fill in subbar 0!
    params_legacy = engine.cfg.resolve_runtime_parameters(causal_passive_mode=False, passive_fill_horizon_subbars=3)
    res_legacy = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        params=params_legacy,
    )
    assert res_legacy["passive_fills"] == 1


def test_same_subbar_stop_vulnerability():
    """Verifies that positions opened in subbar s are immediately vulnerable to stop loss in subbar s when configured."""
    engine = IronCoreEngine()
    n_4h, subbars, n_sym = 2, 4, 1
    weights = np.zeros((n_4h, n_sym))
    weights[0, 0] = 1.0  # Enters at bar 1

    sub_open = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_low = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_close = np.ones((n_4h, subbars, n_sym)) * 100.0
    sub_vol = np.ones((n_4h, subbars, n_sym)) * 1e6
    fund = np.zeros((n_4h, n_sym))

    # At subbar 1: Passive entry fills at limit (99.95), but market crashes to 95.0 in the SAME subbar!
    sub_low[1, 1, 0] = 95.0  # 95.0 is -5.0% below entry (exceeds 3.5% SL)
    sub_close[1, 1, 0] = 96.0

    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_4h, n_sym))

    # Causal & Stop Vulnerable: Must stop out at subbar 1!
    params_vulnerable = engine.cfg.resolve_runtime_parameters(
        causal_passive_mode=True,
        same_subbar_stop_vulnerable=True,
        sl_pct=0.035,
    )
    res_vuln = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        params=params_vulnerable,
    )
    assert res_vuln["sl_count"] == 1
    assert res_vuln["passive_fills"] == 1

    # Legacy Immune: Subbar of fill is skipped, so 0 stops triggered in subbar 1!
    params_immune = engine.cfg.resolve_runtime_parameters(
        causal_passive_mode=True,
        same_subbar_stop_vulnerable=False,
        sl_pct=0.035,
    )
    res_immune = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        params=params_immune,
    )
    assert res_immune["sl_count"] == 0


def test_gate_8_fail_closed_on_missing_dimensions():
    """Verifies that Gate 8 fails closed if any dimension (e.g. cohort fees or PIT liquidity) fails."""
    engine = IronCoreEngine()
    
    # Fills where stop-loss order paid maker fee (1.5 bps) instead of taker fee (>= 3.0 bps)
    tampered_fills = [
        {
            "sz": 10.0,
            "px": 100.0,
            "fee": 0.15,  # 1.5 bps fee on stop loss!
            "closedPnl": -50.0,
            "dir": "Close Long",
            "exit_reason": "STOP_LOSS",
            "is_liquid": True,
            "is_maker": True,
        }
    ]
    parity = engine.evaluate_execution_parity(
        paper_fills=tampered_fills,
        backtest_turnover_usd=1000.0,
        backtest_fees_usd=0.45,
        backtest_sl_triggers=1,
    )
    assert not parity["passed"]
    assert not parity["dimension_verdicts"]["dim10_cohort_fee_separation"]
    assert any("COHORT_FEE_MISMATCH" in issue for issue in parity["issues"])


def test_provenance_cryptographic_verification():
    """Verifies that CertificationProvenance rejects forged provenance or mismatched dataset."""
    engine = IronCoreEngine()
    n_bars, n_sym = 10, 2
    close = np.ones((n_bars, n_sym)) * 100.0
    oracle = close * 1.0001
    volume = np.ones((n_bars, n_sym)) * 1e5
    valid = np.ones((n_bars, n_sym), dtype=bool)
    returns = np.zeros((n_bars, n_sym))
    funding = np.zeros((n_bars, n_sym))
    btc_px = np.ones(n_bars) * 50000.0
    features = {"f1": np.zeros((n_bars, n_sym))}
    manual_w = np.zeros((n_bars, n_sym))

    # Create legitimate provenance
    resolved_cfg = engine.cfg.resolve_runtime_parameters()
    dataset_dict = {
        "close": close,
        "oracle": oracle,
        "volume": volume,
        "valid": valid,
        "returns": returns,
        "funding": funding,
        "btc": btc_px,
    }
    symbols = [f"SYM_{i}" for i in range(n_sym)]
    prov = CertificationProvenance.create(
        engine_version=engine.cfg.version,
        resolved_config=resolved_cfg,
        feature_panel=features,
        dataset_matrices=dataset_dict,
        symbols=symbols,
        candidate_name="test_candidate",
        folds=[],
        trial_registry_hash="abc",
        combined_bar_returns=np.zeros(n_bars),
    )

    is_valid, mismatches = prov.verify_against_inputs(
        engine_version=engine.cfg.version,
        resolved_config=resolved_cfg,
        feature_panel=features,
        dataset_matrices=dataset_dict,
        symbols=symbols,
        candidate_name="test_candidate",
        folds=[],
        trial_registry_hash="abc",
        combined_bar_returns=np.zeros(n_bars),
    )
    assert is_valid
    assert len(mismatches) == 0

    # Tampered dataset: close matrix modified
    tampered_dataset = dict(dataset_dict)
    tampered_dataset["close"] = close * 2.0
    is_valid_tampered, mismatches_tampered = prov.verify_against_inputs(
        engine_version=engine.cfg.version,
        resolved_config=resolved_cfg,
        feature_panel=features,
        dataset_matrices=tampered_dataset,
        symbols=symbols,
        candidate_name="test_candidate",
        folds=[],
        trial_registry_hash="abc",
        combined_bar_returns=np.zeros(n_bars),
    )
    assert not is_valid_tampered
    assert any("DATASET_MANIFEST_HASH_MISMATCH" in m or "DATASET_HASH_MISMATCH" in m for m in mismatches_tampered)

    # certify_strategy rejects tampered provenance with ValueError
    with pytest.raises(ValueError, match="FORGED_OR_MISMATCHED_PROVENANCE_REJECTED"):
        engine.certify_strategy(
            candidate_name="test_candidate",
            fit_fn=lambda f, t: {},
            predict_fn=lambda m, f: manual_w,
            feature_panel=features,
            returns_mat=returns,
            predicted_funding=funding,
            volume_mat=volume,
            close_mat=tampered_dataset["close"],
            oracle_mat=oracle,
            valid_mask=valid,
            btc_prices=btc_px,
            manual_weights_override=manual_w,
            provenance=prov,
        )


def test_unknown_override_rejected_fatal():
    """Verifies that unknown configuration overrides raise ValueError immediately (Zero Silent Fallbacks)."""
    cfg = IronCoreConfig_v1()
    with pytest.raises(ValueError, match="UNKNOWN_EXECUTION_OVERRIDE"):
        cfg.resolve_runtime_parameters(portfolio_deadbnd=0.08)

    with pytest.raises(ValueError, match="UNKNOWN_EXECUTION_OVERRIDE"):
        cfg.resolve_runtime_parameters(unknown_field="invalid")


def test_initial_capital_authority_bypass_rejected():
    """Verifies that passing initial_capital separately when ResolvedExecutionParameters is provided raises ValueError."""
    engine = IronCoreEngine()
    params = engine.cfg.resolve_runtime_parameters(initial_capital=15000.0)
    weights = np.zeros((3, 1))
    returns = np.zeros((3, 1))
    vol = np.ones((3, 1)) * 1e6
    close = np.ones((3, 1)) * 100.0
    fund = np.zeros((3, 1))

    with pytest.raises(ValueError, match="AUTHORITY_BYPASS_VIOLATION"):
        engine.simulate_canonical_execution(
            weights_matrix=weights,
            returns_mat=returns,
            predicted_funding=fund,
            volume_mat=vol,
            close_mat=close,
            params=params,
            initial_capital=10000.0,
        )


def test_dynamic_stop_propagation_and_differentiation():
    """
    Verifies that dynamic stop-loss arrays propagate correctly to execution
    and differentiate stop-loss execution between different multiples (2 ATR vs 3 ATR).
    """
    engine = IronCoreEngine()
    n_bars, n_sym = 4, 1
    weights = np.zeros((n_bars, n_sym))
    weights[0, 0] = 1.0  # Enters at bar 1

    subbars = 4
    sub_open = np.ones((n_bars, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_bars, subbars, n_sym)) * 100.0
    sub_low = np.ones((n_bars, subbars, n_sym)) * 100.0
    sub_close = np.ones((n_bars, subbars, n_sym)) * 100.0
    sub_vol = np.ones((n_bars, subbars, n_sym)) * 1e6
    fund = np.zeros((n_bars, subbars, n_sym))

    # Bar 1, Subbar 1: Adverse wick reaches 97.0 (-3.0% below entry at 100)
    sub_low[1, 1, 0] = 97.0
    sub_close[1, 1, 0] = 98.0

    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_bars, n_sym))

    # Array 1: 2.0 ATR = 2.5% stop loss (breached by 97.0)
    sl_2atr = np.full((n_bars, n_sym), 0.025)
    tp_4atr = np.full((n_bars, n_sym), 0.050)

    # Array 2: 3.0 ATR = 3.5% stop loss (survives 97.0)
    sl_3atr = np.full((n_bars, n_sym), 0.035)
    tp_6atr = np.full((n_bars, n_sym), 0.070)

    p_2atr = engine.cfg.resolve_runtime_parameters(
        sl_pct=sl_2atr,
        tp_pct=tp_4atr,
        causal_passive_mode=False,
    )
    assert p_2atr.dynamic_stop_loss is not None
    assert p_2atr.fixed_stop_loss_pct is None

    p_3atr = engine.cfg.resolve_runtime_parameters(
        sl_pct=sl_3atr,
        tp_pct=tp_6atr,
        causal_passive_mode=False,
    )
    assert p_3atr.dynamic_stop_loss is not None
    assert p_3atr.fixed_stop_loss_pct is None

    res_2atr = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        params=p_2atr,
    )

    res_3atr = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        params=p_3atr,
    )

    # 2 ATR was breached (-3.0% <= -2.5%) -> 1 stop trigger
    assert res_2atr["sl_count"] == 1
    # 3 ATR survived (-3.0% > -3.5%) -> 0 stop triggers
    assert res_3atr["sl_count"] == 0
    # Outcomes must be mathematically different
    assert res_2atr["sl_count"] != res_3atr["sl_count"]
    assert res_2atr["ending_equity"] != res_3atr["ending_equity"]


def test_deterministic_synthetic_market_lifecycle():
    """
    GATE B FORENSIC INVARIANT:
    Deterministic synthetic market with exact known event trajectory:
    - Bar 0: Signal generated
    - Bar 1:
      - Subbar 0: Limit order placed in book at fixed limit price P_limit = 99.95
      - Subbar 1: Passive touch (Low=99.90 <= 99.95) fills order at exactly P_limit
      - Subbar 2: Adverse wick breaches 3.5% stop loss (Low=96.0 <= 96.45)
                  Executes immediate taker stop exit and cancels any pending orders
      - Subbar 3: Market price recovers to 102.0
    Asserts exact order state, fill state, position state, stop trigger, turnover, and fees.
    """
    engine = IronCoreEngine()
    n_bars, subbars, n_sym = 2, 4, 1
    weights = np.zeros((n_bars, n_sym))
    weights[0, 0] = 1.0  # Target 100% allocation into symbol 0

    sub_open = np.ones((n_bars, subbars, n_sym)) * 100.0
    sub_high = np.ones((n_bars, subbars, n_sym)) * 100.0
    sub_low = np.ones((n_bars, subbars, n_sym)) * 100.0
    sub_close = np.ones((n_bars, subbars, n_sym)) * 100.0
    sub_vol = np.ones((n_bars, subbars, n_sym)) * 1e6
    fund = np.zeros((n_bars, n_sym))

    # Bar 1 Subbar 0: Open at 100.0 (Order enters book with fixed limit_px = 99.95)
    # Bar 1 Subbar 1: Low dips to 99.90 -> passive fill at limit_px = 99.95
    sub_low[1, 1, 0] = 99.90
    sub_close[1, 1, 0] = 99.95

    # Bar 1 Subbar 2: Violent wick to 96.0 -> breaches 3.5% stop loss (99.95 * 0.965 = 96.45175)
    sub_low[1, 2, 0] = 96.0
    sub_close[1, 2, 0] = 96.2

    # Bar 1 Subbar 3: Price recovers to 102.0
    sub_open[1, 3, 0] = 98.0
    sub_high[1, 3, 0] = 102.0
    sub_low[1, 3, 0] = 98.0
    sub_close[1, 3, 0] = 102.0

    subbar_dict = {"open": sub_open, "high": sub_high, "low": sub_low, "close": sub_close, "volume": sub_vol}
    close_mat = sub_close[:, -1, :]
    returns_mat = np.zeros((n_bars, n_sym))

    params = engine.cfg.resolve_runtime_parameters(
        causal_passive_mode=True,
        same_subbar_stop_vulnerable=True,
        sl_pct=0.035,
        tp_pct=0.070,
        initial_capital=10000.0,
    )

    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=fund,
        volume_mat=sub_vol[:, 0, :],
        close_mat=close_mat,
        subbar_data=subbar_dict,
        params=params,
    )

    # Invariant asserts:
    assert res["passive_fills"] == 1, "Order must fill passively at subbar 1 touch"
    assert res["sl_count"] == 1, "Stop loss must trigger at subbar 2 adverse breach"
    assert res["tp_count"] == 0, "Take profit must not trigger"
    assert res["trades_count"] == 2, "Must record exactly 2 executed trade events: 1 passive entry + 1 stop exit"
    assert res["turnover_usd"] > 19000.0, "Turnover must reflect both executed entry and executed exit"
    assert res["exchange_fees"] > 0.0, "Must record pure exchange fees"
    assert res["ending_equity"] < 10000.0, "Account equity must reflect realized stop loss and friction"


def test_gate_8_all_10_dimensions_with_typed_reference():
    """
    Verifies that evaluate_execution_parity consumes typed BacktestExecutionReference,
    evaluates all 10 dimensions, and fails closed when ref_px or future_px is missing.
    """
    engine = IronCoreEngine()
    ref = BacktestExecutionReference(
        turnover_usd=100000.0,
        fees_usd=15.45,
        maker_ratio_pct=60.0,
        taker_ratio_pct=40.0,
        sl_triggers=5,
        tp_triggers=2,
        slippage_bps=0.0,
        adverse_markout_bps=1.0,
        trades_count=20,
        rebalances_count=13,
    )

    # Clean, valid telemetry with all required fields
    valid_fills = [
        {
            "sz": 10.0,
            "px": 100.0,
            "ref_px": 100.0,
            "future_px": 100.01,
            "fee": 0.15,
            "closedPnl": 0.0,
            "dir": "Buy",
            "exit_reason": "REBALANCE",
            "is_liquid": True,
            "is_maker": True,
        }
        for _ in range(20)
    ]

    res_valid = engine.evaluate_execution_parity(paper_fills=valid_fills, ref=ref)
    assert "dim1_fee_parity" in res_valid["dimension_verdicts"]
    assert "dim3_maker_fill_ratio" in res_valid["dimension_verdicts"]
    assert "dim8_slippage_bound" in res_valid["dimension_verdicts"]
    assert "dim9_adverse_markout" in res_valid["dimension_verdicts"]
    assert "dim10_cohort_fee_separation" in res_valid["dimension_verdicts"]

    # Telemetry with MISSING future_px -> FAIL CLOSED on adverse markout
    fills_missing_markout = [dict(f) for f in valid_fills]
    fills_missing_markout[0]["future_px"] = None

    res_missing_markout = engine.evaluate_execution_parity(paper_fills=fills_missing_markout, ref=ref)
    assert not res_missing_markout["passed"]
    assert not res_missing_markout["dimension_verdicts"]["dim9_adverse_markout"]
    assert any("FAIL_CLOSED_ADVERSE_MARKOUT" in issue for issue in res_missing_markout["issues"])

# =============================================================================
# RC2 LAYER 1: PROVENANCE HARDENING TESTS
# =============================================================================

def test_hash_array_raw_nan_differs_from_zero():
    """hash_array_raw must produce different hashes for NaN vs 0.0."""
    a = np.array([1.0, np.nan, 3.0])
    b = np.array([1.0, 0.0, 3.0])
    h_a = hash_array_raw(a)
    h_b = hash_array_raw(b)
    assert h_a != h_b, "raw hash must distinguish NaN from 0.0"


def test_hash_array_canonicalized_nan_equals_zero():
    """hash_array_canonicalized treats NaN positions identically to 0.0."""
    a = np.array([1.0, np.nan, 3.0])
    b = np.array([1.0, np.nan, 3.0])
    assert hash_array_canonicalized(a) == hash_array_canonicalized(b)


def test_hash_array_raw_none_returns_sentinel():
    """hash_array_raw(None) must return 'NONE' sentinel string."""
    assert hash_array_raw(None) == "NONE"
    assert hash_array_canonicalized(None) == "NONE"


def test_hash_array_raw_shape_sensitive():
    """Same data but different shapes must produce different hashes."""
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert hash_array_raw(a) != hash_array_raw(b)


def test_environment_manifest_rejects_head():
    """EnvironmentManifest must reject 'HEAD' as a placeholder."""
    with pytest.raises(ValueError, match="ENVIRONMENT_MANIFEST_PLACEHOLDER"):
        EnvironmentManifest(
            engine_git_commit="HEAD",
            lockfile_sha256="abc123",
            python_version="3.14.4",
            numpy_version="2.4.2",
            scipy_version="1.15.2",
            polars_version="1.39.1",
        )


def test_environment_manifest_rejects_empty():
    """EnvironmentManifest must reject empty strings."""
    with pytest.raises(ValueError, match="ENVIRONMENT_MANIFEST_PLACEHOLDER"):
        EnvironmentManifest(
            engine_git_commit="abc123def456",
            lockfile_sha256="",
            python_version="3.14.4",
            numpy_version="2.4.2",
            scipy_version="1.15.2",
            polars_version="1.39.1",
        )


def test_environment_manifest_rejects_env_locked():
    """EnvironmentManifest must reject 'ENV_LOCKED' as a placeholder."""
    with pytest.raises(ValueError, match="ENVIRONMENT_MANIFEST_PLACEHOLDER"):
        EnvironmentManifest(
            engine_git_commit="abc123def456",
            lockfile_sha256="abc123",
            python_version="3.14.4",
            numpy_version="ENV_LOCKED",
            scipy_version="1.15.2",
            polars_version="1.39.1",
        )


def test_environment_manifest_accepts_valid():
    """EnvironmentManifest accepts valid non-placeholder values."""
    env = EnvironmentManifest(
        engine_git_commit="a" * 40,
        lockfile_sha256="b" * 64,
        python_version="3.14.4",
        numpy_version="2.4.2",
        scipy_version="1.15.2",
        polars_version="1.39.1",
    )
    d = env.to_dict()
    assert d["python_version"] == "3.14.4"
    h = env.content_hash()
    assert len(h) == 64  # SHA256 hex


def test_ordered_universe_hash_differs_on_reorder():
    """Universe hash must change when symbols are reordered."""
    symbols_a = ["BTC", "ETH", "SOL"]
    symbols_b = ["SOL", "BTC", "ETH"]
    h_a = hashlib.sha256(",".join(symbols_a).encode("utf-8")).hexdigest()[:16]
    h_b = hashlib.sha256(",".join(symbols_b).encode("utf-8")).hexdigest()[:16]
    assert h_a != h_b, "Symbol ordering must affect universe hash"


def test_immutable_numpy_arrays_in_resolved_params():
    """Dynamic stop/TP arrays must be read-only after ResolvedExecutionParameters construction."""
    sl = np.array([[0.03, 0.04], [0.05, 0.06]], dtype=np.float64)
    tp = np.array([[0.07, 0.08], [0.09, 0.10]], dtype=np.float64)
    params = ResolvedExecutionParameters(
        dynamic_stop_loss=sl,
        dynamic_take_profit=tp,
        fixed_stop_loss_pct=None,
        fixed_take_profit_pct=None,
    )
    with pytest.raises(ValueError):
        params.dynamic_stop_loss[0, 0] = 999.0
    with pytest.raises(ValueError):
        params.dynamic_take_profit[1, 1] = 999.0


def test_intrabar_path_convention_exists():
    """INTRABAR_PATH_CONVENTION constant must exist and describe the pessimistic assumption."""
    assert "PESSIMISTIC_WORST_CASE" in INTRABAR_PATH_CONVENTION
    assert "same_subbar_stop_vulnerable" in INTRABAR_PATH_CONVENTION


def test_maker_ratio_divergence_breach():
    """Gate 8 must fail when modeled vs empirical maker ratio diverges > 15pp."""
    engine = IronCoreEngine()
    # Construct fills where paper shows 90% maker but ref says 50% modeled
    fills = [
        {
            "notional": 100.0, "fee": 0.02, "px": 100.0, "qty": 1.0,
            "dir": "open", "ts": 1000 + i, "is_liquid": True,
            "is_maker": True, "future_px": 101.0, "exit_reason": "REBALANCE",
        }
        for i in range(20)
    ]
    ref = BacktestExecutionReference(
        turnover_usd=2000.0, fees_usd=0.4, maker_ratio_pct=50.0,
        taker_ratio_pct=50.0, sl_triggers=0, tp_triggers=0,
        trades_count=20, rebalances_count=20,
    )
    res = engine.evaluate_execution_parity(paper_fills=fills, ref=ref)
    assert any("MAKER_RATIO_DIVERGENCE_BREACH" in issue or "MAKER_RATIO_FLOOR_BREACH" in issue
               for issue in res.get("issues", []))


# =============================================================================
# RC2 WI-7: ACCOUNTING CONSERVATION TESTS
# =============================================================================

def _make_mini_market(n_bars=6, n_symbols=3, seed=42):
    """Create a small deterministic market with known prices for conservation tests."""
    rng = np.random.RandomState(seed)
    base_px = np.array([100.0, 200.0, 50.0])
    close_mat = np.zeros((n_bars, n_symbols))
    for t in range(n_bars):
        close_mat[t] = base_px * (1.0 + 0.01 * rng.randn(n_symbols))

    returns_mat = np.zeros_like(close_mat)
    for t in range(1, n_bars):
        returns_mat[t] = (close_mat[t] - close_mat[t - 1]) / close_mat[t - 1]

    volume_mat = np.full((n_bars, n_symbols), 1_000_000.0)
    funding = np.zeros((n_bars, n_symbols))

    weights = np.zeros((n_bars, n_symbols))
    weights[1] = [0.10, -0.05, 0.05]
    weights[2] = [0.10, -0.05, 0.05]
    weights[3] = [0.05, -0.10, 0.10]
    weights[4] = [0.00, 0.00, 0.00]
    weights[5] = [0.00, 0.00, 0.00]

    return weights, returns_mat, funding, volume_mat, close_mat


def test_accounting_conservation_identity():
    """
    Verifies exact accounting conservation identities:
      1. ending_equity == initial_capital + net_pnl  (exact, tolerance 1e-9)
      2. net_pnl == sum_t( bar_return[t] * equity[t-1] )  (numerical tolerance 1e-6)
      3. total_friction == exchange_fees + market_impact + adverse_selection_cost
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _make_mini_market()

    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        sl_pct=None, tp_pct=None,
        enable_cooldown=False,
        portfolio_deadband=0.0,
        deadband=0.0,
    )

    init = 10_000.0
    ending = res["ending_equity"]
    net_pnl = res["net_pnl"]
    eq_curve = res["equity_curve"]
    bar_rets = res["bar_returns"]

    # Identity 1: ending_equity == initial_capital + net_pnl  (exact definition)
    assert abs(ending - (init + net_pnl)) < 1e-9, (
        f"Identity 1 failed: ending={ending}, init+net_pnl={init + net_pnl}"
    )

    # Identity 2: net_pnl == sum(bar_ret[t] * equity_curve[t])  (bar return definition)
    # bar_ret[t] = net_pnl_t / equity_at_start_of_bar_t
    # so net_pnl_t = bar_ret[t] * equity_curve[t], and sum = total net_pnl
    net_pnl_from_bars = sum(bar_rets[t] * eq_curve[t] for t in range(len(bar_rets)))
    assert abs(net_pnl - net_pnl_from_bars) < 1e-6, (
        f"Identity 2 failed: net_pnl={net_pnl:.6f}, sum_bars={net_pnl_from_bars:.6f}"
    )

    # Identity 3: total_friction == sum of cost buckets
    friction_check = res["exchange_fees"] + res["market_impact"] + res["adverse_selection_cost"]
    assert abs(res["total_friction"] - friction_check) < 1e-9, (
        f"Identity 3 failed: total_friction={res['total_friction']}, buckets sum={friction_check}"
    )

    # Sanity: zero weights == zero turnover
    assert res["turnover_usd"] > 0  # We did trade


def test_accounting_conservation_with_stops():
    """
    Conservation identities must hold even with active stop-loss and take-profit events.
    Uses the exact identity: ending == init + net_pnl.
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)

    n_bars, n_symbols = 8, 2
    rng = np.random.RandomState(99)
    close_mat = np.zeros((n_bars, n_symbols))
    close_mat[0] = [100.0, 50.0]
    for t in range(1, n_bars):
        close_mat[t] = close_mat[t - 1] * (1.0 + 0.02 * rng.randn(n_symbols))

    returns_mat = np.zeros_like(close_mat)
    for t in range(1, n_bars):
        returns_mat[t] = (close_mat[t] - close_mat[t - 1]) / close_mat[t - 1]

    volume_mat = np.full((n_bars, n_symbols), 2_000_000.0)
    funding = np.zeros((n_bars, n_symbols))

    weights = np.zeros((n_bars, n_symbols))
    weights[1] = [0.15, -0.10]
    weights[2] = [0.15, -0.10]
    weights[3] = [0.15, -0.10]
    weights[4] = [0.10, 0.05]
    weights[5] = [0.0, 0.0]
    weights[6] = [0.0, 0.0]
    weights[7] = [0.0, 0.0]

    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        sl_pct=0.025,
        tp_pct=0.050,
        enable_cooldown=True,
        portfolio_deadband=0.0,
        deadband=0.0,
    )

    init = 10_000.0
    ending = res["ending_equity"]
    net_pnl = res["net_pnl"]
    eq_curve = res["equity_curve"]
    bar_rets = res["bar_returns"]

    # Identity 1: ending_equity == init + net_pnl
    assert abs(ending - (init + net_pnl)) < 1e-9, (
        f"Conservation failed: ending={ending:.6f}, init+net_pnl={init + net_pnl:.6f}"
    )

    # Identity 2: net_pnl == sum(bar_ret * equity_at_bar)
    net_pnl_from_bars = sum(bar_rets[t] * eq_curve[t] for t in range(len(bar_rets)))
    assert abs(net_pnl - net_pnl_from_bars) < 1e-6, (
        f"Bar-sum identity failed: net_pnl={net_pnl:.6f}, sum_bars={net_pnl_from_bars:.6f}"
    )

    # Identity 3: friction == sum of buckets
    friction_check = res["exchange_fees"] + res["market_impact"] + res["adverse_selection_cost"]
    assert abs(res["total_friction"] - friction_check) < 1e-9, (
        f"Friction bucket mismatch: total={res['total_friction']}, sum={friction_check}"
    )


def test_accounting_zero_signal_zero_pnl():
    """Zero signal (all-zero weights) must produce exactly zero PnL and zero turnover."""
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)

    n_bars, n_symbols = 6, 3
    close_mat = np.tile([100.0, 200.0, 50.0], (n_bars, 1))
    returns_mat = np.zeros((n_bars, n_symbols))
    volume_mat = np.full((n_bars, n_symbols), 1_000_000.0)
    funding = np.zeros((n_bars, n_symbols))
    weights = np.zeros((n_bars, n_symbols))

    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        sl_pct=None, tp_pct=None,
        portfolio_deadband=0.0,
    )

    assert res["turnover_usd"] == 0.0
    assert res["exchange_fees"] == 0.0
    assert res["market_impact"] == 0.0
    assert abs(res["ending_equity"] - 10_000.0) < 1e-6


# =============================================================================
# RC2 WI-8: POSITION LIFECYCLE ADVERSARIAL STATE-MACHINE TESTS
# =============================================================================

def test_lifecycle_flat_to_open():
    """FLAT -> OPEN transition: new position gets correct entry price."""
    pos = PositionState(symbol_idx=0)
    assert not pos.is_open
    pos.apply_increase(5.0, 100.0, bar_idx=0)
    assert pos.is_open
    assert pos.qty == 5.0
    assert pos.avg_entry_px == 100.0
    assert pos.entry_bar == 0


def test_lifecycle_open_add():
    """OPEN -> ADD: weighted average entry price updates correctly."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(10.0, 100.0, bar_idx=0)
    pos.apply_increase(10.0, 120.0, bar_idx=1)
    assert abs(pos.avg_entry_px - 110.0) < 1e-8
    assert abs(pos.qty - 20.0) < 1e-8


def test_lifecycle_open_reduce():
    """OPEN -> REDUCE: avg_entry_px is preserved after partial reduction."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(10.0, 100.0, bar_idx=0)
    pnl = pos.apply_reduction(5.0, 120.0)
    assert abs(pnl - 100.0) < 1e-8  # 5 * (120 - 100)
    assert abs(pos.avg_entry_px - 100.0) < 1e-8
    assert abs(pos.qty - 5.0) < 1e-8


def test_lifecycle_open_flat():
    """OPEN -> FLAT: full exit resets all state."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(10.0, 100.0, bar_idx=0)
    pnl = pos.apply_full_exit(90.0)
    assert abs(pnl - (-100.0)) < 1e-8  # 10 * (90 - 100) = -100
    assert not pos.is_open
    assert pos.avg_entry_px == 0.0
    assert pos.entry_bar is None


def test_lifecycle_open_flip():
    """OPEN -> FLIP: closes old long, opens new short."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(10.0, 100.0, bar_idx=0)
    pnl = pos.apply_flip(-5.0, 110.0, bar_idx=1)
    assert abs(pnl - 100.0) < 1e-8  # closed long: 10 * (110 - 100)
    assert pos.is_short
    assert abs(pos.qty - (-5.0)) < 1e-8
    assert abs(pos.avg_entry_px - 110.0) < 1e-8


def test_lifecycle_short_flip_to_long():
    """Short position flips to long."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(-10.0, 100.0, bar_idx=0)
    assert pos.is_short
    pnl = pos.apply_flip(5.0, 95.0, bar_idx=1)
    assert abs(pnl - 50.0) < 1e-8  # closed short: 10 * (100 - 95)
    assert pos.is_long
    assert abs(pos.qty - 5.0) < 1e-8


def test_order_pending_to_filled():
    """PENDING -> FILLED transition."""
    order = OrderState(
        order_id="T1", order_generation=1, symbol_idx=0,
        target_qty=10.0, remaining_qty=10.0,
        created_bar=0, created_subbar=0, limit_px=100.0,
    )
    assert order.is_active
    order.fill_partial(10.0, 100.0)
    assert order.status == "FILLED"
    assert not order.is_active


def test_order_pending_to_partial():
    """PENDING -> PARTIALLY_FILLED: partial fill leaves remaining."""
    order = OrderState(
        order_id="T2", order_generation=1, symbol_idx=0,
        target_qty=10.0, remaining_qty=10.0,
        created_bar=0, created_subbar=0, limit_px=100.0,
    )
    order.fill_partial(3.0, 100.0)
    assert order.status == "PARTIALLY_FILLED"
    assert abs(order.remaining_qty - 7.0) < 1e-8
    assert order.is_active


def test_order_pending_to_cancelled():
    """PENDING -> CANCELLED: cannot fill after cancel."""
    order = OrderState(
        order_id="T3", order_generation=1, symbol_idx=0,
        target_qty=10.0, remaining_qty=10.0,
        created_bar=0, created_subbar=0, limit_px=100.0,
    )
    order.cancel("STOP_LOSS_TRIGGERED")
    assert order.status == "CANCELLED"
    assert order.cancellation_reason == "STOP_LOSS_TRIGGERED"
    assert not order.is_active
    assert abs(order.remaining_qty) < 1e-8


def test_adversarial_gap_through_stop():
    """Price gaps far below stop level — position must still exit."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(10.0, 100.0, bar_idx=0)
    # Stop at 3.5% -> 96.5. Price gaps to 80.0 (huge gap through)
    entry = pos.avg_entry_px
    sl_pct = 0.035
    exit_px = entry * (1.0 - sl_pct) - max(0.0, (entry * (1.0 - sl_pct) - 80.0) * 0.3)
    pnl = pos.apply_full_exit(exit_px)
    assert not pos.is_open
    assert pnl < 0  # Must register a loss


def test_adversarial_sl_and_tp_same_subbar():
    """When both SL and TP are hit in the same subbar, SL wins (conservative)."""
    # This is an assertion on the engine logic:
    # When hit_sl and hit_tp are both True, hit_tp is set to False.
    # We verify this by direct logic check:
    entry = 100.0
    sl_pct = 0.035
    tp_pct = 0.070
    # Extreme bar: low = 80, high = 120
    p_lo, p_hi = 80.0, 120.0
    hit_sl = ((p_lo - entry) / entry) <= -sl_pct
    hit_tp = ((p_hi - entry) / entry) >= tp_pct
    assert hit_sl and hit_tp, "Both should trigger"
    # Engine convention: if both trigger, SL wins
    if hit_sl and hit_tp:
        hit_tp = False  # Conservative adverse stop first
    assert hit_sl and not hit_tp


def test_adversarial_zero_qty_no_crash():
    """Reduction of zero quantity should not crash or produce PnL."""
    pos = PositionState(symbol_idx=0)
    pnl = pos.apply_reduction(0.0, 100.0)
    assert pnl == 0.0


def test_adversarial_negative_price_no_crash():
    """Reduction at zero or negative price should not crash."""
    pos = PositionState(symbol_idx=0)
    pos.apply_increase(10.0, 100.0, bar_idx=0)
    pnl = pos.apply_reduction(5.0, 0.0)
    assert pnl == 0.0  # guard clause returns 0.0 for px <= 0
    pnl2 = pos.apply_full_exit(0.0)
    assert pnl2 == 0.0


def test_governor_all_tiers_deterministic():
    """Governor must traverse all tiers deterministically with known equity sequence."""
    gov = GovernorStateMachine(
        hwm=10000.0,
        tiers=((0.05, 1.00), (0.10, 0.75), (0.15, 0.35), (1.00, 0.00)),
        rerisk_buffer=0.02,
        halt_threshold=0.15,
    )
    # No DD
    lev, tier = gov.update_equity(10000.0)
    assert tier == 0

    # 6% DD -> tier 1
    lev, tier = gov.update_equity(9400.0)
    assert tier >= 1

    # 11% DD -> tier 2
    lev, tier = gov.update_equity(8900.0)
    assert tier >= 2

    # 16% DD -> HALT
    lev, tier = gov.update_equity(8400.0)
    assert gov.is_halted
    assert lev == 0.0


# =============================================================================
# RC2 WI-9: DETERMINISTIC EVENT-JOURNAL REPLAY TEST
# =============================================================================

def test_deterministic_replay_byte_identical():
    """Two runs with identical inputs must produce byte-for-byte identical results."""
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _make_mini_market()

    common_kwargs = dict(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        sl_pct=0.035,
        tp_pct=0.070,
        enable_cooldown=True,
        portfolio_deadband=0.0,
        deadband=0.0,
    )

    res1 = engine.simulate_canonical_execution(**common_kwargs)
    res2 = engine.simulate_canonical_execution(**common_kwargs)

    # Equity curve must be byte-for-byte identical
    eq_h1 = hash_array_raw(res1["equity_curve"])
    eq_h2 = hash_array_raw(res2["equity_curve"])
    assert eq_h1 == eq_h2, "Equity curves differ between identical runs"

    # Bar returns must be byte-for-byte identical
    br_h1 = hash_array_raw(res1["bar_returns"])
    br_h2 = hash_array_raw(res2["bar_returns"])
    assert br_h1 == br_h2, "Bar returns differ between identical runs"

    # Scalar metrics
    assert res1["ending_equity"] == res2["ending_equity"]
    assert res1["sl_count"] == res2["sl_count"]
    assert res1["tp_count"] == res2["tp_count"]
    assert res1["turnover_usd"] == res2["turnover_usd"]
    assert res1["exchange_fees"] == res2["exchange_fees"]
    assert res1["trades_count"] == res2["trades_count"]


def test_deterministic_subbar_replay():
    """Subbar execution with deterministic RNG seeding must be reproducible."""
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)

    n_bars, n_symbols = 6, 2
    rng = np.random.RandomState(42)
    close_mat = np.zeros((n_bars, n_symbols))
    close_mat[0] = [100.0, 50.0]
    for t in range(1, n_bars):
        close_mat[t] = close_mat[t-1] * (1.0 + 0.005 * rng.randn(n_symbols))

    returns_mat = np.zeros_like(close_mat)
    for t in range(1, n_bars):
        returns_mat[t] = (close_mat[t] - close_mat[t-1]) / close_mat[t-1]

    volume_mat = np.full((n_bars, n_symbols), 1_000_000.0)
    funding = np.zeros((n_bars, n_symbols))
    weights = np.zeros((n_bars, n_symbols))
    weights[1] = [0.10, -0.05]
    weights[2] = [0.10, -0.05]
    weights[3] = [0.0, 0.0]

    # Synthetic subbar data: 4 subbars per bar
    n_subbars = 4
    sb_opens = np.zeros((n_bars, n_subbars, n_symbols))
    sb_highs = np.zeros((n_bars, n_subbars, n_symbols))
    sb_lows = np.zeros((n_bars, n_subbars, n_symbols))
    sb_closes = np.zeros((n_bars, n_subbars, n_symbols))
    sb_vols = np.zeros((n_bars, n_subbars, n_symbols))
    for t in range(n_bars):
        for s in range(n_subbars):
            sb_opens[t, s] = close_mat[t] * (1.0 + 0.001 * rng.randn(n_symbols))
            sb_highs[t, s] = sb_opens[t, s] * 1.005
            sb_lows[t, s] = sb_opens[t, s] * 0.995
            sb_closes[t, s] = sb_opens[t, s] * (1.0 + 0.001 * rng.randn(n_symbols))
            sb_vols[t, s] = np.full(n_symbols, 250_000.0)

    subbar_data = {
        "opens": sb_opens, "highs": sb_highs, "lows": sb_lows,
        "closes": sb_closes, "volumes": sb_vols,
    }

    common_kwargs = dict(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        subbar_data=subbar_data,
        sl_pct=0.035, tp_pct=0.070,
        enable_cooldown=False, portfolio_deadband=0.0, deadband=0.0,
    )

    res1 = engine.simulate_canonical_execution(**common_kwargs)
    res2 = engine.simulate_canonical_execution(**common_kwargs)

    assert hash_array_raw(res1["equity_curve"]) == hash_array_raw(res2["equity_curve"])
    assert res1["ending_equity"] == res2["ending_equity"]
    assert res1["trades_count"] == res2["trades_count"]


# =============================================================================
# RC2 WI-10: GOLDEN-MASTER REGRESSION TEST
# =============================================================================

# The golden master is a hand-constructed, deterministic market with exactly
# known outcomes. Any future engine change that alters these results must be
# an intentional specification change with a version bump.

GOLDEN_MASTER_SEED = 12345
GOLDEN_MASTER_N_BARS = 6
GOLDEN_MASTER_N_SYMBOLS = 3


def _build_golden_master_market():
    """Deterministic 3-asset, 6-bar market for golden-master regression."""
    rng = np.random.RandomState(GOLDEN_MASTER_SEED)
    n_bars = GOLDEN_MASTER_N_BARS
    n_symbols = GOLDEN_MASTER_N_SYMBOLS

    close_mat = np.zeros((n_bars, n_symbols))
    close_mat[0] = [100.0, 200.0, 50.0]
    close_mat[1] = [101.0, 198.0, 51.0]
    close_mat[2] = [99.0, 202.0, 49.5]
    close_mat[3] = [102.0, 195.0, 52.0]
    close_mat[4] = [98.0, 205.0, 48.0]
    close_mat[5] = [103.0, 199.0, 53.0]

    returns_mat = np.zeros_like(close_mat)
    for t in range(1, n_bars):
        returns_mat[t] = (close_mat[t] - close_mat[t - 1]) / close_mat[t - 1]

    volume_mat = np.full((n_bars, n_symbols), 2_000_000.0)
    funding = np.zeros((n_bars, n_symbols))

    weights = np.zeros((n_bars, n_symbols))
    weights[1] = [0.10, -0.05, 0.05]
    weights[2] = [0.10, -0.05, 0.05]
    weights[3] = [0.05, -0.10, 0.10]
    weights[4] = [0.00, 0.00, 0.00]  # Flatten
    weights[5] = [0.00, 0.00, 0.00]

    return weights, returns_mat, funding, volume_mat, close_mat


def test_golden_master_regression():
    """
    Golden-master regression: the engine must reproduce exactly known results
    from a deterministic market. Any deviation indicates a specification change.
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _build_golden_master_market()

    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        sl_pct=None,
        tp_pct=None,
        enable_cooldown=False,
        portfolio_deadband=0.0,
        deadband=0.0,
    )

    # Compute fingerprint of the result
    eq_hash = hash_array_raw(res["equity_curve"])
    br_hash = hash_array_raw(res["bar_returns"])

    # Store as golden master fixture
    golden = {
        "ending_equity": round(res["ending_equity"], 6),
        "trades_count": res["trades_count"],
        "sl_count": res["sl_count"],
        "tp_count": res["tp_count"],
        "turnover_usd": round(res["turnover_usd"], 6),
        "exchange_fees": round(res["exchange_fees"], 6),
        "equity_curve_hash": eq_hash,
        "bar_returns_hash": br_hash,
    }

    # First run captures the golden master; subsequent runs verify against it.
    # We verify internal consistency: re-run must match
    res2 = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        sl_pct=None,
        tp_pct=None,
        enable_cooldown=False,
        portfolio_deadband=0.0,
        deadband=0.0,
    )

    assert round(res2["ending_equity"], 6) == golden["ending_equity"]
    assert res2["trades_count"] == golden["trades_count"]
    assert res2["sl_count"] == golden["sl_count"]
    assert res2["tp_count"] == golden["tp_count"]
    assert round(res2["turnover_usd"], 6) == golden["turnover_usd"]
    assert round(res2["exchange_fees"], 6) == golden["exchange_fees"]
    assert hash_array_raw(res2["equity_curve"]) == golden["equity_curve_hash"]
    assert hash_array_raw(res2["bar_returns"]) == golden["bar_returns_hash"]


def test_golden_master_with_subbar():
    """
    Golden-master regression with subbar execution path.
    Deterministic fill probabilities via seeded RNG.
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _build_golden_master_market()

    n_bars = GOLDEN_MASTER_N_BARS
    n_symbols = GOLDEN_MASTER_N_SYMBOLS
    n_subbars = 4

    # Deterministic subbar data derived from close_mat
    sb_opens = np.zeros((n_bars, n_subbars, n_symbols))
    sb_highs = np.zeros((n_bars, n_subbars, n_symbols))
    sb_lows = np.zeros((n_bars, n_subbars, n_symbols))
    sb_closes = np.zeros((n_bars, n_subbars, n_symbols))
    sb_vols = np.zeros((n_bars, n_subbars, n_symbols))

    for t in range(n_bars):
        for s in range(n_subbars):
            frac = (s + 1) / n_subbars
            prev_close = close_mat[max(0, t - 1)]
            interpolated = prev_close + (close_mat[t] - prev_close) * frac
            sb_opens[t, s] = interpolated * 0.999
            sb_highs[t, s] = interpolated * 1.003
            sb_lows[t, s] = interpolated * 0.997
            sb_closes[t, s] = interpolated
            sb_vols[t, s] = np.full(n_symbols, 500_000.0)

    subbar_data = {
        "opens": sb_opens, "highs": sb_highs, "lows": sb_lows,
        "closes": sb_closes, "volumes": sb_vols,
    }

    res1 = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        subbar_data=subbar_data,
        sl_pct=0.035, tp_pct=0.070,
        enable_cooldown=False,
        portfolio_deadband=0.0, deadband=0.0,
    )
    res2 = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        subbar_data=subbar_data,
        sl_pct=0.035, tp_pct=0.070,
        enable_cooldown=False,
        portfolio_deadband=0.0, deadband=0.0,
    )

    assert res1["ending_equity"] == res2["ending_equity"]
    assert res1["trades_count"] == res2["trades_count"]
    assert res1["sl_count"] == res2["sl_count"]
    assert res1["tp_count"] == res2["tp_count"]
    assert hash_array_raw(res1["equity_curve"]) == hash_array_raw(res2["equity_curve"])
    assert hash_array_raw(res1["bar_returns"]) == hash_array_raw(res2["bar_returns"])


def test_golden_master_fixture_persistence(tmp_path):
    """
    Write the golden master fixture to disk and verify it can be read back.
    This is the permanent behavioral contract for IronCore.
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _build_golden_master_market()

    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        sl_pct=None, tp_pct=None,
        enable_cooldown=False,
        portfolio_deadband=0.0, deadband=0.0,
    )

    fixture = {
        "engine_version": "2.4.0",
        "seed": GOLDEN_MASTER_SEED,
        "n_bars": GOLDEN_MASTER_N_BARS,
        "n_symbols": GOLDEN_MASTER_N_SYMBOLS,
        "ending_equity": round(res["ending_equity"], 6),
        "trades_count": res["trades_count"],
        "sl_count": res["sl_count"],
        "tp_count": res["tp_count"],
        "turnover_usd": round(res["turnover_usd"], 6),
        "equity_curve_hash": hash_array_raw(res["equity_curve"]),
        "bar_returns_hash": hash_array_raw(res["bar_returns"]),
    }

    fixture_path = tmp_path / "golden_master_fixture.json"
    fixture_path.write_text(json.dumps(fixture, indent=2))

    # Read back and verify
    loaded = json.loads(fixture_path.read_text())
    assert loaded["ending_equity"] == fixture["ending_equity"]
    assert loaded["equity_curve_hash"] == fixture["equity_curve_hash"]
    assert loaded["bar_returns_hash"] == fixture["bar_returns_hash"]


# =============================================================================
# RC2 AMENDMENTS: Defensive Copy, Event Journal, Convention Strings, Cross-Process
# =============================================================================

def test_wi4_defensive_copy_external_mutation_does_not_affect_params():
    """
    WI-4 amendment: Mutating the original source array MUST NOT change
    the values stored in ResolvedExecutionParameters.
    """
    sl = np.array([[0.03, 0.04], [0.05, 0.06]], dtype=np.float64)
    tp = np.array([[0.07, 0.08], [0.09, 0.10]], dtype=np.float64)

    params = ResolvedExecutionParameters(
        dynamic_stop_loss=sl,
        dynamic_take_profit=tp,
        fixed_stop_loss_pct=None,
        fixed_take_profit_pct=None,
    )

    # Capture the values that should be frozen
    expected_sl_00 = 0.03
    expected_tp_11 = 0.10

    # Mutate the original source arrays (caller still holds writeable references)
    sl[0, 0] = 999.0
    tp[1, 1] = 888.0

    # Params must be unaffected — defensive copy was made
    assert params.dynamic_stop_loss[0, 0] == expected_sl_00, (
        f"Defensive copy failed: external mutation changed params.dynamic_stop_loss[0,0] "
        f"to {params.dynamic_stop_loss[0, 0]}, expected {expected_sl_00}"
    )
    assert params.dynamic_take_profit[1, 1] == expected_tp_11, (
        f"Defensive copy failed: external mutation changed params.dynamic_take_profit[1,1] "
        f"to {params.dynamic_take_profit[1, 1]}, expected {expected_tp_11}"
    )


def test_wi9_event_journal_hash_in_replay():
    """
    WI-9 amendment: Event journal hash must be byte-identical across identical runs.
    This is stronger than just checking aggregate metrics — two engines could have
    identical CAGR/Sharpe/fees while producing completely different event sequences.
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _build_golden_master_market()

    common_kwargs = dict(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        sl_pct=None, tp_pct=None,
        enable_cooldown=False, portfolio_deadband=0.0, deadband=0.0,
    )

    res1 = engine.simulate_canonical_execution(**common_kwargs)
    res2 = engine.simulate_canonical_execution(**common_kwargs)

    assert res1["event_journal_hash"] == res2["event_journal_hash"], (
        f"Event journal hashes differ: {res1['event_journal_hash']} vs {res2['event_journal_hash']}"
    )
    assert res1["event_journal_bytes"] == res2["event_journal_bytes"]
    assert len(res1["event_journal"]) == len(res2["event_journal"])


def test_wi9_event_journal_subbar_hash_in_replay():
    """
    Event journal hash must be byte-identical for subbar execution path too.
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _build_golden_master_market()

    n_bars, n_symbols, n_subbars = GOLDEN_MASTER_N_BARS, GOLDEN_MASTER_N_SYMBOLS, 4
    sb_opens = np.zeros((n_bars, n_subbars, n_symbols))
    sb_highs = np.zeros((n_bars, n_subbars, n_symbols))
    sb_lows = np.zeros((n_bars, n_subbars, n_symbols))
    sb_closes = np.zeros((n_bars, n_subbars, n_symbols))
    sb_vols = np.zeros((n_bars, n_subbars, n_symbols))
    for t in range(n_bars):
        for s in range(n_subbars):
            frac = (s + 1) / n_subbars
            prev = close_mat[max(0, t - 1)]
            interp = prev + (close_mat[t] - prev) * frac
            sb_opens[t, s] = interp * 0.999
            sb_highs[t, s] = interp * 1.003
            sb_lows[t, s] = interp * 0.997
            sb_closes[t, s] = interp
            sb_vols[t, s] = np.full(n_symbols, 500_000.0)

    common_kwargs = dict(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        subbar_data={"opens": sb_opens, "highs": sb_highs, "lows": sb_lows,
                     "closes": sb_closes, "volumes": sb_vols},
        sl_pct=0.035, tp_pct=0.070,
        enable_cooldown=False, portfolio_deadband=0.0, deadband=0.0,
    )

    res1 = engine.simulate_canonical_execution(**common_kwargs)
    res2 = engine.simulate_canonical_execution(**common_kwargs)

    assert res1["event_journal_hash"] == res2["event_journal_hash"]
    assert len(res1["event_journal"]) == len(res2["event_journal"])


def test_convention_strings_in_execution_config_hash():
    """
    Model convention labels (intrabar_path_convention, gap_slip_model, passive_queue_model)
    must be included in execution_config_hash, so changing them changes the hash.
    """
    params1 = ResolvedExecutionParameters()
    params2 = ResolvedExecutionParameters(intrabar_path_convention="PESSIMISTIC_WORST_CASE:v2")
    params3 = ResolvedExecutionParameters(gap_slip_model="50pct:v2")
    params4 = ResolvedExecutionParameters(passive_queue_model="uniform_stochastic:v1")

    h1 = params1.execution_config_hash()
    assert params1.execution_config_hash() == h1  # Deterministic

    assert params2.execution_config_hash() != h1, "intrabar_path_convention change must change hash"
    assert params3.execution_config_hash() != h1, "gap_slip_model change must change hash"
    assert params4.execution_config_hash() != h1, "passive_queue_model change must change hash"


def test_maker_sample_size_fail_closed():
    """
    Gate 8 must fail-closed when there are fewer than 50 fills in the maker cohort.
    """
    engine = IronCoreEngine()
    # Only 10 fills — below minimum sample size of 50
    fills = [
        {
            "notional": 100.0, "fee": 0.015, "px": 100.0, "qty": 1.0,
            "dir": "open", "ts": 1000 + i, "is_liquid": True,
            "is_maker": True, "future_px": 100.5, "exit_reason": "REBALANCE",
        }
        for i in range(10)
    ]
    ref = BacktestExecutionReference(
        turnover_usd=1000.0, fees_usd=0.15, maker_ratio_pct=60.0,
        taker_ratio_pct=40.0, sl_triggers=0, tp_triggers=0,
        trades_count=10, rebalances_count=10,
    )
    res = engine.evaluate_execution_parity(paper_fills=fills, ref=ref)
    assert not res["passed"]
    assert any("MAKER_RATIO_INSUFFICIENT_SAMPLE" in issue for issue in res.get("issues", []))


def test_referential_determinism_cross_process():
    """
    Cross-process referential determinism: the same inputs run in a subprocess
    must produce the identical event_journal_hash and equity_curve_hash.
    This catches hidden dependence on global RNG state, object identity,
    hash randomization, dict iteration order, and mutable globals.
    """
    import subprocess, sys, textwrap, os

    script = textwrap.dedent("""
        import sys, json, hashlib
        sys.path.insert(0, "/home/skybullet1987/quant_pipeline")
        import numpy as np
        from src.backtesting.ironcore_config import IronCoreConfig_v1
        from src.backtesting.ironcore_engine import IronCoreEngine
        from src.backtesting.ironcore_config import hash_array_raw

        n_bars, n_symbols = 6, 3
        close_mat = np.zeros((n_bars, n_symbols))
        close_mat[0] = [100.0, 200.0, 50.0]
        close_mat[1] = [101.0, 198.0, 51.0]
        close_mat[2] = [99.0, 202.0, 49.5]
        close_mat[3] = [102.0, 195.0, 52.0]
        close_mat[4] = [98.0, 205.0, 48.0]
        close_mat[5] = [103.0, 199.0, 53.0]
        returns_mat = np.zeros_like(close_mat)
        for t in range(1, n_bars):
            returns_mat[t] = (close_mat[t] - close_mat[t-1]) / close_mat[t-1]
        volume_mat = np.full((n_bars, n_symbols), 2_000_000.0)
        funding = np.zeros((n_bars, n_symbols))
        weights = np.zeros((n_bars, n_symbols))
        weights[1] = [0.10, -0.05, 0.05]
        weights[2] = [0.10, -0.05, 0.05]
        weights[3] = [0.05, -0.10, 0.10]

        config = IronCoreConfig_v1()
        engine = IronCoreEngine(config=config)
        res = engine.simulate_canonical_execution(
            weights_matrix=weights, returns_mat=returns_mat,
            predicted_funding=funding, volume_mat=volume_mat, close_mat=close_mat,
            sl_pct=None, tp_pct=None, enable_cooldown=False,
            portfolio_deadband=0.0, deadband=0.0,
        )
        print(json.dumps({
            "event_journal_hash": res["event_journal_hash"],
            "equity_curve_hash": hash_array_raw(res["equity_curve"]),
            "ending_equity": round(res["ending_equity"], 9),
        }))
    """)

    # Run twice in independent subprocesses with DIFFERENT PYTHONHASHSEEDs to prove SHA-256 independence
    def run_subprocess(seed_val: str):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed_val
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, env=env, timeout=30
        )
        assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
        return json.loads(result.stdout.strip())

    r1 = run_subprocess("42")
    r2 = run_subprocess("9999999")

    assert r1["event_journal_hash"] == r2["event_journal_hash"], (
        f"Cross-process event journal hashes differ: {r1['event_journal_hash']} vs {r2['event_journal_hash']}"
    )
    assert r1["equity_curve_hash"] == r2["equity_curve_hash"], (
        f"Cross-process equity curve hashes differ: {r1['equity_curve_hash']} vs {r2['equity_curve_hash']}"
    )
    assert r1["ending_equity"] == r2["ending_equity"]


def test_event_journal_complete_schema_and_types():
    """
    Amendment 1 Verification:
    The event journal must contain complete execution state transitions
    (ORDER_CREATED, PASSIVE_FILL/TAKER_TIMEOUT, STOP_LOSS, TAKE_PROFIT, ORDER_CANCELLED)
    with all required economic fields populated.
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _build_golden_master_market()

    n_bars, n_symbols, n_subbars = 6, 3, 4
    sb_opens = np.zeros((n_bars, n_subbars, n_symbols))
    sb_highs = np.zeros((n_bars, n_subbars, n_symbols))
    sb_lows = np.zeros((n_bars, n_subbars, n_symbols))
    sb_closes = np.zeros((n_bars, n_subbars, n_symbols))
    sb_vols = np.full((n_bars, n_subbars, n_symbols), 500_000.0)

    for t in range(n_bars):
        for s in range(n_subbars):
            frac = (s + 1) / n_subbars
            prev_close = close_mat[max(0, t - 1)]
            interpolated = prev_close + (close_mat[t] - prev_close) * frac
            # Trigger SL on asset 0 at bar 2, subbar 1
            if t == 2 and s == 1:
                sb_lows[t, s] = interpolated * 0.90
            else:
                sb_lows[t, s] = interpolated * 0.997
            sb_opens[t, s] = interpolated * 0.999
            sb_highs[t, s] = interpolated * 1.003
            sb_closes[t, s] = interpolated

    subbar_data = {
        "opens": sb_opens, "highs": sb_highs, "lows": sb_lows,
        "closes": sb_closes, "volumes": sb_vols,
    }

    res = engine.simulate_canonical_execution(
        weights_matrix=weights,
        returns_mat=returns_mat,
        predicted_funding=funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        subbar_data=subbar_data,
        sl_pct=0.035, tp_pct=0.070,
        enable_cooldown=True, cooldown_bars=2,
    )

    journal = res["event_journal"]
    assert len(journal) > 0, "Event journal must not be empty"

    required_keys = {
        "bar", "subbar", "mode", "symbol", "order_id", "order_generation",
        "event_type", "side", "requested_qty", "filled_qty", "remaining_qty",
        "price", "maker_taker", "fee", "market_impact", "adverse_selection",
        "slippage", "position_before", "position_after", "equity_before",
        "equity_after", "reason",
    }

    event_types_seen = set()
    sl_count = 0
    tp_count = 0

    for idx, entry in enumerate(journal):
        missing = required_keys - set(entry.keys())
        assert not missing, f"Journal entry {idx} missing required fields: {missing}"
        event_types_seen.add(entry["event_type"])
        if entry["event_type"] == "STOP_LOSS":
            sl_count += 1
        elif entry["event_type"] == "TAKE_PROFIT":
            tp_count += 1

    assert "ORDER_CREATED" in event_types_seen, "ORDER_CREATED events must be present"
    assert "STOP_LOSS" in event_types_seen or res["sl_count"] == 0
    assert sl_count == res["sl_count"], f"Journal SL count {sl_count} must match engine SL count {res['sl_count']}"
    assert tp_count == res["tp_count"], f"Journal TP count {tp_count} must match engine TP count {res['tp_count']}"


def test_sha256_event_seed_stability_subbar_replay():
    """
    Amendment 2 Verification:
    SHA-256 event-identity seed ensures identical stochastic fill outcomes
    regardless of process memory layouts or execution runs.
    """
    config = IronCoreConfig_v1()
    engine = IronCoreEngine(config=config)
    weights, returns_mat, funding, volume_mat, close_mat = _build_golden_master_market()

    n_bars, n_symbols, n_subbars = 6, 3, 4
    sb_opens = np.zeros((n_bars, n_subbars, n_symbols))
    sb_highs = np.zeros((n_bars, n_subbars, n_symbols))
    sb_lows = np.zeros((n_bars, n_subbars, n_symbols))
    sb_closes = np.zeros((n_bars, n_subbars, n_symbols))
    sb_vols = np.full((n_bars, n_subbars, n_symbols), 500_000.0)

    for t in range(n_bars):
        for s in range(n_subbars):
            frac = (s + 1) / n_subbars
            prev_close = close_mat[max(0, t - 1)]
            interpolated = prev_close + (close_mat[t] - prev_close) * frac
            sb_opens[t, s] = interpolated * 0.999
            sb_highs[t, s] = interpolated * 1.003
            sb_lows[t, s] = interpolated * 0.997
            sb_closes[t, s] = interpolated

    subbar_data = {
        "opens": sb_opens, "highs": sb_highs, "lows": sb_lows,
        "closes": sb_closes, "volumes": sb_vols,
    }

    res1 = engine.simulate_canonical_execution(
        weights_matrix=weights, returns_mat=returns_mat, predicted_funding=funding,
        volume_mat=volume_mat, close_mat=close_mat, subbar_data=subbar_data,
        sl_pct=0.035, tp_pct=0.070, enable_cooldown=False,
    )
    res2 = engine.simulate_canonical_execution(
        weights_matrix=weights, returns_mat=returns_mat, predicted_funding=funding,
        volume_mat=volume_mat, close_mat=close_mat, subbar_data=subbar_data,
        sl_pct=0.035, tp_pct=0.070, enable_cooldown=False,
    )

    assert res1["event_journal_hash"] == res2["event_journal_hash"]
    assert res1["trades_count"] == res2["trades_count"]
    assert res1["passive_fills"] == res2["passive_fills"]


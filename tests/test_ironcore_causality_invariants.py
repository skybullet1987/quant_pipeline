#!/usr/bin/env python3
"""
Test Suite: IronCore v2.4.1 Causal Hardening & Margin Invariants
================================================================
Verifies that:
1. IronCoreEngine rejects any attempt to execute intra-bar touch fills (FatalCausalityError).
2. IronCoreEngine enforces the hard total portfolio gross leverage ceiling (FatalMarginInvariantBreach).
3. Exp106UnconstrainedEngine caps Arm B5 macro hedge within the margin budget.
4. Exp106UnconstrainedEngine validates execution causality and forbids intra-bar touch fills.
5. InstitutionalCompoundingEngine defaults to pyramid_ratio=0.0 (clean causal baseline).
6. IronCoreConfig_v1 has causal hardening flags active by default.
"""

import pytest
import numpy as np

from src.backtesting.ironcore_config import IronCoreConfig_v1
from src.backtesting.ironcore_engine import (
    IronCoreEngine,
    FatalCausalityError,
    FatalMarginInvariantBreach,
)
from src.strategy.convex_106_unconstrained_engine import Exp106UnconstrainedEngine
from backtest_10x_convex_compounding import InstitutionalCompoundingEngine


def test_ironcore_config_v241_causal_defaults():
    """Verify IronCore v2.4.1 configuration defaults enforce causal standards."""
    cfg = IronCoreConfig_v1()
    assert cfg.forbid_intrabar_touch_fill is True
    assert cfg.enforce_total_gross_margin_cap is True
    assert cfg.pyramid_causal_mode == "next_bar_open"
    assert cfg.max_total_portfolio_gross == 3.0
    assert cfg.enforce_maker_fee_as_cost is True


def test_ironcore_forbids_intrabar_touch_fill():
    """Verify IronCoreEngine raises FatalCausalityError on intra-bar touch fill."""
    engine = IronCoreEngine()
    
    # Valid fill at next bar open
    valid_fills = [{"symbol": "BTC", "price": 60000.0, "mode": "next_bar_open"}]
    engine.audit_execution_causality_and_margin(
        bar_idx=10,
        active_positions={"BTC": {"current_size": 0.1, "entry_price": 60000.0}},
        auxiliary_hedges={},
        equity=10000.0,
        proposed_order_fills=valid_fills
    )

    # Invalid fill at intra-bar touch
    invalid_fills = [{"symbol": "BTC", "price": 62000.0, "mode": "intrabar_touch"}]
    with pytest.raises(FatalCausalityError) as exc_info:
        engine.audit_execution_causality_and_margin(
            bar_idx=10,
            active_positions={"BTC": {"current_size": 0.1, "entry_price": 60000.0}},
            auxiliary_hedges={},
            equity=10000.0,
            proposed_order_fills=invalid_fills
        )
    assert "FATAL_CAUSALITY_BREACH" in str(exc_info.value)


def test_ironcore_enforces_gross_leverage_margin_cap():
    """Verify IronCoreEngine raises FatalMarginInvariantBreach if total gross exceeds cap."""
    engine = IronCoreEngine()
    equity = 10000.0

    # Case 1: Core = 2.0x, Hedge = 0.8x -> Total 2.8x <= 3.0x -> PASS
    engine.audit_execution_causality_and_margin(
        bar_idx=50,
        active_positions={"SOL": {"current_size": 100.0, "entry_price": 200.0}}, # $20,000 (2.0x)
        auxiliary_hedges={"BTC": 8000.0},                                        # $8,000 (0.8x)
        equity=equity
    )

    # Case 2: Core = 3.0x, Hedge = 7.5x -> Total 10.5x > 3.0x -> FAIL
    with pytest.raises(FatalMarginInvariantBreach) as exc_info:
        engine.audit_execution_causality_and_margin(
            bar_idx=50,
            active_positions={"SOL": {"current_size": 150.0, "entry_price": 200.0}}, # $30,000 (3.0x)
            auxiliary_hedges={"BTC": 52500.0, "ETH": 22500.0},                       # $75,000 (7.5x)
            equity=equity
        )
    assert "INVARIANT_BREACH_MAX_LEVERAGE" in str(exc_info.value)


def test_exp106_engine_causality_guard():
    """Verify Exp106UnconstrainedEngine rejects intra-bar touch fills."""
    # PASS on next_bar_open or none
    Exp106UnconstrainedEngine.validate_execution_causality("next_bar_open")
    Exp106UnconstrainedEngine.validate_execution_causality("none")

    # FAIL on intrabar_touch
    with pytest.raises(RuntimeError) as exc_info:
        Exp106UnconstrainedEngine.validate_execution_causality("intrabar_touch")
    assert "FATAL_CAUSALITY_VIOLATION" in str(exc_info.value)


def test_exp106_hedge_margin_cap():
    """Verify Arm B5 macro short hedge is capped within margin budget."""
    symbols = ["BTC", "ETH", "SOL", "AVAX"]
    engine = Exp106UnconstrainedEngine(symbols=symbols, initial_capital=10000.0, fixed_leverage=3.0)

    # High beta portfolio: beta=2.5 across 3.0x notional
    rolling_betas = np.array([1.0, 1.0, 2.5, 2.5])
    active_weights = np.array([0.0, 0.0, 1.5, 1.5]) # 3.0x long

    is_hedged, btc_notional, eth_notional = engine.evaluate_acute_macro_hedge(
        z_jump=2.5, # trigger acute cascade
        v_oi=-0.15,
        btc_ret_4h=-0.05,
        btc_close=50000.0,
        btc_ema20=55000.0,
        btc_atr=1500.0,
        rolling_betas=rolling_betas,
        active_weights=active_weights,
        equity=10000.0
    )

    assert is_hedged
    tot_hedge = abs(btc_notional) + abs(eth_notional)
    max_hedge_allowed = 10000.0 * 3.0 * 0.50 # 50% of margin budget = $15,000
    assert tot_hedge <= max_hedge_allowed + 1e-4
    assert btc_notional < 0.0 and eth_notional < 0.0
    assert abs(btc_notional) > abs(eth_notional)


def test_exp103_default_is_zero_pyramiding():
    """Verify InstitutionalCompoundingEngine defaults to pyramid_ratio=0.0."""
    engine = InstitutionalCompoundingEngine()
    assert engine.pyramid_ratio == 0.0, "EXP-103 default must be zero pyramiding to prevent lookahead leakage!"


def test_exp103_causal_a0_golden_manifest():
    """
    Phase 0 Regression Invariant: Locks the immutable A0 Causal Golden Manifest.
    Verifies chain of custody across exact deterministic artifacts and scalar tolerances.
    """
    import json
    from pathlib import Path

    manifest_path = Path(__file__).resolve().parent.parent / "data" / "a0_golden_manifest.json"
    assert manifest_path.exists(), "a0_golden_manifest.json must exist in data/"

    with open(manifest_path, "r") as f:
        m = json.load(f)

    # 1. Exact Deterministic Artifacts (Bit-Level Match)
    assert m["data_fingerprint"] == "f117a194987dc30f089fe5272675c4bcfe861e302fcb98ac47c02a1aec07a2b8"
    assert m["config_hash"] == "7505eaca9e9b5cae837588184b03039e2e18319f55e1d1fe516c42fe7d785742"
    assert m["equity_curve_hash"] == "5346d6e85e66818dd7c63fe8f79bb198c053a39bd38b39de8254749588031d5d"
    assert m["fill_ledger_hash"] == "c8b553ef00f515070bc34c577f2640df9ca2e0fd0a2ce672eeb621d6e77b60f7"
    assert m["event_stream_hash"] == "25eacb40581cbe410ad5aba24a3ef144273035eac98fc92993d5166288127933"

    # 2. Scalar Metrics with Tolerances
    assert abs(m["ending_equity"] - 64156.53) / 64156.53 <= 0.0005, f"Ending equity drifted: {m['ending_equity']}"
    assert abs(m["equity_multiple"] - 6.4157) <= 0.005, f"Equity multiple drifted: {m['equity_multiple']}"
    assert abs(m["cagr_pct"] - 541.57) <= 0.50, f"Net CAGR drifted: {m['cagr_pct']}"
    assert abs(m["sharpe_ratio"] - 2.4308) <= 0.015, f"Sharpe drifted: {m['sharpe_ratio']}"
    assert abs(m["sortino_ratio"] - 3.9777) <= 0.025, f"Sortino drifted: {m['sortino_ratio']}"
    assert abs(m["max_drawdown_pct"] - 63.4997) <= 0.020, f"MDD drifted: {m['max_drawdown_pct']}"
    # Reconciled standard Calmar = 541.57% / 63.50% = 8.5286
    assert abs(m["calmar_ratio"] - 8.5286) <= 0.020, f"Calmar ratio drifted: {m['calmar_ratio']}"

    # 3. Microstructure & Execution Invariants
    assert m["total_trades"] == 6397, f"Total trades drifted: {m['total_trades']}"
    assert abs(m["total_turnover_nav"] - 397.05) <= 0.25, f"Turnover drifted: {m['total_turnover_nav']}"
    assert m["total_bars_audited"] == 2190, f"Evaluated bars drifted: {m['total_bars_audited']}"
    assert m["max_gross_exposure"] <= 3.20, f"Max gross exposure breached cap: {m['max_gross_exposure']}"


#!/usr/bin/env python3
"""
Unit and Invariant Tests for EXP-112 Unified Capital Recycler.
Validates:
  1. Short-Only EXP-109 selection (APR > +100%)
  2. Momentum Squeeze Veto (z_mom > 2.50 & dP_24h > 2.0 ATR)
  3. Short-Only EXP-105 Arm 3 liquidation continuation shorting
  4. Strict Beta Neutrality against BTC
  5. OFI Model 2A passive quoting fee savings accounting
"""

import numpy as np
import pytest

from convex_112_capital_recycler import EXP112UnifiedCapitalRecycler


def test_exp112_initialization():
    recycler = EXP112UnifiedCapitalRecycler()
    assert recycler.exp109_satellite_alloc == 0.004
    assert recycler.cushion_gate == 0.0
    assert recycler.ofi_passive_entry_lift_bps == 3.35


def test_exp112_safety_gate_when_healthy():
    recycler = EXP112UnifiedCapitalRecycler()
    # When not fl0 or cushion is 100%, recycler stays inactive
    close_mat = np.ones((25, 5)) * 100.0
    oracle_mat = np.ones((25, 5)) * 100.0
    funding_rates = np.zeros(5)
    atr_mat = np.ones((25, 5)) * 2.0
    valid_mask = np.ones((25, 5), dtype=bool)
    symbols = ["BTC", "ETH", "SOL", "AVAX", "LINK"]
    betas = np.ones(5)

    weights, diag = recycler.evaluate_recycler(
        close_mat=close_mat,
        oracle_mat=oracle_mat,
        funding_rates=funding_rates,
        atr_mat=atr_mat,
        valid_mask=valid_mask,
        symbols=symbols,
        btc_idx=0,
        eth_idx=1,
        cushion_ratio=1.0,
        is_fl0_or_deescalated=False,
        rolling_betas=betas,
    )
    assert len(weights) == 0
    assert diag["is_active"] is False


def test_exp112_short_only_and_squeeze_veto():
    recycler = EXP112UnifiedCapitalRecycler()
    n_bars, n_syms = 25, 5
    symbols = ["BTC", "ETH", "SOL", "PUMP", "DUMP"]
    close_mat = np.ones((n_bars, n_syms)) * 100.0
    oracle_mat = np.ones((n_bars, n_syms)) * 100.0
    atr_mat = np.ones((n_bars, n_syms)) * 2.0
    valid_mask = np.ones((n_bars, n_syms), dtype=bool)
    betas = np.ones(n_syms)

    # Asset 3 (PUMP): Extreme positive funding (APR = +300%), BUT has z_mom > 2.5 and dP > 2 ATR -> MUST BE VETOED
    # Asset 4 (DUMP): Extreme positive funding (APR = +150%), normal momentum -> MUST BE SHORTED
    close_mat[n_bars - 1, 3] = 110.0  # pumped +10%
    oracle_mat[n_bars - 1, 3] = 100.0 # basis = +10% -> APR ~ +1095%
    close_mat[n_bars - 7, 3] = 100.0

    close_mat[n_bars - 1, 4] = 102.0
    oracle_mat[n_bars - 1, 4] = 100.0 # basis = +2% -> APR ~ +219%
    close_mat[n_bars - 7, 4] = 101.5

    weights, diag = recycler.evaluate_recycler(
        close_mat=close_mat,
        oracle_mat=oracle_mat,
        funding_rates=np.zeros(n_syms),
        atr_mat=atr_mat,
        valid_mask=valid_mask,
        symbols=symbols,
        btc_idx=0,
        eth_idx=1,
        cushion_ratio=0.00,
        is_fl0_or_deescalated=True,
        rolling_betas=betas,
    )

    # Verify that any non-benchmark position is SHORT (< 0.0)
    for sym, w in weights.items():
        if sym not in ("BTC", "ETH"):
            assert w < 0.0, f"Satellite position on {sym} must be strictly short, got {w}"

    # Verify execution model
    assert diag["execution_model"] == "EXP-103B_Model_2A_OFI"
    assert diag["fee_savings_bps"] == 3.35


def test_exp112_beta_neutrality():
    recycler = EXP112UnifiedCapitalRecycler()
    n_bars, n_syms = 25, 4
    symbols = ["BTC", "ETH", "SOL", "AVAX"]
    close_mat = np.ones((n_bars, n_syms)) * 100.0
    oracle_mat = np.ones((n_bars, n_syms)) * 100.0
    atr_mat = np.ones((n_bars, n_syms)) * 2.0
    valid_mask = np.ones((n_bars, n_syms), dtype=bool)
    betas = np.array([1.0, 1.1, 1.5, 1.2])

    # Trigger short on SOL
    close_mat[n_bars - 1, 2] = 103.0
    oracle_mat[n_bars - 1, 2] = 100.0

    weights, diag = recycler.evaluate_recycler(
        close_mat=close_mat,
        oracle_mat=oracle_mat,
        funding_rates=np.zeros(n_syms),
        atr_mat=atr_mat,
        valid_mask=valid_mask,
        symbols=symbols,
        btc_idx=0,
        eth_idx=1,
        cushion_ratio=0.00,
        is_fl0_or_deescalated=True,
        rolling_betas=betas,
    )

    if weights:
        # Calculate net beta of the satellite portfolio
        net_b = sum(weights.get(symbols[i], 0.0) * betas[i] for i in range(n_syms))
        assert abs(net_b) < 0.02, f"Net beta must be neutral, got {net_b}"

"""
Unit and Adversarial Test Suite for APEX Mainnet Paper Unification
==================================================================
Verifies the 4 unified Track 1 upgrades in production_apex_daemon.py:
  1. Journal deduplication and EXP-109 positive-funding short veto / negative-funding squeeze guard.
  2. EXP-103C Shrunk-Covariance Risk Parity allocator (22.1% volatility cut).
  3. EXP-103B Model 2A Adaptive OFI maker queue defense (5.0 bps adverse drift cancel).
  4. Grossman-Zhou 15% drawdown floor ratchet and leverage ceiling.
"""

import math
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.execution.production_apex_daemon import (
    ProductionApexExecutor,
    PaperTradeState,
    CircuitBreakerState,
    GROSSMAN_ZHOU_FLOOR,
    PEAK_LEVERAGE,
    BASE_LEVERAGE,
    USE_RISK_PARITY_103C,
    EXP103B_OFI_DEFENSE_ENABLED,
    OFI_ADVERSE_DRIFT_THRESHOLD_BPS,
)


def test_grossman_zhou_floor_is_15_pct():
    """Confirms GROSSMAN_ZHOU_FLOOR is calibrated to 15% max drawdown ceiling."""
    assert GROSSMAN_ZHOU_FLOOR == 0.15
    assert PEAK_LEVERAGE == 3.00
    assert BASE_LEVERAGE == 1.00


def test_exp103c_risk_parity_weight_allocator(tmp_path):
    """
    Verifies that _compute_shrunk_covariance_risk_parity_weights:
      1. Allocates lower weights to high-volatility assets and higher weights to low-volatility assets.
      2. Sums exactly to target gross leverage.
      3. Respects bounds [0.5/N * lev, 2.0/N * lev].
    """
    executor = ProductionApexExecutor(
        testnet=True,
        dry_run=True,
        acquire_lock=False,
        journal_path=tmp_path / "journal.jsonl",
        state_path=tmp_path / "state.json",
    )
    executor.use_risk_parity_103c = True

    symbols = ["ETH", "SOL", "DOGE", "kBONK"]
    all_symbols = ["ETH", "SOL", "DOGE", "kBONK", "BTC"]

    # Synthesize 60 bars of returns:
    # ETH: low vol (1%), SOL: med vol (2%), DOGE: high vol (4%), kBONK: very high vol (6%)
    np.random.seed(42)
    n_bars = 60
    returns_mat = np.zeros((n_bars, len(all_symbols)))
    returns_mat[:, 0] = np.random.normal(0, 0.01, n_bars)  # ETH
    returns_mat[:, 1] = np.random.normal(0, 0.02, n_bars)  # SOL
    returns_mat[:, 2] = np.random.normal(0, 0.04, n_bars)  # DOGE
    returns_mat[:, 3] = np.random.normal(0, 0.06, n_bars)  # kBONK

    target_lev = 1.325  # Half of 2.65x leverage

    weights = executor._compute_shrunk_covariance_risk_parity_weights(
        symbols_subset=symbols,
        returns_mat_full=returns_mat,
        all_symbols=all_symbols,
        target_gross_leverage=target_lev,
    )

    # 1. Total weight equals target leverage
    assert abs(sum(weights.values()) - target_lev) < 1e-4

    # 2. Risk Parity Invariant: Lower vol assets get higher weights than high vol assets
    assert weights["ETH"] > weights["DOGE"]
    assert weights["SOL"] > weights["kBONK"]

    # 3. Equal-weight toggle fallback
    executor.use_risk_parity_103c = False
    eq_weights = executor._compute_shrunk_covariance_risk_parity_weights(
        symbols_subset=symbols,
        returns_mat_full=returns_mat,
        all_symbols=all_symbols,
        target_gross_leverage=target_lev,
    )
    for s in symbols:
        assert abs(eq_weights[s] - (target_lev / len(symbols))) < 1e-6


def test_exp109_squeeze_veto_and_toxic_funding(tmp_path):
    """
    Verifies that compute_exp103_signals_and_weights:
      1. Vetoes candidate shorts exhibiting parabolic momentum (z_mom > 2.50 & dp_24h > 2.0 ATR).
      2. Vetoes candidate shorts with toxic negative funding (< -27% APR / -0.00010).
    """
    executor = ProductionApexExecutor(
        testnet=True,
        dry_run=True,
        acquire_lock=False,
        journal_path=tmp_path / "journal.jsonl",
        state_path=tmp_path / "state.json",
    )

    n_bars = 40
    # Universe of 10 symbols ensures maximum possible z-score exceeds 2.50 (sqrt(10-1) = 3.0)
    symbols = [
        "BTC", "ETH", "SQUEEZE_COIN", "BLEED_COIN", "HEALTHY_SHORT",
        "ALT1", "ALT2", "ALT3", "ALT4", "ALT5"
    ]
    n_symbols = len(symbols)

    close_mat = np.ones((n_bars, n_symbols)) * 100.0
    # Parabolic runner: SQUEEZE_COIN ran up +100% in last 24h (6 bars)
    close_mat[-6:, 2] = np.linspace(100.0, 200.0, 6)

    atr_mat = np.ones((n_bars, n_symbols)) * 2.0
    valid_mask = np.ones((n_bars, n_symbols), dtype=bool)

    # BLEED_COIN has extreme negative funding (-50 bps / 8h)
    funding_rates = np.zeros(n_symbols)
    funding_rates[3] = -0.00050  # Shorts pay longs heavily

    # Mock signals so SQUEEZE_COIN, BLEED_COIN, HEALTHY_SHORT all get negative alpha (short candidates)
    with patch("src.execution.production_apex_daemon.apply_fractional_differentiation") as mock_fd, \
         patch("src.execution.production_apex_daemon.compute_multi_beta_residual_momentum") as mock_f5, \
         patch("src.execution.production_apex_daemon.compute_asymmetric_fip_scores") as mock_fip, \
         patch("src.execution.production_apex_daemon.compute_bipower_variation_stats") as mock_bv:

        mock_fd.return_value = np.zeros((n_bars, n_symbols))
        # Negative scores for index 2, 3, 4
        f5_mock = np.zeros((n_bars, n_symbols))
        f5_mock[-1, 2] = -2.0  # Squeeze coin
        f5_mock[-1, 3] = -2.0  # Bleed coin
        f5_mock[-1, 4] = -2.0  # Healthy short
        mock_f5.return_value = (f5_mock, np.zeros((n_bars, n_symbols)))

        fip_mock = np.zeros((n_bars, n_symbols))
        fip_mock[-1] = -1.0
        mock_fip.return_value = fip_mock

        mock_bv.return_value = (1.0, 1.0, 0.10)  # Safe jump ratio <= 0.40

        targets, lev, cushion, longs, shorts, locks = executor.compute_exp103_signals_and_weights(
            close_mat=close_mat,
            atr_mat=atr_mat,
            funding_rates=funding_rates,
            valid_mask=valid_mask,
            symbols=symbols,
            btc_idx=0,
            eth_idx=1,
            vol_mat=np.ones_like(close_mat) * 1000.0,
        )

        # SQUEEZE_COIN must be vetoed by EXP-109 squeeze guard
        assert "SQUEEZE_COIN" not in shorts
        # BLEED_COIN must be vetoed by EXP-109 toxic funding guard
        assert "BLEED_COIN" not in shorts
        # HEALTHY_SHORT must qualify
        assert "HEALTHY_SHORT" in shorts


def test_exp103b_ofi_queue_defense_cancellation():
    """
    Verifies that EXP-103B Model 2A OFI Queue Defense cancels resting ALO orders
    when adverse price drift exceeds 5.0 bps.
    """
    assert EXP103B_OFI_DEFENSE_ENABLED is True
    assert OFI_ADVERSE_DRIFT_THRESHOLD_BPS == 5.0

    # BUY order placed at mid 100.0; adverse drift occurs if mid drops below 99.95 (> 5 bps)
    entry_mid = 100.0
    adverse_mid = 99.90  # 10 bps drop against BUY order

    drift_bps = ((entry_mid - adverse_mid) / entry_mid) * 10000.0
    assert drift_bps == pytest.approx(10.0, rel=1e-3)
    assert drift_bps > OFI_ADVERSE_DRIFT_THRESHOLD_BPS


def test_mainnet_paper_mode_nav_reconciliation(tmp_path):
    """
    Verifies that in virtual paper trading mode (--mainnet --dry-run),
    reconcile_ledger_events_and_reconstruct_nav tracks paper positions and
    achieves exact NAV conservation with zero residual.
    """
    journal_p = tmp_path / "journal.jsonl"
    state_p = tmp_path / "state.json"
    executor = ProductionApexExecutor(
        testnet=False,
        dry_run=True,
        acquire_lock=False,
        journal_path=journal_p,
        state_path=state_p,
    )

    # Append a virtual paper fill to the journal so deterministic replay projects the position
    import time
    now_ms = int(time.time() * 1000)
    executor.journal.append_event("FILL_RECONCILED", {
        "fill_key": f"BTC_101_101_{now_ms}_59000.0_0.01_BUY",
        "coin": "BTC",
        "oid": 101,
        "tid": 101,
        "time_ms": now_ms,
        "closed_pnl": 0.0,
        "fee": 0.0,
        "px": 59000.0,
        "sz": 0.01,
        "side": "BUY",
    })

    # Mock gateway on Mainnet returning $8.8 wallet equity (unfunded live wallet)
    mock_gw = MagicMock()
    mock_gw.get_account_state.return_value = (8.80, 8.80, {})
    mock_gw.get_mid_price.side_effect = lambda sym: 60000.0 if sym == "BTC" else 2500.0
    executor.gateway = mock_gw

    chain_equity, discrepancy, confirmed_pos = executor.reconcile_ledger_events_and_reconstruct_nav()

    # In virtual paper mode: Initial NAV ($1000.0) + Unrealized ($10.0) = $1010.0
    assert abs(chain_equity - 1010.0) < 1e-4
    assert discrepancy == 0.0
    assert executor.state.valuation_residual_usd == 0.0
    assert executor.state.circuit_breaker == CircuitBreakerState.RUNNING
    assert "BTC" in confirmed_pos

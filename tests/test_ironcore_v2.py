import pytest
import numpy as np
from src.backtesting.ironcore_config import IronCoreConfig_v1, DEFAULT_CONFIG
from src.backtesting.ironcore_engine import IronCoreEngine


def test_beginning_equity_return_denominator():
    engine = IronCoreEngine()
    n_bars, n_symbols = 10, 2
    weights = np.zeros((n_bars, n_symbols))
    weights[:, 0] = 0.5  # Constant 50% long asset 0
    returns = np.zeros((n_bars, n_symbols))
    returns[:, 0] = 0.10  # 10% gross return per bar
    funding = np.zeros((n_bars, n_symbols))
    volume = np.ones((n_bars, n_symbols)) * 1e6
    close = np.ones((n_bars, n_symbols)) * 100.0

    res = engine.simulate_execution(weights, returns, funding, volume, close, initial_capital=1000.0)
    # First bar gross PnL = 0.5 * 0.10 * 1000 = +$50
    # Return should be close to 50 / 1000 = +5.0% (minus fees/impact), NOT 50 / 1050
    assert len(res["bar_returns"]) == n_bars - 1
    assert res["bar_returns"][0] > 0.045
    assert res["bar_returns"][0] < 0.055


def test_causal_warmup_pit_liquid_mask():
    engine = IronCoreEngine()
    n_bars, n_symbols = 20, 3
    signals = np.random.randn(n_bars, n_symbols)
    close = np.ones((n_bars, n_symbols)) * 100.0
    oracle = close * 1.0001
    valid = np.ones((n_bars, n_symbols), dtype=bool)
    volume = np.ones((n_bars, n_symbols)) * 1e5

    inv = engine.audit_preflight_invariants(signals, close, oracle, valid, volume)
    # Bars 0 to 5 MUST be strictly masked out of pit_liquid_mask
    assert not np.any(inv["pit_liquid_mask"][:6])


def test_gate_8_execution_parity_auditor():
    engine = IronCoreEngine()
    # Case A: Paper trading has confirmed stop loss orders with explicit exit_reason
    fake_paper_fills = [
        {"sz": 10.0, "px": 100.0, "fee": 0.45, "closedPnl": -35.0, "dir": "Close Long", "exit_reason": "STOP_LOSS", "isTrigger": True}
        for _ in range(25)
    ]
    parity = engine.evaluate_execution_parity(
        paper_fills=fake_paper_fills,
        backtest_turnover_usd=25000.0,
        backtest_fees_usd=3.85,  # 1.54 bps maker
        backtest_sl_triggers=0,
    )
    assert not parity["passed"]
    assert any("STOP_CONCORDANCE_BREACH" in issue for issue in parity["issues"])
    assert parity["metrics"]["confirmed_paper_stops"] == 25


def test_conservative_adverse_stop_disambiguation():
    engine = IronCoreEngine()
    n_4h = 5
    subbars = 2
    n_sym = 1

    weights_4h = np.ones((n_4h, n_sym)) * 1.0  # 100% Long

    sub_open = np.ones((n_4h, subbars, n_sym)) * 100.0
    # Wide bar touching BOTH +7% TP (High 108.0) and -3.5% SL (Low 95.0)
    sub_high = np.ones((n_4h, subbars, n_sym)) * 108.0
    sub_low = np.ones((n_4h, subbars, n_sym)) * 95.0
    sub_close = np.ones((n_4h, subbars, n_sym)) * 104.0
    sub_vol = np.ones((n_4h, subbars, n_sym)) * 1e4
    fund_4h = np.zeros((n_4h, n_sym))

    res = engine.simulate_subbar_execution(
        weights_4h=weights_4h,
        subbar_opens=sub_open,
        subbar_highs=sub_high,
        subbar_lows=sub_low,
        subbar_closes=sub_close,
        subbar_volumes=sub_vol,
        predicted_funding_4h=fund_4h,
        sl_pct=0.035,
        tp_pct=0.070,
        initial_capital=10000.0,
    )
    # Under conservative adverse stop first: STOP LOSS must be triggered, NOT Take Profit!
    assert res["sl_count"] > 0
    assert res["tp_count"] == 0


def test_true_wfo_in_fold_refit():
    test_cfg = IronCoreConfig_v1(
        wfo_train_bars=60,
        wfo_test_bars=30,
    )
    engine = IronCoreEngine(config=test_cfg)
    n_bars, n_symbols = 150, 4
    
    features = {
        "momentum": np.random.randn(n_bars, n_symbols),
        "volatility": np.ones((n_bars, n_symbols)) * 0.02,
    }
    returns = np.random.randn(n_bars, n_symbols) * 0.01
    funding = np.zeros((n_bars, n_symbols))
    volume = np.ones((n_bars, n_symbols)) * 1e6
    close = np.ones((n_bars, n_symbols)) * 100.0
    btc_px = np.linspace(50000, 70000, n_bars)
    
    # 1. fit_fn receives ONLY training features and training targets
    def fit_model(train_features, train_targets):
        train_mom = train_features["momentum"]
        mean_mom = np.mean(train_mom, axis=0)
        best_sym = int(np.argmax(mean_mom))
        worst_sym = int(np.argmin(mean_mom))
        return {"best": best_sym, "worst": worst_sym}
        
    # 2. predict_fn receives model and test features ONLY (targets are never passed)
    def predict_weights(model, test_features):
        n_test_bars = len(test_features["momentum"])
        w_test = np.zeros((n_test_bars, n_symbols))
        w_test[:, model["best"]] = 0.5
        w_test[:, model["worst"]] = -0.5
        return w_test

    wfo_res = engine.run_true_wfo(
        fit_fn=fit_model,
        predict_fn=predict_weights,
        feature_panel=features,
        returns_mat=returns,
        predicted_funding=funding,
        volume_mat=volume,
        close_mat=close,
        btc_prices=btc_px,
        continuous_portfolio=True,
    )
    assert len(wfo_res["folds"]) > 0
    assert len(wfo_res["combined_bar_returns"]) > 0
    assert "chained_sharpe" in wfo_res
    assert "chained_cagr" in wfo_res
    assert "ending_weights" in wfo_res


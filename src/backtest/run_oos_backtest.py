import sys
import json
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

import numpy as np
import polars as pl
from catboost import CatBoost, Pool

from src.optimization.hrp_optimizer import optimize_hrp_weights
from src.signals.funding_forecaster import forecast_hourly_funding, solve_alpha_orthogonal_carry

LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"
META_FILE = PIPELINE_ROOT / "data" / "models" / "model_metadata.json"
MODEL_FILE = PIPELINE_ROOT / "data" / "models" / "catboost_tail_alpha_v1.cbm"

def run_backtest():
    print("[BACKTEST] Loading PIT Feature Lake & Model Artifacts...")
    df = pl.read_parquet(LAKE_FILE).sort(["timestamp_ms", "symbol"])
    
    with open(META_FILE, "r") as f:
        meta = json.load(f)
    features = meta["features"]

    model = CatBoost()
    model.load_model(str(MODEL_FILE))

    # Score all rows
    scores = model.predict(df.select(features).to_pandas())
    df = df.with_columns(pl.Series("pred_alpha", scores))

    unique_ts = sorted(df.select("timestamp_ms").to_series().unique().to_list())
    n_bars = len(unique_ts)
    
    # 60% Train, 40% Out-of-Sample Test with 7-day embargo
    split_idx = int(n_bars * 0.60) + 42
    test_ts = unique_ts[split_idx:]
    
    print(f"[BACKTEST] Total 4H Bars: {n_bars} | Out-of-Sample Test Bars: {len(test_ts)} (~{len(test_ts)*4/24:.1f} days)")
    
    initial_capital = 10_000.0
    capital = initial_capital
    equity_curve = [capital]
    returns_list = []
    maker_rebates_collected = 0.0

    prev_weights = {}

    for t_idx, ts in enumerate(test_ts[:-1]):
        current_panel = df.filter(pl.col("timestamp_ms") == ts)
        next_panel = df.filter(pl.col("timestamp_ms") == test_ts[t_idx + 1])
        
        symbols = current_panel.select("symbol").to_series().to_list()
        
        # 1. Dynamic Leverage Governor (Yang-Zhang Vol Targeting)
        market_yz = float(current_panel.select(pl.mean("vol_yang_zhang")).to_series()[0])
        dyn_leverage = float(np.clip(2.5 * (0.035 / (market_yz + 1e-8)), 0.5, 3.50))

        # 2. Historical Returns Covariance Window (42 bars)
        hist_window = df.filter((pl.col("timestamp_ms") <= ts) & (pl.col("timestamp_ms") > ts - (42 * 4 * 3600 * 1000)))
        pivoted_rets = hist_window.pivot(values="ret_4h", index="timestamp_ms", on="symbol").sort("timestamp_ms")
        common_symbols = [s for s in symbols if s in pivoted_rets.columns]
        ret_matrix = pivoted_rets.select(common_symbols).fill_null(0.0).to_numpy()

        alpha_scores = {row["symbol"]: float(row["pred_alpha"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}
        betas = {row["symbol"]: float(row["beta_btc"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}

        # 3. Momentum Core (HRP)
        momentum_weights = optimize_hrp_weights(
            symbols=common_symbols,
            alpha_scores=alpha_scores,
            returns_matrix=ret_matrix,
            target_gross_leverage=dyn_leverage,
            top_k=5
        )

        # 4. Carry Yield Overlay (Null-Space QP)
        carry_yields = {}
        for row in current_panel.iter_rows(named=True):
            sym = row["symbol"]
            if sym in common_symbols:
                _, y_ann = forecast_hourly_funding(
                    instant_basis=float(row["basis_spread"]),
                    volume_zscore=float(row["volume_zscore_72h"]),
                    ret_4h=float(row["ret_4h"]),
                    realized_twap_basis=float(row["basis_spread"])
                )
                carry_yields[sym] = y_ann

        carry_weights = solve_alpha_orthogonal_carry(
            symbols=common_symbols,
            carry_yields=carry_yields,
            alpha_scores=alpha_scores,
            btc_betas=betas,
            returns_matrix=ret_matrix,
            target_carry_leverage=0.60
        )

        # Unified Portfolio Weights
        all_syms = set(list(momentum_weights.keys()) + list(carry_weights.keys()))
        target_weights = {s: momentum_weights.get(s, 0.0) + carry_weights.get(s, 0.0) for s in all_syms}

        # 5. Turnover & Fee Friction (92% Maker Rebate +0.0015%, 8% Taker 0.045%)
        turnover = sum(abs(target_weights.get(s, 0.0) - prev_weights.get(s, 0.0)) for s in set(list(target_weights.keys()) + list(prev_weights.keys())))
        fee_rate = 0.92 * (-0.00015) + 0.08 * (0.00045)  # Net maker rebate capture
        friction_cost = turnover * fee_rate * capital

        # 6. Realized 4H Return
        next_ret_map = {row["symbol"]: float(row["ret_4h"]) for row in next_panel.iter_rows(named=True)}
        period_gross_ret = sum(target_weights[s] * next_ret_map.get(s, 0.0) for s in target_weights)
        
        net_dollar_pnl = (capital * period_gross_ret) - friction_cost
        capital += net_dollar_pnl
        equity_curve.append(capital)
        returns_list.append(net_dollar_pnl / (equity_curve[-2]))
        prev_weights = target_weights

    # --- Performance Metrics Calculation ---
    rets = np.array(returns_list)
    periods_per_year = 6 * 365  # 4H bars in a year
    
    mean_ret = np.mean(rets)
    std_ret = np.std(rets) + 1e-8
    sharpe = (mean_ret / std_ret) * np.sqrt(periods_per_year)
    
    cagr = ((capital / initial_capital) ** (periods_per_year / len(rets)) - 1) * 100
    
    eq_arr = np.array(equity_curve)
    peak = np.maximum.accumulate(eq_arr)
    drawdowns = (eq_arr - peak) / peak
    max_dd = np.min(drawdowns) * 100
    
    win_rate = (np.sum(rets > 0) / len(rets)) * 100
    profit_factor = abs(np.sum(rets[rets > 0])) / (abs(np.sum(rets[rets < 0])) + 1e-8)

    print("\n" + "=" * 65)
    print("           OUT-OF-SAMPLE BACKTEST RESULTS (99-ASSET LAKE)          ")
    print("=" * 65)
    print(f"Initial Capital       : ${initial_capital:,.2f}")
    print(f"Final Equity          : ${capital:,.2f} ({capital/initial_capital:.2f}x multiplier)")
    print(f"Annualized Return CAGR: {cagr:,.2f}%")
    print(f"Out-of-Sample Sharpe  : {sharpe:.2f}")
    print(f"Maximum Drawdown (MDD): {max_dd:.2f}%")
    print(f"Win Rate (4H Bars)    : {win_rate:.2f}%")
    print(f"Profit Factor         : {profit_factor:.2f}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_backtest()

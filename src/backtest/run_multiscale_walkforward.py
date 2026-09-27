import sys
import json
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
from scipy.stats import spearmanr, norm
from catboost import CatBoost, Pool

from src.optimization.hrp_optimizer import optimize_hrp_weights
from src.signals.funding_forecaster import forecast_hourly_funding, solve_alpha_orthogonal_carry

LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"

FEATURE_COLS = [
    "ret_4h", "ret_24h", "ret_72h", "ret_168h",
    "volume_zscore_72h", "basis_spread", "vol_yang_zhang", "beta_btc"
]

def compute_deflated_sharpe_ratio(sharpe: float, returns: np.ndarray, n_trials: int = 50) -> float:
    n = len(returns)
    if n < 30 or np.std(returns) == 0:
        return 0.50
    skew = float(np.mean((returns - np.mean(returns))**3) / (np.std(returns)**3 + 1e-8))
    kurt = float(np.mean((returns - np.mean(returns))**4) / (np.std(returns)**4 + 1e-8))
    
    em_const = 0.5772156649
    e_max_s = (1 - em_const) * norm.ppf(1 - 1/n_trials) + em_const * norm.ppf(1 - 1/(n_trials * np.e))
    var_sr = (1 + 0.5 * sharpe**2 - skew * sharpe + ((kurt - 3) / 4) * sharpe**2) / (n - 1)
    z = (sharpe - e_max_s) / np.sqrt(max(var_sr, 1e-8))
    return float(norm.cdf(z))

def run_multiscale_backtest(n_epochs: int = 78, step_bars: int = 8, embargo_bars: int = 42, initial_capital: float = 1000.0):
    print(f"[MULTI-SCALE] Initializing Tri-Horizon Ensemble (12H / 48H / 168H) across 99 Assets...")
    
    raw_df = pl.read_parquet(LAKE_FILE)
    
    # 1. Engineer Multi-Scale Residual Targets
    # 12H Fast Mean-Reversion Target (3 bars)
    # 48H Medium Drift Target (12 bars)
    # 168H Macro Trend Target (42 bars)
    df = raw_df.with_columns([
        (pl.col("close").shift(-3).over("symbol") / pl.col("close")).log().alias("fwd_ret_12h"),
        (pl.col("close").shift(-12).over("symbol") / pl.col("close")).log().alias("fwd_ret_48h"),
        (pl.col("close").shift(-42).over("symbol") / pl.col("close")).log().alias("fwd_ret_168h"),
    ])
    
    btc_targets = df.filter(pl.col("symbol") == "BTC").select([
        "timestamp_ms",
        pl.col("fwd_ret_12h").alias("btc_fwd_12h"),
        pl.col("fwd_ret_48h").alias("btc_fwd_48h"),
        pl.col("fwd_ret_168h").alias("btc_fwd_168h"),
    ])
    df = df.join(btc_targets, on="timestamp_ms", how="left")
    
    df = df.with_columns([
        # Microstructure mean-reversion target (anticipate counter-drift)
        (-1.0 * (pl.col("fwd_ret_12h") - (pl.col("beta_btc") * pl.col("btc_fwd_12h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_12h_reversion"),
        # Medium-term drift target
        ((pl.col("fwd_ret_48h") - (pl.col("beta_btc") * pl.col("btc_fwd_48h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_48h_drift"),
        # Macro trend-following target
        ((pl.col("fwd_ret_168h") - (pl.col("beta_btc") * pl.col("btc_fwd_168h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_168h_trend")
    ]).drop_nulls(subset=FEATURE_COLS + ["target_12h_reversion", "target_48h_drift", "target_168h_trend"])

    unique_ts = sorted(df.select("timestamp_ms").to_series().unique().to_list())
    total_bars = len(unique_ts)
    ts_to_grp = {ts: idx for idx, ts in enumerate(unique_ts)}
    df = df.with_columns(pl.col("timestamp_ms").replace(ts_to_grp).alias("group_id")).sort(["group_id", "symbol"])

    eval_bars_needed = n_epochs * step_bars
    start_train_end = total_bars - eval_bars_needed - embargo_bars

    capital = initial_capital
    equity_curve = [capital]
    returns_series = []
    epoch_metrics = []
    prev_weights = {}

    print(f"[MULTI-SCALE] Warmup: {start_train_end} bars ({start_train_end*4/24:.1f} days) | Breadth: Top/Bottom 12 perps ($K=12$)")
    print("-" * 75)

    for epoch in range(n_epochs):
        train_end_grp = start_train_end + (epoch * step_bars)
        test_start_grp = train_end_grp + embargo_bars
        test_end_grp = min(test_start_grp + step_bars, total_bars)

        if test_start_grp >= total_bars:
            break

        train_df = df.filter(pl.col("group_id") < train_end_grp)
        test_df = df.filter((pl.col("group_id") >= test_start_grp) & (pl.col("group_id") < test_end_grp))

        # Train 3 Orthogonal YetiRank Sub-Models
        X_train = train_df.select(FEATURE_COLS).to_pandas()
        grp_train = train_df.select("group_id").to_series().to_numpy()
        X_test = test_df.select(FEATURE_COLS).to_pandas()

        base_params = {
            "iterations": 150, "depth": 4, "learning_rate": 0.04,
            "l2_leaf_reg": 3.0, "subsample": 0.75, "loss_function": "YetiRank",
            "thread_count": -1, "verbose": False, "random_seed": 42 + epoch
        }

        # Model 1: 12H Reversion
        pool_12 = Pool(X_train, train_df.select("target_12h_reversion").to_series().to_numpy(), group_id=grp_train)
        m_12 = CatBoost(base_params).fit(pool_12)
        preds_12 = m_12.predict(X_test)

        # Model 2: 48H Drift
        pool_48 = Pool(X_train, train_df.select("target_48h_drift").to_series().to_numpy(), group_id=grp_train)
        m_48 = CatBoost(base_params).fit(pool_48)
        preds_48 = m_48.predict(X_test)

        # Model 3: 168H Macro
        pool_168 = Pool(X_train, train_df.select("target_168h_trend").to_series().to_numpy(), group_id=grp_train)
        m_168 = CatBoost(base_params).fit(pool_168)
        preds_168 = m_168.predict(X_test)

        # Ensemble Score (Equal-Risk Weighted Blend: 30% Micro, 45% Drift, 25% Macro)
        ensemble_score = (0.30 * preds_12) + (0.45 * preds_48) + (0.25 * preds_168)
        test_df = test_df.with_columns(pl.Series("pred_alpha", ensemble_score))

        # Out-of-Sample Bar Execution
        for grp in range(test_start_grp, test_end_grp):
            current_panel = test_df.filter(pl.col("group_id") == grp)
            if current_panel.height == 0 or grp + 1 >= total_bars:
                continue
                
            next_panel = df.filter(pl.col("group_id") == grp + 1)
            symbols = current_panel.select("symbol").to_series().to_list()

            # Volatility-Acceleration Leverage Governor (Capped at 1.75x)
            market_yz = float(current_panel.select(pl.mean("vol_yang_zhang")).to_series()[0])
            if market_yz > 0.045:  # Crisis Vol Spike
                dyn_leverage = 0.50
            else:
                dyn_leverage = float(np.clip(1.50 * (0.025 / (market_yz + 1e-8)), 0.60, 1.75))

            # 42-Bar Rolling Covariance
            hist_sub = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 42))
            pivoted_rets = hist_sub.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
            common_symbols = [s for s in symbols if s in pivoted_rets.columns]
            ret_matrix = pivoted_rets.select(common_symbols).fill_null(0.0).to_numpy()

            alpha_scores = {row["symbol"]: float(row["pred_alpha"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}
            betas = {row["symbol"]: float(row["beta_btc"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}

            # Momentum Core with Expanded Breadth (Top 12 Longs / Top 12 Shorts)
            momentum_weights = optimize_hrp_weights(
                symbols=common_symbols,
                alpha_scores=alpha_scores,
                returns_matrix=ret_matrix,
                target_gross_leverage=dyn_leverage,
                top_k=12
            )

            # Basis Carry Overlay
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
                target_carry_leverage=0.50
            )

            # Combined Target Allocations & Friction
            target_weights = {s: momentum_weights.get(s, 0.0) + carry_weights.get(s, 0.0) for s in set(list(momentum_weights.keys()) + list(carry_weights.keys()))}
            all_eval = set(list(target_weights.keys()) + list(prev_weights.keys()))
            turnover = sum(abs(target_weights.get(s, 0.0) - prev_weights.get(s, 0.0)) for s in all_eval)
            
            # Net Maker Execution Friction
            net_fee = 0.92 * (-0.00015) + 0.08 * (0.00045)
            friction_cost = turnover * net_fee * capital

            next_rets = {row["symbol"]: float(row["ret_4h"]) for row in next_panel.iter_rows(named=True)}
            gross_pnl_pct = sum(target_weights[s] * next_rets.get(s, 0.0) for s in target_weights)
            
            dollar_pnl = (capital * gross_pnl_pct) - friction_cost
            capital += dollar_pnl
            equity_curve.append(capital)
            returns_series.append(dollar_pnl / equity_curve[-2])
            prev_weights = target_weights

        if (epoch + 1) % 10 == 0 or epoch == n_epochs - 1:
            print(f"Epoch {epoch+1:02d}/{n_epochs:02d} | Train: {train_end_grp} bars | OOS: {test_start_grp}-{test_end_grp} | Equity: ${capital:,.2f}")

    rets = np.array(returns_series)
    total_days = (len(rets) * 4) / 24.0
    periods_per_year = 6 * 365
    
    mean_ret = np.mean(rets)
    std_ret = np.std(rets) + 1e-8
    sharpe = float((mean_ret / std_ret) * np.sqrt(periods_per_year))
    cagr = float(((capital / initial_capital) ** (365.0 / total_days) - 1) * 100) if total_days > 0 else 0.0
    
    eq_arr = np.array(equity_curve)
    peak = np.maximum.accumulate(eq_arr)
    drawdowns = (eq_arr - peak) / peak
    max_dd = float(np.min(drawdowns) * 100)
    
    win_rate = float((np.sum(rets > 0) / len(rets)) * 100)
    profit_factor = float(abs(np.sum(rets[rets > 0])) / (abs(np.sum(rets[rets < 0])) + 1e-8))
    dsr = compute_deflated_sharpe_ratio(sharpe, rets, n_trials=50)

    print("\n" + "=" * 70)
    print("      MULTI-SCALE ENSEMBLE (K=12) WALK-FORWARD VALIDATION SUMMARY   ")
    print("=" * 70)
    print(f"Total Retraining Epochs   : {n_epochs}")
    print(f"Out-of-Sample Horizon     : {total_days:.1f} days ({len(rets)} discrete 4H bars)")
    print(f"Starting Capital          : ${initial_capital:,.2f}")
    print(f"Ending Capital            : ${capital:,.2f} ({capital/initial_capital:.2f}x multiplier)")
    print(f"Annualized Return (CAGR)  : {cagr:,.2f}%")
    print(f"Out-of-Sample Sharpe      : {sharpe:.2f}")
    print(f"Maximum Drawdown (MDD)    : {max_dd:.2f}%")
    print(f"Deflated Sharpe Ratio(DSR): {dsr * 100:.2f}%")
    print(f"4H Bar Win Rate           : {win_rate:.2f}%")
    print(f"Profit Factor             : {profit_factor:.2f}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_multiscale_backtest()

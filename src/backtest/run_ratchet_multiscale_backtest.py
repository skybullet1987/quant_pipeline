import sys
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
    if n < 30 or np.std(returns) == 0: return 0.50
    skew = float(np.mean((returns - np.mean(returns))**3) / (np.std(returns)**3 + 1e-8))
    kurt = float(np.mean((returns - np.mean(returns))**4) / (np.std(returns)**4 + 1e-8))
    em_const = 0.5772156649
    e_max_s = (1 - em_const) * norm.ppf(1 - 1/n_trials) + em_const * norm.ppf(1 - 1/(n_trials * np.e))
    var_sr = (1 + 0.5 * sharpe**2 - skew * sharpe + ((kurt - 3) / 4) * sharpe**2) / (n - 1)
    z = (sharpe - e_max_s) / np.sqrt(max(var_sr, 1e-8))
    return float(norm.cdf(z))

def run_backtest():
    print("[BACKTEST] Loading PIT Feature Lake from Parquet...")
    df = pl.read_parquet(LAKE_FILE)

    df = df.with_columns([
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
    df = df.join(btc_targets, on="timestamp_ms", how="left").with_columns([
        (-1.0 * (pl.col("fwd_ret_12h") - (pl.col("beta_btc") * pl.col("btc_fwd_12h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_12h_reversion"),
        ((pl.col("fwd_ret_48h") - (pl.col("beta_btc") * pl.col("btc_fwd_48h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_48h_drift"),
        ((pl.col("fwd_ret_168h") - (pl.col("beta_btc") * pl.col("btc_fwd_168h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_168h_trend")
    ]).drop_nulls(subset=FEATURE_COLS + ["target_12h_reversion", "target_48h_drift", "target_168h_trend"])

    unique_ts = sorted(df.select("timestamp_ms").to_series().unique().to_list())
    total_bars = len(unique_ts)
    ts_to_grp = {ts: idx for idx, ts in enumerate(unique_ts)}
    df = df.with_columns(pl.col("timestamp_ms").replace(ts_to_grp).alias("group_id")).sort(["group_id", "symbol"])

    split_idx = int(total_bars * 0.60) + 42
    test_ts = unique_ts[split_idx:]
    initial_capital = 1000.0
    capital = initial_capital
    equity_curve = [capital]
    returns_series = []
    prev_weights = {}

    print(f"[BACKTEST] Evaluating Out-of-Sample Horizon: {len(test_ts)} discrete 4H bars (~{len(test_ts)*4/24:.1f} days)...")
    
    # Train Initial Tri-Horizon Models
    train_df = df.filter(pl.col("group_id") < (split_idx - 42))
    X_tr = train_df.select(FEATURE_COLS).to_pandas()
    grp_tr = train_df.select("group_id").to_series().to_numpy()

    p = {"iterations": 150, "depth": 4, "learning_rate": 0.04, "l2_leaf_reg": 3.5, "loss_function": "YetiRank", "thread_count": -1, "verbose": False}
    m12 = CatBoost(p).fit(Pool(X_tr, train_df.select("target_12h_reversion").to_series().to_numpy(), group_id=grp_tr))
    m48 = CatBoost(p).fit(Pool(X_tr, train_df.select("target_48h_drift").to_series().to_numpy(), group_id=grp_tr))
    m168 = CatBoost(p).fit(Pool(X_tr, train_df.select("target_168h_trend").to_series().to_numpy(), group_id=grp_tr))

    for t_idx, ts in enumerate(test_ts[:-1]):
        current_panel = df.filter(pl.col("timestamp_ms") == ts)
        next_panel = df.filter(pl.col("timestamp_ms") == test_ts[t_idx + 1])
        symbols = current_panel.select("symbol").to_series().to_list()

        X_cur = current_panel.select(FEATURE_COLS).to_pandas()
        p12 = m12.predict(X_cur)
        p48 = m48.predict(X_cur)
        p168 = m168.predict(X_cur)
        alpha_blend = (0.30 * p12) + (0.45 * p48) + (0.25 * p168)
        current_panel = current_panel.with_columns(pl.Series("pred_alpha", alpha_blend))

        market_yz = float(current_panel.select(pl.mean("vol_yang_zhang")).to_series()[0])
        dyn_leverage = float(np.clip(1.50 * (0.025 / (market_yz + 1e-8)), 0.60, 1.75))

        hist_sub = df.filter((pl.col("timestamp_ms") <= ts) & (pl.col("timestamp_ms") > ts - (42 * 4 * 3600 * 1000)))
        pivoted_rets = hist_sub.pivot(values="ret_4h", index="timestamp_ms", on="symbol").sort("timestamp_ms")
        common_symbols = [s for s in symbols if s in pivoted_rets.columns]
        ret_matrix = pivoted_rets.select(common_symbols).fill_null(0.0).to_numpy()

        alpha_scores = {row["symbol"]: float(row["pred_alpha"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}
        betas = {row["symbol"]: float(row["beta_btc"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}

        momentum_weights = optimize_hrp_weights(common_symbols, alpha_scores, ret_matrix, dyn_leverage, top_k=8)

        carry_yields = {}
        for row in current_panel.iter_rows(named=True):
            sym = row["symbol"]
            if sym in common_symbols:
                _, y_ann = forecast_hourly_funding(float(row["basis_spread"]), float(row["volume_zscore_72h"]), float(row["ret_4h"]), float(row["basis_spread"]))
                carry_yields[sym] = y_ann

        carry_weights = solve_alpha_orthogonal_carry(common_symbols, carry_yields, alpha_scores, betas, ret_matrix, target_carry_leverage=0.50)

        target_weights = {s: momentum_weights.get(s, 0.0) + carry_weights.get(s, 0.0) for s in set(list(momentum_weights.keys()) + list(carry_weights.keys()))}
        turnover = sum(abs(target_weights.get(s, 0.0) - prev_weights.get(s, 0.0)) for s in set(list(target_weights.keys()) + list(prev_weights.keys())))
        
        # 92% Maker Rebate (-1.5 bps) + 8% Taker (+4.5 bps)
        net_fee = 0.92 * (-0.00015) + 0.08 * (0.00045)
        friction = turnover * net_fee * capital

        next_rets = {row["symbol"]: float(row["ret_4h"]) for row in next_panel.iter_rows(named=True)}
        gross_pnl_pct = sum(target_weights[s] * next_rets.get(s, 0.0) for s in target_weights)

        dollar_pnl = (capital * gross_pnl_pct) - friction
        capital += dollar_pnl
        equity_curve.append(capital)
        returns_series.append(dollar_pnl / equity_curve[-2])
        prev_weights = target_weights

    rets = np.array(returns_series)
    total_days = (len(rets) * 4) / 24.0
    periods_year = 6 * 365
    mean_r, std_r = np.mean(rets), np.std(rets) + 1e-8
    sharpe = float((mean_r / std_r) * np.sqrt(periods_year))
    cagr = float(((capital / initial_capital) ** (365.0 / total_days) - 1) * 100) if total_days > 0 else 0.0
    eq_arr = np.array(equity_curve)
    peaks = np.maximum.accumulate(eq_arr)
    max_dd = float(np.min((eq_arr - peaks) / peaks) * 100)
    win_rate = float((np.sum(rets > 0) / len(rets)) * 100)
    pf = float(abs(np.sum(rets[rets > 0])) / (abs(np.sum(rets[rets < 0])) + 1e-8))
    dsr = compute_deflated_sharpe_ratio(sharpe, rets)

    print("\n" + "=" * 70)
    print("      MULTI-SCALE + HRP + DEFENDED ALO WALK-FORWARD PERFORMANCE      ")
    print("=" * 70)
    print(f"Out-of-Sample Days        : {total_days:.1f} days ({len(rets)} discrete 4H bars)")
    print(f"Starting Capital          : ${initial_capital:,.2f}")
    print(f"Ending Capital            : ${capital:,.2f} ({capital/initial_capital:.2f}x multiplier)")
    print(f"Annualized Return (CAGR)  : {cagr:,.2f}%")
    print(f"Out-of-Sample Sharpe      : {sharpe:.2f}")
    print(f"Maximum Drawdown (MDD)    : {max_dd:.2f}%")
    print(f"Deflated Sharpe (DSR)     : {dsr * 100:.2f}%")
    print(f"4H Bar Win Rate           : {win_rate:.2f}%")
    print(f"Profit Factor             : {pf:.2f}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_backtest()

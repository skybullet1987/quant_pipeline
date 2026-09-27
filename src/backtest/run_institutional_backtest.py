import sys
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

import numpy as np
import scipy.stats as stats
import polars as pl
from catboost import CatBoost, Pool
from src.optimization.hrp_optimizer import optimize_hrp_weights
from src.signals.funding_forecaster import forecast_hourly_funding, solve_alpha_orthogonal_carry

LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"

class OnlineMicrostructureHMM:
    def __init__(self):
        self.A = np.array([
            [0.88, 0.10, 0.02],
            [0.12, 0.82, 0.06],
            [0.05, 0.25, 0.70]
        ])
        self.means = np.array([
            [0.018,  1.10, 0.0012],
            [0.038, -0.10, 0.0035],
            [0.075, -2.40, 0.0085]
        ])
        self.cov_diags = np.array([
            [0.008**2, 0.60**2, 0.0008**2],
            [0.015**2, 0.80**2, 0.0018**2],
            [0.030**2, 1.20**2, 0.0040**2]
        ])
        self.gamma = np.array([0.70, 0.25, 0.05])
        
    def filter_step(self, obs: np.ndarray) -> tuple[np.ndarray, float]:
        prior = self.A.T @ self.gamma
        likelihoods = np.zeros(3)
        for j in range(3):
            diff = obs - self.means[j]
            var = self.cov_diags[j]
            log_prob = -0.5 * np.sum(np.log(2.0 * np.pi * var) + (diff ** 2) / var)
            likelihoods[j] = np.exp(np.clip(log_prob, -50.0, 50.0))
            
        unnorm = prior * likelihoods
        c_t = np.sum(unnorm)
        self.gamma = unnorm / c_t if c_t > 0 else prior
        
        leverage_tiers = np.array([3.50, 1.60, 0.50])
        dyn_leverage = float(np.dot(self.gamma, leverage_tiers))
        return self.gamma.copy(), dyn_leverage

def calc_deflated_sharpe(returns: np.ndarray, n_trials: int = 25) -> tuple[float, float, float]:
    T = len(returns)
    if T < 5:
        return 0.0, 0.0, 0.0
        
    mean_r = np.mean(returns)
    std_r = np.std(returns) + 1e-8
    ann_sharpe = (mean_r / std_r) * np.sqrt(121.67)
    
    skew = float(stats.skew(returns))
    kurt = float(stats.kurtosis(returns, fisher=False))
    gamma = 0.5772156649
    var_sharpe = 0.5
    sr_0 = np.sqrt(var_sharpe) * ((1 - gamma) * stats.norm.ppf(1 - 1/n_trials) + gamma * stats.norm.ppf(1 - 1/(n_trials * np.e)))
    sr_std = np.sqrt((1 - skew * ann_sharpe + ((kurt - 1) / 4) * (ann_sharpe ** 2)) / (T - 1))
    
    psr = float(stats.norm.cdf((ann_sharpe - 0.0) / (sr_std + 1e-8)))
    dsr = float(stats.norm.cdf((ann_sharpe - sr_0) / (sr_std + 1e-8)))
    return ann_sharpe, psr, dsr

def run_backtest():
    if not LAKE_FILE.exists():
        print(f"Error: Lake artifact not found at {LAKE_FILE}")
        sys.exit(1)

    print(f"Loading PIT Dataset from: {LAKE_FILE}")
    df = pl.read_parquet(LAKE_FILE).sort(["timestamp_ms", "symbol"])
    timestamps = df.select("timestamp_ms").unique().sort("timestamp_ms").to_series().to_list()
    
    features = [
        "ret_4h", "ret_24h", "ret_72h", "ret_168h",
        "vol_yang_zhang", "vol_ratio_24_168", "volume_zscore_72h",
        "basis_spread", "spillover_alpha", "cs_rank_72h"
    ]
    
    epoch_step = 18       # 72H holding period
    min_train_bars = 720  # 120 days warm-up
    embargo_bars = 42     # 7-day structural embargo
    
    rebalance_indices = list(range(min_train_bars, len(timestamps) - epoch_step, epoch_step))
    total_epochs = len(rebalance_indices)
    print(f"Total 4H Bars: {len(timestamps)} | Evaluated OOS Epochs: {total_epochs}\n")
    
    equity = 1.0
    equity_curve = [equity]
    epoch_returns = []
    
    # Microstructure Quoting Defense Frictions
    maker_rebate = -0.00015     # HyperCore Maker Rebate (-1.5 bps)
    taker_fee = 0.00045         # Taker Fee (+4.5 bps)
    spread_slippage = 0.00015   # Reduced adverse selection spread crossing
    stop_slippage = 0.00200     # Jump-adjusted ATR stop slippage
    passive_fill_rate = 0.92    # 92% Maker Fill Efficiency via Level-5 MLOFI/VPIN
    
    hmm = OnlineMicrostructureHMM()
    
    for step_num, idx in enumerate(rebalance_indices, 1):
        t_now = timestamps[idx]
        t_next = timestamps[idx + epoch_step]
        t_train_end = timestamps[idx - embargo_bars]
        
        train_df = df.filter(pl.col("timestamp_ms") <= t_train_end)
        current_panel = df.filter(pl.col("timestamp_ms") == t_now)
        
        # 1. HMM Regime Update
        btc_row = current_panel.filter(pl.col("symbol") == "BTC")
        btc_vol = float(btc_row.select("vol_yang_zhang").to_series()[0]) if len(btc_row) > 0 else 0.03
        oi_z = float(current_panel.select(pl.mean("volume_zscore_72h")).to_series()[0])
        basis_disp = float(current_panel.select(pl.col("basis_spread").std()).to_series()[0])
        if np.isnan(basis_disp):
            basis_disp = 0.002
            
        obs = np.array([btc_vol, oi_z, basis_disp])
        gamma_probs, dyn_leverage = hmm.filter_step(obs)
        dominant_state = int(np.argmax(gamma_probs))
        state_names = ["TRENDING", "CHOP", "CASCADE"]
        
        # 2. YetiRank Alpha Retraining
        train_pool = Pool(
            data=train_df.select(features).to_pandas(),
            label=train_df.select("target_residual_alpha_72h").to_pandas().values.ravel(),
            group_id=train_df.select("group_id").to_pandas().values.ravel()
        )
        
        model = CatBoost({
            "loss_function": "YetiRank",
            "iterations": 100,
            "learning_rate": 0.05,
            "depth": 5,
            "thread_count": -1,
            "verbose": 0
        })
        model.fit(train_pool)
        
        X_test = current_panel.select(features).to_pandas()
        scores = model.predict(X_test)
        current_panel = current_panel.with_columns(pl.Series("pred_alpha", scores))
        
        symbols = current_panel.select("symbol").to_series().to_list()
        hist_window = df.filter(
            (pl.col("timestamp_ms") <= t_now) & 
            (pl.col("timestamp_ms") > t_now - (42 * 4 * 3600 * 1000))
        )
        pivoted_rets = hist_window.pivot(values="ret_4h", index="timestamp_ms", on="symbol").sort("timestamp_ms")
        common_symbols = [s for s in symbols if s in pivoted_rets.columns]
        ret_matrix = pivoted_rets.select(common_symbols).fill_null(0.0).to_numpy()
        
        alpha_scores = {row["symbol"]: float(row["pred_alpha"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}
        
        # 3. Top-5 Long / Bottom-5 Short Momentum Core
        momentum_weights = optimize_hrp_weights(
            symbols=common_symbols,
            alpha_scores=alpha_scores,
            returns_matrix=ret_matrix,
            target_gross_leverage=dyn_leverage,
            top_k=5
        )
        
        # 4. Bar-by-bar execution with MLOFI-defended friction
        epoch_slice = df.filter(
            (pl.col("timestamp_ms") >= t_now) & 
            (pl.col("timestamp_ms") <= t_next) & 
            pl.col("symbol").is_in(list(momentum_weights.keys()))
        ).sort("timestamp_ms")
        
        epoch_pnl = 0.0
        # Net weighted fee per entry/exit leg
        effective_fee_per_side = (passive_fill_rate * maker_rebate) + ((1.0 - passive_fill_rate) * (taker_fee + spread_slippage))
        
        for sym, w in momentum_weights.items():
            sym_bars = epoch_slice.filter(pl.col("symbol") == sym)
            if len(sym_bars) < 2:
                continue
                
            p_entry = float(sym_bars.select("open").to_series()[0])
            p_exit = float(sym_bars.select("close").to_series()[-1])
            atr = float(sym_bars.select("atr_14").to_series()[0])
            
            is_long = (w > 0)
            stop_px = (p_entry - 2.5 * atr) if is_long else (p_entry + 2.5 * atr)
            
            stopped_out = False
            for bar in sym_bars.iter_rows(named=True):
                if is_long and bar["low"] <= stop_px:
                    p_exit = stop_px * (1.0 - stop_slippage)
                    stopped_out = True
                    break
                elif not is_long and bar["high"] >= stop_px:
                    p_exit = stop_px * (1.0 + stop_slippage)
                    stopped_out = True
                    break
                    
            raw_ret = (p_exit - p_entry) / p_entry if is_long else (p_entry - p_exit) / p_entry
            
            basis = float(sym_bars.select("basis_spread").to_series()[0])
            hourly_funding = np.clip(basis / 8.0, -0.0005, 0.0005)
            funding_drag = hourly_funding * (len(sym_bars) * 4) if is_long else -hourly_funding * (len(sym_bars) * 4)
            
            fee_friction = 2 * effective_fee_per_side * abs(w)
            net_leg_ret = (raw_ret * abs(w)) - (abs(funding_drag) * abs(w)) - fee_friction
            epoch_pnl += net_leg_ret
            
        equity *= (1.0 + epoch_pnl)
        equity_curve.append(equity)
        epoch_returns.append(epoch_pnl)
        
        print(f"[{step_num:02d}/{total_epochs:02d}] Regime: {state_names[dominant_state]:<9} | PnL: {epoch_pnl * 100:>+6.2f}% | Equity: {equity:.2f}x | Lev: {dyn_leverage:.2f}x")
        sys.stdout.flush()
        
    ann_sharpe, psr, dsr = calc_deflated_sharpe(np.array(epoch_returns))
    cagr = (equity ** (121.67 / len(epoch_returns))) - 1.0
    vol = np.std(epoch_returns) * np.sqrt(121.67)
    peaks = np.maximum.accumulate(equity_curve)
    max_dd = np.min((np.array(equity_curve) - peaks) / peaks)
    
    print("\n" + "=" * 70)
    print("  MLOFI/VPIN DEFENDED 3-STATE HMM INSTITUTIONAL BACKTEST (92% MAKER)")
    print("=" * 70)
    print(f"{'Ending Equity Multiplier':<30}: {equity:.2f}x")
    print(f"{'Annualized CAGR':<30}: {cagr * 100:.2f}%")
    print(f"{'Annualized Volatility':<30}: {vol * 100:.2f}%")
    print(f"{'Annualized Sharpe Ratio':<30}: {ann_sharpe:.2f}")
    print(f"{'Probabilistic Sharpe (PSR)':<30}: {psr * 100:.2f}%")
    print(f"{'Deflated Sharpe (DSR)':<30}: {dsr * 100:.2f}%")
    print(f"{'Max Out-of-Sample Drawdown':<30}: {max_dd * 100:.2f}%")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_backtest()

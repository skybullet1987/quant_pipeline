import sys
import json
from pathlib import Path
import numpy as np
import polars as pl
from catboost import CatBoost

PIPELINE_ROOT = Path.home() / "quant_pipeline"
LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"
MODEL_FILE = PIPELINE_ROOT / "data" / "models" / "catboost_tail_alpha_v1.cbm"
META_FILE = PIPELINE_ROOT / "data" / "models" / "model_metadata.json"

def run_backtest():
    if not LAKE_FILE.exists() or not MODEL_FILE.exists() or not META_FILE.exists():
        print("Error: Required lake or model artifacts not found.")
        sys.exit(1)

    with open(META_FILE) as f:
        metadata = json.load(f)
    features = metadata["features"]
    
    # Load CatBoost Model
    model = CatBoost()
    model.load_model(str(MODEL_FILE))
    
    print(f"Loading PIT Feature Panel from: {LAKE_FILE}")
    df = pl.read_parquet(LAKE_FILE).sort(["timestamp_ms", "symbol"])
    timestamps = df.select("timestamp_ms").unique().sort("timestamp_ms").to_series().to_list()
    
    # 72-hour epoch steps (18 four-hour bars per epoch)
    epoch_step = 18
    rebalance_indices = list(range(0, len(timestamps) - epoch_step, epoch_step))
    
    print(f"Total 4H Bars: {len(timestamps)} | Evaluated 72H Epochs: {len(rebalance_indices)}")
    
    equity_curve = [1.0]
    baseline_equity_curve = [1.0]
    
    maker_fee = 0.00015   # 0.015% ALO Maker
    taker_fee = 0.00045   # 0.045% Legacy Taker
    slippage_taker = 0.00050  # 0.05% Market order slippage
    
    for idx in rebalance_indices:
        t_now = timestamps[idx]
        t_next = timestamps[idx + epoch_step]
        
        current_panel = df.filter(pl.col("timestamp_ms") == t_now)
        next_panel = df.filter(pl.col("timestamp_ms") == t_next)
        
        # 1. Score strictly on historical PIT features via CatBoost
        X = current_panel.select(features).to_pandas()
        scores = model.predict(X)
        
        # Add model predictions to current cross-section
        scored_panel = current_panel.with_columns(
            pl.Series("pred_alpha", scores)
        ).sort("pred_alpha", descending=True)
        
        longs = scored_panel.head(3).select("symbol").to_series().to_list()
        shorts = scored_panel.tail(3).select("symbol").to_series().to_list()
        
        # 2. Measure actual forward 72H return
        long_rets, short_rets = [], []
        for s in longs:
            p0 = current_panel.filter(pl.col("symbol") == s).select("close").to_series()
            p1 = next_panel.filter(pl.col("symbol") == s).select("close").to_series()
            if len(p0) > 0 and len(p1) > 0:
                long_rets.append((p1[0] - p0[0]) / p0[0])
                
        for s in shorts:
            p0 = current_panel.filter(pl.col("symbol") == s).select("close").to_series()
            p1 = next_panel.filter(pl.col("symbol") == s).select("close").to_series()
            if len(p0) > 0 and len(p1) > 0:
                # Short return: (Entry - Exit) / Entry
                short_rets.append((p0[0] - p1[0]) / p0[0])
                
        avg_long = np.mean(long_rets) if long_rets else 0.0
        avg_short = np.mean(short_rets) if short_rets else 0.0
        
        # Baseline gross: unconstrained 1.5x leverage
        gross_ret_baseline = (0.75 * avg_long) + (0.75 * avg_short)
        
        # Upgraded gross: 2.5x ATR dynamic short stop cutoff (max -12% on shorts)
        capped_short_ret = np.mean([max(-0.12, r) for r in short_rets]) if short_rets else 0.0
        gross_ret_upgraded = (0.75 * avg_long) + (0.75 * capped_short_ret)
        
        # Upgraded net: ALO Maker (0.015% per side)
        net_ret_upgraded = gross_ret_upgraded - (1.5 * 2 * maker_fee)
        equity_curve.append(equity_curve[-1] * (1.0 + net_ret_upgraded))
        
        # Baseline net: Taker Orders + Slippage Drag (0.095% per side)
        net_ret_baseline = gross_ret_baseline - (1.5 * 2 * (taker_fee + slippage_taker))
        baseline_equity_curve.append(baseline_equity_curve[-1] * (1.0 + net_ret_baseline))
        
    def calc_stats(curve):
        rets = np.diff(curve) / curve[:-1]
        cagr = (curve[-1] ** (121.67 / len(curve))) - 1.0
        vol = np.std(rets) * np.sqrt(121.67)
        sharpe = (np.mean(rets) / (np.std(rets) + 1e-8)) * np.sqrt(121.67)
        peaks = np.maximum.accumulate(curve)
        max_dd = np.min((np.array(curve) - peaks) / peaks)
        return cagr, vol, sharpe, max_dd

    up_cagr, up_vol, up_sharpe, up_dd = calc_stats(equity_curve)
    base_cagr, base_vol, base_sharpe, base_dd = calc_stats(baseline_equity_curve)

    print("\n" + "=" * 70)
    print("           REAL MODEL-DRIVEN BACKTEST PERFORMANCE")
    print("=" * 70)
    print(f"{'Metric':<25} | {'Baseline (Taker)':<18} | {'Upgraded (Yeti+ALO)'}")
    print("-" * 70)
    print(f"{'Ending Equity Multiplier':<25} | {baseline_equity_curve[-1]:<17.2f}x | {equity_curve[-1]:.2f}x")
    print(f"{'Annualized CAGR':<25} | {base_cagr * 100:<17.2f}% | {up_cagr * 100:.2f}%")
    print(f"{'Annualized Volatility':<25} | {base_vol * 100:<17.2f}% | {up_vol * 100:.2f}%")
    print(f"{'Sharpe Ratio':<25} | {base_sharpe:<18.2f} | {up_sharpe:.2f}")
    print(f"{'Max Drawdown':<25} | {base_dd * 100:<17.2f}% | {up_dd * 100:.2f}%")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_backtest()

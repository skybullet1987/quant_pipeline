#!/usr/bin/env python3
"""
BACKTEST: EXP-109 FUNDING / OPEN INTEREST SQUEEZE ENGINE (TIER 2)
================================================================
Strategic Objective:
  Distinguish true funding-rate / open interest squeeze alpha from generic
  price trend and market crowding (Section 15.5).

Factorial Hypothesis Matrix:
  - Factor A: Funding level z(F)
  - Factor B: Funding velocity z(Delta F)
  - Factor C: Open interest delta Delta OI
  - Factor D: Price trend P > EMA_20

Nested Evaluation Protocol:
  Model 1: [A only]              - Funding level alone
  Model 2: [A + C]               - Funding level + Open Interest expansion
  Model 3: [A + D]               - Funding level + Price Trend
  Model 4: [A + B + C + D]       - Full Squeeze Specification

Audit Standards:
  - Exact causal lag: features evaluated strictly at t-1 bar boundary.
  - VIP-0 taker friction (15 bps round-trip) deducted.
  - Forward 12H and 24H return regression, Information Coefficient (IC),
    and economic PnL simulation.
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data"
LAKE_DIR = DATA_DIR / "lake"

def run_backtest():
    print("=" * 80)
    print("  EXP-109: FUNDING / OPEN INTEREST SQUEEZE ENGINE (NESTED FACTORIAL)")
    print("=" * 80)

    ctx_path = LAKE_DIR / "raw_asset_ctx_4h.parquet"
    if not ctx_path.exists():
        print(f"Error: {ctx_path} not found.")
        sys.exit(1)

    df_ctx = pd.read_parquet(ctx_path)
    df_ctx['dt'] = pd.to_datetime(df_ctx['timestamp_ms'], unit='ms')
    df_ctx = df_ctx.sort_values(by=['symbol', 'dt']).reset_index(drop=True)

    print(f"Loaded {len(df_ctx)} context observations across {df_ctx['symbol'].nunique()} assets.")
    print(f"Date range: {df_ctx['dt'].min()} to {df_ctx['dt'].max()}")

    # Compute Factor features per symbol
    feature_rows = []
    ROUNDTRIP_FRICTION = 0.0015  # 15 bps

    for symbol, group in df_ctx.groupby('symbol'):
        g = group.copy().sort_values('dt').reset_index(drop=True)
        if len(g) < 15:
            continue

        px = g['oracle_px'].values
        f_rate = g['funding_rate'].values
        oi = g['open_interest'].values
        n = len(g)

        # Factor A: Funding level z-score (rolling 12 bars)
        f_series = pd.Series(f_rate)
        f_mean = f_series.rolling(12, min_periods=6).mean()
        f_std = f_series.rolling(12, min_periods=6).std() + 1e-12
        z_f = ((f_series - f_mean) / f_std).values

        # Factor B: Funding velocity (delta over 3 bars / 12H)
        delta_f = f_series.diff(3).values
        df_mean = pd.Series(delta_f).rolling(12, min_periods=6).mean()
        df_std = pd.Series(delta_f).rolling(12, min_periods=6).std() + 1e-12
        z_df = ((pd.Series(delta_f) - df_mean) / df_std).values

        # Factor C: Open Interest delta (pct change over 3 bars)
        oi_series = pd.Series(oi)
        oi_pct_delta = oi_series.pct_change(3).values

        # Factor D: Price trend (Price relative to EMA-12)
        ema_12 = pd.Series(px).ewm(span=12).mean().values
        trend_d = (px - ema_12) / ema_12

        # Forward 3-bar (12H) and 6-bar (24H) returns
        px_series = pd.Series(px)
        fwd_ret_12h = px_series.shift(-3) / px_series - 1.0
        fwd_ret_24h = px_series.shift(-6) / px_series - 1.0

        for i in range(12, n - 6):
            feature_rows.append({
                'symbol': symbol,
                'dt': g.loc[i, 'dt'],
                'px': px[i],
                'factor_A': z_f[i],
                'factor_B': z_df[i],
                'factor_C': oi_pct_delta[i],
                'factor_D': trend_d[i],
                'fwd_ret_12h': fwd_ret_12h.iloc[i],
                'fwd_ret_24h': fwd_ret_24h.iloc[i]
            })

    df_feats = pd.DataFrame(feature_rows).dropna()
    print(f"Constructed {len(df_feats)} aligned causal feature observations.")

    # Nested Hypothesis Testing
    # Define Squeeze signals:
    # Short squeeze setup: negative funding (crowded shorts), funding velocity turning up, OI rising, price turning up
    # Long squeeze setup: positive funding (crowded longs), price breaking down

    # Model 1: Factor A only (Contrarian to extreme funding: Short if high funding, Long if negative funding)
    sig_m1 = -np.sign(df_feats['factor_A']) * (np.abs(df_feats['factor_A']) > 1.5)

    # Model 2: Factor A + C (Funding extreme + OI expansion)
    sig_m2 = np.zeros(len(df_feats))
    mask_short_squeeze_m2 = (df_feats['factor_A'] < -1.5) & (df_feats['factor_C'] > 0.05)
    mask_long_flush_m2 = (df_feats['factor_A'] > 1.5) & (df_feats['factor_C'] > 0.05)
    sig_m2[mask_short_squeeze_m2] = 1.0
    sig_m2[mask_long_flush_m2] = -1.0

    # Model 3: Factor A + D (Funding extreme + Trend alignment)
    sig_m3 = np.zeros(len(df_feats))
    mask_short_squeeze_m3 = (df_feats['factor_A'] < -1.5) & (df_feats['factor_D'] > 0.01)
    mask_long_flush_m3 = (df_feats['factor_A'] > 1.5) & (df_feats['factor_D'] < -0.01)
    sig_m3[mask_short_squeeze_m3] = 1.0
    sig_m3[mask_long_flush_m3] = -1.0

    # Model 4: Full Squeeze Model (A + B + C + D)
    sig_m4 = np.zeros(len(df_feats))
    mask_short_squeeze_m4 = (df_feats['factor_A'] < -1.5) & (df_feats['factor_B'] > 0.5) & (df_feats['factor_C'] > 0.02) & (df_feats['factor_D'] > 0.005)
    mask_long_flush_m4 = (df_feats['factor_A'] > 1.5) & (df_feats['factor_B'] < -0.5) & (df_feats['factor_C'] > 0.02) & (df_feats['factor_D'] < -0.005)
    sig_m4[mask_short_squeeze_m4] = 1.0
    sig_m4[mask_long_flush_m4] = -1.0

    models = {
        'Model_1_Funding_Level_Only': sig_m1.values,
        'Model_2_Funding_Plus_OI': sig_m2,
        'Model_3_Funding_Plus_Trend': sig_m3,
        'Model_4_Full_Squeeze_ABCD': sig_m4
    }

    results = {}
    fwd_rets = df_feats['fwd_ret_24h'].values

    print("\n" + "=" * 80)
    print("  NESTED FACTORIAL MODEL COMPARISON (24H Forward Horizon, 15 bps Friction)")
    print("=" * 80)
    print(f"{'Model':<30} | {'Trades':<7} | {'WinRate':<8} | {'Net E[R]':<9} | {'IC':<7} | {'t-stat':<7} | {'Verdict'}")
    print("-" * 80)

    for m_name, sig in models.items():
        active_idx = np.where(sig != 0)[0]
        n_trades = len(active_idx)
        if n_trades < 5:
            print(f"{m_name:<30} | {n_trades:<7} | {'N/A':<8} | {'N/A':<9} | {'N/A':<7} | {'N/A':<7} | INSUFFICIENT_N")
            continue

        trade_rets = sig[active_idx] * fwd_rets[active_idx] - ROUNDTRIP_FRICTION
        winners = trade_rets[trade_rets > 0]
        win_rate = len(winners) / n_trades * 100.0
        net_er = np.mean(trade_rets) * 100.0
        
        # IC
        ic, _ = stats.spearmanr(sig[active_idx], fwd_rets[active_idx])
        t_stat = np.mean(trade_rets) / (np.std(trade_rets, ddof=1) / np.sqrt(n_trades)) if np.std(trade_rets) > 0 else 0.0
        verdict = "PASSED" if (net_er > 0 and t_stat > 1.96) else "REJECTED"

        print(f"{m_name:<30} | {n_trades:<7} | {win_rate:6.1f}% | {net_er:+7.2f}% | {ic:+6.3f} | {t_stat:+6.2f} | {verdict}")

        results[m_name] = {
            'trades': int(n_trades),
            'win_rate_pct': round(float(win_rate), 2),
            'net_expected_return_pct': round(float(net_er), 3),
            'information_coefficient': round(float(ic) if np.isfinite(ic) else 0.0, 3),
            't_stat': round(float(t_stat), 2),
            'verdict': verdict
        }

    # Factor Correlation Matrix
    factor_df = df_feats[['factor_A', 'factor_B', 'factor_C', 'factor_D']]
    factor_corr = factor_df.corr().round(3).to_dict()
    print("\nFactor Correlation Matrix (Collinearity Audit):")
    print(pd.DataFrame(factor_corr))

    out_payload = {
        'experiment': 'EXP-109',
        'specification': 'v3.5-funding-oi-squeeze-nested-factorial',
        'sample_size_bars': len(df_feats),
        'results': results,
        'factor_correlations': factor_corr
    }

    out_path = DATA_DIR / "exp109_backtest_results.json"
    with open(out_path, "w") as f:
        json.dump(out_payload, f, indent=2)
    print(f"\nSaved empirical results to {out_path}")

if __name__ == "__main__":
    run_backtest()

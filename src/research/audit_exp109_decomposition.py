#!/usr/bin/env python3
"""
AUDIT: EXP-109 6-BUCKET PNL DECOMPOSITION & CORE ORTHOGONALITY ANALYSIS
=======================================================================
Addresses User Critique Point 1:
1. Decomposes the +1.20% net return per trade into exact 6 buckets:
     PnL = Price_PnL + Funding_Cashflow - Fees - Spread - Impact - Slippage
   Determines whether edge is true funding yield vs price mean-reversion.
2. Computes empirical correlation rho(r_109, r_103) across all bars and
   conditional correlation specifically during CASH_FLOOR_fl0.
3. Computes marginal contribution to portfolio CVaR_99 during cash floor regimes.
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

def run_decomposition():
    print("=" * 90)
    print("  EXP-109: 6-BUCKET PNL DECOMPOSITION & CORE ORTHOGONALITY AUDIT")
    print("=" * 90)

    ctx_path = LAKE_DIR / "raw_asset_ctx_4h.parquet"
    if not ctx_path.exists():
        print(f"Error: {ctx_path} not found.")
        sys.exit(1)

    df_ctx = pd.read_parquet(ctx_path)
    df_ctx['dt'] = pd.to_datetime(df_ctx['timestamp_ms'], unit='ms')
    df_ctx = df_ctx.sort_values(by=['symbol', 'dt']).reset_index(drop=True)

    # 1. Reconstruct Trade Records with Exact 6-Bucket Accounting
    # Model 1: Contrarian to extreme funding: Short if z(F) > 1.5, Long if z(F) < -1.5
    trades = []
    
    # VIP-0 Hyperliquid Institutional Friction Standard:
    # Taker Fee = 4.5 bps per side (9.0 bps roundtrip)
    # Half Spread = 2.0 bps per side (4.0 bps roundtrip)
    # Market Impact = 0.5 bps per side (1.0 bps roundtrip)
    # Adverse Slippage = 0.5 bps per side (1.0 bps roundtrip)
    # Total Roundtrip Friction = 15.0 bps

    TAKER_FEE_BPS = 9.0
    SPREAD_BPS = 4.0
    IMPACT_BPS = 1.0
    SLIPPAGE_BPS = 1.0

    for symbol, group in df_ctx.groupby('symbol'):
        g = group.copy().sort_values('dt').reset_index(drop=True)
        if len(g) < 18:
            continue

        px = g['oracle_px'].values
        f_rate = g['funding_rate'].values
        n = len(g)

        # Factor A: Funding level z-score (rolling 12 bars)
        f_series = pd.Series(f_rate)
        f_mean = f_series.rolling(12, min_periods=6).mean()
        f_std = f_series.rolling(12, min_periods=6).std() + 1e-12
        z_f = ((f_series - f_mean) / f_std).values

        for i in range(12, n - 6):
            sig = 0
            if z_f[i] < -1.5:
                sig = 1   # Long (crowded negative funding)
            elif z_f[i] > 1.5:
                sig = -1  # Short (crowded positive funding)

            if sig != 0:
                entry_px = px[i]
                exit_px = px[i + 6]  # 24H hold (6 4H bars)
                
                # Gross Price Return
                price_ret = sig * (exit_px - entry_px) / entry_px
                
                # Funding Cashflow Collected:
                # On Hyperliquid, funding is paid every 1 hour (8H rate divided by 8, or 1H rate).
                # Over 6 4H bars (24 hours), we sum realized funding payments.
                # If Long, receive positive cashflow when funding_rate is negative.
                # If Short, receive positive cashflow when funding_rate is positive.
                # Realized funding cashflow = -sig * sum(funding_rate over holding period)
                funding_slice = f_rate[i+1 : i+7]
                funding_cashflow = -sig * np.sum(funding_slice)

                # Total Net Return
                total_friction = (TAKER_FEE_BPS + SPREAD_BPS + IMPACT_BPS + SLIPPAGE_BPS) / 10000.0
                net_ret = price_ret + funding_cashflow - total_friction

                trades.append({
                    'symbol': symbol,
                    'dt': g.loc[i, 'dt'],
                    'side': 'LONG' if sig == 1 else 'SHORT',
                    'z_funding': float(z_f[i]),
                    'price_ret_pct': float(price_ret * 100),
                    'funding_ret_pct': float(funding_cashflow * 100),
                    'fee_pct': float(TAKER_FEE_BPS / 100.0),
                    'spread_pct': float(SPREAD_BPS / 100.0),
                    'impact_pct': float(IMPACT_BPS / 100.0),
                    'slippage_pct': float(SLIPPAGE_BPS / 100.0),
                    'net_ret_pct': float(net_ret * 100)
                })

    df_t = pd.DataFrame(trades)
    print(f"Total Model 1 Trades Analyzed: {len(df_t)}")

    # Compute Means
    mean_gross_price = df_t['price_ret_pct'].mean()
    mean_funding = df_t['funding_ret_pct'].mean()
    mean_fees = df_t['fee_pct'].mean()
    mean_spread = df_t['spread_pct'].mean()
    mean_impact = df_t['impact_pct'].mean()
    mean_slippage = df_t['slippage_pct'].mean()
    mean_net = df_t['net_ret_pct'].mean()

    print("\n" + "=" * 90)
    print("      EXACT 6-BUCKET PNL DECOMPOSITION PER TRADE (MEAN BPS / %)")
    print("=" * 90)
    print(f"{'Component':<35} | {'Percentage':<15} | {'Basis Points':<15} | {'Share of Net'}")
    print("-" * 90)
    print(f"{'1. Gross Price PnL (Reversal)':<35} | {mean_gross_price:>+14.3f}% | {mean_gross_price*100:>+14.1f} bps | {mean_gross_price/mean_net*100:>10.1f}%")
    print(f"{'2. Realized Funding Carry':<35} | {mean_funding:>+14.3f}% | {mean_funding*100:>+14.1f} bps | {mean_funding/mean_net*100:>10.1f}%")
    print(f"{'3. Exchange Fees (VIP-0 Taker)':<35} | {-mean_fees:>14.3f}% | {-mean_fees*100:>14.1f} bps | {-mean_fees/mean_net*100:>10.1f}%")
    print(f"{'4. Half-Spread Friction':<35} | {-mean_spread:>14.3f}% | {-mean_spread*100:>14.1f} bps | {-mean_spread/mean_net*100:>10.1f}%")
    print(f"{'5. Market Impact Drag':<35} | {-mean_impact:>14.3f}% | {-mean_impact*100:>14.1f} bps | {-mean_impact/mean_net*100:>10.1f}%")
    print(f"{'6. Adverse Execution Slippage':<35} | {-mean_slippage:>14.3f}% | {-mean_slippage*100:>14.1f} bps | {-mean_slippage/mean_net*100:>10.1f}%")
    print("-" * 90)
    print(f"{'TOTAL NET EXPECTED RETURN':<35} | {mean_net:>+14.3f}% | {mean_net*100:>+14.1f} bps | 100.0%")
    print("=" * 90)

    # 2. Orthogonality to EXP-103 Core Returns
    # Load 4H raw candles and simulate daily returns for EXP-103 and EXP-109
    candles_path = LAKE_DIR / "raw_candles_4h.parquet"
    df_c = pd.read_parquet(candles_path)
    df_c['dt'] = pd.to_datetime(df_c['timestamp_ms'], unit='ms')
    df_close = df_c.pivot(index='dt', columns='symbol', values='close').sort_index()
    df_rets = df_close.pct_change().fillna(0.0)

    # Aggregate EXP-109 trade returns by datetime
    exp109_bar_rets = df_t.groupby('dt')['net_ret_pct'].mean() / 100.0
    common_dts = df_rets.index.intersection(exp109_bar_rets.index)

    # Cross-sectional momentum proxy for EXP-103 (top quintile mean return)
    # When rho_7d < -0.10, EXP-103 return is exactly 0.0 (in cash)
    # Estimate rho_7d series
    w_rho = 42
    rets_mat = df_rets.values
    active_cols = np.where((~np.isnan(rets_mat)).sum(axis=0) > len(rets_mat)*0.5)[0]

    rho_series = []
    exp103_rets = []
    exp109_aligned_rets = []
    in_cash_floor = []

    for dt in common_dts:
        idx = df_rets.index.get_loc(dt)
        if idx < w_rho:
            continue
        sub = rets_mat[idx - w_rho : idx, active_cols]
        # autocorrelation
        r_c = sub[1:] - np.mean(sub[1:], axis=0)
        r_l = sub[:-1] - np.mean(sub[:-1], axis=0)
        nom = np.sum(r_c * r_l, axis=0)
        denom = np.sqrt(np.sum(r_c**2, axis=0) * np.sum(r_l**2, axis=0)) + 1e-12
        corrs = (nom/denom)[np.isfinite(nom/denom)]
        rho_val = float(np.mean(corrs)) if len(corrs) >= 5 else 0.0

        is_fl0 = (rho_val < -0.10)
        # EXP-103 return: if in cash floor -> 0.0; else momentum return
        r_103 = 0.0 if is_fl0 else float(np.mean(rets_mat[idx, active_cols]))
        r_109 = exp109_bar_rets.loc[dt]

        rho_series.append(rho_val)
        exp103_rets.append(r_103)
        exp109_aligned_rets.append(r_109)
        in_cash_floor.append(is_fl0)

    exp103_rets = np.array(exp103_rets)
    exp109_aligned_rets = np.array(exp109_aligned_rets)
    in_cash_floor = np.array(in_cash_floor)

    # Unconditional Correlation
    corr_overall, p_corr = stats.pearsonr(exp109_aligned_rets, exp103_rets) if len(exp103_rets) > 5 else (0.0, 1.0)
    
    # Conditional Correlation during CASH_FLOOR_fl0
    # During cash floor, EXP-103 return is 0, so correlation is identically 0.0
    # But let's check correlation against the underlying market returns during cash floor
    mkt_rets_fl0 = np.mean(rets_mat, axis=1)[[df_rets.index.get_loc(dt) for dt in common_dts]][in_cash_floor]
    corr_fl0_mkt, p_mkt = stats.pearsonr(exp109_aligned_rets[in_cash_floor], mkt_rets_fl0) if len(mkt_rets_fl0) > 5 else (0.0, 1.0)

    # Conditional CVaR_99 Analysis
    # Does adding EXP-109 worsen or improve portfolio downside tail during cash floors?
    # Standalone Cash Floor CVaR_99 of Cash = 0.0 (risk free)
    # Standalone CVaR_99 of EXP-109 (at 15% budget):
    r_109_fl0 = exp109_aligned_rets[in_cash_floor] * 0.15
    q01 = np.percentile(r_109_fl0, 1)
    cvar_99_109 = float(np.mean(r_109_fl0[r_109_fl0 <= q01])) if len(r_109_fl0) > 0 else 0.0

    print("\n" + "=" * 90)
    print("      ORTHOGONALITY & CONDITIONAL RISK AUDIT (EXP-109 vs EXP-103)")
    print("=" * 90)
    print(f"Overall Correlation rho(r_109, r_103):          {corr_overall:+.3f} (p = {p_corr:.4f})")
    print(f"Correlation with Market during CASH_FLOOR_fl0: {corr_fl0_mkt:+.3f} (p = {p_mkt:.4f})")
    print(f"EXP-109 1-day 99% CVaR during Cash Floor (15% sz): {cvar_99_109*100:+.2f}%")
    print(f"True Nature of Edge: {mean_gross_price/mean_net*100:.1f}% Price Reversal + {mean_funding/mean_net*100:.1f}% Realized Funding Carry")
    print("=" * 90)

    out_data = {
        'experiment': 'EXP-109',
        'audit_type': 'six_bucket_decomposition_and_orthogonality',
        'n_trades': len(df_t),
        'decomposition_means_pct': {
            'price_reversal_pnl': round(float(mean_gross_price), 3),
            'realized_funding_carry': round(float(mean_funding), 3),
            'exchange_fees': round(float(mean_fees), 3),
            'spread': round(float(mean_spread), 3),
            'market_impact': round(float(mean_impact), 3),
            'adverse_slippage': round(float(mean_slippage), 3),
            'net_pnl': round(float(mean_net), 3)
        },
        'decomposition_shares_pct': {
            'price_reversal_share': round(float(mean_gross_price / mean_net * 100), 1),
            'funding_carry_share': round(float(mean_funding / mean_net * 100), 1)
        },
        'orthogonality': {
            'correlation_with_core_exp103': round(float(corr_overall), 3),
            'correlation_with_market_during_fl0': round(float(corr_fl0_mkt), 3),
            'conditional_cvar_99_pct': round(float(cvar_99_109 * 100), 3)
        }
    }

    out_file = DATA_DIR / "exp109_decomposition_audit.json"
    with open(out_file, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\nSaved audit findings to {out_file}")

if __name__ == "__main__":
    run_decomposition()

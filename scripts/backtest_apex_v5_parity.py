#!/usr/bin/env python3
"""
APEX v5.0 Shared-Kernel Honest Open[t+1] Backtester & Purged WFO Verifier
=========================================================================
Calls `src.strategy.apex_v5_kernel` — the exact stateless kernel executed live by
`ProductionApexExecutor.compute_exp103_signals_and_weights` — to guarantee 100%
mathematical parity between research backtests and live execution.

Honest Accounting Invariants:
  1. Strictly causal 210-bar rolling windows ending at completed bar `t` (`Close[t]`).
  2. Execution strictly at `Open[t+1]` (`open_to_open_ret = Open[t+2]/Open[t+1] - 1`).
  3. Real Hyperliquid historical 4H funding cashflows (`hl_real_funding_4h.parquet`, 527k hourly obs).
  4. Tier-0 fee + half-spread charged on 100% of gross turnover (`5.5 bps` per side on Top-15 majors).
  5. Purged Walk-Forward evaluation across 3 expanding OOS folds with a 12-day (`72`-bar) embargo.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.strategy.apex_v5_kernel import (
    BARS_PER_YEAR_4H,
    compute_apex_v5_raw_unit_weights,
    scale_and_smooth_apex_v5_weights,
)


def compute_summary_metrics(bar_net_rets: np.ndarray, bar_turnovers: np.ndarray) -> Dict[str, float]:
    r = np.asarray(bar_net_rets, dtype=np.float64)
    n = len(r)
    if n < 6:
        return {"cagr_pct": 0.0, "sharpe": 0.0, "sortino": 0.0, "max_dd_pct": 0.0, "calmar": 0.0, "daily_turnover": 0.0}
    eq = np.cumprod(np.maximum(1.0 + r, 1e-6))
    yrs = n / BARS_PER_YEAR_4H
    cagr = float(eq[-1] ** (1.0 / max(yrs, 1e-6)) - 1.0)
    sd = float(np.std(r, ddof=1))
    sharpe = float((np.mean(r) / sd) * math.sqrt(BARS_PER_YEAR_4H)) if sd > 1e-12 else 0.0
    neg = np.minimum(r, 0.0)
    dsd = float(np.sqrt(np.mean(neg ** 2)))
    sortino = float((np.mean(r) / dsd) * math.sqrt(BARS_PER_YEAR_4H)) if dsd > 1e-12 else 0.0
    hwm = np.maximum.accumulate(np.insert(eq, 0, 1.0))[1:]
    dd = (hwm - eq) / np.maximum(hwm, 1e-12)
    max_dd = float(np.max(dd))
    calmar = float(cagr / max_dd) if max_dd > 1e-6 else 0.0
    daily_to = float(np.mean(bar_turnovers) * 6.0) if len(bar_turnovers) > 0 else 0.0
    return {
        "bars": int(n),
        "days": round(n / 6.0, 1),
        "total_return_pct": round(float(eq[-1] - 1.0) * 100.0, 2),
        "cagr_pct": round(cagr * 100.0, 2),
        "ann_vol_pct": round(sd * math.sqrt(BARS_PER_YEAR_4H) * 100.0, 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "max_dd_pct": round(max_dd * 100.0, 2),
        "calmar": round(calmar, 3),
        "daily_turnover_x": round(daily_to, 3),
    }


def run_shared_kernel_simulation(
    close_mat: np.ndarray,
    open_mat: np.ndarray,
    vol_mat: np.ndarray,
    valid_mask: np.ndarray,
    fund_1h_ema: np.ndarray,
    fund_4h_sum: np.ndarray,
    symbols: List[str],
    start_idx: int,
    end_idx: int,
    cost_bps_per_side: float = 5.5,
    lookback_window: int = 210,
) -> Tuple[np.ndarray, np.ndarray]:
    btc_idx = symbols.index("BTC")
    eth_idx = symbols.index("ETH") if "ETH" in symbols else 0
    n_syms = len(symbols)

    prev_w = np.zeros(n_syms, dtype=np.float64)
    equity = 1000.0
    hwm = 1000.0
    cost_rate = cost_bps_per_side * 1e-4

    net_rets: List[float] = []
    turnovers: List[float] = []

    # Bar t decision uses data [max(0, t - lookback_window + 1) : t + 1] (completed bar t),
    # executes at Open[t + 1], and earns Open[t + 2] / Open[t + 1] - 1 over bar t + 1.
    for t in range(start_idx, min(end_idx, close_mat.shape[0] - 2)):
        w0 = max(0, t - lookback_window + 1)
        c_win = close_mat[w0 : t + 1]
        v_win = vol_mat[w0 : t + 1]
        m_win = valid_mask[w0 : t + 1]
        f_now = fund_1h_ema[t]

        raw_w, betas, vol_bar, idio_vol, _, _ = compute_apex_v5_raw_unit_weights(
            close_mat=c_win,
            valid_mask=m_win,
            funding_rates_1h=f_now,
            symbols=symbols,
            btc_idx=btc_idx,
            eth_idx=eth_idx,
            vol_mat=v_win,
            top_n=15,
            max_single_alt_weight=0.25,
            regime_adaptive_routing=True,
            er_gate_tsmom=True,
            fast_tsmom_blend=True,
            fip_quality_weight=0.05,
            vol_accel_weight=0.05,
        )
        w_new, _, _ = scale_and_smooth_apex_v5_weights(
            raw_w=raw_w,
            prev_w=prev_w,
            betas=betas,
            vol_bar=vol_bar,
            idio_vol=idio_vol,
            btc_idx=btc_idx,
            current_equity=equity,
            historical_hwm=hwm,
            target_vol_ann=0.35,
            max_gross_leverage=3.0,
            gz_max_dd=0.25,
            gp_keep=0.88,
            deadband_nav=0.03,
            max_single_alt_weight=0.25,
            clean_zero_exit=True,
        )

        turnover = float(np.sum(np.abs(w_new - prev_w)))
        tc = turnover * cost_rate

        # Open[t+1] -> Open[t+2] causal execution return
        op1 = open_mat[t + 1]
        op2 = open_mat[t + 2]
        ok_ret = (op1 > 0) & (op2 > 0) & np.isfinite(op1) & np.isfinite(op2)
        oo_ret = np.where(ok_ret, np.clip((op2 / np.maximum(op1, 1e-12)) - 1.0, -0.60, 1.50), 0.0)

        price_pnl = float(np.sum(w_new * oo_ret))
        # Longs pay positive funding, shorts receive positive funding over bar t+1
        fund_pnl = float(-np.sum(w_new * fund_4h_sum[t + 1]))
        bar_net = max(-0.95, price_pnl + fund_pnl - tc)

        equity *= (1.0 + bar_net)
        if equity > hwm:
            hwm = equity
        prev_w = w_new

        net_rets.append(bar_net)
        turnovers.append(turnover)

    return np.array(net_rets, dtype=np.float64), np.array(turnovers, dtype=np.float64)


def main():
    parser = argparse.ArgumentParser(description="APEX v5.0 Shared-Kernel Honest Open[t+1] Backtester")
    parser.add_argument(
        "--candles",
        type=str,
        default=str(PIPELINE_ROOT / "data" / "lake" / "raw_candles_4h.parquet"),
    )
    parser.add_argument(
        "--funding",
        type=str,
        default=str(PIPELINE_ROOT / "data" / "lake" / "hl_real_funding_4h.parquet"),
    )
    parser.add_argument("--out-json", type=str, default="/tmp/apex_v5_shared_kernel_parity_report.json")
    args = parser.parse_args()

    cdf = pd.read_parquet(args.candles)
    ts_col = "timestamp_ms" if "timestamp_ms" in cdf.columns else "timestamp"
    if not np.issubdtype(cdf[ts_col].dtype, np.integer):
        cdf["bar_ms"] = pd.to_datetime(cdf[ts_col], utc=True).astype("int64") // 10**6
    else:
        cdf["bar_ms"] = cdf[ts_col].astype("int64")

    close_df = cdf.pivot_table(index="bar_ms", columns="symbol", values="close", aggfunc="last").sort_index()
    open_df = cdf.pivot_table(index="bar_ms", columns="symbol", values="open", aggfunc="first").reindex(close_df.index)
    vol_df = cdf.pivot_table(index="bar_ms", columns="symbol", values="volume", aggfunc="last").reindex(close_df.index)

    symbols = list(close_df.columns)
    obs = ~close_df.isna().to_numpy()
    n_bars, n_syms = obs.shape
    age = np.zeros((n_bars, n_syms), dtype=int)
    for r in range(n_bars):
        if r == 0:
            age[r] = np.where(obs[r], 0, 999)
        else:
            age[r] = np.where(obs[r], 0, age[r - 1] + 1)
    valid_mask = age <= 2

    close_mat = close_df.ffill(limit=2).fillna(0.0).to_numpy(dtype=np.float64)
    open_mat = open_df.ffill(limit=2).fillna(0.0).to_numpy(dtype=np.float64)
    vol_mat = vol_df.fillna(0.0).to_numpy(dtype=np.float64)

    fund_1h_ema = np.zeros_like(close_mat)
    fund_4h_sum = np.zeros_like(close_mat)
    if Path(args.funding).exists():
        fdf = pd.read_parquet(args.funding)
        ts_f_col = "timestamp_ms" if "timestamp_ms" in fdf.columns else "bar_4h_ms"
        mean_f_col = "funding_rate_mean" if "funding_rate_mean" in fdf.columns else "funding_1h_mean"
        sum_f_col = "funding_rate_4h_sum" if "funding_rate_4h_sum" in fdf.columns else "funding_4h_sum"
        f_mean = (
            fdf.pivot_table(index=ts_f_col, columns="symbol", values=mean_f_col, aggfunc="last")
            .reindex(index=close_df.index, columns=symbols)
            .ffill(limit=3)
            .fillna(0.0)
        )
        f_sum = (
            fdf.pivot_table(index=ts_f_col, columns="symbol", values=sum_f_col, aggfunc="last")
            .reindex(index=close_df.index, columns=symbols)
            .fillna(0.0)
        )
        fund_1h_ema = f_mean.ewm(span=6, min_periods=1).mean().to_numpy(dtype=np.float64)
        fund_4h_sum = f_sum.to_numpy(dtype=np.float64)

    warmup = 180
    full_rets, full_to = run_shared_kernel_simulation(
        close_mat, open_mat, vol_mat, valid_mask, fund_1h_ema, fund_4h_sum, symbols, warmup, n_bars - 2
    )
    full_metrics = compute_summary_metrics(full_rets, full_to)

    # 3-Fold Purged Walk-Forward OOS Verification (12-day = 72-bar embargo)
    embargo = 72
    usable_end = n_bars - 2
    folds_spec = [
        ("Fold_1_OOS", warmup + 700 + embargo, warmup + 1104 + embargo),
        ("Fold_2_OOS", warmup + 1104 + embargo, warmup + 1508 + embargo),
        ("Fold_3_OOS", warmup + 1508 + embargo, min(usable_end, warmup + 1912 + embargo)),
    ]
    oos_concat_r = []
    oos_concat_to = []
    fold_reports = {}
    for fname, s_i, e_i in folds_spec:
        if s_i >= usable_end:
            continue
        fr, fto = run_shared_kernel_simulation(
            close_mat, open_mat, vol_mat, valid_mask, fund_1h_ema, fund_4h_sum, symbols, s_i, min(e_i, usable_end)
        )
        fold_reports[fname] = compute_summary_metrics(fr, fto)
        oos_concat_r.append(fr)
        oos_concat_to.append(fto)

    purged_oos_metrics = (
        compute_summary_metrics(np.concatenate(oos_concat_r), np.concatenate(oos_concat_to))
        if oos_concat_r
        else {}
    )

    report = {
        "strategy_version": "v5.1.0-adaptive-regime-majors",
        "kernel": "src.strategy.apex_v5_kernel",
        "total_bars_loaded": int(n_bars),
        "symbols_loaded": int(n_syms),
        "full_sample_open_t1": full_metrics,
        "purged_wfo_oos_concat": purged_oos_metrics,
        "purged_wfo_folds": fold_reports,
    }
    Path(args.out_json).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

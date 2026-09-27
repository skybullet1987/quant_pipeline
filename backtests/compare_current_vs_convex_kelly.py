"""
Head-to-Head Comparison: Current Setup vs. 10x Convex Kelly Research Engine
===========================================================================
Backtest evaluation with Starting Capital = $1,000.00:
  Strategy A: Current Production Continuous Dollar-Neutral Pipeline
  Strategy B: 10x Convex Fractional Kelly & Asymmetric Beta Engine
"""

import math
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.execution.papertrade_daemon import (
    _load_4h_feature_panel,
    _build_macro_features,
    _compute_delta_dispersion,
    _apply_deadband,
    HMMRegimeGovernor,
    CrossSectionalAlphaRanker,
    DollarNeutralRiskParityAllocator,
    MacroRiskGovernor,
    FEAT_COLS,
    HMM_FEATURE_COLS,
    S2_CASH_CHOKE_THRESHOLD,
    MIN_BREADTH,
    VOL_FLOOR_USD,
)
from src.optimization.convex_risk_engine import (
    compute_bull_conviction_score,
    compute_dynamic_net_beta,
    compute_fractional_kelly_leverage,
)
from src.risk.asymmetric_beta_governor import RMTBetaGovernor
from src.execution.asynchronous_clock import AsynchronousVarianceClock
from src.risk.grossman_zhou_engine import GrossmanZhouRiskGovernor


def run_head_to_head_comparison(initial_capital: float = 1000.0, taker_fee_bps: float = 3.5, slippage_bps: float = 2.0):
    print("=" * 80)
    print("    HEAD-TO-HEAD BACKTEST: CURRENT PRODUCTION vs. 10x CONVEX KELLY SUITE    ")
    print(f"    Starting Capital: ${initial_capital:,.2f} | Execution Horizon: 4H Point-in-Time Lake")
    print("=" * 80)

    # 1. Load Data
    df = _load_4h_feature_panel()
    if df is None or df.height == 0:
        print("[ERROR] Could not load 4H feature panel.")
        return

    ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms"
    timestamps = sorted(df[ts_col].unique().to_list())
    total_bars = len(timestamps)
    friction_rate = (taker_fee_bps + slippage_bps) / 10_000.0

    print(f"\n--> Loaded {df.height:,} rows across {len(df['symbol'].unique())} assets ({total_bars} 4H bars).")

    # Fast Pre-computation: Rolling Beta Residualization & Tri-Alpha Scores
    ranker = CrossSectionalAlphaRanker()
    res_df = ranker.residualize_returns(df)

    # Pre-aggregate returns & price pivots for rapid simulation
    returns_by_bar = {}
    for row in df.select([ts_col, "symbol", "ret_4h"]).iter_rows(named=True):
        t = row[ts_col]
        if t not in returns_by_bar:
            returns_by_bar[t] = {}
        returns_by_bar[t][row["symbol"]] = row["ret_4h"] or 0.0

    # Macro features for HMM
    macro_df = _build_macro_features(res_df)
    macro_features_all = macro_df.select(HMM_FEATURE_COLS).to_numpy()
    macro_ts_list = macro_df[ts_col].to_list()
    macro_idx_map = {ts: i for i, ts in enumerate(macro_ts_list)}

    WARMUP_BARS = 30
    eval_bars = total_bars - WARMUP_BARS - 1

    print(f"--> Initializing 2 parallel strategy walk-forward tracks across {eval_bars} 4H periods...")

    # =========================================================================
    # TRACK A: CURRENT PRODUCTION PIPELINE
    # =========================================================================
    hmm_gov_a = HMMRegimeGovernor()
    allocator_a = DollarNeutralRiskParityAllocator(target_gross_leverage=2.5)
    macro_risk_a = MacroRiskGovernor()

    equity_a = initial_capital
    weights_a = {}
    equity_curve_a = [equity_a]
    turnover_a = []
    lev_a = []

    # =========================================================================
    # TRACK B: 10x CONVEX KELLY & ASYMMETRIC BETA ENGINE
    # =========================================================================
    equity_b = initial_capital
    peak_b = initial_capital
    weights_b = {}
    equity_curve_b = [equity_b]
    turnover_b = []
    lev_b = []
    asym_gov_b = RMTBetaGovernor(n_assets=50, lookback_t=180)
    async_clock_b = AsynchronousVarianceClock()
    gz_gov_b = GrossmanZhouRiskGovernor(d_max=0.22, beta_d=1.35, l_base=4.0, l_max=8.0)

    # Periodic ranker model refit cache (refits every 18 bars / 3 days for fast vector execution)
    cached_model = None
    last_train_bar = -999

    # Pre-calculate point-in-time Delta Dispersion lookup dictionary
    vol_expr = pl.col("volume") >= pl.col("volume").median().over(ts_col) * 0.20
    liquid_disp = res_df.filter(vol_expr & pl.col("ret_72h").is_not_null())
    disp_df = (
        liquid_disp.group_by(ts_col)
        .agg([
            pl.col("ret_72h").std().alias("cs_disp_72h"),
            pl.len().alias("count"),
        ])
        .filter(pl.col("count") >= 10)
        .sort(ts_col)
        .with_columns([pl.col("cs_disp_72h").rolling_mean(24).alias("cs_disp_ma24")])
        .with_columns([(pl.col("cs_disp_72h") - pl.col("cs_disp_ma24")).alias("delta_disp_24h")])
        .fill_null(0.005)
    )
    delta_disp_map = {row[ts_col]: (row["delta_disp_24h"] or 0.005) for row in disp_df.iter_rows(named=True)}

    start_t = time.time()

    for idx in range(WARMUP_BARS, total_bars - 1):
        curr_ts = timestamps[idx]
        next_ts = timestamps[idx + 1]

        hist_df = res_df.filter(pl.col(ts_col) <= curr_ts)
        curr_snap = res_df.filter(pl.col(ts_col) == curr_ts)
        next_rets = returns_by_bar.get(next_ts, {})

        # -------------------------------------------------------------
        # 1. Macro Regime & Alpha Scoring (Shared Foundation)
        # -------------------------------------------------------------
        m_idx = macro_idx_map.get(curr_ts, -1)
        if m_idx >= 10:
            if (idx - last_train_bar) >= 18 or hmm_gov_a.model is None:
                hmm_gov_a.fit(macro_features_all[:m_idx])
            active_state, omega_h = hmm_gov_a.compute_regime_entropy(macro_features_all[m_idx])
        else:
            active_state, omega_h = 1, 0.5

        delta_disp = delta_disp_map.get(curr_ts, 0.005)

        # Train / update ranker every 18 bars (3 days)
        if (idx - last_train_bar) >= 18 or cached_model is None:
            train_snap = hist_df.filter(pl.col(ts_col) < curr_ts)
            avail_feats = [c for c in FEAT_COLS if c in train_snap.columns]
            if avail_feats and train_snap.height > 100:
                train_snap = train_snap.with_columns(
                    (pl.col("residual_return") > 0).cast(pl.Int32).alias("forward_res_decile")
                )
                ranker.train_lambdarank(train_snap, avail_feats)
                cached_model = True
                last_train_bar = idx

        avail_feats = [c for c in FEAT_COLS if c in curr_snap.columns]
        ranked_df = ranker.rank_universe(curr_snap, avail_feats) if cached_model else curr_snap

        # -------------------------------------------------------------
        # TRACK A EXECUTION (Current Setup: S2 Choke + Strict Dollar-Neutral)
        # -------------------------------------------------------------
        if delta_disp <= S2_CASH_CHOKE_THRESHOLD:
            target_weights_a = {}
        else:
            panel_a = curr_snap.filter(
                (pl.col("close") * pl.col("volume") >= VOL_FLOOR_USD)
                & pl.col("vol_yang_zhang").is_not_null()
            )
            if panel_a.height < MIN_BREADTH:
                target_weights_a = {}
            else:
                macro_scale_a = macro_risk_a.compute_leverage_multiplier(current_equity=equity_a)
                order_batch_a = allocator_a.allocate(ranked_df, macro_omega=macro_scale_a * omega_h)
                if hasattr(order_batch_a, "weights") and isinstance(order_batch_a.weights, dict):
                    raw_a = order_batch_a.weights
                else:
                    sym_col = "symbol" if "symbol" in order_batch_a.columns else "ticker"
                    raw_a = dict(zip(order_batch_a[sym_col].to_list(), order_batch_a["target_weight"].to_list()))
                target_weights_a = _apply_deadband(raw_a, weights_a)

        # Track A PnL & Turnover
        all_syms_a = set(weights_a.keys()).union(target_weights_a.keys())
        to_a = sum(abs(target_weights_a.get(s, 0.0) - weights_a.get(s, 0.0)) for s in all_syms_a)
        fee_a = equity_a * to_a * friction_rate
        pnl_a = sum(equity_a * w * next_rets.get(s, 0.0) for s, w in target_weights_a.items()) - fee_a
        equity_a += pnl_a
        weights_a = target_weights_a

        equity_curve_a.append(equity_a)
        turnover_a.append(to_a)
        lev_a.append(sum(abs(w) for w in target_weights_a.values()))

        # -------------------------------------------------------------
        # TRACK B EXECUTION (10x Convex Kelly & Asymmetric Beta Engine)
        # -------------------------------------------------------------
        # 1. Calculate Bull Conviction Score S_t & Grossman-Zhou Dynamic Leverage
        alpha_scores = ranked_df["predicted_rank_score"].to_numpy() if "predicted_rank_score" in ranked_df.columns else np.array([0.0])
        alpha_skew = float(np.mean(alpha_scores)) if len(alpha_scores) > 0 else 0.0
        btc_sub = curr_snap.filter(pl.col("symbol") == "BTC")
        btc_trend = float(btc_sub["ret_4h"][0]) if btc_sub.height > 0 else 0.0
        bull_score = 0.50 + 0.30 * np.tanh(alpha_skew * 5.0) + 0.20 * np.tanh(btc_trend * 10.0)

        target_lev_b, _ = gz_gov_b.compute_leverage(
            equity=equity_b,
            bull_score=bull_score,
            regime_entropy=omega_h,
            funding_rate_avg=0.0001,
        )

        # 2. Asymmetric Gearing with Benchmark Beta Hedging (Pillars 1 & 4)
        alt_betas = {}
        if "beta_btc" in curr_snap.columns:
            for row in curr_snap.select(["symbol", "beta_btc"]).iter_rows():
                alt_betas[row[0]] = float(row[1]) if row[1] is not None else 1.2

        raw_target_b = asym_gov_b.allocate_asymmetric_portfolio(
            ranked_df=ranked_df,
            regime_state=active_state,
            clarity_omega=omega_h,
            target_gross_leverage=target_lev_b,
            alt_betas=alt_betas,
        )

        # 3. Apply Leland Optimal Deadband (Pillar 2)
        vols_b = {}
        if "vol_yang_zhang" in curr_snap.columns:
            for row in curr_snap.select(["symbol", "vol_yang_zhang"]).iter_rows():
                vols_b[row[0]] = float(row[1]) if row[1] is not None else 0.03

        target_weights_b = async_clock_b.filter_leland_deadband(raw_target_b, weights_b, vols_b)

        # Track B PnL & Turnover
        all_syms_b = set(weights_b.keys()).union(target_weights_b.keys())
        to_b = sum(abs(target_weights_b.get(s, 0.0) - weights_b.get(s, 0.0)) for s in all_syms_b)
        fee_b = equity_b * to_b * friction_rate
        pnl_b = sum(equity_b * w * next_rets.get(s, 0.0) for s, w in target_weights_b.items()) - fee_b
        equity_b += pnl_b
        if equity_b > peak_b:
            peak_b = equity_b
        weights_b = target_weights_b

        equity_curve_b.append(equity_b)
        turnover_b.append(to_b)
        lev_b.append(sum(abs(w) for w in target_weights_b.values()))

    sim_time = time.time() - start_t
    print(f"--> Both simulations completed in {sim_time:.2f}s.\n")

    # =========================================================================
    # PERFORMANCE METRICS CALCULATION
    # =========================================================================
    def compute_stats(eq_arr, to_arr, lev_arr):
        eq_arr = np.array(eq_arr)
        total_pnl = eq_arr[-1] - initial_capital
        ret_pct = (total_pnl / initial_capital) * 100.0
        days = (len(eq_arr) * 4) / 24.0
        cagr = ((eq_arr[-1] / initial_capital) ** (365.25 / max(days, 1.0)) - 1.0) * 100.0

        bar_rets = np.diff(eq_arr) / eq_arr[:-1]
        mean_ret = np.mean(bar_rets) if len(bar_rets) > 0 else 0.0
        std_ret = np.std(bar_rets) if len(bar_rets) > 0 else 1e-8
        ann_factor = math.sqrt(365.25 * 6)
        sharpe = (mean_ret / std_ret) * ann_factor

        down_rets = bar_rets[bar_rets < 0]
        down_std = np.std(down_rets) if len(down_rets) > 0 else 1e-8
        sortino = (mean_ret / down_std) * ann_factor

        cummax = np.maximum.accumulate(eq_arr)
        dds = (eq_arr - cummax) / cummax
        mdd = abs(np.min(dds)) * 100.0
        calmar = (cagr / mdd) if mdd > 0 else np.nan

        wins = np.sum(bar_rets > 0)
        losses = np.sum(bar_rets < 0)
        win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0
        gross_win = np.sum(bar_rets[bar_rets > 0])
        gross_loss = abs(np.sum(bar_rets[bar_rets < 0]))
        pf = (gross_win / gross_loss) if gross_loss > 0 else np.nan

        return {
            "final_equity": eq_arr[-1],
            "total_pnl": total_pnl,
            "ret_pct": ret_pct,
            "cagr": cagr,
            "sharpe": sharpe,
            "sortino": sortino,
            "calmar": calmar,
            "mdd": mdd,
            "win_rate": win_rate,
            "profit_factor": pf,
            "avg_lev": np.mean(lev_arr),
            "avg_turnover": np.mean(to_arr),
        }

    stats_a = compute_stats(equity_curve_a, turnover_a, lev_a)
    stats_b = compute_stats(equity_curve_b, turnover_b, lev_b)

    # =========================================================================
    # PRINT COMPARISON SCOREBOARD
    # =========================================================================
    print("=" * 86)
    print("                    HEAD-TO-HEAD PERFORMANCE SCOREBOARD                    ")
    print("=" * 86)
    print(f"{'METRIC':<32} | {'STRATEGY A (CURRENT)':<24} | {'STRATEGY B (10x CONVEX KELLY)':<24}")
    print("-" * 86)
    print(f"{'Starting Capital':<32} | ${initial_capital:<23,.2f} | ${initial_capital:<23,.2f}")
    print(f"{'Ending Equity':<32} | ${stats_a['final_equity']:<23,.2f} | ${stats_b['final_equity']:<23,.2f}")
    print(f"{'Total Net Profit':<32} | ${stats_a['total_pnl']:<+23,.2f} | ${stats_b['total_pnl']:<+23,.2f}")
    print(f"{'Cumulative Return':<32} | {stats_a['ret_pct']:<+23.2f}% | {stats_b['ret_pct']:<+23.2f}%")
    print(f"{'Annualized Return (CAGR)':<32} | {stats_a['cagr']:<+23.2f}% | {stats_b['cagr']:<+23.2f}%")
    print("-" * 86)
    print(f"{'Annualized Sharpe Ratio':<32} | {stats_a['sharpe']:<24.2f} | {stats_b['sharpe']:<24.2f}")
    print(f"{'Annualized Sortino Ratio':<32} | {stats_a['sortino']:<24.2f} | {stats_b['sortino']:<24.2f}")
    print(f"{'Calmar Ratio':<32} | {stats_a['calmar']:<24.2f} | {stats_b['calmar']:<24.2f}")
    print(f"{'Maximum Drawdown (MDD)':<32} | {stats_a['mdd']:<23.2f}% | {stats_b['mdd']:<23.2f}%")
    print("-" * 86)
    print(f"{'4H Bar Win Rate':<32} | {stats_a['win_rate']:<23.1f}% | {stats_b['win_rate']:<23.1f}%")
    print(f"{'Profit Factor':<32} | {stats_a['profit_factor']:<24.2f} | {stats_b['profit_factor']:<24.2f}")
    print(f"{'Average Gross Leverage':<32} | {stats_a['avg_lev']:<23.2f}x | {stats_b['avg_lev']:<23.2f}x")
    print(f"{'Avg Turnover per 4H Bar':<32} | {stats_a['avg_turnover']:<23.2%} | {stats_b['avg_turnover']:<23.2%}")
    print("=" * 86)

    return stats_a, stats_b


if __name__ == "__main__":
    run_head_to_head_comparison()

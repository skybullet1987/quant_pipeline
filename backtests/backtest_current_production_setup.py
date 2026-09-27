"""
Backtest Engine for Current Production Setup
=============================================
Simulates the exact production pipeline currently active in papertrade_daemon.py:
  1. 4H PIT Feature Extraction & Rolling Beta Residualization
  2. Causal Online HMM Regime Governor (Bull, Bear, Chop)
  3. Cross-Sectional LambdaRank Ranking Engine
  4. Dollar-Neutral Risk-Parity Allocation
  5. 5.0% Leland Deadband Filtering
  6. S2 Cash Choke & Universe Breadth Gating
  7. Realistic Friction Model (3.5 bps taker + 2.0 bps slippage)
"""

import math
import sys
import time
from pathlib import Path

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


def run_production_backtest(initial_capital: float = 10_000.0, taker_fee_bps: float = 3.5, slippage_bps: float = 2.0):
    print("=" * 75)
    print("      CURRENT PRODUCTION PIPELINE BACKTEST (DUAL-CLOCK 4H PARITY)      ")
    print("=" * 75)

    print("\n--> [1/4] Loading and normalizing 4H Point-in-Time feature panel...")
    df = _load_4h_feature_panel()
    if df is None or df.height == 0:
        print("[ERROR] Failed to load 4H feature panel.")
        return

    ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms"
    timestamps = sorted(df[ts_col].unique().to_list())
    total_bars = len(timestamps)
    print(f"Loaded {df.height:,} rows across {len(df['symbol'].unique())} symbols over {total_bars} 4H periods.")

    # Warmup period: require at least 30 4H bars (~5 days) for rolling stats and HMM initialization
    WARMUP_BARS = 30
    if total_bars <= WARMUP_BARS:
        print(f"[ERROR] Total bars ({total_bars}) <= warmup bars ({WARMUP_BARS}).")
        return

    print("\n--> [2/4] Initializing Production Model Components...")
    hmm_gov = HMMRegimeGovernor()
    ranker = CrossSectionalAlphaRanker()
    allocator = DollarNeutralRiskParityAllocator(target_gross_leverage=2.5)
    macro_risk = MacroRiskGovernor()

    # Pre-residualize returns
    print("--> Vectorizing beta residualization across universe...")
    res_df = ranker.residualize_returns(df)

    print("\n--> [3/4] Executing Sequential Walk-Forward Simulation...")
    equity = initial_capital
    previous_weights = {}
    
    equity_curve = []
    timestamps_record = []
    leverage_record = []
    regime_record = []
    turnover_record = []
    pnl_record = []
    choke_count = 0
    breadth_count = 0

    # Build price lookup for next-bar return realization
    # Pivot returns: {symbol: ret_4h} per timestamp
    returns_by_bar = {}
    for row in df.select([ts_col, "symbol", "ret_4h"]).iter_rows(named=True):
        t = row[ts_col]
        if t not in returns_by_bar:
            returns_by_bar[t] = {}
        returns_by_bar[t][row["symbol"]] = row["ret_4h"] or 0.0

    friction_rate = (taker_fee_bps + slippage_bps) / 10_000.0

    start_time = time.time()

    for idx in range(WARMUP_BARS, total_bars - 1):
        curr_ts = timestamps[idx]
        next_ts = timestamps[idx + 1]

        # Slice historical window up to curr_ts
        hist_df = res_df.filter(pl.col(ts_col) <= curr_ts)
        curr_snap = res_df.filter(pl.col(ts_col) == curr_ts)

        # 1. Delta dispersion & S2 cash choke
        delta_disp = _compute_delta_dispersion(hist_df)
        if delta_disp <= S2_CASH_CHOKE_THRESHOLD:
            choke_count += 1
            target_weights = {}
            active_state = "S2_CHOKE"
            omega_h = 0.0
        else:
            # 2. Breadth gate
            panel = curr_snap.filter(
                (pl.col("close") * pl.col("volume") >= VOL_FLOOR_USD)
                & pl.col("vol_yang_zhang").is_not_null()
            )
            n_avail = panel.height
            if n_avail < MIN_BREADTH:
                breadth_count += 1
                target_weights = {}
                active_state = "BREADTH_GATE"
                omega_h = 0.0
            else:
                # 3. Causal HMM Regime
                macro_df = _build_macro_features(hist_df)
                hmm_features = macro_df.select(HMM_FEATURE_COLS).to_numpy()
                if len(hmm_features) >= 10:
                    hmm_gov.fit(hmm_features[:-1])
                    active_state, omega_h = hmm_gov.compute_regime_entropy(hmm_features[-1])
                else:
                    active_state, omega_h = "CHOP", 0.5

                # 4. Macro risk scalar
                macro_scale = macro_risk.compute_leverage_multiplier(current_equity=equity)

                # 5. LambdaRank Alpha Ranking
                train_snap = hist_df.filter(pl.col(ts_col) < curr_ts)
                avail_feat_cols = [c for c in FEAT_COLS if c in train_snap.columns]
                
                if avail_feat_cols and train_snap.height > 100:
                    train_snap = train_snap.with_columns(
                        (pl.col("residual_return") > 0).cast(pl.Int32).alias("forward_res_decile")
                    )
                    ranker.train_lambdarank(train_snap, avail_feat_cols)
                    ranked_df = ranker.rank_universe(curr_snap, avail_feat_cols)

                    # 6. Dollar-neutral allocation
                    order_batch = allocator.allocate(ranked_df, macro_omega=macro_scale * omega_h)
                    if hasattr(order_batch, "weights") and isinstance(order_batch.weights, dict):
                        raw_target = order_batch.weights
                    else:
                        sym_col = "symbol" if "symbol" in order_batch.columns else "ticker"
                        raw_target = dict(
                            zip(order_batch[sym_col].to_list(), order_batch["target_weight"].to_list())
                        )
                    
                    # 7. Leland Deadband (5.0%)
                    target_weights = _apply_deadband(raw_target, previous_weights)
                else:
                    target_weights = {}

        # Compute Portfolio Rebalance Turnover & Transaction Friction
        all_syms = set(previous_weights.keys()).union(target_weights.keys())
        turnover = sum(abs(target_weights.get(s, 0.0) - previous_weights.get(s, 0.0)) for s in all_syms)
        fee_cost = equity * turnover * friction_rate

        # Compute Realized Period Return (over next 4H candle)
        next_rets = returns_by_bar.get(next_ts, {})
        gross_bar_pnl = sum(equity * weight * next_rets.get(sym, 0.0) for sym, weight in target_weights.items())

        net_bar_pnl = gross_bar_pnl - fee_cost
        equity += net_bar_pnl

        # Track metrics
        gross_lev = sum(abs(w) for w in target_weights.values())
        equity_curve.append(equity)
        timestamps_record.append(next_ts)
        leverage_record.append(gross_lev)
        regime_record.append(active_state)
        turnover_record.append(turnover)
        pnl_record.append(net_bar_pnl)

        previous_weights = target_weights

    elapsed = time.time() - start_time
    print(f"Simulation completed across {len(equity_curve)} 4H rebalance epochs in {elapsed:.2f}s.")

    # ── 4. Comprehensive Performance Analytics ────────────────────────
    print("\n--> [4/4] Computing Risk-Adjusted Performance Analytics...")
    eq_series = np.array(equity_curve)
    pnl_series = np.array(pnl_record)
    lev_series = np.array(leverage_record)

    total_bars_eval = len(eq_series)
    days = (total_bars_eval * 4) / 24.0

    total_pnl = equity - initial_capital
    total_ret_pct = (total_pnl / initial_capital) * 100.0
    cagr = ((equity / initial_capital) ** (365.25 / max(days, 1.0)) - 1.0) * 100.0

    # Returns series
    ret_series = np.diff(eq_series) / eq_series[:-1]
    
    # 4H to Annualized Sharpe / Sortino
    mean_ret_4h = np.mean(ret_series) if len(ret_series) > 0 else 0.0
    std_ret_4h = np.std(ret_series) if len(ret_series) > 0 else 1e-8
    ann_factor = math.sqrt(365.25 * 6)  # 6 4H bars per day
    sharpe = (mean_ret_4h / (std_ret_4h + 1e-8)) * ann_factor

    downside_rets = ret_series[ret_series < 0]
    downside_std = np.std(downside_rets) if len(downside_rets) > 0 else 1e-8
    sortino = (mean_ret_4h / downside_std) * ann_factor

    # Drawdown Analytics
    cummax = np.maximum.accumulate(eq_series)
    drawdowns = (eq_series - cummax) / cummax
    max_dd_pct = abs(np.min(drawdowns)) * 100.0
    calmar = (cagr / max_dd_pct) if max_dd_pct > 0 else np.nan

    # Win Rate & Profit Factor
    winning_bars = np.sum(pnl_series > 0)
    losing_bars = np.sum(pnl_series < 0)
    bar_win_rate = (winning_bars / (winning_bars + losing_bars) * 100.0) if (winning_bars + losing_bars) > 0 else 0.0

    gross_profit = np.sum(pnl_series[pnl_series > 0])
    gross_loss = abs(np.sum(pnl_series[pnl_series < 0]))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.nan

    # Average metrics
    avg_gross_lev = np.mean(lev_series)
    avg_turnover = np.mean(turnover_record)
    total_fees_paid = sum(initial_capital * t * friction_rate for t in turnover_record)

    print("\n" + "=" * 70)
    print("      PRODUCTION SETUP WALK-FORWARD BACKTEST RESULTS")
    print("=" * 70)
    print(f"Evaluation Period        : {days:.1f} Days ({total_bars_eval} 4H periods)")
    print(f"Starting Capital         : ${initial_capital:,.2f}")
    print(f"Final Equity             : ${equity:,.2f}")
    print(f"Net Profit               : ${total_pnl:+,.2f} ({total_ret_pct:+.2f}%)")
    print(f"Annualized Return (CAGR) : {cagr:+.2f}%")
    print("-" * 70)
    print(f"Annualized Sharpe Ratio  : {sharpe:.2f}")
    print(f"Annualized Sortino Ratio : {sortino:.2f}")
    print(f"Calmar Ratio             : {calmar:.2f}")
    print(f"Maximum Drawdown (MDD)   : {max_dd_pct:.2f}%")
    print("-" * 70)
    print(f"4H Bar Win Rate          : {bar_win_rate:.1f}% ({winning_bars}W / {losing_bars}L)")
    print(f"Profit Factor            : {profit_factor:.2f}")
    print(f"Avg Gross Leverage       : {avg_gross_lev:.2f}x")
    print(f"Avg Turnover per 4H Bar  : {avg_turnover:.2%}")
    print(f"S2 Choke Trigger Count   : {choke_count} bars")
    print(f"Breadth Gate Count       : {breadth_count} bars")
    print("=" * 70)

    return {
        "initial_capital": initial_capital,
        "final_equity": equity,
        "net_pnl": total_pnl,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_dd": max_dd_pct,
        "profit_factor": profit_factor,
        "win_rate": bar_win_rate,
    }


if __name__ == "__main__":
    run_production_backtest()

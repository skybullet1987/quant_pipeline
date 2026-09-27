import sys
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
from scipy.stats import skew, spearmanr
from sklearn.covariance import LedoitWolf

from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.backtest_models import OnlineMicrostructureHMM
from src.backtest.backtest_matured_ir import compute_ensemble_alpha
from src.backtest.run_fast_institutional_matrix import precompute_rolling_predictions
from src.optimization.convex_risk_engine import compute_bull_conviction_score, compute_dynamic_net_beta, compute_fractional_kelly_leverage
from src.optimization.clarabel_conic_optimizer import compute_softmax_conviction_weights, solve_clarabel_conic_portfolio
from src.risk.adaptive_parabolic_exits import ConvexPosition, evaluate_convex_position_exits
from src.signals.funding_forecaster import forecast_hourly_funding

def run_convex_backtest():
    print("=" * 95)
    print("   CONVEX ALPHA BACKTEST: FRACTIONAL KELLY (0.5x-5.0x) + ASYMMETRIC BETA (0.0-2.5)   ")
    print("=" * 95)

    df, unique_ts, grp_to_ts = load_and_prepare_panel()
    preds_12, preds_48, preds_168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42

    capital = 1000.0
    peak_capital = 1000.0
    equity_curve = [capital]
    rets = []
    positions = {}
    hmm = OnlineMicrostructureHMM()
    last_reb = 0
    matured_ic_hist = {"12h": [], "48h": [], "168h": []}

    target_map = {"12h": ("target_12h_alpha", 3), "48h": ("target_48h_drift", 12), "168h": ("target_168h_trend", 42)}

    # Rolling indicators history
    s_t_history = []
    realized_leverages = []
    realized_betas = []

    print("\n[SIMULATION] Executing High-Convexity Walk-Forward Engine...")

    for grp in range(start_eval_grp, total_grps - 1):
        if grp not in preds_12: continue
        c_pan = df.filter(pl.col("group_id") == grp)
        n_pan = df.filter(pl.col("group_id") == grp + 1)
        if c_pan.height == 0 or n_pan.height == 0: continue

        c_rows = {r["symbol"]: r for r in c_pan.iter_rows(named=True)}
        n_rows = {r["symbol"]: r for r in n_pan.iter_rows(named=True)}
        symbols = list(c_rows.keys())

        if grp in hmm_data:
            hmm.fit_from_training_observations(hmm_data[grp])

        # 1. HMM Step
        b_row = c_pan.filter(pl.col("symbol") == "BTC")
        b_vol = float(b_row.select("vol_yang_zhang").to_series()[0]) if len(b_row) > 0 else 0.03
        obs = np.array([b_vol, float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0]), 0.002])
        hmm_probs, hmm_lev, dom_state = hmm.filter_step(obs)

        # 2. Matured Prediction Processing
        for h_name, (t_col, delay) in target_map.items():
            mat_grp = grp - delay
            if mat_grp in preds_12:
                old_p = preds_12[mat_grp] if h_name == "12h" else (preds_48[mat_grp] if h_name == "48h" else preds_168[mat_grp])
                past_panel = df.filter(pl.col("group_id") == mat_grp).to_dicts()
                past_targets = {r["symbol"]: r.get(t_col) for r in past_panel if r.get(t_col) is not None}
                common = [s for s in old_p if s in past_targets]
                if len(common) >= 20:
                    ic, _ = spearmanr([old_p[s] for s in common], [past_targets[s] for s in common])
                    if not np.isnan(ic): matured_ic_hist[h_name].append(ic)

        p12_arr = np.array([preds_12[grp][s] for s in symbols])
        p48_arr = np.array([preds_48[grp][s] for s in symbols])
        p168_arr = np.array([preds_168[grp][s] for s in symbols])
        alpha_vec = compute_ensemble_alpha(p12_arr, p48_arr, p168_arr, matured_ic_hist, use_dynamic_ir=True)
        alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

        # 3. Dynamic Stop Exits (Parabolic YZ + 4.0x ATR Catastrophe Collar)
        bar_pnl = 0.0
        stopped_syms = []
        rank_order = np.argsort(alpha_vec)
        ranks_pct = {symbols[rank_order[i]]: i / len(symbols) for i in range(len(symbols))}

        for sym, pos in list(positions.items()):
            if sym not in n_rows or sym not in c_rows: continue
            r_nxt, r_cur = n_rows[sym], c_rows[sym]
            p_cur, p_nxt_hi, p_nxt_lo, p_nxt_cl = r_cur["close"], r_nxt["high"], r_nxt["low"], r_nxt["close"]
            sig_cur = float(r_cur.get("vol_yang_zhang", 0.04))

            is_exit, exit_px, exit_type = evaluate_convex_position_exits(
                pos, p_nxt_hi, p_nxt_lo, p_nxt_cl, sig_cur, ranks_pct.get(sym, 0.5)
            )

            if is_exit:
                if pos.is_long:
                    pnl_mult = (exit_px - p_cur) / p_cur
                else:
                    pnl_mult = (p_cur - exit_px) / p_cur
                fee = capital * abs(pos.weight) * (0.00045 if exit_type == "CATASTROPHE_COLLAR" else -0.00015)
                bar_pnl += (capital * abs(pos.weight) * pnl_mult) - fee
                stopped_syms.append(sym)
            else:
                pnl_mult = (p_nxt_cl - p_cur) / p_cur if pos.is_long else (p_cur - p_nxt_cl) / p_cur
                bar_pnl += capital * abs(pos.weight) * pnl_mult

        for s in stopped_syms: del positions[s]

        # 4. Periodic Rebalance & Optimization
        rebal_fee = 0.0
        if (grp - last_reb) >= 6 or last_reb == 0:
            last_reb = grp
            hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
            piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
            v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]

            if len(v_cols) >= 15:
                shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
                a_sub = np.array([alpha_dict[s] for s in v_cols])
                b_sub = np.array([c_rows[s]["beta_btc"] for s in v_cols])
                m_yz = float(c_pan.select(pl.mean("vol_yang_zhang")).to_series()[0])

                # Calculate Bull Conviction Score S_t
                alpha_sk = float(skew(a_sub))
                btc_trend = float(c_rows["BTC"]["ret_168h"] / (c_rows["BTC"]["vol_yang_zhang"] + 1e-6)) if "BTC" in c_rows else 0.5
                oi_vel = float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0])
                basis_exp = float(c_pan.select(pl.mean("basis_spread")).to_series()[0])
                s_t = compute_bull_conviction_score(alpha_sk, btc_trend, oi_vel, basis_exp)
                s_t_history.append(s_t)

                # Target Beta Target [0.0, +2.50]
                target_beta = compute_dynamic_net_beta(s_t, hmm_probs)

                # Fractional Kelly Gross Leverage [0.50x, 5.00x]
                current_dd = (peak_capital - capital) / peak_capital
                alpha_disp = float(np.percentile(a_sub, 90) - np.median(a_sub))
                ic_recent = float(np.mean(matured_ic_hist["48h"][-20:])) if len(matured_ic_hist["48h"]) >= 10 else 0.05
                target_lev, telem = compute_fractional_kelly_leverage(ic_recent, alpha_disp, m_yz, current_dd, portfolio_funding_rate=0.10)

                # Softmax Conviction Tilting (K_long=4, K_short=3, tau=0.85)
                alpha_conv, l_idx, s_idx = compute_softmax_conviction_weights(a_sub, top_k_long=4, top_k_short=3, tau_temp=0.85)

                # Forecast Carry
                carry_y = np.array([forecast_hourly_funding(float(c_rows[s]["basis_spread"]), float(c_rows[s]["volume_zscore_72h"]), float(c_rows[s]["ret_4h"]), float(c_rows[s]["basis_spread"]))[1] for s in v_cols])

                # Solve Clarabel SOCP Problem
                prev_w = np.array([positions[s].weight if s in positions else 0.0 for s in v_cols])
                w_opt = solve_clarabel_conic_portfolio(
                    cov_shrunk=shrunk_cov,
                    alpha_conviction=alpha_conv,
                    betas_btc=b_sub,
                    carry_yields=carry_y,
                    w_prev=prev_w,
                    target_net_beta=target_beta,
                    target_gross_leverage=target_lev,
                    long_idx=l_idx,
                    short_idx=s_idx
                )

                # Synchronize Positions
                tgt = {v_cols[i]: float(w_opt[i]) for i in range(len(v_cols)) if abs(w_opt[i]) > 0.005}
                turnover = 0.0
                all_s = set(list(tgt.keys()) + list(positions.keys()))
                for s in all_s:
                    w_t = tgt.get(s, 0.0)
                    w_c = positions[s].weight if s in positions else 0.0
                    turnover += abs(w_t - w_c)
                    if abs(w_t) < 0.005 and s in positions:
                        del positions[s]
                    elif abs(w_t) >= 0.005 and (s not in positions or (w_t * w_c < 0)):
                        r_c = c_rows.get(s)
                        if r_c:
                            px, atr = r_c["close"], r_c["atr_14"]
                            sig = r_c["vol_yang_zhang"]
                            is_l = w_t > 0
                            sl_cat = px - (4.0 * atr) if is_l else px + (4.0 * atr)
                            sl_par = px * (1.0 - 4.0 * sig * np.sqrt(4/24)) if is_l else px * (1.0 + 4.0 * sig * np.sqrt(4/24))
                            positions[s] = ConvexPosition(s, is_l, w_t, px, atr, sig, px, px, sl_par, sl_cat, grp)
                    elif s in positions:
                        positions[s].weight = w_t

                rebal_fee = turnover * (0.92 * -0.00015 + 0.08 * 0.00045) * capital
                realized_leverages.append(np.sum(np.abs(list(tgt.values()))))
                realized_betas.append(target_beta)

        d_pnl = bar_pnl - rebal_fee
        capital += d_pnl
        peak_capital = max(peak_capital, capital)
        equity_curve.append(capital)
        rets.append(d_pnl / equity_curve[-2])

    r_arr = np.array(rets)
    days = (len(r_arr) * 4) / 24.0
    sharpe = float((np.mean(r_arr) / (np.std(r_arr) + 1e-8)) * np.sqrt(2190))
    neg_rets = r_arr[r_arr < 0]
    sortino = float((np.mean(r_arr) / (np.std(neg_rets) + 1e-8)) * np.sqrt(2190)) if len(neg_rets) > 0 else sharpe
    cagr = float(((capital / 1000.0) ** (365.0 / days) - 1) * 100) if days > 0 else 0.0
    eq = np.array(equity_curve)
    mdd = float(np.min((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)) * 100)
    pf = float(abs(np.sum(r_arr[r_arr > 0])) / (abs(np.sum(r_arr[r_arr < 0])) + 1e-8))

    print("\n" + "=" * 95)
    print("                      CONVEX ARCHITECTURE PERFORMANCE REPORT                         ")
    print("=" * 95)
    print(f" • Out-of-Sample Period    : {grp_to_ts[start_eval_grp]} to {grp_to_ts[total_grps-1]} ({days:.1f} Days)")
    print(f" • Starting Capital        : $1,000.00")
    print(f" • Ending Portfolio Equity : ${capital:,.2f}")
    print(f" • Annualized Return (CAGR): {cagr:>+6.1f}%")
    print(f" • Maximum Drawdown (MDD)  : {mdd:>5.1f}% (Drawdown Brake Limit: 28.0%)")
    print(f" • Sharpe Ratio            : {sharpe:.2f} | Sortino Ratio: {sortino:.2f}")
    print(f" • Profit Factor           : {pf:.2f} | 4H Win Rate: {(np.sum(r_arr > 0) / len(r_arr)) * 100:.1f}%")
    print(f" • Average Gross Leverage  : {np.mean(realized_leverages):.2f}x (Peak: {np.max(realized_leverages):.2f}x)")
    print(f" • Average Net Beta Target : {np.mean(realized_betas):+.2f} (Peak Bull Beta: {np.max(realized_betas):+.2f})")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    run_convex_backtest()

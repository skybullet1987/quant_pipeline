import sys
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
import pandas as pd
from scipy.stats import skew, spearmanr
from sklearn.covariance import LedoitWolf

from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.backtest_models import OnlineMicrostructureHMM, Position
from src.backtest.backtest_matured_ir import compute_ensemble_alpha
from src.backtest.backtest_positions import evaluate_intrabar_stops, sync_positions
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.backtest.run_fast_institutional_matrix import precompute_rolling_predictions
from src.signals.funding_forecaster import forecast_hourly_funding

from src.optimization.convex_core import (
    compute_bull_conviction_score,
    compute_clean_dynamic_beta,
    compute_risk_scaled_leverage,
    compute_softmax_weights_with_caps,
    solve_clarabel_socp
)

def evaluate_ablation_trial(
    df: pl.DataFrame,
    preds_12: dict,
    preds_48: dict,
    preds_168: dict,
    hmm_data: dict,
    cfg_name: str,
    enable_dyn_beta: bool = False,
    enable_dyn_lev: bool = False,
    enable_socp: bool = False
) -> dict:
    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42

    capital, peak_capital = 1000.0, 1000.0
    equity_curve = [capital]
    rets, turnovers = [], []
    positions = {}
    hmm = OnlineMicrostructureHMM()
    last_reb = 0
    matured_ic_hist = {"12h": [], "48h": [], "168h": []}

    target_map = {"12h": ("target_12h_alpha", 3), "48h": ("target_48h_drift", 12), "168h": ("target_168h_trend", 42)}

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

        b_row = c_pan.filter(pl.col("symbol") == "BTC")
        b_vol = float(b_row.select("vol_yang_zhang").to_series()[0]) if len(b_row) > 0 else 0.03
        obs = np.array([b_vol, float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0]), 0.002])
        hmm_probs, hmm_lev, dom_state = hmm.filter_step(obs)

        # Dynamic IC
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

        # Disaster Collar Evaluation
        bar_pnl, stopped = evaluate_intrabar_stops(positions, c_rows, n_rows, capital, use_ratchet=False, disaster_stop_atr=3.5)
        for s in stopped: del positions[s]

        # 24H Rebalance
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

                # Leverage Scaling
                if enable_dyn_lev:
                    curr_dd = (peak_capital - capital) / peak_capital
                    disp = float(np.percentile(a_sub, 90) - np.median(a_sub))
                    ic_rec = float(np.mean(matured_ic_hist["48h"][-20:])) if len(matured_ic_hist["48h"]) >= 10 else 0.05
                    target_lev, _ = compute_risk_scaled_leverage(ic_rec, disp, m_yz, curr_dd, 0.10, base_leverage=1.75)
                else:
                    vol_s = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))
                    target_lev = float(np.clip(hmm_lev * (1.75 / 1.50) * vol_s, 0.50, 1.75))

                # Dynamic Beta
                if enable_dyn_beta:
                    a_sk = float(skew(a_sub))
                    btc_t = float(c_rows["BTC"]["ret_168h"] / (c_rows["BTC"]["vol_yang_zhang"] + 1e-6)) if "BTC" in c_rows else 0.5
                    oi_v = float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0])
                    bas_e = float(c_pan.select(pl.mean("basis_spread")).to_series()[0])
                    s_t = compute_bull_conviction_score(a_sk, btc_t, oi_v, bas_e)
                    target_beta = compute_clean_dynamic_beta(s_t, hmm_probs)
                else:
                    target_beta = 0.0

                carry_y = np.array([forecast_hourly_funding(float(c_rows[s]["basis_spread"]), float(c_rows[s]["volume_zscore_72h"]), float(c_rows[s]["ret_4h"]), float(c_rows[s]["basis_spread"]))[1] for s in v_cols])

                if enable_socp:
                    alpha_conv, l_idx, s_idx = compute_softmax_weights_with_caps(a_sub, top_k_long=5, top_k_short=4, tau_temp=0.85)
                    prev_w = np.array([positions[s].weight if s in positions else 0.0 for s in v_cols])
                    w_comb = solve_clarabel_socp(shrunk_cov, alpha_conv, b_sub, carry_y, prev_w, target_beta, target_lev, l_idx, s_idx)
                else:
                    w_mom = compute_hrp_from_cov(shrunk_cov, a_sub, target_lev, top_k=5)
                    if dom_state == 0:
                        # Apply asymmetric bull short multiplier
                        short_mult = 0.35 if not enable_dyn_beta else max(0.10, 0.35 - (target_beta * 0.10))
                        w_mom[w_mom < 0] *= short_mult

                    w_car = compute_null_space_carry(shrunk_cov, carry_y, a_sub, b_sub, target_carry_leverage=0.40)
                    w_comb = w_mom + w_car
                    g_exp = np.sum(np.abs(w_comb))
                    if g_exp > target_lev: w_comb *= (target_lev / g_exp)
                    w_comb = np.clip(w_comb, -0.30, 0.30)

                tgt = {v_cols[i]: float(w_comb[i]) for i in range(len(v_cols)) if abs(w_comb[i]) > 0.005}
                turnover = sync_positions(tgt, positions, c_rows, grp, disaster_stop_atr=3.5)
                rebal_fee = turnover * (0.92 * -0.00015 + 0.08 * 0.00045) * capital
                turnovers.append(turnover)

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

    return {
        "Config": cfg_name, "CAGR": f"{cagr:>+6.1f}%", "Sharpe": f"{sharpe:.2f}",
        "Sortino": f"{sortino:.2f}", "Max DD": f"{mdd:>5.1f}%", "Calmar": f"{abs(cagr/mdd):.2f}",
        "PF": f"{pf:.2f}", "Ending $": f"${capital:,.0f}"
    }

def run_matrix():
    print("=" * 95)
    print("      REVISED CONVEX ABLATION STUDY: CORRECTED LEVERAGE & SOCP ENGINE      ")
    print("=" * 95)
    df, unique_ts, grp_to_ts = load_and_prepare_panel()
    p12, p48, p168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    ablations = [
        ("A0. Baseline Institutional v3 (1.75x, 35% S0 Short, HRP)", False, False, False),
        ("A1. + Dynamic Asymmetric Beta (0.0 to +2.00 in HRP)", True, False, False),
        ("A2. + Calibrated Risk-Scaled Leverage (0.5x to 3.5x)", True, True, False),
        ("A3. + Unified Clarabel SOCP Solver (Beta + Carry + Cov)", True, True, True),
    ]

    results = []
    for label, d_beta, d_lev, socp in ablations:
        res = evaluate_ablation_trial(
            df, p12, p48, p168, hmm_data, label,
            enable_dyn_beta=d_beta, enable_dyn_lev=d_lev, enable_socp=socp
        )
        results.append(res)
        print(f" • Completed: {label}")

    res_df = pd.DataFrame(results)
    print("\n" + "=" * 95)
    print("                         REVISED ABLATION EVALUATION MATRIX                          ")
    print("=" * 95)
    print(res_df.to_string(index=False))
    print("=" * 95 + "\n")

if __name__ == "__main__":
    run_matrix()

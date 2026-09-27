import sys
import warnings
from pathlib import Path
from itertools import product
import pandas as pd
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.backtest_models import OnlineMicrostructureHMM, Position
from src.backtest.backtest_matured_ir import compute_ensemble_alpha
from src.backtest.backtest_positions import evaluate_intrabar_stops, sync_positions
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.backtest.run_fast_institutional_matrix import precompute_rolling_predictions
from src.signals.funding_forecaster import forecast_hourly_funding

def evaluate_configuration(
    df: pl.DataFrame,
    preds_12: dict,
    preds_48: dict,
    preds_168: dict,
    hmm_training_data: dict,
    max_gross_lev: float,
    s0_short_mult: float,
    top_k: int,
    carry_lev: float,
    disaster_stop_atr: float = 3.5
) -> dict:
    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42

    capital, equity_curve, rets, positions = 1000.0, [1000.0], [], {}
    hmm, last_reb = OnlineMicrostructureHMM(), 0
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

        if grp in hmm_training_data:
            hmm.fit_from_training_observations(hmm_training_data[grp])

        # HMM Regime Step
        b_row = c_pan.filter(pl.col("symbol") == "BTC")
        b_vol = float(b_row.select("vol_yang_zhang").to_series()[0]) if len(b_row) > 0 else 0.03
        obs = np.array([b_vol, float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0]), 0.002])
        _, hmm_lev, dom_state = hmm.filter_step(obs)

        # Matured IC Updates
        for h_name, (t_col, delay) in target_map.items():
            mat_grp = grp - delay
            if mat_grp in preds_12:
                old_p = preds_12[mat_grp] if h_name == "12h" else (preds_48[mat_grp] if h_name == "48h" else preds_168[mat_grp])
                past_panel = df.filter(pl.col("group_id") == mat_grp).to_dicts()
                past_targets = {r["symbol"]: r.get(t_col) for r in past_panel if r.get(t_col) is not None}
                common = [s for s in old_p if s in past_targets]
                if len(common) >= 20:
                    from scipy.stats import spearmanr
                    ic, _ = spearmanr([old_p[s] for s in common], [past_targets[s] for s in common])
                    if not np.isnan(ic): matured_ic_hist[h_name].append(ic)

        p12_arr = np.array([preds_12[grp][s] for s in symbols])
        p48_arr = np.array([preds_48[grp][s] for s in symbols])
        p168_arr = np.array([preds_168[grp][s] for s in symbols])
        alpha_vec = compute_ensemble_alpha(p12_arr, p48_arr, p168_arr, matured_ic_hist, use_dynamic_ir=True)
        alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

        # Disaster Stop Check (3.5x ATR - Liquidation collar only)
        bar_pnl, stopped = evaluate_intrabar_stops(positions, c_rows, n_rows, capital, use_ratchet=False)
        for s in stopped: del positions[s]

        # 24H Periodic Allocation Rebalance
        rebal_fee = 0.0
        if (grp - last_reb) >= 6 or last_reb == 0:
            last_reb = grp
            hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
            piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
            v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]

            if len(v_cols) >= 15:
                shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
                m_yz = float(c_pan.select(pl.mean("vol_yang_zhang")).to_series()[0])
                
                # Scaled Dynamic Leverage
                vol_scaler = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))
                target_lev = float(np.clip(hmm_lev * (max_gross_lev / 1.50) * vol_scaler, 0.50, max_gross_lev))

                a_sub = np.array([alpha_dict[s] for s in v_cols])
                b_sub = np.array([c_rows[s]["beta_btc"] for s in v_cols])
                w_mom = compute_hrp_from_cov(shrunk_cov, a_sub, target_lev, top_k=top_k)

                # Asymmetric Regime Gating: State 0 (Bull) short multiplier
                if dom_state == 0:
                    w_mom[w_mom < 0] *= s0_short_mult

                if carry_lev > 0:
                    carry_y = np.array([forecast_hourly_funding(float(c_rows[s]["basis_spread"]), float(c_rows[s]["volume_zscore_72h"]), float(c_rows[s]["ret_4h"]), float(c_rows[s]["basis_spread"]))[1] for s in v_cols])
                    w_car = compute_null_space_carry(shrunk_cov, carry_y, a_sub, b_sub, target_carry_leverage=carry_lev)
                else:
                    w_car = np.zeros(len(v_cols))

                w_comb = w_mom + w_car
                g_exp = np.sum(np.abs(w_comb))
                if g_exp > max_gross_lev:
                    w_comb *= (max_gross_lev / g_exp)
                w_comb = np.clip(w_comb, -0.35, 0.35)

                tgt = {v_cols[i]: float(w_comb[i]) for i in range(len(v_cols)) if abs(w_comb[i]) > 0.005}
                turnover = sync_positions(tgt, positions, c_rows, grp)
                rebal_fee = turnover * (0.92 * -0.00015 + 0.08 * 0.00045) * capital

        d_pnl = bar_pnl - rebal_fee
        capital += d_pnl
        equity_curve.append(capital)
        rets.append(d_pnl / equity_curve[-2])

    r_arr = np.array(rets)
    days = (len(r_arr) * 4) / 24.0
    sharpe = float((np.mean(r_arr) / (np.std(r_arr) + 1e-8)) * np.sqrt(2190))
    cagr = float(((capital / 1000.0) ** (365.0 / days) - 1) * 100) if days > 0 else 0.0
    eq = np.array(equity_curve)
    mdd = float(np.min((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)) * 100)
    pf = float(abs(np.sum(r_arr[r_arr > 0])) / (abs(np.sum(r_arr[r_arr < 0])) + 1e-8))
    calmar = abs(cagr / mdd) if mdd != 0 else 0.0

    return {
        "Max Gross": f"{max_gross_lev:.1f}x",
        "Bull Shorts": f"{s0_short_mult*100:.0f}%",
        "Top-K": top_k,
        "Carry Lev": f"{carry_lev:.2f}x",
        "Ending $": f"${capital:,.0f}",
        "CAGR": f"{cagr:>+6.1f}%",
        "Sharpe": f"{sharpe:.2f}",
        "Max DD": f"{mdd:>5.1f}%",
        "Calmar": f"{calmar:.2f}",
        "Profit Factor": f"{pf:.2f}",
        "raw_cagr": cagr
    }

def run_grid():
    print("=" * 95)
    print("       ALPHA MAXIMIZATION GRID SEARCH (24 PARAMETER COMBINATIONS)        ")
    print("=" * 95)
    df, unique_ts, grp_to_ts = load_and_prepare_panel()
    preds_12, preds_48, preds_168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    leverage_options = [1.75, 2.50, 3.25]
    bull_short_options = [0.0, 0.20]       # 0% = Pure Long-Only in Bull, 20% = Light Hedges
    top_k_options = [3, 5]                 # K=3 (Decile Conviction) vs K=5 (Broader Basket)
    carry_options = [0.40, 0.65]

    print("\n[GRID] Sweeping parameter surface...")
    results = []
    for lev, s0_s, k, carry in product(leverage_options, bull_short_options, top_k_options, carry_options):
        res = evaluate_configuration(df, preds_12, preds_48, preds_168, hmm_data, lev, s0_s, k, carry)
        results.append(res)

    res_df = pd.DataFrame(results).sort_values(by="raw_cagr", ascending=False).drop(columns=["raw_cagr"])
    print("\n" + res_df.to_string(index=False))
    print("=" * 95 + "\n")

if __name__ == "__main__":
    run_grid()

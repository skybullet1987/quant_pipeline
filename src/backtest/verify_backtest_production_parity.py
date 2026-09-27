import sys
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.backtest_models import OnlineMicrostructureHMM
from src.backtest.backtest_matured_ir import compute_ensemble_alpha
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.backtest.run_fast_institutional_matrix import precompute_rolling_predictions
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine
from src.signals.funding_forecaster import forecast_hourly_funding

def run_parity_test():
    print("=" * 90)
    print("       BACKTEST <-> PRODUCTION STRATEGY PARITY VERIFICATION HARNESS       ")
    print("=" * 90)

    df, unique_ts, grp_to_ts = load_and_prepare_panel()
    preds_12, preds_48, preds_168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42
    target_map = {"12h": ("target_12h_alpha", 3), "48h": ("target_48h_drift", 12), "168h": ("target_168h_trend", 42)}

    test_rebalance_grps = [g for g in range(start_eval_grp, total_grps - 1, 6)][:50]
    print(f"\n[AUDIT] Verifying numerical portfolio weight parity across {len(test_rebalance_grps)} rebalance epochs...")

    prod_engine = ProductionMultiScaleEngine(m12=None, m48=None, m168=None)
    matured_ic_hist = {"12h": [], "48h": [], "168h": []}
    hmm_sim = OnlineMicrostructureHMM()
    
    max_discrepancy = 0.0
    failed_epochs = 0

    for grp in range(start_eval_grp, total_grps - 1):
        c_pan = df.filter(pl.col("group_id") == grp)
        if c_pan.height == 0: continue
        symbols = c_pan.select("symbol").to_series().to_list()

        # Step backtest reference HMM
        if grp in hmm_data:
            hmm_sim.fit_from_training_observations(hmm_data[grp])
        b_row = c_pan.filter(pl.col("symbol") == "BTC")
        b_vol = float(b_row.select("vol_yang_zhang").to_series()[0]) if len(b_row) > 0 else 0.03
        obs = np.array([b_vol, float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0]), 0.002])
        _, hmm_lev, dom_state = hmm_sim.filter_step(obs)

        # Dynamic IC updates
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

        if grp in test_rebalance_grps:
            # 1. Backtest Reference Weights
            c_rows = {r["symbol"]: r for r in c_pan.iter_rows(named=True)}
            p12_arr = np.array([preds_12[grp][s] for s in symbols])
            p48_arr = np.array([preds_48[grp][s] for s in symbols])
            p168_arr = np.array([preds_168[grp][s] for s in symbols])
            alpha_vec = compute_ensemble_alpha(p12_arr, p48_arr, p168_arr, matured_ic_hist, use_dynamic_ir=True)
            alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

            hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
            piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
            v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]

            shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
            m_yz = float(c_pan.select(pl.mean("vol_yang_zhang")).to_series()[0])
            vol_scaler = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))

            target_lev = float(np.clip(hmm_lev * (1.75 / 1.50) * vol_scaler, 0.50, 1.75))
            a_sub = np.array([alpha_dict[s] for s in v_cols])
            b_sub = np.array([c_rows[s]["beta_btc"] for s in v_cols])

            w_mom = compute_hrp_from_cov(shrunk_cov, a_sub, target_lev, top_k=5)
            if dom_state == 0: w_mom[w_mom < 0] *= 0.35

            carry_y = np.array([forecast_hourly_funding(float(c_rows[s]["basis_spread"]), float(c_rows[s]["volume_zscore_72h"]), float(c_rows[s]["ret_4h"]), float(c_rows[s]["basis_spread"]))[1] for s in v_cols])
            w_car = compute_null_space_carry(shrunk_cov, carry_y, a_sub, b_sub, target_carry_leverage=0.40)

            w_comb = w_mom + w_car
            g_exp = np.sum(np.abs(w_comb))
            if g_exp > 1.75: w_comb *= (1.75 / g_exp)
            w_comb = np.clip(w_comb, -0.30, 0.30)
            backtest_weights = {v_cols[i]: float(w_comb[i]) for i in range(len(v_cols)) if abs(w_comb[i]) > 0.005}

            # 2. Production Engine Calculation
            prod_weights, diag = prod_engine.generate_target_portfolio(
                df=df,
                target_grp=grp,
                preds_12_cache=preds_12,
                preds_48_cache=preds_48,
                preds_168_cache=preds_168,
                matured_ic_hist=matured_ic_hist,
                max_bull_lev=1.75,
                s0_short_mult=0.35,
                carry_lev=0.40,
                top_k=5
            )

            # 3. Assert Exact Equality
            all_syms = set(list(backtest_weights.keys()) + list(prod_weights.keys()))
            epoch_max_err = 0.0
            for s in all_syms:
                w_bt = backtest_weights.get(s, 0.0)
                w_pr = prod_weights.get(s, 0.0)
                err = abs(w_bt - w_pr)
                epoch_max_err = max(epoch_max_err, err)
                max_discrepancy = max(max_discrepancy, err)

            if epoch_max_err > 1e-5:
                print(f" [FAIL] Discrepancy at Group {grp} ({grp_to_ts[grp]}): Max Error = {epoch_max_err:.8f}")
                failed_epochs += 1

    print("\n" + "=" * 90)
    print("                                PARITY AUDIT VERDICT                                  ")
    print("=" * 90)
    print(f" • Rebalance Epochs Tested : {len(test_rebalance_grps)}")
    print(f" • Maximum Absolute Error  : {max_discrepancy:.10f}")
    print(f" • Failed Epochs (>1e-5)   : {failed_epochs}")
    
    if failed_epochs == 0 and max_discrepancy < 1e-5:
        print("\n [PASSED] Strategy Parity Confirmed. Production engine exactly matches backtest.")
    else:
        print("\n [FAILED] Discrepancies detected. Do not deploy.")
    print("=" * 90 + "\n")

if __name__ == "__main__":
    run_parity_test()

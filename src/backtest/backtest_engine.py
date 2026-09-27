import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf
from catboost import CatBoost, Pool
from typing import Dict

from src.backtest.backtest_models import OnlineMicrostructureHMM, Position
from src.backtest.backtest_data import FEATURE_COLS
from src.backtest.backtest_matured_ir import process_matured_predictions, compute_ensemble_alpha
from src.backtest.backtest_positions import evaluate_intrabar_stops, sync_positions
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.signals.funding_forecaster import forecast_hourly_funding

def simulate_walkforward(
    df: pl.DataFrame,
    grp_to_ts: Dict[int, str],
    config_name: str,
    use_dynamic_ir: bool = True,
    use_ratchet: bool = True,
    use_hmm: bool = True,
    use_hrp: bool = True,
    use_carry: bool = True,
    retrain_step: int = 42,
    rebalance_holding_bars: int = 6,
    top_k: int = 5
) -> dict:
    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42
    capital, equity_curve, rets, positions = 1000.0, [1000.0], [], {}
    hmm, current_eval, last_reb = OnlineMicrostructureHMM(), start_eval_grp, 0
    pred_ledger = {"12h": {}, "48h": {}, "168h": {}}
    matured_ic_hist = {"12h": [], "48h": [], "168h": []}

    while current_eval < total_grps:
        eval_end = min(current_eval + retrain_step, total_grps)
        tr_df = df.filter((pl.col("group_id") >= max(0, current_eval - 42 - 1080)) & (pl.col("group_id") < current_eval - 42))
        te_df = df.filter((pl.col("group_id") >= current_eval) & (pl.col("group_id") < eval_end))

        if tr_df.height < 1000 or te_df.height == 0:
            current_eval = eval_end; continue

        # Train models & fit HMM on training window
        X_tr, grp_tr = tr_df.select(FEATURE_COLS).to_pandas(), tr_df.select("group_id").to_series().to_numpy()
        p = {"iterations": 140, "depth": 4, "learning_rate": 0.035, "l2_leaf_reg": 3.2, "loss_function": "YetiRank", "thread_count": -1, "verbose": False}
        m12 = CatBoost(p).fit(Pool(X_tr, tr_df.select("target_12h_alpha").to_series().to_numpy(), group_id=grp_tr))
        m48 = CatBoost(p).fit(Pool(X_tr, tr_df.select("target_48h_drift").to_series().to_numpy(), group_id=grp_tr))
        m168 = CatBoost(p).fit(Pool(X_tr, tr_df.select("target_168h_trend").to_series().to_numpy(), group_id=grp_tr))

        # Fit HMM empirically on training data
        btc_tr = tr_df.filter(pl.col("symbol") == "BTC").sort("group_id")
        if btc_tr.height >= 100:
            hmm_tr_obs = np.column_stack([btc_tr["vol_yang_zhang"].to_numpy(), btc_tr["volume_zscore_72h"].to_numpy(), btc_tr["basis_spread"].to_numpy()])
            hmm.fit_from_training_observations(hmm_tr_obs)

        for grp in range(current_eval, eval_end):
            c_pan = te_df.filter(pl.col("group_id") == grp)
            if c_pan.height == 0 or grp + 1 >= total_grps: continue
            n_pan = df.filter(pl.col("group_id") == grp + 1)
            c_rows = {r["symbol"]: r for r in c_pan.iter_rows(named=True)}
            n_rows = {r["symbol"]: r for r in n_pan.iter_rows(named=True)}
            symbols = list(c_rows.keys())

            # 1. HMM Update
            b_row = c_pan.filter(pl.col("symbol") == "BTC")
            b_vol = float(b_row.select("vol_yang_zhang").to_series()[0]) if len(b_row) > 0 else 0.03
            obs = np.array([b_vol, float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0]), float(c_pan.select(pl.col("basis_spread").std()).to_series()[0]) if not np.isnan(float(c_pan.select(pl.col("basis_spread").std()).to_series()[0])) else 0.002])
            _, hmm_lev, dom_state = hmm.filter_step(obs)

            # 2. Prediction & Matured Target Correlation
            X_c = c_pan.select(FEATURE_COLS).to_pandas()
            p12, p48, p168 = m12.predict(X_c), m48.predict(X_c), m168.predict(X_c)
            pred_ledger["12h"][grp] = {s: v for s, v in zip(symbols, p12)}
            pred_ledger["48h"][grp] = {s: v for s, v in zip(symbols, p48)}
            pred_ledger["168h"][grp] = {s: v for s, v in zip(symbols, p168)}
            process_matured_predictions(pred_ledger, matured_ic_hist, grp, c_pan, df)
            alpha_vec = compute_ensemble_alpha(p12, p48, p168, matured_ic_hist, use_dynamic_ir)
            alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

            # 3. Stops
            bar_pnl, stopped = evaluate_intrabar_stops(positions, c_rows, n_rows, capital, use_ratchet)
            for s in stopped: del positions[s]

            # 4. Periodic Rebalance
            rebal_fee = 0.0
            if (grp - last_reb) >= rebalance_holding_bars or last_reb == 0:
                last_reb = grp
                hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
                piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
                v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]

                if len(v_cols) >= 15:
                    a_sub = np.array([alpha_dict[s] for s in v_cols])
                    b_sub = np.array([c_rows[s]["beta_btc"] for s in v_cols])

                    if not use_hrp:
                        # Naive Benchmark 0 (Equal-Weight Top/Bottom 5)
                        ord_idx = np.argsort(-a_sub)
                        w_mom = np.zeros(len(v_cols))
                        w_mom[ord_idx[:top_k]] = 0.50 / top_k
                        w_mom[ord_idx[-top_k:]] = -0.50 / top_k
                        w_car = np.zeros(len(v_cols))
                    else:
                        shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
                        m_yz = float(c_pan.select(pl.mean("vol_yang_zhang")).to_series()[0])
                        t_lev = (hmm_lev * float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.50))) if use_hmm else 1.50
                        w_mom = compute_hrp_from_cov(shrunk_cov, a_sub, t_lev, top_k=top_k)
                        if use_hmm and dom_state == 0: w_mom[w_mom < 0] *= 0.35

                        if use_carry:
                            carry_y = np.array([forecast_hourly_funding(float(c_rows[s]["basis_spread"]), float(c_rows[s]["volume_zscore_72h"]), float(c_rows[s]["ret_4h"]), float(c_rows[s]["basis_spread"]))[1] for s in v_cols])
                            w_car = compute_null_space_carry(shrunk_cov, carry_y, a_sub, b_sub, target_carry_leverage=0.40)
                        else:
                            w_car = np.zeros(len(v_cols))

                    # P1 Multi-Objective Portfolio Constraints
                    w_comb = w_mom + w_car
                    g_exp = np.sum(np.abs(w_comb))
                    if g_exp > 1.75: w_comb *= (1.75 / g_exp)
                    w_comb = np.clip(w_comb, -0.25, 0.25)
                    
                    tgt = {v_cols[i]: float(w_comb[i]) for i in range(len(v_cols)) if abs(w_comb[i]) > 0.005}
                    turnover = sync_positions(tgt, positions, c_rows, grp)
                    rebal_fee = turnover * (0.92 * -0.00015 + 0.08 * 0.00045) * capital

            d_pnl = bar_pnl - rebal_fee
            capital += d_pnl
            equity_curve.append(capital)
            rets.append(d_pnl / equity_curve[-2])

        current_eval = eval_end

    r_arr = np.array(rets)
    days = (len(r_arr) * 4) / 24.0
    sharpe = float((np.mean(r_arr) / (np.std(r_arr) + 1e-8)) * np.sqrt(2190))
    cagr = float(((capital / 1000.0) ** (365.0 / days) - 1) * 100) if days > 0 else 0.0
    eq = np.array(equity_curve)
    mdd = float(np.min((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)) * 100)
    pf = float(abs(np.sum(r_arr[r_arr > 0])) / (abs(np.sum(r_arr[r_arr < 0])) + 1e-8))
    
    return {
        "config": config_name, "sharpe": sharpe, "cagr": cagr, "max_dd": mdd, "pf": pf,
        "win_rate": float((np.sum(r_arr > 0) / len(r_arr)) * 100), "end_cap": capital, "days": days
    }

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
from catboost import CatBoost, Pool
from typing import Dict, Tuple

from src.backtest.backtest_data import load_and_prepare_panel, FEATURE_COLS
from src.backtest.backtest_models import OnlineMicrostructureHMM, Position
from src.backtest.backtest_matured_ir import compute_ensemble_alpha
from src.backtest.backtest_positions import evaluate_intrabar_stops, sync_positions
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.signals.funding_forecaster import forecast_hourly_funding

def precompute_rolling_predictions(df: pl.DataFrame, retrain_step: int = 42) -> Tuple[dict, dict, dict, dict]:
    """Fits CatBoost models once across rolling windows and caches all OOS predictions."""
    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42
    rolling_train_bars = 1080
    max_target_horizon = 42

    preds_12, preds_48, preds_168 = {}, {}, {}
    hmm_training_data = {}
    current_eval = start_eval_grp

    print(f"\n[PASS 1] Precomputing Rolling OOS Predictions ({start_eval_grp} -> {total_grps})...")
    block_num = 1
    total_blocks = (total_grps - start_eval_grp) // retrain_step + 1

    while current_eval < total_grps:
        eval_end = min(current_eval + retrain_step, total_grps)
        tr_df = df.filter((pl.col("group_id") >= max(0, current_eval - max_target_horizon - rolling_train_bars)) & (pl.col("group_id") < current_eval - max_target_horizon))
        te_df = df.filter((pl.col("group_id") >= current_eval) & (pl.col("group_id") < eval_end))

        if tr_df.height < 1000 or te_df.height == 0:
            current_eval = eval_end
            continue

        print(f" • Training Block {block_num}/{total_blocks} (Groups {current_eval} -> {eval_end})...")
        X_tr, grp_tr = tr_df.select(FEATURE_COLS).to_pandas(), tr_df.select("group_id").to_series().to_numpy()
        p = {"iterations": 130, "depth": 4, "learning_rate": 0.035, "l2_leaf_reg": 3.2, "loss_function": "YetiRank", "thread_count": -1, "verbose": False}

        m12 = CatBoost(p).fit(Pool(X_tr, tr_df.select("target_12h_alpha").to_series().to_numpy(), group_id=grp_tr))
        m48 = CatBoost(p).fit(Pool(X_tr, tr_df.select("target_48h_drift").to_series().to_numpy(), group_id=grp_tr))
        m168 = CatBoost(p).fit(Pool(X_tr, tr_df.select("target_168h_trend").to_series().to_numpy(), group_id=grp_tr))

        btc_tr = tr_df.filter(pl.col("symbol") == "BTC").sort("group_id")
        if btc_tr.height >= 100:
            hmm_training_data[current_eval] = np.column_stack([
                btc_tr["vol_yang_zhang"].to_numpy(),
                btc_tr["volume_zscore_72h"].to_numpy(),
                btc_tr["basis_spread"].to_numpy()
            ])

        for grp in range(current_eval, eval_end):
            c_pan = te_df.filter(pl.col("group_id") == grp)
            if c_pan.height == 0: continue
            syms = c_pan.select("symbol").to_series().to_list()
            X_c = c_pan.select(FEATURE_COLS).to_pandas()
            preds_12[grp] = {s: float(v) for s, v in zip(syms, m12.predict(X_c))}
            preds_48[grp] = {s: float(v) for s, v in zip(syms, m48.predict(X_c))}
            preds_168[grp] = {s: float(v) for s, v in zip(syms, m168.predict(X_c))}

        current_eval = eval_end
        block_num += 1

    return preds_12, preds_48, preds_168, hmm_training_data

def evaluate_fast_backtest(
    df: pl.DataFrame,
    grp_to_ts: Dict[int, str],
    preds_12: dict,
    preds_48: dict,
    preds_168: dict,
    hmm_training_data: dict,
    config_name: str,
    use_dynamic_ir: bool = True,
    use_ratchet: bool = True,
    use_hmm: bool = True,
    use_hrp: bool = True,
    use_carry: bool = True,
    rebalance_holding_bars: int = 6,
    top_k: int = 5
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

        # Fit HMM at block boundary
        if grp in hmm_training_data:
            hmm.fit_from_training_observations(hmm_training_data[grp])

        # 1. HMM Update
        b_row = c_pan.filter(pl.col("symbol") == "BTC")
        b_vol = float(b_row.select("vol_yang_zhang").to_series()[0]) if len(b_row) > 0 else 0.03
        obs = np.array([b_vol, float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0]), 0.002])
        _, hmm_lev, dom_state = hmm.filter_step(obs)

        # 2. Process Matured ICs & Dynamic Alpha
        p12_dict = preds_12[grp]
        p48_dict = preds_48[grp]
        p168_dict = preds_168[grp]

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

        p12_arr = np.array([p12_dict[s] for s in symbols])
        p48_arr = np.array([p48_dict[s] for s in symbols])
        p168_arr = np.array([p168_dict[s] for s in symbols])
        alpha_vec = compute_ensemble_alpha(p12_arr, p48_arr, p168_arr, matured_ic_hist, use_dynamic_ir)
        alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

        # 3. Stops
        bar_pnl, stopped = evaluate_intrabar_stops(positions, c_rows, n_rows, capital, use_ratchet)
        for s in stopped: del positions[s]

        # 4. Rebalance & Allocation
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

def run_matrix():
    print("=" * 90)
    print("      FAST INSTITUTIONAL WALK-FORWARD MATRIX (CACHED MODEL INFERENCE)      ")
    print("=" * 90)
    df, unique_ts, grp_to_ts = load_and_prepare_panel()

    p12, p48, p168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    configs = [
        ("B0. Benchmark 0 (Naive EW Top-5, 1.0x Gross, No HRP, No Carry, No HMM)", False, False, False, False, False),
        ("B1. + Ledoit-Wolf HRP Allocation (1.5x Gross)", False, False, False, True, False),
        ("B2. + Null-Space Carry Overlay", False, False, False, True, True),
        ("B3. + Matured Dynamic IC-IR Stability Horizon Weighting", True, False, False, True, True),
        ("B4. + Empirically Fitted 3-State HMM Regime Governor", True, False, True, True, True),
        ("B5. + Intrabar Dynamic Ratchet & Chandelier Stops (Full Production)", True, True, True, True, True)
    ]

    print("\n[PASS 2] Running Instant Progressive Portfolio Matrix (B0 -> B5)...")
    for label, use_ir, use_ratchet, use_hmm, use_hrp, use_carry in configs:
        res = evaluate_fast_backtest(
            df, grp_to_ts, p12, p48, p168, hmm_data, config_name=label,
            use_dynamic_ir=use_ir, use_ratchet=use_ratchet, use_hmm=use_hmm,
            use_hrp=use_hrp, use_carry=use_carry, rebalance_holding_bars=6, top_k=5
        )
        print(f"\n--> {res['config']}")
        print(f"    • Out-of-Sample Sharpe : {res['sharpe']:.2f} | Profit Factor: {res['pf']:.2f}")
        print(f"    • Annualized CAGR      : {res['cagr']:,.1f}% (Ending Capital: ${res['end_cap']:,.2f})")
        print(f"    • Maximum Drawdown     : {res['max_dd']:.2f}% | 4H Win Rate: {res['win_rate']:.1f}%")

    print("\n" + "=" * 90)

if __name__ == "__main__":
    run_matrix()

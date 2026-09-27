import sys
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
from scipy.stats import spearmanr, norm
from sklearn.covariance import LedoitWolf
from catboost import CatBoost, Pool

from src.optimization.hrp_optimizer import optimize_hrp_weights
from src.signals.funding_forecaster import forecast_hourly_funding, solve_alpha_orthogonal_carry

LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"

FEATURE_COLS = [
    "ret_4h", "ret_24h", "ret_72h", "ret_168h",
    "volume_zscore_72h", "basis_spread", "vol_yang_zhang", "beta_btc"
]

def compute_deflated_sharpe(sharpe: float, rets: np.ndarray, n_trials: int = 50) -> float:
    n = len(rets)
    if n < 30 or np.std(rets) == 0: return 0.50
    skew = float(np.mean((rets - np.mean(rets))**3) / (np.std(rets)**3 + 1e-8))
    kurt = float(np.mean((rets - np.mean(rets))**4) / (np.std(rets)**4 + 1e-8))
    em_c = 0.5772156649
    e_max = (1 - em_c) * norm.ppf(1 - 1/n_trials) + em_c * norm.ppf(1 - 1/(n_trials * np.e))
    var_sr = (1 + 0.5 * sharpe**2 - skew * sharpe + ((kurt - 3) / 4) * sharpe**2) / (n - 1)
    z = (sharpe - e_max) / np.sqrt(max(var_sr, 1e-8))
    return float(norm.cdf(z))

def load_and_prepare_panel():
    df = pl.read_parquet(LAKE_FILE)
    
    # Corrected: All forward targets must represent POSITIVE forward residual return
    df = df.with_columns([
        (pl.col("close").shift(-3).over("symbol") / pl.col("close")).log().alias("fwd_ret_12h"),
        (pl.col("close").shift(-12).over("symbol") / pl.col("close")).log().alias("fwd_ret_48h"),
        (pl.col("close").shift(-42).over("symbol") / pl.col("close")).log().alias("fwd_ret_168h"),
    ])
    btc_targets = df.filter(pl.col("symbol") == "BTC").select([
        "timestamp_ms",
        pl.col("fwd_ret_12h").alias("btc_fwd_12h"),
        pl.col("fwd_ret_48h").alias("btc_fwd_48h"),
        pl.col("fwd_ret_168h").alias("btc_fwd_168h"),
    ])
    df = df.join(btc_targets, on="timestamp_ms", how="left").with_columns([
        ((pl.col("fwd_ret_12h") - (pl.col("beta_btc") * pl.col("btc_fwd_12h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_12h_alpha"),
        ((pl.col("fwd_ret_48h") - (pl.col("beta_btc") * pl.col("btc_fwd_48h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_48h_drift"),
        ((pl.col("fwd_ret_168h") - (pl.col("beta_btc") * pl.col("btc_fwd_168h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_168h_trend")
    ]).drop_nulls(subset=FEATURE_COLS + ["target_12h_alpha", "target_48h_drift", "target_168h_trend"])

    unique_ts = sorted(df.select("timestamp_ms").to_series().unique().to_list())
    ts_to_grp = {ts: idx for idx, ts in enumerate(unique_ts)}
    df = df.with_columns(pl.col("timestamp_ms").replace(ts_to_grp).alias("group_id")).sort(["group_id", "symbol"])
    return df, unique_ts

def run_simulation(df: pl.DataFrame, use_dynamic_ir: bool, use_ratchet: bool, retrain_step: int = 42):
    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42
    embargo = 42
    rolling_train_bars = 1080

    capital = 1000.0
    equity_curve = [capital]
    returns_list = []
    prev_weights = {}
    
    # Position tracking for ratchet exits: {symbol: {"entry_px", "peak_px", "trough_px", "stage", "atr"}}
    pos_tracker = {}
    ir_history = {"m12": [], "m48": [], "m168": []}
    current_eval = start_eval_grp

    while current_eval < total_grps:
        eval_end = min(current_eval + retrain_step, total_grps)
        train_end = current_eval - embargo
        train_start = max(0, train_end - rolling_train_bars)

        train_df = df.filter((pl.col("group_id") >= train_start) & (pl.col("group_id") < train_end))
        test_df = df.filter((pl.col("group_id") >= current_eval) & (pl.col("group_id") < eval_end))

        if train_df.height < 1000 or test_df.height == 0:
            current_eval = eval_end
            continue

        X_tr = train_df.select(FEATURE_COLS).to_pandas()
        grp_tr = train_df.select("group_id").to_series().to_numpy()
        p = {"iterations": 120, "depth": 4, "learning_rate": 0.04, "l2_leaf_reg": 3.0, "loss_function": "YetiRank", "thread_count": -1, "verbose": False}

        m12 = CatBoost(p).fit(Pool(X_tr, train_df.select("target_12h_alpha").to_series().to_numpy(), group_id=grp_tr))
        m48 = CatBoost(p).fit(Pool(X_tr, train_df.select("target_48h_drift").to_series().to_numpy(), group_id=grp_tr))
        m168 = CatBoost(p).fit(Pool(X_tr, train_df.select("target_168h_trend").to_series().to_numpy(), group_id=grp_tr))

        for grp in range(current_eval, eval_end):
            cur_panel = test_df.filter(pl.col("group_id") == grp)
            if cur_panel.height == 0 or grp + 1 >= total_grps: continue
            next_panel = df.filter(pl.col("group_id") == grp + 1)

            # 1. Model Predictions & Dynamic IR Weighting
            X_cur = cur_panel.select(FEATURE_COLS).to_pandas()
            p12 = m12.predict(X_cur)
            p48 = m48.predict(X_cur)
            p168 = m168.predict(X_cur)

            if cur_panel.height >= 30:
                c12, _ = spearmanr(p12, cur_panel["target_12h_alpha"])
                c48, _ = spearmanr(p48, cur_panel["target_48h_drift"])
                c168, _ = spearmanr(p168, cur_panel["target_168h_trend"])
                if not np.isnan(c12): ir_history["m12"].append(c12)
                if not np.isnan(c48): ir_history["m48"].append(c48)
                if not np.isnan(c168): ir_history["m168"].append(c168)

            if use_dynamic_ir and len(ir_history["m12"]) >= 15:
                w12 = max(0.05, float(np.mean(ir_history["m12"][-30:]) / (np.std(ir_history["m12"][-30:]) + 1e-6)))
                w48 = max(0.05, float(np.mean(ir_history["m48"][-30:]) / (np.std(ir_history["m48"][-30:]) + 1e-6)))
                w168 = max(0.05, float(np.mean(ir_history["m168"][-30:]) / (np.std(ir_history["m168"][-30:]) + 1e-6)))
                raw_w = np.array([w12**2, w48**2, w168**2]) / (w12**2 + w48**2 + w168**2 + 1e-8)
                clamped_w = np.clip(raw_w, 0.10, 0.60)
                norm_w = clamped_w / np.sum(clamped_w)
                alpha_score = (norm_w[0] * p12) + (norm_w[1] * p48) + (norm_w[2] * p168)
            else:
                alpha_score = (0.30 * p12) + (0.45 * p48) + (0.25 * p168)

            cur_panel = cur_panel.with_columns(pl.Series("pred_alpha", alpha_score))
            symbols = cur_panel.select("symbol").to_series().to_list()

            # 2. Covariance Matrix & Portfolio Optimization
            hist_sub = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
            pivoted_rets = hist_sub.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
            valid_cols = [c for c in symbols if c in pivoted_rets.columns and pivoted_rets[c].null_count() <= 10]
            ret_mat = pivoted_rets.select(valid_cols).fill_null(strategy="backward").fill_null(strategy="forward").fill_null(0.0).to_numpy()

            if len(valid_cols) < 10 or ret_mat.shape[0] < 30: continue

            market_yz = float(cur_panel.select(pl.mean("vol_yang_zhang")).to_series()[0])
            dyn_leverage = float(np.clip(1.50 * (0.025 / (market_yz + 1e-8)), 0.60, 1.75))

            alpha_dict = {row["symbol"]: float(row["pred_alpha"]) for row in cur_panel.iter_rows(named=True) if row["symbol"] in valid_cols}
            betas = {row["symbol"]: float(row["beta_btc"]) for row in cur_panel.iter_rows(named=True) if row["symbol"] in valid_cols}

            mom_weights = optimize_hrp_weights(valid_cols, alpha_dict, ret_mat, dyn_leverage, top_k=8)

            carry_yields = {}
            for row in cur_panel.iter_rows(named=True):
                sym = row["symbol"]
                if sym in valid_cols:
                    _, y_ann = forecast_hourly_funding(float(row["basis_spread"]), float(row["volume_zscore_72h"]), float(row["ret_4h"]), float(row["basis_spread"]))
                    carry_yields[sym] = y_ann

            carry_weights = solve_alpha_orthogonal_carry(valid_cols, carry_yields, alpha_dict, betas, ret_mat, target_carry_leverage=0.50)
            target_weights = {s: mom_weights.get(s, 0.0) + carry_weights.get(s, 0.0) for s in set(list(mom_weights.keys()) + list(carry_weights.keys()))}

            # 3. Turnover & Normal Execution Friction
            all_eval = set(list(target_weights.keys()) + list(prev_weights.keys()))
            turnover = sum(abs(target_weights.get(s, 0.0) - prev_weights.get(s, 0.0)) for s in all_eval)
            net_fee = 0.92 * (-0.00015) + 0.08 * (0.00045)  # 92% maker rebate (-1.5 bps), 8% taker (+4.5 bps)
            friction_cost = turnover * net_fee * capital

            # 4. Realistic Bar-by-Bar Ratchet Stop Evaluation
            next_rows = {row["symbol"]: row for row in next_panel.iter_rows(named=True)}
            period_pnl = 0.0

            # Update Tracker
            for s, w in target_weights.items():
                if abs(w) > 0.001 and s not in pos_tracker:
                    match_row = cur_panel.filter(pl.col("symbol") == s).to_dicts()[0]
                    px = match_row["close"]
                    atr = match_row["atr_14"]
                    pos_tracker[s] = {"entry_px": px, "peak_px": px, "trough_px": px, "stage": "INITIAL", "atr": atr}

            # Clean up closed positions
            pos_tracker = {k: v for k, v in pos_tracker.items() if k in target_weights and abs(target_weights[k]) > 0.001}

            for s, w in target_weights.items():
                if abs(w) <= 0.001 or s not in next_rows: continue
                r_next = next_rows[s]
                p_cur = cur_panel.filter(pl.col("symbol") == s).select("close").to_series()[0]
                p_next_close = r_next["close"]
                p_next_high = r_next["high"]
                p_next_low = r_next["low"]
                
                is_long = (w > 0)
                trk = pos_tracker.get(s, {"entry_px": p_cur, "peak_px": p_cur, "trough_px": p_cur, "stage": "INITIAL", "atr": p_cur * 0.035})
                trk["peak_px"] = max(trk["peak_px"], p_next_high)
                trk["trough_px"] = min(trk["trough_px"], p_next_low)
                atr = trk["atr"]
                entry_px = trk["entry_px"]

                # Calculate Active Stop Level
                if use_ratchet:
                    mfe = (trk["peak_px"] - entry_px) / (atr + 1e-8) if is_long else (entry_px - trk["trough_px"]) / (atr + 1e-8)
                    if mfe >= 2.0:
                        active_sl = trk["peak_px"] - (2.0 * atr) if is_long else trk["trough_px"] + (2.0 * atr)
                        trk["stage"] = "CHANDELIER"
                    elif mfe >= 1.5:
                        active_sl = entry_px + (0.10 * atr) if is_long else entry_px - (0.10 * atr)
                        trk["stage"] = "BREAKEVEN"
                    else:
                        active_sl = entry_px - (1.5 * atr) if is_long else entry_px + (1.5 * atr)
                else:
                    active_sl = entry_px - (1.5 * atr) if is_long else entry_px + (1.5 * atr)

                # Intrabar Stop Breach Check for current bar
                stopped = False
                if is_long and p_next_low <= active_sl:
                    exit_px = min(p_cur, active_sl)
                    bar_ret = (exit_px - p_cur) / p_cur
                    stopped = True
                elif not is_long and p_next_high >= active_sl:
                    exit_px = max(p_cur, active_sl)
                    bar_ret = (p_cur - exit_px) / p_cur
                    stopped = True
                else:
                    bar_ret = (p_next_close - p_cur) / p_cur if is_long else (p_cur - p_next_close) / p_cur

                leg_pnl = capital * abs(w) * bar_ret
                if stopped:
                    # Deduct taker fee + slippage on stop execution
                    leg_pnl -= capital * abs(w) * 0.00195
                    if s in pos_tracker: del pos_tracker[s]

                period_pnl += leg_pnl

            total_dollar_pnl = period_pnl - friction_cost
            capital += total_dollar_pnl
            equity_curve.append(capital)
            returns_list.append(total_dollar_pnl / equity_curve[-2])
            prev_weights = target_weights

        current_eval = eval_end

    rets = np.array(returns_list)
    total_days = (len(rets) * 4) / 24.0
    periods_yr = 6 * 365
    sharpe = float((np.mean(rets) / (np.std(rets) + 1e-8)) * np.sqrt(periods_yr))
    cagr = float(((capital / 1000.0) ** (365.0 / total_days) - 1) * 100) if total_days > 0 else 0.0
    eq_arr = np.array(equity_curve)
    peaks = np.maximum.accumulate(eq_arr)
    max_dd = float(np.min((eq_arr - peaks) / peaks) * 100)
    pf = float(abs(np.sum(rets[rets > 0])) / (abs(np.sum(rets[rets < 0])) + 1e-8))
    dsr = compute_deflated_sharpe(sharpe, rets)
    return {"sharpe": sharpe, "cagr": cagr, "max_dd": max_dd, "pf": pf, "dsr": dsr, "end_cap": capital}

def run_experiment_matrix():
    print("=" * 85)
    print("       AUTHENTIC WALK-FORWARD ABLATION MATRIX (CORRECTED TARGETS)        ")
    print("=" * 85)
    df, unique_ts = load_and_prepare_panel()

    configs = [
        ("1. Static 30/45/25 + No Ratchet (Baseline Refined)", False, False),
        ("2. Dynamic IR Clamped [0.10, 0.60] + No Ratchet", True, False),
        ("3. Dynamic IR Clamped + Full Ratchet (Breakeven + Chandelier)", True, True)
    ]

    for label, use_ir, use_ratchet in configs:
        res = run_simulation(df, use_dynamic_ir=use_ir, use_ratchet=use_ratchet, retrain_step=42)
        print(f"\n--> {label}")
        print(f"    • Out-of-Sample Sharpe : {res['sharpe']:.2f} (DSR: {res['dsr']*100:.1f}%)")
        print(f"    • Annualized CAGR      : {res['cagr']:,.1f}% (Ending Capital: ${res['end_cap']:,.2f})")
        print(f"    • Max Drawdown (MDD)   : {res['max_dd']:.2f}%")
        print(f"    • Profit Factor        : {res['pf']:.2f}")

    print("\n" + "=" * 85)

if __name__ == "__main__":
    run_experiment_matrix()

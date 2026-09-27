#!/usr/bin/env python3
"""
Optuna Bayesian Hyperparameter Optimization for High-Octane Policy
Optimizes: Entry thresholds, Kelly fractions, Leverage caps, and Margin limits.
Objective: Maximize Calmar Ratio subject to Max DD <= 25%.
"""

import os
import json
import joblib
import optuna
import requests
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
STARTING_CAPITAL = 1000.0
MAX_POSITIONS = 5
MAX_TRADES_PER_CYCLE = 2
FEE_SLIPPAGE_BPS = 15.0
HARD_LIQUIDITY_CAP_USD = 150000.0
LOOKBACK_DAYS = 90
N_TRIALS = 50

def get_active_model_dir() -> str:
    manifest_path = "models/manifest.json"
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
                active_ver = data.get("active_version", "v2026_08_01")
                release_dir = os.path.join("models", "releases", active_ver)
                if os.path.exists(release_dir):
                    return release_dir
        except Exception:
            pass
    return "production_models" if os.path.exists("production_models") else "."

PROD_MODELS_DIR = get_active_model_dir()

def get_hyperliquid_max_leverage() -> dict:
    try:
        resp = requests.post("https://api.hyperliquid.xyz/info", json={"type": "meta"}, timeout=5)
        return {a["name"]: a["maxLeverage"] for a in resp.json().get("universe", [])}
    except Exception:
        return {}

def load_scored_matrix():
    client = bigquery.Client(project=PROJECT_ID)
    print(f"\n[1/3] Ingesting {LOOKBACK_DAYS}-day matrix from BigQuery...")

    query = f"""
        WITH max_time AS (
            SELECT MAX(signal_time) AS max_ts 
            FROM `{PROJECT_ID}.market_data.fct_exact_path_resolution`
        )
        SELECT 
            f.*, 
            p.exit_time, p.exit_reason, p.exact_gross_return, p.minutes_in_trade,
            p.target_long, p.target_short,
            COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h,
            COALESCE(t.tfm_ret_72h, 0.0) AS tfm_ret_72h,
            COALESCE(t.tfm_slope, 0.0) AS tfm_slope,
            COALESCE(t.tfm_uncertainty, 0.0) AS tfm_uncertainty,
            COALESCE(t.tfm_residual_24h, 0.0) AS tfm_residual_24h,
            COALESCE(t.tfm_conviction_delta, 0.0) AS tfm_conviction_delta,
            COALESCE(l.total_liq_usd, 0) AS total_liq_usd,
            COALESCE(l.liq_imbalance_ratio, 0) AS liq_imbalance_ratio,
            COALESCE(l.long_liq_accel, 0) AS long_liq_accel,
            COALESCE(l.short_liq_accel, 0) AS short_liq_accel,
            COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.ticker = p.ticker AND f.timestamp = p.signal_time
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        CROSS JOIN max_time
        WHERE f.timestamp >= TIMESTAMP_SUB(max_time.max_ts, INTERVAL {LOOKBACK_DAYS} DAY)
          AND p.exit_reason != 'DATA_ERROR'
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["exit_time"] = pd.to_datetime(df["exit_time"])

    # Score HMM
    hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
    hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")

    for c in hmm_feats:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    scaled_x = hmm_scaler.transform(df[hmm_feats])
    probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    df["p_chop"] = probs[:, 0]
    df["regime"] = probs.argmax(axis=1).astype(str)

    # Score CatBoost
    cb_long = CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_1_long_expert.cbm")
    cb_short = CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_2_short_expert.cbm")
    all_cat_cols = joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else []
    cat_set = set(all_cat_cols)

    feats_l = cb_long.feature_names_
    feats_s = cb_short.feature_names_

    for c in set(feats_l + feats_s):
        if c not in df.columns:
            df[c] = "missing" if c in cat_set else 0.0
        elif c in cat_set:
            df[c] = df[c].astype(str).fillna("missing")
        else:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    pool_l = Pool(df[feats_l], cat_features=[c for c in feats_l if c in cat_set])
    pool_s = Pool(df[feats_s], cat_features=[c for c in feats_s if c in cat_set])

    cal_l = joblib.load(f"{PROD_MODELS_DIR}/meta_calibrator_long.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/meta_calibrator_long.pkl") else None
    cal_s = joblib.load(f"{PROD_MODELS_DIR}/meta_calibrator_short.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/meta_calibrator_short.pkl") else None

    raw_pl = cb_long.predict_proba(pool_l)[:, 1]
    raw_ps = cb_short.predict_proba(pool_s)[:, 1]

    df["p_long"] = cal_l.predict(raw_pl) if cal_l and hasattr(cal_l, "predict") else raw_pl
    df["p_short"] = cal_s.predict(raw_ps) if cal_s and hasattr(cal_s, "predict") else raw_ps

    return df

# ============================================================================
# 2. VECTORIZED SIMULATOR FUNCTION
# ============================================================================
def simulate_policy(df, params, hl_max_lev_map):
    capital = STARTING_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    open_positions = []
    trade_log = []

    fee_cut = FEE_SLIPPAGE_BPS / 10000.0
    timestamps = sorted(df["timestamp"].unique())

    for current_ts in timestamps:
        still_open = []
        for pos in open_positions:
            if current_ts >= pos["exit_time"]:
                capital += pos["margin"] + pos["pnl"]
                if capital > peak_capital:
                    peak_capital = capital
                trade_log.append(pos)
            else:
                still_open.append(pos)
        open_positions = still_open

        dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

        if capital <= 10.0:
            return 0.0, 1.0, len(trade_log)

        dd_mult = 0.25 if dd >= 0.30 else (0.50 if dd >= 0.15 else 1.0)

        bar_candidates = df[df["timestamp"] == current_ts]
        active_coins = {p["coin"] for p in open_positions}
        available_slots = MAX_POSITIONS - len(open_positions)

        if available_slots <= 0:
            continue

        eligible = []
        for _, row in bar_candidates.iterrows():
            coin = str(row["ticker"]).replace("USDT", "").replace("USD", "").upper()
            if coin in active_coins:
                continue

            pl, ps, pc, reg = float(row["p_long"]), float(row["p_short"]), float(row["p_chop"]), str(row["regime"])
            px, atr = float(row["close"]), float(row["atr_20"])
            if px <= 0 or atr <= 0 or pc >= 0.50 or reg == "0":
                continue

            l_pass = (pl >= params["entry_threshold_long"] and reg != "2")
            s_pass = (ps >= params["entry_threshold_short"] and reg != "1")

            if not l_pass and not s_pass:
                continue

            r_dist = (1.50 * atr) / px
            net_win = r_dist - 0.0014
            net_loss = r_dist + 0.0020

            ev_l = (pl * net_win) - ((1.0 - pl) * net_loss)
            ev_s = (ps * net_win) - ((1.0 - ps) * net_loss)

            is_buy = l_pass and (not s_pass or pl >= ps)
            side, p_win, ev_val = ("BUY", pl, ev_l) if is_buy else ("SELL", ps, ev_s)
            k_frac = params["kelly_frac_long"] if is_buy else params["kelly_frac_short"]
            base_lev = params["leverage_long"] if is_buy else params["leverage_short"]

            if ev_val > 0:
                eligible.append({
                    "coin": coin, "is_buy": is_buy, "side": side, "ev": ev_val,
                    "p_win": p_win, "k_frac": k_frac, "base_lev": base_lev,
                    "net_win": net_win, "net_loss": net_loss,
                    "target_long": row["target_long"], "target_short": row["target_short"],
                    "exit_time": row["exit_time"]
                })

        ranked = sorted(eligible, key=lambda x: x["ev"], reverse=True)
        margin_used = sum(p["margin"] for p in open_positions)
        available_margin = max(0.0, (capital * params["max_margin_utilization"]) - margin_used)
        trades_this_cycle = 0

        for cand in ranked:
            if trades_this_cycle >= min(MAX_TRADES_PER_CYCLE, available_slots):
                break

            coin = cand["coin"]
            p_win = cand["p_win"]
            k_frac = cand["k_frac"]
            is_buy = cand["is_buy"]

            dynamic_payoff = cand["net_win"] / cand["net_loss"]
            kelly_f = p_win - ((1.0 - p_win) / dynamic_payoff)
            coin_max_lev = float(hl_max_lev_map.get(coin, cand["base_lev"]))
            applied_lev = min(coin_max_lev, cand["base_lev"])

            trade_notional_pct = min(kelly_f * k_frac * applied_lev * dd_mult, 2.0)
            ideal_notional = capital * trade_notional_pct

            max_notional = available_margin * applied_lev
            final_notional = min(ideal_notional, max_notional, HARD_LIQUIDITY_CAP_USD)
            req_margin = final_notional / applied_lev

            if req_margin > available_margin or final_notional < 10.0:
                continue

            hit_target = (cand["target_long"] == 1) if is_buy else (cand["target_short"] == 1)
            pnl = (final_notional * cand["net_win"]) if hit_target else (-final_notional * cand["net_loss"])

            capital -= req_margin
            available_margin -= req_margin
            trades_this_cycle += 1

            open_positions.append({
                "coin": coin, "margin": req_margin, "pnl": pnl,
                "exit_time": cand["exit_time"]
            })
            active_coins.add(coin)

    for pos in open_positions:
        capital += pos["margin"] + pos["pnl"]
        trade_log.append(pos)

    return capital, max_dd, len(trade_log)

# ============================================================================
# 3. OPTUNA BAYESIAN OBJECTIVE & RUNNER
# ============================================================================
def main():
    df_scored = load_scored_matrix()
    hl_max_lev_map = get_hyperliquid_max_leverage()

    # 70% In-Sample Train / 30% Out-of-Sample Holdout with 72h Embargo
    timestamps = np.sort(df_scored["timestamp"].unique())
    split_idx = int(len(timestamps) * 0.70)
    train_end = timestamps[split_idx]
    test_start = train_end + pd.Timedelta(hours=72)

    df_train = df_scored[df_scored["timestamp"] <= train_end].copy().reset_index(drop=True)
    df_holdout = df_scored[df_scored["timestamp"] >= test_start].copy().reset_index(drop=True)

    print(f"\n[2/3] Partitioning: In-Sample ({len(df_train):,} bars) | 72h Embargo | Frozen OOS Holdout ({len(df_holdout):,} bars)")
    print(f"Starting {N_TRIALS} Bayesian Optimization Trials...")

    def objective(trial):
        params = {
            "entry_threshold_long": trial.suggest_float("entry_threshold_long", 0.54, 0.64, step=0.01),
            "entry_threshold_short": trial.suggest_float("entry_threshold_short", 0.50, 0.60, step=0.01),
            "kelly_frac_long": trial.suggest_float("kelly_frac_long", 0.10, 0.45, step=0.05),
            "kelly_frac_short": trial.suggest_float("kelly_frac_short", 0.20, 0.75, step=0.05),
            "leverage_long": trial.suggest_float("leverage_long", 2.0, 6.0, step=0.5),
            "leverage_short": trial.suggest_float("leverage_short", 5.0, 12.0, step=1.0),
            "max_margin_utilization": trial.suggest_float("max_margin_utilization", 0.50, 0.90, step=0.05)
        }

        cap, max_dd, n_trades = simulate_policy(df_train, params, hl_max_lev_map)

        if n_trades < 30 or cap <= 10.0 or max_dd >= 0.50:
            return -100.0

        days_train = (df_train["timestamp"].max() - df_train["timestamp"].min()).total_seconds() / 86400.0
        cagr = ((cap / STARTING_CAPITAL) ** (365.0 / max(1.0, days_train)) - 1.0) * 100.0
        calmar = cagr / (max_dd * 100.0) if max_dd > 0 else 0.0

        # Drawdown penalty hurdle: penalize heavily if Max DD exceeds 25%
        dd_penalty = max(0.0, (max_dd - 0.25) * 20.0)
        score = calmar - dd_penalty
        return score

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=N_TRIALS)

    best_p = study.best_params
    print("\n" + "=" * 90)
    print("                    OPTIMIZATION COMPLETE: BEST IN-SAMPLE PARAMETERS")
    print("=" * 90)
    for k, v in best_p.items():
        print(f"  • {k:<28}: {v}")

    print("\n[3/3] Validating Optimal Parameters on Frozen Out-of-Sample Holdout...")
    cap_oos, dd_oos, n_oos = simulate_policy(df_holdout, best_p, hl_max_lev_map)
    days_oos = (df_holdout["timestamp"].max() - df_holdout["timestamp"].min()).total_seconds() / 86400.0
    cagr_oos = ((cap_oos / STARTING_CAPITAL) ** (365.0 / max(1.0, days_oos)) - 1.0) * 100.0 if cap_oos > 0 else -100.0
    calmar_oos = cagr_oos / (dd_oos * 100.0) if dd_oos > 0 else 0.0

    print("\n" + "=" * 90)
    print("               UNTOUCHED OUT-OF-SAMPLE HOLDOUT PERFORMANCE")
    print("=" * 90)
    print(f"Ending Equity ($1k Start):    ${cap_oos:,.2f}")
    print(f"Out-of-Sample Net Return:     {((cap_oos/STARTING_CAPITAL)-1)*100:+.2f}%")
    print(f"Annualized CAGR:              {cagr_oos:>+12.2f}%")
    print(f"Maximum Drawdown:            -{dd_oos*100:>11.2f}%")
    print(f"Calmar Ratio:                 {calmar_oos:>12.2f}")
    print(f"Total Trades Executed:        {n_oos:>12}")
    print("=" * 90)

    with open("optimal_policy_params.json", "w") as f:
        json.dump(best_p, f, indent=4)
    print("\n[SUCCESS] Optimal parameter vector exported to 'optimal_policy_params.json'!\n")

if __name__ == "__main__":
    main()

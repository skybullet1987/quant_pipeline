#!/usr/bin/env python3
"""
Quantitative Risk Frontier, Parameter Stability, & Trade Autopsy Diagnostic
Evaluates:
  1. Granular Statistical Autopsy of OOS Trades (Long vs Short, Regimes, Percentiles)
  2. 2D Parameter Stability Matrix (Threshold x Kelly)
  3. Pareto Risk-Frontier Surface (Short Kelly x Short Leverage)
"""

import os
import json
import joblib
import requests
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool

warnings.filterwarnings("ignore")

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
STARTING_CAPITAL = 1000.0
MAX_POSITIONS = 5
MAX_TRADES_PER_CYCLE = 2
FEE_SLIPPAGE_BPS = 15.0
HARD_LIQUIDITY_CAP_USD = 150000.0
LOOKBACK_DAYS = 90

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

def load_and_score_matrix():
    client = bigquery.Client(project=PROJECT_ID)
    print(f"\n[1/4] Ingesting {LOOKBACK_DAYS}-day feature store from BigQuery...")

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
# 2. CORE SIMULATION ENGINE
# ============================================================================
def simulate_holdout_trades(df, params, hl_max_lev_map):
    capital = STARTING_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    open_positions = []
    trade_log = []

    timestamps = sorted(df["timestamp"].unique())

    for current_ts in timestamps:
        # Process exits
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
            break

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
                    "exit_time": row["exit_time"], "regime": reg
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
                "coin": coin, "side": cand["side"], "margin": req_margin,
                "notional": final_notional, "pnl": pnl,
                "ret_pct": cand["net_win"] if hit_target else -cand["net_loss"],
                "entry_time": current_ts, "exit_time": cand["exit_time"],
                "regime": cand["regime"], "hit_target": hit_target
            })
            active_coins.add(coin)

    for pos in open_positions:
        capital += pos["margin"] + pos["pnl"]
        trade_log.append(pos)

    return pd.DataFrame(trade_log), capital, max_dd

# ============================================================================
# 3. EXPERIMENT SUITE: AUTOPSY, STABILITY & FRONTIER
# ============================================================================
def main():
    df_scored = load_and_score_matrix()
    hl_max_lev_map = get_hyperliquid_max_leverage()

    timestamps = np.sort(df_scored["timestamp"].unique())
    split_idx = int(len(timestamps) * 0.70)
    train_end = timestamps[split_idx]
    test_start = train_end + pd.Timedelta(hours=72)
    df_holdout = df_scored[df_scored["timestamp"] >= test_start].copy().reset_index(drop=True)

    oos_days = (df_holdout["timestamp"].max() - df_holdout["timestamp"].min()).total_seconds() / 86400.0
    print(f"[2/4] Frozen OOS Holdout: {len(df_holdout):,} ticker-bars across {oos_days:.1f} days ({df_holdout['ticker'].nunique()} tickers).")

    # ------------------------------------------------------------------------
    # EXPERIMENT 1: STATISTICAL AUTOPSY OF THE 50 OPTUNA OOS TRADES
    # ------------------------------------------------------------------------
    optuna_params = {
        "entry_threshold_long": 0.61, "entry_threshold_short": 0.59,
        "kelly_frac_long": 0.35, "kelly_frac_short": 0.75,
        "leverage_long": 4.0, "leverage_short": 11.0,
        "max_margin_utilization": 0.90
    }
    trades_df, cap_oos, max_dd = simulate_holdout_trades(df_holdout, optuna_params, hl_max_lev_map)

    print("\n" + "=" * 90)
    print("                EXPERIMENT 1: OOS 50-TRADE STATISTICAL AUTOPSY")
    print("=" * 90)

    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] <= 0]
    wr = len(wins) / len(trades_df) * 100.0
    gp = wins["pnl"].sum()
    gl = abs(losses["pnl"].sum())
    pf = (gp / gl) if gl > 0 else np.nan
    ret_pct = ((cap_oos / STARTING_CAPITAL) - 1.0) * 100.0
    r_dd = (ret_pct / (max_dd * 100.0)) if max_dd > 0 else np.nan

    # Consecutive losses calculation
    streak = 0
    max_consec_loss = 0
    for is_win in (trades_df["pnl"] > 0):
        if not is_win:
            streak += 1
            max_consec_loss = max(max_consec_loss, streak)
        else:
            streak = 0

    p_pnl = np.percentile(trades_df["pnl"], [5, 25, 50, 75, 95])

    print(f"OOS Capital Growth:          ${STARTING_CAPITAL:,.2f}  ──>  ${cap_oos:,.2f}  ({ret_pct:+.2f}%)")
    print(f"Maximum Drawdown:           -{max_dd * 100.0:.2f}%")
    print(f"Return / Drawdown (R/DD):    {r_dd:.2f}x")
    print(f"Total Trades:                {len(trades_df)}")
    print(f"Win Rate:                    {wr:.1f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Profit Factor:               {pf:.2f}")
    print(f"Expectancy Per Trade:       +${trades_df['pnl'].mean():.2f} ({(trades_df['ret_pct'].mean())*100:+.2f}%)")
    print(f"Average Winner / Loser:     +${wins['pnl'].mean():.2f}  /  -${abs(losses['pnl'].mean()):.2f}")
    print(f"Max Consecutive Losses:      {max_consec_loss} trades")
    print(f"PnL Percentiles (5/25/50/75/95):")
    print(f"  [ 5% ]: -${abs(p_pnl[0]):.2f} | [ 25% ]: -${abs(p_pnl[1]):.2f} | [ Median ]: +${p_pnl[2]:.2f} | [ 75% ]: +${p_pnl[3]:.2f} | [ 95% ]: +${p_pnl[4]:.2f}")

    print("\n--- SIDE & REGIME ATTRIBUTION ---")
    for side in ["BUY", "SELL"]:
        sub = trades_df[trades_df["side"] == side]
        s_wr = (sub['pnl'] > 0).mean() * 100.0 if len(sub) > 0 else 0
        print(f"  • {side:<4} ({len(sub):>2} trades): PnL: ${sub['pnl'].sum():>+8.2f} | WR: {s_wr:>5.1f}% | Avg Trade: ${sub['pnl'].mean():>+6.2f}")

    for reg in sorted(trades_df["regime"].unique()):
        sub = trades_df[trades_df["regime"] == reg]
        r_wr = (sub['pnl'] > 0).mean() * 100.0 if len(sub) > 0 else 0
        print(f"  • Regime {reg:<1} ({len(sub):>2} trades): PnL: ${sub['pnl'].sum():>+8.2f} | WR: {r_wr:>5.1f}% | Avg Trade: ${sub['pnl'].mean():>+6.2f}")

    # ------------------------------------------------------------------------
    # EXPERIMENT 2: 2D PARAMETER STABILITY GRID (Short Thresh x Short Kelly)
    # ------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("         EXPERIMENT 2: 2D PARAMETER STABILITY GRID (FROZEN OOS RET % / MAX DD %)")
    print("=" * 90)
    thresholds = [0.55, 0.57, 0.59, 0.61, 0.63]
    kellys = [0.35, 0.45, 0.55, 0.65, 0.75]

    header = f"{'Threshold':<10}" + "".join([f"Kelly {k:<8.2f}" for k in kellys])
    print(header)
    print("-" * 90)

    for th in thresholds:
        row_str = f"S-Th: {th:<5.2f} |"
        for k in kellys:
            p = optuna_params.copy()
            p["entry_threshold_short"] = th
            p["kelly_frac_short"] = k
            _, cap, dd = simulate_holdout_trades(df_holdout, p, hl_max_lev_map)
            r = ((cap / STARTING_CAPITAL) - 1.0) * 100.0
            row_str += f" +{r:>4.0f}%/-{dd*100:>2.0f}% |"
        print(row_str)

    # ------------------------------------------------------------------------
    # EXPERIMENT 3: PARETO RISK-FRONTIER (Short Kelly x Short Leverage)
    # ------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("         EXPERIMENT 3: SHORT-SIDE PARETO RISK FRONTIER (FROZEN OOS)")
    print("=" * 90)
    print(f"{'Short Kelly':<13}{'Short Lev':<12}{'OOS Return':<14}{'Max Drawdown':<15}{'R / DD Ratio':<15}{'Profit Factor':<14}{'Trades':<8}")
    print("-" * 90)

    frontier_configs = [
        (0.35, 8.0, "Conservative"),
        (0.50, 8.0, "Moderate-Lev"),
        (0.50, 10.0, "Moderate-Balanced"),
        (0.60, 10.0, "Aggressive"),
        (0.75, 8.0, "High-Kelly/Low-Lev"),
        (0.75, 11.0, "Optuna Max Bounds")
    ]

    for k, lev, label in frontier_configs:
        p = optuna_params.copy()
        p["kelly_frac_short"] = k
        p["leverage_short"] = lev
        sub_trades, cap, dd = simulate_holdout_trades(df_holdout, p, hl_max_lev_map)
        r = ((cap / STARTING_CAPITAL) - 1.0) * 100.0
        r_dd_val = (r / (dd * 100.0)) if dd > 0 else 0
        w = sub_trades[sub_trades["pnl"] > 0]["pnl"].sum()
        l = abs(sub_trades[sub_trades["pnl"] <= 0]["pnl"].sum())
        pf_val = (w / l) if l > 0 else np.nan

        print(f"{k:<13.2f}{lev:<12.1f}{r:>+10.2f}%   {'-' + f'{dd*100:.2f}%':<15}{r_dd_val:>10.2f}x   {pf_val:>10.2f}    {len(sub_trades):>6}  ({label})")

    print("=" * 90 + "\n")

if __name__ == "__main__":
    main()

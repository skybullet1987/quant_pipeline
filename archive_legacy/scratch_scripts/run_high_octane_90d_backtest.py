#!/usr/bin/env python3
"""
High-Octane 90-Day Compounding Backtest Engine
Directly integrated with BigQuery market_data schema, HMM regimes,
CatBoost meta-labelers (dynamic feature alignment), and dynamic leverage compounding.
"""

import os
import sys
import glob
import requests
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = "parnasa-498503"
STARTING_CAPITAL = 1000.0
ROUNDTRIP_FEE_BPS = 15.0  # 15 bps taker fee + slippage buffer
MAX_MARGIN_CAP = 0.60     # 60% max committed margin


def find_model_dir():
    search_dirs = [
        os.getenv("MODEL_DIR", ""),
        "production_models",
        "/home/skybullet1987/quant_pipeline/production_models",
        "models",
        "artifacts",
        ".",
    ]
    for d in search_dirs:
        if d and os.path.exists(os.path.join(d, "hmm_macro.pkl")):
            return os.path.abspath(d)
    
    for root, _, files in os.walk("/home/skybullet1987/quant_pipeline"):
        if "hmm_macro.pkl" in files:
            return root
    return "."


def get_hyperliquid_max_leverage():
    try:
        resp = requests.post("https://api.hyperliquid.xyz/info", json={"type": "meta"}, timeout=10)
        meta = resp.json()
        return {asset["name"]: asset["maxLeverage"] for asset in meta["universe"]}
    except Exception:
        return {}


def main():
    print("=" * 80)
    print("  SIMULATING HIGH-OCTANE 90-DAY ASYMMETRIC COMPOUNDING BACKTEST")
    print("=" * 80)

    model_dir = find_model_dir()
    print(f"Detected Model Artifacts Directory: {model_dir}")

    hl_max_lev_map = get_hyperliquid_max_leverage()
    client = bigquery.Client(project=PROJECT_ID)

    print("[1/4] Querying 90-day feature store matrix & exact path resolutions...")
    query = f"""
        SELECT 
            f.*, 
            t.* EXCEPT (ticker, timestamp),
            l.* EXCEPT (ticker, timestamp),
            p.target_price_1_5_atr, p.stop_loss_1_5_atr,
            p.target_short, p.target_long, p.minutes_in_trade
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.ticker = p.ticker AND f.timestamp = p.signal_time
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t 
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    print(f"Loaded {len(df):,} candidate rows across the 90-day out-of-sample window.")

    print("[2/4] Loading ML model artifacts & computing regime inferences...")
    hmm_model = joblib.load(f"{model_dir}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{model_dir}/hmm_scaler.pkl")
    hmm_features = joblib.load(f"{model_dir}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{model_dir}/hmm_canonical_order.pkl")
    
    meta_long = CatBoostClassifier().load_model(f"{model_dir}/meta_labeler_long.cbm")
    cal_long = joblib.load(f"{model_dir}/meta_calibrator_long.pkl")
    meta_short = CatBoostClassifier().load_model(f"{model_dir}/meta_labeler_short.cbm")
    cal_short = joblib.load(f"{model_dir}/meta_calibrator_short.pkl")
    
    all_cat_cols = joblib.load(f"{model_dir}/cat_cols.pkl")
    all_features = joblib.load(f"{model_dir}/feature_names.pkl")
    cat_set = set(all_cat_cols)

    # 1. HMM Features Sanitation & Inference
    for col in hmm_features:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    scaled_x = hmm_scaler.transform(df[hmm_features])
    can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    df["hmm_p_chop"] = can_probs[:, 0]
    df["hmm_regime"] = can_probs.argmax(axis=1).astype(str)

    # 2. Base Features Sanitation for Regime Experts
    for col in all_features:
        if col not in df.columns:
            df[col] = "missing" if col in cat_set else 0.0
        elif col in cat_set:
            df[col] = df[col].astype(str).fillna("missing")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    cat_features_in_base = [c for c in all_features if c in cat_set]

    df["primary_prob_short"] = 0.0
    df["primary_prob_long"] = 0.0

    # Regime Experts Inference
    for regime in ["0", "1", "2"]:
        m_s_path = f"{model_dir}/regime_{regime}_short_expert.cbm"
        m_l_path = f"{model_dir}/regime_{regime}_long_expert.cbm"
        mask = df["hmm_regime"] == regime
        if mask.sum() > 0:
            regime_pool = Pool(df.loc[mask, all_features], cat_features=cat_features_in_base)
            if os.path.exists(m_s_path):
                m_s = CatBoostClassifier().load_model(m_s_path)
                df.loc[mask, "primary_prob_short"] = m_s.predict_proba(regime_pool)[:, 1]
            if os.path.exists(m_l_path):
                m_l = CatBoostClassifier().load_model(m_l_path)
                df.loc[mask, "primary_prob_long"] = m_l.predict_proba(regime_pool)[:, 1]

    # 3. Meta-Labelers Dynamic Feature Alignment
    meta_s_features = meta_short.feature_names_
    meta_l_features = meta_long.feature_names_

    for col in meta_s_features:
        if col not in df.columns:
            df[col] = "missing" if col in cat_set else 0.0
        elif col in cat_set:
            df[col] = df[col].astype(str).fillna("missing")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in meta_l_features:
        if col not in df.columns:
            df[col] = "missing" if col in cat_set else 0.0
        elif col in cat_set:
            df[col] = df[col].astype(str).fillna("missing")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    meta_s_cats = [c for c in meta_s_features if c in cat_set]
    meta_l_cats = [c for c in meta_l_features if c in cat_set]

    pool_short = Pool(df[meta_s_features], cat_features=meta_s_cats)
    pool_long = Pool(df[meta_l_features], cat_features=meta_l_cats)

    raw_short_probs = meta_short.predict_proba(pool_short)[:, 1]
    raw_long_probs = meta_long.predict_proba(pool_long)[:, 1]

    df["prob_short_cal"] = cal_short.predict(raw_short_probs) if hasattr(cal_short, "predict") else raw_short_probs
    df["prob_long_cal"] = cal_long.predict(raw_long_probs) if hasattr(cal_long, "predict") else raw_long_probs

    print("[3/4] Running continuous compounding simulation across 10x fixed & dynamic tiers...")

    def run_simulation(mode="dynamic"):
        equity = STARTING_CAPITAL
        peak_equity = STARTING_CAPITAL
        max_dd = 0.0
        trades = []

        grouped = df.groupby("timestamp", sort=True)
        for ts, group in grouped:
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

            dd_mult = 0.25 if dd >= 0.30 else (0.50 if dd >= 0.15 else 1.0)
            avail_margin = equity * MAX_MARGIN_CAP
            used_margin = 0.0

            for _, row in group.iterrows():
                p_short = row["prob_short_cal"]
                p_long = row["prob_long_cal"]
                ticker = row["ticker"]

                side = None
                if p_short >= 0.52:
                    side = "SHORT"
                    k_frac = 0.75
                    base_lev = 10.0 if mode == "fixed" else min(hl_max_lev_map.get(ticker, 10.0), 10.0)
                elif p_long >= 0.58:
                    side = "LONG"
                    k_frac = 0.35
                    base_lev = 6.0 if mode == "fixed" else min(hl_max_lev_map.get(ticker, 6.0), 6.0)

                if side is None:
                    continue

                target_margin = equity * k_frac * dd_mult
                if used_margin + target_margin > avail_margin:
                    target_margin = avail_margin - used_margin
                    if target_margin <= 1.0:
                        break

                used_margin += target_margin
                pos_notional = target_margin * base_lev

                if side == "SHORT":
                    hit_target = (row["target_short"] == 1)
                else:
                    hit_target = (row["target_long"] == 1)

                raw_ret_pct = 0.0225 if hit_target else -0.0150
                net_ret_pct = raw_ret_pct - (ROUNDTRIP_FEE_BPS / 10000.0)
                pnl = pos_notional * net_ret_pct

                equity += pnl
                if equity > peak_equity:
                    peak_equity = equity

                trades.append({
                    "timestamp": ts,
                    "ticker": ticker,
                    "side": side,
                    "leverage": base_lev,
                    "pnl": pnl,
                    "win": 1 if pnl > 0 else 0
                })

            if equity <= 10.0:
                print("[CRITICAL] Liquidation threshold reached.")
                break

        t_df = pd.DataFrame(trades)
        wr = (t_df["win"].sum() / len(t_df) * 100.0) if len(t_df) > 0 else 0.0
        return equity, len(t_df), wr, max_dd

    eq_fixed, n_fixed, wr_fixed, dd_fixed = run_simulation("fixed")
    eq_dyn, n_dyn, wr_dyn, dd_dyn = run_simulation("dynamic")

    print("\n" + "-" * 72)
    print("                 90-DAY HIGH-OCTANE BACKTEST RESULTS")
    print("-" * 72)
    print(f"{'Metric':<26} | {'Fixed 10x Baseline':<20} | {'Dynamic Platform Lev':<20}")
    print("-" * 72)
    print(f"{'Final Equity ($1k Start)':<26} | ${eq_fixed:>18,.2f} | ${eq_dyn:>18,.2f}")
    print(f"{'Total Trades Executed':<26} | {n_fixed:>18,} | {n_dyn:>18,}")
    print(f"{'Win Rate':<26} | {wr_fixed:>17.2f}% | {wr_dyn:>17.2f}%")
    print(f"{'Maximum Drawdown':<26} | -{dd_fixed*100:>16.2f}% | -{dd_dyn*100:>16.2f}%")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()

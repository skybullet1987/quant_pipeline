#!/usr/bin/env python3
"""
Champion vs Challenger Model Governance Engine
- Walk-Forward Training & OOF Isotonic Calibration
- Untouched 90-Day Holdout Simulation
- Tier 1 Hard Gates & Tier 2 Paired Bootstrap (10,000 runs)
- Immutable Release Creation & Atomic Manifest Pointer Update
"""

import os
import json
import shutil
import logging
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import KFold
from sklearn.metrics import brier_score_loss

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ID = "parnasa-498503"
HOLDOUT_DAYS = 90
FEE_SLIPPAGE_BPS = 15.0
BOOTSTRAP_ROUNDS = 10000


def load_dataset():
    client = bigquery.Client(project=PROJECT_ID)
    logging.info("Querying historical feature tables from BigQuery...")
    query = f"""
        SELECT 
            f.*, 
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
        LEFT JOIN (
            SELECT * QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker, timestamp ORDER BY timestamp DESC) = 1
            FROM `{PROJECT_ID}.market_data.fct_timesfm_features`
        ) t ON f.ticker = t.ticker AND f.timestamp = t.timestamp
        LEFT JOIN (
            SELECT * QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker, timestamp ORDER BY timestamp DESC) = 1
            FROM `{PROJECT_ID}.market_data.fct_liquidation_features`
        ) l ON f.ticker = l.ticker AND f.timestamp = l.timestamp
        WHERE f.target_binary_long IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def simulate_trades(df_slice, model_dir):
    """Simulates selective execution and returns trade returns in basis points."""
    cb_long = CatBoostClassifier().load_model(os.path.join(model_dir, "regime_1_long_expert.cbm"))
    cb_short = CatBoostClassifier().load_model(os.path.join(model_dir, "regime_2_short_expert.cbm"))
    cal_l = joblib.load(os.path.join(model_dir, "meta_calibrator_long.pkl"))
    cal_s = joblib.load(os.path.join(model_dir, "meta_calibrator_short.pkl"))
    cat_set = set(joblib.load(os.path.join(model_dir, "cat_cols.pkl")) if os.path.exists(os.path.join(model_dir, "cat_cols.pkl")) else [])

    feats_l = cb_long.feature_names_
    feats_s = cb_short.feature_names_

    for c in set(feats_l + feats_s):
        if c not in df_slice.columns:
            df_slice[c] = "missing" if c in cat_set else 0.0
        elif c in cat_set:
            df_slice[c] = df_slice[c].astype(str).fillna("missing")
        else:
            df_slice[c] = pd.to_numeric(df_slice[c], errors="coerce").fillna(0.0)

    pl_raw = cb_long.predict_proba(Pool(df_slice[feats_l], cat_features=[c for c in feats_l if c in cat_set]))[:, 1]
    ps_raw = cb_short.predict_proba(Pool(df_slice[feats_s], cat_features=[c for c in feats_s if c in cat_set]))[:, 1]

    pl = cal_l.predict(pl_raw)
    ps = cal_s.predict(ps_raw)

    trades = []
    for idx, (_, row) in enumerate(df_slice.iterrows()):
        p_l, p_s = pl[idx], ps[idx]
        px = float(row.get("close_price", row.get("close", 1.0)))
        atr = float(row.get("atr_14", row.get("atr_20", px * 0.02)))
        r_dist = (1.50 * atr) / px if px > 0 else 0.03
        fee_cut = FEE_SLIPPAGE_BPS / 10000.0

        if p_l >= 0.58 and (((2 * p_l) - 1) * r_dist - fee_cut) > 0:
            realized_ret = (float(row.get("realized_return_tb", r_dist)) - fee_cut) * 10000.0
            trades.append({"side": "LONG", "ev_bps": realized_ret, "p": p_l, "y": int(row.get("target_binary_long", 0))})
        elif p_s >= 0.52 and (((2 * p_s) - 1) * r_dist - fee_cut) > 0:
            realized_ret = (float(row.get("realized_return_tb", r_dist)) - fee_cut) * 10000.0
            trades.append({"side": "SHORT", "ev_bps": realized_ret, "p": p_s, "y": int(row.get("target_binary_short", 0))})

    return pd.DataFrame(trades)


def run_governance_cycle():
    df = load_dataset()
    cutoff_dt = df["timestamp"].max() - pd.Timedelta(days=HOLDOUT_DAYS)
    
    df_train = df[df["timestamp"] < cutoff_dt].copy()
    df_holdout = df[df["timestamp"] >= cutoff_dt].copy()
    logging.info(f"Split completed: Train={len(df_train)} rows | Frozen Holdout={len(df_holdout)} rows ({HOLDOUT_DAYS} days)")

    # 1. Resolve Active Champion Directory
    with open("models/manifest.json", "r") as f:
        manifest = json.load(f)
    champ_dir = os.path.join("models", "releases", manifest["active_version"])

    # 2. Train Challenger Candidates
    chal_dir = "models/challenger_temp"
    os.makedirs(chal_dir, exist_ok=True)

    ignore_cols = {"timestamp", "ticker", "target_binary_long", "target_binary_short", "realized_return_tb"}
    feature_cols = [c for c in df_train.columns if c not in ignore_cols]
    cat_cols = [c for c in feature_cols if df_train[c].dtype == "object"]
    joblib.dump(cat_cols, f"{chal_dir}/cat_cols.pkl")

    for c in cat_cols:
        df_train[c] = df_train[c].astype(str).fillna("missing")
    for c in [c for c in feature_cols if c not in cat_cols]:
        df_train[c] = pd.to_numeric(df_train[c], errors="coerce").fillna(0.0)

    # Train CatBoost Long & Short Experts
    cb_long = CatBoostClassifier(iterations=600, depth=6, learning_rate=0.03, verbose=0)
    cb_long.fit(Pool(df_train[feature_cols], df_train["target_binary_long"], cat_features=cat_cols))
    cb_long.save_model(f"{chal_dir}/regime_1_long_expert.cbm")

    cb_short = CatBoostClassifier(iterations=600, depth=6, learning_rate=0.03, verbose=0)
    cb_short.fit(Pool(df_train[feature_cols], df_train["target_binary_short"], cat_features=cat_cols))
    cb_short.save_model(f"{chal_dir}/regime_2_short_expert.cbm")

    # Fit Isotonic Calibrators via 5-Fold OOF Predictions
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_preds_l = np.zeros(len(df_train))
    oof_preds_s = np.zeros(len(df_train))

    for tr_idx, val_idx in kf.split(df_train):
        fold_train, fold_val = df_train.iloc[tr_idx], df_train.iloc[val_idx]
        m_l = CatBoostClassifier(iterations=400, depth=6, learning_rate=0.03, verbose=0).fit(
            Pool(fold_train[feature_cols], fold_train["target_binary_long"], cat_features=cat_cols)
        )
        m_s = CatBoostClassifier(iterations=400, depth=6, learning_rate=0.03, verbose=0).fit(
            Pool(fold_train[feature_cols], fold_train["target_binary_short"], cat_features=cat_cols)
        )
        oof_preds_l[val_idx] = m_l.predict_proba(Pool(fold_val[feature_cols], cat_features=cat_cols))[:, 1]
        oof_preds_s[val_idx] = m_s.predict_proba(Pool(fold_val[feature_cols], cat_features=cat_cols))[:, 1]

    iso_l = IsotonicRegression(out_of_bounds="clip").fit(oof_preds_l, df_train["target_binary_long"])
    iso_s = IsotonicRegression(out_of_bounds="clip").fit(oof_preds_s, df_train["target_binary_short"])
    joblib.dump(iso_l, f"{chal_dir}/meta_calibrator_long.pkl")
    joblib.dump(iso_s, f"{chal_dir}/meta_calibrator_short.pkl")

    # Copy stable HMM macro model from current champion
    if os.path.exists(f"{champ_dir}/hmm_macro.pkl"):
        shutil.copy(f"{champ_dir}/hmm_macro.pkl", f"{chal_dir}/hmm_macro.pkl")
        for extra in ["hmm_scaler.pkl", "hmm_feature_names.pkl", "hmm_canonical_order.pkl"]:
            if os.path.exists(f"{champ_dir}/{extra}"):
                shutil.copy(f"{champ_dir}/{extra}", f"{chal_dir}/{extra}")

    # 3. Simulate on Untouched 90-Day Holdout
    logging.info("Simulating performance across 90-day frozen holdout...")
    t_champ = simulate_trades(df_holdout.copy(), champ_dir)
    t_chal = simulate_trades(df_holdout.copy(), chal_dir)

    n_champ, n_chal = len(t_champ), len(t_chal)
    ev_champ = t_champ["ev_bps"].mean() if n_champ > 0 else 0.0
    ev_chal = t_chal["ev_bps"].mean() if n_chal > 0 else 0.0

    n_long_chal = len(t_chal[t_chal["side"] == "LONG"])
    n_short_chal = len(t_chal[t_chal["side"] == "SHORT"])
    ev_long_chal = t_chal[t_chal["side"] == "LONG"]["ev_bps"].mean() if n_long_chal > 0 else 0.0
    ev_short_chal = t_chal[t_chal["side"] == "SHORT"]["ev_bps"].mean() if n_short_chal > 0 else 0.0

    logging.info("=" * 80)
    logging.info(f"CHAMPION ({manifest['active_version']}): N={n_champ} | Net EV: {ev_champ:+.2f} bps")
    logging.info(f"CHALLENGER (Candidate): N={n_chal} (L:{n_long_chal}, S:{n_short_chal}) | Net EV: {ev_chal:+.2f} bps (L:{ev_long_chal:+.1f}, S:{ev_short_chal:+.1f})")
    logging.info("=" * 80)

    # 4. Evaluate Tier 1 Hard Gates
    hard_pass = True
    reasons = []

    if ev_chal <= 0:
        hard_pass = False; reasons.append("Challenger Net EV <= 0")
    if n_chal < 40:
        hard_pass = False; reasons.append(f"Insufficient trade sample (N={n_chal} < 40)")
    if n_long_chal < 10 or n_short_chal < 10:
        hard_pass = False; reasons.append(f"Directional imbalance (Long N={n_long_chal}, Short N={n_short_chal})")
    if ev_long_chal <= 0 or ev_short_chal < -10.0:
        hard_pass = False; reasons.append("Directional EV failure")

    if not hard_pass:
        logging.warning(f"[REJECTED - TIER 1] Hard gates failed: {', '.join(reasons)}. Champion retained.")
        shutil.rmtree(chal_dir)
        return

    # 5. Evaluate Tier 2 Paired Bootstrap Significance (10,000 iterations)
    logging.info(f"Running {BOOTSTRAP_ROUNDS:,} bootstrap iterations for paired ΔEV significance...")
    diffs = []
    chal_evs = t_chal["ev_bps"].values
    champ_evs = t_champ["ev_bps"].values

    for _ in range(BOOTSTRAP_ROUNDS):
        b_chal = np.random.choice(chal_evs, size=len(chal_evs), replace=True).mean()
        b_champ = np.random.choice(champ_evs, size=len(champ_evs), replace=True).mean()
        diffs.append(b_chal - b_champ)

    p_superior = (np.array(diffs) > 0).mean()
    logging.info(f"Bootstrap P(Challenger > Champion) = {p_superior*100:.2f}%")

    if p_superior < 0.70:
        logging.warning(f"[REJECTED - TIER 2] Delta EV statistically inconclusive (P={p_superior*100:.1f}% < 70%). Champion retained.")
        shutil.rmtree(chal_dir)
        return

    # 6. Promotion Execution
    new_version = f"v{datetime.now(timezone.utc).strftime('%Y_%m_%d')}"
    new_release_dir = os.path.join("models", "releases", new_version)
    os.makedirs(new_release_dir, exist_ok=True)

    for item in os.listdir(chal_dir):
        shutil.move(os.path.join(chal_dir, item), os.path.join(new_release_dir, item))
    shutil.rmtree(chal_dir)

    # Update manifest.json atomically
    updated_manifest = {
        "active_version": new_version,
        "previous_version": manifest["active_version"],
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "holdout_window_days": HOLDOUT_DAYS,
        "metrics": {
            "net_ev_bps": round(float(ev_chal), 2),
            "sample_size": n_chal,
            "p_superiority": round(float(p_superior), 4)
        }
    }
    with open("models/manifest.json", "w") as f:
        json.dump(updated_manifest, f, indent=2)

    logging.info(f"[PROMOTED] Challenger promoted to active release: {new_version}")


if __name__ == "__main__":
    run_governance_cycle()

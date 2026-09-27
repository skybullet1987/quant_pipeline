"""
Asymmetric Target Barrier Method (TBM) ML Alpha Engine:
Trains independent Long and Short CatBoost probability classifiers
on asymmetric reward-to-risk target barriers.
"""
import numpy as np
import pandas as pd
import polars as pl
from catboost import CatBoostClassifier

from src.features.orthogonal_library import compute_orthogonal_features


def compute_tbm_labels(df: pl.DataFrame, tp_mult_long=2.2, sl_mult_long=1.1, tp_mult_short=1.4, sl_mult_short=0.9, max_horizon=18) -> pl.DataFrame:
    """Computes exact forward Target Barrier Method (TBM) discrete hit labels."""
    print("Computing forward Target Barrier Method (TBM) labels...")
    pdf = df.sort(["symbol", "bucket_timestamp_utc"]).to_pandas()
    
    n_rows = len(pdf)
    long_labels = np.zeros(n_rows, dtype=np.int32)
    short_labels = np.zeros(n_rows, dtype=np.int32)
    
    prices_close = pdf["close"].values
    prices_high = pdf["high"].values
    prices_low = pdf["low"].values
    atrs = pdf["normalized_atr_24h"].values * prices_close
    symbols = pdf["symbol"].values
    
    # Vectorized fast lookahead for each symbol
    sym_indices = {s: np.where(symbols == s)[0] for s in np.unique(symbols)}
    
    for sym, idxs in sym_indices.items():
        m = len(idxs)
        for i in range(m - max_horizon):
            curr_idx = idxs[i]
            entry_px = prices_close[curr_idx]
            atr = max(atrs[curr_idx], entry_px * 0.01)
            
            # Long Barriers
            tp_l = entry_px + (tp_mult_long * atr)
            sl_l = entry_px - (sl_mult_long * atr)
            
            # Short Barriers
            tp_s = entry_px - (tp_mult_short * atr)
            sl_s = entry_px + (sl_mult_short * atr)
            
            fwd_highs = prices_high[idxs[i+1 : i+1+max_horizon]]
            fwd_lows = prices_low[idxs[i+1 : i+1+max_horizon]]
            
            # Long evaluation: Check if TP hit before SL
            l_hit = 0
            for h, l in zip(fwd_highs, fwd_lows):
                if l <= sl_l:
                    l_hit = 0
                    break
                if h >= tp_l:
                    l_hit = 1
                    break
            long_labels[curr_idx] = l_hit
            
            # Short evaluation: Check if TP hit before SL
            s_hit = 0
            for h, l in zip(fwd_highs, fwd_lows):
                if h >= sl_s:
                    s_hit = 0
                    break
                if l <= tp_s:
                    s_hit = 1
                    break
            short_labels[curr_idx] = s_hit

    pdf["label_long_tbm"] = long_labels
    pdf["label_short_tbm"] = short_labels
    return pl.from_pandas(pdf)


def generate_asymmetric_tbm_alphas(raw_df: pl.DataFrame) -> pd.DataFrame:
    """Trains decoupled Long & Short CatBoost classifiers on asymmetric TBM labels."""
    feat_df = compute_orthogonal_features(raw_df)
    labeled_df = compute_tbm_labels(feat_df)
    
    pdf = labeled_df.to_pandas()
    pdf["ts_utc"] = pd.to_datetime(pdf["bucket_timestamp_utc"], utc=True)
    
    long_features = [
        "cs_rank_ret_24h", "cs_mom_acceleration_24_72", "cs_dist_to_universe_median_24h",
        "lower_wick_absorption_ratio_4h", "bollinger_keltner_squeeze_ratio_20",
        "cs_rank_volume_pct_24h", "interaction_mom_squeeze_24h",
        "interaction_breakout_thrust", "interaction_tbm_score", "clv_4h"
    ]
    
    short_features = [
        "cs_rank_ret_72h", "cs_dist_to_universe_median_24h", "upper_wick_ratio_4h",
        "intrabar_wick_imbalance_4h", "garman_klass_vol_ratio_24h",
        "beta_btc_7d", "idio_residual_ret_btc_24h", "normalized_atr_24h"
    ]
    
    pdf = pdf.dropna(subset=long_features + short_features + ["label_long_tbm", "label_short_tbm"])
    timestamps = pd.Series(pdf["ts_utc"].unique()).sort_values().reset_index(drop=True)
    
    pdf["prob_long_tp"] = 0.50
    pdf["prob_short_tp"] = 0.50
    
    print(f"Training Dual Walk-Forward CatBoost Classifiers across {len(timestamps)} bars...")
    
    for s in range(2160, len(timestamps), 720):
        e = min(s + 720, len(timestamps))
        tr_mask = pdf["ts_utc"].isin(set(timestamps.iloc[:s]))
        te_mask = pdf["ts_utc"].isin(set(timestamps.iloc[s:e]))
        
        # 1. Train Long Classifier (P(TP Long hit))
        X_tr_l = pdf.loc[tr_mask, long_features].values
        y_tr_l = pdf.loc[tr_mask, "label_long_tbm"].values
        X_te_l = pdf.loc[te_mask, long_features].values
        
        # 2. Train Short Classifier (P(TP Short hit))
        X_tr_s = pdf.loc[tr_mask, short_features].values
        y_tr_s = pdf.loc[tr_mask, "label_short_tbm"].values
        X_te_s = pdf.loc[te_mask, short_features].values
        
        if len(X_te_l) == 0 or len(X_tr_l) == 0:
            continue
            
        cat_long = CatBoostClassifier(iterations=60, depth=4, learning_rate=0.04, random_seed=42, thread_count=-1, verbose=0)
        cat_short = CatBoostClassifier(iterations=60, depth=4, learning_rate=0.04, random_seed=42, thread_count=-1, verbose=0)
        
        cat_long.fit(X_tr_l, y_tr_l)
        cat_short.fit(X_tr_s, y_tr_s)
        
        # Predict calibrated class probabilities
        pdf.loc[te_mask, "prob_long_tp"] = cat_long.predict_proba(X_te_l)[:, 1]
        pdf.loc[te_mask, "prob_short_tp"] = cat_short.predict_proba(X_te_s)[:, 1]

    # Composite Asymmetric Alpha Score: Long Edge minus Short Edge
    pdf["asymmetric_alpha"] = pdf["prob_long_tp"] - pdf["prob_short_tp"]
    
    return pdf.pivot(index="ts_utc", columns="symbol", values="asymmetric_alpha").fillna(0.0)

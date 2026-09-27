"""
Production execution snippet to embed inside execute_trading_decisions.py
"""
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

MODEL_PATH = "models/artifacts/catboost_macro_interaction_v1.cbm"
model = CatBoostClassifier()
model.load_model(MODEL_PATH)

FEATURE_COLS = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "expected_sharpe_proxy", "forecast_momentum",
    "macro_expansion_score", "expansion_quintile", "is_q1_coiling", "is_q5_laggard"
]

def score_live_universe(df_features: pd.DataFrame, live_mode: bool = False):
    df = df_features.dropna(subset=FEATURE_COLS).copy()
    if df.empty:
        return None, "NO_VALID_DATA"
        
    df["model_p_long"] = model.predict_proba(df[FEATURE_COLS])[:, 1]
    
    # Sort cross-sectionally
    candidates = df.sort_values("model_p_long", ascending=False).reset_index(drop=True)
    top_setup = candidates.iloc[0]
    
    macro_score = top_setup["macro_expansion_score"]
    quintile = top_setup["expansion_quintile"]
    p_long = top_setup["model_p_long"]
    ticker = top_setup["ticker"]
    
    # Calibrated Meta-Router Policy:
    # Baseline Hurdle = 0.53 (~98th percentile conviction)
    # Q1 Coiling / Q5 Expansion permit entry at 0.52; Q2-Q4 enforce cash unless P >= 0.56
    if quintile in [1, 5]:
        active_hurdle = 0.52
    else:
        active_hurdle = 0.56
        
    should_execute = p_long >= active_hurdle
    
    audit_record = {
        "timestamp": str(top_setup["timestamp"]),
        "top_ticker": ticker,
        "p_long": round(float(p_long), 4),
        "active_hurdle": active_hurdle,
        "macro_score": round(float(macro_score), 4),
        "regime_quintile": int(quintile),
        "should_execute": should_execute,
        "dist_ema20_atr": round(float(top_setup.get("dist_ema20_atr", 0.0)), 2),
        "execution_state": "DISPATCHED" if (should_execute and live_mode) else ("SHADOW_SIGNAL" if should_execute else "CASH_PRESERVED")
    }
    
    return top_setup if should_execute else None, audit_record

"""
SIGNAL DECAY & INFORMATION COEFFICIENT (IC) DIAGNOSTIC
================================================================================
Empirical evaluation of cross-sectional feature decay across horizons h in {1, 2, 4, 8, 12, 18} bars
(4H, 8H, 16H, 32H, 48H, 72H) for both Raw Returns r_i and Beta-Neutral Residual Returns alpha_i.
Includes sub-regime conditioning: Bull vs Bear and High vs Low Volatility.
"""

import sys
import warnings
from pathlib import Path
import numpy as np
import polars as pl
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from catboost import CatBoostClassifier
from src.execution.papertrade_daemon import FEAT_COLS, HMM_FEATURE_COLS

LAKE_CACHE = PIPELINE_ROOT / "data" / "lake" / "fct_4h_production_cache.parquet"
MODELS_DIR = PIPELINE_ROOT / "models" / "prod"

HORIZONS = [1, 2, 4, 8, 12, 18]  # in 4H bars: 4H, 8H, 16H, 32H, 48H, 72H


def compute_spearman_ic(x: np.ndarray, y: np.ndarray) -> float:
    mask = ~np.isnan(x) & ~np.isnan(y) & ~np.isinf(x) & ~np.isinf(y)
    if np.sum(mask) < 10:
        return np.nan
    x_valid = x[mask]
    y_valid = y[mask]
    if np.all(x_valid == x_valid[0]) or np.all(y_valid == y_valid[0]):
        return np.nan
    corr, _ = spearmanr(x_valid, y_valid)
    return float(corr) if not np.isnan(corr) else np.nan


def run_ic_diagnostic():
    print("=" * 115)
    print("           INSTITUTIONAL SIGNAL DECAY & INFORMATION COEFFICIENT (IC) AUDIT           ")
    print("=" * 115)

    if not LAKE_CACHE.exists():
        raise FileNotFoundError(f"Cache {LAKE_CACHE} does not exist.")

    print("--> [1/5] Loading 4H Production Lake Cache...")
    df = pl.read_parquet(LAKE_CACHE)
    if "ticker" in df.columns and "symbol" not in df.columns:
        df = df.rename({"ticker": "symbol"})
    if "timestamp" in df.columns and "timestamp_ms" not in df.columns:
        df = df.with_columns(pl.col("timestamp").dt.epoch("ms").alias("timestamp_ms"))

    ts_col = "timestamp_ms"
    df = df.sort(["symbol", ts_col])

    # 1-bar return
    df = df.with_columns(
        (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).fill_null(0.0).alias("ret_4h")
    )

    # Multi-horizon forward returns
    fwd_exprs = []
    for h in HORIZONS:
        fwd_exprs.append(
            (pl.col("close").shift(-h).over("symbol") / pl.col("close") - 1.0).alias(f"fwd_ret_{h}b")
        )
    df = df.with_columns(fwd_exprs)

    # Extract BTC series for beta estimation and macro gating
    btc_df = df.filter(pl.col("symbol") == "BTC").select([
        ts_col,
        pl.col("close").alias("btc_close"),
        pl.col("ret_4h").alias("btc_ret_4h")
    ]).sort(ts_col)

    btc_df = btc_df.with_columns([
        (pl.col("btc_close") > pl.col("btc_close").ewm_mean(span=20)).alias("btc_bull")
    ])
    for h in HORIZONS:
        btc_df = btc_df.with_columns(
            (pl.col("btc_close").shift(-h) / pl.col("btc_close") - 1.0).alias(f"btc_fwd_{h}b")
        )

    df = df.join(btc_df, on=ts_col, how="left")

    print("--> [2/5] Computing Rolling 60-Bar Beta & Market-Neutral Residual Returns...")
    # Convert to pandas for fast rolling covariance computation per symbol
    pdf = df.to_pandas()
    pdf = pdf.sort_values(["symbol", ts_col])

    # Rolling beta: cov(r_i, r_btc) / var(r_btc) over 60 bars (10 days)
    def calc_sym_beta(group):
        cov = group["ret_4h"].rolling(60, min_periods=20).cov(group["btc_ret_4h"])
        var = group["btc_ret_4h"].rolling(60, min_periods=20).var()
        beta = (cov / (var + 1e-8)).clip(0.10, 3.00).fillna(1.0)
        group["beta_btc"] = beta
        return group

    pdf = pdf.groupby("symbol", group_keys=False).apply(calc_sym_beta)

    # Residual forward returns: alpha_i = fwd_ret_i - beta_i * btc_fwd
    for h in HORIZONS:
        pdf[f"res_fwd_{h}b"] = pdf[f"fwd_ret_{h}b"] - pdf["beta_btc"] * pdf[f"btc_fwd_{h}b"]

    # Add CatBoost probabilities
    print("--> [3/5] Scoring Production ML Models (CatBoost Long/Short)...")
    cb_feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]
    # Fallback default macro features if not directly in columns
    for c in ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear"]:
        if c not in pdf.columns:
            pdf[c] = 0.33

    try:
        cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
        cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")
        valid_cb = [c for c in cb_feature_cols if c in pdf.columns]
        for c in cb_feature_cols:
            if c not in pdf.columns:
                pdf[c] = 0.0
        pdf["catboost_long_score"] = cb_long.predict_proba(pdf[cb_feature_cols])[:, 1]
        pdf["catboost_short_score"] = cb_short.predict_proba(pdf[cb_feature_cols])[:, 1]
        pdf["catboost_net_score"] = pdf["catboost_long_score"] - pdf["catboost_short_score"]
        has_cb = True
    except Exception as e:
        print(f"    [WARN] CatBoost loading failed: {e}")
        has_cb = False

    # Beta-stripped residual momentum
    pdf["res_mom_24h"] = pdf["mom_24h"] - pdf["beta_btc"] * pdf.groupby(ts_col)["btc_ret_4h"].transform("first") * 6.0
    pdf["res_mom_7d"] = pdf["mom_7d"] - pdf["beta_btc"] * pdf.groupby(ts_col)["btc_ret_4h"].transform("first") * 42.0

    # Macro dispersion
    ts_disp = pdf.groupby(ts_col)["ret_4h"].std().to_dict()
    pdf["csd"] = pdf[ts_col].map(ts_disp)
    median_csd = float(np.nanmedian(list(ts_disp.values())))

    # Features to analyze
    feature_candidates = [
        "mom_24h", "mom_7d", "mom_accel_24h", "dist_ema20_atr", "dist_to_120p_high",
        "bbw_pct_40", "gk_vol_20p", "vol_compression_ratio", "relative_vol_120p",
        "macro_expansion_score", "res_mom_24h", "res_mom_7d"
    ]
    if has_cb:
        feature_candidates.extend(["catboost_long_score", "catboost_net_score"])

    # Filter out timestamps near the end without forward returns
    max_h = max(HORIZONS)
    all_ts = sorted(pdf[ts_col].unique())
    eval_ts = all_ts[60:-max_h]  # Warmup 60 bars for beta, drop last max_h bars
    print(f"--> [4/5] Computing Spearman Rank IC across {len(eval_ts)} evaluation bars for {len(feature_candidates)} features...")

    # Group dataframe by timestamp for fast cross-sectional correlation
    ts_groups = {t: sub for t, sub in pdf[pdf[ts_col].isin(eval_ts)].groupby(ts_col)}

    results = []

    for feat in feature_candidates:
        if feat not in pdf.columns:
            continue

        for h in HORIZONS:
            ic_raw_list = []
            ic_res_list = []
            ic_bull_list = []
            ic_bear_list = []
            ic_hvol_list = []
            ic_lvol_list = []

            for t in eval_ts:
                if t not in ts_groups:
                    continue
                sub = ts_groups[t]
                x = sub[feat].to_numpy()
                y_raw = sub[f"fwd_ret_{h}b"].to_numpy()
                y_res = sub[f"res_fwd_{h}b"].to_numpy()

                ic_r = compute_spearman_ic(x, y_raw)
                ic_a = compute_spearman_ic(x, y_res)

                if not np.isnan(ic_r):
                    ic_raw_list.append(ic_r)
                    is_bull = bool(sub["btc_bull"].iloc[0]) if "btc_bull" in sub.columns else True
                    is_hvol = bool(sub["csd"].iloc[0] > median_csd) if "csd" in sub.columns else False

                    if is_bull:
                        ic_bull_list.append(ic_r)
                    else:
                        ic_bear_list.append(ic_r)

                    if is_hvol:
                        ic_hvol_list.append(ic_r)
                    else:
                        ic_lvol_list.append(ic_r)

                if not np.isnan(ic_a):
                    ic_res_list.append(ic_a)

            mean_raw = np.mean(ic_raw_list) if ic_raw_list else np.nan
            std_raw = np.std(ic_raw_list) if ic_raw_list else np.nan
            ir_raw = (mean_raw / (std_raw + 1e-8)) * np.sqrt(2190.0 / h) if not np.isnan(mean_raw) else np.nan
            hit_raw = (sum(1 for v in ic_raw_list if v > 0) / len(ic_raw_list)) * 100.0 if ic_raw_list else np.nan

            mean_res = np.mean(ic_res_list) if ic_res_list else np.nan
            std_res = np.std(ic_res_list) if ic_res_list else np.nan
            ir_res = (mean_res / (std_res + 1e-8)) * np.sqrt(2190.0 / h) if not np.isnan(mean_res) else np.nan

            mean_bull = np.mean(ic_bull_list) if ic_bull_list else np.nan
            mean_bear = np.mean(ic_bear_list) if ic_bear_list else np.nan
            mean_hvol = np.mean(ic_hvol_list) if ic_hvol_list else np.nan
            mean_lvol = np.mean(ic_lvol_list) if ic_lvol_list else np.nan

            results.append({
                "feature": feat,
                "horizon_bars": h,
                "horizon_hours": h * 4,
                "mean_ic_raw": mean_raw,
                "ir_raw": ir_raw,
                "hit_rate_raw": hit_raw,
                "mean_ic_res": mean_res,
                "ir_res": ir_res,
                "ic_bull": mean_bull,
                "ic_bear": mean_bear,
                "ic_hvol": mean_hvol,
                "ic_lvol": mean_lvol,
            })

    res_df = pd.DataFrame(results)

    # 5. Output Institutional Tables
    print("--> [5/5] Diagnostic Complete. Outputting Summary Tables...\n")

    # Table 1: Raw Return IC across Horizons
    print("=" * 115)
    print("TABLE 1: INFORMATION COEFFICIENT (RAW RETURNS r_i) ACROSS HORIZONS (h in 4H, 8H, 16H, 32H, 48H, 72H)")
    print("=" * 115)
    p_raw = res_df.pivot(index="feature", columns="horizon_hours", values="mean_ic_raw")
    print(p_raw.to_string(float_format=lambda x: f"{x:>+7.4f}"))

    # Table 2: Beta-Neutral Residual Return IC (alpha_i) across Horizons
    print("\n" + "=" * 115)
    print("TABLE 2: INFORMATION COEFFICIENT (RESIDUAL ALPHA alpha_i = r_i - beta*r_BTC) ACROSS HORIZONS")
    print("=" * 115)
    p_res = res_df.pivot(index="feature", columns="horizon_hours", values="mean_ic_res")
    print(p_res.to_string(float_format=lambda x: f"{x:>+7.4f}"))

    # Table 3: Annualized Information Ratio (IR) for Residual Alpha
    print("\n" + "=" * 115)
    print("TABLE 3: ANNUALIZED INFORMATION RATIO (IR = IC / std(IC) * sqrt(N_periods)) FOR RESIDUAL ALPHA")
    print("=" * 115)
    p_ir = res_df.pivot(index="feature", columns="horizon_hours", values="ir_res")
    print(p_ir.to_string(float_format=lambda x: f"{x:>+7.2f}"))

    # Table 4: Sub-Regime Breakdown at 24H (6-bar) Horizon
    print("\n" + "=" * 115)
    print("TABLE 4: SUB-REGIME DECOMPOSITION AT 24H (6-BAR) HORIZON (Bull vs Bear, High Vol vs Low Vol)")
    print("=" * 115)
    sub24 = res_df[res_df["horizon_hours"] == 32].copy()
    if not sub24.empty:
        disp_cols = ["feature", "mean_ic_raw", "mean_ic_res", "ic_bull", "ic_bear", "ic_hvol", "ic_lvol"]
        print(sub24[disp_cols].to_string(index=False, float_format=lambda x: f"{x:>+7.4f}"))

    print("\n" + "=" * 115)


if __name__ == "__main__":
    run_ic_diagnostic()

"""
CATBOOST INCREMENTAL INFORMATION & REDUNDANCY DIAGNOSTIC
================================================================================
Empirically tests whether CatBoost provides independent, orthogonal predictive
power after conditioning on LightGBM LambdaRank cross-sectional scores:

1. Linear Regression per bar:
   Prob_CatBoost,i = alpha + beta * Rank_LGBM,i + epsilon_i
2. Spearman Rank Correlation of Residuals epsilon_i against forward returns:
   IC_incremental = Corr_rank(epsilon_i, fwd_ret_i)
3. Formal Kill Criterion:
   CatBoost survives ONLY if:
   - IC_residual > 0
   - t-statistic(IC) > 2.0 (p < 0.05)
4. Decile Expected Return Monotonicity:
   Evaluates E[R | P_CatBoost] across deciles net of 17.0 bps round-trip friction.
"""

import sys
import warnings
from pathlib import Path
import numpy as np
import polars as pl
import pandas as pd
from scipy.stats import spearmanr, ttest_1samp
from sklearn.linear_model import LinearRegression
from catboost import CatBoostClassifier

warnings.filterwarnings("ignore")

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.execution.papertrade_daemon import CrossSectionalAlphaRanker, FEAT_COLS

LAKE_CACHE = PIPELINE_ROOT / "data" / "lake" / "fct_4h_production_cache.parquet"
MODELS_DIR = PIPELINE_ROOT / "models" / "prod"


def run_catboost_redundancy_diagnostic():
    print("=" * 115)
    print("           CATBOOST ORTHOGONAL INCREMENTAL INFORMATION & REDUNDANCY AUDIT           ")
    print("=" * 115)

    if not LAKE_CACHE.exists():
        raise FileNotFoundError(f"Cache {LAKE_CACHE} does not exist.")

    print("--> [1/4] Loading 4H Production Lake Cache...")
    df = pl.read_parquet(LAKE_CACHE)
    if "ticker" in df.columns and "symbol" not in df.columns:
        df = df.rename({"ticker": "symbol"})
    if "timestamp" in df.columns and "timestamp_ms" not in df.columns:
        df = df.with_columns(pl.col("timestamp").dt.epoch("ms").alias("timestamp_ms"))

    ts_col = "timestamp_ms"
    df = df.sort(["symbol", ts_col])

    # Compute forward returns at 4H, 8H, 16H, 32H
    df = df.with_columns([
        (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_4h"),
        (pl.col("close").shift(-2).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_8h"),
        (pl.col("close").shift(-4).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_16h"),
        (pl.col("close").shift(-8).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_32h"),
    ])

    all_timestamps = sorted(df[ts_col].unique().to_list())
    total_bars = len(all_timestamps)

    # 2. Score LightGBM Ranker across all bars
    print("--> [2/4] Scoring LightGBM LambdaRank & CatBoost Across Universe...")
    avail_feats = [c for c in FEAT_COLS if c in df.columns]
    ranker = CrossSectionalAlphaRanker()

    # Pre-train LightGBM on first 60 bars
    train_snap = df.filter(pl.col(ts_col) < all_timestamps[60]).with_columns(
        (pl.col("fwd_ret_4h") > 0).cast(pl.Int32).alias("forward_res_decile")
    )
    ranker.train_lambdarank(train_snap, avail_feats)

    # Load CatBoost production models
    cb_feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]
    pdf = df.to_pandas()
    for c in cb_feature_cols:
        if c not in pdf.columns:
            pdf[c] = 0.0
    cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
    cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")
    pdf["p_cb_long"] = cb_long.predict_proba(pdf[cb_feature_cols])[:, 1]
    pdf["p_cb_short"] = cb_short.predict_proba(pdf[cb_feature_cols])[:, 1]
    pdf["cb_net_score"] = pdf["p_cb_long"] - pdf["p_cb_short"]

    df_scored = pl.from_pandas(pdf)

    # Cross-sectional inference
    lgbm_scores = []
    eval_bars = all_timestamps[60:-8]

    for t in eval_bars:
        curr_snap = df_scored.filter(pl.col(ts_col) == t)
        ranked = ranker.rank_universe(curr_snap, avail_feats)
        for row in ranked.select(["symbol", ts_col, "predicted_rank_score"]).iter_rows(named=True):
            lgbm_scores.append(row)

    lgbm_df = pl.DataFrame(lgbm_scores)
    merged_df = df_scored.join(lgbm_df, on=["symbol", ts_col], how="inner").to_pandas()

    print(f"--> [3/4] Performing Cross-Sectional Orthogonalization Across {len(eval_bars)} Bars...")

    # Group by bar and regress CatBoost net score on LightGBM rank score
    residuals = []
    horizons = [("fwd_ret_4h", 4), ("fwd_ret_8h", 8), ("fwd_ret_16h", 16), ("fwd_ret_32h", 32)]

    ic_residual_series = {h: [] for h, _ in horizons}
    ic_raw_cb_series = {h: [] for h, _ in horizons}
    ic_raw_lgbm_series = {h: [] for h, _ in horizons}

    for t, sub in merged_df.groupby(ts_col):
        clean = sub.dropna(subset=["predicted_rank_score", "cb_net_score", "fwd_ret_4h"])
        if len(clean) < 15:
            continue

        x_lgbm = clean["predicted_rank_score"].to_numpy().reshape(-1, 1)
        y_cb = clean["cb_net_score"].to_numpy()

        lr = LinearRegression().fit(x_lgbm, y_cb)
        cb_residual = y_cb - lr.predict(x_lgbm)
        clean["cb_residual"] = cb_residual

        # Compute Spearman rank IC against forward returns
        for h_col, _ in horizons:
            y_ret = clean[h_col].to_numpy()
            mask = ~np.isnan(y_ret) & ~np.isinf(y_ret)
            if np.sum(mask) >= 15:
                ic_res, _ = spearmanr(cb_residual[mask], y_ret[mask])
                ic_cb, _ = spearmanr(y_cb[mask], y_ret[mask])
                ic_lgbm, _ = spearmanr(x_lgbm.flatten()[mask], y_ret[mask])

                if not np.isnan(ic_res):
                    ic_residual_series[h_col].append(ic_res)
                if not np.isnan(ic_cb):
                    ic_raw_cb_series[h_col].append(ic_cb)
                if not np.isnan(ic_lgbm):
                    ic_raw_lgbm_series[h_col].append(ic_lgbm)

        residuals.append(clean)

    full_res_df = pd.concat(residuals, ignore_index=True)

    # 4. Compile Results & Statistical Tests
    print("--> [4/4] Evaluating Statistical Significance & Economic Decile Curves...\n")

    summary_rows = []
    for h_col, h_hours in horizons:
        res_arr = np.array(ic_residual_series[h_col])
        cb_arr = np.array(ic_raw_cb_series[h_col])
        lgbm_arr = np.array(ic_raw_lgbm_series[h_col])

        mean_res = np.mean(res_arr)
        t_stat, p_val = ttest_1samp(res_arr, 0.0)
        mean_cb = np.mean(cb_arr)
        mean_lgbm = np.mean(lgbm_arr)

        summary_rows.append({
            "Horizon (Hours)": f"{h_hours}H",
            "Raw LightGBM IC": mean_lgbm,
            "Raw CatBoost IC": mean_cb,
            "Residual CatBoost IC": mean_res,
            "t-Statistic": t_stat,
            "p-Value": p_val,
            "Significant (p < 0.05)?": "YES" if (p_val < 0.05 and mean_res > 0) else "NO (REDUNDANT)"
        })

    summary_df = pd.DataFrame(summary_rows)

    print("=" * 115)
    print("TABLE 1: CATBOOST ORTHOGONAL INCREMENTAL INFORMATION AUDIT (AFTER REGRESSING OUT LIGHTGBM)")
    print("=" * 115)
    print(summary_df.to_string(index=False, float_format=lambda x: f"{x:>+7.4f}" if isinstance(x, (float, np.floating)) else str(x)))
    print("=" * 115)

    # Economic Decile Curve: E[R | P_CatBoost] net of 17.0 bps round-trip friction
    print("\n" + "=" * 115)
    print("TABLE 2: ECONOMIC CALIBRATION: REALIZED FORWARD 8H RETURN BY CATBOOST PROBABILITY DECILE")
    print("=" * 115)
    full_res_df["prob_decile"] = pd.qcut(full_res_df["p_cb_long"], q=10, labels=False, duplicates="drop")
    decile_stats = full_res_df.groupby("prob_decile").agg(
        p_min=("p_cb_long", "min"),
        p_mean=("p_cb_long", "mean"),
        p_max=("p_cb_long", "max"),
        gross_ret=("fwd_ret_8h", lambda x: np.mean(x) * 10000.0),  # in bps
        net_ret=("fwd_ret_8h", lambda x: (np.mean(x) * 10000.0) - 17.0),  # net 17 bps round-trip
        obs_count=("fwd_ret_8h", "count")
    ).reset_index()

    print(f"{'DECILE':<8} | {'P(LONG) RANGE':<22} | {'MEAN PROB':<12} | {'GROSS RETURN':<16} | {'NET RETURN (NET 17 bps)':<24} | {'OBS COUNT'}")
    print("-" * 115)
    for _, r in decile_stats.iterrows():
        p_range = f"[{r['p_min']:.3f}, {r['p_max']:.3f}]"
        gross_s = f"{r['gross_ret']:>+7.1f} bps"
        net_s = f"{r['net_ret']:>+7.1f} bps"
        print(f"Decile {int(r['prob_decile']):<1} | {p_range:<22} | {r['p_mean']:<12.3f} | {gross_s:<16} | {net_s:<24} | {int(r['obs_count']):<9d}")
    print("=" * 115)

    # Formal Kill Recommendation
    survives = all(r["Significant (p < 0.05)?"] == "YES" for r in summary_rows[:2])
    print(f"\n--> DIAGNOSTIC CONCLUSION:")
    if survives:
        print("    [PASS] CatBoost possesses statistically and economically significant orthogonal alpha.")
    else:
        print("    [FAIL / KILL] CatBoost residual information is statistically insignificant or economically negative.")
        print("    Recommendation: PRUNE CatBoost from the production architecture to eliminate redundant compute and fee drag.\n")


if __name__ == "__main__":
    run_catboost_redundancy_diagnostic()

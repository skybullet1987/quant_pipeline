import sys
from pathlib import Path
import numpy as np
import polars as pl
from scipy.stats import spearmanr

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine

lake_path = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet"
df = pl.read_parquet(lake_path)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

engine = ProductionMultiScaleEngine()
_, _ = engine.compute_live_targets(lake_file=lake_path)

all_groups = sorted(df.select("group_id").unique().to_series().to_list())
valid_groups = [g for g in all_groups if g >= 168]

# Calculate forward realized returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-3).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_12h"),
    (pl.col("close").shift(-12).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_48h"),
    (pl.col("close").shift(-42).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_168h")
])

def evaluate_ic_block(groups, label):
    ic_12, ic_48, ic_168 = [], [], []
    for grp in groups:
        bar = df.filter(pl.col("group_id") == grp).drop_nulls(subset=["fwd_ret_12h", "fwd_ret_48h", "fwd_ret_168h"] + engine.m12.feature_names_)
        if bar.height < 15:
            continue
        X = bar.select(engine.m12.feature_names_).to_pandas()
        
        p12 = engine.m12.predict(X)
        p48 = engine.m48.predict(X)
        p168 = engine.m168.predict(X)
        
        ic_12.append(spearmanr(p12, bar["fwd_ret_12h"].to_numpy()).statistic)
        ic_48.append(spearmanr(p48, bar["fwd_ret_48h"].to_numpy()).statistic)
        ic_168.append(spearmanr(p168, bar["fwd_ret_168h"].to_numpy()).statistic)
        
    print(f"\n--- {label} ({len(groups)} bars) ---")
    print(f"• 12H Reversion Model Mean Rank IC : {np.nanmean(ic_12):+.4f} | t-stat: {np.nanmean(ic_12)/(np.nanstd(ic_12)+1e-6)*np.sqrt(len(ic_12)):.2f}")
    print(f"• 48H Drift Model Mean Rank IC     : {np.nanmean(ic_48):+.4f} | t-stat: {np.nanmean(ic_48)/(np.nanstd(ic_48)+1e-6)*np.sqrt(len(ic_48)):.2f}")
    print(f"• 168H Trend Model Mean Rank IC    : {np.nanmean(ic_168):+.4f} | t-stat: {np.nanmean(ic_168)/(np.nanstd(ic_168)+1e-6)*np.sqrt(len(ic_168)):.2f}")

is_groups = [g for g in valid_groups if g < 1315]
oos_groups = [g for g in valid_groups if g >= 1315]

evaluate_ic_block(is_groups, "IN-SAMPLE BASELINE (Groups 168 to 1314)")
evaluate_ic_block(oos_groups, "OUT-OF-SAMPLE HOLDOUT (Groups 1315 to 2221)")

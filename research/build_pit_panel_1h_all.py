import polars as pl
import numpy as np
from pathlib import Path
import time

RAW_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "raw" / "klines_1h_full_universe.parquet"
OUT_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_full.parquet"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

if not RAW_PATH.exists():
    print(f"[!] Error: {RAW_PATH} not found. Please run fetch_hyperliquid_1h_all.py first.")
    exit(1)

print(f"[+] Loading raw unconstrained klines from {RAW_PATH}...")
t0 = time.time()
df = pl.read_parquet(RAW_PATH).sort(["symbol", "timestamp_ms"])

# 1. Multi-Horizon Price Returns
print("[+] Generating multi-horizon price returns...")
df = df.with_columns([
    (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_1h"),
    (pl.col("close") / pl.col("close").shift(4).over("symbol") - 1.0).alias("ret_4h"),
    (pl.col("close") / pl.col("close").shift(12).over("symbol") - 1.0).alias("ret_12h"),
    (pl.col("close") / pl.col("close").shift(24).over("symbol") - 1.0).alias("ret_24h"),
    (pl.col("close") / pl.col("close").shift(72).over("symbol") - 1.0).alias("ret_72h"),
])

# 2. Yang-Zhang Realized Volatility Estimator (24h Window)
print("[+] Calculating 24-period Yang-Zhang volatility...")
k = 0.34 / (1.34 + (24 + 1) / (24 - 1))
df = df.with_columns([
    (pl.col("open") / pl.col("close").shift(1).over("symbol")).log().alias("log_oc_prev"),
    (pl.col("close") / pl.col("open")).log().alias("log_co"),
    (pl.col("high") / pl.col("close")).log().alias("log_hc"),
    (pl.col("high") / pl.col("open")).log().alias("log_ho"),
    (pl.col("low") / pl.col("close")).log().alias("log_lc"),
    (pl.col("low") / pl.col("open")).log().alias("log_lo"),
])

df = df.with_columns([
    (pl.col("log_hc") * pl.col("log_ho") + pl.col("log_lc") * pl.col("log_lo")).alias("rs_term")
])

df = df.with_columns([
    pl.col("log_oc_prev").rolling_var(window_size=24).over("symbol").alias("var_open"),
    pl.col("log_co").rolling_var(window_size=24).over("symbol").alias("var_close"),
    pl.col("rs_term").rolling_mean(window_size=24).over("symbol").alias("var_rs"),
])

df = df.with_columns([
    (pl.col("var_open") + k * pl.col("var_close") + (1.0 - k) * pl.col("var_rs")).sqrt().alias("vol_yang_zhang")
])

# 3. Dollar Volume & Volume Z-Score
df = df.with_columns([
    (pl.col("volume") * pl.col("close")).alias("dollar_volume_1h"),
    ((pl.col("volume") - pl.col("volume").rolling_mean(72).over("symbol")) /
     (pl.col("volume").rolling_std(72).over("symbol") + 1e-6)).alias("volume_zscore_72h")
])

# 4. BTC Benchmark Alignment & Rolling Beta
print("[+] Aligning BTC returns and estimating rolling betas...")
btc_df = df.filter(pl.col("symbol") == "BTC").select([
    "timestamp_ms",
    pl.col("ret_1h").alias("btc_ret_1h"),
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("vol_yang_zhang").alias("btc_vol_yz")
]).unique(subset=["timestamp_ms"])

df = df.join(btc_df, on="timestamp_ms", how="left")

cov_df = df.with_columns([
    (pl.col("ret_1h") * pl.col("btc_ret_1h")).alias("xy_ret"),
    (pl.col("btc_ret_1h") ** 2).alias("x2_ret")
]).with_columns([
    (pl.col("xy_ret").rolling_mean(72).over("symbol") /
     (pl.col("x2_ret").rolling_mean(72).over("symbol") + 1e-8)).clip(0.0, 3.0).alias("beta_btc")
])

# 5. Discrete Group IDs
unique_ts = cov_df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
    pl.int_range(0, pl.len()).alias("group_id")
)
final_df = cov_df.join(unique_ts, on="timestamp_ms", how="left").sort(["group_id", "symbol"])

final_df.write_parquet(OUT_PATH)
file_mb = OUT_PATH.stat().st_size / (1024 * 1024)
print(f"\n[+] Feature lake assembled -> {OUT_PATH} ({file_mb:.2f} MB)")
print(f"• Total Feature Rows : {final_df.height:,}")
print(f"• Active Symbols     : {final_df['symbol'].n_unique()}")
print(f"• Total Groups (1H)  : {final_df['group_id'].max():,}")
print(f"• Build Elapsed Time : {time.time() - t0:.1f}s")

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Tuple, List, Dict

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

import polars as pl

LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"

FEATURE_COLS = [
    'ret_4h', 'ret_24h', 'ret_72h', 'ret_168h', 
    'volume_zscore_72h', 'basis_spread', 'vol_yang_zhang', 'beta_btc'
]

def load_and_prepare_panel() -> Tuple[pl.DataFrame, List[int], Dict[int, str]]:
    print("[INIT] Loading PIT Feature Lake...")
    df = pl.read_parquet(LAKE_FILE)

    # Compute 14-period ATR on the fly if missing from lake
    if "atr_14" not in df.columns:
        prev_c = pl.col("close").shift(1).over("symbol")
        tr1 = pl.col("high") - pl.col("low")
        tr2 = (pl.col("high") - prev_c).abs()
        tr3 = (pl.col("low") - prev_c).abs()
        tr = pl.max_horizontal([tr1, tr2, tr3]).fill_null(tr1)
        df = df.with_columns(
            tr.rolling_mean(window_size=14).over("symbol").fill_null(tr1).alias("atr_14")
        )

    # Forward returns & beta-adjusted alpha targets
    df = df.with_columns([
        (pl.col("close").shift(-3).over("symbol") / pl.col("close")).log().alias("fwd_ret_12h"),
        (pl.col("close").shift(-12).over("symbol") / pl.col("close")).log().alias("fwd_ret_48h"),
        (pl.col("close").shift(-42).over("symbol") / pl.col("close")).log().alias("fwd_ret_168h"),
    ])
    btc_targets = df.filter(pl.col("symbol") == "BTC").select([
        "timestamp_ms",
        pl.col("fwd_ret_12h").alias("btc_fwd_12h"),
        pl.col("fwd_ret_48h").alias("btc_fwd_48h"),
        pl.col("fwd_ret_168h").alias("btc_fwd_168h"),
    ])
    df = df.join(btc_targets, on="timestamp_ms", how="left").with_columns([
        ((pl.col("fwd_ret_12h") - (pl.col("beta_btc") * pl.col("btc_fwd_12h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_12h_alpha"),
        ((pl.col("fwd_ret_48h") - (pl.col("beta_btc") * pl.col("btc_fwd_48h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_48h_drift"),
        ((pl.col("fwd_ret_168h") - (pl.col("beta_btc") * pl.col("btc_fwd_168h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_168h_trend")
    ]).drop_nulls(subset=FEATURE_COLS + ["target_12h_alpha", "target_48h_drift", "target_168h_trend", "atr_14"])

    unique_ts = sorted(df.select("timestamp_ms").to_series().unique().to_list())
    ts_to_grp = {ts: idx for idx, ts in enumerate(unique_ts)}
    grp_to_ts = {idx: datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") for ts, idx in ts_to_grp.items()}
    df = df.with_columns(pl.col("timestamp_ms").replace(ts_to_grp).alias("group_id")).sort(["group_id", "symbol"])
    return df, unique_ts, grp_to_ts

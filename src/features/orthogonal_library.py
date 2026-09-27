"""
Vectorized Orthogonal Quantitative Feature Library for Hyperliquid Perpetuals.
Implements Cross-Sectional Alpha, Beta-Decoupling, Squeeze Geometry, 
Intrabar Microstructure, and Non-Linear Economic Interactions.
"""
import numpy as np
import polars as pl


def compute_orthogonal_features(df: pl.DataFrame) -> pl.DataFrame:
    """Computes orthogonal feature families across the multi-asset 4H panel."""
    print("Computing Family 1 & 6: Returns, Multi-horizon Rankings, and Intrabar Microstructure...")
    
    # 1. Base log returns and Intrabar Candle Geometry
    base_df = (
        df.sort(["symbol", "bucket_timestamp_utc"])
        .with_columns([
            pl.col("close").log().diff().over("symbol").alias("log_ret_4h"),
            pl.col("close").pct_change(6).over("symbol").alias("ret_24h"),
            pl.col("close").pct_change(18).over("symbol").alias("ret_72h"),
            pl.col("close").pct_change(42).over("symbol").alias("ret_168h"),
            pl.col("close").pct_change(6).shift(-6).over("symbol").alias("fwd_ret_24h"),
            
            # Intrabar Microstructure (Family 6)
            (pl.col("high") - pl.col("low") + 1e-8).alias("range_4h"),
            ((2.0 * pl.col("close") - pl.col("high") - pl.col("low")) / (pl.col("high") - pl.col("low") + 1e-8))
                .clip(-1.0, 1.0).alias("clv_4h"),
            (pl.max_horizontal("open", "close")).alias("body_upper"),
            (pl.min_horizontal("open", "close")).alias("body_lower"),
        ])
        .with_columns([
            ((pl.col("high") - pl.col("body_upper")) / pl.col("range_4h")).clip(0.0, 1.0).alias("upper_wick_ratio_4h"),
            ((pl.col("body_lower") - pl.col("low")) / pl.col("range_4h")).clip(0.0, 1.0).alias("lower_wick_absorption_ratio_4h"),
            ((pl.col("close") - pl.col("open")).abs() / pl.col("range_4h")).clip(0.0, 1.0).alias("body_to_range_4h"),
        ])
        .with_columns([
            (pl.col("upper_wick_ratio_4h") - pl.col("lower_wick_absorption_ratio_4h")).alias("intrabar_wick_imbalance_4h")
        ])
    )

    print("Computing Family 1 & 7: Cross-Sectional Percentiles & Volume Dynamics...")
    # 2. Cross-sectional ranking per timestamp
    cs_df = (
        base_df
        .with_columns([
            pl.col("ret_24h").rank("ordinal").over("bucket_timestamp_utc").alias("rank_24h_raw"),
            pl.col("ret_72h").rank("ordinal").over("bucket_timestamp_utc").alias("rank_72h_raw"),
            pl.col("ret_168h").rank("ordinal").over("bucket_timestamp_utc").alias("rank_168h_raw"),
            pl.col("volume").rank("ordinal").over("bucket_timestamp_utc").alias("rank_vol_raw"),
            pl.len().over("bucket_timestamp_utc").alias("n_tokens"),
        ])
        .with_columns([
            ((pl.col("rank_24h_raw") - 1.0) / (pl.col("n_tokens") - 1.0 + 1e-8)).clip(0.0, 1.0).alias("cs_rank_ret_24h"),
            ((pl.col("rank_72h_raw") - 1.0) / (pl.col("n_tokens") - 1.0 + 1e-8)).clip(0.0, 1.0).alias("cs_rank_ret_72h"),
            ((pl.col("rank_168h_raw") - 1.0) / (pl.col("n_tokens") - 1.0 + 1e-8)).clip(0.0, 1.0).alias("cs_rank_ret_7d"),
            ((pl.col("rank_vol_raw") - 1.0) / (pl.col("n_tokens") - 1.0 + 1e-8)).clip(0.0, 1.0).alias("cs_rank_volume_pct_24h"),
            (pl.col("ret_24h") - pl.col("ret_24h").median().over("bucket_timestamp_utc")).alias("cs_dist_to_universe_median_24h"),
        ])
        .with_columns([
            (pl.col("cs_rank_ret_24h") - pl.col("cs_rank_ret_72h")).alias("cs_mom_acceleration_24_72")
        ])
    )

    print("Computing Family 5: Volatility Geometry & Squeeze Dynamics...")
    # 3. Garman-Klass, Bollinger/Keltner Squeeze & NATR
    gk_part = 0.5 * ((pl.col("high") / pl.col("low")).log() ** 2) - (2.0 * np.log(2) - 1.0) * ((pl.col("close") / pl.col("open")).log() ** 2)
    
    vol_df = (
        cs_df
        .with_columns([
            gk_part.alias("gk_bar"),
            (pl.max_horizontal(
                pl.col("high") - pl.col("low"),
                (pl.col("high") - pl.col("close").shift(1).over("symbol")).abs(),
                (pl.col("low") - pl.col("close").shift(1).over("symbol")).abs()
            )).alias("tr_bar"),
            pl.col("log_ret_4h").rolling_std(window_size=6).over("symbol").alias("c2c_vol_6"),
            pl.col("log_ret_4h").rolling_std(window_size=20).over("symbol").alias("c2c_vol_20"),
        ])
        .with_columns([
            (pl.col("gk_bar").rolling_mean(window_size=6).over("symbol").sqrt() / (pl.col("c2c_vol_6") + 1e-8)).alias("garman_klass_vol_ratio_24h"),
            pl.col("tr_bar").rolling_mean(window_size=6).over("symbol").alias("atr_6"),
            pl.col("tr_bar").rolling_mean(window_size=20).over("symbol").alias("atr_20"),
        ])
        .with_columns([
            (pl.col("atr_6") / (pl.col("close") + 1e-8)).alias("normalized_atr_24h"),
            ((4.0 * pl.col("c2c_vol_20")) / (3.0 * (pl.col("atr_20") / pl.col("close")) + 1e-8)).clip(0.2, 3.0).alias("bollinger_keltner_squeeze_ratio_20"),
        ])
    )

    print("Computing Family 2: Beta-Decoupled Residuals against BTC...")
    # 4. Extract BTC baseline returns
    btc_df = (
        vol_df.filter(pl.col("symbol") == "BTC")
        .select(["bucket_timestamp_utc", pl.col("log_ret_4h").alias("btc_ret_4h"), pl.col("ret_24h").alias("btc_ret_24h")])
    )

    merged_df = vol_df.join(btc_df, on="bucket_timestamp_utc", how="left")

    # Vectorized Rolling Beta to BTC (42 bars = 7d)
    cov_btc = (
        (merged_df["log_ret_4h"] * merged_df["btc_ret_4h"])
        .to_frame("prod")
        .with_columns(merged_df["symbol"])
        .select(pl.col("prod").rolling_mean(42).over("symbol"))
    )["prod"]
    var_btc = (
        (merged_df["btc_ret_4h"] ** 2)
        .to_frame("var")
        .with_columns(merged_df["symbol"])
        .select(pl.col("var").rolling_mean(42).over("symbol"))
    )["var"]

    beta_7d = (cov_btc / (var_btc + 1e-8)).clip(-0.5, 3.5)

    final_df = (
        merged_df
        .with_columns([
            beta_7d.alias("beta_btc_7d"),
        ])
        .with_columns([
            (pl.col("ret_24h") - pl.col("beta_btc_7d") * pl.col("btc_ret_24h")).alias("idio_residual_ret_btc_24h"),
            (pl.col("close") / (merged_df["close"] + 1e-8)).alias("synth_btc_ratio"),
        ])
        .with_columns([
            # Family 8: Non-Linear Economic Interactions
            (pl.col("cs_rank_ret_24h") * (1.0 / (pl.col("bollinger_keltner_squeeze_ratio_20") + 1e-8))).alias("interaction_mom_squeeze_24h"),
            (pl.col("clv_4h") * pl.col("cs_rank_volume_pct_24h")).alias("interaction_breakout_thrust"),
            (pl.col("idio_residual_ret_btc_24h") / (pl.col("garman_klass_vol_ratio_24h") + 1e-8)).alias("interaction_tbm_score"),
        ])
    )

    return final_df

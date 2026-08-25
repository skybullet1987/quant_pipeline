import polars as pl
import numpy as np

class FeatureEngineeringEngine:
    def __init__(self, forward_horizon_bars: int = 6, lookback_bars: int = 120):
        self.forward_horizon = forward_horizon_bars
        self.lookback = lookback_bars

    def compute_ohlcv_features(self, df: pl.DataFrame) -> pl.DataFrame:
        return (
            df.sort(["ticker", "timestamp"])
            .with_columns([
                # Garman-Klass Volatility per bar
                (0.5 * (pl.col("high").log() - pl.col("low").log()).pow(2) - 
                 (2 * np.log(2) - 1) * (pl.col("close").log() - pl.col("open").log()).pow(2)
                ).sqrt().alias("gk_vol_bar"),
                (pl.col("close") / pl.col("close").shift(1).over("ticker") - 1.0).alias("ret_1b"),
                (pl.col("close") / pl.col("close").shift(6).over("ticker") - 1.0).alias("mom_24h"),
                (pl.col("close") / pl.col("close").shift(42).over("ticker") - 1.0).alias("mom_7d"),
                ((pl.col("high") - pl.col("low")) / pl.col("close"))
                .rolling_mean(window_size=20)
                .over("ticker")
                .alias("atr_pct_20"),
            ])
            .with_columns([
                pl.col("gk_vol_bar").rolling_mean(window_size=20).over("ticker").sqrt().alias("gk_vol_20p"),
                ((pl.col("close") - pl.col("high").rolling_max(window_size=self.lookback).over("ticker")) /
                 pl.col("high").rolling_max(window_size=self.lookback).over("ticker")).alias("dist_to_120p_high")
            ])
            .with_columns([
                (pl.col("gk_vol_20p") / 
                 (pl.col("gk_vol_20p").rolling_min(window_size=self.lookback).over("ticker") + 1e-8)
                ).alias("vol_compression_ratio")
            ])
        )

    def residualize_against_market(self, df: pl.DataFrame) -> pl.DataFrame:
        benchmarks = (
            df.filter(pl.col("ticker").is_in(["BTCUSD", "ETHUSD", "BTC", "ETH", "BTCUSDT", "ETHUSDT"]))
            .pivot(index="timestamp", on="ticker", values="ret_1b")
        )
        
        non_ts = [c for c in benchmarks.columns if c != "timestamp"]
        btc_col = next((c for c in non_ts if "BTC" in c), non_ts[0] if non_ts else "timestamp")
        eth_col = next((c for c in non_ts if "ETH" in c), non_ts[1] if len(non_ts) > 1 else btc_col)
        
        benchmarks = benchmarks.rename({btc_col: "ret_btc", eth_col: "ret_eth"}).select(["timestamp", "ret_btc", "ret_eth"])
        df_merged = df.join(benchmarks, on="timestamp", how="left")

        return (
            df_merged.with_columns([
                (pl.rolling_cov(pl.col("ret_1b"), pl.col("ret_btc"), window_size=60).over("ticker") /
                 (pl.col("ret_btc").rolling_var(window_size=60).over("ticker") + 1e-8)).fill_null(1.0).alias("beta_btc"),
                (pl.rolling_cov(pl.col("ret_1b"), pl.col("ret_eth"), window_size=60).over("ticker") /
                 (pl.col("ret_eth").rolling_var(window_size=60).over("ticker") + 1e-8)).fill_null(0.0).alias("beta_eth")
            ])
            .with_columns([
                (pl.col("ret_1b") - 
                 (pl.col("beta_btc") * pl.col("ret_btc").fill_null(0.0) + 
                  pl.col("beta_eth") * pl.col("ret_eth").fill_null(0.0))
                ).alias("ret_residual_1b")
            ])
            .with_columns([
                (pl.col("ret_residual_1b").rolling_sum(window_size=self.forward_horizon).over("ticker") /
                 (pl.col("ret_residual_1b").rolling_std(window_size=60).over("ticker") * np.sqrt(self.forward_horizon) + 1e-8)
                ).fill_null(0.0).alias("residual_momentum_zscore")
            ])
        )

    def construct_ranking_targets(self, df: pl.DataFrame) -> pl.DataFrame:
        return (
            df.with_columns([
                (pl.col("close").shift(-self.forward_horizon).over("ticker") / pl.col("close") - 1.0).alias("fwd_ret_raw"),
                (pl.col("ret_btc").rolling_sum(window_size=self.forward_horizon).shift(-self.forward_horizon).over("ticker")).alias("fwd_ret_btc")
            ])
            .with_columns([
                (pl.col("fwd_ret_raw") - pl.col("beta_btc") * pl.col("fwd_ret_btc").fill_null(0.0)).alias("fwd_residual_ret")
            ])
            .with_columns([
                # Normalized Rank Scaled to 0..4 (LambdaRank Quintile Targets)
                ((pl.col("fwd_residual_ret").rank().over("timestamp") - 1) /
                 (pl.col("fwd_residual_ret").count().over("timestamp") + 1e-8) * 5)
                .floor()
                .clip(0, 4)
                .cast(pl.Int32)
                .alias("ranking_target")
            ])
        )

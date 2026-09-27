"""
RESIDUAL ALPHA & BETA-NEUTRAL CROSS-SECTIONAL ENGINE
================================================================================
Extracts idiosyncratic alpha by decomposing asset returns against Bitcoin market beta:
    r_i(t) = beta_i(t) * r_BTC(t) + alpha_i(t) + epsilon_i(t)

Incorporates findings from the Institutional Signal Decay Diagnostic:
1. Low-Volatility Premium (Garman-Klass vol has negative IC: -0.08 to -0.09)
2. Coiling / Squeeze Status (Bollinger Bandwidth has negative IC: -0.045)
3. Beta-Neutral Residual Momentum (ResMom = Mom_i - beta_i * Mom_BTC)
4. Model Meta-Confirmation (CatBoost net probability differential)
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import polars as pl
import pandas as pd


class ResidualAlphaEngine:
    def __init__(
        self,
        beta_lookback_bars: int = 60,
        beta_min: float = 0.10,
        beta_max: float = 3.00,
        weight_res_mom: float = 0.30,
        weight_low_vol: float = 0.30,
        weight_coiling: float = 0.20,
        weight_model_net: float = 0.20,
    ):
        self.beta_lookback_bars = beta_lookback_bars
        self.beta_min = beta_min
        self.beta_max = beta_max
        self.w_res_mom = weight_res_mom
        self.w_low_vol = weight_low_vol
        self.w_coiling = weight_coiling
        self.w_model_net = weight_model_net

    def estimate_betas(
        self,
        panel_df: pl.DataFrame,
        ts_col: str = "timestamp_ms",
        symbol_col: str = "symbol",
        ret_col: str = "ret_4h",
        btc_symbol: str = "BTC",
    ) -> pl.DataFrame:
        """
        Computes rolling 60-bar beta of each asset against BTC using Polars/Pandas.
        """
        pdf = panel_df.select([ts_col, symbol_col, ret_col]).to_pandas()
        pdf = pdf.sort_values([symbol_col, ts_col])

        # Extract BTC series
        btc_pdf = pdf[pdf[symbol_col] == btc_symbol][[ts_col, ret_col]].rename(
            columns={ret_col: "btc_ret"}
        ).drop_duplicates(subset=[ts_col])

        pdf = pdf.merge(btc_pdf, on=ts_col, how="left")
        pdf["btc_ret"] = pdf["btc_ret"].fillna(0.0)

        def _calc_beta(group):
            cov = group[ret_col].rolling(self.beta_lookback_bars, min_periods=20).cov(group["btc_ret"])
            var = group["btc_ret"].rolling(self.beta_lookback_bars, min_periods=20).var()
            beta = (cov / (var + 1e-8)).clip(self.beta_min, self.beta_max).fillna(1.0)
            group["beta_btc"] = beta
            return group

        pdf = pdf.groupby(symbol_col, group_keys=False).apply(_calc_beta)
        beta_df = pl.from_pandas(pdf[[ts_col, symbol_col, "beta_btc"]])
        return beta_df

    def compute_residual_alpha(
        self,
        snapshot_df: pl.DataFrame,
        btc_ret_snapshot: float = 0.0,
    ) -> pl.DataFrame:
        """
        Computes standardized cross-sectional residual alpha score for a single time bar snapshot.
        """
        df = snapshot_df.clone()

        if "beta_btc" not in df.columns:
            df = df.with_columns(pl.lit(1.0).alias("beta_btc"))

        # 1. Residual Momentum (stripped of BTC return)
        if "mom_24h" in df.columns:
            df = df.with_columns(
                (pl.col("mom_24h") - pl.col("beta_btc") * (btc_ret_snapshot * 6.0)).alias("res_mom")
            )
        else:
            df = df.with_columns(pl.lit(0.0).alias("res_mom"))

        # 2. Low Volatility Signal (inverted Garman-Klass volatility, since IC is -0.09)
        if "gk_vol_20p" in df.columns:
            df = df.with_columns(
                (-pl.col("gk_vol_20p")).alias("low_vol_signal")
            )
        elif "vol_yang_zhang" in df.columns:
            df = df.with_columns(
                (-pl.col("vol_yang_zhang")).alias("low_vol_signal")
            )
        else:
            df = df.with_columns(pl.lit(0.0).alias("low_vol_signal"))

        # 3. Coiling / Bandwidth Compression (inverted BBW, since IC is -0.045)
        if "bbw_pct_40" in df.columns:
            df = df.with_columns(
                (-pl.col("bbw_pct_40")).alias("coiling_signal")
            )
        else:
            df = df.with_columns(pl.lit(0.0).alias("coiling_signal"))

        # 4. Model Net Probability Score (p_long - p_short)
        if "catboost_long_score" in df.columns and "catboost_short_score" in df.columns:
            df = df.with_columns(
                (pl.col("catboost_long_score") - pl.col("catboost_short_score")).alias("model_net_score")
            )
        elif "catboost_net_score" in df.columns:
            df = df.with_columns(pl.col("catboost_net_score").alias("model_net_score"))
        else:
            df = df.with_columns(pl.lit(0.0).alias("model_net_score"))

        # Cross-sectional Z-score helper
        def _zscore(col_name: str) -> pl.Expr:
            mean = pl.col(col_name).mean()
            std = pl.col(col_name).std()
            return pl.when(std > 1e-6).then((pl.col(col_name) - mean) / std).otherwise(0.0)

        df = df.with_columns([
            _zscore("res_mom").clip(-3.0, 3.0).alias("z_res_mom"),
            _zscore("low_vol_signal").clip(-3.0, 3.0).alias("z_low_vol"),
            _zscore("coiling_signal").clip(-3.0, 3.0).alias("z_coiling"),
            _zscore("model_net_score").clip(-3.0, 3.0).alias("z_model_net"),
        ])

        # Composite Residual Alpha Score
        composite_expr = (
            self.w_res_mom * pl.col("z_res_mom") +
            self.w_low_vol * pl.col("z_low_vol") +
            self.w_coiling * pl.col("z_coiling") +
            self.w_model_net * pl.col("z_model_net")
        )

        df = df.with_columns(composite_expr.alias("residual_alpha_score"))
        return df.sort("residual_alpha_score", descending=True)

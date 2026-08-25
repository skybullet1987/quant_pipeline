import polars as pl
import numpy as np

class ContinuousRiskGovernor:
    @staticmethod
    def compute_exposure_scalar(bar_df: pl.DataFrame) -> float:
        breadth = (bar_df["close"] > bar_df["close"].shift(20)).mean() or 0.50
        csd = bar_df["mom_24h"].std() or 0.02
        vol_zscore = bar_df["gk_vol_20p"].mean() or 0.0

        latent_risk = (2.5 * (breadth - 0.50)) + (10.0 * (csd - 0.02)) - (1.5 * vol_zscore)
        omega = 1.0 / (1.0 + np.exp(-latent_risk))
        return float(np.clip(omega, 0.20, 1.00))

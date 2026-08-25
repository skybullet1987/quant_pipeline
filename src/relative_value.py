from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Any, Dict, List

class CrossSectionalRelativeValueEngine:
    def __init__(
        self,
        lookback_bars: int = 210,
        momentum_horizon_bars: int = 6,
        gross_leverage: float = 2.5
    ) -> None:
        self.lookback = lookback_bars
        self.horizon = momentum_horizon_bars
        self.gross_leverage = gross_leverage

    def compute_residual_momentum(
        self,
        returns_df: pd.DataFrame
    ) -> pd.DataFrame:
        if returns_df.empty:
            return pd.DataFrame()

        btc_col = next((c for c in returns_df.columns if c in ("BTC", "kBTC", "BTC-PERP")), None)
        eth_col = next((c for c in returns_df.columns if c in ("ETH", "kETH", "ETH-PERP")), None)

        if not btc_col or not eth_col:
            benchmarks = returns_df.columns[:2].tolist()
            btc_col, eth_col = benchmarks[0], benchmarks[1]

        assets = [c for c in returns_df.columns if c not in (btc_col, eth_col)]
        avail_bars = min(len(returns_df), self.lookback)
        if avail_bars < 18:
            return pd.DataFrame()

        horizon = min(self.horizon, max(avail_bars // 3, 2))
        r_market = returns_df[[btc_col, eth_col]].iloc[-avail_bars:].values
        X = np.column_stack([np.ones(avail_bars), r_market])
        X_t = X.T

        try:
            beta_hat_inv = np.linalg.pinv(X_t @ X) @ X_t
        except Exception:
            return pd.DataFrame()

        records = []
        dof = max(avail_bars - 3, 1)

        for asset in assets:
            y = returns_df[asset].iloc[-avail_bars:].values
            if len(y) < avail_bars or np.isnan(y).any():
                continue

            params = beta_hat_inv @ y
            predicted = X @ params
            residuals = y - predicted

            sigma_eps = float(np.sqrt(np.sum(residuals**2) / dof))
            cum_residual = float(np.sum(residuals[-horizon:]))
            res_mom = float(cum_residual / (sigma_eps * np.sqrt(horizon) + 1e-8))

            records.append({
                "coin": asset,
                "res_mom": res_mom,
                "sigma_eps": sigma_eps,
                "beta_btc": float(params[1]),
                "beta_eth": float(params[2])
            })

        return pd.DataFrame(records)

    def generate_market_neutral_basket(
        self,
        metrics_df: pd.DataFrame,
        equity_usd: float
    ) -> Dict[str, Any]:
        if metrics_df.empty or len(metrics_df) < 4:
            return {}

        sorted_df = metrics_df.sort_values(by="res_mom", ascending=False).reset_index(drop=True)
        long_leg = sorted_df.iloc[:2].copy()
        short_leg = sorted_df.iloc[-2:].copy()

        long_leg["inv_vol"] = 1.0 / (long_leg["sigma_eps"] + 1e-8)
        long_leg["weight"] = (long_leg["inv_vol"] / long_leg["inv_vol"].sum()) * (self.gross_leverage / 2.0)
        long_leg["notional_usd"] = long_leg["weight"] * equity_usd

        short_leg["inv_vol"] = 1.0 / (short_leg["sigma_eps"] + 1e-8)
        short_leg["weight"] = -(short_leg["inv_vol"] / short_leg["inv_vol"].sum()) * (self.gross_leverage / 2.0)
        short_leg["notional_usd"] = short_leg["weight"] * equity_usd

        net_beta_btc = float(
            np.sum(long_leg["weight"] * long_leg["beta_btc"]) +
            np.sum(short_leg["weight"] * short_leg["beta_btc"])
        )

        return {
            "long_basket": long_leg[["coin", "weight", "notional_usd", "beta_btc"]].to_dict(orient="records"),
            "short_basket": short_leg[["coin", "weight", "notional_usd", "beta_btc"]].to_dict(orient="records"),
            "net_market_exposure": float(long_leg["weight"].sum() + short_leg["weight"].sum()),
            "portfolio_beta_btc": net_beta_btc,
            "gross_leverage": float(self.gross_leverage)
        }

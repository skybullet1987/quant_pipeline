from typing import Dict, Any
import polars as pl

class DollarNeutralPortfolioAllocator:
    def __init__(self, top_quantile: float = 0.15, max_gross_leverage: float = 2.0):
        self.top_q = top_quantile
        self.base_leverage = max_gross_leverage

    def generate_orders(
        self,
        df_scored: pl.DataFrame,
        equity_usd: float,
        macro_omega: float
    ) -> Dict[str, Any]:
        sorted_df = df_scored.sort("predicted_rank_score", descending=True)
        n_assets = len(sorted_df)
        k_assets = max(int(n_assets * self.top_q), 2)

        long_candidates = sorted_df.head(k_assets)
        short_candidates = sorted_df.tail(k_assets)

        effective_gross_leverage = self.base_leverage * macro_omega
        half_gross = (equity_usd * effective_gross_leverage) / 2.0

        # Long Leg (Inverse volatility parity)
        long_inv_vol = 1.0 / (long_candidates["gk_vol_20p"] + 1e-5)
        long_weights = long_inv_vol / long_inv_vol.sum()
        long_notionals = long_weights * half_gross

        # Short Leg (Inverse volatility parity)
        short_inv_vol = 1.0 / (short_candidates["gk_vol_20p"] + 1e-5)
        short_weights = short_inv_vol / short_inv_vol.sum()
        short_notionals = short_weights * half_gross

        long_basket = [
            {"ticker": t, "side": "BUY", "notional_usd": float(n), "price": float(p)}
            for t, n, p in zip(long_candidates["ticker"], long_notionals, long_candidates["close"])
        ]
        short_basket = [
            {"ticker": t, "side": "SELL", "notional_usd": float(n), "price": float(p)}
            for t, n, p in zip(short_candidates["ticker"], short_notionals, short_candidates["close"])
        ]

        net_notional = float(long_notionals.sum() - short_notionals.sum())

        return {
            "macro_omega": macro_omega,
            "effective_gross_leverage": effective_gross_leverage,
            "net_dollar_exposure": net_notional,
            "long_basket": long_basket,
            "short_basket": short_basket
        }

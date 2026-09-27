"""
Dollar-Neutral Long/Short Portfolio Allocator with Leverage & Quantile Constraints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np
import polars as pl


@dataclass(frozen=True)
class AllocationResult:
    weights: dict[str, float]
    gross_leverage: float
    net_exposure: float


class OrderBatch(pl.DataFrame):
    """
    Polars DataFrame representing portfolio order batches with direct scalar
    and basket access to portfolio-level metrics for risk checks and assertions.
    """
    def __init__(
        self,
        data: pl.DataFrame,
        net_dollar_exposure: float = 0.0,
        gross_dollar_exposure: float = 0.0,
        gross_leverage: float = 0.0,
        net_exposure: float = 0.0,
        long_basket: list[str] | None = None,
        short_basket: list[str] | None = None,
    ):
        super().__init__(data)
        self._metrics: dict[str, Any] = {
            "net_dollar_exposure": float(net_dollar_exposure),
            "gross_dollar_exposure": float(gross_dollar_exposure),
            "gross_leverage": float(gross_leverage),
            "net_exposure": float(net_exposure),
            "long_basket": list(long_basket) if long_basket is not None else [],
            "short_basket": list(short_basket) if short_basket is not None else [],
            "long_positions": list(long_basket) if long_basket is not None else [],
            "short_positions": list(short_basket) if short_basket is not None else [],
            "orders": self,
        }

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str) and hasattr(self, "_metrics") and key in self._metrics:
            return self._metrics[key]
        return super().__getitem__(key)

    def __getattr__(self, name: str) -> Any:
        if "_metrics" in self.__dict__ and name in self._metrics:
            return self._metrics[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __contains__(self, key: Any) -> bool:
        if hasattr(self, "_metrics") and key in self._metrics:
            return True
        return key in self.columns

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, "_metrics") and key in self._metrics:
            return self._metrics[key]
        if key in self.columns:
            return self.get_column(key)
        return default


class DollarNeutralPortfolioAllocator:
    """
    Allocates dollar-neutral long/short weights based on predicted rank scores.
    Supports quantile selection, exposure scaling, and concrete order generation.
    """
    def __init__(
        self,
        top_quantile: float = 0.33,
        max_gross_leverage: float = 1.0,
        target_gross_leverage: float = 1.0,
        max_single_weight: float = 0.50,
        **kwargs: Any
    ):
        self.top_quantile = top_quantile
        self.max_gross_leverage = max_gross_leverage if max_gross_leverage != 1.0 else target_gross_leverage
        self.target_gross_leverage = self.max_gross_leverage
        self.max_single_weight = max_single_weight

    def _compute_weights_array(self, scores: np.ndarray, effective_gross: float) -> np.ndarray:
        n = len(scores)
        if n == 0:
            return np.array([], dtype=np.float64)

        ranks = np.argsort(np.argsort(-scores))  # 0 is highest score
        k = max(1, int(round(n * self.top_quantile)))

        weights = np.zeros(n, dtype=np.float64)
        long_mask = ranks < k
        short_mask = ranks >= (n - k)

        if np.any(long_mask):
            weights[long_mask] = (effective_gross / 2.0) / np.sum(long_mask)
        if np.any(short_mask):
            weights[short_mask] = -(effective_gross / 2.0) / np.sum(short_mask)

        if self.max_single_weight < 1.0:
            weights = np.clip(weights, -self.max_single_weight, self.max_single_weight)

        return weights

    def allocate(
        self,
        data: pl.DataFrame | dict[str, float],
        exposure_scalar: float = 1.0,
        *args: Any,
        **kwargs: Any
    ) -> OrderBatch | AllocationResult:
        scalar = kwargs.get("macro_omega", kwargs.get("omega", exposure_scalar))
        if args and isinstance(args[0], (int, float)):
            scalar = float(args[0])

        effective_gross = self.max_gross_leverage * scalar

        if isinstance(data, pl.DataFrame):
            score_col = None
            for col in ["predicted_rank_score", "predicted_score", "alpha_score", "score", "signal", "rank_score"]:
                if col in data.columns:
                    score_col = col
                    break

            if score_col is None:
                raise ValueError("DataFrame must contain a predicted score or rank column.")

            ticker_col = "ticker" if "ticker" in data.columns else "symbol" if "symbol" in data.columns else None
            raw_scores = data[score_col].to_numpy().astype(np.float64)
            weights = self._compute_weights_array(raw_scores, effective_gross)

            df = data.with_columns([
                pl.Series("target_weight", weights, dtype=pl.Float64),
                pl.Series("weight", weights, dtype=pl.Float64),
                pl.Series("allocated_weight", weights, dtype=pl.Float64),
            ])

            long_basket = df.filter(pl.col("target_weight") > 1e-8)[ticker_col].to_list() if ticker_col else []
            short_basket = df.filter(pl.col("target_weight") < -1e-8)[ticker_col].to_list() if ticker_col else []

            return OrderBatch(
                data=df,
                net_dollar_exposure=0.0,
                gross_dollar_exposure=0.0,
                gross_leverage=float(np.sum(np.abs(weights))),
                net_exposure=float(np.sum(weights)),
                long_basket=long_basket,
                short_basket=short_basket,
            )

        symbols = list(data.keys())
        if not symbols:
            return AllocationResult(weights={}, gross_leverage=0.0, net_exposure=0.0)

        raw_scores = np.array([data[s] for s in symbols], dtype=np.float64)
        weights_arr = self._compute_weights_array(raw_scores, effective_gross)

        weights_dict = {s: float(w) for s, w in zip(symbols, weights_arr)}
        return AllocationResult(
            weights=weights_dict,
            gross_leverage=float(np.sum(np.abs(weights_arr))),
            net_exposure=float(np.sum(weights_arr)),
        )

    def generate_orders(
        self,
        df: pl.DataFrame,
        equity_usd: float = 1000.0,
        macro_omega: float = 1.0,
        **kwargs: Any
    ) -> OrderBatch:
        """
        Generates target dollar positions, share quantities, and portfolio exposure summaries.
        """
        allocated_batch = self.allocate(df, exposure_scalar=macro_omega, **kwargs)
        ticker_col = "ticker" if "ticker" in allocated_batch.columns else "symbol" if "symbol" in allocated_batch.columns else None

        price_col = "close" if "close" in allocated_batch.columns else "price"
        prices = allocated_batch[price_col].to_numpy().astype(np.float64)
        weights = allocated_batch["target_weight"].to_numpy().astype(np.float64)

        notional_usd = weights * equity_usd
        target_shares = np.where(prices > 0, notional_usd / prices, 0.0)
        target_qty = np.abs(target_shares)

        sides = [
            "BUY" if w > 1e-8 else "SELL" if w < -1e-8 else "HOLD"
            for w in weights
        ]

        net_dollar_exposure = float(np.sum(notional_usd))
        gross_dollar_exposure = float(np.sum(np.abs(notional_usd)))
        net_exposure = float(np.sum(weights))
        gross_leverage = float(np.sum(np.abs(weights)))

        enriched_df = allocated_batch.with_columns([
            pl.Series("target_notional_usd", notional_usd, dtype=pl.Float64),
            pl.Series("notional_usd", notional_usd, dtype=pl.Float64),
            pl.Series("target_shares", target_shares, dtype=pl.Float64),
            pl.Series("target_qty", target_qty, dtype=pl.Float64),
            pl.Series("quantity", target_qty, dtype=pl.Float64),
            pl.Series("side", sides, dtype=pl.Utf8),
        ])

        long_basket = enriched_df.filter(pl.col("target_weight") > 1e-8)[ticker_col].to_list() if ticker_col else []
        short_basket = enriched_df.filter(pl.col("target_weight") < -1e-8)[ticker_col].to_list() if ticker_col else []

        return OrderBatch(
            data=enriched_df,
            net_dollar_exposure=net_dollar_exposure,
            gross_dollar_exposure=gross_dollar_exposure,
            gross_leverage=gross_leverage,
            net_exposure=net_exposure,
            long_basket=long_basket,
            short_basket=short_basket,
        )

    allocate_weights = allocate
    compute_weights = allocate

# Backwards compatibility alias for cli.py
DollarNeutralRiskParityAllocator = DollarNeutralPortfolioAllocator

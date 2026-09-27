"""
Continuous Risk Governor: Enforces drawdown constraints, volatility scaling,
and dynamic leverage modulation across portfolios.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import polars as pl


@dataclass(frozen=True)
class GovernorState:
    current_drawdown: float
    realized_vol: float
    leverage_multiplier: float
    is_halted: bool


class ContinuousRiskGovernor:
    def __init__(
        self,
        max_drawdown_limit: float = 0.15,
        target_volatility: float = 0.20,
        max_leverage: float = 3.0,
        vol_lookback: int = 30,
    ):
        self.max_drawdown_limit = max_drawdown_limit
        self.target_volatility = target_volatility
        self.max_leverage = max_leverage
        self.vol_lookback = vol_lookback
        self.peak_equity = 1.0
        self.current_equity = 1.0

    @staticmethod
    def compute_exposure_scalar(
        data: pl.DataFrame | np.ndarray | float | None = None,
        target_vol: float = 0.035,
        max_exposure: float = 2.0,
        **kwargs
    ) -> float:
        """
        Computes exposure scalar (omega) from market state / cross-sectional volatility.
        """
        if data is None:
            return 1.0
        if isinstance(data, (int, float)):
            return float(data)
        if isinstance(data, pl.DataFrame):
            for vol_col in ["gk_vol_20p", "realized_vol", "vol", "volatility"]:
                if vol_col in data.columns:
                    mean_vol = float(data[vol_col].mean() or 0.0)
                    if mean_vol > 1e-6:
                        scalar = target_vol / mean_vol
                        return float(np.clip(scalar, 0.0, max_exposure))
            return 1.0
        return 1.0

    def update_equity(self, equity: float) -> float:
        self.current_equity = equity
        if equity > self.peak_equity:
            self.peak_equity = equity
        dd = (self.peak_equity - self.current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        return float(dd)

    def compute_leverage_multiplier(
        self,
        returns: np.ndarray | list[float] | None = None,
        current_equity: float | None = None
    ) -> float:
        if current_equity is not None:
            self.update_equity(current_equity)
        
        dd = (self.peak_equity - self.current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        if dd >= self.max_drawdown_limit:
            return 0.0

        dd_factor = max(0.0, 1.0 - (dd / self.max_drawdown_limit))

        if returns is not None and len(returns) >= 2:
            arr = np.asarray(returns, dtype=np.float64)
            recent = arr[-self.vol_lookback:]
            realized_vol = float(np.std(recent) * np.sqrt(365.25 * 24 * 60))
            if realized_vol > 1e-6:
                vol_scaler = self.target_volatility / realized_vol
            else:
                vol_scaler = 1.0
        else:
            vol_scaler = 1.0

        multiplier = np.clip(vol_scaler * dd_factor, 0.0, self.max_leverage)
        return float(multiplier)

    def govern_weights(
        self,
        weights: dict[str, float],
        returns: np.ndarray | list[float] | None = None,
        current_equity: float | None = None
    ) -> dict[str, float]:
        multiplier = self.compute_leverage_multiplier(returns=returns, current_equity=current_equity)
        return {s: float(w * multiplier) for s, w in weights.items()}

# Backwards compatibility alias for cli.py
MacroRiskGovernor = ContinuousRiskGovernor

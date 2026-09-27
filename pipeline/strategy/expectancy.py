"""
Layer 2 Expectancy Engine & Continuous Funding Path Model (Zero-I/O).
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ExpectancyMetrics:
    ev_return_pct: float
    ev_dollar: float
    ev_equity_bps: float
    funding_drag_pct: float
    net_edge_bps: float
    is_positive_ev: bool


class ContinuousFundingPathModel:
    r"""
    Continuous Funding Path Model:
    Projects cumulative funding carry C_funding = \sum s * FR_t * N_t
    accounting for current rate and mean-reverting predicted rate.
    """
    def __init__(self, half_life_hours: float = 8.0):
        self.decay_rate = np.log(2.0) / max(half_life_hours, 1e-4)

    def estimate_funding_cost_pct(
        self,
        current_rate: float,
        predicted_next_rate: float,
        holding_horizon_hours: float = 1.0,
        is_long: bool = True
    ) -> float:
        s = 1.0 if is_long else -1.0
        
        h = max(holding_horizon_hours, 1e-3)
        mean_rate = 0.5 * (current_rate + predicted_next_rate * np.exp(-self.decay_rate * h))
        cumulative_funding = s * mean_rate * h
        return float(cumulative_funding)


class ExpectancyEngine:
    """
    Multi-Outcome Expectancy Engine:
    EV_return = P_win * R_win - P_loss * R_loss - C_funding - C_fee - C_slippage
    """
    def __init__(
        self,
        maker_fee_pct: float = -0.00005,  # Hyperliquid maker rebate
        taker_fee_pct: float = 0.00035,   # Hyperliquid taker fee
        default_slippage_pct: float = 0.00010
    ):
        self.maker_fee_pct = maker_fee_pct
        self.taker_fee_pct = taker_fee_pct
        self.default_slippage_pct = default_slippage_pct
        self.funding_model = ContinuousFundingPathModel()

    def evaluate_expectancy(
        self,
        win_prob: float,
        expected_gain_pct: float,
        expected_loss_pct: float,
        current_funding_rate: float,
        predicted_funding_rate: float,
        is_long: bool,
        notional_usd: float = 1000.0,
        holding_horizon_hours: float = 1.0,
        is_maker: bool = True
    ) -> ExpectancyMetrics:
        p_win = np.clip(win_prob, 0.0, 1.0)
        p_loss = 1.0 - p_win

        fee_pct = self.maker_fee_pct if is_maker else self.taker_fee_pct
        slippage_pct = 0.0 if is_maker else self.default_slippage_pct
        execution_drag = fee_pct + slippage_pct

        funding_drag = self.funding_model.estimate_funding_cost_pct(
            current_rate=current_funding_rate,
            predicted_next_rate=predicted_funding_rate,
            holding_horizon_hours=holding_horizon_hours,
            is_long=is_long
        )

        raw_ev = (p_win * expected_gain_pct) - (p_loss * expected_loss_pct)
        ev_return = raw_ev - funding_drag - execution_drag
        ev_dollar = ev_return * notional_usd
        ev_equity_bps = ev_return * 10000.0

        return ExpectancyMetrics(
            ev_return_pct=float(ev_return),
            ev_dollar=float(ev_dollar),
            ev_equity_bps=float(ev_equity_bps),
            funding_drag_pct=float(funding_drag),
            net_edge_bps=float(ev_equity_bps),
            is_positive_ev=bool(ev_return > 0.0)
        )

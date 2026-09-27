"""
Section 3.1 & 4: Multi-Outcome Expectancy Engine & Immutable TradeIntent Builder.
Computes return-normalized EV across the triple-barrier distribution and constructs TradeIntents.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np


@dataclass(frozen=True)
class RawMarketState:
    symbol: str
    t_event_ns: int
    t_recv_ns: int
    bid_price: float
    ask_price: float
    mid_price: float
    oracle_price: float
    funding_rate_1h: float
    funding_missing: bool


@dataclass(frozen=True)
class TradeIntent:
    symbol: str
    action: Literal["LONG", "SHORT", "FLAT"]
    target_weight: float        # Fractional allocation (0.0 to 1.0)
    stop_price: float
    target_price: float
    stop_distance_pct: float    # |Stop - Entry| / Entry
    target_distance_pct: float  # |Target - Entry| / Entry
    time_limit_sec: int
    ev_return: float            # Dimensionless expected return on notional
    ev_dollar: float            # Expected dollar gain on position
    ev_equity: float            # Expected return as % of total equity


def compute_multi_outcome_ev(
    action: Literal["LONG", "SHORT"],
    entry_price: float,
    target_price: float,
    stop_price: float,
    p_tp: float,
    p_sl: float,
    funding_rate_1h: float,
    expected_holding_hours: float = 4.0,
    expected_exec_cost_bps: float = 3.5,  # 3.5 bps taker fee + slippage buffer
) -> float:
    """
    EV_return = P_TP * R_TP + P_SL * R_SL + P_TO * R_TO - E[C_exec] - E[C_funding]
    """
    p_to = max(0.0, 1.0 - (p_tp + p_sl))
    
    # 1. Discrete Barrier Payoffs
    if action == "LONG":
        r_tp = (target_price - entry_price) / entry_price
        r_sl = (stop_price - entry_price) / entry_price
        r_to = 0.5 * (r_tp + r_sl)  # Neutral expectation on timeout
        funding_sign = 1.0
    else:
        r_tp = (entry_price - target_price) / entry_price
        r_sl = (entry_price - stop_price) / entry_price
        r_to = 0.5 * (r_tp + r_sl)
        funding_sign = -1.0

    # 2. Execution and Continuous Funding Costs
    c_exec = expected_exec_cost_bps * 1e-4
    c_funding = funding_sign * funding_rate_1h * expected_holding_hours

    # 3. Multi-Outcome Net Expectancy
    ev_return = (p_tp * r_tp) + (p_sl * r_sl) + (p_to * r_to) - c_exec - c_funding
    return float(ev_return)


def build_trade_intent(
    market: RawMarketState,
    target_weight: float,
    total_portfolio_equity: float,
    p_tp: float = 0.58,
    p_sl: float = 0.35,
    atr_pct: float = 0.018,      # 1.8% 4H ATR
) -> TradeIntent:
    """Builds an immutable TradeIntent contract from allocated weight and expected returns."""
    if abs(target_weight) < 1e-4 or market.funding_missing:
        return TradeIntent(
            symbol=market.symbol,
            action="FLAT",
            target_weight=0.0,
            stop_price=market.mid_price,
            target_price=market.mid_price,
            stop_distance_pct=0.0,
            target_distance_pct=0.0,
            time_limit_sec=14400,
            ev_return=0.0,
            ev_dollar=0.0,
            ev_equity=0.0,
        )

    action: Literal["LONG", "SHORT"] = "LONG" if target_weight > 0 else "SHORT"
    entry = market.mid_price
    
    # Asymmetric 2:1 R:R Triple Barrier Setup
    target_dist = 2.0 * atr_pct
    stop_dist = 1.0 * atr_pct

    if action == "LONG":
        target_price = entry * (1.0 + target_dist)
        stop_price = entry * (1.0 - stop_dist)
    else:
        target_price = entry * (1.0 - target_dist)
        stop_price = entry * (1.0 + stop_dist)

    ev_ret = compute_multi_outcome_ev(
        action=action,
        entry_price=entry,
        target_price=target_price,
        stop_price=stop_price,
        p_tp=p_tp,
        p_sl=p_sl,
        funding_rate_1h=market.funding_rate_1h,
    )

    notional_allocated = abs(target_weight) * total_portfolio_equity
    ev_dollar = ev_ret * notional_allocated
    ev_equity = ev_dollar / total_portfolio_equity if total_portfolio_equity > 0 else 0.0

    return TradeIntent(
        symbol=market.symbol,
        action=action,
        target_weight=abs(target_weight),
        stop_price=float(stop_price),
        target_price=float(target_price),
        stop_distance_pct=float(stop_dist),
        target_distance_pct=float(target_dist),
        time_limit_sec=14400, # 4-hour window
        ev_return=float(ev_ret),
        ev_dollar=float(ev_dollar),
        ev_equity=float(ev_equity),
    )

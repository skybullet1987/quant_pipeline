"""
Layer 2: Pure Strategy Core (Zero-I/O) State Definitions.
Immutable state pipeline guaranteeing no network, database, or disk I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IntentSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass(frozen=True)
class RawMarketState:
    timestamp_ns: int
    symbol: str
    best_bid: float
    best_ask: float
    mid_price: float
    last_trade_price: float
    bid_depth_l5: float
    ask_depth_l5: float
    funding_rate_hourly: float
    predicted_funding_next: float


@dataclass(frozen=True)
class FeatureState:
    timestamp_ns: int
    symbol: str
    log_ret_1m: float
    rvol_15m: float
    rvol_1h: float
    natr_14m: float
    order_flow_imbalance: float
    vwap_basis_bps: float
    cvd_15m: float
    volume_zscore_60m: float


@dataclass(frozen=True)
class RegimeState:
    timestamp_ns: int
    symbol: str
    p_trend: float
    p_chop: float
    p_expansion: float
    p_hazard: float
    long_permission: float       # Continuous permission [0.0, 1.0]
    short_permission: float      # Continuous permission [0.0, 1.0]
    regime_multiplier: float     # Combined alpha dampener / amplifier


@dataclass(frozen=True)
class AlphaState:
    timestamp_ns: int
    symbol: str
    raw_alpha_score: float
    calibrated_win_prob: float
    expected_gain_pct: float
    expected_loss_pct: float
    ev_return_pct: float
    ev_dollar: float
    funding_cost_est_pct: float
    shrunk_mu: float


@dataclass(frozen=True)
class TradeIntent:
    timestamp_ns: int
    symbol: str
    target_side: IntentSide
    target_weight: float
    target_notional_usd: float
    limit_price_ref: float
    urgency_bps: float
    ev_return_pct: float
    regime_multiplier: float
    metadata: dict[str, float] = field(default_factory=dict)

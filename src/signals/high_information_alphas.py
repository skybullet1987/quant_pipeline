"""
Novel High-Information Alpha Signals for Crypto Perpetuals
==========================================================
Implements the 4 alpha feature families from the Deep Research architecture:
1. Liquidation Cluster Absorption (LCA) & Pressure Dynamics (LPR)
2. Funding Velocity Divergence (FVD) & Basis Term Structure Curvature
3. Orderbook Microstructure Imbalance (OFI) & Taker Volume Skew (TVS)
4. Structural Open Interest Decoupling (OID)
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


def compute_liquidation_cluster_absorption(
    long_liq_volume: np.ndarray,
    short_liq_volume: np.ndarray,
    total_volume: np.ndarray,
    bid_depth_05pct: np.ndarray,
    price_change: np.ndarray,
    atr: np.ndarray,
    oi_change_pct: np.ndarray,
    theta_flush: float = 0.03,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Computes Liquidation Pressure Ratio (LPR) and Liquidation Cluster Absorption (LCA).
    
    LPR = (ShortLiq - LongLiq) / TotalVolume
    LCA = ln(1 + LongLiq / BidDepth) * exp(-|DeltaP| / ATR) * 1_{DeltaOI / OI < -theta}
    """
    safe_vol = np.where(total_volume <= 0, 1e-8, total_volume)
    lpr = (short_liq_volume - long_liq_volume) / safe_vol
    lpr = np.clip(lpr, -1.0, 1.0)

    safe_depth = np.where(bid_depth_05pct <= 0, 1e-8, bid_depth_05pct)
    safe_atr = np.where(atr <= 0, 1e-8, atr)

    liq_absorption_ratio = np.log1p(long_liq_volume / safe_depth)
    price_damping = np.exp(-np.abs(price_change) / safe_atr)
    oi_flush_mask = np.where(oi_change_pct < -theta_flush, 1.0, 0.0)

    lca = liq_absorption_ratio * price_damping * oi_flush_mask
    return lpr, lca


def compute_funding_velocity_divergence(
    funding_rate: pd.Series,
    price: pd.Series,
    lookback_k: int = 24,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Computes Funding Velocity (V_f), Normalized Price Velocity (V_p),
    and Funding Velocity Divergence (FVD = V_p - V_f).
    """
    f_mean = funding_rate.rolling(window=lookback_k, min_periods=4).mean()
    f_std = funding_rate.rolling(window=lookback_k, min_periods=4).std().replace(0, 1e-8)
    v_f = (funding_rate - f_mean) / f_std

    p_delta = price - price.shift(lookback_k)
    p_std = price.rolling(window=lookback_k, min_periods=4).std().replace(0, 1e-8)
    v_p = p_delta / p_std

    fvd = v_p - v_f
    return v_f, v_p, fvd


def compute_basis_curvature(
    perp_price: pd.Series,
    spot_price: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """
    Computes Annualized Basis and Basis Term Structure Curvature:
    C_basis = 2 * Basis_8H - Basis_1H - Basis_24H
    """
    safe_spot = spot_price.replace(0, 1e-8)
    raw_basis = (perp_price - spot_price) / safe_spot

    basis_1h = raw_basis * (365 * 24 / 1.0)
    basis_8h = raw_basis.rolling(2).mean() * (365 * 24 / 8.0)
    basis_24h = raw_basis.rolling(6).mean() * (365 * 24 / 24.0)

    c_basis = (2.0 * basis_8h) - basis_1h - basis_24h
    return basis_1h, c_basis


def compute_order_flow_imbalance(
    bid_qty_change: np.ndarray,
    ask_qty_change: np.ndarray,
    bid_price_delta: np.ndarray,
    ask_price_delta: np.ndarray,
) -> np.ndarray:
    """
    Computes Multi-Level Order Flow Imbalance (OFI).
    OFI = Delta q_b * 1_{Delta P_b >= 0} - Delta q_a * 1_{Delta P_a <= 0}
    """
    bid_contrib = np.where(bid_price_delta >= 0, bid_qty_change, 0.0)
    ask_contrib = np.where(ask_price_delta <= 0, ask_qty_change, 0.0)
    ofi = bid_contrib - ask_contrib
    return ofi


def compute_taker_volume_skew(
    taker_buy_vol: np.ndarray,
    taker_sell_vol: np.ndarray,
) -> np.ndarray:
    """
    Computes Taker Volume Skew (TVS).
    TVS = (TakerBuy - TakerSell) / (TakerBuy + TakerSell)
    """
    total_taker = taker_buy_vol + taker_sell_vol
    safe_total = np.where(total_taker <= 0, 1e-8, total_taker)
    tvs = (taker_buy_vol - taker_sell_vol) / safe_total
    return np.clip(tvs, -1.0, 1.0)


def compute_structural_oi_decoupling(
    price_change: np.ndarray,
    oi_change: np.ndarray,
    mean_oi: np.ndarray,
    price_std: np.ndarray,
    xi: float = 1.5,
) -> np.ndarray:
    """
    Computes Structural Open Interest Decoupling (OID).
    Phi_OID = sgn(Delta P) * (Delta OI / MeanOI) * [1 - tanh(xi * |Delta P / sigma_p|)]
    """
    safe_mean_oi = np.where(mean_oi <= 0, 1e-8, mean_oi)
    safe_p_std = np.where(price_std <= 0, 1e-8, price_std)

    sgn_dp = np.sign(price_change)
    norm_oi_change = oi_change / safe_mean_oi
    compression_factor = 1.0 - np.tanh(xi * np.abs(price_change / safe_p_std))

    phi_oid = sgn_dp * norm_oi_change * compression_factor
    return phi_oid

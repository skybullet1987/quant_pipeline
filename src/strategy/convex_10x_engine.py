#!/usr/bin/env python3
"""
Institutional Production Quant Engine: IronCore v2.4.0 (Frozen E3 Reality)
Architecture: Convex 10x Compounding Core (EXP-102 Sovereign Finality Standard)
Target Venue: Hyperliquid Layer 1 Derivatives Protocol (Perpetual Futures)

Key Features:
1. Multi-Cadence Regime Decoupling (72H Macro Rebalance, 4H Micro Risk Monitor)
2. Dual-Barrier Rank Hysteresis (K_in = 8, K_out = 14) with Position-Lock Buffer
3. Asset-Specific Volatility Deadband (tau_0 = 300 bps)
4. Continuous Bipower Variation (BV) Jump Disentanglement & Parabolic Trailing Ratchet
5. True Layer 1 Funding Carry Settlement & Squeeze Harvesting
6. Second-Order Fractional Kelly & Grossman-Zhou Drawdown Floor (M = 0.20, L_max = 3.50x)
7. Anti-Martingale Two-Tranche Milestone Profit Vaulting (60% Tranche A / 40% Tranche B)
8. Hyperliquid L1 Consensus Quantization Invariants (<= 5 sig figs, <= 6 - szDecimals, >= $10 notional)
9. Exact 6-Bucket Mark-to-Market Ledger Conservation (|epsilon| < 10^-12)
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np


class MachineState(Enum):
    IDLE = 0
    ENTER_PENDING = 1
    OPEN_ACTIVE = 2
    TRAILING_LOCK = 3
    EXIT_PENDING = 4


@dataclass
class PositionRecord:
    symbol: str
    direction: int                  # +1: Long, -1: Short
    entry_price: float
    current_size: float
    stop_price: float
    atr_entry: float
    bipower_entry: float
    highest_high: float
    lowest_low: float
    entry_timestamp: int
    lock_expiration_bar: int
    lock_duration_bars: int = 18    # Default 72H (18 4H bars)
    pyramided: bool = False
    state: MachineState = MachineState.OPEN_ACTIVE
    last_price: float = 0.0
    realized_pnl: float = 0.0
    accumulated_funding: float = 0.0


# ==============================================================================
# 1. HYPERLIQUID L1 CONSENSUS QUANTIZATION INVARIANTS
# ==============================================================================

def round_sz(size: float, sz_decimals: int) -> float:
    """
    Enforces Hyperliquid L1 size quantization:
    Rounds down (floor) strictly to szDecimals decimal places, preserving sign.
    """
    if sz_decimals < 0 or abs(size) <= 0.0:
        return 0.0
    factor = 10 ** sz_decimals
    truncated = math.floor(abs(size) * factor) / factor
    return round(truncated, sz_decimals) * (1 if size >= 0 else -1)


def round_px(price: float, sz_decimals: int) -> float:
    """
    Enforces Hyperliquid L1 price quantization invariants:
    1. Maximum of 5 significant figures.
    2. Maximum of (MAX_DECIMALS - szDecimals) decimal places (MAX_DECIMALS = 6 for perps).
    """
    if math.isnan(price) or price <= 0.0:
        return 0.0
    
    max_decimals = max(0, 6 - sz_decimals)
    magnitude = math.floor(math.log10(abs(price)))
    sig_fig_decimals = 5 - magnitude - 1
    
    if sig_fig_decimals < 0:
        return float(round(price, sig_fig_decimals))
    
    target_decimals = min(max_decimals, sig_fig_decimals)
    return float(round(price, target_decimals))


def validate_l1_order(
    symbol: str,
    price: float,
    size: float,
    sz_decimals: int,
    is_reduce_only: bool = False
) -> Tuple[bool, str, float, float]:
    """
    Validates order notional and precision against Hyperliquid L1 consensus invariants.
    """
    q_px = round_px(price, sz_decimals)
    q_sz = round_sz(size, sz_decimals)
    notional = q_px * q_sz
    
    if not is_reduce_only and notional < 10.00:
        return False, f"Order notional ${notional:.2f} below $10.00 L1 minimum", q_px, q_sz
        
    if q_sz <= 0.0:
        return False, "Order size truncated to 0.0 under szDecimals floor", q_px, q_sz
        
    return True, "VALID", q_px, q_sz


# ==============================================================================
# 2. MICROSTRUCTURE VARIATION & FRACTAL PERSISTENCE OPERATORS
# ==============================================================================

def compute_continuous_bipower_variation(return_subbars: np.ndarray) -> Tuple[float, float]:
    """
    Separates continuous Gaussian diffusion variance from Poisson jump shocks
    using the Barndorff-Nielsen & Shephard (2004) Bipower Variation framework.
    Returns: (continuous_volatility_annualized, jump_volatility_annualized)
    """
    M = len(return_subbars)
    if M < 12:
        vol = float(np.std(return_subbars) * math.sqrt(2190))
        return vol, 0.0
        
    rv = float(np.sum(return_subbars ** 2))
    bv = float((math.pi / 2.0) * (M / (M - 1.0)) * np.sum(np.abs(return_subbars[1:]) * np.abs(return_subbars[:-1])))
    jump_var = max(0.0, rv - bv)
    
    cont_vol_ann = math.sqrt(max(bv, 1e-8)) * math.sqrt(2190)
    jump_vol_ann = math.sqrt(max(jump_var, 0.0)) * math.sqrt(2190)
    return cont_vol_ann, jump_vol_ann


def compute_hurst_exponent(returns: np.ndarray, min_window: int = 10) -> float:
    """
    Evaluates rolling local Hurst exponent H using Rescaled Range (R/S) trajectory.
    H > 0.50: Persistent / Trending
    H = 0.50: Pure Brownian Motion
    H < 0.50: Mean-Reverting
    """
    n = len(returns)
    if n < min_window:
        return 0.50
        
    mean_r = np.mean(returns)
    y = np.cumsum(returns - mean_r)
    r_range = np.max(y) - np.min(y)
    s_std = np.std(returns)
    
    if s_std < 1e-12 or r_range < 1e-12:
        return 0.50
        
    rs = r_range / s_std
    hurst = math.log(rs) / math.log(n)
    return float(np.clip(hurst, 0.0, 1.0))


def compute_variance_ratio(returns: np.ndarray, q: int = 6) -> float:
    """
    Lo-MacKinlay Variance Ratio test statistic VR(q) evaluated at lag aggregation q.
    q = 6 corresponds to 24 hours of 4-hour bars.
    VR > 1.0 indicates positive autocorrelation and trend persistence.
    """
    n = len(returns)
    if n < q * 4:
        return 1.0
        
    var_1 = float(np.var(returns, ddof=1))
    if var_1 < 1e-12:
        return 1.0
        
    # Aggregate returns over q bars
    agg_returns = np.convolve(returns, np.ones(q), mode='valid')
    var_q = float(np.var(agg_returns, ddof=1))
    
    vr = var_q / (q * var_1)
    return float(vr)


def determine_holding_lock_duration(hurst: float, vr: float) -> int:
    """
    Maps fractal persistence metrics into dynamic position lock duration (bars):
    - Super-Persistent (H >= 0.65 and VR > 1.25): 168 Hours (42 bars)
    - Persistent (0.55 <= H < 0.65 and VR > 1.05): 72 Hours (18 bars)
    - Diffusive (0.45 <= H < 0.55): 24 Hours (6 bars)
    - Anti-Persistent (H < 0.45 or VR < 0.85): 0 Hours (0 bars, immediate exit)
    """
    if hurst >= 0.65 and vr > 1.25:
        return 42   # 168 Hours
    elif hurst >= 0.55 and vr > 1.05:
        return 18   # 72 Hours
    elif hurst >= 0.45:
        return 6    # 24 Hours
    else:
        return 0    # Immediate exit eligible


# ==============================================================================
# CANONICAL SHARED MARKET MATHEMATICS & PARITY INVARIANTS
# ==============================================================================

LELAND_DEADBAND: float = 0.100  # 10.0% absolute portfolio percentage points deadband


def compute_canonical_wilder_atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    window: int = 14
) -> np.ndarray:
    """
    Computes true canonical Wilder's Smoothed Average True Range (ATR) over completed bars:
      TR_t = max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)
      ATR_0 = mean(TR_{0:window})
      ATR_t = (1/window) * TR_t + ((window - 1)/window) * ATR_{t-1}
    Supports 1D (time,) or 2D (time, symbols) matrices.
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)

    is_1d = high.ndim == 1
    if is_1d:
        high = high[:, np.newaxis]
        low = low[:, np.newaxis]
        close = close[:, np.newaxis]

    n_bars, n_syms = close.shape
    tr = np.zeros((n_bars, n_syms), dtype=float)
    tr[0] = high[0] - low[0]

    for t in range(1, n_bars):
        hl = high[t] - low[t]
        hc = np.abs(high[t] - close[t - 1])
        lc = np.abs(low[t] - close[t - 1])
        tr[t] = np.maximum(hl, np.maximum(hc, lc))

    atr = np.zeros_like(tr)
    if n_bars <= window:
        atr[:] = np.mean(tr, axis=0, keepdims=True)
    else:
        atr[window - 1] = np.mean(tr[:window], axis=0)
        alpha = 1.0 / float(window)
        for t in range(window, n_bars):
            atr[t] = alpha * tr[t] + (1.0 - alpha) * atr[t - 1]
        for t in range(window - 1):
            atr[t] = atr[window - 1]

    return atr[:, 0] if is_1d else atr


def compute_canonical_f1_carry(
    funding_rates: np.ndarray,
    eligible_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Canonical F1 Remediated Funding Carry Operator:
    Inverts the retail funding transfer equation ('Become the House'):
      F1_i,t = - (FundingRate_i,t - Mean(Funding_t)) / (Std(Funding_t) + 1e-8)
    Systematically shorts crowded high-positive-funding tokens (receiving cashflows)
    and longs discount/negative-funding tokens (receiving cashflows).
    Supports 1D (symbols,) or 2D (time, symbols) cross-sectional arrays.
    """
    arr = np.asarray(funding_rates, dtype=float)
    is_1d = arr.ndim == 1
    if is_1d:
        arr = arr[np.newaxis, :]
        if eligible_mask is not None:
            eligible_mask = np.asarray(eligible_mask, dtype=bool)[np.newaxis, :]

    T, N = arr.shape
    f1_scores = np.zeros((T, N), dtype=float)

    for t in range(T):
        row = arr[t]
        if eligible_mask is not None:
            mask = eligible_mask[t] & ~np.isnan(row)
        else:
            mask = ~np.isnan(row)

        if np.sum(mask) >= 3:
            sub = row[mask]
            mean_val = np.mean(sub)
            std_val = np.std(sub)
            if std_val > 1e-8:
                f1_scores[t, mask] = - ((sub - mean_val) / std_val)

    return f1_scores[0] if is_1d else f1_scores


# ==============================================================================
# 3. IRONCORE CONVEX COMPOUNDING ENGINE (v2.4.0 FROZEN E3 REALITY)
# ==============================================================================

class IronCoreEngine:
    def __init__(
        self,
        symbols: List[str],
        sz_decimals_map: Dict[str, int],
        initial_nav: float = 10000.0,
        m_drawdown_floor: float = 0.20,     # Grossman-Zhou 20% Hard Floor Bound
        target_vol: float = 0.60,           # 60% Annualized Target Volatility
        max_leverage: float = 3.50,         # Maximum Gearing Cap
        holding_period_bars: int = 18,      # 72H Macro Decoupling Horizon
        turnover_deadband: float = 0.030,   # 300 bps rebalance deadband
        k_in: int = 8,                      # Top K conviction entry gate
        k_out: int = 14,                    # Retention hysteresis outer corridor
        lock_dwell_bars: int = 12           # 48H minimum position lock dwell
    ):
        self.symbols = symbols
        self.sz_dec = sz_decimals_map
        self.nav = initial_nav
        self.initial_nav = initial_nav
        self.hwm = initial_nav
        self.m_floor = m_drawdown_floor
        self.target_vol = target_vol
        self.max_lev = max_leverage
        self.macro_period = holding_period_bars
        self.deadband = turnover_deadband
        self.k_in = k_in
        self.k_out = k_out
        self.lock_dwell_bars = lock_dwell_bars
        
        # Exact 6-Bucket Accounting Ledger
        self.ledger = {
            "gross_price_pnl": 0.0,
            "funding_pnl": 0.0,
            "exchange_fees": 0.0,
            "market_impact": 0.0,
            "adverse_selection": 0.0,
            "realized_stop_slippage": 0.0
        }
        
        self.positions: Dict[str, PositionRecord] = {}
        self.cooldowns: Dict[str, int] = {s: 0 for s in symbols}
        self.weights_prev = np.zeros(len(symbols))
        
        # Two-Tranche Anti-Martingale Milestone Vaulting Architecture
        self.tranche_a_nav = initial_nav * 0.60  # 60% Preservation & Carry Core
        self.tranche_b_nav = initial_nav * 0.40  # 40% Convex Momentum Runner
        self.tranche_b_base = self.tranche_b_nav
        self.tranche_b_hwm = self.tranche_b_nav
        self.vaulted_profits_total = 0.0
        
        # Telemetry & Trade History
        self.total_rebalances = 0
        self.total_trades = 0
        self.cumulative_turnover = 0.0
        self.equity_curve: List[Tuple[int, float, float, float]] = [] # (bar, nav, hwm, gearing)

    def audit_ledger_identity(self) -> Tuple[bool, float]:
        """
        Audits exact 6-bucket mark-to-market balance sheet conservation:
        Net PnL = Gross Price PnL + Funding PnL - Exchange Fees - Market Impact - Adverse Selection - Realized Stop Slippage
        Returns: (is_conserved, discrepancy) with machine-precision tolerance (|discrepancy| < 10^-11)
        """
        net_pnl = self.nav - self.initial_nav
        reconciled_pnl = (
            self.ledger["gross_price_pnl"]
            + self.ledger["funding_pnl"]
            - self.ledger["exchange_fees"]
            - self.ledger["market_impact"]
            - self.ledger["adverse_selection"]
            - self.ledger["realized_stop_slippage"]
        )
        discrepancy = abs(net_pnl - reconciled_pnl)
        is_conserved = discrepancy < 1e-11
        return is_conserved, discrepancy

    def update_grossman_zhou_cushion(self) -> float:
        """
        Evaluates the Grossman-Zhou (1993) capital cushion governor.
        Floor level: F(t) = (1 - M) * HWM(t) = 0.80 * HWM(t).
        Cushion: C(t) = max(0, NAV(t) - F(t)).
        Gearing: L_target = clip(L_max * (C(t) / (M * HWM(t)))^0.75, 0.0, L_max).
        Automatically throttles operational leverage to 0.0x as drawdown approaches 20%.
        """
        if self.nav > self.hwm:
            self.hwm = self.nav
            
        floor_level = (1.0 - self.m_floor) * self.hwm
        cushion = max(0.0, self.nav - floor_level)
        total_buffer = self.m_floor * self.hwm
        cushion_ratio = float(np.clip(cushion / (total_buffer + 1e-8), 0.0, 1.0))
        
        gearing = float(np.clip(self.max_lev * (cushion_ratio ** 0.75), 0.0, self.max_lev))
        return gearing

    def process_micro_bar_risk(
        self,
        bar_idx: int,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        atrs: np.ndarray,
        subbar_returns: Optional[Dict[str, np.ndarray]] = None
    ):
        """
        High-resolution continuous risk-monitoring clock (T_micro = 4H).
        Executes adverse selection stop-losses, trailing Chandelier ratchets, and state transitions.
        """
        closed_syms = []
        
        for sym, pos in self.positions.items():
            s_idx = self.symbols.index(sym)
            px_high = highs[s_idx]
            px_low = lows[s_idx]
            px_close = closes[s_idx]
            atr = atrs[s_idx]
            sz_dec = self.sz_dec[sym]
            
            is_stopped = False
            exit_fill_px = pos.stop_price
            slippage_gap = 0.50 * atr
            
            # Adverse selection barrier evaluation under E3 physics
            if pos.direction == 1:
                if px_low <= pos.stop_price:
                    is_stopped = True
                    raw_exit = pos.stop_price - slippage_gap
                    exit_fill_px = round_px(raw_exit, sz_dec)
            else:
                if px_high >= pos.stop_price:
                    is_stopped = True
                    raw_exit = pos.stop_price + slippage_gap
                    exit_fill_px = round_px(raw_exit, sz_dec)
                    
            if is_stopped:
                # Execution accounting with exact 6-bucket breakdown
                # Incremental price delta from pos.last_price to exit_fill_px
                incremental_gross = pos.current_size * (exit_fill_px - pos.last_price) * pos.direction
                
                notional = pos.current_size * exit_fill_px
                taker_fee = notional * 0.00045        # 4.5 bps taker fee
                market_impact = notional * 0.00050    # 5.0 bps market impact
                
                # Book into ledger
                self.ledger["gross_price_pnl"] += incremental_gross
                self.ledger["exchange_fees"] += taker_fee
                self.ledger["market_impact"] += market_impact
                
                net_trade_pnl = incremental_gross - (taker_fee + market_impact)
                self.nav += net_trade_pnl
                self.total_trades += 1
                
                pos.state = MachineState.EXIT_PENDING
                closed_syms.append(sym)
                self.cooldowns[sym] = bar_idx + 6     # 24H cooldown
                continue
                
            # Continuous MTM price tracking on surviving positions
            incremental_gross = pos.current_size * (px_close - pos.last_price) * pos.direction
            self.ledger["gross_price_pnl"] += incremental_gross
            self.nav += incremental_gross
            pos.last_price = px_close

            # Update extreme excursion prices
            pos.highest_high = max(pos.highest_high, px_high)
            pos.lowest_low = min(pos.lowest_low, px_low)
            
            # Parabolic trailing ratchet
            if pos.direction == 1:
                unrealized_dist = pos.highest_high - pos.entry_price
                if unrealized_dist >= 1.5 * pos.atr_entry:
                    pos.state = MachineState.TRAILING_LOCK
                    # Regime 2 & 3: Ratchet accelerates as momentum extends
                    k_accel = 2.50 * math.exp(-0.35 * (unrealized_dist / (pos.atr_entry + 1e-8))) + 0.75
                    chan_stop = round_px(pos.highest_high - (k_accel * atr), sz_dec)
                    # Ratchet is strictly monotonic upward
                    pos.stop_price = max(pos.stop_price, chan_stop)
            else:
                unrealized_dist = pos.entry_price - pos.lowest_low
                if unrealized_dist >= 1.5 * pos.atr_entry:
                    pos.state = MachineState.TRAILING_LOCK
                    k_accel = 2.50 * math.exp(-0.35 * (unrealized_dist / (pos.atr_entry + 1e-8))) + 0.75
                    chan_stop = round_px(pos.lowest_low + (k_accel * atr), sz_dec)
                    pos.stop_price = min(pos.stop_price, chan_stop)
                    
        for s in closed_syms:
            del self.positions[s]

    def execute_macro_rebalance(
        self,
        bar_idx: int,
        alpha_scores: np.ndarray,
        current_prices: np.ndarray,
        hourly_funding_rates: np.ndarray,
        atrs: np.ndarray,
        cont_vols: np.ndarray,
        hurst_exponents: Optional[np.ndarray] = None,
        variance_ratios: Optional[np.ndarray] = None,
        macro_regime_scalar: float = 1.0,
        tradable_mask: Optional[np.ndarray] = None
    ):
        """
        Macro portfolio reallocation clock (T_macro = 72H).
        Enforces stateful rank hysteresis [K_in=8, K_out=14], position-lock buffer,
        and volatility-adjusted turnover deadbands.
        """
        self.total_rebalances += 1
        gearing = self.update_grossman_zhou_cushion() * macro_regime_scalar
        
        # Systemic de-leveraging if cushion is exhausted
        if gearing <= 0.05:
            for sym, pos in list(self.positions.items()):
                px = current_prices[self.symbols.index(sym)]
                incremental_gross = pos.current_size * (px - pos.last_price) * pos.direction
                notional = pos.current_size * px
                fee = notional * 0.00045
                self.ledger["gross_price_pnl"] += incremental_gross
                self.ledger["exchange_fees"] += fee
                self.nav += (incremental_gross - fee)
                del self.positions[sym]
            self.weights_prev = np.zeros(len(self.symbols))
            return

        N = len(self.symbols)
        cd_mask = np.array([self.cooldowns[s] <= bar_idx for s in self.symbols])
        if tradable_mask is not None:
            valid_mask = cd_mask & tradable_mask & (current_prices > 0.0)
        else:
            valid_mask = cd_mask & (current_prices > 0.0)
        eligible_indices = np.where(valid_mask)[0]
        
        if len(eligible_indices) < 16:
            return

        # Funding filter: screen out crowded positive funding traps (> +105% APR)
        funding_apr = hourly_funding_rates * 24.0 * 365.25
        crowded_long_mask = funding_apr > 1.05

        # Rank cross-sectional alpha scores
        sorted_ranks = np.argsort(alpha_scores[eligible_indices])
        
        # Short candidates (lowest alpha)
        short_candidates = eligible_indices[sorted_ranks[:self.k_in]]
        
        # Long candidates (highest alpha, excluding crowded funding traps)
        top_long_indices = eligible_indices[sorted_ranks[::-1]]
        filtered_longs = [idx for idx in top_long_indices if not crowded_long_mask[idx]]
        long_candidates = np.array(filtered_longs[:self.k_in]) if len(filtered_longs) >= self.k_in else top_long_indices[:self.k_in]

        # Target allocation construction
        target_weights = np.zeros(N)
        weight_per_asset = (gearing * 0.50) / float(self.k_in)
        
        for idx in long_candidates:
            target_weights[idx] = weight_per_asset
        for idx in short_candidates:
            target_weights[idx] = -weight_per_asset
            
        # Cross-sectional volatility median for deadband scaling
        med_vol = float(np.median(cont_vols[eligible_indices])) if len(eligible_indices) > 0 else 0.50

        # Stateful Hysteresis and Position-Lock Evaluation
        for i in range(N):
            sym = self.symbols[i]
            target_w = target_weights[i]
            current_w = self.weights_prev[i]
            px = current_prices[i]
            sz_dec = self.sz_dec[sym]
            atr_val = atrs[i]
            cont_vol = cont_vols[i]
            if math.isnan(atr_val) or atr_val <= 0.0:
                atr_val = 0.02 * max(px, 1e-4)
            if math.isnan(cont_vol) or cont_vol <= 0.0:
                cont_vol = 0.50
            
            # Asset-specific volatility deadband
            tau_i = self.deadband * (med_vol / (cont_vol + 1e-8))
            weight_delta = target_w - current_w
            
            # 1. Check if position is locked
            if sym in self.positions:
                pos = self.positions[sym]
                is_locked = bar_idx < pos.lock_expiration_bar
                
                # If position is locked, prevent exit or churn unless stop is breached
                if is_locked and (target_w * pos.direction > 0):
                    # Maintain existing position with zero rebalance
                    target_weights[i] = current_w
                    continue
                
                # If position lock expired, check retention condition via outer barrier K_out
                if not is_locked:
                    # Find current ordinal rank
                    pos_in_eligible = np.where(eligible_indices == i)[0]
                    if len(pos_in_eligible) > 0:
                        current_rank = np.where(sorted_ranks == pos_in_eligible[0])[0]
                        if len(current_rank) > 0:
                            rank_val = current_rank[0]
                            # If long and rank within retention corridor [K_in, K_out], retain!
                            if pos.direction == 1 and rank_val >= (len(eligible_indices) - self.k_out):
                                target_weights[i] = current_w
                                continue
                            # If short and rank within retention corridor, retain!
                            elif pos.direction == -1 and rank_val < self.k_out:
                                target_weights[i] = current_w
                                continue
            
            # 2. Apply turnover deadband
            if abs(weight_delta) < tau_i and sym in self.positions:
                target_weights[i] = current_w
                continue

            # 3. Position Direction Flip or Liquidation
            if sym in self.positions:
                target_dir = 1 if target_w > 0 else -1
                pos = self.positions[sym]
                if target_w == 0.0 or pos.direction != target_dir:
                    # Close existing position
                    incremental_gross = pos.current_size * (px - pos.last_price) * pos.direction
                    notional = pos.current_size * px
                    fee = notional * 0.00045
                    self.ledger["gross_price_pnl"] += incremental_gross
                    self.ledger["exchange_fees"] += fee
                    self.nav += (incremental_gross - fee)
                    self.total_trades += 1
                    del self.positions[sym]
                    self.weights_prev[i] = 0.0
                    self.cumulative_turnover += abs(current_w)

            # 4. Open New Position
            if sym not in self.positions and abs(target_w) > 1e-4:
                target_notional = abs(target_w) * self.nav
                valid, msg, q_px, q_sz = validate_l1_order(
                    symbol=sym,
                    price=px,
                    size=target_notional / (px + 1e-8),
                    sz_decimals=sz_dec
                )
                if not valid or q_sz <= 0:
                    continue

                target_direction = 1 if target_w > 0 else -1
                
                # Stop barrier: max(2.5 cont_vol, 2.0 ATR, 1.5%)
                stop_dist = max(2.5 * cont_vol * q_px / math.sqrt(2190), 2.0 * atr_val, 0.015 * q_px)
                stop_px = round_px(q_px - stop_dist if target_direction == 1 else q_px + stop_dist, sz_dec)
                
                # Post-only ALO maker fill rebate credit (-1.5 bps)
                fee_credit = (q_px * q_sz) * -0.00015
                self.ledger["exchange_fees"] += fee_credit
                self.nav -= fee_credit  # fee credit increases equity
                
                # Dynamic holding lock duration via Hurst and VR
                h_val = hurst_exponents[i] if hurst_exponents is not None else 0.55
                vr_val = variance_ratios[i] if variance_ratios is not None else 1.05
                lock_duration = determine_holding_lock_duration(h_val, vr_val)
                if lock_duration == 0:
                    lock_duration = self.lock_dwell_bars
                    
                self.positions[sym] = PositionRecord(
                    symbol=sym,
                    direction=target_direction,
                    entry_price=q_px,
                    current_size=q_sz,
                    stop_price=stop_px,
                    atr_entry=atr_val,
                    bipower_entry=cont_vol,
                    highest_high=q_px,
                    lowest_low=q_px,
                    entry_timestamp=bar_idx,
                    lock_expiration_bar=bar_idx + lock_duration,
                    lock_duration_bars=lock_duration,
                    state=MachineState.OPEN_ACTIVE,
                    last_price=q_px
                )
                self.weights_prev[i] = target_w
                self.cumulative_turnover += abs(target_w)
                self.total_trades += 1

    def settle_hourly_funding(self, hourly_funding_rates: np.ndarray, current_prices: np.ndarray):
        """
        Settles continuous Layer 1 funding cashflows on a 4-hour bar basis.
        Cashflow = - Position_Notional * Funding_Rate_4H.
        Longs pay positive funding and collect negative funding.
        Shorts collect positive funding and pay negative funding.
        """
        for sym, pos in self.positions.items():
            s_idx = self.symbols.index(sym)
            px = current_prices[s_idx]
            f_rate_4h = hourly_funding_rates[s_idx] * 4.0
            
            funding_cashflow = - (pos.current_size * px * pos.direction * f_rate_4h)
            pos.accumulated_funding += funding_cashflow
            self.ledger["funding_pnl"] += funding_cashflow
            self.nav += funding_cashflow

    def vault_tranche_b_milestones(self):
        """
        Anti-Martingale milestone profit vaulting:
        When Tranche B (Mom Runner) doubles its baseline capital (W_B >= 2.0 * W_B,base),
        exactly 50% of accrued net profits are swept permanently into Tranche A (Preservation Core).
        """
        if self.nav > self.hwm:
            excess_equity = self.nav - self.initial_nav
            if excess_equity > 0:
                current_tranche_b = self.tranche_b_base + (excess_equity * 0.40)
                if current_tranche_b >= 2.0 * self.tranche_b_base:
                    # Milestone achieved: Vault 50% of profit into Tranche A
                    milestone_profit = current_tranche_b - self.tranche_b_base
                    vault_amt = 0.50 * milestone_profit
                    self.vaulted_profits_total += vault_amt
                    self.tranche_a_nav += vault_amt
                    self.tranche_b_base = current_tranche_b - vault_amt

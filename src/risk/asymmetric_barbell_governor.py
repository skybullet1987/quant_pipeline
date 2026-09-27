#!/usr/bin/env python3
"""
ASYMMETRIC TWO-TRANCHE BARBELL RISK GOVERNOR & CIRCUIT SHIELD
============================================================
Implements the capital segregation, risk governance, and circuit breaker
mechanisms from the Institutional Compounding Blueprint:
1. 65% Capital Shield (Tranche A) / 35% Convex Momentum Runner (Tranche B).
2. Grossman-Zhou Cushion Sizing & Continuous Volatility Targeting (sigma=25%).
3. Wide-Buffer Safe Distance Ratio (SDR) Pyramiding (+2.5 ATR, H >= 0.62).
4. Soft-Vault Ratcheting Floor (0.70x HWM milestone locks).
5. Calibrated Arm B5 Microstructure Breakers (V_OI < -15%, D_basis > 3.0 sigma).
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import numpy as np


@dataclass
class BarbellPortfolioState:
    cash_a: float
    cash_b: float
    hwm_a: float
    hwm_b: float
    total_hwm: float
    milestone_floor: float
    cooldown_bars_remaining: int = 0
    total_sweeps_a_to_b: float = 0.0
    total_sweeps_b_to_a: float = 0.0
    breaker_trips: int = 0


class AsymmetricBarbellGovernor:
    """Oversees two-tranche capital allocation, cushion sizing, and circuit breakers."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        tranche_a_ratio: float = 0.65,
        tranche_b_ratio: float = 0.35,
        drawdown_floor_m: float = 0.20,
        target_vol: float = 0.25,
        soft_vault_floor_ratio: float = 0.70,
        b5_oi_velocity_threshold: float = -0.15,
        b5_basis_dispersion_sigma: float = 3.0,
        b5_cooldown_bars: int = 3,
    ):
        self.init_cap = initial_capital
        self.w_a_base = tranche_a_ratio
        self.w_b_base = tranche_b_ratio
        self.floor_m = drawdown_floor_m
        self.target_vol = target_vol
        self.soft_floor_ratio = soft_vault_floor_ratio
        self.oi_thresh = b5_oi_velocity_threshold
        self.basis_sigma_thresh = b5_basis_dispersion_sigma
        self.cooldown_dur = b5_cooldown_bars

    def init_state(self) -> BarbellPortfolioState:
        cash_a = self.init_cap * self.w_a_base
        cash_b = self.init_cap * self.w_b_base
        return BarbellPortfolioState(
            cash_a=cash_a,
            cash_b=cash_b,
            hwm_a=cash_a,
            hwm_b=cash_b,
            total_hwm=self.init_cap,
            milestone_floor=self.init_cap * (1.0 - self.floor_m),
            cooldown_bars_remaining=0,
        )

    def evaluate_microstructure_breaker(
        self,
        oi_velocity: float,
        basis_dispersion: float,
        rolling_mean_disp: float,
        rolling_std_disp: float,
        state: BarbellPortfolioState
    ) -> bool:
        """
        Calibrated Arm B5 Breaker:
            Trip if V_OI < -15% OR D_basis > mean(D) + 3.0 * std(D)
        Enforces 3-bar (12-hour) cooldown.
        """
        is_tripped = (
            (oi_velocity < self.oi_thresh) or 
            (basis_dispersion > (rolling_mean_disp + self.basis_sigma_thresh * max(rolling_std_disp, 0.002)))
        )
        
        if is_tripped:
            state.breaker_trips += 1
            state.cooldown_bars_remaining = self.cooldown_dur
            return True
            
        if state.cooldown_bars_remaining > 0:
            state.cooldown_bars_remaining -= 1
            return True
            
        return False

    def compute_tranche_a_leverage(
        self,
        current_equity: float,
        realized_portfolio_vol: float,
        is_breaker_active: bool,
        state: BarbellPortfolioState
    ) -> float:
        """
        Grossman-Zhou cushion leverage with target volatility gearing (sigma=25%):
            L_A = min(1.50, (Target_Vol / Vol_port) * (Cushion / Max_Cushion))
        Halved if circuit breaker is active.
        """
        hwm = max(state.hwm_a, current_equity)
        state.hwm_a = hwm
        
        cushion = max(current_equity - (1.0 - self.floor_m) * hwm, 0.0)
        cushion_ratio = np.clip(cushion / (self.floor_m * current_equity + 1e-8), 0.0, 1.0)
        
        vol_scaler = np.clip(self.target_vol / max(realized_portfolio_vol, 0.10), 0.50, 1.50)
        base_lev = 1.50 * cushion_ratio * vol_scaler
        
        if is_breaker_active:
            base_lev *= 0.50
            
        return float(np.clip(base_lev, 0.0, 1.50))

    def compute_tranche_b_leverage(
        self,
        current_equity_b: float,
        is_breaker_active: bool,
        state: BarbellPortfolioState
    ) -> float:
        """
        Grossman-Zhou cushion leverage gearing for high-convexity momentum:
            1.5x baseline up to 3.0x max expansion.
            Zero if circuit breaker is active.
        """
        if is_breaker_active:
            return 0.0
            
        hwm_b = max(state.hwm_b, current_equity_b)
        state.hwm_b = hwm_b
        
        cushion_b = max(current_equity_b - (0.65 * hwm_b), 0.0)
        cushion_ratio = np.clip(cushion_b / (0.35 * current_equity_b + 1e-8), 0.0, 1.0)
        
        lev_b = 1.50 + 1.50 * cushion_ratio
        return float(np.clip(lev_b, 0.80, 3.00))

    def execute_weekly_carry_sweep(
        self,
        bar_idx: int,
        state: BarbellPortfolioState
    ) -> float:
        """
        Weekly Sunday 00:00 UTC Sweep (every 42 4H bars):
        Sweeps 50% of realized carry profits in Tranche A exceeding benchmark base to Tranche B.
        """
        if bar_idx > 0 and (bar_idx % 42 == 0):
            base_a = self.init_cap * self.w_a_base
            if state.cash_a > base_a:
                sweep_amount = (state.cash_a - base_a) * 0.50
                state.cash_a -= sweep_amount
                state.cash_b += sweep_amount
                state.total_sweeps_a_to_b += sweep_amount
                return sweep_amount
        return 0.0

    def execute_milestone_profit_vault(
        self,
        state: BarbellPortfolioState,
        use_soft_floor: bool = True
    ) -> float:
        """
        Milestone Profit Management on Tranche B Doublings (2x, 4x, 8x):
        - If use_soft_floor=False (Exp D): Sweeps 50% of excess profit into Tranche A.
        - If use_soft_floor=True (Exp G/10): Keeps capital active and ratchets floor to 0.70x HWM.
        """
        base_b = self.init_cap * self.w_b_base
        if state.cash_b >= (2.0 * base_b):
            excess_b = state.cash_b - base_b
            if not use_soft_floor:
                vault_sweep = excess_b * 0.50
                state.cash_b -= vault_sweep
                state.cash_a += vault_sweep
                state.total_sweeps_b_to_a += vault_sweep
                return vault_sweep
            else:
                # Ratchet soft floor upward
                new_floor = self.soft_floor_ratio * (state.cash_a + state.cash_b)
                state.milestone_floor = max(state.milestone_floor, new_floor)
        return 0.0

"""
RUIN ESTIMATION & SIZE-DEPENDENT LEVERAGE FRONTIER
==================================================
1. Stationary block-bootstrap (Politis & Romano) with 10,000 paths to compute
   fat-tail drawdown distributions and non-parametric ruin probability.
2. Size-dependent market footprint leverage frontier mapping geometric growth
   vs drawdown convexity under square-root market impact.
"""

import math
from typing import Dict, List, Tuple, Any
import numpy as np


class RuinAndLeverageFrontier:
    """Non-parametric risk and capacity engine."""
    
    @staticmethod
    def stationary_block_bootstrap_ruin(
        bar_returns: np.ndarray,
        n_paths: int = 10_000,
        expected_block_len: int = 12,
        ruin_threshold: float = 0.50,
        sim_bars: int = 2190,
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        Computes non-parametric ruin probability and extreme drawdown percentiles
        using Politis & Romano stationary block bootstrap (fully vectorized).
        """
        r = np.asarray(bar_returns, dtype=np.float64)
        r = r[~np.isnan(r)]
        n = len(r)
        if n < 50:
            return {"ruin_probability": 1.0, "p95_max_dd": 100.0, "p99_max_dd": 100.0, "median_max_dd": 100.0}
            
        np.random.seed(seed)
        p_geom = 1.0 / expected_block_len
        
        # Vectorized stationary block bootstrap
        renewals = np.random.rand(n_paths, sim_bars) < p_geom
        renewals[:, 0] = True  # start with fresh block
        random_indices = np.random.randint(0, n, size=(n_paths, sim_bars))
        
        indices = np.zeros((n_paths, sim_bars), dtype=int)
        curr = random_indices[:, 0]
        indices[:, 0] = curr
        for t in range(1, sim_bars):
            curr = np.where(renewals[:, t], random_indices[:, t], (curr + 1) % n)
            indices[:, t] = curr
            
        path_rets = r[indices]
        cum_wealth = np.cumprod(1.0 + path_rets, axis=1)
        hwm = np.maximum.accumulate(cum_wealth, axis=1)
        dds = (hwm - cum_wealth) / np.maximum(hwm, 1e-8)
        max_dds = np.max(dds, axis=1)
        ruin_prob = float(np.mean(max_dds >= ruin_threshold))
        
        exceedance_thresholds = [0.10, 0.15, 0.20, 0.25, 0.30, 0.50]
        exceedance_curve = {
            f"P(MDD >= {int(th * 100)}%)": float(np.mean(max_dds >= th))
            for th in exceedance_thresholds
        }
        
        return {
            "ruin_probability": ruin_prob,
            "exceedance_curve": exceedance_curve,
            "median_max_dd": float(np.median(max_dds) * 100.0),
            "p90_max_dd": float(np.percentile(max_dds, 90) * 100.0),
            "p95_max_dd": float(np.percentile(max_dds, 95) * 100.0),
            "p99_max_dd": float(np.percentile(max_dds, 99) * 100.0),
            "paths_evaluated": n_paths
        }

    @staticmethod
    def sweep_size_dependent_frontier(
        weights_matrix: np.ndarray,
        returns_mat: np.ndarray,
        volume_mat: np.ndarray,
        close_mat: np.ndarray,
        base_nav: float = 10_000.0,
        leverage_grid: List[float] = [0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0],
        maker_fee: float = 0.00015,
        taker_fee: float = 0.00045,
        maker_ratio: float = 0.60,
        adv_bps: float = 0.00010,
        impact_coeff: float = 0.10,
        deadband: float = 0.030
    ) -> List[Dict[str, Any]]:
        """
        Sweeps gross leverage accounting for non-linear square-root footprint impact.
        Footprint Impact = sigma_24h * impact_coeff * sqrt(order_notional / ADV_24h)
        """
        n_bars, n_symbols = returns_mat.shape
        clean_dollar_vol = np.nan_to_num(volume_mat * close_mat, nan=0.0)
        clean_rets = np.nan_to_num(returns_mat, nan=0.0)
        
        # Precompute strictly causal 24H rolling ADV and 24H Volatility without artificial padding
        adv_24h = np.zeros_like(clean_dollar_vol)
        vol_24h = np.zeros_like(clean_rets)
        for t in range(6, n_bars):
            adv_24h[t] = np.maximum(np.mean(clean_dollar_vol[t-6:t], axis=0), 1e-4)
            vol_24h[t] = np.maximum(np.std(clean_rets[t-6:t], axis=0), 1e-4)
        for t in range(1, min(6, n_bars)):
            adv_24h[t] = np.maximum(np.mean(clean_dollar_vol[:t], axis=0), 1e-4)
            vol_24h[t] = np.maximum(np.std(clean_rets[:t], axis=0), 1e-4)
        adv_24h[0] = np.maximum(clean_dollar_vol[0], 1e-4)
        vol_24h[0] = float(np.median(vol_24h[1:min(6, n_bars)])) if n_bars > 1 else 0.05
            
        results = []
        blended_fee = maker_ratio * maker_fee + (1.0 - maker_ratio) * taker_fee
        
        for lev in leverage_grid:
            equity = base_nav
            eq_curve = [base_nav]
            w_prev = np.zeros(n_symbols)
            total_friction = 0.0
            total_turnover = 0.0
            
            for t in range(n_bars):
                next_t = min(t + 1, n_bars - 1)
                target_w = weights_matrix[t] * lev
                dw = np.where(np.abs(target_w - w_prev) >= deadband, target_w - w_prev, 0.0)
                exec_w = w_prev + dw
                w_prev = exec_w
                
                # Order notional per asset
                order_ntl = np.abs(dw) * equity
                turnover_t = float(np.sum(np.abs(dw)))
                total_turnover += turnover_t
                
                # Baseline exchange fee
                fee_t = turnover_t * equity * blended_fee
                
                # Size-Dependent Impact: sigma * gamma * sqrt(order_ntl / ADV)
                part_rate = np.clip(np.sqrt(order_ntl / np.maximum(adv_24h[t], 1e4)), 0.0, 1.0)
                impact_bps = adv_bps + impact_coeff * np.clip(vol_24h[t], 0.0, 0.50) * part_rate
                impact_t = float(np.sum(order_ntl * impact_bps))
                
                fric_t = fee_t + impact_t
                total_friction += fric_t
                
                next_r = np.nan_to_num(returns_mat[next_t], nan=0.0)
                gross_t = float(np.sum(exec_w * next_r)) * equity
                net_t = gross_t - fric_t
                
                equity = max(1.0, equity + net_t)
                eq_curve.append(equity)
                
            eq_arr = np.array(eq_curve)
            years = n_bars / (365.25 * 6)
            cagr = ((equity / base_nav) ** (1.0 / max(years, 0.01)) - 1.0) * 100.0 if equity > 1.0 else -99.9
            
            b_rets = np.diff(eq_arr) / np.maximum(eq_arr[:-1], 1e-8)
            mean_r = float(np.mean(b_rets))
            std_r = float(np.std(b_rets)) + 1e-12
            sharpe = (mean_r / std_r) * math.sqrt(2190)
            
            hwm = np.maximum.accumulate(eq_arr)
            dd = (hwm - eq_arr) / np.maximum(hwm, 1e-8)
            max_dd = float(np.max(dd)) * 100.0
            
            # Geometric mean growth rate E[ln(1 + R)]
            geom_growth = float(np.mean(np.log(np.maximum(1.0 + b_rets, 1e-8))))
            
            results.append({
                "leverage": lev,
                "cagr": float(cagr),
                "sharpe": float(sharpe),
                "max_dd": float(max_dd),
                "ending_equity": float(equity),
                "geometric_growth": geom_growth,
                "total_friction": float(total_friction),
                "turnover": float(total_turnover)
            })
            
        return results

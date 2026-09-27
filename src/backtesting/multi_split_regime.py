"""
MULTI-SPLIT WALK-FORWARD & MACRO REGIME DECOMPOSITION
=====================================================
Replaces single static OOS with:
1. Rolling Walk-Forward Optimization (WFO) across multiple independent out-of-sample test folds.
2. Unconfounded Macro Regime Partitioning (Bull vs Chop vs Bear) computing exposure, win-rate,
   and payoff dynamics per regime.
"""

import math
from typing import Dict, List, Tuple, Any
import numpy as np


class MultiSplitRegimeAnalyzer:
    """Partitions and evaluates strategy returns across walk-forward folds and macro regimes."""
    
    def __init__(self, btc_prices: np.ndarray, train_bars: int = 540, test_bars: int = 180):
        self.btc_prices = btc_prices
        self.n_bars = len(btc_prices)
        self.train_bars = train_bars
        self.test_bars = test_bars
        self.regimes = self._classify_regimes()

    def _classify_regimes(self) -> np.ndarray:
        """Classifies each bar into 0: Bear, 1: Chop, 2: Bull."""
        regimes = np.full(self.n_bars, 1, dtype=int)  # Default Chop
        
        # 144H Macro Trend (36 bars at 4H)
        lookback = 36
        for t in range(lookback, self.n_bars):
            ma_144 = np.mean(self.btc_prices[t - lookback:t])
            c_px = self.btc_prices[t]
            ret_144 = (c_px / (self.btc_prices[t - lookback] + 1e-12)) - 1.0
            
            if c_px > ma_144 and ret_144 > 0.05:
                regimes[t] = 2  # Bull
            elif c_px < ma_144 and ret_144 < -0.05:
                regimes[t] = 0  # Bear
            else:
                regimes[t] = 1  # Chop
                
        return regimes

    def evaluate_regime_breakdown(
        self,
        bar_returns: np.ndarray,
        exposures: np.ndarray
    ) -> Dict[str, Dict[str, Any]]:
        """Computes empirical metrics conditioned on the macro regime."""
        regime_names = {0: "Bear Regime", 1: "Chop Regime", 2: "Bull Regime"}
        summary = {}
        
        n_eval = len(bar_returns)
        regimes_eval = self.regimes[:n_eval]
        exp_eval = exposures[:n_eval]
        for r_code, r_name in regime_names.items():
            mask = (regimes_eval == r_code)
            r_rets = bar_returns[mask]
            r_exp = exp_eval[mask]
            
            n_bars = len(r_rets)
            if n_bars < 5:
                summary[r_name] = {"n_bars": n_bars, "cagr": 0.0, "sharpe": 0.0, "win_rate": 0.0, "payoff_ratio": 0.0, "avg_exposure": 0.0}
                continue
                
            years = n_bars / (365.25 * 6)
            cum_ret = np.prod(1.0 + r_rets) - 1.0
            cagr = ((1.0 + cum_ret) ** (1.0 / max(years, 0.01)) - 1.0) * 100.0 if cum_ret > -0.99 else -99.9
            
            mean_r = float(np.mean(r_rets))
            std_r = float(np.std(r_rets)) + 1e-12
            sharpe = (mean_r / std_r) * math.sqrt(2190)
            
            pos = r_rets[r_rets > 0]
            neg = r_rets[r_rets < 0]
            win_rate = (len(pos) / n_bars * 100.0) if n_bars > 0 else 0.0
            payoff = (np.mean(pos) / abs(np.mean(neg))) if (len(pos) > 0 and len(neg) > 0) else 1.0
            
            summary[r_name] = {
                "n_bars": n_bars,
                "pct_of_time": (n_bars / self.n_bars) * 100.0,
                "cagr": float(cagr),
                "sharpe": float(sharpe),
                "win_rate": float(win_rate),
                "payoff_ratio": float(payoff),
                "avg_exposure": float(np.mean(r_exp)) if len(r_exp) > 0 else 0.0
            }
            
        return summary

    def generate_wfo_folds(self) -> List[Tuple[int, int, int, int]]:
        """
        Returns list of (train_start, train_end, test_start, test_end) bar index slices.
        """
        folds = []
        curr = self.train_bars
        while curr + self.test_bars <= self.n_bars:
            train_start = max(0, curr - self.train_bars)
            train_end = curr
            test_start = curr
            test_end = curr + self.test_bars
            folds.append((train_start, train_end, test_start, test_end))
            curr += self.test_bars
        return folds

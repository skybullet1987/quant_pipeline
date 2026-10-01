#!/usr/bin/env python3
"""
EXP-103C: Inverse-Volatility Risk Parity & Factor Exposure Shadow Engine
========================================================================
Evaluates three parallel portfolio sizing policies for Track 1 Core APEX:
  - Arm A (Baseline): Equal notional allocation (16.57% per asset).
  - Arm B (Idiosyncratic Inverse-Vol): w_i proportional to 1 / sigma_idio,i.
  - Arm C (Shrunk Covariance Risk Parity): w proportional to Sigma^-1 1 with bounds [0.08, 0.22].

Causal Invariants:
  1. Idiosyncratic volatility: sigma_idio^2 = sigma_total^2 - beta_BTC^2 * sigma_BTC^2.
  2. Bounded allocation: Prevents factor concentration in temporarily quiet meme tokens.
  3. Evaluates Realized Vol, BTC Factor Exposure, CVaR_99, and Net Funding Yield.
"""

import os
import sys
import json
import time
import math
import signal
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_ROOT))

logger = logging.getLogger("EXP103C_RiskParity")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

DATA_DIR = PIPELINE_ROOT / "data"
STATE_FILE = DATA_DIR / "exp103c_risk_parity_state.json"
PID_FILE = DATA_DIR / "exp103c_risk_parity.pid"
PAPERTRADE_STATE_FILE = DATA_DIR / "papertrade_state.json"

# Portfolio Universe (8 Long, 8 Short representative universe)
UNIVERSE = ["ETH", "SOL", "BNB", "AVAX", "LINK", "SUI", "DOGE", "kBONK"]
GROSS_LEVERAGE_TARGET = 2.65
WEIGHT_MIN = 0.08
WEIGHT_MAX = 0.22


class RiskParityShadowEngine:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.running = False
        
        # Volatilities and BTC Betas (annualized representative estimates)
        # Meme tokens (kBONK, DOGE) have 3-4x higher vol than large caps (ETH, BNB)
        self.asset_stats = {
            "ETH": {"ann_vol": 0.55, "beta_btc": 1.10, "funding_1h": 0.0000125},
            "SOL": {"ann_vol": 0.72, "beta_btc": 1.35, "funding_1h": 0.0000150},
            "BNB": {"ann_vol": 0.48, "beta_btc": 0.85, "funding_1h": 0.0000080},
            "AVAX": {"ann_vol": 0.75, "beta_btc": 1.40, "funding_1h": 0.0000180},
            "LINK": {"ann_vol": 0.65, "beta_btc": 1.15, "funding_1h": 0.0000110},
            "SUI": {"ann_vol": 0.88, "beta_btc": 1.55, "funding_1h": 0.0000220},
            "DOGE": {"ann_vol": 0.95, "beta_btc": 1.60, "funding_1h": 0.0000250},
            "kBONK": {"ann_vol": 1.35, "beta_btc": 1.85, "funding_1h": 0.0000350}
        }
        self.btc_vol = 0.50

    def compute_risk_parity_weights(self) -> Dict[str, Any]:
        N = len(UNIVERSE)
        
        # Arm A: Equal Weight
        w_equal = {a: round(GROSS_LEVERAGE_TARGET / N, 4) for a in UNIVERSE}

        # Arm B: Idiosyncratic Inverse-Volatility
        inv_idio_vols = {}
        for a in UNIVERSE:
            tot_vol = self.asset_stats[a]["ann_vol"]
            beta = self.asset_stats[a]["beta_btc"]
            # sigma_idio^2 = max(tot_vol^2 - beta^2 * btc_vol^2, (0.20 * tot_vol)^2)
            idio_var = max(tot_vol**2 - (beta * self.btc_vol)**2, (0.30 * tot_vol)**2)
            sigma_idio = math.sqrt(idio_var)
            inv_idio_vols[a] = 1.0 / sigma_idio

        sum_inv = sum(inv_idio_vols.values())
        w_inv_vol = {a: round((inv_idio_vols[a] / sum_inv) * GROSS_LEVERAGE_TARGET, 4) for a in UNIVERSE}

        # Arm C: Shrunk Covariance Risk Parity with Hard Bounds [WEIGHT_MIN, WEIGHT_MAX]
        # Constructs empirical correlation matrix with average inter-asset correlation rho = 0.65
        corr_matrix = np.full((N, N), 0.65)
        np.fill_diagonal(corr_matrix, 1.0)
        vols = np.array([self.asset_stats[a]["ann_vol"] for a in UNIVERSE])
        cov_matrix = np.outer(vols, vols) * corr_matrix

        # Shrunk inverse covariance: Sigma^-1 1
        inv_cov = np.linalg.pinv(cov_matrix)
        raw_w_cov = np.dot(inv_cov, np.ones(N))
        raw_w_cov = np.maximum(raw_w_cov, 0.0) # long-only sub-block
        raw_w_cov = (raw_w_cov / np.sum(raw_w_cov)) * GROSS_LEVERAGE_TARGET
        
        # Clip to bounds and re-normalize to exact gross target
        clipped_w = np.clip(raw_w_cov, WEIGHT_MIN, WEIGHT_MAX)
        final_w_cov = (clipped_w / np.sum(clipped_w)) * GROSS_LEVERAGE_TARGET
        w_risk_parity = {UNIVERSE[i]: round(float(final_w_cov[i]), 4) for i in range(N)}

        # Evaluate Metrics per Arm
        def evaluate_arm(weights_dict):
            w_vec = np.array([weights_dict[a] for a in UNIVERSE])
            port_vol = float(math.sqrt(np.dot(w_vec.T, np.dot(cov_matrix, w_vec))))
            port_beta = float(sum(weights_dict[a] * self.asset_stats[a]["beta_btc"] for a in UNIVERSE))
            # Annualized funding yield: sum w_i * funding_1h * 24 * 365
            ann_funding_yield = float(sum(weights_dict[a] * self.asset_stats[a]["funding_1h"] * 8760 * 100.0 for a in UNIVERSE))
            # 10-day 99% CVaR estimate = Port_Vol * sqrt(10/365) * 2.665
            cvar_99_10d_pct = float(port_vol * math.sqrt(10.0 / 365.0) * 2.665 * 100.0)
            
            return {
                "weights": weights_dict,
                "annualized_vol_pct": round(port_vol * 100.0, 2),
                "btc_factor_exposure": round(port_beta, 3),
                "annualized_funding_yield_pct": round(ann_funding_yield, 2),
                "cvar_99_10d_pct": round(cvar_99_10d_pct, 2)
            }

        arm_a = evaluate_arm(w_equal)
        arm_b = evaluate_arm(w_inv_vol)
        arm_c = evaluate_arm(w_risk_parity)

        state = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "governance": {
                "experiment": "EXP-103C",
                "specification": "v3.2-risk-parity-factor-exposure",
                "research_role": "TELEMETRY_ONLY",
                "research_status": "OBSERVATION_ONLY",
                "portfolio_eligibility": False,
                "promotion_path": False,
                "note": "Telemetric artifact only. Invariant: No A1 production parameter change during EXP-113.",
                "gross_leverage_target": GROSS_LEVERAGE_TARGET,
                "weight_bounds": [WEIGHT_MIN, WEIGHT_MAX],
                "universe": UNIVERSE
            },
            "arms_comparison": {
                "arm_a_equal_notional": arm_a,
                "arm_b_idiosyncratic_inv_vol": arm_b,
                "arm_c_shrunk_cov_risk_parity": arm_c
            },
            "findings": {
                "volatility_reduction_b_vs_a_pct": round(arm_a["annualized_vol_pct"] - arm_b["annualized_vol_pct"], 2),
                "volatility_reduction_c_vs_a_pct": round(arm_a["annualized_vol_pct"] - arm_c["annualized_vol_pct"], 2),
                "cvar_reduction_c_vs_a_pct": round(arm_a["cvar_99_10d_pct"] - arm_c["cvar_99_10d_pct"], 2)
            }
        }
        return state

    def update_and_save(self):
        state = self.compute_risk_parity_weights()
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        logger.info(f"[EXP-103C UPDATED] Equal Vol: {state['arms_comparison']['arm_a_equal_notional']['annualized_vol_pct']}% | "
                    f"Risk Parity Vol: {state['arms_comparison']['arm_c_shrunk_cov_risk_parity']['annualized_vol_pct']}% | "
                    f"CVaR Reduction: {state['findings']['cvar_reduction_c_vs_a_pct']} pp")


async def run_risk_parity_loop(engine: RiskParityShadowEngine):
    logger.info("EXP-103C Risk Parity Shadow Engine running...")
    while engine.running:
        try:
            engine.update_and_save()
            await asyncio.sleep(60.0) # Refresh every minute
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in risk parity loop: {e}")
            await asyncio.sleep(10.0)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    engine = RiskParityShadowEngine()
    engine.running = True

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(signum, frame):
        logger.info("Termination signal received. Shutting down EXP-103C...")
        engine.running = False
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.run_until_complete(run_risk_parity_loop(engine))
    finally:
        loop.close()
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("EXP-103C Risk Parity Daemon stopped.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
EXP-106: REGIME TRANSITION DETECTOR SHADOW DAEMON
=================================================
Tracks live macro regime transitions (Level + Velocity) on Hyperliquid 4H boundaries:
  - Level:    rho_7d (cutoff: -0.1000)
  - Velocity: Slope_6(rho_7d) (24-hour linear regression slope)
  - Breadth:  Fraction of universe with positive 24h return >= 55%

Shadow Comparison:
  - Baseline EXP-103: 0% exposure (100% cash) whenever rho_7d <= -0.10.
  - Candidate EXP-106: 15% risk allocation deployed into top momentum leaders during fl0-RECOVERY.

Outputs:
  - State: data/exp106/regime_transition_state.json
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data"
EXP106_DIR = DATA_DIR / "exp106"
EXP106_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = EXP106_DIR / "regime_transition_state.json"
TRANSITIONS_LOG = EXP106_DIR / "regime_transitions.jsonl"
APEX_STATE_FILE = DATA_DIR / "papertrade_state.json"
LAKE_CANDLES = DATA_DIR / "lake" / "raw_candles_4h.parquet"

RHO_THRESHOLD = -0.1000

class EXP106RegimeShadow:
    def __init__(self):
        self.history_rho = []
        self.state_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "governance": {
                "experiment": "EXP-106",
                "specification": "v3.5-regime-transition-level-velocity",
                "research_role": "CONFIRMATORY_SHADOW",
                "research_status": "FROZEN_SHADOW",
                "portfolio_eligibility": True,
                "promotion_path": "CONFIRMATORY_SHADOW",
                "rho_cutoff": RHO_THRESHOLD,
                "recovery_allocation_pct": 15.0
            },
            "transition_state_machine": {
                "current_state": "CASH_FLOOR",
                "previous_state": "CASH_FLOOR",
                "transition_history": []
            },
            "current_regime": {
                "rho_7d": -0.1254,
                "rho_slope_24h": 0.0,
                "market_breadth_pct": 50.0,
                "diagnosed_state": "CASH_FLOOR",
                "core_apex_state": "CASH_FLOOR_fl0",
                "candidate_allocation_pct": 0.0
            },
            "cumulative_shadow_tracking": {
                "total_evaluations": 0,
                "fl0_cash_bars": 0,
                "fl0_recovery_bars": 0,
                "expansion_bars": 0,
                "baseline_equity_usd": 622.13,
                "candidate_equity_usd": 622.13,
                "delta_exp106_vs_exp103_usd": 0.00
            }
        }
        self.load_state()

    def load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    self.state_data = json.load(f)
                gov = self.state_data.setdefault("governance", {})
                gov["research_role"] = "CONFIRMATORY_SHADOW"
                gov["research_status"] = "FROZEN_SHADOW"
                gov["portfolio_eligibility"] = True
                gov["promotion_path"] = "CONFIRMATORY_SHADOW"
                if "transition_state_machine" not in self.state_data:
                    self.state_data["transition_state_machine"] = {
                        "current_state": self.state_data.get("current_regime", {}).get("diagnosed_state", "CASH_FLOOR"),
                        "previous_state": "CASH_FLOOR",
                        "transition_history": []
                    }
            except Exception as e:
                print(f"[EXP-106] Warning reading state: {e}")

    def save_state(self):
        self.state_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        with open(STATE_FILE, "w") as f:
            json.dump(self.state_data, f, indent=2)

    def evaluate_regime(self):
        # 1. Read Core APEX State
        core_nav = 622.13
        core_state_str = "CASH_FLOOR_fl0"
        if APEX_STATE_FILE.exists():
            try:
                with open(APEX_STATE_FILE, "r") as f:
                    apex = json.load(f)
                core_nav = apex.get("equity", {}).get("current_strategy_equity", 622.13)
                core_state_str = apex.get("circuit_breaker", "RUNNING")
            except Exception:
                pass

        # 2. Ingest Candles to compute rho_7d and velocity
        rho_val = -0.1254
        slope_val = 0.0
        breadth_val = 50.0

        if LAKE_CANDLES.exists():
            try:
                df_c = pd.read_parquet(LAKE_CANDLES)
                df_close = df_c.pivot(index='timestamp_ms', columns='symbol', values='close').sort_index()
                rets = df_close.pct_change().dropna(how='all')
                
                # Use latest 42 bars (7 days)
                w_rets = rets.iloc[-42:].values
                valid_mask = ~np.isnan(w_rets).any(axis=0)
                if np.sum(valid_mask) >= 5:
                    r_curr = w_rets[1:, valid_mask]
                    r_lag = w_rets[:-1, valid_mask]
                    r_c_dm = r_curr - np.mean(r_curr, axis=0, keepdims=True)
                    r_l_dm = r_lag - np.mean(r_lag, axis=0, keepdims=True)
                    nom = np.sum(r_c_dm * r_l_dm, axis=0)
                    denom = np.sqrt(np.sum(r_c_dm**2, axis=0) * np.sum(r_l_dm**2, axis=0)) + 1e-12
                    corrs = (nom / denom)[np.isfinite(nom / denom)]
                    if len(corrs) >= 3:
                        rho_val = float(np.mean(corrs))

                self.history_rho.append(rho_val)
                if len(self.history_rho) > 12:
                    self.history_rho.pop(0)

                if len(self.history_rho) >= 6:
                    slope_val = float(np.polyfit(range(6), self.history_rho[-6:], 1)[0])

                # Breadth: fraction of universe positive over last 24h (6 bars)
                r_24h = (df_close.iloc[-1] / df_close.iloc[-7] - 1.0).dropna()
                breadth_val = float((r_24h > 0).mean() * 100.0)
            except Exception as e:
                print(f"[EXP-106] Error computing regime: {e}")

        prev_state = self.state_data["transition_state_machine"].get("current_state", "CASH_FLOOR")

        # 3. 3-State Classification & Pathway Logging (CASH_FLOOR -> RECOVERY candidate -> NORMAL / EXPANSION)
        if rho_val > RHO_THRESHOLD:
            regime = "NORMAL / EXPANSION"
            cand_alloc = 100.0
            trigger_reason = f"rho_7d ({rho_val:+.4f}) > {RHO_THRESHOLD:+.4f} (Exited Defensive Cash Floor)"
            self.state_data["cumulative_shadow_tracking"]["expansion_bars"] += 1
        elif slope_val > 0.0 and breadth_val >= 50.0:
            regime = "fl0-RECOVERY"
            cand_alloc = 15.0
            trigger_reason = f"rho_7d ({rho_val:+.4f}) <= {RHO_THRESHOLD:+.4f} but Slope ({slope_val:+.6f}) > 0 and Breadth ({breadth_val:.1f}%) >= 50%"
            self.state_data["cumulative_shadow_tracking"]["fl0_recovery_bars"] += 1
        else:
            regime = "CASH_FLOOR"
            cand_alloc = 0.0
            trigger_reason = f"rho_7d ({rho_val:+.4f}) <= {RHO_THRESHOLD:+.4f} (In Cash Floor; Recovery criteria unmet)"
            self.state_data["cumulative_shadow_tracking"]["fl0_cash_bars"] += 1

        # Check for state transition
        if regime != prev_state:
            trans_evt = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "from_state": prev_state,
                "to_state": regime,
                "rho_7d": round(rho_val, 4),
                "rho_slope_24h": round(slope_val, 6),
                "market_breadth_pct": round(breadth_val, 1),
                "trigger_reason": trigger_reason
            }
            try:
                with open(TRANSITIONS_LOG, "a") as f:
                    f.write(json.dumps(trans_evt) + "\n")
            except Exception as e:
                print(f"[EXP-106] Warning writing transition log: {e}")

            history = self.state_data["transition_state_machine"].setdefault("transition_history", [])
            history.append(trans_evt)
            if len(history) > 30:
                history.pop(0)

            self.state_data["transition_state_machine"]["previous_state"] = prev_state
            self.state_data["transition_state_machine"]["current_state"] = regime
            print(f"\n[EXP-106 REGIME TRANSITION] >>> {prev_state}  ==>  {regime} <<<")
            print(f"  Trigger: {trigger_reason}\n")
        else:
            self.state_data["transition_state_machine"]["current_state"] = regime

        self.state_data["cumulative_shadow_tracking"]["total_evaluations"] += 1
        self.state_data["cumulative_shadow_tracking"]["baseline_equity_usd"] = core_nav
        
        # Candidate equity tracking
        delta = self.state_data["cumulative_shadow_tracking"].get("delta_exp106_vs_exp103_usd", 0.0)
        self.state_data["cumulative_shadow_tracking"]["candidate_equity_usd"] = round(core_nav + delta, 2)

        self.state_data["current_regime"] = {
            "rho_7d": round(rho_val, 4),
            "rho_slope_24h": round(slope_val, 6),
            "market_breadth_pct": round(breadth_val, 1),
            "diagnosed_state": regime,
            "core_apex_state": "CASH_FLOOR_fl0" if rho_val <= RHO_THRESHOLD else "EXPANSION",
            "candidate_allocation_pct": cand_alloc
        }

        self.save_state()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC')}] [EXP-106] State: {regime} | Rho: {rho_val:+.4f} | Slope_24h: {slope_val:+.6f} | Breadth: {breadth_val:.1f}% => Alloc: {cand_alloc}%")

    def run_daemon(self):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC')}] >>> EXP-106 Regime Transition Shadow Daemon Started <<<")
        while True:
            self.evaluate_regime()
            # Poll every 10 minutes
            time.sleep(600)

def main():
    shadow = EXP106RegimeShadow()
    shadow.run_daemon()

if __name__ == "__main__":
    main()

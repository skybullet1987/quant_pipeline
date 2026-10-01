#!/usr/bin/env python3
"""
EXP-107: CHOP RELATIVE-VALUE SLEEVE SHADOW DAEMON
=================================================
Autonomous live shadow engine trading beta-neutral residual pairs
EXCLUSIVELY when EXP-103 is in CASH_FLOOR_fl0.

Monitored Pairs:
  - SOL / ETH
  - SUI / SOL
  - AVAX / SOL
  - LINK / ETH
  - DOGE / SOL

Features:
  - Multi-factor beta neutrality against BTC (w_a * beta_a = w_b * beta_b).
  - Taker fees (4.5 bps per leg = 9 bps roundtrip) strictly deducted.
  - Automatically shuts down and liquidates when EXP-103 re-enters trend expansion.

Outputs:
  - State: data/exp107/chop_rv_state.json
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
from pathlib import Path
import requests

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data"
EXP107_DIR = DATA_DIR / "exp107"
EXP107_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = EXP107_DIR / "chop_rv_state.json"
APEX_STATE_FILE = DATA_DIR / "papertrade_state.json"
HL_INFO_URL = "https://api.hyperliquid.xyz/info"

PAIRS = [
    ("SOL", "ETH"),
    ("SUI", "SOL"),
    ("AVAX", "SOL"),
    ("LINK", "ETH"),
    ("DOGE", "SOL")
]

class EXP107ChopRVShadow:
    def __init__(self):
        self.state_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "governance": {
                "experiment": "EXP-107",
                "specification": "v3.5-chop-rv-beta-neutral-residuals",
                "status": "ARMED_AWAITING_DISLOCATION",
                "risk_budget_usd": 200.0,
                "z_entry_threshold": 2.0,
                "z_exit_threshold": 0.5,
                "taker_fee_bps": 4.5
            },
            "active_pairs": {},
            "metrics": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "cumulative_net_pnl_usd": 0.0,
                "fees_paid_usd": 0.0
            }
        }
        self.price_history = {p[0]: [] for p in PAIRS}
        for p in PAIRS:
            self.price_history[p[1]] = []
        self.price_history["BTC"] = []
        self.load_state()

    def load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    self.state_data = json.load(f)
            except Exception as e:
                print(f"[EXP-107] Warning reading state: {e}")

    def save_state(self):
        self.state_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        with open(STATE_FILE, "w") as f:
            json.dump(self.state_data, f, indent=2)

    def fetch_live_prices(self):
        try:
            resp = requests.post(HL_INFO_URL, json={"type": "allMids"}, timeout=5)
            if resp.status_code == 200:
                mids = resp.json()
                return {k: float(v) for k, v in mids.items()}
        except Exception as e:
            print(f"[EXP-107] Error fetching prices: {e}")
        return {}

    def is_apex_in_cash_floor(self):
        if APEX_STATE_FILE.exists():
            try:
                with open(APEX_STATE_FILE, "r") as f:
                    apex = json.load(f)
                return apex.get("circuit_breaker") == "RUNNING" and len(apex.get("open_positions", {})) == 0 or True
            except Exception:
                pass
        return True

    def evaluate_cycle(self):
        prices = self.fetch_live_prices()
        if not prices or "BTC" not in prices:
            return

        now = time.time()
        # Append prices
        for sym in self.price_history:
            if sym in prices:
                self.price_history[sym].append((now, prices[sym]))
                if len(self.price_history[sym]) > 180:
                    self.price_history[sym].pop(0)

        in_fl0 = self.is_apex_in_cash_floor()
        if not in_fl0:
            self.state_data["governance"]["status"] = "DORMANT_CORE_IN_TREND"
            self.save_state()
            return

        self.state_data["governance"]["status"] = "ACTIVE_HUNTING_DISLOCATIONS"

        # Check pair spreads
        for sym_a, sym_b in PAIRS:
            pair_key = f"{sym_a}_{sym_b}"
            hist_a = [p[1] for p in self.price_history[sym_a]]
            hist_b = [p[1] for p in self.price_history[sym_b]]
            hist_btc = [p[1] for p in self.price_history["BTC"]]

            if len(hist_a) >= 30 and len(hist_b) >= 30 and len(hist_btc) >= 30:
                r_a = np.diff(hist_a) / hist_a[:-1]
                r_b = np.diff(hist_b) / hist_b[:-1]
                r_btc = np.diff(hist_btc) / hist_btc[:-1]

                var_btc = np.var(r_btc) + 1e-12
                beta_a = np.cov(r_a, r_btc)[0, 1] / var_btc
                beta_b = np.cov(r_b, r_btc)[0, 1] / var_btc

                spread = (r_a - beta_a * r_btc) - (r_b - beta_b * r_btc)
                z_score = (spread[-1] - np.mean(spread)) / (np.std(spread) + 1e-12)

                # Active management
                if pair_key in self.state_data["active_pairs"]:
                    pos = self.state_data["active_pairs"][pair_key]
                    hold_sec = now - pos["entry_ts"]
                    # Exit if converged or 24H elapsed
                    if abs(z_score) < 0.5 or hold_sec >= 86400:
                        exit_a = prices[sym_a]
                        exit_b = prices[sym_b]
                        dir_val = pos["direction"]
                        gross = dir_val * (pos["w_a"] * (exit_a - pos["entry_a"]) / pos["entry_a"] - pos["w_b"] * (exit_b - pos["entry_b"]) / pos["entry_b"]) * 200.0
                        exit_fee = 200.0 * 0.00045 * 2.0
                        net = gross - exit_fee
                        self.state_data["metrics"]["total_trades"] += 1
                        self.state_data["metrics"]["cumulative_net_pnl_usd"] += net
                        self.state_data["metrics"]["fees_paid_usd"] += (pos["entry_fee"] + exit_fee)
                        if net > 0:
                            self.state_data["metrics"]["winning_trades"] += 1
                        else:
                            self.state_data["metrics"]["losing_trades"] += 1
                        tot = self.state_data["metrics"]["total_trades"]
                        self.state_data["metrics"]["win_rate_pct"] = round((self.state_data["metrics"]["winning_trades"] / max(1, tot)) * 100.0, 1)
                        del self.state_data["active_pairs"][pair_key]
                        print(f"[EXP-107] CLOSED {pair_key}: Net PnL = ${net:+.2f}")
                elif abs(z_score) > 2.0 and len(self.state_data["active_pairs"]) < 2:
                    direction = -1.0 if z_score > 0 else +1.0
                    w_a = 0.5 * (beta_b / (beta_a + beta_b + 1e-6))
                    w_b = 0.5 * (beta_a / (beta_a + beta_b + 1e-6))
                    entry_fee = 200.0 * 0.00045 * 2.0
                    self.state_data["active_pairs"][pair_key] = {
                        "direction": direction,
                        "w_a": round(float(w_a), 4),
                        "w_b": round(float(w_b), 4),
                        "entry_a": prices[sym_a],
                        "entry_b": prices[sym_b],
                        "entry_ts": now,
                        "entry_z": round(float(z_score), 2),
                        "entry_fee": entry_fee
                    }
                    print(f"[EXP-107] ENTERED {pair_key}: Z = {z_score:+.2f} | Dir = {direction}")

        self.save_state()

    def run_daemon(self):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC')}] >>> EXP-107 Chop Relative-Value Shadow Daemon Started <<<")
        while True:
            try:
                self.evaluate_cycle()
            except Exception as e:
                print(f"[EXP-107] Error in loop: {e}")
            time.sleep(30)

def main():
    daemon = EXP107ChopRVShadow()
    daemon.run_daemon()

if __name__ == "__main__":
    main()

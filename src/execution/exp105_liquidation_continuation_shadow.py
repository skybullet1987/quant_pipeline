#!/usr/bin/env python3
"""
EXP-105: LIQUIDATION CONTINUATION VS REBOUND SHADOW DAEMON
=========================================================
Autonomous live shadow engine tracking liquidation cascade dynamics on Hyperliquid.
Evaluates 3 parallel counterfactual policies on every detected liquidation shock:
  - Arm 1: Rebound Long (Dip-Buying with 1.8% stop loss)
  - Arm 2: Continuation Short (Trend-Following Cascade with 1.8% stop loss)
  - Arm 3: Dynamic Classifier (R_250 vs T_250 State Discriminator)

Outputs:
  - Ledger: data/exp105/counterfactual_continuation_ledger.jsonl
  - State:  data/exp105/continuation_shadow_state.json
"""

import os
import sys
import time
import math
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import websockets
import numpy as np

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data" / "exp105"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "continuation_shadow_state.json"
LEDGER_FILE = DATA_DIR / "counterfactual_continuation_ledger.jsonl"

BINANCE_WS_URL = "wss://fstream.binance.com/market/ws/btcusdt@aggTrade"
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"

SHOCK_VOLUME_USD = 1500000.0   # $1.5M sweep threshold
SHOCK_WINDOW_MS = 100
COOLDOWN_SEC = 300.0           # 5-min cluster window
NOTIONAL_USD = 200.0           # $200 virtual ticket ($20 collateral @ 10x)
TAKER_FEE_RATE = 0.00045       # 4.5 bps

TRACKED_ASSETS = ["SOL", "HYPE", "SUI", "DOGE"]

class EXP105ShadowDaemon:
    def __init__(self):
        self.order_books: Dict[str, Dict[str, float]] = {
            a: {"bid": 0.0, "ask": 0.0, "mid": 0.0, "bid_sz": 0.0, "ask_sz": 0.0} for a in TRACKED_ASSETS
        }
        self.agg_trades: List[Dict[str, Any]] = []
        self.last_shock_ts = 0.0
        self.episode_counter = 0
        self.active_positions: List[Dict[str, Any]] = []
        self.closed_episodes: List[Dict[str, Any]] = []

        self.metrics = {
            "arm_1_fade_long": {"trades": 0, "wins": 0, "cum_pnl": 0.0},
            "arm_2_follow_short": {"trades": 0, "wins": 0, "cum_pnl": 0.0},
            "arm_3_dynamic_classifier": {"trades": 0, "wins": 0, "flat": 0, "cum_pnl": 0.0},
        }

        # Load persisted ledger if exists
        self.load_persisted_state()

    def load_persisted_state(self):
        if LEDGER_FILE.exists():
            try:
                with open(LEDGER_FILE, "r") as f:
                    for line in f:
                        if line.strip():
                            ep = json.loads(line)
                            self.closed_episodes.append(ep)
                            self.episode_counter = max(self.episode_counter, ep.get("episode_index", 0))
                self.recompute_metrics()
                print(f"[INIT] Loaded {len(self.closed_episodes)} historical episodes from {LEDGER_FILE}")
            except Exception as e:
                print(f"[INIT] Warning reading ledger: {e}")

    def recompute_metrics(self):
        for k in self.metrics:
            self.metrics[k] = {"trades": 0, "wins": 0, "cum_pnl": 0.0}
        self.metrics["arm_3_dynamic_classifier"]["flat"] = 0

        for ep in self.closed_episodes:
            res = ep.get("outcomes", {})
            for arm, arm_key in [("arm_1_fade_long", "FADE_LONG"), ("arm_2_follow_short", "FOLLOW_SHORT"), ("arm_3_dynamic_classifier", "CLASSIFIER")]:
                out = res.get(arm_key, {})
                pnl = out.get("net_pnl", 0.0)
                if out.get("action") == "FLAT":
                    self.metrics[arm]["flat"] = self.metrics[arm].get("flat", 0) + 1
                    continue
                self.metrics[arm]["trades"] += 1
                self.metrics[arm]["cum_pnl"] += pnl
                if pnl > 0:
                    self.metrics[arm]["wins"] += 1

    def persist_state(self):
        state_payload = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "governance": {
                "experiment": "EXP-105",
                "specification": "v3.5-liquidation-continuation-classifier",
                "research_role": "CONFIRMATORY_SHADOW",
                "research_status": "FROZEN_SHADOW",
                "portfolio_eligibility": False,
                "promotion_path": "CONFIRMATORY_SHADOW",
                "note": "A2 prospective confirmation. Maintained frozen; directional sanity check under tiny live sample.",
                "notional_usd": NOTIONAL_USD,
                "taker_fee_bps": 4.5,
                "assets": TRACKED_ASSETS
            },
            "sample_size": {
                "total_episodes": len(self.closed_episodes),
                "active_sprints": len(self.active_positions)
            },
            "metrics": {
                "arm_1_fade_long": {
                    "total_trades": self.metrics["arm_1_fade_long"]["trades"],
                    "win_rate_pct": round((self.metrics["arm_1_fade_long"]["wins"] / max(1, self.metrics["arm_1_fade_long"]["trades"])) * 100.0, 1),
                    "cumulative_net_pnl_usd": round(self.metrics["arm_1_fade_long"]["cum_pnl"], 2),
                    "mean_pnl_usd": round(self.metrics["arm_1_fade_long"]["cum_pnl"] / max(1, self.metrics["arm_1_fade_long"]["trades"]), 3)
                },
                "arm_2_follow_short": {
                    "total_trades": self.metrics["arm_2_follow_short"]["trades"],
                    "win_rate_pct": round((self.metrics["arm_2_follow_short"]["wins"] / max(1, self.metrics["arm_2_follow_short"]["trades"])) * 100.0, 1),
                    "cumulative_net_pnl_usd": round(self.metrics["arm_2_follow_short"]["cum_pnl"], 2),
                    "mean_pnl_usd": round(self.metrics["arm_2_follow_short"]["cum_pnl"] / max(1, self.metrics["arm_2_follow_short"]["trades"]), 3)
                },
                "arm_3_dynamic_classifier": {
                    "total_trades": self.metrics["arm_3_dynamic_classifier"]["trades"],
                    "flat_avoided": self.metrics["arm_3_dynamic_classifier"].get("flat", 0),
                    "win_rate_pct": round((self.metrics["arm_3_dynamic_classifier"]["wins"] / max(1, self.metrics["arm_3_dynamic_classifier"]["trades"])) * 100.0, 1),
                    "cumulative_net_pnl_usd": round(self.metrics["arm_3_dynamic_classifier"]["cum_pnl"], 2),
                    "mean_pnl_usd": round(self.metrics["arm_3_dynamic_classifier"]["cum_pnl"] / max(1, self.metrics["arm_3_dynamic_classifier"]["trades"]), 3),
                    "delta_vs_fade_usd": round(self.metrics["arm_3_dynamic_classifier"]["cum_pnl"] - self.metrics["arm_1_fade_long"]["cum_pnl"], 2)
                }
            }
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state_payload, f, indent=2)

    async def run_binance_stream(self):
        while True:
            try:
                async with websockets.connect(BINANCE_WS_URL) as ws:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC')}] [BINANCE] Connected to aggTrade stream.")
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        # Process aggTrade: {'p': price, 'q': qty, 'm': is_buyer_maker, 'T': time_ms}
                        t_ms = data.get("T", int(time.time() * 1000))
                        px = float(data.get("p", 0.0))
                        qty = float(data.get("q", 0.0))
                        is_buyer_maker = data.get("m", False)  # True => sell sweep, False => buy sweep
                        val_usd = px * qty

                        self.agg_trades.append({"t": t_ms, "val": val_usd, "is_sell": is_buyer_maker, "px": px})

                        # Prune older than 500ms
                        cutoff = t_ms - 500
                        while self.agg_trades and self.agg_trades[0]["t"] < cutoff:
                            self.agg_trades.pop(0)

                        # Check 100ms rolling sweep
                        sweep_cutoff = t_ms - SHOCK_WINDOW_MS
                        recent = [tr for tr in self.agg_trades if tr["t"] >= sweep_cutoff and tr["is_sell"]]
                        total_sell_usd = sum(tr["val"] for tr in recent)

                        now_sec = time.time()
                        if total_sell_usd >= SHOCK_VOLUME_USD and (now_sec - self.last_shock_ts) >= COOLDOWN_SEC:
                            self.last_shock_ts = now_sec
                            self.episode_counter += 1
                            self.trigger_shock_episode(self.episode_counter, total_sell_usd, px)
            except Exception as e:
                print(f"[BINANCE] Error: {e}; reconnecting in 5s...")
                await asyncio.sleep(5)

    async def run_hyperliquid_stream(self):
        while True:
            try:
                async with websockets.connect(HYPERLIQUID_WS_URL) as ws:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC')}] [HL] Connected to L2 WebSocket.")
                    for asset in TRACKED_ASSETS:
                        sub = {"method": "subscribe", "subscription": {"type": "l2Book", "coin": asset}}
                        await ws.send(json.dumps(sub))

                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if data.get("channel") == "l2Book":
                            book_data = data.get("data", {})
                            coin = book_data.get("coin")
                            if coin in self.order_books:
                                levels = book_data.get("levels", [[], []])
                                bids = levels[0]
                                asks = levels[1]
                                if bids and asks:
                                    best_bid = float(bids[0]["px"])
                                    best_ask = float(asks[0]["px"])
                                    bid_sz = float(bids[0]["sz"])
                                    ask_sz = float(asks[0]["sz"])
                                    mid = (best_bid + best_ask) / 2.0
                                    self.order_books[coin] = {
                                        "bid": best_bid,
                                        "ask": best_ask,
                                        "mid": mid,
                                        "bid_sz": bid_sz,
                                        "ask_sz": ask_sz,
                                        "obi": (bid_sz - ask_sz) / (bid_sz + ask_sz + 1e-8)
                                    }
                                    # Update active positions FSM
                                    self.evaluate_active_positions()
            except Exception as e:
                print(f"[HL] Error: {e}; reconnecting in 5s...")
                await asyncio.sleep(5)

    def trigger_shock_episode(self, ep_idx: int, sweep_usd: float, btc_px: float):
        ep_id = f"EPISODE_{ep_idx}_{int(time.time())}"
        print(f"\n[>>> EXP-105 SHOCK DETECTED ({ep_id}) <<<]")
        print(f"  Sweep USD: ${sweep_usd:,.0f} | BTC: ${btc_px:,.2f}")

        # Choose highest liquidity/volume alt (SOL or HYPE)
        target_asset = "SOL" if self.order_books["SOL"]["mid"] > 0 else "HYPE"
        book = self.order_books[target_asset]
        obi = book.get("obi", 0.0)

        # Classify: High book imbalance (> 0.20) => Rebound; Severe selling (< -0.50) => Continuation
        if obi > 0.20:
            classifier_action = "LONG"
        elif obi < -0.40:
            classifier_action = "SHORT"
        else:
            classifier_action = "FLAT"

        print(f"  Target: {target_asset} | OBI: {obi:+.2f} | Dynamic Action: {classifier_action}")

        now = time.time()
        # Arm 1: Rebound Long
        pos_long = {
            "ep_id": ep_id, "ep_idx": ep_idx, "asset": target_asset, "arm": "FADE_LONG",
            "side": "BUY", "entry_px": book["ask"] * 1.0001, "entry_ts": now,
            "stop_px": book["ask"] * 0.982, "fee_entry": NOTIONAL_USD * TAKER_FEE_RATE
        }
        # Arm 2: Continuation Short
        pos_short = {
            "ep_id": ep_id, "ep_idx": ep_idx, "asset": target_asset, "arm": "FOLLOW_SHORT",
            "side": "SELL", "entry_px": book["bid"] * 0.9999, "entry_ts": now,
            "stop_px": book["bid"] * 1.018, "fee_entry": NOTIONAL_USD * TAKER_FEE_RATE
        }
        # Arm 3: Dynamic Classifier
        pos_class = {
            "ep_id": ep_id, "ep_idx": ep_idx, "asset": target_asset, "arm": "CLASSIFIER",
            "action": classifier_action, "side": "BUY" if classifier_action == "LONG" else "SELL",
            "entry_px": book["ask"] if classifier_action == "LONG" else book["bid"],
            "entry_ts": now,
            "stop_px": (book["ask"] * 0.982) if classifier_action == "LONG" else (book["bid"] * 1.018),
            "fee_entry": NOTIONAL_USD * TAKER_FEE_RATE if classifier_action != "FLAT" else 0.0
        }

        self.active_positions.extend([pos_long, pos_short, pos_class])
        self.persist_state()

    def evaluate_active_positions(self):
        now = time.time()
        remaining = []
        closed_in_batch = {}

        for pos in self.active_positions:
            asset = pos["asset"]
            book = self.order_books[asset]
            mid = book["mid"]
            if mid <= 0:
                remaining.append(pos)
                continue

            hold_sec = now - pos["entry_ts"]
            closed = False
            exit_px = mid
            reason = ""

            if pos.get("action") == "FLAT":
                # Flat closes immediately with 0 PnL
                closed = True
                exit_px = pos["entry_px"]
                reason = "CLASSIFIER_FLAT"
            elif pos["side"] == "BUY":
                # Long: stop loss or 90s horizon
                if book["bid"] <= pos["stop_px"]:
                    closed = True
                    exit_px = book["bid"]
                    reason = "STOP_LOSS_HIT"
                elif hold_sec >= 90.0:
                    closed = True
                    exit_px = book["bid"]
                    reason = "HORIZON_90S_EXPIRED"
            elif pos["side"] == "SELL":
                # Short: stop loss or 90s horizon
                if book["ask"] >= pos["stop_px"]:
                    closed = True
                    exit_px = book["ask"]
                    reason = "STOP_LOSS_HIT"
                elif hold_sec >= 90.0:
                    closed = True
                    exit_px = book["ask"]
                    reason = "HORIZON_90S_EXPIRED"

            if closed:
                fee_exit = NOTIONAL_USD * TAKER_FEE_RATE if pos.get("action") != "FLAT" else 0.0
                total_fees = pos["fee_entry"] + fee_exit
                if pos.get("action") == "FLAT":
                    gross_pnl = 0.0
                    net_pnl = 0.0
                elif pos["side"] == "BUY":
                    gross_pnl = NOTIONAL_USD * ((exit_px - pos["entry_px"]) / pos["entry_px"])
                    net_pnl = gross_pnl - total_fees
                else:
                    gross_pnl = NOTIONAL_USD * ((pos["entry_px"] - exit_px) / pos["entry_px"])
                    net_pnl = gross_pnl - total_fees

                res = {
                    "action": pos.get("action", pos["side"]),
                    "entry_px": pos["entry_px"],
                    "exit_px": exit_px,
                    "holding_sec": round(hold_sec, 1),
                    "reason": reason,
                    "gross_pnl": round(gross_pnl, 4),
                    "fees": round(total_fees, 4),
                    "net_pnl": round(net_pnl, 4)
                }

                ep_id = pos["ep_id"]
                if ep_id not in closed_in_batch:
                    closed_in_batch[ep_id] = {"episode_id": ep_id, "episode_index": pos["ep_idx"], "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "outcomes": {}}
                closed_in_batch[ep_id]["outcomes"][pos["arm"]] = res
            else:
                remaining.append(pos)

        self.active_positions = remaining

        # If full episode is finalized, write to ledger
        for ep_id, ep_record in closed_in_batch.items():
            if len(ep_record["outcomes"]) == 3:
                self.closed_episodes.append(ep_record)
                with open(LEDGER_FILE, "a") as f:
                    f.write(json.dumps(ep_record) + "\n")
                self.recompute_metrics()
                self.persist_state()
                print(f"[FINALIZED] {ep_id}: Fade = ${ep_record['outcomes']['FADE_LONG']['net_pnl']:+.2f} | Follow = ${ep_record['outcomes']['FOLLOW_SHORT']['net_pnl']:+.2f} | Classifier = ${ep_record['outcomes']['CLASSIFIER']['net_pnl']:+.2f}")

    async def run(self):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC')}] >>> EXP-105 Liquidation Continuation vs Rebound Shadow Daemon Started <<<")
        self.persist_state()
        await asyncio.gather(
            self.run_binance_stream(),
            self.run_hyperliquid_stream()
        )

def main():
    daemon = EXP105ShadowDaemon()
    asyncio.run(daemon.run())

if __name__ == "__main__":
    main()

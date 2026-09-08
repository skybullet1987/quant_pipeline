#!/usr/bin/env python3
"""
Continuous Paper & Live Execution Runner for HL-3A Apex Quantitative System.
Runs a continuous daemon synchronized to the Hyperliquid 6-Hour UTC rebalancing bar.
Includes a 15-minute ALO maker fill convergence monitor and dynamic TP/SL bracket updates.
"""

import os
import sys
import time
import json
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_ROOT))

from src.execution.papertrade_daemon import HyperliquidPaperTrader
from src.execution.live_executor import DynamicHyperliquidExecutor


def seconds_until_next_6h_bar() -> int:
    """Calculates seconds until the next 6-hour bar boundary (00, 06, 12, 18 UTC) + 19s buffer."""
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    next_hour = ((current_hour // 6) + 1) * 6
    
    if next_hour == 24:
        target = now.replace(hour=0, minute=0, second=19, microsecond=0)
        target = target.replace(day=now.day + 1)
    else:
        target = now.replace(hour=next_hour, minute=0, second=19, microsecond=0)
        
    diff = (target - now).total_seconds()
    return max(int(diff), 1)


def execute_cycle(trader: HyperliquidPaperTrader, executor: DynamicHyperliquidExecutor):
    # 1. Compute Apex Tri-Alpha and update paper ledger state
    trader.run_rebalance_cycle()

    # 2. If live execution is confirmed, dispatch orders to Hyperliquid
    if os.getenv("EXECUTION_LIVE_CONFIRMED", "false").lower() == "true":
        state_file = PIPELINE_ROOT / "data" / "papertrade_state.json"
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)

            target_weights = {
                sym: data["weight"]
                for sym, data in state.get("positions", {}).items()
            }

            print(f"[RUNNER] Live execution active. Dispatching {len(target_weights)} target positions to testnet...")
            executor.reconcile_and_execute(target_weights)

            print("[RUNNER] Entering 15-Minute ALO Convergence & Bracket Monitor...")
            poll_interval = 30
            max_convergence_seconds = 900  # 15 minutes
            elapsed = 0

            while elapsed < max_convergence_seconds:
                time.sleep(poll_interval)
                elapsed += poll_interval

                # Check if resting rebalance orders are still on the book
                open_fe = executor.info.frontend_open_orders(executor.wallet)
                resting_non_triggers = [
                    o for o in open_fe
                    if not o.get("isTrigger") and "trigger" not in str(o.get("orderType", "")).lower()
                ]

                print(f"[RUNNER MONITOR] T+{elapsed}s | Resting Maker Orders: {len(resting_non_triggers)}")

                # Dynamically sync brackets to current filled inventory
                executor.arm_position_brackets()

                if len(resting_non_triggers) == 0:
                    print("[RUNNER MONITOR] All maker orders filled cleanly. Convergence complete.")
                    break

            if elapsed >= max_convergence_seconds:
                print("[RUNNER MONITOR] Convergence window expired. Cancelling residual unfilled maker quotes...")
                executor.cancel_all_open_orders()
                executor.arm_position_brackets()


def run_loop():
    print("[RUNNER] Initializing autonomous 6-Hour HL-3A Apex Execution Loop...")
    trader = HyperliquidPaperTrader()
    executor = DynamicHyperliquidExecutor()

    # Immediate sync cycle upon boot
    try:
        execute_cycle(trader, executor)
    except Exception as e:
        print(f"[RUNNER ERROR] Initial execution cycle failed: {e}")

    while True:
        sleep_secs = seconds_until_next_6h_bar()
        next_run_utc = datetime.fromtimestamp(time.time() + sleep_secs, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        hours, remainder = divmod(sleep_secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"\n[RUNNER] Sleeping {hours}h {minutes}m {seconds}s until next 6H rebalance ({next_run_utc})...\n")
        time.sleep(sleep_secs)

        try:
            execute_cycle(trader, executor)
        except Exception as e:
            print(f"[RUNNER ERROR] Scheduled rebalance cycle failed: {e}")


if __name__ == "__main__":
    run_loop()

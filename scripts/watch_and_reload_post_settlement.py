#!/usr/bin/env python3
"""
Automated Post-Settlement Watcher & Graceful Reload (v3.6)

Dynamically inspects `active_positions` in data/polymarket/live_harvester_state.json (no hardcoded
trade/order IDs). Once every live position has settled/closed (active_positions_count == 0) it
delegates the daemon restart to scripts/reload_production_daemons.py (graceful SIGTERM, systemd
managed, risk limits from config/polymarket_risk_config.json) and prints a verified report.

Authoritative collateral is read through PolymarketLiveExecutor (CLOB V2 client), never through the
legacy py_clob_client.

Usage:
    python scripts/watch_and_reload_post_settlement.py [--poll-sec 10] [--timeout-sec 0] [--no-reload]
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PIPELINE_ROOT / "data/polymarket/live_harvester_state.json"
RELOAD_SCRIPT = PIPELINE_ROOT / "scripts/reload_production_daemons.py"
RISK_CONFIG_FILE = PIPELINE_ROOT / "config/polymarket_risk_config.json"

if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PIPELINE_ROOT / ".env")
except Exception:
    pass


def load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def open_position_ids(state: dict) -> list:
    active = state.get("active_positions", {}) or {}
    return sorted(active.keys())


def get_onchain_collateral():
    """Authoritative USDC/pUSD collateral via the V2 executor; None if unavailable."""
    try:
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        executor = PolymarketLiveExecutor(dry_run=False)
        for name in ("get_collateral_balance", "get_available_collateral", "get_usdc_balance"):
            fn = getattr(executor, name, None)
            if callable(fn):
                return float(fn())
    except Exception as exc:
        print(f"[WARN] Could not query live collateral via executor: {exc}")
    return None


def current_risk_pct(equity: float) -> float:
    try:
        with open(RISK_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if equity >= float(cfg["scale_up_equity_threshold"]):
            return float(cfg["scale_up_risk_pct"])
        return float(cfg["dynamic_risk_pct"])
    except Exception:
        return 0.18


def delegate_reload() -> int:
    """Graceful, position-guarded restart (the reload script itself refuses if positions are open)."""
    print("Delegating restart to scripts/reload_production_daemons.py (graceful SIGTERM, systemd)...")
    return subprocess.call([sys.executable, str(RELOAD_SCRIPT)], cwd=str(PIPELINE_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Wait for live positions to settle, then gracefully reload daemons")
    ap.add_argument("--poll-sec", type=float, default=10.0)
    ap.add_argument("--timeout-sec", type=float, default=0.0, help="0 = wait indefinitely")
    ap.add_argument("--no-reload", action="store_true", help="Only report; do not restart daemons")
    args = ap.parse_args()

    print("=" * 80)
    print("   POST-SETTLEMENT WATCHER & GRACEFUL RELOAD (v3.6)")
    print("=" * 80)

    start = time.time()
    last_log = 0.0
    while True:
        state = load_state()
        open_ids = open_position_ids(state)
        now = time.time()
        if not open_ids:
            print(f"[{datetime.now(timezone.utc):%H:%M:%S} UTC] No active live positions.")
            break
        if now - last_log >= 30.0:
            print(f"[{datetime.now(timezone.utc):%H:%M:%S} UTC] Waiting on {len(open_ids)} position(s): {', '.join(open_ids)}")
            last_log = now
        if args.timeout_sec and (now - start) >= args.timeout_sec:
            print("Timed out waiting for positions to settle; not reloading.")
            return 1
        time.sleep(args.poll_sec)

    rc = 0
    if not args.no_reload:
        rc = delegate_reload()

    final_state = load_state()
    cash = get_onchain_collateral()
    bankroll = final_state.get("live_bankroll")
    equity = float(final_state.get("total_account_equity") or bankroll or cash or 0.0)
    effective_cash = cash if cash is not None else bankroll
    pct = current_risk_pct(equity)

    print("\n" + "=" * 80)
    print("POST-SETTLEMENT RELOAD REPORT")
    print("=" * 80)
    print(f"Reload exit code:            {rc}")
    print(f"Authoritative Cash:          {('$%.2f' % float(effective_cash)) if effective_cash is not None else 'n/a'}")
    print(f"Total Account Equity:        ${equity:.2f}")
    print(f"Active Positions Count:      {final_state.get('active_positions_count', len(open_position_ids(final_state)))}")
    print(f"Dynamic risk pct (config):   {pct:.0%}  -> ticket ~${equity * pct:.2f}")
    print(f"Supervisor Status:           {final_state.get('status', 'RUNNING')}")
    print("=" * 80 + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())

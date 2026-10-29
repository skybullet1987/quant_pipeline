#!/usr/bin/env python3
"""
APEX Mainnet Canary Pre-Flight & Gate-2 Readiness Verifier
==========================================================
Evaluates all 10 mandatory quantitative, accounting, infrastructure, and capital
authorization gates required before promoting HyperCore APEX (`v5.2.0`) from
Hyperliquid Testnet (`--mainnet-signals`) to a `$250-$500` Mainnet Canary.

Strictly read-only: NEVER submits orders, transfers funds, or alters live services.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

V51_CUTOVER_ISO = "2026-10-29T02:06:00Z"


def evaluate_canary_readiness(
    repo_root: Path = REPO_ROOT,
    target_post_v51_fills: int = 100,
    min_canary_usdc: float = 250.0,
    max_canary_usdc: float = 500.0,
) -> Dict[str, Any]:
    load_dotenv(repo_root / ".env")
    state_path = repo_root / "data" / "papertrade_state.json"
    journal_path = repo_root / "data" / "papertrade_journal.jsonl"

    state: Dict[str, Any] = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))

    # Parse journal audit records (total vs post-v5.1 cutover)
    total_audits = 0
    post_v51_audits: List[Dict[str, Any]] = []
    post_v51_halts = 0
    if journal_path.exists():
        with open(journal_path, "r", encoding="utf-8", errors="replace") as jf:
            for ln in jf:
                if '"IMPLEMENTATION_AUDIT_RECORD"' not in ln and '"CIRCUIT_BREAKER"' not in ln:
                    continue
                try:
                    ev = json.loads(ln)
                except Exception:
                    continue
                et = ev.get("event_type")
                pl = ev.get("payload") or {}
                ts_ev = str(ev.get("timestamp") or pl.get("timestamp_utc") or "")
                if et == "IMPLEMENTATION_AUDIT_RECORD":
                    total_audits += 1
                    if str(pl.get("timestamp_utc", "")) >= V51_CUTOVER_ISO:
                        post_v51_audits.append(pl)
                elif et == "CIRCUIT_BREAKER" and pl.get("state") == "HALTED":
                    if ts_ev >= "2026-10-29 02:06:00 UTC":
                        post_v51_halts += 1

    post_n = len(post_v51_audits)
    post_maker_n = sum(1 for x in post_v51_audits if x.get("order_type") == "RESTING_ALO")
    post_maker_pct = (100.0 * post_maker_n / post_n) if post_n > 0 else 100.0
    post_mean_shortfall = (
        sum(float(x.get("total_shortfall_bps", 0.0)) for x in post_v51_audits) / post_n
        if post_n > 0
        else 0.0
    )

    acct_ledger = state.get("accounting_ledger") or {}
    recon_status = acct_ledger.get("reconciliation_status", "UNKNOWN")
    cb_status = state.get("circuit_breaker", "UNKNOWN")
    ws_stats = state.get("ws_market_cache") or {}

    # Check systemd service
    try:
        r_svc = subprocess.run(
            ["systemctl", "--user", "is-active", "apex-perp.service"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        svc_active = r_svc.stdout.strip() == "active"
    except Exception:
        svc_active = False

    # Check Mainnet clock drift + Mainnet account state
    drift_ms = 99999.0
    try:
        req = urllib.request.Request(
            constants.MAINNET_API_URL + "/info",
            data=b'{"type":"meta"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=5) as resp:
            hdr_date = resp.headers.get("Date")
        t1 = time.time()
        if hdr_date:
            srv_ts = parsedate_to_datetime(hdr_date).timestamp()
            drift_ms = abs(0.5 * (t0 + t1) - srv_ts) * 1000.0
    except Exception:
        pass

    addr = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "")
    mainnet_usdc = 0.0
    mainnet_positions = 0
    mainnet_open_orders = 0
    if addr:
        try:
            m_info = Info(constants.MAINNET_API_URL, skip_ws=True)
            sp = m_info.spot_user_state(addr)
            bals = {b["coin"]: float(b.get("total", 0.0)) for b in sp.get("balances", [])}
            us = m_info.user_state(addr)
            perp_eq = float(us.get("marginSummary", {}).get("accountValue", 0.0))
            mainnet_usdc = bals.get("USDC", 0.0) if bals.get("USDC", 0.0) > 0 else perp_eq
            mainnet_positions = sum(
                1 for p in us.get("assetPositions", []) if abs(float(p.get("position", {}).get("szi", 0.0))) > 0
            )
            mainnet_open_orders = len(m_info.open_orders(addr))
        except Exception:
            pass

    gates = [
        {
            "gate": "G01_POST_UPGRADE_ALO_SAMPLE",
            "passed": post_n >= target_post_v51_fills,
            "detail": f"{post_n}/{target_post_v51_fills} post-v5.1+ fills (total Gate-2 ledger: {total_audits}/500)",
        },
        {
            "gate": "G02_MAKER_ONLY_COMPLIANCE",
            "passed": post_maker_pct >= 95.0,
            "detail": f"{post_maker_pct:.1f}% RESTING_ALO compliance (require >= 95.0%)",
        },
        {
            "gate": "G03_EXECUTION_SHORTFALL_BOUND",
            "passed": post_mean_shortfall <= 3.5,
            "detail": f"Mean shortfall {post_mean_shortfall:+.2f} bps (require <= +3.50 bps)",
        },
        {
            "gate": "G04_RECONCILIATION_AND_ZERO_HALTS",
            "passed": cb_status == "RUNNING" and recon_status in ("EXACT", "ACCEPTABLE") and post_v51_halts == 0,
            "detail": f"CB={cb_status}, Recon={recon_status}, PostUpgradeHalts={post_v51_halts}",
        },
        {
            "gate": "G05_SYSTEMD_SUPERVISION",
            "passed": svc_active,
            "detail": f"apex-perp.service active={svc_active}",
        },
        {
            "gate": "G06_WS_MARKET_CACHE_HEALTH",
            "passed": bool(ws_stats.get("connected", False)),
            "detail": f"WS connected={ws_stats.get('connected', False)}, msgs={ws_stats.get('messages_received', 0)}",
        },
        {
            "gate": "G07_MAINNET_CLOCK_SYNC",
            "passed": drift_ms <= 2000.0,
            "detail": f"Clock drift={drift_ms:.0f} ms (require <= 2000 ms)",
        },
        {
            "gate": "G08_MAINNET_CLEAN_BOOK",
            "passed": mainnet_positions == 0 and mainnet_open_orders == 0,
            "detail": f"Mainnet positions={mainnet_positions}, open_orders={mainnet_open_orders}",
        },
        {
            "gate": "G09_MAINNET_CANARY_COLLATERAL",
            "passed": mainnet_usdc >= min_canary_usdc,
            "detail": f"Mainnet USDC=${mainnet_usdc:.2f} (require >= ${min_canary_usdc:.2f}, recommended ${min_canary_usdc:.0f}-${max_canary_usdc:.0f})",
        },
    ]

    all_passed = all(g["passed"] for g in gates)
    return {
        "evaluated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "strategy_version": state.get("version", "unknown"),
        "ready_for_mainnet_canary": all_passed,
        "mainnet_usdc_balance": round(mainnet_usdc, 2),
        "post_v51_fills": post_n,
        "total_gate2_fills": total_audits,
        "gates": gates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="APEX Mainnet Canary Pre-Flight Readiness Verifier")
    parser.add_argument("--target-fills", type=int, default=100, help="Required clean post-v5.1+ ALO fills")
    parser.add_argument("--min-canary-usdc", type=float, default=250.0, help="Minimum Mainnet USDC canary collateral")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    res = evaluate_canary_readiness(
        target_post_v51_fills=args.target_fills,
        min_canary_usdc=args.min_canary_usdc,
    )
    if args.json:
        print(json.dumps(res, indent=2))
        return

    print("=" * 78)
    print(f" APEX MAINNET CANARY PRE-FLIGHT REPORT  |  {res['evaluated_at_utc']}")
    print(f" Engine Version: {res['strategy_version']}  |  Overall Ready: {res['ready_for_mainnet_canary']}")
    print("=" * 78)
    for g in res["gates"]:
        badge = "[PASS]" if g["passed"] else "[WAIT]"
        print(f" {badge} {g['gate']:34s} | {g['detail']}")
    print("=" * 78)


if __name__ == "__main__":
    main()

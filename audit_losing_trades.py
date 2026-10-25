#!/usr/bin/env python3
"""
AUTONOMOUS POST-TRADE FORENSIC AUDITOR (LIVE REAL-MONEY KRAKEN-FINLAND ONLY)
============================================================================
1. Queries `kraken-finland:/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json`
   for real-money Polymarket trades and `polymarket-live-harvester.service` health.
2. Automatically marks winning real-money trades (`won == True`) as `PROFIT_OK`.
3. Surfaces any newly settled losing real-money trades (`won == False`) in `uninspected_losses`.
4. Provides deterministic CLI actions for the Antigravity Forensic Agent:
   - `python audit_losing_trades.py --check`
   - `python audit_losing_trades.py --mark-audited <trade_id> --verdict <EXPECTED_LOSS|BUG_FIXED> --notes "<reason>"`
   - `python audit_losing_trades.py --redeploy`
"""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_DIR = Path(r"C:\Users\Anton\source\repos\Dominus")
DATA_DIR = REPO_DIR / "data" / "polymarket"
AUDIT_STATE_FILE = DATA_DIR / "forensic_audit_state.json"
AUDIT_LEDGER_FILE = DATA_DIR / "forensic_audit_ledger.jsonl"

# Historical closed trades already audited prior to 2026-10-23 02:00 UTC
HISTORICAL_BASELINE_TRADES = {
    "LIVE_6011767_1792677997_DOWN",
    "LIVE_6011823_1792678868_UP",
    "LIVE_6011834_1792678920_UP",
    "LIVE_6012053_1792679970_UP",
    "LIVE_6012062_1792679970_UP",
    "LIVE_5969579_1792680240_UP",
    "LIVE_6012995_1792682563_UP",
    "LIVE_6013539_1792683334_UP",
    "LIVE_6014317_1792684214_UP",
    "LIVE_5972389_1792686568_DOWN",
    "LIVE_6016117_1792686984_DOWN",
    "LIVE_6017333_1792688700_DOWN",
    "LIVE_5978915_1792691143_UP",
    "LIVE_6019058_1792692519_DOWN",
    "LIVE_6022563_1792694165_UP",
    "LIVE_6024982_1792697736_DOWN",
    "LIVE_6026368_1792702377_DOWN",
    "LIVE_6027101_1792704984_DOWN",
    "LIVE_6032439_1792715250_DOWN",
    "LIVE_6032790_1792716941_UP",
}


def load_audit_state() -> Dict[str, Any]:
    if AUDIT_STATE_FILE.exists():
        try:
            st = json.loads(AUDIT_STATE_FILE.read_text(encoding="utf-8"))
            audited = st.setdefault("audited_trades", {})
            for tid in HISTORICAL_BASELINE_TRADES:
                if tid not in audited:
                    audited[tid] = {"trade_id": tid, "verdict": "HISTORICAL_BASELINE"}
            return st
        except Exception:
            pass
    return {
        "updated_at": None,
        "audited_trades": {tid: {"trade_id": tid, "verdict": "HISTORICAL_BASELINE"} for tid in HISTORICAL_BASELINE_TRADES},
        "stats": {
            "profits_skipped": 0,
            "expected_losses_ok": 0,
            "bugs_fixed_and_redeployed": 0,
            "total_redeployments": 0,
        },
        "recent_verdicts": [],
    }


def save_audit_state(st: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    st["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    tmp = AUDIT_STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=2), encoding="utf-8")
    os.replace(tmp, AUDIT_STATE_FILE)


def append_audit_ledger(rec: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def fetch_kraken_live_state() -> Dict[str, Any]:
    cmd = [
        "ssh", "-n", "-o", "ConnectTimeout=5", "kraken-finland",
        "systemctl --user is-active polymarket-live-harvester.service ; cat /home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=9.0)
    if res.returncode != 0 and not res.stdout.strip():
        raise RuntimeError(res.stderr.strip() or "SSH to kraken-finland failed")
    lines = res.stdout.strip().splitlines()
    svc_status = lines[0].strip() if lines else "unknown"
    st = json.loads("\n".join(lines[1:]))
    return {"service_status": svc_status, "state": st}


def scan_trades() -> Dict[str, Any]:
    audit_st = load_audit_state()
    audited = audit_st.setdefault("audited_trades", {})
    uninspected_losses: List[Dict[str, Any]] = []
    newly_skipped_wins = 0

    try:
        remote = fetch_kraken_live_state()
        svc_status = remote["service_status"]
        st = remote["state"]
        risk_st = st.get("risk_state") or {}
        is_halted = bool(st.get("risk_halt", False) or risk_st.get("halted", False))
        healthy = (svc_status == "active") and (not is_halted) and (st.get("status") == "RUNNING")
        closed_positions = list(st.get("closed_positions", []))
    except Exception as e:
        return {
            "status": "ACTION_REQUIRED",
            "daemon_health": {"healthy": False, "error": str(e)},
            "newly_cleared_wins": 0,
            "uninspected_losses_count": 0,
            "uninspected_losses": [],
            "audit_stats": audit_st.get("stats", {}),
        }

    for rec in closed_positions:
        tid = str(rec.get("trade_id") or "")
        if not tid or tid in audited:
            continue
        # Skip positions still awaiting on-chain redemption resolution if PnL is not yet finalized
        if (
            rec.get("exit_order_status") == "AWAITING_REDEMPTION"
            or rec.get("status") == "AWAITING_ONCHAIN_SETTLEMENT"
        ) and rec.get("net_pnl_usd") is None:
            continue

        raw_pnl = rec.get("net_pnl_usd")
        if raw_pnl is not None:
            won = float(raw_pnl) >= 0.0
        else:
            won = bool(rec.get("won") is True)
        if won:
            entry = {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "trade_id": tid,
                "sleeve": rec.get("sleeve"),
                "asset": rec.get("asset"),
                "net_pnl_usd": rec.get("net_pnl_usd"),
                "verdict": "PROFIT_OK",
                "notes": "Winning real-money trade — auto-cleared.",
            }
            audited[tid] = entry
            audit_st["stats"]["profits_skipped"] = audit_st["stats"].get("profits_skipped", 0) + 1
            newly_skipped_wins += 1
            append_audit_ledger(entry)
        else:
            uninspected_losses.append(rec)

    save_audit_state(audit_st)

    health = {
        "mode": "LIVE_REAL_MONEY_KRAKEN_FINLAND",
        "healthy": healthy,
        "service_status": svc_status,
        "status": st.get("status"),
        "risk_halt": is_halted,
        "halt_reason": (st.get("risk_state") or {}).get("halt_reason", ""),
        "live_bankroll_usd": round(float(st.get("live_bankroll") or 0.0), 2),
        "total_account_equity_usd": round(float(st.get("total_account_equity") or 0.0), 2),
        "open_positions_count": st.get("active_positions_count", 0),
        "open_position_ids": st.get("active_position_ids", []),
        "closed_positions_count": st.get("closed_positions_count", 0),
        "trades_this_hour": st.get("trades_this_hour", 0),
    }

    status_code = "ACTION_REQUIRED" if (uninspected_losses or not healthy) else "ALL_GOOD"
    return {
        "status": status_code,
        "daemon_health": health,
        "newly_cleared_wins": newly_skipped_wins,
        "uninspected_losses_count": len(uninspected_losses),
        "uninspected_losses": uninspected_losses,
        "audit_stats": audit_st.get("stats", {}),
    }


def mark_audited(trade_id: str, verdict: str, notes: str) -> None:
    audit_st = load_audit_state()
    audited = audit_st.setdefault("audited_trades", {})
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    entry = {
        "timestamp": now_str,
        "trade_id": trade_id,
        "verdict": verdict,
        "notes": notes,
    }
    audited[trade_id] = entry

    if verdict == "EXPECTED_LOSS":
        audit_st["stats"]["expected_losses_ok"] = audit_st["stats"].get("expected_losses_ok", 0) + 1
    elif verdict == "BUG_FIXED":
        audit_st["stats"]["bugs_fixed_and_redeployed"] = audit_st["stats"].get("bugs_fixed_and_redeployed", 0) + 1

    recent = audit_st.setdefault("recent_verdicts", [])
    recent.append(entry)
    audit_st["recent_verdicts"] = recent[-30:]
    save_audit_state(audit_st)
    append_audit_ledger(entry)
    print(json.dumps({"ok": True, "recorded": entry}, indent=2))


def redeploy_daemon() -> None:
    cmd = [
        "ssh", "-n", "kraken-finland",
        (
            "/home/skybullet1987/quant_pipeline/venv/bin/python -m py_compile "
            "/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_executor.py "
            "/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_harvester.py && "
            "systemctl --user daemon-reload && "
            "systemctl --user reset-failed polymarket-live-harvester.service || true && "
            "systemctl --user restart polymarket-live-harvester.service && "
            "sleep 12 && systemctl --user is-active polymarket-live-harvester.service"
        ),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=35.0)
    if res.returncode != 0:
        raise RuntimeError(f"Redeploy on kraken-finland failed: {res.stderr or res.stdout}")

    audit_st = load_audit_state()
    audit_st["stats"]["total_redeployments"] = audit_st["stats"].get("total_redeployments", 0) + 1
    save_audit_state(audit_st)
    scan_res = scan_trades()
    print(json.dumps({"redeployed": True, "daemon_health": scan_res["daemon_health"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Post-Trade Forensic Auditor (Real-Money Live Harvester)")
    parser.add_argument("--check", action="store_true", help="Scan for uninspected real-money losing trades and live harvester health")
    parser.add_argument("--mark-audited", type=str, help="Trade ID to mark as audited")
    parser.add_argument("--verdict", type=str, choices=["EXPECTED_LOSS", "BUG_FIXED", "PROFIT_OK"], default="EXPECTED_LOSS")
    parser.add_argument("--notes", type=str, default="", help="Forensic explanation or patch summary")
    parser.add_argument("--redeploy", action="store_true", help="Compile-check and restart polymarket-live-harvester.service on kraken-finland")
    args = parser.parse_args()

    if args.mark_audited:
        mark_audited(args.mark_audited, args.verdict, args.notes)
    elif args.redeploy:
        redeploy_daemon()
    else:
        res = scan_trades()
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

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
from typing import Any, Dict, List, Optional

REPO_DIR = Path(r"C:\Users\Anton\source\repos\Dominus")
DATA_DIR = REPO_DIR / "data" / "polymarket"
AUDIT_STATE_FILE = DATA_DIR / "forensic_audit_state.json"
AUDIT_LEDGER_FILE = DATA_DIR / "forensic_audit_ledger.jsonl"
WFO_HYPOTHESIS_QUEUE_FILE = DATA_DIR / "wfo_hypothesis_queue.jsonl"

AUDIT_CLASSIFICATIONS = (
    "PLUMBING_0_PARAM",
    "SEQUENCE_TELEMETRY_REQUIRED",
    "PARAM_WFO_REQUIRED",
    "EXPECTED_VARIANCE_NO_CHANGE",
    "WIN_AUTO_CLEARED",
)
_TYPE2_PARAM_TOKENS = (
    "min_cushion", "dist_pct", "z_strike", "min_z", "sigma_1h", "max_px", "min_px", "kelly", "wrong_side_thresh",
)
_TUNE_VERBS = ("tighten", "widen", "raise", "lower", "increase", "decrease", "tune", "adjust threshold")

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


def append_wfo_hypothesis_queue(rec: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(WFO_HYPOTHESIS_QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def classify_losing_trade_forensics(rec: Dict[str, Any]) -> Dict[str, str]:
    st = str(rec.get("status") or "").upper()
    cr = str(rec.get("close_reason") or "").upper()
    em = str(rec.get("entry_mode") or "").upper()
    if st in {"UNRESOLVED_BALANCE_DISCREPANCY", "ENTRY_OUTCOME_UNKNOWN", "EXIT_CANCEL_PENDING"} or "ERROR" in cr:
        return {"suggested_classification": "PLUMBING_0_PARAM", "rationale": "Deterministic state/reconciliation anomaly."}
    if "LEGGED_OUT" in cr or any(k in em for k in ("RESCUE", "FALLBACK", "DOWNSNAP")):
        return {"suggested_classification": "SEQUENCE_TELEMETRY_REQUIRED", "rationale": "Sequence/timing event; check simulator."}
    return {"suggested_classification": "EXPECTED_VARIANCE_NO_CHANGE", "rationale": "Variance; threshold edits need PARAM_WFO_REQUIRED."}


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
                "classification": "WIN_AUTO_CLEARED",
                "notes": "Winning real-money trade — auto-cleared.",
            }
            audited[tid] = entry
            audit_st["stats"]["profits_skipped"] = audit_st["stats"].get("profits_skipped", 0) + 1
            newly_skipped_wins += 1
            append_audit_ledger(entry)
        else:
            rec_enriched = dict(rec)
            rec_enriched["forensic_classification_hint"] = classify_losing_trade_forensics(rec)
            uninspected_losses.append(rec_enriched)

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


def mark_audited(
    trade_id: str,
    verdict: str,
    notes: str,
    classification: Optional[str] = None,
    wfo_grid: str = "",
) -> Dict[str, Any]:
    default_cls = {
        "EXPECTED_LOSS": "EXPECTED_VARIANCE_NO_CHANGE",
        "BUG_FIXED": "PLUMBING_0_PARAM",
        "PARAM_WFO_REQUIRED": "PARAM_WFO_REQUIRED",
        "PROFIT_OK": "WIN_AUTO_CLEARED",
    }
    resolved_cls = classification or default_cls.get(verdict, "EXPECTED_VARIANCE_NO_CHANGE")
    if resolved_cls not in AUDIT_CLASSIFICATIONS:
        raise ValueError(f"Unsupported classification: {resolved_cls}")

    notes_low = (notes or "").lower()
    if verdict == "BUG_FIXED":
        if resolved_cls != "PLUMBING_0_PARAM":
            raise ValueError(
                f"GOVERNANCE_VIOLATION: verdict=BUG_FIXED requires classification=PLUMBING_0_PARAM (got {resolved_cls})."
            )
        if classification is None and any(tok in notes_low for tok in _TYPE2_PARAM_TOKENS) and any(
            vb in notes_low for vb in _TUNE_VERBS
        ):
            raise ValueError(
                "GOVERNANCE_VIOLATION: Numerical strategy/risk parameter tuning cannot be recorded as BUG_FIXED; "
                "use --verdict PARAM_WFO_REQUIRED."
            )

    audit_st = load_audit_state()
    audited = audit_st.setdefault("audited_trades", {})
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    entry: Dict[str, Any] = {
        "timestamp": now_str,
        "trade_id": trade_id,
        "verdict": verdict,
        "classification": resolved_cls,
        "notes": notes,
    }
    if wfo_grid:
        entry["wfo_grid"] = wfo_grid
    audited[trade_id] = entry

    if verdict == "EXPECTED_LOSS":
        audit_st["stats"]["expected_losses_ok"] = audit_st["stats"].get("expected_losses_ok", 0) + 1
    elif verdict == "BUG_FIXED":
        audit_st["stats"]["bugs_fixed_and_redeployed"] = audit_st["stats"].get("bugs_fixed_and_redeployed", 0) + 1
    elif verdict == "PARAM_WFO_REQUIRED":
        audit_st["stats"]["param_wfo_queued"] = audit_st["stats"].get("param_wfo_queued", 0) + 1

    if verdict == "PARAM_WFO_REQUIRED" or resolved_cls in ("PARAM_WFO_REQUIRED", "SEQUENCE_TELEMETRY_REQUIRED"):
        append_wfo_hypothesis_queue({
            "queued_at": now_str,
            "trade_id": trade_id,
            "verdict": verdict,
            "classification": resolved_cls,
            "wfo_grid": wfo_grid,
            "notes": notes,
            "status": "QUEUED_FOR_PURGED_WFO",
        })

    recent = audit_st.setdefault("recent_verdicts", [])
    recent.append(entry)
    audit_st["recent_verdicts"] = recent[-30:]
    save_audit_state(audit_st)
    append_audit_ledger(entry)
    print(json.dumps({"ok": True, "recorded": entry}, indent=2))
    return entry


def redeploy_daemon(force: bool = False) -> None:
    if not force:
        pre = fetch_kraken_live_state()["state"]
        open_cnt = int(pre.get("active_positions_count", 0) or 0)
        if open_cnt > 0:
            raise RuntimeError(
                f"Refusing to restart live harvester with {open_cnt} open position(s): "
                f"{pre.get('active_position_ids', [])}. Wait until flat."
            )

    cmd = [
        "ssh", "-n", "kraken-finland",
        (
            "/home/skybullet1987/quant_pipeline/venv/bin/python -m py_compile "
            "/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_terminal_recorder.py "
            "/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_executor.py "
            "/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_harvester.py && "
            "systemctl --user daemon-reload && "
            "systemctl --user reset-failed polymarket-live-harvester.service || true && "
            "systemctl --user restart polymarket-live-harvester.service && "
            "for i in 1 2 3 4 5 6 7 8 9 10; do "
            "sleep 2; "
            "if grep -q '\"status\": \"RUNNING\"' /home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json 2>/dev/null; then break; fi; "
            "done && "
            "systemctl --user is-active polymarket-live-harvester.service"
        ),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=45.0)
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
    parser.add_argument("--verdict", type=str, choices=["EXPECTED_LOSS", "BUG_FIXED", "PARAM_WFO_REQUIRED", "PROFIT_OK"], default="EXPECTED_LOSS")
    parser.add_argument("--classification", type=str, choices=list(AUDIT_CLASSIFICATIONS), default=None, help="Structured Type 0 / Type 1 / Type 2 forensic classification")
    parser.add_argument("--wfo-grid", type=str, default="", help="Optional Purged WFO grid specification routed to wfo_hypothesis_queue.jsonl")
    parser.add_argument("--notes", type=str, default="", help="Forensic explanation or patch summary")
    parser.add_argument("--redeploy", action="store_true", help="Compile-check and restart polymarket-live-harvester.service on kraken-finland")
    parser.add_argument("--force-redeploy", action="store_true", help="Override open-position safety lock during emergency recovery")
    args = parser.parse_args()

    if args.mark_audited:
        mark_audited(args.mark_audited, args.verdict, args.notes, classification=args.classification, wfo_grid=args.wfo_grid)
    elif args.redeploy:
        redeploy_daemon(force=args.force_redeploy)
    else:
        res = scan_trades()
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

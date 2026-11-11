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
import contextlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

REPO_DIR = Path(os.getenv("DOMINUS_REPO_DIR") or Path(__file__).resolve().parent)
DATA_DIR = REPO_DIR / "data" / "polymarket"
AUDIT_STATE_FILE = DATA_DIR / "forensic_audit_state.json"
_DEFAULT_AUDIT_LOCK_FILE = DATA_DIR / "forensic_audit_state.lock"
AUDIT_LOCK_FILE = _DEFAULT_AUDIT_LOCK_FILE
AUDIT_LEDGER_FILE = DATA_DIR / "forensic_audit_ledger.jsonl"
WFO_HYPOTHESIS_QUEUE_FILE = DATA_DIR / "wfo_hypothesis_queue.jsonl"


@contextlib.contextmanager
def _audit_state_lock(timeout_sec: float = 10.0) -> Iterator[None]:
    """Cross-process atomic file lock preventing concurrent monitor/PAA races on forensic_audit_state.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = (
        (Path(DATA_DIR) / "forensic_audit_state.lock")
        if AUDIT_LOCK_FILE == _DEFAULT_AUDIT_LOCK_FILE
        else Path(AUDIT_LOCK_FILE)
    )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "r+b" if lock_path.exists() else "w+b")
    deadline = time.monotonic() + max(0.5, timeout_sec)
    locked = False
    try:
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0, os.SEEK_END)
                    if fh.tell() == 0:
                        fh.write(b"\x00")
                        fh.flush()
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out acquiring exclusive audit lock: {lock_path}")
                time.sleep(0.05)
        yield
    finally:
        if locked:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()

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
    tid = str(rec.get("trade_id") or "")
    slv = str(rec.get("sleeve") or "")
    st = str(rec.get("status") or "").upper()
    eos = str(rec.get("exit_order_status") or "").upper()
    cr = str(rec.get("close_reason") or "").upper()
    em = str(rec.get("entry_mode") or "").upper()
    if (
        st in {"UNRESOLVED_BALANCE_DISCREPANCY", "ENTRY_OUTCOME_UNKNOWN", "EXIT_CANCEL_PENDING"}
        or eos in {"UNRESOLVED_BALANCE_DISCREPANCY", "ENTRY_OUTCOME_UNKNOWN", "EXIT_CANCEL_PENDING"}
        or "ERROR" in cr
    ):
        return {"suggested_classification": "PLUMBING_0_PARAM", "rationale": "Deterministic state/reconciliation anomaly."}
    if "PRE_KICKOFF" in cr or (tid.startswith("SPORTS_CORRIDOR_LIVE_") and slv == "SOC2_EXACT_SCORE_2D_LATTICE"):
        return {
            "suggested_classification": "EXPECTED_VARIANCE_NO_CHANGE",
            "rationale": "Authorized pre-kickoff Maker scratch / T-5m protection on legacy pre-v5.4.2 SOC2 corridor leg (SOC2 live routing already disabled in v5.4.2+); record EXPECTED_LOSS and do NOT edit code or restart.",
        }
    if "LEGGED_OUT" in cr or any(k in em for k in ("RESCUE", "FALLBACK", "DOWNSNAP")):
        return {"suggested_classification": "SEQUENCE_TELEMETRY_REQUIRED", "rationale": "Sequence/timing event; check simulator."}
    return {"suggested_classification": "EXPECTED_VARIANCE_NO_CHANGE", "rationale": "Variance; threshold edits need PARAM_WFO_REQUIRED."}


def fetch_kraken_live_state() -> Dict[str, Any]:
    local_state = Path("/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json")
    if os.name != "nt" and local_state.exists():
        res = subprocess.run(
            ["systemctl", "--user", "is-active", "polymarket-live-harvester.service"],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        svc_line = (res.stdout or "").strip().splitlines()
        svc_status = svc_line[0].strip() if svc_line else "unknown"
        return {"service_status": svc_status, "state": json.loads(local_state.read_text(encoding="utf-8"))}
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
    try:
        remote = fetch_kraken_live_state()
        svc_status = remote["service_status"]
        st = remote["state"]
        risk_st = st.get("risk_state") or {}
        is_halted = bool(st.get("risk_halt", False) or risk_st.get("halted", False))
        healthy = (svc_status == "active") and (not is_halted) and (st.get("status") == "RUNNING")
        closed_positions = list(st.get("closed_positions", []))
    except Exception as e:
        audit_st = load_audit_state()
        return {
            "status": "ACTION_REQUIRED",
            "daemon_health": {"healthy": False, "error": str(e)},
            "newly_cleared_wins": 0,
            "uninspected_losses_count": 0,
            "uninspected_losses": [],
            "audit_stats": audit_st.get("stats", {}),
        }

    with _audit_state_lock():
        audit_st = load_audit_state()
        audited = audit_st.setdefault("audited_trades", {})
        uninspected_losses: List[Dict[str, Any]] = []
        newly_skipped_wins = 0

        active_positions_map = st.get("active_positions") or {}
        active_box_ids = {
            str(p.get("box_id") or "").strip()
            for p in (active_positions_map.values() if isinstance(active_positions_map, dict) else [])
            if isinstance(p, dict) and str(p.get("box_id") or "").strip()
        }
        closed_by_box: Dict[str, List[Dict[str, Any]]] = {}
        for _r in closed_positions:
            if isinstance(_r, dict):
                _bk = str(_r.get("box_id") or "").strip()
                if _bk:
                    closed_by_box.setdefault(_bk, []).append(_r)

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

            bk = str(rec.get("box_id") or "").strip()
            is_box_group = bool(bk) and (bool(rec.get("is_dominance_box")) or len(closed_by_box.get(bk, ())) > 1)
            if is_box_group and bk in active_box_ids:
                # Partner leg of the same box is still active / settling; wait for full box resolution
                continue

            raw_pnl = rec.get("net_pnl_usd")
            if is_box_group and len(closed_by_box.get(bk, ())) >= 2:
                box_legs = closed_by_box[bk]
                if any(
                    (
                        x.get("exit_order_status") == "AWAITING_REDEMPTION"
                        or x.get("status") == "AWAITING_ONCHAIN_SETTLEMENT"
                    )
                    and x.get("net_pnl_usd") is None
                    for x in box_legs
                ):
                    continue
                box_net_pnl = sum(
                    float(x.get("net_pnl_usd") if x.get("net_pnl_usd") is not None else (x.get("realized_pnl_usd") or 0.0))
                    for x in box_legs
                )
                won = box_net_pnl >= -1e-6
            elif raw_pnl is not None:
                won = float(raw_pnl) >= 0.0
            else:
                won = bool(rec.get("won") is True)
            if won:
                win_note = (
                    f"Winning multi-leg box leg (box_id={bk}) — auto-cleared."
                    if is_box_group and float(raw_pnl or 0.0) < 0.0
                    else "Winning real-money trade — auto-cleared."
                )
                entry = {
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "trade_id": tid,
                    "sleeve": rec.get("sleeve"),
                    "asset": rec.get("asset"),
                    "net_pnl_usd": rec.get("net_pnl_usd"),
                    "verdict": "PROFIT_OK",
                    "classification": "WIN_AUTO_CLEARED",
                    "notes": win_note,
                }
                audited[tid] = entry
                audit_st["stats"]["profits_skipped"] = audit_st["stats"].get("profits_skipped", 0) + 1
                newly_skipped_wins += 1
                append_audit_ledger(entry)
            else:
                rec_enriched = dict(rec)
                rec_enriched["forensic_classification_hint"] = classify_losing_trade_forensics(rec)
                uninspected_losses.append(rec_enriched)

        if newly_skipped_wins > 0 or not AUDIT_STATE_FILE.exists():
            save_audit_state(audit_st)
        stats_snapshot = dict(audit_st.get("stats", {}))

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
        "audit_stats": stats_snapshot,
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
        if any(tok in notes_low for tok in _TYPE2_PARAM_TOKENS) and any(
            vb in notes_low for vb in _TUNE_VERBS
        ):
            raise ValueError(
                "GOVERNANCE_VIOLATION: Numerical strategy/risk parameter tuning cannot be recorded as BUG_FIXED; "
                "use --verdict PARAM_WFO_REQUIRED."
            )

    with _audit_state_lock():
        audit_st = load_audit_state()
        audited = audit_st.setdefault("audited_trades", {})
        existing = audited.get(trade_id)
        if isinstance(existing, dict) and existing.get("verdict") not in (None, "HISTORICAL_BASELINE"):
            print(json.dumps({"ok": True, "already_audited": True, "recorded": existing}, indent=2))
            return existing

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


def _is_restart_safe_frozen_uma_lock(pos: Dict[str, Any], now_ts: Optional[float] = None) -> bool:
    """
    Matches `scripts/paa_flat_harvester_redeploy_once.py:_is_restart_safe_frozen_uma_lock` and
    `riskless_protocol_v2_expansion.py:is_post_expiry_uma_frozen_lock`: returns True ONLY for
    passive post-expiry (`>= expiry + 60s`) UMA-disputed or `>= 4h` oracle-lagged positions
    carrying zero active CLOB exit/unwind orders (`KMIA` Nov 7 safe-restart invariant `POL-07`).
    """
    if not isinstance(pos, dict):
        return False
    now_f = float(time.time() if now_ts is None else now_ts)
    try:
        from scripts.paa_flat_harvester_redeploy_once import _is_restart_safe_frozen_uma_lock as _flat_uma_lock
        if _flat_uma_lock(pos, now_f):
            return True
    except Exception:
        pass
    if str(pos.get("exit_order_status") or "").upper() in ("UNWIND_RETRY_REQUIRED", "UNWIND_EXECUTION_OUTCOME_UNKNOWN", "PARTIAL_UNWIND_REMAINING"):
        return False
    if pos.get("is_legged_out_residual") and not pos.get("hold_to_maturity_lock") and str(pos.get("umaResolutionStatus") or "").strip().lower() != "disputed":
        return False
    if pos.get("is_liquidating") or pos.get("exit_order_id") or pos.get("unwind_order_id"):
        return False
    bt_frz = str(pos.get("box_type") or "").strip().upper()
    if not (
        pos.get("is_single_leg_lock")
        or pos.get("is_dominance_box")
        or pos.get("hold_to_maturity_lock")
        or bt_frz in {"SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK", "MULTI_LEG_RESIDUAL", "MULTI_LEG_BUNDLE", "DOMINANCE"}
    ):
        return False
    exp_ts = float(pos.get("candle_expiry_ts") or 0.0)
    if exp_ts <= 0.0 or now_f < exp_ts + 60.0:
        return False
    uma_st = str(pos.get("umaResolutionStatus") or pos.get("uma_resolution_status") or "").strip().lower()
    anchor_ts = max(exp_ts, float(pos.get("entry_ts") or 0.0))
    return uma_st == "disputed" or now_f >= anchor_ts + 14400.0


def is_harvester_state_restart_safe(st: Dict[str, Any], now_ts: Optional[float] = None) -> tuple[bool, List[str]]:
    """
    Evaluates whether `live_harvester_state.json` is safe for a graceful `systemctl --user restart`:
      - Allows restart when `active_positions` is empty OR consists solely of post-expiry frozen UMA locks
        (such as the 4 disputed `KMIA` positions with `exit_order_id=None`, `unwind_order_id=None`).
      - Fails closed on any pre-expiry trade, active exit/unwind order, `pre_split_inventory_state.active`,
        `_prepost_sll_reserved_usd > 0`, non-maker `pending_entry_intents`, or missing position detail.
    """
    if not isinstance(st, dict):
        return False, ["INVALID_STATE_PAYLOAD"]
    now_f = float(time.time() if now_ts is None else now_ts)
    blocking: List[str] = []
    if bool((st.get("pre_split_inventory_state") or {}).get("active", False)):
        blocking.append("PRE_SPLIT_INVENTORY_ACTIVE")
    if float(st.get("_prepost_sll_reserved_usd") or 0.0) > 0.0:
        blocking.append("PREPOST_SLL_RESERVED_USD_ACTIVE")
    pend = st.get("pending_entry_intents") or {}
    if isinstance(pend, dict):
        for pk, pv in pend.items():
            if isinstance(pv, dict) and not pv.get("live_maker_anchor_inflight"):
                blocking.append(f"PENDING_ENTRY_INTENT:{pk}")

    act = st.get("active_positions")
    raw_cnt = int(
        st.get("active_positions_count")
        if st.get("active_positions_count") is not None
        else (len(act) if isinstance(act, dict) else 0)
    )
    if raw_cnt > 0 and (not isinstance(act, dict) or len(act) < raw_cnt):
        fallback_ids = [str(x) for x in (st.get("active_position_ids") or [])] or [f"UNSPECIFIED_OPEN_POSITIONS({raw_cnt})"]
        blocking.extend(fallback_ids)
    elif isinstance(act, dict):
        for pid, pos in act.items():
            if not _is_restart_safe_frozen_uma_lock(pos, now_f):
                blocking.append(str(pid))

    return (len(blocking) == 0), blocking


def redeploy_daemon(force: bool = False) -> None:
    if not force:
        pre = fetch_kraken_live_state()["state"]
        safe_ok, blocking_reasons = is_harvester_state_restart_safe(pre)
        if not safe_ok:
            open_cnt = int(pre.get("active_positions_count") or len(pre.get("active_positions") or {}))
            ps_active = bool((pre.get("pre_split_inventory_state") or {}).get("active", False))
            raise RuntimeError(
                f"Refusing to restart live harvester with {open_cnt} open position(s) / pre_split_active={ps_active} "
                f"(blocking={blocking_reasons}): {pre.get('active_position_ids', [])}. Wait until flat."
            )

    cmd = [
        "ssh", "-n", "kraken-finland",
        (
            "/home/skybullet1987/quant_pipeline/venv/bin/python -m py_compile "
            "/home/skybullet1987/quant_pipeline/src/polymarket_research/holistic_strategy_governance.py "
            "/home/skybullet1987/quant_pipeline/src/polymarket_research/riskless_machine_gun_engine.py "
            "/home/skybullet1987/quant_pipeline/src/polymarket_research/riskless_protocol_v2_expansion.py "
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

    with _audit_state_lock():
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

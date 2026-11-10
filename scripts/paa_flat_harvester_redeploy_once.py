#!/usr/bin/env python3
"""
paa_flat_harvester_redeploy_once.py
Persistent systemd-supervised one-shot watcher that waits until `live_harvester_state.json`
has `0` active positions and `0` pending entry intents before restarting
`polymarket-live-harvester.service` onto a newly verified Git revision.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/skybullet1987/quant_pipeline")
STATE = ROOT / "data/polymarket/live_harvester_state.json"
LOG = ROOT / "data/paa_os/flat_redeploy_watcher.log"
LOCK_FILE = Path("/tmp/paa_flat_harvester_redeploy.lock")
ENV = {**os.environ, "XDG_RUNTIME_DIR": "/run/user/1001"}
_LOCK_FH = None


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    line = f"[{ts}] {msg}\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="", flush=True)


def _is_restart_safe_frozen_uma_lock(pos: dict, now_ts: float) -> bool:
    if not isinstance(pos, dict):
        return False
    if pos.get("is_liquidating") or pos.get("exit_order_id") or pos.get("unwind_order_id"):
        return False
    if not (pos.get("is_single_leg_lock") or pos.get("is_dominance_box") or pos.get("hold_to_maturity_lock")):
        return False
    exp_ts = float(pos.get("candle_expiry_ts") or 0.0)
    if exp_ts <= 0.0 or now_ts < exp_ts + 60.0:
        return False
    uma_st = str(pos.get("umaResolutionStatus") or "").strip().lower()
    anchor_ts = max(exp_ts, float(pos.get("entry_ts") or 0.0))
    return uma_st == "disputed" or now_ts >= anchor_ts + 14400.0


def _safe_to_restart(st: dict, now_ts: float | None = None) -> bool:
    act = st.get("active_positions") or {}
    now_f = float(time.time() if now_ts is None else now_ts)
    if any(not _is_restart_safe_frozen_uma_lock(v, now_f) for v in act.values()):
        return False
    if bool((st.get("pre_split_inventory_state") or {}).get("active")):
        return False
    pend = st.get("pending_entry_intents") or {}
    # Resting post-only Maker anchors (`live_maker_anchor_inflight`) are cleanly preempted & canceled
    # on SIGTERM in <0.2s; only block if a non-maker/directional order is mid-submission.
    return not any(
        isinstance(v, dict) and not v.get("live_maker_anchor_inflight")
        for v in pend.values()
    )


def main() -> int:
    global _LOCK_FH
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target_sha = args[0] if args else "HEAD"
    timeout_sec = float(os.environ.get("PM_FLAT_REDEPLOY_TIMEOUT_SEC", "345600"))
    for idx, tok in enumerate(sys.argv[1:], 1):
        if tok == "--timeout-sec" and idx < len(sys.argv) - 1:
            timeout_sec = max(60.0, float(sys.argv[idx + 1]))
        elif tok.startswith("--timeout-sec="):
            timeout_sec = max(60.0, float(tok.split("=", 1)[1]))
    try:
        import fcntl

        _LOCK_FH = open(LOCK_FILE, "a+", encoding="utf-8")
        try:
            fcntl.flock(_LOCK_FH.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log(f"Singleton lock already held ({LOCK_FILE}); skipping duplicate watcher for {target_sha}.")
            return 0
        _LOCK_FH.seek(0)
        _LOCK_FH.truncate()
        _LOCK_FH.write(f"{os.getpid()} {target_sha}\n")
        _LOCK_FH.flush()
    except ImportError:
        pass
    log(f"Armed flat-book harvester redeploy watcher for target SHA {target_sha} (timeout={timeout_sec / 3600.0:.1f}h).")

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            st = json.loads(STATE.read_text(encoding="utf-8"))
            if _safe_to_restart(st):
                log("Detected 0 active_positions (flat inventory)! Waiting 2s stability check...")
                time.sleep(2.0)
                st2 = json.loads(STATE.read_text(encoding="utf-8"))
                if _safe_to_restart(st2):
                    log(f"Executing graceful systemctl --user restart polymarket-live-harvester.service for SHA {target_sha}...")
                    subprocess.run(["systemctl", "--user", "restart", "polymarket-live-harvester.service"], env=ENV, check=True)
                    time.sleep(5.0)
                    act_s = subprocess.run(
                        ["systemctl", "--user", "is-active", "polymarket-live-harvester.service"],
                        env=ENV,
                        capture_output=True,
                        text=True,
                    ).stdout.strip()
                    st3 = json.loads(STATE.read_text(encoding="utf-8"))
                    log(
                        f"Post-redeploy verification: service={act_s}, status={st3.get('status')}, "
                        f"risk_halt={st3.get('risk_halt')}, bankroll=${st3.get('live_bankroll')}"
                    )
                    try:
                        sys.path.insert(0, str(ROOT))
                        from src.paa_os.task_db import PAATaskDB

                        db = PAATaskDB()
                        db.upsert_verified_fact(
                            fact_key="live_harvester_deployed_sha",
                            category="DEPLOYMENT",
                            value={
                                "git_sha": target_sha,
                                "service": act_s,
                                "status": st3.get("status"),
                                "risk_halt": st3.get("risk_halt"),
                            },
                            epistemic_status="VERIFIED_FACT",
                            source_type="SYSTEMD_PROBE",
                            source_ref="paa_flat_harvester_redeploy_once",
                            verified_by="paa_flat_harvester_redeploy_once",
                            ttl_sec=86400.0,
                        )
                    except Exception as db_exc:
                        log(f"DB receipt note: {db_exc}")
                    return 0 if act_s == "active" else 1
        except Exception as exc:
            log(f"Poll warning: {exc}")
        time.sleep(10.0)

    log(f"Watcher timed out after {timeout_sec / 3600.0:.1f}h without flat book.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

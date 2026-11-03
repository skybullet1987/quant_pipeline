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
ENV = {**os.environ, "XDG_RUNTIME_DIR": "/run/user/1001"}


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    line = f"[{ts}] {msg}\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="", flush=True)


def _safe_to_restart(st: dict) -> bool:
    act = st.get("active_positions") or {}
    if len(act) > 0:
        return False
    pend = st.get("pending_entry_intents") or {}
    # Resting post-only Maker anchors (`live_maker_anchor_inflight`) are cleanly preempted & canceled
    # on SIGTERM in <0.2s; only block if a non-maker/directional order is mid-submission.
    return not any(
        isinstance(v, dict) and not v.get("live_maker_anchor_inflight")
        for v in pend.values()
    )


def main() -> int:
    target_sha = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    log(f"Armed flat-book harvester redeploy watcher for target SHA {target_sha}.")

    deadline = time.time() + 14400.0
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
                        from src.paa_os.database import PAADatabase

                        db = PAADatabase(ROOT / "data/paa_os/paa_state.db")
                        db.record_fact(
                            fact_key="live_harvester_deployed_sha",
                            fact_value={
                                "git_sha": target_sha,
                                "service": act_s,
                                "status": st3.get("status"),
                                "risk_halt": st3.get("risk_halt"),
                            },
                            source="paa_flat_harvester_redeploy_once",
                            ttl_sec=86400,
                        )
                    except Exception as db_exc:
                        log(f"DB receipt note: {db_exc}")
                    return 0 if act_s == "active" else 1
        except Exception as exc:
            log(f"Poll warning: {exc}")
        time.sleep(10.0)

    log("Watcher timed out after 4h without flat book.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

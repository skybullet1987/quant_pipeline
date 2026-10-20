#!/usr/bin/env python3
"""
Clean, graceful reload of the four Polymarket production daemons (v3.5 Zero-Trust Hardening).

All four daemons are managed UNIFORMLY by systemd (user units) so a manual `nohup` copy can never race a
systemd auto-respawn (the twin-recorder bug):

    polymarket-recorder.service        BTC terminal recorder
    polymarket-recorder-eth.service    ETH terminal recorder
    polymarket-trader.service          forward paper trader
    polymarket-live-harvester.service  live real-money harvester

Safety properties
  * Refuses to restart the live harvester (or paper trader) while positions are open unless --force.
  * NEVER uses `pkill -9` first: every stop is SIGTERM (graceful: harvester/paper flush state atomically),
    polled for up to 8s, and only then escalated to SIGKILL as a last resort.
  * Risk limits come from config/polymarket_risk_config.json (single source of truth).
  * Fails closed if the authoritative on-chain collateral balance is unavailable or below the equity floor.
  * Verifies exactly ONE process per daemon afterwards and kills any twin.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PIPELINE_ROOT / ".env")

LIVE_STATE = PIPELINE_ROOT / "data/polymarket/live_harvester_state.json"
PAPER_STATE = PIPELINE_ROOT / "data/polymarket/paper_trader_state.json"
RESERVATIONS = PIPELINE_ROOT / "data/polymarket/inventory_reservations.json"
RESERVATIONS_DRYRUN = PIPELINE_ROOT / "data/polymarket/inventory_reservations.dryrun.json"
KILL_SWITCH = PIPELINE_ROOT / "data/polymarket/KILL_SWITCH"
RESET_MARKER = PIPELINE_ROOT / "data/polymarket/RESET_RISK_ONCE"

UNIT_SRC_DIR = PIPELINE_ROOT / "systemd"
UNIT_DST_DIR = Path.home() / ".config/systemd/user"

# name -> (systemd unit, pgrep pattern used for verification / legacy manual-process migration)
SERVICES = {
    "btc_recorder": ("polymarket-recorder.service", r"polymarket_terminal_recorder\.py.*BTC"),
    "eth_recorder": ("polymarket-recorder-eth.service", r"polymarket_terminal_recorder\.py.*ETH"),
    "paper_trader": ("polymarket-trader.service", r"polymarket_paper_trader\.py"),
    "live_harvester": ("polymarket-live-harvester.service", r"polymarket_live_harvester\.py"),
}
GRACEFUL_STOP_TIMEOUT_S = 8.0


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def sctl(*args, check=False):
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, check=check)


def pgrep(pattern: str) -> list:
    res = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    return [int(p) for p in res.stdout.split() if int(p) != os.getpid()]


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:  # a zombie (state 'Z') has already exited; only its parent has not reaped it yet
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        return state != "Z"
    except Exception:
        return True


def terminate_gracefully(pids: list, timeout: float = GRACEFUL_STOP_TIMEOUT_S) -> None:
    """SIGTERM -> poll up to `timeout` seconds -> SIGKILL only for stragglers."""
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + timeout
    while time.time() < deadline and any(pid_alive(p) for p in pids):
        time.sleep(0.2)
    for pid in pids:
        if pid_alive(pid):
            print(f"[WARN] PID {pid} ignored SIGTERM for {timeout:.0f}s; escalating to SIGKILL.")
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def ensure_kill_switch_removed():
    if KILL_SWITCH.exists():
        KILL_SWITCH.unlink()
        print("✓ Removed KILL_SWITCH flag.")
    else:
        print("✓ No KILL_SWITCH flag present.")


def clean_orphan_test_reservations():
    for f in (RESERVATIONS, RESERVATIONS_DRYRUN):
        if f.exists():
            try:
                with open(f) as fp:
                    d = json.load(fp)
                recs = d.get("reservation_records", {})
                has_test = any(
                    str(r.get("token_id", "")).startswith("0xTOKEN") or str(rid).startswith("EXCEPTION_UNWIND_")
                    for rid, r in recs.items()
                )
                if has_test:
                    f.unlink()
                    print(f"✓ Purged orphan test reservations from {f.name}.")
            except Exception:
                pass


def check_active_positions(force: bool) -> None:
    """Abort BEFORE touching any daemon if a live position (or paper trade) is open, unless --force."""
    blockers = []
    if LIVE_STATE.exists():
        try:
            with open(LIVE_STATE) as f:
                st = json.load(f)
            active = st.get("active_positions", {}) or {}
            count = max(int(st.get("active_positions_count", 0) or 0), len(active))
            if count > 0:
                blockers.append(f"Live Harvester has {count} active position(s): {list(active.keys())}")
            else:
                print("✓ Live Harvester: 0 active positions. Safe to reload.")
        except Exception as e:
            print(f"[WARN] Could not parse live_harvester_state.json ({e})")
            if not force:
                blockers.append("live_harvester_state.json unreadable (refusing to reload blind)")
    if PAPER_STATE.exists():
        try:
            with open(PAPER_STATE) as f:
                pst = json.load(f)
            open_tr = pst.get("open_trades", {}) or {}
            if open_tr:
                blockers.append(f"Paper Trader has {len(open_tr)} open trade(s): {list(open_tr.keys())}")
            else:
                print("✓ Paper Trader: 0 open trades. Safe to reload.")
        except Exception as e:
            print(f"[WARN] Could not parse paper_trader_state.json ({e})")
    if blockers:
        for b in blockers:
            print(f"[{'FORCED' if force else 'ABORT'}] {b}")
        if not force:
            print("Reload aborted so no open position is orphaned. Re-run with --force to override.")
            sys.exit(1)
        print("[FORCE] Proceeding despite open positions (resting exits remain on the exchange).")


def get_onchain_balance() -> float:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    executor = PolymarketLiveExecutor(dry_run=False)
    bal = executor.get_collateral_balance(max_cache_age_s=0.0)
    if bal is None or not (isinstance(bal, (int, float)) and bal > 0):
        raise RuntimeError(f"Authoritative CLOB L2 collateral balance unavailable: {bal!r}")
    return float(bal)


# --------------------------------------------------------------------------------------
# systemd management
# --------------------------------------------------------------------------------------
def install_units() -> bool:
    """Copies repo unit files to ~/.config/systemd/user when they differ; returns True if a daemon-reload ran."""
    UNIT_DST_DIR.mkdir(parents=True, exist_ok=True)
    changed = False
    for unit, _ in SERVICES.values():
        src, dst = UNIT_SRC_DIR / unit, UNIT_DST_DIR / unit
        if not src.exists():
            print(f"[WARN] Missing repo unit file {src}")
            continue
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dst)
            changed = True
            print(f"✓ Installed unit {unit}")
    if changed:
        sctl("daemon-reload", check=True)
        print("✓ systemctl --user daemon-reload")
    return changed


def stop_service(key: str) -> None:
    """Graceful stop: systemd SIGTERM (KillSignal) honoring TimeoutStopSec, then sweep any non-systemd stragglers."""
    unit, pattern = SERVICES[key]
    sctl("stop", unit)
    stragglers = pgrep(pattern)
    if stragglers:
        print(f"Stopping {len(stragglers)} non-systemd {key} process(es) gracefully: {stragglers}")
        terminate_gracefully(stragglers)


def start_service(key: str) -> None:
    unit, _ = SERVICES[key]
    sctl("enable", unit)
    res = sctl("start", unit)
    if res.returncode != 0:
        print(f"[ERROR] systemctl start {unit} failed: {res.stderr.strip()}")


def unit_main_pid(unit: str) -> int:
    out = sctl("show", "-p", "MainPID", "--value", unit).stdout.strip()
    return int(out) if out.isdigit() else 0


def dedupe(key: str) -> list:
    """Keep exactly one process per daemon: the systemd MainPID (else newest). Returns surviving PIDs."""
    unit, pattern = SERVICES[key]
    pids = sorted(pgrep(pattern))
    if len(pids) <= 1:
        return pids
    keep = unit_main_pid(unit)
    if keep not in pids:
        keep = pids[-1]
    for pid in pids:
        if pid != keep:
            print(f"Killing duplicate {key} PID {pid} (keeping {keep})")
            terminate_gracefully([pid], timeout=3.0)
    return sorted(pgrep(pattern))


def main():
    ap = argparse.ArgumentParser(description="Graceful Polymarket daemon reload (systemd-managed).")
    ap.add_argument("--force", action="store_true", help="Reload even if live/paper positions are open.")
    ap.add_argument("--keep-risk-state", action="store_true",
                    help="Do NOT drop the one-shot RESET_RISK_ONCE marker (preserve persisted halt/loss counters).")
    args = ap.parse_args()

    from src.polymarket_research.polymarket_live_executor import load_risk_config
    cfg = load_risk_config()

    print("=" * 70)
    print("   POLYMARKET DAEMON PRODUCTION RELOAD (v3.5 systemd + graceful SIGTERM)")
    print("=" * 70)
    print(
        f"Risk config: floor=${cfg['min_equity_floor']:.2f} daily_loss=${cfg['max_daily_loss']:.2f} "
        f"max_exposure=${cfg['max_exposure']:.2f} ticket={cfg['dynamic_risk_pct']*100:.0f}% "
        f"(-> {cfg['scale_up_risk_pct']*100:.0f}% above ${cfg['scale_up_equity_threshold']:.0f})"
    )

    check_active_positions(args.force)
    ensure_kill_switch_removed()
    clean_orphan_test_reservations()

    # Fail-closed: NEVER fall back to a hardcoded balance!
    usdc_bal = get_onchain_balance()
    print(f"✓ Authoritative On-Chain Balance: ${usdc_bal:.2f} USDC")
    from src.polymarket_research.polymarket_live_harvester import get_equity_tier_limits
    tier_limits = get_equity_tier_limits(usdc_bal)
    floor = tier_limits["min_equity_floor"]
    if usdc_bal < floor and os.getenv("POLYMARKET_ALLOW_BELOW_FLOOR_RELOAD", "0") != "1":
        print(
            f"[CIRCUIT BREAKER BLOCK] Live collateral (${usdc_bal:.2f}) is below the ${floor:.2f} equity floor. "
            "Refusing to reload unless POLYMARKET_ALLOW_BELOW_FLOOR_RELOAD=1."
        )
        sys.exit(1)
    risk_pct = tier_limits["dynamic_bankroll_pct"]
    lot_size = round(risk_pct * usdc_bal, 2)
    max_exposure = tier_limits["max_exposure"]
    max_concurrent = tier_limits["max_concurrent_positions"]
    max_daily_loss = tier_limits["max_daily_loss"]
    print(f"✓ Dynamic {risk_pct*100:.0f}% Sizing ({tier_limits['tier']} Tier): ${lot_size:.2f} USD base ticket (on ${usdc_bal:.2f} bankroll)")
    print(f"✓ Auto-Stepping Tier Limits: max_exposure=${max_exposure:.2f}, max_concurrent={max_concurrent}, max_daily_loss=${max_daily_loss:.2f}, floor=${floor:.2f}")

    install_units()

    # Stop consumers first (live harvester, then paper trader), then restart producers (recorders).
    print("Stopping live harvester & paper trader gracefully (SIGTERM, state flush)...")
    stop_service("live_harvester")
    legacy_wrappers = pgrep(r"run_polymarket_harvester\.sh")
    if legacy_wrappers:
        terminate_gracefully(legacy_wrappers, timeout=3.0)  # legacy nohup supervisor (exits itself on rc=0)
    stop_service("paper_trader")

    print("Restarting terminal recorders via systemd...")
    for key in ("btc_recorder", "eth_recorder"):
        unit, pattern = SERVICES[key]
        stragglers = [p for p in pgrep(pattern) if p != unit_main_pid(unit)]
        if stragglers:
            terminate_gracefully(stragglers)
        sctl("enable", unit)
        sctl("restart", unit)
    time.sleep(3)

    if not args.keep_risk_state and not os.getenv("POLYMARKET_DRY_RUN"):
        RESET_MARKER.parent.mkdir(parents=True, exist_ok=True)
        RESET_MARKER.touch()  # consumed exactly once by the harvester at startup (== legacy --reset-risk)

    print("Starting paper trader and live harvester under systemd...")
    start_service("paper_trader")
    start_service("live_harvester")

    time.sleep(7)  # outlast RestartSec so any (unwanted) respawn would have appeared

    report = {}
    for key in SERVICES:
        report[key] = dedupe(key)

    print("=" * 70)
    print("            v3.6 PRODUCTION DAEMON REPORT")
    print("=" * 70)
    all_ok = True
    for idx, (key, (unit, _)) in enumerate(SERVICES.items(), 1):
        pids = report[key]
        ok = len(pids) == 1
        all_ok &= ok
        active = sctl("is-active", unit).stdout.strip()
        print(f"{idx}. {key:<15} PID(s): {pids}  systemd={active:<10} {'[RUNNING OK]' if ok else '[CHECK!]'}")
    print(f"Risk limits:       floor ${floor:.2f} | daily loss ${max_daily_loss:.2f} | "
          f"max exposure ${max_exposure:.2f} | concurrent {max_concurrent} [{tier_limits['tier']} Tier]")
    print(f"Ticket sizing:     {risk_pct*100:.0f}% -> ${lot_size:.2f} base (2nd correlated ~54% of that)")
    print(f"Capacity cap:      --max-ticket-cap 200.0 --max-price-ceiling 0.86")
    print(f"Exactly 1 PID/daemon: {'YES' if all_ok else 'NO'}")
    print("=" * 70)

    print("\nLive Harvester State (data/polymarket/live_harvester_state.json):")
    if LIVE_STATE.exists():
        try:
            with open(LIVE_STATE) as f:
                state_data = json.load(f)
            for noisy in ("seen_shock_ids", "traded_market_ids", "closed_positions", "redeemed_tx_hashes"):
                if noisy in state_data:
                    state_data[noisy] = f"<{len(state_data[noisy])} entries>"
            print(json.dumps(state_data, indent=2))
        except Exception as e:
            print(f"[WARN] Error reading {LIVE_STATE}: {e}")
    sys.exit(0 if all_ok else 2)


if __name__ == "__main__":
    main()

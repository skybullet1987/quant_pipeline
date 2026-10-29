#!/usr/bin/env python3
"""Interactive secret-safe helper to save Polymarket Builder Relayer credentials into .env on kraken-finland."""
import getpass
import json
import os
import pathlib
import subprocess
import sys


def count_live_open_or_pending_positions(st: dict) -> int:
    if not isinstance(st, dict):
        return 0
    act = st.get("active_positions")
    pend = st.get("pending_entry_intents")
    n_act = len(act) if isinstance(act, dict) else int(st.get("active_positions_count", 0) or 0)
    n_pend = len(pend) if isinstance(pend, dict) else 0
    return max(int(st.get("active_positions_count", 0) or 0), n_act) + n_pend


def main() -> None:
    repo = pathlib.Path("/home/skybullet1987/quant_pipeline")
    env_path = repo / ".env"

    print("=================================================================")
    print("  DOMINUS — ADD POLYMARKET BUILDER KEYS (HIDDEN INPUT, NO ECHO)  ")
    print("  Tip: Right-click to paste each value, then press Enter.        ")
    print("       (Nothing will appear on screen while pasting — normal!)   ")
    print("=================================================================")

    key = getpass.getpass("1) Paste POLY_BUILDER_API_KEY, then press Enter: ").strip().strip('"').strip("'")
    sec = getpass.getpass("2) Paste POLY_BUILDER_SECRET, then press Enter: ").strip().strip('"').strip("'")
    pas = getpass.getpass("3) Paste POLY_BUILDER_PASSPHRASE, then press Enter: ").strip().strip('"').strip("'")

    if not (key and sec and pas):
        sys.exit("\nABORTED: One or more fields were empty. Nothing was changed.")
    if any(any(ch in v for ch in ("\r", "\n", "\x00")) for v in (key, sec, pas)):
        sys.exit("\nABORTED: Control/newline characters detected in pasted credential.")

    existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    lines = [
        ln for ln in existing
        if not ln.strip().startswith(("POLY_BUILDER_API_KEY=", "POLY_BUILDER_SECRET=", "POLY_BUILDER_PASSPHRASE="))
    ]
    lines += [
        f"POLY_BUILDER_API_KEY={key}",
        f"POLY_BUILDER_SECRET={sec}",
        f"POLY_BUILDER_PASSPHRASE={pas}",
    ]
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    tmp_path = env_path.with_name(f".env.tmp.{os.getpid()}")
    fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp_path), str(env_path))
    env_path.chmod(0o600)
    print(f"\n[OK] Saved Builder keys atomically to {env_path} (chmod 600) | lengths: key={len(key)}, secret={len(sec)}, pass={len(pas)}")

    st_path = repo / "data/polymarket/live_harvester_state.json"
    open_n = 0
    if st_path.exists():
        st = json.loads(st_path.read_text(encoding="utf-8"))
        open_n = count_live_open_or_pending_positions(st)

    if open_n == 0:
        subprocess.run(["systemctl", "--user", "restart", "polymarket-live-harvester.service"], check=True)
        print("[OK] Flat (0 open positions) -> restarted polymarket-live-harvester.service with Builder Relayer armed!")
    else:
        print(f"[NOTE] {open_n} live position(s) currently open — keys are saved; harvester will pick them up once restarted flat.")


if __name__ == "__main__":
    main()

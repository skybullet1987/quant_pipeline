#!/usr/bin/env python3
"""Interactive secret-safe helper to save venue API credentials into .env on kraken-finland."""
from __future__ import annotations

import getpass
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Dict, List, Tuple

PRESETS: Dict[str, Tuple[str, List[str]]] = {
    "1": (
        "Polymarket Builder Relayer Keys",
        ["POLY_BUILDER_API_KEY", "POLY_BUILDER_SECRET", "POLY_BUILDER_PASSPHRASE"],
    ),
    "2": (
        "Predict.fun Mainnet API Key (Stage G Read-Only / Mainnet)",
        ["PREDICT_FUN_API_KEY"],
    ),
    "3": (
        "SX Bet OBv3 API Key",
        ["SX_BET_API_KEY"],
    ),
    "4": (
        "Limitless Exchange API Key",
        ["LIMITLESS_API_KEY"],
    ),
    "5": (
        "Polymarket CLOB L2 API Keys",
        ["POLY_API_KEY", "POLY_SECRET", "POLY_PASSPHRASE"],
    ),
}

ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


def count_live_open_or_pending_positions(st: dict) -> int:
    if not isinstance(st, dict):
        return 0
    act = st.get("active_positions")
    pend = st.get("pending_entry_intents")
    n_act = len(act) if isinstance(act, dict) else int(st.get("active_positions_count", 0) or 0)
    n_pend = len(pend) if isinstance(pend, dict) else 0
    return max(int(st.get("active_positions_count", 0) or 0), n_act) + n_pend


def atomic_upsert_env(env_path: pathlib.Path, updates: Dict[str, str]) -> None:
    existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    prefixes = tuple(f"{k}=" for k in updates)
    kept = [ln for ln in existing if not ln.strip().startswith(prefixes)]
    for k, v in updates.items():
        kept.append(f"{k}={v}")

    payload = ("\n".join(kept) + "\n").encode("utf-8")
    tmp_path = env_path.with_name(f".env.tmp.{os.getpid()}")
    fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp_path), str(env_path))
    env_path.chmod(0o600)


def prompt_secret(var_name: str) -> str:
    val = getpass.getpass(f"  Paste {var_name} (hidden, right-click then Enter): ").strip().strip('"').strip("'")
    if not val:
        sys.exit(f"\nABORTED: {var_name} was empty. Nothing was changed.")
    if any(ch in val for ch in ("\r", "\n", "\x00")):
        sys.exit(f"\nABORTED: Control/newline characters detected in {var_name}.")
    return val


def main() -> None:
    repo = pathlib.Path("/home/skybullet1987/quant_pipeline")
    env_path = repo / ".env"

    print("=====================================================================")
    print("  DOMINUS — SAVE API KEYS TO FINLAND VM (.env, CHMOD 600, NO ECHO)   ")
    print("=====================================================================")
    for code, (label, keys) in PRESETS.items():
        print(f"  [{code}] {label} ({', '.join(keys)})")
    print("  [6] Custom .env Variable(s) (e.g. DERIBIT_CLIENT_ID, KALSHI_KEY_ID)")
    print("=====================================================================")

    choice = input("Select option [1-6]: ").strip()
    updates: Dict[str, str] = {}

    if choice in PRESETS:
        label, keys = PRESETS[choice]
        print(f"\nSelected: {label}")
        for k in keys:
            updates[k] = prompt_secret(k)
    elif choice == "6":
        raw_names = input("Enter ENV variable name(s), comma-separated (e.g. MY_API_KEY,MY_API_SECRET): ").strip()
        names = [n.strip().upper() for n in raw_names.split(",") if n.strip()]
        if not names:
            sys.exit("\nABORTED: No variable names entered.")
        for n in names:
            if not ENV_NAME_RE.match(n):
                sys.exit(f"\nABORTED: Invalid variable name '{n}' (use UPPER_SNAKE_CASE).")
            updates[n] = prompt_secret(n)
    else:
        sys.exit("\nABORTED: Invalid selection.")

    atomic_upsert_env(env_path, updates)
    summary = ", ".join(f"{k} (len={len(v)})" for k, v in updates.items())
    print(f"\n[OK] Atomically saved to {env_path} (chmod 600): {summary}")

    if any(k.startswith("POLY_") for k in updates):
        st_path = repo / "data/polymarket/live_harvester_state.json"
        open_n = 0
        if st_path.exists():
            st = json.loads(st_path.read_text(encoding="utf-8"))
            open_n = count_live_open_or_pending_positions(st)
        if open_n == 0:
            ans = input("0 open positions detected. Restart polymarket-live-harvester.service now? [y/N]: ").strip().lower()
            if ans == "y":
                subprocess.run(["systemctl", "--user", "restart", "polymarket-live-harvester.service"], check=True)
                print("[OK] Restarted polymarket-live-harvester.service cleanly.")
        else:
            print(f"[NOTE] {open_n} live position(s) open — keys saved; harvester will load them on next flat restart.")


if __name__ == "__main__":
    main()

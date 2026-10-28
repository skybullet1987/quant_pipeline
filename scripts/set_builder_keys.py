#!/usr/bin/env python3
"""Interactive secret-safe helper to save Polymarket Builder Relayer credentials into .env on kraken-finland."""
import getpass
import json
import pathlib
import subprocess
import sys


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
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    env_path.chmod(0o600)
    print(f"\n[OK] Saved Builder keys to {env_path} (chmod 600) | lengths: key={len(key)}, secret={len(sec)}, pass={len(pas)}")

    st_path = repo / "data/polymarket/live_harvester_state.json"
    open_n = 0
    if st_path.exists():
        st = json.loads(st_path.read_text(encoding="utf-8"))
        open_n = int(st.get("active_positions_count", 0) or 0)

    if open_n == 0:
        subprocess.run(["systemctl", "--user", "restart", "polymarket-live-harvester.service"], check=True)
        print("[OK] Flat (0 open positions) -> restarted polymarket-live-harvester.service with Builder Relayer armed!")
    else:
        print(f"[NOTE] {open_n} live position(s) currently open — keys are saved; harvester will pick them up once restarted flat.")


if __name__ == "__main__":
    main()

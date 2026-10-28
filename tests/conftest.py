import os
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def _polymarket_test_sandbox_isolation(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Automatic sandbox isolation for all unit tests so zero `PYTEST_CURRENT_TEST`
    branches exist anywhere in `src/polymarket_research/`.
    Isolates order ledgers, inventory reservations, operational alerts, Unix IPC
    socket names, shadow trackers, and `/dev/shm` fast-tick files into `tmp_path`.
    """
    if "test_polymarket_live_qa" not in request.node.nodeid:
        from unittest.mock import MagicMock
        import src.polymarket_research.polymarket_live_executor as ex_mod

        monkeypatch.setattr(ex_mod, "ClobClient", MagicMock(name="OfflineClobClient"))
        monkeypatch.setattr(ex_mod, "PY_CLOB_AVAILABLE", True)
        if not os.getenv("POLYGON_PRIVATE_KEY"):
            monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
        if not (os.getenv("POLYGON_FUNDER_ADDRESS") or os.getenv("POLYGON_PROXY_ADDRESS")):
            monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
        if not os.getenv("POLYGON_SIGNATURE_TYPE"):
            monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "3")
        monkeypatch.setenv("PM_ENABLE_TLS_KEEPALIVE", "0")
        monkeypatch.setenv("PM_ENABLE_USER_WS", "0")
    shm_dir = tmp_path / "default_shm"
    tele_dir = tmp_path / "default_tele"
    shm_dir.mkdir(parents=True, exist_ok=True)
    tele_dir.mkdir(parents=True, exist_ok=True)
    # Seed empty `{}` fast-tick files: mtime is fresh (so recorder watchdog passes in
    # mock harvester tests that don't override PM_FAST_TICK_DIR), while `ts` is absent
    # so `read_fast_tick()` / `_get_verified_shm_book()` cleanly return None.
    for asset in ("BTC", "ETH", "SOL"):
        (shm_dir / f"pm_fast_tick_{asset}.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("POLYMARKET_LEDGER_PATH", str(tmp_path / "test_live_orders.jsonl"))
    monkeypatch.setenv("POLYMARKET_RESERVATIONS_PATH", str(tmp_path / "test_inventory_reservations.json"))
    monkeypatch.setenv("POLYMARKET_ALERTS_FILE", "")
    monkeypatch.setenv("POLYMARKET_ALERTS_SUPPRESS_HTTP", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(shm_dir))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tele_dir))
    monkeypatch.setenv("PM_SHADOW_TRACKER_FILE", str(tmp_path / "test_shadow_tracker.jsonl"))
    monkeypatch.setenv("PM_SVI_DISABLE_BG_REFRESH", "1")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_DISABLE_EXP316_LIVE_EMIT", "1")
    monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES", "0")
    monkeypatch.setenv("POLYMARKET_IPC_SOCKET_NAME", f"pm_shock_test_{os.getpid()}_{id(tmp_path) & 0xFFFF}")

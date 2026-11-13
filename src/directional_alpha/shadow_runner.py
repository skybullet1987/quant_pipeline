#!/usr/bin/env python3
"""
Polymarket Directional Alpha — Forward Read-Only Shadow Research Engine (`Deliverable E`)
=========================================================================================
Strictly isolated, zero-credential, swapless-RAM-safe (`< 60 MiB` RSS) forward shadow
evaluation engine for directional Polymarket strategies.

Hard Safety & Isolation Invariants:
  1. Zero Credentials & Zero Live Orders: Never loads `.env`, strips any signing/API env keys
     from process view, and enforces a strict URL/method allowlist (`ShadowIsolationViolationError`
     on any order/cancel/relayer endpoint).
  2. Complete Runtime Isolation from `DOMINUS RISKLESS`: Writes exclusively to
     `data/directional_alpha/shadow_research.sqlite3` (or explicit test path); never touches
     `data/polymarket/*`, `/dev/shm/pm_*`, or the 4 disputed `KMIA` positions (`D-001`).
  3. Swapless Host Memory Safety (`D-010`, `< 60 MiB` RSS): Caps tracked markets (`<= 120`),
     trims L2 depth to top `15` levels per side, strips multi-KB Gamma descriptions, caps
     `aiohttp.TCPConnector(limit=12)`, and invokes `gc.collect()` + `libc.malloc_trim(0)` on Linux.
  4. Honest Microstructure Accounting (`RT-02`, `RT-03`, `D-009`):
     - Taker fills sweep real observed live L2 levels with latency/speedbump drift + exact V2 curved fees.
     - Passive Maker orders enforce `postOnly` non-crossing, initialize FIFO `queue_ahead_shares` from
       live L2 depth at `limit_price`, credit only `35%` of top-level size shrinkage (distinguishing
       cancellations from trades) unless `best_ask <= limit_price` (price traded through), and track
       post-fill adverse markout.
     - Open shadow positions mark strictly to **executable L2 bid net of V2 exit fee** (never midpoint!),
       and apply `$0.00` guaranteed-floor haircut if `umaResolutionStatus == "disputed"`.
"""

from __future__ import annotations

import asyncio
import ctypes
import gc
import json
import math
import os
import sqlite3
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    import aiohttp as _aiohttp
except ImportError:  # pragma: no cover - stdlib urllib fallback supported on LibreOffice Python
    _aiohttp = None  # type: ignore[assignment]

try:
    import orjson as _orjson
except ImportError:  # pragma: no cover
    _orjson = None  # type: ignore[assignment]

from directional_alpha.execution_microstructure import (
    FeeSchedule,
    KRAKEN_FINLAND_CLOB_P50_MS,
    MIN_CLOB_MARKETABLE_NOTIONAL_USD,
    MIN_CLOB_ORDER_SHARES,
    compute_sell_taker_fee_usd,
    derive_complement_l2_book,
    normalize_category_name,
    resolve_fee_schedule,
    resolve_tick_size,
    round_price_to_tick,
    simulate_maker_order,
    simulate_taker_fill,
    validate_and_quantize_order_lot,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SHADOW_DB_PATH = REPO_ROOT / "data" / "directional_alpha" / "shadow_research.sqlite3"

GAMMA_HOST = "gamma-api.polymarket.com"
CLOB_HOST = "clob.polymarket.com"
OPEN_METEO_HOST = "api.open-meteo.com"

ALLOWED_PUBLIC_HOSTS = frozenset({GAMMA_HOST, CLOB_HOST, OPEN_METEO_HOST})
FORBIDDEN_PATH_SUBSTRINGS = (
    "/order",
    "/orders",
    "/cancel",
    "/cancel-all",
    "/cancel-market-orders",
    "/auth/",
    "/data/orders",
    "/data/trades",
    "/balance-allowance",
    "/submit",
)
try:
    from paa_os.permissions import SENSITIVE_SIGNING_ENV_KEYS as _PAA_SENSITIVE_KEYS
except ImportError:  # pragma: no cover
    _PAA_SENSITIVE_KEYS = ("PRIVATE_KEY", "MNEMONIC", "EXECUTION_LIVE_CONFIRMED")

FROZEN_KMIA_MARKET_IDS = frozenset({"6707503", "6707502"})


def _is_sensitive_env_key(key: str) -> bool:
    """Zero-literal credential key detector compliant with `PermissionGate.inspect_candidate_diff` (`RT-10`)."""
    ku = str(key or "").upper()
    return (
        ku in _PAA_SENSITIVE_KEYS
        or ku.startswith(("POLY_", "POLYGON_", "HYPERLIQUID_"))
        or "PRIVATE_KEY" in ku
        or "SECRET" in ku
        or "PASSPHRASE" in ku
        or ku == "MNEMONIC"
    )


class ShadowIsolationViolationError(RuntimeError):
    """Raised immediately if shadow code attempts non-public endpoints, forbidden paths, or prod DB writes."""


def measure_process_rss_mib() -> float:
    """Cross-platform lightweight resident set size (RSS) measurement in MiB (`< 60 MiB` invariant check)."""
    # Linux fast path (`/proc/self/status`)
    proc_status = Path("/proc/self/status")
    if proc_status.exists():
        try:
            for line in proc_status.read_text(encoding="utf-8").splitlines():
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024.0, 2)
        except Exception:
            pass

    # Windows Win32 `K32GetProcessMemoryInfo` via stdlib `ctypes` (64-bit HANDLE safe)
    if os.name == "nt":
        try:
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
            get_cur = k32.GetCurrentProcess
            get_cur.argtypes = []
            get_cur.restype = ctypes.c_void_p
            get_mem = getattr(k32, "K32GetProcessMemoryInfo", None)
            if get_mem is None:
                psapi = ctypes.WinDLL("psapi", use_last_error=True)  # type: ignore[attr-defined]
                get_mem = psapi.GetProcessMemoryInfo
            get_mem.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_ulong]
            get_mem.restype = ctypes.c_int

            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            if get_mem(get_cur(), ctypes.byref(pmc), pmc.cb):
                return round(float(pmc.WorkingSetSize) / (1024.0 * 1024.0), 2)
        except Exception:
            pass
    return 0.0


def reclaim_unused_heap() -> None:
    """Bounds heap fragmentation on swapless Linux VMs (`D-010`)."""
    gc.collect()
    if os.name == "posix":
        try:
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:
            pass


def assert_public_readonly_request(method: str, url: str) -> None:
    """Hard zero-trust network firewall for the shadow runner."""
    m_up = str(method or "").upper()
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in ALLOWED_PUBLIC_HOSTS:
        raise ShadowIsolationViolationError(f"Blocked non-allowlisted host/scheme in shadow mode: {url!r}")
    path_low = (parsed.path or "").lower()
    for bad in FORBIDDEN_PATH_SUBSTRINGS:
        if bad in path_low:
            raise ShadowIsolationViolationError(f"Blocked trading/private path {bad!r} in shadow mode: {url!r}")
    # Only GET is permitted everywhere, plus read-only batch L2 fetch `POST https://clob.polymarket.com/books`
    if m_up == "GET":
        return
    if m_up == "POST" and parsed.netloc == CLOB_HOST and path_low == "/books":
        return
    raise ShadowIsolationViolationError(f"Blocked HTTP method {m_up!r} on {url!r} in read-only shadow mode")


def assert_safe_shadow_db_path(db_path: Path) -> Path:
    """Prevents accidental writes into production `data/polymarket/` or `data/cross_venue_shadow/`."""
    resolved = db_path.resolve()
    norm = str(resolved).replace("\\", "/").lower()
    if "/data/polymarket/" in norm or "/data/cross_venue_shadow/" in norm or "/data/alpha124/" in norm:
        raise ShadowIsolationViolationError(f"Refusing to point directional shadow DB at production path: {resolved}")
    return resolved


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True)
class ShadowSignalIntent:
    strategy_id: str
    market_id: str
    side_label: str  # "YES" or "NO"
    exec_mode: str  # "TAKER" or "MAKER_POST_ONLY"
    notional_usd: float
    model_p_yes_true: float
    limit_price: Optional[float] = None
    exit_policy: str = "PRE_RESOLUTION_EXIT"  # "HOLD_TO_SETTLEMENT" or "PRE_RESOLUTION_EXIT"
    target_exit_px: float = 0.85
    stop_exit_px: float = 0.15
    max_hold_sec: float = 7200.0
    ttl_cycles: int = 3
    rationale: str = ""


# Public alias for cross-agent compatibility (`#33`)
SignalCandidate = ShadowSignalIntent


def _coerce_signal_intent(raw: Any, default_market_id: str = "") -> Optional[ShadowSignalIntent]:
    """Coerces `ShadowSignalIntent`, foreign `SignalCandidate` dataclasses, or dicts into `ShadowSignalIntent`."""
    if isinstance(raw, ShadowSignalIntent):
        return raw
    getter = (lambda k, d=None: raw.get(k, d)) if isinstance(raw, dict) else (lambda k, d=None: getattr(raw, k, d))
    strat_id = str(getter("strategy_id") or getter("sleeve_id") or "").strip()
    mkt_id = str(getter("market_id") or default_market_id or "").strip()
    side_raw = str(getter("side_label") or getter("side") or "").strip().upper()
    if side_raw in ("BUY_YES", "LONG_YES"):
        side_raw = "YES"
    elif side_raw in ("BUY_NO", "LONG_NO"):
        side_raw = "NO"
    if not strat_id or not mkt_id or side_raw not in ("YES", "NO"):
        return None
    exec_raw = str(getter("exec_mode") or getter("execution_mode") or "TAKER").strip().upper()
    if "MAKER" in exec_raw:
        exec_raw = "MAKER_POST_ONLY"
    else:
        exec_raw = "TAKER"
    notional = float(getter("notional_usd") or getter("size_usd") or getter("clip_usd") or 15.0)
    p_yes = getter("model_p_yes_true")
    if p_yes is None:
        p_yes = getter("p_yes_hat")
    if p_yes is None:
        p_hat = getter("p_hat")
        if p_hat is not None:
            p_yes = float(p_hat) if side_raw == "YES" else (1.0 - float(p_hat))
    p_yes_f = max(0.001, min(0.999, float(p_yes if p_yes is not None else 0.5)))
    lim_px = getter("limit_price")
    exit_pol = str(getter("exit_policy") or "HOLD_TO_SETTLEMENT").strip().upper()
    if "EXIT" in exit_pol and "HOLD" not in exit_pol:
        exit_pol = "PRE_RESOLUTION_EXIT"
    elif "HOLD" in exit_pol or "SETTLE" in exit_pol:
        exit_pol = "HOLD_TO_SETTLEMENT"
    return ShadowSignalIntent(
        strategy_id=strat_id,
        market_id=mkt_id,
        side_label=side_raw,
        exec_mode=exec_raw,
        notional_usd=max(1.0, notional),
        model_p_yes_true=round(p_yes_f, 6),
        limit_price=(float(lim_px) if lim_px is not None else None),
        exit_policy=exit_pol,
        target_exit_px=float(getter("target_exit_px") or 0.85),
        stop_exit_px=float(getter("stop_exit_px") or 0.15),
        max_hold_sec=float(getter("max_hold_sec") or 7200.0),
        ttl_cycles=max(1, int(getter("ttl_cycles") or 3)),
        rationale=str(getter("rationale") or "")[:180],
    )


@dataclass
class ShadowConfig:
    db_path: Path = DEFAULT_SHADOW_DB_PATH
    starting_virtual_bankroll_usd: float = 500.0
    max_tracked_markets: int = 60
    max_l2_levels_per_side: int = 12
    max_event_concentration_pct: float = 0.15
    max_open_positions: int = 15
    simulated_clob_latency_ms: float = KRAKEN_FINLAND_CLOB_P50_MS
    maker_cancel_vs_trade_shrink_credit: float = 0.35
    max_rss_mib_budget: float = 60.0
    resume_existing: bool = False
    persistent_run_id: Optional[str] = None
    max_raw_book_obs_rows: int = 200_000


ShadowStrategyFn = Callable[[Dict[str, Any], List[Dict[str, Any]]], Sequence[ShadowSignalIntent]]


# ==============================================================================
# BUILT-IN REFERENCE SHADOW EVALUATION STRATEGIES (FOR LIVE DRY-RUN & BENCHMARK)
# ==============================================================================

def builtin_favorite_no_carry_shadow_strategy(
    snap: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> List[ShadowSignalIntent]:
    """
    Reference Strategy 1 (`SHADOW_FAV_NO_CARRY`):
    Targets multi-outcome/binary retail longshot overpricing (`YES` mid in `[0.04, 0.14]`, i.e., `NO` ask in `[0.86, 0.96]`)
    on low/zero-fee categories where spread <= 2.0c and L1 depth >= $15, testing passive Maker NO accumulation vs Taker.
    """
    mid_yes = float(snap.get("mid_px") or 0.5)
    spread = float(snap.get("spread_px") or 1.0)
    l1_bid_yes_usd = float(snap.get("l1_bid_usd") or 0.0)  # YES bid == NO ask liquidity!
    fee_rate = float(snap.get("fee_rate") or 0.05)
    if not (0.04 <= mid_yes <= 0.14) or spread > 0.022 or l1_bid_yes_usd < 12.0:
        return []
    # Empirical favorite-longshot shrinkage: retail 6c YES tickets resolve ~4.2% on non-crypto markets
    if snap.get("category") == "crypto":
        return []
    shrink = 0.72 if fee_rate <= 0.04 else 0.80
    p_yes_est = max(0.01, mid_yes * shrink)
    q_no_est = 1.0 - p_yes_est
    no_ask = 1.0 - float(snap["best_bid"])
    if q_no_est - no_ask < 0.015:
        return []
    return [
        ShadowSignalIntent(
            strategy_id="SHADOW_FAV_NO_CARRY_TAKER",
            market_id=str(snap["market_id"]),
            side_label="NO",
            exec_mode="TAKER",
            notional_usd=15.0,
            model_p_yes_true=round(p_yes_est, 5),
            exit_policy="HOLD_TO_SETTLEMENT",
            target_exit_px=0.99,
            stop_exit_px=0.60,
            max_hold_sec=86400.0,
            rationale=f"Longshot YES={mid_yes:.3f} shrinkage -> q_NO={q_no_est:.3f} vs ask_NO={no_ask:.3f}",
        )
    ]


def builtin_obi_microprice_shadow_strategy(
    snap: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> List[ShadowSignalIntent]:
    """
    Reference Strategy 2 (`SHADOW_OBI_DRIFT`):
    Tests short-horizon L2 order-book imbalance + microprice divergence (`|obi_5c| >= 0.45`, midrange `0.20..0.80`)
    using passive `postOnly=True` Maker entry at `best_bid` (or +1 tick inside >=2-tick spread) to avoid V2 taker fees.
    """
    mid_yes = float(snap.get("mid_px") or 0.5)
    spread = float(snap.get("spread_px") or 1.0)
    obi_5c = float(snap.get("obi_5c") or 0.0)
    tick = float(snap.get("tick_size") or 0.01)
    if not (0.18 <= mid_yes <= 0.82) or spread > 0.04 or abs(obi_5c) < 0.45:
        return []
    side_label = "YES" if obi_5c > 0 else "NO"
    # Modest 2.2c microprice tilt
    p_yes_est = min(0.95, max(0.05, mid_yes + 0.025 * obi_5c))
    if side_label == "YES":
        b_bid, b_ask = float(snap["best_bid"]), float(snap["best_ask"])
    else:
        b_bid, b_ask = round(1.0 - float(snap["best_ask"]), 6), round(1.0 - float(snap["best_bid"]), 6)
    lim_px = round_price_to_tick(b_bid + tick if (b_ask - b_bid) >= 2.0 * tick - 1e-9 else b_bid, tick, mode="floor")
    if lim_px >= b_ask - 1e-9:
        return []
    return [
        ShadowSignalIntent(
            strategy_id="SHADOW_OBI_MAKER_POSTONLY",
            market_id=str(snap["market_id"]),
            side_label=side_label,
            exec_mode="MAKER_POST_ONLY",
            notional_usd=15.0,
            model_p_yes_true=round(p_yes_est, 5),
            limit_price=lim_px,
            exit_policy="PRE_RESOLUTION_EXIT",
            target_exit_px=min(0.97, lim_px + 0.04),
            stop_exit_px=max(0.03, lim_px - 0.05),
            max_hold_sec=1800.0,
            ttl_cycles=2,
            rationale=f"5c OBI={obi_5c:+.2f} passive maker bid @ {lim_px:.3f}",
        )
    ]


# ==============================================================================
# SHADOW RESEARCH SQLITE STORE & MULTI-CYCLE ENGINE
# ==============================================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS shadow_runs (
    run_id TEXT PRIMARY KEY,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    cycles_completed INTEGER NOT NULL DEFAULT 0,
    starting_virtual_bankroll_usd REAL NOT NULL,
    peak_rss_mib REAL NOT NULL DEFAULT 0.0,
    isolation_verified INTEGER NOT NULL DEFAULT 1,
    config_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shadow_book_observations (
    obs_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    cycle_idx INTEGER NOT NULL,
    observed_at_utc TEXT NOT NULL,
    market_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    category TEXT NOT NULL,
    yes_token_id TEXT NOT NULL,
    best_bid REAL NOT NULL,
    best_ask REAL NOT NULL,
    mid_px REAL NOT NULL,
    spread_px REAL NOT NULL,
    l1_bid_usd REAL NOT NULL,
    l1_ask_usd REAL NOT NULL,
    bid_5c_usd REAL NOT NULL,
    ask_5c_usd REAL NOT NULL,
    obi_5c REAL NOT NULL,
    fee_rate REAL NOT NULL,
    tick_size REAL NOT NULL,
    http_rtt_ms REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS shadow_orders (
    shadow_order_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    category TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side_label TEXT NOT NULL,
    order_side TEXT NOT NULL,
    exec_mode TEXT NOT NULL,
    submitted_at_utc TEXT NOT NULL,
    submitted_cycle INTEGER NOT NULL,
    ttl_cycles INTEGER NOT NULL,
    limit_price REAL NOT NULL,
    requested_shares REAL NOT NULL,
    requested_notional_usd REAL NOT NULL,
    queue_ahead_shares_initial REAL NOT NULL,
    queue_ahead_shares_remaining REAL NOT NULL,
    filled_shares REAL NOT NULL DEFAULT 0.0,
    avg_fill_px REAL NOT NULL DEFAULT 0.0,
    fee_paid_usd REAL NOT NULL DEFAULT 0.0,
    adverse_selection_haircut_prob REAL NOT NULL DEFAULT 0.0,
    model_p_yes_true REAL NOT NULL,
    market_mid_at_submit REAL NOT NULL,
    exit_policy TEXT NOT NULL,
    target_exit_px REAL NOT NULL,
    stop_exit_px REAL NOT NULL,
    max_hold_sec REAL NOT NULL,
    status TEXT NOT NULL,
    reject_reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS shadow_fills (
    fill_id TEXT PRIMARY KEY,
    shadow_order_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    filled_at_utc TEXT NOT NULL,
    cycle_idx INTEGER NOT NULL,
    fill_shares REAL NOT NULL,
    fill_px REAL NOT NULL,
    fee_usd REAL NOT NULL,
    half_spread_cost_usd REAL NOT NULL,
    depth_impact_cost_usd REAL NOT NULL,
    latency_drift_cost_usd REAL NOT NULL,
    mid_px_at_fill REAL NOT NULL,
    post_fill_markout_1cycle_px REAL,
    fill_mechanism TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shadow_positions (
    position_id TEXT PRIMARY KEY,
    shadow_order_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    category TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side_label TEXT NOT NULL,
    opened_at_utc TEXT NOT NULL,
    opened_epoch REAL NOT NULL,
    shares REAL NOT NULL,
    entry_vwap_px REAL NOT NULL,
    entry_cost_with_fees_usd REAL NOT NULL,
    exit_policy TEXT NOT NULL,
    target_exit_px REAL NOT NULL,
    stop_exit_px REAL NOT NULL,
    max_hold_sec REAL NOT NULL,
    latest_executable_bid_px REAL NOT NULL,
    latest_mid_px REAL NOT NULL,
    unrealized_mtb_pnl_usd REAL NOT NULL,
    uma_resolution_status TEXT NOT NULL DEFAULT 'open',
    status TEXT NOT NULL,
    closed_at_utc TEXT,
    exit_or_settle_px REAL,
    exit_fee_usd REAL NOT NULL DEFAULT 0.0,
    realized_net_pnl_usd REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS shadow_cycle_metrics (
    run_id TEXT NOT NULL,
    cycle_idx INTEGER NOT NULL,
    recorded_at_utc TEXT NOT NULL,
    markets_polled INTEGER NOT NULL,
    valid_two_sided_books INTEGER NOT NULL,
    orders_submitted INTEGER NOT NULL,
    resting_maker_orders INTEGER NOT NULL,
    fills_recorded INTEGER NOT NULL,
    open_positions INTEGER NOT NULL,
    virtual_cash_usd REAL NOT NULL,
    mark_to_bid_nav_usd REAL NOT NULL,
    guaranteed_floor_nav_usd REAL NOT NULL,
    realized_net_pnl_usd REAL NOT NULL,
    unrealized_mtb_pnl_usd REAL NOT NULL,
    rss_mib REAL NOT NULL,
    cycle_wall_ms REAL NOT NULL,
    PRIMARY KEY (run_id, cycle_idx)
);

CREATE INDEX IF NOT EXISTS idx_shadow_orders_run_status ON shadow_orders(run_id, status);
CREATE INDEX IF NOT EXISTS idx_shadow_pos_run_status ON shadow_positions(run_id, status);
CREATE INDEX IF NOT EXISTS idx_shadow_obs_run_mkt ON shadow_book_observations(run_id, market_id, cycle_idx);
"""


class ForwardShadowRunner:
    """
    Read-only forward shadow research runner evaluating directional strategy signals against
    real live (or deterministically replayed) Polymarket L2 order books.
    """

    def __init__(
        self,
        config: Optional[ShadowConfig] = None,
        strategies: Optional[Sequence[ShadowStrategyFn]] = None,
    ) -> None:
        self.config = config or ShadowConfig()
        self.db_path = assert_safe_shadow_db_path(Path(self.config.db_path))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.strategies: List[ShadowStrategyFn] = list(
            strategies if strategies is not None else [builtin_favorite_no_carry_shadow_strategy, builtin_obi_microprice_shadow_strategy]
        )

        # Verify no private credentials are ever imported or cached on self (`RT-10` compliant)
        self._sanitized_env_check = {
            k: "REDACTED_IGNORED" for k in os.environ.keys() if _is_sensitive_env_key(k)
        }

        self.run_id = (
            str(self.config.persistent_run_id).strip()
            if self.config.persistent_run_id
            else f"SHDW_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )
        self.virtual_cash_usd = float(self.config.starting_virtual_bankroll_usd)
        self.realized_net_pnl_usd = 0.0
        self.cycles_completed_offset = 0
        self.peak_rss_mib = measure_process_rss_mib()
        self._history_by_market: Dict[str, List[Dict[str, Any]]] = {}
        self._last_level_sizes: Dict[Tuple[str, str, float], float] = {}
        self._pending_markout_fills: List[Tuple[str, str, str, float]] = []  # (fill_id, market_id, side_label, fill_px)
        self._signals_emitted_by_sleeve: Dict[str, int] = {}
        self._rtt_history_ms: List[float] = []

        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(
            "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA temp_store=MEMORY; PRAGMA cache_size=-4096; PRAGMA mmap_size=0;\n"
            + SCHEMA_SQL
        )
        cfg_dict = asdict(self.config)
        cfg_dict["db_path"] = str(self.db_path)
        if self.config.resume_existing:
            existing = self._conn.execute(
                "SELECT run_id, cycles_completed, peak_rss_mib FROM shadow_runs WHERE run_id = ? ORDER BY started_at_utc DESC LIMIT 1",
                (self.run_id,),
            ).fetchone()
            if existing is None and not self.config.persistent_run_id:
                existing = self._conn.execute(
                    "SELECT run_id, cycles_completed, peak_rss_mib FROM shadow_runs WHERE completed_at_utc IS NULL ORDER BY started_at_utc DESC LIMIT 1"
                ).fetchone()
            if existing is not None:
                self.run_id = str(existing["run_id"])
                self.cycles_completed_offset = int(existing["cycles_completed"] or 0)
                self.peak_rss_mib = max(self.peak_rss_mib, float(existing["peak_rss_mib"] or 0.0))
                last_m = self._conn.execute(
                    "SELECT virtual_cash_usd, realized_net_pnl_usd FROM shadow_cycle_metrics WHERE run_id = ? ORDER BY cycle_idx DESC LIMIT 1",
                    (self.run_id,),
                ).fetchone()
                if last_m is not None:
                    self.virtual_cash_usd = float(last_m["virtual_cash_usd"])
                    self.realized_net_pnl_usd = float(last_m["realized_net_pnl_usd"])
                self._conn.execute("UPDATE shadow_runs SET completed_at_utc = NULL WHERE run_id = ?", (self.run_id,))
                self._conn.commit()
                return
        self._conn.execute(
            """
            INSERT OR REPLACE INTO shadow_runs (run_id, started_at_utc, starting_virtual_bankroll_usd, peak_rss_mib, isolation_verified, config_json)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (self.run_id, utc_now_iso(), self.virtual_cash_usd, self.peak_rss_mib, json.dumps(cfg_dict)),
        )
        self._conn.commit()

    def close(self, mark_completed: bool = True) -> None:
        try:
            comp_ts = utc_now_iso() if mark_completed else None
            self._conn.execute(
                "UPDATE shadow_runs SET completed_at_utc = ?, peak_rss_mib = ? WHERE run_id = ?",
                (comp_ts, self.peak_rss_mib, self.run_id),
            )
            self._conn.commit()
        finally:
            self._conn.close()

    # ------------------------------------------------------------------
    # Public Read-Only Market Discovery & L2 Book Ingestion
    # ------------------------------------------------------------------

    async def discover_live_watchlist(
        self,
        limit: Optional[int] = None,
        retain_existing: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Discovers diverse active markets via public Gamma REST (slimming descriptions immediately for `<75 MiB` RAM)."""
        cap = min(180, int(limit or self.config.max_tracked_markets))
        per_tag = max(8, cap // 7)
        urls = [
            f"https://{GAMMA_HOST}/events?active=true&closed=false&tag_slug=politics&limit={per_tag}&order=volume24hr&ascending=false",
            f"https://{GAMMA_HOST}/events?active=true&closed=false&tag_slug=geopolitics&limit={per_tag}&order=volume24hr&ascending=false",
            f"https://{GAMMA_HOST}/events?active=true&closed=false&tag_slug=economics&limit={per_tag}&order=volume24hr&ascending=false",
            f"https://{GAMMA_HOST}/events?active=true&closed=false&tag_slug=weather&limit={per_tag}&order=volume24hr&ascending=false",
            f"https://{GAMMA_HOST}/events?active=true&closed=false&tag_slug=finance&limit={per_tag}&order=volume24hr&ascending=false",
            f"https://{GAMMA_HOST}/events?active=true&closed=false&tag_slug=crypto&limit={per_tag}&order=volume24hr&ascending=false",
            f"https://{GAMMA_HOST}/events?active=true&closed=false&tag_slug=sports&limit={per_tag}&order=volume24hr&ascending=false",
            f"https://{GAMMA_HOST}/events?active=true&closed=false&tag_slug=tech&limit={max(6, per_tag // 2)}&order=volume24hr&ascending=false",
        ]
        seen: Dict[str, Dict[str, Any]] = {}
        # Always retain markets with open positions or resting orders across watchlist refreshes
        if retain_existing:
            must_keep = {
                str(r[0])
                for r in self._conn.execute(
                    """
                    SELECT market_id FROM shadow_positions WHERE run_id = ? AND status IN ('OPEN', 'DISPUTED_HAIRCUITED')
                    UNION
                    SELECT market_id FROM shadow_orders WHERE run_id = ? AND status IN ('RESTING', 'PARTIALLY_FILLED')
                    """,
                    (self.run_id, self.run_id),
                ).fetchall()
            }
            for item in retain_existing:
                mid_keep = str(item.get("market_id") or "")
                if mid_keep in must_keep and mid_keep not in FROZEN_KMIA_MARKET_IDS:
                    seen[mid_keep] = dict(item)

        try:
            from directional_alpha.live_shadow_signals import enrich_watchlist_metadata_from_gamma as _enrich_gamma
        except Exception:
            _enrich_gamma = None

        payloads = await self._http_get_many_json(urls)
        for p in payloads:
            if not isinstance(p, list):
                continue
            for ev in p:
                if not isinstance(ev, dict):
                    continue
                ev_id = str(ev.get("id") or "")
                ev_title = str(ev.get("title") or "")[:110]
                ev_mkts_all = [x for x in (ev.get("markets") or []) if isinstance(x, dict) and x.get("active") and not x.get("closed")]
                ev_mkt_cnt = len(ev_mkts_all)
                ev_neg_risk = bool(ev.get("negRisk"))
                ev_neg_aug = bool(ev.get("negRiskAugmented"))
                per_ev_cap = 5 if (ev_neg_aug or ev_mkt_cnt >= 5) else 2
                for m in ev_mkts_all[:per_ev_cap]:
                    if m.get("acceptingOrders") is False:
                        continue
                    mid = str(m.get("id") or "")
                    if not mid or mid in seen or mid in FROZEN_KMIA_MARKET_IDS:
                        continue
                    tids = m.get("clobTokenIds")
                    if isinstance(tids, str):
                        try:
                            tids = json.loads(tids)
                        except Exception:
                            tids = []
                    if not isinstance(tids, list) or len(tids) < 2:
                        continue
                    sched = resolve_fee_schedule(market_meta=m)
                    cat = normalize_category_name(
                        str(m.get("category") or ""),
                        f"{m.get('slug', '')} {m.get('question', '')} {ev_title}",
                    )
                    vol_usd = float(m.get("volumeNum") or m.get("volume") or 0.0)
                    extra_meta = _enrich_gamma(m, ev) if _enrich_gamma is not None else {}
                    # Slim metadata only: NEVER retain multi-KB `description` strings (`F-01` lesson!)
                    seen[mid] = {
                        **extra_meta,
                        "market_id": mid,
                        "condition_id": str(m.get("conditionId") or ""),
                        "event_id": ev_id or mid,
                        "event_title": ev_title,
                        "event_market_count": max(ev_mkt_cnt, int(extra_meta.get("event_market_count") or 0)),
                        "neg_risk": bool(m.get("negRisk") or ev_neg_risk or extra_meta.get("neg_risk")),
                        "neg_risk_augmented": bool(m.get("negRiskAugmented") or ev_neg_aug or extra_meta.get("neg_risk_augmented")),
                        "group_item_title": str(m.get("groupItemTitle") or "")[:80],
                        "slug": str(m.get("slug") or "")[:96],
                        "question": str(m.get("question") or "")[:140],
                        "category": cat,
                        "yes_token_id": str(tids[0]),
                        "no_token_id": str(tids[1]),
                        "fee_schedule": sched,
                        "fees_enabled": sched.fees_enabled,
                        "fee_type": sched.fee_type,
                        "tick_size": float(m.get("orderPriceMinTickSize") or 0.01),
                        "liquidity_usd": float(m.get("liquidityNum") or 0.0),
                        "volume_usd": vol_usd,
                        "volume_24h_usd": float(m.get("volume24hr") or 0.0),
                        "end_date_iso": str(m.get("endDate") or "")[:32],
                        "uma_resolution_status": str(m.get("umaResolutionStatus") or "open"),
                        "closed": bool(m.get("closed")),
                        "outcome_prices": m.get("outcomePrices"),
                    }
                    if len(seen) >= cap:
                        break
                if len(seen) >= cap:
                    break
        reclaim_unused_heap()
        return list(seen.values())[:cap]

    async def fetch_live_books_for_watchlist(
        self,
        watchlist: Sequence[Dict[str, Any]],
    ) -> Tuple[Dict[str, Dict[str, Any]], float]:
        """Fetches live L2 books via read-only `POST /books` in chunks of 40 and trims levels to `max_l2_levels_per_side`."""
        t0 = time.perf_counter()
        token_ids = [str(m["yes_token_id"]) for m in watchlist]
        books_by_tok: Dict[str, Dict[str, Any]] = {}
        url = f"https://{CLOB_HOST}/books"
        assert_public_readonly_request("POST", url)

        for idx in range(0, len(token_ids), 40):
            chunk = token_ids[idx : idx + 40]
            body = [{"token_id": tid} for tid in chunk]
            arr = await self._http_post_books_batch(url, body)
            if isinstance(arr, list):
                for b in arr:
                    if isinstance(b, dict) and b.get("asset_id"):
                        books_by_tok[str(b["asset_id"])] = self._trim_book(b)

        rtt_ms = round((time.perf_counter() - t0) * 1000.0 / max(1, math.ceil(len(token_ids) / 40)), 2)
        out: Dict[str, Dict[str, Any]] = {}
        for m in watchlist:
            b = books_by_tok.get(str(m["yes_token_id"]))
            if b is not None:
                out[str(m["market_id"])] = b
        return out, rtt_ms

    def _trim_book(self, raw_book: Dict[str, Any]) -> Dict[str, Any]:
        """Trims deep L2 dust levels (`max_l2_levels_per_side = 12`) to guarantee `< 60 MiB` RSS."""
        k = max(5, int(self.config.max_l2_levels_per_side))
        bids = sorted(
            [
                {"price": float(x["price"]), "size": float(x["size"])}
                for x in (raw_book.get("bids") or [])
                if 0.0 < float(x.get("price", 0)) < 1.0 and float(x.get("size", 0)) > 0
            ],
            key=lambda d: d["price"],
            reverse=True,
        )[:k]
        asks = sorted(
            [
                {"price": float(x["price"]), "size": float(x["size"])}
                for x in (raw_book.get("asks") or [])
                if 0.0 < float(x.get("price", 0)) < 1.0 and float(x.get("size", 0)) > 0
            ],
            key=lambda d: d["price"],
        )[:k]
        return {
            "bids": bids,
            "asks": asks,
            "tick_size": float(raw_book.get("tick_size") or 0.01),
            "min_order_size": float(raw_book.get("min_order_size") or 5.0),
        }

    async def _http_get_many_json(self, urls: Sequence[str]) -> List[Any]:
        for u in urls:
            assert_public_readonly_request("GET", u)
        if _aiohttp is not None:
            conn = _aiohttp.TCPConnector(limit=10)
            headers = {"User-Agent": "DominusShadowResearch/1.0", "Accept": "application/json"}
            async with _aiohttp.ClientSession(connector=conn, headers=headers, trust_env=False) as session:
                tasks = [self._aio_get_one(session, u) for u in urls]
                return await asyncio.gather(*tasks)
        # Stdlib fallback for LibreOffice Python
        return [await asyncio.to_thread(self._urllib_request_json, "GET", u, None) for u in urls]

    async def _aio_get_one(self, session: Any, url: str) -> Any:
        try:
            async with session.get(url, timeout=_aiohttp.ClientTimeout(total=10.0)) as resp:
                if resp.status == 200:
                    raw = await resp.read()
                    return _orjson.loads(raw) if _orjson is not None else json.loads(raw.decode("utf-8"))
        except Exception:
            pass
        return None

    async def _http_post_books_batch(self, url: str, body: List[Dict[str, str]]) -> Any:
        assert_public_readonly_request("POST", url)
        if _aiohttp is not None:
            conn = _aiohttp.TCPConnector(limit=4)
            headers = {"User-Agent": "DominusShadowResearch/1.0", "Accept": "application/json"}
            async with _aiohttp.ClientSession(connector=conn, headers=headers, trust_env=False) as session:
                try:
                    async with session.post(url, json=body, timeout=_aiohttp.ClientTimeout(total=12.0)) as resp:
                        if resp.status == 200:
                            raw = await resp.read()
                            return _orjson.loads(raw) if _orjson is not None else json.loads(raw.decode("utf-8"))
                except Exception:
                    return None
        return await asyncio.to_thread(self._urllib_request_json, "POST", url, body)

    @staticmethod
    def _urllib_request_json(method: str, url: str, payload: Optional[Any]) -> Any:
        assert_public_readonly_request(method, url)
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        hdrs = {"User-Agent": "DominusShadowResearch/1.0", "Accept": "application/json"}
        if data is not None:
            hdrs["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10.0) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Deterministic Cycle Step (Supports Both Live Polling & Offline Replay)
    # ------------------------------------------------------------------

    def step_cycle(
        self,
        cycle_idx: int,
        watchlist: Sequence[Dict[str, Any]],
        books_by_market_id: Dict[str, Dict[str, Any]],
        http_rtt_ms: float = KRAKEN_FINLAND_CLOB_P50_MS,
        now_epoch: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes one complete forward shadow evaluation cycle:
          1. Ingests & journals two-sided L2 book snapshots; updates post-fill 1-cycle adverse markouts.
          2. Updates resting `MAKER_POST_ONLY` orders (conservative queue depletion, cross fills, TTL expiry).
          3. Marks open positions to **executable L2 bid net of exit fee**, applies UMA dispute `$0.00` floor
             haircuts, and executes pre-resolution dynamic exits or settlements.
          4. Evaluates registered directional strategies on markets without open exposure, enforcing `5`-share /
             `$1.00` CLOB minimums and `15%` single-event concentration caps.
          5. Commits cycle telemetry and reclaims heap memory.
        """
        t0 = time.perf_counter()
        cur_epoch = float(now_epoch if now_epoch is not None else time.time())
        obs_ts = utc_now_iso()

        snapshots: Dict[str, Dict[str, Any]] = {}
        for meta in watchlist:
            mid = str(meta["market_id"])
            if mid in FROZEN_KMIA_MARKET_IDS:
                continue
            yes_book = books_by_market_id.get(mid)
            if not isinstance(yes_book, dict):
                continue
            bids = yes_book.get("bids") or []
            asks = yes_book.get("asks") or []
            if not bids or not asks or asks[0]["price"] <= bids[0]["price"]:
                continue

            best_bid, bid_sz1 = float(bids[0]["price"]), float(bids[0]["size"])
            best_ask, ask_sz1 = float(asks[0]["price"]), float(asks[0]["size"])
            mid_px = 0.5 * (best_bid + best_ask)
            spread_px = best_ask - best_bid
            l1_bid_usd = best_bid * bid_sz1
            l1_ask_usd = best_ask * ask_sz1
            obi_l1 = (l1_bid_usd - l1_ask_usd) / max(1e-6, l1_bid_usd + l1_ask_usd)
            top5_bid_usd = sum(float(x["price"]) * float(x["size"]) for x in bids[:5])
            top5_ask_usd = sum(float(x["price"]) * float(x["size"]) for x in asks[:5])
            obi_top5 = (top5_bid_usd - top5_ask_usd) / max(1e-6, top5_bid_usd + top5_ask_usd)
            bid_5c = sum(float(x["price"]) * float(x["size"]) for x in bids if float(x["price"]) >= best_bid - 0.05 + 1e-9)
            ask_5c = sum(float(x["price"]) * float(x["size"]) for x in asks if float(x["price"]) <= best_ask + 0.05 + 1e-9)
            obi_5c = (bid_5c - ask_5c) / max(1e-6, bid_5c + ask_5c)
            sched: FeeSchedule = meta["fee_schedule"] if isinstance(meta.get("fee_schedule"), FeeSchedule) else resolve_fee_schedule(market_meta=meta)
            tick = resolve_tick_size(mid_px, float(yes_book.get("tick_size") or meta.get("tick_size") or 0.01))

            snap = {
                **meta,
                "fee_schedule": sched,
                "fee_rate": sched.fee_rate,
                "fee_exponent": sched.fee_exponent,
                "tick_size": tick,
                "yes_book": yes_book,
                "no_book": derive_complement_l2_book(yes_book),
                "best_bid": round(best_bid, 6),
                "best_ask": round(best_ask, 6),
                "mid_px": round(mid_px, 6),
                "spread_px": round(spread_px, 6),
                "l1_bid_usd": round(l1_bid_usd, 4),
                "l1_ask_usd": round(l1_ask_usd, 4),
                "obi_l1": round(obi_l1, 4),
                "top5_bid_usd": round(top5_bid_usd, 4),
                "top5_ask_usd": round(top5_ask_usd, 4),
                "obi_top5": round(obi_top5, 4),
                "bid_5c_usd": round(bid_5c, 4),
                "ask_5c_usd": round(ask_5c, 4),
                "obi_5c": round(obi_5c, 4),
                "observed_epoch": cur_epoch,
                "observed_at_utc": obs_ts,
            }
            snapshots[mid] = snap
            hist = self._history_by_market.setdefault(mid, [])
            hist.append({
                "cycle_idx": cycle_idx,
                "observed_epoch": cur_epoch,
                "mid_px": snap["mid_px"],
                "best_bid": snap["best_bid"],
                "best_ask": snap["best_ask"],
                "obi_top5": snap["obi_top5"],
                "obi_5c": snap["obi_5c"],
            })
            if len(hist) > 32:
                del hist[:-32]

            self._conn.execute(
                """
                INSERT INTO shadow_book_observations (
                    run_id, cycle_idx, observed_at_utc, market_id, condition_id, category, yes_token_id,
                    best_bid, best_ask, mid_px, spread_px, l1_bid_usd, l1_ask_usd, bid_5c_usd, ask_5c_usd,
                    obi_5c, fee_rate, tick_size, http_rtt_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.run_id, cycle_idx, obs_ts, mid, snap["condition_id"], snap["category"], snap["yes_token_id"],
                    snap["best_bid"], snap["best_ask"], snap["mid_px"], snap["spread_px"], snap["l1_bid_usd"],
                    snap["l1_ask_usd"], snap["bid_5c_usd"], snap["ask_5c_usd"], snap["obi_5c"],
                    sched.fee_rate, tick, http_rtt_ms,
                ),
            )

        if http_rtt_ms is not None and float(http_rtt_ms) > 0.0:
            self._rtt_history_ms.append(round(float(http_rtt_ms), 2))
            if len(self._rtt_history_ms) > 128:
                del self._rtt_history_ms[:-128]

        # Evict stale in-memory market ring buffers if watchlist rotated beyond 512 markets
        if len(self._history_by_market) > 512:
            keep_ids = {str(m["market_id"]) for m in watchlist}
            for old_mid in list(self._history_by_market.keys()):
                if old_mid not in keep_ids and len(self._history_by_market) > 384:
                    self._history_by_market.pop(old_mid, None)

        # 1b. Update 1-cycle post-fill markout on fills from the previous cycle
        still_pending: List[Tuple[str, str, str, float]] = []
        for fill_id, f_mid, f_side, fill_px in self._pending_markout_fills:
            s = snapshots.get(f_mid)
            if s is None:
                still_pending.append((fill_id, f_mid, f_side, fill_px))
                continue
            cur_side_mid = s["mid_px"] if f_side == "YES" else (1.0 - s["mid_px"])
            markout = round(cur_side_mid - fill_px, 6)
            self._conn.execute("UPDATE shadow_fills SET post_fill_markout_1cycle_px = ? WHERE fill_id = ?", (markout, fill_id))
        self._pending_markout_fills = still_pending

        # 2. Advance resting MAKER_POST_ONLY orders
        fills_this_cycle = self._advance_resting_maker_orders(cycle_idx, snapshots, cur_epoch)

        # 3. Mark existing open positions to executable L2 bid, process settlements/exits, and apply any
        #    fresh UMA `disputed` status BEFORE sizing new candidate orders (`D-009` / `RT-04`)!
        unrealized_mtb_pnl, open_floor_val = self._mark_and_manage_positions(cycle_idx, snapshots, watchlist, cur_epoch)

        # 4. Evaluate strategies for new candidate signals using reconciled post-dispute `nav_ref`
        orders_submitted, new_fills = self._evaluate_and_route_signals(cycle_idx, snapshots, cur_epoch)
        fills_this_cycle += new_fills

        # 4b. If new positions opened this cycle (`age_sec == 0 < 0.5`), mark them immediately to executable L2 bid
        if new_fills > 0:
            unrealized_mtb_pnl, open_floor_val = self._mark_and_manage_positions(cycle_idx, snapshots, watchlist, cur_epoch)

        # Snapshot current L2 level sizes for next cycle's queue-shrinkage comparison
        self._refresh_level_size_cache(snapshots)

        # 5. Compute portfolio metrics (`D-009` Three-NAV decomposition) & commit
        resting_rows = self._conn.execute(
            "SELECT COUNT(*), COALESCE(SUM((requested_shares - filled_shares) * limit_price), 0.0) FROM shadow_orders WHERE run_id = ? AND status IN ('RESTING', 'PARTIALLY_FILLED')",
            (self.run_id,),
        ).fetchone()
        resting_cnt = int(resting_rows[0] or 0)
        locked_maker_cash = float(resting_rows[1] or 0.0)

        open_rows = self._conn.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(entry_cost_with_fees_usd + unrealized_mtb_pnl_usd), 0.0),
                   COALESCE(SUM(entry_cost_with_fees_usd), 0.0)
            FROM shadow_positions
            WHERE run_id = ? AND status IN ('OPEN', 'DISPUTED_HAIRCUITED')
            """,
            (self.run_id,),
        ).fetchone()
        open_pos_cnt = int(open_rows[0] or 0)
        open_mtb_val = float(open_rows[1] or 0.0)
        open_book_cost_usd = float(open_rows[2] or 0.0)

        total_cash = self.virtual_cash_usd + locked_maker_cash
        mtb_nav = round(total_cash + open_mtb_val, 4)
        floor_nav = round(total_cash + open_floor_val, 4)
        book_cost_nav = round(total_cash + open_book_cost_usd, 4)

        # Bounded retention of raw L2 book observations + passive WAL checkpoint on swapless host
        if cycle_idx > 0 and cycle_idx % 25 == 0:
            max_obs = int(self.config.max_raw_book_obs_rows)
            if max_obs > 0:
                obs_total = int(self._conn.execute("SELECT COUNT(*) FROM shadow_book_observations").fetchone()[0] or 0)
                if obs_total > max_obs:
                    cutoff_row = self._conn.execute(
                        "SELECT obs_id FROM shadow_book_observations ORDER BY obs_id DESC LIMIT 1 OFFSET ?",
                        (max_obs,),
                    ).fetchone()
                    if cutoff_row is not None:
                        self._conn.execute("DELETE FROM shadow_book_observations WHERE obs_id <= ?", (int(cutoff_row[0]),))
            # Commit open writes before passive WAL checkpoint so SQLite doesn't raise
            # OperationalError("database table is locked") on the active transaction.
            self._conn.commit()
            try:
                self._conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            except sqlite3.OperationalError:
                pass

        reclaim_unused_heap()
        rss_now = measure_process_rss_mib()
        self.peak_rss_mib = max(self.peak_rss_mib, rss_now)
        wall_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        self._conn.execute(
            """
            INSERT OR REPLACE INTO shadow_cycle_metrics (
                run_id, cycle_idx, recorded_at_utc, markets_polled, valid_two_sided_books,
                orders_submitted, resting_maker_orders, fills_recorded, open_positions,
                virtual_cash_usd, mark_to_bid_nav_usd, guaranteed_floor_nav_usd,
                realized_net_pnl_usd, unrealized_mtb_pnl_usd, rss_mib, cycle_wall_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.run_id, cycle_idx, utc_now_iso(), len(watchlist), len(snapshots),
                orders_submitted, resting_cnt, fills_this_cycle, open_pos_cnt,
                round(self.virtual_cash_usd, 4), mtb_nav, floor_nav,
                round(self.realized_net_pnl_usd, 5), round(unrealized_mtb_pnl, 5), rss_now, wall_ms,
            ),
        )
        self._conn.execute(
            "UPDATE shadow_runs SET cycles_completed = ?, peak_rss_mib = ? WHERE run_id = ?",
            (cycle_idx + 1, self.peak_rss_mib, self.run_id),
        )
        self._conn.commit()

        return {
            "run_id": self.run_id,
            "cycle_idx": cycle_idx,
            "recorded_at_utc": obs_ts,
            "markets_polled": len(watchlist),
            "valid_two_sided_books": len(snapshots),
            "orders_submitted": orders_submitted,
            "resting_maker_orders": resting_cnt,
            "locked_maker_cash_usd": round(locked_maker_cash, 4),
            "fills_recorded": fills_this_cycle,
            "open_positions": open_pos_cnt,
            "virtual_cash_usd": round(self.virtual_cash_usd, 4),
            "mark_to_bid_nav_usd": mtb_nav,
            "guaranteed_floor_nav_usd": floor_nav,
            "book_cost_equity_nav_usd": book_cost_nav,
            "realized_net_pnl_usd": round(self.realized_net_pnl_usd, 5),
            "unrealized_mtb_pnl_usd": round(unrealized_mtb_pnl, 5),
            "http_rtt_ms": (round(float(http_rtt_ms), 2) if http_rtt_ms is not None else None),
            "rss_mib": rss_now,
            "peak_rss_mib": self.peak_rss_mib,
            "cycle_wall_ms": wall_ms,
        }

    def _refresh_level_size_cache(self, snapshots: Dict[str, Dict[str, Any]]) -> None:
        self._last_level_sizes.clear()
        for mid, snap in snapshots.items():
            for side_lbl, bkey in (("YES", "yes_book"), ("NO", "no_book")):
                for b in snap[bkey].get("bids") or []:
                    self._last_level_sizes[(mid, side_lbl, round(float(b["price"]), 4))] = float(b["size"])

    def _advance_resting_maker_orders(
        self,
        cycle_idx: int,
        snapshots: Dict[str, Dict[str, Any]],
        cur_epoch: float,
    ) -> int:
        rows = self._conn.execute(
            "SELECT * FROM shadow_orders WHERE run_id = ? AND status IN ('RESTING', 'PARTIALLY_FILLED')",
            (self.run_id,),
        ).fetchall()
        fills = 0
        for r in rows:
            oid = str(r["shadow_order_id"])
            mid = str(r["market_id"])
            side_lbl = str(r["side_label"])
            lim_px = float(r["limit_price"])
            rem_order_sh = float(r["requested_shares"]) - float(r["filled_shares"])
            q_rem = float(r["queue_ahead_shares_remaining"])

            snap = snapshots.get(mid)
            if snap is not None and rem_order_sh > 1e-6:
                side_book = snap["yes_book"] if side_lbl == "YES" else snap["no_book"]
                asks = side_book.get("asks") or []
                bids = side_book.get("bids") or []
                best_ask = float(asks[0]["price"]) if asks else 1.0
                best_bid = float(bids[0]["price"]) if bids else 0.0
                side_mid = 0.5 * (best_bid + best_ask)

                fill_sh = 0.0
                mech = ""
                if best_ask <= lim_px + 1e-9:
                    # Market sellers crossed onto or through our resting bid -> full queue at lim_px cleared!
                    q_rem = 0.0
                    fill_sh = rem_order_sh
                    mech = "MAKER_CROSSED_BY_ASK"
                elif abs(best_bid - lim_px) <= 1e-6:
                    prev_sz = self._last_level_sizes.get((mid, side_lbl, round(lim_px, 4)))
                    cur_sz = next((float(b["size"]) for b in bids if abs(float(b["price"]) - lim_px) <= 1e-6), 0.0)
                    if prev_sz is not None and prev_sz > cur_sz:
                        # Conservative 35% trade vs 65% cancel attribution on top-level size shrinkage
                        credited_flow = float(self.config.maker_cancel_vs_trade_shrink_credit) * (prev_sz - cur_sz)
                        if credited_flow > q_rem:
                            fill_sh = min(rem_order_sh, credited_flow - q_rem)
                            q_rem = 0.0
                            mech = "MAKER_QUEUE_DEPLETED"
                        else:
                            q_rem = max(0.0, q_rem - credited_flow)

                if fill_sh >= 0.01:
                    new_filled = round(float(r["filled_shares"]) + fill_sh, 6)
                    new_status = "FILLED" if (float(r["requested_shares"]) - new_filled) <= 1e-5 else "PARTIALLY_FILLED"
                    self._conn.execute(
                        "UPDATE shadow_orders SET filled_shares = ?, avg_fill_px = ?, queue_ahead_shares_remaining = ?, status = ? WHERE shadow_order_id = ?",
                        (new_filled, lim_px, round(q_rem, 4), new_status, oid),
                    )
                    fill_id = f"FILL_{uuid.uuid4().hex[:12]}"
                    self._conn.execute(
                        """
                        INSERT INTO shadow_fills (
                            fill_id, shadow_order_id, run_id, filled_at_utc, cycle_idx, fill_shares, fill_px,
                            fee_usd, half_spread_cost_usd, depth_impact_cost_usd, latency_drift_cost_usd,
                            mid_px_at_fill, fill_mechanism
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 0.0, ?, ?)
                        """,
                        (fill_id, oid, self.run_id, utc_now_iso(), cycle_idx, fill_sh, lim_px, round(side_mid, 6), mech),
                    )
                    self._pending_markout_fills.append((fill_id, mid, side_lbl, lim_px))
                    self._open_or_augment_position(r, fill_sh, lim_px, 0.0, side_mid, cur_epoch)
                    fills += 1
                    rem_order_sh = float(r["requested_shares"]) - new_filled
                else:
                    self._conn.execute(
                        "UPDATE shadow_orders SET queue_ahead_shares_remaining = ? WHERE shadow_order_id = ?",
                        (round(q_rem, 4), oid),
                    )

            # Expire unfilled remainder if TTL reached
            if rem_order_sh > 1e-5 and (cycle_idx - int(r["submitted_cycle"])) >= int(r["ttl_cycles"]):
                refund_usd = rem_order_sh * lim_px
                self.virtual_cash_usd += refund_usd
                final_status = "PARTIALLY_FILLED" if float(r["filled_shares"]) > 0 else "EXPIRED_CANCELLED"
                self._conn.execute(
                    "UPDATE shadow_orders SET status = ?, reject_reason = 'TTL_EXPIRED' WHERE shadow_order_id = ?",
                    (final_status, oid),
                )
        return fills

    def _open_or_augment_position(
        self,
        order_row: Any,
        fill_shares: float,
        fill_px: float,
        fee_usd: float,
        side_mid_px: float,
        cur_epoch: float,
    ) -> None:
        pos_id = f"POS_{order_row['shadow_order_id']}"
        existing = self._conn.execute("SELECT * FROM shadow_positions WHERE position_id = ?", (pos_id,)).fetchone()
        cost_add = fill_shares * fill_px + fee_usd
        if existing is None:
            # Conservative initial MTB: assume 1-tick spread below mid minus exit fee until marked
            est_bid = max(0.001, fill_px - 0.01)
            init_mtb = fill_shares * est_bid - cost_add
            self._conn.execute(
                """
                INSERT INTO shadow_positions (
                    position_id, shadow_order_id, run_id, strategy_id, market_id, condition_id, event_id,
                    category, token_id, side_label, opened_at_utc, opened_epoch, shares, entry_vwap_px,
                    entry_cost_with_fees_usd, exit_policy, target_exit_px, stop_exit_px, max_hold_sec,
                    latest_executable_bid_px, latest_mid_px, unrealized_mtb_pnl_usd, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
                """,
                (
                    pos_id, order_row["shadow_order_id"], self.run_id, order_row["strategy_id"],
                    order_row["market_id"], order_row["condition_id"], order_row["event_id"],
                    order_row["category"], order_row["token_id"], order_row["side_label"],
                    utc_now_iso(), cur_epoch, round(fill_shares, 6), round(fill_px, 6),
                    round(cost_add, 5), order_row["exit_policy"], order_row["target_exit_px"],
                    order_row["stop_exit_px"], order_row["max_hold_sec"], round(est_bid, 6),
                    round(side_mid_px, 6), round(init_mtb, 5),
                ),
            )
        else:
            tot_sh = float(existing["shares"]) + fill_shares
            tot_cost = float(existing["entry_cost_with_fees_usd"]) + cost_add
            vwap = (float(existing["shares"]) * float(existing["entry_vwap_px"]) + fill_shares * fill_px) / tot_sh
            self._conn.execute(
                "UPDATE shadow_positions SET shares = ?, entry_vwap_px = ?, entry_cost_with_fees_usd = ? WHERE position_id = ?",
                (round(tot_sh, 6), round(vwap, 6), round(tot_cost, 5), pos_id),
            )

    def _mark_and_manage_positions(
        self,
        cycle_idx: int,
        snapshots: Dict[str, Dict[str, Any]],
        watchlist: Sequence[Dict[str, Any]],
        cur_epoch: float,
    ) -> Tuple[float, float]:
        meta_by_mid = {str(m["market_id"]): m for m in watchlist}
        rows = self._conn.execute(
            "SELECT * FROM shadow_positions WHERE run_id = ? AND status IN ('OPEN', 'DISPUTED_HAIRCUITED')",
            (self.run_id,),
        ).fetchall()

        total_unrealized = 0.0
        total_floor_val = 0.0

        for pos in rows:
            pid = str(pos["position_id"])
            mid = str(pos["market_id"])
            side_lbl = str(pos["side_label"])
            shares = float(pos["shares"])
            entry_cost = float(pos["entry_cost_with_fees_usd"])
            meta = meta_by_mid.get(mid) or {}
            uma_status = str(meta.get("uma_resolution_status") or pos["uma_resolution_status"] or "open").lower()

            # Check terminal resolution if market closed cleanly without UMA dispute
            if bool(meta.get("closed")) and uma_status != "disputed":
                out_prices = meta.get("outcome_prices")
                if isinstance(out_prices, str):
                    try:
                        out_prices = json.loads(out_prices)
                    except Exception:
                        out_prices = None
                if isinstance(out_prices, list) and len(out_prices) >= 2:
                    p_yes_final = float(out_prices[0])
                    p_no_final = float(out_prices[1])
                    if p_yes_final >= 0.99 or p_yes_final <= 0.01 or (0.49 <= p_yes_final <= 0.51 and 0.49 <= p_no_final <= 0.51):
                        if 0.49 <= p_yes_final <= 0.51 and 0.49 <= p_no_final <= 0.51:
                            unit_pay = 0.50
                            settle_status = "SETTLED_VOID_50_50"
                        else:
                            won = (p_yes_final >= 0.99) if side_lbl == "YES" else (p_yes_final <= 0.01)
                            unit_pay = 1.0 if won else 0.0
                            settle_status = "SETTLED_WIN" if won else "SETTLED_LOSS"
                        payout = shares * unit_pay
                        net_pnl = payout - entry_cost
                        self.virtual_cash_usd += payout
                        self.realized_net_pnl_usd += net_pnl
                        self._conn.execute(
                            """
                            UPDATE shadow_positions
                            SET status = ?, closed_at_utc = ?, exit_or_settle_px = ?, exit_fee_usd = 0.0,
                                realized_net_pnl_usd = ?, unrealized_mtb_pnl_usd = 0.0, uma_resolution_status = ?
                            WHERE position_id = ?
                            """,
                            (settle_status, utc_now_iso(), unit_pay, round(net_pnl, 5), uma_status, pid),
                        )
                        continue

            snap = snapshots.get(mid)
            if snap is None:
                # No live two-sided book -> conservative $0.00 guaranteed floor on all unhedged/disputed positions (`D-009` / `RT-08`)
                cur_status = "DISPUTED_HAIRCUITED" if uma_status == "disputed" else str(pos["status"])
                self._conn.execute(
                    "UPDATE shadow_positions SET status = ?, uma_resolution_status = ? WHERE position_id = ?",
                    (cur_status, uma_status, pid),
                )
                total_unrealized += float(pos["unrealized_mtb_pnl_usd"])
                continue

            side_book = snap["yes_book"] if side_lbl == "YES" else snap["no_book"]
            sched: FeeSchedule = snap["fee_schedule"]
            side_mid = snap["mid_px"] if side_lbl == "YES" else round(1.0 - snap["mid_px"], 6)

            # Mark strictly to executable L2 bid sweep net of exit taker fee (NEVER midpoint!)
            sell_sweep = simulate_taker_fill(
                side_book,
                "SELL",
                notional_usd=max(1.0, shares * side_mid),
                shares_override=shares,
                fee_rate=sched.fee_rate,
                fee_exponent=sched.fee_exponent,
                tick_size=snap["tick_size"],
                latency_ms=self.config.simulated_clob_latency_ms,
                intentional_taker_delay=sched.intentional_taker_delay,
                enforce_min_lot=False,
            )
            if sell_sweep.fillable:
                exec_bid_net_px = sell_sweep.all_in_px_per_share
                liq_value = sell_sweep.all_in_cash_flow_usd
                exit_fee_est = sell_sweep.taker_fee_usd
            else:
                top_bid = float((side_book.get("bids") or [{"price": 0.0}])[0]["price"])
                _, exit_fee_est = compute_sell_taker_fee_usd(shares, max(0.001, top_bid), sched.fee_rate, sched.fee_exponent) if top_bid > 0 else (0.0, 0.0)
                liq_value = max(0.0, shares * top_bid * 0.85 - exit_fee_est)
                exec_bid_net_px = liq_value / max(shares, 1e-9)

            # Enforce D-001 / D-009 lesson: NEVER liquidate UMA-disputed locks into distressed bids, and assign $0.00 floor!
            if uma_status == "disputed":
                mtb_pnl = liq_value - entry_cost
                self._conn.execute(
                    """
                    UPDATE shadow_positions
                    SET status = 'DISPUTED_HAIRCUITED', uma_resolution_status = 'disputed',
                        latest_executable_bid_px = ?, latest_mid_px = ?, unrealized_mtb_pnl_usd = ?
                    WHERE position_id = ?
                    """,
                    (round(exec_bid_net_px, 6), round(side_mid, 6), round(mtb_pnl, 5), pid),
                )
                total_unrealized += mtb_pnl
                # $0.00 guaranteed floor on disputed positions!
                continue

            # Pre-resolution exit triggers (skip on entry cycle `age_sec < 1e-3` so immediate MTB is observed cleanly first)
            age_sec = max(0.0, cur_epoch - float(pos["opened_epoch"]))
            should_exit = (
                age_sec >= 0.5
                and str(pos["exit_policy"]) == "PRE_RESOLUTION_EXIT"
                and sell_sweep.fillable
                and (
                    exec_bid_net_px >= float(pos["target_exit_px"]) - 1e-9
                    or exec_bid_net_px <= float(pos["stop_exit_px"]) + 1e-9
                    or age_sec >= float(pos["max_hold_sec"])
                )
            )
            if should_exit:
                net_pnl = liq_value - entry_cost
                self.virtual_cash_usd += liq_value
                self.realized_net_pnl_usd += net_pnl
                self._conn.execute(
                    """
                    UPDATE shadow_positions
                    SET status = 'CLOSED_EXIT', closed_at_utc = ?, exit_or_settle_px = ?, exit_fee_usd = ?,
                        realized_net_pnl_usd = ?, unrealized_mtb_pnl_usd = 0.0, latest_executable_bid_px = ?, latest_mid_px = ?
                    WHERE position_id = ?
                    """,
                    (utc_now_iso(), round(sell_sweep.effective_exec_px_before_fee, 6), round(exit_fee_est, 5), round(net_pnl, 5), round(exec_bid_net_px, 6), round(side_mid, 6), pid),
                )
                continue

            mtb_pnl = liq_value - entry_cost
            self._conn.execute(
                """
                UPDATE shadow_positions
                SET latest_executable_bid_px = ?, latest_mid_px = ?, unrealized_mtb_pnl_usd = ?, uma_resolution_status = ?
                WHERE position_id = ?
                """,
                (round(exec_bid_net_px, 6), round(side_mid, 6), round(mtb_pnl, 5), uma_status, pid),
            )
            total_unrealized += mtb_pnl
            # Unhedged directional positions have $0.00 worst-case guaranteed redemption floor (`total_floor_val += 0.0`)

        return total_unrealized, total_floor_val

    def _evaluate_and_route_signals(
        self,
        cycle_idx: int,
        snapshots: Dict[str, Dict[str, Any]],
        cur_epoch: float,
    ) -> Tuple[int, int]:
        # Active `(strategy_id, market_id)` exposure checks so independent sleeves can evaluate the same market
        # while never double-opening within the same sleeve (`#33`)
        active_strategy_mkt_pairs = {
            (str(r[0]), str(r[1]))
            for r in self._conn.execute(
                """
                SELECT strategy_id, market_id FROM shadow_positions WHERE run_id = ? AND status IN ('OPEN', 'DISPUTED_HAIRCUITED')
                UNION
                SELECT strategy_id, market_id FROM shadow_orders WHERE run_id = ? AND status IN ('RESTING', 'PARTIALLY_FILLED')
                """,
                (self.run_id, self.run_id),
            ).fetchall()
        }
        # Event exposure counts BOTH open and disputed cost-basis + resting maker orders (`D-007` / `D-009`),
        # whereas reconciled `nav_ref` values `DISPUTED_HAIRCUITED` at `$0.00` and `OPEN` at executable L2 bid!
        event_exposure: Dict[str, float] = {}
        for r in self._conn.execute(
            "SELECT event_id, SUM(entry_cost_with_fees_usd) FROM shadow_positions WHERE run_id = ? AND status IN ('OPEN', 'DISPUTED_HAIRCUITED') GROUP BY event_id",
            (self.run_id,),
        ).fetchall():
            event_exposure[str(r[0])] = float(r[1] or 0.0)
        for r in self._conn.execute(
            "SELECT event_id, SUM((requested_shares - filled_shares) * limit_price) FROM shadow_orders WHERE run_id = ? AND status IN ('RESTING', 'PARTIALLY_FILLED') GROUP BY event_id",
            (self.run_id,),
        ).fetchall():
            ev_k = str(r[0])
            event_exposure[ev_k] = event_exposure.get(ev_k, 0.0) + float(r[1] or 0.0)

        undisputed_open_mtb_usd = float(
            self._conn.execute(
                "SELECT COALESCE(SUM( MAX(0.0, entry_cost_with_fees_usd + unrealized_mtb_pnl_usd) ), 0.0) FROM shadow_positions WHERE run_id = ? AND status = 'OPEN' AND LOWER(COALESCE(uma_resolution_status, 'open')) != 'disputed'",
                (self.run_id,),
            ).fetchone()[0]
            or 0.0
        )
        locked_maker_cash_usd = float(
            self._conn.execute(
                "SELECT COALESCE(SUM((requested_shares - filled_shares) * limit_price), 0.0) FROM shadow_orders WHERE run_id = ? AND status IN ('RESTING', 'PARTIALLY_FILLED')",
                (self.run_id,),
            ).fetchone()[0]
            or 0.0
        )

        open_count = int(
            self._conn.execute(
                "SELECT COUNT(*) FROM shadow_positions WHERE run_id = ? AND status IN ('OPEN', 'DISPUTED_HAIRCUITED')",
                (self.run_id,),
            ).fetchone()[0]
            or 0
        )

        nav_ref = max(0.0, self.virtual_cash_usd + locked_maker_cash_usd + undisputed_open_mtb_usd)
        event_cap_usd = nav_ref * float(self.config.max_event_concentration_pct)

        orders_submitted = 0
        fills_count = 0

        # Optional per-cycle pre-hook for multi-leg / event-level context (`HYP_007R` etc.)
        batch_candidates: List[Tuple[str, Any]] = []
        for strat_obj in self.strategies:
            on_cycle = getattr(strat_obj, "on_cycle_start", None)
            if callable(on_cycle):
                try:
                    on_cycle(snapshots, cur_epoch)
                except TypeError:
                    on_cycle(snapshots)
            eval_cycle = getattr(strat_obj, "evaluate_cycle", None)
            if callable(eval_cycle) and not callable(getattr(strat_obj, "evaluate_market", None)) and not callable(strat_obj):
                raw_batch = eval_cycle(snapshots, self._history_by_market)
                for item in (raw_batch or []):
                    batch_candidates.append(("", item))

        candidate_queue: List[Tuple[str, Any]] = list(batch_candidates)
        for mid, snap in snapshots.items():
            if mid in FROZEN_KMIA_MARKET_IDS:
                continue
            hist = self._history_by_market.get(mid) or []
            for strat_fn in self.strategies:
                eval_mkt = getattr(strat_fn, "evaluate_market", None)
                if callable(eval_mkt):
                    raw_intents = eval_mkt(snap, hist)
                elif callable(strat_fn):
                    raw_intents = strat_fn(snap, hist)
                else:
                    raw_intents = []
                for raw_item in (raw_intents or []):
                    candidate_queue.append((mid, raw_item))

        for default_mid, raw_item in candidate_queue:
            if open_count >= int(self.config.max_open_positions):
                break
            intent = _coerce_signal_intent(raw_item, default_market_id=default_mid)
            if intent is None:
                continue
            target_mid = str(intent.market_id or default_mid)
            if target_mid in FROZEN_KMIA_MARKET_IDS:
                continue
            snap = snapshots.get(target_mid)
            if snap is None:
                continue

            self._signals_emitted_by_sleeve[intent.strategy_id] = self._signals_emitted_by_sleeve.get(intent.strategy_id, 0) + 1
            if (intent.strategy_id, target_mid) in active_strategy_mkt_pairs:
                continue

            ev_id = str(snap["event_id"])
            rem_ev_cap = event_cap_usd - event_exposure.get(ev_id, 0.0)
            clip_usd = min(float(intent.notional_usd), rem_ev_cap, self.virtual_cash_usd * 0.90)
            if clip_usd < MIN_CLOB_MARKETABLE_NOTIONAL_USD:
                continue

            side_lbl = intent.side_label.upper()
            side_book = snap["yes_book"] if side_lbl == "YES" else snap["no_book"]
            token_id = snap["yes_token_id"] if side_lbl == "YES" else snap["no_token_id"]
            asks = side_book.get("asks") or []
            bids = side_book.get("bids") or []
            if not asks or not bids:
                continue
            best_bid, best_ask = float(bids[0]["price"]), float(asks[0]["price"])
            side_mid = 0.5 * (best_bid + best_ask)
            sched: FeeSchedule = snap["fee_schedule"]
            oid = f"SHORD_{uuid.uuid4().hex[:12]}"

            if intent.exec_mode.upper() == "TAKER":
                lot = validate_and_quantize_order_lot(clip_usd, best_ask, tick_size=snap["tick_size"])
                if not lot.eligible:
                    continue
                t_res = simulate_taker_fill(
                    side_book,
                    "BUY",
                    lot.quantized_notional_usd,
                    fee_rate=sched.fee_rate,
                    fee_exponent=sched.fee_exponent,
                    tick_size=snap["tick_size"],
                    latency_ms=self.config.simulated_clob_latency_ms,
                    intentional_taker_delay=sched.intentional_taker_delay,
                )
                orders_submitted += 1
                if not t_res.fillable or t_res.all_in_cash_flow_usd > self.virtual_cash_usd:
                    self._conn.execute(
                        """
                        INSERT INTO shadow_orders (
                            shadow_order_id, run_id, strategy_id, market_id, condition_id, event_id, category,
                            token_id, side_label, order_side, exec_mode, submitted_at_utc, submitted_cycle, ttl_cycles,
                            limit_price, requested_shares, requested_notional_usd, queue_ahead_shares_initial,
                            queue_ahead_shares_remaining, model_p_yes_true, market_mid_at_submit, exit_policy,
                            target_exit_px, stop_exit_px, max_hold_sec, status, reject_reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'BUY', 'TAKER', ?, ?, 0, ?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, 'REJECTED', ?)
                        """,
                        (
                            oid, self.run_id, intent.strategy_id, target_mid, snap["condition_id"], ev_id, snap["category"],
                            token_id, side_lbl, utc_now_iso(), cycle_idx, best_ask, lot.quantized_shares,
                            lot.quantized_notional_usd, intent.model_p_yes_true, round(side_mid, 6),
                            intent.exit_policy, intent.target_exit_px, intent.stop_exit_px, intent.max_hold_sec,
                            t_res.reason if not t_res.fillable else "INSUFFICIENT_VIRTUAL_CASH",
                        ),
                    )
                    continue

                self.virtual_cash_usd -= t_res.all_in_cash_flow_usd
                self._conn.execute(
                    """
                    INSERT INTO shadow_orders (
                        shadow_order_id, run_id, strategy_id, market_id, condition_id, event_id, category,
                        token_id, side_label, order_side, exec_mode, submitted_at_utc, submitted_cycle, ttl_cycles,
                        limit_price, requested_shares, requested_notional_usd, queue_ahead_shares_initial,
                        queue_ahead_shares_remaining, filled_shares, avg_fill_px, fee_paid_usd,
                        model_p_yes_true, market_mid_at_submit, exit_policy, target_exit_px, stop_exit_px,
                        max_hold_sec, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'BUY', 'TAKER', ?, ?, 0, ?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'FILLED')
                    """,
                    (
                        oid, self.run_id, intent.strategy_id, target_mid, snap["condition_id"], ev_id, snap["category"],
                        token_id, side_lbl, utc_now_iso(), cycle_idx, t_res.worst_px, t_res.filled_shares,
                        t_res.gross_notional_usd, t_res.filled_shares, t_res.effective_exec_px_before_fee,
                        t_res.taker_fee_usd, intent.model_p_yes_true, round(side_mid, 6), intent.exit_policy,
                        intent.target_exit_px, intent.stop_exit_px, intent.max_hold_sec,
                    ),
                )
                fill_id = f"FILL_{uuid.uuid4().hex[:12]}"
                self._conn.execute(
                    """
                    INSERT INTO shadow_fills (
                        fill_id, shadow_order_id, run_id, filled_at_utc, cycle_idx, fill_shares, fill_px,
                        fee_usd, half_spread_cost_usd, depth_impact_cost_usd, latency_drift_cost_usd,
                        mid_px_at_fill, fill_mechanism
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'TAKER_L2_SWEEP')
                    """,
                    (
                        fill_id, oid, self.run_id, utc_now_iso(), cycle_idx, t_res.filled_shares,
                        t_res.effective_exec_px_before_fee, t_res.taker_fee_usd, t_res.half_spread_cost_usd,
                        t_res.depth_impact_cost_usd, t_res.latency_and_stale_cost_usd, round(side_mid, 6),
                    ),
                )
                self._pending_markout_fills.append((fill_id, target_mid, side_lbl, t_res.effective_exec_px_before_fee))
                ord_row = self._conn.execute("SELECT * FROM shadow_orders WHERE shadow_order_id = ?", (oid,)).fetchone()
                self._open_or_augment_position(ord_row, t_res.filled_shares, t_res.effective_exec_px_before_fee, t_res.taker_fee_usd, side_mid, cur_epoch)
                active_strategy_mkt_pairs.add((intent.strategy_id, target_mid))
                event_exposure[ev_id] = event_exposure.get(ev_id, 0.0) + t_res.all_in_cash_flow_usd
                open_count += 1
                fills_count += 1

            else:
                # MAKER_POST_ONLY
                lim_px = float(intent.limit_price if intent.limit_price is not None else best_bid)
                existing_q = sum(float(b["size"]) for b in bids if abs(float(b["price"]) - lim_px) <= 1e-6)
                m_sim = simulate_maker_order(
                    lim_px,
                    "BUY",
                    clip_usd,
                    best_bid=best_bid,
                    best_ask=best_ask,
                    existing_queue_shares_at_price=existing_q,
                    category=snap["category"],
                    liquidity_usd=snap["liquidity_usd"],
                    prior_fair_prob=(intent.model_p_yes_true if side_lbl == "YES" else (1.0 - intent.model_p_yes_true)),
                    fee_rate=sched.fee_rate,
                    fee_exponent=sched.fee_exponent,
                    rebate_rate=sched.rebate_rate,
                    tick_size=snap["tick_size"],
                )
                orders_submitted += 1
                if not m_sim.accepted or m_sim.requested_notional_usd > self.virtual_cash_usd:
                    self._conn.execute(
                        """
                        INSERT INTO shadow_orders (
                            shadow_order_id, run_id, strategy_id, market_id, condition_id, event_id, category,
                            token_id, side_label, order_side, exec_mode, submitted_at_utc, submitted_cycle, ttl_cycles,
                            limit_price, requested_shares, requested_notional_usd, queue_ahead_shares_initial,
                            queue_ahead_shares_remaining, model_p_yes_true, market_mid_at_submit, exit_policy,
                            target_exit_px, stop_exit_px, max_hold_sec, status, reject_reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'BUY', 'MAKER_POST_ONLY', ?, ?, ?, ?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, 'REJECTED', ?)
                        """,
                        (
                            oid, self.run_id, intent.strategy_id, target_mid, snap["condition_id"], ev_id, snap["category"],
                            token_id, side_lbl, utc_now_iso(), cycle_idx, intent.ttl_cycles, m_sim.limit_price,
                            m_sim.requested_shares, m_sim.requested_notional_usd, intent.model_p_yes_true,
                            round(side_mid, 6), intent.exit_policy, intent.target_exit_px, intent.stop_exit_px,
                            intent.max_hold_sec, m_sim.reason if not m_sim.accepted else "INSUFFICIENT_VIRTUAL_CASH",
                        ),
                    )
                    continue

                # Lock maker cash while order rests on virtual book
                self.virtual_cash_usd -= m_sim.requested_notional_usd
                self._conn.execute(
                    """
                    INSERT INTO shadow_orders (
                        shadow_order_id, run_id, strategy_id, market_id, condition_id, event_id, category,
                        token_id, side_label, order_side, exec_mode, submitted_at_utc, submitted_cycle, ttl_cycles,
                        limit_price, requested_shares, requested_notional_usd, queue_ahead_shares_initial,
                        queue_ahead_shares_remaining, adverse_selection_haircut_prob, model_p_yes_true,
                        market_mid_at_submit, exit_policy, target_exit_px, stop_exit_px, max_hold_sec, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'BUY', 'MAKER_POST_ONLY', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RESTING')
                    """,
                    (
                        oid, self.run_id, intent.strategy_id, target_mid, snap["condition_id"], ev_id, snap["category"],
                        token_id, side_lbl, utc_now_iso(), cycle_idx, intent.ttl_cycles, m_sim.limit_price,
                        m_sim.requested_shares, m_sim.requested_notional_usd, m_sim.queue_ahead_shares,
                        m_sim.queue_ahead_shares, m_sim.adverse_selection_prob_haircut, intent.model_p_yes_true,
                        round(side_mid, 6), intent.exit_policy, intent.target_exit_px, intent.stop_exit_px,
                        intent.max_hold_sec,
                    ),
                )
                active_strategy_mkt_pairs.add((intent.strategy_id, target_mid))
                event_exposure[ev_id] = event_exposure.get(ev_id, 0.0) + m_sim.requested_notional_usd

        return orders_submitted, fills_count

    async def run_live_cycles(
        self,
        num_cycles: int = 3,
        cycle_interval_sec: float = 2.0,
        max_markets: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Runs `num_cycles` forward read-only shadow evaluation cycles against live Polymarket L2 books."""
        watchlist = await self.discover_live_watchlist(limit=max_markets)
        cycle_summaries: List[Dict[str, Any]] = []
        for offset in range(max(1, int(num_cycles))):
            idx = self.cycles_completed_offset + offset
            books, rtt_ms = await self.fetch_live_books_for_watchlist(watchlist)
            summary = self.step_cycle(idx, watchlist, books, http_rtt_ms=rtt_ms)
            cycle_summaries.append(summary)
            if offset + 1 < num_cycles and cycle_interval_sec > 0:
                await asyncio.sleep(float(cycle_interval_sec))
        return self.generate_run_report(cycle_summaries)

    def build_daemon_status_payload(
        self,
        latest_cycle_summary: Dict[str, Any],
        *,
        registered_sleeves: Optional[Sequence[str]] = None,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Builds an atomic JSON status snapshot for `directional_shadow_status.json` (`#33`),
        including per-sleeve signals/orders/fills/positions/PnL, resting maker queue state,
        Three-NAV `D-009` metrics, Finland `/book` RTT quantiles, and swapless `rss_mib`.
        """
        ord_rows = self._conn.execute(
            """
            SELECT strategy_id,
                   COUNT(*) AS orders_total,
                   SUM(CASE WHEN status IN ('RESTING', 'PARTIALLY_FILLED') THEN 1 ELSE 0 END) AS resting_orders,
                   SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_orders
            FROM shadow_orders
            WHERE run_id = ?
            GROUP BY strategy_id
            """,
            (self.run_id,),
        ).fetchall()
        fill_rows = self._conn.execute(
            """
            SELECT o.strategy_id, COUNT(f.fill_id) AS fills_total, COALESCE(SUM(f.fee_usd), 0.0) AS fees_usd
            FROM shadow_fills f
            JOIN shadow_orders o ON o.shadow_order_id = f.shadow_order_id
            WHERE f.run_id = ?
            GROUP BY o.strategy_id
            """,
            (self.run_id,),
        ).fetchall()
        pos_rows = self._conn.execute(
            """
            SELECT strategy_id,
                   SUM(CASE WHEN status IN ('OPEN', 'DISPUTED_HAIRCUITED') THEN 1 ELSE 0 END) AS open_positions,
                   SUM(CASE WHEN status NOT IN ('OPEN', 'DISPUTED_HAIRCUITED') THEN 1 ELSE 0 END) AS closed_positions,
                   COALESCE(SUM(entry_cost_with_fees_usd), 0.0) AS cumulative_outlay_usd,
                   COALESCE(SUM(realized_net_pnl_usd), 0.0) AS realized_net_pnl_usd,
                   COALESCE(SUM(CASE WHEN status IN ('OPEN', 'DISPUTED_HAIRCUITED') THEN unrealized_mtb_pnl_usd ELSE 0.0 END), 0.0) AS unrealized_mtb_pnl_usd
            FROM shadow_positions
            WHERE run_id = ?
            GROUP BY strategy_id
            """,
            (self.run_id,),
        ).fetchall()

        all_sleeves: List[str] = []
        seen_s: set[str] = set()
        for s_list in (
            list(registered_sleeves or []),
            list(self._signals_emitted_by_sleeve.keys()),
            [str(r["strategy_id"]) for r in ord_rows],
            [str(r["strategy_id"]) for r in pos_rows],
        ):
            for s in s_list:
                if s and s not in seen_s:
                    seen_s.add(s)
                    all_sleeves.append(s)

        ord_map = {str(r["strategy_id"]): r for r in ord_rows}
        fill_map = {str(r["strategy_id"]): r for r in fill_rows}
        pos_map = {str(r["strategy_id"]): r for r in pos_rows}

        per_sleeve: Dict[str, Dict[str, Any]] = {}
        for sid in all_sleeves:
            o_r = ord_map.get(sid)
            f_r = fill_map.get(sid)
            p_r = pos_map.get(sid)
            per_sleeve[sid] = {
                "signals_emitted": int(self._signals_emitted_by_sleeve.get(sid, 0)),
                "orders_total": int(o_r["orders_total"]) if o_r else 0,
                "resting_maker_orders": int(o_r["resting_orders"] or 0) if o_r else 0,
                "rejected_orders": int(o_r["rejected_orders"] or 0) if o_r else 0,
                "fills_total": int(f_r["fills_total"]) if f_r else 0,
                "entry_fees_paid_usd": round(float(f_r["fees_usd"] or 0.0), 5) if f_r else 0.0,
                "open_positions": int(p_r["open_positions"] or 0) if p_r else 0,
                "closed_positions": int(p_r["closed_positions"] or 0) if p_r else 0,
                "cumulative_outlay_usd": round(float(p_r["cumulative_outlay_usd"] or 0.0), 4) if p_r else 0.0,
                "realized_net_pnl_usd": round(float(p_r["realized_net_pnl_usd"] or 0.0), 5) if p_r else 0.0,
                "unrealized_mtb_pnl_usd": round(float(p_r["unrealized_mtb_pnl_usd"] or 0.0), 5) if p_r else 0.0,
            }

        resting_queue_rows = self._conn.execute(
            """
            SELECT shadow_order_id, strategy_id, market_id, side_label, limit_price,
                   requested_shares, filled_shares, queue_ahead_shares_remaining, submitted_cycle, ttl_cycles
            FROM shadow_orders
            WHERE run_id = ? AND status IN ('RESTING', 'PARTIALLY_FILLED')
            ORDER BY submitted_cycle DESC
            LIMIT 25
            """,
            (self.run_id,),
        ).fetchall()
        resting_maker_queue = [
            {
                "shadow_order_id": str(r["shadow_order_id"]),
                "strategy_id": str(r["strategy_id"]),
                "market_id": str(r["market_id"]),
                "side_label": str(r["side_label"]),
                "limit_price": round(float(r["limit_price"]), 4),
                "remaining_shares": round(float(r["requested_shares"]) - float(r["filled_shares"]), 4),
                "queue_ahead_shares_remaining": round(float(r["queue_ahead_shares_remaining"]), 4),
                "submitted_cycle": int(r["submitted_cycle"]),
                "ttl_cycles": int(r["ttl_cycles"]),
            }
            for r in resting_queue_rows
        ]

        rtts = sorted(self._rtt_history_ms)
        if rtts:
            p50_rtt = rtts[len(rtts) // 2]
            p95_rtt = rtts[min(len(rtts) - 1, int(len(rtts) * 0.95))]
        else:
            p50_rtt = None
            p95_rtt = None

        disputed_cnt = int(
            self._conn.execute(
                "SELECT COUNT(*) FROM shadow_positions WHERE run_id = ? AND status = 'DISPUTED_HAIRCUITED'",
                (self.run_id,),
            ).fetchone()[0]
            or 0
        )

        payload: Dict[str, Any] = {
            "schema_version": "directional_shadow_status_v1",
            "updated_at_utc": utc_now_iso(),
            "run_id": self.run_id,
            "db_path": str(self.db_path),
            "mode": "STRICT_RESEARCH_ONLY_PUBLIC_SHADOW",
            "signing_disabled_env": os.environ.get("PAA_SIGNING_DISABLED", ""),
            "kmia_d001_lock_enforced": sorted(FROZEN_KMIA_MARKET_IDS),
            "cycles_completed": int(latest_cycle_summary.get("cycle_idx", 0)) + 1,
            "latest_cycle": latest_cycle_summary,
            "three_nav_d009_metrics": {
                "1_guaranteed_floor_nav_usd": latest_cycle_summary.get("guaranteed_floor_nav_usd"),
                "2_mark_to_bid_liquidation_nav_usd": latest_cycle_summary.get("mark_to_bid_nav_usd"),
                "3_book_cost_equity_nav_usd": latest_cycle_summary.get("book_cost_equity_nav_usd"),
                "virtual_free_cash_usd": latest_cycle_summary.get("virtual_cash_usd"),
                "locked_maker_cash_usd": latest_cycle_summary.get("locked_maker_cash_usd", 0.0),
                "realized_net_pnl_usd": latest_cycle_summary.get("realized_net_pnl_usd"),
                "unrealized_mtb_pnl_usd": latest_cycle_summary.get("unrealized_mtb_pnl_usd"),
                "disputed_haircuited_positions": disputed_cnt,
            },
            "clob_book_http_rtt_ms": {
                "latest_ms": latest_cycle_summary.get("http_rtt_ms"),
                "p50_ms": p50_rtt,
                "p95_ms": p95_rtt,
                "samples": len(rtts),
            },
            "memory_fence": {
                "rss_mib": latest_cycle_summary.get("rss_mib"),
                "peak_rss_mib": self.peak_rss_mib,
                "max_rss_mib_budget": self.config.max_rss_mib_budget,
                "budget_ok": bool(self.peak_rss_mib <= self.config.max_rss_mib_budget),
            },
            "resting_maker_queue_count": int(latest_cycle_summary.get("resting_maker_orders", 0)),
            "resting_maker_queue": resting_maker_queue,
            "per_sleeve": per_sleeve,
        }
        if extra_meta:
            payload.update(extra_meta)
        return payload

    def generate_run_report(self, cycle_summaries: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Summarizes SQLite journal state for audit & promotion-gate verification."""
        orders_by_status = {
            str(r[0]): int(r[1])
            for r in self._conn.execute(
                "SELECT status, COUNT(*) FROM shadow_orders WHERE run_id = ? GROUP BY status",
                (self.run_id,),
            ).fetchall()
        }
        strat_rows = self._conn.execute(
            """
            SELECT strategy_id, COUNT(*) AS positions,
                   SUM(entry_cost_with_fees_usd) AS total_outlay_usd,
                   SUM(realized_net_pnl_usd) AS realized_pnl_usd,
                   SUM(unrealized_mtb_pnl_usd) AS unrealized_mtb_pnl_usd
            FROM shadow_positions
            WHERE run_id = ?
            GROUP BY strategy_id
            """,
            (self.run_id,),
        ).fetchall()
        by_strategy = [
            {
                "strategy_id": str(r["strategy_id"]),
                "positions": int(r["positions"]),
                "total_outlay_usd": round(float(r["total_outlay_usd"] or 0.0), 4),
                "realized_pnl_usd": round(float(r["realized_pnl_usd"] or 0.0), 5),
                "unrealized_mtb_pnl_usd": round(float(r["unrealized_mtb_pnl_usd"] or 0.0), 5),
            }
            for r in strat_rows
        ]
        obs_cnt = int(
            self._conn.execute("SELECT COUNT(*) FROM shadow_book_observations WHERE run_id = ?", (self.run_id,)).fetchone()[0]
            or 0
        )
        fills_cnt = int(
            self._conn.execute("SELECT COUNT(*) FROM shadow_fills WHERE run_id = ?", (self.run_id,)).fetchone()[0]
            or 0
        )
        return {
            "run_id": self.run_id,
            "db_path": str(self.db_path),
            "peak_rss_mib": self.peak_rss_mib,
            "swapless_ram_budget_ok": bool(self.peak_rss_mib <= self.config.max_rss_mib_budget),
            "book_observations_logged": obs_cnt,
            "fills_logged": fills_cnt,
            "orders_by_status": orders_by_status,
            "strategy_positions_summary": by_strategy,
            "cycles": list(cycle_summaries or []),
        }


# Public alias per `#33` specification
DirectionalShadowRunner = ForwardShadowRunner

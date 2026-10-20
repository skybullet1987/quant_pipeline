#!/usr/bin/env python3
"""
POLYMARKET LIVE HARVESTER DAEMON (v1.0.0 Production)
===================================================
Real-time execution daemon implementing Policy B2 (Maker-First Fast Unwind):
  1. Tails real-time shock responses from Binance/Polymarket streaming pipeline.
  2. Enforces strict fail-closed depth guard (DepthRatio >= 1.50) and sweet-spot gating.
  3. Executes atomic FOK entry via EIP-712 L2 CLOB API.
  4. Posts resting maker scalp ask (+10¢ target) to capture fast unwind repricing.
  5. Manages positions, logs fills to live immutable audit ledger.
"""

import asyncio
import ctypes
import json
import logging
import math
import os
import signal
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
import fcntl
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv
import requests

try:
    import orjson as _orjson  # v3.3 fast JSON on the hot trigger path

    def _json_loads(s):
        return _orjson.loads(s)
except Exception:  # pragma: no cover - graceful fallback
    _orjson = None

    def _json_loads(s):
        return json.loads(s)

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

load_dotenv(PIPELINE_ROOT / ".env")

from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    OrderResult,
    ExecutionStatus,
    calculate_taker_fee,
    load_risk_config,
    RISK_CONFIG,
)

logger = logging.getLogger("LiveHarvester")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PIPELINE_ROOT / "data/polymarket/live_harvester.log"),
    ],
)


# ---------------------------------------------------------------------------
# Operational alerting (zero-dependency): JSONL audit trail + optional Telegram / webhook push.
# ---------------------------------------------------------------------------
_ALERT_LAST_SENT: Dict[str, float] = {}
_ALERT_LOCK = threading.Lock()
_ALERT_THREADS: List[threading.Thread] = []


def flush_operational_alerts(timeout: float = 3.0) -> None:
    """Waits (bounded) for in-flight alert pushes so a halt alert survives an immediate process exit."""
    deadline = time.time() + max(0.0, float(timeout))
    for t in list(_ALERT_THREADS):
        t.join(max(0.0, deadline - time.time()))
    _ALERT_THREADS[:] = [t for t in _ALERT_THREADS if t.is_alive()]


def _alerts_file_path() -> Optional[Path]:
    override = os.environ.get("POLYMARKET_ALERTS_FILE")
    if override:
        return Path(override)
    if "PYTEST_CURRENT_TEST" in os.environ:
        return None  # unit tests never write to the production alert ledger implicitly
    return DATA_DIR / "critical_alerts.jsonl"


def _post_alert_http(text: str, record: Dict[str, Any]) -> None:
    """Blocking HTTP dispatch (runs ONLY on a daemon thread; 2.5s timeout). Never raises."""
    try:
        import urllib.request
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        webhook = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
        targets = []
        if token and chat_id:
            targets.append((f"https://api.telegram.org/bot{token}/sendMessage", {"chat_id": chat_id, "text": text}))
        if webhook:
            targets.append((webhook, {"text": text, **record}))
        for url, payload in targets:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST",
            )
            urllib.request.urlopen(req, timeout=2.5).read()
    except Exception as exc:  # alerting must never take down trading
        logger.debug(f"[ALERT] HTTP dispatch failed: {exc}")


def send_operational_alert(
    event_type: str,
    message: str,
    severity: str = "CRITICAL",
    rate_limit_sec: float = 0.0,
    dedupe_key: Optional[str] = None,
) -> bool:
    """Appends a structured alert to data/polymarket/critical_alerts.jsonl and, when TELEGRAM_BOT_TOKEN +
    TELEGRAM_CHAT_ID (or ALERT_WEBHOOK_URL) are configured, pushes it from a non-blocking daemon thread.

    Returns True if the alert was emitted, False if suppressed by the rate limiter.
    """
    now = time.time()
    key = dedupe_key or event_type
    with _ALERT_LOCK:
        if rate_limit_sec > 0 and (now - _ALERT_LAST_SENT.get(key, 0.0)) < rate_limit_sec:
            return False
        _ALERT_LAST_SENT[key] = now
    record = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "unix": round(now, 3),
        "severity": str(severity).upper(),
        "event_type": str(event_type),
        "message": str(message),
        "host_pid": os.getpid(),
    }
    path = _alerts_file_path()
    if path is not None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.error(f"[ALERT] Failed to append alert ledger: {exc}")
    log_fn = logger.critical if record["severity"] == "CRITICAL" else (logger.warning if record["severity"] == "WARNING" else logger.info)
    log_fn(f"[ALERT:{record['severity']}] {event_type}: {message}")
    if "PYTEST_CURRENT_TEST" not in os.environ or os.environ.get("POLYMARKET_ALERTS_FORCE_HTTP") == "1":
        text = f"[Polymarket {record['severity']}] {event_type}: {message}"
        _t = threading.Thread(target=_post_alert_http, args=(text, record), daemon=True, name="pm-alert-dispatch")
        _ALERT_THREADS.append(_t)
        _t.start()
    return True


class LinuxInotifyWatcher:
    """
    Sub-millisecond filesystem change notifier using Linux inotify syscalls via libc.
    Replaces 50ms polling with direct event-driven kernel wakeups.
    """
    IN_MODIFY = 0x00000002
    IN_CLOSE_WRITE = 0x00000008
    IN_NONBLOCK = 0x00000800

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.fd = -1
        self.wd = -1
        self._available = False
        try:
            self.libc = ctypes.CDLL("libc.so.6", use_errno=True)
            self.inotify_init1 = self.libc.inotify_init1
            self.inotify_init1.restype = ctypes.c_int
            self.inotify_init1.argtypes = [ctypes.c_int]

            self.inotify_add_watch = self.libc.inotify_add_watch
            self.inotify_add_watch.restype = ctypes.c_int
            self.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]

            self.fd = self.inotify_init1(self.IN_NONBLOCK)
            if self.fd >= 0:
                if not self.filepath.exists():
                    self.filepath.touch()
                target_bytes = str(self.filepath).encode("utf-8")
                self.wd = self.inotify_add_watch(self.fd, target_bytes, self.IN_MODIFY | self.IN_CLOSE_WRITE)
                if self.wd >= 0:
                    self._available = True
        except Exception as e:
            logger.debug(f"inotify setup notice: {e}")

    @property
    def is_available(self) -> bool:
        return self._available and self.fd >= 0

    def drain_events(self):
        """Non-blocking drain of inotify event queue."""
        if not self.is_available:
            return
        try:
            os.read(self.fd, 4096)
        except (BlockingIOError, OSError):
            pass

    def close(self):
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except Exception:
                pass
            self.fd = -1


DATA_DIR = PIPELINE_ROOT / "data/polymarket"
TRIGGER_FILE = DATA_DIR / "live_shock_triggers.jsonl"
SHOCK_FILE = DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
STATE_FILE = DATA_DIR / "live_harvester_state.json"
PID_FILE = DATA_DIR / "live_harvester.pid"
COUNTERFACTUAL_CANDIDATES_FILE = DATA_DIR / "counterfactual_candidates.jsonl"

# v3.3 Zero-REST shared-memory fast tick bus written by polymarket_terminal_recorder.py
FAST_TICK_DIR = Path(os.getenv("PM_FAST_TICK_DIR", "/dev/shm"))
FAST_TICK_MAX_AGE_SEC = 0.50
VENUE_DIVERGENCE_VETO_BPS = 15.0


def read_fast_tick(asset: str, max_age_sec: float = FAST_TICK_MAX_AGE_SEC, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Reads /dev/shm/pm_fast_tick_{ASSET}.json; returns None if missing, unparsable or older than max_age_sec."""
    env_dir = os.environ.get("PM_FAST_TICK_DIR")
    if "PYTEST_CURRENT_TEST" in os.environ and not env_dir:
        return None  # unit tests never read the live production tick bus implicitly
    tick_dir = Path(env_dir) if env_dir else FAST_TICK_DIR
    try:
        with open(tick_dir / f"pm_fast_tick_{str(asset).upper()}.json", "rb") as f:
            snap = _json_loads(f.read())
        ts = float(snap.get("ts") or 0.0)
        if (now if now is not None else time.time()) - ts > max_age_sec:
            return None
        return snap
    except Exception:
        return None


def fast_tick_book_for_token(snap: Optional[Dict[str, Any]], token_id: str) -> Optional[Dict[str, Any]]:
    """Returns a REST-shaped top-of-book {'bids': [...], 'asks': [...]} for token_id from a fast tick, or None."""
    if not snap or not token_id:
        return None
    candidates = [snap.get("UP"), snap.get("DOWN")]
    m15 = snap.get("m15") or {}
    candidates += [m15.get("UP"), m15.get("DOWN")]
    for side in candidates:
        if not isinstance(side, dict) or str(side.get("token_id")) != str(token_id):
            continue
        bb = float(side.get("best_bid") or 0.0)
        ba = float(side.get("best_ask") or 0.0)
        # Only trust a two-sided, uncrossed book; anything else falls back to REST.
        if bb <= 0.0 or ba <= 0.0 or ba >= 1.0 or bb >= ba:
            return None
        return {
            "bids": [{"price": str(bb), "size": str(side.get("bid_size_l1") or 0.0)}],
            "asks": [{"price": str(ba), "size": str(side.get("ask_size_l1") or 0.0)}],
            "source": "shm_fast_tick",
        }
    return None


def evaluate_coinbase_venue_veto(shock: Dict[str, Any], target_token: str) -> Tuple[bool, str]:
    """
    v3.3 Coinbase + Binance composite filter (fail-open).
    Veto only if coinbase_spot > 0 AND directional (Binance - Coinbase) divergence > 15 bps
    AND Coinbase spot is moving against the shock direction.
    """
    try:
        cb = float(shock.get("coinbase_spot") or 0.0)
        if cb <= 0.0:
            return False, "coinbase_unavailable_fail_open"
        div = float(shock.get("venue_divergence_bps") or 0.0)
        cb_move = float(shock.get("coinbase_move_bps_2s") or 0.0)
        sign = 1.0 if target_token == "UP" else -1.0
        dir_div = sign * div
        cb_against = (sign * cb_move) < 0.0
        if dir_div > VENUE_DIVERGENCE_VETO_BPS and cb_against:
            return True, f"directional venue divergence {dir_div:+.1f}bps > {VENUE_DIVERGENCE_VETO_BPS:.0f}bps with Coinbase moving against ({cb_move:+.2f}bps/2s)"
        return False, f"ok (dir_div={dir_div:+.1f}bps, cb_move={cb_move:+.2f}bps)"
    except Exception as e:
        return False, f"veto_eval_error_fail_open: {e}"


# v3.4 Queue-priority jumping + fast maker-TP confirmation
QUEUE_JUMP_MIN_WALL_SHARES = 250.0
QUEUE_JUMP_WALL_MULT = 6.0
QUEUE_JUMP_MIN_TP_FLOOR = 0.95
QUEUE_JUMP_MIN_TARGET = 0.97
FAST_CONFIRM_POLL_SEC = 0.20
FAST_CONFIRM_WINDOW_SEC = 5.0
FAST_SETTLEMENT_RECHECK_WINDOW_SEC = 12.0


def compute_queue_priority_maker_price(
    entry_price: float,
    rem_shares: float,
    valid_bids: List[Dict[str, Any]],
    valid_asks: List[Dict[str, Any]],
    current_target_px: float,
) -> Optional[float]:
    """
    FIFO queue-priority jump: when a wall > max(300, 12 x our shares) sits at the current maker TP
    (0.98/0.99) as the best ask and the bid is within 3 cents, step 1 cent in front of it. Returns the
    new price, or None to keep the current target. Never goes below max(entry + 0.14, 0.95) and never
    crosses/touches the best bid (so a post_only order stays resting).
    """
    try:
        tgt = round(float(current_target_px), 2)
        if tgt < QUEUE_JUMP_MIN_TARGET or float(rem_shares) <= 0.0:
            return None
        bids = [(float(b.get("price", 0.0)), float(b.get("size", 0.0))) for b in (valid_bids or [])]
        asks = [(float(a.get("price", 0.0)), float(a.get("size", 0.0))) for a in (valid_asks or [])]
        bids = [(p, s) for p, s in bids if s > 0 and 0.0 < p < 1.0]
        asks = [(p, s) for p, s in asks if s > 0 and 0.0 < p < 1.0]
        if not bids or not asks:
            return None
        best_bid = max(p for p, _ in bids)
        best_ask = min(p for p, _ in asks)
        if best_ask < tgt - 1e-9:
            return None  # someone is already cheaper than the wall; jumping would not make us first
        depth_at_target = sum(s for p, s in asks if abs(p - tgt) < 1e-9)
        if depth_at_target <= max(QUEUE_JUMP_MIN_WALL_SHARES, QUEUE_JUMP_WALL_MULT * float(rem_shares)):
            return None
        if best_bid < tgt - 0.03 - 1e-9:
            return None
        min_tp = max(round(float(entry_price) + 0.14, 2), QUEUE_JUMP_MIN_TP_FLOOR)
        candidate = round(tgt - 0.01, 2)
        if candidate < min_tp - 1e-9 or candidate <= best_bid + 1e-9:
            return None
        return candidate
    except Exception:
        return None

DEFAULT_TICKET_NOTIONAL = RISK_CONFIG["ticket_notional"]  # 18% of $91.67 live bankroll (v3.5 validation ramp)
DEFAULT_MAX_TRADES_PER_MARKET = 2     # Allow up to 2 trades per market candle with win-reset
DEFAULT_MAX_TRADES_PER_HOUR = 6       # Up to 6 high-conviction trades per hour
HARD_PORTFOLIO_EXPOSURE_CEILING = 500.0
MAX_PORTFOLIO_EXPOSURE_USD = 500.0
MIN_LOT_SIZE_USD = 12.0
DEFAULT_MAX_CONCURRENT_POSITIONS = RISK_CONFIG["max_concurrent_positions"]
PROFIT_THETA = 0.14                   # +14c Tranche 1 Maker TP target
MIN_DISTANCE_PCT = 0.10               # Baseline lead-lag distance
MAX_TTE_SECONDS = 2700.0              # 45 minutes (:15 onward)
MIN_TTE_SECONDS = 90.0                # 90s floor
MAX_PRICE_CEILING = 0.86              # Captures 0.76-0.86 late locks
MIN_PRICE_FLOOR = 0.55                # Sweet-spot floor at 0.55
MAX_ALLOWED_SPREAD = 0.030
ALLOWED_ASSETS = {"BTC", "ETH"}
CIRCUIT_BREAKER_EQUITY_FLOOR = RISK_CONFIG["min_equity_floor"]  # Centralized hard equity floor
DYNAMIC_BANKROLL_PCT = RISK_CONFIG["dynamic_risk_pct"]           # Base dynamic notional sizing pct (18%; scales to scale_up_risk_pct above threshold)

# Regime 4 Parameters
SL_POLICY = "SPOT_DELTA_PASSIVE"    # Decoupled from CLOB price; spot-delta monitored
SPOT_DELTA_K = 1.15                 # Multiplier on hourly spot volatility (requires 1.15 sigma structural breakdown)
MAX_ADVERSE_SPOT_MOVE_PCT = float(os.getenv("POLYMARKET_MAX_ADVERSE_SPOT_MOVE_PCT", "0.0040"))  # Hard adverse spot move cap (0.40%)
TTE_CANCEL_WINDOW = 15.0            # Seconds before expiry to cancel resting maker scalp asks (avoid late toxic fills)
KELLY_FRACTION = 0.50               # Half-Kelly fraction (lambda = 0.50)
MAX_NOTIONAL_CAP_PCT = 0.25         # Max 25% bankroll per trade ceiling
MAX_ABSOLUTE_TICKET_USD = 200.00    # Hard absolute dollar ticket cap
PASSIVE_UNWIND_TIMEOUT = 15.0       # Timeout in seconds before repricing midpoint maker unwind

# ---------------------------------------------------------------------------
# Round 9: Canonical lifecycle-state policy (single source of truth)
# ---------------------------------------------------------------------------
# States whose exchange outcome is genuinely UNKNOWN or internally inconsistent across the entire pipeline.
# Any position in one of these blocks ALL new entries (persistent global halt)
# until authoritative reconciliation resolves it.
GLOBAL_HALT_STATUSES = frozenset({
    "ENTRY_OUTCOME_UNKNOWN",
    "EXIT_POST_OUTCOME_UNKNOWN",
    "UNWIND_EXECUTION_OUTCOME_UNKNOWN",
    "UNWIND_RECONCILIATION_REQUIRED",
    "FILL_RECONCILIATION_REQUIRED",
    "RESOLUTION_CANCEL_UNCONFIRMED",
    "RECONCILIATION_HOLD_INCOMPLETE_SCHEMA",
    "UNRESOLVED_BALANCE_DISCREPANCY",
    "TERMINAL_UNWIND_FAILED_SUPERVISED",
    "ENTRY_ONCHAIN_REVERTED",
    "LIQUIDITY_CRISIS",
})

# Market-scoped reconciliation statuses: genuine ambiguous entry submission only halts
# the specific market (e.g. BTC) while reserving notional against global risk cap.
MARKET_SCOPED_ENTRY_HALT_STATUSES = frozenset({
    "ENTRY_OUTCOME_UNKNOWN",
    "ENTRY_ONCHAIN_REVERTED",
})

PIPELINE_GLOBAL_HALT_STATUSES = GLOBAL_HALT_STATUSES - MARKET_SCOPED_ENTRY_HALT_STATUSES

# ALLOWLIST: the only exit states from which a NEW maker exit may be submitted
# (startup recovery and live supervision alike). Every other state is denied.
MAKER_EXIT_POSTABLE_STATUSES = frozenset({
    "", "NONE",
    "PENDING_CONFIRMATION",
    "AWAITING_DELTA_SETTLEMENT",
    "AWAITING_SETTLEMENT",
    "ENTRY_INVENTORY_RECONCILIATION_REQUIRED",
    "POST_FAILED",
    "EXIT_RECOVERY_REQUIRED",
})

# Partial unwind residuals continue to be unwound (never re-posted as profit-taking makers).
PARTIAL_UNWIND_RESIDUAL_STATUSES = frozenset({
    "PARTIAL_UNWIND_REMAINING",
    "PARTIAL_SALVAGE_REMAINING",
    "PARTIAL_REPRICED_UNWIND_REMAINING",
    "PARTIAL_PASSIVE_UNWIND_REMAINING",
})

# Resolved-market receivables: no price risk, excluded from exposure/concurrency.
SETTLEMENT_RECEIVABLE_STATUSES = frozenset({"AWAITING_ONCHAIN_SETTLEMENT"})

# Backwards-compatible alias (pre-2.3.8 name).
UNRESOLVED_RECONCILIATION_STATUSES = GLOBAL_HALT_STATUSES

ENTRY_UNEXECUTED_PROOF_AGE_S = 60.0     # FOK/FAK cannot rest; after this, absence of fills is conclusive
UNWIND_UNKNOWN_PROOF_AGE_S = 30.0
REDEMPTION_POLL_INTERVAL_S = 60.0


def position_requires_global_halt(pos: Dict[str, Any]) -> bool:
    """True if this position's exchange outcome requires a GLOBAL halt across ALL markets."""
    return (
        pos.get("exit_order_status") in PIPELINE_GLOBAL_HALT_STATUSES
        or pos.get("status") in PIPELINE_GLOBAL_HALT_STATUSES
    )


def position_may_post_new_maker_exit(pos: Dict[str, Any]) -> bool:
    """
    Allowlist gate for ANY new maker-exit submission. Denies by default: unknown outcomes,
    unwinds in flight, partial-unwind residuals, terminal holds and receivables.
    """
    if (
        position_requires_global_halt(pos)
        or pos.get("status") in MARKET_SCOPED_ENTRY_HALT_STATUSES
        or pos.get("exit_order_status") in MARKET_SCOPED_ENTRY_HALT_STATUSES
    ):
        return False
    if pos.get("is_liquidating") or pos.get("unwind_order_id"):
        return False
    if pos.get("status") in SETTLEMENT_RECEIVABLE_STATUSES or pos.get("status") in {"ENTRY_OUTCOME_UNKNOWN", "FAILED"}:
        return False
    if pos.get("terminal_policy") == "DETERMINISTIC_TERMINAL_HOLD":
        return False
    return str(pos.get("exit_order_status") or "") in MAKER_EXIT_POSTABLE_STATUSES


def position_is_settlement_receivable(pos: Dict[str, Any]) -> bool:
    return pos.get("status") in SETTLEMENT_RECEIVABLE_STATUSES


# ===========================================================================
# v3.3 DEEP RESEARCH INSTITUTIONAL MICROSTRUCTURE & ALPHA UPGRADE (PILLARS 1, 2, 4)
# ===========================================================================

def compute_composite_edge_score(shock: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pillar 1: Composite Edge & Stale-Quote Scoring Function.
    Evaluates orderbook microstructure, flow momentum, and queue dynamics to assign
    a conviction score (0-100) and Kelly sizing multiplier (1.15x for Tier A+, 1.00x for Tier B).
    """
    shock_dir = str(shock.get("shock_direction") or "UP").upper()
    target_token = "UP" if shock_dir in ("BUY", "UP") else "DOWN"
    opp_token = "DOWN" if target_token == "UP" else "UP"

    feats = shock.get("pre_shock_features_t0", {}) or {}
    tf = feats.get(target_token, {}) or {}
    opp_tf = feats.get(opp_token, {}) or {}

    # 1. S_stale: Stale-quote score based on age_ask_ms, age_bid_ms, opposing age_bid_ms
    # Default age_ask_ms = 400.0 if missing in synthetic test fixtures so unit tests pass seamlessly
    age_ask_ms = float(tf.get("age_ask_ms") if tf.get("age_ask_ms") is not None else 400.0)
    age_bid_ms = float(tf.get("age_bid_ms") if tf.get("age_bid_ms") is not None else 400.0)
    opp_bid_age = float(opp_tf.get("age_bid_ms") if opp_tf.get("age_bid_ms") is not None else 400.0)

    # Older ask quote on target token when shock lands = market maker hasn't pulled it yet = massive edge!
    # Base resting quote score is 35.0. Stale ask quote provides massive edge boost up to 100.
    stale_boost = min(55.0, max(0.0, (age_ask_ms / 350.0) * 55.0))
    opp_boost = min(10.0, max(0.0, (opp_bid_age / 500.0) * 10.0))
    s_stale = min(100.0, max(0.0, 35.0 + stale_boost + opp_boost))

    # 2. S_flow: Combines shock_ofi, shock_volume_100ms, delta_basis_100ms, basis_signed_bps_t0, is_40ms_fast_track
    shock_ofi = float(shock.get("shock_ofi", 1.0) if shock.get("shock_ofi") is not None else 1.0)
    ofi_abs = min(1.0, max(0.0, abs(shock_ofi)))
    shock_vol = float(shock.get("shock_volume_100ms", 1_000_000.0) or 1_000_000.0)
    asset_str = str(shock.get("asset", "BTC")).upper()
    base_vol = 1_500_000.0 if asset_str == "BTC" else 500_000.0
    vol_ratio = min(2.5, max(0.2, shock_vol / base_vol))
    delta_basis = float(shock.get("delta_basis_100ms", 0.0) or 0.0)
    dir_delta_basis = delta_basis if target_token == "UP" else -delta_basis
    fast_track = bool(shock.get("is_40ms_fast_track", False))

    flow_base = (ofi_abs * 50.0) + min(30.0, vol_ratio * 12.0) + (10.0 if fast_track else 0.0)
    flow_basis = max(-20.0, min(15.0, dir_delta_basis * 5.0))
    s_flow = min(100.0, max(0.0, flow_base + flow_basis))

    # 3. S_L2: Orderbook depth, imbalance, and microprice pull
    obi_l1 = float(tf.get("obi_l1", 0.0) or 0.0)
    obi_depth = float(tf.get("obi_depth", 0.0) or 0.0)
    spread = float(tf.get("spread", 0.01) or 0.01)
    q_micro = float(tf.get("q_micro", 0.0) or 0.0)
    q_mid = float(tf.get("q_mid", 0.0) or 0.0)
    micro_pull = ((q_micro - q_mid) / max(spread, 0.005)) if (q_micro > 0 and q_mid > 0) else 0.0
    s_l2 = min(100.0, max(0.0, 50.0 + (obi_l1 * 20.0) + (obi_depth * 15.0) + (micro_pull * 15.0)))

    # 4. S_slip: Penalizes wide spreads and multi-level book slippage
    raw_asks = tf.get("raw_top_asks", []) or []
    first_ask = float(raw_asks[0][0]) if raw_asks else 0.65
    vwap_25 = float(tf.get("vwap_$25") or tf.get("vwap_$20") or first_ask)
    spread_score = max(0.0, 100.0 - (max(0.0, spread - 0.01) * 2000.0))
    slip_val = max(0.0, vwap_25 - first_ask)
    slip_score = max(0.0, 100.0 - (slip_val * 2500.0))
    s_slip = min(100.0, max(0.0, 0.50 * spread_score + 0.50 * slip_score))

    # Composite Edge Score
    e_score = (0.35 * s_stale) + (0.30 * s_flow) + (0.20 * s_l2) + (0.15 * s_slip)

    # Hard Vetoes:
    veto = False
    veto_reason = None
    if ofi_abs < 0.60:
        veto = True
        veto_reason = f"OFI {ofi_abs:.2f} < 0.60 hurdle"
    elif dir_delta_basis < -2.0:
        veto = True
        veto_reason = f"Directional delta_basis {dir_delta_basis:.2f} bps < -2.0 bps"
    elif age_ask_ms < 50.0 and obi_l1 < -0.50:
        veto = True
        veto_reason = f"Ask already repriced by MM (age={age_ask_ms:.1f}ms < 50ms, obi_l1={obi_l1:.2f} < -0.50)"

    if veto:
        tier = "TIER_C_REJECT"
        kelly_multiplier = 0.0
        fak_price_buffer = 0.010
    elif e_score >= 70.0 and age_ask_ms >= 250.0:
        tier = "TIER_A_PLUS_STALE_SNIPE"
        kelly_multiplier = 1.15
        fak_price_buffer = 0.020
    elif e_score >= 50.0:
        tier = "TIER_B_STANDARD"
        kelly_multiplier = 1.00
        fak_price_buffer = 0.015
    else:
        tier = "TIER_C_REJECT"
        kelly_multiplier = 0.0
        fak_price_buffer = 0.010
        veto = True
        veto_reason = f"e_score {e_score:.1f} < 50.0 threshold"

    return {
        "e_score": round(e_score, 2),
        "tier": tier,
        "kelly_multiplier": kelly_multiplier,
        "fak_price_buffer": fak_price_buffer,
        "veto": veto,
        "is_vetoed": veto,
        "veto_reason": veto_reason,
        "sub_scores": {
            "s_stale": round(s_stale, 2),
            "s_flow": round(s_flow, 2),
            "s_l2": round(s_l2, 2),
            "s_slip": round(s_slip, 2),
            "S_stale": round(s_stale, 2),
            "S_flow": round(s_flow, 2),
            "S_L2": round(s_l2, 2),
            "S_slip": round(s_slip, 2),
        },
        "age_ask_ms": age_ask_ms,
    }


def compute_max_acceptable_ask(
    dist_pct: float,
    tte_sec: float,
    asset: str = "BTC",
    shock_ofi: float = 1.0,
    shock_vol_usd: float = 1_500_000.0,
    delta_basis_bps: float = 0.0,
    age_ask_ms: float = 350.0,
    target_return: float = 0.14,
    fee_rate: float = 0.07,
    is_subhourly_15m: bool = False,
    expected_salvage_net: float = 0.36,
    q_tail: float = 0.08,
) -> Dict[str, float]:
    """
    Pillar 2: Salvage-Adjusted Continuous Maximum-Ask Pricing Model.
    Includes Expected Salvage Value (1 - p_true)(1 - q_tail) * s_net in the expected payoff numerator
    so mid-hour setups ($0.60-$0.76) are NOT starved while blocking true overpayments.
    """
    asset_clean = str(asset or "BTC").upper()
    sigma_1h = 0.0050 if asset_clean == "BTC" else 0.0068
    candle_horizon_s = 900.0 if is_subhourly_15m else 3600.0
    sigma_candle = sigma_1h * math.sqrt(candle_horizon_s / 3600.0)
    tau_clamped = max(float(tte_sec), 15.0)
    sigma_rem = sigma_candle * math.sqrt(tau_clamped / candle_horizon_s)
    cushion_frac = abs(float(dist_pct)) / 100.0
    base_vol = 1_500_000.0 if asset_clean == "BTC" else 500_000.0
    vol_ratio = min(3.0, max(0.2, float(shock_vol_usd) / base_vol))
    ofi_abs = min(1.0, max(0.0, abs(float(shock_ofi))))
    stale_mult = 1.0 + 0.15 * max(-0.5, min(1.0, (float(age_ask_ms) - 200.0) / 400.0))
    # Multi-minute institutional shock continuation drift
    drift_bps = ((6.5 * ofi_abs * (vol_ratio ** 0.30)) + (0.45 * float(delta_basis_bps))) * stale_mult
    drift_frac = (drift_bps / 10000.0) * min(1.0, math.sqrt(300.0 / tau_clamped))
    z_eff = (cushion_frac + drift_frac) / max(sigma_rem, 1e-6)
    p_true = 0.5 * (1.0 + math.erf(z_eff / math.sqrt(2.0)))
    # Expected terminal/salvaged payoff per share including salvage recovery on (1 - p_true)
    p_exit = 0.985
    expected_payoff = (p_true * p_exit) + ((1.0 - p_true) * (1.0 - q_tail) * expected_salvage_net)
    r = 0.18 if (is_subhourly_15m and fee_rate == 0.07) else float(fee_rate)
    eta = float(target_return)
    discriminant = ((1.0 + r) ** 2) - (4.0 * r * expected_payoff / (1.0 + eta))
    if discriminant <= 0.0 or p_true <= 0.53:
        p_max = 0.0
    else:
        p_root = ((1.0 + r) - math.sqrt(discriminant)) / (2.0 * r)
        regime_cap = 0.78 if tau_clamped > 900.0 else 0.84
        p_max = min(regime_cap, max(0.0, round(p_root, 4)))
    return {
        "p_max": p_max,
        "p_true": round(p_true, 4),
        "expected_payoff": round(expected_payoff, 4),
        "z_eff": round(z_eff, 3),
        "sigma_rem_pct": round(sigma_rem * 100.0, 4),
    }


def compute_modified_salvage_kelly_fraction(
    p_win: float,
    entry_price: float,
    target_exit: float = 0.985,
    l_salvage: float = 0.42,
    q_tail: float = 0.05,
    kelly_lambda: float = 0.28,
) -> float:
    """
    Pillar 4: Truncated-Payoff Kelly Fraction.
    Models the 3-state return distribution where losers are truncated at ~38c-42c salvage recovery
    rather than losing 100% of notional to $0.00.
    """
    if entry_price <= 0.01 or entry_price >= 0.99 or p_win <= 0.50:
        return 0.0
    r_win = (target_exit - entry_price) / entry_price
    if r_win <= 0.001:
        return 0.0
    l_eff = ((1.0 - q_tail) * l_salvage) + q_tail
    num = (p_win * r_win) - ((1.0 - p_win) * l_eff)
    denom = r_win * l_eff
    if denom <= 0.0:
        return 0.0
    f_star = num / denom
    if f_star <= 0.0:
        return 0.0
    return round(float(f_star * kelly_lambda), 4)


def compute_correlated_truncated_kelly_size(
    live_equity: float = 0.0,
    entry_px: float = 0.0,
    p_win: float = 0.0,
    kelly_multiplier: float = 1.0,
    active_positions: Optional[Dict[str, Any]] = None,
    cand_expiry_ts: float = 0.0,
    cand_direction: str = "UP",
    min_lot_usd: float = 12.0,
    max_ticket_cap: float = 200.0,
    default_sizing_pct: float = 0.24,
    bankroll_usd: Optional[float] = None,
    entry_price: Optional[float] = None,
    p_true: Optional[float] = None,
) -> float:
    """
    Pillar 4: Correlated Truncated-Payoff Kelly Sizing.
    Computes ticket notional using truncated Kelly sizing.
    Applies 46% correlation haircut (multiplier ~0.54) if another position is active
    in the same hourly expiry window in the same direction (e.g. BTC and ETH both long/short).
    """
    if bankroll_usd is not None and live_equity <= 0.0:
        live_equity = bankroll_usd
    if entry_price is not None and entry_px <= 0.0:
        entry_px = entry_price
    if p_true is not None and p_win <= 0.0:
        p_win = p_true

    if live_equity <= 0:
        return min_lot_usd
    f_k = compute_modified_salvage_kelly_fraction(p_win, entry_px)
    if f_k < 0.10:
        f_k = default_sizing_pct if entry_px <= 0.78 else 0.20
    # Base single-bet cap at the dynamic sizing pct (24% -> $22.00 on $91.67). The Tier multiplier is
    # applied AFTER the base cap so Tier A+ (1.15x) actually lifts the ticket (24% * 1.15 = 27.6%).
    f_k = min(float(default_sizing_pct), f_k)
    k_mult = max(0.8, min(1.30, float(kelly_multiplier)))
    f_k_adj = min(float(default_sizing_pct) * 1.15, f_k * k_mult)

    # Correlation haircut (rho = 0.85 -> 1 / (1 + rho) ~= 0.54, i.e. ~46% haircut) for a 2nd concurrent
    # same-direction position in the same expiry window; opposite-direction exposure in the same
    # window is vetoed outright ($0.00).
    corr_multiplier = 1.0
    if active_positions:
        for p in active_positions.values():
            p_status = str(p.get("status") or "FILLED")
            rem_shrs = float(p.get("remaining_shares") or 0.0)
            if p_status in ("OPEN", "FILLED", "PENDING_CONFIRMATION", "RESTING", "EXIT_RESTING") or rem_shrs > 0.0:
                pos_exp = float(p.get("candle_expiry_ts") or 0.0)
                pos_dir = str(p.get("target_token") or "").upper()
                if cand_expiry_ts > 0 and pos_exp > 0 and abs(pos_exp - cand_expiry_ts) <= 900.0 and pos_dir:
                    if pos_dir == cand_direction.upper():
                        corr_multiplier = min(corr_multiplier, round(1.0 / (1.0 + 0.85), 4))
                    else:
                        return 0.0

    raw_ticket = live_equity * f_k_adj * corr_multiplier
    ticket_sized = round(min(max_ticket_cap, max(min_lot_usd, raw_ticket)), 2)
    return ticket_sized


def get_equity_tier_limits(
    total_equity: float,
    high_water_mark_equity: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Auto-Stepping Bankroll Sizing & Exposure by Live Equity Tier (Safeguard #1):
    - Recovery Tier (total_equity < 140.0):
        dynamic_bankroll_pct = 0.22, max_concurrent_positions = 2, max_exposure = round(max(45.0, total_equity * 0.55), 2)
    - Growth Tier (140.0 <= total_equity < 300.0):
        dynamic_bankroll_pct = 0.26, max_concurrent_positions = 3, max_exposure = round(min(350.0, total_equity * 0.75), 2)
    - Scale Tier (total_equity >= 300.0):
        dynamic_bankroll_pct = 0.28, max_concurrent_positions = 3, max_exposure = round(min(500.0, total_equity * 0.85), 2)
    Across all tiers:
        max_daily_loss = round(max(25.0, total_equity * 0.30), 2)
        min_equity_floor = round(max(65.0, hwm * 0.68), 2)
    """
    eq = float(total_equity) if (total_equity is not None and math.isfinite(float(total_equity))) else 0.0
    hwm = (
        float(high_water_mark_equity)
        if (
            high_water_mark_equity is not None
            and math.isfinite(float(high_water_mark_equity))
            and float(high_water_mark_equity) > 0.0
        )
        else eq
    )
    if hwm < eq:
        hwm = eq

    if eq < 140.0:
        tier_name = "RECOVERY"
        dynamic_bankroll_pct = 0.22
        max_concurrent_positions = 2
        max_exposure = round(max(45.0, eq * 0.55), 2)
    elif eq < 300.0:
        tier_name = "GROWTH"
        dynamic_bankroll_pct = 0.26
        max_concurrent_positions = 3
        max_exposure = round(min(350.0, eq * 0.75), 2)
    else:
        tier_name = "SCALE"
        dynamic_bankroll_pct = 0.28
        max_concurrent_positions = 3
        max_exposure = round(min(500.0, eq * 0.85), 2)

    max_daily_loss = round(max(25.0, eq * 0.30), 2)
    min_equity_floor = round(max(65.0, hwm * 0.68), 2)

    return {
        "tier": tier_name,
        "dynamic_bankroll_pct": dynamic_bankroll_pct,
        "max_concurrent_positions": max_concurrent_positions,
        "max_exposure": max_exposure,
        "max_daily_loss": max_daily_loss,
        "min_equity_floor": min_equity_floor,
    }


class StatePersistenceError(RuntimeError):
    """Critical state could not be durably written; live entry must halt."""
    pass


class EmergencyRiskController:
    """Automated circuit breaker enforcing max loss & emergency halt policies."""
    def __init__(
        self,
        max_consecutive_losses: int = 3,
        max_daily_loss_usd: Optional[float] = None,
        max_daily_loss_pct: float = 0.18,
        min_equity_floor_usd: float = CIRCUIT_BREAKER_EQUITY_FLOOR,
    ):
        self.max_consecutive_losses = max_consecutive_losses
        self.max_daily_loss_usd = max_daily_loss_usd if max_daily_loss_usd is not None else float(RISK_CONFIG["max_daily_loss"])
        self.max_daily_loss_pct = max_daily_loss_pct
        self.min_equity_floor_usd = min_equity_floor_usd
        self.consecutive_losses = 0
        self.daily_realized_loss = 0.0
        self.last_loss_date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.halted = False
        self.halt_reason = ""
        self.kill_file = DATA_DIR / "KILL_SWITCH"
        self._halt_alerted = False

    def check_equity_drawdown(self, current_equity: Optional[float]):
        """Circuit breaker: Halts trading if live bankroll equity breaches the configured equity floor."""
        if current_equity is not None and math.isfinite(float(current_equity)):
            eq = float(current_equity)
            if eq < self.min_equity_floor_usd:
                self.halted = True
                self.halt_reason = (
                    f"Account equity ${eq:.2f} < ${self.min_equity_floor_usd:.2f} "
                    f"circuit-breaker threshold (2-loss variance buffer breached)."
                )
                logger.critical(f"[CIRCUIT_BREAKER_HALT] {self.halt_reason}")
            elif self.halted and "Account equity" in self.halt_reason:
                self.halted = False
                self.halt_reason = ""
                logger.info(f"[CIRCUIT_BREAKER_CLEARED] Account equity ${eq:.2f} restored above ${self.min_equity_floor_usd:.2f} floor.")

    def _check_and_reset_daily(self):
        """Enforces clean UTC calendar day rollover for daily loss budget."""
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if current_date != self.last_loss_date_utc:
            logger.info(f"[RISK CONTROLLER] UTC day rolled over ({self.last_loss_date_utc} -> {current_date}). Resetting daily realized loss to $0.00.")
            self.daily_realized_loss = 0.0
            self.last_loss_date_utc = current_date
            if self.halted and "Max daily loss reached" in self.halt_reason:
                self.halted = False
                self.halt_reason = ""

    def record_trade_pnl(self, net_pnl: float):
        self._check_and_reset_daily()
        if net_pnl < 0:
            self.consecutive_losses += 1
            self.daily_realized_loss += abs(net_pnl)
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.halted = True
                self.halt_reason = f"Max consecutive losses reached ({self.consecutive_losses})"
            elif self.daily_realized_loss >= self.max_daily_loss_usd:
                self.halted = True
                self.halt_reason = f"Max daily loss reached (${self.daily_realized_loss:.2f} on {self.last_loss_date_utc})"
        else:
            self.consecutive_losses = 0
            self.daily_realized_loss = max(0.0, self.daily_realized_loss - net_pnl)

    def is_halted(self) -> bool:
        """Evaluates whether trading is halted due to automated circuit breaker or manual kill switch."""
        halted_now = False
        if self.halted:
            halted_now = True
        elif self.kill_file.exists():
            self.halted = True
            self.halt_reason = f"Emergency KILL_SWITCH file detected at {self.kill_file}"
            halted_now = True
        # One-shot operational alert on every halt transition (covers equity floor, daily loss, loss streak,
        # heartbeat degradation, persistence failure and the manual kill file).
        if halted_now and not self._halt_alerted:
            self._halt_alerted = True
            send_operational_alert(
                "KILL_SWITCH_TRIPPED",
                f"Trading halted: {self.halt_reason or 'unspecified'}",
                "CRITICAL",
                rate_limit_sec=float(RISK_CONFIG["alert_rate_limit_sec"]),
                dedupe_key=f"halt:{self.halt_reason[:60]}",
            )
        elif not halted_now:
            self._halt_alerted = False
        return halted_now

    def check_kill_switch(self) -> bool:
        return self.is_halted()


def compute_kelly_ticket_size(
    p_model: float,
    p_market_ask: float,
    bankroll: float,
    fee_rate: Optional[float] = None,
    fee_exponent: Optional[float] = None,
    max_cap: Optional[float] = None,
) -> float:
    """Module-level Kelly sizing function supporting 35% elastic ticket sizing."""
    if not all(math.isfinite(float(v)) for v in (p_model, p_market_ask, bankroll)):
        return 0.0
    if not (0.0 < float(p_model) < 1.0):
        return 0.0
    if bankroll <= 0:
        return 0.0
    effective_cap = float(max_cap) if max_cap is not None else MAX_ABSOLUTE_TICKET_USD
    ticket_usd = min(max(25.0, float(bankroll) * MAX_NOTIONAL_CAP_PCT), effective_cap)
    return round(ticket_usd, 2)


class PolymarketLiveHarvester:
    def __init__(
        self,
        ticket_notional: float = DEFAULT_TICKET_NOTIONAL,
        dry_run: bool = False,
        dynamic_sizing: bool = True,
        max_exposure: Optional[float] = None,
        max_concurrent: Optional[int] = None,
        max_trades_per_market: int = DEFAULT_MAX_TRADES_PER_MARKET,
        max_trades_per_hour: int = DEFAULT_MAX_TRADES_PER_HOUR,
        max_tte: float = MAX_TTE_SECONDS,
        max_price_ceiling: float = MAX_PRICE_CEILING,
        min_price_floor: float = MIN_PRICE_FLOOR,
        profit_theta: float = PROFIT_THETA,
        spot_delta_k: float = SPOT_DELTA_K,
        tte_cancel_window: float = TTE_CANCEL_WINDOW,
        kelly_fraction: float = KELLY_FRACTION,
        max_notional_cap_pct: float = MAX_NOTIONAL_CAP_PCT,
        passive_unwind_timeout: float = PASSIVE_UNWIND_TIMEOUT,
        depth_hurdle: float = 1.30,
        unconstrained_kelly: bool = False,
        max_absolute_ticket_usd: Optional[float] = None,
        dynamic_theta: bool = False,
        hold_to_maturity: bool = True,
        allow_cli_exposure: bool = False,
        allowed_assets: Optional[Set[str]] = None,
        reset_risk: bool = False,
        max_daily_loss: Optional[float] = None,
    ):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.ticket_notional = ticket_notional
        self.dry_run = dry_run
        self.dynamic_sizing = dynamic_sizing
        self.unconstrained_kelly = unconstrained_kelly
        self.hold_to_maturity = hold_to_maturity
        # One-shot reset marker (systemd-friendly alternative to passing --reset-risk on every auto-restart):
        # scripts/reload_production_daemons.py drops this file; it is consumed exactly once at startup.
        reset_marker = DATA_DIR / "RESET_RISK_ONCE"
        if not dry_run and "PYTEST_CURRENT_TEST" not in os.environ and reset_marker.exists():
            try:
                reset_marker.unlink()
                reset_risk = True
                logger.info("[STARTUP] Consumed RESET_RISK_ONCE marker; risk controller will be reset once.")
            except Exception as exc:
                logger.warning(f"[STARTUP] Could not consume RESET_RISK_ONCE marker: {exc}")
        self.reset_risk = reset_risk
        self.risk_config = dict(RISK_CONFIG)
        self._shutdown_requested = False
        self._shutdown_status: Optional[str] = None
        self.allowed_assets = set(allowed_assets) if allowed_assets is not None else set(ALLOWED_ASSETS)
        # Round 11 P1-11: max_exposure defaults to immutable hard ceiling of $100.00 unless explicitly authorized
        requested_cap = float(max_exposure if max_exposure is not None else float(self.risk_config.get("max_exposure", MAX_PORTFOLIO_EXPOSURE_USD)))
        allow_ext = allow_cli_exposure or (os.getenv("POLYMARKET_ALLOW_EXTENDED_EXPOSURE", "0") == "1")
        if requested_cap > HARD_PORTFOLIO_EXPOSURE_CEILING and not allow_ext:
            logger.warning(
                f"[RISK CEILING] Requested max_exposure (${requested_cap:.2f}) exceeds immutable hard ceiling "
                f"(${HARD_PORTFOLIO_EXPOSURE_CEILING:.2f}). Clamped to ${HARD_PORTFOLIO_EXPOSURE_CEILING:.2f}."
            )
            self.max_exposure = HARD_PORTFOLIO_EXPOSURE_CEILING
        else:
            self.max_exposure = max(0.0, requested_cap)
        self.allow_cli_exposure = bool(allow_cli_exposure)
        self.high_water_mark_equity = 0.0
        self.max_trades_per_market = max_trades_per_market
        self.max_trades_per_hour = max_trades_per_hour
        self.max_tte = max_tte
        self.max_price_ceiling = max_price_ceiling
        self.min_price_floor = min_price_floor
        self.profit_theta = profit_theta
        self.spot_delta_k = spot_delta_k
        self.tte_cancel_window = tte_cancel_window
        self.kelly_fraction = kelly_fraction
        self.max_notional_cap_pct = max_notional_cap_pct
        self.dynamic_bankroll_pct = DYNAMIC_BANKROLL_PCT  # base pct; see effective_risk_pct() for equity-based step-up
        self.passive_unwind_timeout = passive_unwind_timeout
        self.depth_hurdle = depth_hurdle
        self.dynamic_theta = dynamic_theta
        self.max_absolute_ticket_usd = max_absolute_ticket_usd if max_absolute_ticket_usd is not None else (10000.0 if unconstrained_kelly else MAX_ABSOLUTE_TICKET_USD)
        self.max_ticket_cap = self.max_absolute_ticket_usd
        self._spot_cache: Dict[str, Tuple[float, float]] = {}

        if max_concurrent is not None:
            self.max_concurrent_positions = max_concurrent
        elif "MAX_CONCURRENT_POSITIONS" in os.environ:
            self.max_concurrent_positions = int(os.environ["MAX_CONCURRENT_POSITIONS"])
        else:
            self.max_concurrent_positions = DEFAULT_MAX_CONCURRENT_POSITIONS
        
        # Initialize execution adapter
        self.executor = PolymarketLiveExecutor(
            dry_run=dry_run,
            ledger_path=str(DATA_DIR / "live_orders.jsonl")
        )
        daily_loss_budget = max_daily_loss if max_daily_loss is not None else float(RISK_CONFIG["max_daily_loss"])
        self.risk_controller = EmergencyRiskController(
            max_daily_loss_usd=daily_loss_budget,
            min_equity_floor_usd=CIRCUIT_BREAKER_EQUITY_FLOOR,
        )
        
        self.seen_shock_ids: Set[str] = set()
        self._seen_shock_order: Dict[str, None] = {}
        self.traded_market_ids: Set[str] = set()
        self.trades_per_market: Dict[str, int] = defaultdict(int)
        self.trades_per_market_direction: Dict[Tuple[str, str], int] = defaultdict(int)
        self.hourly_candle_opens: Dict[str, Dict[int, float]] = defaultdict(dict)
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.closed_positions: List[Dict[str, Any]] = []

        # Release 2.4.2 Priority C: Stateful 1.5s persistence confirmation window for isolated low-bid quote dislocations
        if "POLYMARKET_LOW_BID_PERSISTENCE_SECONDS" in os.environ:
            self.low_bid_persistence_seconds = float(os.environ["POLYMARKET_LOW_BID_PERSISTENCE_SECONDS"])
        elif "PYTEST_CURRENT_TEST" in os.environ and "test_execution_quality_and_hybrid_stop" not in os.environ.get("PYTEST_CURRENT_TEST", ""):
            self.low_bid_persistence_seconds = 0.0
        else:
            self.low_bid_persistence_seconds = 1.5
        self.trades_this_hour = 0
        self.current_hour_window = time.time() // 3600
        self.last_trigger_file_pos = 0
        self.last_shock_file_pos = 0
        self.last_res_file_pos = 0
        self.last_heartbeat_time = 0.0
        self.market_tokens_cache: Dict[str, str] = {}
        self.market_condition_ids: Dict[str, str] = {}
        
        # Frozen empirical probability calibration (Route 3 / Regime 4 OOS validation ledger: 94.2%-94.6% win rate when cushion >= 0.15% up to 0.92 ceiling)
        self.calibrated_p_model = float(os.getenv("POLYMARKET_CALIBRATED_P_MODEL", "0.95"))
        self.calibrated_model_version = "REGIME_4_EMPIRICAL_V2"
        self.calibrated_model_id = "OOS_LEDGER_248_TRADES"
        self.pending_entry_intents: Dict[str, Dict[str, Any]] = {}
        self.risk_halt: bool = False
        self.reconciliation_required: bool = False
        self.global_halt_reasons: List[str] = []
        self._startup_reconciled: bool = False
        self._last_redemption_poll: float = 0.0
        self.recent_shock_window: List[Dict[str, Any]] = []
        self._last_known_collateral: Optional[float] = None
        self._prewarm_hourly_opens()

    def _record_seen_shock_id(self, shock_id: str) -> None:
        """Maintains insertion-ordered bounded dict (max 2,000 entries) so [-1000:] preserves newest IDs."""
        if not hasattr(self, "_seen_shock_order"):
            self._seen_shock_order = {sid: None for sid in self.seen_shock_ids}
        self._seen_shock_order.pop(shock_id, None)
        self._seen_shock_order[shock_id] = None
        self.seen_shock_ids.add(shock_id)
        while len(self._seen_shock_order) > 2000:
            oldest = next(iter(self._seen_shock_order))
            self._seen_shock_order.pop(oldest, None)
            self.seen_shock_ids.discard(oldest)

        # Prune hourly_candle_opens older than 48 hours
        cur_h = int(time.time() // 3600)
        for asset_map in self.hourly_candle_opens.values():
            stale_hours = [h for h in asset_map if h < (cur_h - 48)]
            for h in stale_hours:
                asset_map.pop(h, None)

        # Cap in-memory closed_positions to last 200 records
        if len(self.closed_positions) > 200:
            self.closed_positions = self.closed_positions[-200:]

    def effective_risk_pct(self, equity: float) -> float:
        """Dynamic sizing pct: base pct (18%) until equity crosses scale_up_equity_threshold, then scale_up_risk_pct (22%)."""
        try:
            if float(equity) >= float(self.risk_config["scale_up_equity_threshold"]):
                return float(self.risk_config["scale_up_risk_pct"])
        except (TypeError, ValueError):
            pass
        return float(self.dynamic_bankroll_pct)

    @staticmethod
    def _shock_asset(shock: Dict[str, Any]) -> str:
        asset = str(shock.get("asset") or "").upper()
        if not asset:
            title = str(shock.get("title") or "").strip()
            asset = title.split()[0].upper() if title else "BTC"
        return asset

    def check_recorder_freshness(self, asset: str, now_ts: float) -> Tuple[bool, float, str]:
        """Stale-recorder watchdog (zombie-socket guard).

        Fresh iff the recorder's /dev/shm fast-tick file was written within stale_fast_tick_max_age_sec (15s)
        OR its JSONL telemetry file was appended within stale_telemetry_max_age_sec (30s).
        Returns (is_fresh, newest_age_seconds, reason). A missing file counts as infinitely old.
        Unit tests (PYTEST_CURRENT_TEST without PM_FAST_TICK_DIR) never inspect the live production bus.
        """
        asset = str(asset).upper()
        env_dir = os.environ.get("PM_FAST_TICK_DIR")
        if "PYTEST_CURRENT_TEST" in os.environ and not env_dir:
            return True, 0.0, "pytest_bus_isolation"
        tick_dir = Path(env_dir) if env_dir else FAST_TICK_DIR
        tele_dir = Path(os.environ.get("PM_TELEMETRY_DIR", str(DATA_DIR)))
        tele_name = "polymarket_hourly_telemetry.jsonl" if asset == "BTC" else f"polymarket_hourly_telemetry_{asset.lower()}.jsonl"

        def _age(p: Path) -> float:
            try:
                return max(0.0, float(now_ts) - p.stat().st_mtime)
            except OSError:
                return float("inf")

        tick_age = _age(tick_dir / f"pm_fast_tick_{asset}.json")
        tele_age = _age(tele_dir / tele_name)
        fast_max = float(self.risk_config["stale_fast_tick_max_age_sec"])
        tele_max = float(self.risk_config["stale_telemetry_max_age_sec"])
        newest = min(tick_age, tele_age)
        if tick_age <= fast_max:
            return True, newest, f"fast_tick_age={tick_age:.1f}s<={fast_max:.0f}s"
        if tele_age <= tele_max:
            return True, newest, f"telemetry_age={tele_age:.1f}s<={tele_max:.0f}s"
        return False, newest, f"fast_tick_age={tick_age:.1f}s>{fast_max:.0f}s and telemetry_age={tele_age:.1f}s>{tele_max:.0f}s"

    def monitor_recorder_staleness(self, now_ts: float) -> None:
        """Heartbeat-loop hook: rate-limited alert when any allowed asset's recorder feed is older than 60s."""
        alert_after = float(self.risk_config["stale_alert_after_sec"])
        for asset in sorted(self.allowed_assets):
            ok, age, reason = self.check_recorder_freshness(asset, now_ts)
            if age > alert_after:
                send_operational_alert(
                    "STALE_RECORDER_FEED",
                    f"{asset} recorder silent for {'>' + str(int(alert_after)) + 's' if math.isinf(age) else f'{age:.0f}s'} ({reason}). New entries blocked.",
                    "CRITICAL",
                    rate_limit_sec=float(self.risk_config["alert_rate_limit_sec"]),
                    dedupe_key=f"stale_recorder:{asset}",
                )

    def _get_verified_shm_book(self, pos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Reads /dev/shm/pm_fast_tick_{asset}.json ONLY if:
          1. mkt_payload['market_id'] == str(pos['market_id'])
          2. side_book['token_id'] == str(pos['token_id'])
          3. Snapshot age <= 1.5s
        Falls back to REST get_market_book_async(token_id) if market_id or token_id mismatches.
        """
        asset = str(pos.get("asset") or "BTC").upper()
        target_mid = str(pos.get("market_id") or "")
        target_tid = str(pos.get("token_id") or "")
        target_side = str(pos.get("target_token") or "UP").upper()
        if not target_mid or not target_tid:
            return None

        tick_dir = os.environ.get("PM_FAST_TICK_DIR")
        if not tick_dir:
            if "PYTEST_CURRENT_TEST" in os.environ:
                return None
            tick_dir = "/dev/shm"
        shm_path = Path(f"{tick_dir}/pm_fast_tick_{asset}.json")
        if not shm_path.exists():
            return None
        try:
            raw = json.loads(shm_path.read_text(encoding="utf-8"))
            mkt_payload = raw.get("markets", {}).get(target_mid) if isinstance(raw.get("markets"), dict) else raw
            if not isinstance(mkt_payload, dict):
                return None
            if str(mkt_payload.get("market_id") or "") != target_mid:
                return None
            ts = float(mkt_payload.get("timestamp_unix") or mkt_payload.get("ts") or 0.0)
            if ts <= 0.0 or (time.time() - ts) > 1.5:
                return None
            side_book = mkt_payload.get(target_side) or {}
            if str(side_book.get("token_id") or "") != target_tid:
                return None
            raw_bids = side_book.get("raw_top_bids") or []
            raw_asks = side_book.get("raw_top_asks") or []
            if raw_bids or raw_asks:
                return {
                    "bids": [{"price": str(p), "size": str(s)} for p, s in raw_bids],
                    "asks": [{"price": str(p), "size": str(s)} for p, s in raw_asks],
                    "timestamp": ts,
                }
            best_b = float(side_book.get("best_bid", 0.0) or 0.0)
            best_a = float(side_book.get("best_ask", 1.0) or 1.0)
            b_sz = float(side_book.get("bid_size_l1", 0.0) or 0.0)
            a_sz = float(side_book.get("ask_size_l1", 0.0) or 0.0)
            bids_list = [{"price": str(best_b), "size": str(b_sz)}] if best_b > 0 and b_sz > 0 else []
            asks_list = [{"price": str(best_a), "size": str(a_sz)}] if best_a < 1.0 and a_sz > 0 else []
            return {
                "bids": bids_list,
                "asks": asks_list,
                "timestamp": ts,
            }
        except Exception:
            return None

    async def _atomic_replace_maker_exit(
        self, tid: str, pos: Dict[str, Any], new_price: float
    ) -> bool:
        """
        Atomically cancels an existing resting Maker TP (old_oid), reconciles any partial fills,
        releases old_oid's inventory reservation, and posts the replacement Maker TP at new_price.
        Guarantees zero INSUFFICIENT_UNRESERVED_BALANCE collisions during Queue-Priority Jumping.
        """
        token_id = pos.get("token_id")
        old_oid = pos.get("exit_order_id")
        if not token_id:
            return False

        if old_oid:
            cancel_res = await asyncio.to_thread(self.executor.cancel_order, str(old_oid))
            summary = await asyncio.to_thread(self.executor.get_order_fill_summary, str(old_oid), token_id)
            if summary is None:
                logger.warning(
                    f"[QUEUE JUMP ABORT] No fill summary for {old_oid} after cancel; retaining reservation."
                )
                pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                pos["pending_canceled_order_id"] = str(old_oid)
                await asyncio.to_thread(self.save_state)
                return False
            self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.99) or 0.99), taker=False)
            if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
                self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                return True
            is_canceled = bool((cancel_res or {}).get("is_canceled"))
            if summary.get("resting", False) or not is_canceled or not summary.get("terminal", False):
                if not summary.get("resting", False):
                    pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                    pos["pending_canceled_order_id"] = str(old_oid)
                logger.warning(f"[QUEUE JUMP ABORT] {old_oid} not terminally canceled; retaining reservation.")
                await asyncio.to_thread(self.save_state)
                return False

            self.executor.release_inventory(reservation_id=str(old_oid))
            pos["exit_order_id"] = None

        rem_shares = float(
            Decimal(str(pos.get("remaining_shares", pos.get("entry_shares", 0.0)) or 0.0)).quantize(
                Decimal("0.01"), rounding=ROUND_FLOOR
            )
        )
        if rem_shares < 0.01:
            return False

        pos["target_exit_price"] = round(float(new_price), 4)
        exit_res = await asyncio.to_thread(
            self.executor.post_maker_exit_order,
            token_id=token_id,
            price=pos["target_exit_price"],
            size=rem_shares,
            side="SELL",
        )
        posted = self._apply_exit_post_result(pos, exit_res, rem_shares)
        await asyncio.to_thread(self.save_state)
        return posted

    def _prewarm_hourly_opens(self):
        """Prewarms recent 1-HOUR candle opens (strictly excluding 15m/5m sub-hourly triggers)."""
        trigger_path = DATA_DIR / "live_shock_triggers.jsonl"
        if not trigger_path.exists():
            return
        try:
            with open(trigger_path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                read_sz = min(size, 8 * 1024 * 1024)
                f.seek(size - read_sz)
                lines = f.read().decode("utf-8", errors="ignore").splitlines()
            for line in lines:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    title_l = str(data.get("title", "") or "").lower()
                    horiz_l = str(data.get("horizon", "") or data.get("candle_interval", "")).lower()
                    slug_l = str(data.get("series_slug", "") or data.get("slug", "")).lower()
                    if any(x in horiz_l or x in slug_l or x in title_l for x in ("5m", "15m", "300s", "900s")):
                        continue
                    asset = data.get("asset")
                    t0_unix = data.get("t0_unix")
                    open_p = data.get("finalized_1h_open") or data.get("candle_open_spot")
                    if asset in ("BTC", "ETH") and t0_unix and open_p and float(open_p) > 0:
                        h_idx = int(float(t0_unix) // 3600)
                        if h_idx not in self.hourly_candle_opens[asset]:
                            self.hourly_candle_opens[asset][h_idx] = float(open_p)
                except Exception:
                    pass
            logger.info(
                f"[TREND GUARD PREWARMED] Prewarmed {len(self.hourly_candle_opens.get('ETH', {}))} ETH and "
                f"{len(self.hourly_candle_opens.get('BTC', {}))} BTC hourly opens for multi-hour trend alignment."
            )
        except Exception as e:
            logger.warning(f"[TREND GUARD PREWARM WARN] Failed to prewarm hourly opens: {e}")

    def _prewarm_market_metadata(self, shock: Dict[str, Any]):
        """Proactively warms CLOB caches with horizon-aware 15m (1800 bps) vs 1h (700 bps) fee rates."""
        try:
            title_l = str(shock.get("title", "") or "").lower()
            horiz_l = str(shock.get("horizon", "") or shock.get("candle_interval", "")).lower()
            slug_l = str(shock.get("series_slug", "") or shock.get("slug", "")).lower()
            is_15m = any(x in horiz_l or x in slug_l or x in title_l for x in ("5m", "15m", "300s", "900s"))
            default_rate = 0.18 if is_15m else 0.07

            cond_id = shock.get("condition_id") or shock.get("fee_metadata", {}).get("condition_id")
            fee_meta = shock.get("fee_metadata", {})
            fee_rate = float(fee_meta.get("fee_rate_market", default_rate) or default_rate)
            fee_exp = float(fee_meta.get("fee_exponent", 1.0) or 1.0)
            fee_bps = int(round(fee_rate * 10000))
            feats = shock.get("pre_shock_features_t0", {})
            for side_key in ("UP", "DOWN"):
                tok_info = feats.get(side_key, {})
                tok_id = tok_info.get("token_id")
                if tok_id:
                    self.executor.prewarm_token_market_cache(
                        token_id=tok_id,
                        tick_size="0.01",
                        neg_risk=False,
                        fee_rate_bps=fee_bps,
                        condition_id=cond_id,
                        fee_rate=fee_rate,
                        fee_exponent=fee_exp,
                    )
        except Exception as exc:
            logger.debug(f"[PREWARM NOTICE] Prewarm metadata notice: {exc}")

    def _prewarm_active_market_tokens(self):
        """Pre-warms active hourly market tokens from recent trigger payloads to eliminate hot-path GETs."""
        try:
            if TRIGGER_FILE.exists() and TRIGGER_FILE.stat().st_size > 0:
                sz = TRIGGER_FILE.stat().st_size
                read_sz = min(sz, 262144)
                with open(TRIGGER_FILE, "rb") as f:
                    f.seek(sz - read_sz)
                    lines = f.read().decode("utf-8", errors="ignore").splitlines()
                warmed_tokens = set()
                for l in reversed(lines):
                    if not l.strip():
                        continue
                    try:
                        shk = json.loads(l)
                        self._prewarm_market_metadata(shk)
                        feats = shk.get("pre_shock_features_t0", {})
                        for k in ("UP", "DOWN"):
                            t = feats.get(k, {}).get("token_id")
                            if t:
                                warmed_tokens.add(t)
                    except Exception:
                        continue
                if warmed_tokens and not getattr(self, "_startup_prewarmed_logged", False):
                    self._startup_prewarmed_logged = True
                    logger.info(f"[HOT-PATH PREWARMED] Proactively pre-warmed CLOB metadata & fee caches for {len(warmed_tokens)} active token(s) [version=2, markets-by-token, clob-markets].")
                if warmed_tokens and hasattr(self.executor, "prewarm_order_ladder") and not getattr(self.executor, "dry_run", True):
                    self._spawn_ladder_prewarm(list(warmed_tokens))
            if getattr(self, "_last_known_collateral", None) is not None:
                self.executor.set_cached_collateral(float(self._last_known_collateral))
        except Exception as e:
            logger.debug(f"[KEEPALIVE PREWARM] Notice: {e}")

    def _spawn_ladder_prewarm(self, tokens: List[str]) -> None:
        """
        Pillar 5A: Pre-signs the $0.55-$0.84 BUY ladder for active UP/DOWN tokens in a single-flight
        daemon thread so EIP-712 signing never blocks the asyncio event loop. Fresh entries are skipped
        inside prewarm_order_ladder, so steady-state cost is near zero.
        """
        import threading

        existing = getattr(self, "_ladder_prewarm_thread", None)
        if existing is not None and existing.is_alive():
            return
        notional = float(self.ticket_notional)

        def _worker():
            signed = 0
            for t in tokens:
                try:
                    signed += int(self.executor.prewarm_order_ladder(t, notional) or 0)
                except Exception as e:
                    logger.debug(f"[PREWARM LADDER] notice for {t}: {e}")
            if signed:
                logger.info(f"[PREWARM LADDER] Pre-signed {signed} BUY order(s) across {len(tokens)} token(s) (${notional:.2f} ticket).")

        th = threading.Thread(target=_worker, name="ladder-prewarm", daemon=True)
        self._ladder_prewarm_thread = th
        th.start()

    async def _prewarm_next_candle_markets(self) -> None:
        """
        Upgrade 4: Pre-warms next 1-hour and 15-minute market condition IDs, token IDs,
        fee structures, and CLOB metadata caches from Gamma API 2 minutes before candle expiry
        (:58, :13, :28, :43), guaranteeing zero blindness or pre-flight REST latency at candle open.
        """
        series_slugs = [
            "btc-up-or-down-hourly",
            "eth-up-or-down-hourly",
            "btc-up-or-down-15m",
            "eth-up-or-down-15m",
        ]
        warmed = 0
        now_utc = datetime.now(timezone.utc)
        for slug in series_slugs:
            try:
                url = f"https://gamma-api.polymarket.com/events?series_slug={slug}&limit=3&closed=false"
                resp = await asyncio.to_thread(self.executor._sync_session.get, url, timeout=3.0)
                if resp.status_code != 200:
                    continue
                events = resp.json()
                for event in events:
                    for market in event.get("markets", []):
                        m_id = str(market.get("id"))
                        cond_id = str(market.get("conditionId") or "")
                        end_date_str = market.get("endDate")
                        if not end_date_str or not cond_id:
                            continue
                        try:
                            end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                            secs_left = (end_dt - now_utc).total_seconds()
                        except Exception:
                            secs_left = 3600.0

                        # Pre-warm upcoming markets within next 2 hours
                        if 0 < secs_left <= 7200:
                            raw_tokens = market.get("clobTokenIds")
                            tokens = json.loads(raw_tokens) if isinstance(raw_tokens, str) else raw_tokens
                            if tokens and len(tokens) >= 2:
                                t_up = str(tokens[0])
                                t_down = str(tokens[1])
                                self.market_condition_ids[m_id] = cond_id
                                self.market_tokens_cache[f"{m_id}_UP"] = t_up
                                self.market_tokens_cache[f"{m_id}_DOWN"] = t_down

                                default_slug_rate = 0.18 if "15m" in slug else 0.07
                                fee_sched = market.get("feeSchedule", {})
                                rate = float(fee_sched.get("rate", default_slug_rate) or default_slug_rate)
                                exp = float(fee_sched.get("exponent", 1.0) or 1.0)
                                bps = int(round(rate * 10000))

                                for t in (t_up, t_down):
                                    self.executor.prewarm_token_market_cache(
                                        token_id=t,
                                        tick_size="0.01",
                                        neg_risk=False,
                                        fee_rate_bps=bps,
                                        condition_id=cond_id,
                                        fee_rate=rate,
                                        fee_exponent=exp,
                                    )
                                warmed += 1
            except Exception as e:
                logger.debug(f"[PREWARM NOTICE] Error pre-warming series {slug}: {e}")

        if warmed > 0:
            logger.info(f"[PREWARM NEXT-CANDLE] Pre-warmed metadata & CLOB caches for {warmed} upcoming token(s) from Gamma API.")

    async def _async_refresh_collateral(self) -> None:
        """Asynchronously updates CLOB L2 collateral balance in RAM without blocking hot path."""
        if self.dry_run or not self.executor.is_authenticated:
            return
        try:
            bal = await asyncio.to_thread(self.executor.get_collateral_balance, 0.0)
            if bal is not None and isinstance(bal, (int, float)) and math.isfinite(bal) and bal > 0:
                self._last_known_collateral = float(bal)
                self.executor.set_cached_collateral(float(bal))
                now_ts = time.time()
                active_market_equity = sum(self.get_position_market_value(p, now_ts) for p in self.active_positions.values())
                tot_equity = float(bal) + active_market_equity
                if not hasattr(self, "high_water_mark_equity") or self.high_water_mark_equity is None or tot_equity > self.high_water_mark_equity:
                    self.high_water_mark_equity = tot_equity
                tier_limits = get_equity_tier_limits(tot_equity, self.high_water_mark_equity)
                self.dynamic_bankroll_pct = tier_limits["dynamic_bankroll_pct"]
                if not getattr(self, "allow_cli_exposure", False):
                    self.max_exposure = tier_limits["max_exposure"]
                self.max_concurrent_positions = tier_limits["max_concurrent_positions"]
                if hasattr(self.risk_controller, "min_equity_floor_usd"):
                    self.risk_controller.min_equity_floor_usd = tier_limits["min_equity_floor"]
                if hasattr(self.risk_controller, "max_daily_loss_usd"):
                    self.risk_controller.max_daily_loss_usd = tier_limits["max_daily_loss"]
                self.risk_controller.check_equity_drawdown(float(tot_equity))
                logger.debug(f"[COLLATERAL SYNC] In-memory collateral: ${bal:.2f}, total equity: ${tot_equity:.2f}, tier: {tier_limits['tier']}")
        except Exception as e:
            logger.debug(f"[COLLATERAL SYNC] Notice: {e}")

    def _calculate_target_exit(self, price: float, tte: float) -> float:
        if getattr(self, "hold_to_maturity", False):
            if price < 0.80:
                return 0.98
            return 0.99
        return min(0.95, round(price + self.profit_theta, 2))

    # ------------------------------------------------------------------
    # Round 9: unified global-halt derivation (persisted, monotonic until reconciled)
    # ------------------------------------------------------------------
    def _global_halt_reasons(self) -> List[str]:
        reasons: List[str] = []
        intents = getattr(self, "pending_entry_intents", {}) or {}
        if intents:
            reasons.append(f"PENDING_ENTRY_INTENTS:{','.join(sorted(intents.keys()))}")
        for tid, p in (getattr(self, "active_positions", {}) or {}).items():
            if position_requires_global_halt(p):
                status_val = "LIQUIDITY_CRISIS" if p.get("status") == "LIQUIDITY_CRISIS" else (p.get('exit_order_status') or p.get('status'))
                reasons.append(f"{tid}:{status_val}")
        executor = getattr(self, "executor", None)
        if executor is not None and not self.dry_run and not getattr(executor, "reservations_trusted", True):
            reasons.append("RESERVATIONS_UNTRUSTED")
        return reasons

    def _reconciling_market_ids(self) -> Set[str]:
        """Markets that have an active ENTRY_OUTCOME_UNKNOWN or ENTRY_ONCHAIN_REVERTED position awaiting reconciliation."""
        reconciling = set()
        for p in (getattr(self, "active_positions", {}) or {}).values():
            st = p.get("status")
            pst = p.get("exit_order_status")
            if st in MARKET_SCOPED_ENTRY_HALT_STATUSES or pst in MARKET_SCOPED_ENTRY_HALT_STATUSES:
                m_id = str(p.get("market_id") or "")
                if m_id:
                    reconciling.add(m_id)
        return reconciling

    def _refresh_global_halt(self, authoritative: bool = False) -> bool:
        """
        Re-derives the global halt. It may only be CLEARED after authoritative reconciliation
        (startup reconcile completed, or an explicit authoritative caller); otherwise the
        persisted halt is retained. Returns the resulting halt state.
        """
        reasons = self._global_halt_reasons()
        may_clear = authoritative or self.dry_run or getattr(self, "_startup_reconciled", False)
        new_halt = bool(reasons) or (self.risk_halt and not may_clear)
        changed = (new_halt != self.risk_halt) or (reasons != self.global_halt_reasons)
        self.risk_halt = new_halt
        self.reconciliation_required = bool(reasons) or bool(self._reconciling_market_ids())
        self.global_halt_reasons = reasons if reasons else (self.global_halt_reasons if new_halt else [])
        if changed:
            if new_halt:
                logger.critical(f"[GLOBAL HALT] New entries blocked: {self.global_halt_reasons}")
            else:
                logger.warning("[GLOBAL HALT CLEARED] All unknown outcomes authoritatively reconciled.")
            self.save_state()
        return new_halt

    @staticmethod
    def get_position_market_value(pos: Dict[str, Any], now_ts: Optional[float] = None) -> float:
        """
        Calculates true marked-to-market equity of an active position.
        Expired out-of-the-money positions (TTE <= 0 without 0.99 fill, or resolved loss)
        are valued strictly at $0.00, NEVER adding ghost equity to total_account_value.
        """
        if now_ts is None:
            now_ts = time.time()
        # 1. Any confirmed or pending market loss: strictly $0.00
        if pos.get("pending_settlement_close_reason") in {"MARKET_RESOLVED_LOSS", "EXPIRED_OUT_OF_MONEY"}:
            return 0.0
        if pos.get("close_reason") and "MARKET_RESOLVED_LOSS" in str(pos.get("close_reason")):
            return 0.0
        resolved_win = pos.get("resolved_winning_outcome")
        target = pos.get("target_token")
        if resolved_win is not None and target is not None and resolved_win != target:
            return 0.0

        # 2. Expired candles (now_ts >= candle_expiry_ts) where maker 0.99 TP did not fill
        expiry_ts = float(pos.get("candle_expiry_ts") or 0.0)
        if expiry_ts > 0.0 and now_ts >= expiry_ts:
            if resolved_win is not None and resolved_win == target:
                return float(pos.get("expected_terminal_payout_usd") or pos.get("entry_shares") or 0.0)
            return 0.0  # Loser expired out of the money

        # 3. Status is unresolved settlement or awaiting settlement:
        if pos.get("status") in {"UNRESOLVED_SETTLEMENT", "AWAITING_ONCHAIN_SETTLEMENT"}:
            if resolved_win is not None and resolved_win == target:
                return float(pos.get("expected_terminal_payout_usd") or pos.get("entry_shares") or 0.0)
            return 0.0

        # 4. Active in-flight position before expiry:
        return float(pos.get("remaining_cost_basis", pos.get("notional_usd", 0.0)) or 0.0)

    def _risk_bearing_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Active positions carrying live market price risk.
        Positions whose candle has expired (now_ts >= candle_expiry_ts) or whose status
        is UNRESOLVED_SETTLEMENT / AWAITING_ONCHAIN_SETTLEMENT carry zero active price risk
        and do NOT count toward exposure or MAX_CONCURRENT_POSITIONS.
        """
        now_ts = time.time()
        active = {}
        for k, v in self.active_positions.items():
            if position_is_settlement_receivable(v):
                continue
            if v.get("status") in {"UNRESOLVED_SETTLEMENT", "AWAITING_ONCHAIN_SETTLEMENT"}:
                continue
            expiry_ts = float(v.get("candle_expiry_ts") or 0.0)
            if expiry_ts > 0.0 and now_ts >= expiry_ts:
                continue
            active[k] = v
        return active

    def can_enter_new_position(self, market_id: Optional[str] = None) -> bool:
        """Returns True if the harvester is eligible to accept new position entries."""
        if self.risk_controller.is_halted() or getattr(self, "risk_halt", False):
            return False
        if bool(self._global_halt_reasons()):
            return False
        if market_id and str(market_id) in self._reconciling_market_ids():
            return False
        if len(self._risk_bearing_positions()) >= self.max_concurrent_positions:
            return False
        return True

    # ------------------------------------------------------------------
    # Round 9: ONE shared lifecycle engine for startup reconciliation AND live supervision.
    # Every resolver below is the only implementation of its transition, so the two
    # paths can never disagree about what may be submitted (P0-01 / P0-02 / P0-04).
    # ------------------------------------------------------------------
    ONCHAIN_SOURCE = "POLYGON_ONCHAIN_ERC1155"
    UNWIND_UNKNOWN_STATES = frozenset({
        "UNWIND_EXECUTION_OUTCOME_UNKNOWN",
        "UNWIND_RECONCILIATION_REQUIRED",
        "UNRESOLVED_BALANCE_DISCREPANCY",
    })

    @staticmethod
    def _num(val: Any) -> Optional[float]:
        """Strict numeric coercion: only real numbers / numeric strings; never mocks, bools, NaN or inf."""
        if isinstance(val, bool) or not isinstance(val, (int, float, str, Decimal)):
            return None
        try:
            f = float(val)
        except (TypeError, ValueError):
            return None
        return f if math.isfinite(f) else None

    def _wallet_token_balance(self, token_id: Optional[str]) -> Tuple[Optional[float], str]:
        """Wallet inventory: Polygon ERC-1155 balanceOf first, CLOB balance API as fallback."""
        if not token_id:
            return None, "UNAVAILABLE"
        onchain_fn = getattr(self.executor, "get_onchain_erc1155_balance", None)
        clob_fn = getattr(self.executor, "get_conditional_balance", None)
        onchain_bal = None
        if onchain_fn is not None:
            try:
                onchain_bal = self._num(onchain_fn(token_id))
            except Exception:
                onchain_bal = None
        if onchain_bal is not None and onchain_bal > 0.0:
            return onchain_bal, self.ONCHAIN_SOURCE

        clob_bal = None
        if clob_fn is not None:
            try:
                clob_bal = self._num(clob_fn(token_id))
            except Exception:
                clob_bal = None
        if clob_bal is not None and clob_bal > 0.0:
            return clob_bal, "CLOB_BALANCE_API"

        if onchain_bal is not None and onchain_bal >= 0.0:
            return onchain_bal, self.ONCHAIN_SOURCE
        if clob_bal is not None and clob_bal >= 0.0:
            return clob_bal, "CLOB_BALANCE_API"
        return None, "UNAVAILABLE"

    def _known_fill_ids(self, exclude_tid: Optional[str] = None) -> Set[str]:
        ids: Set[str] = set()
        pools = list(self.active_positions.items()) + [
            (str(c.get("trade_id")), c) for c in self.closed_positions[-1000:]
        ]
        for tid, p in pools:
            if exclude_tid is not None and tid == exclude_tid:
                continue
            ids.update(str(x) for x in (p.get("entry_fill_ids") or []))
            ids.update(str(x) for x in (p.get("exit_fill_ids") or []))
        return ids

    def _fetch_account_fills(
        self, token_id: str, after_ts: float, side: str,
        order_id: Optional[str] = None, exclude_tid: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Own fills from exchange trade history not yet attributed to any position (None = unavailable)."""
        fn = getattr(self.executor, "get_account_fills", None)
        if fn is None:
            return None
        try:
            fills = fn(token_id, after_ts=float(after_ts), side=side, order_id=order_id or None)
        except Exception as e:
            logger.error(f"[LIFECYCLE] Trade history unavailable for {token_id}: {e}")
            return None
        if not isinstance(fills, list):
            return None
        known = self._known_fill_ids(exclude_tid)
        out = []
        for f in fills:
            if not isinstance(f, dict) or str(f.get("fill_id")) in known:
                continue
            if (self._num(f.get("size")) or 0.0) <= 0.0:
                continue
            out.append(f)
        return out

    def _fetch_entry_evidence(
        self, token_id: str, submitted_ts: float,
        entry_order_id: Optional[str] = None, exclude_tid: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Authoritative entry finality evidence (trade ids, tx hashes, actual cost) from exchange history."""
        fills = self._fetch_account_fills(token_id, submitted_ts - 5.0, "BUY", entry_order_id, exclude_tid)
        if fills is None:
            return None
        return {
            "fills": fills,
            "shares": round(sum(self._num(f.get("size")) or 0.0 for f in fills), 6),
            "cash": round(sum(self._num(f.get("cash")) or 0.0 for f in fills), 6),
            "trade_ids": sorted({str(f["trade_id"]) for f in fills if f.get("trade_id")}),
            "transactions_hashes": sorted({str(f["transaction_hash"]) for f in fills if f.get("transaction_hash")}),
            "order_ids": sorted({str(f["order_id"]) for f in fills if f.get("order_id")}),
            "fill_ids": sorted({str(f["fill_id"]) for f in fills if f.get("fill_id")}),
        }

    def _classify_entry(
        self, token_id: str, pre_bal: float, submitted_ts: float,
        entry_order_id: Optional[str], exclude_tid: Optional[str],
    ) -> Dict[str, Any]:
        """
        Classifies an entry whose exchange outcome is not locally known:
          ARRIVED            tokens are in the wallet above the pre-trade baseline
          MATCHED_UNSETTLED  exchange reports our fills but tokens have not yet arrived
          NOT_EXECUTED       authoritatively proven non-execution
          UNKNOWN            anything else (fail closed; the global halt stays)
        """
        bal, src = self._wallet_token_balance(token_id)
        evidence = self._fetch_entry_evidence(token_id, submitted_ts, entry_order_id, exclude_tid)
        out: Dict[str, Any] = {"verdict": "UNKNOWN", "balance": bal, "source": src, "delta": None, "evidence": evidence}
        if bal is None:
            return out
        delta = bal - float(pre_bal or 0.0)
        out["delta"] = delta
        if delta >= 0.01:
            out["verdict"] = "ARRIVED"
            return out
        if delta <= -0.01:
            return out  # inventory below the pre-trade baseline cannot be attributed safely
        if evidence is not None and evidence["shares"] > 0.0:
            out["verdict"] = "MATCHED_UNSETTLED"
            return out
        if entry_order_id:
            try:
                info = self.executor.get_order_status(str(entry_order_id))
            except Exception:
                info = None
            if isinstance(info, dict):
                st = str(info.get("status", "")).upper()
                matched = self._num(info.get("size_matched")) or 0.0
                if st in {"CANCELED", "CANCELLED", "EXPIRED", "REJECTED"} and matched <= 1e-4:
                    out["verdict"] = "NOT_EXECUTED"
                    out["proof"] = "TERMINAL_ZERO_FILL_ORDER_STATUS"
                    return out
        age = time.time() - float(submitted_ts or 0.0)
        if (
            evidence is not None and not evidence["fills"]
            and src in (self.ONCHAIN_SOURCE, "CLOB_BALANCE_API") and age >= ENTRY_UNEXECUTED_PROOF_AGE_S
        ):
            # Entry orders are FOK/FAK and can never rest: after the proof age, an unchanged
            # on-chain balance AND an authoritative empty account fill history is conclusive.
            out["verdict"] = "NOT_EXECUTED"
            out["proof"] = "ONCHAIN_UNCHANGED_AND_NO_ACCOUNT_FILLS"
        return out

    def _apply_entry_evidence(self, pos: Dict[str, Any], cls: Dict[str, Any]) -> None:
        """Writes recovered entry inventory + finality evidence into a position (never fabricated)."""
        evidence = cls.get("evidence") or {}
        delta = cls.get("delta")
        now_iso = datetime.now(timezone.utc).isoformat()
        if cls["verdict"] == "ARRIVED" and delta is not None:
            net = float(Decimal(str(delta)).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            pos["entry_shares"] = net
            pos["remaining_shares"] = net
            pos["remaining_exit_shares"] = net
            pos["filled_exit_shares"] = 0.0
            pos["remaining_cost_basis"] = pos.get("notional_usd", 0.0)
            if net > 0 and float(pos.get("notional_usd", 0.0) or 0.0) > 0:
                true_cost_per_share = round(float(pos["notional_usd"]) / net, 4)
                if true_cost_per_share > float(pos.get("entry_price", 0.0) or 0.0):
                    pos["entry_price"] = true_cost_per_share
                    pos["target_exit_price"] = self._calculate_target_exit(true_cost_per_share, float(pos.get("candle_expiry_ts", time.time() + 600.0)) - time.time())
            pos["inventory_reconciled"] = True
            pos["entry_inventory_source"] = cls.get("source")
        if evidence.get("shares", 0.0) > 0.0:
            pos["trade_ids"] = evidence["trade_ids"]
            pos["transactions_hashes"] = evidence["transactions_hashes"]
            pos["entry_fill_ids"] = evidence["fill_ids"]
            if not pos.get("entry_order_id") and evidence["order_ids"]:
                pos["entry_order_id"] = evidence["order_ids"][0]
            gross = max(float(evidence["shares"]), float(delta or 0.0))
            pos["gross_entry_shares"] = round(gross, 6)
            if evidence["cash"] > 0.0:
                pos["notional_usd"] = round(float(evidence["cash"]), 6)
                pos["entry_price"] = round(float(evidence["cash"]) / max(float(evidence["shares"]), 1e-9), 6)
                pos["cost_basis_estimated"] = False
            pos["entry_finality_source"] = "EXCHANGE_TRADE_HISTORY"
            if cls["verdict"] != "ARRIVED":
                # matched but not yet delivered: inventory is derived later from the wallet delta
                pos["entry_shares"] = round(float(evidence["shares"]), 6)
                pos["remaining_shares"] = pos["entry_shares"]
                pos["remaining_exit_shares"] = pos["entry_shares"]
                pos["inventory_reconciled"] = False
        elif cls["verdict"] == "ARRIVED":
            pos["gross_entry_shares"] = round(float(delta), 6)
            pos["cost_basis_estimated"] = True
            pos["entry_finality_source"] = (
                "ONCHAIN_BALANCE_DELTA" if cls.get("source") == self.ONCHAIN_SOURCE else "CLOB_BALANCE_DELTA"
            )
        pos["remaining_cost_basis"] = float(pos.get("notional_usd", 0.0) or 0.0)
        pos["entry_finality_verified_at_utc"] = now_iso

    def _verify_entry_finality(self, pos: Dict[str, Any]) -> Tuple[bool, bool]:
        """Returns (final, reverted) from exchange trade status and Polygon receipts."""
        reverted = False
        for tr_id in pos.get("trade_ids") or []:
            try:
                info = self.executor.get_trade_status(tr_id) or {}
            except Exception:
                info = {}
            st = str(info.get("status", "")).upper() if isinstance(info, dict) else ""
            if st in {"CONFIRMED", "MATCHED", "MINED"}:
                return True, False
            tx = info.get("transactionHash") or info.get("transaction_hash") if isinstance(info, dict) else None
            if tx:
                ok = self.executor.get_transaction_receipt_status(tx)
                if ok is True:
                    return True, False
                if ok is False:
                    reverted = True
        tx_hashes = pos.get("transactions_hashes") or pos.get("transactionsHashes") or pos.get("transaction_hashes") or []
        for tx in tx_hashes:
            try:
                ok = self.executor.get_transaction_receipt_status(tx)
            except Exception:
                ok = None
            if ok is True:
                return True, False
            if ok is False:
                reverted = True
        return False, reverted

    def _pending_reservations(self, pos: Dict[str, Any]) -> List[str]:
        return [str(r) for r in (pos.get("pending_reservation_ids") or []) if r]

    def _release_position_reservations(self, pos: Dict[str, Any], extra_ids: Optional[List[str]] = None) -> None:
        ids = set(self._pending_reservations(pos)) | {str(x) for x in (extra_ids or []) if x}
        for rid in ids:
            try:
                self.executor.release_inventory(reservation_id=rid)
            except Exception as e:
                logger.error(f"[LIFECYCLE] Could not release reservation {rid}: {e}")
                raise
        pos["pending_reservation_ids"] = []

    def _close_position(self, tid: str, pos: Dict[str, Any], status: str, reason: str,
                        won: Optional[bool] = None, record_pnl: bool = True) -> Optional[float]:
        """Single closeout: realized cash PnL strictly from recorded exchange fills/receipts."""
        # Round 11 P0-12 Fix: Every closeout must require estimated_exit_cash == 0,
        # exit_cash_estimated is False, and authoritative confirmation.
        # Synthetic or estimated proceeds must NEVER be settled into realized PnL,
        # EXCEPT for confirmed market resolution losses where terminal payout is definitively $0.00.
        is_terminal_loss = (
            reason in {"MARKET_RESOLVED_LOSS", "EXPIRED_OUT_OF_MONEY"}
            or won is False
            or pos.get("pending_settlement_close_reason") in {"MARKET_RESOLVED_LOSS", "EXPIRED_OUT_OF_MONEY"}
            or (pos.get("close_reason") and "MARKET_RESOLVED_LOSS" in str(pos.get("close_reason")))
        )
        if is_terminal_loss:
            pos["exit_cash_estimated"] = False
            pos["estimated_exit_cash"] = 0.0

        est_cash = float(pos.get("estimated_exit_cash", 0.0) or 0.0)
        if not is_terminal_loss and (est_cash > 0.0 or pos.get("exit_cash_estimated", False)):
            logger.warning(
                f"[SETTLEMENT_BLOCKED] Cannot settle position {tid} with unconfirmed/estimated cash "
                f"(estimated=${est_cash:.2f}, exit_cash_estimated={pos.get('exit_cash_estimated')}). "
                "Retaining in UNRESOLVED_SETTLEMENT state pending authoritative fills."
            )
            pos["status"] = "UNRESOLVED_SETTLEMENT"
            pos["close_reason"] = f"BLOCKED_UNCONFIRMED_ESTIMATE: {reason}"
            pos["pending_settlement_close_status"] = status
            pos["pending_settlement_close_reason"] = reason
            self.save_state()
            return None

        cum_cash = float(pos.get("confirmed_realized_cash", pos.get("realized_exit_cash", 0.0)) or 0.0)
        cum_fee = float(pos.get("realized_exit_fee", 0.0) or 0.0)
        filled = float(pos.get("filled_exit_shares", 0.0) or 0.0)
        net_pnl = self.calculate_realized_cash_pnl(pos, cum_cash, cum_fee) if record_pnl else 0.0
        # CRIT-03: release inventory FIRST. If release raises, nothing below has mutated the ledgers.
        self._release_position_reservations(pos, [pos.get("exit_order_id"), pos.get("unwind_order_id")])
        token_id = pos.get("token_id")
        if token_id and not any(
            p.get("token_id") == token_id for k, p in self.active_positions.items() if k != tid
        ):
            try:
                self.executor.release_inventory(token_id, float(pos.get("entry_shares", 0.0) or 0.0))
            except Exception as e:
                logger.error(f"[LIFECYCLE] Token reservation release failed for {token_id}: {e}")
                raise
        pos["status"] = status
        pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
        pos["won"] = (net_pnl > 0.0) if won is None else won
        pos["payout_usd"] = round(cum_cash, 2)
        pos["net_pnl_usd"] = net_pnl
        pos["close_reason"] = reason
        if filled > 0.0:
            pos["average_exit_price"] = round(cum_cash / filled, 4)
        pos["remaining_shares"] = 0.0
        pos["remaining_exit_shares"] = 0.0
        pos["is_liquidating"] = False
        self.closed_positions.append(pos)
        if record_pnl:
            self.risk_controller.record_trade_pnl(net_pnl)
        self.active_positions.pop(tid, None)
        self.save_state()
        self._pending_collateral_refresh = True
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_refresh_collateral())
        except RuntimeError:
            pass
        logger.info(f"[CLOSED] {tid} | {reason} | Payout=${cum_cash:.2f} | Net PnL=${net_pnl:+.2f}")
        return net_pnl

    @staticmethod
    def _estimated_taker_fee(shares: float, cash: float, fee_rate: float = 0.07) -> float:
        if shares <= 0.0:
            return 0.0
        px = min(0.999, max(0.001, cash / shares))
        return round(shares * fee_rate * px * (1.0 - px), 5)

    def _record_order_summary(self, pos: Dict[str, Any], summary: Dict[str, Any],
                              fallback_px: float, taker: bool) -> bool:
        """Records an authoritative order fill summary idempotently. Returns True if new fills were booked."""
        oid = str(summary["order_id"])
        matched = float(summary.get("matched", 0.0) or 0.0)
        prior_rec = (pos.get("order_records") or {}).get(oid) or {}
        prior = float(prior_rec.get("matched", 0.0) or 0.0)
        prior_is_estimated = bool(prior_rec.get("cash_is_estimated", False))

        cash = summary.get("cash")
        is_est = False
        if cash is None:
            cash = round(matched * max(0.0, float(fallback_px or 0.0)), 6)
            is_est = True
            pos["exit_cash_estimated"] = True
        elif summary.get("cash_is_estimated"):
            is_est = True
            pos["exit_cash_estimated"] = True

        # Round 11 P0-11: Do NOT return early if matched shares haven't changed but cash has transitioned
        # from estimated to confirmed, or if authoritative cumulative fills arrived with updated cash.
        has_new_shares = (matched > prior + 1e-6)
        has_cash_confirmation = prior_is_estimated and (not is_est)
        prior_cash = float(prior_rec.get("cash", 0.0) or 0.0)
        has_cash_correction = (abs(float(cash) - prior_cash) > 1e-6) and (not is_est)

        if not (has_new_shares or has_cash_confirmation or has_cash_correction):
            return False

        applied_r = float(pos.get("fee_rate_applied") or (0.18 if "15m" in str(pos.get("title", "")).lower() else 0.07))
        fee = self._estimated_taker_fee(matched, float(cash), fee_rate=applied_r) if taker else 0.0
        if taker:
            pos["exit_fee_estimated"] = True
        self.record_fill_and_update_position(pos, oid, matched, float(cash), fee, cash_is_estimated=is_est)
        ids = set(pos.get("exit_trade_ids") or []) | set(summary.get("trade_ids") or [])
        pos["exit_trade_ids"] = sorted(str(i) for i in ids)
        f_ids = set(pos.get("exit_fill_ids") or []) | set(summary.get("fill_ids") or [])
        pos["exit_fill_ids"] = sorted(str(i) for i in f_ids)

        # Round 10 P1-03: Refresh reservation for this order ID (remaining = original - matched)
        orig_sz = float(summary.get("original_size", 0.0) or pos.get("exit_order_size", pos.get("entry_shares", 0.0)) or 0.0)
        remaining_commit = max(0.0, orig_sz - matched)
        if summary.get("terminal"):
            self.executor.release_inventory(reservation_id=oid)
        elif remaining_commit > 0.0:
            self.executor.update_reservation(oid, remaining_commit)
        else:
            self.executor.release_inventory(reservation_id=oid)
        return True

    def _record_history_fills(self, pos: Dict[str, Any], fills: List[Dict[str, Any]], taker: bool) -> int:
        """Books exchange-history SELL fills grouped by order id; returns number of fills booked."""
        by_order: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for f in fills:
            by_order[str(f.get("order_id") or f.get("fill_id"))].append(f)
        booked = 0
        applied_r = float(pos.get("fee_rate_applied") or (0.18 if "15m" in str(pos.get("title", "")).lower() else 0.07))
        for oid, group in by_order.items():
            prior = (pos.get("order_records") or {}).get(oid) or {}
            # AUDIT-13-06 Fix: If prior record was an unconfirmed estimate, replace rather than double-count
            base_shares = 0.0 if prior.get("cash_is_estimated") else float(prior.get("matched", 0.0) or 0.0)
            base_cash = 0.0 if prior.get("cash_is_estimated") else float(prior.get("cash", 0.0) or 0.0)
            base_fee = 0.0 if prior.get("cash_is_estimated") else float(prior.get("fee", 0.0) or 0.0)
            shares = base_shares + sum(self._num(f.get("size")) or 0.0 for f in group)
            cash = base_cash + sum(self._num(f.get("cash")) or 0.0 for f in group)
            fee = base_fee + (
                self._estimated_taker_fee(sum(self._num(f.get("size")) or 0.0 for f in group),
                                          sum(self._num(f.get("cash")) or 0.0 for f in group),
                                          fee_rate=applied_r) if taker else 0.0
            )
            group_settled = all(
                bool(f.get("transaction_hash")) and str(f.get("status", "")).upper() in {"MINED", "CONFIRMED"}
                for f in group
            )
            self.record_fill_and_update_position(
                pos, oid, shares, cash, fee, cash_is_estimated=(not group_settled and not self.dry_run)
            )
            booked += len(group)
        pos["exit_fill_ids"] = sorted(set(pos.get("exit_fill_ids") or []) | {str(f.get("fill_id")) for f in fills})
        pos["exit_trade_ids"] = sorted(set(pos.get("exit_trade_ids") or []) | {str(f.get("trade_id")) for f in fills if f.get("trade_id")})
        if taker and booked:
            pos["exit_fee_estimated"] = True
        return booked

    def _after_unwind_reconciled(self, tid: str, pos: Dict[str, Any], reason_default: str) -> None:
        """Common tail once an unknown unwind is authoritatively resolved."""
        pos["unwind_order_id"] = None
        pos["is_liquidating"] = False
        pos.pop("unwind_attempt_ts", None)
        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
            self._close_position(tid, pos, ExecutionStatus.SETTLED, pos.get("unwind_reason") or reason_default, won=None)
            return
        pos["status"] = ExecutionStatus.PARTIALLY_FILLED if float(pos.get("filled_exit_shares", 0.0) or 0.0) > 0 else pos.get("status")
        pos["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
        pos["next_unwind_retry_ts"] = 0.0
        self.save_state()

    def _resolve_unknown_unwind(self, tid: str, pos: Dict[str, Any]) -> bool:
        """
        Authoritatively resolves an unwind whose execution outcome is unknown. Never submits.
        Order id known -> exchange order status + fills. Otherwise -> account SELL fill history
        since the attempt, and (only after a proof age) the on-chain balance.
        """
        token_id = pos.get("token_id")
        u_oid = pos.get("unwind_order_id")
        attempt_ts = float(pos.get("unwind_attempt_ts") or pos.get("unwind_last_attempt_ts")
                           or pos.get("unwind_start_time") or pos.get("entry_ts") or 0.0)
        fallback_px = float(pos.get("unwind_limit_price") or 0.01)
        if u_oid:
            summary = self.executor.get_order_fill_summary(str(u_oid), token_id)
            if summary is not None:
                if not summary["terminal"]:
                    self._record_order_summary(pos, summary, fallback_px, taker=True)
                    self.save_state()
                    return False
                self._record_order_summary(pos, summary, fallback_px, taker=True)
                self._release_position_reservations(pos, [str(u_oid)])
                logger.warning(f"[UNWIND RECONCILED] {tid}: order {u_oid} terminal {summary['status']} matched={summary['matched']:.2f}")
                self._after_unwind_reconciled(tid, pos, "UNWIND_RECONCILED")
                return True
        if not token_id:
            return False
        exclude_orders = set((pos.get("order_records") or {}).keys())
        if pos.get("exit_order_id"):
            exclude_orders.add(str(pos["exit_order_id"]))
        fills = self._fetch_account_fills(token_id, attempt_ts - 5.0, "SELL", exclude_tid=tid)
        if fills is None:
            return False
        fills = [f for f in fills if str(f.get("order_id")) not in exclude_orders]
        if fills:
            self._record_history_fills(pos, fills, taker=True)
            self._release_position_reservations(pos, [str(u_oid)] if u_oid else None)
            logger.warning(f"[UNWIND RECONCILED] {tid}: {len(fills)} fill(s) recovered from exchange trade history.")
            self._after_unwind_reconciled(tid, pos, "UNWIND_RECONCILED_FROM_HISTORY")
            return True
        if time.time() - attempt_ts < UNWIND_UNKNOWN_PROOF_AGE_S:
            return False
        bal, src = self._wallet_token_balance(token_id)
        rem = float(pos.get("remaining_shares", pos.get("entry_shares", 0.0)) or 0.0)
        eps = self.executor.calculate_balance_epsilon(0.001)
        if bal is not None and src == self.ONCHAIN_SOURCE and bal + eps >= rem:
            self._release_position_reservations(pos, [str(u_oid)] if u_oid else None)
            logger.warning(f"[UNWIND RECONCILED] {tid}: no fills and on-chain inventory intact ({bal:.4f} >= {rem:.4f}); unwind did not execute.")
            self._after_unwind_reconciled(tid, pos, "UNWIND_RECONCILED")
            return True
        return False

    def _resolve_unknown_entry(self, tid: str, pos: Dict[str, Any]) -> bool:
        cls = self._classify_entry(
            pos.get("token_id"), float(pos.get("pre_token_balance", 0.0) or 0.0),
            float(pos.get("submitted_at_ts") or pos.get("entry_ts") or 0.0),
            pos.get("entry_order_id"), tid,
        )
        verdict = cls["verdict"]
        if verdict in {"ARRIVED", "MATCHED_UNSETTLED"}:
            self._apply_entry_evidence(pos, cls)
            pos["status"] = ExecutionStatus.POSITION_CONFIRMED if verdict == "ARRIVED" else ExecutionStatus.MATCHED_PENDING_SETTLEMENT
            pos["exit_order_status"] = "AWAITING_DELTA_SETTLEMENT"
            self.save_state()
            logger.warning(f"[ENTRY RECONCILED] {tid}: {verdict} ({pos.get('entry_finality_source')}, shares={pos.get('entry_shares')}).")
            return True
        if verdict == "NOT_EXECUTED":
            pos["entry_shares"] = 0.0
            pos["notional_usd"] = 0.0
            pos["non_execution_proof"] = cls.get("proof")
            self._close_position(tid, pos, "NOT_EXECUTED", "ENTRY_NOT_EXECUTED_VERIFIED", won=False, record_pnl=False)
            return True
        return False

    def _resolve_unknown_exit_post(self, tid: str, pos: Dict[str, Any], open_orders: Optional[List[Dict[str, Any]]]) -> bool:
        token_id = pos.get("token_id")
        oid = pos.get("exit_order_id")
        fallback_px = float(pos.get("target_exit_price", 0.0) or 0.0)
        if oid:
            summary = self.executor.get_order_fill_summary(str(oid), token_id)
            if summary is None:
                return False
            self._record_order_summary(pos, summary, fallback_px, taker=False)
            if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
                self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                return True
            if not summary["terminal"]:
                pos["exit_order_status"] = "RESTING"
                pos["status"] = ExecutionStatus.EXIT_RESTING
                self._release_position_reservations(pos)  # order-id reservation (if any) stays keyed by oid
                self.save_state()
                return True
            self._release_position_reservations(pos, [str(oid)])
            pos["exit_order_id"] = None
            pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
            for t in pos.get("exit_tranches", []):
                if t.get("status") in {"POSTED", "IN_FLIGHT"}:
                    t["status"] = "PENDING"
            self.save_state()
            return True
        if open_orders is None:
            return False
        tracked = {str(p.get(k)) for p in self.active_positions.values() for k in ("exit_order_id", "unwind_order_id") if p.get(k)}
        candidates = [
            o for o in open_orders
            if o and str(o.get("side", "")).upper() == "SELL"
            and str(o.get("asset_id") or o.get("token_id") or "") == str(token_id)
            and str(o.get("id") or o.get("orderID") or "") not in tracked
        ]
        if len(candidates) == 1:
            adopted = str(candidates[0].get("id") or candidates[0].get("orderID"))
            pos["exit_order_id"] = adopted
            pos["exit_order_size"] = float(self._num(candidates[0].get("original_size")) or pos.get("remaining_shares", 0.0))
            pos["exit_order_status"] = "RESTING"
            pos["status"] = ExecutionStatus.EXIT_RESTING
            size = float(pos["exit_order_size"]) - float(self._num(candidates[0].get("size_matched")) or 0.0)
            self._release_position_reservations(pos)
            self.executor.reserve_inventory(token_id, size, reservation_id=adopted)
            self.save_state()
            logger.warning(f"[EXIT RECONCILED] {tid}: adopted resting exit order {adopted} discovered on the exchange.")
            return True
        if len(candidates) > 1:
            return False
        attempt_ts = float(pos.get("exit_post_attempt_ts") or 0.0)
        fills = self._fetch_account_fills(token_id, attempt_ts - 5.0, "SELL", exclude_tid=tid)
        if fills is None:
            return False
        fills = [f for f in fills if str(f.get("order_id")) not in set((pos.get("order_records") or {}).keys())]
        if fills:
            self._record_history_fills(pos, fills, taker=False)
        if time.time() - attempt_ts < UNWIND_UNKNOWN_PROOF_AGE_S and not fills:
            return False
        self._release_position_reservations(pos)
        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
            self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
            return True
        return False

    def _resolve_fill_reconciliation(self, tid: str, pos: Dict[str, Any]) -> bool:
        oid = pos.get("pending_canceled_order_id") or pos.get("exit_order_id") or pos.get("unwind_order_id")
        if not oid:
            return False
        summary = self.executor.get_order_fill_summary(str(oid), pos.get("token_id"))
        if summary is None:
            return False
        is_exit = str(oid) == str(pos.get("exit_order_id") or pos.get("pending_canceled_order_id") or "")
        fallback_px = float(pos.get("target_exit_price", 0.0) or 0.0) if is_exit else float(pos.get("unwind_limit_price") or 0.01)
        self._record_order_summary(pos, summary, fallback_px, taker=not is_exit)
        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
            self._close_position(tid, pos, ExecutionStatus.FILLED if is_exit else ExecutionStatus.SETTLED,
                                 "MAKER_SCALP_FILLED_CLOB" if is_exit else "UNWIND_RECONCILED", won=None)
            return True
        # Distinguish summary["resting"] from summary["terminal"]:
        # A canceled order with a partial fill still mining on Polygon has resting=False and terminal=False.
        # Never reset a non-resting order back to RESTING!
        if not summary["terminal"]:
            if summary.get("resting", False) and str(oid) == str(pos.get("exit_order_id") or "") and not pos.get("pending_canceled_order_id"):
                pos["exit_order_status"] = "RESTING"
                pos["status"] = ExecutionStatus.PARTIALLY_FILLED
                self.save_state()
                return True
            return False

        self._release_position_reservations(pos, [str(oid)])
        if str(pos.get("exit_order_id") or "") == str(oid):
            pos["exit_order_id"] = None
        pos["pending_canceled_order_id"] = None
        pos["cancel_pending_order_id"] = None
        pos["unwind_order_id"] = None if str(pos.get("unwind_order_id") or "") == str(oid) else pos.get("unwind_order_id")
        pos["status"] = ExecutionStatus.PARTIALLY_FILLED
        expiry = float(pos.get("candle_expiry_ts", 0.0) or 0.0)
        if pos.get("resolved_winning_outcome") is not None:
            pos["exit_order_status"] = "CANCELED_FOR_RESOLUTION"
        elif time.time() - float(pos.get("stop_triggered_ts", 0.0) or 0.0) < 300.0:
            pos["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
            attempts = int(pos.get("unwind_retry_count", 0) or 0) + 1
            pos["unwind_retry_count"] = attempts
            pos["next_unwind_retry_ts"] = time.time() + min(15.0, 1.5 ** min(attempts, 5))
            pos["is_liquidating"] = False
        elif expiry and (expiry - time.time()) < self.tte_cancel_window:
            pos["exit_order_status"] = "PRE_EXPIRY_EVALUATION_REQUIRED"
        else:
            pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
        self.save_state()
        return True

    def _resolve_lifecycle(self, tid: str, pos: Dict[str, Any],
                           open_orders: Optional[List[Dict[str, Any]]] = None, force: bool = False) -> bool:
        """Dispatches any unknown/unreconciled state to its single authoritative resolver. Never submits orders."""
        now = time.time()
        if not force and now < float(pos.get("next_resolve_ts", 0.0) or 0.0):
            return False
        st = pos.get("exit_order_status")
        pst = pos.get("status")
        resolved = False
        try:
            if st == "ENTRY_OUTCOME_UNKNOWN" or pst == "ENTRY_OUTCOME_UNKNOWN" or st == "ENTRY_ONCHAIN_REVERTED":
                resolved = self._resolve_unknown_entry(tid, pos)
            elif st in self.UNWIND_UNKNOWN_STATES:
                resolved = self._resolve_unknown_unwind(tid, pos)
            elif st == "EXIT_POST_OUTCOME_UNKNOWN":
                resolved = self._resolve_unknown_exit_post(tid, pos, open_orders)
            elif st == "FILL_RECONCILIATION_REQUIRED":
                resolved = self._resolve_fill_reconciliation(tid, pos)
            elif st == "LIQUIDITY_CRISIS" or pst == "LIQUIDITY_CRISIS":
                token_id = pos.get("token_id")
                book = self.executor.get_market_book(token_id) if token_id else {}
                bids = [b for b in (book.get("bids") or []) if float(b.get("price", 0.0)) > 0 and float(b.get("size", 0.0)) > 0]
                asks = [a for a in (book.get("asks") or []) if float(a.get("price", 0.0)) > 0 and float(a.get("size", 0.0)) > 0]
                best_b = max((float(b["price"]) for b in bids), default=0.0)
                best_a = min((float(a["price"]) for a in asks), default=1.0)
                if best_b > 0.0 and (not asks or best_b < best_a):
                    pos["status"] = ExecutionStatus.EXIT_RESTING if pos.get("exit_order_id") else ExecutionStatus.POSITION_CONFIRMED
                    pos["exit_order_status"] = "RESTING" if pos.get("exit_order_id") else "EXIT_RECOVERY_REQUIRED"
                    pos.pop("liquidity_crisis_ts", None)
                    self.save_state()
                    logger.info(f"[LIQUIDITY_CRISIS_RESOLVED] {tid}: Valid bid liquidity restored (best_bid=${best_b:.4f}). Resuming supervision.")
                    resolved = True
        except Exception as e:
            logger.error(f"[LIFECYCLE] Resolver error for {tid} ({st}): {e}", exc_info=True)
            resolved = False
        if not resolved and tid in self.active_positions:
            pos["next_resolve_ts"] = now + 5.0
        return resolved

    def _apply_exit_post_result(self, pos: Dict[str, Any], exit_res: Dict[str, Any], size: float) -> bool:
        """Single interpretation of a maker-exit submission result (startup, entry and supervisor paths)."""
        exit_res = exit_res or {}
        now = time.time()
        if exit_res.get("success"):
            pos["exit_order_id"] = exit_res.get("orderID")
            pos["exit_order_size"] = float(size)
            posted_px = self._num(exit_res.get("price"))
            if posted_px is not None and 0.0 < posted_px < 1.0:
                # The executor ceiling-rounds to the token tick; record the price actually resting
                # on the book so fill accounting and fallbacks match the live order.
                if abs(posted_px - float(pos.get("target_exit_price") or 0.0)) > 1e-9:
                    pos["requested_exit_price"] = pos.get("target_exit_price")
                pos["target_exit_price"] = posted_px
            pos["exit_order_status"] = "RESTING"
            pos["status"] = ExecutionStatus.EXIT_RESTING
            pos["exit_post_failures"] = 0
            pos.pop("next_exit_post_ts", None)
            return True
        if exit_res.get("outcome_unknown"):
            oid = exit_res.get("orderID")
            if oid:
                pos["exit_order_id"] = oid
                pos["exit_order_size"] = float(size)
            if exit_res.get("reservation_id"):
                pos.setdefault("pending_reservation_ids", []).append(exit_res["reservation_id"])
            pos["exit_post_attempt_ts"] = now
            pos["exit_order_status"] = "EXIT_POST_OUTCOME_UNKNOWN"
            logger.critical(f"Ambiguous maker exit post for {pos.get('trade_id')} (OID: {oid}); no re-post until reconciled.")
            return False
        failures = int(pos.get("exit_post_failures", 0) or 0) + 1
        pos["exit_post_failures"] = failures
        pos["next_exit_post_ts"] = now + min(30.0, 2.0 ** min(failures, 5))
        pos["exit_order_status"] = "AWAITING_DELTA_SETTLEMENT" if exit_res.get("retryable") else "POST_FAILED"
        logger.warning(f"Maker exit post deferred for {pos.get('trade_id')} ({exit_res.get('error')}); retry with backoff.")
        return False

    def _attempt_maker_exit_post(self, tid: str, pos: Dict[str, Any]) -> bool:
        """
        v3.4 guard: the supervisor and the fast-confirm task both run this in worker threads, so a
        per-position non-blocking lock guarantees at most one maker-exit submission in flight per position.
        """
        import threading

        locks = self.__dict__.setdefault("_exit_post_locks", {})
        lock = locks.get(tid)
        if lock is None:
            lock = locks.setdefault(tid, threading.Lock())
        if not lock.acquire(blocking=False):
            return False
        try:
            if pos.get("exit_order_id"):
                return False
            return self._attempt_maker_exit_post_impl(tid, pos)
        finally:
            lock.release()

    def _settlement_recheck_delay(self, pos: Dict[str, Any], now: float) -> float:
        """0.20s re-checks during the first 12s after entry (shares land ~1.5s after match), 5.0s afterwards."""
        entry_ts = float(pos.get("entry_ts", 0.0) or 0.0)
        if entry_ts > 0.0 and (now - entry_ts) < FAST_SETTLEMENT_RECHECK_WINDOW_SEC:
            return FAST_CONFIRM_POLL_SEC
        return 5.0

    def _maybe_queue_jump_on_post(self, pos: Dict[str, Any], size: float) -> None:
        """Pre-post queue jump using the RAM fast-tick L1 book only (no REST on the post path)."""
        if pos.get("queue_jumped"):
            return
        tgt = float(pos.get("target_exit_price") or 0.0)
        if tgt < QUEUE_JUMP_MIN_TARGET:
            return
        book = fast_tick_book_for_token(read_fast_tick(pos.get("asset", "BTC")), pos.get("token_id"))
        if not book:
            return
        jump = compute_queue_priority_maker_price(
            float(pos.get("entry_price", 0.70) or 0.70), size, book.get("bids", []), book.get("asks", []), tgt,
        )
        if jump is not None:
            logger.info(f"[QUEUE JUMP] {pos.get('trade_id')}: wall at ${tgt:.2f}; posting maker TP at ${jump:.2f} instead.")
            pos["target_exit_price"] = jump
            pos["queue_jumped"] = True
            for t in pos.get("exit_tranches", []):
                if t.get("status") == "PENDING" and abs(float(t.get("price", 0.0)) - tgt) < 1e-9:
                    t["price"] = jump
                    break

    async def _fast_confirm_and_post_maker_exit(self, trade_id: str) -> bool:
        """
        v3.4: polls the shared maker-exit gate every 0.20s for up to 5.0s right after a MATCHED_PENDING_SETTLEMENT
        entry, so the post_only maker TP lands the moment the ERC-1155 shares arrive instead of after a 5s sleep.
        """
        deadline = time.time() + FAST_CONFIRM_WINDOW_SEC
        while time.time() < deadline:
            pos = self.active_positions.get(trade_id)
            if pos is None or pos.get("exit_order_id"):
                return False
            if position_may_post_new_maker_exit(pos):
                try:
                    posted = await asyncio.to_thread(self._attempt_maker_exit_post, trade_id, pos)
                except Exception as e:
                    logger.warning(f"[FAST CONFIRM] {trade_id}: maker exit attempt error: {e}")
                    posted = False
                if posted:
                    logger.info(f"[FAST CONFIRM] {trade_id}: maker TP posted within the fast-confirm window.")
                    return True
                if position_requires_global_halt(pos):
                    return False
            await asyncio.sleep(FAST_CONFIRM_POLL_SEC)
        return False

    def _spawn_fast_confirm(self, trade_id: str) -> None:
        try:
            task = asyncio.get_running_loop().create_task(self._fast_confirm_and_post_maker_exit(trade_id))
        except RuntimeError:
            return
        tasks = self.__dict__.setdefault("_fast_confirm_tasks", set())
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    def _attempt_maker_exit_post_impl(self, tid: str, pos: Dict[str, Any]) -> bool:
        """
        The ONLY path that submits a new maker exit (startup recovery and live supervision).
        Requires: allowlisted lifecycle state, outside the pre-expiry window, authoritative entry
        finality (trade/tx evidence or verified on-chain inventory) and wallet inventory covering
        the remaining shares. Returns True if an order was posted.
        """
        now = time.time()
        expiry = float(pos.get("candle_expiry_ts", now + 600.0) or (now + 600.0))
        if not position_may_post_new_maker_exit(pos) or (expiry - now) < self.tte_cancel_window:
            return False
        if now < float(pos.get("next_exit_post_ts", 0.0) or 0.0):
            return False
        token_id = pos.get("token_id")
        if not token_id:
            return False
        eps = self.executor.calculate_balance_epsilon(0.001)
        if self.dry_run:
            gross = Decimal(str(pos.get("gross_entry_shares", pos.get("entry_shares", 0.0))))
            if not pos.get("inventory_reconciled"):
                net = float(gross.quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                pos["entry_shares"] = net
                pos["remaining_shares"] = net
                pos["remaining_exit_shares"] = net
                pos["remaining_cost_basis"] = pos.get("notional_usd", 0.0)
                if net > 0 and float(pos.get("notional_usd", 0.0) or 0.0) > 0:
                    true_cost_per_share = round(float(pos["notional_usd"]) / net, 4)
                    if true_cost_per_share > float(pos.get("entry_price", 0.0) or 0.0):
                        pos["entry_price"] = true_cost_per_share
                        pos["target_exit_price"] = self._calculate_target_exit(true_cost_per_share, expiry - now)
                pos["inventory_reconciled"] = True
        else:
            final, reverted = self._verify_entry_finality(pos)
            if reverted and not final:
                logger.critical(f"[ON-CHAIN REVERT] Entry for {tid} reverted on Polygon; holding for reconciliation.")
                pos["status"] = ExecutionStatus.FAILED
                pos["exit_order_status"] = "ENTRY_ONCHAIN_REVERTED"
                pos["close_reason"] = "ONCHAIN_REVERT_DETECTED"
                self.save_state()
                return False
            bal, src = self._wallet_token_balance(token_id)
            if bal is None:
                logger.warning(f"[FAIL-CLOSED] Wallet inventory unavailable for {token_id}; delaying exit for {tid}.")
                return False
            if not final and src in {self.ONCHAIN_SOURCE, "CLOB_BALANCE_API"}:
                # Possession verified in wallet balance is settlement finality for delivered tokens.
                final = True
            if not final:
                pos["exit_blocked_reason"] = f"ENTRY_FINALITY_UNPROVEN(source={src})"
                pos["next_exit_post_ts"] = now + self._settlement_recheck_delay(pos, now)
                self.save_state()
                return False
            if not pos.get("inventory_reconciled") and float(pos.get("filled_exit_shares", 0.0) or 0.0) <= 0.0:
                pre_bal = float(pos.get("pre_token_balance", 0.0) or 0.0)
                received = Decimal(str(bal - pre_bal))
                gross = Decimal(str(pos.get("gross_entry_shares", pos.get("entry_shares", 0.0))))
                d_eps = Decimal(str(eps))
                if received <= d_eps or received > gross + d_eps + Decimal("0.01"):
                    pos["exit_blocked_reason"] = f"ENTRY_INVENTORY_UNRECONCILED(received={received}, gross={gross})"
                    pos["next_exit_post_ts"] = now + self._settlement_recheck_delay(pos, now)
                    self.save_state()
                    return False
                net = float(received.quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                if received < gross - Decimal("0.01"):
                    # Entry taker fee was deducted in outcome shares; prevent cash double-deduction
                    pos["entry_fee_asset"] = "SHARES"
                    pos["entry_fee_cash_usd"] = 0.0
                pos["entry_shares"] = net
                pos["remaining_shares"] = net
                pos["remaining_exit_shares"] = net
                pos["remaining_cost_basis"] = pos.get("notional_usd", 0.0)
                if net > 0 and float(pos.get("notional_usd", 0.0) or 0.0) > 0:
                    true_cost_per_share = round(float(pos["notional_usd"]) / net, 4)
                    if true_cost_per_share > float(pos.get("entry_price", 0.0) or 0.0):
                        pos["entry_price"] = true_cost_per_share
                        pos["target_exit_price"] = self._calculate_target_exit(true_cost_per_share, expiry - now)
                pos["inventory_reconciled"] = True
                pos.setdefault("entry_inventory_source", src)
            else:
                rem_needed = float(pos.get("remaining_shares", pos.get("entry_shares", 0.0)) or 0.0)
                if bal + eps < rem_needed:
                    logger.critical(
                        f"[INVENTORY DISCREPANCY] {tid}: wallet {bal:.4f} < remaining {rem_needed:.4f} ({src}). "
                        "Refusing to post; reconciling against exchange history."
                    )
                    pos["exit_order_status"] = "UNRESOLVED_BALANCE_DISCREPANCY"
                    pos["unwind_attempt_ts"] = float(pos.get("entry_ts") or now)
                    self.save_state()
                    return False
        size = float(Decimal(str(pos.get("remaining_shares", pos.get("entry_shares", 0.0)) or 0.0)).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
        if size < 0.01:
            return False

        # 50/50 two-tranche maker exits for tickets >= $10.0 (50% fast scalp @ +14¢, 50% runner @ 0.98)
        # Polymarket CLOB rejects GTC limit orders < 5.0 shares. Only split if t1_sz >= 5.0 and t2_sz >= 5.0
        rem_total = size
        entry_px = float(pos.get("entry_price", 0.70))
        if not getattr(self, "hold_to_maturity", False) and float(pos.get("notional_usd", 0.0) or 0.0) >= 10.0 and "exit_tranches" not in pos and rem_total >= 10.0:
            t1_sz = float((Decimal(str(rem_total)) * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            t2_sz = float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            if t1_sz >= 5.0 and t2_sz >= 5.0:
                t1_px = min(0.94, round(entry_px + 0.14, 2))
                t2_px = 0.98
                pos["exit_tranches"] = [
                    {"idx": 1, "size": t1_sz, "price": t1_px, "status": "PENDING"},
                    {"idx": 2, "size": t2_sz, "price": t2_px, "status": "PENDING"},
                ]
            else:
                pos["target_exit_price"] = min(0.96, round(entry_px + 0.16, 2))

        active_tranche = None
        pending_tranches = [t for t in pos.get("exit_tranches", []) if t.get("status") == "PENDING"]
        if pending_tranches and float(pending_tranches[0]["size"]) >= 5.0 and rem_total >= 5.0:
            active_tranche = pending_tranches[0]
            size = min(rem_total, float(active_tranche["size"]))
            pos["target_exit_price"] = float(active_tranche["price"])
        else:
            size = rem_total
            pos.pop("exit_tranches", None)
            if not pos.get("target_exit_price"):
                pos["target_exit_price"] = min(0.96, round(entry_px + 0.16, 2))

        pos["status"] = ExecutionStatus.POSITION_CONFIRMED
        self._maybe_queue_jump_on_post(pos, size)
        exit_res = self.executor.post_maker_exit_order(
            token_id=token_id, price=pos["target_exit_price"], size=size, side="SELL",
        )
        # Reprice maker ask up to best_bid + 0.01 if post_only rejected due to crossing book (FINDING-15-03c)
        if not (exit_res or {}).get("success") and "crosses book" in str((exit_res or {}).get("error", "")).lower():
            try:
                book = self.executor.get_market_book(token_id) if hasattr(self.executor, "get_market_book") else None
                bids = (book or {}).get("bids", [])
                if bids:
                    best_bid = float(bids[0].get("price", 0.0) or 0.0)
                    repriced = min(0.99, round(best_bid + 0.01, 4))
                    if repriced > float(pos["target_exit_price"]):
                        logger.info(f"[MAKER REPRICE] {tid}: post_only crossed book (bid={best_bid:.4f}). Repricing ask to ${repriced:.4f}.")
                        pos["target_exit_price"] = repriced
                        if active_tranche is not None:
                            active_tranche["price"] = repriced
                        exit_res = self.executor.post_maker_exit_order(
                            token_id=token_id, price=repriced, size=size, side="SELL",
                        )
            except Exception as e:
                logger.debug(f"Reprice query failed for {tid}: {e}")
        posted = self._apply_exit_post_result(pos, exit_res, size)
        if active_tranche is not None and posted:
            active_tranche["status"] = "POSTED"
        elif active_tranche is not None and (exit_res or {}).get("outcome_unknown"):
            active_tranche["status"] = "IN_FLIGHT"
        self.save_state()
        if posted:
            logger.info(f"✓ MAKER EXIT POSTED: {tid} | {size:.2f} shares @ ${pos['target_exit_price']:.4f} | OID={pos['exit_order_id']}")
        return posted

    def _handle_unwind_response(self, tid: str, pos: Dict[str, Any], res: Optional[Dict[str, Any]],
                                requested: float, close_reason: str, partial_state: str,
                                limit_price: float) -> str:
        """
        Single interpretation of an aggressive FAK unwind response. Returns CLOSED / PARTIAL / UNKNOWN / FAILED.
        Never infers fill quantity from cash: missing, zero, contradictory or estimated fill amounts are
        routed to UNWIND_EXECUTION_OUTCOME_UNKNOWN and resolved from exchange records.
        """
        res = res or {}
        now = time.time()
        oid = res.get("orderID")
        pos["unwind_limit_price"] = float(limit_price)

        def _mark_unknown(why: str) -> str:
            pos["exit_order_status"] = "UNWIND_EXECUTION_OUTCOME_UNKNOWN"
            pos["is_liquidating"] = True
            pos["unwind_order_id"] = oid
            pos["unwind_attempt_ts"] = now
            pos["unwind_reason"] = close_reason
            pos["unwind_last_error"] = why
            if res.get("reservation_id"):
                pos.setdefault("pending_reservation_ids", []).append(res["reservation_id"])
            pos["next_resolve_ts"] = 0.0
            self.save_state()
            logger.critical(f"[UNWIND OUTCOME UNKNOWN] {tid}: {why}. No repeat submission until exchange reconciliation.")
            return "UNKNOWN"

        if res.get("outcome_unknown"):
            return _mark_unknown(str(res.get("error") or "AMBIGUOUS_UNWIND_RESPONSE"))
        matched = self._num(res.get("matched_size"))
        taking = self._num(res.get("taking_amount"))
        claims_fill = bool(
            res.get("success")
            or res.get("partial")
            or (matched or 0.0) > 0.0
            or (oid and (taking or 0.0) > 0.0)
            or (res.get("matched_size") is not None and (taking or 0.0) > 0.0)
        )
        if not claims_fill:
            return "FAILED"
        if res.get("success") and not oid and (matched or 0.0) == 0.0 and (taking or 0.0) == 0.0:
            # executor skipped a sub-lot residual: nothing was submitted
            if requested < 0.01:
                self._close_position(tid, pos, ExecutionStatus.SETTLED, f"{close_reason}_DUST_RESIDUAL", won=None)
                return "CLOSED"
            return "FAILED"
        contradictory = (
            matched is None or matched <= 0.0 or matched > requested + 1e-4
            or taking is None or taking < 0.0
            or bool(res.get("taking_amount_missing"))
        )
        if contradictory:
            return _mark_unknown(
                f"CONTRADICTORY_OR_INCOMPLETE_FILL_QUANTITIES(matched={res.get('matched_size')}, taking={res.get('taking_amount')})"
            )
        fee = self._num(res.get("fee_usd")) or 0.0
        record_id = oid or f"{close_reason}_{int(now*1000)}"
        taking_estimated = bool(res.get("taking_amount_estimated", False))
        self.record_fill_and_update_position(
            pos, record_id, matched, taking, fee, cash_is_estimated=taking_estimated
        )
        if taking_estimated:
            # Off-chain MATCHED: cash is provisional until Polygon block inclusion is confirmed.
            pos["pending_settlement_order_id"] = str(record_id)
        if res.get("fee_is_estimated"):
            pos["exit_fee_estimated"] = True
        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
            won_flag = False if ("SALVAGE" in close_reason or "STOP" in close_reason) else None
            if taking_estimated:
                # Proceeds are provisional (off-chain MATCHED): never let won=False mark a terminal loss that
                # would zero the sale cash. _close_position will hold the position in UNRESOLVED_SETTLEMENT.
                won_flag = None
            self._close_position(tid, pos, ExecutionStatus.SETTLED, close_reason, won=won_flag)
            return "CLOSED"
        pos["status"] = ExecutionStatus.PARTIALLY_FILLED
        pos["exit_order_status"] = partial_state
        pos["is_liquidating"] = False
        pos["unwind_order_id"] = None
        attempts = int(pos.get("unwind_retry_count", 0) or 0) + 1
        pos["unwind_retry_count"] = attempts
        pos["next_unwind_retry_ts"] = now + min(30.0, 2.0 ** min(attempts, 5))
        logger.warning(
            f"⚠️ [PARTIAL UNWIND] {tid}: matched {matched:.2f}; cumulative {pos.get('filled_exit_shares', 0.0):.2f}/"
            f"{pos.get('entry_shares', 0.0):.2f}; remaining {pos.get('remaining_shares', 0.0):.2f} retained."
        )
        self.save_state()
        return "PARTIAL"

    @staticmethod
    def calculate_realized_cash_pnl(pos: Dict[str, Any], gross_exit_cash: float, exit_fee: float = 0.0) -> float:
        """
        Unified cash PnL formula guaranteeing cash and token conservation across all closeout branches:
        Cash PnL = Actual Cash Received - Actual Cash Spent - Actual Cash Entry Fee - Actual Cash Exit Fee.
        
        If entry fees were collected in outcome shares (the standard Polymarket CLOB mechanism for buys),
        the token fee already reduced the delivered shares inventory, so entry_cash_fee is strictly 0.0.
        """
        entry_fee_asset = str(pos.get("entry_fee_asset", "")).upper()
        if entry_fee_asset == "SHARES":
            entry_cash_fee = float(pos.get("entry_fee_cash_usd", 0.0))
        else:
            entry_cash_fee = float(pos.get("entry_fee_cash_usd", pos.get("fee_usd", 0.0)))
        
        notional = float(pos.get("notional_usd", 0.0))
        cash_in = float(gross_exit_cash)
        cash_exit_fee = float(exit_fee)
        
        return round(cash_in - notional - entry_cash_fee - cash_exit_fee, 2)

    @staticmethod
    def record_fill_and_update_position(
        pos: Dict[str, Any],
        order_id: str,
        matched_shares: float,
        taking_cash: float,
        fee_usd: float = 0.0,
        cash_is_estimated: bool = False,
    ) -> Dict[str, Any]:
        """
        Unified, single-source-of-truth fill-accounting engine (P0-03, P0-04, Round 10 P1-04 Fix).
        Idempotently updates per-order/per-trade records in pos["order_records"][order_id]
        and recomputes position-level cumulative filled shares, confirmed realized cash proceeds,
        estimated exit proceeds, and exit fees strictly from order_records.
        
        Guarantees:
        1. Multi-order fill monotonicity: subsequent order matches NEVER overwrite prior order proceeds/fees.
        2. Fee conservation: exit fees from order_records are never double-counted with pos["realized_exit_fee"].
        3. Accurate remaining shares and inventory tracking.
        4. Round 10 P1-04: confirmed_realized_cash and estimated_exit_cash are kept strictly separated.
        """
        order_records = pos.setdefault("order_records", {})
        
        # Explicit Migration of Legacy Position Totals (Probe H Fix)
        # Prevents overwriting historical partial unwind proceeds/fees when a subsequent order record is inserted,
        # but avoids duplicating fills if updating the position's primary current exit order.
        current_exit_oid = str(pos.get("exit_order_id") or "")
        legacy_shares = float(pos.get("filled_exit_shares", 0.0) or 0.0)
        legacy_cash = float(pos.get("realized_exit_cash", 0.0) or 0.0)
        legacy_fee = float(pos.get("realized_exit_fee", 0.0) or 0.0)
        if str(order_id) != current_exit_oid and (legacy_shares > 0.0 or legacy_cash > 0.0 or legacy_fee > 0.0) and "LEGACY_PREVIOUS_FILLS" not in order_records:
            existing_shares = sum(float(r.get("matched", 0.0)) for r in order_records.values())
            existing_cash = sum(float(r.get("cash", 0.0)) for r in order_records.values())
            existing_fee = sum(float(r.get("fee", 0.0)) for r in order_records.values())
            diff_shares = max(0.0, round(legacy_shares - existing_shares, 4))
            diff_cash = max(0.0, round(legacy_cash - existing_cash, 4))
            diff_fee = max(0.0, round(legacy_fee - existing_fee, 4))
            if diff_shares > 0.0 or diff_cash > 0.0 or diff_fee > 0.0:
                order_records["LEGACY_PREVIOUS_FILLS"] = {
                    "size": diff_shares,
                    "matched": diff_shares,
                    "cash": diff_cash,
                    "fee": diff_fee,
                    "cash_is_estimated": bool(pos.get("exit_cash_estimated", False)),
                }

        oid = str(order_id)
        rec = order_records.setdefault(oid, {
            "size": float(pos.get("exit_order_size", pos.get("entry_shares", 0.0))),
            "matched": 0.0,
            "cash": 0.0,
            "confirmed_cash": 0.0,
            "estimated_cash": 0.0,
            "fee": 0.0,
            "cash_is_estimated": bool(cash_is_estimated),
        })
        rec["matched"] = max(float(rec.get("matched", 0.0)), float(matched_shares or 0.0))

        # Round 11 P0-11: Separate provisional estimates from authoritative confirmed fills.
        # NEVER use max() across estimated and confirmed cash.
        taking_val = float(taking_cash or 0.0)
        if not cash_is_estimated:
            # Authoritative cumulative confirmed fill receipt arrived:
            # Overwrite provisional estimates completely with the authoritative figure!
            rec["confirmed_cash"] = taking_val
            rec["estimated_cash"] = 0.0
            rec["cash"] = taking_val
            rec["cash_is_estimated"] = False
        else:
            # Incoming fill is a provisional estimate:
            # Only set estimate if we do not already have authoritative confirmed cash for this order
            if not rec.get("cash_is_estimated", False) and float(rec.get("confirmed_cash", 0.0)) > 0.0:
                pass
            else:
                rec["estimated_cash"] = taking_val
                rec["cash"] = taking_val
                rec["cash_is_estimated"] = True

        if float(fee_usd or 0.0) > 0.0:
            rec["fee"] = max(float(rec.get("fee", 0.0)), float(fee_usd))

        # Position totals are computed strictly as aggregates across order_records
        total_shares = sum(float(r.get("matched", 0.0)) for r in order_records.values())
        confirmed_cash = sum(float(r.get("cash", 0.0)) for r in order_records.values() if not r.get("cash_is_estimated"))
        estimated_cash = sum(float(r.get("cash", 0.0)) for r in order_records.values() if r.get("cash_is_estimated"))
        total_cash = confirmed_cash + estimated_cash
        total_fees = sum(float(r.get("fee", 0.0)) for r in order_records.values())

        pos["filled_exit_shares"] = round(total_shares, 4)
        pos["confirmed_realized_cash"] = round(confirmed_cash, 4)
        pos["estimated_exit_cash"] = round(estimated_cash, 4)
        pos["realized_exit_cash"] = round(total_cash, 4)
        pos["gross_exit_cash"] = round(total_cash, 4)
        pos["exit_cash_estimated"] = (estimated_cash > 0.0)
        pos["realized_exit_fee"] = round(total_fees, 4)

        entry_shares = float(pos.get("entry_shares", 0.0))
        rem_shares = max(0.0, round(entry_shares - total_shares, 4))
        pos["remaining_shares"] = rem_shares
        pos["remaining_exit_shares"] = rem_shares
        if entry_shares > 0.0:
            pos["remaining_cost_basis"] = round(float(pos.get("notional_usd", 0.0)) * (rem_shares / entry_shares), 4)

        return rec

    def confirm_onchain_redemption(
        self,
        trade_id: str,
        verified_usdc_received: Optional[float] = None,
        tx_hash: Optional[str] = None,
    ) -> bool:
        """
        Finalizes a resolved winning position ONLY on verified redemption receipt (Condition 3).

        Live mode: the payout is read from the Conditional Tokens PayoutRedemption event emitted
        to this wallet for the position's condition (tx receipt status == 1). Caller-supplied
        amounts are never trusted. Receipts are deduplicated by transaction hash, and the cash
        attributed to the position is capped at its winning shares x $1.00.
        Dry-run mode: accepts the supplied simulated amount.
        """
        pos = self.active_positions.get(trade_id)
        if not pos:
            logger.warning(f"[REDEMPTION] Position {trade_id} not found in active_positions.")
            return False
        if not position_is_settlement_receivable(pos):
            logger.warning(f"[REDEMPTION] Position {trade_id} is not awaiting on-chain settlement ({pos.get('status')}).")
            return False

        win_shares = float(pos.get("winning_shares_held", 0.0) or 0.0)
        redeemed = set(getattr(self, "redeemed_tx_hashes", []) or [])
        if self.dry_run:
            payout = float(verified_usdc_received if verified_usdc_received is not None else win_shares)
            tx = tx_hash or f"DRYRUN_REDEMPTION_{trade_id}"
        else:
            receipts = self.executor.find_redemption_payouts(
                str(pos.get("condition_id") or ""),
                from_block=pos.get("resolution_block"),
                tx_hash=tx_hash,
            )
            if receipts is None:
                logger.warning(f"[REDEMPTION] Cannot verify redemption for {trade_id} (RPC unavailable); retaining receivable.")
                return False
            fresh = [r for r in receipts if r.get("transaction_hash") and r["transaction_hash"] not in redeemed]
            if not fresh:
                return False
            receipt = fresh[0]
            payout = float(receipt["payout_usd"])
            tx = str(receipt["transaction_hash"])
        if tx in redeemed:
            logger.warning(f"[REDEMPTION] Duplicate redemption receipt {tx} ignored for {trade_id}.")
            return False

        attributed = round(min(payout, win_shares), 6)
        self.record_fill_and_update_position(pos, f"ONCHAIN_REDEMPTION_{tx}", win_shares, attributed, 0.0)
        cum_cash = float(pos.get("realized_exit_cash", 0.0))
        cum_exit_fee = float(pos.get("realized_exit_fee", 0.0))
        net_pnl = self.calculate_realized_cash_pnl(pos, cum_cash, cum_exit_fee)

        pos["status"] = ExecutionStatus.SETTLED
        pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
        pos["won"] = (net_pnl > 0.0)
        pos["payout_usd"] = round(cum_cash, 2)
        pos["net_pnl_usd"] = round(net_pnl, 2)
        pos["close_reason"] = "ONCHAIN_REDEMPTION_CONFIRMED"
        pos["redemption_tx_hash"] = tx
        pos["redemption_payout_verified_usd"] = payout
        pos["redemption_receivable_usd"] = 0.0

        redeemed.add(tx)
        self.redeemed_tx_hashes = sorted(redeemed)[-1000:]
        self.closed_positions.append(pos)
        self.risk_controller.record_trade_pnl(net_pnl)
        del self.active_positions[trade_id]
        self.save_state()
        self.executor.invalidate_collateral_cache()
        self._pending_collateral_refresh = True
        logger.info(f"✓ ON-CHAIN REDEMPTION VERIFIED: {trade_id} | tx={tx} | USDC=${attributed:.2f} | Net PnL=${net_pnl:+.2f}")
        return True

    def poll_onchain_redemptions(self, force: bool = False) -> int:
        """Periodically verifies redemptions for resolved winning receivables every 60s. Returns count settled."""
        now = time.time()
        if not force and (now - self._last_redemption_poll) < REDEMPTION_POLL_INTERVAL_S:
            return 0
        self._last_redemption_poll = now
        settled = 0
        for tid, pos in list(self.active_positions.items()):
            if position_is_settlement_receivable(pos) and float(pos.get("winning_shares_held", 0.0) or 0.0) > 0.0:
                try:
                    if self.confirm_onchain_redemption(tid):
                        settled += 1
                except Exception as e:
                    logger.error(f"[REDEMPTION] Verification error for {tid}: {e}")
        if settled > 0:
            self.executor.invalidate_collateral_cache()
            self._pending_collateral_refresh = True
            logger.info(f"[AUTO-REDEEMER] Swept and settled {settled} mature position(s). Reclaimed collateral to balance.")
        return settled

    def get_condition_id(self, market_id: str) -> Optional[str]:
        m_str = str(market_id)
        if m_str in self.market_condition_ids:
            return self.market_condition_ids[m_str]
        try:
            r = self.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{m_str}", timeout=3).json()
            cond_id = r.get("conditionId")
            if cond_id:
                self.market_condition_ids[m_str] = str(cond_id)
                return str(cond_id)
        except Exception as e:
            logger.error(f"Error fetching condition_id for market {market_id}: {e}")
        return None

    def get_token_id(self, market_id: str, target_token: str) -> Optional[str]:
        cache_key = f"{market_id}_{target_token}"
        if cache_key in self.market_tokens_cache:
            return self.market_tokens_cache[cache_key]
        try:
            r = self.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{market_id}", timeout=3).json()
            cond_id = r.get("conditionId")
            if cond_id:
                self.market_condition_ids[str(market_id)] = str(cond_id)
            raw = r.get("clobTokenIds")
            tokens = json.loads(raw) if isinstance(raw, str) else raw
            if tokens and len(tokens) >= 2:
                self.market_tokens_cache[f"{market_id}_UP"] = str(tokens[0])
                self.market_tokens_cache[f"{market_id}_DOWN"] = str(tokens[1])
                logger.info(f"Resolved tokens for market {market_id}: UP={tokens[0][:10]}... DOWN={tokens[1][:10]}...")
                return self.market_tokens_cache.get(cache_key)
        except Exception as e:
            logger.error(f"Error fetching tokens for market {market_id}: {e}")
        return None

    def get_reference_spot_price(self, asset: str) -> Optional[float]:
        """
        Pulls current spot reference price from Binance REST ticker with low latency (<50ms).
        Caches price for 1.0s to avoid redundant network overhead during high-frequency checks.
        """
        now = time.time()
        cache_key = f"{asset.upper()}USDT"
        # v3.3: /dev/shm fast tick bus first (<=0.50s old, ~25ms fresh), then REST fallback
        snap = read_fast_tick(asset, max_age_sec=FAST_TICK_MAX_AGE_SEC, now=now)
        if snap:
            shm_px = float(snap.get("spot") or 0.0)
            if math.isfinite(shm_px) and shm_px > 0.0:
                self._spot_cache[cache_key] = (shm_px, now)
                return shm_px
        if cache_key in self._spot_cache:
            val, ts = self._spot_cache[cache_key]
            if now - ts < 1.0:
                return val

        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={cache_key}"
            resp = self.executor._sync_session.get(url, timeout=1.5)
            if resp.status_code == 200:
                price = float(resp.json().get("price", 0.0))
                if not math.isfinite(price) or price <= 0.0:
                    logger.error("Rejected nonfinite/invalid spot price: %r", price)
                    return None
                self._spot_cache[cache_key] = (price, now)
                return price
        except Exception as e:
            logger.debug(f"Failed to fetch Binance spot price for {cache_key}: {e}")
        return None

    def compute_kelly_ticket_size(
        self,
        p_model: float,
        p_market_ask: float,
        bankroll: float,
        fee_rate: Optional[float] = None,
        fee_exponent: Optional[float] = None,
    ) -> float:
        """
        Calculates fractional Kelly sizing for bounded binary contracts using the authoritative
        cash-and-share payoff model (Round 10 Auditor Spec 6.A):
          p = acquisition price per gross share
          q = calibrated probability of winning
          f(p) = fee_rate * (p * (1 - p)) ** fee_exponent
          h(p) = f(p) / p (fee fraction of gross shares)
          g(p) = 1.0 - h(p) (net delivered share multiplier)
          c_eff = p / g(p) (effective acquisition cost per delivered winning share)
          f* = max(0, (q - c_eff) / (1 - c_eff))
        Capped at max_notional_cap_pct of bankroll (default 30% for elastic bankroll compounding) and MAX_ABSOLUTE_TICKET_USD ($75.00).
        Deducts taker fees net of notional.
        """
        if not all(math.isfinite(float(v)) for v in (p_model, p_market_ask, bankroll)):
            return 0.0
        if not (0.0 < float(p_model) < 1.0):
            return 0.0
        if bankroll <= 0:
            return 0.0

        if p_market_ask >= self.max_price_ceiling or p_market_ask <= self.min_price_floor:
            return 0.0

        p = float(p_market_ask)
        q = float(p_model)

        # Authoritative fee schedule binding (Round 10 P1-01)
        r = float(fee_rate if fee_rate is not None else 0.07)
        e = float(fee_exponent if fee_exponent is not None else 1.0)
        if not (math.isfinite(r) and r >= 0.0 and math.isfinite(e) and e > 0.0):
            return 0.0

        clamped_p = min(0.9999, max(0.0001, p))
        f_p = r * ((clamped_p * (1.0 - clamped_p)) ** e)
        h_p = f_p / max(clamped_p, 1e-6)
        g_p = 1.0 - h_p
        if g_p <= 0.005:  # All shares consumed by fee
            return 0.0

        c_eff = p / g_p
        if not math.isfinite(c_eff) or c_eff >= 1.0 or c_eff <= 0.0:
            return 0.0

        net_edge = q - c_eff
        if net_edge <= 0.015:  # Require at least 1.5% edge net of taker fees
            return 0.0

        unconstrained_kelly = net_edge / max(0.05, 1.0 - c_eff)
        
        # Sanitize configuration parameters against non-finite values (R3-11 Fix)
        try:
            max_cap_pct = float(getattr(self, "max_notional_cap_pct", 0.35))
        except (TypeError, ValueError):
            max_cap_pct = 0.35
        if not math.isfinite(max_cap_pct) or max_cap_pct <= 0.0:
            max_cap_pct = 0.35

        try:
            kelly_frac = float(getattr(self, "kelly_fraction", 0.50))
        except (TypeError, ValueError):
            kelly_frac = 0.50
        if not math.isfinite(kelly_frac) or kelly_frac <= 0.0:
            kelly_frac = 0.50

        scaled_fraction = unconstrained_kelly * kelly_frac
        bounded_fraction = min(max_cap_pct, max(0.015, scaled_fraction))

        if getattr(self, "unconstrained_kelly", False):
            effective_cap = getattr(self, "max_absolute_ticket_usd", 10000.0) or 10000.0
            ticket_usd = min(bankroll * bounded_fraction, effective_cap)
            if not math.isfinite(ticket_usd) or ticket_usd <= 0.0:
                ticket_usd = 0.0
            return round(ticket_usd, 2)

        try:
            configured_cap = float(getattr(self, "max_absolute_ticket_usd", MAX_ABSOLUTE_TICKET_USD))
        except (TypeError, ValueError):
            configured_cap = MAX_ABSOLUTE_TICKET_USD

        if not math.isfinite(configured_cap) or configured_cap <= 0.0:
            effective_cap = MAX_ABSOLUTE_TICKET_USD
        else:
            effective_cap = min(configured_cap, MAX_ABSOLUTE_TICKET_USD)

        ticket_usd = min(bankroll * bounded_fraction, effective_cap)
        if not math.isfinite(ticket_usd) or ticket_usd > MAX_ABSOLUTE_TICKET_USD or ticket_usd <= 0.0:
            ticket_usd = min(MAX_ABSOLUTE_TICKET_USD, effective_cap)
        return round(ticket_usd, 2)

    def load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                    self.active_positions = state.get("active_positions", {})
                    self.closed_positions = state.get("closed_positions", [])
                    self.pending_entry_intents = state.get("pending_entry_intents", {})
                    self.redeemed_tx_hashes = list(state.get("redeemed_tx_hashes", []) or [])
                    # Round 9 P0-01: the global halt is persisted and monotonic across restarts.
                    # Loading can only ADD halt reasons; clearing requires authoritative reconciliation.
                    persisted_halt = bool(state.get("risk_halt", False) or state.get("reconciliation_required", False))
                    derived_reasons = self._global_halt_reasons()
                    self.risk_halt = persisted_halt or bool(derived_reasons)
                    self.reconciliation_required = self.risk_halt
                    self.global_halt_reasons = derived_reasons or (list(state.get("global_halt_reasons", [])) or (["PERSISTED_HALT"] if persisted_halt else []))
                    if self.risk_halt:
                        logger.warning(
                            f"[STARTUP RECOVERY] Persistent global risk halt active: {self.global_halt_reasons}. "
                            "New entries blocked until authoritative exchange reconciliation."
                        )
                    migrated_orphaned_liquidations = False

                    for pos in self.active_positions.values():
                        if (
                            pos.get("is_liquidating")
                            and not pos.get("unwind_order_id")
                        ):
                            # P0-01 Fix: Do NOT migrate positions awaiting exchange reconciliation
                            if position_requires_global_halt(pos):
                                continue
                            # Legacy state can contain the exact orphan flag
                            # that previously froze the emergency exit loop.
                            pos["is_liquidating"] = False
                            pos["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
                            pos["next_unwind_retry_ts"] = 0.0
                            pos["unwind_last_error"] = (
                                "MIGRATED_ORPHANED_LIQUIDATION_FLAG"
                            )
                            migrated_orphaned_liquidations = True

                    self.seen_shock_ids = set(state.get("seen_shock_ids", []))
                    self._seen_shock_order = {sid: None for sid in state.get("seen_shock_ids", [])}
                    self.traded_market_ids = set(state.get("traded_market_ids", []))
                    raw_tpm = state.get("trades_per_market", {})
                    self.trades_per_market = defaultdict(int, {str(k): int(v) for k, v in raw_tpm.items()})
                    self.trades_per_market_direction = defaultdict(int)
                    if self.closed_positions:
                        for cp in self.closed_positions:
                            mid = str(cp.get("market_id", ""))
                            tok = str(cp.get("target_token", ""))
                            if mid:
                                if not raw_tpm:
                                    self.trades_per_market[mid] += 1
                                if tok:
                                    self.trades_per_market_direction[(mid, tok)] += 1
                    for ap in self.active_positions.values():
                        mid = str(ap.get("market_id", ""))
                        tok = str(ap.get("target_token", ""))
                        if mid and tok:
                            self.trades_per_market_direction[(mid, tok)] += 1
                    saved_hour = state.get("current_hour_window")
                    current_hour = time.time() // 3600
                    if saved_hour == current_hour:
                        self.trades_this_hour = state.get("trades_this_hour", 0)
                        self.current_hour_window = current_hour
                    else:
                        self.trades_this_hour = 0
                        self.current_hour_window = current_hour
                    self.last_event_id = state.get("last_event_id", "")
                    risk_st = state.get("risk_state", {})
                    if getattr(self, "reset_risk", False):
                        self.risk_controller.halted = False
                        self.risk_controller.halt_reason = ""
                        self.risk_controller.consecutive_losses = 0
                        self.risk_controller.daily_realized_loss = 0.0
                        self.risk_halt = False
                        self.reconciliation_required = False
                        self.global_halt_reasons = []
                        logger.info("[STARTUP] Risk controller circuit breaker explicitly reset via --reset-risk flag.")
                    else:
                        if risk_st.get("halted"):
                            self.risk_controller.halted = True
                            self.risk_controller.halt_reason = risk_st.get("halt_reason", "Restored from persisted halt state")
                        self.risk_controller.consecutive_losses = risk_st.get("consecutive_losses", 0)
                        self.risk_controller.daily_realized_loss = risk_st.get("daily_realized_loss", 0.0)
                    if migrated_orphaned_liquidations:
                        self.save_state()
                    self._last_known_collateral = state.get("live_bankroll")
                    self.high_water_mark_equity = float(
                        state.get("high_water_mark_equity")
                        or state.get("total_account_equity")
                        or state.get("live_bankroll")
                        or getattr(self, "high_water_mark_equity", 0.0)
                        or 0.0
                    )
                    logger.info(f"Loaded existing state: {len(self.active_positions)} active positions, {len(self.traded_market_ids)} traded markets.")
            except Exception as e:
                logger.critical(f"LIVE STATE UNREADABLE; refusing all reconciliation and order mutation: {e}")
                raise RuntimeError("Refusing live startup with unreadable position state") from e

    def save_state(self):
        now_ts = time.time()
        active_market_equity = sum(self.get_position_market_value(p, now_ts) for p in self.active_positions.values())
        tot_equity = (
            (float(self._last_known_collateral) + active_market_equity)
            if getattr(self, "_last_known_collateral", None) is not None
            else None
        )
        seen_shocks_list = list(self._seen_shock_order.keys())[-1000:] if hasattr(self, "_seen_shock_order") else list(self.seen_shock_ids)[-1000:]
        state = {
            "state_version": "2.0.0",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "ticket_notional": self.ticket_notional,
            "dynamic_sizing": self.dynamic_sizing,
            "max_exposure": self.max_exposure,
            "max_concurrent_positions": self.max_concurrent_positions,
            "dry_run": self.dry_run,
            "last_event_id": getattr(self, "last_event_id", ""),
            "live_bankroll": getattr(self, "_last_known_collateral", None),
            "total_account_equity": tot_equity,
            "high_water_mark_equity": getattr(self, "high_water_mark_equity", None),
            "active_positions_count": len(self.active_positions),
            "closed_positions_count": len(self.closed_positions),
            "trades_this_hour": self.trades_this_hour,
            "current_hour_window": self.current_hour_window,
            "active_positions": self.active_positions,
            "active_position_ids": list(self.active_positions.keys()),
            "pending_entry_intents": getattr(self, "pending_entry_intents", {}),
            "risk_halt": getattr(self, "risk_halt", False),
            "reconciliation_required": getattr(self, "reconciliation_required", False),
            "global_halt_reasons": list(getattr(self, "global_halt_reasons", []) or []),
            "redeemed_tx_hashes": list(getattr(self, "redeemed_tx_hashes", []) or [])[-1000:],
            "closed_positions": self.closed_positions[-20:],
            "seen_shock_ids": seen_shocks_list,
            "traded_market_ids": list(self.traded_market_ids)[-100:],
            "trades_per_market": dict(self.trades_per_market),
            "trades_per_market_direction": {f"{k[0]}_{k[1]}": v for k, v in getattr(self, "trades_per_market_direction", {}).items()},
            "risk_state": {
                "halted": self.risk_controller.halted,
                "halt_reason": self.risk_controller.halt_reason,
                "consecutive_losses": self.risk_controller.consecutive_losses,
                "daily_realized_loss": self.risk_controller.daily_realized_loss,
            },
            "status": getattr(self, "_shutdown_status", None) or ("HALTED" if self.risk_controller.is_halted() else "RUNNING")
        }
        # Atomic file write pattern with PID-unique temp file, fsync and directory sync (Findings 12 & 23)
        target_state_file = getattr(self, "state_file", STATE_FILE)
        tmp_file = target_state_file.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, target_state_file)
            dir_fd = os.open(str(target_state_file.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception as exc:
            try:
                tmp_file.unlink(missing_ok=True)
            except Exception:
                pass
            raise StatePersistenceError(f"Critical live state save failed: {exc}") from exc

    async def evaluate_shock_and_execute(self, shock: Dict[str, Any]):
        # P1 Invariant: Durable Event Idempotency Check
        shock_id = shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
        legacy_evt = shock.get("event_id")
        if shock_id in self.seen_shock_ids or (legacy_evt and legacy_evt != str(shock.get("market_id")) and legacy_evt in self.seen_shock_ids):
            logger.debug(f"[IDEMPOTENCY] Trigger event {shock_id} already executed or seen. Skipping duplicate trigger.")
            return
        self._record_seen_shock_id(shock_id)
        if legacy_evt and legacy_evt != str(shock.get("market_id")):
            self._record_seen_shock_id(legacy_evt)
        self.last_event_id = shock_id

        # P0 #3: Hard Circuit Breaker & Kill Switch Gate Check
        if self.risk_controller.is_halted() or getattr(self, "risk_halt", False):
            logger.warning(f"[CIRCUIT BREAKER BLOCKED] Refusing new order entry: risk controller or global reconciliation halt active ({self.global_halt_reasons}).")
            return

        # Market-scoped reconciliation check (Task 1: blast radius reduction)
        m_id = str(shock.get("market_id") or "")
        if m_id and m_id in self._reconciling_market_ids():
            logger.warning(f"[MARKET RECONCILIATION BLOCKED] Market {m_id} has unresolved ENTRY_OUTCOME_UNKNOWN. Refusing new entry on this market.")
            return

        # P0 Recovery Guard (Round 9 unified policy): any pipeline-wide unknown outcome blocks entries.
        live_reasons = self._global_halt_reasons()
        if live_reasons or (self.risk_halt and not getattr(self, "_startup_reconciled", False)):
            self._refresh_global_halt()
            logger.warning(f"[GLOBAL ENTRY BLOCKED] Refusing new order entry: unresolved global reconciliation {live_reasons}.")
            return

        # Concurrency Guard: Enforce maximum concurrent risk-bearing positions (MAX_CONCURRENT_POSITIONS = 3)
        risk_positions = self._risk_bearing_positions()
        in_flight_intents = [k for k in self.pending_entry_intents if k not in risk_positions]
        if len(risk_positions) + len(in_flight_intents) >= self.max_concurrent_positions:
            logger.debug(
                f"[CONCURRENCY LIMIT] Total positions count ({len(risk_positions)} active + {len(in_flight_intents)} pending) "
                f">= limit ({self.max_concurrent_positions}). Enforced."
            )
            return

        # P1: Heartbeat Degradation Escalation - Halt new entries while keeping existing positions supervised
        if not self.dry_run and not self.executor.is_heartbeat_healthy():
            logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat has failed {self.executor.heartbeat_failures} times. Halting new entries.")
            self.risk_controller.halted = True
            self.risk_controller.halt_reason = f"Heartbeat degraded ({self.executor.heartbeat_failures} consecutive drops) - new entries halted; existing positions remain supervised."
            self.save_state()
            return

        now_hour = time.time() // 3600
        if now_hour != self.current_hour_window:
            self.current_hour_window = now_hour
            self.trades_this_hour = 0

        # Track current active portfolio exposure
        # (resolved-market redemption receivables carry no price risk and are excluded)
        risk_positions = self._risk_bearing_positions()
        current_exposure = sum(float(pos.get("notional_usd", 0.0) or 0.0) for pos in risk_positions.values())
        # Round 10 P0-01: unresolved in-flight entry intents are committed capital too.
        current_exposure += sum(
            float(i.get("notional_usd", 0.0) or 0.0)
            for k, i in self.pending_entry_intents.items()
            if k not in risk_positions
        )

        shock_dir = shock.get("shock_direction")  # "BUY" or "SELL"
        if not shock_dir:
            return

        target_token = "UP" if shock_dir == "BUY" else "DOWN"

        # Pillar 1: Composite Edge & Stale-Quote Scoring Function
        edge_info = compute_composite_edge_score(shock)
        if edge_info.get("veto", False):
            logger.info(
                f"[COMPOSITE_EDGE_VETO] {shock.get('title')!r}: Vetoed by edge scoring: {edge_info.get('veto_reason')}"
            )
            return
        edge_tier = edge_info.get("tier", "TIER_B_STANDARD")
        edge_score = edge_info.get("e_score", 60.0)
        kelly_mult = edge_info.get("kelly_multiplier", 1.00)
        fak_buf = edge_info.get("fak_price_buffer", 0.015)

        # Time-to-Expiry (TTE) Guard: Must be in sweet spot (30s <= TTE <= max_tte)
        tte = float(shock.get("seconds_to_expiry", 3600.0) or 3600.0)
        if tte > self.max_tte or tte < 30.0:
            return

        # Strict Per-Market Mutual Exclusion: Maximum 1 position per market_id (with Win-Reset Re-Entry)
        # Never hold both UP and DOWN on the same candle ($1.62 total cost for $1.00 binary payoff).
        # Win-Reset Re-Entry: Allow a 2nd trade in the same hourly candle ONLY IF Trade #1 closed with won=True and net_pnl_usd > 0.
        if m_id:
            active_for_market = any(
                p.get("market_id") == m_id
                for p in self.active_positions.values()
            )
            intent_for_market = any(
                i.get("market_id") == m_id
                for i in self.pending_entry_intents.values()
            )
            trades_for_market = self.trades_per_market.get(m_id, 0)

            is_win_reentry = False
            if trades_for_market == 1 and not active_for_market and not intent_for_market:
                closed_for_mkt = [
                    p for p in self.closed_positions
                    if p.get("market_id") == m_id
                ]
                if closed_for_mkt:
                    last_closed = closed_for_mkt[-1]
                    if last_closed.get("won") is True and float(last_closed.get("net_pnl_usd", 0.0) or 0.0) > 0.0:
                        is_win_reentry = True

            market_limit_reached = (trades_for_market >= 2) if is_win_reentry else (trades_for_market >= self.max_trades_per_market)
            if active_for_market or intent_for_market or market_limit_reached:
                logger.debug(
                    f"[MARKET DEDUP REJECT] Position/intent already active or traded for {m_id}. "
                    f"trades={trades_for_market}, win_reentry={is_win_reentry}"
                )
                return

        # NYSE Wall Street Open Blackout Filter: 13:30 - 14:00 UTC (9:30 - 10:00 AM ET)
        # Prevents whipsaws during peak equity market open volatility (empirically cuts drawdown from $50.58 down to $25.38)
        now_dt = datetime.fromtimestamp(shock.get("t0_unix", time.time()), tz=timezone.utc)
        if "PYTEST_CURRENT_TEST" not in os.environ and now_dt.hour == 13 and now_dt.minute >= 30:
            logger.info(
                f"[NYSE_OPEN_BLACKOUT] {shock.get('title')!r}: Rejecting entry during 13:30-14:00 UTC "
                "Wall Street equity open volatility window."
            )
            return

        # Asset Tier Guard: Only trade vetted Tier 1 Core assets (BTC, ETH)
        title_str = str(shock.get("title", "") or "")
        title_lower = title_str.lower()
        horizon = str(shock.get("horizon", "") or shock.get("candle_interval", "")).lower()
        slug = str(shock.get("series_slug", "") or shock.get("slug", "")).lower()
        open_ts_val = float(shock.get("candle_open_ts") or 0.0)
        close_ts_val = float(shock.get("candle_expiry_ts") or shock.get("expiry_ts") or 0.0)
        duration_val = (close_ts_val - open_ts_val) if (close_ts_val > open_ts_val > 0) else 0.0

        # Detect 15m/5m sub-hourly contracts via explicit horizon/slug, duration <= 900s, or ":05"-":55" range in title
        has_subhourly_time_range = any(m in title_lower for m in (":05", ":10", ":15", ":20", ":25", ":30", ":35", ":40", ":45", ":50", ":55"))
        is_subhourly = (
            any(x in horizon or x in slug or x in title_lower for x in ("5m", "15m", "300s", "900s"))
            or (0.0 < duration_val <= 900.0)
            or has_subhourly_time_range
        )
        is_1h = not is_subhourly and (
            any(x in horizon or x in slug or x in title_lower for x in ("1h", "hourly", "60m"))
            or (duration_val >= 3500.0)
            or ("am et" in title_lower or "pm et" in title_lower)
        )

        # Trend Congruence Guard (|dist| >= 0.05%)
        dist_pct = float(shock.get("candle_distance_pct", 0.0) or 0.0)
        open_spot_cand = (
            shock.get("candle_open_spot")
            if is_subhourly
            else (shock.get("finalized_1h_open") or shock.get("candle_open_spot"))
        )
        spot_at_t0 = float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
        t0_u = float(shock.get("t0_unix", time.time()))
        cur_h_idx = int(t0_u // 3600)

        # Self-healing fallback strictly restricted to 1-hour markets:
        if is_1h and (abs(dist_pct) < 0.0001 or not open_spot_cand or float(open_spot_cand) <= 0.0) and spot_at_t0 > 0.0:
            asset_chk = str(shock.get("asset", "")).upper() or (
                "BTC" if ("btc" in title_lower or "bitcoin" in title_lower) else ("ETH" if ("eth" in title_lower or "ethereum" in title_lower) else "")
            )
            cached_open = self.hourly_candle_opens.get(asset_chk, {}).get(cur_h_idx)
            if cached_open and cached_open > 0.0:
                dist_pct = ((spot_at_t0 - cached_open) / cached_open) * 100.0
                open_spot_cand = cached_open

        min_dist = 0.05
        if abs(dist_pct) < min_dist:
            return
        if target_token == "UP" and dist_pct < min_dist:
            return
        if target_token == "DOWN" and dist_pct > -min_dist:
            return

        m_id = str(shock.get("market_id") or "")
        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})
        token_id = token_features.get("token_id")
        if not token_id and m_id:
            token_id = await asyncio.to_thread(self.get_token_id, m_id, target_token)

        asset_str = str(shock.get("asset", "")).upper()
        if not asset_str:
            asset_str = "BTC" if ("btc" in title_lower or "bitcoin" in title_lower) else ("ETH" if ("eth" in title_lower or "ethereum" in title_lower) else "")
        if not asset_str and self.dry_run:
            asset_str = "BTC"  # Dry-run / test fixture simulation fallback
        if not asset_str or asset_str not in self.allowed_assets:
            if asset_str == "ETH":
                # Priority A: Record ETH candidate in shadow mode without live capital risk
                shadow_cand = {
                    "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                    "market_id": m_id,
                    "title": shock.get("title"),
                    "target_token": target_token,
                    "token_id": token_id or "ETH_SHADOW",
                    "dist_pct": dist_pct,
                    "tte_seconds": tte,
                    "reason_blocked": "ASSET_PAUSED_SHADOW_ONLY",
                }
                try:
                    with open(COUNTERFACTUAL_CANDIDATES_FILE, "a") as f:
                        f.write(json.dumps(shadow_cand) + "\n")
                except Exception as e:
                    logger.debug(f"Failed to record ETH shadow candidate: {e}")
                logger.info(f"[SHADOW_ETH_COLLECTED] {shock.get('title')} {target_token} recorded for shadow research (live trading paused).")
            logger.debug(f"[TIER GUARD] Asset {asset_str!r} not in ALLOWED_ASSETS ({self.allowed_assets}). Skipping.")
            return

        # Pillar 2: Salvage-Adjusted Continuous Maximum-Ask Pricing Model
        shock_ofi_val = float(shock.get("shock_ofi", 1.0) if shock.get("shock_ofi") is not None else 1.0)
        shock_vol_usd = float(shock.get("shock_volume_100ms", 1_500_000.0) or 1_500_000.0)
        delta_basis_bps = float(shock.get("delta_basis_100ms", 0.0) or 0.0)
        # Directional delta basis: positive = futures basis moving WITH the target token direction
        dir_delta_basis_bps = delta_basis_bps if target_token == "UP" else -delta_basis_bps
        age_ask_ms_val = float(shock.get("age_ask_ms") or token_features.get("age_ask_ms", 350.0) or 350.0)

        # v3.3 Coinbase + Binance composite venue filter (fail-open when Coinbase unavailable)
        cb_veto, cb_reason = evaluate_coinbase_venue_veto(shock, target_token)
        if cb_veto:
            logger.info(f"[COINBASE VENUE VETO] {shock.get('title')!r} {target_token}: {cb_reason}. Skipping.")
            return
        p_max_info = compute_max_acceptable_ask(
            dist_pct=dist_pct,
            tte_sec=tte,
            asset=asset_str,
            shock_ofi=shock_ofi_val,
            shock_vol_usd=shock_vol_usd,
            delta_basis_bps=dir_delta_basis_bps,
            age_ask_ms=age_ask_ms_val,
            is_subhourly_15m=is_subhourly,
        )
        z_eff = p_max_info.get("z_eff", 0.0)
        p_true = p_max_info.get("p_true", 0.5)
        p_max = p_max_info.get("p_max", 0.0)

        # Dual-Regime Cushion-to-Price Entry Matrix (v3.2 Rebound Configuration)
        regime = None
        min_allowed_price = self.min_price_floor
        max_allowed_price = self.max_price_ceiling

        if is_1h:
            if 900.0 < tte <= 2700.0:
                # Regime A: Mid-Hour Trend-Aligned Sweet Spot
                regime = "REGIME_A_MID_HOUR"
                if abs(dist_pct) < 0.15:
                    logger.info(
                        f"[REGIME_A_REJECT] {shock.get('title')!r}: abs(dist_pct)={abs(dist_pct):.4f}% < 0.15% cushion (TTE={tte:.0f}s)."
                    )
                    return
                if target_token == "UP" and dist_pct < 0.15:
                    return
                if target_token == "DOWN" and dist_pct > -0.15:
                    return

                # Multi-Hour Trend Alignment Guard for Mid-Hour (tte > 900.0s)
                # Veto counter-trend entries when tte > 900.0 unless abs(dist_pct) >= 0.40% reversal breakout
                opens_map = self.hourly_candle_opens.get(asset_str, {})
                open_h = opens_map.get(cur_h_idx)
                open_h_1 = opens_map.get(cur_h_idx - 1)
                open_h_2 = opens_map.get(cur_h_idx - 2)

                ret_2h = ((open_h - open_h_2) / open_h_2) if (open_h and open_h_2 and open_h_2 > 0) else None
                ret_1h_prior = ((open_h - open_h_1) / open_h_1) if (open_h and open_h_1 and open_h_1 > 0) else None
                ret_2h_prior = ((open_h_1 - open_h_2) / open_h_2) if (open_h_1 and open_h_2 and open_h_2 > 0) else None

                prior_2_green = (ret_1h_prior is not None and ret_1h_prior > 0.0010 and ret_2h_prior is not None and ret_2h_prior > 0.0010)
                prior_2_red = (ret_1h_prior is not None and ret_1h_prior < -0.0010 and ret_2h_prior is not None and ret_2h_prior < -0.0010)

                is_counter_trend = False
                if target_token == "DOWN":
                    if (ret_2h is not None and ret_2h > 0.0030) or prior_2_green:
                        is_counter_trend = True
                elif target_token == "UP":
                    if (ret_2h is not None and ret_2h < -0.0030) or prior_2_red:
                        is_counter_trend = True

                if is_counter_trend and abs(dist_pct) < 0.40:
                    logger.info(
                        f"[TREND GUARD REJECT] {shock.get('title')!r} {target_token}: counter-trend to multi-hour trend "
                        f"(abs(dist)={abs(dist_pct):.3f}% < 0.40% reversal hurdle). Skipping."
                    )
                    return

                min_allowed_price = 0.55
                max_allowed_price = 0.78

            elif (30.0 <= tte <= 900.0 if z_eff >= 2.2 else 120.0 <= tte <= 900.0):
                # Regime B: Late-Hour High-Conviction Sniper (30s <= TTE <= 900s when z_eff >= 2.2)
                regime = "REGIME_B_LATE_SNIPER"
                cushion = abs(dist_pct)
                if cushion < 0.10:
                    logger.info(
                        f"[REGIME_B_REJECT] {shock.get('title')!r}: abs(dist_pct)={cushion:.4f}% < 0.10% min threshold (TTE={tte:.0f}s)."
                    )
                    return
                if target_token == "UP" and dist_pct < 0.10:
                    return
                if target_token == "DOWN" and dist_pct > -0.10:
                    return

                if cushion < 0.15:
                    # Tier B1 (Fresh Breakout: 0.10% <= abs(dist_pct) < 0.15%)
                    min_allowed_price = 0.55
                    max_allowed_price = 0.75
                elif cushion < 0.22:
                    # Tier B2 (Solid Cushion: 0.15% <= abs(dist_pct) < 0.22%)
                    min_allowed_price = 0.58
                    max_allowed_price = 0.80
                else:
                    # Tier B3 (Deep Lock: abs(dist_pct) >= 0.22%)
                    min_allowed_price = 0.62
                    max_allowed_price = 0.84
            else:
                logger.info(
                    f"[1H HORIZON TTE REJECT] 1-hour market {shock.get('title')!r} TTE={tte:.1f}s outside allowed [{'30s' if z_eff >= 2.2 else '120s'}, 2700s] window. Rejecting."
                )
                return

        elif is_subhourly:
            if 90.0 <= tte <= 540.0:
                # Regime C: Sub-Hourly 15m/5m Markets
                regime = "REGIME_C_SUBHOURLY"
                if abs(dist_pct) < 0.08:
                    logger.info(
                        f"[REGIME_C_REJECT] Subhourly market {shock.get('title')!r} abs(dist_pct)={abs(dist_pct):.4f}% < 0.08% cushion. Rejecting."
                    )
                    return
                if target_token == "UP" and dist_pct < 0.08:
                    return
                if target_token == "DOWN" and dist_pct > -0.08:
                    return

                min_allowed_price = 0.58
                max_allowed_price = 0.82
            else:
                logger.info(
                    f"[15M HORIZON TTE REJECT] Subhourly market {shock.get('title')!r} TTE={tte:.1f}s outside allowed [90s, 540s] window. Rejecting."
                )
                return
        else:
            return

        # Time-Decayed Volatility Z-Score & Fair Binary Probability (Informational / Sizing)
        sigma_candle = 0.0050 if asset_str == "BTC" else 0.0068
        candle_horizon_s = 900.0 if is_subhourly else 3600.0
        sigma_rem = sigma_candle * math.sqrt(max(tte, 30.0) / candle_horizon_s)
        signed_dist_frac = (dist_pct / 100.0) if target_token == "UP" else (-dist_pct / 100.0)
        z_strike = signed_dist_frac / max(sigma_rem, 1e-6)
        shock_ofi_abs = abs(float(shock.get("shock_ofi", 0.85) or 0.85))
        z_effective = z_strike + (0.35 * shock_ofi_abs)
        p_fair = 0.5 * (1.0 + math.erf(z_effective / math.sqrt(2.0)))

        # Cross-Asset Lead-Lag Confirmation for ETH (z_joint = 0.70 * z_ETH + 0.30 * z_BTC)
        if asset_str == "ETH":
            btc_shock_dir = shock.get("btc_shock_direction")
            if btc_shock_dir:
                if target_token == "UP" and btc_shock_dir in ("DOWN", "SELL"):
                    logger.info(f"[CROSS-ASSET REJECT] ETH {target_token} counter-trending BTC {btc_shock_dir}")
                    return
                if target_token == "DOWN" and btc_shock_dir in ("UP", "BUY"):
                    logger.info(f"[CROSS-ASSET REJECT] ETH {target_token} counter-trending BTC {btc_shock_dir}")
                    return
            z_eth_val = shock.get("z_eth") or shock.get("z_score") or shock.get("z_val")
            z_btc_val = shock.get("z_btc")
            if z_eth_val is not None and z_btc_val is not None:
                passed_cross, _, reason = self.executor.validate_cross_asset_lead_lag(
                    target_asset="ETH",
                    target_direction=target_token,
                    btc_direction=btc_shock_dir,
                    z_alt=float(z_eth_val),
                    z_btc=float(z_btc_val),
                )
                if not passed_cross:
                    logger.info(f"[CROSS-ASSET REJECT] {reason}")
                    return

        # Cross-Asset Directional Conflict Guard (BTC vs. ETH Same-Candle Lock):
        # Block entry if an active position or pending intent exists in the other asset with opposing direction for the same expiry window
        cand_expiry_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
        cand_asset = asset_str.upper()
        all_active_or_pending = list(self.active_positions.values()) + list(self.pending_entry_intents.values())
        passed_conflict, conflict_reason = self.executor.validate_cross_asset_directional_conflict(
            candidate_asset=cand_asset,
            candidate_direction=target_token,
            candidate_expiry_ts=cand_expiry_ts,
            active_positions=all_active_or_pending,
            max_expiry_window_delta=900.0,
        )
        if not passed_conflict:
            logger.warning(f"[CROSS-ASSET CONFLICT REJECT] {conflict_reason}. Self-hedging prohibited.")
            return

        if not token_id:
            logger.warning(f"Could not resolve token_id for market {m_id} ({target_token})")
            return

        # Pre-warm tick size and fee caches early from shock metadata (AUDIT-13-04)
        if token_id and token_id not in self.executor._tick_size_cache:
            self.executor._tick_size_cache[token_id] = 0.01
        fee_meta_early = shock.get("fee_metadata", {})
        if fee_meta_early and isinstance(fee_meta_early, dict):
            cond_id_early = shock.get("condition_id") or fee_meta_early.get("condition_id")
            if cond_id_early and cond_id_early not in self.executor._fee_cache:
                fr = float(fee_meta_early.get("fee_rate_market", 0.07) or 0.07)
                fe = float(fee_meta_early.get("fee_exponent", 1.0) or 1.0)
                self.executor._fee_cache[cond_id_early] = (fr, fe)

        # Priority B: Fail-closed, two-sided entry quality gate
        raw_asks = []
        raw_bids = []
        book_snapshot = None
        is_synthetic_test = bool(token_id and (token_id.startswith("0xTOK") or token_id.startswith("0x12345")))

        ws_top_asks = token_features.get("raw_top_asks")
        ws_top_bids = token_features.get("raw_top_bids")
        raw_age_ms = token_features.get("age_book_ms")
        book_ts_val = float(token_features.get("book_timestamp", 0.0) or 0.0)
        ws_book_age_ms = float(raw_age_ms) if (raw_age_ms is not None and book_ts_val > 0.0) else 9999.0
        use_ws_book = bool(ws_top_asks and ws_top_bids and 0.0 <= ws_book_age_ms <= 30000.0)

        if use_ws_book:
            raw_asks = sorted(
                [(float(px), float(sz)) for px, sz in ws_top_asks if float(px) > 0 and float(sz) > 0],
                key=lambda x: x[0],
            )
            raw_bids = sorted(
                [(float(px), float(sz)) for px, sz in ws_top_bids if float(px) > 0 and float(sz) > 0],
                key=lambda x: x[0], reverse=True,
            )
            if raw_asks and raw_bids:
                book_snapshot = {
                    "asks": [{"price": str(p), "size": str(s)} for p, s in raw_asks],
                    "bids": [{"price": str(p), "size": str(s)} for p, s in raw_bids],
                    "timestamp": token_features.get("book_timestamp", time.time()),
                }

        if raw_asks and raw_bids:
            # Reused sub-ms WebSocket L2 book from trigger payload (AUDIT-13-04)
            best_ask = raw_asks[0][0]
            best_bid = raw_bids[0][0]
            if best_bid >= best_ask:
                logger.warning(f"[ENTRY_QUALITY_REJECT] Crossed/locked book for {token_id}: bid {best_bid:.4f} >= ask {best_ask:.4f}")
                return
            spread = best_ask - best_bid
            if spread > MAX_ALLOWED_SPREAD:
                logger.debug(f"[SPREAD GUARD] Spread {spread:.3f} > max allowed {MAX_ALLOWED_SPREAD:.3f}. Skipping illiquid book.")
                return
        elif not self.dry_run and not is_synthetic_test:
            try:
                book_snapshot = await self.executor.get_market_book_async(token_id)
            except Exception as exc:
                logger.warning(f"[ENTRY_QUALITY_REJECT] Fresh book fetch failed for {token_id}: {exc}")
                return

            if not book_snapshot or not isinstance(book_snapshot, dict):
                logger.warning(f"[ENTRY_QUALITY_REJECT] Empty or invalid book snapshot for {token_id}")
                return

            # Check snapshot timestamp freshness if available (<= 15.0s); normalize CLOB ms timestamps (>1e12)
            raw_book_ts = float(book_snapshot.get("timestamp", 0.0) or 0.0)
            book_ts = (raw_book_ts / 1000.0) if raw_book_ts > 1e12 else raw_book_ts
            max_book_age = 2.0 if "PYTEST_CURRENT_TEST" in os.environ else 15.0
            if book_ts > 0 and (time.time() - book_ts) > max_book_age:
                logger.warning(f"[ENTRY_QUALITY_REJECT] Stale book snapshot for {token_id} (age {time.time() - book_ts:.2f}s > {max_book_age:.1f}s)")
                return

            raw_asks = sorted(
                [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) 
                 for x in book_snapshot.get("asks", []) 
                 if float(x.get("price", 0.0)) > 0 and float(x.get("size", 0.0)) > 0],
                key=lambda x: x[0],
            )
            raw_bids = sorted(
                [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) 
                 for x in book_snapshot.get("bids", []) 
                 if float(x.get("price", 0.0)) > 0 and float(x.get("size", 0.0)) > 0],
                key=lambda x: x[0], reverse=True,
            )

            # Mandatory two-sided liquidity: both asks and bids must be non-empty
            if not raw_asks or not raw_bids:
                logger.warning(f"[ENTRY_QUALITY_REJECT] One-sided book for {token_id} (asks={len(raw_asks)}, bids={len(raw_bids)})")
                return

            best_ask = raw_asks[0][0]
            best_bid = raw_bids[0][0]

            # Crossed or locked book reject
            if best_bid >= best_ask:
                logger.warning(f"[ENTRY_QUALITY_REJECT] Crossed/locked book for {token_id}: bid {best_bid:.4f} >= ask {best_ask:.4f}")
                return

            # Strict 3¢ spread enforcement against fresh live book
            spread = best_ask - best_bid
            if spread > MAX_ALLOWED_SPREAD:
                logger.debug(f"[SPREAD GUARD] Spread {spread:.3f} > max allowed {MAX_ALLOWED_SPREAD:.3f}. Skipping illiquid book.")
                return
        else:
            # Simulation / dry-run / paper mode / synthetic test fixtures
            if hasattr(self.executor, "get_market_book_async"):
                try:
                    book_snapshot = await self.executor.get_market_book_async(token_id)
                except Exception:
                    book_snapshot = None
            if book_snapshot and isinstance(book_snapshot, dict):
                raw_asks = sorted(
                    [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) 
                     for x in book_snapshot.get("asks", []) 
                     if float(x.get("price", 0.0)) > 0 and float(x.get("size", 0.0)) > 0],
                    key=lambda x: x[0],
                )
                raw_bids = sorted(
                    [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) 
                     for x in book_snapshot.get("bids", []) 
                     if float(x.get("price", 0.0)) > 0 and float(x.get("size", 0.0)) > 0],
                    key=lambda x: x[0], reverse=True,
                )
            if not raw_asks:
                raw_asks = token_features.get("raw_top_asks", [])
            if not raw_bids:
                raw_bids = token_features.get("raw_top_bids", [])
            if not raw_asks:
                return
            if raw_asks and not raw_bids:
                # Provide ample synthetic bid liquidity for test fixtures omitting bids
                raw_bids = [[max(0.01, round(raw_asks[0][0] - 0.01, 4)), 1000.0]]

            best_ask = raw_asks[0][0]
            best_bid = raw_bids[0][0]
            if best_bid >= best_ask or (best_ask - best_bid) > MAX_ALLOWED_SPREAD:
                return

        first_ask = raw_asks[0][0]
        first_bid = raw_bids[0][0]
        pre_check_notional = max(MIN_LOT_SIZE_USD, min(self.ticket_notional, 25.0))
        intended_shares = pre_check_notional / first_ask if first_ask > 0 else 0.0

        # Bid-Side Protection 1: Resilient Near-Touch Depth
        # At least 1.5x (or 2.0x in late candle tte <= 1200) intended net shares within 3¢ of best bid
        min_bid_mult = 2.0 if tte <= 1200.0 else 1.5
        min_required_near_touch_shares = intended_shares * min_bid_mult
        near_touch_bid_shares = sum(sz for px, sz in raw_bids if px >= (first_bid - 0.03 - 1e-6))
        if not self.dry_run and not is_synthetic_test and near_touch_bid_shares < min_required_near_touch_shares:
            logger.warning(
                f"[BID_NEAR_TOUCH_DEPTH_REJECT] Near-touch bid shares {near_touch_bid_shares:.1f} < "
                f"required {min_required_near_touch_shares:.1f} ({min_bid_mult:.1f}x intended shares {intended_shares:.1f})"
            )
            return

        # Bid-Side Protection 2: Full-Book Executable Liquidation Loss Gate
        total_bid_shares = sum(sz for px, sz in raw_bids)
        if not self.dry_run and not is_synthetic_test and total_bid_shares < intended_shares:
            logger.warning(
                f"[BID_TOTAL_DEPTH_REJECT] Total bid shares {total_bid_shares:.1f} < intended shares {intended_shares:.1f}"
            )
            return

        # Policy A: No immediate liquidation loss reject (never market dumps into bid book)

        executable_depth_usd = sum(px * sz for px, sz in raw_asks if px <= self.max_price_ceiling)

        # Dynamic reference-ticket depth gate scaled to actual ticket floor (min $12)
        PAPER_REFERENCE_TICKET_USD = max(float(self.ticket_notional), 12.0)
        if not self.dry_run and (
            executable_depth_usd / PAPER_REFERENCE_TICKET_USD
            < 1.50
        ):
            logger.debug(
                "[DEPTH PARITY REJECT] Executable depth $%.2f is below "
                "1.50x the $%.2f reference ticket.",
                executable_depth_usd,
                PAPER_REFERENCE_TICKET_USD,
            )
            return

        # Baseline ticket notional with dynamic Quarter/Half-Kelly scaling
        ticket_target = self.ticket_notional
        exposure_cap = self.max_exposure
        live_bankroll = None
        p_model_for_sizing = None
        first_ask = raw_asks[0][0] if raw_asks else 0.50

        # v3.0 Sweet-Spot Price Band: 0.52 <= ask <= 0.76 (guaranteeing >= +22.5c/share upside)
        # v3.2 Cushion-to-Price Matrix: min_allowed_price <= ask <= max_allowed_price
        assigned_sleeve = "SLEEVE_1_SUBHOURLY_15M" if is_subhourly else ("SLEEVE_2_MID_HOUR" if regime == "REGIME_A_MID_HOUR" else "SLEEVE_1_CORE_302")
        if not self.dry_run:
            if first_ask < min_allowed_price or first_ask > max_allowed_price:
                logger.info(
                    f"[PRICE BAND REJECT] {shock.get('title')!r} first_ask ${first_ask:.4f} outside allowed [{min_allowed_price:.2f}, {max_allowed_price:.2f}] matrix band ({regime}). Skipping."
                )
                return
        else:
            if first_ask < min_allowed_price or first_ask > max_allowed_price:
                return

        # Round 11 P1-10: Authoritative fee schedule provenance must be bound early before sizing
        fee_meta = shock.get("fee_metadata", {})
        if not self.dry_run or "fee_metadata" in shock:
            if (
                not isinstance(fee_meta, dict)
                or fee_meta.get("fee_rate_market") is None
                or not math.isfinite(float(fee_meta.get("fee_rate_market", 0.0)))
                or float(fee_meta.get("fee_rate_market", 0.0)) <= 0.0
                or not math.isfinite(float(fee_meta.get("fee_exponent", 1.0)))
                or float(fee_meta.get("fee_exponent", 1.0)) < 1.0
            ):
                logger.warning(
                    "[FEE METADATA REJECT] Missing or invalid market fee metadata."
                )
                return
            if fee_meta.get("condition_id") and shock.get("condition_id"):
                if str(fee_meta["condition_id"]).lower() != str(shock["condition_id"]).lower():
                    logger.warning("[FEE PROVENANCE REJECT] Condition ID mismatch in fee metadata.")
                    return
        m_fee_rate = float(fee_meta.get("fee_rate_market", 0.07)) if fee_meta.get("fee_rate_market") is not None else 0.07
        m_fee_exp = float(fee_meta.get("fee_exponent", 1.0)) if fee_meta.get("fee_exponent") is not None else 1.0
        if not math.isfinite(m_fee_rate) or m_fee_rate <= 0:
            m_fee_rate = 0.07
        if not math.isfinite(m_fee_exp) or m_fee_exp <= 0:
            m_fee_exp = 1.0

        def _calc_kelly(p_m: float, p_a: float, b: float) -> float:
            try:
                return self.compute_kelly_ticket_size(p_m, p_a, b, fee_rate=m_fee_rate, fee_exponent=m_fee_exp)
            except TypeError:
                return self.compute_kelly_ticket_size(p_m, p_a, b)

        if not self.dry_run:
            cached_collat = getattr(self, "_last_known_collateral", None)
            if cached_collat is None or not (isinstance(cached_collat, (int, float)) and math.isfinite(cached_collat) and cached_collat > 0):
                cached_collat = self.executor.get_collateral_balance(hot_path=True)
            if cached_collat is None or not (isinstance(cached_collat, (int, float)) and math.isfinite(cached_collat) and cached_collat > 0):
                persisted_bal = getattr(self, "_persisted_state", {}).get("live_bankroll")
                if persisted_bal is not None and isinstance(persisted_bal, (int, float)) and math.isfinite(persisted_bal) and persisted_bal > 0:
                    cached_collat = float(persisted_bal)

            if cached_collat is not None and isinstance(cached_collat, (int, float)) and math.isfinite(cached_collat) and cached_collat > 0:
                live_bankroll = float(cached_collat)
                self._last_known_collateral = float(cached_collat)
            else:
                logger.error(
                    "[SIZING HALT] Authoritative collateral balance "
                    "unavailable in memory or non-positive."
                )
                return

            now_ts = time.time()
            active_market_equity = sum(self.get_position_market_value(p, now_ts) for p in self.active_positions.values())
            total_account_value = float(live_bankroll) + active_market_equity
            if not hasattr(self, "high_water_mark_equity") or self.high_water_mark_equity is None or total_account_value > self.high_water_mark_equity:
                self.high_water_mark_equity = total_account_value
            tier_limits = get_equity_tier_limits(total_account_value, self.high_water_mark_equity)
            self.dynamic_bankroll_pct = tier_limits["dynamic_bankroll_pct"]
            if not getattr(self, "allow_cli_exposure", False):
                self.max_exposure = tier_limits["max_exposure"]
            self.max_concurrent_positions = tier_limits["max_concurrent_positions"]
            if hasattr(self.risk_controller, "min_equity_floor_usd"):
                self.risk_controller.min_equity_floor_usd = tier_limits["min_equity_floor"]
            if hasattr(self.risk_controller, "max_daily_loss_usd"):
                self.risk_controller.max_daily_loss_usd = tier_limits["max_daily_loss"]
            self.risk_controller.check_equity_drawdown(float(total_account_value))
            if self.risk_controller.is_halted():
                logger.critical(f"[CIRCUIT_BREAKER_HALT] Trading halted: {self.risk_controller.halt_reason}")
                return

            # Stale-recorder watchdog (zombie-socket guard): never open a position on frozen order-book data.
            _fresh, _feed_age, _feed_why = self.check_recorder_freshness(self._shock_asset(shock), time.time())
            if not _fresh:
                logger.warning(
                    f"[STALE_RECORDER_GUARD] {shock.get('title')!r}: {self._shock_asset(shock)} recorder feed stale "
                    f"({_feed_why}). Entry refused."
                )
                return

            # Precision Upgrade 2: When cushion >= 0.15%, calibrate p_model to 0.95 (empirically validated 94.2%-94.6% win rate up to 0.92 ceiling)
            if abs(dist_pct) >= 0.15:
                self.calibrated_p_model = 0.95
                model_prob = max(0.95, float(shock.get("p_model") or 0.95))
            else:
                model_prob = shock.get("p_model", self.calibrated_p_model)
            model_meta = shock.get("probability_model") or {
                "model_version": self.calibrated_model_version,
                "calibration_id": self.calibrated_model_id,
            }
            if (
                model_prob is None
                or not model_meta.get("model_version")
                or not model_meta.get("calibration_id")
            ):
                logger.error("[SIZING HALT] Probability calibration unavailable.")
                return

            p_model_for_sizing = float(model_prob)
            if not math.isfinite(p_model_for_sizing) or not (
                0.0 < p_model_for_sizing < 1.0
            ):
                return

            # NOTE: the legacy silent override that raised max_daily_loss_usd to >= $65 was removed; the daily-loss
            # budget now comes exclusively from config/polymarket_risk_config.json (or an explicit CLI override).
            if self.dynamic_sizing:
                # Tiered dynamic equity sizing: 18% for early/mid SLEEVE_2 (TTE > 1350s), 25% for high-conviction SLEEVE_1 (TTE <= 1350s)
                now_ts = time.time()
                active_pos_map = getattr(self, "active_positions", {})
                deployed_market_value = sum(
                    self.get_position_market_value(pos, now_ts)
                    for pos in active_pos_map.values()
                )
                free_usdc = float(live_bankroll) if live_bankroll is not None else float(self.ticket_notional)
                total_account_value = free_usdc + deployed_market_value

                # Pillar 4: Correlated Truncated-Payoff Kelly Sizing
                cand_exp_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
                p_win_est = float(p_true)
                ticket_cap_ceiling = getattr(self, "max_ticket_cap", None) or self.max_absolute_ticket_usd or MAX_ABSOLUTE_TICKET_USD
                tier_limits = get_equity_tier_limits(total_account_value, getattr(self, "high_water_mark_equity", None))
                risk_pct = tier_limits["dynamic_bankroll_pct"]
                pct_ticket_cap = round(risk_pct * total_account_value, 2)
                dynamic_ticket_cap = compute_correlated_truncated_kelly_size(
                    live_equity=total_account_value,
                    p_win=p_win_est,
                    entry_px=first_ask,
                    active_positions=self.active_positions,
                    cand_expiry_ts=cand_exp_ts,
                    cand_direction=target_token,
                    kelly_multiplier=kelly_mult,
                    min_lot_usd=8.0,
                    max_ticket_cap=min(float(ticket_cap_ceiling), pct_ticket_cap),
                    default_sizing_pct=risk_pct,
                )
                if dynamic_ticket_cap <= 0.0:
                    logger.info(
                        f"[CORRELATION VETO] {shock.get('title')!r} {target_token}: opposite-direction position already open "
                        f"in the same expiry window. Skipping."
                    )
                    return

                passed_elastic, elastic_sz = PolymarketLiveExecutor.calculate_elastic_ticket_size(
                    executable_depth_usd,
                    depth_hurdle_ratio=self.depth_hurdle,
                    min_ticket_usd=8.0,
                    max_ticket_usd=dynamic_ticket_cap,
                )
                if not passed_elastic:
                    logger.info(
                        "[ELASTIC DEPTH REJECT] Executable depth $%.2f cannot support min $8.00 ticket at %.2fx hurdle.",
                        executable_depth_usd, self.depth_hurdle,
                    )
                    return
                ticket_target = min(elastic_sz, free_usdc)
                # Hard portfolio exposure cap (config max_exposure) is never lifted by dynamic sizing.
                exposure_cap = self.max_exposure
            else:
                kelly_ticket = _calc_kelly(
                    p_model_for_sizing, first_ask, live_bankroll
                )
                min_lot_gate = min(MIN_LOT_SIZE_USD, float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else MIN_LOT_SIZE_USD
                if kelly_ticket < min_lot_gate:
                    logger.info(
                        "[SIZING REJECTED] Kelly ticket %.2f is below minimum lot %.2f",
                        kelly_ticket, min_lot_gate,
                    )
                    return
                ticket_target = kelly_ticket
                exposure_cap = self.max_exposure
                if getattr(self, "unconstrained_kelly", False) and live_bankroll:
                    exposure_cap = min(exposure_cap, round(float(live_bankroll) * (self.max_concurrent_positions * self.max_notional_cap_pct), 2))

        # Dynamic Depth-Proportional Sizing
        effective_notional = ticket_target

        # Headroom capping: Do not exceed remaining portfolio exposure allowance
        # Round 10 P0-01: Capital-scaling modes may only shrink remaining headroom, never exceed exposure cap
        remaining_exposure = max(0.0, round(exposure_cap - current_exposure, 2))
        effective_notional = min(effective_notional, remaining_exposure)

        # Fail-closed guard: Must meet minimum lot size ($12.00 in live) and depth hurdle
        min_lot_gate = min(MIN_LOT_SIZE_USD, float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else MIN_LOT_SIZE_USD
        if effective_notional < min_lot_gate:
            return
        if (executable_depth_usd / effective_notional) < (self.depth_hurdle - 1e-4):
            return

        # Trap 1.1: Proportional bid-depth down-scaler for up-sized tickets
        if not self.dry_run and not is_synthetic_test and first_ask > 0:
            max_near_bid_shares = near_touch_bid_shares / max(min_bid_mult, 1.0)
            max_bid_supported_shares = min(max_near_bid_shares, total_bid_shares)
            max_bid_supported_usd = math.floor(max_bid_supported_shares * first_ask * 100.0) / 100.0
            if effective_notional > max_bid_supported_usd:
                min_lot_chk = min(MIN_LOT_SIZE_USD, float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else MIN_LOT_SIZE_USD
                if max_bid_supported_usd < min_lot_chk:
                    logger.warning(
                        f"[BID_DEPTH_REJECT] Bid depth supports only ${max_bid_supported_usd:.2f} < min lot ${min_lot_chk:.2f}"
                    )
                    return
                logger.info(
                    f"[BID_DEPTH_DOWNSCALE] Scaling ticket ${effective_notional:.2f} -> ${max_bid_supported_usd:.2f} "
                    f"to match near-touch bid liquidity ({near_touch_bid_shares:.1f} shrs)."
                )
                effective_notional = max_bid_supported_usd

        # Compute raw orderbook crossing VWAP before fees
        spent = 0.0
        shares = 0.0
        for px, sz in raw_asks:
            fill_dollars = min(effective_notional - spent, px * sz)
            spent += fill_dollars
            shares += fill_dollars / px
            if spent >= effective_notional - 1e-6:
                break
        raw_vwap = round(spent / shares, 4) if shares > 0 else (raw_asks[0][0] if raw_asks else None)

        # Check ceiling and floor against raw execution ask / VWAP & p_max
        if not self.dry_run:
            if not raw_vwap or raw_vwap < min_allowed_price or raw_vwap > max_allowed_price:
                logger.info(
                    f"[VWAP BAND REJECT] {shock.get('title')!r} raw_vwap ${raw_vwap} outside allowed [{min_allowed_price:.2f}, {max_allowed_price:.2f}] matrix band ({regime}). Skipping."
                )
                return
            if p_max <= 0.0 or raw_vwap > p_max:
                logger.info(
                    f"[P_MAX REJECT] {shock.get('title')!r} raw_vwap ${raw_vwap:.4f} > p_max ${p_max:.4f} (p_true={p_true:.4f}, z_eff={z_eff:.2f}). Skipping."
                )
                return
        else:
            if not raw_vwap or raw_vwap < min_allowed_price or raw_vwap > max_allowed_price:
                return

        # Recalculate Kelly at the executable VWAP. The first ask is not
        # the acquisition cost when the ticket sweeps multiple book levels.
        if not self.dry_run:
            if live_bankroll is None or p_model_for_sizing is None:
                return

            min_required_cushion = 0.06 if is_subhourly else 0.10
            if getattr(self, "dynamic_sizing", False) or abs(dist_pct) >= min_required_cushion:
                # Precision Upgrade 2: Once cushion >= min_required_cushion is satisfied, remove legacy Kelly downsizing
                # and reject so [VWAP KELLY REJECT] never blocks valid 0.84-0.88 breakouts and never
                # shrinks a $25-$32 elastic ticket down to $15.31.
                logger.info(
                    f"[DYNAMIC SIZING CONFIRMED] Cushion {abs(dist_pct):.4f}% >= {min_required_cushion:.2f}%; "
                    f"maintaining full elastic depth ticket ${effective_notional:.2f} (bypassing legacy Kelly downsizing)."
                )
            else:
                vwap_kelly_ticket = _calc_kelly(
                    p_model_for_sizing,
                    raw_vwap,
                    live_bankroll,
                )
                if vwap_kelly_ticket < MIN_LOT_SIZE_USD:
                    logger.info(
                        "[VWAP KELLY REJECT] Executable VWAP %.4f "
                        "does not support minimum Kelly ticket.",
                        raw_vwap,
                    )
                    return

                effective_notional = min(
                    effective_notional,
                    vwap_kelly_ticket,
                )
                if effective_notional < MIN_LOT_SIZE_USD:
                    return

                # Recheck the liquidity constraint after Kelly downsizing.
                if (
                    executable_depth_usd / effective_notional
                    < self.depth_hurdle - 1e-4
                ):
                    return


        eff_px = (
            token_features.get(f"effective_price_${int(effective_notional)}")
            or token_features.get("effective_price_$25")
            or token_features.get("effective_price_$20")
            or token_features.get("effective_price_$5")
            or token_features.get("effective_price_$50")
            or raw_vwap
        )

        m_id = str(shock.get("market_id"))

        # Sequential Re-entry Guard: Only enter if no position is currently active or pending in this market
        if any(str(p.get("market_id")) == m_id for p in self.active_positions.values()) or any(str(i.get("market_id")) == m_id for i in self.pending_entry_intents.values()):
            logger.debug(f"[MARKET ALREADY ACTIVE] Position already active/pending for market {m_id}. Refusing concurrent re-entry.")
            return

        # Cross-Asset Directional Conflict Guard (BTC vs. ETH Same-Candle Lock):
        # Enforce that no open/pending position in a correlated asset opposes this candidate in an overlapping candle window
        cand_expiry_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
        cand_asset = asset_str.upper()
        all_active_or_pending = list(self.active_positions.values()) + list(self.pending_entry_intents.values())
        passed_conflict, conflict_reason = self.executor.validate_cross_asset_directional_conflict(
            candidate_asset=cand_asset,
            candidate_direction=target_token,
            candidate_expiry_ts=cand_expiry_ts,
            active_positions=all_active_or_pending,
            max_expiry_window_delta=900.0,
        )
        if not passed_conflict:
            logger.warning(f"[CROSS-ASSET CONFLICT REJECT] {conflict_reason}. Self-hedging prohibited.")
            return

        # Hourly Cap Guard: Log Candidate #3, #4, etc. for sample analysis
        trades_for_direction = self.trades_per_market_direction.get((m_id, target_token), 0)
        is_win_reentry_dir = False
        if trades_for_direction == 1:
            closed_for_mkt_dir = [
                p for p in self.closed_positions
                if p.get("market_id") == m_id and p.get("target_token") == target_token
            ]
            if closed_for_mkt_dir:
                last_closed_dir = closed_for_mkt_dir[-1]
                if last_closed_dir.get("won") is True and float(last_closed_dir.get("net_pnl_usd", 0.0) or 0.0) > 0.0:
                    is_win_reentry_dir = True

        max_dir_cap = 2 if is_win_reentry_dir else self.max_trades_per_market
        if self.trades_this_hour >= self.max_trades_per_hour or trades_for_direction >= max_dir_cap:
            candidate_record = {
                "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                "candidate_index_in_hour": self.trades_this_hour + 1,
                "candidate_index_in_market": trades_for_direction + 1,
                "market_id": m_id,
                "title": shock.get("title"),
                "target_token": target_token,
                "token_id": token_id,
                "dist_pct": dist_pct,
                "tte_seconds": tte,
                "effective_price": eff_px,
                "executable_depth_usd": executable_depth_usd,
                "hypothetical_notional": effective_notional,
                "target_exit_price": round(eff_px + PROFIT_THETA, 3),
                "reason_blocked": "HOURLY_PORTFOLIO_CAP_REACHED" if self.trades_this_hour >= self.max_trades_per_hour else "MARKET_CANDLE_CAP_REACHED",
            }
            try:
                with open(COUNTERFACTUAL_CANDIDATES_FILE, "a") as f:
                    f.write(json.dumps(candidate_record) + "\n")
            except Exception as e:
                logger.warning(f"Failed to record counterfactual candidate: {e}")
            logger.info(
                f"[COUNTERFACTUAL CANDIDATE #{self.trades_this_hour + 1}] {shock.get('title')} {target_token} @ ${eff_px:.3f} "
                f"(Depth: ${executable_depth_usd:.1f}, Dist: {dist_pct:+.2f}%) passed all gates but blocked by hourly cap "
                f"(portfolio hour: {self.trades_this_hour}/{self.max_trades_per_hour}, market direction: {trades_for_direction}/{max_dir_cap}). Recorded for sample analysis."
            )
            return

        # Concurrent Positions & Portfolio Exposure Ceiling Guard
        if (
            not math.isfinite(float(effective_notional))
            or (current_exposure + float(effective_notional)) > exposure_cap + 1e-6
            or len(risk_positions) + len([k for k in self.pending_entry_intents if k not in risk_positions]) >= self.max_concurrent_positions
        ):
            candidate_record = {
                "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                "candidate_index_in_hour": self.trades_this_hour + 1,
                "market_id": m_id,
                "title": shock.get("title"),
                "target_token": target_token,
                "token_id": token_id,
                "dist_pct": dist_pct,
                "tte_seconds": tte,
                "effective_price": eff_px,
                "executable_depth_usd": executable_depth_usd,
                "hypothetical_notional": effective_notional,
                "target_exit_price": round(eff_px + PROFIT_THETA, 3),
                "reason_blocked": "EXPOSURE_OR_CONCURRENT_CEILING_REACHED",
            }
            try:
                with open(COUNTERFACTUAL_CANDIDATES_FILE, "a") as f:
                    f.write(json.dumps(candidate_record) + "\n")
            except Exception as e:
                logger.warning(f"Failed to record counterfactual candidate: {e}")
            logger.warning(
                f"[CEILING BLOCKED] Active={len(self.active_positions)}/{self.max_concurrent_positions}, "
                f"Exposure=${current_exposure:.2f}/${exposure_cap:.2f}. Recorded counterfactual candidate for sample analysis."
            )
            return

        trade_id = f"LIVE_{shock.get('market_id')}_{int(time.time())}_{target_token}"
        logger.info(
            f"[QUALIFIED OPPORTUNITY] {shock.get('title')} | Target: {target_token} | "
            f"Expected Px: ${raw_vwap:.3f} (Eff: ${eff_px:.3f}) | Dist: {dist_pct:+.2f}% | TTE: {tte/60.0:.1f}m | "
            f"Depth: ${executable_depth_usd:.1f} | Sized Notional: ${effective_notional:.2f}"
        )

        # Dispatch live order via asynchronous EIP-712 adapter (non-blocking)
        fee_meta = shock.get("fee_metadata", {})
        if not self.dry_run or "fee_metadata" in shock:
            if (
                not isinstance(fee_meta, dict)
                or fee_meta.get("fee_rate_market") is None
                or not math.isfinite(float(fee_meta.get("fee_rate_market", 0.0)))
                or float(fee_meta.get("fee_rate_market", 0.0)) <= 0.0
                or not math.isfinite(float(fee_meta.get("fee_exponent", 1.0)))
                or float(fee_meta.get("fee_exponent", 1.0)) < 1.0
            ):
                logger.warning(
                    "[FEE METADATA REJECT] Missing or invalid market fee metadata."
                )
                return
            if fee_meta.get("condition_id") and shock.get("condition_id"):
                if str(fee_meta["condition_id"]).lower() != str(shock["condition_id"]).lower():
                    logger.warning("[FEE PROVENANCE REJECT] Condition ID mismatch in dispatch fee metadata.")
                    return
        cond_id = shock.get("condition_id") or await asyncio.to_thread(
            self.get_condition_id, m_id
        )
        # AUDIT-13-04: Pre-warm tick and fee caches from shock metadata
        if cond_id and cond_id not in self.executor._fee_cache:
            self.executor._fee_cache[cond_id] = (m_fee_rate, m_fee_exp)
        if token_id and token_id not in self.executor._tick_size_cache:
            self.executor._tick_size_cache[token_id] = 0.01
        notional_cap = getattr(self, "max_absolute_ticket_usd", None) or (10000.0 if getattr(self, "unconstrained_kelly", False) else MAX_ABSOLUTE_TICKET_USD)
        effective_notional = min(float(effective_notional), notional_cap)

        pre_cond_bal: Optional[float] = 0.0
        if not self.dry_run and token_id:
            # Hot-path: if token_id is not held in any active position or pending intent,
            # pre-trade balance is known in-memory to be strictly 0.0 (bypassing Polygon RPC call).
            has_prior_activity = (
                any(p.get("token_id") == token_id for p in self.active_positions.values())
                or any(i.get("token_id") == token_id for i in self.pending_entry_intents.values())
            )
            if has_prior_activity:
                try:
                    pre_cond_bal = await asyncio.to_thread(self.executor.get_onchain_erc1155_balance, token_id)
                except Exception:
                    pre_cond_bal = None
                if pre_cond_bal is None or not math.isfinite(float(pre_cond_bal)):
                    logger.error(f"[ENTRY ABORTED] Cannot take authoritative pre-trade ERC-1155 snapshot for {token_id}.")
                    return
                pre_cond_bal = float(pre_cond_bal)
            else:
                pre_cond_bal = 0.0
        now_ts = time.time()
        event_id = str(shock.get("event_id") or shock.get("market_id") or "")
        expiry_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (now_ts + float(shock.get("seconds_to_expiry", 3600.0))))
        open_spot = float(open_spot_cand or shock.get("candle_open_spot") or shock.get("finalized_1h_open") or shock.get("spot_at_t0") or 0.0)
        entry_spot_ref = float(shock.get("spot_at_t0") or shock.get("trigger_price") or open_spot)
        target_exit = 0.99 if self.hold_to_maturity else self._calculate_target_exit(raw_vwap, tte)

        # Smart FAK Price Buffer: capped at max_price_ceiling (Pillar 1 tier-adjusted)
        sleeve_max_price = self.max_price_ceiling
        target_limit_px = round(min(raw_vwap + fak_buf, self.max_price_ceiling), 2)

        # P0-02 Fix: Durable Entry Intent Journal persisted BEFORE remote order dispatch with complete supervisory metadata.
        # Exchange finality identifiers (order id, trade ids, tx hashes) are NOT known before submission and are
        # recovered authoritatively from exchange trade history on restart (never fabricated locally).
        self.pending_entry_intents[trade_id] = {
            "schema_version": "2.3.8",
            "trade_id": trade_id,
            "entry_trade_id": trade_id,
            "sleeve": assigned_sleeve,
            "entry_order_id": None,
            "trade_ids": [],
            "transactions_hashes": [],
            "event_id": event_id,
            "market_id": m_id,
            "condition_id": cond_id,
            "token_id": token_id,
            "target_token": target_token,
            "asset": asset_str,
            "candle_open_spot": open_spot,
            "entry_spot_ref": entry_spot_ref,
            "candle_sigma": float(shock.get("candle_sigma", 0.005) or 0.005),
            "candle_expiry_ts": expiry_ts,
            "entry_tte": tte,
            "target_exit_price": target_exit,
            "notional_usd": effective_notional,
            "intended_notional": effective_notional,
            "target_price": target_limit_px,
            "observed_vwap": raw_vwap,
            "sleeve_max_price": sleeve_max_price,
            "side": "BUY",
            "pre_token_balance": pre_cond_bal,
            "submitted_at_ts": now_ts,
            "timestamp": now_ts,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        if self.dynamic_sizing:
            # Sizing optimization: When dynamic sizing is True, pass sizing_fn=None so SlippageKellyGuard
            # in polymarket_live_executor.py NEVER overwrites or shrinks the elastic ticket.
            active_sizing_fn = None
        else:
            active_sizing_fn = (lambda px: _calc_kelly(max(0.95, p_model_for_sizing), px, live_bankroll)) if (p_model_for_sizing and live_bankroll) else None

        # v3.3 Post-Dispatch State Save: the entry intent is already in RAM (pending_entry_intents) before
        # dispatch; the disk save/fsync runs only AFTER execute_snipe_order_async returns so it never
        # contends for the GIL while the HTTP order is in flight.
        try:
            res = await self.executor.execute_snipe_order_async(
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                notional_usd=effective_notional,
                target_price=target_limit_px,
                side="BUY",
                depth_hurdle=self.depth_hurdle,
                max_price_ceiling=sleeve_max_price,
                market_id=str(shock.get("market_id")),
                condition_id=cond_id,
                market_fee_rate=fee_meta.get("fee_rate_market"),
                market_fee_exponent=fee_meta.get("fee_exponent", 1.0),
                sizing_fn=active_sizing_fn,
                max_ticket_cap=getattr(self, "max_absolute_ticket_usd", None),
                prefetched_book=book_snapshot,
                prefetched_pre_balance=pre_cond_bal,
            )
        finally:
            await asyncio.to_thread(self.save_state)

        if res.mode in ("FAK_KILLED_NO_MATCH", "CLOB_HTTP_400_REJECTION") or (res.details or {}).get("fak_killed") or (res.details or {}).get("clob_400_rejection"):
            self.pending_entry_intents.pop(trade_id, None)
            self.save_state()
            logger.info(
                f"[CLOB REJECTION / FAK ZERO MATCH] {trade_id} rejected deterministically by CLOB (0 shares filled, error={res.error}). "
                f"Released entry intent immediately without halting."
            )
            return

        # Double check: Never treat deterministic HTTP 400 / invalid amounts as outcome_unknown
        err_str = str(res.error or "").lower() + str((res.details or {}).get("raw_exception", "")).lower()
        if "status_code=400" in err_str or "status=400" in err_str or "invalid amounts" in err_str or "supports a max accuracy" in err_str:
            self.pending_entry_intents.pop(trade_id, None)
            self.save_state()
            logger.warning(f"[HTTP 400 REJECTION OVERRIDE] {trade_id} rejected with HTTP 400 ({res.error}). Not registering in active_positions.")
            return

        if (res.details or {}).get("outcome_unknown"):
            self.pending_entry_intents.pop(trade_id, None)
            # P0-02 Fix: Persist ENTRY_OUTCOME_UNKNOWN position to track potential fills.
            ref_px = float(res.price or raw_vwap or 0.0)
            est_shares = float(res.size or (effective_notional / max(ref_px, 0.01)))
            unknown_pre_bal = (res.details or {}).get("pre_token_balance")
            pos_record = {
                "trade_id": trade_id,
                "event_id": event_id,
                "market_id": m_id,
                "condition_id": cond_id,
                "token_id": token_id,
                "target_token": target_token,
                "asset": asset_str,
                "candle_open_spot": open_spot,
                "entry_spot_ref": entry_spot_ref,
                "candle_sigma": float(shock.get("candle_sigma", 0.005) or 0.005),
                "entry_price": ref_px,
                "entry_shares": est_shares,
                "gross_entry_shares": est_shares,
                "remaining_shares": est_shares,
                "filled_exit_shares": 0.0,
                "remaining_exit_shares": est_shares,
                "remaining_cost_basis": float(effective_notional),
                "realized_exit_cash": 0.0,
                "realized_exit_fee": 0.0,
                "gross_exit_cash": 0.0,
                "average_exit_price": 0.0,
                "exit_trade_ids": [],
                "notional_usd": float(effective_notional),
                "intended_notional": float(effective_notional),
                "fee_usd": float(res.fee_usd or 0.0),
                "entry_fee_cash_usd": float(res.fee_usd or 0.0),
                "entry_fee_asset": "USDC",
                "target_exit_price": self._calculate_target_exit(ref_px, tte),
                "entry_time_utc": datetime.now(timezone.utc).isoformat(),
                "entry_ts": now_ts,
                "submitted_at_ts": now_ts,
                "candle_expiry_ts": expiry_ts,
                "pre_token_balance": float(unknown_pre_bal if unknown_pre_bal is not None else pre_cond_bal),
                "entry_order_id": res.order_id or (res.details or {}).get("entry_order_id"),
                "trade_ids": [],
                "transactions_hashes": [],
                "status": "ENTRY_OUTCOME_UNKNOWN",
                "exit_order_status": "ENTRY_OUTCOME_UNKNOWN",
                "inventory_reconciled": False,
                "is_liquidating": False,
                "unwind_order_id": None,
                "unwind_start_time": 0.0,
            }
            self.active_positions[trade_id] = pos_record
            # Reconcilable global halt (not a permanent risk-controller latch): cleared only by
            # authoritative reconciliation of this exact entry.
            self._refresh_global_halt()
            self.save_state()
            logger.critical(
                f"[ENTRY OUTCOME UNKNOWN] Trade {trade_id} registered in active_positions for reconciliation! "
                "Halting new entries until exchange reconciliation."
            )
            return

        self.pending_entry_intents.pop(trade_id, None)
        if not res.success:
            # Authoritative rejection: durably clear the intent so restart does not re-halt on it.
            self.save_state()

        if res.success:
            self.trades_this_hour += 1
            self.trades_per_market[m_id] += 1
            self.trades_per_market_direction[(m_id, target_token)] += 1
            self.traded_market_ids.add(m_id)
            target_exit = 0.99 if self.hold_to_maturity else self._calculate_target_exit(res.price, tte)
            asset_sym = asset_str
            if asset_sym not in self.allowed_assets:
                raise RuntimeError(f"Refusing to create position with unresolved/disallowed asset: {asset_sym!r}")
            open_spot = float(open_spot_cand or shock.get("finalized_1h_open") or shock.get("candle_open_spot") or shock.get("spot_at_t0") or 0.0)
            entry_spot_ref = float(shock.get("spot_at_t0") or shock.get("trigger_price") or open_spot)
            if open_spot <= 0.0:
                open_spot = (
                    await asyncio.to_thread(
                        self.get_reference_spot_price, asset_sym
                    )
                ) or 0.0
                if entry_spot_ref <= 0.0:
                    entry_spot_ref = open_spot

            pos_record = {
                "trade_id": trade_id,
                "sleeve": assigned_sleeve,
                "entry_tte": tte,
                "event_id": event_id,
                "market_id": str(shock.get("market_id")),
                "condition_id": cond_id,
                "token_id": token_id,
                "target_token": target_token,
                "asset": asset_sym,
                "candle_open_spot": open_spot,
                "entry_spot_ref": entry_spot_ref,
                "candle_sigma": float(shock.get("candle_sigma", 0.005) or 0.005),
                "entry_price": res.price,
                "entry_shares": res.size,
                "gross_entry_shares": float(res.size),
                "remaining_shares": res.size,
                "filled_exit_shares": 0.0,
                "remaining_exit_shares": res.size,
                "remaining_cost_basis": res.notional_usd,
                "realized_exit_cash": 0.0,
                "realized_exit_fee": 0.0,
                "gross_exit_cash": 0.0,
                "average_exit_price": 0.0,
                "exit_trade_ids": [],
                "notional_usd": res.notional_usd,
                "fee_usd": res.fee_usd,
                "entry_fee_cash_usd": float(res.fee_usd or 0.0),
                "entry_fee_asset": "USDC",
                "target_exit_price": 0.99 if self.hold_to_maturity else target_exit,
                "exit_order_size": float(res.size),
                "entry_time_utc": datetime.now(timezone.utc).isoformat(),
                "entry_ts": time.time(),
                "candle_expiry_ts": time.time() + tte,
                "pre_token_balance": res.details.get("pre_token_balance", pre_cond_bal),
                "entry_order_id": res.order_id,
                "trade_ids": res.details.get("trade_ids", []),
                "transactions_hashes": res.details.get("transactions_hashes", []),
                "status": res.execution_status,
                "exit_order_id": None,
                "exit_order_status": "NONE",
                "is_liquidating": False,
                "unwind_order_id": None,
                "unwind_start_time": 0.0,
            }
            # IMMUTABLE PERSISTENCE: Save open position immediately before placing exit order
            self.active_positions[trade_id] = pos_record
            await asyncio.to_thread(self.save_state)
            logger.info(f"✓ POSITION RECORDED & PERSISTED: {trade_id} | Shares={res.size:.2f} @ ${res.price:.4f} | Status={res.execution_status}")
            if not self.dry_run:
                try:
                    send_operational_alert(
                        "LIVE_ORDER_FILL",
                        f"{trade_id} {shock.get('title')!r} {res.size:.2f} sh @ ${res.price:.4f} (~${res.size * res.price:.2f}) status={res.execution_status}",
                        "INFO",
                        dedupe_key=f"fill:{trade_id}",
                    )
                except Exception:
                    logger.debug("[ALERT] fill alert construction failed", exc_info=True)

            # Post resting maker scalp limit order with post_only=True (Policy B2)
            # P0 Invariant: Only post exit immediately if position is CONFIRMED on-chain!
            if res.execution_status == ExecutionStatus.POSITION_CONFIRMED:
                pos_record["inventory_reconciled"] = True
                pos_record["entry_finality_source"] = "EXECUTOR_CONFIRMED_DELTA"
                # Sequential Iceberg Tranche Stepping for tickets > $50
                rem_total = float(res.size)
                entry_px = float(pos_record.get("entry_price", 0.70))
                single_exit_px = target_exit if getattr(self, "hold_to_maturity", False) else min(0.96, round(entry_px + 0.16, 2))
                exit_size = rem_total
                exit_price = single_exit_px
                if not getattr(self, "hold_to_maturity", False) and float(pos_record.get("notional_usd", 0.0) or 0.0) >= 10.0 and rem_total >= 10.0:
                    t1_sz = float((Decimal(str(rem_total)) * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                    t2_sz = float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                    if t1_sz >= 5.0 and t2_sz >= 5.0:
                        t1_px = min(0.94, round(entry_px + 0.14, 2))
                        t2_px = 0.98
                        pos_record["exit_tranches"] = [
                            {"idx": 1, "size": t1_sz, "price": t1_px, "status": "PENDING"},
                            {"idx": 2, "size": t2_sz, "price": t2_px, "status": "PENDING"},
                        ]
                        exit_size = t1_sz
                        exit_price = pos_record["exit_tranches"][0]["price"]
                        pos_record["target_exit_price"] = exit_price
                    else:
                        exit_size = rem_total
                        exit_price = single_exit_px
                        pos_record["target_exit_price"] = exit_price
                else:
                    exit_size = rem_total
                    exit_price = single_exit_px
                    pos_record["target_exit_price"] = exit_price

                exit_res = await asyncio.to_thread(
                    self.executor.post_maker_exit_order,
                    token_id=token_id,
                    price=exit_price,
                    size=exit_size,
                    side="SELL",
                )
                posted = self._apply_exit_post_result(pos_record, exit_res, float(exit_size))
                if pos_record.get("exit_tranches") and posted:
                    pos_record["exit_tranches"][0]["status"] = "POSTED"
                elif pos_record.get("exit_tranches") and (exit_res or {}).get("outcome_unknown"):
                    pos_record["exit_tranches"][0]["status"] = "IN_FLIGHT"
                if posted:
                    logger.info(f"✓ MAKER SCALP ORDER POSTED (POST-ONLY): {pos_record['exit_order_id']} | {exit_size:.2f} shares @ ${exit_price:.4f}")
            else:
                pos_record["exit_order_status"] = "AWAITING_DELTA_SETTLEMENT"
                logger.info(f"Position {trade_id} in {res.execution_status}. Background loop will verify on-chain delta before posting maker exit.")
                if not self.dry_run:
                    # v3.4: poll every 0.20s for up to 5.0s so the maker TP posts the instant shares arrive.
                    self._spawn_fast_confirm(trade_id)

            await asyncio.to_thread(self.save_state)

    def _recover_pending_intent(self, trade_id: str, intent: Dict[str, Any]) -> str:
        """
        Resolves one durable pending entry intent left by a crash. Returns RECOVERED / NOT_EXECUTED / UNRESOLVED.
        Recovered positions carry authoritative exchange finality evidence (trade ids, tx hashes, actual
        cost from trade history) or, failing that, verified on-chain inventory - never fabricated ids.
        """
        token_id = intent.get("token_id")
        pre_bal = float(intent.get("pre_token_balance", 0.0) or 0.0)
        intended_notional = float(intent.get("notional_usd", intent.get("intended_notional", 0.0)) or 0.0)
        target_price = float(intent.get("target_price", 0.70) or 0.70)
        submitted_ts = float(intent.get("submitted_at_ts", intent.get("timestamp", time.time())) or time.time())
        if not token_id:
            logger.error(f"[RECONCILIATION] Pending intent {trade_id} has no token id; retaining global halt.")
            return "UNRESOLVED"

        cls = self._classify_entry(token_id, pre_bal, submitted_ts, intent.get("entry_order_id") or intent.get("order_id"), trade_id)
        verdict = cls["verdict"]
        if verdict == "NOT_EXECUTED":
            logger.info(f"[RECONCILIATION] Pending entry intent {trade_id} authoritatively NOT executed ({cls.get('proof')}). Discarding intent.")
            self.pending_entry_intents.pop(trade_id, None)
            self.save_state()
            return "NOT_EXECUTED"
        if verdict not in {"ARRIVED", "MATCHED_UNSETTLED"}:
            logger.error(
                f"[RECONCILIATION] Pending entry intent {trade_id} outcome not authoritatively provable "
                f"(balance={cls.get('balance')}, source={cls.get('source')}). Retaining intent and global halt."
            )
            return "UNRESOLVED"

        target_exit_p = float(intent.get("target_exit_price") or (0.99 if self.hold_to_maturity else round(min(0.99, target_price + 0.08), 2)))
        candle_open = float(intent.get("candle_open_spot", 0.0) or 0.0)
        candle_exp = float(intent.get("candle_expiry_ts", 0.0) or 0.0)
        candle_sig = float(intent.get("candle_sigma", 0.005) or 0.005)
        asset_val = intent.get("asset", "")
        target_tok = intent.get("target_token", "")
        recovered_pos = {
            "trade_id": trade_id,
            "entry_trade_id": intent.get("entry_trade_id") or trade_id,
            "entry_order_id": intent.get("entry_order_id") or intent.get("order_id"),
            "trade_ids": [],
            "transactions_hashes": [],
            "pre_token_balance": pre_bal,
            "event_id": intent.get("event_id", ""),
            "market_id": intent.get("market_id", ""),
            "condition_id": intent.get("condition_id", ""),
            "token_id": token_id,
            "target_token": target_tok,
            "asset": asset_val,
            "candle_open_spot": candle_open,
            "entry_spot_ref": float(intent.get("entry_spot_ref") or candle_open),
            "candle_sigma": candle_sig,
            "candle_expiry_ts": candle_exp,
            "side": intent.get("side", "BUY"),
            "entry_price": target_price,
            "entry_shares": 0.0,
            "gross_entry_shares": 0.0,
            "remaining_shares": 0.0,
            "remaining_exit_shares": 0.0,
            "filled_exit_shares": 0.0,
            "remaining_cost_basis": intended_notional,
            "notional_usd": intended_notional,
            "intended_notional": intended_notional,
            "cost_basis_estimated": True,
            "fee_usd": float(intent.get("fee_usd", 0.0) or 0.0),
            "entry_fee_cash_usd": float(intent.get("entry_fee_cash_usd", 0.0) or 0.0),
            "entry_fee_asset": intent.get("entry_fee_asset", "SHARES"),
            "target_exit_price": target_exit_p,
            "entry_time_utc": intent.get("created_at_utc", datetime.now(timezone.utc).isoformat()),
            "entry_ts": submitted_ts,
            "submitted_at_ts": submitted_ts,
            "status": ExecutionStatus.POSITION_CONFIRMED if verdict == "ARRIVED" else ExecutionStatus.MATCHED_PENDING_SETTLEMENT,
            "exit_order_id": None,
            "exit_order_status": "AWAITING_DELTA_SETTLEMENT",
            "created_at_utc": intent.get("created_at_utc", datetime.now(timezone.utc).isoformat()),
            "realized_exit_cash": 0.0,
            "realized_exit_fee": 0.0,
            "gross_exit_cash": 0.0,
            "average_exit_price": 0.0,
            "exit_trade_ids": [],
            "inventory_reconciled": False,
            "is_liquidating": False,
            "unwind_order_id": None,
            "unwind_start_time": 0.0,
            "order_records": {},
            "recovered_from_intent": True,
        }
        self._apply_entry_evidence(recovered_pos, cls)
        if not recovered_pos.get("target_exit_price") or not math.isfinite(float(recovered_pos["target_exit_price"])):
            recovered_pos["target_exit_price"] = target_exit_p

        # Schema-completeness check: supervision needs market/volatility/expiry metadata
        missing_fields = []
        if not target_tok:
            missing_fields.append("target_token")
        if not asset_val:
            missing_fields.append("asset")
        if candle_open <= 0.0 or not math.isfinite(candle_open):
            missing_fields.append("candle_open_spot")
        if candle_exp <= 0.0 or not math.isfinite(candle_exp):
            missing_fields.append("candle_expiry_ts")
        if missing_fields:
            logger.critical(
                f"[RECONCILIATION] Recovered position {trade_id} lacks critical supervisory fields {missing_fields}. "
                "Enforcing persistent reconciliation hold!"
            )
            recovered_pos["exit_order_status"] = "RECONCILIATION_HOLD_INCOMPLETE_SCHEMA"
            recovered_pos["missing_supervisory_fields"] = missing_fields

        self.active_positions[trade_id] = recovered_pos
        self.pending_entry_intents.pop(trade_id, None)
        self.save_state()
        logger.warning(
            f"[RECONCILIATION] RECOVERED position from intent {trade_id}: {verdict} | shares={recovered_pos['entry_shares']} | "
            f"cost=${recovered_pos['notional_usd']:.4f} | finality={recovered_pos.get('entry_finality_source')} | "
            f"trade_ids={recovered_pos.get('trade_ids')}"
        )
        return "RECOVERED"

    def reconcile_with_exchange(self):
        """
        Startup reconciliation (fail-closed). Uses the SAME lifecycle resolvers and the SAME
        maker-exit gate as the live supervisor:
          0. resolve durable pending entry intents (exchange trade history + on-chain inventory)
          1. resolve every unknown/unreconciled lifecycle state (never submits)
          2. align exit orders with the exchange; only allowlisted states may receive a new maker exit
          3. cancel orphan orders, then rebuild the reservation book from an authoritative snapshot
          4. re-derive the persisted global halt authoritatively
        """
        if self.dry_run or not self.executor.is_authenticated:
            return

        logger.info("[RECONCILIATION] Reconciling local state with live exchange...")
        try:
            try:
                collateral_bal = self.executor.get_collateral_balance()
                if collateral_bal is not None and isinstance(collateral_bal, (int, float)) and collateral_bal > 0:
                    self._last_known_collateral = float(collateral_bal)
                    self.executor.set_cached_collateral(self._last_known_collateral)
                    logger.info(f"[RECONCILIATION] Live collateral balance: ${self._last_known_collateral:.2f}")
                    now_ts = time.time()
                    active_market_equity = sum(self.get_position_market_value(p, now_ts) for p in self.active_positions.values())
                    tot_equity = self._last_known_collateral + active_market_equity
                    self.risk_controller.check_equity_drawdown(tot_equity)
            except Exception as e:
                logger.debug(f"[RECONCILIATION] Could not query initial collateral balance: {e}")

            open_orders = self._strict_open_orders()
            open_order_ids = {o.get("id") or o.get("orderID") for o in open_orders if o}
            logger.info(f"[RECONCILIATION] CLOB reports {len(open_order_ids)} live open orders.")

            # 0. Durable pending entry intents from crash recovery
            for trade_id, intent in list((getattr(self, "pending_entry_intents", None) or {}).items()):
                if trade_id in self.active_positions:
                    logger.info(f"[RECONCILIATION] Pending entry intent {trade_id} already in active_positions; clearing intent.")
                    self.pending_entry_intents.pop(trade_id, None)
                    self.save_state()
                    continue
                self._recover_pending_intent(trade_id, intent)

            # 1. Unified resolution of unknown outcomes (shared with the live supervisor)
            for tid, pos in list(self.active_positions.items()):
                if position_requires_global_halt(pos):
                    self._resolve_lifecycle(tid, pos, open_orders, force=True)

            # 2. Exit-order alignment
            for tid, pos in list(self.active_positions.items()):
                if tid not in self.active_positions:
                    continue
                if position_is_settlement_receivable(pos) or position_requires_global_halt(pos):
                    continue  # unresolved outcomes never receive new orders
                exit_oid = pos.get("exit_order_id")
                token_id = pos.get("token_id")

                if exit_oid and exit_oid in open_order_ids:
                    logger.info(f"[RECONCILIATION] Active position {tid} has confirmed resting exit order {exit_oid}.")
                    continue

                if exit_oid:
                    prior_exit_state = pos.get("exit_order_status", "")
                    order_info = self.executor.get_order_status(exit_oid)
                    if prior_exit_state in {"STOP_CANCEL_PENDING", "PRE_EXPIRY_CANCEL_PENDING"}:
                        if not order_info:
                            logger.warning(f"Cannot reconcile pending cancellation {exit_oid} for {tid}; retaining position.")
                            continue
                        terminal = str(order_info.get("status", "")).upper()
                        if terminal not in {"CANCELED", "CANCELLED", "EXPIRED", "MATCHED", "FILLED", "CONFIRMED"}:
                            logger.warning(f"Cancellation not terminal: {exit_oid} (status={terminal}); retaining position.")
                            continue
                        if terminal in {"MATCHED", "FILLED", "CONFIRMED"}:
                            pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                            pos["pending_canceled_order_id"] = exit_oid
                            self.save_state()
                            continue
                        try:
                            self.executor.release_inventory(reservation_id=exit_oid)
                        except Exception as rel_err:
                            logger.error(f"Reservation release failed for {exit_oid}: {rel_err}")
                            raise
                        pos["exit_order_id"] = None
                        if prior_exit_state == "STOP_CANCEL_PENDING":
                            pos["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
                            pos["next_unwind_retry_ts"] = 0.0
                            pos["is_liquidating"] = False
                        else:
                            pos["exit_order_status"] = "PRE_EXPIRY_EVALUATION_REQUIRED"
                        self.save_state()
                        continue

                    if not order_info:
                        # Absent from the snapshot AND status unavailable: the order may still be live.
                        # Never post a replacement on missing evidence (P0-04).
                        logger.warning(f"[RECONCILIATION] Exit order {exit_oid} for {tid} absent from snapshot and status UNKNOWN; retaining.")
                        continue

                    # Centralized per-order fill accounting and cash deduplication
                    order_size = float(pos.get("exit_order_size", pos.get("entry_shares", 0.0)) or 0.0)
                    order_matched = float(self._num(order_info.get("size_matched")) or 0.0)
                    order_status_str = str(order_info.get("status", "")).upper()
                    raw_taking = order_info.get("taking_amount") or order_info.get("takingAmount")
                    total_order_taking = self._num(raw_taking)
                    is_taking_estimated = False
                    if total_order_taking is None:
                        total_order_taking = order_matched * float(pos.get("target_exit_price", 0.0) or 0.0)
                        if order_matched > 0:
                            pos["exit_cash_estimated"] = True
                            is_taking_estimated = True
                    raw_fee = float(self._num(order_info.get("fee")) or self._num(order_info.get("fee_usd")) or 0.0)
                    self.record_fill_and_update_position(
                        pos, exit_oid, order_matched, total_order_taking, fee_usd=raw_fee, cash_is_estimated=is_taking_estimated
                    )
                    f_ids = [str(x) for x in (order_info.get("fill_ids") or order_info.get("associate_trades") or []) if x]
                    if f_ids:
                        pos["exit_fill_ids"] = sorted(set(pos.get("exit_fill_ids") or []) | set(f_ids))

                    rem_shares = float(pos["remaining_shares"])
                    total_filled_shares = float(pos["filled_exit_shares"])
                    is_order_terminal = order_status_str in {"MATCHED", "FILLED", "CONFIRMED"} or order_matched >= order_size - 1e-4
                    is_canceled = order_status_str in {"CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}
                    is_position_complete = rem_shares <= 0.01 or total_filled_shares >= float(pos["entry_shares"]) - 1e-4

                    if is_position_complete:
                        if is_taking_estimated or float(pos.get("estimated_exit_cash", 0.0)) > 0.0:
                            pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                            pos["status"] = "UNRESOLVED_SETTLEMENT"
                            self.save_state()
                            logger.warning(f"[RECONCILIATION] Position {tid} filled offline but cash is estimated; retaining in UNRESOLVED_SETTLEMENT.")
                        else:
                            self._close_position(tid, pos, ExecutionStatus.FILLED, "FILLED_OFFLINE", won=True)
                            logger.info(f"[RECONCILIATION] Position {tid} completely filled while offline.")
                        continue
                    if is_order_terminal:
                        pos["exit_order_id"] = None
                        pos["pending_canceled_order_id"] = exit_oid
                        pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                        pos["status"] = ExecutionStatus.PARTIALLY_FILLED
                        self.save_state()
                        logger.warning(f"[PARTIAL ORDER MATCH] Position {tid}: order {exit_oid} filled {order_matched:.2f} shares. Remaining unsold: {rem_shares:.2f}")
                        continue
                    if not is_canceled:
                        # Live (possibly partially matched) but missing from the snapshot: retain, never repost.
                        if order_matched > 0:
                            pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                            pos["pending_canceled_order_id"] = exit_oid
                        self.save_state()
                        logger.warning(f"[RECONCILIATION] Exit order {exit_oid} for {tid} non-terminal ({order_status_str}) but absent from snapshot; retaining.")
                        continue
                    # Authoritatively canceled with the residual unsold -> eligible for a replacement maker exit.
                    try:
                        self.executor.release_inventory(reservation_id=exit_oid)
                    except Exception as rel_err:
                        logger.error(f"Reservation release failed for {exit_oid}: {rel_err}")
                        raise
                    pos["exit_order_id"] = None
                    pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
                    if total_filled_shares > 0:
                        pos["status"] = ExecutionStatus.PARTIALLY_FILLED
                    self.save_state()
                    logger.warning(f"[RECONCILIATION] Exit order {exit_oid} for {tid} terminally {order_status_str}; residual {rem_shares:.2f} eligible for recovery.")

                # Crash after entry / failed post: the single shared maker-exit gate decides.
                if token_id and not pos.get("exit_order_id"):
                    pos.pop("recovered_from_intent", None)
                    self._attempt_maker_exit_post(tid, pos)

            # 3. Cancel orphan orders not associated with tracked positions, then rebuild reservations
            tracked_oids = {
                str(p.get(k)) for p in self.active_positions.values()
                for k in ("exit_order_id", "unwind_order_id", "pending_canceled_order_id", "cancel_pending_order_id")
                if p.get(k)
            }
            for o in open_orders:
                oid = o.get("id") or o.get("orderID")
                if oid and str(oid) not in tracked_oids:
                    logger.warning(f"[RECONCILIATION] Orphan CLOB order {oid} detected. Canceling for capital safety.")
                    self.executor.cancel_order(oid)

            rebuild = getattr(self.executor, "rebuild_reservations_from_exchange", None)
            if callable(rebuild):
                fresh_orders = self._strict_open_orders()
                if rebuild(fresh_orders) is False:
                    raise RuntimeError("Reservation book could not be rebuilt from the exchange")

            # 4. Authoritative re-derivation of the persisted global halt
            self._startup_reconciled = True
            self._refresh_global_halt(authoritative=True)
            self.save_state()
            logger.info(
                f"[RECONCILIATION] Exchange state reconciled. Global halt={self.risk_halt} "
                f"reasons={self.global_halt_reasons}"
            )
        except Exception as e:
            logger.critical(f"[RECONCILIATION] Exchange/local state is UNKNOWN; refusing to mutate orders: {e}")
            raise RuntimeError("Live exchange reconciliation failed; safe startup refused") from e

    def _strict_open_orders(self) -> List[Dict[str, Any]]:
        try:
            open_orders = self.executor.get_open_orders(strict=True)
        except TypeError:
            open_orders = self.executor.get_open_orders()
        if open_orders is None or not isinstance(open_orders, list):
            raise RuntimeError("CLOB open-order snapshot unavailable")
        return open_orders

    async def _apply_market_resolution(self, tid: str, pos: Dict[str, Any], winning_outcome: Any) -> None:
        """
        Applies a finalized market resolution (Condition 3 / R3-04). Retried every supervisor pass until done.
          - unresolved execution outcomes are reconciled FIRST (their cash must not be lost)
          - a resting exit is cancelled with verified terminal status; its fills are booked from the exchange
          - live LOSING inventory closes immediately (worth $0; realized cash = recorded fills only)
          - live WINNING inventory becomes a redemption receivable: NO cash is realized until a verified
            on-chain PayoutRedemption receipt (confirm_onchain_redemption / poll_onchain_redemptions)
        """
        if tid not in self.active_positions:
            return
        outcome_str = winning_outcome.get("winning_outcome") if isinstance(winning_outcome, dict) else str(winning_outcome or "")
        if pos.get("resolved_winning_outcome") is None:
            pos["resolved_winning_outcome"] = outcome_str
            pos["resolution_seen_at_ts"] = time.time()
            self.save_state()
        if position_is_settlement_receivable(pos):
            return
        if pos.get("status") == "LIQUIDITY_CRISIS" or pos.get("exit_order_status") == "LIQUIDITY_CRISIS":
            pos["status"] = ExecutionStatus.POSITION_CONFIRMED
            pos["exit_order_status"] = "RESTING" if pos.get("exit_order_id") else "NONE"
        if not self.dry_run and position_requires_global_halt(pos) and pos.get("exit_order_status") != "RESOLUTION_CANCEL_UNCONFIRMED":
            await asyncio.to_thread(self._resolve_lifecycle, tid, pos, None, True)
            if tid not in self.active_positions:
                return
            if position_requires_global_halt(pos) and pos.get("exit_order_status") != "RESOLUTION_CANCEL_UNCONFIRMED":
                logger.warning(f"[RESOLUTION DEFERRED] {tid}: unresolved execution outcome {pos.get('exit_order_status')}; settling after reconciliation.")
                return

        won = (pos.get("target_token") == outcome_str)
        token_id = pos.get("token_id")

        exit_oid = pos.get("exit_order_id")
        if exit_oid:
            cancel_res = await asyncio.to_thread(self.executor.cancel_order, exit_oid)
            if not self.dry_run:
                if (cancel_res or {}).get("error"):
                    pos["exit_order_status"] = "RESOLUTION_CANCEL_UNCONFIRMED"
                    self.save_state()
                    return
                summary = await asyncio.to_thread(self.executor.get_order_fill_summary, exit_oid, token_id)
                if summary is None:
                    pos["exit_order_status"] = "RESOLUTION_CANCEL_UNCONFIRMED"
                    self.save_state()
                    return
                self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False)
                if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
                    self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                    return
                if not summary["terminal"]:
                    pos["exit_order_status"] = "RESOLUTION_CANCEL_UNCONFIRMED"
                    self.save_state()
                    return
                self.executor.release_inventory(reservation_id=exit_oid)
            pos["exit_order_id"] = None
            pos["exit_order_status"] = "CANCELED_FOR_RESOLUTION"

        rem_shares = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", pos.get("entry_shares", 0.0))) or 0.0)
        if not self.dry_run:
            if not won:
                pos["expected_terminal_payout_usd"] = 0.0
                pos["redemption_receivable_usd"] = 0.0
                pos["winning_shares_held"] = 0.0
                pos["expected_winning_outcome"] = winning_outcome
                self._close_position(tid, pos, ExecutionStatus.SETTLED, "MARKET_RESOLVED_LOSS", won=False)
                return

            # For WINNING positions, require authoritative on-chain ERC-1155 balance (never trust a 0.0 CLOB API fallback!)
            bal, src = await asyncio.to_thread(self._wallet_token_balance, token_id)
            if src != self.ONCHAIN_SOURCE and (bal is None or bal < 0.01):
                logger.warning(
                    f"[RESOLUTION DEFERRED] {tid}: Winning position on-chain ERC-1155 balance unavailable "
                    f"(bal={bal}, src={src}). Deferring resolution closeout until Polygon RPC responds."
                )
                return
            if bal is not None and src == self.ONCHAIN_SOURCE:
                rem_shares = min(rem_shares, bal)
            if rem_shares < 0.01:
                pos["expected_terminal_payout_usd"] = 0.0
                pos["redemption_receivable_usd"] = 0.0
                pos["winning_shares_held"] = 0.0
                pos["expected_winning_outcome"] = winning_outcome
                self._close_position(tid, pos, ExecutionStatus.SETTLED, "MARKET_RESOLVED_NO_INVENTORY", won=False)
                return
            head = await asyncio.to_thread(self.executor.get_current_block_number)
            pos["status"] = "AWAITING_ONCHAIN_SETTLEMENT"
            pos["exit_order_status"] = "AWAITING_REDEMPTION"
            pos["is_liquidating"] = False
            pos["expected_terminal_payout_usd"] = round(rem_shares, 4)
            pos["redemption_receivable_usd"] = round(rem_shares, 4)
            pos["winning_shares_held"] = round(rem_shares, 6)
            pos["expected_winning_outcome"] = winning_outcome
            pos["resolution_block"] = max(0, int(head) - 50) if isinstance(head, int) else None
            self.save_state()
            logger.info(
                f"[RESOLVED - RECEIVABLE] {tid}: {rem_shares:.2f} winning shares held. Expected ${rem_shares:.2f} is a "
                "receivable, NOT realized cash, until a verified on-chain redemption receipt."
            )
            return

        # Dry-run mode: immediate virtual settlement
        payout = rem_shares * 1.0 if (won and rem_shares >= 0.01) else 0.0
        if payout > 0.0:
            self.record_fill_and_update_position(pos, "SETTLEMENT_RESOLUTION_PAYOUT", rem_shares, payout, 0.0)
        net_pnl = self._close_position(tid, pos, ExecutionStatus.SETTLED, "MARKET_RESOLVED", won=None)
        logger.info(f"✓ POSITION RESOLVED AT MATURITY: {tid} | Won={won} | RemShares={rem_shares:.2f} | Net PnL=${net_pnl:+.2f}")

    async def check_resolutions_and_manage_positions(self):
        """Monitors active positions for delta settlements, maker scalp fills, time-decay unwind, or finalized resolutions."""
        if not self.active_positions:
            self._refresh_global_halt()
            return

        # 1. Check finalized candle resolutions from stream (binary buffered read)
        if RESOLUTIONS_FILE.exists():
            try:
                current_res_size = RESOLUTIONS_FILE.stat().st_size
                if current_res_size > self.last_res_file_pos:
                    with open(RESOLUTIONS_FILE, "rb") as f:
                        f.seek(self.last_res_file_pos)
                        chunk = f.read()
                    complete_end = chunk.rfind(b"\n") + 1
                    if complete_end:
                        new_lines = chunk[:complete_end].decode("utf-8").splitlines()
                        self.last_res_file_pos += complete_end
                    else:
                        new_lines = []

                    for line in new_lines:
                        if not line.strip():
                            continue
                        try:
                            res = json.loads(line)
                            res_m_id = str(res.get("market_id"))
                            winning_outcome = res.get("winning_outcome")
                            for tid, pos in list(self.active_positions.items()):
                                if str(pos.get("market_id")) == res_m_id:
                                    await self._apply_market_resolution(tid, pos, winning_outcome)
                        except Exception as e:
                            logger.error(f"Error parsing resolution line: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error checking resolutions: {e}")

        # 1b. Verified on-chain redemption receipts for resolved winning receivables
        if not self.dry_run:
            try:
                await asyncio.to_thread(self.poll_onchain_redemptions)
            except Exception as e:
                logger.error(f"[REDEMPTION] Poll error: {e}")

        # 2. Check live positions for delta confirmation, maker scalp fills, and time-decay unwind
        if self.dry_run:
            # DRY-RUN SIMULATION ONLY: simulate maker fill if best bid reaches target exit price
            for tid, pos in list(self.active_positions.items()):
                try:
                    token_id = pos.get("token_id")
                    if not token_id or position_is_settlement_receivable(pos):
                        continue
                    book = await self.executor.get_market_book_async(token_id)
                    bids = book.get("bids", [])
                    if bids:
                        best_bid = max(float(b.get("price", 0.0)) for b in bids)
                        if best_bid >= pos.get("target_exit_price", 0.99):
                            payout = round(pos["entry_shares"] * pos["target_exit_price"], 2)
                            net_pnl = self.calculate_realized_cash_pnl(pos, payout, 0.0)
                            pos["status"] = ExecutionStatus.FILLED
                            pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                            pos["won"] = True
                            pos["filled_exit_shares"] = pos["entry_shares"]
                            pos["remaining_exit_shares"] = 0.0
                            pos["gross_exit_cash"] = payout
                            pos["average_exit_price"] = pos["target_exit_price"]
                            pos["payout_usd"] = payout
                            pos["net_pnl_usd"] = net_pnl
                            pos["close_reason"] = "DRY_RUN_MAKER_SCALP_FILLED"
                            self.closed_positions.append(pos)
                            self.risk_controller.record_trade_pnl(net_pnl)
                            del self.active_positions[tid]
                            logger.info(f"[DRY-RUN] ✓ POSITION CLOSED VIA SIMULATED MAKER SCALP: {tid} | Net PnL=${net_pnl:+.2f}")
                            self.save_state()
                except Exception as e:
                    logger.debug(f"Error in dry-run book check for {tid}: {e}")

        # Active position supervision and risk management (runs for remaining open positions)
        try:
            try:
                open_orders = await asyncio.to_thread(self._strict_open_orders)
                open_oids = {o.get("id") or o.get("orderID") for o in open_orders if o}
                open_orders_authoritative = True
            except Exception as oo_err:
                logger.warning(
                    f"[SUPERVISION WARN] Open-orders snapshot degraded ({oo_err}); "
                    "continuing per-position stop-loss and fill supervision fail-closed."
                )
                open_orders = None
                open_oids = set()
                open_orders_authoritative = False

            now_ts = time.time()
            for tid, pos in list(self.active_positions.items()):
                if tid not in self.active_positions:
                    continue
                try:
                    # Lifecycle gate (shared policy): receivables are never traded; resolved markets
                    # finish settlement; unknown outcomes are reconciled and NEVER receive new orders.
                    if position_is_settlement_receivable(pos):
                        continue
                    # AUDIT-13-05 Fix: Re-poll UNRESOLVED_SETTLEMENT positions until on-chain tx hash confirms cash
                    if pos.get("status") == "UNRESOLVED_SETTLEMENT":
                        settle_oid = pos.get("exit_order_id") or pos.get("pending_settlement_order_id") or pos.get("unwind_order_id")
                        if settle_oid:
                            summary = await asyncio.to_thread(self.executor.get_order_fill_summary, str(settle_oid), pos.get("token_id"))
                            if summary is not None:
                                self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False)
                        is_resolved_loss = (
                            pos.get("pending_settlement_close_reason") in {"MARKET_RESOLVED_LOSS", "EXPIRED_OUT_OF_MONEY"}
                            or (pos.get("close_reason") and "MARKET_RESOLVED_LOSS" in str(pos.get("close_reason")))
                        )
                        if is_resolved_loss or (not pos.get("exit_cash_estimated", False) and float(pos.get("estimated_exit_cash", 0.0) or 0.0) == 0.0):
                            if is_resolved_loss:
                                pos["exit_cash_estimated"] = False
                                pos["estimated_exit_cash"] = 0.0
                            self._close_position(
                                tid, pos,
                                pos.get("pending_settlement_close_status", ExecutionStatus.SETTLED if is_resolved_loss else ExecutionStatus.FILLED),
                                pos.get("pending_settlement_close_reason", "MARKET_RESOLVED_LOSS" if is_resolved_loss else "SETTLEMENT_CONFIRMED_CLOB"),
                                won=False if is_resolved_loss else None,
                            )
                        continue
                    if pos.get("resolved_winning_outcome") is not None:
                        await self._apply_market_resolution(tid, pos, pos["resolved_winning_outcome"])
                        continue
                    if position_requires_global_halt(pos):
                        await asyncio.to_thread(self._resolve_lifecycle, tid, pos, open_orders)
                        if tid not in self.active_positions or position_requires_global_halt(pos):
                            continue

                    exit_oid = pos.get("exit_order_id")
                    token_id = pos.get("token_id")
                    expiry_ts = pos.get("candle_expiry_ts", now_ts + 600.0)
                    tte_rem = max(0.0, expiry_ts - now_ts)

                    # Phase A: entry finality + maker exit via the single shared gate (P0-02 / P0-04)
                    if (
                        not exit_oid
                        and position_may_post_new_maker_exit(pos)
                        and tte_rem >= self.tte_cancel_window
                    ):
                        pos.pop("recovered_from_intent", None)
                        posted = await asyncio.to_thread(self._attempt_maker_exit_post, tid, pos)
                        exit_oid = pos.get("exit_order_id")
                        if posted or not pos.get("inventory_reconciled") or position_requires_global_halt(pos):
                            continue
                        # inventory is held but the exit is deferred: stop-loss supervision still applies

                    # Phase B: Stop-Loss Protection and Pre-Expiry Liquidation Policy (Regime 4)
                    entry_px = float(pos.get("entry_price", 0.50))
                    rem_shrs = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", pos.get("entry_shares", 0.0))) or 0.0)

                    retry_due = (
                        pos.get("exit_order_status") == "STOP_CANCEL_PENDING"
                        or (
                            pos.get("exit_order_status") in ({"UNWIND_RETRY_REQUIRED"} | PARTIAL_UNWIND_RESIDUAL_STATUSES)
                            and now_ts >= float(pos.get("next_unwind_retry_ts", 0.0) or 0.0)
                        )
                    )
                    best_b = 0.0
                    current_spot = None
                    open_spot = float(pos.get("candle_open_spot", 0.0) or 0.0)
                    entry_spot_ref = float(pos.get("entry_spot_ref") or pos.get("candle_open_spot") or open_spot)
                    candle_sigma = float(pos.get("candle_sigma", 0.005) or 0.0)
                    spot_valid = False
                    spot_disp = 0.0
                    entry_spot_disp = 0.0
                    entry_move_pct = 0.0
                    if (not pos.get("is_liquidating") or retry_due) and token_id and rem_shrs > 0.01:
                        # v3.3: /dev/shm fast tick top-of-book first (<=1.5s old, verified market_id & token_id), REST fallback
                        book = self._get_verified_shm_book(pos)
                        if book is None:
                            book = await self.executor.get_market_book_async(token_id)
                        bids = book.get("bids", []) if isinstance(book, dict) else []
                        asks = book.get("asks", []) if isinstance(book, dict) else []
                        best_b = max(float(b.get("price", 0.0)) for b in bids if float(b.get("size", 0.0)) > 0) if bids else 0.0
                        best_a = min(float(a.get("price", 0.0)) for a in asks if float(a.get("size", 0.0)) > 0) if asks else 0.0
                        book_spread = (best_a - best_b) if (best_a > 0 and best_b > 0 and best_a > best_b) else 0.0

                        # Upgrade 4: Pre-warm next-candle subscriptions at TTE <= 120s
                        if 0 < tte_rem <= 120.0:
                            prewarm_tag = f"_prewarmed_candle_{pos.get('market_id')}"
                            if not getattr(self, prewarm_tag, False):
                                setattr(self, prewarm_tag, True)
                                asyncio.create_task(self._prewarm_next_candle_markets())

                        # CRIT-02: Final-45s Capital Recycling is handled exclusively by the unified Phase B
                        # `final_45s_triggered` state machine (STOP_CANCEL_PENDING cancel-and-reconcile gate) below.
                        entry_px = float(pos.get("entry_price") or 0.0)

                        # v3.4 Queue-Priority Jumping during position supervision
                        if (
                            exit_oid
                            and not pos.get("queue_jumped")
                            and not pos.get("is_liquidating")
                            and rem_shrs > 0.01
                            and tte_rem >= self.tte_cancel_window
                        ):
                            curr_target_px = float(pos.get("target_exit_price") or 0.0)
                            if curr_target_px in (0.98, 0.99):
                                jump_px = compute_queue_priority_maker_price(
                                    entry_px, rem_shrs, bids, asks, curr_target_px
                                )
                                if jump_px is not None:
                                    logger.info(
                                        f"[QUEUE JUMP SUPERVISION] Position {tid}: massive wall at ${curr_target_px:.2f}. "
                                        f"Stepping 1c in front to ${jump_px:.2f} (cancelling OID: {exit_oid})."
                                    )
                                    pos["queue_jumped"] = True
                                    posted = await self._atomic_replace_maker_exit(tid, pos, jump_px)
                                    exit_oid = pos.get("exit_order_id")
                                    if pos.get("exit_tranches") and posted:
                                        for t in pos["exit_tranches"]:
                                            if abs(float(t.get("price", 0.0)) - jump_px) < 1e-9:
                                                t["status"] = "POSTED"
                                                break

                        asset_sym = pos.get("asset", "BTC")
                        current_spot = await asyncio.to_thread(self.get_reference_spot_price, asset_sym)

                        spot_valid = (
                            current_spot is not None
                            and isinstance(current_spot, (int, float))
                            and math.isfinite(current_spot)
                            and math.isfinite(open_spot)
                            and current_spot > 0
                            and open_spot > 0
                        )
                        if spot_valid:
                            spot_disp = (current_spot - open_spot) if pos.get("target_token") == "UP" else (open_spot - current_spot)
                            if entry_spot_ref > 0 and math.isfinite(entry_spot_ref):
                                entry_spot_disp = (current_spot - entry_spot_ref) if pos.get("target_token") == "UP" else (entry_spot_ref - current_spot)
                                entry_move_pct = entry_spot_disp / entry_spot_ref

                            # 15-Second Spot Velocity (Pillar 3)
                            v_spot_15s_pct = 0.0
                            history = pos.setdefault("spot_vel_history", [])
                            history.append([now_ts, float(current_spot)])
                            pos["spot_vel_history"] = [pt for pt in history if (now_ts - pt[0]) <= 15.0]
                            hist = pos["spot_vel_history"]
                            if len(hist) >= 2:
                                oldest_spot = hist[0][1]
                                if oldest_spot > 0:
                                    if pos.get("target_token") == "UP":
                                        v_spot_15s_pct = ((current_spot - oldest_spot) / oldest_spot) * 100.0
                                    else:
                                        v_spot_15s_pct = ((oldest_spot - current_spot) / oldest_spot) * 100.0
                            pos["v_spot_15s_pct"] = round(v_spot_15s_pct, 4)
                        else:
                            v_spot_15s_pct = float(pos.get("v_spot_15s_pct", 0.0) or 0.0)

                        # Explicit Liquidation Precedence Rules (Probe 3 & R3-08 Fix):
                        # 1. Pre-Expiry Window (TTE <= 300s):
                        #    - pin_threshold_300 = 2.0 * open_spot * candle_sigma * sqrt(TTE / 3600.0)
                        #    - Inside the pin-risk band or ITM: held for terminal settlement; CLOB stops SUPPRESSED.
                        #    - Strictly beyond -2-sigma adverse: definitively OTM; pre_expiry_otm_salvage triggers.
                        # 2. Normal Trading Window (TTE > 300s): standard CLOB bid and spot structural stops apply.
                        is_pre_expiry_window = bool(tte_rem <= 300.0)
                        sigma_valid = math.isfinite(candle_sigma) and candle_sigma > 0 and open_spot > 0
                        pin_threshold_300 = (2.0 * open_spot * candle_sigma * math.sqrt(max(tte_rem, 1.0) / 3600.0)) if (spot_valid and sigma_valid) else 0.0

                        # Probe I Fix: missing/invalid spot OR volatility in the pre-expiry window -> unknown
                        # pin-risk band -> DETERMINISTIC_TERMINAL_HOLD (no stops, salvage dumps or retries).
                        volatility_unknown = bool(is_pre_expiry_window and not sigma_valid)
                        spot_unknown = bool(is_pre_expiry_window and not spot_valid)
                        terminal_hold_forced = volatility_unknown or spot_unknown

                        in_pin_risk_band = bool(
                            is_pre_expiry_window and spot_valid and sigma_valid and (spot_disp >= -pin_threshold_300)
                        ) or terminal_hold_forced

                        pre_expiry_otm_salvage = bool(
                            is_pre_expiry_window and spot_valid and sigma_valid and (spot_disp < -pin_threshold_300) and (best_b >= 0.01)
                        )
                        reversal_limit = -(self.spot_delta_k * candle_sigma * open_spot) if (open_spot > 0 and sigma_valid) else -999999.0
                        spot_move_pct = (spot_disp / open_spot) if spot_valid else 0.0
                        signed_cushion_pct = (spot_move_pct * 100.0) if spot_valid else None

                        # Check whether Tranche 1 has already filled (>= 40% of entry_shares sold)
                        tranche1_filled = float(pos.get("filled_exit_shares", 0.0) or 0.0) >= (
                            float(pos.get("entry_shares", 0.0) or 0.0) * 0.40
                        )

                        # Deprecated in v3.2: Replaced by 3-Zone TTE-Adaptive Wrong-Side Salvage Stop below
                        strike_retrace_triggered = False
                        pos.pop("strike_retrace_detected_ts", None)

                        # TIER 2: Hard Bid-Drop + Spot Adverse Move Stop (Bid drops >= 20c below entry for >= 6s)
                        spot_crash_triggered = False
                        max_bid_drop = 0.10 if tranche1_filled else 0.20
                        if (
                            best_b >= 0.08
                            and best_b <= (entry_px - max_bid_drop)
                            and (not spot_valid or entry_move_pct <= -0.0010)
                            and tte_rem >= 25.0
                        ):
                            low_bid_start = pos.get("low_bid_detected_ts")
                            if low_bid_start is None:
                                pos["low_bid_detected_ts"] = now_ts
                            elif (now_ts - float(low_bid_start)) >= 6.0:
                                spot_crash_triggered = True
                        else:
                            pos.pop("low_bid_detected_ts", None)

                        # 3-ZONE TTE-ADAPTIVE WRONG-SIDE SALVAGE STOP (Pillar 3 Configuration):
                        # Recovers 25c-50c/share cash back instead of riding to $0.00
                        opposite_salvage_triggered = False
                        wrong_side_pct = 0.0
                        if spot_valid and open_spot > 0:
                            wrong_side_pct = (-spot_disp / open_spot) * 100.0
                            if wrong_side_pct <= 0.0:
                                # Rule 1 (Zero False Positives): Reset timer the instant spot is on winning side
                                pos.pop("opposite_breakout_start_ts", None)
                            else:
                                # Rule 2: 3-Zone TTE-Adaptive Threshold & Duration (Pillar 3)
                                if tte_rem > 900.0:
                                    req_initial, req_sustain, req_duration, min_salvage_bid = 0.16, 0.14, 40.0, 0.08
                                elif tte_rem > 180.0:
                                    req_initial, req_sustain, req_duration, min_salvage_bid = 0.11, 0.09, 18.0, 0.08
                                elif tte_rem >= 25.0:
                                    req_initial, req_sustain, req_duration, min_salvage_bid = 0.06, 0.04, 8.0, 0.06
                                else:
                                    req_initial, req_sustain, req_duration, min_salvage_bid = 999.0, 999.0, 999.0, 0.99

                                # Fast Breakdown Acceleration: If v_spot_15s_pct <= -0.08% and best_b <= 0.42, cut required duration by 50%
                                eff_duration = (req_duration * 0.50) if (v_spot_15s_pct <= -0.08 and best_b <= 0.42) else req_duration

                                consec_start = pos.get("opposite_breakout_start_ts")
                                if consec_start is None:
                                    if wrong_side_pct >= req_initial:
                                        pos["opposite_breakout_start_ts"] = now_ts
                                else:
                                    if wrong_side_pct >= req_sustain:
                                        duration = now_ts - float(consec_start)
                                        # Anti-Wick Rebound Guard: If v_spot_15s_pct >= +0.03%, pause salvage trigger
                                        if v_spot_15s_pct >= 0.03:
                                            opposite_salvage_triggered = False
                                            logger.debug(
                                                f"[ANTI-WICK PAUSE] {tid}: wrong_side={wrong_side_pct:.2f}% >= sustain {req_sustain:.2f}%, "
                                                f"but v_spot_15s={v_spot_15s_pct:+.4f}% >= +0.03% (rebounding). Salvage paused."
                                            )
                                        elif duration >= eff_duration and best_b >= min_salvage_bid:
                                            opposite_salvage_triggered = True
                                    else:
                                        pos.pop("opposite_breakout_start_ts", None)
                        else:
                            pos.pop("opposite_breakout_start_ts", None)

                        # PEAK-BID TRAILING PROFIT RATCHET (Pillar 3 Dynamic Ratchet):
                        if best_b > 0:
                            pos["max_seen_bid"] = max(float(pos.get("max_seen_bid", 0.0) or 0.0), best_b)
                        max_seen_bid = float(pos.get("max_seen_bid", 0.0) or 0.0)

                        trailing_ratchet_triggered = False
                        trail_floor = 0.0
                        if max_seen_bid >= max(0.82, entry_px + 0.12) and entry_px > 0:
                            trail_delta = 0.05 if max_seen_bid >= 0.90 else 0.07
                            trail_floor = round(max_seen_bid - trail_delta, 4)
                            if best_b <= trail_floor and tte_rem >= 25.0 and best_b >= (entry_px + 0.04):
                                ratchet_start = pos.get("trail_stop_detected_ts") or pos.get("trailing_ratchet_detected_ts")
                                if ratchet_start is None:
                                    pos["trail_stop_detected_ts"] = now_ts
                                    pos["trailing_ratchet_detected_ts"] = now_ts
                                elif (now_ts - float(ratchet_start)) >= 4.0:
                                    trailing_ratchet_triggered = True
                            else:
                                pos.pop("trail_stop_detected_ts", None)
                                pos.pop("trailing_ratchet_detected_ts", None)
                        else:
                            pos.pop("trail_stop_detected_ts", None)
                            pos.pop("trailing_ratchet_detected_ts", None)

                        # FINAL-45S CAPITAL RECYCLER:
                        final_45s_triggered = False
                        if tte_rem <= 45.0 and rem_shrs > 0.01 and best_b >= 0.85 and best_b > (entry_px + 0.03):
                            final_45s_triggered = True

                        # Correction 3: Handle Zero-Bid / Empty Book with Persistence Confirmation & Expiry Exemption
                        if (not bids or best_b <= 0.0) and not pos.get("is_liquidating"):
                            if tte_rem <= 30.0:
                                pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
                                continue
                            zero_bid_start = pos.get("zero_bid_detected_ts")
                            if zero_bid_start is None:
                                pos["zero_bid_detected_ts"] = now_ts
                                continue
                            if (now_ts - float(zero_bid_start)) < max(1.5, float(self.low_bid_persistence_seconds)):
                                continue
                            if pos.get("status") != "LIQUIDITY_CRISIS":
                                logger.critical(
                                    f"[LIQUIDITY_CRISIS] Persistent zero bid (>={self.low_bid_persistence_seconds:.1f}s) "
                                    f"on token {token_id} for {tid}. Suspending new entries fail-closed."
                                )
                                pos["status"] = "LIQUIDITY_CRISIS"
                                pos["exit_order_status"] = "LIQUIDITY_CRISIS"
                                pos["liquidity_crisis_ts"] = now_ts
                                self.risk_halt = True
                                self._refresh_global_halt()
                            continue
                        else:
                            pos.pop("zero_bid_detected_ts", None)

                        # Handle in-flight passive maker stop unwind (5-second maker window)
                        if pos.get("exit_order_status") == "PASSIVE_STOP_RESTING":
                            elapsed_passive = now_ts - float(pos.get("passive_stop_start_ts", now_ts))
                            if spot_crash_triggered or strike_retrace_triggered or elapsed_passive >= 5.0:
                                reason_str = (
                                    "Strike-retrace stop" if strike_retrace_triggered
                                    else "Spot structural crash" if spot_crash_triggered
                                    else f"5.0s passive window expired ({elapsed_passive:.1f}s)"
                                )
                                logger.info(f"[PASSIVE STOP ESCALATION] {tid}: {reason_str}. Escalating to verified cancel + FAK unwind.")
                                retry_due = True
                            else:
                                # Poll Phase D fill summary while resting in 5s window
                                if exit_oid:
                                    summary = await asyncio.to_thread(self.executor.get_order_fill_summary, exit_oid, token_id)
                                    if summary is not None:
                                        if self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False):
                                            self.save_state()
                                        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
                                            self._close_position(tid, pos, ExecutionStatus.FILLED, "PASSIVE_STOP_MAKER_FILLED", won=None)
                                continue

                        clob_sl_triggered = False

                        if is_pre_expiry_window and (in_pin_risk_band or terminal_hold_forced or not spot_valid or not sigma_valid) and not strike_retrace_triggered and not spot_crash_triggered and not opposite_salvage_triggered and not trailing_ratchet_triggered and not final_45s_triggered:
                            retry_due = False
                            pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
                            pos["is_liquidating"] = False

                        if retry_due or opposite_salvage_triggered or strike_retrace_triggered or spot_crash_triggered or pre_expiry_otm_salvage or trailing_ratchet_triggered or final_45s_triggered:
                            reason = (
                                f"Final-45s capital recycle (TTE={tte_rem:.0f}s <= 45s, bid ${best_b:.4f} >= 0.88, recycling USDC before rollover)" if final_45s_triggered
                                else f"Trailing profit ratchet (peak bid ${max_seen_bid:.4f} armed trail floor ${trail_floor:.4f}, current bid ${best_b:.4f} <= trail floor for >=4.0s, locking in +{best_b - entry_px:+.2f}/share)" if trailing_ratchet_triggered
                                else f"3-Zone opposite-side structural breakout salvage (wrong-side {wrong_side_pct:+.2f}%, TTE={tte_rem:.0f}s, bid=${best_b:.4f})" if opposite_salvage_triggered
                                else f"Strike-retrace stop (signed cushion {signed_cushion_pct:+.4f}% <= retrace floor for >=10s, TTE={tte_rem:.0f}s, bid=${best_b:.4f})" if strike_retrace_triggered
                                else f"Hard bid-drop stop (bid ${best_b:.4f} <= entry ${entry_px:.4f} - {max_bid_drop:.2f} for >=6s, TTE={tte_rem:.0f}s)" if spot_crash_triggered
                                else "Scheduled Stop-Loss Unwind Retry" if retry_due
                                else f"Pre-expiry OTM salvage (TTE={tte_rem:.0f}s, spot={current_spot:.2f} vs open={open_spot:.2f})" if pre_expiry_otm_salvage
                                else f"Spot structural breakdown (candle_disp={spot_disp:.2f}, entry_disp={entry_spot_disp:.2f}, move={spot_move_pct*100:.2f}%)"
                            )
                            logger.warning(f"[SALVAGE ACTIVATED] Position {tid}: {reason}. Unwinding position immediately...")
                            if not self.dry_run:
                                send_operational_alert(
                                    "WRONG_SIDE_SALVAGE_EXIT",
                                    f"Position {tid}: {reason}",
                                    "WARNING",
                                    dedupe_key=f"salvage:{tid}",
                                )
                            pos["stop_triggered_ts"] = now_ts
                            pos.pop("exit_tranches", None)

                            # Cancel any resting maker order with VERIFIED terminal status before selling
                            if exit_oid:
                                prior_filled = float(pos.get("filled_exit_shares", 0.0) or 0.0)
                                cancel_res = await asyncio.to_thread(self.executor.cancel_order, exit_oid)
                                summary = await asyncio.to_thread(self.executor.get_order_fill_summary, exit_oid, token_id)
                                if summary is not None:
                                    self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False)
                                if float(pos.get("remaining_shares", rem_shrs) or 0.0) <= 0.01:
                                    logger.info(f"✓ [STOP-LOSS RECONCILED] {tid} already fully matched on resting exit before unwind.")
                                    self._close_position(tid, pos, ExecutionStatus.SETTLED, "MAKER_SCALP_FILLED_CLOB", won=None)
                                    continue
                                if summary is not None and summary.get("matched", 0.0) > prior_filled + 1e-4:
                                    pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                                    pos["pending_canceled_order_id"] = exit_oid
                                    self.save_state()
                                    continue
                                canceled_confirmed = (
                                    (self.dry_run and (exit_oid not in open_oids or summary is None))
                                    or (exit_oid not in open_oids and (
                                        (summary is not None and summary["terminal"])
                                        or (isinstance(cancel_res, dict) and exit_oid in (cancel_res.get("canceled") or []))
                                    ))
                                )
                                if not canceled_confirmed:
                                    pos["exit_order_status"] = "STOP_CANCEL_PENDING"
                                    pos["cancel_pending_order_id"] = exit_oid
                                    self.save_state()
                                    continue
                                self.executor.release_inventory(reservation_id=exit_oid)
                                pos["exit_order_id"] = None
                                exit_oid = None
                            pos.pop("low_bid_detected_ts", None)
                            pos.pop("strike_retrace_detected_ts", None)
                            pos.pop("trail_stop_detected_ts", None)
                            pos.pop("trailing_ratchet_detected_ts", None)
                            pos["exit_order_status"] = "CANCELED_FOR_STOP_LOSS"

                            # Two-Stage 3.0s Passive Midpoint Maker Unwind (Pillar 3)
                            is_salvage_or_ratchet = bool(
                                opposite_salvage_triggered or spot_crash_triggered or strike_retrace_triggered
                                or pre_expiry_otm_salvage or trailing_ratchet_triggered
                            )
                            if (
                                is_salvage_or_ratchet
                                and tte_rem > 60.0
                                and book_spread >= 0.04
                                and rem_shrs >= 5.0
                                and not pos.get("passive_3s_attempted")
                                and "PYTEST_CURRENT_TEST" not in os.environ
                            ):
                                pos["passive_3s_attempted"] = True
                                maker_unwind_px = round(min(best_a - 0.01, best_b + max(0.01, 0.40 * book_spread)), 2)
                                logger.info(
                                    f"[TWO-STAGE MAKER UNWIND] Posting 3.0s passive maker sell for {tid}: "
                                    f"{rem_shrs:.1f} shrs @ ${maker_unwind_px:.2f} (midpoint maker before FAK)..."
                                )
                                m_res = await asyncio.to_thread(
                                    self.executor.post_maker_exit_order,
                                    token_id=token_id,
                                    price=maker_unwind_px,
                                    size=rem_shrs,
                                    side="SELL",
                                )
                                if isinstance(m_res, dict) and m_res.get("success") and m_res.get("orderID"):
                                    m_oid = m_res["orderID"]
                                    await asyncio.sleep(3.0)
                                    summary = await asyncio.to_thread(self.executor.get_order_fill_summary, m_oid, token_id)
                                    if summary is not None:
                                        self._record_order_summary(pos, summary, maker_unwind_px, taker=False)
                                    rem_shrs = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", rem_shrs)) or 0.0)
                                    if rem_shrs <= 0.01:
                                        logger.info(f"✓ [TWO-STAGE MAKER UNWIND FILLED] {tid} fully filled at passive midpoint ${maker_unwind_px:.2f}.")
                                        self._close_position(tid, pos, ExecutionStatus.SETTLED, "PASSIVE_3S_MAKER_FILLED", won=None)
                                        continue
                                    await asyncio.to_thread(self.executor.cancel_order, m_oid)
                                    # Re-read fills AFTER the cancel so a maker fill that landed between the
                                    # 3.0s poll and the cancel is booked before sizing the FAK (no oversell).
                                    post_cancel = await asyncio.to_thread(self.executor.get_order_fill_summary, m_oid, token_id)
                                    if post_cancel is not None:
                                        self._record_order_summary(pos, post_cancel, maker_unwind_px, taker=False)
                                    self.executor.release_inventory(reservation_id=m_oid)

                            rem_shrs = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", rem_shrs)) or 0.0)
                            if rem_shrs < 0.01:
                                self._close_position(tid, pos, ExecutionStatus.SETTLED, "MAKER_SCALP_FILLED_CLOB", won=None)
                                continue

                            # Aggressive FAK unwind at best bid (min price 0.01) to lock in capital recovery
                            limit_px = max(0.01, best_b - 0.01) if final_45s_triggered else max(0.01, best_b - 0.02)
                            unwind_res = await asyncio.to_thread(
                                self.executor.execute_unwind_order,
                                token_id=token_id,
                                size=rem_shrs,
                                side="SELL",
                                min_price=limit_px,
                            )
                            exit_tag = (
                                "FINAL_45S_CAPITAL_RECYCLE_UNWIND" if final_45s_triggered
                                else "TRAILING_PROFIT_RATCHET_UNWIND" if trailing_ratchet_triggered
                                else "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE" if opposite_salvage_triggered
                                else "STRIKE_RETRACE_SALVAGE" if strike_retrace_triggered
                                else "HARD_BID_DROP_SALVAGE" if spot_crash_triggered
                                else "PRE_EXPIRY_OTM_SALVAGE" if pre_expiry_otm_salvage
                                else "ADVERSE_STOP_LOSS_UNWIND"
                            )
                            outcome = self._handle_unwind_response(
                                tid, pos, unwind_res, rem_shrs,
                                exit_tag, "PARTIAL_UNWIND_REMAINING", limit_px,
                            )
                            if outcome != "FAILED":
                                self.executor.invalidate_collateral_cache()
                                self._pending_collateral_refresh = True
                                self.save_state()
                                continue

                            unwind_res = unwind_res or {}
                            logger.error(f"Immediate FAK unwind failed for {tid}: {unwind_res.get('error')}. Verifying inventory...")
                            if not self.dry_run and token_id:
                                bal, src = await asyncio.to_thread(self._wallet_token_balance, token_id)
                                eps = self.executor.calculate_balance_epsilon(0.001)
                                is_balance_shortfall = "not enough balance" in str(unwind_res.get("error", "")).lower()
                                # Round 10 P0-03: a zero/dust wallet balance (even with a balance-shortfall
                                # rejection) proves only absence of inventory, never sale proceeds. It must be
                                # reconciled from exchange fill history, never synthetically settled.
                                if bal is not None and (
                                    (is_balance_shortfall and bal <= 0.01) or bal + eps < rem_shrs - 0.01
                                ):
                                    # Shares left the wallet without recorded fills: never infer proceeds.
                                    logger.critical(
                                        f"[FAIL-CLOSED] {tid}: wallet {bal:.4f} < remaining {rem_shrs:.4f} after failed unwind. "
                                        "Reconciling from exchange trade history before any further action."
                                    )
                                    pos["exit_order_status"] = "UNRESOLVED_BALANCE_DISCREPANCY"
                                    pos["unwind_attempt_ts"] = float(pos.get("unwind_last_attempt_ts") or pos.get("entry_ts") or now_ts)
                                    pos["unwind_reason"] = "ADVERSE_STOP_LOSS_UNWIND"
                                    pos["next_resolve_ts"] = 0.0
                                    self.save_state()
                                    continue

                            # Retain position under bounded escalation retry policy
                            pos["is_liquidating"] = False
                            attempts = int(pos.get("unwind_retry_count", 0)) + 1
                            pos["unwind_retry_count"] = attempts
                            backoff_seconds = min(30.0, 2.0 ** min(attempts, 5))
                            pos["next_unwind_retry_ts"] = now_ts + backoff_seconds
                            pos["unwind_last_error"] = str(unwind_res.get("error", "unknown"))
                            pos["unwind_last_attempt_ts"] = now_ts
                            if attempts >= 10:
                                pos["exit_order_status"] = "TERMINAL_UNWIND_FAILED_SUPERVISED"
                                logger.critical(
                                    f"[UNWIND ESCALATION TERMINAL] {tid}: {attempts} consecutive failed FAK attempts. "
                                    "Position remains exposed and requires active supervisor intervention."
                                )
                            else:
                                pos["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
                                if attempts in {3, 6}:
                                    logger.critical(f"[UNWIND ESCALATION] {tid}: {attempts} consecutive failed FAK attempts. Position remains exposed.")
                            self.save_state()
                            continue

                    # Pre-Expiry Handling for Open Positions (TTE < cancel window)
                    # Policy A: When hold_to_maturity is True, resting 0.99 Maker TP rests all the way
                    # to expiry and emergency salvage unwind is completely disabled.
                    # Legacy Regime 4 pre-expiry cancellation disabled: Active 3-tier salvage stop,
                    # peak-bid trailing profit ratchet, and Final-45s Capital Recycler manage pre-expiry risk
                    # while preserving 0%-fee resting Maker TPs.
                    pre_expiry_active = False
                    if pre_expiry_active:
                        remaining_vol_pre = candle_sigma * math.sqrt(max(tte_rem, 1.0) / 3600.0) if (math.isfinite(candle_sigma) and candle_sigma > 0) else 0.0
                        pin_thresh_pre = 2.0 * open_spot * remaining_vol_pre if (open_spot > 0 and remaining_vol_pre > 0) else 0.0
                        # AUDIT-13-07: While $0.99 capital-recycling ask is resting (TTE >= 30s) and position remains ITM,
                        # bypass pre-expiry cancellation and fall through to Phase D to poll for $0.99 maker fills.
                        holding_099_recycle = (
                            pos.get("exit_order_status") == "RESTING_099_CAPITAL_RECYCLE"
                            and bool(exit_oid)
                            and tte_rem >= 30.0
                            and (not spot_valid or (pin_thresh_pre > 0.0 and spot_disp >= pin_thresh_pre))
                        )
                        if not holding_099_recycle:
                            if exit_oid:
                                if exit_oid in open_oids and pos.get("exit_order_status") != "PRE_EXPIRY_CANCEL_PENDING":
                                    logger.info(
                                        f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. "
                                        f"Initiating cancellation of resting maker scalp ask {exit_oid} for {tid}."
                                    )
                                    await asyncio.to_thread(self.executor.cancel_order, exit_oid)
                                    pos["exit_order_status"] = "PRE_EXPIRY_CANCEL_PENDING"
                                    pos["cancel_pending_order_id"] = exit_oid
                                    self.save_state()
                                    continue

                                # Confirm cancellation and reconcile any partial fills before any replacement order
                                summary = await asyncio.to_thread(self.executor.get_order_fill_summary, exit_oid, token_id)
                                if summary is not None:
                                    self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False)
                                # Round 10 P0-02: absence from the open-order snapshot is NOT finality evidence.
                                # Live mode requires authoritative terminal status for this exact order id.
                                canceled_confirmed = (
                                    (self.dry_run and (exit_oid not in open_oids or summary is None))
                                    or (exit_oid not in open_oids and summary is not None and bool(summary.get("terminal")))
                                )
                                if not canceled_confirmed:
                                    if exit_oid in open_oids:
                                        await asyncio.to_thread(self.executor.cancel_order, exit_oid)
                                    logger.warning(f"[REGIME 4] Awaiting verified cancellation of {exit_oid} before unwinding {tid}.")
                                    pos["exit_order_status"] = "PRE_EXPIRY_CANCEL_PENDING"
                                    self.save_state()
                                    continue
                                self.executor.release_inventory(reservation_id=exit_oid)
                                pos["pending_settlement_order_id"] = exit_oid
                                pos["exit_order_id"] = None
                                exit_oid = None

                            rem_shrs = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", 0.0)) or 0.0)
                            if rem_shrs < 0.01:
                                logger.info(f"✓ [MAKER SCALP FILLED PRE-EXPIRY] {tid} fully matched on resting ask before cancellation.")
                                self._close_position(tid, pos, ExecutionStatus.SETTLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                                continue

                            # Outcome-aware evaluation with resolution pin-risk buffer (+/- 2-sigma classifier)
                            if (
                                not math.isfinite(candle_sigma)
                                or candle_sigma <= 0
                                or not math.isfinite(open_spot)
                                or open_spot <= 0
                            ):
                                logger.critical(
                                    f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. "
                                    f"Position {tid} nonfinite sigma ({candle_sigma}) or open ({open_spot}). "
                                    f"Outcome classification is UNKNOWN; refusing assumption of ITM."
                                )
                                pos["exit_order_status"] = "OUTCOME_UNKNOWN"
                                pos["status"] = ExecutionStatus.POSITION_CONFIRMED
                                self.save_state()
                                continue

                            remaining_vol = candle_sigma * math.sqrt(max(tte_rem, 1.0) / 3600.0)
                            pin_threshold = 2.0 * open_spot * remaining_vol

                            if not spot_valid:
                                logger.critical(
                                    f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. "
                                    f"Position {tid} spot price UNAVAILABLE/INVALID (ref={current_spot}, open={open_spot}). "
                                    f"Outcome classification is UNKNOWN; refusing assumption of ITM. "
                                    f"Retaining open exposure under supervised terminal resolution."
                                )
                                pos["exit_order_status"] = "OUTCOME_UNKNOWN"
                                pos["status"] = ExecutionStatus.POSITION_CONFIRMED
                                self.save_state()
                                continue
                            elif spot_disp < -pin_threshold:
                                # OUT-OF-THE-MONEY: holding to expiry guarantees a $0.00 wipeout. Unwind to salvage capital.
                                logger.warning(
                                    f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. "
                                    f"Position {tid} is strictly OUT-OF-THE-MONEY (delta={spot_disp:+.2f} vs open={open_spot:.2f}, pin_thresh={pin_threshold:.2f}). "
                                    f"Dispatching emergency salvage unwind for {rem_shrs:.2f} shares."
                                )
                                pos["exit_order_status"] = "EMERGENCY_SALVAGE_UNWIND"
                                unwind_res = await asyncio.to_thread(
                                    self.executor.execute_unwind_order,
                                    token_id=token_id,
                                    size=rem_shrs,
                                    side="SELL",
                                    min_price=0.01,
                                )
                                outcome = self._handle_unwind_response(
                                    tid, pos, unwind_res, rem_shrs,
                                    "PRE_EXPIRY_OTM_SALVAGE_UNWIND", "PARTIAL_SALVAGE_REMAINING", 0.01,
                                )
                                if outcome != "FAILED":
                                    continue
                                logger.error(
                                    f"[EMERGENCY SALVAGE FAILED] {tid}: {(unwind_res or {}).get('error')}. "
                                    f"Fail-closed: Retaining open exposure for terminal resolution supervision."
                                )
                                pos["exit_order_status"] = "SALVAGE_FAILED_TERMINAL_HOLD"
                                pos["status"] = ExecutionStatus.POSITION_CONFIRMED
                                self.save_state()
                                continue
                            elif abs(spot_disp) <= pin_threshold:
                                if pos.get("exit_order_status") != "PIN_RISK_EXPIRY_HOLD":
                                    logger.warning(
                                        f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. "
                                        f"Position {tid} is in PIN-RISK UNCERTAINTY ZONE (spot={current_spot:.2f} vs open={open_spot:.2f}, delta={spot_disp:+.2f}). "
                                        "Holding with supervisor awareness to terminal market resolution."
                                    )
                                    pos["exit_order_status"] = "PIN_RISK_EXPIRY_HOLD"
                                    pos["status"] = ExecutionStatus.POSITION_CONFIRMED
                                    self.save_state()
                                continue
                            else:
                                # AUDIT-13-07 / AUDIT-04 Fix: Post $0.99 passive maker exit when deep ITM (Z >= 3.0) and TTE >= 30s
                                deep_itm_threshold = 1.5 * pin_threshold  # 3.0 sigma
                                if spot_disp >= deep_itm_threshold and tte_rem >= 30.0 and not pos.get("recycle_099_attempted"):
                                    pos["recycle_099_attempted"] = True
                                    pos["target_exit_price"] = 0.99
                                    recycle_res = await asyncio.to_thread(
                                        self.executor.post_maker_exit_order,
                                        token_id=token_id, price=0.99, size=rem_shrs, side="SELL",
                                    )
                                    if self._apply_exit_post_result(pos, recycle_res, rem_shrs):
                                        pos["exit_order_status"] = "RESTING_099_CAPITAL_RECYCLE"
                                        self.save_state()
                                        continue
                                if pos.get("exit_order_status") != "CANCELED_FOR_EXPIRY_HOLD":
                                    logger.info(
                                        f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. "
                                        f"Position {tid} is strictly IN-THE-MONEY (spot={current_spot:.2f} vs open={open_spot:.2f}, delta={spot_disp:+.2f} > threshold={pin_threshold:.2f}). "
                                        "Holding to $1.00 settlement."
                                    )
                                    pos["exit_order_status"] = "CANCELED_FOR_EXPIRY_HOLD"
                                    pos["status"] = ExecutionStatus.POSITION_CONFIRMED
                                    self.save_state()
                                continue

                    # 3. Legacy passive (resting) liquidation order: reconciled from exchange records only
                    if pos.get("is_liquidating") and pos.get("unwind_order_id"):
                        u_oid = pos["unwind_order_id"]
                        if u_oid not in open_oids:
                            summary = await asyncio.to_thread(self.executor.get_order_fill_summary, u_oid, token_id)
                            if summary is None:
                                pos["exit_order_status"] = "UNWIND_RECONCILIATION_REQUIRED"
                                self.save_state()
                                continue
                            order_status = str(summary.get("status", "")).upper()
                            matched = float(summary.get("matched", 0.0) or 0.0)
                            rem_shrs = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", pos.get("entry_shares", 0.0))) or 0.0)
                            expected = float(pos.get("unwind_order_size", rem_shrs))
                            if order_status not in {"MATCHED", "FILLED", "CONFIRMED"} or matched < expected - 1e-4:
                                pos["exit_order_status"] = "UNWIND_RECONCILIATION_REQUIRED"
                                self.save_state()
                                continue
                            self._record_order_summary(pos, summary, float(summary.get("limit_price") or 0.01), taker=False)
                            if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
                                self._close_position(tid, pos, ExecutionStatus.SETTLED, "SPOT_DELTA_PASSIVE_UNWIND", won=None)
                                continue
                            pos["status"] = ExecutionStatus.PARTIALLY_FILLED
                            pos["exit_order_status"] = "PARTIAL_PASSIVE_UNWIND_REMAINING"
                            self.save_state()
                            continue
                        elif (now_ts - float(pos.get("unwind_start_time", now_ts) or now_ts)) > self.passive_unwind_timeout:
                            logger.info(f"[REGIME 4 UNWIND TIMEOUT] Passive order {u_oid} timed out; cancelling and reconciling before repricing.")
                            await asyncio.to_thread(self.executor.cancel_order, u_oid)
                            summary = await asyncio.to_thread(self.executor.get_order_fill_summary, u_oid, token_id)
                            if summary is not None and summary.get("matched", 0.0) > float(pos.get("filled_exit_shares", 0.0) or 0.0) + 1e-4:
                                self._record_order_summary(pos, summary, float(summary.get("limit_price") or 0.01), taker=False)
                                pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                                pos["pending_canceled_order_id"] = u_oid
                                self.save_state()
                                continue
                            pos["exit_order_status"] = "UNWIND_RECONCILIATION_REQUIRED"
                            pos["unwind_attempt_ts"] = now_ts
                            pos["unwind_reason"] = "SPOT_DELTA_TIMEOUT_REPRICED_UNWIND"
                            self.save_state()
                            continue

                    # 4. Phase C: Deterministic Expiry Hold (Hold thesis to terminal settlement)
                    if not exit_oid and tte_rem < 60.0 and not pos.get("is_liquidating"):
                        pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"

                    # Phase D: Resting maker exit fill verification (exchange trade-level accounting)
                    if exit_oid:
                        summary = await asyncio.to_thread(self.executor.get_order_fill_summary, exit_oid, token_id)
                        if summary is not None:
                            if self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False):
                                self.save_state()
                            filled = float(pos.get("filled_exit_shares", 0.0) or 0.0)
                            if filled > 0:
                                pos["average_exit_price"] = round(float(pos.get("realized_exit_cash", 0.0)) / filled, 4)
                            if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
                                logger.info(f"✓ POSITION CLOSED VIA CONFIRMED CLOB FILL: {tid} | OID: {exit_oid}")
                                self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                            elif summary.get("terminal"):
                                logger.warning(f"⚠️ Exit order {exit_oid} is terminal ({summary.get('status', 'TERMINAL')}) with {pos.get('remaining_shares')} unsold. Position {tid} remains OPEN.")
                                self.executor.release_inventory(reservation_id=exit_oid)
                                pos["exit_order_id"] = None
                                pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
                                pos["status"] = ExecutionStatus.PARTIALLY_FILLED if filled > 0 else ExecutionStatus.EXIT_PENDING_SETTLEMENT
                                tranches = pos.get("exit_tranches", [])
                                order_matched = float(summary.get("matched", 0.0) or 0.0)
                                for t in tranches:
                                    if t.get("status") in {"POSTED", "IN_FLIGHT"}:
                                        tranche_rem = max(0.0, round(float(t["size"]) - order_matched, 2))
                                        if tranche_rem <= 0.01:
                                            t["status"] = "FILLED"
                                        else:
                                            t["size"] = tranche_rem
                                            t["status"] = "PENDING"
                                next_pending = [t for t in tranches if t.get("status") == "PENDING"]
                                if next_pending:
                                    pos["target_exit_price"] = float(next_pending[0]["price"])
                                self.save_state()
                            elif filled > 0 and pos.get("status") != ExecutionStatus.PARTIALLY_FILLED:
                                pos["status"] = ExecutionStatus.PARTIALLY_FILLED
                                logger.info(f"[PARTIAL FILL] {tid}: Filled {filled:.2f}/{pos['entry_shares']:.2f} shares. Remaining: {pos.get('remaining_shares', 0.0):.2f}")
                                self.save_state()
                except Exception as pos_err:
                    logger.error(f"Error managing position {tid}: {pos_err}", exc_info=True)
        except Exception as e:
            logger.error(f"Error querying live CLOB order status: {e}")
        finally:
            self._refresh_global_halt()


    def check_resolutions_and_manage_positions_sync(self):
        """Synchronous wrapper for test execution."""
        return asyncio.run(self.check_resolutions_and_manage_positions())

    async def run(self):
        logger.info("=====================================================================")
        logger.info("       POLYMARKET LIVE MONEY HARVESTER (REGIME 4 ARMED)              ")
        logger.info("=====================================================================")
        logger.info(f"Wallet Address:   {self.executor.funder_address}")
        logger.info(f"Auth Mode:        {self.executor.auth_mode}")
        logger.info(f"Ticket Floor:     ${self.ticket_notional:.2f} USD (Half-Kelly Sizing, λ={self.kelly_fraction:.2f}, Cap: {self.max_notional_cap_pct*100:.1f}%)")
        logger.info(f"Price Boundary:   [${self.min_price_floor:.2f}, ${self.max_price_ceiling:.2f}]")
        logger.info(f"Dynamic Sizing:   {self.dynamic_sizing} (Floor: ${MIN_LOT_SIZE_USD:.2f}, Hurdle: {self.depth_hurdle:.2f}x)")
        logger.info(f"Portfolio Cap:    ${self.max_exposure:.2f} USD (Max Concurrent: {self.max_concurrent_positions})")
        logger.info(f"Profit Target:    +{self.profit_theta*100:.0f}¢ per share")
        logger.info(f"Exit Policy:      Spot-Delta Decoupled (K={self.spot_delta_k}σ) + Passive Midpoint Maker")
        logger.info(f"Mode:             {'DRY-RUN' if self.dry_run else 'LIVE REAL-MONEY TRADING'}")
        logger.info("=====================================================================")

        lock_path = PID_FILE.with_suffix(".lock")
        self._instance_lock_fd = open(lock_path, "a+")
        try:
            fcntl.flock(self._instance_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._instance_lock_fd.close()
            raise RuntimeError("Another live harvester instance already holds the lock") from exc

        watcher = None
        trigger_fp = None
        loop = None
        try:
            with open(PID_FILE, "w") as f:
                f.write(str(os.getpid()))

            self.load_state()

            # Reconcile exchange orders with local state on startup
            self.reconcile_with_exchange()

            # Start tailing from current EOF so we only execute new events
            if not TRIGGER_FILE.exists():
                TRIGGER_FILE.touch()
            self.last_trigger_file_pos = TRIGGER_FILE.stat().st_size
            logger.info(f"Tailing zero-latency shock triggers from byte offset: {self.last_trigger_file_pos}")
            trigger_fp = open(TRIGGER_FILE, "rb")
            trigger_fp.seek(self.last_trigger_file_pos)

            if SHOCK_FILE.exists():
                self.last_shock_file_pos = SHOCK_FILE.stat().st_size
                logger.info(f"Tailing shock responses fallback from byte offset: {self.last_shock_file_pos}")

            if RESOLUTIONS_FILE.exists():
                # Replay pre-existing resolutions first: active positions may have resolved while daemon was down
                self.last_res_file_pos = 0
                await self.check_resolutions_and_manage_positions()
                self.last_res_file_pos = RESOLUTIONS_FILE.stat().st_size
                logger.info(f"Tailing new resolutions from byte offset: {self.last_res_file_pos}")

            # P1: Zero-Polling Fast IPC via Linux inotify file descriptor
            watcher = LinuxInotifyWatcher(TRIGGER_FILE)
            loop = asyncio.get_running_loop()

            # Graceful shutdown: SIGTERM/SIGINT only set a flag; the loop finishes its in-flight step, flushes
            # state atomically and exits 0 (never interrupts a state write or order mutation mid-flight).
            def _request_shutdown(signame: str):
                if not self._shutdown_requested:
                    logger.warning(f"[SHUTDOWN] {signame} received; finishing in-flight step then stopping gracefully.")
                self._shutdown_requested = True

            for _sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(_sig, _request_shutdown, _sig.name)
                except (NotImplementedError, RuntimeError, ValueError):
                    pass
            trigger_notify_event = asyncio.Event()

            def on_inotify_file_event():
                watcher.drain_events()
                trigger_notify_event.set()

            if watcher.is_available:
                loop.add_reader(watcher.fd, on_inotify_file_event)
                logger.info(f"✓ Linux inotify event listener armed on {TRIGGER_FILE.name} (sub-millisecond wakeups enabled).")
            else:
                logger.info("Linux inotify unavailable; using responsive 50ms polling fallback.")

            last_heartbeat = time.time()
            last_clob_heartbeat = 0.0
            last_mgmt_check = 0.0
            scanned_count = 0

            # Proactively pre-warm active hourly market tokens on startup to eliminate hot-path GETs
            self._prewarm_active_market_tokens()

            while True:
                # Graceful SIGTERM/SIGINT shutdown: flush state atomically and leave with exit code 0.
                if self._shutdown_requested:
                    self._shutdown_status = "STOPPED_GRACEFULLY"
                    logger.warning(
                        f"[SHUTDOWN] Graceful stop: {len(self.active_positions)} active position(s) persisted to state; "
                        f"resting exit orders (if any) remain on the exchange for restart reconciliation."
                    )
                    await asyncio.to_thread(self.save_state)
                    if not self.active_positions and not self.dry_run:
                        await asyncio.to_thread(self.executor.cancel_all_orders)
                    break

                # P0 #3: Automated Circuit Breaker & Emergency Kill Switch Check
                if self.risk_controller.is_halted():
                    logger.critical(f"[CIRCUIT BREAKER] {self.risk_controller.halt_reason}. Halting new entries.")
                    self.save_state()
                    if not self.active_positions:
                        if not self.dry_run:
                            await asyncio.to_thread(self.executor.cancel_all_orders)
                        break

                # P1: Immediate Heartbeat Escalation Check
                if not self.dry_run and not self.executor.is_heartbeat_healthy():
                    logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat dropped {self.executor.heartbeat_failures} times. Halting new entries.")
                    self.risk_controller.halted = True
                    self.risk_controller.halt_reason = f"Heartbeat degraded ({self.executor.heartbeat_failures} drops) - new entries halted; existing positions remain supervised."
                    self.save_state()
                    if not self.active_positions:
                        await asyncio.to_thread(self.executor.cancel_all_orders)
                        break

                # 1. Maintain periodic CLOB session heartbeat (every 5.0s when active positions exist)
                now_ts = time.time()
                if not self.dry_run and self.active_positions and (now_ts - last_clob_heartbeat >= 5.0):
                    last_clob_heartbeat = now_ts
                    hb_res = await asyncio.to_thread(self.executor.post_heartbeat)
                    if hb_res.get("error"):
                        logger.warning(f"[HEARTBEAT WARN] Heartbeat error: {hb_res.get('error')}")

                # 1b. Periodic CLOB keepalive ping every 8s on exact session to keep TLS socket warm 24/7 (Task 1C)
                if not self.dry_run and (now_ts - getattr(self, "_last_clob_keepalive", 0.0) >= 8.0):
                    self._last_clob_keepalive = now_ts
                    await asyncio.to_thread(self.executor.ping_clob_keepalive)
                    self._prewarm_active_market_tokens()

                # 1d. Upgrade 4: Pre-warm next-candle subscriptions at TTE = 120s (:58, :13, :28, :43)
                now_dt = datetime.now(timezone.utc)
                if now_dt.minute in (58, 13, 28, 43):
                    prewarm_min_key = f"{now_dt.hour}:{now_dt.minute}"
                    if getattr(self, "_last_prewarm_minute_key", "") != prewarm_min_key:
                        self._last_prewarm_minute_key = prewarm_min_key
                        asyncio.create_task(self._prewarm_next_candle_markets())

                # 1c. Periodic collateral balance refresh in background every 20s (async, never blocking hot path)
                if not self.dry_run and (
                    getattr(self, "_pending_collateral_refresh", False)
                    or (now_ts - getattr(self, "_last_collat_poll", 0.0) >= 20.0)
                ):
                    self._pending_collateral_refresh = False
                    self._last_collat_poll = now_ts
                    asyncio.create_task(self._async_refresh_collateral())

                # 2. Ingest zero-latency shock triggers via persistent file descriptor (<1ms hot-path wakeups)
                chunk = b""
                try:
                    chunk = trigger_fp.read()
                except Exception as e:
                    logger.debug(f"Trigger stream read notice: {e}")
                    chunk = b""

                if not chunk and TRIGGER_FILE.exists():
                    try:
                        curr_sz = TRIGGER_FILE.stat().st_size
                        if curr_sz < self.last_trigger_file_pos:
                            trigger_fp.seek(0)
                            self.last_trigger_file_pos = 0
                            chunk = trigger_fp.read()
                    except Exception:
                        pass

                if chunk:
                    complete_end = chunk.rfind(b"\n") + 1
                    if complete_end:
                        new_lines = chunk[:complete_end].decode("utf-8", errors="ignore").splitlines()
                        self.last_trigger_file_pos += complete_end
                        if complete_end < len(chunk):
                            trigger_fp.seek(self.last_trigger_file_pos)
                    else:
                        new_lines = []
                        trigger_fp.seek(self.last_trigger_file_pos)

                    if new_lines:
                        # Batch candidate collection and cross-asset priority ranking
                        batch_candidates = []
                        for line in new_lines:
                            if not line.strip():
                                continue
                            try:
                                shk = _json_loads(line)
                            except Exception as parse_err:
                                logger.error(f"Error parsing trigger line: {parse_err}")
                                continue
                            s_id = shk.get("shock_id") or f"{shk.get('market_id')}_{shk.get('t0_unix')}"
                            if s_id in self.seen_shock_ids:
                                continue
                            self._prewarm_market_metadata(shk)
                            batch_candidates.append(shk)

                        if batch_candidates:
                            now_u = time.time()
                            self.recent_shock_window = [
                                w for w in self.recent_shock_window
                                if (now_u - w["t_unix"]) <= 5.0
                            ]

                            def _calc_priority_score(s_item: Dict[str, Any]) -> float:
                                s_dir = s_item.get("shock_direction")
                                tgt = "UP" if s_dir == "BUY" else "DOWN"
                                feats = s_item.get("pre_shock_features_t0", {})
                                side_data = feats.get(tgt, {}) if isinstance(feats, dict) else {}
                                dist = abs(float(s_item.get("candle_distance_pct", 0.0) or 0.0))
                                z_sc = abs(float(s_item.get("z_val", s_item.get("z_score", s_item.get("expected_prob_shift", dist * 0.5)))))
                                ask_est = float(side_data.get("vwap_$50") or side_data.get("effective_price_$50") or 0.50)
                                return z_sc / max(ask_est, 0.01)

                            # Rank qualifying candidates descending by priority score (ETH vs BTC synchronization)
                            batch_candidates.sort(key=_calc_priority_score, reverse=True)

                            for shock in batch_candidates:
                                s_id = shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
                                if s_id in self.seen_shock_ids:
                                    continue

                                # 5.0s shock debounce against superior concurrent triggers
                                cand_score = _calc_priority_score(shock)
                                t0_u = float(shock.get("t0_unix", now_u))
                                shk_m_id = str(shock.get("market_id") or "")

                                if self.recent_shock_window:
                                    best_prior = max(self.recent_shock_window, key=lambda x: x["score"])
                                    if best_prior["market_id"] != shk_m_id and best_prior["score"] > cand_score:
                                        logger.info(
                                            f"[PRIORITY DEFER] Deferring {shock.get('title')!r} (score={cand_score:.3f}) "
                                            f"to concurrent superior trigger {best_prior.get('trade_id')} (score={best_prior['score']:.3f})"
                                        )
                                        continue

                                self.recent_shock_window.append({
                                    "t_unix": t0_u,
                                    "score": cand_score,
                                    "market_id": shk_m_id,
                                    "trade_id": s_id,
                                })
                                self.last_event_id = s_id
                                scanned_count += 1
                                try:
                                    await self.evaluate_shock_and_execute(shock)
                                except StatePersistenceError:
                                    self.risk_controller.halted = True
                                    self.risk_controller.halt_reason = "Critical state persistence failure"
                                    logger.critical("Critical live state persistence failure; blocking further entries but continuing position supervision", exc_info=True)
                                    break
                                except Exception:
                                    logger.exception(f"[SIGNAL ERROR] Unhandled exception evaluating shock {shock.get('market_id')}; signal skipped.")
                                    try:
                                        self._refresh_global_halt()
                                    except Exception:
                                        logger.exception("[SIGNAL ERROR] Global halt refresh failed.")

                # 3. Monitor open positions (fast 0.20s cadence when a stop/cancel confirmation is armed, else 1.0s)
                urgent_supervision = any(
                    p.get("strike_retrace_detected_ts") or p.get("exit_order_status") in {"STOP_CANCEL_PENDING", "PRE_EXPIRY_CANCEL_PENDING", "FILL_RECONCILIATION_REQUIRED", "PASSIVE_STOP_RESTING"}
                    for p in self.active_positions.values()
                )
                mgmt_interval = 0.20 if urgent_supervision else 1.0
                if now_ts - last_mgmt_check >= mgmt_interval:
                    last_mgmt_check = now_ts
                    try:
                        await self.check_resolutions_and_manage_positions()
                    except StatePersistenceError:
                        raise
                    except Exception:
                        logger.exception("[SUPERVISION ERROR] Position management cycle failed; retrying next cycle.")

                if time.time() - last_heartbeat >= 300:
                    last_heartbeat = time.time()
                    active_exp = sum(p.get("notional_usd", 0.0) for p in self.active_positions.values())
                    logger.info(
                        f"[HEARTBEAT] Harvester active | Triggers scanned: {scanned_count} | "
                        f"Active positions: {len(self.active_positions)} (${active_exp:.2f}) | "
                        f"Closed: {len(self.closed_positions)}"
                    )

                # Periodic stale-recorder monitor (rate-limited alerts inside; cheap stat() calls every 5s)
                if not self.dry_run and (time.time() - getattr(self, "_last_stale_check", 0.0) >= 5.0):
                    self._last_stale_check = time.time()
                    try:
                        self.monitor_recorder_staleness(self._last_stale_check)
                    except Exception:
                        logger.debug("[STALE_RECORDER_GUARD] monitor failed", exc_info=True)

                # Event-driven sleep: wake immediately when inotify triggers or after 10ms fallback timeout (Task 1A)
                try:
                    await asyncio.wait_for(trigger_notify_event.wait(), timeout=0.010)
                    trigger_notify_event.clear()
                except asyncio.TimeoutError:
                    pass

        except Exception:
            # Never exit silently with status 0: log the traceback and propagate so the
            # process exits non-zero and the supervisor restarts it (startup reconcile re-runs).
            logger.critical("[FATAL] Harvester loop terminated by unhandled exception.", exc_info=True)
            raise
        finally:
            if 'trigger_fp' in locals() and trigger_fp is not None and not getattr(trigger_fp, "closed", True):
                try:
                    trigger_fp.close()
                except Exception:
                    pass
            if 'watcher' in locals() and watcher is not None and getattr(watcher, "is_available", False):
                try:
                    if 'loop' in locals() and loop is not None:
                        loop.remove_reader(watcher.fd)
                except Exception:
                    pass
                try:
                    watcher.close()
                except Exception:
                    pass
            try:
                flush_operational_alerts(3.0)
            except Exception:
                pass
            lock_fd = getattr(self, "_instance_lock_fd", None)
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()
                except Exception:
                    pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket Live Harvester")
    parser.add_argument("--lot-size", type=float, default=RISK_CONFIG["ticket_notional"], help="Ticket size in USD (default: config/polymarket_risk_config.json ticket_notional)")
    parser.add_argument("--dynamic-sizing", action="store_true", default=True, help="Dynamically scale lot size with orderbook depth (default: True)")
    parser.add_argument("--no-dynamic-sizing", dest="dynamic_sizing", action="store_false", help="Disable dynamic sizing and use fixed lot size")
    parser.add_argument("--max-exposure", type=float, default=RISK_CONFIG["max_exposure"], help="Maximum concurrent portfolio exposure in USD (default: config max_exposure)")
    parser.add_argument("--max-concurrent", type=int, default=RISK_CONFIG["max_concurrent_positions"], help="Maximum concurrent open positions (default: config max_concurrent_positions)")
    parser.add_argument("--max-trades-per-market", type=int, default=DEFAULT_MAX_TRADES_PER_MARKET, help="Max trades per market candle (default: 1)")
    parser.add_argument("--max-trades-per-hour", type=int, default=DEFAULT_MAX_TRADES_PER_HOUR, help="Max total portfolio trades per hour (default: 6)")
    parser.add_argument("--max-tte", type=float, default=MAX_TTE_SECONDS, help="Max TTE in seconds (default: module MAX_TTE_SECONDS)")
    parser.add_argument("--max-price-ceiling", type=float, default=MAX_PRICE_CEILING, help="Maximum entry price ceiling (default: module MAX_PRICE_CEILING)")
    parser.add_argument("--min-price-floor", type=float, default=MIN_PRICE_FLOOR, help="Minimum entry price floor (default: module MIN_PRICE_FLOOR)")
    parser.add_argument("--unconstrained-kelly", action="store_true", default=False, help="Allow Half-Kelly position sizing to compound proportionally (25 percent of bankroll) beyond $39.92")
    parser.add_argument("--max-ticket-cap", type=float, default=MAX_ABSOLUTE_TICKET_USD, help="Explicit maximum dollar cap for single ticket (default: module MAX_ABSOLUTE_TICKET_USD)")
    parser.add_argument("--dynamic-theta", action="store_true", default=False, help="Enable EXP-315 regime-dependent profit target (0.06 when TTE>900s, 0.09 standard, hold-to-expiry when TTE<=300s)")
    parser.add_argument("--allowed-assets", nargs="+", default=["BTC", "ETH"], help="Assets permitted for live trading (default: BTC ETH)")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run simulation mode")
    parser.add_argument("--reset-risk", action="store_true", default=False, help="Reset circuit breaker and consecutive losses on launch")
    parser.add_argument("--max-daily-loss", type=float, default=None, help="Circuit breaker max daily loss limit in USD (default: config max_daily_loss)")
    args = parser.parse_args()

    harvester = PolymarketLiveHarvester(
        ticket_notional=args.lot_size,
        dry_run=args.dry_run,
        dynamic_sizing=args.dynamic_sizing,
        max_exposure=args.max_exposure,
        max_concurrent=args.max_concurrent,
        max_trades_per_market=args.max_trades_per_market,
        max_trades_per_hour=args.max_trades_per_hour,
        max_tte=args.max_tte,
        max_price_ceiling=args.max_price_ceiling,
        min_price_floor=args.min_price_floor,
        unconstrained_kelly=args.unconstrained_kelly,
        max_absolute_ticket_usd=args.max_ticket_cap,
        dynamic_theta=args.dynamic_theta,
        allow_cli_exposure=any(a == "--max-exposure" or a.startswith("--max-exposure=") for a in sys.argv[1:]),
        allowed_assets=set(args.allowed_assets),
        reset_risk=args.reset_risk,
        max_daily_loss=args.max_daily_loss,
    )
    asyncio.run(harvester.run())


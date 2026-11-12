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
from collections import defaultdict, deque
from contextvars import ContextVar
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore
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
    is_market_closed_or_disabled_error,
    load_risk_config,
    quantize_fok_buy_box_legs,
    RISK_CONFIG,
    _get_hot_io_pool,
    _HOT_DISPATCH_ACTIVE,
)

_PRE_HOT_CTX: ContextVar[Optional[Tuple[List[str], Any, Any]]] = ContextVar("polymarket_pre_hot_ctx", default=None)
try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    _NY_TZ = _ZoneInfo("America/New_York")
except Exception:
    try:
        from src.polymarket_research.riskless_protocol_v2_expansion import get_us_eastern_tz as _get_ny_tz
        _NY_TZ = _get_ny_tz()
    except Exception:
        _NY_TZ = None

try:
    from src.polymarket_research.latency_trace import (
        LatencyTrace as _LatencyTrace,
        CURRENT_TRACE as _CURRENT_TRACE,
        emit_shock_attempt as _emit_shock_attempt,
        emit_shock_attempt_from_trace as _emit_shock_attempt_trace,
    )
except Exception:  # pragma: no cover - tracing is optional and must never block trading
    _LatencyTrace = None  # type: ignore
    _CURRENT_TRACE = None  # type: ignore
    _emit_shock_attempt = None  # type: ignore
    _emit_shock_attempt_trace = None  # type: ignore

try:
    from src.polymarket_research.economic_attribution_ledger import (
        GLOBAL_DECAY_TRACKER as _STAGE_B_DECAY_TRACKER,
        GLOBAL_MARKOUT_SAMPLER as _STAGE_B_MARKOUT_SAMPLER,
        emit_funnel_event as _stage_b_emit_funnel,
        register_candidate_funnel_and_decay_watch as _stage_b_reg_decay_watch,
    )
except Exception:  # pragma: no cover
    _STAGE_B_DECAY_TRACKER = None  # type: ignore
    _STAGE_B_MARKOUT_SAMPLER = None  # type: ignore
    _stage_b_emit_funnel = None  # type: ignore
    _stage_b_reg_decay_watch = None  # type: ignore

try:
    from src.polymarket_research.polymarket_ws_streams import (
        PolymarketClobMarketWsTracker as _PolymarketClobMarketWsTracker,
        PolymarketShardedClobMarketWsTracker as _PolymarketShardedClobMarketWsTracker,
        PolymarketPerpsLeadLagStream as _PolymarketPerpsLeadLagStream,
    )
except Exception:
    try:
        from polymarket_ws_streams import (  # type: ignore
            PolymarketClobMarketWsTracker as _PolymarketClobMarketWsTracker,
            PolymarketShardedClobMarketWsTracker as _PolymarketShardedClobMarketWsTracker,
            PolymarketPerpsLeadLagStream as _PolymarketPerpsLeadLagStream,
        )
    except Exception:
        _PolymarketClobMarketWsTracker = None  # type: ignore
        _PolymarketShardedClobMarketWsTracker = None  # type: ignore
        _PolymarketPerpsLeadLagStream = None  # type: ignore

# Max age of the recorder's WebSocket L2 snapshot that live entries may trade on without a fresh REST /book.
# Default preserves the previous hard-coded 2500 ms; lower it only after the latency traces show
# edge decay vs book age (see scripts/latency_trace_report.py).
LIVE_WS_BOOK_MAX_AGE_MS = float(os.environ.get("PM_LIVE_WS_BOOK_MAX_AGE_MS", "2500"))

try:
    from src.polymarket_research.deribit_svi_surface import GLOBAL_SVI_ENGINE
except Exception:
    GLOBAL_SVI_ENGINE = None

try:
    from src.polymarket_research.holistic_strategy_governance import (
        GLOBAL_GOVERNANCE_MANAGER,
        compute_stop_risk_fractional_kelly_ticket,
        evaluate_ev_terminal_twap_t5_salvage,
        get_unleashed_v5_tier_profile,
        passes_capital_velocity_hurdle,
    )
except Exception:
    from holistic_strategy_governance import (  # type: ignore
        GLOBAL_GOVERNANCE_MANAGER,
        compute_stop_risk_fractional_kelly_ticket,
        evaluate_ev_terminal_twap_t5_salvage,
        get_unleashed_v5_tier_profile,
        passes_capital_velocity_hurdle,
    )

try:
    from src.polymarket_research.net_alpha_opportunity_engine import (
        compute_capital_velocity_ev,
        compute_smart_maker_bid,
        evaluate_cross_oracle_basis_box_ev,
        evaluate_d1_15m_to_5m_corridor_conversion,
        evaluate_guarded_complement_merge,
        evaluate_optimal_stopping_exit,
        inspect_microstructure_feature_completeness,
        publish_global_positions_shm,
        rank_microbatch_shock_tournament,
        walk_dual_leg_overround_bids,
    )
except Exception:
    compute_capital_velocity_ev = None
    compute_smart_maker_bid = None
    evaluate_cross_oracle_basis_box_ev = None
    evaluate_d1_15m_to_5m_corridor_conversion = None
    evaluate_guarded_complement_merge = None
    evaluate_optimal_stopping_exit = None
    inspect_microstructure_feature_completeness = None
    publish_global_positions_shm = None
    rank_microbatch_shock_tournament = None
    walk_dual_leg_overround_bids = None

try:
    from src.polymarket_research.exact_twap_lock_engine import should_suppress_final60s_twap_salvage
except Exception:
    should_suppress_final60s_twap_salvage = None

try:
    from src.polymarket_research.same_oracle_dominance_box import walk_equal_shares_dominance_box
except Exception:
    walk_equal_shares_dominance_box = None

logger = logging.getLogger("LiveHarvester")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
_FILE_LOGGER_ATTACHED = False
_LOG_QUEUE_LISTENER: Optional[Any] = None


def _ensure_file_logging() -> None:
    """Attaches non-blocking QueueHandler -> QueueListener(FileHandler + StreamHandler) so hot-path logging never blocks uvloop on disk I/O."""
    global _FILE_LOGGER_ATTACHED, _LOG_QUEUE_LISTENER
    if _FILE_LOGGER_ATTACHED:
        return
    try:
        import atexit
        import logging.handlers
        import queue as _qmod

        log_path = DATA_DIR / "live_harvester.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s"))
        root_log = logging.getLogger()
        if os.environ.get("PM_ASYNC_FILE_LOGGING", "1") == "1":
            downstream = [fh]
            for h in list(root_log.handlers):
                if type(h) is logging.StreamHandler:
                    root_log.removeHandler(h)
                    downstream.append(h)
            q_obj = _qmod.SimpleQueue()
            qh = logging.handlers.QueueHandler(q_obj)
            ql = logging.handlers.QueueListener(q_obj, *downstream, respect_handler_level=True)
            ql.start()
            _LOG_QUEUE_LISTENER = ql
            atexit.register(ql.stop)
            root_log.addHandler(qh)
        else:
            root_log.addHandler(fh)
        _FILE_LOGGER_ATTACHED = True
    except Exception as exc:
        logger.debug(f"Could not attach file logger: {exc}")

# ------------------------------------
# Operational alerting (zero-dependency): JSONL audit trail + optional Telegram / webhook push.
# ------------------------------------
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
    if "POLYMARKET_ALERTS_FILE" in os.environ:
        override = os.environ["POLYMARKET_ALERTS_FILE"].strip()
        return Path(override) if override else None
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
    suppress_http = (
        os.environ.get("POLYMARKET_ALERTS_SUPPRESS_HTTP") == "1"
        and os.environ.get("POLYMARKET_ALERTS_FORCE_HTTP") != "1"
    )
    if not suppress_http:
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
SHADOW_PHASE3_4_FILE = DATA_DIR / "shadow_phase3_4_tracker.jsonl"
D1_LIVE_CANDIDATES_FILE = DATA_DIR / "d1_live_box_candidates.jsonl"

# v3.3 Zero-REST shared-memory fast tick bus written by polymarket_terminal_recorder.py
FAST_TICK_DIR = Path(os.getenv("PM_FAST_TICK_DIR", "/dev/shm"))
FAST_TICK_SHM_DIR = FAST_TICK_DIR
FAST_TICK_MAX_AGE_SEC = 0.50
VENUE_DIVERGENCE_VETO_BPS = 15.0
RECORDER_HEARTBEAT_FILES: List[Path] = [FAST_TICK_DIR / f"pm_fast_tick_{a}.json" for a in ("BTC", "ETH", "SOL")]

def read_fast_tick(asset: str, max_age_sec: float = FAST_TICK_MAX_AGE_SEC, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Reads /dev/shm/pm_fast_tick_{ASSET}.json; returns None if missing, unparsable, stale, or future-skewed."""
    if "PM_FAST_TICK_DIR" in os.environ:
        env_dir = os.environ["PM_FAST_TICK_DIR"].strip()
        if not env_dir:
            return None
        tick_dir = Path(env_dir)
    else:
        tick_dir = FAST_TICK_SHM_DIR
    try:
        with open(tick_dir / f"pm_fast_tick_{str(asset).upper()}.json", "rb") as f:
            snap = _json_loads(f.read())
        ts = float(snap.get("ts") or snap.get("timestamp_unix") or 0.0)
        age = (now if now is not None else time.time()) - ts
        if ts <= 0.0 or age > max_age_sec or age < -2.0:
            return None
        return snap
    except Exception:
        return None

def check_recorder_freshness(max_stale_sec: float = 15.0, now_ts: Optional[float] = None) -> Tuple[bool, str]:
    """Module-level heartbeat freshness guard checking both file mtime and internal JSON timestamp_unix/ts."""
    ref_now = float(now_ts if now_ts is not None else time.time())
    if not RECORDER_HEARTBEAT_FILES:
        return False, "no_heartbeat_files"
    reasons: List[str] = []
    for p in RECORDER_HEARTBEAT_FILES:
        try:
            m_age = ref_now - p.stat().st_mtime
            if m_age < -2.0 or m_age > max_stale_sec:
                reasons.append(f"mtime_stale:{p.name}:{m_age:.1f}s")
                continue
            snap = _json_loads(p.read_bytes())
            if isinstance(snap, dict):
                inner_ts = float(snap.get("ts") or snap.get("timestamp_unix") or 0.0)
                if inner_ts > 0.0:
                    in_age = ref_now - inner_ts
                    if in_age < -2.0 or in_age > max_stale_sec:
                        reasons.append(f"internal_stale:{p.name}:{in_age:.1f}s>{max_stale_sec:.1f}s")
                        continue
                spot_ts = float(snap.get("spot_ts") or 0.0)
                if spot_ts > 0.0:
                    sp_age = ref_now - spot_ts
                    if sp_age < -2.0 or sp_age > max_stale_sec:
                        reasons.append(f"spot_stale:{p.name}:{sp_age:.1f}s>{max_stale_sec:.1f}s")
                        continue
            return True, f"ok:{p.name}"
        except Exception as exc:
            reasons.append(f"missing:{p.name}:{exc}")
    return False, ";".join(reasons) or "stale"

def fast_tick_book_for_token(snap: Optional[Dict[str, Any]], token_id: str) -> Optional[Dict[str, Any]]:
    """Returns a REST-shaped top-of-book {'bids': [...], 'asks': [...]} for token_id from a fast tick, or None."""
    if not snap or not token_id:
        return None
    candidates = [snap.get("UP"), snap.get("DOWN")]
    for sub_k in ("m15", "m5", "h4"):
        sub_m = snap.get(sub_k)
        if isinstance(sub_m, dict):
            candidates += [sub_m.get("UP"), sub_m.get("DOWN")]
    mkts_map = snap.get("markets")
    if isinstance(mkts_map, dict):
        for m_obj in mkts_map.values():
            if isinstance(m_obj, dict):
                candidates += [m_obj.get("UP"), m_obj.get("DOWN")]
    for side in candidates:
        if not isinstance(side, dict) or str(side.get("token_id")) != str(token_id):
            continue
        bb = float(side.get("best_bid") or 0.0)
        ba = float(side.get("best_ask") or 0.0)
        # Only trust a two-sided, uncrossed book; anything else falls back to REST.
        if bb <= 0.0 or ba <= 0.0 or ba >= 1.0 or bb >= ba:
            return None
        r_bids = side.get("raw_top_bids")
        r_asks = side.get("raw_top_asks")
        bids_out = (
            [{"price": str(p), "size": str(s)} for p, s in r_bids if float(p) > 0 and float(s) > 0]
            if isinstance(r_bids, list) and r_bids
            else []
        ) or [{"price": str(bb), "size": str(side.get("bid_size_l1") or 0.0)}]
        asks_out = (
            [{"price": str(p), "size": str(s)} for p, s in r_asks if float(p) > 0 and float(s) > 0]
            if isinstance(r_asks, list) and r_asks
            else []
        ) or [{"price": str(ba), "size": str(side.get("ask_size_l1") or 0.0)}]
        return {
            "bids": bids_out,
            "asks": asks_out,
            "source": "shm_fast_tick",
        }
    return None

def evaluate_coinbase_venue_veto(shock: Dict[str, Any], target_token: str) -> Tuple[bool, str]:
    """
    v3.8 Coinbase + Binance composite filter (fail-open, WFO F-10 OR-parity, v3.9.5 0-DOF vol-scaled).
    - Scales BTC-calibrated bps thresholds (12.0 / -4.0 / 15.0) by clamp(sigma_1h / 0.0050, 1.0, 2.0)
      so normal 2-second microstructure noise on higher-vol assets (ETH ~1.36x, SOL ~1.70x) is not falsely vetoed.
    """
    try:
        cb = float(shock.get("coinbase_spot") or 0.0)
        if cb <= 0.0:
            return False, "coinbase_unavailable_fail_open"
        asset_u = str(shock.get("asset") or "").upper()
        hz_l = str(shock.get("horizon") or shock.get("candle_interval") or "").lower()
        rec_s = float(shock.get("candle_sigma") or 0.0)
        if rec_s > 0.0:
            sig_1h = rec_s * (2.0 if ("15m" in hz_l or "900" in hz_l) else (math.sqrt(12.0) if hz_l in ("5m", "5min", "300", "300s") else 1.0))
        elif asset_u == "ETH":
            sig_1h = 0.0068
        elif asset_u in ("SOL", "XRP"):
            sig_1h = 0.0085
        else:
            sig_1h = 0.0050
        vol_mult = min(2.0, max(1.0, sig_1h / 0.0050))
        has_centered = shock.get("venue_divergence_centered_bps") is not None
        if has_centered:
            eff_div = float(shock["venue_divergence_centered_bps"])
        else:
            eff_div = float(shock.get("venue_divergence_bps") or 0.0)
        cb_move = float(shock.get("coinbase_move_bps_2s") or 0.0)
        sign = 1.0 if target_token == "UP" else -1.0
        dir_div = sign * eff_div
        dir_cb_move = sign * cb_move
        cb_against = dir_cb_move < (-0.50 * vol_mult)
        if (has_centered and dir_div > (12.0 * vol_mult)) or dir_cb_move < (-4.0 * vol_mult) or (dir_div > (VENUE_DIVERGENCE_VETO_BPS * vol_mult) and cb_against):
            return True, f"directional venue divergence {dir_div:+.1f}bps / Coinbase opposing dump ({cb_move:+.2f}bps/2s, mult={vol_mult:.2f}x)"
        return False, f"ok (dir_div={dir_div:+.1f}bps, cb_move={cb_move:+.2f}bps)"
    except Exception as e:
        return False, f"veto_eval_error_fail_open: {e}"

# v3.4 Queue-priority jumping + fast maker-TP confirmation
QUEUE_JUMP_MIN_WALL_SHARES = 250.0
QUEUE_JUMP_WALL_MULT = 6.0
QUEUE_JUMP_MIN_TP_FLOOR = 0.95
QUEUE_JUMP_MIN_TARGET = 0.97
FAST_CONFIRM_POLL_SEC = 0.20
FAST_CONFIRM_WINDOW_SEC = 10.0
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

# ------------------------------------
# Round 9: Canonical lifecycle-state policy (single source of truth)
# ------------------------------------
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
    # Post-only TP rejected because best bid sat at the max tick; re-post once `next_exit_post_ts` elapses.
    "CROSSED_AT_MAX_TICK_WAIT",
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
REDEMPTION_POLL_INTERVAL_S = 15.0

def position_requires_global_halt(pos: Dict[str, Any]) -> bool:
    """True if this position's exchange outcome requires a GLOBAL halt across ALL markets."""
    return (
        pos.get("exit_order_status") in PIPELINE_GLOBAL_HALT_STATUSES
        or pos.get("status") in PIPELINE_GLOBAL_HALT_STATUSES
    )

def position_requires_lifecycle_resolution(pos: Dict[str, Any]) -> bool:
    """True if this position's outcome (global OR market-scoped) requires _resolve_lifecycle."""
    return (
        pos.get("exit_order_status") in GLOBAL_HALT_STATUSES
        or pos.get("status") in GLOBAL_HALT_STATUSES
    )

def position_may_post_new_maker_exit(pos: Dict[str, Any]) -> bool:
    """
    Allowlist gate for ANY new maker-exit submission. Denies by default: unknown outcomes,
    unwinds in flight, partial-unwind residuals, terminal holds and receivables.
    """
    if position_requires_lifecycle_resolution(pos):
        return False
    if pos.get("is_liquidating") or pos.get("unwind_order_id"):
        return False
    if pos.get("status") in SETTLEMENT_RECEIVABLE_STATUSES or pos.get("status") in {"ENTRY_OUTCOME_UNKNOWN", "FAILED"}:
        return False
    if pos.get("hold_to_maturity_lock") or pos.get("terminal_policy") == "DETERMINISTIC_TERMINAL_HOLD_FINAL" or pos.get("exit_order_status") == "SUB_MINIMUM_LOT_SUPERVISED_HOLD":
        return False
    return str(pos.get("exit_order_status") or "") in MAKER_EXIT_POSTABLE_STATUSES

def position_is_settlement_receivable(pos: Dict[str, Any]) -> bool:
    return pos.get("status") in SETTLEMENT_RECEIVABLE_STATUSES

# ====================================
# v3.3 DEEP RESEARCH INSTITUTIONAL MICROSTRUCTURE & ALPHA UPGRADE (PILLARS 1, 2, 4)
# ====================================

def compute_composite_edge_score(shock: Dict[str, Any], *, v5_wfo_parity: bool = False) -> Dict[str, Any]:
    """
    Pillar 1: Composite Edge & Stale-Quote Scoring Function.
    Evaluates orderbook microstructure, flow momentum, and queue dynamics to assign
    a conviction score (0-100) and Kelly sizing multiplier (1.15x for Tier A+, 1.00x for Tier B).
    When `v5_wfo_parity=True`, enforces Purged-WFO + Live-OOT Row-15 parity (`OFI >= 0.20`,
    keeps directional basis & thin-cushion L1 ask-wall guards, strips uncalibrated `e_score < 50`
    and `<25ms/<50ms` MM-reload vetoes).
    """
    shock_dir = str(shock.get("shock_direction") or "UP").upper()
    target_token = "UP" if shock_dir in ("BUY", "UP") else "DOWN"
    opp_token = "DOWN" if target_token == "UP" else "UP"

    feats = shock.get("pre_shock_features_t0", {}) or {}
    tf = feats.get(target_token, {}) or {}
    opp_tf = feats.get(opp_token, {}) or {}

    if inspect_microstructure_feature_completeness is not None:
        feat_hygiene = inspect_microstructure_feature_completeness(
            shock, target_token, str(tf.get("token_id") or "")
        )
        _missing_f = list(feat_hygiene.get("missing_fields") or [])
        if feat_hygiene.get("hard_veto_live") and (not v5_wfo_parity or any(f != "age_ask_ms" for f in _missing_f)):
            return {
                "e_score": 0.0,
                "tier": "TIER_C_REJECT",
                "kelly_multiplier": 0.0,
                "fak_price_buffer": 0.010,
                "veto": True,
                "veto_reason": f"Missing live microstructure telemetry: {_missing_f}",
                "feature_hygiene": feat_hygiene,
            }

    # 1. S_stale: Stale-quote score based on age_ask_ms, age_bid_ms, opposing age_bid_ms
    # Default age_ask_ms = 400.0 if missing in synthetic test fixtures so unit tests pass seamlessly;
    # on a live empty-ask book with a valid observed age_bid_ms, cap fallback at <=240ms to avoid synthetic TIER_A+ inflation.
    if tf.get("age_ask_ms") is not None:
        age_ask_ms = float(tf.get("age_ask_ms"))
    elif float(tf.get("best_ask") or 0.0) >= 0.995 and tf.get("age_bid_ms") is not None:
        age_ask_ms = min(240.0, float(tf.get("age_bid_ms")))
    else:
        age_ask_ms = 400.0
    if shock.get("shock_source") in ("BOUNDARY_LOCK", "EXP316_TRACK_A_CONVERGENCE") or shock.get("sleeve") == "SLEEVE_3_STRIKE_CONVERGENCE":
        age_ask_ms = max(age_ask_ms, 450.0)
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

    # Hard Vetoes (Unified across dry-run, test, and live production):
    veto = False
    veto_reason = None
    basis_veto_floor = -6.0 if str(shock.get("shock_source", "")).upper() == "SPOT" else -2.0
    min_ofi_hurdle = 0.20 if v5_wfo_parity else 0.60
    min_e_score_hurdle = 0.0 if v5_wfo_parity else 50.0
    candle_dist_abs = abs(float(shock.get("candle_distance_pct", 0.0) or 0.0))
    _raw_csig = float(shock.get("candle_sigma") or 0.0)
    _raw_tte = float(shock.get("seconds_to_expiry") or 3600.0)
    _hz_hint = str(shock.get("horizon") or "").lower()
    _sig_mult = math.sqrt(12.0) if _hz_hint == "5m" else (2.0 if _hz_hint == "15m" else 1.0)
    _sig_1h_est = (_raw_csig * _sig_mult) if _raw_csig > 0.0 else 0.0050
    _z_cush_est = (candle_dist_abs / 100.0) / max(0.00025, _sig_1h_est * math.sqrt(max(_raw_tte, 30.0) / 3600.0))
    if ofi_abs < min_ofi_hurdle:
        veto = True
        veto_reason = f"OFI {ofi_abs:.2f} < {min_ofi_hurdle:.2f} hurdle"
    elif dir_delta_basis < basis_veto_floor:
        veto = True
        veto_reason = f"Directional delta_basis {dir_delta_basis:.2f} bps < {basis_veto_floor:.1f} bps"
    elif not v5_wfo_parity and age_ask_ms < 25.0 and obi_l1 < -0.25:
        veto = True
        veto_reason = f"Ultra-fresh MM ask reload (age={age_ask_ms:.1f}ms < 25ms, obi_l1={obi_l1:.2f} < -0.25)"
    elif not v5_wfo_parity and age_ask_ms < 50.0 and obi_l1 < -0.50:
        veto = True
        veto_reason = f"Ask already repriced by MM (age={age_ask_ms:.1f}ms < 50ms, obi_l1={obi_l1:.2f} < -0.50)"
    elif obi_l1 < -0.55 and 0.0 < candle_dist_abs < 0.09 and not (_raw_csig > 0.0 and _z_cush_est >= 0.55 and age_ask_ms >= 150.0):
        veto = True
        veto_reason = f"Heavy L1 ask wall against thin cushion (obi_l1={obi_l1:.2f} < -0.55, dist={candle_dist_abs:.4f}% < 0.09%)"

    if veto:
        tier = "TIER_C_REJECT"
        kelly_multiplier = 0.0
        fak_price_buffer = 0.010
    elif round(e_score, 1) >= 70.0 and age_ask_ms >= 250.0:
        tier = "TIER_A_PLUS_STALE_SNIPE"
        kelly_multiplier = 1.15
        fak_price_buffer = 0.020
    elif round(e_score, 1) >= min_e_score_hurdle:
        tier = "TIER_B_STANDARD"
        kelly_multiplier = 1.00
        fak_price_buffer = 0.015
    else:
        tier = "TIER_C_REJECT"
        kelly_multiplier = 0.0
        fak_price_buffer = 0.010
        veto = True
        veto_reason = f"e_score {e_score:.1f} < {min_e_score_hurdle:.1f} threshold"

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
    candle_sigma: Optional[float] = None,
    is_5m: bool = False,
) -> Dict[str, float]:
    """
    Pillar 2: Salvage-Adjusted Continuous Maximum-Ask Pricing Model (C^0-smooth across all dist_pct).
    """
    asset_clean = str(asset or "BTC").upper()
    sigma_1h = 0.0050 if asset_clean == "BTC" else (0.0095 if asset_clean == "SOL" else 0.0068)
    _sig_floor = 0.0028
    if candle_sigma is not None and float(candle_sigma) > 0.0:
        _cmult = math.sqrt(12.0) if is_5m else (2.0 if is_subhourly_15m else 1.0)
        sigma_1h = max(_sig_floor, float(candle_sigma) * _cmult)
    if GLOBAL_SVI_ENGINE is not None and os.environ.get("PM_SVI_DISABLE_BG_REFRESH") != "1":
        try:
            _svi_sig = float(GLOBAL_SVI_ENGINE.get_hourly_sigma(asset_clean, fallback=sigma_1h) or 0.0)
            if _svi_sig > 0.0:
                sigma_1h = max(_sig_floor, min(sigma_1h, _svi_sig * 0.80))
        except Exception:
            pass
    candle_horizon_s = 300.0 if is_5m else (900.0 if is_subhourly_15m else 3600.0)
    sigma_candle = sigma_1h * math.sqrt(candle_horizon_s / 3600.0)
    tau_clamped = max(float(tte_sec), 15.0)
    sigma_rem = sigma_candle * math.sqrt(tau_clamped / candle_horizon_s)
    cushion_frac = abs(float(dist_pct)) / 100.0
    base_vol = 1_500_000.0 if asset_clean == "BTC" else 500_000.0
    vol_ratio = min(3.0, max(0.2, float(shock_vol_usd) / base_vol))
    ofi_abs = min(1.0, max(0.0, abs(float(shock_ofi))))
    stale_mult = 1.0 + 0.15 * max(-0.5, min(1.0, (float(age_ask_ms) - 200.0) / 400.0))
    drift_bps = ((6.5 * ofi_abs * (vol_ratio ** 0.30)) + (0.45 * float(delta_basis_bps))) * stale_mult
    drift_frac = (drift_bps / 10000.0) * min(1.0, math.sqrt(300.0 / tau_clamped))
    if is_subhourly_15m or is_5m:
        w_cush = max(0.0, min(1.0, (cushion_frac - 0.00065) / 0.00050))
        drift_frac = min(drift_frac, (0.25 + 0.75 * w_cush) * cushion_frac)
        expected_salvage_net = float(expected_salvage_net) * (0.45 + 0.55 * w_cush)
    z_eff = (cushion_frac + drift_frac) / max(sigma_rem, 1e-6)
    p_true = 0.5 * (1.0 + math.erf(z_eff / math.sqrt(2.0)))
    p_exit = 0.985
    expected_payoff = (p_true * p_exit) + ((1.0 - p_true) * (1.0 - q_tail) * expected_salvage_net)
    r = float(fee_rate)
    eta = float(target_return)
    discriminant = ((1.0 + r) ** 2) - (4.0 * r * expected_payoff / (1.0 + eta))
    if discriminant <= 0.0 or p_true <= 0.53:
        p_max = 0.0
    else:
        p_root = ((1.0 + r) - math.sqrt(discriminant)) / (2.0 * r)
        regime_cap = 0.78 if tau_clamped > 900.0 else 0.85
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
    Pillar 4: Monotonic Correlated Truncated-Payoff Kelly Sizing (no <10% step inversion).
    """
    if bankroll_usd is not None and live_equity <= 0.0:
        live_equity = bankroll_usd
    if entry_price is not None and entry_px <= 0.0:
        entry_px = entry_price
    if p_true is not None and p_win <= 0.0:
        p_win = p_true

    if live_equity <= 0.0 or entry_px <= 0.0 or p_win <= 0.0:
        return 0.0
    f_k = compute_modified_salvage_kelly_fraction(p_win, entry_px)
    if f_k <= 0.0:
        return 0.0
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


def apply_convex_payoff_sizing_cap(
    raw_ticket_usd: float,
    *,
    live_equity: float,
    entry_px: float,
    sleeve: str = "",
    knee: float = 0.79,
    gamma: float = 0.75,
    min_taper: float = 0.58,
    max_salvage_risk_pct: float = 0.125,
    salvage_floor_px: float = 0.24,
    min_lot_usd: float = 8.0,
) -> float:
    """
    EXP-PM-407 Purged-WFO Convex Payoff-Normalized Sizing (`convex_k79_g075_stop125`):
      - Preserves full Kelly firepower in the sweet-spot `$0.55–$0.79` band (`+24%..+75%` ROI).
      - Above `knee` (`$0.79`), tapers ticket size smoothly by remaining upside `((0.99 - px)/(0.99 - knee))**0.75`
        AND caps worst-case salvage loss (`salvage_floor_px = $0.24`) at `max_salvage_risk_pct` (`12.5%`) of equity
        so a single `$0.84–$0.86` stop can never wipe out half a dozen wins.
      - Purged WFO (`Train / Val / Sealed Holdout` on BTC+ETH): lifts Holdout net PnL `+$57.93 -> +$71.19` (`+22.9%`),
        PF `1.197 -> 1.375`, Sharpe `0.953 -> 1.182`, and cuts Holdout MaxDD `54.4% -> 39.9%`.
    """
    if raw_ticket_usd <= 0.0 or live_equity <= 0.0 or entry_px <= 0.0:
        return max(0.0, float(raw_ticket_usd))
    slv_u = str(sleeve or "").upper()
    if "BOX" in slv_u or slv_u == "SLEEVE_4_BOUNDARY_SNIPE":
        return round(float(raw_ticket_usd), 2)
    px = min(0.97, max(0.05, float(entry_px)))
    taper = 1.0
    if px > knee:
        rem_up = max(0.04, 0.99 - px)
        ref_up = max(0.04, 0.99 - knee)
        taper = max(float(min_taper), (rem_up / ref_up) ** float(gamma))
    loss_frac_at_salvage = max(0.25, (px - float(salvage_floor_px)) / px)
    stop_cap_tkt = (float(max_salvage_risk_pct) * float(live_equity)) / loss_frac_at_salvage
    capped = min(float(raw_ticket_usd) * taper, stop_cap_tkt)
    return round(min(float(raw_ticket_usd), max(float(min_lot_usd), capped)), 2)

def get_equity_tier_limits(
    total_equity: float,
    high_water_mark_equity: Optional[float] = None,
    previous_tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Auto-Stepping Bankroll Sizing & Exposure by Live Equity Tier (Safeguard #1 + v3.9 R04 Smooth Ramp):
    - Seed Survival (< $88.00, with +$3.00 upward hysteresis when previous_tier == 'SEED_SURVIVAL'):
        dynamic_bankroll_pct = 0.1568 ($12 ticket cap), max_concurrent_positions = 1, floor = $48.00
    - Seed Ramp ($91.00 <= equity < $108.00 when graduating up from SEED_SURVIVAL / SEED_RAMP):
        Smooth transition band eliminating the +61% single-ticket jump and 2x concurrency cliff at $88.01!
    - Recovery Tier (total_equity < 140.0):
        dynamic_bankroll_pct = 0.22, max_concurrent_positions = 2, max_exposure = round(max(45.0, total_equity * 0.55), 2)
    - Growth Tier (140.0 <= total_equity < 300.0):
        dynamic_bankroll_pct = 0.26, max_concurrent_positions = 3, max_exposure = round(min(350.0, total_equity * 0.75), 2)
    - Scale Tier (total_equity >= 300.0):
        dynamic_bankroll_pct = 0.28, max_concurrent_positions = 3, max_exposure = round(min(500.0, total_equity * 0.85), 2)
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

    seed_thresh = float(RISK_CONFIG.get("seed_survival_equity_threshold", 88.0))
    seed_exit_thresh = seed_thresh + 3.0 if previous_tier == "SEED_SURVIVAL" else seed_thresh
    if eq < seed_exit_thresh:
        tier_name = "SEED_SURVIVAL"
        dynamic_bankroll_pct = float(RISK_CONFIG.get("dynamic_risk_pct", 0.1568))
        max_concurrent_positions = int(RISK_CONFIG.get("seed_survival_max_concurrent", 1))
        _seed_cfg_exp = float(RISK_CONFIG.get("max_exposure", 24.0))
        max_exposure = round(max(min(_seed_cfg_exp, eq * 0.82) if eq > 0 else _seed_cfg_exp, eq * 0.30), 2)
        max_daily_loss = float(RISK_CONFIG.get("max_daily_loss", 22.0))
        min_equity_floor = float(RISK_CONFIG.get("seed_survival_floor_usd", 48.0))
        return {
            "tier": tier_name,
            "dynamic_bankroll_pct": dynamic_bankroll_pct,
            "max_concurrent_positions": max_concurrent_positions,
            "max_slots": max_concurrent_positions,
            "max_exposure": max_exposure,
            "max_daily_loss": max_daily_loss,
            "min_equity_floor": min_equity_floor,
        }

    if previous_tier in ("SEED_SURVIVAL", "SEED_RAMP") and eq < 108.0:
        _ramp_slots = 1 if eq < 98.0 else 2
        return {
            "tier": "SEED_RAMP",
            "dynamic_bankroll_pct": float(RISK_CONFIG.get("dynamic_risk_pct", 0.18)),
            "max_concurrent_positions": _ramp_slots,
            "max_slots": _ramp_slots,
            "max_exposure": round(max(30.0, eq * 0.38), 2),
            "max_daily_loss": round(max(22.0, eq * 0.26), 2),
            "min_equity_floor": round(max(54.0, min(65.0, hwm * 0.64)), 2),
        }

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
        "max_slots": max_concurrent_positions,
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
        self.last_checked_equity: Optional[float] = None
        self._harvester_ref: Any = None

    def _kill_file_active(self) -> bool:
        kf = self.kill_file
        if kf == (DATA_DIR / "KILL_SWITCH") and STATE_FILE.parent != DATA_DIR:
            kf = STATE_FILE.parent / "KILL_SWITCH"
        return kf.exists()

    def check_equity_drawdown(
        self, current_equity: Optional[float], high_water_mark: Optional[float] = None, *, allow_auto_clear: bool = False
    ) -> bool:
        """Circuit breaker: Halts trading if live bankroll equity breaches floor; sticky until verified +$3.00 hysteresis."""
        if current_equity is not None and math.isfinite(float(current_equity)):
            eq = float(current_equity)
            self.last_checked_equity = eq
            if eq < self.min_equity_floor_usd:
                self.halted = True
                self.halt_reason = (
                    f"Account equity ${eq:.2f} < ${self.min_equity_floor_usd:.2f} "
                    f"circuit-breaker threshold (2-loss variance buffer breached)."
                )
                logger.critical(f"[CIRCUIT_BREAKER_HALT] {self.halt_reason}")
            elif (
                self.halted
                and "Account equity" in self.halt_reason
                and allow_auto_clear
                and eq >= (self.min_equity_floor_usd + 3.00)
            ):
                if self._kill_file_active():
                    self.halt_reason = f"Emergency KILL_SWITCH file detected at {self.kill_file}"
                else:
                    self.halted = False
                    self.halt_reason = ""
                    logger.info(f"[CIRCUIT_BREAKER_CLEARED] Verified equity ${eq:.2f} >= +$3.00 above ${self.min_equity_floor_usd:.2f} floor.")
        return bool(self.halted)

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
                self._halt_alerted = False

    def record_trade_pnl(self, net_pnl: float, *, is_non_directional: bool = False):
        self._check_and_reset_daily()
        if is_non_directional and bool(
            GLOBAL_GOVERNANCE_MANAGER.snapshot.get("risk_controller", {}).get(
                "decouple_riskless_boxes_from_directional_halt", True
            )
        ):
            self.non_directional_realized_pnl = round(
                float(getattr(self, "non_directional_realized_pnl", 0.0) or 0.0) + float(net_pnl), 4
            )
            return
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
            if not self.halted:
                self.daily_realized_loss = max(0.0, self.daily_realized_loss - net_pnl)

    def is_halted(self) -> bool:
        """Evaluates whether trading is halted due to automated circuit breaker or manual kill switch."""
        self._check_and_reset_daily()
        kf_on = self._kill_file_active()
        if self.halted and "KILL_SWITCH file" in str(self.halt_reason or "") and not kf_on:
            self.halted = False
            self.halt_reason = ""
            self._halt_alerted = False
        halted_now = False
        if kf_on:
            self.halted = True
            if not self.halt_reason:
                self.halt_reason = f"Emergency KILL_SWITCH file detected at {self.kill_file}"
            halted_now = True
        elif self.halted:
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

    def is_riskless_box_halted(self) -> bool:
        """Dual-Budget gate: halts $1.00-payout boxes ONLY on manual KILL_SWITCH, infra/reconciliation halts, or riskless ruin floor breach."""
        if self._kill_file_active():
            return True
        if self.halted:
            rs = str(self.halt_reason or "").lower()
            if any(k in rs for k in ("persistence", "reconcil", "heartbeat", "kill_switch")):
                return True
            if "equity" in rs:
                rc_snap = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("risk_controller", {})
                if not bool(rc_snap.get("decouple_riskless_boxes_from_directional_halt", True)):
                    return True
                rl_floor = float(rc_snap.get("riskless_hard_ruin_floor_usd", 30.0) or 30.0)
                eq_candidates: List[float] = []
                if self.last_checked_equity is not None and math.isfinite(float(self.last_checked_equity)):
                    eq_candidates.append(float(self.last_checked_equity))
                href = getattr(self, "_harvester_ref", None)
                if href is not None:
                    try:
                        from src.polymarket_research.riskless_protocol_v2_expansion import (
                            compute_reconciled_concentration_nav_usd,
                        )
                        if (
                            getattr(href, "_last_known_collateral", None) is not None
                            or getattr(href, "active_positions", None)
                            or getattr(href, "pending_entry_intents", None)
                        ):
                            eq_candidates.append(compute_reconciled_concentration_nav_usd(href))
                    except Exception:
                        return True
                if not eq_candidates:
                    return True
                if min(eq_candidates) < rl_floor - 1e-6:
                    return True
        return False

def compute_kelly_ticket_size(
    p_model: float,
    p_market_ask: Optional[float] = None,
    bankroll: float = 0.0,
    fee_rate: Optional[float] = None,
    fee_exponent: Optional[float] = None,
    max_cap: Optional[float] = None,
    *,
    p_eff: Optional[float] = None,
) -> float:
    """Module-level Kelly sizing function supporting 35% elastic ticket sizing (returns 0.0 on non-positive edge/bankroll)."""
    ask_px = p_eff if p_market_ask is None else p_market_ask
    if ask_px is None or not all(math.isfinite(float(v)) for v in (p_model, ask_px, bankroll)):
        return 0.0
    if not (0.0 < float(p_model) < 1.0) or float(bankroll) <= 0.0 or float(ask_px) <= 0.0 or float(p_model) <= float(ask_px):
        return 0.0
    effective_cap = float(max_cap) if max_cap is not None else MAX_ABSOLUTE_TICKET_USD
    ticket_usd = min(max(25.0, float(bankroll) * MAX_NOTIONAL_CAP_PCT), effective_cap)
    return round(ticket_usd, 2)

from src.polymarket_research.riskless_protocol_v2_expansion import (
    _hv__attempt_live_phase3a_maker_rescue,
    _hv__finish_single_leg_lock,
    _hv__finish_negrisk_convert_arb,
    _hv__record_inline_d1_legged_out_close,
    _hv_maybe_execute_graduated_maker_anchor_box,
    _hv__evaluate_shock_and_execute_impl,
    _hv__maybe_recycle_disputed_htm_lock,
)


def _bind_hv_method(_raw_fn: Any, _pub_name: str) -> Any:
    import types as _types
    _fn = _types.FunctionType(_raw_fn.__code__, globals(), _pub_name, _raw_fn.__defaults__, _raw_fn.__closure__)
    _fn.__kwdefaults__ = getattr(_raw_fn, '__kwdefaults__', None)
    _fn.__annotations__ = dict(getattr(_raw_fn, '__annotations__', {}) or {})
    _fn.__doc__ = _raw_fn.__doc__
    _fn.__module__ = _raw_fn.__module__
    return _fn


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
        exit_policy: str = "two_tranche_95_98",
        allow_cli_exposure: bool = False,
        allow_cli_concurrency: bool = False,
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
        self.exit_policy = str(exit_policy or "two_tranche_95_98").strip().lower()
        # One-shot reset marker (systemd-friendly alternative to passing --reset-risk on every auto-restart):
        # scripts/reload_production_daemons.py drops this file; it is consumed exactly once at startup.
        reset_marker = STATE_FILE.parent / "RESET_RISK_ONCE"
        if not dry_run and reset_marker.exists():
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
        self.allow_cli_concurrency = bool(allow_cli_concurrency or os.getenv("PM_FORCE_MAX_CONCURRENT", "0") == "1")
        self._explicit_max_concurrent = int(self.max_concurrent_positions)
        
        # Initialize execution adapter (ledger_path=None honors POLYMARKET_LEDGER_PATH when set, else DATA_DIR/live_orders.jsonl)
        self.executor = PolymarketLiveExecutor(
            dry_run=dry_run,
            ledger_path=None,
        )
        daily_loss_budget = max_daily_loss if max_daily_loss is not None else float(RISK_CONFIG["max_daily_loss"])
        eff_eq_floor = CIRCUIT_BREAKER_EQUITY_FLOOR
        self.risk_controller = EmergencyRiskController(
            max_daily_loss_usd=daily_loss_budget,
            min_equity_floor_usd=eff_eq_floor,
        )
        self.risk_controller._harvester_ref = self
        
        self.seen_shock_ids: Set[str] = set()
        self._seen_shock_order: Dict[str, None] = {}
        self._seen_d1_box_keys: Set[str] = set()
        self._seen_d1_box_order: Dict[str, None] = {}
        self.traded_market_ids: Set[str] = set()
        self.trades_per_market: Dict[str, int] = defaultdict(int)
        self.trades_per_market_direction: Dict[Tuple[str, str], int] = defaultdict(int)
        self.hourly_candle_opens: Dict[str, Dict[int, float]] = defaultdict(dict)
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.closed_positions: List[Dict[str, Any]] = []

        # Release 2.4.2 Priority C: Stateful 1.5s persistence confirmation window for isolated low-bid quote dislocations
        if "POLYMARKET_LOW_BID_PERSISTENCE_SECONDS" in os.environ:
            self.low_bid_persistence_seconds = float(os.environ["POLYMARKET_LOW_BID_PERSISTENCE_SECONDS"])
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
        self._inflight_directional_entry_ids: Set[str] = set()
        self.risk_halt: bool = False
        self.reconciliation_required: bool = False
        self.global_halt_reasons: List[str] = []
        self._startup_reconciled: bool = False
        self._last_redemption_poll: float = 0.0
        self.recent_shock_window: List[Dict[str, Any]] = []
        self._last_known_collateral: Optional[float] = None
        self._current_equity_tier: Optional[str] = None
        self.current_equity_tier: Optional[str] = None
        self._capital_reservation_ledger: Any = None
        self.hierarchical_risk_budget_config: Any = None
        self._prewarm_hourly_opens()
        try:
            self.sync_capital_reservation_ledger()
        except Exception:
            pass

    def sync_capital_reservation_ledger(
        self,
        now_ts: Optional[float] = None,
        *,
        safety_buffer_usd: Optional[float] = None,
    ) -> Any:
        """Reconciles `live_bankroll`, open Maker intents, and non-frozen positions into `CapitalReservationLedger`."""
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            sync_harvester_capital_reservation_ledger,
        )

        return sync_harvester_capital_reservation_ledger(
            self,
            now_ts=now_ts,
            safety_buffer_usd=safety_buffer_usd,
        )

    def get_hierarchical_risk_budget_config(self) -> Any:
        """Returns or constructs `HierarchicalRiskBudgetConfig` for this harvester."""
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            build_harvester_hierarchical_risk_budget,
        )

        return build_harvester_hierarchical_risk_budget(self)

    def check_pre_trade_reservation_and_budget(
        self,
        candidate: Dict[str, Any],
        *,
        requested_notional_usd: Optional[float] = None,
        market_ids: Optional[Any] = None,
        now_ts: Optional[float] = None,
        exclude_intent_ids: Optional[Any] = None,
        reserve_on_accept: bool = False,
    ) -> Dict[str, Any]:
        """Pre-trade v6 reservation, hierarchical risk budget, and CWCE check (strictly preserving D-001 KMIA quarantine)."""
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            evaluate_candidate_v6_cwce_and_reservation,
        )

        return evaluate_candidate_v6_cwce_and_reservation(
            self,
            candidate,
            requested_notional_usd=requested_notional_usd,
            market_ids=market_ids,
            now_ts=now_ts,
            exclude_intent_ids=exclude_intent_ids,
            reserve_on_accept=reserve_on_accept,
        )

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
        if len(self.closed_positions) > 500:
            self.closed_positions = self.closed_positions[-500:]

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
        """
        asset = str(asset).upper()
        env_dir = os.environ.get("PM_FAST_TICK_DIR")
        tick_dir = Path(env_dir) if env_dir else FAST_TICK_DIR
        tele_dir = Path(os.environ.get("PM_TELEMETRY_DIR", str(DATA_DIR)))
        tele_name = "polymarket_hourly_telemetry.jsonl" if asset == "BTC" else f"polymarket_hourly_telemetry_{asset.lower()}.jsonl"

        def _age_with_payload(p: Path, is_jsonl: bool = False) -> float:
            try:
                raw_m = float(now_ts) - p.stat().st_mtime
                if raw_m < -2.0:
                    return float("inf")
                m_age = max(0.0, raw_m)
                try:
                    if not is_jsonl:
                        snap = _json_loads(p.read_bytes())
                        if isinstance(snap, dict):
                            in_ts = float(snap.get("ts") or snap.get("timestamp_unix") or 0.0)
                            sp_ts = float(snap.get("spot_ts") or 0.0)
                            eff_age = m_age
                            if in_ts > 0.0:
                                in_age = float(now_ts) - in_ts
                                if in_age < -2.0:
                                    return float("inf")
                                eff_age = max(eff_age, max(0.0, in_age))
                            if sp_ts > 0.0:
                                sp_age = float(now_ts) - sp_ts
                                if sp_age < -2.0:
                                    return float("inf")
                                eff_age = max(eff_age, max(0.0, sp_age))
                            return eff_age
                    else:
                        sz = p.stat().st_size
                        if sz > 2:
                            with open(p, "rb") as fh:
                                fh.seek(max(0, sz - 4096))
                                lines = [ln.strip() for ln in fh.read().splitlines() if ln.strip()]
                            if lines:
                                last_obj = _json_loads(lines[-1])
                                if isinstance(last_obj, dict):
                                    in_ts = float(last_obj.get("timestamp_unix") or last_obj.get("ts") or 0.0)
                                    if in_ts > 0.0:
                                        in_age = float(now_ts) - in_ts
                                        return float("inf") if in_age < -2.0 else max(m_age, max(0.0, in_age))
                except Exception:
                    pass
                return m_age
            except OSError:
                return float("inf")

        tick_age = _age_with_payload(tick_dir / f"pm_fast_tick_{asset}.json", is_jsonl=False)
        fast_max = float(self.risk_config["stale_fast_tick_max_age_sec"])
        if tick_age <= fast_max:
            return True, tick_age, f"fast_tick_age={tick_age:.1f}s<={fast_max:.0f}s"
        tele_age = _age_with_payload(tele_dir / tele_name, is_jsonl=True)
        tele_max = float(self.risk_config["stale_telemetry_max_age_sec"])
        newest = min(tick_age, tele_age)
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

    def _append_shadow_phase3_4_event(self, record: Dict[str, Any]) -> None:
        """Appends a structured Phase 3A / Phase 4 shadow telemetry event to shadow_phase3_4_tracker.jsonl (fail-open)."""
        raw_target = os.environ.get("PM_SHADOW_TRACKER_FILE")
        if raw_target is not None and not raw_target.strip():
            return
        try:
            out_path = Path(raw_target) if raw_target else SHADOW_PHASE3_4_FILE
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.debug(f"[SHADOW_TRACKER] Write failed: {exc}")

    def _register_shadow_phase3a_maker_in(
        self,
        shock: Dict[str, Any],
        target_token: str,
        first_ask: float,
        first_bid: float,
        max_allowed_price: float,
        raw_asks: List[Tuple[float, float]],
        reject_reason: str,
        is_subhourly: bool,
        dist_pct: float,
        tte: float,
    ) -> None:
        """
        Phase 3A Shadow Tracker: Registers a virtual 15s Post-Only Maker-In limit order (0% fee + 20% rebate)
        whenever a qualified shock is rejected by max_allowed_price, 400 FAK miss, or FOK Sweep Infeasible.
        Also records Idea #1 (Elastic Rung Down-Snapping) and Idea #5 (+2c Fallback Headroom) diagnostics.
        """
        try:
            if first_ask <= 0.0 or first_bid < 0.50 or tte < 35.0:
                return
            m_id = str(shock.get("market_id") or "")
            if not m_id:
                return
            shadow_orders = getattr(self, "_shadow_maker_orders", None)
            if shadow_orders is None:
                self._shadow_maker_orders = {}
                shadow_orders = self._shadow_maker_orders
            key = f"{m_id}_{target_token}"
            if key in shadow_orders:
                return  # already tracking a shadow maker order for this market/direction

            maker_px = round(min(max_allowed_price, first_ask - 0.01), 2)
            if maker_px < 0.54:
                return
            r_rebate = 0.20 * 0.07
            maker_eff_cost = round(maker_px - r_rebate * maker_px * (1.0 - maker_px), 5)

            # Idea #1 diagnostic: check available L1/limit depth for $16.50 / $12.00 pre-signed rungs
            depth_at_max = sum(px * sz for px, sz in (raw_asks or []) if px <= max_allowed_price)
            snapped_rung = 16.50 if depth_at_max >= 16.50 else (12.00 if depth_at_max >= 12.00 else 0.0)
            headroom_cents = round((max_allowed_price - first_ask) * 100.0, 2)

            now_ts = time.time()
            ttl_sec = float(os.environ.get("PM_SHADOW_MAKER_TTL_SEC", "3.5"))
            open_spot = float(
                (shock.get("candle_open_spot") if is_subhourly else (shock.get("finalized_1h_open") or shock.get("candle_open_spot")))
                or 0.0
            )
            expiry_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (now_ts + tte))
            asset_str = str(shock.get("asset") or "BTC").upper()

            rec = {
                "event_type": "SHADOW_PHASE3A_MAKER_IN_REGISTERED", "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                "market_id": m_id, "title": shock.get("title"), "asset": asset_str, "horizon": "15m" if is_subhourly else "1h",
                "target_token": target_token, "reject_reason": reject_reason, "first_ask": round(first_ask, 4), "first_bid": round(first_bid, 4),
                "max_allowed_price": round(max_allowed_price, 4), "shadow_maker_px": maker_px, "shadow_maker_eff_cost": maker_eff_cost,
                "idea1_depth_at_max_usd": round(depth_at_max, 2), "idea1_snapped_rung_usd": snapped_rung, "idea5_headroom_cents": headroom_cents,
                "entry_dist_pct": round(dist_pct, 4), "tte_sec": round(tte, 1), "placed_ts": now_ts, "ttl_sec": ttl_sec,
                "ttl_expires_ts": now_ts + ttl_sec, "expiry_ts": expiry_ts, "open_spot": open_spot, "status": "RESTING",
            }
            shadow_orders[key] = rec
            self._append_shadow_phase3_4_event(rec)
            logger.info(
                f"[SHADOW PHASE 3A] Registered virtual Maker-In {asset_str} {target_token} @ ${maker_px:.2f} "
                f"(eff=${maker_eff_cost:.4f}, TTL={ttl_sec:.1f}s, reason={reject_reason}, snapped_rung=${snapped_rung:.2f})"
            )
        except Exception as exc:
            logger.debug(f"[SHADOW PHASE 3A] Register error: {exc}")

    @staticmethod
    def _ws_snap_fully_filled(snap_o: Any, expected_sh: float = 0.0) -> bool:
        if not isinstance(snap_o, dict) or str(snap_o.get("status") or "").upper() not in ("MATCHED", "FILLED"):
            return False
        req_sh = max(float(expected_sh or 0.0), float(snap_o.get("original_size") or 0.0))
        return req_sh <= 0.0 or float(snap_o.get("size_matched") or 0.0) >= req_sh - 1e-6

    async def _reconcile_maker_entry_fill(
        self,
        maker_oid: str,
        token_id: str,
        ws_filled: bool,
        posted_sh: float,
        fallback_px: float,
        pre_bal: Optional[float] = None,
        *,
        allow_ws_fast_fill: bool = False,
        use_fast_cancel: Optional[bool] = None,
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], float, float]:
        _fast_canc_ok = (
            bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_fast_1rtt_cancel", True))
            if use_fast_cancel is None
            else bool(use_fast_cancel)
        )

        def _canc_one() -> Dict[str, Any]:
            if (
                _fast_canc_ok
                and hasattr(self.executor, "cancel_order_fast")
                and "cancel_order" not in getattr(self.executor, "__dict__", {})
            ):
                try:
                    return self.executor.cancel_order_fast(maker_oid, token_id=token_id, pre_token_balance=pre_bal)
                except TypeError:
                    return self.executor.cancel_order_fast(maker_oid)
            try:
                return self.executor.cancel_order(maker_oid, token_id=token_id, pre_token_balance=pre_bal)
            except TypeError:
                return self.executor.cancel_order(maker_oid)

        cancel_res = {"is_canceled": False, "outcome": "FILLED"} if ws_filled else await asyncio.to_thread(_canc_one)
        _uws_rec = getattr(self.executor, "_user_ws_cache", None)
        _uws_ok_fast = bool(_uws_rec is not None and hasattr(_uws_rec, "is_healthy") and _uws_rec.is_healthy())
        _uws_snap = _uws_rec.get_order_snapshot(maker_oid, max_age_sec=10.0) if (_uws_rec is not None and hasattr(_uws_rec, "get_order_snapshot")) else None
        _uws_m = float((_uws_snap or {}).get("size_matched") or 0.0) if isinstance(_uws_snap, dict) else 0.0
        if (
            not self.dry_run
            and ws_filled
            and allow_ws_fast_fill
            and _uws_ok_fast
            and isinstance(_uws_snap, dict)
            and _uws_m >= max(0.01, float(posted_sh or 0.0) - 1e-4)
            and "get_order_fill_summary" not in getattr(self.executor, "__dict__", {})
            and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
        ):
            ws_px = float(_uws_snap.get("avg_fill_price") or _uws_snap.get("price") or fallback_px)
            if _STAGE_B_MARKOUT_SAMPLER is not None and _uws_m > 0.01 and ws_px > 0.0 and hasattr(self.executor, "get_market_book"):
                try:
                    _sl_mk = next((str(v.get("sleeve") or v.get("sleeve_source") or "") for v in (self.pending_entry_intents or {}).values() if isinstance(v, dict) and str(v.get("entry_order_id") or v.get("order_id") or "") == str(maker_oid)), "") or "MAKER_ENTRY"
                    _m_ws_r = getattr(self, "_pos_market_ws", None)
                    _bk_fn = (lambda _t: (_m_ws_r.get_book(str(_t), max_age_sec=5.0) if _m_ws_r is not None else None) or self.executor.get_market_book(str(_t)))
                    _STAGE_B_MARKOUT_SAMPLER.schedule_maker_fill(
                        order_id=str(maker_oid), token_id=str(token_id), sleeve=_sl_mk, side="BUY",
                        fill_px=ws_px, shares=_uws_m, book_lookup_fn=_bk_fn,
                    )
                except Exception:
                    pass
            return (
                cancel_res,
                {
                    "order_id": maker_oid,
                    "matched": _uws_m,
                    "avg_price": ws_px,
                    "cash": round(_uws_m * ws_px, 6),
                    "fee": 0.0,
                    "terminal": True,
                    "resting": False,
                    "source": "USER_WS_FAST_FILL",
                },
                _uws_m,
                ws_px,
            )
        if (
            not self.dry_run
            and not ws_filled
            and _uws_ok_fast
            and isinstance(_uws_snap, dict)
            and _uws_m <= 0.0
            and str(_uws_snap.get("status") or "").upper() in ("CANCELED", "CANCELLED")
            and bool((cancel_res or {}).get("is_canceled"))
            and not bool((cancel_res or {}).get("read_replica_stale_live"))
            and float((cancel_res or {}).get("matched") or 0.0) <= 0.0
            and "get_order_fill_summary" not in getattr(self.executor, "__dict__", {})
            and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
        ):
            return (
                cancel_res,
                {"order_id": maker_oid, "matched": 0.0, "avg_price": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True, "resting": False, "source": "USER_WS_FAST_CANCEL"},
                0.0,
                fallback_px,
            )
        summary = await asyncio.to_thread(self.executor.get_order_fill_summary, maker_oid, token_id)
        if ws_filled and (summary is None or bool(summary.get("resting")) or float((summary or {}).get("matched") or 0.0) < 0.01):
            cancel_res = await asyncio.to_thread(_canc_one)
            summary = await asyncio.to_thread(self.executor.get_order_fill_summary, maker_oid, token_id)
        c_out = str((cancel_res or {}).get("outcome") or "")
        exp_sh = max(
            _uws_m,
            float(posted_sh or 0.0) if (ws_filled or c_out == "FILLED") else float((cancel_res or {}).get("matched") or 0.0),
        )
        stale_live_lag = bool(not self.dry_run and not ws_filled and (bool((cancel_res or {}).get("read_replica_stale_live")) or bool((summary or {}).get("resting"))))
        for _ in range(3):
            need_more = (exp_sh > 0.01 and float((summary or {}).get("matched") or 0.0) < exp_sh - 0.01) or (stale_live_lag and bool((summary or {}).get("resting")))
            if not need_more:
                break
            await asyncio.sleep(0.15)
            summary = await asyncio.to_thread(self.executor.get_order_fill_summary, maker_oid, token_id)
        s_m = float((summary or {}).get("matched") or 0.0)
        matched_sh = max(s_m, _uws_m, float((cancel_res or {}).get("matched") or 0.0), float(posted_sh or 0.0) if (ws_filled and s_m > 0.0) else 0.0)
        s_cash = float((summary or {}).get("cash") or 0.0)
        avg_px = float((summary or {}).get("avg_price") or (round(s_cash / s_m, 6) if (s_cash > 0.0 and s_m > 0.0) else 0.0) or (summary or {}).get("limit_price") or fallback_px)
        if not self.dry_run and _STAGE_B_MARKOUT_SAMPLER is not None and matched_sh > 0.01 and avg_px > 0.0 and hasattr(self.executor, "get_market_book"):
            try:
                _sl_mk = next((str(v.get("sleeve") or v.get("sleeve_source") or "") for v in (self.pending_entry_intents or {}).values() if isinstance(v, dict) and str(v.get("entry_order_id") or v.get("order_id") or "") == str(maker_oid)), "") or "MAKER_ENTRY"
                _m_ws_r = getattr(self, "_pos_market_ws", None)
                _bk_fn = (lambda _t: (_m_ws_r.get_book(str(_t), max_age_sec=5.0) if _m_ws_r is not None else None) or self.executor.get_market_book(str(_t)))
                _STAGE_B_MARKOUT_SAMPLER.schedule_maker_fill(
                    order_id=str(maker_oid), token_id=str(token_id), sleeve=_sl_mk, side="BUY",
                    fill_px=avg_px, shares=matched_sh, book_lookup_fn=_bk_fn,
                )
            except Exception:
                pass
        return cancel_res, summary, matched_sh, avg_px

    _attempt_live_phase3a_maker_rescue = _bind_hv_method(_hv__attempt_live_phase3a_maker_rescue, '_attempt_live_phase3a_maker_rescue')

    async def _maybe_merge_live_complete_sets(self, now_ts: float) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import maybe_merge_live_complete_sets_impl
        await maybe_merge_live_complete_sets_impl(self, now_ts, ExecutionStatus, logger)

    async def _execute_guarded_complement_merge(
        self, tid: str, pos: Dict[str, Any], opp_tok: str, cm_plan: Dict[str, Any], now_ts: float
    ) -> bool:
        from src.polymarket_research.riskless_protocol_v2_expansion import execute_guarded_complement_merge_impl
        return await execute_guarded_complement_merge_impl(self, tid, pos, opp_tok, cm_plan, now_ts, ExecutionStatus)

    async def _try_atomic_box_overround_unwind(self, now_ts: float, open_oids: Set[str]) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import try_atomic_box_overround_unwind_impl
        await try_atomic_box_overround_unwind_impl(
            self, now_ts, open_oids, pos_is_recv_fn=position_is_settlement_receivable,
            read_fast_tick_fn=read_fast_tick, walk_ovr_fn=walk_dual_leg_overround_bids,
            gov_mgr=GLOBAL_GOVERNANCE_MANAGER, exec_status_cls=ExecutionStatus, h_logger=logger,
        )

    def _update_shadow_phase4_monotonicity_scanner(
        self, shock: Dict[str, Any], asset_str: str, is_subhourly: bool, is_1h: bool, tte: float, open_spot: float
    ) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import update_shadow_phase4_monotonicity_scanner_impl
        update_shadow_phase4_monotonicity_scanner_impl(
            self, shock, asset_str, is_subhourly, is_1h, tte, open_spot,
            eval_basis_fn=evaluate_cross_oracle_basis_box_ev, h_logger=logger,
        )

    def _step_shadow_phase3_4_tracker(self, now_ts: float) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import step_shadow_phase3_4_tracker_impl
        step_shadow_phase3_4_tracker_impl(self, now_ts, read_fast_tick_fn=read_fast_tick, h_logger=logger)

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
            if self.dry_run:
                return None
            tick_dir = "/dev/shm"
        shm_path = Path(f"{tick_dir}/pm_fast_tick_{asset}.json")
        if not shm_path.exists():
            return None
        try:
            raw = _json_loads(shm_path.read_bytes())
            mkt_payload = raw.get("markets", {}).get(target_mid) if isinstance(raw.get("markets"), dict) else raw
            if not isinstance(mkt_payload, dict):
                return None
            if str(mkt_payload.get("market_id") or "") != target_mid:
                return None
            ts = float(mkt_payload.get("timestamp_unix") or mkt_payload.get("ts") or 0.0)
            age_s = time.time() - ts
            if ts <= 0.0 or age_s > 1.5 or age_s < -2.0:
                return None
            side_book = mkt_payload.get(target_side) or {}
            if str(side_book.get("token_id") or "") != target_tid:
                return None
            raw_bids = side_book.get("raw_top_bids") or []
            raw_asks = side_book.get("raw_top_asks") or []
            if raw_bids:
                return {
                    "bids": [{"price": str(p), "size": str(s)} for p, s in raw_bids],
                    "asks": [{"price": str(p), "size": str(s)} for p, s in raw_asks],
                    "timestamp": ts,
                }
            best_b = float(side_book.get("best_bid", 0.0) or 0.0)
            best_a = float(side_book.get("best_ask", 1.0) or 1.0)
            b_sz = float(side_book.get("bid_size_l1", 0.0) or 0.0)
            a_sz = float(side_book.get("ask_size_l1", 0.0) or 0.0)
            if best_b <= 0.0 or b_sz <= 0.0:
                return None
            return {
                "bids": [{"price": str(best_b), "size": str(b_sz)}],
                "asks": [{"price": str(best_a), "size": str(a_sz)}] if best_a < 1.0 and a_sz > 0 else [],
                "timestamp": ts,
            }
        except Exception:
            return None

    async def _atomic_replace_maker_exit(
        self, tid: str, pos: Dict[str, Any], new_price: float, collapse_tranches: bool = False
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

        order_matched = 0.0
        if old_oid:
            cancel_res = await asyncio.to_thread(self.executor.cancel_order, str(old_oid))
            is_canceled = bool((cancel_res or {}).get("is_canceled"))
            summary = await asyncio.to_thread(self.executor.get_order_fill_summary, str(old_oid), token_id)
            if is_canceled and isinstance(summary, dict) and summary.get("resting", False):
                await asyncio.sleep(0.25)
                summary = await asyncio.to_thread(self.executor.get_order_fill_summary, str(old_oid), token_id)
            if summary is None:
                logger.warning(
                    f"[QUEUE JUMP ABORT] No fill summary for {old_oid} after cancel; retaining reservation."
                )
                pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                pos["pending_canceled_order_id"] = str(old_oid)
                await asyncio.to_thread(self.save_state)
                return False
            order_matched = float(summary.get("matched", 0.0) or 0.0)
            self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.99) or 0.99), taker=False)
            if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.02:
                self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                return True
            if summary.get("resting", False) or not is_canceled or not summary.get("terminal", False):
                if not summary.get("resting", False) or is_canceled:
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

        post_size = rem_shares
        active_tranche = None
        if collapse_tranches:
            pos.pop("exit_tranches", None)
        elif pos.get("exit_tranches"):
            for t in pos["exit_tranches"]:
                if t.get("status") in {"POSTED", "IN_FLIGHT"}:
                    t_rem = max(0.0, round(float(t.get("size", 0.0)) - order_matched, 2))
                    if t_rem <= 0.01:
                        t["status"] = "FILLED"
                    else:
                        t["size"] = t_rem
                        t["status"] = "PENDING"
            pending_tr = [t for t in pos["exit_tranches"] if t.get("status") == "PENDING" and float(t.get("size", 0.0)) >= 5.0]
            if pending_tr and rem_shares >= 5.0:
                cand_sz = min(rem_shares, float(pending_tr[0]["size"]))
                leftover = round(rem_shares - cand_sz, 4)
                if 0.01 < leftover < 5.0:
                    pos.pop("exit_tranches", None)
                else:
                    active_tranche = pending_tr[0]
                    post_size = cand_sz
                    active_tranche["price"] = round(float(new_price), 4)
            else:
                pos.pop("exit_tranches", None)

        if post_size < 5.0 and not self.dry_run and str(token_id).isdigit() and len(str(token_id)) >= 20:
            pos["exit_order_status"] = "SUB_MINIMUM_LOT_SUPERVISED_HOLD"
            pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
            await asyncio.to_thread(self.save_state)
            return False

        pos["target_exit_price"] = round(float(new_price), 4)
        exit_res = await asyncio.to_thread(
            self.executor.post_maker_exit_order,
            token_id=token_id,
            price=pos["target_exit_price"],
            size=post_size,
            side="SELL",
        )
        posted = self._apply_exit_post_result(pos, exit_res, post_size)
        if active_tranche is not None and posted:
            active_tranche["status"] = "POSTED"
        elif active_tranche is not None and (exit_res or {}).get("outcome_unknown"):
            active_tranche["status"] = "IN_FLIGHT"
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
                    if asset in ("BTC", "ETH", "SOL") and t0_unix and open_p and float(open_p) > 0:
                        h_idx = int(float(t0_unix) // 3600)
                        asset_opens = self.hourly_candle_opens.setdefault(asset, {})
                        if h_idx not in asset_opens:
                            asset_opens[h_idx] = float(open_p)
                except Exception:
                    pass
            logger.info(
                f"[TREND GUARD PREWARMED] Prewarmed {len(self.hourly_candle_opens.get('BTC', {}))} BTC, "
                f"{len(self.hourly_candle_opens.get('SOL', {}))} SOL, and "
                f"{len(self.hourly_candle_opens.get('ETH', {}))} ETH hourly opens for multi-hour trend alignment."
            )
        except Exception as e:
            logger.warning(f"[TREND GUARD PREWARM WARN] Failed to prewarm hourly opens: {e}")

    def _register_active_warmed_token(self, tok_id: str, expiry_ts: float = 0.0) -> None:
        if not tok_id:
            return
        reg = getattr(self, "_active_warmed_token_expiries", None)
        if reg is None:
            reg = {}
            self._active_warmed_token_expiries = reg
        now_u = time.time()
        exp_val = float(expiry_ts or 0.0)
        if exp_val <= 0.0:
            exp_val = now_u + 3600.0
        reg[str(tok_id)] = max(float(reg.get(str(tok_id), 0.0)), exp_val)
        expired = [k for k, v in reg.items() if v < now_u - 30.0]
        for k in expired:
            reg.pop(k, None)
        _max_warm = 24 if len(getattr(self, "allowed_assets", None) or ()) >= 3 else 12
        while len(reg) > _max_warm:
            furthest_k = max(reg, key=reg.get)
            reg.pop(furthest_k, None)

    def _prewarm_market_metadata(self, shock: Dict[str, Any]):
        """Proactively warms CLOB caches with authoritative Polymarket V2 fee rates (default 700 bps / exponent 1.0)."""
        try:
            title_l = str(shock.get("title", "") or "").lower()
            default_rate = 0.07

            cond_id = shock.get("condition_id") or shock.get("fee_metadata", {}).get("condition_id")
            fee_meta = shock.get("fee_metadata", {})
            fee_rate = float(fee_meta.get("fee_rate_market", default_rate) or default_rate)
            fee_exp = float(fee_meta.get("fee_exponent", 1.0) or 1.0)
            fee_bps = int(round(fee_rate * 10000))
            exp_ts = float(shock.get("candle_expiry_ts") or shock.get("expiry_ts") or 0.0)
            if exp_ts <= 0.0 and shock.get("seconds_to_expiry"):
                exp_ts = float(shock.get("t0_unix") or time.time()) + float(shock.get("seconds_to_expiry") or 0.0)
            asset_s = str(shock.get("asset") or "").upper()
            if not asset_s:
                asset_s = "BTC" if "btc" in title_l or "bitcoin" in title_l else ("ETH" if "eth" in title_l or "ethereum" in title_l else ("SOL" if "sol" in title_l or "solana" in title_l else ""))
            allow_ladder = (not self._is_riskless_only_mode()) and ((not asset_s) or (asset_s in getattr(self, "allowed_assets", {"BTC", "ETH"})))
            feats = shock.get("pre_shock_features_t0", {})
            for side_key in ("UP", "DOWN"):
                tok_info = feats.get(side_key, {})
                tok_id = tok_info.get("token_id")
                if tok_id:
                    self.executor.prewarm_token_market_cache(
                        token_id=tok_id,
                        tick_size=tok_info.get("tick_size") or shock.get("tick_size") or "0.01",
                        neg_risk=False,
                        fee_rate_bps=fee_bps,
                        condition_id=cond_id,
                        fee_rate=fee_rate,
                        fee_exponent=fee_exp,
                    )
                    if allow_ladder and (exp_ts <= 0.0 or exp_ts > time.time() - 30.0):
                        self._register_active_warmed_token(str(tok_id), exp_ts)
        except Exception as exc:
            logger.debug(f"[PREWARM NOTICE] Prewarm metadata notice: {exc}")

    def _handle_prewarm_ipc_signal(self) -> None:
        """Handles sub-threshold shock precursor IPC: drains Gen-0 GC early and touches hot CLOB TLS socket."""
        now_m = time.monotonic()
        if (now_m - float(getattr(self, "_last_precursor_touch_mono", 0.0) or 0.0)) < 1.5:
            return
        self._last_precursor_touch_mono = now_m
        if not getattr(self, "active_positions", None):
            try:
                import gc as _gc_p
                _gc_p.collect(0)
            except Exception:
                pass
        if not self.dry_run and hasattr(self.executor, "touch_hot_async_clob_socket"):
            try:
                asyncio.get_running_loop().create_task(self.executor.touch_hot_async_clob_socket(1.5))
            except Exception:
                pass

    def _prewarm_active_market_tokens(self):
        """Pre-warms active market tokens without re-reading disk after startup."""
        try:
            _rl_only = self._is_riskless_only_mode()
            reg = getattr(self, "_active_warmed_token_expiries", None)
            if (not _rl_only) and (not getattr(self, "_startup_prewarmed_logged", False) or not reg):
                if TRIGGER_FILE.exists() and TRIGGER_FILE.stat().st_size > 0:
                    sz = TRIGGER_FILE.stat().st_size
                    read_sz = min(sz, 131072)
                    with open(TRIGGER_FILE, "rb") as f:
                        f.seek(sz - read_sz)
                        lines = f.read().decode("utf-8", errors="ignore").splitlines()
                    for l in reversed(lines):
                        if not l.strip():
                            continue
                        try:
                            shk = _json_loads(l)
                            self._prewarm_market_metadata(shk)
                        except Exception:
                            continue
            reg = getattr(self, "_active_warmed_token_expiries", None) or {}
            now_u = time.time()
            active_tokens = [k for k, exp_v in reg.items() if exp_v >= now_u - 30.0]
            if active_tokens and not getattr(self, "_startup_prewarmed_logged", False):
                self._startup_prewarmed_logged = True
                logger.info(f"[HOT-PATH PREWARMED] Proactively pre-warmed CLOB metadata & fee caches for {len(active_tokens)} active token(s) [version=2, markets-by-token, clob-markets].")
            if active_tokens and not _rl_only and hasattr(self.executor, "prewarm_order_ladder") and not getattr(self.executor, "dry_run", True):
                self._spawn_ladder_prewarm(active_tokens)
            if getattr(self, "_last_known_collateral", None) is not None:
                self.executor.set_cached_collateral(float(self._last_known_collateral))
        except Exception as e:
            logger.debug(f"[KEEPALIVE PREWARM] Notice: {e}")

    def _spawn_ladder_prewarm(self, tokens: List[str]) -> None:
        """
        Pillar 5A: Pre-signs the $0.55-$0.88 BUY ladder for active UP/DOWN tokens in a single-flight
        daemon thread so EIP-712 signing never blocks the asyncio event loop. Fresh entries are skipped
        inside prewarm_order_ladder, so steady-state cost is near zero.
        """
        import threading

        if _HOT_DISPATCH_ACTIVE.is_set() or self._is_riskless_only_mode():
            return
        existing = getattr(self, "_ladder_prewarm_thread", None)
        if existing is not None and existing.is_alive():
            return
        notionals = [float(self.ticket_notional)]
        collat = getattr(self, "_last_known_collateral", None)
        rungs_pre = (12.00, 16.50, 20.00, 24.00, 28.00, 36.00) if (collat and isinstance(collat, (int, float)) and collat >= 45.0) else (12.00, 13.77, 16.50)
        for fallback_rung in rungs_pre:
            if all(abs(fallback_rung - x) >= 0.40 for x in notionals):
                notionals.append(fallback_rung)
        if getattr(self, "dynamic_sizing", False) and collat and isinstance(collat, (int, float)) and collat > 0:
            dyn_pct = float(getattr(self, "dynamic_bankroll_pct", 0.22) or 0.22)
            for mult in (1.0, 1.15, 0.5405, 0.6216):
                cand_n = round(float(collat) * dyn_pct * mult, 2)
                if cand_n >= 12.0 and all(abs(cand_n - x) >= 0.40 for x in notionals):
                    notionals.append(cand_n)

        def _worker():
            try:
                if hasattr(os, "sched_setscheduler") and hasattr(os, "SCHED_IDLE"):
                    os.sched_setscheduler(0, os.SCHED_IDLE, os.sched_param(0))
            except Exception:
                pass
            signed = 0
            # Wave 3 + Kaizen #2/#4 Bankroll-Proportional Dense Grid + SCHED_IDLE 2-vCPU pacing
            _open_exp = sum(float(p.get("notional_usd") or 0.0) for p in getattr(self, "active_positions", {}).values())
            _hwm_eq = float(getattr(getattr(self, "risk_controller", None), "equity_high_water_mark_usd", 0.0) or 0.0)
            _eq_est = max(float(collat) + _open_exp, _hwm_eq) if (collat and isinstance(collat, (int, float)) and collat > 0) else max(140.0, _hwm_eq)
            max_dense_sh = max(48, min(160, int(math.ceil(max(_eq_est * 0.35, float(self.ticket_notional or 16.5) * 1.35) / 0.52)) + 6))
            dense_shares = list(range(5, max_dense_sh))
            for t in tokens:
                if not getattr(self, "dry_run", True):
                    _w_s2 = 0
                    while 4.0 <= (300.0 - (time.time() % 300.0)) <= 42.0 and _w_s2 < 160:
                        time.sleep(0.25)
                        _w_s2 += 1
                _w_hot = 0
                while _HOT_DISPATCH_ACTIVE.is_set() and _w_hot < 40:
                    time.sleep(0.05)
                    _w_hot += 1
                tok_tick = str(getattr(self.executor, "_tick_size_cache", {}).get(t) or "0.01")
                try:
                    signed += int(
                        self.executor.prewarm_order_ladder(
                            t, 12.0, tick_size=tok_tick, exact_shares=dense_shares, pace_every=2, pace_sleep_sec=0.008
                        ) or 0
                    )
                except TypeError:
                    try:
                        signed += int(self.executor.prewarm_order_ladder(t, 12.0, tick_size=tok_tick, exact_shares=dense_shares) or 0)
                    except TypeError:
                        for n_val in notionals:
                            signed += int(self.executor.prewarm_order_ladder(t, n_val) or 0)
                except Exception as e:
                    logger.debug(f"[PREWARM LADDER] dense grid notice for {t}: {e}")
                for n_val in notionals:
                    if n_val <= 18.0 or (math.floor(n_val / 0.55) + 1) < max_dense_sh:
                        continue
                    try:
                        signed += int(
                            self.executor.prewarm_order_ladder(
                                t, n_val, tick_size=tok_tick, share_deltas=(-2, -1, 0, 1), pace_every=2, pace_sleep_sec=0.008
                            ) or 0
                        )
                    except TypeError:
                        signed += int(self.executor.prewarm_order_ladder(t, n_val) or 0)
                    except Exception as e:
                        logger.debug(f"[PREWARM LADDER] notice for {t}: {e}")
                time.sleep(0.015)
            if signed:
                if not getattr(self, "_gc_frozen_ladder", False) and signed >= 500:
                    self._gc_frozen_ladder = True
                    try:
                        import gc as _gc_f
                        _gc_f.collect()
                        if hasattr(_gc_f, "freeze"):
                            _gc_f.freeze()
                    except Exception:
                        pass
                logger.info(
                    f"[PREWARM LADDER] Pre-signed {signed} BUY order(s) across {len(tokens)} token(s) "
                    f"(dense_shares=5..{max_dense_sh - 1} + tickets={[n for n in notionals if n > 18.0]})."
                )

        th = threading.Thread(target=_worker, name="ladder-prewarm", daemon=True)
        self._ladder_prewarm_thread = th
        th.start()

    async def _prewarm_next_candle_markets(self) -> None:
        """
        Upgrade 4: Pre-warms next 1-hour and 15-minute market condition IDs, token IDs,
        fee structures, and CLOB metadata caches from Gamma API 2 minutes before candle expiry
        (:58, :13, :28, :43), guaranteeing zero blindness or pre-flight REST latency at candle open.
        """
        dir_slugs = (
            "btc-up-or-down-hourly",
            "solana-up-or-down-hourly",
            "eth-up-or-down-hourly",
            "btc-up-or-down-15m",
            "solana-up-or-down-15m",
            "eth-up-or-down-15m",
        )
        series_slugs = (*dir_slugs, "xrp-up-or-down-15m", "btc-updown-5m", "eth-updown-5m", "sol-updown-5m", "xrp-updown-5m")
        held_tokens = {str(p.get("token_id") or "") for p in getattr(self, "active_positions", {}).values()}
        pre_bal_cache = self.__dict__.setdefault("_d1_clean_pre_bal_cache", {})
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

                                default_slug_rate = 0.07
                                fee_sched = market.get("feeSchedule", {})
                                rate = float(fee_sched.get("rate", default_slug_rate) or default_slug_rate)
                                exp = float(fee_sched.get("exponent", 1.0) or 1.0)
                                bps = int(round(rate * 10000))

                                now_pb = time.time()
                                gamma_tick = market.get("orderPriceMinTickSize") or "0.01"
                                _slug_l = slug.lower()
                                _slug_asset = "BTC" if "btc" in _slug_l else ("SOL" if "sol" in _slug_l else ("ETH" if "eth" in _slug_l else "XRP"))
                                _ladder_horizon_cap = 1050.0 if "15m" in _slug_l else 2520.0
                                _allow_slug_ladder = (
                                    not self._is_riskless_only_mode()
                                    and slug in dir_slugs
                                    and _slug_asset in self.get_graduated_allowed_assets()
                                    and secs_left <= _ladder_horizon_cap
                                )
                                for t in (t_up, t_down):
                                    self.executor.prewarm_token_market_cache(
                                        token_id=t,
                                        tick_size=gamma_tick,
                                        neg_risk=False,
                                        fee_rate_bps=bps,
                                        condition_id=cond_id,
                                        fee_rate=rate,
                                        fee_exponent=exp,
                                    )
                                    if _allow_slug_ladder:
                                        self._register_active_warmed_token(str(t), now_utc.timestamp() + secs_left)
                                    if str(t) not in held_tokens:
                                        pre_bal_cache[str(t)] = (0.0, now_pb)
                                warmed += 1
            except Exception as e:
                logger.debug(f"[PREWARM NOTICE] Error pre-warming series {slug}: {e}")

        if warmed > 0:
            logger.info(f"[PREWARM NEXT-CANDLE] Pre-warmed metadata & CLOB caches for {warmed} upcoming token(s) from Gamma API.")
            self._prewarm_active_market_tokens()

    def _has_unsettled_collateral_overlap(self, now_ts: Optional[float] = None) -> bool:
        """
        True whenever CLOB L2 collateral balance and active_positions valuation may transiently
        overlap (e.g. UNRESOLVED_SETTLEMENT / AWAITING_ONCHAIN_SETTLEMENT payouts already in
        collateral, MATCHED_PENDING_SETTLEMENT or <30s post-entry indexer lag before collateral
        deduction, or partial maker exit fills before remaining_cost_basis settles).
        While True, high_water_mark_equity must NOT ratchet upward.
        """
        if now_ts is None:
            now_ts = time.time()
        if getattr(self, "pending_entry_intents", None):
            return True
        for p in (getattr(self, "active_positions", None) or {}).values():
            st = p.get("status")
            if st in {
                "MATCHED_PENDING_SETTLEMENT",
                "ENTRY_OUTCOME_UNKNOWN",
                "UNRESOLVED_SETTLEMENT",
                "AWAITING_ONCHAIN_SETTLEMENT",
            }:
                return True
            if position_is_settlement_receivable(p):
                return True
            expiry_ts = float(p.get("candle_expiry_ts") or 0.0)
            if expiry_ts > 0.0 and now_ts >= expiry_ts:
                return True
            entry_ts = float(p.get("entry_ts") or 0.0)
            if entry_ts > 0.0 and (now_ts - entry_ts) < 30.0:
                return True
            if (
                float(p.get("filled_exit_shares", 0.0) or 0.0) > 0.0
                or float(p.get("confirmed_realized_cash", 0.0) or 0.0) > 0.0
                or float(p.get("estimated_exit_cash", 0.0) or 0.0) > 0.0
            ):
                return True
        return False

    def _is_v5_live_strict(self) -> bool:
        """
        True when running real unmocked L2 live execution on production (or explicit `holistic_v5_live_mode=True`),
        preserving 100% backward compatibility with legacy dry-run and mocked unit test fixtures.
        """
        explicit_v5 = getattr(self, "holistic_v5_live_mode", None)
        if explicit_v5 is False:
            return False
        if explicit_v5 is True:
            return True
        ex = getattr(self, "executor", None)
        ex_dict = getattr(ex, "__dict__", {}) if ex is not None else {}
        return bool(
            not getattr(self, "dry_run", True)
            and getattr(ex, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
            and getattr(ex, "client", None) is not None
            and getattr(getattr(ex, "client", None), "_mock_children", None) is None
            and not any(k in ex_dict for k in ("execute_snipe_order_async", "execute_snipe_order"))
        )

    def _is_v5_unleashed_active(self) -> bool:
        return bool(
            self._is_v5_live_strict()
            and GLOBAL_GOVERNANCE_MANAGER.snapshot.get("sizing_tiers", {}).get("unleash_full_throttle", True)
        )

    def _effective_sizing_equity_usd(
        self, raw_tot_equity: Optional[float], now_ts: Optional[float] = None
    ) -> Tuple[float, bool]:
        """
        Returns `(sizing_equity_usd, has_frozen_uma_lock)`.
        When active positions contain post-expiry UMA-frozen or disputed locks (such as the 4 disputed
        KMIA positions), haircuts sizing/tier/concentration equity to `compute_reconciled_concentration_nav_usd`
        so frozen book cost basis never inflates equity tiers (`HYPER_GROWTH`) or `15%` event concentration caps,
        while preserving `raw_tot_equity` unchanged whenever no frozen/disputed UMA lock exists.
        """
        raw_f = (
            max(0.0, float(raw_tot_equity))
            if (raw_tot_equity is not None and math.isfinite(float(raw_tot_equity)))
            else 0.0
        )
        act_pos = getattr(self, "active_positions", None) or {}
        if not act_pos:
            return raw_f, False
        now_f = float(time.time() if now_ts is None else now_ts)
        try:
            from src.polymarket_research.riskless_protocol_v2_expansion import (
                compute_reconciled_concentration_nav_usd,
                is_post_expiry_uma_frozen_lock,
            )
            has_frozen = any(
                isinstance(p, dict)
                and (
                    is_post_expiry_uma_frozen_lock(p, now_f)
                    or str(p.get("umaResolutionStatus") or "").strip().lower() == "disputed"
                )
                for p in act_pos.values()
            )
            if not has_frozen:
                return raw_f, False
            rec_nav = compute_reconciled_concentration_nav_usd(self, now_ts=now_f)
            return (min(raw_f, rec_nav) if raw_f > 0.0 else rec_nav), True
        except Exception:
            return raw_f, False

    def _update_equity_tier(self, total_equity: float, *, allow_hwm_ratchet: Optional[bool] = None) -> Dict[str, Any]:
        """Calculates equity tier, updates high-water mark, bankroll pct, exposure, and risk limits."""
        tot_equity = float(total_equity) if (total_equity is not None and math.isfinite(float(total_equity))) else 0.0
        seed_thresh = float(RISK_CONFIG.get("seed_survival_equity_threshold", 88.0))
        if allow_hwm_ratchet is None:
            allow_hwm_ratchet = not self._has_unsettled_collateral_overlap()
        cur_hwm = getattr(self, "high_water_mark_equity", None)
        if cur_hwm is None or not math.isfinite(float(cur_hwm)) or float(cur_hwm) <= 0.0:
            self.high_water_mark_equity = tot_equity
        elif tot_equity < seed_thresh and float(cur_hwm) > tot_equity * 1.15:
            self.high_water_mark_equity = tot_equity
        elif allow_hwm_ratchet and tot_equity > float(cur_hwm):
            self.high_water_mark_equity = tot_equity
        prev_tier = getattr(self, "_current_equity_tier", None) or getattr(self, "current_equity_tier", None)
        if self._is_v5_unleashed_active():
            v5_lim = get_unleashed_v5_tier_profile(tot_equity, self.high_water_mark_equity, previous_tier=prev_tier)
            self._current_equity_tier = v5_lim["tier"]
            self.current_equity_tier = v5_lim["tier"]
            self.dynamic_bankroll_pct = v5_lim["dynamic_bankroll_pct"]
            if not getattr(self, "allow_cli_exposure", False):
                self.max_exposure = v5_lim["max_exposure"]
            self.max_concurrent_positions = v5_lim["max_directional_slots"]
            _enforce_v5_slots = os.environ.get("PM_ENFORCE_V5_TIER_SLOTS") == "1" or bool(
                GLOBAL_GOVERNANCE_MANAGER.snapshot.get("sizing_tiers", {}).get("enforce_tier_slots_over_unlimited", False)
            )
            if getattr(self, "allow_cli_concurrency", False) and not _enforce_v5_slots and tot_equity >= v5_lim["min_equity_floor"]:
                self.max_concurrent_positions = max(1, int(getattr(self, "_explicit_max_concurrent", self.max_concurrent_positions)))
                if not getattr(self, "allow_cli_exposure", False) and self._is_unlimited_slots_active():
                    self.max_exposure = round(
                        max(self.max_exposure, 100.0 if tot_equity < 140.0 else (350.0 if tot_equity < 300.0 else 500.0)),
                        2,
                    )
            if hasattr(self.risk_controller, "min_equity_floor_usd"):
                self.risk_controller.min_equity_floor_usd = v5_lim["min_equity_floor"]
            if hasattr(self.risk_controller, "max_daily_loss_usd"):
                self.risk_controller.max_daily_loss_usd = v5_lim["max_daily_loss"]
            if hasattr(self.risk_controller, "max_consecutive_losses"):
                self.risk_controller.max_consecutive_losses = v5_lim["max_consecutive_losses"]
            return v5_lim
        tier_limits = get_equity_tier_limits(tot_equity, self.high_water_mark_equity, previous_tier=prev_tier)
        self._current_equity_tier = tier_limits["tier"]
        self.current_equity_tier = tier_limits["tier"]
        self.dynamic_bankroll_pct = tier_limits["dynamic_bankroll_pct"]
        if not getattr(self, "allow_cli_exposure", False):
            _rcfg_e = getattr(self, "risk_config", None) or RISK_CONFIG
            _cfg_exp = float(_rcfg_e.get("max_exposure", 35.0)) if (not _rcfg_e.get("unlimited_slots") or self._is_unlimited_slots_active()) else float(tier_limits["max_exposure"])
            self.max_exposure = round(min(HARD_PORTFOLIO_EXPOSURE_CEILING if tot_equity < 140.0 else 500.0, max(tier_limits["max_exposure"], min(_cfg_exp, tot_equity * 0.82) if tot_equity > 0 else _cfg_exp)), 2)
        self.max_concurrent_positions = tier_limits["max_concurrent_positions"]
        if hasattr(self.risk_controller, "min_equity_floor_usd"):
            self.risk_controller.min_equity_floor_usd = tier_limits["min_equity_floor"]
        if hasattr(self.risk_controller, "max_daily_loss_usd"):
            self.risk_controller.max_daily_loss_usd = tier_limits["max_daily_loss"]
        if tot_equity < seed_thresh:
            self.max_concurrent_positions = min(self.max_concurrent_positions, int(RISK_CONFIG.get("seed_survival_max_concurrent", 1)))
            if hasattr(self.risk_controller, "min_equity_floor_usd"):
                self.risk_controller.min_equity_floor_usd = float(RISK_CONFIG.get("seed_survival_floor_usd", 48.0))
        if getattr(self, "allow_cli_concurrency", False) and tot_equity >= float(RISK_CONFIG.get("seed_survival_floor_usd", 48.0)):
            self.max_concurrent_positions = max(1, int(getattr(self, "_explicit_max_concurrent", self.max_concurrent_positions)))
            if not getattr(self, "allow_cli_exposure", False):
                if self._is_unlimited_slots_active():
                    self.max_exposure = round(max(self.max_exposure, 100.0 if tot_equity < 140.0 else (350.0 if tot_equity < 300.0 else 500.0)), 2)
                else:
                    self.max_exposure = max(self.max_exposure, round(tot_equity * min(0.82, 0.26 * self.max_concurrent_positions), 2))
        return tier_limits

    def _is_unlimited_slots_active(self) -> bool:
        if os.environ.get("PM_ENFORCE_V5_TIER_SLOTS") == "1" or bool(
            GLOBAL_GOVERNANCE_MANAGER.snapshot.get("sizing_tiers", {}).get("enforce_tier_slots_over_unlimited", False)
        ):
            return False
        return bool(
            (getattr(self, "risk_config", None) or RISK_CONFIG).get("unlimited_slots", False)
            and getattr(self, "allow_cli_concurrency", False)
            and int(getattr(self, "_explicit_max_concurrent", 0) or 0) >= 10
        )

    def _effective_directional_slot_cap(self, now_u: Optional[float] = None) -> int:
        """Returns effective concurrent directional crypto slot cap from live equity tier limits."""
        now_ts = float(now_u if now_u is not None else time.time())
        if self._is_v5_unleashed_active() and not self._is_unlimited_slots_active():
            eq_v5 = float(getattr(self, "_last_known_collateral", 0.0) or 0.0) + sum(
                self.get_position_market_value(p, now_ts) for p in self.active_positions.values()
            )
            prof_v5 = get_unleashed_v5_tier_profile(
                eq_v5 if eq_v5 > 0.0 else 69.06,
                getattr(self, "high_water_mark_equity", None),
                previous_tier=getattr(self, "_current_equity_tier", None),
            )
            return max(1, int(prof_v5["max_directional_slots"]))
        eff_slot_cap = max(1, int(getattr(self, "max_concurrent_positions", 1) or 1))
        if getattr(self, "allow_cli_concurrency", False):
            eq_cli = float(getattr(self, "_last_known_collateral", 0.0) or 0.0) + sum(
                self.get_position_market_value(p, now_ts) for p in self.active_positions.values()
            )
            if eq_cli <= 0.0 or eq_cli >= float(RISK_CONFIG.get("seed_survival_floor_usd", 48.0)):
                return max(1, int(getattr(self, "_explicit_max_concurrent", eff_slot_cap)))
        if getattr(self, "dynamic_sizing", False):
            rcfg_pd = getattr(self, "risk_config", None) or RISK_CONFIG
            eq_pd = float(getattr(self, "_last_known_collateral", 0.0) or 0.0) + sum(
                self.get_position_market_value(p, now_ts) for p in self.active_positions.values()
            )
            if eq_pd > 0.0:
                corr_cap_pd = float(rcfg_pd.get("correlated_crypto_single_slot_threshold", 110.0))
                if not self.dry_run and eq_pd < corr_cap_pd and os.environ.get("PM_ALLOW_SMALL_BANKROLL_CORRELATED_CRYPTO") != "1":
                    eff_slot_cap = 1
                else:
                    tier_lim = get_equity_tier_limits(
                        eq_pd,
                        getattr(self, "high_water_mark_equity", None),
                        previous_tier=getattr(self, "_current_equity_tier", None),
                    )
                    eff_slot_cap = max(1, int(tier_lim.get("max_concurrent_positions", eff_slot_cap) or 1))
        return eff_slot_cap

    async def _async_refresh_collateral(self) -> None:
        """Asynchronously updates CLOB L2 collateral balance in RAM without blocking hot path."""
        if self.dry_run or not self.executor.is_authenticated:
            return
        try:
            bal = await asyncio.to_thread(self.executor.get_collateral_balance, 0.0)
            if bal is not None and isinstance(bal, (int, float)) and math.isfinite(bal) and bal > 0:
                now_ts = time.time()
                cred_w = getattr(self, "_last_exit_credit_window", None)
                deb_w = getattr(self, "_last_entry_debit_window", None)
                if (
                    isinstance(cred_w, tuple) and len(cred_w) == 2
                    and not getattr(self, "pending_entry_intents", None)
                    and (now_ts - float(cred_w[0])) < 15.0
                    and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
                    and float(bal) < float(cred_w[1]) - 0.50
                ):
                    bal = float(cred_w[1])
                    self._pending_collateral_refresh = True
                elif (
                    isinstance(deb_w, tuple) and len(deb_w) == 2
                    and (now_ts - float(deb_w[0])) < 10.0
                    and not (isinstance(cred_w, tuple) and len(cred_w) == 2 and float(cred_w[0]) > float(deb_w[0]))
                    and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
                    and float(bal) > float(deb_w[1]) + 0.50
                ):
                    bal = float(deb_w[1])
                    self._pending_collateral_refresh = True
                prev_bal = getattr(self, "_last_known_collateral", None)
                persisted_bal = getattr(self, "_last_persisted_collateral", prev_bal)
                self._last_known_collateral = float(bal)
                self._collateral_sync_seq = int(getattr(self, "_collateral_sync_seq", 0) or 0) + 1
                from src.polymarket_research.riskless_protocol_v2_expansion import (
                    pending_intents_synced_equity_usd,
                    sync_pending_intents_on_collateral_refresh,
                )
                sync_pending_intents_on_collateral_refresh(self, prev_bal, float(bal))
                for _p_sync in self.active_positions.values():
                    if isinstance(_p_sync, dict) and not _p_sync.get("exit_cash_estimated", False):
                        _sync_exit_c = max(
                            0.0,
                            float(_p_sync.get("confirmed_realized_cash", _p_sync.get("realized_exit_cash", 0.0)) or 0.0)
                            - float(_p_sync.get("realized_exit_fee", 0.0) or 0.0),
                        )
                        if _sync_exit_c > 0.0:
                            _p_sync["_synced_exit_cash_usd"] = max(
                                float(_p_sync.get("_synced_exit_cash_usd", 0.0) or 0.0),
                                _sync_exit_c,
                            )
                self.executor.set_cached_collateral(float(bal))
                _pend_sync_eq = pending_intents_synced_equity_usd(getattr(self, "pending_entry_intents", None))
                active_market_equity = sum(self.get_position_market_value(p, now_ts) for p in self.active_positions.values()) + _pend_sync_eq
                in_flight_unwind_cash = sum(
                    max(
                        float(p.get("confirmed_realized_cash", 0.0) or 0.0),
                        float(p.get("estimated_exit_cash", 0.0) or 0.0),
                    )
                    for p in self.active_positions.values()
                    if p.get("status") == "UNRESOLVED_SETTLEMENT"
                )
                tot_equity = float(bal) + active_market_equity + in_flight_unwind_cash
                sizing_eq, has_frozen_uma = self._effective_sizing_equity_usd(tot_equity, now_ts)
                allow_ratchet = (
                    (in_flight_unwind_cash <= 0.0)
                    and (_pend_sync_eq <= 0.0)
                    and (not has_frozen_uma)
                    and (not self._has_unsettled_collateral_overlap(now_ts))
                )
                prev_tier_sync = getattr(self, "_current_equity_tier", None) or getattr(self, "current_equity_tier", None)
                tier_limits = self._update_equity_tier(sizing_eq, allow_hwm_ratchet=allow_ratchet)
                prev_halted = bool(self.risk_controller.halted)
                ruin_chk_eq = float(tot_equity)
                if not self.dry_run and ruin_chk_eq < float(self.risk_controller.min_equity_floor_usd) and hasattr(self.executor, "get_idle_usdce_balance"):
                    _idle_uc = await asyncio.to_thread(self.executor.get_idle_usdce_balance)
                    if isinstance(_idle_uc, (int, float)) and not isinstance(_idle_uc, bool) and float(_idle_uc) > 0.0:
                        ruin_chk_eq += float(_idle_uc)
                self.risk_controller.check_equity_drawdown(ruin_chk_eq, allow_auto_clear=True)
                halt_transition = (prev_halted != bool(self.risk_controller.halted))
                tier_transition = (prev_tier_sync != tier_limits["tier"])
                if (
                    prev_bal is None
                    or abs(float(bal) - float(prev_bal)) >= 0.25
                    or persisted_bal is None
                    or abs(float(bal) - float(persisted_bal)) >= 0.05
                    or halt_transition
                    or tier_transition
                ):
                    await asyncio.to_thread(self.save_state)
                logger.debug(f"[COLLATERAL SYNC] In-memory collateral: ${bal:.2f}, total equity: ${tot_equity:.2f}, tier: {tier_limits['tier']}")
        except Exception as e:
            logger.debug(f"[COLLATERAL SYNC] Notice: {e}")

    def _effective_exit_policy(self) -> str:
        pol = str(getattr(self, "exit_policy", "") or "")
        if GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {}).get("respect_configured_exit_policy_on_safe", True):
            return pol
        if (
            pol == "hold_98"
            and not getattr(self, "dry_run", True)
            and getattr(self.executor, "client", None) is not None
            and not hasattr(self.executor.client, "_mock_children")
            and int(getattr(self.executor, "signature_type", 0) or 0) == 3
            and not (os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY"))
            and os.getenv("PM_ENABLE_ONCHAIN_MERGE", "0") != "1"
        ):
            return "two_tranche_95_98"
        return pol

    def _calculate_target_exit(self, price: float, tte: float) -> float:
        if getattr(self, "hold_to_maturity", False):
            return 0.98 if price < 0.80 else 0.99
        if self._effective_exit_policy() == "hold_98":
            return 0.98
        return min(0.95, round(price + self.profit_theta, 2))

    def _use_two_tranche_maker_exit(self, sleeve: Optional[str]) -> bool:
        """Enables 2-tranche resting maker exit unless hold_98 / hold_to_maturity is active."""
        if sleeve and ("BOX" in str(sleeve).upper() or sleeve == "SLEEVE_4_BOUNDARY_SNIPE"):
            return False
        if sleeve == "SLEEVE_2_MID_HOUR" and getattr(self, "enable_mid_hour_t1_12c", False):
            return True
        if self._effective_exit_policy() == "hold_98":
            return False
        if not getattr(self, "hold_to_maturity", False):
            return True
        return False

    def _tranche1_tp_offset(self, sleeve: Optional[str]) -> float:
        """Returns +$0.12 when mid-hour tight tranche is explicitly enabled, else +$0.14 (WFO optimum)."""
        if sleeve == "SLEEVE_2_MID_HOUR" and getattr(self, "enable_mid_hour_t1_12c", False):
            return 0.12
        return 0.14

    # Round 9: unified global-halt derivation (persisted, monotonic until reconciled)
    def _global_halt_reasons(self) -> List[str]:
        reasons: List[str] = []
        intents = getattr(self, "pending_entry_intents", {}) or {}
        if intents:
            now_gh = time.time()
            live_mkr_keys = getattr(self, "_inflight_maker_anchor_keys", None) or set()
            live_p3a_ids = getattr(self, "_inflight_phase3a_maker_ids", None) or set()
            live_dir_ids = getattr(self, "_inflight_directional_entry_ids", None) or set()
            unsupervised_keys = [
                k for k, v in intents.items()
                if not (
                    isinstance(v, dict)
                    and (now_gh - float(v.get("heartbeat_ts") or v.get("ts") or v.get("submitted_at_ts") or 0.0)) < 45.0
                    and (
                        (v.get("live_maker_anchor_inflight") and str(v.get("inflight_key") or "") in live_mkr_keys)
                        or (k in live_p3a_ids)
                        or (k in live_dir_ids)
                    )
                )
            ]
            if unsupervised_keys:
                reasons.append(f"PENDING_ENTRY_INTENTS:{','.join(sorted(unsupervised_keys))}")
        _now_gh2 = time.time()
        _ex_sup_gh = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("exit_supervisor", {})
        _iso_lc = bool(_ex_sup_gh.get("isolate_single_market_zero_bid", True))
        _req_lc_mkts = int(_ex_sup_gh.get("global_zero_bid_halt_min_markets", _ex_sup_gh.get("min_markets_for_global_liquidity_halt", 2)))
        _active_map_gh = getattr(self, "active_positions", {}) or {}
        _lc_mkts_gh = {
            str(p_x.get("market_id") or k_x)
            for k_x, p_x in _active_map_gh.items()
            if (p_x.get("status") == "LIQUIDITY_CRISIS" or p_x.get("exit_order_status") == "LIQUIDITY_CRISIS")
            and (float(p_x.get("candle_expiry_ts", 0.0) or 0.0) - _now_gh2) > 120.0
        }
        for tid, p in _active_map_gh.items():
            if position_requires_global_halt(p):
                is_lc_only = (
                    (p.get("status") == "LIQUIDITY_CRISIS" or p.get("exit_order_status") == "LIQUIDITY_CRISIS")
                    and p.get("status") not in (PIPELINE_GLOBAL_HALT_STATUSES - {"LIQUIDITY_CRISIS"})
                    and p.get("exit_order_status") not in (PIPELINE_GLOBAL_HALT_STATUSES - {"LIQUIDITY_CRISIS"})
                )
                if is_lc_only and _iso_lc and len(_lc_mkts_gh) < _req_lc_mkts:
                    continue
                status_val = "LIQUIDITY_CRISIS" if p.get("status") == "LIQUIDITY_CRISIS" else (p.get('exit_order_status') or p.get('status'))
                reasons.append(f"{tid}:{status_val}")
        executor = getattr(self, "executor", None)
        if executor is not None and not self.dry_run and not getattr(executor, "reservations_trusted", True):
            reasons.append("RESERVATIONS_UNTRUSTED")
        if not self.dry_run:
            try:
                from src.polymarket_research.riskless_protocol_v2_expansion import check_harvester_fail_closed_accounting_halt

                reasons.extend(check_harvester_fail_closed_accounting_halt(self, default_state_file=STATE_FILE))
            except Exception:
                reasons.append("ACCOUNTING_INVARIANT_CHECK_FAILED")
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
        _closed_partner = pos.get("_closed_partner_leg")
        _partner_lost_box = bool(
            pos.get("is_dominance_box")
            and isinstance(_closed_partner, dict)
            and float(_closed_partner.get("payout_usd", 0.0) or 0.0) <= 0.01
        )
        _box_floor_val = (
            max(
                float(pos.get("expected_terminal_payout_usd") or pos.get("entry_shares") or 0.0),
                float(pos.get("remaining_cost_basis", pos.get("notional_usd", 0.0)) or 0.0)
                + float(_closed_partner.get("notional_usd", 0.0) or 0.0),
            )
            if _partner_lost_box
            else 0.0
        )
        expiry_ts = float(pos.get("candle_expiry_ts") or 0.0)
        if expiry_ts > 0.0 and now_ts >= expiry_ts:
            if resolved_win is not None and resolved_win == target:
                return float(pos.get("expected_terminal_payout_usd") or pos.get("entry_shares") or 0.0)
            if _partner_lost_box:
                return _box_floor_val
            if resolved_win is None:
                return float(pos.get("remaining_cost_basis", pos.get("notional_usd", 0.0)) or 0.0)
            return 0.0  # Loser expired out of the money

        # 3. Status is unresolved settlement or awaiting settlement:
        if pos.get("status") in {"UNRESOLVED_SETTLEMENT", "AWAITING_ONCHAIN_SETTLEMENT"}:
            if resolved_win is not None and resolved_win == target:
                return float(pos.get("expected_terminal_payout_usd") or pos.get("entry_shares") or 0.0)
            if _partner_lost_box:
                return _box_floor_val
            if resolved_win is None and (pos.get("is_dominance_box") or pos.get("is_single_leg_lock")):
                return float(pos.get("remaining_cost_basis", pos.get("notional_usd", 0.0)) or 0.0)
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
            if v.get("is_dominance_box") or v.get("is_single_leg_lock"):
                continue
            if position_is_settlement_receivable(v):
                continue
            if v.get("status") in {"UNRESOLVED_SETTLEMENT", "AWAITING_ONCHAIN_SETTLEMENT"}:
                continue
            expiry_ts = float(v.get("candle_expiry_ts") or 0.0)
            if expiry_ts > 0.0 and now_ts >= expiry_ts:
                continue
            active[k] = v
        return active

    def _active_box_ids(self) -> Set[str]:
        now_ts = time.time()
        return {
            str(p.get("box_id") or k)
            for k, p in self.active_positions.items()
            if (p.get("is_dominance_box") or p.get("is_single_leg_lock"))
            and not position_is_settlement_receivable(p)
            and p.get("status") not in {"UNRESOLVED_SETTLEMENT", "AWAITING_ONCHAIN_SETTLEMENT"}
            and not (float(p.get("candle_expiry_ts") or 0.0) > 0.0 and now_ts >= float(p.get("candle_expiry_ts") or 0.0))
        }

    def _total_open_portfolio_slots(self) -> int:
        return len(self._active_box_ids()) + len(self._risk_bearing_positions())

    def _preempt_resting_maker_anchors(self, reason: str = "", market_ids: Optional[Set[str]] = None) -> int:
        preempt_map = getattr(self, "_maker_anchor_preempt_events", None) or {}
        if not preempt_map:
            return 0
        reason_map = self.__dict__.setdefault("_maker_anchor_preempt_reasons", {})
        signaled = 0
        for _i_p in list((getattr(self, "pending_entry_intents", None) or {}).values()):
            if not (isinstance(_i_p, dict) and _i_p.get("live_maker_anchor_inflight")):
                continue
            if market_ids is not None and str(_i_p.get("market_id") or "") not in market_ids:
                continue
            _ik = str(_i_p.get("inflight_key") or "")
            _ev_p = preempt_map.get(_ik)
            if _ev_p is not None:
                if reason and _ik not in reason_map:
                    reason_map[_ik] = reason
                _ev_p.set()
                signaled += 1
        return signaled

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

    # Round 9: ONE shared lifecycle engine for startup reconciliation AND live supervision.
    # Every resolver below is the only implementation of its transition, so the two
    # paths can never disagree about what may be submitted (P0-01 / P0-02 / P0-04).
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
        if (
            onchain_bal is not None and onchain_bal == 0.0
            and not any(str(p.get("token_id")) == str(token_id) for p in self.active_positions.values())
            and not any(str(i.get("token_id")) == str(token_id) for i in (getattr(self, "pending_entry_intents", None) or {}).values() if isinstance(i, dict))
        ):
            return 0.0, self.ONCHAIN_SOURCE

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

    def _mark_token_pre_bal_dirty(self, token_id: Optional[str], ttl_sec: float = 3600.0) -> None:
        if not token_id:
            return
        tok_s = str(token_id)
        now_d = time.time()
        dirty = self.__dict__.setdefault("_d1_dirty_token_until", {})
        if len(dirty) > 256:
            for k_old, ts_old in list(dirty.items()):
                if float(ts_old or 0.0) <= now_d:
                    dirty.pop(k_old, None)
        dirty[tok_s] = now_d + float(ttl_sec)
        (self.__dict__.get("_d1_clean_pre_bal_cache") or {}).pop(tok_s, None)

    def _try_fast_clean_zero_pre_bal(self, token_id: Optional[str], exclude_intent_id: str = "") -> Optional[float]:
        if self.dry_run or not token_id:
            return 0.0
        tok_s = str(token_id)
        ex = getattr(self, "executor", None)
        ex_d = getattr(ex, "__dict__", {}) if ex is not None else {}
        is_live_or_forced = bool(getattr(self, "_force_fast_pre_bal_ram", False)) or (
            getattr(ex, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
            and getattr(getattr(ex, "client", None), "_mock_children", None) is None
            and getattr(ex, "_mock_children", None) is None
        )
        has_custom_bal = ("_wallet_token_balance" in self.__dict__) or any(
            k in ex_d for k in ("get_onchain_erc1155_balance", "get_conditional_balance", "get_token_balance")
        )
        if not is_live_or_forced or has_custom_bal:
            return None
        now_pb = time.time()
        dirty = self.__dict__.setdefault("_d1_dirty_token_until", {})
        if float(dirty.get(tok_s, 0.0) or 0.0) > now_pb:
            return None
        uws_pb = getattr(ex, "_user_ws_cache", None)
        if uws_pb is not None and hasattr(uws_pb, "has_token_fill_since") and uws_pb.has_token_fill_since(tok_s, now_pb - 600.0):
            return None
        if any(str(p.get("token_id") or "") == tok_s for p in (getattr(self, "active_positions", None) or {}).values()):
            return None
        if any(
            k != exclude_intent_id and isinstance(i, dict) and str(i.get("token_id") or "") == tok_s
            for k, i in (getattr(self, "pending_entry_intents", None) or {}).items()
        ):
            return None
        if any(
            str(p.get("token_id") or "") == tok_s
            and (float(p.get("remaining_shares", 0.0) or 0.0) > 0.01 or (now_pb - float(p.get("closed_at_ts") or p.get("exit_ts") or 0.0)) < 180.0)
            for p in (getattr(self, "closed_positions", None) or [])[-30:]
        ):
            return None
        (self.__dict__.setdefault("_d1_clean_pre_bal_cache", {}))[tok_s] = (0.0, now_pb)
        return 0.0

    def _resolve_fast_pre_token_balance_sync(self, token_id: Optional[str], exclude_intent_id: str = "") -> float:
        fast_z = self._try_fast_clean_zero_pre_bal(token_id, exclude_intent_id=exclude_intent_id)
        if fast_z is not None:
            return fast_z
        return float((self._wallet_token_balance(token_id))[0] or 0.0)

    async def _resolve_fast_pre_token_balance_async(self, token_id: Optional[str], exclude_intent_id: str = "") -> float:
        fast_z = self._try_fast_clean_zero_pre_bal(token_id, exclude_intent_id=exclude_intent_id)
        if fast_z is not None:
            return fast_z
        return float((await asyncio.to_thread(self._wallet_token_balance, token_id))[0] or 0.0)

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
        from src.polymarket_research.riskless_protocol_v2_expansion import collect_claimed_position_fill_and_order_ids
        c_fids, c_tids, c_buy_oids, c_sell_oids = collect_claimed_position_fill_and_order_ids(self, exclude_tid=exclude_tid)
        known = self._known_fill_ids(exclude_tid) | c_fids
        side_u = str(side or "").upper()
        req_oid = str(order_id or "").strip()
        out = []
        for f in fills:
            if not isinstance(f, dict) or str(f.get("fill_id")) in known:
                continue
            f_oid = str(f.get("order_id") or "").strip()
            tr_id = str(f.get("trade_id") or f.get("id") or "").strip()
            if tr_id and tr_id in c_tids and not (req_oid and f_oid == req_oid):
                continue
            if not req_oid and f_oid:
                if side_u == "SELL" and f_oid in c_sell_oids:
                    continue
                if side_u == "BUY" and f_oid in c_buy_oids:
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
        market_resolved: bool = False,
        condition_id: Optional[str] = None,
        resolution_seen_at_ts: float = 0.0,
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
        now_ts = time.time()
        age = now_ts - float(submitted_ts or 0.0)
        res_age = (now_ts - float(resolution_seen_at_ts)) if float(resolution_seen_at_ts or 0.0) > 0.0 else age

        def _resolved_purged_zero_fill(nc_reason_raw: Any, matched_qty: float, assoc_trades: Any) -> bool:
            if not market_resolved or matched_qty > 1e-4 or bool(assoc_trades):
                return False
            if evidence is None or evidence.get("fills") or src != self.ONCHAIN_SOURCE:
                return False
            if age < ENTRY_UNEXECUTED_PROOF_AGE_S or res_age < 15.0:
                return False
            nc_r = str(nc_reason_raw or "").lower()
            if not any(p in nc_r for p in ("can't be found", "cannot be found", "already canceled", "already cancelled", "market is closed")):
                return False
            if condition_id and hasattr(self.executor, "redemption_payouts"):
                try:
                    rp = self.executor.redemption_payouts(str(condition_id), float(submitted_ts or 0.0))
                except Exception:
                    return False
                if rp is None or len(rp) > 0:
                    return False
            return True

        if entry_order_id:
            try:
                info = self.executor.get_order_status(str(entry_order_id))
            except Exception:
                info = None
            if isinstance(info, dict):
                st = str(info.get("status", "")).upper()
                matched = self._num(info.get("size_matched")) or 0.0
                if st in {"LIVE", "OPEN", "RESTING", "DELAYED"}:
                    try:
                        c_res = self.executor.cancel_order(str(entry_order_id))
                    except Exception:
                        c_res = {}
                    if not (c_res or {}).get("is_canceled"):
                        if _resolved_purged_zero_fill((c_res or {}).get("not_canceled_reason"), matched, info.get("associate_trades")):
                            self.executor.release_inventory(reservation_id=str(entry_order_id))
                            out["verdict"] = "NOT_EXECUTED"
                            out["proof"] = "RESOLVED_MARKET_PURGED_ORDER_ZERO_FILL"
                        return out
                    try:
                        info = self.executor.get_order_status(str(entry_order_id)) or info
                    except Exception:
                        pass
                    st = str(info.get("status", "")).upper()
                    matched = max(matched, self._num((c_res or {}).get("matched")) or 0.0, self._num(info.get("size_matched")) or 0.0)
                    if matched > 1e-4:
                        out["verdict"] = "MATCHED_UNSETTLED"
                        return out
                    if (c_res or {}).get("is_canceled") and matched <= 1e-4:
                        out["verdict"] = "NOT_EXECUTED"
                        out["proof"] = "RESTING_ENTRY_CANCELED_ZERO_FILL"
                        return out
                if (st.startswith("CANCEL") or st in {"EXPIRED", "REJECTED", "INVALID"}) and matched <= 1e-4:
                    out["verdict"] = "NOT_EXECUTED"
                    out["proof"] = "TERMINAL_ZERO_FILL_ORDER_STATUS"
                    return out
        if (
            evidence is not None and not evidence["fills"]
            and src in (self.ONCHAIN_SOURCE, "CLOB_BALANCE_API") and (age >= ENTRY_UNEXECUTED_PROOF_AGE_S or market_resolved)
        ):
            if hasattr(self.executor, "get_open_orders"):
                try:
                    open_os = self.executor.get_open_orders(strict=True)
                except TypeError:
                    open_os = self.executor.get_open_orders()
                except Exception:
                    open_os = None
                if not isinstance(open_os, list):
                    if market_resolved and src == self.ONCHAIN_SOURCE:
                        out["verdict"] = "NOT_EXECUTED"
                        out["proof"] = "RESOLVED_MARKET_ONCHAIN_ZERO_AND_NO_FILLS"
                        return out
                    # Fail closed: cannot prove no resting BUY is still live on the book.
                    return out
                if isinstance(open_os, list):
                    for o_b in open_os:
                        if str((o_b or {}).get("asset_id") or (o_b or {}).get("token_id") or "") == str(token_id) and str((o_b or {}).get("side") or "").upper() == "BUY":
                            o_bid = str((o_b or {}).get("id") or (o_b or {}).get("orderID") or "")
                            if o_bid:
                                try:
                                    c_b = self.executor.cancel_order(o_bid)
                                except Exception:
                                    c_b = {}
                                _b_matched = max(self._num((c_b or {}).get("matched")) or 0.0, self._num((o_b or {}).get("size_matched")) or 0.0)
                                if not (c_b or {}).get("is_canceled") or _b_matched > 1e-4:
                                    if not _resolved_purged_zero_fill((c_b or {}).get("not_canceled_reason"), _b_matched, (o_b or {}).get("associate_trades")):
                                        return out
                                    self.executor.release_inventory(reservation_id=o_bid)
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
            if float(pos.get("notional_usd", 0.0) or 0.0) <= 0.0 and net > 0:
                est_px = float(pos.get("entry_price") or pos.get("target_price") or 0.70)
                pos["notional_usd"] = round(net * est_px, 4)
                pos["cost_basis_estimated"] = True
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
            if st in {"CONFIRMED", "MINED"}:
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

    def _consolidate_dominance_box_close(
        self, tid: str, pos: Dict[str, Any], cum_cash: float, cum_fee: float, net_pnl: float, reason: str, record_pnl: bool
    ) -> Tuple[bool, float]:
        from src.polymarket_research.riskless_protocol_v2_expansion import consolidate_any_box_leg_close
        return consolidate_any_box_leg_close(self, tid, pos, cum_cash, cum_fee, net_pnl, reason, record_pnl)

    def _close_position(self, tid: str, pos: Dict[str, Any], status: str, reason: str,
                        won: Optional[bool] = None, record_pnl: bool = True) -> Optional[float]:
        """Single closeout: realized cash PnL strictly from recorded exchange fills/receipts."""
        # Round 11 P0-12 Fix: Every closeout must require estimated_exit_cash == 0,
        # exit_cash_estimated is False, and authoritative confirmation.
        # Synthetic or estimated proceeds must NEVER be settled into realized PnL,
        # EXCEPT for confirmed market resolution losses where terminal payout is definitively $0.00.
        is_terminal_loss = (
            reason in {"MARKET_RESOLVED_LOSS", "EXPIRED_OUT_OF_MONEY"}
            or pos.get("pending_settlement_close_reason") in {"MARKET_RESOLVED_LOSS", "EXPIRED_OUT_OF_MONEY"}
            or (pos.get("close_reason") and "MARKET_RESOLVED_LOSS" in str(pos.get("close_reason")))
        )
        has_partial_exit_fills = float(pos.get("filled_exit_shares", 0.0) or 0.0) > 0.01
        if is_terminal_loss and not has_partial_exit_fills:
            pos["exit_cash_estimated"] = False
            pos["estimated_exit_cash"] = 0.0

        est_cash = float(pos.get("estimated_exit_cash", 0.0) or 0.0)
        if (not is_terminal_loss or has_partial_exit_fills) and (est_cash > 0.0 or pos.get("exit_cash_estimated", False)):
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

        if (
            not getattr(self, "dry_run", True)
            and not bool(pos.get("inventory_reconciled"))
            and (
                str(pos.get("status") or "") in {"ENTRY_OUTCOME_UNKNOWN", "NOT_EXECUTED"}
                or str(pos.get("exit_order_status") or "") == "ENTRY_OUTCOME_UNKNOWN"
            )
            and not (pos.get("trade_ids") or pos.get("transactions_hashes"))
            and float(pos.get("filled_exit_shares", 0.0) or 0.0) < 0.01
            and float(pos.get("confirmed_realized_cash", pos.get("realized_exit_cash", 0.0)) or 0.0) <= 0.0
        ):
            status = "NOT_EXECUTED"
            if status != reason and "NOT_EXECUTED" not in str(reason or "").upper() and "UNFILLED" not in str(reason or "").upper():
                reason = (
                    "UNFILLED_MAKER_EXPIRED_NO_FILL"
                    if "MAKER" in str(pos.get("box_type") or pos.get("fee_source") or "").upper()
                    else "ENTRY_NOT_EXECUTED_AT_RESOLUTION"
                )
            won = False
            record_pnl = False
            pos["entry_shares"] = 0.0
            pos["notional_usd"] = 0.0
            pos["remaining_cost_basis"] = 0.0
            pos["fee_usd"] = 0.0
            pos["entry_fee_cash_usd"] = 0.0

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
        _closed_ts = time.time()
        pos.setdefault("opened_at_ts", float(pos.get("entry_ts") or _closed_ts))
        pos["closed_at_ts"] = _closed_ts
        pos["exit_ts"] = _closed_ts
        pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
        pos["won"] = (net_pnl > 0.0) if won is None else won
        pos["payout_usd"] = round(cum_cash, 4)
        pos["net_pnl_usd"] = round(net_pnl, 4)
        pos["close_reason"] = reason
        if filled > 0.0:
            pos["average_exit_price"] = round(cum_cash / filled, 4)
        pos["remaining_shares"] = 0.0
        pos["remaining_exit_shares"] = 0.0
        pos["is_liquidating"] = False
        r_up = str(reason or "").upper()
        if status == "NOT_EXECUTED":
            pos["exit_decomposition_bucket"] = "NOT_EXECUTED"
        elif "MAKER_SCALP" in r_up or "MAKER_RECYCLE" in r_up or "FILLED_OFFLINE" in r_up:
            pos["exit_decomposition_bucket"] = "MAKER_SCALP"
            if not getattr(self, "dry_run", True) and _STAGE_B_MARKOUT_SAMPLER is not None and filled > 0.01 and cum_cash > 0.0 and token_id and hasattr(self.executor, "get_market_book"):
                try:
                    _m_ws_ex = getattr(self, "_pos_market_ws", None)
                    _STAGE_B_MARKOUT_SAMPLER.schedule_maker_fill(
                        order_id=str(pos.get("exit_order_id") or tid), token_id=str(token_id),
                        sleeve=str(pos.get("sleeve") or pos.get("sleeve_source") or "MAKER_EXIT"), side="SELL",
                        fill_px=round(cum_cash / filled, 6), shares=filled,
                        book_lookup_fn=lambda _t: (_m_ws_ex.get_book(str(_t), max_age_sec=5.0) if _m_ws_ex is not None else None) or self.executor.get_market_book(str(_t)),
                    )
                except Exception:
                    pass
        elif "RATCHET" in r_up or "RECYCLE" in r_up:
            pos["exit_decomposition_bucket"] = "PROFIT_RATCHET"
        elif "STOP" in r_up or "UNWIND" in r_up or "SALVAGE" in r_up:
            pos["exit_decomposition_bucket"] = "SALVAGE_UNWIND"
        elif "AUTOREDEEM" in r_up:
            pos["exit_decomposition_bucket"] = "TERMINAL_HOLD_WIN"
        elif "REDEMPTION" in r_up or (pos.get("won") and "RESOLVED" in r_up):
            pos["exit_decomposition_bucket"] = "TERMINAL_SETTLEMENT"
        elif pos.get("won") and net_pnl > 0.0:
            pos["exit_decomposition_bucket"] = "PROFIT_RATCHET"
        else:
            pos["exit_decomposition_bucket"] = "TERMINAL_LOSS"
        m_id_closed = str(pos.get("market_id") or "")
        pos["entry_sequence_in_market"] = int((getattr(self, "trades_per_market", None) or {}).get(m_id_closed, 1) or 1)
        pos["is_win_reset_second_entry"] = bool(pos["entry_sequence_in_market"] >= 2)
        leg_net_cash = max(0.0, float(cum_cash or 0.0) - float(cum_fee or 0.0))
        unsynced_leg_net_cash = max(0.0, leg_net_cash - float(pos.get("_synced_exit_cash_usd", 0.0) or 0.0))
        _unres_seq = pos.get("_unresolved_settle_seq")
        _already_synced_in_collat = (
            _unres_seq is not None and int(getattr(self, "_collateral_sync_seq", 0) or 0) > int(_unres_seq)
        )
        if (
            not getattr(self, "dry_run", True)
            and getattr(self, "_last_known_collateral", None) is not None
            and unsynced_leg_net_cash > 0.0
            and not pos.get("_collateral_exit_credited")
            and not _already_synced_in_collat
        ):
            pos["_collateral_exit_credited"] = True
            self._last_known_collateral = float(self._last_known_collateral) + unsynced_leg_net_cash
            self._last_exit_credit_window = (time.time(), float(self._last_known_collateral))
        deferred_partner, net_pnl = self._consolidate_dominance_box_close(
            tid, pos, cum_cash, cum_fee, net_pnl, reason, record_pnl
        )
        if deferred_partner:
            try:
                asyncio.get_running_loop().create_task(self._async_refresh_collateral())
            except RuntimeError:
                pass
            return net_pnl
        self.closed_positions.append(pos)
        if record_pnl:
            _is_nd = bool(
                pos.get("is_dominance_box")
                or pos.get("is_single_leg_lock")
                or pos.get("is_legged_out_residual")
                or "BOX" in str(pos.get("sleeve") or "").upper()
            )
            self.risk_controller.record_trade_pnl(net_pnl, is_non_directional=_is_nd)
        self.active_positions.pop(tid, None)
        from src.polymarket_research.riskless_protocol_v2_expansion import clear_d1_dedupe_on_close
        clear_d1_dedupe_on_close(self, pos)
        collat_after = getattr(self, "_last_known_collateral", None)
        if not getattr(self, "dry_run", True) and isinstance(collat_after, (int, float)) and math.isfinite(collat_after) and collat_after > 0.0:
            now_close_ts = time.time()
            rem_mkt_eq = sum(self.get_position_market_value(p, now_close_ts) for p in self.active_positions.values())
            sizing_eq_close, _ = self._effective_sizing_equity_usd(float(collat_after) + rem_mkt_eq, now_close_ts)
            self._update_equity_tier(sizing_eq_close, allow_hwm_ratchet=False)
        self.save_state()
        self._pending_collateral_refresh = True
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_refresh_collateral())
        except RuntimeError:
            pass
        _pnl_fmt = f"{net_pnl:+.4f}" if 0.0 < abs(net_pnl) < 0.01 else f"{net_pnl:+.2f}"
        logger.info(f"[CLOSED] {tid} | {reason} | Payout=${cum_cash:.2f} | Net PnL=${_pnl_fmt}")
        return net_pnl

    @staticmethod
    def _estimated_taker_fee(shares: float, cash: float, fee_rate: float = 0.07, fee_exponent: float = 1.0) -> float:
        if shares <= 0.0:
            return 0.0
        px = min(0.999, max(0.001, cash / shares))
        return round(shares * fee_rate * ((px * (1.0 - px)) ** max(1.0, float(fee_exponent))), 5)

    def _exit_taker_fee_rate(self, pos: Dict[str, Any]) -> float:
        from src.polymarket_research.riskless_machine_gun_engine import resolve_authoritative_exit_fee_rate
        return resolve_authoritative_exit_fee_rate(getattr(self, "executor", None), pos)

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
            if matched > 0.0:
                is_est = True
                pos["exit_cash_estimated"] = True
        elif summary.get("cash_is_estimated") and matched > 0.0:
            is_est = True
            pos["exit_cash_estimated"] = True

        if matched <= 1e-6 and float(pos.get("estimated_exit_cash", 0.0) or 0.0) <= 1e-6:
            has_other_est = any(
                isinstance(v, dict) and v.get("cash_is_estimated") and float(v.get("matched", 0.0) or 0.0) > 1e-6
                for k, v in (pos.get("order_records") or {}).items()
                if str(k) != oid
            )
            if not has_other_est and pos.get("exit_cash_estimated"):
                pos["exit_cash_estimated"] = False

        # Round 11 P0-11: Do NOT return early if matched shares haven't changed but cash has transitioned
        # from estimated to confirmed, or if authoritative cumulative fills arrived with updated cash.
        has_new_shares = (matched > prior + 1e-6)
        has_cash_confirmation = prior_is_estimated and (not is_est)
        prior_cash = float(prior_rec.get("cash", 0.0) or 0.0)
        has_cash_correction = (abs(float(cash) - prior_cash) > 1e-6) and (not is_est)

        if not (has_new_shares or has_cash_confirmation or has_cash_correction):
            return False

        applied_r = self._exit_taker_fee_rate(pos)
        applied_e = float(pos.get("fee_exponent_applied") or 1.0)
        charge_est_fee = bool(taker and not summary.get("cash_from_reported_taking"))
        fee = self._estimated_taker_fee(matched, float(cash), fee_rate=applied_r, fee_exponent=applied_e) if charge_est_fee else 0.0
        if charge_est_fee:
            pos["exit_fee_estimated"] = True
        rec_meta = self.record_fill_and_update_position(pos, oid, matched, float(cash), fee, cash_is_estimated=is_est)
        if isinstance(rec_meta, dict):
            rec_meta["is_taker"] = bool(taker)
            rec_meta["fallback_price"] = float(fallback_px or 0.0)
        ids = set(pos.get("exit_trade_ids") or []) | set(summary.get("trade_ids") or [])
        pos["exit_trade_ids"] = sorted(str(i) for i in ids)
        f_ids = set(pos.get("exit_fill_ids") or []) | set(summary.get("fill_ids") or [])
        pos["exit_fill_ids"] = sorted(str(i) for i in f_ids)

        # Round 10 P1-03: Refresh reservation for this order ID (remaining = original - matched)
        orig_sz = float(summary.get("original_size", 0.0) or pos.get("exit_order_size", pos.get("entry_shares", 0.0)) or 0.0)
        remaining_commit = max(0.0, orig_sz - matched)
        if summary.get("terminal") or remaining_commit <= 0.0:
            self.executor.release_inventory(reservation_id=oid)
        else:
            self.executor.update_reservation(oid, remaining_commit)
        return True

    def _record_history_fills(self, pos: Dict[str, Any], fills: List[Dict[str, Any]], taker: bool) -> int:
        """Books exchange-history SELL fills grouped by order id; returns number of fills booked."""
        from src.polymarket_research.riskless_protocol_v2_expansion import filter_unclaimed_position_fills
        fills = filter_unclaimed_position_fills(
            self, pos, fills, side="SELL", exclude_tid=str(pos.get("trade_id") or "")
        )
        if not fills:
            return 0
        by_order: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for f in fills:
            by_order[str(f.get("order_id") or f.get("fill_id"))].append(f)
        booked = 0
        applied_r = self._exit_taker_fee_rate(pos)
        applied_e = float(pos.get("fee_exponent_applied") or 1.0)
        entry_sh_cap = float(pos.get("entry_shares") or 0.0)
        booked_fills: List[Dict[str, Any]] = []
        for oid, group in by_order.items():
            prior = (pos.get("order_records") or {}).get(oid) or {}
            # AUDIT-13-06 Fix: If prior record was an unconfirmed estimate, replace rather than double-count
            base_shares = 0.0 if prior.get("cash_is_estimated") else float(prior.get("matched", 0.0) or 0.0)
            base_cash = 0.0 if prior.get("cash_is_estimated") else float(prior.get("cash", 0.0) or 0.0)
            base_fee = 0.0 if prior.get("cash_is_estimated") else float(prior.get("fee", 0.0) or 0.0)
            g_sh = sum(self._num(f.get("size")) or 0.0 for f in group)
            g_cash = sum(self._num(f.get("cash")) or 0.0 for f in group)
            shares = base_shares + g_sh
            cash = base_cash + g_cash
            if entry_sh_cap > 0.0:
                other_sh = sum(
                    float((v or {}).get("matched", 0.0) or 0.0)
                    for k, v in (pos.get("order_records") or {}).items()
                    if str(k) != oid and isinstance(v, dict)
                )
                max_oid_sh = max(0.0, entry_sh_cap - other_sh)
                if shares > max_oid_sh + 0.02:
                    if max_oid_sh <= 1e-6:
                        continue
                    cash = cash * (max_oid_sh / shares)
                    g_sh = max(0.0, max_oid_sh - base_shares)
                    g_cash = max(0.0, cash - base_cash)
                    shares = max_oid_sh
            fee = base_fee + (self._estimated_taker_fee(g_sh, g_cash, fee_rate=applied_r, fee_exponent=applied_e) if taker else 0.0)
            group_settled = all(
                bool(f.get("transaction_hash")) and str(f.get("status", "")).upper() in {"MINED", "CONFIRMED"}
                for f in group
            )
            rec_meta = self.record_fill_and_update_position(
                pos, oid, shares, cash, fee, cash_is_estimated=(not group_settled and not self.dry_run)
            )
            if isinstance(rec_meta, dict):
                rec_meta["is_taker"] = bool(taker)
            booked += len(group)
            booked_fills.extend(group)
        if booked_fills:
            pos["exit_fill_ids"] = sorted(set(pos.get("exit_fill_ids") or []) | {str(f.get("fill_id")) for f in booked_fills if f.get("fill_id")})
            pos["exit_trade_ids"] = sorted(set(pos.get("exit_trade_ids") or []) | {str(f.get("trade_id")) for f in booked_fills if f.get("trade_id")})
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
        exp_ts_rec = float(pos.get("candle_expiry_ts", 0.0) or 0.0)
        if exp_ts_rec > 0.0 and time.time() >= exp_ts_rec:
            pos["exit_order_status"] = "DETERMINISTIC_TERMINAL_HOLD"
            pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
            pos["next_unwind_retry_ts"] = 0.0
            self.save_state()
            return
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
        c_mkr_oids = [str(x) for x in (pos.get("canceled_maker_exit_oids") or []) if x]
        c_mkr_set = set(c_mkr_oids)
        for c_oid in c_mkr_oids:
            c_sum = self.executor.get_order_fill_summary(c_oid, token_id)
            if c_sum is not None and float(c_sum.get("matched") or 0.0) > 0.0:
                self._record_order_summary(pos, c_sum, float(pos.get("target_exit_price", 0.98) or 0.98), taker=False)
                if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
                    self._after_unwind_reconciled(tid, pos, "MAKER_SCALP_FILLED_CLOB")
                    return True
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
        ord_recs = pos.get("order_records") or {}
        exclude_orders = {
            str(k)
            for k, v in ord_recs.items()
            if str(k) not in c_mkr_set or (isinstance(v, dict) and not v.get("cash_is_estimated") and float(v.get("matched") or 0.0) > 0.0)
        }
        if pos.get("exit_order_id"):
            exclude_orders.add(str(pos["exit_order_id"]))
        fills_since_ts = min(attempt_ts, float(pos.get("entry_ts") or attempt_ts)) - 5.0 if c_mkr_set else (attempt_ts - 5.0)
        fills = self._fetch_account_fills(token_id, fills_since_ts, "SELL", exclude_tid=tid)
        if fills is None:
            return False
        fills = [f for f in fills if str(f.get("order_id")) not in exclude_orders]
        if fills:
            mkr_fills = [f for f in fills if str(f.get("order_id")) in c_mkr_set]
            tkr_fills = [f for f in fills if str(f.get("order_id")) not in c_mkr_set]
            if mkr_fills:
                self._record_history_fills(pos, mkr_fills, taker=False)
            if tkr_fills:
                self._record_history_fills(pos, tkr_fills, taker=True)
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
            market_resolved=bool(pos.get("resolved_winning_outcome") is not None),
            condition_id=pos.get("condition_id"),
            resolution_seen_at_ts=float(pos.get("resolution_seen_at_ts") or 0.0),
        )
        verdict = cls["verdict"]
        p_tid = str(pos.get("box_partner_trade_id") or "")
        if verdict in {"ARRIVED", "MATCHED_UNSETTLED"}:
            self._apply_entry_evidence(pos, cls)
            if pos.get("is_single_leg_lock") and float(pos.get("entry_shares") or 0.0) > 0.0:
                _tot_c = round(float(pos.get("notional_usd") or 0.0) + float(pos.get("fee_usd") or 0.0), 4)
                pos["box_total_cost_usd"] = _tot_c
                pos["box_cost_net"] = round(_tot_c / float(pos["entry_shares"]), 6)
            partner_dead = bool(
                p_tid
                and p_tid not in self.active_positions
                and any(c.get("trade_id") == p_tid and c.get("status") == "NOT_EXECUTED" for c in self.closed_positions)
            )
            if partner_dead:
                pos["is_dominance_box"] = False
                pos["is_legged_out_residual"] = True
                pos["pending_unwind_tag"] = "D1_LEGGED_OUT_RESIDUAL_UNWIND"
                pos["status"] = ExecutionStatus.POSITION_CONFIRMED if verdict == "ARRIVED" else ExecutionStatus.MATCHED_PENDING_SETTLEMENT
                pos["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
                pos["stop_triggered_ts"] = time.time()
                pos["next_unwind_retry_ts"] = 0.0
            else:
                pos["status"] = ExecutionStatus.POSITION_CONFIRMED if verdict == "ARRIVED" else ExecutionStatus.MATCHED_PENDING_SETTLEMENT
                pos["exit_order_status"] = "DETERMINISTIC_TERMINAL_HOLD" if pos.get("hold_to_maturity_lock") else "AWAITING_DELTA_SETTLEMENT"
            self.save_state()
            logger.warning(f"[ENTRY RECONCILED] {tid}: {verdict} ({pos.get('entry_finality_source')}, shares={pos.get('entry_shares')}).")
            return True
        if verdict == "NOT_EXECUTED":
            pos["entry_shares"] = 0.0
            pos["notional_usd"] = 0.0
            pos["non_execution_proof"] = cls.get("proof")
            partner = self.active_positions.get(p_tid) if p_tid else None
            if isinstance(partner, dict) and partner.get("is_dominance_box"):
                partner["is_dominance_box"] = False
                partner["is_legged_out_residual"] = True
                partner["pending_unwind_tag"] = "D1_LEGGED_OUT_RESIDUAL_UNWIND"
                if partner.get("status") != "ENTRY_OUTCOME_UNKNOWN":
                    partner["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
                    partner["stop_triggered_ts"] = time.time()
                    partner["next_unwind_retry_ts"] = 0.0
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

    def _exit_fill_settled_onchain(self, pos: Dict[str, Any], summary: Dict[str, Any]) -> bool:
        """
        True when a fully MATCHED maker-exit SELL is provably settled on-chain even though CLOB `/trades`
        under-reports its fills (e.g. 2 associate trades, 1 returned). The executor's own fallback requires
        the wallet balance to drop to ~0, which never holds for a partial-tranche TP (the position's other
        shares remain in the wallet). Here we compare against THIS position's recorded remaining shares.
        """
        try:
            st = str(summary.get("status") or "").upper()
            orig = float(summary.get("original_size") or 0.0)
            matched = float(summary.get("matched") or 0.0)
            is_full_match = st in {"MATCHED", "FILLED", "CONFIRMED", "MINED"} and orig > 0.0 and matched >= orig - 0.01
            is_partial_cancel = (st.startswith("CANCEL") or st in {"EXPIRED"}) and matched > 0.01
            if (
                self.dry_run
                or summary.get("resting")
                or summary.get("has_reverted_fills")
                or not (is_full_match or is_partial_cancel)
                or str((summary.get("raw") or {}).get("side") or "SELL").upper() != "SELL"
                or not hasattr(self.executor, "get_onchain_erc1155_balance")
            ):
                return False
            tok = str(pos.get("token_id") or "")
            if not tok:
                return False
            bal = self.executor.get_onchain_erc1155_balance(tok)
            if not isinstance(bal, (int, float)) or isinstance(bal, bool) or not math.isfinite(float(bal)):
                return False
            rem = float(pos.get("remaining_shares", 0.0) or 0.0)
            ok = float(bal) <= rem + 0.011
            if ok:
                logger.info(
                    f"[FILL RECONCILED ON-CHAIN] {summary.get('order_id')}: MATCHED {matched:.2f}/{orig:.2f}; wallet "
                    f"{float(bal):.4f} <= position remaining {rem:.4f} -> exit fill final."
                )
            return ok
        except Exception as e:
            logger.debug(f"On-chain exit settlement check skipped: {e}")
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
        if not summary["terminal"] and is_exit and self._exit_fill_settled_onchain(pos, summary):
            summary = {**summary, "terminal": True}
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
                lc_exit_oid = pos.get("exit_order_id")
                if lc_exit_oid and token_id and hasattr(self.executor, "get_order_fill_summary"):
                    lc_sum = self.executor.get_order_fill_summary(str(lc_exit_oid), token_id)
                    if lc_sum is not None:
                        self._record_order_summary(pos, lc_sum, float(pos.get("target_exit_price", 0.98) or 0.98), taker=False)
                        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.02:
                            self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                            return True
                expiry_ts = float(pos.get("candle_expiry_ts", 0.0) or 0.0)
                book_closed = (expiry_ts > 0.0 and now >= expiry_ts)
                book = {}
                if token_id and not book_closed:
                    try:
                        book = self.executor.get_market_book(token_id)
                    except Exception as bk_err:
                        if "404" in str(bk_err) or "no orderbook exists" in str(bk_err).lower():
                            book_closed = True
                        else:
                            raise
                bids = [b for b in (book.get("bids") or []) if float(b.get("price", 0.0)) > 0 and float(b.get("size", 0.0)) > 0]
                asks = [a for a in (book.get("asks") or []) if float(a.get("price", 0.0)) > 0 and float(a.get("size", 0.0)) > 0]
                best_b = max((float(b["price"]) for b in bids), default=0.0)
                best_a = min((float(a["price"]) for a in asks), default=1.0)
                if book_closed or (best_b > 0.0 and (not asks or best_b < best_a)):
                    pos["status"] = ExecutionStatus.EXIT_RESTING if pos.get("exit_order_id") else ExecutionStatus.POSITION_CONFIRMED
                    pos["exit_order_status"] = "RESTING" if pos.get("exit_order_id") else ("CANCELED_FOR_EXPIRY_HOLD" if book_closed else "EXIT_RECOVERY_REQUIRED")
                    pos.pop("liquidity_crisis_ts", None)
                    pos.pop("zero_bid_detected_ts", None)
                    self.save_state()
                    logger.info(f"[LIQUIDITY_CRISIS_RESOLVED] {tid}: {'Market expired/closed' if book_closed else f'Valid bid restored (${best_b:.4f})'}. Resuming.")
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
        if exit_res.get("crossed_at_max_tick"):
            pos["next_exit_post_ts"] = now + 1.0
            pos["exit_order_status"] = "CROSSED_AT_MAX_TICK_WAIT"
            return False
        failures = int(pos.get("exit_post_failures", 0) or 0) + 1
        pos["exit_post_failures"] = failures
        err_txt = str(exit_res.get("error") or "").lower()
        entry_age = now - float(pos.get("entry_ts", 0.0) or 0.0)
        if ("not enough balance" in err_txt or "insufficient_unreserved_balance" in err_txt) and 0.0 <= entry_age < 15.0:
            pos["next_exit_post_ts"] = now + 0.40
            pos["exit_order_status"] = "AWAITING_DELTA_SETTLEMENT"
            logger.info(f"Maker exit post awaiting CLOB balance indexer sync for {pos.get('trade_id')} (age={entry_age:.2f}s); retry in 0.40s.")
            return False
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
        if pos.get("queue_jumped") or pos.get("is_dominance_box") or pos.get("is_single_leg_lock"):
            return
        tgt = float(pos.get("target_exit_price") or 0.0)
        if tgt < QUEUE_JUMP_MIN_TARGET or (self._effective_exit_policy() == "hold_98" and tgt <= 0.98):
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
        uws = getattr(self.executor, "_user_ws_cache", None)
        while time.time() < deadline:
            prev_seq = uws.fill_sequence if uws is not None else None
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
                if position_requires_lifecycle_resolution(pos):
                    return False
            if uws is not None and uws.is_healthy():
                await uws.wait_for_fill_or_timeout(FAST_CONFIRM_POLL_SEC, prev_seq=prev_seq)
            else:
                await asyncio.sleep(FAST_CONFIRM_POLL_SEC)
        return False

    def _spawn_fast_confirm(self, trade_id: str) -> None:
        inflight = self.__dict__.setdefault("_fast_confirm_inflight_ids", set())
        if trade_id in inflight:
            return
        try:
            loop = asyncio.get_running_loop()
            self._main_loop = loop
        except RuntimeError:
            main_loop = getattr(self, "_main_loop", None)
            if main_loop is not None and main_loop.is_running():
                try:
                    main_loop.call_soon_threadsafe(self._spawn_fast_confirm, trade_id)
                except RuntimeError:
                    pass
            return
        inflight.add(trade_id)
        task = loop.create_task(self._fast_confirm_and_post_maker_exit(trade_id))
        tasks = self.__dict__.setdefault("_fast_confirm_tasks", set())
        tasks.add(task)
        task.add_done_callback(lambda t: (tasks.discard(t), inflight.discard(trade_id)))

    def _attempt_maker_exit_post_impl(self, tid: str, pos: Dict[str, Any]) -> bool:
        """
        The ONLY path that submits a new maker exit (startup recovery and live supervision).
        Requires: allowlisted lifecycle state, outside the pre-expiry window, authoritative entry
        finality (trade/tx evidence or verified on-chain inventory) and wallet inventory covering
        the remaining shares. Returns True if an order was posted.
        """
        now = time.time()
        expiry = float(pos.get("candle_expiry_ts", now + 600.0) or (now + 600.0))
        eff_cancel_win = 5.0 if pos.get("sleeve") == "SLEEVE_4_BOUNDARY_SNIPE" else self.tte_cancel_window
        if not position_may_post_new_maker_exit(pos) or (expiry - now) < eff_cancel_win:
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
                        pos["target_exit_price"] = float(pos.get("custom_maker_exit_price") or 0.99) if (pos.get("is_dominance_box") or pos.get("is_single_leg_lock")) else self._calculate_target_exit(true_cost_per_share, expiry - now)
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
                min_valid_received = Decimal("0.01")
                if received > gross + d_eps + Decimal("0.01"):
                    entry_oid_up = str(pos.get("entry_order_id") or pos.get("order_id") or "").strip()
                    if entry_oid_up and hasattr(self.executor, "get_order_fill_summary"):
                        try:
                            up_sum = self.executor.get_order_fill_summary(entry_oid_up, token_id)
                            up_m = Decimal(str((up_sum or {}).get("matched") or 0.0))
                            if up_m >= received - Decimal("0.05"):
                                gross = up_m
                                pos["gross_entry_shares"] = float(up_m)
                                up_px = float((up_sum or {}).get("avg_price") or (up_sum or {}).get("limit_price") or pos.get("entry_price") or 0.0)
                                if up_px > 0.0:
                                    pos["entry_price"] = up_px
                                pos["notional_usd"] = round(float((up_sum or {}).get("cash") or (float(up_m) * max(up_px, 0.01))), 4)
                        except Exception:
                            pass
                if received < min_valid_received or received > gross + d_eps + Decimal("0.01"):
                    pos["exit_blocked_reason"] = f"ENTRY_INVENTORY_UNRECONCILED(received={received}, gross={gross})"
                    pos["next_exit_post_ts"] = now + self._settlement_recheck_delay(pos, now)
                    self.save_state()
                    return False
                net = float(min(received, gross).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                if gross > Decimal("0") and received < gross - Decimal("0.02"):
                    # v3.9 R02 / Patch B: Verify against authoritative CLOB fill summary before altering ledger!
                    # On Polymarket V2 (0xE111...), BUY fees are charged in pUSD cash and 100% of gross shares settle.
                    entry_oid = str(pos.get("entry_order_id") or pos.get("order_id") or "").strip()
                    clob_entry_sum = None
                    if entry_oid and hasattr(self.executor, "get_order_fill_summary"):
                        try:
                            raw_es = self.executor.get_order_fill_summary(entry_oid, token_id)
                            if isinstance(raw_es, dict) and float(raw_es.get("matched") or 0.0) > 0.0:
                                clob_entry_sum = raw_es
                        except Exception:
                            clob_entry_sum = None
                    entry_age_s = max(0.0, now - float(pos.get("entry_ts") or now))
                    if clob_entry_sum is not None:
                        clob_m = Decimal(str(clob_entry_sum["matched"]))
                        exp_settled_m = (
                            min(clob_m, Decimal(str(pos.get("entry_shares") or clob_m)))
                            if str(pos.get("entry_fee_asset") or "").upper() == "SHARES"
                            else clob_m
                        )
                        if received + Decimal("0.05") < exp_settled_m:
                            if entry_age_s < 18.0:
                                pos["exit_blocked_reason"] = f"PARTIAL_BATCH_SETTLING(wallet={received}, clob={clob_m})"
                                pos["next_exit_post_ts"] = now + self._settlement_recheck_delay(pos, now)
                            else:
                                pos["exit_blocked_reason"] = f"ENTRY_INVENTORY_RECONCILIATION_REQUIRED(wallet={received}, clob={clob_m})"
                                pos["exit_order_status"] = "ENTRY_INVENTORY_RECONCILIATION_REQUIRED"
                            self.save_state()
                            return False
                        if clob_m < gross * Decimal("0.98"):
                            orig_notional = float(pos.get("notional_usd", 0.0) or 0.0)
                            pos.setdefault("intended_notional", orig_notional)
                            auth_cash = float(clob_entry_sum.get("cash") or 0.0)
                            fill_ratio = float(clob_m / gross)
                            pos["notional_usd"] = round(auth_cash if auth_cash > 0.0 else (orig_notional * fill_ratio), 4)
                            pos["fee_usd"] = round(float(clob_entry_sum.get("fee") or (float(pos.get("fee_usd", 0.0) or 0.0) * fill_ratio)), 4)
                    elif entry_oid:
                        if entry_age_s < 15.0:
                            pos["exit_blocked_reason"] = f"ENTRY_SETTLEMENT_PENDING(wallet={received}, gross={gross})"
                            pos["next_exit_post_ts"] = now + self._settlement_recheck_delay(pos, now)
                        else:
                            pos["exit_blocked_reason"] = f"ENTRY_INVENTORY_RECONCILIATION_REQUIRED(wallet={received}, gross={gross})"
                            pos["exit_order_status"] = "ENTRY_INVENTORY_RECONCILIATION_REQUIRED"
                        self.save_state()
                        return False
                    elif received < gross * Decimal("0.92"):
                        # Partial FAK fill on orderless/synthetic record: scale booked notional & fee proportionally
                        fill_ratio = float(received / gross)
                        orig_notional = float(pos.get("notional_usd", 0.0) or 0.0)
                        pos.setdefault("intended_notional", orig_notional)
                        pos["notional_usd"] = round(orig_notional * fill_ratio, 4)
                        pos["fee_usd"] = round(float(pos.get("fee_usd", 0.0) or 0.0) * fill_ratio, 4)
                    elif "v2" not in str(pos.get("fee_source") or "").lower():
                        # Legacy V1 share-withheld fee fallback
                        pos["entry_fee_asset"] = "SHARES"
                        pos["entry_fee_cash_usd"] = 0.0
                elif (
                    gross > Decimal("0")
                    and str(pos.get("entry_fee_asset") or "").upper() == "SHARES"
                    and float(pos.get("fee_usd", 0.0) or 0.0) == 0.0
                    and float(pos.get("fee_rate_applied", 0.0) or 0.0) > 0.0
                    and net > 0.0
                ):
                    # Polymarket V2 (FeeModuleV2) settles 100% of gross shares and charges BUY fee in pUSD cash
                    raw_px_v2 = float(pos.get("notional_usd", 0.0) or 0.0) / float(net)
                    if 0.0 < raw_px_v2 < 1.0:
                        fr_v2 = float(pos.get("fee_rate_applied", 0.0) or 0.0)
                        fe_v2 = float(pos.get("fee_exponent_applied", 1.0) or 1.0)
                        v2_fee_u = round(float(net) * fr_v2 * ((raw_px_v2 * (1.0 - raw_px_v2)) ** fe_v2), 4)
                        pos["entry_fee_asset"] = "USDC"
                        pos["fee_usd"] = v2_fee_u
                        pos["entry_fee_cash_usd"] = v2_fee_u
                        if v2_fee_u > 0.0 and not pos.get("_v2_fee_collat_debited"):
                            pos["_v2_fee_collat_debited"] = True
                            _lk_v2 = getattr(self, "_last_known_collateral", None)
                            if isinstance(_lk_v2, (int, float)) and not isinstance(_lk_v2, bool):
                                self._last_known_collateral = max(0.0, float(_lk_v2) - v2_fee_u)
                            self._pending_collateral_refresh = True
                pos["entry_shares"] = net
                pos["remaining_shares"] = net
                pos["remaining_exit_shares"] = net
                pos["remaining_cost_basis"] = pos.get("notional_usd", 0.0)
                if net > 0 and float(pos.get("notional_usd", 0.0) or 0.0) > 0:
                    true_cost_per_share = round(float(pos["notional_usd"]) / net, 4)
                    if true_cost_per_share > float(pos.get("entry_price", 0.0) or 0.0):
                        pos["entry_price"] = true_cost_per_share
                        pos["target_exit_price"] = float(pos.get("custom_maker_exit_price") or 0.99) if (pos.get("is_dominance_box") or pos.get("is_single_leg_lock")) else self._calculate_target_exit(true_cost_per_share, expiry - now)
                pos["inventory_reconciled"] = True
                pos.pop("exit_blocked_reason", None)
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

        # 50/50 two-tranche maker exits for tickets >= $10.0 (50% fast scalp @ +12¢/+14¢, 50% runner @ 0.98)
        # Polymarket CLOB rejects GTC limit orders < 5.0 shares. Only split if t1_sz >= 5.0 and t2_sz >= 5.0
        rem_total = size
        entry_px = float(pos.get("entry_price", 0.70))
        use_tranches = False if pos.get("is_single_leg_lock") else self._use_two_tranche_maker_exit(pos.get("sleeve"))
        t1_offset = self._tranche1_tp_offset(pos.get("sleeve"))
        is_live_ctf = (
            (not self.dry_run)
            and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
            and bool(token_id and str(token_id).isdigit() and len(str(token_id)) >= 20)
            and not getattr(self, "enable_mid_hour_t1_12c", False)
        )
        if use_tranches and float(pos.get("notional_usd", 0.0) or 0.0) >= 10.0 and "exit_tranches" not in pos and rem_total >= 10.0:
            t1_sz = float((Decimal(str(rem_total)) * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            t2_sz = float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            if t1_sz >= 5.0 and t2_sz >= 5.0:
                # v3.9 Upgrade 2 (WFO-Validated +82.5% Holdout Profit): On live high-WR CTF positions, rest T1 at $0.95
                # and T2 at $0.98 instead of giving away half the binary upside at entry + $0.14!
                t1_px = 0.95 if is_live_ctf else min(0.94, round(entry_px + t1_offset, 2))
                t2_px = 0.98
                pos["exit_tranches"] = [
                    {"idx": 1, "size": t1_sz, "price": t1_px, "status": "PENDING"},
                    {"idx": 2, "size": t2_sz, "price": t2_px, "status": "PENDING"},
                ]
            else:
                pos["target_exit_price"] = 0.96 if is_live_ctf else min(0.96, round(entry_px + 0.16, 2))

        active_tranche = None
        pending_tranches = [t for t in pos.get("exit_tranches", []) if t.get("status") == "PENDING"]
        if pending_tranches and float(pending_tranches[0]["size"]) >= 5.0 and rem_total >= 5.0:
            cand_sz = min(rem_total, float(pending_tranches[0]["size"]))
            leftover = round(rem_total - cand_sz, 4)
            if 0.01 < leftover < 5.0:
                size = rem_total
                pos["target_exit_price"] = max(float(t["price"]) for t in pending_tranches)
                pos.pop("exit_tranches", None)
            else:
                active_tranche = pending_tranches[0]
                size = cand_sz
                pos["target_exit_price"] = float(active_tranche["price"])
        else:
            size = rem_total
            if pending_tranches and rem_total >= 5.0:
                pos["target_exit_price"] = max(float(t["price"]) for t in pending_tranches)
            from src.polymarket_research.riskless_machine_gun_engine import is_locked_arbitrage_box_leg
            pos.pop("exit_tranches", None)
            if is_locked_arbitrage_box_leg(pos, self.active_positions):
                pos["target_exit_price"] = max(0.99, float(pos.get("custom_maker_exit_price") or 0.99))
            elif pos.get("custom_maker_exit_price"):
                pos["target_exit_price"] = float(pos["custom_maker_exit_price"])
            elif pos.get("is_dominance_box") or pos.get("is_single_leg_lock"):
                pos["target_exit_price"] = 0.99
            elif self._effective_exit_policy() == "hold_98":
                pos["target_exit_price"] = 0.98
            elif not pos.get("target_exit_price"):
                pos["target_exit_price"] = 0.96 if is_live_ctf else min(0.96, round(entry_px + 0.16, 2))

        pos["status"] = ExecutionStatus.POSITION_CONFIRMED
        if size < 5.0 and not self.dry_run and str(token_id).isdigit() and len(str(token_id)) >= 20:
            logger.warning(
                f"[SUB-MINIMUM LOT GUARD] {tid}: remaining size {size:.2f} < 5.0 CLOB lot minimum; "
                "holding under supervised terminal policy without spamming HTTP 400s."
            )
            pos["exit_order_status"] = "SUB_MINIMUM_LOT_SUPERVISED_HOLD"
            pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
            self.save_state()
            return False
        self._maybe_queue_jump_on_post(pos, size)
        exit_res = self.executor.post_maker_exit_order(
            token_id=token_id, price=pos["target_exit_price"], size=size, side="SELL",
        )
        # Reprice maker ask up to best_bid + 0.01 if post_only rejected due to crossing book (FINDING-15-03c)
        if (
            not (exit_res or {}).get("success")
            and not (exit_res or {}).get("outcome_unknown")
            and not (exit_res or {}).get("crossed_at_max_tick")
            and "crosses book" in str((exit_res or {}).get("error", "")).lower()
        ):
            try:
                book = self.executor.get_market_book(token_id) if hasattr(self.executor, "get_market_book") else None
                bids = (book or {}).get("bids", [])
                if bids:
                    best_bid = max((float(b.get("price", 0.0) or 0.0) for b in bids if isinstance(b, dict)), default=0.0)
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

        if res.get("outcome_unknown") and str(close_reason or "") == "HTM_EARLY_998_PROFIT_RECYCLE":
            from src.polymarket_research.riskless_protocol_v2_expansion import resolve_delayed_recycle_unwind_sync
            res = resolve_delayed_recycle_unwind_sync(self, pos, res, close_reason, limit_price)
            oid = res.get("orderID") or oid
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
        if fee > 0.0 and self._exit_taker_fee_rate(pos) <= 0.0 and res.get("fee_is_estimated", True):
            fee = 0.0
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
        entry_fee_asset = str(pos.get("entry_fee_asset") or "").upper()
        raw_entry_cash_fee = pos.get("entry_fee_cash_usd")
        if entry_fee_asset == "SHARES":
            entry_cash_fee = float(raw_entry_cash_fee or 0.0)
        else:
            entry_cash_fee = float(raw_entry_cash_fee if raw_entry_cash_fee is not None else (pos.get("fee_usd") or 0.0))

        notional = float(pos.get("notional_usd") or 0.0)
        cash_in = float(gross_exit_cash or 0.0)
        cash_exit_fee = float(exit_fee or 0.0)
        
        raw_pnl = cash_in - notional - entry_cash_fee - cash_exit_fee
        cent_pnl = round(raw_pnl, 2)
        if cent_pnl != 0.0:
            return cent_pnl
        subcent_pnl = round(raw_pnl, 4)
        return subcent_pnl if abs(subcent_pnl) >= 0.0001 else 0.0

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
        redeemed_list = list(dict.fromkeys(str(h) for h in (getattr(self, "redeemed_tx_hashes", []) or []) if h))
        redeemed = set(redeemed_list)
        consumed_map = self.__dict__.setdefault("redeemed_tx_consumed_usd", {})
        if self.dry_run:
            payout = float(verified_usdc_received if verified_usdc_received is not None else win_shares)
            tx = tx_hash or f"DRYRUN_REDEMPTION_{trade_id}"
        else:
            receipts = self.executor.find_redemption_payouts(
                str(pos.get("condition_id") or ""),
                from_block=pos.get("resolution_block"),
                tx_hash=tx_hash,
            )
            if not receipts and win_shares >= 0.01 and not tx_hash:
                # Redemptions submitted outside the harvester (Polymarket UI / pUSD adapter route) may emit
                # PayoutRedemption with a redeemer other than this wallet, so the topic scan finds nothing.
                # If the winning ERC-1155 balance is verifiably ZERO on-chain after resolution, the shares were
                # redeemed: settle the receivable at $1.00/share instead of double-counting it in equity forever.
                tok_r = str(pos.get("token_id") or "")
                bal_r = None
                if tok_r and hasattr(self.executor, "get_onchain_erc1155_balance"):
                    try:
                        bal_r = self.executor.get_onchain_erc1155_balance(tok_r)
                    except Exception:
                        bal_r = None
                if bal_r is not None and float(bal_r) <= 0.0001:
                    logger.info(
                        f"[REDEMPTION EXTERNAL] {trade_id}: winning token balance is 0 on-chain -> settling "
                        f"{win_shares:.2f} sh receivable as redeemed outside the harvester."
                    )
                    receipts = [{"transaction_hash": f"EXTERNAL_REDEMPTION_{trade_id}", "payout_usd": win_shares}]
            if receipts is None:
                if (
                    win_shares < 0.01
                    and float(pos.get("confirmed_realized_cash", pos.get("realized_exit_cash", 0.0)) or 0.0) > 0.0
                ):
                    pos["exit_cash_estimated"] = False
                    pos["estimated_exit_cash"] = 0.0
                    pos["confirmed_realized_cash"] = float(pos.get("confirmed_realized_cash") or pos.get("realized_exit_cash") or 0.0)
                    logger.info(
                        f"[REDEMPTION DUST CLOSE] {trade_id}: closing on confirmed CLOB cash "
                        f"${pos['confirmed_realized_cash']:.2f} (ignoring {win_shares:.4f} sh dust receivable)."
                    )
                    self._close_position(trade_id, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=None)
                    return True
                logger.warning(f"[REDEMPTION] Cannot verify redemption for {trade_id} (RPC unavailable); retaining receivable.")
                return False
            fresh = [
                r for r in receipts
                if r.get("transaction_hash")
                and r["transaction_hash"] not in redeemed
                and (float(r.get("payout_usd") or 0.0) - float(consumed_map.get(str(r["transaction_hash"]), 0.0) or 0.0)) > 0.005
            ]
            if not fresh:
                return False
            receipt = fresh[0]
            payout = float(receipt["payout_usd"])
            tx = str(receipt["transaction_hash"])
        if tx in redeemed:
            logger.warning(f"[REDEMPTION] Duplicate redemption receipt {tx} ignored for {trade_id}.")
            return False

        avail_payout = payout if self.dry_run else max(0.0, payout - float(consumed_map.get(tx, 0.0) or 0.0))
        if not self.dry_run and avail_payout <= 0.005:
            return False
        attributed = round(min(avail_payout, win_shares), 6)
        self.record_fill_and_update_position(pos, f"ONCHAIN_REDEMPTION_{tx}", win_shares, attributed, 0.0)
        cum_cash = float(pos.get("realized_exit_cash", 0.0))
        cum_exit_fee = float(pos.get("realized_exit_fee", 0.0))
        net_pnl = self.calculate_realized_cash_pnl(pos, cum_cash, cum_exit_fee)

        pos["status"] = ExecutionStatus.SETTLED
        pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
        pos["won"] = (net_pnl > 0.0)
        pos["payout_usd"] = round(cum_cash, 4)
        pos["net_pnl_usd"] = round(net_pnl, 4)
        pos["close_reason"] = "ONCHAIN_REDEMPTION_CONFIRMED"
        pos["exit_decomposition_bucket"] = "TERMINAL_SETTLEMENT"
        pos["redemption_tx_hash"] = tx
        pos["redemption_payout_verified_usd"] = payout
        pos["redemption_receivable_usd"] = 0.0

        if not self.dry_run:
            consumed_map[tx] = round(float(consumed_map.get(tx, 0.0) or 0.0) + attributed, 6)
        if self.dry_run or float(consumed_map.get(tx, 0.0) or 0.0) >= payout - 0.009:
            if tx not in redeemed:
                redeemed.add(tx)
                redeemed_list.append(tx)
            consumed_map.pop(tx, None)
        self.redeemed_tx_hashes = redeemed_list[-1000:]
        leg_net_cash = max(0.0, float(cum_cash or 0.0) - float(cum_exit_fee or 0.0))
        unsynced_leg_net_cash = max(0.0, leg_net_cash - float(pos.get("_synced_exit_cash_usd", 0.0) or 0.0))
        if (
            not getattr(self, "dry_run", True)
            and getattr(self, "_last_known_collateral", None) is not None
            and unsynced_leg_net_cash > 0.0
            and not pos.get("_collateral_exit_credited")
            and not pos.get("_pre_redeemed_onchain")
            and not str(tx).startswith("EXTERNAL_REDEMPTION_")
        ):
            pos["_collateral_exit_credited"] = True
            self._last_known_collateral = float(self._last_known_collateral) + unsynced_leg_net_cash
            self._last_exit_credit_window = (time.time(), float(self._last_known_collateral))
        deferred_partner, net_pnl = self._consolidate_dominance_box_close(
            trade_id, pos, cum_cash, cum_exit_fee, net_pnl, "ONCHAIN_REDEMPTION_CONFIRMED", True
        )
        if deferred_partner:
            self.executor.invalidate_collateral_cache()
            return True
        self.closed_positions.append(pos)
        _is_nd_red = bool(
            pos.get("is_dominance_box")
            or pos.get("is_single_leg_lock")
            or pos.get("is_legged_out_residual")
            or "BOX" in str(pos.get("sleeve") or "").upper()
        )
        self.risk_controller.record_trade_pnl(net_pnl, is_non_directional=_is_nd_red)
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
        submitted_tx_by_cond: Dict[str, str] = {}
        for tid, pos in list(self.active_positions.items()):
            if position_is_settlement_receivable(pos) and float(pos.get("winning_shares_held", 0.0) or 0.0) > 0.0:
                try:
                    m_id_str = str(pos.get("market_id") or "")
                    if not self.dry_run and m_id_str.isdigit() and int(m_id_str) >= 100000:
                        try:
                            gm = self.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{m_id_str}", timeout=3.0).json()
                            uma_st = str(gm.get("umaResolutionStatus") or "").strip().lower()
                            raw_op = gm.get("outcomePrices")
                            op = json.loads(raw_op) if isinstance(raw_op, str) else raw_op
                            raw_toks = gm.get("clobTokenIds")
                            clob_toks = json.loads(raw_toks) if isinstance(raw_toks, str) else raw_toks
                            if uma_st in ("", "resolved") and isinstance(op, list) and len(op) >= 2:
                                pos_tok = str(pos.get("token_id") or "")
                                if isinstance(clob_toks, list) and pos_tok and pos_tok in [str(x) for x in clob_toks]:
                                    t_idx = [str(x) for x in clob_toks].index(pos_tok)
                                else:
                                    t_idx = 0 if str(pos.get("target_token", "UP")).upper() in ("UP", "YES") else 1
                                if float(op[t_idx]) == 0.0 and float(op[1 - t_idx]) == 1.0:
                                    logger.warning(f"[GAMMA ORACLE OVERRIDE] {tid}: Gamma outcomePrices={op} (idx={t_idx}) shows authoritative resolution against local spot oracle. Closing ghost receivable.")
                                    pos["expected_terminal_payout_usd"] = 0.0
                                    pos["redemption_receivable_usd"] = 0.0
                                    pos["winning_shares_held"] = 0.0
                                    self._close_position(tid, pos, ExecutionStatus.SETTLED, "MARKET_RESOLVED_LOSS", won=False)
                                    continue
                        except Exception:
                            pass
                    sub_tx = None
                    if not self.dry_run and hasattr(self.executor, "attempt_onchain_redemption"):
                        raw_sig_t = getattr(self.executor, "signature_type", None)
                        sig_t_val = 1 if raw_sig_t is None else int(raw_sig_t)
                        if sig_t_val == 3 and not bool((os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY") or "").strip()):
                            send_operational_alert(
                                "REDEMPTION_BUILDER_CREDS_MISSING",
                                f"Mature winning receivable {tid} (${float(pos.get('winning_shares_held') or 0.0):.2f}) requires POLY_BUILDER_API_KEY.",
                                "WARNING", rate_limit_sec=3600.0, dedupe_key="redemption_builder_creds_missing",
                            )
                        cond_str = str(pos.get("condition_id") or "")
                        prev_pend_tx = pos.get("pending_redemption_tx_hash")
                        prev_pend_ts = float(pos.get("pending_redemption_submitted_ts", 0.0) or 0.0)
                        if cond_str and cond_str in submitted_tx_by_cond:
                            sub_tx = submitted_tx_by_cond[cond_str]
                        elif prev_pend_tx and (now - prev_pend_ts) < 60.0:
                            sub_tx = None
                        else:
                            try:
                                sub_tx = self.executor.attempt_onchain_redemption(
                                    cond_str,
                                    neg_risk=pos.get("neg_risk") if "neg_risk" in pos else None,
                                )
                            except TypeError:
                                sub_tx = self.executor.attempt_onchain_redemption(cond_str)
                            if sub_tx and cond_str:
                                submitted_tx_by_cond[cond_str] = str(sub_tx)
                    if sub_tx:
                        pos["pending_redemption_tx_hash"] = str(sub_tx)
                        pos["pending_redemption_submitted_ts"] = now
                    if self.confirm_onchain_redemption(tid, tx_hash=sub_tx or pos.get("pending_redemption_tx_hash")):
                        settled += 1
                except Exception as e:
                    logger.error(f"[REDEMPTION] Verification error for {tid}: {e}")
        _auto_wrap_on = bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("routing", {}).get("enable_auto_wrap_legacy_usdce_to_pusd", True))
        if settled > 0:
            if not self.dry_run and _auto_wrap_on and hasattr(self.executor, "wrap_idle_usdce_to_pusd"):
                try:
                    self._last_usdce_wrap_chk = now
                    self.executor.wrap_idle_usdce_to_pusd(min_usd=1.0)
                except Exception:
                    pass
            if not self.dry_run and hasattr(self.executor, "sync_clob_collateral_allowance"):
                try:
                    self.executor.sync_clob_collateral_allowance()
                except Exception:
                    self.executor.invalidate_collateral_cache()
            else:
                self.executor.invalidate_collateral_cache()
            self._pending_collateral_refresh = True
            main_loop = getattr(self, "_main_loop", None)
            if main_loop is not None and main_loop.is_running():
                try:
                    main_loop.call_soon_threadsafe(lambda: asyncio.create_task(self._async_refresh_collateral()))
                except Exception:
                    pass
            logger.info(f"[AUTO-REDEEMER] Swept and settled {settled} mature position(s). Reclaimed collateral to balance.")
        elif (
            not self.dry_run
            and _auto_wrap_on
            and hasattr(self.executor, "wrap_idle_usdce_to_pusd")
            and getattr(self.executor, "_mock_children", None) is None
            and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
            and (now - float(getattr(self, "_last_usdce_wrap_chk", 0.0) or 0.0)) >= 300.0
        ):
            self._last_usdce_wrap_chk = now
            try:
                _w_tx = self.executor.wrap_idle_usdce_to_pusd(min_usd=1.0)
                if _w_tx:
                    self.executor.invalidate_collateral_cache()
                    self._pending_collateral_refresh = True
            except Exception:
                pass
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

    @staticmethod
    def _resolve_true_usd_spot_from_shock(shock: Dict[str, Any]) -> Tuple[float, float]:
        """Extracts true USD (spot, twap_60s) from a shock/SHM payload, sanitizing any legacy USDT cl_proxy."""
        cl_proxy = float(shock.get("chainlink_proxy_spot") or 0.0)
        cb_spot = float(shock.get("coinbase_spot") or 0.0)
        bn_spot = float(shock.get("spot_at_t0") or shock.get("spot_price") or shock.get("spot") or shock.get("trigger_price") or 0.0)
        cl_twap = float(shock.get("chainlink_twap_60s") or 0.0)
        is_anchored = bool(shock.get("chainlink_basis_anchored", False))
        if not is_anchored and cb_spot > 0.0 and cl_proxy > 0.0 and bn_spot > 0.0:
            if abs(cl_proxy - cb_spot) / cb_spot > 0.0004 and abs(cl_proxy - bn_spot) / bn_spot < 0.00025:
                return cb_spot, (round(cl_twap * (cb_spot / cl_proxy), 4) if cl_twap > 0.0 else 0.0)
        usd_spot = cl_proxy if cl_proxy > 0.0 else cb_spot
        if usd_spot > 0.0 and cl_twap > 0.0 and bn_spot > 0.0 and not is_anchored:
            if abs(cl_twap - usd_spot) / usd_spot > 0.0004 and abs(cl_twap - bn_spot) / bn_spot < 0.0005:
                cl_twap = round(cl_twap * (usd_spot / bn_spot), 4)
        return usd_spot, cl_twap

    def get_usd_reference_spot_price(self, asset: str) -> Optional[float]:
        """Pulls true-USD spot price for 15m Chainlink-settled positions (/dev/shm true USD first, Coinbase USD REST fallback)."""
        now = time.time()
        sym = asset.upper()
        cache_key = f"{sym}USD"
        snap = read_fast_tick(sym, max_age_sec=FAST_TICK_MAX_AGE_SEC, now=now)
        if snap and not (float(snap.get("spot_ts") or 0.0) > 0.0 and (now - float(snap["spot_ts"])) > 5.0):
            usd_px, _ = self._resolve_true_usd_spot_from_shock(snap)
            if math.isfinite(usd_px) and usd_px > 0.0:
                self._spot_cache[cache_key] = (usd_px, now)
                return usd_px
        if cache_key in self._spot_cache:
            val, ts = self._spot_cache[cache_key]
            if now - ts < 1.0:
                return val
        try:
            resp = self.executor._sync_session.get(f"https://api.exchange.coinbase.com/products/{sym}-USD/ticker", timeout=1.5)
            if resp.status_code == 200:
                price = float(resp.json().get("price", 0.0))
                if math.isfinite(price) and price > 0.0:
                    self._spot_cache[cache_key] = (price, now)
                    return price
        except Exception as e:
            logger.debug(f"Failed to fetch Coinbase USD spot for {sym}: {e}")
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
        if snap and not (float(snap.get("spot_ts") or 0.0) > 0.0 and (now - float(snap["spot_ts"])) > 5.0):
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

        # Authoritative fee schedule binding (Round 10 P1-01; supports zero_fees r=0.0, e>=0.0)
        r = float(fee_rate if fee_rate is not None else 0.07)
        e = float(fee_exponent if fee_exponent is not None else 1.0)
        if not (math.isfinite(r) and r >= 0.0 and math.isfinite(e) and (e > 0.0 or (r == 0.0 and e >= 0.0))):
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
        if not math.isfinite(ticket_usd) or ticket_usd <= 0.0:
            return 0.0
        if ticket_usd > MAX_ABSOLUTE_TICKET_USD:
            ticket_usd = min(MAX_ABSOLUTE_TICKET_USD, effective_cap)
        return round(ticket_usd, 2)

    def load_state(self):
        target_state_file = getattr(self, "state_file", STATE_FILE)
        if target_state_file.exists():
            try:
                with open(target_state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.active_positions = state.get("active_positions", {})
                self.closed_positions = state.get("closed_positions", [])
                self.pending_entry_intents = state.get("pending_entry_intents", {})
                self.redeemed_tx_hashes = list(state.get("redeemed_tx_hashes", []) or [])
                self.redeemed_tx_consumed_usd = dict(state.get("redeemed_tx_consumed_usd", {}) or {})
                self.pre_split_inventory_state = dict(state.get("pre_split_inventory_state") or {})
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
                        if position_requires_lifecycle_resolution(pos):
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
                saved_d1_keys = [str(k) for k in (state.get("seen_d1_box_keys") or []) if k]
                self._seen_d1_box_keys = set(saved_d1_keys)
                self._seen_d1_box_order = {k: None for k in saved_d1_keys}
                raw_d1_ts = state.get("seen_d1_box_ts") if isinstance(state.get("seen_d1_box_ts"), dict) else {}
                self._seen_d1_box_ts = {
                    str(k): float(v)
                    for k, v in raw_d1_ts.items()
                    if str(k) in self._seen_d1_box_keys and isinstance(v, (int, float))
                }
                self._persisted_state = dict(state)
                raw_ft_f = state.get("ft_live_funnel")
                if not isinstance(raw_ft_f, dict) and isinstance(state.get("live_riskless_funnel"), dict):
                    raw_ft_f = state["live_riskless_funnel"].get("ft_bridge_stats")
                if isinstance(raw_ft_f, dict):
                    self._ft_live_funnel = dict(raw_ft_f)
                self.traded_market_ids = set(state.get("traded_market_ids", []))
                raw_tpm = state.get("trades_per_market", {})
                raw_tpmd = state.get("trades_per_market_direction", {}) or {}
                self.trades_per_market = defaultdict(int, {str(k): int(v) for k, v in raw_tpm.items()})
                self.trades_per_market_direction = defaultdict(int)
                for k_dir, v_dir in raw_tpmd.items():
                    if "_" in str(k_dir):
                        m_part, t_part = str(k_dir).rsplit("_", 1)
                        self.trades_per_market_direction[(m_part, t_part)] = int(v_dir)
                if not raw_tpmd:
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
                elif not raw_tpm and self.closed_positions:
                    for cp in self.closed_positions:
                        mid = str(cp.get("market_id", ""))
                        if mid:
                            self.trades_per_market[mid] += 1
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
                    self.risk_controller.non_directional_realized_pnl = 0.0
                    self.risk_halt = False
                    self.reconciliation_required = False
                    self.global_halt_reasons = []
                    logger.info("[STARTUP] Risk controller circuit breaker explicitly reset via --reset-risk flag.")
                else:
                    if risk_st.get("halted"):
                        saved_reason = str(risk_st.get("halt_reason", "Restored from persisted halt state"))
                        if not self.dry_run and "Heartbeat degraded" in saved_reason and self.executor.is_heartbeat_healthy():
                            logger.info(f"[STARTUP] Cleared transient session heartbeat halt on fresh process startup ({saved_reason}).")
                            self.risk_controller.halted = False
                            self.risk_controller.halt_reason = ""
                        else:
                            self.risk_controller.halted = True
                            self.risk_controller.halt_reason = saved_reason
                    saved_loss_date = risk_st.get("last_loss_date_utc")
                    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    if saved_loss_date and saved_loss_date != today_utc:
                        self.risk_controller.consecutive_losses = 0
                        self.risk_controller.daily_realized_loss = 0.0
                        self.risk_controller.last_loss_date_utc = today_utc
                    else:
                        self.risk_controller.consecutive_losses = int(risk_st.get("consecutive_losses", 0) or 0)
                        self.risk_controller.daily_realized_loss = float(risk_st.get("daily_realized_loss", 0.0) or 0.0)
                        if saved_loss_date:
                            self.risk_controller.last_loss_date_utc = str(saved_loss_date)
                    self.risk_controller.non_directional_realized_pnl = float(
                        risk_st.get("non_directional_realized_pnl", 0.0) or 0.0
                    )
                if migrated_orphaned_liquidations:
                    self.save_state()
                self._last_known_collateral = state.get("live_bankroll")
                if isinstance(self._last_known_collateral, (int, float)) and math.isfinite(self._last_known_collateral) and self._last_known_collateral > 0.0:
                    self.executor.set_cached_collateral(float(self._last_known_collateral))
                saved_tier = state.get("current_equity_tier") or state.get("equity_tier")
                if isinstance(saved_tier, str) and saved_tier:
                    self._current_equity_tier = saved_tier
                    self.current_equity_tier = saved_tier
                elif not getattr(self, "_current_equity_tier", None):
                    self._current_equity_tier = "UNLEASHED_LAUNCH"
                    self.current_equity_tier = "UNLEASHED_LAUNCH"
                if state.get("dynamic_bankroll_pct") is not None:
                    try:
                        self.dynamic_bankroll_pct = float(state["dynamic_bankroll_pct"])
                    except (TypeError, ValueError):
                        pass
                if getattr(self, "reset_risk", False):
                    self.high_water_mark_equity = float(state.get("live_bankroll") or 0.0)
                else:
                    self.high_water_mark_equity = float(
                        state.get("high_water_mark_equity")
                        or state.get("total_account_equity")
                        or state.get("live_bankroll")
                        or getattr(self, "high_water_mark_equity", 0.0)
                        or 0.0
                    )
                tot_equity_saved = float(state.get("total_account_equity") or self._last_known_collateral or 0.0)
                if tot_equity_saved > 0:
                    sizing_eq_saved, has_frozen_saved = self._effective_sizing_equity_usd(tot_equity_saved)
                    self._update_equity_tier(sizing_eq_saved, allow_hwm_ratchet=(not has_frozen_saved))
                    if (
                        self.risk_controller.halted
                        and "Account equity" in str(self.risk_controller.halt_reason or "")
                        and tot_equity_saved >= (self.risk_controller.min_equity_floor_usd + 3.00)
                    ):
                        logger.info(
                            f"[STARTUP] Cleared stale equity circuit-breaker halt on startup: "
                            f"persisted equity ${tot_equity_saved:.2f} >= +$3.00 above ${self.risk_controller.min_equity_floor_usd:.2f} tier floor."
                        )
                        self.risk_controller.halted = False
                        self.risk_controller.halt_reason = ""
                migrated_subcent_wins = 0
                for cp in self.closed_positions:
                    if (
                        isinstance(cp, dict)
                        and str(cp.get("status") or "").upper() in {"SETTLED", "FILLED"}
                        and not bool(cp.get("exit_cash_estimated", False))
                        and float(cp.get("estimated_exit_cash", 0.0) or 0.0) <= 0.0
                        and not (cp.get("box_legs_summary") or [])
                        and not bool(cp.get("won"))
                        and float(cp.get("net_pnl_usd", 0.0) or 0.0) == 0.0
                        and float(cp.get("notional_usd", 0.0) or 0.0) > 0.0
                    ):
                        _cp_cash = float(cp.get("confirmed_realized_cash", cp.get("realized_exit_cash", 0.0)) or 0.0)
                        if _cp_cash > 0.0:
                            _cp_exact_pnl = self.calculate_realized_cash_pnl(
                                cp, _cp_cash, float(cp.get("realized_exit_fee", 0.0) or 0.0)
                            )
                            if 0.0 < _cp_exact_pnl < 0.01:
                                cp["net_pnl_usd"] = _cp_exact_pnl
                                cp["won"] = True
                                if "REDEMPTION" in str(cp.get("close_reason") or "").upper():
                                    cp["exit_decomposition_bucket"] = "TERMINAL_SETTLEMENT"
                                if bool(
                                    cp.get("is_dominance_box")
                                    or cp.get("is_single_leg_lock")
                                    or cp.get("is_legged_out_residual")
                                    or "BOX" in str(cp.get("sleeve") or "").upper()
                                ):
                                    self.risk_controller.non_directional_realized_pnl = round(
                                        float(getattr(self.risk_controller, "non_directional_realized_pnl", 0.0) or 0.0)
                                        + _cp_exact_pnl,
                                        4,
                                    )
                                migrated_subcent_wins += 1
                if migrated_subcent_wins > 0:
                    logger.info(f"[STARTUP] Reconciled {migrated_subcent_wins} sub-cent settled winning trade(s) in closed_positions.")
                    self.save_state()
                logger.info(f"Loaded existing state: {len(self.active_positions)} active positions, {len(self.traded_market_ids)} traded markets.")
            except Exception as e:
                logger.critical(f"LIVE STATE UNREADABLE; refusing all reconciliation and order mutation: {e}")
                raise RuntimeError("Refusing live startup with unreadable position state") from e

    _GLOBAL_STATE_SAVE_LOCK = threading.RLock()
    _RISKLESS_SAVE_HELPERS: Optional[Tuple[Any, Any]] = None

    def save_state(self):
        lock = getattr(self, "_state_save_lock", None) or self._GLOBAL_STATE_SAVE_LOCK
        with lock:
            now_ts = time.time()
            helpers = type(self)._RISKLESS_SAVE_HELPERS
            if helpers is None:
                from src.polymarket_research.riskless_protocol_v2_expansion import (
                    compute_dynamic_riskless_tier_caps,
                    pending_intents_synced_equity_usd,
                )
                helpers = (compute_dynamic_riskless_tier_caps, pending_intents_synced_equity_usd)
                type(self)._RISKLESS_SAVE_HELPERS = helpers
            else:
                compute_dynamic_riskless_tier_caps, pending_intents_synced_equity_usd = helpers
            _ps_st = getattr(self, "pre_split_inventory_state", None) or {}
            _ps_eq = (min(float(_ps_st.get("up_rem", 0.0) or 0.0), float(_ps_st.get("dn_rem", 0.0) or 0.0)) if _ps_st.get("active") else 0.0) + sum(
                min(float(_s.get("up_rem", 0.0) or 0.0), float(_s.get("dn_rem", 0.0) or 0.0))
                for _s in ((_ps_st.get("extra_slots") if isinstance(_ps_st.get("extra_slots"), dict) else None) or {}).values()
                if isinstance(_s, dict) and _s.get("active")
            )
            active_market_equity = sum(self.get_position_market_value(p, now_ts) for p in self.active_positions.values()) + _ps_eq + pending_intents_synced_equity_usd(getattr(self, "pending_entry_intents", None))
            tot_equity = (
                (float(self._last_known_collateral) + active_market_equity)
                if getattr(self, "_last_known_collateral", None) is not None
                else None
            )
            sizing_eq_save, _ = self._effective_sizing_equity_usd(tot_equity, now_ts)
            _http_s = sorted(float(x) for x in (self.__dict__.get("_sll_post_http_ms") or ()))
            _pend_map_s = getattr(self, "pending_entry_intents", None) or {}
            _funnel_st = {
                "ws_watch_tokens": len(getattr(self, "_clinched_ws_watchlist", None) or {}) * 2,
                "ws_snipe_emitted": int(self.__dict__.get("_ws_clinch_snipe_emitted_count", 0) or 0),
                "resting_maker_slots": sum(1 for i in _pend_map_s.values() if isinstance(i, dict) and i.get("live_maker_anchor_inflight")),
                "fifo_rank1_slots": sum(1 for i in _pend_map_s.values() if isinstance(i, dict) and bool(i.get("fifo_rank1_verified"))),
                "outbid_repegs": int(self.__dict__.get("_sll_repeg_count", 0) or 0),
                "http_p50_ms": round(_http_s[len(_http_s) // 2], 2) if _http_s else None,
                "http_p99_ms": round(_http_s[min(len(_http_s) - 1, int(len(_http_s) * 0.99))], 2) if _http_s else None,
                "uma_early_recycles": int(self.__dict__.get("_uma_early_recycle_count", 0) or 0),
                "presigned_repeg_hits": int(getattr(getattr(self, "executor", None), "_presigned_maker_repeg_hits", 0) or 0),
                "dynamic_tier_caps": compute_dynamic_riskless_tier_caps(
                    float(sizing_eq_save if tot_equity is not None else 0.0),
                    GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes"),
                ),
            }
            now_utc_iso = datetime.now(timezone.utc).isoformat()
            _ft_snap = self._snapshot_ft_live_funnel(_pend_map_s, now_utc_iso=now_utc_iso)
            _funnel_st["ft_bridge_stats"] = _ft_snap
            seen_shocks_list = list(self._seen_shock_order.keys())[-1000:] if hasattr(self, "_seen_shock_order") else list(self.seen_shock_ids)[-1000:]
            seen_d1_list = (
                list(self._seen_d1_box_order.keys())[-200:]
                if hasattr(self, "_seen_d1_box_order")
                else list(getattr(self, "_seen_d1_box_keys", set()))[-200:]
            )
            cur_tier = getattr(self, "_current_equity_tier", None) or getattr(self, "current_equity_tier", None)
            state = {
                "state_version": "2.0.0", "updated_at_utc": now_utc_iso,
                "ticket_notional": self.ticket_notional, "dynamic_sizing": self.dynamic_sizing,
                "max_exposure": self.max_exposure, "max_concurrent_positions": self.max_concurrent_positions,
                "max_total_portfolio_slots": int((getattr(self, "risk_config", None) or RISK_CONFIG).get("max_total_portfolio_slots", 4)),
                "unlimited_slots": self._is_unlimited_slots_active(),
                "dry_run": self.dry_run, "last_event_id": getattr(self, "last_event_id", ""),
                "live_bankroll": getattr(self, "_last_known_collateral", None), "total_account_equity": tot_equity,
                "reconciled_nav_usd": (round(sizing_eq_save, 4) if tot_equity is not None else None),
                "high_water_mark_equity": getattr(self, "high_water_mark_equity", None),
                "equity_tier": cur_tier, "current_equity_tier": cur_tier,
                "dynamic_bankroll_pct": getattr(self, "dynamic_bankroll_pct", None),
                "active_positions_count": len(self.active_positions), "closed_positions_count": len(self.closed_positions),
                "trades_this_hour": self.trades_this_hour, "current_hour_window": self.current_hour_window,
                "active_positions": self.active_positions, "active_position_ids": list(self.active_positions.keys()),
                "pending_entry_intents": getattr(self, "pending_entry_intents", {}),
                "risk_halt": getattr(self, "risk_halt", False), "reconciliation_required": getattr(self, "reconciliation_required", False),
                "global_halt_reasons": list(getattr(self, "global_halt_reasons", []) or []),
                "redeemed_tx_hashes": list(getattr(self, "redeemed_tx_hashes", []) or [])[-1000:],
                "redeemed_tx_consumed_usd": dict(getattr(self, "redeemed_tx_consumed_usd", {}) or {}),
                "pre_split_inventory_state": dict(getattr(self, "pre_split_inventory_state", {}) or {}),
                "closed_positions": self.closed_positions[-500:], "seen_shock_ids": seen_shocks_list,
                "seen_d1_box_keys": seen_d1_list,
                "seen_d1_box_ts": {
                    k: float(self.__dict__.get("_seen_d1_box_ts", {}).get(k))
                    for k in seen_d1_list
                    if k in (self.__dict__.get("_seen_d1_box_ts") or {})
                },
                "traded_market_ids": list(self.traded_market_ids)[-100:], "trades_per_market": dict(self.trades_per_market),
                "trades_per_market_direction": {f"{k[0]}_{k[1]}": v for k, v in getattr(self, "trades_per_market_direction", {}).items()},
                "risk_state": {
                    "halted": self.risk_controller.halted, "halt_reason": self.risk_controller.halt_reason,
                    "consecutive_losses": self.risk_controller.consecutive_losses, "daily_realized_loss": self.risk_controller.daily_realized_loss,
                    "non_directional_realized_pnl": float(getattr(self.risk_controller, "non_directional_realized_pnl", 0.0) or 0.0),
                    "last_loss_date_utc": getattr(self.risk_controller, "last_loss_date_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                },
                "status": getattr(self, "_shutdown_status", None) or ("HALTED" if self.risk_controller.is_halted() else "RUNNING"),
                "live_riskless_funnel": _funnel_st,
                "ft_live_funnel": _ft_snap,
            }
            # Atomic file write pattern with PID+TID-unique temp file, fsync and directory sync (Findings 12 & 23)
            target_state_file = getattr(self, "state_file", STATE_FILE)
            tmp_file = target_state_file.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
            try:
                payload_bytes: Optional[bytes] = None
                if _orjson is not None:
                    try:
                        payload_bytes = _orjson.dumps(state, option=_orjson.OPT_INDENT_2)
                    except TypeError:
                        payload_bytes = None
                if payload_bytes is not None:
                    with open(tmp_file, "wb") as f:
                        f.write(payload_bytes)
                        f.flush()
                        os.fsync(f.fileno())
                else:
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                for _rep_i in range(3):
                    try:
                        os.replace(tmp_file, target_state_file)
                        break
                    except PermissionError:
                        if os.name != "nt" or _rep_i >= 2:
                            raise
                        time.sleep(0.01)
                self._last_persisted_collateral = state.get("live_bankroll")
                if publish_global_positions_shm is not None and not self.dry_run:
                    publish_global_positions_shm("live_harvester", self.active_positions.values())
                if os.name != "nt":
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

    def get_graduated_allowed_assets(self, total_equity: Optional[float] = None) -> Set[str]:
        """Returns base allowed_assets, auto-adding SOL/XRP once equity >= $110 and shadow state marks ready_for_live_graduation."""
        assets = set(self.allowed_assets)
        if self._is_v5_live_strict():
            _d_gov = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {})
            for _k in ("allowed_assets_1h", "allowed_assets_15m_maker"):
                assets.update(str(x).upper() for x in (_d_gov.get(_k) or []))
            paused = {str(x).upper() for x in (_d_gov.get("paused_directional_assets") or [])}
        else:
            paused = set()
        if not RISK_CONFIG.get("enable_graduated_alt_sleeves", True):
            return assets - paused
        eq = total_equity
        if eq is None and getattr(self, "_last_known_collateral", None) is not None:
            now_t = time.time()
            eq = float(self._last_known_collateral) + sum(
                self.get_position_market_value(p, now_t) for p in self.active_positions.values()
            )
        if eq is None or float(eq) < float(RISK_CONFIG.get("scale_up_equity_threshold", 110.0)):
            return assets - paused
        grad_cache = self.__dict__.setdefault("_alt_grad_file_cache", {})
        for sym, fname in (("SOL", "state_shadow_sol_v392.json"), ("XRP", "state_shadow_xrp_v392.json")):
            try:
                sp = DATA_DIR / fname
                st_sp = sp.stat()
                ck = (str(sp), st_sp.st_mtime_ns, st_sp.st_size)
                cached_g = grad_cache.get(sym)
                if isinstance(cached_g, tuple) and len(cached_g) == 2 and cached_g[0] == ck:
                    is_grad = bool(cached_g[1])
                else:
                    st_doc = _json_loads(sp.read_bytes())
                    pf_ok = float(st_doc.get("profit_factor", 2.0) or 2.0) >= 1.80 if "profit_factor" in st_doc else True
                    wr_ok = float(st_doc.get("win_rate_pct", 90.0) or 90.0) >= 84.0 if "win_rate_pct" in st_doc else True
                    is_grad = bool(st_doc.get("ready_for_live_graduation") is True and pf_ok and wr_ok)
                    grad_cache[sym] = (ck, is_grad)
                if is_grad:
                    assets.add(sym)
            except Exception:
                continue
        return assets - paused

    def _record_seen_d1_box_key(self, dedupe_k: str) -> None:
        """Records D1 box dedupe key with timestamp for 15s cooldown + per-market open-notional cap."""
        if not dedupe_k:
            return
        seen_boxes = self.__dict__.setdefault("_seen_d1_box_keys", set())
        seen_order = self.__dict__.setdefault("_seen_d1_box_order", {k: None for k in seen_boxes})
        seen_ts = self.__dict__.setdefault("_seen_d1_box_ts", {})
        seen_order.pop(dedupe_k, None)
        seen_order[dedupe_k] = None
        seen_boxes.add(dedupe_k)
        seen_ts[dedupe_k] = round(time.time(), 3)
        while len(seen_order) > 400:
            oldest_k = next(iter(seen_order))
            seen_order.pop(oldest_k, None)
            seen_boxes.discard(oldest_k)
            seen_ts.pop(oldest_k, None)

    def _is_d1_box_halted(self) -> bool:
        """
        Decouples $1.00-payout riskless 2-leg/1-leg boxes from directional daily-loss variance halts,
        halting boxes ONLY on explicit disable, reconciliation/heartbeat/kill-file halts, or hard survival equity breach.
        """
        _rcfg_d1_h = getattr(self, "risk_config", None) or {}
        _gov_d1_on = bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_graduated_d1_box", True))
        if (
            not bool(_rcfg_d1_h.get("enable_graduated_d1_box", RISK_CONFIG.get("enable_graduated_d1_box", True)))
            or not _gov_d1_on
            or getattr(self, "risk_halt", False)
        ):
            return True
        if not self.dry_run:
            if self._global_halt_reasons() or not self.executor.is_heartbeat_healthy():
                return True
        if hasattr(self.risk_controller, "_mock_children"):
            if bool(self.risk_controller.is_halted()):
                return True
        elif self.risk_controller.is_riskless_box_halted():
            return True
        return False

    def maybe_execute_graduated_d1_box(self, candidate_box: Dict[str, Any]) -> Dict[str, Any]:
        """Executes verified 8/8-graduated 2-leg riskless boxes (D1 7-coin, C1, M3, B3, 2-leg N1) with multi-box concurrency."""
        if self._is_d1_box_halted():
            return {"executed": False, "reason": "DISABLED_OR_HALTED"}
        box_type = str(candidate_box.get("box_type") or "DOMINANCE").strip().upper()
        if box_type == "C1_BINARY_COMPLETE_SET":
            box_type = "COMPLETE_SET"
        elif box_type == "DOMINANCE_BOX":
            box_type = "MACRO_DOMINANCE"
        sleeve_src = str(candidate_box.get("sleeve_source") or ("D1_SAME_ORACLE_DOMINANCE_BOX" if box_type != "SINGLE_LEG_LOCK" else "")).strip()
        _enforce_paused_rb = bool(
            getattr(self, "enforce_paused_riskless_sleeves", False)
            or (
                not self.dry_run
                and getattr(self.executor, "client", None) is not None
                and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                and "get_market_book" not in getattr(self.executor, "__dict__", {})
            )
        )
        from src.polymarket_research.stage_c_zero_loss_velocity import (
            check_strict_pure_riskless_candidate_gate,
            is_nr0_closed_partition_graduated_unlock,
            is_verified_full_throttle_2leg_box,
            resolve_dynamic_paused_riskless_sleeves,
        )
        _ft_cert_2l = is_verified_full_throttle_2leg_box(candidate_box)
        if _ft_cert_2l:
            candidate_box = dict(candidate_box)
            candidate_box["box_type"] = box_type
            if box_type == "DOMINANCE" and str(candidate_box.get("leg_a_side") or "").strip().upper() != "UP":
                box_type = "MACRO_DOMINANCE"
                candidate_box["box_type"] = box_type
            elif box_type == "NEGRISK_CONVERT" and not candidate_box.get("convert_mode"):
                candidate_box["convert_mode"] = "NR2_PURE_CASH_CONVERT"
        _rb_snap = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
        _cached_sl_map = (getattr(self, "_d1_grad_cache", None) or (None, {}, {}))[1]
        _nav_est = float(getattr(self, "_last_known_collateral", 0.0) or 0.0)
        _eff_paused = resolve_dynamic_paused_riskless_sleeves(_rb_snap, _nav_est, _cached_sl_map)
        if _enforce_paused_rb and sleeve_src.upper() in _eff_paused:
            return {"executed": False, "reason": f"PAUSED_RISKLESS_SLEEVE:{sleeve_src}"}
        if (
            sleeve_src.upper() == "NR0_ZERO_FEE_SLATE_ARB"
            and candidate_box.get("neg_risk_augmented") is False
            and is_nr0_closed_partition_graduated_unlock(_nav_est, _rb_snap, _cached_sl_map)
        ):
            candidate_box = dict(candidate_box)
            candidate_box["nr0_graduated_unlock_verified"] = True
        _pure_rl_veto = check_strict_pure_riskless_candidate_gate(
            self, candidate_box, _rb_snap, is_maker=False
        )
        if _pure_rl_veto is not None:
            return {"executed": False, "reason": _pure_rl_veto}
        cand_asset = str(candidate_box.get("asset") or "").strip().upper()
        core_d1 = {"BTC", "ETH", "XRP"} | ({"SOL"} if RISK_CONFIG.get("enable_sol_d1_box", True) else set())
        exp_d1 = {"BNB", "DOGE", "HYPE", "ZEC", "XAU", "XAG"}
        mid_a_chk = str(candidate_box.get("leg_a_market_id") or "")
        mid_b_chk = str(candidate_box.get("leg_b_market_id") or "")
        tok_a = str(candidate_box.get("leg_a_token_id") or "")
        tok_b = str(candidate_box.get("leg_b_token_id") or "")
        if box_type == "DOMINANCE":
            if cand_asset and cand_asset not in (core_d1 | exp_d1):
                return {"executed": False, "reason": f"UNSUPPORTED_D1_ASSET:{cand_asset}"}
            corr_bps = float(candidate_box.get("corridor_bps") or 0.0)
            min_corr = 6.0 if cand_asset == "ZEC" else (4.0 if cand_asset in {"XAU", "XAG"} else (5.0 if cand_asset in exp_d1 else 3.0))
            if corr_bps < min_corr:
                return {"executed": False, "reason": f"CORRIDOR_TOO_NARROW_OR_MISSING:{corr_bps:.2f}"}
            try:
                k_a_chk = float(candidate_box.get("leg_a_strike") or 0.0)
                k_b_chk = float(candidate_box.get("leg_b_strike") or 0.0)
            except (TypeError, ValueError):
                k_a_chk = k_b_chk = 0.0
            if (
                str(candidate_box.get("leg_a_side") or "").upper() != "UP"
                or str(candidate_box.get("leg_b_side") or "").upper() != "DOWN"
                or not (0.0 < k_a_chk < k_b_chk)
                or not mid_a_chk or not mid_b_chk or mid_a_chk == mid_b_chk or not tok_a or not tok_b or tok_a == tok_b
            ):
                return {"executed": False, "reason": "INVALID_BOX_INVARIANTS"}
        elif box_type == "SINGLE_LEG_LOCK":
            opp_chk = str(candidate_box.get("leg_a_opp_token_id") or "")
            if not sleeve_src or not tok_a or not opp_chk or tok_a == opp_chk or not mid_a_chk:
                return {"executed": False, "reason": "INVALID_SINGLE_LEG_LOCK_INVARIANTS"}
        elif box_type == "NEGRISK_CONVERT":
            nrm_chk = str(candidate_box.get("neg_risk_market_id") or "").strip().lower().replace("0x", "")
            _cm_chk = str(candidate_box.get("convert_mode") or "")
            _is_nr3_chk = _cm_chk == "NR3_SYNTHETIC_ALL_YES_OVERROUND"
            _is_m1_chk = (
                _cm_chk == "NR_M1_DEAD_SEED_OVERROUND"
                and bool(candidate_box.get("nr_m1_zero_loss_verified")) is True
                and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_nr_m1_dead_seed_fanout", True))
            )
            nr_legs_chk = (candidate_box.get("yes_sell_legs") if _is_nr3_chk else candidate_box.get("no_legs")) or []
            _min_nr_legs = 1 if _is_m1_chk else 2
            if not sleeve_src or len(nrm_chk) != 64 or not isinstance(nr_legs_chk, list) or not (_min_nr_legs <= len(nr_legs_chk) <= 15):
                return {"executed": False, "reason": "INVALID_NEGRISK_CONVERT_INVARIANTS"}
        elif box_type in {"COMPLETE_SET", "LADDER_MONO", "BARRIER_MONO", "NEGRISK_2LEG", "NBA_DOMINANCE", "SPORTS_CORRIDOR", "MACRO_DOMINANCE", "COUNTING_DOMINANCE", "CROSS_BASIS_DOMINANCE"}:
            same_mkt_ok = (mid_a_chk == mid_b_chk) if box_type == "COMPLETE_SET" else (mid_a_chk != mid_b_chk)
            if not tok_a or not tok_b or tok_a == tok_b or not mid_a_chk or not mid_b_chk or not same_mkt_ok:
                return {"executed": False, "reason": "INVALID_BOX_INVARIANTS"}
        elif box_type in {"CTF_OVERROUND", "MULTI_LEG_BUNDLE"}:
            if not sleeve_src or (box_type == "CTF_OVERROUND" and not candidate_box.get("condition_id")) or (box_type == "MULTI_LEG_BUNDLE" and not (3 <= len(candidate_box.get("legs") or []) <= 12)):
                return {"executed": False, "reason": "INVALID_SPECIAL_BOX_INVARIANTS"}
        else:
            return {"executed": False, "reason": f"UNSUPPORTED_BOX_TYPE:{box_type}"}
        if not self.dry_run:
            if not getattr(self, "_startup_reconciled", False):
                return {"executed": False, "reason": "STARTUP_NOT_RECONCILED"}
            halt_rs = self._global_halt_reasons()
            if halt_rs:
                return {"executed": False, "reason": f"GLOBAL_HALT:{halt_rs[0]}"}
            recon_m = self._reconciling_market_ids()
            nr_reconciling = box_type == "NEGRISK_CONVERT" and any(
                str(lg.get("market_id") or "") in recon_m
                for lg in (candidate_box.get("no_legs") or [])
                if isinstance(lg, dict) and lg.get("market_id")
            )
            if mid_a_chk in recon_m or (mid_b_chk and mid_b_chk in recon_m) or nr_reconciling:
                return {"executed": False, "reason": "MARKET_RECONCILING"}
        from src.polymarket_research.riskless_protocol_v2_expansion import is_post_expiry_uma_frozen_lock
        now_res_chk = time.time()
        _supervised_terminal_resid_statuses = {
            "TERMINAL_UNWIND_FAILED_SUPERVISED",
            "SUB_MINIMUM_LOT_SUPERVISED_HOLD",
            "DETERMINISTIC_TERMINAL_HOLD",
            "EXIT_RECOVERY_REQUIRED",
            "HOLD_TO_MATURITY_LOCK",
            "AWAITING_REDEMPTION",
        }
        for p_act in self.active_positions.values():
            if position_is_settlement_receivable(p_act) or is_post_expiry_uma_frozen_lock(p_act, now_res_chk):
                continue
            _ex_st_act = str(p_act.get("exit_order_status") or "")
            if _ex_st_act in ("UNWIND_RETRY_REQUIRED", "UNWIND_EXECUTION_OUTCOME_UNKNOWN", "PARTIAL_UNWIND_REMAINING"):
                return {"executed": False, "reason": "UNHEDGED_BOX_RESIDUAL_ACTIVE"}
            is_box_p = "BOX" in str(p_act.get("sleeve") or "").upper() or bool(p_act.get("box_id"))
            if (
                is_box_p
                and not (p_act.get("is_dominance_box") or p_act.get("is_single_leg_lock"))
                and _ex_st_act not in _supervised_terminal_resid_statuses
            ):
                return {"executed": False, "reason": "UNHEDGED_BOX_RESIDUAL_ACTIVE"}
        now_ts = time.time()
        active_box_ids = self._active_box_ids()
        _rcfg_b1 = getattr(self, "risk_config", None) or RISK_CONFIG
        max_conc_boxes = int(_rcfg_b1.get("max_concurrent_d1_boxes", 4))
        max_tot_slots = int(_rcfg_b1.get("max_total_portfolio_slots", 4))
        if self._is_v5_unleashed_active():
            _gsn = GLOBAL_GOVERNANCE_MANAGER.snapshot
            max_conc_boxes = int(_gsn.get("riskless_boxes", {}).get("max_concurrent_riskless_boxes", 10))
            max_tot_slots = int(_gsn.get("sizing_tiers", {}).get("max_total_slots", 12))
        if len(active_box_ids) >= max_conc_boxes or (not self.dry_run and (len(active_box_ids) + len(self._risk_bearing_positions())) >= max_tot_slots):
            return {"executed": False, "reason": "MAX_CONCURRENT_BOXES_REACHED"}
        cand_exp_slot = float(candidate_box.get("expiry_ts") or 0.0)
        if box_type not in {"DOMINANCE", "NEGRISK_CONVERT", "CTF_OVERROUND"} and max_conc_boxes >= 2 and cand_exp_slot > 0.0 and (cand_exp_slot - now_ts) > 3600.0:
            if len(active_box_ids) >= (max_conc_boxes - 1):
                return {"executed": False, "reason": "INTRADAY_D1_SLOT_RESERVED"}
        dedupe_k = str(candidate_box.get("dedupe_key") or "")
        pair_dedupe_k = str(
            candidate_box.get("pair_dedupe_key")
            or (
                f"BOND1_{mid_a_chk}"
                if sleeve_src in {"BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"} and mid_a_chk
                else ""
            )
        )
        seen_boxes = self.__dict__.setdefault("_seen_d1_box_keys", set())
        _dedupe_mids = [mid_a_chk, mid_b_chk] if (mid_a_chk or mid_b_chk) else [
            str(lg.get("market_id") or "")
            for lg in (candidate_box.get("no_legs") or candidate_box.get("legs") or [])
            if isinstance(lg, dict) and lg.get("market_id")
        ]
        from src.polymarket_research.riskless_protocol_v2_expansion import is_d1_dedupe_blocked
        if is_d1_dedupe_blocked(self, dedupe_k, pair_dedupe_k, _dedupe_mids, now_ts):
            return {"executed": False, "reason": "ALREADY_EXECUTED_PAIR"}
        retry_cd = self.__dict__.setdefault("_d1_retry_cooldown_until", {})
        if dedupe_k and float(retry_cd.get(dedupe_k, 0.0) or 0.0) > now_ts:
            return {"executed": False, "reason": "RETRY_COOLDOWN_10S"}
        if cand_asset:
            leg_outs_12h = [
                p for p in getattr(self, "closed_positions", [])
                if str(p.get("asset") or "").upper() == cand_asset
                and (now_ts - float(p.get("exit_ts") or p.get("exit_time_unix") or p.get("entry_ts") or 0.0)) <= 43200.0
                and (
                    "LEGGED_OUT" in str(p.get("close_reason") or "").upper()
                    or "LEGGED_OUT" in str(p.get("sleeve") or "").upper()
                    or "_LEG_RESID" in str(p.get("trade_id") or "")
                    or "_UNWRESID_" in str(p.get("trade_id") or "")
                    or bool(p.get("is_legged_out_residual"))
                    or str(p.get("box_type") or "").upper() in {"MULTI_LEG_RESIDUAL", "CTF_OVERROUND_RESIDUAL"}
                )
            ]
            if len(leg_outs_12h) >= 2 or sum(float(p.get("net_pnl_usd") or 0.0) for p in leg_outs_12h) <= -2.50:
                return {"executed": False, "reason": f"ASSET_LEGGING_COOLDOWN:{cand_asset}"}
        try:
            from src.polymarket_research.stage_c_zero_loss_velocity import load_alpha124_graduation_maps_with_lkg_cache

            by_sl_map, by_da_map, _a124_err_d1 = load_alpha124_graduation_maps_with_lkg_cache(
                self,
                DATA_DIR,
                PIPELINE_ROOT,
                json_loads_fn=_json_loads,
                stale_reason="ALPHA124_STATE_STALE",
                missing_reason="NO_ALPHA124_STATE",
            )
            if _a124_err_d1 is not None or by_sl_map is None or by_da_map is None:
                if (
                    _ft_cert_2l
                    and getattr(self, "_d1_grad_cache", "UNSET") is not None
                    and (now_ts - float(candidate_box.get("ts_unix") or now_ts)) <= 86400.0
                ):
                    by_sl_map, by_da_map, _a124_err_d1 = {}, {}, None
                else:
                    return {"executed": False, "reason": _a124_err_d1 or "NO_ALPHA124_STATE"}

            def _grad8(rec: Dict[str, Any]) -> bool:
                raw_p = rec.get("realized_pnl_t1000_usd", rec.get("realized_pnl_usd", 0.0))
                adj_pnl = rec.get("legging_adjusted_pnl_t1000_usd", raw_p)
                return bool(
                    int(rec.get("closed", 0) or 0) >= 8
                    and float(rec.get("win_rate_pct", 0.0) or 0.0) >= 100.0
                    and float(raw_p or 0.0) > 0.0
                    and float(adj_pnl or 0.0) > 0.0
                )

            _c_legs_fr = candidate_box.get("legs") or candidate_box.get("no_legs") or []
            fr_a = (
                float(candidate_box["leg_a_fee_rate"])
                if candidate_box.get("leg_a_fee_rate") is not None
                else (max((float(x.get("fee_rate") or 0.0) for x in _c_legs_fr if isinstance(x, dict)), default=0.07) if _c_legs_fr else 0.07)
            )
            fr_b = (
                float(candidate_box["leg_b_fee_rate"])
                if candidate_box.get("leg_b_fee_rate") is not None
                else (0.0 if box_type in {"SINGLE_LEG_LOCK", "MULTI_LEG_BUNDLE", "CTF_OVERROUND"} else fr_a)
            )
            zero_fee_box = (fr_a == 0.0) if box_type == "SINGLE_LEG_LOCK" else (max(fr_a, fr_b) == 0.0)
            _rb_gov_m = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
            _zf1_cap = round(1.0 - max(0.0010, float(_rb_gov_m.get("zerofee1_min_net_edge_bps", 15.0) or 15.0) / 10000.0), 4)
            _sig_m = getattr(self.executor, "signature_type", None)
            _merge_wallet_ok = (
                (3 if _sig_m is None else int(_sig_m)) != 3
                or bool(os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY") or os.getenv("PM_ENABLE_ONCHAIN_MERGE", "0") == "1")
                or self.dry_run
                or hasattr(getattr(self.executor, "client", None), "_mock_children")
            )
            _cid_ca = str(candidate_box.get("leg_a_condition_id") or "").strip()
            _zf_c1_merge_ok = (
                box_type == "COMPLETE_SET"
                and zero_fee_box
                and bool(candidate_box.get("leg_a_neg_risk")) == bool(candidate_box.get("leg_b_neg_risk"))
                and bool(_cid_ca)
                and _cid_ca == str(candidate_box.get("leg_b_condition_id") or "").strip()
                and bool(_rb_gov_m.get("enable_zerofee1_mergeable_sweeper", True))
                and bool(_rb_gov_m.get("enable_c1_gasless_batch_merge", True))
                and (_merge_wallet_ok or (float(candidate_box.get("expiry_ts") or 0.0) - now_ts) <= 86400.0)
            )
            own_grad = True
            own_asset_grad = True
            from src.polymarket_research.riskless_protocol_v2_expansion import PROTOCOL_V2_MATH_SLEEVES
            _v3_7d = {"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG", "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX", "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX", "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION"}
            _v3_mkr_clinch = {"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "MKR_REWARD_LOCKED_CARRY"}
            _v3_g8 = _v3_7d | PROTOCOL_V2_MATH_SLEEVES | _v3_mkr_clinch | {"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH", "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR", "AFF1_FROZEN_SUBPERIOD_COLLAPSE", "SOC2_EXACT_SCORE_2D_LATTICE", "NFL_PRP1_MILESTONE_AND_MAX_LOCKS", "SUM1_FRECHET_SUM_TRIANGLES", "B3_BARRIER_MONO_BOX", "D2_12PM_BINANCE_BOX", "GAS1_AAA_GASOLINE_LOCK", "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK", "W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK", "SP2_NBA_ENDGAME_LOCK", "U1_DAILY_UPDOWN_LOCK", "CM_B2_PYTH_SESSION_NO_LOCK", "CM_U1_PYTH_CLOSE_LOCK"}
            if box_type == "DOMINANCE":
                d1_core_ok = _grad8(by_sl_map.get("D1_SAME_ORACLE_DOMINANCE_BOX") or {})
                d1_quiet_ok = sleeve_src == "D1_QUIET_BOOK_BOX" and _grad8(by_sl_map.get("D1_QUIET_BOOK_BOX") or {})
                if not (d1_core_ok or d1_quiet_ok or _ft_cert_2l):
                    return {"executed": False, "reason": "D1_NOT_YET_8_OF_8_GRADUATED"}
                if cand_asset in exp_d1:
                    da_rec = by_da_map.get(cand_asset) or {}
                    own_asset_grad = _grad8(da_rec)
                    exp_bridge_ok = bool((getattr(self, "risk_config", None) or RISK_CONFIG).get("enable_exp_d1_bridge", True)) and int(da_rec.get("losses", 0) or 0) == 0 and float(da_rec.get("legging_adjusted_pnl_t1000_usd", 0.0) or 0.0) >= 0.0
                    if not (own_asset_grad or exp_bridge_ok or _ft_cert_2l):
                        return {"executed": False, "reason": f"EXPANSION_ASSET_NOT_YET_8_OF_8_GRADUATED:{cand_asset}"}
            else:
                sl_rec = by_sl_map.get(sleeve_src) or {}
                b1_rec_inh = by_sl_map.get("BOND1_UMA_RESOLUTION_CARRY") or {}
                no_loss = int(sl_rec.get("losses", 0) or 0) == 0 and (
                    sleeve_src != "UMA_READY1_LIVENESS_PRIORITY" or int(b1_rec_inh.get("losses", 0) or 0) == 0
                )
                d1_g8 = _grad8(by_sl_map.get("D1_SAME_ORACLE_DOMINANCE_BOX") or {})
                _prob_sll_sleeves = {"W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK", "W_SOLAR1_POST_2351_LOCK", "SP2_NBA_ENDGAME_LOCK", "U1_DAILY_UPDOWN_LOCK", "CM_B2_PYTH_SESSION_NO_LOCK", "CM_U1_PYTH_CLOSE_LOCK"}
                _ro_sll = bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {}).get("riskless_only_mode", False)) and not self.dry_run
                _pm_raw_sll = float(candidate_box.get("p_model") or 0.0)
                _prob_sll_ok = not (_ro_sll and box_type == "SINGLE_LEG_LOCK" and sleeve_src in _prob_sll_sleeves) or _pm_raw_sll >= 0.999
                own_grad = (
                    (_grad8(sl_rec) or (sleeve_src == "UMA_READY1_LIVENESS_PRIORITY" and _grad8(b1_rec_inh)))
                    and no_loss
                    and _prob_sll_ok
                )
                cand_rem_zf = float(candidate_box.get("expiry_ts") or 0.0) - now_ts
                c_net = float(candidate_box.get("box_cost_net") or 1.0)
                _2l_t = {"COMPLETE_SET", "BARRIER_MONO", "NEGRISK_2LEG", "NBA_DOMINANCE", "SPORTS_CORRIDOR", "MACRO_DOMINANCE", "COUNTING_DOMINANCE", "LADDER_MONO", "CROSS_BASIS_DOMINANCE"}
                cond1_short_ok = sleeve_src == "COND1_MACRO_PARTITION_BOX" and (
                    (own_grad and 0.0 < cand_rem_zf <= 172800.0 and c_net <= 0.992)
                    or (0.0 < cand_rem_zf <= 108000.0 and c_net <= 0.985)
                    or _ft_cert_2l
                )
                fee_2l_ok = no_loss and (
                    (sleeve_src == "C1_BINARY_COMPLETE_SET" and bool(candidate_box.get("recorder_fast_ipc")) and c_net <= 0.989 and 0.0 < cand_rem_zf <= 86400.0)
                    or (
                        c_net <= 0.988
                        and (
                            (sleeve_src == "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX" and 0.0 < cand_rem_zf <= 21600.0)
                            or (sleeve_src in {"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX", "M3_LADDER_MONO_BOX"} and 0.0 < cand_rem_zf <= 86400.0)
                        )
                    )
                )
                _2l_ok = box_type in _2l_t and sleeve_src != "NR_CONV_NO_BASKET_ARB" and (sleeve_src != "COND1_MACRO_PARTITION_BOX" or cond1_short_ok)
                d1_zf_bridge = _2l_ok and (zero_fee_box or fee_2l_ok) and sleeve_src not in _v3_g8 and d1_g8
                _v3_max_rem = 604800.0 if sleeve_src in _v3_7d else 129600.0
                _v2_sp_ok = (box_type in {"CTF_OVERROUND", "MULTI_LEG_BUNDLE"} or _zf_c1_merge_ok) and bool(_rb_gov_m.get("enable_graduated_d1_box", True))
                _v3_cfg_ok = bool(_rb_gov_m.get("enable_ungraduated_v3_math_live", False)) if _enforce_paused_rb else (bool(_rcfg_b1.get("enable_ungraduated_v3_math_live", False)) or bool(_rb_gov_m.get("enable_ungraduated_v3_math_live", False)))
                _v3_en = (_v3_cfg_ok or _v2_sp_ok) and (not _enforce_paused_rb or sleeve_src.upper() not in {str(x).upper() for x in (_rb_gov_m.get("paused_riskless_sleeves") or [])})
                _pm_cand = float(candidate_box.get("p_model") or (0.0 if (sleeve_src in _v3_mkr_clinch or (_ro_sll and sleeve_src in _prob_sll_sleeves)) else 0.998))
                _sll_hi_tte_lim = 54000.0 if sleeve_src == "W_PRUNE1_DEAD_NO_BOND" else 14400.0
                _sll_c_cap = 0.9975 if (zero_fee_box and cand_rem_zf <= 28800.0) else ((0.995 if _pm_cand >= 0.9999 else 0.994) if (_pm_cand >= 0.999 and cand_rem_zf <= _sll_hi_tte_lim) else 0.992)
                v3_math_ok = _v3_en and not self.dry_run and self._is_v5_unleashed_active() and no_loss and d1_g8 and _prob_sll_ok and (box_type == "CTF_OVERROUND" or (_zf_c1_merge_ok and cand_rem_zf > 25.0) or 0.0 < cand_rem_zf <= _v3_max_rem) and ((_2l_ok and c_net <= (_zf1_cap if _zf_c1_merge_ok else (0.992 if zero_fee_box else 0.989))) or (box_type in {"CTF_OVERROUND", "MULTI_LEG_BUNDLE"} and c_net <= 0.9955) or (box_type == "SINGLE_LEG_LOCK" and (sleeve_src in _v3_g8 or sleeve_src.startswith("SP4_")) and _pm_cand >= (0.999 if (sleeve_src in _v3_mkr_clinch or (_ro_sll and sleeve_src in _prob_sll_sleeves)) else 0.998) and c_net <= _sll_c_cap))
                _nr_mode = str(candidate_box.get("convert_mode") or "")
                nr2_pure_cash_bridge = box_type == "NEGRISK_CONVERT" and bool(_rcfg_b1.get("enable_nr2_pure_cash_bridge", True)) and (
                    (_nr_mode in {"NR2_PURE_CASH_CONVERT", "NR2_SUBSET_LIQUID_YES_CONVERT", "NR2_SUBSET_CONVERT_FREE_TAIL", "NR4_FULL_SWEEP", "NR5_NEGATIVE_COST_FREEROLL"} and 2 <= len(candidate_box.get("no_legs") or []) <= 15)
                    or (_nr_mode == "NR3_SYNTHETIC_ALL_YES_OVERROUND" and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_nr3_synthetic_overround", True)) and 2 <= len(candidate_box.get("yes_sell_legs") or []) <= 15)
                    or (
                        _nr_mode == "NR_M1_DEAD_SEED_OVERROUND"
                        and bool(candidate_box.get("nr_m1_zero_loss_verified")) is True
                        and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_nr_m1_dead_seed_fanout", True))
                        and len(candidate_box.get("no_legs") or []) == 1
                    )
                ) and no_loss and (d1_g8 or _ft_cert_2l)
                _b1_br_rec = b1_rec_inh if (sleeve_src == "UMA_READY1_LIVENESS_PRIORITY" and int(sl_rec.get("closed", 0) or 0) == 0) else sl_rec
                bond1_live_bridge = box_type == "SINGLE_LEG_LOCK" and sleeve_src in {"BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", "UMA_READY1_LIVENESS_PRIORITY"} and bool(_rcfg_b1.get("enable_bond1_live_bridge", True)) and no_loss and float(_b1_br_rec.get("realized_pnl_t1000_usd", 0.0) or 0.0) >= 0.0 and (int(_b1_br_rec.get("closed", 0) or 0) == 0 or float(_b1_br_rec.get("win_rate_pct", 100.0) or 0.0) >= 100.0) and d1_g8
                s2_live_bridge = box_type == "SINGLE_LEG_LOCK" and sleeve_src in {"S2_EXACT_TWAP_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR"} and (bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_s2_twap_lock_live", True)) or not _enforce_paused_rb) and not self.dry_run and no_loss and float(candidate_box.get("p_model") or 0.0) >= 0.9985 and c_net <= 0.9972 and d1_g8
                ft_certified_bridge = bool(
                    _ft_cert_2l
                    and no_loss
                    and bool(_rb_gov_m.get("enable_graduated_d1_box", True))
                    and (not _enforce_paused_rb or sleeve_src.upper() not in {str(x).upper() for x in (_rb_gov_m.get("paused_riskless_sleeves") or [])})
                )
                if not (own_grad or d1_zf_bridge or v3_math_ok or nr2_pure_cash_bridge or bond1_live_bridge or s2_live_bridge or ft_certified_bridge):
                    return {"executed": False, "reason": f"SLEEVE_NOT_YET_8_OF_8_GRADUATED:{sleeve_src}"}
        except Exception as exc:
            return {"executed": False, "reason": f"STATE_READ_ERROR:{exc}"}

        inflight_lock = self.__dict__.setdefault("_d1_inflight_exec_lock", threading.Lock())
        if not inflight_lock.acquire(blocking=False):
            return {"executed": False, "reason": "BOX_EXECUTION_INFLIGHT"}
        try:
            from src.polymarket_research.stage_c_zero_loss_velocity import check_multileg_3plus_nav_and_certification_gate

            _ml3_veto = check_multileg_3plus_nav_and_certification_gate(
                self, candidate_box, GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}), now_ts=now_ts
            )
            if _ml3_veto is not None:
                return {"executed": False, "reason": _ml3_veto}
            if box_type == "SINGLE_LEG_LOCK":
                return self._finish_single_leg_lock(candidate_box, sleeve_src, tok_a, mid_a_chk, dedupe_k, retry_cd, now_ts, _rcfg_b1, own_grad=own_grad)
            if box_type == "NEGRISK_CONVERT":
                return self._finish_negrisk_convert_arb(candidate_box, sleeve_src, dedupe_k, retry_cd, now_ts, _rcfg_b1, own_grad=own_grad)
            if box_type in {"CTF_OVERROUND", "MULTI_LEG_BUNDLE"}:
                from src.polymarket_research.riskless_protocol_v2_expansion import finish_protocol_v2_special_box_sync
                return finish_protocol_v2_special_box_sync(self, candidate_box, dedupe_k, retry_cd, now_ts, _rcfg_b1, own_grad=own_grad)
            lbl_a = str(candidate_box.get("leg_a_label", "LEG_A"))
            lbl_b = str(candidate_box.get("leg_b_label", "LEG_B"))
            px_a_lim = float(candidate_box["leg_a_limit_price"])
            px_b_lim = float(candidate_box["leg_b_limit_price"])
            sh_req = float(candidate_box.get("net_paired_shares") or candidate_box.get("shares", 12.0))
            sh_a_gross = float(candidate_box.get("leg_a_gross_shares") or candidate_box.get("shares", sh_req))
            sh_b_gross = float(candidate_box.get("leg_b_gross_shares") or candidate_box.get("shares", sh_req))
            cap_net = float(candidate_box.get("max_box_cost_net", 0.995))
            fresh_box_net = float(candidate_box.get("box_cost_net") or (px_a_lim + px_b_lim))
            avail_a = candidate_box.get("leg_a_avail_shares")
            avail_b = candidate_box.get("leg_b_avail_shares")
            fe_a = float(candidate_box.get("leg_a_fee_exponent", 1.0) or 1.0)
            fe_b = float(candidate_box.get("leg_b_fee_exponent", 1.0) or 1.0)
            pre_bal_a, pre_bal_b = 0.0, 0.0

            is_live_ctf_box = (
                (not self.dry_run)
                and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
                and len(tok_a) >= 20 and tok_a.isdigit()
                and len(tok_b) >= 20 and tok_b.isdigit()
            )
            cand_ts = float(candidate_box.get("ts_unix") or now_ts)
            ipc_age_ms = round(max(0.0, (now_ts - cand_ts) * 1000.0), 2)
            pre_bal_ms, book_walk_ms = 0.0, 0.0
            if not self.dry_run and (
                not is_live_ctf_box
                or not candidate_box.get("ts_unix")
                or not candidate_box.get("expiry_ts")
                or walk_equal_shares_dominance_box is None
                or not hasattr(self.executor, "get_market_book")
            ):
                return {"executed": False, "reason": "LIVE_PRECHECK_UNAVAILABLE"}
            if is_live_ctf_box:
                exp_ts = float(candidate_box.get("expiry_ts") or 0.0)
                is_4h_box = str(candidate_box.get("leg_a_horizon") or "").lower() in ("4h", "1h") or str(candidate_box.get("leg_b_horizon") or "").lower() in ("4h", "1h")
                if box_type == "DOMINANCE":
                    max_tte_box = 900.0 if is_4h_box else 300.0
                elif sleeve_src == "COND1_MACRO_PARTITION_BOX" and not own_grad:
                    max_tte_box = 108000.0
                elif sleeve_src == "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX" or sleeve_src in _v3_7d or _ft_cert_2l:
                    max_tte_box = 604800.0
                elif box_type in {"SPORTS_CORRIDOR", "NBA_DOMINANCE"}:
                    max_tte_box = 259200.0
                elif box_type in {"NEGRISK_2LEG", "MACRO_DOMINANCE", "BARRIER_MONO"}:
                    max_tte_box = 172800.0
                elif _zf_c1_merge_ok:
                    max_tte_box = 31536000.0
                else:
                    max_tte_box = 86400.0
                _rb_ipc_cfg = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
                _max_ipc_age = (
                    float(_rb_ipc_cfg.get("ipc_candidate_max_age_sec", 60.0) or 60.0)
                    if (_ft_cert_2l or box_type != "DOMINANCE")
                    else float(_rb_ipc_cfg.get("ipc_subhourly_d1_max_age_sec", 15.0) or 15.0)
                )
                if (now_ts - cand_ts) > _max_ipc_age or (exp_ts > 0.0 and not (16.0 <= (exp_ts - now_ts) <= max_tte_box)):
                    return {"executed": False, "reason": "STALE_OR_OUTSIDE_TTE_WINDOW"}
                m_a = str(candidate_box.get("leg_a_market_id") or "")
                m_b = str(candidate_box.get("leg_b_market_id") or "")
                if m_a in {"6707502", "6707503"} or m_b in {"6707502", "6707503"}:
                    return {"executed": False, "reason": "D001_DISPUTED_KMIA_NON_INTERFERENCE"}
                from src.polymarket_research.riskless_protocol_v2_expansion import (
                    check_per_event_concentration_cap,
                    compute_d1_per_market_notional_cap,
                    compute_sll_and_carry_gatling_budget,
                    is_market_busy_for_scaling,
                    open_market_notional_usd,
                    pending_intents_cash_reserved_usd,
                    pending_intents_synced_equity_usd,
                    preempt_makers_for_instant_taker_arb,
                    sync_pending_intents_on_collateral_refresh,
                )
                _lk_c_d1 = getattr(self, "_last_known_collateral", None)
                _free_pre_d1 = (
                    max(0.0, float(_lk_c_d1) - (0.0 if self.dry_run else pending_intents_cash_reserved_usd(getattr(self, "pending_entry_intents", None))))
                    if isinstance(_lk_c_d1, (int, float)) and not isinstance(_lk_c_d1, bool)
                    else None
                )
                _force_cross_d1 = bool(not self.dry_run and (box_type == "DOMINANCE" or own_grad))
                _signaled_d1, _preempt_keys_d1 = preempt_makers_for_instant_taker_arb(
                    self,
                    reason=f"D1_BOX:{cand_asset}",
                    target_market_ids={m_a, m_b},
                    cand_net_cost=fresh_box_net,
                    free_cash_hint=_free_pre_d1,
                    target_arb_cash_usd=45.0,
                    min_fallback_cash_usd=26.0,
                    force_cross_market_when_low_cash=_force_cross_d1,
                    now_ts=now_ts,
                )
                _ev_loop_ref = getattr(self, "_main_loop", None)
                _same_ev_thr = _ev_loop_ref is not None and getattr(_ev_loop_ref, "_thread_id", None) == threading.get_ident()
                if _signaled_d1 > 0 and not _same_ev_thr:
                    for _ in range(60):
                        if not any(
                            isinstance(_i_p, dict)
                            and _i_p.get("live_maker_anchor_inflight")
                            and (
                                str(_i_p.get("inflight_key") or "") in _preempt_keys_d1
                                if _preempt_keys_d1
                                else str(_i_p.get("market_id") or "") in {m_a, m_b}
                            )
                            for _i_p in getattr(self, "pending_entry_intents", {}).values()
                        ):
                            break
                        time.sleep(0.015)
                if (m_a and is_market_busy_for_scaling(self, m_a)) or (m_b and is_market_busy_for_scaling(self, m_b)):
                    return {"executed": False, "reason": "MARKET_ALREADY_OCCUPIED"}
                _prev_c_d1 = getattr(self, "_last_known_collateral", None)
                collat = None if (_signaled_d1 > 0 and not self.dry_run) else _prev_c_d1
                if collat is None:
                    try:
                        collat = self.executor.get_collateral_balance()
                        if isinstance(collat, (int, float)) and not isinstance(collat, bool) and math.isfinite(float(collat)) and float(collat) >= 0.0:
                            self._last_known_collateral = float(collat)
                            sync_pending_intents_on_collateral_refresh(self, _prev_c_d1, float(collat))
                    except Exception:
                        collat = None
                _pend_d1 = getattr(self, "pending_entry_intents", None)
                inflight_intent_usd = pending_intents_cash_reserved_usd(_pend_d1)
                collat_f = max(0.0, float(collat or 0.0) - inflight_intent_usd)
                rem_tte_s = max(1.0, exp_ts - now_ts) if exp_ts > 0.0 else 0.0
                _gov_rb_d1r = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
                _d1_clip_rec = min(26.0, max(12.0, float(_gov_rb_d1r.get("gatling_base_clip_d1_usd", 22.0) or 22.0)))
                if (
                    not self.dry_run
                    and collat_f < _d1_clip_rec - 0.50
                    and fresh_box_net <= 0.98005
                    and getattr(self.executor, "client", None) is not None
                    and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                    and bool(_gov_rb_d1r.get("enable_zero_loss_open_carry_velocity_recycle", True))
                ):
                    from src.polymarket_research.stage_c_zero_loss_velocity import recycle_open_zero_loss_carry_for_fast_arb
                    _rec_c = recycle_open_zero_loss_carry_for_fast_arb(
                        self,
                        needed_cash_gap_usd=max(0.0, _d1_clip_rec - collat_f),
                        challenger_net_cost=fresh_box_net,
                        challenger_rem_tte_sec=rem_tte_s,
                        challenger_sleeve=sleeve_src,
                        exclude_market_ids={m_a, m_b},
                        now_ts=now_ts,
                    )
                    if _rec_c.get("recycled_count", 0) > 0:
                        collat = getattr(self, "_last_known_collateral", collat)
                        collat_f = max(collat_f + float(_rec_c.get("freed_cash_usd", 0.0)), max(0.0, float(collat or 0.0) - inflight_intent_usd))
                early_exp_ts = min(
                    float(candidate_box.get("leg_a_expiry_ts") or exp_ts),
                    float(candidate_box.get("leg_b_expiry_ts") or exp_ts),
                )
                vel_tte_s = (
                    max(1.0, early_exp_ts - now_ts)
                    if (sleeve_src == "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX" and early_exp_ts > 0.0)
                    else rem_tte_s
                )
                if box_type != "DOMINANCE" and rem_tte_s > 0.0:
                    fast_recycle_sl = zero_fee_box and (
                        sleeve_src in {
                            "COND1_MACRO_PARTITION_BOX",
                            "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
                            "M3_LADDER_MONO_BOX",
                            "N1_NEGRISK_CROSS_BOX",
                            "TW1_COUNTING_TRUNCATION_AND_BOX",
                            "FED1_CENTRAL_BANK_LP_BOX",
                            "C1_BINARY_COMPLETE_SET",
                            "NR0_ZERO_FEE_SLATE_ARB",
                            "FT_DUP1_EXACT_CROSS_EVENT_BOX",
                            "FT_STRIKE1_VERIFIED_DOMINANCE_BOX",
                            "XV_SUBSET_NO_2LEG_BOX",
                        }
                        or (
                            sleeve_src == "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"
                            and (own_grad or _ft_cert_2l)
                            and vel_tte_s <= 129600.0
                        )
                        or (
                            sleeve_src == "CM_B3_PYTH_BARRIER_BOX"
                            and vel_tte_s <= 43200.0
                            and fresh_box_net <= 0.988
                        )
                    )
                    from src.polymarket_research.riskless_protocol_v2_expansion import is_disputed_or_frozen_uma_position
                    _liq_eq_d1 = collat_f + inflight_intent_usd + sum(
                        float(_p_lq.get("notional_usd", 0.0) or 0.0)
                        for _p_lq in self.active_positions.values()
                        if isinstance(_p_lq, dict)
                        and not position_is_settlement_receivable(_p_lq)
                        and not is_disputed_or_frozen_uma_position(_p_lq, now_ts)
                    )
                    _prev_t_d1 = getattr(self, "_current_equity_tier", None) or "UNLEASHED_LAUNCH"
                    vel_ok, vel_reason = passes_capital_velocity_hurdle(
                        collat_usd=_liq_eq_d1, rem_tte_sec=vel_tte_s, box_cost_net=fresh_box_net,
                        box_type=box_type, sleeve_src=sleeve_src, fast_recycle_eligible=fast_recycle_sl,
                        merge_wallet_ok=bool(_zf_c1_merge_ok and _merge_wallet_ok),
                        previous_tier=_prev_t_d1,
                    )
                    if not vel_ok:
                        return {"executed": False, "reason": vel_reason}
                from src.polymarket_research.riskless_machine_gun_engine import is_soc2_exhaustive_lattice_safe, is_sports_dead_ball_safe
                from src.polymarket_research.riskless_protocol_v2_expansion import is_disputed_or_frozen_uma_position
                if not is_soc2_exhaustive_lattice_safe(candidate_box):
                    return {"executed": False, "reason": "SOC2_NON_EXHAUSTIVE_QUARANTINED"}
                if box_type in {"SPORTS_CORRIDOR", "NBA_DOMINANCE"} and not is_sports_dead_ball_safe(candidate_box):
                    return {"executed": False, "reason": "LIVE_BALL_SPORTS_ORACLE_LAG_VETO"}
                cur_open_exp = sum(
                    float(p.get("notional_usd", 0.0) or 0.0)
                    for p in self.active_positions.values()
                    if not position_is_settlement_receivable(p)
                    and not is_disputed_or_frozen_uma_position(p, now_ts)
                ) + inflight_intent_usd + pending_intents_synced_equity_usd(_pend_d1)
                if self._is_v5_unleashed_active():
                    _tot_eq_box = collat_f + cur_open_exp
                    _v5_box_prof = get_unleashed_v5_tier_profile(
                        _tot_eq_box, previous_tier=getattr(self, "_current_equity_tier", None) or "UNLEASHED_LAUNCH"
                    )
                    d1_pct = float(_v5_box_prof["d1_free_cash_pct"])
                    asset_cap = {"BTC": 250.0, "ETH": 150.0, "SOL": 65.0, "XRP": 65.0, "BNB": 35.0, "HYPE": 25.0, "DOGE": 25.0, "ZEC": 10.0, "XAU": 25.0, "XAG": 25.0}.get(cand_asset, 45.0)
                    _tier_nm_box = str(_v5_box_prof.get("tier") or "")
                    _tier_single_box_cap = (
                        60.0
                        if _tier_nm_box == "UNLEASHED_LAUNCH"
                        else (120.0 if _tier_nm_box == "HYPER_GROWTH" else 150.0)
                    )
                    if not (sleeve_src == "D1_SAME_ORACLE_DOMINANCE_BOX" and rem_tte_s <= 3600.0 and fresh_box_net <= 0.975):
                        asset_cap = min(asset_cap, _tier_single_box_cap)
                    if cand_asset in exp_d1 and not own_asset_grad:
                        asset_cap = min(asset_cap, 20.0)
                    port_headroom = max(0.0, max(float(self.max_exposure), _tot_eq_box * 0.96) - cur_open_exp)
                    bridged_zf_cap = min(float(_v5_box_prof["bridged_zero_fee_cap_usd"]), _tier_single_box_cap)
                    if box_type != "DOMINANCE" and not own_grad:
                        _ungrad_single_cap = max(12.0, _tot_eq_box * 0.28) if _tier_nm_box == "UNLEASHED_LAUNCH" else max(20.0, _tot_eq_box * 0.25)
                        bridged_zf_cap = min(bridged_zf_cap, _ungrad_single_cap)
                        if not self.dry_run:
                            from src.polymarket_research.riskless_protocol_v2_expansion import is_post_expiry_uma_frozen_lock

                            _cur_ungrad_exp = sum(
                                float(p.get("notional_usd", 0.0) or 0.0)
                                for p in self.active_positions.values()
                                if not position_is_settlement_receivable(p)
                                and not is_post_expiry_uma_frozen_lock(p, now_ts)
                                and str(p.get("box_type") or "DOMINANCE") != "DOMINANCE"
                                and not _grad8(by_sl_map.get(str(p.get("sleeve") or "")) or {})
                            )
                            bridged_zf_cap = min(bridged_zf_cap, max(0.0, max(12.0, _tot_eq_box * 0.30) - _cur_ungrad_exp))
                    box_reserve_u = float(_v5_box_prof["box_collateral_reserve_usd"])
                else:
                    d1_pct = (
                        0.32
                        if collat_f >= 160.0
                        else float(RISK_CONFIG.get("d1_box_bankroll_pct", 0.25))
                    )
                    asset_cap = {"BTC": 150.0, "ETH": 75.0, "SOL": 16.5, "XRP": 16.5, "BNB": 22.0, "HYPE": 15.0, "DOGE": 15.0, "ZEC": 10.0, "XAU": 25.0, "XAG": 25.0}.get(cand_asset, 25.0)
                    if cand_asset in exp_d1 and not own_asset_grad:
                        asset_cap = min(asset_cap, 12.0)
                    port_headroom = max(0.0, max(float(self.max_exposure), collat_f * 0.55) - cur_open_exp)
                    bridged_zf_cap = 12.0 if sleeve_src == "COND1_MACRO_PARTITION_BOX" else 16.50
                    box_reserve_u = float(RISK_CONFIG.get("d1_box_collateral_reserve_usd", 16.50))
                target_budget = min(
                    float(RISK_CONFIG.get("d1_box_max_budget_usd", 250.0)),
                    bridged_zf_cap if (box_type != "DOMINANCE" and not own_grad) else asset_cap,
                    max(0.0, collat_f - box_reserve_u),
                    collat_f * d1_pct,
                    port_headroom,
                )
                target_budget = compute_sll_and_carry_gatling_budget(
                    self, target_budget, collat_f, cur_open_exp, box_type, sleeve_src, own_grad,
                    GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes"),
                    rem_tte_sec=rem_tte_s, now_ts=now_ts,
                    cap_usd=min(float(RISK_CONFIG.get("d1_box_max_budget_usd", 250.0)), asset_cap if box_type == "DOMINANCE" else 250.0),
                )
                existing_pair_u = max(
                    open_market_notional_usd(self, [m_a]) if m_a else 0.0,
                    open_market_notional_usd(self, [m_b]) if m_b else 0.0,
                )
                if existing_pair_u > 0.0:
                    target_budget = min(target_budget, max(0.0, compute_d1_per_market_notional_cap(self) - existing_pair_u))
                if box_type != "DOMINANCE":
                    _evt_ok_2l, _evt_rsn_2l, _evt_rem_2l, _ = check_per_event_concentration_cap(self, candidate_box, market_ids=[m_a, m_b], now_ts=now_ts, min_headroom_usd=4.50)
                    if not _evt_ok_2l:
                        return {"executed": False, "reason": _evt_rsn_2l}
                    target_budget = min(target_budget, _evt_rem_2l)
                if target_budget < 4.50:
                    return {"executed": False, "reason": "INSUFFICIENT_BOX_COLLATERAL_HEADROOM"}
                use_mock_d1_tk = self.dry_run or hasattr(getattr(self.executor, "client", None), "_mock_children")
                for t_id, c_id, nr_raw, fr_f, fe_f, tk_sz_raw in (
                    (tok_a, str(candidate_box.get("leg_a_condition_id") or ""), candidate_box.get("leg_a_neg_risk"), fr_a, fe_a, candidate_box.get("leg_a_tick_size") if use_mock_d1_tk else None),
                    (tok_b, str(candidate_box.get("leg_b_condition_id") or ""), candidate_box.get("leg_b_neg_risk"), fr_b, fe_b, candidate_box.get("leg_b_tick_size") if use_mock_d1_tk else None),
                ):
                    if c_id and isinstance(nr_raw, bool) and hasattr(self.executor, "prewarm_token_market_cache"):
                        self.executor.prewarm_token_market_cache(
                            token_id=t_id, tick_size=tk_sz_raw, neg_risk=nr_raw,
                            fee_rate_bps=int(round(fr_f * 10000)), condition_id=c_id, fee_rate=fr_f, fee_exponent=fe_f,
                        )
                hot_pool = _get_hot_io_pool()
                pre_bal_cache = self.__dict__.setdefault("_d1_clean_pre_bal_cache", {})
                use_bal_cache = "_wallet_token_balance" not in self.__dict__
                now_pb = time.time()
                uws_d1 = getattr(self.executor, "_user_ws_cache", None) if use_bal_cache else None
                uws_d1_ok = bool(uws_d1 is not None and uws_d1.is_healthy())
                bal_ttl = 1800.0 if uws_d1_ok else 360.0
                prior_toks = (
                    {p.get("token_id") for p in self.active_positions.values()}
                    | {i.get("token_id") for i in getattr(self, "pending_entry_intents", {}).values()}
                    | {
                        p.get("token_id")
                        for p in getattr(self, "closed_positions", [])[-20:]
                        if float(p.get("remaining_shares", 0.0) or 0.0) > 0.01 or not uws_d1_ok
                    }
                    | {
                        k
                        for k, u in (self.__dict__.get("_d1_dirty_token_until") or {}).items()
                        if float(u or 0.0) > now_pb
                    }
                ) if use_bal_cache else {tok_a, tok_b}
                c_ba = pre_bal_cache.get(tok_a) if use_bal_cache else None
                c_bb = pre_bal_cache.get(tok_b) if use_bal_cache else None
                if c_ba is not None and uws_d1_ok and uws_d1.has_token_fill_since(tok_a, c_ba[1]):
                    c_ba = None
                if c_bb is not None and uws_d1_ok and uws_d1.has_token_fill_since(tok_b, c_bb[1]):
                    c_bb = None
                if use_bal_cache and tok_a not in prior_toks and c_ba is None and not (uws_d1_ok and uws_d1.has_token_fill_since(tok_a, now_pb - 300.0)):
                    c_ba = (0.0, now_pb)
                if use_bal_cache and tok_b not in prior_toks and c_bb is None and not (uws_d1_ok and uws_d1.has_token_fill_since(tok_b, now_pb - 300.0)):
                    c_bb = (0.0, now_pb)
                t_pb0 = time.perf_counter_ns()
                fb_a = None if (c_ba is not None and (now_pb - c_ba[1]) <= bal_ttl) else hot_pool.submit(self._wallet_token_balance, tok_a)
                fb_b = None if (c_bb is not None and (now_pb - c_bb[1]) <= bal_ttl) else hot_pool.submit(self._wallet_token_balance, tok_b)
                b_a = c_ba[0] if fb_a is None else fb_a.result()[0]
                b_b = c_bb[0] if fb_b is None else fb_b.result()[0]
                pre_bal_ms = round((time.perf_counter_ns() - t_pb0) / 1_000_000.0, 2)
                pre_bal_a = float(b_a or 0.0)
                pre_bal_b = float(b_b or 0.0)
                if use_bal_cache:
                    now_pb_done = time.time()
                    pre_bal_cache[tok_a] = (pre_bal_a, now_pb_done)
                    pre_bal_cache[tok_b] = (pre_bal_b, now_pb_done)
                if walk_equal_shares_dominance_box is not None and hasattr(self.executor, "get_market_book"):
                    t_bk0 = time.perf_counter_ns()
                    opp_a = str(candidate_box.get("leg_a_opp_token_id") or "").strip()
                    opp_b = str(candidate_box.get("leg_b_opp_token_id") or "").strip()
                    cid_a_opp = str(candidate_box.get("leg_a_condition_id") or "").strip()
                    cid_b_opp = str(candidate_box.get("leg_b_condition_id") or "").strip()
                    _same_bin_mkt = bool(((m_a and m_a == m_b) or (cid_a_opp and cid_a_opp == cid_b_opp)) and tok_a != tok_b)
                    if _same_bin_mkt:
                        opp_a = opp_a or tok_b
                        opp_b = opp_b or tok_a
                    need_sep_opp = box_type != "COMPLETE_SET" and not _same_bin_mkt
                    if need_sep_opp:
                        from src.polymarket_research.riskless_protocol_v2_expansion import resolve_missing_opp_token_id
                        if not (len(opp_a) >= 20 and opp_a.isdigit()):
                            _res_oa = resolve_missing_opp_token_id(self, m_a, cid_a_opp, tok_a)
                            if _res_oa:
                                opp_a = _res_oa
                                candidate_box["leg_a_opp_token_id"] = opp_a
                        if not (len(opp_b) >= 20 and opp_b.isdigit()):
                            _res_ob = resolve_missing_opp_token_id(self, m_b, cid_b_opp, tok_b)
                            if _res_ob:
                                opp_b = _res_ob
                                candidate_box["leg_b_opp_token_id"] = opp_b
                        if not (len(opp_a) >= 20 and opp_a.isdigit() and len(opp_b) >= 20 and opp_b.isdigit()):
                            return {"executed": False, "reason": "ANTI_BOX_COMPLEMENT_UNVERIFIED:MISSING_OPP_TOKENS"}
                    custom_book_fn = "get_market_book" in getattr(self.executor, "__dict__", {})
                    ws_bks = candidate_box.get("ws_books") if not custom_book_fn else None
                    ws_bks_ts = float(candidate_box.get("ws_books_ts") or 0.0)
                    use_ws_bks = (
                        isinstance(ws_bks, dict)
                        and (time.time() - ws_bks_ts) <= 0.65
                        and isinstance(ws_bks.get(tok_a), dict)
                        and isinstance(ws_bks.get(tok_b), dict)
                        and (not need_sep_opp or (isinstance(ws_bks.get(opp_a), dict) and isinstance(ws_bks.get(opp_b), dict)))
                    )
                    if use_ws_bks:
                        bk_a = ws_bks[tok_a]
                        bk_b = ws_bks[tok_b]
                        bk_oa_pre = bk_b if not need_sep_opp else ws_bks[opp_a]
                        bk_ob_pre = bk_a if not need_sep_opp else ws_bks[opp_b]
                    elif not custom_book_fn and hasattr(self.executor, "get_market_books_batch"):
                        req_toks = [tok_a, tok_b] + ([opp_a, opp_b] if need_sep_opp else [])
                        batch_map = self.executor.get_market_books_batch(req_toks)
                        bk_a = batch_map.get(tok_a) or {}
                        bk_b = batch_map.get(tok_b) or {}
                        bk_oa_pre = bk_b if not need_sep_opp else (batch_map.get(opp_a) or {})
                        bk_ob_pre = bk_a if not need_sep_opp else (batch_map.get(opp_b) or {})
                    else:
                        fk_a = hot_pool.submit(self.executor.get_market_book, tok_a)
                        fk_b = hot_pool.submit(self.executor.get_market_book, tok_b)
                        fk_oa = hot_pool.submit(self.executor.get_market_book, opp_a) if need_sep_opp else None
                        fk_ob = hot_pool.submit(self.executor.get_market_book, opp_b) if need_sep_opp else None
                        bk_a = fk_a.result() or {}
                        bk_b = fk_b.result() or {}
                        bk_oa_pre = bk_b if not need_sep_opp else (fk_oa.result() or {})
                        bk_ob_pre = bk_a if not need_sep_opp else (fk_ob.result() or {})
                    try:
                        bk_oa = bk_oa_pre
                        bk_ob = bk_ob_pre
                        b_oa = bk_oa.get("bids") or []
                        b_ob = bk_ob.get("bids") or []
                        a_oa = bk_oa.get("asks") or []
                        a_ob = bk_ob.get("asks") or []
                        bid_oa_v = max((float(x["price"] if isinstance(x, dict) else x[0]) for x in b_oa), default=0.0)
                        bid_ob_v = max((float(x["price"] if isinstance(x, dict) else x[0]) for x in b_ob), default=0.0)
                        ask_oa_v = min((float(x["price"] if isinstance(x, dict) else x[0]) for x in a_oa), default=0.0)
                        ask_ob_v = min((float(x["price"] if isinstance(x, dict) else x[0]) for x in a_ob), default=0.0)
                        oa_ok = bid_oa_v > 0.0 or (0.0 < ask_oa_v <= 0.12)
                        ob_ok = bid_ob_v > 0.0 or (0.0 < ask_ob_v <= 0.12)
                        if not (oa_ok and ob_ok) or (bid_oa_v <= 0.0 and bid_ob_v <= 0.0):
                            return {"executed": False, "reason": "ANTI_BOX_COMPLEMENT_UNVERIFIED:EMPTY_OPP_BOOK"}
                        opp_sum = bid_oa_v + bid_ob_v
                        opp_ub_sum = (bid_oa_v if bid_oa_v > 0.0 else ask_oa_v) + (bid_ob_v if bid_ob_v > 0.0 else ask_ob_v)
                        ask_a_v = min((float(x["price"] if isinstance(x, dict) else x[0]) for x in (bk_a.get("asks") or [])), default=0.0)
                        ask_b_v = min((float(x["price"] if isinstance(x, dict) else x[0]) for x in (bk_b.get("asks") or [])), default=0.0)
                        parity_a_viol = ask_a_v > 0.0 and bid_oa_v > 0.0 and (ask_a_v + bid_oa_v) > 1.015
                        parity_b_viol = ask_b_v > 0.0 and bid_ob_v > 0.0 and (ask_b_v + bid_ob_v) > 1.015
                        if parity_a_viol or parity_b_viol or opp_sum > 1.160 or opp_ub_sum > 1.180:
                            return {"executed": False, "reason": f"ANTI_BOX_COMPLEMENT_VETO:{max(opp_sum, opp_ub_sum, ask_a_v + bid_oa_v, ask_b_v + bid_ob_v):.4f}"}
                    except Exception as exc_opp:
                        return {"executed": False, "reason": f"ANTI_BOX_COMPLEMENT_UNVERIFIED:{exc_opp}"}
                    book_walk_ms = round((time.perf_counter_ns() - t_bk0) / 1_000_000.0, 2)

                    def _bk_quiet(bk_d: Dict[str, Any]) -> bool:
                        asks_d, bids_d = bk_d.get("asks") or [], bk_d.get("bids") or []
                        if not asks_d or not bids_d:
                            return False
                        ba = min(float(x["price"] if isinstance(x, dict) else x[0]) for x in asks_d)
                        bb = max(float(x["price"] if isinstance(x, dict) else x[0]) for x in bids_d)
                        return bb > 0.0 and (ba - bb) <= 0.041

                    fresh_quiet = bool(candidate_box.get("is_quiet_book") and _bk_quiet(bk_a) and _bk_quiet(bk_b))
                    _rcfg_d1_w = getattr(self, "risk_config", None) or RISK_CONFIG
                    _rb_d1_gov = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
                    _d1_cfg_cap = float(
                        _rcfg_d1_w["d1_max_box_cost_net"]
                        if isinstance(_rcfg_d1_w, dict) and "d1_max_box_cost_net" in _rcfg_d1_w
                        else _rb_d1_gov.get("d1_max_box_cost_net", RISK_CONFIG.get("d1_max_box_cost_net", 0.985))
                    )
                    if sleeve_src == "COND1_MACRO_PARTITION_BOX" and not own_grad:
                        live_walk_cap = 0.985
                    elif sleeve_src == "COND1_MACRO_PARTITION_BOX" and own_grad and 0.0 < rem_tte_s <= 172800.0:
                        live_walk_cap = 0.992 if zero_fee_box else 0.988
                    elif zero_fee_box:
                        _grad_cap_max_tte = 604800.0 if sleeve_src in _v3_7d else 172800.0
                        _zf_base_cap = (
                            float(
                                _rcfg_d1_w["cm_b3_max_walk_cap"]
                                if isinstance(_rcfg_d1_w, dict) and "cm_b3_max_walk_cap" in _rcfg_d1_w
                                else _rb_d1_gov.get("cm_b3_max_walk_cap", RISK_CONFIG.get("cm_b3_max_walk_cap", 0.990))
                            )
                            if box_type == "BARRIER_MONO"
                            else (0.992 if (fresh_quiet or (own_grad and 0.0 < rem_tte_s <= _grad_cap_max_tte)) else 0.990)
                        )
                        if _zf_c1_merge_ok:
                            live_walk_cap = max(_zf_base_cap, _zf1_cap)
                        elif (
                            box_type == "DOMINANCE"
                            and self._is_v5_unleashed_active()
                            and 0.0 < rem_tte_s <= float(_rb_d1_gov.get("d1_short_tte_threshold_sec", 180.0))
                        ):
                            live_walk_cap = max(_zf_base_cap, float(_rb_d1_gov.get("d1_short_tte_max_box_cost_net", 0.9925)))
                        else:
                            live_walk_cap = _zf_base_cap
                    elif box_type in {"SPORTS_CORRIDOR", "MACRO_DOMINANCE", "NBA_DOMINANCE", "NEGRISK_2LEG", "LADDER_MONO", "COUNTING_DOMINANCE"} or sleeve_src == "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":
                        live_walk_cap = 0.988
                    elif sleeve_src == "D1_QUIET_BOOK_BOX" and fresh_quiet and self._is_v5_unleashed_active():
                        live_walk_cap = max(_d1_cfg_cap, 0.989)
                    elif box_type == "COMPLETE_SET" and self._is_v5_unleashed_active():
                        live_walk_cap = max(_d1_cfg_cap, min(0.990, float(candidate_box.get("max_box_cost_net") or 0.989)))
                    else:
                        live_walk_cap = _d1_cfg_cap
                    if _ft_cert_2l:
                        _ft_walk_max = max(_zf1_cap, 0.9990) if _zf_c1_merge_ok else (0.9990 if zero_fee_box else 0.995)
                        live_walk_cap = max(live_walk_cap, min(_ft_walk_max, float(candidate_box.get("max_box_cost_net") or live_walk_cap)))
                    w_fresh = walk_equal_shares_dominance_box(
                        bk_a.get("asks") or [], bk_b.get("asks") or [],
                        target_budget_usd=target_budget, fee_rate_a=fr_a, fee_rate_b=fr_b,
                        fee_exponent_a=fe_a, fee_exponent_b=fe_b, max_box_cost_net=live_walk_cap,
                        min_shares=5, min_box_notional_usd=4.50, min_box_cost_net=0.860,
                    )
                    if not w_fresh.get("filled"):
                        rej_r = str(w_fresh.get("reason"))
                        logger.info(
                            f"[D1 FRESH BOOK REJECT] {candidate_box.get('box_id')} ({cand_asset or 'BTC'}): {rej_r} | "
                            f"cap={live_walk_cap:.3f} quiet={fresh_quiet} ipc_age_ms={ipc_age_ms:.1f} pre_bal_ms={pre_bal_ms:.1f} book_ms={book_walk_ms:.1f}"
                        )
                        if not self.dry_run and _stage_b_emit_funnel is not None and ipc_age_ms >= 0.0:
                            try:
                                _b_id_r = str(candidate_box.get("box_id") or dedupe_k or "")
                                if _STAGE_B_DECAY_TRACKER is not None and _b_id_r:
                                    _STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(_b_id_r)
                                _c_c0 = float(candidate_box.get("box_cost_net") or 0.985)
                                _sh_c0 = float(candidate_box.get("shares") or 10.0)
                                _stage_b_emit_funnel("COMPETITOR_DECAY_OBSERVED", sleeve=sleeve_src, candidate_key=_b_id_r, box_type=box_type, asset=str(cand_asset or ""), net_edge_bps=max(0.0, 1.0 - _c_c0) * 10000.0, est_profit_usd=max(0.0, 1.0 - _c_c0) * _sh_c0, competitor_decay_ms=max(0.1, ipc_age_ms + pre_bal_ms + book_walk_ms), reason=f"FRESH_BOOK_WALK_REJECT:{rej_r}")
                            except Exception:
                                pass
                        return {"executed": False, "reason": f"FRESH_BOOK_WALK_REJECT:{rej_r}"}
                    avail_min_f = min(float(w_fresh["avail_a_shares"]), float(w_fresh["avail_b_shares"]))
                    if int(w_fresh["shares"]) > 16 and avail_min_f < 2.0 * float(w_fresh["shares"]):
                        cap_sh = max(16, int(math.floor(avail_min_f * 0.50)))
                        w_trim = walk_equal_shares_dominance_box(
                            bk_a.get("asks") or [], bk_b.get("asks") or [],
                            target_budget_usd=min(target_budget, (cap_sh + 0.25) * float(w_fresh["eff_px"])),
                            fee_rate_a=fr_a, fee_rate_b=fr_b, fee_exponent_a=fe_a, fee_exponent_b=fe_b,
                            max_box_cost_net=live_walk_cap, min_shares=5, min_box_notional_usd=4.50, min_box_cost_net=0.860,
                        )
                        if w_trim.get("filled"):
                            w_fresh = w_trim
                            avail_min_f = min(float(w_fresh["avail_a_shares"]), float(w_fresh["avail_b_shares"]))
                    _min_depth_gate = max(1.0, float((getattr(self, "risk_config", None) or RISK_CONFIG).get("d1_min_depth_mult_gate", 1.15)))
                    if avail_min_f + 1e-6 < _min_depth_gate * float(w_fresh["shares"]):
                        cap_sh_gate = int(math.floor((avail_min_f + 1e-9) / _min_depth_gate))
                        if cap_sh_gate < 5:
                            return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:MIN_DEPTH_MULT_GATE"}
                        w_gate = walk_equal_shares_dominance_box(
                            bk_a.get("asks") or [], bk_b.get("asks") or [],
                            target_budget_usd=min(target_budget, (cap_sh_gate + 0.25) * float(w_fresh["eff_px"])),
                            fee_rate_a=fr_a, fee_rate_b=fr_b, fee_exponent_a=fe_a, fee_exponent_b=fe_b,
                            max_box_cost_net=live_walk_cap, min_shares=5, min_box_notional_usd=4.50, min_box_cost_net=0.860,
                        )
                        if not w_gate.get("filled") or avail_min_f + 1e-6 < _min_depth_gate * float(w_gate["shares"]):
                            return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:MIN_DEPTH_MULT_GATE"}
                        w_fresh = w_gate
                        avail_min_f = min(float(w_fresh["avail_a_shares"]), float(w_fresh["avail_b_shares"]))
                    fresh_box_net = float(w_fresh["box_cost_net"])
                    if fresh_box_net > 0.975 and avail_min_f < 1.5 * float(w_fresh["shares"]):
                        cap_sh_q = int(math.floor((avail_min_f + 1e-9) / 1.50))
                        w_q = (
                            walk_equal_shares_dominance_box(
                                bk_a.get("asks") or [], bk_b.get("asks") or [],
                                target_budget_usd=min(target_budget, (cap_sh_q + 0.25) * float(w_fresh["eff_px"])),
                                fee_rate_a=fr_a, fee_rate_b=fr_b, fee_exponent_a=fe_a, fee_exponent_b=fe_b,
                                max_box_cost_net=live_walk_cap, min_shares=5, min_box_notional_usd=4.50, min_box_cost_net=0.860,
                            )
                            if cap_sh_q >= 5
                            else {"filled": False}
                        )
                        if not w_q.get("filled") or avail_min_f + 1e-6 < 1.5 * float(w_q["shares"]):
                            logger.info(
                                f"[D1 FRESH BOOK REJECT] {candidate_box.get('box_id')} ({cand_asset or 'BTC'}): QUIET_DEPTH_THINNED | "
                                f"net={fresh_box_net:.4f} sh={w_fresh['shares']} avail_min={avail_min_f:.1f}"
                            )
                            return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:QUIET_DEPTH_THINNED"}
                        w_fresh = w_q
                        avail_min_f = min(float(w_fresh["avail_a_shares"]), float(w_fresh["avail_b_shares"]))
                        fresh_box_net = float(w_fresh["box_cost_net"])
                    px_a_lim = float(w_fresh["leg_a_walk"]["worst_px"])
                    px_b_lim = float(w_fresh["leg_b_walk"]["worst_px"])
                    sh_req = float(w_fresh.get("net_paired_shares") or w_fresh["shares"])
                    sh_a_gross = float(w_fresh.get("leg_a_gross_shares") or w_fresh["shares"])
                    sh_b_gross = float(w_fresh.get("leg_b_gross_shares") or w_fresh["shares"])
                    avail_a = float(w_fresh["avail_a_shares"])
                    avail_b = float(w_fresh["avail_b_shares"])
                    cap_net = live_walk_cap
                    _is_real_clob_d1 = (
                        not self.dry_run
                        and getattr(self.executor, "client", None) is not None
                        and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                        and ("execute_atomic_dominance_box" not in getattr(self.executor, "__dict__", {}) or getattr(self, "holistic_v5_live_mode", None) is True)
                    )
                    if _is_real_clob_d1:
                        _ha_q = min(0.25, max(0.0, (fr_a * ((px_a_lim * (1.0 - px_a_lim)) ** fe_a)) / max(px_a_lim, 1e-6))) if fr_a > 0.0 else 0.0
                        _hb_q = min(0.25, max(0.0, (fr_b * ((px_b_lim * (1.0 - px_b_lim)) ** fe_b)) / max(px_b_lim, 1e-6))) if fr_b > 0.0 else 0.0
                        _q_d1 = quantize_fok_buy_box_legs(
                            shares_net=sh_req,
                            px_a=px_a_lim,
                            px_b=px_b_lim,
                            h_a=_ha_q,
                            h_b=_hb_q,
                            max_box_cost_net=live_walk_cap,
                            avail_a=avail_a,
                            avail_b=avail_b,
                            max_budget_usd=max(target_budget, 5.0),
                            min_shares=5.0,
                        )
                        if _q_d1 is None:
                            return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:FOK_QUANTIZATION_EXCEEDS_CAP"}
                        sh_a_gross = _q_d1["leg_a_gross_shares"]
                        sh_b_gross = _q_d1["leg_b_gross_shares"]
                        sh_req = _q_d1["net_paired_shares"]
                        fresh_box_net = max(fresh_box_net, _q_d1["eff_box_cost_net"])

            if fresh_box_net < 0.860:
                return {"executed": False, "reason": f"ANTI_BOX_COST_FLOOR_REJECT:{fresh_box_net:.4f}"}
            is_4h_cand = (
                str(candidate_box.get("leg_a_horizon") or "").lower() == "4h"
                or str(candidate_box.get("leg_b_horizon") or "").lower() == "4h"
            )
            is_zero_itode_box = box_type == "COMPLETE_SET" or (
                zero_fee_box
                and box_type in {"NEGRISK_2LEG", "NEGRISK_CROSS", "NBA_DOMINANCE", "SPORTS_CORRIDOR", "MACRO_DOMINANCE", "COUNTING_DOMINANCE", "BARRIER_MONO"}
            )
            _rcfg_d1 = getattr(self, "risk_config", None) or RISK_CONFIG
            _d1_route_mode = str(_rcfg_d1.get("d1_routing_mode", "hybrid_auto"))
            if _d1_route_mode == "fragile_first":
                use_parallel_d1 = False
            elif _d1_route_mode == "parallel_2leg":
                use_parallel_d1 = bool((not is_4h_cand) and min(px_a_lim, px_b_lim) >= (0.05 if is_zero_itode_box else 0.30))
            else:
                _mock_exec_override = (
                    "execute_atomic_dominance_box" in getattr(self.executor, "__dict__", {})
                    and not bool(candidate_box.get("force_parallel_batch"))
                )
                _par_net_cap = 0.975 if _mock_exec_override else 0.994
                use_parallel_d1 = bool(
                    (
                        is_zero_itode_box
                        or (
                            (not is_4h_cand)
                            and (not cand_asset or cand_asset in {"BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "HYPE", "ZEC", "XAU", "XAG"})
                            and fresh_box_net <= _par_net_cap
                        )
                    )
                    and min(px_a_lim, px_b_lim) >= (0.05 if is_zero_itode_box else 0.20)
                    and (
                        avail_a is None
                        or avail_b is None
                        or min(float(avail_a), float(avail_b)) >= 1.50 * sh_req
                    )
                )
            box_id = str(candidate_box.get("box_id") or f"D1_LIVE_{int(now_ts)}")
            st_lock = getattr(self, "_state_save_lock", None) or self._GLOBAL_STATE_SAVE_LOCK
            t_fok0 = time.perf_counter_ns()
            _box_call_kw = dict(
                box_id=box_id,
                leg_a_token_id=tok_a,
                leg_a_label=lbl_a,
                leg_a_limit_price=px_a_lim,
                leg_b_token_id=tok_b,
                leg_b_label=lbl_b,
                leg_b_limit_price=px_b_lim,
                shares=sh_req,
                max_box_cost_net=cap_net,
                leg_a_avail_shares=avail_a,
                leg_b_avail_shares=avail_b,
                fee_rate_a=fr_a,
                fee_rate_b=fr_b,
                fee_exponent_a=fe_a,
                fee_exponent_b=fe_b,
                parallel_dispatch=use_parallel_d1,
            )
            try:
                res = self.executor.execute_atomic_dominance_box(
                    **_box_call_kw,
                    leg_a_pre_balance=pre_bal_a,
                    leg_b_pre_balance=pre_bal_b,
                    min_box_cost_floor=0.860,
                    leg_a_shares=sh_a_gross,
                    leg_b_shares=sh_b_gross,
                )
            except TypeError:
                try:
                    res = self.executor.execute_atomic_dominance_box(
                        **_box_call_kw,
                        leg_a_pre_balance=pre_bal_a,
                        leg_b_pre_balance=pre_bal_b,
                        min_box_cost_floor=0.860,
                    )
                except TypeError:
                    try:
                        res = self.executor.execute_atomic_dominance_box(
                            **_box_call_kw,
                            leg_a_pre_balance=pre_bal_a,
                            leg_b_pre_balance=pre_bal_b,
                        )
                    except TypeError:
                        res = self.executor.execute_atomic_dominance_box(**_box_call_kw)
            fok_box_ms = round((time.perf_counter_ns() - t_fok0) / 1_000_000.0, 2)
            _fok_ok = bool(res.get("success"))
            _fok_err = "" if _fok_ok else f" | abort={res.get('stage') or res.get('error') or 'FAILED'}"
            logger.info(
                f"[D1 LATENCY TELEMETRY] {box_id} ({cand_asset or 'BTC'}): ipc_age_ms={ipc_age_ms:.2f} | "
                f"pre_bal_ms={pre_bal_ms:.2f} | book_walk_ms={book_walk_ms:.2f} | fok_box_ms={fok_box_ms:.2f} | "
                f"sh={sh_req:.0f} | parallel={use_parallel_d1} | ok={_fok_ok}{_fok_err}"
            )
            if _LatencyTrace is not None:
                try:
                    _d1_tr = _LatencyTrace(
                        box_id=box_id, asset=str(cand_asset or "BTC"), sleeve=sleeve_src,
                        ipc_age_ms=ipc_age_ms, pre_bal_ms=pre_bal_ms, book_walk_ms=book_walk_ms,
                        fok_box_ms=fok_box_ms, shares=sh_req, parallel=use_parallel_d1,
                        outcome="d1_ok" if _fok_ok else f"d1_{res.get('stage') or 'fail'}",
                    )
                    _d1_tr.emit()
                except Exception:
                    pass
            if not self.dry_run and _stage_b_emit_funnel is not None:
                try:
                    _ed_bps = round(max(0.0, 1.0 - fresh_box_net) * 10000.0, 2)
                    _est_pf = round(max(0.0, 1.0 - fresh_box_net) * sh_req, 4)
                    _not_sb = round(fresh_box_net * sh_req, 4)
                    _stage_b_emit_funnel("ORDER_SUBMITTED", sleeve=sleeve_src, candidate_key=box_id, box_type=box_type, asset=str(cand_asset or ""), net_edge_bps=_ed_bps, est_profit_usd=_est_pf, notional_usd=_not_sb)
                    if _STAGE_B_DECAY_TRACKER is not None:
                        _STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(box_id)
                        if dedupe_k:
                            _STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(dedupe_k)
                    if _fok_ok:
                        _stage_b_emit_funnel("COMPLETE_BASKET_LOCKED", sleeve=sleeve_src, candidate_key=box_id, box_type=box_type, asset=str(cand_asset or ""), net_edge_bps=_ed_bps, est_profit_usd=_est_pf, notional_usd=_not_sb)
                    elif isinstance(res.get("residual_unhedged_leg"), dict) or res.get("legged_out"):
                        _stage_b_emit_funnel("PARTIAL_BASKET_UNWOUND", sleeve=sleeve_src, candidate_key=box_id, box_type=box_type, asset=str(cand_asset or ""), notional_usd=_not_sb, reason=str(res.get("stage") or "LEGGED_OUT"))
                except Exception:
                    pass
            leg_tids: List[str] = []
            clean_zero_cost_abort = bool(
                not res.get("success")
                and not res.get("outcome_unknown")
                and not res.get("legged_out")
                and not isinstance(res.get("residual_unhedged_leg"), dict)
            )
            _pb_map = self.__dict__.setdefault("_d1_clean_pre_bal_cache", {})
            if clean_zero_cost_abort and "_wallet_token_balance" not in self.__dict__:
                _now_c = time.time()
                for _tk_old, (_, _ts_old) in list(_pb_map.items()):
                    if (_now_c - _ts_old) > 120.0:
                        _pb_map.pop(_tk_old, None)
                _pb_map[tok_a] = (pre_bal_a, _now_c)
                _pb_map[tok_b] = (pre_bal_b, _now_c)
            else:
                _pb_map.pop(tok_a, None)
                _pb_map.pop(tok_b, None)
            with st_lock:
                if dedupe_k:
                    if clean_zero_cost_abort:
                        seen_boxes.discard(dedupe_k)
                        self.__dict__.get("_seen_d1_box_order", {}).pop(dedupe_k, None)
                        for k_cd, ts_cd in list(retry_cd.items()):
                            if float(ts_cd or 0.0) <= now_ts:
                                retry_cd.pop(k_cd, None)
                        retry_cd[dedupe_k] = now_ts + 9.5
                        if is_live_ctf_box:
                            self.save_state()
                    else:
                        retry_cd.pop(dedupe_k, None)
                        self._record_seen_d1_box_key(dedupe_k)
                if res.get("success") and isinstance(res.get("leg_1"), dict) and isinstance(res.get("leg_2"), dict):
                    leg_tids = self._register_live_d1_box_positions(box_id, candidate_box, res, pre_bal_a, pre_bal_b)
                elif res.get("outcome_unknown"):
                    self._register_unknown_d1_box_legs(box_id, candidate_box, res, pre_bal_a, pre_bal_b)
                elif isinstance(res.get("residual_unhedged_leg"), dict):
                    self.executor.invalidate_collateral_cache()
                    self._pending_collateral_refresh = True
                    resid = res["residual_unhedged_leg"]
                    if float(resid.get("residual_shares") or 0.0) > 0.01 or resid.get("unwind_outcome_unknown"):
                        leg_tids = self._register_legged_out_d1_residual(box_id, candidate_box, resid, pre_bal_a, pre_bal_b)
                    else:
                        self._record_inline_d1_legged_out_close(box_id, candidate_box, resid, res)
                elif dedupe_k and not clean_zero_cost_abort:
                    self.save_state()
            return {"executed": bool(res.get("success")), "result": res, "leg_trade_ids": leg_tids}
        finally:
            inflight_lock.release()

    def _make_single_leg_lock_pos(
        self, lid: str, box_type: str, sleeve_src: str, cand_asset: str, horizon_s: str,
        mid_a: str, cid_a: str, tok_a: str, side_s: str, nr_a: bool, f_sh: float, not_u: float,
        fee_u: float, fr_a: float, fe_a: float, fee_src: str, exp_ts: float, now_ts: float,
        pre_b: float, oid: Any, h_mat: bool, unk: bool = False, sub_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        from src.polymarket_research.riskless_protocol_v2_expansion import resolve_canonical_fee_source
        eff_px = round((not_u + fee_u) / max(f_sh, 0.01), 5)
        _canon_fsrc = "maker_post_only_0pct" if fee_src == "maker_post_only_0pct" else resolve_canonical_fee_source(fr_a, sleeve_src, fee_src)
        rec = {
            "trade_id": lid, "box_id": lid, "box_partner_trade_id": "", "is_dominance_box": False,
            "is_single_leg_lock": True, "hold_to_maturity_lock": h_mat, "box_type": box_type,
            "box_cost_net": eff_px, "box_total_cost_usd": round(not_u + fee_u, 4),
            "sleeve": sleeve_src, "sleeve_source": sleeve_src, "entry_tte": max(1.0, exp_ts - now_ts), "event_id": lid, "event_group_key": "",
            "market_id": mid_a, "condition_id": cid_a, "token_id": tok_a, "target_token": side_s,
            "asset": cand_asset, "horizon": horizon_s, "is_subhourly": False, "neg_risk": bool(nr_a),
            "candle_open_spot": 100.0, "entry_spot_ref": 100.0, "spot_denomination": "USD", "candle_sigma": 0.0,
            "entry_price": round(not_u / max(f_sh, 0.01), 4), "entry_shares": f_sh, "gross_entry_shares": f_sh,
            "remaining_shares": f_sh, "filled_exit_shares": 0.0, "remaining_exit_shares": f_sh,
            "remaining_cost_basis": not_u, "realized_exit_cash": 0.0, "realized_exit_fee": 0.0,
            "gross_exit_cash": 0.0, "average_exit_price": 0.0, "exit_trade_ids": [],
            "notional_usd": not_u, "fee_usd": fee_u, "entry_fee_cash_usd": fee_u,
            "entry_fee_asset": "USDC", "fee_source": _canon_fsrc, "fee_rate_applied": fr_a, "fee_exponent_applied": fe_a,
            "target_exit_price": 1.0 if h_mat else 0.99, "exit_order_size": f_sh,
            "entry_time_utc": datetime.now(timezone.utc).isoformat(), "entry_ts": now_ts,
            "candle_expiry_ts": exp_ts, "pre_token_balance": pre_b,
            "order_id": oid, "entry_order_id": oid, "trade_ids": [], "transactions_hashes": [],
            "status": "ENTRY_OUTCOME_UNKNOWN" if unk else (ExecutionStatus.POSITION_CONFIRMED if self.dry_run else ExecutionStatus.MATCHED_PENDING_SETTLEMENT),
            "inventory_reconciled": bool(self.dry_run and not unk), "exit_order_id": None,
            "exit_order_status": "ENTRY_OUTCOME_UNKNOWN" if unk else ("DETERMINISTIC_TERMINAL_HOLD" if h_mat else ("NONE" if self.dry_run else "AWAITING_DELTA_SETTLEMENT")),
            "terminal_policy": "DETERMINISTIC_TERMINAL_HOLD" if h_mat else None,
            "is_liquidating": False, "unwind_order_id": None, "unwind_start_time": 0.0,
        }
        if sub_ts is not None:
            rec["submitted_at_ts"] = sub_ts
        return rec

    _finish_single_leg_lock = _bind_hv_method(_hv__finish_single_leg_lock, '_finish_single_leg_lock')

    _finish_negrisk_convert_arb = _bind_hv_method(_hv__finish_negrisk_convert_arb, '_finish_negrisk_convert_arb')

    _record_inline_d1_legged_out_close = _bind_hv_method(_hv__record_inline_d1_legged_out_close, '_record_inline_d1_legged_out_close')

    def _register_live_d1_box_positions(
        self, box_id: str, cand: Dict[str, Any], res: Dict[str, Any], pre_bal_a: float, pre_bal_b: float
    ) -> List[str]:
        """Registers both filled legs of a live D1 Dominance Box ($1.00 DETERMINISTIC_TERMINAL_HOLD for <=900s DOMINANCE)."""
        from src.polymarket_research.riskless_protocol_v2_expansion import register_live_d1_box_positions_impl

        return register_live_d1_box_positions_impl(
            self, box_id, cand, res, pre_bal_a, pre_bal_b,
            ExecutionStatus.POSITION_CONFIRMED, ExecutionStatus.MATCHED_PENDING_SETTLEMENT,
        )

    def _register_legged_out_d1_residual(
        self, box_id: str, cand: Dict[str, Any], resid: Dict[str, Any], pre_bal_a: float, pre_bal_b: float
    ) -> List[str]:
        """Registers any unhedged legged-out D1 residual shares so supervision reconciles Polygon settlement & unwinds 100%."""
        now_ts = time.time()
        exp_ts = float(cand.get("expiry_ts") or (now_ts + 180.0))
        asset_sym = str(cand.get("asset") or "BTC").upper()
        tok = str(resid.get("token_id") or "")
        meta_by_tok = {
            str(cand.get("leg_a_token_id")): ("leg_a", pre_bal_a),
            str(cand.get("leg_b_token_id")): ("leg_b", pre_bal_b),
        }
        pfx, pre_b = meta_by_tok.get(tok, ("leg_a", 0.0))
        m_sh = float(resid.get("matched_shares") or cand.get("shares") or 12.0)
        uw_unk = bool(resid.get("unwind_outcome_unknown"))
        rem_sh = m_sh if uw_unk else float(resid.get("residual_shares") or 0.0)
        px = float(resid.get("price") or cand.get(f"{pfx}_limit_price") or 0.48)
        fr = 0.0 if resid.get("is_maker_anchor") else (float(cand[f"{pfx}_fee_rate"]) if cand.get(f"{pfx}_fee_rate") is not None else 0.07)
        fe = float(cand.get(f"{pfx}_fee_exponent", 1.0) or 1.0)
        notional = round(rem_sh * px, 4)
        fee_u = round(rem_sh * fr * ((px * (1.0 - px)) ** fe), 4) if fr > 0.0 else 0.0
        tid = f"{box_id}_LEG_RESID"
        if tid in self.active_positions or any(p.get("trade_id") == tid for p in self.closed_positions):
            tid = f"{tid}_{int(now_ts)}"
        uw_oid = (resid.get("unwind_result") or {}).get("orderID") if isinstance(resid.get("unwind_result"), dict) else None
        strike_resid = float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx == "leg_a" else "k_high") or 100.0)
        self.active_positions[tid] = {
            "trade_id": tid, "box_id": box_id, "is_dominance_box": False, "is_legged_out_residual": True,
            "pending_unwind_tag": "D1_LEGGED_OUT_RESIDUAL_UNWIND",
            "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX", "entry_tte": max(1.0, exp_ts - now_ts), "event_id": box_id,
            "market_id": str(cand.get(f"{pfx}_market_id") or tid),
            "condition_id": str(cand.get(f"{pfx}_condition_id") or ""),
            "token_id": tok, "target_token": str(cand.get(f"{pfx}_side") or "UP"), "asset": asset_sym,
            "horizon": str(cand.get(f"{pfx}_horizon") or "15m"), "is_subhourly": True,
            "candle_open_spot": strike_resid,
            "entry_spot_ref": strike_resid, "spot_denomination": "USD",
            "candle_sigma": 0.0025 if asset_sym == "BTC" else 0.0035,
            "entry_price": px, "entry_shares": rem_sh, "gross_entry_shares": rem_sh,
            "remaining_shares": rem_sh, "filled_exit_shares": 0.0, "remaining_exit_shares": rem_sh,
            "remaining_cost_basis": notional, "realized_exit_cash": 0.0, "realized_exit_fee": 0.0,
            "gross_exit_cash": 0.0, "average_exit_price": 0.0, "exit_trade_ids": [],
            "notional_usd": notional, "fee_usd": fee_u, "entry_fee_cash_usd": fee_u,
            "entry_fee_asset": "USDC", "fee_source": "crypto_fees_v2",
            "fee_rate_applied": fr, "fee_exponent_applied": fe, "target_exit_price": 0.99,
            "entry_time_utc": datetime.now(timezone.utc).isoformat(), "entry_ts": now_ts,
            "candle_expiry_ts": exp_ts, "pre_token_balance": pre_b,
            "order_id": resid.get("orderID"), "entry_order_id": resid.get("orderID"),
            "trade_ids": [], "transactions_hashes": [],
            "status": ExecutionStatus.MATCHED_PENDING_SETTLEMENT, "inventory_reconciled": False,
            "exit_order_id": None,
            "exit_order_status": "UNWIND_EXECUTION_OUTCOME_UNKNOWN" if uw_unk else "UNWIND_RETRY_REQUIRED",
            "stop_triggered_ts": now_ts, "next_unwind_retry_ts": now_ts + 0.35,
            "unwind_attempt_ts": now_ts, "unwind_order_id": uw_oid if uw_unk else None,
            "is_liquidating": False, "unwind_start_time": now_ts,
        }
        self._refresh_global_halt()
        self.save_state()
        logger.warning(f"[D1 LEGGED-OUT RESIDUAL SUPERVISED] {tid} ({asset_sym}): {rem_sh:.2f} sh queued for supervised unwind.")
        return [tid]

    def _register_unknown_d1_box_legs(
        self, box_id: str, cand: Dict[str, Any], res: Dict[str, Any], pre_bal_a: float, pre_bal_b: float
    ) -> None:
        now_ts = time.time()
        exp_ts = float(cand.get("expiry_ts") or (now_ts + 180.0))
        sh = float(cand.get("shares") or 12.0)
        meta_by_tok = {
            str(cand.get("leg_a_token_id")): ("leg_a", pre_bal_a),
            str(cand.get("leg_b_token_id")): ("leg_b", pre_bal_b),
        }
        slots = [
            (res.get("leg_1_token_id") or cand.get("leg_a_token_id"), res.get("leg_1_order_id")),
            (res.get("leg_2_token_id") or cand.get("leg_b_token_id"), res.get("leg_2_order_id")),
        ]
        unk_tids: List[str] = []
        unk_entries: List[Tuple[int, str, Optional[str]]] = []
        for idx, (tok_raw, oid) in enumerate(slots):
            tok = str(tok_raw or "")
            if not tok:
                continue
            tid = f"{box_id}_UNK_{idx + 1}"
            if tid in self.active_positions or any(p.get("trade_id") == tid for p in self.closed_positions):
                tid = f"{tid}_{int(now_ts)}"
            unk_tids.append(tid)
            unk_entries.append((idx, tok, oid))
        for pos_i, (idx, tok, oid) in enumerate(unk_entries):
            tid = unk_tids[pos_i]
            partner_tid = unk_tids[1 - pos_i] if len(unk_tids) == 2 else ""
            pfx, pre_b = meta_by_tok.get(tok, ("leg_a" if idx == 0 else "leg_b", 0.0))
            px = float(cand.get(f"{pfx}_limit_price") or 0.50)
            strike_u = float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx == "leg_a" else "k_high") or 100.0)
            self.active_positions[tid] = {
                "trade_id": tid, "box_id": box_id, "box_partner_trade_id": partner_tid,
                "is_dominance_box": True, "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "event_id": box_id, "market_id": str(cand.get(f"{pfx}_market_id") or tid),
                "condition_id": str(cand.get(f"{pfx}_condition_id") or ""), "token_id": tok,
                "target_token": str(cand.get(f"{pfx}_side") or "UP"), "asset": str(cand.get("asset") or "BTC").upper(),
                "candle_open_spot": strike_u,
                "entry_spot_ref": strike_u, "spot_denomination": "USD",
                "candle_sigma": 0.003, "entry_price": px, "entry_shares": sh, "gross_entry_shares": sh,
                "remaining_shares": sh, "filled_exit_shares": 0.0, "remaining_exit_shares": sh,
                "remaining_cost_basis": round(sh * px, 4), "realized_exit_cash": 0.0, "realized_exit_fee": 0.0,
                "gross_exit_cash": 0.0, "average_exit_price": 0.0, "exit_trade_ids": [],
                "notional_usd": round(sh * px, 4), "intended_notional": round(sh * px, 4),
                "fee_usd": 0.0, "entry_fee_cash_usd": 0.0, "entry_fee_asset": "USDC", "fee_source": "crypto_fees_v2",
                "target_exit_price": 0.99, "entry_time_utc": datetime.now(timezone.utc).isoformat(),
                "entry_ts": now_ts, "submitted_at_ts": now_ts, "candle_expiry_ts": exp_ts,
                "pre_token_balance": pre_b, "entry_order_id": oid, "order_id": oid,
                "trade_ids": [], "transactions_hashes": [], "status": "ENTRY_OUTCOME_UNKNOWN",
                "exit_order_status": "ENTRY_OUTCOME_UNKNOWN", "inventory_reconciled": False,
                "is_liquidating": False, "unwind_order_id": None, "unwind_start_time": 0.0,
            }
        self._refresh_global_halt()
        self.save_state()

    maybe_execute_graduated_maker_anchor_box = _bind_hv_method(_hv_maybe_execute_graduated_maker_anchor_box, 'maybe_execute_graduated_maker_anchor_box')

    async def maybe_execute_graduated_single_leg_maker_lock(self, candidate_box: Dict[str, Any]) -> Dict[str, Any]:
        """Executes 0%-fee resting Maker single-leg deterministic locks (`BOND1_UMA_RESOLUTION_CARRY`) asynchronously."""
        if self._is_d1_box_halted():
            return {"executed": False, "reason": "DISABLED_OR_HALTED"}
        box_type = str(candidate_box.get("box_type") or "").strip().upper()
        if box_type != "SINGLE_LEG_MAKER_LOCK":
            return {"executed": False, "reason": f"UNSUPPORTED_SINGLE_LEG_MAKER_TYPE:{box_type}"}
        sleeve_src = str(candidate_box.get("sleeve_source") or "BOND1_UMA_RESOLUTION_CARRY").strip()
        cand_asset = str(candidate_box.get("asset") or sleeve_src[:4]).strip().upper()
        mid_a = str(candidate_box.get("leg_a_market_id") or "")
        if mid_a in {"6707502", "6707503"}:
            return {"executed": False, "reason": "D001_DISPUTED_KMIA_NON_INTERFERENCE"}
        cid_a = str(candidate_box.get("leg_a_condition_id") or "")
        tok_a = str(candidate_box.get("leg_a_token_id") or "")
        opp_a = str(candidate_box.get("leg_a_opp_token_id") or "").strip()
        if tok_a and not opp_a:
            from src.polymarket_research.riskless_protocol_v2_expansion import resolve_missing_opp_token_id
            _res_opp_a = resolve_missing_opp_token_id(self, mid_a, cid_a, tok_a)
            if _res_opp_a:
                opp_a = _res_opp_a
                candidate_box["leg_a_opp_token_id"] = opp_a
        side_s = str(candidate_box.get("leg_a_side") or "YES").upper()
        if not sleeve_src or not mid_a or not tok_a or not opp_a or tok_a == opp_a:
            return {"executed": False, "reason": "INVALID_SINGLE_LEG_MAKER_INVARIANTS"}

        inflight_mkr = self.__dict__.setdefault("_inflight_maker_anchor_keys", set())
        inflight_mkr_types = self.__dict__.setdefault("_inflight_maker_anchor_types", set())
        inflight_s2_mkr = self.__dict__.setdefault("_inflight_s2_maker_keys", set())
        dedupe_k = str(candidate_box.get("dedupe_key") or f"BOND1_MKR_{mid_a}")
        pair_dedupe_k = str(candidate_box.get("pair_dedupe_key") or f"BOND1_{mid_a}")
        _unlim_mkr = self._is_unlimited_slots_active() or self._is_v5_unleashed_active()
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            PROTOCOL_V2_MATH_SLEEVES,
            check_per_event_concentration_cap,
            check_s2_live_adverse_move_cancel,
            check_sll_cand_dispute_guard,
            compute_d1_per_market_notional_cap,
            compute_dynamic_riskless_tier_caps,
            compute_sll_entry_budget,
            compute_sll_maker_keep_and_renew,
            debit_sll_collateral_after_fill,
            eval_sll_fresh_book_and_peg,
            eval_sll_live_book_poll,
            extract_sll_event_group_key,
            extract_top_bid_from_book,
            is_d1_dedupe_blocked,
            is_market_busy_for_scaling,
            is_s2_maker_concurrent_capped,
            maybe_preempt_low_tier_s2_maker_slot,
            maybe_preempt_mlk1_if_bond1_starved,
            prepare_sll_stalk_guard,
            record_sll_exit_cooldown,
            release_sll_pending_intent,
            resolve_harvester_sll_tick_size,
            select_sll_velocity_preempt_target,
            sll_repost_expiry_and_ok,
            sll_settlement_lag_floor_hours,
            sync_harvester_sll_enforced_tick,
            spawn_fast_htm_maker_fill_reconcile,
            sync_pending_intents_on_collateral_refresh,
            update_sll_intent_partial_fill,
        )
        _is_s2_early = sleeve_src in {"S2_EXACT_TWAP_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR"}
        if _is_s2_early and not await maybe_preempt_low_tier_s2_maker_slot(self, cand_asset, inflight_s2_mkr):
            return {"executed": False, "reason": "S2_MAKER_CONCURRENT_CAP_1"}
        mkr_type_k = f"SINGLE_LEG_MAKER_LOCK:{mid_a}"
        sll_inflight_cnt = sum(1 for k in inflight_mkr_types if str(k).startswith("SINGLE_LEG_MAKER_LOCK:"))
        if (
            mkr_type_k in inflight_mkr_types
            or (not _is_s2_early and sll_inflight_cnt >= (8 if _unlim_mkr else 2))
            or len(inflight_mkr) >= ((12 if _is_s2_early else 10) if _unlim_mkr else (6 if _is_s2_early else 4))
        ):
            return {"executed": False, "reason": "SINGLE_LEG_MAKER_ALREADY_INFLIGHT"}
        if sleeve_src == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":
            _mlk1_active = sum(
                1
                for _iv in getattr(self, "pending_entry_intents", {}).values()
                if isinstance(_iv, dict) and _iv.get("sleeve_source") == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"
            )
            _mlk1_cap = (
                max(1, int(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("mkr_lock1_max_concurrent_slots", 1) or 1))
                if (
                    getattr(self, "enforce_bond1_smart_queue", False)
                    or (
                        not self.dry_run
                        and getattr(self.executor, "client", None) is not None
                        and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                        and "post_maker_entry_order" not in getattr(self.executor, "__dict__", {})
                    )
                )
                else 1
            )
            if _mlk1_active >= _mlk1_cap:
                return {"executed": False, "reason": "MKR_LOCK1_CONCURRENT_CAP_1"}
        now_ts = time.time()
        _disp_mkr = check_sll_cand_dispute_guard(candidate_box)
        if _disp_mkr:
            return {"executed": False, "reason": _disp_mkr}
        seen_boxes = self.__dict__.setdefault("_seen_d1_box_keys", set())
        retry_cd = self.__dict__.setdefault("_d1_retry_cooldown_until", {})
        if (
            is_d1_dedupe_blocked(self, dedupe_k, pair_dedupe_k, [mid_a], now_ts)
            or (dedupe_k and float(retry_cd.get(dedupe_k, 0.0) or 0.0) > now_ts)
            or (pair_dedupe_k and float(retry_cd.get(pair_dedupe_k, 0.0) or 0.0) > now_ts)
        ):
            return {"executed": False, "reason": "ALREADY_SEEN_OR_COOLDOWN"}
        if not self.dry_run and (
            not getattr(self, "_startup_reconciled", False)
            or self._global_halt_reasons()
            or mid_a in self._reconciling_market_ids()
        ):
            return {"executed": False, "reason": "NOT_READY_OR_GLOBAL_HALT"}

        _rcfg_sll = getattr(self, "risk_config", None) or RISK_CONFIG
        try:
            from src.polymarket_research.stage_c_zero_loss_velocity import load_alpha124_graduation_maps_with_lkg_cache

            by_sl_map, _by_da_s, _a124_err_s = load_alpha124_graduation_maps_with_lkg_cache(
                self,
                DATA_DIR,
                PIPELINE_ROOT,
                json_loads_fn=_json_loads,
                stale_reason="ALPHA124_STATE_MISSING_OR_STALE",
                missing_reason="ALPHA124_STATE_MISSING_OR_STALE",
            )
            if _a124_err_s is not None or by_sl_map is None:
                return {"executed": False, "reason": _a124_err_s or "ALPHA124_STATE_MISSING_OR_STALE"}

            def _grad8_s(rec: Dict[str, Any]) -> bool:
                adj_p = rec.get("legging_adjusted_pnl_t1000_usd", rec.get("realized_pnl_t1000_usd", 0.0))
                return bool(
                    int(rec.get("closed", 0) or 0) >= 8
                    and float(rec.get("win_rate_pct", 0.0) or 0.0) >= 100.0
                    and float(rec.get("realized_pnl_t1000_usd", 0.0) or 0.0) > 0.0
                    and float(adj_p or 0.0) > 0.0
                )

            _is_mlk1 = sleeve_src == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"
            _is_rw_carry = sleeve_src == "MKR_REWARD_LOCKED_CARRY"
            _is_s2_mkr = sleeve_src in {"S2_EXACT_TWAP_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR"}
            _is_wp_mkr = sleeve_src in {"W_PRUNE1_DEAD_NO_BOND", "UMA_READY1_LIVENESS_PRIORITY"}
            _rb_mkr_gov = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
            _is_inv_comp_mkr = bool(
                sleeve_src in {"C1_BINARY_COMPLETE_SET", "D1_SAME_ORACLE_DOMINANCE_BOX", "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"}
                and bool(_rb_mkr_gov.get("enable_inventory_backed_maker_completion", True))
                and (bool(candidate_box.get("full_throttle_bridge")) or candidate_box.get("rule_verified") is True)
            )
            _partner_tok_mkr = str(
                candidate_box.get("partner_held_token_id")
                or candidate_box.get("leg_b_token_id")
                or (opp_a if sleeve_src == "C1_BINARY_COMPLETE_SET" else "")
                or ""
            ).strip()
            _held_partner_mkr_sh, _partner_cost_ps_mkr, _inv_leg_cap_mkr = 0.0, 0.0, 0.998
            if _is_inv_comp_mkr:
                from src.polymarket_research.riskless_protocol_v2_expansion import resolve_unencumbered_partner_inventory_and_leg_cap
                if not _partner_tok_mkr or _partner_tok_mkr == tok_a:
                    return {"executed": False, "reason": "PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
                _held_partner_mkr_sh, _partner_cost_ps_mkr, _inv_leg_cap_mkr = resolve_unencumbered_partner_inventory_and_leg_cap(
                    self, candidate_box, _partner_tok_mkr, default_max_box_net=0.994, now_ts=now_ts, verify_wallet=not self.dry_run
                )
                if _held_partner_mkr_sh < 5.0:
                    return {"executed": False, "reason": "PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
                if _inv_leg_cap_mkr <= 0.01:
                    return {"executed": False, "reason": f"PARTNER_COST_BASIS_EXCEEDS_BOX_CAP:{_partner_cost_ps_mkr:.4f}"}
                candidate_box["_inventory_backed_maker"] = True
            _paused_mkr_set = {str(x).upper() for x in (_rb_mkr_gov.get("paused_riskless_sleeves") or [])}
            _enforce_paused_mkr = bool(
                getattr(self, "enforce_paused_riskless_sleeves", False)
                or (
                    not self.dry_run
                    and getattr(self.executor, "client", None) is not None
                    and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                    and "post_maker_entry_order" not in getattr(self.executor, "__dict__", {})
                )
            )
            if _enforce_paused_mkr and not bool(_rb_mkr_gov.get("enable_single_leg_maker_bond1", True)):
                return {"executed": False, "reason": "SINGLE_LEG_MAKER_BOND1_DISABLED"}
            if _enforce_paused_mkr and sleeve_src.upper() in _paused_mkr_set:
                return {"executed": False, "reason": f"PAUSED_RISKLESS_SLEEVE:{sleeve_src}"}
            from src.polymarket_research.stage_c_zero_loss_velocity import check_strict_pure_riskless_candidate_gate
            _pure_mkr_veto = check_strict_pure_riskless_candidate_gate(
                self, candidate_box, _rb_mkr_gov, is_maker=True
            )
            if _pure_mkr_veto is not None:
                return {"executed": False, "reason": _pure_mkr_veto}
            sl_rec_s = by_sl_map.get(sleeve_src) or {}
            b1_rec_s = by_sl_map.get("BOND1_UMA_RESOLUTION_CARRY") or {}
            no_l_s = int(sl_rec_s.get("losses", 0) or 0) == 0 and (
                sleeve_src != "UMA_READY1_LIVENESS_PRIORITY" or int(b1_rec_s.get("losses", 0) or 0) == 0
            )
            d1_s_ok = _grad8_s(by_sl_map.get("D1_SAME_ORACLE_DOMINANCE_BOX") or {})
            _prob_mkr_sleeves = {"W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK", "W_SOLAR1_POST_2351_LOCK", "SP2_NBA_ENDGAME_LOCK", "U1_DAILY_UPDOWN_LOCK", "CM_B2_PYTH_SESSION_NO_LOCK", "CM_U1_PYTH_CLOSE_LOCK"}
            _ro_mkr = bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {}).get("riskless_only_mode", False)) and not self.dry_run
            _prob_mkr_ok = not (_ro_mkr and sleeve_src in _prob_mkr_sleeves) or float(candidate_box.get("p_model") or 0.0) >= 0.999
            own_mkr_grad = (
                (_grad8_s(sl_rec_s) or (sleeve_src == "UMA_READY1_LIVENESS_PRIORITY" and _grad8_s(b1_rec_s)))
                and no_l_s
                and _prob_mkr_ok
            )
            _v3_mkr_cfg_ok = bool(_rb_mkr_gov.get("enable_ungraduated_v3_math_live", False)) if _enforce_paused_mkr else bool(_rcfg_sll.get("enable_ungraduated_v3_math_live", False) or _rb_mkr_gov.get("enable_ungraduated_v3_math_live", False))
            _v3_mkr_det = (
                _v3_mkr_cfg_ok
                and (not _enforce_paused_mkr or sleeve_src.upper() not in _paused_mkr_set)
                and (sleeve_src in PROTOCOL_V2_MATH_SLEEVES or sleeve_src.startswith("SP4_") or sleeve_src in {"SP2_NBA_ENDGAME_LOCK", "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH", "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK", "B4_TOUCHED_BARRIER_WICK_LOCK", "GAS1_AAA_GASOLINE_LOCK", "W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK", "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR", "AFF1_FROZEN_SUBPERIOD_COLLAPSE", "NFL_PRP1_MILESTONE_AND_MAX_LOCKS", "U1_DAILY_UPDOWN_LOCK", "CM_B2_PYTH_SESSION_NO_LOCK", "CM_U1_PYTH_CLOSE_LOCK"})
            )
            bond1_mkr_bridge = bool(
                (no_l_s and _is_inv_comp_mkr)
                or (
                    no_l_s
                    and d1_s_ok
                    and (
                        (sleeve_src in {"BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", "UMA_READY1_LIVENESS_PRIORITY"} and _rcfg_sll.get("enable_bond1_live_bridge", True) and float(sl_rec_s.get("realized_pnl_t1000_usd", 0.0) or 0.0) >= 0.0 and (int(sl_rec_s.get("closed", 0) or 0) == 0 or float(sl_rec_s.get("win_rate_pct", 100.0) or 0.0) >= 100.0))
                        or (not self.dry_run and self._is_v5_unleashed_active() and _is_mlk1 and float(candidate_box.get("p_model") or 0.0) >= (0.999 if _ro_mkr else 0.998))
                        or (not self.dry_run and _is_rw_carry and float(candidate_box.get("p_model") or 0.0) >= 0.999 and (bool(_rb_mkr_gov.get("enable_reward_locked_carry_live_bridge", True)) or not _enforce_paused_mkr))
                        or (not self.dry_run and _is_s2_mkr and float(candidate_box.get("p_model") or 0.0) >= 0.9985 and (bool(_rb_mkr_gov.get("enable_s2_twap_lock_live", True)) or not _enforce_paused_mkr))
                        or (not self.dry_run and self._is_v5_unleashed_active() and (_is_wp_mkr or _v3_mkr_det) and float(candidate_box.get("p_model") or 0.0) >= 0.999)
                    )
                )
            )
            if not (own_mkr_grad or bond1_mkr_bridge):
                return {"executed": False, "reason": f"SINGLE_LEG_MAKER_NOT_GRADUATED:{sleeve_src}"}
            if _is_rw_carry:
                from src.polymarket_research.riskless_protocol_v2_expansion import is_disputed_or_frozen_uma_position as _is_df_rw
                _eq_rw_est = float(getattr(self, "_last_known_collateral", None) or 0.0) + sum(
                    float(p.get("notional_usd", 0.0) or 0.0)
                    for p in self.active_positions.values()
                    if not position_is_settlement_receivable(p) and not _is_df_rw(p, now_ts)
                )
                if compute_dynamic_riskless_tier_caps(_eq_rw_est, _rb_mkr_gov).get("reward_unlocked"):
                    self._last_rw_carry_cand_ts = now_ts
        except Exception as exc_s:
            return {"executed": False, "reason": f"STATE_READ_ERROR:{exc_s}"}

        exp_ts = float(candidate_box.get("expiry_ts") or 0.0)
        cand_ts = float(candidate_box.get("ts_unix") or now_ts)
        _min_sll_tte = 4.8 if _is_s2_mkr else (45.0 if (_is_mlk1 or _is_inv_comp_mkr or sleeve_src in {"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", "UMA_READY1_LIVENESS_PRIORITY"}) else 90.0)
        _max_sll_tte = 39.0 if _is_s2_mkr else (86400.0 if (_is_rw_carry or _is_inv_comp_mkr or _is_wp_mkr) else 86400.0)
        _max_sll_age = 2.5 if _is_s2_mkr else float(_rb_mkr_gov.get("ipc_candidate_max_age_sec", 60.0) or 60.0)
        if not self.dry_run and ((now_ts - cand_ts) > _max_sll_age or (exp_ts > 0.0 and not (_min_sll_tte <= (exp_ts - now_ts) <= _max_sll_tte))):
            return {"executed": False, "reason": "STALE_OR_OUTSIDE_TTE_WINDOW"}
        _prepost_res = self.__dict__.setdefault("_prepost_sll_reserved_usd", {})
        _prepost_mkts = self.__dict__.setdefault("_prepost_sll_markets", {})
        _prepost_evts = self.__dict__.setdefault("_prepost_sll_events", {})
        if _is_inv_comp_mkr:
            if any(
                not position_is_settlement_receivable(_pm_d) and str(_pm_d.get("token_id") or "").strip() == tok_a
                for _pm_d in self.active_positions.values()
            ) or any(
                isinstance(_im_d, dict) and str(_im_d.get("token_id") or "").strip() == tok_a
                for _im_d in getattr(self, "pending_entry_intents", {}).values()
            ):
                return {"executed": False, "reason": "MARKET_ALREADY_OCCUPIED"}
        elif is_market_busy_for_scaling(self, mid_a, extra_busy_markets=list(_prepost_mkts.values())):
            return {"executed": False, "reason": "MARKET_ALREADY_OCCUPIED"}

        active_box_ids = self._active_box_ids()
        _gsn_s = GLOBAL_GOVERNANCE_MANAGER.snapshot
        _b1_gov = _gsn_s.get("riskless_boxes", {})
        max_conc_sll = int(_rcfg_sll.get("max_concurrent_d1_boxes", 4))
        max_tot_sll = int(_rcfg_sll.get("max_total_portfolio_slots", 4))
        if self._is_v5_unleashed_active():
            max_conc_sll = int(_b1_gov.get("max_concurrent_riskless_boxes", 10))
            max_tot_sll = int(_gsn_s.get("sizing_tiers", {}).get("max_total_slots", 12))
        if len(active_box_ids) >= max_conc_sll or (not self.dry_run and (len(active_box_ids) + len(self._risk_bearing_positions())) >= max_tot_sll):
            return {"executed": False, "reason": "MAX_CONCURRENT_BOXES_REACHED"}
        if max_conc_sll >= 2 and exp_ts > 0.0 and (exp_ts - now_ts) > 3600.0 and len(active_box_ids) >= (max_conc_sll - 1):
            return {"executed": False, "reason": "INTRADAY_D1_SLOT_RESERVED"}

        _repost_n_in = int(candidate_box.get("_bond1_repost_count") or 0)
        if not self.dry_run and (
            dedupe_k in inflight_mkr
            or mkr_type_k in inflight_mkr_types
            or mid_a in _prepost_mkts.values()
            or any(str(i.get("market_id") or "") == mid_a for i in getattr(self, "pending_entry_intents", {}).values() if isinstance(i, dict))
        ):
            return {"executed": False, "reason": "SINGLE_LEG_MAKER_ALREADY_INFLIGHT"}
        _enforce_b1_v53 = bool(
            getattr(self, "enforce_bond1_smart_queue", False)
            or (
                not self.dry_run
                and getattr(self.executor, "client", None) is not None
                and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                and "post_maker_entry_order" not in getattr(self.executor, "__dict__", {})
            )
        )
        box_id = str(candidate_box.get("box_id") or f"MKR_LOCK1_{int(now_ts)}")
        intent_id = f"{box_id}_SLL_INTENT"
        evt_k = extract_sll_event_group_key(candidate_box)
        _evt_ok_mkr, _evt_rsn_mkr, _evt_rem_mkr, _evt_gk_mkr = check_per_event_concentration_cap(
            self, candidate_box, market_ids=[mid_a], now_ts=now_ts,
            enforce_override=bool(_enforce_b1_v53 and _b1_gov.get("enable_event_slot_diversification", True)),
            exclude_intent_ids=(intent_id,),
        )
        if not _evt_ok_mkr:
            return {"executed": False, "reason": _evt_rsn_mkr}
        evt_k = _evt_gk_mkr or evt_k or (f"MKT:{mid_a}" if mid_a else "")
        if not self.dry_run and evt_k:
            _prepost_evts[intent_id] = {
                "trade_id": intent_id,
                "market_id": mid_a,
                "condition_id": cid_a,
                "inflight_key": dedupe_k,
                "event_group_key": evt_k,
                "event_id": candidate_box.get("event_id"),
                "title": candidate_box.get("title"),
                "leg_a_label": candidate_box.get("leg_a_label"),
                "asset": cand_asset,
                "expiry_ts": exp_ts,
                "notional_usd": 5.0,
                "live_maker_anchor_inflight": True,
            }
        try:
            collat = getattr(self, "_last_known_collateral", None)
            _skip_repeg_collat = bool(
                _repost_n_in > 0
                and candidate_box.get("_repeg_zero_fill")
                and collat is not None
                and "get_collateral_balance" not in getattr(self.executor, "__dict__", {})
            )
            if not self.dry_run and (collat is None or (_repost_n_in > 0 and not _skip_repeg_collat)) and hasattr(self.executor, "get_collateral_balance"):
                _prev_c_sll = collat
                try:
                    _fresh_c = await asyncio.to_thread(self.executor.get_collateral_balance)
                    if isinstance(_fresh_c, (int, float)) and not isinstance(_fresh_c, bool) and math.isfinite(float(_fresh_c)) and float(_fresh_c) >= 0.0:
                        collat = float(_fresh_c)
                        self._last_known_collateral = collat
                        sync_pending_intents_on_collateral_refresh(self, _prev_c_sll, collat)
                except Exception:
                    if collat is None:
                        collat = 0.0
            if not self.dry_run and (
                dedupe_k in inflight_mkr
                or mkr_type_k in inflight_mkr_types
                or mid_a in _prepost_mkts.values()
                or any(str(i.get("market_id") or "") == mid_a for i in getattr(self, "pending_entry_intents", {}).values() if isinstance(i, dict))
            ):
                _prepost_evts.pop(intent_id, None)
                return {"executed": False, "reason": "SINGLE_LEG_MAKER_ALREADY_INFLIGHT"}
            _evt_ok_mkr, _evt_rsn_mkr, _evt_rem_mkr, _evt_gk_mkr2 = check_per_event_concentration_cap(
                self, candidate_box, market_ids=[mid_a], now_ts=now_ts,
                enforce_override=bool(_enforce_b1_v53 and _b1_gov.get("enable_event_slot_diversification", True)),
                exclude_intent_ids=(intent_id,),
            )
            if not _evt_ok_mkr:
                _prepost_evts.pop(intent_id, None)
                return {"executed": False, "reason": _evt_rsn_mkr}
            evt_k = _evt_gk_mkr2 or evt_k
            _b1_q_cap = float(_rcfg_sll.get("bond1_max_join_queue_usd", _b1_gov.get("bond1_max_join_queue_usd", 350.0)) or 350.0)
            _b1_buried_s = float(_rcfg_sll.get("bond1_buried_cancel_sec", _b1_gov.get("bond1_buried_cancel_sec", 15.0)) or 15.0)
            budget, _open_mid_u, _ = compute_sll_entry_budget(
                self, sleeve_src, mid_a, collat, own_mkr_grad, _enforce_b1_v53, _b1_gov, _rcfg_sll, _gsn_s, exp_ts - now_ts, now_ts
            )
            budget = min(budget, _evt_rem_mkr)
            min_rb = float(candidate_box.get("min_resting_bid", 0.02 if _is_inv_comp_mkr else 0.940) or (0.02 if _is_inv_comp_mkr else 0.940))
            max_rb = min(0.998, float(candidate_box.get("max_box_cost_net", 0.994) or 0.994))
            if _is_inv_comp_mkr:
                from src.polymarket_research.riskless_protocol_v2_expansion import resolve_unencumbered_partner_inventory_and_leg_cap
                _held_partner_mkr_sh, _partner_cost_ps_mkr, _inv_leg_cap_mkr = resolve_unencumbered_partner_inventory_and_leg_cap(
                    self, candidate_box, _partner_tok_mkr, default_max_box_net=0.994, now_ts=now_ts, exclude_intent_id=intent_id, verify_wallet=False
                )
                if _held_partner_mkr_sh < 5.0:
                    return {"executed": False, "reason": "PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
                max_rb = min(max_rb, _inv_leg_cap_mkr)
                if max_rb < min_rb or max_rb <= 0.01:
                    _prepost_evts.pop(intent_id, None)
                    return {"executed": False, "reason": f"PARTNER_COST_BASIS_EXCEEDS_BOX_CAP:{max_rb:.4f}"}
            max_opp = float(candidate_box.get("max_opp_bid", 0.99 if _is_inv_comp_mkr else 0.008) or (0.99 if _is_inv_comp_mkr else 0.008))
            anc_bid_px = float(candidate_box.get("anchor_bid_px") or candidate_box.get("leg_a_limit_price") or 0.0)
            if not (min_rb <= anc_bid_px <= max_rb):
                _prepost_evts.pop(intent_id, None)
                return {"executed": False, "reason": f"RESTING_BID_OUT_OF_BAND:{anc_bid_px:.4f}"}
            budget = await maybe_preempt_mlk1_if_bond1_starved(
                self, sleeve_src, budget, collat, own_mkr_grad, _enforce_b1_v53, _b1_gov, _rcfg_sll, _gsn_s, _open_mid_u, exp_ts - now_ts, now_ts, compute_d1_per_market_notional_cap(self) if _open_mid_u > 0.0 else 0.0, cand_bid_px=anc_bid_px
            )
            budget = min(budget, _evt_rem_mkr)
            uma_floor_h = sll_settlement_lag_floor_hours(sleeve_src)
            cand_vel_bps = round(((1.0 - anc_bid_px) * 10000.0) / max(uma_floor_h, (exp_ts - now_ts) / 3600.0), 2) if exp_ts > now_ts else 0.0
            _cand_ask_d = candidate_box.get("ask_depth_usd")
            _cand_vol24 = candidate_box.get("volume_24h_usd", candidate_box.get("volume24hr"))
            _cand_tot_vol = candidate_box.get("total_volume_usd")
            _has_cand_vol = (_cand_vol24 is not None) or (_cand_tot_vol is not None)
            _eff_cand_vol = (
                max(float(_cand_vol24 or 0.0), float(_cand_tot_vol or 0.0) * 0.5)
                if _has_cand_vol
                else None
            )
            _max_cand_vol = (
                max(float(_cand_vol24 or 0.0), float(_cand_tot_vol or 0.0))
                if _has_cand_vol
                else None
            )
            if (
                not self.dry_run
                and not _is_s2_mkr
                and sleeve_src != "MKR_REWARD_LOCKED_CARRY"
                and _cand_ask_d is not None
                and float(_cand_ask_d or 0.0) < 5.0
                and _max_cand_vol is not None
                and _max_cand_vol < 25.0
            ):
                _prepost_evts.pop(intent_id, None)
                if dedupe_k:
                    retry_cd[dedupe_k] = time.time() + 300.0
                return {"executed": False, "reason": "GHOST_ZERO_VOLUME_BOOK"}
            _cand_vel_supply_mult = 1.0
            if _cand_ask_d is not None and _eff_cand_vol is not None:
                _ask_f = float(_cand_ask_d or 0.0)
                if _ask_f < 5.0:
                    if _eff_cand_vol < 25.0:
                        _cand_vel_supply_mult = 0.04
                    elif _eff_cand_vol < 500.0:
                        _cand_vel_supply_mult = 0.15
                    elif _eff_cand_vol < 1500.0:
                        _cand_vel_supply_mult = 0.65
                    elif _eff_cand_vol >= 2500.0:
                        _cand_vel_supply_mult = 1.10
                elif _ask_f >= 10.0 and _eff_cand_vol >= 1000.0:
                    _cand_vel_supply_mult = 1.15
            _cand_edge_hr = round(cand_vel_bps * _cand_vel_supply_mult, 2)
            min_lot_shares = 5
            sh_int = int(math.floor(budget / anc_bid_px))
            if _is_inv_comp_mkr and _held_partner_mkr_sh > 0.0:
                sh_int = min(sh_int, int(math.floor(_held_partner_mkr_sh + 1e-9)))
            _fan_active_sll = bool(
                (getattr(self, "enforce_gatling_sizing", False) or getattr(self, "enforce_gatling_fast_gun_reserve", False) or (not self.dry_run and getattr(self.executor, "client", None) is not None and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None and "get_market_book" not in getattr(self.executor, "__dict__", {}) and not getattr(self, "enforce_bond1_smart_queue", False)))
                and float(_b1_gov.get("bond1_maker_fanout_clip_usd_seed") or 0.0) > 0.0
                and float(collat or 0.0) < 150.0
            )
            if (
                not _is_s2_mkr
                and sh_int < (min_lot_shares if _fan_active_sll else 12)
                and not self.dry_run
                and anc_bid_px >= min_rb
                and cand_vel_bps >= 40.0
                and self._is_v5_unleashed_active()
            ):
                _vel_mult = float(_b1_gov.get("bond1_velocity_preempt_mult", 1.80) or 1.80)
                _pe_map = getattr(self, "_maker_anchor_preempt_events", {})
                _claimed_pe = self.__dict__.setdefault("_claimed_velocity_preempts", set())
                _slow_vel, _slow_k = select_sll_velocity_preempt_target(self, _cand_edge_hr, _is_s2_mkr, _vel_mult, cand_sleeve=sleeve_src)
                if _slow_k:
                    _proj_b, _, _ = compute_sll_entry_budget(
                        self, sleeve_src, mid_a, collat, own_mkr_grad, _enforce_b1_v53, _b1_gov, _rcfg_sll, _gsn_s, exp_ts - now_ts, now_ts, post_vel_preempt=True, exclude_inflight_key=_slow_k
                    )
                    if int(math.floor(_proj_b / anc_bid_px)) < min_lot_shares:
                        _slow_k = ""
                if _slow_k:
                    _claimed_pe.add(_slow_k)
                    try:
                        (self.__dict__.setdefault("_maker_anchor_preempt_reasons", {}))[_slow_k] = f"VELOCITY_UPGRADE:{dedupe_k}"
                        logger.info(f"[BOND1 VELOCITY UPGRADE] Preempting {_slow_k} ({_slow_vel:.1f} bps/h) -> {dedupe_k} ({_cand_edge_hr:.1f} bps/h @ ${anc_bid_px:.3f})")
                        _pe_map[_slow_k].set()
                        for _ in range(16):
                            await asyncio.sleep(0.06)
                            if not any(isinstance(i, dict) and i.get("inflight_key") == _slow_k for i in self.pending_entry_intents.values()):
                                break
                    finally:
                        _claimed_pe.discard(_slow_k)
                    collat = getattr(self, "_last_known_collateral", collat)
                    budget, _open_mid_u, _ = compute_sll_entry_budget(
                        self, sleeve_src, mid_a, collat, own_mkr_grad, _enforce_b1_v53, _b1_gov, _rcfg_sll, _gsn_s, exp_ts - now_ts, now_ts, post_vel_preempt=True
                    )
                    budget = min(budget, _evt_rem_mkr)
                    sh_int = int(math.floor(budget / anc_bid_px))
                    if _is_inv_comp_mkr and _held_partner_mkr_sh > 0.0:
                        sh_int = min(sh_int, int(math.floor(_held_partner_mkr_sh + 1e-9)))
            if _is_inv_comp_mkr:
                _held_partner_mkr_sh, _partner_cost_ps_mkr, _inv_leg_cap_mkr2 = resolve_unencumbered_partner_inventory_and_leg_cap(
                    self, candidate_box, _partner_tok_mkr, default_max_box_net=0.994, now_ts=time.time(), exclude_intent_id=intent_id, verify_wallet=False
                )
                max_rb = min(max_rb, _inv_leg_cap_mkr2)
                sh_int = min(sh_int, int(math.floor(_held_partner_mkr_sh + 1e-9)))
                if _held_partner_mkr_sh < min_lot_shares or anc_bid_px > max_rb + 1e-6:
                    _prepost_evts.pop(intent_id, None)
                    return {"executed": False, "reason": "PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
            if sh_int < min_lot_shares:
                _prepost_evts.pop(intent_id, None)
                if not self.dry_run and dedupe_k:
                    retry_cd[dedupe_k] = time.time() + (2.0 if _is_s2_mkr else 8.0)
                return {"executed": False, "reason": "INSUFFICIENT_MAKER_BOX_BUDGET"}
            if _is_s2_early and not await maybe_preempt_low_tier_s2_maker_slot(self, cand_asset, inflight_s2_mkr):
                _prepost_evts.pop(intent_id, None)
                return {"executed": False, "reason": "S2_MAKER_CONCURRENT_CAP_1"}
        except BaseException:
            _prepost_evts.pop(intent_id, None)
            (self.__dict__.get("_prepost_partner_pledged_shares") or {}).pop(intent_id, None)
            raise

        inflight_key = dedupe_k
        inflight_mkr.add(inflight_key)
        inflight_mkr_types.add(mkr_type_k)
        if _is_s2_early:
            inflight_s2_mkr.add(inflight_key)
        preempt_events = self.__dict__.setdefault("_maker_anchor_preempt_events", {})
        preempt_ev = threading.Event()
        preempt_events[inflight_key] = preempt_ev
        _prepost_res[intent_id] = round(sh_int * anc_bid_px, 4)
        _prepost_mkts[intent_id] = mid_a
        if _is_inv_comp_mkr:
            self.__dict__.setdefault("_prepost_partner_pledged_shares", {})[intent_id] = (_partner_tok_mkr, float(sh_int))
        if intent_id in _prepost_evts:
            _prepost_evts[intent_id]["notional_usd"] = round(sh_int * anc_bid_px, 4)
        _tk_wf = 0.0
        mkt_ws_s = getattr(self, "_pos_market_ws", None)
        if mkt_ws_s is not None and hasattr(mkt_ws_s, "subscribe_tokens_immediate"):
            mkt_ws_s.subscribe_tokens_immediate([tok_a, opp_a])
        _ws_bk_ev = asyncio.Event()
        self.__dict__.setdefault("_sll_ws_book_events", {})[intent_id] = (tok_a, opp_a, _ws_bk_ev)
        try:
            if self.dry_run:
                pre_bal_a = 0.0
            elif hasattr(self.executor, "get_market_book"):
                custom_bk_s = "get_market_book" in getattr(self.executor, "__dict__", {})
                ws_bks_s = candidate_box.get("ws_books") if not custom_bk_s else None
                ws_s_fresh = isinstance(ws_bks_s, dict) and (time.time() - float(candidate_box.get("ws_books_ts") or 0.0)) <= 0.65
                _ws_age_lim = 0.85 if _repost_n_in > 0 else 1.5
                bk_win_f = ws_bks_s.get(tok_a) if ws_s_fresh else (mkt_ws_s.get_book(tok_a, max_age_sec=_ws_age_lim) if (mkt_ws_s and not custom_bk_s) else None)
                bk_opp_f = ws_bks_s.get(opp_a) if ws_s_fresh else (mkt_ws_s.get_book(opp_a, max_age_sec=_ws_age_lim) if (mkt_ws_s and not custom_bk_s) else None)
                if isinstance(bk_win_f, dict) and bk_win_f.get("is_partial_delta") and (not bk_win_f.get("bids") or not bk_win_f.get("asks")):
                    bk_win_f = None
                if isinstance(bk_opp_f, dict) and bk_opp_f.get("is_partial_delta") and not bk_opp_f.get("bids"):
                    bk_opp_f = None
                if bk_win_f is None or bk_opp_f is None:
                    pre_bal_a, bk_win_f, bk_opp_f = await asyncio.gather(
                        self._resolve_fast_pre_token_balance_async(tok_a, exclude_intent_id=intent_id),
                        asyncio.to_thread(self.executor.get_market_book, tok_a) if bk_win_f is None else asyncio.sleep(0, result=bk_win_f),
                        asyncio.to_thread(self.executor.get_market_book, opp_a) if bk_opp_f is None else asyncio.sleep(0, result=bk_opp_f),
                    )
                    if mkt_ws_s is not None and not custom_bk_s and hasattr(mkt_ws_s, "seed_book"):
                        if isinstance(bk_win_f, dict):
                            mkt_ws_s.seed_book(tok_a, bk_win_f)
                        if isinstance(bk_opp_f, dict):
                            mkt_ws_s.seed_book(opp_a, bk_opp_f)
                else:
                    pre_bal_a = await self._resolve_fast_pre_token_balance_async(tok_a, exclude_intent_id=intent_id)
                _real_clob_sll = (
                    getattr(self.executor, "client", None) is not None
                    and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                )
                _custom_tk_fn = "get_token_tick_size" in getattr(self.executor, "__dict__", {})
                _tk_wf = resolve_harvester_sll_tick_size(
                    self.executor, tok_a, candidate_box, bk_win=bk_win_f, mkt_ws=mkt_ws_s,
                    real_clob=_real_clob_sll, custom_tk_fn=_custom_tk_fn, price_hint=anc_bid_px,
                )
                if _tk_wf <= 0.0 and hasattr(self.executor, "get_token_tick_size") and (_real_clob_sll or _custom_tk_fn):
                    try:
                        _tk_wf = float((await asyncio.to_thread(self.executor.get_token_tick_size, tok_a, anc_bid_px)) or 0.0)
                    except TypeError:
                        _tk_wf = float((await asyncio.to_thread(self.executor.get_token_tick_size, tok_a)) or 0.0)
                    except Exception:
                        _tk_wf = 0.0
                    if _tk_wf > 0.0 and _real_clob_sll:
                        if hasattr(self.executor, "update_ws_tick_size"):
                            self.executor.update_ws_tick_size(tok_a, _tk_wf)
                        if mkt_ws_s is not None and hasattr(mkt_ws_s, "_tick_sizes"):
                            mkt_ws_s._tick_sizes[tok_a] = _tk_wf
                _veto_r, _cd_s, anc_bid_px, sh_int, _tk_wf = eval_sll_fresh_book_and_peg(
                    bk_win_f, bk_opp_f, candidate_box, anc_bid_px, min_rb, max_rb, max_opp, budget,
                    _tk_wf, _real_clob_sll, _enforce_b1_v53, _is_mlk1, _is_s2_mkr, _repost_n_in, _b1_q_cap,
                )
                if _veto_r is not None:
                    if (
                        not self.dry_run
                        and _real_clob_sll
                        and bool(_rb_mkr_gov.get("enable_clinched_dead_leg_split_sell", False))
                        and sleeve_src in {"W_PRUNE1_DEAD_NO_BOND", "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"}
                    ):
                        from src.polymarket_research.stage_c_zero_loss_velocity import (
                            evaluate_clinched_dead_leg_split_arb,
                            execute_clinched_dead_leg_split_arb,
                        )
                        _evt_ok_sp, _evt_rsn_sp, _evt_rem_sp, _ = check_per_event_concentration_cap(
                            self, candidate_box, market_ids=[mid_a], now_ts=now_ts,
                            enforce_override=bool(_enforce_b1_v53 and _b1_gov.get("enable_event_slot_diversification", True)),
                            exclude_intent_ids=(intent_id,),
                        )
                        _sp_plan = (
                            evaluate_clinched_dead_leg_split_arb(
                                candidate_box,
                                bk_opp_f,
                                budget_usd=min(budget, _evt_rem_sp),
                                now_ts=now_ts,
                                executor=self.executor,
                            )
                            if _evt_ok_sp
                            else None
                        )
                        if _sp_plan is not None:
                            _sp_plan = {**_sp_plan, "market_id": mid_a, "exclude_intent_ids": [intent_id]}
                            _sp_res = await asyncio.to_thread(
                                execute_clinched_dead_leg_split_arb, self, candidate_box, _sp_plan, now_ts=now_ts
                            )
                            if _sp_res.get("executed") or _sp_res.get("split_tx_hash") or _sp_res.get("merged_pairs"):
                                if dedupe_k:
                                    if hasattr(self, "_record_seen_d1_box_key"):
                                        self._record_seen_d1_box_key(dedupe_k)
                                    else:
                                        seen_boxes.add(dedupe_k)
                                return _sp_res
                    if _cd_s > 0.0:
                        retry_cd[dedupe_k] = time.time() + _cd_s
                    return {"executed": False, "reason": _veto_r}
                if _is_inv_comp_mkr and _held_partner_mkr_sh > 0.0:
                    sh_int = min(sh_int, int(math.floor(_held_partner_mkr_sh + 1e-9)))
                    if sh_int < min_lot_shares:
                        return {"executed": False, "reason": "PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
                _prepost_res[intent_id] = round(sh_int * anc_bid_px, 4)
            else:
                pre_bal_a = await self._resolve_fast_pre_token_balance_async(tok_a, exclude_intent_id=intent_id)

            _raw_nr_a = candidate_box.get("leg_a_neg_risk")
            nr_a = _raw_nr_a if isinstance(_raw_nr_a, bool) else None
            if hasattr(self.executor, "prewarm_token_market_cache"):
                use_mock_tk = self.dry_run or hasattr(getattr(self.executor, "client", None), "_mock_children")
                cand_tk = candidate_box.get("leg_a_tick_size") if use_mock_tk else (_tk_wf if _tk_wf > 0.0 else None)
                _mkt_fr = max(0.0, float(candidate_box.get("leg_a_market_fee_rate") or candidate_box.get("leg_a_fee_rate") or 0.0))
                _mkt_fe = max(1.0, float(candidate_box.get("leg_a_market_fee_exponent") or candidate_box.get("leg_a_fee_exponent") or 1.0))
                try:
                    self.executor.prewarm_token_market_cache(
                        token_id=tok_a, tick_size=cand_tk, neg_risk=bool(nr_a),
                        fee_rate_bps=int(round(_mkt_fr * 10000.0)),
                        condition_id=(cid_a if str(cid_a or "").startswith("0x") else None),
                        fee_rate=_mkt_fr, fee_exponent=_mkt_fe, preserve_fee_cache=(_mkt_fr <= 0.0),
                    )
                except TypeError:
                    self.executor.prewarm_token_market_cache(
                        token_id=tok_a, tick_size=cand_tk, neg_risk=bool(nr_a),
                        fee_rate_bps=int(round(_mkt_fr * 10000.0)),
                        condition_id=(cid_a if str(cid_a or "").startswith("0x") else None),
                        fee_rate=_mkt_fr, fee_exponent=_mkt_fe,
                    )

            anc_notional = round((sh_int + 0.01) * anc_bid_px, 4)
            now_int_ts = time.time()
            if not self.dry_run:
                _evt_ok_post, _evt_rsn_post, _evt_rem_post, _ = check_per_event_concentration_cap(
                    self, candidate_box, market_ids=[mid_a], now_ts=now_int_ts,
                    enforce_override=bool(_enforce_b1_v53 and _b1_gov.get("enable_event_slot_diversification", True)),
                    exclude_intent_ids=(intent_id,),
                )
                if not _evt_ok_post:
                    return {"executed": False, "reason": _evt_rsn_post}
                if _evt_rem_post < round(sh_int * anc_bid_px, 4) - 0.05:
                    sh_int = int(math.floor(_evt_rem_post / anc_bid_px))
                    if _is_inv_comp_mkr and _held_partner_mkr_sh > 0.0:
                        sh_int = min(sh_int, int(math.floor(_held_partner_mkr_sh + 1e-9)))
                    if sh_int < min_lot_shares:
                        return {"executed": False, "reason": "MAX_EVENT_NOTIONAL_CAP_REACHED"}
                    anc_notional = round((sh_int + 0.01) * anc_bid_px, 4)
            _orig_post_ts = float(candidate_box.get("_bond1_first_post_ts") or now_int_ts)
            _init_fifo_r1 = bool(candidate_box.get("queue_front") and float(candidate_box.get("queue_ahead_usd") or 0.0) <= 5.0)
            if not self.dry_run:
                self._mark_token_pre_bal_dirty(tok_a)
            _t_b1 = time.perf_counter()
            _use_async_mkr_post = bool(
                not self.dry_run
                and "post_maker_entry_order" not in getattr(self.executor, "__dict__", {})
                and hasattr(self.executor, "post_maker_entry_order_async")
                and bool(getattr(self.executor, "_can_use_native_async_post_order", lambda: False)())
            )
            _mkr_px_floor = max(0.02 if _is_inv_comp_mkr else (0.50 if _is_s2_mkr else 0.90), min_rb)
            _mkr_px_ceil = max_rb if _is_inv_comp_mkr else max(0.995, max_rb)
            if _use_async_mkr_post:
                post_res = await self.executor.post_maker_entry_order_async(
                    token_id=tok_a, price=anc_bid_px, notional_usd=anc_notional, side="BUY",
                    neg_risk=nr_a, min_price_floor=_mkr_px_floor, max_price_ceiling=_mkr_px_ceil,
                )
            else:
                post_res = await asyncio.to_thread(
                    self.executor.post_maker_entry_order,
                    token_id=tok_a, price=anc_bid_px, notional_usd=anc_notional, side="BUY",
                    neg_risk=nr_a, min_price_floor=_mkr_px_floor, max_price_ceiling=_mkr_px_ceil,
                )
            _b1_post_ms = round((time.perf_counter() - _t_b1) * 1000.0, 2)
            self.__dict__.setdefault("_sll_post_http_ms", deque(maxlen=128)).append(_b1_post_ms)
            maker_oid = str((post_res or {}).get("orderID") or "").strip()
            if not isinstance(post_res, dict) or not post_res.get("success") or not maker_oid:
                if not self.dry_run and pre_bal_a == 0.0 and not (post_res or {}).get("outcome_unknown"):
                    (self.__dict__.get("_d1_dirty_token_until") or {}).pop(tok_a, None)
                _prepost_res.pop(intent_id, None)
                _prepost_mkts.pop(intent_id, None)
                _prepost_evts.pop(intent_id, None)
                (self.__dict__.get("_prepost_partner_pledged_shares") or {}).pop(intent_id, None)
                self.pending_entry_intents.pop(intent_id, None)
                if _emit_shock_attempt is not None:
                    _emit_shock_attempt({
                        "dry_run": self.dry_run, "asset": cand_asset or "BOND1", "horizon": "box", "side": side_s,
                        "market_id": mid_a, "title": str(candidate_box.get("title") or box_id), "sleeve": sleeve_src,
                        "path_type": "MAKER_BOX", "target_px": float((post_res or {}).get("price") or anc_bid_px), "notional_usd": anc_notional, "http_ms": _b1_post_ms,
                        "stage_outcome": "BOND1_MAKER_POST_FAILED", "gate_detail": str((post_res or {}).get("error") or ""),
                    })
                return {"executed": False, "reason": f"BOND1_MAKER_POST_FAILED:{(post_res or {}).get('error')}"}
            posted_px = float(post_res.get("price") or anc_bid_px)
            posted_sh = float(post_res.get("shares") or sh_int)
            _tk_wf = sync_harvester_sll_enforced_tick(self.executor, mkt_ws_s, tok_a, _tk_wf)
            _now_p = time.time()
            _prepost_res.pop(intent_id, None)
            _prepost_mkts.pop(intent_id, None)
            _prepost_evts.pop(intent_id, None)
            (self.__dict__.get("_prepost_partner_pledged_shares") or {}).pop(intent_id, None)
            _posted_nom_vel = round(((1.0 - posted_px) * 10000.0) / max(uma_floor_h, (exp_ts - _now_p) / 3600.0), 2) if exp_ts > _now_p else 0.0
            self.pending_entry_intents[intent_id] = {
                "trade_id": intent_id, "market_id": mid_a, "token_id": tok_a, "opp_token_id": opp_a, "anchor_bid_px": posted_px,
                "asset": cand_asset, "entry_order_id": maker_oid, "posted_shares": posted_sh,
                "posted_notional_usd": round(posted_sh * posted_px, 4), "notional_usd": round(posted_sh * posted_px, 4),
                "matched_notional_usd": 0.0, "collat_drop_usd": 0.0,
                "ts": _orig_post_ts, "heartbeat_ts": _now_p, "_last_persist_ts": _now_p,
                "live_maker_anchor_inflight": True, "inflight_key": inflight_key, "sleeve_source": sleeve_src, "event_group_key": evt_k,
                **({"inventory_backed_completion": True, "partner_held_token_id": _partner_tok_mkr, "partner_avg_cost_ps": round(_partner_cost_ps_mkr, 4)} if _is_inv_comp_mkr else {}),
                **({"event_id": str(candidate_box.get("event_id"))} if candidate_box.get("event_id") else {}),
                **({"ask_depth_usd": round(float(_cand_ask_d or 0.0), 2)} if _cand_ask_d is not None else {}),
                **({"volume_24h_usd": round(float(_eff_cand_vol or 0.0), 2)} if _eff_cand_vol is not None else {}),
                **({"effective_velocity_bps_hr": round(_posted_nom_vel * _cand_vel_supply_mult, 2)} if _eff_cand_vol is not None else {}),
                "expiry_ts": exp_ts, "fifo_rank1_verified": _init_fifo_r1,
                "velocity_bps_hr": _posted_nom_vel,
            }
            self._record_ft_candidate_funnel(
                candidate_box, stage="MAKER_POSTED", maker_posted=True, is_maker=True
            )
            if not self.dry_run:
                await asyncio.to_thread(self.save_state)
                if _repost_n_in <= 0 and _stage_b_emit_funnel is not None:
                    try:
                        _stage_b_emit_funnel(
                            "ORDER_SUBMITTED", sleeve=sleeve_src, candidate_key=box_id, box_type="SINGLE_LEG_MAKER_LOCK",
                            asset=str(cand_asset or ""), net_edge_bps=round(max(0.0, 1.0 - posted_px) * 10000.0, 2),
                            est_profit_usd=round(max(0.0, 1.0 - posted_px) * posted_sh, 4), notional_usd=round(posted_sh * posted_px, 4),
                        )
                    except Exception:
                        pass

            _saved_intent: Optional[Dict[str, Any]] = None
            if self.dry_run:
                matched_sh, avg_px = posted_sh, posted_px
                summary = {"matched": matched_sh, "avg_price": avg_px, "cash": round(matched_sh * avg_px, 4), "fee": 0.0, "terminal": True}
                _saved_intent = release_sll_pending_intent(self.pending_entry_intents, intent_id, round(matched_sh * avg_px, 4))
            else:
                uws = getattr(self.executor, "_user_ws_cache", None)
                first_post_ts = _orig_post_ts
                _fp_el = max(0.0, time.time() - first_post_ts) if "_bond1_first_post_ts" in candidate_box else 0.0
                _b1_poll_s = 0.35 if _is_s2_mkr else (float(_rcfg_sll.get("bond1_book_poll_sec", 4.0) or 4.0))
                _last_has_active_asks: Optional[bool] = (
                    bool(float(_cand_ask_d or 0.0) >= 1.0) if _cand_ask_d is not None else None
                )
                t_sll_0 = time.monotonic()
                full_max_keep_s, deadline, _ = compute_sll_maker_keep_and_renew(
                    sleeve_src,
                    uws_ok=bool(uws is not None and uws.is_healthy()),
                    exp_ts=exp_ts,
                    now_ts=time.time(),
                    created_mono=t_sll_0,
                    posted_px=posted_px,
                    rcfg=_rcfg_sll,
                    first_post_elapsed_s=_fp_el,
                    has_active_asks=_last_has_active_asks,
                    matched_notional_usd=0.0,
                    volume_24h_usd=_eff_cand_vol,
                )
                last_opp_chk = t_sll_0
                last_ws_chk = 0.0
                last_fill_poll = t_sll_0
                last_tk_poll = t_sll_0
                last_top_bid_px: Optional[float] = posted_px
                adverse_cancelled = False
                buried_cancelled = False
                buried_since_mono: Optional[float] = None
                outbid_repeg_px: Optional[float] = None
                ws_filled = False
                _consec_blind_bk_polls = 0
                _last_good_bk_mono = t_sll_0
                _use_ws_bk_ev = bool(mkt_ws_s is not None or getattr(self, "_force_sll_ws_events", False))
                try:
                    while time.monotonic() < deadline:
                        _uws_live_ok = bool(uws is not None and uws.is_healthy())
                        _, _, _near_exp = compute_sll_maker_keep_and_renew(
                            sleeve_src, uws_ok=_uws_live_ok, exp_ts=exp_ts, now_ts=time.time(),
                            created_mono=t_sll_0, deadline_mono=deadline, posted_px=posted_px, rcfg=_rcfg_sll,
                            first_post_elapsed_s=_fp_el,
                        )
                        if (
                            preempt_ev.is_set()
                            or getattr(self, "_shutdown_requested", False)
                            or self._is_d1_box_halted()
                            or _near_exp
                        ):
                            break
                        if _enforce_paused_mkr:
                            _rb_live_w = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
                            if (
                                not bool(_rb_live_w.get("enable_single_leg_maker_bond1", True))
                                or sleeve_src.upper() in {str(x).upper() for x in (_rb_live_w.get("paused_riskless_sleeves") or [])}
                                or check_strict_pure_riskless_candidate_gate(self, candidate_box, _rb_live_w, is_maker=True) is not None
                            ):
                                adverse_cancelled = True
                                logger.warning(f"[PURE RISKLESS PREEMPT] {box_id}: single-leg maker disabled/paused by governance; canceling {maker_oid} immediately.")
                                break
                        if _is_s2_mkr and check_s2_live_adverse_move_cancel(cand_asset, side_s, candidate_box, exp_ts):
                            adverse_cancelled = True
                            logger.warning(f"[S2 TWAP SIGMA VETO] {box_id}: SHM cushion < 2.5 sigma; canceling {maker_oid} immediately.")
                            break
                        if intent_id in self.pending_entry_intents:
                            _hb_now = time.time()
                            _it_hb = self.pending_entry_intents[intent_id]
                            _it_hb["heartbeat_ts"] = _hb_now
                            if not self.dry_run and (_hb_now - float(_it_hb.get("_last_persist_ts", 0.0) or 0.0)) >= 30.0:
                                _it_hb["_last_persist_ts"] = _hb_now
                                await asyncio.to_thread(self.save_state)
                        rem_w = max(0.05, min(0.10, deadline - time.monotonic()))
                        if _uws_live_ok:
                            if _use_ws_bk_ev:
                                if _ws_bk_ev.is_set():
                                    await asyncio.sleep(0)
                                else:
                                    _t_fw = asyncio.create_task(uws.wait_for_fill_or_timeout(rem_w, prev_seq=uws.fill_sequence))
                                    _t_bw = asyncio.create_task(_ws_bk_ev.wait())
                                    _, _pend_w = await asyncio.wait({_t_fw, _t_bw}, return_when=asyncio.FIRST_COMPLETED)
                                    for _pw in _pend_w:
                                        _pw.cancel()
                                    await asyncio.gather(*_pend_w, return_exceptions=True)
                            else:
                                await uws.wait_for_fill_or_timeout(rem_w, prev_seq=uws.fill_sequence)
                            snap_o = uws.get_order_snapshot(maker_oid, max_age_sec=5.0)
                            if isinstance(snap_o, dict) and intent_id in self.pending_entry_intents:
                                _ws_m_c = float(snap_o.get("size_matched") or 0.0)
                                if _ws_m_c > 0.0:
                                    if update_sll_intent_partial_fill(self.pending_entry_intents, intent_id, posted_sh, posted_px, _ws_m_c, time.time()) and not self.dry_run:
                                        await asyncio.to_thread(self.save_state)
                            if self._ws_snap_fully_filled(snap_o, posted_sh):
                                ws_filled = True
                                break
                        else:
                            if _use_ws_bk_ev:
                                try:
                                    await asyncio.wait_for(_ws_bk_ev.wait(), timeout=rem_w)
                                except asyncio.TimeoutError:
                                    pass
                            else:
                                await asyncio.sleep(rem_w)
                        if preempt_ev.is_set() or getattr(self, "_shutdown_requested", False):
                            break
                        _ws_bk_triggered = bool(_use_ws_bk_ev and _ws_bk_ev.is_set())
                        if _ws_bk_triggered:
                            _ws_bk_ev.clear()
                        _now_m_chk = time.monotonic()
                        if hasattr(self.executor, "get_market_book") and (
                            (_ws_bk_triggered and (_now_m_chk - last_ws_chk) >= 0.010)
                            or (_now_m_chk - last_opp_chk) >= _b1_poll_s
                        ):
                            last_opp_chk = _now_m_chk
                            if _ws_bk_triggered:
                                last_ws_chk = _now_m_chk
                            custom_bk_l = "get_market_book" in getattr(self.executor, "__dict__", {})
                            _ws_bk_max_age = (
                                1.0
                                if _is_s2_mkr
                                else min(
                                    5.0,
                                    max(1.0, float(_b1_gov.get("maker_ws_book_max_age_sec", 5.0) or 5.0)),
                                )
                            )
                            bk_oc = mkt_ws_s.get_book(opp_a, max_age_sec=_ws_bk_max_age) if (mkt_ws_s and not custom_bk_l) else None
                            bk_wc = mkt_ws_s.get_book(tok_a, max_age_sec=_ws_bk_max_age) if (mkt_ws_s and not custom_bk_l) else None
                            if isinstance(bk_oc, dict) and bk_oc.get("is_partial_delta") and not bk_oc.get("bids"):
                                bk_oc = None
                            if isinstance(bk_wc, dict) and bk_wc.get("is_partial_delta") and (not bk_wc.get("bids") or not bk_wc.get("asks")):
                                bk_wc = None
                            if bk_oc is None or bk_wc is None:
                                try:
                                    bk_oc, bk_wc = await asyncio.gather(
                                        asyncio.to_thread(self.executor.get_market_book, opp_a) if bk_oc is None else asyncio.sleep(0, result=bk_oc),
                                        asyncio.to_thread(self.executor.get_market_book, tok_a) if bk_wc is None else asyncio.sleep(0, result=bk_wc),
                                    )
                                    if mkt_ws_s is not None and not custom_bk_l and hasattr(mkt_ws_s, "seed_book"):
                                        if isinstance(bk_oc, dict):
                                            mkt_ws_s.seed_book(opp_a, bk_oc)
                                        if isinstance(bk_wc, dict):
                                            mkt_ws_s.seed_book(tok_a, bk_wc)
                                except Exception as _bk_poll_exc:
                                    logger.debug(f"[BOND1 BOOK POLL TIMEOUT] {box_id}: {_bk_poll_exc}; blind_polls={_consec_blind_bk_polls + 1}.")
                                    bk_oc, bk_wc = None, None
                            if bk_oc is None or bk_wc is None:
                                _consec_blind_bk_polls += 1
                                _max_blind_polls = max(1, int(_b1_gov.get("maker_max_consecutive_blind_book_polls", 3) or 3))
                                _max_blind_age_s = 3.5 if _is_s2_mkr else 12.0
                                if _consec_blind_bk_polls >= _max_blind_polls or (time.monotonic() - _last_good_bk_mono) >= _max_blind_age_s:
                                    adverse_cancelled = True
                                    logger.warning(
                                        f"[MAKER BLIND BOOK FAIL-CLOSED CANCEL] {box_id}: {_consec_blind_bk_polls} blind book polls "
                                        f"(age={time.monotonic() - _last_good_bk_mono:.1f}s); canceling {maker_oid} immediately."
                                    )
                                    break
                            if bk_oc is not None and bk_wc is not None:
                                _consec_blind_bk_polls = 0
                                _last_good_bk_mono = time.monotonic()
                                _prev_tk_wf = _tk_wf
                                _tk_wf = sync_harvester_sll_enforced_tick(self.executor, mkt_ws_s, tok_a, _tk_wf, bk_wc=bk_wc)
                                _c400_live = getattr(self.executor, "_clob_400_tick_until", None)
                                _c400_pinned = isinstance(_c400_live, dict) and tok_a in _c400_live and time.monotonic() < float(_c400_live[tok_a][1])
                                if not _c400_pinned and (_tk_wf <= 0.0 or _tk_wf >= 0.01):
                                    _ws_tk_now = float(mkt_ws_s.get_tick_size(tok_a) or 0.0) if (mkt_ws_s is not None and hasattr(mkt_ws_s, "get_tick_size")) else 0.0
                                    if 0.0001 <= _ws_tk_now < 0.01:
                                        _tk_wf = _ws_tk_now
                                    elif _is_s2_mkr and posted_px >= 0.96 and hasattr(self.executor, "get_token_tick_size") and (time.monotonic() - last_tk_poll) >= 2.5:
                                        last_tk_poll = time.monotonic()
                                        try:
                                            _sdk_tk_now = float((await asyncio.to_thread(self.executor.get_token_tick_size, tok_a, posted_px)) or 0.0)
                                            if 0.0001 <= _sdk_tk_now < 0.01:
                                                _tk_wf = _sdk_tk_now
                                        except Exception:
                                            pass
                                candidate_box["_posted_notional_usd"] = round(posted_sh * posted_px, 2)
                                _cur_top_b = extract_top_bid_from_book(bk_wc)
                                _raw_b_wc = (bk_wc.get("bids") or []) if isinstance(bk_wc, dict) else []
                                _above_q_u = sum(
                                    float(b["price"] if isinstance(b, dict) else b[0]) * float(b["size"] if isinstance(b, dict) else b[1])
                                    for b in _raw_b_wc
                                    if float(b["price"] if isinstance(b, dict) else b[0]) > posted_px + 1e-6
                                )
                                _is_outbid_now = (
                                    (_cur_top_b is not None)
                                    and (float(_cur_top_b) > posted_px + 1e-6)
                                    and (_above_q_u > 50.0)
                                )
                                _now_sll_p = time.time()
                                _eff_buried_s = prepare_sll_stalk_guard(
                                    self, dedupe_k, candidate_box, _repost_n_in, time.monotonic() - t_sll_0,
                                    int(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("bond1_max_outbid_repegs", 3)),
                                    _b1_buried_s, _now_sll_p, is_outbid_now=_is_outbid_now, buried_since_mono=buried_since_mono,
                                )
                                from src.polymarket_research.riskless_protocol_v2_expansion import is_post_expiry_uma_frozen_lock
                                _liq_eq_sll = float(collat or 75.0) + sum(
                                    float(_p_lq.get("notional_usd", 0.0) or 0.0)
                                    for _p_lq in self.active_positions.values()
                                    if isinstance(_p_lq, dict)
                                    and not position_is_settlement_receivable(_p_lq)
                                    and not is_post_expiry_uma_frozen_lock(_p_lq, _now_sll_p)
                                )
                                _act_l, _rp_l, buried_since_mono, _msg_l = eval_sll_live_book_poll(
                                    bk_oc, bk_wc, candidate_box, posted_px, min_rb, max_rb, max_opp, _tk_wf,
                                    _enforce_b1_v53, _is_s2_mkr, _repost_n_in, _b1_q_cap, _eff_buried_s, exp_ts, buried_since_mono,
                                    collat_usd=_liq_eq_sll,
                                )
                                _live_ask_u_wc = sum(
                                    float(a["price"] if isinstance(a, dict) else a[0]) * float(a["size"] if isinstance(a, dict) else a[1])
                                    for a in ((bk_wc.get("asks") or []) if isinstance(bk_wc, dict) else [])
                                    if float(a["size"] if isinstance(a, dict) else a[1]) > 0.0
                                )
                                if _eff_cand_vol is not None or _cand_ask_d is not None:
                                    _last_has_active_asks = bool(_live_ask_u_wc >= 1.0)
                                if intent_id in self.pending_entry_intents:
                                    self.pending_entry_intents[intent_id]["fifo_rank1_verified"] = bool(
                                        candidate_box.get("_fifo_rank1_verified")
                                    )
                                    if _cand_ask_d is not None:
                                        self.pending_entry_intents[intent_id]["ask_depth_usd"] = round(_live_ask_u_wc, 2)
                                if _act_l == "ADVERSE":
                                    adverse_cancelled = True
                                    logger.warning(f"[BOND1 DISPUTE/COLLAPSE VETO] {box_id}: {_msg_l}; canceling {maker_oid} immediately.")
                                    break
                                if _act_l == "REPEG":
                                    outbid_repeg_px = _rp_l
                                    logger.info(f"[BOND1 OUTBID REPEG] {box_id}: {_msg_l}.")
                                    break
                                if _act_l == "BURIED":
                                    buried_cancelled = True
                                    logger.info(f"[BOND1 BURIED RELEASE] {box_id}: {_msg_l}; canceling {maker_oid}.")
                                    break
                                last_top_bid_px = extract_top_bid_from_book(bk_wc)
                                _, deadline, _ = compute_sll_maker_keep_and_renew(
                                    sleeve_src, uws_ok=bool(uws is not None and uws.is_healthy()), exp_ts=exp_ts,
                                    now_ts=time.time(), created_mono=t_sll_0, now_mono=time.monotonic(),
                                    deadline_mono=deadline, posted_px=posted_px, cur_best_bid=last_top_bid_px,
                                    buried_since_mono=buried_since_mono, rcfg=_rcfg_sll, first_post_elapsed_s=_fp_el,
                                    has_active_asks=_last_has_active_asks,
                                    matched_notional_usd=float((self.pending_entry_intents.get(intent_id) or {}).get("matched_notional_usd") or 0.0),
                                    volume_24h_usd=_eff_cand_vol,
                                )
                        _poll_iv_s = 1.5 if (_repost_n_in > 0 and last_fill_poll == t_sll_0 and (deadline - t_sll_0) >= 60.0) else 15.0
                        if hasattr(self.executor, "get_order_fill_summary") and (time.monotonic() - last_fill_poll) >= _poll_iv_s:
                            last_fill_poll = time.monotonic()
                            try:
                                poll_s = await asyncio.to_thread(self.executor.get_order_fill_summary, maker_oid, tok_a)
                            except Exception as _poll_exc:
                                logger.debug(f"[BOND1 FILL POLL TIMEOUT] {box_id}: {_poll_exc}; preserving resting Maker order {maker_oid}.")
                                poll_s = None
                            if isinstance(poll_s, dict):
                                _m_poll = float(poll_s.get("matched") or 0.0)
                                if update_sll_intent_partial_fill(self.pending_entry_intents, intent_id, posted_sh, posted_px, _m_poll, time.time()) and not self.dry_run:
                                    await asyncio.to_thread(self.save_state)
                                if _m_poll >= posted_sh - 0.01:
                                    ws_filled = True
                                    break
                                if poll_s.get("terminal"):
                                    if (deadline - time.monotonic()) > 5.0:
                                        candidate_box["_clob_early_terminal_detected"] = True
                                    break
                                _, deadline, _ = compute_sll_maker_keep_and_renew(
                                    sleeve_src, uws_ok=bool(uws is not None and uws.is_healthy()), exp_ts=exp_ts,
                                    now_ts=time.time(), created_mono=t_sll_0, now_mono=time.monotonic(),
                                    deadline_mono=deadline, posted_px=posted_px, cur_best_bid=last_top_bid_px,
                                    buried_since_mono=buried_since_mono, rcfg=_rcfg_sll, first_post_elapsed_s=_fp_el,
                                    has_active_asks=_last_has_active_asks,
                                    matched_notional_usd=float((self.pending_entry_intents.get(intent_id) or {}).get("matched_notional_usd") or 0.0),
                                    volume_24h_usd=_eff_cand_vol,
                                )
                except BaseException as _mon_exc:
                    logger.warning(f"[BOND1 MONITOR INTERRUPTED] {box_id}: {_mon_exc}; reconciling/canceling {maker_oid} before releasing intent.")

                cancel_res, summary, matched_sh, avg_px = await self._reconcile_maker_entry_fill(maker_oid, tok_a, ws_filled, posted_sh, posted_px, pre_bal_a)
                _fin_m_u = round(float((summary or {}).get("cash") or (max(0.0, matched_sh) * avg_px)), 4) if matched_sh >= 0.01 else 0.0
                if not self.dry_run and (matched_sh >= 0.01 or not bool((cancel_res or {}).get("is_canceled"))):
                    _prepost_evts[intent_id] = {
                        "trade_id": intent_id,
                        "market_id": mid_a,
                        "condition_id": cid_a,
                        "inflight_key": inflight_key,
                        "event_group_key": evt_k or (f"MKT:{mid_a}" if mid_a else ""),
                        "event_id": candidate_box.get("event_id"),
                        "title": candidate_box.get("title"),
                        "leg_a_label": candidate_box.get("leg_a_label"),
                        "asset": cand_asset,
                        "expiry_ts": exp_ts,
                        "notional_usd": _fin_m_u if _fin_m_u > 0.0 else round(posted_sh * posted_px, 4),
                        "live_maker_anchor_inflight": True,
                    }
                _saved_intent = release_sll_pending_intent(self.pending_entry_intents, intent_id, _fin_m_u)
                if not self.dry_run:
                    await asyncio.to_thread(self.save_state)
                c_out_s = str((cancel_res or {}).get("outcome") or "")
                is_canc_s = bool((cancel_res or {}).get("is_canceled"))
                if (
                    not is_canc_s
                    and c_out_s != "FILLED"
                    and matched_sh < 0.01
                    and "already canceled or matched" in str((cancel_res or {}).get("not_canceled_reason") or "").lower()
                ):
                    _cb_u, _src_u = await asyncio.to_thread(self._wallet_token_balance, tok_a)
                    if _src_u in (self.ONCHAIN_SOURCE, "CLOB_BALANCE_API") and (float(_cb_u or 0.0) - pre_bal_a) <= 1e-4:
                        is_canc_s = True
                if not is_canc_s and c_out_s != "FILLED" and (summary is None or not summary.get("terminal")) and matched_sh < 0.01:
                    lid_u = box_id if box_id not in self.active_positions else f"{box_id}_{int(time.time() * 1000) % 10000}"
                    not_unk = round(posted_sh * posted_px, 4)
                    st_lock = getattr(self, "_state_save_lock", None) or self._GLOBAL_STATE_SAVE_LOCK
                    with st_lock:
                        _pos_u = self._make_single_leg_lock_pos(
                            lid_u, "SINGLE_LEG_MAKER_LOCK", sleeve_src, cand_asset, "maker_lock_1leg",
                            mid_a, cid_a, tok_a, side_s, bool(nr_a), posted_sh, not_unk, 0.0, 0.0, 1.0,
                            "maker_post_only_0pct", exp_ts, time.time(), pre_bal_a, maker_oid, True, unk=True, sub_ts=now_int_ts,
                        )
                        _pos_u["dedupe_key"], _pos_u["pair_dedupe_key"], _pos_u["event_group_key"] = dedupe_k, pair_dedupe_k, evt_k
                        if candidate_box.get("event_id"):
                            _pos_u["event_id"] = str(candidate_box.get("event_id"))
                        if _is_inv_comp_mkr:
                            _pos_u["inventory_backed_completion"] = True
                            _pos_u["partner_held_token_id"] = _partner_tok_mkr
                            _pos_u["partner_avg_cost_ps"] = round(_partner_cost_ps_mkr, 4)
                        self.active_positions[lid_u] = _pos_u
                        _prepost_evts.pop(intent_id, None)
                        self._refresh_global_halt()
                        self.save_state()
                    return {"executed": False, "reason": "BOND1_CANCEL_OUTCOME_UNKNOWN"}
                if matched_sh < 0.01:
                    _prepost_evts.pop(intent_id, None)
                    if not self.dry_run and is_canc_s and pre_bal_a == 0.0:
                        (self.__dict__.get("_d1_dirty_token_until") or {}).pop(tok_a, None)
                    if outbid_repeg_px is not None and not self.dry_run and not getattr(self, "_shutdown_requested", False):
                        retry_cd.pop(dedupe_k, None)
                        _rp_px_target = float(outbid_repeg_px)
                        self._sll_repeg_count = int(getattr(self, "_sll_repeg_count", 0) or 0) + 1

                        async def _repost_outbid_bond1() -> None:
                            await asyncio.sleep(0.08)
                            _now_rp = time.time()
                            _ok_rp, _next_exp_rp = sll_repost_expiry_and_ok(
                                sleeve_src, exp_ts, _now_rp, (7.0 if _is_s2_mkr else 120.0),
                                first_post_ts=first_post_ts, uws_ok=bool(uws is not None and uws.is_healthy()), rcfg=_rcfg_sll,
                            )
                            if (
                                not _ok_rp
                                or getattr(self, "_shutdown_requested", False)
                                or self._is_d1_box_halted()
                                or is_d1_dedupe_blocked(self, dedupe_k, pair_dedupe_k, [mid_a], _now_rp)
                            ):
                                return
                            _rp_w = mkt_ws_s.get_book(tok_a, max_age_sec=0.85) if (mkt_ws_s is not None and "get_market_book" not in getattr(self.executor, "__dict__", {})) else None
                            _rp_o = mkt_ws_s.get_book(opp_a, max_age_sec=0.85) if (mkt_ws_s is not None and "get_market_book" not in getattr(self.executor, "__dict__", {})) else None
                            self._spawn_live_maker_anchor_box_task(
                                {
                                    **candidate_box,
                                    "expiry_ts": _next_exp_rp,
                                    "anchor_bid_px": _rp_px_target,
                                    "box_cost_net": _rp_px_target,
                                    **({"leg_a_max_price": max_rb} if (_is_inv_comp_mkr and not candidate_box.get("leg_a_max_price")) else {}),
                                    "ws_books": ({tok_a: _rp_w, opp_a: _rp_o} if (_rp_w and _rp_o) else None),
                                    "ws_books_ts": _now_rp,
                                    "ts_unix": _now_rp,
                                    "_bond1_repost_count": _repost_n_in + 1,
                                    "_bond1_first_post_ts": first_post_ts,
                                    "_repeg_zero_fill": bool(is_canc_s),
                                }
                            )

                        _rp_tasks = self.__dict__.setdefault("_bond1_repost_bg_tasks", set())
                        _rp_t = asyncio.create_task(_repost_outbid_bond1())
                        _rp_tasks.add(_rp_t)
                        _rp_t.add_done_callback(_rp_tasks.discard)
                        return {"executed": False, "reason": "BOND1_OUTBID_REPEGGED", "repeg_px": _rp_px_target}
                    _clob_early_term = bool(
                        candidate_box.pop("_clob_early_terminal_detected", False)
                        and not adverse_cancelled
                        and not buried_cancelled
                        and not preempt_ev.is_set()
                    )
                    was_preempted = bool(preempt_ev.is_set() and not adverse_cancelled and not buried_cancelled)
                    preempt_why = str((getattr(self, "_maker_anchor_preempt_reasons", None) or {}).pop(inflight_key, "") or "")
                    if buried_cancelled and not preempt_why:
                        preempt_why = f"outbid_buried_{_b1_buried_s:.0f}s"
                    elif _clob_early_term and not preempt_why:
                        preempt_why = "clob_postonly_early_terminal_requote"
                    out_stage = (
                        "BOND1_MAKER_ADVERSE_CANCELLED"
                        if adverse_cancelled
                        else (
                            "BOND1_MAKER_OUTBID_RELEASED"
                            if buried_cancelled
                            else (
                                "BOND1_MAKER_PREEMPTED"
                                if was_preempted
                                else ("BOND1_MAKER_POSTONLY_REQUOTE" if _clob_early_term else "BOND1_MAKER_EXPIRED_UNFILLED")
                            )
                        )
                    )
                    if _emit_shock_attempt is not None:
                        _emit_shock_attempt({
                            "dry_run": self.dry_run, "asset": cand_asset or "BOND1", "horizon": "box", "side": side_s,
                            "market_id": mid_a, "title": str(candidate_box.get("title") or box_id), "sleeve": sleeve_src,
                            "path_type": "MAKER_BOX", "target_px": posted_px, "notional_usd": round(posted_sh * posted_px, 2),
                            "http_ms": _b1_post_ms, "ttl_ms": round((time.monotonic() - t_sll_0) * 1000.0, 1),
                            "stage_outcome": out_stage,
                            "gate_detail": preempt_why,
                        })
                    _ok_pe0, _ = sll_repost_expiry_and_ok(
                        sleeve_src, exp_ts, time.time(), 150.0,
                        first_post_ts=first_post_ts, uws_ok=bool(uws is not None and uws.is_healthy()), rcfg=_rcfg_sll,
                    )
                    if (
                        (was_preempted or _clob_early_term)
                        and not self.dry_run
                        and not getattr(self, "_shutdown_requested", False)
                        and preempt_why != "SHUTDOWN"
                        and not preempt_why.startswith(("VELOCITY_UPGRADE:", "S2_TIER1_UPGRADE:", "GOVERNANCE_DISABLED"))
                        and _repost_n_in < 3
                        and _ok_pe0
                    ):
                        _repost_delay = (
                            float(_b1_gov.get("bond1_postonly_requote_delay_sec", 1.0) or 1.0)
                            if _clob_early_term
                            else float(_rcfg_sll.get("bond1_preempt_repost_delay_sec", 6.0) or 6.0)
                        )
                        retry_cd[dedupe_k] = time.time() + min(1.0, _repost_delay * 0.5)

                        async def _repost_preempted_bond1() -> None:
                            await asyncio.sleep(_repost_delay)
                            _now_pe = time.time()
                            _ok_pe1, _next_exp_pe = sll_repost_expiry_and_ok(
                                sleeve_src, exp_ts, _now_pe, 120.0,
                                first_post_ts=first_post_ts, uws_ok=bool(uws is not None and uws.is_healthy()), rcfg=_rcfg_sll,
                            )
                            if (
                                not _ok_pe1
                                or getattr(self, "_shutdown_requested", False)
                                or self._is_d1_box_halted()
                                or is_d1_dedupe_blocked(self, dedupe_k, pair_dedupe_k, [mid_a], _now_pe)
                            ):
                                return
                            _next_cand_pe = {
                                **candidate_box,
                                "expiry_ts": _next_exp_pe,
                                "ts_unix": _now_pe,
                                "_bond1_repost_count": _repost_n_in + 1,
                                "_bond1_first_post_ts": first_post_ts,
                            }
                            if _clob_early_term:
                                _next_cand_pe.pop("ws_books", None)
                                _next_cand_pe.pop("ws_books_ts", None)
                            self._spawn_live_maker_anchor_box_task(_next_cand_pe)

                        _rp_tasks = self.__dict__.setdefault("_bond1_repost_bg_tasks", set())
                        _rp_t = asyncio.create_task(_repost_preempted_bond1())
                        _rp_tasks.add(_rp_t)
                        _rp_t.add_done_callback(_rp_tasks.discard)
                    else:
                        _now_cd = time.time()
                        retry_cd[dedupe_k] = _now_cd + record_sll_exit_cooldown(self, dedupe_k, buried_cancelled, adverse_cancelled, _is_s2_mkr, _repost_n_in, _now_cd)
                    return {"executed": False, "reason": out_stage}

            f_sh = round(matched_sh, 4)
            not_u = round(float((summary or {}).get("cash") or (f_sh * avg_px)), 4)
            if _emit_shock_attempt is not None:
                _emit_shock_attempt({
                    "dry_run": self.dry_run, "asset": cand_asset or "BOND1", "horizon": "box", "side": side_s,
                    "market_id": mid_a, "title": str(candidate_box.get("title") or box_id), "sleeve": sleeve_src,
                    "path_type": "MAKER_BOX", "target_px": posted_px, "fill_px": avg_px, "notional_usd": not_u,
                    "http_ms": _b1_post_ms, "stage_outcome": "FILLED_BOX",
                })
            fee_u = round(float((summary or {}).get("fee") or 0.0), 4)
            eff_px = round((not_u + fee_u) / max(f_sh, 0.01), 5)
            h_mat = bool(_is_inv_comp_mkr or candidate_box.get("hold_to_maturity", True) or avg_px >= 0.982)
            _mkr_fills = list((summary or {}).get("fills") or [])
            if not _mkr_fills and not self.dry_run and hasattr(self.executor, "get_account_fills"):
                try:
                    _mkr_fills = list(
                        (await asyncio.to_thread(self.executor.get_account_fills, tok_a, max(0.0, now_int_ts - 60.0), "BUY", maker_oid))
                        or []
                    )
                except Exception:
                    _mkr_fills = []
            _mkr_tids = list(
                dict.fromkeys(
                    [str(x) for x in ((summary or {}).get("trade_ids") or (post_res or {}).get("tradeIDs") or []) if x]
                    + [str(f.get("trade_id") or f.get("id")) for f in _mkr_fills if isinstance(f, dict) and (f.get("trade_id") or f.get("id"))]
                )
            )
            _mkr_txs = list(
                dict.fromkeys(
                    [str(x) for x in ((summary or {}).get("transactions_hashes") or (post_res or {}).get("transactionsHashes") or []) if x]
                    + [str(f.get("transaction_hash")) for f in _mkr_fills if isinstance(f, dict) and f.get("transaction_hash")]
                )
            )
            now_fill_ts = time.time()
            lid = box_id if box_id not in self.active_positions else f"{box_id}_{int(now_fill_ts * 1000) % 10000}"
            st_lock = getattr(self, "_state_save_lock", None) or self._GLOBAL_STATE_SAVE_LOCK
            with st_lock:
                for dk_done in (dedupe_k, pair_dedupe_k):
                    if dk_done:
                        retry_cd.pop(dk_done, None)
                        self._record_seen_d1_box_key(dk_done)
                _pos_ok = self._make_single_leg_lock_pos(
                    lid, "SINGLE_LEG_MAKER_LOCK", sleeve_src, cand_asset, "maker_lock_1leg",
                    mid_a, cid_a, tok_a, side_s, bool(nr_a), f_sh, not_u, fee_u, 0.0, 1.0,
                    "maker_post_only_0pct", exp_ts, now_fill_ts, pre_bal_a, maker_oid, h_mat, unk=False,
                )
                _pos_ok["trade_ids"], _pos_ok["transactions_hashes"] = _mkr_tids, _mkr_txs
                _pos_ok["dedupe_key"], _pos_ok["pair_dedupe_key"], _pos_ok["event_group_key"] = dedupe_k, pair_dedupe_k, evt_k
                if candidate_box.get("event_id"):
                    _pos_ok["event_id"] = str(candidate_box.get("event_id"))
                if _is_inv_comp_mkr:
                    _pos_ok["inventory_backed_completion"] = True
                    _pos_ok["partner_held_token_id"] = _partner_tok_mkr
                    _pos_ok["partner_avg_cost_ps"] = round(_partner_cost_ps_mkr, 4)
                self._record_ft_candidate_funnel(
                    candidate_box, stage="MAKER_FILLED", executed=True, maker_filled=True, is_maker=True
                )
                (self.__dict__.get("_clinched_ws_watchlist") or {}).pop(tok_a, None)
                self.active_positions[lid] = _pos_ok
                _prepost_evts.pop(intent_id, None)
                debit_sll_collateral_after_fill(self, _saved_intent, not_u + fee_u, time.time())
                self.executor.invalidate_collateral_cache()
                self._pending_collateral_refresh = True
                self.save_state()
                logger.info(
                    f"✓ [SINGLE-LEG MAKER LOCK FILLED] {lid} ({sleeve_src}) | {f_sh:.2f} sh @ ${eff_px:.4f} "
                    f"(0% Maker fee, hold_to_maturity={h_mat})"
                )
            if not self.dry_run and _stage_b_emit_funnel is not None:
                try:
                    if _STAGE_B_DECAY_TRACKER is not None:
                        _STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(box_id)
                        if dedupe_k:
                            _STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(dedupe_k)
                    _stage_b_emit_funnel(
                        "COMPLETE_BASKET_LOCKED", sleeve=sleeve_src, candidate_key=box_id, box_type="SINGLE_LEG_MAKER_LOCK",
                        asset=str(cand_asset or ""), net_edge_bps=round(max(0.0, 1.0 - eff_px) * 10000.0, 2),
                        est_profit_usd=round(max(0.0, 1.0 - eff_px) * f_sh, 4), notional_usd=not_u,
                    )
                except Exception:
                    pass
            if not self.dry_run and h_mat:
                spawn_fast_htm_maker_fill_reconcile(self, lid)
            return {"executed": True, "result": summary or post_res, "leg_trade_ids": [] if h_mat else [lid]}
        finally:
            (self.__dict__.get("_sll_ws_book_events") or {}).pop(intent_id, None)
            _prepost_res.pop(intent_id, None)
            _prepost_mkts.pop(intent_id, None)
            _prepost_evts.pop(intent_id, None)
            (self.__dict__.get("_prepost_partner_pledged_shares") or {}).pop(intent_id, None)
            release_sll_pending_intent(self.pending_entry_intents, intent_id, 0.0)
            inflight_mkr.discard(inflight_key)
            inflight_mkr_types.discard(mkr_type_k)
            inflight_s2_mkr.discard(inflight_key)
            preempt_events.pop(inflight_key, None)

    def _notify_sll_ws_book_change(self, _tok: str, loop_ref: Any = None) -> int:
        _sll_ev_map = getattr(self, "_sll_ws_book_events", None)
        if not _sll_ev_map:
            return 0
        lp = loop_ref or getattr(self, "_main_loop", None)
        woke = 0
        for _tk_w, _op_w, _ev_s in list(_sll_ev_map.values()):
            if _tok in (_tk_w, _op_w) and not _ev_s.is_set():
                if lp is not None:
                    lp.call_soon_threadsafe(_ev_s.set)
                else:
                    _ev_s.set()
                woke += 1
        return woke

    def _spawn_live_maker_anchor_box_task(self, candidate_box: Dict[str, Any]) -> bool:
        from src.polymarket_research.riskless_protocol_v2_expansion import is_s2_maker_bg_task_capped, register_s2_maker_bg_task

        tasks = self.__dict__.setdefault("_maker_anchor_bg_tasks", set())
        by_type = self.__dict__.setdefault("_maker_anchor_bg_tasks_by_type", {})
        b_type = str(candidate_box.get("box_type") or "DOMINANCE_MAKER_ANCHOR").strip().upper()
        sl_t = str(candidate_box.get("sleeve_source") or "").strip()
        _is_s2_t = sl_t in {"S2_EXACT_TWAP_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR"}
        _unlim_t = self._is_unlimited_slots_active()
        is_sll_mkr = b_type == "SINGLE_LEG_MAKER_LOCK"
        if is_sll_mkr:
            if _is_s2_t and is_s2_maker_bg_task_capped(self):
                return False
            b_key = f"SINGLE_LEG_MAKER_LOCK:{candidate_box.get('dedupe_key') or candidate_box.get('leg_a_market_id') or b_type}"
            sll_running = sum(1 for k, tk in by_type.items() if str(k).startswith("SINGLE_LEG_MAKER_LOCK:") and not tk.done())
            _sll_lim = (10 if _is_s2_t else 8) if (_unlim_t or self._is_v5_unleashed_active()) else (4 if _is_s2_t else 2)
            if sll_running >= _sll_lim:
                return False
        else:
            b_key = f"{b_type}:{candidate_box.get('dedupe_key') or candidate_box.get('asset') or b_type}" if _unlim_t else b_type
            box2_running = sum(1 for k, tk in by_type.items() if not str(k).startswith("SINGLE_LEG_MAKER_LOCK:") and not tk.done())
            if box2_running >= (8 if _unlim_t else 2):
                return False
        cur_t = by_type.get(b_key)
        if cur_t is not None and not cur_t.done():
            return False
        if len(tasks) >= ((12 if _is_s2_t else 10) if (_unlim_t or self._is_v5_unleashed_active()) else (6 if _is_s2_t else 4)):
            return False
        coro = (
            self.maybe_execute_graduated_single_leg_maker_lock(candidate_box)
            if is_sll_mkr
            else self.maybe_execute_graduated_maker_anchor_box(candidate_box)
        )
        t = asyncio.create_task(coro)
        tasks.add(t)
        by_type[b_key] = t
        if is_sll_mkr and _is_s2_t:
            register_s2_maker_bg_task(self, t)

        def _cleanup(done_t: Any) -> None:
            tasks.discard(done_t)
            if by_type.get(b_key) is done_t:
                by_type.pop(b_key, None)
            try:
                if not done_t.cancelled() and done_t.exception() is None:
                    _r = done_t.result()
                    if isinstance(_r, dict) and not _r.get("executed"):
                        logger.info(f"[SLL MAKER SKIP] {b_key} ({sl_t or b_type}): {_r.get('reason')}")
            except Exception:
                pass

        t.add_done_callback(_cleanup)
        return True

    def _desired_market_ws_tokens(self, now_ts: Optional[float] = None) -> List[str]:
        from src.polymarket_research.riskless_protocol_v2_expansion import desired_market_ws_tokens_impl
        return desired_market_ws_tokens_impl(self, now_ts=now_ts)

    def register_clinched_ws_watch_cand(self, cand: Dict[str, Any], now_ts: Optional[float] = None) -> bool:
        from src.polymarket_research.riskless_protocol_v2_expansion import register_clinched_ws_watch_cand_impl
        return register_clinched_ws_watch_cand_impl(self, cand, now_ts=now_ts)

    def evaluate_clinched_ws_book_snipe(
        self, tok_id: str, bk_win: Optional[Dict[str, Any]] = None, now_ts: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        from src.polymarket_research.riskless_protocol_v2_expansion import evaluate_clinched_ws_book_snipe_impl
        return evaluate_clinched_ws_book_snipe_impl(self, tok_id, bk_win=bk_win, now_ts=now_ts)

    async def _poll_d1_live_box_candidates(self, now_ts: float) -> int:
        loop = asyncio.get_running_loop()
        if getattr(self, "_d1_poll_lock_loop", None) is not loop or getattr(self, "_d1_poll_async_lock", None) is None:
            self._d1_poll_async_lock = asyncio.Lock()
            self._d1_poll_lock_loop = loop
        async with self._d1_poll_async_lock:
            return await self._poll_d1_live_box_candidates_unlocked(now_ts, loop)

    async def _poll_d1_live_box_candidates_unlocked(self, now_ts: float, loop: Any) -> int:
        raw_lines: List[str] = []
        fast_q = getattr(self, "_fast_d1_cand_lines", None)
        if fast_q:
            while fast_q:
                raw_lines.append(fast_q.popleft())
        if not raw_lines or (now_ts - getattr(self, "_last_d1_disk_poll", 0.0)) >= 0.50:
            self._last_d1_disk_poll = now_ts
            cand_file = DATA_DIR / "d1_live_box_candidates.jsonl"
            if not getattr(self, "_d1_cand_initialized", False):
                self._d1_cand_initialized = True
                # Always tail from EOF at startup: the file is append-only and large (embedded ws_books); fresh
                # candidates arrive via IPC, and replaying history would only stall the loop on stale rejects.
                self._last_d1_cand_offset = cand_file.stat().st_size if cand_file.exists() else 0
            if cand_file.exists():
                sz = cand_file.stat().st_size
                if sz < self._last_d1_cand_offset:
                    self._last_d1_cand_offset = 0
                if sz > self._last_d1_cand_offset:
                    with open(cand_file, "rb") as fp:
                        fp.seek(self._last_d1_cand_offset)
                        chunk = fp.read()
                    end_nl = chunk.rfind(b"\n") + 1
                    if end_nl:
                        self._last_d1_cand_offset += end_nl
                        raw_lines.extend(chunk[:end_nl].decode("utf-8", errors="ignore").splitlines())
        if not raw_lines:
            return 0
        seen_emits = self.__dict__.setdefault("_seen_d1_emit_ids", {})
        retry_cd_poll = self.__dict__.setdefault("_d1_retry_cooldown_until", {})
        from src.polymarket_research.riskless_protocol_v2_expansion import is_d1_dedupe_blocked
        executed = 0
        loop = asyncio.get_running_loop()
        self._main_loop = loop
        taker_cands: List[Tuple[str, Dict[str, Any]]] = []
        mkr_cands: List[Tuple[str, Dict[str, Any]]] = []
        for raw_ln in raw_lines:
            if not raw_ln.strip():
                continue
            try:
                cand = _json_loads(raw_ln)
                emit_id = f"{cand.get('dedupe_key') or cand.get('box_id')}:{cand.get('ts_unix')}"
                if emit_id in seen_emits:
                    continue
                b_type_c = str(cand.get("box_type") or "").strip().upper()
                if b_type_c == "CLINCH_WATCHLIST_REG":
                    seen_emits[emit_id] = None
                    self._record_ft_candidate_funnel(cand, stage="CLINCH_WATCHLIST")
                    self.register_clinched_ws_watch_cand(cand, now_ts)
                    continue
                self._record_ft_candidate_funnel(cand, stage="RECEIVED")
                if not self.dry_run and _stage_b_reg_decay_watch is not None:
                    try:
                        _stage_b_reg_decay_watch(cand, emit_funnel=False, tracker=_STAGE_B_DECAY_TRACKER)
                    except Exception:
                        pass
                if b_type_c == "SINGLE_LEG_MAKER_LOCK" and float(cand.get("p_model") or 0.0) >= 0.998:
                    self.register_clinched_ws_watch_cand(cand, now_ts)
                if b_type_c in {"DOMINANCE_MAKER_ANCHOR", "ZERO_FEE_MAKER_ANCHOR", "SINGLE_LEG_MAKER_LOCK"}:
                    mkr_cands.append((emit_id, cand))
                else:
                    taker_cands.append((emit_id, cand))
            except Exception as exc:
                logger.error(f"[D1 LIVE BRIDGE] Error evaluating candidate: {exc}", exc_info=True)
        if not self.dry_run and getattr(self, "_pos_market_ws", None) is not None and (taker_cands or mkr_cands):
            try:
                self._pos_market_ws.set_desired_tokens(self._desired_market_ws_tokens(now_ts))
            except Exception:
                pass

        from src.polymarket_research.riskless_protocol_v2_expansion import score_live_candidate_velocity_ev

        def _cand_vel_ev(c: Dict[str, Any], is_maker: bool) -> float:
            return score_live_candidate_velocity_ev(c, is_maker, now_ts, compute_capital_velocity_ev)

        if taker_cands:
            taker_cands.sort(key=lambda item: _cand_vel_ev(item[1], False), reverse=True)
            max_batch_boxes = int(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("max_concurrent_riskless_boxes", 10)) if self._is_v5_unleashed_active() else max(1, int(RISK_CONFIG.get("max_concurrent_d1_boxes", 4)))
            for emit_id, cand in taker_cands:
                try:
                    seen_emits[emit_id] = None
                    while len(seen_emits) > 4096:
                        seen_emits.pop(next(iter(seen_emits)), None)
                    out = await loop.run_in_executor(_get_hot_io_pool(), self.maybe_execute_graduated_d1_box, cand)
                    if out.get("executed"):
                        self._record_ft_candidate_funnel(cand, stage="TAKER_EXECUTED", executed=True)
                        if not self.dry_run:
                            for tid in out.get("leg_trade_ids") or []:
                                if not (self.active_positions.get(tid) or {}).get("hold_to_maturity_lock"):
                                    self._spawn_fast_confirm(tid)
                        executed += 1
                        if executed >= max_batch_boxes:
                            break
                    else:
                        _skip_r = str(out.get("reason") or "UNKNOWN")
                        self._record_ft_candidate_funnel(cand, stage="TAKER_REJECTED", reason=_skip_r)
                        if _skip_r not in {"DUPLICATE_BOX_KEY", "RETRY_COOLDOWN_10S", "BOX_EXECUTION_INFLIGHT"}:
                            logger.info(
                                f"[D1 LIVE BOX SKIP] {cand.get('box_id') or cand.get('dedupe_key')} "
                                f"({cand.get('sleeve_source') or cand.get('box_type')} {cand.get('asset')}): {_skip_r}"
                            )
                except Exception as exc:
                    logger.error(f"[D1 LIVE BRIDGE] Error evaluating candidate: {exc}", exc_info=True)

        if mkr_cands and os.environ.get("PM_DISABLE_LIVE_MAKER_ANCHOR_BOX", "0") != "1":
            _rcfg_mkr_p = getattr(self, "risk_config", None) or RISK_CONFIG
            _gov_rb_p = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}) if self._is_v5_live_strict() else {}
            _allow_2leg_mkr = bool(
                _rcfg_mkr_p.get("enable_live_maker_anchor_boxes", False)
                and _gov_rb_p.get("enable_two_leg_maker_anchor_boxes", True)
            )
            _allow_1leg_bond1 = bool(
                _rcfg_mkr_p.get("enable_single_leg_maker_bond1", True)
                and _gov_rb_p.get("enable_single_leg_maker_bond1", True)
            )
            _allow_rebate_mg = bool(_gov_rb_p.get("enable_d1_rebate_maker_canary", False))
            from src.polymarket_research.riskless_protocol_v2_expansion import (
                check_per_event_concentration_cap,
                extract_canonical_event_keys,
            )
            mkr_cands.sort(key=lambda item: _cand_vel_ev(item[1], True), reverse=True)
            _batch_evt_slot_counts: Dict[str, int] = {}
            _max_evt_slots_b = int((_gov_rb_p.get("max_concurrent_intents_per_event") if isinstance(_gov_rb_p, dict) else None) or 1)
            for emit_id, cand in mkr_cands:
                _is_sll_c = str(cand.get("box_type") or "").strip().upper() == "SINGLE_LEG_MAKER_LOCK"
                _is_rmg_c = str(cand.get("sleeve_source") or "").strip() == "D1_REBATE_MACHINE_GUN"
                if not (_allow_1leg_bond1 if _is_sll_c else (_allow_rebate_mg if _is_rmg_c else _allow_2leg_mkr)):
                    self._record_ft_candidate_funnel(cand, stage="MAKER_REJECTED", reason="MAKER_LANE_DISABLED", is_maker=True)
                    seen_emits[emit_id] = None
                    continue
                dk_m = str(cand.get("dedupe_key") or "")
                pdk_m = str(cand.get("pair_dedupe_key") or "")
                mids_m = [str(cand.get("leg_a_market_id") or ""), str(cand.get("leg_b_market_id") or "")]
                if (dk_m and float(retry_cd_poll.get(dk_m, 0.0) or 0.0) > now_ts) or is_d1_dedupe_blocked(self, dk_m, pdk_m, mids_m, now_ts):
                    self._record_ft_candidate_funnel(cand, stage="MAKER_REJECTED", reason="ALREADY_SEEN_OR_COOLDOWN", is_maker=True)
                    seen_emits[emit_id] = None
                    continue
                if _is_sll_c and bool(_gov_rb_p.get("enable_event_slot_diversification", True)):
                    _c_ev_keys = extract_canonical_event_keys(cand, market_ids=[m for m in mids_m if m])
                    if _c_ev_keys:
                        _ok_ev_b, _ev_r_b, _, _ = check_per_event_concentration_cap(self, cand, market_ids=[m for m in mids_m if m], now_ts=now_ts)
                        if not _ok_ev_b or any(_batch_evt_slot_counts.get(ek, 0) >= _max_evt_slots_b for ek in _c_ev_keys):
                            self._record_ft_candidate_funnel(cand, stage="MAKER_REJECTED", reason=str(_ev_r_b or "EVENT_SLOT_CAPPED"), is_maker=True)
                            seen_emits[emit_id] = None
                            continue
                else:
                    _c_ev_keys = set()
                if self._spawn_live_maker_anchor_box_task(cand):
                    self._record_ft_candidate_funnel(cand, stage="MAKER_SPAWNED", is_maker=True)
                    for ek in _c_ev_keys:
                        _batch_evt_slot_counts[ek] = _batch_evt_slot_counts.get(ek, 0) + 1
                    seen_emits[emit_id] = None
                    while len(seen_emits) > 4096:
                        seen_emits.pop(next(iter(seen_emits)), None)
        if not self.dry_run and (taker_cands or mkr_cands) and executed == 0:
            _ft_p_iv = float(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("ft_funnel_persist_interval_sec", 5.0) or 5.0)
            if (now_ts - float(self.__dict__.get("_last_ft_funnel_save_ts") or 0.0)) >= _ft_p_iv:
                self._last_ft_funnel_save_ts = now_ts
                await asyncio.to_thread(self.save_state)
        return executed

    def _snapshot_ft_live_funnel(
        self,
        pend_map: Optional[Dict[str, Any]] = None,
        *,
        now_utc_iso: Optional[str] = None,
    ) -> Dict[str, Any]:
        raw = self.__dict__.setdefault("_ft_live_funnel", {})
        pm = pend_map if isinstance(pend_map, dict) else (getattr(self, "pending_entry_intents", None) or {})
        resting_mkr = sum(1 for v in pm.values() if isinstance(v, dict) and v.get("live_maker_anchor_inflight"))
        return {
            "updated_at_utc": now_utc_iso or datetime.now(timezone.utc).isoformat(),
            "candidates_received": int(raw.get("candidates_received", 0) or 0),
            "ft_bridge_received": int(raw.get("ft_bridge_received", 0) or 0),
            "clinch_watchlist_registered": int(raw.get("clinch_watchlist_registered", 0) or 0),
            "taker_evaluated": int(raw.get("taker_evaluated", 0) or 0),
            "taker_executed": int(raw.get("taker_executed", 0) or 0),
            "maker_spawned": int(raw.get("maker_spawned", 0) or 0),
            "maker_posted": int(raw.get("maker_posted", 0) or 0),
            "maker_filled": int(raw.get("maker_filled", 0) or 0),
            "rejected_total": int(raw.get("rejected_total", 0) or 0),
            "resting_maker_slots": int(resting_mkr),
            "by_sleeve": dict(raw.get("by_sleeve") or {}),
            "reject_reasons": dict(raw.get("reject_reasons") or {}),
            "recent_candidates": list(raw.get("recent_candidates") or [])[-25:],
        }

    def _record_ft_candidate_funnel(
        self,
        cand: Any,
        *,
        stage: str,
        reason: str = "",
        executed: bool = False,
        maker_posted: bool = False,
        maker_filled: bool = False,
        is_maker: bool = False,
    ) -> None:
        if not isinstance(cand, dict):
            return
        st = self.__dict__.setdefault("_ft_live_funnel", {})
        sl = str(cand.get("sleeve_source") or cand.get("sleeve") or cand.get("box_type") or "UNKNOWN").strip() or "UNKNOWN"
        is_ft = bool(cand.get("full_throttle_bridge") or cand.get("rule_verified") is True)
        now_f = time.time()
        by_sl = st.setdefault("by_sleeve", {})
        if sl not in by_sl and len(by_sl) >= 64:
            by_sl.pop(next(iter(by_sl)), None)
        rec = by_sl.setdefault(
            sl,
            {
                "received": 0,
                "ft_bridge": 0,
                "taker_evaluated": 0,
                "taker_executed": 0,
                "maker_spawned": 0,
                "maker_posted": 0,
                "maker_filled": 0,
                "rejected": 0,
                "last_reason": "",
                "last_ts": 0.0,
            },
        )
        rec["last_ts"] = round(now_f, 3)
        if stage == "CLINCH_WATCHLIST":
            st["clinch_watchlist_registered"] = int(st.get("clinch_watchlist_registered", 0) or 0) + 1
            return
        if stage == "RECEIVED":
            st["candidates_received"] = int(st.get("candidates_received", 0) or 0) + 1
            rec["received"] = int(rec.get("received", 0) or 0) + 1
            if is_ft:
                st["ft_bridge_received"] = int(st.get("ft_bridge_received", 0) or 0) + 1
                rec["ft_bridge"] = int(rec.get("ft_bridge", 0) or 0) + 1
            return
        if stage in {"TAKER_EXECUTED", "TAKER_REJECTED"}:
            st["taker_evaluated"] = int(st.get("taker_evaluated", 0) or 0) + 1
            rec["taker_evaluated"] = int(rec.get("taker_evaluated", 0) or 0) + 1
        if executed and not is_maker:
            st["taker_executed"] = int(st.get("taker_executed", 0) or 0) + 1
            rec["taker_executed"] = int(rec.get("taker_executed", 0) or 0) + 1
            rec["last_reason"] = "EXECUTED"
        if stage == "MAKER_SPAWNED":
            st["maker_spawned"] = int(st.get("maker_spawned", 0) or 0) + 1
            rec["maker_spawned"] = int(rec.get("maker_spawned", 0) or 0) + 1
        if maker_posted:
            st["maker_posted"] = int(st.get("maker_posted", 0) or 0) + 1
            rec["maker_posted"] = int(rec.get("maker_posted", 0) or 0) + 1
            rec["last_reason"] = "MAKER_POSTED"
        if maker_filled:
            st["maker_filled"] = int(st.get("maker_filled", 0) or 0) + 1
            rec["maker_filled"] = int(rec.get("maker_filled", 0) or 0) + 1
            rec["last_reason"] = "MAKER_FILLED"
        if reason:
            rk = str(reason).split(":", 1)[0][:64]
            st["rejected_total"] = int(st.get("rejected_total", 0) or 0) + 1
            rec["rejected"] = int(rec.get("rejected", 0) or 0) + 1
            rec["last_reason"] = str(reason)[:96]
            rr = st.setdefault("reject_reasons", {})
            if rk not in rr and len(rr) >= 64:
                rr.pop(next(iter(rr)), None)
            rr[rk] = int(rr.get(rk, 0) or 0) + 1
        rc = st.setdefault("recent_candidates", [])
        rc.append(
            {
                "ts_unix": round(now_f, 3),
                "box_id": str(cand.get("box_id") or cand.get("dedupe_key") or "")[:72],
                "sleeve": sl[:64],
                "box_type": str(cand.get("box_type") or "")[:32],
                "asset": str(cand.get("asset") or "")[:16],
                "market_id": str(cand.get("leg_a_market_id") or cand.get("market_id") or "")[:24],
                "ft_bridge": is_ft,
                "stage": stage,
                "reason": str(reason or ("EXECUTED" if (executed or maker_filled) else stage))[:96],
            }
        )
        if len(rc) > 25:
            del rc[:-25]

    def _is_phase3a_maker_rescue_live_active(self) -> bool:
        explicit_flag = self.__dict__.get("enable_live_phase3a_maker_fallback")
        if explicit_flag is False or os.environ.get("PM_DISABLE_LIVE_PHASE3A_MAKER", "0") == "1":
            return False
        real_live = (
            not self.dry_run and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
            and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
            and not any(k in getattr(self.executor, "__dict__", {}) for k in ("execute_snipe_order_async", "execute_snipe_order"))
        )
        return bool(explicit_flag is True or (real_live and bool(RISK_CONFIG.get("enable_live_phase3a_maker_fallback", True))))

    def _calc_priority_score(self, s_item: Dict[str, Any]) -> float:
        _a_s = str(s_item.get("asset") or "").upper()
        if _a_s and _a_s not in self.get_graduated_allowed_assets():
            return 0.0
        s_dir = s_item.get("shock_direction")
        tgt = "UP" if s_dir == "BUY" else "DOWN"
        feats = s_item.get("pre_shock_features_t0", {})
        side_data = feats.get(tgt, {}) if isinstance(feats, dict) else {}
        dist_raw = float(s_item.get("candle_distance_pct", 0.0) or 0.0)
        if (tgt == "UP" and dist_raw < 0.04) or (tgt == "DOWN" and dist_raw > -0.04):
            return 0.0
        dist = abs(dist_raw)
        z_sc = abs(float(s_item.get("z_val", s_item.get("z_score", s_item.get("expected_prob_shift", dist * 0.5)))))
        _v5_strict = self._is_v5_live_strict()
        _raw_ask_est = (
            (
                side_data.get("vwap_$20")
                or side_data.get("effective_price_$20")
                or side_data.get("vwap_$25")
                or side_data.get("effective_price_$25")
                or side_data.get("best_ask")
                or side_data.get("vwap_$50")
                or side_data.get("effective_price_$50")
            )
            if _v5_strict
            else (
                side_data.get("vwap_$50")
                or side_data.get("effective_price_$50")
                or side_data.get("vwap_$25")
                or side_data.get("effective_price_$25")
                or side_data.get("best_ask")
            )
        )
        ask_est = float(_raw_ask_est) if _raw_ask_est is not None else (0.60 if _v5_strict else 0.50)
        _t_low = str(s_item.get("title", "")).lower()
        _hz_low = str(s_item.get("horizon") or s_item.get("candle_interval") or s_item.get("timeframe") or "").lower()
        _is_15m = ("pm-" in _t_low or "am-" in _t_low or "15" in _hz_low)
        _tte_s = float(s_item.get("seconds_to_expiry", 3600.0) or 3600.0)
        _is_bnd = (
            s_item.get("shock_source") == "BOUNDARY_LOCK"
            or s_item.get("regime_override") == "REGIME_D_BOUNDARY_LOCK"
            or (12.0 <= _tte_s <= 90.0 and dist >= 0.08)
        )
        _is_slv3 = s_item.get("sleeve") == "SLEEVE_3_STRIKE_CONVERGENCE" or s_item.get("shock_source") == "EXP316_TRACK_A_CONVERGENCE"
        _v5_d = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {}) if _v5_strict else {}
        if _is_bnd:
            _ceil = 0.94
        elif _is_slv3:
            _ceil = 0.89
        elif _v5_strict:
            _ceil = (
                max(float(_v5_d.get("max_taker_price_15m", 0.82)), float(_v5_d.get("max_maker_price_15m", 0.82)))
                if _is_15m
                else max(float(_v5_d.get("max_taker_price_1h", 0.82)), float(_v5_d.get("max_maker_price_1h", 0.82)))
            )
        else:
            _ceil = min(self.max_price_ceiling, 0.85) if _is_15m else self.max_price_ceiling
        _eff_floor = float(_v5_d.get("min_entry_price", 0.52)) if _v5_strict else self.min_price_floor
        if ask_est < _eff_floor:
            return 0.0
        if ask_est > _ceil:
            _l1_ask = float(side_data.get("best_ask") or ask_est)
            if not _is_bnd and not _is_slv3 and _tte_s >= 85.0 and dist >= 0.06 and min(ask_est, _l1_ask) <= round(_ceil + 0.03, 4) and self._is_phase3a_maker_rescue_live_active():
                return 0.5 * (z_sc / max(ask_est, 0.01))
            return 0.0
        return z_sc / max(ask_est, 0.01)

    async def evaluate_shock_and_execute(self, shock: Dict[str, Any], *, _cold_unqualified: bool = False):
        """
        Thin tracing wrapper: opens a per-trigger LatencyTrace (published to the executor through a
        ContextVar) and always resets it, so a stale trace can never leak into an unrelated order.
        Kaizen #2: Holds _HOT_DISPATCH_ACTIVE from trigger_consumed through primary order dispatch so
        background ladder-prewarm threads yield the GIL during hot qualification + zero-hop POST /order.
        """
        self._main_loop = asyncio.get_running_loop()
        _pre_logs: List[str] = []
        _hot_held = False
        _cold_set = self.__dict__.get("_cold_shock_objs")
        if _cold_set and id(shock) in _cold_set:
            _cold_set.discard(id(shock))
            _cold_unqualified = True
        _shk_asset = str(shock.get("asset") or "").upper()
        _tgt_hot = "UP" if shock.get("shock_direction") == "BUY" else "DOWN"
        _sd_hot = ((shock.get("pre_shock_features_t0") or {}).get(_tgt_hot) or {}) if isinstance(shock.get("pre_shock_features_t0"), dict) else {}
        _pinned_dead = bool(float(_sd_hot.get("best_ask") or 0.0) >= 0.985 and float(_sd_hot.get("best_bid") or 0.0) >= 0.95)
        _allow_hot = (not _cold_unqualified) and (not _pinned_dead) and ((not _shk_asset) or (_shk_asset in self.get_graduated_allowed_assets()) or (_shk_asset in ("SOL", "ETH")))
        if not getattr(self, "dry_run", False) and _allow_hot:
            _HOT_DISPATCH_ACTIVE.enter()
            _hot_held = True

        def _flush_pre_logs() -> None:
            if _pre_logs:
                _batch = _pre_logs[:]
                _pre_logs.clear()
                for _m in _batch:
                    logger.info(_m)

        def _release_pre_hot() -> None:
            nonlocal _hot_held
            if _hot_held:
                _hot_held = False
                _HOT_DISPATCH_ACTIVE.leave()

        _hot_tok = _PRE_HOT_CTX.set((_pre_logs, _flush_pre_logs, _release_pre_hot))
        token = None
        trace = None
        try:
            if _LatencyTrace is not None and _CURRENT_TRACE is not None:
                try:
                    trace = _LatencyTrace(
                        shock_id=str(shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"),
                        market_id=str(shock.get("market_id") or ""),
                        asset=str(shock.get("asset") or ""),
                        sleeve=str(shock.get("sleeve") or shock.get("regime") or shock.get("strategy") or ""),
                        src_t0_unix=shock.get("t0_unix"),
                        dry_run=bool(getattr(self, "dry_run", False)),
                    )
                    trace.stamp("trigger_consumed")
                    try:
                        # Cross-process wall-clock lag (recorder -> harvester). Valid only with chrony-synced host clock.
                        trace.set(trigger_to_consume_wall_ms=round((time.time() - float(shock.get("t0_unix"))) * 1000.0, 3))
                    except (TypeError, ValueError):
                        pass
                    token = _CURRENT_TRACE.set(trace)
                except Exception:
                    token = None
            return await self._evaluate_shock_and_execute_impl(shock)
        finally:
            _release_pre_hot()
            _flush_pre_logs()
            try:
                _PRE_HOT_CTX.reset(_hot_tok)
            except Exception:
                pass
            if _emit_shock_attempt_trace is not None and trace is not None:
                try:
                    _emit_shock_attempt_trace(trace, shock)
                except Exception:
                    pass
            if token is not None:
                try:
                    _CURRENT_TRACE.reset(token)
                except Exception:
                    pass

    _evaluate_shock_and_execute_impl = _bind_hv_method(_hv__evaluate_shock_and_execute_impl, '_evaluate_shock_and_execute_impl')

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
            "trade_id": trade_id, "entry_trade_id": intent.get("entry_trade_id") or trade_id,
            "order_id": intent.get("entry_order_id") or intent.get("order_id"),
            "entry_order_id": intent.get("entry_order_id") or intent.get("order_id"),
            "trade_ids": [], "transactions_hashes": [], "pre_token_balance": pre_bal,
            "event_id": intent.get("event_id", ""), "market_id": intent.get("market_id", ""),
            "condition_id": intent.get("condition_id", ""), "token_id": token_id, "target_token": target_tok,
            "asset": asset_val, "candle_open_spot": candle_open,
            "entry_spot_ref": float(intent.get("entry_spot_ref") or candle_open),
            "spot_denomination": intent.get("spot_denomination", "USDT"),
            "candle_sigma": candle_sig, "candle_expiry_ts": candle_exp, "side": intent.get("side", "BUY"),
            "entry_price": target_price, "entry_shares": 0.0, "gross_entry_shares": 0.0,
            "remaining_shares": 0.0, "remaining_exit_shares": 0.0, "filled_exit_shares": 0.0,
            "remaining_cost_basis": intended_notional, "notional_usd": intended_notional,
            "intended_notional": intended_notional, "cost_basis_estimated": True,
            "fee_usd": float(intent.get("fee_usd", 0.0) or 0.0),
            "entry_fee_cash_usd": float(intent.get("entry_fee_cash_usd", 0.0) or 0.0),
            "entry_fee_asset": intent.get("entry_fee_asset", "USDC"),
            "fee_source": intent.get("fee_source", "crypto_fees_v2"),
            "target_exit_price": target_exit_p,
            "entry_time_utc": intent.get("created_at_utc", datetime.now(timezone.utc).isoformat()),
            "entry_ts": submitted_ts, "submitted_at_ts": submitted_ts,
            "status": ExecutionStatus.POSITION_CONFIRMED if verdict == "ARRIVED" else ExecutionStatus.MATCHED_PENDING_SETTLEMENT,
            "exit_order_id": None, "exit_order_status": "AWAITING_DELTA_SETTLEMENT",
            "created_at_utc": intent.get("created_at_utc", datetime.now(timezone.utc).isoformat()),
            "realized_exit_cash": 0.0, "realized_exit_fee": 0.0, "gross_exit_cash": 0.0,
            "average_exit_price": 0.0, "exit_trade_ids": [], "inventory_reconciled": False,
            "is_liquidating": False, "unwind_order_id": None, "unwind_start_time": 0.0,
            "order_records": {}, "recovered_from_intent": True,
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
                    sizing_eq_rec, has_frozen_rec = self._effective_sizing_equity_usd(tot_equity, now_ts)
                    self._update_equity_tier(sizing_eq_rec, allow_hwm_ratchet=(not has_frozen_rec))
                    ruin_chk_init = float(tot_equity)
                    if not self.dry_run and ruin_chk_init < float(self.risk_controller.min_equity_floor_usd) and hasattr(self.executor, "get_idle_usdce_balance"):
                        _idle_init_uc = self.executor.get_idle_usdce_balance()
                        if isinstance(_idle_init_uc, (int, float)) and not isinstance(_idle_init_uc, bool) and float(_idle_init_uc) > 0.0:
                            ruin_chk_init += float(_idle_init_uc)
                    self.risk_controller.check_equity_drawdown(ruin_chk_init, allow_auto_clear=True)
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
                if position_requires_lifecycle_resolution(pos):
                    self._resolve_lifecycle(tid, pos, open_orders, force=True)

            # 2. Exit-order alignment
            for tid, pos in list(self.active_positions.items()):
                if tid not in self.active_positions:
                    continue
                if position_is_settlement_receivable(pos) or position_requires_lifecycle_resolution(pos):
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
                        matched_pre = float(self._num(order_info.get("size_matched")) or 0.0)
                        if terminal in {"MATCHED", "FILLED", "CONFIRMED"} or (
                            matched_pre > 1e-6 and (terminal.startswith("CANCEL") or terminal in {"EXPIRED", "REJECTED", "INVALID"})
                        ):
                            pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                            pos["pending_canceled_order_id"] = exit_oid
                            self.save_state()
                            continue
                        if not (terminal.startswith("CANCEL") or terminal in {"EXPIRED", "REJECTED"} or (terminal == "INVALID" and matched_pre <= 1e-6)):
                            logger.warning(f"Cancellation not terminal: {exit_oid} (status={terminal}); retaining position.")
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
                    if order_status_str == "INVALID" and order_matched > 1e-6:
                        pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                        pos["pending_canceled_order_id"] = exit_oid
                        pos["status"] = "UNRESOLVED_SETTLEMENT"
                        self.save_state()
                        logger.warning(
                            f"[RECONCILIATION] {tid}: INVALID exit {exit_oid} has size_matched={order_matched:.2f}; deferring to fill reconciliation."
                        )
                        continue
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
                    is_order_terminal = (
                        order_status_str in {"MATCHED", "FILLED", "CONFIRMED"}
                        or order_status_str.startswith("CANCEL")
                        or order_status_str in {"EXPIRED", "REJECTED"}
                        or (order_status_str == "INVALID" and order_matched <= 1e-6)
                        or order_matched >= order_size - 1e-4
                    )
                    is_canceled = (
                        order_status_str.startswith("CANCEL")
                        or order_status_str in {"EXPIRED", "REJECTED"}
                        or (order_status_str == "INVALID" and order_matched <= 1e-6)
                    )
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
                    tranches = pos.get("exit_tranches", [])
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
        if pos.get("status") == "UNRESOLVED_SETTLEMENT" and not self.dry_run and bool(pos.get("exit_cash_estimated")):
            logger.info(f"[RESOLUTION DEFERRED] {tid}: awaiting CLOB fill confirmation for in-flight UNRESOLVED_SETTLEMENT exit.")
            return
        if pos.get("status") == "LIQUIDITY_CRISIS" or pos.get("exit_order_status") == "LIQUIDITY_CRISIS":
            pos["status"] = ExecutionStatus.POSITION_CONFIRMED
            pos["exit_order_status"] = "RESTING" if pos.get("exit_order_id") else "NONE"
        if not self.dry_run and position_requires_lifecycle_resolution(pos) and pos.get("exit_order_status") != "RESOLUTION_CANCEL_UNCONFIRMED":
            await asyncio.to_thread(self._resolve_lifecycle, tid, pos, None, True)
            if tid not in self.active_positions:
                return
            if position_requires_lifecycle_resolution(pos) and pos.get("exit_order_status") != "RESOLUTION_CANCEL_UNCONFIRMED":
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
                    # Closed markets purge resting order IDs from /data/order/{oid}; verify via open_orders + trade fills
                    try:
                        oo = await asyncio.to_thread(self._strict_open_orders)
                        oo_ids = {o.get("id") or o.get("orderID") for o in oo if o}
                        fills = await asyncio.to_thread(self.executor.get_account_fills, token_id, float(pos.get("entry_ts", 0.0) or 0.0), "SELL", exit_oid)
                    except Exception:
                        oo_ids, fills = {exit_oid}, None
                    if exit_oid in oo_ids or fills is None:
                        pos["exit_order_status"] = "RESOLUTION_CANCEL_UNCONFIRMED"
                        self.save_state()
                        return
                    if fills:
                        self._record_history_fills(pos, fills, taker=False)
                    if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.02:
                        self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                        return
                else:
                    self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False)
                    if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.02:
                        self._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                        return
                    if not summary["terminal"]:
                        pos["exit_order_status"] = "RESOLUTION_CANCEL_UNCONFIRMED"
                        self.save_state()
                        return
                self.executor.release_inventory(reservation_id=exit_oid)
            if str(exit_oid) not in pos.setdefault("canceled_maker_exit_oids", []):
                pos["canceled_maker_exit_oids"].append(str(exit_oid))
            pos.pop("_htm_passive_recycle_active", None)
            pos["exit_order_id"] = None
            pos["exit_order_status"] = "CANCELED_FOR_RESOLUTION"
        _prev_exit_oid = str(exit_oid or pos.get("unwind_order_id") or "").strip() or None
        _entry_oid_res = str(pos.get("entry_order_id") or pos.get("order_id") or "").strip() or None

        book_rem_shares = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", pos.get("entry_shares", 0.0))) or 0.0)
        rem_shares = book_rem_shares
        if not self.dry_run:
            from src.polymarket_research.riskless_protocol_v2_expansion import reconcile_resolution_fills_and_pre_redeem
            res_state, rem_shares = await reconcile_resolution_fills_and_pre_redeem(
                self, tid, pos, outcome_str, won, token_id, _prev_exit_oid, _entry_oid_res, book_rem_shares
            )
            if res_state != "RECEIVABLE":
                return
            head = await asyncio.to_thread(self.executor.get_current_block_number)
            _lookback_blks = 15000 if pos.get("_pre_redeemed_onchain") else 2500
            pos["status"] = "AWAITING_ONCHAIN_SETTLEMENT"
            pos["exit_order_status"] = "AWAITING_REDEMPTION"
            pos["is_liquidating"] = False
            pos["expected_terminal_payout_usd"] = round(rem_shares, 4)
            pos["redemption_receivable_usd"] = round(rem_shares, 4)
            pos["winning_shares_held"] = round(rem_shares, 6)
            pos["expected_winning_outcome"] = outcome_str
            pos["resolution_block"] = max(0, int(head) - _lookback_blks) if isinstance(head, int) else None
            self.save_state()
            logger.info(
                f"[RESOLVED - RECEIVABLE] {tid}: {rem_shares:.2f} winning shares held. Expected ${rem_shares:.2f} is a "
                "receivable, NOT realized cash, until a verified on-chain redemption receipt."
            )
            try:
                await asyncio.to_thread(self.poll_onchain_redemptions, True)
            except Exception as exc_red_imm:
                logger.debug(f"[AUTO-REDEEMER] Immediate post-resolution redemption poll notice: {exc_red_imm}")
            return

        # Dry-run mode: immediate virtual settlement
        payout = rem_shares * 1.0 if (won and rem_shares >= 0.01) else 0.0
        if payout > 0.0:
            self.record_fill_and_update_position(pos, "SETTLEMENT_RESOLUTION_PAYOUT", rem_shares, payout, 0.0)
        net_pnl = self._close_position(tid, pos, ExecutionStatus.SETTLED, "MARKET_RESOLVED", won=None)
        logger.info(f"✓ POSITION RESOLVED AT MATURITY: {tid} | Won={won} | RemShares={rem_shares:.2f} | Net PnL=${net_pnl:+.2f}")

    _maybe_recycle_disputed_htm_lock = _bind_hv_method(_hv__maybe_recycle_disputed_htm_lock, '_maybe_recycle_disputed_htm_lock')

    async def check_resolutions_and_manage_positions(self):
        """Monitors active positions for delta settlements, maker scalp fills, time-decay unwind, or finalized resolutions."""
        self._main_loop = asyncio.get_running_loop()
        if not self.dry_run:
            try:
                from src.polymarket_research.riskless_machine_gun_engine import PreSplitInventoryGun
                _psg = self.__dict__.get("_pre_split_gun") or setattr(self, "_pre_split_gun", PreSplitInventoryGun()) or self._pre_split_gun
                await _psg.tick(self, time.time(), fast_tick_reader=(lambda a: read_fast_tick(a, max_age_sec=1.5)) if callable(read_fast_tick) else None)
            except Exception as psg_exc:
                logger.debug(f"[PRE-SPLIT GUN] supervision notice: {psg_exc}")
        if (
            not self.dry_run
            and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
            and hasattr(self.executor, "wrap_idle_usdce_to_pusd")
        ):
            now_wrap = time.time()
            if (now_wrap - float(getattr(self, "_last_usdce_wrap_check_ts", 0.0) or 0.0)) >= 180.0:
                self._last_usdce_wrap_check_ts = now_wrap
                try:
                    wrap_res = await asyncio.to_thread(self.executor.wrap_idle_usdce_to_pusd, 1.0)
                    if isinstance(wrap_res, dict) and wrap_res.get("wrapped"):
                        self._pending_collateral_refresh = True
                        await self._async_refresh_collateral()
                except Exception as wrap_exc:
                    logger.debug(f"[PUSD-WRAP] periodic check notice: {wrap_exc}")
        if not self.active_positions:
            self._refresh_global_halt()
            return

        # 1. Check finalized candle resolutions from stream (binary buffered read)
        _default_res = PIPELINE_ROOT / "data/polymarket/finalized_market_resolutions.jsonl"
        _res_file = RESOLUTIONS_FILE if (RESOLUTIONS_FILE.parent == DATA_DIR or RESOLUTIONS_FILE != _default_res) else (DATA_DIR / "finalized_market_resolutions.jsonl")
        if _res_file.exists():
            try:
                current_res_size = _res_file.stat().st_size
                if current_res_size > self.last_res_file_pos:
                    with open(_res_file, "rb") as f:
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

        # 1a. Direct Gamma API resolution fallback for expired active positions
        if not self.dry_run and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2"):
            now_g = time.time()
            for tid, pos in list(self.active_positions.items()):
                exp_ts = float(pos.get("candle_expiry_ts", 0.0) or 0.0)
                m_id = str(pos.get("market_id") or "")
                _fast_sub_h = exp_ts > 0.0 and (exp_ts - float(pos.get("entry_ts") or 0.0)) <= 3600.0
                _sll_early = (bool(pos.get("is_single_leg_lock")) and now_g >= float(pos.get("entry_ts") or 0.0) + 45.0) or bool(pos.get("_zero_bal_gamma_urgent"))
                _poll_iv = 3.0 if (_fast_sub_h and now_g >= exp_ts + 3.0) else (8.0 if (pos.get("is_single_leg_lock") and now_g < exp_ts + 12.0) else 15.0)
                if ((exp_ts > 0.0 and now_g >= exp_ts + (3.0 if _fast_sub_h else 12.0)) or _sll_early) and pos.get("resolved_winning_outcome") is None and m_id.isdigit() and int(m_id) >= 100000:
                    if now_g - float(pos.get("_last_gamma_res_poll", 0.0) or 0.0) >= _poll_iv:
                        pos.pop("_zero_bal_gamma_urgent", None)
                        pos["_last_gamma_res_poll"] = now_g
                        try:
                            r_gm = await asyncio.to_thread(
                                lambda: self.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{m_id}", timeout=3.0).json()
                            )
                            if isinstance(r_gm, dict) and r_gm.get("umaResolutionStatus") is not None:
                                pos["umaResolutionStatus"] = str(r_gm.get("umaResolutionStatus") or "")
                            if isinstance(r_gm, dict) and (r_gm.get("umaResolutionStatus") == "resolved" or r_gm.get("closed")):
                                raw_p = r_gm.get("outcomePrices")
                                p_list = json.loads(raw_p) if isinstance(raw_p, str) else (raw_p or [])
                                raw_t = r_gm.get("clobTokenIds")
                                t_list = json.loads(raw_t) if isinstance(raw_t, str) else (raw_t or [])
                                pos_tok = str(pos.get("token_id") or "")
                                tgt_tok = str(pos.get("target_token") or "UP")
                                _opp_lbls = {"UP": "DOWN", "DOWN": "UP", "YES": "NO", "NO": "YES"}
                                opp_tok = _opp_lbls.get(tgt_tok.upper(), f"NOT_{tgt_tok}")
                                if len(p_list) >= 2 and len(t_list) >= 2 and pos_tok in (str(t_list[0]), str(t_list[1])):
                                    idx = 0 if pos_tok == str(t_list[0]) else 1
                                    if str(p_list[idx]) in ("1", "1.0"):
                                        await self._apply_market_resolution(tid, pos, tgt_tok)
                                    elif str(p_list[1 - idx]) in ("1", "1.0"):
                                        await self._apply_market_resolution(tid, pos, opp_tok)
                                elif len(p_list) >= 2 and str(p_list[0]) in ("1", "1.0") and str(p_list[1]) in ("0", "0.0"):
                                    await self._apply_market_resolution(tid, pos, "YES" if tgt_tok.upper() in ("YES", "NO") else "UP")
                                elif len(p_list) >= 2 and str(p_list[0]) in ("0", "0.0") and str(p_list[1]) in ("1", "1.0"):
                                    await self._apply_market_resolution(tid, pos, "NO" if tgt_tok.upper() in ("YES", "NO") else "DOWN")
                            elif (
                                isinstance(r_gm, dict)
                                and str(r_gm.get("umaResolutionStatus") or "").strip().lower() == "disputed"
                                and not r_gm.get("closed")
                                and bool(pos.get("hold_to_maturity_lock"))
                                and bool(pos.get("is_single_leg_lock"))
                                and "KMIA" not in str(pos.get("asset") or "").upper()
                                and "KMIA" not in str(tid or "").upper()
                            ):
                                await self._maybe_recycle_disputed_htm_lock(tid, pos, now_g)
                        except Exception as gm_err:
                            logger.debug(f"Gamma resolution poll notice for {tid}: {gm_err}")

        # 1b. Verified on-chain redemption receipts for resolved winning receivables
        if not self.dry_run:
            try:
                _force_red = (
                    any(position_is_settlement_receivable(p) for p in self.active_positions.values())
                    and (time.time() - float(getattr(self, "_last_redemption_poll", 0.0) or 0.0)) >= 2.5
                )
                await asyncio.to_thread(self.poll_onchain_redemptions, _force_red)
            except Exception as e:
                logger.error(f"[REDEMPTION] Poll error: {e}")

        # 2. Check live positions for delta confirmation, maker scalp fills, and time-decay unwind
        if self.dry_run:
            # DRY-RUN SIMULATION ONLY: simulate maker fill if best bid reaches target exit price
            for tid, pos in list(self.active_positions.items()):
                try:
                    token_id = pos.get("token_id")
                    if not token_id or position_is_settlement_receivable(pos) or pos.get("hold_to_maturity_lock"):
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
                            self.risk_controller.record_trade_pnl(
                                net_pnl,
                                is_non_directional=bool(
                                    pos.get("is_dominance_box")
                                    or pos.get("is_single_leg_lock")
                                    or pos.get("is_legged_out_residual")
                                    or "BOX" in str(pos.get("sleeve") or "").upper()
                                ),
                            )
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
            mkt_ws = getattr(self, "_pos_market_ws", None)
            if mkt_ws is not None:
                mkt_ws.set_desired_tokens(self._desired_market_ws_tokens(now_ts))
            try:
                await self._maybe_merge_live_complete_sets(now_ts)
            except Exception as merge_exc:
                logger.exception(f"[C1 MERGE] complete-set merge pass failed (supervision continues): {merge_exc}")
            try:
                await self._try_atomic_box_overround_unwind(now_ts, open_oids)
            except Exception as ovr_exc:
                logger.exception(f"[BOX OVERROUND] dual-leg unwind pass failed (supervision continues): {ovr_exc}")
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
                        pos.setdefault("_unresolved_settle_seq", int(getattr(self, "_collateral_sync_seq", 0) or 0))
                        settle_oid = pos.get("exit_order_id") or pos.get("pending_settlement_order_id") or pos.get("unwind_order_id")
                        est_oids = [
                            str(k)
                            for k, v in (pos.get("order_records") or {}).items()
                            if isinstance(v, dict) and v.get("cash_is_estimated")
                        ]
                        c_mkr_set_u = {str(x) for x in (pos.get("canceled_maker_exit_oids") or []) if x}
                        for poll_oid in dict.fromkeys(([str(settle_oid)] if settle_oid else []) + est_oids):
                            rec_meta = (pos.get("order_records") or {}).get(str(poll_oid)) or {}
                            if isinstance(rec_meta, dict) and "is_taker" in rec_meta:
                                is_taker_oid = bool(rec_meta["is_taker"])
                            else:
                                is_taker_oid = (str(poll_oid) != str(pos.get("exit_order_id") or "") and str(poll_oid) not in c_mkr_set_u)
                            summary = await asyncio.to_thread(self.executor.get_order_fill_summary, str(poll_oid), pos.get("token_id"))
                            if summary is not None:
                                fb_px = float(
                                    (rec_meta.get("fallback_price") if isinstance(rec_meta, dict) else None)
                                    or ((pos.get("unwind_limit_price") or 0.01) if is_taker_oid else (pos.get("target_exit_price", 0.0) or 0.0))
                                )
                                self._record_order_summary(pos, summary, fb_px, taker=is_taker_oid)
                            cur_rec_u = (pos.get("order_records") or {}).get(str(poll_oid)) or {}
                            if (
                                (summary is None or (isinstance(cur_rec_u, dict) and cur_rec_u.get("cash_is_estimated")))
                                and pos.get("token_id")
                            ):
                                hist_fills = await asyncio.to_thread(
                                    self._fetch_account_fills,
                                    str(pos.get("token_id")),
                                    max(0.0, float(pos.get("entry_ts", 0.0) or 0.0) - 60.0),
                                    "SELL",
                                    str(poll_oid),
                                    tid,
                                )
                                if isinstance(hist_fills, list) and hist_fills:
                                    self._record_history_fills(pos, hist_fills, taker=is_taker_oid)
                        is_resolved_loss = (
                            pos.get("pending_settlement_close_reason") in {"MARKET_RESOLVED_LOSS", "EXPIRED_OUT_OF_MONEY"}
                            or (pos.get("close_reason") and "MARKET_RESOLVED_LOSS" in str(pos.get("close_reason")))
                        )
                        has_part_fills_u = float(pos.get("filled_exit_shares", 0.0) or 0.0) > 0.01
                        if (is_resolved_loss and not has_part_fills_u) or (
                            not pos.get("exit_cash_estimated", False) and float(pos.get("estimated_exit_cash", 0.0) or 0.0) == 0.0
                        ):
                            if is_resolved_loss and not has_part_fills_u:
                                pos["exit_cash_estimated"] = False
                                pos["estimated_exit_cash"] = 0.0
                            self._close_position(
                                tid, pos,
                                pos.get("pending_settlement_close_status", ExecutionStatus.SETTLED if is_resolved_loss else ExecutionStatus.FILLED),
                                pos.get("pending_settlement_close_reason", "MARKET_RESOLVED_LOSS" if is_resolved_loss else "SETTLEMENT_CONFIRMED_CLOB"),
                                won=False if (is_resolved_loss and not has_part_fills_u) else None,
                            )
                        continue
                    if pos.get("resolved_winning_outcome") is not None:
                        await self._apply_market_resolution(tid, pos, pos["resolved_winning_outcome"])
                        continue
                    if position_requires_lifecycle_resolution(pos):
                        await asyncio.to_thread(self._resolve_lifecycle, tid, pos, open_orders)
                        if tid not in self.active_positions or position_requires_lifecycle_resolution(pos):
                            continue
                    _uma_st_sup = str(pos.get("umaResolutionStatus") or pos.get("uma_resolution_status") or "").strip().lower()
                    if (
                        not pos.get("exit_order_id")
                        and not pos.get("is_liquidating")
                        and not pos.get("is_legged_out_residual")
                        and ("KMIA" in str(pos.get("asset") or "").upper() or "KMIA" in str(tid or "").upper())
                        and (
                            pos.get("hold_to_maturity_lock")
                            or _uma_st_sup == "disputed"
                            or max(0.0, float(pos.get("candle_expiry_ts", now_ts + 600.0) or 0.0) - now_ts) <= 0.0
                        )
                    ):
                        continue

                    exit_oid = pos.get("exit_order_id")
                    token_id = pos.get("token_id")
                    expiry_ts = pos.get("candle_expiry_ts", now_ts + 600.0)
                    tte_rem = max(0.0, expiry_ts - now_ts)
                    if (
                        not self.dry_run
                        and token_id
                        and pos.get("hold_to_maturity_lock")
                        and pos.get("status") == ExecutionStatus.MATCHED_PENDING_SETTLEMENT
                        and (now_ts - float(pos.get("_last_htm_inv_chk", 0.0) or 0.0)) >= 10.0
                    ):
                        pos["_last_htm_inv_chk"] = now_ts
                        bal_h, src_h = await asyncio.to_thread(self._wallet_token_balance, token_id)
                        pre_h = float(pos.get("pre_token_balance", 0.0) or 0.0)
                        exp_h = float(pos.get("entry_shares", 0.0) or 0.0)
                        if bal_h is not None and src_h in {self.ONCHAIN_SOURCE, "CLOB_BALANCE_API"}:
                            d_h = bal_h - pre_h
                            fr_h = float(pos.get("fee_rate_applied", 0.0) or 0.0)
                            if d_h >= max(0.01, exp_h - 0.05):
                                pos["status"], pos["inventory_reconciled"] = ExecutionStatus.POSITION_CONFIRMED, True
                                self.save_state()
                            elif fr_h > 0.0 and d_h >= max(0.01, exp_h * (1.0 - fr_h * 0.30) - 0.05):
                                pos["entry_shares"] = pos["remaining_shares"] = pos["remaining_exit_shares"] = round(d_h, 4)
                                pos["entry_fee_asset"], pos["entry_fee_cash_usd"] = "SHARES", 0.0
                                pos["status"], pos["inventory_reconciled"] = ExecutionStatus.POSITION_CONFIRMED, True
                                self.save_state()
                    elif (
                        not self.dry_run
                        and token_id
                        and pos.get("hold_to_maturity_lock")
                        and pos.get("status") == ExecutionStatus.POSITION_CONFIRMED
                        and "KMIA" not in str(pos.get("asset") or "").upper()
                        and "KMIA" not in str(tid or "").upper()
                        and _uma_st_sup != "disputed"
                        and (now_ts - float(pos.get("_last_htm_prereed_chk", 0.0) or 0.0)) >= 12.0
                    ):
                        pos["_last_htm_prereed_chk"] = now_ts
                        bal_p, src_p = await asyncio.to_thread(self._wallet_token_balance, token_id)
                        if bal_p is not None and src_p == self.ONCHAIN_SOURCE and float(bal_p) <= 0.0001:
                            pos["_last_gamma_res_poll"] = 0.0
                            pos["_zero_bal_gamma_urgent"] = True

                    # Phase A: entry finality + maker exit via the single shared gate (P0-02 / P0-04)
                    eff_cancel_win = 5.0 if pos.get("sleeve") == "SLEEVE_4_BOUNDARY_SNIPE" else self.tte_cancel_window
                    if (
                        not exit_oid
                        and position_may_post_new_maker_exit(pos)
                        and tte_rem >= eff_cancel_win
                    ):
                        pos.pop("recovered_from_intent", None)
                        posted = await asyncio.to_thread(self._attempt_maker_exit_post, tid, pos)
                        exit_oid = pos.get("exit_order_id")
                        if posted or not pos.get("inventory_reconciled") or position_requires_lifecycle_resolution(pos):
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
                    from src.polymarket_research.riskless_machine_gun_engine import is_locked_arbitrage_box_leg
                    _unhedged_sc = bool(
                        str(pos.get("box_type") or "") == "SPORTS_CORRIDOR"
                        and not str(pos.get("box_partner_trade_id") or "")
                        and not is_locked_arbitrage_box_leg(pos, self.active_positions)
                        and not pos.get("hold_to_maturity_lock")
                    )
                    if _unhedged_sc and 0.05 < float(pos.get("target_exit_price") or 0.99) < 0.95 and not pos.get("custom_maker_exit_price"):
                        pos["custom_maker_exit_price"] = float(pos["target_exit_price"])
                    _hz_mfe_triggered = False
                    current_spot = None
                    open_spot = float(pos.get("candle_open_spot", 0.0) or 0.0)
                    entry_spot_ref = float(pos.get("entry_spot_ref") or pos.get("candle_open_spot") or open_spot)
                    candle_sigma = float(pos.get("candle_sigma", 0.005) or 0.0)
                    spot_valid = False
                    spot_disp = 0.0
                    entry_spot_disp = 0.0
                    entry_move_pct = 0.0
                    if (
                        not exit_oid
                        and not pos.get("is_liquidating")
                        and not retry_due
                        and ("KMIA" in str(pos.get("asset") or "").upper() or "KMIA" in str(tid or "").upper())
                        and (pos.get("hold_to_maturity_lock") or tte_rem <= 0.0)
                    ):
                        continue
                    if (not pos.get("is_liquidating") or retry_due) and token_id and rem_shrs > 0.01:
                        # v3.3: /dev/shm fast tick top-of-book first (<=1.5s old), then live CLOB market WS, then REST fallback
                        book = self._get_verified_shm_book(pos)
                        if book is None and mkt_ws is not None and "get_market_book_async" not in getattr(self.executor, "__dict__", {}):
                            book = mkt_ws.get_book(token_id, max_age_sec=2.0)
                        if book is None:
                            try:
                                book = await self.executor.get_market_book_async(token_id)
                            except Exception as bk_err:
                                _bk_err_l = str(bk_err).lower()
                                if "404" in _bk_err_l or "no orderbook exists" in _bk_err_l:
                                    pos["_book_closed_404"] = True
                                    book = {}
                                    tte_rem = 0.0
                                elif pos.get("hold_to_maturity_lock") and not pos.get("is_liquidating"):
                                    logger.debug(f"[HTM BOOK POLL NOTICE] {tid}: {bk_err}; skipping pass.")
                                    continue
                                elif (
                                    (
                                        any(c in _bk_err_l for c in ("429", "502", "503", "504", "timeout", "timed out", "remoteprotocolerror", "connecterror", "connection"))
                                        or "timeout" in type(bk_err).__name__.lower()
                                    )
                                    and not pos.get("is_liquidating")
                                    and (pos.get("is_single_leg_lock") or pos.get("is_dominance_box") or tte_rem <= 0.0)
                                ):
                                    logger.debug(f"[TRANSIENT BOOK POLL NOTICE] {tid}: {bk_err}; continuing to Phase D fill check.")
                                    book = {}
                                else:
                                    raise
                        bids = book.get("bids", []) if isinstance(book, dict) else []
                        asks = book.get("asks", []) if isinstance(book, dict) else []
                        if bids or asks:
                            pos.pop("_book_closed_404", None)
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
                        if pos.get("hold_to_maturity_lock"):
                            from src.polymarket_research.riskless_protocol_v2_expansion import maybe_early_profit_recycle_htm_lock, maybe_manage_passive_htm_early_maker_recycle
                            if (best_b >= 0.998 and await maybe_early_profit_recycle_htm_lock(self, tid, pos, book, now_ts)) or await maybe_manage_passive_htm_early_maker_recycle(self, tid, pos, book, now_ts, open_oids):
                                continue
                            exit_oid = pos.get("exit_order_id")
                        _is_dom_box = bool(pos.get("is_dominance_box") or pos.get("is_single_leg_lock"))

                        # PAA_Q2: Pre-Kickoff Maker Step-Down (T-30m / T-15m / undercut) for unhedged SPORTS_CORRIDOR legs
                        if (
                            _unhedged_sc
                            and exit_oid
                            and not pos.get("is_liquidating")
                            and rem_shrs >= 5.0
                            and best_b >= 0.35
                            and tte_rem > 300.0
                        ):
                            _cur_sc_tp = float(pos.get("target_exit_price") or 0.99)
                            _sc_px = (
                                round(best_b + 0.01, 2) if tte_rem <= 900.0
                                else max(round(best_b + 0.02, 2), round(min(_cur_sc_tp - 0.02, best_b + 0.04), 2)) if tte_rem <= 1800.0
                                else (round(best_a - 0.01, 2) if (0.58 <= best_a < _cur_sc_tp - 1e-4 and best_a >= best_b + 0.02) else None)
                            )
                            if _sc_px is not None and best_b + 1e-4 < _sc_px < _cur_sc_tp - 1e-4 and (now_ts - float(pos.get("_sc_step_ts", 0.0) or 0.0)) >= 180.0:
                                pos["_sc_step_ts"] = now_ts
                                pos["custom_maker_exit_price"] = _sc_px
                                logger.info(f"[PAA PRE-KICKOFF STEPDOWN] {tid}: TTE={tte_rem:.0f}s bid=${best_b:.2f} ask=${best_a:.2f} -> ${_cur_sc_tp:.2f} to ${_sc_px:.2f}")
                                await self._atomic_replace_maker_exit(tid, pos, _sc_px)
                                continue

                        # v3.4 Queue-Priority Jumping during position supervision
                        if (
                            not _is_dom_box
                            and exit_oid
                            and not pos.get("queue_jumped")
                            and not pos.get("is_liquidating")
                            and rem_shrs > 0.01
                            and tte_rem >= self.tte_cancel_window
                        ):
                            curr_target_px = float(pos.get("target_exit_price") or 0.0)
                            _allow_sup_qjump = (
                                curr_target_px == 0.99
                                or (
                                    curr_target_px == 0.98
                                    and (self._effective_exit_policy() != "hold_98" or (tte_rem <= 75.0 and best_b >= 0.96))
                                )
                            )
                            if _allow_sup_qjump:
                                jump_px = compute_queue_priority_maker_price(
                                    entry_px, rem_shrs, bids, asks, curr_target_px
                                )
                                if jump_px is not None and (now_ts - float(pos.get("queue_jump_attempt_ts", 0.0) or 0.0)) >= 30.0:
                                    pos["queue_jump_attempt_ts"] = now_ts
                                    logger.info(
                                        f"[QUEUE JUMP SUPERVISION] Position {tid}: massive wall at ${curr_target_px:.2f}. "
                                        f"Stepping 1c in front to ${jump_px:.2f} (cancelling OID: {exit_oid})."
                                    )
                                    posted = await self._atomic_replace_maker_exit(tid, pos, jump_px)
                                    if tid not in self.active_positions:
                                        continue
                                    if posted:
                                        pos["queue_jumped"] = True
                                    exit_oid = pos.get("exit_order_id")
                                    rem_shrs = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", rem_shrs)) or 0.0)

                        asset_sym = pos.get("asset", "BTC")
                        if not _is_dom_box and str(asset_sym or "").upper() in {"BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "HYPE", "ZEC", "XAU", "XAG"}:
                            if pos.get("spot_denomination") == "USD":
                                current_spot = await asyncio.to_thread(self.get_usd_reference_spot_price, asset_sym)
                            else:
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

                        if (
                            not _is_dom_box
                            and evaluate_optimal_stopping_exit is not None
                            and (self._effective_exit_policy() != "hold_98" or os.environ.get("PM_ENABLE_HOLD98_OBI_STEPDOWN", "0") == "1")
                            and not getattr(self, "hold_to_maturity", False)
                            and exit_oid
                            and not pos.get("obi_stepped_down")
                            and not pos.get("is_liquidating")
                            and rem_shrs >= 5.0
                            and tte_rem >= self.tte_cancel_window
                            and best_b > 0.0
                            and best_a > 0.0
                            and bids
                            and asks
                        ):
                            _b1_sz = sum(
                                float(b.get("size", 0.0) if isinstance(b, dict) else b[1])
                                for b in bids
                                if abs(float(b.get("price", 0.0) if isinstance(b, dict) else b[0]) - best_b) < 1e-6
                            )
                            _a1_sz = sum(
                                float(a.get("size", 0.0) if isinstance(a, dict) else a[1])
                                for a in asks
                                if abs(float(a.get("price", 0.0) if isinstance(a, dict) else a[0]) - best_a) < 1e-6
                            )
                            _obi_cur = (_b1_sz - _a1_sz) / max(1e-6, _b1_sz + _a1_sz)
                            _opt_exit = evaluate_optimal_stopping_exit(
                                entry_px=entry_px,
                                rem_shares=rem_shrs,
                                best_bid=best_b,
                                best_ask=best_a,
                                curr_target_px=float(pos.get("target_exit_price") or 0.0),
                                tte_sec=tte_rem,
                                obi_l1=_obi_cur,
                                v_spot_15s_pct=v_spot_15s_pct,
                            )
                            if _opt_exit.get("action") == "OBI_MAKER_STEP_DOWN" and (now_ts - float(pos.get("obi_step_attempt_ts", 0.0) or 0.0)) >= 30.0:
                                pos["obi_step_attempt_ts"] = now_ts
                                _step_px = float(_opt_exit["target_px"])
                                logger.info(
                                    f"[OBI MAKER STEP-DOWN] {tid}: heavy sell wall obi_l1={_obi_cur:.2f} <= -0.40 at TTE={tte_rem:.0f}s "
                                    f"(v_spot_15s={v_spot_15s_pct:+.3f}%); stepping resting maker ask to ${_step_px:.2f}."
                                )
                                posted_step = await self._atomic_replace_maker_exit(
                                    tid, pos, _step_px, collapse_tranches=True
                                )
                                if tid not in self.active_positions:
                                    continue
                                if posted_step:
                                    pos["obi_stepped_down"] = True
                                exit_oid = pos.get("exit_order_id")
                                rem_shrs = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", rem_shrs)) or 0.0)

                        # Explicit Liquidation Precedence Rules (Probe 3 & R3-08 Fix):
                        # 1. Pre-Expiry Window (TTE <= 300s):
                        #    - pin_threshold_300 = 2.0 * open_spot * candle_sigma * sqrt(TTE / 3600.0)
                        #    - Inside the pin-risk band or ITM: held for terminal settlement; CLOB stops SUPPRESSED.
                        #    - Strictly beyond -2-sigma adverse: definitively OTM; pre_expiry_otm_salvage triggers.
                        # 2. Normal Trading Window (TTE > 300s): standard CLOB bid and spot structural stops apply.
                        is_pre_expiry_window = bool(tte_rem <= 300.0)
                        sigma_valid = math.isfinite(candle_sigma) and candle_sigma > 0 and open_spot > 0
                        _is_5m_pos = str(pos.get("horizon") or "").lower() == "5m"
                        _is_subhourly_pos = bool(
                            _is_5m_pos
                            or pos.get("is_subhourly")
                            or pos.get("horizon") == "15m"
                            or pos.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M"
                            or (
                                0.0 < float(pos.get("entry_tte", 3600.0) or 3600.0) <= 900.0
                                and pos.get("sleeve") == "SLEEVE_4_BOUNDARY_SNIPE"
                                and "hourly" not in str(pos.get("title", "") or "").lower()
                            )
                        )
                        _ft_sup = read_fast_tick(asset_sym, max_age_sec=2.0) if _is_subhourly_pos or not _is_dom_box else None
                        _mkt_ft = (
                            (_ft_sup.get("markets") or {}).get(str(pos.get("market_id") or ""))
                            if isinstance(_ft_sup, dict) and isinstance(_ft_sup.get("markets"), dict)
                            else None
                        )
                        if _mkt_ft is None and isinstance(_ft_sup, dict):
                            for _hk in ("m15", "m5", "h1"):
                                _cand_m = _ft_sup.get(_hk)
                                if isinstance(_cand_m, dict) and str(_cand_m.get("market_id") or "") == str(pos.get("market_id") or ""):
                                    _mkt_ft = _cand_m
                                    break
                        if (
                            not _is_dom_box
                            and not self.dry_run
                            and evaluate_guarded_complement_merge is not None
                            and exit_oid
                            and not pos.get("is_liquidating")
                            and rem_shrs >= 5.0
                            and tte_rem >= 12.0
                            and isinstance(_mkt_ft, dict)
                            and (os.getenv("PM_ENABLE_ONCHAIN_MERGE", "0") == "1" or os.getenv("POLY_BUILDER_API_KEY") or getattr(self.executor, "signature_type", 3) != 3)
                            and (now_ts - float(pos.get("comp_merge_attempt_ts", 0.0) or 0.0)) >= 15.0
                        ):
                            _opp_s = "DOWN" if pos.get("target_token") == "UP" else "UP"
                            _opp_bk = _mkt_ft.get(_opp_s) or {}
                            _opp_ask = float(_opp_bk.get("best_ask") or 1.0)
                            _opp_tok = str(_opp_bk.get("token_id") or "")
                            if _opp_tok and 0.0 < _opp_ask <= 0.03:
                                _cm_plan = evaluate_guarded_complement_merge(
                                    rem_shares=rem_shrs,
                                    opp_ask=_opp_ask,
                                    opp_ask_size=float(_opp_bk.get("ask_size_l1") or 0.0),
                                    min_net_proceeds_ps=max(0.9820, float(pos.get("target_exit_price") or 0.98) + 0.0020),
                                    fee_rate=self._exit_taker_fee_rate(pos),
                                    fee_exponent=float(pos.get("market_fee_exponent", pos.get("fee_exponent_applied", 1.0)) or 1.0),
                                )
                                if _cm_plan.get("approved"):
                                    pos["comp_merge_attempt_ts"] = now_ts
                                    if await self._execute_guarded_complement_merge(tid, pos, _opp_tok, _cm_plan, now_ts):
                                        continue
                        if (
                            not _is_dom_box
                            and _is_subhourly_pos
                            and not _is_5m_pos
                            and evaluate_d1_15m_to_5m_corridor_conversion is not None
                            and 15.0 <= tte_rem <= 295.0
                            and rem_shrs >= 5.0
                            and isinstance(_ft_sup, dict)
                            and isinstance(_ft_sup.get("m5"), dict)
                        ):
                            _d1_c = evaluate_d1_15m_to_5m_corridor_conversion(pos, _ft_sup.get("m5"), now_ts=now_ts)
                            if _d1_c.get("eligible"):
                                pos["d1_corridor_candidate"] = _d1_c

                        _candle_denom_s = 300.0 if _is_5m_pos else (900.0 if _is_subhourly_pos else 3600.0)
                        pin_threshold_300 = (2.0 * open_spot * candle_sigma * math.sqrt(max(tte_rem, 1.0) / _candle_denom_s)) if (spot_valid and sigma_valid) else 0.0

                        # Probe I Fix: missing/invalid spot OR volatility in the pre-expiry window -> unknown
                        # pin-risk band -> DETERMINISTIC_TERMINAL_HOLD (no stops, salvage dumps or retries).
                        volatility_unknown = bool(is_pre_expiry_window and not sigma_valid)
                        spot_unknown = bool(is_pre_expiry_window and not spot_valid)
                        terminal_hold_forced = volatility_unknown or spot_unknown

                        in_pin_risk_band = bool(
                            is_pre_expiry_window and spot_valid and sigma_valid and (spot_disp >= -pin_threshold_300)
                        ) or terminal_hold_forced

                        raw_pre_expiry_otm = bool(
                            is_pre_expiry_window and spot_valid and sigma_valid and (spot_disp < -pin_threshold_300) and (best_b >= 0.01)
                        )
                        if (
                            raw_pre_expiry_otm
                            and _is_subhourly_pos
                            and 0.0 < tte_rem < 60.0
                            and should_suppress_final60s_twap_salvage is not None
                            and isinstance(_mkt_ft, dict)
                        ):
                            _sig_1h_pos = candle_sigma * (math.sqrt(12.0) if _is_5m_pos else 2.0)
                            _tw_sup, _ = should_suppress_final60s_twap_salvage(
                                side=str(pos.get("target_token") or "UP"),
                                strike_open=open_spot,
                                current_spot=float(current_spot),
                                twap_locked_mean=_mkt_ft.get("twap_locked_mean"),
                                tte_sec=tte_rem,
                                sigma_1h=_sig_1h_pos,
                                twap_locked_weight=_mkt_ft.get("twap_locked_weight"),
                            )
                            if _tw_sup:
                                raw_pre_expiry_otm = False
                                in_pin_risk_band = True
                        if raw_pre_expiry_otm:
                            if tte_rem <= 10.0 or getattr(self.executor, "auth_mode", "") not in ("LIVE", "AUTHENTICATED_L2"):
                                pre_expiry_otm_salvage = True
                            else:
                                _otm_deb_s = 2.0 if tte_rem <= 60.0 else 3.0
                                _otm_ts = pos.get("pre_expiry_otm_detected_ts")
                                if _otm_ts is None:
                                    pos["pre_expiry_otm_detected_ts"] = now_ts
                                    pre_expiry_otm_salvage = False
                                else:
                                    pre_expiry_otm_salvage = (now_ts - float(_otm_ts)) >= _otm_deb_s
                        else:
                            pos.pop("pre_expiry_otm_detected_ts", None)
                            pre_expiry_otm_salvage = False
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

                        # Unified v5.0 Expected-Value Terminal-TWAP Exit Supervisor (`ev_terminal_twap_t5`):
                        # Offline-spot fallback when `not spot_valid`; otherwise positive-EV Student-t(df=5) + 60s TWAP salvage.
                        spot_crash_triggered = False
                        max_bid_drop = 0.10 if tranche1_filled else 0.20
                        _is_live_auth = (
                            (not self.dry_run)
                            and (getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2"))
                            and bool(token_id and str(token_id).isdigit() and len(str(token_id)) >= 20)
                        )
                        _is_15m_pos = _is_subhourly_pos
                        if (
                            best_b >= 0.08
                            and best_b <= (entry_px - max_bid_drop)
                            and (not is_pre_expiry_window and not spot_valid and best_b <= 0.36)
                            and tte_rem >= 25.0
                        ):
                            low_bid_start = pos.get("low_bid_detected_ts")
                            if low_bid_start is None:
                                pos["low_bid_detected_ts"] = now_ts
                            elif (now_ts - float(low_bid_start)) >= 6.0:
                                spot_crash_triggered = True
                        else:
                            pos.pop("low_bid_detected_ts", None)

                        opposite_salvage_triggered, wrong_side_pct, _ev_diag = evaluate_ev_terminal_twap_t5_salvage(
                            pos=pos, now_ts=now_ts, tte_rem=tte_rem, spot_valid=spot_valid, open_spot=open_spot,
                            spot_disp=spot_disp, sigma_valid=sigma_valid, candle_sigma=candle_sigma,
                            is_subhourly_pos=_is_subhourly_pos, is_5m_pos=_is_5m_pos, best_b=best_b,
                            entry_px=entry_px, v_spot_15s_pct=v_spot_15s_pct,
                            exit_fee_rate=self._exit_taker_fee_rate(pos),
                            fee_exp=float(pos.get("market_fee_exponent", pos.get("fee_exponent_applied", 1.0)) or 1.0),
                            twap_locked_mean=_mkt_ft.get("twap_locked_mean") if isinstance(_mkt_ft, dict) else None,
                            twap_locked_weight=_mkt_ft.get("twap_locked_weight") if isinstance(_mkt_ft, dict) else None,
                            current_spot=float(current_spot) if spot_valid and current_spot else None,
                            is_live_auth=_is_live_auth,
                        )

                        # PEAK-BID TRAILING PROFIT RATCHET (Pillar 3 Unified WFO-Optimal Dynamic Ratchet):
                        # Restores Purged-WFO selected ratchet_arm=0.16 (max(0.84, entry_px + 0.16)) so +16c..+20c winning peaks
                        # (e.g. $0.89-$0.92) never round-trip into -$13.50/-$15.24 terminal wipeouts (100% Holdout WR, 0 wipeouts).
                        if best_b > 0:
                            pos["max_seen_bid"] = max(float(pos.get("max_seen_bid", 0.0) or 0.0), best_b)
                        max_seen_bid = float(pos.get("max_seen_bid", 0.0) or 0.0)

                        trailing_ratchet_triggered = False
                        _hz_mfe_triggered = False
                        trail_floor = 0.0
                        _ex_gov = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("exit_supervisor", {})
                        _hz_on = bool(_is_live_auth and _ex_gov.get("enable_high_zone_mfe_ratchet", True))
                        _hz_arm = float(_ex_gov.get("high_zone_mfe_arm_bid", 0.93))
                        _hz_drop = float(_ex_gov.get("high_zone_mfe_drop", 0.04))
                        _hz_hold_s = float(_ex_gov.get("high_zone_mfe_hold_confirm_sec", 2.0))
                        _hz_min_tte = float(_ex_gov.get("high_zone_mfe_min_tte_sec", 16.0))
                        if _is_live_auth:
                            _rem_to_tp = max(0.04, 0.98 - entry_px)
                            _min_ratchet_arm = round(min(0.945, max(0.86, entry_px + max(0.05, 0.65 * _rem_to_tp))), 4)
                        else:
                            _min_ratchet_arm = max(0.82, entry_px + 0.12)
                        _min_ratchet_gain = 0.03 if _is_live_auth else 0.04
                        _rem_candle_sig = (candle_sigma * math.sqrt(max(tte_rem, 15.0) / _candle_denom_s)) if sigma_valid else 0.0
                        _deep_itm_z = (spot_disp / max(1e-9, open_spot * max(0.00020, _rem_candle_sig))) if (spot_valid and sigma_valid) else 0.0
                        if _hz_on and 0.0 < entry_px < 0.90 and not pos.get("is_single_leg_lock") and max_seen_bid >= _hz_arm:
                            trail_floor = round(max_seen_bid - _hz_drop, 4)
                            if best_b <= trail_floor + 1e-6 and tte_rem >= _hz_min_tte and best_b >= max(0.50, round(entry_px + 0.03, 4)):
                                ratchet_start = pos.get("trail_stop_detected_ts") or pos.get("trailing_ratchet_detected_ts")
                                if ratchet_start is None:
                                    pos["trail_stop_detected_ts"] = now_ts
                                    pos["trailing_ratchet_detected_ts"] = now_ts
                                elif (now_ts - float(ratchet_start)) >= _hz_hold_s:
                                    trailing_ratchet_triggered = True
                                    _hz_mfe_triggered = True
                            else:
                                pos.pop("trail_stop_detected_ts", None)
                                pos.pop("trailing_ratchet_detected_ts", None)
                        elif max_seen_bid >= _min_ratchet_arm and entry_px > 0 and _deep_itm_z < 1.50:
                            trail_delta = (0.04 if max_seen_bid >= 0.93 else 0.05) if _is_live_auth else (0.05 if max_seen_bid >= 0.90 else 0.07)
                            trail_floor = round(max_seen_bid - trail_delta, 4)
                            if best_b <= trail_floor and tte_rem >= 25.0 and best_b >= (entry_px + _min_ratchet_gain):
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

                        # FINAL-45S & PRE-EXPIRY 99c CAPITAL RECYCLER (Gemini #6: instant pre-rollover collateral reuse at >=$0.985):
                        pre_expiry_99c_recycle = bool(
                            8.0 <= tte_rem <= 25.0 and rem_shrs >= 5.0 and best_b >= 0.985 and best_b > (entry_px + 0.02)
                        )
                        final_45s_triggered = False
                        _d1_bid_harvest = False
                        _partner_bid_harvested = False
                        if _is_dom_box:
                            pre_expiry_otm_salvage = False
                            spot_crash_triggered = False
                            opposite_salvage_triggered = False
                            trailing_ratchet_triggered = False
                            _box_unit = float(pos.get("box_cost_net") or 0.975)
                            _box_tot_cost = float(pos.get("box_total_cost_usd", 999.0) or 999.0)
                            _p_closed = pos.get("_closed_partner_leg")
                            _p_live = self.active_positions.get(str(pos.get("box_partner_trade_id") or ""))
                            _partner_cov = bool(
                                (isinstance(_p_closed, dict) and float(_p_closed.get("payout_usd", 0.0) or 0.0) >= _box_tot_cost)
                                or (
                                    isinstance(_p_live, dict)
                                    and float(_p_live.get("remaining_shares", 1.0) or 0.0) <= 0.01
                                    and max(float(_p_live.get("confirmed_realized_cash", 0.0) or 0.0), float(_p_live.get("realized_exit_cash", 0.0) or 0.0)) >= _box_tot_cost
                                )
                            )
                            _partner_bid_harvested = bool(
                                (isinstance(_p_closed, dict) and "BOX_EARLY_BID_HARVEST" in str(_p_closed.get("close_reason") or ""))
                                or (
                                    isinstance(_p_live, dict)
                                    and float(_p_live.get("remaining_shares", 1.0) or 0.0) <= 0.01
                                    and "BOX_EARLY_BID_HARVEST" in str(_p_live.get("pending_settlement_close_reason") or _p_live.get("close_reason") or "")
                                )
                            )
                            _harv_target_shrs = rem_shrs
                            _leg1_net_cash = 0.0
                            if isinstance(_p_closed, dict) and "BOX_EARLY_BID_HARVEST" in str(_p_closed.get("close_reason") or ""):
                                _leg1_net_cash = float(_p_closed.get("payout_usd", 0.0) or 0.0) - float(_p_closed.get("exit_fee_usd", 0.0) or 0.0)
                            elif isinstance(_p_live, dict):
                                _p_rem = float(_p_live.get("remaining_shares", rem_shrs) or 0.0)
                                _p_cash = max(float(_p_live.get("confirmed_realized_cash", 0.0) or 0.0), float(_p_live.get("realized_exit_cash", 0.0) or 0.0)) - float(_p_live.get("realized_exit_fee", 0.0) or 0.0)
                                if _partner_bid_harvested:
                                    _leg1_net_cash = _p_cash
                                elif (
                                    rem_shrs - _p_rem >= 5.0
                                    and float(_p_live.get("filled_exit_shares", 0.0) or 0.0) >= 5.0
                                    and (
                                        "BOX_EARLY_BID_HARVEST" in str(_p_live.get("unwind_reason") or _p_live.get("pending_unwind_tag") or "")
                                        or _p_live.get("exit_order_status") in PARTIAL_UNWIND_RESIDUAL_STATUSES
                                    )
                                ):
                                    _partner_bid_harvested = True
                                    _harv_target_shrs = round(rem_shrs - _p_rem, 2)
                                    _leg1_net_cash = _p_cash
                            _pos_fr = self._exit_taker_fee_rate(pos)
                            _pos_fe = float(pos.get("fee_exponent_applied", 1.0) or 1.0)
                            _net_b = best_b - (_pos_fr * ((best_b * (1.0 - best_b)) ** _pos_fe) if _pos_fr > 0.0 else 0.0)
                            _be_gross_px = 0.02
                            if _partner_bid_harvested and _harv_target_shrs >= 5.0:
                                _ent_sh_tot = max(_harv_target_shrs, float(pos.get("entry_shares") or _harv_target_shrs))
                                _scaled_box_cost = (_box_tot_cost * (_harv_target_shrs / _ent_sh_tot)) if _box_tot_cost < 900.0 else (_box_unit * _harv_target_shrs)
                                _req_net_ps = max(0.02, (_scaled_box_cost - _leg1_net_cash - 0.02) / max(_harv_target_shrs, 1e-6))
                                _g_est = _req_net_ps
                                for _ in range(2):
                                    _g_cl = max(0.01, min(0.99, _g_est))
                                    _g_est = _req_net_ps + (_pos_fr * ((_g_cl * (1.0 - _g_cl)) ** _pos_fe) if _pos_fr > 0.0 else 0.0)
                                _be_gross_px = max(0.02, min(0.99, math.ceil(_g_est * 100.0 - 1e-9) / 100.0))
                            if _harv_target_shrs >= 5.0 and best_b >= _be_gross_px and _partner_bid_harvested:
                                _d1_bid_harvest = True
                            elif (
                                tte_rem > 45.0
                                and rem_shrs >= 5.0
                                and best_b >= 0.05
                                and isinstance(_p_live, dict)
                                and not pos.get("is_liquidating")
                                and not _p_live.get("is_liquidating")
                                and _p_live.get("exit_order_status") not in ({"STOP_CANCEL_PENDING", "UNWIND_RETRY_REQUIRED"} | PARTIAL_UNWIND_RESIDUAL_STATUSES)
                                and _p_live.get("pending_unwind_tag") != "BOX_EARLY_BID_HARVEST_UNWIND"
                                and (self.dry_run or (pos.get("inventory_reconciled") and _p_live.get("inventory_reconciled")))
                                and abs(rem_shrs - float(_p_live.get("remaining_shares") or 0.0)) <= 0.02
                            ):
                                _b1_sh = sum(float(b.get("size", 0.0) if isinstance(b, dict) else b[1]) for b in bids if abs(float(b.get("price", 0.0) if isinstance(b, dict) else b[0]) - best_b) < 1e-6)
                                if _b1_sh >= rem_shrs * 1.25:
                                    _pbk = self._get_verified_shm_book(_p_live)
                                    if _pbk is None and hasattr(self.executor, "get_market_book") and (self.dry_run or now_ts - float(pos.get("_pb_ts", 0.0)) >= 3.0):
                                        pos["_pb_ts"] = now_ts
                                        _pbk = await asyncio.to_thread(self.executor.get_market_book, str(_p_live.get("token_id") or ""))
                                    _pbids = (_pbk or {}).get("bids") or []
                                    _pbb = max((float(b.get("price", 0.0) if isinstance(b, dict) else b[0]) for b in _pbids if float(b.get("size", 0.0) if isinstance(b, dict) else b[1]) > 0), default=0.0)
                                    _pb1_sh = sum(float(b.get("size", 0.0) if isinstance(b, dict) else b[1]) for b in _pbids if abs(float(b.get("price", 0.0) if isinstance(b, dict) else b[0]) - _pbb) < 1e-6)
                                    _pfr = self._exit_taker_fee_rate(_p_live)
                                    _pfe = float(_p_live.get("fee_exponent_applied", _pos_fe) or 1.0)
                                    _pnet_b = _pbb - (_pfr * ((_pbb * (1.0 - _pbb)) ** _pfe) if _pfr > 0.0 else 0.0)
                                    _corridor_harvest_ok = (
                                        str(pos.get("box_type") or "") in {"COMPLETE_SET", "NEGRISK_2LEG", "NEGRISK_CROSS"}
                                        or tte_rem > 3600.0
                                        or (_net_b + _pnet_b) >= max(1.080, _box_unit + 0.080)
                                    )
                                    if _pbb >= 0.05 and _pb1_sh >= rem_shrs * 1.25 and (_net_b + _pnet_b) >= max(1.008, _box_unit + 0.015) and _corridor_harvest_ok:
                                        _d1_bid_harvest = True
                            if _unhedged_sc and (expiry_ts - 300.0) <= now_ts <= (expiry_ts + 300.0) and rem_shrs >= 1.0 and best_b >= 0.25:
                                _d1_bid_harvest = True
                            if retry_due and pos.get("pending_unwind_tag") == "BOX_EARLY_BID_HARVEST_UNWIND" and not _d1_bid_harvest and not exit_oid:
                                retry_due = False
                                pos.pop("pending_unwind_tag", None)
                                pos["is_liquidating"] = False
                                pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED" if tte_rem > 45.0 else "DETERMINISTIC_TERMINAL_HOLD"
                                self.save_state()
                                continue
                            _k_lo = float(pos.get("box_k_low") or 0.0)
                            _k_hi = float(pos.get("box_k_high") or 0.0)
                            _outside_corr = bool(
                                spot_valid
                                and _k_hi >= _k_lo > 0.0
                                and (current_spot < _k_lo * (1.0 - 0.0012) or current_spot > _k_hi * (1.0 + 0.0012))
                            )
                            _d1_prim = bool(
                                not pos.get("hold_to_maturity_lock")
                                and rem_shrs >= 5.0
                                and _net_b >= (_box_unit + 0.002)
                                and (
                                    (5.0 <= tte_rem <= 35.0 and best_b >= 0.99)
                                    or (5.0 <= tte_rem <= 65.0 and best_b >= 0.985 and _outside_corr)
                                )
                            )
                            _d1_bonus = bool(5.0 <= tte_rem <= 35.0 and rem_shrs >= 5.0 and _partner_cov and best_b >= 0.20)
                            pre_expiry_99c_recycle = _d1_prim
                            final_45s_triggered = bool(_d1_prim or _d1_bonus or _d1_bid_harvest)
                        elif pre_expiry_99c_recycle or (
                            self._effective_exit_policy() != "hold_98"
                            and not getattr(self, "hold_to_maturity", False)
                            and pos.get("sleeve") != "SLEEVE_4_BOUNDARY_SNIPE" and tte_rem <= 45.0 and rem_shrs > 0.01 and best_b >= 0.85 and best_b > (entry_px + 0.03)
                        ):
                            final_45s_triggered = True

                        # Correction 3: Handle Zero-Bid / Empty Book with Persistence Confirmation & Expiry Exemption
                        if (not bids or best_b <= 0.0) and not pos.get("is_liquidating"):
                            if tte_rem <= 30.0 or _is_dom_box:
                                pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
                                continue
                            zero_bid_start = pos.get("zero_bid_detected_ts")
                            if zero_bid_start is None:
                                pos["zero_bid_detected_ts"] = now_ts
                                continue
                            if (now_ts - float(zero_bid_start)) < max(1.5, float(self.low_bid_persistence_seconds)):
                                continue
                            if pos.get("status") != "LIQUIDITY_CRISIS":
                                pos["status"] = "LIQUIDITY_CRISIS"
                                pos["exit_order_status"] = "LIQUIDITY_CRISIS"
                                pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
                                pos["liquidity_crisis_ts"] = now_ts
                                _ex_sup = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("exit_supervisor", {})
                                _req_mkts = int(_ex_sup.get("global_zero_bid_halt_min_markets", _ex_sup.get("min_markets_for_global_liquidity_halt", 2)))
                                _lc_mkts = {
                                    str(p_lc.get("market_id") or k_lc)
                                    for k_lc, p_lc in self.active_positions.items()
                                    if p_lc.get("status") == "LIQUIDITY_CRISIS"
                                    and (float(p_lc.get("candle_expiry_ts", 0.0) or 0.0) - now_ts) > 120.0
                                }
                                if not bool(_ex_sup.get("isolate_single_market_zero_bid", True)) or len(_lc_mkts) >= _req_mkts:
                                    logger.critical(f"[LIQUIDITY_CRISIS_GLOBAL] {len(_lc_mkts)} markets zero-bid (>120s TTE). Suspending new entries.")
                                    self.risk_halt = True
                                    self._refresh_global_halt()
                                else:
                                    logger.warning(f"[ZERO_BID_ISOLATED] {tid} ({token_id}) zero-bid; isolated to DETERMINISTIC_TERMINAL_HOLD without global halt.")
                            continue
                        else:
                            pos.pop("zero_bid_detected_ts", None)

                        # Handle in-flight passive maker stop unwind (3.0s maker window)
                        if pos.get("exit_order_status") == "PASSIVE_STOP_RESTING":
                            elapsed_passive = now_ts - float(pos.get("passive_stop_start_ts", now_ts))
                            passive_window_s = 3.0
                            if spot_crash_triggered or strike_retrace_triggered or elapsed_passive >= passive_window_s:
                                reason_str = (
                                    "Strike-retrace stop" if strike_retrace_triggered
                                    else "Spot structural crash" if spot_crash_triggered
                                    else f"3.0s passive window expired ({elapsed_passive:.1f}s)"
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
                                        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.02:
                                            self._close_position(tid, pos, ExecutionStatus.FILLED, "PASSIVE_STOP_MAKER_FILLED", won=None)
                                continue

                        clob_sl_triggered = False

                        if is_pre_expiry_window and (in_pin_risk_band or terminal_hold_forced or not spot_valid or not sigma_valid) and not strike_retrace_triggered and not spot_crash_triggered and not opposite_salvage_triggered and not trailing_ratchet_triggered and not final_45s_triggered:
                            if (
                                not pos.get("is_legged_out_residual")
                                and pos.get("active_unwind_trigger_kind") not in {"BOX_HARVEST", "PROFIT_RATCHET", "PRE_EXPIRY_99C", "FINAL_45S"}
                                and pos.get("exit_order_status") not in ({"STOP_CANCEL_PENDING"} | PARTIAL_UNWIND_RESIDUAL_STATUSES)
                            ):
                                retry_due = False
                                pos["is_liquidating"] = False
                            pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD_FINAL" if tte_rem < self.tte_cancel_window else "DETERMINISTIC_TERMINAL_HOLD"

                        if tte_rem <= 0.0 and not (_unhedged_sc and now_ts <= expiry_ts + 300.0) and (retry_due or opposite_salvage_triggered or strike_retrace_triggered or spot_crash_triggered or pre_expiry_otm_salvage or trailing_ratchet_triggered or final_45s_triggered):
                            pos["is_liquidating"] = False
                            pos["exit_order_status"] = "DETERMINISTIC_TERMINAL_HOLD"
                            pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD_FINAL"
                            pos["next_unwind_retry_ts"] = 0.0
                            self.save_state()
                            continue

                        _unwind_backoff_active = (
                            pos.get("exit_order_status") == "TERMINAL_UNWIND_FAILED_SUPERVISED"
                            or (
                                pos.get("exit_order_status") in ({"UNWIND_RETRY_REQUIRED"} | PARTIAL_UNWIND_RESIDUAL_STATUSES)
                                and not retry_due
                                and not spot_crash_triggered
                                and tte_rem > 10.0
                            )
                        )
                        if not _unwind_backoff_active and (
                            retry_due
                            or opposite_salvage_triggered
                            or strike_retrace_triggered
                            or spot_crash_triggered
                            or pre_expiry_otm_salvage
                            or trailing_ratchet_triggered
                            or final_45s_triggered
                        ):
                            _prev_uw_kind = str(pos.get("active_unwind_trigger_kind") or "")
                            _any_fresh_trig = bool(
                                _d1_bid_harvest
                                or final_45s_triggered
                                or trailing_ratchet_triggered
                                or opposite_salvage_triggered
                                or strike_retrace_triggered
                                or spot_crash_triggered
                                or pre_expiry_otm_salvage
                            )
                            if (
                                retry_due
                                and not _any_fresh_trig
                                and pos.get("exit_order_status") not in {"STOP_CANCEL_PENDING", "PASSIVE_STOP_RESTING"}
                                and _prev_uw_kind in {"PROFIT_RATCHET", "PRE_EXPIRY_99C"}
                                and not _is_dom_box
                            ):
                                _last_rf = float(pos.get("_last_ratchet_floor", 0.0) or 0.0)
                                _recovered_above_ratchet = (_prev_uw_kind == "PROFIT_RATCHET" and _last_rf > 0.0 and best_b > _last_rf + 0.005)
                                _dipped_99c_no_salvage = (_prev_uw_kind == "PRE_EXPIRY_99C" and best_b < 0.98)
                                if _recovered_above_ratchet or _dipped_99c_no_salvage:
                                    pos["is_liquidating"] = False
                                    pos.pop("active_unwind_trigger_kind", None)
                                    pos.pop("pending_unwind_tag", None)
                                    if not exit_oid and "saved_tp_exit_price" in pos:
                                        pos["target_exit_price"] = float(pos.pop("saved_tp_exit_price"))
                                    pos["exit_order_status"] = (
                                        "RESTING"
                                        if exit_oid
                                        else ("EXIT_RECOVERY_REQUIRED" if tte_rem >= eff_cancel_win else "DETERMINISTIC_TERMINAL_HOLD")
                                    )
                                    self.save_state()
                                    logger.info(
                                        f"[UNWIND RETRY ABORTED -> RESTORE TP] {tid}: prior {_prev_uw_kind} condition cleared "
                                        f"(best_b=${best_b:.4f}, floor=${_last_rf:.4f}, TTE={tte_rem:.0f}s); restoring {pos['exit_order_status']}."
                                    )
                                    continue

                            if _d1_bid_harvest:
                                pos["active_unwind_trigger_kind"] = "BOX_HARVEST"
                            elif pre_expiry_99c_recycle or final_45s_triggered:
                                pos["active_unwind_trigger_kind"] = "PRE_EXPIRY_99C" if pre_expiry_99c_recycle else "FINAL_45S"
                            elif trailing_ratchet_triggered:
                                pos["active_unwind_trigger_kind"] = "PROFIT_RATCHET"
                                pos["_last_ratchet_floor"] = float(trail_floor)
                            elif opposite_salvage_triggered or strike_retrace_triggered or spot_crash_triggered or pre_expiry_otm_salvage:
                                pos["active_unwind_trigger_kind"] = "ADVERSE_SALVAGE"
                            _cur_uw_kind = str(pos.get("active_unwind_trigger_kind") or _prev_uw_kind)
                            _is_profit_or_recycle_uw = bool(
                                _d1_bid_harvest
                                or final_45s_triggered
                                or trailing_ratchet_triggered
                                or _cur_uw_kind in {"BOX_HARVEST", "PRE_EXPIRY_99C", "FINAL_45S", "PROFIT_RATCHET"}
                            )
                            reason = (
                                f"Box combined-bid overround harvest (TTE={tte_rem:.0f}s, bid ${best_b:.4f})" if _d1_bid_harvest
                                else f"Final-45s capital recycle (TTE={tte_rem:.0f}s <= 45s, bid ${best_b:.4f} >= 0.88, recycling USDC before rollover)" if final_45s_triggered
                                else f"High-Zone MFE profit-lock ratchet (peak bid ${max_seen_bid:.4f} >= ${_hz_arm:.2f} armed floor ${trail_floor:.4f}, current bid ${best_b:.4f} <= floor for >={_hz_hold_s:.1f}s, locking {best_b - entry_px:+.2f}/share)" if _hz_mfe_triggered
                                else f"Trailing profit ratchet (peak bid ${max_seen_bid:.4f} armed trail floor ${trail_floor:.4f}, current bid ${best_b:.4f} <= trail floor for >=4.0s, locking in +{best_b - entry_px:+.2f}/share)" if trailing_ratchet_triggered
                                else f"3-Zone opposite-side structural breakout salvage (wrong-side {wrong_side_pct:+.2f}%, TTE={tte_rem:.0f}s, bid=${best_b:.4f})" if opposite_salvage_triggered
                                else f"Strike-retrace stop (signed cushion {signed_cushion_pct:+.4f}% <= retrace floor for >=10s, TTE={tte_rem:.0f}s, bid=${best_b:.4f})" if strike_retrace_triggered
                                else f"Hard bid-drop stop (bid ${best_b:.4f} <= entry ${entry_px:.4f} - {max_bid_drop:.2f} for >=6s, TTE={tte_rem:.0f}s)" if spot_crash_triggered
                                else f"Scheduled Unwind Retry ({_cur_uw_kind or 'STOP_LOSS'})" if retry_due
                                else f"Pre-expiry OTM salvage (TTE={tte_rem:.0f}s, spot={current_spot:.2f} vs open={open_spot:.2f})" if pre_expiry_otm_salvage
                                else f"Spot structural breakdown (candle_disp={spot_disp:.2f}, entry_disp={entry_spot_disp:.2f}, move={spot_move_pct*100:.2f}%)"
                            )
                            logger.warning(f"[SALVAGE ACTIVATED] Position {tid}: {reason}. Unwinding position immediately...")
                            if not self.dry_run and not _is_profit_or_recycle_uw:
                                send_operational_alert(
                                    "WRONG_SIDE_SALVAGE_EXIT",
                                    f"Position {tid}: {reason}",
                                    "WARNING",
                                    dedupe_key=f"salvage:{tid}",
                                )
                            pos["stop_triggered_ts"] = now_ts
                            pos.pop("exit_tranches", None)
                            _uw_tag = (
                                "D1_LEGGED_OUT_RESIDUAL_UNWIND" if pos.get("is_legged_out_residual")
                                else "BOX_EARLY_BID_HARVEST_UNWIND" if _d1_bid_harvest
                                else "FINAL_45S_CAPITAL_RECYCLE_UNWIND" if final_45s_triggered
                                else "TRAILING_PROFIT_RATCHET_UNWIND" if (trailing_ratchet_triggered or _cur_uw_kind == "PROFIT_RATCHET")
                                else "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE" if opposite_salvage_triggered
                                else "STRIKE_RETRACE_SALVAGE" if strike_retrace_triggered
                                else "HARD_BID_DROP_SALVAGE" if spot_crash_triggered
                                else "PRE_EXPIRY_OTM_SALVAGE" if pre_expiry_otm_salvage
                                else pos.get("pending_unwind_tag") or "ADVERSE_STOP_LOSS_UNWIND"
                            )
                            pos["pending_unwind_tag"] = _uw_tag

                            # Cancel any resting maker order with VERIFIED terminal status before selling
                            if exit_oid:
                                prior_filled = float(pos.get("filled_exit_shares", 0.0) or 0.0)
                                cancel_res = await asyncio.to_thread(self.executor.cancel_order, exit_oid)
                                summary = await asyncio.to_thread(self.executor.get_order_fill_summary, exit_oid, token_id)
                                if summary is not None:
                                    self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False)
                                if float(pos.get("remaining_shares", rem_shrs) or 0.0) <= 0.02:
                                    logger.info(f"✓ [STOP-LOSS RECONCILED] {tid} already fully matched on resting exit before unwind.")
                                    self._close_position(tid, pos, ExecutionStatus.SETTLED, "MAKER_SCALP_FILLED_CLOB", won=None)
                                    continue
                                _new_exit_m = max(
                                    float(summary.get("matched", 0.0) or 0.0) if isinstance(summary, dict) else 0.0,
                                    float(cancel_res.get("matched", 0.0) or 0.0) if isinstance(cancel_res, dict) else 0.0,
                                )
                                if _new_exit_m > prior_filled + 1e-4:
                                    pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                                    pos["pending_canceled_order_id"] = exit_oid
                                    self.save_state()
                                    continue
                                if isinstance(cancel_res, dict) and bool(cancel_res.get("is_canceled")):
                                    # v3.9.5 Forensic Fix: cancel_order already verified CLOB cancel_orders ack +
                                    # zero unrecorded fills (line 7753). Evict exit_oid immediately even if the
                                    # get_order read-replica lags by ~300-600ms with stale status=LIVE.
                                    open_oids.discard(exit_oid)
                                canceled_confirmed = (
                                    (self.dry_run and (exit_oid not in open_oids or summary is None))
                                    or (exit_oid not in open_oids and (
                                        (summary is not None and summary["terminal"])
                                        or (isinstance(cancel_res, dict) and (
                                            exit_oid in (cancel_res.get("canceled") or [])
                                            or bool(cancel_res.get("is_canceled"))
                                        ))
                                    ))
                                )
                                if not canceled_confirmed:
                                    pos["exit_order_status"] = "STOP_CANCEL_PENDING"
                                    pos["cancel_pending_order_id"] = exit_oid
                                    pos["pending_unwind_tag"] = _uw_tag
                                    self.save_state()
                                    continue
                                self.executor.release_inventory(reservation_id=exit_oid)
                                _c_oids_hist = pos.setdefault("canceled_maker_exit_oids", [])
                                if str(exit_oid) not in _c_oids_hist:
                                    _c_oids_hist.append(str(exit_oid))
                                    if len(_c_oids_hist) > 16:
                                        del _c_oids_hist[:-16]
                                pos["exit_order_id"] = None
                                exit_oid = None
                                if "saved_tp_exit_price" in pos:
                                    pos["target_exit_price"] = float(pos.pop("saved_tp_exit_price"))
                            pos.pop("low_bid_detected_ts", None)
                            pos.pop("strike_retrace_detected_ts", None)
                            pos.pop("trail_stop_detected_ts", None)
                            pos.pop("trailing_ratchet_detected_ts", None)
                            pos["exit_order_status"] = "CANCELED_FOR_STOP_LOSS"

                            # Two-Stage 3.0s Passive Midpoint Maker Unwind (Pillar 3, Non-Blocking via PASSIVE_STOP_RESTING;
                            # bypassed on confirmed EV salvage, High-Zone MFE ratchet, fast crashes, or TTE <= 120s)
                            is_salvage_or_ratchet = bool(
                                trailing_ratchet_triggered
                                and not _hz_mfe_triggered
                                and not opposite_salvage_triggered
                                and not pre_expiry_otm_salvage
                                and v_spot_15s_pct > -0.05
                            )
                            if (
                                is_salvage_or_ratchet
                                and tte_rem > 120.0
                                and book_spread >= 0.04
                                and rem_shrs >= 5.0
                                and not pos.get("passive_3s_attempted")
                                and not self.dry_run
                                and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
                            ):
                                pos["passive_3s_attempted"] = True
                                maker_unwind_px = round(min(best_a - 0.01, best_b + max(0.01, 0.40 * book_spread)), 2)
                                logger.info(
                                    f"[TWO-STAGE MAKER UNWIND] Posting 3.0s non-blocking passive maker sell for {tid}: "
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
                                    pos.setdefault("saved_tp_exit_price", float(pos.get("target_exit_price") or 0.98))
                                    pos["exit_order_id"] = m_oid
                                    pos["target_exit_price"] = maker_unwind_px
                                    pos["exit_order_status"] = "PASSIVE_STOP_RESTING"
                                    pos["passive_stop_start_ts"] = now_ts
                                    self.save_state()
                                    continue
                                elif isinstance(m_res, dict) and m_res.get("outcome_unknown"):
                                    m_oid = m_res.get("orderID")
                                    if m_oid:
                                        pos["exit_order_id"] = m_oid
                                        pos["exit_order_size"] = float(rem_shrs)
                                    if m_res.get("reservation_id"):
                                        pos.setdefault("pending_reservation_ids", []).append(m_res["reservation_id"])
                                    pos["target_exit_price"] = maker_unwind_px
                                    pos["exit_post_attempt_ts"] = now_ts
                                    pos["exit_order_status"] = "EXIT_POST_OUTCOME_UNKNOWN"
                                    self.save_state()
                                    logger.critical(
                                        f"[TWO-STAGE MAKER UNWIND] Ambiguous passive maker post for {tid} (OID: {m_oid}); "
                                        "holding reservation and deferring FAK unwind until reconciled."
                                    )
                                    continue

                            rem_shrs = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", rem_shrs)) or 0.0)
                            if rem_shrs <= 0.02:
                                self._close_position(tid, pos, ExecutionStatus.SETTLED, "MAKER_SCALP_FILLED_CLOB", won=None)
                                continue

                            # Refresh best_b from /dev/shm fast-tick after cancel RTT so FAK min_price isn't stale
                            if _is_live_auth:
                                _post_cancel_bk = self._get_verified_shm_book(pos)
                                if isinstance(_post_cancel_bk, dict):
                                    _pc_bids = _post_cancel_bk.get("bids") or []
                                    _pc_best = max((float(b.get("price", 0.0)) for b in _pc_bids if float(b.get("size", 0.0)) > 0), default=0.0)
                                    if _pc_best > 0.0:
                                        best_b = _pc_best

                            # Aggressive FAK unwind at best bid (min price 0.01) to lock in capital recovery.
                            # v3.9.3 Forensic Fix: Use 4c (+4c/retry) sweep floor on live adverse salvage so 1-2c L1
                            # flickers don't cause 400 FAK zero-match rejections (CLOB FAK still fills at top resting bid).
                            _prior_retries = int(pos.get("unwind_retry_count", 0) or 0)
                            _unwind_sz = rem_shrs
                            if _is_dom_box and _d1_bid_harvest:
                                _unwind_sz = min(rem_shrs, _harv_target_shrs) if _partner_bid_harvested else rem_shrs
                                limit_px = (
                                    max(0.25, round(best_b - 0.03, 2)) if _unhedged_sc
                                    else max(_be_gross_px if _partner_bid_harvested else 0.02, round(best_b - (0.02 if _partner_bid_harvested else 0.0), 4))
                                )
                            elif _is_dom_box and not _d1_bonus:
                                limit_px = 0.98
                            elif final_45s_triggered or _cur_uw_kind == "PRE_EXPIRY_99C":
                                limit_px = (
                                    max(0.98, round(math.floor((best_b + 1e-9) * 1000.0) / 1000.0, 3))
                                    if (pre_expiry_99c_recycle or _cur_uw_kind == "PRE_EXPIRY_99C")
                                    else max(0.01, round(best_b - 0.01, 4))
                                )
                            elif _cur_uw_kind == "PROFIT_RATCHET":
                                limit_px = max(0.01, round(best_b - min(0.04, 0.02 + 0.01 * min(_prior_retries, 2)), 4))
                            elif (_is_live_auth and not trailing_ratchet_triggered) or _prior_retries > 0:
                                _fak_slip = 0.04 + (0.04 * min(_prior_retries, 4))
                                _tk_uw_c = (getattr(self.executor, "_tick_size_cache", None) or {}).get(str(token_id))
                                _uw_floor_px = (
                                    0.001
                                    if (best_b < 0.02 or (_tk_uw_c is not None and float(_tk_uw_c) <= 0.001 + 1e-9))
                                    else 0.01
                                )
                                limit_px = max(_uw_floor_px, round(best_b - _fak_slip, 4))
                            else:
                                _uw_floor_px = 0.001 if best_b < 0.02 else 0.01
                                limit_px = max(_uw_floor_px, round(best_b - 0.02, 4))
                            if isinstance(getattr(self.executor, "_fee_cache", None), dict) and str(token_id) not in self.executor._fee_cache:
                                self.executor._fee_cache[str(token_id)] = (
                                    self._exit_taker_fee_rate(pos),
                                    float(pos.get("fee_exponent_applied", pos.get("fee_exponent", 1.0)) or 1.0),
                                )
                            unwind_res = await asyncio.to_thread(
                                self.executor.execute_unwind_order,
                                token_id=token_id,
                                size=_unwind_sz,
                                side="SELL",
                                min_price=limit_px,
                            )
                            pos.pop("pending_unwind_tag", None)
                            outcome = self._handle_unwind_response(
                                tid, pos, unwind_res, _unwind_sz,
                                _uw_tag, "PARTIAL_UNWIND_REMAINING", limit_px,
                            )
                            if outcome != "FAILED":
                                self.executor.invalidate_collateral_cache()
                                self._pending_collateral_refresh = True
                                self.save_state()
                                continue
                            pos["pending_unwind_tag"] = _uw_tag

                            unwind_res = unwind_res or {}
                            logger.error(f"Immediate FAK unwind failed for {tid}: {unwind_res.get('error')}. Verifying inventory...")
                            _settling_buy = (
                                not pos.get("inventory_reconciled")
                                and (now_ts - float(pos.get("entry_ts") or now_ts)) < 18.0
                                and "sell_inventory_reconciliation_required" in str(unwind_res.get("error", "")).lower()
                            )
                            if not self.dry_run and token_id:
                                bal, src = await asyncio.to_thread(self._wallet_token_balance, token_id)
                                eps = self.executor.calculate_balance_epsilon(0.001)
                                if bal is not None and bal >= rem_shrs - 0.05:
                                    pos["inventory_reconciled"] = True
                                is_balance_shortfall = "not enough balance" in str(unwind_res.get("error", "")).lower()
                                # Round 10 P0-03: a zero/dust wallet balance (even with a balance-shortfall
                                # rejection) proves only absence of inventory, never sale proceeds. It must be
                                # reconciled from exchange fill history, never synthetically settled.
                                if not _settling_buy and bal is not None and (
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

                            # Retain position under bounded escalation retry policy (or supervised hold if <5.0 CLOB lot minimum)
                            err_u_low = str(unwind_res.get("error", "") or "").lower()
                            if (
                                bool(unwind_res.get("market_closed"))
                                or is_market_closed_or_disabled_error(resp=unwind_res)
                                or (tte_rem <= 5.0 and "trading is disabled" in err_u_low)
                                or any(k in err_u_low for k in ("market is closed", "orderbook does not exist", "no orderbook exists"))
                            ):
                                pos["is_liquidating"] = False
                                pos["exit_order_status"] = "DETERMINISTIC_TERMINAL_HOLD"
                                pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD_FINAL"
                                pos["next_unwind_retry_ts"] = 0.0
                                self.save_state()
                                continue
                            if rem_shrs < 5.0 and any(k in err_u_low for k in ("minimum", "min size", "invalid amounts", "size too small")):
                                pos["is_liquidating"] = False
                                pos["exit_order_status"] = "SUB_MINIMUM_LOT_SUPERVISED_HOLD"
                                pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
                                self.save_state()
                                continue
                            pos["is_liquidating"] = False
                            if _is_dom_box and not _d1_bonus and not _partner_bid_harvested and not _unhedged_sc:
                                pos.pop("pending_unwind_tag", None)
                                pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED" if (_d1_bid_harvest and tte_rem > 45.0) else "DETERMINISTIC_TERMINAL_HOLD"
                                pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"
                                self.save_state()
                                continue
                            if _settling_buy:
                                attempts = int(pos.get("unwind_retry_count", 0))
                                backoff_seconds = 0.50
                            else:
                                attempts = int(pos.get("unwind_retry_count", 0)) + 1
                                pos["unwind_retry_count"] = attempts
                                if "no orders found to match with fak order" in err_u_low:
                                    # Retry rapidly on the first 3 empty-match checks, then back off exponentially
                                    # so thin sub-cent / event books do not exhaust all 10 retries in 3.5 seconds!
                                    backoff_seconds = 0.35 if attempts <= 3 else min(30.0, 2.0 ** min(attempts - 2, 5))
                                else:
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
                        remaining_vol_pre = candle_sigma * math.sqrt(max(tte_rem, 1.0) / _candle_denom_s) if (math.isfinite(candle_sigma) and candle_sigma > 0) else 0.0
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

                            remaining_vol = candle_sigma * math.sqrt(max(tte_rem, 1.0) / _candle_denom_s)
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
                                if isinstance(getattr(self.executor, "_fee_cache", None), dict) and str(token_id) not in self.executor._fee_cache:
                                    self.executor._fee_cache[str(token_id)] = (
                                        self._exit_taker_fee_rate(pos),
                                        float(pos.get("fee_exponent_applied", pos.get("fee_exponent", 1.0)) or 1.0),
                                    )
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
                        pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD_FINAL" if tte_rem < self.tte_cancel_window else "DETERMINISTIC_TERMINAL_HOLD"

                    # Phase D: Resting maker exit fill verification (exchange trade-level accounting)
                    if exit_oid:
                        summary = await asyncio.to_thread(self.executor.get_order_fill_summary, exit_oid, token_id)
                        if summary is not None:
                            if self._record_order_summary(pos, summary, float(pos.get("target_exit_price", 0.0) or 0.0), taker=False):
                                self.save_state()
                            filled = float(pos.get("filled_exit_shares", 0.0) or 0.0)
                            if filled > 0:
                                pos["average_exit_price"] = round(float(pos.get("realized_exit_cash", 0.0)) / filled, 4)
                            if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.02:
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
                                    if tte_rem >= self.tte_cancel_window and position_may_post_new_maker_exit(pos):
                                        await asyncio.to_thread(self._attempt_maker_exit_post, tid, pos)
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

    async def _drain_and_dispatch_shock_triggers(
        self,
        trigger_fp: Optional[Any] = None,
        wakeup_supervision_event: Optional[asyncio.Event] = None,
    ) -> int:
        if self._shutdown_requested:
            return 0
        if not self.dry_run and not self.executor.is_heartbeat_healthy():
            if not self.risk_controller.is_halted():
                self.risk_controller.halted = True
                self.risk_controller.halt_reason = (
                    f"Heartbeat degraded ({self.executor.heartbeat_failures} drops) - "
                    "new entries halted; existing positions remain supervised."
                )
            if wakeup_supervision_event is not None:
                wakeup_supervision_event.set()

        fast_lines: List[str] = []
        fast_q = getattr(self, "_fast_trigger_lines", None)
        if fast_q:
            while fast_q:
                fast_lines.append(fast_q.popleft())

        disk_lines: List[str] = []
        if trigger_fp is not None and not getattr(trigger_fp, "closed", True):
            try:
                chunk = trigger_fp.read()
            except Exception as e:
                logger.debug(f"Trigger stream read notice: {e}")
                chunk = b""

            if not chunk and TRIGGER_FILE.exists():
                try:
                    curr_sz = TRIGGER_FILE.stat().st_size
                    if curr_sz < self.last_trigger_file_pos:
                        # File was compacted/truncated in place: resume from EOF instead of re-ingesting the
                        # retained hot tail (old triggers would evict real IDs from seen_shock_ids). IPC covers the gap.
                        trigger_fp.seek(0, 2)
                        self.last_trigger_file_pos = trigger_fp.tell()
                        chunk = b""
                except Exception:
                    pass

            if chunk:
                complete_end = chunk.rfind(b"\n") + 1
                if complete_end:
                    disk_lines = chunk[:complete_end].decode("utf-8", errors="ignore").splitlines()
                    self.last_trigger_file_pos += complete_end
                    if complete_end < len(chunk):
                        trigger_fp.seek(self.last_trigger_file_pos)
                else:
                    disk_lines = []
                    trigger_fp.seek(self.last_trigger_file_pos)

        new_lines = fast_lines + disk_lines
        if not new_lines:
            return 0
        now_u = time.time()
        _dir_open_cnt = sum(
            1
            for p in self.active_positions.values()
            if not p.get("is_dominance_box")
            and "BOX" not in str(p.get("sleeve") or "").upper()
            and not position_is_settlement_receivable(p)
        )
        _eff_slot_cap = self._effective_directional_slot_cap(now_u)
        if (
            len(new_lines) == 1
            and not fast_lines
            and not self.dry_run
            and len(self.allowed_assets) > 1
            and (_eff_slot_cap - _dir_open_cnt) <= 1
            and '"BTC"' not in new_lines[0]
        ):
            _coal_s = (
                float(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("routing", {}).get("microbatch_coalesce_alt_sec", 0.003) or 0.003)
                if self._is_v5_live_strict()
                else 0.0005
            )
            await asyncio.sleep(_coal_s)
            if fast_q:
                while fast_q:
                    new_lines.append(fast_q.popleft())
            if trigger_fp is not None and not getattr(trigger_fp, "closed", True):
                try:
                    chunk_c = trigger_fp.read()
                    if chunk_c:
                        end_c = chunk_c.rfind(b"\n") + 1
                        if end_c:
                            new_lines.extend(chunk_c[:end_c].decode("utf-8", errors="ignore").splitlines())
                            self.last_trigger_file_pos += end_c
                            if end_c < len(chunk_c):
                                trigger_fp.seek(self.last_trigger_file_pos)
                        else:
                            trigger_fp.seek(self.last_trigger_file_pos)
                except Exception:
                    pass

        if self.risk_controller.is_halted() and not self.active_positions:
            return 0

        batch_candidates = []
        batch_seen_ids = set()
        for line in new_lines:
            if not line.strip():
                continue
            try:
                shk = _json_loads(line)
            except Exception as parse_err:
                logger.error(f"Error parsing trigger line: {parse_err}")
                continue
            s_id = shk.get("shock_id") or f"{shk.get('market_id')}_{shk.get('t0_unix')}"
            if s_id in self.seen_shock_ids or s_id in batch_seen_ids:
                continue
            batch_seen_ids.add(s_id)
            batch_candidates.append(shk)

        if not batch_candidates:
            return 0

        self.recent_shock_window = [
            w for w in self.recent_shock_window
            if (now_u - w["t_unix"]) <= 5.0
        ]

        _scores = {id(c): self._calc_priority_score(c) for c in batch_candidates}
        # Rank qualifying candidates descending by 60ms EV*Kelly tournament (+ corridor bonus), 15m/5m ahead on ties
        if len(batch_candidates) > 1 and rank_microbatch_shock_tournament is not None:
            _qual = [c for c in batch_candidates if _scores[id(c)] > 0.0]
            _unq = [c for c in batch_candidates if _scores[id(c)] <= 0.0]
            batch_candidates = (
                rank_microbatch_shock_tournament(_qual, list(self._risk_bearing_positions().values()))
                + _unq
            )
        elif len(batch_candidates) > 1:
            batch_candidates.sort(
                key=lambda c: (_scores[id(c)], 1 if str(c.get("horizon") or "").lower() in ("15m", "5m") else 0),
                reverse=True,
            )

        loop_now = asyncio.get_running_loop()
        dispatched_tasks: List[asyncio.Task] = []
        _bg_shks = self.__dict__.setdefault("_bg_shock_tasks", set())
        _cold_objs = self.__dict__.setdefault("_cold_shock_objs", set())

        def _spawn_shock_eval(shock: Dict[str, Any], is_cold: bool) -> Optional[asyncio.Task]:
            s_id = shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
            if s_id in self.seen_shock_ids:
                return None
            cand_score = _scores[id(shock)]
            shk_m_id = str(shock.get("market_id") or "")
            if cand_score > 0.0 and self.recent_shock_window and _dir_open_cnt >= _eff_slot_cap:
                best_prior = max(self.recent_shock_window, key=lambda x: x["score"])
                if best_prior["market_id"] != shk_m_id and best_prior["score"] > cand_score:
                    logger.info(
                        f"[PRIORITY DEFER] Deferring {shock.get('title')!r} (score={cand_score:.3f}) "
                        f"to concurrent superior qualified trigger {best_prior.get('trade_id')} (score={best_prior['score']:.3f})"
                    )
                    return None
            self.last_event_id = s_id
            self._triggers_scanned_count = getattr(self, "_triggers_scanned_count", 0) + 1
            _shk_oid = id(shock)
            if is_cold:
                _cold_objs.add(_shk_oid)
            _shk_task = asyncio.create_task(self.evaluate_shock_and_execute(shock))
            _bg_shks.add(_shk_task)
            dispatched_tasks.append(_shk_task)
            if not is_cold:
                loop_now.call_soon(self._prewarm_market_metadata, shock)

            def _on_shk_done(_t: asyncio.Task, _m_id: str = shk_m_id, _oid: int = _shk_oid) -> None:
                _bg_shks.discard(_t)
                _cold_objs.discard(_oid)
                if _t.cancelled():
                    return
                _exc = _t.exception()
                if isinstance(_exc, StatePersistenceError):
                    self.risk_controller.halted = True
                    self.risk_controller.halt_reason = "Critical state persistence failure"
                    logger.critical("Critical live state persistence failure; blocking further entries", exc_info=_exc)
                    if wakeup_supervision_event is not None:
                        wakeup_supervision_event.set()
                elif _exc is not None:
                    logger.error(f"[SIGNAL ERROR] Unhandled exception evaluating shock {_m_id}: {_exc}")
                    try:
                        self._refresh_global_halt()
                    except Exception:
                        pass

            _shk_task.add_done_callback(_on_shk_done)
            return _shk_task

        hot_wave = [c for c in batch_candidates if _scores[id(c)] > 0.0]
        cold_wave = [c for c in batch_candidates if _scores[id(c)] <= 0.0]
        hot_spawned = 0
        for shock in hot_wave:
            if _spawn_shock_eval(shock, False) is not None:
                hot_spawned += 1
        if hot_spawned:
            await asyncio.sleep(0)
        cold_spawned = 0
        for shock in cold_wave:
            if _spawn_shock_eval(shock, True) is not None:
                cold_spawned += 1
        if cold_spawned:
            await asyncio.sleep(0)
        return len(dispatched_tasks)

    def _is_riskless_only_mode(self) -> bool:
        return bool(
            not self.dry_run
            and (self._is_v5_live_strict() or getattr(self, "enforce_seed_directional_shadow_gate", False))
            and GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {}).get("riskless_only_mode", False)
        )

    async def _fast_trigger_consumer_loop(
        self,
        fast_shock_event: asyncio.Event,
        trigger_fp: Optional[Any] = None,
        wakeup_supervision_event: Optional[asyncio.Event] = None,
        has_event_driven_wakeup: bool = False,
    ) -> None:
        """Dedicated hot-path shock consumer decoupled from slow position supervision & D1 polling."""
        poll_timeout = 0.25 if has_event_driven_wakeup else 0.010
        try:
            while not self._shutdown_requested:
                fast_shock_event.clear()
                if self._is_riskless_only_mode() and not getattr(self, "_fast_trigger_lines", None):
                    if trigger_fp is not None:
                        try:
                            trigger_fp.seek(0, os.SEEK_END)
                            self.last_trigger_file_pos = trigger_fp.tell()
                        except Exception:
                            pass
                    try:
                        await asyncio.wait_for(fast_shock_event.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass
                    continue
                await self._drain_and_dispatch_shock_triggers(
                    trigger_fp=trigger_fp,
                    wakeup_supervision_event=wakeup_supervision_event,
                )
                if self._shutdown_requested:
                    break
                if getattr(self, "_fast_trigger_lines", None):
                    await asyncio.sleep(0)
                    continue
                try:
                    await asyncio.wait_for(fast_shock_event.wait(), timeout=poll_timeout)
                except asyncio.TimeoutError:
                    pass
        finally:
            if wakeup_supervision_event is not None:
                wakeup_supervision_event.set()

    async def _fast_d1_consumer_loop(
        self,
        fast_d1_event: asyncio.Event,
        wakeup_supervision_event: Optional[asyncio.Event] = None,
    ) -> None:
        """Dedicated hot-path D1/SLL/WS_SNIPE candidate consumer decoupled from check_resolutions_and_manage_positions."""
        try:
            while not self._shutdown_requested:
                fast_d1_event.clear()
                now_d1 = time.time()
                if self._is_d1_box_halted():
                    _fq_clr = getattr(self, "_fast_d1_cand_lines", None)
                    if _fq_clr:
                        _fq_clr.clear()
                elif (
                    bool(getattr(self, "_fast_d1_cand_lines", None))
                    or (now_d1 - getattr(self, "_last_d1_cand_poll", 0.0) >= 0.50)
                ):
                    self._last_d1_cand_poll = now_d1
                    try:
                        if await self._poll_d1_live_box_candidates(now_d1) > 0 and wakeup_supervision_event is not None:
                            wakeup_supervision_event.set()
                    except Exception:
                        logger.exception("[FAST D1 CONSUMER] Candidate poll failed; continuing.")
                if self._shutdown_requested:
                    break
                if not self._is_d1_box_halted() and bool(getattr(self, "_fast_d1_cand_lines", None)):
                    await asyncio.sleep(0)
                    continue
                try:
                    await asyncio.wait_for(fast_d1_event.wait(), timeout=0.25)
                except asyncio.TimeoutError:
                    pass
        finally:
            if wakeup_supervision_event is not None:
                wakeup_supervision_event.set()

    async def run(self):
        if not self.dry_run and _alerts_file_path() is not None:
            _ensure_file_logging()
        logger.info(
            f"[LIVE HARVESTER] Wallet={self.executor.funder_address} | Auth={self.executor.auth_mode} | "
            f"Ticket=${self.ticket_notional:.2f} | Cap=${self.max_exposure:.2f} (slots={self.max_concurrent_positions}) | "
            f"Mode={'DRY-RUN' if self.dry_run else 'LIVE'} | RisklessOnly={self._is_riskless_only_mode()}"
        )

        lock_path = PID_FILE.with_suffix(".lock")
        self._instance_lock_fd = open(lock_path, "a+b")
        if fcntl is not None:
            try:
                fcntl.flock(self._instance_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                self._instance_lock_fd.close()
                raise RuntimeError("Another live harvester instance already holds the lock") from exc
        elif os.name == "nt":
            import msvcrt as _msvcrt
            try:
                self._instance_lock_fd.seek(0, os.SEEK_END)
                if self._instance_lock_fd.tell() == 0:
                    self._instance_lock_fd.write(b"\x00")
                    self._instance_lock_fd.flush()
                self._instance_lock_fd.seek(0)
                _msvcrt.locking(self._instance_lock_fd.fileno(), _msvcrt.LK_NBLCK, 1)
            except OSError as exc:
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
            if not self.dry_run:
                self.save_state()

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

            _default_res = PIPELINE_ROOT / "data/polymarket/finalized_market_resolutions.jsonl"
            _res_file = RESOLUTIONS_FILE if (RESOLUTIONS_FILE.parent == DATA_DIR or RESOLUTIONS_FILE != _default_res) else (DATA_DIR / "finalized_market_resolutions.jsonl")
            if _res_file.exists():
                # Replay pre-existing resolutions first: active positions may have resolved while daemon was down
                self.last_res_file_pos = 0
                await self.check_resolutions_and_manage_positions()
                self.last_res_file_pos = _res_file.stat().st_size
                logger.info(f"Tailing new resolutions from byte offset: {self.last_res_file_pos}")

            # P1: Zero-Polling Fast IPC via Linux inotify file descriptor
            watcher = LinuxInotifyWatcher(TRIGGER_FILE)
            loop = asyncio.get_running_loop()

            # Graceful shutdown: SIGTERM/SIGINT only set a flag; the loop finishes its in-flight step, flushes
            # state atomically and exits 0 (never interrupts a state write or order mutation mid-flight).
            trigger_notify_event = asyncio.Event()
            fast_shock_event = asyncio.Event()
            fast_d1_box_event = asyncio.Event()

            def _request_shutdown(signame: str):
                if not self._shutdown_requested:
                    logger.warning(f"[SHUTDOWN] {signame} received; finishing in-flight step then stopping gracefully.")
                self._shutdown_requested = True
                fast_shock_event.set()
                fast_d1_box_event.set()
                trigger_notify_event.set()

            for _sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(_sig, _request_shutdown, _sig.name)
                except (NotImplementedError, RuntimeError, ValueError):
                    pass
            self._main_loop = loop
            if getattr(self, "_fast_trigger_lines", None) is None:
                from collections import deque as _deque
                self._fast_trigger_lines = _deque(maxlen=512)
            if getattr(self, "_fast_d1_cand_lines", None) is None:
                from collections import deque as _deque
                self._fast_d1_cand_lines = _deque(maxlen=256)

            def on_inotify_file_event():
                watcher.drain_events()
                fast_shock_event.set()

            if watcher.is_available:
                loop.add_reader(watcher.fd, on_inotify_file_event)
                logger.info(f"✓ Linux inotify event listener armed on {TRIGGER_FILE.name} (sub-millisecond wakeups enabled).")
            else:
                logger.info("Linux inotify unavailable; using responsive 10ms consumer polling fallback.")

            ipc_sock = None
            if os.name != "nt":
                try:
                    import socket
                    ipc_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                    ipc_sock.setblocking(False)
                    try:
                        ipc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
                    except Exception:
                        pass
                    ipc_name = os.environ.get(
                        "POLYMARKET_IPC_SOCKET_NAME",
                        "polymarket_shock_notify" if not self.dry_run else f"pm_shock_dry_{os.getpid()}",
                    )
                    ipc_addr = f"\x00{ipc_name}".encode("utf-8")
                    ipc_sock.bind(ipc_addr)

                    def on_fast_ipc_datagram():
                        has_real_trigger = False
                        while True:
                            try:
                                pkt = ipc_sock.recv(65536)
                                if not pkt:
                                    break
                                for ln in pkt.decode("utf-8", errors="ignore").splitlines():
                                    s_ln = ln.strip()
                                    if not s_ln:
                                        continue
                                    if '"_prewarm_clob_tls"' in s_ln:
                                        self._handle_prewarm_ipc_signal()
                                        continue
                                    if self._is_riskless_only_mode():
                                        continue
                                    self._fast_trigger_lines.append(s_ln)
                                    has_real_trigger = True
                            except (BlockingIOError, InterruptedError):
                                break
                            except Exception:
                                break
                        if has_real_trigger:
                            fast_shock_event.set()

                    loop.add_reader(ipc_sock.fileno(), on_fast_ipc_datagram)
                    logger.info("✓ Fast RAM IPC datagram listener armed on @polymarket_shock_notify (~15us zero-VFS delivery).")
                except Exception as ipc_exc:
                    logger.debug(f"Fast IPC datagram setup notice: {ipc_exc}")
                    if ipc_sock is not None:
                        try:
                            ipc_sock.close()
                        except Exception:
                            pass
                        ipc_sock = None

            d1_ipc_sock = None
            if os.name != "nt":
                try:
                    import socket
                    d1_ipc_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                    d1_ipc_sock.setblocking(False)
                    try:
                        d1_ipc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 524288)
                    except Exception:
                        pass
                    d1_ipc_name = os.environ.get(
                        "POLYMARKET_D1_IPC_SOCKET_NAME",
                        "polymarket_d1_box_notify" if not self.dry_run else f"pm_d1_dry_{os.getpid()}",
                    )
                    d1_ipc_sock.bind(f"\x00{d1_ipc_name}".encode("utf-8"))

                    def on_fast_d1_ipc_datagram():
                        while True:
                            try:
                                pkt = d1_ipc_sock.recv(262144)
                                if not pkt:
                                    break
                                for ln in pkt.decode("utf-8", errors="ignore").splitlines():
                                    if ln.strip():
                                        self._fast_d1_cand_lines.append(ln)
                            except (BlockingIOError, InterruptedError):
                                break
                            except Exception:
                                break
                        fast_d1_box_event.set()
                        trigger_notify_event.set()

                    loop.add_reader(d1_ipc_sock.fileno(), on_fast_d1_ipc_datagram)
                    logger.info("✓ Fast D1 Box IPC datagram listener armed on @polymarket_d1_box_notify (~15us wakeup).")
                except Exception as d1_ipc_exc:
                    logger.debug(f"Fast D1 IPC setup notice: {d1_ipc_exc}")
                    if d1_ipc_sock is not None:
                        try:
                            d1_ipc_sock.close()
                        except Exception:
                            pass
                        d1_ipc_sock = None

            last_heartbeat = time.time()
            last_clob_heartbeat = 0.0
            last_mgmt_check = 0.0
            self._triggers_scanned_count = 0
            pos_ws_task = None
            fast_consumer_task = None
            fast_d1_consumer_task = None
            if (
                not self.dry_run
                and _PolymarketClobMarketWsTracker is not None
                and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
                and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                and os.environ.get("PM_ENABLE_HARVESTER_MKT_WS", "1") == "1"
            ):
                def _on_ws_recycle_bid(_tok: str, _bb: float) -> None:
                    self._ws_urgent_recycle_ts = time.time()
                    loop.call_soon_threadsafe(trigger_notify_event.set)

                def _on_ws_book_change(_tok: str, _bk: Dict[str, Any]) -> None:
                    self._notify_sll_ws_book_change(_tok, loop)
                    _asks = (_bk or {}).get("asks") or []
                    if _STAGE_B_DECAY_TRACKER is not None and _tok in _STAGE_B_DECAY_TRACKER._by_token:
                        try:
                            _ba_px = float(_asks[0].get("price") or 0.0) if _asks else None
                            _ba_sz = float(_asks[0].get("size") or 0.0) if _asks else 0.0
                            _STAGE_B_DECAY_TRACKER.on_top_of_book_tick(_tok, _ba_px, _ba_sz)
                        except Exception:
                            pass
                    _bids = (_bk or {}).get("bids") or []
                    if _bids and float(_bids[0].get("price", 0.0) or 0.0) >= 0.52:
                        _top_b_ws = float(_bids[0].get("price", 0.0) or 0.0)
                        if any(
                            (p.get("is_dominance_box") or (_top_b_ws >= 0.997 and p.get("hold_to_maturity_lock")))
                            and str(p.get("token_id") or "") == _tok
                            for p in self.active_positions.values()
                        ):
                            self._ws_urgent_recycle_ts = time.time()
                            loop.call_soon_threadsafe(trigger_notify_event.set)
                    if getattr(self, "_clinched_ws_watchlist", None) and _asks:
                        _snipe_c = self.evaluate_clinched_ws_book_snipe(_tok, _bk)
                        if _snipe_c is not None:
                            _fq = getattr(self, "_fast_d1_cand_lines", None)
                            if _fq is not None:
                                _fq.append(
                                    _orjson.dumps(_snipe_c).decode("utf-8")
                                    if _orjson is not None
                                    else json.dumps(_snipe_c, separators=(",", ":"))
                                )
                                loop.call_soon_threadsafe(fast_d1_box_event.set)
                                loop.call_soon_threadsafe(trigger_notify_event.set)

                _ws_shards_cfg = max(
                    1,
                    min(8, int(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("ws_market_num_shards", 4) or 4)),
                )
                _on_tk_cb = (
                    (lambda _tok, _tk: self.executor.update_ws_tick_size(_tok, _tk))
                    if hasattr(self.executor, "update_ws_tick_size")
                    else None
                )
                if _ws_shards_cfg > 1 and _PolymarketShardedClobMarketWsTracker is not None:
                    self._pos_market_ws = _PolymarketShardedClobMarketWsTracker(
                        num_shards=_ws_shards_cfg,
                        per_shard_max=485,
                        recycle_bid_trigger=0.985,
                        on_urgent_bid=_on_ws_recycle_bid,
                        on_book_change=_on_ws_book_change,
                        on_tick_size_change=_on_tk_cb,
                    )
                else:
                    self._pos_market_ws = _PolymarketClobMarketWsTracker(
                        recycle_bid_trigger=0.985,
                        on_urgent_bid=_on_ws_recycle_bid,
                        on_book_change=_on_ws_book_change,
                        on_tick_size_change=_on_tk_cb,
                    )
                self._pos_market_ws.set_desired_tokens(self._desired_market_ws_tokens())
                pos_ws_task = asyncio.create_task(self._pos_market_ws.run_forever(lambda: bool(self._shutdown_requested)))
            if (
                not self.dry_run
                and _PolymarketPerpsLeadLagStream is not None
                and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_perp1_maker_precancel_leadlag", True))
            ):
                self._perps_leadlag_ws = _PolymarketPerpsLeadLagStream()
                self._perps_leadlag_ws.start_background()

            # Proactively pre-warm active hourly market tokens on startup to eliminate hot-path GETs
            self._prewarm_active_market_tokens()
            _evt_driven = bool(ipc_sock is not None and watcher.is_available)
            fast_consumer_task = asyncio.create_task(
                self._fast_trigger_consumer_loop(fast_shock_event, trigger_fp, trigger_notify_event, _evt_driven)
            )
            fast_d1_consumer_task = asyncio.create_task(
                self._fast_d1_consumer_loop(fast_d1_box_event, trigger_notify_event)
            )

            while True:
                # Graceful SIGTERM/SIGINT shutdown: flush state atomically and leave with exit code 0.
                if self._shutdown_requested:
                    self._shutdown_status = "STOPPED_GRACEFULLY"
                    self._preempt_resting_maker_anchors(reason="SHUTDOWN")
                    fast_shock_event.set()
                    fast_d1_box_event.set()
                    for _ft in (fast_consumer_task, fast_d1_consumer_task):
                        if _ft is not None and not _ft.done():
                            await asyncio.gather(_ft, return_exceptions=True)
                    if getattr(self, "_bg_shock_tasks", None):
                        await asyncio.gather(*list(self._bg_shock_tasks), return_exceptions=True)
                    if getattr(self, "_maker_anchor_bg_tasks", None):
                        await asyncio.gather(*list(self._maker_anchor_bg_tasks), return_exceptions=True)
                    logger.warning(
                        f"[SHUTDOWN] Graceful stop: {len(self.active_positions)} active position(s) persisted to state; "
                        f"resting exit orders (if any) remain on the exchange for restart reconciliation."
                    )
                    await asyncio.to_thread(self.save_state)
                    _any_resting_pos_exit = any(
                        isinstance(_p_sh, dict) and (_p_sh.get("exit_order_id") or _p_sh.get("unwind_order_id"))
                        for _p_sh in self.active_positions.values()
                    )
                    if not _any_resting_pos_exit and not self.dry_run:
                        await asyncio.to_thread(self.executor.cancel_all_orders)
                    break

                if fast_consumer_task is not None and fast_consumer_task.done() and not fast_consumer_task.cancelled():
                    _fc_exc = fast_consumer_task.exception()
                    if _fc_exc is not None:
                        raise _fc_exc
                    fast_consumer_task = asyncio.create_task(
                        self._fast_trigger_consumer_loop(fast_shock_event, trigger_fp, trigger_notify_event, _evt_driven)
                    )
                if fast_d1_consumer_task is not None and fast_d1_consumer_task.done() and not fast_d1_consumer_task.cancelled():
                    _fd1_exc = fast_d1_consumer_task.exception()
                    if _fd1_exc is not None:
                        raise _fd1_exc
                    fast_d1_consumer_task = asyncio.create_task(
                        self._fast_d1_consumer_loop(fast_d1_box_event, trigger_notify_event)
                    )

                # P0 #3: Automated Circuit Breaker & Emergency Kill Switch Check (+ Hot-Reload & Orphaned-Intent Recovery)
                _now_pre_halt = time.time()
                if not self.dry_run and (_now_pre_halt - getattr(self, "_last_pre_halt_gov_chk", 0.0) >= 6.0):
                    self._last_pre_halt_gov_chk = _now_pre_halt
                    await self._apply_governance_hot_reload(_now_pre_halt)
                    if self.pending_entry_intents:
                        _in_dir = getattr(self, "_inflight_directional_entry_ids", set())
                        _in_p3a = getattr(self, "_inflight_phase3a_maker_ids", set())
                        _rec_any = False
                        for _k_pi, _v_pi in list(self.pending_entry_intents.items()):
                            if (
                                not isinstance(_v_pi, dict)
                                or _k_pi in _in_dir
                                or _k_pi in _in_p3a
                                or _v_pi.get("live_maker_anchor_inflight")
                            ):
                                continue
                            _pi_age = _now_pre_halt - float(_v_pi.get("heartbeat_ts") or _v_pi.get("submitted_at_ts") or 0.0)
                            if bool(_v_pi.get("needs_runtime_recovery")) or _pi_age >= 12.0:
                                await asyncio.to_thread(self._recover_pending_intent, _k_pi, _v_pi)
                                _rec_any = True
                        if _rec_any:
                            self._refresh_global_halt(authoritative=True)

                if (
                    not self.dry_run
                    and self.risk_controller.is_halted()
                    and "Heartbeat degraded" in str(self.risk_controller.halt_reason or "")
                    and self.executor.is_heartbeat_healthy()
                ):
                    self.risk_controller.halted = False
                    self.risk_controller.halt_reason = ""
                    self._halt_logged_active = False
                    logger.info("[HEARTBEAT RECOVERED] CLOB heartbeat healthy again; clearing temporary heartbeat halt.")
                    self.save_state()

                if self.risk_controller.is_halted():
                    if (
                        not self.active_positions
                        and not self.dry_run
                        and (time.time() - getattr(self, "_last_halt_collat_check", 0.0) >= 15.0)
                    ):
                        self._last_halt_collat_check = time.time()
                        await self._async_refresh_collateral()
                    if self.risk_controller.is_halted():
                        if not getattr(self, "_halt_logged_active", False):
                            logger.critical(
                                f"[CIRCUIT BREAKER] {self.risk_controller.halt_reason}. "
                                "Halting new entries (supervisor staying alive for recovery / UTC rollover)."
                            )
                            self.save_state()
                            self._halt_logged_active = True
                        if not self.active_positions:
                            if not self.dry_run and not getattr(self, "_halt_orders_cancelled", False):
                                await asyncio.to_thread(self.executor.cancel_all_orders)
                                self._halt_orders_cancelled = True
                            if not self.dry_run and "Heartbeat degraded" in str(self.risk_controller.halt_reason or ""):
                                if (time.time() - getattr(self, "_last_halt_hb_probe", 0.0)) >= 5.0:
                                    self._last_halt_hb_probe = time.time()
                                    await asyncio.to_thread(self.executor.post_heartbeat)
                            await asyncio.sleep(1.0)
                            continue
                else:
                    self._halt_logged_active = False
                    self._halt_orders_cancelled = False

                # P1: Immediate Heartbeat Escalation Check (R03 / Patch A: never exit 0; stay alive & probe recovery)
                if not self.dry_run and not self.executor.is_heartbeat_healthy():
                    self.risk_controller.halted = True
                    self.risk_controller.halt_reason = f"Heartbeat degraded ({self.executor.heartbeat_failures} drops) - new entries halted; existing positions remain supervised."
                    if not getattr(self, "_halt_logged_active", False):
                        logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat dropped {self.executor.heartbeat_failures} times. Halting new entries.")
                        self.save_state()
                        self._halt_logged_active = True
                    if not self.active_positions:
                        if not getattr(self, "_halt_orders_cancelled", False):
                            await asyncio.to_thread(self.executor.cancel_all_orders)
                            self._halt_orders_cancelled = True
                        await asyncio.to_thread(self.executor.post_heartbeat)
                        await asyncio.sleep(1.0)
                        continue

                # 1. Maintain periodic CLOB session heartbeat (every 5.0s when active positions or resting intents exist)
                now_ts = time.time()
                _sync_bg_io = getattr(self.executor, "auth_mode", "") not in ("LIVE", "AUTHENTICATED_L2")
                _needs_clob_hb = bool(
                    self.active_positions
                    or (getattr(self, "pre_split_inventory_state", None) or {}).get("active")
                    or any(isinstance(i, dict) and (i.get("live_maker_anchor_inflight") or i.get("entry_order_id")) for i in getattr(self, "pending_entry_intents", {}).values())
                )
                if not self.dry_run and _needs_clob_hb and (now_ts - last_clob_heartbeat >= 5.0):
                    last_clob_heartbeat = now_ts
                    if _sync_bg_io:
                        hb_res = await asyncio.to_thread(self.executor.post_heartbeat)
                        if isinstance(hb_res, dict) and hb_res.get("error"):
                            logger.warning(f"[HEARTBEAT WARN] Heartbeat error: {hb_res.get('error')}")
                    elif not getattr(self, "_hb_in_flight", False):
                        self._hb_in_flight = True

                        async def _bg_heartbeat():
                            try:
                                res = await asyncio.to_thread(self.executor.post_heartbeat)
                                if isinstance(res, dict) and res.get("error"):
                                    logger.warning(f"[HEARTBEAT WARN] Heartbeat error: {res.get('error')}")
                            finally:
                                self._hb_in_flight = False

                        asyncio.create_task(_bg_heartbeat())

                # 1b. Periodic CLOB keepalive ping every 5s on sync + async hot sockets to keep ARN->LHR tunnel warm 24/7
                if not self.dry_run and (now_ts - getattr(self, "_last_clob_keepalive", 0.0) >= 5.0):
                    self._last_clob_keepalive = now_ts
                    if hasattr(self.executor, "touch_hot_async_clob_socket") and not _sync_bg_io:
                        asyncio.create_task(self.executor.touch_hot_async_clob_socket(3.0))
                        if hasattr(self.executor, "start_async_clob_keepalive_task"):
                            self.executor.start_async_clob_keepalive_task(3.5)
                    await self._apply_governance_hot_reload(now_ts)
                    if _sync_bg_io:
                        await asyncio.to_thread(self.executor.ping_clob_keepalive)
                    elif not getattr(self, "_keepalive_in_flight", False):
                        self._keepalive_in_flight = True

                        async def _bg_keepalive():
                            try:
                                await asyncio.to_thread(self.executor.ping_clob_keepalive)
                            finally:
                                self._keepalive_in_flight = False

                        asyncio.create_task(_bg_keepalive())
                    self._prewarm_active_market_tokens()
                    if not self.active_positions:
                        try:
                            import gc as _gc
                            _gc.collect(0)
                        except Exception:
                            pass
                    if (
                        GLOBAL_SVI_ENGINE is not None
                        and not self._is_riskless_only_mode()
                        and (now_ts - getattr(self, "_last_svi_refresh", 0.0) >= 60.0)
                    ):
                        self._last_svi_refresh = now_ts
                        asyncio.create_task(asyncio.to_thread(GLOBAL_SVI_ENGINE.get_surface, "BTC"))
                        asyncio.create_task(asyncio.to_thread(GLOBAL_SVI_ENGINE.get_surface, "ETH"))

                # 1d. Upgrade 4: Pre-warm next-candle & D1 5m overlap subscriptions at TTE = 120s (:58, :13, :28, :43, :08, :23, :38, :53)
                now_dt = datetime.now(timezone.utc)
                if now_dt.minute in (58, 13, 28, 43, 8, 23, 38, 53):
                    prewarm_min_key = f"{now_dt.hour}:{now_dt.minute}"
                    if getattr(self, "_last_prewarm_minute_key", "") != prewarm_min_key:
                        self._last_prewarm_minute_key = prewarm_min_key
                        asyncio.create_task(self._prewarm_next_candle_markets())

                # 1c. Periodic collateral balance refresh in background (60s when ws/user healthy & flat, else 20s)
                _uws_c = getattr(self.executor, "_user_ws_cache", None)
                _collat_iv = 60.0 if (not self.active_positions and _uws_c is not None and _uws_c.is_healthy()) else 20.0
                if not self.dry_run and (
                    getattr(self, "_pending_collateral_refresh", False)
                    or (now_ts - getattr(self, "_last_collat_poll", 0.0) >= _collat_iv)
                ):
                    self._pending_collateral_refresh = False
                    self._last_collat_poll = now_ts
                    asyncio.create_task(self._async_refresh_collateral())

                # 2. Hot shock triggers are drained concurrently by `fast_consumer_task` (_fast_trigger_consumer_loop)
                #    so slow supervision / D1 box REST & RPC awaits never head-of-line block @polymarket_shock_notify.

                # 2b. Ingest verified D1 Same-Oracle Dominance Box live candidates (<0.2ms RAM IPC or 0.50s disk fallback)
                if (
                    not self._is_d1_box_halted()
                    and (bool(getattr(self, "_fast_d1_cand_lines", None)) or (now_ts - getattr(self, "_last_d1_cand_poll", 0.0) >= 0.50))
                ):
                    self._last_d1_cand_poll = now_ts
                    await self._poll_d1_live_box_candidates(now_ts)

                # 3. Monitor open positions (fast 0.20s cadence when a stop/cancel confirmation or WS >=98.5c recycle bid is armed, else 1.0s)
                urgent_supervision = (
                    (now_ts - float(getattr(self, "_ws_urgent_recycle_ts", 0.0) or 0.0)) <= 1.5
                    or any(
                        p.get("_zero_bal_gamma_urgent")
                        or p.get("strike_retrace_detected_ts")
                        or p.get("opposite_breakout_start_ts")
                        or p.get("low_bid_detected_ts")
                        or p.get("trail_stop_detected_ts")
                        or p.get("zero_bid_detected_ts")
                        or p.get("exit_order_status") in {"STOP_CANCEL_PENDING", "PRE_EXPIRY_CANCEL_PENDING", "FILL_RECONCILIATION_REQUIRED", "PASSIVE_STOP_RESTING", "EXIT_RECOVERY_REQUIRED", "UNWIND_RETRY_REQUIRED"}
                        for p in self.active_positions.values()
                    )
                )
                mgmt_interval = 0.20 if urgent_supervision else 1.0
                if now_ts - last_mgmt_check >= mgmt_interval:
                    last_mgmt_check = now_ts
                    try:
                        await self.check_resolutions_and_manage_positions()
                        if not self.dry_run and not self._is_riskless_only_mode():
                            self._step_shadow_phase3_4_tracker(now_ts)
                    except StatePersistenceError:
                        raise
                    except Exception:
                        logger.exception("[SUPERVISION ERROR] Position management cycle failed; retrying next cycle.")

                if time.time() - last_heartbeat >= 300:
                    last_heartbeat = time.time()
                    for _cd_attr, _ttl_s in (("_d1_retry_cooldown_until", 0.0), ("_ovr_unwind_cd", 600.0)):
                        _cd_m = getattr(self, _cd_attr, None)
                        if isinstance(_cd_m, dict):
                            for _k, _v in list(_cd_m.items()):
                                if float(_v or 0.0) < (last_heartbeat - _ttl_s):
                                    _cd_m.pop(_k, None)
                    _pb_m = getattr(self, "_d1_clean_pre_bal_cache", None)
                    if isinstance(_pb_m, dict):
                        for _k, _v in list(_pb_m.items()):
                            if isinstance(_v, tuple) and (last_heartbeat - float(_v[1] or 0.0)) > 3600.0:
                                _pb_m.pop(_k, None)
                    _lc = getattr(self.executor, "order_ladder_cache", None)
                    if _lc is not None and hasattr(_lc, "prune_expired"):
                        _lc.prune_expired()
                    import gc as _gc
                    if self.active_positions or self.pending_entry_intents or getattr(self, "_clinched_ws_watchlist", None):
                        _gc.collect(0)
                    else:
                        _gc.collect()
                    active_exp = sum(p.get("notional_usd", 0.0) for p in self.active_positions.values())
                    logger.info(
                        f"[HEARTBEAT] Harvester active | Triggers scanned: {self._triggers_scanned_count} | "
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

                # Supervision sleep: wakes immediately on D1 IPC / WS recycle bid / shutdown, else 50ms cadence
                try:
                    await asyncio.wait_for(trigger_notify_event.wait(), timeout=0.050)
                    trigger_notify_event.clear()
                except asyncio.TimeoutError:
                    pass

        except Exception:
            # Never exit silently with status 0: log the traceback and propagate so the
            # process exits non-zero and the supervisor restarts it (startup reconcile re-runs).
            logger.critical("[FATAL] Harvester loop terminated by unhandled exception.", exc_info=True)
            raise
        finally:
            for _ft_c in (
                fast_consumer_task if 'fast_consumer_task' in locals() else None,
                fast_d1_consumer_task if 'fast_d1_consumer_task' in locals() else None,
            ):
                if _ft_c is not None and not _ft_c.done():
                    _ft_c.cancel()
                    try:
                        await _ft_c
                    except (asyncio.CancelledError, Exception):
                        pass
            if 'pos_ws_task' in locals() and pos_ws_task is not None:
                pos_ws_task.cancel()
            if getattr(self, "_perps_leadlag_ws", None) is not None:
                try:
                    self._perps_leadlag_ws.stop()
                except Exception:
                    pass
            if 'd1_ipc_sock' in locals() and d1_ipc_sock is not None:
                try:
                    if 'loop' in locals() and loop is not None:
                        loop.remove_reader(d1_ipc_sock.fileno())
                except Exception:
                    pass
                try:
                    d1_ipc_sock.close()
                except Exception:
                    pass
            if 'ipc_sock' in locals() and ipc_sock is not None:
                try:
                    if 'loop' in locals() and loop is not None:
                        loop.remove_reader(ipc_sock.fileno())
                except Exception:
                    pass
                try:
                    ipc_sock.close()
                except Exception:
                    pass
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
                    if fcntl is not None:
                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()
                except Exception:
                    pass
            try:
                PID_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    async def _apply_governance_hot_reload(self, now_ts: float) -> bool:
        """Applies hot-reloaded governance configuration consistently across pre-halt and active-loop checks."""
        if not getattr(self, "_v5_sighup_installed", False):
            self._v5_sighup_installed = True
            GLOBAL_GOVERNANCE_MANAGER.install_sighup_handler()
        reloaded, snap = GLOBAL_GOVERNANCE_MANAGER.maybe_reload()
        if not reloaded or not isinstance(getattr(self, "risk_config", None), dict):
            return False
        dr_cfg = snap.get("directional", {})
        rk_cfg = snap.get("risk_controller", {})
        rb_cfg = snap.get("riskless_boxes", {})
        self.risk_config["directional_taker_max_price"] = float(dr_cfg.get("max_taker_price_1h", 0.74))
        self.risk_config["directional_taker_max_price_15m"] = float(dr_cfg.get("max_taker_price_15m", 0.72))
        self.risk_config["directional_maker_max_price"] = float(dr_cfg.get("max_maker_price_1h", 0.76))
        self.risk_config["phase3a_15m_long_tte_max_price"] = float(dr_cfg.get("max_maker_price_15m", 0.72))
        if isinstance(rb_cfg, dict):
            if "enable_graduated_d1_box" in rb_cfg:
                self.risk_config["enable_graduated_d1_box"] = bool(rb_cfg["enable_graduated_d1_box"])
            if rb_cfg.get("d1_max_box_cost_net") is not None:
                self.risk_config["d1_max_box_cost_net"] = float(rb_cfg["d1_max_box_cost_net"])
            if rb_cfg.get("cm_b3_max_walk_cap") is not None:
                self.risk_config["cm_b3_max_walk_cap"] = float(rb_cfg["cm_b3_max_walk_cap"])
        if isinstance(rb_cfg, dict) and not bool(rb_cfg.get("enable_single_leg_maker_bond1", True)):
            self._preempt_resting_maker_anchors(reason="GOVERNANCE_DISABLED:SINGLE_LEG_MAKER_BOND1")
        elif isinstance(rb_cfg, dict) and getattr(self, "pending_entry_intents", None):
            _paused_hot = {str(x).upper() for x in (rb_cfg.get("paused_riskless_sleeves") or [])}
            _paused_mids = {
                str(_iv.get("market_id") or "")
                for _iv in self.pending_entry_intents.values()
                if isinstance(_iv, dict)
                and _iv.get("live_maker_anchor_inflight")
                and str(_iv.get("sleeve_source") or "").upper() in _paused_hot
                and _iv.get("market_id")
            }
            if _paused_mids:
                self._preempt_resting_maker_anchors(reason="GOVERNANCE_DISABLED:PAUSED_SLEEVE", market_ids=_paused_mids)
        if dr_cfg.get("min_entry_price") is not None:
            self.min_price_floor = float(dr_cfg["min_entry_price"])
        if dr_cfg.get("max_maker_price_1h") is not None:
            self.max_price_ceiling = float(dr_cfg["max_maker_price_1h"])
        self.risk_controller.max_daily_loss_usd = float(
            rk_cfg.get("max_daily_directional_loss_usd", self.risk_controller.max_daily_loss_usd)
        )
        max_consec = rk_cfg.get(
            "max_consecutive_directional_losses",
            rk_cfg.get("max_consecutive_losses"),
        )
        if max_consec is not None:
            self.risk_controller.max_consecutive_losses = int(max_consec)
        if self.risk_controller.halted:
            hr_str = str(self.risk_controller.halt_reason or "")
            if (
                "Max daily loss reached" in hr_str
                and self.risk_controller.daily_realized_loss < self.risk_controller.max_daily_loss_usd
            ):
                self.risk_controller.halted = False
                self.risk_controller.halt_reason = ""
                self._halt_logged_active = False
            elif (
                "Max consecutive losses reached" in hr_str
                and self.risk_controller.consecutive_losses < self.risk_controller.max_consecutive_losses
            ):
                self.risk_controller.halted = False
                self.risk_controller.halt_reason = ""
                self._halt_logged_active = False
        if getattr(self, "_last_known_collateral", None) is not None:
            eq_now = float(self._last_known_collateral or 0.0) + sum(
                self.get_position_market_value(p, now_ts) for p in self.active_positions.values()
            )
            self._update_equity_tier(eq_now)
            await asyncio.to_thread(self.save_state)
        return True

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
    parser.add_argument("--hold-to-maturity", dest="hold_to_maturity", action="store_true", default=bool(RISK_CONFIG.get("hold_to_maturity", False)), help="Hold resting $0.99 single-tranche ask to maturity instead of 2-tranche / $0.95 WFO maker exit")
    parser.add_argument("--no-hold-to-maturity", dest="hold_to_maturity", action="store_false", help="Enable WFO-optimal resting maker exits (default in production)")
    parser.add_argument("--exit-policy", type=str, default=str(RISK_CONFIG.get("exit_policy", "two_tranche_95_98")), help="Exit policy: hold_98 or two_tranche_95_98")
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
        hold_to_maturity=args.hold_to_maturity,
        exit_policy=args.exit_policy,
        allow_cli_exposure=any(a == "--max-exposure" or a.startswith("--max-exposure=") for a in sys.argv[1:]),
        allow_cli_concurrency=any(a == "--max-concurrent" or a.startswith("--max-concurrent=") for a in sys.argv[1:]),
        allowed_assets=set(args.allowed_assets),
        reset_risk=args.reset_risk,
        max_daily_loss=args.max_daily_loss,
    )
    if os.name != "nt":
        try:
            import uvloop
            uvloop.install()
        except Exception:
            pass
    asyncio.run(harvester.run())


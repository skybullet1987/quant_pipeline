"""
End-to-end latency tracing for the Polymarket live hot path (Phase 0 instrumentation).

Design goals
------------
* Zero risk to trading: every public call is non-blocking and swallows its own errors.
* Three clock domains are recorded and must never be mixed up:
    - local monotonic (`time.perf_counter_ns`)  -> elapsed stage durations on this host only
    - local wall (`time.time_ns`)               -> cross-process / cross-host alignment (needs chrony)
    - source/exchange timestamps                -> stored verbatim as `src_*` fields
* One JSONL record per `execute_snipe_order_async` dispatch attempt, written by a daemon thread.

Output file: `$PM_LATENCY_TRACE_FILE`, else `$PM_TELEMETRY_DIR/latency_trace.jsonl`,
else `data/polymarket/latency_trace.jsonl`. Disable entirely with `PM_LATENCY_TRACE=0`.

Analyse with `python scripts/latency_trace_report.py`.
"""

from __future__ import annotations

import atexit
import contextvars
import json
import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_WRITER_LOCK = threading.Lock()
_WRITER_QUEUE: "queue.SimpleQueue[str]" = queue.SimpleQueue()
_WRITER_THREAD: Optional[threading.Thread] = None
_QUEUE_SOFT_LIMIT = 5000
_pending = 0
_pending_lock = threading.Lock()


def tracing_enabled() -> bool:
    return os.environ.get("PM_LATENCY_TRACE", "1").strip().lower() not in ("0", "false", "no", "off")


def trace_path() -> Path:
    explicit = os.environ.get("PM_LATENCY_TRACE_FILE")
    if explicit:
        return Path(explicit)
    tele = os.environ.get("PM_TELEMETRY_DIR")
    if tele:
        return Path(tele) / "latency_trace.jsonl"
    return Path("data") / "polymarket" / "latency_trace.jsonl"


def _writer_loop() -> None:
    global _pending
    while True:
        try:
            first = _WRITER_QUEUE.get()
            batch = [first]
            deadline = time.monotonic() + 0.25
            while len(batch) < 200 and time.monotonic() < deadline:
                try:
                    batch.append(_WRITER_QUEUE.get(timeout=0.05))
                except queue.Empty:
                    break
            path = trace_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\n".join(batch) + "\n")
            with _pending_lock:
                _pending = max(0, _pending - len(batch))
        except Exception:  # never let telemetry kill anything
            time.sleep(0.5)


def _ensure_writer() -> None:
    global _WRITER_THREAD
    if _WRITER_THREAD is not None and _WRITER_THREAD.is_alive():
        return
    with _WRITER_LOCK:
        if _WRITER_THREAD is not None and _WRITER_THREAD.is_alive():
            return
        t = threading.Thread(target=_writer_loop, name="pm-latency-trace-writer", daemon=True)
        t.start()
        _WRITER_THREAD = t


def flush(timeout: float = 2.0) -> None:
    """Best-effort wait until queued records are written (used by tests / shutdown)."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        with _pending_lock:
            if _pending == 0:
                return
        time.sleep(0.02)


atexit.register(flush)


class LatencyTrace:
    """Collects monotonic stamps + scalar fields for one trigger -> dispatch journey."""

    __slots__ = ("fields", "stamps_ns", "created_mono_ns", "created_wall_ns", "attempt")

    def __init__(self, **fields: Any) -> None:
        self.fields: Dict[str, Any] = dict(fields)
        self.stamps_ns: Dict[str, int] = {}
        self.created_mono_ns = time.perf_counter_ns()
        self.created_wall_ns = time.time_ns()
        self.attempt = 0

    def stamp(self, name: str) -> None:
        try:
            self.stamps_ns[name] = time.perf_counter_ns()
        except Exception:
            pass

    def set(self, **kv: Any) -> None:
        try:
            self.fields.update(kv)
        except Exception:
            pass

    def elapsed_ms(self, a: str, b: str) -> Optional[float]:
        sa, sb = self.stamps_ns.get(a), self.stamps_ns.get(b)
        if sa is None or sb is None:
            return None
        return (sb - sa) / 1e6

    def to_record(self) -> Dict[str, Any]:
        rec: Dict[str, Any] = dict(self.fields)
        rec["attempt"] = self.attempt
        rec["created_wall_ns"] = self.created_wall_ns
        # Stamps are stored relative to trace creation (monotonic, same-host only).
        rec["stamps_rel_ms"] = {
            k: round((v - self.created_mono_ns) / 1e6, 4) for k, v in self.stamps_ns.items()
        }
        return rec

    def emit(self, **final_fields: Any) -> None:
        """Queue one JSONL record. Non-blocking, never raises."""
        global _pending
        try:
            if not tracing_enabled():
                return
            if final_fields:
                self.fields.update(final_fields)
            self.stamp("emit")
            line = json.dumps(self.to_record(), default=str, separators=(",", ":"))
            with _pending_lock:
                if _pending >= _QUEUE_SOFT_LIMIT:
                    return  # drop rather than grow unbounded
                _pending += 1
            _ensure_writer()
            _WRITER_QUEUE.put(line)
            self.attempt += 1
        except Exception:
            logger.debug("latency trace emit failed", exc_info=True)


# Carries the active trace from the harvester coroutine into executor.execute_snipe_order_async
# without changing either public signature.
CURRENT_TRACE: "contextvars.ContextVar[Optional[LatencyTrace]]" = contextvars.ContextVar(
    "pm_current_latency_trace", default=None
)


class ActiveCounter:
    """
    Thread-safe re-entrant activity counter replacing a process-global Event.

    The hot pool has several workers; with an Event the first finisher cleared the flag while
    another POST was still in flight, letting background socket warming collide with it.
    """

    __slots__ = ("_n", "_lock")

    def __init__(self) -> None:
        self._n = 0
        self._lock = threading.Lock()

    def enter(self) -> None:
        with self._lock:
            self._n += 1

    def leave(self) -> None:
        with self._lock:
            self._n = max(0, self._n - 1)

    def is_set(self) -> bool:  # Event-compatible read API for existing call sites
        return self._n > 0

    @property
    def count(self) -> int:
        return self._n

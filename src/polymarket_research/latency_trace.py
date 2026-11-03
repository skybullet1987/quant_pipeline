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

try:
    import orjson as _orjson
except ImportError:  # pragma: no cover
    _orjson = None

logger = logging.getLogger(__name__)

_WRITER_LOCK = threading.Lock()
_WRITER_QUEUE: "queue.SimpleQueue[tuple[str, str]]" = queue.SimpleQueue()
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


def shock_attempt_path() -> Path:
    explicit = os.environ.get("PM_SHOCK_ATTEMPT_FILE")
    if explicit:
        return Path(explicit)
    tele = os.environ.get("PM_TELEMETRY_DIR")
    if tele:
        return Path(tele) / "shock_attempt_forensics.jsonl"
    return Path("data") / "polymarket" / "shock_attempt_forensics.jsonl"


def _writer_loop() -> None:
    global _pending
    while True:
        try:
            first_item = _WRITER_QUEUE.get()
            batch_items = [first_item]
            deadline = time.monotonic() + 0.25
            while len(batch_items) < 200 and time.monotonic() < deadline:
                try:
                    batch_items.append(_WRITER_QUEUE.get(timeout=0.05))
                except queue.Empty:
                    break
            try:
                by_dest: Dict[str, list[str]] = {}
                for dest_s, ln in batch_items:
                    by_dest.setdefault(dest_s, []).append(ln)
                for dest_s, lines_out in by_dest.items():
                    try:
                        path = Path(dest_s)
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with open(path, "a", encoding="utf-8") as fh:
                            fh.write("\n".join(lines_out) + "\n")
                    except Exception:
                        pass
            finally:
                with _pending_lock:
                    _pending = max(0, _pending - len(batch_items))
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
            rec = self.to_record()
            if _orjson is not None:
                try:
                    line = _orjson.dumps(rec, default=str).decode("utf-8")
                except Exception:
                    line = json.dumps(rec, default=str, separators=(",", ":"))
            else:
                line = json.dumps(rec, default=str, separators=(",", ":"))
            dest_str = str(trace_path())
            with _pending_lock:
                if _pending >= _QUEUE_SOFT_LIMIT:
                    return  # drop rather than grow unbounded
                _pending += 1
            _ensure_writer()
            _WRITER_QUEUE.put((dest_str, line))
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

    exit = leave

    def __enter__(self) -> "ActiveCounter":
        self.enter()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.leave()
        return False

    def is_set(self) -> bool:  # Event-compatible read API for existing call sites
        return self._n > 0

    @property
    def count(self) -> int:
        return self._n


def _fin_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    if val is None or isinstance(val, bool):
        return default
    try:
        f = float(val)
        return f if f == f and abs(f) != float("inf") else default
    except (TypeError, ValueError):
        return default


def classify_shock_attempt(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure root-cause & speed attribution classifier for directional shocks and order attempts.
    Answers explicitly whether a missed trade failed due to latency/speed (flight repricing,
    pre-eval MM repricing, or feed/IPC lag), passive Maker runaway, adverse shield protection,
    already-priced-in market quotes, or intentional WFO alpha/governance guardrails.
    """
    now_u = _fin_float(raw.get("unix_ts"), time.time()) or time.time()
    ts_utc = str(raw.get("ts_utc") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_u)))
    asset = str(raw.get("asset") or "").upper()
    horizon = str(raw.get("horizon") or "").lower()
    raw_tt = str(raw.get("target_token") or "").upper()
    raw_sd = str(raw.get("side") or "").upper()
    side = raw_tt if (raw_tt and raw_sd in ("", "BUY", "SELL")) else (raw_sd or raw_tt)
    path_type = str(raw.get("path_type") or "PRE_EVAL").upper()
    gate_code = str(raw.get("gate_code") or "").upper()
    _raw_gd = str(raw.get("gate_detail") or "").strip()
    if not _raw_gd and raw.get("diagnosis"):
        _diag_in = str(raw.get("diagnosis") or "").strip()
        for _pfx in ("Feed/IPC lag blocked entry", "TOO SLOW (MM Beat Shock)"):
            if _diag_in.startswith(_pfx) and "): " in _diag_in:
                _diag_in = _diag_in.split("): ", 1)[1].strip()
                break
            if _diag_in.startswith(_pfx) and ": " in _diag_in:
                _diag_in = _diag_in.split(": ", 1)[1].strip()
                break
        _raw_gd = _diag_in
    gate_detail = _raw_gd
    stage_out = str(raw.get("stage_outcome") or raw.get("outcome") or "").upper()

    tte_s = _fin_float(raw.get("tte_s"))
    dist_pct = _fin_float(raw.get("dist_pct"))
    z_strike = _fin_float(raw.get("z_strike"))
    obi_l1 = _fin_float(raw.get("obi_l1"))
    t0_ask = _fin_float(raw.get("t0_ask"))
    eval_ask = _fin_float(raw.get("eval_ask"))
    eval_bid = _fin_float(raw.get("eval_bid"))
    target_px = _fin_float(raw.get("target_px") if raw.get("target_px") is not None else raw.get("target_limit_px"))
    cap_px = _fin_float(raw.get("cap_px"))
    post_ask = _fin_float(raw.get("post_ask"))
    post_bid = _fin_float(raw.get("post_bid"))
    fill_px = _fin_float(raw.get("fill_px"))
    notional_usd = _fin_float(raw.get("notional_usd") if raw.get("notional_usd") is not None else raw.get("effective_notional_usd"))

    exch_lag_ms = _fin_float(raw.get("exch_lag_ms"))
    ipc_ms = _fin_float(raw.get("ipc_ms") if raw.get("ipc_ms") is not None else raw.get("trigger_to_consume_wall_ms"))
    book_age_ms = _fin_float(raw.get("book_age_ms") if raw.get("book_age_ms") is not None else raw.get("age_ask_ms"))
    empty_ask_ms = _fin_float(raw.get("empty_ask_ms"))
    ws_book_age_ms = _fin_float(raw.get("ws_book_age_ms"))
    gate_ms = _fin_float(raw.get("gate_ms"))
    sign_ms = _fin_float(raw.get("sign_ms"))
    http_ms = _fin_float(raw.get("http_ms") if raw.get("http_ms") is not None else raw.get("clob_http_post_ms"))
    ttl_ms = _fin_float(raw.get("ttl_ms"))
    presign_hit = bool(raw.get("presign_cache_hit", False))

    e2e_parts = [x for x in (exch_lag_ms, ipc_ms, gate_ms, sign_ms, http_ms) if x is not None and x >= 0.0]
    e2e_ms = round(sum(e2e_parts), 2) if e2e_parts else None

    ask_drift_pre_c = round((eval_ask - t0_ask) * 100.0, 1) if (eval_ask and t0_ask and eval_ask > 0 and t0_ask > 0) else None
    ref_pre_flight_ask = eval_ask if (eval_ask and eval_ask > 0) else t0_ask
    ask_drift_flight_c = (
        round((post_ask - ref_pre_flight_ask) * 100.0, 1)
        if (post_ask and ref_pre_flight_ask and post_ask > 0 and ref_pre_flight_ask > 0)
        else None
    )

    if stage_out in ("FILLED_TAKER", "POSTED", "MATCHED") and str(raw.get("resp_status") or "matched").lower() in ("matched", "filled", ""):
        if path_type == "PRE_EVAL":
            path_type = "TAKER_FOK"
    elif stage_out in ("FAK_KILLED", "FAK_KILLED_NO_MATCH") and path_type == "PRE_EVAL":
        path_type = "TAKER_FOK"
    elif "MAKER" in stage_out and path_type == "PRE_EVAL":
        path_type = "MAKER_P3A"

    is_order_attempt = path_type in ("TAKER_FOK", "MAKER_P3A", "MAKER_BOX")
    speed_verdict = "ALPHA_GATE_VETO"
    badge = "GATE VETO"
    diagnosis = gate_detail or gate_code or "Filtered by strategy guardrail"

    def _lat_tag() -> str:
        bits = []
        if exch_lag_ms is not None:
            bits.append(f"Exch {exch_lag_ms:.0f}ms")
        if ipc_ms is not None:
            bits.append(f"IPC {ipc_ms:.1f}ms")
        if sign_ms is not None:
            bits.append(f"Sign {sign_ms:.2f}ms")
        if http_ms is not None:
            bits.append(f"HTTP {http_ms:.0f}ms")
        return ", ".join(bits) if bits else "n/a"

    if stage_out in ("FILLED_TAKER", "FILLED_MAKER", "FILLED_BOX") or (
        stage_out == "POSTED" and str(raw.get("resp_status") or "").lower() == "matched"
    ):
        speed_verdict = "FILLED"
        badge = "FILLED"
        px_show = fill_px or target_px or eval_ask or 0.0
        diagnosis = f"Filled @ ${px_show:.3f}" + (f" (${notional_usd:.2f})" if notional_usd else "") + f" [{_lat_tag()}]"

    elif stage_out in ("FAK_KILLED", "FAK_KILLED_NO_MATCH"):
        speed_verdict = "TOO_SLOW_FLIGHT"
        badge = "TOO SLOW (FLIGHT)"
        lim_s = f"${target_px:.2f}" if target_px else "limit"
        ev_s = f"${eval_ask:.2f}" if eval_ask else (f"${t0_ask:.2f}" if t0_ask else "?")
        if post_ask and target_px and post_ask > target_px + 0.005:
            jump_c = (post_ask - (eval_ask or target_px)) * 100.0
            diagnosis = f"TOO SLOW (Flight): FOK @{lim_s} (eval {ev_s}) missed — MM repriced ask -> ${post_ask:.2f} ({jump_c:+.1f}c) during flight ({_lat_tag()})"
        else:
            diagnosis = f"TOO SLOW (Flight): FOK @{lim_s} (eval {ev_s}) 0-fill — L1 liquidity swept ahead during flight ({_lat_tag()})"

    elif stage_out in ("MAKER_POST_FAILED", "BOND1_MAKER_POST_FAILED", "HTTP_400", "CLOB_HTTP_400_REJECTION"):
        err_l = gate_detail.lower()
        if any(k in err_l for k in ("crosses book", "post only", "post-only")):
            speed_verdict = "TOO_SLOW_FLIGHT"
            badge = "POST-ONLY CROSSED"
            diagnosis = f"Book crossed Maker bid ${target_px or 0:.3f} during HTTP flight ({_lat_tag()}): {gate_detail[:90]}"
        else:
            speed_verdict = "CLOB_REJECT"
            badge = "CLOB 400 REJECT"
            diagnosis = f"CLOB rejected order @${target_px or 0:.3f}: {gate_detail[:110] or stage_out}"

    elif stage_out in ("SHIELD_PRE_POST", "SHIELD_ADVERSE_TTL", "BOND1_MAKER_ADVERSE_CANCELLED"):
        speed_verdict = "SHIELD_SAVED"
        badge = "SHIELD SAVED"
        diagnosis = gate_detail or (
            "Pre-post shield aborted Maker: spot retraced >25% before post"
            if stage_out == "SHIELD_PRE_POST"
            else f"Mid-TTL adverse shield canceled Maker @{f'${target_px:.3f}' if target_px else ''} before toxic fill"
        )

    elif stage_out == "BOND1_MAKER_OUTBID_RELEASED":
        ttl_s_lbl = f"{(ttl_ms or 0.0) / 1000.0:.1f}s" if ttl_ms else "TTL"
        speed_verdict = "ALPHA_GATE_VETO"
        badge = "OUTBID RELEASED"
        diagnosis = (
            f"Released outbid 0%-fee Maker @${target_px or 0:.3f} after {ttl_s_lbl} "
            f"to free collateral ({gate_detail or 'outbid above cap'}) [{_lat_tag()}]"
        )

    elif stage_out in ("MAKER_TTL_EXPIRED", "BOND1_MAKER_EXPIRED_UNFILLED", "BOND1_MAKER_PREEMPTED"):
        ttl_s_lbl = f"{(ttl_ms or 0.0) / 1000.0:.1f}s" if ttl_ms else "TTL"
        if stage_out == "BOND1_MAKER_PREEMPTED":
            speed_verdict = "MAKER_TTL_QUIET"
            badge = "MAKER PREEMPTED"
            diagnosis = (
                f"Preempted resting 0%-fee Maker @${target_px or 0:.3f} after {ttl_s_lbl} "
                f"to free collateral ({gate_detail or 'priority entry'}) [{_lat_tag()}]"
            )
        elif path_type == "MAKER_P3A" and post_ask and target_px and (
            post_ask >= target_px + 0.03 or (eval_ask and post_ask >= eval_ask + 0.02)
        ):
            speed_verdict = "LEFT_BEHIND_MAKER"
            badge = "LEFT BEHIND (MAKER)"
            ev_s = f"${eval_ask:.2f}" if eval_ask else f"${target_px + 0.01:.2f}"
            diagnosis = (
                f"LEFT BEHIND: Posted 0%-fee Maker @${target_px:.2f} ({_lat_tag()}); "
                f"ask ran {ev_s} -> ${post_ask:.2f} ({(post_ask - (eval_ask or target_px))*100:+.0f}c) over {ttl_s_lbl} without pullback"
            )
        else:
            speed_verdict = "MAKER_TTL_QUIET"
            badge = "MAKER TTL QUIET"
            end_s = f" (end ask ${post_ask:.3f})" if post_ask else ""
            diagnosis = f"Resting 0%-fee Maker @${target_px or 0:.3f} unfilled after {ttl_s_lbl}, canceled cleanly{end_s} [{_lat_tag()}]"

    elif gate_code == "NO_RESTING_ASKS":
        speed_verdict = "ALPHA_GATE_VETO"
        badge = "NO ASKS"
        diagnosis = gate_detail or "Empty ask book at t0 — not a speed miss"

    elif (
        gate_code == "COMPOSITE_EDGE_VETO"
        and "AGE_ASK_MS" in gate_detail.upper()
        and t0_ask is not None
        and t0_ask >= 0.995
    ):
        speed_verdict = "ALREADY_PRICED_IN"
        badge = "ALREADY PRICED IN"
        diagnosis = f"Already Priced In: No resting asks < $1.00 at t0 ({_lat_tag()}) — not a speed miss"

    elif gate_code == "COMPOSITE_EDGE_VETO" and (
        "REPRICED BY MM" in gate_detail.upper() or "MM ASK RELOAD" in gate_detail.upper()
    ):
        _mm_px = eval_ask if eval_ask is not None else t0_ask
        _mm_cap = cap_px if (cap_px is not None and cap_px > 0.0) else (0.72 if "15" in horizon else 0.76)
        _mm_jumped = bool(ask_drift_pre_c is not None and ask_drift_pre_c >= 1.9)
        if _mm_px is not None and _mm_px >= max(0.88, _mm_cap + 0.12) and not _mm_jumped:
            speed_verdict = "ALREADY_PRICED_IN"
            badge = "ALREADY PRICED IN"
            diagnosis = (
                f"Already Priced In: Ask already deep ITM @${_mm_px:.2f} (> ${_mm_cap:.2f} cap) "
                f"before shock ({_lat_tag()}) — not a speed miss"
            )
        else:
            speed_verdict = "TOO_SLOW_PRE_EVAL"
            badge = "TOO SLOW (PRE-EVAL)"
            diagnosis = f"TOO SLOW (MM Beat Shock): {gate_detail} ({_lat_tag()})"

    elif gate_code in ("EXCHANGE_LAG_REJECT", "STALE_TRIGGER_INGRESS"):
        speed_verdict = "TOO_SLOW_FEED_LAG"
        badge = "FEED / IPC LAG"
        diagnosis = f"Feed/IPC lag blocked entry ({_lat_tag()}): {gate_detail or gate_code}"

    elif gate_code in (
        "CLOB_WS_DISCONNECTED",
        "STALE_RECORDER_GUARD",
        "SLOW_REST_BOOK",
    ) or ("MISSING LIVE MICROSTRUCTURE" in gate_detail.upper() or "AGE_ASK_MS" in gate_detail.upper()):
        _lag_px = eval_ask if eval_ask is not None else t0_ask
        if _lag_px is not None and _lag_px >= 0.985 and not (ask_drift_pre_c is not None and ask_drift_pre_c >= 1.9):
            speed_verdict = "ALREADY_PRICED_IN"
            badge = "ALREADY PRICED IN"
            diagnosis = f"Already Priced In: Book already pinned @${_lag_px:.3f} before shock ({_lat_tag()}) — not a speed miss"
        else:
            speed_verdict = "TOO_SLOW_FEED_LAG"
            badge = "FEED / IPC LAG"
            diagnosis = f"Feed/IPC lag blocked entry ({_lat_tag()}): {gate_detail or gate_code}"

    elif gate_code in (
        "TAKER_ASYMMETRY_VETO",
        "15M_MAKER_INELIGIBLE",
        "EV_CEILING_REJECT",
        "PRICE_BAND_REJECT",
        "VWAP_BAND_REJECT",
        "P_MAX_REJECT",
    ):
        px_now = eval_ask or t0_ask or 0.0
        cap_s = f"${cap_px:.2f}" if cap_px else "cap"
        jumped_since_t0 = bool(ask_drift_pre_c is not None and ask_drift_pre_c >= 1.9)
        just_repriced_by_mm = bool(
            book_age_ms is not None
            and 0.0 <= book_age_ms <= 350.0
            and (cap_px is None or px_now <= cap_px + 0.12)
        )
        just_swept_empty = bool(
            px_now >= 0.995 and empty_ask_ms is not None and 0.0 <= empty_ask_ms <= 350.0
        )
        _pinned_floor = cap_px if (cap_px is not None and cap_px > 0.0) else 0.80
        if just_swept_empty:
            speed_verdict = "TOO_SLOW_PRE_EVAL"
            badge = "TOO SLOW (PRE-EVAL)"
            diagnosis = (
                f"TOO SLOW (Swept Empty): Asks swept to empty {empty_ask_ms:.0f}ms ago "
                f"before dispatch ({_lat_tag()})"
            )
        elif px_now >= 0.995 and eval_bid is not None and eval_bid >= _pinned_floor and not jumped_since_t0:
            speed_verdict = "ALREADY_PRICED_IN"
            badge = "ALREADY PRICED IN"
            diagnosis = f"Already Priced In: Book pinned @${eval_bid:.2f} bid / no asks < $1.00 before shock — not a speed miss"
        elif jumped_since_t0 or just_repriced_by_mm:
            speed_verdict = "TOO_SLOW_PRE_EVAL"
            badge = "TOO SLOW (PRE-EVAL)"
            if jumped_since_t0 and t0_ask:
                diagnosis = (
                    f"TOO SLOW (Pre-Eval): Ask jumped ${t0_ask:.2f} -> ${px_now:.2f} (+{ask_drift_pre_c:.1f}c > {cap_s}) "
                    f"before dispatch ({_lat_tag()})"
                )
            else:
                diagnosis = (
                    f"TOO SLOW (MM Beat Shock): MM repriced ask {book_age_ms:.0f}ms ago to ${px_now:.2f} > {cap_s} "
                    f"before trigger arrived ({_lat_tag()})"
                )
        elif cap_px and px_now < cap_px and eval_bid and eval_bid > cap_px:
            speed_verdict = "ALREADY_PRICED_IN"
            badge = "ABOVE CAP"
            diagnosis = f"Bid ${eval_bid:.2f} / Ask ${px_now:.2f} already above {cap_s} ceiling"
        else:
            speed_verdict = "ALREADY_PRICED_IN"
            badge = "ALREADY PRICED IN"
            age_s = f" for {book_age_ms/1000.0:.1f}s" if (book_age_ms and book_age_ms >= 400.0) else ""
            diagnosis = f"Already Priced In: Book sat @${px_now:.2f}{age_s} (> {cap_s}) before shock — not a speed miss"

    elif gate_code == "SHADOW_ASSET_PAUSED":
        speed_verdict = "SHADOW_RECORDED"
        badge = "SHADOW ONLY"
        path_type = "SHADOW"
        diagnosis = f"{asset} live directional paused in v5.2; logged to shadow ledger (ask ${t0_ask or 0:.2f}, dist {dist_pct or 0:+.3f}%)"

    elif gate_code == "WFO_Z_CUSHION":
        speed_verdict = "ALPHA_GATE_VETO"
        badge = "WFO Z-GATE"
        diagnosis = gate_detail or f"z_strike={z_strike or 0:.2f} below WFO floor (dist {dist_pct or 0:+.3f}%, TTE {tte_s or 0:.0f}s)"

    elif gate_code == "COMPOSITE_EDGE_VETO":
        speed_verdict = "ALPHA_GATE_VETO"
        badge = "OBI / EDGE VETO"
        diagnosis = gate_detail or f"Composite microstructure veto (obi_l1={obi_l1 or 0:+.2f})"

    elif gate_code in ("15M_TTE_WINDOW", "1H_TTE_WINDOW", "TTE_OUT_OF_RANGE"):
        speed_verdict = "ALPHA_GATE_VETO"
        badge = "TTE WINDOW"
        diagnosis = gate_detail or f"TTE {tte_s or 0:.0f}s outside allowed entry window"

    elif gate_code == "CUSHION_TOO_SMALL":
        speed_verdict = "ALPHA_GATE_VETO"
        badge = "THIN CUSHION"
        diagnosis = gate_detail or f"Spot distance {dist_pct or 0:+.4f}% insufficient / opposing {side} shock"

    else:
        speed_verdict = "ALPHA_GATE_VETO"
        badge = gate_code[:18].replace("_", " ") if gate_code else "GATE VETO"
        diagnosis = gate_detail or gate_code or "Filtered prior to dispatch"

    _px_settled = eval_ask if eval_ask is not None else t0_ask
    is_settled_99c = bool(
        speed_verdict == "ALREADY_PRICED_IN"
        and _px_settled is not None
        and (
            (0.985 <= _px_settled < 0.995)
            or (_px_settled >= 0.995 and (eval_bid is None or eval_bid >= 0.98))
            or (eval_bid is not None and eval_bid >= 0.98 and _px_settled >= 0.985)
        )
    )
    if is_settled_99c:
        badge = "SETTLED 99c+"

    is_speed_miss = speed_verdict in ("TOO_SLOW_FLIGHT", "TOO_SLOW_PRE_EVAL", "TOO_SLOW_FEED_LAG", "LEFT_BEHIND_MAKER")
    meaningful = bool(
        is_order_attempt
        or is_speed_miss
        or speed_verdict in ("SHIELD_SAVED", "CLOB_REJECT", "SHADOW_RECORDED")
        or (speed_verdict == "ALREADY_PRICED_IN" and not is_settled_99c)
        or (
            not is_settled_99c
            and gate_code not in ("CUSHION_TOO_SMALL", "TTE_OUT_OF_RANGE", "1H_TTE_WINDOW", "15M_TTE_WINDOW", "MARKET_DEDUP", "CONCURRENCY_LIMIT")
            and (dist_pct is None or abs(dist_pct) >= 0.04)
        )
    )

    return {
        "ts_utc": ts_utc,
        "unix_ts": round(now_u, 3),
        "shock_id": str(raw.get("shock_id") or ""),
        "trade_id": str(raw.get("trade_id") or ""),
        "asset": asset,
        "horizon": horizon,
        "side": side,
        "market_id": str(raw.get("market_id") or ""),
        "title": str(raw.get("title") or "")[:72],
        "sleeve": str(raw.get("sleeve") or ""),
        "path_type": path_type,
        "gate_code": gate_code,
        "stage_outcome": stage_out,
        "speed_verdict": speed_verdict,
        "badge": badge,
        "is_speed_miss": is_speed_miss,
        "is_order_attempt": is_order_attempt,
        "meaningful": meaningful,
        "tte_s": round(tte_s, 1) if tte_s is not None else None,
        "dist_pct": round(dist_pct, 4) if dist_pct is not None else None,
        "z_strike": round(z_strike, 3) if z_strike is not None else None,
        "obi_l1": round(obi_l1, 3) if obi_l1 is not None else None,
        "t0_ask": round(t0_ask, 4) if t0_ask is not None else None,
        "eval_ask": round(eval_ask, 4) if eval_ask is not None else None,
        "eval_bid": round(eval_bid, 4) if eval_bid is not None else None,
        "target_px": round(target_px, 4) if target_px is not None else None,
        "cap_px": round(cap_px, 4) if cap_px is not None else None,
        "post_ask": round(post_ask, 4) if post_ask is not None else None,
        "post_bid": round(post_bid, 4) if post_bid is not None else None,
        "fill_px": round(fill_px, 4) if fill_px is not None else None,
        "notional_usd": round(notional_usd, 2) if notional_usd is not None else None,
        "ask_drift_pre_c": ask_drift_pre_c,
        "ask_drift_flight_c": ask_drift_flight_c,
        "exch_lag_ms": round(exch_lag_ms, 1) if exch_lag_ms is not None else None,
        "ipc_ms": round(ipc_ms, 2) if ipc_ms is not None else None,
        "book_age_ms": round(book_age_ms, 1) if book_age_ms is not None else None,
        "ws_book_age_ms": round(ws_book_age_ms, 1) if ws_book_age_ms is not None else None,
        "gate_ms": round(gate_ms, 2) if gate_ms is not None else None,
        "sign_ms": round(sign_ms, 3) if sign_ms is not None else None,
        "http_ms": round(http_ms, 2) if http_ms is not None else None,
        "ttl_ms": round(ttl_ms, 1) if ttl_ms is not None else None,
        "e2e_ms": e2e_ms,
        "presign_hit": presign_hit,
        "diagnosis": diagnosis,
    }


def emit_shock_attempt(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Non-blocking background write to `shock_attempt_forensics.jsonl`."""
    global _pending
    try:
        if not tracing_enabled():
            return None
        if raw.get("skip_forensic"):
            return None
        if raw.get("dry_run") and not os.environ.get("PM_SHOCK_ATTEMPT_FILE"):
            return None
        rec = classify_shock_attempt(raw)
        if _orjson is not None:
            try:
                line = _orjson.dumps(rec, default=str).decode("utf-8")
            except Exception:
                line = json.dumps(rec, default=str, separators=(",", ":"))
        else:
            line = json.dumps(rec, default=str, separators=(",", ":"))
        dest_str = str(shock_attempt_path())
        with _pending_lock:
            if _pending >= _QUEUE_SOFT_LIMIT:
                return rec
            _pending += 1
        _ensure_writer()
        _WRITER_QUEUE.put((dest_str, line))
        if rec.get("is_order_attempt") or rec.get("is_speed_miss"):
            logger.info(
                "[ATTEMPT FORENSICS] %s %s %s [%s] %s",
                rec.get("asset"),
                rec.get("horizon"),
                rec.get("side"),
                rec.get("badge"),
                rec.get("diagnosis"),
            )
        return rec
    except Exception:
        logger.debug("emit_shock_attempt failed", exc_info=True)
        return None


def emit_shock_attempt_from_trace(trace: Optional[LatencyTrace], shock: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Extracts monotonic timing + gate/attempt telemetry from `LatencyTrace` + `shock` and queues forensics."""
    try:
        if trace is None:
            return None
        f = dict(trace.fields)
        if f.get("skip_forensic"):
            return None
        shk = shock or {}
        s_dir = str(shk.get("shock_direction") or "").upper()
        f_tt = str(f.get("target_token") or "").upper()
        f_sd = str(f.get("side") or "").upper()
        side = f_tt or (f_sd if f_sd not in ("", "BUY", "SELL") else ("UP" if s_dir == "BUY" else ("DOWN" if s_dir == "SELL" else f_sd)))
        tf_t0 = ((shk.get("pre_shock_features_t0") or {}).get(side) or {}) if side else {}
        t0_u = _fin_float(shk.get("t0_unix"))
        exch_ms = _fin_float(shk.get("exchange_event_ts_ms"))
        exch_lag = ((t0_u * 1000.0) - exch_ms) if (t0_u and exch_ms and exch_ms > 0) else None
        gate_ms = trace.elapsed_ms("trigger_consumed", "dispatch_call")
        if gate_ms is None:
            s_c = trace.stamps_ns.get("trigger_consumed")
            if s_c is not None:
                gate_ms = (time.perf_counter_ns() - s_c) / 1e6

        _shk_age_ms = shk.get("age_ask_ms") if shk.get("age_ask_ms") is not None else tf_t0.get("age_ask_ms")
        merged: Dict[str, Any] = {
            "unix_ts": time.time(),
            "shock_id": f.get("shock_id") or shk.get("shock_id") or f"{shk.get('market_id')}_{shk.get('t0_unix')}",
            "market_id": f.get("market_id") or shk.get("market_id") or "",
            "title": f.get("title") or shk.get("title") or "",
            "asset": f.get("asset") or shk.get("asset") or "",
            "horizon": f.get("horizon") or shk.get("horizon") or shk.get("candle_interval") or "",
            "side": side,
            "tte_s": f.get("tte_s") if f.get("tte_s") is not None else shk.get("seconds_to_expiry"),
            "dist_pct": f.get("dist_pct") if f.get("dist_pct") is not None else shk.get("candle_distance_pct"),
            "t0_ask": f.get("t0_ask") if f.get("t0_ask") is not None else tf_t0.get("best_ask"),
            "book_age_ms": f.get("book_age_ms") if f.get("book_age_ms") is not None else _shk_age_ms,
            "empty_ask_ms": f.get("empty_ask_ms") if f.get("empty_ask_ms") is not None else tf_t0.get("empty_ask_ms"),
            "obi_l1": f.get("obi_l1") if f.get("obi_l1") is not None else tf_t0.get("obi_l1"),
            "exch_lag_ms": f.get("exch_lag_ms") if f.get("exch_lag_ms") is not None else exch_lag,
            "gate_ms": gate_ms,
        }
        merged.update(f)
        return emit_shock_attempt(merged)
    except Exception:
        logger.debug("emit_shock_attempt_from_trace failed", exc_info=True)
        return None

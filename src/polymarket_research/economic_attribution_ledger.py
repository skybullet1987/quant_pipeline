"""
Stage B Institutional Opportunity Funnel, Competitor Decay Curve & Reconciled Economic Attribution Engine
(`src/polymarket_research/economic_attribution_ledger.py`).

Design invariants:
  1. Zero risk to live trading: every public telemetry hook (`emit_funnel_event`,
     `register_competitor_decay_watch`, `on_ws_book_top_tick`, `schedule_maker_markout`)
     is 100% non-blocking, bounded in memory, and swallows all internal exceptions.
  2. Zero double-counting economic identity:
       Net Economic PnL = (Ending Reconciled Equity - Starting Reconciled Equity - Net Deposits)
                          - Pro-Rated Infra & AI Cost
     And across closed strategy positions (grouped by multi-leg `box_id` via `group_closed_positions_by_box`):
       Realized Net Strategy PnL = Gross Structural Capture
                                   - Normal Taker Fees Paid
                                   - Partial-Basket Unwind Bleed (spread + unwind fees)
                                   + Paid Maker Rebates + Paid Liquidity/Holding Rewards
                                   - Direct On-Chain Gas
     Unsettled/estimated rebates are tracked in `est_unsettled_rebates_usd` only and NEVER added to realized cash.
  3. Actionable 4-Bucket Competitor Decay Telemetry (`competitor_decay_ms`):
       - `lt_5ms`   (< 5 ms)   : London Rust Co-Lo Taker zone (or resting #1 FIFO Maker ahead of time)
       - `5_15ms`   (5-15 ms)  : London AWS eu-west-2 Co-Lo zone (Rung 4 trigger)
       - `15_40ms`  (15-40 ms) : Compliant <12ms EU Proximity VM zone (Rung 2 trigger when > 5x VM delta)
       - `gt_40ms`  (> 40 ms)  : Capturable directly from Finland (`europe-north1`)
"""

from __future__ import annotations

import atexit
from datetime import datetime, timezone
import heapq
import json
import logging
import math
import os
from pathlib import Path
import queue
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

try:
    import orjson as _orjson
except ImportError:  # pragma: no cover
    _orjson = None

logger = logging.getLogger(__name__)

FUNNEL_STAGES: Tuple[str, ...] = (
    "GROSS_ARB_SEEN",
    "EXECUTABLE_NET_L2",
    "ORDER_SUBMITTED",
    "COMPLETE_BASKET_LOCKED",
    "PARTIAL_BASKET_UNWOUND",
    "COMPETITOR_DECAY_OBSERVED",
)

DECAY_BUCKETS: Tuple[str, ...] = ("lt_5ms", "5_15ms", "15_40ms", "gt_40ms")

UNHEDGED_DIRECTIONAL_SLEEVES: frozenset[str] = frozenset({
    "SLEEVE_1_CORE_302",
    "SLEEVE_1_SUBHOURLY_15M",
})

BENIGN_FLAT_MERGE_REASONS: frozenset[str] = frozenset({
    "PRE_SPLIT_PRE_EXPIRY_MERGED",
    "COMPLETE_SET_ONCHAIN_MERGED",
    "SYNTHETIC_COMPLEMENT_MERGED",
    "CROSS_CONDITION_COMPLEMENT_MERGED",
    "CTF_COMPLETE_SET_MERGED",
    "OVERROUND_SWEEP_REJECTED_MERGED_BACK",
})

PARTIAL_UNWIND_REASON_TOKENS: Tuple[str, ...] = (
    "LEGGED_OUT",
    "RESIDUAL_UNWIND",
    "PARTIAL_BASKET",
    "EMERGENCY_UNWOUND",
    "INLINE_UNWIND",
    "MAKER_ANCHOR_UNWIND",
    "UNHEDGED_LEG_UNWIND",
)

DEFAULT_VM_HOURLY_COST_USD = 0.0730  # e2-custom-2-4096 (~$1.752/day = ~US$52.56/mo = ~CA$72/mo)
DEFAULT_RISKLESS_LOCK_START_UTC = "2026-11-04T02:05:00Z"
DEFAULT_RISKLESS_LOCK_START_EQUITY_USD = 60.92


def _sf(val: Any, default: float = 0.0) -> float:
    if val is None or isinstance(val, bool) or val == "":
        return default
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _opt_float(val: Any) -> Optional[float]:
    if val is None or isinstance(val, bool) or val == "":
        return None
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _parse_ts(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        f = float(val)
        if f <= 0 or not math.isfinite(f):
            return None
        return f / 1000.0 if f > 1e12 else f
    s = str(val).strip()
    if not s:
        return None
    try:
        f = float(s)
        if f > 1e8 and math.isfinite(f):
            return f / 1000.0 if f > 1e12 else f
    except ValueError:
        pass
    try:
        iso = s.replace(" UTC", "Z").replace(" ", "T")
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def external_cashflows_config_path(data_or_repo_root: Optional[Path] = None) -> Path:
    explicit = os.environ.get("PM_EXTERNAL_CASHFLOWS_FILE")
    if explicit and data_or_repo_root is None:
        return Path(explicit)
    if data_or_repo_root is not None:
        p = Path(data_or_repo_root)
        if p.is_file():
            return p
        cand_direct = p / "config" / "polymarket_external_cashflows.json"
        if cand_direct.exists():
            return cand_direct
        # If caller passed `data/polymarket`, check parent repo root `../../config/...`
        cand_parent = p.resolve().parents[1] / "config" / "polymarket_external_cashflows.json" if len(p.resolve().parents) >= 2 else cand_direct
        if cand_parent.exists():
            return cand_parent
        return cand_direct
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "config" / "polymarket_external_cashflows.json"


def load_external_cashflows_summary(
    data_or_repo_root: Optional[Path] = None,
    *,
    since_utc: Any = None,
    epoch_start_utc: str = DEFAULT_RISKLESS_LOCK_START_UTC,
) -> Dict[str, Any]:
    """
    Loads authoritative post-lock operator deposits/withdrawals so external principal
    is never misattributed as trading profit in wallet-delta, 24h delta, or Stage B KPI #1.
    """
    cfg_path = external_cashflows_config_path(data_or_repo_root)
    start_eq = DEFAULT_RISKLESS_LOCK_START_EQUITY_USD
    ep_utc = epoch_start_utc
    rows: List[Dict[str, Any]] = []
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                start_eq = _sf(raw.get("riskless_lock_start_equity_usd"), DEFAULT_RISKLESS_LOCK_START_EQUITY_USD)
                ep_utc = str(raw.get("riskless_lock_epoch_start_utc") or epoch_start_utc)
                for item in raw.get("cashflows") or ():
                    if isinstance(item, dict):
                        rows.append(dict(item))
        except Exception:
            pass

    ep_ts = _parse_ts(ep_utc)
    since_ts = _parse_ts(since_utc) if since_utc is not None else None
    net_post_lock = 0.0
    net_since_window = 0.0
    valid_count = 0

    for item in rows:
        amt = abs(_sf(item.get("amount_usd"), 0.0))
        if amt <= 0.0:
            continue
        cf_type = str(item.get("type") or "DEPOSIT").strip().upper()
        signed_amt = -amt if cf_type in ("WITHDRAWAL", "WITHDRAW", "OUTFLOW") else amt
        cf_ts = _parse_ts(item.get("recorded_at_utc") or item.get("ts_utc") or item.get("timestamp"))
        if ep_ts is None or cf_ts is None or cf_ts >= ep_ts:
            net_post_lock += signed_amt
            valid_count += 1
        if since_ts is not None and cf_ts is not None and cf_ts > since_ts:
            net_since_window += signed_amt

    net_post_lock_r = round(net_post_lock, 4)
    contributed_basis_r = round(float(start_eq) + net_post_lock_r, 4)
    return {
        "starting_lock_equity_usd": round(float(start_eq), 2),
        "riskless_lock_epoch_start_utc": ep_utc,
        "net_deposits_post_lock_usd": round(net_post_lock_r, 2),
        "contributed_capital_basis_usd": round(contributed_basis_r, 2),
        "net_deposits_since_window_usd": round(net_since_window, 2),
        "cashflows_count": valid_count,
        "cashflows": rows,
    }


def telemetry_enabled() -> bool:
    return os.environ.get("PM_STAGE_B_TELEMETRY", "1").strip().lower() not in ("0", "false", "no", "off")


def _base_telemetry_dir() -> Path:
    tele = os.environ.get("PM_TELEMETRY_DIR")
    if tele:
        return Path(tele)
    return Path("data") / "polymarket"


def funnel_log_path(data_dir: Optional[Path] = None) -> Path:
    explicit = os.environ.get("PM_OPPORTUNITY_FUNNEL_FILE")
    if explicit and data_dir is None:
        return Path(explicit)
    base = Path(data_dir) if data_dir is not None else _base_telemetry_dir()
    return base / "opportunity_funnel.jsonl"


def markout_log_path(data_dir: Optional[Path] = None) -> Path:
    explicit = os.environ.get("PM_MAKER_MARKOUT_FILE")
    if explicit and data_dir is None:
        return Path(explicit)
    base = Path(data_dir) if data_dir is not None else _base_telemetry_dir()
    return base / "maker_markouts.jsonl"


def classify_decay_bucket(decay_ms: float) -> str:
    ms = max(0.0, float(decay_ms))
    if ms < 5.0:
        return "lt_5ms"
    if ms < 15.0:
        return "5_15ms"
    if ms <= 40.0:
        return "15_40ms"
    return "gt_40ms"


# ---------------------------------------------------------------------------
# Non-Blocking Async JSONL Writer (Shared by Opportunity Funnel & Markouts)
# ---------------------------------------------------------------------------

_WRITER_LOCK = threading.Lock()
_WRITER_QUEUE: "queue.SimpleQueue[tuple[str, str]]" = queue.SimpleQueue()
_WRITER_THREAD: Optional[threading.Thread] = None
_PENDING_LOCK = threading.Lock()
_PENDING_COUNT = 0
_QUEUE_SOFT_CAP = 8192
_ROTATE_MAX_BYTES = 20 * 1024 * 1024


def _dumps_line(rec: Mapping[str, Any]) -> str:
    if _orjson is not None:
        try:
            return _orjson.dumps(dict(rec), default=str).decode("utf-8")
        except Exception:
            pass
    return json.dumps(dict(rec), default=str, separators=(",", ":"))


def _writer_loop() -> None:
    global _PENDING_COUNT
    while True:
        try:
            first = _WRITER_QUEUE.get()
            batch = [first]
            deadline = time.monotonic() + 0.25
            while len(batch) < 250 and time.monotonic() < deadline:
                try:
                    batch.append(_WRITER_QUEUE.get(timeout=0.04))
                except queue.Empty:
                    break
            try:
                grouped: Dict[str, List[str]] = {}
                for dst, line in batch:
                    grouped.setdefault(dst, []).append(line)
                for dst, lines in grouped.items():
                    try:
                        p = Path(dst)
                        p.parent.mkdir(parents=True, exist_ok=True)
                        if p.exists():
                            try:
                                if p.stat().st_size >= _ROTATE_MAX_BYTES:
                                    os.replace(p, p.with_name(p.name + ".1"))
                            except OSError:
                                pass
                        with open(p, "a", encoding="utf-8") as fh:
                            fh.write("\n".join(lines) + "\n")
                    except Exception:
                        pass
            finally:
                with _PENDING_LOCK:
                    _PENDING_COUNT = max(0, _PENDING_COUNT - len(batch))
        except Exception:
            time.sleep(0.4)


def _ensure_writer() -> None:
    global _WRITER_THREAD
    if _WRITER_THREAD is not None and _WRITER_THREAD.is_alive():
        return
    with _WRITER_LOCK:
        if _WRITER_THREAD is not None and _WRITER_THREAD.is_alive():
            return
        th = threading.Thread(target=_writer_loop, name="pm-stage-b-telemetry-writer", daemon=True)
        th.start()
        _WRITER_THREAD = th


def _enqueue_jsonl(dest: Path, record: Mapping[str, Any]) -> bool:
    global _PENDING_COUNT
    try:
        if not telemetry_enabled():
            return False
        line = _dumps_line(record)
        with _PENDING_LOCK:
            if _PENDING_COUNT >= _QUEUE_SOFT_CAP:
                return False
            _PENDING_COUNT += 1
        _ensure_writer()
        _WRITER_QUEUE.put((str(dest), line))
        return True
    except Exception:
        return False


def flush_stage_b_telemetry(timeout: float = 2.0) -> None:
    deadline = time.monotonic() + max(0.05, float(timeout))
    while time.monotonic() < deadline:
        with _PENDING_LOCK:
            if _PENDING_COUNT == 0:
                return
        time.sleep(0.02)


atexit.register(flush_stage_b_telemetry)


def emit_funnel_event(
    stage: str,
    *,
    sleeve: str,
    candidate_key: str = "",
    box_type: str = "",
    asset: str = "",
    net_edge_bps: Optional[float] = None,
    est_profit_usd: Optional[float] = None,
    notional_usd: Optional[float] = None,
    competitor_decay_ms: Optional[float] = None,
    reason: str = "",
    extra: Optional[Mapping[str, Any]] = None,
    dest_path: Optional[Path] = None,
) -> bool:
    """Appends one 6-stage Opportunity Funnel event non-blockingly."""
    try:
        st_u = str(stage or "").strip().upper()
        if st_u not in FUNNEL_STAGES:
            return False
        now_u = time.time()
        rec: Dict[str, Any] = {
            "ts_unix": round(now_u, 4),
            "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_u)),
            "stage": st_u,
            "sleeve": str(sleeve or "UNKNOWN").strip(),
            "candidate_key": str(candidate_key or "").strip(),
            "box_type": str(box_type or "").strip().upper(),
            "asset": str(asset or "").strip().upper(),
        }
        if net_edge_bps is not None:
            rec["net_edge_bps"] = round(_sf(net_edge_bps), 2)
        if est_profit_usd is not None:
            rec["est_profit_usd"] = round(_sf(est_profit_usd), 4)
        if notional_usd is not None:
            rec["notional_usd"] = round(_sf(notional_usd), 4)
        if competitor_decay_ms is not None:
            ms_v = max(0.0, _sf(competitor_decay_ms))
            rec["competitor_decay_ms"] = round(ms_v, 3)
            rec["decay_bucket"] = classify_decay_bucket(ms_v)
        if reason:
            rec["reason"] = str(reason)[:140]
        if extra:
            for k, v in extra.items():
                if k not in rec and v is not None:
                    rec[k] = v
        return _enqueue_jsonl(dest_path or funnel_log_path(), rec)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Sub-Millisecond O(1) Competitor Decay Tracker (`competitor_decay_ms`)
# ---------------------------------------------------------------------------

class CompetitorDecayTracker:
    """
    Watches live actionable arbs across 1-leg or 2-leg books and records the exact
    monotonic elapsed time (`competitor_decay_ms`) when a faster participant sweeps
    or reprices the L2 book above `max_cost_threshold` (or drains L1 size < `min_shares`).

    Hot-path cost when a token is NOT actively watched: single `token_id in self._by_token`
    dict membership check (< 100 ns, lock-free fast path).
    """

    def __init__(self, max_watches: int = 256, watch_ttl_sec: float = 30.0) -> None:
        self._lock = threading.Lock()
        self._watches: Dict[str, Dict[str, Any]] = {}
        self._by_token: Dict[str, Set[str]] = {}
        self._max_watches = max(16, int(max_watches))
        self._watch_ttl_sec = max(1.0, float(watch_ttl_sec))

    @property
    def active_watch_count(self) -> int:
        return len(self._watches)

    def register_watch(
        self,
        *,
        candidate_key: str,
        sleeve: str,
        token_ids: Sequence[str],
        initial_asks: Mapping[str, float],
        max_sum_ask: float,
        min_shares: float = 5.0,
        net_edge_bps: float = 0.0,
        est_profit_usd: float = 0.0,
        box_type: str = "",
        asset: str = "",
        detected_mono_ns: Optional[int] = None,
    ) -> bool:
        try:
            key = str(candidate_key or "").strip()
            toks = [str(t).strip() for t in token_ids if str(t or "").strip()]
            if not key or not toks:
                return False
            mono_ns = int(detected_mono_ns if detected_mono_ns is not None else time.perf_counter_ns())
            now_u = time.time()
            asks_state = {t: _sf(initial_asks.get(t), 0.0) for t in toks}
            if any(v <= 0.0 for v in asks_state.values()):
                return False
            with self._lock:
                if key in self._watches:
                    return False
                if len(self._watches) >= self._max_watches:
                    self._prune_expired_locked(now_u)
                    if len(self._watches) >= self._max_watches:
                        oldest_k = next(iter(self._watches))
                        self._remove_watch_locked(oldest_k)
                self._watches[key] = {
                    "candidate_key": key,
                    "sleeve": str(sleeve or "UNKNOWN"),
                    "box_type": str(box_type or ""),
                    "asset": str(asset or ""),
                    "tokens": tuple(toks),
                    "asks": asks_state,
                    "max_sum_ask": float(max_sum_ask),
                    "min_shares": max(1.0, float(min_shares)),
                    "net_edge_bps": float(net_edge_bps),
                    "est_profit_usd": float(est_profit_usd),
                    "detected_mono_ns": mono_ns,
                    "expires_unix": now_u + self._watch_ttl_sec,
                }
                for t in toks:
                    self._by_token.setdefault(t, set()).add(key)
            return True
        except Exception:
            return False

    def mark_our_fill_or_cancel(self, candidate_key: str) -> None:
        """Removes watch when WE capture the box ourselves so self-fills aren't miscounted as competitor sweeps."""
        if not candidate_key or candidate_key not in self._watches:
            return
        with self._lock:
            self._remove_watch_locked(str(candidate_key))

    def on_top_of_book_tick(
        self,
        token_id: str,
        best_ask: float,
        best_ask_shares: float,
        *,
        now_mono_ns: Optional[int] = None,
        dest_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """Fast O(1) check on incoming WS book ticks; emits `COMPETITOR_DECAY_OBSERVED` when cleared."""
        if not token_id or token_id not in self._by_token:
            return []
        fired: List[Dict[str, Any]] = []
        try:
            mono_ns = int(now_mono_ns if now_mono_ns is not None else time.perf_counter_ns())
            now_u = time.time()
            with self._lock:
                keys = list(self._by_token.get(token_id) or ())
                if not keys:
                    return []
                for k in keys:
                    w = self._watches.get(k)
                    if w is None:
                        continue
                    if now_u > float(w["expires_unix"]):
                        self._remove_watch_locked(k)
                        continue
                    ask_f = _sf(best_ask, 0.0)
                    sh_f = _sf(best_ask_shares, 0.0)
                    w["asks"][token_id] = ask_f if ask_f > 0.0 else 1.0
                    sum_asks = sum(float(x) for x in w["asks"].values())
                    book_cleared = (
                        ask_f <= 0.0
                        or sh_f < float(w["min_shares"])
                        or sum_asks > float(w["max_sum_ask"]) + 1e-6
                    )
                    if book_cleared:
                        decay_ms = max(0.01, (mono_ns - int(w["detected_mono_ns"])) / 1_000_000.0)
                        fired.append({
                            "candidate_key": k,
                            "sleeve": w["sleeve"],
                            "box_type": w["box_type"],
                            "asset": w["asset"],
                            "competitor_decay_ms": round(decay_ms, 3),
                            "decay_bucket": classify_decay_bucket(decay_ms),
                            "net_edge_bps": w["net_edge_bps"],
                            "est_profit_usd": w["est_profit_usd"],
                            "post_sum_ask": round(sum_asks, 4),
                            "post_ask_shares": round(sh_f, 2),
                        })
                        self._remove_watch_locked(k)
            for item in fired:
                emit_funnel_event(
                    "COMPETITOR_DECAY_OBSERVED",
                    sleeve=item["sleeve"],
                    candidate_key=item["candidate_key"],
                    box_type=item["box_type"],
                    asset=item["asset"],
                    net_edge_bps=item["net_edge_bps"],
                    est_profit_usd=item["est_profit_usd"],
                    competitor_decay_ms=item["competitor_decay_ms"],
                    reason=f"cleared_sum_ask={item['post_sum_ask']:.4f}_sh={item['post_ask_shares']:.1f}",
                    dest_path=dest_path,
                )
        except Exception:
            pass
        return fired

    def watched_token_ids(self, limit: int = 128) -> List[str]:
        """Returns active watched token IDs so Harvester Market WS stays subscribed to decay targets."""
        try:
            now_u = time.time()
            with self._lock:
                self._prune_expired_locked(now_u)
                return [str(t) for t in list(self._by_token.keys())[: max(1, int(limit))] if t]
        except Exception:
            return []

    def _prune_expired_locked(self, now_u: float) -> None:
        for k, w in list(self._watches.items()):
            if now_u > float(w.get("expires_unix") or 0.0):
                self._remove_watch_locked(k)

    def _remove_watch_locked(self, key: str) -> None:
        w = self._watches.pop(key, None)
        if not w:
            return
        for t in w.get("tokens") or ():
            s = self._by_token.get(t)
            if s is not None:
                s.discard(key)
                if not s:
                    self._by_token.pop(t, None)


GLOBAL_DECAY_TRACKER = CompetitorDecayTracker()


def register_candidate_funnel_and_decay_watch(
    cand: Mapping[str, Any],
    *,
    stage: str = "EXECUTABLE_NET_L2",
    emit_funnel: bool = True,
    dest_path: Optional[Path] = None,
    tracker: Optional[CompetitorDecayTracker] = None,
) -> None:
    """Extracts L2 candidate metadata from any live/shadow candidate dict and registers funnel + decay watch."""
    try:
        if not isinstance(cand, Mapping):
            return
        sleeve = str(cand.get("sleeve_source") or cand.get("sleeve") or "UNKNOWN").strip()
        b_type = str(cand.get("box_type") or "DOMINANCE").strip().upper()
        if b_type == "CLINCH_WATCHLIST_REG":
            return
        key = str(cand.get("box_id") or cand.get("dedupe_key") or "").strip()
        asset = str(cand.get("asset") or "").strip().upper()
        box_cost = _opt_float(
            cand.get("box_cost_net")
            or cand.get("cost_per_share")
            or cand.get("entry_eff_px")
            or cand.get("leg_a_limit_price")
        )
        sh = _sf(cand.get("net_paired_shares") or cand.get("shares") or cand.get("max_fillable_shares"), 10.0)
        edge_per_sh = _opt_float(cand.get("legging_adjusted_net_ev_per_pair") or cand.get("net_edge"))
        if edge_per_sh is None and box_cost is not None and 0.0 < box_cost < 1.0:
            edge_per_sh = max(0.0, 1.0 - box_cost)
        edge_bps = round((edge_per_sh or 0.0) * 10000.0, 2)
        est_prof = round((edge_per_sh or 0.0) * max(1.0, sh), 4)
        notional = round((box_cost or 0.98) * max(1.0, sh), 4)

        if emit_funnel:
            if stage == "EXECUTABLE_NET_L2":
                emit_funnel_event(
                    "GROSS_ARB_SEEN",
                    sleeve=sleeve,
                    candidate_key=key,
                    box_type=b_type,
                    asset=asset,
                    net_edge_bps=edge_bps,
                    est_profit_usd=est_prof,
                    notional_usd=notional,
                    dest_path=dest_path,
                )
            emit_funnel_event(
                stage,
                sleeve=sleeve,
                candidate_key=key,
                box_type=b_type,
                asset=asset,
                net_edge_bps=edge_bps,
                est_profit_usd=est_prof,
                notional_usd=notional,
                dest_path=dest_path,
            )

        trk = tracker or GLOBAL_DECAY_TRACKER
        tok_a = str(cand.get("leg_a_token_id") or cand.get("token_id") or "").strip()
        tok_b = str(cand.get("leg_b_token_id") or "").strip()
        px_a = _opt_float(cand.get("leg_a_limit_price") or cand.get("ask_px"))
        px_b = _opt_float(cand.get("leg_b_limit_price"))
        max_cap = _sf(cand.get("max_box_cost_net") or cand.get("max_lock_eff_px"), 0.992)
        raw_legs = cand.get("legs") or cand.get("no_legs")
        if isinstance(raw_legs, Sequence) and not isinstance(raw_legs, (str, bytes)) and len(raw_legs) >= 2:
            leg_toks: List[str] = []
            init_asks: Dict[str, float] = {}
            for lg in raw_legs[:12]:
                if isinstance(lg, Mapping):
                    lt = str(lg.get("token_id") or "").strip()
                    lp = _opt_float(lg.get("ask_px") or lg.get("limit_price") or lg.get("price"))
                    if lt and lp and lp > 0.0:
                        leg_toks.append(lt)
                        init_asks[lt] = lp
            if len(leg_toks) >= 2:
                sum_init = sum(init_asks.values())
                trk.register_watch(
                    candidate_key=key or f"{sleeve}:{leg_toks[0][:10]}:{int(time.time()*1000)}",
                    sleeve=sleeve,
                    token_ids=leg_toks,
                    initial_asks=init_asks,
                    max_sum_ask=max(sum_init, min(max(0.998, sum_init + 0.004), max_cap if max_cap > sum_init else sum_init + 0.003)),
                    min_shares=max(5.0, min(sh, 8.0)),
                    net_edge_bps=edge_bps,
                    est_profit_usd=est_prof,
                    box_type=b_type,
                    asset=asset,
                )
                return
        if tok_a and tok_b and px_a and px_b:
            trk.register_watch(
                candidate_key=key or f"{sleeve}:{tok_a[:10]}:{int(time.time()*1000)}",
                sleeve=sleeve,
                token_ids=(tok_a, tok_b),
                initial_asks={tok_a: px_a, tok_b: px_b},
                max_sum_ask=max(px_a + px_b, min(0.998, max_cap)),
                min_shares=max(5.0, min(sh, 8.0)),
                net_edge_bps=edge_bps,
                est_profit_usd=est_prof,
                box_type=b_type,
                asset=asset,
            )
        elif tok_a and b_type == "SINGLE_LEG_MAKER_LOCK":
            ws_bks = cand.get("ws_books")
            ask_ws = None
            if isinstance(ws_bks, Mapping) and isinstance(ws_bks.get(tok_a), Mapping):
                asks_l = ws_bks[tok_a].get("asks") or []
                for a_it in asks_l:
                    ap = _sf(a_it.get("price") if isinstance(a_it, Mapping) else (a_it[0] if isinstance(a_it, (list, tuple)) and a_it else 0.0))
                    asz = _sf(a_it.get("size") if isinstance(a_it, Mapping) else (a_it[1] if isinstance(a_it, (list, tuple)) and len(a_it) > 1 else 0.0))
                    if ap > 0.0 and asz > 0.0 and (ask_ws is None or ap < ask_ws):
                        ask_ws = ap
            if ask_ws is not None and 0.50 <= ask_ws < 0.999:
                trk.register_watch(
                    candidate_key=key or f"{sleeve}:{tok_a[:10]}:{int(time.time()*1000)}",
                    sleeve=sleeve,
                    token_ids=(tok_a,),
                    initial_asks={tok_a: ask_ws},
                    max_sum_ask=min(0.999, max(ask_ws, _sf(cand.get("max_resting_bid") or max_cap, 0.9975))),
                    min_shares=5.0,
                    net_edge_bps=edge_bps,
                    est_profit_usd=est_prof,
                    box_type=b_type,
                    asset=asset,
                )
        elif tok_a and px_a and b_type not in {"DOMINANCE_MAKER_ANCHOR", "ZERO_FEE_MAKER_ANCHOR"}:
            trk.register_watch(
                candidate_key=key or f"{sleeve}:{tok_a[:10]}:{int(time.time()*1000)}",
                sleeve=sleeve,
                token_ids=(tok_a,),
                initial_asks={tok_a: px_a},
                max_sum_ask=min(0.999, max(px_a, _sf(cand.get("max_box_cost_net") or cand.get("max_lock_eff_px"), 0.9975))),
                min_shares=5.0,
                net_edge_bps=edge_bps,
                est_profit_usd=est_prof,
                box_type=b_type,
                asset=asset,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Post-Fill Multi-Horizon Adverse Markout Sampler (+1s / +5s / +30s)
# ---------------------------------------------------------------------------

def extract_book_mid_price(book: Optional[Mapping[str, Any]]) -> Optional[float]:
    if not isinstance(book, Mapping):
        return None
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    best_b = 0.0
    best_a = 0.0
    for b in bids:
        px = _sf(b.get("price") if isinstance(b, Mapping) else (b[0] if isinstance(b, (list, tuple)) and b else 0.0))
        sz = _sf(b.get("size") if isinstance(b, Mapping) else (b[1] if isinstance(b, (list, tuple)) and len(b) > 1 else 0.0))
        if px > best_b and sz > 0.0:
            best_b = px
    for a in asks:
        px = _sf(a.get("price") if isinstance(a, Mapping) else (a[0] if isinstance(a, (list, tuple)) and a else 0.0))
        sz = _sf(a.get("size") if isinstance(a, Mapping) else (a[1] if isinstance(a, (list, tuple)) and len(a) > 1 else 0.0))
        if px > 0.0 and sz > 0.0 and (best_a == 0.0 or px < best_a):
            best_a = px
    if best_b > 0.0 and best_a > 0.0 and best_b <= best_a:
        return round(0.5 * (best_b + best_a), 5)
    if best_b > 0.0:
        return round(best_b, 5)
    if best_a > 0.0:
        return round(best_a, 5)
    return None


def compute_signed_markout_cents(side: str, ref_px: float, future_mid: Optional[float]) -> Optional[float]:
    """
    Signed markout in cents/share:
      - BUY at `ref_px`:  `+100 * (future_mid - ref_px)` (< 0 means price moved against our passive bid)
      - SELL at `ref_px`: `+100 * (ref_px - future_mid)` (< 0 means price rallied through our passive ask)
    """
    if future_mid is None or ref_px <= 0.0:
        return None
    sgn = -1.0 if str(side or "BUY").strip().upper() == "SELL" else 1.0
    return round(sgn * (float(future_mid) - float(ref_px)) * 100.0, 4)


class MakerMarkoutSampler:
    """Non-blocking min-heap timer thread sampling +1s, +5s, and +30s mid-prices after Maker fills."""

    HORIZONS_SEC: Tuple[float, ...] = (1.0, 5.0, 30.0)

    def __init__(self, max_inflight: int = 256) -> None:
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._heap: List[Tuple[float, int, float, Dict[str, Any]]] = []
        self._seq = 0
        self._max_inflight = max(16, int(max_inflight))
        self._thread: Optional[threading.Thread] = None

    def schedule_maker_fill(
        self,
        *,
        order_id: str,
        token_id: str,
        sleeve: str,
        side: str,
        fill_px: float,
        shares: float,
        book_lookup_fn: Callable[[str], Optional[Mapping[str, Any]]],
        trade_id: str = "",
        mid_at_fill: Optional[float] = None,
        horizons_sec: Sequence[float] = HORIZONS_SEC,
        dest_path: Optional[Path] = None,
    ) -> bool:
        try:
            if not telemetry_enabled() or not token_id or fill_px <= 0.0 or shares <= 0.0 or not callable(book_lookup_fn):
                return False
            hz_sorted = tuple(sorted(float(h) for h in horizons_sec if float(h) > 0.0))
            if not hz_sorted:
                return False
            init_mid = mid_at_fill
            if init_mid is None:
                try:
                    init_mid = extract_book_mid_price(book_lookup_fn(str(token_id)))
                except Exception:
                    init_mid = None
            now_mono = time.monotonic()
            now_u = time.time()
            ctx: Dict[str, Any] = {
                "order_id": str(order_id or ""),
                "trade_id": str(trade_id or ""),
                "token_id": str(token_id),
                "sleeve": str(sleeve or "UNKNOWN"),
                "side": str(side or "BUY").upper(),
                "fill_px": round(float(fill_px), 5),
                "shares": round(float(shares), 4),
                "mid_t0": init_mid if init_mid is not None else round(float(fill_px), 5),
                "fill_unix": round(now_u, 3),
                "book_lookup_fn": book_lookup_fn,
                "horizons": hz_sorted,
                "samples": {},
                "dest_path": dest_path,
            }
            with self._lock:
                if len(self._heap) >= self._max_inflight * len(hz_sorted):
                    return False
                self._seq += 1
                heapq.heappush(self._heap, (now_mono + hz_sorted[0], self._seq, hz_sorted[0], ctx))
                self._ensure_thread_locked()
            self._wake.set()
            return True
        except Exception:
            return False

    def _ensure_thread_locked(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        th = threading.Thread(target=self._run_loop, name="pm-maker-markout-sampler", daemon=True)
        th.start()
        self._thread = th

    def _run_loop(self) -> None:
        while True:
            try:
                with self._lock:
                    if not self._heap:
                        wait_s = 2.0
                        due_item = None
                    else:
                        now_m = time.monotonic()
                        if self._heap[0][0] <= now_m:
                            due_item = heapq.heappop(self._heap)
                            wait_s = 0.0
                        else:
                            due_item = None
                            wait_s = min(1.0, max(0.005, self._heap[0][0] - now_m))
                if due_item is None:
                    self._wake.wait(timeout=wait_s)
                    self._wake.clear()
                    continue
                _, _, hz, ctx = due_item
                mid_now: Optional[float] = None
                try:
                    bk = ctx["book_lookup_fn"](ctx["token_id"])
                    mid_now = extract_book_mid_price(bk)
                except Exception:
                    mid_now = None
                hz_key = f"{int(hz)}s" if float(hz).is_integer() else f"{hz:.2f}s"
                ctx["samples"][hz_key] = {
                    "mid": mid_now,
                    "vs_fill_cents": compute_signed_markout_cents(ctx["side"], ctx["fill_px"], mid_now),
                    "mid_drift_cents": compute_signed_markout_cents(ctx["side"], ctx["mid_t0"], mid_now),
                }
                hz_list: Tuple[float, ...] = ctx["horizons"]
                idx_cur = hz_list.index(hz)
                if idx_cur + 1 < len(hz_list):
                    nxt_hz = hz_list[idx_cur + 1]
                    due_next = time.monotonic() + max(0.005, nxt_hz - hz)
                    with self._lock:
                        self._seq += 1
                        heapq.heappush(self._heap, (due_next, self._seq, nxt_hz, ctx))
                else:
                    self._emit_completed_sample(ctx)
            except Exception:
                time.sleep(0.25)

    def _emit_completed_sample(self, ctx: Mapping[str, Any]) -> None:
        samples = ctx.get("samples") or {}
        hz_list: Tuple[float, ...] = tuple(ctx.get("horizons") or ())
        def _hz_lbl(h: float) -> str:
            return f"{int(h)}s" if float(h).is_integer() else f"{h:.2f}s"
        s1 = samples.get("1s") or (samples.get(_hz_lbl(hz_list[0])) if len(hz_list) >= 1 else None) or {}
        s5 = samples.get("5s") or (samples.get(_hz_lbl(hz_list[1])) if len(hz_list) >= 2 else None) or {}
        s30 = samples.get("30s") or (samples.get(_hz_lbl(hz_list[2])) if len(hz_list) >= 3 else None) or {}
        sh = _sf(ctx.get("shares"), 0.0)
        m5_c = s5.get("vs_fill_cents")
        m30_c = s30.get("vs_fill_cents")
        rec = {
            "ts_unix": round(time.time(), 3),
            "fill_unix": ctx.get("fill_unix"),
            "order_id": ctx.get("order_id"),
            "trade_id": ctx.get("trade_id"),
            "sleeve": ctx.get("sleeve"),
            "token_id": ctx.get("token_id"),
            "side": ctx.get("side"),
            "fill_px": ctx.get("fill_px"),
            "mid_t0": ctx.get("mid_t0"),
            "shares": sh,
            "mid_1s": s1.get("mid"),
            "mid_5s": s5.get("mid"),
            "mid_30s": s30.get("mid"),
            "markout_1s_cents": s1.get("vs_fill_cents"),
            "markout_5s_cents": m5_c,
            "markout_30s_cents": m30_c,
            "mid_drift_1s_cents": s1.get("mid_drift_cents"),
            "mid_drift_5s_cents": s5.get("mid_drift_cents"),
            "mid_drift_30s_cents": s30.get("mid_drift_cents"),
            "adverse_markout_5s_usd": round(min(0.0, (_sf(m5_c) / 100.0) * sh), 4) if m5_c is not None else None,
            "adverse_markout_30s_usd": round(min(0.0, (_sf(m30_c) / 100.0) * sh), 4) if m30_c is not None else None,
            "samples": samples,
        }
        _enqueue_jsonl(ctx.get("dest_path") or markout_log_path(), rec)


GLOBAL_MARKOUT_SAMPLER = MakerMarkoutSampler()


# ---------------------------------------------------------------------------
# Reconciled Per-Sleeve & Portfolio Economic Attribution Aggregator
# ---------------------------------------------------------------------------

def is_partial_basket_unwind_record(rec: Mapping[str, Any]) -> bool:
    if not isinstance(rec, Mapping):
        return False
    if bool(rec.get("is_legged_out_residual")):
        return True
    btype_u = str(rec.get("box_type") or "").upper()
    if btype_u in {"MULTI_LEG_RESIDUAL", "CTF_OVERROUND_RESIDUAL"}:
        return True
    tid_u = str(rec.get("trade_id") or "").upper()
    if "_LEG_INLINE_UNWIND" in tid_u or "_LEG_RESID" in tid_u or "_UNWRESID_" in tid_u:
        return True
    rsn_u = str(rec.get("close_reason") or rec.get("unwind_reason") or rec.get("status") or "").upper()
    return any(tok in rsn_u for tok in PARTIAL_UNWIND_REASON_TOKENS)


def _fallback_hold_hours_for_sleeve(sleeve: str, rec: Mapping[str, Any]) -> float:
    sl_u = str(sleeve or "").upper()
    tte_s = _sf(rec.get("entry_tte"), 0.0)
    if tte_s > 0.0:
        return max(1.0 / 60.0, min(72.0, tte_s / 3600.0))
    if sl_u.startswith("D1_") or sl_u.startswith("S2_") or "SUBHOURLY" in sl_u:
        return 0.20
    if sl_u.startswith("BOND1") or sl_u.startswith("BOND2"):
        return 2.15
    if sl_u.startswith("MKR_LOCK1") or sl_u.startswith("W_PRUNE1") or sl_u.startswith("MKR_REWARD"):
        return 0.75
    return 1.25


def estimate_position_hold_hours(rec: Mapping[str, Any], *, now_unix: Optional[float] = None, is_open: bool = False) -> float:
    t_in = _parse_ts(rec.get("entry_ts") or rec.get("entry_time_utc") or rec.get("submitted_at_ts"))
    if is_open:
        now_u = float(now_unix if now_unix is not None else time.time())
        if t_in is not None and now_u >= t_in:
            return max(1.0 / 60.0, min(720.0, (now_u - t_in) / 3600.0))
        return 0.25
    t_out = _parse_ts(
        rec.get("exit_ts")
        or rec.get("closed_at_ts")
        or rec.get("settled_at_utc")
        or rec.get("exit_time_utc")
    )
    if t_in is not None and t_out is not None and t_out >= t_in:
        return max(1.0 / 60.0, min(720.0, (t_out - t_in) / 3600.0))
    return _fallback_hold_hours_for_sleeve(str(rec.get("sleeve") or ""), rec)


def _percentile(sorted_vals: Sequence[float], pct: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return round(float(sorted_vals[0]), 2)
    rank = (max(0.0, min(100.0, float(pct))) / 100.0) * (len(sorted_vals) - 1)
    lo = int(math.floor(rank))
    hi = min(len(sorted_vals) - 1, lo + 1)
    frac = rank - lo
    return round(float(sorted_vals[lo]) * (1.0 - frac) + float(sorted_vals[hi]) * frac, 2)


def _tail_jsonl(path: Optional[Path], max_bytes: int = 524288, max_lines: int = 1200) -> List[Dict[str, Any]]:
    if path is None or not Path(path).exists():
        return []
    p = Path(path)
    out: List[Dict[str, Any]] = []
    try:
        with p.open("rb") as fh:
            fh.seek(0, 2)
            sz = fh.tell()
            off = max(0, sz - max_bytes)
            fh.seek(off, 0)
            raw = fh.read().decode("utf-8", errors="replace").splitlines()
        if off > 0 and raw:
            raw = raw[1:]
        for ln in raw[-max_lines:]:
            s = ln.strip()
            if not s.startswith("{"):
                continue
            try:
                obj = _orjson.loads(s) if _orjson is not None else json.loads(s)
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                continue
    except Exception:
        return []
    return out


def compute_stage_b_attribution_report(
    *,
    grouped_closed: Iterable[Mapping[str, Any]],
    active_positions: Optional[Mapping[str, Any]] = None,
    reconciled_equity_usd: float = 0.0,
    starting_lock_equity_usd: float = DEFAULT_RISKLESS_LOCK_START_EQUITY_USD,
    net_deposits_post_lock_usd: float = 0.0,
    riskless_epoch_start_utc: str = DEFAULT_RISKLESS_LOCK_START_UTC,
    equity_24h_delta_usd: Optional[float] = None,
    vm_hourly_cost_usd: float = DEFAULT_VM_HOURLY_COST_USD,
    daily_infra_cost_usd: Optional[float] = None,
    all_time_ai_cost_usd: float = 0.0,
    daily_ai_cost_usd: float = 0.0,
    accounting_discrepancy_usd: float = 0.0,
    orphan_orders_count: int = 0,
    paused_sleeves: Optional[Iterable[str]] = None,
    funnel_records: Optional[Sequence[Mapping[str, Any]]] = None,
    markout_records: Optional[Sequence[Mapping[str, Any]]] = None,
    latency_records: Optional[Sequence[Mapping[str, Any]]] = None,
    order_records: Optional[Sequence[Mapping[str, Any]]] = None,
    candidate_records: Optional[Sequence[Mapping[str, Any]]] = None,
    data_dir: Optional[Path] = None,
    now_unix: Optional[float] = None,
    eu_vm_monthly_delta_usd: float = 12.0,
) -> Dict[str, Any]:
    """
    Computes the complete Stage B Reconciled Economic Attribution Book, 6-Stage Opportunity Funnel,
    4-Bucket Competitor Decay Distribution, Maker Post-Fill Adverse Markouts, and all 10 North-Star KPIs.
    """
    now_u = float(now_unix if now_unix is not None else time.time())
    d_dir = Path(data_dir) if data_dir is not None else None
    paused_set = {str(x).strip().upper() for x in (paused_sleeves or ()) if x}

    if funnel_records is None and d_dir is not None:
        funnel_records = _tail_jsonl(funnel_log_path(d_dir))
    if markout_records is None and d_dir is not None:
        markout_records = _tail_jsonl(markout_log_path(d_dir))
    if latency_records is None and d_dir is not None:
        latency_records = _tail_jsonl(d_dir / "latency_trace.jsonl")
    if order_records is None and d_dir is not None:
        order_records = _tail_jsonl(d_dir / "live_orders.jsonl")
    if candidate_records is None and d_dir is not None:
        candidate_records = _tail_jsonl(d_dir / "d1_live_box_candidates.jsonl", max_bytes=393216, max_lines=600)

    funnel_list = list(funnel_records or ())
    markout_list = list(markout_records or ())
    lat_list = list(latency_records or ())
    ord_list = list(order_records or ())
    cand_list = list(candidate_records or ())

    # 1. Per-Sleeve & Pure-Riskless Reconciled Economic Attribution Book (Zero Double-Counting)
    by_sleeve: Dict[str, Dict[str, Any]] = {}

    def _ensure_sl(sl_name: str) -> Dict[str, Any]:
        if sl_name not in by_sleeve:
            sl_u = sl_name.upper()
            is_rl = sl_u not in UNHEDGED_DIRECTIONAL_SLEEVES and sl_u not in paused_set
            by_sleeve[sl_name] = {
                "sleeve": sl_name,
                "is_active_riskless": is_rl,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "flat_merges": 0,
                "open_positions": 0,
                "notional_usd": 0.0,
                "gross_capture_usd": 0.0,
                "taker_fees_usd": 0.0,
                "paid_maker_rebates_usd": 0.0,
                "est_unsettled_rebates_usd": 0.0,
                "paid_rewards_usd": 0.0,
                "partial_basket_unwind_loss_usd": 0.0,
                "partial_basket_unwind_count": 0,
                "gas_usd": 0.0,
                "net_pnl_usd": 0.0,
                "expected_edge_usd": 0.0,
                "expected_edge_measured_pnl_usd": 0.0,
                "occupied_capital_hours": 0.0,
                "active_capital_hours": 0.0,
                "markout_5s_cents_samples": [],
                "markout_30s_cents_samples": [],
                "adverse_markout_5s_usd": 0.0,
                "adverse_markout_30s_usd": 0.0,
            }
        return by_sleeve[sl_name]

    tot_rl_notional = 0.0
    tot_rl_net_pnl = 0.0
    tot_rl_gross_capture = 0.0
    tot_rl_fees = 0.0
    tot_rl_paid_rebates = 0.0
    tot_rl_est_rebates = 0.0
    tot_rl_paid_rewards = 0.0
    tot_rl_unwind_loss = 0.0
    tot_rl_unwind_cnt = 0
    tot_rl_gas = 0.0
    tot_rl_cap_hrs = 0.0
    tot_all_net_pnl = 0.0
    tot_all_notional = 0.0
    tot_all_cap_hrs = 0.0
    tot_exp_edge_usd = 0.0
    tot_realized_on_exp_usd = 0.0

    for g in grouped_closed or ():
        if not isinstance(g, Mapping):
            continue
        sl = str(g.get("sleeve") or "UNKNOWN").strip()
        rec_s = _ensure_sl(sl)
        pnl = _sf(g.get("net_pnl_usd", g.get("realized_pnl_usd", 0.0)))
        notional = max(0.0, _sf(g.get("notional_usd")))
        is_grouped_box = int(_sf(g.get("box_leg_count"), 1)) > 1
        fee = max(
            0.0,
            _sf(g.get("fee_usd")) if is_grouped_box else (_sf(g.get("fee_usd")) + _sf(g.get("realized_exit_fee"))),
        )
        paid_reb = max(0.0, _sf(g.get("paid_maker_rebate_usd")))
        est_reb = max(0.0, _sf(g.get("est_maker_rebate_usd")))
        paid_rew = max(0.0, _sf(g.get("paid_liquidity_reward_usd")) + _sf(g.get("paid_holding_reward_usd")))
        gas_u = max(0.0, _sf(g.get("gas_usd")))
        rsn_u = str(g.get("close_reason") or g.get("status") or "").strip().upper()
        is_flat = abs(pnl) < 0.005 and (rsn_u in BENIGN_FLAT_MERGE_REASONS or "MERGED" in rsn_u)
        is_unwind = is_partial_basket_unwind_record(g)

        # Additive decomposition preserving exact penny identity for ALL combinations of rebates/rewards/gas:
        #   gross_capture - normal_taker_fees - partial_basket_unwind_loss + paid_reb + paid_rew - gas == pnl
        if is_unwind and pnl < 0.0:
            raw_unwind = -pnl + paid_reb + paid_rew - gas_u
            if raw_unwind >= 0.0:
                unwind_loss = raw_unwind
                normal_fee = 0.0
                gross_cap = 0.0
            else:
                unwind_loss = 0.0
                normal_fee = 0.0
                gross_cap = -raw_unwind
            rec_s["partial_basket_unwind_count"] += 1
        else:
            unwind_loss = 0.0
            normal_fee = fee
            gross_cap = pnl + normal_fee + gas_u - paid_reb - paid_rew

        hold_h = estimate_position_hold_hours(g, now_unix=now_u, is_open=False)
        cap_h = notional * hold_h

        # Expected edge at entry vs realized net PnL (for KPI #7 Expected vs Realized Edge Capture %)
        sh_g = _sf(g.get("entry_shares"), 0.0)
        box_cost_g = _opt_float(g.get("box_cost_net"))
        exp_edge = _opt_float(g.get("expected_net_profit_usd") or g.get("expected_edge_usd"))
        if exp_edge is None and not is_flat:
            if box_cost_g is not None and 0.50 <= box_cost_g < 1.0 and sh_g > 0.0:
                exp_edge = max(0.0, (1.0 - box_cost_g) * sh_g)
            elif bool(g.get("hold_to_maturity_lock")) and sh_g > 0.0 and notional > 0.0 and sh_g > notional:
                exp_edge = max(0.0, sh_g - notional - fee)

        if is_flat:
            rec_s["flat_merges"] += 1
        else:
            rec_s["trades"] += 1
            if pnl >= -1e-6:
                rec_s["wins"] += 1
            else:
                rec_s["losses"] += 1

        rec_s["notional_usd"] += notional
        rec_s["gross_capture_usd"] += gross_cap
        rec_s["taker_fees_usd"] += normal_fee
        rec_s["paid_maker_rebates_usd"] += paid_reb
        rec_s["est_unsettled_rebates_usd"] += est_reb
        rec_s["paid_rewards_usd"] += paid_rew
        rec_s["partial_basket_unwind_loss_usd"] += unwind_loss
        rec_s["gas_usd"] += gas_u
        rec_s["net_pnl_usd"] += pnl
        rec_s["occupied_capital_hours"] += cap_h

        if exp_edge is not None and exp_edge > 0.001:
            rec_s["expected_edge_usd"] += exp_edge
            rec_s["expected_edge_measured_pnl_usd"] += pnl

        tot_all_net_pnl += pnl
        tot_all_notional += notional
        tot_all_cap_hrs += cap_h

        if rec_s["is_active_riskless"]:
            tot_rl_notional += notional
            tot_rl_net_pnl += pnl
            tot_rl_gross_capture += gross_cap
            tot_rl_fees += normal_fee
            tot_rl_paid_rebates += paid_reb
            tot_rl_est_rebates += est_reb
            tot_rl_paid_rewards += paid_rew
            tot_rl_unwind_loss += unwind_loss
            if is_unwind and pnl < 0.0:
                tot_rl_unwind_cnt += 1
            tot_rl_gas += gas_u
            tot_rl_cap_hrs += cap_h
            if exp_edge is not None and exp_edge > 0.001:
                tot_exp_edge_usd += exp_edge
                tot_realized_on_exp_usd += pnl

    for _, p_open in (active_positions or {}).items():
        if not isinstance(p_open, Mapping):
            continue
        sl_o = str(p_open.get("sleeve") or "UNKNOWN").strip()
        rec_o = _ensure_sl(sl_o)
        rec_o["open_positions"] += 1
        not_o = max(0.0, _sf(p_open.get("remaining_cost_basis", p_open.get("notional_usd", 0.0))))
        hold_o = estimate_position_hold_hours(p_open, now_unix=now_u, is_open=True)
        rec_o["active_capital_hours"] += not_o * hold_o

    # 2. Maker Post-Fill Adverse Markout Aggregation (1s / 5s / 30s)
    m1_all: List[float] = []
    m5_all: List[float] = []
    m30_all: List[float] = []
    d5_all: List[float] = []
    d30_all: List[float] = []
    tot_adv_5s_usd = 0.0
    tot_adv_30s_usd = 0.0
    for mr in markout_list:
        sl_m = str(mr.get("sleeve") or "UNKNOWN").strip()
        rec_m = _ensure_sl(sl_m)
        c1 = _opt_float(mr.get("markout_1s_cents"))
        c5 = _opt_float(mr.get("markout_5s_cents"))
        c30 = _opt_float(mr.get("markout_30s_cents"))
        dr5 = _opt_float(mr.get("mid_drift_5s_cents"))
        dr30 = _opt_float(mr.get("mid_drift_30s_cents"))
        adv5 = _sf(mr.get("adverse_markout_5s_usd"), 0.0)
        adv30 = _sf(mr.get("adverse_markout_30s_usd"), 0.0)
        if c1 is not None:
            m1_all.append(c1)
        if c5 is not None:
            m5_all.append(c5)
            rec_m["markout_5s_cents_samples"].append(c5)
        if c30 is not None:
            m30_all.append(c30)
            rec_m["markout_30s_cents_samples"].append(c30)
        if dr5 is not None:
            d5_all.append(dr5)
        if dr30 is not None:
            d30_all.append(dr30)
        rec_m["adverse_markout_5s_usd"] += adv5
        rec_m["adverse_markout_30s_usd"] += adv30
        tot_adv_5s_usd += adv5
        tot_adv_30s_usd += adv30

    sleeves_out: List[Dict[str, Any]] = []
    for sl_name, r in by_sleeve.items():
        not_s = r["notional_usd"]
        cap_s = r["occupied_capital_hours"]
        pnl_s = r["net_pnl_usd"]
        exp_s = r["expected_edge_usd"]
        m5_s = r.pop("markout_5s_cents_samples")
        m30_s = r.pop("markout_30s_cents_samples")
        r["notional_usd"] = round(not_s, 2)
        r["gross_capture_usd"] = round(r["gross_capture_usd"], 4)
        r["taker_fees_usd"] = round(r["taker_fees_usd"], 4)
        r["paid_maker_rebates_usd"] = round(r["paid_maker_rebates_usd"], 4)
        r["est_unsettled_rebates_usd"] = round(r["est_unsettled_rebates_usd"], 4)
        r["paid_rewards_usd"] = round(r["paid_rewards_usd"], 4)
        r["partial_basket_unwind_loss_usd"] = round(r["partial_basket_unwind_loss_usd"], 4)
        r["gas_usd"] = round(r["gas_usd"], 4)
        r["net_pnl_usd"] = round(pnl_s, 4)
        r["occupied_capital_hours"] = round(cap_s, 3)
        r["active_capital_hours"] = round(r["active_capital_hours"], 3)
        r["adverse_markout_5s_usd"] = round(r["adverse_markout_5s_usd"], 4)
        r["adverse_markout_30s_usd"] = round(r["adverse_markout_30s_usd"], 4)
        r["avg_markout_5s_cents"] = round(sum(m5_s) / len(m5_s), 3) if m5_s else None
        r["avg_markout_30s_cents"] = round(sum(m30_s) / len(m30_s), 3) if m30_s else None
        r["net_pnl_per_1000_usd"] = round(1000.0 * pnl_s / not_s, 2) if not_s >= 1.0 else 0.0
        r["net_pnl_per_capital_hour_usd"] = round(pnl_s / cap_s, 4) if cap_s >= 0.01 else 0.0
        r["bps_per_capital_hour"] = round(10000.0 * pnl_s / cap_s, 1) if cap_s >= 0.01 else 0.0
        r["expected_vs_realized_pct"] = (
            round(100.0 * r["expected_edge_measured_pnl_usd"] / exp_s, 1) if exp_s >= 0.005 else None
        )
        r.pop("expected_edge_usd", None)
        r.pop("expected_edge_measured_pnl_usd", None)
        sleeves_out.append(r)

    sleeves_out.sort(
        key=lambda x: (
            0 if x["is_active_riskless"] else 1,
            -float(x["net_pnl_usd"]),
            -int(x["open_positions"]),
        )
    )

    # 3. Signal-to-Ack Hot-Path Latency Distribution (p50 / p95 / p99 ms)
    sig_to_ack_samples: List[float] = []
    http_post_samples: List[float] = []
    ipc_samples: List[float] = []
    for lr in lat_list:
        fok_ms = _opt_float(lr.get("fok_box_ms"))
        ipc_ms = _opt_float(lr.get("ipc_age_ms"))
        stamps = lr.get("stamps_rel_ms") if isinstance(lr.get("stamps_rel_ms"), Mapping) else {}
        http_done = _opt_float(stamps.get("http_done") or stamps.get("emit"))
        if fok_ms is not None and 0.5 <= fok_ms <= 15000.0:
            tot_ms = fok_ms + max(0.0, _sf(ipc_ms)) + max(0.0, _sf(lr.get("book_walk_ms")))
            sig_to_ack_samples.append(tot_ms)
            http_post_samples.append(fok_ms)
        elif http_done is not None and 1.0 <= http_done <= 15000.0:
            sig_to_ack_samples.append(http_done)
        if ipc_ms is not None and 0.0 <= ipc_ms <= 5000.0:
            ipc_samples.append(ipc_ms)

    for or_rec in ord_list:
        _det_o = or_rec.get("details") if isinstance(or_rec.get("details"), Mapping) else {}
        _lat_o = _det_o.get("latency_telemetry") if isinstance(_det_o.get("latency_telemetry"), Mapping) else {}
        ms_o = _opt_float(
            or_rec.get("clob_http_post_ms")
            if or_rec.get("clob_http_post_ms") is not None
            else (
                _lat_o.get("clob_http_post_ms")
                if _lat_o.get("clob_http_post_ms") is not None
                else or_rec.get("latency_ms")
            )
        )
        if ms_o is not None and 1.0 <= ms_o <= 15000.0:
            http_post_samples.append(ms_o)
            if len(sig_to_ack_samples) < 25:
                sig_to_ack_samples.append(ms_o)

    sig_to_ack_samples.sort()
    http_post_samples.sort()
    ipc_samples.sort()

    # 4. 6-Stage Opportunity Funnel + 4-Bucket Competitor Decay Curve
    stage_counts: Dict[str, int] = {k: 0 for k in FUNNEL_STAGES}
    decay_counts: Dict[str, int] = {k: 0 for k in DECAY_BUCKETS}
    decay_missed_usd: Dict[str, float] = {k: 0.0 for k in DECAY_BUCKETS}
    decay_ms_samples: List[float] = []
    recent_funnel_rows: List[Dict[str, Any]] = []

    for fr in funnel_list:
        st_f = str(fr.get("stage") or "").strip().upper()
        if st_f in stage_counts:
            stage_counts[st_f] += 1
        if st_f == "COMPETITOR_DECAY_OBSERVED":
            dms = _opt_float(fr.get("competitor_decay_ms"))
            if dms is not None and dms >= 0.0:
                bkt = str(fr.get("decay_bucket") or classify_decay_bucket(dms))
                if bkt not in decay_counts:
                    bkt = classify_decay_bucket(dms)
                decay_counts[bkt] += 1
                decay_missed_usd[bkt] += max(0.0, _sf(fr.get("est_profit_usd")))
                decay_ms_samples.append(dms)

    for fr in reversed(funnel_list[-20:]):
        recent_funnel_rows.append({
            "ts_unix": fr.get("ts_unix"),
            "ts_utc": fr.get("ts_utc"),
            "stage": fr.get("stage"),
            "sleeve": fr.get("sleeve"),
            "asset": fr.get("asset"),
            "candidate_key": fr.get("candidate_key"),
            "net_edge_bps": fr.get("net_edge_bps"),
            "est_profit_usd": fr.get("est_profit_usd"),
            "competitor_decay_ms": fr.get("competitor_decay_ms"),
            "decay_bucket": fr.get("decay_bucket"),
            "reason": fr.get("reason"),
        })

    # Baseline enrichment from existing live telemetry when `opportunity_funnel.jsonl` is freshly initialized
    # or when pre-patch historical fills exist before `ORDER_SUBMITTED` / `COMPLETE_BASKET_LOCKED` instrumentation.
    funnel_backfilled = False
    hist_locked_cnt = sum(int(r["wins"]) for r in sleeves_out if r["is_active_riskless"])
    if sum(stage_counts.values()) == 0 and (cand_list or ord_list or grouped_closed):
        funnel_backfilled = True
        stage_counts["EXECUTABLE_NET_L2"] = len(cand_list)
        stage_counts["GROSS_ARB_SEEN"] = max(len(cand_list), len(ord_list))
        stage_counts["ORDER_SUBMITTED"] = len(ord_list)
        stage_counts["COMPLETE_BASKET_LOCKED"] = hist_locked_cnt
        stage_counts["PARTIAL_BASKET_UNWOUND"] = tot_rl_unwind_cnt
    elif stage_counts["ORDER_SUBMITTED"] == 0 and (ord_list or hist_locked_cnt > 0 or tot_rl_unwind_cnt > 0):
        funnel_backfilled = True
        stage_counts["ORDER_SUBMITTED"] = max(stage_counts["ORDER_SUBMITTED"], len(ord_list), hist_locked_cnt + tot_rl_unwind_cnt)
        stage_counts["COMPLETE_BASKET_LOCKED"] = max(stage_counts["COMPLETE_BASKET_LOCKED"], hist_locked_cnt)
        stage_counts["PARTIAL_BASKET_UNWOUND"] = max(stage_counts["PARTIAL_BASKET_UNWOUND"], tot_rl_unwind_cnt)

    if stage_counts["EXECUTABLE_NET_L2"] < stage_counts["ORDER_SUBMITTED"]:
        stage_counts["EXECUTABLE_NET_L2"] = max(stage_counts["EXECUTABLE_NET_L2"], len(cand_list), stage_counts["ORDER_SUBMITTED"])
    if stage_counts["GROSS_ARB_SEEN"] < stage_counts["EXECUTABLE_NET_L2"]:
        stage_counts["GROSS_ARB_SEEN"] = stage_counts["EXECUTABLE_NET_L2"]

    decay_ms_samples.sort()
    tot_decay_obs = sum(decay_counts.values())
    gt40_share_pct = round(100.0 * decay_counts["gt_40ms"] / tot_decay_obs, 1) if tot_decay_obs > 0 else None
    missed_15_40_usd = round(decay_missed_usd["15_40ms"], 2)

    # Estimate observation span for monthlyizing Rung-2 trigger (`15-40ms missed net profit > 5x monthly VM delta`)
    funnel_ts = [float(x["ts_unix"]) for x in funnel_list if _opt_float(x.get("ts_unix")) is not None]
    obs_days = max(1.0, (max(funnel_ts) - min(funnel_ts)) / 86400.0) if len(funnel_ts) >= 2 else 1.0
    proj_monthly_15_40_usd = round(missed_15_40_usd * (30.0 / obs_days), 2) if tot_decay_obs >= 10 else 0.0
    rung2_trigger_threshold_usd = round(5.0 * max(1.0, float(eu_vm_monthly_delta_usd)), 2)
    rung2_proximity_triggered = bool(tot_decay_obs >= 25 and proj_monthly_15_40_usd >= rung2_trigger_threshold_usd)

    # 5. Governing Wallet-to-Wallet Net Economic Identity
    lock_start_ts = _parse_ts(riskless_epoch_start_utc)
    lock_elapsed_hours = max(1.0, (now_u - lock_start_ts) / 3600.0) if (lock_start_ts and now_u > lock_start_ts) else 24.0
    daily_infra_u = float(daily_infra_cost_usd) if daily_infra_cost_usd is not None else round(24.0 * float(vm_hourly_cost_usd), 4)
    prorated_lock_infra_usd = round(lock_elapsed_hours * float(vm_hourly_cost_usd), 4)
    prorated_lock_ops_usd = round(prorated_lock_infra_usd + float(all_time_ai_cost_usd), 4)

    has_wallet_eq = reconciled_equity_usd > 0.0
    wallet_delta_post_lock_usd = (
        round(float(reconciled_equity_usd) - float(starting_lock_equity_usd) - float(net_deposits_post_lock_usd), 4)
        if has_wallet_eq
        else round(tot_rl_net_pnl, 4)
    )
    net_economic_pnl_post_lock_usd = round(wallet_delta_post_lock_usd - prorated_lock_ops_usd, 4)

    net_economic_24h_usd: Optional[float] = None
    if equity_24h_delta_usd is not None:
        net_economic_24h_usd = round(float(equity_24h_delta_usd) - daily_infra_u - float(daily_ai_cost_usd), 4)

    # KPI #2, #3, #5, #7, #8, #9, #10
    rl_pnl_per_1000 = round(1000.0 * tot_rl_net_pnl / tot_rl_notional, 2) if tot_rl_notional >= 1.0 else 0.0
    rl_pnl_per_cap_hr = round(tot_rl_net_pnl / tot_rl_cap_hrs, 4) if tot_rl_cap_hrs >= 0.01 else 0.0
    rl_bps_per_cap_hr = round(10000.0 * tot_rl_net_pnl / tot_rl_cap_hrs, 1) if tot_rl_cap_hrs >= 0.01 else 0.0

    avg_m5_c = round(sum(m5_all) / len(m5_all), 3) if m5_all else None
    avg_m30_c = round(sum(m30_all) / len(m30_all), 3) if m30_all else None
    avg_drift_5_c = round(sum(d5_all) / len(d5_all), 3) if d5_all else None

    exp_vs_real_pct = (
        round(100.0 * tot_realized_on_exp_usd / tot_exp_edge_usd, 1)
        if tot_exp_edge_usd >= 0.01
        else (100.0 if tot_rl_net_pnl > 0.0 else None)
    )
    infra_to_gross_pct = (
        round(100.0 * prorated_lock_ops_usd / wallet_delta_post_lock_usd, 1)
        if wallet_delta_post_lock_usd > 0.01
        else None
    )

    # Verify additive ledger identity discrepancy across closed trades (must be 0.0000)
    additive_check_pnl = (
        tot_rl_gross_capture
        - tot_rl_fees
        - tot_rl_unwind_loss
        + tot_rl_paid_rebates
        + tot_rl_paid_rewards
        - tot_rl_gas
    )
    internal_identity_gap_usd = round(abs(additive_check_pnl - tot_rl_net_pnl), 6)

    north_star_kpis = {
        "kpi_1_net_economic_pnl_usd": round(net_economic_pnl_post_lock_usd, 2),
        "kpi_1_wallet_gain_before_ops_usd": round(wallet_delta_post_lock_usd, 2),
        "kpi_1_prorated_ops_cost_usd": round(prorated_lock_ops_usd, 2),
        "kpi_1_net_economic_24h_usd": round(net_economic_24h_usd, 2) if net_economic_24h_usd is not None else None,
        "kpi_2_net_pnl_per_1000_usd": rl_pnl_per_1000,
        "kpi_3_net_pnl_per_capital_hour_usd": rl_pnl_per_cap_hr,
        "kpi_3_bps_per_capital_hour": rl_bps_per_cap_hr,
        "kpi_3_occupied_capital_hours": round(tot_rl_cap_hrs, 2),
        "kpi_4_partial_basket_unwind_loss_usd": round(tot_rl_unwind_loss, 4),
        "kpi_4_partial_basket_unwind_count": tot_rl_unwind_cnt,
        "kpi_5_maker_markout_5s_cents": avg_m5_c,
        "kpi_5_maker_markout_30s_cents": avg_m30_c,
        "kpi_5_mid_drift_5s_cents": avg_drift_5_c,
        "kpi_5_markout_samples": len(m5_all),
        "kpi_6_signal_to_ack_p50_ms": _percentile(sig_to_ack_samples, 50.0),
        "kpi_6_signal_to_ack_p95_ms": _percentile(sig_to_ack_samples, 95.0),
        "kpi_6_signal_to_ack_p99_ms": _percentile(sig_to_ack_samples, 99.0),
        "kpi_6_http_post_p50_ms": _percentile(http_post_samples, 50.0),
        "kpi_6_ipc_p50_ms": _percentile(ipc_samples, 50.0),
        "kpi_7_expected_vs_realized_capture_pct": exp_vs_real_pct,
        "kpi_8_infra_burn_to_gross_profit_pct": infra_to_gross_pct,
        "kpi_8_daily_infra_burn_usd": round(daily_infra_u + float(daily_ai_cost_usd), 3),
        "kpi_9_competitor_decay_median_ms": _percentile(decay_ms_samples, 50.0),
        "kpi_9_finland_capturable_gt40ms_pct": gt40_share_pct,
        "kpi_9_decay_samples": tot_decay_obs,
        "kpi_10_wallet_accounting_discrepancy_usd": round(abs(float(accounting_discrepancy_usd)), 4),
        "kpi_10_orphan_orders_count": int(orphan_orders_count),
        "kpi_10_internal_identity_gap_usd": internal_identity_gap_usd,
    }

    return {
        "schema_version": "stage_b_v1.0",
        "computed_at_unix": round(now_u, 3),
        "governing_identity": {
            "starting_reconciled_equity_usd": round(float(starting_lock_equity_usd), 2),
            "ending_reconciled_equity_usd": round(float(reconciled_equity_usd), 2),
            "net_deposits_usd": round(float(net_deposits_post_lock_usd), 2),
            "contributed_capital_basis_usd": round(float(starting_lock_equity_usd) + float(net_deposits_post_lock_usd), 2),
            "wallet_equity_delta_usd": round(wallet_delta_post_lock_usd, 4),
            "prorated_vm_infra_cost_usd": prorated_lock_infra_usd,
            "ai_research_cost_usd": round(float(all_time_ai_cost_usd), 4),
            "net_economic_pnl_usd": net_economic_pnl_post_lock_usd,
            "lock_elapsed_hours": round(lock_elapsed_hours, 2),
            "vm_hourly_cost_usd": round(float(vm_hourly_cost_usd), 4),
            "pure_riskless_strategy_pnl_usd": round(tot_rl_net_pnl, 4),
            "all_time_reconciled_strategy_pnl_usd": round(tot_all_net_pnl, 4),
            "internal_identity_gap_usd": internal_identity_gap_usd,
        },
        "north_star_kpis": north_star_kpis,
        "opportunity_funnel": {
            "backfilled_baseline": funnel_backfilled,
            "stages": stage_counts,
            "decay_buckets": {
                "counts": decay_counts,
                "missed_profit_usd": {k: round(v, 4) for k, v in decay_missed_usd.items()},
                "median_ms": _percentile(decay_ms_samples, 50.0),
                "p25_ms": _percentile(decay_ms_samples, 25.0),
                "p75_ms": _percentile(decay_ms_samples, 75.0),
                "gt_40ms_capturable_pct": gt40_share_pct,
                "rung2_eu_proximity_missed_15_40ms_monthly_proj_usd": proj_monthly_15_40_usd,
                "rung2_trigger_threshold_usd": rung2_trigger_threshold_usd,
                "rung2_migration_justified": rung2_proximity_triggered,
            },
            "recent_events": recent_funnel_rows,
        },
        "maker_markouts": {
            "samples_count": len(m5_all),
            "avg_1s_cents": round(sum(m1_all) / len(m1_all), 3) if m1_all else None,
            "avg_5s_cents": avg_m5_c,
            "avg_30s_cents": avg_m30_c,
            "avg_mid_drift_5s_cents": avg_drift_5_c,
            "adverse_markout_5s_usd": round(tot_adv_5s_usd, 4),
            "adverse_markout_30s_usd": round(tot_adv_30s_usd, 4),
        },
        "portfolio_totals": {
            "pure_riskless_notional_usd": round(tot_rl_notional, 2),
            "pure_riskless_gross_capture_usd": round(tot_rl_gross_capture, 4),
            "pure_riskless_taker_fees_usd": round(tot_rl_fees, 4),
            "pure_riskless_paid_rebates_usd": round(tot_rl_paid_rebates, 4),
            "pure_riskless_est_unsettled_rebates_usd": round(tot_rl_est_rebates, 4),
            "pure_riskless_paid_rewards_usd": round(tot_rl_paid_rewards, 4),
            "pure_riskless_unwind_loss_usd": round(tot_rl_unwind_loss, 4),
            "pure_riskless_gas_usd": round(tot_rl_gas, 4),
            "pure_riskless_net_pnl_usd": round(tot_rl_net_pnl, 4),
            "pure_riskless_occupied_capital_hours": round(tot_rl_cap_hrs, 3),
            "all_time_notional_usd": round(tot_all_notional, 2),
            "all_time_occupied_capital_hours": round(tot_all_cap_hrs, 3),
        },
        "by_sleeve": sleeves_out,
    }

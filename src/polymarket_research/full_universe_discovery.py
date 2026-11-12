"""
Exhaustive Observable Polymarket Universe Discovery, Incremental SQLite Registry &
Two-Layer Surveillance Engine (`src/polymarket_research/full_universe_discovery.py`).

DOMINUS — RISKLESS FULL THROTTLE (Agents 2 & 10: Universe Discovery & Surveillance).

Design & Safety Invariants:
  1. Strict Mode 1 (Research) / Mode 2 (Shadow) public read-only operation:
     - Connects ONLY to `https://gamma-api.polymarket.com` and `https://clob.polymarket.com`.
     - Zero private credentials, zero order placement, zero touches on protected files.
  2. `D-001` Frozen KMIA Protection:
     - Markets `6707502` and `6707503` (and any market with `umaResolutionStatus == "disputed"`)
       are retained for 100% discovery completeness while explicitly marked ineligible for
       execution via `KMIA_D001_PROTECTED_LOCK` and `UMA_DISPUTED_FROZEN`.
  3. `D-010` Swapless Host Memory Envelope (`< 120 MiB` Peak RSS):
     - Uses `@dataclass(slots=True)` models, streaming page-by-page `/events/keyset`
       (`after_cursor=...`) normalization, per-page SQLite primary-key digest diffing,
       compact bounded L2 snapshots, and optional Linux `libc.malloc_trim(0)`.
  4. Strict Separation of Discovery Completeness (`100%`) vs. Execution Eligibility:
     - Zero arbitrary volume, liquidity, category, fee-regime, or top-N exclusions at discovery.
     - Every non-tradable, paused, placeholder, disputed, disabled-book, or empty-book
       instrument/market is preserved in `FullUniverseRegistry` with machine-readable `skip_codes`.
  5. Two-Layer Surveillance (`TwoLayerSurveillanceScheduler`):
     - Layer A: Persistent round-robin full-universe sweep cursor so low-priority / quiet
       markets never starve or disappear from surveillance.
     - Layer B: High-priority adaptive book polling via batched `POST /books` (`<= 500` tokens
       per request; default `450`) over persistent HTTP/1.1 keep-alive connections with explicit
       rate-limit budgeting and per-token staleness tracking.
"""

from __future__ import annotations

import collections
import ctypes
import gc
import gzip
import hashlib
import heapq
import http.client
import json
import math
import os
import re
import sqlite3
import ssl
import sys
import threading
import time
import tracemalloc
import urllib.parse
import zlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

try:
    import orjson as _orjson  # type: ignore
except ImportError:
    _orjson = None


GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
ALLOWED_PUBLIC_HOSTS: frozenset[str] = frozenset({"gamma-api.polymarket.com", "clob.polymarket.com"})

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_UNIVERSE_DIR = REPO_ROOT / "data" / "universe"
DEFAULT_REGISTRY_DB_PATH = DEFAULT_UNIVERSE_DIR / "market_registry.sqlite3"
DEFAULT_COVERAGE_SNAPSHOT_PATH = DEFAULT_UNIVERSE_DIR / "coverage_snapshot.json"

# Binding D-001 frozen disputed KMIA Nov 7 market IDs (100% non-interference)
KMIA_D001_FROZEN_MARKET_IDS: frozenset[str] = frozenset({"6707502", "6707503"})

# CLOB server-enforced ceiling is 500 tokens per POST /books (550 returns HTTP 400)
CLOB_BOOKS_MAX_BATCH_SIZE = 500
CLOB_BOOKS_DEFAULT_BATCH_SIZE = 450


class SkipReason(str, Enum):
    """Explicit machine-readable execution-eligibility & caution skip codes."""

    ORDERBOOK_DISABLED = "ORDERBOOK_DISABLED"
    NOT_ACCEPTING_ORDERS = "NOT_ACCEPTING_ORDERS"
    MISSING_TOKEN_IDS = "MISSING_TOKEN_IDS"
    MISSING_CONDITION_ID = "MISSING_CONDITION_ID"
    CLOSED_OR_ARCHIVED = "CLOSED_OR_ARCHIVED"
    INACTIVE_OR_PAUSED = "INACTIVE_OR_PAUSED"
    AUGMENTED_PLACEHOLDER_OUTCOME = "AUGMENTED_PLACEHOLDER_OUTCOME"
    AUGMENTED_OTHER_MUTABLE_OUTCOME = "AUGMENTED_OTHER_MUTABLE_OUTCOME"
    UMA_DISPUTED_FROZEN = "UMA_DISPUTED_FROZEN"
    KMIA_D001_PROTECTED_LOCK = "KMIA_D001_PROTECTED_LOCK"
    UMA_PROPOSED_SETTLEMENT_STAGE = "UMA_PROPOSED_SETTLEMENT_STAGE"
    PAST_END_DATE_UNRESOLVED = "PAST_END_DATE_UNRESOLVED"
    ZERO_RESTING_DEPTH = "ZERO_RESTING_DEPTH"
    ONE_SIDED_BOOK = "ONE_SIDED_BOOK"
    STALE_BOOK = "STALE_BOOK"
    NON_STANDARD_OUTCOME_ARITY = "NON_STANDARD_OUTCOME_ARITY"


# Hard execution blockers (instrument/market cannot be directly executed as standard live CLOB legs)
HARD_EXECUTION_BLOCK_CODES: frozenset[str] = frozenset(
    {
        SkipReason.ORDERBOOK_DISABLED.value,
        SkipReason.NOT_ACCEPTING_ORDERS.value,
        SkipReason.MISSING_TOKEN_IDS.value,
        SkipReason.MISSING_CONDITION_ID.value,
        SkipReason.CLOSED_OR_ARCHIVED.value,
        SkipReason.INACTIVE_OR_PAUSED.value,
        SkipReason.AUGMENTED_PLACEHOLDER_OUTCOME.value,
        SkipReason.UMA_DISPUTED_FROZEN.value,
        SkipReason.KMIA_D001_PROTECTED_LOCK.value,
    }
)

# Unnamed placeholder patterns in augmented NegRisk events (`Person A`, `Candidate B`, `Player X`, `Option 1`, `Placeholder`)
_PLACEHOLDER_OUTCOME_RE = re.compile(
    r"^(?:"
    r"placeholder(?:\s*[-_#]?\s*[a-z0-9]+)?|"
    r"(?:person|candidate|player|team|company|party|nominee|contender|option|choice|item|outcome|slot|entity|coach|driver|club|country|movie|film|song|artist|game)\s+[a-z0-9]{1,3}|"
    r"tbd(?:\s*\d+)?|unnamed(?:\s*[-_#]?\s*[a-z0-9]+)?"
    r")$",
    re.IGNORECASE,
)

_OTHER_OUTCOME_RE = re.compile(
    r"^(?:other|others|any\s+other(?:\s+\w+){0,3}|field|all\s+other(?:\s+\w+){0,2}|none\s+of\s+the\s+above)$",
    re.IGNORECASE,
)

# Category & ladder classification regexes for structural breakdown
_STRIKE_OR_THRESHOLD_RE = re.compile(
    r"(?:\babove\b|\bbelow\b|\breach\b|\bhit\b|\bdip\s+to\b|\bover\b|\bunder\b|\bbetween\b|[<>]=?|\$\d+(?:[.,]\d+)?\s*[kmbtr]?)",
    re.IGNORECASE,
)
_TEMPORAL_DEADLINE_RE = re.compile(
    r"\b(?:by|before|in|on|prior\s+to)\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|q[1-4]\s*20\d{2}|202[5-9])\b",
    re.IGNORECASE,
)


def _json_loads(raw: bytes | str) -> Any:
    if _orjson is not None:
        return _orjson.loads(raw)
    if isinstance(raw, bytes):
        try:
            return json.loads(raw)
        except UnicodeDecodeError:
            return json.loads(raw.decode("utf-8", errors="replace"))
    return json.loads(raw)


def _json_dumps_str(obj: Any) -> str:
    if _orjson is not None:
        return _orjson.dumps(obj).decode("utf-8")
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _release_unused_heap_memory() -> None:
    """Runs Python cyclic GC and invokes glibc `malloc_trim(0)` on Linux (`D-010`)."""
    gc.collect()
    if sys.platform.startswith("linux"):
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except Exception:
            pass


def get_process_rss_mib() -> float:
    """Returns current OS resident set size (MiB) on Linux/Windows, with tracemalloc fallback."""
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as fp:
                for line in fp:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            return round(float(parts[1]) / 1024.0, 2)
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            get_cur = kernel32.GetCurrentProcess
            get_cur.argtypes = []
            get_cur.restype = wintypes.HANDLE
            handle = get_cur()
            get_mem = getattr(kernel32, "K32GetProcessMemoryInfo", None)
            if get_mem is None:
                psapi = ctypes.WinDLL("psapi", use_last_error=True)
                get_mem = psapi.GetProcessMemoryInfo
            get_mem.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
            get_mem.restype = wintypes.BOOL
            if get_mem(handle, ctypes.byref(pmc), pmc.cb):
                return round(float(pmc.WorkingSetSize) / (1024.0 * 1024.0), 2)
        except Exception:
            pass
    if tracemalloc.is_tracing():
        cur_b, _ = tracemalloc.get_traced_memory()
        return round(float(cur_b) / (1024.0 * 1024.0), 2)
    return 0.0


def parse_iso_timestamp(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        fv = float(val)
        return fv / 1000.0 if fv > 1e11 else (fv if fv > 0 else None)
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        elif " " in s and "T" not in s:
            s = s.replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    except Exception:
        return None


def _parse_str_tuple(raw: Any) -> Tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return ()
        if s.startswith("["):
            try:
                parsed = _json_loads(s)
                if isinstance(parsed, list):
                    return tuple(str(x).strip() for x in parsed if x is not None and str(x).strip())
            except Exception:
                return ()
        return (s,)
    if isinstance(raw, (list, tuple)):
        out: List[str] = []
        for item in raw:
            if isinstance(item, Mapping):
                lbl = str(item.get("slug") or item.get("label") or item.get("name") or "").strip()
                if lbl:
                    out.append(lbl)
            elif item is not None:
                s_i = str(item).strip()
                if s_i:
                    out.append(s_i)
        return tuple(out)
    return ()


def _parse_float_tuple(raw: Any) -> Tuple[float, ...]:
    if raw is None:
        return ()
    seq: Any = raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s or not s.startswith("["):
            return ()
        try:
            seq = _json_loads(s)
        except Exception:
            return ()
    if isinstance(seq, (list, tuple)):
        out: List[float] = []
        for x in seq:
            try:
                v = float(x)
                out.append(v if math.isfinite(v) else 0.0)
            except Exception:
                out.append(0.0)
        return tuple(out)
    return ()


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        fv = float(val)
        return fv if math.isfinite(fv) else default
    except Exception:
        return default


def is_valid_hex_condition_id(cid: str) -> bool:
    s = str(cid or "").strip()
    if len(s) != 66 or not s.startswith("0x"):
        return False
    return all(ch in "0123456789abcdefABCDEF" for ch in s[2:])


def detect_placeholder_or_other_outcome(
    *,
    question: str,
    group_item_title: str,
    market_slug: str,
    neg_risk: bool,
    neg_risk_augmented: bool,
    neg_risk_other_flag: bool,
    active: bool,
    enable_order_book: bool,
) -> Tuple[bool, bool]:
    """
    Returns `(is_augmented_placeholder, is_other_outcome)` for NegRisk / multi-outcome markets.
    - `is_augmented_placeholder`: True for unnamed placeholder slots (`Person A`, `Option X`, `Placeholder_*`)
      or inactive unclarified sub-slots inside an augmented NegRisk slate.
    - `is_other_outcome`: True when `negRiskOther == True` or group/question label denotes catch-all `"Other"`.
    """
    lbl = (group_item_title or "").strip()
    q_clean = (question or "").strip()
    slug_l = (market_slug or "").strip().lower()

    is_other = bool(neg_risk_other_flag)
    if not is_other and (neg_risk or neg_risk_augmented):
        if lbl and _OTHER_OUTCOME_RE.match(lbl):
            is_other = True
        elif slug_l.endswith("-other") and (not lbl or "other" in lbl.lower()):
            is_other = True

    is_placeholder = False
    if lbl and _PLACEHOLDER_OUTCOME_RE.match(lbl):
        is_placeholder = True
    elif "placeholder" in slug_l or re.search(r"-(?:person|candidate|player|option)-[a-z0-9]$", slug_l):
        if neg_risk or neg_risk_augmented:
            is_placeholder = True
    elif neg_risk_augmented and not is_other and (not active or not enable_order_book):
        if not lbl or re.search(r"\b(?:placeholder|unnamed|tbd)\b", q_clean, re.IGNORECASE):
            is_placeholder = True

    return is_placeholder, is_other


def infer_primary_category(tags: Sequence[str], event_slug: str, title: str) -> str:
    """Normalizes primary domain category from Gamma tags + slug/title tokens."""
    tag_set = {t.lower().strip() for t in tags if t}
    txt = f"{event_slug} {title}".lower()

    if tag_set & {
        "sports", "nba", "nfl", "nhl", "mlb", "soccer", "football", "tennis", "esports",
        "ufc", "mma", "golf", "f1", "cricket", "basketball", "baseball", "hockey", "ncaa", "cfb",
    } or re.search(r"\b(?:nba|nfl|nhl|mlb|ufc|epl|uefa|premier-league|ATP|WTA|bo3|counter-strike|dota)\b", txt):
        return "sports"
    if "weather" in tag_set or re.search(r"\b(?:highest-temperature|lowest-temperature|precipitation|hurricane|snowfall)\b", txt):
        return "weather"
    if tag_set & {"crypto", "bitcoin", "ethereum", "solana", "defi", "memecoins"} or re.search(
        r"\b(?:bitcoin|btc|ethereum|eth|solana|sol|xrp|dogecoin|doge|fdv|airdrop|token)\b", txt
    ):
        return "crypto"
    if tag_set & {"politics", "elections", "us-elections", "midterms", "trump", "congress", "senate"} or re.search(
        r"\b(?:election|senate|governor|president|parliament|prime-minister|democrat|republican|midterm)\b", txt
    ):
        return "politics"
    if tag_set & {"geopolitics", "world", "ukraine", "middle-east", "china", "russia"} or re.search(
        r"\b(?:ceasefire|invasion|nato|military|tariff|sanction|israel|iran|ukraine|taiwan)\b", txt
    ):
        return "geopolitics"
    if tag_set & {"economics", "fed", "macro", "finance", "stocks", "equities", "commodities", "oil"} or re.search(
        r"\b(?:fomc|interest-rate|inflation|cpi|gdp|recession|ipo|s&p|nasdaq|crude-oil|gold|silver)\b", txt
    ):
        return "macro_finance"
    if tag_set & {"tech", "ai", "science", "space"} or re.search(
        r"\b(?:openai|gpt|claude|gemini|anthropic|spacex|apple|nvidia|microsoft|meta|tesla)\b", txt
    ):
        return "tech_ai"
    if tag_set & {"pop-culture", "culture", "entertainment", "movies", "music", "awards"} or re.search(
        r"\b(?:oscars|grammy|box-office|spotify|billboard|tweet|elon-musk)\b", txt
    ):
        return "culture_media"
    if tags:
        return str(tags[0]).lower()
    return "uncategorized"


# ===========================================================================
# Rate-Limit Budget & Persistent Keep-Alive Public HTTPS Client
# ===========================================================================


@dataclass(slots=True)
class RateLimitBudget:
    """Sliding-window request budget preventing HTTP 429 bursts on Gamma & CLOB APIs."""

    max_requests_per_window: int = 120
    window_sec: float = 10.0
    min_interval_sec: float = 0.0
    _timestamps: Deque[float] = field(default_factory=collections.deque, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    throttled_sleep_sec_total: float = 0.0
    total_requests: int = 0

    def acquire(self, now_fn: Callable[[], float] = time.monotonic, sleep_fn: Callable[[float], None] = time.sleep) -> float:
        slept = 0.0
        while True:
            wait_for = 0.0
            with self._lock:
                now = now_fn()
                cutoff = now - self.window_sec
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()
                if self.min_interval_sec > 0.0 and self._timestamps:
                    gap = (self._timestamps[-1] + self.min_interval_sec) - now
                    if gap > 0.0:
                        wait_for = max(wait_for, gap)
                if len(self._timestamps) >= self.max_requests_per_window:
                    oldest = self._timestamps[0]
                    wait_for = max(wait_for, (oldest + self.window_sec) - now + 0.005)
                if wait_for <= 0.0:
                    self._timestamps.append(now)
                    self.total_requests += 1
                    self.throttled_sleep_sec_total += slept
                    return slept
            sleep_fn(min(wait_for, 1.0))
            slept += min(wait_for, 1.0)


class PersistentJsonHttpClient:
    """
    Zero-dependency stdlib HTTP/1.1 keep-alive JSON client (`http.client.HTTPSConnection`)
    with gzip decompression, TLS session reuse, sliding-window rate-limit budgeting,
    and strict host allowlisting (`gamma-api.polymarket.com` & `clob.polymarket.com`).
    """

    def __init__(
        self,
        *,
        timeout_sec: float = 15.0,
        max_retries: int = 3,
        gamma_budget: Optional[RateLimitBudget] = None,
        clob_budget: Optional[RateLimitBudget] = None,
        requester_override: Optional[Callable[[str, str, Optional[bytes]], Tuple[int, Any]]] = None,
    ) -> None:
        self.timeout_sec = float(timeout_sec)
        self.max_retries = max(1, int(max_retries))
        self.gamma_budget = gamma_budget or RateLimitBudget(max_requests_per_window=160, window_sec=10.0)
        self.clob_budget = clob_budget or RateLimitBudget(max_requests_per_window=90, window_sec=10.0)
        self._requester_override = requester_override
        self._ssl_ctx = ssl.create_default_context()
        self._pool: Dict[str, List[http.client.HTTPSConnection]] = collections.defaultdict(list)
        self._pool_lock = threading.Lock()
        self.stats: Counter[str] = Counter()

    def _checkout(self, host: str) -> http.client.HTTPSConnection:
        if host not in ALLOWED_PUBLIC_HOSTS:
            raise ValueError(f"Disallowed host outside public Mode 1/2 boundary: {host!r}")
        with self._pool_lock:
            conns = self._pool[host]
            if conns:
                return conns.pop()
        return http.client.HTTPSConnection(host, timeout=self.timeout_sec, context=self._ssl_ctx)

    def _checkin(self, host: str, conn: http.client.HTTPSConnection) -> None:
        with self._pool_lock:
            if len(self._pool[host]) < 8:
                self._pool[host].append(conn)
                return
        try:
            conn.close()
        except Exception:
            pass

    def close(self) -> None:
        with self._pool_lock:
            for conns in self._pool.values():
                for c in conns:
                    try:
                        c.close()
                    except Exception:
                        pass
            self._pool.clear()

    def request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: Any = None,
    ) -> Tuple[int, Any]:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower()
        if host not in ALLOWED_PUBLIC_HOSTS:
            raise ValueError(f"Disallowed host outside public Mode 1/2 boundary: {host!r}")

        body_bytes: Optional[bytes] = None
        if json_body is not None:
            body_bytes = _orjson.dumps(json_body) if _orjson is not None else _json_dumps_str(json_body).encode("utf-8")

        budget = self.gamma_budget if "gamma-api" in host else self.clob_budget
        budget.acquire()

        if self._requester_override is not None:
            status, payload = self._requester_override(method.upper(), url, body_bytes)
            self.stats[f"http_{status}"] += 1
            return status, payload

        path_and_query = parsed.path or "/"
        if parsed.query:
            path_and_query = f"{path_and_query}?{parsed.query}"

        headers = {
            "User-Agent": "DominusFullUniverseDiscovery/2.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        if body_bytes is not None:
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(body_bytes))

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            conn = self._checkout(host)
            try:
                conn.request(method.upper(), path_and_query, body=body_bytes, headers=headers)
                resp = conn.getresponse()
                status = int(resp.status)
                raw = resp.read()
                enc = (resp.getheader("Content-Encoding") or "").lower()
                conn_hdr = (resp.getheader("Connection") or "").lower()
                if "close" in conn_hdr:
                    conn.close()
                else:
                    self._checkin(host, conn)

                self.stats[f"http_{status}"] += 1
                if status in (429, 500, 502, 503, 504) and attempt + 1 < self.max_retries:
                    backoff = min(4.0, 0.35 * (2 ** attempt))
                    self.stats["retries"] += 1
                    time.sleep(backoff)
                    continue

                if not raw:
                    return status, None
                if enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    raw = zlib.decompress(raw)
                try:
                    return status, _json_loads(raw)
                except Exception:
                    return status, raw.decode("utf-8", errors="replace")
            except Exception as exc:
                last_exc = exc
                self.stats["socket_reconnects"] += 1
                try:
                    conn.close()
                except Exception:
                    pass
                if attempt + 1 < self.max_retries:
                    time.sleep(min(2.0, 0.2 * (2 ** attempt)))
        raise RuntimeError(f"{method} {url} failed after {self.max_retries} attempts: {last_exc}")


# ===========================================================================
# Normalized Compact Domain Models (`@dataclass(slots=True)`)
# ===========================================================================


@dataclass(slots=True)
class NormalizedBookSnapshot:
    """Normalized CLOB L2 order-book snapshot with top-N bounded depth for `<120 MiB` safety."""

    token_id: str
    bids: Tuple[Tuple[float, float], ...]
    asks: Tuple[Tuple[float, float], ...]
    best_bid: float
    best_bid_size: float
    best_ask: float
    best_ask_size: float
    resting_bid_depth_usd: float
    resting_ask_depth_usd: float
    tick_size: float
    min_order_size: float
    fetched_ts: float
    exchange_ts_ms: int = 0
    market_condition_id: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.bids and not self.asks

    @property
    def is_one_sided(self) -> bool:
        return bool(self.bids) != bool(self.asks)

    @property
    def is_two_sided(self) -> bool:
        return bool(self.bids) and bool(self.asks)

    def to_clob_dict(self) -> Dict[str, Any]:
        """Drop-in CLOB `/books` dict shape compatible with all peer detectors."""
        return {
            "asset_id": self.token_id,
            "market": self.market_condition_id,
            "bids": [{"price": f"{px:.4f}".rstrip("0").rstrip(".") or "0", "size": f"{sz:.4f}"} for px, sz in self.bids],
            "asks": [{"price": f"{px:.4f}".rstrip("0").rstrip(".") or "0", "size": f"{sz:.4f}"} for px, sz in self.asks],
            "minimum_tick_size": str(self.tick_size),
            "tick_size": str(self.tick_size),
            "min_order_size": str(self.min_order_size),
            "timestamp": str(self.exchange_ts_ms or int(self.fetched_ts * 1000)),
            "_fetched_ts": self.fetched_ts,
        }

    @classmethod
    def from_clob_dict(
        cls,
        raw: Mapping[str, Any],
        *,
        fetched_ts: Optional[float] = None,
        max_levels: int = 25,
    ) -> "NormalizedBookSnapshot":
        now_f = float(time.time() if fetched_ts is None else fetched_ts)
        tid = str(raw.get("asset_id") or raw.get("token_id") or "").strip()
        raw_bids = raw.get("bids") or ()
        raw_asks = raw.get("asks") or ()

        parsed_bids: List[Tuple[float, float]] = []
        for b in raw_bids:
            if isinstance(b, Mapping):
                px = _safe_float(b.get("price"), 0.0)
                sz = _safe_float(b.get("size"), 0.0)
            elif isinstance(b, (list, tuple)) and len(b) >= 2:
                px = _safe_float(b[0], 0.0)
                sz = _safe_float(b[1], 0.0)
            else:
                continue
            if 0.0 < px < 1.0 and sz > 0.0:
                parsed_bids.append((round(px, 6), round(sz, 6)))
        parsed_bids.sort(key=lambda kv: kv[0], reverse=True)

        parsed_asks: List[Tuple[float, float]] = []
        for a in raw_asks:
            if isinstance(a, Mapping):
                px = _safe_float(a.get("price"), 0.0)
                sz = _safe_float(a.get("size"), 0.0)
            elif isinstance(a, (list, tuple)) and len(a) >= 2:
                px = _safe_float(a[0], 0.0)
                sz = _safe_float(a[1], 0.0)
            else:
                continue
            if 0.0 < px <= 1.0 and sz > 0.0:
                parsed_asks.append((round(px, 6), round(sz, 6)))
        parsed_asks.sort(key=lambda kv: kv[0])

        bid_depth_usd = round(sum(px * sz for px, sz in parsed_bids), 4)
        ask_depth_usd = round(sum(px * sz for px, sz in parsed_asks), 4)

        top_bids = tuple(parsed_bids[: max(1, int(max_levels))])
        top_asks = tuple(parsed_asks[: max(1, int(max_levels))])

        best_bid = top_bids[0][0] if top_bids else 0.0
        best_bid_sz = top_bids[0][1] if top_bids else 0.0
        best_ask = top_asks[0][0] if top_asks else 0.0
        best_ask_sz = top_asks[0][1] if top_asks else 0.0

        tick_sz = _safe_float(raw.get("minimum_tick_size") or raw.get("tick_size"), 0.01)
        if tick_sz <= 0.0:
            tick_sz = 0.01
        min_ord = _safe_float(raw.get("min_order_size") or raw.get("minimum_order_size"), 5.0)
        if min_ord <= 0.0:
            min_ord = 5.0
        ts_raw = raw.get("timestamp")
        ex_ms = int(_safe_float(ts_raw, 0.0))

        return cls(
            token_id=tid,
            bids=top_bids,
            asks=top_asks,
            best_bid=best_bid,
            best_bid_size=best_bid_sz,
            best_ask=best_ask,
            best_ask_size=best_ask_sz,
            resting_bid_depth_usd=bid_depth_usd,
            resting_ask_depth_usd=ask_depth_usd,
            tick_size=tick_sz,
            min_order_size=min_ord,
            fetched_ts=now_f,
            exchange_ts_ms=ex_ms,
            market_condition_id=str(raw.get("market") or ""),
        )


@dataclass(slots=True)
class NormalizedInstrument:
    """Normalized ERC-1155 conditional outcome token instrument."""

    token_id: str
    market_id: str
    event_id: str
    condition_id: str
    outcome_index: int
    outcome_label: str
    complement_token_id: str = ""
    gamma_indicative_price: Optional[float] = None
    tick_size: float = 0.01
    min_order_size: float = 5.0
    fee_rate_bps: float = 0.0
    maker_fee_bps: float = 0.0
    neg_risk: bool = False
    enable_order_book: bool = True
    is_tradable: bool = True
    skip_codes: Tuple[str, ...] = ()
    last_book_ts: float = 0.0
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    resting_bid_depth_usd: float = 0.0
    resting_ask_depth_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "market_id": self.market_id,
            "event_id": self.event_id,
            "condition_id": self.condition_id,
            "outcome_index": self.outcome_index,
            "outcome_label": self.outcome_label,
            "complement_token_id": self.complement_token_id,
            "gamma_indicative_price": self.gamma_indicative_price,
            "tick_size": self.tick_size,
            "min_order_size": self.min_order_size,
            "fee_rate_bps": self.fee_rate_bps,
            "maker_fee_bps": self.maker_fee_bps,
            "neg_risk": self.neg_risk,
            "enable_order_book": self.enable_order_book,
            "is_tradable": self.is_tradable,
            "skip_codes": list(self.skip_codes),
            "last_book_ts": self.last_book_ts,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "resting_bid_depth_usd": self.resting_bid_depth_usd,
            "resting_ask_depth_usd": self.resting_ask_depth_usd,
        }


@dataclass(slots=True)
class NormalizedMarket:
    """
    Normalized Polymarket market separating 100% Discovery Completeness (`discovery_complete=True`)
    from machine-verifiable Execution Eligibility (`execution_eligible` + `skip_codes`).
    """

    market_id: str
    event_id: str
    condition_id: str
    question_id: str
    slug: str
    question: str
    group_item_title: str
    group_item_threshold: str
    outcomes: Tuple[str, ...]
    token_ids: Tuple[str, ...]
    indicative_outcome_prices: Tuple[float, ...]
    instruments: Tuple[NormalizedInstrument, ...]
    active: bool
    closed: bool
    archived: bool
    accepting_orders: bool
    enable_order_book: bool
    neg_risk: bool
    neg_risk_augmented: bool
    neg_risk_other: bool
    neg_risk_market_id: str
    neg_risk_request_id: str
    is_augmented_placeholder: bool
    is_50_50_outcome: bool
    fees_enabled: bool
    fee_rate_bps: float
    maker_fee_bps: float
    fee_schedule_rate: float
    fee_exponent: float
    fee_taker_only: bool
    fee_rebate_rate: float
    fee_type: str
    tick_size: float
    min_order_size: float
    rfq_enabled: bool
    holding_rewards_enabled: bool
    rewards_min_size: float
    rewards_max_spread: float
    uma_resolution_status: str
    resolution_source: str
    description_rule_hash: str
    rule_summary: str
    start_date_iso: str
    end_date_iso: str
    end_ts: Optional[float]
    volume_24hr: float
    volume_total: float
    liquidity_usd: float
    category: str
    tags: Tuple[str, ...]
    series_slug: str
    discovered_sources: Tuple[str, ...]
    discovery_complete: bool
    execution_eligible: bool
    skip_codes: Tuple[str, ...]
    is_kmia_frozen_d001: bool
    metadata_digest: str

    @property
    def is_binary(self) -> bool:
        return len(self.outcomes) == 2 and len(self.token_ids) == 2

    @property
    def yes_token_id(self) -> str:
        return self.token_ids[0] if len(self.token_ids) >= 1 else ""

    @property
    def no_token_id(self) -> str:
        return self.token_ids[1] if len(self.token_ids) >= 2 else ""

    @property
    def is_zero_fee(self) -> bool:
        return (not self.fees_enabled) and self.fee_rate_bps <= 1e-9 and self.fee_schedule_rate <= 1e-9

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_id": self.market_id,
            "event_id": self.event_id,
            "condition_id": self.condition_id,
            "question_id": self.question_id,
            "slug": self.slug,
            "question": self.question,
            "group_item_title": self.group_item_title,
            "group_item_threshold": self.group_item_threshold,
            "outcomes": list(self.outcomes),
            "token_ids": list(self.token_ids),
            "indicative_outcome_prices": list(self.indicative_outcome_prices),
            "instruments": [inst.to_dict() for inst in self.instruments],
            "active": self.active,
            "closed": self.closed,
            "archived": self.archived,
            "accepting_orders": self.accepting_orders,
            "enable_order_book": self.enable_order_book,
            "neg_risk": self.neg_risk,
            "neg_risk_augmented": self.neg_risk_augmented,
            "neg_risk_other": self.neg_risk_other,
            "neg_risk_market_id": self.neg_risk_market_id,
            "neg_risk_request_id": self.neg_risk_request_id,
            "is_augmented_placeholder": self.is_augmented_placeholder,
            "is_50_50_outcome": self.is_50_50_outcome,
            "fees_enabled": self.fees_enabled,
            "fee_rate_bps": self.fee_rate_bps,
            "maker_fee_bps": self.maker_fee_bps,
            "fee_schedule_rate": self.fee_schedule_rate,
            "fee_exponent": self.fee_exponent,
            "fee_taker_only": self.fee_taker_only,
            "fee_rebate_rate": self.fee_rebate_rate,
            "fee_type": self.fee_type,
            "tick_size": self.tick_size,
            "min_order_size": self.min_order_size,
            "rfq_enabled": self.rfq_enabled,
            "holding_rewards_enabled": self.holding_rewards_enabled,
            "rewards_min_size": self.rewards_min_size,
            "rewards_max_spread": self.rewards_max_spread,
            "uma_resolution_status": self.uma_resolution_status,
            "resolution_source": self.resolution_source,
            "description_rule_hash": self.description_rule_hash,
            "rule_summary": self.rule_summary,
            "start_date_iso": self.start_date_iso,
            "end_date_iso": self.end_date_iso,
            "end_ts": self.end_ts,
            "volume_24hr": self.volume_24hr,
            "volume_total": self.volume_total,
            "liquidity_usd": self.liquidity_usd,
            "category": self.category,
            "tags": list(self.tags),
            "series_slug": self.series_slug,
            "discovered_sources": list(self.discovered_sources),
            "discovery_complete": self.discovery_complete,
            "execution_eligible": self.execution_eligible,
            "skip_codes": list(self.skip_codes),
            "is_kmia_frozen_d001": self.is_kmia_frozen_d001,
            "metadata_digest": self.metadata_digest,
        }


@dataclass(slots=True)
class NormalizedEvent:
    """Normalized Polymarket parent event grouping binary or multi-outcome markets."""

    event_id: str
    slug: str
    ticker: str
    title: str
    series_slug: str
    category: str
    tags: Tuple[str, ...]
    active: bool
    closed: bool
    archived: bool
    enable_order_book: bool
    neg_risk: bool
    enable_neg_risk: bool
    neg_risk_augmented: bool
    cumulative_markets: bool
    neg_risk_market_id: str
    resolution_source: str
    start_date_iso: str
    end_date_iso: str
    end_ts: Optional[float]
    volume_24hr: float
    volume_total: float
    liquidity_usd: float
    markets: Tuple[NormalizedMarket, ...]
    structure_kind: str
    has_other_outcome: bool
    placeholder_market_count: int
    active_market_count: int
    tradable_market_count: int
    total_market_count: int
    skip_codes: Tuple[str, ...]
    metadata_digest: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "slug": self.slug,
            "ticker": self.ticker,
            "title": self.title,
            "series_slug": self.series_slug,
            "category": self.category,
            "tags": list(self.tags),
            "active": self.active,
            "closed": self.closed,
            "archived": self.archived,
            "enable_order_book": self.enable_order_book,
            "neg_risk": self.neg_risk,
            "enable_neg_risk": self.enable_neg_risk,
            "neg_risk_augmented": self.neg_risk_augmented,
            "cumulative_markets": self.cumulative_markets,
            "neg_risk_market_id": self.neg_risk_market_id,
            "resolution_source": self.resolution_source,
            "start_date_iso": self.start_date_iso,
            "end_date_iso": self.end_date_iso,
            "end_ts": self.end_ts,
            "volume_24hr": self.volume_24hr,
            "volume_total": self.volume_total,
            "liquidity_usd": self.liquidity_usd,
            "structure_kind": self.structure_kind,
            "has_other_outcome": self.has_other_outcome,
            "placeholder_market_count": self.placeholder_market_count,
            "active_market_count": self.active_market_count,
            "tradable_market_count": self.tradable_market_count,
            "total_market_count": self.total_market_count,
            "skip_codes": list(self.skip_codes),
            "metadata_digest": self.metadata_digest,
            "markets": [m.to_dict() for m in self.markets],
        }


# ===========================================================================
# Normalization Constructors (Gamma + CLOB Cross-Reconciliation)
# ===========================================================================


def normalize_gamma_market(
    raw_mkt: Mapping[str, Any],
    *,
    parent_event: Optional[Mapping[str, Any]] = None,
    clob_overlay: Optional[Mapping[str, Any]] = None,
    now_ts: Optional[float] = None,
    discovered_sources: Sequence[str] = ("gamma_events",),
) -> NormalizedMarket:
    """
    Normalizes a raw Gamma market dict (optionally enriched by CLOB `/sampling-markets` overlay)
    into `NormalizedMarket` + `NormalizedInstrument`s, retaining 100% of metadata while attaching
    explicit machine-readable `skip_codes`.
    """
    now_f = float(time.time() if now_ts is None else now_ts)
    ev = parent_event or {}
    clob = clob_overlay or {}

    market_id = str(raw_mkt.get("id") or clob.get("question_id") or raw_mkt.get("conditionId") or "").strip()
    event_id = str(ev.get("id") or raw_mkt.get("_parent_event_id") or "").strip()
    if not event_id and isinstance(raw_mkt.get("events"), list) and raw_mkt["events"]:
        e0 = raw_mkt["events"][0]
        if isinstance(e0, Mapping):
            event_id = str(e0.get("id") or "").strip()

    condition_id = str(raw_mkt.get("conditionId") or clob.get("condition_id") or "").strip()
    question_id = str(raw_mkt.get("questionID") or clob.get("question_id") or "").strip()
    slug = str(raw_mkt.get("slug") or clob.get("market_slug") or "").strip()
    question = str(raw_mkt.get("question") or clob.get("question") or "").strip()
    group_item_title = str(raw_mkt.get("groupItemTitle") or "").strip()
    group_item_threshold = (
        str(raw_mkt.get("groupItemThreshold")).strip()
        if raw_mkt.get("groupItemThreshold") is not None
        else ""
    )

    outcomes = _parse_str_tuple(raw_mkt.get("outcomes"))
    token_ids = _parse_str_tuple(raw_mkt.get("clobTokenIds"))
    if (not outcomes or not token_ids) and isinstance(clob.get("tokens"), list):
        c_outs: List[str] = []
        c_toks: List[str] = []
        for tk_obj in clob["tokens"]:
            if isinstance(tk_obj, Mapping):
                tid_c = str(tk_obj.get("token_id") or "").strip()
                out_c = str(tk_obj.get("outcome") or "").strip()
                if tid_c:
                    c_toks.append(tid_c)
                    c_outs.append(out_c or f"Outcome_{len(c_outs)}")
        if not token_ids and c_toks:
            token_ids = tuple(c_toks)
        if not outcomes and c_outs:
            outcomes = tuple(c_outs)

    indicative_prices = _parse_float_tuple(raw_mkt.get("outcomePrices"))

    active = bool(raw_mkt.get("active", clob.get("active", True)))
    closed = bool(raw_mkt.get("closed", clob.get("closed", False)))
    archived = bool(raw_mkt.get("archived", clob.get("archived", False)))
    deploying = bool(raw_mkt.get("deploying") or raw_mkt.get("pendingDeployment") or ev.get("deploying") or ev.get("pendingDeployment"))

    ev_eob = ev.get("enableOrderBook", True)
    mkt_eob = raw_mkt.get("enableOrderBook", clob.get("enable_order_book", True))
    enable_order_book = bool(mkt_eob is not False and ev_eob is not False)
    if clob and clob.get("enable_order_book") is False:
        enable_order_book = False

    accepting_raw = raw_mkt.get("acceptingOrders")
    if accepting_raw is None:
        accepting_raw = clob.get("accepting_orders", True)
    accepting_orders = bool(accepting_raw is not False)

    neg_risk = bool(
        raw_mkt.get("negRisk")
        or ev.get("negRisk")
        or ev.get("enableNegRisk")
        or clob.get("neg_risk")
    )
    neg_risk_augmented = bool(
        ev.get("negRiskAugmented")
        or raw_mkt.get("negRiskAugmented")
        or ev.get("augmentedNegRisk")
        or ev.get("enableNegRiskOther")
    )
    neg_risk_market_id = str(
        raw_mkt.get("negRiskMarketID")
        or ev.get("negRiskMarketID")
        or clob.get("neg_risk_market_id")
        or ""
    ).strip()
    neg_risk_request_id = str(
        raw_mkt.get("negRiskRequestID")
        or clob.get("neg_risk_request_id")
        or ""
    ).strip()
    neg_risk_other_flag = bool(raw_mkt.get("negRiskOther") or ev.get("negRiskOther"))

    is_placeholder, is_other = detect_placeholder_or_other_outcome(
        question=question,
        group_item_title=group_item_title,
        market_slug=slug,
        neg_risk=neg_risk,
        neg_risk_augmented=neg_risk_augmented,
        neg_risk_other_flag=neg_risk_other_flag,
        active=active,
        enable_order_book=enable_order_book,
    )

    is_50_50 = bool(clob.get("is_50_50_outcome", False))

    # Exact fee extraction (Gamma `feesEnabled` + `takerBaseFee` + `feeSchedule` + CLOB `taker_base_fee`)
    fee_sched = raw_mkt.get("feeSchedule") if isinstance(raw_mkt.get("feeSchedule"), Mapping) else {}
    fees_enabled_raw = raw_mkt.get("feesEnabled")
    taker_base_raw = clob.get("taker_base_fee") if clob.get("taker_base_fee") is not None else raw_mkt.get("takerBaseFee")
    maker_base_raw = clob.get("maker_base_fee") if clob.get("maker_base_fee") is not None else raw_mkt.get("makerBaseFee")

    fee_rate_bps = _safe_float(taker_base_raw, 0.0)
    if 0.0 < fee_rate_bps < 1.0:
        fee_rate_bps = round(fee_rate_bps * 10000.0, 4)
    raw_maker_bps = _safe_float(maker_base_raw, 0.0)
    if 0.0 < raw_maker_bps < 1.0:
        raw_maker_bps = round(raw_maker_bps * 10000.0, 4)

    sched_rate = _safe_float(fee_sched.get("rate"), 0.0)
    fee_exponent = _safe_float(fee_sched.get("exponent"), 1.0)
    fee_taker_only = bool(fee_sched.get("takerOnly", True))
    fee_rebate_rate = _safe_float(fee_sched.get("rebateRate"), 0.0)
    fee_type = str(raw_mkt.get("feeType") or "").strip()

    if fees_enabled_raw is None:
        fees_enabled = bool(fee_rate_bps > 0.0 or sched_rate > 0.0)
    else:
        fees_enabled = bool(fees_enabled_raw)
    if not fees_enabled and clob.get("taker_base_fee") is None:
        fee_rate_bps = 0.0
        sched_rate = 0.0
    maker_fee_bps = 0.0 if (not fees_enabled or fee_taker_only) else raw_maker_bps

    tick_size = _safe_float(
        clob.get("minimum_tick_size") or raw_mkt.get("orderPriceMinTickSize"),
        0.01,
    )
    if tick_size <= 0.0:
        tick_size = 0.01
    min_order_size = _safe_float(
        clob.get("minimum_order_size") or raw_mkt.get("orderMinSize"),
        5.0,
    )
    if min_order_size <= 0.0:
        min_order_size = 5.0

    rfq_enabled = bool(raw_mkt.get("rfqEnabled", False))
    holding_rewards_enabled = bool(raw_mkt.get("holdingRewardsEnabled", False))
    rewards_min_size = _safe_float(raw_mkt.get("rewardsMinSize"), 0.0)
    rewards_max_spread = _safe_float(raw_mkt.get("rewardsMaxSpread"), 0.0)

    uma_status = str(raw_mkt.get("umaResolutionStatus") or "").strip().lower()
    if uma_status in ("none", "null"):
        uma_status = ""

    resolution_source = str(raw_mkt.get("resolutionSource") or ev.get("resolutionSource") or "").strip()
    desc_raw = str(raw_mkt.get("description") or ev.get("description") or clob.get("description") or "").strip()
    desc_hash = hashlib.sha256(desc_raw.encode("utf-8", errors="ignore")).hexdigest()[:16] if desc_raw else ""
    rule_summary = re.sub(r"\s+", " ", desc_raw)[:320] if desc_raw else ""

    start_date_iso = str(raw_mkt.get("startDate") or ev.get("startDate") or "").strip()
    end_date_iso = str(raw_mkt.get("endDate") or clob.get("end_date_iso") or ev.get("endDate") or "").strip()
    end_ts = parse_iso_timestamp(end_date_iso)

    vol_24h = _safe_float(raw_mkt.get("volume24hr"), 0.0)
    vol_tot = _safe_float(raw_mkt.get("volumeNum") or raw_mkt.get("volume"), 0.0)
    liq_usd = _safe_float(raw_mkt.get("liquidityNum") or raw_mkt.get("liquidity") or raw_mkt.get("liquidityClob"), 0.0)

    ev_tags = _parse_str_tuple(ev.get("tags") or raw_mkt.get("tags") or clob.get("tags"))
    series_slug = ""
    if isinstance(ev.get("series"), list) and ev["series"]:
        s0 = ev["series"][0]
        if isinstance(s0, Mapping):
            series_slug = str(s0.get("slug") or "").strip()
    if not series_slug:
        series_slug = str(ev.get("seriesSlug") or raw_mkt.get("seriesSlug") or "").strip()

    category = infer_primary_category(ev_tags, str(ev.get("slug") or slug), str(ev.get("title") or question))
    is_kmia_d001 = market_id in KMIA_D001_FROZEN_MARKET_IDS

    # Machine-readable skip / caution codes
    skips: List[str] = []
    if is_kmia_d001:
        skips.append(SkipReason.KMIA_D001_PROTECTED_LOCK.value)
    if closed or archived or bool(ev.get("closed")) or bool(ev.get("archived")):
        skips.append(SkipReason.CLOSED_OR_ARCHIVED.value)
    if not active or deploying or ev.get("active") is False:
        skips.append(SkipReason.INACTIVE_OR_PAUSED.value)
    if not enable_order_book:
        skips.append(SkipReason.ORDERBOOK_DISABLED.value)
    if not accepting_orders:
        skips.append(SkipReason.NOT_ACCEPTING_ORDERS.value)
    if not is_valid_hex_condition_id(condition_id):
        skips.append(SkipReason.MISSING_CONDITION_ID.value)
    if not token_ids or len(token_ids) < 2:
        skips.append(SkipReason.MISSING_TOKEN_IDS.value)
    elif len(outcomes) != len(token_ids):
        skips.append(SkipReason.NON_STANDARD_OUTCOME_ARITY.value)
    if is_placeholder:
        skips.append(SkipReason.AUGMENTED_PLACEHOLDER_OUTCOME.value)
    if is_other:
        skips.append(SkipReason.AUGMENTED_OTHER_MUTABLE_OUTCOME.value)
    if uma_status == "disputed":
        skips.append(SkipReason.UMA_DISPUTED_FROZEN.value)
    elif uma_status == "proposed":
        skips.append(SkipReason.UMA_PROPOSED_SETTLEMENT_STAGE.value)
    if end_ts is not None and end_ts < now_f and not closed:
        skips.append(SkipReason.PAST_END_DATE_UNRESOLVED.value)

    skip_tuple = tuple(dict.fromkeys(skips))
    execution_eligible = not any(code in HARD_EXECUTION_BLOCK_CODES for code in skip_tuple)

    instruments: List[NormalizedInstrument] = []
    inst_hard_blocked = not execution_eligible
    for idx, tid in enumerate(token_ids):
        lbl = outcomes[idx] if idx < len(outcomes) else f"Outcome_{idx}"
        comp_tid = ""
        if len(token_ids) == 2:
            comp_tid = token_ids[1 - idx]
        ind_px = indicative_prices[idx] if idx < len(indicative_prices) else None
        instruments.append(
            NormalizedInstrument(
                token_id=tid,
                market_id=market_id,
                event_id=event_id,
                condition_id=condition_id,
                outcome_index=idx,
                outcome_label=lbl,
                complement_token_id=comp_tid,
                gamma_indicative_price=ind_px,
                tick_size=tick_size,
                min_order_size=min_order_size,
                fee_rate_bps=fee_rate_bps,
                maker_fee_bps=maker_fee_bps,
                neg_risk=neg_risk,
                enable_order_book=enable_order_book,
                is_tradable=not inst_hard_blocked,
                skip_codes=skip_tuple,
            )
        )

    src_tuple = tuple(dict.fromkeys(s for s in discovered_sources if s))
    digest_material = (
        f"{market_id}|{event_id}|{condition_id}|{int(active)}|{int(closed)}|{int(archived)}|"
        f"{int(accepting_orders)}|{int(enable_order_book)}|{int(neg_risk)}|{int(neg_risk_augmented)}|"
        f"{int(is_other)}|{int(is_placeholder)}|{int(fees_enabled)}|{fee_rate_bps:.2f}|{sched_rate:.4f}|"
        f"{tick_size:.4f}|{min_order_size:.2f}|{uma_status}|{end_date_iso}|{','.join(token_ids)}|"
        f"{','.join(skip_tuple)}"
    )
    meta_digest = hashlib.sha1(digest_material.encode("utf-8")).hexdigest()[:20]

    return NormalizedMarket(
        market_id=market_id,
        event_id=event_id,
        condition_id=condition_id,
        question_id=question_id,
        slug=slug,
        question=question,
        group_item_title=group_item_title,
        group_item_threshold=group_item_threshold,
        outcomes=outcomes,
        token_ids=token_ids,
        indicative_outcome_prices=indicative_prices,
        instruments=tuple(instruments),
        active=active,
        closed=closed,
        archived=archived,
        accepting_orders=accepting_orders,
        enable_order_book=enable_order_book,
        neg_risk=neg_risk,
        neg_risk_augmented=neg_risk_augmented,
        neg_risk_other=is_other,
        neg_risk_market_id=neg_risk_market_id,
        neg_risk_request_id=neg_risk_request_id,
        is_augmented_placeholder=is_placeholder,
        is_50_50_outcome=is_50_50,
        fees_enabled=fees_enabled,
        fee_rate_bps=fee_rate_bps,
        maker_fee_bps=maker_fee_bps,
        fee_schedule_rate=sched_rate,
        fee_exponent=fee_exponent,
        fee_taker_only=fee_taker_only,
        fee_rebate_rate=fee_rebate_rate,
        fee_type=fee_type,
        tick_size=tick_size,
        min_order_size=min_order_size,
        rfq_enabled=rfq_enabled,
        holding_rewards_enabled=holding_rewards_enabled,
        rewards_min_size=rewards_min_size,
        rewards_max_spread=rewards_max_spread,
        uma_resolution_status=uma_status,
        resolution_source=resolution_source,
        description_rule_hash=desc_hash,
        rule_summary=rule_summary,
        start_date_iso=start_date_iso,
        end_date_iso=end_date_iso,
        end_ts=end_ts,
        volume_24hr=vol_24h,
        volume_total=vol_tot,
        liquidity_usd=liq_usd,
        category=category,
        tags=ev_tags,
        series_slug=series_slug,
        discovered_sources=src_tuple,
        discovery_complete=True,
        execution_eligible=execution_eligible,
        skip_codes=skip_tuple,
        is_kmia_frozen_d001=is_kmia_d001,
        metadata_digest=meta_digest,
    )


def normalize_gamma_event(
    raw_ev: Mapping[str, Any],
    *,
    clob_by_condition: Optional[Mapping[str, Mapping[str, Any]]] = None,
    now_ts: Optional[float] = None,
) -> NormalizedEvent:
    """Normalizes a raw Gamma event and 100% of its child markets into `NormalizedEvent`."""
    now_f = float(time.time() if now_ts is None else now_ts)
    clob_map = clob_by_condition or {}

    event_id = str(raw_ev.get("id") or "").strip()
    slug = str(raw_ev.get("slug") or "").strip()
    ticker = str(raw_ev.get("ticker") or "").strip()
    title = str(raw_ev.get("title") or "").strip()
    tags = _parse_str_tuple(raw_ev.get("tags"))

    series_slug = ""
    if isinstance(raw_ev.get("series"), list) and raw_ev["series"]:
        s0 = raw_ev["series"][0]
        if isinstance(s0, Mapping):
            series_slug = str(s0.get("slug") or "").strip()
    if not series_slug:
        series_slug = str(raw_ev.get("seriesSlug") or "").strip()

    category = infer_primary_category(tags, slug, title)
    active = bool(raw_ev.get("active", True))
    closed = bool(raw_ev.get("closed", False))
    archived = bool(raw_ev.get("archived", False))
    enable_order_book = bool(raw_ev.get("enableOrderBook", True) is not False)
    neg_risk = bool(raw_ev.get("negRisk", False))
    enable_neg_risk = bool(raw_ev.get("enableNegRisk", False))
    neg_risk_augmented = bool(
        raw_ev.get("negRiskAugmented") or raw_ev.get("augmentedNegRisk") or raw_ev.get("enableNegRiskOther")
    )
    cumulative_markets = bool(raw_ev.get("cumulativeMarkets", False))
    neg_risk_market_id = str(raw_ev.get("negRiskMarketID") or "").strip()
    resolution_source = str(raw_ev.get("resolutionSource") or "").strip()

    start_date_iso = str(raw_ev.get("startDate") or "").strip()
    end_date_iso = str(raw_ev.get("endDate") or "").strip()
    end_ts = parse_iso_timestamp(end_date_iso)

    vol_24h = _safe_float(raw_ev.get("volume24hr"), 0.0)
    vol_tot = _safe_float(raw_ev.get("volume"), 0.0)
    liq_usd = _safe_float(raw_ev.get("liquidity") or raw_ev.get("liquidityClob"), 0.0)

    raw_markets = raw_ev.get("markets") if isinstance(raw_ev.get("markets"), list) else []
    norm_markets: List[NormalizedMarket] = []
    for rm in raw_markets:
        if not isinstance(rm, Mapping):
            continue
        cid_l = str(rm.get("conditionId") or "").strip().lower()
        clob_ov = clob_map.get(cid_l) if cid_l else None
        srcs = ("gamma_events", "clob_sampling") if clob_ov is not None else ("gamma_events",)
        nm = normalize_gamma_market(
            rm,
            parent_event=raw_ev,
            clob_overlay=clob_ov,
            now_ts=now_f,
            discovered_sources=srcs,
        )
        if not neg_risk_market_id and nm.neg_risk_market_id:
            neg_risk_market_id = nm.neg_risk_market_id
        norm_markets.append(nm)

    active_mkts = [m for m in norm_markets if m.active and not m.closed and not m.archived]
    tradable_mkts = [m for m in norm_markets if m.execution_eligible]
    has_other = any(m.neg_risk_other for m in norm_markets)
    placeholder_cnt = sum(1 for m in norm_markets if m.is_augmented_placeholder)

    is_nr_any = neg_risk or enable_neg_risk or any(m.neg_risk for m in norm_markets)
    if not norm_markets:
        structure_kind = "EMPTY_EVENT"
    elif any(len(m.outcomes) > 2 for m in active_mkts):
        structure_kind = "NON_BINARY_OUTCOMES"
    elif len(active_mkts) <= 1 and len(norm_markets) == 1:
        structure_kind = "SINGLE_BINARY"
    elif is_nr_any and (neg_risk_augmented or has_other or placeholder_cnt > 0):
        structure_kind = "MULTI_OUTCOME_AUGMENTED_NEGRISK"
    elif is_nr_any:
        structure_kind = "MULTI_OUTCOME_NEGRISK"
    elif len(active_mkts) == 1:
        structure_kind = "SINGLE_ACTIVE_BINARY_IN_SERIES"
    else:
        structure_kind = "MULTI_MARKET_INDEPENDENT_OR_LADDER"

    ev_skips: List[str] = []
    if closed or archived:
        ev_skips.append(SkipReason.CLOSED_OR_ARCHIVED.value)
    if not active:
        ev_skips.append(SkipReason.INACTIVE_OR_PAUSED.value)
    if not enable_order_book:
        ev_skips.append(SkipReason.ORDERBOOK_DISABLED.value)
    if not norm_markets:
        ev_skips.append(SkipReason.MISSING_TOKEN_IDS.value)

    child_digests = ",".join(m.metadata_digest for m in norm_markets)
    ev_digest_raw = f"{event_id}|{slug}|{structure_kind}|{int(active)}|{int(closed)}|{int(archived)}|{child_digests}"
    ev_digest = hashlib.sha1(ev_digest_raw.encode("utf-8")).hexdigest()[:20]

    return NormalizedEvent(
        event_id=event_id,
        slug=slug,
        ticker=ticker,
        title=title,
        series_slug=series_slug,
        category=category,
        tags=tags,
        active=active,
        closed=closed,
        archived=archived,
        enable_order_book=enable_order_book,
        neg_risk=is_nr_any,
        enable_neg_risk=enable_neg_risk,
        neg_risk_augmented=neg_risk_augmented,
        cumulative_markets=cumulative_markets,
        neg_risk_market_id=neg_risk_market_id,
        resolution_source=resolution_source,
        start_date_iso=start_date_iso,
        end_date_iso=end_date_iso,
        end_ts=end_ts,
        volume_24hr=vol_24h,
        volume_total=vol_tot,
        liquidity_usd=liq_usd,
        markets=tuple(norm_markets),
        structure_kind=structure_kind,
        has_other_outcome=has_other,
        placeholder_market_count=placeholder_cnt,
        active_market_count=len(active_mkts),
        tradable_market_count=len(tradable_mkts),
        total_market_count=len(norm_markets),
        skip_codes=tuple(ev_skips),
        metadata_digest=ev_digest,
    )


# ===========================================================================
# Existing DOMINUS v5.1 Empirical Universe Coverage Simulator
# ===========================================================================


class ExistingDominusV51CoverageTracker:
    """
    Exact deterministic mirror of DOMINUS v5.1's live discovery & evaluation filters across:
      1. `Alpha124ShadowDaemon.discover_all_markets` (`alpha_124_shadow_daemon.py:2620-3152`)
      2. `Alpha124ShadowDaemon.extract_zerofee_general_binaries` (`max_markets=340`, `feesEnabled=False`, `max(liq,vol24)>=500`)
      3. `Alpha124ShadowDaemon.discover_uma_proposed_markets` (`offset=0,200` with `limit=200` -> clamped to `100`, plus top-1500 events UMA-only)
      4. `Alpha124ShadowDaemon._partition_ws_shards` (`3 x 200 = 600` WS token cap)
      5. `PolymarketDualFeed1HRecorder` (`10` crypto/metal co-assets)
      6. `PolymarketConnector` (`cross_venue_connectors.py`: `max_pages=2, page_limit=60 -> 120` markets, `max_hydrated_markets=30`)

    Accumulates lightweight `< 5 MiB` event/market tuples during streaming so we compute the
    100% EXACT numerator & denominator against the full live Polymarket universe!
    """

    # Exact v5.1 hardcoded tag caps in `alpha_124_shadow_daemon.py`
    TAG_CAPS: Dict[str, int] = {
        "weather": 500,       # L2633: offset in (0, 100, 200, 300, 400)
        "sports": 40,         # L2800: tag_slug=sports&limit=40
        "soccer": 100,        # L2923: tag_id=100350&limit=100
        "esports": 100,       # L2925: tag_id=64&limit=100
        "tennis": 45,         # L2956: tag_slug=tennis&limit=45
        "midterms": 60,       # L2957: tag_slug=midterms&limit=60
        "politics": 60,       # L2958: tag_slug=politics&limit=60
        "geopolitics": 80,    # L2959: tag_slug=geopolitics&limit=80
        "oil": 50,            # L2960: tag_slug=oil&limit=50
        "ukraine": 45,        # L2961: tag_slug=ukraine&limit=45
        "world": 60,          # L2962: tag_slug=world&limit=60
    }

    RECORDER_CO_ASSET_PREFIXES: Tuple[str, ...] = (
        "btc-up", "bitcoin-up", "eth-up", "ethereum-up", "sol-up", "solana-up",
        "xrp-up", "bnb-up", "doge-up", "hype-up", "zec-up", "gold-up", "silver-up",
        "xau-up", "xag-up",
    )

    def __init__(self) -> None:
        self.total_active_events: int = 0
        self.total_active_markets: int = 0
        self.total_tradable_markets: int = 0
        self.total_active_tokens: int = 0
        self.recorder_mkt_count: int = 0
        self._ev_seq: int = 0
        self._mkt_seq: int = 0

        # Bounded min-heaps `(vol_24hr, -seq_idx, id)` preserving exact stable descending tie-break order (`< 4 MiB` total!)
        self._top_1500_events_heap: List[Tuple[float, int, str]] = []
        self._tag_heaps: Dict[str, List[Tuple[float, int, str]]] = {k: [] for k in self.TAG_CAPS}
        self._sport_series_heaps: Dict[str, List[Tuple[float, int, str]]] = {
            "nba": [], "nfl": [], "nhl": [], "mlb": [], "cfb": [], "cbb": [],
        }
        self._unbounded_series_eids: Set[str] = set()
        # Retained compact `(seq_idx, vol_24hr, mkt_int_keys_tuple, category, is_closed_nr_le45, slug_lower)` ONLY for heap/series members
        self._retained_events: Dict[str, Tuple[int, float, Tuple[int | str, ...], str, bool, str]] = {}

        self._top_300_mkts_heap: List[Tuple[float, int, int | str]] = []
        self._zf_candidates: List[Tuple[str, int | str, float, float, float, bool]] = []
        self._uma_proposed: List[Tuple[int | str, str]] = []

    @staticmethod
    def _compact_mid(mid: str) -> int | str:
        return int(mid) if mid.isdigit() else mid

    @staticmethod
    def _push_bounded_heap(heap: List[Tuple[float, int, Any]], item: Tuple[float, int, Any], cap: int) -> Optional[Any]:
        if len(heap) < cap:
            heapq.heappush(heap, item)
            return None
        if item > heap[0]:
            popped = heapq.heapreplace(heap, item)
            return popped[2]
        return item[2]

    def _prune_retained_events(self) -> None:
        referenced: Set[str] = set(self._unbounded_series_eids)
        for _, _, eid in self._top_1500_events_heap:
            referenced.add(eid)
        for hp in self._tag_heaps.values():
            for _, _, eid in hp:
                referenced.add(eid)
        for hp in self._sport_series_heaps.values():
            for _, _, eid in hp:
                referenced.add(eid)
        stale = [eid for eid in self._retained_events if eid not in referenced]
        for eid in stale:
            del self._retained_events[eid]

    def observe_event(self, ev: NormalizedEvent) -> None:
        act_mkts = [m for m in ev.markets if m.active and not m.closed and not m.archived]
        if not act_mkts:
            return

        ev_idx = self._ev_seq
        self._ev_seq += 1
        self.total_active_events += 1
        self.total_active_markets += len(act_mkts)
        self.total_tradable_markets += sum(1 for m in act_mkts if m.execution_eligible)
        self.total_active_tokens += sum(len(m.token_ids) for m in act_mkts if m.enable_order_book)

        eid = ev.event_id
        v24_ev = ev.volume_24hr
        slug_l = ev.slug.lower()
        tags_l = tuple(t.lower() for t in ev.tags)
        ev_item = (v24_ev, -ev_idx, eid)

        retained_any = False
        if self._push_bounded_heap(self._top_1500_events_heap, ev_item, 1500) != eid:
            retained_any = True

        for tag_name, cap in self.TAG_CAPS.items():
            if tag_name in tags_l or tag_name in slug_l:
                if self._push_bounded_heap(self._tag_heaps[tag_name], ev_item, cap) != eid:
                    retained_any = True

        if any(slug_l.startswith(p) for p in self.RECORDER_CO_ASSET_PREFIXES) or any(
            k in slug_l for k in ("bitcoin-above", "ethereum-above", "what-price-will-bitcoin", "what-price-will-ethereum", "fomc", "fed-decision")
        ):
            self._unbounded_series_eids.add(eid)
            retained_any = True
        elif slug_l.startswith("nba-"):
            if self._push_bounded_heap(self._sport_series_heaps["nba"], ev_item, 40) != eid:
                retained_any = True
        elif any(slug_l.startswith(p) for p in ("nfl-", "nhl-", "mlb-", "cfb-", "cbb-")):
            sp_k = slug_l[:3]
            if self._push_bounded_heap(self._sport_series_heaps[sp_k], ev_item, 25) != eid:
                retained_any = True

        if retained_any:
            act_mids = tuple(self._compact_mid(m.market_id) for m in act_mkts)
            is_closed_nr_le45 = (
                ev.neg_risk
                and not ev.neg_risk_augmented
                and not ev.has_other_outcome
                and ev.placeholder_market_count == 0
                and 2 <= len(act_mkts) <= 45
            )
            self._retained_events[eid] = (ev_idx, v24_ev, act_mids, ev.category, is_closed_nr_le45, slug_l)
            if len(self._retained_events) > 7500:
                self._prune_retained_events()

        for m in act_mkts:
            m_idx = self._mkt_seq
            self._mkt_seq += 1
            cmid = self._compact_mid(m.market_id)
            m_slug_l = m.slug.lower()
            if any(m_slug_l.startswith(p) for p in self.RECORDER_CO_ASSET_PREFIXES):
                self.recorder_mkt_count += 1
            self._push_bounded_heap(self._top_300_mkts_heap, (m.volume_24hr, -m_idx, cmid), 300)
            if m.uma_resolution_status == "proposed":
                self._uma_proposed.append((cmid, eid))
            if m.is_zero_fee and m.is_binary and m.execution_eligible and max(m.volume_24hr, m.liquidity_usd) >= 500.0:
                self._zf_candidates.append((eid, cmid, m.volume_24hr, m.liquidity_usd, float(m.end_ts or 0.0), m.neg_risk))

    def finalize_metrics(self, *, now_ts: float) -> Dict[str, Any]:
        total_active_events = self.total_active_events
        total_active_markets = self.total_active_markets
        total_tradable_markets = self.total_tradable_markets
        total_active_tokens = self.total_active_tokens

        if total_active_events == 0 or total_active_markets == 0:
            return {
                "total_active_events": 0,
                "total_active_markets": 0,
                "v51_general_discovered_events": 0,
                "v51_general_discovered_events_pct": 0.0,
                "v51_evaluated_markets": 0,
                "v51_evaluated_markets_pct": 0.0,
            }

        self._prune_retained_events()
        top_1500_sorted = sorted(self._top_1500_events_heap, key=lambda x: (-x[0], -x[1]))
        top_600_eids = {x[2] for x in top_1500_sorted[:600]}
        top_1500_uma_only_eids = {x[2] for x in top_1500_sorted}

        tag_discovered_eids: Set[str] = set()
        zf_pool_eids: Set[str] = set(top_600_eids)
        for tag_name, hp in self._tag_heaps.items():
            for _, _, eid in hp:
                tag_discovered_eids.add(eid)
                if tag_name in ("midterms", "politics", "geopolitics", "oil", "ukraine", "world"):
                    zf_pool_eids.add(eid)

        series_eids: Set[str] = set(self._unbounded_series_eids)
        for hp in self._sport_series_heaps.values():
            for _, _, eid in hp:
                series_eids.add(eid)

        v51_general_discovered_eids = top_600_eids | tag_discovered_eids | series_eids
        v51_any_http_touched_eids = v51_general_discovered_eids | top_1500_uma_only_eids

        general_discovered_mkts: Set[int | str] = set()
        any_http_touched_mkts: Set[int | str] = set()
        for eid in v51_general_discovered_eids:
            info = self._retained_events.get(eid)
            if info is not None:
                general_discovered_mkts.update(info[2])
        for eid in v51_any_http_touched_eids:
            info = self._retained_events.get(eid)
            if info is not None:
                any_http_touched_mkts.update(info[2])

        evaluated_mids: Set[int | str] = set()

        # 1. `extract_zerofee_general_binaries` (`max_markets=340`, `is_zero_fee`, `max(liq, vol24) >= 500`, `end_ts > now + 120`, only from `zf_pool_eids`)
        zf_cands: List[Tuple[float, int | str]] = []
        for eid, cmid, v24, liq, end_ts, is_nr in self._zf_candidates:
            if eid in zf_pool_eids and end_ts > (now_ts + 120.0):
                rem_days = max(0.01, (end_ts - now_ts) / 86400.0)
                score = math.log1p(max(0.0, v24) * 4.0 + max(0.0, liq)) + (0.45 if not is_nr else 0.0) + (0.30 if rem_days <= 7.0 else 0.0)
                zf_cands.append((-score, str(cmid)))
        zf_cands.sort()
        zf_selected_mids = { (int(mid) if mid.isdigit() else mid) for _, mid in zf_cands[:340] }
        evaluated_mids.update(zf_selected_mids)

        # 2. Closed NegRisk Convert slates (`<= 45` brackets)
        nrc_pool = sorted(
            (self._retained_events[eid] for eid in v51_general_discovered_eids if eid in self._retained_events and self._retained_events[eid][4]),
            key=lambda info: (-info[1], info[0]),
        )
        for info in nrc_pool[:128]:
            evaluated_mids.update(info[2])

        # 3. Weather, Crypto candles/ladders, Sports/Soccer/Tennis/Esports & CAL1 ladders inside `v51_general_discovered_eids`
        for eid in v51_general_discovered_eids:
            info = self._retained_events.get(eid)
            if info is None:
                continue
            _, _, m_keys, cat, _, sl = info
            if cat in ("weather", "sports") or any(sl.startswith(p) for p in self.RECORDER_CO_ASSET_PREFIXES):
                evaluated_mids.update(m_keys)
            elif _TEMPORAL_DEADLINE_RE.search(sl) or _STRIKE_OR_THRESHOLD_RE.search(sl):
                if len(m_keys) >= 2:
                    evaluated_mids.update(m_keys)

        # 4. UMA `proposed` markets discovered (`offset=0..99` + `offset=200..299` hole + `top_1500_uma_only_eids`)
        mkts_top_300_sorted = sorted(self._top_300_mkts_heap, key=lambda r: (-r[0], -r[1]))
        uma_page_slice_mids = {r[2] for r in mkts_top_300_sorted[0:100]} | {r[2] for r in mkts_top_300_sorted[200:300]}
        uma_evaluated_mids = {
            cmid
            for cmid, eid in self._uma_proposed
            if cmid in uma_page_slice_mids or eid in top_1500_uma_only_eids
        }
        evaluated_mids.update(uma_evaluated_mids)

        # 5. Cross-Venue Connector (`max_pages=2 * page_limit=60 = 120` markets + `100` sports markets; `max_hydrated_markets=30`)
        cv_discovered_cnt = min(total_active_markets, 220)
        cv_hydrated_cnt = min(total_tradable_markets, 30)

        ws_subscribed_tokens_cap = min(total_active_tokens, 600)

        return {
            "universe_denominators": {
                "total_active_events": total_active_events,
                "total_active_markets": total_active_markets,
                "total_tradable_markets": total_tradable_markets,
                "total_orderbook_tokens": total_active_tokens,
            },
            "alpha124_shadow_and_live_harvester_bridge": {
                "general_discovered_events": len(v51_general_discovered_eids),
                "general_discovered_events_pct": round(100.0 * len(v51_general_discovered_eids) / total_active_events, 3),
                "any_http_touched_events_incl_uma1500": len(v51_any_http_touched_eids),
                "any_http_touched_events_pct": round(100.0 * len(v51_any_http_touched_eids) / total_active_events, 3),
                "general_discovered_markets": len(general_discovered_mkts),
                "general_discovered_markets_pct": round(100.0 * len(general_discovered_mkts) / total_active_markets, 3),
                "any_http_touched_markets_incl_uma1500": len(any_http_touched_mkts),
                "any_http_touched_markets_pct": round(100.0 * len(any_http_touched_mkts) / total_active_markets, 3),
                "strategy_evaluated_markets": len(evaluated_mids),
                "strategy_evaluated_markets_pct_of_active": round(100.0 * len(evaluated_mids) / total_active_markets, 3),
                "strategy_evaluated_markets_pct_of_tradable": round(
                    100.0 * len(evaluated_mids) / max(1, total_tradable_markets), 3
                ),
                "zerofee_general_binaries_evaluated": len(zf_selected_mids),
                "uma_proposed_evaluated": len(uma_evaluated_mids),
                "ws_realtime_subscribed_tokens_cap": ws_subscribed_tokens_cap,
                "ws_realtime_subscribed_tokens_pct": round(
                    100.0 * ws_subscribed_tokens_cap / max(1, total_active_tokens), 3
                ),
                "blind_unmonitored_active_markets": total_active_markets - len(evaluated_mids),
                "blind_unmonitored_active_markets_pct": round(
                    100.0 * (total_active_markets - len(evaluated_mids)) / total_active_markets, 3
                ),
            },
            "polymarket_terminal_recorder": {
                "hardcoded_co_assets_count": 10,
                "discovered_markets_count": self.recorder_mkt_count,
                "discovered_markets_pct": round(100.0 * self.recorder_mkt_count / total_active_markets, 4),
            },
            "cross_venue_polymarket_connector": {
                "default_max_pages_x_limit_markets": cv_discovered_cnt,
                "discovered_markets_pct": round(100.0 * cv_discovered_cnt / total_active_markets, 3),
                "l2_hydrated_markets_cap": cv_hydrated_cnt,
                "l2_hydrated_markets_pct": round(100.0 * cv_hydrated_cnt / total_active_markets, 4),
            },
        }


# ===========================================================================
# SQLite Incremental Full-Universe Registry (`< 120 MiB` RAM Footprint)
# ===========================================================================


@dataclass(slots=True)
class SweepDiffStats:
    """Exact incremental diff counts produced on each full or delta registry sync."""

    run_id: str
    started_ts: float
    completed_ts: float
    wall_time_sec: float
    gamma_pages_fetched: int
    clob_pages_fetched: int
    added_events: int = 0
    updated_events: int = 0
    unchanged_events: int = 0
    added_markets: int = 0
    updated_markets: int = 0
    unchanged_markets: int = 0
    newly_closed_or_missing_markets: int = 0
    total_events_seen: int = 0
    total_markets_seen: int = 0
    total_instruments_seen: int = 0
    peak_rss_mib: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_ts": round(self.started_ts, 3),
            "completed_ts": round(self.completed_ts, 3),
            "wall_time_sec": round(self.wall_time_sec, 3),
            "gamma_pages_fetched": self.gamma_pages_fetched,
            "clob_pages_fetched": self.clob_pages_fetched,
            "added_events": self.added_events,
            "updated_events": self.updated_events,
            "unchanged_events": self.unchanged_events,
            "added_markets": self.added_markets,
            "updated_markets": self.updated_markets,
            "unchanged_markets": self.unchanged_markets,
            "newly_closed_or_missing_markets": self.newly_closed_or_missing_markets,
            "total_events_seen": self.total_events_seen,
            "total_markets_seen": self.total_markets_seen,
            "total_instruments_seen": self.total_instruments_seen,
            "peak_rss_mib": round(self.peak_rss_mib, 2),
        }


class FullUniverseRegistry:
    """
    Durable, `<120 MiB` RAM full-universe registry backed by SQLite WAL
    (`data/universe/market_registry.sqlite3`) and `data/universe/coverage_snapshot.json`.

    Supports both:
      - Live 100% untruncated streaming sweeps (`sweep_full_universe`)
      - Deterministic offline / unit-test ingestion (`ingest_events`)
    """

    def __init__(
        self,
        db_path: Path | str = DEFAULT_REGISTRY_DB_PATH,
        snapshot_path: Path | str = DEFAULT_COVERAGE_SNAPSHOT_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.snapshot_path = Path(snapshot_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self._init_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            c = sqlite3.connect(str(self.db_path), check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL;")
            c.execute("PRAGMA synchronous=NORMAL;")
            c.execute("PRAGMA temp_store=FILE;")
            c.execute("PRAGMA cache_size=-3000;")  # <= 3 MiB SQLite page cache
            c.execute("PRAGMA mmap_size=0;")       # 0 MiB memory-mapped DB pages (`D-010`)
            c.execute("PRAGMA wal_autocheckpoint=200;")
            self._conn = c
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    def _init_schema(self) -> None:
        with self._lock:
            c = self.conn
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    slug TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    title TEXT NOT NULL,
                    series_slug TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    closed INTEGER NOT NULL,
                    archived INTEGER NOT NULL,
                    enable_order_book INTEGER NOT NULL,
                    neg_risk INTEGER NOT NULL,
                    enable_neg_risk INTEGER NOT NULL,
                    neg_risk_augmented INTEGER NOT NULL,
                    cumulative_markets INTEGER NOT NULL,
                    neg_risk_market_id TEXT NOT NULL,
                    resolution_source TEXT NOT NULL,
                    start_date_iso TEXT NOT NULL,
                    end_date_iso TEXT NOT NULL,
                    end_ts REAL,
                    volume_24hr REAL NOT NULL,
                    volume_total REAL NOT NULL,
                    liquidity_usd REAL NOT NULL,
                    structure_kind TEXT NOT NULL,
                    has_other_outcome INTEGER NOT NULL,
                    placeholder_market_count INTEGER NOT NULL,
                    active_market_count INTEGER NOT NULL,
                    tradable_market_count INTEGER NOT NULL,
                    total_market_count INTEGER NOT NULL,
                    skip_codes_json TEXT NOT NULL,
                    metadata_digest TEXT NOT NULL,
                    first_seen_ts REAL NOT NULL,
                    last_seen_ts REAL NOT NULL,
                    last_sweep_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS markets (
                    market_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    condition_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    question TEXT NOT NULL,
                    group_item_title TEXT NOT NULL,
                    group_item_threshold TEXT NOT NULL,
                    outcomes_json TEXT NOT NULL,
                    token_ids_json TEXT NOT NULL,
                    indicative_prices_json TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    closed INTEGER NOT NULL,
                    archived INTEGER NOT NULL,
                    accepting_orders INTEGER NOT NULL,
                    enable_order_book INTEGER NOT NULL,
                    neg_risk INTEGER NOT NULL,
                    neg_risk_augmented INTEGER NOT NULL,
                    neg_risk_other INTEGER NOT NULL,
                    neg_risk_market_id TEXT NOT NULL,
                    neg_risk_request_id TEXT NOT NULL,
                    is_augmented_placeholder INTEGER NOT NULL,
                    is_50_50_outcome INTEGER NOT NULL,
                    fees_enabled INTEGER NOT NULL,
                    fee_rate_bps REAL NOT NULL,
                    maker_fee_bps REAL NOT NULL,
                    fee_schedule_rate REAL NOT NULL,
                    fee_exponent REAL NOT NULL,
                    fee_taker_only INTEGER NOT NULL,
                    fee_rebate_rate REAL NOT NULL,
                    fee_type TEXT NOT NULL,
                    tick_size REAL NOT NULL,
                    min_order_size REAL NOT NULL,
                    rfq_enabled INTEGER NOT NULL,
                    holding_rewards_enabled INTEGER NOT NULL,
                    rewards_min_size REAL NOT NULL,
                    rewards_max_spread REAL NOT NULL,
                    uma_resolution_status TEXT NOT NULL,
                    resolution_source TEXT NOT NULL,
                    description_rule_hash TEXT NOT NULL,
                    rule_summary TEXT NOT NULL,
                    start_date_iso TEXT NOT NULL,
                    end_date_iso TEXT NOT NULL,
                    end_ts REAL,
                    volume_24hr REAL NOT NULL,
                    volume_total REAL NOT NULL,
                    liquidity_usd REAL NOT NULL,
                    category TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    series_slug TEXT NOT NULL,
                    discovered_sources_json TEXT NOT NULL,
                    discovery_complete INTEGER NOT NULL,
                    execution_eligible INTEGER NOT NULL,
                    skip_codes_json TEXT NOT NULL,
                    is_kmia_frozen_d001 INTEGER NOT NULL,
                    metadata_digest TEXT NOT NULL,
                    first_seen_ts REAL NOT NULL,
                    last_seen_ts REAL NOT NULL,
                    last_sweep_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS instruments (
                    token_id TEXT PRIMARY KEY,
                    market_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    condition_id TEXT NOT NULL,
                    outcome_index INTEGER NOT NULL,
                    outcome_label TEXT NOT NULL,
                    complement_token_id TEXT NOT NULL,
                    gamma_indicative_price REAL,
                    tick_size REAL NOT NULL,
                    min_order_size REAL NOT NULL,
                    fee_rate_bps REAL NOT NULL,
                    maker_fee_bps REAL NOT NULL,
                    neg_risk INTEGER NOT NULL,
                    enable_order_book INTEGER NOT NULL,
                    is_tradable INTEGER NOT NULL,
                    skip_codes_json TEXT NOT NULL,
                    last_book_ts REAL NOT NULL DEFAULT 0.0,
                    best_bid REAL,
                    best_ask REAL,
                    resting_bid_depth_usd REAL NOT NULL DEFAULT 0.0,
                    resting_ask_depth_usd REAL NOT NULL DEFAULT 0.0,
                    last_seen_ts REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS surveillance_state (
                    key TEXT PRIMARY KEY,
                    value_text TEXT NOT NULL,
                    updated_ts REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sweep_runs (
                    run_id TEXT PRIMARY KEY,
                    started_ts REAL NOT NULL,
                    completed_ts REAL NOT NULL,
                    wall_time_sec REAL NOT NULL,
                    added_markets INTEGER NOT NULL,
                    updated_markets INTEGER NOT NULL,
                    unchanged_markets INTEGER NOT NULL,
                    newly_closed_markets INTEGER NOT NULL,
                    peak_rss_mib REAL NOT NULL,
                    summary_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_markets_event_id ON markets(event_id);
                CREATE INDEX IF NOT EXISTS idx_markets_condition_id ON markets(condition_id);
                CREATE INDEX IF NOT EXISTS idx_markets_active_elig ON markets(active, closed, execution_eligible);
                CREATE INDEX IF NOT EXISTS idx_markets_category ON markets(category, active, closed);
                CREATE INDEX IF NOT EXISTS idx_instruments_market_id ON instruments(market_id);
                CREATE INDEX IF NOT EXISTS idx_instruments_tradable_book_ts ON instruments(is_tradable, last_book_ts);
                """
            )
            c.commit()

    def _upsert_normalized_events_page(
        self,
        norm_events: Sequence[NormalizedEvent],
        *,
        sweep_id: str,
        now_ts: float,
        diff: SweepDiffStats,
    ) -> None:
        if not norm_events:
            return
        with self._lock:
            c = self.conn
            eids = [ev.event_id for ev in norm_events if ev.event_id]
            existing_ev_digests: Dict[str, str] = {}
            for i in range(0, len(eids), 400):
                ch = eids[i : i + 400]
                q_marks = ",".join("?" for _ in ch)
                for row in c.execute(f"SELECT event_id, metadata_digest FROM events WHERE event_id IN ({q_marks})", ch):
                    existing_ev_digests[str(row[0])] = str(row[1])

            all_mkts: List[NormalizedMarket] = [m for ev in norm_events for m in ev.markets if m.market_id]
            mids = [m.market_id for m in all_mkts]
            existing_mkt_digests: Dict[str, str] = {}
            for i in range(0, len(mids), 400):
                ch = mids[i : i + 400]
                q_marks = ",".join("?" for _ in ch)
                for row in c.execute(f"SELECT market_id, metadata_digest FROM markets WHERE market_id IN ({q_marks})", ch):
                    existing_mkt_digests[str(row[0])] = str(row[1])

            ev_to_upsert: List[Tuple[Any, ...]] = []
            ev_touch_only: List[Tuple[float, str, str]] = []
            for ev in norm_events:
                if not ev.event_id:
                    continue
                diff.total_events_seen += 1
                prev_d = existing_ev_digests.get(ev.event_id)
                if prev_d == ev.metadata_digest:
                    diff.unchanged_events += 1
                    ev_touch_only.append((now_ts, sweep_id, ev.event_id))
                else:
                    if prev_d is None:
                        diff.added_events += 1
                    else:
                        diff.updated_events += 1
                    ev_to_upsert.append(
                        (
                            ev.event_id,
                            ev.slug,
                            ev.ticker,
                            ev.title,
                            ev.series_slug,
                            ev.category,
                            _json_dumps_str(list(ev.tags)),
                            int(ev.active),
                            int(ev.closed),
                            int(ev.archived),
                            int(ev.enable_order_book),
                            int(ev.neg_risk),
                            int(ev.enable_neg_risk),
                            int(ev.neg_risk_augmented),
                            int(ev.cumulative_markets),
                            ev.neg_risk_market_id,
                            ev.resolution_source,
                            ev.start_date_iso,
                            ev.end_date_iso,
                            ev.end_ts,
                            ev.volume_24hr,
                            ev.volume_total,
                            ev.liquidity_usd,
                            ev.structure_kind,
                            int(ev.has_other_outcome),
                            ev.placeholder_market_count,
                            ev.active_market_count,
                            ev.tradable_market_count,
                            ev.total_market_count,
                            _json_dumps_str(list(ev.skip_codes)),
                            ev.metadata_digest,
                            now_ts,
                            now_ts,
                            sweep_id,
                        )
                    )

            mkt_to_upsert: List[Tuple[Any, ...]] = []
            mkt_touch_only: List[Tuple[float, str, str]] = []
            inst_to_upsert: List[Tuple[Any, ...]] = []

            for m in all_mkts:
                diff.total_markets_seen += 1
                diff.total_instruments_seen += len(m.instruments)
                prev_md = existing_mkt_digests.get(m.market_id)
                if prev_md == m.metadata_digest:
                    diff.unchanged_markets += 1
                    mkt_touch_only.append((now_ts, sweep_id, m.market_id))
                else:
                    if prev_md is None:
                        diff.added_markets += 1
                    else:
                        diff.updated_markets += 1
                    mkt_to_upsert.append(
                        (
                            m.market_id,
                            m.event_id,
                            m.condition_id,
                            m.question_id,
                            m.slug,
                            m.question,
                            m.group_item_title,
                            m.group_item_threshold,
                            _json_dumps_str(list(m.outcomes)),
                            _json_dumps_str(list(m.token_ids)),
                            _json_dumps_str(list(m.indicative_outcome_prices)),
                            int(m.active),
                            int(m.closed),
                            int(m.archived),
                            int(m.accepting_orders),
                            int(m.enable_order_book),
                            int(m.neg_risk),
                            int(m.neg_risk_augmented),
                            int(m.neg_risk_other),
                            m.neg_risk_market_id,
                            m.neg_risk_request_id,
                            int(m.is_augmented_placeholder),
                            int(m.is_50_50_outcome),
                            int(m.fees_enabled),
                            m.fee_rate_bps,
                            m.maker_fee_bps,
                            m.fee_schedule_rate,
                            m.fee_exponent,
                            int(m.fee_taker_only),
                            m.fee_rebate_rate,
                            m.fee_type,
                            m.tick_size,
                            m.min_order_size,
                            int(m.rfq_enabled),
                            int(m.holding_rewards_enabled),
                            m.rewards_min_size,
                            m.rewards_max_spread,
                            m.uma_resolution_status,
                            m.resolution_source,
                            m.description_rule_hash,
                            m.rule_summary,
                            m.start_date_iso,
                            m.end_date_iso,
                            m.end_ts,
                            m.volume_24hr,
                            m.volume_total,
                            m.liquidity_usd,
                            m.category,
                            _json_dumps_str(list(m.tags)),
                            m.series_slug,
                            _json_dumps_str(list(m.discovered_sources)),
                            int(m.discovery_complete),
                            int(m.execution_eligible),
                            _json_dumps_str(list(m.skip_codes)),
                            int(m.is_kmia_frozen_d001),
                            m.metadata_digest,
                            now_ts,
                            now_ts,
                            sweep_id,
                        )
                    )
                    for inst in m.instruments:
                        inst_to_upsert.append(
                            (
                                inst.token_id,
                                inst.market_id,
                                inst.event_id,
                                inst.condition_id,
                                inst.outcome_index,
                                inst.outcome_label,
                                inst.complement_token_id,
                                inst.gamma_indicative_price,
                                inst.tick_size,
                                inst.min_order_size,
                                inst.fee_rate_bps,
                                inst.maker_fee_bps,
                                int(inst.neg_risk),
                                int(inst.enable_order_book),
                                int(inst.is_tradable),
                                _json_dumps_str(list(inst.skip_codes)),
                                now_ts,
                            )
                        )

            c.execute("BEGIN")
            try:
                if ev_to_upsert:
                    c.executemany(
                        """
                        INSERT INTO events VALUES (
                            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                        )
                        ON CONFLICT(event_id) DO UPDATE SET
                            slug=excluded.slug,
                            ticker=excluded.ticker,
                            title=excluded.title,
                            series_slug=excluded.series_slug,
                            category=excluded.category,
                            tags_json=excluded.tags_json,
                            active=excluded.active,
                            closed=excluded.closed,
                            archived=excluded.archived,
                            enable_order_book=excluded.enable_order_book,
                            neg_risk=excluded.neg_risk,
                            enable_neg_risk=excluded.enable_neg_risk,
                            neg_risk_augmented=excluded.neg_risk_augmented,
                            cumulative_markets=excluded.cumulative_markets,
                            neg_risk_market_id=excluded.neg_risk_market_id,
                            resolution_source=excluded.resolution_source,
                            start_date_iso=excluded.start_date_iso,
                            end_date_iso=excluded.end_date_iso,
                            end_ts=excluded.end_ts,
                            volume_24hr=excluded.volume_24hr,
                            volume_total=excluded.volume_total,
                            liquidity_usd=excluded.liquidity_usd,
                            structure_kind=excluded.structure_kind,
                            has_other_outcome=excluded.has_other_outcome,
                            placeholder_market_count=excluded.placeholder_market_count,
                            active_market_count=excluded.active_market_count,
                            tradable_market_count=excluded.tradable_market_count,
                            total_market_count=excluded.total_market_count,
                            skip_codes_json=excluded.skip_codes_json,
                            metadata_digest=excluded.metadata_digest,
                            last_seen_ts=excluded.last_seen_ts,
                            last_sweep_id=excluded.last_sweep_id
                        """,
                        ev_to_upsert,
                    )
                if ev_touch_only:
                    c.executemany(
                        "UPDATE events SET last_seen_ts=?, last_sweep_id=? WHERE event_id=?",
                        ev_touch_only,
                    )
                if mkt_to_upsert:
                    c.executemany(
                        """
                        INSERT INTO markets VALUES (
                            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                        )
                        ON CONFLICT(market_id) DO UPDATE SET
                            event_id=excluded.event_id,
                            condition_id=excluded.condition_id,
                            question_id=excluded.question_id,
                            slug=excluded.slug,
                            question=excluded.question,
                            group_item_title=excluded.group_item_title,
                            group_item_threshold=excluded.group_item_threshold,
                            outcomes_json=excluded.outcomes_json,
                            token_ids_json=excluded.token_ids_json,
                            indicative_prices_json=excluded.indicative_prices_json,
                            active=excluded.active,
                            closed=excluded.closed,
                            archived=excluded.archived,
                            accepting_orders=excluded.accepting_orders,
                            enable_order_book=excluded.enable_order_book,
                            neg_risk=excluded.neg_risk,
                            neg_risk_augmented=excluded.neg_risk_augmented,
                            neg_risk_other=excluded.neg_risk_other,
                            neg_risk_market_id=excluded.neg_risk_market_id,
                            neg_risk_request_id=excluded.neg_risk_request_id,
                            is_augmented_placeholder=excluded.is_augmented_placeholder,
                            is_50_50_outcome=excluded.is_50_50_outcome,
                            fees_enabled=excluded.fees_enabled,
                            fee_rate_bps=excluded.fee_rate_bps,
                            maker_fee_bps=excluded.maker_fee_bps,
                            fee_schedule_rate=excluded.fee_schedule_rate,
                            fee_exponent=excluded.fee_exponent,
                            fee_taker_only=excluded.fee_taker_only,
                            fee_rebate_rate=excluded.fee_rebate_rate,
                            fee_type=excluded.fee_type,
                            tick_size=excluded.tick_size,
                            min_order_size=excluded.min_order_size,
                            rfq_enabled=excluded.rfq_enabled,
                            holding_rewards_enabled=excluded.holding_rewards_enabled,
                            rewards_min_size=excluded.rewards_min_size,
                            rewards_max_spread=excluded.rewards_max_spread,
                            uma_resolution_status=excluded.uma_resolution_status,
                            resolution_source=excluded.resolution_source,
                            description_rule_hash=excluded.description_rule_hash,
                            rule_summary=excluded.rule_summary,
                            start_date_iso=excluded.start_date_iso,
                            end_date_iso=excluded.end_date_iso,
                            end_ts=excluded.end_ts,
                            volume_24hr=excluded.volume_24hr,
                            volume_total=excluded.volume_total,
                            liquidity_usd=excluded.liquidity_usd,
                            category=excluded.category,
                            tags_json=excluded.tags_json,
                            series_slug=excluded.series_slug,
                            discovered_sources_json=excluded.discovered_sources_json,
                            discovery_complete=excluded.discovery_complete,
                            execution_eligible=excluded.execution_eligible,
                            skip_codes_json=excluded.skip_codes_json,
                            is_kmia_frozen_d001=excluded.is_kmia_frozen_d001,
                            metadata_digest=excluded.metadata_digest,
                            last_seen_ts=excluded.last_seen_ts,
                            last_sweep_id=excluded.last_sweep_id
                        """,
                        mkt_to_upsert,
                    )
                if mkt_touch_only:
                    c.executemany(
                        "UPDATE markets SET last_seen_ts=?, last_sweep_id=? WHERE market_id=?",
                        mkt_touch_only,
                    )
                if inst_to_upsert:
                    c.executemany(
                        """
                        INSERT INTO instruments (
                            token_id, market_id, event_id, condition_id, outcome_index,
                            outcome_label, complement_token_id, gamma_indicative_price,
                            tick_size, min_order_size, fee_rate_bps, maker_fee_bps,
                            neg_risk, enable_order_book, is_tradable, skip_codes_json, last_seen_ts
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(token_id) DO UPDATE SET
                            market_id=excluded.market_id,
                            event_id=excluded.event_id,
                            condition_id=excluded.condition_id,
                            outcome_index=excluded.outcome_index,
                            outcome_label=excluded.outcome_label,
                            complement_token_id=excluded.complement_token_id,
                            gamma_indicative_price=excluded.gamma_indicative_price,
                            tick_size=excluded.tick_size,
                            min_order_size=excluded.min_order_size,
                            fee_rate_bps=excluded.fee_rate_bps,
                            maker_fee_bps=excluded.maker_fee_bps,
                            neg_risk=excluded.neg_risk,
                            enable_order_book=excluded.enable_order_book,
                            is_tradable=excluded.is_tradable,
                            skip_codes_json=excluded.skip_codes_json,
                            last_seen_ts=excluded.last_seen_ts
                        """,
                        inst_to_upsert,
                    )
                c.commit()
            except Exception:
                c.rollback()
                raise

    def _mark_disappeared_markets_closed(self, sweep_id: str, now_ts: float) -> int:
        """Marks previously active markets absent from a completed full sweep as `CLOSED_OR_ARCHIVED`."""
        with self._lock:
            c = self.conn
            rows = c.execute(
                "SELECT market_id, skip_codes_json FROM markets WHERE active=1 AND closed=0 AND last_sweep_id != ?",
                (sweep_id,),
            ).fetchall()
            if not rows:
                return 0
            updates: List[Tuple[str, str, float, str]] = []
            mids: List[str] = []
            for r in rows:
                mid = str(r["market_id"])
                mids.append(mid)
                cur_skips = list(_json_loads(r["skip_codes_json"]))
                if SkipReason.CLOSED_OR_ARCHIVED.value not in cur_skips:
                    cur_skips.append(SkipReason.CLOSED_OR_ARCHIVED.value)
                new_digest = hashlib.sha1(f"closed|{mid}|{now_ts}".encode("utf-8")).hexdigest()[:20]
                updates.append((_json_dumps_str(cur_skips), new_digest, now_ts, mid))
            c.execute("BEGIN")
            try:
                c.executemany(
                    """
                    UPDATE markets
                    SET active=0, closed=1, execution_eligible=0, skip_codes_json=?, metadata_digest=?, last_seen_ts=?
                    WHERE market_id=?
                    """,
                    updates,
                )
                for i in range(0, len(mids), 400):
                    ch = mids[i : i + 400]
                    q_marks = ",".join("?" for _ in ch)
                    c.execute(f"UPDATE instruments SET is_tradable=0 WHERE market_id IN ({q_marks})", ch)
                c.commit()
            except Exception:
                c.rollback()
                raise
            return len(updates)

    def ingest_events(
        self,
        raw_events: Iterable[Mapping[str, Any]],
        *,
        clob_markets: Sequence[Mapping[str, Any]] = (),
        now_ts: Optional[float] = None,
        mark_missing_closed: bool = True,
        page_chunk_size: int = 100,
    ) -> SweepDiffStats:
        """Deterministic offline / synthetic ingestion entrypoint with full diff accounting."""
        t0 = time.time()
        eval_ts = float(t0 if now_ts is None else now_ts)
        run_id = f"INGEST_{int(eval_ts * 1000)}"
        clob_by_cid: Dict[str, Mapping[str, Any]] = {}
        for cm in clob_markets:
            if isinstance(cm, Mapping) and cm.get("condition_id"):
                clob_by_cid[str(cm["condition_id"]).strip().lower()] = cm

        diff = SweepDiffStats(
            run_id=run_id,
            started_ts=eval_ts,
            completed_ts=eval_ts,
            wall_time_sec=0.0,
            gamma_pages_fetched=0,
            clob_pages_fetched=1 if clob_markets else 0,
        )

        seen_cids: Set[str] = set()
        buf: List[NormalizedEvent] = []
        for raw_ev in raw_events:
            if not isinstance(raw_ev, Mapping):
                continue
            nev = normalize_gamma_event(raw_ev, clob_by_condition=clob_by_cid, now_ts=eval_ts)
            for nm in nev.markets:
                if nm.condition_id:
                    seen_cids.add(nm.condition_id.lower())
            buf.append(nev)
            if len(buf) >= page_chunk_size:
                diff.gamma_pages_fetched += 1
                self._upsert_normalized_events_page(buf, sweep_id=run_id, now_ts=eval_ts, diff=diff)
                buf.clear()

        # Reconcile any CLOB-only markets absent from Gamma events into synthetic standalone events
        for cid_l, cm in clob_by_cid.items():
            if cid_l not in seen_cids:
                nm_c = normalize_gamma_market(
                    {},
                    parent_event=None,
                    clob_overlay=cm,
                    now_ts=eval_ts,
                    discovered_sources=("clob_sampling",),
                )
                syn_ev_id = f"CLOB_STANDALONE_{nm_c.market_id or cid_l[:16]}"
                nm_c.event_id = syn_ev_id
                for inst in nm_c.instruments:
                    inst.event_id = syn_ev_id
                buf.append(
                    NormalizedEvent(
                        event_id=syn_ev_id,
                        slug=nm_c.slug or syn_ev_id.lower(),
                        ticker="",
                        title=nm_c.question or syn_ev_id,
                        series_slug="",
                        category=nm_c.category,
                        tags=nm_c.tags,
                        active=nm_c.active,
                        closed=nm_c.closed,
                        archived=nm_c.archived,
                        enable_order_book=nm_c.enable_order_book,
                        neg_risk=nm_c.neg_risk,
                        enable_neg_risk=nm_c.neg_risk,
                        neg_risk_augmented=nm_c.neg_risk_augmented,
                        cumulative_markets=False,
                        neg_risk_market_id=nm_c.neg_risk_market_id,
                        resolution_source="",
                        start_date_iso="",
                        end_date_iso=nm_c.end_date_iso,
                        end_ts=nm_c.end_ts,
                        volume_24hr=0.0,
                        volume_total=0.0,
                        liquidity_usd=0.0,
                        markets=(nm_c,),
                        structure_kind="SINGLE_BINARY",
                        has_other_outcome=nm_c.neg_risk_other,
                        placeholder_market_count=int(nm_c.is_augmented_placeholder),
                        active_market_count=int(nm_c.active and not nm_c.closed and not nm_c.archived),
                        tradable_market_count=int(nm_c.execution_eligible),
                        total_market_count=1,
                        skip_codes=nm_c.skip_codes,
                        metadata_digest=nm_c.metadata_digest,
                    )
                )

        if buf:
            diff.gamma_pages_fetched += 1
            self._upsert_normalized_events_page(buf, sweep_id=run_id, now_ts=eval_ts, diff=diff)
            buf.clear()

        if mark_missing_closed:
            diff.newly_closed_or_missing_markets = self._mark_disappeared_markets_closed(run_id, eval_ts)

        diff.completed_ts = time.time()
        diff.wall_time_sec = max(0.0, diff.completed_ts - t0)
        diff.peak_rss_mib = max(diff.peak_rss_mib, get_process_rss_mib())
        self._record_sweep_run(diff, {"diff": diff.to_dict()})
        return diff

    def _record_sweep_run(self, diff: SweepDiffStats, summary: Mapping[str, Any]) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO sweep_runs VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    diff.run_id,
                    diff.started_ts,
                    diff.completed_ts,
                    diff.wall_time_sec,
                    diff.added_markets,
                    diff.updated_markets,
                    diff.unchanged_markets,
                    diff.newly_closed_or_missing_markets,
                    diff.peak_rss_mib,
                    _json_dumps_str(dict(summary)),
                ),
            )
            self.conn.commit()

    def sweep_full_universe(
        self,
        *,
        http_client: Optional[PersistentJsonHttpClient] = None,
        max_gamma_pages: Optional[int] = None,
        include_clob_sampling: bool = True,
        include_boundary_probes: bool = True,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a 100% untruncated live public sweep across:
          1. CLOB `/sampling-markets` (`next_cursor` until `LTE=`), capturing compact authoritative
             CLOB microstructures (`taker_base_fee`, `maker_base_fee`, `minimum_order_size`,
             `minimum_tick_size`, `is_50_50_outcome`, `neg_risk_market_id`, `accepting_orders`).
          2. Gamma `/events/keyset?active=true&closed=false&limit=200&after_cursor=...` until
             `next_cursor is None` (`0` offset truncation, `0` volume/liquidity/category exclusions).
          3. Boundary probes on Gamma `/events?offset=...` (`offset=2100` HTTP 422 check),
             paused/inactive (`active=false&closed=false`), and archived-unclosed (`archived=true&closed=false`).
          4. Exact v5.1 empirical discovery vs. evaluation comparison (`ExistingDominusV51CoverageTracker`).
        """
        own_client = http_client is None
        client = http_client or PersistentJsonHttpClient()
        t0 = time.time()
        run_id = f"SWEEP_{datetime.fromtimestamp(t0, tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        peak_rss = get_process_rss_mib()

        diff = SweepDiffStats(
            run_id=run_id,
            started_ts=t0,
            completed_ts=t0,
            wall_time_sec=0.0,
            gamma_pages_fetched=0,
            clob_pages_fetched=0,
            peak_rss_mib=peak_rss,
        )

        # Compact CLOB overlay keyed by lowercase `condition_id` (`~10.7k` entries => `< 3.5 MiB` RAM)
        clob_overlay_by_cid: Dict[str, Dict[str, Any]] = {}
        clob_active_count = 0
        clob_eob_count = 0
        clob_fee_dist: Counter[str] = Counter()

        try:
            if include_clob_sampling:
                cursor = ""
                seen_cursors: Set[str] = set()
                while True:
                    url = f"{CLOB_API_BASE}/sampling-markets" + (
                        f"?next_cursor={urllib.parse.quote(cursor, safe='')}" if cursor else ""
                    )
                    st, payload = client.request_json("GET", url)
                    if st != 200 or not isinstance(payload, Mapping):
                        break
                    rows = payload.get("data") or []
                    diff.clob_pages_fetched += 1
                    for cm in rows:
                        if not isinstance(cm, Mapping):
                            continue
                        cid_c = str(cm.get("condition_id") or "").strip().lower()
                        if not cid_c:
                            continue
                        if cm.get("active") and not cm.get("closed"):
                            clob_active_count += 1
                        if cm.get("enable_order_book") and not cm.get("closed"):
                            clob_eob_count += 1
                        tbf = int(_safe_float(cm.get("taker_base_fee"), 0.0))
                        clob_fee_dist[str(tbf)] += 1
                        clob_overlay_by_cid[cid_c] = {
                            "condition_id": cm.get("condition_id"),
                            "question_id": cm.get("question_id"),
                            "market_slug": cm.get("market_slug"),
                            "active": cm.get("active"),
                            "closed": cm.get("closed"),
                            "archived": cm.get("archived"),
                            "accepting_orders": cm.get("accepting_orders"),
                            "enable_order_book": cm.get("enable_order_book"),
                            "taker_base_fee": cm.get("taker_base_fee"),
                            "maker_base_fee": cm.get("maker_base_fee"),
                            "minimum_order_size": cm.get("minimum_order_size"),
                            "minimum_tick_size": cm.get("minimum_tick_size"),
                            "neg_risk": cm.get("neg_risk"),
                            "neg_risk_market_id": cm.get("neg_risk_market_id"),
                            "neg_risk_request_id": cm.get("neg_risk_request_id"),
                            "is_50_50_outcome": cm.get("is_50_50_outcome"),
                        }
                    nc = str(payload.get("next_cursor") or "").strip()
                    if not rows or not nc or nc == "LTE=" or nc in seen_cursors:
                        break
                    seen_cursors.add(nc)
                    cursor = nc
                peak_rss = max(peak_rss, get_process_rss_mib())

            # Streaming histograms across 100% of active unclosed Gamma `/events/keyset`
            v51_tracker = ExistingDominusV51CoverageTracker()
            event_structure_counts: Counter[str] = Counter()
            category_event_counts: Counter[str] = Counter()
            category_active_market_counts: Counter[str] = Counter()
            tag_counts: Counter[str] = Counter()
            skip_code_market_counts: Counter[str] = Counter()
            uma_status_active_counts: Counter[str] = Counter()
            fee_type_active_counts: Counter[str] = Counter()
            fee_bps_active_counts: Counter[str] = Counter()

            active_events_total = 0
            binary_single_events = 0
            multi_market_events = 0
            negrisk_events_total = 0
            negrisk_standard_events = 0
            negrisk_augmented_events = 0
            events_with_other_outcome = 0

            all_child_markets_total = 0
            closed_sibling_markets_in_active_events = 0
            active_unclosed_markets = 0
            execution_eligible_markets = 0
            eob_true_active_markets = 0
            eob_false_active_markets = 0
            accepting_orders_true_active = 0
            accepting_orders_false_active = 0
            fees_enabled_true_active = 0
            fees_enabled_false_active = 0
            fee_bps_gt_zero_active = 0
            fee_bps_zero_active = 0
            neg_risk_active_markets = 0
            augmented_placeholder_markets_total = 0
            augmented_other_markets_total = 0
            strike_or_threshold_ladder_events = 0
            temporal_deadline_ladder_events = 0
            rfq_enabled_active_markets = 0
            holding_rewards_active_markets = 0

            tradable_outcome_tokens = 0
            all_active_market_tokens = 0
            matched_clob_cids: Set[str] = set()

            after_cursor: Optional[str] = None
            seen_gamma_cursors: Set[str] = set()

            while True:
                if max_gamma_pages is not None and diff.gamma_pages_fetched >= max_gamma_pages:
                    break
                q = "/events/keyset?active=true&closed=false&limit=25"
                if after_cursor:
                    q += "&after_cursor=" + urllib.parse.quote(after_cursor, safe="")
                st_g, body_g = client.request_json("GET", f"{GAMMA_API_BASE}{q}")
                if st_g != 200 or not isinstance(body_g, Mapping):
                    raise RuntimeError(f"Gamma /events/keyset failed HTTP {st_g}: {str(body_g)[:200]}")

                nc_g = str(body_g.get("next_cursor") or "").strip()
                raw_evts = list(body_g.get("events") or ())
                del body_g
                if not raw_evts:
                    break
                diff.gamma_pages_fetched += 1
                now_page = time.time()

                norm_page: List[NormalizedEvent] = []
                for idx_e in range(len(raw_evts)):
                    raw_ev = raw_evts[idx_e]
                    raw_evts[idx_e] = None  # Free raw JSON dict immediately as we normalize
                    if not isinstance(raw_ev, Mapping):
                        continue
                    nev = normalize_gamma_event(raw_ev, clob_by_condition=clob_overlay_by_cid, now_ts=now_page)
                    del raw_ev
                    norm_page.append(nev)
                    v51_tracker.observe_event(nev)

                    active_events_total += 1
                    event_structure_counts[nev.structure_kind] += 1
                    category_event_counts[nev.category] += 1
                    for tg in nev.tags[:8]:
                        tag_counts[tg.lower()] += 1

                    if nev.active_market_count <= 1:
                        binary_single_events += 1
                    else:
                        multi_market_events += 1
                        joined_txt = f"{nev.title} {nev.slug}"
                        if _STRIKE_OR_THRESHOLD_RE.search(joined_txt):
                            strike_or_threshold_ladder_events += 1
                        if _TEMPORAL_DEADLINE_RE.search(joined_txt):
                            temporal_deadline_ladder_events += 1

                    if nev.neg_risk:
                        negrisk_events_total += 1
                        if nev.neg_risk_augmented or nev.has_other_outcome or nev.placeholder_market_count > 0:
                            negrisk_augmented_events += 1
                        else:
                            negrisk_standard_events += 1
                    if nev.has_other_outcome:
                        events_with_other_outcome += 1

                    for nm in nev.markets:
                        all_child_markets_total += 1
                        if nm.condition_id:
                            cid_low = nm.condition_id.lower()
                            if cid_low in clob_overlay_by_cid:
                                matched_clob_cids.add(cid_low)
                        if nm.is_augmented_placeholder:
                            augmented_placeholder_markets_total += 1
                        if nm.neg_risk_other:
                            augmented_other_markets_total += 1
                        for sc in nm.skip_codes:
                            skip_code_market_counts[sc] += 1

                        if nm.closed or nm.archived or not nm.active:
                            closed_sibling_markets_in_active_events += 1
                            continue

                        active_unclosed_markets += 1
                        category_active_market_counts[nm.category] += 1
                        all_active_market_tokens += len(nm.token_ids)

                        if nm.execution_eligible:
                            execution_eligible_markets += 1
                            tradable_outcome_tokens += sum(1 for inst in nm.instruments if inst.is_tradable)
                        if nm.enable_order_book:
                            eob_true_active_markets += 1
                        else:
                            eob_false_active_markets += 1
                        if nm.accepting_orders:
                            accepting_orders_true_active += 1
                        else:
                            accepting_orders_false_active += 1
                        if nm.fees_enabled:
                            fees_enabled_true_active += 1
                        else:
                            fees_enabled_false_active += 1
                        if nm.fee_rate_bps > 0.0 or nm.fee_schedule_rate > 0.0:
                            fee_bps_gt_zero_active += 1
                        else:
                            fee_bps_zero_active += 1
                        if nm.neg_risk:
                            neg_risk_active_markets += 1
                        if nm.rfq_enabled:
                            rfq_enabled_active_markets += 1
                        if nm.holding_rewards_enabled:
                            holding_rewards_active_markets += 1

                        uma_status_active_counts[nm.uma_resolution_status or "none"] += 1
                        fee_type_active_counts[nm.fee_type or "zero_fee"] += 1
                        fee_bps_active_counts[str(int(round(nm.fee_rate_bps)))] += 1

                del raw_evts
                self._upsert_normalized_events_page(norm_page, sweep_id=run_id, now_ts=now_page, diff=diff)
                del norm_page

                if diff.gamma_pages_fetched % 10 == 0:
                    _release_unused_heap_memory()
                if diff.gamma_pages_fetched % 50 == 0:
                    try:
                        self.conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
                    except Exception:
                        pass
                peak_rss = max(peak_rss, get_process_rss_mib())
                diff.peak_rss_mib = peak_rss

                if progress_callback is not None:
                    progress_callback(diff.gamma_pages_fetched, active_events_total, peak_rss)

                if not nc_g or nc_g in seen_gamma_cursors:
                    break
                seen_gamma_cursors.add(nc_g)
                after_cursor = nc_g

            # Reconcile any CLOB `/sampling-markets` rows whose condition_id did not appear in active Gamma events
            clob_only_markets_reconciled = 0
            if clob_overlay_by_cid:
                clob_extra_events: List[NormalizedEvent] = []
                now_clob_rec = time.time()
                for cid_l, cm_ov in clob_overlay_by_cid.items():
                    if cid_l in matched_clob_cids:
                        continue
                    if cm_ov.get("closed") or not cm_ov.get("active", True):
                        continue
                    nm_c = normalize_gamma_market(
                        {},
                        parent_event=None,
                        clob_overlay=cm_ov,
                        now_ts=now_clob_rec,
                        discovered_sources=("clob_sampling",),
                    )
                    syn_eid = f"CLOB_STANDALONE_{nm_c.market_id or cid_l[:16]}"
                    nm_c.event_id = syn_eid
                    for inst_c in nm_c.instruments:
                        inst_c.event_id = syn_eid
                    clob_only_markets_reconciled += 1
                    clob_extra_events.append(
                        NormalizedEvent(
                            event_id=syn_eid,
                            slug=nm_c.slug or syn_eid.lower(),
                            ticker="",
                            title=nm_c.question or syn_eid,
                            series_slug="",
                            category=nm_c.category,
                            tags=nm_c.tags,
                            active=nm_c.active,
                            closed=nm_c.closed,
                            archived=nm_c.archived,
                            enable_order_book=nm_c.enable_order_book,
                            neg_risk=nm_c.neg_risk,
                            enable_neg_risk=nm_c.neg_risk,
                            neg_risk_augmented=nm_c.neg_risk_augmented,
                            cumulative_markets=False,
                            neg_risk_market_id=nm_c.neg_risk_market_id,
                            resolution_source="",
                            start_date_iso="",
                            end_date_iso=nm_c.end_date_iso,
                            end_ts=nm_c.end_ts,
                            volume_24hr=0.0,
                            volume_total=0.0,
                            liquidity_usd=0.0,
                            markets=(nm_c,),
                            structure_kind="SINGLE_BINARY",
                            has_other_outcome=nm_c.neg_risk_other,
                            placeholder_market_count=int(nm_c.is_augmented_placeholder),
                            active_market_count=1,
                            tradable_market_count=int(nm_c.execution_eligible),
                            total_market_count=1,
                            skip_codes=nm_c.skip_codes,
                            metadata_digest=nm_c.metadata_digest,
                        )
                    )
                    if len(clob_extra_events) >= 100:
                        self._upsert_normalized_events_page(
                            clob_extra_events, sweep_id=run_id, now_ts=now_clob_rec, diff=diff
                        )
                        clob_extra_events.clear()
                if clob_extra_events:
                    self._upsert_normalized_events_page(
                        clob_extra_events, sweep_id=run_id, now_ts=now_clob_rec, diff=diff
                    )
                    clob_extra_events.clear()

            if max_gamma_pages is None:
                diff.newly_closed_or_missing_markets = self._mark_disappeared_markets_closed(run_id, time.time())

            # Boundary probes: offset=2100 truncation check + paused (`active=false&closed=false`) + archived (`archived=true&closed=false`)
            boundary_probes: Dict[str, Any] = {}
            if include_boundary_probes:
                st_lim, b_lim = client.request_json(
                    "GET", f"{GAMMA_API_BASE}/events?active=true&closed=false&limit=500&offset=0"
                )
                st_422, b_422 = client.request_json(
                    "GET", f"{GAMMA_API_BASE}/events?active=true&closed=false&limit=100&offset=3000"
                )
                st_paused, b_paused = client.request_json(
                    "GET", f"{GAMMA_API_BASE}/events?active=false&closed=false&limit=20&offset=0&order=id&ascending=false"
                )
                st_arch, b_arch = client.request_json(
                    "GET", f"{GAMMA_API_BASE}/events?active=true&archived=true&closed=false&limit=20&offset=0&order=id&ascending=false"
                )
                paused_list = b_paused if isinstance(b_paused, list) else []
                arch_list = b_arch if isinstance(b_arch, list) else []
                boundary_probes = {
                    "gamma_limit_500_actual_returned_len": len(b_lim) if isinstance(b_lim, list) else 0,
                    "gamma_offset_3000_http_status": st_422,
                    "gamma_offset_3000_error": b_422 if isinstance(b_422, Mapping) else str(b_422)[:160],
                    "paused_inactive_unclosed_sample_http": st_paused,
                    "paused_inactive_unclosed_sample_count": len(paused_list),
                    "paused_deploying_in_sample": sum(
                        1 for e in paused_list if isinstance(e, Mapping) and (e.get("deploying") or e.get("pendingDeployment"))
                    ),
                    "archived_unclosed_sample_http": st_arch,
                    "archived_unclosed_sample_count": len(arch_list),
                }
                del b_lim, b_422, b_paused, b_arch, paused_list, arch_list

            now_done = time.time()
            v51_comparison = v51_tracker.finalize_metrics(now_ts=now_done)
            del v51_tracker, matched_clob_cids, clob_overlay_by_cid
            _release_unused_heap_memory()

            peak_rss = max(peak_rss, get_process_rss_mib())
            diff.completed_ts = now_done
            diff.wall_time_sec = max(0.0, now_done - t0)
            diff.peak_rss_mib = peak_rss

            snapshot_doc: Dict[str, Any] = {
                "schema_version": "2.0",
                "run_id": run_id,
                "generated_at_utc": datetime.fromtimestamp(now_done, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "generated_at_unix": round(now_done, 3),
                "mode": "MODE_1_2_PUBLIC_READ_ONLY",
                "discovery_completeness_pct": 100.0 if max_gamma_pages is None else round(100.0 * (max_gamma_pages / 190.0), 2),
                "sweep_truncated": max_gamma_pages is not None,
                "diff_stats": diff.to_dict(),
                "universe_totals": {
                    "active_unclosed_events": active_events_total,
                    "single_market_binary_events": binary_single_events,
                    "multi_market_events": multi_market_events,
                    "all_child_markets_in_active_events": all_child_markets_total,
                    "closed_or_inactive_sibling_markets_in_active_events": closed_sibling_markets_in_active_events,
                    "active_unclosed_markets": active_unclosed_markets,
                    "execution_eligible_markets": execution_eligible_markets,
                    "ineligible_active_markets_retained_with_skip_codes": active_unclosed_markets - execution_eligible_markets,
                    "tradable_outcome_token_ids": tradable_outcome_tokens,
                    "all_active_market_token_ids": all_active_market_tokens,
                    "clob_sampling_markets_active": clob_active_count,
                    "clob_sampling_markets_eob_true": clob_eob_count,
                    "clob_standalone_markets_reconciled": clob_only_markets_reconciled,
                },
                "protocol_and_instrument_breakdown": {
                    "negrisk_events_total": negrisk_events_total,
                    "negrisk_standard_closed_slate_events": negrisk_standard_events,
                    "negrisk_augmented_or_other_or_placeholder_events": negrisk_augmented_events,
                    "events_with_other_outcome": events_with_other_outcome,
                    "negrisk_active_markets": neg_risk_active_markets,
                    "augmented_placeholder_markets_total": augmented_placeholder_markets_total,
                    "augmented_other_markets_total": augmented_other_markets_total,
                    "enable_order_book_true_active_markets": eob_true_active_markets,
                    "enable_order_book_false_active_markets": eob_false_active_markets,
                    "accepting_orders_true_active_markets": accepting_orders_true_active,
                    "accepting_orders_false_active_markets": accepting_orders_false_active,
                    "fees_enabled_true_active_markets": fees_enabled_true_active,
                    "fees_enabled_false_active_markets": fees_enabled_false_active,
                    "fee_rate_bps_gt_zero_active_markets": fee_bps_gt_zero_active,
                    "fee_rate_bps_eq_zero_active_markets": fee_bps_zero_active,
                    "rfq_enabled_active_markets": rfq_enabled_active_markets,
                    "holding_rewards_enabled_active_markets": holding_rewards_active_markets,
                    "strike_or_threshold_ladder_events": strike_or_threshold_ladder_events,
                    "temporal_deadline_ladder_events": temporal_deadline_ladder_events,
                    "event_structure_kinds": dict(event_structure_counts.most_common()),
                    "fee_types_active_markets": dict(fee_type_active_counts.most_common()),
                    "fee_rate_bps_distribution_active": dict(fee_bps_active_counts.most_common()),
                    "clob_sampling_taker_base_fee_bps": dict(clob_fee_dist.most_common()),
                    "uma_resolution_status_active": dict(uma_status_active_counts.most_common()),
                },
                "category_and_tag_breakdown": {
                    "events_by_category": dict(category_event_counts.most_common()),
                    "active_markets_by_category": dict(category_active_market_counts.most_common()),
                    "top_40_tags_by_event_count": dict(tag_counts.most_common(40)),
                },
                "skip_code_counts_all_retained_markets": dict(skip_code_market_counts.most_common()),
                "boundary_and_pagination_probes": boundary_probes,
                "existing_dominus_v51_coverage_comparison": v51_comparison,
                "http_transport_stats": dict(client.stats),
            }

            self._record_sweep_run(diff, snapshot_doc)
            self._write_atomic_json(self.snapshot_path, snapshot_doc)
            return snapshot_doc
        finally:
            if own_client:
                client.close()

    @staticmethod
    def _write_atomic_json(path: Path, doc: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".tmp.{os.getpid()}")
        txt = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        tmp.write_text(txt, encoding="utf-8", newline="\n")
        os.replace(tmp, path)

    # -----------------------------------------------------------------------
    # Row -> Dataclass Reconstruction & Streaming Query Methods
    # -----------------------------------------------------------------------

    @staticmethod
    def _row_to_instrument(row: sqlite3.Row) -> NormalizedInstrument:
        return NormalizedInstrument(
            token_id=str(row["token_id"]),
            market_id=str(row["market_id"]),
            event_id=str(row["event_id"]),
            condition_id=str(row["condition_id"]),
            outcome_index=int(row["outcome_index"]),
            outcome_label=str(row["outcome_label"]),
            complement_token_id=str(row["complement_token_id"]),
            gamma_indicative_price=float(row["gamma_indicative_price"]) if row["gamma_indicative_price"] is not None else None,
            tick_size=float(row["tick_size"]),
            min_order_size=float(row["min_order_size"]),
            fee_rate_bps=float(row["fee_rate_bps"]),
            maker_fee_bps=float(row["maker_fee_bps"]),
            neg_risk=bool(row["neg_risk"]),
            enable_order_book=bool(row["enable_order_book"]),
            is_tradable=bool(row["is_tradable"]),
            skip_codes=tuple(_json_loads(row["skip_codes_json"])),
            last_book_ts=float(row["last_book_ts"] or 0.0),
            best_bid=float(row["best_bid"]) if row["best_bid"] is not None else None,
            best_ask=float(row["best_ask"]) if row["best_ask"] is not None else None,
            resting_bid_depth_usd=float(row["resting_bid_depth_usd"] or 0.0),
            resting_ask_depth_usd=float(row["resting_ask_depth_usd"] or 0.0),
        )

    @classmethod
    def _row_to_market(cls, row: sqlite3.Row, instruments: Tuple[NormalizedInstrument, ...]) -> NormalizedMarket:
        return NormalizedMarket(
            market_id=str(row["market_id"]),
            event_id=str(row["event_id"]),
            condition_id=str(row["condition_id"]),
            question_id=str(row["question_id"]),
            slug=str(row["slug"]),
            question=str(row["question"]),
            group_item_title=str(row["group_item_title"]),
            group_item_threshold=str(row["group_item_threshold"]),
            outcomes=tuple(_json_loads(row["outcomes_json"])),
            token_ids=tuple(_json_loads(row["token_ids_json"])),
            indicative_outcome_prices=tuple(float(x) for x in _json_loads(row["indicative_prices_json"])),
            instruments=instruments,
            active=bool(row["active"]),
            closed=bool(row["closed"]),
            archived=bool(row["archived"]),
            accepting_orders=bool(row["accepting_orders"]),
            enable_order_book=bool(row["enable_order_book"]),
            neg_risk=bool(row["neg_risk"]),
            neg_risk_augmented=bool(row["neg_risk_augmented"]),
            neg_risk_other=bool(row["neg_risk_other"]),
            neg_risk_market_id=str(row["neg_risk_market_id"]),
            neg_risk_request_id=str(row["neg_risk_request_id"]),
            is_augmented_placeholder=bool(row["is_augmented_placeholder"]),
            is_50_50_outcome=bool(row["is_50_50_outcome"]),
            fees_enabled=bool(row["fees_enabled"]),
            fee_rate_bps=float(row["fee_rate_bps"]),
            maker_fee_bps=float(row["maker_fee_bps"]),
            fee_schedule_rate=float(row["fee_schedule_rate"]),
            fee_exponent=float(row["fee_exponent"]),
            fee_taker_only=bool(row["fee_taker_only"]),
            fee_rebate_rate=float(row["fee_rebate_rate"]),
            fee_type=str(row["fee_type"]),
            tick_size=float(row["tick_size"]),
            min_order_size=float(row["min_order_size"]),
            rfq_enabled=bool(row["rfq_enabled"]),
            holding_rewards_enabled=bool(row["holding_rewards_enabled"]),
            rewards_min_size=float(row["rewards_min_size"]),
            rewards_max_spread=float(row["rewards_max_spread"]),
            uma_resolution_status=str(row["uma_resolution_status"]),
            resolution_source=str(row["resolution_source"]),
            description_rule_hash=str(row["description_rule_hash"]),
            rule_summary=str(row["rule_summary"]),
            start_date_iso=str(row["start_date_iso"]),
            end_date_iso=str(row["end_date_iso"]),
            end_ts=float(row["end_ts"]) if row["end_ts"] is not None else None,
            volume_24hr=float(row["volume_24hr"]),
            volume_total=float(row["volume_total"]),
            liquidity_usd=float(row["liquidity_usd"]),
            category=str(row["category"]),
            tags=tuple(_json_loads(row["tags_json"])),
            series_slug=str(row["series_slug"]),
            discovered_sources=tuple(_json_loads(row["discovered_sources_json"])),
            discovery_complete=bool(row["discovery_complete"]),
            execution_eligible=bool(row["execution_eligible"]),
            skip_codes=tuple(_json_loads(row["skip_codes_json"])),
            is_kmia_frozen_d001=bool(row["is_kmia_frozen_d001"]),
            metadata_digest=str(row["metadata_digest"]),
        )

    def _load_instruments_by_market_ids(self, market_ids: Sequence[str]) -> Dict[str, Tuple[NormalizedInstrument, ...]]:
        out: Dict[str, List[NormalizedInstrument]] = collections.defaultdict(list)
        if not market_ids:
            return {}
        with self._lock:
            c = self.conn
            for i in range(0, len(market_ids), 400):
                ch = list(market_ids[i : i + 400])
                q_marks = ",".join("?" for _ in ch)
                rows = c.execute(
                    f"SELECT * FROM instruments WHERE market_id IN ({q_marks}) ORDER BY market_id, outcome_index",
                    ch,
                ).fetchall()
                for r in rows:
                    out[str(r["market_id"])].append(self._row_to_instrument(r))
        return {k: tuple(v) for k, v in out.items()}

    def get_instrument(self, token_id: str) -> Optional[NormalizedInstrument]:
        with self._lock:
            row = self.conn.execute("SELECT * FROM instruments WHERE token_id=?", (str(token_id),)).fetchone()
            return self._row_to_instrument(row) if row is not None else None

    def get_market(self, market_id: str) -> Optional[NormalizedMarket]:
        mid = str(market_id)
        with self._lock:
            row = self.conn.execute("SELECT * FROM markets WHERE market_id=?", (mid,)).fetchone()
            if row is None:
                return None
            inst_map = self._load_instruments_by_market_ids([mid])
            return self._row_to_market(row, inst_map.get(mid, ()))

    def get_market_by_condition(self, condition_id: str) -> Optional[NormalizedMarket]:
        cid = str(condition_id).strip()
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM markets WHERE lower(condition_id)=lower(?) LIMIT 1", (cid,)
            ).fetchone()
            if row is None:
                return None
            mid = str(row["market_id"])
            inst_map = self._load_instruments_by_market_ids([mid])
            return self._row_to_market(row, inst_map.get(mid, ()))

    def get_event(self, event_id: str) -> Optional[NormalizedEvent]:
        eid = str(event_id)
        with self._lock:
            ev_row = self.conn.execute("SELECT * FROM events WHERE event_id=?", (eid,)).fetchone()
            if ev_row is None:
                return None
            mkt_rows = self.conn.execute("SELECT * FROM markets WHERE event_id=? ORDER BY market_id", (eid,)).fetchall()
            mids = [str(r["market_id"]) for r in mkt_rows]
            inst_map = self._load_instruments_by_market_ids(mids)
            mkts = tuple(self._row_to_market(r, inst_map.get(str(r["market_id"]), ())) for r in mkt_rows)
            return NormalizedEvent(
                event_id=str(ev_row["event_id"]),
                slug=str(ev_row["slug"]),
                ticker=str(ev_row["ticker"]),
                title=str(ev_row["title"]),
                series_slug=str(ev_row["series_slug"]),
                category=str(ev_row["category"]),
                tags=tuple(_json_loads(ev_row["tags_json"])),
                active=bool(ev_row["active"]),
                closed=bool(ev_row["closed"]),
                archived=bool(ev_row["archived"]),
                enable_order_book=bool(ev_row["enable_order_book"]),
                neg_risk=bool(ev_row["neg_risk"]),
                enable_neg_risk=bool(ev_row["enable_neg_risk"]),
                neg_risk_augmented=bool(ev_row["neg_risk_augmented"]),
                cumulative_markets=bool(ev_row["cumulative_markets"]),
                neg_risk_market_id=str(ev_row["neg_risk_market_id"]),
                resolution_source=str(ev_row["resolution_source"]),
                start_date_iso=str(ev_row["start_date_iso"]),
                end_date_iso=str(ev_row["end_date_iso"]),
                end_ts=float(ev_row["end_ts"]) if ev_row["end_ts"] is not None else None,
                volume_24hr=float(ev_row["volume_24hr"]),
                volume_total=float(ev_row["volume_total"]),
                liquidity_usd=float(ev_row["liquidity_usd"]),
                markets=mkts,
                structure_kind=str(ev_row["structure_kind"]),
                has_other_outcome=bool(ev_row["has_other_outcome"]),
                placeholder_market_count=int(ev_row["placeholder_market_count"]),
                active_market_count=int(ev_row["active_market_count"]),
                tradable_market_count=int(ev_row["tradable_market_count"]),
                total_market_count=int(ev_row["total_market_count"]),
                skip_codes=tuple(_json_loads(ev_row["skip_codes_json"])),
                metadata_digest=str(ev_row["metadata_digest"]),
            )

    def iter_markets(
        self,
        *,
        active_only: bool = True,
        execution_eligible_only: bool = False,
        enable_order_book_only: bool = False,
        zero_fee_only: bool = False,
        neg_risk_only: bool = False,
        category: Optional[str] = None,
        uma_status: Optional[str] = None,
        limit: Optional[int] = None,
        batch_size: int = 250,
    ) -> Iterator[NormalizedMarket]:
        clauses: List[str] = []
        params: List[Any] = []
        if active_only:
            clauses.append("active=1 AND closed=0 AND archived=0")
        if execution_eligible_only:
            clauses.append("execution_eligible=1")
        if enable_order_book_only:
            clauses.append("enable_order_book=1")
        if zero_fee_only:
            clauses.append("fees_enabled=0 AND fee_rate_bps<=0.000001")
        if neg_risk_only:
            clauses.append("neg_risk=1")
        if category is not None:
            clauses.append("category=?")
            params.append(str(category))
        if uma_status is not None:
            clauses.append("uma_resolution_status=?")
            params.append(str(uma_status))

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        lim_sql = f"LIMIT {int(limit)}" if limit is not None else ""
        sql = f"SELECT * FROM markets {where_sql} ORDER BY volume_24hr DESC, market_id ASC {lim_sql}"

        with self._lock:
            cur = self.conn.execute(sql, params)
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                mids = [str(r["market_id"]) for r in rows]
                inst_map = self._load_instruments_by_market_ids(mids)
                for r in rows:
                    yield self._row_to_market(r, inst_map.get(str(r["market_id"]), ()))

    def iter_events(
        self,
        *,
        active_only: bool = True,
        neg_risk_only: bool = False,
        multi_market_only: bool = False,
        category: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[NormalizedEvent]:
        clauses: List[str] = []
        params: List[Any] = []
        if active_only:
            clauses.append("active=1 AND closed=0 AND archived=0")
        if neg_risk_only:
            clauses.append("neg_risk=1")
        if multi_market_only:
            clauses.append("active_market_count>=2")
        if category is not None:
            clauses.append("category=?")
            params.append(str(category))
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        lim_sql = f"LIMIT {int(limit)}" if limit is not None else ""
        sql = f"SELECT event_id FROM events {where_sql} ORDER BY volume_24hr DESC, event_id ASC {lim_sql}"

        with self._lock:
            eids = [str(r[0]) for r in self.conn.execute(sql, params).fetchall()]
        for eid in eids:
            ev = self.get_event(eid)
            if ev is not None:
                yield ev

    def count_summary(self) -> Dict[str, int]:
        with self._lock:
            c = self.conn
            return {
                "events_total": int(c.execute("SELECT COUNT(*) FROM events").fetchone()[0]),
                "events_active": int(c.execute("SELECT COUNT(*) FROM events WHERE active=1 AND closed=0 AND archived=0").fetchone()[0]),
                "markets_total": int(c.execute("SELECT COUNT(*) FROM markets").fetchone()[0]),
                "markets_active": int(c.execute("SELECT COUNT(*) FROM markets WHERE active=1 AND closed=0 AND archived=0").fetchone()[0]),
                "markets_execution_eligible": int(c.execute("SELECT COUNT(*) FROM markets WHERE execution_eligible=1").fetchone()[0]),
                "instruments_total": int(c.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]),
                "instruments_tradable": int(c.execute("SELECT COUNT(*) FROM instruments WHERE is_tradable=1").fetchone()[0]),
            }

    def update_books_from_snapshots(
        self,
        snapshots: Mapping[str, NormalizedBookSnapshot],
        *,
        now_ts: Optional[float] = None,
    ) -> Dict[str, int]:
        """
        Persists observed L2 depth & top-of-book prices onto `instruments` and refines
        `ZERO_RESTING_DEPTH` / `ONE_SIDED_BOOK` skip codes on both `instruments` and `markets`.
        """
        if not snapshots:
            return {"instruments_updated": 0, "zero_depth_marked": 0, "one_sided_marked": 0, "two_sided_healthy": 0}

        eval_ts = float(time.time() if now_ts is None else now_ts)
        tids = list(snapshots.keys())
        zero_cnt = 0
        one_cnt = 0
        two_cnt = 0

        with self._lock:
            c = self.conn
            existing_rows: Dict[str, sqlite3.Row] = {}
            for i in range(0, len(tids), 400):
                ch = tids[i : i + 400]
                q_marks = ",".join("?" for _ in ch)
                for r in c.execute(f"SELECT token_id, market_id, skip_codes_json FROM instruments WHERE token_id IN ({q_marks})", ch):
                    existing_rows[str(r["token_id"])] = r

            inst_updates: List[Tuple[Any, ...]] = []
            affected_markets: Set[str] = set()
            for tid, snap in snapshots.items():
                r = existing_rows.get(tid)
                if r is None:
                    continue
                affected_markets.add(str(r["market_id"]))
                base_skips = [
                    sc
                    for sc in _json_loads(r["skip_codes_json"])
                    if sc not in (SkipReason.ZERO_RESTING_DEPTH.value, SkipReason.ONE_SIDED_BOOK.value, SkipReason.STALE_BOOK.value)
                ]
                if snap.is_empty:
                    base_skips.append(SkipReason.ZERO_RESTING_DEPTH.value)
                    zero_cnt += 1
                elif snap.is_one_sided:
                    base_skips.append(SkipReason.ONE_SIDED_BOOK.value)
                    one_cnt += 1
                else:
                    two_cnt += 1

                inst_updates.append(
                    (
                        snap.fetched_ts or eval_ts,
                        snap.best_bid if snap.best_bid > 0 else None,
                        snap.best_ask if snap.best_ask > 0 else None,
                        snap.resting_bid_depth_usd,
                        snap.resting_ask_depth_usd,
                        _json_dumps_str(base_skips),
                        tid,
                    )
                )

            c.execute("BEGIN")
            try:
                if inst_updates:
                    c.executemany(
                        """
                        UPDATE instruments
                        SET last_book_ts=?, best_bid=?, best_ask=?, resting_bid_depth_usd=?,
                            resting_ask_depth_usd=?, skip_codes_json=?
                        WHERE token_id=?
                        """,
                        inst_updates,
                    )
                if affected_markets:
                    aff_list = list(affected_markets)
                    for i in range(0, len(aff_list), 300):
                        ch_m = aff_list[i : i + 300]
                        q_m = ",".join("?" for _ in ch_m)
                        inst_rows = c.execute(
                            f"SELECT market_id, resting_bid_depth_usd, resting_ask_depth_usd FROM instruments WHERE market_id IN ({q_m})",
                            ch_m,
                        ).fetchall()
                        depth_by_m: Dict[str, List[Tuple[float, float]]] = collections.defaultdict(list)
                        for ir in inst_rows:
                            depth_by_m[str(ir["market_id"])].append(
                                (float(ir["resting_bid_depth_usd"] or 0.0), float(ir["resting_ask_depth_usd"] or 0.0))
                            )
                        mkt_rows = c.execute(
                            f"SELECT market_id, skip_codes_json FROM markets WHERE market_id IN ({q_m})",
                            ch_m,
                        ).fetchall()
                        m_upd: List[Tuple[str, str]] = []
                        for mr in mkt_rows:
                            mid = str(mr["market_id"])
                            ds = depth_by_m.get(mid, [])
                            orig_sk = _json_loads(mr["skip_codes_json"])
                            sk = [
                                s
                                for s in orig_sk
                                if s not in (SkipReason.ZERO_RESTING_DEPTH.value, SkipReason.ONE_SIDED_BOOK.value)
                            ]
                            if ds and all(bd <= 0.0 and ad <= 0.0 for bd, ad in ds):
                                sk.append(SkipReason.ZERO_RESTING_DEPTH.value)
                            elif ds and any((bd <= 0.0) != (ad <= 0.0) for bd, ad in ds):
                                sk.append(SkipReason.ONE_SIDED_BOOK.value)
                            if sk != orig_sk:
                                m_upd.append((_json_dumps_str(sk), mid))
                        if m_upd:
                            c.executemany("UPDATE markets SET skip_codes_json=? WHERE market_id=?", m_upd)
                c.commit()
            except Exception:
                c.rollback()
                raise

        return {
            "instruments_updated": len(inst_updates),
            "zero_depth_marked": zero_cnt,
            "one_sided_marked": one_cnt,
            "two_sided_healthy": two_cnt,
        }

    def get_surveillance_state(self, key: str, default: str = "") -> str:
        with self._lock:
            row = self.conn.execute("SELECT value_text FROM surveillance_state WHERE key=?", (key,)).fetchone()
            return str(row[0]) if row is not None else default

    def set_surveillance_state(self, key: str, value: str, now_ts: Optional[float] = None) -> None:
        ts = float(time.time() if now_ts is None else now_ts)
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO surveillance_state VALUES (?,?,?)",
                (key, str(value), ts),
            )
            self.conn.commit()


# ===========================================================================
# Batched CLOB `/books` Fetcher & Two-Layer Surveillance Scheduler
# ===========================================================================


def fetch_clob_books_batched(
    token_ids: Sequence[str],
    *,
    http_client: Optional[PersistentJsonHttpClient] = None,
    batch_size: int = CLOB_BOOKS_DEFAULT_BATCH_SIZE,
    now_ts: Optional[float] = None,
    max_levels: int = 25,
) -> Tuple[Dict[str, NormalizedBookSnapshot], Dict[str, Any]]:
    """
    Fetches L2 order books via batched `POST https://clob.polymarket.com/books`
    (`<= 500` tokens per request; default `450`) over persistent keep-alive TLS sockets.
    """
    uniq_tids = list(dict.fromkeys(str(t).strip() for t in token_ids if t and str(t).strip()))
    t0 = time.perf_counter()
    fetch_ts = float(time.time() if now_ts is None else now_ts)
    if not uniq_tids:
        return {}, {
            "tokens_requested": 0,
            "books_returned": 0,
            "missing_or_unlisted_tokens": 0,
            "batches_sent": 0,
            "wall_time_sec": 0.0,
            "fetch_timestamp_sec": fetch_ts,
        }

    eff_batch = min(CLOB_BOOKS_MAX_BATCH_SIZE, max(1, int(batch_size)))
    own_client = http_client is None
    client = http_client or PersistentJsonHttpClient()
    out: Dict[str, NormalizedBookSnapshot] = {}
    batches = 0

    try:
        for idx in range(0, len(uniq_tids), eff_batch):
            chunk = uniq_tids[idx : idx + eff_batch]
            batches += 1
            payload = [{"token_id": tid} for tid in chunk]
            status, resp_data = client.request_json("POST", f"{CLOB_API_BASE}/books", json_body=payload)
            snap_ts = time.time() if now_ts is None else fetch_ts
            if status == 200 and isinstance(resp_data, list):
                for item in resp_data:
                    if isinstance(item, Mapping):
                        snap = NormalizedBookSnapshot.from_clob_dict(item, fetched_ts=snap_ts, max_levels=max_levels)
                        if snap.token_id:
                            out[snap.token_id] = snap
        # Any requested token omitted from a 200 `/books` response has zero active CLOB book
        for tid in uniq_tids:
            if tid not in out:
                out[tid] = NormalizedBookSnapshot(
                    token_id=tid,
                    bids=(),
                    asks=(),
                    best_bid=0.0,
                    best_bid_size=0.0,
                    best_ask=0.0,
                    best_ask_size=0.0,
                    resting_bid_depth_usd=0.0,
                    resting_ask_depth_usd=0.0,
                    tick_size=0.01,
                    min_order_size=5.0,
                    fetched_ts=fetch_ts,
                )
    finally:
        if own_client:
            client.close()

    elapsed = round(time.perf_counter() - t0, 4)
    non_empty = sum(1 for s in out.values() if not s.is_empty)
    return out, {
        "tokens_requested": len(uniq_tids),
        "books_returned_non_empty": non_empty,
        "empty_books": len(uniq_tids) - non_empty,
        "batches_sent": batches,
        "batch_size_cap": eff_batch,
        "wall_time_sec": elapsed,
        "fetch_timestamp_sec": fetch_ts,
    }


@dataclass(slots=True)
class SurveillancePollPlan:
    """Explicit Layer B (high-priority adaptive) + Layer A (full-universe sweep) poll allocation."""

    planned_at_ts: float
    layer_b_priority_tokens: Tuple[str, ...]
    layer_a_sweep_tokens: Tuple[str, ...]
    combined_unique_tokens: Tuple[str, ...]
    layer_a_cursor_before: str
    layer_a_cursor_after: str
    layer_a_wrapped_around: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planned_at_ts": round(self.planned_at_ts, 3),
            "layer_b_priority_count": len(self.layer_b_priority_tokens),
            "layer_a_sweep_count": len(self.layer_a_sweep_tokens),
            "combined_unique_count": len(self.combined_unique_tokens),
            "layer_a_cursor_before": self.layer_a_cursor_before,
            "layer_a_cursor_after": self.layer_a_cursor_after,
            "layer_a_wrapped_around": self.layer_a_wrapped_around,
        }


class TwoLayerSurveillanceScheduler:
    """
    Two-Layer Order-Book Surveillance Engine (`Section 10` / Agent 10):
      - **Layer A (Exhaustive Full-Universe Sweep Budget):**
        Maintains a durable lexicographic `token_id` round-robin cursor in `market_registry.sqlite3`
        (`surveillance_state.layer_a_cursor`). Every cycle allocates a guaranteed slice
        (`layer_a_tokens_per_cycle`) of tradable tokens so low-volume, newly-listed, or quiet
        markets NEVER permanently disappear or starve!
      - **Layer B (High-Priority Adaptive Book Polling):**
        Scores & polls high-priority structural candidates first:
          1. Explicitly pinned dormant / near-arb watch tokens (`register_priority_tokens`)
          2. Zero-fee (`feeRateBps == 0`) active markets & UMA `proposed` markets
          3. Multi-outcome closed NegRisk slates & expiring-soon (`<= 24h`) ladders
          4. High-activity / tight indicative sum (`|p_yes + p_no - 1.0| >= 0.005`) markets
      - **Bounded LRU Hot Book Cache (`max_hot_books = 8,000`):**
        Keeps RAM strictly bounded (`< 120 MiB`) while tracking exact staleness metrics.
    """

    def __init__(
        self,
        registry: FullUniverseRegistry,
        *,
        layer_a_tokens_per_cycle: int = 1350,
        layer_b_tokens_per_cycle: int = 1800,
        clob_batch_size: int = CLOB_BOOKS_DEFAULT_BATCH_SIZE,
        hot_freshness_sla_sec: float = 30.0,
        sweep_freshness_sla_sec: float = 900.0,
        max_hot_books_cached: int = 8000,
        clob_rate_budget: Optional[RateLimitBudget] = None,
    ) -> None:
        self.registry = registry
        self.layer_a_tokens_per_cycle = max(0, int(layer_a_tokens_per_cycle))
        self.layer_b_tokens_per_cycle = max(0, int(layer_b_tokens_per_cycle))
        self.clob_batch_size = min(CLOB_BOOKS_MAX_BATCH_SIZE, max(1, int(clob_batch_size)))
        self.hot_freshness_sla_sec = float(hot_freshness_sla_sec)
        self.sweep_freshness_sla_sec = float(sweep_freshness_sla_sec)
        self.max_hot_books_cached = max(100, int(max_hot_books_cached))
        self.clob_rate_budget = clob_rate_budget or RateLimitBudget(max_requests_per_window=80, window_sec=10.0)

        self._pinned_priority_tokens: collections.OrderedDict[str, str] = collections.OrderedDict()
        self._hot_books_lru: collections.OrderedDict[str, NormalizedBookSnapshot] = collections.OrderedDict()
        self.cycles_completed: int = 0
        self.layer_a_full_wraps: int = 0

    def register_priority_tokens(self, token_ids: Iterable[str], *, reason: str = "dormant_or_near_arb") -> int:
        """Pins tokens (e.g. from `DormantOpportunityStore` or active candidates) into Layer B."""
        added = 0
        for t in token_ids:
            ts = str(t or "").strip()
            if not ts:
                continue
            self._pinned_priority_tokens[ts] = reason
            self._pinned_priority_tokens.move_to_end(ts)
            added += 1
        while len(self._pinned_priority_tokens) > self.max_hot_books_cached:
            self._pinned_priority_tokens.popitem(last=False)
        return added

    def _select_layer_b_tokens(self, now_ts: float, budget: int) -> List[str]:
        if budget <= 0:
            return []
        selected: List[str] = []
        seen: Set[str] = set()

        def _push(tid: str) -> bool:
            if not tid or tid in seen:
                return len(selected) < budget
            seen.add(tid)
            selected.append(tid)
            return len(selected) < budget

        # 1. Pinned dormant/near-arb watch tokens that aren't ultra-fresh (`> 3s`)
        for tid in reversed(list(self._pinned_priority_tokens.keys())):
            snap = self._hot_books_lru.get(tid)
            if snap is not None and (now_ts - snap.fetched_ts) <= 3.0:
                continue
            if not _push(tid):
                return selected

        # 2. Structural priority SQL query:
        #    (a) zero-fee markets, (b) UMA proposed, (c) multi-outcome NegRisk / near-expiry / high-24h-volume,
        #    excluding tokens already refreshed within `hot_freshness_sla_sec * 0.5`.
        stale_cutoff = now_ts - (self.hot_freshness_sla_sec * 0.5)
        rem = budget - len(selected)
        sql = """
            SELECT i.token_id
            FROM instruments i
            JOIN markets m ON m.market_id = i.market_id
            WHERE i.is_tradable = 1
              AND m.execution_eligible = 1
              AND i.last_book_ts <= ?
            ORDER BY
              (CASE WHEN m.fees_enabled = 0 THEN 1 ELSE 0 END) DESC,
              (CASE WHEN m.uma_resolution_status = 'proposed' THEN 1 ELSE 0 END) DESC,
              (CASE WHEN m.end_ts IS NOT NULL AND m.end_ts > ? AND (m.end_ts - ?) <= 86400 THEN 1 ELSE 0 END) DESC,
              m.volume_24hr DESC,
              m.liquidity_usd DESC,
              i.token_id ASC
            LIMIT ?
        """
        with self.registry._lock:
            rows = self.registry.conn.execute(sql, (stale_cutoff, now_ts, now_ts, rem + 64)).fetchall()
        for r in rows:
            if not _push(str(r[0])):
                break
        return selected

    def _select_layer_a_sweep_tokens(
        self,
        now_ts: float,
        budget: int,
        exclude: Set[str],
    ) -> Tuple[List[str], str, str, bool]:
        cursor_before = self.registry.get_surveillance_state("layer_a_cursor", "")
        if budget <= 0:
            return [], cursor_before, cursor_before, False

        selected: List[str] = []
        wrapped = False
        with self.registry._lock:
            c = self.registry.conn
            rows_after = c.execute(
                """
                SELECT token_id FROM instruments
                WHERE is_tradable = 1 AND token_id > ?
                ORDER BY token_id ASC
                LIMIT ?
                """,
                (cursor_before, budget + len(exclude) + 32),
            ).fetchall()
            for r in rows_after:
                tid = str(r[0])
                if tid not in exclude:
                    selected.append(tid)
                    if len(selected) >= budget:
                        break

            if len(selected) < budget:
                # Reached end of universe -> wrap around to beginning so 100% of tokens cycle!
                wrapped = True
                need = budget - len(selected)
                rows_wrap = c.execute(
                    """
                    SELECT token_id FROM instruments
                    WHERE is_tradable = 1
                    ORDER BY token_id ASC
                    LIMIT ?
                    """,
                    (need + len(exclude) + len(selected) + 32,),
                ).fetchall()
                already = set(selected) | exclude
                for r in rows_wrap:
                    tid = str(r[0])
                    if tid not in already:
                        selected.append(tid)
                        already.add(tid)
                        if len(selected) >= budget:
                            break

        cursor_after = selected[-1] if selected else ("" if wrapped else cursor_before)
        if wrapped:
            self.layer_a_full_wraps += 1
        return selected, cursor_before, cursor_after, wrapped

    def plan_next_poll_batch(self, *, now_ts: Optional[float] = None) -> SurveillancePollPlan:
        eval_ts = float(time.time() if now_ts is None else now_ts)
        b_toks = self._select_layer_b_tokens(eval_ts, self.layer_b_tokens_per_cycle)
        a_toks, cur_before, cur_after, wrapped = self._select_layer_a_sweep_tokens(
            eval_ts,
            self.layer_a_tokens_per_cycle,
            exclude=set(b_toks),
        )
        combined = tuple(dict.fromkeys([*b_toks, *a_toks]))
        return SurveillancePollPlan(
            planned_at_ts=eval_ts,
            layer_b_priority_tokens=tuple(b_toks),
            layer_a_sweep_tokens=tuple(a_toks),
            combined_unique_tokens=combined,
            layer_a_cursor_before=cur_before,
            layer_a_cursor_after=cur_after,
            layer_a_wrapped_around=wrapped,
        )

    def execute_poll_cycle(
        self,
        *,
        http_client: Optional[PersistentJsonHttpClient] = None,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Executes one coordinated Layer B + Layer A surveillance cycle and updates registry + LRU."""
        eval_ts = float(time.time() if now_ts is None else now_ts)
        plan = self.plan_next_poll_batch(now_ts=eval_ts)

        own_client = http_client is None
        client = http_client or PersistentJsonHttpClient(clob_budget=self.clob_rate_budget)
        try:
            snaps, poll_meta = fetch_clob_books_batched(
                plan.combined_unique_tokens,
                http_client=client,
                batch_size=self.clob_batch_size,
                now_ts=now_ts,
            )
        finally:
            if own_client:
                client.close()

        # Advance Layer A cursor only after successful fetch
        self.registry.set_surveillance_state("layer_a_cursor", plan.layer_a_cursor_after, now_ts=eval_ts)
        db_upd = self.registry.update_books_from_snapshots(snaps, now_ts=eval_ts)

        for tid, sn in snaps.items():
            if not sn.is_empty:
                self._hot_books_lru[tid] = sn
                self._hot_books_lru.move_to_end(tid)
        while len(self._hot_books_lru) > self.max_hot_books_cached:
            self._hot_books_lru.popitem(last=False)

        self.cycles_completed += 1
        staleness = self.get_staleness_report(now_ts=time.time() if now_ts is None else eval_ts)
        return {
            "cycle_index": self.cycles_completed,
            "plan": plan.to_dict(),
            "poll_meta": poll_meta,
            "registry_updates": db_upd,
            "staleness_report": staleness,
            "hot_books_lru_size": len(self._hot_books_lru),
            "rss_mib": get_process_rss_mib(),
        }

    def get_fresh_book(self, token_id: str, *, max_age_sec: Optional[float] = None, now_ts: Optional[float] = None) -> Optional[NormalizedBookSnapshot]:
        snap = self._hot_books_lru.get(str(token_id))
        if snap is None:
            return None
        eval_ts = float(time.time() if now_ts is None else now_ts)
        ttl = self.hot_freshness_sla_sec if max_age_sec is None else float(max_age_sec)
        if (eval_ts - snap.fetched_ts) > ttl:
            return None
        return snap

    def export_fresh_clob_books_dict(
        self,
        *,
        max_age_sec: Optional[float] = None,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Dict[str, Any]]:
        eval_ts = float(time.time() if now_ts is None else now_ts)
        ttl = self.sweep_freshness_sla_sec if max_age_sec is None else float(max_age_sec)
        return {
            tid: snap.to_clob_dict()
            for tid, snap in self._hot_books_lru.items()
            if (eval_ts - snap.fetched_ts) <= ttl
        }

    def get_staleness_report(self, *, now_ts: Optional[float] = None) -> Dict[str, Any]:
        eval_ts = float(time.time() if now_ts is None else now_ts)
        hot_cut = eval_ts - self.hot_freshness_sla_sec
        sweep_cut = eval_ts - self.sweep_freshness_sla_sec
        with self.registry._lock:
            c = self.registry.conn
            row = c.execute(
                """
                SELECT
                    COUNT(*) AS tradable_total,
                    SUM(CASE WHEN last_book_ts <= 0 THEN 1 ELSE 0 END) AS never_polled,
                    SUM(CASE WHEN last_book_ts > 0 AND last_book_ts >= ? THEN 1 ELSE 0 END) AS fresh_hot,
                    SUM(CASE WHEN last_book_ts > 0 AND last_book_ts >= ? THEN 1 ELSE 0 END) AS fresh_sweep,
                    SUM(CASE WHEN last_book_ts > 0 AND last_book_ts < ? THEN 1 ELSE 0 END) AS stale_beyond_sweep,
                    MIN(CASE WHEN last_book_ts > 0 THEN last_book_ts ELSE NULL END) AS oldest_polled_ts,
                    SUM(CASE WHEN resting_bid_depth_usd > 0 AND resting_ask_depth_usd > 0 THEN 1 ELSE 0 END) AS two_sided_books,
                    SUM(CASE WHEN last_book_ts > 0 AND resting_bid_depth_usd <= 0 AND resting_ask_depth_usd <= 0 THEN 1 ELSE 0 END) AS empty_books_observed
                FROM instruments
                WHERE is_tradable = 1
                """,
                (hot_cut, sweep_cut, sweep_cut),
            ).fetchone()

        tradable_total = int(row["tradable_total"] or 0)
        oldest_ts = row["oldest_polled_ts"]
        max_age_sec = round(eval_ts - float(oldest_ts), 2) if oldest_ts is not None else None
        est_cycles_for_100pct = (
            math.ceil(tradable_total / max(1, self.layer_a_tokens_per_cycle))
            if self.layer_a_tokens_per_cycle > 0 and tradable_total > 0
            else 0
        )
        return {
            "tradable_tokens_total": tradable_total,
            "never_polled_tokens": int(row["never_polled"] or 0),
            "fresh_within_hot_sla_tokens": int(row["fresh_hot"] or 0),
            "fresh_within_sweep_sla_tokens": int(row["fresh_sweep"] or 0),
            "stale_beyond_sweep_sla_tokens": int(row["stale_beyond_sweep"] or 0),
            "two_sided_books_observed": int(row["two_sided_books"] or 0),
            "empty_books_observed": int(row["empty_books_observed"] or 0),
            "max_observed_book_age_sec": max_age_sec,
            "layer_a_full_wraps": self.layer_a_full_wraps,
            "layer_a_cycles_for_full_universe_pass": est_cycles_for_100pct,
        }


__all__ = [
    "ALLOWED_PUBLIC_HOSTS",
    "CLOB_API_BASE",
    "CLOB_BOOKS_DEFAULT_BATCH_SIZE",
    "CLOB_BOOKS_MAX_BATCH_SIZE",
    "DEFAULT_COVERAGE_SNAPSHOT_PATH",
    "DEFAULT_REGISTRY_DB_PATH",
    "ExistingDominusV51CoverageTracker",
    "FullUniverseRegistry",
    "GAMMA_API_BASE",
    "HARD_EXECUTION_BLOCK_CODES",
    "KMIA_D001_FROZEN_MARKET_IDS",
    "NormalizedBookSnapshot",
    "NormalizedEvent",
    "NormalizedInstrument",
    "NormalizedMarket",
    "PersistentJsonHttpClient",
    "RateLimitBudget",
    "SkipReason",
    "SurveillancePollPlan",
    "SweepDiffStats",
    "TwoLayerSurveillanceScheduler",
    "detect_placeholder_or_other_outcome",
    "fetch_clob_books_batched",
    "get_process_rss_mib",
    "infer_primary_category",
    "is_valid_hex_condition_id",
    "normalize_gamma_event",
    "normalize_gamma_market",
    "parse_iso_timestamp",
]


"""
Universal Polymarket Directional Market Discovery, Taxonomy & Opportunity Scoring Engine
(`src/directional_alpha/universe_discovery.py`).

Agent A (`@universe-map`) — Dominus Directional Alpha Research Campaign.

Core Guarantees & Boundaries:
  1. Strict Read-Only Public Research Mode:
     - Connects ONLY to public `https://gamma-api.polymarket.com` and `https://clob.polymarket.com`.
     - Zero private keys, zero order placement, zero mutations to production files.
  2. Zero Hardcoded Symbol or Category Caps:
     - Paginates 100% of active unclosed events & child markets via `/events/keyset` (`Accept-Encoding: gzip`
       unlocking full 100-event pages with zero offset-ceiling truncation), cross-reconciled with
       CLOB `/sampling-markets`, stratified live CLOB `POST /books` L2 snapshots, live CLOB
       `GET /fee-rate` schedule verification, and multi-category recently resolved (`closed=true`)
       contracts via `/events` and `/markets` (including low-volume and losing contracts to prevent
       survivorship bias).
  3. Safety & Structural Invariants:
     - Enforces `D-001` non-interference on disputed Miami `KMIA` markets (`6707502`, `6707503`)
       and any `umaResolutionStatus == "disputed"` market (`PERM_KMIA_D001_PROTECTED_LOCK`,
       `PERM_UMA_DISPUTED_FROZEN`).
     - Explicitly separates `PERMANENT_EXCLUSION` (hard structural, safety, or post-maturity hazards)
       from `COMPUTATIONAL_DEPRIORITIZATION` (illiquid, wide-spread, clamped-tail, or unquoted markets
       retained 100% in the inventory).
  4. Forecasting Inefficiency vs. Execution Friction Scoring:
     - Scores markets on domain calibration potential, multi-outcome cross-leg lag, new-listing price
       discovery (`<48h`), behavioral tail/jump distortion, and capital velocity MINUS bid-ask spread,
       curved category taker fee drag (`rate * (p*(1-p))^exp`), depth scarcity, and oracle ambiguity —
       NEVER raw volume alone.
"""

from __future__ import annotations

import collections
import gc
import gzip
import http.client
import json
import math
import os
import re
import ssl
import statistics
import threading
import time
import urllib.parse
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

try:
    import orjson as _orjson  # type: ignore
except ImportError:  # pragma: no cover
    _orjson = None


GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
ALLOWED_PUBLIC_HOSTS: frozenset[str] = frozenset({"gamma-api.polymarket.com", "clob.polymarket.com"})

# Binding D-001 frozen disputed KMIA Nov 7 market IDs (100% non-interference)
KMIA_D001_FROZEN_MARKET_IDS: frozenset[str] = frozenset({"6707502", "6707503"})

# CLOB POST /books batch limit (server max is 500; 450 provides clean margin)
CLOB_BOOKS_BATCH_SIZE = 450

CANONICAL_CATEGORIES: Tuple[str, ...] = (
    "crypto",
    "sports",
    "politics",
    "economics_macro",
    "finance",
    "weather",
    "geopolitics",
    "tech_ai",
    "culture_entertainment",
    "science",
)

# Exclusion reason classifications
PERMANENT_EXCLUSION_CODES: frozenset[str] = frozenset(
    {
        "PERM_KMIA_D001_PROTECTED_LOCK",
        "PERM_UMA_DISPUTED_FROZEN",
        "PERM_UMA_PROPOSED_POST_EVENT",
        "PERM_PAST_MATURITY_UNRESOLVED",
        "PERM_CLOSED_OR_ARCHIVED",
        "PERM_INACTIVE_OR_PAUSED",
        "PERM_ORDERBOOK_DISABLED",
        "PERM_NOT_ACCEPTING_ORDERS",
        "PERM_AUGMENTED_PLACEHOLDER",
        "PERM_MISSING_VALID_TOKENS_OR_CONDITION",
    }
)

COMPUTATIONAL_DEPRIORITIZATION_CODES: frozenset[str] = frozenset(
    {
        "DEPRIO_NO_TWO_SIDED_QUOTES",
        "DEPRIO_EXTREME_SPREAD_GT_20C",
        "DEPRIO_SUB_100_USD_LIQUIDITY",
        "DEPRIO_CLAMPED_TAIL_995_OR_005",
        "DEPRIO_MUTABLE_NEGRISK_OTHER",
        "DEPRIO_ZERO_HISTORICAL_VOLUME",
    }
)


# ===========================================================================
# Serialization & Parsing Helpers (Pure-Python + Optional `orjson`)
# ===========================================================================


def json_loads(raw: bytes | str) -> Any:
    if _orjson is not None:
        return _orjson.loads(raw)
    if isinstance(raw, bytes):
        return json.loads(raw.decode("utf-8", errors="replace"))
    return json.loads(raw)


def json_dumps_bytes(obj: Any, *, indent: bool = False) -> bytes:
    if _orjson is not None:
        opts = _orjson.OPT_APPEND_NEWLINE
        if indent:
            opts |= _orjson.OPT_INDENT_2
        return _orjson.dumps(obj, option=opts)
    if indent:
        return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return (json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def write_atomic_json_file(path: Path | str, payload: Any, *, indent: bool = False) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f"{target.suffix}.tmp.{os.getpid()}")
    raw_bytes = json_dumps_bytes(payload, indent=indent)
    tmp.write_bytes(raw_bytes)
    os.replace(tmp, target)
    return len(raw_bytes)


def safe_float(val: Any, default: Optional[float] = 0.0) -> Optional[float]:
    if val is None or val == "":
        return default
    try:
        fv = float(val)
        return fv if math.isfinite(fv) else default
    except Exception:
        return default


def parse_iso_ts(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        fv = float(val)
        if not math.isfinite(fv) or fv <= 0:
            return None
        return fv / 1000.0 if fv > 1e11 else fv
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        elif " " in s and "T" not in s:
            s = s.replace(" ", "T", 1)
        # Handle Postgres short timezone offsets like `+00` or `-05`
        if re.search(r"[+-]\d{2}$", s):
            s = s + ":00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    except Exception:
        return None


def parse_str_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                parsed = json_loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if x is not None and str(x).strip()]
            except Exception:
                return []
        return [s]
    if isinstance(raw, (list, tuple)):
        out: List[str] = []
        for item in raw:
            if isinstance(item, Mapping):
                lbl = str(item.get("slug") or item.get("label") or item.get("name") or "").strip()
                if lbl:
                    out.append(lbl)
            elif item is not None:
                si = str(item).strip()
                if si:
                    out.append(si)
        return out
    return []


def parse_float_list(raw: Any) -> List[float]:
    if raw is None:
        return []
    seq: Any = raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s or not s.startswith("["):
            return []
        try:
            seq = json_loads(s)
        except Exception:
            return []
    if isinstance(seq, (list, tuple)):
        out: List[float] = []
        for x in seq:
            fv = safe_float(x, 0.0)
            out.append(float(fv or 0.0))
        return out
    return []


def is_valid_condition_id(cid: str) -> bool:
    s = str(cid or "").strip()
    if len(s) != 66 or not s.startswith("0x"):
        return False
    return all(ch in "0123456789abcdefABCDEF" for ch in s[2:])


def quantiles_from_sorted(sorted_vals: Sequence[float]) -> Dict[str, Optional[float]]:
    n = len(sorted_vals)
    if n == 0:
        return {"count": 0, "min": None, "p10": None, "p25": None, "median": None, "p75": None, "p90": None, "max": None, "mean": None}

    def _pct(q: float) -> float:
        if n == 1:
            return round(sorted_vals[0], 6)
        idx = q * (n - 1)
        lo = int(math.floor(idx))
        hi = min(n - 1, lo + 1)
        frac = idx - lo
        return round(sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac, 6)

    return {
        "count": n,
        "min": round(sorted_vals[0], 6),
        "p10": _pct(0.10),
        "p25": _pct(0.25),
        "median": _pct(0.50),
        "p75": _pct(0.75),
        "p90": _pct(0.90),
        "max": round(sorted_vals[-1], 6),
        "mean": round(sum(sorted_vals) / n, 6),
    }


# ===========================================================================
# Public Keep-Alive HTTP Client (`gamma-api.polymarket.com` & `clob.polymarket.com`)
# ===========================================================================


@dataclass(slots=True)
class RateLimitWindow:
    """Sliding-window HTTP request budget to prevent 429 bursts."""

    max_requests: int = 150
    window_sec: float = 10.0
    _timestamps: Deque[float] = field(default_factory=collections.deque, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def acquire(self) -> None:
        while True:
            wait_sec = 0.0
            with self._lock:
                now = time.monotonic()
                cutoff = now - self.window_sec
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()
                if len(self._timestamps) >= self.max_requests:
                    wait_sec = max(0.005, (self._timestamps[0] + self.window_sec) - now + 0.005)
                else:
                    self._timestamps.append(now)
                    return
            time.sleep(min(wait_sec, 1.0))


class PublicPolymarketDiscoveryClient:
    """
    Zero-credential keep-alive HTTPS JSON client strictly restricted to public
    Polymarket discovery & market-data hosts (`gamma-api.polymarket.com`, `clob.polymarket.com`).
    """

    def __init__(
        self,
        *,
        timeout_sec: float = 20.0,
        max_retries: int = 3,
        gamma_window: Optional[RateLimitWindow] = None,
        clob_window: Optional[RateLimitWindow] = None,
        requester_override: Optional[Callable[[str, str, Optional[bytes]], Tuple[int, Any]]] = None,
    ) -> None:
        self.timeout_sec = float(timeout_sec)
        self.max_retries = max(1, int(max_retries))
        self.gamma_window = gamma_window or RateLimitWindow(max_requests=175, window_sec=10.0)
        self.clob_window = clob_window or RateLimitWindow(max_requests=100, window_sec=10.0)
        self._requester_override = requester_override
        self._ssl_ctx = ssl.create_default_context()
        self._pool: Dict[str, List[http.client.HTTPSConnection]] = defaultdict(list)
        self._pool_lock = threading.Lock()
        self.stats: Counter[str] = Counter()

    def _checkout(self, host: str) -> http.client.HTTPSConnection:
        if host not in ALLOWED_PUBLIC_HOSTS:
            raise ValueError(f"Host {host!r} violates strict public Polymarket research allowlist")
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

    def request_json(self, method: str, url: str, *, json_body: Any = None) -> Tuple[int, Any]:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower()
        if host not in ALLOWED_PUBLIC_HOSTS:
            raise ValueError(f"Host {host!r} violates strict public Polymarket research allowlist")

        body_bytes: Optional[bytes] = None
        if json_body is not None:
            body_bytes = json_dumps_bytes(json_body, indent=False).rstrip(b"\n")

        (self.gamma_window if "gamma-api" in host else self.clob_window).acquire()

        if self._requester_override is not None:
            status, payload = self._requester_override(method.upper(), url, body_bytes)
            self.stats[f"http_{status}"] += 1
            return status, payload

        path_q = parsed.path or "/"
        if parsed.query:
            path_q = f"{path_q}?{parsed.query}"

        headers = {
            "User-Agent": "DominusDirectionalAlphaDiscovery/1.0",
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
                conn.request(method.upper(), path_q, body=body_bytes, headers=headers)
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
                    self.stats["retries"] += 1
                    time.sleep(min(4.0, 0.35 * (2 ** attempt)))
                    continue

                if not raw:
                    return status, None
                if enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    raw = zlib.decompress(raw)
                try:
                    return status, json_loads(raw)
                except Exception:
                    return status, raw.decode("utf-8", errors="replace")
            except Exception as exc:
                last_exc = exc
                self.stats["reconnects"] += 1
                try:
                    conn.close()
                except Exception:
                    pass
                if attempt + 1 < self.max_retries:
                    time.sleep(min(2.0, 0.2 * (2 ** attempt)))
        raise RuntimeError(f"{method} {url} failed after {self.max_retries} attempts: {last_exc}")


# ===========================================================================
# Unrestricted Multi-Category & Subcategory Taxonomy Classifier
# ===========================================================================

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

_CRYPTO_ASSET_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("BTC", re.compile(r"\b(?:bitcoin|btc|\$btc)\b", re.IGNORECASE)),
    ("ETH", re.compile(r"\b(?:ethereum|ether|eth|\$eth)\b", re.IGNORECASE)),
    ("SOL", re.compile(r"\b(?:solana|sol|\$sol)\b", re.IGNORECASE)),
    ("XRP", re.compile(r"\b(?:ripple|xrp|\$xrp)\b", re.IGNORECASE)),
    ("DOGE", re.compile(r"\b(?:dogecoin|doge|\$doge)\b", re.IGNORECASE)),
    ("BNB", re.compile(r"\b(?:binance\s*coin|bnb|\$bnb)\b", re.IGNORECASE)),
    ("HYPE", re.compile(r"\b(?:hyperliquid|hype|\$hype)\b", re.IGNORECASE)),
    ("ZEC", re.compile(r"\b(?:zcash|zec|\$zec)\b", re.IGNORECASE)),
    ("SUI", re.compile(r"\b(?:sui|\$sui)\b", re.IGNORECASE)),
    ("ADA", re.compile(r"\b(?:cardano|ada|\$ada)\b", re.IGNORECASE)),
    ("AVAX", re.compile(r"\b(?:avalanche|avax|\$avax)\b", re.IGNORECASE)),
    ("LINK", re.compile(r"\b(?:chainlink|link|\$link)\b", re.IGNORECASE)),
    ("TON", re.compile(r"\b(?:toncoin|ton|\$ton)\b", re.IGNORECASE)),
    ("LTC", re.compile(r"\b(?:litecoin|ltc|\$ltc)\b", re.IGNORECASE)),
    ("PEPE", re.compile(r"\b(?:pepe|\$pepe)\b", re.IGNORECASE)),
    ("TRUMP_TOKEN", re.compile(r"\b(?:\$trump|trump\s+memecoin|official\s+trump\s+token)\b", re.IGNORECASE)),
)

_WEATHER_CITY_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("NYC_KNYC", re.compile(r"\b(?:nyc|new\s+york(?:\s+city)?|central\s+park|knyc|klga)\b", re.IGNORECASE)),
    ("MIAMI_KMIA", re.compile(r"\b(?:miami|kmia)\b", re.IGNORECASE)),
    ("CHICAGO_KORD", re.compile(r"\b(?:chicago|kord|kmdw)\b", re.IGNORECASE)),
    ("LONDON_EGLC", re.compile(r"\b(?:london|eglc|egll)\b", re.IGNORECASE)),
    ("SEOUL_RKSS", re.compile(r"\b(?:seoul|rkss|rksi)\b", re.IGNORECASE)),
    ("PARIS_LFPG", re.compile(r"\b(?:paris|lfpg|lfpb)\b", re.IGNORECASE)),
    ("TORONTO_CYYZ", re.compile(r"\b(?:toronto|cyyz|cytz)\b", re.IGNORECASE)),
    ("DALLAS_KDAL", re.compile(r"\b(?:dallas|kdal|kdfw)\b", re.IGNORECASE)),
    ("ATLANTA_KATL", re.compile(r"\b(?:atlanta|katl)\b", re.IGNORECASE)),
    ("SEATTLE_KSEA", re.compile(r"\b(?:seattle|ksea)\b", re.IGNORECASE)),
    ("BUENOS_AIRES_SAEZ", re.compile(r"\b(?:buenos\s+aires|saez|sabe)\b", re.IGNORECASE)),
    ("ANKARA_LTAC", re.compile(r"\b(?:ankara|ltac)\b", re.IGNORECASE)),
    ("LOS_ANGELES_KLAX", re.compile(r"\b(?:los\s+angeles|klax)\b", re.IGNORECASE)),
)

_STRIKE_THRESHOLD_RE = re.compile(
    r"(?:\babove\b|\bbelow\b|\breach\b|\bhit\b|\bdip\s+to\b|\bover\b|\bunder\b|\bbetween\b|\bless\s+than\b|\bmore\s+than\b|[<>]=?|\$\d+(?:[.,]\d+)?\s*[kmbtr]?)",
    re.IGNORECASE,
)
_TEMPORAL_LADDER_RE = re.compile(
    r"\b(?:by|before|in|on|prior\s+to)\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|q[1-4]\s*20\d{2}|202[5-9])\b",
    re.IGNORECASE,
)
_NEGATED_QUESTION_RE = re.compile(
    r"(?:\bwill\b[^?]{1,80}\bnot\b|\bfail\s+to\b|\bnever\b|\bwithout\b|\bwon't\b|\bno\s+(?:rate\s+cut|ceasefire|recession|change)\b)",
    re.IGNORECASE,
)


def detect_placeholder_and_other(
    *,
    question: str,
    group_item_title: str,
    slug: str,
    neg_risk: bool,
    neg_risk_augmented: bool,
    neg_risk_other_flag: bool,
    active: bool,
    enable_order_book: bool,
) -> Tuple[bool, bool]:
    lbl = (group_item_title or "").strip()
    q_clean = (question or "").strip()
    slug_l = (slug or "").strip().lower()

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


def classify_market_taxonomy(
    *,
    tags: Sequence[str],
    event_slug: str,
    market_slug: str,
    event_title: str,
    question: str,
    fee_type: str,
    start_ts: Optional[float],
    end_ts: Optional[float],
    now_ts: float,
) -> Tuple[str, str, str]:
    """
    Classifies any Polymarket contract into `(category, subcategory, asset_or_entity)` across
    all 10 canonical domains with zero hardcoded symbol/category caps.
    """
    tag_set = {t.lower().strip() for t in tags if t}
    ft_l = (fee_type or "").lower()
    txt = f"{event_slug} {market_slug} {event_title} {question}".lower()

    # 1. WEATHER (check before general/politics so city names never misroute)
    if (
        "weather" in tag_set
        or "weather" in ft_l
        or re.search(
            r"\b(?:highest\s+temperature|lowest\s+temperature|temperature\s+in|precipitation|rainfall|snowfall|inches\s+of\s+(?:rain|snow)|hurricane|tropical\s+storm|landfall|typhoon|tornado|hottest\s+(?:year|month))\b",
            txt,
        )
    ):
        station = "WEATHER_OTHER"
        for code, pat in _WEATHER_CITY_PATTERNS:
            if pat.search(txt):
                station = code
                break
        if re.search(r"\b(?:hurricane|tropical\s+storm|typhoon|cyclone|tornado|landfall|category\s+[1-5])\b", txt):
            sub = "weather_hurricane_storm_extreme"
        elif re.search(r"\b(?:precipitation|rainfall|rain|snowfall|snow)\b", txt):
            sub = "weather_precipitation_snow"
        elif re.search(r"\b(?:hottest\s+year|hottest\s+month|global\s+warming|anomaly|el\s+nino|la\s+nina)\b", txt):
            sub = "weather_climate_longterm"
        else:
            sub = "weather_daily_temperature_bucket"
        return "weather", sub, station

    # 2. SPORTS (major/minor leagues, game outcomes, spreads, totals, props, live, futures)
    is_sports = bool(
        "sports" in ft_l
        or tag_set
        & {
            "sports", "nba", "nfl", "nhl", "mlb", "soccer", "football", "tennis", "esports",
            "ufc", "mma", "golf", "f1", "formula-1", "cricket", "basketball", "baseball",
            "hockey", "ncaa", "cfb", "cbb", "boxing", "atp", "wta", "premier-league", "ucl",
            "parlays", "wnba", "mls", "laliga", "bundesliga", "serie-a", "ligue-1",
        }
        or re.search(
            r"\b(?:nba|nfl|nhl|mlb|ufc|epl|uefa|champions\s+league|premier\s+league|world\s+cup|super\s+bowl|stanley\s+cup|atp|wta|counter-strike|cs2|dota\s*2|valorant|league\s+of\s+legends|spread:|o/u\s+\d|exact\s+score|both\s+teams\s+to\s+score)\b",
            txt,
        )
        or re.match(r"^(?:nba|nfl|nhl|mlb|cfb|cbb|epl|ucl|ufc|atp|wta|mls|wnba|cs2|lol|dota2|clf|uel|bun|lal|ser|lig)-", market_slug.lower())
    )
    if is_sports:
        league = "SPORTS_OTHER"
        for lg_code, lg_pat in (
            ("NBA", r"\b(?:nba|lakers|celtics|warriors|knicks|bucks)\b|^nba-"),
            ("NFL", r"\b(?:nfl|super\s+bowl|chiefs|eagles|bills|ravens|49ers)\b|^nfl-"),
            ("NHL", r"\b(?:nhl|stanley\s+cup)\b|^nhl-"),
            ("MLB", r"\b(?:mlb|world\s+series)\b|^mlb-"),
            ("NCAAF", r"\b(?:cfb|college\s+football|heisman)\b|^cfb-"),
            ("NCAAB", r"\b(?:cbb|march\s+madness|ncaa\s+basketball)\b|^cbb-"),
            ("SOCCER", r"\b(?:soccer|premier\s+league|epl|champions\s+league|ucl|la\s+liga|bundesliga|serie\s+a|mls|fifa|world\s+cup|fc|united\s+vs|exact\s+score|both\s+teams\s+to\s+score)\b|^(?:epl|ucl|mls|clf|uel|bun|lal|ser|lig)-"),
            ("TENNIS", r"\b(?:tennis|atp|wta|wimbledon|roland\s+garros|us\s+open|australian\s+open)\b|^(?:atp|wta)-"),
            ("ESPORTS", r"\b(?:esports|counter-strike|cs2|dota|valorant|league\s+of\s+legends|lol)\b|^(?:cs2|lol|dota)"),
            ("UFC_MMA", r"\b(?:ufc|mma|bellator)\b|^ufc-"),
            ("F1_MOTORSPORT", r"\b(?:formula\s*1|f1|grand\s+prix|nascar|indycar)\b"),
            ("GOLF", r"\b(?:pga|masters|ryder\s+cup|liv\s+golf|golf)\b"),
            ("CRICKET", r"\b(?:cricket|ipl|t20|ashes)\b"),
        ):
            if re.search(lg_pat, txt):
                league = lg_code
                break

        if re.search(r"\b(?:exact\s+score|winning\s+margin|correct\s+score)\b", txt):
            sub = "sports_exact_score_margin"
        elif re.search(r"\b(?:spread|handicap|puck\s+line|run\s+line|[+-]\d+\.5)\b", txt):
            sub = "sports_spread_handicap"
        elif re.search(r"\b(?:o/u|over/under|total\s+(?:points|goals|runs|games|maps|sets)|over\s+\d+\.?\d*|under\s+\d+\.?\d*)\b", txt):
            sub = "sports_game_total_ou"
        elif re.search(
            r"\b(?:points|rebounds|assists|touchdowns|passing\s+yards|rushing\s+yards|receiving\s+yards|strikeouts|home\s+runs|shots\s+on\s+goal|first\s+goalscorer|anytime\s+touchdown|double-double|triple-double)\b",
            txt,
        ) and not re.search(r"\btotal\s+points\b", txt):
            sub = "sports_player_prop"
        elif re.search(
            r"\b(?:championship|champion|win\s+the\s+202\d|mvp|rookie\s+of\s+the\s+year|cy\s+young|ballon\s+d'or|playoffs|make\s+the\s+playoffs|draft|transfer|next\s+team|head\s+coach)\b",
            txt,
        ):
            sub = "sports_futures_award_transfer"
        elif start_ts is not None and end_ts is not None and start_ts <= now_ts < end_ts and (end_ts - now_ts) <= 6.0 * 3600.0:
            sub = "sports_live_in_play"
        else:
            sub = "sports_game_moneyline"
        return "sports", sub, league

    # 3. CRYPTO (BTC, ETH, SOL, XRP, DOGE, BNB, HYPE, altcoins; 5m/15m/1h/4h/daily/weekly/monthly/thresholds/up-down)
    is_crypto = bool(
        "crypto" in ft_l
        or tag_set
        & {
            "crypto", "crypto-prices", "bitcoin", "ethereum", "solana", "defi", "memecoins",
            "airdrops", "nft", "stablecoins", "xrp", "dogecoin", "hyperliquid", "altcoins",
        }
        or re.search(
            r"\b(?:bitcoin|btc|ethereum|eth|solana|sol|xrp|dogecoin|doge|hyperliquid|fdv|airdrop|memecoin|blockchain|uniswap|tether|usdt|usdc|satoshi|binance|coinbase\s+listing)\b",
            txt,
        )
    )
    if is_crypto:
        asset = "CRYPTO_ALT_OTHER"
        for sym, pat in _CRYPTO_ASSET_PATTERNS:
            if pat.search(txt):
                asset = sym
                break
        if asset == "CRYPTO_ALT_OTHER":
            m_dyn = re.search(r"\$([a-z]{2,8})\b", txt)
            if m_dyn:
                asset = m_dyn.group(1).upper()
            elif re.search(r"\b(?:airdrop|fdv|token\s+launch|tge)\b", txt):
                asset = "AIRDROP_FDV"

        if re.search(r"\b(?:5\s*min|5m|15\s*min|15m)\b|-(?:5m|15m)-", txt) or ft_l == "crypto_15_min":
            sub = "crypto_subhourly_5m_15m"
        elif re.search(r"\b(?:1\s*hour|1h|hourly|4\s*hour|4h)\b|-(?:1h|4h)-", txt):
            sub = "crypto_intraday_1h_4h"
        elif re.search(r"\b(?:up\s+or\s+down|higher\s+or\s+lower)\b", txt):
            sub = "crypto_daily_up_down"
        elif re.search(r"\b(?:airdrop|fdv|fully\s+diluted|tge|token\s+launch|mainnet)\b", txt):
            sub = "crypto_defi_airdrop_fdv"
        elif re.search(r"\b(?:etf|sec\s+approv|strategic\s+reserve|hack|exploit|depeg)\b", txt):
            sub = "crypto_etf_protocol_event"
        elif re.search(r"\b(?:all-time\s+high|ath|new\s+high)\b", txt):
            sub = "crypto_milestone_ath"
        elif re.search(r"\b(?:what\s+price\s+will|price\s+range|between\s+\$)\b", txt):
            sub = "crypto_weekly_monthly_range"
        else:
            sub = "crypto_strike_threshold"
        return "crypto", sub, asset

    # 4. ECONOMICS & MACRO (CPI, Fed/central banks, NFP/jobs, GDP, recessions, tariffs)
    is_macro = bool(
        "economics" in ft_l
        or tag_set
        & {
            "economics", "economy", "fed", "fomc", "macro", "macro-indicators", "inflation",
            "cpi", "pce", "ppi", "jobs", "nfp", "gdp", "recession", "tariffs", "ecb", "boe",
            "boj", "snb", "rbi", "global-rates", "umich", "ism",
        }
        or re.search(
            r"\b(?:fed\s+(?:decrease|increase|cut|hike|hold|interest\s+rate)|fomc|central\s+bank|ecb|bank\s+of\s+(?:england|japan|canada)|snb|cpi|consumer\s+price\s+index|core\s+pce|inflation\s+rate|nonfarm\s+payroll|unemployment\s+rate|jobless\s+claims|gdp\s+growth|recession|tariff|trade\s+deficit|ism\s+manufacturing)\b",
            txt,
        )
    )
    if is_macro:
        if re.search(r"\b(?:fed|fomc|interest\s+rate|rate\s+cut|rate\s+hike|bps|ecb|boe|boj|snb|rbi|bank\s+of)\b", txt):
            sub = "macro_central_bank_rates"
            ent = "CENTRAL_BANKS"
        elif re.search(r"\b(?:cpi|inflation|pce|ppi|consumer\s+price)\b", txt):
            sub = "macro_inflation_cpi_pce"
            ent = "INFLATION_PRICES"
        elif re.search(r"\b(?:payroll|nfp|unemployment|jobs|jobless|jolts|labor)\b", txt):
            sub = "macro_labor_nfp_jobs"
            ent = "LABOR_MARKET"
        elif re.search(r"\b(?:tariff|duty|trade\s+war|trade\s+deal|customs|debt\s+ceiling|deficit)\b", txt):
            sub = "macro_tariffs_fiscal_trade"
            ent = "FISCAL_TARIFFS"
        else:
            sub = "macro_gdp_recession_activity"
            ent = "GDP_ACTIVITY"
        return "economics_macro", sub, ent

    # 5. FINANCE (equities, indexes, earnings, M&A, IPOs, market-cap milestones, commodities)
    is_finance = bool(
        "finance" in ft_l
        or tag_set
        & {
            "finance", "stocks", "equities", "earnings", "ipo", "commodities", "oil", "gold",
            "silver", "parcl", "real-estate", "forex", "currencies", "s&p-500", "nasdaq",
        }
        or re.search(
            r"\b(?:s&p\s*500|spx|nasdaq|dow\s+jones|russell\s+2000|vix|nikkei|stock\s+price|share\s+price|market\s+cap|largest\s+company|ipo|earnings|eps|quarterly\s+revenue|acquire|merger|buyout|crude\s+oil|wti|brent|gold\s+price|xau|silver\s+price|xag|natural\s+gas|parcl|treasury\s+yield|10-year\s+yield)\b",
            txt,
        )
    )
    if is_finance:
        if re.search(r"\b(?:crude\s+oil|wti|brent|gold|xau|silver|xag|natural\s+gas|copper|wheat|parcl|home\s+price|usd/jpy|eur/usd)\b", txt):
            sub = "finance_commodities_fx_realestate"
            ent = "COMMODITIES_FX_RE"
        elif re.search(r"\b(?:market\s+cap|largest\s+company|trillion\s+market\s+cap)\b", txt):
            sub = "finance_market_cap_ranking"
            ent = "MARKET_CAP"
        elif re.search(r"\b(?:earnings|eps|revenue\s+beat|quarterly\s+results)\b", txt):
            sub = "finance_earnings_revenue"
            ent = "EARNINGS"
        elif re.search(r"\b(?:ipo|acquire|acquisition|merger|buyout|bankrupt|chapter\s+11|ceo\s+|resign|step\s+down)\b", txt):
            sub = "finance_ma_ipo_corporate"
            ent = "CORPORATE_EVENTS"
        else:
            sub = "finance_equities_indexes"
            ent = "EQUITIES_INDEXES"
        return "finance", sub, ent

    # 6. GEOPOLITICS (conflict, ceasefires, sanctions, diplomacy)
    is_geopolitics = bool(
        tag_set
        & {
            "geopolitics", "ukraine", "russia", "middle-east", "israel", "iran", "gaza",
            "taiwan", "china", "nato", "military", "war", "united-nations", "conflict",
        }
        or re.search(
            r"\b(?:ceasefire|invasion|invade|military\s+strike|airstrike|missile|nuclear\s+test|nato|sanction|blockade|hostage|peace\s+deal|regime\s+change|israel|iran|hezbollah|hamas|ukraine|zelensky|putin|taiwan\s+strait|north\s+korea)\b",
            txt,
        )
    )
    if is_geopolitics:
        if re.search(r"\b(?:ceasefire|invasion|invade|strike|airstrike|missile|war|troops|capture|territory|blockade)\b", txt):
            sub = "geopolitics_conflict_ceasefire"
        else:
            sub = "geopolitics_diplomacy_sanctions"
        return "geopolitics", sub, "GEOPOLITICS"

    # 7. POLITICS (US & global elections, polling, legislation, appointments, approvals)
    is_politics = bool(
        "politics" in ft_l
        or "mentions" in ft_l
        or tag_set
        & {
            "politics", "poltics", "elections", "us-elections", "global-elections", "midterms",
            "trump", "congress", "senate", "house", "governor", "supreme-court", "judicial",
            "uk", "canada", "brazil", "france", "germany", "dnc", "gop", "cabinet",
        }
        or re.search(
            r"\b(?:presidential\s+election|election|senate|house\s+of\s+representatives|governor|mayor|parliament|prime\s+minister|chancellor|democrat|republican|nominee|primary|approval\s+rating|favorability|poll|impeach|pardon|executive\s+order|supreme\s+court|confirm|cabinet|government\s+shutdown)\b",
            txt,
        )
    )
    if is_politics:
        if re.search(r"\b(?:approval\s+rating|favorability|polling|poll\s+average|rcp|538)\b", txt):
            sub = "politics_polling_approval"
            ent = "POLLING_APPROVAL"
        elif re.search(r"\b(?:bill\s+|legislation|pass\s+the|senate\s+vote|house\s+vote|supreme\s+court|scotus|ruling|shutdown|impeach)\b", txt):
            sub = "politics_legislation_judicial"
            ent = "LEGISLATION_COURTS"
        elif re.search(r"\b(?:cabinet|secretary\s+of|appoint|confirm|nomination|pardon|chief\s+of\s+staff|resign)\b", txt):
            sub = "politics_appointment_cabinet"
            ent = "APPOINTMENTS"
        elif re.search(r"\b(?:say\s+|mention|speech|press\s+conference|debate)\b", txt) or "mentions" in ft_l:
            sub = "politics_speech_mentions_general"
            ent = "SPEECH_MENTIONS"
        elif re.search(
            r"\b(?:uk\s+|canada|canadian|french|france|german|germany|brazil|mexico|japan|south\s+korea|australia|israel|eu\s+|parliament|prime\s+minister|bundestag|tory|labour)\b",
            txt,
        ):
            sub = "politics_global_election"
            ent = "GLOBAL_ELECTIONS"
        else:
            sub = "politics_us_election"
            ent = "US_ELECTIONS"
        return "politics", sub, ent

    # 8. SCIENCE (space, aerospace, biotech/health, climate/physics)
    is_science = bool(
        tag_set & {"science", "space", "nasa", "spacex", "health", "biotech", "fda", "disease", "medicine"}
        or re.search(
            r"\b(?:spacex|starship|nasa|artemis|orbital|moon\s+landing|mars|satellite|fda\s+approv|clinical\s+trial|vaccine|bird\s+flu|h5n1|mpox|pandemic|who\s+|cdc|nobel\s+prize\s+in\s+(?:physics|chemistry|medicine)|nuclear\s+fusion|superconductor)\b",
            txt,
        )
    )
    if is_science:
        if re.search(r"\b(?:spacex|starship|nasa|artemis|rocket|orbital|launch|moon|mars|satellite|boeing\s+starliner)\b", txt):
            sub = "science_space_aerospace"
            ent = "SPACE_AEROSPACE"
        else:
            sub = "science_health_biotech_physics"
            ent = "HEALTH_SCIENCE"
        return "science", sub, ent

    # 9. TECH & AI
    is_tech = bool(
        "tech" in ft_l
        or tag_set & {"tech", "ai", "artificial-intelligence", "openai", "big-tech", "apple", "tesla"}
        or re.search(
            r"\b(?:openai|gpt-?\d|chatgpt|anthropic|claude|gemini|google\s+ai|xai|grok|deepseek|llama|lmsys|chatbot\s+arena|agi|asi|apple|iphone|ios|nvidia|microsoft|meta|tesla|robotaxi|fsd|tiktok\s+ban|semiconductor)\b",
            txt,
        )
    )
    if is_tech:
        if re.search(r"\b(?:openai|gpt|chatgpt|anthropic|claude|gemini|xai|grok|deepseek|llama|lmsys|arena|agi|ai\s+model|frontier\s+model)\b", txt):
            sub = "tech_ai_models_benchmarks"
            ent = "AI_MODELS"
        else:
            sub = "tech_product_launch_adoption"
            ent = "TECH_PRODUCTS"
        return "tech_ai", sub, ent

    # 10. CULTURE & ENTERTAINMENT (plus catch-all social/viral markets)
    if re.search(r"\b(?:tweet|posts?\s+on\s+x|truth\s+social|elon\s+musk\s+#\s+of|followers)\b", txt) or "social" in tag_set:
        return "culture_entertainment", "culture_social_tweet_counts", "SOCIAL_TWEETS"
    if re.search(r"\b(?:oscar|academy\s+award|grammy|emmy|golden\s+globe|box\s+office|rotten\s+tomatoes|movie|film)\b", txt):
        return "culture_entertainment", "culture_awards_box_office", "AWARDS_BOX_OFFICE"
    return "culture_entertainment", "culture_music_streaming_creator", "CULTURE_GENERAL"


def extract_contract_semantics(question: str, group_item_title: str, outcomes: Sequence[str]) -> Tuple[str, bool]:
    """
    Identifies contract polarity & payoff semantics so downstream strategies never invert YES/NO
    (`RT-04` defense).
    """
    q = f"{question} {group_item_title}".strip()
    q_low = q.lower()
    is_negated = bool(_NEGATED_QUESTION_RE.search(q_low))

    if len(outcomes) == 2 and [o.lower() for o in outcomes] not in (["yes", "no"], ["no", "yes"]):
        outs_l = [o.lower() for o in outcomes]
        if outs_l == ["up", "down"]:
            return "UP_OR_HIGHER", is_negated
        if outs_l == ["down", "up"]:
            return "DOWN_OR_LOWER", is_negated
        if outs_l == ["over", "under"]:
            return "ABOVE_OR_OVER_THRESHOLD", is_negated
        if outs_l == ["under", "over"]:
            return "BELOW_OR_UNDER_THRESHOLD", is_negated
        return "HEAD_TO_HEAD_MATCHUP", is_negated

    if is_negated:
        return "NEGATED_EVENT", True
    if re.search(r"\b(?:between\s+[$]?\d|\d+(?:\.\d+)?\s*(?:to|-|–|and)\s*[$]?\d+|exact(?:ly)?(?:\s+score)?\s+\d)", q_low):
        return "INTERIOR_BUCKET_OR_EXACT", False
    if re.search(r"\b(?:below|under|less\s+than|lower\s+than|dip\s+to|drop\s+to|or\s+below|or\s+less)\b", q_low):
        return "BELOW_OR_UNDER_THRESHOLD", False
    if re.search(r"\b(?:above|over|more\s+than|higher\s+than|exceed|reach|hit|or\s+above|or\s+higher)\b", q_low):
        return "ABOVE_OR_OVER_THRESHOLD", False
    if re.search(r"\b(?:up\s+or\s+down)\b", q_low):
        return "UP_OR_HIGHER", False
    return "AFFIRMATIVE_EVENT", False


def classify_oracle_mechanism(resolution_source: str, rule_summary: str, category: str) -> str:
    txt = f"{resolution_source} {rule_summary}".lower()
    if re.search(r"\b(?:binance|coinbase|chainlink|pyth|coingecko|dexscreener|kraken|okx)\b", txt):
        return "CHAINLINK_OR_CEX_PRICE_FEED"
    if re.search(r"\b(?:wunderground|weather\s+underground|noaa|national\s+weather\s+service|nhc|met\s+office|asos)\b", txt) or category == "weather":
        return "WEATHER_ASOS_WUNDERGROUND_NOAA"
    if re.search(r"\b(?:bls\.gov|federalreserve\.gov|bea\.gov|ecb\.europa|treasury\.gov|official\s+government)\b", txt):
        return "OFFICIAL_GOVT_CENTRAL_BANK_RELEASE"
    if re.search(r"\b(?:nba\.com|nfl\.com|nhl\.com|mlb\.com|espn|opta|premierleague|atptour|ufc\.com|hltv|liquipedia|official\s+box\s+score)\b", txt) or category == "sports":
        return "OFFICIAL_SPORTS_STATS_FEED"
    if re.search(r"\b(?:nasdaq|nyse|sec\.gov|yahoo\s+finance|tradingview|companiesmarketcap)\b", txt):
        return "CORPORATE_FILING_OR_EXCHANGE"
    return "UMA_OPTIMISTIC_CONSENSUS_TEXT"


def classify_maturity_bucket(ttc_hours: Optional[float], closed: bool) -> str:
    if closed or (ttc_hours is not None and ttc_hours <= 0.0):
        return "RESOLVED_OR_PAST_END"
    if ttc_hours is None:
        return "UNSPECIFIED_MATURITY"
    if ttc_hours < 2.0:
        return "ULTRA_SHORT_LT_2H"
    if ttc_hours <= 24.0:
        return "INTRADAY_2H_TO_24H"
    if ttc_hours <= 168.0:
        return "SHORT_1D_TO_7D"
    if ttc_hours <= 720.0:
        return "MEDIUM_7D_TO_30D"
    if ttc_hours <= 1440.0:
        return "INTERMEDIATE_30D_TO_60D"
    return "LONG_GT_60D"


# ===========================================================================
# Polymarket Fee Curve & Directional Opportunity Scoring Engine
# ===========================================================================


# Polymarket Protocol V2 curved-fee schedules (`fee_ps = rate * (p * (1 - p)) ** exponent`).
# Note: CLOB `base_fee == 1000` (`takerBaseFee == 1000`) is the V2 curved-fee sentinel, NEVER 10% flat bps!
V2_FEE_SCHEDULE_BY_TYPE: Dict[str, Tuple[float, float, float]] = {
    "zero_fee": (0.0, 1.0, 0.0),
    "zero_fees": (0.0, 1.0, 0.0),
    "crypto_fees_v2": (0.07, 1.0, 0.20),
    "crypto_15_min": (0.25, 2.0, 0.20),
    "sports_fees_v3": (0.05, 1.0, 0.15),
    "sports_fees_v2": (0.03, 1.0, 0.25),
    "sports_fees_nfl_cfb_oct26": (0.03, 1.0, 0.15),
    "weather_fees": (0.05, 1.0, 0.25),
    "economics_fees": (0.05, 1.0, 0.25),
    "culture_fees": (0.05, 1.0, 0.25),
    "general_fees": (0.05, 1.0, 0.25),
    "politics_fees": (0.04, 1.0, 0.25),
    "finance_prices_fees": (0.04, 1.0, 0.25),
    "tech_fees": (0.04, 1.0, 0.25),
    "mentions_fees": (0.04, 1.0, 0.25),
}

V2_FALLBACK_RATE_BY_CATEGORY: Dict[str, float] = {
    "crypto": 0.07,
    "sports": 0.05,
    "weather": 0.05,
    "economics_macro": 0.05,
    "culture_entertainment": 0.05,
    "politics": 0.04,
    "finance": 0.04,
    "tech_ai": 0.04,
    "science": 0.04,
    "geopolitics": 0.04,
}


def resolve_v2_fee_parameters(
    *,
    fees_enabled_raw: Any,
    fee_type_raw: str,
    fee_sched: Mapping[str, Any],
    taker_base_bps_raw: float,
    maker_base_bps_raw: float,
    category: str,
) -> Tuple[bool, str, float, float, float, float, float]:
    """
    Resolves `(fees_enabled, fee_type, fee_schedule_rate, fee_exponent, maker_rebate_rate, taker_base_bps, maker_base_bps)`.
    Handles Polymarket V2's `base_fee == 1000` curved-fee sentinel and `fee_type == 'zero_fees'` cleanly.
    """
    ft = (fee_type_raw or "").strip()
    ft_low = ft.lower()

    sched_rate = float(safe_float(fee_sched.get("rate"), 0.0) or 0.0)
    sched_exp = float(safe_float(fee_sched.get("exponent"), 1.0) or 1.0)
    taker_only = bool(fee_sched.get("takerOnly", True))
    rebate_rate = float(safe_float(fee_sched.get("rebateRate"), 0.0) or 0.0)

    if ft_low in ("zero_fee", "zero_fees") or fees_enabled_raw is False:
        return False, (ft or "zero_fee"), 0.0, 1.0, 0.0, 0.0, 0.0

    fees_enabled = bool(fees_enabled_raw) if fees_enabled_raw is not None else bool(sched_rate > 0.0 or taker_base_bps_raw > 0.0)
    if not fees_enabled:
        return False, (ft or "zero_fee"), 0.0, 1.0, 0.0, 0.0, 0.0

    if sched_rate <= 0.0:
        if ft_low in V2_FEE_SCHEDULE_BY_TYPE:
            sched_rate, sched_exp, def_reb = V2_FEE_SCHEDULE_BY_TYPE[ft_low]
            if rebate_rate <= 0.0:
                rebate_rate = def_reb
        elif taker_base_bps_raw >= 999.0:
            # `1000` is the V2 curved-fee sentinel (NOT 10% flat bps!)
            sched_rate = V2_FALLBACK_RATE_BY_CATEGORY.get(category, 0.04)
            sched_exp = 1.0

    if sched_rate <= 0.0 and taker_base_bps_raw <= 0.0:
        return False, (ft or "zero_fee"), 0.0, 1.0, 0.0, 0.0, 0.0

    if not ft:
        ft = "custom_v2_fee"
    eff_maker_bps = 0.0 if taker_only else maker_base_bps_raw
    return True, ft, sched_rate, sched_exp, rebate_rate, taker_base_bps_raw, eff_maker_bps


def compute_polymarket_taker_fee_metrics(
    *,
    mid_price: Optional[float],
    best_ask: Optional[float],
    best_bid: Optional[float],
    fees_enabled: bool,
    fee_schedule_rate: float,
    fee_exponent: float,
    taker_base_fee_bps: float,
) -> Tuple[float, float, float]:
    """
    Computes exact Polymarket category-curved taker fee metrics:
      - `effective_taker_fee_per_share`: USD fee per share on YES at executable/mid price `p`
      - `effective_taker_fee_bps_on_yes`: Taker fee as bps of YES capital outlay (`fee_ps / p_yes`)
      - `effective_taker_fee_bps_on_no`: Taker fee as bps of NO capital outlay (`fee_ps / p_no`, where `p_no = 1 - p_yes`)

    Never misinterprets V2 `taker_base_fee_bps == 1000` as 10% flat bps.
    """
    if not fees_enabled or (fee_schedule_rate <= 0.0 and (taker_base_fee_bps <= 0.0 or taker_base_fee_bps >= 999.0)):
        return 0.0, 0.0, 0.0

    p_ref = best_ask if (best_ask is not None and 0.001 < best_ask < 0.999) else mid_price
    if p_ref is None or not (0.001 <= p_ref <= 0.999):
        p_ref = 0.50
    p = max(0.001, min(0.999, float(p_ref)))
    exp = float(fee_exponent if fee_exponent > 0.0 else 1.0)

    if fee_schedule_rate > 0.0:
        rate = float(fee_schedule_rate)
        fee_ps = rate * ((p * (1.0 - p)) ** exp)
    else:
        # Legacy non-1000 flat bps fallback (`< 999` bps only)
        rate = float(taker_base_fee_bps) / 10000.0
        fee_ps = rate * p

    yes_outlay = max(0.01, p)
    no_ask = (1.0 - best_bid) if (best_bid is not None and 0.001 <= best_bid < 0.999) else (1.0 - p)
    no_outlay = max(0.01, min(0.999, no_ask))
    if fee_schedule_rate > 0.0:
        fee_ps_no = float(fee_schedule_rate) * ((no_outlay * (1.0 - no_outlay)) ** exp)
    else:
        fee_ps_no = (float(taker_base_fee_bps) / 10000.0) * no_outlay

    bps_yes = round(10000.0 * fee_ps / yes_outlay, 2)
    bps_no = round(10000.0 * fee_ps_no / no_outlay, 2)
    return round(fee_ps, 6), bps_yes, bps_no


def score_directional_opportunity(
    *,
    category: str,
    subcategory: str,
    structure_type: str,
    sibling_market_count: int,
    age_hours: Optional[float],
    ttc_hours: Optional[float],
    liquidity_usd: float,
    volume_24h_usd: float,
    mid_price: Optional[float],
    bid_ask_spread: Optional[float],
    one_day_price_change: Optional[float],
    fees_enabled: bool,
    effective_taker_fee_per_share: float,
    maker_rebate_rate: float,
    tick_size: float,
    min_order_size: float,
    oracle_mechanism: str,
    is_other_catchall: bool,
    permanent_exclusions: Sequence[str],
) -> Tuple[float, float, float, List[str]]:
    """
    Computes `(directional_opportunity_score, inefficiency_potential_score, execution_friction_penalty, alpha_mechanisms)`.

    Explicitly weighs **forecasting & behavioral inefficiency potential** against **execution & fee
    friction** rather than raw volume:
      - Penalizes HFT-saturated sub-hourly crypto (`5m/15m`) and clamped `99.9c` mega-volume markets.
      - Rewards domain-calibratable series (Weather ensembles, Macro releases, NegRisk/ladder cross-leg
        lag, newly created `<48h` price discovery, `0%`-fee legacy contracts, and low-fee-bps `88c-97c`
        NO-carry / longshot-bias zones) ONLY when spread and depth allow clean execution.
    """
    mechanisms: List[str] = []
    if permanent_exclusions:
        return 0.0, 0.0, 100.0, mechanisms

    # --- A. Forecasting & Behavioral Inefficiency Potential (`0..100`) ---
    domain_pts = {
        "weather": 22.0,
        "economics_macro": 19.5,
        "finance": 18.0,
        "geopolitics": 18.0,
        "politics": 17.5,
        "tech_ai": 17.0,
        "science": 17.0,
        "culture_entertainment": 16.5,
        "crypto": 14.5,
        "sports": 12.0,
    }.get(category, 14.0)

    if subcategory == "crypto_subhourly_5m_15m":
        domain_pts = 5.5  # Heavily HFT-arbitraged with 7% curved fee churn
    elif subcategory == "crypto_intraday_1h_4h":
        domain_pts = 9.5
    elif subcategory in ("sports_player_prop", "sports_futures_award_transfer"):
        domain_pts = 14.5
    elif subcategory == "sports_exact_score_margin":
        domain_pts = 8.5

    if category == "weather":
        mechanisms.append("SPECIALIST_WEATHER_CALIBRATION")
    elif category in ("economics_macro", "finance"):
        mechanisms.append("MACRO_EVENT_DRIFT_CALIBRATION")

    # Cross-contract / multi-outcome structural signal
    cross_leg_pts = 0.0
    if sibling_market_count >= 3 and structure_type in (
        "MULTI_OUTCOME_NEGRISK",
        "MULTI_OUTCOME_AUGMENTED_NEGRISK",
        "MULTI_MARKET_THRESHOLD_LADDER",
        "MULTI_MARKET_TEMPORAL_LADDER",
    ):
        cross_leg_pts = min(9.0, 4.0 + 1.2 * math.log1p(sibling_market_count))
        mechanisms.append("CROSS_CONTRACT_LAG_OR_SLATE_RESIDUAL")

    # Behavioral & price-discovery component (`0..26`)
    behav_pts = 0.0
    if age_hours is not None and 0.0 <= age_hours <= 48.0:
        behav_pts += 11.0 * math.exp(-age_hours / 36.0)
        mechanisms.append("NEW_LISTING_PRICE_DISCOVERY")

    if one_day_price_change is not None and abs(one_day_price_change) >= 0.04:
        behav_pts += min(8.0, abs(one_day_price_change) * 35.0)
        mechanisms.append("JUMP_OVERREACTION_OR_MOMENTUM")

    if mid_price is not None:
        if 0.02 <= mid_price < 0.12 or 0.88 < mid_price <= 0.97:
            behav_pts += 9.5
            mechanisms.append("FAVORITE_LONGSHOT_ASYMMETRY")
        elif 0.12 <= mid_price <= 0.88:
            behav_pts += 7.5
        elif 0.006 <= mid_price < 0.02 or 0.97 < mid_price <= 0.994:
            behav_pts += 2.5
        else:
            behav_pts += 0.0
    else:
        behav_pts += 2.0

    # Flow-to-liquidity ratio (`vol24 / max(liq, 250)`), NOT raw mega-volume (`0..18`)
    turnover_ratio = max(0.0, volume_24h_usd) / max(250.0, liquidity_usd)
    flow_pts = min(18.0, 6.2 * math.log1p(turnover_ratio * 3.0))

    # Horizon / capital-velocity efficiency (`0..17`)
    if ttc_hours is None:
        horizon_pts = 7.0
    elif ttc_hours < 0.75:
        horizon_pts = 4.5
    elif ttc_hours < 6.0:
        horizon_pts = 11.5
    elif ttc_hours <= 336.0:  # 6h to 14d sweet spot
        horizon_pts = 17.0
        mechanisms.append("HIGH_VELOCITY_HORIZON_6H_14D")
    elif ttc_hours <= 1440.0:  # 14d to 60d
        horizon_pts = 11.0
    else:
        horizon_pts = 4.5  # >60d opportunity-cost drag

    # Depth sufficiency concave floor (`0..12`, saturates around $5k-$10k so $1M markets get no unfair boost)
    depth_pts = 12.0 * (1.0 - math.exp(-max(0.0, liquidity_usd) / 2500.0))

    if not fees_enabled:
        mechanisms.append("ZERO_FEE_CONTRACT")

    ineff_score = min(100.0, round(domain_pts + cross_leg_pts + behav_pts + flow_pts + horizon_pts + depth_pts, 2))

    # --- B. Execution, Fee & Governance Friction Penalty (`0..100`) ---
    if bid_ask_spread is None:
        spread_pen = 36.0
    else:
        spread_pen = min(38.0, max(0.0, bid_ask_spread) * 380.0)

    # Dynamic taker fee drag relative to typical directional edge
    fee_pen = min(24.0, effective_taker_fee_per_share * 1050.0)
    if maker_rebate_rate > 0.0 and bid_ask_spread is not None and bid_ask_spread >= 2.0 * tick_size:
        fee_pen *= 0.80  # Passive post-only maker entry can avoid taker fee and earn rebate

    # Scarcity / quantization penalty
    depth_pen = 0.0
    if liquidity_usd < 100.0:
        depth_pen = 18.0
    elif liquidity_usd < 500.0:
        depth_pen = 18.0 * ((500.0 - liquidity_usd) / 500.0)
    if min_order_size > 5.0:
        depth_pen = min(20.0, depth_pen + 3.5)

    # Governance / semantic ambiguity penalty
    gov_pen = 0.0
    if is_other_catchall:
        gov_pen += 16.0
    if oracle_mechanism == "UMA_OPTIMISTIC_CONSENSUS_TEXT":
        gov_pen += 3.5

    friction_pen = min(100.0, round(spread_pen + fee_pen + depth_pen + gov_pen, 2))
    net_score = max(0.0, min(100.0, round(ineff_score - 0.65 * friction_pen + 8.0, 2)))
    return net_score, ineff_score, friction_pen, mechanisms


# ===========================================================================
# Market Normalization & Full-Universe Discovery Engine
# ===========================================================================


def build_directional_market_record(
    raw_mkt: Mapping[str, Any],
    *,
    parent_event: Optional[Mapping[str, Any]] = None,
    clob_overlay: Optional[Mapping[str, Any]] = None,
    sibling_market_count: int = 1,
    event_structure_type: str = "SINGLE_BINARY",
    now_ts: Optional[float] = None,
    lifecycle_hint: str = "ACTIVE",
) -> Dict[str, Any]:
    """
    Converts a raw Gamma market (+ optional parent event & CLOB `/sampling-markets` overlay)
    into the canonical Agent A directional universe record with full taxonomy, fee curve,
    microstructure, opportunity score, and explicit exclusion classification.
    """
    eval_ts = float(time.time() if now_ts is None else now_ts)
    ev = parent_event or {}
    clob = clob_overlay or {}

    market_id = str(raw_mkt.get("id") or clob.get("question_id") or raw_mkt.get("conditionId") or "").strip()
    event_id = str(ev.get("id") or raw_mkt.get("_parent_event_id") or "").strip()
    if not event_id and isinstance(raw_mkt.get("events"), list) and raw_mkt["events"]:
        e0 = raw_mkt["events"][0]
        if isinstance(e0, Mapping):
            event_id = str(e0.get("id") or "").strip()
            if not ev:
                ev = e0

    condition_id = str(raw_mkt.get("conditionId") or clob.get("condition_id") or "").strip()
    slug = str(raw_mkt.get("slug") or clob.get("market_slug") or "").strip()
    event_slug = str(ev.get("slug") or slug).strip()
    event_title = str(ev.get("title") or "").strip()
    question = str(raw_mkt.get("question") or clob.get("question") or event_title).strip()
    group_item_title = str(raw_mkt.get("groupItemTitle") or "").strip()

    outcomes = parse_str_list(raw_mkt.get("outcomes"))
    token_ids = parse_str_list(raw_mkt.get("clobTokenIds"))
    if (not outcomes or not token_ids) and isinstance(clob.get("tokens"), list):
        c_outs: List[str] = []
        c_toks: List[str] = []
        for tk in clob["tokens"]:
            if isinstance(tk, Mapping):
                tid = str(tk.get("token_id") or "").strip()
                out_lbl = str(tk.get("outcome") or "").strip()
                if tid:
                    c_toks.append(tid)
                    c_outs.append(out_lbl or f"Outcome_{len(c_outs)}")
        if not token_ids and c_toks:
            token_ids = c_toks
        if not outcomes and c_outs:
            outcomes = c_outs

    outcome_prices = parse_float_list(raw_mkt.get("outcomePrices"))

    yes_token_id = token_ids[0] if len(token_ids) >= 1 else ""
    no_token_id = token_ids[1] if len(token_ids) >= 2 else ""

    active = bool(raw_mkt.get("active", clob.get("active", True)))
    closed = bool(raw_mkt.get("closed", clob.get("closed", False)) or ev.get("closed", False))
    archived = bool(raw_mkt.get("archived", clob.get("archived", False)) or ev.get("archived", False))
    deploying = bool(raw_mkt.get("deploying") or raw_mkt.get("pendingDeployment") or ev.get("deploying"))

    enable_order_book = bool(
        raw_mkt.get("enableOrderBook", True) is not False
        and ev.get("enableOrderBook", True) is not False
        and clob.get("enable_order_book", True) is not False
    )
    accepting_raw = raw_mkt.get("acceptingOrders")
    if accepting_raw is None:
        accepting_raw = clob.get("accepting_orders", True)
    accepting_orders = bool(accepting_raw is not False)

    neg_risk = bool(raw_mkt.get("negRisk") or ev.get("negRisk") or ev.get("enableNegRisk") or clob.get("neg_risk"))
    neg_risk_augmented = bool(
        ev.get("negRiskAugmented")
        or raw_mkt.get("negRiskAugmented")
        or ev.get("augmentedNegRisk")
        or ev.get("enableNegRiskOther")
    )
    neg_risk_market_id = str(
        raw_mkt.get("negRiskMarketID") or ev.get("negRiskMarketID") or clob.get("neg_risk_market_id") or ""
    ).strip()
    neg_risk_other_flag = bool(raw_mkt.get("negRiskOther") or ev.get("negRiskOther"))

    is_placeholder, is_other = detect_placeholder_and_other(
        question=question,
        group_item_title=group_item_title,
        slug=slug,
        neg_risk=neg_risk,
        neg_risk_augmented=neg_risk_augmented,
        neg_risk_other_flag=neg_risk_other_flag,
        active=active,
        enable_order_book=enable_order_book,
    )

    # Timestamps, age, and time-to-maturity
    created_iso = str(raw_mkt.get("createdAt") or ev.get("createdAt") or "").strip()
    start_iso = str(raw_mkt.get("startDate") or ev.get("startDate") or "").strip()
    end_iso = str(raw_mkt.get("endDate") or clob.get("end_date_iso") or ev.get("endDate") or "").strip()
    closed_iso = str(raw_mkt.get("closedTime") or ev.get("closedTime") or "").strip()

    created_ts = parse_iso_ts(created_iso)
    start_ts = parse_iso_ts(start_iso)
    end_ts = parse_iso_ts(end_iso)
    closed_ts = parse_iso_ts(closed_iso)

    age_hours = round(max(0.0, (eval_ts - created_ts) / 3600.0), 2) if created_ts is not None else None
    ttc_hours = round((end_ts - eval_ts) / 3600.0, 2) if end_ts is not None else None

    is_newly_created_48h = bool(not closed and age_hours is not None and 0.0 <= age_hours <= 48.0)
    is_long_duration_60d = bool(not closed and ttc_hours is not None and ttc_hours > 1440.0)
    maturity_bucket = classify_maturity_bucket(ttc_hours, closed)

    # Raw fee metadata (resolved with category-aware V2 schedule below)
    fee_sched = raw_mkt.get("feeSchedule") if isinstance(raw_mkt.get("feeSchedule"), Mapping) else {}
    fee_type_raw = str(raw_mkt.get("feeType") or "").strip()
    taker_base_bps_raw = float(
        safe_float(
            clob.get("taker_base_fee") if clob.get("taker_base_fee") is not None else raw_mkt.get("takerBaseFee"),
            0.0,
        )
        or 0.0
    )
    if 0.0 < taker_base_bps_raw < 1.0:
        taker_base_bps_raw = round(taker_base_bps_raw * 10000.0, 4)
    maker_base_bps_raw = float(
        safe_float(
            clob.get("maker_base_fee") if clob.get("maker_base_fee") is not None else raw_mkt.get("makerBaseFee"),
            0.0,
        )
        or 0.0
    )
    if 0.0 < maker_base_bps_raw < 1.0:
        maker_base_bps_raw = round(maker_base_bps_raw * 10000.0, 4)
    fees_enabled_raw = raw_mkt.get("feesEnabled")

    # Top-of-book & liquidity/volume from Gamma
    raw_bb = safe_float(raw_mkt.get("bestBid"), None)
    raw_ba = safe_float(raw_mkt.get("bestAsk"), None)
    raw_sp = safe_float(raw_mkt.get("spread"), None)

    best_bid = round(raw_bb, 5) if (raw_bb is not None and 0.0 < raw_bb < 1.0) else None
    best_ask = round(raw_ba, 5) if (raw_ba is not None and 0.0 < raw_ba <= 1.0) else None

    if best_bid is not None and best_ask is not None and best_ask >= best_bid:
        bid_ask_spread: Optional[float] = round(best_ask - best_bid, 5)
        mid_price: Optional[float] = round(0.5 * (best_bid + best_ask), 5)
    else:
        bid_ask_spread = round(raw_sp, 5) if (raw_sp is not None and 0.0 < raw_sp < 1.0 and best_bid is not None) else None
        if outcome_prices:
            mid_price = round(outcome_prices[0], 5)
        elif best_bid is not None:
            mid_price = best_bid
        elif best_ask is not None and best_ask < 1.0:
            mid_price = best_ask
        else:
            mid_price = None

    spread_bps_of_mid = (
        round(10000.0 * bid_ask_spread / max(0.02, mid_price), 1)
        if (bid_ask_spread is not None and mid_price is not None)
        else None
    )

    liquidity_usd = round(
        float(safe_float(raw_mkt.get("liquidityNum") or raw_mkt.get("liquidityClob") or raw_mkt.get("liquidity"), 0.0) or 0.0),
        2,
    )
    volume_24h_usd = round(float(safe_float(raw_mkt.get("volume24hr"), 0.0) or 0.0), 2)
    volume_total_usd = round(float(safe_float(raw_mkt.get("volumeNum") or raw_mkt.get("volume"), 0.0) or 0.0), 2)
    one_day_price_change = safe_float(raw_mkt.get("oneDayPriceChange"), None)
    if one_day_price_change is not None:
        one_day_price_change = round(one_day_price_change, 5)

    tick_size = float(safe_float(clob.get("minimum_tick_size") or raw_mkt.get("orderPriceMinTickSize"), 0.01) or 0.01)
    if tick_size <= 0.0:
        tick_size = 0.01
    min_order_size = float(safe_float(clob.get("minimum_order_size") or raw_mkt.get("orderMinSize"), 5.0) or 5.0)
    if min_order_size <= 0.0:
        min_order_size = 5.0

    holding_rewards = bool(raw_mkt.get("holdingRewardsEnabled", False))
    rewards_max_spread = float(safe_float(raw_mkt.get("rewardsMaxSpread"), 0.0) or 0.0)

    # Taxonomy, contract semantics & resolution summary
    tags = parse_str_list(ev.get("tags") or raw_mkt.get("tags") or clob.get("tags"))
    category, subcategory, asset_or_entity = classify_market_taxonomy(
        tags=tags,
        event_slug=event_slug,
        market_slug=slug,
        event_title=event_title,
        question=question,
        fee_type=fee_type_raw,
        start_ts=start_ts,
        end_ts=end_ts,
        now_ts=eval_ts,
    )
    (
        fees_enabled,
        fee_type,
        fee_schedule_rate,
        fee_exponent,
        maker_rebate_rate,
        taker_base_bps,
        effective_maker_bps,
    ) = resolve_v2_fee_parameters(
        fees_enabled_raw=fees_enabled_raw,
        fee_type_raw=fee_type_raw,
        fee_sched=fee_sched,
        taker_base_bps_raw=taker_base_bps_raw,
        maker_base_bps_raw=maker_base_bps_raw,
        category=category,
    )
    polarity_type, is_negated = extract_contract_semantics(question, group_item_title, outcomes)

    resolution_source = str(raw_mkt.get("resolutionSource") or ev.get("resolutionSource") or "").strip()
    desc_raw = str(raw_mkt.get("description") or ev.get("description") or "").strip()
    rule_clean = re.sub(r"\s+", " ", desc_raw)[:160] if desc_raw else ""
    oracle_mechanism = classify_oracle_mechanism(resolution_source, rule_clean, category)

    uma_status = str(raw_mkt.get("umaResolutionStatus") or "").strip().lower()
    if uma_status in ("none", "null"):
        uma_status = ""

    # Determine resolved outcome & continuous payout (`1.0`, `0.0`, `0.5` for void/50-50, `0.0` floor if disputed per D-009)
    resolved_outcome: Optional[str] = None
    settlement_payout_yes: Optional[float] = None
    if uma_status == "disputed":
        settlement_payout_yes = 0.0
    if closed and len(outcome_prices) >= 2 and len(outcomes) >= 2:
        if outcome_prices[0] >= 0.99 and outcome_prices[1] <= 0.01:
            resolved_outcome = outcomes[0]
            settlement_payout_yes = 1.0
        elif outcome_prices[1] >= 0.99 and outcome_prices[0] <= 0.01:
            resolved_outcome = outcomes[1]
            settlement_payout_yes = 0.0
        elif 0.45 <= outcome_prices[0] <= 0.55 and 0.45 <= outcome_prices[1] <= 0.55:
            resolved_outcome = "SPLIT_50_50"
            settlement_payout_yes = 0.5

    fee_ps, fee_bps_yes, fee_bps_no = compute_polymarket_taker_fee_metrics(
        mid_price=mid_price,
        best_ask=best_ask,
        best_bid=best_bid,
        fees_enabled=fees_enabled,
        fee_schedule_rate=fee_schedule_rate,
        fee_exponent=fee_exponent,
        taker_base_fee_bps=taker_base_bps,
    )

    # Explicit Permanent Exclusion vs Computational Deprioritization
    perm_reasons: List[str] = []
    deprio_reasons: List[str] = []

    is_kmia_d001 = market_id in KMIA_D001_FROZEN_MARKET_IDS
    if is_kmia_d001:
        perm_reasons.append("PERM_KMIA_D001_PROTECTED_LOCK")
    if uma_status == "disputed":
        perm_reasons.append("PERM_UMA_DISPUTED_FROZEN")
    elif uma_status == "proposed" and not closed:
        perm_reasons.append("PERM_UMA_PROPOSED_POST_EVENT")
    if closed or archived:
        perm_reasons.append("PERM_CLOSED_OR_ARCHIVED")
    if not active or deploying:
        perm_reasons.append("PERM_INACTIVE_OR_PAUSED")
    if not enable_order_book:
        perm_reasons.append("PERM_ORDERBOOK_DISABLED")
    if not accepting_orders and not closed:
        perm_reasons.append("PERM_NOT_ACCEPTING_ORDERS")
    if is_placeholder:
        perm_reasons.append("PERM_AUGMENTED_PLACEHOLDER")
    if not is_valid_condition_id(condition_id) or len(token_ids) < 2:
        perm_reasons.append("PERM_MISSING_VALID_TOKENS_OR_CONDITION")
    if not closed and end_ts is not None and end_ts < eval_ts:
        perm_reasons.append("PERM_PAST_MATURITY_UNRESOLVED")

    if not perm_reasons:
        if best_bid is None or best_ask is None:
            deprio_reasons.append("DEPRIO_NO_TWO_SIDED_QUOTES")
        elif bid_ask_spread is not None and bid_ask_spread > 0.20:
            deprio_reasons.append("DEPRIO_EXTREME_SPREAD_GT_20C")
        if liquidity_usd < 100.0:
            deprio_reasons.append("DEPRIO_SUB_100_USD_LIQUIDITY")
        if mid_price is not None and (mid_price >= 0.995 or mid_price <= 0.005):
            deprio_reasons.append("DEPRIO_CLAMPED_TAIL_995_OR_005")
        if is_other:
            deprio_reasons.append("DEPRIO_MUTABLE_NEGRISK_OTHER")
        if volume_total_usd <= 0.0 and (age_hours is None or age_hours > 24.0):
            deprio_reasons.append("DEPRIO_ZERO_HISTORICAL_VOLUME")

    opp_score, ineff_score, friction_pen, mechanisms = score_directional_opportunity(
        category=category,
        subcategory=subcategory,
        structure_type=event_structure_type,
        sibling_market_count=sibling_market_count,
        age_hours=age_hours,
        ttc_hours=ttc_hours,
        liquidity_usd=liquidity_usd,
        volume_24h_usd=volume_24h_usd,
        mid_price=mid_price,
        bid_ask_spread=bid_ask_spread,
        one_day_price_change=one_day_price_change,
        fees_enabled=fees_enabled,
        effective_taker_fee_per_share=fee_ps,
        maker_rebate_rate=maker_rebate_rate,
        tick_size=tick_size,
        min_order_size=min_order_size,
        oracle_mechanism=oracle_mechanism,
        is_other_catchall=is_other,
        permanent_exclusions=perm_reasons,
    )

    # Determine exclusion_tier & lifecycle_status
    if closed:
        lifecycle_status = lifecycle_hint if lifecycle_hint in ("RECENTLY_RESOLVED", "CLOSED_SIBLING") else "RECENTLY_RESOLVED"
        if (
            not is_placeholder
            and is_valid_condition_id(condition_id)
            and len(token_ids) >= 2
            and resolved_outcome is not None
        ):
            exclusion_tier = "RESOLVED_RESEARCH_UNIVERSE"
        else:
            exclusion_tier = "PERMANENT_EXCLUSION"
    elif perm_reasons:
        lifecycle_status = "PAUSED_OR_INACTIVE" if not active else "ACTIVE_RESTRICTED"
        exclusion_tier = "PERMANENT_EXCLUSION"
    elif deprio_reasons:
        lifecycle_status = "ACTIVE"
        exclusion_tier = "COMPUTATIONAL_DEPRIORITIZATION"
    elif opp_score >= 55.0:
        lifecycle_status = "ACTIVE"
        exclusion_tier = "INCLUDED_ACTIVE_PRIORITY"
    else:
        lifecycle_status = "ACTIVE"
        exclusion_tier = "INCLUDED_ACTIVE_STANDARD"

    # Data quality flag
    if not is_valid_condition_id(condition_id) or len(token_ids) < 2:
        data_quality_flag = "MISSING_CRITICAL_METADATA"
    elif closed:
        data_quality_flag = "RESOLVED_FINAL_SETTLEMENT" if resolved_outcome else "RESOLVED_AMBIGUOUS_PRICES"
    elif best_bid is not None and best_ask is not None and (bid_ask_spread or 0.0) <= 0.20:
        data_quality_flag = "OBSERVED_GAMMA_TOP_OF_BOOK"
    elif best_bid is not None or best_ask is not None:
        data_quality_flag = "GAMMA_ONE_SIDED_OR_WIDE_BOOK"
    else:
        data_quality_flag = "GAMMA_INDICATIVE_NO_ACTIVE_QUOTES"

    all_exclusion_reasons = perm_reasons if perm_reasons else deprio_reasons

    return {
        "market_id": market_id,
        "event_id": event_id,
        "condition_id": condition_id,
        "slug": slug,
        "category": category,
        "subcategory": subcategory,
        "asset_or_entity": asset_or_entity,
        "question": question,
        "outcomes": outcomes,
        "yes_token_id": yes_token_id,
        "no_token_id": no_token_id,
        "resolution_source": resolution_source,
        "oracle_mechanism": oracle_mechanism,
        "resolution_criteria_summary": rule_clean,
        "created_at_iso": created_iso,
        "end_date_iso": end_iso,
        "closed_time_iso": closed_iso if closed else "",
        "market_age_hours": age_hours,
        "time_to_maturity_hours": ttc_hours,
        "maturity_bucket": maturity_bucket,
        "is_newly_created_48h": is_newly_created_48h,
        "is_long_duration_60d": is_long_duration_60d,
        "liquidity_usd": liquidity_usd,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid_price,
        "bid_ask_spread": bid_ask_spread,
        "spread_bps_of_mid": spread_bps_of_mid,
        "l2_sampled": False,
        "l2_bid_depth_top5_usd": None,
        "l2_ask_depth_top5_usd": None,
        "l2_imbalance_top5": None,
        "volume_24h_usd": volume_24h_usd,
        "volume_total_usd": volume_total_usd,
        "one_day_price_change": one_day_price_change,
        "fees_enabled": fees_enabled,
        "fee_type": fee_type,
        "fee_schedule_rate": fee_schedule_rate,
        "fee_exponent": fee_exponent,
        "maker_rebate_rate": maker_rebate_rate,
        "taker_base_fee_bps": taker_base_bps,
        "maker_base_fee_bps": effective_maker_bps,
        "effective_taker_fee_per_share": fee_ps,
        "effective_taker_fee_bps_on_yes": fee_bps_yes,
        "effective_taker_fee_bps_on_no": fee_bps_no,
        "tick_size": tick_size,
        "min_order_size": min_order_size,
        "holding_rewards_enabled": holding_rewards,
        "rewards_max_spread": rewards_max_spread,
        "neg_risk": neg_risk,
        "neg_risk_augmented": neg_risk_augmented,
        "neg_risk_market_id": neg_risk_market_id,
        "structure_type": event_structure_type,
        "sibling_market_count": sibling_market_count,
        "contract_semantics": polarity_type,
        "is_negated_question": is_negated,
        "is_other_catchall": is_other,
        "is_augmented_placeholder": is_placeholder,
        "is_kmia_d001_locked": is_kmia_d001,
        "lifecycle_status": lifecycle_status,
        "uma_resolution_status": uma_status,
        "resolved_outcome": resolved_outcome,
        "settlement_payout_yes": settlement_payout_yes,
        "data_quality_flag": data_quality_flag,
        "directional_opportunity_score": opp_score,
        "inefficiency_potential_score": ineff_score,
        "execution_friction_penalty": friction_pen,
        "alpha_mechanisms": mechanisms,
        "exclusion_tier": exclusion_tier,
        "exclusion_reasons": all_exclusion_reasons,
    }


def infer_event_structure_type(raw_ev: Mapping[str, Any], raw_mkts: Sequence[Mapping[str, Any]]) -> Tuple[str, int]:
    active_mkts = [
        m for m in raw_mkts
        if isinstance(m, Mapping) and bool(m.get("active", True)) and not bool(m.get("closed", False))
    ]
    n_sib = max(1, len(active_mkts) if active_mkts else len(raw_mkts))
    any_nr = bool(raw_ev.get("negRisk") or raw_ev.get("enableNegRisk") or any(m.get("negRisk") for m in raw_mkts if isinstance(m, Mapping)))
    any_aug = bool(
        raw_ev.get("negRiskAugmented")
        or raw_ev.get("augmentedNegRisk")
        or raw_ev.get("enableNegRiskOther")
        or any(m.get("negRiskOther") for m in raw_mkts if isinstance(m, Mapping))
    )

    for m in active_mkts:
        outs = parse_str_list(m.get("outcomes"))
        if len(outs) > 2:
            return "NON_BINARY_OUTCOMES", n_sib

    if n_sib <= 1:
        return "SINGLE_BINARY", 1
    if any_nr and any_aug:
        return "MULTI_OUTCOME_AUGMENTED_NEGRISK", n_sib
    if any_nr:
        return "MULTI_OUTCOME_NEGRISK", n_sib

    txt = f"{raw_ev.get('title') or ''} {raw_ev.get('slug') or ''}".lower()
    if re.match(r"^(?:nba|nfl|nhl|mlb|cfb|cbb|epl|ucl|ufc|atp|wta|mls|cs2|lol|dota2)-", str(raw_ev.get("slug") or "").lower()):
        return "MULTI_MARKET_SPORTS_SLATE", n_sib
    if _STRIKE_THRESHOLD_RE.search(txt):
        return "MULTI_MARKET_THRESHOLD_LADDER", n_sib
    if _TEMPORAL_LADDER_RE.search(txt):
        return "MULTI_MARKET_TEMPORAL_LADDER", n_sib
    return "MULTI_MARKET_INDEPENDENT", n_sib


def enrich_records_with_clob_books(
    records: Sequence[Dict[str, Any]],
    *,
    client: PublicPolymarketDiscoveryClient,
    max_markets_to_sample: int = 1800,
    per_category_quota: int = 160,
) -> Dict[str, Any]:
    """
    Selects a stratified + top-opportunity cohort across ALL 10 canonical categories and queries
    live CLOB `POST /books` (in `<=450`-token batches) + `GET /fee-rate` verification across every
    observed `fee_type`. Updates `records` in place with observed L2 top-5 depth, imbalance, and
    quote agreement diagnostics.
    """
    by_cat: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        if rec["lifecycle_status"] == "ACTIVE" and rec["yes_token_id"] and rec["no_token_id"]:
            if "PERM_" not in ",".join(rec["exclusion_reasons"]):
                by_cat[rec["category"]].append(rec)

    selected_by_id: Dict[str, Dict[str, Any]] = {}
    for cat in CANONICAL_CATEGORIES:
        pool = sorted(
            by_cat.get(cat, ()),
            key=lambda r: (r["directional_opportunity_score"], r["volume_24h_usd"]),
            reverse=True,
        )
        for rec in pool[:per_category_quota]:
            selected_by_id[rec["market_id"]] = rec

    if len(selected_by_id) < max_markets_to_sample:
        rem_pool = sorted(
            (
                r for r in records
                if r["lifecycle_status"] == "ACTIVE"
                and r["yes_token_id"]
                and r["no_token_id"]
                and r["market_id"] not in selected_by_id
                and "PERM_" not in ",".join(r["exclusion_reasons"])
            ),
            key=lambda r: r["directional_opportunity_score"],
            reverse=True,
        )
        for rec in rem_pool[: max(0, max_markets_to_sample - len(selected_by_id))]:
            selected_by_id[rec["market_id"]] = rec

    selected_list = list(selected_by_id.values())
    token_to_rec_side: Dict[str, Tuple[Dict[str, Any], str]] = {}
    all_tokens: List[str] = []
    for rec in selected_list:
        yt = rec["yes_token_id"]
        nt = rec["no_token_id"]
        token_to_rec_side[yt] = (rec, "YES")
        token_to_rec_side[nt] = (rec, "NO")
        all_tokens.append(yt)
        all_tokens.append(nt)

    books_by_token: Dict[str, Mapping[str, Any]] = {}
    batches_sent = 0
    for idx in range(0, len(all_tokens), CLOB_BOOKS_BATCH_SIZE):
        chunk = all_tokens[idx : idx + CLOB_BOOKS_BATCH_SIZE]
        payload = [{"token_id": tid} for tid in chunk]
        st, resp = client.request_json("POST", f"{CLOB_API_BASE}/books", json_body=payload)
        batches_sent += 1
        if st == 200 and isinstance(resp, list):
            for bk in resp:
                if isinstance(bk, Mapping):
                    aid = str(bk.get("asset_id") or bk.get("token_id") or "").strip()
                    if aid:
                        books_by_token[aid] = bk

    def _top5_stats(bk: Optional[Mapping[str, Any]]) -> Tuple[Optional[float], Optional[float], float, float]:
        if not bk:
            return None, None, 0.0, 0.0
        bids_raw = bk.get("bids") or ()
        asks_raw = bk.get("asks") or ()
        bids: List[Tuple[float, float]] = []
        for b in bids_raw:
            if isinstance(b, Mapping):
                px = float(safe_float(b.get("price"), 0.0) or 0.0)
                sz = float(safe_float(b.get("size"), 0.0) or 0.0)
                if 0.0 < px < 1.0 and sz > 0.0:
                    bids.append((px, sz))
        bids.sort(key=lambda x: x[0], reverse=True)
        asks: List[Tuple[float, float]] = []
        for a in asks_raw:
            if isinstance(a, Mapping):
                px = float(safe_float(a.get("price"), 0.0) or 0.0)
                sz = float(safe_float(a.get("size"), 0.0) or 0.0)
                if 0.0 < px <= 1.0 and sz > 0.0:
                    asks.append((px, sz))
        asks.sort(key=lambda x: x[0])

        bb = round(bids[0][0], 5) if bids else None
        ba = round(asks[0][0], 5) if asks else None
        b_usd = round(sum(px * sz for px, sz in bids[:5]), 2)
        a_usd = round(sum(px * sz for px, sz in asks[:5]), 2)
        return bb, ba, b_usd, a_usd

    gamma_clob_spread_diffs: List[float] = []
    two_sided_l2_count = 0
    for rec in selected_list:
        ybk = books_by_token.get(rec["yes_token_id"])
        nbk = books_by_token.get(rec["no_token_id"])
        if ybk is None and nbk is None:
            continue
        y_bb, y_ba, y_b_usd, y_a_usd = _top5_stats(ybk)
        _, _, n_b_usd, _ = _top5_stats(nbk)
        # Note: On Polymarket binary CTF books, resting NO bids mirror YES asks; record direct YES L2 book depth + combined liquidity
        eff_ask_depth = round(max(y_a_usd, n_b_usd), 2)
        tot_top5 = y_b_usd + eff_ask_depth
        imbalance = round((y_b_usd - eff_ask_depth) / tot_top5, 4) if tot_top5 > 0.0 else 0.0

        rec["l2_sampled"] = True
        rec["l2_bid_depth_top5_usd"] = y_b_usd
        rec["l2_ask_depth_top5_usd"] = eff_ask_depth
        rec["l2_imbalance_top5"] = imbalance
        if y_bb is not None and y_ba is not None and y_ba >= y_bb:
            two_sided_l2_count += 1
            clob_sp = round(y_ba - y_bb, 5)
            if rec["bid_ask_spread"] is not None:
                gamma_clob_spread_diffs.append(abs(clob_sp - float(rec["bid_ask_spread"])))
            rec["best_bid"] = y_bb
            rec["best_ask"] = y_ba
            rec["mid_price"] = round(0.5 * (y_bb + y_ba), 5)
            rec["bid_ask_spread"] = clob_sp
            rec["data_quality_flag"] = "OBSERVED_CLOB_L2_AND_GAMMA"

    # Cross-verify live CLOB `/fee-rate` across one representative token per distinct `fee_type`
    fee_type_samples: Dict[str, str] = {}
    for rec in selected_list:
        ft = rec["fee_type"]
        if ft not in fee_type_samples and rec["yes_token_id"]:
            fee_type_samples[ft] = rec["yes_token_id"]

    fee_rate_checks: Dict[str, Any] = {}
    for ft, tid in sorted(fee_type_samples.items()):
        st_f, resp_f = client.request_json(
            "GET",
            f"{CLOB_API_BASE}/fee-rate?token_id={urllib.parse.quote(tid, safe='')}",
        )
        if st_f == 200 and isinstance(resp_f, Mapping):
            fee_rate_checks[ft] = {"token_id_prefix": tid[:18], "clob_base_fee": resp_f.get("base_fee")}

    gamma_clob_spread_diffs.sort()
    return {
        "markets_targeted_for_l2": len(selected_list),
        "tokens_queried": len(all_tokens),
        "post_books_batches": batches_sent,
        "tokens_returned": len(books_by_token),
        "two_sided_l2_markets_verified": two_sided_l2_count,
        "gamma_vs_clob_spread_abs_diff": quantiles_from_sorted(gamma_clob_spread_diffs),
        "live_clob_fee_rate_verification_by_fee_type": fee_rate_checks,
    }


def discover_full_directional_universe(
    *,
    client: Optional[PublicPolymarketDiscoveryClient] = None,
    max_active_keyset_pages: Optional[int] = None,
    include_clob_sampling_overlay: bool = True,
    include_live_l2_enrichment: bool = True,
    max_l2_sample_markets: int = 1800,
    closed_events_pages: int = 18,
    closed_category_tag_pages: int = 3,
    closed_sibling_retention_days: float = 45.0,
    max_closed_sports_siblings: int = 3000,
    progress_fn: Optional[Callable[[str], None]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Executes the complete unrestricted Polymarket directional market universe discovery:
      1. Paginates CLOB `/sampling-markets` (`next_cursor` until `LTE=`).
      2. Paginates 100% of active unclosed Gamma `/events/keyset?active=true&closed=false&limit=200`
         (`Accept-Encoding: gzip`, zero hardcoded symbol/category caps), retaining 100% of active
         markets plus recent/non-sports closed sibling contracts for historical research.
      3. Paginates recently resolved (`closed=true`) events & markets ordered by `closedTime DESC`
         plus tag-stratified resolved sweeps across Crypto, Weather, Politics, Economics, Finance,
         Geopolitics, Tech/AI, Culture, Science, and Sports so all 10 categories have deep resolved
         coverage (including low-volume and losing contracts).
      4. Enriches stratified multi-category active markets with live CLOB `POST /books` L2 snapshots
         and `GET /fee-rate` verification.
      5. Synthesizes `inventory_doc` (`universe_inventory.json`) and `summary_doc` (`universe_summary.json`).
    """
    own_client = client is None
    http_client = client or PublicPolymarketDiscoveryClient()
    t0 = time.time()
    eval_ts = t0

    try:
        clob_by_cid: Dict[str, Dict[str, Any]] = {}
        clob_pages = 0
        if include_clob_sampling_overlay:
            cursor = ""
            seen_c: Set[str] = set()
            while True:
                q_url = f"{CLOB_API_BASE}/sampling-markets" + (
                    f"?next_cursor={urllib.parse.quote(cursor, safe='')}" if cursor else ""
                )
                st, payload = http_client.request_json("GET", q_url)
                if st != 200 or not isinstance(payload, Mapping):
                    break
                rows = payload.get("data") or []
                clob_pages += 1
                for cm in rows:
                    if not isinstance(cm, Mapping):
                        continue
                    cid = str(cm.get("condition_id") or "").strip().lower()
                    if cid:
                        clob_by_cid[cid] = {
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
                        }
                nc = str(payload.get("next_cursor") or "").strip()
                if not rows or not nc or nc == "LTE=" or nc in seen_c:
                    break
                seen_c.add(nc)
                cursor = nc
            if progress_fn:
                progress_fn(f"[CLOB sampling] pages={clob_pages} unique_conditions={len(clob_by_cid)} ({time.time()-t0:.1f}s)")

        records_by_mid: Dict[str, Dict[str, Any]] = {}
        active_events_seen = 0
        raw_closed_siblings_seen = 0
        raw_closed_siblings_by_cat: Counter[str] = Counter()
        gamma_active_pages = 0

        after_cursor: Optional[str] = None
        seen_gamma_cursors: Set[str] = set()
        sibling_cutoff_ts = eval_ts - (closed_sibling_retention_days * 86400.0)

        while True:
            if max_active_keyset_pages is not None and gamma_active_pages >= max_active_keyset_pages:
                break
            q = "/events/keyset?active=true&closed=false&limit=200"
            if after_cursor:
                q += "&after_cursor=" + urllib.parse.quote(after_cursor, safe="")
            st_g, body_g = http_client.request_json("GET", f"{GAMMA_API_BASE}{q}")
            if st_g != 200 or not isinstance(body_g, Mapping):
                raise RuntimeError(f"Gamma /events/keyset failed HTTP {st_g}: {str(body_g)[:200]}")

            nc_g = str(body_g.get("next_cursor") or "").strip()
            raw_evts = body_g.get("events") or []
            if not raw_evts:
                break
            gamma_active_pages += 1

            for raw_ev in raw_evts:
                if not isinstance(raw_ev, Mapping):
                    continue
                active_events_seen += 1
                raw_mkts = raw_ev.get("markets") if isinstance(raw_ev.get("markets"), list) else []
                ev_struct, n_sib = infer_event_structure_type(raw_ev, raw_mkts)

                for rm in raw_mkts:
                    if not isinstance(rm, Mapping):
                        continue
                    mid_s = str(rm.get("id") or "").strip()
                    if not mid_s:
                        continue
                    is_closed_sib = bool(rm.get("closed", False) or rm.get("archived", False) or not rm.get("active", True))
                    if is_closed_sib:
                        raw_closed_siblings_seen += 1
                        # Retain closed siblings if non-sports or within bounded sports sibling sample (keeping 100% of active markets!)
                        c_ts = parse_iso_ts(rm.get("closedTime") or rm.get("endDate"))
                        ft_s = str(rm.get("feeType") or "").lower()
                        is_sports_sib = "sports" in ft_s
                        if is_sports_sib and (
                            c_ts is None
                            or c_ts < sibling_cutoff_ts
                            or raw_closed_siblings_by_cat["sports"] >= max_closed_sports_siblings
                        ):
                            raw_closed_siblings_by_cat["sports_omitted_beyond_resolved_sample_cap"] += 1
                            continue

                    cid_l = str(rm.get("conditionId") or "").strip().lower()
                    rec = build_directional_market_record(
                        rm,
                        parent_event=raw_ev,
                        clob_overlay=clob_by_cid.get(cid_l) if cid_l else None,
                        sibling_market_count=n_sib,
                        event_structure_type=ev_struct,
                        now_ts=eval_ts,
                        lifecycle_hint="CLOSED_SIBLING" if is_closed_sib else "ACTIVE",
                    )
                    if is_closed_sib:
                        raw_closed_siblings_by_cat[rec["category"]] += 1
                    records_by_mid[mid_s] = rec

            if gamma_active_pages % 25 == 0:
                gc.collect()
                if progress_fn:
                    progress_fn(
                        f"[Gamma active keyset] pages={gamma_active_pages} events={active_events_seen} "
                        f"records={len(records_by_mid)} ({time.time()-t0:.1f}s)"
                    )

            if not nc_g or nc_g in seen_gamma_cursors:
                break
            seen_gamma_cursors.add(nc_g)
            after_cursor = nc_g

        # Reconcile any active CLOB-only markets absent from Gamma active events
        seen_cids = {r["condition_id"].lower() for r in records_by_mid.values() if r["condition_id"]}
        clob_standalone_added = 0
        for cid_l, cm_ov in clob_by_cid.items():
            if cid_l in seen_cids or cm_ov.get("closed") or not cm_ov.get("active", True):
                continue
            rec_c = build_directional_market_record(
                {},
                parent_event=None,
                clob_overlay=cm_ov,
                sibling_market_count=1,
                event_structure_type="SINGLE_BINARY",
                now_ts=eval_ts,
                lifecycle_hint="ACTIVE",
            )
            if rec_c["market_id"] and rec_c["market_id"] not in records_by_mid:
                records_by_mid[rec_c["market_id"]] = rec_c
                clob_standalone_added += 1

        # Paginate recently resolved (`closed=true`) standalone events & category-stratified closed events
        closed_pages_fetched = 0
        for pg in range(max(0, int(closed_events_pages))):
            off = pg * 100
            if off > 2000:
                break
            q_ce = f"/events?closed=true&limit=100&offset={off}&order=closedTime&ascending=false"
            st_ce, evs_ce = http_client.request_json("GET", f"{GAMMA_API_BASE}{q_ce}")
            if st_ce != 200 or not isinstance(evs_ce, list) or not evs_ce:
                break
            closed_pages_fetched += 1
            for raw_ev in evs_ce:
                if not isinstance(raw_ev, Mapping):
                    continue
                raw_mkts = raw_ev.get("markets") if isinstance(raw_ev.get("markets"), list) else []
                ev_struct, n_sib = infer_event_structure_type(raw_ev, raw_mkts)
                for rm in raw_mkts:
                    if not isinstance(rm, Mapping):
                        continue
                    mid_s = str(rm.get("id") or "").strip()
                    if not mid_s or mid_s in records_by_mid:
                        continue
                    cid_l = str(rm.get("conditionId") or "").strip().lower()
                    records_by_mid[mid_s] = build_directional_market_record(
                        rm,
                        parent_event=raw_ev,
                        clob_overlay=clob_by_cid.get(cid_l) if cid_l else None,
                        sibling_market_count=n_sib,
                        event_structure_type=ev_struct,
                        now_ts=eval_ts,
                        lifecycle_hint="RECENTLY_RESOLVED",
                    )

        # Tag-stratified resolved sweeps so non-sports/non-crypto categories also have rich resolved histories
        stratified_tags = (
            "crypto",
            "weather",
            "politics",
            "economics",
            "fed",
            "finance",
            "stocks",
            "geopolitics",
            "ai",
            "tech",
            "science",
            "culture",
        )
        for tag_slug in stratified_tags:
            for pg in range(max(0, int(closed_category_tag_pages))):
                off = pg * 100
                q_t = f"/events?closed=true&tag_slug={urllib.parse.quote(tag_slug)}&limit=100&offset={off}&order=closedTime&ascending=false"
                st_t, evs_t = http_client.request_json("GET", f"{GAMMA_API_BASE}{q_t}")
                if st_t != 200 or not isinstance(evs_t, list) or not evs_t:
                    break
                closed_pages_fetched += 1
                for raw_ev in evs_t:
                    if not isinstance(raw_ev, Mapping):
                        continue
                    raw_mkts = raw_ev.get("markets") if isinstance(raw_ev.get("markets"), list) else []
                    ev_struct, n_sib = infer_event_structure_type(raw_ev, raw_mkts)
                    for rm in raw_mkts:
                        if not isinstance(rm, Mapping):
                            continue
                        mid_s = str(rm.get("id") or "").strip()
                        if not mid_s or mid_s in records_by_mid:
                            continue
                        cid_l = str(rm.get("conditionId") or "").strip().lower()
                        records_by_mid[mid_s] = build_directional_market_record(
                            rm,
                            parent_event=raw_ev,
                            clob_overlay=clob_by_cid.get(cid_l) if cid_l else None,
                            sibling_market_count=n_sib,
                            event_structure_type=ev_struct,
                            now_ts=eval_ts,
                            lifecycle_hint="RECENTLY_RESOLVED",
                        )

        if progress_fn:
            progress_fn(
                f"[Resolved sweep] closed_pages={closed_pages_fetched} total_records={len(records_by_mid)} ({time.time()-t0:.1f}s)"
            )

        all_records = list(records_by_mid.values())
        del records_by_mid, clob_by_cid
        gc.collect()

        # Live CLOB L2 order-book + fee-rate enrichment across all categories
        l2_enrichment_report: Dict[str, Any] = {}
        if include_live_l2_enrichment and max_l2_sample_markets > 0:
            l2_enrichment_report = enrich_records_with_clob_books(
                all_records,
                client=http_client,
                max_markets_to_sample=max_l2_sample_markets,
            )
            if progress_fn:
                progress_fn(
                    f"[CLOB L2 enrichment] sampled={l2_enrichment_report.get('markets_targeted_for_l2')} "
                    f"two_sided_verified={l2_enrichment_report.get('two_sided_l2_markets_verified')} ({time.time()-t0:.1f}s)"
                )

        # Deterministic sort: highest directional opportunity score first, then 24h volume, then market_id
        all_records.sort(
            key=lambda r: (
                1 if r["lifecycle_status"] == "ACTIVE" else 0,
                r["directional_opportunity_score"],
                r["volume_24h_usd"],
                r["market_id"],
            ),
            reverse=True,
        )

        wall_sec = round(time.time() - t0, 3)
        summary_doc = compile_universe_summary(
            all_records,
            generated_at_ts=time.time(),
            wall_time_sec=wall_sec,
            active_events_seen=active_events_seen,
            gamma_active_pages=gamma_active_pages,
            closed_pages_fetched=closed_pages_fetched,
            clob_sampling_pages=clob_pages,
            clob_standalone_added=clob_standalone_added,
            raw_closed_siblings_seen=raw_closed_siblings_seen,
            raw_closed_siblings_by_cat=dict(raw_closed_siblings_by_cat),
            l2_enrichment_report=l2_enrichment_report,
            http_stats=dict(http_client.stats),
            sweep_truncated=max_active_keyset_pages is not None,
        )

        inventory_doc = {
            "schema_version": "1.0",
            "campaign": "DOMINUS_DIRECTIONAL_ALPHA_V1",
            "agent": "Agent A (@universe-map)",
            "generated_at_utc": summary_doc["generated_at_utc"],
            "generated_at_unix": summary_doc["generated_at_unix"],
            "sweep_truncated": summary_doc["sweep_truncated"],
            "total_records": len(all_records),
            "counts_by_exclusion_tier": summary_doc["universe_overview"]["counts_by_exclusion_tier"],
            "markets": all_records,
        }
        return inventory_doc, summary_doc
    finally:
        if own_client:
            http_client.close()


# ===========================================================================
# Empirical Universe Summary & Segment Microstructure Compiler
# ===========================================================================


def compile_universe_summary(
    records: Sequence[Dict[str, Any]],
    *,
    generated_at_ts: float,
    wall_time_sec: float,
    active_events_seen: int,
    gamma_active_pages: int,
    closed_pages_fetched: int,
    clob_sampling_pages: int,
    clob_standalone_added: int,
    raw_closed_siblings_seen: int,
    raw_closed_siblings_by_cat: Mapping[str, int],
    l2_enrichment_report: Mapping[str, Any],
    http_stats: Mapping[str, int],
    sweep_truncated: bool = False,
) -> Dict[str, Any]:
    """Builds exact empirical category, fee, spread, liquidity, and inefficiency tables."""
    gen_utc = datetime.fromtimestamp(generated_at_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    tier_counts: Counter[str] = Counter()
    lifecycle_counts: Counter[str] = Counter()
    perm_reason_counts: Counter[str] = Counter()
    deprio_reason_counts: Counter[str] = Counter()
    data_quality_counts: Counter[str] = Counter()
    structure_counts_active: Counter[str] = Counter()
    maturity_counts_active: Counter[str] = Counter()
    semantics_counts_active: Counter[str] = Counter()
    oracle_counts_active: Counter[str] = Counter()
    mechanism_counts_active: Counter[str] = Counter()
    crypto_asset_counts_active: Counter[str] = Counter()

    # Per-category accumulators
    cat_stats: Dict[str, Dict[str, Any]] = {}
    for c in CANONICAL_CATEGORIES:
        cat_stats[c] = {
            "active_markets": 0,
            "active_priority_markets": 0,
            "active_standard_markets": 0,
            "active_deprioritized_markets": 0,
            "active_permanently_excluded": 0,
            "resolved_markets": 0,
            "zero_fee_active_markets": 0,
            "fee_enabled_active_markets": 0,
            "neg_risk_active_markets": 0,
            "newly_created_48h_active": 0,
            "long_duration_60d_active": 0,
            "volume_24h_usd_total": 0.0,
            "liquidity_usd_total": 0.0,
            "_spreads": [],
            "_liq": [],
            "_scores": [],
            "_fee_bps_yes": [],
            "_fee_bps_no": [],
            "_l2_top5_depth": [],
        }

    subcat_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "category": "",
            "active_markets": 0,
            "resolved_markets": 0,
            "priority_markets": 0,
            "zero_fee_active": 0,
            "volume_24h_usd": 0.0,
            "liquidity_usd": 0.0,
            "_spreads": [],
            "_scores": [],
        }
    )

    fee_schedule_registry: Dict[str, Dict[str, Any]] = {}
    all_active_spreads: List[float] = []
    all_active_liq: List[float] = []
    all_active_scores: List[float] = []

    newly_48h_count = 0
    long_60d_count = 0
    neg_risk_active_total = 0
    zero_fee_active_total = 0
    fee_enabled_active_total = 0
    negated_active_total = 0
    kmia_locked_found: List[str] = []

    for rec in records:
        tier = rec["exclusion_tier"]
        lc = rec["lifecycle_status"]
        cat = rec["category"]
        sub = rec["subcategory"]
        tier_counts[tier] += 1
        lifecycle_counts[lc] += 1
        data_quality_counts[rec["data_quality_flag"]] += 1

        if rec.get("is_kmia_d001_locked"):
            kmia_locked_found.append(rec["market_id"])

        for code in rec["exclusion_reasons"]:
            if code in PERMANENT_EXCLUSION_CODES:
                perm_reason_counts[code] += 1
            elif code in COMPUTATIONAL_DEPRIORITIZATION_CODES:
                deprio_reason_counts[code] += 1

        cs = cat_stats.setdefault(
            cat,
            {
                "active_markets": 0,
                "active_priority_markets": 0,
                "active_standard_markets": 0,
                "active_deprioritized_markets": 0,
                "active_permanently_excluded": 0,
                "resolved_markets": 0,
                "zero_fee_active_markets": 0,
                "fee_enabled_active_markets": 0,
                "neg_risk_active_markets": 0,
                "newly_created_48h_active": 0,
                "long_duration_60d_active": 0,
                "volume_24h_usd_total": 0.0,
                "liquidity_usd_total": 0.0,
                "_spreads": [],
                "_liq": [],
                "_scores": [],
                "_fee_bps_yes": [],
                "_fee_bps_no": [],
                "_l2_top5_depth": [],
            },
        )
        ss = subcat_stats[sub]
        ss["category"] = cat

        is_resolved = lc in ("RECENTLY_RESOLVED", "CLOSED_SIBLING")
        if is_resolved:
            cs["resolved_markets"] += 1
            ss["resolved_markets"] += 1
            continue

        # Active / unclosed records
        cs["active_markets"] += 1
        ss["active_markets"] += 1
        cs["volume_24h_usd_total"] += rec["volume_24h_usd"]
        cs["liquidity_usd_total"] += rec["liquidity_usd"]
        ss["volume_24h_usd"] += rec["volume_24h_usd"]
        ss["liquidity_usd"] += rec["liquidity_usd"]

        if tier == "INCLUDED_ACTIVE_PRIORITY":
            cs["active_priority_markets"] += 1
            ss["priority_markets"] += 1
        elif tier == "INCLUDED_ACTIVE_STANDARD":
            cs["active_standard_markets"] += 1
        elif tier == "COMPUTATIONAL_DEPRIORITIZATION":
            cs["active_deprioritized_markets"] += 1
        elif tier == "PERMANENT_EXCLUSION":
            cs["active_permanently_excluded"] += 1

        structure_counts_active[rec["structure_type"]] += 1
        maturity_counts_active[rec["maturity_bucket"]] += 1
        semantics_counts_active[rec["contract_semantics"]] += 1
        oracle_counts_active[rec["oracle_mechanism"]] += 1
        if rec["is_negated_question"]:
            negated_active_total += 1
        for mech in rec["alpha_mechanisms"]:
            mechanism_counts_active[mech] += 1

        if cat == "crypto":
            crypto_asset_counts_active[rec["asset_or_entity"]] += 1

        if rec["is_newly_created_48h"]:
            newly_48h_count += 1
            cs["newly_created_48h_active"] += 1
        if rec["is_long_duration_60d"]:
            long_60d_count += 1
            cs["long_duration_60d_active"] += 1
        if rec["neg_risk"]:
            neg_risk_active_total += 1
            cs["neg_risk_active_markets"] += 1
        if rec["fees_enabled"]:
            fee_enabled_active_total += 1
            cs["fee_enabled_active_markets"] += 1
        else:
            zero_fee_active_total += 1
            cs["zero_fee_active_markets"] += 1
            ss["zero_fee_active"] += 1

        ft = rec["fee_type"]
        if ft not in fee_schedule_registry:
            fee_schedule_registry[ft] = {
                "active_market_count": 0,
                "fees_enabled": rec["fees_enabled"],
                "fee_schedule_rate": rec["fee_schedule_rate"],
                "fee_exponent": rec["fee_exponent"],
                "maker_rebate_rate": rec["maker_rebate_rate"],
                "taker_base_fee_bps": rec["taker_base_fee_bps"],
                "fee_at_50c_per_share_usd": round(rec["fee_schedule_rate"] * (0.25 ** rec["fee_exponent"]), 5) if rec["fees_enabled"] else 0.0,
                "fee_at_50c_bps_of_outlay": round(10000.0 * (rec["fee_schedule_rate"] * (0.25 ** rec["fee_exponent"])) / 0.50, 1) if rec["fees_enabled"] else 0.0,
                "fee_at_90c_no_bps_of_outlay": round(10000.0 * (rec["fee_schedule_rate"] * (0.09 ** rec["fee_exponent"])) / 0.90, 1) if rec["fees_enabled"] else 0.0,
                "fee_at_10c_yes_bps_of_outlay": round(10000.0 * (rec["fee_schedule_rate"] * (0.09 ** rec["fee_exponent"])) / 0.10, 1) if rec["fees_enabled"] else 0.0,
            }
        fee_schedule_registry[ft]["active_market_count"] += 1

        if rec["bid_ask_spread"] is not None:
            sp = float(rec["bid_ask_spread"])
            cs["_spreads"].append(sp)
            ss["_spreads"].append(sp)
            all_active_spreads.append(sp)
        if rec["liquidity_usd"] > 0.0:
            cs["_liq"].append(float(rec["liquidity_usd"]))
            all_active_liq.append(float(rec["liquidity_usd"]))
        if tier in ("INCLUDED_ACTIVE_PRIORITY", "INCLUDED_ACTIVE_STANDARD"):
            sc = float(rec["directional_opportunity_score"])
            cs["_scores"].append(sc)
            ss["_scores"].append(sc)
            all_active_scores.append(sc)
            cs["_fee_bps_yes"].append(float(rec["effective_taker_fee_bps_on_yes"]))
            cs["_fee_bps_no"].append(float(rec["effective_taker_fee_bps_on_no"]))
        if rec["l2_sampled"] and rec["l2_bid_depth_top5_usd"] is not None and rec["l2_ask_depth_top5_usd"] is not None:
            cs["_l2_top5_depth"].append(float(rec["l2_bid_depth_top5_usd"]) + float(rec["l2_ask_depth_top5_usd"]))

    # Finalize per-category & per-subcategory tables
    category_breakdown: Dict[str, Any] = {}
    for cat, cs in cat_stats.items():
        sps = sorted(cs.pop("_spreads"))
        lqs = sorted(cs.pop("_liq"))
        scs = sorted(cs.pop("_scores"))
        f_yes = sorted(cs.pop("_fee_bps_yes"))
        f_no = sorted(cs.pop("_fee_bps_no"))
        l2d = sorted(cs.pop("_l2_top5_depth"))
        cs["volume_24h_usd_total"] = round(cs["volume_24h_usd_total"], 2)
        cs["liquidity_usd_total"] = round(cs["liquidity_usd_total"], 2)
        cs["spread_distribution"] = quantiles_from_sorted(sps)
        cs["liquidity_usd_distribution"] = quantiles_from_sorted(lqs)
        cs["opportunity_score_distribution_included"] = quantiles_from_sorted(scs)
        cs["median_taker_fee_bps_yes_included"] = round(statistics.median(f_yes), 2) if f_yes else 0.0
        cs["median_taker_fee_bps_no_included"] = round(statistics.median(f_no), 2) if f_no else 0.0
        cs["sampled_l2_top5_total_depth_usd"] = quantiles_from_sorted(l2d)
        category_breakdown[cat] = cs

    subcategory_breakdown: List[Dict[str, Any]] = []
    for sub, ss in subcat_stats.items():
        sps = sorted(ss.pop("_spreads"))
        scs = sorted(ss.pop("_scores"))
        subcategory_breakdown.append(
            {
                "subcategory": sub,
                "category": ss["category"],
                "active_markets": ss["active_markets"],
                "resolved_markets": ss["resolved_markets"],
                "priority_markets": ss["priority_markets"],
                "zero_fee_active": ss["zero_fee_active"],
                "volume_24h_usd": round(ss["volume_24h_usd"], 2),
                "liquidity_usd": round(ss["liquidity_usd"], 2),
                "median_spread": round(statistics.median(sps), 5) if sps else None,
                "mean_opportunity_score_included": round(sum(scs) / len(scs), 2) if scs else None,
                "p90_opportunity_score_included": quantiles_from_sorted(scs)["p90"],
            }
        )
    subcategory_breakdown.sort(
        key=lambda r: (r["priority_markets"], r["mean_opportunity_score_included"] or 0.0, r["volume_24h_usd"]),
        reverse=True,
    )

    # Top prioritized opportunities overall and per category (concise pointers for downstream agents)
    def _slim_opp(r: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "market_id": r["market_id"],
            "event_id": r["event_id"],
            "category": r["category"],
            "subcategory": r["subcategory"],
            "asset_or_entity": r["asset_or_entity"],
            "question": r["question"][:120],
            "yes_token_id": r["yes_token_id"],
            "no_token_id": r["no_token_id"],
            "mid_price": r["mid_price"],
            "bid_ask_spread": r["bid_ask_spread"],
            "liquidity_usd": r["liquidity_usd"],
            "volume_24h_usd": r["volume_24h_usd"],
            "fees_enabled": r["fees_enabled"],
            "fee_type": r["fee_type"],
            "fee_schedule_rate": r["fee_schedule_rate"],
            "effective_taker_fee_bps_on_yes": r["effective_taker_fee_bps_on_yes"],
            "effective_taker_fee_bps_on_no": r["effective_taker_fee_bps_on_no"],
            "time_to_maturity_hours": r["time_to_maturity_hours"],
            "market_age_hours": r["market_age_hours"],
            "structure_type": r["structure_type"],
            "sibling_market_count": r["sibling_market_count"],
            "directional_opportunity_score": r["directional_opportunity_score"],
            "inefficiency_potential_score": r["inefficiency_potential_score"],
            "execution_friction_penalty": r["execution_friction_penalty"],
            "alpha_mechanisms": r["alpha_mechanisms"],
        }

    included_active = [r for r in records if r["exclusion_tier"] in ("INCLUDED_ACTIVE_PRIORITY", "INCLUDED_ACTIVE_STANDARD")]
    included_active.sort(key=lambda r: r["directional_opportunity_score"], reverse=True)

    top_by_category: Dict[str, List[Dict[str, Any]]] = {}
    for cat in CANONICAL_CATEGORIES:
        cat_cands = [r for r in included_active if r["category"] == cat]
        top_by_category[cat] = [_slim_opp(r) for r in cat_cands[:12]]

    all_active_spreads.sort()
    all_active_liq.sort()
    all_active_scores.sort()

    active_total = sum(cs["active_markets"] for cs in category_breakdown.values())
    resolved_total = sum(cs["resolved_markets"] for cs in category_breakdown.values())

    return {
        "schema_version": "1.0",
        "campaign": "DOMINUS_DIRECTIONAL_ALPHA_V1",
        "agent": "Agent A (@universe-map)",
        "generated_at_utc": gen_utc,
        "generated_at_unix": round(generated_at_ts, 3),
        "wall_time_sec": wall_time_sec,
        "sweep_truncated": sweep_truncated,
        "safety_and_governance_verification": {
            "mode": "STRICT_PUBLIC_READ_ONLY",
            "allowed_hosts": sorted(ALLOWED_PUBLIC_HOSTS),
            "zero_hardcoded_symbol_or_category_caps": True,
            "kmia_d001_protected_market_ids": sorted(KMIA_D001_FROZEN_MARKET_IDS),
            "kmia_d001_markets_observed_and_locked": sorted(kmia_locked_found),
        },
        "pagination_and_ingestion_stats": {
            "gamma_active_keyset_pages": gamma_active_pages,
            "gamma_closed_pages_fetched": closed_pages_fetched,
            "clob_sampling_pages_fetched": clob_sampling_pages,
            "active_events_discovered": active_events_seen,
            "clob_standalone_markets_reconciled": clob_standalone_added,
            "raw_closed_siblings_inside_active_events_total": raw_closed_siblings_seen,
            "raw_closed_siblings_disposition": dict(raw_closed_siblings_by_cat),
            "http_transport_stats": dict(http_stats),
        },
        "universe_overview": {
            "total_records_in_inventory": len(records),
            "total_active_unclosed_markets": active_total,
            "total_resolved_research_markets_retained": resolved_total,
            "counts_by_exclusion_tier": dict(tier_counts.most_common()),
            "counts_by_lifecycle_status": dict(lifecycle_counts.most_common()),
            "counts_by_data_quality_flag": dict(data_quality_counts.most_common()),
            "zero_fee_active_markets": zero_fee_active_total,
            "fee_enabled_active_markets": fee_enabled_active_total,
            "neg_risk_active_markets": neg_risk_active_total,
            "newly_created_lt_48h_active_markets": newly_48h_count,
            "long_duration_gt_60d_active_markets": long_60d_count,
            "negated_polarity_active_markets": negated_active_total,
            "overall_active_spread_distribution": quantiles_from_sorted(all_active_spreads),
            "overall_active_liquidity_usd_distribution": quantiles_from_sorted(all_active_liq),
            "overall_included_opportunity_score_distribution": quantiles_from_sorted(all_active_scores),
        },
        "exclusion_taxonomy_breakdown": {
            "permanent_exclusion_reasons": dict(perm_reason_counts.most_common()),
            "computational_deprioritization_reasons": dict(deprio_reason_counts.most_common()),
        },
        "structural_and_semantic_breakdown_active": {
            "by_structure_type": dict(structure_counts_active.most_common()),
            "by_maturity_bucket": dict(maturity_counts_active.most_common()),
            "by_contract_semantics": dict(semantics_counts_active.most_common()),
            "by_oracle_mechanism": dict(oracle_counts_active.most_common()),
            "by_alpha_mechanism_tag": dict(mechanism_counts_active.most_common()),
            "crypto_active_markets_by_asset": dict(crypto_asset_counts_active.most_common(30)),
        },
        "fee_schedule_microstructure_table": dict(
            sorted(fee_schedule_registry.items(), key=lambda kv: kv[1]["active_market_count"], reverse=True)
        ),
        "live_clob_l2_verification": dict(l2_enrichment_report),
        "category_breakdown": category_breakdown,
        "subcategory_ranking_by_inefficiency": subcategory_breakdown,
        "top_50_directional_opportunities_overall": [_slim_opp(r) for r in included_active[:50]],
        "top_opportunities_by_category": top_by_category,
    }

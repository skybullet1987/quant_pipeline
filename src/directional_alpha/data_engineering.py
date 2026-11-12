"""Leak-free historical market data engineering & provenance engine (`@data-eng`).

Provides schema definitions, strict data-provenance validation, anti-lookahead
timestamp guards (`RT-01`), contract semantics & negation/polarity classification
(`RT-04`), correlated event cluster keys (`RT-06`), L2 book depth/VWAP extraction
(`RT-02`), and zero-dependency SQLite query helpers for all Dominus directional
alpha research agents.

Strict Operational Invariants:
  - Research-only: zero credentials, zero order placement, zero touches on
    existing production files or `D-001` frozen `KMIA` positions (`6707502`, `6707503`).
  - Pure Python 3.12 stdlib compatible (optional `orjson` acceleration when installed;
    zero `numpy`/`pandas` requirement so suites pass on both `.venv` and LibreOffice Python).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    import orjson as _orjson  # type: ignore
except ImportError:  # pragma: no cover
    _orjson = None


def json_loads(raw: bytes | str) -> Any:
    if _orjson is not None:
        return _orjson.loads(raw)
    return json.loads(raw)


def json_dumps(obj: Any) -> str:
    if _orjson is not None:
        return _orjson.dumps(obj).decode("utf-8")
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DIRECTIONAL_DATA_DIR = REPO_ROOT / "data" / "directional_alpha"
DEFAULT_HISTORICAL_DB_PATH = DEFAULT_DIRECTIONAL_DATA_DIR / "historical_dataset.sqlite3"
DEFAULT_AUDIT_MANIFEST_PATH = DEFAULT_DIRECTIONAL_DATA_DIR / "data_audit_manifest.json"

# Binding D-001 frozen disputed KMIA Nov 7 market IDs (preserved for audit, flagged non-tradable)
KMIA_D001_MARKET_IDS: frozenset[str] = frozenset({"6707502", "6707503"})

# Mandatory Data Provenance Classes (Task 3)
QUALITY_OBSERVED_EXECUTABLE_L2 = "OBSERVED_EXECUTABLE_L2"
QUALITY_OBSERVED_TRADE_OR_CLOB_SERIES = "OBSERVED_TRADE_OR_CLOB_SERIES"
QUALITY_EXTERNAL_PUBLIC_OBSERVED = "EXTERNAL_PUBLIC_OBSERVED"
QUALITY_ESTIMATED_SPREAD_ADJUSTED = "ESTIMATED_SPREAD_ADJUSTED"
QUALITY_UNAVAILABLE = "UNAVAILABLE"

VALID_DATA_QUALITY_CLASSES: frozenset[str] = frozenset(
    {
        QUALITY_OBSERVED_EXECUTABLE_L2,
        QUALITY_OBSERVED_TRADE_OR_CLOB_SERIES,
        QUALITY_EXTERNAL_PUBLIC_OBSERVED,
        QUALITY_ESTIMATED_SPREAD_ADJUSTED,
        QUALITY_UNAVAILABLE,
    }
)

# Canonical Multi-Category Taxonomy
CANONICAL_CATEGORIES: Tuple[str, ...] = (
    "crypto",
    "sports",
    "politics",
    "economics_macro",
    "finance",
    "weather",
    "geopolitics",
    "tech_ai",
    "culture_science",
)

# Default UMA Optimistic Oracle challenge window + proposal latency buffer (2h + 15m = 8,100s)
# Applied when `closedTime` occurs BEFORE `endDate` (meaning `closedTime` reflects UMA settlement
# finalization ~2.25h AFTER the real-world match/weather/event outcome actually clinched!).
UMA_EARLY_CLOSE_CLINCH_BUFFER_SEC = 8100.0
# Minimum safety buffer before scheduled_end_ts on fixed-expiry contracts to prevent clock-skew leakage
FIXED_EXPIRY_SAFETY_BUFFER_SEC = 60.0
# Terminal absorption threshold: once CLOB price enters [0, 0.015] or [0.985, 1.0] and never exits
# prior to resolution, subsequent prints represent post-outcome convergence / UMA carry, NOT pre-outcome alpha.
TERMINAL_ABSORPTION_BAND = 0.015


def validate_data_quality_class(value: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned not in VALID_DATA_QUALITY_CLASSES:
        raise ValueError(
            f"Invalid data_quality_class={cleaned!r}; expected one of {sorted(VALID_DATA_QUALITY_CLASSES)}"
        )
    return cleaned


def parse_utc_timestamp(raw: Any) -> Optional[float]:
    """Parses ISO-8601 / Postgres UTC strings or numeric seconds/ms into UTC epoch seconds."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        if not math.isfinite(val) or val <= 0:
            return None
        if val > 1e11:
            return val / 1000.0
        return val
    text = str(raw).strip()
    if not text:
        return None
    try:
        val = float(text)
        if math.isfinite(val) and val > 0:
            return val / 1000.0 if val > 1e11 else val
    except ValueError:
        pass

    norm = text
    if norm.endswith("Z"):
        norm = norm[:-1] + "+00:00"
    elif re.search(r"[+-]\d{2}$", norm):
        norm = norm + ":00"
    elif " UTC" in norm:
        norm = norm.replace(" UTC", "+00:00")
    if " " in norm and "T" not in norm:
        parts = norm.split(" ", 1)
        if len(parts) == 2 and len(parts[0]) == 10:
            norm = f"{parts[0]}T{parts[1]}"
    if "+" not in norm[10:] and "-" not in norm[11:]:
        norm = norm + "+00:00"
    try:
        dt = datetime.fromisoformat(norm)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).timestamp()
    except ValueError:
        return None


def format_utc_iso(ts_unix: Optional[float]) -> Optional[str]:
    if ts_unix is None or not math.isfinite(ts_unix) or ts_unix <= 0:
        return None
    return datetime.fromtimestamp(float(ts_unix), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Category, Contract Semantics (`RT-04`) & Correlation Cluster (`RT-06`)
# ---------------------------------------------------------------------------

_WEATHER_RE = re.compile(
    r"\b(?:temperature|highest\s+temp|lowest\s+temp|degrees?\s*[cf]\b|°[cf]|fahrenheit|celsius|"
    r"hurricane|typhoon|cyclone|tornado|rainfall|precipitation|snowfall|inches\s+of\s+rain|"
    r"weather|metar|wunderground|noaa|hko)\b",
    re.IGNORECASE,
)
_CRYPTO_RE = re.compile(
    r"\b(?:bitcoin|btc|ethereum|eth|solana|sol|xrp|ripple|dogecoin|doge|bnb|hyperliquid|hype|"
    r"cardano|ada|avalanche|avax|chainlink|sui|pepe|memecoin|crypto|stablecoin|usdt|usdc|"
    r"fdv|airdrop|token\s+launch|tge|binance|coinbase|uniswap|polymarket\s+token)\b",
    re.IGNORECASE,
)
_ECON_MACRO_RE = re.compile(
    r"\b(?:fed\b|federal\s+reserve|fomc|interest\s+rate|rate\s+cut|rate\s+hike|bps\b|cpi\b|"
    r"inflation|pce\b|ppi\b|nonfarm|payroll|nfp\b|unemployment|jobless|gdp\b|recession|"
    r"tariff|ecb\b|bank\s+of\s+england|bank\s+of\s+japan|boj\b|treasury\s+yield|debt\s+ceiling)\b",
    re.IGNORECASE,
)
_FINANCE_RE = re.compile(
    r"\b(?:s&p\s*500|spx|nasdaq|qqq|dow\s+jones|russell\s+2000|nyse|ipo\b|earnings|revenue|"
    r"eps\b|market\s+cap|stock\s+price|share\s+price|nvda|nvidia|tsla|tesla|aapl|apple|"
    r"msft|microsoft|amzn|googl|meta\b|crude\s+oil|wti|brent|gold\s+price|xau|silver\s+price|xag)\b",
    re.IGNORECASE,
)
_GEOPOLITICS_RE = re.compile(
    r"\b(?:ceasefire|invasion|missile|strike\s+on|military|nato\b|ukraine|russia|israel|gaza|"
    r"iran|taiwan|north\s+korea|sanctions|treaty|united\s+nations|un\s+security|regime\s+change|"
    r"hostage|nuclear|war\s+in|border\s+clash|hezbollah|hamas|syria|yemen)\b",
    re.IGNORECASE,
)
_POLITICS_RE = re.compile(
    r"\b(?:election|president|presidential|senate|house\s+of\s+representatives|congress|parliament|"
    r"prime\s+minister|governor|mayor|nominee|nomination|primary|ballot|referendum|approval\s+rating|"
    r"impeach|cabinet|supreme\s+court|scotus|democrat|republican|labour|conservative|trump|biden|"
    r"vance|newsom|harris|starmer|macron|lula|milei|poll\b|legislation|veto)\b",
    re.IGNORECASE,
)
_SPORTS_RE = re.compile(
    r"\b(?:nba|nfl|mlb|nhl|mls|ufc|mma|pga|atp|wta|f1\b|formula\s+1|premier\s+league|champions\s+league|"
    r"la\s+liga|serie\s+a|bundesliga|ligue\s+1|world\s+cup|super\s+bowl|playoffs|stanley\s+cup|"
    r"esports|dota\s*2|counter-strike|cs2|valorant|league\s+of\s+legends|lol\b|vs\.?\s|spread:|"
    r"o/u\s*\d|over/under|moneyline|touchdown|home\s+run|grand\s+slam|game\s+[1-7]\s+winner)\b",
    re.IGNORECASE,
)
_TECH_AI_RE = re.compile(
    r"\b(?:openai|chatgpt|gpt-\d|claude|anthropic|gemini|deepmind|llama|xai|grok|agi\b|"
    r"artificial\s+intelligence|llm\b|frontier\s+model|chatbot\s+arena|lmarena|semiconductor|"
    r"tiktok|spacex|starship|neuralink|robotics|waymo|autonomous|app\s+store|github)\b",
    re.IGNORECASE,
)

_NEGATION_RE = re.compile(
    r"(?:\bnot\b|\bn't\b|\bnever\b|\bwithout\b|\bfail\s+to\b|\bno\s+longer\b|\bnone\s+of\b)",
    re.IGNORECASE,
)
_LOWER_THRESHOLD_RE = re.compile(
    r"(?:\bbelow\b|\bunder\b|\bless\s+than\b|\bfewer\s+than\b|\bdip\s+to\b|\bdrop\s+to\b|\bfall\s+below\b|<=|<)",
    re.IGNORECASE,
)
_UPPER_THRESHOLD_RE = re.compile(
    r"(?:\babove\b|\bover\b|\bmore\s+than\b|\bgreater\s+than\b|\breach\b|\bhit\b|\bexceed\b|>=|>)",
    re.IGNORECASE,
)
_RANGE_BUCKET_RE = re.compile(
    r"(?:\bbetween\b|\d+\s*[-–to]+\s*\d+\s*(?:°[cf]|%|bps|k|m|b)?)",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(
    r"^(?:other|others|any\s+other.*|none\s+of\s+the\s+above|field|placeholder.*|"
    r"(?:person|candidate|player|team|option|company|country)\s+[a-z0-9]{1,3}|tbd.*)$",
    re.IGNORECASE,
)


def classify_market_category(
    question: str,
    slug: str = "",
    tags: Optional[Sequence[str]] = None,
    event_title: str = "",
    raw_category: str = "",
) -> Tuple[str, str]:
    """Deterministically classifies a Polymarket contract into `(category, subcategory)`."""
    tag_blob = " ".join(str(t).lower() for t in (tags or []))
    text = f"{question} {event_title} {slug.replace('-', ' ')} {raw_category} {tag_blob}".strip()
    low = text.lower()

    if "weather" in tag_blob or _WEATHER_RE.search(text):
        sub = "temperature_bucket" if ("temp" in low or "°" in low or "degrees" in low) else "meteorological_event"
        return "weather", sub

    # Check sports BEFORE crypto/politics so esports/team abbreviations don't misroute
    if any(t in tag_blob for t in ("sports", "esports", "nba", "nfl", "mlb", "nhl", "soccer", "tennis", "ufc")) or _SPORTS_RE.search(text):
        if any(k in low for k in ("dota", "cs2", "counter-strike", "valorant", "league of legends", "esports")):
            return "sports", "esports"
        if any(k in low for k in ("o/u", "over/under", "total")):
            return "sports", "totals_over_under"
        if "spread" in low or "handicap" in low:
            return "sports", "spread_handicap"
        return "sports", "match_or_futures"

    if any(t in tag_blob for t in ("economy", "macro", "fed", "inflation", "rates", "jobs", "tariffs")) or _ECON_MACRO_RE.search(text):
        if any(k in low for k in ("fed", "fomc", "ecb", "boj", "rate")):
            return "economics_macro", "central_bank_rates"
        if any(k in low for k in ("cpi", "inflation", "pce", "ppi")):
            return "economics_macro", "inflation_prints"
        return "economics_macro", "macro_indicators"

    if any(t in tag_blob for t in ("crypto", "bitcoin", "ethereum", "solana", "defi", "memecoins")) or _CRYPTO_RE.search(text):
        if "up or down" in low or "up-or-down" in low:
            return "crypto", "intraday_up_down"
        if any(k in low for k in ("above", "below", "hit", "reach", "dip")):
            return "crypto", "price_barrier_or_strike"
        return "crypto", "token_or_protocol_event"

    if any(t in tag_blob for t in ("finance", "stocks", "equities", "earnings", "commodities")) or _FINANCE_RE.search(text):
        if any(k in low for k in ("gold", "silver", "oil", "wti", "xau", "xag")):
            return "finance", "commodities"
        if any(k in low for k in ("earnings", "revenue", "ipo", "market cap")):
            return "finance", "corporate_events"
        return "finance", "equities_and_indices"

    if any(t in tag_blob for t in ("geopolitics", "middle-east", "ukraine", "world-affairs", "war")) or _GEOPOLITICS_RE.search(text):
        return "geopolitics", "conflict_and_diplomacy"

    if any(t in tag_blob for t in ("politics", "elections", "us-politics", "trump", "congress")) or _POLITICS_RE.search(text):
        if any(k in low for k in ("election", "win", "nominee", "president", "governor", "senate", "mayor")):
            return "politics", "elections"
        return "politics", "policy_and_governance"

    if any(t in tag_blob for t in ("ai", "tech", "technology", "spacex", "openai")) or _TECH_AI_RE.search(text):
        return "tech_ai", "ai_and_technology"

    return "culture_science", "culture_entertainment_science"


@dataclass(frozen=True, slots=True)
class ContractSemantics:
    outcomes: Tuple[str, str]
    is_standard_yes_no: bool
    has_negation_semantics: bool
    semantic_type: str
    is_other_or_placeholder: bool


def parse_contract_semantics(
    question: str,
    outcomes: Sequence[str],
    group_item_title: str = "",
    neg_risk_other: bool = False,
) -> ContractSemantics:
    """Explicitly classifies binary outcome labels, negation, thresholds, and placeholders (`RT-04`)."""
    o0 = str(outcomes[0]).strip() if len(outcomes) >= 1 else "Yes"
    o1 = str(outcomes[1]).strip() if len(outcomes) >= 2 else "No"
    l0, l1 = o0.lower(), o1.lower()
    is_std_yn = (l0 == "yes" and l1 == "no")
    has_neg = bool(_NEGATION_RE.search(question))

    grp = str(group_item_title or "").strip()
    is_placeholder = bool(
        neg_risk_other
        or _PLACEHOLDER_RE.match(grp)
        or _PLACEHOLDER_RE.match(question.strip())
    )

    if is_placeholder:
        sem_type = "OTHER_PLACEHOLDER"
    elif (l0, l1) in (("up", "down"), ("higher", "lower"), ("over", "under")):
        sem_type = "UP_DOWN_DIRECTIONAL"
    elif not is_std_yn:
        sem_type = "HEAD_TO_HEAD_MATCHUP"
    elif has_neg:
        sem_type = "NEGATED_QUESTION"
    elif _RANGE_BUCKET_RE.search(question):
        sem_type = "RANGE_BUCKET"
    elif _LOWER_THRESHOLD_RE.search(question):
        sem_type = "LOWER_TAIL_THRESHOLD"
    elif _UPPER_THRESHOLD_RE.search(question):
        sem_type = "UPPER_TAIL_THRESHOLD"
    else:
        sem_type = "STANDARD_AFFIRMATIVE"

    return ContractSemantics(
        outcomes=(o0, o1),
        is_standard_yes_no=is_std_yn,
        has_negation_semantics=has_neg,
        semantic_type=sem_type,
        is_other_or_placeholder=is_placeholder,
    )


def build_correlation_cluster_id(
    *,
    event_id: str,
    category: str,
    slug: str,
    scheduled_end_ts: Optional[float],
    neg_risk_market_id: str = "",
) -> str:
    """Builds a canonical cluster ID (`RT-06`) so correlated strikes/buckets share one bootstrap unit."""
    if neg_risk_market_id:
        return f"NEGRISK:{neg_risk_market_id}"
    if event_id:
        # Also group same-day intraday crypto candles or weather station slates by date+underlying
        day_str = format_utc_iso(scheduled_end_ts)[:10] if scheduled_end_ts else "unknown_day"
        low_slug = slug.lower()
        if category == "crypto":
            for sym in ("btc", "bitcoin", "eth", "ethereum", "sol", "solana", "xrp", "doge", "bnb", "hype"):
                if sym in low_slug:
                    canon = {"bitcoin": "btc", "ethereum": "eth", "solana": "sol"}.get(sym, sym)
                    return f"CRYPTO:{canon}:{day_str}"
        if category == "weather":
            parts = low_slug.split("-")
            city = parts[0] if parts else "wx"
            return f"WEATHER:{city}:{day_str}"
        return f"EVENT:{event_id}"
    digest = hashlib.sha1(f"{category}:{slug}".encode("utf-8")).hexdigest()[:12]
    return f"SLUG:{digest}"


# ---------------------------------------------------------------------------
# Anti-Lookahead & Post-Clinch Detection (`RT-01`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LeakFreeCutoffResult:
    effective_cutoff_ts: float
    uma_pre_close_buffer_sec: float
    terminal_absorption_ts: Optional[float]
    safe_decision_cutoff_ts: float


def detect_terminal_absorption_ts(
    sorted_points: Sequence[Tuple[float, float]],
    band: float = TERMINAL_ABSORPTION_BAND,
) -> Optional[float]:
    """Strictly causal first-passage stopping time `min{t : p(t) <= band or p(t) >= 1 - band}`.

    Remediation for `@red-team` Advisory #1 (`RT-01` / `RT-05`): NEVER walks backwards from
    `sorted_points[-1]`, so the stopping time is 100% independent of whether `p(u)` reverses at
    any future `u > t`. Recorded strictly as an informational diagnostic column; `safe_decision_cutoff_ts`
    depends ONLY on causal schedule / pre-UMA-liveness metadata.
    """
    for t_val, p_val in sorted_points:
        if p_val <= band or p_val >= (1.0 - band):
            return float(t_val)
    return None


def compute_leak_free_cutoff(
    *,
    created_ts: float,
    scheduled_end_ts: Optional[float],
    closed_ts: Optional[float],
    automatically_resolved: bool = False,
    sorted_price_points: Sequence[Tuple[float, float]] = (),
    max_reference_ts: Optional[float] = None,
) -> LeakFreeCutoffResult:
    """Computes strict causal pre-outcome cutoff timestamps (`RT-01` & `RT-05` safe).

    Key empirical Polymarket mechanics accounted for:
      1. Fixed-window markets (e.g., 1h/daily crypto candles): real outcome clinches at
         `scheduled_end_ts`, while `closed_ts` (`closedTime`) happens minutes/hours AFTER `scheduled_end_ts`.
         Here `effective_cutoff_ts = scheduled_end_ts - 60s`.
      2. Early-clinching markets (sports matches, weather daily highs, legislation votes,
         nominations): real outcome clinches BEFORE `scheduled_end_ts`, and `closed_ts` occurs ~2h+
         AFTER clinch due to the UMA Optimistic Oracle liveness challenge window!
         Whenever `closed_ts < scheduled_end_ts`, we subtract `UMA_EARLY_CLOSE_CLINCH_BUFFER_SEC`
         (or `1800s` if `automaticallyResolved` fast oracle).
      3. Zero Future-Price Conditioning (`@red-team` #12): `safe_decision_cutoff_ts` is computed
         exclusively from schedule/UMA timestamps (`candidates` never inspects `sorted_price_points`),
         guaranteeing identical cutoff semantics regardless of future price reversals or outcomes!
    """
    valid_sched = scheduled_end_ts if (scheduled_end_ts is not None and scheduled_end_ts > 0) else None
    valid_closed = closed_ts if (closed_ts is not None and closed_ts > 0) else None

    if valid_sched is not None and valid_closed is not None:
        effective_cutoff = min(valid_sched, valid_closed)
    elif valid_closed is not None:
        effective_cutoff = valid_closed
    elif valid_sched is not None:
        effective_cutoff = valid_sched
    else:
        effective_cutoff = created_ts + 3600.0

    if max_reference_ts is not None and effective_cutoff > max_reference_ts:
        effective_cutoff = float(max_reference_ts)

    # Determine UMA pre-close clinch buffer purely from metadata (zero price-path peeking!)
    if valid_closed is not None and (valid_sched is None or valid_closed < valid_sched - 300.0):
        raw_buf = 1800.0 if automatically_resolved else UMA_EARLY_CLOSE_CLINCH_BUFFER_SEC
        lifetime = max(60.0, valid_closed - created_ts)
        uma_buf = min(raw_buf, 0.45 * lifetime)
    else:
        uma_buf = FIXED_EXPIRY_SAFETY_BUFFER_SEC

    term_ts = detect_terminal_absorption_ts(sorted_price_points)

    candidates = [effective_cutoff - FIXED_EXPIRY_SAFETY_BUFFER_SEC]
    if valid_closed is not None:
        candidates.append(valid_closed - uma_buf)

    safe_cutoff = min(candidates)
    if safe_cutoff <= created_ts:
        safe_cutoff = created_ts + max(1.0, 0.5 * (effective_cutoff - created_ts))

    return LeakFreeCutoffResult(
        effective_cutoff_ts=float(effective_cutoff),
        uma_pre_close_buffer_sec=float(uma_buf),
        terminal_absorption_ts=term_ts,
        safe_decision_cutoff_ts=float(safe_cutoff),
    )


# ---------------------------------------------------------------------------
# L2 Orderbook Metrics & Executable VWAP Helpers (`RT-02`)
# ---------------------------------------------------------------------------


def parse_l2_side(levels: Sequence[Any], descending: bool) -> List[Tuple[float, float]]:
    """Normalizes raw `[[px, sz], ...]` or `[{'price': ..., 'size': ...}]` into sorted `(price, shares)`."""
    parsed: List[Tuple[float, float]] = []
    for item in levels or ():
        try:
            if isinstance(item, Mapping):
                px = float(item.get("price", 0.0))
                sz = float(item.get("size", 0.0))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                px = float(item[0])
                sz = float(item[1])
            else:
                continue
            if 0.0 < px < 1.0 and sz > 0.0 and math.isfinite(px) and math.isfinite(sz):
                parsed.append((round(px, 6), round(sz, 4)))
        except (TypeError, ValueError):
            continue
    parsed.sort(key=lambda x: x[0], reverse=descending)
    return parsed


def compute_book_vwap_for_notional(
    levels: Sequence[Tuple[float, float]],
    target_notional_usd: float,
    is_buy_ask: bool,
) -> Optional[float]:
    """Computes exact share-weighted executable price to fill `target_notional_usd` against `levels`.

    Returns `None` if resting depth is insufficient to fill `target_notional_usd` (never fabricates depth!).
    """
    if not levels or target_notional_usd <= 0.0:
        return None
    rem_usd = float(target_notional_usd)
    tot_usd = 0.0
    tot_shares = 0.0
    for px, sz in levels:
        if px <= 0.0 or sz <= 0.0:
            continue
        lvl_usd = px * sz
        take_usd = min(rem_usd, lvl_usd)
        take_sh = take_usd / px
        tot_usd += take_usd
        tot_shares += take_sh
        rem_usd -= take_usd
        if rem_usd <= 1e-6:
            break
    if rem_usd > 1e-4 or tot_shares <= 0.0:
        return None
    vwap = tot_usd / tot_shares
    if is_buy_ask and vwap + 1e-9 < levels[0][0]:
        vwap = levels[0][0]
    if (not is_buy_ask) and vwap - 1e-9 > levels[0][0]:
        vwap = levels[0][0]
    return round(vwap, 6)


def summarize_binary_l2_book(
    yes_bids_raw: Sequence[Any],
    yes_asks_raw: Sequence[Any],
    no_bids_raw: Optional[Sequence[Any]] = None,
    no_asks_raw: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    """Computes top-of-book, OBI, microprice, depth, and multi-size VWAPs from observed L2 levels."""
    yb = parse_l2_side(yes_bids_raw, descending=True)
    ya = parse_l2_side(yes_asks_raw, descending=False)
    if no_bids_raw is not None or no_asks_raw is not None:
        nb = parse_l2_side(no_bids_raw or (), descending=True)
        na = parse_l2_side(no_asks_raw or (), descending=False)
    else:
        # Mirror complement on binary CTF orderbook when only YES token book is queried
        nb = sorted([(round(1.0 - px, 6), sz) for px, sz in ya if 0.0 < 1.0 - px < 1.0], key=lambda x: x[0], reverse=True)
        na = sorted([(round(1.0 - px, 6), sz) for px, sz in yb if 0.0 < 1.0 - px < 1.0], key=lambda x: x[0])

    y_bid = yb[0][0] if yb else None
    y_ask = ya[0][0] if ya else None
    n_bid = nb[0][0] if nb else None
    n_ask = na[0][0] if na else None

    y_mid: Optional[float] = None
    y_spread: Optional[float] = None
    y_spread_bps: Optional[float] = None
    n_spread_bps: Optional[float] = None
    obi_l1: Optional[float] = None
    microprice: Optional[float] = None

    if y_bid is not None and y_ask is not None and y_ask >= y_bid:
        y_mid = round(0.5 * (y_bid + y_ask), 6)
        y_spread = round(y_ask - y_bid, 6)
        y_spread_bps = round(y_spread * 10000.0, 2)
        q_b1, q_a1 = yb[0][1], ya[0][1]
        denom = q_b1 + q_a1
        if denom > 0.0:
            obi_l1 = round((q_b1 - q_a1) / denom, 6)
            microprice = round((y_ask * q_b1 + y_bid * q_a1) / denom, 6)

    if n_bid is not None and n_ask is not None and n_ask >= n_bid:
        n_spread_bps = round((n_ask - n_bid) * 10000.0, 2)

    top5_b_sh = sum(sz for _, sz in yb[:5])
    top5_a_sh = sum(sz for _, sz in ya[:5])
    obi_top5 = (
        round((top5_b_sh - top5_a_sh) / (top5_b_sh + top5_a_sh), 6)
        if (top5_b_sh + top5_a_sh) > 0.0
        else None
    )

    l1_b_usd = round(yb[0][0] * yb[0][1], 4) if yb else 0.0
    l1_a_usd = round(ya[0][0] * ya[0][1], 4) if ya else 0.0
    top5_b_usd = round(sum(px * sz for px, sz in yb[:5]), 4)
    top5_a_usd = round(sum(px * sz for px, sz in ya[:5]), 4)
    total_depth_usd = round(
        sum(px * sz for px, sz in yb) + sum((1.0 - px) * sz for px, sz in ya),
        4,
    )

    return {
        "yes_bids": yb[:10],
        "yes_asks": ya[:10],
        "no_bids": nb[:10],
        "no_asks": na[:10],
        "yes_best_bid": y_bid,
        "yes_best_ask": y_ask,
        "no_best_bid": n_bid,
        "no_best_ask": n_ask,
        "yes_mid": y_mid,
        "yes_spread": y_spread,
        "yes_spread_bps": y_spread_bps,
        "no_spread_bps": n_spread_bps,
        "yes_obi_l1": obi_l1,
        "yes_obi_top5": obi_top5,
        "yes_microprice": microprice,
        "l1_yes_bid_usd": l1_b_usd,
        "l1_yes_ask_usd": l1_a_usd,
        "top5_yes_bid_usd": top5_b_usd,
        "top5_yes_ask_usd": top5_a_usd,
        "total_depth_usd": total_depth_usd,
        "vwap_yes_ask_10_usd": compute_book_vwap_for_notional(ya, 10.0, is_buy_ask=True),
        "vwap_yes_ask_25_usd": compute_book_vwap_for_notional(ya, 25.0, is_buy_ask=True),
        "vwap_yes_ask_100_usd": compute_book_vwap_for_notional(ya, 100.0, is_buy_ask=True),
        "vwap_yes_bid_10_usd": compute_book_vwap_for_notional(yb, 10.0, is_buy_ask=False),
        "vwap_yes_bid_25_usd": compute_book_vwap_for_notional(yb, 25.0, is_buy_ask=False),
        "vwap_yes_bid_100_usd": compute_book_vwap_for_notional(yb, 100.0, is_buy_ask=False),
    }


# ---------------------------------------------------------------------------
# SQLite Schema Initialization & Research Query API
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dataset_metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_utc TEXT NOT NULL,
    data_quality_class TEXT NOT NULL CHECK (
        data_quality_class IN (
            'OBSERVED_EXECUTABLE_L2',
            'OBSERVED_TRADE_OR_CLOB_SERIES',
            'EXTERNAL_PUBLIC_OBSERVED',
            'ESTIMATED_SPREAD_ADJUSTED',
            'UNAVAILABLE'
        )
    )
);

CREATE TABLE IF NOT EXISTS resolved_markets (
    market_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    event_slug TEXT NOT NULL,
    market_slug TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    correlation_cluster_id TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    question TEXT NOT NULL,
    outcomes_json TEXT NOT NULL,
    outcome_0_label TEXT NOT NULL,
    outcome_1_label TEXT NOT NULL,
    token_0_id TEXT NOT NULL,
    token_1_id TEXT NOT NULL,
    is_standard_yes_no INTEGER NOT NULL CHECK (is_standard_yes_no IN (0, 1)),
    has_negation_semantics INTEGER NOT NULL CHECK (has_negation_semantics IN (0, 1)),
    semantic_type TEXT NOT NULL,
    neg_risk INTEGER NOT NULL CHECK (neg_risk IN (0, 1)),
    is_other_or_placeholder INTEGER NOT NULL CHECK (is_other_or_placeholder IN (0, 1)),
    resolution_source TEXT NOT NULL,
    created_ts REAL NOT NULL,
    start_ts REAL,
    scheduled_end_ts REAL,
    closed_ts REAL,
    effective_cutoff_ts REAL NOT NULL,
    uma_pre_close_buffer_sec REAL NOT NULL,
    terminal_absorption_ts REAL,
    safe_decision_cutoff_ts REAL NOT NULL,
    resolution_month TEXT NOT NULL,
    duration_hours REAL NOT NULL,
    volume_usd REAL NOT NULL,
    liquidity_final_usd REAL NOT NULL,
    volume_stratum TEXT NOT NULL,
    duration_stratum TEXT NOT NULL,
    fees_enabled INTEGER NOT NULL CHECK (fees_enabled IN (0, 1)),
    fee_type TEXT NOT NULL,
    fee_rate REAL NOT NULL DEFAULT 0.0,
    fee_exponent REAL NOT NULL DEFAULT 1.0,
    maker_rebate_rate REAL NOT NULL DEFAULT 0.0,
    maker_base_fee_bps REAL NOT NULL,
    taker_base_fee_bps REAL NOT NULL,
    tick_size REAL NOT NULL,
    min_order_size REAL NOT NULL,
    uma_resolution_status TEXT NOT NULL,
    winning_index INTEGER NOT NULL CHECK (winning_index IN (-1, 0, 1)),
    winning_label TEXT NOT NULL,
    outcome_0_payout REAL NOT NULL,
    outcome_1_payout REAL NOT NULL,
    is_void_or_50_50 INTEGER NOT NULL CHECK (is_void_or_50_50 IN (0, 1)),
    is_disputed_or_frozen INTEGER NOT NULL CHECK (is_disputed_or_frozen IN (0, 1)),
    price_points_total INTEGER NOT NULL DEFAULT 0,
    price_points_leak_free INTEGER NOT NULL DEFAULT 0,
    trajectory_quality_class TEXT NOT NULL CHECK (
        trajectory_quality_class IN (
            'OBSERVED_EXECUTABLE_L2',
            'OBSERVED_TRADE_OR_CLOB_SERIES',
            'EXTERNAL_PUBLIC_OBSERVED',
            'ESTIMATED_SPREAD_ADJUSTED',
            'UNAVAILABLE'
        )
    ),
    source_origin TEXT NOT NULL,
    data_quality_class TEXT NOT NULL CHECK (
        data_quality_class IN (
            'OBSERVED_EXECUTABLE_L2',
            'OBSERVED_TRADE_OR_CLOB_SERIES',
            'EXTERNAL_PUBLIC_OBSERVED',
            'ESTIMATED_SPREAD_ADJUSTED',
            'UNAVAILABLE'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_rm_cat_cutoff ON resolved_markets(category, safe_decision_cutoff_ts);
CREATE INDEX IF NOT EXISTS idx_rm_cluster ON resolved_markets(correlation_cluster_id);
CREATE INDEX IF NOT EXISTS idx_rm_month ON resolved_markets(resolution_month);
CREATE INDEX IF NOT EXISTS idx_rm_strata ON resolved_markets(volume_stratum, duration_stratum);

CREATE TABLE IF NOT EXISTS price_history (
    market_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    outcome_index INTEGER NOT NULL CHECK (outcome_index IN (0, 1)),
    ts_unix REAL NOT NULL,
    clob_price REAL NOT NULL CHECK (clob_price >= 0.0 AND clob_price <= 1.0),
    complement_clob_price REAL NOT NULL CHECK (complement_clob_price >= 0.0 AND complement_clob_price <= 1.0),
    fidelity_min INTEGER NOT NULL,
    seconds_since_created REAL NOT NULL,
    seconds_to_scheduled_end REAL,
    seconds_to_closed REAL,
    seconds_to_safe_cutoff REAL NOT NULL,
    life_fraction REAL NOT NULL,
    is_after_scheduled_end INTEGER NOT NULL CHECK (is_after_scheduled_end IN (0, 1)),
    is_after_closed INTEGER NOT NULL CHECK (is_after_closed IN (0, 1)),
    is_post_clinch_or_uma_tail INTEGER NOT NULL CHECK (is_post_clinch_or_uma_tail IN (0, 1)),
    is_leak_free_pre_outcome INTEGER NOT NULL CHECK (is_leak_free_pre_outcome IN (0, 1)),
    is_executable_quote INTEGER NOT NULL CHECK (is_executable_quote IN (0, 1)),
    data_quality_class TEXT NOT NULL CHECK (
        data_quality_class IN (
            'OBSERVED_EXECUTABLE_L2',
            'OBSERVED_TRADE_OR_CLOB_SERIES',
            'EXTERNAL_PUBLIC_OBSERVED',
            'ESTIMATED_SPREAD_ADJUSTED',
            'UNAVAILABLE'
        )
    ),
    PRIMARY KEY (market_id, outcome_index, ts_unix),
    FOREIGN KEY (market_id) REFERENCES resolved_markets(market_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ph_market_leakfree ON price_history(market_id, is_leak_free_pre_outcome, ts_unix);
CREATE INDEX IF NOT EXISTS idx_ph_ts ON price_history(ts_unix);

CREATE TABLE IF NOT EXISTS l2_orderbook_snapshots (
    snapshot_uid TEXT PRIMARY KEY,
    ts_unix REAL NOT NULL,
    quote_ts_ms INTEGER NOT NULL,
    market_id TEXT NOT NULL,
    token_yes_id TEXT NOT NULL,
    token_no_id TEXT NOT NULL,
    slug TEXT NOT NULL,
    category TEXT NOT NULL,
    question TEXT NOT NULL,
    fees_enabled INTEGER NOT NULL CHECK (fees_enabled IN (0, 1)),
    fee_rate REAL NOT NULL DEFAULT 0.0,
    taker_base_fee_bps REAL NOT NULL,
    tick_size REAL NOT NULL,
    yes_best_bid REAL,
    yes_best_ask REAL,
    no_best_bid REAL,
    no_best_ask REAL,
    yes_mid REAL,
    yes_spread REAL,
    yes_spread_bps REAL,
    no_spread_bps REAL,
    yes_obi_l1 REAL,
    yes_obi_top5 REAL,
    yes_microprice REAL,
    l1_yes_bid_usd REAL NOT NULL,
    l1_yes_ask_usd REAL NOT NULL,
    top5_yes_bid_usd REAL NOT NULL,
    top5_yes_ask_usd REAL NOT NULL,
    total_depth_usd REAL NOT NULL,
    vwap_yes_ask_10_usd REAL,
    vwap_yes_ask_25_usd REAL,
    vwap_yes_ask_100_usd REAL,
    vwap_yes_bid_10_usd REAL,
    vwap_yes_bid_25_usd REAL,
    vwap_yes_bid_100_usd REAL,
    l2_levels_json TEXT NOT NULL,
    source_origin TEXT NOT NULL,
    is_executable_quote INTEGER NOT NULL CHECK (is_executable_quote = 1),
    data_quality_class TEXT NOT NULL CHECK (data_quality_class = 'OBSERVED_EXECUTABLE_L2')
);

CREATE INDEX IF NOT EXISTS idx_l2_cat_depth ON l2_orderbook_snapshots(category, total_depth_usd);
CREATE INDEX IF NOT EXISTS idx_l2_market_ts ON l2_orderbook_snapshots(market_id, ts_unix);

CREATE TABLE IF NOT EXISTS dual_feed_l2_ticks (
    tick_uid TEXT PRIMARY KEY,
    record_kind TEXT NOT NULL,
    ts_unix REAL NOT NULL,
    asset TEXT NOT NULL,
    horizon TEXT NOT NULL,
    market_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    title TEXT NOT NULL,
    seconds_to_expiry REAL NOT NULL,
    binance_spot REAL NOT NULL,
    binance_futures REAL,
    basis_bps REAL,
    delta_basis_100ms REAL,
    candle_open_spot REAL,
    candle_distance_pct REAL,
    fee_rate_market REAL NOT NULL,
    up_best_bid REAL,
    up_best_ask REAL,
    up_spread REAL,
    up_q_mid REAL,
    up_q_micro REAL,
    up_obi_l1 REAL,
    up_obi_depth REAL,
    up_age_ask_ms REAL,
    up_vwap_ask_20 REAL,
    up_vwap_ask_50 REAL,
    dn_best_bid REAL,
    dn_best_ask REAL,
    dn_spread REAL,
    dn_obi_l1 REAL,
    dn_vwap_ask_20 REAL,
    dn_vwap_ask_50 REAL,
    shock_direction TEXT,
    shock_ofi REAL,
    impulse_500ms_up_ask REAL,
    impulse_1s_up_ask REAL,
    impulse_5s_up_ask REAL,
    impulse_30s_up_ask REAL,
    verified_winner TEXT,
    verified_up_payout REAL,
    l2_raw_json TEXT NOT NULL,
    is_executable_quote INTEGER NOT NULL CHECK (is_executable_quote = 1),
    data_quality_class TEXT NOT NULL CHECK (data_quality_class = 'OBSERVED_EXECUTABLE_L2')
);

CREATE INDEX IF NOT EXISTS idx_df_asset_ts ON dual_feed_l2_ticks(asset, horizon, ts_unix);
CREATE INDEX IF NOT EXISTS idx_df_market ON dual_feed_l2_ticks(market_id);

CREATE TABLE IF NOT EXISTS external_reference_series (
    series_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    interval_label TEXT NOT NULL,
    ts_unix REAL NOT NULL,
    date_utc TEXT NOT NULL,
    value_primary REAL NOT NULL,
    value_secondary REAL,
    value_open REAL,
    value_high REAL,
    value_low REAL,
    volume_raw REAL,
    unit TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    source_origin TEXT NOT NULL,
    data_quality_class TEXT NOT NULL CHECK (data_quality_class = 'EXTERNAL_PUBLIC_OBSERVED'),
    PRIMARY KEY (series_id, ts_unix)
);

CREATE INDEX IF NOT EXISTS idx_ext_domain_subj_ts ON external_reference_series(domain, subject_key, ts_unix);

CREATE TABLE IF NOT EXISTS data_audit_log (
    audit_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    location_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    time_min_utc TEXT,
    time_max_utc TEXT,
    data_quality_class TEXT NOT NULL CHECK (
        data_quality_class IN (
            'OBSERVED_EXECUTABLE_L2',
            'OBSERVED_TRADE_OR_CLOB_SERIES',
            'EXTERNAL_PUBLIC_OBSERVED',
            'ESTIMATED_SPREAD_ADJUSTED',
            'UNAVAILABLE'
        )
    ),
    notes_json TEXT NOT NULL
);
"""


def initialize_research_db(db_path: Path = DEFAULT_HISTORICAL_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def connect_research_db(
    db_path: Path = DEFAULT_HISTORICAL_DB_PATH,
    readonly: bool = True,
) -> sqlite3.Connection:
    """Opens `historical_dataset.sqlite3` in read-only mode by default for downstream agents."""
    p = Path(db_path).resolve()
    if readonly:
        uri = f"file:{p.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


def load_resolved_markets(
    db_path: Path = DEFAULT_HISTORICAL_DB_PATH,
    *,
    categories: Optional[Sequence[str]] = None,
    exclude_disputed_or_void: bool = False,
    exclude_placeholders: bool = True,
    require_leak_free_points: int = 0,
) -> List[Dict[str, Any]]:
    """Loads resolved Polymarket contracts ordered chronologically by `safe_decision_cutoff_ts`."""
    clauses: List[str] = ["1=1"]
    params: List[Any] = []
    if categories:
        placeholders = ",".join("?" for _ in categories)
        clauses.append(f"category IN ({placeholders})")
        params.extend(categories)
    if exclude_disputed_or_void:
        clauses.append("is_void_or_50_50 = 0 AND is_disputed_or_frozen = 0 AND winning_index IN (0, 1)")
    if exclude_placeholders:
        clauses.append("is_other_or_placeholder = 0")
    if require_leak_free_points > 0:
        clauses.append("price_points_leak_free >= ?")
        params.append(int(require_leak_free_points))

    sql = (
        "SELECT * FROM resolved_markets WHERE "
        + " AND ".join(clauses)
        + " ORDER BY safe_decision_cutoff_ts ASC, market_id ASC"
    )
    with connect_research_db(db_path, readonly=True) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def load_leak_free_price_trajectories(
    db_path: Path = DEFAULT_HISTORICAL_DB_PATH,
    *,
    market_ids: Optional[Iterable[str]] = None,
    leak_free_only: bool = True,
) -> Dict[str, List[Dict[str, Any]]]:
    """Loads per-market chronological price trajectories (`is_leak_free_pre_outcome = 1` by default).

    Guarantees `created_ts <= ts_unix < safe_decision_cutoff_ts` and excludes all post-clinch /
    UMA challenge-window tail prints (`RT-01` protection).
    """
    out: Dict[str, List[Dict[str, Any]]] = {}
    clauses = ["1=1"]
    params: List[Any] = []
    if leak_free_only:
        clauses.append("is_leak_free_pre_outcome = 1")
    id_list = list(market_ids) if market_ids is not None else None

    with connect_research_db(db_path, readonly=True) as conn:
        if id_list is not None:
            if not id_list:
                return {}
            # Chunk IN clauses safely below SQLite 999-parameter ceiling
            for i in range(0, len(id_list), 500):
                chunk = id_list[i : i + 500]
                ph = ",".join("?" for _ in chunk)
                q = (
                    f"SELECT * FROM price_history WHERE {' AND '.join(clauses)} "
                    f"AND market_id IN ({ph}) ORDER BY market_id ASC, ts_unix ASC"
                )
                for row in conn.execute(q, [*params, *chunk]):
                    d = dict(row)
                    out.setdefault(d["market_id"], []).append(d)
        else:
            q = f"SELECT * FROM price_history WHERE {' AND '.join(clauses)} ORDER BY market_id ASC, ts_unix ASC"
            for row in conn.execute(q, params):
                d = dict(row)
                out.setdefault(d["market_id"], []).append(d)
    return out


def load_observed_l2_snapshots(
    db_path: Path = DEFAULT_HISTORICAL_DB_PATH,
    *,
    category: Optional[str] = None,
    two_sided_only: bool = True,
) -> List[Dict[str, Any]]:
    """Loads real observed executable Polymarket L2 orderbook snapshots (`OBSERVED_EXECUTABLE_L2`)."""
    clauses = ["data_quality_class = 'OBSERVED_EXECUTABLE_L2'"]
    params: List[Any] = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if two_sided_only:
        clauses.append("yes_best_bid IS NOT NULL AND yes_best_ask IS NOT NULL AND yes_best_ask >= yes_best_bid")
    q = f"SELECT * FROM l2_orderbook_snapshots WHERE {' AND '.join(clauses)} ORDER BY ts_unix ASC"
    with connect_research_db(db_path, readonly=True) as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def load_dual_feed_ticks(
    db_path: Path = DEFAULT_HISTORICAL_DB_PATH,
    *,
    asset: Optional[str] = None,
    record_kind: Optional[str] = None,
    require_verified_resolution: bool = False,
) -> List[Dict[str, Any]]:
    """Loads synchronized Binance Spot/Futures + Polymarket L2 orderbook ticks (`OBSERVED_EXECUTABLE_L2`)."""
    clauses = ["1=1"]
    params: List[Any] = []
    if asset:
        clauses.append("asset = ?")
        params.append(asset.upper())
    if record_kind:
        clauses.append("record_kind = ?")
        params.append(record_kind)
    if require_verified_resolution:
        clauses.append("verified_up_payout IS NOT NULL")
    q = f"SELECT * FROM dual_feed_l2_ticks WHERE {' AND '.join(clauses)} ORDER BY ts_unix ASC"
    with connect_research_db(db_path, readonly=True) as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def load_external_series(
    db_path: Path = DEFAULT_HISTORICAL_DB_PATH,
    *,
    domain: Optional[str] = None,
    subject_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Loads external public reference series (`EXTERNAL_PUBLIC_OBSERVED`)."""
    clauses = ["1=1"]
    params: List[Any] = []
    if domain:
        clauses.append("domain = ?")
        params.append(domain)
    if subject_key:
        clauses.append("subject_key = ?")
        params.append(subject_key)
    q = f"SELECT * FROM external_reference_series WHERE {' AND '.join(clauses)} ORDER BY series_id ASC, ts_unix ASC"
    with connect_research_db(db_path, readonly=True) as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def compute_dataset_summary(db_path: Path = DEFAULT_HISTORICAL_DB_PATH) -> Dict[str, Any]:
    """Computes complete table/category/provenance summary for board handoff and manifest audit."""
    with connect_research_db(db_path, readonly=True) as conn:
        tables = [
            "resolved_markets",
            "price_history",
            "l2_orderbook_snapshots",
            "dual_feed_l2_ticks",
            "external_reference_series",
            "data_audit_log",
        ]
        row_counts = {
            t: int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
            for t in tables
        }
        by_category = {
            r["category"]: {
                "markets": int(r["cnt"]),
                "clusters": int(r["clusters"]),
                "with_leak_free_series": int(r["with_lf"]),
                "fees_enabled_count": int(r["fee_cnt"]),
                "void_or_disputed_count": int(r["vd_cnt"]),
                "low_vol_lt_500_count": int(r["low_vol"]),
            }
            for r in conn.execute(
                """
                SELECT
                    category,
                    COUNT(*) AS cnt,
                    COUNT(DISTINCT correlation_cluster_id) AS clusters,
                    SUM(CASE WHEN price_points_leak_free > 0 THEN 1 ELSE 0 END) AS with_lf,
                    SUM(fees_enabled) AS fee_cnt,
                    SUM(CASE WHEN is_void_or_50_50 = 1 OR is_disputed_or_frozen = 1 THEN 1 ELSE 0 END) AS vd_cnt,
                    SUM(CASE WHEN volume_stratum = 'LOW_LT_500' THEN 1 ELSE 0 END) AS low_vol
                FROM resolved_markets
                GROUP BY category
                ORDER BY cnt DESC
                """
            )
        }
        ph_breakdown = dict(
            conn.execute(
                """
                SELECT
                    COUNT(*) AS total_points,
                    SUM(is_leak_free_pre_outcome) AS leak_free_points,
                    SUM(is_post_clinch_or_uma_tail) AS flagged_tail_points,
                    SUM(is_after_scheduled_end) AS after_scheduled_end_points,
                    SUM(is_after_closed) AS after_closed_points
                FROM price_history
                """
            ).fetchone()
        )
        l2_by_cat = {
            r["category"]: {
                "snapshots": int(r["cnt"]),
                "distinct_markets": int(r["mkts"]),
                "median_approx_spread_bps": round(float(r["avg_sp"] or 0.0), 2),
                "avg_top5_ask_usd": round(float(r["avg_d5"] or 0.0), 2),
            }
            for r in conn.execute(
                """
                SELECT
                    category,
                    COUNT(*) AS cnt,
                    COUNT(DISTINCT market_id) AS mkts,
                    AVG(yes_spread_bps) AS avg_sp,
                    AVG(top5_yes_ask_usd) AS avg_d5
                FROM l2_orderbook_snapshots
                WHERE yes_spread_bps IS NOT NULL
                GROUP BY category
                ORDER BY cnt DESC
                """
            )
        }
        time_span = dict(
            conn.execute(
                """
                SELECT
                    MIN(created_ts) AS min_created_ts,
                    MIN(safe_decision_cutoff_ts) AS min_cutoff_ts,
                    MAX(safe_decision_cutoff_ts) AS max_cutoff_ts
                FROM resolved_markets
                """
            ).fetchone()
        )
        ext_by_domain = {
            r["domain"]: int(r["cnt"])
            for r in conn.execute(
                "SELECT domain, COUNT(*) AS cnt FROM external_reference_series GROUP BY domain"
            )
        }
    return {
        "db_path": str(Path(db_path).resolve()),
        "row_counts": row_counts,
        "resolved_markets_by_category": by_category,
        "price_history_leakage_guard_stats": ph_breakdown,
        "l2_snapshots_by_category": l2_by_cat,
        "external_series_by_domain": ext_by_domain,
        "resolved_time_span_utc": {
            "min_created_utc": format_utc_iso(time_span.get("min_created_ts")),
            "min_cutoff_utc": format_utc_iso(time_span.get("min_cutoff_ts")),
            "max_cutoff_utc": format_utc_iso(time_span.get("max_cutoff_ts")),
        },
    }

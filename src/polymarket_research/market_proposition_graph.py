"""
Unified Market Proposition & Contract Relationship Graph
(`src/polymarket_research/market_proposition_graph.py`).

Implements Section 7 of DOMINUS — RISKLESS FULL THROTTLE:
  1. Canonical Graph Entities:
     - `EventNode`, `MarketNode`, `OutcomeInstrumentNode`, `ResolutionSpec`,
       `PropositionSpec`, and `PortfolioHoldingNode` (strictly quarantining frozen
       UMA-disputed `KMIA` positions `6707503` & `6707502` per `D-001`).
  2. Four Strict Edge Provenance Tiers (`EdgeType`):
     - `OFFICIAL_CONTRACTUAL`: Binary CTF complement (`YES + NO == $1.00` on identical
       `condition_id`) and verified closed-slate `NegRiskAdapter` conversion groups.
     - `VERIFIED_MATHEMATICAL`: Proven numerical threshold dominance (`S >= K2 => S >= K1`),
       contiguous interval partition cover, temporal deadline containment (`T1 <= T2`),
       and state-identical duplicate markets sharing verified oracle, settlement basis,
       timezone, overtime rules, and cancel/void rules.
     - `SUSPECTED_REQUIRES_PROOF`: Candidate propositions with rule divergence
       (`TOUCH_ANYTIME` vs `CLOSE_AT_CUTOFF`, `REGULATION_90M` vs `FULL_GAME_INCL_OT`,
       timezone mismatch, missing `rules_hash`, or augmented-NegRisk unnamed placeholder /
       missing `Other`).
     - `STATISTICAL_CORRELATION_ONLY`: Cross-oracle (`Chainlink` vs `Binance`), cross-date
       weather station, or thematic correlations ineligible for `CLASS_A` / `CLASS_B`.
  3. Sub-Quadratic Bucket Indexing, Connected-Component Pruning & Incremental Updates:
     - Avoids blind `O(N^2)` all-pairs scans via inverted bucket indexes (`condition_id`,
       `neg_risk_market_id`, `event_id`, `subject_key`, `temporal_stem_key`) and `O(m log m)`
       transitive ladder chains.
     - Supports incremental market/event upserts & removals returning exact dirty market and
       component IDs for fast-cycle re-evaluation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from src.polymarket_research.universal_arb_verifier import (
    DEFAULT_MIN_ORDER_SHARES,
    FROZEN_DISPUTED_MARKET_IDS,
    FROZEN_DISPUTED_TRADE_SUBSTRINGS,
    normalize_fee_rate,
)


class EdgeType(str, Enum):
    """Four mandatory relationship provenance tiers (`Section 7`)."""

    OFFICIAL_CONTRACTUAL = "OFFICIAL_CONTRACTUAL"
    VERIFIED_MATHEMATICAL = "VERIFIED_MATHEMATICAL"
    SUSPECTED_REQUIRES_PROOF = "SUSPECTED_REQUIRES_PROOF"
    STATISTICAL_CORRELATION_ONLY = "STATISTICAL_CORRELATION_ONLY"


class RelationKind(str, Enum):
    """Specific algebraic / contractual relationship carried by an edge."""

    BINARY_CTF_COMPLEMENT = "BINARY_CTF_COMPLEMENT"
    NEGRISK_CLOSED_SLATE = "NEGRISK_CLOSED_SLATE"
    NEGRISK_AUGMENTED_OR_INCOMPLETE = "NEGRISK_AUGMENTED_OR_INCOMPLETE"
    IMPLIES = "IMPLIES"                      # source YES => target YES (`NO_src + YES_dst >= $1`)
    EQUIVALENT = "EQUIVALENT"                # source YES <=> target YES
    MUTUALLY_EXCLUSIVE = "MUTUALLY_EXCLUSIVE"  # source YES perp target YES (`NO_src + NO_dst >= $1`)
    INTERVAL_COVER = "INTERVAL_COVER"        # bracket child of threshold/union cover
    PORTFOLIO_INVENTORY_LINK = "PORTFOLIO_INVENTORY_LINK"
    CORRELATED_SUBJECT = "CORRELATED_SUBJECT"


# ---------------------------------------------------------------------------
# Regex & Rule-Signature Extraction Helpers
# ---------------------------------------------------------------------------

_OTHER_LABEL_RE = re.compile(
    r"^\s*(?:other|any\s+other(?:\s+\w+)*|all\s+other(?:\s+\w+)*|field|none\s+of\s+the\s+above|someone\s+else)\s*$",
    re.IGNORECASE,
)
_PLACEHOLDER_LABEL_RE = re.compile(
    r"(?:\bplaceholder\b|\bunnamed\b|^person\s+[a-z0-9]+$|^player\s+[a-z0-9]+$|^candidate\s+[a-z0-9]+$|^option\s+\d+$|^tba$|^tbd$)",
    re.IGNORECASE,
)
_CHAINLINK_STREAM_RE = re.compile(r"https://data\.chain\.link/streams/([a-z0-9\-]+)", re.IGNORECASE)
_ICAO_STATION_RE = re.compile(r"\b(K[A-Z]{3}|EGLL|LFPG|EDDF|RJTT|RKSI|CYYZ|SBGR|YSSY)\b")
_TOUCH_ANYTIME_Q_RE = re.compile(
    r"\b(?:touch(?:es)?|hit(?:s)?|reach(?:es)?|at\s+any\s+(?:point|time)|for\s+any\s+(?:date|day|time)|dip(?:s)?\s+to|drop(?:s)?\s+to|fall(?:s)?\s+to|plunge(?:s)?\s+to|climb(?:s)?\s+to|surge(?:s)?\s+to|trade\s+at\s+or\s+(?:above|below)|all[\-\s]time\s+high)\b",
    re.IGNORECASE,
)
_TOUCH_ANYTIME_DESC_RE = re.compile(
    r"\b(?:touches\s+or\s+hits|at\s+any\s+(?:point|time)|for\s+any\s+(?:date|day|time)|between\s+market\s+creation\s+and|trade\s+at\s+or\s+(?:above|below))\b",
    re.IGNORECASE,
)
_CLOSE_AT_CUTOFF_RE = re.compile(
    r"\b(?:close\s+(?:above|below|at)|closing\s+price|price\s+of\s+\S+\s+(?:at|on)|be\s+(?:above|below|greater|less)\s+.*\b(?:at|on)\b|up\s+or\s+down)\b",
    re.IGNORECASE,
)
_REGULATION_90M_RE = re.compile(
    r"\b(?:regular\s+time|regulation\s+(?:time|only)|90\s+minutes(?:\s+only)?|excludes?\s+overtime|excluding\s+extra\s+time)\b",
    re.IGNORECASE,
)
_OVERTIME_INCLUDED_RE = re.compile(
    r"\b(?:includ(?:es?|ing)\s+(?:overtime|extra\s+time|shootout)|incl\.?\s*ot|to\s+advance|qualify|win\s+the\s+(?:series|trophy|cup|championship|title))\b",
    re.IGNORECASE,
)
_CRYPTO_TICKER_RE = re.compile(
    r"\b(bitcoin|btc|ethereum|eth|solana|sol|xrp|bnb|dogecoin|doge|hyperliquid|hype|zcash|zec|gold|xau|silver|xag)\b",
    re.IGNORECASE,
)
_CRYPTO_CANON_MAP: Dict[str, str] = {
    "bitcoin": "BTC",
    "btc": "BTC",
    "ethereum": "ETH",
    "eth": "ETH",
    "solana": "SOL",
    "sol": "SOL",
    "xrp": "XRP",
    "bnb": "BNB",
    "dogecoin": "DOGE",
    "doge": "DOGE",
    "hyperliquid": "HYPE",
    "hype": "HYPE",
    "zcash": "ZEC",
    "zec": "ZEC",
    "gold": "XAU",
    "xau": "XAU",
    "silver": "XAG",
    "xag": "XAG",
}

_OVER_UNDER_RE = re.compile(
    r"\b(?:over\s*/\s*under|o\s*/\s*u)\b\s*:?\s*(\$?\s*[+\-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°?[fc]|%|bps|pts|points|goals|runs|kills|maps|games|rounds|sets|corners|cards|aces)?",
    re.IGNORECASE,
)
_RANGE_NUM_RE = re.compile(
    r"(?:between\s+(\$?\s*[+\-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°?[fc]|%|bps)?\s*(?:and|to|[-–])\s*(\$?\s*[+\-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°?[fc]|%|bps)?|(\$?\s*[+\-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°[fc]|%|bps)\s*(?:to|[-–])\s*(\$?\s*[+\-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°?[fc]|%|bps)?)",
    re.IGNORECASE,
)
_THRESHOLD_GE_RE = re.compile(
    r"(?:\b(at\s+or\s+above|above|over|exceeds?|exceed|at\s+least|greater\s+than\s+or\s+equal\s+to|greater\s+than|more\s+than|higher\s+than)\s+|(>=|>)\s*)(\$?\s*[+\-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°?[fc]|%|bps|pts|points|goals|runs|kills|maps|games|rounds|sets|corners|cards|aces)?",
    re.IGNORECASE,
)
_THRESHOLD_LE_RE = re.compile(
    r"(?:\b(at\s+or\s+below|below|under|at\s+most|less\s+than\s+or\s+equal\s+to|less\s+than|fewer\s+than|lower\s+than)\s+|(<=|<)\s*)(\$?\s*[+\-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°?[fc]|%|bps|pts|points|goals|runs|kills|maps|games|rounds|sets|corners|cards|aces)?",
    re.IGNORECASE,
)
_PATH_BARRIER_NUM_RE = re.compile(
    r"\b(hit(?:s)?|reach(?:es)?|touch(?:es)?|dip(?:s)?\s+to|drop(?:s)?\s+to|fall(?:s)?\s+to|plunge(?:s)?\s+to|climb(?:s)?\s+to|surge(?:s)?\s+to)\s+(\$?\s*[+\-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°?[fc]|%|bps|pts|points|goals|runs|kills|maps|games|rounds|sets|corners|cards|aces)?",
    re.IGNORECASE,
)
_DESC_CONTRADICTS_GE_RE = re.compile(
    r"\b(?:equal\s+to\s+or\s+below|at\s+or\s+below|less\s+than\s+or\s+equal\s+to|is\s+(?:less|lower)\s+than|is\s+below)\s+the\s+(?:listed|specified|stated|target)\b",
    re.IGNORECASE,
)
_DESC_CONTRADICTS_LE_RE = re.compile(
    r"\b(?:equal\s+to\s+or\s+above|at\s+or\s+above|greater\s+than\s+or\s+equal\s+to|is\s+(?:greater|higher|more)\s+than|is\s+above)\s+the\s+(?:listed|specified|stated|target)\b",
    re.IGNORECASE,
)
_NEGATION_RE = re.compile(
    r"(?:\b(?:not|never|neither|nor|without|fail(?:s|ed|ing)?\s+to|refuse(?:s|d)?\s+to|avoid(?:s|ed|ing)?|prevent(?:s|ed)?)\b|\b[a-z]+n['’]t\b|\bno\s+(?!later\s+than\b|more\s+than\b|less\s+than\b|fewer\s+than\b)[a-z]+)",
    re.IGNORECASE,
)
_STRICT_GE_OPS: frozenset[str] = frozenset(
    {"above", "over", "exceed", "exceeds", "greater than", "more than", "higher than", ">"}
)
_STRICT_LE_OPS: frozenset[str] = frozenset(
    {"below", "under", "less than", "fewer than", "lower than", "<"}
)
_MONTH_MAP: Dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_DEADLINE_BY_DATE_RE = re.compile(
    r"\b(by|before|on\s+or\s+before)\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(20\d{2}))?",
    re.IGNORECASE,
)
_NUMBERED_SUB_PERIOD_RE = re.compile(
    r"\b(map|game|set|match|round|inning)\s*#?\s*(\d+)\b",
    re.IGNORECASE,
)
_ORDINAL_TO_INT: Dict[str, int] = {
    "1": 1, "1st": 1, "first": 1,
    "2": 2, "2nd": 2, "second": 2,
    "3": 3, "3rd": 3, "third": 3,
    "4": 4, "4th": 4, "fourth": 4,
}


def _extract_sub_period_scope_key(text: str) -> str:
    """
    Extracts canonical sub-period / map / game / set / half / quarter / period / inning
    qualifiers so `Map 3` and `Map 2` (or `1st Half` and `Full Game`) never share a ladder.
    """
    t = str(text or "").strip().lower()
    if not t:
        return ""
    tokens: Set[str] = set()
    for m_sp in _NUMBERED_SUB_PERIOD_RE.finditer(t):
        tokens.add(f"{m_sp.group(1).upper()}_{int(m_sp.group(2))}")
    if re.search(r"\b(?:(?:1st|first)\s+(?:5|five)\s+innings|f5)\b", t):
        tokens.add("FIRST_5_INNINGS")
    if re.search(r"\b(?:(?:1st|first)\s+half|1h)\b", t):
        tokens.add("HALF_1")
    if re.search(r"\b(?:(?:2nd|second)\s+half|2h)\b", t):
        tokens.add("HALF_2")
    for m_q in re.finditer(r"\b(?:(1st|first|2nd|second|3rd|third|4th|fourth)\s+quarter|q([1-4]))\b", t):
        ord_key = (m_q.group(1) or m_q.group(2) or "").lower()
        if ord_key in _ORDINAL_TO_INT:
            tokens.add(f"QTR_{_ORDINAL_TO_INT[ord_key]}")
    for m_p in re.finditer(r"\b(?:(1st|first|2nd|second|3rd|third)\s+period|p([1-3]))\b", t):
        ord_key = (m_p.group(1) or m_p.group(2) or "").lower()
        if ord_key in _ORDINAL_TO_INT:
            tokens.add(f"PERIOD_{_ORDINAL_TO_INT[ord_key]}")
    return "|".join(sorted(tokens))


def _classify_outcome_polarity_mode(outcome_labels: Sequence[str]) -> str:
    """
    Classifies `outcomes` token polarity so `['Over', 'Under']` (`toks[0] == Over`),
    `['Under', 'Over']` (`toks[0] == Under`), inverted `['No', 'Yes']`, and team/player
    outcome pairs are never conflated with standard `['Yes', 'No']`.
    """
    norm = [re.sub(r"\s+", " ", str(x or "").strip().lower()) for x in (outcome_labels or ()) if str(x or "").strip()]
    if not norm:
        return "YES_NO"
    if len(norm) >= 2:
        o0, o1 = norm[0], norm[1]
        if o0 in ("yes", "true") and o1 in ("no", "false"):
            return "YES_NO"
        if o0 in ("no", "false") and o1 in ("yes", "true"):
            return "INVERTED_NO_YES"
        if (o0 == "over" or o0.startswith("over ")) and (o1 == "under" or o1.startswith("under ")):
            return "OVER_UNDER"
        if (o0 == "under" or o0.startswith("under ")) and (o1 == "over" or o1.startswith("over ")):
            return "UNDER_OVER"
        return f"CUSTOM:{o0}|{o1}"
    return f"SINGLE:{norm[0]}"


def _normalize_metric_stem_key(question: str, matched_span_in_q: Optional[Tuple[int, int]]) -> str:
    """
    Normalizes a numerical question stem with the strike/range/O-U clause replaced by `<strike>`
    so unrelated metrics on the same event/match (e.g. `Map 2` vs `Map 3`, `Team A Points` vs
    `Team B Points`, `Kills` vs `Rounds`, `High Temp` vs `Low Temp`) never share a cohort ladder.
    """
    q = str(question or "")
    if matched_span_in_q is not None:
        s_i, e_i = matched_span_in_q
        raw_stem = q[:s_i] + " __strike__ " + q[e_i:]
    else:
        raw_stem = q + " __strike__ "
    low = raw_stem.lower()
    for syn, canon in _CRYPTO_CANON_MAP.items():
        low = re.sub(rf"\b{re.escape(syn)}\b", canon.lower(), low)
    low = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", low)
    low = re.sub(r"[^a-z0-9_\s]", " ", low)
    low = re.sub(r"\bbe\s+__strike__\b", "__strike__", low)
    low = re.sub(r"\s+", " ", low).strip()
    return low


def _compute_deadline_utc_ts(yr: int, mo: int, dy: int, prep: str) -> Optional[int]:
    if not (1 <= mo <= 12 and 1 <= dy <= 31):
        return None
    try:
        if prep == "before":
            return int(datetime(yr, mo, dy, 0, 0, 0, tzinfo=timezone.utc).timestamp()) - 1
        return int(datetime(yr, mo, dy, 23, 59, 59, tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None


def _normalize_rules_hash(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", str(text or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    if not cleaned:
        return ""
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:24]


def _parse_iso_or_unix_ts(raw: Any) -> Optional[int]:
    if raw in (None, ""):
        return None
    if isinstance(raw, (int, float)):
        v = float(raw)
        if not math.isfinite(v) or v <= 0:
            return None
        return int(v / 1000.0) if v > 1e11 else int(v)
    s = str(raw).strip()
    if not s:
        return None
    if s.isdigit():
        v_i = int(s)
        return int(v_i / 1000) if v_i > 10**11 else v_i
    try:
        iso = s.replace(" ", "T")
        if iso.endswith("+00"):
            iso += ":00"
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


_SPORT_STAT_UNIT_MAP: Dict[str, str] = {
    "pts": "PTS",
    "points": "PTS",
    "goals": "GOALS",
    "runs": "RUNS",
    "kills": "KILLS",
    "maps": "MAPS",
    "games": "GAMES",
    "rounds": "ROUNDS",
    "sets": "SETS",
    "corners": "CORNERS",
    "cards": "CARDS",
    "aces": "ACES",
}


def _scale_num(num_str: str, suffix: str, has_dollar: bool) -> Tuple[float, str]:
    clean = num_str.replace("$", "").replace(",", "").strip()
    val = float(clean)
    suf = (suffix or "").strip().lower()
    mult = 1.0
    unit = "USD" if has_dollar or "$" in num_str else ""
    if suf == "k":
        mult = 1e3
    elif suf == "m":
        mult = 1e6
    elif suf == "b":
        mult = 1e9
    elif suf == "t":
        mult = 1e12
    elif suf in ("°f", "f"):
        unit = "F"
    elif suf in ("°c", "c"):
        unit = "C"
    elif suf == "%":
        unit = "PCT"
    elif suf == "bps":
        unit = "BPS"
    elif suf in _SPORT_STAT_UNIT_MAP:
        unit = _SPORT_STAT_UNIT_MAP[suf]
    return val * mult, unit


def _extract_explicit_timezone_token(text: str) -> Optional[str]:
    t = str(text or "")
    if not t.strip():
        return None
    if re.search(r"\b(?:UTC|GMT)\b", t):
        return "UTC"
    if re.search(r"\b(?:ET|EST|EDT|Eastern\s+Time|New\s+York)\b", t, re.IGNORECASE):
        return "America/New_York"
    if re.search(r"\b(?:CT|CST|CDT|Central\s+Time|Chicago)\b", t, re.IGNORECASE):
        return "America/Chicago"
    if re.search(r"\b(?:PT|PST|PDT|Pacific\s+Time|Los\s+Angeles)\b", t, re.IGNORECASE):
        return "America/Los_Angeles"
    return None


def _extract_timezone_token(text: str) -> str:
    return _extract_explicit_timezone_token(text) or "UTC"


# ---------------------------------------------------------------------------
# Graph Node & Edge Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolutionSpec:
    """Normalized contractual resolution metadata for rule-compatibility proofs."""

    authority: str = "UMA_OPTIMISTIC_ORACLE"
    oracle_source_id: str = ""
    cutoff_ts: Optional[int] = None
    timezone_name: str = "UTC"
    settlement_basis: str = "EVENT_OCCURRENCE"  # CLOSE_AT_CUTOFF | TOUCH_ANYTIME | TWAP_60S | REGULATION_90M | FULL_GAME_INCL_OT | DAILY_METAR | EVENT_OCCURRENCE
    cancel_void_rule: str = "50_50"             # 50_50 | NEGRISK_DESIGNATED | VOID_REFUND
    rules_hash: str = ""
    includes_overtime: Optional[bool] = None

    def check_compatibility(
        self,
        other: "ResolutionSpec",
        *,
        allow_ordered_cutoffs: bool = False,
    ) -> Tuple[bool, Tuple[str, ...]]:
        """
        Deterministically checks whether two contracts share compatible resolution semantics.
        Returns `(is_compatible, mismatch_codes)`.
        """
        issues: List[str] = []
        if self.authority != other.authority:
            issues.append(f"AUTHORITY_MISMATCH:{self.authority}!={other.authority}")
        if (self.oracle_source_id or other.oracle_source_id) and self.oracle_source_id != other.oracle_source_id:
            issues.append(f"ORACLE_SOURCE_MISMATCH:{self.oracle_source_id}!={other.oracle_source_id}")
        if self.settlement_basis != other.settlement_basis:
            issues.append(f"SETTLEMENT_BASIS_MISMATCH:{self.settlement_basis}!={other.settlement_basis}")
        if self.includes_overtime is not None and other.includes_overtime is not None:
            if self.includes_overtime != other.includes_overtime:
                issues.append("SPORTS_REGULATION_VS_OVERTIME_MISMATCH")
        if self.timezone_name.startswith("CONFLICT:") or other.timezone_name.startswith("CONFLICT:"):
            issues.append(f"INTERNAL_TIMEZONE_CONFLICT:{self.timezone_name}|{other.timezone_name}")
        elif self.timezone_name != other.timezone_name:
            issues.append(f"TIMEZONE_MISMATCH:{self.timezone_name}!={other.timezone_name}")
        if self.cancel_void_rule != other.cancel_void_rule:
            issues.append(f"CANCEL_VOID_RULE_MISMATCH:{self.cancel_void_rule}!={other.cancel_void_rule}")
        if not allow_ordered_cutoffs:
            if self.cutoff_ts is not None and other.cutoff_ts is not None and abs(self.cutoff_ts - other.cutoff_ts) > 60:
                issues.append(f"CUTOFF_TIMESTAMP_MISMATCH:{self.cutoff_ts}!={other.cutoff_ts}")
        if not self.rules_hash or not other.rules_hash:
            issues.append("MISSING_RESOLUTION_RULES_TEXT")
        return (len(issues) == 0, tuple(issues))


@dataclass(frozen=True)
class PropositionSpec:
    """Extracted formal proposition signature for sub-quadratic bucketing & logical matching."""

    subject_key: str = ""                     # e.g., "CRYPTO:BTC", "WX:KMIA:2026-11-11", "MATCH:ARSENAL_VS_CHELSEA"
    temporal_stem_key: str = ""               # Question stem with deadline date stripped for Family E matching
    duplicate_stem_key: str = ""              # Canonical normalized question stem for Family I matching
    predicate_type: str = "BINARY"            # THRESHOLD_GE | THRESHOLD_LE | RANGE_BRACKET | DEADLINE_BY | OUTCOME_SLATE | BINARY
    threshold_low: Optional[float] = None
    threshold_high: Optional[float] = None
    is_strict_low: bool = False               # True for `S > K`, False for `S >= K` or `[L, U]`
    is_strict_high: bool = False              # True for `S < K`, False for `S <= K` or `[L, U]`
    is_negated: bool = False                  # True when `not` / `n't` / `never` / `fail to` / `without` negates predicate
    unit: str = ""
    deadline_ts: Optional[int] = None
    scope_key: str = ""                       # Sub-period qualifier (`MAP_2` vs `MAP_3`, `HALF_1` vs `HALF_2`, etc.)
    metric_stem_key: str = ""                 # Question stem with numeric strike/range replaced by `__strike__`
    outcome_polarity_mode: str = "YES_NO"     # YES_NO | OVER_UNDER | UNDER_OVER | INVERTED_NO_YES | AMBIGUOUS_OU | CUSTOM:...
    deadline_year_ambiguous: bool = False     # True when yearless `by <Month> <Day>` lacks matching `endDate`
    is_path_dependent_barrier: bool = False   # True for `hit`/`reach`/`touch`/`dip to`/`drop to` or `TOUCH_ANYTIME` barriers
    has_creation_relative_window: bool = False  # True when rules anchor start window to `"market creation"`


@dataclass(frozen=True)
class OutcomeInstrumentNode:
    token_id: str
    market_id: str
    event_id: str
    condition_id: str
    outcome_label: str
    polarity: str  # "YES" | "NO"
    question_index: Optional[int] = None
    fee_rate_bps: float = 0.0
    tick_size: float = 0.01
    min_order_size: float = DEFAULT_MIN_ORDER_SHARES
    is_placeholder: bool = False
    is_other: bool = False
    enable_order_book: bool = True


@dataclass(frozen=True)
class MarketNode:
    market_id: str
    event_id: str
    condition_id: str
    slug: str
    question: str
    group_item_title: str = ""
    category: str = "other"
    yes_token_id: str = ""
    no_token_id: str = ""
    instrument_ids: Tuple[str, ...] = ()
    outcome_labels: Tuple[str, ...] = ()
    enable_order_book: bool = True
    active: bool = True
    closed: bool = False
    archived: bool = False
    neg_risk: bool = False
    neg_risk_market_id: str = ""
    neg_risk_augmented: bool = False
    uma_resolution_status: str = ""
    fee_rate_bps: float = 0.0
    tick_size: float = 0.01
    min_order_size: float = DEFAULT_MIN_ORDER_SHARES
    is_placeholder: bool = False
    is_other: bool = False
    question_index: Optional[int] = None
    resolution: ResolutionSpec = field(default_factory=ResolutionSpec)
    proposition: PropositionSpec = field(default_factory=PropositionSpec)


@dataclass(frozen=True)
class EventNode:
    event_id: str
    slug: str
    title: str
    category: str = "other"
    neg_risk: bool = False
    neg_risk_market_id: str = ""
    neg_risk_augmented: bool = False
    enable_neg_risk_other: bool = False
    market_ids: Tuple[str, ...] = ()
    raw_market_count: int = 0


@dataclass(frozen=True)
class PortfolioHoldingNode:
    """Wallet CTF holding attached to the graph (`D-001` frozen `KMIA` holdings quarantined)."""

    holding_id: str
    token_id: str
    market_id: str
    condition_id: str
    side: str
    shares: float
    cost_basis_usd: float
    mark_bid_px: float = 0.0
    uma_resolution_status: str = ""
    is_frozen_disputed: bool = False
    eligible_for_recycling: bool = True


@dataclass(frozen=True)
class PropositionEdge:
    """Typed directed or symmetric edge between markets / instruments in the proposition graph."""

    edge_id: str
    edge_type: EdgeType
    relation_kind: RelationKind
    source_market_id: str
    target_market_id: str
    source_token_id: str = ""
    target_token_id: str = ""
    group_key: str = ""
    disqualifiers: Tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class ConnectedMarketComponent:
    """Pruned connected component of markets & instruments for localized solver/detector runs."""

    component_id: str
    market_ids: Tuple[str, ...]
    instrument_ids: Tuple[str, ...]
    event_ids: Tuple[str, ...]
    edge_types_present: Tuple[str, ...]
    edges: Tuple[PropositionEdge, ...]
    recyclable_holding_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphUpdateDelta:
    upserted_market_ids: Tuple[str, ...]
    removed_market_ids: Tuple[str, ...]
    dirty_market_ids: Tuple[str, ...]
    dirty_group_keys: Tuple[str, ...]
    edges_rebuilt: int


# ---------------------------------------------------------------------------
# Unified Market Proposition Graph Engine
# ---------------------------------------------------------------------------


class MarketPropositionGraph:
    """
    Indexed, incrementally-updatable proposition & contract relationship graph (`Section 7`).
    """

    def __init__(self) -> None:
        self.events: Dict[str, EventNode] = {}
        self.markets: Dict[str, MarketNode] = {}
        self.instruments: Dict[str, OutcomeInstrumentNode] = {}
        self.holdings: Dict[str, PortfolioHoldingNode] = {}
        self.edges: Dict[str, PropositionEdge] = {}

        # Sub-quadratic inverted indexes (never scan O(N^2) unrelated pairs!)
        self._markets_by_event: Dict[str, Set[str]] = {}
        self._markets_by_condition: Dict[str, Set[str]] = {}
        self._markets_by_negrisk_id: Dict[str, Set[str]] = {}
        self._markets_by_subject: Dict[str, Set[str]] = {}
        self._markets_by_temporal_stem: Dict[str, Set[str]] = {}
        self._markets_by_duplicate_stem: Dict[str, Set[str]] = {}
        self._edges_by_market: Dict[str, Set[str]] = {}
        self._edges_by_group: Dict[str, Set[str]] = {}

    # -----------------------------------------------------------------------
    # Parsing & Extraction from Raw Gamma / Normalized Discovery Objects
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_attr_or_key(obj: Any, *keys: str, default: Any = None) -> Any:
        for k in keys:
            if isinstance(obj, Mapping) and k in obj and obj[k] is not None:
                return obj[k]
            if hasattr(obj, k):
                val = getattr(obj, k)
                if val is not None:
                    return val
        return default

    @classmethod
    def extract_resolution_and_proposition(
        cls,
        *,
        question: str,
        description: str = "",
        slug: str = "",
        group_item_title: str = "",
        category: str = "",
        end_ts: Optional[int] = None,
        neg_risk: bool = False,
        event_id: str = "",
        outcome_labels: Sequence[str] = (),
        rules_hash_override: str = "",
        ref_year: int = 2026,
    ) -> Tuple[ResolutionSpec, PropositionSpec]:
        q_str = str(question or "").strip()
        d_str = str(description or "").strip()
        s_str = str(slug or "").strip()
        g_str = str(group_item_title or "").strip()
        blob = f"{q_str} {g_str} {d_str}"
        blob_low = blob.lower()

        # 1. Authority & Oracle Source ID
        authority = "UMA_OPTIMISTIC_ORACLE"
        oracle_src = ""
        m_cl = _CHAINLINK_STREAM_RE.search(d_str)
        if m_cl:
            authority = "CHAINLINK_DATA_STREAMS"
            oracle_src = f"chainlink:{m_cl.group(1).lower()}"
        elif "chainlink" in blob_low:
            authority = "CHAINLINK_DATA_STREAMS"
            oracle_src = "chainlink:unspecified"
        elif "pyth.network" in blob_low or "pyth network" in blob_low:
            authority = "PYTH_ORACLE"
            oracle_src = "pyth"
        elif "binance" in blob_low:
            authority = "EXCHANGE_SPOT_CANDLE"
            oracle_src = "binance"
        elif "coinbase" in blob_low:
            authority = "EXCHANGE_SPOT_CANDLE"
            oracle_src = "coinbase"
        elif "wunderground" in blob_low or "weather underground" in blob_low or _ICAO_STATION_RE.search(blob):
            m_icao = _ICAO_STATION_RE.search(blob)
            if m_icao and ("temp" in blob_low or "°" in blob_low or "weather" in blob_low or "high" in blob_low):
                authority = "WEATHER_STATION_METAR"
                oracle_src = f"icao:{m_icao.group(1).upper()}"

        # 2. Settlement Basis & Overtime Flag
        includes_ot: Optional[bool] = None
        if _TOUCH_ANYTIME_Q_RE.search(f"{q_str} {g_str}") or (
            _TOUCH_ANYTIME_DESC_RE.search(d_str) and not _CLOSE_AT_CUTOFF_RE.search(q_str)
        ):
            basis = "TOUCH_ANYTIME"
        elif "twap" in blob_low or "60-second" in blob_low:
            basis = "TWAP_60S"
        elif _REGULATION_90M_RE.search(blob):
            basis = "REGULATION_90M"
            includes_ot = False
        elif _OVERTIME_INCLUDED_RE.search(blob):
            basis = "FULL_GAME_INCL_OT"
            includes_ot = True
        elif authority == "WEATHER_STATION_METAR":
            basis = "DAILY_METAR_EXTREMA"
        elif _CLOSE_AT_CUTOFF_RE.search(blob):
            basis = "CLOSE_AT_CUTOFF"
        else:
            basis = "EVENT_OCCURRENCE"

        tz_d = _extract_explicit_timezone_token(d_str)
        tz_q = _extract_explicit_timezone_token(q_str)
        if tz_d is not None and tz_q is not None and tz_d != tz_q:
            tz_name = f"CONFLICT:{tz_q}_VS_{tz_d}"
        else:
            tz_name = tz_d or tz_q or "UTC"
        cancel_rule = "NEGRISK_DESIGNATED" if neg_risk else "50_50"
        if "void" in blob_low and "refund" in blob_low:
            cancel_rule = "VOID_REFUND"
        rules_h = str(rules_hash_override or "").strip() if (not d_str and rules_hash_override) else _normalize_rules_hash(d_str)

        res_spec = ResolutionSpec(
            authority=authority,
            oracle_source_id=oracle_src,
            cutoff_ts=end_ts,
            timezone_name=tz_name,
            settlement_basis=basis,
            cancel_void_rule=cancel_rule,
            rules_hash=rules_h,
            includes_overtime=includes_ot,
        )

        # 3. Sub-Period Scope Qualifier (`MAP_2` vs `MAP_3`, `HALF_1` vs `HALF_2`, etc.) & Canonical Subject Key
        scope_key = _extract_sub_period_scope_key(f"{q_str} {g_str}")
        polarity_mode = _classify_outcome_polarity_mode(outcome_labels)

        subj = ""
        m_cry = _CRYPTO_TICKER_RE.search(f"{q_str} {s_str}")
        if authority.startswith("WEATHER_STATION") and oracle_src:
            day_bucket = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d") if end_ts else "NODATE"
            subj = f"WX:{oracle_src}:{day_bucket}"
        elif m_cry and (
            authority in ("CHAINLINK_DATA_STREAMS", "PYTH_ORACLE", "EXCHANGE_SPOT_CANDLE")
            or any(k in blob_low for k in ("price", "$", "up or down", "above", "below", "hit", "reach", "touch", "dip"))
        ):
            tkr = _CRYPTO_CANON_MAP.get(m_cry.group(1).lower(), m_cry.group(1).upper())
            subj = f"CRYPTO:{tkr}"
            if not oracle_src:
                oracle_src = f"crypto:{tkr.lower()}"
        elif " vs " in q_str.lower() or " vs. " in q_str.lower():
            parts = re.split(r"\s+vs\.?\s+", re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", q_str), maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                t1 = re.sub(r"[^a-z0-9]+", "_", parts[0].strip().lower()).strip("_")[-24:]
                t2 = re.sub(r"[^a-z0-9]+", "_", re.split(r"[:\?\|\-]", parts[1])[0].strip().lower()).strip("_")[:24]
                if t1 and t2:
                    pair = "_VS_".join(sorted((t1.upper(), t2.upper())))
                    day_b = (end_ts // 86400) if end_ts else 0
                    subj = f"MATCH:{pair}:{day_b}" + (f":{scope_key}" if scope_key else "")

        # 4. Duplicate & Temporal Stems + Negation + Year-Disambiguated Deadlines + Thresholds
        dup_src = f"{q_str} || {g_str}".lower() if g_str else q_str.lower()
        dup_src = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", dup_src)
        dup_norm = re.sub(r"[^a-z0-9$%>=<.+\-°|\s]", " ", dup_src)
        dup_norm = re.sub(r"\s+", " ", dup_norm).strip()
        dup_stem = hashlib.sha256(dup_norm.encode("utf-8")).hexdigest()[:20] if len(dup_norm) >= 12 else ""

        is_neg = bool(_NEGATION_RE.search(f"{q_str} {g_str}"))
        pred_type = "BINARY"
        th_lo: Optional[float] = None
        th_hi: Optional[float] = None
        is_strict_lo = False
        is_strict_hi = False
        unit = ""
        deadline_ts: Optional[int] = None
        deadline_year_ambiguous = False
        temporal_stem = ""

        m_dead = _DEADLINE_BY_DATE_RE.search(q_str)
        if m_dead:
            prep = re.sub(r"\s+", " ", m_dead.group(1).strip().lower())
            mo = _MONTH_MAP.get(m_dead.group(2).lower()[:3], 0)
            dy = int(m_dead.group(3))
            explicit_yr_str = m_dead.group(4)
            if explicit_yr_str:
                yr = int(explicit_yr_str)
                deadline_ts = _compute_deadline_utc_ts(yr, mo, dy, prep)
                if deadline_ts is not None and end_ts is not None and end_ts < deadline_ts - 2 * 86400:
                    deadline_year_ambiguous = True
            else:
                # Yearless deadline (e.g. "by March 31?" vs "by November 15?"): infer year ONLY when
                # `endDate` (`end_ts`) aligns within +/-14 days of `(cand_year, mo, dy)`; otherwise
                # flag `deadline_year_ambiguous=True` so backwards cross-year edges can never be emitted!
                if end_ts is not None:
                    end_dt = datetime.fromtimestamp(end_ts, tz=timezone.utc)
                    best_ts: Optional[int] = None
                    best_gap: Optional[int] = None
                    for cand_yr in (end_dt.year - 1, end_dt.year, end_dt.year + 1):
                        cand_ts = _compute_deadline_utc_ts(cand_yr, mo, dy, prep)
                        if cand_ts is not None:
                            gap = abs(cand_ts - end_ts)
                            if best_gap is None or gap < best_gap:
                                best_gap = gap
                                best_ts = cand_ts
                    if best_ts is not None and best_gap is not None and best_gap <= 14 * 86400:
                        deadline_ts = best_ts
                    else:
                        deadline_ts = best_ts if best_ts is not None else _compute_deadline_utc_ts(int(ref_year), mo, dy, prep)
                        deadline_year_ambiguous = True
                else:
                    deadline_ts = _compute_deadline_utc_ts(int(ref_year), mo, dy, prep)
                    deadline_year_ambiguous = True

            if deadline_ts is not None:
                stem_txt = (q_str[: m_dead.start()] + " <DATE> " + q_str[m_dead.end() :]).lower()
                stem_txt = re.sub(r"[^a-z0-9$%<>+\-.]+", " ", stem_txt)
                stem_txt = re.sub(r"\s+", " ", stem_txt).strip()
                if len(stem_txt) >= 10:
                    temporal_stem = f"TSTEM:{stem_txt}" + (f"|SCOPE:{scope_key}" if scope_key else "")
                    pred_type = "DEADLINE_BY"
                    if not subj:
                        subj = temporal_stem

        target_num_txt = f"{q_str} {g_str}" if g_str else q_str
        has_dollar = "$" in target_num_txt
        m_ou = _OVER_UNDER_RE.search(target_num_txt)
        m_rng = _RANGE_NUM_RE.search(target_num_txt)
        m_ge = _THRESHOLD_GE_RE.search(target_num_txt)
        m_le = _THRESHOLD_LE_RE.search(target_num_txt)
        m_bar = _PATH_BARRIER_NUM_RE.search(target_num_txt)
        is_path_barrier = bool(basis == "TOUCH_ANYTIME" or m_bar is not None)

        matched_q_span: Optional[Tuple[int, int]] = None

        def _q_span(match_obj: re.Match[str]) -> Optional[Tuple[int, int]]:
            if match_obj.start() < len(q_str):
                return (match_obj.start(), min(match_obj.end(), len(q_str)))
            return None

        # Check `Over/Under X` (`O/U X`) BEFORE `_THRESHOLD_LE_RE` so `"Over/Under 50.5"` is NEVER
        # misparsed as `"Under 50.5"` (`THRESHOLD_LE`) when `outcomes == ["Over", "Under"]`!
        if m_ou and pred_type == "BINARY":
            try:
                v_ou, u_ou = _scale_num(m_ou.group(1), m_ou.group(2) or "", has_dollar)
                matched_q_span = _q_span(m_ou)
                unit = u_ou or "OU_TOTAL"
                if polarity_mode == "OVER_UNDER":
                    pred_type = "THRESHOLD_GE"
                    th_lo = v_ou
                    is_strict_lo = True
                elif polarity_mode == "UNDER_OVER":
                    pred_type = "THRESHOLD_LE"
                    th_hi = v_ou
                    is_strict_hi = True
                else:
                    # O/U phrasing without explicit ["Over","Under"] or ["Under","Over"] labels: quarantine!
                    pred_type = "THRESHOLD_GE"
                    th_lo = v_ou
                    is_strict_lo = True
                    polarity_mode = "AMBIGUOUS_OU_OUTCOMES"
            except ValueError:
                pass
        elif m_rng and not (" vs " in q_str.lower() or " vs. " in q_str.lower()):
            try:
                if m_rng.group(1) is not None:
                    r_n1, r_s1, r_n2, r_s2 = m_rng.group(1), m_rng.group(2) or "", m_rng.group(3), m_rng.group(4) or ""
                else:
                    r_n1, r_s1, r_n2, r_s2 = m_rng.group(5), m_rng.group(6) or "", m_rng.group(7), m_rng.group(8) or ""
                v1, u1 = _scale_num(r_n1, r_s1 or r_s2, has_dollar)
                v2, u2 = _scale_num(r_n2, r_s2 or r_s1, has_dollar)
                if v2 >= v1:
                    matched_q_span = _q_span(m_rng)
                    pred_type = "RANGE_BRACKET"
                    th_lo, th_hi = v1, v2
                    is_strict_lo = False
                    is_strict_hi = False
                    unit = u1 or u2
                    if polarity_mode != "YES_NO":
                        polarity_mode = f"CONFLICT_RANGE_{polarity_mode}"
            except ValueError:
                pass
        elif m_ge and pred_type == "BINARY":
            try:
                op_ge = re.sub(r"\s+", " ", (m_ge.group(1) or m_ge.group(2) or "").strip().lower())
                v_ge, u_ge = _scale_num(m_ge.group(3), m_ge.group(4) or "", has_dollar)
                matched_q_span = _q_span(m_ge)
                pred_type = "THRESHOLD_GE"
                th_lo = v_ge
                is_strict_lo = op_ge in _STRICT_GE_OPS
                unit = u_ge
                if polarity_mode == "UNDER_OVER":
                    polarity_mode = "CONFLICT_UNDER_FIRST_ON_GE"
            except ValueError:
                pass
        elif m_le and pred_type == "BINARY":
            try:
                op_le = re.sub(r"\s+", " ", (m_le.group(1) or m_le.group(2) or "").strip().lower())
                v_le, u_le = _scale_num(m_le.group(3), m_le.group(4) or "", has_dollar)
                matched_q_span = _q_span(m_le)
                pred_type = "THRESHOLD_LE"
                th_hi = v_le
                is_strict_hi = op_le in _STRICT_LE_OPS
                unit = u_le
                if polarity_mode == "OVER_UNDER":
                    polarity_mode = "CONFLICT_OVER_FIRST_ON_LE"
            except ValueError:
                pass
        elif m_bar and pred_type == "BINARY":
            try:
                op_bar = re.sub(r"\s+", " ", (m_bar.group(1) or "").strip().lower())
                v_bar, u_bar = _scale_num(m_bar.group(2), m_bar.group(3) or "", has_dollar)
                matched_q_span = _q_span(m_bar)
                unit = u_bar
                is_path_barrier = True
                if op_bar.startswith(("dip", "drop", "fall", "plunge")):
                    pred_type = "THRESHOLD_LE"
                    th_hi = v_bar
                    is_strict_hi = False
                else:
                    pred_type = "THRESHOLD_GE"
                    th_lo = v_bar
                    is_strict_lo = False
            except ValueError:
                pass

        # Guard against description-vs-title inequality reversals (e.g. `"hit 36%"` resolving Yes when
        # rating is `"equal to or below the listed value"`):
        if pred_type == "THRESHOLD_GE" and _DESC_CONTRADICTS_GE_RE.search(d_str):
            polarity_mode = "CONFLICT_DESC_LE_VS_TITLE_GE"
        elif pred_type == "THRESHOLD_LE" and _DESC_CONTRADICTS_LE_RE.search(d_str):
            polarity_mode = "CONFLICT_DESC_GE_VS_TITLE_LE"

        metric_stem = (
            _normalize_metric_stem_key(q_str, matched_q_span)
            if pred_type in ("THRESHOLD_GE", "THRESHOLD_LE", "RANGE_BRACKET")
            else ""
        )

        if not subj and event_id:
            subj = f"EVT:{event_id}" + (f":{scope_key}" if scope_key else "")
        elif not subj and len(metric_stem) >= 10:
            day_b_stem = (end_ts // 86400) if end_ts else 0
            subj = f"MSTEM:{metric_stem}:{day_b_stem}" + (f":{scope_key}" if scope_key else "")

        has_creation_win = bool(
            re.search(r"\b(?:between|since|after|from)\s+market\s+creation\b", d_str, re.IGNORECASE)
        )

        prop_spec = PropositionSpec(
            subject_key=subj,
            temporal_stem_key=temporal_stem,
            duplicate_stem_key=dup_stem,
            predicate_type=pred_type,
            threshold_low=th_lo,
            threshold_high=th_hi,
            is_strict_low=is_strict_lo,
            is_strict_high=is_strict_hi,
            is_negated=is_neg,
            unit=unit,
            deadline_ts=deadline_ts if deadline_ts is not None else end_ts,
            scope_key=scope_key,
            metric_stem_key=metric_stem,
            outcome_polarity_mode=polarity_mode,
            deadline_year_ambiguous=deadline_year_ambiguous,
            is_path_dependent_barrier=is_path_barrier,
            has_creation_relative_window=has_creation_win,
        )
        return res_spec, prop_spec

    # -----------------------------------------------------------------------
    # Node Ingestion & Incremental Mutation
    # -----------------------------------------------------------------------

    def _parse_market_object(self, raw_m: Any, parent_event: Optional[EventNode] = None) -> Optional[Tuple[MarketNode, Tuple[OutcomeInstrumentNode, ...]]]:
        g = self._get_attr_or_key
        mid = str(g(raw_m, "market_id", "id", default="") or "").strip()
        slug = str(g(raw_m, "slug", "market_slug", default=mid) or mid).strip()
        if not mid:
            mid = slug
        if not mid:
            return None

        ev_id = str(
            g(raw_m, "event_id", "parent_event_id", default=(parent_event.event_id if parent_event else "")) or ""
        ).strip()
        cid = str(g(raw_m, "condition_id", "conditionId", default="") or "").strip()
        question = str(g(raw_m, "question", "title", default=slug) or slug).strip()
        grp_title = str(g(raw_m, "group_item_title", "groupItemTitle", default="") or "").strip()
        desc = str(g(raw_m, "description", "rules_text", "rule_summary", default="") or "").strip()
        rules_h_ovr = str(g(raw_m, "description_rule_hash", "rules_hash", default="") or "").strip()
        cat = str(g(raw_m, "category", default=(parent_event.category if parent_event else "other")) or "other").strip().lower()

        # Extract outcome labels & token IDs across both Gamma JSON strings & NormalizedMarket objects
        raw_tokens = g(raw_m, "clobTokenIds", "token_ids", "clob_token_ids", "token_ids_json", default=None)
        if isinstance(raw_tokens, str):
            try:
                tok_list = [str(x).strip() for x in json.loads(raw_tokens) if str(x).strip()]
            except Exception:
                tok_list = []
        elif isinstance(raw_tokens, Sequence):
            tok_list = [str(x).strip() for x in raw_tokens if str(x).strip()]
        else:
            tok_list = []

        raw_outcomes = g(raw_m, "outcomes", "outcome_labels", "outcomes_json", default=None)
        if isinstance(raw_outcomes, str):
            try:
                out_labels = [str(x).strip() for x in json.loads(raw_outcomes)]
            except Exception:
                out_labels = []
        elif isinstance(raw_outcomes, Sequence):
            out_labels = [str(x).strip() for x in raw_outcomes]
        else:
            out_labels = []

        # Support `@discovery` `NormalizedMarket.instruments` or `tokens` list of dicts/dataclasses
        inst_objs = g(raw_m, "instruments", "tokens", default=None)
        if not tok_list and isinstance(inst_objs, Sequence) and not isinstance(inst_objs, (str, bytes)):
            for io in inst_objs:
                tid = str(g(io, "token_id", "tokenId", "instrument_id", "id", default="") or "").strip()
                lbl = str(g(io, "outcome_label", "outcome", "label", "name", default="") or "").strip()
                if tid:
                    tok_list.append(tid)
                    out_labels.append(lbl or ("Yes" if len(tok_list) == 1 else "No"))

        explicit_out_labels = tuple(x for x in out_labels if x)
        yes_tok = str(g(raw_m, "yes_token_id", default=(tok_list[0] if len(tok_list) >= 1 else "")) or "").strip()
        no_tok = str(g(raw_m, "no_token_id", default=(tok_list[1] if len(tok_list) >= 2 else "")) or "").strip()
        if yes_tok and no_tok and not tok_list:
            tok_list = [yes_tok, no_tok]
        if len(out_labels) < len(tok_list):
            out_labels = ["Yes", "No"] + [f"Outcome_{k}" for k in range(2, len(tok_list))]

        enable_ob = bool(g(raw_m, "enable_order_book", "enableOrderBook", default=True) is not False)
        active = bool(g(raw_m, "active", default=True) is not False)
        closed = bool(g(raw_m, "closed", default=False) is True)
        archived = bool(g(raw_m, "archived", default=False) is True)

        neg_risk = bool(
            g(raw_m, "neg_risk", "negRisk", "enableNegRisk", default=(parent_event.neg_risk if parent_event else False))
        )
        nrm_id = str(
            g(raw_m, "neg_risk_market_id", "negRiskMarketID", "negRiskMarketId", default=(parent_event.neg_risk_market_id if parent_event else "")) or ""
        ).strip().lower()
        neg_aug = bool(
            g(raw_m, "neg_risk_augmented", "negRiskAugmented", "augmentedNegRisk", default=(parent_event.neg_risk_augmented if parent_event else False))
        )
        uma_st = str(g(raw_m, "uma_resolution_status", "umaResolutionStatus", default="") or "").strip().lower()

        # Fee rate bps extraction
        raw_bps = g(raw_m, "fee_rate_bps", "feeRateBps", "takerBaseFee", default=None)
        raw_fr = g(raw_m, "fee_rate", "feeRate", default=None)
        if raw_bps is not None:
            fv = float(raw_bps)
            fee_bps = fv if fv >= 1.0 or fv == 0.0 else fv * 10_000.0
        elif raw_fr is not None:
            fee_bps = normalize_fee_rate(fee_rate=float(raw_fr)) * 10_000.0
        else:
            fee_bps = 0.0

        tick_raw = g(raw_m, "tick_size", "minimum_tick_size", "orderPriceMinTickSize", default=0.01)
        try:
            tick_sz = float(tick_raw) if float(tick_raw or 0.0) > 0.0 else 0.01
        except (TypeError, ValueError):
            tick_sz = 0.01

        min_sz_raw = g(raw_m, "min_order_size", "minimum_order_size", "orderMinSize", default=DEFAULT_MIN_ORDER_SHARES)
        try:
            min_sz = max(DEFAULT_MIN_ORDER_SHARES, float(min_sz_raw or DEFAULT_MIN_ORDER_SHARES))
        except (TypeError, ValueError):
            min_sz = DEFAULT_MIN_ORDER_SHARES

        q_idx_raw = g(raw_m, "question_index", "questionIndex", default=None)
        q_idx: Optional[int] = None
        if isinstance(q_idx_raw, (int, float)) and not isinstance(q_idx_raw, bool):
            q_idx = int(q_idx_raw)
        elif isinstance(q_idx_raw, str) and q_idx_raw.strip().isdigit():
            q_idx = int(q_idx_raw.strip())

        check_lbl = grp_title or question
        is_ph = bool(
            g(raw_m, "is_placeholder", "isPlaceholder", "is_augmented_placeholder", default=False)
            or _PLACEHOLDER_LABEL_RE.search(check_lbl)
        )
        is_oth = bool(
            g(raw_m, "is_other", "isOther", "negRiskOther", "neg_risk_other", default=False)
            or _OTHER_LABEL_RE.match(check_lbl)
        )

        end_ts = _parse_iso_or_unix_ts(g(raw_m, "end_ts", "endDate", "endDateIso", "end_date_iso", default=None))
        res_spec, prop_spec = self.extract_resolution_and_proposition(
            question=question,
            description=desc,
            slug=slug,
            group_item_title=grp_title,
            category=cat,
            end_ts=end_ts,
            neg_risk=neg_risk,
            event_id=ev_id,
            outcome_labels=explicit_out_labels,
            rules_hash_override=rules_h_ovr,
        )

        inst_nodes: List[OutcomeInstrumentNode] = []
        for idx_t, tid in enumerate(tok_list):
            pol = "YES" if idx_t == 0 else ("NO" if idx_t == 1 else f"OUTCOME_{idx_t}")
            inst_nodes.append(
                OutcomeInstrumentNode(
                    token_id=tid,
                    market_id=mid,
                    event_id=ev_id,
                    condition_id=cid,
                    outcome_label=out_labels[idx_t] if idx_t < len(out_labels) else pol,
                    polarity=pol,
                    question_index=q_idx,
                    fee_rate_bps=fee_bps,
                    tick_size=tick_sz,
                    min_order_size=min_sz,
                    is_placeholder=is_ph,
                    is_other=is_oth,
                    enable_order_book=enable_ob,
                )
            )

        m_node = MarketNode(
            market_id=mid,
            event_id=ev_id,
            condition_id=cid,
            slug=slug,
            question=question,
            group_item_title=grp_title,
            category=cat,
            yes_token_id=yes_tok,
            no_token_id=no_tok,
            instrument_ids=tuple(tok_list),
            outcome_labels=tuple(out_labels[: len(tok_list)]) if tok_list else explicit_out_labels,
            enable_order_book=enable_ob,
            active=active,
            closed=closed,
            archived=archived,
            neg_risk=neg_risk,
            neg_risk_market_id=nrm_id,
            neg_risk_augmented=neg_aug,
            uma_resolution_status=uma_st,
            fee_rate_bps=fee_bps,
            tick_size=tick_sz,
            min_order_size=min_sz,
            is_placeholder=is_ph,
            is_other=is_oth,
            question_index=q_idx,
            resolution=res_spec,
            proposition=prop_spec,
        )
        return m_node, tuple(inst_nodes)

    def _index_market(self, m: MarketNode) -> Set[str]:
        touched_groups: Set[str] = set()
        if m.condition_id:
            gk = f"COND:{m.condition_id}"
            self._markets_by_condition.setdefault(m.condition_id, set()).add(m.market_id)
            touched_groups.add(gk)
        if m.event_id:
            gk = f"EVT:{m.event_id}"
            self._markets_by_event.setdefault(m.event_id, set()).add(m.market_id)
            touched_groups.add(gk)
        if m.neg_risk_market_id:
            gk = f"NR:{m.neg_risk_market_id}"
            self._markets_by_negrisk_id.setdefault(m.neg_risk_market_id, set()).add(m.market_id)
            touched_groups.add(gk)
        if m.proposition.subject_key:
            gk = f"SUBJ:{m.proposition.subject_key}"
            self._markets_by_subject.setdefault(m.proposition.subject_key, set()).add(m.market_id)
            touched_groups.add(gk)
        if m.proposition.temporal_stem_key:
            gk = f"TEMP:{m.proposition.temporal_stem_key}"
            self._markets_by_temporal_stem.setdefault(m.proposition.temporal_stem_key, set()).add(m.market_id)
            touched_groups.add(gk)
        if m.proposition.duplicate_stem_key:
            gk = f"DUP:{m.proposition.duplicate_stem_key}"
            self._markets_by_duplicate_stem.setdefault(m.proposition.duplicate_stem_key, set()).add(m.market_id)
            touched_groups.add(gk)
        return touched_groups

    def _unindex_market(self, m: MarketNode) -> Set[str]:
        touched_groups: Set[str] = set()
        if m.condition_id and m.condition_id in self._markets_by_condition:
            self._markets_by_condition[m.condition_id].discard(m.market_id)
            touched_groups.add(f"COND:{m.condition_id}")
        if m.event_id and m.event_id in self._markets_by_event:
            self._markets_by_event[m.event_id].discard(m.market_id)
            touched_groups.add(f"EVT:{m.event_id}")
        if m.neg_risk_market_id and m.neg_risk_market_id in self._markets_by_negrisk_id:
            self._markets_by_negrisk_id[m.neg_risk_market_id].discard(m.market_id)
            touched_groups.add(f"NR:{m.neg_risk_market_id}")
        if m.proposition.subject_key and m.proposition.subject_key in self._markets_by_subject:
            self._markets_by_subject[m.proposition.subject_key].discard(m.market_id)
            touched_groups.add(f"SUBJ:{m.proposition.subject_key}")
        if m.proposition.temporal_stem_key and m.proposition.temporal_stem_key in self._markets_by_temporal_stem:
            self._markets_by_temporal_stem[m.proposition.temporal_stem_key].discard(m.market_id)
            touched_groups.add(f"TEMP:{m.proposition.temporal_stem_key}")
        if m.proposition.duplicate_stem_key and m.proposition.duplicate_stem_key in self._markets_by_duplicate_stem:
            self._markets_by_duplicate_stem[m.proposition.duplicate_stem_key].discard(m.market_id)
            touched_groups.add(f"DUP:{m.proposition.duplicate_stem_key}")
        for tid in m.instrument_ids:
            self.instruments.pop(tid, None)
        return touched_groups

    def _add_edge(self, edge: PropositionEdge) -> None:
        self.edges[edge.edge_id] = edge
        self._edges_by_market.setdefault(edge.source_market_id, set()).add(edge.edge_id)
        self._edges_by_market.setdefault(edge.target_market_id, set()).add(edge.edge_id)
        if edge.group_key:
            self._edges_by_group.setdefault(edge.group_key, set()).add(edge.edge_id)

    def _clear_group_edges(self, group_key: str) -> Set[str]:
        dirty_mkts: Set[str] = set()
        eids = list(self._edges_by_group.pop(group_key, ()))
        for eid in eids:
            ed = self.edges.pop(eid, None)
            if ed is not None:
                dirty_mkts.add(ed.source_market_id)
                dirty_mkts.add(ed.target_market_id)
                if ed.source_market_id in self._edges_by_market:
                    self._edges_by_market[ed.source_market_id].discard(eid)
                if ed.target_market_id in self._edges_by_market:
                    self._edges_by_market[ed.target_market_id].discard(eid)
        return dirty_mkts

    def _rebuild_group(self, group_key: str) -> Tuple[Set[str], int]:
        """Recomputes all edges for a single indexed bucket `group_key` in O(m log m)."""
        dirty_mkts = self._clear_group_edges(group_key)
        added = 0

        if group_key.startswith("COND:"):
            cid = group_key[5:]
            mids = sorted(self._markets_by_condition.get(cid, ()))
            for mid in mids:
                m = self.markets.get(mid)
                if m is None:
                    continue
                dirty_mkts.add(mid)
                if m.yes_token_id and m.no_token_id and m.yes_token_id != m.no_token_id:
                    eid = f"BIN_CTF:{mid}"
                    self._add_edge(
                        PropositionEdge(
                            edge_id=eid,
                            edge_type=EdgeType.OFFICIAL_CONTRACTUAL,
                            relation_kind=RelationKind.BINARY_CTF_COMPLEMENT,
                            source_market_id=mid,
                            target_market_id=mid,
                            source_token_id=m.yes_token_id,
                            target_token_id=m.no_token_id,
                            group_key=group_key,
                            notes="On-chain CTF binary partition: 1 YES + 1 NO == $1.00 collateral",
                        )
                    )
                    added += 1

        elif group_key.startswith("NR:") or group_key.startswith("EVT:"):
            is_nr_bucket = group_key.startswith("NR:")
            raw_id = group_key[3:] if is_nr_bucket else group_key[4:]
            mids = sorted(
                self._markets_by_negrisk_id.get(raw_id, ())
                if is_nr_bucket
                else self._markets_by_event.get(raw_id, ())
            )
            mkts = [self.markets[mid] for mid in mids if mid in self.markets]
            if not is_nr_bucket:
                # Skip markets already grouped under a shared `neg_risk_market_id` so we don't duplicate
                mkts = [m for m in mkts if not m.neg_risk_market_id]
            if len(mkts) >= 2:
                for m in mkts:
                    dirty_mkts.add(m.market_id)
                ev_node = self.events.get(mkts[0].event_id)
                all_nr = is_nr_bucket or all(m.neg_risk for m in mkts)
                has_ph = any(m.is_placeholder for m in mkts)
                has_oth = any(m.is_other for m in mkts)
                has_closed = any(m.closed for m in mkts)
                has_disabled = any(not m.enable_order_book or not m.active or m.archived for m in mkts)
                is_aug = any(m.neg_risk_augmented for m in mkts) or bool(ev_node and (ev_node.neg_risk_augmented or ev_node.enable_neg_risk_other))

                disq: List[str] = []
                if has_ph:
                    disq.append("UNNAMED_PLACEHOLDER_OUTCOME_PRESENT")
                if is_aug and not has_oth:
                    disq.append("AUGMENTED_NEGRISK_MISSING_OTHER_SLOT")
                if has_closed:
                    disq.append("CLOSED_OR_RESOLVED_SLATE_MEMBER_PRESENT")
                if has_disabled:
                    disq.append("INACTIVE_OR_DISABLED_SLATE_MEMBER")
                if not all_nr:
                    disq.append("NON_NEGRISK_MULTI_MARKET_EVENT_REQUIRES_EXHAUSTIVENESS_PROOF")

                q_indices = [m.question_index for m in mkts if m.question_index is not None]
                if q_indices:
                    if (
                        len(q_indices) != len(mkts)
                        or len(set(q_indices)) != len(mkts)
                        or sorted(q_indices) != list(range(len(mkts)))
                    ):
                        disq.append("INCOMPLETE_OR_GAPPED_NEGRISK_QUESTION_INDICES")

                for ev_id_ref in sorted({m.event_id for m in mkts if m.event_id}):
                    ev_ref = self.events.get(ev_id_ref)
                    if ev_ref is not None and (ev_ref.raw_market_count > len(mkts) or len(ev_ref.market_ids) > len(mkts)):
                        disq.append("PARTIAL_EVENT_MARKET_SLATE_INGESTED")
                        break

                etype = EdgeType.OFFICIAL_CONTRACTUAL if (all_nr and not disq and len(mkts) >= 2) else EdgeType.SUSPECTED_REQUIRES_PROOF
                rkind = RelationKind.NEGRISK_CLOSED_SLATE if etype == EdgeType.OFFICIAL_CONTRACTUAL else RelationKind.NEGRISK_AUGMENTED_OR_INCOMPLETE

                # Star/chain topology (`mkts[0] -> mkts[k]`) keeps edge count O(m) instead of O(m^2)!
                anchor = mkts[0]
                for peer in mkts[1:]:
                    eid = f"{group_key}:{anchor.market_id}->{peer.market_id}"
                    self._add_edge(
                        PropositionEdge(
                            edge_id=eid,
                            edge_type=etype,
                            relation_kind=rkind,
                            source_market_id=anchor.market_id,
                            target_market_id=peer.market_id,
                            source_token_id=anchor.yes_token_id,
                            target_token_id=peer.yes_token_id,
                            group_key=group_key,
                            disqualifiers=tuple(disq),
                            notes="Closed NegRisk slate" if not disq else ";".join(disq),
                        )
                    )
                    added += 1

        elif group_key.startswith("SUBJ:"):
            s_key = group_key[5:]
            mids = sorted(self._markets_by_subject.get(s_key, ()))
            mkts = [self.markets[mid] for mid in mids if mid in self.markets]
            if len(mkts) >= 2:
                for m in mkts:
                    dirty_mkts.add(m.market_id)
                added += self._build_subject_ladder_edges(group_key, mkts)

        elif group_key.startswith("TEMP:"):
            t_key = group_key[5:]
            mids = sorted(self._markets_by_temporal_stem.get(t_key, ()))
            mkts = [
                self.markets[mid] for mid in mids if mid in self.markets and self.markets[mid].proposition.deadline_ts is not None
            ]
            if len(mkts) >= 2:
                mkts.sort(key=lambda x: (int(x.proposition.deadline_ts or 0), x.market_id))
                for i in range(len(mkts) - 1):
                    m_early, m_late = mkts[i], mkts[i + 1]
                    dirty_mkts.update((m_early.market_id, m_late.market_id))
                    if int(m_early.proposition.deadline_ts or 0) >= int(m_late.proposition.deadline_ts or 0):
                        continue
                    ok_res, issues = m_early.resolution.check_compatibility(m_late.resolution, allow_ordered_cutoffs=True)
                    disq_t = list(issues)
                    if m_early.proposition.is_negated or m_late.proposition.is_negated:
                        disq_t.append("NEGATED_DEADLINE_MONOTONICITY_REVERSAL")
                    if m_early.proposition.deadline_year_ambiguous or m_late.proposition.deadline_year_ambiguous:
                        disq_t.append("AMBIGUOUS_YEARLESS_DEADLINE")
                    if (
                        m_early.proposition.has_creation_relative_window
                        or m_late.proposition.has_creation_relative_window
                    ):
                        disq_t.append("MARKET_CREATION_RELATIVE_WINDOW_REQUIRES_TIMESTAMP_PROOF")
                    if (
                        m_early.resolution.cutoff_ts is not None
                        and m_late.resolution.cutoff_ts is not None
                        and m_early.resolution.cutoff_ts > m_late.resolution.cutoff_ts + 3600
                    ):
                        disq_t.append("DEADLINE_VS_ENDDATE_ORDER_INVERSION")
                    if m_early.proposition.scope_key != m_late.proposition.scope_key:
                        disq_t.append(
                            f"SUB_PERIOD_SCOPE_MISMATCH:{m_early.proposition.scope_key}!={m_late.proposition.scope_key}"
                        )
                    if (
                        m_early.proposition.outcome_polarity_mode != "YES_NO"
                        or m_late.proposition.outcome_polarity_mode != "YES_NO"
                    ):
                        disq_t.append(
                            f"NON_YES_NO_OUTCOME_POLARITY_ON_DEADLINE:{m_early.proposition.outcome_polarity_mode}|{m_late.proposition.outcome_polarity_mode}"
                        )
                    etype = EdgeType.VERIFIED_MATHEMATICAL if (ok_res and not disq_t) else EdgeType.SUSPECTED_REQUIRES_PROOF
                    structural_invalid = (
                        m_early.proposition.is_negated
                        or m_late.proposition.is_negated
                        or m_early.proposition.deadline_year_ambiguous
                        or m_late.proposition.deadline_year_ambiguous
                        or m_early.proposition.has_creation_relative_window
                        or m_late.proposition.has_creation_relative_window
                        or "DEADLINE_VS_ENDDATE_ORDER_INVERSION" in disq_t
                        or m_early.proposition.scope_key != m_late.proposition.scope_key
                        or m_early.proposition.outcome_polarity_mode != "YES_NO"
                        or m_late.proposition.outcome_polarity_mode != "YES_NO"
                    )
                    eid = f"{group_key}:{m_early.market_id}=>{m_late.market_id}"
                    self._add_edge(
                        PropositionEdge(
                            edge_id=eid,
                            edge_type=etype,
                            relation_kind=RelationKind.CORRELATED_SUBJECT if structural_invalid else RelationKind.IMPLIES,
                            source_market_id=m_early.market_id,
                            target_market_id=m_late.market_id,
                            source_token_id=m_early.yes_token_id,
                            target_token_id=m_late.yes_token_id,
                            group_key=group_key,
                            disqualifiers=tuple(disq_t),
                            notes=f"Deadline monotonicity: by {m_early.proposition.deadline_ts} => by {m_late.proposition.deadline_ts}",
                        )
                    )
                    added += 1

        elif group_key.startswith("DUP:"):
            d_key = group_key[4:]
            mids = sorted(self._markets_by_duplicate_stem.get(d_key, ()))
            mkts = [self.markets[mid] for mid in mids if mid in self.markets]
            if len(mkts) >= 2:
                anchor = mkts[0]
                for peer in mkts[1:]:
                    if anchor.condition_id and anchor.condition_id == peer.condition_id:
                        continue
                    dirty_mkts.update((anchor.market_id, peer.market_id))
                    ok_res, issues = anchor.resolution.check_compatibility(peer.resolution, allow_ordered_cutoffs=False)
                    disq_d = list(issues)
                    if anchor.proposition.is_negated != peer.proposition.is_negated:
                        disq_d.append("NEGATION_POLARITY_MISMATCH")
                    if anchor.proposition.scope_key != peer.proposition.scope_key:
                        disq_d.append(
                            f"SUB_PERIOD_SCOPE_MISMATCH:{anchor.proposition.scope_key}!={peer.proposition.scope_key}"
                        )
                    if (
                        anchor.proposition.outcome_polarity_mode != peer.proposition.outcome_polarity_mode
                        or anchor.proposition.outcome_polarity_mode not in ("YES_NO", "OVER_UNDER", "UNDER_OVER")
                    ):
                        disq_d.append(
                            f"OUTCOME_POLARITY_MISMATCH:{anchor.proposition.outcome_polarity_mode}!={peer.proposition.outcome_polarity_mode}"
                        )
                    if anchor.proposition.deadline_year_ambiguous or peer.proposition.deadline_year_ambiguous:
                        disq_d.append("AMBIGUOUS_YEARLESS_DEADLINE")
                    if (
                        anchor.proposition.has_creation_relative_window
                        or peer.proposition.has_creation_relative_window
                    ):
                        disq_d.append("MARKET_CREATION_RELATIVE_WINDOW_REQUIRES_TIMESTAMP_PROOF")
                    if (
                        anchor.proposition.deadline_ts is not None
                        and peer.proposition.deadline_ts is not None
                        and abs(anchor.proposition.deadline_ts - peer.proposition.deadline_ts) > 60
                    ):
                        disq_d.append("DEADLINE_TIMESTAMP_MISMATCH")
                    if (
                        anchor.proposition.threshold_low != peer.proposition.threshold_low
                        or anchor.proposition.threshold_high != peer.proposition.threshold_high
                        or anchor.proposition.is_strict_low != peer.proposition.is_strict_low
                        or anchor.proposition.is_strict_high != peer.proposition.is_strict_high
                    ):
                        disq_d.append("THRESHOLD_OR_STRICTNESS_MISMATCH")
                    etype = EdgeType.VERIFIED_MATHEMATICAL if (ok_res and not disq_d) else EdgeType.SUSPECTED_REQUIRES_PROOF
                    eid = f"{group_key}:{anchor.market_id}<=>{peer.market_id}"
                    self._add_edge(
                        PropositionEdge(
                            edge_id=eid,
                            edge_type=etype,
                            relation_kind=RelationKind.EQUIVALENT,
                            source_market_id=anchor.market_id,
                            target_market_id=peer.market_id,
                            source_token_id=anchor.yes_token_id,
                            target_token_id=peer.yes_token_id,
                            group_key=group_key,
                            disqualifiers=tuple(disq_d),
                            notes="Duplicate proposition question stem",
                        )
                    )
                    added += 1

        return dirty_mkts, added

    def _build_subject_ladder_edges(self, group_key: str, mkts: Sequence[MarketNode]) -> int:
        """
        Builds O(m log m) numerical threshold dominance (`S >= K_high => S >= K_low`,
        `S <= K_low => S <= K_high`), range cover (`[L, U)` => `>= L`), and cross-cohort
        (`SUSPECTED_REQUIRES_PROOF` / `STATISTICAL_CORRELATION_ONLY`) edges within a single
        subject bucket without allowing cross-oracle, cross-map/sub-period, or outcome-polarity-
        mismatched markets to sever or invert intra-cohort `VERIFIED_MATHEMATICAL` chains.
        """
        added = 0
        valid_polarity_modes = ("YES_NO", "OVER_UNDER", "UNDER_OVER")

        def _cohort_key(m: MarketNode) -> Tuple[str, str, str, str, int, str, str, str, str]:
            cut_min = int(m.resolution.cutoff_ts // 60) if m.resolution.cutoff_ts is not None else -1
            return (
                m.resolution.authority,
                m.resolution.oracle_source_id,
                m.resolution.settlement_basis,
                m.resolution.timezone_name,
                cut_min,
                m.proposition.unit,
                m.proposition.scope_key,
                m.proposition.metric_stem_key,
                m.proposition.outcome_polarity_mode,
            )

        cohorts: Dict[Tuple[str, str, str, str, int, str, str, str, str], List[MarketNode]] = {}
        for m in mkts:
            cohorts.setdefault(_cohort_key(m), []).append(m)

        cohort_anchors_by_day: Dict[int, List[MarketNode]] = {}

        for c_mkts in cohorts.values():
            aff_mkts = [
                m
                for m in c_mkts
                if not m.proposition.is_negated
                and not m.proposition.is_path_dependent_barrier
                and m.proposition.outcome_polarity_mode in valid_polarity_modes
            ]
            neg_mkts = [m for m in c_mkts if m.proposition.is_negated]
            barrier_mkts = [
                m
                for m in c_mkts
                if not m.proposition.is_negated and m.proposition.is_path_dependent_barrier
            ]
            bad_pol_mkts = [
                m
                for m in c_mkts
                if not m.proposition.is_negated
                and not m.proposition.is_path_dependent_barrier
                and m.proposition.outcome_polarity_mode not in valid_polarity_modes
            ]

            ge_mkts = [m for m in aff_mkts if m.proposition.predicate_type == "THRESHOLD_GE" and m.proposition.threshold_low is not None]
            le_mkts = [m for m in aff_mkts if m.proposition.predicate_type == "THRESHOLD_LE" and m.proposition.threshold_high is not None]
            rng_mkts = [
                m for m in aff_mkts
                if m.proposition.predicate_type == "RANGE_BRACKET"
                and m.proposition.threshold_low is not None
                and m.proposition.threshold_high is not None
            ]

            # 1. Intra-cohort upper-tail ladder: total inclusion order `(K, 1 if strict '>' else 0)`
            #    so `[K1, inf) supset (K1, inf) supset [K2, inf) supset (K2, inf)` (`S > K => S >= K`, never converse!)
            ge_mkts.sort(
                key=lambda m: (
                    float(m.proposition.threshold_low or 0.0),
                    1 if m.proposition.is_strict_low else 0,
                    m.market_id,
                )
            )
            for i in range(len(ge_mkts) - 1):
                m_lo, m_hi = ge_mkts[i], ge_mkts[i + 1]
                k_lo = float(m_lo.proposition.threshold_low or 0.0)
                k_hi = float(m_hi.proposition.threshold_low or 0.0)
                s_lo = bool(m_lo.proposition.is_strict_low)
                s_hi = bool(m_hi.proposition.is_strict_low)
                if abs(k_hi - k_lo) <= 1e-12 and s_hi == s_lo:
                    continue
                ok_res, issues = m_hi.resolution.check_compatibility(m_lo.resolution, allow_ordered_cutoffs=False)
                etype = EdgeType.VERIFIED_MATHEMATICAL if ok_res else EdgeType.SUSPECTED_REQUIRES_PROOF
                op_hi = ">" if s_hi else ">="
                op_lo = ">" if s_lo else ">="
                eid = f"{group_key}:GE:{m_hi.market_id}=>{m_lo.market_id}"
                self._add_edge(
                    PropositionEdge(
                        edge_id=eid,
                        edge_type=etype,
                        relation_kind=RelationKind.IMPLIES,
                        source_market_id=m_hi.market_id,
                        target_market_id=m_lo.market_id,
                        source_token_id=m_hi.yes_token_id,
                        target_token_id=m_lo.yes_token_id,
                        group_key=group_key,
                        disqualifiers=issues,
                        notes=f"Threshold dominance: S {op_hi} {k_hi} => S {op_lo} {k_lo}",
                    )
                )
                added += 1

            # 2. Intra-cohort lower-tail ladder: total inclusion order `(K, 0 if strict '<' else 1)`
            #    so `(-inf, K1) subset (-inf, K1] subset (-inf, K2) subset (-inf, K2]` (`S < K => S <= K`, never converse!)
            le_mkts.sort(
                key=lambda m: (
                    float(m.proposition.threshold_high or 0.0),
                    0 if m.proposition.is_strict_high else 1,
                    m.market_id,
                )
            )
            for i in range(len(le_mkts) - 1):
                m_lo, m_hi = le_mkts[i], le_mkts[i + 1]
                k_lo = float(m_lo.proposition.threshold_high or 0.0)
                k_hi = float(m_hi.proposition.threshold_high or 0.0)
                s_lo = bool(m_lo.proposition.is_strict_high)
                s_hi = bool(m_hi.proposition.is_strict_high)
                if abs(k_hi - k_lo) <= 1e-12 and s_hi == s_lo:
                    continue
                ok_res, issues = m_lo.resolution.check_compatibility(m_hi.resolution, allow_ordered_cutoffs=False)
                etype = EdgeType.VERIFIED_MATHEMATICAL if ok_res else EdgeType.SUSPECTED_REQUIRES_PROOF
                op_lo = "<" if s_lo else "<="
                op_hi = "<" if s_hi else "<="
                eid = f"{group_key}:LE:{m_lo.market_id}=>{m_hi.market_id}"
                self._add_edge(
                    PropositionEdge(
                        edge_id=eid,
                        edge_type=etype,
                        relation_kind=RelationKind.IMPLIES,
                        source_market_id=m_lo.market_id,
                        target_market_id=m_hi.market_id,
                        source_token_id=m_lo.yes_token_id,
                        target_token_id=m_hi.yes_token_id,
                        group_key=group_key,
                        disqualifiers=issues,
                        notes=f"Lower-tail dominance: S {op_lo} {k_lo} => S {op_hi} {k_hi}",
                    )
                )
                added += 1

            # 3. Intra-cohort range bracket `[L, U]` containment:
            #    - `[L, U] subset [K, inf)` requires `K <= L` (weak `>=`)
            #    - `[L, U] subset (K, inf)` requires `K < L` STRICTLY (strict `>`)!
            if rng_mkts and ge_mkts:
                for m_r in rng_mkts:
                    r_lo = float(m_r.proposition.threshold_low or 0.0)
                    valid_cands = [
                        g
                        for g in ge_mkts
                        if g.market_id != m_r.market_id
                        and (
                            float(g.proposition.threshold_low or 0.0) < r_lo - 1e-12
                            or (
                                not g.proposition.is_strict_low
                                and float(g.proposition.threshold_low or 0.0) <= r_lo + 1e-12
                            )
                        )
                    ]
                    if valid_cands:
                        m_g = valid_cands[-1]
                        ok_res, issues = m_r.resolution.check_compatibility(m_g.resolution, allow_ordered_cutoffs=False)
                        etype = EdgeType.VERIFIED_MATHEMATICAL if ok_res else EdgeType.SUSPECTED_REQUIRES_PROOF
                        op_g = ">" if m_g.proposition.is_strict_low else ">="
                        eid = f"{group_key}:RNG_IMP:{m_r.market_id}=>{m_g.market_id}"
                        self._add_edge(
                            PropositionEdge(
                                edge_id=eid,
                                edge_type=etype,
                                relation_kind=RelationKind.INTERVAL_COVER,
                                source_market_id=m_r.market_id,
                                target_market_id=m_g.market_id,
                                source_token_id=m_r.yes_token_id,
                                target_token_id=m_g.yes_token_id,
                                group_key=group_key,
                                disqualifiers=issues,
                                notes=f"Interval containment: [{r_lo}, {m_r.proposition.threshold_high}] => S {op_g} {m_g.proposition.threshold_low}",
                            )
                        )
                        added += 1
                    else:
                        # Boundary collision `[L, U]` vs strict `S > L`: quarantine as SUSPECTED_REQUIRES_PROOF!
                        strict_eq = [
                            g
                            for g in ge_mkts
                            if g.market_id != m_r.market_id
                            and g.proposition.is_strict_low
                            and abs(float(g.proposition.threshold_low or 0.0) - r_lo) <= 1e-12
                        ]
                        if strict_eq:
                            m_g = strict_eq[0]
                            _, issues = m_r.resolution.check_compatibility(m_g.resolution, allow_ordered_cutoffs=False)
                            disq_b = tuple(list(issues) + ["STRICT_BOUNDARY_EXCLUSION_AT_LOWER_ENDPOINT"])
                            eid = f"{group_key}:RNG_STRICT_BOUND:{m_r.market_id}<->{m_g.market_id}"
                            self._add_edge(
                                PropositionEdge(
                                    edge_id=eid,
                                    edge_type=EdgeType.SUSPECTED_REQUIRES_PROOF,
                                    relation_kind=RelationKind.CORRELATED_SUBJECT,
                                    source_market_id=m_r.market_id,
                                    target_market_id=m_g.market_id,
                                    source_token_id=m_r.yes_token_id,
                                    target_token_id=m_g.yes_token_id,
                                    group_key=group_key,
                                    disqualifiers=disq_b,
                                    notes=f"Boundary gap at {r_lo}: [{r_lo}, {m_r.proposition.threshold_high}] does NOT imply S > {r_lo}",
                                )
                            )
                            added += 1

            # 3b. Intra-cohort range bracket `[L, U]` upper containment against `THRESHOLD_LE`:
            #     - `[L, U] subset (-inf, K]` requires `K >= U` (weak `<=`)
            #     - `[L, U] subset (-inf, K)` requires `K > U` STRICTLY (strict `<`)!
            if rng_mkts and le_mkts:
                for m_r in rng_mkts:
                    r_hi = float(m_r.proposition.threshold_high or 0.0)
                    valid_le = [
                        l_m
                        for l_m in le_mkts
                        if l_m.market_id != m_r.market_id
                        and (
                            float(l_m.proposition.threshold_high or 0.0) > r_hi + 1e-12
                            or (
                                not l_m.proposition.is_strict_high
                                and float(l_m.proposition.threshold_high or 0.0) >= r_hi - 1e-12
                            )
                        )
                    ]
                    if valid_le:
                        m_l = valid_le[0]
                        ok_res, issues = m_r.resolution.check_compatibility(m_l.resolution, allow_ordered_cutoffs=False)
                        etype = EdgeType.VERIFIED_MATHEMATICAL if ok_res else EdgeType.SUSPECTED_REQUIRES_PROOF
                        op_l = "<" if m_l.proposition.is_strict_high else "<="
                        eid = f"{group_key}:RNG_LE_IMP:{m_r.market_id}=>{m_l.market_id}"
                        self._add_edge(
                            PropositionEdge(
                                edge_id=eid,
                                edge_type=etype,
                                relation_kind=RelationKind.INTERVAL_COVER,
                                source_market_id=m_r.market_id,
                                target_market_id=m_l.market_id,
                                source_token_id=m_r.yes_token_id,
                                target_token_id=m_l.yes_token_id,
                                group_key=group_key,
                                disqualifiers=issues,
                                notes=f"Interval upper containment: [{m_r.proposition.threshold_low}, {r_hi}] => S {op_l} {m_l.proposition.threshold_high}",
                            )
                        )
                        added += 1
                    else:
                        strict_eq_hi = [
                            l_m
                            for l_m in le_mkts
                            if l_m.market_id != m_r.market_id
                            and l_m.proposition.is_strict_high
                            and abs(float(l_m.proposition.threshold_high or 0.0) - r_hi) <= 1e-12
                        ]
                        if strict_eq_hi:
                            m_l = strict_eq_hi[0]
                            _, issues = m_r.resolution.check_compatibility(m_l.resolution, allow_ordered_cutoffs=False)
                            disq_bu = tuple(list(issues) + ["STRICT_BOUNDARY_EXCLUSION_AT_UPPER_ENDPOINT"])
                            eid = f"{group_key}:RNG_STRICT_HI_BOUND:{m_r.market_id}<->{m_l.market_id}"
                            self._add_edge(
                                PropositionEdge(
                                    edge_id=eid,
                                    edge_type=EdgeType.SUSPECTED_REQUIRES_PROOF,
                                    relation_kind=RelationKind.CORRELATED_SUBJECT,
                                    source_market_id=m_r.market_id,
                                    target_market_id=m_l.market_id,
                                    source_token_id=m_r.yes_token_id,
                                    target_token_id=m_l.yes_token_id,
                                    group_key=group_key,
                                    disqualifiers=disq_bu,
                                    notes=f"Boundary gap at {r_hi}: [{m_r.proposition.threshold_low}, {r_hi}] does NOT imply S < {r_hi}",
                                )
                            )
                            added += 1

            rep = ge_mkts[0] if ge_mkts else (le_mkts[0] if le_mkts else (rng_mkts[0] if rng_mkts else None))
            if neg_mkts:
                neg_anchor = rep if rep is not None else neg_mkts[0]
                for m_neg in neg_mkts:
                    if m_neg.market_id == neg_anchor.market_id:
                        continue
                    _, issues = m_neg.resolution.check_compatibility(neg_anchor.resolution, allow_ordered_cutoffs=False)
                    disq_n = tuple(list(issues) + ["NEGATED_THRESHOLD_PROPOSITION"])
                    eid = f"{group_key}:NEG:{m_neg.market_id}<->{neg_anchor.market_id}"
                    self._add_edge(
                        PropositionEdge(
                            edge_id=eid,
                            edge_type=EdgeType.SUSPECTED_REQUIRES_PROOF,
                            relation_kind=RelationKind.CORRELATED_SUBJECT,
                            source_market_id=m_neg.market_id,
                            target_market_id=neg_anchor.market_id,
                            source_token_id=m_neg.yes_token_id,
                            target_token_id=neg_anchor.yes_token_id,
                            group_key=group_key,
                            disqualifiers=disq_n,
                            notes="Negated threshold proposition quarantined from dominance chain",
                        )
                    )
                    added += 1
                if rep is None:
                    rep = neg_mkts[0]

            if barrier_mkts:
                bar_anchor = rep if rep is not None else barrier_mkts[0]
                for m_bar in barrier_mkts:
                    if m_bar.market_id == bar_anchor.market_id:
                        continue
                    _, issues = m_bar.resolution.check_compatibility(bar_anchor.resolution, allow_ordered_cutoffs=False)
                    disq_bar = list(issues) + ["PATH_DEPENDENT_BARRIER_REQUIRES_SPOT_AND_WINDOW_PROOF"]
                    if (
                        m_bar.proposition.has_creation_relative_window
                        or bar_anchor.proposition.has_creation_relative_window
                    ):
                        disq_bar.append("MARKET_CREATION_RELATIVE_WINDOW_REQUIRES_TIMESTAMP_PROOF")
                    if m_bar.proposition.outcome_polarity_mode not in valid_polarity_modes:
                        disq_bar.append(
                            f"AMBIGUOUS_OR_NON_STANDARD_OUTCOME_POLARITY:{m_bar.proposition.outcome_polarity_mode}"
                        )
                    elif bar_anchor.proposition.outcome_polarity_mode not in valid_polarity_modes:
                        disq_bar.append(
                            f"AMBIGUOUS_OR_NON_STANDARD_OUTCOME_POLARITY:{bar_anchor.proposition.outcome_polarity_mode}"
                        )
                    eid = f"{group_key}:BARRIER:{m_bar.market_id}<->{bar_anchor.market_id}"
                    self._add_edge(
                        PropositionEdge(
                            edge_id=eid,
                            edge_type=EdgeType.SUSPECTED_REQUIRES_PROOF,
                            relation_kind=RelationKind.CORRELATED_SUBJECT,
                            source_market_id=m_bar.market_id,
                            target_market_id=bar_anchor.market_id,
                            source_token_id=m_bar.yes_token_id,
                            target_token_id=bar_anchor.yes_token_id,
                            group_key=group_key,
                            disqualifiers=tuple(disq_bar),
                            notes="Path-dependent hit/reach/touch barrier quarantined from dominance chain",
                        )
                    )
                    added += 1
                if rep is None:
                    rep = barrier_mkts[0]

            if bad_pol_mkts:
                pol_anchor = rep if rep is not None else bad_pol_mkts[0]
                for m_pol in bad_pol_mkts:
                    if m_pol.market_id == pol_anchor.market_id:
                        continue
                    _, issues = m_pol.resolution.check_compatibility(pol_anchor.resolution, allow_ordered_cutoffs=False)
                    disq_p = tuple(
                        list(issues)
                        + [f"AMBIGUOUS_OR_NON_STANDARD_OUTCOME_POLARITY:{m_pol.proposition.outcome_polarity_mode}"]
                    )
                    eid = f"{group_key}:POL:{m_pol.market_id}<->{pol_anchor.market_id}"
                    self._add_edge(
                        PropositionEdge(
                            edge_id=eid,
                            edge_type=EdgeType.SUSPECTED_REQUIRES_PROOF,
                            relation_kind=RelationKind.CORRELATED_SUBJECT,
                            source_market_id=m_pol.market_id,
                            target_market_id=pol_anchor.market_id,
                            source_token_id=m_pol.yes_token_id,
                            target_token_id=pol_anchor.yes_token_id,
                            group_key=group_key,
                            disqualifiers=disq_p,
                            notes="Ambiguous or non-standard outcome polarity quarantined from dominance chain",
                        )
                    )
                    added += 1
                if rep is None and any(
                    m.proposition.predicate_type in ("THRESHOLD_GE", "THRESHOLD_LE", "RANGE_BRACKET")
                    for m in bad_pol_mkts
                ):
                    rep = bad_pol_mkts[0]

            if rep is not None:
                day_b = int(rep.resolution.cutoff_ts // 86400) if rep.resolution.cutoff_ts is not None else -1
                cohort_anchors_by_day.setdefault(day_b, []).append(rep)

        # 4. Cross-cohort links on same subject & day (`SUSPECTED_REQUIRES_PROOF` / `STATISTICAL_CORRELATION_ONLY`)
        for day_anchors in cohort_anchors_by_day.values():
            if len(day_anchors) < 2:
                continue
            day_anchors.sort(key=lambda m: m.market_id)
            primary = day_anchors[0]
            for sec in day_anchors[1:]:
                _, issues = sec.resolution.check_compatibility(primary.resolution, allow_ordered_cutoffs=True)
                disq = list(issues)
                if primary.proposition.unit != sec.proposition.unit:
                    disq.append(f"UNIT_MISMATCH:{sec.proposition.unit}!={primary.proposition.unit}")
                if primary.proposition.scope_key != sec.proposition.scope_key:
                    disq.append(f"SUB_PERIOD_SCOPE_MISMATCH:{sec.proposition.scope_key}!={primary.proposition.scope_key}")
                if primary.proposition.is_path_dependent_barrier or sec.proposition.is_path_dependent_barrier:
                    disq.append("PATH_DEPENDENT_BARRIER_REQUIRES_SPOT_AND_WINDOW_PROOF")
                if primary.proposition.is_negated or sec.proposition.is_negated:
                    disq.append("NEGATED_THRESHOLD_PROPOSITION")
                elif primary.proposition.metric_stem_key != sec.proposition.metric_stem_key:
                    disq.append("METRIC_OR_ENTITY_STEM_MISMATCH")
                if (
                    primary.proposition.outcome_polarity_mode not in valid_polarity_modes
                    or sec.proposition.outcome_polarity_mode not in valid_polarity_modes
                    or primary.proposition.outcome_polarity_mode != sec.proposition.outcome_polarity_mode
                ):
                    disq.append(
                        f"OUTCOME_POLARITY_MISMATCH:{sec.proposition.outcome_polarity_mode}!={primary.proposition.outcome_polarity_mode}"
                    )
                cross_oracle = any(x.startswith(("AUTHORITY_MISMATCH", "ORACLE_SOURCE_MISMATCH")) for x in disq)
                etype = EdgeType.STATISTICAL_CORRELATION_ONLY if cross_oracle else EdgeType.SUSPECTED_REQUIRES_PROOF
                eid = f"{group_key}:XCOHORT:{sec.market_id}<->{primary.market_id}"
                self._add_edge(
                    PropositionEdge(
                        edge_id=eid,
                        edge_type=etype,
                        relation_kind=RelationKind.CORRELATED_SUBJECT,
                        source_market_id=sec.market_id,
                        target_market_id=primary.market_id,
                        source_token_id=sec.yes_token_id,
                        target_token_id=primary.yes_token_id,
                        group_key=group_key,
                        disqualifiers=tuple(disq),
                        notes="Cross-cohort subject comparison (" + ";".join(disq) + ")",
                    )
                )
                added += 1

        # 5. Sports / Matchup bucket (`MATCH:...`) where markets lack numerical thresholds (e.g. 90m vs Moneyline)
        if group_key.startswith("SUBJ:MATCH:") and len(mkts) >= 2:
            existing_group_eids = self._edges_by_group.get(group_key, set())
            covered_mids: Set[str] = set()
            for geid in existing_group_eids:
                ged = self.edges.get(geid)
                if ged is not None:
                    covered_mids.add(ged.source_market_id)
                    covered_mids.add(ged.target_market_id)
            anchor = mkts[0]
            for peer in mkts[1:]:
                if anchor.market_id in covered_mids and peer.market_id in covered_mids:
                    continue
                if anchor.event_id and anchor.event_id == peer.event_id and anchor.neg_risk and peer.neg_risk:
                    continue
                ok_res, issues = anchor.resolution.check_compatibility(peer.resolution, allow_ordered_cutoffs=True)
                etype = EdgeType.SUSPECTED_REQUIRES_PROOF if issues else EdgeType.STATISTICAL_CORRELATION_ONLY
                eid = f"{group_key}:MATCH:{anchor.market_id}<->{peer.market_id}"
                self._add_edge(
                    PropositionEdge(
                        edge_id=eid,
                        edge_type=etype,
                        relation_kind=RelationKind.CORRELATED_SUBJECT,
                        source_market_id=anchor.market_id,
                        target_market_id=peer.market_id,
                        source_token_id=anchor.yes_token_id,
                        target_token_id=peer.yes_token_id,
                        group_key=group_key,
                        disqualifiers=issues,
                        notes="Shared sports matchup bucket" + (f" ({';'.join(issues)})" if issues else ""),
                    )
                )
                added += 1

        return added

    def ingest_events_and_markets(
        self,
        *,
        events: Sequence[Any] = (),
        standalone_markets: Sequence[Any] = (),
    ) -> GraphUpdateDelta:
        """
        Ingests a batch of Gamma raw event/market dicts OR `@discovery` `NormalizedEvent` /
        `NormalizedMarket` objects, incrementally rebuilding only affected relationship buckets.
        """
        g = self._get_attr_or_key
        upserted_mids: List[str] = []
        touched_groups: Set[str] = set()

        for raw_ev in events or ():
            ev_id = str(g(raw_ev, "event_id", "id", default="") or "").strip()
            slug = str(g(raw_ev, "slug", default=ev_id) or ev_id).strip()
            if not ev_id:
                ev_id = slug
            if not ev_id:
                continue
            ev_mkts_raw = g(raw_ev, "markets", default=()) or ()
            declared_mkt_cnt = int(g(raw_ev, "market_count", "marketCount", "numMarkets", default=0) or 0)
            prev_ev = self.events.get(ev_id)
            raw_mkt_cnt = max(len(ev_mkts_raw), declared_mkt_cnt, prev_ev.raw_market_count if prev_ev else 0)
            ev_node = EventNode(
                event_id=ev_id,
                slug=slug,
                title=str(g(raw_ev, "title", default=slug) or slug).strip(),
                category=str(g(raw_ev, "category", default="other") or "other").strip().lower(),
                neg_risk=bool(g(raw_ev, "neg_risk", "negRisk", "enableNegRisk", default=False)),
                neg_risk_market_id=str(g(raw_ev, "neg_risk_market_id", "negRiskMarketID", "negRiskMarketId", default="") or "").strip().lower(),
                neg_risk_augmented=bool(g(raw_ev, "neg_risk_augmented", "negRiskAugmented", "augmentedNegRisk", default=False)),
                enable_neg_risk_other=bool(g(raw_ev, "enable_neg_risk_other", "enableNegRiskOther", "negRiskOther", default=False)),
                market_ids=(),
                raw_market_count=raw_mkt_cnt,
            )
            child_ids: List[str] = []
            for rm in ev_mkts_raw:
                parsed = self._parse_market_object(rm, parent_event=ev_node)
                if parsed is None:
                    continue
                m_node, inst_tuple = parsed
                child_ids.append(m_node.market_id)
                if m_node.market_id in self.markets:
                    touched_groups |= self._unindex_market(self.markets[m_node.market_id])
                self.markets[m_node.market_id] = m_node
                for inst in inst_tuple:
                    self.instruments[inst.token_id] = inst
                touched_groups |= self._index_market(m_node)
                upserted_mids.append(m_node.market_id)

            self.events[ev_id] = EventNode(
                event_id=ev_node.event_id,
                slug=ev_node.slug,
                title=ev_node.title,
                category=ev_node.category,
                neg_risk=ev_node.neg_risk,
                neg_risk_market_id=ev_node.neg_risk_market_id,
                neg_risk_augmented=ev_node.neg_risk_augmented,
                enable_neg_risk_other=ev_node.enable_neg_risk_other,
                market_ids=tuple(child_ids),
                raw_market_count=raw_mkt_cnt,
            )

        for rm in standalone_markets or ():
            parsed = self._parse_market_object(rm, parent_event=None)
            if parsed is None:
                continue
            m_node, inst_tuple = parsed
            if m_node.market_id in self.markets:
                touched_groups |= self._unindex_market(self.markets[m_node.market_id])
            self.markets[m_node.market_id] = m_node
            for inst in inst_tuple:
                self.instruments[inst.token_id] = inst
            touched_groups |= self._index_market(m_node)
            upserted_mids.append(m_node.market_id)

        dirty_mkts: Set[str] = set(upserted_mids)
        edges_rebuilt = 0
        for gk in sorted(touched_groups):
            d_m, cnt = self._rebuild_group(gk)
            dirty_mkts |= d_m
            edges_rebuilt += cnt

        return GraphUpdateDelta(
            upserted_market_ids=tuple(dict.fromkeys(upserted_mids)),
            removed_market_ids=(),
            dirty_market_ids=tuple(sorted(dirty_mkts)),
            dirty_group_keys=tuple(sorted(touched_groups)),
            edges_rebuilt=edges_rebuilt,
        )

    def incremental_update(
        self,
        *,
        updated_markets: Sequence[Any] = (),
        removed_market_ids: Sequence[str] = (),
    ) -> GraphUpdateDelta:
        """
        Incrementally updates/removes changed markets and recomputes ONLY affected relationship groups.
        """
        touched_groups: Set[str] = set()
        removed_out: List[str] = []
        for rmid in removed_market_ids or ():
            mid_s = str(rmid or "").strip()
            old_m = self.markets.pop(mid_s, None)
            if old_m is not None:
                touched_groups |= self._unindex_market(old_m)
                removed_out.append(mid_s)

        delta_ing = self.ingest_events_and_markets(standalone_markets=updated_markets)
        extra_dirty: Set[str] = set(delta_ing.dirty_market_ids) | set(removed_out)
        extra_edges = delta_ing.edges_rebuilt

        only_removed_groups = touched_groups - set(delta_ing.dirty_group_keys)
        for gk in sorted(only_removed_groups):
            d_m, cnt = self._rebuild_group(gk)
            extra_dirty |= d_m
            extra_edges += cnt

        return GraphUpdateDelta(
            upserted_market_ids=delta_ing.upserted_market_ids,
            removed_market_ids=tuple(removed_out),
            dirty_market_ids=tuple(sorted(extra_dirty)),
            dirty_group_keys=tuple(sorted(set(delta_ing.dirty_group_keys) | touched_groups)),
            edges_rebuilt=extra_edges,
        )

    def add_explicit_edge(self, edge: PropositionEdge) -> None:
        """Allows specialized detectors or solvers to attach custom verified/suspected edges."""
        self._add_edge(edge)

    # -----------------------------------------------------------------------
    # Portfolio Holdings Attachment (`D-001` Frozen `KMIA` Quarantine)
    # -----------------------------------------------------------------------

    def load_portfolio_holdings(self, positions_or_state: Any) -> Tuple[int, int]:
        """
        Attaches existing portfolio positions from `live_harvester_state.json` (or a dict/list of
        position dicts) onto the graph while **strictly quarantining** the 4 disputed `KMIA` Nov 7
        positions (`6707503`, `6707502`) and any `umaResolutionStatus == 'disputed'` lock (`D-001`).
        Returns `(recyclable_count, frozen_quarantined_count)`.
        """
        self.holdings.clear()
        self._clear_group_edges("PORTFOLIO_HOLDINGS")

        raw_items: List[Tuple[str, Mapping[str, Any]]] = []
        if isinstance(positions_or_state, Mapping):
            if "active_positions" in positions_or_state and isinstance(positions_or_state["active_positions"], Mapping):
                raw_items = [(str(k), v) for k, v in positions_or_state["active_positions"].items() if isinstance(v, Mapping)]
            else:
                raw_items = [(str(k), v) for k, v in positions_or_state.items() if isinstance(v, Mapping)]
        elif isinstance(positions_or_state, Sequence) and not isinstance(positions_or_state, (str, bytes)):
            for idx, item in enumerate(positions_or_state):
                if isinstance(item, Mapping):
                    hid = str(item.get("trade_id") or item.get("holding_id") or f"pos_{idx}")
                    raw_items.append((hid, item))

        recyclable_n = 0
        frozen_n = 0
        for hid, pos in raw_items:
            mid = str(pos.get("market_id") or "").strip()
            cid = str(pos.get("condition_id") or "").strip()
            tok = str(pos.get("token_id") or pos.get("asset_id") or "").strip()
            sh = float(pos.get("remaining_shares") or pos.get("shares") or pos.get("entry_shares") or 0.0)
            if sh <= 0.0:
                continue
            cost_usd = float(pos.get("notional_usd") or pos.get("cost_basis_usd") or 0.0)
            mark_bid = float(pos.get("best_bid") or pos.get("mark_bid") or 0.0)
            uma_st = str(pos.get("umaResolutionStatus") or pos.get("uma_resolution_status") or "").strip().lower()
            tid_u = str(pos.get("trade_id") or hid).strip().upper()

            is_frozen = bool(
                pos.get("is_frozen_disputed")
                or uma_st == "disputed"
                or mid in FROZEN_DISPUTED_MARKET_IDS
                or any(sub in tid_u for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS)
            )
            node = PortfolioHoldingNode(
                holding_id=hid,
                token_id=tok,
                market_id=mid,
                condition_id=cid,
                side=str(pos.get("side") or pos.get("target_token") or "").strip().upper(),
                shares=round(sh, 6),
                cost_basis_usd=round(cost_usd, 6),
                mark_bid_px=round(mark_bid, 6),
                uma_resolution_status=uma_st,
                is_frozen_disputed=is_frozen,
                eligible_for_recycling=not is_frozen,
            )
            self.holdings[hid] = node
            if is_frozen:
                frozen_n += 1
            else:
                recyclable_n += 1
                if mid and mid in self.markets:
                    self._add_edge(
                        PropositionEdge(
                            edge_id=f"HOLDING:{hid}->{mid}",
                            edge_type=EdgeType.OFFICIAL_CONTRACTUAL,
                            relation_kind=RelationKind.PORTFOLIO_INVENTORY_LINK,
                            source_market_id=mid,
                            target_market_id=mid,
                            source_token_id=tok,
                            target_token_id=self.markets[mid].no_token_id if tok == self.markets[mid].yes_token_id else self.markets[mid].yes_token_id,
                            group_key="PORTFOLIO_HOLDINGS",
                            notes="Recyclable non-frozen wallet inventory link",
                        )
                    )
        return recyclable_n, frozen_n

    def get_recyclable_holdings(self) -> List[PortfolioHoldingNode]:
        return [h for h in self.holdings.values() if h.eligible_for_recycling and not h.is_frozen_disputed]

    def get_frozen_holdings(self) -> List[PortfolioHoldingNode]:
        return [h for h in self.holdings.values() if h.is_frozen_disputed or not h.eligible_for_recycling]

    # -----------------------------------------------------------------------
    # Connected-Component Pruning & Query API
    # -----------------------------------------------------------------------

    def get_connected_components(
        self,
        *,
        allowed_edge_types: Sequence[EdgeType] = (
            EdgeType.OFFICIAL_CONTRACTUAL,
            EdgeType.VERIFIED_MATHEMATICAL,
        ),
        only_market_ids: Optional[Set[str]] = None,
        include_single_market_binaries: bool = False,
        only_orderbook_enabled: bool = True,
    ) -> List[ConnectedMarketComponent]:
        """
        Extracts pruned connected components using ONLY `allowed_edge_types`, preventing solvers and
        multi-leg detectors from running combinatorial `O(N^2)` searches across unrelated markets.
        """
        allowed_set = {EdgeType(et) if not isinstance(et, EdgeType) else et for et in allowed_edge_types}
        recyclable_by_mkt: Dict[str, List[str]] = {}
        for h in self.get_recyclable_holdings():
            if h.market_id:
                recyclable_by_mkt.setdefault(h.market_id, []).append(h.holding_id)

        visited: Set[str] = set()
        components: List[ConnectedMarketComponent] = []

        seed_mids = sorted(only_market_ids) if only_market_ids is not None else sorted(self.markets.keys())

        for start_mid in seed_mids:
            if start_mid in visited or start_mid not in self.markets:
                continue
            m0 = self.markets[start_mid]
            if only_orderbook_enabled and not m0.enable_order_book:
                visited.add(start_mid)
                continue

            comp_mkts: Set[str] = set()
            comp_edges: Dict[str, PropositionEdge] = {}
            q: deque[str] = deque([start_mid])
            visited.add(start_mid)

            while q:
                cur = q.popleft()
                cm = self.markets.get(cur)
                if cm is None or (only_orderbook_enabled and not cm.enable_order_book):
                    continue
                comp_mkts.add(cur)
                for eid in self._edges_by_market.get(cur, ()):
                    ed = self.edges.get(eid)
                    if ed is None or ed.edge_type not in allowed_set:
                        continue
                    comp_edges[eid] = ed
                    for nbr in (ed.source_market_id, ed.target_market_id):
                        if nbr not in visited and nbr in self.markets:
                            nm = self.markets[nbr]
                            if not only_orderbook_enabled or nm.enable_order_book:
                                visited.add(nbr)
                                q.append(nbr)

            if not comp_mkts:
                continue
            has_cross_market_edge = any(e.source_market_id != e.target_market_id for e in comp_edges.values())
            has_holding = any(mid in recyclable_by_mkt for mid in comp_mkts)
            if len(comp_mkts) == 1 and not has_cross_market_edge and not include_single_market_binaries and not has_holding:
                continue

            sorted_mids = tuple(sorted(comp_mkts))
            inst_ids: List[str] = []
            ev_ids: Set[str] = set()
            hold_ids: List[str] = []
            for mid in sorted_mids:
                mn = self.markets[mid]
                inst_ids.extend(mn.instrument_ids)
                if mn.event_id:
                    ev_ids.add(mn.event_id)
                hold_ids.extend(recyclable_by_mkt.get(mid, ()))

            sorted_edges = tuple(sorted(comp_edges.values(), key=lambda e: e.edge_id))
            etypes = tuple(sorted({e.edge_type.value for e in sorted_edges}))
            cid_hash = hashlib.sha256(",".join(sorted_mids).encode("utf-8")).hexdigest()[:12]
            components.append(
                ConnectedMarketComponent(
                    component_id=f"COMP_{cid_hash}",
                    market_ids=sorted_mids,
                    instrument_ids=tuple(dict.fromkeys(inst_ids)),
                    event_ids=tuple(sorted(ev_ids)),
                    edge_types_present=etypes,
                    edges=sorted_edges,
                    recyclable_holding_ids=tuple(sorted(set(hold_ids))),
                )
            )

        components.sort(key=lambda c: (-len(c.market_ids), c.component_id))
        return components

    def get_component_for_market(
        self,
        market_id: str,
        *,
        allowed_edge_types: Sequence[EdgeType] = (
            EdgeType.OFFICIAL_CONTRACTUAL,
            EdgeType.VERIFIED_MATHEMATICAL,
        ),
    ) -> Optional[ConnectedMarketComponent]:
        if market_id not in self.markets:
            return None
        comps = self.get_connected_components(
            allowed_edge_types=allowed_edge_types,
            only_market_ids={market_id},
            include_single_market_binaries=True,
            only_orderbook_enabled=False,
        )
        return comps[0] if comps else None

    def get_edges_for_market(
        self,
        market_id: str,
        *,
        edge_types: Optional[Sequence[EdgeType]] = None,
    ) -> List[PropositionEdge]:
        allowed = {EdgeType(et) if not isinstance(et, EdgeType) else et for et in edge_types} if edge_types else None
        out: List[PropositionEdge] = []
        for eid in self._edges_by_market.get(market_id, ()):
            ed = self.edges.get(eid)
            if ed is not None and (allowed is None or ed.edge_type in allowed):
                out.append(ed)
        out.sort(key=lambda e: e.edge_id)
        return out

    def summary_metrics(self) -> Dict[str, Any]:
        """Returns exact graph coverage & relationship metrics for `FULL_THROTTLE_DASHBOARD.md`."""
        by_type: Dict[str, int] = {et.value: 0 for et in EdgeType}
        by_kind: Dict[str, int] = {rk.value: 0 for rk in RelationKind}
        cross_market_edges = 0
        for ed in self.edges.values():
            by_type[ed.edge_type.value] = by_type.get(ed.edge_type.value, 0) + 1
            by_kind[ed.relation_kind.value] = by_kind.get(ed.relation_kind.value, 0) + 1
            if ed.source_market_id != ed.target_market_id:
                cross_market_edges += 1

        multi_mkt_comps = self.get_connected_components(
            allowed_edge_types=(EdgeType.OFFICIAL_CONTRACTUAL, EdgeType.VERIFIED_MATHEMATICAL),
            include_single_market_binaries=False,
        )
        return {
            "total_events": len(self.events),
            "total_markets": len(self.markets),
            "orderbook_enabled_markets": sum(1 for m in self.markets.values() if m.enable_order_book),
            "total_instruments": len(self.instruments),
            "total_edges": len(self.edges),
            "cross_market_edges": cross_market_edges,
            "edges_by_type": by_type,
            "edges_by_relation_kind": by_kind,
            "verified_multi_market_components": len(multi_mkt_comps),
            "recyclable_holdings_count": len(self.get_recyclable_holdings()),
            "frozen_disputed_holdings_quarantined": len(self.get_frozen_holdings()),
        }

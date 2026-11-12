#!/usr/bin/env python3
"""
Polymarket Directional Alpha — Live Multi-Strategy Shadow Signal Engine (`Phase 2`)
===================================================================================
Lightweight, bounded-memory (`< 15 MiB` overhead), strictly causal, zero-credential live
signal engine evaluating the **7 locked roadmap candidate sleeves** (`M_internal = 1` per
sleeve) against real live Polymarket two-sided L2 order books in `shadow_runner.py`.

Locked 7-Sleeve Candidate Portfolio (`#28`, `#29`, `#30`, `#33` & `Deliverable G`):
  1. `P3_LIQUIDITY_SHOCK_SNAPBACK__HOLD` (`Tier 1 Validated`, `@red-team == CLEARED`)
  2. `P1_SHORT_OVERREACTION_REVERSION__HOLD` (`Tier 1 Validated`, `@red-team == CLEARED`)
  3. `HYP_012R_ZERO_PARAM_UP_SPIKE_FADE__HOLD` (`EXP-DIR-02`: `p_hat = p_mkt - 0.35 * max(0, dp_4h - 0.12)`)
  4. `HYP_007R_AUGMENTED_CONTENDER_NO__HOLD` (`EXP-DIR-03`: `>= 5`-leg `negRiskAugmented` contender `BUY NO`)
  5. `HYP_023_WEATHER_HORIZON_ROUNDING__HOLD` (`EXP-DIR-03`: narrow temp bucket `BUY NO`, `D-001` + `D-006`)
  6. `HYP_018_SEMANTIC_POLARITY_AWARE__HOLD` (`EXP-DIR-01`: negated status-quo `BUY YES` at `88c–95c`)
  7. `ZERO_FEE_LIVE_L2_OBI_SNAPBACK__PRE_EXIT` (`EXP-DIR-06` + `EXP-DIR-08`: `0%`-fee Geopolitics/Politics/Macro
     live Top-5 L2 OBI + snapback `PRE_RESOLUTION_EXIT`)

Hard Safety & Swapless Host Invariants (`AGENTS.md` / `D-001` / `D-006` / `D-009` / `D-010`):
  - STRICT RESEARCH ONLY: Zero live orders, zero credential/env access, read-only public REST only.
  - `PERM_KMIA_D001_PROTECTED_LOCK`: Hard-blocks `KMIA` market IDs `6707502` and `6707503` across all sleeves.
  - `FIND-RT02-002` Thin-Book & Quote-Pull Guard: Requires `volume_usd >= $5,000` AND genuine observed
    two-sided live L2 depth (`best_bid < best_ask`, executable L1 & 5c depth, bounded spread) on every signal.
  - Swapless Memory Fence (`< 15 MiB` overhead): `__slots__` ring-buffers bounded to `<= 500` LRU markets
    x `<= 64` observations (`collections.deque(maxlen=64)`) + bounded event/cooldown tables.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import re
import statistics
import time
from typing import Any, Callable, Deque, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import urllib.parse
import urllib.request

try:
    import aiohttp as _aiohttp
except ImportError:  # pragma: no cover - stdlib urllib fallback for LibreOffice Python
    _aiohttp = None  # type: ignore[assignment]

try:
    import orjson as _orjson
except ImportError:  # pragma: no cover
    _orjson = None  # type: ignore[assignment]

try:
    from src.directional_alpha.execution_microstructure import (
        FeeSchedule,
        MIN_CLOB_MARKETABLE_NOTIONAL_USD,
        MIN_CLOB_ORDER_SHARES,
        normalize_category_name,
        resolve_fee_schedule,
        resolve_tick_size,
        round_price_to_tick,
        validate_and_quantize_order_lot,
    )
    from src.directional_alpha.portfolio_allocation import uncertainty_penalized_kelly_binary
    from src.directional_alpha.shadow_runner import (
        CLOB_HOST,
        FROZEN_KMIA_MARKET_IDS,
        ShadowSignalIntent,
        ShadowStrategyFn,
        assert_public_readonly_request,
        reclaim_unused_heap,
    )
except ImportError:
    from directional_alpha.execution_microstructure import (
        FeeSchedule,
        MIN_CLOB_MARKETABLE_NOTIONAL_USD,
        MIN_CLOB_ORDER_SHARES,
        normalize_category_name,
        resolve_fee_schedule,
        resolve_tick_size,
        round_price_to_tick,
        validate_and_quantize_order_lot,
    )
    from directional_alpha.portfolio_allocation import uncertainty_penalized_kelly_binary
    from directional_alpha.shadow_runner import (
        CLOB_HOST,
        FROZEN_KMIA_MARKET_IDS,
        ShadowSignalIntent,
        ShadowStrategyFn,
        assert_public_readonly_request,
        reclaim_unused_heap,
    )

# Alias supporting both `ShadowSignalIntent` (`shadow_runner.py`) and `SignalCandidate` (`#33`) naming
SignalCandidate = ShadowSignalIntent

# Canonical locked Phase-2 sleeve identifiers (exact priority order 1..7, M_internal = 1 per sleeve)
SLEEVE_P3_SHOCK_HOLD = "P3_LIQUIDITY_SHOCK_SNAPBACK__HOLD"
SLEEVE_P1_OVERREACTION_HOLD = "P1_SHORT_OVERREACTION_REVERSION__HOLD"
SLEEVE_HYP012R_UPSPIKE_HOLD = "HYP_012R_ZERO_PARAM_UP_SPIKE_FADE__HOLD"
SLEEVE_HYP007R_AUGMENTED_NO_HOLD = "HYP_007R_AUGMENTED_CONTENDER_NO__HOLD"
SLEEVE_HYP023_WEATHER_HOLD = "HYP_023_WEATHER_HORIZON_ROUNDING__HOLD"
SLEEVE_HYP018_POLARITY_HOLD = "HYP_018_SEMANTIC_POLARITY_AWARE__HOLD"
SLEEVE_ZERO_FEE_L2_OBI_PRE_EXIT = "ZERO_FEE_LIVE_L2_OBI_SNAPBACK__PRE_EXIT"

LOCKED_SLEEVE_IDS: Tuple[str, ...] = (
    SLEEVE_P3_SHOCK_HOLD,
    SLEEVE_P1_OVERREACTION_HOLD,
    SLEEVE_HYP012R_UPSPIKE_HOLD,
    SLEEVE_HYP007R_AUGMENTED_NO_HOLD,
    SLEEVE_HYP023_WEATHER_HOLD,
    SLEEVE_HYP018_POLARITY_HOLD,
    SLEEVE_ZERO_FEE_L2_OBI_PRE_EXIT,
)

# Category depth-concavity optimal clip caps Q_cap* from Deliverable G (`portfolio_allocation_results.json`)
CATEGORY_CLIP_CAP_USD: Dict[str, float] = {
    "weather": 30.96,
    "crypto": 79.61,
    "politics": 194.02,
    "geopolitics": 194.02,
    "economics": 194.02,
    "macro": 194.02,
    "economics_macro": 194.02,
    "finance": 125.00,
    "tech": 125.00,
    "tech_ai": 125.00,
    "culture": 125.00,
    "culture_science": 125.00,
    "science": 125.00,
    "sports": 450.00,
    "other": 125.00,
}

NARRATIVE_CATEGORIES = frozenset(
    {"politics", "geopolitics", "culture", "culture_science", "tech", "tech_ai", "science", "entertainment"}
)
ZERO_FEE_PRE_EXIT_CATEGORIES = frozenset(
    {"geopolitics", "politics", "economics", "macro", "economics_macro"}
)

# Regex extractors compiled once at import time (`0` per-cycle regex compilation overhead)
_NEGATION_RE = re.compile(
    r"(?:\bwill\b[^?]{0,80}\bnot\b|\bwon['’]?t\b|\bwill\s+no\b|\bwill\s+there\s+be\s+no\b|"
    r"\bfail(?:s|ed)?\s+to\b|\bwithout\b|\bnever\b|\bnobody\b|\bno\s+one\b)",
    re.IGNORECASE,
)
_FALSE_NEGATION_RE = re.compile(r"\bnot\s+only\b", re.IGNORECASE)

_OTHER_PLACEHOLDER_RE = re.compile(
    r"(?:^\s*other\s*$|\bany\s+other\b|\bnone\s+of\s+the\s+above\b|\bsomeone\s+else\b|"
    r"\banother\s+(?:candidate|person|team|party|player|coach|company)\b|\bplaceholder\b|"
    r"\bperson\s+[a-z]\b|\bcandidate\s+[a-z]\b|\bthe\s+field\b)",
    re.IGNORECASE,
)
_AUGMENTED_HINT_RE = re.compile(
    r"\b(?:next\s+pope|next\s+ceo|who\s+will\s+be\s+(?:appointed|named|nominated|selected|elected)|"
    r"acquire|buy\s+tiktok|nobel|person\s+of\s+the\s+year|oscars?|grammys?|champion|winner\s+of)\b",
    re.IGNORECASE,
)
_TEMP_RANGE_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*°?\s*([fc])?\s*(?:to|[-–]|and)\s*(-?\d+(?:\.\d+)?)\s*°?\s*([fc])\b",
    re.IGNORECASE,
)
_TEMP_OPEN_TAIL_RE = re.compile(
    r"\b(?:or\s+(?:higher|more|above|greater|warmer|lower|less|below|colder)|"
    r"(?:above|over|at\s+least|higher\s+than|below|under|at\s+most|lower\s+than)\s*-?\d+)\b",
    re.IGNORECASE,
)
_TEMP_EXACT_UNIT_RE = re.compile(
    r"\b(?:be|reach|hit)\s+(-?\d+(?:\.\d+)?)\s*°\s*([fc])\b",
    re.IGNORECASE,
)
_ASOS_MAINT_TOKEN_RE = re.compile(r"(?:\bRMK\b.*\$\s*$|\bMAINT(?:ENANCE)?\b|\bSENSOR\s+OUTAGE\b)", re.IGNORECASE)
_ICAO_STATION_RE = re.compile(r"\b(K[A-Z]{3}|E[A-Z]{3}|L[A-Z]{3}|R[A-Z]{3}|C[A-Z]{3}|Y[A-Z]{3}|S[A-Z]{3})\b")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def _logit(p: float, eps: float = 1e-5) -> float:
    pc = _clamp(p, eps, 1.0 - eps)
    return math.log(pc / (1.0 - pc))


def _sigmoid(z: float) -> float:
    if z >= 0.0:
        ez = math.exp(-min(float(z), 60.0))
        return 1.0 / (1.0 + ez)
    ez = math.exp(max(float(z), -60.0))
    return ez / (1.0 + ez)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(float(z) * 0.7071067811865475))


def _to_celsius(val: float, unit: str) -> float:
    if unit.strip().upper().startswith("F"):
        return (float(val) - 32.0) * (5.0 / 9.0)
    return float(val)


def detect_semantic_negation(question: str) -> bool:
    """Detects inverted status-quo polarity ('Will X NOT happen?') while excluding 'not only'."""
    q = str(question or "").strip()
    if not q or _FALSE_NEGATION_RE.search(q):
        return False
    return bool(_NEGATION_RE.search(q))


def detect_other_or_placeholder(question: str, slug: str = "", group_item_title: str = "") -> bool:
    """Detects `negRiskAugmented` 'Other' / unnamed catch-all legs (`RT-04` protection)."""
    for txt in (group_item_title, question, slug.replace("-", " ")):
        s = str(txt or "").strip()
        if s and _OTHER_PLACEHOLDER_RE.search(s):
            return True
    return False


def parse_narrow_temperature_bucket_celsius(question: str) -> Optional[Tuple[float, float]]:
    """Extracts narrow closed temperature bucket `(lo_c, hi_c)` in Celsius (`width <= 2.6°C`).

    - Explicit narrow ranges (`"68°F to 69°F"` -> `[67.5°F, 69.5°F]` integer rounding interval).
    - Exact single-degree buckets (`"be 18°C on"` -> `[17.5°C, 18.5°C]`).
    - Strictly excludes open-ended tails (`"72°F or higher"`, `"below 10°C"`).
    """
    q = str(question or "")
    if not q or _TEMP_OPEN_TAIL_RE.search(q):
        return None

    m_rng = _TEMP_RANGE_RE.search(q)
    if m_rng:
        v1 = float(m_rng.group(1))
        u2 = (m_rng.group(4) or m_rng.group(2) or "C").upper()
        u1 = (m_rng.group(2) or u2).upper()
        v2 = float(m_rng.group(3))
        lo_raw, hi_raw = min(v1, v2), max(v1, v2)
        # Integer meteorological buckets include ±0.5 half-unit integer rounding bounds
        lo_c = _to_celsius(lo_raw - 0.5, u1)
        hi_c = _to_celsius(hi_raw + 0.5, u2)
        if 0.2 <= (hi_c - lo_c) <= 2.6:
            return (round(lo_c, 4), round(hi_c, 4))
        return None

    m_ex = _TEMP_EXACT_UNIT_RE.search(q)
    if m_ex:
        val = float(m_ex.group(1))
        unit = m_ex.group(2).upper()
        lo_c = _to_celsius(val - 0.5, unit)
        hi_c = _to_celsius(val + 0.5, unit)
        if 0.2 <= (hi_c - lo_c) <= 2.6:
            return (round(lo_c, 4), round(hi_c, 4))
    return None


def parse_end_epoch(snap: Mapping[str, Any]) -> Optional[float]:
    """Parses scheduled contract expiration epoch from numeric or ISO-8601 Gamma fields."""
    for k in ("end_ts", "scheduled_end_ts", "end_epoch"):
        v = snap.get(k)
        if v is not None:
            try:
                fv = float(v)
                if fv > 1_000_000_000.0:
                    return fv
            except (TypeError, ValueError):
                pass
    for k in ("end_date_iso", "endDate", "endDateIso"):
        raw = snap.get(k)
        if isinstance(raw, str) and len(raw) >= 10:
            try:
                s = raw.strip().replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except ValueError:
                continue
    return None


def enrich_watchlist_metadata_from_gamma(
    raw_market: Mapping[str, Any],
    raw_event: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Extracts slim (`< 200B`) directional metadata from raw Gamma market/event dicts (`F-01` safe)."""
    ev = raw_event or {}
    ev_mkts = ev.get("markets")
    ev_cnt = int(ev.get("totalMarketCount") or (len(ev_mkts) if isinstance(ev_mkts, list) else 1) or 1)
    q_txt = str(raw_market.get("question") or "")[:140]
    grp_title = str(raw_market.get("groupItemTitle") or "")[:64]
    slug = str(raw_market.get("slug") or "")[:96]
    end_ep = parse_end_epoch(raw_market) or parse_end_epoch(ev)
    return {
        "volume_usd": float(raw_market.get("volumeNum") or raw_market.get("volume") or 0.0),
        "volume_24hr_usd": float(raw_market.get("volume24hr") or 0.0),
        "end_ts": end_ep,
        "neg_risk": bool(raw_market.get("negRisk") or ev.get("negRisk")),
        "neg_risk_augmented": bool(
            raw_market.get("negRiskAugmented")
            or ev.get("negRiskAugmented")
            or ev.get("enableNegRisk") and bool(raw_market.get("negRiskOther"))
        ),
        "event_market_count": max(1, ev_cnt),
        "fees_enabled": raw_market.get("feesEnabled"),
        "group_item_title": grp_title,
        "has_negation": detect_semantic_negation(q_txt),
        "is_other_or_placeholder": bool(raw_market.get("negRiskOther"))
        or detect_other_or_placeholder(q_txt, slug, grp_title),
    }


# ==============================================================================
# COMPACT SWAPLESS RING-BUFFER STRUCTURES (`__slots__`, `< 15 MiB` GUARANTEED)
# ==============================================================================


@dataclass(slots=True)
class _CompactObs:
    ts_epoch: float
    mid_px: float
    best_bid: float
    best_ask: float
    obi_5c: float
    top5_obi: float
    is_live_l2: bool


@dataclass(slots=True)
class _MarketRingState:
    obs: Deque[_CompactObs]
    last_live_cycle_idx: int
    bootstrapped_points: int


@dataclass(slots=True)
class _EventLegQuote:
    mid_px: float
    ts_epoch: float
    is_other: bool
    temp_mid_c: Optional[float]


@dataclass(slots=True)
class WeatherStationForecast:
    forecast_high_c: float
    updated_epoch: float
    obs_max_so_far_c: Optional[float] = None
    has_maintenance_flag: bool = False
    metar_raw: str = ""


@dataclass
class LiveSignalConfig:
    """Configuration for `LiveDirectionalSignalSuite` (locked defaults match Roadmap Stage 1/2)."""

    virtual_bankroll_usd: float = 500.0
    kelly_multiplier: float = 0.25
    ambiguity_z: float = 0.50
    shrinkage_eta: float = 0.50
    max_event_concentration_pct: float = 0.15
    min_volume_usd: float = 5000.0
    min_l1_depth_usd: float = 10.0
    min_5c_depth_usd: float = 25.0
    max_spread_px: float = 0.040
    max_markets: int = 500
    max_obs_per_market: int = 64
    max_events_tracked: int = 250
    per_market_cooldown_sec: float = 1800.0
    assumed_cycle_interval_sec: float = 60.0
    allow_liquidity_volume_proxy_when_missing: bool = True


# ==============================================================================
# MAIN LIVE MULTI-STRATEGY SHADOW SIGNAL SUITE
# ==============================================================================


class LiveDirectionalSignalSuite:
    """
    Evaluates all 7 locked directional shadow sleeves over bounded in-memory price/L2 ring-buffers.

    Compatible with `ForwardShadowRunner` (`shadow_runner.py`) in two ways:
      1. `ForwardShadowRunner(config=cfg, strategies=suite.as_strategy_functions())` (recommended:
         registers 1 named `ShadowStrategyFn` per locked sleeve in exact priority order `1..7`).
      2. `ForwardShadowRunner(config=cfg, strategies=[suite])` (`suite(snap, history)` evaluates
         all 7 sleeves in priority order and returns matching `ShadowSignalIntent` objects).
    """

    def __init__(self, config: Optional[LiveSignalConfig] = None) -> None:
        self.config = config or LiveSignalConfig()
        self._max_markets = max(16, min(2000, int(self.config.max_markets)))
        self._max_obs = max(16, min(128, int(self.config.max_obs_per_market)))
        self._max_events = max(32, min(1000, int(self.config.max_events_tracked)))

        self._rings: "OrderedDict[str, _MarketRingState]" = OrderedDict()
        self._event_slates: "OrderedDict[str, Dict[str, _EventLegQuote]]" = OrderedDict()
        self._event_declared_counts: "OrderedDict[str, int]" = OrderedDict()
        self._cooldown_until: "OrderedDict[Tuple[str, str], float]" = OrderedDict()
        self._weather_forecasts: Dict[str, WeatherStationForecast] = {}
        self._clock_override_epoch: Optional[float] = None

        self._sleeve_stats: Dict[str, Dict[str, Any]] = {
            sid: {
                "evaluated": 0,
                "rejected_safety_or_liquidity": 0,
                "rejected_edge_or_lot": 0,
                "signals_emitted": 0,
                "last_signal_utc": None,
                "last_market_id": None,
            }
            for sid in LOCKED_SLEEVE_IDS
        }
        self._cold_bootstrapped_markets: int = 0

    # ------------------------------------------------------------------
    # Optional Clock, Weather Forecast, & Pre-Cycle Slate Context Hooks
    # ------------------------------------------------------------------

    def set_clock_epoch(self, now_epoch: Optional[float]) -> None:
        """Sets deterministic evaluation epoch (used in offline replay & unit tests; `None` = wall clock)."""
        self._clock_override_epoch = float(now_epoch) if now_epoch is not None else None

    def _now_epoch(self, snap: Optional[Mapping[str, Any]] = None) -> float:
        if snap is not None:
            for k in ("observed_epoch", "now_epoch", "ts_epoch"):
                v = snap.get(k)
                if v is not None:
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        pass
        if self._clock_override_epoch is not None:
            return self._clock_override_epoch
        return time.time()

    def set_weather_forecast(
        self,
        key: str,
        forecast_high_c: float,
        *,
        obs_max_so_far_c: Optional[float] = None,
        has_maintenance_flag: bool = False,
        metar_raw: str = "",
        updated_epoch: Optional[float] = None,
    ) -> None:
        """Registers external read-only NWP / station forecast (`key` = `market_id`, `event_id`, or ICAO like `'EGLL'`)."""
        norm_k = str(key or "").strip().upper()
        if not norm_k or norm_k in FROZEN_KMIA_MARKET_IDS:
            return
        if len(self._weather_forecasts) >= 256 and norm_k not in self._weather_forecasts:
            oldest_k = next(iter(self._weather_forecasts))
            del self._weather_forecasts[oldest_k]
        self._weather_forecasts[norm_k] = WeatherStationForecast(
            forecast_high_c=float(forecast_high_c),
            updated_epoch=float(updated_epoch if updated_epoch is not None else self._now_epoch()),
            obs_max_so_far_c=float(obs_max_so_far_c) if obs_max_so_far_c is not None else None,
            has_maintenance_flag=bool(has_maintenance_flag),
            metar_raw=str(metar_raw or "")[:160],
        )

    def ingest_watchlist_context(
        self,
        watchlist: Sequence[Mapping[str, Any]],
        books_by_market_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
        now_epoch: Optional[float] = None,
    ) -> None:
        """Pre-indexes multi-leg event counts & sibling midpoints before a `step_cycle` pass."""
        ts_now = float(now_epoch if now_epoch is not None else self._now_epoch())
        counts_in_batch: Dict[str, int] = {}
        for m in watchlist:
            mid = str(m.get("market_id") or "")
            if not mid or mid in FROZEN_KMIA_MARKET_IDS:
                continue
            ev_id = str(m.get("event_id") or mid)
            counts_in_batch[ev_id] = counts_in_batch.get(ev_id, 0) + 1
            decl = int(m.get("event_market_count") or 0)
            self._record_event_declared_count(ev_id, max(counts_in_batch[ev_id], decl))

            if books_by_market_id is not None:
                b = books_by_market_id.get(mid)
                if isinstance(b, Mapping):
                    bids = b.get("bids") or []
                    asks = b.get("asks") or []
                    if bids and asks and float(asks[0]["price"]) > float(bids[0]["price"]):
                        mid_px = 0.5 * (float(bids[0]["price"]) + float(asks[0]["price"]))
                        self._update_event_leg_quote(ev_id, mid, m, mid_px, ts_now)

    # ------------------------------------------------------------------
    # Cold-Start CLOB `/prices-history` Bootstrapper (Read-Only Public GET)
    # ------------------------------------------------------------------

    def seed_market_history(
        self,
        market_id: str,
        points: Iterable[Tuple[float, float]],
        *,
        now_epoch: Optional[float] = None,
    ) -> int:
        """Seeds strictly pre-now `(ts_epoch, mid_px)` history into bounded ring-buffer (`<= max_obs - 1`)."""
        mid = str(market_id or "").strip()
        if not mid or mid in FROZEN_KMIA_MARKET_IDS:
            return 0
        cutoff = float(now_epoch if now_epoch is not None else self._now_epoch())
        cleaned: List[Tuple[float, float]] = []
        for ts_raw, px_raw in points:
            try:
                ts_f = float(ts_raw)
                px_f = float(px_raw)
            except (TypeError, ValueError):
                continue
            if math.isnan(ts_f) or math.isnan(px_f):
                continue
            if ts_f > cutoff + 1.0 or not (0.001 <= px_f <= 0.999):
                continue
            cleaned.append((ts_f, px_f))
        if not cleaned:
            return 0
        cleaned.sort(key=lambda item: item[0])

        # Deduplicate timestamps & keep at most `max_obs - 1` points so Cycle 1 live L2 tick fits cleanly
        keep_cap = max(8, self._max_obs - 1)
        dedup: List[Tuple[float, float]] = []
        last_t = -1.0
        for ts_f, px_f in cleaned:
            if ts_f > last_t + 1e-6:
                dedup.append((ts_f, px_f))
                last_t = ts_f
        dedup = dedup[-keep_cap:]

        ring = self._get_or_create_ring(mid)
        # Preserve any newer live L2 observations already recorded
        existing_live = [o for o in ring.obs if o.is_live_l2 and o.ts_epoch > dedup[-1][0]]
        ring.obs.clear()
        for ts_f, px_f in dedup:
            ring.obs.append(
                _CompactObs(
                    ts_epoch=ts_f,
                    mid_px=round(px_f, 6),
                    best_bid=round(max(0.001, px_f - 0.005), 6),
                    best_ask=round(min(0.999, px_f + 0.005), 6),
                    obi_5c=0.0,
                    top5_obi=0.0,
                    is_live_l2=False,
                )
            )
        for live_obs in existing_live:
            ring.obs.append(live_obs)
        ring.bootstrapped_points = len(dedup)
        return len(dedup)

    def bootstrap_from_payloads(
        self,
        payloads_by_market_id: Mapping[str, Any],
        *,
        now_epoch: Optional[float] = None,
    ) -> int:
        """Parses CLOB `/prices-history` JSON payloads (`{'history': [{'t': ..., 'p': ...}]}`) offline."""
        seeded_markets = 0
        for mid, payload in payloads_by_market_id.items():
            if not isinstance(payload, Mapping):
                continue
            hist_arr = payload.get("history")
            if not isinstance(hist_arr, list):
                continue
            pts: List[Tuple[float, float]] = []
            for row in hist_arr:
                if isinstance(row, Mapping) and "t" in row and "p" in row:
                    try:
                        pts.append((float(row["t"]), float(row["p"])))
                    except (TypeError, ValueError):
                        continue
            if self.seed_market_history(str(mid), pts, now_epoch=now_epoch) > 0:
                seeded_markets += 1
        self._cold_bootstrapped_markets += seeded_markets
        return seeded_markets

    async def bootstrap_from_clob_prices_history(
        self,
        watchlist: Sequence[Mapping[str, Any]],
        *,
        interval: str = "1d",
        fidelity_min: int = 15,
        concurrency: int = 8,
        timeout_sec: float = 8.0,
        now_epoch: Optional[float] = None,
        fetcher: Optional[Callable[[str], Any]] = None,
    ) -> Dict[str, Any]:
        """Cold-bootstraps bounded ring-buffers from public read-only `GET https://clob.polymarket.com/prices-history`.

        Enables `P3_LIQUIDITY_SHOCK_SNAPBACK__HOLD`, `P1_SHORT_OVERREACTION_REVERSION__HOLD`, and
        `HYP_012R_ZERO_PARAM_UP_SPIKE_FADE__HOLD` (`dp_4h`) to evaluate immediately on Cycle 1
        without waiting 4 hours after daemon startup, while still requiring real live L2 books to trade.
        """
        t0 = time.perf_counter()
        cur_ep = float(now_epoch if now_epoch is not None else self._now_epoch())
        targets: List[Tuple[str, str]] = []
        for m in watchlist[: self._max_markets]:
            mid = str(m.get("market_id") or "").strip()
            tok = str(m.get("yes_token_id") or "").strip()
            if not mid or not tok or mid in FROZEN_KMIA_MARKET_IDS:
                continue
            q_tok = urllib.parse.quote(tok, safe="")
            q_int = urllib.parse.quote(str(interval), safe="")
            url = f"https://{CLOB_HOST}/prices-history?market={q_tok}&interval={q_int}&fidelity={max(1, int(fidelity_min))}"
            assert_public_readonly_request("GET", url)
            targets.append((mid, url))

        sem = asyncio.Semaphore(max(1, min(12, int(concurrency))))
        payloads: Dict[str, Any] = {}

        if fetcher is not None:
            async def _run_custom(m_id: str, u: str) -> None:
                async with sem:
                    assert_public_readonly_request("GET", u)
                    res = fetcher(u)
                    if asyncio.iscoroutine(res):
                        res = await res
                    if isinstance(res, Mapping):
                        payloads[m_id] = res

            await asyncio.gather(*(_run_custom(m_id, u) for m_id, u in targets))
        elif _aiohttp is not None:
            conn = _aiohttp.TCPConnector(limit=max(2, min(10, int(concurrency))))
            headers = {"User-Agent": "DominusShadowResearch/1.0", "Accept": "application/json"}
            async with _aiohttp.ClientSession(connector=conn, headers=headers, trust_env=False) as session:
                async def _fetch_aio(m_id: str, u: str) -> None:
                    async with sem:
                        assert_public_readonly_request("GET", u)
                        try:
                            async with session.get(u, timeout=_aiohttp.ClientTimeout(total=float(timeout_sec))) as resp:
                                if resp.status == 200:
                                    raw = await resp.read()
                                    obj = _orjson.loads(raw) if _orjson is not None else json.loads(raw.decode("utf-8"))
                                    if isinstance(obj, Mapping):
                                        payloads[m_id] = obj
                        except Exception:
                            return

                await asyncio.gather(*(_fetch_aio(m_id, u) for m_id, u in targets))
        else:
            async def _fetch_urllib(m_id: str, u: str) -> None:
                async with sem:
                    obj = await asyncio.to_thread(self._urllib_get_json, u, float(timeout_sec))
                    if isinstance(obj, Mapping):
                        payloads[m_id] = obj

            await asyncio.gather(*(_fetch_urllib(m_id, u) for m_id, u in targets))

        seeded = self.bootstrap_from_payloads(payloads, now_epoch=cur_ep)
        reclaim_unused_heap()
        return {
            "requested_markets": len(targets),
            "seeded_markets": seeded,
            "total_buffered_observations": self.total_buffered_observations(),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    @staticmethod
    def _urllib_get_json(url: str, timeout_sec: float = 8.0) -> Any:
        assert_public_readonly_request("GET", url)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "DominusShadowResearch/1.0", "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as r:
                raw = r.read()
                return _orjson.loads(raw) if _orjson is not None else json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Ring-Buffer Management & Bounded Memory Accounting
    # ------------------------------------------------------------------

    def _get_or_create_ring(self, market_id: str) -> _MarketRingState:
        ring = self._rings.get(market_id)
        if ring is not None:
            self._rings.move_to_end(market_id)
            return ring
        while len(self._rings) >= self._max_markets:
            self._rings.popitem(last=False)
        ring = _MarketRingState(
            obs=deque(maxlen=self._max_obs),
            last_live_cycle_idx=-999_999,
            bootstrapped_points=0,
        )
        self._rings[market_id] = ring
        return ring

    def _record_event_declared_count(self, event_id: str, count: int) -> None:
        if not event_id:
            return
        prev = self._event_declared_counts.get(event_id, 0)
        self._event_declared_counts[event_id] = max(prev, int(count))
        self._event_declared_counts.move_to_end(event_id)
        while len(self._event_declared_counts) > self._max_events:
            self._event_declared_counts.popitem(last=False)

    def _update_event_leg_quote(
        self,
        event_id: str,
        market_id: str,
        meta: Mapping[str, Any],
        mid_px: float,
        ts_epoch: float,
    ) -> None:
        if not event_id or market_id in FROZEN_KMIA_MARKET_IDS:
            return
        slate = self._event_slates.get(event_id)
        if slate is None:
            while len(self._event_slates) >= self._max_events:
                self._event_slates.popitem(last=False)
            slate = {}
            self._event_slates[event_id] = slate
        else:
            self._event_slates.move_to_end(event_id)

        if len(slate) >= 40 and market_id not in slate:
            oldest_m = min(slate.items(), key=lambda kv: kv[1].ts_epoch)[0]
            del slate[oldest_m]

        q_txt = str(meta.get("question") or "")
        slug = str(meta.get("slug") or "")
        grp = str(meta.get("group_item_title") or meta.get("groupItemTitle") or "")
        is_oth = bool(meta.get("is_other_or_placeholder")) or detect_other_or_placeholder(q_txt, slug, grp)
        rng_c = parse_narrow_temperature_bucket_celsius(q_txt)
        t_mid = 0.5 * (rng_c[0] + rng_c[1]) if rng_c is not None else None
        slate[market_id] = _EventLegQuote(
            mid_px=round(float(mid_px), 6),
            ts_epoch=float(ts_epoch),
            is_other=is_oth,
            temp_mid_c=t_mid,
        )

    @staticmethod
    def _compute_top5_obi(yes_book: Mapping[str, Any]) -> Tuple[float, float, float]:
        bids = (yes_book.get("bids") or [])[:5]
        asks = (yes_book.get("asks") or [])[:5]
        b_usd = sum(float(x.get("price", 0.0)) * float(x.get("size", 0.0)) for x in bids)
        a_usd = sum(float(x.get("price", 0.0)) * float(x.get("size", 0.0)) for x in asks)
        denom = b_usd + a_usd
        obi = (b_usd - a_usd) / denom if denom > 1e-6 else 0.0
        return round(obi, 6), round(b_usd, 4), round(a_usd, 4)

    def _sync_live_observation(
        self,
        snap: Mapping[str, Any],
        history: Sequence[Mapping[str, Any]],
        cur_epoch: float,
    ) -> _MarketRingState:
        """Records `(snap, history)` into the market's bounded ring-buffer once per cycle."""
        mid = str(snap["market_id"])
        ring = self._get_or_create_ring(mid)

        # Determine cycle index from `history[-1]` if provided by `ForwardShadowRunner`
        cur_cycle_idx = -1
        if history:
            last_h = history[-1]
            if isinstance(last_h, Mapping) and "cycle_idx" in last_h:
                try:
                    cur_cycle_idx = int(last_h["cycle_idx"])
                except (TypeError, ValueError):
                    cur_cycle_idx = -1

        # Backfill synthetic/runner `history` priors if ring was empty (stateless caller support)
        if len(ring.obs) == 0 and len(history) > 1:
            prior_items = list(history)[:-1][-(self._max_obs - 1) :]
            n_prior = len(prior_items)
            dt = max(1.0, float(self.config.assumed_cycle_interval_sec))
            for idx_p, h_item in enumerate(prior_items):
                if not isinstance(h_item, Mapping):
                    continue
                h_mid = float(h_item.get("mid_px") or snap.get("mid_px") or 0.5)
                if not (0.001 <= h_mid <= 0.999):
                    continue
                h_ts_raw = h_item.get("ts_epoch", h_item.get("ts"))
                h_ts = float(h_ts_raw) if h_ts_raw is not None else (cur_epoch - (n_prior - idx_p) * dt)
                h_bid = float(h_item.get("best_bid") or max(0.001, h_mid - 0.005))
                h_ask = float(h_item.get("best_ask") or min(0.999, h_mid + 0.005))
                h_obi = float(h_item.get("obi_5c") or 0.0)
                h_t5 = float(h_item.get("top5_obi") if h_item.get("top5_obi") is not None else h_obi)
                ring.obs.append(
                    _CompactObs(
                        ts_epoch=h_ts,
                        mid_px=round(h_mid, 6),
                        best_bid=round(h_bid, 6),
                        best_ask=round(h_ask, 6),
                        obi_5c=round(h_obi, 6),
                        top5_obi=round(h_t5, 6),
                        is_live_l2=bool(h_item.get("is_live_l2", True)),
                    )
                )

        # Deduplicate within the same cycle when all 7 per-sleeve callables run sequentially
        if cur_cycle_idx >= 0 and ring.last_live_cycle_idx == cur_cycle_idx and len(ring.obs) > 0:
            return ring
        if cur_cycle_idx < 0 and len(ring.obs) > 0 and ring.obs[-1].is_live_l2:
            if abs(cur_epoch - ring.obs[-1].ts_epoch) < 0.05 and abs(float(snap["mid_px"]) - ring.obs[-1].mid_px) < 1e-6:
                return ring

        yes_book = snap.get("yes_book") or {}
        top5_obi, _, _ = self._compute_top5_obi(yes_book) if isinstance(yes_book, Mapping) else (0.0, 0.0, 0.0)
        obs_ts = cur_epoch
        if len(ring.obs) > 0 and obs_ts <= ring.obs[-1].ts_epoch:
            obs_ts = ring.obs[-1].ts_epoch + 1.0

        ring.obs.append(
            _CompactObs(
                ts_epoch=obs_ts,
                mid_px=round(float(snap["mid_px"]), 6),
                best_bid=round(float(snap["best_bid"]), 6),
                best_ask=round(float(snap["best_ask"]), 6),
                obi_5c=round(float(snap.get("obi_5c") or 0.0), 6),
                top5_obi=top5_obi,
                is_live_l2=True,
            )
        )
        if cur_cycle_idx >= 0:
            ring.last_live_cycle_idx = cur_cycle_idx

        ev_id = str(snap.get("event_id") or mid)
        decl = int(snap.get("event_market_count") or 0)
        if decl > 0:
            self._record_event_declared_count(ev_id, decl)
        self._update_event_leg_quote(ev_id, mid, snap, float(snap["mid_px"]), obs_ts)
        return ring

    # ------------------------------------------------------------------
    # Shared Pre-Trade Safety, Volume, Live L2 Depth & UPK Sizing Gates
    # ------------------------------------------------------------------

    def _passes_common_market_gates(self, snap: Mapping[str, Any], cur_epoch: float) -> Tuple[bool, str]:
        mid = str(snap.get("market_id") or "").strip()
        if not mid or mid in FROZEN_KMIA_MARKET_IDS:
            return False, "D001_KMIA_PROTECTED_LOCK"

        q_low = f"{snap.get('slug', '')} {snap.get('question', '')}".lower()
        if "kmia" in q_low and ("november-7" in q_low or "november 7" in q_low or "nov-7" in q_low or "nov 7" in q_low):
            return False, "D001_KMIA_NOV7_LOCK"

        if bool(snap.get("closed")) or snap.get("accepting_orders") is False or snap.get("acceptingOrders") is False:
            return False, "MARKET_CLOSED_OR_NOT_ACCEPTING"

        uma_st = str(snap.get("uma_resolution_status") or "open").strip().lower()
        if uma_st in ("disputed", "resolved", "proposed"):
            return False, "POST_EXPIRY_UMA_STATUS"

        # Mandatory Volume >= $5,000 Gate (`FIND-RT02-002` + `#33`)
        explicit_vol: Optional[float] = None
        for vk in ("volume_usd", "volumeNum", "volume"):
            if vk in snap and snap.get(vk) is not None:
                try:
                    explicit_vol = float(snap[vk])
                    break
                except (TypeError, ValueError):
                    pass
        if explicit_vol is not None:
            if explicit_vol < float(self.config.min_volume_usd) - 1e-6:
                return False, "VOLUME_BELOW_5K_FLOOR"
        else:
            if not self.config.allow_liquidity_volume_proxy_when_missing:
                return False, "MISSING_EXPLICIT_VOLUME"
            liq_usd = float(snap.get("liquidity_usd") or 0.0)
            if liq_usd * 4.0 < float(self.config.min_volume_usd) - 1e-6:
                return False, "LIQUIDITY_PROXY_BELOW_5K_FLOOR"

        # Mandatory Observed Two-Sided Live L2 Book Gate
        yes_book = snap.get("yes_book")
        no_book = snap.get("no_book")
        if not isinstance(yes_book, Mapping) or not isinstance(no_book, Mapping):
            return False, "MISSING_L2_BOOK"
        y_bids = yes_book.get("bids") or []
        y_asks = yes_book.get("asks") or []
        if not y_bids or not y_asks:
            return False, "ONE_SIDED_L2_BOOK"

        best_bid = float(snap.get("best_bid") or y_bids[0].get("price", 0.0))
        best_ask = float(snap.get("best_ask") or y_asks[0].get("price", 1.0))
        spread_px = best_ask - best_bid
        mid_px = 0.5 * (best_bid + best_ask)
        if not (0.0 < best_bid < best_ask < 1.0) or spread_px > float(self.config.max_spread_px) + 1e-9:
            return False, "SPREAD_TOO_WIDE_OR_CROSSED"
        if not (0.02 <= mid_px <= 0.98):
            return False, "EXTREME_POST_CLINCH_PRICE"

        end_ep = parse_end_epoch(snap)
        if end_ep is not None and cur_epoch >= end_ep - 600.0:
            return False, "WITHIN_10M_EXPIRY_CUTOFF"

        return True, "OK"

    @staticmethod
    def _extract_side_l2_metrics(snap: Mapping[str, Any], side_label: str) -> Optional[Dict[str, float]]:
        side_u = side_label.upper()
        book = snap.get("yes_book") if side_u == "YES" else snap.get("no_book")
        if not isinstance(book, Mapping):
            return None
        bids = book.get("bids") or []
        asks = book.get("asks") or []
        if not bids or not asks:
            return None
        b0_px, b0_sz = float(bids[0]["price"]), float(bids[0]["size"])
        a0_px, a0_sz = float(asks[0]["price"]), float(asks[0]["size"])
        if not (0.0 < b0_px < a0_px < 1.0) or b0_sz <= 0.0 or a0_sz <= 0.0:
            return None
        bid_5c = sum(float(x["price"]) * float(x["size"]) for x in bids if float(x["price"]) >= b0_px - 0.05 + 1e-9)
        ask_5c = sum(float(x["price"]) * float(x["size"]) for x in asks if float(x["price"]) <= a0_px + 0.05 + 1e-9)
        return {
            "best_bid": round(b0_px, 6),
            "best_ask": round(a0_px, 6),
            "mid_px": round(0.5 * (b0_px + a0_px), 6),
            "spread_px": round(a0_px - b0_px, 6),
            "l1_bid_usd": round(b0_px * b0_sz, 4),
            "l1_ask_usd": round(a0_px * a0_sz, 4),
            "bid_5c_usd": round(bid_5c, 4),
            "ask_5c_usd": round(ask_5c, 4),
        }

    @staticmethod
    def _resolve_snap_fee_schedule(snap: Mapping[str, Any]) -> FeeSchedule:
        sched = snap.get("fee_schedule")
        if isinstance(sched, FeeSchedule):
            return sched
        return resolve_fee_schedule(
            market_meta=snap,
            category=str(snap.get("category") or ""),
            fees_enabled=snap.get("fees_enabled") if "fees_enabled" in snap else snap.get("feesEnabled"),
        )

    @staticmethod
    def _estimate_uma_dispute_prob(category_norm: str) -> float:
        if category_norm == "weather":
            return 0.0065
        if category_norm in ("crypto", "sports", "economics", "macro", "economics_macro", "finance"):
            return 0.0018
        return 0.0090

    def _size_and_build_intent(
        self,
        *,
        strategy_id: str,
        snap: Mapping[str, Any],
        side_label: str,
        p_yes_hat: float,
        sigma_p: float,
        min_net_edge_ps: float,
        exec_mode: str = "TAKER",
        limit_price: Optional[float] = None,
        exit_policy: str = "HOLD_TO_SETTLEMENT",
        target_exit_px: float = 0.88,
        stop_exit_px: float = 0.15,
        max_hold_sec: float = 86400.0,
        ttl_cycles: int = 3,
        cur_epoch: float,
        rationale: str,
    ) -> Optional[ShadowSignalIntent]:
        mid = str(snap["market_id"])
        cd_key = (strategy_id, mid)
        cd_until = self._cooldown_until.get(cd_key, 0.0)
        if cur_epoch < cd_until:
            self._sleeve_stats[strategy_id]["rejected_safety_or_liquidity"] += 1
            return None

        side_u = side_label.upper()
        q_txt = str(snap.get("question") or "")
        slug = str(snap.get("slug") or "")
        grp = str(snap.get("group_item_title") or snap.get("groupItemTitle") or "")
        is_other = bool(snap.get("is_other_or_placeholder")) or detect_other_or_placeholder(q_txt, slug, grp)
        if side_u == "YES" and is_other:
            self._sleeve_stats[strategy_id]["rejected_safety_or_liquidity"] += 1
            return None

        side_l2 = self._extract_side_l2_metrics(snap, side_u)
        if side_l2 is None:
            self._sleeve_stats[strategy_id]["rejected_safety_or_liquidity"] += 1
            return None

        # Verify real executable depth on the entry side AND two-sided opposing depth
        is_maker = exec_mode.upper() == "MAKER_POST_ONLY"
        if not is_maker:
            if (
                side_l2["l1_ask_usd"] < float(self.config.min_l1_depth_usd)
                or side_l2["ask_5c_usd"] < float(self.config.min_5c_depth_usd)
                or side_l2["bid_5c_usd"] < 12.0
            ):
                self._sleeve_stats[strategy_id]["rejected_safety_or_liquidity"] += 1
                return None
            entry_ref_px = side_l2["best_ask"]
            est_slip_ps = min(0.025, 0.002 + 0.004 * (15.0 / max(15.0, side_l2["ask_5c_usd"])))
        else:
            if side_l2["bid_5c_usd"] < 15.0 or side_l2["ask_5c_usd"] < 15.0 or limit_price is None:
                self._sleeve_stats[strategy_id]["rejected_safety_or_liquidity"] += 1
                return None
            entry_ref_px = float(limit_price)
            est_slip_ps = 0.0

        if not (0.015 <= entry_ref_px <= 0.975):
            self._sleeve_stats[strategy_id]["rejected_edge_or_lot"] += 1
            return None

        sched = self._resolve_snap_fee_schedule(snap)
        cat_norm = normalize_category_name(str(snap.get("category") or ""), f"{slug} {q_txt}")
        p_disp = self._estimate_uma_dispute_prob(cat_norm)

        # Evaluate net probability/trading edge & Quarter-Kelly (`0.25x` UPK) fraction
        upk = uncertainty_penalized_kelly_binary(
            p_yes_hat=_clamp(p_yes_hat, 0.002, 0.998),
            sigma_p=max(0.005, float(sigma_p)),
            entry_ask_price=entry_ref_px,
            side=side_u,
            question_is_negated=False,
            entry_slippage_per_share=est_slip_ps,
            fee_rate=sched.fee_rate,
            fee_exponent=sched.fee_exponent,
            is_maker_entry=is_maker,
            maker_rebate_rate=0.0,
            p_uma_dispute=p_disp if exit_policy == "HOLD_TO_SETTLEMENT" else (0.25 * p_disp),
            dispute_payout_per_share=0.0,
            kelly_multiplier=float(self.config.kelly_multiplier),
            ambiguity_z=float(self.config.ambiguity_z),
            shrinkage_eta=float(self.config.shrinkage_eta),
            max_fraction_cap=float(self.config.max_event_concentration_pct),
        )
        pi_side = _clamp(p_yes_hat if side_u == "YES" else (1.0 - p_yes_hat), 0.002, 0.998)
        fee_ps = 0.0 if is_maker else (sched.fee_rate * ((entry_ref_px * (1.0 - entry_ref_px)) ** sched.fee_exponent))
        net_edge_ps = pi_side - (entry_ref_px + est_slip_ps + fee_ps) - (p_disp if exit_policy == "HOLD_TO_SETTLEMENT" else 0.0)
        if net_edge_ps < float(min_net_edge_ps) or upk.capped_fraction <= 0.0:
            self._sleeve_stats[strategy_id]["rejected_edge_or_lot"] += 1
            return None

        bankroll = max(25.0, float(self.config.virtual_bankroll_usd))
        event_cap_usd = bankroll * float(self.config.max_event_concentration_pct)
        cat_cap_usd = CATEGORY_CLIP_CAP_USD.get(cat_norm, 125.0)
        depth_cap_usd = max(6.0, 0.40 * (side_l2["ask_5c_usd"] if not is_maker else side_l2["bid_5c_usd"]))
        hard_ceiling_usd = min(event_cap_usd, cat_cap_usd, depth_cap_usd)

        desired_usd = min(bankroll * upk.capped_fraction, hard_ceiling_usd)
        tick_sz = resolve_tick_size(entry_ref_px, float(snap.get("tick_size") or 0.01))

        # Safe 5-share lot floor check (`portfolio_allocation.py` L626 exact ruin-bound law):
        # Allow rounding up to the 5.0-share CLOB minimum ONLY when `min_lot_usd` stays strictly below
        # `0.85 * LCB_Full_Kelly_USD` AND `hard_ceiling_usd` (never over-betting into negative log-growth).
        min_lot_usd = max(MIN_CLOB_MARKETABLE_NOTIONAL_USD, MIN_CLOB_ORDER_SHARES * entry_ref_px)
        safe_lcb_kelly_ceiling_usd = 0.85 * bankroll * upk.lcb_full_kelly_fraction
        can_safely_round_to_min_lot = (min_lot_usd <= hard_ceiling_usd + 1e-9) and (
            min_lot_usd <= safe_lcb_kelly_ceiling_usd + 1e-9
        )
        max_upsize_ratio = (
            max(1.0, min(hard_ceiling_usd, safe_lcb_kelly_ceiling_usd) / max(desired_usd, 1e-6))
            if can_safely_round_to_min_lot
            else 1.0
        )

        lot = validate_and_quantize_order_lot(
            desired_notional_usd=desired_usd,
            price=entry_ref_px,
            min_order_shares=MIN_CLOB_ORDER_SHARES,
            min_order_notional_usd=MIN_CLOB_MARKETABLE_NOTIONAL_USD,
            tick_size=tick_sz,
            exact_cent_maker_amount=is_maker,
            allow_lot_floor_upsize=can_safely_round_to_min_lot,
            max_lot_upsize_ratio=max_upsize_ratio,
        )
        if not lot.eligible or lot.quantized_shares < MIN_CLOB_ORDER_SHARES - 1e-6:
            self._sleeve_stats[strategy_id]["rejected_edge_or_lot"] += 1
            return None

        # Record cooldown & emit intent
        self._cooldown_until[cd_key] = cur_epoch + max(0.0, float(self.config.per_market_cooldown_sec))
        self._cooldown_until.move_to_end(cd_key)
        while len(self._cooldown_until) > 2048:
            self._cooldown_until.popitem(last=False)

        self._sleeve_stats[strategy_id]["signals_emitted"] += 1
        self._sleeve_stats[strategy_id]["last_signal_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._sleeve_stats[strategy_id]["last_market_id"] = mid

        return ShadowSignalIntent(
            strategy_id=strategy_id,
            market_id=mid,
            side_label=side_u,
            exec_mode="MAKER_POST_ONLY" if is_maker else "TAKER",
            notional_usd=round(float(lot.quantized_notional_usd), 4),
            model_p_yes_true=round(_clamp(p_yes_hat, 0.002, 0.998), 6),
            limit_price=round(float(limit_price), 6) if limit_price is not None else None,
            exit_policy=exit_policy,
            target_exit_px=round(_clamp(target_exit_px, 0.02, 0.99), 4),
            stop_exit_px=round(_clamp(stop_exit_px, 0.01, 0.97), 4),
            max_hold_sec=float(max_hold_sec),
            ttl_cycles=int(ttl_cycles),
            rationale=rationale[:220],
        )

    # ------------------------------------------------------------------
    # Causal Time-Lookback Helpers Over `_MarketRingState`
    # ------------------------------------------------------------------

    @staticmethod
    def _tte_hours(snap: Mapping[str, Any], cur_epoch: float, default_hours: float = 48.0) -> float:
        end_ep = parse_end_epoch(snap)
        if end_ep is None:
            return default_hours
        return max(0.0, (end_ep - cur_epoch) / 3600.0)

    @staticmethod
    def _interp_price_before(
        obs_seq: Sequence[_CompactObs],
        target_epoch: float,
        min_age_sec: float,
        max_age_sec: float,
        cur_epoch: float,
    ) -> Optional[float]:
        """Finds strictly causal observation closest to `target_epoch` within `[min_age_sec, max_age_sec]`."""
        if len(obs_seq) < 2:
            return None
        best_px: Optional[float] = None
        best_dist = float("inf")
        for o in obs_seq[:-1]:
            age = cur_epoch - o.ts_epoch
            if min_age_sec <= age <= max_age_sec:
                dist = abs(o.ts_epoch - target_epoch)
                if dist < best_dist:
                    best_dist = dist
                    best_px = o.mid_px
        return best_px

    # ------------------------------------------------------------------
    # Sleeve 1: `P3_LIQUIDITY_SHOCK_SNAPBACK__HOLD` (`Tier 1 Validated`)
    # ------------------------------------------------------------------

    def eval_p3_liquidity_shock_snapback_hold(
        self,
        snap: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> List[ShadowSignalIntent]:
        sid = SLEEVE_P3_SHOCK_HOLD
        self._sleeve_stats[sid]["evaluated"] += 1
        cur_ep = self._now_epoch(snap)
        ok, _ = self._passes_common_market_gates(snap, cur_ep)
        if not ok:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        ring = self._sync_live_observation(snap, history, cur_ep)
        if len(ring.obs) < 5 or self._tte_hours(snap, cur_ep, default_hours=36.0) < 12.0:
            return []
        if float(snap.get("spread_px") or 1.0) > 0.035:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        obs_list = list(ring.obs)
        pm = obs_list[-1].mid_px
        if not (0.10 <= pm <= 0.90):
            return []

        prev_slice = [o.mid_px for o in obs_list[-5:-1]]
        local_med = statistics.median(prev_slice)
        shock_dev = pm - local_med
        if abs(shock_dev) < 0.075:
            return []

        side = "NO" if shock_dev > 0.0 else "YES"
        p_yes_hat = _clamp(pm - 0.55 * shock_dev, 0.02, 0.98)
        intent = self._size_and_build_intent(
            strategy_id=sid,
            snap=snap,
            side_label=side,
            p_yes_hat=p_yes_hat,
            sigma_p=0.028,
            min_net_edge_ps=0.014,
            exec_mode="TAKER",
            exit_policy="HOLD_TO_SETTLEMENT",
            cur_epoch=cur_ep,
            rationale=f"P3 shock_dev={shock_dev:+.3f} vs 4-obs median={local_med:.3f} -> BUY {side} HOLD",
        )
        return [intent] if intent is not None else []

    # ------------------------------------------------------------------
    # Sleeve 2: `P1_SHORT_OVERREACTION_REVERSION__HOLD` (`Tier 1 Validated`)
    # ------------------------------------------------------------------

    def eval_p1_short_overreaction_reversion_hold(
        self,
        snap: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> List[ShadowSignalIntent]:
        sid = SLEEVE_P1_OVERREACTION_HOLD
        self._sleeve_stats[sid]["evaluated"] += 1
        cur_ep = self._now_epoch(snap)
        ok, _ = self._passes_common_market_gates(snap, cur_ep)
        if not ok:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        ring = self._sync_live_observation(snap, history, cur_ep)
        tte_h = self._tte_hours(snap, cur_ep, default_hours=48.0)
        if len(ring.obs) < 7 or tte_h < 24.0:
            return []

        obs_list = list(ring.obs)
        pm = obs_list[-1].mid_px
        if not (0.12 <= pm <= 0.88):
            return []

        # Prefer timestamp-anchored 30m short vs 3h long anchors; fall back cleanly to step indices
        p_short = self._interp_price_before(obs_list, cur_ep - 1800.0, 120.0, 5400.0, cur_ep)
        if p_short is None:
            p_short = obs_list[-3].mid_px
        p_long = self._interp_price_before(obs_list, cur_ep - 10800.0, 3600.0, 43200.0, cur_ep)
        if p_long is None:
            p_long = obs_list[max(0, len(obs_list) - 8)].mid_px

        dp_short = pm - p_short
        dz_short = _logit(pm) - _logit(p_short)
        dz_long = _logit(pm) - _logit(p_long)
        prior_drift = dz_long - dz_short

        if abs(dp_short) < 0.11 or abs(prior_drift) > 0.30:
            return []

        reversion_shift = _clamp(-0.38 * dz_short, -0.45, 0.45)
        p_yes_hat = _sigmoid(_logit(pm) + reversion_shift)
        side = "NO" if dp_short > 0.0 else "YES"
        intent = self._size_and_build_intent(
            strategy_id=sid,
            snap=snap,
            side_label=side,
            p_yes_hat=p_yes_hat,
            sigma_p=0.035,
            min_net_edge_ps=0.016,
            exec_mode="TAKER",
            exit_policy="HOLD_TO_SETTLEMENT",
            cur_epoch=cur_ep,
            rationale=f"P1 overreaction dp_short={dp_short:+.3f}, prior_drift={prior_drift:+.2f}, TTE={tte_h:.0f}h -> BUY {side} HOLD",
        )
        return [intent] if intent is not None else []

    # ------------------------------------------------------------------
    # Sleeve 3: `HYP_012R_ZERO_PARAM_UP_SPIKE_FADE__HOLD` (`EXP-DIR-02`)
    # ------------------------------------------------------------------

    def eval_hyp012r_zero_param_up_spike_fade_hold(
        self,
        snap: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> List[ShadowSignalIntent]:
        sid = SLEEVE_HYP012R_UPSPIKE_HOLD
        self._sleeve_stats[sid]["evaluated"] += 1
        cur_ep = self._now_epoch(snap)
        ok, _ = self._passes_common_market_gates(snap, cur_ep)
        if not ok:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        ring = self._sync_live_observation(snap, history, cur_ep)
        q_txt = str(snap.get("question") or "")
        slug = str(snap.get("slug") or "")
        cat_norm = normalize_category_name(str(snap.get("category") or ""), f"{slug} {q_txt}")
        has_neg = bool(snap.get("has_negation")) if "has_negation" in snap else detect_semantic_negation(q_txt)
        if cat_norm not in NARRATIVE_CATEGORIES or has_neg:
            return []
        if self._tte_hours(snap, cur_ep, default_hours=48.0) < 6.0 or len(ring.obs) < 3:
            return []

        obs_list = list(ring.obs)
        p_mkt = obs_list[-1].mid_px
        if not (0.20 <= p_mkt <= 0.78):
            return []

        p_4h_ago = self._interp_price_before(obs_list, cur_ep - 14400.0, 5400.0, 28800.0, cur_ep)
        if p_4h_ago is None:
            return []
        dp_4h = p_mkt - p_4h_ago
        if dp_4h <= 0.12:
            return []

        # Locked zero-parameter continuous shrinkage formula (`EXP-DIR-02`, M_internal = 1):
        #   p_hat = p_mkt - 0.35 * max(0.0, dp_4h - 0.12)
        p_yes_hat = _clamp(p_mkt - 0.35 * max(0.0, dp_4h - 0.12), 0.03, 0.95)
        intent = self._size_and_build_intent(
            strategy_id=sid,
            snap=snap,
            side_label="NO",
            p_yes_hat=p_yes_hat,
            sigma_p=0.025,
            min_net_edge_ps=0.012,
            exec_mode="TAKER",
            exit_policy="HOLD_TO_SETTLEMENT",
            cur_epoch=cur_ep,
            rationale=f"HYP-012R dp_4h={dp_4h:+.3f} -> p_hat={p_yes_hat:.3f} vs p_mkt={p_mkt:.3f} -> BUY NO HOLD",
        )
        return [intent] if intent is not None else []

    # ------------------------------------------------------------------
    # Sleeve 4: `HYP_007R_AUGMENTED_CONTENDER_NO__HOLD` (`EXP-DIR-03`)
    # ------------------------------------------------------------------

    def eval_hyp007r_augmented_contender_no_hold(
        self,
        snap: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> List[ShadowSignalIntent]:
        sid = SLEEVE_HYP007R_AUGMENTED_NO_HOLD
        self._sleeve_stats[sid]["evaluated"] += 1
        cur_ep = self._now_epoch(snap)
        ok, _ = self._passes_common_market_gates(snap, cur_ep)
        if not ok:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        self._sync_live_observation(snap, history, cur_ep)
        q_txt = str(snap.get("question") or "")
        slug = str(snap.get("slug") or "")
        grp = str(snap.get("group_item_title") or snap.get("groupItemTitle") or "")
        if detect_other_or_placeholder(q_txt, slug, grp) or bool(snap.get("is_other_or_placeholder")):
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []
        has_neg = bool(snap.get("has_negation")) if "has_negation" in snap else detect_semantic_negation(q_txt)
        if has_neg or self._tte_hours(snap, cur_ep, default_hours=48.0) < 4.0:
            return []

        ev_id = str(snap.get("event_id") or "")
        obs_slate = self._event_slates.get(ev_id, {})
        leg_count = max(
            int(snap.get("event_market_count") or 0),
            self._event_declared_counts.get(ev_id, 0),
            len(obs_slate),
        )
        neg_risk = bool(snap.get("neg_risk") or snap.get("negRisk") or snap.get("neg_risk_augmented") or snap.get("negRiskAugmented"))
        aug_explicit = bool(snap.get("neg_risk_augmented") or snap.get("negRiskAugmented"))
        aug_inferred = neg_risk and (
            aug_explicit
            or any(v.is_other for v in obs_slate.values())
            or bool(_AUGMENTED_HINT_RE.search(f"{q_txt} {slug}"))
        )
        if not ((aug_inferred and leg_count >= 5) or (aug_explicit and leg_count >= 5) or (neg_risk and leg_count >= 5 and aug_inferred)):
            return []

        p_mkt = float(snap["mid_px"])
        if not (0.05 <= p_mkt <= 0.22):
            return []

        # Locked parameter-free salience/unnamed-field shrinkage (`EXP-DIR-03`, 0 legging risk)
        p_yes_hat = _clamp(p_mkt * 0.62, 0.01, 0.90)
        intent = self._size_and_build_intent(
            strategy_id=sid,
            snap=snap,
            side_label="NO",
            p_yes_hat=p_yes_hat,
            sigma_p=0.022,
            min_net_edge_ps=0.014,
            exec_mode="TAKER",
            exit_policy="HOLD_TO_SETTLEMENT",
            cur_epoch=cur_ep,
            rationale=f"HYP-007R >=5-leg negRiskAugmented ({leg_count} legs) contender p={p_mkt:.3f} -> p_hat={p_yes_hat:.3f} BUY NO",
        )
        return [intent] if intent is not None else []

    # ------------------------------------------------------------------
    # Sleeve 5: `HYP_023_WEATHER_HORIZON_ROUNDING__HOLD` (`EXP-DIR-03`)
    # ------------------------------------------------------------------

    def _lookup_weather_forecast(self, snap: Mapping[str, Any]) -> Tuple[Optional[float], Optional[float], bool]:
        """Resolves `(forecast_high_c, obs_max_c, has_maintenance_flag)` from snap or registered station map."""
        maint = bool(snap.get("weather_has_maintenance_flag"))
        metar_raw = str(snap.get("metar_raw") or "")
        if metar_raw and _ASOS_MAINT_TOKEN_RE.search(metar_raw):
            maint = True

        fc_c: Optional[float] = None
        obs_max_c: Optional[float] = None
        if snap.get("weather_forecast_c") is not None:
            fc_c = float(snap["weather_forecast_c"])
        if snap.get("weather_obs_max_c") is not None:
            obs_max_c = float(snap["weather_obs_max_c"])

        keys_to_check = [str(snap.get("market_id") or "").upper(), str(snap.get("event_id") or "").upper()]
        q_blob = f"{snap.get('question', '')} {snap.get('slug', '')}".upper()
        st_m = _ICAO_STATION_RE.search(q_blob)
        if st_m:
            keys_to_check.append(st_m.group(1).upper())

        for k in keys_to_check:
            rec = self._weather_forecasts.get(k)
            if rec is not None:
                if rec.has_maintenance_flag or (rec.metar_raw and _ASOS_MAINT_TOKEN_RE.search(rec.metar_raw)):
                    maint = True
                if fc_c is None:
                    fc_c = rec.forecast_high_c
                if obs_max_c is None:
                    obs_max_c = rec.obs_max_so_far_c
        return fc_c, obs_max_c, maint

    def eval_hyp023_weather_horizon_rounding_hold(
        self,
        snap: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> List[ShadowSignalIntent]:
        sid = SLEEVE_HYP023_WEATHER_HOLD
        self._sleeve_stats[sid]["evaluated"] += 1
        cur_ep = self._now_epoch(snap)
        ok, _ = self._passes_common_market_gates(snap, cur_ep)
        if not ok:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        self._sync_live_observation(snap, history, cur_ep)
        q_txt = str(snap.get("question") or "")
        slug = str(snap.get("slug") or "")
        cat_norm = normalize_category_name(str(snap.get("category") or ""), f"{slug} {q_txt}")
        if cat_norm != "weather":
            return []

        # Binding D-006 Sensor Maintenance Veto (`$` ASOS outage flag)
        fc_c, obs_max_c, has_maint = self._lookup_weather_forecast(snap)
        if has_maint:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        tte_h = self._tte_hours(snap, cur_ep, default_hours=18.0)
        if tte_h < 4.0:
            return []

        bucket_c = parse_narrow_temperature_bucket_celsius(q_txt)
        if bucket_c is None:
            return []
        lo_c, hi_c = bucket_c
        p_mkt = float(snap["mid_px"])
        if not (0.04 <= p_mkt <= 0.28):
            return []

        # Path A: Explicit forecast / intraday METAR max with D-006 ±0.55°C sensor rounding cushion
        p_yes_hat: Optional[float] = None
        rationale = ""
        if fc_c is not None or obs_max_c is not None:
            if obs_max_c is not None and obs_max_c > hi_c + 0.55:
                # Intraday observed high already exceeded upper bucket bound + 0.55°C rounding cushion!
                p_bucket = 0.012
                p_yes_hat = _clamp(0.75 * p_bucket + 0.25 * p_mkt, 0.01, 0.40)
                rationale = f"HYP-023 obs_max={obs_max_c:.1f}C > hi={hi_c:.1f}C+0.55C -> BUY NO HOLD"
            elif fc_c is not None:
                # Enforce D-006 ±0.55°C cushion: forecast must sit clearly outside [lo_c - 0.55, hi_c + 0.55]
                if (lo_c - 0.55) <= fc_c <= (hi_c + 0.55):
                    self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
                    return []
                tte_days = max(0.15, tte_h / 24.0)
                # sigma_c already incorporates 0.55°C sensor rounding variance (`0.55^2`) + horizon NWP error;
                # [lo_c, hi_c] from `parse_narrow_temperature_bucket_celsius` already includes ±0.5 unit bounds.
                sigma_c = math.sqrt(0.55 ** 2 + (1.05 + 0.45 * min(7.0, tte_days)) ** 2)
                p_bucket = max(
                    0.005,
                    _norm_cdf((hi_c - fc_c) / sigma_c) - _norm_cdf((lo_c - fc_c) / sigma_c),
                )
                p_cand = _clamp(0.75 * p_bucket + 0.25 * p_mkt, 0.01, 0.50)
                if p_mkt - p_cand >= 0.035:
                    p_yes_hat = p_cand
                    rationale = (
                        f"HYP-023 fc={fc_c:.1f}C vs [{lo_c:.1f},{hi_c:.1f}]C (±0.55C D-006), "
                        f"p_hat={p_cand:.3f} vs mkt={p_mkt:.3f} -> BUY NO"
                    )
        else:
            # Path B: Multi-bracket weather slate overround & modal temperature cushion (`>= 3` sibling brackets)
            ev_id = str(snap.get("event_id") or "")
            slate = self._event_slates.get(ev_id, {})
            temp_legs = [v for v in slate.values() if v.temp_mid_c is not None and (cur_ep - v.ts_epoch) <= 900.0]
            if len(temp_legs) >= 3 and 0.05 <= p_mkt <= 0.18:
                sum_p = sum(v.mid_px for v in temp_legs)
                modal_leg = max(temp_legs, key=lambda v: v.mid_px)
                this_mid_c = 0.5 * (lo_c + hi_c)
                # Require modal temperature bracket to sit outside this bracket + 0.55°C D-006 cushion!
                if sum_p >= 0.98 and modal_leg.temp_mid_c is not None:
                    if modal_leg.temp_mid_c < (lo_c - 0.55) or modal_leg.temp_mid_c > (hi_c + 0.55):
                        tail_shrink = _clamp(math.sqrt(min(36.0, max(6.0, tte_h)) / 36.0), 0.45, 0.85)
                        p_cand = _clamp((p_mkt / max(1.0, sum_p)) * tail_shrink, 0.01, 0.45)
                        if p_mkt - p_cand >= 0.035:
                            p_yes_hat = p_cand
                            rationale = (
                                f"HYP-023 slate_sum={sum_p:.2f}, modal={modal_leg.temp_mid_c:.1f}C vs "
                                f"bucket={this_mid_c:.1f}C -> p_hat={p_cand:.3f} BUY NO"
                            )

        if p_yes_hat is None:
            return []

        intent = self._size_and_build_intent(
            strategy_id=sid,
            snap=snap,
            side_label="NO",
            p_yes_hat=p_yes_hat,
            sigma_p=0.025,
            min_net_edge_ps=0.015,
            exec_mode="TAKER",
            exit_policy="HOLD_TO_SETTLEMENT",
            cur_epoch=cur_ep,
            rationale=rationale,
        )
        return [intent] if intent is not None else []

    # ------------------------------------------------------------------
    # Sleeve 6: `HYP_018_SEMANTIC_POLARITY_AWARE__HOLD` (`EXP-DIR-01`)
    # ------------------------------------------------------------------

    def eval_hyp018_semantic_polarity_aware_hold(
        self,
        snap: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> List[ShadowSignalIntent]:
        sid = SLEEVE_HYP018_POLARITY_HOLD
        self._sleeve_stats[sid]["evaluated"] += 1
        cur_ep = self._now_epoch(snap)
        ok, _ = self._passes_common_market_gates(snap, cur_ep)
        if not ok:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        self._sync_live_observation(snap, history, cur_ep)
        q_txt = str(snap.get("question") or "")
        slug = str(snap.get("slug") or "")
        grp = str(snap.get("group_item_title") or snap.get("groupItemTitle") or "")
        if detect_other_or_placeholder(q_txt, slug, grp) or bool(snap.get("is_other_or_placeholder")):
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        has_neg = bool(snap.get("has_negation")) if "has_negation" in snap else detect_semantic_negation(q_txt)
        if not has_neg or self._tte_hours(snap, cur_ep, default_hours=48.0) < 4.0:
            return []

        # Strictly target negated status-quo BUY YES at executable ask in [0.88, 0.95] (`#33` / `EXP-DIR-01`)
        yes_ask = float(snap["best_ask"])
        spread_px = float(snap["spread_px"])
        if not (0.88 <= yes_ask <= 0.95) or spread_px > 0.025:
            return []

        mid_yes = float(snap["mid_px"])
        p_dramatic_action = _clamp(1.0 - mid_yes, 0.02, 0.30)
        p_yes_hat = _clamp(1.0 - 0.55 * p_dramatic_action, 0.50, 0.99)

        intent = self._size_and_build_intent(
            strategy_id=sid,
            snap=snap,
            side_label="YES",
            p_yes_hat=p_yes_hat,
            sigma_p=0.016,
            min_net_edge_ps=0.010,
            exec_mode="TAKER",
            exit_policy="HOLD_TO_SETTLEMENT",
            cur_epoch=cur_ep,
            rationale=f"HYP-018 negated status-quo ask_YES={yes_ask:.3f}, p_hat={p_yes_hat:.3f} -> BUY YES HOLD",
        )
        return [intent] if intent is not None else []

    # ------------------------------------------------------------------
    # Sleeve 7: `ZERO_FEE_LIVE_L2_OBI_SNAPBACK__PRE_EXIT` (`EXP-DIR-06` + `EXP-DIR-08`)
    # ------------------------------------------------------------------

    def eval_zero_fee_live_l2_obi_snapback_pre_exit(
        self,
        snap: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> List[ShadowSignalIntent]:
        sid = SLEEVE_ZERO_FEE_L2_OBI_PRE_EXIT
        self._sleeve_stats[sid]["evaluated"] += 1
        cur_ep = self._now_epoch(snap)
        ok, _ = self._passes_common_market_gates(snap, cur_ep)
        if not ok:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        # Strict 0%-fee (`feesEnabled == False` AND `fee_rate == 0.0`) + Geopolitics/Politics/Macro gate!
        sched = self._resolve_snap_fee_schedule(snap)
        explicit_fees_en = snap.get("fees_enabled") if "fees_enabled" in snap else snap.get("feesEnabled")
        if sched.fees_enabled or sched.fee_rate > 0.0 or float(snap.get("fee_rate") or 0.0) > 0.0 or explicit_fees_en is True:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        q_txt = str(snap.get("question") or "")
        slug = str(snap.get("slug") or "")
        cat_norm = normalize_category_name(str(snap.get("category") or ""), f"{slug} {q_txt}")
        raw_cat_low = str(snap.get("category") or "").strip().lower()
        if cat_norm not in ZERO_FEE_PRE_EXIT_CATEGORIES and raw_cat_low not in ZERO_FEE_PRE_EXIT_CATEGORIES:
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        ring = self._sync_live_observation(snap, history, cur_ep)
        if self._tte_hours(snap, cur_ep, default_hours=48.0) < 6.0 or len(ring.obs) < 3:
            return []

        yes_book = snap.get("yes_book") or {}
        top5_obi, top5_bid_usd, top5_ask_usd = self._compute_top5_obi(yes_book)
        spread_px = float(snap["spread_px"])
        mid_yes = float(snap["mid_px"])

        # Require genuine live Top-5 two-sided L2 depth & tight spread (`<= 3.0c`)
        if top5_bid_usd < 25.0 or top5_ask_usd < 25.0 or spread_px > 0.030 or not (0.12 <= mid_yes <= 0.88):
            self._sleeve_stats[sid]["rejected_safety_or_liquidity"] += 1
            return []

        obs_list = list(ring.obs)
        prev_mids = [o.mid_px for o in obs_list[-7:-1]]
        anchor_mid = statistics.median(prev_mids)
        dislocation = mid_yes - anchor_mid
        prev_t5_obi = obs_list[-2].top5_obi

        side: Optional[str] = None
        p_yes_hat: Optional[float] = None
        trigger_tag = ""

        # Trigger A: Short-horizon dislocation (`>= 3.5c`) with confirming Top-5 L2 OBI snapback support
        if dislocation <= -0.035 and top5_obi >= 0.22:
            side = "YES"
            shift = _clamp(-0.50 * dislocation + 0.020 * top5_obi, 0.020, 0.18)
            p_yes_hat = _clamp(mid_yes + shift, 0.04, 0.96)
            trigger_tag = f"dip={dislocation:+.3f}+top5_obi={top5_obi:+.2f}"
        elif dislocation >= 0.035 and top5_obi <= -0.22:
            side = "NO"
            shift = _clamp(-0.50 * dislocation + 0.020 * top5_obi, -0.18, -0.020)
            p_yes_hat = _clamp(mid_yes + shift, 0.04, 0.96)
            trigger_tag = f"spike={dislocation:+.3f}+top5_obi={top5_obi:+.2f}"
        # Trigger B: Persistent multi-cycle heavy Top-5 L2 imbalance on ultra-tight (`<= 2.0c`) 0%-fee book
        elif abs(dislocation) <= 0.025 and abs(top5_obi) >= 0.52 and (top5_obi * prev_t5_obi > 0.0) and abs(prev_t5_obi) >= 0.30 and spread_px <= 0.020:
            side = "YES" if top5_obi > 0.0 else "NO"
            p_yes_hat = _clamp(mid_yes + 0.038 * top5_obi, 0.04, 0.96)
            trigger_tag = f"sustained_top5_obi={top5_obi:+.2f}"

        if side is None or p_yes_hat is None:
            return []

        side_l2 = self._extract_side_l2_metrics(snap, side)
        if side_l2 is None:
            return []
        tick_sz = resolve_tick_size(side_l2["mid_px"], float(snap.get("tick_size") or 0.01))
        pi_side_hat = p_yes_hat if side == "YES" else (1.0 - p_yes_hat)

        # Hybrid Taker (tight <=2.0c book with >=1.8c immediate ask edge) vs Passive postOnly Maker
        if spread_px <= 0.020 and (pi_side_hat - side_l2["best_ask"]) >= 0.018:
            exec_mode = "TAKER"
            lim_px = None
            entry_ref = side_l2["best_ask"]
        else:
            exec_mode = "MAKER_POST_ONLY"
            cand_bid = side_l2["best_bid"] + tick_sz if side_l2["spread_px"] >= 2.0 * tick_sz - 1e-9 else side_l2["best_bid"]
            lim_px = round_price_to_tick(cand_bid, tick_sz, mode="floor")
            if lim_px >= side_l2["best_ask"] - 1e-9:
                return []
            entry_ref = lim_px

        raw_edge = max(0.030, pi_side_hat - entry_ref)
        target_px = _clamp(entry_ref + max(0.025, 0.65 * raw_edge), 0.04, 0.97)
        stop_px = _clamp(entry_ref - 0.060, 0.02, 0.94)

        intent = self._size_and_build_intent(
            strategy_id=sid,
            snap=snap,
            side_label=side,
            p_yes_hat=p_yes_hat,
            sigma_p=0.022,
            min_net_edge_ps=0.012,
            exec_mode=exec_mode,
            limit_price=lim_px,
            exit_policy="PRE_RESOLUTION_EXIT",
            target_exit_px=target_px,
            stop_exit_px=stop_px,
            max_hold_sec=14400.0,
            ttl_cycles=3,
            cur_epoch=cur_ep,
            rationale=f"0%-fee {cat_norm} L2 snapback ({trigger_tag}) -> {exec_mode} BUY {side} PRE_EXIT",
        )
        return [intent] if intent is not None else []

    # ------------------------------------------------------------------
    # Public Runner Entrypoints & Per-Cycle Diagnostics
    # ------------------------------------------------------------------

    def as_strategy_functions(self) -> List[ShadowStrategyFn]:
        """Returns the 7 locked sleeve `ShadowStrategyFn` callables in exact priority order `1..7`."""
        return [
            self.eval_p3_liquidity_shock_snapback_hold,
            self.eval_p1_short_overreaction_reversion_hold,
            self.eval_hyp012r_zero_param_up_spike_fade_hold,
            self.eval_hyp007r_augmented_contender_no_hold,
            self.eval_hyp023_weather_horizon_rounding_hold,
            self.eval_hyp018_semantic_polarity_aware_hold,
            self.eval_zero_fee_live_l2_obi_snapback_pre_exit,
        ]

    def evaluate_market(
        self,
        snap: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[ShadowSignalIntent]:
        """Evaluates all 7 locked sleeves on a single market snapshot (`ShadowStrategyFn` compatible)."""
        hist_list = history if history is not None else []
        out: List[ShadowSignalIntent] = []
        for fn in self.as_strategy_functions():
            intents = fn(snap, hist_list)
            if intents:
                out.extend(intents)
        return out

    def __call__(
        self,
        snap: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Sequence[ShadowSignalIntent]:
        return self.evaluate_market(snap, history)

    def total_buffered_observations(self) -> int:
        return sum(len(r.obs) for r in self._rings.values())

    def estimated_buffer_memory_kib(self) -> float:
        """Conservative upper-bound estimate of internal ring-buffer + slate heap overhead in KiB."""
        obs_bytes = self.total_buffered_observations() * 112
        ring_bytes = len(self._rings) * 240
        slate_legs = sum(len(s) for s in self._event_slates.values())
        slate_bytes = len(self._event_slates) * 180 + slate_legs * 128
        cd_bytes = len(self._cooldown_until) * 96
        return round((obs_bytes + ring_bytes + slate_bytes + cd_bytes) / 1024.0, 2)

    def get_sleeve_telemetry(self) -> Dict[str, Any]:
        """Returns lightweight per-sleeve telemetry for `directional_shadow_status.json`."""
        return {
            "locked_sleeve_count": len(LOCKED_SLEEVE_IDS),
            "locked_sleeves": list(LOCKED_SLEEVE_IDS),
            "ring_buffer_markets": len(self._rings),
            "ring_buffer_max_markets": self._max_markets,
            "ring_buffer_max_obs_per_market": self._max_obs,
            "total_buffered_observations": self.total_buffered_observations(),
            "cold_bootstrapped_markets": self._cold_bootstrapped_markets,
            "tracked_events": len(self._event_slates),
            "estimated_suite_buffer_kib": self.estimated_buffer_memory_kib(),
            "per_sleeve": {sid: dict(stats) for sid, stats in self._sleeve_stats.items()},
            "config": asdict(self.config),
        }

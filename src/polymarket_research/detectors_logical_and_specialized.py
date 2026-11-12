"""
Opportunity Families D, E, F, G, H & I — Rule-Verified Logical & Specialized Arbitrage Detectors
(`src/polymarket_research/detectors_logical_and_specialized.py`).

Implements Agents 5 & 6 of DOMINUS — RISKLESS FULL THROTTLE:
  - Step 1 Baseline Audit (`audit_existing_logical_specialized_scanners`):
      Exact coverage & rule-vulnerability audit of existing DOMINUS v5.1 logical, temporal,
      strike, sports, weather, and duplicate-market scanners.
  - Family D (`detect_family_d_logical_arbitrage`):
      Cross-market formal proposition implications (`A => B` -> `1 NO_A + 1 YES_B`),
      mutual exclusions (`A perp B` -> `1 NO_A + 1 NO_B`), and hierarchical subset/containment
      (Candidate->Party with explicit ballot/party verification, Conjunction/Trifecta->Component,
      Pending-Condition Joint->Marginal, Nomination/Championship hierarchies), strictly blocking
      natural-language similarity without proven resolution-rule compatibility.
  - Family E (`detect_family_e_temporal_deadline_arbitrage`):
      Full-universe cross-category temporal & deadline scanner (politics, geopolitics, macro/Fed,
      tech/AI, corporate/IPO/M&A, pop culture, crypto) across intra-event AND cross-event pairs
      (including `negRisk` and standalone binaries). Parses exact cutoffs, timezones, survival vs
      first-passage semantics, and reset-window vs cumulative containment; walks L2 asks via
      `UniversalArbVerifier` only when resolution authority, timezone, and void clauses match.
  - Family F (`detect_family_f_price_strike_ladders`):
      Price-threshold (`>=`, `>`, `<=`, `<`), market-cap/FDV (`$M`/`$B`/`$T`), macro rate (`%`/`bps`),
      and range-partition (`[K1, K2)` + `>= K2` <=> `>= K1`) detector. Enforces identical reference
      exchange/oracle, `TOUCH_ANYTIME` vs `CLOSE_AT_EXPIRY` mode parity, exact settlement timestamp,
      spot-vs-futures separation, and boundary/gap state modeling.
  - Family G (`detect_family_g_sports_structures`):
      Full-universe sports outcome structure scanner (Soccer 3-way `1X2` vs Double-Chance / DNB /
      Qualification, NBA/NFL/NHL/MLB/Esports/Tennis moneylines vs spreads/handicaps, spread ladders,
      totals `Over/Under` corridors, and single-elimination tournament advancement). Explicitly audits
      regulation (`90m + stoppage`) vs overtime/shootout (`incl. OT`), tie push rules, tennis
      retirement/walkover divergence, and `50-50` abandonment vs `NegRisk` void asymmetry.
  - Family H (`detect_family_h_weather_measurable`):
      Full-universe weather & measurable-event structure scanner across temperature, precipitation,
      wind/hurricane, and measurable count brackets. Verifies exact station ICAO / agency, local
      calendar date window, unit (`°F` vs `°C`), `D-001` disputed `KMIA` non-interference, and
      `D-006` ASOS `$` hardware maintenance block + `±0.55°C` unverified sensor rounding cushion.
      External METAR observations are used strictly as verification inputs, never as substitutes for
      contractual state proofs.
  - Family I (`detect_family_i_duplicate_markets`):
      Cross-event proposition + 6-axis rule-signature matcher across the entire active universe.
      Classifies provably state-identical rules as `CLASS_B` (when L2 net profitable) and
      rule-divergent near-duplicates as `CLASS_C` / `CLASS_D` with exact machine-readable divergence notes.

Pure Python 3.12 stdlib + `src.polymarket_research.universal_arb_verifier` (zero third-party runtime deps;
100% MODE 1 / MODE 2 read-only public endpoints; `D-001`, `D-002`, `D-003`, `D-006`, `D-007`, `D-010` compliant).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone, tzinfo
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
import ssl
import threading
import time
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
import urllib.parse
from zoneinfo import ZoneInfo

from src.polymarket_research.universal_arb_verifier import (
    ActionLeg,
    ActionType,
    ArbitrageProofObject,
    CandidateStructure,
    DEFAULT_LIVE_RECONCILED_NAV_USD,
    DEFAULT_MIN_ORDER_SHARES,
    FROZEN_DISPUTED_MARKET_IDS,
    InstrumentOrderBook,
    InventoryHolding,
    OpportunityClass,
    StateSpaceBuilder,
    StateSpec,
    UniversalArbVerifier,
    VerificationConfig,
    compute_net_buy_cost_per_delivered_share,
    normalize_fee_rate,
)


GAMMA_HOST = "gamma-api.polymarket.com"
CLOB_HOST = "clob.polymarket.com"
DEFAULT_OUTPUT_DIR = Path("data/full_throttle/scans_d_to_i")
DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT: float = 0.035  # 350 bps near-arb retention window


# ---------------------------------------------------------------------------
# 0. Timezone & Pure-Stdlib Normalization Utilities (`tzdata`-free safe)
# ---------------------------------------------------------------------------


class _USFallbackDST(tzinfo):
    """Stdlib-pure North American DST `tzinfo` fallback when Windows Python lacks IANA `tzdata`."""

    def __init__(self, std_hours: int, std_name: str, dst_name: str) -> None:
        self._std_hours = int(std_hours)
        self._std_name = std_name
        self._dst_name = dst_name

    @staticmethod
    def _nth_sunday(year: int, month: int, n: int) -> int:
        wd = datetime(year, month, 1).weekday()
        first_sun = 1 + ((6 - wd) % 7)
        return first_sun + 7 * (n - 1)

    def _is_dst(self, dt: Optional[datetime]) -> bool:
        if dt is None:
            return False
        y = dt.year
        s_day = self._nth_sunday(y, 3, 2)
        e_day = self._nth_sunday(y, 11, 1)
        naive = dt.replace(tzinfo=None)
        return datetime(y, 3, s_day, 2, 0, 0) <= naive < datetime(y, 11, e_day, 2, 0, 0)

    def utcoffset(self, dt: Optional[datetime]) -> timedelta:
        return timedelta(hours=(self._std_hours + 1) if self._is_dst(dt) else self._std_hours)

    def dst(self, dt: Optional[datetime]) -> timedelta:
        return timedelta(hours=1 if self._is_dst(dt) else 0)

    def tzname(self, dt: Optional[datetime]) -> str:
        return self._dst_name if self._is_dst(dt) else self._std_name


_TZ_FALLBACKS: Dict[str, tzinfo] = {
    "UTC": timezone.utc,
    "America/New_York": _USFallbackDST(-5, "EST", "EDT"),
    "America/Chicago": _USFallbackDST(-6, "CST", "CDT"),
    "America/Denver": _USFallbackDST(-7, "MST", "MDT"),
    "America/Phoenix": timezone(timedelta(hours=-7), "MST"),
    "America/Los_Angeles": _USFallbackDST(-8, "PST", "PDT"),
    "America/Toronto": _USFallbackDST(-5, "EST", "EDT"),
    "America/Sao_Paulo": timezone(timedelta(hours=-3), "BRT"),
    "America/Argentina/Buenos_Aires": timezone(timedelta(hours=-3), "ART"),
    "America/Mexico_City": timezone(timedelta(hours=-6), "CST"),
    "America/Panama": timezone(timedelta(hours=-5), "EST"),
    "Europe/London": timezone.utc,
    "Europe/Paris": timezone(timedelta(hours=1), "CET"),
    "Europe/Berlin": timezone(timedelta(hours=1), "CET"),
    "Europe/Madrid": timezone(timedelta(hours=1), "CET"),
    "Europe/Rome": timezone(timedelta(hours=1), "CET"),
    "Europe/Amsterdam": timezone(timedelta(hours=1), "CET"),
    "Europe/Warsaw": timezone(timedelta(hours=1), "CET"),
    "Europe/Helsinki": timezone(timedelta(hours=2), "EET"),
    "Europe/Istanbul": timezone(timedelta(hours=3), "TRT"),
    "Europe/Moscow": timezone(timedelta(hours=3), "MSK"),
    "Asia/Jerusalem": timezone(timedelta(hours=2), "IST"),
    "Asia/Riyadh": timezone(timedelta(hours=3), "AST"),
    "Asia/Tehran": timezone(timedelta(hours=3, minutes=30), "IRST"),
    "Asia/Dubai": timezone(timedelta(hours=4), "GST"),
    "Asia/Karachi": timezone(timedelta(hours=5), "PKT"),
    "Asia/Kolkata": timezone(timedelta(hours=5, minutes=30), "IST"),
    "Asia/Shanghai": timezone(timedelta(hours=8), "CST"),
    "Asia/Hong_Kong": timezone(timedelta(hours=8), "HKT"),
    "Asia/Taipei": timezone(timedelta(hours=8), "CST"),
    "Asia/Singapore": timezone(timedelta(hours=8), "SGT"),
    "Asia/Manila": timezone(timedelta(hours=8), "PHT"),
    "Asia/Kuala_Lumpur": timezone(timedelta(hours=8), "MYT"),
    "Asia/Tokyo": timezone(timedelta(hours=9), "JST"),
    "Asia/Seoul": timezone(timedelta(hours=9), "KST"),
    "Africa/Johannesburg": timezone(timedelta(hours=2), "SAST"),
    "Pacific/Auckland": timezone(timedelta(hours=12), "NZST"),
}


def resolve_tz(iana_or_abbr: str) -> tzinfo:
    key = str(iana_or_abbr or "UTC").strip()
    if not key or key.upper() in {"UTC", "GMT", "Z", "ETC/UTC"}:
        return timezone.utc
    try:
        return ZoneInfo(key)
    except Exception:
        return _TZ_FALLBACKS.get(key, timezone.utc)


_FEE_TYPE_FALLBACK_BPS: Dict[str, Tuple[float, float]] = {
    "zero_fees": (0.0, 1.0),
    "sports_fees_nfl_cfb_oct26": (300.0, 1.0),
    "sports_fees_v2": (300.0, 1.0),
    "sports_fees_v3": (500.0, 1.0),
    "crypto_fees_v2": (700.0, 1.0),
    "crypto_15_min": (720.0, 1.0),
    "politics_fees": (400.0, 1.0),
    "weather_fees": (500.0, 1.0),
    "culture_fees": (500.0, 1.0),
    "economics_fees": (500.0, 1.0),
    "finance_prices_fees": (400.0, 1.0),
    "tech_fees": (400.0, 1.0),
    "mentions_fees": (500.0, 1.0),
    "general_fees": (400.0, 1.0),
}


def extract_fee_bps_and_exponent(mkt: Mapping[str, Any]) -> Tuple[float, float]:
    """Extracts `(fee_rate_bps, fee_exponent)` across Gamma & normalized market payloads."""
    if mkt.get("fee_rate_bps") is not None:
        return max(0.0, float(mkt.get("fee_rate_bps") or 0.0)), max(0.5, float(mkt.get("fee_exponent") or 1.0))
    if mkt.get("feeRateBps") is not None:
        return max(0.0, float(mkt.get("feeRateBps") or 0.0)), max(0.5, float(mkt.get("feeExponent") or 1.0))
    fee_type = str(mkt.get("feeType") or mkt.get("fee_type") or "").strip().lower()
    if fee_type == "zero_fees" or mkt.get("feesEnabled") is False or mkt.get("fees_enabled") is False:
        return 0.0, 1.0
    sched = mkt.get("feeSchedule") if isinstance(mkt.get("feeSchedule"), Mapping) else {}
    if "rate" in sched and sched.get("rate") is not None:
        r = float(sched.get("rate") or 0.0)
        bps = r if r >= 1.0 else r * 10_000.0
        return max(0.0, bps), max(0.5, float(sched.get("exponent") or 1.0))
    for k in ("fee_rate", "feeRate", "takerBaseFee"):
        if mkt.get(k) is not None:
            v = float(mkt.get(k) or 0.0)
            if v > 0.0:
                bps = v if v >= 1.0 else v * 10_000.0
                return max(0.0, bps), max(0.5, float(mkt.get("feeExponent") or mkt.get("fee_exponent") or 1.0))
    if fee_type in _FEE_TYPE_FALLBACK_BPS:
        return _FEE_TYPE_FALLBACK_BPS[fee_type]
    if mkt.get("feesEnabled") is True and fee_type:
        return 400.0, 1.0
    return 0.0, 1.0


def _parse_json_seq(val: Any) -> List[Any]:
    if isinstance(val, (list, tuple)):
        return list(val)
    if isinstance(val, str):
        s = val.strip()
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
    return []


def _parse_iso_epoch(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        f = float(raw)
        return (f / 1000.0 if f > 1e11 else f) if math.isfinite(f) and f > 0 else None
    s = str(raw).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    except Exception:
        return None


def _sf(val: Any, default: float = 0.0) -> float:
    if val in (None, ""):
        return default
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# 1. Step 1 Deliverable: Audit of Existing DOMINUS Logical & Specialized Scanners
# ---------------------------------------------------------------------------


def audit_existing_logical_specialized_scanners() -> Dict[str, Any]:
    """
    Returns the exact forensic coverage & rule-vulnerability audit of existing DOMINUS v5.1
    modules (`riskless_protocol_v2_expansion.py`, `riskless_frontier_v3_engine.py`,
    `weather_metar_engine.py`, `tradfi_sports_zero_fee_engine.py`, `same_oracle_dominance_box.py`).
    """
    return {
        "audit_version": "DOMINUS_FULL_THROTTLE_D_TO_I_BASELINE_V1",
        "total_families_audited": 6,
        "inspected_modules": [
            "src/polymarket_research/riskless_protocol_v2_expansion.py",
            "src/polymarket_research/riskless_frontier_v3_engine.py",
            "src/polymarket_research/weather_metar_engine.py",
            "src/polymarket_research/tradfi_sports_zero_fee_engine.py",
            "src/polymarket_research/same_oracle_dominance_box.py",
            "tests/test_v51_catalog_expansion_and_qa.py",
        ],
        "families": {
            "D_cross_market_logical": {
                "existing_sleeves": ["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],
                "missed_opportunities": [
                    "LP2 is hardcoded to 7 US 2026 midterm slugs + 7 Senate tossup state slugs; 0% coverage of other elections, geopolitics, macro, corporate, or award hierarchies.",
                    "No general cross-event formal implication (`A => B` -> `NO_A + YES_B`), conjunction-to-component (`A and B => A`), or cross-event mutual exclusion (`A perp B` -> `NO_A + NO_B`) scanner.",
                ],
                "rule_vulnerabilities_identified": [
                    "Cross-event combinations between `negRisk` slates (where event void resolves non-Other `YES=$0.00, NO=$1.00`) and standalone binaries (`50-50` `$0.50` void) suffer asymmetric void risk (`$0.50 < $1.00`) unless explicitly modeled in `Omega`.",
                    "Candidate-to-Party implication fails if a candidate runs on an independent/third-party ballot line unless party ballot rule is verified.",
                ],
            },
            "E_temporal_deadline": {
                "existing_sleeves": ["CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"],
                "missed_opportunities": [
                    "`parse_cal1_monotonic_ladder_event` hard-skips ALL `negRisk == True` events (`if ev.get('negRisk'): return []`) and ALL `_COVERED_CRYPTO_PYTH_SLUG_RE` slugs.",
                    "Only inspects child markets inside a single parent Gamma event — misses 100% of cross-event deadline pairs (e.g. standalone monthly/quarterly event vs annual `'in 2026'` event).",
                    "`detect_cal1_monotonic_boxes` evaluates top-of-book `best_asks` only rather than multi-rung L2 depth walking.",
                ],
                "rule_vulnerabilities_identified": [
                    "`_parse_group_label_date_ts` stamps `23:59:59 UTC` regardless of contractual timezone (`ET`, `PT`, `UTC`, `CET`, `IRST`), risking 4h-8h cutoff inversions across mismatched timezones.",
                ],
            },
            "F_price_threshold_strike_ladders": {
                "existing_sleeves": [
                    "D1_SAME_ORACLE_DOMINANCE_BOX",
                    "EQ1_PYTH_EQUITY_DOMINANCE_BOX",
                    "CM_B3_PYTH_BARRIER_BOX",
                    "CAL1_SCALAR_ABOVE",
                ],
                "missed_opportunities": [
                    "`EQ1` only checks 14 hardcoded Pyth equity symbols during `09:30-16:00 ET`; `D1` only checks 10 RTDS crypto/metal tickers on `5m/15m/1h/4h`.",
                    "`CAL1` `SCALAR_ABOVE` only triggers on 8 title substrings and rejects all downward (`<=`, `<`, `below`, `under`) ladders and `[K1, K2)` + `>= K2` <=> `>= K1` range-plus-tail covers.",
                ],
                "rule_vulnerabilities_identified": [
                    "Range + tail covers (`[K1, K2]` vs `>= K2`) have discrete gaps (e.g., `$90k-$99k` + `$100k+` leaves `($99k, $100k)` uncovered!) or boundary overlaps at `K2` that break short-side parity unless endpoint states are modeled.",
                ],
            },
            "G_sports_outcome_structures": {
                "existing_sleeves": [
                    "DC1_DOUBLE_CHANCE_1X2_PARITY",
                    "LP_COMP1_SPORTS_TRIANGLES",
                    "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
                    "SP1_NBA_ZERO_FEE_BOX",
                    "SP2_NBA_ENDGAME_LOCK",
                    "SOC2_EXACT_SCORE_2D_LATTICE",
                    "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
                ],
                "missed_opportunities": [
                    "Narrow league/slug allowlists omit hundreds of active soccer, basketball, hockey, baseball, tennis, MMA/UFC, golf, and esports (`CS2`, `LoL`, `Dota 2`, `Valorant`) events.",
                    "No general tournament advancement hierarchy detector (`Win Title => Win Conference / Reach Final`) or universal multi-sport totals/spreads ladder scanner.",
                ],
                "rule_vulnerabilities_identified": [
                    "`LP_COMP1_SPORTS_TRIANGLES` (`NO_DRAW + YES_BTTS + YES_UNDER_1_5`) did not enforce `neg_risk` / `cancel_rule` parity or `has_us_overtime_inequality` across its 3 legs.",
                    "2-legged aggregate cup ties (UEFA/Copa) allow a team to win a 90m leg yet fail `To Advance`, and double-elimination esports brackets allow losing Upper Final while still winning Grand Final.",
                    "Tennis mid-match retirement void (`50-50`) vs advancing-winner settlement creates `$0.50` worst-case loss if mixed.",
                ],
            },
            "H_weather_measurable": {
                "existing_sleeves": ["W_PRUNE1_DEAD_NO_BOND", "W_PRUNE1_NR0_BASKET", "W_SOLAR1_POST_2351_LOCK"],
                "missed_opportunities": [
                    "`weather_metar_engine.py` only polls ~72 hardcoded airport temperature slugs (`HIGH_VOLUME_WEATHER_SERIES`), omitting new weather cities and non-temperature measurable brackets (precipitation, hurricane wind/category, earthquake count, TSA/measurable ladders).",
                    "Lacks purely contractual cross-bracket / cross-metric (`Daily Low <= Daily High` on identical station/date/unit) dominance detection.",
                ],
                "rule_vulnerabilities_identified": [
                    "Single-leg METAR-pruned `DEAD_NO` locks depend on external sensor telemetry rather than purely contractual multi-leg hedging and can face UMA disputes during ASOS `$` maintenance incidents (`KMIA` Nov 7 `D-001` / `D-006`) — must never be classified `CLASS_A` or `CLASS_B`.",
                ],
            },
            "I_duplicate_near_duplicate_markets": {
                "existing_sleeves": [],
                "missed_opportunities": [
                    "100% unimplemented in existing DOMINUS repository — zero cross-event duplicate or near-duplicate question/rule matcher existed prior to Full Throttle.",
                ],
                "rule_vulnerabilities_identified": [
                    "Near-duplicate questions across separate events frequently differ in `endDate` timezone (`23:59 UTC` vs `23:59 ET`), `negRisk` void settlement, or resolution source URL, trapping naive text-matching bots.",
                ],
            },
        },
    }


# ---------------------------------------------------------------------------
# 2. Normalized Market Adapter & Canonical Rule Signatures
# ---------------------------------------------------------------------------

_PLACEHOLDER_LABEL_RE = re.compile(
    r"(?:\bplaceholder\b|\bunnamed\b|^person\s+[a-z0-9]{1,2}$|^player\s+[a-z0-9]{1,2}$"
    r"|^candidate\s+[a-z0-9]{1,2}$|^option\s+\d+$|^team\s+[a-z0-9]{1,2}$|^tba$|^tbd$)",
    re.IGNORECASE,
)
_OTHER_LABEL_RE = re.compile(
    r"^\s*(?:other|any\s+other(?:\s+\w+)*|all\s+other(?:\s+\w+)*|field|none\s+of\s+the\s+above|someone\s+else)\s*$",
    re.IGNORECASE,
)
_URL_DOMAIN_RE = re.compile(r"https?://(?:www\.)?([a-z0-9.\-]+\.[a-z]{2,})(?:/[^\s)\"']*)?", re.IGNORECASE)


@dataclass(frozen=True)
class CanonicalBinaryMarket:
    """Lightweight, immutable normalized binary market record for `Families D..I`."""

    market_id: str
    condition_id: str
    event_id: str
    event_slug: str
    event_title: str
    market_slug: str
    question: str
    group_item_title: str
    description: str
    resolution_source: str
    resolved_by: str
    yes_token_id: str
    no_token_id: str
    outcome_0_label: str
    outcome_1_label: str
    is_standard_yes_no: bool
    neg_risk: bool
    neg_risk_augmented: bool
    neg_risk_market_id: str
    is_other_outcome: bool
    is_placeholder_outcome: bool
    enable_order_book: bool
    accepting_orders: bool
    closed_or_archived: bool
    uma_resolution_status: str
    fee_rate_bps: float
    fee_exponent: float
    min_order_size: float
    tick_size: Optional[float]
    start_ts: Optional[float]
    end_ts: Optional[float]
    end_date_iso: str
    sports_market_type: str
    sports_line: Optional[float]
    tags: Tuple[str, ...]
    indicative_yes_price: Optional[float] = None
    indicative_no_price: Optional[float] = None
    best_ask_hint: Optional[float] = None
    liquidity_usd: float = 0.0
    volume_24h_usd: float = 0.0

    def is_d001_disputed_quarantined(self) -> bool:
        if self.market_id in FROZEN_DISPUTED_MARKET_IDS:
            return True
        return self.uma_resolution_status.lower() == "disputed"

    @property
    def cancel_rule_tag(self) -> str:
        if self.neg_risk:
            return "NEGRISK_YES" if self.is_other_outcome else "NEGRISK_NO"
        return "50_50"

    @property
    def lockup_hours_estimate(self) -> Tuple[float, float]:
        now_s = time.time()
        if self.end_ts is not None and self.end_ts > now_s:
            rem_h = max(0.25, (self.end_ts - now_s) / 3600.0)
            return round(rem_h + 2.0, 3), round(rem_h + 24.0, 3)
        return 2.5, 24.0


@dataclass(frozen=True)
class DetectedOpportunity:
    """Unified output record wrapping `CandidateStructure` + `ArbitrageProofObject` + family diagnostics."""

    candidate_id: str
    family: str
    sub_type: str
    relationship_type: str
    edge_proof_status: str  # "VERIFIED_MATHEMATICAL" | "OFFICIAL_CONTRACTUAL" | "RULE_MISMATCH_REJECTED" | "NEAR_DUPLICATE_DIVERGENT" | "SENSOR_VERIFICATION_ONLY"
    market_ids: Tuple[str, ...]
    event_ids: Tuple[str, ...]
    instrument_ids: Tuple[str, ...]
    title_summary: str
    rule_compatibility_notes: Tuple[str, ...]
    divergence_or_rejection_reasons: Tuple[str, ...]
    is_dormant_near_miss: bool
    gap_to_breakeven_bps: float
    structure: CandidateStructure
    proof: ArbitrageProofObject
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def opportunity_class(self) -> str:
        return self.proof.opportunity_class

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "sub_type": self.sub_type,
            "relationship_type": self.relationship_type,
            "edge_proof_status": self.edge_proof_status,
            "opportunity_class": self.proof.opportunity_class,
            "is_mathematically_proven_arb": self.proof.is_mathematically_proven_arb,
            "is_atomic_or_prelocked": self.proof.is_atomic_or_prelocked,
            "d007_sub500_multileg_quarantine": self.proof.d007_sub500_multileg_quarantine,
            "execution_mode_cap": self.proof.execution_mode_cap,
            "is_dormant_near_miss": self.is_dormant_near_miss,
            "gap_to_breakeven_bps": self.gap_to_breakeven_bps,
            "market_ids": list(self.market_ids),
            "event_ids": list(self.event_ids),
            "instrument_ids": list(self.instrument_ids),
            "title_summary": self.title_summary,
            "optimal_executable_quantity": self.proof.optimal_executable_quantity,
            "gross_top_of_book_edge_per_unit": self.proof.gross_top_of_book_edge_per_unit,
            "net_executable_edge_per_unit": self.proof.net_executable_edge_per_unit,
            "min_state_net_payoff_usd": self.proof.min_state_net_payoff_usd,
            "max_state_net_payoff_usd": self.proof.max_state_net_payoff_usd,
            "expected_net_payoff_usd": self.proof.expected_net_payoff_usd,
            "worst_state_id": self.proof.worst_state_id,
            "capital_efficiency_bps_per_hr": self.proof.capital_efficiency_bps_per_hr,
            "four_value_ledger": asdict(self.proof.four_value_ledger),
            "cost_breakdown": asdict(self.proof.cost_breakdown),
            "rule_compatibility_notes": list(self.rule_compatibility_notes),
            "divergence_or_rejection_reasons": list(self.divergence_or_rejection_reasons),
            "counterexample_states": list(self.proof.counterexample_states),
            "disqualifiers": list(self.proof.disqualifiers),
            "residual_risks": list(self.proof.residual_risks),
            "proof_sha256": self.proof.proof_sha256,
            "legs": [asdict(lg) | {"action_type": lg.action_type.value} for lg in self.structure.legs],
            "metadata": dict(self.metadata),
        }


def _obj_get(obj: Any, *keys: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        for k in keys:
            if k in obj and obj[k] is not None:
                return obj[k]
        return default
    for k in keys:
        if hasattr(obj, k):
            val = getattr(obj, k)
            if val is not None:
                return val
    return default


def normalize_universe_to_canonical_markets(
    events_or_markets: Iterable[Any],
    *,
    skip_closed_non_disputed: bool = False,
) -> List[CanonicalBinaryMarket]:
    """
    Converts raw Gamma `events` dicts, `NormalizedEvent` objects, or flat market dicts/objects
    into deduplicated `CanonicalBinaryMarket` records.
    """
    out: List[CanonicalBinaryMarket] = []
    seen_mids: Set[str] = set()

    for item in events_or_markets or ():
        mkts_raw = _obj_get(item, "markets")
        if mkts_raw is not None and isinstance(mkts_raw, Iterable) and not isinstance(mkts_raw, (str, bytes)):
            ev_id = str(_obj_get(item, "event_id", "id", default="") or "").strip()
            ev_slug = str(_obj_get(item, "slug", "event_slug", default="") or "").strip()
            ev_title = str(_obj_get(item, "title", "event_title", default="") or "").strip()
            ev_desc = str(_obj_get(item, "description", default="") or "").strip()
            ev_res_src = str(_obj_get(item, "resolutionSource", "resolution_source", default="") or "").strip()
            ev_nr = bool(_obj_get(item, "negRisk", "enableNegRisk", "neg_risk", default=False))
            ev_aug = bool(_obj_get(item, "negRiskAugmented", "augmentedNegRisk", "neg_risk_augmented", default=False))
            ev_nrmid = str(_obj_get(item, "negRiskMarketID", "neg_risk_market_id", default="") or "").strip()
            ev_end = _obj_get(item, "endDate", "end_date_iso", "end_ts")
            ev_start = _obj_get(item, "startDate", "startTime", "createdAt", "start_ts")
            raw_tags = _obj_get(item, "tags", default=()) or ()
            tag_strs: List[str] = []
            for tg in raw_tags:
                if isinstance(tg, str):
                    tag_strs.append(tg.lower())
                elif isinstance(tg, Mapping):
                    lbl = str(tg.get("slug") or tg.get("label") or "").strip().lower()
                    if lbl:
                        tag_strs.append(lbl)
                elif hasattr(tg, "slug"):
                    tag_strs.append(str(getattr(tg, "slug") or "").lower())
            mkt_iter = list(mkts_raw)
        else:
            ev_id = str(_obj_get(item, "event_id", "eventId", default="") or "").strip()
            ev_slug = str(_obj_get(item, "event_slug", "eventSlug", "_ev_slug", default="") or "").strip()
            ev_title = str(_obj_get(item, "event_title", "eventTitle", default="") or "").strip()
            ev_desc = ""
            ev_res_src = ""
            ev_nr = False
            ev_aug = False
            ev_nrmid = ""
            ev_end = None
            ev_start = None
            tag_strs = [str(t).lower() for t in (_obj_get(item, "tags", default=()) or ()) if isinstance(t, str)]
            mkt_iter = [item]

        for m in mkt_iter:
            mid = str(_obj_get(m, "market_id", "id", default="") or "").strip()
            cid = str(_obj_get(m, "condition_id", "conditionId", default="") or "").strip()
            dedup_k = mid or cid
            if not dedup_k or dedup_k in seen_mids:
                continue
            if skip_closed_non_disputed:
                uma_fast = str(_obj_get(m, "umaResolutionStatus", "uma_resolution_status", default="") or "").strip().lower()
                if mid not in FROZEN_DISPUTED_MARKET_IDS and uma_fast != "disputed":
                    if bool(_obj_get(m, "closed", default=False) or _obj_get(m, "archived", default=False)):
                        continue

            # Extract tokens & outcomes (supporting both Gamma `clobTokenIds` and normalized `instruments`)
            toks = _parse_json_seq(_obj_get(m, "clobTokenIds", "clob_token_ids", "token_ids"))
            outs = [str(o).strip() for o in _parse_json_seq(_obj_get(m, "outcomes", "outcome_labels"))]
            instruments = _obj_get(m, "instruments")
            if (len(toks) < 2 or len(outs) < 2) and isinstance(instruments, Sequence) and len(instruments) >= 2:
                toks = [str(_obj_get(ins, "instrument_id", "token_id", default="") or "") for ins in instruments[:2]]
                outs = [str(_obj_get(ins, "outcome_label", "label", default="") or "") for ins in instruments[:2]]

            # Only binary markets have 2 complementary CTF slots; multi-slot non-binary CTF is Family B
            if len(outs) > 2 or len(toks) > 2:
                continue
            y_tok = str(toks[0]).strip() if len(toks) >= 1 else str(_obj_get(m, "yes_token_id", "yes_token", default="") or "").strip()
            n_tok = str(toks[1]).strip() if len(toks) >= 2 else str(_obj_get(m, "no_token_id", "no_token", default="") or "").strip()
            o0 = outs[0] if len(outs) >= 1 else "Yes"
            o1 = outs[1] if len(outs) >= 2 else "No"

            # Normalize standard Yes/No token ordering in case outcomes are ["No", "Yes"]
            o0_l, o1_l = o0.strip().lower(), o1.strip().lower()
            if o0_l == "no" and o1_l == "yes":
                y_tok, n_tok = n_tok, y_tok
                o0, o1 = "Yes", "No"
                o0_l, o1_l = "yes", "no"
            is_std_yn = o0_l == "yes" and o1_l == "no"

            q = str(_obj_get(m, "question", "title", default="") or "").strip()
            grp = str(_obj_get(m, "groupItemTitle", "group_item_title", default="") or "").strip()
            desc = str(_obj_get(m, "description", "rules", "rules_text", default=ev_desc) or ev_desc).strip()
            res_src = str(_obj_get(m, "resolutionSource", "resolution_source", default=ev_res_src) or ev_res_src).strip()
            res_by = str(_obj_get(m, "resolvedBy", "resolved_by", default="") or "").strip().lower()
            nr = bool(_obj_get(m, "negRisk", "neg_risk", default=ev_nr))
            nr_aug = bool(_obj_get(m, "negRiskAugmented", "neg_risk_augmented", default=ev_aug))
            nr_mid = str(_obj_get(m, "negRiskMarketID", "neg_risk_market_id", default=ev_nrmid) or ev_nrmid).strip()

            lbl_probe = grp or q
            is_other = bool(_obj_get(m, "negRiskOther", "is_other", "isOther", default=False) or _OTHER_LABEL_RE.match(lbl_probe))
            is_ph = bool(
                _obj_get(m, "isPlaceholder", "is_placeholder", "placeholder", default=False)
                or _PLACEHOLDER_LABEL_RE.search(grp)
                or _PLACEHOLDER_LABEL_RE.search(q)
            )

            en_ob = _obj_get(m, "enableOrderBook", "enable_order_book", default=True) is not False
            acc_ord = _obj_get(m, "acceptingOrders", "accepting_orders", default=True) is not False
            closed_arch = bool(
                _obj_get(m, "closed", default=False)
                or _obj_get(m, "archived", default=False)
                or (_obj_get(m, "active", default=True) is False)
            )
            uma_st = str(_obj_get(m, "umaResolutionStatus", "uma_resolution_status", default="") or "").strip()

            m_dict = m if isinstance(m, Mapping) else {
                "fee_rate_bps": _obj_get(m, "fee_rate_bps", "feeRateBps"),
                "fee_exponent": _obj_get(m, "fee_exponent", "feeExponent"),
                "feeType": _obj_get(m, "feeType", "fee_type"),
                "feesEnabled": _obj_get(m, "feesEnabled", "fees_enabled"),
            }
            f_bps, f_exp = extract_fee_bps_and_exponent(m_dict)
            min_sz = max(DEFAULT_MIN_ORDER_SHARES, _sf(_obj_get(m, "orderMinSize", "min_order_size"), DEFAULT_MIN_ORDER_SHARES))
            tk_raw = _obj_get(m, "orderPriceMinTickSize", "tick_size")
            tk_f = _sf(tk_raw, 0.0)
            tick_sz = tk_f if tk_f > 0.0 else None

            end_raw = _obj_get(m, "endDate", "end_date_iso", "end_ts", default=ev_end)
            start_raw = _obj_get(m, "eventStartTime", "gameStartTime", "startDate", "createdAt", "start_ts", default=ev_start)
            end_ts = _parse_iso_epoch(end_raw)
            start_ts = _parse_iso_epoch(start_raw)
            end_iso = str(end_raw or "") if not isinstance(end_raw, (int, float)) else ""

            smt = str(_obj_get(m, "sportsMarketType", "sports_market_type", default="") or "").strip().lower()
            line_raw = _obj_get(m, "line", "sports_line")
            line_f = _sf(line_raw, float("nan"))
            sp_line = line_f if math.isfinite(line_f) else None

            op_seq = _parse_json_seq(_obj_get(m, "outcomePrices", "outcome_prices"))
            ind_y = _sf(op_seq[0], -1.0) if len(op_seq) >= 1 else -1.0
            ind_n = _sf(op_seq[1], -1.0) if len(op_seq) >= 2 else -1.0
            if _obj_get(m, "outcomes") and len(_parse_json_seq(_obj_get(m, "outcomes"))) >= 2:
                raw_o0 = str(_parse_json_seq(_obj_get(m, "outcomes"))[0]).strip().lower()
                if raw_o0 == "no" and ind_y >= 0 and ind_n >= 0:
                    ind_y, ind_n = ind_n, ind_y

            ba_raw = _sf(_obj_get(m, "bestAsk", "best_ask"), -1.0)
            liq_val = max(0.0, _sf(_obj_get(m, "liquidityClob", "liquidityNum", "liquidity", "liquidity_usd"), 0.0))
            vol_24h = max(0.0, _sf(_obj_get(m, "volume24hrClob", "volume24hr", "volume_24h_usd"), 0.0))

            seen_mids.add(dedup_k)
            out.append(
                CanonicalBinaryMarket(
                    market_id=mid or cid,
                    condition_id=cid,
                    event_id=ev_id or mid or cid,
                    event_slug=ev_slug,
                    event_title=ev_title,
                    market_slug=str(_obj_get(m, "slug", "market_slug", default="") or "").strip(),
                    question=q,
                    group_item_title=grp,
                    description=desc,
                    resolution_source=res_src,
                    resolved_by=res_by,
                    yes_token_id=y_tok,
                    no_token_id=n_tok,
                    outcome_0_label=o0,
                    outcome_1_label=o1,
                    is_standard_yes_no=is_std_yn,
                    neg_risk=nr,
                    neg_risk_augmented=nr_aug,
                    neg_risk_market_id=nr_mid,
                    is_other_outcome=is_other,
                    is_placeholder_outcome=is_ph,
                    enable_order_book=bool(en_ob),
                    accepting_orders=bool(acc_ord),
                    closed_or_archived=closed_arch,
                    uma_resolution_status=uma_st,
                    fee_rate_bps=f_bps,
                    fee_exponent=f_exp,
                    min_order_size=min_sz,
                    tick_size=tick_sz,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    end_date_iso=end_iso,
                    sports_market_type=smt,
                    sports_line=sp_line,
                    tags=tuple(dict.fromkeys(tag_strs)),
                    indicative_yes_price=ind_y if 0.0 <= ind_y <= 1.0 else None,
                    indicative_no_price=ind_n if 0.0 <= ind_n <= 1.0 else None,
                    best_ask_hint=ba_raw if 0.0 < ba_raw < 1.0 else None,
                    liquidity_usd=liq_val,
                    volume_24h_usd=vol_24h,
                )
            )
    return out


def build_instrument_order_books(
    markets: Sequence[CanonicalBinaryMarket],
    raw_books: Optional[Mapping[str, Any]],
    *,
    default_fetch_ts: Optional[float] = None,
) -> Dict[str, InstrumentOrderBook]:
    """
    Normalizes either `Mapping[str, InstrumentOrderBook]` or raw CLOB `/books` `Mapping[str, dict]`
    into `Dict[str, InstrumentOrderBook]`, enriching every instrument with its market's exact
    `fee_rate_bps`, `fee_exponent`, `min_order_size`, `tick_size`, `enable_order_book`, and
    `is_placeholder` / `is_other` metadata.
    """
    src = raw_books or {}
    out: Dict[str, InstrumentOrderBook] = {}
    mkt_by_tok: Dict[str, Tuple[CanonicalBinaryMarket, str]] = {}
    for m in markets:
        if m.yes_token_id:
            mkt_by_tok[m.yes_token_id] = (m, m.outcome_0_label)
        if m.no_token_id:
            mkt_by_tok[m.no_token_id] = (m, m.outcome_1_label)

    for tok_id, bk_val in src.items():
        tid = str(tok_id).strip()
        if not tid:
            continue
        m_meta = mkt_by_tok.get(tid)
        mkt = m_meta[0] if m_meta else None
        lbl = m_meta[1] if m_meta else ""

        if isinstance(bk_val, InstrumentOrderBook):
            out[tid] = bk_val
            continue
        if isinstance(bk_val, Mapping):
            # Prefer explicit caller `timestamp_sec` / `book_timestamp_sec`; if raw CLOB `/books`
            # only carries resting-order `timestamp` and caller passed `default_fetch_ts`, use `default_fetch_ts`
            explicit_ts = bk_val.get("book_timestamp_sec") or bk_val.get("timestamp_sec") or bk_val.get("fetched_at_ts")
            ts_use = explicit_ts if explicit_ts is not None else (
                default_fetch_ts if default_fetch_ts is not None else bk_val.get("timestamp")
            )
            out[tid] = InstrumentOrderBook.from_raw(
                tid,
                bk_val,
                market_id=mkt.market_id if mkt else "",
                condition_id=mkt.condition_id if mkt else "",
                outcome_label=lbl,
                fee_rate_bps=mkt.fee_rate_bps if mkt else None,
                fee_exponent=mkt.fee_exponent if mkt else 1.0,
                tick_size=mkt.tick_size if mkt else None,
                min_order_size=mkt.min_order_size if mkt else None,
                enable_order_book=(mkt.enable_order_book and mkt.accepting_orders and not mkt.closed_or_archived) if mkt else True,
                book_timestamp_sec=_sf(ts_use, 0.0) if ts_use is not None else None,
                is_placeholder=mkt.is_placeholder_outcome if mkt else False,
                is_other=mkt.is_other_outcome if mkt else False,
            )

    # Also register disabled-orderbook markers when a market explicitly disables its orderbook
    for m in markets:
        if not m.enable_order_book:
            for tid, lbl in ((m.yes_token_id, m.outcome_0_label), (m.no_token_id, m.outcome_1_label)):
                if tid and tid not in out:
                    out[tid] = InstrumentOrderBook(
                        instrument_id=tid,
                        market_id=m.market_id,
                        condition_id=m.condition_id,
                        outcome_label=lbl,
                        enable_order_book=False,
                        fee_rate_bps=m.fee_rate_bps,
                        fee_exponent=m.fee_exponent,
                        min_order_size=m.min_order_size,
                        tick_size=m.tick_size,
                        is_placeholder=m.is_placeholder_outcome,
                        is_other=m.is_other_outcome,
                    )
    return out


# ---------------------------------------------------------------------------
# 3. Shared Rule-Signature Extractors (Authority, Timezone, Exceptions, Oracles)
# ---------------------------------------------------------------------------

_TZ_EXPLICIT_PATTERNS: Tuple[Tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\b(?:ET|EDT|EST|Eastern\s+(?:Daylight|Standard)?\s*Time|New\s+York\s+time)\b", re.I), "ET", "America/New_York"),
    (re.compile(r"\b(?:PT|PDT|PST|Pacific\s+(?:Daylight|Standard)?\s*Time|Los\s+Angeles\s+time)\b", re.I), "PT", "America/Los_Angeles"),
    (re.compile(r"\b(?:CT|CDT|CST|Central\s+(?:Daylight|Standard)?\s*Time|Chicago\s+time)\b", re.I), "CT", "America/Chicago"),
    (re.compile(r"\b(?:MT|MDT|MST|Mountain\s+(?:Daylight|Standard)?\s*Time|Denver\s+time)\b", re.I), "MT", "America/Denver"),
    (re.compile(r"\b(?:UTC|GMT|Coordinated\s+Universal\s+Time)\b", re.I), "UTC", "UTC"),
    (re.compile(r"\b(?:CET|CEST|Central\s+European\s+(?:Summer\s+)?Time)\b", re.I), "CET", "Europe/Paris"),
    (re.compile(r"\b(?:EET|EEST|Eastern\s+European\s+(?:Summer\s+)?Time)\b", re.I), "EET", "Europe/Helsinki"),
    (re.compile(r"\b(?:IRST|Iran\s+Standard\s+Time)\b", re.I), "IRST", "Asia/Tehran"),
    (re.compile(r"\b(?:JST|Japan\s+Standard\s+Time)\b", re.I), "JST", "Asia/Tokyo"),
    (re.compile(r"\b(?:HKT|Hong\s+Kong\s+Time)\b", re.I), "HKT", "Asia/Hong_Kong"),
    (re.compile(r"\b(?:KST|Korea\s+Standard\s+Time)\b", re.I), "KST", "Asia/Seoul"),
)

_AUTHORITY_PHRASE_MAP: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"binance\.com|\bbinance\b", re.I), "BINANCE"),
    (re.compile(r"coinbase\.com|\bcoinbase\b", re.I), "COINBASE"),
    (re.compile(r"kraken\.com|\bkraken\b", re.I), "KRAKEN"),
    (re.compile(r"coingecko\.com|\bcoingecko\b", re.I), "COINGECKO"),
    (re.compile(r"coinmarketcap\.com|\bcoinmarketcap\b", re.I), "COINMARKETCAP"),
    (re.compile(r"data\.chain\.link|chainlink|\brtds\b|twap-60s-streams", re.I), "CHAINLINK"),
    (re.compile(r"pyth\.network|\bpyth\b", re.I), "PYTH"),
    (re.compile(r"deribit\.com|\bderibit\b", re.I), "DERIBIT"),
    (re.compile(r"hyperliquid", re.I), "HYPERLIQUID"),
    (re.compile(r"federalreserve\.gov|\bfederal\s+reserve\b|\bfomc\b", re.I), "FEDERAL_RESERVE"),
    (re.compile(r"bls\.gov|\bbureau\s+of\s+labor\s+statistics\b", re.I), "BLS_GOV"),
    (re.compile(r"bea\.gov|\bbureau\s+of\s+economic\s+analysis\b", re.I), "BEA_GOV"),
    (re.compile(r"aviationweather\.gov", re.I), "AWC_METAR"),
    (re.compile(r"wunderground\.com|weather\s+underground", re.I), "WUNDERGROUND"),
    (re.compile(r"weather\.gov/wrh/climate|daily\s+climate\s+report|\bnws\s+cli\b", re.I), "NWS_CLI"),
    (re.compile(r"hko\.gov\.hk|hong\s+kong\s+observatory", re.I), "HKO_GOV"),
    (re.compile(r"\bassociated\s+press\b|\bap\s+call\b", re.I), "ASSOCIATED_PRESS"),
    (re.compile(r"\bfox\s+news\b", re.I), "FOX_NEWS"),
    (re.compile(r"\bnbc\s+news\b", re.I), "NBC_NEWS"),
    (re.compile(r"\bdecision\s+desk\s+hq\b|\bddhq\b", re.I), "DDHQ"),
    (re.compile(r"\bofficial\s+certification\b|certified\s+election\s+results|clerk\s+of\s+the\s+house", re.I), "OFFICIAL_CERTIFICATION"),
    (re.compile(r"consensus\s+of\s+credible\s+reporting", re.I), "CREDIBLE_REPORTING_CONSENSUS"),
    (re.compile(r"\bofficial\s+(?:announcement|statement|confirmation|press\s+release)\b", re.I), "OFFICIAL_ANNOUNCEMENT"),
)

_EXCEPTION_CLAUSE_FLAGS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:acting|interim)\b.*?\b(?:will\s+not|does\s+not|do\s+not|excluded)\b", re.I), "EXCLUDES_INTERIM_ACTING"),
    (re.compile(r"\b(?:acting|interim)\b.*?\b(?:will\s+count|counts|included)\b", re.I), "INCLUDES_INTERIM_ACTING"),
    (re.compile(r"\b50[\s/-]*50\b|\b0\.50\b", re.I), "HAS_50_50_CLAUSE"),
    (re.compile(r"\b(?:postponed|abandoned|canceled|cancelled)\b", re.I), "HAS_POSTPONEMENT_CANCEL_CLAUSE"),
    (re.compile(r"\b(?:rumor|unconfirmed|leak)\b.*?\b(?:not\s+count|insufficient)\b", re.I), "EXCLUDES_RUMORS"),
    (re.compile(r"\b(?:split|reverse\s+split|stock\s+split)\b", re.I), "SPLIT_ADJUSTMENT_CLAUSE"),
    (re.compile(r"\b(?:retire(?:s|d|ment)|walkover|disqualif)\b", re.I), "WALKOVER_RETIREMENT_CLAUSE"),
)


def extract_timezone_signature(m: CanonicalBinaryMarket) -> Tuple[str, str]:
    """
    Returns `(tz_tag, iana_name)`, `'CONFLICTING_TZ'` if question and description state different
    explicit timezones, or `('UNSPECIFIED', 'UTC')` when no explicit timezone is stated.
    """
    q_found: Optional[Tuple[str, str]] = None
    d_found: Optional[Tuple[str, str]] = None
    for pat, tag, iana in _TZ_EXPLICIT_PATTERNS:
        if q_found is None and pat.search(m.question):
            q_found = (tag, iana)
        if d_found is None and pat.search(m.description):
            d_found = (tag, iana)
    if q_found and d_found and q_found[0] != d_found[0]:
        return f"CONFLICTING_TZ_{q_found[0]}_VS_{d_found[0]}", "UTC"
    if d_found:
        return d_found
    if q_found:
        return q_found
    return "UNSPECIFIED", "UTC"


def extract_resolution_authority_signature(m: CanonicalBinaryMarket) -> str:
    """Canonicalizes resolution authority across explicit `resolutionSource` URL and rule text."""
    tokens: List[str] = []
    src_raw = f"{m.resolution_source} {m.description}"
    for dom_m in _URL_DOMAIN_RE.finditer(m.resolution_source):
        dom = dom_m.group(1).lower()
        if dom and dom != "polymarket.com":
            tokens.append(f"URL:{dom}")
    for pat, code in _AUTHORITY_PHRASE_MAP:
        if pat.search(src_raw):
            tokens.append(code)
    if not tokens:
        for dom_m in _URL_DOMAIN_RE.finditer(m.description):
            dom = dom_m.group(1).lower()
            if dom and dom not in {"polymarket.com", "t.me", "discord.gg", "x.com", "twitter.com"}:
                tokens.append(f"DESC_URL:{dom}")
    dedup = sorted(set(tokens))
    return "|".join(dedup) if dedup else "UNSPECIFIED_AUTHORITY"


def extract_exception_clause_signature(m: CanonicalBinaryMarket) -> Tuple[str, ...]:
    blob = f"{m.question} {m.description}"
    blob_l = blob.lower()
    if not any(
        kw in blob_l
        for kw in ("acting", "interim", "50", "0.50", "postpon", "abandon", "cancel", "rumor", "unconfirmed", "leak", "split", "retire", "walkover", "disqualif")
    ):
        return ()
    found: List[str] = []
    for pat, code in _EXCEPTION_CLAUSE_FLAGS:
        if pat.search(blob):
            found.append(code)
    return tuple(sorted(set(found)))


def _make_candidate_id(family: str, sub_type: str, parts: Sequence[str]) -> str:
    raw = f"{family}:{sub_type}:" + "|".join(str(p) for p in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:14]
    return f"FT_{family}_{sub_type}_{digest}"


def _build_leg_with_optional_inventory(
    instrument_id: str,
    market_id: str,
    label: str,
    holdings: Optional[Mapping[str, InventoryHolding]],
    *,
    weight: float = 1.0,
) -> ActionLeg:
    """
    Uses unlocked pre-held inventory (`ActionType.USE_INVENTORY`) ONLY when `holdings` holds
    `>= DEFAULT_MIN_ORDER_SHARES` of `instrument_id` AND the holding is NOT `D-001` protected (`KMIA`/disputed).
    Otherwise builds standard `ActionType.BUY_CLOB`.
    """
    if holdings and instrument_id in holdings:
        inv = holdings[instrument_id]
        if not inv.is_d001_protected() and float(inv.shares) >= DEFAULT_MIN_ORDER_SHARES * max(1.0, weight):
            return ActionLeg(
                action_type=ActionType.USE_INVENTORY,
                instrument_id=instrument_id,
                weight=weight,
                market_id=market_id,
                label=f"INV:{label}",
            )
    return ActionLeg(
        action_type=ActionType.BUY_CLOB,
        instrument_id=instrument_id,
        weight=weight,
        market_id=market_id,
        label=label,
    )


def _finalize_detected_opportunity(
    verifier: UniversalArbVerifier,
    books: Mapping[str, InstrumentOrderBook],
    holdings: Optional[Mapping[str, InventoryHolding]],
    *,
    candidate_id: str,
    family: str,
    sub_type: str,
    relationship_type: str,
    edge_proof_status: str,
    markets: Sequence[CanonicalBinaryMarket],
    legs: Sequence[ActionLeg],
    states: Sequence[StateSpec],
    title_summary: str,
    rule_verified: bool,
    rule_compatibility_notes: Sequence[str] = (),
    divergence_or_rejection_reasons: Sequence[str] = (),
    is_statistical_or_cross_oracle_only: bool = False,
    requires_exhaustive_partition: bool = False,
    is_exhaustive_partition: bool = True,
    is_mutually_exclusive: bool = True,
    metadata: Optional[Mapping[str, Any]] = None,
) -> DetectedOpportunity:
    """Runs `UniversalArbVerifier.verify_and_simulate` and computes exact dormant near-miss metrics."""
    exp_h = max((m.lockup_hours_estimate[0] for m in markets), default=2.5)
    worst_h = max((m.lockup_hours_estimate[1] for m in markets), default=24.0)
    has_ph = any(m.is_placeholder_outcome for m in markets)
    has_mut_other = any(m.neg_risk_augmented and m.is_other_outcome for m in markets)

    disq_list = list(divergence_or_rejection_reasons) if not rule_verified else []

    cand_struct = CandidateStructure(
        candidate_id=candidate_id,
        family=family,
        legs=tuple(legs),
        states=tuple(states),
        rule_verified=bool(rule_verified),
        rule_disqualifiers=tuple(disq_list),
        is_exhaustive_partition=is_exhaustive_partition,
        is_mutually_exclusive=is_mutually_exclusive,
        requires_exhaustive_partition=requires_exhaustive_partition,
        has_augmented_placeholder_risk=has_ph,
        has_mutable_other_exposure=has_mut_other,
        is_statistical_or_cross_oracle_only=is_statistical_or_cross_oracle_only,
        expected_lockup_hours=exp_h,
        worst_case_lockup_hours=worst_h,
        notes=tuple(rule_compatibility_notes),
    )
    proof = verifier.verify_and_simulate(cand_struct, books, holdings=holdings)

    # Determine if this is a mathematically proven contractual structure sitting within 350 bps of breakeven
    tob_edge = float(proof.gross_top_of_book_edge_per_unit)
    all_books_have_asks = all(
        (books.get(lg.instrument_id) is not None and len(books[lg.instrument_id].asks) > 0)
        for lg in legs
        if lg.action_type == ActionType.BUY_CLOB
    )
    is_dormant = bool(
        rule_verified
        and not is_statistical_or_cross_oracle_only
        and not has_ph
        and not has_mut_other
        and proof.opportunity_class == OpportunityClass.CLASS_E.value
        and all_books_have_asks
        and (-DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT <= tob_edge <= 0.005)
    )
    gap_bps = round(max(0.0, -tob_edge) * 10_000.0, 2) if tob_edge <= 0.0 else 0.0

    return DetectedOpportunity(
        candidate_id=candidate_id,
        family=family,
        sub_type=sub_type,
        relationship_type=relationship_type,
        edge_proof_status=edge_proof_status,
        market_ids=tuple(dict.fromkeys(m.market_id for m in markets)),
        event_ids=tuple(dict.fromkeys(m.event_id for m in markets)),
        instrument_ids=tuple(lg.instrument_id for lg in legs if lg.instrument_id),
        title_summary=title_summary,
        rule_compatibility_notes=tuple(rule_compatibility_notes),
        divergence_or_rejection_reasons=tuple(divergence_or_rejection_reasons),
        is_dormant_near_miss=is_dormant,
        gap_to_breakeven_bps=gap_bps,
        structure=cand_struct,
        proof=proof,
        metadata=dict(metadata or {}),
    )


def _quick_l1_buy_cost_sum(
    legs_tokens_and_mkts: Sequence[Tuple[str, CanonicalBinaryMarket]],
    books: Mapping[str, InstrumentOrderBook],
) -> Optional[float]:
    """Fast L1 pre-check returning sum of V2 net unit ask costs across legs, or `None` if any ask book is empty."""
    tot = 0.0
    for tok, m in legs_tokens_and_mkts:
        bk = books.get(tok)
        if bk is not None and bk.asks:
            px = bk.asks[0].price
            c_u, _, _ = compute_net_buy_cost_per_delivered_share(
                px, fee_rate_bps=bk.fee_rate_bps, fee_exponent=bk.fee_exponent
            )
            tot += c_u
        else:
            return None
    return tot


_CLASS_SORT_RANK: Dict[str, int] = {
    OpportunityClass.CLASS_A.value: 0,
    OpportunityClass.CLASS_B.value: 1,
    OpportunityClass.CLASS_C.value: 3,
    OpportunityClass.CLASS_D.value: 4,
    OpportunityClass.CLASS_E.value: 5,
}


def _rank_and_cap_opportunities(
    cands: List[DetectedOpportunity],
    max_candidates: int,
) -> List[DetectedOpportunity]:
    """
    Sorts candidates so `CLASS_A`, `CLASS_B`, `is_dormant_near_miss`, `CLASS_C`, and `CLASS_D`
    rule-mismatch catches ALWAYS rank ahead of deep-OTM `CLASS_E` structures before capping.
    """
    def _sort_key(op: DetectedOpportunity) -> Tuple[int, float, str]:
        cls_val = op.proof.opportunity_class
        rk = 2 if (op.is_dormant_near_miss and cls_val == OpportunityClass.CLASS_E.value) else _CLASS_SORT_RANK.get(cls_val, 9)
        return (rk, -float(op.proof.gross_top_of_book_edge_per_unit), op.candidate_id)

    cands_sorted = sorted(cands, key=_sort_key)
    if max_candidates > 0 and len(cands_sorted) > max_candidates:
        return cands_sorted[:max_candidates]
    return cands_sorted


# ---------------------------------------------------------------------------
# 4. FAMILY D — Cross-Market Logical Arbitrage (`A => B`, `A perp B`, Containment)
# ---------------------------------------------------------------------------

_ELECTION_OFFICE_RE = re.compile(
    r"\b(presidential\s+election|presidency|president\s+of\s+the\s+united\s+states|"
    r"(?:[a-z]+(?:\s+[a-z]+)?)\s+(?:senate|gubernatorial|governor|mayoral|mayor)\s+election|"
    r"house\s+of\s+representatives|win\s+the\s+(?:house|senate|presidency))\b",
    re.IGNORECASE,
)
_PARTY_WIN_RE = re.compile(
    r"\b(republican(?:\s+party)?|democrat(?:ic)?(?:\s+party)?)\b.*?\b(?:win|control)\b",
    re.IGNORECASE,
)
_EXPLICIT_CANDIDATE_PARTY_RE = re.compile(
    r"(?:\(\s*([RD])\s*\)|\bas\s+the\s+(republican|democratic)\s+nominee\b|\b(republican|democratic)\s+candidate\b)",
    re.IGNORECASE,
)
_TRIFECTA_OR_SWEEP_RE = re.compile(
    r"\b(republican|democratic)\s+(?:trifecta|sweep)\b",
    re.IGNORECASE,
)
_NOMINATION_AND_WIN_RE = re.compile(
    r"^will\s+(.+?)\s+win\s+the\s+(20\d{2})\s+(republican|democratic)\s+presidential\s+nomination\s*\??$",
    re.IGNORECASE,
)
_PRES_WIN_CANDIDATE_RE = re.compile(
    r"^will\s+(.+?)\s+win\s+the\s+(20\d{2})\s+(?:us\s+)?presidential\s+election\s*\??$",
    re.IGNORECASE,
)
_POPULAR_AND_EC_WIN_RE = re.compile(
    r"^will\s+(.+?)\s+win\s+(?:both\s+)?the\s+popular\s+vote\s+and\s+(?:the\s+)?(?:presidency|presidential\s+election)(?:\s+in\s+(20\d{2}))?\s*\??$",
    re.IGNORECASE,
)
_SINGLE_WINNER_QUESTION_RE = re.compile(
    r"^will\s+(.+?)\s+(?:win|be\s+elected|be\s+named|be\s+appointed|be\s+the\s+next)\s+(.+?)\s*\??$",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(202[5-9]|203\d)\b")
_STOPWORDS = frozenset(
    {
        "will", "the", "be", "a", "an", "in", "on", "at", "to", "of", "for", "by", "or",
        "and", "is", "are", "was", "were", "this", "that", "from", "with", "as", "who", "what",
        "which", "market", "resolve", "yes", "no", "if",
    }
)


def _norm_entity_text(s: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", str(s or "").lower())
    return " ".join(cleaned.split())


def detect_family_d_logical_arbitrage(
    markets: Sequence[CanonicalBinaryMarket],
    books: Mapping[str, InstrumentOrderBook],
    *,
    verifier: Optional[UniversalArbVerifier] = None,
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
    max_candidates: int = 300,
) -> Tuple[List[DetectedOpportunity], Dict[str, int]]:
    """
    Family D — Cross-Market Logical Arbitrage:
      1. Formal Proposition Implications (`A => B` -> `1 NO_A + 1 YES_B` pays `min_w = $1.00`, `$2.00` on `(0,1)`):
         - Conjunction / Joint-to-Marginal (`Popular Vote AND Presidency => Presidency`,
           `Party Trifecta / Sweep => Party Senate & Party House`, `Pending-Cond & Outcome => Outcome`).
         - Party-Verified Candidate Victory (`Candidate X (R/D) wins Election => Party wins Election`,
           strictly rejecting unverified party-ballot candidates to `CLASS_D`!).
      2. Cross-Market & Non-NegRisk Mutual Exclusions (`A perp B` -> `1 NO_A + 1 NO_B` pays `min_w = $1.00`,
         `$2.00` on `(0,0)`, AND `$0.50 + $0.50 = $1.00` on `50-50` standalone cancellation!).
      3. Natural-Language Similarity Trap Guard: high token-overlap cross-event pairs lacking a proven
         logical rule template are explicitly caught and blocked at `CLASS_D` (`NATURAL_LANGUAGE_SIMILARITY_UNPROVEN`).
    """
    ver = verifier or UniversalArbVerifier()
    results: List[DetectedOpportunity] = []
    rejection_counts: Dict[str, int] = {}

    active = [
        m for m in markets
        if not m.closed_or_archived and m.is_standard_yes_no and m.yes_token_id and m.no_token_id
        and not m.is_d001_disputed_quarantined()
    ]

    def _bump(reason: str) -> None:
        rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    def _eval_implication(
        m_a: CanonicalBinaryMarket,
        m_b: CanonicalBinaryMarket,
        sub_type: str,
        notes: List[str],
        extra_reasons: Optional[List[str]] = None,
    ) -> None:
        if m_a.market_id == m_b.market_id:
            return
        reasons = list(extra_reasons or [])
        auth_a = extract_resolution_authority_signature(m_a)
        auth_b = extract_resolution_authority_signature(m_b)
        if auth_a != "UNSPECIFIED_AUTHORITY" and auth_b != "UNSPECIFIED_AUTHORITY" and auth_a != auth_b:
            reasons.append(f"RESOLUTION_AUTHORITY_MISMATCH:{auth_a}_vs_{auth_b}")

        exc_a = set(extract_exception_clause_signature(m_a))
        exc_b = set(extract_exception_clause_signature(m_b))
        if ("EXCLUDES_INTERIM_ACTING" in exc_a and "INCLUDES_INTERIM_ACTING" in exc_b) or (
            "INCLUDES_INTERIM_ACTING" in exc_a and "EXCLUDES_INTERIM_ACTING" in exc_b
        ):
            reasons.append("INTERIM_ACTING_OFFICEHOLDER_MISMATCH")

        # Asymmetric void check: `NO_A + YES_B` under `(cancel_a='50_50', cancel_b='NEGRISK_NO')` pays `0.5 + 0.0 = $0.50 < $1.00`!
        ca, cb = m_a.cancel_rule_tag, m_b.cancel_rule_tag
        if ca == "50_50" and cb == "NEGRISK_NO":
            reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")

        for r in reasons:
            _bump(r.split(":")[0])

        states = StateSpaceBuilder.two_market_logical_states(
            m_a.yes_token_id,
            m_a.no_token_id,
            m_b.yes_token_id,
            m_b.no_token_id,
            relation="A_IMPLIES_B" if not reasons else "UNCONSTRAINED",
            cancel_rule_a=ca,
            cancel_rule_b=cb,
            oracle_mismatch=any(r.startswith("RESOLUTION_AUTHORITY_MISMATCH") for r in reasons),
        )
        legs = [
            _build_leg_with_optional_inventory(m_a.no_token_id, m_a.market_id, f"NO[{m_a.group_item_title or m_a.question[:36]}]", holdings),
            _build_leg_with_optional_inventory(m_b.yes_token_id, m_b.market_id, f"YES[{m_b.group_item_title or m_b.question[:36]}]", holdings),
        ]
        cid = _make_candidate_id("D", sub_type, [m_a.market_id, m_b.market_id])
        rule_ok = len(reasons) == 0
        results.append(
            _finalize_detected_opportunity(
                ver,
                books,
                holdings,
                candidate_id=cid,
                family="FAMILY_D_CROSS_MARKET_LOGICAL",
                sub_type=sub_type,
                relationship_type="A_IMPLIES_B",
                edge_proof_status="VERIFIED_MATHEMATICAL" if rule_ok else "RULE_MISMATCH_REJECTED",
                markets=[m_a, m_b],
                legs=legs,
                states=states,
                title_summary=f"[{sub_type}] ({m_a.question[:48]}) => ({m_b.question[:48]})",
                rule_verified=rule_ok,
                rule_compatibility_notes=notes,
                divergence_or_rejection_reasons=reasons,
            )
        )

    # Index markets by `(year, office/chamber)` for Trifecta / Party / Candidate / Popular+EC links
    house_party_mkts: Dict[Tuple[str, str], CanonicalBinaryMarket] = {}
    senate_party_mkts: Dict[Tuple[str, str], CanonicalBinaryMarket] = {}
    pres_cand_mkts: Dict[Tuple[str, str], CanonicalBinaryMarket] = {}
    pres_party_mkts: Dict[Tuple[str, str], CanonicalBinaryMarket] = {}

    for m in active:
        q_l = m.question.lower()
        ev_l = f"{m.event_slug} {m.event_title}".lower()
        yr_m = _YEAR_RE.search(f"{m.question} {m.event_title} {m.end_date_iso}")
        yr = yr_m.group(1) if yr_m else "ANY"
        grp_l = m.group_item_title.lower()

        if ("which party will win the house" in ev_l or "win the house" in q_l) and "trifecta" not in ev_l and "sweep" not in ev_l:
            if "republican" in grp_l or "republican" in q_l:
                house_party_mkts.setdefault((yr, "republican"), m)
            elif "democrat" in grp_l or "democrat" in q_l:
                house_party_mkts.setdefault((yr, "democratic"), m)

        if ("which party will win the senate" in ev_l or "win the senate" in q_l) and "pending" not in ev_l and "trifecta" not in ev_l:
            if "republican" in grp_l or "republican" in q_l:
                senate_party_mkts.setdefault((yr, "republican"), m)
            elif "democrat" in grp_l or "democrat" in q_l:
                senate_party_mkts.setdefault((yr, "democratic"), m)

        mp_cand = _PRES_WIN_CANDIDATE_RE.match(m.question.strip())
        if mp_cand:
            cand_norm = _norm_entity_text(mp_cand.group(1))
            c_yr = mp_cand.group(2)
            if "party" in cand_norm and ("republican" in cand_norm or "democrat" in cand_norm):
                pty = "republican" if "republican" in cand_norm else "democratic"
                pres_party_mkts.setdefault((c_yr, pty), m)
            else:
                pres_cand_mkts.setdefault((c_yr, cand_norm), m)
        elif "presidential election winner" in ev_l and ("party" in ev_l or "party" in q_l):
            if "republican" in grp_l or "republican" in q_l:
                pres_party_mkts.setdefault((yr, "republican"), m)
            elif "democrat" in grp_l or "democrat" in q_l:
                pres_party_mkts.setdefault((yr, "democratic"), m)

    # D.1a: Trifecta / Sweep => Chamber Control (`A and B => A`, `A and B => B`)
    for m in active:
        blob = f"{m.event_title} {m.question}"
        m_tri = _TRIFECTA_OR_SWEEP_RE.search(blob)
        if m_tri and "no " not in m.group_item_title.lower():
            pty = "republican" if m_tri.group(1).lower().startswith("rep") else "democratic"
            yr_m = _YEAR_RE.search(f"{blob} {m.end_date_iso}")
            yr = yr_m.group(1) if yr_m else "ANY"
            if (yr, pty) in senate_party_mkts:
                _eval_implication(
                    m,
                    senate_party_mkts[(yr, pty)],
                    "TRIFECTA_IMPLIES_SENATE",
                    [f"{pty.title()} Trifecta/Sweep ({yr}) requires winning Senate control"],
                )
            if (yr, pty) in house_party_mkts:
                _eval_implication(
                    m,
                    house_party_mkts[(yr, pty)],
                    "TRIFECTA_IMPLIES_HOUSE",
                    [f"{pty.title()} Trifecta/Sweep ({yr}) requires winning House control"],
                )

        # D.1b: Popular Vote AND Presidency => Presidency
        m_pop = _POPULAR_AND_EC_WIN_RE.match(m.question.strip())
        if m_pop:
            c_norm = _norm_entity_text(m_pop.group(1))
            yr_m = _YEAR_RE.search(f"{m.question} {m.event_title} {m.end_date_iso}")
            c_yr = m_pop.group(2) or (yr_m.group(1) if yr_m else "ANY")
            if (c_yr, c_norm) in pres_cand_mkts:
                _eval_implication(
                    m,
                    pres_cand_mkts[(c_yr, c_norm)],
                    "CONJUNCTION_POPULAR_AND_PRESIDENCY",
                    ["Winning both Popular Vote and Presidency strictly implies winning Presidency"],
                )

        # D.1c: Pending-Condition Joint Outcome (`Cond C; R Senate`) => Marginal (`R Senate`)
        if "who-wins-the-senate-pending-" in m.event_slug.lower():
            grp_l = m.group_item_title.lower()
            yr_m = _YEAR_RE.search(f"{m.event_title} {m.end_date_iso}")
            yr = yr_m.group(1) if yr_m else "2026"
            if not grp_l.startswith("no "):
                if ("r senate" in grp_l or "republican" in grp_l) and (yr, "republican") in senate_party_mkts:
                    _eval_implication(
                        m,
                        senate_party_mkts[(yr, "republican")],
                        "CONDITIONAL_JOINT_IMPLIES_MARGINAL",
                        ["Joint event (Condition C AND R Senate) strictly implies R Senate"],
                    )
                elif ("d senate" in grp_l or "democrat" in grp_l) and (yr, "democratic") in senate_party_mkts:
                    _eval_implication(
                        m,
                        senate_party_mkts[(yr, "democratic")],
                        "CONDITIONAL_JOINT_IMPLIES_MARGINAL",
                        ["Joint event (Condition C AND D Senate) strictly implies D Senate"],
                    )

    # D.1d: Candidate Wins Presidency => Party Wins Presidency (ONLY when candidate ballot party is explicitly verified!)
    for (c_yr, c_norm), m_cand in pres_cand_mkts.items():
        party_match = _EXPLICIT_CANDIDATE_PARTY_RE.search(f"{m_cand.question} {m_cand.group_item_title} {m_cand.description}")
        if party_match:
            raw_p = (party_match.group(1) or party_match.group(2) or party_match.group(3) or "").lower()
            pty = "republican" if raw_p.startswith("r") else "democratic"
            if (c_yr, pty) in pres_party_mkts:
                _eval_implication(
                    m_cand,
                    pres_party_mkts[(c_yr, pty)],
                    "CANDIDATE_IMPLIES_PARTY",
                    [f"Explicit party ballot verification ({pty}) links candidate win to party win"],
                )
        else:
            # Check if there is a Party market for the same year: without explicit ballot-party rule,
            # an independent/third-party switch breaks `Candidate => Party` -> emit explicit CLASS_D guard if mispriced!
            for pty in ("republican", "democratic"):
                if pty in f"{m_cand.description}".lower() and (c_yr, pty) in pres_party_mkts:
                    _eval_implication(
                        m_cand,
                        pres_party_mkts[(c_yr, pty)],
                        "CANDIDATE_IMPLIES_PARTY_UNVERIFIED_BALLOT",
                        ["Candidate description mentions party without binding ballot-ticket clause"],
                        extra_reasons=["UNVERIFIED_PARTY_BALLOT_RULE"],
                    )

    # D.2: Mutual Exclusion (`A perp B` -> `1 NO_A + 1 NO_B`) across non-NegRisk single-winner slates & cross-event opposites
    by_single_winner_prize: Dict[str, List[Tuple[str, CanonicalBinaryMarket]]] = {}
    for m in active:
        # Skip intra-event NegRisk slates here only if already covered by Family C? Wait: cross-event or non-NegRisk
        # single-winner slates are Family D's core mutual-exclusion domain!
        mw = _SINGLE_WINNER_QUESTION_RE.match(m.question.strip()) if (
            m.question[:5].lower() == "will " and (" win " in m.question.lower() or " be " in m.question.lower())
        ) else None
        if mw:
            subj = _norm_entity_text(mw.group(1))
            raw_prize = mw.group(2).strip()
            prize = _norm_entity_text(raw_prize)
            if subj and prize and len(prize) >= 8 and not m.is_placeholder_outcome and not m.is_other_outcome:
                # `BUG-LS-2`: Strip benign 4-digit election/season years (`2026..2039`) and league names (`Formula 1`, `Ligue 1`),
                # then reject ANY remaining count/range digits, `%`, plural count nouns (`seats`, `votes`, `medals`, `games`, `states`, ...),
                # or multi-winner / range quantifiers (`between`, `at least`, `more than`, `top`, `playoffs`, `nominations`)!
                raw_prize_no_yr = re.sub(r"\b(?:19|20)\d{2}\b", "", raw_prize.lower())
                raw_prize_no_yr = re.sub(r"\b(?:formula|ligue|division|tier)\s+\d+\b", "", raw_prize_no_yr)
                is_multi_or_count_predicate = bool(
                    re.search(
                        r"\d|%"
                        r"|\b(?:top|playoffs?|a\s+medal|medals|nominat\w*|a\s+seat|seats|votes|games|matches|states|"
                        r"districts|awards|stages|rounds|sets|maps|points|goals|titles|races|counties|provinces|regions|"
                        r"between|at\s+least|at\s+most|more\s+than|fewer\s+than|less\s+than|over|under|or\s+more|or\s+fewer)\b",
                        raw_prize_no_yr,
                    )
                )
                if not is_multi_or_count_predicate:
                    auth = extract_resolution_authority_signature(m)
                    by_single_winner_prize.setdefault(f"{prize}::{auth}", []).append((subj, m))

    for prize_key, entries in by_single_winner_prize.items():
        if len(entries) < 2:
            continue
        # Focus on cross-event pairs OR non-NegRisk multi-market events
        entries_sorted = sorted(
            entries,
            key=lambda pair: (
                books[pair[1].no_token_id].asks[0].price
                if (pair[1].no_token_id in books and books[pair[1].no_token_id].asks)
                else 1.5
            ),
        )
        checked_pairs = 0
        for i in range(min(len(entries_sorted), 8)):
            subj_a, m_a = entries_sorted[i]
            for j in range(i + 1, min(len(entries_sorted), 10)):
                subj_b, m_b = entries_sorted[j]
                if subj_a == subj_b or m_a.market_id == m_b.market_id:
                    continue
                if m_a.event_id == m_b.event_id and m_a.neg_risk and m_b.neg_risk:
                    # Intra-event NegRisk NO pairs belong to Family C unless cross-event
                    continue
                if checked_pairs >= 6:
                    break
                l1_sum = _quick_l1_buy_cost_sum([(m_a.no_token_id, m_a), (m_b.no_token_id, m_b)], books)
                if l1_sum is not None and l1_sum > 1.0 + DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT and checked_pairs >= 1:
                    continue
                checked_pairs += 1
                reasons_me: List[str] = []
                is_party_a = bool(re.search(r"\b(?:party|republican|democratic|democrat|labour|conservative|liberal|green|coalition)\b", subj_a))
                is_party_b = bool(re.search(r"\b(?:party|republican|democratic|democrat|labour|conservative|liberal|green|coalition)\b", subj_b))
                if is_party_a != is_party_b:
                    reasons_me.append("PARTY_VS_CANDIDATE_NOT_MUTUALLY_EXCLUSIVE")
                if m_a.end_ts and m_b.end_ts and abs(m_a.end_ts - m_b.end_ts) > 7 * 86400.0:
                    reasons_me.append("DISJOINT_CUTOFF_WINDOW_MISMATCH")
                for r in reasons_me:
                    _bump(r)
                states_me = StateSpaceBuilder.two_market_logical_states(
                    m_a.yes_token_id,
                    m_a.no_token_id,
                    m_b.yes_token_id,
                    m_b.no_token_id,
                    relation="MUTUAL_EXCLUSION" if not reasons_me else "UNCONSTRAINED",
                    cancel_rule_a=m_a.cancel_rule_tag,
                    cancel_rule_b=m_b.cancel_rule_tag,
                )
                legs_me = [
                    _build_leg_with_optional_inventory(m_a.no_token_id, m_a.market_id, f"NO[{subj_a[:28]}]", holdings),
                    _build_leg_with_optional_inventory(m_b.no_token_id, m_b.market_id, f"NO[{subj_b[:28]}]", holdings),
                ]
                cid_me = _make_candidate_id("D", "MUTUAL_EXCLUSION", sorted([m_a.market_id, m_b.market_id]))
                results.append(
                    _finalize_detected_opportunity(
                        ver,
                        books,
                        holdings,
                        candidate_id=cid_me,
                        family="FAMILY_D_CROSS_MARKET_LOGICAL",
                        sub_type="MUTUAL_EXCLUSION_NO_PAIR",
                        relationship_type="MUTUAL_EXCLUSION",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_me else "RULE_MISMATCH_REJECTED",
                        markets=[m_a, m_b],
                        legs=legs_me,
                        states=states_me,
                        title_summary=f"[MUTUAL_EXCLUSION] NO({subj_a[:28]}) + NO({subj_b[:28]}) on '{prize_key.split('::')[0][:40]}'",
                        rule_verified=len(reasons_me) == 0,
                        rule_compatibility_notes=["Single-winner office/title guarantees at most one YES (`NO_A + NO_B >= $1.00`)"],
                        divergence_or_rejection_reasons=reasons_me,
                    )
                )

    return _rank_and_cap_opportunities(results, max_candidates), rejection_counts


def evaluate_explicit_logical_pair(
    m_a: CanonicalBinaryMarket,
    m_b: CanonicalBinaryMarket,
    books: Mapping[str, InstrumentOrderBook],
    *,
    claimed_relation: str = "A_IMPLIES_B",
    has_formal_rule_proof: bool = False,
    verifier: Optional[UniversalArbVerifier] = None,
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
) -> DetectedOpportunity:
    """
    Direct pair verifier for Family D (and `@qa-auditor` adversarial probes):
      - Enforces exact implication direction (`A_IMPLIES_B` -> `NO_A + YES_B`, NEVER converse `YES_A + NO_B`!).
      - Blocks natural-language similarity (`has_formal_rule_proof=False`) at `CLASS_D`!
      - Blocks authority / void asymmetry mismatches at `CLASS_D`!
    """
    ver = verifier or UniversalArbVerifier()
    rel = str(claimed_relation or "A_IMPLIES_B").strip().upper()
    reasons: List[str] = []
    if not has_formal_rule_proof:
        reasons.append("NATURAL_LANGUAGE_SIMILARITY_ONLY_NO_RULE_PROOF")

    auth_a = extract_resolution_authority_signature(m_a)
    auth_b = extract_resolution_authority_signature(m_b)
    if auth_a != "UNSPECIFIED_AUTHORITY" and auth_b != "UNSPECIFIED_AUTHORITY" and auth_a != auth_b:
        reasons.append(f"RESOLUTION_AUTHORITY_MISMATCH:{auth_a}_vs_{auth_b}")

    ca, cb = m_a.cancel_rule_tag, m_b.cancel_rule_tag
    if rel == "A_IMPLIES_B":
        if ca == "50_50" and cb == "NEGRISK_NO":
            reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
        legs = [
            _build_leg_with_optional_inventory(m_a.no_token_id, m_a.market_id, f"NO[{m_a.question[:32]}]", holdings),
            _build_leg_with_optional_inventory(m_b.yes_token_id, m_b.market_id, f"YES[{m_b.question[:32]}]", holdings),
        ]
    elif rel == "B_IMPLIES_A":
        if cb == "50_50" and ca == "NEGRISK_NO":
            reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
        legs = [
            _build_leg_with_optional_inventory(m_b.no_token_id, m_b.market_id, f"NO[{m_b.question[:32]}]", holdings),
            _build_leg_with_optional_inventory(m_a.yes_token_id, m_a.market_id, f"YES[{m_a.question[:32]}]", holdings),
        ]
    elif rel in {"MUTUAL_EXCLUSION", "DISJOINT"}:
        legs = [
            _build_leg_with_optional_inventory(m_a.no_token_id, m_a.market_id, f"NO[{m_a.question[:32]}]", holdings),
            _build_leg_with_optional_inventory(m_b.no_token_id, m_b.market_id, f"NO[{m_b.question[:32]}]", holdings),
        ]
    else:
        reasons.append(f"UNSUPPORTED_LOGICAL_RELATION:{rel}")
        legs = [
            _build_leg_with_optional_inventory(m_a.yes_token_id, m_a.market_id, f"YES[{m_a.question[:32]}]", holdings),
            _build_leg_with_optional_inventory(m_b.no_token_id, m_b.market_id, f"NO[{m_b.question[:32]}]", holdings),
        ]

    states = StateSpaceBuilder.two_market_logical_states(
        m_a.yes_token_id,
        m_a.no_token_id,
        m_b.yes_token_id,
        m_b.no_token_id,
        relation=rel if not reasons else "UNCONSTRAINED",
        cancel_rule_a=ca,
        cancel_rule_b=cb,
        oracle_mismatch=any(r.startswith("RESOLUTION_AUTHORITY_MISMATCH") for r in reasons),
    )
    rule_ok = len(reasons) == 0
    return _finalize_detected_opportunity(
        ver,
        books,
        holdings,
        candidate_id=_make_candidate_id("D", rel, [m_a.market_id, m_b.market_id]),
        family="FAMILY_D_CROSS_MARKET_LOGICAL",
        sub_type=f"EXPLICIT_{rel}",
        relationship_type=rel,
        edge_proof_status="VERIFIED_MATHEMATICAL" if rule_ok else "RULE_MISMATCH_REJECTED",
        markets=[m_a, m_b],
        legs=legs,
        states=states,
        title_summary=f"{m_a.question[:48]} [{rel}] {m_b.question[:48]}",
        rule_verified=rule_ok,
        rule_compatibility_notes=["Formal proposition proof verified"] if rule_ok else [],
        divergence_or_rejection_reasons=reasons,
    )


# ---------------------------------------------------------------------------
# 5. FAMILY E — Temporal & Deadline Arbitrage (`Event by T1 => Event by T2`)
# ---------------------------------------------------------------------------

_MONTH_NUMS: Dict[str, int] = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_DEADLINE_TAIL_RE = re.compile(
    r"\s+(?P<prep>by|before|on\s+or\s+before|through|until|prior\s+to|in)\s+"
    r"(?P<date_expr>"
    r"(?:end\s+of\s+)?(?:q[1-4]\s+20\d{2}|20\d{2})"
    r"|(?:january|february|march|april|may|june|july|august|september|october|november|december"
    r"|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+\d{1,2}(?:,?\s*20\d{2})?"
    r"|(?:end\s+of\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+20\d{2})?"
    r"|20\d{2}-\d{2}-\d{2}"
    r")(?:\s+(?:ET|EDT|EST|PT|PDT|PST|CT|CDT|CST|MT|UTC|GMT|CET|CEST|EET|IRST|JST|HKT|KST))?\s*\??$",
    re.IGNORECASE,
)
_EXPLICIT_TIME_OF_DAY_RE = re.compile(
    r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?\b",
    re.IGNORECASE,
)
_SURVIVAL_STEM_RE = re.compile(
    r"\b(?:remain(?:s)?\s+(?:in\s+office|in\s+effect|above|leader|ceo|president|prime\s+minister)"
    r"|continue(?:s)?\s+through|stay(?:s)?\s+in\s+office|hold(?:s)?\s+through|still\s+be\s+in\s+office)\b",
    re.IGNORECASE,
)
_PERIOD_ISOLATED_PREP_RE = re.compile(
    r"\b(?:during\s+(?:the\s+)?(?:month|quarter|week)|between\s+[a-z]+\s+\d+\s+and\s+[a-z]+\s+\d+)\b",
    re.IGNORECASE,
)


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def _parse_cutoff_epoch_in_tz(
    date_expr: str,
    prep: str,
    tz_iana: str,
    description: str,
    ref_end_ts: Optional[float],
) -> Optional[Tuple[float, bool]]:
    """
    Parses `(cutoff_utc_epoch, is_isolated_period)` in the market's exact contractual timezone `tz_iana`.
    Note: `"before Month DD"` with no explicit `11:59 PM` in rules means `00:00:00` at start of `Month DD`
    UNLESS Polymarket's description explicitly states `"by Month DD, 11:59 PM"`! We inspect `description` first!
    """
    tz_obj = resolve_tz(tz_iana)
    de = " ".join(date_expr.strip().lower().replace(".", "").split())
    pr = " ".join(prep.strip().lower().split())
    desc_l = description.lower()

    # `BUG-LS-4`: Extract explicit time-of-day ONLY when anchored to a resolution/deadline/close clause
    # (never grab unrelated background prose like `"BLS releases reports at 8:30 AM ET"` ahead of `"by Nov 30, 11:59 PM ET"`!).
    hh, mm, ss = 23, 59, 59
    strict_before_midnight = False
    deadline_tod_matches: List[re.Match[str]] = []
    for cand_tod in _EXPLICIT_TIME_OF_DAY_RE.finditer(description):
        ctx_before = description[max(0, cand_tod.start() - 80) : cand_tod.start()].lower()
        ctx_after = description[cand_tod.end() : min(len(description), cand_tod.end() + 45)].lower()
        # Reject background agency release-schedule sentences (`releases/published/opens at 8:30 AM`) unless immediately inside `resolve ... by`
        is_release_prose = bool(re.search(r"\b(?:releases?|released|publishes?|published|scheduled|opens?)\b[^.!?\n]*$", ctx_before))
        has_cutoff_cue = bool(
            re.search(
                r"(?:\b(?:by|before|prior\s+to|until|through|cutoff|deadline|specified\s+date|end\s+of|close(?:\s+price)?\s+at|"
                r"closing(?:\s+snapshot)?\s+at|snapshot\s+at|settlement(?:\s+price)?\s+at|resolves?\s+[^\n.!?]{0,60}\bat)\b"
                r"|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
                r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,?\s*20\d{2})?\s*,?\s*$)",
                ctx_before,
            )
            or re.search(r"^\s*(?:et|est|edt|utc|gmt|pt|ct)?\s*(?:on\s+[a-z]+\s+\d{1,2}|cutoff|deadline)", ctx_after)
        )
        if has_cutoff_cue and not is_release_prose:
            deadline_tod_matches.append(cand_tod)

    m_tod = deadline_tod_matches[-1] if deadline_tod_matches else None
    if m_tod:
        raw_h = int(m_tod.group(1))
        raw_m = int(m_tod.group(2))
        raw_s = int(m_tod.group(3) or (59 if raw_m == 59 else 0))
        ampm = (m_tod.group(4) or "").upper()
        if ampm == "PM" and raw_h < 12:
            raw_h += 12
        elif ampm == "AM" and raw_h == 12:
            raw_h = 0
        if 0 <= raw_h <= 23 and 0 <= raw_m <= 59:
            hh, mm, ss = raw_h, raw_m, raw_s
    elif pr in {"before", "prior to"} and "11:59" not in desc_l and "23:59" not in desc_l and "end of" not in de:
        # Pure `"before April 2, 2027"` without `11:59 PM` in rules means strictly before April 2 (`Apr 1 23:59:59`)!
        hh, mm, ss = 0, 0, 0
        strict_before_midnight = True

    def _adj(ts_val: float) -> float:
        return (ts_val - 1.0) if strict_before_midnight else ts_val

    ref_year = datetime.fromtimestamp(ref_end_ts, tz=timezone.utc).year if ref_end_ts else 2026

    # 1. ISO `YYYY-MM-DD`
    m_iso = re.match(r"^(20\d{2})-(\d{2})-(\d{2})$", de)
    if m_iso:
        dt = datetime(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)), hh, mm, ss, tzinfo=tz_obj)
        return _adj(float(dt.timestamp())), False

    # 2. Quarter `(end of )?q[1-4] YYYY`
    m_q = re.match(r"^(?:end\s+of\s+)?q([1-4])\s+(20\d{2})$", de)
    if m_q:
        q_idx, yr = int(m_q.group(1)), int(m_q.group(2))
        if pr in {"before", "prior to"} and "end of" not in de:
            start_m = (q_idx - 1) * 3 + 1
            dt = datetime(yr, start_m, 1, 0, 0, 0, tzinfo=tz_obj)
            return float(dt.timestamp()) - 1.0, False
        end_m = q_idx * 3
        ld = _last_day_of_month(yr, end_m)
        dt = datetime(yr, end_m, ld, 23, 59, 59, tzinfo=tz_obj)
        return float(dt.timestamp()), (pr == "in")

    # 3. Year `(end of )?YYYY`
    m_yr = re.match(r"^(?:end\s+of\s+)?(20\d{2})$", de)
    if m_yr:
        yr = int(m_yr.group(1))
        if pr in {"before", "prior to"} and "end of" not in de:
            # `"before 2027"` ALWAYS means Dec 31, 2026 23:59:59 (`Jan 1, 2027 00:00:00 - 1s`), even when rules state `"Dec 31, 2026, 11:59 PM"`!
            dt = datetime(yr, 1, 1, 0, 0, 0, tzinfo=tz_obj)
            return float(dt.timestamp()) - 1.0, False
        dt = datetime(yr, 12, 31, 23, 59, 59, tzinfo=tz_obj)
        return float(dt.timestamp()), False

    # 4. `Month DD(, YYYY)?`
    m_md = re.match(r"^([a-z]+)\s+(\d{1,2})(?:,?\s*(20\d{2}))?$", de)
    if m_md and m_md.group(1) in _MONTH_NUMS:
        mon = _MONTH_NUMS[m_md.group(1)]
        day = int(m_md.group(2))
        if m_md.group(3):
            yr = int(m_md.group(3))
            try:
                return _adj(float(datetime(yr, mon, day, hh, mm, ss, tzinfo=tz_obj).timestamp())), False
            except ValueError:
                return None
        # Yearless `Month DD` (handle `Dec 31` when `endDate` is `Jan 1 04:59Z` or umbrella `endDate`!)
        cands: List[float] = []
        for y_try in (ref_year - 1, ref_year, ref_year + 1):
            try:
                ts_c = _adj(float(datetime(y_try, mon, day, hh, mm, ss, tzinfo=tz_obj).timestamp()))
                cands.append(ts_c)
            except ValueError:
                continue
        if not cands:
            return None
        if ref_end_ts is not None:
            causal = [t for t in cands if t <= ref_end_ts + 2.0 * 86400.0]
            pool = causal if causal else cands
            return min(pool, key=lambda t: abs(t - ref_end_ts)), False
        return cands[1] if len(cands) > 1 else cands[0], False

    # 5. `(end of )?Month( YYYY)?`
    m_mo = re.match(r"^(?:end\s+of\s+)?([a-z]+)(?:\s+(20\d{2}))?$", de)
    if m_mo and m_mo.group(1) in _MONTH_NUMS:
        mon = _MONTH_NUMS[m_mo.group(1)]
        yr = int(m_mo.group(2)) if m_mo.group(2) else ref_year
        if not m_mo.group(2) and ref_end_ts is not None:
            # Pick year closest to `ref_end_ts` without exceeding `ref_end_ts + 5d`
            best_y = yr
            best_gap = 1e18
            for y_try in (ref_year - 1, ref_year, ref_year + 1):
                ld_t = _last_day_of_month(y_try, mon)
                ts_t = float(datetime(y_try, mon, ld_t, 23, 59, 59, tzinfo=tz_obj).timestamp())
                if ts_t <= ref_end_ts + 5.0 * 86400.0 and abs(ts_t - ref_end_ts) < best_gap:
                    best_gap = abs(ts_t - ref_end_ts)
                    best_y = y_try
            yr = best_y
        if pr == "before" and "end of" not in de:
            return float(datetime(yr, mon, 1, 0, 0, 0, tzinfo=tz_obj).timestamp()), False
        ld = _last_day_of_month(yr, mon)
        is_iso = pr == "in" and "end of" not in de
        return float(datetime(yr, mon, ld, 23, 59, 59, tzinfo=tz_obj).timestamp()), is_iso

    return None


@dataclass(frozen=True)
class ParsedTemporalContract:
    market: CanonicalBinaryMarket
    proposition_stem: str
    temporal_mode: str  # "FIRST_PASSAGE" | "SURVIVAL" | "ISOLATED_WINDOW"
    cutoff_ts_utc: float
    window_start_ts_utc: Optional[float]
    tz_tag: str
    tz_iana: str
    authority_sig: str
    exception_sig: Tuple[str, ...]


def parse_temporal_contract(m: CanonicalBinaryMarket) -> Optional[ParsedTemporalContract]:
    """Parses any binary market with an explicit temporal cutoff across ALL Polymarket categories."""
    if not m.is_standard_yes_no or m.closed_or_archived or not m.yes_token_id or not m.no_token_id:
        return None
    if m.sports_market_type or m.is_placeholder_outcome or m.is_other_outcome:
        return None
    if m.is_d001_disputed_quarantined():
        return None

    q_clean = " ".join(m.question.strip().split())
    q_clean_l = q_clean.lower()
    mt = _DEADLINE_TAIL_RE.search(q_clean) if any(
        kw in q_clean_l for kw in (" by ", " before ", " through ", " until ", " prior to ", " in 20", " in q")
    ) else None
    stem_raw = ""
    prep = "by"
    date_expr = ""
    if mt:
        stem_raw = q_clean[: mt.start()].strip()
        prep = mt.group("prep")
        date_expr = mt.group("date_expr")
    elif m.group_item_title and ("by " in m.event_title.lower() or "before " in m.event_title.lower() or "through " in m.event_title.lower()):
        # Multi-market event where `event_title` is `"Event X by...?"` and `groupItemTitle` is `"December 31"`
        ev_clean = re.sub(r"\.\.\.\??$|\s+by\s*\??$|\s+before\s*\??$", "", m.event_title.strip(), flags=re.I)
        stem_raw = ev_clean
        prep = "through" if "through" in m.event_title.lower() else ("before" if "before" in m.event_title.lower() else "by")
        date_expr = m.group_item_title.strip()
    else:
        return None

    tz_tag, tz_iana = extract_timezone_signature(m)
    parsed_cut = _parse_cutoff_epoch_in_tz(date_expr, prep, tz_iana, m.description, m.end_ts)
    if parsed_cut is None:
        return None
    cutoff_ts, is_iso_month = parsed_cut

    blob_l = f"{m.question} {m.description}".lower()
    stem_l = stem_raw.lower()
    # Strip embedded complement clauses like `"agrees not to join"` / `"votes not to"` before testing outer main-verb negation!
    stem_outer_l = re.sub(
        r"\b(?:agrees?|pledges?|votes?|commits?|vows?|decides?|promises?|plans?)\s+not\s+to\b",
        "agrees_to",
        stem_l,
    )
    has_stem_negation = bool(
        re.search(r"\b(?:not|never|fail(?:s)?\s+to|without|no\s+(?!longer\b)[a-z]+)\b|n't\b", stem_outer_l)
    )
    # Reversible status predicates like `"Perim Island no longer under Houthi control by Date"` can flip and revert
    # between T1 and T2 unless explicitly defined as irreversible `"at any point"`, so quarantine as `ISOLATED_WINDOW`.
    has_reversible_status_phrase = bool(
        re.search(r"\bno\s+longer\b", stem_l) and not re.search(r"\bat\s+any\s+(?:point|time)\b", blob_l)
    )
    if _PERIOD_ISOLATED_PREP_RE.search(blob_l) or is_iso_month or has_reversible_status_phrase:
        mode = "ISOLATED_WINDOW"
    elif _SURVIVAL_STEM_RE.search(blob_l) or prep.strip().lower() in {"through", "until"} or has_stem_negation:
        # `"Will X NOT happen by T?"` is mathematically a survival predicate (`tau > T2 => tau > T1`, i.e., `B_IMPLIES_A`!)
        mode = "SURVIVAL"
    else:
        mode = "FIRST_PASSAGE"

    # Normalize proposition stem (preserving `+`, `-`, `<`, `>`, `=`, numbers, negations, and entity tokens)
    stem_norm = re.sub(r"^will\s+", "", stem_raw.lower())
    stem_norm = re.sub(r"[^a-z0-9$%+<>=\-\s]", " ", stem_norm)
    stem_norm = " ".join(stem_norm.split())
    if len(stem_norm) < 8:
        return None

    return ParsedTemporalContract(
        market=m,
        proposition_stem=stem_norm,
        temporal_mode=mode,
        cutoff_ts_utc=cutoff_ts,
        window_start_ts_utc=m.start_ts,
        tz_tag=tz_tag,
        tz_iana=tz_iana,
        authority_sig=extract_resolution_authority_signature(m),
        exception_sig=extract_exception_clause_signature(m),
    )


def detect_family_e_temporal_deadline_arbitrage(
    markets: Sequence[CanonicalBinaryMarket],
    books: Mapping[str, InstrumentOrderBook],
    *,
    verifier: Optional[UniversalArbVerifier] = None,
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
    now_ts: Optional[float] = None,
    max_candidates: int = 350,
) -> Tuple[List[DetectedOpportunity], Dict[str, int]]:
    """
    Family E — Full-Universe Temporal & Deadline Arbitrage (`Event by T1 => Event by T2`):
      - Groups parsed temporal propositions across ALL categories & BOTH intra-event and cross-event markets.
      - Enforces strict parity on:
          (1) `resolution_authority` (`authority_sig`),
          (2) explicit `timezone` (`tz_tag`, rejecting unspecified or mismatched timezones to `CLASS_D`),
          (3) `exception_sig` & void/cancellation rules (`50-50` vs `NEGRISK_NO`),
          (4) `FIRST_PASSAGE` vs `SURVIVAL` vs `ISOLATED_WINDOW` semantics.
    """
    ver = verifier or UniversalArbVerifier()
    now_f = float(time.time() if now_ts is None else now_ts)
    results: List[DetectedOpportunity] = []
    rejection_counts: Dict[str, int] = {}

    def _bump(r: str) -> None:
        rejection_counts[r] = rejection_counts.get(r, 0) + 1

    by_stem: Dict[str, List[ParsedTemporalContract]] = {}
    for m in markets:
        pt = parse_temporal_contract(m)
        if pt is not None and pt.cutoff_ts_utc > now_f - 3600.0:
            by_stem.setdefault(pt.proposition_stem, []).append(pt)

    for stem, group in by_stem.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda x: x.cutoff_ts_utc)
        n_g = len(group)
        # Evaluate adjacent rungs + best-ask cross pairs so O(R) scaling holds even on 20-rung ladders
        pair_indices: List[Tuple[int, int]] = []
        for i in range(n_g - 1):
            pair_indices.append((i, i + 1))
        if n_g <= 12:
            for i in range(n_g):
                for j in range(i + 2, n_g):
                    pair_indices.append((i, j))
        else:
            # Also pair global cheapest early-NO with global cheapest late-YES
            for i in range(min(4, n_g)):
                for j in range(max(i + 2, n_g - 4), n_g):
                    pair_indices.append((i, j))

        for i, j in dict.fromkeys(pair_indices):
            c1, c2 = group[i], group[j]
            if c1.market.market_id == c2.market.market_id:
                continue
            # Skip identical timestamp duplicates (handled by Family I)
            if abs(c2.cutoff_ts_utc - c1.cutoff_ts_utc) < 60.0 and c1.tz_tag == c2.tz_tag:
                continue

            reasons: List[str] = []
            tz_mismatch = False
            oracle_mismatch = False

            # 1. Timezone verification
            if (
                c1.tz_tag == "UNSPECIFIED"
                or c2.tz_tag == "UNSPECIFIED"
                or c1.tz_tag.startswith("CONFLICTING_TZ_")
                or c2.tz_tag.startswith("CONFLICTING_TZ_")
            ):
                reasons.append(f"TIMEZONE_UNSPECIFIED:{c1.tz_tag}_vs_{c2.tz_tag}")
                tz_mismatch = True
            elif c1.tz_tag != c2.tz_tag:
                reasons.append(f"TIMEZONE_MISMATCH:{c1.tz_tag}_vs_{c2.tz_tag}")
                tz_mismatch = True

            # 2. Resolution authority verification
            if c1.authority_sig == "UNSPECIFIED_AUTHORITY" or c2.authority_sig == "UNSPECIFIED_AUTHORITY":
                # Allow intra-event identical non-empty descriptions (>= 60 chars) sharing exact resolvedBy
                if not (
                    c1.market.event_id == c2.market.event_id
                    and c1.market.resolved_by
                    and c1.market.resolved_by == c2.market.resolved_by
                    and len(c1.market.description) >= 60
                ):
                    reasons.append("RESOLUTION_AUTHORITY_UNSPECIFIED")
                    oracle_mismatch = True
            elif c1.authority_sig != c2.authority_sig:
                reasons.append(f"RESOLUTION_AUTHORITY_MISMATCH:{c1.authority_sig}_vs_{c2.authority_sig}")
                oracle_mismatch = True

            # 3. Exceptional early-resolution / void clause verification
            if c1.exception_sig != c2.exception_sig:
                reasons.append(f"EXCEPTIONAL_CLAUSE_MISMATCH:{c1.exception_sig}_vs_{c2.exception_sig}")
            if c1.market.resolved_by and c2.market.resolved_by and c1.market.resolved_by != c2.market.resolved_by:
                reasons.append("UMA_ADAPTER_MISMATCH")

            # 4. Temporal mode (`FIRST_PASSAGE` vs `SURVIVAL` vs `ISOLATED_WINDOW`)
            relation = "A_IMPLIES_B"
            m_early, m_late = c1.market, c2.market
            if c1.temporal_mode != c2.temporal_mode:
                reasons.append(f"TEMPORAL_MODE_MISMATCH:{c1.temporal_mode}_vs_{c2.temporal_mode}")
            elif c1.temporal_mode == "ISOLATED_WINDOW":
                reasons.append("RESET_WINDOW_NON_CONTAINMENT")
            elif c1.temporal_mode == "SURVIVAL":
                # Survival through T2 (`c2`) => Survival through T1 (`c1`), i.e., `B_IMPLIES_A` (`NO_T2 + YES_T1`)!
                relation = "B_IMPLIES_A"

            # Check `endDate` monotonicity sanity guard (`m_early` must never expire strictly after `m_late`!)
            if m_early.end_ts is not None and m_late.end_ts is not None and m_early.end_ts > m_late.end_ts + 3600.0:
                reasons.append("CUTOFF_VS_ENDDATE_ORDER_INVERSION")

            # Check start-window inclusion (`start_2 <= start_1` for first-passage so early history cannot make T1=1, T2=0!)
            if (
                relation == "A_IMPLIES_B"
                and c1.window_start_ts_utc is not None
                and c2.window_start_ts_utc is not None
                and c2.window_start_ts_utc > c1.window_start_ts_utc + 3600.0
            ):
                reasons.append("LATE_RUNG_START_DATE_AFTER_EARLY_RUNG_START")

            ca, cb = m_early.cancel_rule_tag, m_late.cancel_rule_tag
            if relation == "A_IMPLIES_B" and ca == "50_50" and cb == "NEGRISK_NO":
                reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
            elif relation == "B_IMPLIES_A" and cb == "50_50" and ca == "NEGRISK_NO":
                reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")

            for r in reasons:
                _bump(r.split(":")[0])

            if relation == "A_IMPLIES_B":
                legs = [
                    _build_leg_with_optional_inventory(
                        m_early.no_token_id, m_early.market_id, f"NO[{m_early.group_item_title or m_early.question[:30]}]", holdings
                    ),
                    _build_leg_with_optional_inventory(
                        m_late.yes_token_id, m_late.market_id, f"YES[{m_late.group_item_title or m_late.question[:30]}]", holdings
                    ),
                ]
            else:
                legs = [
                    _build_leg_with_optional_inventory(
                        m_late.no_token_id, m_late.market_id, f"NO[{m_late.group_item_title or m_late.question[:30]}]", holdings
                    ),
                    _build_leg_with_optional_inventory(
                        m_early.yes_token_id, m_early.market_id, f"YES[{m_early.group_item_title or m_early.question[:30]}]", holdings
                    ),
                ]

            # Prune uninteresting deep out-of-the-money valid pairs on huge ladders while always keeping
            # (a) rule mismatches (for audit visibility), (b) net arbs (`<= 1.00`), and (c) dormant near-misses (`<= 1.035`)!
            if not reasons and (j - i) > 1:
                l1_cost = _quick_l1_buy_cost_sum(
                    [(legs[0].instrument_id, m_early if relation == "A_IMPLIES_B" else m_late),
                     (legs[1].instrument_id, m_late if relation == "A_IMPLIES_B" else m_early)],
                    books,
                )
                if l1_cost is None or l1_cost > 1.0 + DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT:
                    continue

            states = StateSpaceBuilder.two_market_logical_states(
                m_early.yes_token_id,
                m_early.no_token_id,
                m_late.yes_token_id,
                m_late.no_token_id,
                relation=relation if not reasons else "UNCONSTRAINED",
                cancel_rule_a=ca,
                cancel_rule_b=cb,
                timezone_mismatch=tz_mismatch,
                oracle_mismatch=oracle_mismatch,
            )
            rule_ok = len(reasons) == 0
            sub_t = "TEMPORAL_SURVIVAL_BOX" if c1.temporal_mode == "SURVIVAL" else "TEMPORAL_DEADLINE_IMPLICATION"
            results.append(
                _finalize_detected_opportunity(
                    ver,
                    books,
                    holdings,
                    candidate_id=_make_candidate_id("E", sub_t, [m_early.market_id, m_late.market_id]),
                    family="FAMILY_E_TEMPORAL_DEADLINE",
                    sub_type=sub_t,
                    relationship_type=relation,
                    edge_proof_status="VERIFIED_MATHEMATICAL" if rule_ok else "RULE_MISMATCH_REJECTED",
                    markets=[m_early, m_late],
                    legs=legs,
                    states=states,
                    title_summary=f"[{sub_t}] {stem[:42]} ({c1.cutoff_ts_utc:.0f} -> {c2.cutoff_ts_utc:.0f} {c1.tz_tag})",
                    rule_verified=rule_ok,
                    rule_compatibility_notes=[
                        f"tz={c1.tz_tag}",
                        f"authority={c1.authority_sig}",
                        f"mode={c1.temporal_mode}",
                    ],
                    divergence_or_rejection_reasons=reasons,
                    metadata={
                        "proposition_stem": stem,
                        "early_cutoff_ts": c1.cutoff_ts_utc,
                        "late_cutoff_ts": c2.cutoff_ts_utc,
                        "timezone": c1.tz_tag,
                    },
                )
            )

    return _rank_and_cap_opportunities(results, max_candidates), rejection_counts


# ---------------------------------------------------------------------------
# 6. FAMILY F — Price-Threshold & Strike-Ladder Arbitrage
# ---------------------------------------------------------------------------

_ASSET_ALIASES: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("BTC", re.compile(r"\b(?:bitcoin|btc)\b", re.I)),
    ("ETH", re.compile(r"\b(?:ethereum|eth|ether)\b", re.I)),
    ("SOL", re.compile(r"\b(?:solana|sol)\b", re.I)),
    ("XRP", re.compile(r"\b(?:ripple|xrp)\b", re.I)),
    ("DOGE", re.compile(r"\b(?:dogecoin|doge)\b", re.I)),
    ("BNB", re.compile(r"\b(?:bnb|binance\s+coin)\b", re.I)),
    ("HYPE", re.compile(r"\b(?:hyperliquid|hype)\b", re.I)),
    ("SUI", re.compile(r"\bsui\b", re.I)),
    ("ADA", re.compile(r"\b(?:cardano|ada)\b", re.I)),
    ("AVAX", re.compile(r"\b(?:avalanche|avax)\b", re.I)),
    ("LINK", re.compile(r"\bchainlink\b", re.I)),
    ("GOLD", re.compile(r"\b(?:gold|xau(?:/usd)?)\b", re.I)),
    ("SILVER", re.compile(r"\b(?:silver|xag(?:/usd)?)\b", re.I)),
    ("CRUDE_OIL", re.compile(r"\b(?:wti|crude\s+oil|brent\s+crude)\b", re.I)),
    ("SP500", re.compile(r"\b(?:s&p\s*500|spx)\b", re.I)),
    ("NASDAQ100", re.compile(r"\b(?:nasdaq(?:\s*100)?|ndx)\b", re.I)),
    ("DOW_JONES", re.compile(r"\b(?:dow\s+jones|djia)\b", re.I)),
    ("NVDA", re.compile(r"\b(?:nvidia|nvda)\b", re.I)),
    ("AAPL", re.compile(r"\b(?:apple|aapl)\b", re.I)),
    ("TSLA", re.compile(r"\b(?:tesla|tsla)\b", re.I)),
    ("MSFT", re.compile(r"\b(?:microsoft|msft)\b", re.I)),
    ("GOOGL", re.compile(r"\b(?:alphabet|googl|google\s+stock)\b", re.I)),
    ("AMZN", re.compile(r"\b(?:amazon|amzn)\b", re.I)),
    ("META", re.compile(r"\b(?:meta\s+platforms|meta\s+stock)\b", re.I)),
    ("MSTR", re.compile(r"\b(?:microstrategy|strategy\s+stock|mstr)\b", re.I)),
    ("COIN", re.compile(r"\b(?:coinbase\s+stock|coin\s+stock)\b", re.I)),
    ("FED_RATE", re.compile(r"\b(?:federal\s+funds\s+rate|fed\s+interest\s+rate|upper\s+bound\s+of\s+the\s+federal\s+funds)\b", re.I)),
    ("US_CPI_YOY", re.compile(r"\b(?:annual\s+inflation|cpi\s+inflation|year-over-year\s+cpi|yoy\s+cpi)\b", re.I)),
    ("US_10Y_YIELD", re.compile(r"\b10-year\s+treasury\s+yield\b", re.I)),
)

_FDV_MCAP_ENTITY_RE = re.compile(
    r"\b([a-z0-9][a-z0-9.\-]{1,24})\s+(?P<mkind>fdv|fully\s+diluted\s+valuation|market\s+cap(?:italization)?)\b",
    re.IGNORECASE,
)

_WEATHER_GUARD_RE = re.compile(
    r"(?:°\s*[fc]\b|\bdegrees\s+(?:fahrenheit|celsius)\b|\bhighest\s+temperature\b|\blowest\s+temperature\b|"
    r"\bwunderground\b|\bprecipitation\b|\bsnowfall\b|\brainfall\b)",
    re.IGNORECASE,
)

# Non-backtracking word-bounded numeric + multiplier parser (`$100k`, `$2.5B`, `4.25%`)
_RANGE_STRIKE_RE = re.compile(
    r"(?:\bbetween\s+|\bfrom\s+|^)"
    r"\$?(?P<lo>\d+(?:,\d{3})*(?:\.\d+)?)(?:\s*(?P<lo_m>trillion|billion|million|thousand|[kmbt]))?\b\s*%?"
    r"\s*(?:and|to|[-–—])\s*"
    r"\$?(?P<hi>\d+(?:,\d{3})*(?:\.\d+)?)(?:\s*(?P<hi_m>trillion|billion|million|thousand|[kmbt]))?\b\s*(?P<pct>%?)",
    re.IGNORECASE,
)

_SINGLE_DOLLAR_OR_PCT_STRIKE_RE = re.compile(
    r"(?P<dir_pre>"
    r">=|<=|>|<|"
    r"\b(?:at\s+least|at\s+most|above|over|more\s+than|greater\s+than|higher\s+than|exceed(?:s)?|"
    r"reach(?:es)?|hit(?:s)?|touch(?:es)?|dip(?:s)?\s+to|drop(?:s)?\s+to|fall(?:s)?\s+(?:to|below)|"
    r"below|under|less\s+than|lower\s+than)\s+"
    r")?"
    r"(?P<has_dollar>\$?)(?P<val>\d+(?:,\d{3})*(?:\.\d+)?)"
    r"(?:\s*(?P<mult>trillion|billion|million|thousand|[kmbt])(?![a-z0-9]))?"
    r"(?P<plus>\+?)\s*(?P<pct>%?)"
    r"(?:\s*(?P<dir_post>or\s+(?:above|higher|more|greater|less|lower|below)))?",
    re.IGNORECASE,
)

_MULT_FACTORS: Dict[str, float] = {
    "k": 1e3,
    "thousand": 1e3,
    "m": 1e6,
    "million": 1e6,
    "b": 1e9,
    "billion": 1e9,
    "t": 1e12,
    "trillion": 1e12,
}

_TOUCH_UP_RE = re.compile(
    r"\b(?:reach(?:es)?|hit(?:s)?|touch(?:es)?|at\s+any\s+point|any\s+1-minute\s+candle|any\s+1m\s+candle|"
    r"high\s+of\s+any|any\s+time\s+(?:before|prior|during|in))\b",
    re.IGNORECASE,
)
_TOUCH_DOWN_RE = re.compile(
    r"\b(?:dip(?:s)?\s+(?:to|below)|drop(?:s)?\s+(?:to|below)|fall(?:s)?\s+(?:to|below)|low\s+of\s+any)\b",
    re.IGNORECASE,
)
_CLOSE_AT_EXPIRY_RE = re.compile(
    r"\b(?:close(?:\s+price)?\s+(?:at|on|of)|1\s*(?:m|min|minute)\s+candle\s+close|settlement\s+price|"
    r"closing\s+price|official\s+close|end\s+of\s+day|price\s+of\s+[a-z0-9]+\s+be\s+(?:above|below|between|over|under|at\s+least)"
    r"|at\s+\d{1,2}:\d{2}\s*(?:am|pm)?\s*(?:et|est|edt|utc|gmt))\b",
    re.IGNORECASE,
)
_TWAP_OBS_RE = re.compile(r"\b(?:twap|time-weighted\s+average)\b", re.IGNORECASE)


def _scale_strike_value(raw_num: str, mult_str: Optional[str], default_mult: float = 1.0) -> Optional[float]:
    try:
        v = float(raw_num.replace(",", ""))
    except ValueError:
        return None
    if mult_str:
        f = _MULT_FACTORS.get(mult_str.strip().lower())
        if f is None:
            return None
        return v * f
    return v * default_mult


def extract_price_oracle_feed(m: CanonicalBinaryMarket) -> str:
    """Extracts exact contractual reference exchange/oracle feed (`BINANCE_USDT`, `COINBASE_USD`, `CME_FUTURES`, etc.)."""
    blob = f"{m.resolution_source} {m.description}".lower()
    if "binance" in blob:
        if "usdt" in blob:
            return "BINANCE_SPOT_USDT"
        if "usdc" in blob:
            return "BINANCE_SPOT_USDC"
        return "BINANCE_SPOT"
    if "coinbase" in blob:
        return "COINBASE_SPOT"
    if "kraken" in blob:
        return "KRAKEN_SPOT"
    if "chainlink" in blob or "data.chain.link" in blob:
        return "CHAINLINK_TWAP_60S" if _TWAP_OBS_RE.search(blob) else "CHAINLINK_STREAM"
    if "pyth.network" in blob or "pyth " in blob:
        return "PYTH_ORACLE"
    if "coingecko" in blob:
        return "COINGECKO"
    if "coinmarketcap" in blob:
        return "COINMARKETCAP"
    if any(k in blob for k in ("cmegroup", "cme ", "comex", "nymex", "futures contract", "front-month futures")):
        return "CME_FUTURES"
    if any(k in blob for k in ("lbma", "xau/usd", "xag/usd", "spot gold", "spot silver", "oanda", "tradingview")):
        return "SPOT_METAL_FX"
    if "yahoo finance" in blob or "finance.yahoo.com" in blob:
        return "YAHOO_FINANCE"
    if "nasdaq.com" in blob or "nasdaq official" in blob:
        return "NASDAQ_OFFICIAL"
    if "nyse" in blob:
        return "NYSE_OFFICIAL"
    if "federalreserve.gov" in blob or "fomc" in blob:
        return "FEDERAL_RESERVE"
    if "home.treasury.gov" in blob or "daily treasury par yield" in blob:
        return "US_TREASURY_PAR_YIELD"
    if "bls.gov" in blob or "bureau of labor statistics" in blob:
        return "BLS_OFFICIAL"
    return "UNSPECIFIED_ORACLE"


@dataclass(frozen=True)
class ParsedStrikeContract:
    market: CanonicalBinaryMarket
    asset_key: str
    metric_kind: str  # "PRICE" | "FDV" | "MARKET_CAP" | "MACRO_RATE"
    comparator: str   # "GTE" | "GT" | "LTE" | "LT" | "RANGE"
    strike_low: float
    strike_high: Optional[float]
    lower_inclusive: bool
    upper_inclusive: bool
    obs_mode: str     # "CLOSE_AT_EXPIRY" | "TOUCH_ANYTIME" | "TOUCH_DOWN_ANYTIME" | "TWAP_WINDOW" | "UNSPECIFIED_OBS"
    oracle_feed: str
    cutoff_ts_utc: float
    tz_tag: str


def parse_strike_contract(m: CanonicalBinaryMarket) -> Optional[ParsedStrikeContract]:
    """
    Parses a binary price-threshold, market-cap/FDV, macro-rate, or `[L, U)` range contract.
    Never conflates weather temperatures (`°F`/`°C`), sports spreads/totals, or `FDV` vs `Spot Price`.
    """
    if not m.is_standard_yes_no or m.closed_or_archived or not m.yes_token_id or not m.no_token_id:
        return None
    if m.sports_market_type or m.is_placeholder_outcome or m.is_other_outcome:
        return None
    if m.is_d001_disputed_quarantined():
        return None

    full_q = f"{m.event_title} :: {m.question} :: {m.group_item_title}"
    if _WEATHER_GUARD_RE.search(full_q) or _WEATHER_GUARD_RE.search(m.description[:300]):
        return None

    # 1. Identify metric_kind & asset_key
    metric_kind = "PRICE"
    asset_key = ""
    m_fdv = _FDV_MCAP_ENTITY_RE.search(f"{m.event_title} {m.question}")
    if m_fdv and m_fdv.group(1).lower() not in _STOPWORDS:
        ent = m_fdv.group(1).upper()
        mk_raw = m_fdv.group("mkind").lower()
        metric_kind = "FDV" if ("fdv" in mk_raw or "diluted" in mk_raw) else "MARKET_CAP"
        asset_key = ent
    for code, pat in _ASSET_ALIASES:
        if pat.search(f"{m.event_title} {m.question}"):
            asset_key = code
            if code in {"FED_RATE", "US_CPI_YOY", "US_10Y_YIELD"}:
                metric_kind = "MACRO_RATE"
            break
    if not asset_key:
        return None

    # Also detect FDV / Market Cap on known assets (e.g. "ETH market cap", "NVDA market cap")
    q_ev_l = f"{m.event_title} {m.question}".lower()
    if "fdv" in q_ev_l or "fully diluted" in q_ev_l:
        metric_kind = "FDV"
    elif "market cap" in q_ev_l:
        metric_kind = "MARKET_CAP"

    # 2. Extract observation mode (`TOUCH_ANYTIME` vs `TOUCH_DOWN_ANYTIME` vs `CLOSE_AT_EXPIRY` vs `TWAP_WINDOW`)
    # `BUG-LS-1`: Never allow an unsigned `"hit/reach/touch <K>"` verb to default to `TOUCH_ANYTIME` (`GTE` `CLASS_B`)
    # without explicit upward (`(HIGH)`/`↑`, candle `high`, `higher than`, `at or above`, `exceeds`) or downward
    # (`(LOW)`/`↓`, `dip/drop/fall`, candle `low`, `lower than`, `equal to or below`, `at or below`) confirmation!
    desc_q = f"{m.question} {m.description}"
    full_q_l = full_q.lower()
    q_l_probe = m.question.lower()
    desc_l_probe = m.description.lower()
    desc_low_barrier = bool(
        re.search(
            r"\b(?:equal\s+to\s+or\s+(?:below|lower\s+than)|reaches?\s+or\s+(?:is\s+)?(?:below|lower\s+than)|"
            r"is\s+(?:below|lower\s+than)|at\s+or\s+below|falls?\s+to\s+or\s+below|listed\s+(?:value|price|rate)\s+or\s+(?:lower|below)|"
            r"candle\s+['\"]?low['\"]?|['\"]low['\"]\s+(?:price|bar)|low\s+of\s+any)\b|<=",
            desc_l_probe,
        )
    )
    desc_high_barrier = bool(
        re.search(
            r"\b(?:equal\s+to\s+or\s+(?:above|higher\s+than)|reaches?\s+or\s+(?:is\s+)?(?:above|higher\s+than)|"
            r"is\s+(?:above|higher\s+than)|at\s+or\s+above|rises?\s+to\s+or\s+above|exceeds?|"
            r"listed\s+(?:value|price|rate)\s+or\s+(?:higher|above)|candle\s+['\"]?high['\"]?|['\"]high['\"]\s+(?:price|bar)|high\s+of\s+any)\b|>=",
            desc_l_probe,
        )
    )
    q_explicit_up_ineq = bool(
        re.search(r">=|>|\b(?:at\s+least|above|over|more\s+than|greater\s+than|higher\s+than|exceed(?:s)?|or\s+(?:above|higher|more|greater))\b", q_l_probe)
    )
    q_explicit_dn_ineq = bool(
        re.search(r"<=|<|\b(?:at\s+most|below|under|less\s+than|lower\s+than|or\s+(?:below|lower|less))\b", q_l_probe)
    )
    has_unsigned_touch_verb = bool(re.search(r"\b(?:reach(?:es)?|hit(?:s)?|touch(?:es)?)\b", q_l_probe))
    is_explicit_low_touch = bool(
        "(low)" in full_q_l or "↓" in m.group_item_title or "↓" in m.question or _TOUCH_DOWN_RE.search(m.question) or (desc_low_barrier and not desc_high_barrier)
    )
    is_explicit_high_touch = bool(
        "(high)" in full_q_l or "↑" in m.group_item_title or "↑" in m.question or (desc_high_barrier and not desc_low_barrier)
    )
    if _TWAP_OBS_RE.search(desc_q):
        obs_mode = "TWAP_WINDOW"
    elif is_explicit_low_touch and not is_explicit_high_touch and (has_unsigned_touch_verb or _TOUCH_DOWN_RE.search(desc_q) or not _CLOSE_AT_EXPIRY_RE.search(desc_q)):
        obs_mode = "TOUCH_DOWN_ANYTIME"
    elif is_explicit_high_touch and not is_explicit_low_touch and (has_unsigned_touch_verb or _TOUCH_UP_RE.search(desc_q) or not _CLOSE_AT_EXPIRY_RE.search(desc_q)):
        obs_mode = "TOUCH_ANYTIME"
    elif has_unsigned_touch_verb and not (q_explicit_up_ineq or q_explicit_dn_ineq):
        # Unsigned `hit / reach / touch <K>` without directional barrier rule in title or description -> `UNSPECIFIED_OBS` (`CLASS_D`)!
        obs_mode = "UNSPECIFIED_OBS"
    elif _CLOSE_AT_EXPIRY_RE.search(desc_q):
        obs_mode = "CLOSE_AT_EXPIRY"
    elif _TOUCH_UP_RE.search(m.description) and (q_explicit_up_ineq or desc_high_barrier):
        obs_mode = "TOUCH_ANYTIME"
    else:
        obs_mode = "UNSPECIFIED_OBS"

    # 3. Extract timezone & exact settlement/cutoff timestamp
    tz_tag, tz_iana = extract_timezone_signature(m)
    cutoff_ts: Optional[float] = None
    mt_q = _DEADLINE_TAIL_RE.search(" ".join(m.question.strip().split()))
    if mt_q:
        pc = _parse_cutoff_epoch_in_tz(mt_q.group("date_expr"), mt_q.group("prep"), tz_iana, m.description, m.end_ts)
        if pc is not None:
            cutoff_ts = pc[0]
    if cutoff_ts is None and m.end_ts is not None:
        cutoff_ts = float(m.end_ts)
    if cutoff_ts is None:
        return None

    oracle_feed = extract_price_oracle_feed(m)
    desc_l = m.description.lower()

    # Guard against negated strike questions (`"Will BTC NOT close above $90k?"`, `"fail to reach"`):
    #   - On single-valued `CLOSE_AT_EXPIRY` / `TWAP_WINDOW`, `NOT (S >= K)` is `S < K` (`LT`) and `NOT (S > K)` is `S <= K` (`LTE`)!
    #   - On `TOUCH` or `RANGE`, negated predicates invert path semantics (`never touch` = path survival != `TOUCH_ANYTIME`), so reject!
    has_q_negation = bool(re.search(r"\b(?:not|never|fail(?:s)?\s+to|without|avoid(?:s)?)\b|n't\b", m.question.lower()))
    if has_q_negation and obs_mode not in {"CLOSE_AT_EXPIRY", "TWAP_WINDOW"}:
        return None

    # 4. Parse RANGE vs Single Strike (prefer `group_item_title` when clean, else `question`)
    probe_texts = [t for t in (m.group_item_title.strip(), m.question.strip()) if t]
    for txt in probe_texts:
        if has_q_negation:
            break  # `NOT in [L, U]` is a non-convex two-tail union, not a single range!
        # Guard against matching ISO dates like `2026-11` as ranges: require `$` or `%` or explicit `between` in question/group
        if "$" in txt or "%" in txt or metric_kind == "MACRO_RATE" or "between" in txt.lower():
            mr = _RANGE_STRIKE_RE.search(txt)
            if mr and ("$" in txt or "%" in txt or "between" in m.question.lower()):
                hi_mult = mr.group("hi_m")
                lo_mult = mr.group("lo_m") or hi_mult  # e.g., `"$90-$100B"` shares trailing `B`
                lo_v = _scale_strike_value(mr.group("lo"), lo_mult)
                hi_v = _scale_strike_value(mr.group("hi"), hi_mult)
                if lo_v is not None and hi_v is not None and hi_v > lo_v > 0:
                    # Determine boundary inclusivity from description (`strictly less than` / `[L, U)` vs `inclusive`)
                    lo_inc = not bool(re.search(r"strictly\s+(?:greater|above|more)\s+than\s+\$?" + re.escape(mr.group("lo")), desc_l))
                    if re.search(r"\b(?:less\s+than|under|below)\s+\$?" + re.escape(mr.group("hi")), desc_l) or "[l, u)" in desc_l:
                        hi_inc = False
                    elif re.search(r"\binclusive\b|or\s+less|at\s+most", desc_l):
                        hi_inc = True
                    else:
                        # Standard Polymarket discrete range `$90,000 - $99,999.99` or `$90k-$100k`: check `.99` vs integer
                        hi_inc = True
                    return ParsedStrikeContract(
                        market=m,
                        asset_key=asset_key,
                        metric_kind=metric_kind,
                        comparator="RANGE",
                        strike_low=lo_v,
                        strike_high=hi_v,
                        lower_inclusive=lo_inc,
                        upper_inclusive=hi_inc,
                        obs_mode=obs_mode,
                        oracle_feed=oracle_feed,
                        cutoff_ts_utc=cutoff_ts,
                        tz_tag=tz_tag,
                    )

    # Single-threshold parse (`>=`, `>`, `<=`, `<`, `hit $X`, `dip to $X`, `$100k+`)
    for ms in _SINGLE_DOLLAR_OR_PCT_STRIKE_RE.finditer(m.question):
        has_d = bool(ms.group("has_dollar"))
        has_pct = bool(ms.group("pct"))
        mult_s = ms.group("mult")
        dir_pre = (ms.group("dir_pre") or "").strip().lower()
        dir_post = (ms.group("dir_post") or "").strip().lower()
        plus_s = (ms.group("plus") or "").strip()

        # Require `$` for price/FDV/mcap or `%` for macro rates so years (`2026`) or days (`31`) are never parsed as strikes!
        if metric_kind in {"PRICE", "FDV", "MARKET_CAP"} and not has_d and not (
            asset_key in {"SP500", "NASDAQ100", "DOW_JONES"} and (dir_pre or dir_post or plus_s)
        ):
            continue
        if metric_kind == "MACRO_RATE" and not has_pct:
            continue
        if not (dir_pre or dir_post or plus_s):
            continue

        val_f = _scale_strike_value(ms.group("val"), mult_s)
        if val_f is None or val_f <= 0:
            continue
        if asset_key in {"SP500", "NASDAQ100", "DOW_JONES"} and not has_d and 1990 <= val_f <= 2035 and not dir_pre:
            continue

        comp = ""
        if dir_pre in {">="} or "at least" in dir_pre or plus_s == "+" or any(
            w in dir_post for w in ("or above", "or higher", "or more", "or greater")
        ):
            comp = "GTE"
        elif any(w in dir_pre for w in ("reach", "hit", "touch")):
            # Live Polymarket quirk: `"Will S&P 500 (SPX) hit $7,200 (LOW) in December?"` (`↓ $7,200`) is `LTE`, NOT `GTE`!
            comp = "LTE" if obs_mode == "TOUCH_DOWN_ANYTIME" else "GTE"
        elif dir_pre in {">"} or any(w in dir_pre for w in ("above", "over", "more than", "greater than", "higher than", "exceed")):
            # Check if description clarifies `"X or higher"` (`GTE`) vs strictly greater (`GT`)
            comp = "GTE" if ("or higher" in desc_l or "or above" in desc_l or ">=" in desc_l) else "GT"
        elif dir_pre in {"<="} or "at most" in dir_pre or any(w in dir_post for w in ("or below", "or lower", "or less")):
            comp = "LTE"
        elif any(w in dir_pre for w in ("dip", "drop", "fall")):
            comp = "LT" if "below" in dir_pre else "LTE"
        elif dir_pre in {"<"} or any(w in dir_pre for w in ("below", "under", "less than", "lower than")):
            comp = "LTE" if ("or lower" in desc_l or "or below" in desc_l or "<=" in desc_l) else "LT"

        if comp:
            if has_q_negation:
                inv_map = {"GTE": "LT", "GT": "LTE", "LTE": "GT", "LT": "GTE"}
                comp = inv_map[comp]
            return ParsedStrikeContract(
                market=m,
                asset_key=asset_key,
                metric_kind=metric_kind,
                comparator=comp,
                strike_low=val_f,
                strike_high=None,
                lower_inclusive=(comp in {"GTE", "LTE"}),
                upper_inclusive=(comp in {"LTE"}),
                obs_mode=obs_mode,
                oracle_feed=oracle_feed,
                cutoff_ts_utc=cutoff_ts,
                tz_tag=tz_tag,
            )

    return None


def _eval_strike_point_truth(sc: ParsedStrikeContract, price_point: float) -> bool:
    """Exact indicator `I(price_point satisfies contract sc)` at single-valued expiry settlement."""
    if sc.comparator == "GTE":
        return price_point >= sc.strike_low
    if sc.comparator == "GT":
        return price_point > sc.strike_low
    if sc.comparator == "LTE":
        return price_point <= sc.strike_low
    if sc.comparator == "LT":
        return price_point < sc.strike_low
    if sc.comparator == "RANGE" and sc.strike_high is not None:
        ok_lo = (price_point >= sc.strike_low) if sc.lower_inclusive else (price_point > sc.strike_low)
        ok_hi = (price_point <= sc.strike_high) if sc.upper_inclusive else (price_point < sc.strike_high)
        return ok_lo and ok_hi
    return False


def _mk_state(
    state_id: str,
    description: str,
    instrument_payouts: Mapping[str, float],
    probability: float,
    *,
    is_edge_or_void_state: bool = False,
) -> StateSpec:
    return StateSpec(
        state_id=state_id,
        instrument_payouts=dict(instrument_payouts),
        probability=float(probability),
        is_edge_or_void_state=bool(is_edge_or_void_state),
        description=description,
    )


def _build_strike_sample_states(contracts: Sequence[ParsedStrikeContract]) -> List[StateSpec]:
    """
    Constructs a complete finite partition of sample points on `R+` covering every critical
    open interval AND exact boundary point across `contracts`, plus `VOID`!
    Any gap (`$99k` vs `$100k`) or boundary overlap (`<= $100k` and `>= $100k`) is caught with 100% precision.
    """
    knots_set: Set[float] = set()
    for c in contracts:
        knots_set.add(float(c.strike_low))
        if c.strike_high is not None:
            knots_set.add(float(c.strike_high))
    knots = sorted(knots_set)
    sample_points: List[Tuple[str, float]] = []
    if knots:
        lo0 = knots[0]
        eps0 = max(abs(lo0) * 1e-4, 1e-6)
        sample_points.append((f"S_LT_{lo0:g}", max(0.0, lo0 - eps0)))
        for idx, k_val in enumerate(knots):
            sample_points.append((f"S_EQ_{k_val:g}", k_val))
            if idx + 1 < len(knots):
                k_next = knots[idx + 1]
                if k_next > k_val:
                    sample_points.append((f"S_MID_{k_val:g}_{k_next:g}", 0.5 * (k_val + k_next)))
        hi_last = knots[-1]
        eps_hi = max(abs(hi_last) * 1e-4, 1e-6)
        sample_points.append((f"S_GT_{hi_last:g}", hi_last + eps_hi))

    states: List[StateSpec] = []
    prob_main = 0.99 / max(1, len(sample_points))
    for sid, s_val in sample_points:
        pay: Dict[str, float] = {}
        for c in contracts:
            is_yes = _eval_strike_point_truth(c, s_val)
            pay[c.market.yes_token_id] = 1.0 if is_yes else 0.0
            pay[c.market.no_token_id] = 0.0 if is_yes else 1.0
        states.append(_mk_state(sid, f"S_T={s_val:g}", pay, prob_main))

    # Add VOID / emergency resolution state
    void_pay: Dict[str, float] = {}
    for c in contracts:
        tag = c.market.cancel_rule_tag
        if tag == "NEGRISK_NO":
            void_pay[c.market.yes_token_id] = 0.0
            void_pay[c.market.no_token_id] = 1.0
        else:
            void_pay[c.market.yes_token_id] = 0.5
            void_pay[c.market.no_token_id] = 0.5
    states.append(_mk_state("VOID_MARKET_HALT", "Exchange halt / void settlement", void_pay, 0.01, is_edge_or_void_state=True))
    return states


def detect_family_f_price_strike_ladders(
    markets: Sequence[CanonicalBinaryMarket],
    books: Mapping[str, InstrumentOrderBook],
    *,
    verifier: Optional[UniversalArbVerifier] = None,
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
    now_ts: Optional[float] = None,
    max_candidates: int = 350,
) -> Tuple[List[DetectedOpportunity], Dict[str, int]]:
    """
    Family F — Price-Threshold & Strike-Ladder Arbitrage:
      1. Upward Strike Dominance (`S >= K_high => S >= K_low` -> `1 NO_high + 1 YES_low`)
      2. Downward Strike Dominance (`S <= K_low => S <= K_high` -> `1 NO_low + 1 YES_high`)
      3. Disjoint Tail Mutual Exclusion (`S >= K_high` perp `S <= K_low` at `CLOSE_AT_EXPIRY`,
         explicitly rejecting `TOUCH_ANYTIME` double-touch traps to `CLASS_D`!)
      4. 3-Leg Range + Tail Interval Covers (`[K1, K2) + >= K2 <=> >= K1` in BOTH long-cover and
         short-cover directions, catching discrete gaps `$99k..$100k` and endpoint overlaps via exact sample points!)
      5. Cross-Mode & Cross-Oracle Trap Guard (`Touch` vs `Close`, `Binance` vs `Coinbase`,
         `Spot XAUUSD` vs `CME GC Futures`, `FDV` vs `Market Cap` -> all downgraded to `CLASS_D`!).
    """
    ver = verifier or UniversalArbVerifier()
    now_f = float(time.time() if now_ts is None else now_ts)
    results: List[DetectedOpportunity] = []
    rejection_counts: Dict[str, int] = {}

    def _bump(r: str) -> None:
        rejection_counts[r] = rejection_counts.get(r, 0) + 1

    parsed_all: List[ParsedStrikeContract] = []
    for m in markets:
        ps = parse_strike_contract(m)
        if ps is not None and ps.cutoff_ts_utc > now_f - 3600.0:
            parsed_all.append(ps)

    # Group by `(asset_key, day_bucket)` so we BOTH evaluate valid ladders AND catch same-day
    # `Touch` vs `Close`, `Binance` vs `Coinbase`, `Spot` vs `Futures`, and `FDV` vs `MCAP` mismatches!
    by_asset_day: Dict[Tuple[str, int], List[ParsedStrikeContract]] = {}
    for ps in parsed_all:
        day_bkt = int(ps.cutoff_ts_utc // 86400.0)
        by_asset_day.setdefault((ps.asset_key, day_bkt), []).append(ps)

    def _pair_rule_reasons(a: ParsedStrikeContract, b: ParsedStrikeContract) -> Tuple[List[str], bool, bool]:
        reasons: List[str] = []
        touch_close_mis = False
        oracle_mis = False

        if a.metric_kind != b.metric_kind:
            reasons.append(f"METRIC_KIND_MISMATCH:{a.metric_kind}_vs_{b.metric_kind}")
            oracle_mis = True

        if a.obs_mode == "UNSPECIFIED_OBS" or b.obs_mode == "UNSPECIFIED_OBS":
            reasons.append(f"OBSERVATION_MODE_UNSPECIFIED:{a.obs_mode}_vs_{b.obs_mode}")
            touch_close_mis = True
        elif a.obs_mode != b.obs_mode:
            reasons.append(f"TOUCH_VS_CLOSE_OBSERVATION_MISMATCH:{a.obs_mode}_vs_{b.obs_mode}")
            touch_close_mis = True

        if a.oracle_feed == "UNSPECIFIED_ORACLE" or b.oracle_feed == "UNSPECIFIED_ORACLE":
            if not (
                a.market.event_id == b.market.event_id
                and a.market.resolved_by
                and a.market.resolved_by == b.market.resolved_by
                and a.market.resolution_source == b.market.resolution_source
                and len(a.market.description) >= 60
            ):
                reasons.append("REFERENCE_ORACLE_UNSPECIFIED")
                oracle_mis = True
        elif a.oracle_feed != b.oracle_feed:
            if {a.oracle_feed, b.oracle_feed} == {"CME_FUTURES", "SPOT_METAL_FX"}:
                reasons.append("SPOT_VS_FUTURES_BASIS_MISMATCH")
            else:
                reasons.append(f"REFERENCE_ORACLE_MISMATCH:{a.oracle_feed}_vs_{b.oracle_feed}")
            oracle_mis = True

        if abs(a.cutoff_ts_utc - b.cutoff_ts_utc) > 60.0:
            reasons.append(f"EXPIRY_TIMESTAMP_MISMATCH:{abs(a.cutoff_ts_utc - b.cutoff_ts_utc):.0f}s")
        if a.tz_tag != b.tz_tag and "UNSPECIFIED" not in {a.tz_tag, b.tz_tag}:
            reasons.append(f"TIMEZONE_MISMATCH:{a.tz_tag}_vs_{b.tz_tag}")

        return reasons, touch_close_mis, oracle_mis

    for (asset_key, _day_bkt), group in by_asset_day.items():
        if len(group) < 2:
            continue

        up_list = sorted([c for c in group if c.comparator in {"GTE", "GT"}], key=lambda x: (x.strike_low, 0 if x.comparator == "GTE" else 1))
        dn_list = sorted([c for c in group if c.comparator in {"LTE", "LT"}], key=lambda x: (x.strike_low, 0 if x.comparator == "LT" else 1))
        rg_list = sorted([c for c in group if c.comparator == "RANGE" and c.strike_high is not None], key=lambda x: x.strike_low)

        # F.1: Upward Strike Dominance (`c_hi => c_lo` -> `NO(c_hi) + YES(c_lo)`)
        n_up = len(up_list)
        up_pairs: List[Tuple[int, int]] = [(i, i + 1) for i in range(n_up - 1)]
        if n_up <= 14:
            for i in range(n_up):
                for j in range(i + 2, n_up):
                    up_pairs.append((i, j))
        for i, j in dict.fromkeys(up_pairs):
            c_lo, c_hi = up_list[i], up_list[j]
            if c_lo.market.market_id == c_hi.market.market_id:
                continue
            # Check strict dominance: `K_hi > K_lo` OR (`K_hi == K_lo` and `c_hi=GT` and `c_lo=GTE`)
            if c_hi.strike_low == c_lo.strike_low and not (c_hi.comparator == "GT" and c_lo.comparator == "GTE"):
                continue
            reasons, tc_mis, or_mis = _pair_rule_reasons(c_hi, c_lo)
            if c_hi.market.cancel_rule_tag == "50_50" and c_lo.market.cancel_rule_tag == "NEGRISK_NO":
                reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
            for r in reasons:
                _bump(r.split(":")[0])

            legs = [
                _build_leg_with_optional_inventory(c_hi.market.no_token_id, c_hi.market.market_id, f"NO[{asset_key} {c_hi.comparator} {c_hi.strike_low:g}]", holdings),
                _build_leg_with_optional_inventory(c_lo.market.yes_token_id, c_lo.market.market_id, f"YES[{asset_key} {c_lo.comparator} {c_lo.strike_low:g}]", holdings),
            ]
            if not reasons and (j - i) > 1:
                l1 = _quick_l1_buy_cost_sum([(legs[0].instrument_id, c_hi.market), (legs[1].instrument_id, c_lo.market)], books)
                if l1 is None or l1 > 1.0 + DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT:
                    continue

            states = StateSpaceBuilder.two_market_logical_states(
                c_hi.market.yes_token_id,
                c_hi.market.no_token_id,
                c_lo.market.yes_token_id,
                c_lo.market.no_token_id,
                relation="A_IMPLIES_B" if not reasons else "UNCONSTRAINED",
                cancel_rule_a=c_hi.market.cancel_rule_tag,
                cancel_rule_b=c_lo.market.cancel_rule_tag,
                touch_vs_close_mismatch=tc_mis,
                oracle_mismatch=or_mis,
            )
            rule_ok = len(reasons) == 0
            results.append(
                _finalize_detected_opportunity(
                    ver,
                    books,
                    holdings,
                    candidate_id=_make_candidate_id("F", "STRIKE_UP_DOM", [c_hi.market.market_id, c_lo.market.market_id]),
                    family="FAMILY_F_PRICE_STRIKE_LADDER",
                    sub_type="UPWARD_STRIKE_DOMINANCE",
                    relationship_type="A_IMPLIES_B",
                    edge_proof_status="VERIFIED_MATHEMATICAL" if rule_ok else "RULE_MISMATCH_REJECTED",
                    markets=[c_hi.market, c_lo.market],
                    legs=legs,
                    states=states,
                    title_summary=f"[STRIKE_UP] {asset_key} {c_hi.comparator} {c_hi.strike_low:g} => {c_lo.comparator} {c_lo.strike_low:g}",
                    rule_verified=rule_ok,
                    rule_compatibility_notes=[f"oracle={c_hi.oracle_feed}", f"obs={c_hi.obs_mode}", f"metric={c_hi.metric_kind}"],
                    divergence_or_rejection_reasons=reasons,
                )
            )

        # F.2: Downward Strike Dominance (`c_lo <= K_lo => c_hi <= K_hi` -> `NO(c_lo) + YES(c_hi)`)
        n_dn = len(dn_list)
        for i in range(n_dn - 1):
            c_lo, c_hi = dn_list[i], dn_list[i + 1]
            if c_lo.market.market_id == c_hi.market.market_id:
                continue
            if c_lo.strike_low == c_hi.strike_low and not (c_lo.comparator == "LT" and c_hi.comparator == "LTE"):
                continue
            reasons, tc_mis, or_mis = _pair_rule_reasons(c_lo, c_hi)
            if c_lo.market.cancel_rule_tag == "50_50" and c_hi.market.cancel_rule_tag == "NEGRISK_NO":
                reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
            for r in reasons:
                _bump(r.split(":")[0])
            legs = [
                _build_leg_with_optional_inventory(c_lo.market.no_token_id, c_lo.market.market_id, f"NO[{asset_key} {c_lo.comparator} {c_lo.strike_low:g}]", holdings),
                _build_leg_with_optional_inventory(c_hi.market.yes_token_id, c_hi.market.market_id, f"YES[{asset_key} {c_hi.comparator} {c_hi.strike_low:g}]", holdings),
            ]
            states = StateSpaceBuilder.two_market_logical_states(
                c_lo.market.yes_token_id,
                c_lo.market.no_token_id,
                c_hi.market.yes_token_id,
                c_hi.market.no_token_id,
                relation="A_IMPLIES_B" if not reasons else "UNCONSTRAINED",
                cancel_rule_a=c_lo.market.cancel_rule_tag,
                cancel_rule_b=c_hi.market.cancel_rule_tag,
                touch_vs_close_mismatch=tc_mis,
                oracle_mismatch=or_mis,
            )
            rule_ok = len(reasons) == 0
            results.append(
                _finalize_detected_opportunity(
                    ver,
                    books,
                    holdings,
                    candidate_id=_make_candidate_id("F", "STRIKE_DN_DOM", [c_lo.market.market_id, c_hi.market.market_id]),
                    family="FAMILY_F_PRICE_STRIKE_LADDER",
                    sub_type="DOWNWARD_STRIKE_DOMINANCE",
                    relationship_type="A_IMPLIES_B",
                    edge_proof_status="VERIFIED_MATHEMATICAL" if rule_ok else "RULE_MISMATCH_REJECTED",
                    markets=[c_lo.market, c_hi.market],
                    legs=legs,
                    states=states,
                    title_summary=f"[STRIKE_DN] {asset_key} {c_lo.comparator} {c_lo.strike_low:g} => {c_hi.comparator} {c_hi.strike_low:g}",
                    rule_verified=rule_ok,
                    rule_compatibility_notes=[f"oracle={c_lo.oracle_feed}", f"obs={c_lo.obs_mode}"],
                    divergence_or_rejection_reasons=reasons,
                )
            )

        # F.3: Disjoint Tails (`>= K_hi` perp `<= K_lo` -> `NO_hi + NO_lo`, strictly blocking `TOUCH` double-hit traps!)
        for c_up in up_list[:6]:
            for c_dn in dn_list[:6]:
                if c_up.market.market_id == c_dn.market.market_id:
                    continue
                if c_up.strike_low < c_dn.strike_low:
                    continue
                if c_up.strike_low == c_dn.strike_low and c_up.comparator == "GTE" and c_dn.comparator == "LTE":
                    continue
                reasons, tc_mis, or_mis = _pair_rule_reasons(c_up, c_dn)
                if "TOUCH" in c_up.obs_mode or "TOUCH" in c_dn.obs_mode:
                    reasons.append("TOUCH_ANYTIME_BOTH_TAILS_POSSIBLE")
                    tc_mis = True
                for r in reasons:
                    _bump(r.split(":")[0])
                legs = [
                    _build_leg_with_optional_inventory(c_up.market.no_token_id, c_up.market.market_id, f"NO[{asset_key}>={c_up.strike_low:g}]", holdings),
                    _build_leg_with_optional_inventory(c_dn.market.no_token_id, c_dn.market.market_id, f"NO[{asset_key}<={c_dn.strike_low:g}]", holdings),
                ]
                states = StateSpaceBuilder.two_market_logical_states(
                    c_up.market.yes_token_id,
                    c_up.market.no_token_id,
                    c_dn.market.yes_token_id,
                    c_dn.market.no_token_id,
                    relation="MUTUAL_EXCLUSION" if not reasons else "UNCONSTRAINED",
                    cancel_rule_a=c_up.market.cancel_rule_tag,
                    cancel_rule_b=c_dn.market.cancel_rule_tag,
                    touch_vs_close_mismatch=tc_mis,
                    oracle_mismatch=or_mis,
                )
                rule_ok = len(reasons) == 0
                results.append(
                    _finalize_detected_opportunity(
                        ver,
                        books,
                        holdings,
                        candidate_id=_make_candidate_id("F", "DISJOINT_TAILS", [c_up.market.market_id, c_dn.market.market_id]),
                        family="FAMILY_F_PRICE_STRIKE_LADDER",
                        sub_type="DISJOINT_STRIKE_TAILS",
                        relationship_type="MUTUAL_EXCLUSION",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if rule_ok else "RULE_MISMATCH_REJECTED",
                        markets=[c_up.market, c_dn.market],
                        legs=legs,
                        states=states,
                        title_summary=f"[DISJOINT_TAILS] NO({asset_key}>={c_up.strike_low:g}) + NO({asset_key}<={c_dn.strike_low:g})",
                        rule_verified=rule_ok,
                        rule_compatibility_notes=[f"oracle={c_up.oracle_feed}", f"obs={c_up.obs_mode}"],
                        divergence_or_rejection_reasons=reasons,
                    )
                )

        # F.4: 3-Leg Interval Cover (`[K1, K2)` + `>= K2` <=> `>= K1`)
        if rg_list and len(up_list) >= 2:
            up_by_strike: Dict[float, ParsedStrikeContract] = {u.strike_low: u for u in up_list}
            for c_rg in rg_list:
                assert c_rg.strike_high is not None
                c_base = up_by_strike.get(c_rg.strike_low)
                # Find tail contract matching `strike_high` OR closest upward strike `>= strike_high` (to catch `$99k` vs `$100k` gaps!)
                c_tail = up_by_strike.get(c_rg.strike_high)
                if c_tail is None:
                    higher_tails = [u for u in up_list if c_rg.strike_high < u.strike_low <= c_rg.strike_high * 1.05]
                    if higher_tails:
                        c_tail = higher_tails[0]
                if c_base is None or c_tail is None:
                    continue
                if len({c_rg.market.market_id, c_base.market.market_id, c_tail.market.market_id}) < 3:
                    continue

                r12, _, _ = _pair_rule_reasons(c_rg, c_base)
                r13, _, _ = _pair_rule_reasons(c_rg, c_tail)
                base_reasons = list(dict.fromkeys(r12 + r13))
                if any("TOUCH" in c.obs_mode for c in (c_rg, c_base, c_tail)):
                    base_reasons.append("TOUCH_MODE_BREAKS_INTERVAL_PARTITION")

                # Exact sample-point state space over `R+`
                cover_states = _build_strike_sample_states([c_rg, c_tail, c_base])

                # Direction A (Long Cover): `YES([K1, K2)) + YES(>= K2) + NO(>= K1)` (target min payout = $1.00)
                reasons_long = list(base_reasons)
                if c_tail.strike_low > c_rg.strike_high:
                    reasons_long.append(f"INTERVAL_GAP_BETWEEN_RANGE_AND_TAIL:{c_rg.strike_high:g}_to_{c_tail.strike_low:g}")
                elif c_tail.strike_low == c_rg.strike_high and (not c_rg.upper_inclusive) and c_tail.comparator == "GT":
                    reasons_long.append(f"BOUNDARY_POINT_MISSING_AT_K2:{c_rg.strike_high:g}")
                if (not c_rg.lower_inclusive) and c_base.comparator == "GTE":
                    reasons_long.append(f"LOWER_BOUNDARY_MISSING_AT_K1:{c_rg.strike_low:g}")

                for r in reasons_long:
                    _bump(r.split(":")[0])

                legs_long = [
                    _build_leg_with_optional_inventory(c_rg.market.yes_token_id, c_rg.market.market_id, f"YES[{c_rg.strike_low:g}-{c_rg.strike_high:g}]", holdings),
                    _build_leg_with_optional_inventory(c_tail.market.yes_token_id, c_tail.market.market_id, f"YES[>={c_tail.strike_low:g}]", holdings),
                    _build_leg_with_optional_inventory(c_base.market.no_token_id, c_base.market.market_id, f"NO[>={c_base.strike_low:g}]", holdings),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver,
                        books,
                        holdings,
                        candidate_id=_make_candidate_id("F", "INTERVAL_COVER_LONG", [c_rg.market.market_id, c_tail.market.market_id, c_base.market.market_id]),
                        family="FAMILY_F_PRICE_STRIKE_LADDER",
                        sub_type="INTERVAL_COVER_LONG",
                        relationship_type="PARTITION_EQUIVALENCE",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_long else "RULE_MISMATCH_REJECTED",
                        markets=[c_rg.market, c_tail.market, c_base.market],
                        legs=legs_long,
                        states=cover_states,
                        title_summary=f"[INTERVAL_COVER_LONG] {asset_key} [{c_rg.strike_low:g},{c_rg.strike_high:g}) + >={c_tail.strike_low:g} vs >={c_base.strike_low:g}",
                        rule_verified=len(reasons_long) == 0,
                        rule_compatibility_notes=[f"oracle={c_rg.oracle_feed}", f"obs={c_rg.obs_mode}"],
                        divergence_or_rejection_reasons=reasons_long,
                    )
                )

                # Direction B (Short Cover): `NO([K1, K2)) + NO(>= K2) + YES(>= K1)` (target min payout = $2.00 when disjoint!)
                reasons_short = list(base_reasons)
                if c_tail.strike_low == c_rg.strike_high and c_rg.upper_inclusive and c_tail.comparator == "GTE":
                    reasons_short.append(f"ENDPOINT_OVERLAP_DOUBLE_YES_AT_K2:{c_rg.strike_high:g}")
                for r in reasons_short:
                    _bump(r.split(":")[0])

                legs_short = [
                    _build_leg_with_optional_inventory(c_rg.market.no_token_id, c_rg.market.market_id, f"NO[{c_rg.strike_low:g}-{c_rg.strike_high:g}]", holdings),
                    _build_leg_with_optional_inventory(c_tail.market.no_token_id, c_tail.market.market_id, f"NO[>={c_tail.strike_low:g}]", holdings),
                    _build_leg_with_optional_inventory(c_base.market.yes_token_id, c_base.market.market_id, f"YES[>={c_base.strike_low:g}]", holdings),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver,
                        books,
                        holdings,
                        candidate_id=_make_candidate_id("F", "INTERVAL_COVER_SHORT", [c_rg.market.market_id, c_tail.market.market_id, c_base.market.market_id]),
                        family="FAMILY_F_PRICE_STRIKE_LADDER",
                        sub_type="INTERVAL_COVER_SHORT",
                        relationship_type="PARTITION_EQUIVALENCE",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_short else "RULE_MISMATCH_REJECTED",
                        markets=[c_rg.market, c_tail.market, c_base.market],
                        legs=legs_short,
                        states=cover_states,
                        title_summary=f"[INTERVAL_COVER_SHORT] {asset_key} NO([{c_rg.strike_low:g},{c_rg.strike_high:g})) + NO(>={c_tail.strike_low:g}) + YES(>={c_base.strike_low:g})",
                        rule_verified=len(reasons_short) == 0,
                        rule_compatibility_notes=[f"oracle={c_rg.oracle_feed}", f"obs={c_rg.obs_mode}"],
                        divergence_or_rejection_reasons=reasons_short,
                    )
                )

    return _rank_and_cap_opportunities(results, max_candidates), rejection_counts


# ---------------------------------------------------------------------------
# 7. FAMILY G — Sports Outcome Structure (`1X2`, `DC`, `DNB`, Spreads, Totals, Advancement)
# ---------------------------------------------------------------------------

_SOCCER_HINTS_RE = re.compile(
    r"\b(?:soccer|premier\s+league|epl|la\s*liga|bundesliga|serie\s+a|ligue\s+1|champions\s+league|ucl|"
    r"europa\s+league|conference\s+league|eredivisie|liga\s+mx|primeira\s+liga|libertadores|"
    r"mls|copa|world\s+cup|fa\s+cup|efl\s+cup|carabao\s+cup|90\s+minutes|stoppage\s+time|injury\s+time|"
    r"end\s+in\s+a\s+draw|draw\s+no\s+bet|double\s+chance|fc\b|cf\b|afc\b|sc\b|united\b)\b",
    re.IGNORECASE,
)
_SPORT_LEAGUE_RES: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("NBA_BASKETBALL", re.compile(r"\b(?:nba|wnba|ncaab|basketball|euroleague)\b", re.I)),
    ("NFL_FOOTBALL", re.compile(r"\b(?:nfl|cfb|college\s+football|super\s+bowl|afc\s+championship|nfc\s+championship)\b", re.I)),
    ("NHL_HOCKEY", re.compile(r"\b(?:nhl|stanley\s+cup|ice\s+hockey)\b", re.I)),
    ("MLB_BASEBALL", re.compile(r"\b(?:mlb|world\s+series|baseball)\b", re.I)),
    ("TENNIS", re.compile(r"\b(?:atp|wta|wimbledon|us\s+open\s+tennis|roland\s+garros|australian\s+open|tennis)\b", re.I)),
    ("COMBAT", re.compile(r"\b(?:ufc|mma|bellator|boxing)\b", re.I)),
    ("ESPORTS", re.compile(r"\b(?:cs2|counter-strike|valorant|league\s+of\s+legends|dota\s*2|esports)\b", re.I)),
    ("SOCCER", _SOCCER_HINTS_RE),
)

_VS_FIXTURE_RE = re.compile(
    r"^(?:will\s+)?(?P<t1>[A-Za-z0-9.\-'\s]{2,40}?)\s+(?:vs\.?|v\.?|@)\s+(?P<t2>[A-Za-z0-9.\-'\s]{2,40}?)(?:\s*[:\-–?]|$|\s+end\s+in|\s+on\s+20\d{2})",
    re.IGNORECASE,
)
_TEAM_WIN_MATCH_RE = re.compile(
    r"^will\s+(?P<team>[A-Za-z0-9.\-'\s]{2,40}?)\s+(?:win|beat|defeat)(?:\s+on\s+20\d{2}-\d{2}-\d{2})?\s*\??$",
    re.IGNORECASE,
)
_DRAW_MATCH_RE = re.compile(
    r"(?:\bend\s+in\s+a\s+draw\b|^draw\b|\bdraw\s*\()",
    re.IGNORECASE,
)
_DOUBLE_CHANCE_RE = re.compile(
    r"(?:(?P<t1>[A-Za-z0-9.\-'\s]{2,35}?)\s+or\s+draw\b|draw\s+or\s+(?P<t2>[A-Za-z0-9.\-'\s]{2,35}?)\b|"
    r"(?P<ta>[A-Za-z0-9.\-'\s]{2,30}?)\s+or\s+(?P<tb>[A-Za-z0-9.\-'\s]{2,30}?)\s+to\s+win\b|\bdouble\s+chance\b)",
    re.IGNORECASE,
)
_ADVANCE_QUALIFY_RE = re.compile(
    r"\b(?:advance\s+to|qualify\s+for|to\s+advance|to\s+qualify|lift\s+the\s+trophy)\b",
    re.IGNORECASE,
)
_SPREAD_PARSE_RE = re.compile(
    r"(?:spread\s*:\s*)?(?P<team>[A-Za-z0-9.\-'\s]{2,36}?)\s*\(?(?P<sign>[+\-])(?P<pts>\d+(?:\.\d+)?)\)?",
    re.IGNORECASE,
)
_TOTAL_OU_RE = re.compile(
    r"(?:\bo/u\b|\bover/under\b|\btotal\s+(?:points|goals|runs|games|maps)\b)\s*:?\s*(?P<line>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SUBPERIOD_SPORTS_RE = re.compile(
    r"(?:\b1st\s+half\b|\bfirst\s+half\b|\b2nd\s+half\b|\bsecond\s+half\b|(?:^|[\s_])(?:1h|2h|h1|h2)(?:$|[\s_:])|"
    r"\b(?:1st|2nd|3rd|4th|first|second|third|fourth)\s+quarter\b|(?:^|[\s_])(?:[1-4]q|q[1-4])(?:$|[\s_:])|"
    r"\b(?:1st|2nd|3rd)\s+period\b|(?:^|[\s_])p[1-3](?:$|[\s_:])|"
    r"\b1st\s+five\s+innings\b|\bfirst\s+5\s+innings\b|(?:^|[\s_])f5(?:$|[\s_:])|"
    r"\b(?:map|set|game|inning|round)\s+[1-9]\b|\b1st\s+set\b)",
    re.IGNORECASE,
)
_PLAYER_OR_TEAM_PROP_TYPES = frozenset(
    {
        "points", "rebounds", "assists", "threes", "three_pointers", "blocks", "steals", "turnovers",
        "pra", "pts_rebs_asts", "pts_rebs", "pts_asts", "rebs_asts", "double_double", "triple_double",
        "passing_yards", "rushing_yards", "receiving_yards", "pass_tds", "anytime_td", "touchdowns",
        "completions", "interceptions", "receptions", "sacks", "kicking_points",
        "strikeouts", "hits", "home_runs", "rbis", "total_bases", "earned_runs", "outs",
        "shots_on_goal", "saves", "goals", "player_points", "aces", "double_faults", "kills", "headshots",
        "team_totals", "home_totals", "away_totals",
    }
)
_REGULATION_90M_RE = re.compile(
    r"\b(?:90\s+minutes|regulation\s+time|regular\s+time\s+only|excludes?\s+extra\s+time|"
    r"extra\s+time\s+and\s+penalt(?:y|ies)\s+do\s+not\s+count)\b",
    re.IGNORECASE,
)
_INCL_OT_RE = re.compile(
    r"\b(?:including\s+overtime|includes?\s+overtime|incl\.?\s+ot|extra\s+time\s+and\s+penalt|"
    r"shootout\s+included|overtime\s+counts)\b",
    re.IGNORECASE,
)
_TENNIS_RETIREMENT_ADV_RE = re.compile(
    r"\b(?:player\s+who\s+advances|advances\s+to\s+the\s+next\s+round\s+resolves\s+to\s+yes|"
    r"walkover.*resolves\s+50-50.*retirement.*advances)\b",
    re.IGNORECASE,
)
_TENNIS_RETIREMENT_VOID_RE = re.compile(
    r"\b(?:if\s+a\s+player\s+retires.*50-50|retirement.*void|must\s+complete\s+all\s+sets)\b",
    re.IGNORECASE,
)
_TWO_LEGGED_AGG_RE = re.compile(r"\b(?:aggregate\s+score|two-legged|1st\s+leg|2nd\s+leg)\b", re.IGNORECASE)
_DOUBLE_ELIM_RE = re.compile(r"\b(?:upper\s+bracket|lower\s+bracket|grand\s+final\s+reset|double\s+elimination)\b", re.IGNORECASE)

_TOURNAMENT_CHAMP_RE = re.compile(
    r"^will\s+(?:the\s+)?(?P<team>[A-Za-z0-9.\-'\s]{2,36}?)\s+win\s+(?:the\s+)?(?P<yr>20\d{2}(?:[-–]\d{2,4})?\s+)?(?P<comp>nba\s+finals|nba\s+championship|super\s+bowl|stanley\s+cup|world\s+series|uefa\s+champions\s+league|fifa\s+world\s+cup)\s*\??$",
    re.IGNORECASE,
)
_TOURNAMENT_SEMI_CONF_RE = re.compile(
    r"^will\s+(?:the\s+)?(?P<team>[A-Za-z0-9.\-'\s]{2,36}?)\s+(?:win\s+the\s+(?P<yr1>20\d{2}(?:[-–]\d{2,4})?\s+)?(?P<conf>(?:eastern|western|afc|nfc|american\s+league|national\s+league)\s+(?:conference|pennant))|reach\s+the\s+(?P<yr2>20\d{2}(?:[-–]\d{2,4})?\s+)?(?P<final_comp>nba\s+finals|super\s+bowl|stanley\s+cup\s+final|world\s+series|uefa\s+champions\s+league\s+final|fifa\s+world\s+cup\s+final))\s*\??$",
    re.IGNORECASE,
)


def _norm_team(raw: str) -> str:
    s = str(raw or "").lower()
    s = re.sub(
        r"\s+(?:double\s+chance|draw\s+no\s+bet|cup\s+tie|more\s+markets|spreads?|totals?|moneyline|over\s*under|o/u.*|1st\s+half|2nd\s+half)\s*$",
        "",
        s,
    )
    s = re.sub(r"\b(?:the|fc|cf|afc|sc)\b", " ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return " ".join(s.split())


@dataclass(frozen=True)
class ParsedSportsContract:
    market: CanonicalBinaryMarket
    sport_league: str
    fixture_key: str
    teams: Tuple[str, ...]
    market_kind: str
    # Token & outcome semantics:
    primary_team: str
    secondary_team: str
    line_value: Optional[float]
    period_scope: str  # "REGULATION_90M" | "FULL_MATCH_INCL_OT" | "SUBPERIOD" | "TOURNAMENT" | "UNSPECIFIED_PERIOD"
    void_policy: str   # "50_50" | "NEGRISK_NO" | "DNB_DRAW_50_50" | "TENNIS_RET_ADVANCE" | "TENNIS_RET_VOID"
    has_two_legged_or_double_elim_risk: bool
    tournament_key: str = ""
    tournament_stage: str = ""  # "CHAMPION" | "CONF_OR_REACH_FINAL"


def parse_sports_contract(m: CanonicalBinaryMarket) -> Optional[ParsedSportsContract]:
    """Parses binary and 2-way (`[TeamA, TeamB]`, `[Over, Under]`) sports contracts across all leagues."""
    if m.closed_or_archived or not m.yes_token_id or not m.no_token_id:
        return None
    if m.is_placeholder_outcome or m.is_other_outcome or m.is_d001_disputed_quarantined():
        return None

    tag_blob = " ".join(m.tags)
    full_blob = f"{tag_blob} {m.event_slug} {m.event_title} {m.question}"
    sport_league = ""
    for lg, pat in _SPORT_LEAGUE_RES:
        if pat.search(full_blob):
            sport_league = lg
            break
    if not sport_league and m.sports_market_type:
        sport_league = "OTHER_SPORTS"
    if not sport_league:
        return None

    desc_q = f"{m.question} {m.description}"
    q_early_l = m.question.lower()
    grp_early_l = m.group_item_title.lower()
    q_grp_early_l = f"{q_early_l} {grp_early_l}"

    # Determine period_scope (preserving exact subperiod tag so Map 2 vs Map 3 AND 1H vs Full-Game are caught!)
    m_subp = _SUBPERIOD_SPORTS_RE.search(f"{m.question} {m.group_item_title} {m.sports_market_type}")
    if m_subp:
        sub_tok = re.sub(r"\s+", "_", m_subp.group(0).strip().upper())
        period_scope = f"SUBPERIOD:{sub_tok}"
    elif _ADVANCE_QUALIFY_RE.search(m.question):
        period_scope = "FULL_MATCH_INCL_OT"
    elif _REGULATION_90M_RE.search(desc_q):
        period_scope = "REGULATION_90M"
    elif _INCL_OT_RE.search(desc_q):
        period_scope = "FULL_MATCH_INCL_OT"
    elif sport_league == "SOCCER" and ("draw" in full_blob.lower() or m.neg_risk):
        period_scope = "REGULATION_90M"
    elif sport_league in {"NBA_BASKETBALL", "MLB_BASEBALL", "TENNIS"} and m.sports_market_type in {"moneyline", "spreads", "totals"}:
        period_scope = "FULL_MATCH_INCL_OT"
    else:
        period_scope = "UNSPECIFIED_PERIOD"

    # Determine void / retirement policy
    if "draw no bet" in q_early_l or "dnb" in grp_early_l:
        void_policy = "DNB_DRAW_50_50"
    elif sport_league == "TENNIS" and ("retire" in desc_q.lower() or "walkover" in desc_q.lower() or "advances" in desc_q.lower() or "sets" in desc_q.lower()):
        if _TENNIS_RETIREMENT_VOID_RE.search(desc_q):
            void_policy = "TENNIS_RET_VOID"
        elif _TENNIS_RETIREMENT_ADV_RE.search(desc_q):
            void_policy = "TENNIS_RET_ADVANCE"
        else:
            void_policy = m.cancel_rule_tag
    else:
        void_policy = m.cancel_rule_tag

    two_leg_or_de = bool(_TWO_LEGGED_AGG_RE.search(desc_q) or _DOUBLE_ELIM_RE.search(desc_q))

    # Check Tournament Championship vs Reach-Final / Win-Conference
    if m.is_standard_yes_no and q_early_l.startswith("will ") and ("win " in q_early_l or "reach " in q_early_l):
        mc = _TOURNAMENT_CHAMP_RE.match(m.question.strip())
        if mc:
            tm = _norm_team(mc.group("team"))
            yr_m = _YEAR_RE.search(f"{m.question} {m.event_title} {m.end_date_iso}")
            yr = yr_m.group(1) if yr_m else "2026"
            comp_raw = mc.group("comp").lower()
            t_key = "NBA" if "nba" in comp_raw else ("NFL" if "super bowl" in comp_raw else ("NHL" if "stanley" in comp_raw else ("MLB" if "world series" in comp_raw else ("UCL" if "champions league" in comp_raw else "WC"))))
            return ParsedSportsContract(
                market=m,
                sport_league=sport_league,
                fixture_key=f"TOURN::{t_key}::{yr}",
                teams=(tm,),
                market_kind="TOURNAMENT_ADVANCEMENT",
                primary_team=tm,
                secondary_team="",
                line_value=None,
                period_scope="TOURNAMENT",
                void_policy=void_policy,
                has_two_legged_or_double_elim_risk=two_leg_or_de,
                tournament_key=f"{t_key}::{yr}",
                tournament_stage="CHAMPION",
            )

        msf = _TOURNAMENT_SEMI_CONF_RE.match(m.question.strip())
        if msf:
            tm = _norm_team(msf.group("team"))
            yr_m = _YEAR_RE.search(f"{m.question} {m.event_title} {m.end_date_iso}")
            yr = yr_m.group(1) if yr_m else "2026"
            c_blob = f"{sport_league} {msf.group('conf') or ''} {msf.group('final_comp') or ''} {m.event_title}".lower()
            t_key = "NBA" if "nba" in c_blob else ("NFL" if ("nfl" in c_blob or "afc" in c_blob or "nfc" in c_blob or "super bowl" in c_blob) else ("NHL" if ("nhl" in c_blob or "stanley" in c_blob) else ("MLB" if ("mlb" in c_blob or "league pennant" in c_blob or "world series" in c_blob) else ("UCL" if "champions league" in c_blob else "WC"))))
            return ParsedSportsContract(
                market=m,
                sport_league=sport_league,
                fixture_key=f"TOURN::{t_key}::{yr}",
                teams=(tm,),
                market_kind="TOURNAMENT_ADVANCEMENT",
                primary_team=tm,
                secondary_team="",
                line_value=None,
                period_scope="TOURNAMENT",
                void_policy=void_policy,
                has_two_legged_or_double_elim_risk=two_leg_or_de,
                tournament_key=f"{t_key}::{yr}",
                tournament_stage="CONF_OR_REACH_FINAL",
            )

    # Extract fixture teams `(t1, t2)` from `event_title` or `question`
    t1_norm, t2_norm = "", ""
    for src_txt in (m.event_title, m.question):
        src_s = src_txt.strip()
        src_sl = src_s.lower()
        if " vs" not in src_sl and " v." not in src_sl and " v " not in src_sl and " @ " not in src_sl:
            continue
        mv = _VS_FIXTURE_RE.search(src_s)
        if mv:
            t1_norm = _norm_team(mv.group("t1"))
            t2_norm = _norm_team(mv.group("t2"))
            if t1_norm and t2_norm and t1_norm != t2_norm:
                break
    if (not t1_norm or not t2_norm) and not m.is_standard_yes_no:
        o0_n, o1_n = _norm_team(m.outcome_0_label), _norm_team(m.outcome_1_label)
        if o0_n not in {"over", "under", "yes", "no"} and o1_n not in {"over", "under", "yes", "no"}:
            t1_norm, t2_norm = o0_n, o1_n

    if not t1_norm or not t2_norm or t1_norm == t2_norm:
        return None

    day_ref = int((m.start_ts or m.end_ts or 0.0) // (2 * 86400.0))
    pair_sorted = tuple(sorted((t1_norm, t2_norm)))
    fixture_key = f"{sport_league}::{pair_sorted[0]}__VS__{pair_sorted[1]}::{day_ref}"

    q_l = q_early_l
    grp_l = grp_early_l
    smt = m.sports_market_type

    # Reject individual player props / team totals so `"Jayson Tatum: Points O/U 39.5"` never mixes with match totals!
    if smt in _PLAYER_OR_TEAM_PROP_TYPES or any(
        smt.endswith(sfx) for sfx in ("_points", "_rebounds", "_assists", "_yards", "_tds", "_threes", "_kills", "team_totals")
    ):
        return None
    if ":" in m.question:
        q_prefix = m.question.split(":", 1)[0].strip().lower()
        if " vs" not in q_prefix and " v." not in q_prefix and " @ " not in q_prefix and q_prefix not in {"spread", "totals", "total", "over/under", "moneyline"}:
            # Prefix like `"Jayson Tatum: ..."` or `"Celtics Team Total: ..."` is a player/team prop, not full match!
            return None

    # 1. Match Totals (`Over / Under` — full-match or same-subperiod match total only, never player props!)
    has_ou_outcomes = {m.outcome_0_label.lower(), m.outcome_1_label.lower()} == {"over", "under"}
    is_total_smt = (smt in {"totals", "total", ""} or smt.endswith("_totals")) and "team" not in smt
    mt_ou = _TOTAL_OU_RE.search(f"{m.question} {m.group_item_title}") if (
        is_total_smt and (smt in {"totals", "total"} or smt.endswith("_totals") or has_ou_outcomes or "o/u" in q_grp_early_l or "over/under" in q_grp_early_l or "total " in q_grp_early_l)
    ) else None
    if is_total_smt and (smt in {"totals", "total"} or smt.endswith("_totals") or mt_ou or has_ou_outcomes):
        ln = m.sports_line if m.sports_line is not None else (_sf(mt_ou.group("line"), float("nan")) if mt_ou else float("nan"))
        if math.isfinite(ln) and ln > 0:
            return ParsedSportsContract(
                market=m,
                sport_league=sport_league,
                fixture_key=fixture_key,
                teams=pair_sorted,
                market_kind="TOTAL_OU",
                primary_team="OVER" if m.outcome_0_label.lower() != "under" else "UNDER",
                secondary_team="UNDER" if m.outcome_0_label.lower() != "under" else "OVER",
                line_value=float(ln),
                period_scope=period_scope,
                void_policy=void_policy,
                has_two_legged_or_double_elim_risk=two_leg_or_de,
            )

    # 2. Spreads / Handicaps (`Team (+/-X.5)`)
    if smt in {"spreads", "spread", "handicap"} or "spread" in q_grp_early_l:
        msp = _SPREAD_PARSE_RE.search(f"{m.group_item_title} {m.question}")
        raw_tm = _norm_team(msp.group("team")) if msp else _norm_team(m.outcome_0_label)
        h_val = float("nan")
        if msp:
            sgn = -1.0 if msp.group("sign") == "-" else 1.0
            h_val = sgn * float(msp.group("pts"))
        elif m.sports_line is not None:
            h_val = float(m.sports_line)
        matched_tm = pair_sorted[0] if (raw_tm and (raw_tm in pair_sorted[0] or pair_sorted[0] in raw_tm)) else (
            pair_sorted[1] if (raw_tm and (raw_tm in pair_sorted[1] or pair_sorted[1] in raw_tm)) else ""
        )
        other_tm = pair_sorted[1] if matched_tm == pair_sorted[0] else pair_sorted[0]
        if matched_tm and math.isfinite(h_val):
            return ParsedSportsContract(
                market=m,
                sport_league=sport_league,
                fixture_key=fixture_key,
                teams=pair_sorted,
                market_kind="SPREAD",
                primary_team=matched_tm,
                secondary_team=other_tm,
                line_value=h_val,
                period_scope=period_scope,
                void_policy=void_policy,
                has_two_legged_or_double_elim_risk=two_leg_or_de,
            )

    # 3. Soccer Draw
    if m.is_standard_yes_no and "draw" in q_grp_early_l and _DRAW_MATCH_RE.search(f"{m.group_item_title} {m.question}") and "or draw" not in q_l and "draw or" not in q_l and "draw no bet" not in q_l:
        return ParsedSportsContract(
            market=m,
            sport_league=sport_league,
            fixture_key=fixture_key,
            teams=pair_sorted,
            market_kind="SOCCER_DRAW",
            primary_team="DRAW",
            secondary_team="",
            line_value=None,
            period_scope=period_scope,
            void_policy=void_policy,
            has_two_legged_or_double_elim_risk=two_leg_or_de,
        )

    # 4. Double Chance (`Team A or Draw`, `Team B or Draw`, `Team A or Team B`)
    mdc = _DOUBLE_CHANCE_RE.search(f"{m.group_item_title} {m.question}") if (
        m.is_standard_yes_no and ("draw" in q_grp_early_l or "double chance" in q_grp_early_l or "to win" in q_grp_early_l)
    ) else None
    if m.is_standard_yes_no and mdc:
        dc_raw = _norm_team(mdc.group("t1") or mdc.group("t2") or "")
        if dc_raw:
            matched_tm = pair_sorted[0] if (dc_raw in pair_sorted[0] or pair_sorted[0] in dc_raw) else (
                pair_sorted[1] if (dc_raw in pair_sorted[1] or pair_sorted[1] in dc_raw) else ""
            )
            if matched_tm:
                return ParsedSportsContract(
                    market=m,
                    sport_league=sport_league,
                    fixture_key=fixture_key,
                    teams=pair_sorted,
                    market_kind="DOUBLE_CHANCE_TEAM_DRAW",
                    primary_team=matched_tm,
                    secondary_team="DRAW",
                    line_value=None,
                    period_scope=period_scope,
                    void_policy=void_policy,
                    has_two_legged_or_double_elim_risk=two_leg_or_de,
                )
        elif mdc.group("ta") and mdc.group("tb"):
            return ParsedSportsContract(
                market=m,
                sport_league=sport_league,
                fixture_key=fixture_key,
                teams=pair_sorted,
                market_kind="DOUBLE_CHANCE_EITHER_TEAM",
                primary_team=pair_sorted[0],
                secondary_team=pair_sorted[1],
                line_value=None,
                period_scope=period_scope,
                void_policy=void_policy,
                has_two_legged_or_double_elim_risk=two_leg_or_de,
            )

    # 5. Qualification / To Advance (`incl. extra time & penalties`)
    if m.is_standard_yes_no and _ADVANCE_QUALIFY_RE.search(m.question):
        for tm_cand in pair_sorted:
            if tm_cand in _norm_team(m.question):
                return ParsedSportsContract(
                    market=m,
                    sport_league=sport_league,
                    fixture_key=fixture_key,
                    teams=pair_sorted,
                    market_kind="TO_ADVANCE",
                    primary_team=tm_cand,
                    secondary_team=pair_sorted[1] if tm_cand == pair_sorted[0] else pair_sorted[0],
                    line_value=None,
                    period_scope="FULL_MATCH_INCL_OT",
                    void_policy=void_policy,
                    has_two_legged_or_double_elim_risk=two_leg_or_de,
                )

    # 6. Moneyline (`[Team0, Team1]` 2-way OR `Will Team X win?` Yes/No leg)
    if not m.is_standard_yes_no:
        o0_n, o1_n = _norm_team(m.outcome_0_label), _norm_team(m.outcome_1_label)
        t0 = pair_sorted[0] if (o0_n in pair_sorted[0] or pair_sorted[0] in o0_n) else (pair_sorted[1] if (o0_n in pair_sorted[1] or pair_sorted[1] in o0_n) else "")
        t1 = pair_sorted[1] if t0 == pair_sorted[0] else (pair_sorted[0] if t0 == pair_sorted[1] else "")
        if t0 and t1:
            return ParsedSportsContract(
                market=m,
                sport_league=sport_league,
                fixture_key=fixture_key,
                teams=pair_sorted,
                market_kind="TWO_WAY_MONEYLINE",
                primary_team=t0,
                secondary_team=t1,
                line_value=None,
                period_scope=period_scope,
                void_policy=void_policy,
                has_two_legged_or_double_elim_risk=two_leg_or_de,
            )
    else:
        mw = _TEAM_WIN_MATCH_RE.match(m.question.strip())
        probe_tm = _norm_team(mw.group("team")) if mw else _norm_team(grp_l)
        if probe_tm:
            matched_tm = pair_sorted[0] if (probe_tm in pair_sorted[0] or pair_sorted[0] in probe_tm) else (
                pair_sorted[1] if (probe_tm in pair_sorted[1] or pair_sorted[1] in probe_tm) else ""
            )
            if matched_tm:
                mk = "DRAW_NO_BET" if void_policy == "DNB_DRAW_50_50" else "THREE_WAY_TEAM_WIN"
                return ParsedSportsContract(
                    market=m,
                    sport_league=sport_league,
                    fixture_key=fixture_key,
                    teams=pair_sorted,
                    market_kind=mk,
                    primary_team=matched_tm,
                    secondary_team=pair_sorted[1] if matched_tm == pair_sorted[0] else pair_sorted[0],
                    line_value=None,
                    period_scope=period_scope,
                    void_policy=void_policy,
                    has_two_legged_or_double_elim_risk=two_leg_or_de,
                )

    return None


def _sports_team_token(sc: ParsedSportsContract, team: str) -> Optional[str]:
    if sc.market_kind == "TWO_WAY_MONEYLINE":
        if sc.primary_team == team:
            return sc.market.yes_token_id
        if sc.secondary_team == team:
            return sc.market.no_token_id
        return None
    if sc.primary_team == team:
        return sc.market.yes_token_id
    return None


def _sports_spread_tokens_for_team(sc: ParsedSportsContract, team: str) -> Optional[Tuple[str, float]]:
    """Returns `(token_id_for_team_spread, signed_handicap_for_team)`."""
    if sc.market_kind != "SPREAD" or sc.line_value is None:
        return None
    if sc.market.is_standard_yes_no:
        if sc.primary_team == team:
            return sc.market.yes_token_id, float(sc.line_value)
        if sc.secondary_team == team:
            return sc.market.no_token_id, -float(sc.line_value)
    else:
        if sc.primary_team == team:
            return sc.market.yes_token_id, float(sc.line_value)
        if sc.secondary_team == team:
            return sc.market.no_token_id, -float(sc.line_value)
    return None


def _sports_total_tokens(sc: ParsedSportsContract) -> Optional[Tuple[str, str, float]]:
    """Returns `(over_token_id, under_token_id, line)`."""
    if sc.market_kind != "TOTAL_OU" or sc.line_value is None:
        return None
    if sc.primary_team == "OVER":
        return sc.market.yes_token_id, sc.market.no_token_id, float(sc.line_value)
    return sc.market.no_token_id, sc.market.yes_token_id, float(sc.line_value)


def detect_family_g_sports_structures(
    markets: Sequence[CanonicalBinaryMarket],
    books: Mapping[str, InstrumentOrderBook],
    *,
    verifier: Optional[UniversalArbVerifier] = None,
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
    max_candidates: int = 350,
) -> Tuple[List[DetectedOpportunity], Dict[str, int]]:
    """
    Family G — Full-Universe Sports Outcome Structure Scanner:
      1. Soccer 3-Way (`TeamA / Draw / TeamB`) vs Double-Chance (`1X + TeamB`, `X2 + TeamA`, `12 + Draw`),
         Draw-No-Bet, Qualification (`90m` vs `incl. OT` trap explicitly downgraded to `CLASS_D`!),
         and Standalone 3-Way `NO` Void Trap (`50-50` cancellation turns `3 NO` cost `>$1.50` into a loss!).
      2. Moneyline (`Team A`) vs Opposite Spread (`Team B + k`, `k > 0` "Polish Middle") across NBA/NFL/NHL/MLB/Esports/Tennis,
         explicitly modeling Regulation Tie (`NFL`/`Soccer`), Integer Push (`k in Z`), `50-50` Postponement/Void,
         `Regulation` vs `OT` mismatch, and Tennis Retirement rule divergence (`CLASS_D`!).
      3. Totals Corridors (`Over K_low + Under K_high` for `K_low < K_high`).
      4. Single-Elimination Tournament Advancement (`Win Championship => Win Conference / Reach Final`),
         blocking Two-Legged Aggregate and Double-Elimination bracket resets (`CLASS_D`!).
    """
    ver = verifier or UniversalArbVerifier()
    results: List[DetectedOpportunity] = []
    rejection_counts: Dict[str, int] = {}

    def _bump(r: str) -> None:
        rejection_counts[r] = rejection_counts.get(r, 0) + 1

    by_fixture: Dict[str, List[ParsedSportsContract]] = {}
    tourn_groups: Dict[Tuple[str, str], List[ParsedSportsContract]] = {}

    for m in markets:
        ps = parse_sports_contract(m)
        if ps is None:
            continue
        if ps.market_kind == "TOURNAMENT_ADVANCEMENT":
            tourn_groups.setdefault((ps.tournament_key, ps.primary_team), []).append(ps)
        else:
            by_fixture.setdefault(ps.fixture_key, []).append(ps)

    def _check_sports_rule_compat(contracts: Sequence[ParsedSportsContract]) -> List[str]:
        reasons: List[str] = []
        scopes = {c.period_scope for c in contracts}
        sub_scopes = {s for s in scopes if s.startswith("SUBPERIOD")}
        non_sub_scopes = scopes - sub_scopes
        if sub_scopes and non_sub_scopes:
            reasons.append("SUBPERIOD_VS_FULL_GAME_MISMATCH")
        elif len(sub_scopes) > 1:
            reasons.append(f"SUBPERIOD_MISMATCH:{sorted(sub_scopes)}")
        elif "UNSPECIFIED_PERIOD" in scopes:
            reasons.append(f"PERIOD_SCOPE_UNSPECIFIED:{sorted(scopes)}")
        elif len(scopes) > 1:
            reasons.append(f"REGULATION_VS_OVERTIME_MISMATCH:{sorted(scopes)}")

        voids = {c.void_policy for c in contracts}
        if {"TENNIS_RET_ADVANCE", "TENNIS_RET_VOID"}.issubset(voids):
            reasons.append("TENNIS_RETIREMENT_RULE_MISMATCH")
        if any(c.has_two_legged_or_double_elim_risk for c in contracts):
            reasons.append("TWO_LEGGED_OR_DOUBLE_ELIMINATION_RULE_TRAP")
        return reasons

    for fix_key, grp in by_fixture.items():
        if len(grp) < 2:
            continue
        team_a, team_b = grp[0].teams[0], grp[0].teams[1]

        three_way_a = [c for c in grp if c.market_kind == "THREE_WAY_TEAM_WIN" and c.primary_team == team_a]
        three_way_b = [c for c in grp if c.market_kind == "THREE_WAY_TEAM_WIN" and c.primary_team == team_b]
        draws = [c for c in grp if c.market_kind == "SOCCER_DRAW"]
        two_way_mls = [c for c in grp if c.market_kind == "TWO_WAY_MONEYLINE"]
        dc_team_draw = [c for c in grp if c.market_kind == "DOUBLE_CHANCE_TEAM_DRAW"]
        dc_either = [c for c in grp if c.market_kind == "DOUBLE_CHANCE_EITHER_TEAM"]
        to_adv = [c for c in grp if c.market_kind == "TO_ADVANCE"]
        dnbs = [c for c in grp if c.market_kind == "DRAW_NO_BET"]
        spreads = [c for c in grp if c.market_kind == "SPREAD"]
        totals = [c for c in grp if c.market_kind == "TOTAL_OU"]

        # G.1a: Soccer 3-Way Standalone Complete Set (`YES_A + YES_Draw + YES_B` AND `NO_A + NO_Draw + NO_B`)
        if three_way_a and three_way_b and draws:
            ca, cd, cb = three_way_a[0], draws[0], three_way_b[0]
            # Skip intra-event NegRisk 3-way (owned by Family C) UNLESS standalone `neg_risk == False` or cross-event!
            if not (ca.market.event_id == cd.market.event_id == cb.market.event_id and ca.market.neg_risk and cd.market.neg_risk and cb.market.neg_risk):
                reasons = _check_sports_rule_compat([ca, cd, cb])
                # Build exact 4-state `HOME_WIN`, `DRAW`, `AWAY_WIN`, `VOID_POSTPONED`!
                v_pay_y = 0.0 if ca.void_policy == "NEGRISK_NO" else 0.5
                v_pay_n = 1.0 if ca.void_policy == "NEGRISK_NO" else 0.5
                states_1x2 = [
                    _mk_state("HOME_REG_WIN", f"{team_a} wins", {
                        ca.market.yes_token_id: 1.0, ca.market.no_token_id: 0.0,
                        cd.market.yes_token_id: 0.0, cd.market.no_token_id: 1.0,
                        cb.market.yes_token_id: 0.0, cb.market.no_token_id: 1.0,
                    }, 0.40),
                    _mk_state("REG_DRAW", "Regulation draw", {
                        ca.market.yes_token_id: 0.0, ca.market.no_token_id: 1.0,
                        cd.market.yes_token_id: 1.0, cd.market.no_token_id: 0.0,
                        cb.market.yes_token_id: 0.0, cb.market.no_token_id: 1.0,
                    }, 0.25),
                    _mk_state("AWAY_REG_WIN", f"{team_b} wins", {
                        ca.market.yes_token_id: 0.0, ca.market.no_token_id: 1.0,
                        cd.market.yes_token_id: 0.0, cd.market.no_token_id: 1.0,
                        cb.market.yes_token_id: 1.0, cb.market.no_token_id: 0.0,
                    }, 0.34),
                    _mk_state("VOID_ABANDONED_50_50", "Match abandoned/voided outside window", {
                        ca.market.yes_token_id: v_pay_y, ca.market.no_token_id: v_pay_n,
                        cd.market.yes_token_id: 0.0 if cd.void_policy == "NEGRISK_NO" else 0.5,
                        cd.market.no_token_id: 1.0 if cd.void_policy == "NEGRISK_NO" else 0.5,
                        cb.market.yes_token_id: 0.0 if cb.void_policy == "NEGRISK_NO" else 0.5,
                        cb.market.no_token_id: 1.0 if cb.void_policy == "NEGRISK_NO" else 0.5,
                    }, 0.01, is_edge_or_void_state=True),
                ]
                if any(c.void_policy == "50_50" for c in (ca, cd, cb)):
                    # Note: for `YES_A + YES_D + YES_B`, `0.5 + 0.5 + 0.5 = $1.50 >= $1.00` (safe!),
                    # whereas for `NO_A + NO_D + NO_B`, `0.5 + 0.5 + 0.5 = $1.50 < $2.00` (VOID TRAP if cost > $1.50!)
                    pass
                for r in reasons:
                    _bump(r.split(":")[0])
                legs_yes3 = [
                    _build_leg_with_optional_inventory(ca.market.yes_token_id, ca.market.market_id, f"YES[{team_a}]", holdings),
                    _build_leg_with_optional_inventory(cd.market.yes_token_id, cd.market.market_id, "YES[Draw]", holdings),
                    _build_leg_with_optional_inventory(cb.market.yes_token_id, cb.market.market_id, f"YES[{team_b}]", holdings),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "SOCCER_3WAY_YES", [ca.market.market_id, cd.market.market_id, cb.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="SOCCER_3WAY_COMPLETE_YES",
                        relationship_type="THREE_WAY_PARTITION",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons else "RULE_MISMATCH_REJECTED",
                        markets=[ca.market, cd.market, cb.market],
                        legs=legs_yes3,
                        states=states_1x2,
                        title_summary=f"[SOCCER_1X2_YES] {team_a} / Draw / {team_b}",
                        rule_verified=len(reasons) == 0,
                        rule_compatibility_notes=[f"period={ca.period_scope}", f"void={ca.void_policy}"],
                        divergence_or_rejection_reasons=reasons,
                    )
                )
                # Also evaluate 3-way `NO` bundle so `VOID_ABANDONED_50_50` (`$1.50` vs `$2.00`) is explicitly audited!
                reasons_no3 = list(reasons)
                if any(c.void_policy == "50_50" for c in (ca, cd, cb)):
                    reasons_no3.append("STANDALONE_50_50_VOID_CAPS_3NO_PAYOUT_AT_1_50")
                    _bump("STANDALONE_50_50_VOID_CAPS_3NO_PAYOUT_AT_1_50")
                legs_no3 = [
                    _build_leg_with_optional_inventory(ca.market.no_token_id, ca.market.market_id, f"NO[{team_a}]", holdings),
                    _build_leg_with_optional_inventory(cd.market.no_token_id, cd.market.market_id, "NO[Draw]", holdings),
                    _build_leg_with_optional_inventory(cb.market.no_token_id, cb.market.market_id, f"NO[{team_b}]", holdings),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "SOCCER_3WAY_NO", [ca.market.market_id, cd.market.market_id, cb.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="SOCCER_3WAY_NO_BUNDLE",
                        relationship_type="THREE_WAY_NO_COVER",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_no3 else "RULE_MISMATCH_REJECTED",
                        markets=[ca.market, cd.market, cb.market],
                        legs=legs_no3,
                        states=states_1x2,
                        title_summary=f"[SOCCER_1X2_NO] NO({team_a}) + NO(Draw) + NO({team_b})",
                        rule_verified=len(reasons_no3) == 0,
                        rule_compatibility_notes=[f"period={ca.period_scope}", f"void={ca.void_policy}"],
                        divergence_or_rejection_reasons=reasons_no3,
                    )
                )

        # G.1b: Double-Chance (`TeamA or Draw`) + `YES(TeamB)` (`1X + 2` complete cover)
        for cdc in dc_team_draw:
            opp_wins = three_way_b if cdc.primary_team == team_a else three_way_a
            opp_tm = team_b if cdc.primary_team == team_a else team_a
            for copp in opp_wins:
                reasons = _check_sports_rule_compat([cdc, copp])
                if cdc.void_policy != copp.void_policy and "NEGRISK_NO" in {cdc.void_policy, copp.void_policy}:
                    reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
                for r in reasons:
                    _bump(r.split(":")[0])
                v_dc = 0.0 if cdc.void_policy == "NEGRISK_NO" else 0.5
                v_op = 0.0 if copp.void_policy == "NEGRISK_NO" else 0.5
                states_dc = [
                    _mk_state("DC_TEAM_OR_DRAW", f"{cdc.primary_team} or Draw", {
                        cdc.market.yes_token_id: 1.0, cdc.market.no_token_id: 0.0,
                        copp.market.yes_token_id: 0.0, copp.market.no_token_id: 1.0,
                    }, 0.65),
                    _mk_state("OPP_REG_WIN", f"{opp_tm} wins", {
                        cdc.market.yes_token_id: 0.0, cdc.market.no_token_id: 1.0,
                        copp.market.yes_token_id: 1.0, copp.market.no_token_id: 0.0,
                    }, 0.34),
                    _mk_state("VOID_MATCH", "Match voided", {
                        cdc.market.yes_token_id: v_dc, cdc.market.no_token_id: 1.0 - v_dc,
                        copp.market.yes_token_id: v_op, copp.market.no_token_id: 1.0 - v_op,
                    }, 0.01, is_edge_or_void_state=True),
                ]
                legs_dc = [
                    _build_leg_with_optional_inventory(cdc.market.yes_token_id, cdc.market.market_id, f"YES[{cdc.primary_team}/Draw]", holdings),
                    _build_leg_with_optional_inventory(copp.market.yes_token_id, copp.market.market_id, f"YES[{opp_tm}]", holdings),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "SOCCER_DC_COVER", [cdc.market.market_id, copp.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="SOCCER_DOUBLE_CHANCE_COVER",
                        relationship_type="COMPLEMENTARY_COVER",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons else "RULE_MISMATCH_REJECTED",
                        markets=[cdc.market, copp.market],
                        legs=legs_dc,
                        states=states_dc,
                        title_summary=f"[DOUBLE_CHANCE] ({cdc.primary_team} or Draw) + ({opp_tm})",
                        rule_verified=len(reasons) == 0,
                        rule_compatibility_notes=[f"period={cdc.period_scope}"],
                        divergence_or_rejection_reasons=reasons,
                    )
                )

        # G.1c: `12` Double-Chance (`Either Team Wins`) + `Draw`
        for ce in dc_either:
            for cd in draws:
                reasons = _check_sports_rule_compat([ce, cd])
                if ce.void_policy != cd.void_policy and "NEGRISK_NO" in {ce.void_policy, cd.void_policy}:
                    reasons.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
                for r in reasons:
                    _bump(r.split(":")[0])
                states_12 = [
                    _mk_state("TEAM_WINS", "Either team wins in regulation", {
                        ce.market.yes_token_id: 1.0, ce.market.no_token_id: 0.0,
                        cd.market.yes_token_id: 0.0, cd.market.no_token_id: 1.0,
                    }, 0.74),
                    _mk_state("DRAW", "Regulation draw", {
                        ce.market.yes_token_id: 0.0, ce.market.no_token_id: 1.0,
                        cd.market.yes_token_id: 1.0, cd.market.no_token_id: 0.0,
                    }, 0.25),
                    _mk_state("VOID", "Match voided", {
                        ce.market.yes_token_id: 0.0 if ce.void_policy == "NEGRISK_NO" else 0.5,
                        cd.market.yes_token_id: 0.0 if cd.void_policy == "NEGRISK_NO" else 0.5,
                    }, 0.01, is_edge_or_void_state=True),
                ]
                legs_12 = [
                    _build_leg_with_optional_inventory(ce.market.yes_token_id, ce.market.market_id, "YES[12]", holdings),
                    _build_leg_with_optional_inventory(cd.market.yes_token_id, cd.market.market_id, "YES[Draw]", holdings),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "SOCCER_12_DRAW", [ce.market.market_id, cd.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="SOCCER_12_PLUS_DRAW",
                        relationship_type="COMPLEMENTARY_COVER",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons else "RULE_MISMATCH_REJECTED",
                        markets=[ce.market, cd.market],
                        legs=legs_12,
                        states=states_12,
                        title_summary=f"[SOCCER_12_DRAW] ({team_a} or {team_b}) + Draw",
                        rule_verified=len(reasons) == 0,
                        rule_compatibility_notes=[f"period={ce.period_scope}"],
                        divergence_or_rejection_reasons=reasons,
                    )
                )

        # G.1d: Regulation 3-Way vs `To Advance / Qualify` OR `Draw-No-Bet` Trap Check!
        # In single-match knockout soccer: `Team A wins in 90m => Team A advances` (`NO_90m_A + YES_Advance_A` is valid ONLY if single-legged!),
        # whereas `NO_Advance_A + YES_90m_A` or `YES_90m_B + YES_Advance_A` FAILS on Extra-Time / Penalties (`REGULATION_VS_OVERTIME_MISMATCH`)!
        for c_adv in to_adv:
            opp_3w = three_way_b if c_adv.primary_team == team_a else three_way_a
            same_3w = three_way_a if c_adv.primary_team == team_a else three_way_b
            # Trap check: `YES(Team A Advances) + YES(Team B 90m)` leaves `90m Draw -> Team B wins Penalties` uncovered (`$0.00`)!
            for cb_reg in opp_3w:
                reasons_trap = _check_sports_rule_compat([c_adv, cb_reg])
                if "REGULATION_VS_OVERTIME_MISMATCH" not in " ".join(reasons_trap):
                    reasons_trap.append("REGULATION_90M_VS_QUALIFICATION_DRAW_GAP")
                for r in reasons_trap:
                    _bump(r.split(":")[0])
                states_trap = [
                    _mk_state("A_WINS_90M", f"{c_adv.primary_team} wins 90m", {c_adv.market.yes_token_id: 1.0, cb_reg.market.yes_token_id: 0.0}, 0.40),
                    _mk_state("DRAW_90M_OPP_ADVANCES_OT", f"90m Draw then {cb_reg.primary_team} wins OT/PK", {c_adv.market.yes_token_id: 0.0, cb_reg.market.yes_token_id: 0.0}, 0.15, is_edge_or_void_state=True),
                    _mk_state("DRAW_90M_A_ADVANCES_OT", f"90m Draw then {c_adv.primary_team} wins OT/PK", {c_adv.market.yes_token_id: 1.0, cb_reg.market.yes_token_id: 0.0}, 0.15),
                    _mk_state("B_WINS_90M", f"{cb_reg.primary_team} wins 90m", {c_adv.market.yes_token_id: 0.0, cb_reg.market.yes_token_id: 1.0}, 0.30),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "REG_VS_ADV_TRAP", [c_adv.market.market_id, cb_reg.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="REGULATION_VS_ADVANCE_MISMATCH",
                        relationship_type="INVALID_CROSS_PERIOD_COVER",
                        edge_proof_status="RULE_MISMATCH_REJECTED",
                        markets=[c_adv.market, cb_reg.market],
                        legs=[
                            _build_leg_with_optional_inventory(c_adv.market.yes_token_id, c_adv.market.market_id, f"YES[{c_adv.primary_team} Adv]", holdings),
                            _build_leg_with_optional_inventory(cb_reg.market.yes_token_id, cb_reg.market.market_id, f"YES[{cb_reg.primary_team} 90m]", holdings),
                        ],
                        states=states_trap,
                        title_summary=f"[REG_VS_OT_TRAP] {c_adv.primary_team} Advance + {cb_reg.primary_team} 90m",
                        rule_verified=False,
                        divergence_or_rejection_reasons=reasons_trap,
                    )
                )
            # Valid implication ONLY if single-match knockout (`!has_two_legged_or_double_elim_risk`): `Win 90m => Advance` (`NO_90m + YES_Advance`)
            for ca_reg in same_3w:
                reasons_imp: List[str] = []
                if c_adv.has_two_legged_or_double_elim_risk or ca_reg.has_two_legged_or_double_elim_risk:
                    reasons_imp.append("TWO_LEGGED_AGGREGATE_WIN_90M_DOES_NOT_IMPLY_ADVANCE")
                if ca_reg.void_policy == "50_50" and c_adv.void_policy == "NEGRISK_NO":
                    reasons_imp.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
                for r in reasons_imp:
                    _bump(r.split(":")[0])
                states_imp = StateSpaceBuilder.two_market_logical_states(
                    ca_reg.market.yes_token_id, ca_reg.market.no_token_id,
                    c_adv.market.yes_token_id, c_adv.market.no_token_id,
                    relation="A_IMPLIES_B" if not reasons_imp else "UNCONSTRAINED",
                    cancel_rule_a=ca_reg.void_policy, cancel_rule_b=c_adv.void_policy,
                )
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "WIN90_IMPLIES_ADV", [ca_reg.market.market_id, c_adv.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="SINGLE_KNOCKOUT_90M_IMPLIES_ADVANCE",
                        relationship_type="A_IMPLIES_B",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_imp else "RULE_MISMATCH_REJECTED",
                        markets=[ca_reg.market, c_adv.market],
                        legs=[
                            _build_leg_with_optional_inventory(ca_reg.market.no_token_id, ca_reg.market.market_id, f"NO[{ca_reg.primary_team} 90m]", holdings),
                            _build_leg_with_optional_inventory(c_adv.market.yes_token_id, c_adv.market.market_id, f"YES[{c_adv.primary_team} Adv]", holdings),
                        ],
                        states=states_imp,
                        title_summary=f"[90M_IMPLIES_ADV] {ca_reg.primary_team} 90m => Advance",
                        rule_verified=len(reasons_imp) == 0,
                        rule_compatibility_notes=["Single-match knockout: 90m win implies advancement"],
                        divergence_or_rejection_reasons=reasons_imp,
                    )
                )

        # G.1e: Draw-No-Bet (`DNB`) vs 3-Way (`DNB` resolves `$0.50` on Draw, so `DNB_A + 90m_B` only pays `$0.50` on Draw!)
        for cdnb in dnbs:
            opp_3w = three_way_b if cdnb.primary_team == team_a else three_way_a
            for cb_reg in opp_3w:
                _bump("DRAW_NO_BET_PAYS_0_50_ON_DRAW")
                states_dnb = [
                    _mk_state("A_WIN", f"{cdnb.primary_team} wins", {cdnb.market.yes_token_id: 1.0, cb_reg.market.yes_token_id: 0.0}, 0.40),
                    _mk_state("DRAW_50_50", "Draw resolves DNB at 0.50", {cdnb.market.yes_token_id: 0.5, cb_reg.market.yes_token_id: 0.0}, 0.25, is_edge_or_void_state=True),
                    _mk_state("B_WIN", f"{cb_reg.primary_team} wins", {cdnb.market.yes_token_id: 0.0, cb_reg.market.yes_token_id: 1.0}, 0.35),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "DNB_VS_3WAY_TRAP", [cdnb.market.market_id, cb_reg.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="DNB_VS_3WAY_DRAW_HAIR_CUT",
                        relationship_type="FRACTIONAL_DRAW_MISMATCH",
                        edge_proof_status="RULE_MISMATCH_REJECTED",
                        markets=[cdnb.market, cb_reg.market],
                        legs=[
                            _build_leg_with_optional_inventory(cdnb.market.yes_token_id, cdnb.market.market_id, f"DNB[{cdnb.primary_team}]", holdings),
                            _build_leg_with_optional_inventory(cb_reg.market.yes_token_id, cb_reg.market.market_id, f"3W[{cb_reg.primary_team}]", holdings),
                        ],
                        states=states_dnb,
                        title_summary=f"[DNB_TRAP] DNB({cdnb.primary_team}) + 3W({cb_reg.primary_team}) pays $0.50 on Draw",
                        rule_verified=False,
                        divergence_or_rejection_reasons=["DRAW_NO_BET_PAYS_0_50_ON_DRAW"],
                    )
                )

        # G.2: Moneyline vs Opposite Positive Handicap ("Polish Middle": `ML(Team X) + Spread(Team Y + k)`, `k >= 0.5`)
        ml_candidates = two_way_mls + three_way_a + three_way_b
        for c_ml in ml_candidates:
            for c_sp in spreads:
                if c_ml.market.market_id == c_sp.market.market_id:
                    continue
                for fav_tm, dog_tm in ((team_a, team_b), (team_b, team_a)):
                    tok_ml = _sports_team_token(c_ml, fav_tm)
                    sp_dog = _sports_spread_tokens_for_team(c_sp, dog_tm)
                    if not tok_ml or sp_dog is None:
                        continue
                    tok_sp_dog, dog_hcap = sp_dog
                    if dog_hcap < 0.5:
                        continue  # Only `dog_hcap >= +0.5` covers `margin <= 0`!

                    reasons_pm = _check_sports_rule_compat([c_ml, c_sp])
                    is_int_push = abs(dog_hcap - round(dog_hcap)) < 1e-6
                    # Can game end in a tie? (`SOCCER`, `NFL_FOOTBALL` regular season, `ESPORTS` Bo2, `THREE_WAY_TEAM_WIN`)
                    can_tie = (
                        c_ml.market_kind == "THREE_WAY_TEAM_WIN"
                        or c_ml.sport_league in {"SOCCER", "NFL_FOOTBALL", "ESPORTS"}
                    )
                    # Note: On a Tie (`margin == 0`):
                    #   - `THREE_WAY_TEAM_WIN(fav)` pays `0.00`, while `Spread(dog + k)` (`k >= 0.5`) pays `1.00` -> `0 + 1 = $1.00`!
                    #   - `TWO_WAY_MONEYLINE(fav)` on Tie resolves `0.50`, while `Spread(dog + k)` pays `1.00` -> `0.50 + 1.00 = $1.50`!
                    # What about Integer Handicap Push (`fav` wins by exact `k`, e.g., `dog +3.0` and `fav` wins by `3`)?
                    #   - `ML(fav)` pays `1.00` AND `Spread(dog +3.0)` resolves `0.50` -> `1.00 + 0.50 = $1.50 >= $1.00`!
                    # What about Match Void / Postponement (`50-50` vs `NEGRISK_NO`)?
                    v_ml = 0.0 if c_ml.void_policy == "NEGRISK_NO" else 0.5
                    v_sp = 0.0 if c_sp.void_policy == "NEGRISK_NO" else 0.5
                    if v_ml + v_sp < 1.0 - 1e-9:
                        reasons_pm.append("VOID_SETTLEMENT_SUM_BELOW_ONE")

                    for r in reasons_pm:
                        _bump(r.split(":")[0])

                    if not reasons_pm and len(by_fixture) > 25:
                        l1_pm = _quick_l1_buy_cost_sum([(tok_ml, c_ml.market), (tok_sp_dog, c_sp.market)], books)
                        if l1_pm is None or l1_pm > 1.0 + DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT:
                            continue
                    elif reasons_pm and len(results) > max_candidates * 2:
                        continue

                    pm_states: List[StateSpec] = [
                        _mk_state("FAV_WINS_BIG", f"{fav_tm} wins by > {dog_hcap:g}", {tok_ml: 1.0, tok_sp_dog: 0.0}, 0.38),
                        _mk_state("DOG_WINS", f"{dog_tm} wins outright", {tok_ml: 0.0, tok_sp_dog: 1.0}, 0.35),
                        _mk_state("VOID_POSTPONED", "Match postponed/abandoned", {tok_ml: v_ml, tok_sp_dog: v_sp}, 0.01, is_edge_or_void_state=True),
                    ]
                    if dog_hcap > 1.0 or (dog_hcap >= 1.5):
                        pm_states.append(
                            _mk_state("POLISH_MIDDLE_JACKPOT", f"{fav_tm} wins by 1..{dog_hcap:g} (BOTH legs pay!)", {tok_ml: 1.0, tok_sp_dog: 1.0}, 0.16)
                        )
                    if is_int_push:
                        pm_states.append(
                            _mk_state("EXACT_SPREAD_PUSH", f"{fav_tm} wins by exact {dog_hcap:g}", {tok_ml: 1.0, tok_sp_dog: 0.5}, 0.05, is_edge_or_void_state=True)
                        )
                    if can_tie:
                        ml_tie_pay = 0.0 if c_ml.market_kind == "THREE_WAY_TEAM_WIN" else 0.5
                        pm_states.append(
                            _mk_state("MATCH_TIE_SCORE", "Score tied at end of period", {tok_ml: ml_tie_pay, tok_sp_dog: 1.0}, 0.05, is_edge_or_void_state=True)
                        )
                    if any("REGULATION_VS_OVERTIME" in r or "SUBPERIOD" in r or "TENNIS_RETIREMENT" in r for r in reasons_pm):
                        # Explicit rule-break counterexample state (e.g. Fav loses in regulation/1H or opponent retires -> 0 + 0 = $0.00!)
                        pm_states.append(
                            _mk_state("PERIOD_OR_RETIREMENT_COUNTEREXAMPLE", "Rule mismatch state where both legs lose", {tok_ml: 0.0, tok_sp_dog: 0.0}, 0.05, is_edge_or_void_state=True)
                        )

                    legs_pm = [
                        _build_leg_with_optional_inventory(tok_ml, c_ml.market.market_id, f"ML[{fav_tm}]", holdings),
                        _build_leg_with_optional_inventory(tok_sp_dog, c_sp.market.market_id, f"SPREAD[{dog_tm} +{dog_hcap:g}]", holdings),
                    ]
                    results.append(
                        _finalize_detected_opportunity(
                            ver, books, holdings,
                            candidate_id=_make_candidate_id("G", "ML_SPREAD_MIDDLE", [c_ml.market.market_id, c_sp.market.market_id, fav_tm]),
                            family="FAMILY_G_SPORTS_STRUCTURE",
                            sub_type="MONEYLINE_VS_SPREAD_POLISH_MIDDLE",
                            relationship_type="SUPERSET_COVER",
                            edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_pm else "RULE_MISMATCH_REJECTED",
                            markets=[c_ml.market, c_sp.market],
                            legs=legs_pm,
                            states=pm_states,
                            title_summary=f"[ML_SPREAD] ML({fav_tm}) + Spread({dog_tm} +{dog_hcap:g})",
                            rule_verified=len(reasons_pm) == 0,
                            rule_compatibility_notes=[f"sport={c_ml.sport_league}", f"period={c_ml.period_scope}"],
                            divergence_or_rejection_reasons=reasons_pm,
                        )
                    )

        # G.3: Spread Ladder Monotonicity (`Team X + h_low => Team X + h_high` for `h_high > h_low` -> `Opposite(h_low) + TeamX(h_high)`)
        if len(spreads) >= 2:
            for tm in (team_a, team_b):
                tm_sp_items: List[Tuple[float, str, ParsedSportsContract]] = []
                for csp in spreads:
                    res_sp = _sports_spread_tokens_for_team(csp, tm)
                    if res_sp is not None:
                        tm_sp_items.append((res_sp[1], res_sp[0], csp))
                tm_sp_items.sort(key=lambda x: x[0])
                opp_tm = team_b if tm == team_a else team_a
                for idx in range(len(tm_sp_items) - 1):
                    h_tight, _tok_tight, c_tight = tm_sp_items[idx]
                    h_generous, tok_gen, c_gen = tm_sp_items[idx + 1]
                    if c_tight.market.market_id == c_gen.market.market_id or abs(h_generous - h_tight) < 0.25:
                        continue
                    opp_tight = _sports_spread_tokens_for_team(c_tight, opp_tm)
                    if opp_tight is None:
                        continue
                    tok_opp_tight = opp_tight[0]
                    reasons_sl = _check_sports_rule_compat([c_tight, c_gen])
                    for r in reasons_sl:
                        _bump(r.split(":")[0])
                    if not reasons_sl and len(by_fixture) > 25:
                        l1_sl = _quick_l1_buy_cost_sum([(tok_opp_tight, c_tight.market), (tok_gen, c_gen.market)], books)
                        if l1_sl is None or l1_sl > 1.0 + DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT:
                            continue
                    elif reasons_sl and len(results) > max_candidates * 2:
                        continue
                    v_1 = 0.0 if c_tight.void_policy == "NEGRISK_NO" else 0.5
                    v_2 = 0.0 if c_gen.void_policy == "NEGRISK_NO" else 0.5
                    sl_states = [
                        _mk_state("COVERS_TIGHT", f"{tm} covers {h_tight:+g} (and {h_generous:+g})", {tok_opp_tight: 0.0, tok_gen: 1.0}, 0.42),
                        _mk_state("MIDDLE_CORRIDOR", f"Margin lands strictly between {h_tight:+g} and {h_generous:+g}", {tok_opp_tight: 1.0, tok_gen: 1.0}, 0.15),
                        _mk_state("MISSES_BOTH", f"{opp_tm} covers {-h_generous:+g}", {tok_opp_tight: 1.0, tok_gen: 0.0}, 0.42),
                        _mk_state("VOID_GAME", "Match voided", {tok_opp_tight: v_1, tok_gen: v_2}, 0.01, is_edge_or_void_state=True),
                    ]
                    if any(reasons_sl):
                        sl_states.append(_mk_state("RULE_MISMATCH_LOSS", "Subperiod/OT mismatch counterexample", {tok_opp_tight: 0.0, tok_gen: 0.0}, 0.05, is_edge_or_void_state=True))
                    results.append(
                        _finalize_detected_opportunity(
                            ver, books, holdings,
                            candidate_id=_make_candidate_id("G", "SPREAD_LADDER", [c_tight.market.market_id, c_gen.market.market_id, tm]),
                            family="FAMILY_G_SPORTS_STRUCTURE",
                            sub_type="SPREAD_HANDICAP_CORRIDOR",
                            relationship_type="SPREAD_MONOTONICITY",
                            edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_sl else "RULE_MISMATCH_REJECTED",
                            markets=[c_tight.market, c_gen.market],
                            legs=[
                                _build_leg_with_optional_inventory(tok_opp_tight, c_tight.market.market_id, f"SPREAD[{opp_tm} {-h_tight:+g}]", holdings),
                                _build_leg_with_optional_inventory(tok_gen, c_gen.market.market_id, f"SPREAD[{tm} {h_generous:+g}]", holdings),
                            ],
                            states=sl_states,
                            title_summary=f"[SPREAD_CORRIDOR] {opp_tm} ({-h_tight:+g}) + {tm} ({h_generous:+g})",
                            rule_verified=len(reasons_sl) == 0,
                            rule_compatibility_notes=[f"period={c_tight.period_scope}"],
                            divergence_or_rejection_reasons=reasons_sl,
                        )
                    )

        # G.4: Totals Corridor (`Over K_low + Under K_high` for `K_low < K_high`)
        if len(totals) >= 2:
            tot_items: List[Tuple[float, str, str, ParsedSportsContract]] = []
            for ct in totals:
                tt = _sports_total_tokens(ct)
                if tt is not None:
                    tot_items.append((tt[2], tt[0], tt[1], ct))
            tot_items.sort(key=lambda x: x[0])
            for idx in range(len(tot_items) - 1):
                k_lo, tok_over_lo, _tok_under_lo, c_lo = tot_items[idx]
                k_hi, _tok_over_hi, tok_under_hi, c_hi = tot_items[idx + 1]
                if c_lo.market.market_id == c_hi.market.market_id or (k_hi - k_lo) < 0.25:
                    continue
                reasons_tot = _check_sports_rule_compat([c_lo, c_hi])
                for r in reasons_tot:
                    _bump(r.split(":")[0])
                if not reasons_tot and len(by_fixture) > 25:
                    l1_tot = _quick_l1_buy_cost_sum([(tok_over_lo, c_lo.market), (tok_under_hi, c_hi.market)], books)
                    if l1_tot is None or l1_tot > 1.0 + DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT:
                        continue
                elif reasons_tot and len(results) > max_candidates * 2:
                    continue
                v_lo = 0.0 if c_lo.void_policy == "NEGRISK_NO" else 0.5
                v_hi = 0.0 if c_hi.void_policy == "NEGRISK_NO" else 0.5
                tot_states = [
                    _mk_state("SCORE_LOW", f"Total < {k_lo:g}", {tok_over_lo: 0.0, tok_under_hi: 1.0}, 0.42),
                    _mk_state("SCORE_CORRIDOR", f"Total in ({k_lo:g}, {k_hi:g}) (BOTH legs pay!)", {tok_over_lo: 1.0, tok_under_hi: 1.0}, 0.15),
                    _mk_state("SCORE_HIGH", f"Total > {k_hi:g}", {tok_over_lo: 1.0, tok_under_hi: 0.0}, 0.42),
                    _mk_state("VOID_GAME", "Match voided", {tok_over_lo: v_lo, tok_under_hi: v_hi}, 0.01, is_edge_or_void_state=True),
                ]
                if any(reasons_tot):
                    tot_states.append(_mk_state("PERIOD_MISMATCH_ZERO", "Subperiod/OT mismatch state (e.g. 1H Over misses & Full-Game Under misses)", {tok_over_lo: 0.0, tok_under_hi: 0.0}, 0.05, is_edge_or_void_state=True))
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "TOTALS_CORRIDOR", [c_lo.market.market_id, c_hi.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="TOTALS_OVER_UNDER_CORRIDOR",
                        relationship_type="TOTALS_MONOTONICITY",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_tot else "RULE_MISMATCH_REJECTED",
                        markets=[c_lo.market, c_hi.market],
                        legs=[
                            _build_leg_with_optional_inventory(tok_over_lo, c_lo.market.market_id, f"OVER[{k_lo:g}]", holdings),
                            _build_leg_with_optional_inventory(tok_under_hi, c_hi.market.market_id, f"UNDER[{k_hi:g}]", holdings),
                        ],
                        states=tot_states,
                        title_summary=f"[TOTALS_CORRIDOR] Over {k_lo:g} + Under {k_hi:g} ({c_lo.teams[0]} vs {c_lo.teams[1]})",
                        rule_verified=len(reasons_tot) == 0,
                        rule_compatibility_notes=[f"period={c_lo.period_scope}"],
                        divergence_or_rejection_reasons=reasons_tot,
                    )
                )

    # G.5: Single-Elimination Tournament Advancement (`Win Championship => Win Conference / Reach Final`)
    for (t_key, tm), t_items in tourn_groups.items():
        champs = [x for x in t_items if x.tournament_stage == "CHAMPION"]
        semis = [x for x in t_items if x.tournament_stage == "CONF_OR_REACH_FINAL"]
        for c_ch in champs:
            for c_sf in semis:
                if c_ch.market.market_id == c_sf.market.market_id:
                    continue
                reasons_tr: List[str] = []
                if c_ch.has_two_legged_or_double_elim_risk or c_sf.has_two_legged_or_double_elim_risk:
                    reasons_tr.append("DOUBLE_ELIMINATION_LOWER_BRACKET_PATH_BREAKS_IMPLICATION")
                if c_ch.void_policy == "50_50" and c_sf.void_policy == "NEGRISK_NO":
                    reasons_tr.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
                for r in reasons_tr:
                    _bump(r.split(":")[0])
                states_tr = StateSpaceBuilder.two_market_logical_states(
                    c_ch.market.yes_token_id, c_ch.market.no_token_id,
                    c_sf.market.yes_token_id, c_sf.market.no_token_id,
                    relation="A_IMPLIES_B" if not reasons_tr else "UNCONSTRAINED",
                    cancel_rule_a=c_ch.void_policy, cancel_rule_b=c_sf.void_policy,
                )
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("G", "TOURN_ADVANCE", [c_ch.market.market_id, c_sf.market.market_id]),
                        family="FAMILY_G_SPORTS_STRUCTURE",
                        sub_type="TOURNAMENT_CHAMPION_IMPLIES_CONF_FINAL",
                        relationship_type="A_IMPLIES_B",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not reasons_tr else "RULE_MISMATCH_REJECTED",
                        markets=[c_ch.market, c_sf.market],
                        legs=[
                            _build_leg_with_optional_inventory(c_ch.market.no_token_id, c_ch.market.market_id, f"NO[{tm} Champ]", holdings),
                            _build_leg_with_optional_inventory(c_sf.market.yes_token_id, c_sf.market.market_id, f"YES[{tm} Conf/Final]", holdings),
                        ],
                        states=states_tr,
                        title_summary=f"[TOURN_ADV] {tm} Win {t_key} => Reach Final / Win Conf",
                        rule_verified=len(reasons_tr) == 0,
                        rule_compatibility_notes=[f"tournament={t_key}"],
                        divergence_or_rejection_reasons=reasons_tr,
                    )
                )

    return _rank_and_cap_opportunities(results, max_candidates), rejection_counts


# ---------------------------------------------------------------------------
# 8. FAMILY H — Weather & Measurable-Event Structures (`D-001` & `D-006`)
# ---------------------------------------------------------------------------

# Official station / city -> ICAO resolver (strictly separating same-city stations like KLGA vs KJFK vs KNYC!)
_ICAO_DIRECT_RE = re.compile(
    r"(?:wunderground\.com/history/daily/[a-z/\-]+/(?P<wu_icao>[A-Z]{4})\b|\bstation\s+(?P<st_icao>K[A-Z]{3}|E[A-Z]{3}|L[A-Z]{3}|R[A-Z]{3}|VHHH|WSSS|YSSY|CYYZ|SBGR|SAEZ)\b|\(\s*(?P<paren_icao>[A-Z]{4})\s*\))",
    re.IGNORECASE,
)
# `BUG-LS-5`: Separate explicit airport/weather-station facilities (`station_explicit = True`) from bare city names
# (`station_explicit = False`), preventing bare `"Chicago"` (`KMDW` vs `KORD`) or `"Dallas"` (`KDAL` vs `KDFW`) from merging into `CLASS_B`!
_EXPLICIT_FACILITY_STATION_MAP: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("KLGA", re.compile(r"\blaguardia\b", re.I)),
    ("KJFK", re.compile(r"\b(?:jfk\s+airport|kennedy\s+(?:international\s+)?airport)\b", re.I)),
    ("KEWR", re.compile(r"\bnewark\s+(?:liberty\s+)?airport\b", re.I)),
    ("KNYC", re.compile(r"\bcentral\s+park\b", re.I)),
    ("KORD", re.compile(r"\bo['’]?hare\b", re.I)),
    ("KMDW", re.compile(r"\b(?:midway\s+(?:international\s+)?airport|chicago\s+midway)\b", re.I)),
    ("KDAL", re.compile(r"\b(?:dallas\s+love|love\s+field)\b", re.I)),
    ("KDFW", re.compile(r"\b(?:dfw\s+airport|dallas[/\-\s]+fort\s+worth\s+(?:international\s+)?airport)\b", re.I)),
    ("KMIA", re.compile(r"\bmiami\s+international\s+airport\b", re.I)),
    ("KLAX", re.compile(r"\blax\s+airport\b|\blos\s+angeles\s+international\s+airport\b", re.I)),
    ("KSEA", re.compile(r"\b(?:sea-tac|seatac|seattle-tacoma\s+(?:international\s+)?airport)\b", re.I)),
    ("KATL", re.compile(r"\bhartsfield(?:-jackson)?\b", re.I)),
    ("KBOS", re.compile(r"\blogan\s+(?:international\s+)?airport\b", re.I)),
    ("EGLC", re.compile(r"\blondon\s+city\s+airport\b", re.I)),
    ("EGLL", re.compile(r"\bheathrow\b", re.I)),
)
_BARE_CITY_FALLBACK_MAP: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("NYC_UNSPECIFIED_STATION", re.compile(r"\b(?:nyc|new\s+york\s+city)\b", re.I)),
    ("MIAMI_UNSPECIFIED_STATION", re.compile(r"\bmiami\b", re.I)),
    ("CHICAGO_UNSPECIFIED_STATION", re.compile(r"\bchicago\b", re.I)),
    ("LAX_UNSPECIFIED_STATION", re.compile(r"\blos\s+angeles\b", re.I)),
    ("SEATTLE_UNSPECIFIED_STATION", re.compile(r"\bseattle\b", re.I)),
    ("ATLANTA_UNSPECIFIED_STATION", re.compile(r"\batlanta\b", re.I)),
    ("DALLAS_UNSPECIFIED_STATION", re.compile(r"\b(?:dallas|dfw)\b", re.I)),
    ("BOSTON_UNSPECIFIED_STATION", re.compile(r"\bboston\b", re.I)),
    ("DENVER_UNSPECIFIED_STATION", re.compile(r"\bdenver\b", re.I)),
    ("PHOENIX_UNSPECIFIED_STATION", re.compile(r"\bphoenix\b", re.I)),
    ("LAS_VEGAS_UNSPECIFIED_STATION", re.compile(r"\blas\s+vegas\b", re.I)),
    ("SFO_UNSPECIFIED_STATION", re.compile(r"\bsan\s+francisco\b", re.I)),
    ("HOUSTON_UNSPECIFIED_STATION", re.compile(r"\bhouston\b", re.I)),
    ("LONDON_UNSPECIFIED_STATION", re.compile(r"\blondon\b", re.I)),
    ("PARIS_UNSPECIFIED_STATION", re.compile(r"\bparis\b", re.I)),
    ("TOKYO_UNSPECIFIED_STATION", re.compile(r"\btokyo\b", re.I)),
    ("SEOUL_UNSPECIFIED_STATION", re.compile(r"\bseoul\b", re.I)),
    ("HK_UNSPECIFIED_STATION", re.compile(r"\bhong\s+kong\b", re.I)),
    ("TORONTO_UNSPECIFIED_STATION", re.compile(r"\btoronto\b", re.I)),
    ("BUENOS_AIRES_UNSPECIFIED_STATION", re.compile(r"\bbuenos\s+aires\b", re.I)),
)

_MEASURABLE_AGENCY_MAP: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("USGS_EARTHQUAKE", re.compile(r"\b(?:usgs|earthquake\s+of\s+magnitude|magnitude\s+\d+(?:\.\d+)?\s+or\s+higher\s+earthquake)\b", re.I)),
    ("TSA_PASSENGERS", re.compile(r"\b(?:tsa\s+checkpoint|tsa\s+passengers|tsa\s+travel\s+numbers)\b", re.I)),
    ("NOAA_HURRICANE", re.compile(r"\b(?:named\s+storms?|category\s+[1-5]\s+hurricane|national\s+hurricane\s+center)\b", re.I)),
)

_TEMP_RANGE_RE = re.compile(
    r"(?P<lo>-?\d+(?:\.\d+)?)\s*(?:°\s*[fc])?\s*(?:to|[-–—]|and)\s*(?P<hi>-?\d+(?:\.\d+)?)\s*°?\s*(?P<unit>[fc])\b",
    re.IGNORECASE,
)
_TEMP_THRESHOLD_RE = re.compile(
    r"(?:(?P<pre>at\s+least|at\s+most|above|over|below|under|>=|<=|>|<)\s*)?"
    r"(?P<val>-?\d+(?:\.\d+)?)\s*°\s*(?P<unit>[fc])\b"
    r"(?:\s*(?P<post>or\s+(?:higher|above|more|lower|below|less)))?",
    re.IGNORECASE,
)
_PRECIP_THRESHOLD_RE = re.compile(
    r"(?P<pre>at\s+least|at\s+most|above|over|below|under|more\s+than|less\s+than|>=|<=|>|<)\s*"
    r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>inches|inch|in\.|mm|cm)\b",
    re.IGNORECASE,
)
_ON_DATE_RE = re.compile(
    r"\bon\s+(?P<m>[a-z]+)\s+(?P<d>\d{1,2})(?:,?\s*(?P<y>20\d{2}))?\b|\bon\s+(?P<iso>20\d{2}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)

# `D-006`: Unverified integer-METAR rounding cushion (`±0.55°C` == `±0.99°F`)
D006_UNVERIFIED_SENSOR_CUSHION_C: float = 0.55
D006_UNVERIFIED_SENSOR_CUSHION_F: float = 0.99


@dataclass(frozen=True)
class MetarObservationSnapshot:
    """
    External station observation input (strictly verification-only per Section 6 Family H & `D-006`):
      - `has_dollar_maintenance_flag`: True when raw METAR ends with or contains `$` (ASOS hardware maintenance needed).
      - `has_exact_tenths_t_group`: True ONLY when verified `RMK T0...` tenths group is present (`±0.05°C` precision);
        otherwise `±0.55°C` (`±0.99°F`) rounding cushion is mandatory!
      - `is_speci_or_corrected`: True on unverified `SPECI` / `COR` transient reports (blocked by `D-006`).
    """
    station_icao: str
    local_date_iso: str
    observed_high: Optional[float] = None
    observed_low: Optional[float] = None
    unit: str = "F"  # "F" | "C"
    raw_metar: str = ""
    has_dollar_maintenance_flag: bool = False
    has_exact_tenths_t_group: bool = False
    is_speci_or_corrected: bool = False
    day_window_closed: bool = False


@dataclass(frozen=True)
class ParsedWeatherContract:
    market: CanonicalBinaryMarket
    station_or_agency: str
    station_explicit: bool
    local_date_iso: str
    metric_kind: str   # "TEMP_HIGH" | "TEMP_LOW" | "PRECIPITATION" | "MEASURABLE"
    unit: str          # "F" | "C" | "IN" | "MM" | "CM"
    comparator: str    # "RANGE" | "GTE" | "GT" | "LTE" | "LT" | "EXACT"
    low_val: float
    high_val: Optional[float]
    is_integer_unit_oracle: bool


def _parse_local_weather_date(m: CanonicalBinaryMarket) -> Optional[str]:
    blob = f"{m.question} {m.event_title}"
    md = _ON_DATE_RE.search(blob)
    if md:
        if md.group("iso"):
            return md.group("iso")
        mon_s = (md.group("m") or "").lower().rstrip(".")
        if mon_s in _MONTH_NUMS:
            mon = _MONTH_NUMS[mon_s]
            day = int(md.group("d"))
            yr = int(md.group("y")) if md.group("y") else (
                datetime.fromtimestamp(m.end_ts, tz=timezone.utc).year if m.end_ts else 2026
            )
            try:
                return date(yr, mon, day).isoformat()
            except ValueError:
                return None
    if m.end_ts:
        _, tz_iana = extract_timezone_signature(m)
        return datetime.fromtimestamp(m.end_ts, tz=resolve_tz(tz_iana)).date().isoformat()
    return None


def parse_weather_measurable_contract(m: CanonicalBinaryMarket) -> Optional[ParsedWeatherContract]:
    """
    Parses weather (temperature high/low, precipitation/snowfall) and official measurable brackets,
    strictly rejecting `D-001` disputed `KMIA` positions (`6707503`, `6707502`).
    """
    if not m.is_standard_yes_no or m.closed_or_archived or not m.yes_token_id or not m.no_token_id:
        return None
    if m.is_placeholder_outcome or m.is_other_outcome or m.is_d001_disputed_quarantined():
        return None

    q_ev = f"{m.event_title} {m.question} {m.group_item_title}"
    q_ev_l = q_ev.lower()
    if re.search(r"\b(?:not|never|fail(?:s)?\s+to|won't|will\s+not|cannot|can't)\b", f"{m.question} {m.group_item_title}", re.IGNORECASE):
        return None
    src_desc = f"{m.resolution_source} {m.description}"

    # Identify station ICAO or measurable agency
    station = ""
    station_explicit = False
    m_icao = _ICAO_DIRECT_RE.search(f"{src_desc} {q_ev}")
    if m_icao:
        station = (m_icao.group("wu_icao") or m_icao.group("st_icao") or m_icao.group("paren_icao") or "").upper()
        station_explicit = True
    if not station:
        for st_code, pat in _EXPLICIT_FACILITY_STATION_MAP:
            if pat.search(f"{q_ev} {src_desc[:320]}"):
                station = st_code
                station_explicit = True
                break
    if not station:
        for st_code, pat in _BARE_CITY_FALLBACK_MAP:
            if pat.search(f"{q_ev} {src_desc[:240]}"):
                station = st_code
                station_explicit = False
                break
    if not station:
        for ag_code, pat in _MEASURABLE_AGENCY_MAP:
            if pat.search(q_ev):
                station = ag_code
                station_explicit = True
                break
    if not station:
        return None

    # Metric kind
    if any(k in q_ev_l for k in ("highest temperature", "high temperature", "daily high", "max temperature")):
        metric_kind = "TEMP_HIGH"
    elif any(k in q_ev_l for k in ("lowest temperature", "low temperature", "daily low", "min temperature")):
        metric_kind = "TEMP_LOW"
    elif any(k in q_ev_l for k in ("precipitation", "rainfall", "snowfall", "inches of rain", "inches of snow")):
        metric_kind = "PRECIPITATION"
    elif station in {"USGS_EARTHQUAKE", "TSA_PASSENGERS", "NOAA_HURRICANE"}:
        metric_kind = "MEASURABLE"
    elif "°f" in q_ev_l or "°c" in q_ev_l:
        metric_kind = "TEMP_HIGH"
    else:
        return None

    local_dt = _parse_local_weather_date(m)
    if not local_dt:
        return None

    desc_l = src_desc.lower()
    is_int_oracle = bool(
        "wunderground" in desc_l
        or "whole degree" in desc_l
        or "nearest integer" in desc_l
        or metric_kind in {"TEMP_HIGH", "TEMP_LOW"}
    ) and ("tenths of a degree" not in desc_l)

    # Parse temperature range / threshold / exact bracket
    for probe in (m.group_item_title.strip(), m.question.strip()):
        if not probe:
            continue
        mr = _TEMP_RANGE_RE.search(probe)
        if mr and metric_kind in {"TEMP_HIGH", "TEMP_LOW"}:
            lo_v, hi_v = float(mr.group("lo")), float(mr.group("hi"))
            unit = mr.group("unit").upper()
            if hi_v >= lo_v:
                return ParsedWeatherContract(
                    market=m,
                    station_or_agency=station,
                    station_explicit=station_explicit,
                    local_date_iso=local_dt,
                    metric_kind=metric_kind,
                    unit=unit,
                    comparator="RANGE",
                    low_val=lo_v,
                    high_val=hi_v,
                    is_integer_unit_oracle=is_int_oracle,
                )
        mt = _TEMP_THRESHOLD_RE.search(probe)
        if mt and metric_kind in {"TEMP_HIGH", "TEMP_LOW"}:
            v = float(mt.group("val"))
            unit = mt.group("unit").upper()
            pre = (mt.group("pre") or "").strip().lower()
            post = (mt.group("post") or "").strip().lower()
            if "or higher" in post or "or above" in post or "or more" in post or pre in {"at least", ">="}:
                comp = "GTE"
            elif pre in {"above", "over", ">"}:
                comp = "GTE" if ("or higher" in desc_l or ">=" in desc_l) else "GT"
            elif "or lower" in post or "or below" in post or "or less" in post or pre in {"at most", "<="}:
                comp = "LTE"
            elif pre in {"below", "under", "<"}:
                comp = "LTE" if ("or lower" in desc_l or "<=" in desc_l) else "LT"
            else:
                # Exact single-degree Wunderground bracket (e.g. `"be 72°F on Nov 11?"`)
                comp = "RANGE"
                return ParsedWeatherContract(
                    market=m,
                    station_or_agency=station,
                    station_explicit=station_explicit,
                    local_date_iso=local_dt,
                    metric_kind=metric_kind,
                    unit=unit,
                    comparator=comp,
                    low_val=v,
                    high_val=v,
                    is_integer_unit_oracle=is_int_oracle,
                )
            return ParsedWeatherContract(
                market=m,
                station_or_agency=station,
                station_explicit=station_explicit,
                local_date_iso=local_dt,
                metric_kind=metric_kind,
                unit=unit,
                comparator=comp,
                low_val=v,
                high_val=None,
                is_integer_unit_oracle=is_int_oracle,
            )

        mp = _PRECIP_THRESHOLD_RE.search(probe)
        if mp and metric_kind == "PRECIPITATION":
            v = float(mp.group("val"))
            u_raw = mp.group("unit").lower().rstrip(".")
            unit = "IN" if u_raw.startswith("in") else u_raw.upper()
            pre = mp.group("pre").strip().lower()
            comp = "GTE" if pre in {"at least", ">="} else ("GT" if pre in {"above", "over", "more than", ">"} else ("LTE" if pre in {"at most", "<="} else "LT"))
            return ParsedWeatherContract(
                market=m,
                station_or_agency=station,
                station_explicit=station_explicit,
                local_date_iso=local_dt,
                metric_kind=metric_kind,
                unit=unit,
                comparator=comp,
                low_val=v,
                high_val=None,
                is_integer_unit_oracle=False,
            )

    return None


def _eval_weather_truth(wc: ParsedWeatherContract, x: float) -> bool:
    if wc.comparator == "GTE":
        return x >= wc.low_val
    if wc.comparator == "GT":
        return x > wc.low_val
    if wc.comparator == "LTE":
        return x <= wc.low_val
    if wc.comparator == "LT":
        return x < wc.low_val
    if wc.comparator == "RANGE" and wc.high_val is not None:
        return wc.low_val <= x <= wc.high_val
    return False


def _build_weather_sample_states(contracts: Sequence[ParsedWeatherContract]) -> List[StateSpec]:
    """
    Constructs exact sample points across all `contracts` (respecting integer-degree Wunderground grids
    vs continuous precipitation grids so `75-76°F` + `77°F+` has zero false `76.5°F` phantom state on integer oracles,
    while `75-76°F` + `78°F+` catches the `77°F` missing-integer gap!).
    """
    all_int = all(c.is_integer_unit_oracle for c in contracts)
    knots = sorted(
        {float(c.low_val) for c in contracts}
        | {float(c.high_val) for c in contracts if c.high_val is not None}
    )
    pts: List[float] = []
    if knots:
        if all_int and (knots[-1] - knots[0]) <= 60.0:
            lo_i = int(math.floor(knots[0])) - 1
            hi_i = int(math.ceil(knots[-1])) + 1
            pts = [float(v) for v in range(lo_i, hi_i + 1)]
        else:
            pts.append(knots[0] - 1.0)
            for idx, kv in enumerate(knots):
                pts.append(kv)
                if idx + 1 < len(knots) and knots[idx + 1] > kv:
                    pts.append(0.5 * (kv + knots[idx + 1]))
            pts.append(knots[-1] + 1.0)

    states: List[StateSpec] = []
    p_each = 0.99 / max(1, len(pts))
    for v in pts:
        pay: Dict[str, float] = {}
        for c in contracts:
            ok = _eval_weather_truth(c, v)
            pay[c.market.yes_token_id] = 1.0 if ok else 0.0
            pay[c.market.no_token_id] = 0.0 if ok else 1.0
        states.append(_mk_state(f"WX_{v:g}", f"Official={v:g}{contracts[0].unit}", pay, p_each))

    v_pay: Dict[str, float] = {}
    for c in contracts:
        if c.market.cancel_rule_tag == "NEGRISK_NO":
            v_pay[c.market.yes_token_id] = 0.0
            v_pay[c.market.no_token_id] = 1.0
        else:
            v_pay[c.market.yes_token_id] = 0.5
            v_pay[c.market.no_token_id] = 0.5
    states.append(_mk_state("WX_STATION_OUTAGE_VOID", "Official station outage / void", v_pay, 0.01, is_edge_or_void_state=True))
    return states


def detect_family_h_weather_measurable(
    markets: Sequence[CanonicalBinaryMarket],
    books: Mapping[str, InstrumentOrderBook],
    *,
    verifier: Optional[UniversalArbVerifier] = None,
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
    observations: Optional[Sequence[MetarObservationSnapshot]] = None,
    max_candidates: int = 350,
) -> Tuple[List[DetectedOpportunity], Dict[str, int]]:
    """
    Family H — Weather & Measurable-Event Structures:
      - Strictly enforces `D-001` (`6707503`, `6707502`, and `umaResolutionStatus=='disputed'` never touched!).
      - Verifies exact station ICAO, local calendar date, unit (`°F` vs `°C`), and authority (`Wunderground` vs `NWS`).
      - Detects contractual multi-leg structures (`CLASS_B`):
          * Threshold dominance (`>= T_hi => >= T_lo`, `<= T_lo => <= T_hi`),
          * Range + Tail covers (`[T1, T2]` + `>= T2+1` <=> `>= T1` on integer Wunderground grids),
          * Non-NegRisk / cross-event disjoint bracket `NO_i + NO_j` mutual exclusions,
          * Same-station/date/unit physical `Daily Low <= Daily High` dominance (`YES(High >= K1) + YES(Low <= K2)` for `K1 <= K2`).
      - Evaluates external `MetarObservationSnapshot` strictly under `D-006`:
          * ASOS `$` maintenance indicator -> `CLASS_D` hard block (`D006_ASOS_DOLLAR_MAINTENANCE_BLOCK`),
          * `SPECI` / `COR` -> `CLASS_D` hard block,
          * Missing `T`-group tenths -> mandatory `±0.55°C` (`±0.99°F`) rounding cushion,
          * Valid sensor pruning NEVER exceeds `CLASS_C` (`is_statistical_or_cross_oracle_only=True`) because external
            METAR is not a contractual substitute for official Wunderground post-window settlement!
    """
    ver = verifier or UniversalArbVerifier()
    results: List[DetectedOpportunity] = []
    rejection_counts: Dict[str, int] = {}

    def _bump(r: str) -> None:
        rejection_counts[r] = rejection_counts.get(r, 0) + 1

    for m in markets:
        if m.is_d001_disputed_quarantined():
            _bump("D001_DISPUTED_KMIA_QUARANTINED")

    parsed_wx: List[ParsedWeatherContract] = []
    for m in markets:
        pw = parse_weather_measurable_contract(m)
        if pw is not None:
            parsed_wx.append(pw)

    # Group by `(local_date_iso)` + city/station family so cross-station (`KLGA` vs `KJFK`) & unit (`°F` vs `°C`) mismatches are ALSO caught!
    by_station_date_metric: Dict[Tuple[str, str, str], List[ParsedWeatherContract]] = {}
    by_station_date_all: Dict[Tuple[str, str], List[ParsedWeatherContract]] = {}
    by_date_city_probe: Dict[str, List[ParsedWeatherContract]] = {}

    _CITY_FAMILY_GROUPS: Tuple[Tuple[str, FrozenSet[str]], ...] = (
        ("NYC", frozenset({"KLGA", "KJFK", "KEWR", "KNYC", "NYC_UNSPECIFIED_STATION"})),
        ("LONDON", frozenset({"EGLC", "EGLL", "LONDON_UNSPECIFIED_STATION"})),
        ("CHICAGO", frozenset({"KORD", "KMDW", "CHICAGO_UNSPECIFIED_STATION"})),
        ("DALLAS", frozenset({"KDAL", "KDFW", "DALLAS_UNSPECIFIED_STATION"})),
        ("MIAMI", frozenset({"KMIA", "MIAMI_UNSPECIFIED_STATION"})),
        ("LAX", frozenset({"KLAX", "LAX_UNSPECIFIED_STATION"})),
        ("SEATTLE", frozenset({"KSEA", "SEATTLE_UNSPECIFIED_STATION"})),
    )
    for pw in parsed_wx:
        by_station_date_metric.setdefault((pw.station_or_agency, pw.local_date_iso, pw.metric_kind), []).append(pw)
        by_station_date_all.setdefault((pw.station_or_agency, pw.local_date_iso), []).append(pw)
        city_family = pw.station_or_agency
        for cf_name, cf_set in _CITY_FAMILY_GROUPS:
            if pw.station_or_agency in cf_set:
                city_family = cf_name
                break
        by_date_city_probe.setdefault(f"{city_family}::{pw.local_date_iso}::{pw.metric_kind}", []).append(pw)

    def _wx_pair_reasons(a: ParsedWeatherContract, b: ParsedWeatherContract, allow_high_low: bool = False) -> List[str]:
        rs: List[str] = []
        if not a.station_explicit or not b.station_explicit:
            rs.append(f"WEATHER_STATION_ICAO_UNSPECIFIED:{a.station_or_agency}_vs_{b.station_or_agency}")
        elif a.station_or_agency != b.station_or_agency:
            rs.append(f"WEATHER_STATION_ICAO_MISMATCH:{a.station_or_agency}_vs_{b.station_or_agency}")
        if a.local_date_iso != b.local_date_iso:
            rs.append(f"WEATHER_LOCAL_DATE_MISMATCH:{a.local_date_iso}_vs_{b.local_date_iso}")
        if a.unit != b.unit:
            rs.append(f"WEATHER_UNIT_MISMATCH:{a.unit}_vs_{b.unit}")
        if not allow_high_low and a.metric_kind != b.metric_kind:
            rs.append(f"WEATHER_METRIC_MISMATCH:{a.metric_kind}_vs_{b.metric_kind}")
        auth_a = extract_resolution_authority_signature(a.market)
        auth_b = extract_resolution_authority_signature(b.market)
        if auth_a != "UNSPECIFIED_AUTHORITY" and auth_b != "UNSPECIFIED_AUTHORITY" and auth_a != auth_b:
            rs.append(f"WEATHER_AUTHORITY_MISMATCH:{auth_a}_vs_{auth_b}")
        return rs

    # H.1: Catch Cross-Station (`KLGA` vs `KJFK`) or Unit (`°F` vs `°C`) Mismatch Traps on Same City/Date!
    for _ckey, cgrp in by_date_city_probe.items():
        stations_seen = {x.station_or_agency for x in cgrp}
        units_seen = {x.unit for x in cgrp}
        if len(stations_seen) > 1 or len(units_seen) > 1:
            # Emit explicit `CLASS_D` proof for mismatched pairs sharing overlapping numeric strikes
            for i in range(min(len(cgrp), 6)):
                for j in range(i + 1, min(len(cgrp), 8)):
                    a, b = cgrp[i], cgrp[j]
                    if a.station_or_agency == b.station_or_agency and a.unit == b.unit:
                        continue
                    rs = _wx_pair_reasons(a, b)
                    for r in rs:
                        _bump(r.split(":")[0])
                    states_bad = StateSpaceBuilder.two_market_logical_states(
                        a.market.yes_token_id, a.market.no_token_id,
                        b.market.yes_token_id, b.market.no_token_id,
                        relation="UNCONSTRAINED",
                        oracle_mismatch=True,
                    )
                    results.append(
                        _finalize_detected_opportunity(
                            ver, books, holdings,
                            candidate_id=_make_candidate_id("H", "WX_RULE_MISMATCH", [a.market.market_id, b.market.market_id]),
                            family="FAMILY_H_WEATHER_MEASURABLE",
                            sub_type="STATION_OR_UNIT_MISMATCH_TRAP",
                            relationship_type="INVALID_CROSS_STATION_OR_UNIT",
                            edge_proof_status="RULE_MISMATCH_REJECTED",
                            markets=[a.market, b.market],
                            legs=[
                                _build_leg_with_optional_inventory(a.market.no_token_id, a.market.market_id, f"NO[{a.station_or_agency} {a.low_val:g}{a.unit}]", holdings),
                                _build_leg_with_optional_inventory(b.market.yes_token_id, b.market.market_id, f"YES[{b.station_or_agency} {b.low_val:g}{b.unit}]", holdings),
                            ],
                            states=states_bad,
                            title_summary=f"[WX_MISMATCH] {a.station_or_agency} ({a.unit}) vs {b.station_or_agency} ({b.unit}) on {a.local_date_iso}",
                            rule_verified=False,
                            divergence_or_rejection_reasons=rs,
                        )
                    )

    # H.2: Same-Station / Same-Date / Same-Metric Contractual Structures
    for (st, dt_iso, mkind), grp in by_station_date_metric.items():
        if len(grp) < 2:
            continue
        up_wx = sorted([c for c in grp if c.comparator in {"GTE", "GT"}], key=lambda x: (x.low_val, 1 if x.comparator == "GT" else 0))
        dn_wx = sorted([c for c in grp if c.comparator in {"LTE", "LT"}], key=lambda x: (x.low_val, 0 if x.comparator == "LT" else 1))
        rg_wx = sorted([c for c in grp if c.comparator == "RANGE" and c.high_val is not None], key=lambda x: x.low_val)

        # H.2a: Upward threshold dominance (`>= T_hi => >= T_lo` -> `NO_hi + YES_lo`)
        for idx in range(len(up_wx) - 1):
            c_lo, c_hi = up_wx[idx], up_wx[idx + 1]
            if c_lo.market.market_id == c_hi.market.market_id or c_lo.unit != c_hi.unit:
                continue
            if c_hi.low_val == c_lo.low_val and not (c_hi.comparator == "GT" and c_lo.comparator == "GTE"):
                continue
            rs = _wx_pair_reasons(c_hi, c_lo)
            if c_hi.market.cancel_rule_tag == "50_50" and c_lo.market.cancel_rule_tag == "NEGRISK_NO":
                rs.append("ASYMMETRIC_VOID_SETTLEMENT_5050_VS_NEGRISK_NO")
            for r in rs:
                _bump(r.split(":")[0])
            states = _build_weather_sample_states([c_hi, c_lo]) if not rs else StateSpaceBuilder.two_market_logical_states(
                c_hi.market.yes_token_id, c_hi.market.no_token_id,
                c_lo.market.yes_token_id, c_lo.market.no_token_id,
                relation="UNCONSTRAINED", oracle_mismatch=True,
            )
            results.append(
                _finalize_detected_opportunity(
                    ver, books, holdings,
                    candidate_id=_make_candidate_id("H", "WX_UP_DOM", [c_hi.market.market_id, c_lo.market.market_id]),
                    family="FAMILY_H_WEATHER_MEASURABLE",
                    sub_type="WEATHER_THRESHOLD_DOMINANCE",
                    relationship_type="A_IMPLIES_B",
                    edge_proof_status="VERIFIED_MATHEMATICAL" if not rs else "RULE_MISMATCH_REJECTED",
                    markets=[c_hi.market, c_lo.market],
                    legs=[
                        _build_leg_with_optional_inventory(c_hi.market.no_token_id, c_hi.market.market_id, f"NO[{st}>={c_hi.low_val:g}{c_hi.unit}]", holdings),
                        _build_leg_with_optional_inventory(c_lo.market.yes_token_id, c_lo.market.market_id, f"YES[{st}>={c_lo.low_val:g}{c_lo.unit}]", holdings),
                    ],
                    states=states,
                    title_summary=f"[WX_DOM] {st} {dt_iso}: >={c_hi.low_val:g}{c_hi.unit} => >={c_lo.low_val:g}{c_lo.unit}",
                    rule_verified=len(rs) == 0,
                    rule_compatibility_notes=[f"station={st}", f"date={dt_iso}", f"unit={c_hi.unit}"],
                    divergence_or_rejection_reasons=rs,
                )
            )

        # H.2b: Non-NegRisk / Cross-Event Disjoint Bracket `NO_i + NO_j` Pairs
        for i in range(min(len(rg_wx), 8)):
            for j in range(i + 1, min(len(rg_wx), 8)):
                ca, cb = rg_wx[i], rg_wx[j]
                assert ca.high_val is not None and cb.high_val is not None
                if ca.market.market_id == cb.market.market_id or ca.unit != cb.unit:
                    continue
                if ca.market.event_id == cb.market.event_id and ca.market.neg_risk and cb.market.neg_risk:
                    continue  # Intra-event NegRisk bracket slate owned by Family C
                if ca.high_val >= cb.low_val:
                    continue  # Overlapping brackets are NOT mutually exclusive!
                rs = _wx_pair_reasons(ca, cb)
                for r in rs:
                    _bump(r.split(":")[0])
                states = _build_weather_sample_states([ca, cb]) if not rs else StateSpaceBuilder.two_market_logical_states(
                    ca.market.yes_token_id, ca.market.no_token_id,
                    cb.market.yes_token_id, cb.market.no_token_id,
                    relation="UNCONSTRAINED", oracle_mismatch=True,
                )
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("H", "WX_DISJOINT_BRACKETS", [ca.market.market_id, cb.market.market_id]),
                        family="FAMILY_H_WEATHER_MEASURABLE",
                        sub_type="WEATHER_DISJOINT_BRACKET_NO_PAIR",
                        relationship_type="MUTUAL_EXCLUSION",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not rs else "RULE_MISMATCH_REJECTED",
                        markets=[ca.market, cb.market],
                        legs=[
                            _build_leg_with_optional_inventory(ca.market.no_token_id, ca.market.market_id, f"NO[{ca.low_val:g}-{ca.high_val:g}{ca.unit}]", holdings),
                            _build_leg_with_optional_inventory(cb.market.no_token_id, cb.market.market_id, f"NO[{cb.low_val:g}-{cb.high_val:g}{cb.unit}]", holdings),
                        ],
                        states=states,
                        title_summary=f"[WX_DISJOINT] {st} {dt_iso}: NO({ca.low_val:g}-{ca.high_val:g}{ca.unit}) + NO({cb.low_val:g}-{cb.high_val:g}{cb.unit})",
                        rule_verified=len(rs) == 0,
                        rule_compatibility_notes=[f"station={st}", f"date={dt_iso}", f"unit={ca.unit}"],
                        divergence_or_rejection_reasons=rs,
                    )
                )

        # H.2c: Range `[T1, T2]` + Tail `>= T2+1` (or `>= T2`) vs Base `>= T1`
        if rg_wx and len(up_wx) >= 2:
            up_map = {u.low_val: u for u in up_wx}
            for crg in rg_wx:
                assert crg.high_val is not None
                cbase = up_map.get(crg.low_val)
                next_k = (crg.high_val + 1.0) if crg.is_integer_unit_oracle else crg.high_val
                ctail = up_map.get(next_k) or up_map.get(crg.high_val)
                if cbase is None or ctail is None or len({crg.market.market_id, cbase.market.market_id, ctail.market.market_id}) < 3:
                    continue
                rs = list(dict.fromkeys(_wx_pair_reasons(crg, cbase) + _wx_pair_reasons(crg, ctail)))
                states_cov = _build_weather_sample_states([crg, ctail, cbase])
                cov_tokens = (crg.market.yes_token_id, ctail.market.yes_token_id, cbase.market.no_token_id)
                for st_spec in states_cov:
                    if not st_spec.is_edge_or_void_state:
                        if sum(st_spec.instrument_payouts.get(tid, 0.0) for tid in cov_tokens) < 1.0 - 1e-9:
                            rs.append(f"WEATHER_COVER_STATE_GAP:{st_spec.state_id}")
                            break
                for r in rs:
                    _bump(r.split(":")[0])
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("H", "WX_RANGE_COVER", [crg.market.market_id, ctail.market.market_id, cbase.market.market_id]),
                        family="FAMILY_H_WEATHER_MEASURABLE",
                        sub_type="WEATHER_RANGE_TAIL_COVER",
                        relationship_type="PARTITION_EQUIVALENCE",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not rs else "RULE_MISMATCH_REJECTED",
                        markets=[crg.market, ctail.market, cbase.market],
                        legs=[
                            _build_leg_with_optional_inventory(crg.market.yes_token_id, crg.market.market_id, f"YES[{crg.low_val:g}-{crg.high_val:g}]", holdings),
                            _build_leg_with_optional_inventory(ctail.market.yes_token_id, ctail.market.market_id, f"YES[>={ctail.low_val:g}]", holdings),
                            _build_leg_with_optional_inventory(cbase.market.no_token_id, cbase.market.market_id, f"NO[>={cbase.low_val:g}]", holdings),
                        ],
                        states=states_cov,
                        title_summary=f"[WX_COVER] {st} {dt_iso}: [{crg.low_val:g}-{crg.high_val:g}] + >={ctail.low_val:g} vs >={cbase.low_val:g}",
                        rule_verified=len(rs) == 0,
                        rule_compatibility_notes=[f"station={st}", f"integer_grid={crg.is_integer_unit_oracle}"],
                        divergence_or_rejection_reasons=rs,
                    )
                )

    # H.3: Physical `Daily Low <= Daily High` Dominance on Same `(station, local_date, unit)`:
    #   Since `T_low <= T_high` identically on the same official daily summary:
    #     - `YES(High >= K1) + YES(Low <= K2)` covers EVERY physical state `(T_low <= T_high)` whenever `K1 <= K2`!
    for (st, dt_iso), all_st_grp in by_station_date_all.items():
        highs_gte = [c for c in all_st_grp if c.metric_kind == "TEMP_HIGH" and c.comparator == "GTE"]
        lows_lte = [c for c in all_st_grp if c.metric_kind == "TEMP_LOW" and c.comparator == "LTE"]
        for ch in highs_gte:
            for cl in lows_lte:
                if ch.unit != cl.unit or ch.low_val > cl.low_val:
                    continue
                rs = _wx_pair_reasons(ch, cl, allow_high_low=True)
                v_h = 0.0 if ch.market.cancel_rule_tag == "NEGRISK_NO" else 0.5
                v_l = 0.0 if cl.market.cancel_rule_tag == "NEGRISK_NO" else 0.5
                if v_h + v_l < 1.0 - 1e-9:
                    rs.append("VOID_SETTLEMENT_SUM_BELOW_ONE")
                for r in rs:
                    _bump(r.split(":")[0])
                hl_states = [
                    _mk_state("COLD_DAY", f"High < {ch.low_val:g} => Low <= High < {ch.low_val:g} <= {cl.low_val:g}", {ch.market.yes_token_id: 0.0, cl.market.yes_token_id: 1.0}, 0.33),
                    _mk_state("DIURNAL_SPREAD_JACKPOT", f"Low <= {cl.low_val:g} AND High >= {ch.low_val:g} (BOTH pay!)", {ch.market.yes_token_id: 1.0, cl.market.yes_token_id: 1.0}, 0.33),
                    _mk_state("WARM_NIGHT", f"Low > {cl.low_val:g} => High >= Low > {cl.low_val:g} >= {ch.low_val:g}", {ch.market.yes_token_id: 1.0, cl.market.yes_token_id: 0.0}, 0.33),
                    _mk_state("VOID_OUTAGE", "Station outage void", {ch.market.yes_token_id: v_h, cl.market.yes_token_id: v_l}, 0.01, is_edge_or_void_state=True),
                ]
                results.append(
                    _finalize_detected_opportunity(
                        ver, books, holdings,
                        candidate_id=_make_candidate_id("H", "WX_HIGH_GTE_LOW_BOX", [ch.market.market_id, cl.market.market_id]),
                        family="FAMILY_H_WEATHER_MEASURABLE",
                        sub_type="DAILY_HIGH_GTE_DAILY_LOW_PHYSICAL_COVER",
                        relationship_type="PHYSICAL_SUPERSET_COVER",
                        edge_proof_status="VERIFIED_MATHEMATICAL" if not rs else "RULE_MISMATCH_REJECTED",
                        markets=[ch.market, cl.market],
                        legs=[
                            _build_leg_with_optional_inventory(ch.market.yes_token_id, ch.market.market_id, f"YES[High>={ch.low_val:g}{ch.unit}]", holdings),
                            _build_leg_with_optional_inventory(cl.market.yes_token_id, cl.market.market_id, f"YES[Low<={cl.low_val:g}{cl.unit}]", holdings),
                        ],
                        states=hl_states,
                        title_summary=f"[WX_HIGH_LOW] {st} {dt_iso}: High>={ch.low_val:g}{ch.unit} + Low<={cl.low_val:g}{cl.unit}",
                        rule_verified=len(rs) == 0,
                        rule_compatibility_notes=[f"station={st}", f"date={dt_iso}", "T_low <= T_high physical invariant"],
                        divergence_or_rejection_reasons=rs,
                    )
                )

    # H.4: Optional `D-006` External METAR Verification Pruning (strictly capped at `CLASS_C`, NEVER `CLASS_A/B`!)
    if observations:
        obs_by_st_dt: Dict[Tuple[str, str], MetarObservationSnapshot] = {
            (ob.station_icao.upper(), ob.local_date_iso): ob for ob in observations
        }
        for pw in parsed_wx:
            ob = obs_by_st_dt.get((pw.station_or_agency.upper(), pw.local_date_iso))
            if ob is None or ob.unit.upper() != pw.unit.upper() or pw.metric_kind != "TEMP_HIGH" or ob.observed_high is None:
                continue

            d006_reasons: List[str] = []
            has_raw_dollar = "$" in str(ob.raw_metar or "").split() or str(ob.raw_metar or "").strip().endswith("$")
            if ob.has_dollar_maintenance_flag or has_raw_dollar:
                d006_reasons.append("D006_ASOS_DOLLAR_MAINTENANCE_BLOCK")
            if ob.is_speci_or_corrected:
                d006_reasons.append("D006_SPECI_OR_CORRECTED_REPORT_EXCLUDED")
            if not pw.station_explicit:
                d006_reasons.append("WEATHER_STATION_ICAO_UNSPECIFIED")

            cushion = (
                (0.05 if pw.unit == "C" else 0.09)
                if ob.has_exact_tenths_t_group
                else (D006_UNVERIFIED_SENSOR_CUSHION_C if pw.unit == "C" else D006_UNVERIFIED_SENSOR_CUSHION_F)
            )
            # Conservative lower bound on already-reached daily high = `observed_high - cushion`
            conservative_min_high = float(ob.observed_high) - cushion

            # Check if an upper bound (`LTE`, `LT`, or `RANGE` with `high_val`) is already exceeded by `conservative_min_high`!
            upper_cap = pw.high_val if pw.comparator == "RANGE" else (pw.low_val if pw.comparator in {"LTE", "LT"} else None)
            if upper_cap is None:
                continue
            # Under Wunderground integer rounding, e.g., `76°F` bracket caps out at `76.49°F` before rounding to `77°F`
            effective_cap = (upper_cap + 0.499) if pw.is_integer_unit_oracle else upper_cap

            if conservative_min_high <= effective_cap and not d006_reasons:
                # Check if raw `observed_high` WITHOUT cushion would have falsely triggered -> record `D006` cushion block!
                if float(ob.observed_high) > effective_cap:
                    d006_reasons.append(f"D006_ROUNDING_CUSHION_BLOCK:obs={ob.observed_high:g}_cushion={cushion:g}_cap={effective_cap:g}")
                else:
                    continue

            for r in d006_reasons:
                _bump(r.split(":")[0])

            # Even when `D-006` passes cleanly, external METAR != contractual Wunderground post-day table:
            # include `0.015` probability post-audit revision state so `min_w < 0` and set `is_statistical_or_cross_oracle_only=True` (`CLASS_C` max)!
            states_metar = [
                _mk_state("METAR_CONFIRMED_NO", f"Official high >= {conservative_min_high:.2f}{pw.unit} > {upper_cap:g}{pw.unit}", {pw.market.no_token_id: 1.0, pw.market.yes_token_id: 0.0}, 0.985),
                _mk_state("WUNDERGROUND_CLIMO_REVISION_RISK", "Official Wunderground daily summary revises sensor spike", {pw.market.no_token_id: 0.0, pw.market.yes_token_id: 1.0}, 0.015, is_edge_or_void_state=True),
            ]
            rule_ok = len(d006_reasons) == 0
            results.append(
                _finalize_detected_opportunity(
                    ver, books, holdings,
                    candidate_id=_make_candidate_id("H", "WX_METAR_PRUNE", [pw.market.market_id]),
                    family="FAMILY_H_WEATHER_MEASURABLE",
                    sub_type="D006_METAR_SENSOR_PRUNING",
                    relationship_type="EXTERNAL_OBSERVATION_VERIFICATION",
                    edge_proof_status="EXTERNAL_SENSOR_CLASS_C" if rule_ok else "RULE_MISMATCH_REJECTED",
                    markets=[pw.market],
                    legs=[_build_leg_with_optional_inventory(pw.market.no_token_id, pw.market.market_id, f"NO[{pw.station_or_agency}<={upper_cap:g}{pw.unit}]", holdings)],
                    states=states_metar,
                    title_summary=f"[D006_METAR] {pw.station_or_agency} {pw.local_date_iso}: obs={ob.observed_high:g}{pw.unit} (cush={cushion:g}) vs <={upper_cap:g}{pw.unit}",
                    rule_verified=rule_ok,
                    rule_compatibility_notes=[
                        f"station={pw.station_or_agency}",
                        f"t_group={ob.has_exact_tenths_t_group}",
                        f"cushion={cushion:g}{pw.unit}",
                        "External METAR strictly capped at CLASS_C (never contractual CLASS_A/B)",
                    ],
                    divergence_or_rejection_reasons=d006_reasons,
                    is_statistical_or_cross_oracle_only=True,
                )
            )

    return _rank_and_cap_opportunities(results, max_candidates), rejection_counts


# ---------------------------------------------------------------------------
# 9. FAMILY I — Duplicated & Near-Duplicated Markets (`CLASS_B` vs `CLASS_C`/`CLASS_D`)
# ---------------------------------------------------------------------------

_DUP_NUM_TOKEN_RE = re.compile(r"(?<![a-z0-9])[+\-]?\s*\$?\d+(?:,\d{3})*(?:\.\d+)?%?[kmbt]?", re.IGNORECASE)
_NEGATION_TOKENS = frozenset({"not", "no", "never", "without", "fail", "fails", "lose", "under", "below", "less", "fewer"})
_DIRECTION_OPPOSITE_GROUPS: Tuple[FrozenSet[str], ...] = (
    frozenset({"above", "over", "higher", "more", "exceed", "reach", "hit"}),
    frozenset({"below", "under", "lower", "less", "dip", "drop", "fall"}),
)


def _proposition_signature_for_dup(m: CanonicalBinaryMarket) -> Tuple[str, FrozenSet[str], Tuple[str, ...], FrozenSet[str]]:
    """
    Returns `(canonical_stem, content_tokens, ordered_numeric_tokens, polarity_markers)` for fast O(N)
    duplicate & near-duplicate indexing without confusing distinct strike/date rungs (`$90k` vs `$95k`)
    or opposite signed handicaps/temperatures (`-3.5` vs `+3.5`, `-5°F` vs `5°F`)!
    """
    raw_q = m.question.strip()
    if m.group_item_title and m.group_item_title.lower() not in raw_q.lower():
        # Include `group_item_title` if `question` omits it so generic sub-questions don't false-collide
        raw_q = f"{raw_q} {m.group_item_title.strip()}"
    q_l = raw_q.lower()
    nums = tuple(re.sub(r"[\s,]", "", n).lower() for n in _DUP_NUM_TOKEN_RE.findall(q_l))
    words_all = re.findall(r"(?<![a-z0-9])[+\-]\d+(?:\.\d+)?|[a-z0-9$%.]+", q_l)
    content = frozenset(w for w in words_all if w not in _STOPWORDS and len(w) >= 2)
    pol = frozenset(w for w in words_all if w in _NEGATION_TOKENS)
    stem = " ".join(w for w in words_all if w not in _STOPWORDS)
    return stem, content, nums, pol


def _description_clause_jaccard(desc_a: str, desc_b: str) -> float:
    ta = {w for w in re.findall(r"[a-z0-9]{3,}", str(desc_a or "").lower()) if w not in _STOPWORDS}
    tb = {w for w in re.findall(r"[a-z0-9]{3,}", str(desc_b or "").lower()) if w not in _STOPWORDS}
    if not ta and not tb:
        return 0.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / float(len(ta | tb))


def detect_family_i_duplicate_markets(
    markets: Sequence[CanonicalBinaryMarket],
    books: Mapping[str, InstrumentOrderBook],
    *,
    verifier: Optional[UniversalArbVerifier] = None,
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
    max_candidates: int = 350,
) -> Tuple[List[DetectedOpportunity], Dict[str, int]]:
    """
    Family I — Cross-Event Duplicated & Near-Duplicated Market Matcher:
      - Indexes all active binary markets across the full universe via exact stem + sorted token/number buckets.
      - Audits 6 formal rule-equivalence axes:
          (1) `proposition_equivalence` (zero numeric/polarity/comparator conflict, token Jaccard `>= 0.90`),
          (2) `resolution_authority` parity (explicit & identical),
          (3) `cutoff_timestamp` parity (`|end_1 - end_2| <= 60s`),
          (4) `timezone` parity (`tz_1 == tz_2 != UNSPECIFIED`),
          (5) `void_and_adapter` parity (`cancel_rule` & `resolved_by` match),
          (6) `description_clause_parity` (`exception_sig` match & rule-text Jaccard `>= 0.85`).
      - Classification:
          * All 6 axes pass (`PROVEN_STATE_IDENTICAL`) -> `StateSpaceBuilder(..., relation='EQUIVALENT')` ->
            `CLASS_B` when L2 net `min_w > 0` (`CLASS_A` only if 1 leg is unlocked inventory; `CLASS_E` + dormant if near-miss).
          * Near-duplicate with rule divergence (`RULE_DIVERGENT_NEAR_DUPLICATE`):
              - Minor cross-oracle / wording divergence (`cutoff <= 3600s`, same polarity/numbers, positive main-state EV)
                -> `CLASS_C` (`is_statistical_or_cross_oracle_only=True`, explicit `(1,0)/(0,1)` basis-risk states) with exact `divergence_notes`.
              - Structural / cutoff / void / unspecified-rule divergence -> `CLASS_D` (`rule_verified=False`) with exact `divergence_notes`.
    """
    ver = verifier or UniversalArbVerifier()
    results: List[DetectedOpportunity] = []
    rejection_counts: Dict[str, int] = {}

    def _bump(r: str) -> None:
        rejection_counts[r] = rejection_counts.get(r, 0) + 1

    active = [
        m for m in markets
        if not m.closed_or_archived and m.is_standard_yes_no and m.yes_token_id and m.no_token_id
        and not m.is_placeholder_outcome and not m.is_other_outcome and not m.is_d001_disputed_quarantined()
    ]

    sigs: List[Tuple[CanonicalBinaryMarket, str, FrozenSet[str], Tuple[str, ...], FrozenSet[str]]] = []
    by_exact_stem: Dict[str, List[int]] = {}
    by_anchor_bucket: Dict[Tuple[Tuple[str, ...], Tuple[str, ...]], List[int]] = {}

    # Compute document frequency of content tokens so anchor buckets pick the RAREST informative tokens!
    doc_freq: Dict[str, int] = {}
    for m in active:
        stem, ctoks, nums, pol = _proposition_signature_for_dup(m)
        if len(ctoks) < 3:
            continue
        idx = len(sigs)
        sigs.append((m, stem, ctoks, nums, pol))
        for tok in ctoks:
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
        by_exact_stem.setdefault(stem, []).append(idx)

    for idx, (m, stem, ctoks, nums, _pol) in enumerate(sigs):
        # Pick 3 rarest non-numeric words + `nums` tuple to catch reworded near-duplicates in O(N)!
        non_num_words = sorted([w for w in ctoks if not any(ch.isdigit() for ch in w)], key=lambda w: (doc_freq.get(w, 0), w))
        if len(non_num_words) >= 3:
            anchor = (tuple(non_num_words[:3]), nums)
            by_anchor_bucket.setdefault(anchor, []).append(idx)
        if len(non_num_words) >= 4:
            anchor2 = (tuple(non_num_words[1:4]), nums)
            by_anchor_bucket.setdefault(anchor2, []).append(idx)

    candidate_idx_pairs: Set[Tuple[int, int]] = set()
    for bucket in list(by_exact_stem.values()) + list(by_anchor_bucket.values()):
        if len(bucket) < 2 or len(bucket) > 25:
            continue
        for a_pos in range(len(bucket)):
            for b_pos in range(a_pos + 1, len(bucket)):
                i1, i2 = (bucket[a_pos], bucket[b_pos]) if bucket[a_pos] < bucket[b_pos] else (bucket[b_pos], bucket[a_pos])
                candidate_idx_pairs.add((i1, i2))

    for i1, i2 in sorted(candidate_idx_pairs):
        m1, stem1, ctoks1, nums1, pol1 = sigs[i1]
        m2, stem2, ctoks2, nums2, pol2 = sigs[i2]

        if m1.market_id == m2.market_id:
            continue
        if m1.condition_id and m1.condition_id == m2.condition_id:
            continue
        # Require same numeric anchor tuple so distinct strike/date rungs are never misclassified as duplicates
        if nums1 != nums2:
            continue

        union_len = len(ctoks1 | ctoks2)
        if union_len == 0:
            continue
        prop_jacc = len(ctoks1 & ctoks2) / float(union_len)
        if prop_jacc < 0.72:
            continue

        # Reject opposite-direction comparators (`above $100k` vs `below $100k`)
        up_g, dn_g = _DIRECTION_OPPOSITE_GROUPS[0], _DIRECTION_OPPOSITE_GROUPS[1]
        if (bool(ctoks1 & up_g) and bool(ctoks2 & dn_g)) or (bool(ctoks1 & dn_g) and bool(ctoks2 & up_g)):
            continue
        # Reject intra-event NegRisk mutually exclusive siblings that happen to share rare words
        if m1.event_id == m2.event_id and m1.neg_risk and m2.neg_risk and m1.group_item_title != m2.group_item_title:
            continue

        # Audit all 6 formal rule-equivalence axes
        divergence_notes: List[str] = []
        severe_structural_break = False

        # Axis 1: Proposition parity (including strict vs inclusive & `before` vs `by` boundary parity)
        q1_l, q2_l = m1.question.lower(), m2.question.lower()
        has_before_1 = bool(re.search(r"\b(?:before|prior\s+to)\b", q1_l)) and not bool(re.search(r"\bon\s+or\s+before\b", q1_l))
        has_before_2 = bool(re.search(r"\b(?:before|prior\s+to)\b", q2_l)) and not bool(re.search(r"\bon\s+or\s+before\b", q2_l))
        incl_1 = bool(re.search(r"\b(?:at\s+least|at\s+most|or\s+higher|or\s+above|or\s+more|or\s+lower|or\s+below|or\s+less)\b|>=|<=", q1_l))
        incl_2 = bool(re.search(r"\b(?:at\s+least|at\s+most|or\s+higher|or\s+above|or\s+more|or\s+lower|or\s+below|or\s+less)\b|>=|<=", q2_l))
        if pol1 != pol2:
            divergence_notes.append(f"POLARITY_NEGATION_DIVERGENCE:{sorted(pol1)}_vs_{sorted(pol2)}")
            severe_structural_break = True
        elif has_before_1 != has_before_2:
            divergence_notes.append("DEADLINE_STRICT_BEFORE_VS_INCLUSIVE_BY_DIVERGENCE")
            severe_structural_break = True
        elif nums1 and incl_1 != incl_2 and stem1 != stem2:
            divergence_notes.append("THRESHOLD_STRICT_VS_INCLUSIVE_DIVERGENCE")
            severe_structural_break = True
        elif ctoks1 != ctoks2:
            # Any asymmetric content token (`most` vs `second-most`, `Actress` vs `Supporting Actress`) is a different proposition!
            sym_diff = sorted(ctoks1 ^ ctoks2)
            divergence_notes.append(f"ASYMMETRIC_PROPOSITION_TOKENS:{sym_diff}")
            severe_structural_break = True
        elif stem1 != stem2:
            # `BUG-LS-3`: Subject-object reversal (`"OpenAI acquire Anthropic"` vs `"Anthropic acquire OpenAI"`,
            # `"Celtics beat Lakers"` vs `"Lakers beat Celtics"`) shares identical unordered `ctoks` but opposite meaning!
            divergence_notes.append("WORD_ORDER_SUBJECT_OBJECT_INVERSION")
            severe_structural_break = True

        # Axis 2: Resolution authority
        auth1 = extract_resolution_authority_signature(m1)
        auth2 = extract_resolution_authority_signature(m2)
        if auth1 == "UNSPECIFIED_AUTHORITY" or auth2 == "UNSPECIFIED_AUTHORITY":
            divergence_notes.append(f"AUTHORITY_UNSPECIFIED:{auth1}_vs_{auth2}")
            severe_structural_break = True
        elif auth1 != auth2:
            divergence_notes.append(f"AUTHORITY_DIVERGENCE:{auth1}_vs_{auth2}")

        # Axis 3: Cutoff timestamp
        if m1.end_ts is None or m2.end_ts is None:
            divergence_notes.append("CUTOFF_TIMESTAMP_MISSING")
            severe_structural_break = True
        else:
            dt_diff = abs(m1.end_ts - m2.end_ts)
            if dt_diff > 60.0:
                divergence_notes.append(f"CUTOFF_TIMESTAMP_DIVERGENCE:{dt_diff:.0f}s")
                if dt_diff > 3600.0:
                    severe_structural_break = True

        # Axis 4: Timezone
        tz1, _ = extract_timezone_signature(m1)
        tz2, _ = extract_timezone_signature(m2)
        if tz1 == "UNSPECIFIED" or tz2 == "UNSPECIFIED" or tz1.startswith("CONFLICTING_TZ_") or tz2.startswith("CONFLICTING_TZ_"):
            divergence_notes.append(f"TIMEZONE_UNSPECIFIED_OR_CONFLICT:{tz1}_vs_{tz2}")
            severe_structural_break = True
        elif tz1 != tz2:
            divergence_notes.append(f"TIMEZONE_DIVERGENCE:{tz1}_vs_{tz2}")
            severe_structural_break = True

        # Axis 5: Void / cancellation & UMA adapter
        if m1.cancel_rule_tag != m2.cancel_rule_tag:
            divergence_notes.append(f"VOID_RULE_DIVERGENCE:{m1.cancel_rule_tag}_vs_{m2.cancel_rule_tag}")
            severe_structural_break = True
        if m1.resolved_by and m2.resolved_by and m1.resolved_by != m2.resolved_by:
            divergence_notes.append(f"UMA_ADAPTER_DIVERGENCE:{m1.resolved_by}_vs_{m2.resolved_by}")

        # Axis 6: Exception clauses & description rule-text overlap
        exc1 = extract_exception_clause_signature(m1)
        exc2 = extract_exception_clause_signature(m2)
        if exc1 != exc2:
            divergence_notes.append(f"EXCEPTION_CLAUSE_DIVERGENCE:{exc1}_vs_{exc2}")
            severe_structural_break = True
        desc_jacc = _description_clause_jaccard(m1.description, m2.description)
        if desc_jacc < 0.85:
            divergence_notes.append(f"DESCRIPTION_CLAUSE_DIVERGENCE:jaccard={desc_jacc:.2f}")
            if desc_jacc < 0.45:
                severe_structural_break = True

        for dn in divergence_notes:
            _bump(dn.split(":")[0])

        # Choose cheaper hedge direction between `(YES_1 + NO_2)` and `(NO_1 + YES_2)`
        c_dir1 = _quick_l1_buy_cost_sum([(m1.yes_token_id, m1), (m2.no_token_id, m2)], books)
        c_dir2 = _quick_l1_buy_cost_sum([(m1.no_token_id, m1), (m2.yes_token_id, m2)], books)
        use_dir2 = (c_dir2 is not None) and (c_dir1 is None or c_dir2 < c_dir1)

        if not use_dir2:
            legs_dup = [
                _build_leg_with_optional_inventory(m1.yes_token_id, m1.market_id, f"YES[{m1.question[:30]}]", holdings),
                _build_leg_with_optional_inventory(m2.no_token_id, m2.market_id, f"NO[{m2.question[:30]}]", holdings),
            ]
            dir_tag = "YES1_NO2"
        else:
            legs_dup = [
                _build_leg_with_optional_inventory(m1.no_token_id, m1.market_id, f"NO[{m1.question[:30]}]", holdings),
                _build_leg_with_optional_inventory(m2.yes_token_id, m2.market_id, f"YES[{m2.question[:30]}]", holdings),
            ]
            dir_tag = "NO1_YES2"

        best_l1 = c_dir2 if use_dir2 else c_dir1

        if len(divergence_notes) == 0:
            # Provably state-identical rules -> `EQUIVALENT` (`CLASS_B` if L2 net arb > 0, `CLASS_A` if 1 leg held!)
            states_dup = StateSpaceBuilder.two_market_logical_states(
                m1.yes_token_id, m1.no_token_id,
                m2.yes_token_id, m2.no_token_id,
                relation="EQUIVALENT",
                cancel_rule_a=m1.cancel_rule_tag,
                cancel_rule_b=m2.cancel_rule_tag,
            )
            results.append(
                _finalize_detected_opportunity(
                    ver, books, holdings,
                    candidate_id=_make_candidate_id("I", f"DUP_EXACT_{dir_tag}", [m1.market_id, m2.market_id]),
                    family="FAMILY_I_DUPLICATE_MARKETS",
                    sub_type="PROVEN_STATE_IDENTICAL_DUPLICATE",
                    relationship_type="EQUIVALENT",
                    edge_proof_status="VERIFIED_MATHEMATICAL",
                    markets=[m1, m2],
                    legs=legs_dup,
                    states=states_dup,
                    title_summary=f"[EXACT_DUP] ({m1.question[:44]}) == ({m2.question[:44]})",
                    rule_verified=True,
                    rule_compatibility_notes=[
                        f"prop_jaccard={prop_jacc:.2f}",
                        f"desc_jaccard={desc_jacc:.2f}",
                        f"authority={auth1}",
                        f"tz={tz1}",
                    ],
                    divergence_or_rejection_reasons=[],
                    metadata={"proposition_jaccard": round(prop_jacc, 4), "description_jaccard": round(desc_jacc, 4)},
                )
            )
        else:
            # Rule-divergent near-duplicate:
            #   - If NOT `severe_structural_break` AND apparent L1 cost `< $1.00` -> model `96%` correlated main states
            #     + `4%` `(1,0)/(0,1)` basis-divergence states with `is_statistical_or_cross_oracle_only=True` -> `CLASS_C`!
            #   - Otherwise -> `rule_verified=False` -> `CLASS_D`!
            is_soft_near_dup_with_ev = (not severe_structural_break) and (best_l1 is not None and best_l1 < 0.995)
            states_div = [
                _mk_state("BOTH_YES_MAIN", "Correlated YES resolution", {
                    m1.yes_token_id: 1.0, m1.no_token_id: 0.0, m2.yes_token_id: 1.0, m2.no_token_id: 0.0
                }, 0.48),
                _mk_state("BOTH_NO_MAIN", "Correlated NO resolution", {
                    m1.yes_token_id: 0.0, m1.no_token_id: 1.0, m2.yes_token_id: 0.0, m2.no_token_id: 1.0
                }, 0.48),
                _mk_state("RULE_DIVERGENCE_YES1_NO2", "Divergent rules resolve M1=YES, M2=NO", {
                    m1.yes_token_id: 1.0, m1.no_token_id: 0.0, m2.yes_token_id: 0.0, m2.no_token_id: 1.0
                }, 0.02, is_edge_or_void_state=True),
                _mk_state("RULE_DIVERGENCE_NO1_YES2", "Divergent rules resolve M1=NO, M2=YES", {
                    m1.yes_token_id: 0.0, m1.no_token_id: 1.0, m2.yes_token_id: 1.0, m2.no_token_id: 0.0
                }, 0.02, is_edge_or_void_state=True),
            ]
            results.append(
                _finalize_detected_opportunity(
                    ver, books, holdings,
                    candidate_id=_make_candidate_id("I", f"NEAR_DUP_{dir_tag}", [m1.market_id, m2.market_id]),
                    family="FAMILY_I_DUPLICATE_MARKETS",
                    sub_type="NEAR_DUPLICATE_CROSS_ORACLE_BASIS" if is_soft_near_dup_with_ev else "NEAR_DUPLICATE_RULE_MISMATCH",
                    relationship_type="NEAR_EQUIVALENT_DIVERGENT_RULES",
                    edge_proof_status="NEAR_DUPLICATE_CLASS_C" if is_soft_near_dup_with_ev else "RULE_MISMATCH_REJECTED",
                    markets=[m1, m2],
                    legs=legs_dup,
                    states=states_div,
                    title_summary=f"[NEAR_DUP] ({m1.question[:42]}) ~ ({m2.question[:42]})",
                    rule_verified=bool(is_soft_near_dup_with_ev),
                    rule_compatibility_notes=[f"prop_jaccard={prop_jacc:.2f}", f"desc_jaccard={desc_jacc:.2f}"],
                    divergence_or_rejection_reasons=divergence_notes,
                    is_statistical_or_cross_oracle_only=bool(is_soft_near_dup_with_ev),
                    metadata={
                        "proposition_jaccard": round(prop_jacc, 4),
                        "description_jaccard": round(desc_jacc, 4),
                        "divergence_notes": list(divergence_notes),
                    },
                )
            )

    return _rank_and_cap_opportunities(results, max_candidates), rejection_counts


# ---------------------------------------------------------------------------
# 10. Unified Orchestrator, Candidate Token Pre-Selector & Full-Universe Live Scan
# ---------------------------------------------------------------------------

def collect_candidate_token_ids_d_to_i(
    markets: Sequence[CanonicalBinaryMarket],
    *,
    now_ts: Optional[float] = None,
    max_tokens_per_family: int = 8_000,
) -> Dict[str, List[str]]:
    """
    Fast `O(N)` structural pre-pass across all `199k+` active markets identifying every tradable
    `yes_token_id` and `no_token_id` participating in a `>=2`-market Family D..I group so live
    CLOB `/books` batching fetches exact L2 depth for 100% of structurally linked pairs!
    """
    now_f = float(time.time() if now_ts is None else now_ts)
    tradable = [
        m for m in markets
        if not m.closed_or_archived and m.enable_order_book and m.accepting_orders
        and m.yes_token_id and m.no_token_id and not m.is_d001_disputed_quarantined()
    ]

    fam_tokens: Dict[str, Set[str]] = {k: set() for k in ("D", "E", "F", "G", "H", "I")}

    def _add_mkt(fam: str, m: CanonicalBinaryMarket) -> None:
        if len(fam_tokens[fam]) < max_tokens_per_family:
            fam_tokens[fam].add(m.yes_token_id)
            fam_tokens[fam].add(m.no_token_id)

    # Family D structural participants
    by_prize: Dict[str, List[CanonicalBinaryMarket]] = {}
    for m in tradable:
        if not m.is_standard_yes_no:
            continue
        blob_l = f"{m.event_slug} {m.event_title} {m.question}".lower()
        if any(
            kw in blob_l
            for kw in (
                "trifecta",
                "sweep",
                "win the senate",
                "win the house",
                "presidential election",
                "popular vote",
                "nomination",
                "nominee",
                "win both",
                "without losing",
                "by at least",
                "by more than",
            )
        ):
            _add_mkt("D", m)
        mw = _SINGLE_WINNER_QUESTION_RE.match(m.question.strip()) if (
            m.question[:5].lower() == "will " and (" win " in m.question.lower() or " be " in m.question.lower())
        ) else None
        if mw and not m.is_placeholder_outcome and not m.is_other_outcome:
            prize = _norm_entity_text(mw.group(2))
            if len(prize) >= 8 and not re.search(r"\b(?:top\s+\d+|playoffs?|a\s+medal|nominat|a\s+seat|at\s+least)\b", prize):
                by_prize.setdefault(f"{prize}::{extract_resolution_authority_signature(m)}", []).append(m)
    for plist in by_prize.values():
        if len(plist) >= 2:
            ev_ids = {x.event_id for x in plist}
            if len(ev_ids) > 1 or any(not x.neg_risk for x in plist):
                for x in plist[:12]:
                    _add_mkt("D", x)

    # Family E temporal groups (`>= 2` cutoffs on same stem)
    by_t_stem: Dict[str, List[CanonicalBinaryMarket]] = {}
    for m in tradable:
        pt = parse_temporal_contract(m)
        if pt is not None and pt.cutoff_ts_utc > now_f - 3600.0:
            by_t_stem.setdefault(pt.proposition_stem, []).append(m)
    for grp in by_t_stem.values():
        if len(grp) >= 2:
            for x in grp:
                _add_mkt("E", x)

    # Family F strike groups (`>= 2` strikes on same asset+day)
    by_s_key: Dict[Tuple[str, int], List[CanonicalBinaryMarket]] = {}
    for m in tradable:
        ps = parse_strike_contract(m)
        if ps is not None and ps.cutoff_ts_utc > now_f - 3600.0:
            by_s_key.setdefault((ps.asset_key, int(ps.cutoff_ts_utc // 86400.0)), []).append(m)
    for grp in by_s_key.values():
        if len(grp) >= 2:
            for x in grp:
                _add_mkt("F", x)

    # Family G sports fixture & tournament groups (`>= 2` markets on same fixture or team tournament, sorted by liquidity!)
    by_sp_fix: Dict[str, List[CanonicalBinaryMarket]] = {}
    for m in tradable:
        pg = parse_sports_contract(m)
        if pg is not None:
            gk = f"T::{pg.tournament_key}::{pg.primary_team}" if pg.market_kind == "TOURNAMENT_ADVANCEMENT" else pg.fixture_key
            by_sp_fix.setdefault(gk, []).append(m)
    scored_sp_groups: List[Tuple[float, List[CanonicalBinaryMarket]]] = []
    for grp in by_sp_fix.values():
        if len(grp) >= 2:
            # Skip pure intra-event NegRisk 3-way with no auxiliary markets unless standalone/mixed
            if len(grp) == 3 and len({x.event_id for x in grp}) == 1 and all(x.neg_risk and x.is_standard_yes_no for x in grp):
                continue
            liq_sum = sum(x.liquidity_usd + x.volume_24h_usd for x in grp)
            scored_sp_groups.append((liq_sum, grp))
    scored_sp_groups.sort(key=lambda item: -item[0])
    for _liq, grp in scored_sp_groups:
        for x in grp:
            _add_mkt("G", x)

    # Family H weather & measurable groups
    by_wx_city: Dict[str, List[CanonicalBinaryMarket]] = {}
    for m in tradable:
        pw = parse_weather_measurable_contract(m)
        if pw is not None:
            cfam = "NYC" if pw.station_or_agency in {"KLGA", "KJFK", "KNYC", "NYC_UNSPECIFIED_STATION"} else (
                "LONDON" if pw.station_or_agency in {"EGLC", "EGLL", "LONDON_UNSPECIFIED_STATION"} else pw.station_or_agency
            )
            by_wx_city.setdefault(f"{cfam}::{pw.local_date_iso}", []).append(m)
    for grp in by_wx_city.values():
        if len(grp) >= 2:
            for x in grp:
                _add_mkt("H", x)

    # Family I duplicate / near-duplicate buckets
    std_tradable = [m for m in tradable if m.is_standard_yes_no and not m.is_placeholder_outcome and not m.is_other_outcome]
    df: Dict[str, int] = {}
    tmp_sigs: List[Tuple[CanonicalBinaryMarket, str, FrozenSet[str], Tuple[str, ...]]] = []
    stem_bkt: Dict[str, List[CanonicalBinaryMarket]] = {}
    for m in std_tradable:
        st, ct, nm, _ = _proposition_signature_for_dup(m)
        if len(ct) < 3:
            continue
        tmp_sigs.append((m, st, ct, nm))
        stem_bkt.setdefault(st, []).append(m)
        for w in ct:
            df[w] = df.get(w, 0) + 1
    anch_bkt: Dict[Tuple[Tuple[str, ...], Tuple[str, ...]], List[CanonicalBinaryMarket]] = {}
    for m, _st, ct, nm in tmp_sigs:
        nn = sorted([w for w in ct if not any(c.isdigit() for c in w)], key=lambda w: (df.get(w, 0), w))
        if len(nn) >= 3:
            anch_bkt.setdefault((tuple(nn[:3]), nm), []).append(m)
    for bkt in list(stem_bkt.values()) + list(anch_bkt.values()):
        if 2 <= len(bkt) <= 20:
            for x in bkt:
                _add_mkt("I", x)

    return {fam: sorted(toks) for fam, toks in fam_tokens.items()}


@dataclass
class LogicalSpecializedScanReport:
    generated_at_utc: str
    scan_elapsed_sec: float
    total_events_ingested: int
    total_canonical_markets: int
    total_books_loaded: int
    d001_disputed_quarantined_count: int
    per_family_counts: Dict[str, Dict[str, int]]
    class_distribution: Dict[str, int]
    rule_mismatch_rejections_by_reason: Dict[str, int]
    total_rule_mismatch_rejections_prevented: int
    executable_class_a_b_opportunities: List[Dict[str, Any]]
    class_c_conditional_opportunities: List[Dict[str, Any]]
    dormant_near_miss_pairs: List[Dict[str, Any]]
    sample_rule_mismatch_catches: List[Dict[str, Any]]
    existing_scanner_audit: Dict[str, Any]
    all_opportunities: List[DetectedOpportunity] = field(default_factory=list, repr=False)

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "generated_at_utc": self.generated_at_utc,
            "scan_elapsed_sec": round(self.scan_elapsed_sec, 3),
            "universe_metrics": {
                "total_events_ingested": self.total_events_ingested,
                "total_canonical_markets": self.total_canonical_markets,
                "total_books_loaded": self.total_books_loaded,
                "d001_disputed_quarantined_count": self.d001_disputed_quarantined_count,
            },
            "per_family_counts": self.per_family_counts,
            "class_distribution": self.class_distribution,
            "total_rule_mismatch_rejections_prevented": self.total_rule_mismatch_rejections_prevented,
            "rule_mismatch_rejections_by_reason": self.rule_mismatch_rejections_by_reason,
            "executable_class_a_b_count": len(self.executable_class_a_b_opportunities),
            "executable_class_a_b_opportunities": self.executable_class_a_b_opportunities,
            "class_c_conditional_count": len(self.class_c_conditional_opportunities),
            "class_c_conditional_opportunities": self.class_c_conditional_opportunities[:25],
            "dormant_near_miss_count": len(self.dormant_near_miss_pairs),
            "dormant_near_miss_pairs": self.dormant_near_miss_pairs[:40],
            "sample_rule_mismatch_catches": self.sample_rule_mismatch_catches[:40],
            "existing_scanner_audit": self.existing_scanner_audit,
        }


class LogicalSpecializedScanner:
    """
    Unified orchestrator for Opportunity Families D, E, F, G, H & I (`detectors_logical_and_specialized.py`).
    Accepts either raw Gamma `events` dicts, `@discovery` normalized events/markets, or `CanonicalBinaryMarket`s,
    plus either `Mapping[str, InstrumentOrderBook]` or raw CLOB `/books` `Mapping[str, dict]`.
    """

    def __init__(
        self,
        *,
        verifier: Optional[UniversalArbVerifier] = None,
        reconciled_nav_usd: float = DEFAULT_LIVE_RECONCILED_NAV_USD,
        max_budget_usd: Optional[float] = None,
        now_ts: Optional[float] = None,
    ) -> None:
        if verifier is not None:
            self.verifier = verifier
        else:
            cfg = VerificationConfig(
                reconciled_nav_usd=reconciled_nav_usd,
                max_budget_usd=100.0 if max_budget_usd is None else float(max_budget_usd),
                now_ts=now_ts,
            )
            self.verifier = UniversalArbVerifier(config=cfg)

    def scan_all_families(
        self,
        events_or_markets: Sequence[Any],
        raw_or_typed_books: Optional[Mapping[str, Any]] = None,
        *,
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
        weather_observations: Optional[Sequence[MetarObservationSnapshot]] = None,
        default_book_fetch_ts: Optional[float] = None,
        max_candidates_per_family: int = 400,
        total_events_hint: Optional[int] = None,
    ) -> LogicalSpecializedScanReport:
        t0 = time.perf_counter()
        if events_or_markets and isinstance(events_or_markets[0], CanonicalBinaryMarket):
            canon_mkts = list(events_or_markets)
        else:
            canon_mkts = normalize_universe_to_canonical_markets(events_or_markets)

        books = build_instrument_order_books(
            canon_mkts,
            raw_or_typed_books,
            default_fetch_ts=default_book_fetch_ts,
        )
        now_eval = self.verifier.config.now_ts

        opps_d, rej_d = detect_family_d_logical_arbitrage(
            canon_mkts, books, verifier=self.verifier, holdings=holdings, max_candidates=max_candidates_per_family
        )
        opps_e, rej_e = detect_family_e_temporal_deadline_arbitrage(
            canon_mkts, books, verifier=self.verifier, holdings=holdings, now_ts=now_eval, max_candidates=max_candidates_per_family
        )
        opps_f, rej_f = detect_family_f_price_strike_ladders(
            canon_mkts, books, verifier=self.verifier, holdings=holdings, now_ts=now_eval, max_candidates=max_candidates_per_family
        )
        opps_g, rej_g = detect_family_g_sports_structures(
            canon_mkts, books, verifier=self.verifier, holdings=holdings, max_candidates=max_candidates_per_family
        )
        opps_h, rej_h = detect_family_h_weather_measurable(
            canon_mkts, books, verifier=self.verifier, holdings=holdings, observations=weather_observations, max_candidates=max_candidates_per_family
        )
        opps_i, rej_i = detect_family_i_duplicate_markets(
            canon_mkts, books, verifier=self.verifier, holdings=holdings, max_candidates=max_candidates_per_family
        )

        fam_map = {
            "FAMILY_D_CROSS_MARKET_LOGICAL": (opps_d, rej_d),
            "FAMILY_E_TEMPORAL_DEADLINE": (opps_e, rej_e),
            "FAMILY_F_PRICE_STRIKE_LADDER": (opps_f, rej_f),
            "FAMILY_G_SPORTS_STRUCTURE": (opps_g, rej_g),
            "FAMILY_H_WEATHER_MEASURABLE": (opps_h, rej_h),
            "FAMILY_I_DUPLICATE_MARKETS": (opps_i, rej_i),
        }

        per_family_counts: Dict[str, Dict[str, int]] = {}
        merged_rej: Dict[str, int] = {}
        all_opps: List[DetectedOpportunity] = []

        for fam_name, (op_list, r_dict) in fam_map.items():
            all_opps.extend(op_list)
            for rk, rv in r_dict.items():
                merged_rej[rk] = merged_rej.get(rk, 0) + int(rv)
            per_family_counts[fam_name] = {
                "candidates_evaluated": len(op_list),
                "CLASS_A": sum(1 for x in op_list if x.proof.opportunity_class == OpportunityClass.CLASS_A.value),
                "CLASS_B": sum(1 for x in op_list if x.proof.opportunity_class == OpportunityClass.CLASS_B.value),
                "CLASS_C": sum(1 for x in op_list if x.proof.opportunity_class == OpportunityClass.CLASS_C.value),
                "CLASS_D_rejected": sum(1 for x in op_list if x.proof.opportunity_class == OpportunityClass.CLASS_D.value),
                "CLASS_E_no_arb": sum(1 for x in op_list if x.proof.opportunity_class == OpportunityClass.CLASS_E.value),
                "dormant_near_misses": sum(1 for x in op_list if x.is_dormant_near_miss),
                "rule_mismatch_flags": sum(int(v) for v in r_dict.values()),
            }

        class_dist: Dict[str, int] = {c.value: 0 for c in OpportunityClass}
        for op in all_opps:
            class_dist[op.proof.opportunity_class] = class_dist.get(op.proof.opportunity_class, 0) + 1

        exec_ab = [
            op.to_dict()
            for op in sorted(
                [x for x in all_opps if x.proof.opportunity_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value}],
                key=lambda x: -float(x.proof.min_state_net_payoff_usd),
            )
        ]
        cond_c = [
            op.to_dict()
            for op in sorted(
                [x for x in all_opps if x.proof.opportunity_class == OpportunityClass.CLASS_C.value],
                key=lambda x: -float(x.proof.expected_net_payoff_usd),
            )
        ]
        dormant = [
            op.to_dict()
            for op in sorted(
                [x for x in all_opps if x.is_dormant_near_miss],
                key=lambda x: float(x.gap_to_breakeven_bps),
            )
        ]
        mismatch_samples = [
            op.to_dict()
            for op in all_opps
            if op.proof.opportunity_class == OpportunityClass.CLASS_D.value and op.divergence_or_rejection_reasons
        ]

        d001_cnt = sum(1 for m in canon_mkts if m.is_d001_disputed_quarantined())
        ev_cnt = total_events_hint if total_events_hint is not None else len({m.event_id for m in canon_mkts})

        return LogicalSpecializedScanReport(
            generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            scan_elapsed_sec=time.perf_counter() - t0,
            total_events_ingested=ev_cnt,
            total_canonical_markets=len(canon_mkts),
            total_books_loaded=len(books),
            d001_disputed_quarantined_count=d001_cnt,
            per_family_counts=per_family_counts,
            class_distribution=class_dist,
            rule_mismatch_rejections_by_reason=dict(sorted(merged_rej.items(), key=lambda kv: (-kv[1], kv[0]))),
            total_rule_mismatch_rejections_prevented=sum(merged_rej.values()),
            executable_class_a_b_opportunities=exec_ab,
            class_c_conditional_opportunities=cond_c,
            dormant_near_miss_pairs=dormant,
            sample_rule_mismatch_catches=mismatch_samples,
            existing_scanner_audit=audit_existing_logical_specialized_scanners(),
            all_opportunities=all_opps,
        )


# ---------------------------------------------------------------------------
# 11. Pure-Stdlib Public Gamma `/events/keyset` + CLOB `/books` Sweep Runner
# ---------------------------------------------------------------------------

def _read_http_json_response(resp: http.client.HTTPResponse) -> Any:
    import gzip

    raw = resp.read()
    enc = (resp.getheader("Content-Encoding") or "").lower()
    if "gzip" in enc and raw:
        raw = gzip.decompress(raw)
    if not raw:
        return None
    return json.loads(raw.decode("utf-8", errors="replace"))


def fetch_all_active_gamma_events_keyset(
    *,
    limit: int = 200,
    max_pages: int = 250,
    timeout_sec: float = 25.0,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[Dict[str, Any]]:
    """
    Paginates 100% of active unclosed events from public Gamma `/events/keyset?active=true&closed=false`
    using `after_cursor=<next_cursor>` over a persistent TLS keep-alive socket with `gzip` compression.
    Never uses `/events?offset=...` (which truncates at HTTP 422 around `offset=2100`).
    """
    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection("gamma-api.polymarket.com", timeout=timeout_sec, context=ctx)
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "keep-alive",
        "User-Agent": "DominusRisklessScanner/5.1 (MODE1-PublicReadOnly)",
    }

    events_out: List[Dict[str, Any]] = []
    seen_event_ids: Set[str] = set()
    cursor: Optional[str] = None

    try:
        for page_idx in range(max_pages):
            qs: Dict[str, Any] = {"active": "true", "closed": "false", "limit": str(int(limit))}
            if cursor:
                qs["after_cursor"] = cursor
            path = f"/events/keyset?{urllib.parse.urlencode(qs)}"

            payload = None
            for attempt in range(3):
                try:
                    conn.request("GET", path, headers=headers)
                    resp = conn.getresponse()
                    status = resp.status
                    if status == 200:
                        payload = _read_http_json_response(resp)
                        break
                    _ = resp.read()
                    if status in {429, 500, 502, 503, 504}:
                        time.sleep(0.4 * (attempt + 1))
                        conn.close()
                        conn = http.client.HTTPSConnection("gamma-api.polymarket.com", timeout=timeout_sec, context=ctx)
                        continue
                    break
                except Exception:
                    time.sleep(0.35 * (attempt + 1))
                    conn.close()
                    conn = http.client.HTTPSConnection("gamma-api.polymarket.com", timeout=timeout_sec, context=ctx)

            if not isinstance(payload, Mapping):
                break
            batch = payload.get("events")
            if not isinstance(batch, list) or not batch:
                break
            for ev in batch:
                if isinstance(ev, dict):
                    eid = str(ev.get("id") or "").strip()
                    if eid and eid not in seen_event_ids:
                        seen_event_ids.add(eid)
                        events_out.append(ev)
            if progress_callback is not None:
                progress_callback(page_idx + 1, len(events_out))
            nxt = payload.get("next_cursor")
            if not nxt or str(nxt) == str(cursor):
                break
            cursor = str(nxt)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return events_out


def fetch_clob_books_batch_stdlib(
    token_ids: Sequence[str],
    *,
    chunk_size: int = 150,
    max_workers: int = 8,
    timeout_sec: float = 18.0,
) -> Tuple[Dict[str, Dict[str, Any]], float]:
    """
    Fetches live L2 order books via `POST https://clob.polymarket.com/books` using thread-local
    persistent TLS connections (`stdlib` only; zero private credentials).
    Returns `(books_by_asset_id, fetch_timestamp_sec)`.
    """
    unique_toks = [t for t in dict.fromkeys(str(x).strip() for x in token_ids) if t]
    if not unique_toks:
        return {}, time.time()

    chunks = [unique_toks[i : i + chunk_size] for i in range(0, len(unique_toks), chunk_size)]
    tls_local = threading.local()
    ctx = ssl.create_default_context()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "keep-alive",
        "User-Agent": "DominusRisklessScanner/5.1 (MODE1-PublicReadOnly)",
    }

    def _get_conn() -> http.client.HTTPSConnection:
        c = getattr(tls_local, "conn", None)
        if c is None:
            c = http.client.HTTPSConnection("clob.polymarket.com", timeout=timeout_sec, context=ctx)
            tls_local.conn = c
        return c

    def _fetch_chunk(tok_chunk: List[str]) -> Dict[str, Dict[str, Any]]:
        body_bytes = json.dumps([{"token_id": t} for t in tok_chunk]).encode("utf-8")
        out_c: Dict[str, Dict[str, Any]] = {}
        for attempt in range(3):
            conn = _get_conn()
            try:
                conn.request("POST", "/books", body=body_bytes, headers=headers)
                resp = conn.getresponse()
                if resp.status == 200:
                    arr = _read_http_json_response(resp)
                    if isinstance(arr, list):
                        for row in arr:
                            if isinstance(row, dict):
                                aid = str(row.get("asset_id") or row.get("token_id") or "").strip()
                                if aid:
                                    out_c[aid] = row
                    return out_c
                _ = resp.read()
                if resp.status in {429, 500, 502, 503, 504}:
                    time.sleep(0.35 * (attempt + 1))
                conn.close()
                tls_local.conn = None
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                tls_local.conn = None
                time.sleep(0.25 * (attempt + 1))
        return out_c

    merged_books: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(chunks)))) as pool:
        futs = [pool.submit(_fetch_chunk, ch) for ch in chunks]
        for fut in as_completed(futs):
            merged_books.update(fut.result())

    fetch_ts = time.time()
    return merged_books, fetch_ts


def run_live_d_to_i_empirical_scan(
    *,
    output_path: Optional[str | Path] = "data/full_throttle/scans_d_to_i/scan_summary.json",
    max_gamma_pages: int = 260,
    max_tokens_per_family: int = 3_000,
    max_candidates_per_family: int = 500,
    reconciled_nav_usd: float = DEFAULT_LIVE_RECONCILED_NAV_USD,
) -> Dict[str, Any]:
    """
    Executes the full-universe empirical scan across Families D, E, F, G, H & I against live
    public Gamma `/events/keyset` + batched CLOB `/books`, saving `scan_summary.json`.
    """
    import sys

    t_start = time.perf_counter()
    events = fetch_all_active_gamma_events_keyset(
        limit=200,
        max_pages=max_gamma_pages,
        progress_callback=lambda p, n: sys.stderr.write(f"[Gamma] page={p} events={n}\n") if p % 40 == 0 else None,
    )
    sys.stderr.write(f"[Gamma] fetched {len(events)} active events in {time.perf_counter() - t_start:.1f}s\n")
    t1 = time.perf_counter()
    canon_mkts = normalize_universe_to_canonical_markets(events, skip_closed_non_disputed=True)
    sys.stderr.write(f"[Normalize] {len(canon_mkts)} active canonical markets in {time.perf_counter() - t1:.1f}s\n")
    t2 = time.perf_counter()
    fam_tok_map = collect_candidate_token_ids_d_to_i(
        canon_mkts, max_tokens_per_family=max_tokens_per_family
    )
    union_tokens: List[str] = sorted({tok for tlist in fam_tok_map.values() for tok in tlist})
    sys.stderr.write(f"[Preselect] {len(union_tokens)} unique tokens in {time.perf_counter() - t2:.1f}s ({ {k: len(v) for k, v in fam_tok_map.items()} })\n")
    t3 = time.perf_counter()
    raw_books, fetch_ts = fetch_clob_books_batch_stdlib(union_tokens, chunk_size=200, max_workers=8)
    sys.stderr.write(f"[CLOB /books] fetched {len(raw_books)}/{len(union_tokens)} books in {time.perf_counter() - t3:.1f}s\n")

    t4 = time.perf_counter()
    scanner = LogicalSpecializedScanner(reconciled_nav_usd=reconciled_nav_usd, now_ts=fetch_ts)
    report = scanner.scan_all_families(
        canon_mkts,
        raw_books,
        default_book_fetch_ts=fetch_ts,
        max_candidates_per_family=max_candidates_per_family,
        total_events_hint=len(events),
    )
    sys.stderr.write(f"[Detectors D..I] completed in {time.perf_counter() - t4:.1f}s\n")

    summary = report.to_summary_dict()
    summary["live_fetch_telemetry"] = {
        "total_wall_clock_sec": round(time.perf_counter() - t_start, 3),
        "gamma_events_fetched": len(events),
        "candidate_tokens_by_family": {k: len(v) for k, v in fam_tok_map.items()},
        "unique_candidate_tokens_queried": len(union_tokens),
        "clob_books_returned": len(raw_books),
    }

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(summary, indent=2, sort_keys=False), encoding="utf-8", newline="\n")

    return summary


__all__ = [
    "D006_UNVERIFIED_SENSOR_CUSHION_C",
    "D006_UNVERIFIED_SENSOR_CUSHION_F",
    "DORMANT_NEAR_MISS_MAX_DEFICIT_PER_UNIT",
    "CanonicalBinaryMarket",
    "DetectedOpportunity",
    "ExistingScannerGapAudit",
    "LogicalSpecializedScanReport",
    "LogicalSpecializedScanner",
    "MetarObservationSnapshot",
    "ParsedSportsContract",
    "ParsedStrikeContract",
    "ParsedTemporalContract",
    "ParsedWeatherContract",
    "audit_existing_logical_specialized_scanners",
    "build_instrument_order_books",
    "collect_candidate_token_ids_d_to_i",
    "detect_family_d_logical_arbitrage",
    "detect_family_e_temporal_deadline_arbitrage",
    "detect_family_f_price_strike_ladders",
    "detect_family_g_sports_structures",
    "detect_family_h_weather_measurable",
    "detect_family_i_duplicate_markets",
    "evaluate_explicit_logical_pair",
    "extract_exception_clause_signature",
    "extract_fee_bps_and_exponent",
    "extract_price_oracle_feed",
    "extract_resolution_authority_signature",
    "extract_timezone_signature",
    "fetch_all_active_gamma_events_keyset",
    "fetch_clob_books_batch_stdlib",
    "normalize_universe_to_canonical_markets",
    "parse_sports_contract",
    "parse_strike_contract",
    "parse_temporal_contract",
    "parse_weather_measurable_contract",
    "resolve_tz",
    "run_live_d_to_i_empirical_scan",
]


if __name__ == "__main__":
    res = run_live_d_to_i_empirical_scan()
    print(
        json.dumps(
            {
                "universe_metrics": res["universe_metrics"],
                "live_fetch_telemetry": res["live_fetch_telemetry"],
                "class_distribution": res["class_distribution"],
                "executable_class_a_b_count": res["executable_class_a_b_count"],
                "dormant_near_miss_count": res["dormant_near_miss_count"],
                "total_rule_mismatch_rejections_prevented": res["total_rule_mismatch_rejections_prevented"],
            },
            indent=2,
        )
    )

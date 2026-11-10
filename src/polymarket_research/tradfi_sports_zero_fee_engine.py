#!/usr/bin/env python3
"""
Zero-Fee TradFi (Pyth Commodities, Metals & Equities), NBA Polish-Middle & NegRisk Engine
=========================================================================================
Expands Alpha-124 shadow trading into verified `0.00%`-fee (`feeType="zero_fees"`) verticals
while enforcing strict oracle-exactness and zero-lookahead rules:

  1. `CM_B3_PYTH_BARRIER_BOX` (`100%` WR Riskless `0%`-Fee Structural Boxes):
     - Same-event upward/downward barrier monotonicity (`YES(K_low) + NO(K_high) <= $0.994`).
     - Calendar inclusion (`NO(Week, K) + YES(Month, K) <= $0.994` on identical Pyth feed).
     - Path-vs-Terminal inclusion (`NO(Close > K_c) + YES(Hit >= K_h) <= $0.994`, `K_h <= K_c`).
  2. `CM_B2_PYTH_SESSION_NO_LOCK` & `CM_U1_PYTH_CLOSE_LOCK` (`0%`-Fee Session-Clock Locks):
     - Exact NYSE (`6.5h/day` Mon-Fri) & CME/ICE (`23h/day` Sun 18:00 - Fri 17:00 ET) trading-session
       variance clock (`eff_session_hours`), avoiding wall-clock weekend/overnight vol distortion.
     - Restricted strictly to exact instrument matches (never feeding COMEX futures into spot XAU/XAG).
  3. `B4_TOUCHED_BARRIER_WICK_LOCK` (`100%` WR Post-Breach Finalized-1m Wick Sweep):
     - Sweeps stale CLOB `YES` asks after finalized `1m` candle High/Low has deterministically
       breached strike `K` beyond a strict safety buffer (`>= 5 bps` Crypto, `>= 15 bps` Cash Equities).
  4. `SP1_NBA_ZERO_FEE_BOX` (`100%` WR Riskless `0%`-Fee NBA Full-Game Dominance Boxes):
     - Full-game Moneyline vs `+k.5` Spread ("Polish Middle"), Spread vs Spread (`L < U`), and
       Total `Over T_low + Under T_high` (`T_low < T_high`) with `$1.00` floor and `$2.00` middle.
  5. `NR0_ZERO_FEE_SLATE_ARB` (`100%` WR Riskless `0%`-Fee NegRisk Partition Underround):
     - Full-slate `YES` (`sum <= $0.988`) & `NO` complement (`sum <= (N-1) - $0.012`) across
       `elon-tweets`, `elon-tweets-48h`, `fomc`, `bank-of-japan`, and `bank-of-canada-decision`.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from src.polymarket_research.barrier_onetouch_svi_engine import (
    detect_barrier_monotonicity_boxes,
    first_passage_touch_prob,
)

logger = logging.getLogger("TradFiSportsZeroFee")

try:
    NY_TZ = ZoneInfo("America/New_York")
except Exception:
    NY_TZ = timezone(timedelta(hours=-4))

# (asset, yahoo_ticker, session_class, exact_directional_ok, basis_buffer_frac, vol_floor_annual)
PYTH_ASSET_CONFIG: Dict[str, Tuple[str, str, bool, float, float]] = {
    "WTI": ("CL=F", "CME_23H", True, 0.0045, 0.32),
    "NG": ("NG=F", "CME_23H", True, 0.0060, 0.48),
    "GC": ("GC=F", "CME_23H", True, 0.0020, 0.20),
    "SI": ("SI=F", "CME_23H", True, 0.0030, 0.32),
    # Spot XAUUSD / XAGUSD use GC=F / SI=F ONLY as ATM-filter anchor for 100%-riskless CM_B3 boxes
    "XAUUSD": ("GC=F", "CME_23H", False, 0.0150, 0.20),
    "XAGUSD": ("SI=F", "CME_23H", False, 0.0200, 0.32),
    "SPY": ("SPY", "EQUITY_RTH", True, 0.0015, 0.18),
    "NVDA": ("NVDA", "EQUITY_RTH", True, 0.0015, 0.42),
    "AMZN": ("AMZN", "EQUITY_RTH", True, 0.0015, 0.34),
    "GOOGL": ("GOOGL", "EQUITY_RTH", True, 0.0015, 0.34),
    "MSFT": ("MSFT", "EQUITY_RTH", True, 0.0015, 0.30),
    "META": ("META", "EQUITY_RTH", True, 0.0015, 0.38),
    "AAPL": ("AAPL", "EQUITY_RTH", True, 0.0015, 0.28),
    "TSLA": ("TSLA", "EQUITY_RTH", True, 0.0015, 0.52),
    "COIN": ("COIN", "EQUITY_RTH", True, 0.0020, 0.65),
    "HOOD": ("HOOD", "EQUITY_RTH", True, 0.0020, 0.58),
    "PLTR": ("PLTR", "EQUITY_RTH", True, 0.0020, 0.55),
}

PYTH_HIT_SERIES: Tuple[Tuple[str, str, str], ...] = (
    ("WTI", "MONTH", "crude-oil-cl-hit"),
    ("WTI", "WEEK", "wti-crude-oil-hit-price-weekly"),
    ("NG", "WEEK", "natural-gas-hit-price-weekly"),
    ("XAUUSD", "MONTH", "xauusd-hit-month"),
    ("XAUUSD", "WEEK", "gold-hit-price-weekly"),
    ("GC", "MONTH", "what-will-gold-gc-hit"),
    ("XAGUSD", "MONTH", "xagusd-hit-month"),
    ("XAGUSD", "WEEK", "silver-hit-price-weekly"),
    ("SI", "MONTH", "what-will-silver-si-hit"),
    ("SPY", "MONTH", "spy-hit-month"),
    ("SPY", "WEEK", "spy-hit-price-weekly"),
    ("NVDA", "MONTH", "nvidia-hit-price-monthly"),
    ("NVDA", "WEEK", "nvidia-hit-price-weekly"),
    ("AMZN", "WEEK", "amazon-hit-price-weekly"),
    ("GOOGL", "WEEK", "google-hit-price-weekly"),
    ("MSFT", "WEEK", "microsoft-hit-price-weekly"),
    ("META", "WEEK", "meta-hit-price-weekly"),
    ("AAPL", "WEEK", "apple-hit-price-weekly"),
    ("TSLA", "WEEK", "tesla-hit-price-weekly"),
    ("COIN", "MONTH", "coin-hit-month"),
    ("HOOD", "MONTH", "hood-hit-month"),
    ("PLTR", "WEEK", "palantir-hit-price-weekly"),
)

PYTH_CLOSE_SERIES: Tuple[Tuple[str, str], ...] = (
    ("SPY", "spy-daily-close-uo"),
    ("WTI", "wti-daily-close-uo"),
    ("MSFT", "msft-multi-strikes-weekly"),
    ("NVDA", "nvda-multi-strikes-weekly"),
    ("AAPL", "aapl-multi-strikes-weekly"),
    ("TSLA", "tsla-multi-strikes-weekly"),
    ("AMZN", "amzn-multi-strikes-weekly"),
    ("GOOGL", "googl-multi-strikes-weekly"),
    ("META", "meta-multi-strikes-weekly"),
    ("COIN", "coin-multi-strikes-weekly"),
    ("HOOD", "hood-multi-strikes-weekly"),
    ("PLTR", "pltr-multi-strikes-weekly"),
    ("NVDA", "nvda-above-on-daily"),
    ("TSLA", "tsla-above-on-daily"),
    ("AAPL", "aapl-above-on-daily"),
    ("MSFT", "msft-above-on-daily"),
    ("AMZN", "amzn-above-on-daily"),
    ("GOOGL", "googl-above-on-daily"),
    ("META", "meta-above-on-daily"),
    ("PLTR", "pltr-above-on-daily"),
)

NBA_SERIES_SLUGS: Tuple[str, ...] = ("nba-2026",)
MULTI_SPORT_CORRIDOR_SERIES: Tuple[Tuple[str, str], ...] = (
    ("NBA", "nba-2026"),
    ("NFL", "nfl-2026"),
    ("CFB", "cfb-2026"),
    ("NHL", "nhl-2026"),
)

ZERO_FEE_NEGRISK_SERIES: Tuple[str, ...] = (
    "elon-tweets",
    "elon-tweets-48h",
    "trump-truth-social",
    "fomc",
    "fed-3-parlay",
    "bank-of-japan",
    "bank-of-canada-decision",
    "reserve-bank-of-australia-decision",
    "reserve-bank-of-new-zealand-decision",
    "us-gas-price-daily",
    "best-ai-company",
    "chinese-ai-1",
)

_STRIKE_PRICE_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)")
_SPREAD_FAV_RE = re.compile(r"Spread:\s*(.+?)\s*\(\s*([-+]?\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)

_FEE_TYPE_FALLBACK_RATES: Dict[str, Tuple[float, float]] = {
    "sports_fees_nfl_cfb_oct26": (0.03, 1.0),
    "sports_fees_v2": (0.03, 1.0),
    "sports_fees_v3": (0.05, 1.0),
    "crypto_fees_v2": (0.07, 1.0),
    "crypto_15_min": (0.072, 1.0),
    "politics_fees": (0.04, 1.0),
    "weather_fees": (0.05, 1.0),
    "culture_fees": (0.05, 1.0),
    "economics_fees": (0.05, 1.0),
    "finance_prices_fees": (0.04, 1.0),
    "tech_fees": (0.04, 1.0),
    "mentions_fees": (0.05, 1.0),
    "general_fees": (0.04, 1.0),
}


def _extract_market_fee_rate(m: Dict[str, Any]) -> Tuple[float, float]:
    fee_type = str(m.get("feeType") or "").strip().lower()
    if fee_type == "zero_fees" or m.get("feesEnabled") is False:
        return 0.0, 1.0
    sched = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    if "rate" in sched and sched.get("rate") is not None:
        raw_rate = float(sched.get("rate") or 0.0)
        if raw_rate <= 0.0:
            return 0.0, 1.0
        return raw_rate, float(sched.get("exponent") or 1.0)
    if m.get("feeRate") is not None:
        fr_v = float(m.get("feeRate") or 0.0)
        if fr_v > 0.0:
            return (fr_v / 10000.0 if fr_v >= 1.0 else fr_v), float(m.get("feeExponent") or 1.0)
    if m.get("takerBaseFee") is not None:
        tb_v = float(m.get("takerBaseFee") or 0.0)
        if tb_v > 0.0:
            return (tb_v / 10000.0 if tb_v >= 1.0 else tb_v), float(m.get("feeExponent") or 1.0)
    if fee_type in _FEE_TYPE_FALLBACK_RATES:
        return _FEE_TYPE_FALLBACK_RATES[fee_type]
    if m.get("feesEnabled") is True and fee_type:
        return 0.04, 1.0
    return 0.0, 1.0


def _net_unit_ask(px: float, fee_rate: float = 0.0, fee_exponent: float = 1.0) -> float:
    """
    Exact USDC cost to acquire 1.0000 net share on-chain after Polymarket V2 share-deducted BUY fees:
    buying 1 gross share at `p` delivers `1 - h(p)` net shares where `h(p) = r * ((p*(1-p))**e) / p`,
    so 1.0000 net share costs `p / (1 - h(p))`.
    """
    p = float(px)
    r = float(fee_rate or 0.0)
    if r <= 0.0 or p <= 0.0 or p >= 1.0:
        return p
    fee_usdc_eq = r * ((p * (1.0 - p)) ** float(fee_exponent or 1.0))
    h = min(0.50, max(0.0, fee_usdc_eq / p))
    return p / (1.0 - h)


def _parse_clob_tokens(m: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    toks = m.get("clobTokenIds")
    if isinstance(toks, str):
        try:
            toks = json.loads(toks)
        except Exception:
            toks = None
    if isinstance(toks, list) and len(toks) >= 2 and toks[0] and toks[1]:
        return str(toks[0]), str(toks[1])
    return None


def _parse_iso_ts(raw_iso: Any) -> Optional[float]:
    s = str(raw_iso or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


@dataclass
class PythBarrierRungSpec:
    event_id: str
    market_id: str
    condition_id: str
    asset: str
    horizon_group: str  # "WEEK" or "MONTH"
    series_slug: str
    question: str
    strike: float
    direction: str  # "UP" or "DOWN"
    yes_token: str
    no_token: str
    start_ts: float
    end_ts: float
    fee_rate: float = 0.0
    fee_exponent: float = 1.0


@dataclass
class PythCloseRungSpec:
    event_id: str
    market_id: str
    condition_id: str
    asset: str
    series_slug: str
    question: str
    strike: float
    is_downward: bool
    yes_token: str
    no_token: str
    end_ts: float
    fee_rate: float = 0.0
    fee_exponent: float = 1.0


@dataclass
class NbaOutcomeLeg:
    market_id: str
    condition_id: str
    market_type: str  # "moneyline", "spreads", "totals"
    token_id: str
    opp_token_id: str
    side_index: int  # 0 or 1 in outcomes/clobTokenIds
    side_label: str  # "YES" for idx 0, "NO" for idx 1 (matches resolve_via_gamma_market)
    display_label: str
    # For margin markets: "GT" means M > threshold, "LT" means M < threshold (where M = Score(team_a) - Score(team_b))
    # For totals markets: "OVER" means S > threshold, "UNDER" means S < threshold
    relation: str
    threshold: float
    fee_rate: float = 0.0
    fee_exponent: float = 1.0


@dataclass
class NbaGameSpec:
    event_id: str
    slug: str
    title: str
    team_a: str
    team_b: str
    tipoff_ts: float
    settle_est_ts: float
    margin_legs: List[NbaOutcomeLeg] = field(default_factory=list)
    total_legs: List[NbaOutcomeLeg] = field(default_factory=list)


@dataclass
class ZeroFeeNegRiskSlateSpec:
    event_id: str
    series_slug: str
    title: str
    end_ts: float
    brackets: List[Dict[str, Any]]  # market_id, condition_id, label, yes_token, no_token
    neg_risk_augmented: bool = False


def compute_effective_trading_hours(
    start_ts: float,
    end_ts: float,
    session_class: str = "EQUITY_RTH",
) -> float:
    """
    Computes exact active primary-exchange trading hours inside `[start_ts, end_ts]` in `America/New_York`:
      - `EQUITY_RTH`: Mon-Fri `09:30 - 16:00 ET` (`6.5h/day`, `0h` overnight & weekends).
      - `CME_23H`: Sun `18:00 ET` through Fri `17:00 ET` excluding daily `17:00 - 18:00 ET` break (`23h/day`).
    """
    if end_ts <= start_ts:
        return 0.0
    dt_s = datetime.fromtimestamp(start_ts, tz=NY_TZ)
    dt_e = datetime.fromtimestamp(end_ts, tz=NY_TZ)
    cur_date = dt_s.date()
    end_date = dt_e.date()
    total_sec = 0.0

    while cur_date <= end_date:
        wd = cur_date.weekday()  # Mon=0 .. Sun=6
        day_anchor = datetime(cur_date.year, cur_date.month, cur_date.day, 0, 0, tzinfo=NY_TZ)
        windows: List[Tuple[datetime, datetime]] = []
        if session_class == "EQUITY_RTH":
            if wd < 5:
                windows.append((
                    day_anchor.replace(hour=9, minute=30),
                    day_anchor.replace(hour=16, minute=0),
                ))
        else:
            # CME / ICE 23h schedule:
            # Mon-Thu: [00:00, 17:00] + [18:00, 24:00]; Fri: [00:00, 17:00]; Sat: closed; Sun: [18:00, 24:00]
            if wd < 4:
                windows.append((day_anchor, day_anchor.replace(hour=17, minute=0)))
                windows.append((day_anchor.replace(hour=18, minute=0), day_anchor + timedelta(days=1)))
            elif wd == 4:
                windows.append((day_anchor, day_anchor.replace(hour=17, minute=0)))
            elif wd == 6:
                windows.append((day_anchor.replace(hour=18, minute=0), day_anchor + timedelta(days=1)))

        for w0, w1 in windows:
            lo = max(start_ts, w0.timestamp())
            hi = min(end_ts, w1.timestamp())
            if hi > lo:
                total_sec += hi - lo
        cur_date += timedelta(days=1)

    return total_sec / 3600.0


def is_same_continuous_session(now_ts: float, end_ts: float, session_class: str = "EQUITY_RTH") -> bool:
    """
    Verifies ZERO overnight, weekend, or after-hours earnings gaps exist between `now_ts` and `end_ts`:
      - `EQUITY_RTH`: `now_ts` must be inside active Mon-Fri `09:30 - 16:00 ET` on the EXACT same NY
        trading date as `end_ts` (eliminates all post-close / pre-open earnings gap risk!).
      - `CME_23H`: `0 < (end_ts - now_ts) <= 4.0h` with active trading hours matching wall clock (`>= 98%`).
    """
    if end_ts <= now_ts:
        return False
    eff_h = compute_effective_trading_hours(now_ts, end_ts, session_class)
    if eff_h <= 0.0:
        return False
    if session_class == "EQUITY_RTH":
        dt_n = datetime.fromtimestamp(now_ts, tz=NY_TZ)
        dt_e = datetime.fromtimestamp(end_ts, tz=NY_TZ)
        if dt_n.weekday() >= 5 or dt_n.date() != dt_e.date():
            return False
        mins_n = dt_n.hour * 60 + dt_n.minute
        return (9 * 60 + 30) <= mins_n < (16 * 60)
    wall_h = (end_ts - now_ts) / 3600.0
    return wall_h <= 4.0 and eff_h >= 0.98 * wall_h


_MONTH_NAME_MAP: Dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_NAMED_WEEK_RE = re.compile(
    r"(?:week\s+of|trading\s+session\s+of)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:,?\s*(\d{4}))?",
    re.IGNORECASE,
)
_NAMED_MONTH_RE = re.compile(
    r"(?:\bin\s+|trading\s+session\s+of\s+)(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(\d{4}))?(?:\?|\b)",
    re.IGNORECASE,
)


def infer_named_period_start_ts(question: str, desc: str, end_ts: float) -> float:
    """
    Infers the authoritative observation-window start timestamp in `America/New_York` for pre-listed
    weekly/monthly barrier markets (e.g., `"hit $100 in November?"` listed on Oct 25 only counts
    sessions of November, never October candles!).
    """
    blob = f"{question} {desc}"
    ref_yr = datetime.fromtimestamp(max(0.0, float(end_ts) - 5 * 86400.0), tz=NY_TZ).year
    m_wk = _NAMED_WEEK_RE.search(blob)
    if m_wk:
        mo = _MONTH_NAME_MAP[m_wk.group(1).lower()]
        dy = int(m_wk.group(2))
        yr = int(m_wk.group(3)) if m_wk.group(3) else ref_yr
        try:
            dt0 = datetime(yr, mo, dy, 0, 0, tzinfo=NY_TZ)
            # Monday CME session opens Sunday 18:00 ET (-6h)
            return (dt0 - timedelta(hours=6 if dt0.weekday() == 0 else 0)).timestamp()
        except ValueError:
            return 0.0
    m_mo = _NAMED_MONTH_RE.search(blob)
    if m_mo:
        mo = _MONTH_NAME_MAP[m_mo.group(1).lower()]
        yr = int(m_mo.group(2)) if m_mo.group(2) else ref_yr
        try:
            return datetime(yr, mo, 1, 0, 0, tzinfo=NY_TZ).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def parse_pyth_hit_event(
    ev: Dict[str, Any],
    asset: str,
    horizon_group: str,
    series_slug: str,
) -> List[PythBarrierRungSpec]:
    """Parses `zero_fees` Pyth 1-minute barrier hit events (`↑ $K` / `↓ $K`)."""
    mkts = ev.get("markets") or []
    ev_id = str(ev.get("id") or "")
    ev_start = _parse_iso_ts(ev.get("startDate") or ev.get("createdAt")) or (time.time() - 86400.0)
    ev_end = _parse_iso_ts(ev.get("endDate"))
    out: List[PythBarrierRungSpec] = []

    for m in mkts:
        if m.get("closed") or m.get("archived"):
            continue
        fee_rate, fee_exp = _extract_market_fee_rate(m)
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        desc = str(m.get("description") or ev.get("description") or "").lower()
        if "pyth" not in desc and "trading session" not in desc and "regular trading hours" not in desc:
            continue
        q = str(m.get("question") or "")
        git = str(m.get("groupItemTitle") or "")
        ql = (git + " " + q).lower()
        if "↑" in git or "(high)" in ql or "hit above" in ql:
            direction = "UP"
        elif "↓" in git or "(low)" in ql or "dip" in ql or "hit below" in ql:
            direction = "DOWN"
        else:
            continue
        m_px = _STRIKE_PRICE_RE.search(git) or _STRIKE_PRICE_RE.search(q)
        if not m_px:
            continue
        try:
            strike = float(m_px.group(1).replace(",", ""))
        except ValueError:
            continue
        if strike <= 0.0:
            continue
        end_ts = _parse_iso_ts(m.get("endDate")) or ev_end
        raw_m_start = _parse_iso_ts(m.get("startDate") or m.get("createdAt")) or ev_start
        if not end_ts:
            continue
        m_buf = 60.0 if (raw_m_start > ev_start + 300.0 or "creation of this market" in desc) else 0.0
        named_start = infer_named_period_start_ts(q or str(ev.get("title") or ""), desc, float(end_ts))
        start_ts = max(ev_start, named_start, min(float(end_ts) - 60.0, float(raw_m_start) + m_buf))
        out.append(
            PythBarrierRungSpec(
                event_id=ev_id,
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                asset=asset.upper(),
                horizon_group=horizon_group.upper(),
                series_slug=series_slug,
                question=q or git,
                strike=strike,
                direction=direction,
                yes_token=toks[0],
                no_token=toks[1],
                start_ts=float(start_ts),
                end_ts=float(end_ts),
                fee_rate=fee_rate,
                fee_exponent=fee_exp,
            )
        )
    return out


def parse_pyth_close_event(
    ev: Dict[str, Any],
    asset: str,
    series_slug: str,
) -> List[PythCloseRungSpec]:
    """Parses Pyth regular-session Close digital multi-strike ladders (preserving per-market dynamic fees)."""
    mkts = ev.get("markets") or []
    ev_id = str(ev.get("id") or "")
    ev_end = _parse_iso_ts(ev.get("endDate"))
    out: List[PythCloseRungSpec] = []
    for m in mkts:
        if m.get("closed") or m.get("archived"):
            continue
        fee_rate, fee_exp = _extract_market_fee_rate(m)
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        desc = str(m.get("description") or ev.get("description") or "").lower()
        if "pyth" not in desc:
            continue
        q = str(m.get("question") or "")
        git = str(m.get("groupItemTitle") or "")
        ql = q.lower()
        is_down = ("below" in ql or "under" in ql) and ("above" not in ql)
        if not is_down and "above" not in ql and "over" not in ql:
            continue
        m_px = _STRIKE_PRICE_RE.search(git) or _STRIKE_PRICE_RE.search(q)
        if not m_px:
            continue
        try:
            strike = float(m_px.group(1).replace(",", ""))
        except ValueError:
            continue
        end_ts = _parse_iso_ts(m.get("endDate")) or ev_end
        if not end_ts or strike <= 0.0:
            continue
        out.append(
            PythCloseRungSpec(
                event_id=ev_id,
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                asset=asset.upper(),
                series_slug=series_slug,
                question=q or git,
                strike=strike,
                is_downward=is_down,
                yes_token=toks[0],
                no_token=toks[1],
                end_ts=float(end_ts),
                fee_rate=fee_rate,
                fee_exponent=fee_exp,
            )
        )
    out.sort(key=lambda r: r.strike)
    return out


def fetch_yahoo_1m_intraday_sync(
    yahoo_symbol: str,
    vol_floor_annual: float = 0.25,
    timeout: float = 6.0,
) -> Optional[Dict[str, Any]]:
    """
    Fetches 5-day 1-minute intraday OHLC bars from Yahoo Finance v8 chart API.
    Strictly separates `spot` from finalized 1m bars (`bar_ts + 60 <= now_ts`) so unclosed
    bars never trigger finalized-1m barrier breach checks.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(yahoo_symbol)}?interval=1m&range=5d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
        res0 = ((raw.get("chart") or {}).get("result") or [None])[0] or {}
        meta = res0.get("meta") or {}
        spot = float(meta.get("regularMarketPrice") or 0.0)
        ts_arr = res0.get("timestamp") or []
        q0 = (((res0.get("indicators") or {}).get("quote") or [None])[0]) or {}
        h_arr = q0.get("high") or []
        l_arr = q0.get("low") or []
        c_arr = q0.get("close") or []
        now_ts = time.time()
        bars: List[Tuple[int, float, float, float]] = []
        for idx, t_v in enumerate(ts_arr):
            if idx >= len(h_arr) or idx >= len(l_arr) or idx >= len(c_arr):
                continue
            hi, lo, cl = h_arr[idx], l_arr[idx], c_arr[idx]
            if hi is None or lo is None or cl is None:
                continue
            t_int = int(t_v)
            if t_int + 60 <= now_ts and float(cl) > 0:
                bars.append((t_int, float(hi), float(lo), float(cl)))
        if spot <= 0.0 and bars:
            spot = bars[-1][3]
        if spot <= 0.0:
            return None

        # Compute realized session volatility from consecutive 1m log returns (ignoring overnight gaps > 5m)
        rets_sq: List[float] = []
        for i in range(max(1, len(bars) - 390), len(bars)):
            dt_b = bars[i][0] - bars[i - 1][0]
            if 45 <= dt_b <= 180 and bars[i - 1][3] > 0:
                r = math.log(bars[i][3] / bars[i - 1][3])
                rets_sq.append(r * r)
        if len(rets_sq) >= 20:
            var_1m = sum(rets_sq) / len(rets_sq)
            # Annualize on 252 trading days * 390 RTH minutes = 98,280 trading minutes/year
            rv_ann = math.sqrt(var_1m * 98280.0)
        else:
            rv_ann = vol_floor_annual
        sigma_session = max(vol_floor_annual, min(2.0, rv_ann * 1.10))
        return {
            "spot": spot,
            "sigma_session": round(sigma_session, 4),
            "bars": bars,
            "fetched_ts": now_ts,
        }
    except Exception as exc:
        logger.debug(f"Yahoo 1m fetch notice ({yahoo_symbol}): {exc}")
        return None


def window_extremes_from_bars(
    bars: List[Tuple[int, float, float, float]],
    start_ts: float,
    end_ts: float,
) -> Optional[Tuple[float, float]]:
    sub = [b for b in bars if start_ts <= float(b[0]) <= end_ts]
    if not sub:
        return None
    return max(b[1] for b in sub), min(b[2] for b in sub)


def detect_pyth_calendar_inclusion_boxes(
    quote_rows: List[Dict[str, Any]],
    max_box_cost_net: float = 0.994,
    now_ts: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Same-Oracle Calendar Inclusion Box (`NO(Short, K) + YES(Long, K) <= max_box_cost_net`):
    Whenever both windows are active (`start_short <= now_ts` and `start_long <= now_ts`),
    `start_long <= start_short` (epsilon tolerance), and `end_short < end_long - 3600` on the identical
    `0%`-fee `(asset, direction, strike)`, hitting `K` in `Short` implies hitting `K` in `Long`.
    """
    now_v = float(now_ts if now_ts is not None else time.time())
    by_key: Dict[Tuple[str, str, float], List[Dict[str, Any]]] = {}
    for q in quote_rows:
        if float(q.get("start_ts", 0.0)) > now_v:
            continue
        by_key.setdefault((str(q["asset"]), str(q["direction"]), round(float(q["strike"]), 4)), []).append(q)

    arbs: List[Dict[str, Any]] = []
    for (asset, direction, strike), grp in by_key.items():
        if len(grp) < 2:
            continue
        grp_s = sorted(grp, key=lambda x: float(x["end_ts"]))
        for i in range(len(grp_s)):
            for j in range(i + 1, len(grp_s)):
                q_s, q_l = grp_s[i], grp_s[j]
                if float(q_l["end_ts"]) - float(q_s["end_ts"]) < 3600.0:
                    continue
                # Long/YES window must start no later than Short/NO (a later Long start leaves an
                # uncovered gap where Short can hit K but Long cannot) -> epsilon tolerance only.
                if float(q_l["start_ts"]) > float(q_s["start_ts"]) + 1e-6:
                    continue
                ask_n_s = q_s.get("ask_no")
                ask_y_l = q_l.get("ask_yes")
                if ask_n_s is None or ask_y_l is None:
                    continue
                cost_gross = round(float(ask_n_s) + float(ask_y_l), 4)
                cost = round(
                    _net_unit_ask(float(ask_n_s), float(q_s.get("fee_rate", 0.0)), float(q_s.get("fee_exponent", 1.0)))
                    + _net_unit_ask(float(ask_y_l), float(q_l.get("fee_rate", 0.0)), float(q_l.get("fee_exponent", 1.0))),
                    4,
                )
                if cost <= max_box_cost_net:
                    arbs.append({
                        "box_kind": "PYTH_CALENDAR_INCLUSION",
                        "asset": asset,
                        "direction": direction,
                        "strike": strike,
                        "box_cost_net": cost,
                        "box_cost_gross": cost_gross,
                        "yes_row": q_l,
                        "no_row": q_s,
                        "close_ts": float(q_l["end_ts"]),
                        "label": f"NO_SHORT({direction} {strike}) + YES_LONG({direction} {strike})",
                    })
    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


def detect_pyth_close_vs_hit_boxes(
    close_rows: List[Dict[str, Any]],
    hit_rows: List[Dict[str, Any]],
    now_ts: float,
    max_box_cost_net: float = 0.994,
) -> List[Dict[str, Any]]:
    """
    Same-Oracle Path-vs-Terminal Inclusion Box:
    For upward digital `Closes > K_close` at `end_c` inside upward barrier `Hits >= K_hit` (`[start_h, end_h]`)
    with `K_hit <= K_close` and `start_h <= now_ts < end_c <= end_h + 60`:
      `Close > K_close` => final 1m RTH candle `High >= Close > K_hit` => `Hit >= K_hit` is TRUE!
      Hence `NO(Close > K_close) + YES(Hit >= K_hit) >= $1.00` deterministically (`$2.00` on touch-and-fade!).
    """
    arbs: List[Dict[str, Any]] = []
    for qc in close_rows:
        if qc.get("is_downward") or qc.get("ask_no") is None:
            continue
        end_c = float(qc["end_ts"])
        k_c = float(qc["strike"])
        for qh in hit_rows:
            if (
                qh["asset"] != qc["asset"]
                or qh["direction"] != "UP"
                or qh.get("ask_yes") is None
            ):
                continue
            k_h = float(qh["strike"])
            if k_h > k_c + 1e-6:
                continue
            if not (float(qh["start_ts"]) <= now_ts and now_ts < end_c <= float(qh["end_ts"]) + 60.0):
                continue
            cost_gross = round(float(qc["ask_no"]) + float(qh["ask_yes"]), 4)
            cost = round(
                _net_unit_ask(float(qc["ask_no"]), float(qc.get("fee_rate", 0.0)), float(qc.get("fee_exponent", 1.0)))
                + _net_unit_ask(float(qh["ask_yes"]), float(qh.get("fee_rate", 0.0)), float(qh.get("fee_exponent", 1.0))),
                4,
            )
            if cost <= max_box_cost_net:
                arbs.append({
                    "box_kind": "PYTH_CLOSE_VS_HIT",
                    "asset": str(qc["asset"]),
                    "strike_hit": k_h,
                    "strike_close": k_c,
                    "box_cost_net": cost,
                    "box_cost_gross": cost_gross,
                    "yes_row": qh,
                    "no_row": qc,
                    "close_ts": max(end_c, float(qh["end_ts"])),
                    "label": f"NO(Close>{k_c:g}) + YES(Hit>={k_h:g})",
                })
    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


def evaluate_pyth_session_barrier_no_lock(
    spot: float,
    strike: float,
    direction: str,
    eff_session_hours: float,
    sigma_session: float,
    basis_buffer_frac: float,
) -> Dict[str, Any]:
    """
    Computes conservative trading-session-clock `NO` lock probability on `0%`-fee Pyth barriers.
    Shifts `spot` adversely by `basis_buffer_frac` before computing first-passage touch probability.
    """
    if spot <= 0.0 or strike <= 0.0 or eff_session_hours <= 0.0:
        return {"p_touch": 1.0, "p_no": 0.0}
    if direction == "UP":
        adj_spot = spot * (1.0 + basis_buffer_frac)
        if adj_spot >= strike:
            return {"p_touch": 1.0, "p_no": 0.0}
    else:
        adj_spot = spot * (1.0 - basis_buffer_frac)
        if adj_spot <= strike:
            return {"p_touch": 1.0, "p_no": 0.0}
    # Convert active trading hours (`252 * 6.5h = 1638h/yr` for equities; use conservative `1638h` denominator)
    eff_tte_sec = (eff_session_hours / 1638.0) * (365.25 * 86400.0)
    p_touch = first_passage_touch_prob(
        spot=adj_spot,
        strike=strike,
        tte_seconds=eff_tte_sec,
        iv_annual=sigma_session,
        direction=direction,
        wick_vol_multiplier=1.15,
    )
    return {"p_touch": round(p_touch, 5), "p_no": round(1.0 - p_touch, 5)}


def evaluate_pyth_session_close_lock(
    spot: float,
    strike: float,
    is_downward: bool,
    eff_session_hours: float,
    sigma_session: float,
    basis_buffer_frac: float,
) -> Dict[str, Any]:
    """Evaluates final-45m regular-session terminal digital lock using Student-t/Gaussian tail cushion."""
    if spot <= 0.0 or strike <= 0.0 or eff_session_hours <= 0.0:
        return {"eligible": False, "side": "YES", "p_lock": 0.5, "z_session": 0.0}
    win_above = spot > strike
    adj_spot = spot * (1.0 - basis_buffer_frac if win_above else 1.0 + basis_buffer_frac)
    if (win_above and adj_spot <= strike) or ((not win_above) and adj_spot >= strike):
        return {"eligible": False, "side": "YES", "p_lock": 0.5, "z_session": 0.0}
    tau_yr = max(1e-6, eff_session_hours / 1638.0)
    sig_tau = max(0.0012, sigma_session * math.sqrt(tau_yr))
    z = abs(math.log(adj_spot / strike)) / sig_tau
    # Fat-tail conservative blend: 85% Gaussian + 15% Cauchy-like heavy-tail penalty
    p_gauss = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    p_heavy = 0.5 + math.atan(z) / math.pi
    p_lock = min(0.994, 0.85 * p_gauss + 0.15 * p_heavy)
    if is_downward:
        side = "NO" if win_above else "YES"
    else:
        side = "YES" if win_above else "NO"
    return {
        "eligible": bool(z >= 2.15 and p_lock >= 0.955),
        "side": side,
        "p_lock": round(p_lock, 4),
        "z_session": round(z, 3),
    }


def _norm_team(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip()).lower()


def _is_half_integer(val: float) -> bool:
    scaled = abs(float(val)) * 2.0
    return abs(scaled - round(scaled)) < 1e-4 and (int(round(scaled)) % 2 == 1)


def parse_nba_zero_fee_event(ev: Dict[str, Any], now_ts: Optional[float] = None) -> Optional[NbaGameSpec]:
    """
    Parses a full-game `zero_fees` NBA event (`nba-2026`) into canonical margin & total dominance legs.
    Strictly accepts ONLY `sportsMarketType in ("moneyline", "spreads", "totals")` with `fee_rate == 0.0`
    and half-integer spread/total lines (`*.5`), guaranteeing zero pushes and zero full-game ties (NBA OT).
    """
    now = float(now_ts if now_ts is not None else time.time())
    if ev.get("closed") or ev.get("archived"):
        return None
    mkts = ev.get("markets") or []
    if len(mkts) < 3:
        return None

    # Locate full-game moneyline first to anchor canonical `(team_a, team_b)`
    ml_mkt: Optional[Dict[str, Any]] = None
    ml_fr, ml_fe = 0.0, 1.0
    for m in mkts:
        if str(m.get("sportsMarketType") or "").strip().lower() == "moneyline" and not m.get("closed"):
            if _parse_clob_tokens(m):
                ml_fr, ml_fe = _extract_market_fee_rate(m)
                ml_mkt = m
                break
    if ml_mkt is None:
        return None

    raw_outs = ml_mkt.get("outcomes")
    if isinstance(raw_outs, str):
        try:
            raw_outs = json.loads(raw_outs)
        except Exception:
            raw_outs = None
    if not isinstance(raw_outs, list) or len(raw_outs) < 2:
        return None
    team_a = str(raw_outs[0]).strip()
    team_b = str(raw_outs[1]).strip()
    norm_a, norm_b = _norm_team(team_a), _norm_team(team_b)
    if not norm_a or not norm_b or norm_a == norm_b:
        return None

    ml_toks = _parse_clob_tokens(ml_mkt)
    assert ml_toks is not None
    tip_ts = _parse_iso_ts(ml_mkt.get("gameStartTime") or ev.get("endDate")) or (now + 7200.0)
    # NBA games remain tradable in-play for ~2.5-3h after tipoff; ignore stale events >6h past tipoff
    if now > tip_ts + 6.0 * 3600.0:
        return None
    settle_est_ts = max(tip_ts + 3.25 * 3600.0, now + 1800.0)

    margin_legs: List[NbaOutcomeLeg] = [
        NbaOutcomeLeg(
            market_id=str(ml_mkt.get("id") or ""),
            condition_id=str(ml_mkt.get("conditionId") or ""),
            market_type="moneyline",
            token_id=ml_toks[0],
            opp_token_id=ml_toks[1],
            side_index=0,
            side_label="YES",
            display_label=f"{team_a} ML",
            relation="GT",
            threshold=0.0,
            fee_rate=ml_fr,
            fee_exponent=ml_fe,
        ),
        NbaOutcomeLeg(
            market_id=str(ml_mkt.get("id") or ""),
            condition_id=str(ml_mkt.get("conditionId") or ""),
            market_type="moneyline",
            token_id=ml_toks[1],
            opp_token_id=ml_toks[0],
            side_index=1,
            side_label="NO",
            display_label=f"{team_b} ML",
            relation="LT",
            threshold=0.0,
            fee_rate=ml_fr,
            fee_exponent=ml_fe,
        ),
    ]
    total_legs: List[NbaOutcomeLeg] = []

    for m in mkts:
        if m.get("closed") or m.get("archived"):
            continue
        smt = str(m.get("sportsMarketType") or "").strip().lower()
        if smt not in ("spreads", "totals"):
            continue
        fr, fe = _extract_market_fee_rate(m)
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        outs = m.get("outcomes")
        if isinstance(outs, str):
            try:
                outs = json.loads(outs)
            except Exception:
                outs = None
        if not isinstance(outs, list) or len(outs) < 2:
            continue
        q_str = str(m.get("question") or "")
        if any(bad in q_str.lower() for bad in ("1h ", "2h ", "1q ", "2q ", "3q ", "4q ", "half", "quarter")):
            continue

        if smt == "spreads":
            m_sp = _SPREAD_FAV_RE.search(q_str)
            if not m_sp:
                continue
            fav_team = _norm_team(m_sp.group(1))
            line_val = float(m_sp.group(2))
            if line_val >= 0.0 or not _is_half_integer(line_val):
                continue
            k_abs = abs(line_val)
            out0, out1 = _norm_team(outs[0]), _norm_team(outs[1])
            if fav_team == norm_a and out0 == norm_a and out1 == norm_b:
                # idx 0 = team_a -k_abs (wins iff M > +k_abs); idx 1 = team_b +k_abs (wins iff M < +k_abs)
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[0], toks[1], 0, "YES", f"{team_a} -{k_abs:g}", "GT", k_abs, fr, fe))
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[1], toks[0], 1, "NO", f"{team_b} +{k_abs:g}", "LT", k_abs, fr, fe))
            elif fav_team == norm_b and out0 == norm_b and out1 == norm_a:
                # idx 0 = team_b -k_abs (wins iff M < -k_abs); idx 1 = team_a +k_abs (wins iff M > -k_abs)
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[0], toks[1], 0, "YES", f"{team_b} -{k_abs:g}", "LT", -k_abs, fr, fe))
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[1], toks[0], 1, "NO", f"{team_a} +{k_abs:g}", "GT", -k_abs, fr, fe))

        elif smt == "totals":
            raw_line = m.get("line")
            if raw_line is None:
                continue
            t_line = float(raw_line)
            if t_line <= 50.0 or not _is_half_integer(t_line):
                continue
            if _norm_team(outs[0]) == "over" and _norm_team(outs[1]) == "under":
                total_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "totals", toks[0], toks[1], 0, "YES", f"Over {t_line:g}", "OVER", t_line, fr, fe))
                total_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "totals", toks[1], toks[0], 1, "NO", f"Under {t_line:g}", "UNDER", t_line, fr, fe))

    return NbaGameSpec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        title=str(ev.get("title") or f"{team_a} vs. {team_b}"),
        team_a=team_a,
        team_b=team_b,
        tipoff_ts=tip_ts,
        settle_est_ts=settle_est_ts,
        margin_legs=margin_legs,
        total_legs=total_legs,
    )


def detect_nba_dominance_boxes(
    spec: NbaGameSpec,
    best_asks_by_token: Dict[str, float],
    max_box_cost_net: float = 1.20,
) -> List[Dict[str, Any]]:
    """
    Finds all `0%`-fee NBA full-game dominance boxes (`L < U`):
      1. Margin Polish Middle / Spread Monotonicity: `(M > L) + (M < U)` with `L < U` and distinct `market_id`.
         Guaranteed payout = `$1.00` for all `M`, plus `$2.00` middle on integers in `(L, U)`.
      2. Total O/U Middle / Monotonicity: `(S > T_low) + (S < T_high)` with `T_low < T_high`.
         Guaranteed payout = `$1.00` for all `S`, plus `$2.00` middle on integers in `(T_low, T_high)`.
    """
    candidates: List[Dict[str, Any]] = []
    gt_legs = [lg for lg in spec.margin_legs if lg.relation == "GT" and lg.token_id in best_asks_by_token]
    lt_legs = [lg for lg in spec.margin_legs if lg.relation == "LT" and lg.token_id in best_asks_by_token]
    for lg_a in gt_legs:
        a_px = float(best_asks_by_token[lg_a.token_id])
        if not (0.01 <= a_px <= 0.99):
            continue
        a_net = _net_unit_ask(a_px, lg_a.fee_rate, lg_a.fee_exponent)
        for lg_b in lt_legs:
            if lg_a.market_id == lg_b.market_id or lg_a.threshold >= lg_b.threshold - 1e-6:
                continue
            b_px = float(best_asks_by_token[lg_b.token_id])
            if not (0.01 <= b_px <= 0.99):
                continue
            cost_gross = round(a_px + b_px, 4)
            cost = round(a_net + _net_unit_ask(b_px, lg_b.fee_rate, lg_b.fee_exponent), 4)
            if cost <= max_box_cost_net:
                mid_pts = round(lg_b.threshold - lg_a.threshold, 1)
                candidates.append({
                    "box_kind": "NBA_POLISH_MIDDLE" if ("ML" in lg_a.display_label or "ML" in lg_b.display_label) else "NBA_SPREAD_MONO",
                    "event_id": spec.event_id,
                    "title": spec.title,
                    "box_cost_net": cost,
                    "box_cost_gross": cost_gross,
                    "middle_width_pts": mid_pts,
                    "leg_a": lg_a,
                    "leg_b": lg_b,
                    "close_ts": spec.settle_est_ts,
                    "label": f"{lg_a.display_label} + {lg_b.display_label}",
                })

    ov_legs = [lg for lg in spec.total_legs if lg.relation == "OVER" and lg.token_id in best_asks_by_token]
    un_legs = [lg for lg in spec.total_legs if lg.relation == "UNDER" and lg.token_id in best_asks_by_token]
    for lg_o in ov_legs:
        o_px = float(best_asks_by_token[lg_o.token_id])
        if not (0.01 <= o_px <= 0.99):
            continue
        o_net = _net_unit_ask(o_px, lg_o.fee_rate, lg_o.fee_exponent)
        for lg_u in un_legs:
            if lg_o.market_id == lg_u.market_id or lg_o.threshold >= lg_u.threshold - 1e-6:
                continue
            u_px = float(best_asks_by_token[lg_u.token_id])
            if not (0.01 <= u_px <= 0.99):
                continue
            cost_gross = round(o_px + u_px, 4)
            cost = round(o_net + _net_unit_ask(u_px, lg_u.fee_rate, lg_u.fee_exponent), 4)
            if cost <= max_box_cost_net:
                candidates.append({
                    "box_kind": "NBA_TOTAL_MONO",
                    "event_id": spec.event_id,
                    "title": spec.title,
                    "box_cost_net": cost,
                    "box_cost_gross": cost_gross,
                    "middle_width_pts": round(lg_u.threshold - lg_o.threshold, 1),
                    "leg_a": lg_o,
                    "leg_b": lg_u,
                    "close_ts": spec.settle_est_ts,
                    "label": f"{lg_o.display_label} + {lg_u.display_label}",
                })

    candidates.sort(key=lambda x: (float(x["box_cost_net"]), -float(x["middle_width_pts"])))
    return candidates


def parse_zero_fee_negrisk_slate(
    ev: Dict[str, Any], series_slug: str, allow_mixed_fees: bool = True
) -> Optional[ZeroFeeNegRiskSlateSpec]:
    """
    Parses a verified `negRisk=True` complete partition event (`elon-tweets`, `fomc`, `best-ai-company`, etc.).
    Allows early-resolved `NO` brackets (e.g. `<40` tweets already exceeded) while rejecting the event
    if any bracket resolved `YES` or if any active sub-market lacks valid tokens.
    """
    if not ev.get("negRisk") or ev.get("closed") or ev.get("archived"):
        return None
    mkts = ev.get("markets") or []
    if len(mkts) < 3:
        return None
    end_ts = _parse_iso_ts(ev.get("endDate"))
    if not end_ts:
        return None

    open_brackets: List[Dict[str, Any]] = []
    for m in mkts:
        if m.get("archived"):
            continue
        if m.get("closed"):
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            # Only safe if closed bracket definitively resolved NO (`outcomePrices[1] >= 0.99`)
            if not (isinstance(op, list) and len(op) >= 2 and float(op[1]) >= 0.99):
                return None
            continue
        fr, fexp = _extract_market_fee_rate(m)
        if fr > 0.0 and not allow_mixed_fees:
            return None
        toks = _parse_clob_tokens(m)
        if not toks:
            return None
        open_brackets.append({
            "market_id": str(m.get("id") or ""),
            "condition_id": str(m.get("conditionId") or ""),
            "label": str(m.get("groupItemTitle") or m.get("question") or ""),
            "yes_token": toks[0],
            "no_token": toks[1],
            "fee_rate": fr,
            "fee_exponent": fexp,
            "rewards_min_size": float(m.get("rewardsMinSize") or 0.0),
            "rewards_max_spread": float(m.get("rewardsMaxSpread") or 0.0),
        })

    if len(open_brackets) < 3:
        return None
    return ZeroFeeNegRiskSlateSpec(
        event_id=str(ev.get("id") or ""),
        series_slug=series_slug,
        title=str(ev.get("title") or series_slug),
        end_ts=float(end_ts),
        brackets=open_brackets,
        neg_risk_augmented=bool(ev.get("negRiskAugmented", False)),
    )


@dataclass
class MultiSportCorridorLeg:
    market_id: str
    condition_id: str
    scope_key: str  # e.g. "FG:SPREAD", "1H:SPREAD", "Q1:SPREAD", "FG:TOTAL", "1H:TOTAL", "FG_TEAM:panthers"
    token_id: str
    opp_token_id: str
    side_index: int
    side_label: str  # "YES" for idx 0, "NO" for idx 1
    display_label: str
    relation: str  # "GT"/"LT" for spreads, "OVER"/"UNDER" for totals
    threshold: float
    fee_rate: float = 0.0
    fee_exponent: float = 1.0
    neg_risk: bool = False


@dataclass
class MultiSportCorridorSpec:
    event_id: str
    slug: str
    sport: str
    title: str
    team_a: str
    team_b: str
    start_ts: float
    settle_est_ts: float
    legs_by_scope: Dict[str, List[MultiSportCorridorLeg]] = field(default_factory=dict)

    @property
    def legs(self) -> List[MultiSportCorridorLeg]:
        return [lg for sc_lgs in self.legs_by_scope.values() for lg in sc_lgs]


_SPREAD_PERIOD_MAP: Dict[str, str] = {
    "spreads": "FG",
    "first_half_spreads": "1H",
    "second_half_spreads": "2H",
    "q1_spreads": "Q1",
    "q2_spreads": "Q2",
    "q3_spreads": "Q3",
    "q4_spreads": "Q4",
}

_TOTAL_PERIOD_MAP: Dict[str, str] = {
    "totals": "FG",
    "first_half_totals": "1H",
    "second_half_totals": "2H",
    "q1_totals": "Q1",
    "q2_totals": "Q2",
    "q3_totals": "Q3",
    "q4_totals": "Q4",
}

_TEAM_TOTAL_PERIOD_MAP: Dict[str, str] = {
    "team_totals": "FG_TEAM",
    "first_half_team_totals": "1H_TEAM",
    "second_half_team_totals": "2H_TEAM",
}


def _infer_sport_tag(ev: Dict[str, Any], sport_hint: str = "") -> str:
    if sport_hint:
        return sport_hint.upper()
    slug = str(ev.get("slug") or "").lower()
    for pfx, tag in (
        ("nba-", "NBA"),
        ("nfl-", "NFL"),
        ("cfb-", "CFB"),
        ("nhl-", "NHL"),
        ("mlb-", "MLB"),
        ("atp-", "TENNIS"),
        ("wta-", "TENNIS"),
        ("lol-", "ESPORTS"),
        ("cs2-", "ESPORTS"),
    ):
        if slug.startswith(pfx):
            return tag
    for s_obj in (ev.get("series") or []):
        if isinstance(s_obj, dict):
            s_sl = str(s_obj.get("slug") or "").lower()
            for kw, tag in (("nba", "NBA"), ("nfl", "NFL"), ("cfb", "CFB"), ("nhl", "NHL")):
                if kw in s_sl:
                    return tag
    return "SPORTS"


def parse_multi_sport_corridor_event(
    ev: Dict[str, Any],
    sport_hint: str = "",
    now_ts: Optional[float] = None,
    skip_nba_fg_zero_fee: bool = True,
) -> Optional[MultiSportCorridorSpec]:
    """
    Parses multi-market sports events (NBA 1H/2H/Q1..Q4/TeamTotals + NFL/CFB/NHL/Soccer/Esports FG & Period
    spreads/totals) into strictly scoped half-integer (`*.5`) dominance corridors.
    Never mixes periods, never mixes teams, and never uses 2-way moneylines on tie-capable periods/sports
    (half-integer spread hooks `M > L` + `M < U` with `L < U` cover `M == 0` ties 100% deterministically!).
    """
    now = float(now_ts if now_ts is not None else time.time())
    if ev.get("closed") or ev.get("archived") or ev.get("negRisk"):
        return None
    mkts = ev.get("markets") or []
    if len(mkts) < 4:
        return None
    sport = _infer_sport_tag(ev, sport_hint)

    team_a, team_b = "", ""
    start_ts: Optional[float] = None
    for smt_cand in ("moneyline", "spreads", "first_half_spreads"):
        for m in mkts:
            if m.get("closed") or str(m.get("sportsMarketType") or "").strip().lower() != smt_cand:
                continue
            outs = m.get("outcomes")
            if isinstance(outs, str):
                try:
                    outs = json.loads(outs)
                except Exception:
                    outs = None
            if isinstance(outs, list) and len(outs) == 2:
                o0, o1 = str(outs[0]).strip(), str(outs[1]).strip()
                if {_norm_team(o0), _norm_team(o1)} not in ({"yes", "no"}, {"over", "under"}) and _norm_team(o0) != _norm_team(o1):
                    team_a, team_b = o0, o1
                    start_ts = _parse_iso_ts(m.get("gameStartTime") or ev.get("startDate") or ev.get("endDate"))
                    break
        if team_a and team_b:
            break

    norm_a, norm_b = _norm_team(team_a), _norm_team(team_b)
    if start_ts is None:
        for m in mkts:
            start_ts = _parse_iso_ts(m.get("gameStartTime"))
            if start_ts:
                break
    if start_ts is None:
        start_ts = _parse_iso_ts(ev.get("endDate")) or (now + 7200.0)
    if now > start_ts + 6.5 * 3600.0:
        return None
    settle_est_ts = max(start_ts + 3.75 * 3600.0, now + 1800.0)

    legs_by_scope: Dict[str, List[MultiSportCorridorLeg]] = {}
    for m in mkts:
        if m.get("closed") or m.get("archived") or m.get("negRisk"):
            continue
        smt = str(m.get("sportsMarketType") or "").strip().lower()
        if smt not in _SPREAD_PERIOD_MAP and smt not in _TOTAL_PERIOD_MAP and smt not in _TEAM_TOTAL_PERIOD_MAP:
            continue
        fr, fexp = _extract_market_fee_rate(m)
        if skip_nba_fg_zero_fee and sport == "NBA" and fr == 0.0 and smt in ("spreads", "totals"):
            # Already handled by SP1_NBA_ZERO_FEE_BOX; keep zero overlap!
            continue
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        outs = m.get("outcomes")
        if isinstance(outs, str):
            try:
                outs = json.loads(outs)
            except Exception:
                outs = None
        if not isinstance(outs, list) or len(outs) < 2:
            continue
        q_str = str(m.get("question") or "")
        mid = str(m.get("id") or "")
        cid = str(m.get("conditionId") or "")

        if smt in _SPREAD_PERIOD_MAP:
            if not norm_a or not norm_b:
                continue
            per = _SPREAD_PERIOD_MAP[smt]
            if per == "FG" and any(bad in q_str.lower() for bad in ("1h ", "2h ", "1q ", "2q ", "3q ", "4q ", "half", "quarter")):
                continue
            m_sp = _SPREAD_FAV_RE.search(q_str)
            if not m_sp:
                continue
            named_team = _norm_team(m_sp.group(1))
            line_val = float(m_sp.group(2))
            if not _is_half_integer(line_val):
                continue
            out0, out1 = _norm_team(outs[0]), _norm_team(outs[1])
            if {out0, out1} != {norm_a, norm_b} or named_team not in (norm_a, norm_b):
                continue
            idx_named = 0 if out0 == named_team else 1
            idx_other = 1 - idx_named
            tok_named, tok_other = toks[idx_named], toks[idx_other]
            lbl_named = "YES" if idx_named == 0 else "NO"
            lbl_other = "YES" if idx_other == 0 else "NO"
            pfx = "" if per == "FG" else f"{per} "
            scope = f"{per}:SPREAD"
            if named_team == norm_a:
                # team_a + line_val > 0 <=> M > -line_val; team_b covers <=> M < -line_val
                thr = round(-line_val, 2)
                legs_by_scope.setdefault(scope, []).extend([
                    MultiSportCorridorLeg(mid, cid, scope, tok_named, tok_other, idx_named, lbl_named, f"{pfx}{team_a} {line_val:+g}", "GT", thr, fr, fexp, False),
                    MultiSportCorridorLeg(mid, cid, scope, tok_other, tok_named, idx_other, lbl_other, f"{pfx}{team_b} {-line_val:+g}", "LT", thr, fr, fexp, False),
                ])
            else:
                # team_b + line_val > 0 <=> -M + line_val > 0 <=> M < +line_val; team_a covers <=> M > +line_val
                thr = round(line_val, 2)
                legs_by_scope.setdefault(scope, []).extend([
                    MultiSportCorridorLeg(mid, cid, scope, tok_named, tok_other, idx_named, lbl_named, f"{pfx}{team_b} {line_val:+g}", "LT", thr, fr, fexp, False),
                    MultiSportCorridorLeg(mid, cid, scope, tok_other, tok_named, idx_other, lbl_other, f"{pfx}{team_a} {-line_val:+g}", "GT", thr, fr, fexp, False),
                ])

        elif smt in _TOTAL_PERIOD_MAP:
            per = _TOTAL_PERIOD_MAP[smt]
            if per == "FG" and any(bad in q_str.lower() for bad in ("1h ", "2h ", "1q ", "2q ", "3q ", "4q ", "half", "quarter", "team total")):
                continue
            raw_line = m.get("line")
            if raw_line is None:
                continue
            t_line = float(raw_line)
            if t_line <= 0.0 or not _is_half_integer(t_line):
                continue
            if _norm_team(outs[0]) != "over" or _norm_team(outs[1]) != "under":
                continue
            pfx = "" if per == "FG" else f"{per} "
            scope = f"{per}:TOTAL"
            legs_by_scope.setdefault(scope, []).extend([
                MultiSportCorridorLeg(mid, cid, scope, toks[0], toks[1], 0, "YES", f"{pfx}Over {t_line:g}", "OVER", t_line, fr, fexp, False),
                MultiSportCorridorLeg(mid, cid, scope, toks[1], toks[0], 1, "NO", f"{pfx}Under {t_line:g}", "UNDER", t_line, fr, fexp, False),
            ])

        elif smt in _TEAM_TOTAL_PERIOD_MAP:
            if not norm_a or not norm_b:
                continue
            raw_line = m.get("line")
            if raw_line is None:
                continue
            t_line = float(raw_line)
            if t_line <= 0.0 or not _is_half_integer(t_line):
                continue
            if _norm_team(outs[0]) != "over" or _norm_team(outs[1]) != "under":
                continue
            q_head = q_str.split("O/U")[0].lower() if "O/U" in q_str else q_str.lower()
            has_a = norm_a in q_head
            has_b = norm_b in q_head
            if has_a == has_b:
                continue
            tm_tag = norm_a if has_a else norm_b
            tm_disp = team_a if has_a else team_b
            per = _TEAM_TOTAL_PERIOD_MAP[smt]
            pfx = "" if per == "FG_TEAM" else f"{per.split('_')[0]} "
            scope = f"{per}:{tm_tag}"
            legs_by_scope.setdefault(scope, []).extend([
                MultiSportCorridorLeg(mid, cid, scope, toks[0], toks[1], 0, "YES", f"{pfx}{tm_disp} Over {t_line:g}", "OVER", t_line, fr, fexp, False),
                MultiSportCorridorLeg(mid, cid, scope, toks[1], toks[0], 1, "NO", f"{pfx}{tm_disp} Under {t_line:g}", "UNDER", t_line, fr, fexp, False),
            ])

    # Keep only scopes that have at least 2 distinct markets (4 legs) so corridor boxes can form
    valid_scopes = {
        sc: lgs for sc, lgs in legs_by_scope.items() if len({lg.market_id for lg in lgs}) >= 2
    }
    if not valid_scopes:
        return None
    return MultiSportCorridorSpec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        sport=sport,
        title=str(ev.get("title") or f"{team_a} vs. {team_b}"),
        team_a=team_a,
        team_b=team_b,
        start_ts=float(start_ts),
        settle_est_ts=float(settle_est_ts),
        legs_by_scope=valid_scopes,
    )


def detect_multi_sport_corridor_boxes(
    spec: MultiSportCorridorSpec,
    best_asks_by_token: Dict[str, float],
    max_box_cost_net: float = 1.08,
) -> List[Dict[str, Any]]:
    """
    Detects fee-exact, period-exact Dominance & Polish-Middle Boxes across all scopes of `spec`:
      - Spreads (`GT` threshold `L` + `LT` threshold `U` with `L < U`, half-integer hooks -> zero OT tie risk)
      - Totals & Team Totals (`OVER` threshold `L` + `UNDER` threshold `U` with `L < U`, half-integer hooks -> zero push risk)
    """
    candidates: List[Dict[str, Any]] = []
    for scope, legs in spec.legs_by_scope.items():
        if scope.endswith(":SPREAD"):
            low_rel, high_rel, kind_tag = "GT", "LT", "SPREAD_CORRIDOR"
        else:
            low_rel, high_rel, kind_tag = "OVER", "UNDER", "TOTAL_CORRIDOR"
        low_legs = [lg for lg in legs if lg.relation == low_rel and lg.token_id in best_asks_by_token]
        high_legs = [lg for lg in legs if lg.relation == high_rel and lg.token_id in best_asks_by_token]
        for lg_a in low_legs:
            a_px = float(best_asks_by_token[lg_a.token_id])
            if not (0.01 <= a_px <= 0.99):
                continue
            a_net = _net_unit_ask(a_px, lg_a.fee_rate, lg_a.fee_exponent)
            for lg_b in high_legs:
                if lg_a.market_id == lg_b.market_id or lg_a.threshold >= lg_b.threshold - 1e-6:
                    continue
                b_px = float(best_asks_by_token[lg_b.token_id])
                if not (0.01 <= b_px <= 0.99):
                    continue
                b_net = _net_unit_ask(b_px, lg_b.fee_rate, lg_b.fee_exponent)
                cost_net = round(a_net + b_net, 4)
                if cost_net <= max_box_cost_net:
                    candidates.append({
                        "box_kind": f"{spec.sport}_{kind_tag}",
                        "sport": spec.sport,
                        "scope": scope,
                        "event_id": spec.event_id,
                        "title": spec.title,
                        "box_cost_net": cost_net,
                        "box_cost_gross": round(a_px + b_px, 4),
                        "middle_width_pts": round(lg_b.threshold - lg_a.threshold, 1),
                        "leg_a": lg_a,
                        "leg_b": lg_b,
                        "close_ts": spec.settle_est_ts,
                        "label": f"{lg_a.display_label} + {lg_b.display_label}",
                    })
    candidates.sort(key=lambda x: (float(x["box_cost_net"]), -float(x["middle_width_pts"])))
    return candidates


@dataclass
class NegRiskConvertSlateSpec:
    event_id: str
    slug: str
    title: str
    neg_risk_market_id: str
    neg_risk_augmented: bool
    total_market_count: int
    is_closed_convert_safe: bool
    end_ts: float
    brackets: List[Dict[str, Any]]


def parse_negrisk_convert_event(ev: Dict[str, Any]) -> Optional[NegRiskConvertSlateSpec]:
    """
    Parses any open `NegRisk` event for:
      1. Universal 2-leg `NO_i + NO_j` mutual-exclusion dominance boxes (safe even when `negRiskAugmented=True`!),
      2. Closed-partition (`negRiskAugmented=False`) `NegRiskAdapter.convertPositions` `m`-leg `NO` arbitrage
         when all `N` event sub-markets are active and carry verified `0..N-1` `questionID` byte indices.
    """
    if ev.get("closed") or ev.get("archived"):
        return None
    if not (ev.get("enableNegRisk") or ev.get("negRisk")):
        return None
    mkts = ev.get("markets") or []
    if len(mkts) < 2:
        return None
    end_ts = _parse_iso_ts(ev.get("endDate"))
    if not end_ts:
        return None
    nr_mkt_id = str(ev.get("negRiskMarketID") or "").strip().lower()
    nr_aug = bool(ev.get("negRiskAugmented", True))
    valid_nr_hex = len(nr_mkt_id) == 66 and nr_mkt_id.startswith("0x")

    open_brackets: List[Dict[str, Any]] = []
    all_mkts_open = True
    has_placeholder = False
    _ph_re = re.compile(r"(?:\bplaceholder\b|^(?:person|party|option|candidate|team|player)\s+[a-z0-9]{1,2}$)", re.IGNORECASE)
    for m in mkts:
        lbl_raw = str(m.get("groupItemTitle") or m.get("question") or "").strip()
        if _ph_re.search(lbl_raw):
            has_placeholder = True
        if m.get("archived") or m.get("closed") or m.get("active") is False:
            all_mkts_open = False
            continue
        toks = _parse_clob_tokens(m)
        if not toks:
            all_mkts_open = False
            continue
        fr, fexp = _extract_market_fee_rate(m)
        q_id = str(m.get("questionID") or "").strip().lower()
        q_idx: Optional[int] = None
        if valid_nr_hex and len(q_id) == 66 and q_id.startswith("0x") and q_id[:64] == nr_mkt_id[:64]:
            try:
                q_idx = int(q_id[64:], 16)
            except ValueError:
                q_idx = None
        open_brackets.append({
            "market_id": str(m.get("id") or ""),
            "condition_id": str(m.get("conditionId") or ""),
            "question_id": q_id,
            "question_index": q_idx,
            "label": lbl_raw[:48],
            "yes_token": toks[0],
            "no_token": toks[1],
            "fee_rate": fr,
            "fee_exponent": fexp,
        })

    if len(open_brackets) < 2:
        return None
    total_n = len(mkts)
    idx_set = {b["question_index"] for b in open_brackets if isinstance(b.get("question_index"), int)}
    closed_safe = bool(
        (not nr_aug)
        and (not has_placeholder)
        and valid_nr_hex
        and all_mkts_open
        and 3 <= total_n <= 40
        and len(open_brackets) == total_n
        and idx_set == set(range(total_n))
    )
    if closed_safe:
        open_brackets.sort(key=lambda b: int(b["question_index"]))
    return NegRiskConvertSlateSpec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        title=str(ev.get("title") or ev.get("slug") or ""),
        neg_risk_market_id=nr_mkt_id,
        neg_risk_augmented=nr_aug,
        total_market_count=total_n,
        is_closed_convert_safe=closed_safe,
        end_ts=float(end_ts),
        brackets=open_brackets,
    )


def detect_negrisk_no_pair_boxes(
    spec: NegRiskConvertSlateSpec,
    best_no_asks: Dict[str, float],
    max_box_cost_net: float = 1.04,
) -> List[Dict[str, Any]]:
    """
    Universal 2-Leg `NO_i + NO_j` Mutual-Exclusion Dominance Box:
    In ANY `NegRisk` event (both `negRiskAugmented=False` and `negRiskAugmented=True`), at most ONE
    sub-market can resolve `YES`. Thus `NO_i + NO_j` pays `$1.00` if `i` or `j` wins and `$2.00` if ANY
    3rd outcome wins! Only brackets with `ask(NO) <= 0.96` can participate in a `< $1.04` pair, making
    pairwise scan O(1) even on 100-candidate election slates.
    """
    active = []
    for b in spec.brackets:
        nt = b["no_token"]
        if nt not in best_no_asks:
            continue
        px = float(best_no_asks[nt])
        if 0.01 <= px <= 0.985:
            active.append((b, px, _net_unit_ask(px, float(b["fee_rate"]), float(b["fee_exponent"]))))
    active.sort(key=lambda x: x[2])
    # Only the lowest-priced NO legs (co-favorites where YES is high) can sum <= max_box_cost_net
    shortlist = active[:12]
    arbs: List[Dict[str, Any]] = []
    for i in range(len(shortlist)):
        b_i, px_i, net_i = shortlist[i]
        for j in range(i + 1, len(shortlist)):
            b_j, px_j, net_j = shortlist[j]
            if b_i["market_id"] == b_j["market_id"]:
                continue
            cost_net = round(net_i + net_j, 4)
            if cost_net <= max_box_cost_net:
                arbs.append({
                    "mode": "NR_NO_PAIR_BOX",
                    "event_id": spec.event_id,
                    "slug": spec.slug,
                    "title": spec.title,
                    "box_cost_net": cost_net,
                    "box_cost_gross": round(px_i + px_j, 4),
                    "bracket_a": b_i,
                    "bracket_b": b_j,
                    "close_ts": spec.end_ts,
                    "label": f"NO[{b_i['label']}] + NO[{b_j['label']}]",
                })
    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


def _walk_side_exact_shares(
    levels_raw: List[Dict[str, Any]],
    shares_req: float,
    fee_rate: float,
    fee_exp: float,
    is_ask: bool,
) -> Optional[Dict[str, Any]]:
    lvls = sorted(
        [(float(x["price"]), float(x["size"])) for x in (levels_raw or []) if float(x.get("price", 0)) > 0 and float(x.get("size", 0)) > 0],
        key=lambda t: (t[0] if is_ask else -t[0]),
    )
    if not lvls:
        return None
    # On V2 BUY (`is_ask=True`), taker fees are deducted in conditional shares, so to receive
    # `shares_req` net shares on-chain (e.g. for `convertPositions`), walk gross shares `shares_req / (1 - h)`.
    p0 = lvls[0][0]
    h_est = (min(0.50, max(0.0, (fee_rate * ((p0 * (1.0 - p0)) ** fee_exp)) / p0)) if (is_ask and fee_rate > 0.0 and 0.0 < p0 < 1.0) else 0.0)
    gross_shares_req = (math.ceil((float(shares_req) / (1.0 - h_est)) * 100.0 - 1e-9) / 100.0) if (is_ask and h_est > 0.0) else float(shares_req)
    rem = float(gross_shares_req)
    gross = 0.0
    worst_px = lvls[0][0]
    l1_usd = round(lvls[0][0] * lvls[0][1], 2)
    for px, sz in lvls:
        take = min(rem, sz)
        gross += take * px
        worst_px = px
        rem -= take
        if rem <= 1e-6:
            break
    if rem > 1e-5:
        return None
    vwap = gross / gross_shares_req
    if is_ask:
        net_ps = _net_unit_ask(vwap, fee_rate, fee_exp)
        net_cash = float(shares_req) * net_ps
        fee_usd = max(0.0, net_cash - float(shares_req) * vwap)
    else:
        fee_ps = fee_rate * ((vwap * (1.0 - vwap)) ** fee_exp) if fee_rate > 0.0 else 0.0
        fee_usd = float(shares_req) * fee_ps
        net_cash = max(0.0, gross - fee_usd)
        net_ps = net_cash / float(shares_req)
    return {
        "vwap": round(vwap, 5),
        "gross_shares": round(gross_shares_req, 2),
        "net_per_share": round(net_ps, 5),
        "net_cash_usd": round(net_cash, 4),
        "fee_usd": round(fee_usd, 4),
        "worst_px": round(worst_px, 4),
        "l1_usd": l1_usd,
    }


def detect_negrisk_convert_positions_arbs(
    spec: NegRiskConvertSlateSpec,
    books_by_token: Dict[str, Dict[str, Any]],
    target_budget_usd: float = 120.0,
    min_net_edge_per_share: float = 0.010,
    min_shares: float = 8,
    min_net_edge_per_set: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Closed-Partition (`is_closed_convert_safe == True`) `NegRiskAdapter.convertPositions` Arbitrage:
    Evaluates `m = N - 1` (buy `N - 1` `NO` legs -> convert -> `(N - 2) * $1.00` USDC + 1 `YES_k` sold into
    resting `YES_k` bids) and `m = N - 2` subsets, walking exact equal shares across all `NO` ask books and
    complementary `YES` bid books!
    """
    if min_net_edge_per_set is not None:
        min_net_edge_per_share = float(min_net_edge_per_set)
    if not spec.is_closed_convert_safe:
        return []
    n_tot = len(spec.brackets)
    if n_tot < 3:
        return []

    # Pre-score each bracket k by (net_bid_yes(k) + net_ask_no(k) - 1.0): leaving k in the YES-sell complement
    # instead of buying NO_k changes net edge by `net_bid_yes(k) - (1.0 - net_ask_no(k)) = net_bid_yes(k) + net_ask_no(k) - 1.0`!
    scored = []
    for idx, b in enumerate(spec.brackets):
        bk_y = books_by_token.get(b["yes_token"]) or {}
        bk_n = books_by_token.get(b["no_token"]) or {}
        asks_n = sorted(
            [(float(x["price"]), float(x["size"])) for x in (bk_n.get("asks") or []) if float(x.get("price", 0)) > 0 and float(x.get("size", 0)) > 0],
            key=lambda t: t[0],
        )
        bids_y = sorted(
            [(float(x["price"]), float(x["size"])) for x in (bk_y.get("bids") or []) if float(x.get("price", 0)) > 0 and float(x.get("size", 0)) > 0],
            key=lambda t: -t[0],
        )
        fr, fe = float(b["fee_rate"]), float(b["fee_exponent"])
        a_no_net = _net_unit_ask(asks_n[0][0], fr, fe) if asks_n else 9.9
        a_no_sh = asks_n[0][1] if asks_n else 0.0
        if bids_y:
            by0 = bids_y[0][0]
            b_yes_net = max(0.0, by0 - (fr * ((by0 * (1.0 - by0)) ** fe) if fr > 0 else 0.0))
            b_yes_sh = bids_y[0][1]
        else:
            b_yes_net, b_yes_sh = -1.0, 0.0
        comp_adv = b_yes_net + a_no_net - 1.0
        scored.append((comp_adv, idx, b, a_no_net, a_no_sh, b_yes_net, b_yes_sh))

    # Sort descending by `comp_adv`: top 1 (for m=N-1) or top 2 (for m=N-2) are the mathematically optimal YES-sell complements!
    scored.sort(key=lambda t: -t[0])
    cand_subsets: List[Tuple[List[int], List[int]]] = []
    # Candidate 1: m = N - 1 (sell best 1 YES complement)
    if scored[0][5] > 0.0:
        comp_1 = [scored[0][1]]
        no_1 = [t[1] for t in scored[1:]]
        cand_subsets.append((sorted(no_1), comp_1))
    # Candidate 2: m = N - 2 (sell best 2 YES complements, requires N >= 4 so m >= 2)
    if n_tot >= 4 and scored[0][5] > 0.0 and scored[1][5] > 0.0:
        comp_2 = sorted([scored[0][1], scored[1][1]])
        no_2 = [t[1] for t in scored[2:]]
        cand_subsets.append((sorted(no_2), comp_2))

    arbs: List[Dict[str, Any]] = []
    by_orig = {i: spec.brackets[i] for i in range(n_tot)}
    for no_idxs, comp_idxs in cand_subsets:
        m_cnt = len(no_idxs)
        if m_cnt < 2:
            continue
        est_unit_cost = sum(
            next(t[3] for t in scored if t[1] == i) for i in no_idxs
        )
        if est_unit_cost <= 0.0 or est_unit_cost >= float(m_cnt):
            continue
        max_l1_sh = min(
            [next(t[4] for t in scored if t[1] == i) for i in no_idxs]
            + [next(t[6] for t in scored if t[1] == k) for k in comp_idxs]
        )
        sh_try = int(math.floor(min(max_l1_sh, target_budget_usd / max(0.25, est_unit_cost))))
        if sh_try < min_shares:
            continue

        no_walks = []
        ok_walk = True
        for i in no_idxs:
            bi = by_orig[i]
            wi = _walk_side_exact_shares(
                (books_by_token.get(bi["no_token"]) or {}).get("asks") or [],
                float(sh_try), float(bi["fee_rate"]), float(bi["fee_exponent"]), is_ask=True,
            )
            if wi is None:
                ok_walk = False
                break
            no_walks.append((bi, wi))
        if not ok_walk:
            continue

        yes_walks = []
        for k in comp_idxs:
            bk_spec = by_orig[k]
            wk = _walk_side_exact_shares(
                (books_by_token.get(bk_spec["yes_token"]) or {}).get("bids") or [],
                float(sh_try), float(bk_spec["fee_rate"]), float(bk_spec["fee_exponent"]), is_ask=False,
            )
            if wk is None:
                ok_walk = False
                break
            yes_walks.append((bk_spec, wk))
        if not ok_walk:
            continue

        tot_no_cost_ps = sum(w["net_per_share"] for _, w in no_walks)
        tot_yes_bid_ps = sum(w["net_per_share"] for _, w in yes_walks)
        usdc_conv_ps = float(m_cnt - 1)
        tot_proceeds_ps = usdc_conv_ps + tot_yes_bid_ps
        edge_ps = round(tot_proceeds_ps - tot_no_cost_ps, 5)
        if edge_ps < min_net_edge_per_share:
            continue

        q_indices = [int(by_orig[i]["question_index"]) for i in no_idxs]
        index_set_int = sum(1 << qi for qi in q_indices)
        min_l1_usd = min(
            [w["l1_usd"] for _, w in no_walks] + [w["l1_usd"] for _, w in yes_walks]
        )
        arbs.append({
            "mode": "NR_CONV_POSITIONS_INSTANT",
            "event_id": spec.event_id,
            "slug": spec.slug,
            "title": spec.title,
            "neg_risk_market_id": spec.neg_risk_market_id,
            "m_no_legs": m_cnt,
            "n_total": n_tot,
            "question_indices": q_indices,
            "no_question_indices": q_indices,
            "index_set": index_set_int,
            "index_set_int": index_set_int,
            "shares": sh_try,
            "no_cost_per_share": round(tot_no_cost_ps, 4),
            "no_cost_net_per_set": round(tot_no_cost_ps, 4),
            "usdc_converted_per_share": usdc_conv_ps,
            "usdc_released_per_set": usdc_conv_ps,
            "yes_bid_proceeds_per_share": round(tot_yes_bid_ps, 4),
            "yes_bid_proceeds_net_per_set": round(tot_yes_bid_ps, 4),
            "net_proceeds_per_share": round(tot_proceeds_ps, 4),
            "net_edge_per_share": round(edge_ps, 4),
            "net_edge_per_set": round(edge_ps, 4),
            "total_cost_usd": round(sum(w["net_cash_usd"] for _, w in no_walks), 2),
            "total_net_profit_usd": round(sh_try * edge_ps, 2),
            "total_fee_usd": round(sum(w["fee_usd"] for _, w in no_walks) + sum(w["fee_usd"] for _, w in yes_walks), 4),
            "l1_usd": round(min_l1_usd, 2),
            "no_legs": [{"token_id": b["no_token"], "bracket": b, "walk": w} for b, w in no_walks],
            "yes_sell_legs": [{"token_id": b["yes_token"], "bracket": b, "walk": w} for b, w in yes_walks],
            "close_ts": spec.end_ts,
            "label": f"CONV({m_cnt}xNO->${m_cnt-1}+SELL[{','.join(b['label'][:14] for b, _ in yes_walks)}])",
        })
    arbs.sort(key=lambda x: -float(x["net_edge_per_share"]))
    return arbs


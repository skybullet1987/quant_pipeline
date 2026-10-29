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

NY_TZ = ZoneInfo("America/New_York")

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
)

NBA_SERIES_SLUGS: Tuple[str, ...] = ("nba-2026",)

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


def _extract_market_fee_rate(m: Dict[str, Any]) -> Tuple[float, float]:
    sched = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    fees_enabled = bool(m.get("feesEnabled", False))
    raw_rate = float(sched.get("rate") or 0.0)
    fee_type = str(m.get("feeType") or "").lower()
    if fee_type == "zero_fees" or not fees_enabled or raw_rate <= 0.0:
        return 0.0, 1.0
    return raw_rate, float(sched.get("exponent") or 1.0)


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
        fee_rate, _ = _extract_market_fee_rate(m)
        if fee_rate > 0.001:
            continue
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
            )
        )
    return out


def parse_pyth_close_event(
    ev: Dict[str, Any],
    asset: str,
    series_slug: str,
) -> List[PythCloseRungSpec]:
    """Parses `zero_fees` Pyth regular-session Close digital multi-strike ladders."""
    mkts = ev.get("markets") or []
    ev_id = str(ev.get("id") or "")
    ev_end = _parse_iso_ts(ev.get("endDate"))
    out: List[PythCloseRungSpec] = []
    for m in mkts:
        if m.get("closed") or m.get("archived"):
            continue
        fee_rate, _ = _extract_market_fee_rate(m)
        if fee_rate > 0.001:
            continue
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
        if float(q.get("fee_rate", 0.0)) > 0.001 or float(q.get("start_ts", 0.0)) > now_v:
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
                cost = round(float(ask_n_s) + float(ask_y_l), 4)
                if cost <= max_box_cost_net:
                    arbs.append({
                        "box_kind": "PYTH_CALENDAR_INCLUSION",
                        "asset": asset,
                        "direction": direction,
                        "strike": strike,
                        "box_cost_net": cost,
                        "box_cost_gross": cost,
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
        if qc.get("is_downward") or qc.get("ask_no") is None or float(qc.get("fee_rate", 0.0)) > 0.001:
            continue
        end_c = float(qc["end_ts"])
        k_c = float(qc["strike"])
        for qh in hit_rows:
            if (
                qh["asset"] != qc["asset"]
                or qh["direction"] != "UP"
                or qh.get("ask_yes") is None
                or float(qh.get("fee_rate", 0.0)) > 0.001
            ):
                continue
            k_h = float(qh["strike"])
            if k_h > k_c + 1e-6:
                continue
            if not (float(qh["start_ts"]) <= now_ts and now_ts < end_c <= float(qh["end_ts"]) + 60.0):
                continue
            cost = round(float(qc["ask_no"]) + float(qh["ask_yes"]), 4)
            if cost <= max_box_cost_net:
                arbs.append({
                    "box_kind": "PYTH_CLOSE_VS_HIT",
                    "asset": str(qc["asset"]),
                    "strike_hit": k_h,
                    "strike_close": k_c,
                    "box_cost_net": cost,
                    "box_cost_gross": cost,
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
    for m in mkts:
        if str(m.get("sportsMarketType") or "").strip().lower() == "moneyline" and not m.get("closed"):
            fr, _ = _extract_market_fee_rate(m)
            if fr == 0.0 and _parse_clob_tokens(m):
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
        ),
    ]
    total_legs: List[NbaOutcomeLeg] = []

    for m in mkts:
        if m.get("closed") or m.get("archived"):
            continue
        smt = str(m.get("sportsMarketType") or "").strip().lower()
        if smt not in ("spreads", "totals"):
            continue
        fr, _ = _extract_market_fee_rate(m)
        if fr > 0.0:
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
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[0], toks[1], 0, "YES", f"{team_a} -{k_abs:g}", "GT", k_abs))
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[1], toks[0], 1, "NO", f"{team_b} +{k_abs:g}", "LT", k_abs))
            elif fav_team == norm_b and out0 == norm_b and out1 == norm_a:
                # idx 0 = team_b -k_abs (wins iff M < -k_abs); idx 1 = team_a +k_abs (wins iff M > -k_abs)
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[0], toks[1], 0, "YES", f"{team_b} -{k_abs:g}", "LT", -k_abs))
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[1], toks[0], 1, "NO", f"{team_a} +{k_abs:g}", "GT", -k_abs))

        elif smt == "totals":
            raw_line = m.get("line")
            if raw_line is None:
                continue
            t_line = float(raw_line)
            if t_line <= 50.0 or not _is_half_integer(t_line):
                continue
            if _norm_team(outs[0]) == "over" and _norm_team(outs[1]) == "under":
                total_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "totals", toks[0], toks[1], 0, "YES", f"Over {t_line:g}", "OVER", t_line))
                total_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "totals", toks[1], toks[0], 1, "NO", f"Under {t_line:g}", "UNDER", t_line))

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
        for lg_b in lt_legs:
            if lg_a.market_id == lg_b.market_id or lg_a.threshold >= lg_b.threshold - 1e-6:
                continue
            b_px = float(best_asks_by_token[lg_b.token_id])
            if not (0.01 <= b_px <= 0.99):
                continue
            cost = round(a_px + b_px, 4)
            if cost <= max_box_cost_net:
                mid_pts = round(lg_b.threshold - lg_a.threshold, 1)
                candidates.append({
                    "box_kind": "NBA_POLISH_MIDDLE" if ("ML" in lg_a.display_label or "ML" in lg_b.display_label) else "NBA_SPREAD_MONO",
                    "event_id": spec.event_id,
                    "title": spec.title,
                    "box_cost_net": cost,
                    "box_cost_gross": cost,
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
        for lg_u in un_legs:
            if lg_o.market_id == lg_u.market_id or lg_o.threshold >= lg_u.threshold - 1e-6:
                continue
            u_px = float(best_asks_by_token[lg_u.token_id])
            if not (0.01 <= u_px <= 0.99):
                continue
            cost = round(o_px + u_px, 4)
            if cost <= max_box_cost_net:
                candidates.append({
                    "box_kind": "NBA_TOTAL_MONO",
                    "event_id": spec.event_id,
                    "title": spec.title,
                    "box_cost_net": cost,
                    "box_cost_gross": cost,
                    "middle_width_pts": round(lg_u.threshold - lg_o.threshold, 1),
                    "leg_a": lg_o,
                    "leg_b": lg_u,
                    "close_ts": spec.settle_est_ts,
                    "label": f"{lg_o.display_label} + {lg_u.display_label}",
                })

    candidates.sort(key=lambda x: (float(x["box_cost_net"]), -float(x["middle_width_pts"])))
    return candidates


def parse_zero_fee_negrisk_slate(
    ev: Dict[str, Any], series_slug: str, allow_mixed_fees: bool = False
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
    )

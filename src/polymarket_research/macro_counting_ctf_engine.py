#!/usr/bin/env python3
"""
Phase-2 Multi-Vertical Structural & Oracle Engine (`TW1`, `FED1`, `COND1`, `CTF_OVR`, `MKR_RW`, `GAS1`, `CM_SHOCK`, `AI1`, `D2`).
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from src.polymarket_research.barrier_onetouch_svi_engine import first_passage_touch_prob
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    _extract_market_fee_rate,
    _parse_clob_tokens,
    _parse_iso_ts,
)

logger = logging.getLogger("MacroCountingCTF")
NY_TZ = ZoneInfo("America/New_York")
CHROME_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

COUNTING_SERIES_HANDLES: Tuple[Tuple[str, str], ...] = (
    ("elon-tweets", "elonmusk"),
    ("elon-tweets-48h", "elonmusk"),
    ("trump-truth-social", "realDonaldTrump"),
)

FOMC_PARLAY_SERIES: Tuple[str, ...] = ("fomc", "fed-3-parlay")

OIL_SENATE_SLUGS: Tuple[str, ...] = (
    "which-party-will-win-the-senate-in-2026",
    "who-wins-the-senate-pending-oil-below-85-before-the-midterms",
    "who-wins-the-senate-pending-oil-above-or-below-80-before-the-midterms",
)

GAS_SERIES_SLUGS: Tuple[str, ...] = ("us-gas-price-daily", "gas-price-hits-weekly")
AI_SERIES_SLUGS: Tuple[str, ...] = ("best-ai-company", "chinese-ai-1")

HOURLY_BINANCE_SERIES: Dict[str, str] = {
    "BTC": "btc-up-or-down-hourly",
    "ETH": "eth-up-or-down-hourly",
    "SOL": "solana-up-or-down-hourly",
    "XRP": "xrp-up-or-down-hourly",
    "BNB": "bnb-up-or-down-hourly",
    "DOGE": "doge-up-or-down-hourly",
}

_XTRACKER_CACHE: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
_AAA_GAS_CACHE: Tuple[float, Optional[Dict[str, Any]]] = (0.0, None)


# ==============================================================================
# 1. `TW1_COUNTING_TRUNCATION_AND_BOX` (`xtracker.polymarket.com` + Sub-Windows)
# ==============================================================================
@dataclass
class CountingBracket:
    market_id: str
    condition_id: str
    label: str
    low_count: int
    high_count: float  # float("inf") for "200+"
    yes_token: str
    no_token: str
    fee_rate: float = 0.0
    rewards_min_size: float = 0.0
    rewards_max_spread: float = 0.0
    neg_risk: bool = True


@dataclass
class CountingSlateSpec:
    event_id: str
    slug: str
    series_slug: str
    handle: str
    title: str
    window_start_ts: float
    window_end_ts: float
    gamma_closed_floor: int
    brackets: List[CountingBracket] = field(default_factory=list)


_CNT_LT_RE = re.compile(r"^\s*(?:<|under\s+|less than\s+)(\d+)\s*$", re.IGNORECASE)
_CNT_PLUS_RE = re.compile(r"^\s*(\d+)\s*\+\s*$|^\s*(\d+)\s+or\s+more\s*$", re.IGNORECASE)
_CNT_RNG_RE = re.compile(r"^\s*(\d+)\s*[-–—to]+\s*(\d+)\s*$", re.IGNORECASE)
_DESC_WINDOW_RE = re.compile(
    r"(?:from|between)\s+([A-Za-z]+\s+\d{1,2})(?:,\s*(\d{4}))?,?\s+(\d{1,2}:\d{2}\s*[AP]M)\s*ET\s+"
    r"(?:to|and)\s+([A-Za-z]+\s+\d{1,2}),?\s*(\d{4}),?\s+(\d{1,2}:\d{2}\s*[AP]M)\s*ET",
    re.IGNORECASE,
)


def parse_count_bracket_bounds(label: str) -> Optional[Tuple[int, float]]:
    s = str(label or "").strip().replace(",", "")
    m_lt = _CNT_LT_RE.match(s)
    if m_lt:
        v = int(m_lt.group(1))
        return (0, float(v - 1)) if v > 0 else None
    m_pl = _CNT_PLUS_RE.match(s)
    if m_pl:
        v = int(m_pl.group(1) or m_pl.group(2))
        return (v, float("inf"))
    m_rg = _CNT_RNG_RE.match(s)
    if m_rg:
        lo, hi = int(m_rg.group(1)), int(m_rg.group(2))
        if hi >= lo >= 0:
            return (lo, float(hi))
    return None


def _parse_et_window_from_description(desc: str, fallback_end_ts: float) -> Tuple[float, float]:
    m = _DESC_WINDOW_RE.search(str(desc or ""))
    if m:
        start_md, start_yr, start_tm, end_md, end_yr, end_tm = m.groups()
        yr2 = int(end_yr)
        yr1 = int(start_yr) if start_yr else yr2
        try:
            dt1 = datetime.strptime(f"{start_md} {yr1} {start_tm.upper().replace(' ', '')}", "%B %d %Y %I:%M%p")
            dt2 = datetime.strptime(f"{end_md} {yr2} {end_tm.upper().replace(' ', '')}", "%B %d %Y %I:%M%p")
            if dt1 > dt2 and not start_yr:
                dt1 = dt1.replace(year=yr2 - 1)
            t1 = dt1.replace(tzinfo=NY_TZ).timestamp()
            t2 = dt2.replace(tzinfo=NY_TZ).timestamp()
            if t2 > t1:
                return t1, t2
        except Exception:
            pass
    return (fallback_end_ts - 7.0 * 86400.0, fallback_end_ts)


def parse_counting_slate_event(ev: Dict[str, Any], series_slug: str, handle: str) -> Optional[CountingSlateSpec]:
    if ev.get("closed") or ev.get("archived"):
        return None
    end_ts = _parse_iso_ts(ev.get("endDate"))
    if not end_ts:
        return None
    mkts = ev.get("markets") or []
    if len(mkts) < 3:
        return None
    desc = str(ev.get("description") or (mkts[0].get("description") if mkts else "") or "")
    w_start, w_end = _parse_et_window_from_description(desc, float(end_ts))

    closed_floor = 0
    open_brs: List[CountingBracket] = []
    for m in mkts:
        if m.get("archived"):
            continue
        lbl = str(m.get("groupItemTitle") or m.get("question") or "")
        bnds = parse_count_bracket_bounds(lbl)
        if bnds is None:
            continue
        lo_c, hi_c = bnds
        if m.get("closed"):
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            # Closed lower bracket resolved NO => true count is strictly > hi_c
            if isinstance(op, list) and len(op) >= 2 and float(op[1]) >= 0.99 and math.isfinite(hi_c):
                closed_floor = max(closed_floor, int(hi_c) + 1)
            elif isinstance(op, list) and len(op) >= 2 and float(op[0]) >= 0.99:
                return None
            continue
        fr, _ = _extract_market_fee_rate(m)
        if fr > 0.0:
            continue
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        open_brs.append(
            CountingBracket(
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                label=lbl,
                low_count=lo_c,
                high_count=hi_c,
                yes_token=toks[0],
                no_token=toks[1],
                fee_rate=0.0,
                rewards_min_size=float(m.get("rewardsMinSize") or 0.0),
                rewards_max_spread=float(m.get("rewardsMaxSpread") or 0.0),
                neg_risk=bool(m.get("negRisk") if m.get("negRisk") is not None else ev.get("negRisk", True)),
            )
        )
    if len(open_brs) < 2:
        return None
    open_brs.sort(key=lambda b: b.low_count)
    return CountingSlateSpec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        series_slug=series_slug,
        handle=handle,
        title=str(ev.get("title") or series_slug),
        window_start_ts=w_start,
        window_end_ts=w_end,
        gamma_closed_floor=closed_floor,
        brackets=open_brs,
    )


def fetch_xtracker_user_stats_sync(handle: str, ttl_sec: float = 60.0) -> Dict[str, Dict[str, Any]]:
    """
    Polls Polymarket's official counting oracle `https://xtracker.polymarket.com/api/users/{handle}`
    and maps each active `marketLink` event slug to `{total, start_ts, end_ts, hourly_counts}`.
    """
    now = time.time()
    cached = _XTRACKER_CACHE.get(handle)
    if cached and (now - cached[0]) < ttl_sec:
        return cached[1]
    out: Dict[str, Dict[str, Any]] = {}
    try:
        req = urllib.request.Request(
            f"https://xtracker.polymarket.com/api/users/{handle}",
            headers={"User-Agent": CHROME_UA},
        )
        with urllib.request.urlopen(req, timeout=5.0) as r:
            u_data = json.loads(r.read().decode("utf-8", errors="replace")).get("data") or {}
        for tr in (u_data.get("trackings") or []):
            if not tr.get("isActive"):
                continue
            tid = str(tr.get("id") or "")
            mlink = str(tr.get("marketLink") or "")
            eslug = mlink.rstrip("/").split("/")[-1] if mlink else ""
            if not tid or not eslug:
                continue
            req_t = urllib.request.Request(
                f"https://xtracker.polymarket.com/api/trackings/{tid}?includeStats=true",
                headers={"User-Agent": CHROME_UA},
            )
            with urllib.request.urlopen(req_t, timeout=5.0) as rt:
                td = json.loads(rt.read().decode("utf-8", errors="replace")).get("data") or {}
            stats = td.get("stats") or {}
            hourly: List[Tuple[float, int]] = []
            bare_daily = False
            for row in (stats.get("daily") or []):
                d_raw = str(row.get("date") or "").strip()
                if len(d_raw) == 10:
                    bare_daily = True
                ts_r = _parse_iso_ts(d_raw)
                if ts_r is not None:
                    hourly.append((float(ts_r), int(row.get("count") or 0)))
            out[eslug] = {
                "tracking_id": tid,
                "total": int(stats.get("total") or 0),
                "start_ts": _parse_iso_ts(td.get("startDate")) or 0.0,
                "end_ts": _parse_iso_ts(td.get("endDate")) or 0.0,
                "hourly": hourly,
                "daily_tz_pad": 18000.0 if bare_daily else 0.0,
            }
        _XTRACKER_CACHE[handle] = (now, out)
    except Exception as exc:
        logger.debug(f"xtracker fetch notice ({handle}): {exc}")
        if cached:
            return cached[1]
    return out


def evaluate_counting_dead_no_locks(
    slate: CountingSlateSpec,
    xtracker_by_slug: Dict[str, Dict[str, Any]],
    safety_post_buffer: int = 2,
) -> Tuple[int, List[CountingBracket]]:
    """
    Returns `(verified_floor, eliminated_brackets)`.
    Per Polymarket xtracker rules, posts captured by xtracker (~5m) remain counted even if later deleted,
    making `max(gamma_closed_floor, xtracker_total)` a non-decreasing lower bound. We still require
    `verified_floor >= high_count + safety_post_buffer` (`>= +2` posts past bracket ceiling).
    """
    xt = xtracker_by_slug.get(slate.slug) or {}
    xt_total = int(xt.get("total") or 0)
    verified_floor = max(int(slate.gamma_closed_floor), xt_total)
    dead: List[CountingBracket] = []
    for br in slate.brackets:
        if math.isfinite(br.high_count) and verified_floor >= int(br.high_count) + max(1, safety_post_buffer):
            dead.append(br)
    return verified_floor, dead


def detect_counting_subwindow_boxes(
    slates: List[CountingSlateSpec],
    best_asks_by_token: Dict[str, float],
    xtracker_by_handle: Dict[str, Dict[str, Dict[str, Any]]],
    max_box_cost_net: float = 1.05,
) -> List[Dict[str, Any]]:
    """
    Detects 2-leg `0%`-fee Sub-Window Inclusion Boxes (`S ⊂ L`, e.g. `48h ⊂ 7d` on `@elonmusk`):
    Let `N_banked >= 0` be verified posts in `[start_L, start_S)`. Since `N_L >= N_banked + N_S`:
      1. Upper-Tail Box: `N_S >= k_hi` (`high_count == inf`) => `N_L >= K_hi` whenever `K_hi <= N_banked + k_hi`
         => `NO(S >= k_hi) + YES(L >= K_hi) >= $1.00` (`$2.00` middle!).
      2. Lower-Tail Box: `N_L <= K_lo` (`low_count == 0`) => `N_S <= k_lo` whenever `K_lo <= N_banked + k_lo`
         => `NO(L <= K_lo) + YES(S <= k_lo) >= $1.00` (`$2.00` middle!).
    """
    boxes: List[Dict[str, Any]] = []
    for i, s_short in enumerate(slates):
        for j, s_long in enumerate(slates):
            if i == j or s_short.handle != s_long.handle or s_short.event_id == s_long.event_id:
                continue
            # Strict containment (no tolerance): Short window must lie fully inside Long window.
            if not (
                s_long.window_start_ts <= s_short.window_start_ts
                and s_short.window_end_ts <= s_long.window_end_ts
                and (s_long.window_end_ts - s_long.window_start_ts) > (s_short.window_end_ts - s_short.window_start_ts) + 3600.0
            ):
                continue
            xt_long = (xtracker_by_handle.get(s_long.handle) or {}).get(s_long.slug) or {}
            banked = 0
            if xt_long.get("hourly") and s_short.window_start_ts > s_long.window_start_ts + 1800.0:
                tz_pad = float(xt_long.get("daily_tz_pad") or 0.0)
                banked = sum(
                    cnt for ts_h, cnt in xt_long["hourly"]
                    if (ts_h - tz_pad) >= s_long.window_start_ts and (ts_h + 86400.0 + tz_pad) <= s_short.window_start_ts
                )
            # 1. Upper-tail 2-leg dominance
            s_up = [b for b in s_short.brackets if not math.isfinite(b.high_count)]
            l_up = [b for b in s_long.brackets if not math.isfinite(b.high_count)]
            for bs in s_up:
                ask_no_s = best_asks_by_token.get(bs.no_token)
                if ask_no_s is None:
                    continue
                for bl in l_up:
                    if bl.low_count <= banked + bs.low_count:
                        ask_yes_l = best_asks_by_token.get(bl.yes_token)
                        if ask_yes_l is None:
                            continue
                        cost = round(float(ask_no_s) + float(ask_yes_l), 4)
                        if cost <= max_box_cost_net:
                            boxes.append({
                                "box_kind": "TW1_UPPER_SUBWINDOW",
                                "handle": s_short.handle,
                                "banked": banked,
                                "box_cost_net": cost,
                                "leg_a": {"token_id": bs.no_token, "opp_token_id": bs.yes_token, "condition_id": bs.condition_id, "side": "NO", "label": f"NO_48H[{bs.label}]", "market_id": bs.market_id, "fee_rate": 0.0, "strike": float(bs.low_count), "neg_risk": bs.neg_risk},
                                "leg_b": {"token_id": bl.yes_token, "opp_token_id": bl.no_token, "condition_id": bl.condition_id, "side": "YES", "label": f"YES_7D[{bl.label}]", "market_id": bl.market_id, "fee_rate": 0.0, "strike": float(bl.low_count), "neg_risk": bl.neg_risk},
                                "close_ts": max(s_short.window_end_ts, s_long.window_end_ts),
                                "label": f"{s_short.handle} NO({bs.label} short) + YES({bl.label} long, banked={banked})",
                            })
            # 2. Lower-tail 2-leg dominance
            s_lo = [b for b in s_short.brackets if b.low_count == 0 and math.isfinite(b.high_count)]
            l_lo = [b for b in s_long.brackets if b.low_count == 0 and math.isfinite(b.high_count)]
            for bl in l_lo:
                ask_no_l = best_asks_by_token.get(bl.no_token)
                if ask_no_l is None:
                    continue
                for bs in s_lo:
                    if int(bl.high_count) <= banked + int(bs.high_count):
                        ask_yes_s = best_asks_by_token.get(bs.yes_token)
                        if ask_yes_s is None:
                            continue
                        cost = round(float(ask_no_l) + float(ask_yes_s), 4)
                        if cost <= max_box_cost_net:
                            boxes.append({
                                "box_kind": "TW1_LOWER_SUBWINDOW",
                                "handle": s_short.handle,
                                "banked": banked,
                                "box_cost_net": cost,
                                "leg_a": {"token_id": bl.no_token, "opp_token_id": bl.yes_token, "condition_id": bl.condition_id, "side": "NO", "label": f"NO_7D[{bl.label}]", "market_id": bl.market_id, "fee_rate": 0.0, "strike": float(bl.high_count), "neg_risk": bl.neg_risk},
                                "leg_b": {"token_id": bs.yes_token, "opp_token_id": bs.no_token, "condition_id": bs.condition_id, "side": "YES", "label": f"YES_48H[{bs.label}]", "market_id": bs.market_id, "fee_rate": 0.0, "strike": float(bs.high_count), "neg_risk": bs.neg_risk},
                                "close_ts": max(s_short.window_end_ts, s_long.window_end_ts),
                                "label": f"{s_short.handle} NO({bl.label} long) + YES({bs.label} short, banked={banked})",
                            })
    boxes.sort(key=lambda x: float(x["box_cost_net"]))
    return boxes


# ==============================================================================
# 2. Exact Finite-State Bitmask Dominance Engine (`FED1` FOMC & `COND1` Oil-Senate)
# ==============================================================================
FOMC_ACTIONS: Tuple[str, ...] = ("CUT50", "CUT25", "PAUSE", "HIKE25", "HIKE50")
FOMC_STATES_3M: List[Tuple[str, str, str]] = [
    (a, b, c) for a in FOMC_ACTIONS for b in FOMC_ACTIONS for c in FOMC_ACTIONS
]
ALL_FOMC_MASK: int = (1 << len(FOMC_STATES_3M)) - 1  # 125-bit mask


def _classify_single_fomc_label(label: str) -> Optional[str]:
    s = str(label or "").strip().lower()
    if "no change" in s or s == "pause":
        return "PAUSE"
    has_50 = bool(re.search(r"\b50\s*\+?|\b50\s*bps", s))
    has_25_plus = "25+" in s
    has_25 = bool(re.search(r"(?<![.\d])25(?![.\d])", s))
    if has_50 and ("decrease" in s or "cut" in s):
        return "CUT50"
    if has_25_plus and ("decrease" in s or "cut" in s):
        return "CUT25+"
    if has_25_plus and ("increase" in s or "hike" in s):
        return "HIKE25+"
    if has_25 and ("decrease" in s or "cut" in s):
        return "CUT25"
    if has_25 and ("increase" in s or "hike" in s):
        return "HIKE25"
    if has_50 and ("increase" in s or "hike" in s):
        return "HIKE50"
    return None


_FOMC_LABEL_ACTION_SET: Dict[str, Tuple[str, ...]] = {
    "CUT25+": ("CUT25", "CUT50"),
    "HIKE25+": ("HIKE25", "HIKE50"),
}


def _parlay_word_matches(word: str, action: str) -> bool:
    w = word.strip().lower()
    if w == "pause":
        return action == "PAUSE"
    if w == "cut":
        return action in ("CUT25", "CUT50")
    if w == "hike":
        return action in ("HIKE25", "HIKE50")
    return False


def build_fomc_truth_table_legs(
    fomc_events: List[Dict[str, Any]],
    parlay_events: List[Dict[str, Any]],
    sep_2026_realized_action: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Maps every open `0%`-fee contract in `Oct FOMC`, `Dec FOMC`, `Jan FOMC`, `fed-decisions-oct-jan`,
    and `fed-decisions-sepdec` (when `sep_2026_realized_action` is known) to an exact 125-bit state mask.
    """
    legs: List[Dict[str, Any]] = []

    for ev in fomc_events:
        if ev.get("closed"):
            continue
        slug = str(ev.get("slug") or "").lower()
        end_ts = _parse_iso_ts(ev.get("endDate")) or 0.0
        m_idx = 0 if "october" in slug else (1 if "december" in slug else (2 if "january" in slug else -1))
        if m_idx < 0 or end_ts <= 0:
            continue
        m_tag = ("OCT", "DEC", "JAN")[m_idx]
        for m in (ev.get("markets") or []):
            if m.get("closed"):
                continue
            fr, _ = _extract_market_fee_rate(m)
            toks = _parse_clob_tokens(m)
            act = _classify_single_fomc_label(str(m.get("groupItemTitle") or m.get("question") or ""))
            if fr > 0.0 or not toks or not act:
                continue
            y_mask = 0
            act_set = _FOMC_LABEL_ACTION_SET.get(act, (act,))
            for idx, st in enumerate(FOMC_STATES_3M):
                if st[m_idx] in act_set:
                    y_mask |= (1 << idx)
            mid = str(m.get("id") or "")
            cid = str(m.get("conditionId") or "")
            nr_m = m.get("negRisk") if isinstance(m.get("negRisk"), bool) else (ev.get("negRisk") if isinstance(ev.get("negRisk"), bool) else None)
            legs.append({"event_group": f"FOMC_{m_tag}", "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1], "side": "YES", "label": f"YES({m_tag}:{act})", "mask": y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_m})
            legs.append({"event_group": f"FOMC_{m_tag}", "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0], "side": "NO", "label": f"NO({m_tag}:{act})", "mask": ALL_FOMC_MASK ^ y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_m})

    for ev in parlay_events:
        if ev.get("closed"):
            continue
        slug = str(ev.get("slug") or "").lower()
        end_ts = _parse_iso_ts(ev.get("endDate")) or 0.0
        is_oct_jan = "oct-jan" in slug
        is_sep_dec = "sepdec" in slug and sep_2026_realized_action is not None
        if not (is_oct_jan or is_sep_dec) or end_ts <= 0:
            continue
        p_tag = "PARLAY_OCT_JAN" if is_oct_jan else "PARLAY_SEP_DEC"
        named_union_mask = 0
        # If ANY named market is skipped (closed / fee / no tokens / unparseable / zero mask), the
        # named union is incomplete and `Other = ALL ^ union` would over-claim states -> no Other legs.
        named_incomplete = False
        other_mkt: Optional[Tuple[Dict[str, Any], Tuple[str, str]]] = None
        for m in (ev.get("markets") or []):
            lbl = str(m.get("groupItemTitle") or "").strip()
            is_other = lbl.lower() == "other"
            if m.get("closed"):
                if not is_other:
                    named_incomplete = True
                continue
            fr, _ = _extract_market_fee_rate(m)
            toks = _parse_clob_tokens(m)
            if fr > 0.0 or not toks:
                if not is_other:
                    named_incomplete = True
                continue
            if is_other:
                other_mkt = (m, toks)
                continue
            parts = [p.strip() for p in re.split(r"[-–—/]", lbl) if p.strip()]
            if len(parts) != 3:
                named_incomplete = True
                continue
            y_mask = 0
            for idx, (a_oct, a_dec, a_jan) in enumerate(FOMC_STATES_3M):
                if is_oct_jan:
                    ok = _parlay_word_matches(parts[0], a_oct) and _parlay_word_matches(parts[1], a_dec) and _parlay_word_matches(parts[2], a_jan)
                else:
                    assert sep_2026_realized_action is not None
                    ok = _parlay_word_matches(parts[0], sep_2026_realized_action) and _parlay_word_matches(parts[1], a_oct) and _parlay_word_matches(parts[2], a_dec)
                if ok:
                    y_mask |= (1 << idx)
            if y_mask == 0:
                # Unmapped parlay words: a NO leg with ALL-states mask would fabricate a riskless cover.
                named_incomplete = True
                continue
            named_union_mask |= y_mask
            mid = str(m.get("id") or "")
            cid = str(m.get("conditionId") or "")
            nr_p = m.get("negRisk") if isinstance(m.get("negRisk"), bool) else (ev.get("negRisk") if isinstance(ev.get("negRisk"), bool) else None)
            legs.append({"event_group": p_tag, "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1], "side": "YES", "label": f"YES({p_tag}:{lbl})", "mask": y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_p})
            legs.append({"event_group": p_tag, "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0], "side": "NO", "label": f"NO({p_tag}:{lbl})", "mask": ALL_FOMC_MASK ^ y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_p})
        if other_mkt is not None and not named_incomplete:
            m_o, toks_o = other_mkt
            o_mask = ALL_FOMC_MASK ^ named_union_mask
            mid_o = str(m_o.get("id") or "")
            cid_o = str(m_o.get("conditionId") or "")
            nr_o = m_o.get("negRisk") if isinstance(m_o.get("negRisk"), bool) else (ev.get("negRisk") if isinstance(ev.get("negRisk"), bool) else None)
            legs.append({"event_group": p_tag, "market_id": mid_o, "condition_id": cid_o, "token_id": toks_o[0], "opp_token_id": toks_o[1], "side": "YES", "label": f"YES({p_tag}:Other)", "mask": o_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_o})
            legs.append({"event_group": p_tag, "market_id": mid_o, "condition_id": cid_o, "token_id": toks_o[1], "opp_token_id": toks_o[0], "side": "NO", "label": f"NO({p_tag}:Other)", "mask": ALL_FOMC_MASK ^ o_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_o})
    return legs


# 9-state Oil x Senate truth table: 3 Oil regimes (<80, [80,85), >=85) x 3 Senate winners (DEM, REP, OTHER)
OIL_SENATE_STATES: List[Tuple[str, str]] = [
    (o, p) for o in ("LT80", "B80_85", "GE85") for p in ("DEM", "REP", "OTHER")
]
ALL_OIL_SENATE_MASK: int = (1 << len(OIL_SENATE_STATES)) - 1  # 9-bit mask (511)


def build_oil_senate_truth_table_legs(events_by_slug: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Maps `which-party-will-win-the-senate-in-2026` + `who-wins-the-senate-pending-oil-*` (`0%` fee)
    into exact 9-bit masks over `{LT80, B80_85, GE85} x {DEM, REP, OTHER}`.
    """
    legs: List[Dict[str, Any]] = []
    for slug, ev in events_by_slug.items():
        if not ev or ev.get("closed"):
            continue
        end_ts = _parse_iso_ts(ev.get("endDate")) or 0.0
        if end_ts <= 0:
            continue
        s_low = slug.lower()
        for m in (ev.get("markets") or []):
            if m.get("closed"):
                continue
            fr, _ = _extract_market_fee_rate(m)
            toks = _parse_clob_tokens(m)
            if fr > 0.0 or not toks:
                continue
            lbl = str(m.get("groupItemTitle") or m.get("question") or "").strip()
            ll = lbl.lower()
            y_mask = 0
            if "which-party-will-win-the-senate" in s_low:
                party = "DEM" if "democrat" in ll else ("REP" if "republican" in ll else None)
                if not party:
                    continue
                for idx, (_, p_st) in enumerate(OIL_SENATE_STATES):
                    if p_st == party:
                        y_mask |= (1 << idx)
                eg = "SENATE_MAIN"
            elif "pending-oil" in s_low:
                party = "DEM" if ("d senate" in ll or "democrat" in ll) else ("REP" if ("r senate" in ll or "republican" in ll) else None)
                thresh = 85 if "85" in ll else (80 if "80" in ll else 0)
                is_lt = "<" in ll or "below" in ll or "less" in ll
                is_ge = "≥" in ll or ">=" in ll or "above" in ll or "greater" in ll
                if not party or thresh not in (80, 85) or (is_lt == is_ge):
                    continue
                for idx, (o_st, p_st) in enumerate(OIL_SENATE_STATES):
                    if p_st != party:
                        continue
                    oil_ok = (
                        (o_st == "LT80" if is_lt else o_st in ("B80_85", "GE85"))
                        if thresh == 80
                        else (o_st in ("LT80", "B80_85") if is_lt else o_st == "GE85")
                    )
                    if oil_ok:
                        y_mask |= (1 << idx)
                eg = f"OIL_{thresh}_SENATE"
            else:
                continue
            mid = str(m.get("id") or "")
            cid = str(m.get("conditionId") or "")
            nr_s = m.get("negRisk") if isinstance(m.get("negRisk"), bool) else (ev.get("negRisk") if isinstance(ev.get("negRisk"), bool) else None)
            legs.append({"event_group": eg, "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1], "side": "YES", "label": f"YES[{lbl}]", "mask": y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_s})
            legs.append({"event_group": eg, "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0], "side": "NO", "label": f"NO[{lbl}]", "mask": ALL_OIL_SENATE_MASK ^ y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_s})
    return legs


def find_cross_event_bitmask_boxes(
    legs: List[Dict[str, Any]],
    best_asks_by_token: Dict[str, float],
    all_states_mask: int,
    max_2leg_cost: float = 1.05,
    max_3leg_cost: float = 1.03,
) -> List[Dict[str, Any]]:
    """
    Finds all minimal 2-leg and 3-leg cross-event `0%`-fee portfolios whose bitwise OR covers
    100% of states (`(m1 | m2 [| m3]) == all_states_mask`), guaranteeing payout >= $1.00 in every state!
    """
    priced = []
    for lg in legs:
        ask = best_asks_by_token.get(str(lg["token_id"]))
        m = int(lg["mask"])
        if ask is not None and 0.002 <= float(ask) <= 0.995 and 0 < m < all_states_mask:
            priced.append((float(ask), m, lg))

    out: List[Dict[str, Any]] = []
    n = len(priced)
    covered_pairs = set()

    # 1. Exact 2-leg cross-market dominance boxes (`m1 | m2 == all_states_mask`)
    for i in range(n):
        a1, m1, l1 = priced[i]
        for j in range(i + 1, n):
            a2, m2, l2 = priced[j]
            if l1["market_id"] == l2["market_id"] or l1["event_group"] == l2["event_group"]:
                continue
            if (m1 | m2) == all_states_mask:
                cost = round(a1 + a2, 4)
                covered_pairs.add((i, j))
                if cost <= max_2leg_cost:
                    double_states = bin(m1 & m2).count("1")
                    out.append({
                        "n_legs": 2,
                        "box_cost_net": cost,
                        "double_pay_states": double_states,
                        "legs": [l1, l2],
                        "close_ts": max(float(l1["end_ts"]), float(l2["end_ts"])),
                        "label": f"{l1['label']} + {l2['label']}",
                    })

    # 2. Minimal 3-leg cross-event partitions (`m1 | m2 | m3 == all_states_mask`, no 2-leg subset already covers)
    for i in range(n):
        a1, m1, l1 = priced[i]
        if a1 >= max_3leg_cost:
            continue
        for j in range(i + 1, n):
            if (i, j) in covered_pairs:
                continue
            a2, m2, l2 = priced[j]
            if a1 + a2 >= max_3leg_cost or l1["market_id"] == l2["market_id"]:
                continue
            m12 = m1 | m2
            if m12 in (m1, m2):
                continue
            for k in range(j + 1, n):
                if (i, k) in covered_pairs or (j, k) in covered_pairs:
                    continue
                a3, m3, l3 = priced[k]
                cost3 = round(a1 + a2 + a3, 4)
                if cost3 > max_3leg_cost:
                    continue
                if l3["market_id"] in (l1["market_id"], l2["market_id"]):
                    continue
                if len({l1["event_group"], l2["event_group"], l3["event_group"]}) < 2:
                    continue
                if (m12 | m3) == all_states_mask and (m1 | m3) != all_states_mask and (m2 | m3) != all_states_mask:
                    out.append({
                        "n_legs": 3,
                        "box_cost_net": cost3,
                        "double_pay_states": 0,
                        "legs": [l1, l2, l3],
                        "close_ts": max(float(l1["end_ts"]), float(l2["end_ts"]), float(l3["end_ts"])),
                        "label": f"{l1['label']} + {l2['label']} + {l3['label']}",
                    })

    out.sort(key=lambda x: (float(x["box_cost_net"]), int(x["n_legs"])))
    return out


# ==============================================================================
# 3. `CTF_OVERROUND_MINT_SELL` & `MKR_REWARD_LOCKED_CARRY` (`Ideas #21, #22`)
# ==============================================================================
def walk_equal_shares_overround_bids(
    legs_bids_spec: List[Dict[str, Any]],
    target_mint_budget_usd: float = 100.0,
    min_net_proceeds_per_set: float = 1.004,
    min_shares: float = 8.0,
) -> Dict[str, Any]:
    """
    Walks L2 `bids` across all `N` mutually exclusive outcomes (`[YES, NO]` binary or `[YES_1..YES_N]` NegRisk)
    for equal shares `Q` minted at `$1.00 * Q` via `splitPosition`.
    Returns `filled=True` iff net proceeds after per-leg fees >= `min_net_proceeds_per_set * Q`.
    """
    if len(legs_bids_spec) < 2 or target_mint_budget_usd <= 0:
        return {"filled": False}
    parsed_books: List[Tuple[List[Tuple[float, float]], float, float]] = []
    l1_min_sh = float("inf")
    l1_net_sum = 0.0
    for sp in legs_bids_spec:
        fr = float(sp.get("fee_rate") or 0.0)
        fexp = float(sp.get("fee_exponent") or 1.0)
        bids = sorted(
            [(float(b["price"]), float(b["size"])) for b in (sp.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
            key=lambda x: -x[0],
        )
        if not bids:
            return {"filled": False}
        p0, s0 = bids[0]
        fee0 = fr * ((p0 * (1.0 - p0)) ** fexp) if fr > 0 else 0.0
        l1_net_sum += (p0 - fee0)
        l1_min_sh = min(l1_min_sh, s0)
        parsed_books.append((bids, fr, fexp))

    if l1_net_sum < min_net_proceeds_per_set:
        return {"filled": False, "l1_net_proceeds": round(l1_net_sum, 4)}

    cap_sh = min(float(target_mint_budget_usd), min(sum(s for _, s in bds) for bds, _, _ in parsed_books))
    q_sh = math.floor(cap_sh)
    if q_sh < min_shares:
        return {"filled": False, "l1_net_proceeds": round(l1_net_sum, 4)}

    gross_rev = 0.0
    total_fee = 0.0
    for bds, fr, fexp in parsed_books:
        rem = float(q_sh)
        for px, sz in bds:
            take = min(rem, sz)
            gross_rev += take * px
            if fr > 0:
                total_fee += take * fr * ((px * (1.0 - px)) ** fexp)
            rem -= take
            if rem <= 1e-9:
                break
        if rem > 1e-6:
            return {"filled": False}

    net_rev_ps = (gross_rev - total_fee) / q_sh
    if net_rev_ps < min_net_proceeds_per_set:
        return {"filled": False, "l1_net_proceeds": round(l1_net_sum, 4)}
    return {
        "filled": True,
        "shares": float(q_sh),
        "mint_cost_per_set": 1.0,
        "gross_proceeds_per_set": round(gross_rev / q_sh, 4),
        "net_proceeds_per_set": round(net_rev_ps, 4),
        "net_edge_per_set": round(net_rev_ps - 1.0, 4),
        "fee_usd": round(total_fee, 4),
        "spent_usd": round(float(q_sh), 2),
        "l1_usd": round(l1_min_sh, 2),
    }


def walk_position_overround_bid_unwind(
    legs_bids_spec: List[Dict[str, Any]],
    exact_shares: float,
    min_net_proceeds_per_set: float = 1.004,
) -> Dict[str, Any]:
    """
    Walks resting L2 `bids` across all held legs of an open 2-leg or N-leg riskless box
    for 100% of `exact_shares` simultaneously (leaving zero residual open shares).
    Returns `filled=True` iff every leg can absorb `exact_shares` and net proceeds per set
    after per-leg taker sell fees >= `min_net_proceeds_per_set`.
    """
    q_sh = float(exact_shares)
    if len(legs_bids_spec) < 2 or q_sh <= 0.0:
        return {"filled": False}
    gross_rev = 0.0
    total_fee = 0.0
    worst_bids: List[float] = []
    for sp in legs_bids_spec:
        fr = float(sp.get("fee_rate") or 0.0)
        fexp = float(sp.get("fee_exponent") or 1.0)
        bids = sorted(
            [
                (float(b["price"]), float(b["size"]))
                for b in (sp.get("bids") or [])
                if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0
            ],
            key=lambda x: -x[0],
        )
        if not bids:
            return {"filled": False}
        rem = q_sh
        leg_worst = bids[0][0]
        for px, sz in bids:
            take = min(rem, sz)
            gross_rev += take * px
            if fr > 0.0:
                total_fee += take * fr * ((px * (1.0 - px)) ** fexp)
            leg_worst = px
            rem -= take
            if rem <= 1e-9:
                break
        if rem > 1e-6:
            return {"filled": False}
        worst_bids.append(round(leg_worst, 4))

    net_rev_ps = (gross_rev - total_fee) / q_sh
    if net_rev_ps < min_net_proceeds_per_set:
        return {"filled": False, "net_proceeds_per_set": round(net_rev_ps, 4)}
    return {
        "filled": True,
        "shares": round(q_sh, 4),
        "gross_proceeds_per_set": round(gross_rev / q_sh, 4),
        "net_proceeds_per_set": round(net_rev_ps, 4),
        "fee_usd": round(total_fee, 4),
        "worst_leg_bids": worst_bids,
    }


def evaluate_locked_market_reward_carry(
    p_lock: float,
    best_bid: float,
    best_ask: float,
    rewards_min_size: float,
    rewards_max_spread_cents: float,
    fee_rate: float = 0.0,
) -> Dict[str, Any]:
    """
    Graveyard-safe `MKR_REWARD_LOCKED_CARRY`: posts `post_only=True` carry bids ONLY on already
    mathematically locked (`p_lock >= 0.995`), `0%`-fee outcomes where Gamma `rewardsMinSize > 0`
    is active and `0.95 <= bid_px <= 0.990`.
    """
    if fee_rate > 0.0 or p_lock < 0.995 or rewards_min_size <= 0.0 or best_ask <= 0.96:
        return {"eligible": False}
    bid_px = round(min(max(best_bid, 0.96), min(best_ask - 0.005, 0.989)), 3)
    max_spr = float(rewards_max_spread_cents) / 100.0 if rewards_max_spread_cents > 0.5 else float(rewards_max_spread_cents or 0.03)
    in_reward_zone = (best_ask - bid_px) <= max(0.02, max_spr + 1e-6)
    carry_edge = round(p_lock - bid_px, 4)
    if not (0.955 <= bid_px < best_ask and carry_edge >= 0.008 and in_reward_zone):
        return {"eligible": False}
    return {
        "eligible": True,
        "resting_bid": bid_px,
        "carry_edge": carry_edge,
        "rewards_min_size": rewards_min_size,
        "rewards_max_spread": round(max_spr, 4),
    }


# ==============================================================================
# 4. `GAS1_AAA_GASOLINE_LOCK`, `CM_SHOCK`, `AI1`, & `D2_12PM_BINANCE_BOX`
# ==============================================================================
_AAA_AS_OF_RE = re.compile(r"Price\s+as\s+of\s+(\d{1,2})/(\d{1,2})/(\d{2,4})", re.IGNORECASE)
_AAA_ROW_PRICES_RE = re.compile(r"\$(\d+\.\d{3,4})")


def parse_aaa_gas_html(html: str) -> Optional[Dict[str, Any]]:
    m_dt = _AAA_AS_OF_RE.search(str(html or ""))
    prices = [float(x) for x in _AAA_ROW_PRICES_RE.findall(str(html or "")) if 1.5 <= float(x) <= 9.5]
    if not m_dt or len(prices) < 6:
        return None
    mo, dy, yr_raw = int(m_dt.group(1)), int(m_dt.group(2)), int(m_dt.group(3))
    yr = 2000 + yr_raw if yr_raw < 100 else yr_raw
    try:
        as_of_date = date(yr, mo, dy)
    except ValueError:
        return None
    # AAA National Average table layout: [hero_regular, table_current_reg, mid, prem, diesel, e85, table_yesterday_reg, ...]
    cur_reg = prices[1] if abs(prices[0] - prices[1]) < 0.02 else prices[0]
    yest_reg = prices[6] if len(prices) > 6 else cur_reg
    return {
        "as_of_date": as_of_date.isoformat(),
        "current_regular": round(cur_reg, 4),
        "yesterday_regular": round(yest_reg, 4),
    }


def fetch_aaa_national_gas_sync(ttl_sec: float = 180.0) -> Optional[Dict[str, Any]]:
    global _AAA_GAS_CACHE
    now = time.time()
    if _AAA_GAS_CACHE[1] is not None and (now - _AAA_GAS_CACHE[0]) < ttl_sec:
        return _AAA_GAS_CACHE[1]
    try:
        req = urllib.request.Request("https://gasprices.aaa.com/", headers={"User-Agent": CHROME_UA})
        with urllib.request.urlopen(req, timeout=6.0) as r:
            parsed = parse_aaa_gas_html(r.read().decode("utf-8", errors="replace"))
        if parsed:
            _AAA_GAS_CACHE = (now, parsed)
            return parsed
    except Exception as exc:
        logger.debug(f"AAA gas fetch notice: {exc}")
    return _AAA_GAS_CACHE[1]


_GAS_LT_RE = re.compile(r"<\s*\$?\s*(\d+(?:\.\d+)?)")
_GAS_PL_RE = re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*\+")
_GAS_RG_RE = re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:[-–—]|\bto\b)\s*\$?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def parse_gas_daily_bracket(label: str) -> Optional[Tuple[float, float]]:
    s = str(label or "").strip()
    m1 = _GAS_LT_RE.search(s)
    if m1:
        return (0.0, float(m1.group(1)) - 1e-6)
    m2 = _GAS_PL_RE.search(s)
    if m2:
        return (float(m2.group(1)), float("inf"))
    m3 = _GAS_RG_RE.search(s)
    if m3:
        return (float(m3.group(1)), float(m3.group(2)))
    return None


def is_in_scheduled_macro_catalyst_window(now_ts: float) -> Tuple[bool, str]:
    """
    Restricts `CM_SHOCK_PYTH_CATALYST` strictly to institutional macro release windows in NY time:
      - `08:29 - 08:45 ET` Mon-Fri: US CPI / NFP / PPI / GDP / Retail Sales
      - `10:29 - 10:45 ET` Wed (or Thu holiday): EIA Weekly Petroleum Status Report (`WTI`)
      - `13:59 - 14:45 ET` Wed: FOMC Rate Decision & Powell Press Conference
    """
    dt = datetime.fromtimestamp(now_ts, tz=NY_TZ)
    if dt.weekday() >= 5:
        return False, ""
    hm = dt.hour * 60 + dt.minute
    if 8 * 60 + 29 <= hm <= 8 * 60 + 45:
        return True, "US_0830_MACRO_RELEASE"
    if dt.weekday() in (2, 3) and (10 * 60 + 29 <= hm <= 10 * 60 + 45):
        return True, "EIA_1030_PETROLEUM"
    if dt.weekday() == 2 and (13 * 60 + 59 <= hm <= 14 * 60 + 45):
        return True, "FOMC_1400_DECISION"
    return False, ""


def evaluate_pyth_catalyst_shock(
    asset: str,
    prev_spot: float,
    cur_spot: float,
    strike: float,
    direction: str,
    eff_session_hours: float,
    sigma_session: float,
    now_ts: float,
) -> Dict[str, Any]:
    """
    Graveyard-compliant `<1.5%` fee (`0.00%` Pyth `zero_fees`) scheduled macro release jump detector.
    Fires ONLY inside a verified macro catalyst window when `|ret| >= min_jump` and first-passage
    barrier probability jumps by `>= +0.055`.
    """
    in_win, cat_name = is_in_scheduled_macro_catalyst_window(now_ts)
    if not in_win or prev_spot <= 0 or cur_spot <= 0 or eff_session_hours <= 0.1:
        return {"eligible": False}
    ret = (cur_spot - prev_spot) / prev_spot
    min_jump = 0.0035 if asset == "SPY" else 0.0045
    if abs(ret) < min_jump:
        return {"eligible": False}
    eff_sec = (eff_session_hours / 1638.0) * (365.25 * 86400.0)
    p_before = first_passage_touch_prob(prev_spot, strike, eff_sec, sigma_session, direction, wick_vol_multiplier=1.10)
    p_after = first_passage_touch_prob(cur_spot, strike, eff_sec, sigma_session, direction, wick_vol_multiplier=1.10)
    dp = p_after - p_before
    if abs(dp) < 0.055:
        return {"eligible": False}
    side = "YES" if dp > 0 else "NO"
    p_fair = p_after if side == "YES" else (1.0 - p_after)
    return {
        "eligible": bool(0.22 <= p_fair <= 0.94),
        "catalyst": cat_name,
        "side": side,
        "p_fair": round(p_fair, 4),
        "delta_p": round(abs(dp), 4),
        "ret_pct": round(ret * 100.0, 3),
    }


def evaluate_ai_elo_ci_lock(
    leaderboard_rows: List[Dict[str, Any]],
    snapshot_ts: float,
    now_ts: float,
    tte_sec: float,
    max_snapshot_age_sec: float = 21600.0,
) -> Dict[str, Any]:
    """
    Evaluates final-36h (`tte_sec <= 129600`) LMArena Elo bootstrap confidence-interval lock.
    Strictly rejects any stale leaderboard snapshot (`now_ts - snapshot_ts > 6h`) so stale static
    files can NEVER trigger a trade.
    """
    if not leaderboard_rows or (now_ts - snapshot_ts) > max_snapshot_age_sec or not (600.0 <= tte_sec <= 129600.0):
        return {"eligible": False, "reason": "stale_or_outside_window"}
    rows_s = sorted(leaderboard_rows, key=lambda r: float(r.get("rating") or 0.0), reverse=True)
    if len(rows_s) < 2:
        return {"eligible": False}
    top = rows_s[0]
    top_org = str(top.get("organization") or "").strip()
    top_q025 = float(top.get("rating_q025") or 0.0)
    rival_q975 = max(
        (float(r.get("rating_q975") or 0.0) for r in rows_s[1:] if str(r.get("organization") or "").strip() != top_org),
        default=0.0,
    )
    ci_gap = top_q025 - rival_q975
    if not top_org or ci_gap < 6.0:
        return {"eligible": False, "ci_gap": round(ci_gap, 2)}
    p_lock = min(0.992, 0.955 + 0.0025 * min(15.0, ci_gap - 6.0))
    return {"eligible": True, "leader_org": top_org, "ci_gap": round(ci_gap, 2), "p_lock": round(p_lock, 4)}


def detect_d2_12pm_binance_boxes(
    hourly_spec: Dict[str, Any],
    k_1h: float,
    terminal_specs: List[Dict[str, Any]],
    min_corridor_bps: float = 25.0,
) -> List[Dict[str, Any]]:
    """
    Same-Exchange `Binance USDT` `11:00-12:00 PM ET` `1h` Up/Down vs `12:00 PM ET` Daily/Multi-Strike
    Corridor Dominance Detector (`|end_1h - end_12pm| <= 5s`, zero `USDT/USD` peg basis!).
    For `K_low < K_high`: buying `UP/YES(> K_low)` + `DOWN/NO(< K_high)` locks `$1.00` floor + `$2.00` corridor!
    """
    if k_1h <= 0:
        return []
    end_1h = float(hourly_spec["end_ts"])
    out: List[Dict[str, Any]] = []
    for ts_sp in terminal_specs:
        if ts_sp.get("is_downward"):
            continue
        if abs(float(ts_sp["end_ts"]) - end_1h) > 5.0:
            continue
        k_t = float(ts_sp["strike"])
        if k_t <= 0:
            continue
        k_lo, k_hi = min(k_1h, k_t), max(k_1h, k_t)
        corr_bps = (k_hi - k_lo) / k_lo * 10000.0
        if corr_bps < min_corridor_bps:
            continue
        if k_1h < k_t:
            leg_a = {"token_id": hourly_spec["up_token"], "opp_token_id": hourly_spec["down_token"], "condition_id": hourly_spec["condition_id"], "side": "UP", "label": f"1H_UP>{k_1h:g}", "market_id": hourly_spec["market_id"], "fee_rate": float(hourly_spec.get("fee_rate", 0.07)), "fee_exponent": 1.0, "strike": k_1h}
            leg_b = {"token_id": ts_sp["no_token"], "opp_token_id": ts_sp["yes_token"], "condition_id": ts_sp["condition_id"], "side": str(ts_sp.get("no_label", "NO")), "label": f"12PM_NO<{k_t:g}", "market_id": ts_sp["market_id"], "fee_rate": float(ts_sp.get("fee_rate", 0.07)), "fee_exponent": 1.0, "strike": k_t}
        else:
            leg_a = {"token_id": ts_sp["yes_token"], "opp_token_id": ts_sp["no_token"], "condition_id": ts_sp["condition_id"], "side": str(ts_sp.get("yes_label", "YES")), "label": f"12PM_YES>{k_t:g}", "market_id": ts_sp["market_id"], "fee_rate": float(ts_sp.get("fee_rate", 0.07)), "fee_exponent": 1.0, "strike": k_t}
            leg_b = {"token_id": hourly_spec["down_token"], "opp_token_id": hourly_spec["up_token"], "condition_id": hourly_spec["condition_id"], "side": "DOWN", "label": f"1H_DN<{k_1h:g}", "market_id": hourly_spec["market_id"], "fee_rate": float(hourly_spec.get("fee_rate", 0.07)), "fee_exponent": 1.0, "strike": k_1h}
        out.append({
            "asset": str(hourly_spec["asset"]),
            "k_low": k_lo,
            "k_high": k_hi,
            "corridor_bps": round(corr_bps, 2),
            "leg_a": leg_a,
            "leg_b": leg_b,
            "close_ts": max(end_1h, float(ts_sp["end_ts"])),
            "label": f"{leg_a['label']} + {leg_b['label']} ({corr_bps:.0f}bps)",
        })
    return out

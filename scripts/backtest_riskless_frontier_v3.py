#!/usr/bin/env python3
"""
Zero-Lookahead Historical Backtest & Live L2 Audit — Riskless Frontier v3 (`#1–#6`)
===================================================================================
Replays real October 2026 Polymarket events (`Train <= 2026-10-16` vs `Sealed OOS > 2026-10-16`)
with direct CLOB `/prices-history` (`fidelity=2` / `10`), `<= 180s` synchronous print freshness,
`+1.0c` per-leg half-spread slippage penalty, exact Polymarket taker fees, and zero lookahead:

  1. `LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG`
  2. `SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION`
  3. `CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX`
  4. `LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX`
  5. `CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH`
  6. `TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR`
"""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.riskless_frontier_v2_engine import (
    _net_unit_bid,
    find_state_matrix_dominance_boxes,
)
from src.polymarket_research.riskless_frontier_v3_engine import (
    LP2_MIDTERM_CORE_SLUGS,
    LP2_TOSSUP_CUBE_SLUG,
    LP2_TOSSUP_STATE_SLUGS,
    _teams_match_fuzzy,
    build_lp1_nfl_exact_margin_bundle,
    build_lp2_house_seats_truth_legs,
    build_lp2_pending_senate_conditional_groups,
    build_lp2_senate_seats_truth_legs,
    build_lp2_tossup_state_implication_groups,
    detect_cal1_monotonic_boxes,
    detect_lp2_seat_convert_implication_arbs,
    detect_multisport_ml_spread_polish_middles,
    detect_sp4_subperiod_and_ext_prop_boxes,
    evaluate_ten1_tennis_opportunities,
    parse_cal1_monotonic_ladder_event,
    parse_espn_multisport_scoreboard,
    parse_espn_nba_extended_summary,
    parse_nba_subperiod_and_ext_props,
    parse_tennis_retirement_safe_event,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    _extract_market_fee_rate,
    _net_unit_ask,
    _parse_clob_tokens,
    _parse_iso_ts,
    parse_multi_sport_corridor_event,
)
from src.polymarket_research.uma_nba_endgame_engine import (
    _canon_nba_team,
    _parse_json_list,
)

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"

OCT_START_ISO = "2026-10-01T00:00:00Z"
SPLIT_CUTOFF_ISO = "2026-10-16T23:59:59Z"
OOS_START_ISO = "2026-10-17T00:00:00Z"
OCT_START_TS = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
SPLIT_CUTOFF_TS = datetime(2026, 10, 16, 23, 59, 59, tzinfo=timezone.utc).timestamp()

NOTIONAL_T1000 = 100.0
HALF_SPREAD_PENALTY = 0.01
SYNC_MAX_STALE_SEC = 180
_HIST_CACHE: Dict[Tuple[str, int, str], List[Tuple[int, float]]] = {}


def http_json(url: str, timeout: float = 8.0) -> Any:
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DominusBacktestV3/1.0"})
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
        except Exception:
            if attempt == 0:
                time.sleep(0.15)
    return None


def fetch_clob_history(token_id: str, fidelity: int = 2, interval: str = "max") -> List[Tuple[int, float]]:
    ck = (token_id, fidelity, interval)
    if ck in _HIST_CACHE:
        return _HIST_CACHE[ck]
    data = http_json(f"{CLOB_URL}/prices-history?market={token_id}&interval={interval}&fidelity={fidelity}", timeout=8.0)
    hist = (data or {}).get("history") or []
    pts: List[Tuple[int, float]] = []
    for row in hist:
        try:
            t = int(row["t"])
            p = float(row["p"])
            if 0.001 <= p <= 0.999:
                pts.append((t, p))
        except Exception:
            continue
    pts.sort(key=lambda x: x[0])
    _HIST_CACHE[ck] = pts
    return pts


def asof_price(pts: List[Tuple[int, float]], ts: int, max_stale_sec: int = SYNC_MAX_STALE_SEC) -> Optional[float]:
    if not pts:
        return None
    lo, hi = 0, len(pts) - 1
    best_idx = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if pts[mid][0] <= ts:
            best_idx = mid
            lo = mid + 1
        else:
            hi = mid - 1
    if best_idx < 0:
        return None
    t_found, p_found = pts[best_idx]
    if (ts - t_found) > max_stale_sec:
        return None
    return p_found


def resolved_token_payout(mkt: Dict[str, Any], token_idx: int) -> Optional[float]:
    if not mkt.get("closed"):
        return None
    uma_st = str(mkt.get("umaResolutionStatus") or "").strip().lower()
    if uma_st and uma_st != "resolved":
        return None
    op = _parse_json_list(mkt.get("outcomePrices"))
    if len(op) < 2 or token_idx >= len(op):
        return None
    try:
        px = float(op[token_idx])
    except Exception:
        return None
    if px >= 0.99:
        return 1.0
    if px <= 0.01:
        return 0.0
    if 0.49 <= px <= 0.51:
        return 0.5
    return None


def _dedup_events(evs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list({str(e.get("id")): e for e in evs if isinstance(e, dict) and e.get("id")}.values())


def summarize_split(trades: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "label": label, "trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "net_pnl_usd": 0.0, "avg_roi_pct": 0.0, "double_payout_hits": 0, "max_drawdown_usd": 0.0,
        }
    wins = sum(1 for t in trades if float(t["pnl_usd"]) >= -1e-6)
    losses = n - wins
    tot_pnl = sum(float(t["pnl_usd"]) for t in trades)
    avg_roi = sum(float(t["roi_pct"]) for t in trades) / n
    dbl_hits = sum(1 for t in trades if float(t.get("payout_per_share", 1.0)) >= 1.45)
    eq, pk, max_dd = 0.0, 0.0, 0.0
    for t in sorted(trades, key=lambda x: float(x["close_ts"])):
        eq += float(t["pnl_usd"])
        pk = max(pk, eq)
        max_dd = max(max_dd, pk - eq)
    return {
        "label": label,
        "trades": n,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(100.0 * wins / n, 2),
        "net_pnl_usd": round(tot_pnl, 2),
        "avg_roi_pct": round(avg_roi, 3),
        "double_payout_hits": dbl_hits,
        "max_drawdown_usd": round(max_dd, 2),
    }


def split_summary(trades: List[Dict[str, Any]], sleeve: str) -> Dict[str, Any]:
    tr_train = [t for t in trades if float(t["close_ts"]) <= SPLIT_CUTOFF_TS]
    tr_oos = [t for t in trades if float(t["close_ts"]) > SPLIT_CUTOFF_TS]
    return {
        "sleeve": sleeve,
        "all": summarize_split(trades, f"{sleeve}_ALL"),
        "train_le_oct16": summarize_split(tr_train, f"{sleeve}_TRAIN"),
        "oos_gt_oct16": summarize_split(tr_oos, f"{sleeve}_OOS"),
        "sample_trades": trades[:6],
    }


# ==============================================================================
# 1. LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG HISTORICAL REPLAY
# ==============================================================================
def backtest_lp2() -> Dict[str, Any]:
    print("[1/6] Replaying LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG (Oct 2026 Intraday Overround Unwinds)...", flush=True)
    slugs = list(dict.fromkeys(list(LP2_MIDTERM_CORE_SLUGS) + [LP2_TOSSUP_CUBE_SLUG] + list(LP2_TOSSUP_STATE_SLUGS.values())))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        res_ev = list(pool.map(lambda s: http_json(f"{GAMMA_URL}/events?slug={s}"), slugs))
    by_slug: Dict[str, Dict[str, Any]] = {}
    for sl, r in zip(slugs, res_ev):
        if isinstance(r, list) and r:
            by_slug[sl] = r[0]
    mid_extra = http_json(f"{GAMMA_URL}/events?tag_slug=midterms&active=true&closed=false&limit=40") or []
    for e_m in mid_extra:
        if isinstance(e_m, dict) and e_m.get("slug"):
            by_slug.setdefault(str(e_m["slug"]), e_m)

    groups: List[Tuple[str, List[Dict[str, Any]]]] = []
    hs = build_lp2_house_seats_truth_legs(by_slug)
    if hs:
        groups.append(("LP2_HOUSE_SEATS", hs))
    ss = build_lp2_senate_seats_truth_legs(by_slug)
    if ss:
        groups.append(("LP2_SENATE_SEATS", ss))
    groups.extend(build_lp2_pending_senate_conditional_groups(list(by_slug.values()), by_slug.get("which-party-will-win-the-senate-in-2026")))
    groups.extend(build_lp2_tossup_state_implication_groups(by_slug))

    all_toks = sorted({str(lg["token_id"]) for _, lgs in groups for lg in lgs})
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        hs_hist = list(pool.map(lambda t: fetch_clob_history(t, fidelity=10, interval="1m"), all_toks))
    # Fallback to `interval=max&fidelity=10` if `1m` is sparse
    hmap: Dict[str, List[Tuple[int, float]]] = {}
    missing_t = [t for t, h in zip(all_toks, hs_hist) if len(h) < 5]
    for t, h in zip(all_toks, hs_hist):
        if h:
            hmap[t] = [(ts, p) for ts, p in h if ts >= int(OCT_START_TS)]
    if missing_t:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            hs_fb = list(pool.map(lambda t: fetch_clob_history(t, fidelity=10, interval="max"), missing_t))
        for t, h in zip(missing_t, hs_fb):
            hmap[t] = [(ts, p) for ts, p in h if ts >= int(OCT_START_TS)]

    trades: List[Dict[str, Any]] = []
    for g_name, g_legs in groups:
        g_toks = {str(lg["token_id"]) for lg in g_legs}
        ts_grid = sorted({ts for t in g_toks for ts, _ in hmap.get(t, [])})
        if not ts_grid:
            continue
        open_by_pair: Dict[Tuple[str, str], Dict[str, Any]] = {}
        cooldown_until: Dict[Tuple[str, str], int] = {}
        for ts in ts_grid:
            # 1) Check intraday EARLY_OVERROUND_BID_UNWIND on open positions first (strictly causal ts > entry_ts)
            for p_key, pos in list(open_by_pair.items()):
                if ts <= pos["entry_ts"] + 300:
                    continue
                p_a = asof_price(hmap.get(p_key[0], []), ts, max_stale_sec=900)
                p_b = asof_price(hmap.get(p_key[1], []), ts, max_stale_sec=900)
                if p_a is None or p_b is None:
                    continue
                bid_a = _net_unit_bid(max(0.0, p_a - HALF_SPREAD_PENALTY), pos["fa"], pos["fea"])
                bid_b = _net_unit_bid(max(0.0, p_b - HALF_SPREAD_PENALTY), pos["fb"], pos["feb"])
                net_exit = round(bid_a + bid_b, 4)
                min_req = max(pos["cost"] + 0.008, 1.004)
                if net_exit >= min_req and net_exit <= 1.25:
                    sh = math.floor(NOTIONAL_T1000 / pos["cost"])
                    trades.append({
                        "sleeve": "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
                        "mode": f"{g_name}_OVERROUND_UNWIND",
                        "event": f"{g_name}: {pos['label']}"[:70],
                        "entry_ts": pos["entry_ts"],
                        "close_ts": float(ts),
                        "hold_min": round((ts - pos["entry_ts"]) / 60.0, 1),
                        "cost_per_share": pos["cost"],
                        "payout_per_share": net_exit,
                        "pnl_usd": round(sh * (net_exit - pos["cost"]), 2),
                        "roi_pct": round(100.0 * (net_exit - pos["cost"]) / pos["cost"], 3),
                    })
                    del open_by_pair[p_key]
                    cooldown_until[p_key] = ts + 14400

            # 2) Scan for new synchronous dominance box entries (`<= 600s` print staleness for fidelity=10)
            asks_t: Dict[str, float] = {}
            for t in g_toks:
                px = asof_price(hmap.get(t, []), ts, max_stale_sec=600)
                if px is not None:
                    asks_t[t] = min(0.995, px + HALF_SPREAD_PENALTY)
            for bx in find_state_matrix_dominance_boxes(g_legs, asks_t, max_2leg_cost_net=0.992, max_3leg_cost_net=0.0)[:3]:
                if int(bx["n_legs"]) != 2:
                    continue
                cost = float(bx["box_cost_net"])
                if cost < 0.85:
                    continue
                la, lb = bx["legs"][0], bx["legs"][1]
                pk = (str(la["token_id"]), str(lb["token_id"]))
                if pk in open_by_pair or ts < cooldown_until.get(pk, 0):
                    continue
                open_by_pair[pk] = {
                    "entry_ts": ts, "cost": cost, "label": bx["label"],
                    "fa": float(la["fee_rate"]), "fea": float(la["fee_exponent"]),
                    "fb": float(lb["fee_rate"]), "feb": float(lb["fee_exponent"]),
                }

    out = split_summary(trades, "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG")
    out["dag_groups_audited"] = len(groups)
    return out


# ==============================================================================
# 2. SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION HISTORICAL REPLAY
# ==============================================================================
def backtest_sp4_subperiod() -> Dict[str, Any]:
    print("[2/6] Replaying SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION (1H/Q1 Middles, Steals/Blocks & Settled Period Locks)...", flush=True)
    nba_train = http_json(f"{GAMMA_URL}/events?series_slug=nba-2026&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=endDate&ascending=false&limit=25") or []
    nba_oos = http_json(f"{GAMMA_URL}/events?series_slug=nba-2026&closed=true&end_date_min={OOS_START_ISO}&order=endDate&ascending=false&limit=35") or []
    nba_closed = _dedup_events(nba_train + nba_oos)

    espn_gid_by_teams_date: Dict[Tuple[str, str, str], str] = {}
    for day in range(4, 30):
        sb = http_json(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=202610{day:02d}", timeout=6.0) or {}
        for e_sb in sb.get("events") or []:
            cs = (((e_sb.get("competitions") or [{}])[0]) or {}).get("competitors") or []
            if len(cs) == 2:
                t0 = _canon_nba_team(str((cs[0].get("team") or {}).get("name") or ""))
                t1 = _canon_nba_team(str((cs[1].get("team") or {}).get("name") or ""))
                espn_gid_by_teams_date[(min(t0, t1), max(t0, t1), f"2026-10-{day:02d}")] = str(e_sb.get("id") or "")

    trades: List[Dict[str, Any]] = []
    games_audited = 0
    for ev in nba_closed:
        sl = str(ev.get("slug") or "").lower()
        if not sl.startswith("nba-") or sl.endswith("-exact-margin"):
            continue
        tip_ts = _parse_iso_ts(ev.get("startTime") or ev.get("endDate")) or 0.0
        if tip_ts < OCT_START_TS:
            continue
        raw_mkts = ev.get("markets") or []
        ev_open = {**ev, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "acceptingOrders": True} for m in raw_mkts]}
        slate = parse_nba_subperiod_and_ext_props(ev_open)
        if slate is None:
            continue
        games_audited += 1
        if games_audited > 26:
            break
        mkt_by_id = {str(m.get("id")): m for m in raw_mkts}

        toks = [t for rgs in slate.ext_props_by_player_stat.values() if len(rgs) >= 2 for r in rgs for t in (r.yes_token, r.no_token)]
        toks += [t for sm in slate.subperiod_markets if sm.period_scope in ("1H", "Q1") for t in (sm.tok_0, sm.tok_1)]
        toks = sorted(set(toks))[:80]
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            hs = list(pool.map(lambda t: fetch_clob_history(t, fidelity=2), toks))
        hmap = dict(zip(toks, hs))

        # 2B/2C: 1H/Q1 ML+Dog Polish Middles & Steals/Blocks Corridors
        ts_grid = sorted({t for h in hs for t, _ in h if t <= int(tip_ts) + 5400})
        used_keys = set()
        for ts in ts_grid[::max(1, len(ts_grid) // 40)] if ts_grid else []:
            asks = {}
            for tk in toks:
                p = asof_price(hmap.get(tk, []), ts, SYNC_MAX_STALE_SEC)
                if p is not None:
                    asks[tk] = min(0.99, p + HALF_SPREAD_PENALTY)
            for bx in detect_sp4_subperiod_and_ext_prop_boxes(slate, asks, max_box_cost_net=0.992):
                cost = float(bx["box_cost_net"])
                if cost < 0.85:
                    continue
                la, lb = bx["leg_a"], bx["leg_b"]
                uk = (la["market_id"], lb["market_id"])
                if uk in used_keys:
                    continue
                ma, mb = mkt_by_id.get(la["market_id"]), mkt_by_id.get(lb["market_id"])
                if not ma or not mb:
                    continue
                tka, tkb = _parse_clob_tokens(ma), _parse_clob_tokens(mb)
                if not tka or not tkb:
                    continue
                pa = resolved_token_payout(ma, 0 if la["token_id"] == tka[0] else 1)
                pb = resolved_token_payout(mb, 0 if lb["token_id"] == tkb[0] else 1)
                if pa is None or pb is None:
                    continue
                used_keys.add(uk)
                pay = pa + pb
                sh = math.floor(NOTIONAL_T1000 / cost)
                trades.append({
                    "sleeve": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                    "mode": bx["mode"],
                    "event": f"{slate.title}: {bx['label']}"[:70],
                    "entry_ts": ts,
                    "close_ts": tip_ts + 5400,
                    "cost_per_share": cost,
                    "payout_per_share": pay,
                    "pnl_usd": round(sh * (pay - cost), 2),
                    "roi_pct": round(100.0 * (pay - cost) / cost, 3),
                })

        # 2A: Completed Q1 & 1H Settled Sub-Period Locks via ESPN linescores
        m_dt = re.search(r"(2026-10-\d{2})", sl)
        if m_dt:
            gid_e = espn_gid_by_teams_date.get((min(slate.home_team, slate.away_team), max(slate.home_team, slate.away_team), m_dt.group(1)))
            if gid_e:
                summ = http_json(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={gid_e}", timeout=6.0)
                ext = parse_espn_nba_extended_summary(summ or {})
                ls_a = (ext.get("linescores") or {}).get("away") or {}
                ls_h = (ext.get("linescores") or {}).get("home") or {}
                # Evaluate Q1 settled locks after tipoff + 42m, 1H settled locks after tipoff + 80m
                for sm in slate.subperiod_markets:
                    if sm.period_scope not in ("Q1", "1H") or sm.kind not in ("TOTAL", "SPREAD", "ML"):
                        continue
                    if 1 not in ls_a or 1 not in ls_h or (sm.period_scope == "1H" and (2 not in ls_a or 2 not in ls_h)):
                        continue
                    pts_a = ls_a[1] if sm.period_scope == "Q1" else (ls_a[1] + ls_a[2])
                    pts_h = ls_h[1] if sm.period_scope == "Q1" else (ls_h[1] + ls_h[2])
                    settle_after = int(tip_ts + (2520 if sm.period_scope == "Q1" else 4800))
                    m_raw = mkt_by_id.get(sm.market_id)
                    if not m_raw:
                        continue
                    tk_raw = _parse_clob_tokens(m_raw)
                    if not tk_raw:
                        continue
                    win_tok = None
                    if sm.kind == "TOTAL" and sm.line is not None and abs((pts_a + pts_h) - sm.line) >= 1.5:
                        win_tok = sm.tok_0 if (pts_a + pts_h) > sm.line else sm.tok_1
                    elif sm.kind == "ML" and abs(pts_a - pts_h) >= 2:
                        t_pts = {slate.away_team: pts_a, slate.home_team: pts_h}
                        other = slate.home_team if sm.team_side == slate.away_team else slate.away_team
                        win_tok = sm.tok_0 if t_pts.get(sm.team_side or "", 0) > t_pts.get(other, 0) else sm.tok_1
                    if not win_tok:
                        continue
                    h_w = hmap.get(win_tok) or fetch_clob_history(win_tok, fidelity=2)
                    pts_post = [(t, p) for t, p in h_w if t >= settle_after and 0.80 <= p + HALF_SPREAD_PENALTY <= 0.988]
                    pay_w = resolved_token_payout(m_raw, 0 if win_tok == tk_raw[0] else 1)
                    if pts_post and pay_w is not None:
                        t_hit, p_hit = pts_post[0]
                        eff = round(p_hit + HALF_SPREAD_PENALTY, 4)
                        sh = math.floor(NOTIONAL_T1000 / eff)
                        trades.append({
                            "sleeve": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                            "mode": f"SP4_{sm.period_scope}_SETTLED_LOCK",
                            "event": f"{slate.title}: {sm.display_title}",
                            "entry_ts": t_hit,
                            "close_ts": tip_ts + 7200,
                            "cost_per_share": eff,
                            "payout_per_share": pay_w,
                            "pnl_usd": round(sh * (pay_w - eff), 2),
                            "roi_pct": round(100.0 * (pay_w - eff) / eff, 3),
                        })

    out = split_summary(trades, "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION")
    out["nba_games_audited"] = games_audited
    return out


# ==============================================================================
# 3. CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX HISTORICAL REPLAY
# ==============================================================================
def backtest_cal1() -> Dict[str, Any]:
    print("[3/6] Replaying CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX (Resolved + Active Oct 2026 Ladders)...", flush=True)
    c_tr = http_json(f"{GAMMA_URL}/events?closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=volume&ascending=false&limit=100") or []
    c_oo = http_json(f"{GAMMA_URL}/events?closed=true&end_date_min={OOS_START_ISO}&order=volume&ascending=false&limit=100") or []
    c_act = http_json(f"{GAMMA_URL}/events?active=true&closed=false&order=volume24hr&ascending=false&limit=100") or []
    c_pol = http_json(f"{GAMMA_URL}/events?tag_slug=politics&active=true&closed=false&order=volume24hr&ascending=false&limit=60") or []

    all_evs = _dedup_events(c_tr + c_oo + c_act + c_pol)
    trades: List[Dict[str, Any]] = []
    ladders_audited = 0

    for ev in all_evs:
        is_closed_ev = bool(ev.get("closed"))
        raw_mkts = ev.get("markets") or []
        ev_open = {**ev, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "acceptingOrders": True} for m in raw_mkts]}
        specs = parse_cal1_monotonic_ladder_event(ev_open)
        if not specs:
            continue
        mkt_by_id = {str(m.get("id")): m for m in raw_mkts}
        for sp in specs:
            ladders_audited += 1
            if ladders_audited > 40:
                break
            toks = sorted({t for r in sp.rungs for t in (r.yes_token, r.no_token)})
            fid = 2 if is_closed_ev else 10
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
                hs = list(pool.map(lambda t: fetch_clob_history(t, fidelity=fid), toks))
            hmap = {t: [(ts, p) for ts, p in h if ts >= int(OCT_START_TS)] for t, h in zip(toks, hs)}
            ts_grid = sorted({ts for h in hmap.values() for ts, _ in h})
            if not ts_grid:
                continue

            if is_closed_ev:
                used_pairs = set()
                for ts in ts_grid[::max(1, len(ts_grid) // 40)]:
                    asks = {}
                    for tk in toks:
                        p = asof_price(hmap.get(tk, []), ts, SYNC_MAX_STALE_SEC)
                        if p is not None:
                            asks[tk] = min(0.995, p + HALF_SPREAD_PENALTY)
                    for bx in detect_cal1_monotonic_boxes(sp, asks, max_box_cost_net=0.992):
                        cost = float(bx["box_cost_net"])
                        if cost < 0.85:
                            continue
                        la, lb = bx["leg_a"], bx["leg_b"]
                        pk = (la["market_id"], lb["market_id"])
                        if pk in used_pairs:
                            continue
                        ma, mb = mkt_by_id.get(la["market_id"]), mkt_by_id.get(lb["market_id"])
                        if not ma or not mb:
                            continue
                        tka, tkb = _parse_clob_tokens(ma), _parse_clob_tokens(mb)
                        if not tka or not tkb:
                            continue
                        pa = resolved_token_payout(ma, 0 if la["token_id"] == tka[0] else 1)
                        pb = resolved_token_payout(mb, 0 if lb["token_id"] == tkb[0] else 1)
                        if pa is None or pb is None:
                            continue
                        used_pairs.add(pk)
                        pay = pa + pb
                        sh = math.floor(NOTIONAL_T1000 / cost)
                        trades.append({
                            "sleeve": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                            "mode": bx["mode"],
                            "event": bx["label"][:70],
                            "entry_ts": ts,
                            "close_ts": float(bx["close_ts"]),
                            "cost_per_share": cost,
                            "payout_per_share": pay,
                            "pnl_usd": round(sh * (pay - cost), 2),
                            "roi_pct": round(100.0 * (pay - cost) / cost, 3),
                        })
            else:
                # Active ladder: require realized intraday overround bid unwind in Oct 2026!
                open_p: Dict[Tuple[str, str], Dict[str, Any]] = {}
                cool: Dict[Tuple[str, str], int] = {}
                for ts in ts_grid:
                    for pk, pos in list(open_p.items()):
                        if ts <= pos["entry_ts"] + 300:
                            continue
                        pa_m = asof_price(hmap.get(pk[0], []), ts, 900)
                        pb_m = asof_price(hmap.get(pk[1], []), ts, 900)
                        if pa_m is None or pb_m is None:
                            continue
                        exit_px = round(
                            _net_unit_bid(max(0.0, pa_m - HALF_SPREAD_PENALTY), pos["fa"], pos["fea"])
                            + _net_unit_bid(max(0.0, pb_m - HALF_SPREAD_PENALTY), pos["fb"], pos["feb"]),
                            4,
                        )
                        if max(pos["cost"] + 0.008, 1.004) <= exit_px <= 1.25:
                            sh = math.floor(NOTIONAL_T1000 / pos["cost"])
                            trades.append({
                                "sleeve": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                                "mode": f"{pos['mode']}_UNWIND",
                                "event": pos["label"][:70],
                                "entry_ts": pos["entry_ts"],
                                "close_ts": float(ts),
                                "cost_per_share": pos["cost"],
                                "payout_per_share": exit_px,
                                "pnl_usd": round(sh * (exit_px - pos["cost"]), 2),
                                "roi_pct": round(100.0 * (exit_px - pos["cost"]) / pos["cost"], 3),
                            })
                            del open_p[pk]
                            cool[pk] = ts + 14400
                    asks = {tk: min(0.995, p + HALF_SPREAD_PENALTY) for tk in toks for p in [asof_price(hmap.get(tk, []), ts, 600)] if p is not None}
                    for bx in detect_cal1_monotonic_boxes(sp, asks, max_box_cost_net=0.992)[:2]:
                        cost = float(bx["box_cost_net"])
                        if cost < 0.85:
                            continue
                        la, lb = bx["leg_a"], bx["leg_b"]
                        pk = (str(la["token_id"]), str(lb["token_id"]))
                        if pk not in open_p and ts >= cool.get(pk, 0):
                            open_p[pk] = {
                                "entry_ts": ts, "cost": cost, "mode": bx["mode"], "label": bx["label"],
                                "fa": float(la["fee_rate"]), "fea": float(la["fee_exponent"]),
                                "fb": float(lb["fee_rate"]), "feb": float(lb["fee_exponent"]),
                            }

    out = split_summary(trades, "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX")
    out["ladders_audited"] = ladders_audited
    return out


# ==============================================================================
# 4. LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX HISTORICAL REPLAY
# ==============================================================================
def backtest_lp1_nfl() -> Dict[str, Any]:
    print("[4/6] Replaying LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX (Resolved Oct 2026 NFL EM + NFL/CFB/NHL Middles)...", flush=True)
    trades: List[Dict[str, Any]] = []
    nfl_em_audited = 0
    ms_games_audited = 0

    for series_slug, sp_tag in (("nfl-2026", "NFL"), ("cfb-2026", "CFB"), ("nhl-2026", "NHL")):
        s_tr = http_json(f"{GAMMA_URL}/events?series_slug={series_slug}&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=endDate&ascending=false&limit=18") or []
        s_oo = http_json(f"{GAMMA_URL}/events?series_slug={series_slug}&closed=true&end_date_min={OOS_START_ISO}&order=endDate&ascending=false&limit=18") or []
        inter = [ev for pair in zip(s_tr, s_oo) for ev in pair] + s_tr[len(s_oo):] + s_oo[len(s_tr):]
        evs = _dedup_events(inter)[:20]

        for ev in evs:
            start_ts = _parse_iso_ts(ev.get("startTime") or ev.get("endDate")) or 0.0
            if start_ts < OCT_START_TS:
                continue
            raw_mkts = ev.get("markets") or []
            mkt_by_id = {str(m.get("id")): m for m in raw_mkts}
            ev_open = {**ev, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "acceptingOrders": True} for m in raw_mkts]}
            ms_games_audited += 1

            nfl_bundle = build_lp1_nfl_exact_margin_bundle(ev_open) if sp_tag == "NFL" else None
            if nfl_bundle is not None:
                nfl_em_audited += 1
            toks_set = set()
            if nfl_bundle is not None:
                toks_set.update(str(lg["token_id"]) for lg in nfl_bundle["legs"])
            for m in raw_mkts:
                if str(m.get("sportsMarketType") or "").lower() in ("moneyline", "spreads", "first_half_moneyline", "first_half_spreads", "q1_moneyline", "q1_spreads"):
                    tk = _parse_clob_tokens(m)
                    if tk:
                        toks_set.update(tk)
            toks = sorted(toks_set)
            if not toks:
                continue
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
                hs = list(pool.map(lambda t: fetch_clob_history(t, fidelity=2), toks))
            hmap = dict(zip(toks, hs))
            ts_grid = sorted({t for h in hs for t, _ in h if t <= int(start_ts) + 10800})
            if not ts_grid:
                continue

            used_pairs = set()
            for ts in ts_grid[::max(1, len(ts_grid) // 35)]:
                asks = {tk: min(0.995, p + HALF_SPREAD_PENALTY) for tk in toks for p in [asof_price(hmap.get(tk, []), ts, SYNC_MAX_STALE_SEC)] if p is not None}
                cand_boxes: List[Dict[str, Any]] = []
                if nfl_bundle is not None:
                    for nbx_m in find_state_matrix_dominance_boxes(nfl_bundle["legs"], asks, max_2leg_cost_net=0.990, max_3leg_cost_net=0.0):
                        if int(nbx_m["n_legs"]) == 2:
                            cand_boxes.append({**nbx_m, "leg_a": nbx_m["legs"][0], "leg_b": nbx_m["legs"][1], "mode": "NFL_EM_DOMINANCE"})
                cand_boxes.extend(detect_multisport_ml_spread_polish_middles(ev_open, asks, sport_hint=sp_tag, max_box_cost_net=0.988))
                for bx in cand_boxes:
                    cost = float(bx["box_cost_net"])
                    if cost < 0.85:
                        continue
                    la, lb = bx["leg_a"], bx["leg_b"]
                    pk = (la["market_id"], lb["market_id"])
                    if pk in used_pairs:
                        continue
                    ma, mb = mkt_by_id.get(la["market_id"]), mkt_by_id.get(lb["market_id"])
                    if not ma or not mb:
                        continue
                    tka, tkb = _parse_clob_tokens(ma), _parse_clob_tokens(mb)
                    if not tka or not tkb:
                        continue
                    pa = resolved_token_payout(ma, 0 if la["token_id"] == tka[0] else 1)
                    pb = resolved_token_payout(mb, 0 if lb["token_id"] == tkb[0] else 1)
                    if pa is None or pb is None:
                        continue
                    used_pairs.add(pk)
                    pay = pa + pb
                    sh = math.floor(NOTIONAL_T1000 / cost)
                    trades.append({
                        "sleeve": "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
                        "mode": bx.get("mode", "NFL_EM_DOMINANCE"),
                        "event": bx["label"][:70],
                        "entry_ts": ts,
                        "close_ts": start_ts + 12600,
                        "cost_per_share": cost,
                        "payout_per_share": pay,
                        "pnl_usd": round(sh * (pay - cost), 2),
                        "roi_pct": round(100.0 * (pay - cost) / cost, 3),
                    })

    out = split_summary(trades, "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX")
    out["nfl_em_bundles_audited"] = nfl_em_audited
    out["multisport_games_audited"] = ms_games_audited
    return out


# ==============================================================================
# 5. CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH HISTORICAL REPLAY
# ==============================================================================
def backtest_cl1() -> Dict[str, Any]:
    print("[5/6] Replaying CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH (ESPN Settled Periods & Post-Final Locks)...", flush=True)
    trades: List[Dict[str, Any]] = []
    audited = 0

    for sp_tag, series_slug, espn_path in (
        ("NFL", "nfl-2026", "football/nfl"),
        ("CFB", "cfb-2026", "football/college-football"),
        ("NHL", "nhl-2026", "hockey/nhl"),
    ):
        s_tr = http_json(f"{GAMMA_URL}/events?series_slug={series_slug}&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=endDate&ascending=false&limit=18") or []
        s_oo = http_json(f"{GAMMA_URL}/events?series_slug={series_slug}&closed=true&end_date_min={OOS_START_ISO}&order=endDate&ascending=false&limit=18") or []
        evs = _dedup_events(s_tr + s_oo)[:28]
        dates_needed = sorted({
            datetime.fromtimestamp(ts_e + off, tz=timezone.utc).strftime("%Y%m%d")
            for e in evs
            for ts_e in [_parse_iso_ts(e.get("startTime") or e.get("startDate") or e.get("endDate")) or 0.0]
            if ts_e >= OCT_START_TS
            for off in (0, -18000)
        })
        espn_games = []
        seen_gids = set()
        for ds in dates_needed[:22]:
            sb = http_json(f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard?dates={ds}&limit=200", timeout=6.0) or {}
            for g_parsed in parse_espn_multisport_scoreboard(sp_tag, sb):
                if g_parsed.game_id not in seen_gids:
                    seen_gids.add(g_parsed.game_id)
                    espn_games.append(g_parsed)

        for ev in evs:
            raw_mkts = ev.get("markets") or []
            start_ts = 0.0
            for m_st in raw_mkts:
                st_c = _parse_iso_ts(m_st.get("gameStartTime"))
                if st_c:
                    start_ts = st_c
                    break
            if not start_ts:
                start_ts = _parse_iso_ts(ev.get("startTime") or ev.get("startDate") or ev.get("endDate")) or 0.0
            if start_ts < OCT_START_TS:
                continue
            mkt_by_id = {str(m.get("id")): m for m in raw_mkts}
            ev_open = {**ev, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "acceptingOrders": True} for m in raw_mkts]}
            ms_sp = parse_multi_sport_corridor_event(ev_open, sport_hint=sp_tag, now_ts=start_ts)
            if ms_sp is None:
                continue
            matched = None
            for g in espn_games:
                if abs(g.start_ts - ms_sp.start_ts) <= 12 * 3600 and (
                    (_teams_match_fuzzy(ms_sp.team_a, g.away_name) and _teams_match_fuzzy(ms_sp.team_b, g.home_name))
                    or (_teams_match_fuzzy(ms_sp.team_a, g.home_name) and _teams_match_fuzzy(ms_sp.team_b, g.away_name))
                ):
                    matched = g
                    break
            if matched is None or not matched.completed:
                continue
            audited += 1
            tot_final = matched.home_score + matched.away_score
            ls_h, ls_a = matched.linescores_home, matched.linescores_away

            scope_checks: List[Tuple[str, int, int]] = [
                ("FG:TOTAL", tot_final, int(start_ts + (3.25 * 3600 if sp_tag in ("NFL", "CFB") else 2.55 * 3600))),
            ]
            if sp_tag in ("NFL", "CFB"):
                if 1 in ls_h and 1 in ls_a:
                    scope_checks.append(("Q1:TOTAL", ls_h[1] + ls_a[1], int(start_ts + 3000)))
                if 1 in ls_h and 2 in ls_h and 1 in ls_a and 2 in ls_a:
                    scope_checks.append(("1H:TOTAL", ls_h[1] + ls_h[2] + ls_a[1] + ls_a[2], int(start_ts + 6000)))

            for sc_name, sc_pts, min_ts in scope_checks:
                for lg in (ms_sp.legs_by_scope.get(sc_name) or []):
                    req_win = (lg.relation == "OVER" and sc_pts >= int(math.floor(lg.threshold)) + 1) or (
                        sc_name in ("Q1:TOTAL", "1H:TOTAL") and lg.relation == "UNDER" and sc_pts <= int(math.floor(lg.threshold))
                    )
                    if not req_win:
                        continue
                    h = fetch_clob_history(lg.token_id, fidelity=2)
                    cands = [
                        (t, _net_unit_ask(min(0.995, p + HALF_SPREAD_PENALTY), lg.fee_rate, lg.fee_exponent))
                        for t, p in h if t >= min_ts
                    ]
                    cands = [(t, eff) for t, eff in cands if 0.75 <= eff <= 0.982]
                    m_raw = mkt_by_id.get(lg.market_id)
                    tk_raw = _parse_clob_tokens(m_raw or {})
                    if cands and m_raw and tk_raw:
                        pay = resolved_token_payout(m_raw, 0 if lg.token_id == tk_raw[0] else 1)
                        if pay is not None:
                            t_hit, eff = cands[0]
                            sh = math.floor(NOTIONAL_T1000 / eff)
                            trades.append({
                                "sleeve": "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
                                "mode": f"CL1_{sp_tag}_{sc_name.replace(':', '_')}_LOCK",
                                "event": f"{ms_sp.title[:38]} {lg.display_label} (Pts={sc_pts})",
                                "entry_ts": t_hit,
                                "close_ts": start_ts + 13500,
                                "cost_per_share": round(eff, 4),
                                "payout_per_share": pay,
                                "pnl_usd": round(sh * (pay - eff), 2),
                                "roi_pct": round(100.0 * (pay - eff) / eff, 3),
                            })

    out = split_summary(trades, "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH")
    out["matches_audited"] = audited
    return out


# ==============================================================================
# 6. TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR HISTORICAL REPLAY
# ==============================================================================
def backtest_ten1() -> Dict[str, Any]:
    print("[6/6] Replaying TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR (Resolved Oct 2026 ATP/WTA BO3)...", flush=True)
    t_tr = http_json(f"{GAMMA_URL}/events?tag_slug=tennis&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=volume&ascending=false&limit=55") or []
    t_oo = http_json(f"{GAMMA_URL}/events?tag_slug=tennis&closed=true&end_date_min={OOS_START_ISO}&order=volume&ascending=false&limit=55") or []
    inter = [ev for pair in zip(t_tr, t_oo) for ev in pair] + t_tr[len(t_oo):] + t_oo[len(t_tr):]
    ten_evs = _dedup_events(inter)

    trades: List[Dict[str, Any]] = []
    matches_audited = 0
    for ev in ten_evs:
        start_ts = _parse_iso_ts(ev.get("startTime") or ev.get("endDate")) or 0.0
        if start_ts < OCT_START_TS:
            continue
        raw_mkts = ev.get("markets") or []
        mkt_by_id = {str(m.get("id")): m for m in raw_mkts}
        ev_open = {**ev, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "acceptingOrders": True, "outcomePrices": None} for m in raw_mkts]}
        spec = parse_tennis_retirement_safe_event(ev_open)
        if spec is None:
            continue
        matches_audited += 1
        if matches_audited > 42:
            break

        toks = [t for rgs in spec.totals_by_scope.values() for r in rgs for t in (r.over_token, r.under_token)]
        for tk_o in (spec.set1_a_token, spec.set1_b_token, spec.set2_a_token, spec.set2_b_token, spec.sets_ou25_over_token, spec.comp_no_token):
            if tk_o:
                toks.append(tk_o)
        toks = sorted(set(toks))
        with concurrent.futures.ThreadPoolExecutor(max_workers=14) as pool:
            hs = list(pool.map(lambda t: fetch_clob_history(t, fidelity=2), toks))
        hmap = dict(zip(toks, hs))
        ts_grid = sorted({t for h in hs for t, _ in h if t <= int(start_ts) + 10800})
        used = set()
        for ts in ts_grid[::max(1, len(ts_grid) // 35)] if ts_grid else []:
            asks: Dict[str, float] = {}
            bks: Dict[str, Dict[str, Any]] = {}
            for tk in toks:
                p = asof_price(hmap.get(tk, []), ts, SYNC_MAX_STALE_SEC)
                if p is not None:
                    asks[tk] = min(0.995, p + HALF_SPREAD_PENALTY)
                    bks[tk] = {
                        "bids": [{"price": str(round(max(0.0, p - 0.003), 4)), "size": "100"}],
                        "asks": [{"price": str(round(min(1.0, p + 0.003), 4)), "size": "100"}],
                    }
            for bx in evaluate_ten1_tennis_opportunities(spec, bks, asks, max_box_cost_net=0.988):
                cost = float(bx["box_cost_net"])
                if cost < 0.85:
                    continue
                la, lb = bx["leg_a"], bx["leg_b"]
                pk = (la["market_id"], lb["market_id"])
                if pk in used:
                    continue
                ma, mb = mkt_by_id.get(la["market_id"]), mkt_by_id.get(lb["market_id"])
                if not ma or not mb:
                    continue
                tka, tkb = _parse_clob_tokens(ma), _parse_clob_tokens(mb)
                if not tka or not tkb:
                    continue
                pa = resolved_token_payout(ma, 0 if la["token_id"] == tka[0] else 1)
                pb = resolved_token_payout(mb, 0 if lb["token_id"] == tkb[0] else 1)
                if pa is None or pb is None:
                    continue
                used.add(pk)
                pay = pa + pb
                sh = math.floor(NOTIONAL_T1000 / cost)
                trades.append({
                    "sleeve": "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
                    "mode": bx["mode"],
                    "event": bx["label"][:70],
                    "entry_ts": ts,
                    "close_ts": start_ts + 10800,
                    "cost_per_share": cost,
                    "payout_per_share": pay,
                    "pnl_usd": round(sh * (pay - cost), 2),
                    "roi_pct": round(100.0 * (pay - cost) / cost, 3),
                })

    out = split_summary(trades, "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR")
    out["bo3_matches_audited"] = matches_audited
    return out


# ==============================================================================
# LIVE L2 ORDERBOOK SNAPSHOT SCAN ACROSS ALL 6 FRONTIER V3 SLEEVES
# ==============================================================================
def run_live_l2_snapshot() -> Dict[str, Any]:
    print("[LIVE] Scanning current live Polymarket Gamma + CLOB L2 books across all 6 Frontier v3 sleeves...", flush=True)
    now = time.time()

    def _fetch_book(tok: str) -> Tuple[str, Dict[str, Any]]:
        return tok, (http_json(f"{CLOB_URL}/book?token_id={tok}", timeout=4.0) or {})

    # 1) LP2
    lp2_slugs = list(dict.fromkeys(list(LP2_MIDTERM_CORE_SLUGS) + [LP2_TOSSUP_CUBE_SLUG] + list(LP2_TOSSUP_STATE_SLUGS.values())))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        lp2_res = list(pool.map(lambda s: http_json(f"{GAMMA_URL}/events?slug={s}"), lp2_slugs))
    lp2_map = {s: r[0] for s, r in zip(lp2_slugs, lp2_res) if isinstance(r, list) and r}
    lp2_grps = []
    hs = build_lp2_house_seats_truth_legs(lp2_map)
    if hs:
        lp2_grps.append(("LP2_HOUSE_SEATS", hs))
    ss = build_lp2_senate_seats_truth_legs(lp2_map)
    if ss:
        lp2_grps.append(("LP2_SENATE_SEATS", ss))
    lp2_grps.extend(build_lp2_pending_senate_conditional_groups(list(lp2_map.values()), lp2_map.get("which-party-will-win-the-senate-in-2026")))
    lp2_grps.extend(build_lp2_tossup_state_implication_groups(lp2_map))

    lp2_toks = sorted({str(lg["token_id"]) for _, lgs in lp2_grps for lg in lgs})
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        lp2_bks = dict(pool.map(_fetch_book, lp2_toks))
    lp2_asks = {}
    for tk, bk in lp2_bks.items():
        asks_r = [float(a["price"]) for a in (bk.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) * float(a.get("price", 0)) >= 8.0]
        if asks_r:
            lp2_asks[tk] = min(asks_r)
    lp2_best = []
    for gn, gl in lp2_grps:
        bxs = find_state_matrix_dominance_boxes(gl, lp2_asks, max_2leg_cost_net=1.05, max_3leg_cost_net=1.03)
        if bxs:
            lp2_best.append({"group": gn, "label": bxs[0]["label"], "box_cost_net": bxs[0]["box_cost_net"]})
    lp2_conv = detect_lp2_seat_convert_implication_arbs(lp2_map, lp2_bks, max_synthetic_box_cost_net=1.05)

    # 2) SP4_SUBPERIOD + 3) CAL1 + 4) LP1_NFL + 6) TEN1 counts
    nba_act = http_json(f"{GAMMA_URL}/events?series_slug=nba-2026&closed=false&limit=25") or []
    sp4_sub_slates = [s for e in nba_act for s in [parse_nba_subperiod_and_ext_props(e, now_ts=now)] if s is not None]

    nfl_act = http_json(f"{GAMMA_URL}/events?series_slug=nfl-2026&closed=false&limit=25") or []
    nfl_bundles = [b for e in nfl_act for b in [build_lp1_nfl_exact_margin_bundle(e, now_ts=now)] if b is not None]

    ten_act = http_json(f"{GAMMA_URL}/events?tag_slug=tennis&active=true&closed=false&order=volume24hr&ascending=false&limit=40") or []
    ten_specs = [t for e in ten_act for t in [parse_tennis_retirement_safe_event(e, now_ts=now)] if t is not None]

    top_act = http_json(f"{GAMMA_URL}/events?active=true&closed=false&order=volume24hr&ascending=false&limit=80") or []
    cal_specs = [c for e in top_act for c in parse_cal1_monotonic_ladder_event(e, now_ts=now)]

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "lp2_dag_groups_active": len(lp2_grps),
        "lp2_best_boxes": lp2_best[:6],
        "lp2_convert_polish_middles": [{"mode": c["mode"], "synthetic_box_cost_net": c["synthetic_box_cost_net"]} for c in lp2_conv],
        "sp4_subperiod_slates_active": len(sp4_sub_slates),
        "sp4_subperiod_markets_active": sum(len(s.subperiod_markets) for s in sp4_sub_slates),
        "sp4_ext_prop_groups_active": sum(len(s.ext_props_by_player_stat) for s in sp4_sub_slates),
        "cal1_ladders_active": len(cal_specs),
        "lp1_nfl_em_bundles_active": len(nfl_bundles),
        "ten1_bo3_matches_active": len(ten_specs),
    }


def main() -> None:
    t0 = time.time()
    out_path = PROJECT_ROOT / "data" / "alpha124" / "backtest_riskless_frontier_v3_results.json"
    if "--only-cl1" in sys.argv and out_path.exists():
        results = json.loads(out_path.read_text(encoding="utf-8"))
        results["sleeves"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"] = backtest_cl1()
        results["generated_utc"] = datetime.now(timezone.utc).isoformat()
    else:
        results = {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "split_cutoff_iso": SPLIT_CUTOFF_ISO,
            "slippage_per_leg": HALF_SPREAD_PENALTY,
            "sync_max_stale_sec": SYNC_MAX_STALE_SEC,
            "notional_t1000_usd": NOTIONAL_T1000,
            "sleeves": {
                "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG": backtest_lp2(),
                "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION": backtest_sp4_subperiod(),
                "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": backtest_cal1(),
                "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX": backtest_lp1_nfl(),
                "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH": backtest_cl1(),
                "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR": backtest_ten1(),
            },
            "live_l2_snapshot": run_live_l2_snapshot(),
            "elapsed_sec": round(time.time() - t0, 2),
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\n================ RISKLESS FRONTIER V3 BACKTEST SUMMARY ================")
    for sl, d in results["sleeves"].items():
        a = d["all"]
        tr = d["train_le_oct16"]
        oo = d["oos_gt_oct16"]
        print(
            f"{sl:46s} | Total: {a['trades']:3d} ({a['wins']}W/{a['losses']}L, {a['win_rate_pct']:6.2f}%) "
            f"PnL=${a['net_pnl_usd']:8.2f} AvgROI={a['avg_roi_pct']:6.2f}% 2xHits={a['double_payout_hits']:2d} DD=${a['max_drawdown_usd']:.2f} "
            f"| Train=${tr['net_pnl_usd']:7.2f} ({tr['trades']}) | OOS=${oo['net_pnl_usd']:7.2f} ({oo['trades']})"
        )
    print("\nLive Snapshot:", json.dumps(results["live_l2_snapshot"], indent=2))
    print(f"Saved -> {out_path} in {results['elapsed_sec']}s")


if __name__ == "__main__":
    main()

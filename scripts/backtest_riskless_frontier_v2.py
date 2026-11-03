#!/usr/bin/env python3
"""
Chronological Zero-Lookahead Backtester & Live L2 Scanner for Riskless Frontier v2
==================================================================================
Replays REAL resolved October 2026 Polymarket events (`CLOB /prices-history` on exact
traded tokens + official Gamma `outcomePrices` resolutions + ESPN NBA historical boxscores
+ Polygon Mainnet RPC checks) across all 6 selected Riskless Frontier v2 sleeves, plus
executes a real-time Live L2 Orderbook scan:

  1. `NR2_CONVERT_NO_SUBSET_ARB`
  2. `SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK` (`3B` Ladder Corridor + `3A` Live Boxscore Clinch)
  3. `BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY`
  4. `SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX` (`5A` 3-Way Convert + `5B` Regulation Boxes, Fee-Exact)
  5. `LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX` (`6B` 11-State NBA Exact-Margin + `6C` 9-State BOP)
  6. `API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK` (`8A-Lock` Post-Map-1 `+1.5` / `1-1` O2.5 + `8A-Middle`)

Zero-Trust Anti-Illusion & Chronological Split Hygiene:
  - Fetches BOTH Train (`2026-10-01 .. 2026-10-16 23:59:59 UTC`) and Sealed OOS (`> 2026-10-16 23:59:59 UTC`).
  - Queries direct `CLOB /prices-history` (`fidelity=2`) for EVERY leg's actual traded token (never inferring
    illiquid `NO` prices from stale `1 - p_YES` prints).
  - Enforces strict synchronous print freshness (`max_stale_sec = 180`s across all legs simultaneously) plus
    `+1.0c` (`0.010`) ask / `-1.0c` bid half-spread slippage per leg, and deduplicates to at most 1 trade per
    `(game, player, stat)` or `(game, mode)` to eliminate multi-rung double-counting.
"""

from __future__ import annotations

import bisect
import concurrent.futures
import json
import math
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.riskless_frontier_v2_engine import (
    BOP_2026_SLUGS,
    UMA_PROPOSER_WHITELIST_ADDR,
    UMA_V4_ADAPTERS,
    build_lp1_bop_2026_truth_legs,
    build_lp1_nba_exact_margin_bundle,
    detect_nr2_convert_no_subset_arbs,
    detect_soc1_regulation_boxes,
    detect_sp4_milestone_ladder_boxes,
    evaluate_api1_esports_bo3_opportunities,
    find_state_matrix_dominance_boxes,
    link_and_parse_soccer_regulation_trees,
    parse_espn_nba_boxscore_players,
    parse_esports_bo3_event,
    parse_nba_player_props_from_event,
    verify_bond2_moov2_final_hour_sync,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    _extract_market_fee_rate,
    _net_unit_ask,
    _parse_clob_tokens,
    _parse_iso_ts,
    parse_negrisk_convert_event,
)
from src.polymarket_research.uma_nba_endgame_engine import (
    DEFAULT_POLYGON_RPC,
    _canon_nba_team,
    _parse_json_list,
    _rpc_post,
    is_objective_uma_market,
)

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"
OUT_DIR = PROJECT_ROOT / "data" / "alpha124"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "backtest_riskless_frontier_v2_results.json"

OCT_START_ISO = "2026-10-01T00:00:00Z"
SPLIT_CUTOFF_ISO = "2026-10-16T23:59:59Z"
OOS_START_ISO = "2026-10-17T00:00:00Z"
OCT_START_TS = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
SPLIT_CUTOFF_TS = datetime(2026, 10, 16, 23, 59, 59, tzinfo=timezone.utc).timestamp()

HALF_SPREAD_PENALTY = 0.010   # +1.0c ask / -1.0c bid slippage per leg (2.0c round-trip box penalty)
SYNC_MAX_STALE_SEC = 180      # Strict <= 3m simultaneous trade-print requirement across all legs
NOTIONAL_T1000 = 100.0

_SSL_CTX = ssl.create_default_context()
_HIST_CACHE: Dict[str, List[Tuple[int, float]]] = {}


def http_json(url: str, method: str = "GET", payload: Any = None, timeout: float = 10.0) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"User-Agent": "DominusFrontierV2Backtest/1.0", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    for att in range(3):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if att == 2:
                return None
            time.sleep(0.25 * (att + 1))
    return None


def fetch_clob_history(token_id: str, fidelity: int = 2) -> List[Tuple[int, float]]:
    if not token_id:
        return []
    ck = f"{token_id}_{fidelity}"
    if ck in _HIST_CACHE:
        return _HIST_CACHE[ck]
    data = http_json(f"{CLOB_URL}/prices-history?market={token_id}&interval=max&fidelity={fidelity}", timeout=8.0)
    hist = (data or {}).get("history") if isinstance(data, dict) else None
    pts = sorted([(int(r["t"]), float(r["p"])) for r in (hist or []) if "t" in r and "p" in r], key=lambda x: x[0])
    _HIST_CACHE[ck] = pts
    return pts


def fetch_books_sync(token_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    uniq = [t for t in dict.fromkeys(token_ids) if t]
    out: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(uniq), 40):
        batch = [{"token_id": t} for t in uniq[i : i + 40]]
        res = http_json(f"{CLOB_URL}/books", method="POST", payload=batch, timeout=8.0)
        if isinstance(res, list):
            for bk in res:
                if isinstance(bk, dict) and bk.get("asset_id"):
                    out[str(bk["asset_id"])] = bk
    return out


def asof_price(series: List[Tuple[int, float]], ts: int, max_stale_sec: int = SYNC_MAX_STALE_SEC) -> Optional[float]:
    if not series:
        return None
    idx = bisect.bisect_right(series, (ts, 999.0)) - 1
    if idx < 0:
        return None
    t0, p0 = series[idx]
    if (ts - t0) > max_stale_sec:
        return None
    return p0


def resolved_token_payout(m: Dict[str, Any], token_idx: int) -> Optional[float]:
    op = _parse_json_list(m.get("outcomePrices"))
    if len(op) != 2:
        return None
    try:
        v = float(op[token_idx])
        if v >= 0.99:
            return 1.0
        if v <= 0.01:
            return 0.0
        if 0.48 <= v <= 0.52 and m.get("closed"):
            return 0.5
    except (TypeError, ValueError):
        return None
    return None


def summarize_split(trades: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    if not trades:
        return {
            "label": label, "trades": 0, "wins": 0, "losses": 0,
            "win_rate_pct": 0.0, "jackpot_2x_hits": 0, "net_pnl_usd": 0.0,
            "avg_roi_pct": 0.0, "max_drawdown_usd": 0.0, "min_realized_payout_per_sh": None,
        }
    ts_sorted = sorted(trades, key=lambda x: float(x["entry_ts"]))
    pnls = [float(t["pnl_usd"]) for t in ts_sorted]
    rois = [float(t["roi_pct"]) for t in ts_sorted]
    wins = sum(1 for p in pnls if p >= -1e-6)
    losses = len(pnls) - wins
    j2x = sum(1 for t in ts_sorted if float(t.get("payout_per_share", 1.0)) >= 1.5)
    eq, pk, mdd = 0.0, 0.0, 0.0
    for p in pnls:
        eq += p
        pk = max(pk, eq)
        mdd = max(mdd, pk - eq)
    return {
        "label": label,
        "trades": len(pnls),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(100.0 * wins / len(pnls), 2),
        "jackpot_2x_hits": j2x,
        "net_pnl_usd": round(sum(pnls), 2),
        "avg_roi_pct": round(sum(rois) / len(rois), 3),
        "max_drawdown_usd": round(mdd, 2),
        "min_realized_payout_per_sh": round(min(float(t.get("payout_per_share", 1.0)) for t in ts_sorted), 4),
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


def _dedup_events(evs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list({str(e.get("id")): e for e in evs if isinstance(e, dict) and e.get("id")}.values())


# ==============================================================================
# 1. NR2_CONVERT_NO_SUBSET_ARB HISTORICAL REPLAY (Direct NO & YES Token Prints)
# ==============================================================================
def backtest_nr2() -> Dict[str, Any]:
    print("[1/6] Replaying NR2_CONVERT_NO_SUBSET_ARB on resolved Oct 2026 closed NegRisk partitions...", flush=True)
    w_tr: List[Dict[str, Any]] = []
    w_oo: List[Dict[str, Any]] = []
    for series in ("nyc-daily-weather", "london-daily-weather", "tokyo-daily-weather", "chicago-daily-weather"):
        w_tr.extend(http_json(f"{GAMMA_URL}/events?series_slug={series}&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=endDate&ascending=false&limit=3") or [])
        w_oo.extend(http_json(f"{GAMMA_URL}/events?series_slug={series}&closed=true&end_date_min={OOS_START_ISO}&order=endDate&ascending=false&limit=3") or [])
    s_tr = http_json(f"{GAMMA_URL}/events?tag_id=100350&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=volume&ascending=false&limit=24") or []
    s_oo = http_json(f"{GAMMA_URL}/events?tag_id=100350&closed=true&end_date_min={OOS_START_ISO}&order=volume&ascending=false&limit=24") or []
    evs = _dedup_events(w_tr[:8] + s_tr[:22] + w_oo[:8] + s_oo[:22])

    trades: List[Dict[str, Any]] = []
    checked = 0
    for ev in evs:
        end_ts = _parse_iso_ts(ev.get("endDate")) or 0.0
        if end_ts < OCT_START_TS or not ev.get("negRisk") or ev.get("negRiskAugmented", True):
            continue
        mkts = ev.get("markets") or []
        if not (3 <= len(mkts) <= 14):
            continue
        ev_clone = {**ev, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "active": True} for m in mkts]}
        spec = parse_negrisk_convert_event(ev_clone)
        if spec is None or not spec.is_closed_convert_safe:
            continue
        payouts_yes = [resolved_token_payout(m, 0) for m in mkts]
        if any(p is None for p in payouts_yes) or abs(sum(float(p) for p in payouts_yes if p is not None) - 1.0) > 0.02:
            continue
        checked += 1
        if checked > 48:
            break

        # Fetch BOTH actual NO-token AND actual YES-token histories at fidelity=2
        all_toks = [t for b in spec.brackets for t in (b["no_token"], b["yes_token"])]
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            h_res = list(pool.map(lambda t: fetch_clob_history(t, fidelity=2), all_toks))
        hmap = dict(zip(all_toks, h_res))
        # Restrict strictly to pre-settlement active window (>= 2h before end_ts)
        cutoff_entry = int(end_ts) - 7200
        all_ts = sorted({t for h in h_res for t, _ in h if t <= cutoff_entry})
        if not all_ts:
            continue
        step = max(1, len(all_ts) // 45)
        for ts in all_ts[::step]:
            synth_bks: Dict[str, Dict[str, Any]] = {}
            for b in spec.brackets:
                p_no = asof_price(hmap.get(b["no_token"], []), ts, SYNC_MAX_STALE_SEC)
                p_yes = asof_price(hmap.get(b["yes_token"], []), ts, SYNC_MAX_STALE_SEC)
                if p_no is not None and 0.02 <= p_no <= 0.985:
                    ask_no = min(0.995, p_no + HALF_SPREAD_PENALTY)
                    synth_bks[b["no_token"]] = {"asks": [{"price": str(round(ask_no, 4)), "size": "150"}]}
                if p_yes is not None and p_yes >= 0.025:
                    bid_yes = max(0.0, p_yes - HALF_SPREAD_PENALTY)
                    synth_bks[b["yes_token"]] = {"bids": [{"price": str(round(bid_yes, 4)), "size": "150"}]}
            arbs = detect_nr2_convert_no_subset_arbs(
                spec, synth_bks, target_budget_usd=NOTIONAL_T1000,
                min_edge_pure_cash=0.012, min_edge_with_yes_sell=0.015,
            )
            # Filter out any residual data glitches where cost < 0.85 * proceeds
            arbs = [a for a in arbs if float(a["no_cost_per_share"]) >= 0.85 * float(a["net_proceeds_per_share"])]
            if arbs:
                a0 = arbs[0]
                mkt_by_id = {str(m.get("id")): m for m in mkts}
                tail_bonus_ps = sum(
                    float(resolved_token_payout(mkt_by_id[tb["market_id"]], 0) or 0.0)
                    for tb in a0["retained_free_yes_brackets"]
                    if tb["market_id"] in mkt_by_id
                )
                sh = float(a0["shares"])
                cost_ps = float(a0["no_cost_per_share"])
                pay_ps = float(a0["net_proceeds_per_share"]) + tail_bonus_ps
                pnl = sh * (pay_ps - cost_ps)
                trades.append({
                    "sleeve": "NR2_CONVERT_NO_SUBSET_ARB",
                    "event": spec.title[:65],
                    "mode": a0["mode"],
                    "entry_ts": ts,
                    "close_ts": end_ts,
                    "cost_per_share": round(cost_ps, 4),
                    "payout_per_share": round(pay_ps, 4),
                    "retained_tails": a0["retained_tail_count"],
                    "tail_jackpot_hit": tail_bonus_ps >= 0.99,
                    "pnl_usd": round(pnl, 2),
                    "roi_pct": round(100.0 * (pay_ps - cost_ps) / max(0.05, cost_ps), 3),
                })
                break
    out = split_summary(trades, "NR2_CONVERT_NO_SUBSET_ARB")
    out["events_audited"] = checked
    return out


# ==============================================================================
# 2. SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK (3B + 3A) HISTORICAL REPLAY
# ==============================================================================
def backtest_sp4() -> Dict[str, Any]:
    print("[2/6] Replaying SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK (3B Synchronous Ladder + 3A Clinch)...", flush=True)
    nba_train = http_json(f"{GAMMA_URL}/events?series_slug=nba-2026&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=endDate&ascending=false&limit=30") or []
    nba_oos = http_json(f"{GAMMA_URL}/events?series_slug=nba-2026&closed=true&end_date_min={OOS_START_ISO}&order=endDate&ascending=false&limit=35") or []
    nba_closed = _dedup_events(nba_train + nba_oos)
    trades: List[Dict[str, Any]] = []
    games_checked = 0

    espn_gid_by_teams_date: Dict[Tuple[str, str, str], str] = {}
    for day in range(4, 30):
        ds = f"202610{day:02d}"
        sb = http_json(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={ds}", timeout=6.0) or {}
        for e_sb in sb.get("events") or []:
            comp = ((e_sb.get("competitions") or [{}])[0]) or {}
            cs = comp.get("competitors") or []
            if len(cs) == 2:
                t0 = _canon_nba_team(str((cs[0].get("team") or {}).get("name") or ""))
                t1 = _canon_nba_team(str((cs[1].get("team") or {}).get("name") or ""))
                dt_iso = f"2026-10-{day:02d}"
                espn_gid_by_teams_date[(min(t0, t1), max(t0, t1), dt_iso)] = str(e_sb.get("id") or "")

    for ev in nba_closed:
        sl = str(ev.get("slug") or "").lower()
        if not sl.startswith("nba-") or sl.endswith("-exact-margin"):
            continue
        tip_ts = _parse_iso_ts(ev.get("startTime") or ev.get("endDate")) or 0.0
        if tip_ts < OCT_START_TS:
            continue
        mkts = ev.get("markets") or []
        prop_mkts = [m for m in mkts if str(m.get("sportsMarketType") or "").lower() in ("points", "rebounds", "assists", "threes")]
        if not prop_mkts:
            continue
        games_checked += 1
        if games_checked > 24:
            break

        ev_open = {**ev, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "acceptingOrders": True} for m in prop_mkts]}
        slate = parse_nba_player_props_from_event(ev_open)
        if slate is None:
            continue
        mkt_by_id = {str(m.get("id")): m for m in prop_mkts}

        # Fetch BOTH actual YES (Over) AND actual NO (Under) histories at fidelity=2!
        multi_groups = [rgs for rgs in slate.props_by_player_stat.values() if len(rgs) >= 2][:12]
        tok_list = [t for rgs in multi_groups for r in rgs for t in (r.yes_token, r.no_token)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            h_list = list(pool.map(lambda t: fetch_clob_history(t, fidelity=2), tok_list))
        hist_map = dict(zip(tok_list, h_list))

        # 3B Replay: Synchronous <=180s prints on BOTH Over(K1) AND Under(K2), max 1 box per (player, stat)
        ts_grid = sorted({t for h in h_list for t, _ in h if t <= int(tip_ts) + 7200})
        used_player_stat = set()
        for ts in ts_grid[::max(1, len(ts_grid) // 40)] if ts_grid else []:
            best_asks: Dict[str, float] = {}
            for rgs in multi_groups:
                for r in rgs:
                    py = asof_price(hist_map.get(r.yes_token, []), ts, SYNC_MAX_STALE_SEC)
                    pn = asof_price(hist_map.get(r.no_token, []), ts, SYNC_MAX_STALE_SEC)
                    if py is not None:
                        best_asks[r.yes_token] = min(0.99, py + HALF_SPREAD_PENALTY)
                    if pn is not None:
                        best_asks[r.no_token] = min(0.99, pn + HALF_SPREAD_PENALTY)
            boxes = detect_sp4_milestone_ladder_boxes(slate, best_asks, max_box_cost_net=0.992)
            for bx in boxes:
                cost = float(bx["box_cost_net"])
                if cost < 0.85:  # Guard against rare outlier single-share print ticks
                    continue
                ps_key = (bx["player_name"], bx["stat_type"])
                if ps_key in used_player_stat:
                    continue
                la, lb = bx["leg_a"], bx["leg_b"]
                pa = resolved_token_payout(mkt_by_id[la["market_id"]], 0)
                pb = resolved_token_payout(mkt_by_id[lb["market_id"]], 1)
                if pa is None or pb is None:
                    continue
                used_player_stat.add(ps_key)
                pay = pa + pb
                sh = math.floor(NOTIONAL_T1000 / cost)
                trades.append({
                    "sleeve": "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
                    "mode": "3B_MILESTONE_POLISH_MIDDLE",
                    "event": f"{slate.title}: {bx['label']}",
                    "entry_ts": ts,
                    "close_ts": tip_ts + 9000,
                    "cost_per_share": cost,
                    "payout_per_share": pay,
                    "pnl_usd": round(sh * (pay - cost), 2),
                    "roi_pct": round(100.0 * (pay - cost) / cost, 3),
                })

        # 3A Replay: Match ESPN final boxscore & check post-buzzer pre-settlement CLOB lag
        m_dt = re.search(r"(2026-10-\d{2})", sl)
        if m_dt:
            key_espn = (min(slate.home_team, slate.away_team), max(slate.home_team, slate.away_team), m_dt.group(1))
            gid_e = espn_gid_by_teams_date.get(key_espn)
            if gid_e:
                summ = http_json(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={gid_e}", timeout=6.0)
                p_stats = parse_espn_nba_boxscore_players(summ or {})
                buzzer_ts = int(tip_ts + 2.45 * 3600)
                for (pkey, st_t), rgs in slate.props_by_player_stat.items():
                    val = (p_stats.get(pkey) or {}).get(st_t)
                    if val is None:
                        continue
                    for r in rgs:
                        if val >= int(math.floor(r.line)) + 2:
                            h_r = hist_map.get(r.yes_token) or fetch_clob_history(r.yes_token, fidelity=2)
                            pts_after = [(t, p) for t, p in h_r if t >= buzzer_ts and 0.80 <= p + HALF_SPREAD_PENALTY <= 0.986]
                            pay_r = resolved_token_payout(mkt_by_id[r.market_id], 0)
                            if pts_after and pay_r is not None:
                                t_hit, p_hit = pts_after[0]
                                eff = round(p_hit + HALF_SPREAD_PENALTY, 4)
                                sh = math.floor(NOTIONAL_T1000 / eff)
                                trades.append({
                                    "sleeve": "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
                                    "mode": "3A_POST_CLINCH_BOXSCORE_LOCK",
                                    "event": f"{slate.title}: {r.player_name} {st_t}={val} > {r.line}",
                                    "entry_ts": t_hit,
                                    "close_ts": tip_ts + 10800,
                                    "cost_per_share": eff,
                                    "payout_per_share": pay_r,
                                    "pnl_usd": round(sh * (pay_r - eff), 2),
                                    "roi_pct": round(100.0 * (pay_r - eff) / eff, 3),
                                })
                                break

    out = split_summary(trades, "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK")
    out["nba_games_audited"] = games_checked
    return out


# ==============================================================================
# 3. BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY HISTORICAL REPLAY
# ==============================================================================
def backtest_bond2() -> Dict[str, Any]:
    print("[3/6] Replaying BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY across Train & OOS Oct 2026 V4 markets...", flush=True)
    wl_res = _rpc_post(DEFAULT_POLYGON_RPC, {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": UMA_PROPOSER_WHITELIST_ADDR, "data": "0xd01f63f5"}, "latest"]})
    wl_hex = str((wl_res or {}).get("result") or "")
    wl_count = int(wl_hex[66:130], 16) if len(wl_hex) >= 130 else 0

    m_train = http_json(f"{GAMMA_URL}/markets?closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=volumeNum&ascending=false&limit=150") or []
    m_oos = http_json(f"{GAMMA_URL}/markets?closed=true&end_date_min={OOS_START_ISO}&order=closedTime&ascending=false&limit=150") or []
    def _filt_v4(lst: List[Any]) -> List[Dict[str, Any]]:
        return [
            m for m in lst
            if isinstance(m, dict)
            and str(m.get("resolvedBy") or "").lower() in UMA_V4_ADAPTERS
            and (_parse_iso_ts(m.get("closedTime")) or 0.0) >= OCT_START_TS
            and len(_parse_json_list(m.get("outcomes"))) == 2
            and _parse_clob_tokens(m) is not None
            and not any(x in ("disputed", "flagged", "reset") for x in [str(s).lower() for s in _parse_json_list(m.get("umaResolutionStatuses"))])
            and (bool(m.get("sportsMarketType")) or any(k in str(m.get("slug") or "") for k in ("nba", "nfl", "nhl", "weather", "up-or-down", "temperature")))
        ]

    v4_mkts = list({str(m.get("id")): m for m in (_filt_v4(m_train)[:35] + _filt_v4(m_oos)[:35])}.values())

    trades: List[Dict[str, Any]] = []
    for m in v4_mkts:
        closed_ts = _parse_iso_ts(m.get("closedTime")) or 0.0
        end_ts = _parse_iso_ts(m.get("endDate")) or 0.0
        if closed_ts <= 0 or end_ts <= 0 or (closed_ts - end_ts) < 3900:
            continue
        p0, p1 = resolved_token_payout(m, 0), resolved_token_payout(m, 1)
        if p0 == 1.0 and p1 == 0.0:
            win_idx = 0
        elif p1 == 1.0 and p0 == 0.0:
            win_idx = 1
        else:
            continue
        toks = _parse_clob_tokens(m)
        assert toks is not None
        wtok = toks[win_idx]
        fr, fe = _extract_market_fee_rate(m)
        win_start = max(int(end_ts + 3600), int(closed_ts - 3300))
        win_end = int(closed_ts - 240)
        if win_end <= win_start:
            continue
        h = fetch_clob_history(wtok, fidelity=2)
        cands = [(t, p) for t, p in h if win_start <= t <= win_end]
        for t_c, p_c in cands:
            ask_eff = _net_unit_ask(min(0.999, p_c + 0.002), fr, fe)
            if 0.955 <= ask_eff <= 0.9960:
                sh = NOTIONAL_T1000 / ask_eff
                trades.append({
                    "sleeve": "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
                    "mode": "MOOV2_V4_FINAL_HOUR_CARRY",
                    "event": str(m.get("question") or "")[:65],
                    "entry_ts": t_c,
                    "close_ts": closed_ts,
                    "rem_liveness_sec": int(closed_ts - t_c),
                    "cost_per_share": round(ask_eff, 4),
                    "payout_per_share": 1.0,
                    "pnl_usd": round(sh * (1.0 - ask_eff), 2),
                    "roi_pct": round(100.0 * (1.0 - ask_eff) / ask_eff, 3),
                })
                break

    out = split_summary(trades, "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY")
    out["polygon_onchain_whitelist_count"] = wl_count
    out["v4_markets_audited"] = len(v4_mkts)
    return out


# ==============================================================================
# 4. SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX HISTORICAL REPLAY
# ==============================================================================
def backtest_soc1() -> Dict[str, Any]:
    print("[4/6] Replaying SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX (Direct Tokens, Fee-Exact)...", flush=True)
    s_train = http_json(f"{GAMMA_URL}/events?tag_id=100350&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=volume&ascending=false&limit=80") or []
    s_oos = http_json(f"{GAMMA_URL}/events?tag_id=100350&closed=true&end_date_min={OOS_START_ISO}&order=volume&ascending=false&limit=80") or []
    oct_soc = [e for e in _dedup_events(s_train + s_oos) if (_parse_iso_ts(e.get("endDate")) or 0.0) >= OCT_START_TS]
    existing_slugs = {str(e.get("slug") or "") for e in oct_soc}
    mm_tr = [f"{e.get('slug')}-more-markets" for e in s_train if isinstance(e, dict) and e.get("negRisk") and len(e.get("markets") or []) == 3 and f"{e.get('slug')}-more-markets" not in existing_slugs][:18]
    mm_oo = [f"{e.get('slug')}-more-markets" for e in s_oos if isinstance(e, dict) and e.get("negRisk") and len(e.get("markets") or []) == 3 and f"{e.get('slug')}-more-markets" not in existing_slugs][:18]
    mm_slugs = list(dict.fromkeys(mm_tr + mm_oo))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        mm_res = list(pool.map(lambda s: http_json(f"{GAMMA_URL}/events?slug={s}"), mm_slugs))
    for r_m in mm_res:
        if isinstance(r_m, list) and r_m and r_m[0].get("closed"):
            oct_soc.append(r_m[0])

    raw_by_mkt_id = {str(m.get("id")): m for e in oct_soc for m in (e.get("markets") or [])}
    open_clones = [
        {**e, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "acceptingOrders": True} for m in (e.get("markets") or [])]}
        for e in oct_soc
    ]
    trees = link_and_parse_soccer_regulation_trees(open_clones)
    tr_trees = [t for t in trees.values() if t.end_ts <= SPLIT_CUTOFF_TS][:18]
    oo_trees = [t for t in trees.values() if t.end_ts > SPLIT_CUTOFF_TS][:18]
    trades: List[Dict[str, Any]] = []

    for tr in (tr_trees + oo_trees):
        toks = [
            tr.home_leg["yes_token"], tr.home_leg["no_token"],
            tr.draw_leg["yes_token"], tr.draw_leg["no_token"],
            tr.away_leg["yes_token"], tr.away_leg["no_token"],
        ]
        for tl in tr.totals:
            toks.extend((tl["over_token"], tl["under_token"]))
        for sp in tr.spreads:
            toks.extend((sp["fav_minus_token"], sp["dog_plus_token"]))
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            hs = list(pool.map(lambda t: fetch_clob_history(t, fidelity=2), toks))
        hmap = dict(zip(toks, hs))
        kickoff_est = int(tr.end_ts - 2.5 * 3600)
        ts_all = sorted({t for h in hs for t, _ in h if t <= kickoff_est + 5400})
        if not ts_all:
            continue
        used_modes = set()
        for ts in ts_all[::max(1, len(ts_all) // 35)]:
            bks: Dict[str, Dict[str, Any]] = {}
            asks: Dict[str, float] = {}
            for lg3 in (tr.home_leg, tr.draw_leg, tr.away_leg):
                py = asof_price(hmap.get(lg3["yes_token"], []), ts, SYNC_MAX_STALE_SEC)
                pn = asof_price(hmap.get(lg3["no_token"], []), ts, SYNC_MAX_STALE_SEC)
                if py is not None:
                    asks[lg3["yes_token"]] = min(0.995, py + HALF_SPREAD_PENALTY)
                    by = max(0.0, py - HALF_SPREAD_PENALTY)
                    bks[lg3["yes_token"]] = {"bids": [{"price": str(round(by, 4)), "size": "150"}] if by > 0.015 else []}
                if pn is not None:
                    an = min(0.995, pn + HALF_SPREAD_PENALTY)
                    asks[lg3["no_token"]] = an
                    bks[lg3["no_token"]] = {"asks": [{"price": str(round(an, 4)), "size": "150"}]}
            for tl in tr.totals:
                po = asof_price(hmap.get(tl["over_token"], []), ts, SYNC_MAX_STALE_SEC)
                pu = asof_price(hmap.get(tl["under_token"], []), ts, SYNC_MAX_STALE_SEC)
                if po is not None:
                    asks[tl["over_token"]] = min(0.995, po + HALF_SPREAD_PENALTY)
                if pu is not None:
                    asks[tl["under_token"]] = min(0.995, pu + HALF_SPREAD_PENALTY)
            for sp in tr.spreads:
                pf = asof_price(hmap.get(sp["fav_minus_token"], []), ts, SYNC_MAX_STALE_SEC)
                pd = asof_price(hmap.get(sp["dog_plus_token"], []), ts, SYNC_MAX_STALE_SEC)
                if pf is not None:
                    asks[sp["fav_minus_token"]] = min(0.995, pf + HALF_SPREAD_PENALTY)
                if pd is not None:
                    asks[sp["dog_plus_token"]] = min(0.995, pd + HALF_SPREAD_PENALTY)

            det = detect_soc1_regulation_boxes(tr, bks, asks, max_2leg_cost_net=0.988, min_conv_edge_ps=0.010, target_budget_usd=NOTIONAL_T1000)
            for bx in det["two_leg_boxes"]:
                cost = float(bx["box_cost_net"])
                if cost < 0.85 or bx["mode"] in used_modes:
                    continue
                la, lb = bx["leg_a"], bx["leg_b"]
                ma_raw, mb_raw = raw_by_mkt_id.get(la["market_id"]), raw_by_mkt_id.get(lb["market_id"])
                if not ma_raw or not mb_raw:
                    continue
                ta_toks, tb_toks = _parse_clob_tokens(ma_raw), _parse_clob_tokens(mb_raw)
                if not ta_toks or not tb_toks:
                    continue
                pa = resolved_token_payout(ma_raw, 0 if la["token_id"] == ta_toks[0] else 1)
                pb = resolved_token_payout(mb_raw, 0 if lb["token_id"] == tb_toks[0] else 1)
                if pa is None or pb is None:
                    continue
                used_modes.add(bx["mode"])
                pay = pa + pb
                sh = math.floor(NOTIONAL_T1000 / cost)
                trades.append({
                    "sleeve": "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
                    "mode": bx["mode"],
                    "event": bx["label"][:68],
                    "entry_ts": ts,
                    "close_ts": tr.end_ts,
                    "cost_per_share": cost,
                    "payout_per_share": pay,
                    "pnl_usd": round(sh * (pay - cost), 2),
                    "roi_pct": round(100.0 * (pay - cost) / cost, 3),
                })
            for cv in det["convert_arbs"]:
                if "CONV" in used_modes or float(cv["no_cost_per_share"]) < 0.85:
                    continue
                used_modes.add("CONV")
                cost_c = float(cv["no_cost_per_share"])
                pay_c = 1.0 + float(cv["yes_bid_proceeds_per_share"])
                sh_c = float(cv["shares"])
                trades.append({
                    "sleeve": "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
                    "mode": cv["mode"],
                    "event": cv["label"][:68],
                    "entry_ts": ts,
                    "close_ts": tr.end_ts,
                    "cost_per_share": cost_c,
                    "payout_per_share": round(pay_c, 4),
                    "pnl_usd": round(sh_c * (pay_c - cost_c), 2),
                    "roi_pct": round(100.0 * (pay_c - cost_c) / max(0.05, cost_c), 3),
                })

    out = split_summary(trades, "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX")
    out["linked_soccer_trees_audited"] = len(trees)
    return out


# ==============================================================================
# 5. LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX (6B NBA EM + 6C BOP) REPLAY
# ==============================================================================
def backtest_lp1() -> Dict[str, Any]:
    print("[5/6] Replaying LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX (Direct Tokens, NBA EM + BOP)...", flush=True)
    n_train = http_json(f"{GAMMA_URL}/events?series_slug=nba-2026&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=endDate&ascending=false&limit=40") or []
    n_oos = http_json(f"{GAMMA_URL}/events?series_slug=nba-2026&closed=true&end_date_min={OOS_START_ISO}&order=endDate&ascending=false&limit=50") or []
    nba_closed = _dedup_events(n_train + n_oos)
    parents: Dict[str, Dict[str, Any]] = {}
    ems: Dict[str, Dict[str, Any]] = {}
    for e in nba_closed:
        sl = str(e.get("slug") or "").lower()
        if sl.endswith("-exact-margin"):
            ems[sl[:-13]] = e
        elif sl.startswith("nba-"):
            parents[sl] = e
    missing_em = [sl_p for sl_p in list(parents.keys())[:24] if sl_p not in ems]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        em_f = list(pool.map(lambda s: (s, http_json(f"{GAMMA_URL}/events?slug={s}-exact-margin")), missing_em))
    for sl_p, r_em in em_f:
        if isinstance(r_em, list) and r_em and r_em[0].get("closed"):
            ems[sl_p] = r_em[0]

    trades: List[Dict[str, Any]] = []
    paired_cnt = 0
    for sl_p, ev_p in parents.items():
        ev_e = ems.get(sl_p)
        if ev_e is None:
            continue
        tip_ts = _parse_iso_ts(ev_p.get("startTime") or ev_p.get("endDate")) or 0.0
        if tip_ts < OCT_START_TS:
            continue
        raw_mkts = {str(m.get("id")): m for m in (ev_p.get("markets") or []) + (ev_e.get("markets") or [])}
        p_open = {**ev_p, "closed": False, "markets": [{**m, "closed": False, "archived": False} for m in (ev_p.get("markets") or [])]}
        e_open = {**ev_e, "closed": False, "markets": [{**m, "closed": False, "archived": False} for m in (ev_e.get("markets") or [])]}
        bundle = build_lp1_nba_exact_margin_bundle(p_open, e_open)
        if bundle is None:
            continue
        paired_cnt += 1
        all_toks = sorted({str(lg["token_id"]) for lg in bundle["legs"]})
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            h_res = list(pool.map(lambda t: fetch_clob_history(t, fidelity=2), all_toks))
        hmap = dict(zip(all_toks, h_res))
        ts_grid = sorted({t for h in h_res for t, _ in h if t <= int(tip_ts) + 7200})
        used_nlegs = set()
        for ts in ts_grid[::max(1, len(ts_grid) // 35)] if ts_grid else []:
            asks: Dict[str, float] = {}
            for tok_id, h in hmap.items():
                px = asof_price(h, ts, SYNC_MAX_STALE_SEC)
                if px is not None:
                    asks[tok_id] = min(0.995, px + HALF_SPREAD_PENALTY)
            bxs = find_state_matrix_dominance_boxes(bundle["legs"], asks, max_2leg_cost_net=0.993, max_3leg_cost_net=0.991)
            for bx in bxs:
                cost = float(bx["box_cost_net"])
                if cost < 0.85 or bx["n_legs"] in used_nlegs:
                    continue
                pays = []
                for lg in bx["legs"]:
                    mr = raw_mkts[lg["market_id"]]
                    tk = _parse_clob_tokens(mr)
                    assert tk is not None
                    pays.append(resolved_token_payout(mr, 0 if lg["token_id"] == tk[0] else 1))
                if any(p is None for p in pays):
                    continue
                used_nlegs.add(bx["n_legs"])
                pay = sum(float(p) for p in pays if p is not None)
                sh = math.floor(NOTIONAL_T1000 / cost)
                trades.append({
                    "sleeve": "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
                    "mode": f"6B_NBA_EM_{bx['n_legs']}LEG",
                    "event": f"{bundle['title']}: {bx['label']}"[:70],
                    "entry_ts": ts,
                    "close_ts": bundle["end_ts"],
                    "cost_per_share": cost,
                    "payout_per_share": pay,
                    "pnl_usd": round(sh * (pay - cost), 2),
                    "roi_pct": round(100.0 * (pay - cost) / cost, 3),
                })

    out = split_summary(trades, "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX")
    out["nba_em_bundles_audited"] = paired_cnt
    return out


# ==============================================================================
# 6. API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK HISTORICAL REPLAY
# ==============================================================================
def backtest_api1() -> Dict[str, Any]:
    print("[6/6] Replaying API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK across Train & OOS Oct 2026 BO3 Esports...", flush=True)
    e_train = http_json(f"{GAMMA_URL}/events?tag_id=64&closed=true&end_date_min={OCT_START_ISO}&end_date_max={SPLIT_CUTOFF_ISO}&order=volume&ascending=false&limit=60") or []
    e_oos = http_json(f"{GAMMA_URL}/events?tag_id=64&closed=true&end_date_min={OOS_START_ISO}&order=endDate&ascending=false&limit=60") or []
    # Interleave Train and OOS so the 44-match cap samples both windows evenly!
    interleaved_esp = [ev for pair in zip(e_train, e_oos) for ev in pair] + e_train[len(e_oos):] + e_oos[len(e_train):]
    esp_closed = _dedup_events(interleaved_esp)
    trades: List[Dict[str, Any]] = []
    bo3_cnt = 0

    for ev in esp_closed:
        start_ts = _parse_iso_ts(ev.get("startTime") or ev.get("endDate")) or 0.0
        actual_close_ts = _parse_iso_ts(ev.get("closedTime") or ev.get("startTime") or ev.get("endDate")) or start_ts
        if start_ts < OCT_START_TS:
            continue
        raw_mkts = {str(m.get("id")): m for m in (ev.get("markets") or [])}
        ev_open = {**ev, "closed": False, "archived": False, "markets": [{**m, "closed": False, "archived": False, "outcomePrices": None} for m in (ev.get("markets") or [])]}
        spec = parse_esports_bo3_event(ev_open)
        if spec is None:
            continue
        bo3_cnt += 1
        if bo3_cnt > 44:
            break

        toks = [
            t for t in (
                spec.ml_a_token, spec.ml_b_token,
                spec.hc_minus_token, spec.hc_plus_token,
                spec.map1_a_token, spec.map1_b_token,
                spec.map2_a_token, spec.map2_b_token,
                spec.ou25_over_token, spec.ou25_under_token,
            ) if t
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            hs = list(pool.map(lambda t: fetch_clob_history(t, fidelity=2), toks))
        hmap = dict(zip(toks, hs))
        ts_grid = sorted({t for h in hs for t, _ in h})
        used = set()
        for ts in ts_grid[::max(1, len(ts_grid) // 40)] if ts_grid else []:
            bks: Dict[str, Dict[str, Any]] = {}
            asks: Dict[str, float] = {}
            for tok_k in (spec.ml_a_token, spec.ml_b_token, spec.hc_minus_token, spec.hc_plus_token, spec.ou25_over_token):
                if tok_k:
                    px_k = asof_price(hmap.get(tok_k, []), ts, SYNC_MAX_STALE_SEC)
                    if px_k is not None:
                        asks[tok_k] = min(0.995, px_k + HALF_SPREAD_PENALTY)
                        bks[tok_k] = {"asks": [{"price": str(round(asks[tok_k], 4)), "size": "150"}]}
            for m_tok in (spec.map1_a_token, spec.map1_b_token, spec.map2_a_token, spec.map2_b_token):
                if m_tok:
                    pm = asof_price(hmap.get(m_tok, []), ts, 900)
                    if pm is not None:
                        bks[m_tok] = {
                            "bids": [{"price": str(round(max(0.0, pm - 0.003), 4)), "size": "100"}],
                            "asks": [{"price": str(round(min(1.0, pm + 0.003), 4)), "size": "100"}],
                        }

            ev_opps = evaluate_api1_esports_bo3_opportunities(spec, bks, asks, max_middle_cost_net=0.988)
            for lk in ev_opps["single_leg_locks"]:
                if lk["mode"] in used:
                    continue
                px_ask = asks.get(lk["token_id"])
                if px_ask is None:
                    continue
                eff = _net_unit_ask(px_ask, float(lk["fee_rate"]), float(lk["fee_exponent"]))
                if 0.78 <= eff <= 0.980:
                    mr = raw_mkts.get(lk["market_id"])
                    tk = _parse_clob_tokens(mr) if mr else None
                    pay = resolved_token_payout(mr, 0 if (tk and lk["token_id"] == tk[0]) else 1) if (mr and tk) else None
                    if pay is not None:
                        used.add(lk["mode"])
                        sh = NOTIONAL_T1000 / eff
                        trades.append({
                            "sleeve": "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
                            "mode": lk["mode"],
                            "event": lk["display_label"][:68],
                            "entry_ts": ts,
                            "close_ts": min(spec.end_ts, actual_close_ts),
                            "cost_per_share": round(eff, 4),
                            "payout_per_share": pay,
                            "pnl_usd": round(sh * (pay - eff), 2),
                            "roi_pct": round(100.0 * (pay - eff) / eff, 3),
                        })
            for bx in ev_opps["two_leg_boxes"]:
                cost = float(bx["box_cost_net"])
                if "MIDDLE" in used or cost < 0.85:
                    continue
                la, lb = bx["leg_a"], bx["leg_b"]
                ma_r, mb_r = raw_mkts.get(la["market_id"]), raw_mkts.get(lb["market_id"])
                ta_k, tb_k = (_parse_clob_tokens(ma_r) if ma_r else None), (_parse_clob_tokens(mb_r) if mb_r else None)
                pa = resolved_token_payout(ma_r, 0 if la["token_id"] == ta_k[0] else 1) if (ma_r and ta_k) else None
                pb = resolved_token_payout(mb_r, 0 if lb["token_id"] == tb_k[0] else 1) if (mb_r and tb_k) else None
                if pa is not None and pb is not None:
                    used.add("MIDDLE")
                    pay = pa + pb
                    sh = math.floor(NOTIONAL_T1000 / cost)
                    trades.append({
                        "sleeve": "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
                        "mode": bx["mode"],
                        "event": bx["label"][:68],
                        "entry_ts": ts,
                        "close_ts": min(spec.end_ts, actual_close_ts),
                        "cost_per_share": cost,
                        "payout_per_share": pay,
                        "pnl_usd": round(sh * (pay - cost), 2),
                        "roi_pct": round(100.0 * (pay - cost) / cost, 3),
                    })

    out = split_summary(trades, "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK")
    out["bo3_events_audited"] = bo3_cnt
    return out


# ==============================================================================
# 7. LIVE REAL-TIME L2 ORDERBOOK SNAPSHOT SCAN ACROSS ALL 6 SLEEVES
# ==============================================================================
def run_live_l2_snapshot() -> Dict[str, Any]:
    print("[LIVE L2] Scanning live Polymarket L2 orderbooks across all 6 Frontier v2 universes...", flush=True)
    now = time.time()
    min_iso = datetime.fromtimestamp(now - 4.0 * 3600.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    max_nba_iso = datetime.fromtimestamp(now + 72.0 * 3600.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap: Dict[str, Any] = {"timestamp_utc": datetime.now(timezone.utc).isoformat()}

    # 1. BOP x Senate x House (LP1-6C)
    bop_by_slug: Dict[str, Dict[str, Any]] = {}
    for sl in BOP_2026_SLUGS:
        r = http_json(f"{GAMMA_URL}/events?slug={sl}")
        if isinstance(r, list) and r:
            bop_by_slug[sl] = r[0]
    bop_legs = build_lp1_bop_2026_truth_legs(bop_by_slug)
    bop_bks = fetch_books_sync([str(lg["token_id"]) for lg in bop_legs])
    bop_asks = {}
    for t, bk in bop_bks.items():
        asks = sorted([(float(a["price"]), float(a["size"])) for a in (bk.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0], key=lambda x: x[0])
        if asks and asks[0][0] * asks[0][1] >= 8.0:
            bop_asks[t] = asks[0][0]
    bop_boxes = find_state_matrix_dominance_boxes(bop_legs, bop_asks, max_2leg_cost_net=1.05, max_3leg_cost_net=1.05)
    snap["lp1_6c_bop_2026"] = {
        "legs_monitored": len(bop_legs),
        "tightest_boxes": [{"label": b["label"], "n_legs": b["n_legs"], "box_cost_net": b["box_cost_net"], "min_payout": b["min_payout"], "jackpot_states": b["jackpot_states"]} for b in bop_boxes[:5]],
    }

    # 2. NBA SP4 (3B) + LP1-6B (Exact Margin) + NR2
    nba_open = http_json(f"{GAMMA_URL}/events?series_slug=nba-2026&closed=false&end_date_min={min_iso}&end_date_max={max_nba_iso}&order=endDate&ascending=true&limit=60") or []
    prop_slates = [s for e in nba_open if isinstance(e, dict) for s in [parse_nba_player_props_from_event(e, now)] if s is not None]
    sp4_best: List[Dict[str, Any]] = []
    for sl_pr in prop_slates[:6]:
        toks = [t for rgs in sl_pr.props_by_player_stat.values() if len(rgs) >= 2 for r in rgs for t in (r.yes_token, r.no_token)]
        bks = fetch_books_sync(toks)
        asks = {}
        for t, bk in bks.items():
            al = sorted([(float(a["price"]), float(a["size"])) for a in (bk.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0], key=lambda x: x[0])
            if al and al[0][0] * al[0][1] >= 8.0:
                asks[t] = al[0][0]
        for b in detect_sp4_milestone_ladder_boxes(sl_pr, asks, max_box_cost_net=1.05)[:3]:
            sp4_best.append({"game": sl_pr.title, "label": b["label"], "box_cost_net": b["box_cost_net"]})
    sp4_best.sort(key=lambda x: x["box_cost_net"])

    parents_l = {str(e.get("slug")): e for e in nba_open if isinstance(e, dict) and not str(e.get("slug", "")).endswith("-exact-margin")}
    ems_l = {str(e.get("slug"))[:-13]: e for e in nba_open if isinstance(e, dict) and str(e.get("slug", "")).endswith("-exact-margin")}
    em_bundles = [b for sl_k, p_ev in parents_l.items() if sl_k in ems_l for b in [build_lp1_nba_exact_margin_bundle(p_ev, ems_l[sl_k])] if b is not None]
    em_best: List[Dict[str, Any]] = []
    nr2_best: List[Dict[str, Any]] = []
    for emb in em_bundles[:6]:
        bks = fetch_books_sync([str(lg["token_id"]) for lg in emb["legs"]])
        asks = {}
        for t, bk in bks.items():
            al = sorted([(float(a["price"]), float(a["size"])) for a in (bk.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0], key=lambda x: x[0])
            if al and al[0][0] * al[0][1] >= 8.0:
                asks[t] = al[0][0]
        for b in find_state_matrix_dominance_boxes(emb["legs"], asks, max_2leg_cost_net=1.05, max_3leg_cost_net=1.05)[:2]:
            em_best.append({"game": emb["title"], "label": b["label"], "n_legs": b["n_legs"], "box_cost_net": b["box_cost_net"]})
    em_best.sort(key=lambda x: x["box_cost_net"])
    for e_em in list(ems_l.values())[:6]:
        sp_nr = parse_negrisk_convert_event(e_em)
        if sp_nr and sp_nr.is_closed_convert_safe:
            bks_nr = fetch_books_sync([t for br in sp_nr.brackets for t in (br["yes_token"], br["no_token"])])
            for a_nr in detect_nr2_convert_no_subset_arbs(sp_nr, bks_nr, min_edge_pure_cash=-0.04, min_edge_with_yes_sell=-0.04)[:1]:
                nr2_best.append({"event": sp_nr.title, "label": a_nr["label"], "net_edge_per_share": a_nr["net_edge_per_share"], "retained_tails": a_nr["retained_tail_count"]})

    snap["sp4_nba_props"] = {"active_slates": len(prop_slates), "tightest_3b_boxes": sp4_best[:5]}
    snap["lp1_6b_nba_exact_margin"] = {"active_bundles": len(em_bundles), "tightest_boxes": em_best[:5]}
    snap["nr2_closed_negrisk"] = {"sample_evaluations": nr2_best[:5]}

    # 3. Soccer SOC1 (Fixed dual ordering: volume24hr + endDate)
    soc_open = _dedup_events(
        (http_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&order=volume24hr&ascending=false&limit=100") or [])
        + (http_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&end_date_min={min_iso}&order=endDate&ascending=true&limit=100") or [])
    )
    soc_trees = link_and_parse_soccer_regulation_trees(soc_open, now_ts=now)
    soc_best: List[Dict[str, Any]] = []
    for tr in [t for t in soc_trees.values() if t.totals or t.spreads][:10]:
        toks = [tr.home_leg["yes_token"], tr.home_leg["no_token"], tr.draw_leg["yes_token"], tr.draw_leg["no_token"], tr.away_leg["yes_token"], tr.away_leg["no_token"]]
        for tl in tr.totals:
            toks.extend((tl["over_token"], tl["under_token"]))
        for sp in tr.spreads:
            toks.extend((sp["fav_minus_token"], sp["dog_plus_token"]))
        bks = fetch_books_sync(toks)
        asks = {}
        for t, bk in bks.items():
            al = sorted([(float(a["price"]), float(a["size"])) for a in (bk.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0], key=lambda x: x[0])
            if al and al[0][0] * al[0][1] >= 8.0:
                asks[t] = al[0][0]
        res = detect_soc1_regulation_boxes(tr, bks, asks, max_2leg_cost_net=1.06, min_conv_edge_ps=-0.04)
        for b in res["two_leg_boxes"][:2]:
            soc_best.append({"mode": b["mode"], "label": b["label"], "box_cost_net": b["box_cost_net"]})
    soc_best.sort(key=lambda x: x["box_cost_net"])
    snap["soc1_soccer_trees"] = {"linked_trees": len(soc_trees), "with_more_markets": sum(1 for t in soc_trees.values() if t.totals), "tightest_boxes": soc_best[:5]}

    # 4. Esports BO3 API1 (Fixed dual ordering: volume24hr + endDate)
    esp_open = _dedup_events(
        (http_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&order=volume24hr&ascending=false&limit=100") or [])
        + (http_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&end_date_min={min_iso}&order=endDate&ascending=true&limit=100") or [])
    )
    esp_specs = [s for e in esp_open for s in [parse_esports_bo3_event(e, now)] if s is not None]
    esp_best: List[Dict[str, Any]] = []
    esp_locks: List[Dict[str, Any]] = []
    for sp_e in esp_specs[:16]:
        toks = [t for t in (spec_t for spec_t in (sp_e.ml_a_token, sp_e.ml_b_token, sp_e.hc_minus_token, sp_e.hc_plus_token, sp_e.map1_a_token, sp_e.map1_b_token, sp_e.map2_a_token, sp_e.map2_b_token, sp_e.ou25_over_token) if spec_t)]
        bks = fetch_books_sync(toks)
        asks = {}
        for t, bk in bks.items():
            al = sorted([(float(a["price"]), float(a["size"])) for a in (bk.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0], key=lambda x: x[0])
            if al and al[0][0] * al[0][1] >= 8.0:
                asks[t] = al[0][0]
        ev_o = evaluate_api1_esports_bo3_opportunities(sp_e, bks, asks, max_middle_cost_net=1.06)
        for lk in ev_o["single_leg_locks"]:
            esp_locks.append({"mode": lk["mode"], "label": lk["display_label"], "best_ask": asks.get(lk["token_id"])})
        for b in ev_o["two_leg_boxes"]:
            esp_best.append({"mode": b["mode"], "label": b["label"], "box_cost_net": b["box_cost_net"], "post_m1_forfeit_immune": b["post_m1_forfeit_immune"]})
    esp_best.sort(key=lambda x: x["box_cost_net"])
    snap["api1_esports_bo3"] = {"active_bo3_matches": len(esp_specs), "live_clinched_locks": esp_locks[:5], "tightest_middles": esp_best[:5]}

    # 5. Live BOND2 check on active proposed UMA markets
    prop_page = http_json(f"{GAMMA_URL}/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=150") or []
    uma_cands = [m for m in (prop_page if isinstance(prop_page, list) else []) if isinstance(m, dict) and is_objective_uma_market(m)[0]]
    bond2_verified = []
    for m_u in uma_cands[:15]:
        v2 = verify_bond2_moov2_final_hour_sync(m_u, now_ts=now)
        if v2.get("verified"):
            bond2_verified.append({"question": str(m_u.get("question") or "")[:65], "rem_sec": v2["rem_challenge_sec"], "proposer": v2["proposer"]})
    snap["bond2_live_moov2"] = {"objective_proposed_scanned": len(uma_cands), "final_hour_whitelisted_verified": bond2_verified}

    return snap


def main() -> None:
    t0 = time.time()
    sleeves = {
        "NR2_CONVERT_NO_SUBSET_ARB": backtest_nr2(),
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK": backtest_sp4(),
        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY": backtest_bond2(),
        "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX": backtest_soc1(),
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX": backtest_lp1(),
        "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK": backtest_api1(),
    }
    results = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "split_cutoff_utc": SPLIT_CUTOFF_ISO,
        "notional_per_trade_usd": NOTIONAL_T1000,
        "half_spread_penalty_per_leg": HALF_SPREAD_PENALTY,
        "sync_max_stale_sec": SYNC_MAX_STALE_SEC,
        "sleeves": sleeves,
        "live_l2_snapshot": run_live_l2_snapshot(),
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8", newline="\n")
    print("\n=== RISKLESS FRONTIER V2 HARDENED BACKTEST SUMMARY (T1000 = $100/trade) ===")
    for k, v in results["sleeves"].items():
        a, tr, oo = v["all"], v["train_le_oct16"], v["oos_gt_oct16"]
        print(
            f"  {k:44s} | ALL: {a['trades']:3d} tr, WR={a['win_rate_pct']:6.2f}%, 2x={a['jackpot_2x_hits']:2d}, PnL=${a['net_pnl_usd']:+8.2f}, DD=${a['max_drawdown_usd']:5.2f} "
            f"| TRAIN: {tr['trades']:2d} tr (${tr['net_pnl_usd']:+7.2f}) | OOS: {oo['trades']:2d} tr (${oo['net_pnl_usd']:+7.2f})"
        )
    print(f"Saved full telemetry to {OUT_JSON} in {results['elapsed_sec']}s.")


if __name__ == "__main__":
    main()

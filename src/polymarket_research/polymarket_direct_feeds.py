#!/usr/bin/env python3
"""
polymarket_direct_feeds.py
==========================
`$0.00/mo` Official League `liveData` Push Adapters & Dual-Source Conservative Reconcilers
for pure-riskless mathematical sports clinch sleeves (`SP2_NBA_ENDGAME_LOCK`, `CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH`,
`AFF1_FROZEN_SUBPERIOD_COLLAPSE`).

Endpoints (unauthenticated official league JSON feeds over persistent keep-alive TLS):
  1. NBA Official CDN (`https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json`)
  2. NHL Official Web API (`https://api-web.nhle.com/v1/score/now`)
  3. MLB Official StatsAPI (`https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=linescore`)

Zero-Loss Reconciliation Invariants:
  - Monotonic scores (`OVER` / period clinch): when both ESPN and the official league feed match a game,
    we take `min(espn_score, official_score)` and `max(espn_clock_sec, official_clock_sec)` so a single-feed
    typo or premature score increment can NEVER trigger a phantom pre-review lock!
  - `completed=True` (`FINAL` post-game clinch): allowed ONLY when the game is `post` AND if both feeds
    see the game, both agree `completed == True` with identical `(home_score, away_score)`!
  - If ESPN lags behind on discovering an active game or temporarily 503s, official league `FINAL` games
    (`completed == True` with `period >= regulation_periods` and `home_score != away_score`) provide zero-cost
    sub-second backup coverage, while in-play monotonic locks still pass through `ScoreConfirmationTracker`'s
    mandatory `90s` (`NHL`) / `75s` (`NFL`) / `180s` (`SOCCER`) anti-VAR hold timer.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.polymarket_research.riskless_frontier_v3_engine import LiveMultiSportGame
from src.polymarket_research.tradfi_sports_zero_fee_engine import _norm_team, _parse_iso_ts
from src.polymarket_research.uma_nba_endgame_engine import (
    CDN_NBA_SCOREBOARD_URL,
    LiveNbaGameState,
    _canon_nba_team,
    _parse_iso_clock_sec,
)

logger = logging.getLogger("PolymarketDirectFeeds")

NHL_OFFICIAL_SCORE_URL = "https://api-web.nhle.com/v1/score/now"
MLB_OFFICIAL_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=linescore"

_SESSION_LOCAL = threading.local()


def _get_keepalive_session() -> requests.Session:
    sess = getattr(_SESSION_LOCAL, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; DominusDirectFeed/1.0)",
                "Accept": "application/json",
                "Connection": "keep-alive",
            }
        )
        _SESSION_LOCAL.session = sess
    return sess


def parse_nba_cdn_scoreboard(payload: Dict[str, Any]) -> List[LiveNbaGameState]:
    """Parses official `cdn.nba.com` `todaysScoreboard_00.json` into `LiveNbaGameState` objects."""
    sb = (payload or {}).get("scoreboard") if isinstance((payload or {}).get("scoreboard"), dict) else (payload or {})
    games_raw = sb.get("games") if isinstance(sb, dict) else []
    out: List[LiveNbaGameState] = []
    for g in games_raw or []:
        if not isinstance(g, dict):
            continue
        gid = str(g.get("gameId") or "").strip()
        st_code = int(g.get("gameStatus") or 0)  # 1=pre, 2=in, 3=post (Final)
        state = "post" if st_code == 3 else ("in" if st_code == 2 else "pre")
        completed = st_code == 3
        period = int(g.get("period") or 0)
        clk_sec = 0.0 if completed else _parse_iso_clock_sec(g.get("gameClock"))
        start_ts = _parse_iso_ts(g.get("gameTimeUTC") or g.get("gameEt")) or 0.0
        ht = g.get("homeTeam") if isinstance(g.get("homeTeam"), dict) else {}
        at = g.get("awayTeam") if isinstance(g.get("awayTeam"), dict) else {}
        h_city = str(ht.get("teamCity") or "").strip()
        h_nick = str(ht.get("teamName") or "").strip()
        h_name = (f"{h_city} {h_nick}".strip() if (h_city and h_nick and h_city.lower() not in h_nick.lower()) else (h_nick or h_city))
        a_city = str(at.get("teamCity") or "").strip()
        a_nick = str(at.get("teamName") or "").strip()
        a_name = (f"{a_city} {a_nick}".strip() if (a_city and a_nick and a_city.lower() not in a_nick.lower()) else (a_nick or a_city))
        h_abbr = str(ht.get("teamTricode") or "").strip().upper()
        a_abbr = str(at.get("teamTricode") or "").strip().upper()
        try:
            h_sc = int(float(ht.get("score") or 0))
            a_sc = int(float(at.get("score") or 0))
        except Exception:
            continue
        if gid and h_name and a_name:
            out.append(
                LiveNbaGameState(
                    game_id=gid,
                    start_ts=start_ts,
                    state=state,
                    completed=completed,
                    period=period,
                    clock_sec=clk_sec,
                    home_name=h_name,
                    home_abbr=h_abbr,
                    home_score=h_sc,
                    away_name=a_name,
                    away_abbr=a_abbr,
                    away_score=a_sc,
                    source="nba_cdn",
                )
            )
    return out


def fetch_nba_cdn_scoreboard_sync(timeout: float = 2.8) -> List[LiveNbaGameState]:
    try:
        resp = _get_keepalive_session().get(CDN_NBA_SCOREBOARD_URL, timeout=timeout)
        if resp.status_code == 200:
            return parse_nba_cdn_scoreboard(resp.json())
    except Exception as exc:
        logger.debug(f"NBA CDN direct feed fetch notice: {exc}")
    return []


def _extract_nhl_team_str(team_obj: Dict[str, Any]) -> str:
    for k in ("commonName", "name", "placeName"):
        v = team_obj.get(k)
        if isinstance(v, dict):
            s = str(v.get("default") or "").strip()
            if s:
                return s
        elif isinstance(v, str) and v.strip():
            return v.strip()
    return str(team_obj.get("abbrev") or "").strip()


def parse_nhl_official_scoreboard(payload: Dict[str, Any]) -> List[LiveMultiSportGame]:
    """Parses `https://api-web.nhle.com/v1/score/now` into `LiveMultiSportGame` records."""
    games_raw = (payload or {}).get("games") if isinstance(payload, dict) else []
    out: List[LiveMultiSportGame] = []
    for g in games_raw or []:
        if not isinstance(g, dict):
            continue
        gs = str(g.get("gameState") or "").strip().upper()
        if gs == "OFF":
            state, completed = "post", True
        elif gs in ("FINAL", "LIVE", "CRIT"):
            state, completed = "in", False
        else:
            continue
        gid = str(g.get("id") or "").strip()
        start_ts = _parse_iso_ts(g.get("startTimeUTC")) or 0.0
        pd_desc = g.get("periodDescriptor") if isinstance(g.get("periodDescriptor"), dict) else {}
        period = int(pd_desc.get("number") or g.get("period") or 0)
        clk_obj = g.get("clock") if isinstance(g.get("clock"), dict) else {}
        in_intermission = bool(clk_obj.get("inIntermission", False))
        clk_sec = (
            0.0
            if completed
            else float(
                clk_obj.get("secondsRemaining")
                if clk_obj.get("secondsRemaining") is not None
                else _parse_iso_clock_sec(clk_obj.get("timeRemaining"))
            )
        )
        ht = g.get("homeTeam") if isinstance(g.get("homeTeam"), dict) else {}
        at = g.get("awayTeam") if isinstance(g.get("awayTeam"), dict) else {}
        h_name = _extract_nhl_team_str(ht)
        a_name = _extract_nhl_team_str(at)
        try:
            h_sc = int(float(ht.get("score") or 0))
            a_sc = int(float(at.get("score") or 0))
        except Exception:
            continue
        ls_h: Dict[int, int] = {}
        ls_a: Dict[int, int] = {}
        # Derive per-period goal totals when goals[] list is included in score/now
        if isinstance(g.get("goals"), list):
            h_ab = str(ht.get("abbrev") or "").strip().upper()
            a_ab = str(at.get("abbrev") or "").strip().upper()
            for gl in g.get("goals") or []:
                if not isinstance(gl, dict):
                    continue
                p_num = int((gl.get("periodDescriptor") or {}).get("number") or gl.get("period") or 0)
                t_ab = str((gl.get("teamAbbrev") or {}).get("default") if isinstance(gl.get("teamAbbrev"), dict) else (gl.get("teamAbbrev") or "")).strip().upper()
                if p_num >= 1:
                    if h_ab and t_ab == h_ab:
                        ls_h[p_num] = ls_h.get(p_num, 0) + 1
                    elif a_ab and t_ab == a_ab:
                        ls_a[p_num] = ls_a.get(p_num, 0) + 1
        if gid and h_name and a_name:
            out.append(
                LiveMultiSportGame(
                    sport="NHL",
                    game_id=gid,
                    start_ts=start_ts,
                    state=state,
                    completed=completed,
                    is_halftime=in_intermission and period == 1,
                    period=period,
                    clock_sec=clk_sec,
                    home_name=h_name,
                    away_name=a_name,
                    home_score=h_sc,
                    away_score=a_sc,
                    linescores_home=ls_h,
                    linescores_away=ls_a,
                )
            )
    return out


def fetch_nhl_official_scoreboard_sync(timeout: float = 2.8) -> List[LiveMultiSportGame]:
    try:
        resp = _get_keepalive_session().get(NHL_OFFICIAL_SCORE_URL, timeout=timeout)
        if resp.status_code == 200:
            return parse_nhl_official_scoreboard(resp.json())
    except Exception as exc:
        logger.debug(f"NHL official feed fetch notice: {exc}")
    return []


def parse_mlb_statsapi_scoreboard(payload: Dict[str, Any]) -> List[LiveMultiSportGame]:
    """Parses `statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=linescore` into `LiveMultiSportGame`."""
    out: List[LiveMultiSportGame] = []
    for dt_blk in (payload or {}).get("dates") or []:
        if not isinstance(dt_blk, dict):
            continue
        for g in dt_blk.get("games") or []:
            if not isinstance(g, dict):
                continue
            st = g.get("status") if isinstance(g.get("status"), dict) else {}
            abs_st = str(st.get("abstractGameState") or "").strip().lower()
            det_st = str(st.get("detailedState") or "").strip().lower()
            # Strictly exclude postponed/suspended/cancelled rain-shortened ambiguities unless official Final
            if any(bad in det_st for bad in ("postponed", "suspended", "cancelled", "canceled")):
                continue
            if abs_st == "final" and "final" in det_st:
                state, completed = "post", True
            elif abs_st == "live":
                state, completed = "in", False
            else:
                continue
            gid = str(g.get("gamePk") or "").strip()
            start_ts = _parse_iso_ts(g.get("gameDate")) or 0.0
            ls = g.get("linescore") if isinstance(g.get("linescore"), dict) else {}
            period = int(ls.get("currentInning") or 9 if completed else (ls.get("currentInning") or 0))
            tms = g.get("teams") if isinstance(g.get("teams"), dict) else {}
            hm = tms.get("home") if isinstance(tms.get("home"), dict) else {}
            aw = tms.get("away") if isinstance(tms.get("away"), dict) else {}
            h_name = str((hm.get("team") or {}).get("teamName") or (hm.get("team") or {}).get("name") or "").strip()
            a_name = str((aw.get("team") or {}).get("teamName") or (aw.get("team") or {}).get("name") or "").strip()
            try:
                h_sc = int(float(hm.get("score") if hm.get("score") is not None else ((ls.get("teams") or {}).get("home") or {}).get("runs") or 0))
                a_sc = int(float(aw.get("score") if aw.get("score") is not None else ((ls.get("teams") or {}).get("away") or {}).get("runs") or 0))
            except Exception:
                continue
            ls_h: Dict[int, int] = {}
            ls_a: Dict[int, int] = {}
            for inn in ls.get("innings") or []:
                if isinstance(inn, dict) and inn.get("num"):
                    idx = int(inn["num"])
                    if isinstance(inn.get("home"), dict) and inn["home"].get("runs") is not None:
                        ls_h[idx] = int(inn["home"]["runs"])
                    if isinstance(inn.get("away"), dict) and inn["away"].get("runs") is not None:
                        ls_a[idx] = int(inn["away"]["runs"])
            if gid and h_name and a_name:
                out.append(
                    LiveMultiSportGame(
                        sport="MLB",
                        game_id=gid,
                        start_ts=start_ts,
                        state=state,
                        completed=completed,
                        is_halftime=False,
                        period=period,
                        clock_sec=0.0,
                        home_name=h_name,
                        away_name=a_name,
                        home_score=h_sc,
                        away_score=a_sc,
                        linescores_home=ls_h,
                        linescores_away=ls_a,
                    )
                )
    return out


def fetch_mlb_statsapi_scoreboard_sync(timeout: float = 2.8) -> List[LiveMultiSportGame]:
    try:
        resp = _get_keepalive_session().get(MLB_OFFICIAL_SCHEDULE_URL, timeout=timeout)
        if resp.status_code == 200:
            return parse_mlb_statsapi_scoreboard(resp.json())
    except Exception as exc:
        logger.debug(f"MLB StatsAPI direct feed fetch notice: {exc}")
    return []


def reconcile_nba_dual_source_boards(
    espn_board: List[LiveNbaGameState],
    cdn_board: List[LiveNbaGameState],
) -> List[LiveNbaGameState]:
    """
    Conservative dual-source reconciler (`ESPN` + `cdn.nba.com`):
      - When both feeds observe the game:
          * `completed=True` (`state='post'`) ONLY if BOTH report `completed=True` AND identical `(home_score, away_score)`,
            OR if `cdn.nba.com` (official league scorer) reports `completed=True` while ESPN is still in final-seconds `in`
            with `cdn_score >= espn_score` on both sides and non-tied final score!
          * If the two feeds disagree on a `post` final score, downgrades `completed=False` (`state='in'`) to block phantom locks!
          * During `in`-play: uses conservative `min(espn_score, cdn_score)` and `max(espn_clock_sec, cdn_clock_sec)`.
      - When one feed is temporarily empty/unreachable, returns the healthy feed cleanly.
    """
    if not cdn_board:
        return list(espn_board or [])
    if not espn_board:
        return list(cdn_board)

    used_cdn_idx = set()
    merged: List[LiveNbaGameState] = []

    for eg in espn_board:
        eg_hk, eg_ak = _canon_nba_team(eg.home_name), _canon_nba_team(eg.away_name)
        cg: Optional[LiveNbaGameState] = None
        for idx_c, cand_c in enumerate(cdn_board):
            if idx_c in used_cdn_idx:
                continue
            cg_hk, cg_ak = _canon_nba_team(cand_c.home_name), _canon_nba_team(cand_c.away_name)
            if (eg_hk == cg_hk and eg_ak == cg_ak) or (
                _team_tokens_match(eg.home_name, cand_c.home_name)
                and _team_tokens_match(eg.away_name, cand_c.away_name)
            ):
                cg = cand_c
                used_cdn_idx.add(idx_c)
                break
        if cg is None:
            merged.append(eg)
            continue
        scores_match = (eg.home_score == cg.home_score) and (eg.away_score == cg.away_score)
        both_final = bool(eg.completed and cg.completed and scores_match)
        cdn_ahead_final = bool(
            cg.completed
            and not eg.completed
            and cg.period >= 4
            and eg.period >= 4
            and eg.clock_sec <= 35.0
            and cg.home_score != cg.away_score
            and cg.home_score >= eg.home_score
            and cg.away_score >= eg.away_score
        )
        if both_final or cdn_ahead_final:
            merged.append(
                LiveNbaGameState(
                    game_id=eg.game_id,
                    start_ts=eg.start_ts or cg.start_ts,
                    state="post",
                    completed=True,
                    period=max(eg.period, cg.period),
                    clock_sec=0.0,
                    home_name=eg.home_name,
                    home_abbr=eg.home_abbr or cg.home_abbr,
                    home_score=cg.home_score,
                    away_name=eg.away_name,
                    away_abbr=eg.away_abbr or cg.away_abbr,
                    away_score=cg.away_score,
                    source="nba_cdn+espn" if both_final else "nba_cdn_final",
                )
            )
        else:
            # Disagreement or still live -> strictly conservative min-score & max-clock!
            merged.append(
                LiveNbaGameState(
                    game_id=eg.game_id,
                    start_ts=eg.start_ts or cg.start_ts,
                    state="in" if ("in" in (eg.state, cg.state) or "post" in (eg.state, cg.state)) else eg.state,
                    completed=False,
                    period=min(eg.period, cg.period) if (eg.period > 0 and cg.period > 0) else max(eg.period, cg.period),
                    clock_sec=max(eg.clock_sec, cg.clock_sec),
                    home_name=eg.home_name,
                    home_abbr=eg.home_abbr or cg.home_abbr,
                    home_score=min(eg.home_score, cg.home_score),
                    away_name=eg.away_name,
                    away_abbr=eg.away_abbr or cg.away_abbr,
                    away_score=min(eg.away_score, cg.away_score),
                    source="nba_cdn+espn_min",
                )
            )

    for idx_c, cg in enumerate(cdn_board):
        if idx_c not in used_cdn_idx:
            merged.append(cg)
    return merged


def _team_tokens_match(a: str, b: str) -> bool:
    na, nb = _norm_team(a), _norm_team(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    ta = [w for w in na.split() if len(w) >= 3]
    tb = [w for w in nb.split() if len(w) >= 3]
    return bool(ta and tb and ta[-1] == tb[-1])


def reconcile_multisport_dual_source_boards(
    sport: str,
    espn_board: List[LiveMultiSportGame],
    official_board: List[LiveMultiSportGame],
) -> List[LiveMultiSportGame]:
    """
    Conservative dual-source reconciler (`ESPN` + Official `NHL` / `MLB` API):
      - Preserves ESPN `game_id` stability so `ScoreConfirmationTracker` anti-VAR timers never reset!
      - Takes conservative `min(espn_score, official_score)` on live games so a single-feed score glitch
        can NEVER trigger an unconfirmed `OVER` lock.
      - Allows `completed=True` (`post`) when both feeds agree on final score OR when the official league
        scorer (`api-web.nhle.com` / `statsapi.mlb.com`) marks `completed=True` with non-decreasing score
        in final regulation/OT!
    """
    if not official_board:
        return list(espn_board or [])
    if not espn_board:
        return list(official_board)

    used_off: set = set()
    merged: List[LiveMultiSportGame] = []
    min_reg_period = 3 if sport.upper() == "NHL" else (9 if sport.upper() == "MLB" else 2)

    for eg in espn_board:
        og_match: Optional[LiveMultiSportGame] = None
        best_idx_o: Optional[int] = None
        best_dt: float = float("inf")
        for idx_o, og in enumerate(official_board):
            if idx_o in used_off:
                continue
            dt_o = abs(float(eg.start_ts) - float(og.start_ts)) if (eg.start_ts > 0.0 and og.start_ts > 0.0) else 0.0
            if eg.start_ts > 0.0 and og.start_ts > 0.0 and dt_o > 5400.0:
                continue
            if _team_tokens_match(eg.home_name, og.home_name) and _team_tokens_match(eg.away_name, og.away_name):
                if dt_o < best_dt:
                    best_dt = dt_o
                    og_match = og
                    best_idx_o = idx_o
        if og_match is None or best_idx_o is None:
            merged.append(eg)
            continue
        used_off.add(best_idx_o)

        scores_eq = (eg.home_score == og_match.home_score) and (eg.away_score == og_match.away_score)
        both_final = bool(eg.completed and og_match.completed and scores_eq)
        off_ahead_final = bool(
            og_match.completed
            and not eg.completed
            and og_match.period >= min_reg_period
            and eg.period >= min_reg_period
            and og_match.home_score != og_match.away_score
            and og_match.home_score >= eg.home_score
            and og_match.away_score >= eg.away_score
        )
        if both_final or off_ahead_final:
            merged.append(
                LiveMultiSportGame(
                    sport=eg.sport,
                    game_id=eg.game_id,
                    start_ts=eg.start_ts or og_match.start_ts,
                    state="post",
                    completed=True,
                    is_halftime=False,
                    period=max(eg.period, og_match.period),
                    clock_sec=0.0,
                    home_name=eg.home_name,
                    away_name=eg.away_name,
                    home_score=og_match.home_score,
                    away_score=og_match.away_score,
                    linescores_home=eg.linescores_home or og_match.linescores_home,
                    linescores_away=eg.linescores_away or og_match.linescores_away,
                )
            )
        else:
            ls_h_min = dict(eg.linescores_home)
            for k_p, v_p in (og_match.linescores_home or {}).items():
                ls_h_min[k_p] = min(ls_h_min[k_p], v_p) if k_p in ls_h_min else v_p
            ls_a_min = dict(eg.linescores_away)
            for k_p, v_p in (og_match.linescores_away or {}).items():
                ls_a_min[k_p] = min(ls_a_min[k_p], v_p) if k_p in ls_a_min else v_p
            merged.append(
                LiveMultiSportGame(
                    sport=eg.sport,
                    game_id=eg.game_id,
                    start_ts=eg.start_ts or og_match.start_ts,
                    state="in",
                    completed=False,
                    is_halftime=bool(eg.is_halftime and og_match.is_halftime),
                    period=min(eg.period, og_match.period) if (eg.period > 0 and og_match.period > 0) else max(eg.period, og_match.period),
                    clock_sec=max(eg.clock_sec, og_match.clock_sec),
                    home_name=eg.home_name,
                    away_name=eg.away_name,
                    home_score=min(eg.home_score, og_match.home_score),
                    away_score=min(eg.away_score, og_match.away_score),
                    linescores_home=ls_h_min,
                    linescores_away=ls_a_min,
                )
            )

    for idx_o, og in enumerate(official_board):
        if idx_o not in used_off:
            merged.append(og)
    return merged

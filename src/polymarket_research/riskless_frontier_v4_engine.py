#!/usr/bin/env python3
"""
Riskless Frontier v4 Engine — Six Evergreen, High-Velocity Structural & Post-Outcome Sleeves
============================================================================================
Implements 6 repeatable, 365-day/year fee-exact riskless / irreversible-lock sleeves across
Sports, Soccer, NFL Props, Sum-Identities, Crypto Same-Oracle Inclusion, and Maker Rebate Locks
(strictly evergreen daily/weekly markets — zero single-event election dependencies):

  1. `AFF1_FROZEN_SUBPERIOD_COLLAPSE` (`Class I-A` + `Class III-B`, Fee-Exact):
     - Stateful `SubperiodFreezeTracker` confirms frozen sub-period scores (`Q1`, `1H`, `Q1..Q3`)
       with post-period scorer-review cooldown (`>= 45s`) and detects affine identity collapses:
         * `AFF1_POST_Q1_1H_VS_Q2`: `1H Total/Spread` vs `Q2 Total/Spread` (`15-25m` lockup, no OT).
         * `AFF1_HT_TEAM_TOTAL_FG_VS_2H`: `FG Team Total` vs `2H Team Total` shifted by frozen `1H`
           team score (both `FG` & `2H` NBA Team Totals include Overtime identically!).
         * `AFF1_POST_Q3_FG_VS_4Q`: 2-leg `OVER(FG) + UNDER(4Q)` (unconditional since `S_OT >= 0`)
           and 3-leg OT-immunized `UNDER(FG) + OVER(4Q) + YES(Overtime?)`.
         * `AFF1_Q1_FIRST_PASSAGE_CLINCH`: Live confirmed `Team to Score First` & `Race to 10/20/30`.

  2. `SOC2_EXACT_SCORE_2D_LATTICE` (`Class I-A` + `Class III-B`, Fee-Exact):
     - Links 3-Way `NegRisk` Moneyline, `-more-markets` (`Totals`, `Spreads`, `BTTS`), and
       `37`-bracket closed `-exact-score` (`0-0..5-5` + `Any Other Score`, `aug=False`).
     - Models `83` exhaustive states (`81` `(0..8)x(0..8)` score states + `2` cancellation conventions
       reflecting Polymarket's exact rule that `-exact-score` resolves `"0-0"` on cancellation while
       `-more-markets` resolves `50-50`!).
     - Emits post-VAR (`>= 210s`) `SOC2_DEAD_SCORE_NO_LOCK` on dead non-`0-0` score brackets
       (`$1.00` in every played state AND `$1.00` if abandoned!), `SOC2` 2D lattice boxes
       (e.g. `YES[0-0] + OVER[0.5 Goals]`), and closed-slate `NR2` `convertPositions` subsets.

  3. `NFL_PRP1_MILESTONE_AND_MAX_LOCKS` (`Class I-A` + `Class III-B`, Fee-Exact `3%`):
     - `NFL_PRP1_TD_POLISH_MIDDLE`: Same-player `YES(Anytime TD) + NO(2+ Touchdowns)` (`$1.00` floor
       across `{Inactive/DNP, 0 TD, >=2 TD, Canceled}`, `$2.00` on `Exact 1 TD`!) + `.5`-hook ladders.
     - `NFL_PRP1_LIVE_LOCKS`: Live ESPN NFL summary boxscore locks on running-maximum props
       (`longest_reception`, `longest_rush` with `>= 120s` penalty/challenge cooldown), monotonic
       counters (`receptions`, `passing_completions`, `passing_attempts`, `TDs`), `STATUS_FINAL`
       yardage locks, and post-kickoff official Inactive (`didNotPlay`) `"No"` TD locks.

  4. `SUM1_FRECHET_SUM_TRIANGLES` (`Class I-A`, Fee-Exact 3-Leg Sum Decomposition):
     - Detects upper (`Over X + Over Y + Under Z`, `K_Z >= K_X + K_Y - 0.5`) and lower
       (`Under X + Under Y + Over Z`, `K_Z <= K_X + K_Y + 1.5`) 3-leg additive sum triangles across
       verified identical-OT/cancellation triples (`Away TT + Home TT = FG Total`, `Q1 + Q2 = 1H`,
       and NBA `1H Team Total + 2H Team Total = FG Team Total`).

  5. `CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION` (`Class I-A`, Fee-Exact):
     - Same-oracle (`binance.com` Spot USDT `1m` kline) cross-event path-vs-terminal (`Close subset Hit`)
       and nested-horizon (`Daily subset Weekly subset Monthly`) 2-leg inclusion boxes with strict
       mid-period dynamic-rung `start_ts` guards.

  6. `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER` (`Class III-A/B`, `0%` Maker Fee + Rebate):
     - Converts taker-capped (`$0.990-$0.999` ask) confirmed `p_lock >= 0.997` locks (`TTE <= 4h`)
       into passive `post_only=True` resting Maker Bids (`$0.980-$0.991`), earning `0%` fee plus
       Polymarket's `20%` Maker Rebate share of the impatient seller's taker fee.
"""

from __future__ import annotations

import json
import math
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from src.polymarket_research.barrier_onetouch_svi_engine import (
    BarrierRungSpec,
    parse_barrier_direction,
    parse_hit_event,
    parse_strike_from_text,
)
from src.polymarket_research.riskless_frontier_v2_engine import (
    NegRiskConvertSlateSpec,
    _is_half_hook,
    canon_player_name,
    detect_nr2_convert_no_subset_arbs,
    find_state_matrix_dominance_boxes,
)
from src.polymarket_research.riskless_frontier_v3_engine import (
    LiveMultiSportGame,
    NbaSubperiodMarketSpec,
    ScoreConfirmationTracker,
    _teams_match_fuzzy,
    parse_nba_subperiod_and_ext_props,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    _SPREAD_FAV_RE,
    _extract_market_fee_rate,
    _net_unit_ask,
    _norm_team,
    _parse_clob_tokens,
    _parse_iso_ts,
)
from src.polymarket_research.uma_nba_endgame_engine import (
    _canon_nba_team,
    _parse_json_list,
)

FRONTIER_V4_GRAD8_SLEEVES: Tuple[str, ...] = (
    "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
    "SOC2_EXACT_SCORE_2D_LATTICE",
    "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
    "SUM1_FRECHET_SUM_TRIANGLES",
    "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",
    "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
)

ESPN_NFL_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={game_id}"


# ==============================================================================
# 1. SLEEVE #1: AFF1_FROZEN_SUBPERIOD_COLLAPSE
# ==============================================================================
@dataclass
class FirstPassageMarketSpec:
    event_id: str
    market_id: str
    condition_id: str
    kind: str             # "FIRST_SCORE" or "RACE_TO_X"
    target_pts: int       # 1 for FIRST_SCORE, or 10 / 20 / 30 for RACE_TO_X
    away_token: str
    home_token: str
    away_label: str
    home_label: str
    fee_rate: float
    fee_exponent: float
    settle_est_ts: float
    neg_risk: bool = False


@dataclass
class AffineGameBundle:
    sport: str            # "NBA", "NFL", "CFB"
    event_id: str
    slug: str
    title: str
    tipoff_ts: float
    settle_est_ts: float
    away_team: str
    home_team: str
    markets: List[NbaSubperiodMarketSpec] = field(default_factory=list)
    overtime_yes_leg: Optional[Dict[str, Any]] = None
    first_passage_markets: List[FirstPassageMarketSpec] = field(default_factory=list)

    @property
    def start_ts(self) -> float:
        return self.tipoff_ts


class SubperiodFreezeTracker:
    """
    Stateful freeze-confirmation guard for completed sports sub-periods (`Q1`, `1H`, `Q1_Q3`)
    and irreversible Q1 `Race to X` clinches:
      - Ensures a completed sub-period's linescore tuple `(away_pts, home_pts)` has remained
        strictly unchanged for `>= freeze_confirm_sec` (`45s` default) after the period ended
        before treating it as an immutable constant in `AFF1` affine box identities.
      - Latches `Race to X` / `First to Score` winners ONLY when observed live with
        `winner_pts >= X + buffer_pts` AT A MOMENT when `loser_pts < X`!
    """

    def __init__(self) -> None:
        self._frozen_since: Dict[Tuple[str, str, str], Tuple[Tuple[int, int], float]] = {}
        self._race_latched: Dict[Tuple[str, str, int], Tuple[str, float]] = {}

    def confirm_frozen_pair(
        self,
        sport: str,
        game_id: str,
        scope_key: str,
        away_pts: int,
        home_pts: int,
        period_ended: bool,
        now_ts: float,
        freeze_confirm_sec: float = 45.0,
        instant_settled: bool = False,
    ) -> Optional[Tuple[int, int]]:
        key = (sport.upper(), str(game_id), scope_key)
        if not period_ended:
            self._frozen_since.pop(key, None)
            return None
        pair = (int(away_pts), int(home_pts))
        prev = self._frozen_since.get(key)
        if prev is None or prev[0] != pair:
            self._frozen_since[key] = (pair, float(now_ts))
            if instant_settled or freeze_confirm_sec <= 0.0:
                return pair
            return None
        if instant_settled or (float(now_ts) - prev[1]) >= freeze_confirm_sec:
            return pair
        return None

    def observe_and_confirm_race_winner(
        self,
        sport: str,
        game_id: str,
        target_pts: int,
        away_score: int,
        home_score: int,
        now_ts: float,
        buffer_pts: int = 3,
        confirm_sec: float = 45.0,
        is_final: bool = False,
    ) -> Optional[str]:
        """
        Returns `"AWAY"` or `"HOME"` iff one team indisputably crossed `target_pts` strictly
        before the opponent reached `target_pts` and held `>= target_pts + buffer_pts` for `confirm_sec`.
        """
        key = (sport.upper(), str(game_id), int(target_pts))
        latched = self._race_latched.get(key)
        req_win = int(target_pts) + (0 if is_final else int(buffer_pts))

        if latched is not None:
            side, t0 = latched
            cur_w = away_score if side == "AWAY" else home_score
            cur_l = home_score if side == "AWAY" else away_score
            # Verify winner's score was not reverted below req_win by scorer review,
            # and opponent did not also cross target_pts before confirmation completed!
            if cur_w < req_win:
                self._race_latched.pop(key, None)
                return None
            elapsed = float(now_ts) - t0
            if not is_final and elapsed < confirm_sec and cur_l >= int(target_pts):
                self._race_latched.pop(key, None)
                return None
            if is_final or elapsed >= confirm_sec:
                return side
            return None

        # Latch ONLY if one team >= req_win WHILE the other team is STILL strictly < target_pts!
        if away_score >= req_win and home_score < int(target_pts):
            self._race_latched[key] = ("AWAY", float(now_ts))
            return "AWAY" if (is_final or confirm_sec <= 0.0) else None
        if home_score >= req_win and away_score < int(target_pts):
            self._race_latched[key] = ("HOME", float(now_ts))
            return "HOME" if (is_final or confirm_sec <= 0.0) else None
        return None

    def prune(self, now_ts: float, max_age_sec: float = 21600.0) -> int:
        cutoff = float(now_ts) - float(max_age_sec)
        dead_f = [k for k, (_, t0) in self._frozen_since.items() if t0 < cutoff]
        for k in dead_f:
            del self._frozen_since[k]
        dead_r = [k for k, (_, t0) in self._race_latched.items() if t0 < cutoff]
        for k in dead_r:
            del self._race_latched[k]
        return len(dead_f) + len(dead_r)


_AFFINE_SMT_MAP: Dict[str, Tuple[str, str]] = {
    "totals": ("FG", "TOTAL"),
    "spreads": ("FG", "SPREAD"),
    "moneyline": ("FG", "ML"),
    "first_half_totals": ("1H", "TOTAL"),
    "first_half_spreads": ("1H", "SPREAD"),
    "first_half_moneyline": ("1H", "ML"),
    "q1_totals": ("Q1", "TOTAL"),
    "q2_totals": ("Q2", "TOTAL"),
    "q3_totals": ("Q3", "TOTAL"),
    "q4_totals": ("Q4", "TOTAL"),
    "q1_spreads": ("Q1", "SPREAD"),
    "q2_spreads": ("Q2", "SPREAD"),
    "q3_spreads": ("Q3", "SPREAD"),
    "q4_spreads": ("Q4", "SPREAD"),
    "team_totals": ("FG", "TEAM_TOTAL"),
    "first_half_team_totals": ("1H", "TEAM_TOTAL"),
    "second_half_team_totals": ("2H", "TEAM_TOTAL"),
}

_RACE_PTS_RE = re.compile(r"race\s+to\s+(\d+)\s+points", re.IGNORECASE)


def _canon_sport_team(sport: str, raw: str) -> str:
    return _canon_nba_team(raw) if sport.upper() == "NBA" else _norm_team(raw)


def parse_affine_game_bundle(
    events: List[Dict[str, Any]],
    now_ts: Optional[float] = None,
) -> List[AffineGameBundle]:
    """
    Links parent + `-more-markets` events for NBA (`nba-*`), NFL (`nfl-*`), and CFB (`cfb-*`)
    into `AffineGameBundle` objects containing `FG` + sub-period `TOTAL`, `SPREAD`, `TEAM_TOTAL`,
    `basketball_game_overtime`, and `First to Score` / `Race to X` markets.
    """
    grouped_evs: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events or []:
        if not isinstance(ev, dict) or ev.get("closed") or ev.get("archived"):
            continue
        slug = str(ev.get("slug") or "").lower()
        if not slug.startswith(("nba-", "nfl-", "cfb-")):
            continue
        if any(slug.endswith(s) for s in ("-exact-margin", "-player-props", "-halftime-result")):
            continue
        base_slug = re.sub(r"-more-markets$", "", slug)
        grouped_evs.setdefault(base_slug, []).append(ev)

    bundles: List[AffineGameBundle] = []
    for base_slug, ev_list in grouped_evs.items():
        sport = "NBA" if base_slug.startswith("nba-") else ("NFL" if base_slug.startswith("nfl-") else "CFB")
        primary = next((e for e in ev_list if str(e.get("slug") or "").lower() == base_slug), ev_list[0])
        title = re.sub(r"\s*-\s*More Markets\s*$", "", str(primary.get("title") or ""), flags=re.I).strip()
        parts = re.split(r"\s+(?:vs\.?|@)\s+", title, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            continue
        away_t = _canon_sport_team(sport, parts[0])
        home_t = _canon_sport_team(sport, parts[1])
        if not away_t or not home_t or away_t == home_t:
            continue
        tip_ts = _parse_iso_ts(primary.get("startTime") or primary.get("gameStartTime") or primary.get("endDate")) or 0.0
        if tip_ts <= 0.0 or (now_ts is not None and tip_ts < now_ts - 8.0 * 3600.0):
            continue
        settle_ts = tip_ts + (3.25 if sport == "NBA" else 3.75) * 3600.0
        ev_id = str(primary.get("id") or "")

        mkts_parsed: List[NbaSubperiodMarketSpec] = []
        ot_yes_leg: Optional[Dict[str, Any]] = None
        fp_mkts: List[FirstPassageMarketSpec] = []
        seen_mids = set()

        for ev in ev_list:
            for m in ev.get("markets") or []:
                mid = str(m.get("id") or "")
                if not mid or mid in seen_mids or m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
                    continue
                seen_mids.add(mid)
                toks = _parse_clob_tokens(m)
                outs = [str(o).strip() for o in _parse_json_list(m.get("outcomes"))]
                if not toks or len(outs) != 2:
                    continue
                fr, fe = _extract_market_fee_rate(m)
                smt = str(m.get("sportsMarketType") or "").strip().lower()
                q_txt = str(m.get("groupItemTitle") or m.get("question") or "").strip()
                q_full = str(m.get("question") or q_txt).strip()
                cid = str(m.get("conditionId") or "")
                nr = bool(m.get("negRisk"))

                if smt == "basketball_game_overtime" or ("overtime" in q_full.lower() and [o.lower() for o in outs] == ["yes", "no"]):
                    if re.search(r"\b(?:double|triple|2\+|3\+|first\s+half|1h|2h)\b", q_full, re.IGNORECASE):
                        continue
                    ot_yes_leg = {
                        "market_id": mid, "condition_id": cid,
                        "token_id": toks[0], "opp_token_id": toks[1],
                        "side": "YES", "label": "YES[Overtime]",
                        "fee_rate": fr, "fee_exponent": fe, "neg_risk": nr,
                        "end_ts": settle_ts, "strike": 0.5,
                    }
                    continue

                if smt in ("basketball_team_to_score_first", "basketball_game_race_to_points"):
                    if re.search(
                        r"\b(?:1q|2q|3q|4q|q1|q2|q3|q4|quarter|half|1h|2h)\b",
                        f"{q_full} {q_txt}",
                        re.IGNORECASE,
                    ):
                        continue
                    c0, c1 = _canon_sport_team(sport, outs[0]), _canon_sport_team(sport, outs[1])
                    if {c0, c1} == {away_t, home_t}:
                        tgt = 1
                        knd = "FIRST_SCORE"
                        if smt == "basketball_game_race_to_points":
                            m_rc = _RACE_PTS_RE.search(q_full)
                            if not m_rc:
                                continue
                            tgt = int(m_rc.group(1))
                            knd = "RACE_TO_X"
                        if c0 == away_t:
                            a_tk, h_tk, a_lb, h_lb = toks[0], toks[1], outs[0], outs[1]
                        else:
                            a_tk, h_tk, a_lb, h_lb = toks[1], toks[0], outs[1], outs[0]
                        fp_mkts.append(FirstPassageMarketSpec(
                            event_id=ev_id, market_id=mid, condition_id=cid,
                            kind=knd, target_pts=tgt,
                            away_token=a_tk, home_token=h_tk, away_label=a_lb, home_label=h_lb,
                            fee_rate=fr, fee_exponent=fe, settle_est_ts=tip_ts + 0.85 * 3600.0, neg_risk=nr,
                        ))
                    continue

                if smt not in _AFFINE_SMT_MAP:
                    continue
                p_scope, kind = _AFFINE_SMT_MAP[smt]
                if p_scope == "FG" and re.search(
                    r"\b(?:first[\s_-]+half|second[\s_-]+half|1st[\s_-]+half|2nd[\s_-]+half|halftime|half-time|1h|2h|1q|2q|3q|4q|q1|q2|q3|q4|(?:first|second|third|fourth|1st|2nd|3rd|4th)[\s_-]+quarter)\b",
                    f"{q_full} {q_txt}",
                    re.IGNORECASE,
                ):
                    continue
                p_off = {"Q1": 0.75, "Q2": 1.35, "1H": 1.35, "Q3": 2.15}.get(p_scope, 3.25 if sport == "NBA" else 3.75) * 3600.0
                m_settle = tip_ts + p_off

                if kind == "ML":
                    c0, c1 = _canon_sport_team(sport, outs[0]), _canon_sport_team(sport, outs[1])
                    if {c0, c1} == {away_t, home_t}:
                        mkts_parsed.append(NbaSubperiodMarketSpec(
                            ev_id, mid, cid, p_scope, "ML", 0.0, c0,
                            toks[0], toks[1], outs[0], outs[1], fr, m_settle,
                            q_txt or f"{p_scope} ML", nr, fe,
                        ))
                elif kind == "SPREAD":
                    raw_ln = m.get("line")
                    if raw_ln is None:
                        continue
                    try:
                        ln = abs(float(raw_ln))
                    except (TypeError, ValueError):
                        continue
                    if not _is_half_hook(ln):
                        continue
                    c0, c1 = _canon_sport_team(sport, outs[0]), _canon_sport_team(sport, outs[1])
                    if {c0, c1} != {away_t, home_t}:
                        continue
                    m_fav = _SPREAD_FAV_RE.search(q_full)
                    fav_team: Optional[str] = None
                    if m_fav:
                        cand_f = _canon_sport_team(sport, m_fav.group(1))
                        sgn = float(m_fav.group(2))
                        if cand_f in (away_t, home_t):
                            fav_team = cand_f if sgn < 0 else (home_t if cand_f == away_t else away_t)
                    if fav_team is None:
                        continue
                    if c0 == fav_team:
                        f_tok, d_tok, f_out, d_out = toks[0], toks[1], outs[0], outs[1]
                    else:
                        f_tok, d_tok, f_out, d_out = toks[1], toks[0], outs[1], outs[0]
                    mkts_parsed.append(NbaSubperiodMarketSpec(
                        ev_id, mid, cid, p_scope, "SPREAD", ln, fav_team,
                        f_tok, d_tok, f_out, d_out, fr, m_settle,
                        f"{p_scope} {f_out}(-{ln})/{d_out}(+{ln})", nr, fe,
                    ))
                elif kind in ("TOTAL", "TEAM_TOTAL"):
                    raw_ln = m.get("line")
                    if raw_ln is None:
                        continue
                    try:
                        ln = float(raw_ln)
                    except (TypeError, ValueError):
                        continue
                    if ln <= 0.0 or not _is_half_hook(ln):
                        continue
                    if not (outs[0].lower().startswith("over") and outs[1].lower().startswith("under")):
                        continue
                    desc_mkt_l = str(m.get("description") or "").lower()
                    if p_scope in ("FG", "2H") and ("overtime is not included" in desc_mkt_l or "excludes overtime" in desc_mkt_l):
                        continue
                    tm_side: Optional[str] = None
                    if kind == "TEAM_TOTAL":
                        q_head = q_full.split("O/U")[0]
                        ca = away_t in _canon_sport_team(sport, q_head) or _norm_team(parts[0]) in _norm_team(q_head)
                        ch = home_t in _canon_sport_team(sport, q_head) or _norm_team(parts[1]) in _norm_team(q_head)
                        if ca == ch:
                            continue
                        tm_side = away_t if ca else home_t
                    mkts_parsed.append(NbaSubperiodMarketSpec(
                        ev_id, mid, cid, p_scope, kind, ln, tm_side,
                        toks[0], toks[1], "Over", "Under", fr, m_settle,
                        q_txt or f"{p_scope} O/U {ln}", nr, fe,
                    ))

        if mkts_parsed or fp_mkts:
            bundles.append(AffineGameBundle(
                sport=sport, event_id=ev_id, slug=base_slug, title=title,
                tipoff_ts=tip_ts, settle_est_ts=settle_ts, away_team=away_t, home_team=home_t,
                markets=mkts_parsed, overtime_yes_leg=ot_yes_leg, first_passage_markets=fp_mkts,
            ))
    return bundles


def _leg_dict_from_subspec(sm: NbaSubperiodMarketSpec, is_tok0: bool, label_override: Optional[str] = None) -> Dict[str, Any]:
    return {
        "token_id": sm.tok_0 if is_tok0 else sm.tok_1,
        "opp_token_id": sm.tok_1 if is_tok0 else sm.tok_0,
        "condition_id": sm.condition_id,
        "market_id": sm.market_id,
        "side": sm.out_0.upper() if is_tok0 else sm.out_1.upper(),
        "label": label_override or f"{sm.display_title}:{sm.out_0 if is_tok0 else sm.out_1}",
        "fee_rate": sm.fee_rate,
        "fee_exponent": sm.fee_exponent,
        "neg_risk": bool(sm.neg_risk),
        "strike": float(sm.line or 0.0),
        "end_ts": sm.settle_est_ts,
    }


def _spread_signed_legs(sm: NbaSubperiodMarketSpec, away_team: str) -> List[Tuple[str, float, Dict[str, Any]]]:
    """
    Normalizes both tokens of a `.5`-hook spread market onto `M = Away - Home` margin:
      - `("GT", theta)` wins iff `Away - Home > theta`
      - `("LT", theta)` wins iff `Away - Home < theta`
    """
    ln = float(sm.line or 0.0)
    if ln <= 0.0:
        return []
    if sm.team_side == away_team:
        # tok_0 = Away(-ln) => M > +ln; tok_1 = Home(+ln) => M < +ln
        return [
            ("GT", +ln, _leg_dict_from_subspec(sm, True, f"{sm.period_scope} {sm.out_0}(-{ln})")),
            ("LT", +ln, _leg_dict_from_subspec(sm, False, f"{sm.period_scope} {sm.out_1}(+{ln})")),
        ]
    # tok_0 = Home(-ln) => H - A > ln <=> M < -ln; tok_1 = Away(+ln) => A - H > -ln <=> M > -ln
    return [
        ("LT", -ln, _leg_dict_from_subspec(sm, True, f"{sm.period_scope} {sm.out_0}(-{ln})")),
        ("GT", -ln, _leg_dict_from_subspec(sm, False, f"{sm.period_scope} {sm.out_1}(+{ln})")),
    ]


def evaluate_aff1_frozen_subperiod_opportunities(
    bundle: AffineGameBundle,
    live_summary: Dict[str, Any],
    best_asks: Dict[str, float],
    freeze_tracker: SubperiodFreezeTracker,
    now_ts: float,
    espn_game_id: str = "",
    freeze_confirm_sec: float = 45.0,
    max_2leg_cost_net: float = 0.992,
    max_3leg_cost_net: float = 0.990,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Evaluates `AFF1` frozen-subperiod 2-leg/3-leg collapse boxes AND Q1 `First to Score` / `Race to X` locks.
    `live_summary` accepts either `parse_espn_nba_extended_summary` dicts or `LiveMultiSportGame`-derived dicts:
      `{state, completed, is_halftime, period, clock_sec, away_score, home_score, linescores: {away: {1:..}, home: {1:..}}}`.
    """
    two_leg_boxes: List[Dict[str, Any]] = []
    three_leg_boxes: List[Dict[str, Any]] = []
    single_leg_locks: List[Dict[str, Any]] = []

    state = str(live_summary.get("state") or "pre").lower()
    if state not in ("in", "post"):
        return {"two_leg_boxes": two_leg_boxes, "three_leg_boxes": three_leg_boxes, "single_leg_locks": single_leg_locks}

    is_final = bool(live_summary.get("completed") and state == "post")
    is_ht = bool(live_summary.get("is_halftime"))
    period = int(live_summary.get("period") or 0)
    away_sc = int(live_summary.get("away_score") or 0)
    home_sc = int(live_summary.get("home_score") or 0)
    ls_a = (live_summary.get("linescores") or {}).get("away") or {}
    ls_h = (live_summary.get("linescores") or {}).get("home") or {}
    gid = espn_game_id or bundle.event_id

    def _try_2leg(mode: str, lg_a: Dict[str, Any], lg_b: Dict[str, Any], middle_width: float, desc: str) -> None:
        if lg_a["market_id"] == lg_b["market_id"]:
            return
        pa = best_asks.get(lg_a["token_id"])
        pb = best_asks.get(lg_b["token_id"])
        if pa is None or pb is None or not (0.005 <= pa <= 0.99 and 0.005 <= pb <= 0.99):
            return
        c_net = round(
            _net_unit_ask(float(pa), lg_a["fee_rate"], lg_a["fee_exponent"])
            + _net_unit_ask(float(pb), lg_b["fee_rate"], lg_b["fee_exponent"]),
            4,
        )
        if c_net <= max_2leg_cost_net:
            two_leg_boxes.append({
                "mode": mode,
                "sport": bundle.sport,
                "event_id": bundle.event_id,
                "slug": bundle.slug,
                "title": bundle.title,
                "box_cost_gross": round(float(pa) + float(pb), 4),
                "box_cost_net": c_net,
                "middle_width": round(float(middle_width), 1),
                "close_ts": max(float(lg_a["end_ts"]), float(lg_b["end_ts"])),
                "leg_a": lg_a,
                "leg_b": lg_b,
                "label": f"{bundle.title}: {desc}",
            })

    # ------------------------------------------------------------------
    # 1A. Post-Q1 Freeze: `1H` vs `Q2` Totals & Spreads (NBA, NFL, CFB)
    # ------------------------------------------------------------------
    q1_ended = (1 in ls_a and 1 in ls_h) and (is_final or is_ht or period >= 2)
    q1_pair = freeze_tracker.confirm_frozen_pair(
        bundle.sport, gid, "Q1", int(ls_a.get(1, 0)), int(ls_h.get(1, 0)),
        period_ended=q1_ended, now_ts=now_ts, freeze_confirm_sec=freeze_confirm_sec,
        instant_settled=(is_final or is_ht or period >= 3),
    )
    if q1_pair is not None and not is_ht and period <= 2 and not is_final:
        a_q1, h_q1 = q1_pair
        s_q1 = float(a_q1 + h_q1)
        m_q1 = float(a_q1 - h_q1)

        t_1h = [m for m in bundle.markets if m.period_scope == "1H" and m.kind == "TOTAL" and m.line is not None]
        t_q2 = [m for m in bundle.markets if m.period_scope == "Q2" and m.kind == "TOTAL" and m.line is not None]
        for m1 in t_1h:
            k_1h = float(m1.line)  # type: ignore[arg-type]
            eff_rem = k_1h - s_q1
            for m2 in t_q2:
                k_q2 = float(m2.line)  # type: ignore[arg-type]
                if eff_rem <= k_q2 + 1e-9:
                    _try_2leg(
                        "AFF1_POST_Q1_1H_VS_Q2_TOTAL",
                        _leg_dict_from_subspec(m1, True, f"1H O{k_1h:g}"),
                        _leg_dict_from_subspec(m2, False, f"Q2 U{k_q2:g}"),
                        k_q2 - eff_rem,
                        f"1H O{k_1h:g} + Q2 U{k_q2:g} (Q1={int(s_q1)} frozen)",
                    )
                if k_q2 <= eff_rem + 1e-9:
                    _try_2leg(
                        "AFF1_POST_Q1_1H_VS_Q2_TOTAL",
                        _leg_dict_from_subspec(m1, False, f"1H U{k_1h:g}"),
                        _leg_dict_from_subspec(m2, True, f"Q2 O{k_q2:g}"),
                        eff_rem - k_q2,
                        f"1H U{k_1h:g} + Q2 O{k_q2:g} (Q1={int(s_q1)} frozen)",
                    )

        sp_1h = [x for m in bundle.markets if m.period_scope == "1H" and m.kind == "SPREAD" for x in _spread_signed_legs(m, bundle.away_team)]
        sp_q2 = [x for m in bundle.markets if m.period_scope == "Q2" and m.kind == "SPREAD" for x in _spread_signed_legs(m, bundle.away_team)]
        for op1, th1, lg1 in sp_1h:
            rem_th = th1 - m_q1
            for op2, th2, lg2 in sp_q2:
                if op1 == "GT" and op2 == "LT" and rem_th <= th2 + 1e-9:
                    _try_2leg(
                        "AFF1_POST_Q1_1H_VS_Q2_SPREAD", lg1, lg2, th2 - rem_th,
                        f"{lg1['label']} + {lg2['label']} (mQ1={m_q1:+.0f})",
                    )
                elif op1 == "LT" and op2 == "GT" and th2 <= rem_th + 1e-9:
                    _try_2leg(
                        "AFF1_POST_Q1_1H_VS_Q2_SPREAD", lg1, lg2, rem_th - th2,
                        f"{lg1['label']} + {lg2['label']} (mQ1={m_q1:+.0f})",
                    )

    # ------------------------------------------------------------------
    # 1B. Halftime / 2H Freeze: NBA `FG Team Total` vs `2H Team Total`
    #     (Verified: BOTH NBA FG Team Total & 2H Team Total include OT!)
    # ------------------------------------------------------------------
    if bundle.sport == "NBA":
        h1_ended = (1 in ls_a and 2 in ls_a and 1 in ls_h and 2 in ls_h) and (is_final or is_ht or period >= 3)
        h1_pair = freeze_tracker.confirm_frozen_pair(
            bundle.sport, gid, "1H",
            int(ls_a.get(1, 0)) + int(ls_a.get(2, 0)),
            int(ls_h.get(1, 0)) + int(ls_h.get(2, 0)),
            period_ended=h1_ended, now_ts=now_ts, freeze_confirm_sec=freeze_confirm_sec,
            instant_settled=(is_final or period >= 4),
        )
        if h1_pair is not None and not is_final:
            t1h_by_team = {bundle.away_team: float(h1_pair[0]), bundle.home_team: float(h1_pair[1])}
            for tm, pts_1h in t1h_by_team.items():
                fg_tts = [m for m in bundle.markets if m.period_scope == "FG" and m.kind == "TEAM_TOTAL" and m.team_side == tm and m.line is not None]
                h2_tts = [m for m in bundle.markets if m.period_scope == "2H" and m.kind == "TEAM_TOTAL" and m.team_side == tm and m.line is not None]
                for m_fg in fg_tts:
                    k_fg = float(m_fg.line)  # type: ignore[arg-type]
                    rem_k = k_fg - pts_1h
                    for m_2h in h2_tts:
                        k_2h = float(m_2h.line)  # type: ignore[arg-type]
                        if rem_k <= k_2h + 1e-9:
                            _try_2leg(
                                "AFF1_HT_TEAM_TOTAL_FG_VS_2H",
                                _leg_dict_from_subspec(m_fg, True, f"FG {tm.title()} O{k_fg:g}"),
                                _leg_dict_from_subspec(m_2h, False, f"2H {tm.title()} U{k_2h:g}"),
                                k_2h - rem_k,
                                f"{tm.title()} FG O{k_fg:g} + 2H U{k_2h:g} (1H={int(pts_1h)})",
                            )
                        if k_2h <= rem_k + 1e-9:
                            _try_2leg(
                                "AFF1_HT_TEAM_TOTAL_FG_VS_2H",
                                _leg_dict_from_subspec(m_fg, False, f"FG {tm.title()} U{k_fg:g}"),
                                _leg_dict_from_subspec(m_2h, True, f"2H {tm.title()} O{k_2h:g}"),
                                rem_k - k_2h,
                                f"{tm.title()} FG U{k_fg:g} + 2H O{k_2h:g} (1H={int(pts_1h)})",
                            )

    # ------------------------------------------------------------------
    # 1C. Post-Q3 Freeze: `FG Total` vs `4Q Total` (+ `YES[Overtime]`)
    # ------------------------------------------------------------------
    if bundle.sport == "NBA":
        q3_ended = all(q in ls_a and q in ls_h for q in (1, 2, 3)) and (is_final or period >= 4)
        q3_pair = freeze_tracker.confirm_frozen_pair(
            bundle.sport, gid, "Q1_Q3",
            int(ls_a.get(1, 0)) + int(ls_a.get(2, 0)) + int(ls_a.get(3, 0)),
            int(ls_h.get(1, 0)) + int(ls_h.get(2, 0)) + int(ls_h.get(3, 0)),
            period_ended=q3_ended, now_ts=now_ts, freeze_confirm_sec=freeze_confirm_sec,
            instant_settled=is_final,
        )
        if q3_pair is not None and not is_final and period == 4:
            s_123 = float(q3_pair[0] + q3_pair[1])
            fg_tots = [m for m in bundle.markets if m.period_scope == "FG" and m.kind == "TOTAL" and m.line is not None]
            q4_tots = [m for m in bundle.markets if m.period_scope == "Q4" and m.kind == "TOTAL" and m.line is not None]
            ot_leg = bundle.overtime_yes_leg
            px_ot = best_asks.get(ot_leg["token_id"]) if ot_leg is not None else None
            c_ot = _net_unit_ask(float(px_ot), ot_leg["fee_rate"], ot_leg["fee_exponent"]) if (ot_leg and px_ot is not None) else None

            for m_fg in fg_tots:
                k_fg = float(m_fg.line)  # type: ignore[arg-type]
                rem_fg = k_fg - s_123
                for m_q4 in q4_tots:
                    k_q4 = float(m_q4.line)  # type: ignore[arg-type]
                    # 2-leg unconditional (`S_OT >= 0`): OVER(FG) + UNDER(4Q)
                    if rem_fg <= k_q4 + 1e-9:
                        _try_2leg(
                            "AFF1_POST_Q3_FG_OVER_4Q_UNDER",
                            _leg_dict_from_subspec(m_fg, True, f"FG O{k_fg:g}"),
                            _leg_dict_from_subspec(m_q4, False, f"4Q U{k_q4:g}"),
                            k_q4 - rem_fg,
                            f"FG O{k_fg:g} + 4Q U{k_q4:g} (Q1..3={int(s_123)})",
                        )
                    # 3-leg OT-immunized: UNDER(FG) + OVER(4Q) + YES(Overtime)
                    if k_q4 <= rem_fg + 1e-9 and ot_leg is not None and px_ot is not None and c_ot is not None:
                        lg_u_fg = _leg_dict_from_subspec(m_fg, False, f"FG U{k_fg:g}")
                        lg_o_q4 = _leg_dict_from_subspec(m_q4, True, f"4Q O{k_q4:g}")
                        pu = best_asks.get(lg_u_fg["token_id"])
                        po = best_asks.get(lg_o_q4["token_id"])
                        if (
                            pu is not None
                            and po is not None
                            and 0.005 <= float(pu) <= 0.99
                            and 0.005 <= float(po) <= 0.99
                            and 0.005 <= float(px_ot) <= 0.99
                        ):
                            c3 = round(
                                _net_unit_ask(float(pu), lg_u_fg["fee_rate"], lg_u_fg["fee_exponent"])
                                + _net_unit_ask(float(po), lg_o_q4["fee_rate"], lg_o_q4["fee_exponent"])
                                + c_ot,
                                4,
                            )
                            if c3 <= max_3leg_cost_net:
                                three_leg_boxes.append({
                                    "mode": "AFF1_POST_Q3_OT_IMMUNIZED_3LEG",
                                    "sport": bundle.sport,
                                    "event_id": bundle.event_id,
                                    "slug": bundle.slug,
                                    "title": bundle.title,
                                    "n_legs": 3,
                                    "box_cost_gross": round(float(pu) + float(po) + float(px_ot), 4),
                                    "box_cost_net": c3,
                                    "middle_width": round(rem_fg - k_q4, 1),
                                    "close_ts": max(lg_u_fg["end_ts"], lg_o_q4["end_ts"], ot_leg["end_ts"]),
                                    "legs": [lg_u_fg, lg_o_q4, ot_leg],
                                    "label": f"{bundle.title}: FG U{k_fg:g} + 4Q O{k_q4:g} + YES[OT] (Q1..3={int(s_123)})",
                                })

    # ------------------------------------------------------------------
    # 1D. Q1 `First to Score` & `Race to 10/20/30 Points` Live Locks
    # ------------------------------------------------------------------
    for fp in bundle.first_passage_markets:
        buf = 2 if fp.kind == "FIRST_SCORE" else 3
        win_side = freeze_tracker.observe_and_confirm_race_winner(
            bundle.sport, gid, fp.target_pts, away_sc, home_sc,
            now_ts=now_ts, buffer_pts=buf, confirm_sec=freeze_confirm_sec, is_final=is_final,
        )
        if win_side in ("AWAY", "HOME"):
            is_away = win_side == "AWAY"
            single_leg_locks.append({
                "mode": f"AFF1_{fp.kind}_LOCK",
                "sport": bundle.sport,
                "event_id": bundle.event_id,
                "market_id": fp.market_id,
                "condition_id": fp.condition_id,
                "token_id": fp.away_token if is_away else fp.home_token,
                "opp_token_id": fp.home_token if is_away else fp.away_token,
                "side_label": fp.away_label if is_away else fp.home_label,
                "display_label": (
                    f"{bundle.title} {'First Score' if fp.kind == 'FIRST_SCORE' else f'Race to {fp.target_pts}'}: "
                    f"{fp.away_label if is_away else fp.home_label} [{away_sc}-{home_sc}]"
                ),
                "fee_rate": fp.fee_rate,
                "fee_exponent": fp.fee_exponent,
                "neg_risk": fp.neg_risk,
                "p_lock": 0.998,
                "close_ts": fp.settle_est_ts,
            })

    # ------------------------------------------------------------------
    # 1E. Settled Subperiod & Post-Final `.5`-Hook `TOTAL`/`TEAM_TOTAL`/`SPREAD` Locks (`p_lock = 1.0`)
    # ------------------------------------------------------------------
    seen_settled_mids = {str(x["market_id"]) for x in single_leg_locks}

    def _is_narrow_halftime_scorer_review_risk(scope: str, abs_diff: float) -> bool:
        """
        During NBA/Basketball halftime intermission (`is_halftime=True` before Q3 tipoff), Secaucus
        Official Scorer reviews buzzer-beaters & 2pt/3pt foot-on-line calls up to 8 minutes (`480s`) into
        halftime. Any narrow `< 3.5pt` (`1`-possession) `Q2`/`1H` margin or total must wait `>= 480s`!
        """
        if not (is_ht and not is_final and period < 3 and scope in ("Q2", "1H") and abs_diff < 3.49):
            return False
        sc_key = "Q2_ONLY" if scope == "Q2" else "1H_LOCK"
        rec = freeze_tracker._frozen_since.get((bundle.sport.upper(), str(gid), sc_key))
        if rec is None:
            return True
        return (float(now_ts) - float(rec[1])) < 480.0

    def _emit_settled_scope_locks(scope: str, a_pts: int, h_pts: int) -> None:
        tot_pts = float(a_pts + h_pts)
        margin = float(a_pts - h_pts)
        mode_s = "AFF1_FINAL_SUBPERIOD_LOCK" if is_final else f"AFF1_{scope}_SETTLED_LOCK"
        for sm in bundle.markets:
            if sm.period_scope != scope or sm.line is None or sm.market_id in seen_settled_mids:
                continue
            ln = float(sm.line)
            win_tok: Optional[str] = None
            opp_tok: Optional[str] = None
            side_lbl: Optional[str] = None
            stat_lbl = ""
            if sm.kind == "TOTAL" and abs(tot_pts - ln) >= 0.49:
                if _is_narrow_halftime_scorer_review_risk(scope, abs(tot_pts - ln)):
                    continue
                win_over = tot_pts > ln
                win_tok = sm.tok_0 if win_over else sm.tok_1
                opp_tok = sm.tok_1 if win_over else sm.tok_0
                side_lbl = sm.out_0 if win_over else sm.out_1
                stat_lbl = f"{scope} Total={int(tot_pts)} vs {ln:g}"
            elif sm.kind == "TEAM_TOTAL" and sm.team_side in (bundle.away_team, bundle.home_team):
                tm_pts = float(a_pts if sm.team_side == bundle.away_team else h_pts)
                if abs(tm_pts - ln) >= 0.49:
                    if _is_narrow_halftime_scorer_review_risk(scope, abs(tm_pts - ln)):
                        continue
                    win_over = tm_pts > ln
                    win_tok = sm.tok_0 if win_over else sm.tok_1
                    opp_tok = sm.tok_1 if win_over else sm.tok_0
                    side_lbl = sm.out_0 if win_over else sm.out_1
                    stat_lbl = f"{scope} {sm.team_side.title()}={int(tm_pts)} vs {ln:g}"
            elif sm.kind == "SPREAD":
                sp_legs = _spread_signed_legs(sm, bundle.away_team)
                if len(sp_legs) == 2 and abs(margin - float(sp_legs[0][1])) >= 0.49:
                    if _is_narrow_halftime_scorer_review_risk(scope, abs(margin - float(sp_legs[0][1]))):
                        continue
                    for op_s, th_s, lg_s in sp_legs:
                        if (op_s == "GT" and margin > th_s) or (op_s == "LT" and margin < th_s):
                            win_tok = str(lg_s["token_id"])
                            opp_tok = str(lg_s["opp_token_id"])
                            side_lbl = str(lg_s["label"])
                            stat_lbl = f"{scope} Margin={a_pts}-{h_pts} ({margin:+.0f} vs {th_s:+.1f})"
                            break
            if win_tok and opp_tok and side_lbl:
                seen_settled_mids.add(sm.market_id)
                single_leg_locks.append({
                    "mode": mode_s,
                    "sport": bundle.sport,
                    "event_id": bundle.event_id,
                    "market_id": sm.market_id,
                    "condition_id": sm.condition_id,
                    "token_id": win_tok,
                    "opp_token_id": opp_tok,
                    "side_label": side_lbl,
                    "display_label": f"{bundle.title} {sm.display_title} -> {side_lbl} [{stat_lbl}]",
                    "fee_rate": sm.fee_rate,
                    "fee_exponent": sm.fee_exponent,
                    "neg_risk": bool(sm.neg_risk),
                    "p_lock": 1.0,
                    "close_ts": sm.settle_est_ts,
                })

    if q1_pair is not None:
        _emit_settled_scope_locks("Q1", int(q1_pair[0]), int(q1_pair[1]))
    q2_ended_lk = (2 in ls_a and 2 in ls_h) and (is_final or is_ht or period >= 3)
    q2_pair_lk = freeze_tracker.confirm_frozen_pair(
        bundle.sport, gid, "Q2_ONLY", int(ls_a.get(2, 0)), int(ls_h.get(2, 0)),
        period_ended=q2_ended_lk, now_ts=now_ts, freeze_confirm_sec=freeze_confirm_sec,
        instant_settled=(is_final or period >= 4),
    )
    if q2_pair_lk is not None:
        _emit_settled_scope_locks("Q2", int(q2_pair_lk[0]), int(q2_pair_lk[1]))
    h1_ended_all = (1 in ls_a and 2 in ls_a and 1 in ls_h and 2 in ls_h) and (is_final or is_ht or period >= 3)
    h1_pair_all = freeze_tracker.confirm_frozen_pair(
        bundle.sport, gid, "1H_LOCK",
        int(ls_a.get(1, 0)) + int(ls_a.get(2, 0)),
        int(ls_h.get(1, 0)) + int(ls_h.get(2, 0)),
        period_ended=h1_ended_all, now_ts=now_ts, freeze_confirm_sec=freeze_confirm_sec,
        instant_settled=(is_final or period >= 4),
    )
    if h1_pair_all is not None:
        _emit_settled_scope_locks("1H", int(h1_pair_all[0]), int(h1_pair_all[1]))
    q3_ended_lk = (3 in ls_a and 3 in ls_h) and (is_final or period >= 4)
    q3_pair_lk = freeze_tracker.confirm_frozen_pair(
        bundle.sport, gid, "Q3_ONLY", int(ls_a.get(3, 0)), int(ls_h.get(3, 0)),
        period_ended=q3_ended_lk, now_ts=now_ts, freeze_confirm_sec=freeze_confirm_sec,
        instant_settled=is_final,
    )
    if q3_pair_lk is not None:
        _emit_settled_scope_locks("Q3", int(q3_pair_lk[0]), int(q3_pair_lk[1]))
    if is_final:
        fin_pair_lk = freeze_tracker.confirm_frozen_pair(
            bundle.sport, gid, "FINAL_FG", away_sc, home_sc,
            period_ended=True, now_ts=now_ts, freeze_confirm_sec=freeze_confirm_sec,
            instant_settled=False,
        )
        if fin_pair_lk is not None:
            _emit_settled_scope_locks("FG", int(fin_pair_lk[0]), int(fin_pair_lk[1]))

    two_leg_boxes.sort(key=lambda x: float(x["box_cost_net"]))
    three_leg_boxes.sort(key=lambda x: float(x["box_cost_net"]))
    return {
        "two_leg_boxes": two_leg_boxes,
        "three_leg_boxes": three_leg_boxes,
        "single_leg_locks": single_leg_locks,
    }


# ==============================================================================
# 2. SLEEVE #2: SOC2_EXACT_SCORE_2D_LATTICE (`83`-State Exact Score + Canceled)
# ==============================================================================
# Exhaustive 83-state lattice:
#   States 0..80:  Played regulation score `(h, a)` for `h in 0..8, a in 0..8` (`idx = 9 * h + a`).
#                  Covers every `0-0..5-5` Exact-Score bracket PLUS `45` distinct `Any Other Score`
#                  boundary combinations (`6-0, 0-6, 6-1, 1-6, 6-5, 5-6, 6-6, ..., 8-8`) so `BTTS`,
#                  `Home/Draw/Away`, `Totals <= 7.5`, and `Spreads <= 5.5` NEVER over-claim!
#   State 81:      `Canceled_DrawRule` (`Exact Score 0-0 = 1.0`, `non-0-0 = 0.0`, `-more-markets = 0.50`,
#                  `3-Way Draw = 1.0, Home/Away = 0.0`).
#   State 82:      `Canceled_SplitRule` (`Exact Score 0-0 = 1.0`, `non-0-0 = 0.0`, `-more-markets = 0.50`,
#                  `3-Way Home/Draw/Away YES = 0.0, NO = 0.50` conservative lower bound!).
SOC2_GRID_MAX = 8
SOC2_PLAYED_STATES: List[Tuple[int, int]] = [
    (h, a) for h in range(SOC2_GRID_MAX + 1) for a in range(SOC2_GRID_MAX + 1)
]
SOC2_NUM_STATES = len(SOC2_PLAYED_STATES) + 2  # 83 states

_EXACT_SCORE_ITEM_RE = re.compile(r"(\d+)\s*[-–:]\s*(\d+)")
_SOC_ADV_VETO_RE = re.compile(
    r"(\badvance\b|\bqualify\b|\blift the trophy\b|\bincluding extra time\b|\bpenalties\b)",
    re.IGNORECASE,
)
_SOC_SUBPERIOD_OR_PROP_VETO_RE = re.compile(
    r"(\bfirst[\s_-]+half\b|\bsecond[\s_-]+half\b|\b1st[\s_-]+half\b|\b2nd[\s_-]+half\b"
    r"|\bhalftime\b|\bhalf-time\b|\beach[\s_-]+half\b|\bboth[\s_-]+halves\b"
    r"|\b1h\b|\b2h\b|\bteam[\s_-]+totals?\b|\bcorners?\b|\bcards?\b|\bshots?\b|\boffsides?\b)",
    re.IGNORECASE,
)


@dataclass
class SoccerExactScoreLattice:
    game_key: str
    game_id: str
    title: str
    end_ts: float
    home_team: str
    away_team: str
    exact_event_id: str
    exact_slug: str
    exact_neg_risk_market_id: str
    is_closed_37_slate: bool
    score_brackets: Dict[Tuple[int, int], Dict[str, Any]]  # (h, a) in 0..5 x 0..5 -> bracket dict
    any_other_bracket: Optional[Dict[str, Any]]
    convert_spec: Optional[NegRiskConvertSlateSpec]
    matrix_legs: List[Dict[str, Any]] = field(default_factory=list)


def _extract_soccer_slug_match_key(slug: str) -> Optional[str]:
    s = re.sub(r"-(more-markets|exact-score|halftime-result|second-half-result|first-to-score)$", "", slug.lower().strip())
    if re.search(r"-20\d{2}-\d{2}-\d{2}$", s):
        return s
    return None


def link_and_parse_soc2_exact_score_lattices(
    events: List[Dict[str, Any]],
    now_ts: Optional[float] = None,
) -> Dict[str, SoccerExactScoreLattice]:
    """
    Links Soccer `-exact-score` (`37`-bracket closed `NegRisk`, `aug=False`) with sibling
    `3-Way ML` and `-more-markets` (`Totals`, `Spreads`, `BTTS`) via `gameId` or base match slug.
    """
    by_key: Dict[str, List[Dict[str, Any]]] = {}
    slug_to_gid: Dict[str, str] = {}
    for ev in events or []:
        if not isinstance(ev, dict) or ev.get("closed") or ev.get("archived"):
            continue
        sl = str(ev.get("slug") or "").lower()
        gid = str(ev.get("gameId") or "").strip()
        bkey = _extract_soccer_slug_match_key(sl)
        if gid and bkey:
            slug_to_gid[bkey] = gid

    for ev in events or []:
        if not isinstance(ev, dict) or ev.get("closed") or ev.get("archived"):
            continue
        sl = str(ev.get("slug") or "").lower()
        gid = str(ev.get("gameId") or "").strip()
        bkey = _extract_soccer_slug_match_key(sl)
        key = gid or (slug_to_gid.get(bkey) if bkey else None) or bkey
        if key:
            by_key.setdefault(key, []).append(ev)

    lattices: Dict[str, SoccerExactScoreLattice] = {}
    for gkey, ev_list in by_key.items():
        ev_exact = next((e for e in ev_list if str(e.get("slug") or "").lower().endswith("-exact-score")), None)
        if ev_exact is None:
            continue
        ev_3way = next(
            (
                e for e in ev_list
                if e.get("negRisk") and len(e.get("markets") or []) == 3
                and not str(e.get("slug") or "").lower().endswith(("-halftime-result", "-second-half-result", "-first-to-score", "-exact-score"))
            ),
            None,
        )
        ev_more = next((e for e in ev_list if str(e.get("slug") or "").lower().endswith("-more-markets")), None)

        raw_title = re.sub(r"\s*-\s*Exact Score\s*$", "", str(ev_exact.get("title") or ""), flags=re.I).strip()
        t_parts = re.split(r"\s+vs\.?\s+", raw_title, maxsplit=1, flags=re.IGNORECASE)
        if len(t_parts) != 2:
            continue
        # Standard Polymarket Soccer title: `<Home Club> vs. <Away Club>` (`0-1` = Away 1, `1-0` = Home 1)
        home_raw, away_raw = t_parts[0].strip(), t_parts[1].strip()
        home_n, away_n = _norm_team(home_raw), _norm_team(away_raw)
        if not home_n or not away_n or home_n == away_n:
            continue

        end_ts = _parse_iso_ts(
            (ev_3way or ev_exact).get("startTime") or ev_exact.get("gameStartTime") or ev_exact.get("endDate")
        ) or 0.0
        if end_ts <= 0.0 or (now_ts is not None and end_ts < now_ts - 4.0 * 3600.0):
            continue

        score_brs: Dict[Tuple[int, int], Dict[str, Any]] = {}
        any_other_br: Optional[Dict[str, Any]] = None
        conv_brackets: List[Dict[str, Any]] = []
        matrix_legs: List[Dict[str, Any]] = []
        all_37_open = True

        ex_mkts = ev_exact.get("markets") or []
        for idx_m, m in enumerate(ex_mkts):
            if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
                all_37_open = False
                continue
            q_txt = str(m.get("question") or "")
            desc = str(m.get("description") or "")
            grp = str(m.get("groupItemTitle") or "").strip()
            smt_ex = str(m.get("sportsMarketType") or "").strip().lower()
            if _SOC_ADV_VETO_RE.search(f"{q_txt}\n{desc}") or _SOC_SUBPERIOD_OR_PROP_VETO_RE.search(f"{q_txt}\n{grp}\n{smt_ex}"):
                all_37_open = False
                continue
            toks = _parse_clob_tokens(m)
            outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
            if not toks or outs != ["yes", "no"]:
                all_37_open = False
                continue
            fr, fe = _extract_market_fee_rate(m)
            q_id = str(m.get("questionID") or "").strip().lower()
            q_idx = int(q_id[64:], 16) if (len(q_id) == 66 and q_id.startswith("0x")) else idx_m
            mid, cid = str(m.get("id") or ""), str(m.get("conditionId") or "")

            is_other = "other" in grp.lower() or "any other" in q_txt.lower()
            h_sc, a_sc = -1, -1
            if not is_other:
                m_sc = _EXACT_SCORE_ITEM_RE.search(grp or q_txt)
                if not m_sc:
                    all_37_open = False
                    continue
                h_sc, a_sc = int(m_sc.group(1)), int(m_sc.group(2))
                # Verify orientation if club names appear in reversed order around scoreline (e.g. "Away 2 - 1 Home")
                norm_lbl = _norm_team(grp or q_txt)
                if away_n in norm_lbl and home_n in norm_lbl:
                    if norm_lbl.find(away_n) < norm_lbl.find(home_n):
                        h_sc, a_sc = a_sc, h_sc
                elif away_n in norm_lbl and home_n not in norm_lbl and h_sc < a_sc:
                    # Named winner in groupItemTitle ("Chelsea 2-1") must hold the higher score
                    h_sc, a_sc = a_sc, h_sc
                elif home_n in norm_lbl and away_n not in norm_lbl and a_sc > h_sc:
                    h_sc, a_sc = a_sc, h_sc
                if not (0 <= h_sc <= 5 and 0 <= a_sc <= 5):
                    all_37_open = False
                    continue

            b_rec = {
                "market_id": mid,
                "condition_id": cid,
                "question_index": q_idx,
                "label": "Any Other" if is_other else f"{h_sc}-{a_sc}",
                "home_goals": h_sc,
                "away_goals": a_sc,
                "yes_token": toks[0],
                "no_token": toks[1],
                "fee_rate": fr,
                "fee_exponent": fe,
                "neg_risk": True,
            }
            conv_brackets.append(b_rec)
            if is_other:
                any_other_br = b_rec
                v_yes = [1.0 if max(h, a) >= 6 else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [0.0, 0.0]
            else:
                score_brs[(h_sc, a_sc)] = b_rec
                c_pay = 1.0 if (h_sc == 0 and a_sc == 0) else 0.0
                v_yes = [1.0 if (h == h_sc and a == a_sc) else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [c_pay, c_pay]
            v_no = [1.0 - x for x in v_yes]

            lbl_s = b_rec["label"]
            matrix_legs.append({
                "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1],
                "side": "YES", "label": f"CS_Y[{lbl_s}]", "fee_rate": fr, "fee_exponent": fe,
                "neg_risk": True, "end_ts": end_ts, "payoff_vec": v_yes, "strike": float(max(0, h_sc + a_sc)),
            })
            matrix_legs.append({
                "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0],
                "side": "NO", "label": f"CS_N[{lbl_s}]", "fee_rate": fr, "fee_exponent": fe,
                "neg_risk": True, "end_ts": end_ts, "payoff_vec": v_no, "strike": float(max(0, h_sc + a_sc)),
            })

        if not score_brs:
            continue

        is_closed_37 = (
            bool(ev_exact.get("negRisk"))
            and not bool(ev_exact.get("negRiskAugmented", False))
            and all_37_open
            and len(score_brs) == 36
            and any_other_br is not None
            and len(conv_brackets) == 37
        )
        nr_mkt_id = str(ev_exact.get("negRiskMarketID") or "").strip().lower()
        conv_spec: Optional[NegRiskConvertSlateSpec] = None
        if is_closed_37 and nr_mkt_id.startswith("0x") and len(nr_mkt_id) == 66:
            conv_brackets.sort(key=lambda b: int(b["question_index"]))
            if [int(b["question_index"]) for b in conv_brackets] == list(range(37)):
                conv_spec = NegRiskConvertSlateSpec(
                    event_id=str(ev_exact.get("id") or ""),
                    slug=str(ev_exact.get("slug") or ""),
                    title=raw_title,
                    neg_risk_market_id=nr_mkt_id,
                    neg_risk_augmented=False,
                    total_market_count=37,
                    is_closed_convert_safe=True,
                    end_ts=end_ts,
                    brackets=conv_brackets,
                )

        # Attach 3-Way Regulation ML legs if present
        if ev_3way is not None:
            for m in ev_3way.get("markets") or []:
                if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
                    continue
                q_txt = str(m.get("question") or "")
                desc = str(m.get("description") or "")
                grp = str(m.get("groupItemTitle") or "").strip()
                smt_3w = str(m.get("sportsMarketType") or "").strip().lower()
                if _SOC_ADV_VETO_RE.search(f"{q_txt}\n{desc}\n{grp}") or _SOC_SUBPERIOD_OR_PROP_VETO_RE.search(f"{q_txt}\n{grp}\n{smt_3w}"):
                    continue
                toks = _parse_clob_tokens(m)
                outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
                if not toks or outs != ["yes", "no"]:
                    continue
                fr, fe = _extract_market_fee_rate(m)
                mid, cid = str(m.get("id") or ""), str(m.get("conditionId") or "")
                if "draw" in grp.lower() or "end in a draw" in q_txt.lower():
                    v_y = [1.0 if h == a else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [1.0, 0.0]
                    v_n = [1.0 if h != a else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [0.0, 0.5]
                    tag = "Draw"
                else:
                    m_home = _teams_match_fuzzy(grp, home_raw)
                    m_away = _teams_match_fuzzy(grp, away_raw)
                    if m_home and not m_away:
                        v_y = [1.0 if h > a else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [0.0, 0.0]
                        v_n = [1.0 if h <= a else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [1.0, 0.5]
                        tag = home_raw[:14]
                    elif m_away and not m_home:
                        v_y = [1.0 if a > h else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [0.0, 0.0]
                        v_n = [1.0 if a <= h else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [1.0, 0.5]
                        tag = away_raw[:14]
                    else:
                        continue
                matrix_legs.append({
                    "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1],
                    "side": "YES", "label": f"ML_Y[{tag}]", "fee_rate": fr, "fee_exponent": fe,
                    "neg_risk": True, "end_ts": end_ts, "payoff_vec": v_y, "strike": 0.0,
                })
                matrix_legs.append({
                    "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0],
                    "side": "NO", "label": f"ML_N[{tag}]", "fee_rate": fr, "fee_exponent": fe,
                    "neg_risk": True, "end_ts": end_ts, "payoff_vec": v_n, "strike": 0.0,
                })

        # Attach `-more-markets` (`Totals <= 7.5`, `Spreads <= 5.5`, `BTTS`) — all resolve `50-50` (`0.50`) if Canceled!
        if ev_more is not None:
            for m in ev_more.get("markets") or []:
                if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
                    continue
                toks = _parse_clob_tokens(m)
                outs = [str(o).strip() for o in _parse_json_list(m.get("outcomes"))]
                if not toks or len(outs) != 2:
                    continue
                smt = str(m.get("sportsMarketType") or "").strip().lower()
                q_full = str(m.get("question") or m.get("groupItemTitle") or "")
                grp_more = str(m.get("groupItemTitle") or "").strip()
                desc = str(m.get("description") or "")
                if _SOC_ADV_VETO_RE.search(f"{q_full}\n{desc}") or _SOC_SUBPERIOD_OR_PROP_VETO_RE.search(f"{q_full}\n{grp_more}\n{smt}"):
                    continue
                fr, fe = _extract_market_fee_rate(m)
                mid, cid = str(m.get("id") or ""), str(m.get("conditionId") or "")
                nr = bool(m.get("negRisk"))

                if smt == "totals" and m.get("line") is not None:
                    ln = float(m["line"])
                    if _is_half_hook(ln) and 0.5 <= ln <= 7.5 and outs[0].lower().startswith("over"):
                        v_ov = [1.0 if (h + a) > ln else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [0.5, 0.5]
                        v_un = [1.0 if (h + a) < ln else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [0.5, 0.5]
                        matrix_legs.append({
                            "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1],
                            "side": "OVER", "label": f"O[{ln:g} Goals]", "fee_rate": fr, "fee_exponent": fe,
                            "neg_risk": nr, "end_ts": end_ts, "payoff_vec": v_ov, "strike": ln,
                        })
                        matrix_legs.append({
                            "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0],
                            "side": "UNDER", "label": f"U[{ln:g} Goals]", "fee_rate": fr, "fee_exponent": fe,
                            "neg_risk": nr, "end_ts": end_ts, "payoff_vec": v_un, "strike": ln,
                        })
                elif smt in ("", "both_teams_to_score") and (smt == "both_teams_to_score" or "both teams to score" in q_full.lower()):
                    if [o.lower() for o in outs] == ["yes", "no"]:
                        v_by = [1.0 if (h >= 1 and a >= 1) else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [0.5, 0.5]
                        v_bn = [1.0 if (h == 0 or a == 0) else 0.0 for (h, a) in SOC2_PLAYED_STATES] + [0.5, 0.5]
                        matrix_legs.append({
                            "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1],
                            "side": "YES", "label": "BTTS[Yes]", "fee_rate": fr, "fee_exponent": fe,
                            "neg_risk": nr, "end_ts": end_ts, "payoff_vec": v_by, "strike": 1.0,
                        })
                        matrix_legs.append({
                            "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0],
                            "side": "NO", "label": "BTTS[No]", "fee_rate": fr, "fee_exponent": fe,
                            "neg_risk": nr, "end_ts": end_ts, "payoff_vec": v_bn, "strike": 1.0,
                        })
                elif smt == "spreads" and m.get("line") is not None:
                    ln = abs(float(m["line"]))
                    if _is_half_hook(ln) and 0.5 <= ln <= 5.5:
                        m_fav = _SPREAD_FAV_RE.search(q_full)
                        if m_fav:
                            fav_raw = m_fav.group(1).strip()
                            sgn = float(m_fav.group(2))
                            fav_is_home = _teams_match_fuzzy(fav_raw, home_raw)
                            fav_is_away = _teams_match_fuzzy(fav_raw, away_raw)
                            if fav_is_home != fav_is_away:
                                if sgn > 0:
                                    fav_is_home = not fav_is_home
                                o0_home = _teams_match_fuzzy(outs[0], home_raw)
                                fav_tok, dog_tok = (toks[0], toks[1]) if (o0_home == fav_is_home) else (toks[1], toks[0])
                                v_fav = [
                                    1.0 if ((h - a) > ln if fav_is_home else (a - h) > ln) else 0.0
                                    for (h, a) in SOC2_PLAYED_STATES
                                ] + [0.5, 0.5]
                                v_dog = [1.0 - x if i < len(SOC2_PLAYED_STATES) else 0.5 for i, x in enumerate(v_fav)]
                                f_tag = home_raw[:10] if fav_is_home else away_raw[:10]
                                d_tag = away_raw[:10] if fav_is_home else home_raw[:10]
                                matrix_legs.append({
                                    "market_id": mid, "condition_id": cid, "token_id": fav_tok, "opp_token_id": dog_tok,
                                    "side": "SPREAD", "label": f"{f_tag}(-{ln:g})", "fee_rate": fr, "fee_exponent": fe,
                                    "neg_risk": nr, "end_ts": end_ts, "payoff_vec": v_fav, "strike": -ln,
                                })
                                matrix_legs.append({
                                    "market_id": mid, "condition_id": cid, "token_id": dog_tok, "opp_token_id": fav_tok,
                                    "side": "SPREAD", "label": f"{d_tag}(+{ln:g})", "fee_rate": fr, "fee_exponent": fe,
                                    "neg_risk": nr, "end_ts": end_ts, "payoff_vec": v_dog, "strike": ln,
                                })

        lattices[gkey] = SoccerExactScoreLattice(
            game_key=gkey,
            game_id=str(ev_exact.get("gameId") or (ev_3way or {}).get("gameId") or gkey),
            title=raw_title,
            end_ts=end_ts,
            home_team=home_raw,
            away_team=away_raw,
            exact_event_id=str(ev_exact.get("id") or ""),
            exact_slug=str(ev_exact.get("slug") or ""),
            exact_neg_risk_market_id=nr_mkt_id,
            is_closed_37_slate=is_closed_37,
            score_brackets=score_brs,
            any_other_bracket=any_other_br,
            convert_spec=conv_spec,
            matrix_legs=matrix_legs,
        )
    return lattices


def detect_soc2_lattice_boxes_and_converts(
    lattice: SoccerExactScoreLattice,
    books_by_token: Dict[str, Dict[str, Any]],
    best_asks: Dict[str, float],
    max_2leg_cost_net: float = 0.990,
    max_3leg_cost_net: float = 0.988,
    target_budget_usd: float = 120.0,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Runs both:
      1. `83`-state payoff-matrix super-replication (`YES[0-0] + OVER[0.5 Goals]`, `BTTS` vs Exact Score strips, etc.)
      2. Closed 37-bracket `NR2` `convertPositions` subset arbitrage when `lattice.convert_spec` is verified.
    """
    matrix_boxes = find_state_matrix_dominance_boxes(
        lattice.matrix_legs,
        best_asks,
        max_2leg_cost_net=max_2leg_cost_net,
        max_3leg_cost_net=max_3leg_cost_net,
    )
    for b in matrix_boxes:
        b["mode"] = f"SOC2_{b['n_legs']}LEG_LATTICE_BOX"
        b["title"] = lattice.title
        b["game_key"] = lattice.game_key

    convert_arbs: List[Dict[str, Any]] = []
    if lattice.convert_spec is not None and books_by_token:
        convert_arbs = detect_nr2_convert_no_subset_arbs(
            lattice.convert_spec,
            books_by_token,
            target_budget_usd=target_budget_usd,
        )
    return {"matrix_boxes": matrix_boxes, "convert_arbs": convert_arbs}


def evaluate_soc2_dead_score_no_locks(
    lattice: SoccerExactScoreLattice,
    live_soccer_board: List[LiveMultiSportGame],
    tracker: ScoreConfirmationTracker,
    now_ts: float,
    var_confirm_sec: float = 210.0,
) -> List[Dict[str, Any]]:
    """
    Sweeps `NO[h-a]` on mathematically dead Exact-Score brackets once live ESPN soccer goals
    are confirmed post-VAR (`>= 210s` without reversal, or `completed == True`):
      - Every non-`0-0` bracket `(h, a) != (0, 0)` with `h < g_H` or `a < g_A` pays `$1.00`
        in every played continuation AND `$1.00` if the match is abandoned/canceled (`0-0` rule)!
      - `NO[0-0]` is emitted ONLY when `is_final == True` (90m regulation completed) so mid-match
        abandonment (`0-0` fallback) can NEVER cause a loss!
      - If `g_H >= 6` or `g_A >= 6`, `YES[Any Other Score]` is also locked (`$1.00`) once post-VAR confirmed!
    """
    matched: Optional[LiveMultiSportGame] = None
    swapped = False
    for g in live_soccer_board:
        if g.start_ts > 0 and lattice.end_ts > 0 and abs(g.start_ts - lattice.end_ts) > 10.0 * 3600.0:
            continue
        dir_ok = _teams_match_fuzzy(lattice.home_team, g.home_name) and _teams_match_fuzzy(lattice.away_team, g.away_name)
        swp_ok = _teams_match_fuzzy(lattice.home_team, g.away_name) and _teams_match_fuzzy(lattice.away_team, g.home_name)
        if dir_ok and swp_ok:
            continue  # Ambiguous intra-city derby match: fail closed!
        if dir_ok:
            matched, swapped = g, False
            break
        if swp_ok:
            matched, swapped = g, True
            break
    if matched is None:
        return []

    # 90-minute Regulation Extra-Time / Shootout Guard:
    # In knockout cups, period > 2 is Extra Time / Penalties, whereas Polymarket `-exact-score` resolves
    # strictly on 90m + injury time (periods 1 & 2). Never use 120m total scores when period > 2!
    if matched.period > 2:
        if (
            1 in matched.linescores_home
            and 2 in matched.linescores_home
            and 1 in matched.linescores_away
            and 2 in matched.linescores_away
        ):
            reg_espn_h = int(matched.linescores_home[1]) + int(matched.linescores_home[2])
            reg_espn_a = int(matched.linescores_away[1]) + int(matched.linescores_away[2])
            raw_h = reg_espn_a if swapped else reg_espn_h
            raw_a = reg_espn_h if swapped else reg_espn_a
            is_final = True
        else:
            return []
    else:
        is_final = bool(matched.completed and matched.state == "post")
        raw_h = matched.away_score if swapped else matched.home_score
        raw_a = matched.home_score if swapped else matched.away_score
    g_h = tracker.observe_and_confirmed_floor("SOCCER", matched.game_id, "HOME_G", raw_h, now_ts, var_confirm_sec, is_final=is_final)
    g_a = tracker.observe_and_confirmed_floor("SOCCER", matched.game_id, "AWAY_G", raw_a, now_ts, var_confirm_sec, is_final=is_final)
    if g_h == 0 and g_a == 0 and not is_final:
        return []

    locks: List[Dict[str, Any]] = []
    for (bh, ba), br in lattice.score_brackets.items():
        is_dead = (bh != g_h or ba != g_a) if is_final else (bh < g_h or ba < g_a)
        if not is_dead:
            continue
        # Critical abandonment guard: in-play abandonment resolves `-exact-score` to `0-0`!
        if (bh == 0 and ba == 0) and not is_final:
            continue
        locks.append({
            "mode": "SOC2_FINAL_EXACT_SCORE_NO_LOCK" if is_final else "SOC2_LIVE_DEAD_SCORE_NO_LOCK",
            "game_key": lattice.game_key,
            "market_id": br["market_id"],
            "condition_id": br["condition_id"],
            "token_id": br["no_token"],
            "opp_token_id": br["yes_token"],
            "side_label": f"NO[{bh}-{ba}]",
            "display_label": f"{lattice.title} NO[{bh}-{ba}] [Confirmed {g_h}-{g_a}{' FT' if is_final else ' post-VAR'}]",
            "fee_rate": br["fee_rate"],
            "fee_exponent": br["fee_exponent"],
            "neg_risk": True,
            "p_lock": 0.999,
            "close_ts": lattice.end_ts + 7200.0,
        })

    if (g_h >= 6 or g_a >= 6) and lattice.any_other_bracket is not None and is_final:
        ao = lattice.any_other_bracket
        locks.append({
            "mode": "SOC2_ANY_OTHER_SCORE_YES_LOCK",
            "game_key": lattice.game_key,
            "market_id": ao["market_id"],
            "condition_id": ao["condition_id"],
            "token_id": ao["yes_token"],
            "opp_token_id": ao["no_token"],
            "side_label": "YES[Any Other]",
            "display_label": f"{lattice.title} YES[Any Other Score] [FT {g_h}-{g_a}]",
            "fee_rate": ao["fee_rate"],
            "fee_exponent": ao["fee_exponent"],
            "neg_risk": True,
            "p_lock": 0.999,
            "close_ts": lattice.end_ts + 7200.0,
        })
    return locks


# ==============================================================================
# 3. SLEEVE #3: NFL_PRP1_MILESTONE_AND_MAX_LOCKS
# ==============================================================================
@dataclass
class NflPlayerPropRung:
    event_id: str
    event_slug: str
    game_title: str
    market_id: str
    condition_id: str
    player_name: str
    player_key: str
    stat_type: str        # "anytime_td", "two_plus_td", "longest_reception", "longest_rush", "receptions", etc.
    line: float           # 0.5 for anytime_td, 1.5 for two_plus_td, or .5 hook
    yes_over_token: str
    no_under_token: str
    fee_rate: float
    fee_exponent: float
    kickoff_ts: float
    settle_est_ts: float
    home_team: str
    away_team: str
    dnp_resolves_no: bool = False


@dataclass
class NflPlayerPropSlate:
    event_id: str
    slug: str
    title: str
    kickoff_ts: float
    settle_est_ts: float
    home_team: str
    away_team: str
    anytime_td_by_player: Dict[str, NflPlayerPropRung] = field(default_factory=dict)
    two_plus_td_by_player: Dict[str, NflPlayerPropRung] = field(default_factory=dict)
    ladders_by_player_stat: Dict[Tuple[str, str], List[NflPlayerPropRung]] = field(default_factory=dict)


_NFL_ALLOWED_OU_SMTS = frozenset({
    "receptions",
    "receiving_yards",
    "rushing_yards",
    "passing_yards",
    "passing_completions",
    "passing_attempts",
    "passing_touchdowns",
    "longest_reception",
    "longest_rush",
})

_NFL_TD_PLAYER_RE = re.compile(
    r"^(.+?)\s*:\s*(?:anytime\s+touchdown|2\+\s*touchdowns|to\s+score\s+(?:a|2\+))\b",
    re.IGNORECASE,
)
_NFL_WILL_TD_RE = re.compile(
    r"^will\s+(.+?)\s+score\s+(?:a\s+touchdown|2\+\s*touchdowns|at\s+least\s+2\s+touchdowns)",
    re.IGNORECASE,
)
_NFL_COLON_PROP_RE = re.compile(r"^([^:]+?)\s*:\s*(.+?)(?:\s+O/U|\s+Over/Under|\s+\d)", re.IGNORECASE)


def _extract_nfl_prop_player(m: Dict[str, Any]) -> str:
    for fld in ("groupItemTitle", "question"):
        txt = str(m.get(fld) or "").strip()
        if not txt:
            continue
        for pat in (_NFL_TD_PLAYER_RE, _NFL_WILL_TD_RE, _NFL_COLON_PROP_RE):
            mt = pat.search(txt)
            if mt:
                cand = mt.group(1).strip()
                if len(cand) >= 3 and " vs" not in cand.lower():
                    return cand
        if ":" in txt:
            head = txt.split(":", 1)[0].strip()
            if 3 <= len(head) <= 40 and " vs" not in head.lower() and "spread" not in head.lower():
                return head
    return ""


def parse_nfl_player_props_event(ev: Dict[str, Any], now_ts: Optional[float] = None) -> Optional[NflPlayerPropSlate]:
    """
    Parses `nfl-*-player-props` (and parent `nfl-*` events with player props) across `anytime_touchdowns`,
    `two_plus_touchdowns`, `longest_reception`, `longest_rush`, and `.5`-hook counter/yardage props.
    """
    if ev.get("closed") or ev.get("archived"):
        return None
    slug = str(ev.get("slug") or "").lower()
    if not slug.startswith("nfl-"):
        return None
    raw_title = re.sub(r"\s*-\s*(?:Player Props|More Markets)\s*$", "", str(ev.get("title") or ""), flags=re.I).strip()
    parts = re.split(r"\s+(?:vs\.?|@)\s+", raw_title, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None
    away_t, home_t = _norm_team(parts[0]), _norm_team(parts[1])
    kick_ts = _parse_iso_ts(ev.get("startTime") or ev.get("gameStartTime") or ev.get("endDate")) or 0.0
    if kick_ts <= 0.0 or (now_ts is not None and kick_ts < now_ts - 8.0 * 3600.0):
        return None
    settle_ts = kick_ts + 3.75 * 3600.0
    ev_id = str(ev.get("id") or "")

    anytime_map: Dict[str, NflPlayerPropRung] = {}
    two_plus_map: Dict[str, NflPlayerPropRung] = {}
    ladders: Dict[Tuple[str, str], List[NflPlayerPropRung]] = {}

    for m in ev.get("markets") or []:
        if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
            continue
        smt = str(m.get("sportsMarketType") or "").strip().lower()
        toks = _parse_clob_tokens(m)
        outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
        if not toks or len(outs) != 2:
            continue
        fr, fe = _extract_market_fee_rate(m)
        p_raw = _extract_nfl_prop_player(m)
        pkey = canon_player_name(p_raw)
        if not pkey:
            continue

        if smt in ("anytime_touchdowns", "two_plus_touchdowns") and outs == ["yes", "no"]:
            q_td_blob = f"{m.get('question') or ''} {m.get('groupItemTitle') or ''}"
            # Exclude First/Last/Half/Quarter TD markets (which sometimes carry `anytime_touchdowns` tags on Gamma!)
            if re.search(
                r"\b(?:first|last|1st\s+td|1st\s+touchdown|1h|2h|first\s+half|second\s+half|1q|2q|3q|4q|quarter)\b",
                q_td_blob,
                re.IGNORECASE,
            ):
                continue
            desc_td_l = str(m.get("description") or "").lower()
            # Polymarket NFL player props resolve 50-50 if a player plays 0 snaps UNLESS description explicitly specifies resolving to "No"
            dnp_no_ok = bool(
                "50-50" not in desc_td_l
                and "void" not in desc_td_l
                and re.search(r'not\s+play[^.]*resolve[s]?\s+to\s+"?no"?', desc_td_l)
            )
            is_any = smt == "anytime_touchdowns"
            rg = NflPlayerPropRung(
                event_id=ev_id, event_slug=slug, game_title=raw_title,
                market_id=str(m.get("id") or ""), condition_id=str(m.get("conditionId") or ""),
                player_name=p_raw, player_key=pkey,
                stat_type="anytime_td" if is_any else "two_plus_td",
                line=0.5 if is_any else 1.5,
                yes_over_token=toks[0], no_under_token=toks[1],
                fee_rate=fr, fee_exponent=fe, kickoff_ts=kick_ts, settle_est_ts=settle_ts,
                home_team=home_t, away_team=away_t, dnp_resolves_no=dnp_no_ok,
            )
            if is_any:
                anytime_map[pkey] = rg
            else:
                two_plus_map[pkey] = rg
            continue

        if smt in _NFL_ALLOWED_OU_SMTS and (outs == ["over", "under"] or outs == ["yes", "no"]):
            raw_ln = m.get("line")
            if raw_ln is None:
                continue
            try:
                ln = float(raw_ln)
            except (TypeError, ValueError):
                continue
            if ln < 0.5 or not _is_half_hook(ln):
                continue
            ladders.setdefault((pkey, smt), []).append(
                NflPlayerPropRung(
                    event_id=ev_id, event_slug=slug, game_title=raw_title,
                    market_id=str(m.get("id") or ""), condition_id=str(m.get("conditionId") or ""),
                    player_name=p_raw, player_key=pkey, stat_type=smt, line=ln,
                    yes_over_token=toks[0], no_under_token=toks[1],
                    fee_rate=fr, fee_exponent=fe, kickoff_ts=kick_ts, settle_est_ts=settle_ts,
                    home_team=home_t, away_team=away_t,
                )
            )

    for k in ladders:
        ladders[k].sort(key=lambda r: r.line)
    if not anytime_map and not two_plus_map and not ladders:
        return None
    return NflPlayerPropSlate(
        event_id=ev_id, slug=slug, title=raw_title, kickoff_ts=kick_ts, settle_est_ts=settle_ts,
        home_team=home_t, away_team=away_t, anytime_td_by_player=anytime_map,
        two_plus_td_by_player=two_plus_map, ladders_by_player_stat=ladders,
    )


def detect_nfl_prp1_boxes(
    slate: NflPlayerPropSlate,
    best_asks: Dict[str, float],
    max_box_cost_net: float = 0.992,
) -> List[Dict[str, Any]]:
    """
    Detects fee-exact (`3%`) NFL Player Prop boxes:
      1. `NFL_PRP1_TD_POLISH_MIDDLE`: `YES(Anytime TD) + NO(2+ Touchdowns)` (`$1.00` floor across
         `{Inactive/DNP, 0 TD, >=2 TD, Canceled}`, `$2.00` on `Exact 1 TD`!).
      2. `NFL_PRP1_STAT_CORRIDOR`: Same-player, same-stat `OVER(K1) + UNDER(K2)` (`K1 < K2`, `.5` hooks).
    """
    arbs: List[Dict[str, Any]] = []
    for pkey, r_any in slate.anytime_td_by_player.items():
        r_two = slate.two_plus_td_by_player.get(pkey)
        if r_two is None or r_any.market_id == r_two.market_id or r_any.dnp_resolves_no != r_two.dnp_resolves_no:
            continue
        pa = best_asks.get(r_any.yes_over_token)
        pb = best_asks.get(r_two.no_under_token)
        if pa is None or pb is None or not (0.01 <= pa <= 0.99 and 0.01 <= pb <= 0.99):
            continue
        c_net = round(
            _net_unit_ask(float(pa), r_any.fee_rate, r_any.fee_exponent)
            + _net_unit_ask(float(pb), r_two.fee_rate, r_two.fee_exponent),
            4,
        )
        if c_net <= max_box_cost_net:
            arbs.append({
                "mode": "NFL_PRP1_TD_POLISH_MIDDLE",
                "event_id": slate.event_id,
                "slug": slate.slug,
                "title": slate.title,
                "player_name": r_any.player_name,
                "box_cost_gross": round(float(pa) + float(pb), 4),
                "box_cost_net": c_net,
                "close_ts": slate.settle_est_ts,
                "leg_a": {
                    "token_id": r_any.yes_over_token, "opp_token_id": r_any.no_under_token,
                    "condition_id": r_any.condition_id, "market_id": r_any.market_id,
                    "side": "YES", "label": f"{r_any.player_name} Anytime TD",
                    "fee_rate": r_any.fee_rate, "fee_exponent": r_any.fee_exponent,
                    "neg_risk": False, "strike": 0.5, "end_ts": slate.settle_est_ts,
                },
                "leg_b": {
                    "token_id": r_two.no_under_token, "opp_token_id": r_two.yes_over_token,
                    "condition_id": r_two.condition_id, "market_id": r_two.market_id,
                    "side": "NO", "label": f"{r_two.player_name} NO 2+ TDs",
                    "fee_rate": r_two.fee_rate, "fee_exponent": r_two.fee_exponent,
                    "neg_risk": False, "strike": 1.5, "end_ts": slate.settle_est_ts,
                },
                "label": f"{r_any.player_name}: YES(Anytime TD) + NO(2+ TDs)",
            })

    for (_, stat_t), rungs in slate.ladders_by_player_stat.items():
        for i in range(len(rungs)):
            r_lo = rungs[i]
            pa = best_asks.get(r_lo.yes_over_token)
            if pa is None or not (0.02 <= pa <= 0.98):
                continue
            for j in range(i + 1, len(rungs)):
                r_hi = rungs[j]
                if r_hi.line <= r_lo.line + 0.1 or r_lo.market_id == r_hi.market_id:
                    continue
                pb = best_asks.get(r_hi.no_under_token)
                if pb is None or not (0.02 <= pb <= 0.98):
                    continue
                c_net = round(
                    _net_unit_ask(float(pa), r_lo.fee_rate, r_lo.fee_exponent)
                    + _net_unit_ask(float(pb), r_hi.fee_rate, r_hi.fee_exponent),
                    4,
                )
                if c_net <= max_box_cost_net:
                    arbs.append({
                        "mode": "NFL_PRP1_STAT_CORRIDOR",
                        "event_id": slate.event_id,
                        "slug": slate.slug,
                        "title": slate.title,
                        "player_name": r_lo.player_name,
                        "stat_type": stat_t,
                        "box_cost_gross": round(float(pa) + float(pb), 4),
                        "box_cost_net": c_net,
                        "close_ts": slate.settle_est_ts,
                        "leg_a": {
                            "token_id": r_lo.yes_over_token, "opp_token_id": r_lo.no_under_token,
                            "condition_id": r_lo.condition_id, "market_id": r_lo.market_id,
                            "side": "OVER", "label": f"{r_lo.player_name} {stat_t} O{r_lo.line:g}",
                            "fee_rate": r_lo.fee_rate, "fee_exponent": r_lo.fee_exponent,
                            "neg_risk": False, "strike": r_lo.line, "end_ts": slate.settle_est_ts,
                        },
                        "leg_b": {
                            "token_id": r_hi.no_under_token, "opp_token_id": r_hi.yes_over_token,
                            "condition_id": r_hi.condition_id, "market_id": r_hi.market_id,
                            "side": "UNDER", "label": f"{r_hi.player_name} {stat_t} U{r_hi.line:g}",
                            "fee_rate": r_hi.fee_rate, "fee_exponent": r_hi.fee_exponent,
                            "neg_risk": False, "strike": r_hi.line, "end_ts": slate.settle_est_ts,
                        },
                        "label": f"{r_lo.player_name} {stat_t} O{r_lo.line:g} + U{r_hi.line:g}",
                    })

    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


def parse_espn_nfl_summary(summary_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses ESPN NFL `summary?event={id}` into:
      - `players`: `{player_key: {receptions, receiving_yards, longest_reception, rushing_yards,
                     longest_rush, passing_completions, passing_attempts, passing_yards,
                     passing_touchdowns, rush_rec_tds}}`
      - `inactive_players`: `set` of `player_key` explicitly marked `didNotPlay == True` on teams
        that already have active stat-recording players on the field.
      - `state`, `completed`, `period`, `game_id`.
    """
    players: Dict[str, Dict[str, int]] = {}
    dnp_candidates: List[Tuple[str, str]] = []
    teams_with_active: set[str] = set()

    for team_blk in ((summary_json or {}).get("boxscore") or {}).get("players") or []:
        tm_id = str((team_blk.get("team") or {}).get("id") or "")
        for stat_blk in team_blk.get("statistics") or []:
            cat = str(stat_blk.get("name") or "").lower()
            keys = [str(k) for k in (stat_blk.get("keys") or stat_blk.get("labels") or [])]
            for ath in stat_blk.get("athletes") or []:
                pkey = canon_player_name(str((ath.get("athlete") or {}).get("displayName") or ""))
                if not pkey:
                    continue
                if ath.get("didNotPlay"):
                    dnp_candidates.append((tm_id, pkey))
                    continue
                arr = [str(x) for x in (ath.get("stats") or [])]
                if not arr:
                    continue
                teams_with_active.add(tm_id)
                rec = players.setdefault(pkey, {"rush_rec_tds": 0})

                def _get_int(key_aliases: Tuple[str, ...]) -> Optional[int]:
                    for idx_k, kk in enumerate(keys):
                        if kk in key_aliases and idx_k < len(arr):
                            try:
                                return int(float(arr[idx_k].strip()))
                            except ValueError:
                                return None
                    return None

                if cat == "passing":
                    # `C/ATT` is index 0 (`completions/passingAttempts` -> `"21/31"`)
                    for idx_k, kk in enumerate(keys):
                        if ("completions" in kk or kk.upper() == "C/ATT") and idx_k < len(arr) and "/" in arr[idx_k]:
                            c_s, a_s = arr[idx_k].split("/", 1)
                            try:
                                rec["passing_completions"] = int(c_s)
                                rec["passing_attempts"] = int(a_s)
                            except ValueError:
                                pass
                    py = _get_int(("passingYards", "YDS"))
                    ptd = _get_int(("passingTouchdowns", "TD"))
                    if py is not None:
                        rec["passing_yards"] = py
                    if ptd is not None:
                        rec["passing_touchdowns"] = ptd
                elif cat == "rushing":
                    ry = _get_int(("rushingYards", "YDS"))
                    rtd = _get_int(("rushingTouchdowns", "TD"))
                    lr = _get_int(("longRushing", "LONG"))
                    if ry is not None:
                        rec["rushing_yards"] = ry
                    if lr is not None:
                        rec["longest_rush"] = lr
                    if rtd is not None:
                        rec["rushing_tds"] = rtd
                elif cat == "receiving":
                    rc = _get_int(("receptions", "REC"))
                    rcy = _get_int(("receivingYards", "YDS"))
                    rctd = _get_int(("receivingTouchdowns", "TD"))
                    lrec = _get_int(("longReception", "LONG"))
                    if rc is not None:
                        rec["receptions"] = rc
                    if rcy is not None:
                        rec["receiving_yards"] = rcy
                    if lrec is not None:
                        rec["longest_reception"] = lrec
                    if rctd is not None:
                        rec["receiving_tds"] = rctd

                elif cat in ("defensive", "kickreturns", "puntreturns", "fumbles", "interceptions"):
                    ntd = _get_int((
                        "defensiveTouchdowns",
                        "kickReturnTouchdowns",
                        "puntReturnTouchdowns",
                        "fumbleRecoveryTouchdowns",
                        "interceptionTouchdowns",
                        "touchdowns",
                        "TD",
                    ))
                    if ntd is not None and ntd > 0:
                        rec["non_off_tds"] = int(rec.get("non_off_tds", 0)) + ntd

    for rec in players.values():
        rec["rush_rec_tds"] = int(rec.get("rushing_tds", 0)) + int(rec.get("receiving_tds", 0))
        rec["all_tds"] = int(rec["rush_rec_tds"]) + int(rec.get("non_off_tds", 0))

    td_play_blobs: List[str] = []
    for sp_item in (summary_json or {}).get("scoringPlays") or []:
        if not isinstance(sp_item, dict):
            continue
        sp_type = str(((sp_item.get("scoringType") or {}).get("abbreviation") or (sp_item.get("type") or {}).get("text") or "")).upper()
        sp_txt = str(sp_item.get("text") or "")
        if "TD" in sp_type or "TOUCHDOWN" in sp_type or "touchdown" in sp_txt.lower():
            td_play_blobs.append(canon_player_name(sp_txt))

    inactive_set = {
        pk for (tid, pk) in dnp_candidates
        if tid in teams_with_active and pk not in players
    }

    state, completed, period, gid = "pre", False, 0, ""
    comps = ((summary_json or {}).get("header") or {}).get("competitions") or []
    if comps:
        c0 = comps[0]
        gid = str(c0.get("id") or "")
        st = c0.get("status") or {}
        st_t = st.get("type") or {}
        state = str(st_t.get("state") or "pre").lower()
        completed = bool(st_t.get("completed"))
        period = int(st.get("period") or 0)

    return {
        "game_id": gid,
        "state": state,
        "completed": completed,
        "period": period,
        "players": players,
        "inactive_players": inactive_set,
        "td_scoring_texts": td_play_blobs,
    }


def fetch_espn_nfl_summary_sync(espn_game_id: str, timeout: float = 5.0) -> Dict[str, Any]:
    url = ESPN_NFL_SUMMARY_URL.format(game_id=espn_game_id)
    req = urllib.request.Request(url, headers={"User-Agent": "DominusSportsOracle/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    return parse_espn_nfl_summary(data)


def evaluate_nfl_prp1_live_locks(
    slate: NflPlayerPropSlate,
    nfl_summary: Dict[str, Any],
    tracker: ScoreConfirmationTracker,
    now_ts: float,
    play_confirm_sec: float = 240.0,
    td_confirm_sec: float = 180.0,
) -> List[Dict[str, Any]]:
    """
    Evaluates irreversible NFL player prop locks:
      1. `longest_reception` & `longest_rush` running-maximum `OVER` locks (`>= floor(K) + 2` in-play
         after `240s` penalty/coach's-challenge cooldown; `>= floor(K) + 1` at Final).
      2. Monotonic counters (`receptions`, `passing_completions`, `passing_attempts` with `+2` live / `+1` Final)
         and `TD` clinches (`anytime_td >= 1`, `two_plus_td >= 2`, `passing_touchdowns` after `180s` booth-review check).
      3. `STATUS_FINAL` yardage `OVER`/`UNDER` locks (`abs(val - line) >= 2.5`).
      4. Official Inactive (`didNotPlay == True`, `is_final == True`) `"No"` locks ONLY when `rg.dnp_resolves_no == True`
         (protecting against Polymarket's standard `50-50` 0-snap void rule!).
    """
    state = str(nfl_summary.get("state") or "pre").lower()
    if state not in ("in", "post"):
        return []
    is_final = bool(nfl_summary.get("completed") and state == "post")
    gid = str(nfl_summary.get("game_id") or slate.event_id)
    players: Dict[str, Dict[str, int]] = nfl_summary.get("players") or {}
    inactives: set[str] = set(nfl_summary.get("inactive_players") or set())
    td_texts: List[str] = list(nfl_summary.get("td_scoring_texts") or [])
    locks: List[Dict[str, Any]] = []

    # 1. TD Yes locks (post-booth-review) + Verified Final DNP No locks
    for td_map, req_tds, tag in ((slate.anytime_td_by_player, 1, "Anytime TD"), (slate.two_plus_td_by_player, 2, "2+ TDs")):
        for pkey, rg in td_map.items():
            p_rec = players.get(pkey)
            if p_rec is not None:
                raw_tds = int(p_rec.get("all_tds", p_rec.get("rush_rec_tds", 0)))
                conf_tds = tracker.observe_and_confirmed_floor(
                    "NFL", gid, f"TD:{pkey}", raw_tds, now_ts, td_confirm_sec, is_final=is_final
                )
                if conf_tds >= req_tds:
                    locks.append({
                        "mode": "NFL_PRP1_TD_CLINCH_LOCK",
                        "market_id": rg.market_id, "condition_id": rg.condition_id,
                        "token_id": rg.yes_over_token, "opp_token_id": rg.no_under_token,
                        "side_label": "YES",
                        "display_label": f"{rg.player_name} {tag} YES [Confirmed TDs={conf_tds}]",
                        "fee_rate": rg.fee_rate, "fee_exponent": rg.fee_exponent,
                        "neg_risk": False, "p_lock": 0.999 if is_final else 0.998, "close_ts": rg.settle_est_ts,
                    })
                elif is_final and raw_tds < req_tds:
                    # Cross-check scoringPlays text so a return/fumble-recovery TD unrecorded in rush/rec never triggers a false NO!
                    if any(pkey in blob for blob in td_texts):
                        continue
                    locks.append({
                        "mode": "NFL_PRP1_FINAL_TD_NO_LOCK",
                        "market_id": rg.market_id, "condition_id": rg.condition_id,
                        "token_id": rg.no_under_token, "opp_token_id": rg.yes_over_token,
                        "side_label": "NO",
                        "display_label": f"{rg.player_name} {tag} NO [Final TDs={raw_tds}]",
                        "fee_rate": rg.fee_rate, "fee_exponent": rg.fee_exponent,
                        "neg_risk": False, "p_lock": 0.999, "close_ts": rg.settle_est_ts,
                    })
            elif pkey in inactives and is_final and rg.dnp_resolves_no:
                locks.append({
                    "mode": "NFL_PRP1_INACTIVE_DNP_NO_LOCK",
                    "market_id": rg.market_id, "condition_id": rg.condition_id,
                    "token_id": rg.no_under_token, "opp_token_id": rg.yes_over_token,
                    "side_label": "NO",
                    "display_label": f"{rg.player_name} {tag} NO [Official Final DNP->No]",
                    "fee_rate": rg.fee_rate, "fee_exponent": rg.fee_exponent,
                    "neg_risk": False, "p_lock": 0.998, "close_ts": rg.settle_est_ts,
                })

    # 2. Running-Maximum (`longest_reception`, `longest_rush`), Monotonic Counters, and Final Yardage
    for (pkey, stat_t), rungs in slate.ladders_by_player_stat.items():
        p_rec = players.get(pkey)
        if not p_rec or stat_t not in p_rec:
            continue
        raw_v = int(p_rec[stat_t])
        if stat_t in ("longest_reception", "longest_rush", "receptions", "passing_completions", "passing_attempts", "passing_touchdowns"):
            wait_s = td_confirm_sec if stat_t == "passing_touchdowns" else play_confirm_sec
            conf_v = tracker.observe_and_confirmed_floor("NFL", gid, f"{stat_t}:{pkey}", raw_v, now_ts, wait_s, is_final=is_final)
            extra_buf = 1 if (is_final or stat_t == "passing_touchdowns") else 2
            for rg in rungs:
                if conf_v >= int(math.floor(rg.line)) + extra_buf:
                    locks.append({
                        "mode": "NFL_PRP1_MAX_PLAY_LOCK" if stat_t.startswith("longest_") else "NFL_PRP1_COUNTER_LOCK",
                        "market_id": rg.market_id, "condition_id": rg.condition_id,
                        "token_id": rg.yes_over_token, "opp_token_id": rg.no_under_token,
                        "side_label": "OVER",
                        "display_label": f"{rg.player_name} {stat_t} O{rg.line:g} [Confirmed={conf_v}]",
                        "fee_rate": rg.fee_rate, "fee_exponent": rg.fee_exponent,
                        "neg_risk": False, "p_lock": 0.999 if is_final else 0.998, "close_ts": rg.settle_est_ts,
                    })
                elif is_final and raw_v <= int(math.floor(rg.line)) - 1:
                    locks.append({
                        "mode": "NFL_PRP1_FINAL_UNDER_LOCK",
                        "market_id": rg.market_id, "condition_id": rg.condition_id,
                        "token_id": rg.no_under_token, "opp_token_id": rg.yes_over_token,
                        "side_label": "UNDER",
                        "display_label": f"{rg.player_name} {stat_t} U{rg.line:g} [Final={raw_v}]",
                        "fee_rate": rg.fee_rate, "fee_exponent": rg.fee_exponent,
                        "neg_risk": False, "p_lock": 0.999, "close_ts": rg.settle_est_ts,
                    })
        elif is_final and stat_t in ("passing_yards", "rushing_yards", "receiving_yards"):
            for rg in rungs:
                if abs(float(raw_v) - rg.line) >= 2.5:
                    over_w = float(raw_v) > rg.line
                    locks.append({
                        "mode": "NFL_PRP1_FINAL_YARDAGE_LOCK",
                        "market_id": rg.market_id, "condition_id": rg.condition_id,
                        "token_id": rg.yes_over_token if over_w else rg.no_under_token,
                        "opp_token_id": rg.no_under_token if over_w else rg.yes_over_token,
                        "side_label": "OVER" if over_w else "UNDER",
                        "display_label": f"{rg.player_name} {stat_t} {'O' if over_w else 'U'}{rg.line:g} [Final={raw_v}]",
                        "fee_rate": rg.fee_rate, "fee_exponent": rg.fee_exponent,
                        "neg_risk": False, "p_lock": 0.998, "close_ts": rg.settle_est_ts,
                    })

    return locks


# ==============================================================================
# 4. SLEEVE #4: SUM1_FRECHET_SUM_TRIANGLES (3-Leg Additive Sum Identities)
# ==============================================================================
def detect_sum1_frechet_triangles(
    bundle: AffineGameBundle,
    best_asks: Dict[str, float],
    max_3leg_cost_net: float = 0.990,
) -> List[Dict[str, Any]]:
    """
    Detects fee-exact 3-leg additive sum-decomposition triangles `X + Y = Z` (all `.5` hooks,
    identical OT & `50-50` cancellation semantics -> `$1.50` if canceled, `>= $1.00` in every `(X, Y)`!):
      - Upper Triangle: `OVER(X, K_X) + OVER(Y, K_Y) + UNDER(Z, K_Z)` iff `K_Z >= K_X + K_Y - 0.5`
        (`n_Z >= n_X + n_Y`).
      - Lower Triangle: `UNDER(X, K_X) + UNDER(Y, K_Y) + OVER(Z, K_Z)` iff `K_Z <= K_X + K_Y + 1.5`
        (`n_Z <= n_X + n_Y + 1`).
    """
    triples: List[Tuple[str, List[NbaSubperiodMarketSpec], List[NbaSubperiodMarketSpec], List[NbaSubperiodMarketSpec]]] = []

    # Triple 1: Away FG Team Total + Home FG Team Total == FG Game Total (NBA, NFL, CFB)
    x_away = [m for m in bundle.markets if m.period_scope == "FG" and m.kind == "TEAM_TOTAL" and m.team_side == bundle.away_team and m.line is not None]
    y_home = [m for m in bundle.markets if m.period_scope == "FG" and m.kind == "TEAM_TOTAL" and m.team_side == bundle.home_team and m.line is not None]
    z_fg = [m for m in bundle.markets if m.period_scope == "FG" and m.kind == "TOTAL" and m.line is not None]
    if x_away and y_home and z_fg:
        triples.append(("SUM1_AWAY_HOME_FG_TOTAL", x_away, y_home, z_fg))

    # Triple 2: Q1 Total + Q2 Total == 1H Total (NBA, NFL, CFB — all 3 exclude OT!)
    x_q1 = [m for m in bundle.markets if m.period_scope == "Q1" and m.kind == "TOTAL" and m.line is not None]
    y_q2 = [m for m in bundle.markets if m.period_scope == "Q2" and m.kind == "TOTAL" and m.line is not None]
    z_1h = [m for m in bundle.markets if m.period_scope == "1H" and m.kind == "TOTAL" and m.line is not None]
    if x_q1 and y_q2 and z_1h:
        triples.append(("SUM1_Q1_Q2_1H_TOTAL", x_q1, y_q2, z_1h))

    # Triple 3: NBA 1H Team Total + 2H Team Total == FG Team Total (both 2H & FG include OT!)
    if bundle.sport == "NBA":
        for tm in (bundle.away_team, bundle.home_team):
            x_1ht = [m for m in bundle.markets if m.period_scope == "1H" and m.kind == "TEAM_TOTAL" and m.team_side == tm and m.line is not None]
            y_2ht = [m for m in bundle.markets if m.period_scope == "2H" and m.kind == "TEAM_TOTAL" and m.team_side == tm and m.line is not None]
            z_fgt = [m for m in bundle.markets if m.period_scope == "FG" and m.kind == "TEAM_TOTAL" and m.team_side == tm and m.line is not None]
            if x_1ht and y_2ht and z_fgt:
                triples.append((f"SUM1_1H_2H_FG_TEAM_{tm.upper()[:8]}", x_1ht, y_2ht, z_fgt))

    arbs: List[Dict[str, Any]] = []
    for mode_tag, xs, ys, zs in triples:
        for mx in xs:
            kx = float(mx.line)  # type: ignore[arg-type]
            nx = int(math.floor(kx))
            px_ov = best_asks.get(mx.tok_0)
            px_un = best_asks.get(mx.tok_1)
            for my in ys:
                if mx.market_id == my.market_id:
                    continue
                ky = float(my.line)  # type: ignore[arg-type]
                ny = int(math.floor(ky))
                py_ov = best_asks.get(my.tok_0)
                py_un = best_asks.get(my.tok_1)
                for mz in zs:
                    if mz.market_id in (mx.market_id, my.market_id):
                        continue
                    kz = float(mz.line)  # type: ignore[arg-type]
                    nz = int(math.floor(kz))
                    pz_ov = best_asks.get(mz.tok_0)
                    pz_un = best_asks.get(mz.tok_1)

                    # Upper Triangle: Over X + Over Y + Under Z (requires nz >= nx + ny)
                    if nz >= nx + ny and px_ov is not None and py_ov is not None and pz_un is not None:
                        c_up = round(
                            _net_unit_ask(float(px_ov), mx.fee_rate, mx.fee_exponent)
                            + _net_unit_ask(float(py_ov), my.fee_rate, my.fee_exponent)
                            + _net_unit_ask(float(pz_un), mz.fee_rate, mz.fee_exponent),
                            4,
                        )
                        if c_up <= max_3leg_cost_net:
                            lx = _leg_dict_from_subspec(mx, True)
                            ly = _leg_dict_from_subspec(my, True)
                            lz = _leg_dict_from_subspec(mz, False)
                            arbs.append({
                                "mode": f"{mode_tag}_UPPER",
                                "sport": bundle.sport,
                                "event_id": bundle.event_id,
                                "slug": bundle.slug,
                                "title": bundle.title,
                                "n_legs": 3,
                                "box_cost_gross": round(float(px_ov) + float(py_ov) + float(pz_un), 4),
                                "box_cost_net": c_up,
                                "close_ts": max(lx["end_ts"], ly["end_ts"], lz["end_ts"]),
                                "legs": [lx, ly, lz],
                                "label": f"{bundle.title}: {lx['label']} + {ly['label']} + {lz['label']}",
                            })

                    # Lower Triangle: Under X + Under Y + Over Z (requires nz <= nx + ny + 1)
                    if nz <= nx + ny + 1 and px_un is not None and py_un is not None and pz_ov is not None:
                        c_lo = round(
                            _net_unit_ask(float(px_un), mx.fee_rate, mx.fee_exponent)
                            + _net_unit_ask(float(py_un), my.fee_rate, my.fee_exponent)
                            + _net_unit_ask(float(pz_ov), mz.fee_rate, mz.fee_exponent),
                            4,
                        )
                        if c_lo <= max_3leg_cost_net:
                            lx = _leg_dict_from_subspec(mx, False)
                            ly = _leg_dict_from_subspec(my, False)
                            lz = _leg_dict_from_subspec(mz, True)
                            arbs.append({
                                "mode": f"{mode_tag}_LOWER",
                                "sport": bundle.sport,
                                "event_id": bundle.event_id,
                                "slug": bundle.slug,
                                "title": bundle.title,
                                "n_legs": 3,
                                "box_cost_gross": round(float(px_un) + float(py_un) + float(pz_ov), 4),
                                "box_cost_net": c_lo,
                                "close_ts": max(lx["end_ts"], ly["end_ts"], lz["end_ts"]),
                                "legs": [lx, ly, lz],
                                "label": f"{bundle.title}: {lx['label']} + {ly['label']} + {lz['label']}",
                            })

    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


# ==============================================================================
# 5. SLEEVE #5: CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION (`Close subset Hit`, `Sub subset Super`)
# ==============================================================================
@dataclass
class CryptoCloseRungSpec:
    event_id: str
    slug: str
    asset: str
    market_id: str
    condition_id: str
    question: str
    strike: float
    direction: str        # "UP" ("above") or "DOWN" ("below")
    close_ts: float
    yes_token: str
    no_token: str
    fee_rate: float
    fee_exponent: float


_CRYPTO_SLUG_ASSET_MAP: Tuple[Tuple[str, str], ...] = (
    ("bitcoin-", "BTC"),
    ("btc-", "BTC"),
    ("ethereum-", "ETH"),
    ("eth-", "ETH"),
    ("solana-", "SOL"),
    ("sol-", "SOL"),
    ("xrp-", "XRP"),
    ("bnb-", "BNB"),
    ("dogecoin-", "DOGE"),
    ("doge-", "DOGE"),
)


def parse_binance_terminal_close_event(ev: Dict[str, Any]) -> List[CryptoCloseRungSpec]:
    """
    Parses Binance Spot USDT `1m`-close terminal barrier ladders (e.g. `bitcoin-above-on-november-2`,
    `ethereum-price-on-*` binary above/below rungs), strictly verifying `"binance"` in description
    and rejecting Chainlink / Pyth / one-touch `"hit"`/`"reach"`/`"dip"` events!
    """
    if ev.get("closed") or ev.get("archived"):
        return []
    slug = str(ev.get("slug") or "").lower()
    if any(w in slug for w in ("hit-price", "up-or-down", "updown", "5m", "15m")):
        return []
    asset = next((sym for pref, sym in _CRYPTO_SLUG_ASSET_MAP if slug.startswith(pref)), "")
    if not asset:
        return []
    end_ts = _parse_iso_ts(ev.get("endDate")) or 0.0
    if end_ts <= 0.0:
        return []

    out: List[CryptoCloseRungSpec] = []
    for m in ev.get("markets") or []:
        if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
            continue
        q = str(m.get("question") or "")
        gl = str(m.get("groupItemTitle") or "")
        desc = str(m.get("description") or ev.get("description") or "").lower()
        # Strictly verify Binance Spot USDT oracle and terminal-close wording (never one-touch!)
        if "binance" not in desc or "chain.link" in desc or "pyth.network" in desc:
            continue
        ql = q.lower()
        if any(w in ql for w in ("reach", "hit", "touch", "dip", "between")):
            continue
        if not any(w in ql for w in ("above", "below", "over", "under", "greater than", "less than")):
            continue
        # Reject range brackets like `$68,000 - $70,000`
        if re.search(r"\d[\d,]*\s*[-–to]+\s*\$?\d", gl):
            continue
        direction = "DOWN" if any(w in ql for w in ("below", "under", "less than")) else "UP"
        strike = parse_strike_from_text(q, gl)
        toks = _parse_clob_tokens(m)
        outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
        if not strike or strike <= 0.0 or not toks or outs != ["yes", "no"]:
            continue
        fr, fe = _extract_market_fee_rate(m)
        m_end = _parse_iso_ts(m.get("endDate")) or end_ts
        out.append(CryptoCloseRungSpec(
            event_id=str(ev.get("id") or ""), slug=slug, asset=asset,
            market_id=str(m.get("id") or ""), condition_id=str(m.get("conditionId") or ""),
            question=q, strike=strike, direction=direction, close_ts=m_end,
            yes_token=toks[0], no_token=toks[1], fee_rate=fr, fee_exponent=fe,
        ))
    return out


def detect_cry_inc1_binance_inclusion_boxes(
    hit_rungs: List[BarrierRungSpec],
    close_rungs: List[CryptoCloseRungSpec],
    best_asks: Dict[str, float],
    now_ts: float,
    max_box_cost_net: float = 0.992,
) -> List[Dict[str, Any]]:
    """
    Detects fee-exact Same-Oracle (`binance.com` `1m` USDT kline) Cross-Event Inclusion Boxes:
      1. `CRY_INC1_CLOSE_SUBSET_HIT`:
         - Upward: `NO(Close > K_close at T_c) + YES(Hit >= K_hit in [start_h, end_h])`
           whenever `start_h <= T_c <= end_h + 60`, `start_h <= now_ts + 60`, and `K_hit <= K_close`.
         - Downward: `NO(Close < K_close at T_c) + YES(Dip <= K_hit in [start_h, end_h])`
           whenever `start_h <= T_c <= end_h + 60`, `start_h <= now_ts + 60`, and `K_hit >= K_close`.
      2. `CRY_INC1_SUBWINDOW_HIT_INCLUSION`:
         - `NO(Short Hit) + YES(Long Hit)` when `start_long <= start_short + 1e-6` and
           `end_long >= end_short + 1800` (`Daily subset Weekly subset Monthly`), with
           `K_long <= K_short` (`UP`) or `K_long >= K_short` (`DOWN`).
    """
    open_hits = [
        h for h in hit_rungs
        if h.resolved_yes is None and h.end_ts > now_ts + 120.0 and h.asset != "HYPE"  # HYPE uses futures; Spot only!
    ]
    arbs: List[Dict[str, Any]] = []

    # 1. Terminal Close subset One-Touch Hit
    for cr in close_rungs:
        if cr.close_ts <= now_ts + 120.0 or cr.asset == "HYPE":
            continue
        p_no_c = best_asks.get(cr.no_token)
        if p_no_c is None or not (0.01 <= p_no_c <= 0.98):
            continue
        cost_c = _net_unit_ask(float(p_no_c), cr.fee_rate, cr.fee_exponent)
        for hr in open_hits:
            if hr.asset != cr.asset or hr.direction != cr.direction or hr.market_id == cr.market_id:
                continue
            # Active hit window must already have started and strictly cover `cr.close_ts` (zero overhang gap!)
            if not (hr.start_ts <= now_ts and hr.start_ts <= cr.close_ts - 60.0 and cr.close_ts <= hr.end_ts):
                continue
            strike_ok = (hr.strike <= cr.strike + 1e-9) if cr.direction == "UP" else (hr.strike >= cr.strike - 1e-9)
            if not strike_ok:
                continue
            p_yes_h = best_asks.get(hr.yes_token)
            if p_yes_h is None or not (0.01 <= p_yes_h <= 0.98):
                continue
            c_tot = round(cost_c + _net_unit_ask(float(p_yes_h), hr.fee_rate, hr.fee_exponent), 4)
            if c_tot <= max_box_cost_net:
                sym_dir = "↑" if cr.direction == "UP" else "↓"
                arbs.append({
                    "mode": "CRY_INC1_CLOSE_SUBSET_HIT",
                    "asset": cr.asset,
                    "direction": cr.direction,
                    "box_cost_gross": round(float(p_no_c) + float(p_yes_h), 4),
                    "box_cost_net": c_tot,
                    "close_ts": max(cr.close_ts, hr.end_ts),
                    "leg_a": {
                        "token_id": cr.no_token, "opp_token_id": cr.yes_token,
                        "condition_id": cr.condition_id, "market_id": cr.market_id,
                        "side": "NO", "label": f"NO[{cr.asset} Close {sym_dir}{cr.strike:g}]",
                        "fee_rate": cr.fee_rate, "fee_exponent": cr.fee_exponent,
                        "neg_risk": False, "strike": cr.strike, "end_ts": cr.close_ts,
                    },
                    "leg_b": {
                        "token_id": hr.yes_token, "opp_token_id": hr.no_token,
                        "condition_id": hr.condition_id, "market_id": hr.market_id,
                        "side": "YES", "label": f"YES[{cr.asset} {hr.horizon_group} Hit {sym_dir}{hr.strike:g}]",
                        "fee_rate": hr.fee_rate, "fee_exponent": hr.fee_exponent,
                        "neg_risk": False, "strike": hr.strike, "end_ts": hr.end_ts,
                    },
                    "label": f"{cr.asset} NO(Close {sym_dir}{cr.strike:g}) + YES({hr.horizon_group} Hit {sym_dir}{hr.strike:g})",
                })

    # 2. Sub-Window Hit subset Super-Window Hit (`DAILY subset WEEKLY subset MONTHLY`)
    for hs in open_hits:
        p_no_s = best_asks.get(hs.no_token)
        if p_no_s is None or not (0.01 <= p_no_s <= 0.98):
            continue
        cost_s = _net_unit_ask(float(p_no_s), hs.fee_rate, hs.fee_exponent)
        for hl in open_hits:
            if (
                hl.asset != hs.asset
                or hl.direction != hs.direction
                or hl.event_id == hs.event_id
                or hl.market_id == hs.market_id
            ):
                continue
            # Long window must start NO LATER than short window (defeats mid-month dynamic rung mismatch!)
            # and end at least 30 minutes strictly after short window.
            if not (hl.start_ts <= hs.start_ts + 1e-6 and hl.end_ts >= hs.end_ts + 1800.0):
                continue
            strike_ok = (hl.strike <= hs.strike + 1e-9) if hs.direction == "UP" else (hl.strike >= hs.strike - 1e-9)
            if not strike_ok:
                continue
            p_yes_l = best_asks.get(hl.yes_token)
            if p_yes_l is None or not (0.01 <= p_yes_l <= 0.98):
                continue
            c_tot = round(cost_s + _net_unit_ask(float(p_yes_l), hl.fee_rate, hl.fee_exponent), 4)
            if c_tot <= max_box_cost_net:
                sym_dir = "↑" if hs.direction == "UP" else "↓"
                arbs.append({
                    "mode": "CRY_INC1_SUBWINDOW_HIT_INCLUSION",
                    "asset": hs.asset,
                    "direction": hs.direction,
                    "box_cost_gross": round(float(p_no_s) + float(p_yes_l), 4),
                    "box_cost_net": c_tot,
                    "close_ts": hl.end_ts,
                    "leg_a": {
                        "token_id": hs.no_token, "opp_token_id": hs.yes_token,
                        "condition_id": hs.condition_id, "market_id": hs.market_id,
                        "side": "NO", "label": f"NO[{hs.asset} {hs.horizon_group} {sym_dir}{hs.strike:g}]",
                        "fee_rate": hs.fee_rate, "fee_exponent": hs.fee_exponent,
                        "neg_risk": False, "strike": hs.strike, "end_ts": hs.end_ts,
                    },
                    "leg_b": {
                        "token_id": hl.yes_token, "opp_token_id": hl.no_token,
                        "condition_id": hl.condition_id, "market_id": hl.market_id,
                        "side": "YES", "label": f"YES[{hl.asset} {hl.horizon_group} {sym_dir}{hl.strike:g}]",
                        "fee_rate": hl.fee_rate, "fee_exponent": hl.fee_exponent,
                        "neg_risk": False, "strike": hl.strike, "end_ts": hl.end_ts,
                    },
                    "label": f"{hs.asset} NO({hs.horizon_group} {sym_dir}{hs.strike:g}) + YES({hl.horizon_group} {sym_dir}{hl.strike:g})",
                })

    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


# ==============================================================================
# 6. SLEEVE #6: MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER (`0%` Maker Fee + Rebate)
# ==============================================================================
def evaluate_mkr_lock1_post_clinch_rebate_bid(
    *,
    token_id: str,
    opp_token_id: str,
    market_id: str,
    condition_id: str,
    display_label: str,
    source_sleeve: str,
    p_lock: float,
    close_ts: float,
    now_ts: float,
    best_bid: Optional[float],
    best_ask: Optional[float],
    opp_best_bid: Optional[float],
    fee_rate: float = 0.05,
    fee_exponent: float = 1.0,
    maker_rebate_share: float = 0.20,
    neg_risk: bool = False,
    tick_size: float = 0.001,
    min_maker_bid: float = 0.960,
    max_maker_bid: float = 0.991,
    min_net_edge_ps: float = 0.006,
    max_tte_sec: float = 14400.0,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates a passive `post_only=True` resting Maker Bid on an ALREADY-CLINCHED contract
    (`p_lock >= 0.997`, `TTE <= 4h`, `opp_best_bid <= 0.03`) whose taker `best_ask` is too
    expensive (`>= $0.992` or empty):
      - Maker pays `0.00%` fee AND earns `maker_rebate_share * fee_rate * (b*(1-b))**fee_exponent`
        when hit by an impatient holder cashing out early before UMA resolution!
      - Never crosses `best_ask` (`target_bid <= best_ask - tick_size`).
    """
    if p_lock < 0.997:
        return None
    tte = float(close_ts) - float(now_ts)
    if not (60.0 <= tte <= max_tte_sec):
        return None
    if opp_best_bid is not None and float(opp_best_bid) > 0.03:
        return None
    # Only route to passive Maker Lock when taker ask is NOT already cheap enough (< 0.988 net)
    if best_ask is not None and float(best_ask) > 0.0:
        taker_net = _net_unit_ask(float(best_ask), fee_rate, fee_exponent)
        if taker_net <= 0.988:
            return None

    t_sz = max(0.001, float(tick_size))
    ceil_from_ask = (float(best_ask) - t_sz) if (best_ask is not None and float(best_ask) > 0.0) else max_maker_bid
    max_allowed = min(float(max_maker_bid), ceil_from_ask, float(p_lock) - min_net_edge_ps + 0.002)
    if max_allowed < min_maker_bid - 1e-9:
        return None

    if best_bid is not None and float(best_bid) >= min_maker_bid:
        cand_bid = min(max_allowed, float(best_bid) + t_sz)
    else:
        cand_bid = min(max_allowed, 0.986)

    # Quantize down to tick grid
    steps = math.floor((cand_bid + 1e-9) / t_sz)
    bid_px = round(steps * t_sz, 4)
    if not (min_maker_bid <= bid_px <= max_maker_bid):
        return None
    if best_ask is not None and float(best_ask) > 0.0 and bid_px >= float(best_ask) - 1e-9:
        return None

    rebate_ps = (
        float(maker_rebate_share) * float(fee_rate) * ((bid_px * (1.0 - bid_px)) ** float(fee_exponent))
        if fee_rate > 0.0
        else 0.0
    )
    eff_cost_ps = round(bid_px - rebate_ps, 6)
    net_edge_ps = round(float(p_lock) - eff_cost_ps, 6)
    if net_edge_ps < min_net_edge_ps:
        return None

    return {
        "mode": "MKR_LOCK1_POST_CLINCH_REBATE_BID",
        "source_sleeve": source_sleeve,
        "token_id": token_id,
        "opp_token_id": opp_token_id,
        "market_id": market_id,
        "condition_id": condition_id,
        "display_label": f"MKR_LOCK[{display_label}] @{bid_px:.3f}",
        "post_only_bid": bid_px,
        "maker_rebate_per_share": round(rebate_ps, 6),
        "effective_net_cost_per_share": eff_cost_ps,
        "expected_net_edge_per_share": net_edge_ps,
        "p_lock": round(float(p_lock), 5),
        "fee_rate": float(fee_rate),
        "fee_exponent": float(fee_exponent),
        "neg_risk": bool(neg_risk),
        "close_ts": float(close_ts),
        "tte_sec": round(tte, 1),
    }

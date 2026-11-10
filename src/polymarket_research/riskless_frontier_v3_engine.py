#!/usr/bin/env python3
"""
Riskless Frontier v3 Engine — Six Next-Generation Algebraic & Post-Review Lock Sleeves
======================================================================================
Extends Dominus Shadow + Backtest coverage across the 6 highest-volume uncovered riskless
Polymarket structures verified live on Gamma/CLOB (`2026-10-30`):

  1. `LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG` (`Class I-A` + `Class II-A`, `0%` Fee):
     - Zero-assumption state-payoff matrices linking `republican-house-seats` (`aug=False`)
       with `House Control` & `BOP` (splitting `215-219` across `{D, R, Other}`),
       `republican-senate-seats` (`aug=False`) with `Senate Control`, `BOP` & `Supermajority Trifecta`
       (splitting `50` across `{D, R, Other}`), `7-Tossup Senate States` (`aug=False`, `m=128`)
       against individual `0%`-fee State Senate slates, and dynamic `pending-*` conditional
       partitions (e.g., `who-wins-the-senate-pending-hormuz-agreement-before-the-midterms`).
     - Closed-slate `NegRiskAdapterV2.convertPositions` upper-tail `NO` conversion + `YES[Control]`
       synthetic Polish Middles (`$2.00` payout on `218-219` R House or `50` R Senate).

  2. `SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION` (`Class I-A` + `Class III-B`, `0%` Fee):
     - NBA Completed Sub-Period Locks (`Q1`, `Q2`, `1H`, `Q3`) on `77` sub-period markets/game.
     - In-Period Monotonic Score Locks (`+3 pt` Secaucus buffer) on `Team Totals` & `Period Totals`.
     - Tie-proof `1H` & `Q1` `YES(ML[Team X]) + YES(Spread[Opp +k.5])` Polish Middles (`$1.50` on tie, `$2.00` middle).
     - `Steals` & `Blocks` `0%`-fee Polish Middles (`3B`) + post-`Final` (`+2` buffer) stat locks (`3A`).

  3. `CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX` (`Class I-A`, `0%` & Fee-Exact):
     - Clause-stem & timezone-verified temporal survival ladders (`continues-through`: `YES(T1) + NO(T2)`),
       cumulative first-passage ladders (`-by` / `before-`: `NO(T1) + YES(T2)`), and non-Crypto/Pyth
       scalar commitment/FDV strike ladders (`YES(Above K1) + NO(Above K2)`).

  4. `LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX` (`Class I-A`, Fee-Exact):
     - 11-state NFL `exact_margin` (`5` Fav + `Tie` + `4` Dog + `Canceled 50-50`) x `Moneyline` &
       boundary `Spreads` (`-6.5, -12.5, -13.5, -18.5, -20.5, -24.5`) super-replication matrix.
     - Multi-sport (`NFL`, `CFB`, `NHL`) `FG / 1H / Q1` tie-proof `ML + Opp(+k.5)` Polish Middles.

  5. `CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH` (`Class III-B`, Fee-Exact):
     - Sport-specific review-cleared monotonic score clinches via live ESPN scoreboards:
       Soccer (`>= 210s` post-VAR `Over K.5` & `BTTS=YES`), NHL (`>= 150s` post-challenge `Over K.5`),
       and NFL/CFB (completed `Q1/1H/Q3` sub-periods + `+9 pt` replay-immune in-play `Over K.5`).

  6. `TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR` (`Class I-A`, Fee-Exact `5%` ATP/WTA):
     - Injury-retirement-immune (`>= $1.00` across ALL retirement & completed states) same-set &
       same-match game corridors (`Set 1/2 O 8.5 + U 10.5`, `Match O 20.5 + U 23.5`) + post-`1-1`
       split `YES[Total Sets Over 2.5] + NO[Completed Match]` super-replicating box.
"""

from __future__ import annotations

import json
import math
import re
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.polymarket_research.riskless_frontier_v2_engine import (
    ESPN_NBA_SUMMARY_URL,
    NbaPlayerPropRung,
    NbaPlayerPropSlate,
    _infer_live_map_winner,
    _is_half_hook,
    _net_unit_bid,
    canon_player_name,
    find_state_matrix_dominance_boxes,
    parse_espn_nba_boxscore_players,
    verify_negrisk_adapter_slate_sync,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    _SPREAD_FAV_RE,
    _extract_market_fee_rate,
    _net_unit_ask,
    _norm_team,
    _parse_clob_tokens,
    _parse_iso_ts,
    _walk_side_exact_shares,
)
from src.polymarket_research.uma_nba_endgame_engine import (
    LiveNbaGameState,
    _canon_nba_team,
    _parse_json_list,
)

# ==============================================================================
# CONSTANTS & SLUG REGISTRIES
# ==============================================================================
LP2_MIDTERM_CORE_SLUGS: Tuple[str, ...] = (
    "republican-house-seats-after-the-2026-midterm-elections",
    "republican-senate-seats-after-the-2026-midterm-elections-927",
    "which-party-will-win-the-house-in-2026",
    "which-party-will-win-the-senate-in-2026",
    "balance-of-power-2026-midterms",
    "republican-trifecta-with-supermajority-in-the-senate",
    "who-wins-the-senate-pending-hormuz-agreement-before-the-midterms",
)

LP2_TOSSUP_CUBE_SLUG = "which-tossup-senate-states-will-republicans-win-ak-ia-ks-me-mi-oh-tx"
LP2_TOSSUP_STATE_SLUGS: Dict[str, str] = {
    "AK": "alaska-senate-election-winner",
    "IA": "iowa-senate-election-winner",
    "KS": "kansas-senate-election-winner",
    "ME": "maine-senate-election-winner",
    "MI": "michigan-senate-election-winner",
    "OH": "ohio-senate-election-winner",
    "TX": "texas-senate-election-winner",
}

ESPN_SCOREBOARD_URLS: Dict[str, Tuple[str, ...]] = {
    "SOCCER": (
        "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/ksa.1/scoreboard",
    ),
    "NHL": (
        "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    ),
    "NFL": (
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    ),
    "CFB": (
        "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?limit=100",
    ),
}

_EXT_PROP_TITLE_RE = re.compile(
    r"^(.+?):\s*(Steals|Blocks)\s+O/U\s+(\d+\.5)\b",
    re.IGNORECASE,
)
_NFL_EM_BAND_RE = re.compile(
    r"Exact\s+Margin:\s*(.+?)\s+by\s+(\d+)(?:-(\d+)|\+)",
    re.IGNORECASE,
)
_GENERIC_SPREAD_LINE_RE = re.compile(r"([+-]\d+\.5)\b")
_SCALAR_MAG_RE = re.compile(
    r"(?:↑|above|over|at\s+least|more\s+than|exceeds?)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([kmb]|thousand|million|billion)?\b",
    re.IGNORECASE,
)
_COVERED_CRYPTO_PYTH_SLUG_RE = re.compile(
    r"\b(?:bitcoin|btc|ethereum|eth|solana|sol|xrp|dogecoin|doge|bnb|sui|cardano|avax"
    r"|wti|crude-oil|xauusd|xagusd|gold-gc|silver-si|spy-hit|spy-daily|nvidia-hit|nvda-multi"
    r"|apple-hit|aapl-multi|tesla-hit|tsla-multi|microsoft-hit|msft-multi|amazon-hit|google-hit"
    r"|palantir-hit|coin-hit|hood-hit|natural-gas-hit)\b",
    re.IGNORECASE,
)
_RESET_WINDOW_VETO_RE = re.compile(
    r"\b(?:in\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)"
    r"|during\s+(?:the\s+)?(?:month|week|quarter|q[1-4])|between\s+[a-z]+\s+\d+\s+and\s+[a-z]+\s+\d+)\b",
    re.IGNORECASE,
)
_MONTH_DATE_STRIP_RE = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+\d{1,2}(?:,\s*20\d{2})?\b|\b20\d{2}-\d{2}-\d{2}\b|\bq[1-4]\s+20\d{2}\b",
    re.IGNORECASE,
)
_TZ_DETECT_RE = re.compile(
    r"\b(ET|EDT|EST|UTC|GMT|PT|PDT|PST|CT|EET|CET|IRST|Iran\s+Standard\s+Time|Eastern\s+European\s+Time|Eastern\s+Time)\b",
    re.IGNORECASE,
)


def _add_truth_leg(
    legs: List[Dict[str, Any]],
    m: Dict[str, Any],
    event_slug: str,
    tag_lbl: str,
    v_yes: List[float],
    v_no: Optional[List[float]] = None,
) -> None:
    if m.get("closed") or m.get("archived") or m.get("active") is False or m.get("acceptingOrders") is False:
        return
    toks = _parse_clob_tokens(m)
    if not toks:
        return
    fr, fe = _extract_market_fee_rate(m)
    end_ts = _parse_iso_ts(m.get("endDate")) or 0.0
    mid = str(m.get("id") or "")
    cid = str(m.get("conditionId") or "")
    nr = bool(m.get("negRisk"))
    if v_no is None:
        v_no = [1.0 - x for x in v_yes]
    legs.append({
        "event_slug": event_slug, "market_id": mid, "condition_id": cid,
        "token_id": toks[0], "opp_token_id": toks[1], "side": "YES",
        "label": f"YES[{tag_lbl}]", "fee_rate": fr, "fee_exponent": fe,
        "neg_risk": nr, "end_ts": end_ts, "payoff_vec": v_yes, "strike": 1.0,
    })
    legs.append({
        "event_slug": event_slug, "market_id": mid, "condition_id": cid,
        "token_id": toks[1], "opp_token_id": toks[0], "side": "NO",
        "label": f"NO[{tag_lbl}]", "fee_rate": fr, "fee_exponent": fe,
        "neg_risk": nr, "end_ts": end_ts, "payoff_vec": v_no, "strike": 1.0,
    })


# ==============================================================================
# 1. SLEEVE #1: LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG
# ==============================================================================
# 1A. House Seat Count x House Control x BOP (18 zero-assumption states):
#   Brackets 0..5 (`Below 190`..`210-214`): <=214 R seats (<218 majority) -> (b, D), (b, O) [12 states; R=0]
#   Bracket 6 (`215-219`): straddles 218 majority -> (6, D), (6, R), (6, O) [3 states]
#   Brackets 7..9 (`220-224`, `225-229`, `230+`): >=220 R seats (>218 majority of 435) -> (b, R) [3 states]
_HOUSE_SEAT_KEYS: Tuple[str, ...] = (
    "below 190", "190-194", "195-199", "200-204", "205-209",
    "210-214", "215-219", "220-224", "225-229", "230+",
)
_HOUSE_18_STATES: Tuple[Tuple[int, str], ...] = (
    tuple((b, ctrl) for b in range(6) for ctrl in ("D", "O"))
    + ((6, "D"), (6, "R"), (6, "O"))
    + ((7, "R"), (8, "R"), (9, "R"))
)


def build_lp2_house_seats_truth_legs(events_by_slug: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Builds exact 18-state payoff vectors linking House R Seat Ladder, House Control, and BOP."""
    ev_seats = events_by_slug.get("republican-house-seats-after-the-2026-midterm-elections") or {}
    if not ev_seats or ev_seats.get("closed"):
        return []
    legs: List[Dict[str, Any]] = []
    matched_b = set()
    for m in ev_seats.get("markets") or []:
        grp = str(m.get("groupItemTitle") or m.get("question") or "").strip().lower()
        b_idx = next((i for i, k in enumerate(_HOUSE_SEAT_KEYS) if grp == k or k in grp), None)
        if b_idx is None:
            continue
        matched_b.add(b_idx)
        _add_truth_leg(
            legs, m, "r_house_seats", f"HSeats:{_HOUSE_SEAT_KEYS[b_idx]}",
            [1.0 if sb == b_idx else 0.0 for sb, _ in _HOUSE_18_STATES],
        )
    if len(matched_b) < 8:
        return []

    ev_hse = events_by_slug.get("which-party-will-win-the-house-in-2026") or {}
    for m in ev_hse.get("markets") or []:
        grp = str(m.get("groupItemTitle") or "").strip().lower()
        if grp == "democratic party":
            _add_truth_leg(legs, m, "house_ctrl", "House:Dem", [1.0 if c == "D" else 0.0 for _, c in _HOUSE_18_STATES])
        elif grp == "republican party":
            _add_truth_leg(legs, m, "house_ctrl", "House:Rep", [1.0 if c == "R" else 0.0 for _, c in _HOUSE_18_STATES])
    return legs


# 1B. Senate Seat Count x Senate Control x Trifecta Supermajority (17 zero-assumption states):
#   Brackets 0..2 (`<=47`, `48`, `49`): <=49 R seats (<50) -> (b, D), (b, O) [6 states; R=0, Trifecta=0]
#   Bracket 3 (`50`): 50 R seats -> (3, D), (3, R), (3, O) [3 states; Trifecta=0]
#   Brackets 4..9 (`51`..`56`): 51..56 R seats (>50, <60) -> (b, R, 0) [6 states; R=1, Trifecta=0]
#   Bracket 10 (`57+`): >=57 R seats -> (10, R, 0), (10, R, 1) [2 states; R=1, Trifecta in {0,1}]
_SENATE_SEAT_KEYS: Tuple[str, ...] = (
    "≤47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57+",
)
_SENATE_17_STATES: Tuple[Tuple[int, str, int], ...] = (
    tuple((b, ctrl, 0) for b in range(2) for ctrl in ("D", "O"))
    + ((2, "D", 0), (2, "R", 0), (2, "O", 0))
    + ((3, "D", 0), (3, "R", 0), (3, "O", 0))
    + tuple((b, "R", 0) for b in range(4, 10))
    + ((10, "R", 0), (10, "R", 1))
)


def _match_senate_seat_idx(grp_raw: str) -> Optional[int]:
    g = grp_raw.strip().lower().replace("<=", "≤").replace(">=", "")
    if "47" in g and ("≤" in g or "below" in g or "less" in g or "under" in g):
        return 0
    if "57" in g and ("+" in g or "more" in g or "above" in g):
        return 10
    for idx, tok in enumerate(_SENATE_SEAT_KEYS):
        if g == tok:
            return idx
    return None


def build_lp2_senate_seats_truth_legs(events_by_slug: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Builds exact 17-state payoff vectors linking Senate R Seat Ladder, Senate Control, and Supermajority Trifecta."""
    ev_seats = events_by_slug.get("republican-senate-seats-after-the-2026-midterm-elections-927") or {}
    if not ev_seats or ev_seats.get("closed"):
        return []
    legs: List[Dict[str, Any]] = []
    matched_b = set()
    for m in ev_seats.get("markets") or []:
        grp = str(m.get("groupItemTitle") or m.get("question") or "")
        b_idx = _match_senate_seat_idx(grp)
        if b_idx is None:
            continue
        matched_b.add(b_idx)
        _add_truth_leg(
            legs, m, "r_sen_seats", f"SSeats:{_SENATE_SEAT_KEYS[b_idx]}",
            [1.0 if sb == b_idx else 0.0 for sb, _, _ in _SENATE_17_STATES],
        )
    if len(matched_b) < 9:
        return []

    ev_sen = events_by_slug.get("which-party-will-win-the-senate-in-2026") or {}
    for m in ev_sen.get("markets") or []:
        grp = str(m.get("groupItemTitle") or "").strip().lower()
        if grp == "democratic party":
            _add_truth_leg(legs, m, "sen_ctrl", "Sen:Dem", [1.0 if c == "D" else 0.0 for _, c, _ in _SENATE_17_STATES])
        elif grp == "republican party":
            _add_truth_leg(legs, m, "sen_ctrl", "Sen:Rep", [1.0 if c == "R" else 0.0 for _, c, _ in _SENATE_17_STATES])

    ev_tri = events_by_slug.get("republican-trifecta-with-supermajority-in-the-senate") or {}
    for m in ev_tri.get("markets") or []:
        _add_truth_leg(legs, m, "trifecta_60", "R_Trifecta60", [float(tri) for _, _, tri in _SENATE_17_STATES])
    return legs


def build_lp2_pending_senate_conditional_groups(
    conditional_events: List[Dict[str, Any]],
    senate_ev: Optional[Dict[str, Any]],
) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """
    Dynamically links 3-bracket `who-wins-the-senate-pending-*` (`aug=False`, excluding `pending-oil`
    already in `COND1`) with `which-party-will-win-the-senate-in-2026` across 7 exact states:
      (Cond=1, D), (Cond=1, R), (Cond=1, O_no_cond_r_d? -> Other resolves neither D nor R!),
      Wait: in a closed 3-bracket NegRisk (`Cond; R Senate`, `Cond; D Senate`, `No Cond`), if `Cond=1` and `Sen=Other`,
      let's include `(Cond=0, D)`, `(Cond=0, R)`, `(Cond=0, O)` + `(Cond=1, D)`, `(Cond=1, R)` (5 states when closed aug=False!).
    """
    if not senate_ev or senate_ev.get("closed"):
        return []
    groups: List[Tuple[str, List[Dict[str, Any]]]] = []
    # 7 zero-assumption states: (cond, sen_party, no_cond_on_other)
    states_7 = (
        (1, "R", 0),
        (1, "D", 0),
        (1, "O", 0),
        (1, "O", 1),
        (0, "R", 1),
        (0, "D", 1),
        (0, "O", 1),
    )
    for ev in conditional_events:
        slug = str(ev.get("slug") or "").lower()
        if not slug.startswith("who-wins-the-senate-pending-") or "pending-oil" in slug:
            continue
        if ev.get("closed") or not ev.get("negRisk") or ev.get("negRiskAugmented", True):
            continue
        mkts = [m for m in (ev.get("markets") or []) if not m.get("closed")]
        if len(mkts) != 3:
            continue
        m_cr, m_cd, m_no = None, None, None
        for m in mkts:
            g = str(m.get("groupItemTitle") or m.get("question") or "").lower()
            if g.startswith("no "):
                m_no = m
            elif "r senate" in g or "republican" in g:
                m_cr = m
            elif "d senate" in g or "democrat" in g:
                m_cd = m
        if not (m_cr and m_cd and m_no):
            continue
        legs: List[Dict[str, Any]] = []
        tag = slug.replace("who-wins-the-senate-pending-", "")[:22]
        _add_truth_leg(legs, m_cr, slug, f"{tag}:Y&RSen", [1.0 if (c == 1 and s == "R") else 0.0 for c, s, _ in states_7])
        _add_truth_leg(legs, m_cd, slug, f"{tag}:Y&DSen", [1.0 if (c == 1 and s == "D") else 0.0 for c, s, _ in states_7])
        _add_truth_leg(legs, m_no, slug, f"{tag}:NoCond", [float(nc) for _, _, nc in states_7])
        for sm in senate_ev.get("markets") or []:
            sg = str(sm.get("groupItemTitle") or "").strip().lower()
            if sg == "democratic party":
                _add_truth_leg(legs, sm, "sen_ctrl", "Sen:Dem", [1.0 if s == "D" else 0.0 for _, s, _ in states_7])
            elif sg == "republican party":
                _add_truth_leg(legs, sm, "sen_ctrl", "Sen:Rep", [1.0 if s == "R" else 0.0 for _, s, _ in states_7])
        if len(legs) >= 8:
            groups.append((f"COND_{tag.upper()}", legs))
    return groups


def build_lp2_tossup_state_implication_groups(
    events_by_slug: Dict[str, Dict[str, Any]],
) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """
    Zero-Assumption Per-State Implication Groups between `which-tossup-senate-states-will-republicans-win`
    and individual `0%`-fee State Senate slates (`AK, IA, KS, ME, MI, OH, TX`):
      For state `S`, defines 6 exact atomic states:
        `StateOutcome in {Named_R, Other_R, Named_D_or_OtherNonR}` x `Other6TossupsAllR in {True, False}`!
      - Any named `(R)` candidate in state `S` -> `1.0` on `(Named_R, *)`, `0.0` elsewhere (never assumes no write-in R!).
      - Any named `(D)` or `(I)` candidate in state `S` -> `0.0` on `(Named_R, *)` & `(Other_R, *)`!
        More specifically, split `NonR` into `(Named_D, *)` and `(Other_NonR, *)` -> 8 exact states!
      - `All 7` Tossup bracket -> `1.0` on `(Named_R, True)` and `(Other_R, True)`, `0.0` elsewhere!
      - `None` (`0 of 7`) Tossup bracket -> `0.0` whenever `StateOutcome in {Named_R, Other_R}`!
    """
    ev_cube = events_by_slug.get(LP2_TOSSUP_CUBE_SLUG) or {}
    if not ev_cube or ev_cube.get("closed"):
        return []
    cube_mkts = [m for m in (ev_cube.get("markets") or []) if not m.get("closed")]
    if not cube_mkts:
        return []

    m_all7 = next((m for m in cube_mkts if str(m.get("groupItemTitle") or "").strip().lower() == "all 7"), None)
    m_none = next((m for m in cube_mkts if str(m.get("groupItemTitle") or "").strip().lower() in ("none", "0", "no states")), None)
    # Also map 6-of-7 brackets excluding exactly one state `S`!
    all_codes = set(LP2_TOSSUP_STATE_SLUGS.keys())
    m_6_excl: Dict[str, Dict[str, Any]] = {}
    for m in cube_mkts:
        grp_u = str(m.get("groupItemTitle") or "").upper()
        present = {c for c in all_codes if re.search(rf"\b{c}\b", grp_u)}
        if len(present) == 6:
            missing = next(iter(all_codes - present))
            m_6_excl[missing] = m

    # 8 atomic states per state S: (s_out, other6_all_r)
    # s_out in {"NAMED_R", "OTHER_R", "NAMED_D", "OTHER_NON_R"}, other6_all_r in {True, False}
    states_8 = [
        (so, o6)
        for so in ("NAMED_R", "OTHER_R", "NAMED_D", "OTHER_NON_R")
        for o6 in (True, False)
    ]
    groups: List[Tuple[str, List[Dict[str, Any]]]] = []
    for st_code, st_slug in LP2_TOSSUP_STATE_SLUGS.items():
        ev_st = events_by_slug.get(st_slug) or {}
        if not ev_st or ev_st.get("closed"):
            continue
        legs: List[Dict[str, Any]] = []
        # Find top named (R) and top named (D) candidates (strictly skipping Person A/B placeholders)
        r_cands = []
        d_cands = []
        for m in ev_st.get("markets") or []:
            if m.get("closed"):
                continue
            grp = str(m.get("groupItemTitle") or "").strip()
            if re.search(r"^(?:person|option|candidate|party)\s+[a-z0-9]{1,2}$", grp, re.I) or "other" in grp.lower():
                continue
            if "(r)" in grp.lower() or (st_code == "AK" and "sullivan" in grp.lower()):
                r_cands.append((grp, m))
            elif "(d)" in grp.lower() or (st_code == "AK" and "peltola" in grp.lower()):
                d_cands.append((grp, m))
        if len(r_cands) == 1:
            _add_truth_leg(legs, r_cands[0][1], st_slug, f"{st_code}:{r_cands[0][0][:18]}", [1.0 if so == "NAMED_R" else 0.0 for so, _ in states_8])
        if len(d_cands) == 1:
            _add_truth_leg(legs, d_cands[0][1], st_slug, f"{st_code}:{d_cands[0][0][:18]}", [1.0 if so == "NAMED_D" else 0.0 for so, _ in states_8])
        if m_all7 is not None:
            _add_truth_leg(legs, m_all7, LP2_TOSSUP_CUBE_SLUG, "Tossups:All7", [1.0 if (so in ("NAMED_R", "OTHER_R") and o6) else 0.0 for so, o6 in states_8])
        if st_code in m_6_excl:
            _add_truth_leg(legs, m_6_excl[st_code], LP2_TOSSUP_CUBE_SLUG, f"Tossups:6Excl{st_code}", [1.0 if (so in ("NAMED_D", "OTHER_NON_R") and o6) else 0.0 for so, o6 in states_8])
        if m_none is not None:
            # `None` implies state S is Non-R AND other6 not all R (specifically 0 R; add sub-flag via <= bound? Skip None to keep 8 states exact!)
            pass
        if len(legs) >= 6:
            groups.append((f"TOSSUP_{st_code}", legs))
    return groups


def detect_lp2_seat_convert_implication_arbs(
    events_by_slug: Dict[str, Dict[str, Any]],
    books_by_token: Dict[str, Dict[str, Any]],
    target_budget_usd: float = 120.0,
    max_synthetic_box_cost_net: float = 0.992,
    min_shares: int = 6,
    rpc_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluates closed-slate `NegRiskAdapterV2.convertPositions` upper-tail `NO` conversion + `YES[Control]`:
      1. House: Buy `3 x NO` on `{220-224, 225-229, 230+}` -> convert releases `$2.00*(1-f)` USDC + `YES[<=219]`;
         pair with `YES[House:Rep]`. Pays `$1.00` everywhere and `$2.00` on `218-219` R House!
      2. Senate: Buy `7 x NO` on `{51..57+}` -> convert releases `$6.00*(1-f)` USDC + `YES[<=50]`;
         pair with `YES[Sen:Rep]`. Pays `$1.00` everywhere and `$2.00` on `50` R Senate!
    """
    arbs: List[Dict[str, Any]] = []
    configs = [
        (
            "LP2_HOUSE_CONVERT_POLISH_MIDDLE",
            "republican-house-seats-after-the-2026-midterm-elections",
            "which-party-will-win-the-house-in-2026",
            10,
            {"220-224", "225-229", "230+"},
            "House:Rep (218-219 $2x Middle)",
        ),
        (
            "LP2_SENATE_CONVERT_POLISH_MIDDLE",
            "republican-senate-seats-after-the-2026-midterm-elections-927",
            "which-party-will-win-the-senate-in-2026",
            11,
            {"51", "52", "53", "54", "55", "56", "57+"},
            "Sen:Rep (50-Seat $2x Middle)",
        ),
    ]
    for mode, seat_slug, ctrl_slug, exp_n, upper_labels, desc_lbl in configs:
        ev_s = events_by_slug.get(seat_slug) or {}
        ev_c = events_by_slug.get(ctrl_slug) or {}
        if not ev_s or not ev_c or ev_s.get("closed") or ev_c.get("closed"):
            continue
        if not ev_s.get("negRisk") or ev_s.get("negRiskAugmented", True):
            continue
        nr_id = str(ev_s.get("negRiskMarketID") or "").strip().lower()
        mkts_s = ev_s.get("markets") or []
        if len(mkts_s) != exp_n:
            continue
        ok_rpc, fee_bips, _ = verify_negrisk_adapter_slate_sync(nr_id, exp_n, rpc_url=rpc_url)
        if not ok_rpc:
            continue
        f_conv = float(fee_bips) / 10000.0

        m_rep = next(
            (m for m in (ev_c.get("markets") or []) if str(m.get("groupItemTitle") or "").strip().lower() == "republican party" and not m.get("closed")),
            None,
        )
        if m_rep is None:
            continue
        rep_toks = _parse_clob_tokens(m_rep)
        if not rep_toks:
            continue
        rep_yes_tok = rep_toks[0]
        rep_fr, rep_fe = _extract_market_fee_rate(m_rep)

        upper_no_specs = []
        for idx_m, m in enumerate(mkts_s):
            grp = str(m.get("groupItemTitle") or "").strip().lower()
            if grp in upper_labels:
                tk = _parse_clob_tokens(m)
                if not tk:
                    break
                q_id = str(m.get("questionID") or "").strip().lower()
                q_idx = int(q_id[64:], 16) if (len(q_id) == 66 and q_id.startswith("0x") and q_id[:64] == nr_id[:64]) else idx_m
                fr_m, fe_m = _extract_market_fee_rate(m)
                upper_no_specs.append((q_idx, grp, tk[1], fr_m, fe_m, str(m.get("id") or "")))
        if len(upper_no_specs) != len(upper_labels):
            continue

        m_cnt = len(upper_no_specs)
        sh_try = int(math.floor(min(80.0, target_budget_usd)))
        if sh_try < min_shares:
            continue

        # Determine max executable shares bounded by L1/walk across all upper NO legs and YES[Control]
        avail_sh = float(sh_try)
        for _, _, n_tok, _, _, _ in upper_no_specs:
            asks = (books_by_token.get(n_tok) or {}).get("asks") or []
            avail_sh = min(avail_sh, sum(float(x.get("size", 0)) for x in asks if float(x.get("price", 0)) > 0))
        rep_asks = (books_by_token.get(rep_yes_tok) or {}).get("asks") or []
        avail_sh = min(avail_sh, sum(float(x.get("size", 0)) for x in rep_asks if float(x.get("price", 0)) > 0))
        sh_exec = int(math.floor(avail_sh))
        if sh_exec < min_shares:
            continue

        sh_out_rep = sh_exec * (1.0 - f_conv)
        w_rep = _walk_side_exact_shares(rep_asks, sh_out_rep, rep_fr, rep_fe, is_ask=True)
        if w_rep is None:
            continue
        no_walks = []
        ok_w = True
        for q_idx, grp, n_tok, fr_m, fe_m, mid_m in upper_no_specs:
            wn = _walk_side_exact_shares((books_by_token.get(n_tok) or {}).get("asks") or [], float(sh_exec), fr_m, fe_m, is_ask=True)
            if wn is None:
                ok_w = False
                break
            no_walks.append((q_idx, grp, n_tok, mid_m, wn))
        if not ok_w:
            continue

        no_sum_ps = sum(w["net_per_share"] for *_, w in no_walks)
        usdc_rel_ps = float(m_cnt - 1) * (1.0 - f_conv)
        # Per-unit-of-output-bundle (size = 1 - f_conv) effective cost:
        net_bundle_cost_per_out_sh = (no_sum_ps - usdc_rel_ps) / max(1e-6, (1.0 - f_conv)) + float(w_rep["net_per_share"])
        if net_bundle_cost_per_out_sh <= max_synthetic_box_cost_net:
            bundle_legs = [
                {
                    "token_id": n_tok, "market_id": mid_m, "side": "NO",
                    "label": f"NO[{grp}]", "fee_rate": 0.0, "fee_exponent": 1.0,
                }
                for _, grp, n_tok, mid_m, _ in no_walks
            ] + [{
                "token_id": rep_yes_tok, "market_id": str(m_rep.get("id") or ""),
                "side": "YES", "label": f"YES[{desc_lbl}]",
                "fee_rate": rep_fr, "fee_exponent": rep_fe,
            }]
            arbs.append({
                "mode": mode,
                "seat_slug": seat_slug,
                "neg_risk_market_id": nr_id,
                "m_no_legs": m_cnt,
                "index_set_int": sum(1 << qi for qi, *_ in no_walks),
                "shares_in": sh_exec,
                "shares_out": round(sh_out_rep, 4),
                "synthetic_box_cost_net": round(net_bundle_cost_per_out_sh, 4),
                "guaranteed_floor_edge_ps": round(1.0 - net_bundle_cost_per_out_sh, 4),
                "l1_usd": round(min([w["l1_usd"] for *_, w in no_walks] + [w_rep["l1_usd"]]), 2),
                "close_ts": _parse_iso_ts(ev_s.get("endDate")) or 0.0,
                "legs": bundle_legs,
                "label": f"{mode}: CONV({m_cnt}xNO)+YES[{desc_lbl}] @ {net_bundle_cost_per_out_sh:.4f}",
            })
    return arbs


# ==============================================================================
# 2. SLEEVE #2: SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION (0% Fee NBA)
# ==============================================================================
@dataclass
class NbaSubperiodMarketSpec:
    event_id: str
    market_id: str
    condition_id: str
    period_scope: str     # "Q1", "Q2", "Q3", "Q4", "1H", "2H", "FG"
    kind: str             # "ML", "SPREAD", "TOTAL", "TEAM_TOTAL"
    line: Optional[float]
    team_side: Optional[str]  # canonical team for ML[0] / SPREAD fav / TEAM_TOTAL team
    tok_0: str
    tok_1: str
    out_0: str
    out_1: str
    fee_rate: float
    settle_est_ts: float
    display_title: str
    neg_risk: bool = False
    fee_exponent: float = 1.0


@dataclass
class NbaSubperiodAndExtPropSlate:
    event_id: str
    slug: str
    title: str
    tipoff_ts: float
    settle_est_ts: float
    home_team: str
    away_team: str
    ext_props_by_player_stat: Dict[Tuple[str, str], List[NbaPlayerPropRung]] = field(default_factory=dict)
    subperiod_markets: List[NbaSubperiodMarketSpec] = field(default_factory=list)


_NBA_SUBPERIOD_SMT_MAP: Dict[str, Tuple[str, str]] = {
    "first_half_moneyline": ("1H", "ML"),
    "q1_moneyline": ("Q1", "ML"),
    "first_half_spreads": ("1H", "SPREAD"),
    "q1_spreads": ("Q1", "SPREAD"),
    "q2_spreads": ("Q2", "SPREAD"),
    "q3_spreads": ("Q3", "SPREAD"),
    "first_half_totals": ("1H", "TOTAL"),
    "q1_totals": ("Q1", "TOTAL"),
    "q2_totals": ("Q2", "TOTAL"),
    "q3_totals": ("Q3", "TOTAL"),
    "q4_totals": ("Q4", "TOTAL"),
    "team_totals": ("FG", "TEAM_TOTAL"),
    "first_half_team_totals": ("1H", "TEAM_TOTAL"),
    "second_half_team_totals": ("2H", "TEAM_TOTAL"),
}


def parse_nba_subperiod_and_ext_props(ev: Dict[str, Any], now_ts: Optional[float] = None) -> Optional[NbaSubperiodAndExtPropSlate]:
    """
    Extracts `0%`-fee NBA sub-period markets (`Q1..Q4`, `1H`, `2H`, `FG Team Totals`) AND
    extended player milestone rungs (`steals`, `blocks`) currently skipped by `SP4`/`SP2`/`SP1`.
    """
    if ev.get("closed") or ev.get("archived"):
        return None
    slug = str(ev.get("slug") or "").lower()
    if not slug.startswith("nba-") or slug.endswith("-exact-margin"):
        return None
    title = str(ev.get("title") or "")
    parts = re.split(r"\s+(?:vs\.?|@)\s+", title, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None
    away_t, home_t = _canon_nba_team(parts[0]), _canon_nba_team(parts[1])
    tip_ts = _parse_iso_ts(ev.get("startTime") or ev.get("gameStartTime") or ev.get("endDate")) or 0.0
    if tip_ts <= 0.0 or (now_ts is not None and tip_ts < now_ts - 8.0 * 3600.0):
        return None
    settle_ts = tip_ts + 3.25 * 3600.0
    ev_id = str(ev.get("id") or "")

    ext_props: Dict[Tuple[str, str], List[NbaPlayerPropRung]] = {}
    sub_mkts: List[NbaSubperiodMarketSpec] = []

    for m in ev.get("markets") or []:
        if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
            continue
        fr, fe = _extract_market_fee_rate(m)
        toks = _parse_clob_tokens(m)
        outs = [str(o).strip() for o in _parse_json_list(m.get("outcomes"))]
        if not toks or len(outs) != 2:
            continue
        smt = str(m.get("sportsMarketType") or "").strip().lower()
        q_txt = str(m.get("groupItemTitle") or m.get("question") or "").strip()

        if smt in ("steals", "blocks") and [o.lower() for o in outs] == ["yes", "no"]:
            m_pr = _EXT_PROP_TITLE_RE.match(q_txt)
            raw_ln = m.get("line")
            ln = float(raw_ln) if raw_ln is not None else (float(m_pr.group(3)) if m_pr else float("nan"))
            if m_pr and _is_half_hook(ln) and ln >= 0.5:
                p_raw = m_pr.group(1).strip()
                pk = canon_player_name(p_raw)
                if pk:
                    ext_props.setdefault((pk, smt), []).append(
                        NbaPlayerPropRung(
                            event_id=ev_id, event_slug=slug, game_title=title,
                            market_id=str(m.get("id") or ""), condition_id=str(m.get("conditionId") or ""),
                            player_name=p_raw, player_key=pk, stat_type=smt, line=ln,
                            yes_token=toks[0], no_token=toks[1], fee_rate=fr,
                            tipoff_ts=tip_ts, settle_est_ts=settle_ts, home_team=home_t, away_team=away_t,
                            fee_exponent=fe,
                        )
                    )
            continue

        if smt not in _NBA_SUBPERIOD_SMT_MAP:
            continue
        p_scope, kind = _NBA_SUBPERIOD_SMT_MAP[smt]
        p_end_offset = {"Q1": 0.75, "Q2": 1.35, "1H": 1.35, "Q3": 2.15}.get(p_scope, 3.25) * 3600.0
        mkt_settle = tip_ts + p_end_offset

        if kind == "ML":
            c0, c1 = _canon_nba_team(outs[0]), _canon_nba_team(outs[1])
            if {c0, c1} != {away_t, home_t}:
                continue
            sub_mkts.append(NbaSubperiodMarketSpec(
                ev_id, str(m.get("id") or ""), str(m.get("conditionId") or ""),
                p_scope, "ML", 0.0, c0, toks[0], toks[1], outs[0], outs[1], fr, mkt_settle,
                q_txt or f"{p_scope} ML", bool(m.get("negRisk")), fe,
            ))
        elif kind == "SPREAD":
            raw_ln = m.get("line")
            if raw_ln is None:
                continue
            ln = abs(float(raw_ln))
            if not _is_half_hook(ln):
                continue
            c0, c1 = _canon_nba_team(outs[0]), _canon_nba_team(outs[1])
            if {c0, c1} != {away_t, home_t}:
                continue
            # Determine which team is `-ln` favorite from question / description!
            q_full = str(m.get("question") or q_txt)
            m_fav = _SPREAD_FAV_RE.search(q_full)
            fav_team: Optional[str] = None
            if m_fav:
                cand_f = _canon_nba_team(m_fav.group(1))
                sgn = float(m_fav.group(2))
                if cand_f in (away_t, home_t):
                    fav_team = cand_f if sgn < 0 else (home_t if cand_f == away_t else away_t)
            if fav_team is None:
                desc = str(m.get("description") or "")
                m_d = re.search(r'resolve\s+to\s+"([^"]+)"\s+if\s+.+?\s+(?:wins|outscores).+?\s+by\s+(\d+)\s+or\s+more', desc, re.I)
                if m_d:
                    cand_d = _canon_nba_team(m_d.group(1))
                    if cand_d in (away_t, home_t):
                        fav_team = cand_d
            if fav_team is None:
                continue
            # Order tok_0 = Fav (-ln), tok_1 = Dog (+ln)
            if c0 == fav_team:
                f_tok, d_tok, f_out, d_out = toks[0], toks[1], outs[0], outs[1]
            else:
                f_tok, d_tok, f_out, d_out = toks[1], toks[0], outs[1], outs[0]
            sub_mkts.append(NbaSubperiodMarketSpec(
                ev_id, str(m.get("id") or ""), str(m.get("conditionId") or ""),
                p_scope, "SPREAD", ln, fav_team, f_tok, d_tok, f_out, d_out, fr, mkt_settle,
                f"{p_scope} {f_out}(-{ln})/{d_out}(+{ln})", bool(m.get("negRisk")), fe,
            ))
        elif kind in ("TOTAL", "TEAM_TOTAL"):
            raw_ln = m.get("line")
            if raw_ln is None:
                continue
            ln = float(raw_ln)
            if ln <= 0.0 or not _is_half_hook(ln):
                continue
            if not (outs[0].lower().startswith("over") and outs[1].lower().startswith("under")):
                continue
            tm_side: Optional[str] = None
            if kind == "TEAM_TOTAL":
                q_head = (str(m.get("question") or q_txt)).split("O/U")[0]
                ca = away_t in _canon_nba_team(q_head) or _norm_team(parts[0]) in _norm_team(q_head)
                ch = home_t in _canon_nba_team(q_head) or _norm_team(parts[1]) in _norm_team(q_head)
                if ca == ch:
                    continue
                tm_side = away_t if ca else home_t
            sub_mkts.append(NbaSubperiodMarketSpec(
                ev_id, str(m.get("id") or ""), str(m.get("conditionId") or ""),
                p_scope, kind, ln, tm_side, toks[0], toks[1], "Over", "Under", fr, mkt_settle,
                q_txt or f"{p_scope} O/U {ln}", bool(m.get("negRisk")), fe,
            ))

    for k in ext_props:
        ext_props[k].sort(key=lambda r: r.line)
    if not ext_props and not sub_mkts:
        return None
    return NbaSubperiodAndExtPropSlate(
        event_id=ev_id, slug=slug, title=title, tipoff_ts=tip_ts, settle_est_ts=settle_ts,
        home_team=home_t, away_team=away_t, ext_props_by_player_stat=ext_props, subperiod_markets=sub_mkts,
    )


def detect_sp4_subperiod_and_ext_prop_boxes(
    slate: NbaSubperiodAndExtPropSlate,
    best_asks: Dict[str, float],
    max_box_cost_net: float = 0.992,
) -> List[Dict[str, Any]]:
    """
    Detects `0%`-fee:
      1. `SP4_EXT_PROP_POLISH_MIDDLE`: `Steals` & `Blocks` `YES(Over K1) + NO(Over K2)` (`K1 < K2`).
      2. `SP4_SUBPERIOD_ML_SPREAD_MIDDLE`: `1H` & `Q1` `YES(Period_ML[Fav]) + YES(Period_Spread[Dog +k.5])`
         (`$1.00` outside, `$1.50` on exact period tie, `$2.00` when Fav wins period by `1..k`!).
    """
    arbs: List[Dict[str, Any]] = []
    # 1. Steals / Blocks corridors
    for (_, stat_t), rungs in slate.ext_props_by_player_stat.items():
        for i in range(len(rungs)):
            r_lo = rungs[i]
            a_lo = best_asks.get(r_lo.yes_token)
            if a_lo is None or not (0.02 <= a_lo <= 0.98):
                continue
            for j in range(i + 1, len(rungs)):
                r_hi = rungs[j]
                if r_hi.line <= r_lo.line + 0.1:
                    continue
                a_hi = best_asks.get(r_hi.no_token)
                if a_hi is None or not (0.02 <= a_hi <= 0.98):
                    continue
                c_gross = round(float(a_lo) + float(a_hi), 4)
                c = round(
                    _net_unit_ask(float(a_lo), r_lo.fee_rate, r_lo.fee_exponent)
                    + _net_unit_ask(float(a_hi), r_hi.fee_rate, r_hi.fee_exponent),
                    4,
                )
                if c <= max_box_cost_net:
                    arbs.append({
                        "mode": "SP4_EXT_PROP_POLISH_MIDDLE",
                        "event_id": slate.event_id,
                        "slug": slate.slug,
                        "title": slate.title,
                        "box_cost_gross": c_gross,
                        "box_cost_net": c,
                        "close_ts": slate.settle_est_ts,
                        "leg_a": {
                            "token_id": r_lo.yes_token, "opp_token_id": r_lo.no_token,
                            "condition_id": r_lo.condition_id, "market_id": r_lo.market_id,
                            "side": "YES", "label": f"{r_lo.player_name} {stat_t.upper()} O{r_lo.line}",
                            "fee_rate": r_lo.fee_rate, "fee_exponent": r_lo.fee_exponent, "neg_risk": False, "strike": r_lo.line, "end_ts": r_lo.settle_est_ts,
                        },
                        "leg_b": {
                            "token_id": r_hi.no_token, "opp_token_id": r_hi.yes_token,
                            "condition_id": r_hi.condition_id, "market_id": r_hi.market_id,
                            "side": "NO", "label": f"{r_hi.player_name} {stat_t.upper()} U{r_hi.line}",
                            "fee_rate": r_hi.fee_rate, "fee_exponent": r_hi.fee_exponent, "neg_risk": False, "strike": r_hi.line, "end_ts": r_hi.settle_est_ts,
                        },
                        "label": f"{r_lo.player_name} {stat_t} O{r_lo.line} + U{r_hi.line}",
                    })

    # 2. Sub-period (1H, Q1) ML[Fav] + Spread[Dog +k.5] tie-proof Polish Middles
    for per in ("1H", "Q1"):
        mls = [m for m in slate.subperiod_markets if m.period_scope == per and m.kind == "ML"]
        sps = [m for m in slate.subperiod_markets if m.period_scope == per and m.kind == "SPREAD"]
        if not mls or not sps:
            continue
        ml_m = mls[0]
        c0 = ml_m.team_side
        c1 = slate.home_team if c0 == slate.away_team else slate.away_team
        ml_by_team = {c0: (ml_m.tok_0, ml_m.tok_1, ml_m.out_0), c1: (ml_m.tok_1, ml_m.tok_0, ml_m.out_1)}
        for sp_m in sps:
            fav_t = sp_m.team_side
            if fav_t not in ml_by_team or sp_m.line is None or sp_m.line < 0.5:
                continue
            ml_fav_tok, ml_dog_tok, fav_disp = ml_by_team[fav_t]
            dog_plus_tok, fav_minus_tok, dog_disp = sp_m.tok_1, sp_m.tok_0, sp_m.out_1
            a_ml = best_asks.get(ml_fav_tok)
            a_dog = best_asks.get(dog_plus_tok)
            if a_ml is None or a_dog is None:
                continue
            c_gross = round(float(a_ml) + float(a_dog), 4)
            c = round(
                _net_unit_ask(float(a_ml), ml_m.fee_rate, ml_m.fee_exponent)
                + _net_unit_ask(float(a_dog), sp_m.fee_rate, sp_m.fee_exponent),
                4,
            )
            if c <= max_box_cost_net:
                arbs.append({
                    "mode": f"SP4_{per}_ML_SPREAD_MIDDLE",
                    "event_id": slate.event_id,
                    "slug": slate.slug,
                    "title": slate.title,
                    "box_cost_gross": c_gross,
                    "box_cost_net": c,
                    "close_ts": sp_m.settle_est_ts,
                    "leg_a": {
                        "token_id": ml_fav_tok, "opp_token_id": ml_dog_tok,
                        "condition_id": ml_m.condition_id, "market_id": ml_m.market_id,
                        "side": "ML_FAV", "label": f"{per} ML[{fav_disp}]",
                        "fee_rate": ml_m.fee_rate, "fee_exponent": ml_m.fee_exponent, "neg_risk": bool(ml_m.neg_risk), "strike": 0.0, "end_ts": ml_m.settle_est_ts,
                    },
                    "leg_b": {
                        "token_id": dog_plus_tok, "opp_token_id": fav_minus_tok,
                        "condition_id": sp_m.condition_id, "market_id": sp_m.market_id,
                        "side": "DOG_PLUS", "label": f"{per} {dog_disp}(+{sp_m.line})",
                        "fee_rate": sp_m.fee_rate, "fee_exponent": sp_m.fee_exponent, "neg_risk": bool(sp_m.neg_risk), "strike": sp_m.line, "end_ts": sp_m.settle_est_ts,
                    },
                    "label": f"{slate.title}: {per} ML[{fav_disp}] + {dog_disp}(+{sp_m.line})",
                })

    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


def parse_espn_nba_extended_summary(summary_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts from ESPN NBA `summary?event={id}`:
      - `player_ext`: `{player_key: {"steals": int, "blocks": int}}` (active court players only)
      - `linescores`: `{"home": {1: q1, 2: q2, ...}, "away": {1: q1, 2: q2, ...}}`
      - `home_score`, `away_score`, `period`, `clock_sec`, `state`, `completed`, `is_halftime`
    """
    player_ext: Dict[str, Dict[str, int]] = {}
    for team_blk in ((summary_json or {}).get("boxscore") or {}).get("players") or []:
        for stat_blk in team_blk.get("statistics") or []:
            keys = [str(k) for k in (stat_blk.get("keys") or [])]
            idx_min = next((i for i, k in enumerate(keys) if k == "minutes"), -1)
            idx_stl = next((i for i, k in enumerate(keys) if k == "steals"), -1)
            idx_blk = next((i for i, k in enumerate(keys) if k == "blocks"), -1)
            for ath in stat_blk.get("athletes") or []:
                if ath.get("didNotPlay"):
                    continue
                pkey = canon_player_name(str((ath.get("athlete") or {}).get("displayName") or ""))
                arr = ath.get("stats") or []
                if not pkey or not arr:
                    continue
                if 0 <= idx_min < len(arr) and str(arr[idx_min]).strip() in ("", "0", "0:00", "--"):
                    continue
                rec: Dict[str, int] = {}
                try:
                    if 0 <= idx_stl < len(arr):
                        rec["steals"] = int(str(arr[idx_stl]).split("-")[0])
                    if 0 <= idx_blk < len(arr):
                        rec["blocks"] = int(str(arr[idx_blk]).split("-")[0])
                except ValueError:
                    continue
                if rec:
                    player_ext[pkey] = rec

    linescores: Dict[str, Dict[int, int]] = {"home": {}, "away": {}}
    home_sc, away_sc = 0, 0
    period, clock_sec = 0, 0.0
    state, completed, is_halftime = "pre", False, False
    comps = ((summary_json or {}).get("header") or {}).get("competitions") or []
    if comps:
        c0 = comps[0]
        st_obj = c0.get("status") or {}
        st_type = st_obj.get("type") or {}
        period = int(st_obj.get("period") or 0)
        state = str(st_type.get("state") or "pre").lower()
        completed = bool(st_type.get("completed"))
        desc_l = str(st_type.get("description") or st_type.get("name") or "").lower()
        is_halftime = "halftime" in desc_l
        disp_clk = str(st_obj.get("displayClock") or "")
        if ":" in disp_clk:
            try:
                mm, ss = disp_clk.split(":", 1)
                clock_sec = float(mm) * 60.0 + float(ss)
            except ValueError:
                clock_sec = 0.0
        for comp in c0.get("competitors") or []:
            ha = "home" if str(comp.get("homeAway") or "").lower() == "home" else "away"
            try:
                sc_i = int(float(comp.get("score") or 0))
            except (TypeError, ValueError):
                sc_i = 0
            if ha == "home":
                home_sc = sc_i
            else:
                away_sc = sc_i
            for idx_ls, ls in enumerate(comp.get("linescores") or []):
                p_num = int(ls.get("period") or (idx_ls + 1))
                val_raw = ls.get("value") if ls.get("value") is not None else ls.get("displayValue")
                try:
                    linescores[ha][p_num] = int(float(val_raw))
                except (TypeError, ValueError):
                    pass

    return {
        "player_ext": player_ext,
        "linescores": linescores,
        "home_score": home_sc,
        "away_score": away_sc,
        "period": period,
        "clock_sec": clock_sec,
        "state": state,
        "completed": completed,
        "is_halftime": is_halftime,
    }


def fetch_espn_nba_full_summary_sync(espn_game_id: str, timeout: float = 5.0) -> Tuple[Dict[str, Dict[str, int]], Dict[str, Any]]:
    """Single HTTP request returning both `(core_player_stats, extended_summary_and_linescores)`."""
    url = ESPN_NBA_SUMMARY_URL.format(game_id=espn_game_id)
    req = urllib.request.Request(url, headers={"User-Agent": "DominusSportsOracle/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    return parse_espn_nba_boxscore_players(data), parse_espn_nba_extended_summary(data)


def evaluate_sp4_subperiod_and_ext_locks(
    slate: NbaSubperiodAndExtPropSlate,
    ext_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Evaluates `100%` irreversible `0%`-fee single-leg locks on NBA sub-periods & Steals/Blocks:
      1. Completed Sub-Period Locks (`Q1`, `Q2`, `1H`, `Q3`) once subsequent period is >=120s underway,
         or game is at Halftime (for Q1/1H/Q2 with margin >= 1.5), or game is Final.
      2. In-Period Monotonic Score Clinches (`Over K.5`) with `+3 pt` Secaucus buffer (`cur >= floor(K) + 3`).
      3. Post-`Final` (`completed == True`) `Steals` & `Blocks` locks with `+2` stat-correction buffer.
    """
    state = str(ext_summary.get("state") or "pre")
    if state not in ("in", "post"):
        return []
    is_final = bool(ext_summary.get("completed") and state == "post")
    is_ht = bool(ext_summary.get("is_halftime"))
    period = int(ext_summary.get("period") or 0)
    clock_sec = float(ext_summary.get("clock_sec") or 720.0)
    ls_h = (ext_summary.get("linescores") or {}).get("home") or {}
    ls_a = (ext_summary.get("linescores") or {}).get("away") or {}
    home_tot = int(ext_summary.get("home_score") or 0)
    away_tot = int(ext_summary.get("away_score") or 0)
    locks: List[Dict[str, Any]] = []

    def _scope_scores(p_scope: str) -> Tuple[Optional[int], Optional[int], bool]:
        """Returns `(away_pts, home_pts, is_period_officially_settled)`."""
        if p_scope == "FG":
            return away_tot, home_tot, is_final
        if p_scope in ("Q1", "Q2", "Q3", "Q4"):
            q = int(p_scope[1])
            if q not in ls_a or q not in ls_h:
                return None, None, False
            settled = is_final or (q == 1 and is_ht) or (period > q and (clock_sec <= 600.0 or period >= q + 2))
            return ls_a[q], ls_h[q], settled
        if p_scope == "1H":
            if 1 not in ls_a or 1 not in ls_h:
                return None, None, False
            a1h = ls_a.get(1, 0) + ls_a.get(2, 0)
            h1h = ls_h.get(1, 0) + ls_h.get(2, 0)
            settled = is_final or (2 in ls_a and 2 in ls_h and (period >= 3 or is_ht))
            return a1h, h1h, settled
        if p_scope == "2H":
            if period < 3:
                return None, None, False
            # Sum Q3 + Q4 (+ OT if included)
            a2h = sum(v for k, v in ls_a.items() if k >= 3)
            h2h = sum(v for k, v in ls_h.items() if k >= 3)
            return a2h, h2h, is_final
        return None, None, False

    for sm in slate.subperiod_markets:
        sc_a, sc_h, is_settled = _scope_scores(sm.period_scope)
        if sc_a is None or sc_h is None:
            continue
        team_pts = {slate.away_team: sc_a, slate.home_team: sc_h}

        if sm.kind in ("TOTAL", "TEAM_TOTAL") and sm.line is not None:
            cur_pts = (sc_a + sc_h) if sm.kind == "TOTAL" else team_pts.get(sm.team_side or "", -1)
            if cur_pts < 0:
                continue
            # Settled sub-period: Over OR Under is locked (require >=1.5 pt buffer at Halftime against scorer review, >=0.5 at Final/Q+2)
            if is_settled:
                min_buf = 0.5 if (is_final or period >= (int(sm.period_scope[1]) + 2 if sm.period_scope.startswith("Q") else 4)) else 1.5
                if abs(float(cur_pts) - sm.line) >= min_buf:
                    over_won = float(cur_pts) > sm.line
                    locks.append({
                        "mode": f"SP4_{sm.period_scope}_SETTLED_TOTAL_LOCK",
                        "market_id": sm.market_id, "condition_id": sm.condition_id,
                        "token_id": sm.tok_0 if over_won else sm.tok_1,
                        "opp_token_id": sm.tok_1 if over_won else sm.tok_0,
                        "side_label": "OVER" if over_won else "UNDER",
                        "display_label": f"{sm.display_title} [{'OVER' if over_won else 'UNDER'} {cur_pts} settled]",
                        "fee_rate": sm.fee_rate, "fee_exponent": sm.fee_exponent, "neg_risk": bool(sm.neg_risk), "p_lock": 0.999, "close_ts": sm.settle_est_ts,
                    })
                continue
            # Live in-period monotonic Over clinch (+3 pt buffer survives any Secaucus 3PT review!)
            if cur_pts >= int(math.floor(sm.line)) + 3:
                locks.append({
                    "mode": f"SP4_{sm.period_scope}_LIVE_OVER_CLINCH",
                    "market_id": sm.market_id, "condition_id": sm.condition_id,
                    "token_id": sm.tok_0, "opp_token_id": sm.tok_1,
                    "side_label": "OVER",
                    "display_label": f"{sm.display_title} [Live pts={cur_pts} >= {int(math.floor(sm.line))+3}]",
                    "fee_rate": sm.fee_rate, "fee_exponent": sm.fee_exponent, "neg_risk": bool(sm.neg_risk), "p_lock": 0.998, "close_ts": sm.settle_est_ts,
                })

        elif is_settled and sm.kind == "SPREAD" and sm.line is not None and sm.team_side in team_pts:
            fav_t = sm.team_side
            dog_t = slate.home_team if fav_t == slate.away_team else slate.away_team
            margin_fav = float(team_pts[fav_t] - team_pts[dog_t])
            if abs(margin_fav - sm.line) >= (0.5 if is_final else 1.5):
                fav_cov = margin_fav > sm.line
                locks.append({
                    "mode": f"SP4_{sm.period_scope}_SETTLED_SPREAD_LOCK",
                    "market_id": sm.market_id, "condition_id": sm.condition_id,
                    "token_id": sm.tok_0 if fav_cov else sm.tok_1,
                    "opp_token_id": sm.tok_1 if fav_cov else sm.tok_0,
                    "side_label": sm.out_0 if fav_cov else sm.out_1,
                    "display_label": f"{sm.display_title} [Margin={margin_fav:+.0f} settled]",
                    "fee_rate": sm.fee_rate, "fee_exponent": sm.fee_exponent, "neg_risk": bool(sm.neg_risk), "p_lock": 0.999, "close_ts": sm.settle_est_ts,
                })

        elif is_settled and sm.kind == "ML" and sm.team_side in team_pts:
            t0 = sm.team_side
            t1 = slate.home_team if t0 == slate.away_team else slate.away_team
            diff = team_pts[t0] - team_pts[t1]
            # Strictly veto ties (`diff == 0` resolves 50-50!) and require >=2 pt margin if only Halftime
            if abs(diff) >= (1 if is_final else 2):
                t0_won = diff > 0
                locks.append({
                    "mode": f"SP4_{sm.period_scope}_SETTLED_ML_LOCK",
                    "market_id": sm.market_id, "condition_id": sm.condition_id,
                    "token_id": sm.tok_0 if t0_won else sm.tok_1,
                    "opp_token_id": sm.tok_1 if t0_won else sm.tok_0,
                    "side_label": sm.out_0 if t0_won else sm.out_1,
                    "display_label": f"{sm.display_title} [{sm.out_0 if t0_won else sm.out_1} +{abs(diff)} settled]",
                    "fee_rate": sm.fee_rate, "fee_exponent": sm.fee_exponent, "neg_risk": bool(sm.neg_risk), "p_lock": 0.999, "close_ts": sm.settle_est_ts,
                })

    # Post-Final Steals & Blocks stat locks (+2 buffer)
    if is_final:
        p_ext = ext_summary.get("player_ext") or {}
        for (pkey, stat_t), rungs in slate.ext_props_by_player_stat.items():
            cur_v = (p_ext.get(pkey) or {}).get(stat_t)
            if cur_v is None:
                continue
            for rg in rungs:
                if int(cur_v) >= int(math.floor(rg.line)) + 2:
                    locks.append({
                        "mode": "SP4_FINAL_EXT_STAT_LOCK",
                        "market_id": rg.market_id, "condition_id": rg.condition_id,
                        "token_id": rg.yes_token, "opp_token_id": rg.no_token,
                        "side_label": "YES",
                        "display_label": f"{rg.player_name} {stat_t} O{rg.line} [Final={cur_v}]",
                        "fee_rate": rg.fee_rate, "fee_exponent": rg.fee_exponent, "neg_risk": False, "p_lock": 0.998, "close_ts": rg.settle_est_ts,
                    })

    return locks


# ==============================================================================
# 3. SLEEVE #3: CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX
# ==============================================================================
@dataclass
class MonotonicRung:
    market_id: str
    condition_id: str
    label: str
    order_val: float      # Unix deadline_ts for temporal ladders; strike K for scalar ladders
    end_ts: float
    yes_token: str
    no_token: str
    fee_rate: float
    fee_exponent: float
    clause_key: str
    neg_risk: bool = False


@dataclass
class CalendarOrScalarLadderSpec:
    event_id: str
    slug: str
    title: str
    ladder_kind: str      # "SURVIVAL", "DEADLINE_BY", "SCALAR_ABOVE"
    rungs: List[MonotonicRung]


def _canon_clause_stem(desc: str, group_title: str) -> Tuple[str, str]:
    s = str(desc or "").lower().replace("“", '"').replace("”", '"').replace("’", "'")
    tz_m = _TZ_DETECT_RE.search(desc or "")
    tz_tag = (tz_m.group(1).upper().replace(" ", "_") if tz_m else "NO_TZ")
    gt = str(group_title or "").strip().lower()
    if gt and len(gt) >= 2:
        s = s.replace(gt, " <RUNG> ")
    s = _MONTH_DATE_STRIP_RE.sub(" <DATE> ", s)
    s = re.sub(r"\$\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:[kmb]|million|billion)?", " <STRIKE> ", s)
    s = re.sub(
        r"\b(greater\s+than|at\s+least|more\s+than|above|over|exceeds?)\s+[0-9][0-9,]*(?:\.[0-9]+)?\s*%?",
        r"\1 <STRIKE>",
        s,
    )
    s = re.sub(r"\s+", " ", s).strip()
    return s, tz_tag


_MONTH_MAP_CAL1: Dict[str, int] = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}


def _parse_group_label_date_ts(lbl: str, ref_end_ts: float) -> Optional[float]:
    m = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:,\s*(20\d{2}))?\b",
        str(lbl or ""),
        re.IGNORECASE,
    )
    if not m:
        return None
    mon = _MONTH_MAP_CAL1.get(m.group(1).lower())
    day = int(m.group(2))
    if not mon:
        return None
    yr = int(m.group(3)) if m.group(3) else datetime.fromtimestamp(max(1.0, ref_end_ts), tz=timezone.utc).year
    try:
        return datetime(yr, mon, day, 23, 59, 59, tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _parse_scalar_strike(lbl: str) -> Optional[float]:
    s = str(lbl or "").strip()
    if re.search(r"(?:↓|\bbelow\b|\bunder\b|\bless\s+than\b|\bat\s+most\b|\bfewer\s+than\b|\bbetween\b)", s, re.IGNORECASE):
        return None
    m = _SCALAR_MAG_RE.search(s)
    if not m:
        return None
    val = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    mult = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}.get(unit, 1.0)
    return val * mult


def parse_cal1_monotonic_ladder_event(ev: Dict[str, Any], now_ts: Optional[float] = None) -> List[CalendarOrScalarLadderSpec]:
    """
    Parses non-NegRisk multi-market events into clause-verified temporal (`SURVIVAL` or `DEADLINE_BY`)
    or non-Crypto/Pyth scalar (`SCALAR_ABOVE`) monotonicity ladders.
    """
    if ev.get("closed") or ev.get("archived") or ev.get("negRisk"):
        return []
    slug = str(ev.get("slug") or "")
    title = str(ev.get("title") or "")
    if _COVERED_CRYPTO_PYTH_SLUG_RE.search(slug) or _COVERED_CRYPTO_PYTH_SLUG_RE.search(title):
        return []
    mkts = [m for m in (ev.get("markets") or []) if not m.get("closed") and not m.get("archived") and m.get("acceptingOrders") is not False]
    if len(mkts) < 2:
        return []
    # Skip sports match events (`sportsMarketType` present)
    if any(m.get("sportsMarketType") for m in mkts):
        return []

    slug_l, title_l = slug.lower(), title.lower()
    sample_desc = str(mkts[0].get("description") or "")
    desc_l = sample_desc.lower()
    has_reset_window = bool(_RESET_WINDOW_VETO_RE.search(title_l) or _RESET_WINDOW_VETO_RE.search(slug_l.replace("-", " ")))

    ladder_kind: Optional[str] = None
    if not has_reset_window and (
        "continues-through" in slug_l or "continues through" in title_l or (
            "remains in effect" in desc_l and "through" in desc_l
        ) or ('resolve to "no" if' in desc_l.replace("“", '"').replace("”", '"') and "by the specified date" in desc_l)
    ):
        ladder_kind = "SURVIVAL"
    elif not has_reset_window and (any(k in slug_l for k in ("-by", "before-")) or any(k in title_l for k in (" by ", " before "))):
        if "resolve" in desc_l and ("by " in desc_l or "before " in desc_l or "between market creation and" in desc_l):
            ladder_kind = "DEADLINE_BY"
    elif any(
        k in title_l
        for k in ("fdv above", "total commitments", "market cap above", "box office", "revenue above", "rotten tomatoes", "tomatometer")
    ):
        ladder_kind = "SCALAR_ABOVE"

    if ladder_kind is None:
        return []

    by_clause: Dict[str, List[MonotonicRung]] = {}
    for m in mkts:
        outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
        toks = _parse_clob_tokens(m)
        if outs != ["yes", "no"] or not toks:
            continue
        desc_m = str(m.get("description") or "")
        if len(desc_m) < 60:
            continue
        grp = str(m.get("groupItemTitle") or m.get("question") or "").strip()
        stem, tz_tag = _canon_clause_stem(desc_m, grp)
        end_ts = _parse_iso_ts(m.get("endDate")) or 0.0
        if end_ts <= 0.0 or (now_ts is not None and end_ts < now_ts + 120.0):
            continue
        if ladder_kind in ("SURVIVAL", "DEADLINE_BY"):
            lbl_dt = _parse_group_label_date_ts(grp, end_ts)
            if lbl_dt is not None and abs(lbl_dt - end_ts) > 14.0 * 86400.0:
                # If label date and market endDate disagree by >14 days (e.g. shared umbrella endDate),
                # only trust label date when endDate is >= label date - 2 days!
                if end_ts < lbl_dt - 2.0 * 86400.0:
                    continue
                ord_v = lbl_dt
            else:
                ord_v = lbl_dt if lbl_dt is not None else end_ts
        else:
            desc_ml = desc_m.lower()
            if not any(w in desc_ml for w in ("above", "greater than", "exceed", "at least", "more than", "over ", "or higher")):
                continue
            if re.search(r"\b(?:less\s+than\s+\$|fewer\s+than|at\s+most)\b", desc_ml):
                continue
            st_k = _parse_scalar_strike(grp)
            if st_k is None or st_k <= 0.0:
                continue
            ord_v = st_k
        fr, fe = _extract_market_fee_rate(m)
        ck = f"{tz_tag}::{stem[:220]}"
        by_clause.setdefault(ck, []).append(MonotonicRung(
            market_id=str(m.get("id") or ""), condition_id=str(m.get("conditionId") or ""),
            label=grp[:36], order_val=ord_v, end_ts=end_ts,
            yes_token=toks[0], no_token=toks[1], fee_rate=fr, fee_exponent=fe, clause_key=ck,
            neg_risk=bool(m.get("negRisk")),
        ))

    specs: List[CalendarOrScalarLadderSpec] = []
    ev_id = str(ev.get("id") or "")
    for idx_c, (ck, rgs) in enumerate(by_clause.items()):
        rgs.sort(key=lambda r: r.order_val)
        # Deduplicate identical order_val rungs
        dedup: List[MonotonicRung] = []
        min_gap = 43200.0 if ladder_kind in ("SURVIVAL", "DEADLINE_BY") else 1e-6
        for r in rgs:
            if not dedup or (r.order_val - dedup[-1].order_val) >= min_gap:
                dedup.append(r)
        if len(dedup) >= 2:
            specs.append(CalendarOrScalarLadderSpec(
                event_id=f"{ev_id}_{idx_c}" if idx_c > 0 else ev_id,
                slug=slug, title=title, ladder_kind=ladder_kind, rungs=dedup,
            ))
    return specs


def detect_cal1_monotonic_boxes(
    spec: CalendarOrScalarLadderSpec,
    best_asks: Dict[str, float],
    max_box_cost_net: float = 0.992,
) -> List[Dict[str, Any]]:
    """
    Detects fee-exact 2-leg dominance boxes across `spec`:
      - `SURVIVAL` (`T1 < T2`): `YES(T1) + NO(T2)` (`Survive(T2) => Survive(T1)`).
      - `DEADLINE_BY` (`T1 < T2`): `NO(T1) + YES(T2)` (`By(T1) => By(T2)`).
      - `SCALAR_ABOVE` (`K1 < K2`): `YES(K1) + NO(K2)` (`Above(K2) => Above(K1)`).
    """
    arbs: List[Dict[str, Any]] = []
    rgs = spec.rungs
    for i in range(len(rgs)):
        r_lo = rgs[i]
        for j in range(i + 1, len(rgs)):
            r_hi = rgs[j]
            if spec.ladder_kind == "DEADLINE_BY":
                tok_a, opp_a, side_a, lbl_a = r_lo.no_token, r_lo.yes_token, "NO", f"NO[{r_lo.label}]"
                tok_b, opp_b, side_b, lbl_b = r_hi.yes_token, r_hi.no_token, "YES", f"YES[{r_hi.label}]"
            else:
                tok_a, opp_a, side_a, lbl_a = r_lo.yes_token, r_lo.no_token, "YES", f"YES[{r_lo.label}]"
                tok_b, opp_b, side_b, lbl_b = r_hi.no_token, r_hi.yes_token, "NO", f"NO[{r_hi.label}]"

            px_a, px_b = best_asks.get(tok_a), best_asks.get(tok_b)
            if px_a is None or px_b is None or not (0.005 <= px_a <= 0.995 and 0.005 <= px_b <= 0.995):
                continue
            c_net = round(
                _net_unit_ask(px_a, r_lo.fee_rate, r_lo.fee_exponent)
                + _net_unit_ask(px_b, r_hi.fee_rate, r_hi.fee_exponent),
                4,
            )
            if c_net <= max_box_cost_net:
                arbs.append({
                    "mode": f"CAL1_{spec.ladder_kind}_BOX",
                    "event_id": spec.event_id,
                    "slug": spec.slug,
                    "title": spec.title,
                    "ladder_kind": spec.ladder_kind,
                    "box_cost_net": c_net,
                    "close_ts": max(r_lo.end_ts, r_hi.end_ts),
                    "early_leg_close_ts": min(r_lo.end_ts, r_hi.end_ts),
                    "leg_a": {
                        "token_id": tok_a, "opp_token_id": opp_a, "condition_id": r_lo.condition_id,
                        "market_id": r_lo.market_id, "side": side_a, "label": lbl_a,
                        "fee_rate": r_lo.fee_rate, "fee_exponent": r_lo.fee_exponent,
                        "neg_risk": bool(r_lo.neg_risk), "strike": r_lo.order_val, "end_ts": r_lo.end_ts,
                    },
                    "leg_b": {
                        "token_id": tok_b, "opp_token_id": opp_b, "condition_id": r_hi.condition_id,
                        "market_id": r_hi.market_id, "side": side_b, "label": lbl_b,
                        "fee_rate": r_hi.fee_rate, "fee_exponent": r_hi.fee_exponent,
                        "neg_risk": bool(r_hi.neg_risk), "strike": r_hi.order_val, "end_ts": r_hi.end_ts,
                    },
                    "label": f"{spec.title[:40]}: {lbl_a} + {lbl_b}",
                })
    arbs.sort(key=lambda x: (float(x["box_cost_net"]), float(x["early_leg_close_ts"])))
    return arbs


# ==============================================================================
# 4. SLEEVE #4: LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX
# ==============================================================================
# 11 exhaustive NFL Exact-Margin + Canceled states:
#   0..4: Team A (Fav band structure `1-6, 7-12, 13-18, 19-24, 25+` OR `1-6, 7-13, 14-20, 21+` dynamically parsed!)
#   Wait: in NFL Exact Margin (`10` brackets: Fav has 5 bands `1-6, 7-12, 13-18, 19-24, 25+`, Tie = 0, Dog has 4 bands `1-6, 7-13, 14-20, 21+`),
#   that is 5 + 1 + 4 = 10 outcome states + 1 Canceled (50-50 across all non-NegRisk legs) = 11 states!
def build_lp1_nfl_exact_margin_bundle(ev: Dict[str, Any], now_ts: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Builds exact 11-state (`10` disjoint margin bands covering `(-inf, +inf)` + `Canceled 50-50`)
    payoff vectors for `nfl-2026` games linking `exact_margin`, `moneyline`, and boundary `spreads`.
    """
    if ev.get("closed") or ev.get("archived"):
        return None
    mkts = [m for m in (ev.get("markets") or []) if not m.get("closed") and not m.get("archived")]
    em_mkts = [m for m in mkts if str(m.get("sportsMarketType") or "").lower() == "exact_margin"]
    ml_mkt = next((m for m in mkts if str(m.get("sportsMarketType") or "").lower() == "moneyline"), None)
    if len(em_mkts) != 10 or ml_mkt is None:
        return None

    start_ts = _parse_iso_ts(ev.get("startTime") or ml_mkt.get("gameStartTime") or ev.get("endDate")) or 0.0
    end_ts = start_ts + 3.75 * 3600.0
    if now_ts is not None and end_ts < now_ts + 60.0:
        return None

    ml_toks = _parse_clob_tokens(ml_mkt)
    ml_outs = [str(o).strip() for o in _parse_json_list(ml_mkt.get("outcomes"))]
    if not ml_toks or len(ml_outs) != 2:
        return None
    ta_raw, tb_raw = ml_outs[0], ml_outs[1]
    ta_n, tb_n = _norm_team(ta_raw), _norm_team(tb_raw)

    # Parse all 10 Exact Margin brackets into canonical intervals `(winner_norm, lo_int, hi_int)`
    parsed_em: List[Tuple[str, int, int, Dict[str, Any], Tuple[str, str], float, float, str]] = []
    has_tie = False
    for m in em_mkts:
        tk = _parse_clob_tokens(m)
        outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
        if not tk or outs != ["yes", "no"]:
            return None
        fr, fe = _extract_market_fee_rate(m)
        grp = str(m.get("groupItemTitle") or m.get("question") or "").strip()
        if re.search(r"exact\s+margin:\s*tie\b", grp, re.I):
            has_tie = True
            parsed_em.append(("TIE", 0, 0, m, tk, fr, fe, "Tie"))
            continue
        mb = _NFL_EM_BAND_RE.search(grp)
        if not mb:
            return None
        tm_n = _norm_team(mb.group(1))
        lo = int(mb.group(2))
        hi = int(mb.group(3)) if mb.group(3) else 999
        w_key = "A" if (tm_n == ta_n or tm_n in ta_n or ta_n in tm_n) else ("B" if (tm_n == tb_n or tm_n in tb_n or tb_n in tm_n) else "")
        if not w_key:
            return None
        parsed_em.append((w_key, lo, hi, m, tk, fr, fe, grp.replace("Exact Margin:", "").strip()))

    if not has_tie or len(parsed_em) != 10:
        return None
    # Verify exact partition completeness on Team A (1..999) and Team B (1..999)
    for side_chk in ("A", "B"):
        ivs = sorted([(lo, hi) for wk, lo, hi, *_ in parsed_em if wk == side_chk])
        if not ivs or ivs[0][0] != 1 or ivs[-1][1] != 999:
            return None
        for idx_i in range(len(ivs) - 1):
            if ivs[idx_i][1] + 1 != ivs[idx_i + 1][0]:
                return None

    # States 0..9 = the 10 disjoint game-outcome bands; State 10 = Game Canceled (50-50 across all markets)
    n_states = 11
    legs: List[Dict[str, Any]] = []

    # 1. Moneyline legs (1.0 on win, 0.5 on Tie AND 0.5 on Canceled!)
    ml_fr, ml_fe = _extract_market_fee_rate(ml_mkt)
    ml_id, ml_cid = str(ml_mkt.get("id") or ""), str(ml_mkt.get("conditionId") or "")
    va_ml = [1.0 if wk == "A" else (0.5 if wk == "TIE" else 0.0) for wk, *_ in parsed_em] + [0.5]
    vb_ml = [1.0 if wk == "B" else (0.5 if wk == "TIE" else 0.0) for wk, *_ in parsed_em] + [0.5]
    ml_nr = bool(ml_mkt.get("negRisk"))
    legs.append({
        "market_id": ml_id, "condition_id": ml_cid, "token_id": ml_toks[0], "opp_token_id": ml_toks[1],
        "side": "ML_A", "label": f"ML[{ta_raw}]", "fee_rate": ml_fr, "fee_exponent": ml_fe,
        "neg_risk": ml_nr, "end_ts": end_ts, "payoff_vec": va_ml, "strike": 0.0,
    })
    legs.append({
        "market_id": ml_id, "condition_id": ml_cid, "token_id": ml_toks[1], "opp_token_id": ml_toks[0],
        "side": "ML_B", "label": f"ML[{tb_raw}]", "fee_rate": ml_fr, "fee_exponent": ml_fe,
        "neg_risk": ml_nr, "end_ts": end_ts, "payoff_vec": vb_ml, "strike": 0.0,
    })

    # 2. Exact Margin YES & NO legs (0.5 on State 10 Canceled!)
    for st_i, (wk, lo, hi, m_em, tk_em, fr_e, fe_e, s_lbl) in enumerate(parsed_em):
        v_y = [1.0 if s == st_i else 0.0 for s in range(10)] + [0.5]
        v_n = [1.0 - v_y[s] for s in range(10)] + [0.5]
        mid_e, cid_e = str(m_em.get("id") or ""), str(m_em.get("conditionId") or "")
        em_nr = bool(m_em.get("negRisk"))
        legs.append({
            "market_id": mid_e, "condition_id": cid_e, "token_id": tk_em[0], "opp_token_id": tk_em[1],
            "side": "YES", "label": f"EM_Y[{s_lbl}]", "fee_rate": fr_e, "fee_exponent": fe_e,
            "neg_risk": em_nr, "end_ts": end_ts, "payoff_vec": v_y, "strike": float(lo),
        })
        legs.append({
            "market_id": mid_e, "condition_id": cid_e, "token_id": tk_em[1], "opp_token_id": tk_em[0],
            "side": "NO", "label": f"EM_N[{s_lbl}]", "fee_rate": fr_e, "fee_exponent": fe_e,
            "neg_risk": em_nr, "end_ts": end_ts, "payoff_vec": v_n, "strike": float(lo),
        })

    # 3. Exact band-boundary Spreads (where every band `st_i` is 100% inside or 100% outside the spread!)
    for sm in mkts:
        if str(sm.get("sportsMarketType") or "").lower() != "spreads" or sm.get("line") is None:
            continue
        ln = abs(float(sm.get("line")))
        if not _is_half_hook(ln):
            continue
        tk_s = _parse_clob_tokens(sm)
        outs_s = [str(o).strip() for o in _parse_json_list(sm.get("outcomes"))]
        m_sp = _SPREAD_FAV_RE.search(str(sm.get("question") or sm.get("groupItemTitle") or ""))
        if not tk_s or len(outs_s) != 2 or not m_sp:
            continue
        named_n = _norm_team(m_sp.group(1))
        sgn_val = float(m_sp.group(2))
        fav_w = ("A" if named_n == ta_n else "B") if sgn_val < 0 else ("B" if named_n == ta_n else "A")
        if named_n not in (ta_n, tb_n):
            continue
        # Check that `ln` never splits any band `(fav_w, lo, hi)`: i.e., never `lo < ln < hi`!
        if any(wk == fav_w and lo < ln < hi for wk, lo, hi, *_ in parsed_em):
            continue
        o0_n = _norm_team(outs_s[0])
        fav_n = ta_n if fav_w == "A" else tb_n
        fav_tok, dog_tok = (tk_s[0], tk_s[1]) if o0_n == fav_n else (tk_s[1], tk_s[0])
        fav_disp = ta_raw if fav_w == "A" else tb_raw
        dog_disp = tb_raw if fav_w == "A" else ta_raw
        v_fav = [1.0 if (wk == fav_w and lo > ln) else 0.0 for wk, lo, hi, *_ in parsed_em] + [0.5]
        v_dog = [1.0 - v_fav[s] for s in range(10)] + [0.5]
        fr_s, fe_s = _extract_market_fee_rate(sm)
        sm_id, sm_cid = str(sm.get("id") or ""), str(sm.get("conditionId") or "")
        sm_nr = bool(sm.get("negRisk"))
        legs.append({
            "market_id": sm_id, "condition_id": sm_cid, "token_id": fav_tok, "opp_token_id": dog_tok,
            "side": "SPREAD_FAV", "label": f"{fav_disp}(-{ln})", "fee_rate": fr_s, "fee_exponent": fe_s,
            "neg_risk": sm_nr, "end_ts": end_ts, "payoff_vec": v_fav, "strike": -ln,
        })
        legs.append({
            "market_id": sm_id, "condition_id": sm_cid, "token_id": dog_tok, "opp_token_id": fav_tok,
            "side": "SPREAD_DOG", "label": f"{dog_disp}(+{ln})", "fee_rate": fr_s, "fee_exponent": fe_s,
            "neg_risk": sm_nr, "end_ts": end_ts, "payoff_vec": v_dog, "strike": ln,
        })

    return {
        "event_id": str(ev.get("id") or ""),
        "slug": str(ev.get("slug") or ""),
        "title": str(ev.get("title") or ""),
        "end_ts": end_ts,
        "legs": legs,
    }


def detect_multisport_ml_spread_polish_middles(
    ev: Dict[str, Any],
    best_asks: Dict[str, float],
    sport_hint: str = "NFL",
    max_box_cost_net: float = 0.988,
) -> List[Dict[str, Any]]:
    """
    Fee-exact tie-proof `YES(Period_ML[Team X]) + YES(Period_Spread[Opp +k.5])` ($k >= 0.5$)
    Polish Middles across NFL, CFB, and NHL (`FG`, `1H`, `Q1`), strictly skipping `0%`-fee NBA
    (already handled by `SP1` for FG and `SP4` Sleeve #2 for `1H/Q1`).
    """
    if ev.get("closed") or ev.get("archived") or ev.get("negRisk"):
        return []
    slug = str(ev.get("slug") or "").lower()
    if slug.startswith("nba-"):
        return []
    mkts = [m for m in (ev.get("markets") or []) if not m.get("closed") and not m.get("archived")]
    if len(mkts) < 2:
        return []
    start_ts = _parse_iso_ts(ev.get("startTime") or ev.get("endDate")) or 0.0
    title = str(ev.get("title") or slug)
    ev_id = str(ev.get("id") or "")

    period_pairs = (
        ("FG", "moneyline", "spreads", 3.75 * 3600.0),
        ("1H", "first_half_moneyline", "first_half_spreads", 1.75 * 3600.0),
        ("Q1", "q1_moneyline", "q1_spreads", 1.0 * 3600.0),
    )
    arbs: List[Dict[str, Any]] = []
    for p_lbl, ml_smt, sp_smt, dur_s in period_pairs:
        ml_m = next((m for m in mkts if str(m.get("sportsMarketType") or "").lower() == ml_smt), None)
        if ml_m is None:
            continue
        ml_tk = _parse_clob_tokens(ml_m)
        ml_outs = [str(o).strip() for o in _parse_json_list(ml_m.get("outcomes"))]
        if not ml_tk or len(ml_outs) != 2:
            continue
        ta_n, tb_n = _norm_team(ml_outs[0]), _norm_team(ml_outs[1])
        if ta_n in ("yes", "no", "over", "under") or ta_n == tb_n:
            continue
        ml_fr, ml_fe = _extract_market_fee_rate(ml_m)
        ml_map = {
            ta_n: (ml_tk[0], ml_tk[1], ml_outs[0]),
            tb_n: (ml_tk[1], ml_tk[0], ml_outs[1]),
        }
        close_ts = start_ts + dur_s

        for sm in mkts:
            if str(sm.get("sportsMarketType") or "").lower() != sp_smt or sm.get("line") is None:
                continue
            ln = abs(float(sm.get("line")))
            if ln < 0.5 or not _is_half_hook(ln):
                continue
            sp_tk = _parse_clob_tokens(sm)
            sp_outs = [str(o).strip() for o in _parse_json_list(sm.get("outcomes"))]
            m_sp = _SPREAD_FAV_RE.search(str(sm.get("question") or sm.get("groupItemTitle") or ""))
            if not sp_tk or len(sp_outs) != 2 or not m_sp:
                continue
            named_n = _norm_team(m_sp.group(1))
            sgn = float(m_sp.group(2))
            if named_n not in (ta_n, tb_n):
                continue
            fav_n = named_n if sgn < 0 else (tb_n if named_n == ta_n else ta_n)
            o0_n = _norm_team(sp_outs[0])
            if {o0_n, _norm_team(sp_outs[1])} != {ta_n, tb_n}:
                continue
            dog_tok = sp_tk[1] if o0_n == fav_n else sp_tk[0]
            fav_sp_tok = sp_tk[0] if o0_n == fav_n else sp_tk[1]
            dog_disp = sp_outs[1] if o0_n == fav_n else sp_outs[0]
            ml_fav_tok, ml_dog_tok, fav_disp = ml_map[fav_n]

            px_ml = best_asks.get(ml_fav_tok)
            px_dog = best_asks.get(dog_tok)
            if px_ml is None or px_dog is None:
                continue
            sp_fr, sp_fe = _extract_market_fee_rate(sm)
            c_net = round(
                _net_unit_ask(px_ml, ml_fr, ml_fe) + _net_unit_ask(px_dog, sp_fr, sp_fe),
                4,
            )
            if c_net <= max_box_cost_net:
                arbs.append({
                    "mode": f"LP1_{sport_hint}_{p_lbl}_ML_SPREAD_MIDDLE",
                    "sport": sport_hint,
                    "event_id": ev_id,
                    "slug": slug,
                    "title": title,
                    "box_cost_net": c_net,
                    "close_ts": close_ts,
                    "leg_a": {
                        "token_id": ml_fav_tok, "opp_token_id": ml_dog_tok,
                        "condition_id": str(ml_m.get("conditionId") or ""), "market_id": str(ml_m.get("id") or ""),
                        "side": "ML_FAV", "label": f"{p_lbl} ML[{fav_disp}]",
                        "fee_rate": ml_fr, "fee_exponent": ml_fe, "neg_risk": bool(ml_m.get("negRisk")), "strike": 0.0, "end_ts": close_ts,
                    },
                    "leg_b": {
                        "token_id": dog_tok, "opp_token_id": fav_sp_tok,
                        "condition_id": str(sm.get("conditionId") or ""), "market_id": str(sm.get("id") or ""),
                        "side": "DOG_PLUS", "label": f"{p_lbl} {dog_disp}(+{ln})",
                        "fee_rate": sp_fr, "fee_exponent": sp_fe, "neg_risk": bool(sm.get("negRisk")), "strike": ln, "end_ts": close_ts,
                    },
                    "label": f"{title[:38]}: {p_lbl} ML[{fav_disp}] + {dog_disp}(+{ln})",
                })
    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


# ==============================================================================
# 5. SLEEVE #5: CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH
# ==============================================================================
@dataclass
class LiveMultiSportGame:
    sport: str            # "SOCCER", "NHL", "NFL", "CFB"
    game_id: str
    start_ts: float
    state: str            # "pre", "in", "post"
    completed: bool
    is_halftime: bool
    period: int
    clock_sec: float
    home_name: str
    away_name: str
    home_score: int
    away_score: int
    linescores_home: Dict[int, int] = field(default_factory=dict)
    linescores_away: Dict[int, int] = field(default_factory=dict)


class ScoreConfirmationTracker:
    """
    Stateful anti-VAR / anti-coach's-challenge confirmation timer:
    Records the earliest timestamp `ts` at which `(sport, game_id, metric_key)` held `>= val`
    WITHOUT dropping below `val`. If ESPN temporarily increments and then VAR/review reverts
    the score on a subsequent poll, all higher thresholds `> new_val` are immediately purged!
    """

    def __init__(self) -> None:
        self._first_seen: Dict[Tuple[str, str, str, int], float] = {}

    def observe_and_confirmed_floor(
        self,
        sport: str,
        game_id: str,
        metric_key: str,
        current_val: int,
        now_ts: float,
        min_confirm_sec: float,
        is_final: bool = False,
    ) -> int:
        if current_val <= 0:
            self._purge_above(sport, game_id, metric_key, 0)
            return 0
        self._purge_above(sport, game_id, metric_id=metric_key, max_keep=current_val)
        for v in range(1, min(current_val, 120) + 1):
            k = (sport, game_id, metric_key, v)
            if k not in self._first_seen:
                self._first_seen[k] = now_ts
        if is_final:
            return current_val
        confirmed = 0
        for v in range(1, min(current_val, 120) + 1):
            t0 = self._first_seen.get((sport, game_id, metric_key, v), now_ts)
            if (now_ts - t0) >= min_confirm_sec:
                confirmed = v
        return confirmed

    def _purge_above(self, sport: str, game_id: str, metric_id: str = "", max_keep: int = 0) -> None:
        dead = [k for k in self._first_seen if k[0] == sport and k[1] == game_id and k[2] == metric_id and k[3] > max_keep]
        for k in dead:
            del self._first_seen[k]

    def prune(self, now_ts: float, max_age_sec: float = 21600.0) -> int:
        cutoff = float(now_ts) - float(max_age_sec)
        dead = [k for k, t0 in self._first_seen.items() if t0 < cutoff]
        for k in dead:
            del self._first_seen[k]
        return len(dead)


def parse_espn_multisport_scoreboard(sport: str, sb_json: Dict[str, Any]) -> List[LiveMultiSportGame]:
    games: List[LiveMultiSportGame] = []
    for ev in (sb_json or {}).get("events") or []:
        comps = ev.get("competitions") or []
        if not comps:
            continue
        c0 = comps[0]
        st = c0.get("status") or {}
        st_t = st.get("type") or {}
        state = str(st_t.get("state") or "pre").lower()
        if state not in ("in", "post"):
            continue
        completed = bool(st_t.get("completed"))
        desc_l = str(st_t.get("description") or st_t.get("name") or "").lower()
        is_ht = "halftime" in desc_l
        period = int(st.get("period") or 0)
        clock_sec = float(st.get("clock") or 0.0)
        start_ts = _parse_iso_ts(c0.get("date") or ev.get("date")) or 0.0

        h_name, a_name = "", ""
        h_sc, a_sc = 0, 0
        ls_h: Dict[int, int] = {}
        ls_a: Dict[int, int] = {}
        for tm in c0.get("competitors") or []:
            ha = str(tm.get("homeAway") or "").lower()
            nm = str((tm.get("team") or {}).get("displayName") or (tm.get("team") or {}).get("shortDisplayName") or "")
            try:
                sc = int(float(tm.get("score") or 0))
            except (TypeError, ValueError):
                sc = 0
            ls_map: Dict[int, int] = {}
            for idx_l, ls in enumerate(tm.get("linescores") or []):
                p_n = int(ls.get("period") or (idx_l + 1))
                v_r = ls.get("value") if ls.get("value") is not None else ls.get("displayValue")
                try:
                    ls_map[p_n] = int(float(v_r))
                except (TypeError, ValueError):
                    pass
            if ha == "home":
                h_name, h_sc, ls_h = nm, sc, ls_map
            else:
                a_name, a_sc, ls_a = nm, sc, ls_map
        if h_name and a_name:
            games.append(LiveMultiSportGame(
                sport=sport, game_id=str(ev.get("id") or ""), start_ts=start_ts,
                state=state, completed=completed, is_halftime=is_ht, period=period, clock_sec=clock_sec,
                home_name=h_name, away_name=a_name, home_score=h_sc, away_score=a_sc,
                linescores_home=ls_h, linescores_away=ls_a,
            ))
    return games


def fetch_espn_multisport_board_sync(sport: str, timeout: float = 5.0) -> List[LiveMultiSportGame]:
    urls = ESPN_SCOREBOARD_URLS.get(sport.upper()) or ()
    by_id: Dict[str, LiveMultiSportGame] = {}
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "DominusSportsOracle/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
            for g in parse_espn_multisport_scoreboard(sport.upper(), data):
                by_id[g.game_id] = g
        except Exception:
            continue
    return list(by_id.values())


_GENERIC_CLUB_SUFFIX_TOKS = frozenset({"fc", "sc", "cf", "ac", "afc", "club", "de", "cd", "ud", "fk", "sk", "sv", "bv"})
_DERBY_DISAMBIG_TOKS = frozenset({"city", "united", "utd", "real", "atletico", "inter", "ac", "sporting", "dynamo", "lokomotiv", "rangers", "celtic"})


def _teams_match_fuzzy(pm_team: str, espn_team: str) -> bool:
    p = _norm_team(pm_team)
    e = _norm_team(espn_team)
    if not p or not e:
        return False
    if p == e:
        return True
    p_all = p.split()
    e_all = e.split()
    p_core = [t for t in p_all if t not in _GENERIC_CLUB_SUFFIX_TOKS]
    e_core = [t for t in e_all if t not in _GENERIC_CLUB_SUFFIX_TOKS]
    if not p_core or not e_core:
        return False
    # Intra-city derby guard: if BOTH sides carry distinct derby disambiguators (e.g. Man City vs Man United,
    # Real Madrid vs Atletico Madrid, Inter Milan vs AC Milan), never equate them!
    p_derby = set(p_all) & _DERBY_DISAMBIG_TOKS
    e_derby = set(e_all) & _DERBY_DISAMBIG_TOKS
    if p_derby and e_derby and p_derby.isdisjoint(e_derby):
        return False
    if p_core == e_core:
        return True
    # Whole-token subset match (never character-substring like "inter" inside "internacional"):
    if set(p_core).issubset(set(e_core)) and sum(len(t) for t in p_core) >= 4:
        # Reject single-city-token match when the fuller name has a derby disambiguator (e.g. "Madrid" vs "Atletico Madrid")
        if len(p_core) == 1 and e_derby and not p_derby:
            return False
        return True
    if set(e_core).issubset(set(p_core)) and sum(len(t) for t in e_core) >= 4:
        if len(e_core) == 1 and p_derby and not e_derby:
            return False
        return True
    if p_core[-1] == e_core[-1] and len(p_core[-1]) >= 4 and p_core[-1] not in _DERBY_DISAMBIG_TOKS:
        # Same trailing mascot/surname (e.g. "Boston Celtics" vs "Celtics"), provided leading city tokens don't conflict
        if not (len(p_core) >= 2 and len(e_core) >= 2 and p_core[0] != e_core[0]):
            return True
    return False


def evaluate_cl1_soccer_tree_clinch_locks(
    soccer_tree: Any,
    live_soccer_board: List[LiveMultiSportGame],
    tracker: ScoreConfirmationTracker,
    now_ts: float,
    var_confirm_sec: float = 210.0,
) -> List[Dict[str, Any]]:
    """
    Evaluates post-VAR (`>= 210s` confirmed or `Final`regulation) Soccer `Over K.5` goal locks
    on `SOC1` `-more-markets` regulation totals (`0.5, 1.5, 2.5, 3.5, 4.5`).
    """
    matched_g: Optional[LiveMultiSportGame] = None
    sh_name = str(getattr(soccer_tree, "home_team", None) or getattr(soccer_tree, "home_name", "") or "")
    sa_name = str(getattr(soccer_tree, "away_team", None) or getattr(soccer_tree, "away_name", "") or "")
    for g in live_soccer_board:
        if abs(g.start_ts - float(soccer_tree.end_ts - 2.25 * 3600.0)) > 8.0 * 3600.0:
            continue
        h_ok = _teams_match_fuzzy(sh_name, g.home_name) and _teams_match_fuzzy(sa_name, g.away_name)
        r_ok = _teams_match_fuzzy(sh_name, g.away_name) and _teams_match_fuzzy(sa_name, g.home_name)
        if h_ok and r_ok:
            continue
        if h_ok or r_ok:
            matched_g = g
            break
    if matched_g is None:
        return []
    # In knockout competitions, extra time is period > 2; regulation totals only count 90m (periods 1 & 2)!
    # Strictly veto if period > 2 unless linescores[1] + linescores[2] are explicitly present!
    if matched_g.period > 2:
        if 1 in matched_g.linescores_home and 2 in matched_g.linescores_home and 1 in matched_g.linescores_away and 2 in matched_g.linescores_away:
            tot_reg = matched_g.linescores_home[1] + matched_g.linescores_home[2] + matched_g.linescores_away[1] + matched_g.linescores_away[2]
        else:
            return []
        is_reg_final = True
    else:
        tot_reg = matched_g.home_score + matched_g.away_score
        is_reg_final = bool(matched_g.completed and matched_g.state == "post")

    conf_goals = tracker.observe_and_confirmed_floor(
        "SOCCER", matched_g.game_id, "REG_GOALS", tot_reg, now_ts, var_confirm_sec, is_final=is_reg_final
    )
    if conf_goals <= 0:
        return []
    locks: List[Dict[str, Any]] = []
    for tl in soccer_tree.totals:
        ln = float(tl["line"])
        if conf_goals >= int(math.floor(ln)) + 1:
            locks.append({
                "mode": "CL1_SOCCER_POST_VAR_OVER_LOCK",
                "sport": "SOCCER",
                "market_id": str(tl["market_id"]),
                "condition_id": str(tl["condition_id"]),
                "token_id": str(tl["over_token"]),
                "opp_token_id": str(tl["under_token"]),
                "fee_rate": float(tl["fee_rate"]),
                "fee_exponent": float(tl.get("fee_exponent", tl.get("fee_exp", 1.0))),
                "neg_risk": bool(tl.get("neg_risk", False)),
                "side_label": "OVER",
                "display_label": f"{soccer_tree.title[:40]} Over {ln} [Goals={conf_goals} post-VAR]",
                "p_lock": 0.998,
                "close_ts": float(soccer_tree.end_ts),
            })
    return locks


def evaluate_cl1_multisport_corridor_clinch_locks(
    ms_spec: Any,
    live_boards: Dict[str, List[LiveMultiSportGame]],
    tracker: ScoreConfirmationTracker,
    now_ts: float,
) -> List[Dict[str, Any]]:
    """
    Evaluates post-review monotonic `Over K.5` & completed-period locks across `NHL`, `NFL`, and `CFB`
    using already-discovered `MultiSportCorridorSpec` games (`SP3` universe, skipping NBA).
    """
    sp = str(ms_spec.sport or "").upper()
    if sp not in ("NHL", "NFL", "CFB"):
        return []
    board = live_boards.get(sp) or []
    matched: Optional[LiveMultiSportGame] = None
    swapped = False
    best_dt_cl = float("inf")
    max_dt_cl = 10800.0 if float(ms_spec.start_ts or 0.0) > 0.0 else (8.0 * 3600.0)
    for g in board:
        dt_g = abs(float(g.start_ts) - float(ms_spec.start_ts)) if (g.start_ts > 0.0 and float(ms_spec.start_ts or 0.0) > 0.0) else 0.0
        if g.start_ts > 0.0 and float(ms_spec.start_ts or 0.0) > 0.0 and dt_g > max_dt_cl:
            continue
        if _teams_match_fuzzy(ms_spec.team_a, g.away_name) and _teams_match_fuzzy(ms_spec.team_b, g.home_name):
            if dt_g < best_dt_cl:
                matched, swapped, best_dt_cl = g, False, dt_g
        elif _teams_match_fuzzy(ms_spec.team_a, g.home_name) and _teams_match_fuzzy(ms_spec.team_b, g.away_name):
            if dt_g < best_dt_cl:
                matched, swapped, best_dt_cl = g, True, dt_g
    if matched is None:
        return []

    is_final = bool(matched.completed and matched.state == "post")
    sc_a = matched.home_score if swapped else matched.away_score
    sc_b = matched.away_score if swapped else matched.home_score
    ls_a = matched.linescores_home if swapped else matched.linescores_away
    ls_b = matched.linescores_away if swapped else matched.linescores_home
    locks: List[Dict[str, Any]] = []

    if sp == "NHL":
        conf_tot = tracker.observe_and_confirmed_floor(
            "NHL", matched.game_id, "TOT_GOALS", sc_a + sc_b, now_ts, min_confirm_sec=150.0, is_final=is_final
        )
        for lg in (ms_spec.legs_by_scope.get("FG:TOTAL") or []):
            if lg.relation == "OVER" and conf_tot >= int(math.floor(lg.threshold)) + 1:
                locks.append({
                    "mode": "CL1_NHL_POST_CHALLENGE_OVER_LOCK",
                    "sport": "NHL",
                    "market_id": lg.market_id, "condition_id": lg.condition_id,
                    "token_id": lg.token_id, "opp_token_id": lg.opp_token_id,
                    "fee_rate": lg.fee_rate, "fee_exponent": lg.fee_exponent,
                    "neg_risk": bool(getattr(lg, "neg_risk", False)),
                    "side_label": lg.side_label,
                    "display_label": f"{ms_spec.title[:38]} {lg.display_label} [Goals={conf_tot}]",
                    "p_lock": 0.998, "close_ts": float(ms_spec.settle_est_ts),
                })
        return locks

    # NFL & CFB:
    # 1) Full-game Over K.5 with +9 pt one-possession replay buffer in-play (or +1 when Final!)
    fg_buf = 1 if is_final else 9
    for lg in (ms_spec.legs_by_scope.get("FG:TOTAL") or []):
        if lg.relation == "OVER" and (sc_a + sc_b) >= int(math.floor(lg.threshold)) + fg_buf:
            locks.append({
                "mode": f"CL1_{sp}_SCORE_OVER_LOCK",
                "sport": sp,
                "market_id": lg.market_id, "condition_id": lg.condition_id,
                "token_id": lg.token_id, "opp_token_id": lg.opp_token_id,
                "fee_rate": lg.fee_rate, "fee_exponent": lg.fee_exponent,
                "neg_risk": bool(getattr(lg, "neg_risk", False)),
                "side_label": lg.side_label,
                "display_label": f"{ms_spec.title[:36]} {lg.display_label} [Score={sc_a}-{sc_b}]",
                "p_lock": 0.999 if is_final else 0.997, "close_ts": float(ms_spec.settle_est_ts),
            })

    # 2) Completed Sub-Period (`Q1`, `Q2`, `1H`, `Q3`) Spread & Total Locks!
    for sc_key, legs in ms_spec.legs_by_scope.items():
        per = sc_key.split(":")[0]
        pa, pb, settled = None, None, False
        if per in ("Q1", "Q2", "Q3"):
            q = int(per[1])
            if q in ls_a and q in ls_b:
                pa, pb = ls_a[q], ls_b[q]
                settled = is_final or (q == 1 and matched.is_halftime) or (matched.period > q and (matched.clock_sec <= 780.0 or matched.period >= q + 2))
        elif per == "1H":
            if 1 in ls_a and 1 in ls_b and 2 in ls_a and 2 in ls_b:
                pa, pb = ls_a[1] + ls_a[2], ls_b[1] + ls_b[2]
                settled = is_final or matched.is_halftime or matched.period >= 3
        if not settled or pa is None or pb is None:
            continue
        if sc_key.endswith(":TOTAL"):
            tot_p = float(pa + pb)
            for lg in legs:
                won = (tot_p > lg.threshold) if lg.relation == "OVER" else (tot_p < lg.threshold)
                if won and abs(tot_p - lg.threshold) >= 0.5:
                    locks.append({
                        "mode": f"CL1_{sp}_{per}_SETTLED_TOTAL_LOCK",
                        "sport": sp,
                        "market_id": lg.market_id, "condition_id": lg.condition_id,
                        "token_id": lg.token_id, "opp_token_id": lg.opp_token_id,
                        "fee_rate": lg.fee_rate, "fee_exponent": lg.fee_exponent,
                        "neg_risk": bool(getattr(lg, "neg_risk", False)),
                        "side_label": lg.side_label,
                        "display_label": f"{ms_spec.title[:34]} {lg.display_label} [{per}={int(tot_p)} settled]",
                        "p_lock": 0.999, "close_ts": float(ms_spec.settle_est_ts),
                    })
        elif sc_key.endswith(":SPREAD"):
            margin_a = float(pa - pb)
            for lg in legs:
                won = (margin_a > lg.threshold) if lg.relation == "GT" else (margin_a < lg.threshold)
                if won and abs(margin_a - lg.threshold) >= 0.5:
                    locks.append({
                        "mode": f"CL1_{sp}_{per}_SETTLED_SPREAD_LOCK",
                        "sport": sp,
                        "market_id": lg.market_id, "condition_id": lg.condition_id,
                        "token_id": lg.token_id, "opp_token_id": lg.opp_token_id,
                        "fee_rate": lg.fee_rate, "fee_exponent": lg.fee_exponent,
                        "neg_risk": bool(getattr(lg, "neg_risk", False)),
                        "side_label": lg.side_label,
                        "display_label": f"{ms_spec.title[:34]} {lg.display_label} [{per} M={margin_a:+.0f}]",
                        "p_lock": 0.999, "close_ts": float(ms_spec.settle_est_ts),
                    })
    return locks


# ==============================================================================
# 6. SLEEVE #6: TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR (ATP / WTA BO3)
# ==============================================================================
@dataclass
class TennisTotalRung:
    market_id: str
    condition_id: str
    scope: str            # "SET1_GAMES", "SET2_GAMES", "MATCH_GAMES"
    line: float
    over_token: str
    under_token: str
    fee_rate: float
    fee_exp: float
    neg_risk: bool = False


@dataclass
class TennisMatchSpec:
    event_id: str
    slug: str
    title: str
    player_a: str
    player_b: str
    end_ts: float
    totals_by_scope: Dict[str, List[TennisTotalRung]] = field(default_factory=dict)
    set1_a_token: Optional[str] = None
    set1_b_token: Optional[str] = None
    set1_resolved_winner: Optional[str] = None
    set2_a_token: Optional[str] = None
    set2_b_token: Optional[str] = None
    set2_resolved_winner: Optional[str] = None
    sets_ou25_over_token: Optional[str] = None
    sets_ou25_under_token: Optional[str] = None
    sets_ou25_market_id: str = ""
    sets_ou25_condition_id: str = ""
    sets_ou25_fee_rate: float = 0.05
    sets_ou25_fee_exp: float = 1.0
    sets_ou25_neg_risk: bool = False
    comp_yes_token: Optional[str] = None
    comp_no_token: Optional[str] = None
    comp_market_id: str = ""
    comp_condition_id: str = ""
    comp_fee_rate: float = 0.05
    comp_fee_exp: float = 1.0
    comp_neg_risk: bool = False


def parse_tennis_retirement_safe_event(ev: Dict[str, Any], now_ts: Optional[float] = None) -> Optional[TennisMatchSpec]:
    """
    Parses Best-of-3 ATP/WTA events into retirement-immune (`>= $1.00` floor on all injury retirements)
    game-corridor rungs (`Set 1`, `Set 2`, `Match`) plus `1-1` Split `Over 2.5 Sets + NO[Completed Match]`.
    Strictly vetoes BO5 Grand Slam Men's matches (`Set 4/5` or `O/U 3.5/4.5 Sets`).
    """
    if ev.get("closed") or ev.get("archived") or ev.get("negRisk"):
        return None
    slug = str(ev.get("slug") or "").lower()
    mkts = ev.get("markets") or []
    if not (slug.startswith(("atp-", "wta-")) or any(str(m.get("sportsMarketType") or "").startswith("tennis_") for m in mkts)):
        return None
    # Strictly veto BO5 matches
    for m in mkts:
        q_chk = str(m.get("groupItemTitle") or m.get("question") or "").lower()
        if re.search(r"\bset\s+[45]\b", q_chk):
            return None
        if str(m.get("sportsMarketType") or "").lower() == "tennis_set_totals" and m.get("line") is not None and float(m.get("line")) > 3.0:
            return None

    ml_m = next((m for m in mkts if str(m.get("sportsMarketType") or "").lower() == "moneyline"), None)
    if ml_m is None:
        return None
    ml_outs = [str(o).strip() for o in _parse_json_list(ml_m.get("outcomes"))]
    if len(ml_outs) != 2:
        return None
    pa, pb = ml_outs[0], ml_outs[1]
    pa_n, pb_n = _norm_team(pa), _norm_team(pb)
    end_ts = (_parse_iso_ts(ev.get("startTime") or ml_m.get("gameStartTime") or ev.get("endDate")) or 0.0) + 3.25 * 3600.0
    if now_ts is not None and end_ts < now_ts + 60.0:
        return None

    spec = TennisMatchSpec(
        event_id=str(ev.get("id") or ""), slug=slug, title=str(ev.get("title") or slug),
        player_a=pa, player_b=pb, end_ts=end_ts,
    )

    def _parse_set_winner(cm: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        tk = _parse_clob_tokens(cm)
        couts = [_norm_team(str(x)) for x in _parse_json_list(cm.get("outcomes"))]
        cprices = _parse_json_list(cm.get("outcomePrices"))
        ta, tb = None, None
        if tk and len(couts) == 2 and {couts[0], couts[1]} == {pa_n, pb_n}:
            ta, tb = (tk[0], tk[1]) if couts[0] == pa_n else (tk[1], tk[0])
        rw: Optional[str] = None
        if len(cprices) == 2 and len(couts) == 2:
            try:
                p0, p1 = float(cprices[0]), float(cprices[1])
                if cm.get("closed") or (max(p0, p1) >= 0.995 and min(p0, p1) <= 0.005):
                    if p0 >= 0.995 and p1 <= 0.005:
                        rw = "A" if couts[0] == pa_n else "B"
                    elif p1 >= 0.995 and p0 <= 0.005:
                        rw = "A" if couts[1] == pa_n else "B"
            except (TypeError, ValueError):
                pass
        return ta, tb, rw

    for m in mkts:
        smt = str(m.get("sportsMarketType") or "").strip().lower()
        grp = str(m.get("groupItemTitle") or m.get("question") or "")
        if smt == "tennis_first_set_winner":
            spec.set1_a_token, spec.set1_b_token, spec.set1_resolved_winner = _parse_set_winner(m)
            continue
        if smt == "tennis_set_winner" and (str(m.get("line") or "") == "2" or "set 2" in grp.lower()):
            spec.set2_a_token, spec.set2_b_token, spec.set2_resolved_winner = _parse_set_winner(m)
            continue
        if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
            continue
        tk = _parse_clob_tokens(m)
        outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
        if not tk or len(outs) != 2:
            continue
        fr, fe = _extract_market_fee_rate(m)

        if smt == "tennis_completed_match" and outs == ["yes", "no"]:
            spec.comp_yes_token, spec.comp_no_token = tk[0], tk[1]
            spec.comp_market_id = str(m.get("id") or "")
            spec.comp_condition_id = str(m.get("conditionId") or "")
            spec.comp_fee_rate, spec.comp_fee_exp = fr, fe
            spec.comp_neg_risk = bool(m.get("negRisk"))
        elif smt == "tennis_set_totals" and m.get("line") is not None and abs(float(m.get("line")) - 2.5) < 1e-6:
            if outs[0].startswith("over") and outs[1].startswith("under"):
                spec.sets_ou25_over_token, spec.sets_ou25_under_token = tk[0], tk[1]
                spec.sets_ou25_market_id = str(m.get("id") or "")
                spec.sets_ou25_condition_id = str(m.get("conditionId") or "")
                spec.sets_ou25_fee_rate, spec.sets_ou25_fee_exp = fr, fe
                spec.sets_ou25_neg_risk = bool(m.get("negRisk"))
        elif smt in ("tennis_first_set_totals", "tennis_set_games_totals", "tennis_match_totals") and m.get("line") is not None:
            ln = float(m.get("line"))
            if not _is_half_hook(ln) or not (outs[0].startswith("over") and outs[1].startswith("under")):
                continue
            if smt == "tennis_first_set_totals":
                sc = "SET1_GAMES"
            elif smt == "tennis_match_totals":
                sc = "MATCH_GAMES"
            elif "set 2" in grp.lower():
                sc = "SET2_GAMES"
            elif "set 3" in grp.lower():
                sc = "SET3_GAMES"
            else:
                continue
            spec.totals_by_scope.setdefault(sc, []).append(TennisTotalRung(
                market_id=str(m.get("id") or ""), condition_id=str(m.get("conditionId") or ""),
                scope=sc, line=ln, over_token=tk[0], under_token=tk[1], fee_rate=fr, fee_exp=fe,
                neg_risk=bool(m.get("negRisk")),
            ))

    for k in spec.totals_by_scope:
        spec.totals_by_scope[k].sort(key=lambda r: r.line)
    has_corridor = any(len(v) >= 2 for v in spec.totals_by_scope.values())
    has_1_1_hedge = bool(spec.sets_ou25_over_token and spec.comp_no_token)
    if not (has_corridor or has_1_1_hedge):
        return None
    return spec


def evaluate_ten1_tennis_opportunities(
    spec: TennisMatchSpec,
    books_by_token: Dict[str, Dict[str, Any]],
    best_asks: Dict[str, float],
    max_box_cost_net: float = 0.988,
) -> List[Dict[str, Any]]:
    """
    Evaluates retirement-safe (`min_omega V_T(omega) >= $1.00`) 2-leg boxes on ATP/WTA BO3:
      1. `TEN1_GAMES_CORRIDOR`: `YES(Over K_low) + NO(Over K_high)` within identical set/match scope.
      2. `TEN1_1_1_RETIREMENT_HEDGED_BOX`: After Set 1 Winner != Set 2 Winner (`1-1` split),
         `YES[Total Sets Over 2.5] + NO[Completed Match]` (`$1.00` on normal Set 3 finish, `$1.50` on Set 3 retirement!).
    """
    boxes: List[Dict[str, Any]] = []
    for scope, rungs in spec.totals_by_scope.items():
        for i in range(len(rungs)):
            r_lo = rungs[i]
            px_lo = best_asks.get(r_lo.over_token)
            if px_lo is None or not (0.01 <= px_lo <= 0.99):
                continue
            for j in range(i + 1, len(rungs)):
                r_hi = rungs[j]
                if r_hi.line <= r_lo.line + 0.1:
                    continue
                px_hi = best_asks.get(r_hi.under_token)
                if px_hi is None or not (0.01 <= px_hi <= 0.99):
                    continue
                c_net = round(
                    _net_unit_ask(px_lo, r_lo.fee_rate, r_lo.fee_exp)
                    + _net_unit_ask(px_hi, r_hi.fee_rate, r_hi.fee_exp),
                    4,
                )
                if c_net <= max_box_cost_net:
                    boxes.append({
                        "mode": f"TEN1_{scope}_CORRIDOR",
                        "event_id": spec.event_id,
                        "slug": spec.slug,
                        "title": spec.title,
                        "box_cost_net": c_net,
                        "close_ts": spec.end_ts,
                        "leg_a": {
                            "token_id": r_lo.over_token, "opp_token_id": r_lo.under_token,
                            "condition_id": r_lo.condition_id, "market_id": r_lo.market_id,
                            "side": "OVER", "label": f"{scope} O{r_lo.line}",
                            "fee_rate": r_lo.fee_rate, "fee_exponent": r_lo.fee_exp,
                            "neg_risk": bool(r_lo.neg_risk), "strike": r_lo.line, "end_ts": spec.end_ts,
                        },
                        "leg_b": {
                            "token_id": r_hi.under_token, "opp_token_id": r_hi.over_token,
                            "condition_id": r_hi.condition_id, "market_id": r_hi.market_id,
                            "side": "UNDER", "label": f"{scope} U{r_hi.line}",
                            "fee_rate": r_hi.fee_rate, "fee_exponent": r_hi.fee_exp,
                            "neg_risk": bool(r_hi.neg_risk), "strike": r_hi.line, "end_ts": spec.end_ts,
                        },
                        "label": f"{spec.title[:36]}: {scope} O{r_lo.line} + U{r_hi.line}",
                    })

    # Post 1-1 Split Retirement-Hedged Set-3 Box
    s1_w = _infer_live_map_winner(spec.set1_resolved_winner, spec.set1_a_token, spec.set1_b_token, books_by_token)
    s2_w = _infer_live_map_winner(spec.set2_resolved_winner, spec.set2_a_token, spec.set2_b_token, books_by_token)
    if s1_w in ("A", "B") and s2_w in ("A", "B") and s1_w != s2_w and spec.sets_ou25_over_token and spec.comp_no_token:
        px_o25 = best_asks.get(spec.sets_ou25_over_token)
        px_nc = best_asks.get(spec.comp_no_token)
        if px_o25 is not None and px_nc is not None:
            c_11 = round(
                _net_unit_ask(px_o25, spec.sets_ou25_fee_rate, spec.sets_ou25_fee_exp)
                + _net_unit_ask(px_nc, spec.comp_fee_rate, spec.comp_fee_exp),
                4,
            )
            if c_11 <= max_box_cost_net:
                boxes.append({
                    "mode": "TEN1_1_1_RETIREMENT_HEDGED_BOX",
                    "event_id": spec.event_id,
                    "slug": spec.slug,
                    "title": spec.title,
                    "box_cost_net": c_11,
                    "close_ts": spec.end_ts,
                    "leg_a": {
                        "token_id": spec.sets_ou25_over_token, "opp_token_id": spec.sets_ou25_under_token or "",
                        "condition_id": spec.sets_ou25_condition_id, "market_id": spec.sets_ou25_market_id,
                        "side": "OVER_2.5", "label": "Sets O2.5 [1-1]",
                        "fee_rate": spec.sets_ou25_fee_rate, "fee_exponent": spec.sets_ou25_fee_exp,
                        "neg_risk": bool(spec.sets_ou25_neg_risk), "strike": 2.5, "end_ts": spec.end_ts,
                    },
                    "leg_b": {
                        "token_id": spec.comp_no_token, "opp_token_id": spec.comp_yes_token or "",
                        "condition_id": spec.comp_condition_id, "market_id": spec.comp_market_id,
                        "side": "NO_COMP", "label": "NO[Completed Match]",
                        "fee_rate": spec.comp_fee_rate, "fee_exponent": spec.comp_fee_exp,
                        "neg_risk": bool(spec.comp_neg_risk), "strike": 0.0, "end_ts": spec.end_ts,
                    },
                    "label": f"{spec.title[:36]}: Sets O2.5 + NO[Completed] [1-1 Split]",
                })

    boxes.sort(key=lambda x: float(x["box_cost_net"]))
    return boxes

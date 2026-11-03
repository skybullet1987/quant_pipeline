#!/usr/bin/env python3
"""
Riskless Frontier v2 Engine — Six Verified Super-Replicating & Irreversible-Lock Sleeves
========================================================================================
Implements the 6 strictly state-by-state riskless / irreversible-lock strategies selected
from the October 2026 Deep Research audit after live Gamma/CLOB/Polygon schema verification:

  1. `NR2_CONVERT_NO_SUBSET_ARB`:
     Asymmetric `NegRiskAdapter.convertPositions` (`0xc64748c4`) for small contender subsets
     `m in {2, 3}` (plus pure cash conversion `m = N`), selling only liquid complement `YES_j`
     (`j in L`) while retaining illiquid tail `YES_u` (`u in U = S^c \\ L`) as `$0.00`-cost
     free `$1.00` lottery tickets whenever `(m - 1)*(1 - f) + sum_{j in L} net_bid(YES_j) - sum_{i in S} net_ask(NO_i) >= min_edge`.

  2. `SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK`:
     Zero-fee (`feeType="zero_fees"`) NBA player milestone (`points`, `rebounds`, `assists`, `threes`)
     engine combining:
       - `3B` (`SP4_MILESTONE_POLISH_MIDDLE`): Pre/in-game same-player, same-stat `YES(Over K1) + NO(Over K2)`
         (`K1 < K2`, `.5` hooks), paying `$1.00` floor on under/over/DNP/canceled and `$2.00` inside `(K1, K2)`.
       - `3A` (`SP4_INGAME_CLINCH_LOCK`): Live ESPN NBA boxscore (`summary?event=...`) monotonic stat clinch
         with `+2` live buffer (`>= floor(K) + 2` while in-play to survive Secaucus 3PT->2PT / scorer adjustments;
         `>= floor(K) + 1` on `points`/`threes` once `completed == True`).

  3. `BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY`:
     Hardened final-hour (`180s <= rem_challenge_sec <= 3300s`, `proposal_age_sec >= 3600s`) resolution
     carry on `UmaCtfAdapter V4` (`0x65070be91477460d8a7aeeb94ef92fe056c2f2a7`) + `ManagedOptimisticOracleV2`
     (`0x2c0367a9db231ddebd88a94b4f6461a6e47c58b1`), verifying on-chain `isOnWhitelist(proposer)` (`0x3a3ab672`)
     against `0x9F35885CE8f67a942D7B2f4Fbf937987DA08c463` and vetoing `0.5e18` (`P3`) & `type(int256).min` (`P4`).

  4. `SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX`:
     Fee-exact (`sports_fees_v2=0.03`, `sports_fees_v3=0.05`) 90-minute regulation soccer cross-tree engine
     joining 3-way `NegRisk` (`Home / Draw / Away`) with sibling `-more-markets` via `gameId`:
       - `5A`: `2-NO -> $1.00 USDC + YES_k` conversion arb against `YES_k` bids, plus 3-way complete partitions.
       - `5B`: `YES(Draw) + YES(Over 0.5)` scoring-draw corridor (`$1.00` on `0-0`/win, `$1.50` if canceled,
         `$2.00` on `1-1, 2-2, ...`) and `-more-markets` goal/handicap corridors (`Over K1 + Under K2`, `Team(-1.5) + Opp(+2.5)`).

  5. `LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX`:
     Exact real-valued state-payoff matrix super-replication verifier (`min_omega (A x)_omega >= 1.00`) across:
       - `6C` (`BOP_2026`): 9-state `{D, R, Other} x {D, R, Other}` joint `balance-of-power-2026-midterms` (`incl. Other`)
         vs `Senate` + `House` (`zero_fees`).
       - `6B` (`NBA_EXACT_MARGIN`): 11-state `nba-*-exact-margin` (`5` Team A bands + `5` Team B bands + `Other` canceled)
         vs parent `nba-*` `moneyline` & full-game `spreads` (`zero_fees`), plus 5-`NO` `convertPositions` + `YES(ML)`.

  6. `API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK`:
     Fee-exact (`sports_fees_v2=0.03`) Best-of-3 Esports (`CS2`, `LoL`, `Dota 2`) engine:
       - `8A-Lock`: Post-Map-1 winner `+1.5` Map Handicap mathematical clinch (plus `1-1` post-Map-2 `Over 2.5 Games` lock).
       - `8A-Middle`: `YES(Team A Match Winner) + YES(Team B +1.5 Map Handicap)` BO3 `2-1` Polish Middle (`$1.00` floor, `$2.00` on `2-1`).
"""

from __future__ import annotations

import itertools
import json
import math
import os
import re
import unicodedata
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    NegRiskConvertSlateSpec,
    _extract_market_fee_rate,
    _net_unit_ask,
    _norm_team,
    _parse_clob_tokens,
    _parse_iso_ts,
    _walk_side_exact_shares,
)
from src.polymarket_research.uma_nba_endgame_engine import (
    DEFAULT_POLYGON_RPC,
    LiveNbaGameState,
    _canon_nba_team,
    _parse_json_list,
    _rpc_post,
    verify_uma_onchain_proposal_sync,
)

NEGRISK_ADAPTER_ADDR = "0xd91e80cf2e7be2e162c6513ced06f1dd0da35296"
SEL_NR_GET_QUESTION_COUNT = "b7f75d2c"  # getQuestionCount(bytes32)
SEL_NR_GET_FEE_BIPS = "2582cb5e"        # getFeeBips(bytes32)
SEL_NR_GET_DETERMINED = "7ae2e67b"      # getDetermined(bytes32)

UMA_V4_ADAPTERS = frozenset({
    "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7",
    "0x69c47de9d4d3dad79590d61b9e05918e03775f24",
})
MOOV2_ORACLE_ADDR = "0x2c0367a9db231ddebd88a94b4f6461a6e47c58b1"
UMA_PROPOSER_WHITELIST_ADDR = "0x9f35885ce8f67a942d7b2f4fbf937987da08c463"
SEL_IS_ON_WHITELIST = "3a3ab672"        # isOnWhitelist(address)

ESPN_NBA_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
BOP_2026_SLUGS = (
    "balance-of-power-2026-midterms",
    "which-party-will-win-the-senate-in-2026",
    "which-party-will-win-the-house-in-2026",
)

_NR_ADAPTER_CACHE: Dict[str, Tuple[int, int, bool]] = {}
_WHITELIST_CACHE: Dict[str, bool] = {}

_PLAYER_SUFFIX_RE = re.compile(r"\b(?:jr|sr|ii|iii|iv|v)\b\.?", re.IGNORECASE)
_PROP_TITLE_RE = re.compile(
    r"^(.+?):\s*(Points|Rebounds|Assists|3-Pointers Made|Threes|Three Pointers)\s+O/U\s+(\d+\.5)\b",
    re.IGNORECASE,
)
_NBA_EM_BAND_RE = re.compile(r"Exact\s+Margin:\s*(.+?)\s+by\s+(\d+)(?:-(\d+)|\+)", re.IGNORECASE)
_SOC_ADVANCE_VETO_RE = re.compile(
    r"\b(?:advance|qualify|lift\s+the\s+trophy|win\s+the\s+(?:cup|final|tie|trophy)|extra\s+time\s+included|penalt(?:y|ies)\s+included)\b",
    re.IGNORECASE,
)
_SPREAD_PARSE_RE = re.compile(r"^(.+?)\s*\(([+-]?\d+\.5)\)\s*$")
_MAP_HC_PAIR_RE = re.compile(
    r"Map\s+Handicap:\s*(.+?)\s*\(([+-]\d+\.5)\)\s*vs\.?\s*(.+?)\s*\(([+-]\d+\.5)\)",
    re.IGNORECASE,
)


def _net_unit_bid(px: float, fee_rate: float, fee_exp: float = 1.0) -> float:
    p = max(0.0, min(1.0, float(px)))
    fee = float(fee_rate) * ((p * (1.0 - p)) ** float(fee_exp)) if fee_rate > 0.0 else 0.0
    return max(0.0, p - fee)


def _is_half_hook(line: Optional[float]) -> bool:
    if line is None or not math.isfinite(line):
        return False
    rem = abs(float(line)) - math.floor(abs(float(line)))
    return abs(rem - 0.5) < 1e-6


def canon_player_name(raw: str) -> str:
    s = unicodedata.normalize("NFKD", str(raw or "")).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = _PLAYER_SUFFIX_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


# ==============================================================================
# 1. SLEEVE #1: NR2_CONVERT_NO_SUBSET_ARB (Asymmetric Subset Convert + Free Tail)
# ==============================================================================
def verify_negrisk_adapter_slate_sync(
    neg_risk_market_id: str,
    expected_n: int,
    rpc_url: Optional[str] = None,
    timeout: float = 4.5,
) -> Tuple[bool, int, str]:
    """Verifies `getQuestionCount == expected_n`, `getDetermined == False`, and returns `fee_bips`."""
    mkt_hex = str(neg_risk_market_id or "").strip().lower()
    if len(mkt_hex) != 66 or not mkt_hex.startswith("0x"):
        return False, 0, "INVALID_MARKET_ID"
    cached = _NR_ADAPTER_CACHE.get(mkt_hex)
    if cached is not None:
        q_cnt, fee_bips, det = cached
        if det:
            return False, fee_bips, "ALREADY_DETERMINED"
        if q_cnt != expected_n:
            return False, fee_bips, f"QCOUNT_MISMATCH({q_cnt}!={expected_n})"
        return True, fee_bips, "OK"

    rpc = rpc_url or os.getenv("POLYGON_RPC_URL") or DEFAULT_POLYGON_RPC
    arg = mkt_hex[2:]
    batch = [
        {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": NEGRISK_ADAPTER_ADDR, "data": f"0x{SEL_NR_GET_QUESTION_COUNT}{arg}"}, "latest"]},
        {"jsonrpc": "2.0", "id": 2, "method": "eth_call", "params": [{"to": NEGRISK_ADAPTER_ADDR, "data": f"0x{SEL_NR_GET_FEE_BIPS}{arg}"}, "latest"]},
        {"jsonrpc": "2.0", "id": 3, "method": "eth_call", "params": [{"to": NEGRISK_ADAPTER_ADDR, "data": f"0x{SEL_NR_GET_DETERMINED}{arg}"}, "latest"]},
    ]
    try:
        resp = _rpc_post(rpc, batch, timeout=timeout)
        by_id = {int(r["id"]): str(r.get("result") or "") for r in resp if isinstance(r, dict) and "id" in r}
        if not all(by_id.get(i, "").startswith("0x") and len(by_id[i]) >= 66 for i in (1, 2, 3)):
            return False, 0, "BAD_ADAPTER_RPC"
        q_cnt = int(by_id[1], 16)
        fee_bips = int(by_id[2], 16)
        det = int(by_id[3], 16) != 0
        if not det:
            _NR_ADAPTER_CACHE[mkt_hex] = (q_cnt, fee_bips, det)
        if det:
            return False, fee_bips, "ALREADY_DETERMINED"
        if q_cnt != expected_n:
            return False, fee_bips, f"QCOUNT_MISMATCH({q_cnt}!={expected_n})"
        return True, fee_bips, "OK"
    except Exception as exc:
        return False, 0, f"RPC_ERR:{type(exc).__name__}"


def detect_nr2_convert_no_subset_arbs(
    spec: NegRiskConvertSlateSpec,
    books_by_token: Dict[str, Dict[str, Any]],
    target_budget_usd: float = 120.0,
    min_edge_pure_cash: float = 0.012,
    min_edge_with_yes_sell: float = 0.015,
    min_shares: int = 6,
    fee_bips: int = 0,
) -> List[Dict[str, Any]]:
    """
    Evaluates small contender `NO` subsets `S` (`|S| = m in {2, 3}`) + full `m = N` pure-cash conversion
    on verified closed `NegRisk` partitions (`is_closed_convert_safe == True`).
    Sells ONLY liquid complement `YES_j` (`j in L`) where bid depth >= `q_out` and retains illiquid tail
    `YES_u` (`u in U = S^c \\ L`) as `$0.00`-cost free `$1.00` upside tickets!
    """
    if not spec.is_closed_convert_safe:
        return []
    n_tot = len(spec.brackets)
    if n_tot < 3 or fee_bips < 0 or fee_bips >= 500:
        return []
    conv_mult = 1.0 - (float(fee_bips) / 10000.0)

    # Extract L1 NO ask and L1 YES bid metrics per bracket
    br_info: List[Dict[str, Any]] = []
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
        b_yes_net = _net_unit_bid(bids_y[0][0], fr, fe) if bids_y else 0.0
        b_yes_sh = bids_y[0][1] if bids_y else 0.0
        br_info.append({
            "idx": idx,
            "bracket": b,
            "asks_n": asks_n,
            "bids_y": bids_y,
            "a_no_net": a_no_net,
            "a_no_sh": a_no_sh,
            "b_yes_net": b_yes_net,
            "b_yes_sh": b_yes_sh,
        })

    # Candidate NO subsets S:
    #   (a) Top-6 cheapest NO brackets (liquid contenders) -> all pairs (m=2) & triples (m=3)
    #   (b) Full m = N pure on-chain cash conversion (L = empty, U = empty)
    liquid_no = sorted([x for x in br_info if x["a_no_sh"] >= min_shares and x["a_no_net"] < 0.995], key=lambda x: x["a_no_net"])[:6]
    cand_s_list: List[Tuple[int, ...]] = []
    for r_sz in (2, 3):
        if len(liquid_no) >= r_sz and r_sz <= n_tot - 1:
            for comb in itertools.combinations([x["idx"] for x in liquid_no], r_sz):
                cand_s_list.append(tuple(sorted(comb)))
    if all(x["a_no_sh"] >= min_shares and x["a_no_net"] < 0.998 for x in br_info):
        cand_s_list.append(tuple(range(n_tot)))

    arbs: List[Dict[str, Any]] = []
    seen_s = set()
    for s_tup in cand_s_list:
        if s_tup in seen_s:
            continue
        seen_s.add(s_tup)
        m_cnt = len(s_tup)
        s_set = set(s_tup)
        comp_all = [i for i in range(n_tot) if i not in s_set]

        est_no_cost = sum(br_info[i]["a_no_net"] for i in s_tup)
        if est_no_cost <= 0.0:
            continue
        max_no_sh = min(br_info[i]["a_no_sh"] for i in s_tup)
        sh_base = int(math.floor(min(max_no_sh, target_budget_usd / max(0.25, est_no_cost))))
        if sh_base < min_shares:
            continue

        # Greedily select liquid YES complement subset L subseteq S^c that maximizes instant guaranteed cash
        comp_ranked = sorted(
            [i for i in comp_all if br_info[i]["b_yes_net"] >= 0.004 and br_info[i]["b_yes_sh"] >= min_shares * conv_mult],
            key=lambda i: -br_info[i]["b_yes_net"],
        )

        # Try prefix choices of L (from empty L=0 if m>=2 cash covers, up to all liquid complements)
        best_for_s: Optional[Dict[str, Any]] = None
        for k_len in range(0, len(comp_ranked) + 1):
            l_idxs = sorted(comp_ranked[:k_len])
            u_idxs = sorted([i for i in comp_all if i not in set(l_idxs)])
            sh_try = sh_base
            if l_idxs:
                min_y_sh = min(br_info[j]["b_yes_sh"] / max(conv_mult, 1e-6) for j in l_idxs)
                sh_try = int(math.floor(min(float(sh_base), min_y_sh)))
            if sh_try < min_shares:
                continue

            no_walks = []
            ok = True
            for i in s_tup:
                bi = br_info[i]["bracket"]
                wi = _walk_side_exact_shares(
                    (books_by_token.get(bi["no_token"]) or {}).get("asks") or [],
                    float(sh_try), float(bi["fee_rate"]), float(bi["fee_exponent"]), is_ask=True,
                )
                if wi is None:
                    ok = False
                    break
                no_walks.append((bi, wi))
            if not ok:
                continue

            sh_conv_out = float(sh_try) * conv_mult
            yes_walks = []
            for j in l_idxs:
                bj = br_info[j]["bracket"]
                wj = _walk_side_exact_shares(
                    (books_by_token.get(bj["yes_token"]) or {}).get("bids") or [],
                    sh_conv_out, float(bj["fee_rate"]), float(bj["fee_exponent"]), is_ask=False,
                )
                if wj is None or wj["net_per_share"] <= 0.002:
                    ok = False
                    break
                yes_walks.append((bj, wj))
            if not ok:
                continue

            no_cost_ps = sum(w["net_per_share"] for _, w in no_walks)
            usdc_conv_ps = float(m_cnt - 1) * conv_mult
            yes_bid_ps = conv_mult * sum(w["net_per_share"] for _, w in yes_walks)
            proceeds_ps = usdc_conv_ps + yes_bid_ps
            edge_ps = round(proceeds_ps - no_cost_ps, 5)
            req_edge = min_edge_pure_cash if not l_idxs else min_edge_with_yes_sell
            if edge_ps < req_edge:
                continue

            q_indices = [int(br_info[i]["bracket"]["question_index"]) for i in s_tup]
            index_set_int = sum(1 << qi for qi in q_indices)
            min_l1_usd = min([w["l1_usd"] for _, w in no_walks] + ([w["l1_usd"] for _, w in yes_walks] if yes_walks else [9999.0]))
            retained_tail = [br_info[u]["bracket"] for u in u_idxs]
            cand = {
                "mode": "NR2_SUBSET_CONVERT_FREE_TAIL" if retained_tail else "NR2_PURE_CASH_CONVERT",
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
                "converted_shares_out": round(sh_conv_out, 4),
                "fee_bips": fee_bips,
                "no_cost_per_share": round(no_cost_ps, 4),
                "usdc_converted_per_share": round(usdc_conv_ps, 4),
                "yes_bid_proceeds_per_share": round(yes_bid_ps, 4),
                "net_proceeds_per_share": round(proceeds_ps, 4),
                "net_edge_per_share": round(edge_ps, 4),
                "total_cost_usd": round(sum(w["net_cash_usd"] for _, w in no_walks), 2),
                "total_net_profit_usd": round(sh_try * edge_ps, 2),
                "total_fee_usd": round(sum(w["fee_usd"] for _, w in no_walks) + sum(w["fee_usd"] for _, w in yes_walks), 4),
                "l1_usd": round(min_l1_usd, 2),
                "no_legs": [{"token_id": b["no_token"], "bracket": b, "walk": w} for b, w in no_walks],
                "yes_sell_legs": [{"token_id": b["yes_token"], "bracket": b, "walk": w} for b, w in yes_walks],
                "retained_free_yes_brackets": retained_tail,
                "retained_tail_count": len(retained_tail),
                "close_ts": spec.end_ts,
                "label": (
                    f"NR2({m_cnt}/{n_tot}NO->${usdc_conv_ps:.2f}"
                    f"+SELL[{len(yes_walks)}Y]+FREE_TAIL[{len(retained_tail)}Y])"
                ),
            }
            if best_for_s is None or cand["net_edge_per_share"] > best_for_s["net_edge_per_share"]:
                best_for_s = cand
        if best_for_s is not None:
            arbs.append(best_for_s)

    arbs.sort(key=lambda x: (-float(x["net_edge_per_share"]), -int(x["retained_tail_count"])))
    return arbs


# ==============================================================================
# 2. SLEEVE #2: SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK (NBA Player Props 3A + 3B)
# ==============================================================================
@dataclass
class NbaPlayerPropRung:
    event_id: str
    event_slug: str
    game_title: str
    market_id: str
    condition_id: str
    player_name: str
    player_key: str
    stat_type: str        # "points", "rebounds", "assists", "threes"
    line: float           # half-integer hook (e.g. 22.5)
    yes_token: str        # Over
    no_token: str         # Under
    fee_rate: float
    tipoff_ts: float
    settle_est_ts: float
    home_team: str
    away_team: str
    fee_exponent: float = 1.0


@dataclass
class NbaPlayerPropSlate:
    event_id: str
    slug: str
    title: str
    tipoff_ts: float
    settle_est_ts: float
    home_team: str
    away_team: str
    props_by_player_stat: Dict[Tuple[str, str], List[NbaPlayerPropRung]] = field(default_factory=dict)


_ALLOWED_NBA_PROP_SMTS = frozenset({"points", "rebounds", "assists", "threes"})


def parse_nba_player_props_from_event(ev: Dict[str, Any], now_ts: Optional[float] = None) -> Optional[NbaPlayerPropSlate]:
    """Extracts all `0%`-fee half-integer NBA player milestone rungs (`points`, `rebounds`, `assists`, `threes`)."""
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
    if tip_ts <= 0.0:
        return None
    if now_ts is not None and tip_ts < now_ts - 8.0 * 3600.0:
        return None
    settle_ts = tip_ts + 3.25 * 3600.0
    ev_id = str(ev.get("id") or "")

    grouped: Dict[Tuple[str, str], List[NbaPlayerPropRung]] = {}
    for m in ev.get("markets") or []:
        if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
            continue
        smt = str(m.get("sportsMarketType") or "").strip().lower()
        if smt not in _ALLOWED_NBA_PROP_SMTS:
            continue
        fr, fe = _extract_market_fee_rate(m)
        toks = _parse_clob_tokens(m)
        outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
        if not toks or outs != ["yes", "no"]:
            continue
        raw_line = m.get("line")
        try:
            line = float(raw_line) if raw_line is not None else float("nan")
        except (TypeError, ValueError):
            line = float("nan")
        q_txt = str(m.get("groupItemTitle") or m.get("question") or "").strip()
        m_pr = _PROP_TITLE_RE.match(q_txt)
        if not m_pr:
            continue
        player_raw = m_pr.group(1).strip()
        if not math.isfinite(line):
            line = float(m_pr.group(3))
        if not _is_half_hook(line) or line < 0.5:
            continue
        pkey = canon_player_name(player_raw)
        if not pkey:
            continue
        rung = NbaPlayerPropRung(
            event_id=ev_id,
            event_slug=slug,
            game_title=title,
            market_id=str(m.get("id") or ""),
            condition_id=str(m.get("conditionId") or ""),
            player_name=player_raw,
            player_key=pkey,
            stat_type=smt,
            line=line,
            yes_token=toks[0],
            no_token=toks[1],
            fee_rate=fr,
            tipoff_ts=tip_ts,
            settle_est_ts=settle_ts,
            home_team=home_t,
            away_team=away_t,
            fee_exponent=fe,
        )
        grouped.setdefault((pkey, smt), []).append(rung)

    if not grouped:
        return None
    for k in grouped:
        grouped[k].sort(key=lambda r: r.line)
    return NbaPlayerPropSlate(
        event_id=ev_id,
        slug=slug,
        title=title,
        tipoff_ts=tip_ts,
        settle_est_ts=settle_ts,
        home_team=home_t,
        away_team=away_t,
        props_by_player_stat=grouped,
    )


def detect_sp4_milestone_ladder_boxes(
    slate: NbaPlayerPropSlate,
    best_asks: Dict[str, float],
    max_box_cost_net: float = 0.992,
) -> List[Dict[str, Any]]:
    """
    Sub-Mode 3B (`SP4_MILESTONE_POLISH_MIDDLE`):
    For the same player & stat in the same game with `K1 < K2` (both `.5` hooks, `zero_fees`),
    `YES(Over K1) + NO(Over K2)` pays `$1.00` on `< K1`, `> K2`, DNP (`No`), or Canceled (`50-50`),
    and `$2.00` whenever `K1 < Stat < K2`!
    """
    arbs: List[Dict[str, Any]] = []
    for (_, stat_t), rungs in slate.props_by_player_stat.items():
        if len(rungs) < 2:
            continue
        for i in range(len(rungs)):
            r_lo = rungs[i]
            ask_over_lo = best_asks.get(r_lo.yes_token)
            if ask_over_lo is None or not (0.02 <= ask_over_lo <= 0.98):
                continue
            for j in range(i + 1, len(rungs)):
                r_hi = rungs[j]
                if r_hi.line <= r_lo.line + 0.1:
                    continue
                ask_under_hi = best_asks.get(r_hi.no_token)
                if ask_under_hi is None or not (0.02 <= ask_under_hi <= 0.98):
                    continue
                gross_cost = round(float(ask_over_lo) + float(ask_under_hi), 4)
                cost = round(
                    _net_unit_ask(float(ask_over_lo), r_lo.fee_rate, r_lo.fee_exponent)
                    + _net_unit_ask(float(ask_under_hi), r_hi.fee_rate, r_hi.fee_exponent),
                    4,
                )
                if cost <= max_box_cost_net:
                    arbs.append({
                        "mode": "SP4_MILESTONE_POLISH_MIDDLE",
                        "event_id": slate.event_id,
                        "slug": slate.slug,
                        "title": slate.title,
                        "player_name": r_lo.player_name,
                        "stat_type": stat_t,
                        "line_low": r_lo.line,
                        "line_high": r_hi.line,
                        "box_cost_gross": gross_cost,
                        "box_cost_net": cost,
                        "close_ts": slate.settle_est_ts,
                        "leg_a": {
                            "token_id": r_lo.yes_token,
                            "opp_token_id": r_lo.no_token,
                            "condition_id": r_lo.condition_id,
                            "market_id": r_lo.market_id,
                            "side": "YES",
                            "label": f"{r_lo.player_name} {stat_t.upper()} O{r_lo.line}",
                            "fee_rate": r_lo.fee_rate,
                            "fee_exponent": r_lo.fee_exponent,
                            "neg_risk": False,
                            "strike": r_lo.line,
                        },
                        "leg_b": {
                            "token_id": r_hi.no_token,
                            "opp_token_id": r_hi.yes_token,
                            "condition_id": r_hi.condition_id,
                            "market_id": r_hi.market_id,
                            "side": "NO",
                            "label": f"{r_hi.player_name} {stat_t.upper()} U{r_hi.line}",
                            "fee_rate": r_hi.fee_rate,
                            "fee_exponent": r_hi.fee_exponent,
                            "neg_risk": False,
                            "strike": r_hi.line,
                        },
                        "label": f"{r_lo.player_name} {stat_t} O{r_lo.line} + U{r_hi.line}",
                    })
    arbs.sort(key=lambda x: (float(x["box_cost_net"]), -(float(x["line_high"]) - float(x["line_low"]))))
    return arbs


def parse_espn_nba_boxscore_players(summary_json: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """
    Parses ESPN NBA `summary?event={id}` JSON into `player_key -> {"points": int, "rebounds": int, "assists": int, "threes": int}`
    strictly for athletes who actually took the court (`didNotPlay == False` and `MIN > 0`).
    """
    out: Dict[str, Dict[str, int]] = {}
    for team_blk in ((summary_json or {}).get("boxscore") or {}).get("players") or []:
        for stat_blk in team_blk.get("statistics") or []:
            keys = [str(k) for k in (stat_blk.get("keys") or [])]
            if not keys:
                continue
            idx_min = next((i for i, k in enumerate(keys) if k == "minutes"), -1)
            idx_pts = next((i for i, k in enumerate(keys) if k == "points"), -1)
            idx_reb = next((i for i, k in enumerate(keys) if k == "rebounds"), -1)
            idx_ast = next((i for i, k in enumerate(keys) if k == "assists"), -1)
            idx_3pt = next((i for i, k in enumerate(keys) if k.startswith("threePointFieldGoalsMade")), -1)
            for ath in stat_blk.get("athletes") or []:
                if ath.get("didNotPlay"):
                    continue
                disp = str((ath.get("athlete") or {}).get("displayName") or "")
                pkey = canon_player_name(disp)
                stats_arr = ath.get("stats") or []
                if not pkey or not stats_arr:
                    continue
                if idx_min >= 0 and idx_min < len(stats_arr):
                    m_raw = str(stats_arr[idx_min]).strip()
                    if m_raw in ("", "0", "0:00", "--"):
                        continue
                rec: Dict[str, int] = {}
                try:
                    if 0 <= idx_pts < len(stats_arr):
                        rec["points"] = int(str(stats_arr[idx_pts]).split("-")[0])
                    if 0 <= idx_reb < len(stats_arr):
                        rec["rebounds"] = int(str(stats_arr[idx_reb]).split("-")[0])
                    if 0 <= idx_ast < len(stats_arr):
                        rec["assists"] = int(str(stats_arr[idx_ast]).split("-")[0])
                    if 0 <= idx_3pt < len(stats_arr):
                        rec["threes"] = int(str(stats_arr[idx_3pt]).split("-")[0])
                except ValueError:
                    continue
                if rec:
                    out[pkey] = rec
    return out


def fetch_espn_nba_boxscore_players_sync(espn_game_id: str, timeout: float = 5.0) -> Dict[str, Dict[str, int]]:
    url = ESPN_NBA_SUMMARY_URL.format(game_id=espn_game_id)
    req = urllib.request.Request(url, headers={"User-Agent": "DominusSportsOracle/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    return parse_espn_nba_boxscore_players(data)


def evaluate_sp4_ingame_clinch_locks(
    slate: NbaPlayerPropSlate,
    game_state: LiveNbaGameState,
    player_stats: Dict[str, Dict[str, int]],
) -> List[Dict[str, Any]]:
    """
    Sub-Mode 3A (`SP4_INGAME_CLINCH_LOCK`):
    Identifies NBA `YES(Over K)` player props that have ALREADY crossed `K` irreversibly:
      - In-play (`state == "in"`): requires `val >= floor(K) + 2` across all stats (guards against
        Secaucus timeout 3PT->2PT foot-on-line review on `points`/`threes` and scorer strips on `rebounds`/`assists`).
      - Final (`state == "post"` and `completed == True`): `val >= floor(K) + 1` for `points`/`threes`,
        and `val >= floor(K) + 2` for `rebounds`/`assists`.
    """
    if game_state.state not in ("in", "post") or not player_stats:
        return []
    is_final = bool(game_state.completed and game_state.state == "post")
    locks: List[Dict[str, Any]] = []
    for (pkey, stat_t), rungs in slate.props_by_player_stat.items():
        p_rec = player_stats.get(pkey)
        if not p_rec or stat_t not in p_rec:
            continue
        cur_val = int(p_rec[stat_t])
        base_need_extra = 1 if (is_final and stat_t in ("points", "threes")) else 2
        for r in rungs:
            req_int = int(math.floor(r.line)) + base_need_extra
            if cur_val >= req_int:
                cushion = round(float(cur_val) - r.line, 1)
                p_lk = 0.999 if (is_final or cushion >= 2.5) else 0.996
                locks.append({
                    "mode": "SP4_FINAL_STAT_LOCK" if is_final else "SP4_LIVE_STAT_CLINCH",
                    "rung": r,
                    "current_stat": cur_val,
                    "cushion": cushion,
                    "p_lock": p_lk,
                    "game_state": game_state.state,
                    "period": game_state.period,
                })
    return locks


# ==============================================================================
# 3. SLEEVE #3: BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY
# ==============================================================================
def verify_proposer_whitelisted_sync(
    proposer_addr: str,
    rpc_url: Optional[str] = None,
    timeout: float = 4.5,
) -> bool:
    p_clean = str(proposer_addr or "").strip().lower()
    if len(p_clean) != 42 or not p_clean.startswith("0x"):
        return False
    if p_clean in _WHITELIST_CACHE:
        return _WHITELIST_CACHE[p_clean]
    rpc = rpc_url or os.getenv("POLYGON_RPC_URL") or DEFAULT_POLYGON_RPC
    calldata = f"0x{SEL_IS_ON_WHITELIST}{p_clean[2:].rjust(64, '0')}"
    try:
        resp = _rpc_post(
            rpc,
            {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": UMA_PROPOSER_WHITELIST_ADDR, "data": calldata}, "latest"]},
            timeout=timeout,
        )
        res_hex = str((resp or {}).get("result") or "")
        is_wl = res_hex.startswith("0x") and len(res_hex) >= 66 and (int(res_hex, 16) == 1)
        _WHITELIST_CACHE[p_clean] = is_wl
        return is_wl
    except Exception:
        return False


def verify_bond2_moov2_final_hour_sync(
    m: Dict[str, Any],
    rpc_url: Optional[str] = None,
    now_ts: Optional[float] = None,
    min_proposal_age_sec: float = 3600.0,
    min_rem_challenge_sec: float = 180.0,
    max_rem_challenge_sec: float = 3300.0,
) -> Dict[str, Any]:
    """
    Verifies a `BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY` candidate:
      1. Passes full `verify_uma_onchain_proposal_sync` (binary `0` or `1e18`, vetoes `0.5e18` P3 & `int256.min` P4,
         zero disputer/reset/pause/refund/manual flags).
      2. Adapter is `UmaCtfAdapter V4` / `NegRisk V4` pointing to `ManagedOptimisticOracleV2` (`0x2c0367a9...`).
      3. `proposer` is verified on-chain via `isOnWhitelist(proposer) == true` (`0x9F35885C...`).
      4. Proposal has survived `>= 3600s` (`1h`) of liveness and has `180s <= rem_challenge_sec <= 3300s`.
    """
    base = verify_uma_onchain_proposal_sync(
        m,
        rpc_url=rpc_url,
        now_ts=now_ts,
        min_proposal_age_sec=min_proposal_age_sec,
        max_rem_challenge_sec=max_rem_challenge_sec,
    )
    if not base.get("verified"):
        return base
    if str(base.get("adapter") or "").lower() not in UMA_V4_ADAPTERS:
        return {"verified": False, "reason": "NOT_V4_ADAPTER"}
    if str(base.get("oo_address") or "").lower() != MOOV2_ORACLE_ADDR:
        return {"verified": False, "reason": "NOT_MOOV2_ORACLE"}
    rem_s = float(base.get("rem_challenge_sec") or 0.0)
    if rem_s < min_rem_challenge_sec:
        return {"verified": False, "reason": f"REM_TOO_SHORT({rem_s:.0f}s)"}
    if not verify_proposer_whitelisted_sync(str(base.get("proposer") or ""), rpc_url=rpc_url):
        return {"verified": False, "reason": "PROPOSER_NOT_WHITELISTED"}
    out = dict(base)
    out["proposer_whitelisted"] = True
    out["moov2_final_hour"] = True
    return out


# ==============================================================================
# 4. SLEEVE #4: SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX (Soccer 3-Way + More-Mkts)
# ==============================================================================
@dataclass
class SoccerRegulationTree:
    game_id: str
    event_id_3way: str
    slug_3way: str
    title: str
    neg_risk_market_id: str
    end_ts: float
    home_team: str
    away_team: str
    home_leg: Dict[str, Any]   # 3-way NegRisk bracket dict
    draw_leg: Dict[str, Any]
    away_leg: Dict[str, Any]
    over05_leg: Optional[Dict[str, Any]] = None
    totals: List[Dict[str, Any]] = field(default_factory=list)   # sorted by line: Over/Under
    spreads: List[Dict[str, Any]] = field(default_factory=list)  # regulation spreads (-1.5, -2.5)


def link_and_parse_soccer_regulation_trees(
    events: List[Dict[str, Any]],
    now_ts: Optional[float] = None,
) -> Dict[str, SoccerRegulationTree]:
    """
    Groups active Soccer events (`tag_id=100350`) by `gameId`, pairing closed 3-way regulation `NegRisk`
    match moneylines (`Home / Draw / Away`) with optional sibling `-more-markets` totals & spreads.
    Strictly vetoes cup-advancement / extra-time markets.
    """
    by_gid: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events or []:
        if not isinstance(ev, dict) or ev.get("closed") or ev.get("archived"):
            continue
        gid = str(ev.get("gameId") or "").strip()
        if gid:
            by_gid.setdefault(gid, []).append(ev)

    trees: Dict[str, SoccerRegulationTree] = {}
    for gid, ev_list in by_gid.items():
        ev_3way: Optional[Dict[str, Any]] = None
        ev_more: Optional[Dict[str, Any]] = None
        for e in ev_list:
            sl = str(e.get("slug") or "").lower()
            mkts = e.get("markets") or []
            if sl.endswith("-more-markets") and not e.get("negRisk"):
                ev_more = e
            elif (
                bool(e.get("negRisk"))
                and not bool(e.get("negRiskAugmented", True))
                and len(mkts) == 3
                and not any(sl.endswith(suf) for suf in ("-halftime-result", "-second-half-result", "-first-to-score", "-exact-score"))
                and all(str(m.get("sportsMarketType") or "").lower() in ("moneyline", "soccer_match_winner", "") for m in mkts)
            ):
                ev_3way = e
        if ev_3way is None:
            continue

        end_ts = _parse_iso_ts(ev_3way.get("startTime") or ev_3way.get("endDate")) or 0.0
        if end_ts <= 0.0 or (now_ts is not None and end_ts < now_ts - 4.0 * 3600.0):
            continue
        nr_mkt_id = str(ev_3way.get("negRiskMarketID") or "").strip().lower()
        home_b: Optional[Dict[str, Any]] = None
        draw_b: Optional[Dict[str, Any]] = None
        away_b: Optional[Dict[str, Any]] = None
        non_draw: List[Dict[str, Any]] = []
        bad_scope = False

        for idx_m, m in enumerate(ev_3way.get("markets") or []):
            if m.get("closed") or m.get("archived") or m.get("acceptingOrders") is False:
                bad_scope = True
                break
            q_txt = str(m.get("question") or "")
            desc = str(m.get("description") or "")
            grp = str(m.get("groupItemTitle") or "").strip()
            if _SOC_ADVANCE_VETO_RE.search(f"{q_txt}\n{desc}\n{grp}"):
                bad_scope = True
                break
            toks = _parse_clob_tokens(m)
            outs = [str(o).strip().lower() for o in _parse_json_list(m.get("outcomes"))]
            if not toks or outs != ["yes", "no"]:
                bad_scope = True
                break
            fr, fexp = _extract_market_fee_rate(m)
            q_id = str(m.get("questionID") or "").strip().lower()
            q_idx = int(q_id[64:], 16) if (len(q_id) == 66 and q_id.startswith("0x")) else idx_m
            b_rec = {
                "market_id": str(m.get("id") or ""),
                "condition_id": str(m.get("conditionId") or ""),
                "question_index": q_idx,
                "label": grp or q_txt[:36],
                "team_norm": _norm_team(grp),
                "yes_token": toks[0],
                "no_token": toks[1],
                "fee_rate": fr,
                "fee_exponent": fexp,
                "neg_risk": True,
            }
            if "draw" in grp.lower() or "end in a draw" in q_txt.lower():
                draw_b = b_rec
            else:
                non_draw.append(b_rec)

        if bad_scope or draw_b is None or len(non_draw) != 2:
            continue
        home_b, away_b = non_draw[0], non_draw[1]
        tree = SoccerRegulationTree(
            game_id=gid,
            event_id_3way=str(ev_3way.get("id") or ""),
            slug_3way=str(ev_3way.get("slug") or ""),
            title=str(ev_3way.get("title") or ev_3way.get("slug") or ""),
            neg_risk_market_id=nr_mkt_id,
            end_ts=end_ts + 2.5 * 3600.0,
            home_team=home_b["team_norm"],
            away_team=away_b["team_norm"],
            home_leg=home_b,
            draw_leg=draw_b,
            away_leg=away_b,
        )

        if ev_more is not None:
            for mm in ev_more.get("markets") or []:
                if mm.get("closed") or mm.get("archived") or mm.get("acceptingOrders") is False:
                    continue
                desc_mm = str(mm.get("description") or "")
                q_mm = str(mm.get("question") or "")
                grp_mm = str(mm.get("groupItemTitle") or "").strip()
                if _SOC_ADVANCE_VETO_RE.search(f"{q_mm}\n{desc_mm}\n{grp_mm}"):
                    continue
                toks_mm = _parse_clob_tokens(mm)
                outs_mm = [str(o).strip() for o in _parse_json_list(mm.get("outcomes"))]
                if not toks_mm or len(outs_mm) != 2:
                    continue
                fr_m, fe_m = _extract_market_fee_rate(mm)
                smt_m = str(mm.get("sportsMarketType") or "").strip().lower()
                try:
                    ln_m = float(mm.get("line")) if mm.get("line") is not None else float("nan")
                except (TypeError, ValueError):
                    ln_m = float("nan")
                if smt_m == "totals" and _is_half_hook(ln_m):
                    o0 = outs_mm[0].lower()
                    over_tok, under_tok = (toks_mm[0], toks_mm[1]) if "over" in o0 else (toks_mm[1], toks_mm[0])
                    t_rec = {
                        "market_id": str(mm.get("id") or ""),
                        "condition_id": str(mm.get("conditionId") or ""),
                        "line": abs(ln_m),
                        "over_token": over_tok,
                        "under_token": under_tok,
                        "fee_rate": fr_m,
                        "fee_exponent": fe_m,
                        "neg_risk": False,
                    }
                    tree.totals.append(t_rec)
                    if abs(abs(ln_m) - 0.5) < 1e-6:
                        tree.over05_leg = t_rec
                elif smt_m == "spreads" and _is_half_hook(ln_m) and ln_m < 0:
                    m_sp = _SPREAD_PARSE_RE.match(grp_mm)
                    if m_sp:
                        fav_norm = _norm_team(m_sp.group(1))
                        o0_n = _norm_team(outs_mm[0])
                        fav_tok, dog_tok = (toks_mm[0], toks_mm[1]) if fav_norm == o0_n else (toks_mm[1], toks_mm[0])
                        dog_lbl = outs_mm[1] if fav_norm == o0_n else outs_mm[0]
                        tree.spreads.append({
                            "market_id": str(mm.get("id") or ""),
                            "condition_id": str(mm.get("conditionId") or ""),
                            "fav_team": fav_norm,
                            "fav_label": m_sp.group(1).strip(),
                            "dog_label": dog_lbl,
                            "abs_line": abs(ln_m),  # e.g. 1.5 -> fav -1.5 vs dog +1.5
                            "fav_minus_token": fav_tok,
                            "dog_plus_token": dog_tok,
                            "fee_rate": fr_m,
                            "fee_exponent": fe_m,
                            "neg_risk": False,
                        })
            tree.totals.sort(key=lambda x: float(x["line"]))
            tree.spreads.sort(key=lambda x: (x["fav_team"], float(x["abs_line"])))

        trees[gid] = tree
    return trees


def detect_soc1_regulation_boxes(
    tree: SoccerRegulationTree,
    books_by_token: Dict[str, Dict[str, Any]],
    best_asks: Dict[str, float],
    max_2leg_cost_net: float = 0.988,
    min_conv_edge_ps: float = 0.010,
    target_budget_usd: float = 120.0,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fee-exact (`sports_fees_v2=0.03`, `sports_fees_v3=0.05`) detector for `SOC1`:
      - `two_leg_boxes`:
          (i)  `5B-1` `YES(Draw) + YES(Over 0.5 Goals)` (`$1.00` on `0-0`/win, `$1.50` canceled, `$2.00` scoring draw!)
          (ii) `5B-2` `-more-markets` `Over K1 + Under K2` (`K1 < K2`) and `Fav(-k1) + Dog(+k2)` (`k1 < k2`, e.g. `-1.5` + `+2.5`)
      - `convert_arbs`:
          `5A` `NO_i + NO_j` -> `convertPositions` -> `$1.00 USDC + YES_k` sold into `bids(YES_k)`.
    """
    two_leg_boxes: List[Dict[str, Any]] = []
    convert_arbs: List[Dict[str, Any]] = []

    # 5B-1: YES(Draw) + YES(Over 0.5)
    if tree.over05_leg is not None:
        dl, o05 = tree.draw_leg, tree.over05_leg
        px_d = best_asks.get(dl["yes_token"])
        px_o = best_asks.get(o05["over_token"])
        if px_d is not None and px_o is not None:
            c_net = round(
                _net_unit_ask(px_d, dl["fee_rate"], dl["fee_exponent"])
                + _net_unit_ask(px_o, o05["fee_rate"], o05["fee_exponent"]),
                4,
            )
            if c_net <= max_2leg_cost_net:
                two_leg_boxes.append({
                    "mode": "SOC1_SCORING_DRAW_CORRIDOR",
                    "game_id": tree.game_id,
                    "title": tree.title,
                    "box_cost_net": c_net,
                    "close_ts": tree.end_ts,
                    "leg_a": {
                        "token_id": dl["yes_token"], "opp_token_id": dl["no_token"], "condition_id": dl["condition_id"],
                        "market_id": dl["market_id"], "side": "YES", "label": "YES[Draw]",
                        "fee_rate": dl["fee_rate"], "fee_exponent": dl["fee_exponent"], "neg_risk": True, "strike": 0.5,
                    },
                    "leg_b": {
                        "token_id": o05["over_token"], "opp_token_id": o05["under_token"], "condition_id": o05["condition_id"],
                        "market_id": o05["market_id"], "side": "OVER", "label": "OVER[0.5 Goals]",
                        "fee_rate": o05["fee_rate"], "fee_exponent": o05["fee_exponent"], "neg_risk": False, "strike": 0.5,
                    },
                    "label": f"{tree.title}: YES[Draw] + OVER[0.5 Goals]",
                })

    # 5B-2a: Totals Over K1 + Under K2 (K1 < K2)
    for i in range(len(tree.totals)):
        t_lo = tree.totals[i]
        px_lo = best_asks.get(t_lo["over_token"])
        if px_lo is None:
            continue
        for j in range(i + 1, len(tree.totals)):
            t_hi = tree.totals[j]
            if t_hi["line"] <= t_lo["line"] + 0.1:
                continue
            px_hi = best_asks.get(t_hi["under_token"])
            if px_hi is None:
                continue
            c_net = round(
                _net_unit_ask(px_lo, t_lo["fee_rate"], t_lo["fee_exponent"])
                + _net_unit_ask(px_hi, t_hi["fee_rate"], t_hi["fee_exponent"]),
                4,
            )
            if c_net <= max_2leg_cost_net:
                two_leg_boxes.append({
                    "mode": "SOC1_GOAL_CORRIDOR_BOX",
                    "game_id": tree.game_id,
                    "title": tree.title,
                    "box_cost_net": c_net,
                    "close_ts": tree.end_ts,
                    "leg_a": {
                        "token_id": t_lo["over_token"], "opp_token_id": t_lo["under_token"], "condition_id": t_lo["condition_id"],
                        "market_id": t_lo["market_id"], "side": "OVER", "label": f"O{t_lo['line']}",
                        "fee_rate": t_lo["fee_rate"], "fee_exponent": t_lo["fee_exponent"], "neg_risk": False, "strike": t_lo["line"],
                    },
                    "leg_b": {
                        "token_id": t_hi["under_token"], "opp_token_id": t_hi["over_token"], "condition_id": t_hi["condition_id"],
                        "market_id": t_hi["market_id"], "side": "UNDER", "label": f"U{t_hi['line']}",
                        "fee_rate": t_hi["fee_rate"], "fee_exponent": t_hi["fee_exponent"], "neg_risk": False, "strike": t_hi["line"],
                    },
                    "label": f"{tree.title}: Goals O{t_lo['line']} + U{t_hi['line']}",
                })

    # 5B-2b: Regulation Spreads Fav(-k1) + Dog(+k2) for same fav_team with k1 < k2 (e.g. Fav -1.5 + Dog +2.5 -> $2 on 2-goal win, $1 floor & $1 if canceled)
    for i in range(len(tree.spreads)):
        s1 = tree.spreads[i]
        px_1 = best_asks.get(s1["fav_minus_token"])
        if px_1 is None:
            continue
        for j in range(i + 1, len(tree.spreads)):
            s2 = tree.spreads[j]
            if s2["fav_team"] != s1["fav_team"] or s2["abs_line"] <= s1["abs_line"] + 0.1:
                continue
            px_2 = best_asks.get(s2["dog_plus_token"])
            if px_2 is None:
                continue
            c_net = round(
                _net_unit_ask(px_1, s1["fee_rate"], s1["fee_exponent"])
                + _net_unit_ask(px_2, s2["fee_rate"], s2["fee_exponent"]),
                4,
            )
            if c_net <= max_2leg_cost_net:
                two_leg_boxes.append({
                    "mode": "SOC1_HANDICAP_CORRIDOR_BOX",
                    "game_id": tree.game_id,
                    "title": tree.title,
                    "box_cost_net": c_net,
                    "close_ts": tree.end_ts,
                    "leg_a": {
                        "token_id": s1["fav_minus_token"], "opp_token_id": s1["dog_plus_token"], "condition_id": s1["condition_id"],
                        "market_id": s1["market_id"], "side": "SPREAD", "label": f"{s1['fav_label']}(-{s1['abs_line']})",
                        "fee_rate": s1["fee_rate"], "fee_exponent": s1["fee_exponent"], "neg_risk": False, "strike": -s1["abs_line"],
                    },
                    "leg_b": {
                        "token_id": s2["dog_plus_token"], "opp_token_id": s2["fav_minus_token"], "condition_id": s2["condition_id"],
                        "market_id": s2["market_id"], "side": "SPREAD", "label": f"{s2['dog_label']}(+{s2['abs_line']})",
                        "fee_rate": s2["fee_rate"], "fee_exponent": s2["fee_exponent"], "neg_risk": False, "strike": s2["abs_line"],
                    },
                    "label": f"{tree.title}: {s1['fav_label']}(-{s1['abs_line']}) + {s2['dog_label']}(+{s2['abs_line']})",
                })

    # 5A: 3-Way Synthetic Convert (buy NO_i + NO_j -> $1.00 USDC + YES_k sold into bids(YES_k))
    legs3 = [tree.home_leg, tree.draw_leg, tree.away_leg]
    if len(tree.neg_risk_market_id) == 66 and {int(x["question_index"]) for x in legs3} == {0, 1, 2}:
        for idx_k in range(3):
            b_k = legs3[idx_k]
            b_i, b_j = [legs3[u] for u in range(3) if u != idx_k]
            bk_ni = books_by_token.get(b_i["no_token"]) or {}
            bk_nj = books_by_token.get(b_j["no_token"]) or {}
            bk_yk = books_by_token.get(b_k["yes_token"]) or {}
            asks_i = bk_ni.get("asks") or []
            asks_j = bk_nj.get("asks") or []
            bids_k = bk_yk.get("bids") or []
            if not (asks_i and asks_j and bids_k):
                continue
            sh_l1 = min(
                max((float(a.get("size", 0)) for a in asks_i[:1]), default=0.0),
                max((float(a.get("size", 0)) for a in asks_j[:1]), default=0.0),
                max((float(b.get("size", 0)) for b in bids_k[:1]), default=0.0),
            )
            sh_try = int(math.floor(min(sh_l1, target_budget_usd / 0.80)))
            if sh_try < 6:
                continue
            wi = _walk_side_exact_shares(asks_i, float(sh_try), b_i["fee_rate"], b_i["fee_exponent"], is_ask=True)
            wj = _walk_side_exact_shares(asks_j, float(sh_try), b_j["fee_rate"], b_j["fee_exponent"], is_ask=True)
            wk = _walk_side_exact_shares(bids_k, float(sh_try), b_k["fee_rate"], b_k["fee_exponent"], is_ask=False)
            if wi is None or wj is None or wk is None:
                continue
            no_cost_ps = wi["net_per_share"] + wj["net_per_share"]
            proc_ps = 1.0 + wk["net_per_share"]
            edge_ps = round(proc_ps - no_cost_ps, 5)
            if edge_ps >= min_conv_edge_ps:
                q_idxs = sorted([int(b_i["question_index"]), int(b_j["question_index"])])
                convert_arbs.append({
                    "mode": "SOC1_3WAY_CONVERT_SYNTHETIC",
                    "event_id": tree.event_id_3way,
                    "game_id": tree.game_id,
                    "title": tree.title,
                    "neg_risk_market_id": tree.neg_risk_market_id,
                    "m_no_legs": 2,
                    "n_total": 3,
                    "no_question_indices": q_idxs,
                    "index_set_int": sum(1 << q for q in q_idxs),
                    "shares": sh_try,
                    "no_cost_per_share": round(no_cost_ps, 4),
                    "yes_bid_proceeds_per_share": round(wk["net_per_share"], 4),
                    "net_edge_per_share": round(edge_ps, 4),
                    "total_net_profit_usd": round(sh_try * edge_ps, 2),
                    "l1_usd": round(min(wi["l1_usd"], wj["l1_usd"], wk["l1_usd"]), 2),
                    "no_legs": [{"token_id": b_i["no_token"], "bracket": b_i, "walk": wi}, {"token_id": b_j["no_token"], "bracket": b_j, "walk": wj}],
                    "yes_sell_legs": [{"token_id": b_k["yes_token"], "bracket": b_k, "walk": wk}],
                    "close_ts": tree.end_ts,
                    "label": f"SOC1_CONV(NO[{b_i['label'][:12]}]+NO[{b_j['label'][:12]}]->$1+SELL[{b_k['label'][:12]}])",
                })

    two_leg_boxes.sort(key=lambda x: float(x["box_cost_net"]))
    convert_arbs.sort(key=lambda x: -float(x["net_edge_per_share"]))
    return {"two_leg_boxes": two_leg_boxes, "convert_arbs": convert_arbs}


# ==============================================================================
# 5. SLEEVE #5: LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX (6C BOP + 6B NBA EM)
# ==============================================================================
def find_state_matrix_dominance_boxes(
    legs: List[Dict[str, Any]],
    best_asks: Dict[str, float],
    max_2leg_cost_net: float = 0.994,
    max_3leg_cost_net: float = 0.992,
) -> List[Dict[str, Any]]:
    """
    Exact real-valued state-payoff matrix verifier across `S` exhaustive states (`payoff_vec` in `[0.0, 1.0]^S`,
    including `0.5` cancellation payoffs and `Other` states!):
      - Requires `min_s sum_{j in B} v_j[s] >= 1.0 - 1e-9` (strictly state-by-state riskless!).
      - Requires legs come from at least 2 distinct markets (`market_id`) and no proper subset already covers `>= 1.0`.
    """
    priced = []
    for lg in legs:
        tid = str(lg["token_id"])
        if tid not in best_asks:
            continue
        px = float(best_asks[tid])
        if not (0.001 <= px <= 0.992):
            continue
        c_net = _net_unit_ask(px, float(lg.get("fee_rate", 0.0)), float(lg.get("fee_exponent", 1.0)))
        priced.append((lg, px, c_net))
    if len(priced) < 2:
        return []
    n_states = len(priced[0][0]["payoff_vec"])
    arbs: List[Dict[str, Any]] = []

    # 1. Minimal 2-leg boxes
    for i in range(len(priced)):
        la, _, ca = priced[i]
        va = la["payoff_vec"]
        for j in range(i + 1, len(priced)):
            lb, _, cb = priced[j]
            if la["market_id"] == lb["market_id"]:
                continue
            cost2 = round(ca + cb, 4)
            if cost2 > max_2leg_cost_net:
                continue
            vb = lb["payoff_vec"]
            sums = [va[s] + vb[s] for s in range(n_states)]
            if min(sums) >= 1.0 - 1e-9:
                arbs.append({
                    "n_legs": 2,
                    "box_cost_net": cost2,
                    "min_payout": round(min(sums), 4),
                    "max_payout": round(max(sums), 4),
                    "jackpot_states": sum(1 for v in sums if v >= 1.5 - 1e-9),
                    "legs": [la, lb],
                    "close_ts": max(float(la["end_ts"]), float(lb["end_ts"])),
                    "label": f"{la['label']} + {lb['label']}",
                })

    # 2. Minimal 3-leg boxes (skip if any 2-leg sub-pair already >= 1.0 across all states)
    short = sorted(priced, key=lambda x: x[2])[:18]
    for i in range(len(short)):
        la, _, ca = short[i]
        va = la["payoff_vec"]
        for j in range(i + 1, len(short)):
            lb, _, cb = short[j]
            if ca + cb > max_3leg_cost_net:
                continue
            vb = lb["payoff_vec"]
            if min(va[s] + vb[s] for s in range(n_states)) >= 1.0 - 1e-9:
                continue
            for k in range(j + 1, len(short)):
                lc, _, cc = short[k]
                cost3 = round(ca + cb + cc, 4)
                if cost3 > max_3leg_cost_net:
                    continue
                if len({la["market_id"], lb["market_id"], lc["market_id"]}) < 2:
                    continue
                vc = lc["payoff_vec"]
                if min(va[s] + vc[s] for s in range(n_states)) >= 1.0 - 1e-9:
                    continue
                if min(vb[s] + vc[s] for s in range(n_states)) >= 1.0 - 1e-9:
                    continue
                sums3 = [va[s] + vb[s] + vc[s] for s in range(n_states)]
                if min(sums3) >= 1.0 - 1e-9:
                    arbs.append({
                        "n_legs": 3,
                        "box_cost_net": cost3,
                        "min_payout": round(min(sums3), 4),
                        "max_payout": round(max(sums3), 4),
                        "jackpot_states": sum(1 for v in sums3 if v >= 1.5 - 1e-9),
                        "legs": [la, lb, lc],
                        "close_ts": max(float(la["end_ts"]), float(lb["end_ts"]), float(lc["end_ts"])),
                        "label": f"{la['label']} + {lb['label']} + {lc['label']}",
                    })

    arbs.sort(key=lambda x: (float(x["box_cost_net"]), -int(x["jackpot_states"])))
    return arbs


# 9 atomic states for 2026 Midterms: (Senate, House) in {D, R, O} x {D, R, O}
BOP_9_STATES: Tuple[Tuple[str, str], ...] = (
    ("D", "D"), ("D", "R"), ("D", "O"),
    ("R", "D"), ("R", "R"), ("R", "O"),
    ("O", "D"), ("O", "R"), ("O", "O"),
)


def build_lp1_bop_2026_truth_legs(events_by_slug: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Template 6C (`LP1_BOP_CHAMBER_IMPLICATION`):
    Builds exact 9-state `{D, R, Other} x {D, R, Other}` payoff vectors across:
      - `balance-of-power-2026-midterms` (`D Sweep`, `D Sen/R House`, `R Sen/D House`, `R Sweep`, `Other`)
      - `which-party-will-win-the-senate-in-2026` (`Democratic Party`, `Republican Party`)
      - `which-party-will-win-the-house-in-2026` (`Democratic Party`, `Republican Party`)
    """
    legs: List[Dict[str, Any]] = []

    def _add_mkt(m: Dict[str, Any], event_slug: str, tag_lbl: str, yes_fn) -> None:
        if m.get("closed") or m.get("archived") or m.get("active") is False:
            return
        toks = _parse_clob_tokens(m)
        if not toks:
            return
        fr, fe = _extract_market_fee_rate(m)
        end_ts = _parse_iso_ts(m.get("endDate")) or 0.0
        mid = str(m.get("id") or "")
        cid = str(m.get("conditionId") or "")
        nr = bool(m.get("negRisk"))
        v_yes = [1.0 if yes_fn(s_sen, s_hse) else 0.0 for s_sen, s_hse in BOP_9_STATES]
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

    ev_bop = events_by_slug.get("balance-of-power-2026-midterms") or {}
    for m in ev_bop.get("markets") or []:
        q = str(m.get("question") or m.get("groupItemTitle") or "").lower()
        if "d senate, d house" in q or "democrats sweep" in q:
            _add_mkt(m, "bop", "BOP:D_Sweep", lambda s, h: s == "D" and h == "D")
        elif "d senate, r house" in q:
            _add_mkt(m, "bop", "BOP:DSen_RHouse", lambda s, h: s == "D" and h == "R")
        elif "r senate, d house" in q:
            _add_mkt(m, "bop", "BOP:RSen_DHouse", lambda s, h: s == "R" and h == "D")
        elif "r senate, r house" in q or "republicans sweep" in q:
            _add_mkt(m, "bop", "BOP:R_Sweep", lambda s, h: s == "R" and h == "R")
        elif "other" in q:
            _add_mkt(m, "bop", "BOP:Other", lambda s, h: s == "O" or h == "O")

    ev_sen = events_by_slug.get("which-party-will-win-the-senate-in-2026") or {}
    for m in ev_sen.get("markets") or []:
        grp = str(m.get("groupItemTitle") or "").strip().lower()
        if grp == "democratic party":
            _add_mkt(m, "senate", "Sen:Dem", lambda s, h: s == "D")
        elif grp == "republican party":
            _add_mkt(m, "senate", "Sen:Rep", lambda s, h: s == "R")

    ev_hse = events_by_slug.get("which-party-will-win-the-house-in-2026") or {}
    for m in ev_hse.get("markets") or []:
        grp = str(m.get("groupItemTitle") or "").strip().lower()
        if grp == "democratic party":
            _add_mkt(m, "house", "House:Dem", lambda s, h: h == "D")
        elif grp == "republican party":
            _add_mkt(m, "house", "House:Rep", lambda s, h: h == "R")

    return legs


# 11 atomic states for NBA Exact-Margin x Moneyline/Spreads:
#   0..4: Team A wins by [(1,5), (6,10), (11,15), (16,20), (21,999)]
#   5..9: Team B wins by [(1,5), (6,10), (11,15), (16,20), (21,999)]
#   10:   Game Canceled / Not Played (`Exact-Margin Other = 1.0`, `Moneyline/Spread = 0.50`)
_EM_BANDS: Tuple[Tuple[int, int], ...] = ((1, 5), (6, 10), (11, 15), (16, 20), (21, 999))


def build_lp1_nba_exact_margin_bundle(
    parent_ev: Dict[str, Any],
    em_ev: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Template 6B (`LP1_NBA_EXACT_MARGIN_VS_ML`):
    Links `nba-*` (`moneyline` + `spreads`) with sibling `nba-*-exact-margin` (`11` `zero_fees` brackets)
    across all 11 exact states (including State 10 `Canceled 50-50`!).
    """
    if parent_ev.get("closed") or em_ev.get("closed") or not em_ev.get("negRisk") or em_ev.get("negRiskAugmented", True):
        return None
    em_mkts = em_ev.get("markets") or []
    if len(em_mkts) != 11:
        return None
    end_ts = (_parse_iso_ts(parent_ev.get("startTime") or parent_ev.get("endDate")) or 0.0) + 3.25 * 3600.0
    nr_mkt_id = str(em_ev.get("negRiskMarketID") or "").strip().lower()

    # Locate parent moneyline first to define canonical Team A / Team B
    ml_mkt = next((m for m in (parent_ev.get("markets") or []) if str(m.get("sportsMarketType") or "").lower() == "moneyline" and not m.get("closed")), None)
    if ml_mkt is None:
        return None
    ml_toks = _parse_clob_tokens(ml_mkt)
    ml_outs = [str(o).strip() for o in _parse_json_list(ml_mkt.get("outcomes"))]
    ml_fr, ml_fe = _extract_market_fee_rate(ml_mkt)
    if not ml_toks or len(ml_outs) != 2:
        return None
    team_a, team_b = _canon_nba_team(ml_outs[0]), _canon_nba_team(ml_outs[1])
    ml_mid = str(ml_mkt.get("id") or "")
    ml_cid = str(ml_mkt.get("conditionId") or "")

    legs: List[Dict[str, Any]] = []
    # Team A ML: 1.0 in states 0..4, 0.0 in 5..9, 0.5 in state 10 (Canceled)
    va_ml = [1.0]*5 + [0.0]*5 + [0.5]
    vb_ml = [0.0]*5 + [1.0]*5 + [0.5]
    legs.append({
        "market_id": ml_mid, "condition_id": ml_cid, "token_id": ml_toks[0], "opp_token_id": ml_toks[1],
        "side": "ML_A", "label": f"ML[{ml_outs[0]}]", "fee_rate": ml_fr, "fee_exponent": ml_fe,
        "neg_risk": False, "end_ts": end_ts, "payoff_vec": va_ml, "strike": 0.0,
    })
    legs.append({
        "market_id": ml_mid, "condition_id": ml_cid, "token_id": ml_toks[1], "opp_token_id": ml_toks[0],
        "side": "ML_B", "label": f"ML[{ml_outs[1]}]", "fee_rate": ml_fr, "fee_exponent": ml_fe,
        "neg_risk": False, "end_ts": end_ts, "payoff_vec": vb_ml, "strike": 0.0,
    })

    # Exact-band boundary spreads (-5.5, -10.5, -15.5, -20.5) align cleanly with 5-point Exact Margin bands!
    _band_cuts = {5.5: 1, 10.5: 2, 15.5: 3, 20.5: 4}
    for sm in parent_ev.get("markets") or []:
        if sm.get("closed") or str(sm.get("sportsMarketType") or "").lower() != "spreads":
            continue
        fr_s, fe_s = _extract_market_fee_rate(sm)
        try:
            ln_s = abs(float(sm.get("line")))
        except (TypeError, ValueError):
            continue
        if ln_s not in _band_cuts:
            continue
        tk_s = _parse_clob_tokens(sm)
        outs_s = [str(o).strip() for o in _parse_json_list(sm.get("outcomes"))]
        grp_s = str(sm.get("groupItemTitle") or sm.get("question") or "")
        m_sp = re.search(r"([A-Za-z0-9\s\.]+?)\s*\(-" + re.escape(str(ln_s)) + r"\)", grp_s)
        if not tk_s or len(outs_s) != 2 or not m_sp:
            continue
        fav_t = _canon_nba_team(m_sp.group(1))
        cut_idx = _band_cuts[ln_s]
        o0_t = _canon_nba_team(outs_s[0])
        fav_tok, dog_tok = (tk_s[0], tk_s[1]) if fav_t == o0_t else (tk_s[1], tk_s[0])
        if fav_t == team_a:
            v_fav = [1.0 if idx >= cut_idx else 0.0 for idx in range(5)] + [0.0]*5 + [0.5]
        elif fav_t == team_b:
            v_fav = [0.0]*5 + [1.0 if idx >= cut_idx else 0.0 for idx in range(5)] + [0.5]
        else:
            continue
        v_dog = [1.0 - x if i < 10 else 0.5 for i, x in enumerate(v_fav)]
        sm_id, sm_cid = str(sm.get("id") or ""), str(sm.get("conditionId") or "")
        legs.append({
            "market_id": sm_id, "condition_id": sm_cid, "token_id": fav_tok, "opp_token_id": dog_tok,
            "side": "SPREAD", "label": f"{fav_t.title()}(-{ln_s})", "fee_rate": fr_s, "fee_exponent": fe_s,
            "neg_risk": False, "end_ts": end_ts, "payoff_vec": v_fav, "strike": -ln_s,
        })
        legs.append({
            "market_id": sm_id, "condition_id": sm_cid, "token_id": dog_tok, "opp_token_id": fav_tok,
            "side": "SPREAD", "label": f"Opp(+{ln_s})", "fee_rate": fr_s, "fee_exponent": fe_s,
            "neg_risk": False, "end_ts": end_ts, "payoff_vec": v_dog, "strike": ln_s,
        })

    # Parse all 11 Exact-Margin NegRisk child markets
    team_a_em_no: List[Dict[str, Any]] = []
    team_b_em_no: List[Dict[str, Any]] = []
    seen_states = set()
    for idx_m, m in enumerate(em_mkts):
        if m.get("closed") or m.get("archived"):
            return None
        fr_e, fe_e = _extract_market_fee_rate(m)
        tk_e = _parse_clob_tokens(m)
        if not tk_e:
            return None
        grp = str(m.get("groupItemTitle") or m.get("question") or "").strip()
        q_id = str(m.get("questionID") or "").strip().lower()
        q_idx = int(q_id[64:], 16) if (len(q_id) == 66 and q_id.startswith("0x")) else idx_m
        st_idx: Optional[int] = None
        if "other" in grp.lower():
            st_idx = 10
        else:
            m_b = _NBA_EM_BAND_RE.search(grp)
            if m_b:
                t_em = _canon_nba_team(m_b.group(1))
                lo = int(m_b.group(2))
                band_i = next((k for k, (blo, _) in enumerate(_EM_BANDS) if blo == lo), None)
                if band_i is not None:
                    if t_em == team_a or t_em in team_a or team_a in t_em:
                        st_idx = band_i
                    elif t_em == team_b or t_em in team_b or team_b in t_em:
                        st_idx = 5 + band_i
        if st_idx is None:
            return None
        seen_states.add(st_idx)
        v_yes = [1.0 if s == st_idx else 0.0 for s in range(11)]
        v_no = [1.0 - x for x in v_yes]
        mid_e, cid_e = str(m.get("id") or ""), str(m.get("conditionId") or "")
        short_lbl = grp.replace("Exact Margin:", "").strip()
        legs.append({
            "market_id": mid_e, "condition_id": cid_e, "token_id": tk_e[0], "opp_token_id": tk_e[1],
            "side": "YES", "label": f"EM_Y[{short_lbl}]", "fee_rate": fr_e, "fee_exponent": fe_e,
            "neg_risk": True, "end_ts": end_ts, "payoff_vec": v_yes, "strike": float(st_idx),
        })
        no_rec = {
            "market_id": mid_e, "condition_id": cid_e, "token_id": tk_e[1], "opp_token_id": tk_e[0],
            "side": "NO", "label": f"EM_N[{short_lbl}]", "fee_rate": fr_e, "fee_exponent": fe_e,
            "neg_risk": True, "end_ts": end_ts, "payoff_vec": v_no, "strike": float(st_idx),
            "question_index": q_idx,
        }
        legs.append(no_rec)
        if 0 <= st_idx <= 4:
            team_a_em_no.append(no_rec)
        elif 5 <= st_idx <= 9:
            team_b_em_no.append(no_rec)

    if seen_states != set(range(11)):
        return None
    return {
        "event_id": str(parent_ev.get("id") or ""),
        "em_event_id": str(em_ev.get("id") or ""),
        "slug": str(parent_ev.get("slug") or ""),
        "title": str(parent_ev.get("title") or ""),
        "neg_risk_market_id": nr_mkt_id,
        "end_ts": end_ts,
        "legs": legs,
        "ml_a_token": ml_toks[0],
        "ml_b_token": ml_toks[1],
        "ml_a_label": ml_outs[0],
        "ml_b_label": ml_outs[1],
        "team_a_em_no": team_a_em_no,
        "team_b_em_no": team_b_em_no,
    }


# ==============================================================================
# 6. SLEEVE #6: API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK (BO3 Lock + 2-1 Polish Middle)
# ==============================================================================
@dataclass
class EsportsBo3Spec:
    event_id: str
    slug: str
    title: str
    end_ts: float
    team_a: str
    team_b: str
    ml_market_id: str
    ml_condition_id: str
    ml_a_token: str
    ml_b_token: str
    ml_fee_rate: float
    ml_fee_exp: float
    hc_market_id: str
    hc_condition_id: str
    hc_fav_is_a: bool       # If True: hc_minus_token = A(-1.5), hc_plus_token = B(+1.5)
    hc_minus_token: str     # Favorite (-1.5)
    hc_plus_token: str      # Underdog (+1.5)
    hc_fee_rate: float
    hc_fee_exp: float
    map1_a_token: Optional[str] = None
    map1_b_token: Optional[str] = None
    map1_resolved_winner: Optional[str] = None  # "A" or "B" if Gamma already closed/priced 1-0
    map2_a_token: Optional[str] = None
    map2_b_token: Optional[str] = None
    map2_resolved_winner: Optional[str] = None
    ou25_over_token: Optional[str] = None
    ou25_under_token: Optional[str] = None
    ou25_market_id: str = ""
    ou25_condition_id: str = ""
    ou25_fee_rate: float = 0.03


def parse_esports_bo3_event(ev: Dict[str, Any], now_ts: Optional[float] = None) -> Optional[EsportsBo3Spec]:
    """
    Parses Best-of-3 (`(BO3)`) Esports events (`tag_id=64`: CS2, LoL, Dota 2, Valorant) containing
    `moneyline`, `map_handicap` (`-1.5` vs `+1.5`), and `child_moneyline` (`Map 1 Winner`).
    Strictly vetoes BO1/BO2/BO5 events.
    """
    if ev.get("closed") or ev.get("archived"):
        return None
    title = str(ev.get("title") or "")
    mkts = ev.get("markets") or []
    is_bo3_title = bool(re.search(r"\(\s*bo3\s*\)|\bbest\s+of\s+3\b", title, re.IGNORECASE))
    has_map4_or_5 = any(re.search(r"\bmap\s+[45]\b", str(m.get("groupItemTitle") or m.get("question") or ""), re.IGNORECASE) for m in mkts)
    if has_map4_or_5:
        return None
    has_ou25 = any(str(m.get("sportsMarketType") or "").lower() == "totals" and abs(float(m.get("line") or 0) - 2.5) < 1e-6 for m in mkts if m.get("line") is not None)
    if not (is_bo3_title or has_ou25):
        return None

    end_ts = (_parse_iso_ts(ev.get("startTime") or ev.get("endDate")) or 0.0) + 3.5 * 3600.0
    if now_ts is not None and end_ts < now_ts + 60.0:
        return None

    ml_m = next((m for m in mkts if str(m.get("sportsMarketType") or "").lower() == "moneyline" and not m.get("closed")), None)
    hc_m = next((m for m in mkts if str(m.get("sportsMarketType") or "").lower() == "map_handicap" and not m.get("closed") and abs(abs(float(m.get("line") or 0)) - 1.5) < 1e-6), None)
    if ml_m is None or hc_m is None:
        return None

    ml_toks = _parse_clob_tokens(ml_m)
    ml_outs = [str(o).strip() for o in _parse_json_list(ml_m.get("outcomes"))]
    hc_toks = _parse_clob_tokens(hc_m)
    hc_outs = [str(o).strip() for o in _parse_json_list(hc_m.get("outcomes"))]
    if not ml_toks or len(ml_outs) != 2 or not hc_toks or len(hc_outs) != 2:
        return None

    ta_raw, tb_raw = ml_outs[0], ml_outs[1]
    ta_n, tb_n = _norm_team(ta_raw), _norm_team(tb_raw)
    hc_o0_n, hc_o1_n = _norm_team(hc_outs[0]), _norm_team(hc_outs[1])
    if {ta_n, tb_n} != {hc_o0_n, hc_o1_n}:
        return None

    # Identify which outcome in map_handicap is (-1.5) vs (+1.5) from description or groupItemTitle
    hc_desc = str(hc_m.get("description") or "")
    hc_grp = str(hc_m.get("groupItemTitle") or hc_m.get("question") or "")
    fav_is_a: Optional[bool] = None
    m_desc_2maps = re.search(r'resolve\s+to\s+"([^"]+)"\s+if\s+.+?\s+wins\s+2\s+or\s+more\s+maps', hc_desc, re.IGNORECASE)
    if m_desc_2maps:
        fav_n = _norm_team(m_desc_2maps.group(1))
        if fav_n == ta_n:
            fav_is_a = True
        elif fav_n == tb_n:
            fav_is_a = False
    if fav_is_a is None:
        m_pair = _MAP_HC_PAIR_RE.search(hc_grp)
        if m_pair:
            s1 = float(m_pair.group(2))
            # In Polymarket CS2/LoL schema, outcomes[0] corresponds to the first team in `Map Handicap: T1 (-1.5) vs T2 (+1.5)` when s1 == -1.5
            fav_team_hc = hc_o0_n if s1 < 0 else hc_o1_n
            fav_is_a = (fav_team_hc == ta_n)
    if fav_is_a is None:
        return None

    fav_n_final = ta_n if fav_is_a else tb_n
    hc_minus_tok, hc_plus_tok = (hc_toks[0], hc_toks[1]) if hc_o0_n == fav_n_final else (hc_toks[1], hc_toks[0])
    ml_fr, ml_fe = _extract_market_fee_rate(ml_m)
    hc_fr, hc_fe = _extract_market_fee_rate(hc_m)

    spec = EsportsBo3Spec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        title=title,
        end_ts=end_ts,
        team_a=ta_raw,
        team_b=tb_raw,
        ml_market_id=str(ml_m.get("id") or ""),
        ml_condition_id=str(ml_m.get("conditionId") or ""),
        ml_a_token=ml_toks[0],
        ml_b_token=ml_toks[1],
        ml_fee_rate=ml_fr,
        ml_fee_exp=ml_fe,
        hc_market_id=str(hc_m.get("id") or ""),
        hc_condition_id=str(hc_m.get("conditionId") or ""),
        hc_fav_is_a=fav_is_a,
        hc_minus_token=hc_minus_tok,
        hc_plus_token=hc_plus_tok,
        hc_fee_rate=hc_fr,
        hc_fee_exp=hc_fe,
    )

    def _extract_map_winner(cm: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        ctoks = _parse_clob_tokens(cm)
        couts = [_norm_team(str(x)) for x in _parse_json_list(cm.get("outcomes"))]
        cprices = _parse_json_list(cm.get("outcomePrices"))
        tok_a, tok_b = None, None
        if ctoks and len(couts) == 2 and {couts[0], couts[1]} == {ta_n, tb_n}:
            tok_a, tok_b = (ctoks[0], ctoks[1]) if couts[0] == ta_n else (ctoks[1], ctoks[0])
        res_w: Optional[str] = None
        if len(cprices) == 2 and len(couts) == 2:
            try:
                p0, p1 = float(cprices[0]), float(cprices[1])
                if cm.get("closed") or (max(p0, p1) >= 0.995 and min(p0, p1) <= 0.005):
                    if p0 >= 0.995 and p1 <= 0.005:
                        res_w = "A" if couts[0] == ta_n else "B"
                    elif p1 >= 0.995 and p0 <= 0.005:
                        res_w = "A" if couts[1] == ta_n else "B"
            except (TypeError, ValueError):
                pass
        return tok_a, tok_b, res_w

    for cm in mkts:
        smt_c = str(cm.get("sportsMarketType") or "").lower()
        grp_c = str(cm.get("groupItemTitle") or cm.get("question") or "").lower()
        if smt_c == "child_moneyline":
            if "map 1" in grp_c or "game 1" in grp_c:
                spec.map1_a_token, spec.map1_b_token, spec.map1_resolved_winner = _extract_map_winner(cm)
            elif "map 2" in grp_c or "game 2" in grp_c:
                spec.map2_a_token, spec.map2_b_token, spec.map2_resolved_winner = _extract_map_winner(cm)
        elif smt_c == "totals" and not cm.get("closed") and cm.get("line") is not None and abs(float(cm.get("line")) - 2.5) < 1e-6:
            otoks = _parse_clob_tokens(cm)
            oouts = [str(x).lower() for x in _parse_json_list(cm.get("outcomes"))]
            if otoks and len(oouts) == 2:
                spec.ou25_over_token = otoks[0] if "over" in oouts[0] else otoks[1]
                spec.ou25_under_token = otoks[1] if "over" in oouts[0] else otoks[0]
                spec.ou25_market_id = str(cm.get("id") or "")
                spec.ou25_condition_id = str(cm.get("conditionId") or "")
                spec.ou25_fee_rate, _ = _extract_market_fee_rate(cm)

    return spec


def _infer_live_map_winner(
    resolved_flag: Optional[str],
    tok_a: Optional[str],
    tok_b: Optional[str],
    books_by_token: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    if resolved_flag in ("A", "B"):
        return resolved_flag
    if not tok_a or not tok_b:
        return None
    bk_a = books_by_token.get(tok_a) or {}
    bk_b = books_by_token.get(tok_b) or {}
    bid_a = max((float(b.get("price", 0)) for b in (bk_a.get("bids") or []) if float(b.get("size", 0)) > 0), default=0.0)
    bid_b = max((float(b.get("price", 0)) for b in (bk_b.get("bids") or []) if float(b.get("size", 0)) > 0), default=0.0)
    ask_a = min((float(a.get("price", 1)) for a in (bk_a.get("asks") or []) if float(a.get("size", 0)) > 0), default=1.0)
    ask_b = min((float(a.get("price", 1)) for a in (bk_b.get("asks") or []) if float(a.get("size", 0)) > 0), default=1.0)
    if bid_a >= 0.992 and bid_b <= 0.005 and ask_b <= 0.015:
        return "A"
    if bid_b >= 0.992 and bid_a <= 0.005 and ask_a <= 0.015:
        return "B"
    return None


def evaluate_api1_esports_bo3_opportunities(
    spec: EsportsBo3Spec,
    books_by_token: Dict[str, Dict[str, Any]],
    best_asks: Dict[str, float],
    max_middle_cost_net: float = 0.988,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Evaluates:
      1. `single_leg_locks`:
         - `API1_BO3_MAP1_PLUS15_LOCK`: If Underdog (`+1.5` side) won Map 1 (`A` when `hc_fav_is_a == False`,
           or `B` when `hc_fav_is_a == True`), Underdog `+1.5` Map Handicap (`hc_plus_token`) is clinched!
         - `API1_BO3_1_1_OVER25_LOCK`: If Map 1 winner != Map 2 winner (`1-1` split), `Over 2.5 Games` is clinched!
      2. `two_leg_boxes`:
         - `API1_BO3_2_1_POLISH_MIDDLE`: `YES(Fav Match Winner) + YES(Dog +1.5 Map Handicap)` (`$1.00` floor on
           `2-0, 1-2, 0-2` & pre-match void; `$2.00` jackpot on `2-1`! When entered post-Map-1 after Dog won Map 1,
           100% immune even to mid-series forfeits!).
    """
    locks: List[Dict[str, Any]] = []
    boxes: List[Dict[str, Any]] = []

    m1_w = _infer_live_map_winner(spec.map1_resolved_winner, spec.map1_a_token, spec.map1_b_token, books_by_token)
    m2_w = _infer_live_map_winner(spec.map2_resolved_winner, spec.map2_a_token, spec.map2_b_token, books_by_token)

    dog_side = "B" if spec.hc_fav_is_a else "A"
    dog_name = spec.team_b if spec.hc_fav_is_a else spec.team_a
    fav_name = spec.team_a if spec.hc_fav_is_a else spec.team_b
    fav_ml_tok = spec.ml_a_token if spec.hc_fav_is_a else spec.ml_b_token
    dog_ml_tok = spec.ml_b_token if spec.hc_fav_is_a else spec.ml_a_token

    if m1_w == dog_side:
        locks.append({
            "mode": "API1_BO3_MAP1_PLUS15_LOCK",
            "token_id": spec.hc_plus_token,
            "opp_token_id": spec.hc_minus_token,
            "market_id": spec.hc_market_id,
            "condition_id": spec.hc_condition_id,
            "fee_rate": spec.hc_fee_rate,
            "fee_exponent": spec.hc_fee_exp,
            "p_lock": 0.997,
            "side_label": "PLUS_1.5",
            "display_label": f"{dog_name} (+1.5 Maps) [Map 1 Won]",
            "close_ts": spec.end_ts,
        })

    if m1_w in ("A", "B") and m2_w in ("A", "B") and m1_w != m2_w and spec.ou25_over_token and spec.ou25_under_token:
        locks.append({
            "mode": "API1_BO3_1_1_OVER25_LOCK",
            "token_id": spec.ou25_over_token,
            "opp_token_id": spec.ou25_under_token,
            "market_id": spec.ou25_market_id,
            "condition_id": spec.ou25_condition_id,
            "fee_rate": spec.ou25_fee_rate,
            "fee_exponent": 1.0,
            "p_lock": 0.998,
            "side_label": "OVER_2.5",
            "display_label": f"{spec.title[:44]} Over 2.5 Maps [1-1 Split]",
            "close_ts": spec.end_ts,
        })

    # BO3 2-1 Polish Middle: Fav Match Winner + Dog (+1.5 Maps)
    px_fav_ml = best_asks.get(fav_ml_tok)
    px_dog_hc = best_asks.get(spec.hc_plus_token)
    if px_fav_ml is not None and px_dog_hc is not None:
        c_net = round(
            _net_unit_ask(px_fav_ml, spec.ml_fee_rate, spec.ml_fee_exp)
            + _net_unit_ask(px_dog_hc, spec.hc_fee_rate, spec.hc_fee_exp),
            4,
        )
        if c_net <= max_middle_cost_net:
            boxes.append({
                "mode": "API1_BO3_POST_M1_MIDDLE" if m1_w == dog_side else "API1_BO3_2_1_POLISH_MIDDLE",
                "event_id": spec.event_id,
                "title": spec.title,
                "box_cost_net": c_net,
                "post_m1_forfeit_immune": (m1_w == dog_side),
                "close_ts": spec.end_ts,
                "leg_a": {
                    "token_id": fav_ml_tok, "opp_token_id": dog_ml_tok, "condition_id": spec.ml_condition_id,
                    "market_id": spec.ml_market_id, "side": "ML", "label": f"ML[{fav_name}]",
                    "fee_rate": spec.ml_fee_rate, "fee_exponent": spec.ml_fee_exp, "neg_risk": False, "strike": 0.0,
                },
                "leg_b": {
                    "token_id": spec.hc_plus_token, "opp_token_id": spec.hc_minus_token, "condition_id": spec.hc_condition_id,
                    "market_id": spec.hc_market_id, "side": "HANDICAP", "label": f"{dog_name}(+1.5)",
                    "fee_rate": spec.hc_fee_rate, "fee_exponent": spec.hc_fee_exp, "neg_risk": False, "strike": 1.5,
                },
                "label": f"{spec.title[:42]}: ML[{fav_name}] + {dog_name}(+1.5)",
            })

    return {"single_leg_locks": locks, "two_leg_boxes": boxes}

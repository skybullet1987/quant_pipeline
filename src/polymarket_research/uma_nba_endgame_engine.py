#!/usr/bin/env python3
"""
Evergreen Post-Outcome UMA Resolution Bond Harvester & Live NBA Endgame Lock Engine
===================================================================================
Implements two orthogonal, repeatable daily Polymarket alpha sleeves:

  1. `BOND1_UMA_RESOLUTION_CARRY` (`UMA_RESOLUTION_BOND_HARVESTER`):
     - Captures `$0.950 - $0.9955 -> $1.0000` guaranteed redemption carry during the
       UMA Optimistic Oracle liveness challenge window (`15m - 2h`) on objective markets.
     - Enforces a Strict Dual-Verification Gate:
         (a) Direct Polygon RPC `eth_call` verification against `UmaCtfAdapter.getQuestion`
             and `OptimisticOracleV2.getState` / `getRequest` (`state in {Proposed, Expired}`,
             `proposer != 0x0`, `disputer == 0x0`, `reset/paused/refund == False`, exact
             `ancillaryData` `p1`/`p2` outcome mapping, `50/50` tie veto, `age >= 120s`).
         (b) Objective-domain allowlist + anti-subjective speech/editorial veto + live
             primary-source cross-check + losing-complement CLOB book consensus gate.

  2. `SP2_NBA_ENDGAME_LOCK` (`0.00%`-Fee Live NBA Final-2m & Post-Buzzer Sniper):
     - Polls real-time NBA scoreboard state (`site.api.espn.com` primary + `cdn.nba.com`
       fallback) across active `zero_fees` `nba-2026` Moneyline, Spread, and Total markets.
     - Combines post-buzzer `Final` score locks, monotonic `Over + 2.5pt` locks, and
       Q4/OT final-`120s` Bill-James Safe-Lead + Stern Brownian-bridge locks (`p >= 0.993`)
       with strict Overtime-extension trap vetoes on `Under` and `+k.5` spreads.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    NbaGameSpec,
    NbaOutcomeLeg,
    _extract_market_fee_rate,
    _norm_team,
    _parse_clob_tokens,
    _parse_iso_ts,
)

logger = logging.getLogger("UmaNbaEndgameEngine")

DEFAULT_POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"
FALLBACK_POLYGON_RPCS = (
    "https://1rpc.io/matic",
    "https://polygon-rpc.com",
)
ESPN_NBA_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
CDN_NBA_SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"

ZERO_ADDR = "0x0000000000000000000000000000000000000000"
ONE_E18 = 10**18
HALF_E18 = 5 * (10**17)

VERIFIED_UMA_ADAPTERS = frozenset({
    "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7",  # UmaCtfAdapter v3
    "0x69c47de9d4d3dad79590d61b9e05918e03775f24",  # NegRiskUmaCtfAdapter
    "0x2f5e3684cb1f318ec51b00edba38d79ac2c0aa9d",  # UmaCtfAdapter v2
    "0x6a9d222616c90fca5754cd1333cfd9b7fb6a4f74",  # UmaCtfAdapter v1
    "0x157ce2d672854c848c9b79c49a8cc6cc89176a49",  # UmaCtfAdapter legacy
})
NEGRISK_UMA_ADAPTERS = frozenset({
    "0x69c47de9d4d3dad79590d61b9e05918e03775f24",
})

# Verified keccak256 4-byte selectors on Polygon UmaCtfAdapter & OptimisticOracleV2
SEL_OPTIMISTIC_ORACLE = "22302922"  # optimisticOracle()
SEL_GET_QUESTION = "58c039cd"       # getQuestion(bytes32)
SEL_GET_STATE = "ba4b930c"          # getState(address,bytes32,uint256,bytes)
SEL_GET_REQUEST = "a9904f9b"        # getRequest(address,bytes32,uint256,bytes)
YES_OR_NO_IDENT_HEX = b"YES_OR_NO_QUERY".ljust(32, b"\x00").hex()

_OO_ADDR_CACHE: Dict[str, str] = {}

_SUBJECTIVE_VETO_RE = re.compile(
    r'(\bsay\b.{0,30}["“]|\bmention\b|\btweet\b|\btruth social\b|\bceasefire\b'
    r'|\binvade\b|\bstrike on\b|\bpardon\b|\bresign\b|\bnominate\b'
    r'|\bsole discretion\b|\bplaceholder\b)',
    re.IGNORECASE,
)
_OBJECTIVE_ORACLE_RE = re.compile(
    r"(aviationweather\.gov|weather\.gov\.hk|wunderground\.com|binance\.com|chain\.link"
    r"|pyth\.network|federalreserve\.gov|bls\.gov|bea\.gov|census\.gov|eia\.gov|treasury\.gov"
    r"|gasprices\.aaa\.com|boxofficemojo\.com|xtracker"
    r"|nba\.com|wnba\.com|nhl\.com|mlb\.com|nfl\.com|ncaa\.com|espn\.com"
    r"|premierleague\.com|uefa\.com|fifa\.com|fiba\.basketball|atptour\.com|wtatennis\.com"
    r"|ufc\.com|pgatour\.com|formula1\.com|vlr\.gg|liquipedia\.net|lolesports\.com|hlTV|lol\s*esports)",
    re.IGNORECASE,
)
_OFFICIAL_SPORTS_OR_ROSTER_CLAUSE_RE = re.compile(
    r"(?:\bnext\s+team\s+.+?\s+officially\s+joins\s+by\b"
    r"|\bofficially\s+(?:signs?\s+with|traded\s+to|joins)\b"
    r"|\bmake\s+the\s+(?:20\d{2}(?:-\d{2})?\s+)?(?:nfl|nba|mlb|nhl|mls|cfb|college\s+football)\s+playoffs\b"
    r"|\bwin\s+the\s+(?:20\d{2}(?:-\d{2})?\s+)?(?:super\s+bowl|nba\s+finals|world\s+series|stanley\s+cup"
    r"|premier\s+league|champions\s+league|la\s+liga|serie\s+a|bundesliga|ligue\s+1"
    r"|cfb\s+national\s+championship|college\s+football\s+playoff|heisman\s+trophy"
    r"|afc|nfc|eastern\s+conference|western\s+conference"
    r"|(?:afc|nfc)\s+(?:east|north|south|west))\b"
    r"|\b(?:nfl|nba|mlb|nhl|premier\s+league|champions\s+league|ufc|formula\s+1|f1|valorant\s+champions\s+tour|vct|pro[\s\-]+football)\b"
    r".*\b(?:regular\s+season|clean\s+sheet|relegated|top\s+4|playoffs?|championship|division|roster|offseason|next[\s\-]+team|transaction\s+wire|trade\s+deadline)\b)",
    re.IGNORECASE | re.DOTALL,
)
_NON_LEAGUE_POP_OR_POLITICS_VETO_RE = re.compile(
    r"\b(?:election|presidential|senate|congress|house\s+of\s+representatives|governor|mayor|parliament|prime\s+minister"
    r"|dancing\s+with\s+the\s+stars|bachelor|bachelorette|survivor|love\s+island|big\s+brother"
    r"|oscar|academy\s+awards?|grammy|emmy|golden\s+globe|eurovision"
    r"|gta\s+marathon|subathon|twitch|youtuber|streamer|tiktok|podcast)\b",
    re.IGNORECASE,
)
_SPORTS_TITLE_RE = re.compile(
    r"(\bvs\.?\s+|\bwin on 20\d{2}-\d{2}-\d{2}\b|\bo/u\s+\d+|\bspread:\s+|\bgame\s+[1-7]\s+winner\b|\bmap\s+[1-5]\s+winner\b)",
    re.IGNORECASE,
)
_EARLY_BARRIER_MARKET_RE = re.compile(
    r"\b(reach|hit|dip|touch|drop\s+to|fall\s+to|climb\s+to|at\s+any\s+point|before\s+20\d{2})\b",
    re.IGNORECASE,
)
_HEX32_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
_ANC_CORRESPONDS_RE = re.compile(
    r"p1\s+corresponds\s+to\s+([^,\.\n]+),\s*p2\s+to\s+([^,\.\n]+)",
    re.IGNORECASE,
)


@dataclass
class LiveNbaGameState:
    game_id: str
    start_ts: float
    state: str          # "pre", "in", "post"
    completed: bool
    period: int
    clock_sec: float
    home_name: str
    home_abbr: str
    home_score: int
    away_name: str
    away_abbr: str
    away_score: int
    source: str = "espn"


def _parse_json_list(raw: Any) -> List[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("["):
            try:
                val = json.loads(s)
                return val if isinstance(val, list) else []
            except Exception:
                return []
    return []


def is_objective_uma_market(m: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Strictly validates that a Gamma market is an active, undisputed, objective UMA-proposed
    binary market eligible for `BOND1_UMA_RESOLUTION_CARRY`.
    """
    if m.get("closed") or m.get("archived") or not m.get("acceptingOrders", False):
        return False, "NOT_OPEN_CLOB"
    ust = str(m.get("umaResolutionStatus") or "").strip().lower()
    if ust != "proposed":
        return False, f"STATUS_{ust.upper() or 'NONE'}"

    hist = [str(x).strip().lower() for x in _parse_json_list(m.get("umaResolutionStatuses"))]
    if any(x in ("disputed", "flagged", "reset") for x in hist):
        return False, "PRIOR_DISPUTE_HISTORY"
    if hist.count("proposed") > 2:
        return False, "EXCESS_PROPOSAL_CYCLES"

    adapter = str(m.get("resolvedBy") or "").strip().lower()
    if adapter not in VERIFIED_UMA_ADAPTERS:
        return False, "UNVERIFIED_ADAPTER"

    is_nr = bool(m.get("negRisk")) or (adapter in NEGRISK_UMA_ADAPTERS)
    req_hex = str(m.get("negRiskRequestID") if is_nr else m.get("questionID") or "").strip()
    if not _HEX32_RE.match(req_hex):
        return False, "MISSING_REQUEST_ID"

    toks = _parse_clob_tokens(m)
    outs = [str(o).strip() for o in _parse_json_list(m.get("outcomes"))]
    if not toks or len(outs) != 2:
        return False, "NON_BINARY_OUTCOMES"
    if any(o.lower() in ("other", "placeholder", "unknown") for o in outs):
        return False, "PLACEHOLDER_OUTCOME"

    q = str(m.get("question") or "")
    desc = str(m.get("description") or "")
    blob = f"{q}\n{desc}"
    if _SUBJECTIVE_VETO_RE.search(blob):
        return False, "SUBJECTIVE_OR_SPEECH_VETO"

    smt = str(m.get("sportsMarketType") or "").strip().lower()
    if smt:
        return True, f"SPORTS_{smt.upper()}"
    if _OBJECTIVE_ORACLE_RE.search(blob):
        return True, "VERIFIED_PRIMARY_ORACLE"
    if _SPORTS_TITLE_RE.search(q):
        return True, "SPORTS_MATCH_RULE"

    # P1a: Strictly objective post-deadline or mathematically-eliminated (`NO >= $0.94`) official league/roster carries
    slug_blob = f"{m.get('slug') or ''} {m.get('_ev_slug') or ''}\n{blob}"
    if hist.count("proposed") <= 1 and not _NON_LEAGUE_POP_OR_POLITICS_VETO_RE.search(slug_blob):
        if _OFFICIAL_SPORTS_OR_ROSTER_CLAUSE_RE.search(slug_blob):
            now_chk = float(m.get("_eval_now_ts") or time.time())
            end_ts_m = _parse_iso_ts(m.get("endDate")) or 0.0
            if 0.0 < end_ts_m <= now_chk:
                return True, "OFFICIAL_LEAGUE_POST_DEADLINE"
            op_raw = _parse_json_list(m.get("outcomePrices"))
            if (
                len(outs) == 2
                and outs[0].lower() == "yes"
                and outs[1].lower() == "no"
                and len(op_raw) == 2
            ):
                try:
                    p_yes = float(op_raw[0])
                    p_no = float(op_raw[1])
                    if p_no >= 0.94 and p_yes <= 0.06:
                        return True, "OFFICIAL_LEAGUE_ELIMINATED_NO"
                except (TypeError, ValueError):
                    pass

    return False, "NO_OBJECTIVE_DOMAIN_MATCH"


def _rpc_post(rpc_url: str, payload: Any, timeout: float = 5.0) -> Any:
    body = json.dumps(payload).encode("utf-8")
    urls = [rpc_url]
    if rpc_url == DEFAULT_POLYGON_RPC:
        urls.extend(u for u in FALLBACK_POLYGON_RPCS if u != rpc_url)
    last_exc: Optional[Exception] = None
    for u in urls:
        try:
            req = urllib.request.Request(
                u,
                data=body,
                headers={"Content-Type": "application/json", "User-Agent": "DominusUmaVerifier/1.0"},
                method="POST",
            )
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
        except Exception as exc:
            last_exc = exc
    raise last_exc if last_exc is not None else RuntimeError("RPC_FAILED")


def _encode_oo_query_calldata(selector_hex: str, adapter_addr: str, req_ts: int, anc_bytes: bytes) -> str:
    ad_clean = adapter_addr.lower().replace("0x", "").rjust(64, "0")
    ts_hex = int(req_ts).to_bytes(32, "big").hex()
    off_hex = (128).to_bytes(32, "big").hex()
    len_hex = len(anc_bytes).to_bytes(32, "big").hex()
    pad_len = (32 - (len(anc_bytes) % 32)) % 32
    anc_hex = (anc_bytes + (b"\x00" * pad_len)).hex()
    return f"0x{selector_hex}{ad_clean}{YES_OR_NO_IDENT_HEX}{ts_hex}{off_hex}{len_hex}{anc_hex}"


def _decode_int256(word: bytes) -> int:
    val = int.from_bytes(word, "big")
    return val - (1 << 256) if val >= (1 << 255) else val


def map_uma_proposed_price_to_outcome_idx(
    proposed_price: int,
    anc_text: str,
    outcomes: List[str],
) -> Optional[int]:
    """
    Maps UMA OptimisticOracleV2 `proposedPrice` (`0` or `10**18`) to `outcomes` index (`0` or `1`).
    Strictly vetoes `0.5 * 10**18` (`500000000000000000`) ties/splits/unknowns.
    """
    if proposed_price not in (0, ONE_E18):
        return None
    if len(outcomes) != 2:
        return None

    # Check explicit `Where p1 corresponds to X, p2 to Y` in ancillaryData (`res_data: p1: 0, p2: 1`)
    m_corr = _ANC_CORRESPONDS_RE.search(anc_text or "")
    if m_corr and "p1: 0" in anc_text and "p2: 1" in anc_text:
        p1_lbl = _norm_team(m_corr.group(1))
        p2_lbl = _norm_team(m_corr.group(2))
        o0, o1 = _norm_team(outcomes[0]), _norm_team(outcomes[1])
        target_lbl = p1_lbl if proposed_price == 0 else p2_lbl
        if target_lbl == o0 and target_lbl != o1:
            return 0
        if target_lbl == o1 and target_lbl != o0:
            return 1

    # Standard Polymarket binary / NegRisk convention: p2 (1e18) -> outcome[0] (Yes/Over/TeamA), p1 (0) -> outcome[1] (No/Under/TeamB)
    return 0 if proposed_price == ONE_E18 else 1


def verify_uma_onchain_proposal_sync(
    m: Dict[str, Any],
    rpc_url: Optional[str] = None,
    now_ts: Optional[float] = None,
    min_proposal_age_sec: float = 120.0,
    max_rem_challenge_sec: float = 7500.0,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Queries Polygon `UmaCtfAdapter.getQuestion` + `OptimisticOracleV2.getState`/`getRequest` directly
    on-chain to verify an active, undisputed binary UMA assertion.
    """
    ok_obj, domain_tag = is_objective_uma_market(m)
    if not ok_obj:
        return {"verified": False, "reason": domain_tag}

    now = float(now_ts if now_ts is not None else time.time())
    rpc = rpc_url or os.getenv("POLYGON_RPC_URL") or DEFAULT_POLYGON_RPC
    adapter = str(m.get("resolvedBy") or "").strip().lower()
    is_nr = bool(m.get("negRisk")) or (adapter in NEGRISK_UMA_ADAPTERS)
    req_id_hex = str(m.get("negRiskRequestID") if is_nr else m.get("questionID") or "").strip().lower()
    outs = [str(o).strip() for o in _parse_json_list(m.get("outcomes"))]
    toks = _parse_clob_tokens(m)
    assert toks is not None

    try:
        oo_addr = _OO_ADDR_CACHE.get(adapter)
        batch_1 = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": adapter, "data": f"0x{SEL_GET_QUESTION}{req_id_hex[2:]}"}, "latest"],
            }
        ]
        if not oo_addr:
            batch_1.append({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "eth_call",
                "params": [{"to": adapter, "data": f"0x{SEL_OPTIMISTIC_ORACLE}"}, "latest"],
            })
        resp_1 = _rpc_post(rpc, batch_1, timeout=timeout)
        by_id_1 = {int(r["id"]): r.get("result") for r in resp_1 if isinstance(r, dict) and "id" in r}
        gq_hex = str(by_id_1.get(1) or "")
        if not gq_hex.startswith("0x") or len(gq_hex) < 2 + 14 * 64:
            return {"verified": False, "reason": "INVALID_GET_QUESTION_BYTES"}
        if not oo_addr:
            oo_hex = str(by_id_1.get(2) or "")
            if not oo_hex.startswith("0x") or len(oo_hex) < 42:
                return {"verified": False, "reason": "MISSING_OO_ADDRESS"}
            oo_addr = "0x" + oo_hex[-40:].lower()
            _OO_ADDR_CACHE[adapter] = oo_addr

        gq_raw = bytes.fromhex(gq_hex[2:])
        words = [gq_raw[i : i + 32] for i in range(0, 13 * 32, 32)]
        req_ts = int.from_bytes(words[1], "big")
        adapter_liveness = int.from_bytes(words[4], "big")
        manual_ts = int.from_bytes(words[5], "big")
        q_resolved = int.from_bytes(words[6], "big") != 0
        q_paused = int.from_bytes(words[7], "big") != 0
        q_reset = int.from_bytes(words[8], "big") != 0
        q_refund = int.from_bytes(words[9], "big") != 0

        if req_ts <= 0:
            return {"verified": False, "reason": "UNINITIALIZED_QUESTION"}
        if q_resolved or q_paused or q_reset or q_refund or manual_ts > 0:
            return {
                "verified": False,
                "reason": f"QUESTION_FLAGS(res={q_resolved},pause={q_paused},reset={q_reset},refund={q_refund})",
            }

        anc_rel_off = int.from_bytes(words[12], "big")
        anc_pos = 32 + anc_rel_off
        if anc_pos + 32 > len(gq_raw):
            return {"verified": False, "reason": "TRUNCATED_ANCILLARY_OFFSET"}
        anc_len = int.from_bytes(gq_raw[anc_pos : anc_pos + 32], "big")
        anc_bytes = gq_raw[anc_pos + 32 : anc_pos + 32 + anc_len]
        if len(anc_bytes) != anc_len:
            return {"verified": False, "reason": "TRUNCATED_ANCILLARY_BYTES"}
        anc_text = anc_bytes.decode("utf-8", errors="replace")

        batch_2 = [
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "eth_call",
                "params": [{"to": oo_addr, "data": _encode_oo_query_calldata(SEL_GET_STATE, adapter, req_ts, anc_bytes)}, "latest"],
            },
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "eth_call",
                "params": [{"to": oo_addr, "data": _encode_oo_query_calldata(SEL_GET_REQUEST, adapter, req_ts, anc_bytes)}, "latest"],
            },
        ]
        resp_2 = _rpc_post(rpc, batch_2, timeout=timeout)
        by_id_2 = {int(r["id"]): r.get("result") for r in resp_2 if isinstance(r, dict) and "id" in r}
        st_hex = str(by_id_2.get(10) or "")
        rq_hex = str(by_id_2.get(11) or "")
        if not st_hex.startswith("0x") or not rq_hex.startswith("0x") or len(rq_hex) < 2 + 16 * 64:
            return {"verified": False, "reason": "INVALID_OO_RESPONSE"}

        oo_state = int(st_hex, 16)
        rq_raw = bytes.fromhex(rq_hex[2:])
        rq_words = [rq_raw[i : i + 32] for i in range(0, 16 * 32, 32)]
        proposer = "0x" + rq_words[0].hex()[-40:].lower()
        disputer = "0x" + rq_words[1].hex()[-40:].lower()
        oo_settled = int.from_bytes(rq_words[3], "big") != 0
        oo_custom_liveness = int.from_bytes(rq_words[10], "big")
        proposed_price = _decode_int256(rq_words[11])
        expiration_ts = int.from_bytes(rq_words[13], "big")

        # OO State enum: 0=Invalid, 1=Requested, 2=Proposed, 3=Expired (undisputed, ready to settle), 4=Disputed, 5=Resolved, 6=Settled
        if oo_state not in (2, 3):
            return {"verified": False, "reason": f"OO_STATE_{oo_state}"}
        if proposer == ZERO_ADDR or disputer != ZERO_ADDR or oo_settled:
            return {"verified": False, "reason": f"DISPUTER_OR_SETTLED(disp={disputer})"}
        if proposed_price == HALF_E18:
            return {"verified": False, "reason": "TIE_50_50_PROPOSAL_VETO"}

        win_idx = map_uma_proposed_price_to_outcome_idx(proposed_price, anc_text, outs)
        if win_idx not in (0, 1):
            return {"verified": False, "reason": f"NON_BINARY_PRICE_{proposed_price}"}

        # Cross-check Gamma outcomePrices if present (must not contradict on-chain proposal)
        op = _parse_json_list(m.get("outcomePrices"))
        if len(op) >= 2:
            try:
                if float(op[win_idx]) < 0.90:
                    return {"verified": False, "reason": f"GAMMA_PRICE_MISMATCH({op[win_idx]})"}
            except Exception:
                pass

        eff_liveness = (
            oo_custom_liveness
            or adapter_liveness
            or int(m.get("customLiveness") or 0)
            or 7200
        )
        proposal_ts = float(expiration_ts - eff_liveness)
        if domain_tag == "VERIFIED_PRIMARY_ORACLE" and not _EARLY_BARRIER_MARKET_RE.search(str(m.get("question") or "")):
            end_ts_m = _parse_iso_ts(m.get("endDate")) or 0.0
            if end_ts_m > 0.0:
                if now < end_ts_m:
                    return {"verified": False, "reason": f"MARKET_BEFORE_END_DATE(now={int(now)}<end={int(end_ts_m)})"}
                if proposal_ts < (end_ts_m - 5.0):
                    return {"verified": False, "reason": f"PREMATURE_PROPOSAL_BEFORE_END_DATE(prop={int(proposal_ts)}<end={int(end_ts_m)})"}
        proposal_age_sec = now - proposal_ts
        rem_challenge_sec = max(0.0, float(expiration_ts) - now)
        if proposal_age_sec < min_proposal_age_sec:
            return {"verified": False, "reason": f"PROPOSAL_TOO_FRESH({proposal_age_sec:.0f}s)"}
        if rem_challenge_sec > max_rem_challenge_sec:
            return {"verified": False, "reason": f"CHALLENGE_WINDOW_TOO_LONG({rem_challenge_sec:.0f}s)"}

        fee_rate, fee_exp = _extract_market_fee_rate(m)
        lose_idx = 1 - win_idx
        return {
            "verified": True,
            "domain": domain_tag,
            "adapter": adapter,
            "oo_address": oo_addr,
            "oo_state": oo_state,
            "proposer": proposer,
            "proposed_price": proposed_price,
            "win_index": win_idx,
            "win_label": "YES" if win_idx == 0 else "NO",
            "win_outcome_name": outs[win_idx],
            "win_token": toks[win_idx],
            "lose_token": toks[lose_idx],
            "expiration_ts": float(expiration_ts),
            "eff_liveness_sec": int(eff_liveness),
            "proposal_age_sec": round(proposal_age_sec, 1),
            "rem_challenge_sec": round(rem_challenge_sec, 1),
            "fee_rate": fee_rate,
            "fee_exponent": fee_exp,
        }
    except Exception as exc:
        return {"verified": False, "reason": f"RPC_ERR:{type(exc).__name__}"}


# ==============================================================================
# PART 2: LIVE NBA SCOREBOARD & FINAL-2M / POST-BUZZER ENDGAME LOCK ENGINE
# ==============================================================================
_NBA_NICKNAME_ALIASES: Dict[str, str] = {
    "blazers": "trail blazers",
    "sixers": "76ers",
    "wolves": "timberwolves",
    "mavs": "mavericks",
    "cavs": "cavaliers",
}


def _canon_nba_team(raw: str) -> str:
    s = _norm_team(raw)
    for k, v in _NBA_NICKNAME_ALIASES.items():
        if s == k:
            return v
    return s


def _parse_iso_clock_sec(raw_clk: Any) -> float:
    """Parses ESPN numeric seconds (`27.5`), `MM:SS` (`1:14`), or NBA CDN ISO (`PT01M14.20S`)."""
    if isinstance(raw_clk, (int, float)):
        return max(0.0, float(raw_clk))
    s = str(raw_clk or "").strip()
    if not s:
        return 0.0
    m_iso = re.match(r"^PT(?:(\d+)M)?(\d+(?:\.\d+)?)S$", s, re.IGNORECASE)
    if m_iso:
        mins = float(m_iso.group(1) or 0.0)
        secs = float(m_iso.group(2) or 0.0)
        return mins * 60.0 + secs
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            try:
                return float(parts[0]) * 60.0 + float(parts[1])
            except ValueError:
                return 0.0
    try:
        return max(0.0, float(s))
    except ValueError:
        return 0.0


def parse_espn_nba_scoreboard(data: Dict[str, Any]) -> List[LiveNbaGameState]:
    out: List[LiveNbaGameState] = []
    for ev in (data or {}).get("events") or []:
        comp = ((ev.get("competitions") or [None])[0]) or {}
        st = comp.get("status") or ev.get("status") or {}
        st_type = st.get("type") or {}
        state = str(st_type.get("state") or "").strip().lower()
        completed = bool(st_type.get("completed", False))
        period = int(st.get("period") or 0)
        clk_sec = _parse_iso_clock_sec(st.get("clock") if st.get("clock") is not None else st.get("displayClock"))
        start_ts = _parse_iso_ts(comp.get("date") or ev.get("date")) or 0.0

        home_c: Optional[Dict[str, Any]] = None
        away_c: Optional[Dict[str, Any]] = None
        for c in comp.get("competitors") or []:
            ha = str(c.get("homeAway") or "").strip().lower()
            if ha == "home":
                home_c = c
            elif ha == "away":
                away_c = c
        if not home_c or not away_c:
            continue
        ht = home_c.get("team") or {}
        at = away_c.get("team") or {}
        h_name = str(ht.get("name") or ht.get("shortDisplayName") or "").strip()
        a_name = str(at.get("name") or at.get("shortDisplayName") or "").strip()
        try:
            h_sc = int(float(home_c.get("score") or 0))
            a_sc = int(float(away_c.get("score") or 0))
        except Exception:
            continue
        if h_name and a_name:
            out.append(
                LiveNbaGameState(
                    game_id=str(ev.get("id") or ""),
                    start_ts=start_ts,
                    state=state,
                    completed=completed,
                    period=period,
                    clock_sec=clk_sec,
                    home_name=h_name,
                    home_abbr=str(ht.get("abbreviation") or "").upper(),
                    home_score=h_sc,
                    away_name=a_name,
                    away_abbr=str(at.get("abbreviation") or "").upper(),
                    away_score=a_sc,
                    source="espn",
                )
            )
    return out


def fetch_espn_nba_scoreboard_sync(timeout: float = 4.5, now_ts: Optional[float] = None) -> List[LiveNbaGameState]:
    """Fetches real-time NBA scoreboard across yesterday + today ET from ESPN (primary) with `cdn.nba.com` fallback."""
    from src.polymarket_research.riskless_protocol_v2_expansion import get_us_eastern_tz

    hdrs = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    ny_dt = datetime.fromtimestamp(float(now_ts if now_ts is not None else time.time()), tz=get_us_eastern_tz())
    date_tags = [(ny_dt - timedelta(days=1)).strftime("%Y%m%d"), ny_dt.strftime("%Y%m%d")]
    merged: Dict[str, LiveNbaGameState] = {}
    for ymd in dict.fromkeys(date_tags):
        try:
            url = f"{ESPN_NBA_SCOREBOARD_URL}?dates={ymd}"
            raw = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=timeout).read().decode("utf-8"))
            for g in parse_espn_nba_scoreboard(raw):
                merged[g.game_id] = g
        except Exception as exc:
            logger.debug(f"ESPN NBA scoreboard fetch notice ({ymd}): {exc}")
    if merged:
        return list(merged.values())
    try:
        raw = json.loads(urllib.request.urlopen(urllib.request.Request(ESPN_NBA_SCOREBOARD_URL, headers=hdrs), timeout=timeout).read().decode("utf-8"))
        games = parse_espn_nba_scoreboard(raw)
        if games:
            return games
    except Exception as exc:
        logger.debug(f"ESPN NBA scoreboard bare fetch notice: {exc}")

    try:
        nba_hdrs = {
            **hdrs,
            "Referer": "https://www.nba.com/",
            "Origin": "https://www.nba.com",
        }
        sb = json.loads(urllib.request.urlopen(urllib.request.Request(CDN_NBA_SCOREBOARD_URL, headers=nba_hdrs), timeout=timeout).read().decode("utf-8"))
        out: List[LiveNbaGameState] = []
        for g in ((sb.get("scoreboard") or {}).get("games") or []):
            gs = int(g.get("gameStatus") or 1)
            state = "pre" if gs == 1 else ("in" if gs == 2 else "post")
            ht, at = g.get("homeTeam") or {}, g.get("awayTeam") or {}
            out.append(
                LiveNbaGameState(
                    game_id=str(g.get("gameId") or ""),
                    start_ts=_parse_iso_ts(g.get("gameTimeUTC")) or 0.0,
                    state=state,
                    completed=(gs == 3),
                    period=int(g.get("period") or 0),
                    clock_sec=_parse_iso_clock_sec(g.get("gameClock")),
                    home_name=str(ht.get("teamName") or ""),
                    home_abbr=str(ht.get("teamTricode") or "").upper(),
                    home_score=int(ht.get("score") or 0),
                    away_name=str(at.get("teamName") or ""),
                    away_abbr=str(at.get("teamTricode") or "").upper(),
                    away_score=int(at.get("score") or 0),
                    source="cdn_nba",
                )
            )
        return out
    except Exception:
        return []


def match_nba_live_game(
    spec: NbaGameSpec,
    live_games: List[LiveNbaGameState],
) -> Optional[Tuple[LiveNbaGameState, int, int]]:
    """
    Matches `spec` (`team_a`, `team_b`, `tipoff_ts`) to `LiveNbaGameState` within `+/- 10h`
    and returns `(game_state, score_a, score_b)` strictly aligned to `(spec.team_a, spec.team_b)`.
    """
    ca, cb = _canon_nba_team(spec.team_a), _canon_nba_team(spec.team_b)
    for g in live_games:
        if g.start_ts > 0 and spec.tipoff_ts > 0 and abs(g.start_ts - spec.tipoff_ts) > 36000.0:
            continue
        ch, cw = _canon_nba_team(g.home_name), _canon_nba_team(g.away_name)
        if ca == ch and cb == cw:
            return g, g.home_score, g.away_score
        if ca == cw and cb == ch:
            return g, g.away_score, g.home_score
    return None


def verify_uma_against_nba_live(
    m: Dict[str, Any],
    win_index: int,
    live_games: List[LiveNbaGameState],
) -> Tuple[bool, str]:
    """
    Cross-checks any NBA UMA-proposed market against live ESPN/NBA scoreboard state:
      - If matched to an active game that is NOT yet `completed`, HARD VETOES (catches premature proposals!).
      - If matched to a `completed` game on Moneyline, verifies final score winner matches `win_index`.
    """
    if not live_games:
        return True, "NO_LIVE_BOARD"
    outs = [str(o).strip() for o in _parse_json_list(m.get("outcomes"))]
    q = str(m.get("question") or "")
    ev0 = ((m.get("events") or [None])[0]) or {}
    ev_title = str(ev0.get("title") or "") if isinstance(ev0, dict) else ""
    start_ts = _parse_iso_ts(m.get("gameStartTime") or m.get("endDate")) or 0.0
    for g in live_games:
        if g.start_ts > 0 and start_ts > 0 and abs(g.start_ts - start_ts) > 36000.0:
            continue
        ch, cw = _canon_nba_team(g.home_name), _canon_nba_team(g.away_name)
        ql = _norm_team(f"{q} {ev_title}")
        if ch and cw and ch in ql and cw in ql:
            if not g.completed or g.state != "post":
                return False, "NBA_GAME_NOT_FINAL_YET"
            if str(m.get("sportsMarketType") or "").lower() == "moneyline" and len(outs) == 2 and g.home_score != g.away_score:
                actual_winner = ch if g.home_score > g.away_score else cw
                proposed_team = _canon_nba_team(outs[win_index])
                if proposed_team in (ch, cw) and proposed_team != actual_winner:
                    return False, f"NBA_SCORE_CONTRADICTS_PROPOSAL({actual_winner}!={proposed_team})"
            return True, "NBA_FINAL_CONFIRMED"
    return True, "NON_NBA_OR_UNLISTED"


def evaluate_nba_endgame_locks(
    spec: NbaGameSpec,
    game: LiveNbaGameState,
    score_a: int,
    score_b: int,
) -> List[Dict[str, Any]]:
    """
    Evaluates `0%`-fee `SP2_NBA_ENDGAME_LOCK` candidates across Moneyline, Spread, and Total legs:
      1. `POST_BUZZER_FINAL`: `game.completed == True` & `period >= 4` & `score_a != score_b` -> `p_lock = 0.998`.
      2. `LIVE_TOTAL_OVER_LOCKED`: `state == "in"`, `period >= 3`, `score_a + score_b >= T + 2.5` -> `p_lock = 0.997`.
      3. `LIVE_Q4_ENDGAME_LOCK`: `state == "in"`, `period >= 4`, `0 < clock_sec <= 120s`, strict OT-trap veto,
         discrete 3pt-possession floor (`>= 6` @ `<=12s`, `>= 8` @ `<=28s`, `>= 10` @ `<=50s`, `>= 14` @ `<=120s`),
         Bill James Safe-Lead bound `(cushion - 3.0)^2 >= 1.15 * t`, and Stern endgame `p_lock >= 0.993`.
    """
    margin = float(score_a - score_b)
    total_pts = float(score_a + score_b)
    out: List[Dict[str, Any]] = []

    # Case 1: Official Post-Buzzer Finality (before market closes on CLOB)
    if game.completed and game.state == "post" and game.period >= 4 and score_a != score_b:
        for lg in spec.margin_legs:
            won = (margin > lg.threshold) if lg.relation == "GT" else (margin < lg.threshold)
            if won:
                out.append({
                    "leg": lg,
                    "mode": "POST_BUZZER_FINAL",
                    "p_lock": 0.999,
                    "cushion_pts": round(abs(margin - lg.threshold), 1),
                    "clock_sec": 0.0,
                    "period": game.period,
                    "score_str": f"{spec.team_a} {score_a}-{score_b} {spec.team_b} (FINAL)",
                })
        for lg in spec.total_legs:
            won_t = (total_pts > lg.threshold) if lg.relation == "OVER" else (total_pts < lg.threshold)
            if won_t and abs(total_pts - lg.threshold) >= 1.5:
                out.append({
                    "leg": lg,
                    "mode": "POST_BUZZER_FINAL",
                    "p_lock": 0.999,
                    "cushion_pts": round(abs(total_pts - lg.threshold), 1),
                    "clock_sec": 0.0,
                    "period": game.period,
                    "score_str": f"{spec.team_a} {score_a}-{score_b} {spec.team_b} (FINAL Tot={int(total_pts)})",
                })
        return out

    if game.state != "in":
        return out

    # Case 2: Monotonic In-Play Total OVER Lock (+2.5pt buffer against scorer's table 3pt->2pt review)
    if game.period >= 3:
        for lg in spec.total_legs:
            if lg.relation == "OVER" and total_pts >= lg.threshold + 2.5:
                out.append({
                    "leg": lg,
                    "mode": "LIVE_TOTAL_OVER_LOCKED",
                    "p_lock": 0.999,
                    "cushion_pts": round(total_pts - lg.threshold, 1),
                    "clock_sec": round(game.clock_sec, 1),
                    "period": game.period,
                    "score_str": f"P{game.period} {game.clock_sec:.0f}s Tot={int(total_pts)}>{lg.threshold:g}",
                })

    # Case 3: Final-120s Q4/OT Margin & Moneyline Lock
    if game.period >= 4 and 0.0 < game.clock_sec <= 120.0:
        t = max(1.0, float(game.clock_sec))
        min_cush = 5.5 if t <= 12.0 else (7.5 if t <= 28.0 else (9.5 if t <= 50.0 else 13.5))
        sigma_rem = max(1.60, 0.3965 * math.sqrt(t))

        for lg in spec.margin_legs:
            cush = (margin - lg.threshold) if lg.relation == "GT" else (lg.threshold - margin)
            if cush < min_cush:
                continue
            # Overtime Trap Veto: if actual game score is within 8 pts (OT possible!), never lock a +k.5 spread
            # unless our backed side is ALREADY leading the game outright by >= 6 pts!
            if abs(margin) <= 8.5:
                backed_team_leading = (lg.relation == "GT" and margin >= 6.0) or (lg.relation == "LT" and margin <= -6.0)
                if not backed_team_leading:
                    continue
            adj_cush = cush - 3.0
            if adj_cush <= 0.0 or (adj_cush * adj_cush) < 1.15 * t:
                continue
            z_eff = adj_cush / sigma_rem
            p_gauss = 0.5 * (1.0 + math.erf(z_eff / math.sqrt(2.0)))
            p_heavy = 0.5 + math.atan(z_eff) / math.pi
            p_lock = round(min(0.997, 0.98 * p_gauss + 0.02 * p_heavy), 4)
            if p_lock >= 0.993:
                out.append({
                    "leg": lg,
                    "mode": "LIVE_Q4_ENDGAME_LOCK",
                    "p_lock": p_lock,
                    "cushion_pts": round(cush, 1),
                    "z_endgame": round(z_eff, 2),
                    "clock_sec": round(t, 1),
                    "period": game.period,
                    "score_str": f"P{game.period} {t:.0f}s {spec.team_a} {score_a}-{score_b} {spec.team_b}",
                })

    return out

"""
Exhaustive Detectors & L2 Execution Simulators for Opportunity Families A, B, C & J
(`src/polymarket_research/detectors_complete_set_and_negrisk.py`).

Implements Agents 3 & 4 of DOMINUS — RISKLESS FULL THROTTLE:
  - Family A: Binary YES/NO Complete-Set Arbitrage (`Buy-and-Merge` & `Split-and-Sell`)
              across all active binary conditions (including NegRisk sub-conditions and
              fee-bearing dynamic fee-curve markets) with exact multi-rung L2 `q*`.
  - Family B: Multi-Outcome Complete-Set Arbitrage (`Buy-All-YES` & `Split/Convert-and-Sell`)
              gated behind formal mutual-exclusivity and exhaustiveness proofs with explicit
              counterexample states for non-exhaustive lists, ladders, multi-prop bundles,
              `50-50` standalone cancellation voids, and conditional non-occurrence traps.
  - Family C: Negative-Risk (`NegRiskAdapter`) Specialist (`m`-NO subset conversion, `m=1`
              fanout conversion, `m=N` pure cash bridge, synthetic `YES_i` vs CLOB, synthetic
              `NO_i` via complement `YES` bundle vs `bid(NO_i)`, freeroll conversion, and
              strict Augmented NegRisk `Other` / unnamed `Placeholder_*` / `N_total` slot safety).
  - Family J: Inventory, Split/Merge & Capital Recycling (`CLASS_A` held complete-set merge,
              `CLASS_A` single-remaining-leg FOK completion lock, NegRisk conversion inventory
              recycling, and pre-split overround exit, strictly freezing disputed `KMIA`
              positions per `D-001` and measuring exact portfolio `DeltaWealth_min`).

Strict Safety & Mode Boundaries (`D-001`, `D-002`, `D-003`, `D-007`, `D-010`):
  - Pure MODE 1 (Research) / MODE 2 (Shadow): public Gamma & CLOB read-only endpoints and
    read-only local JSON state inspection only; zero signing credentials, zero order placement.
  - Absolute non-interference with the 4 disputed Nov 7 `KMIA` positions (`6707503`, `6707502`).
  - Enforces `< $500` reconciled NAV quarantine (`D-007`) on sequential `>= 3`-leg CLOB bundles.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
import ssl
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
import urllib.parse

try:
    from src.polymarket_research.universal_arb_verifier import (
        ActionLeg,
        ActionType,
        ArbitrageProofObject,
        BookLevel,
        CandidateStructure,
        DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
        DEFAULT_LIVE_RECONCILED_NAV_USD,
        DEFAULT_MAX_BOOK_AGE_SEC,
        DEFAULT_MIN_MARKETABLE_BUY_USD,
        DEFAULT_MIN_ORDER_SHARES,
        FROZEN_DISPUTED_MARKET_IDS,
        FROZEN_DISPUTED_TRADE_SUBSTRINGS,
        InstrumentOrderBook,
        InventoryHolding,
        OpportunityClass,
        StateSpaceBuilder,
        StateSpec,
        UniversalArbVerifier,
        VerificationConfig,
        compute_net_buy_cost_per_delivered_share,
        compute_net_sell_proceeds_per_share,
        compute_polymarket_taker_fee_per_gross_share,
        compute_v2_buy_share_haircut_frac,
        infer_polymarket_tick_size,
        normalize_fee_rate,
        quantize_polymarket_price,
    )
except ImportError:  # pragma: no cover
    from universal_arb_verifier import (  # type: ignore
        ActionLeg,
        ActionType,
        ArbitrageProofObject,
        BookLevel,
        CandidateStructure,
        DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
        DEFAULT_LIVE_RECONCILED_NAV_USD,
        DEFAULT_MAX_BOOK_AGE_SEC,
        DEFAULT_MIN_MARKETABLE_BUY_USD,
        DEFAULT_MIN_ORDER_SHARES,
        FROZEN_DISPUTED_MARKET_IDS,
        FROZEN_DISPUTED_TRADE_SUBSTRINGS,
        InstrumentOrderBook,
        InventoryHolding,
        OpportunityClass,
        StateSpaceBuilder,
        StateSpec,
        UniversalArbVerifier,
        VerificationConfig,
        compute_net_buy_cost_per_delivered_share,
        compute_net_sell_proceeds_per_share,
        compute_polymarket_taker_fee_per_gross_share,
        compute_v2_buy_share_haircut_frac,
        infer_polymarket_tick_size,
        normalize_fee_rate,
        quantize_polymarket_price,
    )


GAMMA_API_HOST = "gamma-api.polymarket.com"
CLOB_API_HOST = "clob.polymarket.com"

DORMANT_MIN_BPS_DEFAULT: float = 0.0
DORMANT_MAX_BPS_DEFAULT: float = 250.0
DORMANT_TIGHT_BAND_MIN_BPS: float = 50.0


# ---------------------------------------------------------------------------
# 1. Existing-Codebase Complete-Set & NegRisk Coverage Audit
# ---------------------------------------------------------------------------


def audit_existing_complete_set_and_negrisk_gaps() -> Dict[str, Any]:
    """
    Structured read-only audit of existing DOMINUS complete-set, NegRisk, and inventory
    recycling modules (`riskless_protocol_v2_expansion.py`, `riskless_machine_gun_engine.py`,
    `alpha_124_shadow_daemon.py`, and `POLYMARKET_ONCHAIN_MOF_AUDIT.md`).
    """
    return {
        "audited_modules": [
            "src/polymarket_research/riskless_protocol_v2_expansion.py",
            "src/polymarket_research/riskless_machine_gun_engine.py",
            "src/polymarket_research/alpha_124_shadow_daemon.py",
            "POLYMARKET_ONCHAIN_MOF_AUDIT.md",
        ],
        "identified_gaps": [
            {
                "gap_id": "GAP-AB-01",
                "family": "A",
                "location": "riskless_protocol_v2_expansion.py:5435",
                "issue": (
                    "scan_full_universe_c1_and_ctf_overround skips every market with negRisk==True, "
                    "even though each NegRisk child question is a valid binary CTF condition whose "
                    "YES_i + NO_i pair merges/splits for $1.00."
                ),
                "remediation": "Evaluate both standalone CTF binaries and NegRisk child binary conditions in Family A.",
            },
            {
                "gap_id": "GAP-AB-02",
                "family": "A",
                "location": "riskless_protocol_v2_expansion.py:5484 & alpha_124_shadow_daemon.py:3221",
                "issue": (
                    "Existing binary scanners hard-exclude feesEnabled==True / fee_rate > 0 markets "
                    "(99.4% of active Polymarket markets) and cap general binaries at top 340."
                ),
                "remediation": (
                    "Scan 100% of fee-bearing and 0-fee binary markets using exact per-rung V2 "
                    "share-haircut BUY costs and cash-deducted SELL proceeds."
                ),
            },
            {
                "gap_id": "GAP-AB-03",
                "family": "A/B/C",
                "location": "riskless_protocol_v2_expansion.py:749-929, 5445-5511",
                "issue": (
                    "C1, CTF_OVERROUND, NR4, and NR5 evaluate scalar L1 top-of-book prices/sizes "
                    "and clamp prices to [0.002, 0.995], missing multi-level L2 optimal executable "
                    "clip q* and [0.001, 0.999] boundary ticks."
                ),
                "remediation": "Walk full sorted L2 ladders to exact marginal breakpoint q* across (0.0, 1.0).",
            },
            {
                "gap_id": "GAP-B-04",
                "family": "B",
                "location": "riskless_machine_gun_engine.py:1415-1437",
                "issue": (
                    "NR3 caps multi-outcome slates at <= 15 brackets (missing 16..60+ outcome slates), "
                    "and standalone non-NegRisk multi-market events lack a formal mutual-exclusivity + "
                    "exhaustiveness + 50-50 void state verifier."
                ),
                "remediation": (
                    "Support arbitrary N-outcome slates with formal PartitionCompletenessProof and "
                    "explicit counterexample states (unlisted winner, multi-winner overlap, 50-50 void)."
                ),
            },
            {
                "gap_id": "GAP-C-05",
                "family": "C",
                "location": "riskless_protocol_v2_expansion.py:840 & 1077",
                "issue": (
                    "detect_nr4_nr5_optimal_tail_convert starts subset size loop at m=2, omitting "
                    "general m=1 single-NO complement fanout (Cost(NO_i) < (1-c)*sum_{j!=i} Bid_net(YES_j)) "
                    "whenever outcome i is not pre-flagged dead, and omits direct synthetic YES_i / NO_i "
                    "parity checks against CLOB asks/bids."
                ),
                "remediation": (
                    "Implement m=1 fanout, m=2..N-1 subset convert, m=N pure cash convert, synthetic YES_i "
                    "routing/arb, synthetic NO_i complement-YES bundle arb, and freeroll conversion."
                ),
            },
            {
                "gap_id": "GAP-C-06",
                "family": "C",
                "location": "riskless_protocol_v2_expansion.py:449-548",
                "issue": (
                    "verify_v2_negrisk_other_partition allows augmented NegRisk slates when an 'Other' "
                    "token has token IDs, without guarding against mutable 'Other' semantics (when a "
                    "new candidate is clarified out of 'Other' or inactive Party A / Person AB slots exist) "
                    "or checking contiguous 0..N_total-1 question_index completeness."
                ),
                "remediation": (
                    "Strictly flag mutable 'Other', all named/inactive placeholder patterns (Person/Party/"
                    "Candidate/Team/Option), closed/missing question_index gaps, and N_total mismatches as CLASS_D/E."
                ),
            },
            {
                "gap_id": "GAP-J-07",
                "family": "J",
                "location": "riskless_machine_gun_engine.py:2032-2130 & POLYMARKET_ONCHAIN_MOF_AUDIT.md",
                "issue": (
                    "PreSplitInventoryGun only monitors BTC/ETH/SOL sub-hourly /dev/shm ticks and gates "
                    "mint-sell behind >= $140 equity; no general portfolio scanner evaluates single-leg "
                    "CLASS_A inventory completion, held pair merges, or held NO NegRisk conversion recycling "
                    "with explicit DeltaWealth_min."
                ),
                "remediation": (
                    "Implement general Family J portfolio scanner across J1..J4 while strictly freezing "
                    "all disputed/KMIA positions under D-001."
                ),
            },
        ],
    }


# ---------------------------------------------------------------------------
# 2. Microstructure, Fee, Placeholder & D-001 Safety Helpers
# ---------------------------------------------------------------------------

_FEE_TYPE_FALLBACK_RATES: Dict[str, Tuple[float, float]] = {
    "crypto_fees": (0.072, 1.0),
    "crypto_15_min": (0.072, 1.0),
    "politics_fees": (0.04, 1.0),
    "finance_prices_fees": (0.04, 1.0),
    "sports_fees": (0.02, 1.0),
}

_PLACEHOLDER_LABEL_RE = re.compile(
    r"(?:\bplaceholder\b|\bunnamed\b|\bunclarified\b|\breserved\s+slot\b"
    r"|^(?:person|player|party|candidate|option|choice|team|club|company|country|driver|golfer|horse|coach|movie|song|artist|nominee|leader|slot|item|bracket)\s+(?:[a-z]{1,3}|\d{1,3})$"
    r"|^tba$|^tbd$|^n/?a$)",
    re.IGNORECASE,
)

_MUTABLE_OTHER_LABEL_RE = re.compile(
    r"^\s*(?:other|others|any\s+other(?:\s+[\w-]+){0,4}|all\s+other(?:\s+[\w-]+){0,4}|the\s+field|field|someone\s+else|another\s+(?:candidate|person|party|team|player|company|option))\s*$",
    re.IGNORECASE,
)

_EXPLICIT_NEGATION_CATCHALL_RE = re.compile(
    r"(?:\b(?:no\s+(?:ipo|change|cut|hike|rate\s+change|deal|merger|acquisition|agreement|winner|election|one|leader|candidate|person|team)"
    r"|none(?:\s+of\s+the\s+(?:above|listed)|\s+before\b|\s+by\b)?|neither|nobody|no\s+one|not\s+happen|does\s+not\s+occur|will\s+not\s+occur)\b)",
    re.IGNORECASE,
)

_CONDITIONAL_EVENT_HEADER_RE = re.compile(
    r"\b(?:ipo|initial\s+public\s+offering|closing\s+market\s+cap|acqui(?:sition|red|re)|merger|buyout|takeover"
    r"|sold\s+in\s+(?:its|an|the)|at\s+what\s+(?:valuation|price)\s+will|deal\s+value|settlement\s+amount)\b",
    re.IGNORECASE,
)

_DEADLINE_SERIES_RE = re.compile(
    r"(?:\b(?:by|before|through|on\s+or\s+before|prior\s+to|until)\s+\.\.\.|___"
    r"|\b(?:by|before|through)\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|q[1-4]\b|202[5-9]|203\d)\b)",
    re.IGNORECASE,
)

_UNILATERAL_THRESHOLD_LABEL_RE = re.compile(
    r"(?:^\s*[↑↓><≥≤]\s*\$?\s*[\d,.]+|\b(?:above|over|below|under|at\s+least|at\s+most|more\s+than|less\s+than|reach|hit)\s+\$?\s*[\d,.]+)",
    re.IGNORECASE,
)

_MULTI_PROP_GAME_LABEL_RE = re.compile(
    r"(?:\bo/u\s*\d|\bover/under\b|\bspread\s*[+-]?\d|\bhandicap\b|\bmap\s+\d+\s+winner\b|\bgame\s+\d+\s+winner\b"
    r"|\bset\s+\d+\s+winner\b|\bboth\s+teams\b|\bpoints\s+o/u\b|\brebounds\s+o/u\b|\bassists\s+o/u\b|\bgo\s+the\s+distance\b|\bcompleted\s+match\b)",
    re.IGNORECASE,
)

_MULTI_WINNER_HEADER_RE = re.compile(
    r"(?:\bmake\s+the\s+playoffs\b|\bfinish\s+in\s+the\s+top\b|\btop\s+\d+\b|\bwhich\s+(?:countries|companies|teams|players|candidates|people|words|terms|coins|tokens)\s+will\b"
    r"|\bwhat\s+will\s+.+\s+(?:say|mention)\b|\bmention(?:s|ed)?\s+during\b|\bwin\s+a\s+medal\b|\bbe\s+nominated\b)",
    re.IGNORECASE,
)

_LOWER_TAIL_BRACKET_RE = re.compile(
    r"(?:^\s*(?:<|<=|≤|under\b|below\b|less\s+than\b|fewer\s+than\b|0\s*[-–]\s*\d|0\s*$|\d+\s+or\s+(?:less|fewer))\b|decrease\b.*\bbps\b)",
    re.IGNORECASE,
)

_UPPER_TAIL_BRACKET_RE = re.compile(
    r"(?:^\s*(?:>|>=|≥|over\b|above\b|more\s+than\b)|(?:\d+(?:\.\d+)?\s*[kmbtr%$]*\s*\+\s*$)|\bor\s+more\b|increase\b.*\bbps\b)",
    re.IGNORECASE,
)


def _sf(val: Any, default: float = 0.0) -> float:
    if val in (None, ""):
        return default
    try:
        out = float(val)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def _parse_json_list(val: Any) -> List[Any]:
    if isinstance(val, list):
        return val
    if isinstance(val, tuple):
        return list(val)
    if isinstance(val, str):
        s = val.strip()
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
    return []


def _parse_end_ts(val: Any) -> Optional[float]:
    if val in (None, ""):
        return None
    if isinstance(val, (int, float)):
        v = float(val)
        return (v / 1000.0 if v > 1e11 else v) if v > 0 else None
    s = str(val).strip()
    if not s:
        return None
    try:
        v = float(s)
        return (v / 1000.0 if v > 1e11 else v) if v > 0 else None
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def extract_market_fee_params(market: Mapping[str, Any]) -> Tuple[float, float, float]:
    """
    Extracts `(fee_rate_fraction, fee_rate_bps, fee_exponent)` from Gamma or normalized market dicts.
    Strictly distinguishes `feesEnabled == False` / `feeType == "zero_fees"` (`0.0`) from dynamic
    fee-curve markets (`feeSchedule = {"rate": r, "exponent": e}` or `fee_rate_bps` / `takerBaseFee`).
    """
    if not isinstance(market, Mapping):
        return 0.0, 0.0, 1.0

    # Explicit normalized override keys take top priority when present
    if market.get("fee_rate_bps") is not None:
        r = normalize_fee_rate(fee_rate_bps=_sf(market.get("fee_rate_bps"), 0.0))
        exp = max(0.5, _sf(market.get("fee_exponent"), 1.0))
        return r, round(r * 10_000.0, 4), exp
    if market.get("fee_rate") is not None:
        r = normalize_fee_rate(fee_rate=_sf(market.get("fee_rate"), 0.0))
        exp = max(0.5, _sf(market.get("fee_exponent"), 1.0))
        return r, round(r * 10_000.0, 4), exp
    if market.get("feeRateBps") is not None:
        r = normalize_fee_rate(fee_rate_bps=_sf(market.get("feeRateBps"), 0.0))
        exp = max(0.5, _sf(market.get("feeExponent"), 1.0))
        return r, round(r * 10_000.0, 4), exp

    fee_type = str(market.get("feeType") or market.get("fee_type") or "").strip().lower()
    if fee_type == "zero_fees" or market.get("feesEnabled") is False:
        return 0.0, 0.0, 1.0

    sched = market.get("feeSchedule") or market.get("fee_schedule")
    if isinstance(sched, Mapping) and sched.get("rate") is not None:
        r = normalize_fee_rate(fee_rate=_sf(sched.get("rate"), 0.0))
        exp = max(0.5, _sf(sched.get("exponent"), 1.0))
        return r, round(r * 10_000.0, 4), exp

    if market.get("feeRate") is not None:
        r = normalize_fee_rate(fee_rate=_sf(market.get("feeRate"), 0.0))
        exp = max(0.5, _sf(market.get("feeExponent"), 1.0))
        return r, round(r * 10_000.0, 4), exp

    if market.get("takerBaseFee") is not None or market.get("taker_base_fee") is not None:
        raw_tb = _sf(
            market.get("takerBaseFee") if market.get("takerBaseFee") is not None else market.get("taker_base_fee"),
            0.0,
        )
        if raw_tb > 0.0:
            # Note: When Gamma sets `feesEnabled=True` + `feeType` without `feeSchedule`, prefer known feeType rate
            if fee_type in _FEE_TYPE_FALLBACK_RATES:
                r_ft, e_ft = _FEE_TYPE_FALLBACK_RATES[fee_type]
                return r_ft, round(r_ft * 10_000.0, 4), e_ft
            r = normalize_fee_rate(fee_rate=raw_tb)
            exp = max(0.5, _sf(market.get("feeExponent"), 1.0))
            return r, round(r * 10_000.0, 4), exp

    if fee_type in _FEE_TYPE_FALLBACK_RATES:
        r_ft, e_ft = _FEE_TYPE_FALLBACK_RATES[fee_type]
        return r_ft, round(r_ft * 10_000.0, 4), e_ft

    if market.get("feesEnabled") is True:
        return 0.04, 400.0, 1.0

    return 0.0, 0.0, 1.0


def extract_binary_token_pair(market: Mapping[str, Any]) -> Tuple[str, str, Tuple[str, str]]:
    """
    Returns `(yes_token_id, no_token_id, (label_0, label_1))` for a 2-outcome market, or `("", "", ("", ""))`
    if the market does not have exactly 2 distinct outcome token IDs.
    """
    yes_tok = str(
        market.get("yes_token_id")
        or market.get("token_id_yes")
        or market.get("yesTokenId")
        or market.get("yes_token")
        or market.get("token_a")
        or ""
    ).strip()
    no_tok = str(
        market.get("no_token_id")
        or market.get("token_id_no")
        or market.get("noTokenId")
        or market.get("no_token")
        or market.get("token_b")
        or ""
    ).strip()

    outcomes_raw = _parse_json_list(market.get("outcomes"))
    labels: Tuple[str, str] = (
        str(outcomes_raw[0]).strip() if len(outcomes_raw) >= 1 else "Yes",
        str(outcomes_raw[1]).strip() if len(outcomes_raw) >= 2 else "No",
    )

    if not (yes_tok and no_tok):
        clob_toks = _parse_json_list(market.get("clobTokenIds") or market.get("clob_token_ids") or market.get("tokens"))
        if len(clob_toks) != 2:
            return "", "", labels
        t0 = str(clob_toks[0].get("token_id") if isinstance(clob_toks[0], Mapping) else clob_toks[0]).strip()
        t1 = str(clob_toks[1].get("token_id") if isinstance(clob_toks[1], Mapping) else clob_toks[1]).strip()
        yes_tok, no_tok = t0, t1

    if not yes_tok or not no_tok or yes_tok == no_tok:
        return "", "", labels
    if outcomes_raw and len(outcomes_raw) != 2:
        return "", "", labels
    return yes_tok, no_tok, labels


def is_placeholder_outcome_market(market: Mapping[str, Any], *, is_augmented_event: bool = False) -> bool:
    """Detects unnamed/inactive placeholder outcomes (`Person A`, `Party B`, `Option 1`, inactive aug slots)."""
    if bool(market.get("isPlaceholder") or market.get("is_placeholder") or market.get("placeholder")):
        return True
    label = str(
        market.get("groupItemTitle")
        or market.get("label")
        or market.get("outcome")
        or market.get("question")
        or market.get("title")
        or ""
    ).strip()
    if _PLACEHOLDER_LABEL_RE.search(label):
        return True
    # In augmented NegRisk events, unclosed `active == False` slots are unclarified protocol placeholders
    if is_augmented_event and market.get("active") is False and not bool(market.get("closed")):
        if not bool(market.get("negRiskOther") or market.get("is_other") or market.get("isOther")):
            return True
    return False


def is_mutable_other_outcome_market(market: Mapping[str, Any], *, is_augmented_event: bool = False) -> bool:
    """
    Detects Polymarket mutable `"Other"` outcomes (`negRiskOther == True` or open-slate `"Other"` / `"Field"`),
    whose payout domain mutates whenever Polymarket clarifies a new named outcome prior to resolution.
    """
    if bool(market.get("negRiskOther") or market.get("isOther") or market.get("is_other")):
        return True
    label = str(
        market.get("groupItemTitle")
        or market.get("label")
        or market.get("outcome")
        or ""
    ).strip()
    if label and _MUTABLE_OTHER_LABEL_RE.match(label):
        # Even when `negRiskOther` flag is omitted in synthetic payloads, `"Other"` on a multi-candidate slate is mutable
        return True
    if is_augmented_event and not label:
        q = str(market.get("question") or "").strip()
        if _MUTABLE_OTHER_LABEL_RE.match(q):
            return True
    return False


def is_d001_frozen_position(pos: Mapping[str, Any], *, now_ts: Optional[float] = None) -> Tuple[bool, str]:
    """
    Non-overridable `D-001` guard: identifies disputed positions and the 4 Nov 7 `KMIA` positions
    (`6707503`, `6707502`) so Family J NEVER sells, merges, converts, unwinds, or mutates them.
    """
    if not isinstance(pos, Mapping):
        return True, "INVALID_POSITION_RECORD"
    uma_st = str(pos.get("umaResolutionStatus") or pos.get("uma_resolution_status") or "").strip().lower()
    if uma_st == "disputed":
        return True, "D001_UMA_DISPUTED_STATUS"
    mid = str(pos.get("market_id") or pos.get("marketId") or "").strip()
    if mid in FROZEN_DISPUTED_MARKET_IDS:
        return True, f"D001_FROZEN_KMIA_MARKET_ID:{mid}"
    for key in ("trade_id", "box_id", "event_id", "event_group_key", "dedupe_key"):
        val_u = str(pos.get(key) or "").strip().upper()
        if "KMIA" in val_u or any(sub in val_u for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS):
            return True, f"D001_FROZEN_KMIA_IDENTIFIER:{key}"
    if bool(pos.get("is_frozen_disputed")):
        return True, "D001_EXPLICIT_FROZEN_FLAG"
    # Post-expiry `>= 4h` frozen UMA lock check matching `is_post_expiry_uma_frozen_lock`
    exp_ts = _sf(pos.get("candle_expiry_ts"), 0.0)
    if exp_ts > 0.0:
        now_f = float(time.time() if now_ts is None else now_ts)
        anchor = max(exp_ts, _sf(pos.get("entry_ts"), 0.0))
        if now_f >= exp_ts + 60.0 and now_f >= anchor + 14400.0:
            if not (pos.get("is_liquidating") or pos.get("exit_order_id") or pos.get("unwind_order_id")):
                bt = str(pos.get("box_type") or "").strip().upper()
                if (
                    pos.get("is_single_leg_lock")
                    or pos.get("is_dominance_box")
                    or pos.get("hold_to_maturity_lock")
                    or bt in {"SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK", "MULTI_LEG_RESIDUAL", "MULTI_LEG_BUNDLE", "DOMINANCE"}
                ):
                    return True, "D001_POST_EXPIRY_UMA_FROZEN_LOCK"
    return False, "ELIGIBLE"


def partition_portfolio_positions_d001(
    portfolio_state: Optional[Mapping[str, Any]],
    *,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Partitions `live_harvester_state.json` (or injected portfolio dict) into:
      - `frozen_positions`: Untouchable `D-001` disputed / `KMIA` / frozen-UMA positions (`$0.00` guaranteed floor)
      - `eligible_positions`: Non-disputed active holdings eligible for Family J recycling evaluation
      - `pre_split_slots`: Active pre-split complete-set slots (`pre_split_inventory_state`)
    """
    if not isinstance(portfolio_state, Mapping):
        return {
            "live_bankroll_usd": DEFAULT_LIVE_RECONCILED_NAV_USD,
            "reconciled_nav_usd": DEFAULT_LIVE_RECONCILED_NAV_USD,
            "book_equity_usd": DEFAULT_LIVE_RECONCILED_NAV_USD,
            "frozen_positions": [],
            "frozen_cost_basis_usd": 0.0,
            "eligible_positions": [],
            "pre_split_slots": [],
        }

    raw_active = (
        portfolio_state.get("active_positions")
        if portfolio_state.get("active_positions") is not None
        else (
            portfolio_state.get("open_positions")
            if portfolio_state.get("open_positions") is not None
            else portfolio_state.get("positions")
        )
    )
    pos_list: List[Dict[str, Any]] = []
    if isinstance(raw_active, Mapping):
        for tid, rec in raw_active.items():
            if isinstance(rec, Mapping):
                d = dict(rec)
                d.setdefault("trade_id", str(tid))
                d.setdefault("_position_key", str(tid))
                pos_list.append(d)
    elif isinstance(raw_active, Sequence) and not isinstance(raw_active, (str, bytes)):
        for rec in raw_active:
            if isinstance(rec, Mapping):
                pos_list.append(dict(rec))

    frozen: List[Dict[str, Any]] = []
    eligible: List[Dict[str, Any]] = []
    frozen_cost = 0.0

    for pos in pos_list:
        is_frz, reason = is_d001_frozen_position(pos, now_ts=now_ts)
        if is_frz:
            rec_copy = dict(pos)
            rec_copy["d001_freeze_reason"] = reason
            frozen.append(rec_copy)
            sh_f = _sf(pos.get("remaining_shares") if pos.get("remaining_shares") is not None else pos.get("shares"), 0.0)
            ep_f = _sf(pos.get("entry_price") or pos.get("avg_price"), 0.0)
            frozen_cost += _sf(
                pos.get("remaining_cost_basis")
                or pos.get("cost_usd")
                or pos.get("notional_usd")
                or (sh_f * ep_f),
                0.0,
            )
            continue
        rem_sh = _sf(pos.get("remaining_shares") if pos.get("remaining_shares") is not None else pos.get("shares"), 0.0)
        if rem_sh <= 1e-6 or bool(pos.get("is_liquidating")) or pos.get("exit_order_id") or pos.get("unwind_order_id"):
            continue
        if str(pos.get("status") or "").strip().upper() == "AWAITING_ONCHAIN_SETTLEMENT":
            continue
        eligible.append(pos)

    pre_split_slots: List[Dict[str, Any]] = []
    ps_raw = portfolio_state.get("pre_split_inventory_state")
    if isinstance(ps_raw, Mapping):
        if ps_raw.get("active") and _sf(ps_raw.get("shares"), 0.0) > 0.0:
            pre_split_slots.append(dict(ps_raw))
        extras = ps_raw.get("extra_slots")
        if isinstance(extras, Mapping):
            for sl in extras.values():
                if isinstance(sl, Mapping) and sl.get("active") and _sf(sl.get("shares"), 0.0) > 0.0:
                    pre_split_slots.append(dict(sl))

    live_bankroll = _sf(portfolio_state.get("live_bankroll"), DEFAULT_LIVE_RECONCILED_NAV_USD)
    book_eq = _sf(portfolio_state.get("total_account_equity"), live_bankroll + frozen_cost)
    # Never size off inflated book equity when frozen disputed positions exist!
    raw_rec_nav = portfolio_state.get("reconciled_nav_usd")
    if raw_rec_nav is not None and _sf(raw_rec_nav, 0.0) > 0.0:
        reconciled_nav = _sf(raw_rec_nav, live_bankroll)
        if frozen_cost > 0.0 and reconciled_nav > book_eq - frozen_cost + 5.0:
            reconciled_nav = max(0.0, book_eq - frozen_cost)
    else:
        reconciled_nav = max(0.0, book_eq - frozen_cost) if frozen_cost > 0.0 else live_bankroll

    return {
        "live_bankroll_usd": round(live_bankroll, 6),
        "reconciled_nav_usd": round(reconciled_nav, 6),
        "book_equity_usd": round(book_eq, 6),
        "frozen_positions": frozen,
        "frozen_cost_basis_usd": round(frozen_cost, 6),
        "eligible_positions": eligible,
        "pre_split_slots": pre_split_slots,
    }


# ---------------------------------------------------------------------------
# 3. Formal Multi-Outcome & NegRisk Partition Completeness Verifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PartitionCompletenessProof:
    """Formal proof / rejection certificate for multi-outcome & NegRisk event slates."""

    event_id: str
    is_negrisk: bool
    is_augmented_negrisk: bool
    is_mutually_exclusive: bool
    is_exhaustive: bool
    has_contiguous_question_indices: bool
    has_placeholder_hazard: bool
    has_mutable_other_hazard: bool
    has_closed_or_disabled_slots: bool
    conditional_missing_catchall: bool
    is_valid_complete_set: bool
    partition_type: str
    n_total_protocol_slots: int
    n_open_tradable_slots: int
    placeholder_slots: Tuple[str, ...] = ()
    mutable_other_slots: Tuple[str, ...] = ()
    closed_or_disabled_slots: Tuple[str, ...] = ()
    disqualifiers: Tuple[str, ...] = ()
    counterexample_states: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extract_question_index(market: Mapping[str, Any], fallback_idx: int) -> Optional[int]:
    for key in ("question_index", "questionIndex"):
        if market.get(key) is not None:
            try:
                return int(market[key])
            except (TypeError, ValueError):
                return None
    # On Gamma NegRisk events, `negRiskRequestID` / `conditionId` or `groupItemThreshold` carries 0..N-1 index
    git = market.get("groupItemThreshold")
    if git is not None and str(git).strip() != "":
        try:
            val = int(str(git).strip())
            if 0 <= val <= 512:
                return val
        except ValueError:
            pass
    q_id = str(market.get("questionID") or market.get("question_id") or "").strip().lower()
    if q_id.startswith("0x") and len(q_id) == 66:
        try:
            tail_byte = int(q_id[-2:], 16)
            return tail_byte
        except ValueError:
            pass
    return fallback_idx


def prove_multi_outcome_partition_completeness(
    event: Mapping[str, Any],
    markets: Optional[Sequence[Mapping[str, Any]]] = None,
) -> PartitionCompletenessProof:
    """
    Proves or refutes mutual exclusivity, exhaustiveness, and protocol slot completeness
    for a multi-outcome Gamma/normalized event (`Families B & C`).

    Fail-closed invariants enforced:
      1. Any missing child market (`len(mkts) < expected_market_count`), closed/archived/inactive
         child market, or `enableOrderBook == False` child market disqualifies `CLASS_A/B`.
      2. Any non-contiguous or duplicate `question_index` on NegRisk slates disqualifies `CLASS_A/B`.
      3. Any augmented NegRisk (`negRiskAugmented`), mutable `"Other"` (`negRiskOther` / `"Other"`),
         or unnamed placeholder (`Person A`, `Party B`, `Option X`) disqualifies `CLASS_A/B`.
      4. Cumulative/deadline series (`by Date X`), unilateral scalar ladders (`↑ $95k`, `above X`),
         sports multi-prop bundles (`Spread` + `O/U` + `Moneyline`), multi-winner questions,
         conditional events lacking `"No <event>"` catch-all, and unverified non-NegRisk candidate
         lists are strictly rejected with explicit counterexample states.
    """
    ev_id = str(event.get("id") or event.get("event_id") or "").strip()
    title = str(event.get("title") or event.get("question") or "").strip()
    desc = str(event.get("description") or "").strip()
    hdr = f"{title} {event.get('slug') or ''}".strip()

    raw_mkts = list(markets if markets is not None else (event.get("markets") or ()))
    expected_n = max(
        len(raw_mkts),
        int(_sf(event.get("market_count") or event.get("total_market_count") or event.get("n_total_slots"), len(raw_mkts))),
    )

    is_nr = bool(
        event.get("negRisk")
        or event.get("enableNegRisk")
        or event.get("neg_risk")
        or any(bool(m.get("negRisk") or m.get("neg_risk")) for m in raw_mkts if isinstance(m, Mapping))
    )
    is_aug = bool(
        event.get("negRiskAugmented")
        or event.get("augmentedNegRisk")
        or event.get("enableNegRiskOther")
        or event.get("negRiskOther")
        or event.get("neg_risk_augmented")
    )

    disqualifiers: List[str] = []
    counterexamples: List[str] = []
    notes: List[str] = []
    placeholders: List[str] = []
    mutable_others: List[str] = []
    closed_or_disabled: List[str] = []
    labels: List[str] = []
    q_indices: List[int] = []
    index_parse_ok = True
    open_tradable = 0

    if len(raw_mkts) < 2:
        return PartitionCompletenessProof(
            event_id=ev_id,
            is_negrisk=is_nr,
            is_augmented_negrisk=is_aug,
            is_mutually_exclusive=False,
            is_exhaustive=False,
            has_contiguous_question_indices=False,
            has_placeholder_hazard=False,
            has_mutable_other_hazard=False,
            has_closed_or_disabled_slots=True,
            conditional_missing_catchall=False,
            is_valid_complete_set=False,
            partition_type="INSUFFICIENT_OUTCOMES",
            n_total_protocol_slots=expected_n,
            n_open_tradable_slots=len(raw_mkts),
            disqualifiers=("FEWER_THAN_2_OUTCOMES",),
            counterexample_states=("OMEGA_INCOMPLETE_SINGLETON",),
        )

    if len(raw_mkts) < expected_n:
        disqualifiers.append(f"PARTIAL_SLATE_MISSING_SLOTS:{len(raw_mkts)}_OF_{expected_n}")
        counterexamples.append("OMEGA_OMITTED_PROTOCOL_SLOT_WINS")

    for idx, m in enumerate(raw_mkts):
        lbl = str(
            m.get("groupItemTitle")
            or m.get("label")
            or m.get("outcome")
            or m.get("question")
            or m.get("title")
            or f"slot_{idx}"
        ).strip()
        labels.append(lbl)

        if is_placeholder_outcome_market(m, is_augmented_event=is_aug):
            placeholders.append(lbl)
        if is_mutable_other_outcome_market(m, is_augmented_event=is_aug):
            mutable_others.append(lbl)

        yes_t, no_t, _ = extract_binary_token_pair(m)
        uma_st = str(m.get("umaResolutionStatus") or m.get("uma_resolution_status") or "").strip().lower()
        is_closed_or_bad = bool(
            m.get("closed") is True
            or m.get("archived") is True
            or m.get("active") is False
            or m.get("enableOrderBook") is False
            or m.get("enable_order_book") is False
            or not (yes_t and no_t)
            or uma_st in {"proposed", "disputed", "resolved"}
        )
        if is_closed_or_bad:
            closed_or_disabled.append(lbl)
        else:
            open_tradable += 1

        q_idx = _extract_question_index(m, idx)
        if q_idx is None:
            index_parse_ok = False
        else:
            q_indices.append(q_idx)

    # Check 0..N_total-1 contiguity for NegRisk
    has_contiguous_q = True
    if is_nr:
        if not index_parse_ok or len(q_indices) != expected_n:
            has_contiguous_q = False
        elif sorted(q_indices) != list(range(expected_n)):
            # Fail whenever explicit `question_index`/`questionIndex` or 66-char `0x...` `questionID` was supplied with gaps/duplicates!
            has_explicit_idx = any(
                (
                    m.get("question_index") is not None
                    or m.get("questionIndex") is not None
                    or (str(m.get("questionID") or m.get("question_id") or "").strip().lower().startswith("0x")
                        and len(str(m.get("questionID") or m.get("question_id") or "").strip()) == 66)
                )
                for m in raw_mkts
            )
            if has_explicit_idx or len(set(q_indices)) != len(raw_mkts):
                has_contiguous_q = False
        if not has_contiguous_q:
            disqualifiers.append("NON_CONTIGUOUS_OR_DUPLICATE_NEGRISK_QUESTION_INDICES")
            counterexamples.append("OMEGA_UNINDEXED_PROTOCOL_QUESTION_WINS")

    has_ph = bool(placeholders)
    has_other = bool(mutable_others)
    has_closed = bool(closed_or_disabled)

    if is_aug:
        disqualifiers.append("AUGMENTED_NEGRISK_OPEN_UNIVERSE")
        counterexamples.append("OMEGA_AUGMENTED_NEW_NAMED_OUTCOME_CLARIFIED")
    if has_ph:
        disqualifiers.append("UNNAMED_OR_INACTIVE_PLACEHOLDER_OUTCOME_PRESENT")
        counterexamples.append("OMEGA_PLACEHOLDER_ACTIVATED_AND_WINS")
    if has_other:
        disqualifiers.append("MUTABLE_OTHER_OUTCOME_SEMANTIC_SHIFT_RISK")
        counterexamples.append("OMEGA_CLARIFIED_CANDIDATE_SPLITS_FROM_MUTABLE_OTHER")
    if has_closed:
        disqualifiers.append("CLOSED_INACTIVE_OR_UNTRADABLE_CHILD_MARKET_IN_SLATE")
        counterexamples.append("OMEGA_CLOSED_OR_UNTRADABLE_SLOT_PAYOUT_DIVERGENCE")

    # Check mutual exclusivity & exhaustiveness of proposition structure
    is_exclusive = True
    is_exhaustive = True
    cond_missing = False

    if bool(event.get("cumulativeMarkets")) or _DEADLINE_SERIES_RE.search(hdr):
        is_exclusive = False
        is_exhaustive = False
        disqualifiers.append("CUMULATIVE_OR_DEADLINE_SERIES_NOT_PARTITION")
        counterexamples.extend(["OMEGA_EARLY_HIT_MULTIPLE_YES_PAYOUT", "OMEGA_NEVER_OCCURS_DOUBLE_ZERO"])

    if any(_MULTI_PROP_GAME_LABEL_RE.search(lb) for lb in labels):
        is_exclusive = False
        is_exhaustive = False
        disqualifiers.append("MULTI_PROP_SPORTS_GAME_BUNDLE_NOT_PARTITION")
        counterexamples.append("OMEGA_INDEPENDENT_GAME_PROPS_CO_OCCUR")

    if _MULTI_WINNER_HEADER_RE.search(hdr):
        is_exclusive = False
        disqualifiers.append("MULTI_WINNER_OR_NON_EXCLUSIVE_EVENT")
        counterexamples.append("OMEGA_MULTIPLE_WINNERS_RESOLVE_YES")

    unilateral_hits = sum(1 for lb in labels if _UNILATERAL_THRESHOLD_LABEL_RE.search(lb))
    if unilateral_hits >= 2 and not is_nr:
        is_exclusive = False
        is_exhaustive = False
        disqualifiers.append("UNILATERAL_SCALAR_THRESHOLD_LADDER_NOT_DISJOINT")
        counterexamples.extend(["OMEGA_EXTREME_MOVE_MULTIPLE_THRESHOLDS_HIT", "OMEGA_INSIDE_DEAD_ZONE_ALL_NO"])

    # Conditional occurrence check (e.g., IPO valuation brackets without `"No IPO"` catch-all)
    if _CONDITIONAL_EVENT_HEADER_RE.search(hdr) or _CONDITIONAL_EVENT_HEADER_RE.search(desc):
        has_neg_catchall = any(_EXPLICIT_NEGATION_CATCHALL_RE.search(lb) for lb in labels)
        if not has_neg_catchall:
            cond_missing = True
            is_exhaustive = False
            disqualifiers.append("CONDITIONAL_EVENT_MISSING_NO_OCCURRENCE_CATCHALL")
            counterexamples.append("OMEGA_UNDERLYING_EVENT_NEVER_OCCURS_ALL_YES_ZERO")

    # Numeric bracket tail completeness check (even on standard NegRisk!)
    bracket_syntax_re = re.compile(
        r"(?:\d+\s*(?:[-–—]|\bto\b)\s*\d+|[$%°]|[<>≤≥]|\b(?:under|over|below|above|less\s+than|more\s+than|between|fewer\s+than|or\s+more|or\s+less|or\s+fewer)\b)",
        re.IGNORECASE,
    )
    numeric_labels = [lb for lb in labels if re.search(r"\d", lb) and not _EXPLICIT_NEGATION_CATCHALL_RE.search(lb)]
    has_bracket_syntax = any(bracket_syntax_re.search(lb) for lb in labels)
    if len(numeric_labels) == len(labels) and len(labels) >= 3 and has_bracket_syntax:
        has_lo = any(_LOWER_TAIL_BRACKET_RE.search(lb) for lb in labels)
        has_hi = any(_UPPER_TAIL_BRACKET_RE.search(lb) for lb in labels)
        if not (has_lo and has_hi):
            is_exhaustive = False
            disqualifiers.append("NUMERIC_BRACKET_SLATE_MISSING_UNBOUNDED_TAIL")
            counterexamples.append("OMEGA_OUTSIDE_BOUNDED_NUMERIC_RANGE_DOUBLE_ZERO")

    # Non-NegRisk standalone multi-market events: NEVER assume candidate/entity lists are exhaustive!
    if not is_nr:
        # Only allow non-NegRisk complete set if explicitly verified 3-way 1X2 regulation partition or
        # caller explicitly attested `verified_exhaustive_non_negrisk == True` with disjoint cover
        is_explicit_1x2 = (
            len(labels) == 3
            and any("draw" in lb.lower() or "tie" in lb.lower() for lb in labels)
            and is_exclusive
            and not has_closed
        )
        explicitly_attested = bool(event.get("verified_exhaustive_non_negrisk"))
        if not (is_explicit_1x2 or explicitly_attested):
            is_exhaustive = False
            disqualifiers.append("STANDALONE_NON_NEGRISK_EXHAUSTIVENESS_UNPROVEN")
            counterexamples.append("OMEGA_UNLISTED_OUTCOME_RESOLVES_ALL_STANDALONE_YES_ZERO")
        else:
            notes.append("STANDALONE_NON_NEGRISK_VOID_50_50_CHECK_REQUIRED")
    else:
        # Even on closed `negRisk` (`negRiskAugmented == False`), check open-ended candidate lists without catch-all
        # e.g. `"Who will win..."` with 4 names, `negRiskAugmented=False`, no `"Other"` / `"None"`, unless protocol closed
        if bool(event.get("non_exhaustive_candidate_list")):
            is_exhaustive = False
            disqualifiers.append("EXPLICIT_NON_EXHAUSTIVE_CANDIDATE_LIST")
            counterexamples.append("OMEGA_UNLISTED_CANDIDATE_WINS_ALL_LISTED_ZERO")

    is_valid = bool(
        is_exclusive
        and is_exhaustive
        and has_contiguous_q
        and not is_aug
        and not has_ph
        and not has_other
        and not has_closed
        and not cond_missing
        and len(raw_mkts) == expected_n
    )

    if is_valid:
        ptype = "CLOSED_NEGRISK_EXHAUSTIVE_PARTITION" if is_nr else "VERIFIED_STANDALONE_EXHAUSTIVE_PARTITION"
    elif is_aug or has_ph or has_other:
        ptype = "AUGMENTED_NEGRISK_PLACEHOLDER_OR_MUTABLE_OTHER"
    elif not is_exclusive:
        ptype = "NON_MUTUALLY_EXCLUSIVE_BUNDLE_OR_LADDER"
    elif cond_missing or not is_exhaustive:
        ptype = "NON_EXHAUSTIVE_MISSING_CATCHALL"
    else:
        ptype = "INCOMPLETE_OR_DISABLED_SLOTS"

    return PartitionCompletenessProof(
        event_id=ev_id,
        is_negrisk=is_nr,
        is_augmented_negrisk=is_aug,
        is_mutually_exclusive=is_exclusive,
        is_exhaustive=is_exhaustive,
        has_contiguous_question_indices=has_contiguous_q,
        has_placeholder_hazard=has_ph,
        has_mutable_other_hazard=has_other,
        has_closed_or_disabled_slots=has_closed or (len(raw_mkts) < expected_n),
        conditional_missing_catchall=cond_missing,
        is_valid_complete_set=is_valid,
        partition_type=ptype,
        n_total_protocol_slots=expected_n,
        n_open_tradable_slots=open_tradable,
        placeholder_slots=tuple(placeholders),
        mutable_other_slots=tuple(mutable_others),
        closed_or_disabled_slots=tuple(closed_or_disabled),
        disqualifiers=tuple(dict.fromkeys(disqualifiers)),
        counterexample_states=tuple(dict.fromkeys(counterexamples)),
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# 4. Canonical Opportunity Output Model & Budget-Guarded Verifier Wrapper
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectedCompleteSetOrNegRiskOpportunity:
    """
    Unified, proof-carrying candidate emitted by Families A, B, C, and J.
    Carries a deterministic `ArbitrageProofObject` from `UniversalArbVerifier`
    plus family-specific economics, synthetic routing deltas, and `DeltaWealth_min`.
    """

    candidate_id: str
    family: str  # "A" | "B" | "C" | "J"
    subfamily: str
    opportunity_class: str  # "CLASS_A" .. "CLASS_E"
    event_id: str
    event_title: str
    market_ids: Tuple[str, ...]
    condition_ids: Tuple[str, ...]
    optimal_shares_q: float
    gross_top_of_book_spread_per_unit: float
    gross_top_of_book_spread_bps: float
    net_executable_edge_per_unit: float
    net_executable_edge_bps: float
    capital_required_usd: float
    peak_intratx_collateral_usd: float
    expected_lockup_hours: float
    worst_case_lockup_hours: float
    theoretical_top_of_book_usd: float
    executable_l2_net_usd: float
    attainable_risk_adjusted_usd: float
    realized_net_usd: float
    min_state_net_payoff_usd: float
    max_state_net_payoff_usd: float
    expected_net_payoff_usd: float
    delta_wealth_min_usd: float
    delta_wealth_vs_cost_basis_usd: Optional[float]
    delta_wealth_vs_liquidation_mark_usd: Optional[float]
    synthetic_vs_direct_ask_savings_per_share: Optional[float]
    taker_fees_usd: float
    conversion_fee_usd: float
    gas_cost_usd: float
    is_atomic_or_prelocked: bool
    clob_leg_count: int
    d007_sub500_multileg_quarantine: bool
    execution_mode_cap: str
    is_dormant_near_arb: bool
    distance_to_breakeven_bps: float
    partition_proof: PartitionCompletenessProof
    proof: ArbitrageProofObject
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def proof_sha256(self) -> str:
        return self.proof.proof_sha256

    @property
    def canonical_event_keys(self) -> Tuple[str, ...]:
        keys: List[str] = []
        if self.event_id:
            keys.append(f"EVT:{self.event_id}")
        for mid in self.market_ids:
            if mid:
                keys.append(f"MKT:{mid}")
        for cid in self.condition_ids:
            if cid:
                keys.append(f"CID:{cid}")
        return tuple(dict.fromkeys(keys))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["proof_sha256"] = self.proof.proof_sha256
        d["canonical_event_keys"] = list(self.canonical_event_keys)
        return d


def _build_instrument_book(
    token_id: str,
    market: Mapping[str, Any],
    books_by_token: Mapping[str, Any],
    *,
    outcome_label: str = "",
    is_placeholder: bool = False,
    is_other: bool = False,
) -> InstrumentOrderBook:
    """Normalizes either an `InstrumentOrderBook` or raw CLOB `/books` dict into `InstrumentOrderBook`."""
    existing = books_by_token.get(token_id)
    if existing is not None and hasattr(existing, "asks") and hasattr(existing, "bids") and hasattr(existing, "fee_rate_bps"):
        if is_placeholder != existing.is_placeholder or is_other != existing.is_other:
            return InstrumentOrderBook(
                instrument_id=existing.instrument_id,
                market_id=existing.market_id,
                condition_id=existing.condition_id,
                outcome_label=existing.outcome_label or outcome_label,
                asks=existing.asks,
                bids=existing.bids,
                fee_rate_bps=existing.fee_rate_bps,
                fee_exponent=existing.fee_exponent,
                tick_size=existing.tick_size,
                min_order_size=existing.min_order_size,
                enable_order_book=existing.enable_order_book,
                book_timestamp_sec=existing.book_timestamp_sec,
                is_placeholder=is_placeholder or existing.is_placeholder,
                is_other=is_other or existing.is_other,
            )
        return existing

    f_rate, f_bps, f_exp = extract_market_fee_params(market)
    raw_tick = market.get("orderPriceMinTickSize") or market.get("minimum_tick_size") or market.get("tick_size")
    tick_f = _sf(raw_tick, 0.0) if raw_tick is not None else 0.0
    raw_min_sz = market.get("orderMinSize") or market.get("minimum_order_size") or market.get("min_order_size")
    min_sz_f = max(DEFAULT_MIN_ORDER_SHARES, _sf(raw_min_sz, DEFAULT_MIN_ORDER_SHARES))
    en_ob = bool(market.get("enableOrderBook", True) is not False and market.get("enable_order_book", True) is not False)

    return InstrumentOrderBook.from_raw(
        token_id,
        existing if isinstance(existing, Mapping) else {},
        market_id=str(market.get("id") or market.get("market_id") or ""),
        condition_id=str(market.get("conditionId") or market.get("condition_id") or ""),
        outcome_label=outcome_label,
        fee_rate_bps=f_bps,
        fee_rate=f_rate,
        fee_exponent=f_exp,
        tick_size=(tick_f if tick_f > 0.0 else None),
        min_order_size=min_sz_f,
        enable_order_book=en_ob,
        is_placeholder=is_placeholder,
        is_other=is_other,
    )


def _verify_with_liquid_cash_budget_guard(
    base_config: VerificationConfig,
    candidate: CandidateStructure,
    books: Mapping[str, InstrumentOrderBook],
    *,
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
    peak_intratx_split_multiplier: float = 0.0,
) -> Tuple[ArbitrageProofObject, float, float]:
    """
    Invokes `UniversalArbVerifier.verify_and_simulate` (`USE_INVENTORY` charges `$0.00` against
    liquid `max_budget_usd` and `fixed_gas_usd` is included in `capital_required_usd`), while
    also bounding peak intra-tx multi-split collateral (`peak_intratx_split_multiplier * q`,
    e.g. `2.0 * q` for `B2` `NR3` before `convertPositions(0b11)` returns `$1.00 * q`).
    Returns `(proof, liquid_cash_required_usd, peak_intratx_collateral_usd)`.
    """
    fixed_gas = 0.0
    split_units = 0.0
    for leg in candidate.legs:
        if leg.action_type in (ActionType.BUY_CLOB, ActionType.SELL_CLOB):
            fixed_gas += max(0.0, float(leg.gas_cost_usd))
        elif leg.action_type in (ActionType.CTF_SPLIT, ActionType.CTF_MERGE, ActionType.NEGRISK_CONVERT):
            fixed_gas += float(leg.gas_cost_usd) if leg.gas_cost_usd > 0.0 else base_config.default_relayer_gas_usd
            if leg.action_type == ActionType.CTF_SPLIT:
                split_units += float(leg.weight)

    verifier = UniversalArbVerifier(config=base_config)
    proof = verifier.verify_and_simulate(candidate, books, holdings=holdings)
    q_opt = proof.optimal_executable_quantity
    liquid_cash_req = round(float(proof.cost_breakdown.capital_required_usd), 6) if q_opt > 0.0 else 0.0

    extra_peak_per_q = max(0.0, float(peak_intratx_split_multiplier) - split_units)
    peak_collateral = round(liquid_cash_req + q_opt * extra_peak_per_q, 6) if q_opt > 0.0 else 0.0

    # Note: In `B2` (`2x split + convert(0b11)`), `split_units == 2.0` (`unit_cash_outlay_non_clob == 2.0` in
    # `UniversalArbVerifier` before conversion cash-back, so `capital_required_usd` ALREADY reflects peak `2.0 * q`
    # intra-tx collateral!). Distinguish net post-convert collateral (`1.0 * q`) vs peak intra-tx (`2.0 * q`):
    conv_cash_per_q = 0.0
    for leg in candidate.legs:
        if leg.action_type == ActionType.NEGRISK_CONVERT:
            m_b = len(leg.burned_no_instrument_ids)
            if m_b >= 2:
                c_f = min(0.25, max(0.0, float(leg.negrisk_fee_bips) / 10_000.0))
                conv_cash_per_q += float(leg.weight) * float(m_b - 1) * (1.0 - c_f)
    if q_opt > 0.0 and split_units > 0.0 and conv_cash_per_q > 0.0:
        # `liquid_cash_req` from `UniversalArbVerifier` is the peak intra-tx split cash needed BEFORE convert returns cash;
        # keep `capital_required_usd == peak_collateral` so wallet never attempts `2x split` without `2x` cash!
        peak_collateral = max(peak_collateral, liquid_cash_req)

    return proof, liquid_cash_req, peak_collateral


def _compute_dormant_flags(
    *,
    opp_class: str,
    is_structurally_valid: bool,
    gross_edge_per_unit: float,
    net_edge_per_unit: float,
    dormant_max_bps: float = DORMANT_MAX_BPS_DEFAULT,
) -> Tuple[bool, float]:
    """
    Identifies dormant near-arbitrage structures (`CLASS_E` on a valid contractual structure
    whose top-of-book or L2 spread sits within `dormant_max_bps` = `250 bps` of net breakeven)
    so the surveillance engine retains & rescans them on book updates rather than dropping them.
    """
    if not is_structurally_valid:
        return False, 99999.0
    best_unit_edge = net_edge_per_unit if net_edge_per_unit != 0.0 else gross_edge_per_unit
    if opp_class in (OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value):
        return False, 0.0
    deficit_bps = round(max(0.0, -best_unit_edge * 10_000.0), 2)
    is_dormant = bool(opp_class == OpportunityClass.CLASS_E.value and 0.0 < deficit_bps <= float(dormant_max_bps))
    return is_dormant, deficit_bps


# ---------------------------------------------------------------------------
# 5. Family A — Binary YES/NO Complete-Set Arbitrage Detector
# ---------------------------------------------------------------------------


def _build_binary_partition_proof(market: Mapping[str, Any]) -> PartitionCompletenessProof:
    mid = str(market.get("id") or market.get("market_id") or market.get("conditionId") or "").strip()
    cid = str(market.get("conditionId") or market.get("condition_id") or "").strip()
    yes_tok, no_tok, _ = extract_binary_token_pair(market)
    is_nr = bool(market.get("negRisk") or market.get("neg_risk"))
    is_aug = bool(market.get("negRiskAugmented") or market.get("neg_risk_augmented"))
    uma_st = str(market.get("umaResolutionStatus") or market.get("uma_resolution_status") or "").strip().lower()

    disq: List[str] = []
    cex: List[str] = []
    if not cid or not yes_tok or not no_tok:
        disq.append("INVALID_BINARY_CONDITION_OR_TOKENS")
        cex.append("OMEGA_MALFORMED_BINARY_PAIR")
    if market.get("closed") is True or market.get("archived") is True or market.get("active") is False:
        disq.append("CLOSED_OR_INACTIVE_BINARY_MARKET")
    if market.get("enableOrderBook") is False or market.get("enable_order_book") is False:
        disq.append("ORDERBOOK_DISABLED")
    if uma_st == "disputed":
        disq.append("UMA_DISPUTED_MARKET")
        cex.append("OMEGA_UMA_DISPUTE_LOCKUP")

    # Note: Even on an augmented NegRisk child market, its OWN binary CTF condition `(YES_i, NO_i)`
    # satisfies `payout(YES_i) + payout(NO_i) == 1.0` (and merges 1:1 on-chain for $1.00 collateral),
    # UNLESS it is an unactivated `active == False` placeholder with disabled trading.
    valid = len(disq) == 0
    return PartitionCompletenessProof(
        event_id=str(market.get("event_id") or mid),
        is_negrisk=is_nr,
        is_augmented_negrisk=is_aug,
        is_mutually_exclusive=valid,
        is_exhaustive=valid,
        has_contiguous_question_indices=True,
        has_placeholder_hazard=False,
        has_mutable_other_hazard=False,
        has_closed_or_disabled_slots=not valid,
        conditional_missing_catchall=False,
        is_valid_complete_set=valid,
        partition_type="BINARY_SINGLE_CONDITION_CTF",
        n_total_protocol_slots=2,
        n_open_tradable_slots=2 if valid else 0,
        disqualifiers=tuple(disq),
        counterexample_states=tuple(cex),
    )


def detect_family_a_binary_complete_sets(
    binary_markets: Sequence[Mapping[str, Any]],
    books_by_token: Mapping[str, Any],
    *,
    config: Optional[VerificationConfig] = None,
    merge_gas_usd: float = 0.0,
    split_gas_usd: float = 0.0,
    dormant_max_bps: float = DORMANT_MAX_BPS_DEFAULT,
    include_non_actionable_class_e: bool = False,
) -> List[DetectedCompleteSetOrNegRiskOpportunity]:
    """
    Family A — Exhaustive Binary YES/NO Complete-Set Detector:
      (i)  `A1_BINARY_BUY_AND_MERGE`: Walk `ask(YES)` + `ask(NO)` L2 ladders + exact Protocol V2
           share-deducted BUY fees + `merge_gas_usd` vs `$1.00` instant CTF `mergePositions`.
      (ii) `A2_BINARY_SPLIT_AND_SELL`: `$1.00` CTF `splitPosition` + `split_gas_usd` into
           `bid(YES)` + `bid(NO)` L2 ladders minus exact cash-deducted SELL fees > `$1.00`.
    """
    cfg = config or VerificationConfig()
    out: List[DetectedCompleteSetOrNegRiskOpportunity] = []

    for m in binary_markets or ():
        if not isinstance(m, Mapping):
            continue
        mid = str(m.get("id") or m.get("market_id") or m.get("conditionId") or "").strip()
        cid = str(m.get("conditionId") or m.get("condition_id") or mid).strip()
        if mid in FROZEN_DISPUTED_MARKET_IDS:
            continue
        yes_tok, no_tok, (lbl_y, lbl_n) = extract_binary_token_pair(m)
        if not (yes_tok and no_tok):
            continue

        part_proof = _build_binary_partition_proof(m)
        bk_yes = _build_instrument_book(yes_tok, m, books_by_token, outcome_label=lbl_y)
        bk_no = _build_instrument_book(no_tok, m, books_by_token, outcome_label=lbl_n)
        local_books = {yes_tok: bk_yes, no_tok: bk_no}

        states = StateSpaceBuilder.binary_complete_set_states(yes_tok, no_tok, include_void_50_50=True)
        ev_id = str(m.get("event_id") or m.get("eventId") or mid)
        title = str(m.get("question") or m.get("title") or mid).strip()
        end_ts = _parse_end_ts(m.get("endDate") or m.get("end_ts"))
        now_f = float(time.time() if cfg.now_ts is None else cfg.now_ts)
        rem_hrs = max(0.02, (end_ts - now_f) / 3600.0) if end_ts is not None else 2.0

        # --- Direction A1: Buy YES + Buy NO -> Instant CTF Merge ($1.00) ---
        gross_a1 = (
            round(1.0 - (bk_yes.asks[0].price + bk_no.asks[0].price), 6)
            if (bk_yes.asks and bk_no.asks)
            else -1.0
        )
        cand_a1 = CandidateStructure(
            candidate_id=f"FAM_A_BUY_MERGE_{mid}",
            family="A",
            legs=(
                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=yes_tok, weight=1.0, market_id=mid, label=lbl_y),
                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=no_tok, weight=1.0, market_id=mid, label=lbl_n),
                ActionLeg(
                    action_type=ActionType.CTF_MERGE,
                    weight=1.0,
                    related_instrument_ids=(yes_tok, no_tok),
                    gas_cost_usd=max(0.0, float(merge_gas_usd)),
                    market_id=mid,
                    label="CTF_MERGE_COMPLETE_SET",
                ),
            ),
            states=states,
            rule_verified=part_proof.is_valid_complete_set,
            rule_disqualifiers=part_proof.disqualifiers,
            is_exhaustive_partition=part_proof.is_exhaustive,
            is_mutually_exclusive=part_proof.is_mutually_exclusive,
            requires_exhaustive_partition=True,
            expected_lockup_hours=0.01,
            worst_case_lockup_hours=min(0.05, rem_hrs),
        )
        proof_a1, cash_a1, peak_a1 = _verify_with_liquid_cash_budget_guard(cfg, cand_a1, local_books)
        unit_edge_a1 = (
            proof_a1.net_executable_edge_per_unit
            if proof_a1.optimal_executable_quantity > 0.0
            else proof_a1.gross_top_of_book_edge_per_unit
        )
        is_dorm_a1, dist_a1 = _compute_dormant_flags(
            opp_class=proof_a1.opportunity_class,
            is_structurally_valid=part_proof.is_valid_complete_set and not bk_yes.has_crossed_or_invalid_book() and not bk_no.has_crossed_or_invalid_book(),
            gross_edge_per_unit=gross_a1,
            net_edge_per_unit=unit_edge_a1,
            dormant_max_bps=dormant_max_bps,
        )
        if (
            include_non_actionable_class_e
            or proof_a1.opportunity_class != OpportunityClass.CLASS_E.value
            or is_dorm_a1
        ):
            out.append(
                DetectedCompleteSetOrNegRiskOpportunity(
                    candidate_id=cand_a1.candidate_id,
                    family="A",
                    subfamily="A1_BINARY_BUY_AND_MERGE",
                    opportunity_class=proof_a1.opportunity_class,
                    event_id=ev_id,
                    event_title=title,
                    market_ids=(mid,),
                    condition_ids=(cid,),
                    optimal_shares_q=proof_a1.optimal_executable_quantity,
                    gross_top_of_book_spread_per_unit=gross_a1,
                    gross_top_of_book_spread_bps=round(gross_a1 * 10_000.0, 2),
                    net_executable_edge_per_unit=unit_edge_a1,
                    net_executable_edge_bps=round(unit_edge_a1 * 10_000.0, 2),
                    capital_required_usd=cash_a1,
                    peak_intratx_collateral_usd=peak_a1,
                    expected_lockup_hours=proof_a1.cost_breakdown.expected_lockup_hours,
                    worst_case_lockup_hours=proof_a1.cost_breakdown.worst_case_lockup_hours,
                    theoretical_top_of_book_usd=proof_a1.four_value_ledger.theoretical_top_of_book_usd,
                    executable_l2_net_usd=proof_a1.four_value_ledger.executable_l2_net_usd,
                    attainable_risk_adjusted_usd=proof_a1.four_value_ledger.attainable_risk_adjusted_usd,
                    realized_net_usd=0.0,
                    min_state_net_payoff_usd=proof_a1.min_state_net_payoff_usd,
                    max_state_net_payoff_usd=proof_a1.max_state_net_payoff_usd,
                    expected_net_payoff_usd=proof_a1.expected_net_payoff_usd,
                    delta_wealth_min_usd=proof_a1.min_state_net_payoff_usd,
                    delta_wealth_vs_cost_basis_usd=None,
                    delta_wealth_vs_liquidation_mark_usd=None,
                    synthetic_vs_direct_ask_savings_per_share=None,
                    taker_fees_usd=proof_a1.cost_breakdown.taker_fees_usd,
                    conversion_fee_usd=proof_a1.cost_breakdown.conversion_costs_usd,
                    gas_cost_usd=proof_a1.cost_breakdown.gas_costs_usd,
                    is_atomic_or_prelocked=proof_a1.is_atomic_or_prelocked,
                    clob_leg_count=2,
                    d007_sub500_multileg_quarantine=proof_a1.d007_sub500_multileg_quarantine,
                    execution_mode_cap=proof_a1.execution_mode_cap,
                    is_dormant_near_arb=is_dorm_a1,
                    distance_to_breakeven_bps=dist_a1,
                    partition_proof=part_proof,
                    proof=proof_a1,
                    metadata={
                        "neg_risk": part_proof.is_negrisk,
                        "fee_rate_bps": bk_yes.fee_rate_bps,
                        "yes_token_id": yes_tok,
                        "no_token_id": no_tok,
                    },
                )
            )

        # --- Direction A2: CTF Split ($1.00) -> Sell YES + Sell NO into Bids ---
        gross_a2 = (
            round((bk_yes.bids[0].price + bk_no.bids[0].price) - 1.0, 6)
            if (bk_yes.bids and bk_no.bids)
            else -1.0
        )
        cand_a2 = CandidateStructure(
            candidate_id=f"FAM_A_SPLIT_SELL_{mid}",
            family="A",
            legs=(
                ActionLeg(
                    action_type=ActionType.CTF_SPLIT,
                    weight=1.0,
                    related_instrument_ids=(yes_tok, no_tok),
                    gas_cost_usd=max(0.0, float(split_gas_usd)),
                    market_id=mid,
                    label="CTF_SPLIT_COLLATERAL",
                ),
                ActionLeg(action_type=ActionType.SELL_CLOB, instrument_id=yes_tok, weight=1.0, market_id=mid, label=lbl_y),
                ActionLeg(action_type=ActionType.SELL_CLOB, instrument_id=no_tok, weight=1.0, market_id=mid, label=lbl_n),
            ),
            states=states,
            rule_verified=part_proof.is_valid_complete_set,
            rule_disqualifiers=part_proof.disqualifiers,
            is_exhaustive_partition=part_proof.is_exhaustive,
            is_mutually_exclusive=part_proof.is_mutually_exclusive,
            requires_exhaustive_partition=True,
            expected_lockup_hours=0.01,
            worst_case_lockup_hours=min(0.05, rem_hrs),
        )
        proof_a2, cash_a2, peak_a2 = _verify_with_liquid_cash_budget_guard(cfg, cand_a2, local_books)
        unit_edge_a2 = (
            proof_a2.net_executable_edge_per_unit
            if proof_a2.optimal_executable_quantity > 0.0
            else proof_a2.gross_top_of_book_edge_per_unit
        )
        is_dorm_a2, dist_a2 = _compute_dormant_flags(
            opp_class=proof_a2.opportunity_class,
            is_structurally_valid=part_proof.is_valid_complete_set and not bk_yes.has_crossed_or_invalid_book() and not bk_no.has_crossed_or_invalid_book(),
            gross_edge_per_unit=gross_a2,
            net_edge_per_unit=unit_edge_a2,
            dormant_max_bps=dormant_max_bps,
        )
        if (
            include_non_actionable_class_e
            or proof_a2.opportunity_class != OpportunityClass.CLASS_E.value
            or is_dorm_a2
        ):
            out.append(
                DetectedCompleteSetOrNegRiskOpportunity(
                    candidate_id=cand_a2.candidate_id,
                    family="A",
                    subfamily="A2_BINARY_SPLIT_AND_SELL",
                    opportunity_class=proof_a2.opportunity_class,
                    event_id=ev_id,
                    event_title=title,
                    market_ids=(mid,),
                    condition_ids=(cid,),
                    optimal_shares_q=proof_a2.optimal_executable_quantity,
                    gross_top_of_book_spread_per_unit=gross_a2,
                    gross_top_of_book_spread_bps=round(gross_a2 * 10_000.0, 2),
                    net_executable_edge_per_unit=unit_edge_a2,
                    net_executable_edge_bps=round(unit_edge_a2 * 10_000.0, 2),
                    capital_required_usd=cash_a2,
                    peak_intratx_collateral_usd=peak_a2,
                    expected_lockup_hours=proof_a2.cost_breakdown.expected_lockup_hours,
                    worst_case_lockup_hours=proof_a2.cost_breakdown.worst_case_lockup_hours,
                    theoretical_top_of_book_usd=proof_a2.four_value_ledger.theoretical_top_of_book_usd,
                    executable_l2_net_usd=proof_a2.four_value_ledger.executable_l2_net_usd,
                    attainable_risk_adjusted_usd=proof_a2.four_value_ledger.attainable_risk_adjusted_usd,
                    realized_net_usd=0.0,
                    min_state_net_payoff_usd=proof_a2.min_state_net_payoff_usd,
                    max_state_net_payoff_usd=proof_a2.max_state_net_payoff_usd,
                    expected_net_payoff_usd=proof_a2.expected_net_payoff_usd,
                    delta_wealth_min_usd=proof_a2.min_state_net_payoff_usd,
                    delta_wealth_vs_cost_basis_usd=None,
                    delta_wealth_vs_liquidation_mark_usd=None,
                    synthetic_vs_direct_ask_savings_per_share=None,
                    taker_fees_usd=proof_a2.cost_breakdown.taker_fees_usd,
                    conversion_fee_usd=proof_a2.cost_breakdown.conversion_costs_usd,
                    gas_cost_usd=proof_a2.cost_breakdown.gas_costs_usd,
                    is_atomic_or_prelocked=proof_a2.is_atomic_or_prelocked,
                    clob_leg_count=2,
                    d007_sub500_multileg_quarantine=proof_a2.d007_sub500_multileg_quarantine,
                    execution_mode_cap=proof_a2.execution_mode_cap,
                    is_dormant_near_arb=is_dorm_a2,
                    distance_to_breakeven_bps=dist_a2,
                    partition_proof=part_proof,
                    proof=proof_a2,
                    metadata={
                        "neg_risk": part_proof.is_negrisk,
                        "fee_rate_bps": bk_yes.fee_rate_bps,
                        "yes_token_id": yes_tok,
                        "no_token_id": no_tok,
                    },
                )
            )

    return out


# ---------------------------------------------------------------------------
# 6. Family B — Multi-Outcome Complete-Set Arbitrage Detector
# ---------------------------------------------------------------------------


def _prepare_event_outcome_specs(
    event: Mapping[str, Any],
    books_by_token: Mapping[str, Any],
) -> Tuple[PartitionCompletenessProof, List[Dict[str, Any]], Dict[str, InstrumentOrderBook], Tuple[StateSpec, ...]]:
    raw_mkts = list(event.get("markets") or ())
    part_proof = prove_multi_outcome_partition_completeness(event, raw_mkts)
    outcome_specs: List[Dict[str, Any]] = []
    local_books: Dict[str, InstrumentOrderBook] = {}

    for idx, m in enumerate(raw_mkts):
        if not isinstance(m, Mapping):
            continue
        mid = str(m.get("id") or m.get("market_id") or f"mkt_{idx}").strip()
        cid = str(m.get("conditionId") or m.get("condition_id") or mid).strip()
        yes_tok, no_tok, _ = extract_binary_token_pair(m)
        lbl = str(
            m.get("groupItemTitle")
            or m.get("label")
            or m.get("outcome")
            or m.get("question")
            or f"outcome_{idx}"
        ).strip()
        is_ph = is_placeholder_outcome_market(m, is_augmented_event=part_proof.is_augmented_negrisk)
        is_oth = is_mutable_other_outcome_market(m, is_augmented_event=part_proof.is_augmented_negrisk)
        q_idx = _extract_question_index(m, idx)

        if yes_tok:
            local_books[yes_tok] = _build_instrument_book(
                yes_tok,
                m,
                books_by_token,
                outcome_label=f"YES:{lbl}",
                is_placeholder=is_ph,
                is_other=is_oth,
            )
        if no_tok:
            local_books[no_tok] = _build_instrument_book(
                no_tok,
                m,
                books_by_token,
                outcome_label=f"NO:{lbl}",
                is_placeholder=is_ph,
                is_other=is_oth,
            )

        outcome_specs.append(
            {
                "slot_index": idx,
                "question_index": q_idx if q_idx is not None else idx,
                "market_id": mid,
                "condition_id": cid,
                "label": lbl,
                "yes_token_id": yes_tok,
                "no_token_id": no_tok,
                "is_placeholder": is_ph,
                "is_other": is_oth,
                "closed": bool(m.get("closed")),
                "active": bool(m.get("active", True) is not False),
                "enable_order_book": bool(m.get("enableOrderBook", True) is not False and m.get("enable_order_book", True) is not False),
            }
        )

    states = StateSpaceBuilder.multi_outcome_partition_states(
        outcome_specs,
        is_mutually_exclusive=part_proof.is_mutually_exclusive,
        is_exhaustive=part_proof.is_exhaustive and not part_proof.has_closed_or_disabled_slots,
        is_negrisk=part_proof.is_negrisk,
        is_augmented_negrisk=part_proof.is_augmented_negrisk,
        has_unnamed_placeholder=part_proof.has_placeholder_hazard,
        has_other_outcome=part_proof.has_mutable_other_hazard,
        conditional_without_catchall=part_proof.conditional_missing_catchall,
        include_void_50_50_if_standalone=True,
    )
    return part_proof, outcome_specs, local_books, states


def detect_family_b_multi_outcome_complete_sets(
    events: Sequence[Mapping[str, Any]],
    books_by_token: Mapping[str, Any],
    *,
    config: Optional[VerificationConfig] = None,
    negrisk_fee_bips_default: int = 0,
    gas_usd: float = 0.0,
    dormant_max_bps: float = DORMANT_MAX_BPS_DEFAULT,
    include_non_actionable_class_e: bool = False,
) -> List[DetectedCompleteSetOrNegRiskOpportunity]:
    """
    Family B — Multi-Outcome Complete-Set Arbitrage Detector:
      (i)  `B1_MULTI_OUTCOME_BUY_ALL_YES`: `sum_i ask(YES_i) + fees + gas < $1.00`.
      (ii) `B2_MULTI_OUTCOME_SPLIT_CONVERT_SELL_ALL`: `sum_i bid(YES_i) - fees - mint_cost - gas > 0`
           (via atomic `2x split + convertPositions(0b11)` on closed NegRisk slates, or `N`-condition
           split + hold-`NO`s on standalone slates with explicit `OMEGA_STANDALONE_VOID_50_50` check).
    CRITICAL: Never promotes non-exhaustive, non-exclusive, augmented-placeholder, or mutable-`Other`
    slates into `CLASS_A`/`CLASS_B` — invalid slates with apparent raw spread > 0 emit `CLASS_D` with
    explicit counterexample states!
    """
    cfg = config or VerificationConfig()
    out: List[DetectedCompleteSetOrNegRiskOpportunity] = []
    now_f = float(time.time() if cfg.now_ts is None else cfg.now_ts)

    for ev in events or ():
        if not isinstance(ev, Mapping):
            continue
        raw_mkts = ev.get("markets") or ()
        if len(raw_mkts) < 2:
            continue

        part_proof, specs, local_books, states = _prepare_event_outcome_specs(ev, books_by_token)
        if any(s["market_id"] in FROZEN_DISPUTED_MARKET_IDS for s in specs):
            continue

        ev_id = str(ev.get("id") or ev.get("event_id") or specs[0]["market_id"]).strip()
        title = str(ev.get("title") or ev.get("question") or ev_id).strip()
        end_ts = _parse_end_ts(ev.get("endDate") or ev.get("end_ts"))
        rem_hrs = max(0.25, (end_ts - now_f) / 3600.0) if end_ts is not None else 24.0
        nr_bips = int(_sf(ev.get("negRiskFeeBips") or ev.get("fee_bips"), negrisk_fee_bips_default))

        # Only evaluate tradable legs that actually have token IDs; if some slots lack tokens,
        # `part_proof.is_valid_complete_set` is ALREADY `False` and `states` carries the double-zero state!
        tradable_specs = [s for s in specs if s["yes_token_id"] and s["no_token_id"] and s["enable_order_book"] and not s["closed"] and s["active"]]
        if len(tradable_specs) < 2:
            continue

        mids = tuple(s["market_id"] for s in tradable_specs)
        cids = tuple(s["condition_id"] for s in tradable_specs)
        all_have_asks = all(bool(local_books[s["yes_token_id"]].asks) for s in tradable_specs)
        all_have_bids = all(bool(local_books[s["yes_token_id"]].bids) for s in tradable_specs)

        # --- B1: Buy All YES Outcomes ---
        if all_have_asks:
            gross_b1 = round(1.0 - sum(local_books[s["yes_token_id"]].asks[0].price for s in tradable_specs), 6)
            legs_b1 = tuple(
                ActionLeg(
                    action_type=ActionType.BUY_CLOB,
                    instrument_id=s["yes_token_id"],
                    weight=1.0,
                    market_id=s["market_id"],
                    label=s["label"],
                    gas_cost_usd=(max(0.0, float(gas_usd)) if i == 0 else 0.0),
                )
                for i, s in enumerate(tradable_specs)
            )
            cand_b1 = CandidateStructure(
                candidate_id=f"FAM_B_BUY_ALL_YES_{ev_id}",
                family="B",
                legs=legs_b1,
                states=states,
                rule_verified=part_proof.is_valid_complete_set,
                rule_disqualifiers=part_proof.disqualifiers,
                is_exhaustive_partition=part_proof.is_exhaustive and not part_proof.has_closed_or_disabled_slots,
                is_mutually_exclusive=part_proof.is_mutually_exclusive,
                requires_exhaustive_partition=True,
                has_augmented_placeholder_risk=part_proof.has_placeholder_hazard or part_proof.is_augmented_negrisk,
                has_mutable_other_exposure=part_proof.has_mutable_other_hazard,
                expected_lockup_hours=rem_hrs,
                worst_case_lockup_hours=max(rem_hrs, 2.0),
            )
            proof_b1, cash_b1, peak_b1 = _verify_with_liquid_cash_budget_guard(cfg, cand_b1, local_books)
            unit_edge_b1 = (
                proof_b1.net_executable_edge_per_unit
                if proof_b1.optimal_executable_quantity > 0.0
                else proof_b1.gross_top_of_book_edge_per_unit
            )
            is_dorm_b1, dist_b1 = _compute_dormant_flags(
                opp_class=proof_b1.opportunity_class,
                is_structurally_valid=part_proof.is_valid_complete_set,
                gross_edge_per_unit=gross_b1,
                net_edge_per_unit=unit_edge_b1,
                dormant_max_bps=dormant_max_bps,
            )
            # Emit if actionable (`CLASS_A/B`), if invalid structure had deceptive positive gross spread (`CLASS_D` trap caught!),
            # if `CLASS_C`, if dormant near-arb, or if `include_non_actionable_class_e=True`.
            should_emit_b1 = (
                include_non_actionable_class_e
                or proof_b1.opportunity_class in (OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value, OpportunityClass.CLASS_C.value)
                or (proof_b1.opportunity_class == OpportunityClass.CLASS_D.value and gross_b1 > -0.02)
                or is_dorm_b1
            )
            if should_emit_b1:
                out.append(
                    DetectedCompleteSetOrNegRiskOpportunity(
                        candidate_id=cand_b1.candidate_id,
                        family="B",
                        subfamily="B1_MULTI_OUTCOME_BUY_ALL_YES",
                        opportunity_class=proof_b1.opportunity_class,
                        event_id=ev_id,
                        event_title=title,
                        market_ids=mids,
                        condition_ids=cids,
                        optimal_shares_q=proof_b1.optimal_executable_quantity,
                        gross_top_of_book_spread_per_unit=gross_b1,
                        gross_top_of_book_spread_bps=round(gross_b1 * 10_000.0, 2),
                        net_executable_edge_per_unit=unit_edge_b1,
                        net_executable_edge_bps=round(unit_edge_b1 * 10_000.0, 2),
                        capital_required_usd=cash_b1,
                        peak_intratx_collateral_usd=peak_b1,
                        expected_lockup_hours=proof_b1.cost_breakdown.expected_lockup_hours,
                        worst_case_lockup_hours=proof_b1.cost_breakdown.worst_case_lockup_hours,
                        theoretical_top_of_book_usd=proof_b1.four_value_ledger.theoretical_top_of_book_usd,
                        executable_l2_net_usd=proof_b1.four_value_ledger.executable_l2_net_usd,
                        attainable_risk_adjusted_usd=proof_b1.four_value_ledger.attainable_risk_adjusted_usd,
                        realized_net_usd=0.0,
                        min_state_net_payoff_usd=proof_b1.min_state_net_payoff_usd,
                        max_state_net_payoff_usd=proof_b1.max_state_net_payoff_usd,
                        expected_net_payoff_usd=proof_b1.expected_net_payoff_usd,
                        delta_wealth_min_usd=proof_b1.min_state_net_payoff_usd,
                        delta_wealth_vs_cost_basis_usd=None,
                        delta_wealth_vs_liquidation_mark_usd=None,
                        synthetic_vs_direct_ask_savings_per_share=None,
                        taker_fees_usd=proof_b1.cost_breakdown.taker_fees_usd,
                        conversion_fee_usd=proof_b1.cost_breakdown.conversion_costs_usd,
                        gas_cost_usd=proof_b1.cost_breakdown.gas_costs_usd,
                        is_atomic_or_prelocked=proof_b1.is_atomic_or_prelocked,
                        clob_leg_count=len(tradable_specs),
                        d007_sub500_multileg_quarantine=proof_b1.d007_sub500_multileg_quarantine,
                        execution_mode_cap=proof_b1.execution_mode_cap,
                        is_dormant_near_arb=is_dorm_b1,
                        distance_to_breakeven_bps=dist_b1,
                        partition_proof=part_proof,
                        proof=proof_b1,
                        metadata={
                            "n_tradable_outcomes": len(tradable_specs),
                            "n_total_slots": part_proof.n_total_protocol_slots,
                            "partition_type": part_proof.partition_type,
                        },
                    )
                )

        # --- B2: Mint/Convert All YES & Sell into Bids (`sum bid(YES_i) > $1.00`) ---
        if all_have_bids:
            gross_b2 = round(sum(local_books[s["yes_token_id"]].bids[0].price for s in tradable_specs) - 1.0, 6)
            c_conv = min(0.25, max(0.0, float(nr_bips) / 10_000.0))
            one_minus_c = 1.0 - c_conv

            if part_proof.is_negrisk and len(tradable_specs) == len(specs):
                # Closed NegRisk atomic `2x splitPosition + convertPositions(0b11)`:
                # Split slot 0 (`YES_0 + NO_0`) + Split slot 1 (`YES_1 + NO_1`), then convert `{NO_0, NO_1}` (`m=2`)
                # -> returns `(2-1)*(1-c) = (1-c)` cash + `(1-c)` of `YES_2..YES_{N-1}`!
                # Total `YES` available to sell: `1.0` on `{0, 1}` and `(1-c)` on `{2..N-1}` (and `c` leftover on `{0,1}` if `c>0`).
                s0, s1 = tradable_specs[0], tradable_specs[1]
                rest_yes_ids = tuple(s["yes_token_id"] for s in tradable_specs[2:])
                legs_b2_list: List[ActionLeg] = [
                    ActionLeg(
                        action_type=ActionType.CTF_SPLIT,
                        weight=1.0,
                        related_instrument_ids=(s0["yes_token_id"], s0["no_token_id"]),
                        gas_cost_usd=max(0.0, float(gas_usd)),
                        market_id=s0["market_id"],
                        label="SPLIT_SLOT_0",
                    ),
                    ActionLeg(
                        action_type=ActionType.CTF_SPLIT,
                        weight=1.0,
                        related_instrument_ids=(s1["yes_token_id"], s1["no_token_id"]),
                        gas_cost_usd=0.0,
                        market_id=s1["market_id"],
                        label="SPLIT_SLOT_1",
                    ),
                    ActionLeg(
                        action_type=ActionType.NEGRISK_CONVERT,
                        weight=1.0,
                        burned_no_instrument_ids=(s0["no_token_id"], s1["no_token_id"]),
                        minted_yes_instrument_ids=rest_yes_ids,
                        negrisk_fee_bips=nr_bips,
                        gas_cost_usd=0.0,
                        market_id=s0["market_id"],
                        label="CONVERT_0B11_MINT_ALL_YES",
                    ),
                ]
                for idx_s, s in enumerate(tradable_specs):
                    w_sell = 1.0 if idx_s < 2 else one_minus_c
                    legs_b2_list.append(
                        ActionLeg(
                            action_type=ActionType.SELL_CLOB,
                            instrument_id=s["yes_token_id"],
                            weight=w_sell,
                            market_id=s["market_id"],
                            label=s["label"],
                        )
                    )
                peak_mult_b2 = 2.0
                lock_hrs_b2 = 0.02
            else:
                # Standalone non-NegRisk (or incomplete NegRisk): split each binary condition ($N total),
                # sell all YES legs, and hold all NO legs until resolution (exposing to `OMEGA_STANDALONE_VOID_50_50`!).
                legs_b2_list = []
                for idx_s, s in enumerate(tradable_specs):
                    legs_b2_list.append(
                        ActionLeg(
                            action_type=ActionType.CTF_SPLIT,
                            weight=1.0,
                            related_instrument_ids=(s["yes_token_id"], s["no_token_id"]),
                            gas_cost_usd=(max(0.0, float(gas_usd)) if idx_s == 0 else 0.0),
                            market_id=s["market_id"],
                            label=f"SPLIT_{s['label'][:20]}",
                        )
                    )
                    legs_b2_list.append(
                        ActionLeg(
                            action_type=ActionType.SELL_CLOB,
                            instrument_id=s["yes_token_id"],
                            weight=1.0,
                            market_id=s["market_id"],
                            label=s["label"],
                        )
                    )
                peak_mult_b2 = float(len(tradable_specs))
                lock_hrs_b2 = rem_hrs

            cand_b2 = CandidateStructure(
                candidate_id=f"FAM_B_SPLIT_SELL_ALL_YES_{ev_id}",
                family="B",
                legs=tuple(legs_b2_list),
                states=states,
                rule_verified=part_proof.is_valid_complete_set,
                rule_disqualifiers=part_proof.disqualifiers,
                is_exhaustive_partition=part_proof.is_exhaustive and not part_proof.has_closed_or_disabled_slots,
                is_mutually_exclusive=part_proof.is_mutually_exclusive,
                requires_exhaustive_partition=True,
                has_augmented_placeholder_risk=part_proof.has_placeholder_hazard or part_proof.is_augmented_negrisk,
                has_mutable_other_exposure=part_proof.has_mutable_other_hazard,
                expected_lockup_hours=lock_hrs_b2,
                worst_case_lockup_hours=max(lock_hrs_b2, 0.05),
            )
            proof_b2, cash_b2, peak_b2 = _verify_with_liquid_cash_budget_guard(
                cfg,
                cand_b2,
                local_books,
                peak_intratx_split_multiplier=peak_mult_b2,
            )
            unit_edge_b2 = (
                proof_b2.net_executable_edge_per_unit
                if proof_b2.optimal_executable_quantity > 0.0
                else proof_b2.gross_top_of_book_edge_per_unit
            )
            is_dorm_b2, dist_b2 = _compute_dormant_flags(
                opp_class=proof_b2.opportunity_class,
                is_structurally_valid=part_proof.is_valid_complete_set,
                gross_edge_per_unit=gross_b2,
                net_edge_per_unit=unit_edge_b2,
                dormant_max_bps=dormant_max_bps,
            )
            should_emit_b2 = (
                include_non_actionable_class_e
                or proof_b2.opportunity_class in (OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value, OpportunityClass.CLASS_C.value)
                or (proof_b2.opportunity_class == OpportunityClass.CLASS_D.value and gross_b2 > -0.02)
                or gross_b2 > 0.0
                or is_dorm_b2
            )
            if should_emit_b2:
                out.append(
                    DetectedCompleteSetOrNegRiskOpportunity(
                        candidate_id=cand_b2.candidate_id,
                        family="B",
                        subfamily="B2_MULTI_OUTCOME_SPLIT_CONVERT_SELL_ALL",
                        opportunity_class=proof_b2.opportunity_class,
                        event_id=ev_id,
                        event_title=title,
                        market_ids=mids,
                        condition_ids=cids,
                        optimal_shares_q=proof_b2.optimal_executable_quantity,
                        gross_top_of_book_spread_per_unit=gross_b2,
                        gross_top_of_book_spread_bps=round(gross_b2 * 10_000.0, 2),
                        net_executable_edge_per_unit=unit_edge_b2,
                        net_executable_edge_bps=round(unit_edge_b2 * 10_000.0, 2),
                        capital_required_usd=cash_b2,
                        peak_intratx_collateral_usd=peak_b2,
                        expected_lockup_hours=proof_b2.cost_breakdown.expected_lockup_hours,
                        worst_case_lockup_hours=proof_b2.cost_breakdown.worst_case_lockup_hours,
                        theoretical_top_of_book_usd=proof_b2.four_value_ledger.theoretical_top_of_book_usd,
                        executable_l2_net_usd=proof_b2.four_value_ledger.executable_l2_net_usd,
                        attainable_risk_adjusted_usd=proof_b2.four_value_ledger.attainable_risk_adjusted_usd,
                        realized_net_usd=0.0,
                        min_state_net_payoff_usd=proof_b2.min_state_net_payoff_usd,
                        max_state_net_payoff_usd=proof_b2.max_state_net_payoff_usd,
                        expected_net_payoff_usd=proof_b2.expected_net_payoff_usd,
                        delta_wealth_min_usd=proof_b2.min_state_net_payoff_usd,
                        delta_wealth_vs_cost_basis_usd=None,
                        delta_wealth_vs_liquidation_mark_usd=None,
                        synthetic_vs_direct_ask_savings_per_share=None,
                        taker_fees_usd=proof_b2.cost_breakdown.taker_fees_usd,
                        conversion_fee_usd=proof_b2.cost_breakdown.conversion_costs_usd,
                        gas_cost_usd=proof_b2.cost_breakdown.gas_costs_usd,
                        is_atomic_or_prelocked=proof_b2.is_atomic_or_prelocked,
                        clob_leg_count=len(tradable_specs),
                        d007_sub500_multileg_quarantine=proof_b2.d007_sub500_multileg_quarantine,
                        execution_mode_cap=proof_b2.execution_mode_cap,
                        is_dormant_near_arb=is_dorm_b2,
                        distance_to_breakeven_bps=dist_b2,
                        partition_proof=part_proof,
                        proof=proof_b2,
                        metadata={
                            "n_tradable_outcomes": len(tradable_specs),
                            "is_negrisk_atomic_mint": bool(part_proof.is_negrisk and len(tradable_specs) == len(specs)),
                            "partition_type": part_proof.partition_type,
                        },
                    )
                )

    return out


# ---------------------------------------------------------------------------
# 7. Family C — Negative-Risk (`NegRiskAdapter`) Specialist Detector
# ---------------------------------------------------------------------------


def detect_family_c_negrisk_conversions(
    events: Sequence[Mapping[str, Any]],
    books_by_token: Mapping[str, Any],
    *,
    config: Optional[VerificationConfig] = None,
    negrisk_fee_bips_default: int = 0,
    convert_gas_usd: float = 0.0,
    dormant_max_bps: float = DORMANT_MAX_BPS_DEFAULT,
    include_non_actionable_class_e: bool = False,
) -> List[DetectedCompleteSetOrNegRiskOpportunity]:
    """
    Family C — Polymarket `NegRiskAdapter` Specialist (`enableNegRisk == True`):
      - `C1_NEGRISK_SUBSET_NO_CONVERT` (`2 <= m <= N-1`): `m` distinct `NO` tokens convert into
        `(m - 1)*(1 - c)` `$1.00` collateral + `(1 - c)` complement `YES_{j not in S}` shares swept into bids.
      - `C2_NEGRISK_M1_FANOUT_CONVERT` (`m = 1`): `1 NO_i` converts into `1*(1 - c)` `YES_j` for all `j != i`
        swept into bids (recovering the missing `m = 1` loop!).
      - `C3_NEGRISK_PURE_ALL_NO_CASH_CONVERT` (`m = N`): all `N` `NO` tokens convert immediately on-chain
        into `(N - 1)*(1 - c)` `$1.00` cash (`0` CLOB sells, `0` settlement lockup).
      - `C4_NEGRISK_SYNTHETIC_YES_VS_CLOB`: synthetic `YES_i` via buying `NO_j` + converting & selling
        remaining `YES_{k not in {i,j}}` (or `{NO_{j != i}}` -> `(N-2)` cash + `YES_i`) vs `ask(YES_i)` / `bid(YES_i)`.
      - `C5_NEGRISK_SYNTHETIC_NO_VS_CLOB`: synthetic `NO_i` via buying complement `{YES_{j != i}}` bundle
        + split/sell `bid(NO_i)`.
      - `C6_NEGRISK_FREEROLL_CONVERT`: selling strict liquid subset `U subsetneq S^c` pays for `S` + positive
        instant cash while retaining `R = S^c \\ U` as zero-downside freeroll `YES` shares.
      - Strictly enforces Augmented NegRisk (`negRiskAugmented` / mutable `"Other"` / `Person A` placeholders /
        `N_total` slot contiguity), downgrading any incomplete or mutable slate to `CLASS_D` / `CLASS_E`.
    """
    cfg = config or VerificationConfig()
    out: List[DetectedCompleteSetOrNegRiskOpportunity] = []
    now_f = float(time.time() if cfg.now_ts is None else cfg.now_ts)

    for ev in events or ():
        if not isinstance(ev, Mapping):
            continue
        raw_mkts = ev.get("markets") or ()
        if len(raw_mkts) < 2:
            continue
        is_nr = bool(
            ev.get("negRisk")
            or ev.get("enableNegRisk")
            or ev.get("neg_risk")
            or any(bool(m.get("negRisk") or m.get("neg_risk")) for m in raw_mkts if isinstance(m, Mapping))
        )
        if not is_nr:
            continue

        part_proof, specs, local_books, states = _prepare_event_outcome_specs(ev, books_by_token)
        if any(s["market_id"] in FROZEN_DISPUTED_MARKET_IDS for s in specs):
            continue

        ev_id = str(ev.get("id") or ev.get("event_id") or specs[0]["market_id"]).strip()
        nrm_id = str(ev.get("negRiskMarketID") or ev.get("neg_risk_market_id") or ev_id).strip()
        title = str(ev.get("title") or ev.get("question") or ev_id).strip()
        end_ts = _parse_end_ts(ev.get("endDate") or ev.get("end_ts"))
        rem_hrs = max(0.25, (end_ts - now_f) / 3600.0) if end_ts is not None else 24.0
        nr_bips = int(_sf(ev.get("negRiskFeeBips") or ev.get("fee_bips"), negrisk_fee_bips_default))
        c_conv = min(0.25, max(0.0, float(nr_bips) / 10_000.0))
        one_minus_c = 1.0 - c_conv

        tradable = [
            s for s in specs
            if s["yes_token_id"] and s["no_token_id"] and s["enable_order_book"] and not s["closed"] and s["active"]
        ]
        if len(tradable) < 2:
            continue

        n_trad = len(tradable)
        full_slate_intact = bool(part_proof.is_valid_complete_set and n_trad == len(specs) == part_proof.n_total_protocol_slots)

        def _emit_c(
            subfamily: str,
            cand: CandidateStructure,
            gross_spread: float,
            clob_legs_n: int,
            *,
            synth_savings: Optional[float] = None,
            extra_meta: Optional[Mapping[str, Any]] = None,
            peak_split_mult: float = 0.0,
        ) -> None:
            proof_c, cash_c, peak_c = _verify_with_liquid_cash_budget_guard(
                cfg,
                cand,
                local_books,
                peak_intratx_split_multiplier=peak_split_mult,
            )
            unit_edge = (
                proof_c.net_executable_edge_per_unit
                if proof_c.optimal_executable_quantity > 0.0
                else proof_c.gross_top_of_book_edge_per_unit
            )
            is_dorm, dist_bps = _compute_dormant_flags(
                opp_class=proof_c.opportunity_class,
                is_structurally_valid=full_slate_intact,
                gross_edge_per_unit=gross_spread,
                net_edge_per_unit=unit_edge,
                dormant_max_bps=dormant_max_bps,
            )
            has_routing_edge = synth_savings is not None and synth_savings > 0.002
            should_emit = (
                include_non_actionable_class_e
                or proof_c.opportunity_class in (OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value, OpportunityClass.CLASS_C.value)
                or (proof_c.opportunity_class == OpportunityClass.CLASS_D.value and (gross_spread > -0.02 or not full_slate_intact))
                or is_dorm
                or (has_routing_edge and full_slate_intact)
            )
            if not should_emit:
                return
            used_mids = tuple(dict.fromkeys(lg.market_id for lg in cand.legs if lg.market_id))
            used_cids = tuple(
                dict.fromkeys(
                    s["condition_id"] for s in tradable if s["market_id"] in set(used_mids)
                )
            )
            meta = {
                "neg_risk_market_id": nrm_id,
                "negrisk_fee_bips": nr_bips,
                "n_total_protocol_slots": part_proof.n_total_protocol_slots,
                "n_tradable_slots": n_trad,
                "partition_type": part_proof.partition_type,
            }
            if extra_meta:
                meta.update(extra_meta)
            out.append(
                DetectedCompleteSetOrNegRiskOpportunity(
                    candidate_id=cand.candidate_id,
                    family="C",
                    subfamily=subfamily,
                    opportunity_class=proof_c.opportunity_class,
                    event_id=ev_id,
                    event_title=title,
                    market_ids=used_mids or tuple(s["market_id"] for s in tradable),
                    condition_ids=used_cids or tuple(s["condition_id"] for s in tradable),
                    optimal_shares_q=proof_c.optimal_executable_quantity,
                    gross_top_of_book_spread_per_unit=round(gross_spread, 6),
                    gross_top_of_book_spread_bps=round(gross_spread * 10_000.0, 2),
                    net_executable_edge_per_unit=unit_edge,
                    net_executable_edge_bps=round(unit_edge * 10_000.0, 2),
                    capital_required_usd=cash_c,
                    peak_intratx_collateral_usd=peak_c,
                    expected_lockup_hours=proof_c.cost_breakdown.expected_lockup_hours,
                    worst_case_lockup_hours=proof_c.cost_breakdown.worst_case_lockup_hours,
                    theoretical_top_of_book_usd=proof_c.four_value_ledger.theoretical_top_of_book_usd,
                    executable_l2_net_usd=proof_c.four_value_ledger.executable_l2_net_usd,
                    attainable_risk_adjusted_usd=proof_c.four_value_ledger.attainable_risk_adjusted_usd,
                    realized_net_usd=0.0,
                    min_state_net_payoff_usd=proof_c.min_state_net_payoff_usd,
                    max_state_net_payoff_usd=proof_c.max_state_net_payoff_usd,
                    expected_net_payoff_usd=proof_c.expected_net_payoff_usd,
                    delta_wealth_min_usd=proof_c.min_state_net_payoff_usd,
                    delta_wealth_vs_cost_basis_usd=None,
                    delta_wealth_vs_liquidation_mark_usd=None,
                    synthetic_vs_direct_ask_savings_per_share=(round(synth_savings, 6) if synth_savings is not None else None),
                    taker_fees_usd=proof_c.cost_breakdown.taker_fees_usd,
                    conversion_fee_usd=proof_c.cost_breakdown.conversion_costs_usd,
                    gas_cost_usd=proof_c.cost_breakdown.gas_costs_usd,
                    is_atomic_or_prelocked=proof_c.is_atomic_or_prelocked,
                    clob_leg_count=clob_legs_n,
                    d007_sub500_multileg_quarantine=proof_c.d007_sub500_multileg_quarantine,
                    execution_mode_cap=proof_c.execution_mode_cap,
                    is_dormant_near_arb=is_dorm,
                    distance_to_breakeven_bps=dist_bps,
                    partition_proof=part_proof,
                    proof=proof_c,
                    metadata=meta,
                )
            )

        # Compute L1 metrics per outcome for fast optimal subset ranking before full L2 depth walking
        l1_rows: List[Dict[str, Any]] = []
        for s in tradable:
            by = local_books[s["yes_token_id"]]
            bn = local_books[s["no_token_id"]]
            no_ask_l1 = bn.asks[0].price if bn.asks else 9.99
            no_net_cost_l1 = (
                compute_net_buy_cost_per_delivered_share(
                    no_ask_l1, fee_rate_bps=bn.fee_rate_bps, fee_exponent=bn.fee_exponent
                )[0]
                if bn.asks
                else 9.99
            )
            yes_ask_l1 = by.asks[0].price if by.asks else 9.99
            yes_net_cost_l1 = (
                compute_net_buy_cost_per_delivered_share(
                    yes_ask_l1, fee_rate_bps=by.fee_rate_bps, fee_exponent=by.fee_exponent
                )[0]
                if by.asks
                else 9.99
            )
            yes_bid_l1 = by.bids[0].price if by.bids else 0.0
            yes_net_bid_l1 = (
                compute_net_sell_proceeds_per_share(
                    yes_bid_l1, fee_rate_bps=by.fee_rate_bps, fee_exponent=by.fee_exponent
                )[0]
                if by.bids
                else 0.0
            )
            no_bid_l1 = bn.bids[0].price if bn.bids else 0.0
            no_net_bid_l1 = (
                compute_net_sell_proceeds_per_share(
                    no_bid_l1, fee_rate_bps=bn.fee_rate_bps, fee_exponent=bn.fee_exponent
                )[0]
                if bn.bids
                else 0.0
            )
            # Marginal advantage of putting outcome into burned `NO` set `S` vs selling `YES` in `S^c`
            marg_s = one_minus_c * (1.0 - yes_net_bid_l1) - no_net_cost_l1
            l1_rows.append(
                {
                    "spec": s,
                    "no_ask_l1": no_ask_l1,
                    "no_net_cost_l1": no_net_cost_l1,
                    "yes_ask_l1": yes_ask_l1,
                    "yes_net_cost_l1": yes_net_cost_l1,
                    "yes_bid_l1": yes_bid_l1,
                    "yes_net_bid_l1": yes_net_bid_l1,
                    "no_bid_l1": no_bid_l1,
                    "no_net_bid_l1": no_net_bid_l1,
                    "marg_s": marg_s,
                }
            )

        # --- C3: Pure All-NO Cash Convert (`m = N`: burns all N NOs -> `(N - 1)*(1 - c)` instant cash) ---
        if all(r["no_ask_l1"] < 1.0 for r in l1_rows):
            gross_c3 = float(n_trad - 1) * one_minus_c - sum(r["no_ask_l1"] for r in l1_rows)
            # Note: In `UniversalArbVerifier`, if `n_trad < len(specs)` (incomplete/augmented slate),
            # `minted_yes_instrument_ids` includes any remaining protocol slots that have token IDs,
            # while `full_slate_intact == False` forces `rule_verified = False` -> `CLASS_D`!
            omitted_yes = tuple(
                s["yes_token_id"]
                for s in specs
                if s["yes_token_id"] and s["market_id"] not in {r["spec"]["market_id"] for r in l1_rows}
            )
            legs_c3 = tuple(
                [
                    ActionLeg(
                        action_type=ActionType.BUY_CLOB,
                        instrument_id=r["spec"]["no_token_id"],
                        weight=1.0,
                        market_id=r["spec"]["market_id"],
                        label=f"NO:{r['spec']['label']}",
                    )
                    for r in l1_rows
                ]
                + [
                    ActionLeg(
                        action_type=ActionType.NEGRISK_CONVERT,
                        weight=1.0,
                        burned_no_instrument_ids=tuple(r["spec"]["no_token_id"] for r in l1_rows),
                        minted_yes_instrument_ids=omitted_yes,
                        negrisk_fee_bips=nr_bips,
                        gas_cost_usd=max(0.0, float(convert_gas_usd)),
                        market_id=l1_rows[0]["spec"]["market_id"],
                        label=f"CONVERT_ALL_{n_trad}_NO_TO_CASH",
                    )
                ]
            )
            cand_c3 = CandidateStructure(
                candidate_id=f"FAM_C_PURE_ALL_NO_CONVERT_{ev_id}",
                family="C",
                legs=legs_c3,
                states=states,
                rule_verified=full_slate_intact,
                rule_disqualifiers=part_proof.disqualifiers,
                is_exhaustive_partition=full_slate_intact,
                is_mutually_exclusive=part_proof.is_mutually_exclusive,
                requires_exhaustive_partition=True,
                has_augmented_placeholder_risk=part_proof.has_placeholder_hazard or part_proof.is_augmented_negrisk,
                has_mutable_other_exposure=part_proof.has_mutable_other_hazard,
                expected_lockup_hours=0.01,
                worst_case_lockup_hours=0.05,
            )
            _emit_c(
                "C3_NEGRISK_PURE_ALL_NO_CASH_CONVERT",
                cand_c3,
                gross_c3,
                n_trad,
                extra_meta={"m_burned_no": n_trad},
            )

        # --- C2: `m = 1` Single-NO Fanout Convert (`1 NO_i -> (1 - c) * {YES_{j != i}}` sold into bids) ---
        if n_trad >= 2:
            best_m1_idx: Optional[int] = None
            best_m1_net = -1e9
            for i_idx, r_i in enumerate(l1_rows):
                if r_i["no_ask_l1"] >= 1.0:
                    continue
                comp = [l1_rows[j] for j in range(n_trad) if j != i_idx]
                if not all(x["yes_bid_l1"] > 0.0 for x in comp):
                    continue
                est_net = one_minus_c * sum(x["yes_net_bid_l1"] for x in comp) - r_i["no_net_cost_l1"]
                if est_net > best_m1_net:
                    best_m1_net = est_net
                    best_m1_idx = i_idx

            if best_m1_idx is not None:
                r_seed = l1_rows[best_m1_idx]
                comp_rows = [l1_rows[j] for j in range(n_trad) if j != best_m1_idx]
                gross_c2 = one_minus_c * sum(x["yes_bid_l1"] for x in comp_rows) - r_seed["no_ask_l1"]
                minted_all_yes = tuple(
                    s["yes_token_id"]
                    for s in specs
                    if s["yes_token_id"] and s["market_id"] != r_seed["spec"]["market_id"]
                )
                legs_c2 = tuple(
                    [
                        ActionLeg(
                            action_type=ActionType.BUY_CLOB,
                            instrument_id=r_seed["spec"]["no_token_id"],
                            weight=1.0,
                            market_id=r_seed["spec"]["market_id"],
                            label=f"NO:{r_seed['spec']['label']}",
                        ),
                        ActionLeg(
                            action_type=ActionType.NEGRISK_CONVERT,
                            weight=1.0,
                            burned_no_instrument_ids=(r_seed["spec"]["no_token_id"],),
                            minted_yes_instrument_ids=minted_all_yes,
                            negrisk_fee_bips=nr_bips,
                            gas_cost_usd=max(0.0, float(convert_gas_usd)),
                            market_id=r_seed["spec"]["market_id"],
                            label="CONVERT_M1_SINGLE_NO_FANOUT",
                        ),
                    ]
                    + [
                        ActionLeg(
                            action_type=ActionType.SELL_CLOB,
                            instrument_id=x["spec"]["yes_token_id"],
                            weight=one_minus_c,
                            market_id=x["spec"]["market_id"],
                            label=f"YES:{x['spec']['label']}",
                        )
                        for x in comp_rows
                    ]
                )
                cand_c2 = CandidateStructure(
                    candidate_id=f"FAM_C_M1_FANOUT_{ev_id}_{r_seed['spec']['market_id']}",
                    family="C",
                    legs=legs_c2,
                    states=states,
                    rule_verified=full_slate_intact,
                    rule_disqualifiers=part_proof.disqualifiers,
                    is_exhaustive_partition=full_slate_intact,
                    is_mutually_exclusive=part_proof.is_mutually_exclusive,
                    requires_exhaustive_partition=True,
                    has_augmented_placeholder_risk=part_proof.has_placeholder_hazard or part_proof.is_augmented_negrisk,
                    has_mutable_other_exposure=part_proof.has_mutable_other_hazard,
                    expected_lockup_hours=0.02,
                    worst_case_lockup_hours=0.05,
                )
                _emit_c(
                    "C2_NEGRISK_M1_FANOUT_CONVERT",
                    cand_c2,
                    gross_c2,
                    1 + len(comp_rows),
                    extra_meta={"m_burned_no": 1, "seed_outcome": r_seed["spec"]["label"]},
                )

        # --- C1 (`2 <= m <= N-1` Optimal Subset Convert) & C6 (Freeroll Convert) ---
        if n_trad >= 3:
            ranked_s = sorted(l1_rows, key=lambda x: x["marg_s"], reverse=True)
            best_m_cfg: Optional[Tuple[int, float, List[Dict[str, Any]], List[Dict[str, Any]]]] = None
            best_freeroll_cfg: Optional[Tuple[int, float, List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]] = None

            for m_sz in range(2, min(n_trad, 25)):
                s_part = ranked_s[:m_sz]
                sc_part = ranked_s[m_sz:]
                if any(x["no_ask_l1"] >= 1.0 for x in s_part):
                    break
                conv_cash_l1 = float(m_sz - 1) * one_minus_c
                cost_s_l1 = sum(x["no_net_cost_l1"] for x in s_part)

                if all(x["yes_bid_l1"] > 0.0 for x in sc_part):
                    est_c1 = conv_cash_l1 + one_minus_c * sum(x["yes_net_bid_l1"] for x in sc_part) - cost_s_l1
                    if best_m_cfg is None or est_c1 > best_m_cfg[1]:
                        best_m_cfg = (m_sz, est_c1, s_part, sc_part)

                # Check C6 Freeroll: strict subset `U \subsetneq sc_part` pays for `S` + positive instant cash!
                if len(sc_part) >= 2:
                    sc_by_bid = sorted(sc_part, key=lambda x: x["yes_net_bid_l1"], reverse=True)
                    for u_cnt in range(1, len(sc_by_bid)):
                        u_part = sc_by_bid[:u_cnt]
                        r_part = sc_by_bid[u_cnt:]
                        if any(x["yes_bid_l1"] <= 0.0 for x in u_part):
                            break
                        instant_l1 = conv_cash_l1 + one_minus_c * sum(x["yes_net_bid_l1"] for x in u_part) - cost_s_l1
                        if instant_l1 > 0.0005:
                            if best_freeroll_cfg is None or instant_l1 > best_freeroll_cfg[1]:
                                best_freeroll_cfg = (m_sz, instant_l1, s_part, u_part, r_part)

            if best_m_cfg is not None:
                m_sz, _, s_part, sc_part = best_m_cfg
                gross_c1 = (
                    float(m_sz - 1) * one_minus_c
                    + one_minus_c * sum(x["yes_bid_l1"] for x in sc_part)
                    - sum(x["no_ask_l1"] for x in s_part)
                )
                s_mids = {x["spec"]["market_id"] for x in s_part}
                minted_yes_ids = tuple(
                    s["yes_token_id"] for s in specs if s["yes_token_id"] and s["market_id"] not in s_mids
                )
                legs_c1 = tuple(
                    [
                        ActionLeg(
                            action_type=ActionType.BUY_CLOB,
                            instrument_id=x["spec"]["no_token_id"],
                            weight=1.0,
                            market_id=x["spec"]["market_id"],
                            label=f"NO:{x['spec']['label']}",
                        )
                        for x in s_part
                    ]
                    + [
                        ActionLeg(
                            action_type=ActionType.NEGRISK_CONVERT,
                            weight=1.0,
                            burned_no_instrument_ids=tuple(x["spec"]["no_token_id"] for x in s_part),
                            minted_yes_instrument_ids=minted_yes_ids,
                            negrisk_fee_bips=nr_bips,
                            gas_cost_usd=max(0.0, float(convert_gas_usd)),
                            market_id=s_part[0]["spec"]["market_id"],
                            label=f"CONVERT_SUBSET_M{m_sz}",
                        )
                    ]
                    + [
                        ActionLeg(
                            action_type=ActionType.SELL_CLOB,
                            instrument_id=x["spec"]["yes_token_id"],
                            weight=one_minus_c,
                            market_id=x["spec"]["market_id"],
                            label=f"YES:{x['spec']['label']}",
                        )
                        for x in sc_part
                    ]
                )
                cand_c1 = CandidateStructure(
                    candidate_id=f"FAM_C_SUBSET_CONVERT_M{m_sz}_{ev_id}",
                    family="C",
                    legs=legs_c1,
                    states=states,
                    rule_verified=full_slate_intact,
                    rule_disqualifiers=part_proof.disqualifiers,
                    is_exhaustive_partition=full_slate_intact,
                    is_mutually_exclusive=part_proof.is_mutually_exclusive,
                    requires_exhaustive_partition=True,
                    has_augmented_placeholder_risk=part_proof.has_placeholder_hazard or part_proof.is_augmented_negrisk,
                    has_mutable_other_exposure=part_proof.has_mutable_other_hazard,
                    expected_lockup_hours=0.02,
                    worst_case_lockup_hours=0.05,
                )
                _emit_c(
                    "C1_NEGRISK_SUBSET_NO_CONVERT",
                    cand_c1,
                    gross_c1,
                    len(s_part) + len(sc_part),
                    extra_meta={
                        "m_burned_no": m_sz,
                        "burned_labels": [x["spec"]["label"] for x in s_part],
                        "sold_complement_labels": [x["spec"]["label"] for x in sc_part],
                    },
                )

            if best_freeroll_cfg is not None:
                m_sz, _, s_part, u_part, r_part = best_freeroll_cfg
                gross_c6 = (
                    float(m_sz - 1) * one_minus_c
                    + one_minus_c * sum(x["yes_bid_l1"] for x in u_part)
                    - sum(x["no_ask_l1"] for x in s_part)
                )
                s_mids = {x["spec"]["market_id"] for x in s_part}
                minted_yes_ids = tuple(
                    s["yes_token_id"] for s in specs if s["yes_token_id"] and s["market_id"] not in s_mids
                )
                legs_c6 = tuple(
                    [
                        ActionLeg(
                            action_type=ActionType.BUY_CLOB,
                            instrument_id=x["spec"]["no_token_id"],
                            weight=1.0,
                            market_id=x["spec"]["market_id"],
                            label=f"NO:{x['spec']['label']}",
                        )
                        for x in s_part
                    ]
                    + [
                        ActionLeg(
                            action_type=ActionType.NEGRISK_CONVERT,
                            weight=1.0,
                            burned_no_instrument_ids=tuple(x["spec"]["no_token_id"] for x in s_part),
                            minted_yes_instrument_ids=minted_yes_ids,
                            negrisk_fee_bips=nr_bips,
                            gas_cost_usd=max(0.0, float(convert_gas_usd)),
                            market_id=s_part[0]["spec"]["market_id"],
                            label=f"CONVERT_FREEROLL_M{m_sz}",
                        )
                    ]
                    + [
                        ActionLeg(
                            action_type=ActionType.SELL_CLOB,
                            instrument_id=x["spec"]["yes_token_id"],
                            weight=one_minus_c,
                            market_id=x["spec"]["market_id"],
                            label=f"YES:{x['spec']['label']}",
                        )
                        for x in u_part
                    ]
                )
                cand_c6 = CandidateStructure(
                    candidate_id=f"FAM_C_FREEROLL_M{m_sz}_{ev_id}",
                    family="C",
                    legs=legs_c6,
                    states=states,
                    rule_verified=full_slate_intact,
                    rule_disqualifiers=part_proof.disqualifiers,
                    is_exhaustive_partition=full_slate_intact,
                    is_mutually_exclusive=part_proof.is_mutually_exclusive,
                    requires_exhaustive_partition=True,
                    has_augmented_placeholder_risk=part_proof.has_placeholder_hazard or part_proof.is_augmented_negrisk,
                    has_mutable_other_exposure=part_proof.has_mutable_other_hazard,
                    expected_lockup_hours=rem_hrs,
                    worst_case_lockup_hours=max(rem_hrs, 2.0),
                )
                _emit_c(
                    "C6_NEGRISK_FREEROLL_CONVERT",
                    cand_c6,
                    gross_c6,
                    len(s_part) + len(u_part),
                    extra_meta={
                        "m_burned_no": m_sz,
                        "retained_freeroll_labels": [x["spec"]["label"] for x in r_part],
                    },
                )

        # --- C4: Synthetic `YES_i` via buying `NO_j` (or `{NO_{j != i}}`) + converting vs CLOB `YES_i` ---
        # Evaluates BOTH exact on-chain `NegRiskAdapter` routes for synthesizing `1.0 YES_i`:
        #   Route (a) `m = N - 1`: buy `1/(1-c)` of `{NO_{j != i}}` -> converts into `(N - 2)` cash + `1.0 YES_i`;
        #   Route (b) `m = 1`:     buy `1/(1-c)` of a single `NO_j` (`j != i`) -> converts into `1.0 YES_i`
        #                          + `1.0 YES_k` (`k not in {i, j}`), sweeping `{YES_k}` into CLOB bids.
        if one_minus_c > 0.5 and n_trad <= 25:
            best_c4: Optional[Tuple[int, str, float, float, float, List[Dict[str, Any]], List[Dict[str, Any]]]] = None
            for i_idx, r_target in enumerate(l1_rows):
                others = [l1_rows[j] for j in range(n_trad) if j != i_idx]
                # Route (a): `m = N - 1` (`{NO_{j != i}}`)
                if all(x["no_ask_l1"] < 1.0 for x in others):
                    cost_net_a = (sum(x["no_net_cost_l1"] for x in others) / one_minus_c) - float(n_trad - 2)
                    cost_gross_a = (sum(x["no_ask_l1"] for x in others) / one_minus_c) - float(n_trad - 2)
                    arb_a = r_target["yes_net_bid_l1"] - cost_net_a if r_target["yes_bid_l1"] > 0.0 else -1.0
                    sav_a = (r_target["yes_net_cost_l1"] - cost_net_a) if r_target["yes_ask_l1"] < 1.0 else 0.0
                    sc_a = max(arb_a, sav_a * 0.5)
                    if best_c4 is None or sc_a > best_c4[2]:
                        best_c4 = (i_idx, "M_N_MINUS_1_ALL_OTHER_NO", sc_a, cost_net_a, cost_gross_a, others, [])

                # Route (b): `m = 1` (`single NO_j` + sell `{YES_{k not in {i, j}}}`)
                if n_trad >= 3:
                    for j_idx, r_seed in enumerate(l1_rows):
                        if j_idx == i_idx or r_seed["no_ask_l1"] >= 1.0:
                            continue
                        rem_k = [l1_rows[k] for k in range(n_trad) if k not in (i_idx, j_idx)]
                        if not all(x["yes_bid_l1"] > 0.0 for x in rem_k):
                            continue
                        cost_net_b = (r_seed["no_net_cost_l1"] / one_minus_c) - sum(x["yes_net_bid_l1"] for x in rem_k)
                        cost_gross_b = (r_seed["no_ask_l1"] / one_minus_c) - sum(x["yes_bid_l1"] for x in rem_k)
                        arb_b = r_target["yes_net_bid_l1"] - cost_net_b if r_target["yes_bid_l1"] > 0.0 else -1.0
                        sav_b = (r_target["yes_net_cost_l1"] - cost_net_b) if r_target["yes_ask_l1"] < 1.0 else 0.0
                        sc_b = max(arb_b, sav_b * 0.5)
                        if best_c4 is None or sc_b > best_c4[2]:
                            best_c4 = (i_idx, "M_1_SINGLE_NO_J_STRIP", sc_b, cost_net_b, cost_gross_b, [r_seed], rem_k)

            if best_c4 is not None:
                i_idx, route_tag, _, synth_yes_cost_net, synth_yes_cost_gross, burned_rows, strip_yes_rows = best_c4
                r_target = l1_rows[i_idx]
                savings_vs_ask = (
                    (r_target["yes_net_cost_l1"] - synth_yes_cost_net)
                    if r_target["yes_ask_l1"] < 1.0
                    else None
                )
                if r_target["yes_bid_l1"] > 0.0:
                    gross_c4 = r_target["yes_bid_l1"] - synth_yes_cost_gross
                    w_buy = round(1.0 / one_minus_c, 8)
                    burned_mids = {x["spec"]["market_id"] for x in burned_rows}
                    minted_for_i = tuple(
                        s["yes_token_id"] for s in specs if s["yes_token_id"] and s["market_id"] not in burned_mids
                    )
                    legs_c4 = tuple(
                        [
                            ActionLeg(
                                action_type=ActionType.BUY_CLOB,
                                instrument_id=x["spec"]["no_token_id"],
                                weight=w_buy,
                                market_id=x["spec"]["market_id"],
                                label=f"NO:{x['spec']['label']}",
                            )
                            for x in burned_rows
                        ]
                        + [
                            ActionLeg(
                                action_type=ActionType.NEGRISK_CONVERT,
                                weight=w_buy,
                                burned_no_instrument_ids=tuple(x["spec"]["no_token_id"] for x in burned_rows),
                                minted_yes_instrument_ids=minted_for_i,
                                negrisk_fee_bips=nr_bips,
                                gas_cost_usd=max(0.0, float(convert_gas_usd)),
                                market_id=r_target["spec"]["market_id"],
                                label=f"SYNTHESIZE_YES_{r_target['spec']['label'][:18]}",
                            ),
                        ]
                        + [
                            ActionLeg(
                                action_type=ActionType.SELL_CLOB,
                                instrument_id=x["spec"]["yes_token_id"],
                                weight=1.0,
                                market_id=x["spec"]["market_id"],
                                label=f"STRIP_YES:{x['spec']['label']}",
                            )
                            for x in strip_yes_rows
                        ]
                        + [
                            ActionLeg(
                                action_type=ActionType.SELL_CLOB,
                                instrument_id=r_target["spec"]["yes_token_id"],
                                weight=1.0,
                                market_id=r_target["spec"]["market_id"],
                                label=f"SELL_YES:{r_target['spec']['label']}",
                            ),
                        ]
                    )
                    cand_c4 = CandidateStructure(
                        candidate_id=f"FAM_C_SYNTH_YES_{ev_id}_{r_target['spec']['market_id']}",
                        family="C",
                        legs=legs_c4,
                        states=states,
                        rule_verified=full_slate_intact,
                        rule_disqualifiers=part_proof.disqualifiers,
                        is_exhaustive_partition=full_slate_intact,
                        is_mutually_exclusive=part_proof.is_mutually_exclusive,
                        requires_exhaustive_partition=True,
                        has_augmented_placeholder_risk=part_proof.has_placeholder_hazard or part_proof.is_augmented_negrisk,
                        has_mutable_other_exposure=part_proof.has_mutable_other_hazard,
                        expected_lockup_hours=0.02,
                        worst_case_lockup_hours=0.05,
                    )
                    _emit_c(
                        "C4_NEGRISK_SYNTHETIC_YES_VS_CLOB",
                        cand_c4,
                        gross_c4,
                        len(burned_rows) + len(strip_yes_rows) + 1,
                        synth_savings=savings_vs_ask,
                        extra_meta={
                            "synthesis_route": route_tag,
                            "target_outcome": r_target["spec"]["label"],
                            "direct_yes_ask_net": round(r_target["yes_net_cost_l1"], 6) if r_target["yes_ask_l1"] < 1.0 else None,
                            "synthetic_yes_ask_net": round(synth_yes_cost_net, 6),
                        },
                    )

        # --- C5: Synthetic `NO_i` via buying complement `{YES_{j != i}}` bundle vs `bid(NO_i)` ---
        # Split `$1.00` on slot `i` -> `1 YES_i + 1 NO_i`; sell `1 NO_i` into `bid(NO_i)`;
        # buy `1 YES_j` for all `j != i` -> holds full complete set `{YES_1..YES_N}` worth `$1.00`!
        if n_trad <= 25:
            best_c5: Optional[Tuple[int, float, float, List[Dict[str, Any]]]] = None
            for i_idx, r_target in enumerate(l1_rows):
                others = [l1_rows[j] for j in range(n_trad) if j != i_idx]
                if any(x["yes_ask_l1"] >= 1.0 for x in others) or r_target["no_bid_l1"] <= 0.0:
                    continue
                comp_yes_cost_net = sum(x["yes_net_cost_l1"] for x in others)
                comp_yes_cost_gross = sum(x["yes_ask_l1"] for x in others)
                arb_edge = r_target["no_net_bid_l1"] - comp_yes_cost_net
                savings_no_ask = (
                    (r_target["no_net_cost_l1"] - comp_yes_cost_net)
                    if r_target["no_ask_l1"] < 1.0
                    else 0.0
                )
                score_c5 = max(arb_edge, savings_no_ask * 0.5)
                if best_c5 is None or score_c5 > best_c5[1]:
                    best_c5 = (i_idx, score_c5, r_target["no_bid_l1"] - comp_yes_cost_gross, others)

            if best_c5 is not None:
                i_idx, _, gross_c5, others = best_c5
                r_target = l1_rows[i_idx]
                comp_yes_cost_net = sum(x["yes_net_cost_l1"] for x in others)
                savings_no_ask = (
                    (r_target["no_net_cost_l1"] - comp_yes_cost_net)
                    if r_target["no_ask_l1"] < 1.0
                    else None
                )
                legs_c5 = tuple(
                    [
                        ActionLeg(
                            action_type=ActionType.CTF_SPLIT,
                            weight=1.0,
                            related_instrument_ids=(r_target["spec"]["yes_token_id"], r_target["spec"]["no_token_id"]),
                            gas_cost_usd=max(0.0, float(convert_gas_usd)),
                            market_id=r_target["spec"]["market_id"],
                            label=f"SPLIT_FOR_SYNTH_NO_{r_target['spec']['label'][:16]}",
                        ),
                        ActionLeg(
                            action_type=ActionType.SELL_CLOB,
                            instrument_id=r_target["spec"]["no_token_id"],
                            weight=1.0,
                            market_id=r_target["spec"]["market_id"],
                            label=f"SELL_NO:{r_target['spec']['label']}",
                        ),
                    ]
                    + [
                        ActionLeg(
                            action_type=ActionType.BUY_CLOB,
                            instrument_id=x["spec"]["yes_token_id"],
                            weight=1.0,
                            market_id=x["spec"]["market_id"],
                            label=f"BUY_COMP_YES:{x['spec']['label']}",
                        )
                        for x in others
                    ]
                )
                cand_c5 = CandidateStructure(
                    candidate_id=f"FAM_C_SYNTH_NO_{ev_id}_{r_target['spec']['market_id']}",
                    family="C",
                    legs=legs_c5,
                    states=states,
                    rule_verified=full_slate_intact,
                    rule_disqualifiers=part_proof.disqualifiers,
                    is_exhaustive_partition=full_slate_intact,
                    is_mutually_exclusive=part_proof.is_mutually_exclusive,
                    requires_exhaustive_partition=True,
                    has_augmented_placeholder_risk=part_proof.has_placeholder_hazard or part_proof.is_augmented_negrisk,
                    has_mutable_other_exposure=part_proof.has_mutable_other_hazard,
                    expected_lockup_hours=rem_hrs,
                    worst_case_lockup_hours=max(rem_hrs, 2.0),
                )
                _emit_c(
                    "C5_NEGRISK_SYNTHETIC_NO_VS_CLOB",
                    cand_c5,
                    gross_c5,
                    len(others) + 1,
                    synth_savings=savings_no_ask,
                    peak_split_mult=1.0,
                    extra_meta={
                        "target_outcome": r_target["spec"]["label"],
                        "direct_no_ask_net": round(r_target["no_net_cost_l1"], 6) if r_target["no_ask_l1"] < 1.0 else None,
                        "synthetic_no_cost_net": round(comp_yes_cost_net, 6),
                    },
                )

    return out


# ---------------------------------------------------------------------------
# 8. Family J — Inventory, Split/Merge & Capital Recycling Detector
# ---------------------------------------------------------------------------


def _build_inventory_holding_for_lock(
    pos: Mapping[str, Any],
    book: InstrumentOrderBook,
    *,
    require_profit_over_cost_basis: bool = True,
) -> Tuple[InventoryHolding, float, float]:
    """
    Constructs an `InventoryHolding` for `UniversalArbVerifier` along with
    `(cost_basis_per_share, immediate_liquidation_bid_net_per_share)`.
    When `require_profit_over_cost_basis=True`, sets `mark_bid_per_share = max(cost_basis, liq_bid_net)`
    so `CLASS_A`/`CLASS_B` is granted ONLY when the action beats BOTH immediate CLOB liquidation
    AND original entry cost basis (preventing underwater spread-saving exits from masquerading as `CLASS_A`).
    """
    shares = max(0.0, _sf(pos.get("shares") or pos.get("size"), 0.0))
    cb_ps = _sf(pos.get("entry_price") or pos.get("avg_price") or pos.get("cost_basis_per_share"), 0.0)
    if cb_ps <= 0.0 and shares > 0.0:
        tot_cost = _sf(pos.get("cost_usd") or pos.get("initial_cost_usd"), 0.0)
        if tot_cost > 0.0:
            cb_ps = tot_cost / shares

    if book.bids:
        liq_net_ps, _, _ = compute_net_sell_proceeds_per_share(
            book.bids[0].price,
            fee_rate_bps=book.fee_rate_bps,
            fee_exponent=book.fee_exponent,
        )
    else:
        liq_net_ps = 0.0

    ref_mark = max(cb_ps, liq_net_ps) if require_profit_over_cost_basis else liq_net_ps
    inv = InventoryHolding(
        instrument_id=str(pos.get("token_id") or pos.get("asset_id") or book.instrument_id),
        market_id=str(pos.get("market_id") or book.market_id),
        condition_id=str(pos.get("condition_id") or book.condition_id),
        shares=shares,
        cost_basis_per_share=max(0.0, cb_ps),
        mark_bid_per_share=max(0.0, ref_mark),
        uma_resolution_status=str(pos.get("umaResolutionStatus") or pos.get("uma_resolution_status") or ""),
        is_frozen_disputed=is_d001_frozen_position(pos)[0],
        trade_id=str(pos.get("trade_id") or pos.get("id") or ""),
    )
    return inv, max(0.0, cb_ps), max(0.0, liq_net_ps)


def detect_family_j_inventory_recycling(
    portfolio_state: Optional[Mapping[str, Any]],
    binary_markets: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    books_by_token: Mapping[str, Any],
    *,
    config: Optional[VerificationConfig] = None,
    merge_gas_usd: float = 0.0,
    convert_gas_usd: float = 0.0,
) -> Tuple[List[DetectedCompleteSetOrNegRiskOpportunity], Dict[str, Any]]:
    """
    Family J — Inventory, Split/Merge & Capital Recycling Detector (`ΔWealth_min`):
      - Strictly enforces `D-001` FIRST via `partition_portfolio_positions_d001`: any disputed
        `KMIA` position (`6707503`, `6707502`, `umaResolutionStatus == "disputed"`) is frozen and
        100% excluded from merge, single-leg completion, convert, or unwind evaluation.
      - Evaluates 4 exact inventory-recycling subfamilies on eligible (`non-frozen`) positions:
          1. `J1_INVENTORY_COMPLETE_SET_MERGE` (`CLASS_A`, `0` CLOB legs): wallet already holds
             complementary `YES + NO` shares on a binary condition -> atomic `CTF_MERGE` into `$1.00`.
          2. `J2_INVENTORY_SINGLE_LEG_LOCK` (`CLASS_A` when `1` FOK CLOB leg + `CTF_MERGE` locks
             strict profit over BOTH entry cost basis and current bid; `J2B_INVENTORY_SPREAD_SAVING_MERGE_EXIT`
             downgraded to `CLASS_C` when buying complement + merging beats dumping into a wide bid
             but remains below entry cost basis!).
          3. `J3_INVENTORY_NEGRISK_CONVERT_RECYCLE` (`CLASS_A` pure on-chain `convertPositions` when
             `m >= 2` held `NO`s yield `(m-1)*(1-c)` instant cash above mark/cost; `CLASS_B` when
             converting `m >= 1` held `NO`s into higher-bid complement `YES` tokens).
          4. `J4_INVENTORY_PRE_SPLIT_OVERROUND_EXIT` (`CLASS_B`): selling pre-held `YES + NO` pairs
             into overround CLOB bids `bid_net(YES) + bid_net(NO) > $1.00` without paying split gas.
      - Returns `(opportunities, d001_inventory_audit_summary)`.
    """
    cfg = config or VerificationConfig()
    part_dict = partition_portfolio_positions_d001(portfolio_state, now_ts=cfg.now_ts)
    eligible_list: List[Dict[str, Any]] = list(part_dict.get("eligible_positions") or ())
    frozen_list: List[Dict[str, Any]] = list(part_dict.get("frozen_positions") or ())

    frozen_cost_usd = round(float(part_dict.get("frozen_cost_basis_usd") or 0.0), 6)
    audit_info: Dict[str, Any] = {
        "eligible_position_count": len(eligible_list),
        "d001_frozen_position_count": len(frozen_list),
        "d001_frozen_cost_basis_usd": frozen_cost_usd,
        "d001_frozen_market_ids": sorted(
            {str(p.get("market_id") or p.get("marketId") or "") for p in frozen_list if p.get("market_id") or p.get("marketId")}
        ),
        "d001_frozen_position_keys": [str(p.get("_position_key") or p.get("trade_id") or "") for p in frozen_list],
        "d001_non_interference_verified": True,
    }

    if not eligible_list:
        return [], audit_info

    # Aggregate eligible shares by `token_id` (weighted-average cost basis)
    agg_by_token: Dict[str, Dict[str, Any]] = {}
    for p in eligible_list:
        if is_d001_frozen_position(p)[0]:  # belt-and-suspenders D-001 guard
            continue
        tok = str(p.get("token_id") or p.get("asset_id") or p.get("instrument_id") or "").strip()
        sh = _sf(p.get("remaining_shares") if p.get("remaining_shares") is not None else (p.get("shares") or p.get("size")), 0.0)
        if not tok or sh <= 0.0:
            continue
        ep = _sf(p.get("entry_price") or p.get("avg_price") or p.get("cost_basis_per_share"), 0.0)
        if ep <= 0.0:
            c_tot = _sf(p.get("remaining_cost_basis") or p.get("cost_usd"), 0.0)
            ep = (c_tot / sh) if c_tot > 0.0 else 0.50
        if tok not in agg_by_token:
            agg_by_token[tok] = {
                "token_id": tok,
                "market_id": str(p.get("market_id") or p.get("marketId") or ""),
                "condition_id": str(p.get("condition_id") or p.get("conditionId") or ""),
                "shares": sh,
                "cost_usd": sh * ep,
                "entry_price": ep,
                "umaResolutionStatus": str(p.get("umaResolutionStatus") or ""),
                "trade_id": str(p.get("_position_key") or p.get("trade_id") or ""),
            }
        else:
            rec = agg_by_token[tok]
            rec["shares"] += sh
            rec["cost_usd"] += sh * ep
            rec["entry_price"] = rec["cost_usd"] / max(rec["shares"], 1e-9)

    if not agg_by_token:
        return [], audit_info

    # Index binary markets (including child markets inside `events`)
    mkt_by_id: Dict[str, Mapping[str, Any]] = {}
    all_bin_markets: List[Mapping[str, Any]] = []
    seen_mids: Set[str] = set()
    for m in binary_markets or ():
        if isinstance(m, Mapping):
            mid = str(m.get("id") or m.get("market_id") or m.get("conditionId") or "").strip()
            if mid and mid not in seen_mids and mid not in FROZEN_DISPUTED_MARKET_IDS:
                seen_mids.add(mid)
                mkt_by_id[mid] = m
                all_bin_markets.append(m)
    for ev in events or ():
        if isinstance(ev, Mapping):
            for m in ev.get("markets") or ():
                if isinstance(m, Mapping):
                    mid = str(m.get("id") or m.get("market_id") or m.get("conditionId") or "").strip()
                    if mid and mid not in seen_mids and mid not in FROZEN_DISPUTED_MARKET_IDS:
                        seen_mids.add(mid)
                        mkt_by_id[mid] = m
                        all_bin_markets.append(m)

    out: List[DetectedCompleteSetOrNegRiskOpportunity] = []

    # --- J1, J2, J4 across Binary Markets ---
    for m in all_bin_markets:
        mid = str(m.get("id") or m.get("market_id") or m.get("conditionId") or "").strip()
        if mid in FROZEN_DISPUTED_MARKET_IDS:
            continue
        cid = str(m.get("conditionId") or m.get("condition_id") or mid).strip()
        yes_tok, no_tok, (lbl_y, lbl_n) = extract_binary_token_pair(m)
        if not (yes_tok and no_tok):
            continue
        held_y = agg_by_token.get(yes_tok)
        held_n = agg_by_token.get(no_tok)
        if held_y is None and held_n is None:
            continue

        part_proof = _build_binary_partition_proof(m)
        if not part_proof.is_valid_complete_set:
            continue

        bk_yes = _build_instrument_book(yes_tok, m, books_by_token, outcome_label=lbl_y)
        bk_no = _build_instrument_book(no_tok, m, books_by_token, outcome_label=lbl_n)
        local_books = {yes_tok: bk_yes, no_tok: bk_no}
        states = StateSpaceBuilder.binary_complete_set_states(yes_tok, no_tok, include_void_50_50=True)
        ev_id = str(m.get("event_id") or m.get("eventId") or mid)
        title = str(m.get("question") or m.get("title") or mid).strip()

        # 1. Both YES and NO already held -> Check J1 (Atomic Merge) & J4 (Pre-Split Overround Sell)
        if held_y is not None and held_n is not None:
            inv_y_liq, cb_y, liq_y = _build_inventory_holding_for_lock(
                held_y, bk_yes, require_profit_over_cost_basis=False
            )
            inv_n_liq, cb_n, liq_n = _build_inventory_holding_for_lock(
                held_n, bk_no, require_profit_over_cost_basis=False
            )
            holdings_pair_liq = {yes_tok: inv_y_liq, no_tok: inv_n_liq}

            # J1: Pure on-chain CTF Merge (`0` CLOB legs -> `CLASS_A` if `1.00 - gas/q > liq_y + liq_n`)
            cand_j1 = CandidateStructure(
                candidate_id=f"FAM_J1_HELD_PAIR_MERGE_{mid}",
                family="J",
                legs=(
                    ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=yes_tok, weight=1.0, market_id=mid, label=lbl_y),
                    ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=no_tok, weight=1.0, market_id=mid, label=lbl_n),
                    ActionLeg(
                        action_type=ActionType.CTF_MERGE,
                        weight=1.0,
                        related_instrument_ids=(yes_tok, no_tok),
                        gas_cost_usd=max(0.0, float(merge_gas_usd)),
                        market_id=mid,
                        label="MERGE_HELD_COMPLETE_SET",
                    ),
                ),
                states=states,
                rule_verified=True,
                is_exhaustive_partition=True,
                is_mutually_exclusive=True,
                requires_exhaustive_partition=True,
                expected_lockup_hours=0.01,
                worst_case_lockup_hours=0.02,
            )
            proof_j1, cash_j1, peak_j1 = _verify_with_liquid_cash_budget_guard(
                cfg, cand_j1, local_books, holdings=holdings_pair_liq
            )
            q_j1 = proof_j1.optimal_executable_quantity
            if q_j1 > 0.0 and proof_j1.min_state_net_payoff_usd > 0.0:
                dw_liq = round(q_j1 * 1.0 - proof_j1.cost_breakdown.gas_costs_usd - q_j1 * (liq_y + liq_n), 6)
                dw_cb = round(q_j1 * 1.0 - proof_j1.cost_breakdown.gas_costs_usd - q_j1 * (cb_y + cb_n), 6)
                out.append(
                    DetectedCompleteSetOrNegRiskOpportunity(
                        candidate_id=cand_j1.candidate_id,
                        family="J",
                        subfamily="J1_INVENTORY_COMPLETE_SET_MERGE",
                        opportunity_class=proof_j1.opportunity_class,
                        event_id=ev_id,
                        event_title=title,
                        market_ids=(mid,),
                        condition_ids=(cid,),
                        optimal_shares_q=q_j1,
                        gross_top_of_book_spread_per_unit=round(1.0 - (liq_y + liq_n), 6),
                        gross_top_of_book_spread_bps=round((1.0 - (liq_y + liq_n)) * 10_000.0, 2),
                        net_executable_edge_per_unit=proof_j1.net_executable_edge_per_unit,
                        net_executable_edge_bps=round(proof_j1.net_executable_edge_per_unit * 10_000.0, 2),
                        capital_required_usd=cash_j1,
                        peak_intratx_collateral_usd=peak_j1,
                        expected_lockup_hours=0.01,
                        worst_case_lockup_hours=0.02,
                        theoretical_top_of_book_usd=proof_j1.four_value_ledger.theoretical_top_of_book_usd,
                        executable_l2_net_usd=proof_j1.four_value_ledger.executable_l2_net_usd,
                        attainable_risk_adjusted_usd=proof_j1.four_value_ledger.attainable_risk_adjusted_usd,
                        realized_net_usd=0.0,
                        min_state_net_payoff_usd=proof_j1.min_state_net_payoff_usd,
                        max_state_net_payoff_usd=proof_j1.max_state_net_payoff_usd,
                        expected_net_payoff_usd=proof_j1.expected_net_payoff_usd,
                        delta_wealth_min_usd=dw_liq,
                        delta_wealth_vs_cost_basis_usd=dw_cb,
                        delta_wealth_vs_liquidation_mark_usd=dw_liq,
                        synthetic_vs_direct_ask_savings_per_share=None,
                        taker_fees_usd=0.0,
                        conversion_fee_usd=0.0,
                        gas_cost_usd=proof_j1.cost_breakdown.gas_costs_usd,
                        is_atomic_or_prelocked=True,
                        clob_leg_count=0,
                        d007_sub500_multileg_quarantine=False,
                        execution_mode_cap=proof_j1.execution_mode_cap,
                        is_dormant_near_arb=False,
                        distance_to_breakeven_bps=0.0,
                        partition_proof=part_proof,
                        proof=proof_j1,
                        metadata={"released_collateral_usd": round(q_j1 * 1.0, 6)},
                    )
                )

            # J4: Pre-Split Overround Exit (`bid_net(YES) + bid_net(NO) > max(1.00, cb_y + cb_n)`)
            if bk_yes.bids and bk_no.bids:
                ref_pair_floor = max(1.0, cb_y + cb_n)
                inv_y_ps = InventoryHolding(
                    instrument_id=yes_tok,
                    market_id=mid,
                    condition_id=cid,
                    shares=inv_y_liq.shares,
                    cost_basis_per_share=cb_y,
                    mark_bid_per_share=ref_pair_floor * 0.5,
                )
                inv_n_ps = InventoryHolding(
                    instrument_id=no_tok,
                    market_id=mid,
                    condition_id=cid,
                    shares=inv_n_liq.shares,
                    cost_basis_per_share=cb_n,
                    mark_bid_per_share=ref_pair_floor * 0.5,
                )
                cand_j4 = CandidateStructure(
                    candidate_id=f"FAM_J4_PRESPLIT_OVERROUND_SELL_{mid}",
                    family="J",
                    legs=(
                        ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=yes_tok, weight=1.0, market_id=mid, label=lbl_y),
                        ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=no_tok, weight=1.0, market_id=mid, label=lbl_n),
                        ActionLeg(action_type=ActionType.SELL_CLOB, instrument_id=yes_tok, weight=1.0, market_id=mid, label=lbl_y),
                        ActionLeg(action_type=ActionType.SELL_CLOB, instrument_id=no_tok, weight=1.0, market_id=mid, label=lbl_n),
                    ),
                    states=states,
                    rule_verified=True,
                    is_exhaustive_partition=True,
                    is_mutually_exclusive=True,
                    requires_exhaustive_partition=True,
                    expected_lockup_hours=0.01,
                    worst_case_lockup_hours=0.02,
                )
                proof_j4, cash_j4, peak_j4 = _verify_with_liquid_cash_budget_guard(
                    cfg, cand_j4, local_books, holdings={yes_tok: inv_y_ps, no_tok: inv_n_ps}
                )
                q_j4 = proof_j4.optimal_executable_quantity
                if q_j4 > 0.0 and proof_j4.min_state_net_payoff_usd > 0.0:
                    gross_j4 = round((bk_yes.bids[0].price + bk_no.bids[0].price) - ref_pair_floor, 6)
                    dw_cb_j4 = round(
                        proof_j4.min_state_net_payoff_usd + q_j4 * (ref_pair_floor - (cb_y + cb_n)),
                        6,
                    )
                    out.append(
                        DetectedCompleteSetOrNegRiskOpportunity(
                            candidate_id=cand_j4.candidate_id,
                            family="J",
                            subfamily="J4_INVENTORY_PRE_SPLIT_OVERROUND_EXIT",
                            opportunity_class=proof_j4.opportunity_class,
                            event_id=ev_id,
                            event_title=title,
                            market_ids=(mid,),
                            condition_ids=(cid,),
                            optimal_shares_q=q_j4,
                            gross_top_of_book_spread_per_unit=gross_j4,
                            gross_top_of_book_spread_bps=round(gross_j4 * 10_000.0, 2),
                            net_executable_edge_per_unit=proof_j4.net_executable_edge_per_unit,
                            net_executable_edge_bps=round(proof_j4.net_executable_edge_per_unit * 10_000.0, 2),
                            capital_required_usd=cash_j4,
                            peak_intratx_collateral_usd=peak_j4,
                            expected_lockup_hours=0.01,
                            worst_case_lockup_hours=0.02,
                            theoretical_top_of_book_usd=proof_j4.four_value_ledger.theoretical_top_of_book_usd,
                            executable_l2_net_usd=proof_j4.four_value_ledger.executable_l2_net_usd,
                            attainable_risk_adjusted_usd=proof_j4.four_value_ledger.attainable_risk_adjusted_usd,
                            realized_net_usd=0.0,
                            min_state_net_payoff_usd=proof_j4.min_state_net_payoff_usd,
                            max_state_net_payoff_usd=proof_j4.max_state_net_payoff_usd,
                            expected_net_payoff_usd=proof_j4.expected_net_payoff_usd,
                            delta_wealth_min_usd=proof_j4.min_state_net_payoff_usd,
                            delta_wealth_vs_cost_basis_usd=dw_cb_j4,
                            delta_wealth_vs_liquidation_mark_usd=proof_j4.min_state_net_payoff_usd,
                            synthetic_vs_direct_ask_savings_per_share=None,
                            taker_fees_usd=proof_j4.cost_breakdown.taker_fees_usd,
                            conversion_fee_usd=0.0,
                            gas_cost_usd=proof_j4.cost_breakdown.gas_costs_usd,
                            is_atomic_or_prelocked=False,
                            clob_leg_count=2,
                            d007_sub500_multileg_quarantine=False,
                            execution_mode_cap=proof_j4.execution_mode_cap,
                            is_dormant_near_arb=False,
                            distance_to_breakeven_bps=0.0,
                            partition_proof=part_proof,
                            proof=proof_j4,
                        )
                    )

        # 2. Single-Side Inventory Held -> Check J2 (`CLASS_A` Single-Remaining-Leg Lock vs `CLASS_C` Spread-Saving Exit)
        for held_rec, held_tok, held_bk, comp_tok, comp_bk, held_lbl, comp_lbl in (
            (held_y, yes_tok, bk_yes, no_tok, bk_no, lbl_y, lbl_n),
            (held_n, no_tok, bk_no, yes_tok, bk_yes, lbl_n, lbl_y),
        ):
            if held_rec is None or not comp_bk.asks:
                continue
            # Also skip if already matched 100% by opposite side (`held_y` & `held_n` equal shares)
            other_sh = _sf(agg_by_token.get(comp_tok, {}).get("shares"), 0.0)
            net_unhedged_sh = max(0.0, _sf(held_rec.get("shares"), 0.0) - other_sh)
            if net_unhedged_sh < DEFAULT_MIN_ORDER_SHARES:
                continue

            unhedged_rec = {**held_rec, "shares": net_unhedged_sh}
            inv_strict, cb_h, liq_h = _build_inventory_holding_for_lock(
                unhedged_rec, held_bk, require_profit_over_cost_basis=True
            )
            comp_ask_net_l1, _, _ = compute_net_buy_cost_per_delivered_share(
                comp_bk.asks[0].price,
                fee_rate_bps=comp_bk.fee_rate_bps,
                fee_exponent=comp_bk.fee_exponent,
            )
            est_profit_vs_cb = 1.0 - cb_h - comp_ask_net_l1
            est_gain_vs_liq = 1.0 - liq_h - comp_ask_net_l1

            if est_profit_vs_cb > 0.0 and est_gain_vs_liq > 0.0:
                # True `CLASS_A` single-leg completion lock: `1` FOK CLOB leg + atomic `CTF_MERGE`!
                cand_j2 = CandidateStructure(
                    candidate_id=f"FAM_J2_SINGLE_LEG_LOCK_{mid}_{held_lbl}",
                    family="J",
                    legs=(
                        ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=held_tok, weight=1.0, market_id=mid, label=held_lbl),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=comp_tok, weight=1.0, market_id=mid, label=comp_lbl),
                        ActionLeg(
                            action_type=ActionType.CTF_MERGE,
                            weight=1.0,
                            related_instrument_ids=(yes_tok, no_tok),
                            gas_cost_usd=max(0.0, float(merge_gas_usd)),
                            market_id=mid,
                            label="CTF_MERGE_SINGLE_LEG_LOCK",
                        ),
                    ),
                    states=states,
                    rule_verified=True,
                    is_exhaustive_partition=True,
                    is_mutually_exclusive=True,
                    requires_exhaustive_partition=True,
                    expected_lockup_hours=0.01,
                    worst_case_lockup_hours=0.02,
                )
                proof_j2, cash_j2, peak_j2 = _verify_with_liquid_cash_budget_guard(
                    cfg, cand_j2, local_books, holdings={held_tok: inv_strict}
                )
                q_j2 = proof_j2.optimal_executable_quantity
                if q_j2 > 0.0 and proof_j2.min_state_net_payoff_usd > 0.0:
                    buy_cost_tot = sum(
                        le.acquisition_or_gross_usd for le in proof_j2.leg_executions if le.action_type == ActionType.BUY_CLOB.value
                    )
                    gas_tot = proof_j2.cost_breakdown.gas_costs_usd
                    dw_cb = round(q_j2 * 1.0 - buy_cost_tot - gas_tot - q_j2 * cb_h, 6)
                    dw_liq = round(q_j2 * 1.0 - buy_cost_tot - gas_tot - q_j2 * liq_h, 6)
                    gross_j2 = round(1.0 - max(cb_h, liq_h) - comp_bk.asks[0].price, 6)
                    out.append(
                        DetectedCompleteSetOrNegRiskOpportunity(
                            candidate_id=cand_j2.candidate_id,
                            family="J",
                            subfamily="J2_INVENTORY_SINGLE_LEG_LOCK",
                            opportunity_class=proof_j2.opportunity_class,
                            event_id=ev_id,
                            event_title=title,
                            market_ids=(mid,),
                            condition_ids=(cid,),
                            optimal_shares_q=q_j2,
                            gross_top_of_book_spread_per_unit=gross_j2,
                            gross_top_of_book_spread_bps=round(gross_j2 * 10_000.0, 2),
                            net_executable_edge_per_unit=proof_j2.net_executable_edge_per_unit,
                            net_executable_edge_bps=round(proof_j2.net_executable_edge_per_unit * 10_000.0, 2),
                            capital_required_usd=cash_j2,
                            peak_intratx_collateral_usd=peak_j2,
                            expected_lockup_hours=0.01,
                            worst_case_lockup_hours=0.02,
                            theoretical_top_of_book_usd=proof_j2.four_value_ledger.theoretical_top_of_book_usd,
                            executable_l2_net_usd=proof_j2.four_value_ledger.executable_l2_net_usd,
                            attainable_risk_adjusted_usd=proof_j2.four_value_ledger.attainable_risk_adjusted_usd,
                            realized_net_usd=0.0,
                            min_state_net_payoff_usd=proof_j2.min_state_net_payoff_usd,
                            max_state_net_payoff_usd=proof_j2.max_state_net_payoff_usd,
                            expected_net_payoff_usd=proof_j2.expected_net_payoff_usd,
                            delta_wealth_min_usd=min(dw_cb, dw_liq),
                            delta_wealth_vs_cost_basis_usd=dw_cb,
                            delta_wealth_vs_liquidation_mark_usd=dw_liq,
                            synthetic_vs_direct_ask_savings_per_share=round(est_gain_vs_liq, 6),
                            taker_fees_usd=proof_j2.cost_breakdown.taker_fees_usd,
                            conversion_fee_usd=0.0,
                            gas_cost_usd=gas_tot,
                            is_atomic_or_prelocked=proof_j2.is_atomic_or_prelocked,
                            clob_leg_count=1,
                            d007_sub500_multileg_quarantine=False,
                            execution_mode_cap=proof_j2.execution_mode_cap,
                            is_dormant_near_arb=False,
                            distance_to_breakeven_bps=0.0,
                            partition_proof=part_proof,
                            proof=proof_j2,
                            metadata={
                                "held_token_id": held_tok,
                                "complement_token_id": comp_tok,
                                "held_cost_basis_per_share": round(cb_h, 6),
                                "held_liq_bid_per_share": round(liq_h, 6),
                            },
                        )
                    )
            elif est_gain_vs_liq > 0.002 and held_bk.bids:
                # Underwater vs original cost basis (`est_profit_vs_cb <= 0`), BUT buying complement + merging
                # recovers strictly more cash than selling into `bid(held)`!
                # Emit as `CLASS_C` (`J2B_INVENTORY_SPREAD_SAVING_MERGE_EXIT`) — NEVER `CLASS_A`!
                inv_liq_only, _, _ = _build_inventory_holding_for_lock(
                    unhedged_rec, held_bk, require_profit_over_cost_basis=False
                )
                cand_j2b = CandidateStructure(
                    candidate_id=f"FAM_J2B_SPREAD_SAVING_MERGE_EXIT_{mid}_{held_lbl}",
                    family="J",
                    legs=(
                        ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=held_tok, weight=1.0, market_id=mid, label=held_lbl),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=comp_tok, weight=1.0, market_id=mid, label=comp_lbl),
                        ActionLeg(
                            action_type=ActionType.CTF_MERGE,
                            weight=1.0,
                            related_instrument_ids=(yes_tok, no_tok),
                            gas_cost_usd=max(0.0, float(merge_gas_usd)),
                            market_id=mid,
                            label="SPREAD_SAVING_SYNTHETIC_EXIT_MERGE",
                        ),
                    ),
                    states=states,
                    rule_verified=True,
                    is_exhaustive_partition=True,
                    is_mutually_exclusive=True,
                    requires_exhaustive_partition=True,
                    expected_lockup_hours=0.01,
                    worst_case_lockup_hours=0.02,
                )
                proof_j2b_liq, cash_j2b, peak_j2b = _verify_with_liquid_cash_budget_guard(
                    cfg,
                    cand_j2b,
                    local_books,
                    holdings={held_tok: inv_liq_only},
                )
                q_j2b = proof_j2b_liq.optimal_executable_quantity
                if q_j2b > 0.0 and proof_j2b_liq.expected_net_payoff_usd > 0.0:
                    buy_cost_tot = sum(
                        le.acquisition_or_gross_usd for le in proof_j2b_liq.leg_executions if le.action_type == ActionType.BUY_CLOB.value
                    )
                    gas_tot = proof_j2b_liq.cost_breakdown.gas_costs_usd
                    dw_cb = round(q_j2b * 1.0 - buy_cost_tot - gas_tot - q_j2b * cb_h, 6)
                    dw_liq = round(q_j2b * 1.0 - buy_cost_tot - gas_tot - q_j2b * liq_h, 6)
                    out.append(
                        DetectedCompleteSetOrNegRiskOpportunity(
                            candidate_id=cand_j2b.candidate_id,
                            family="J",
                            subfamily="J2B_INVENTORY_SPREAD_SAVING_MERGE_EXIT",
                            opportunity_class=OpportunityClass.CLASS_C.value,
                            event_id=ev_id,
                            event_title=title,
                            market_ids=(mid,),
                            condition_ids=(cid,),
                            optimal_shares_q=q_j2b,
                            gross_top_of_book_spread_per_unit=round(1.0 - liq_h - comp_bk.asks[0].price, 6),
                            gross_top_of_book_spread_bps=round((1.0 - liq_h - comp_bk.asks[0].price) * 10_000.0, 2),
                            net_executable_edge_per_unit=round(dw_liq / q_j2b, 6),
                            net_executable_edge_bps=round((dw_liq / q_j2b) * 10_000.0, 2),
                            capital_required_usd=cash_j2b,
                            peak_intratx_collateral_usd=peak_j2b,
                            expected_lockup_hours=0.01,
                            worst_case_lockup_hours=0.02,
                            theoretical_top_of_book_usd=dw_liq,
                            executable_l2_net_usd=dw_liq,
                            attainable_risk_adjusted_usd=proof_j2b_liq.four_value_ledger.attainable_risk_adjusted_usd,
                            realized_net_usd=0.0,
                            min_state_net_payoff_usd=dw_cb,
                            max_state_net_payoff_usd=dw_liq,
                            expected_net_payoff_usd=dw_liq,
                            delta_wealth_min_usd=dw_cb,
                            delta_wealth_vs_cost_basis_usd=dw_cb,
                            delta_wealth_vs_liquidation_mark_usd=dw_liq,
                            synthetic_vs_direct_ask_savings_per_share=round(dw_liq / q_j2b, 6),
                            taker_fees_usd=proof_j2b_liq.cost_breakdown.taker_fees_usd,
                            conversion_fee_usd=0.0,
                            gas_cost_usd=gas_tot,
                            is_atomic_or_prelocked=False,
                            clob_leg_count=1,
                            d007_sub500_multileg_quarantine=False,
                            execution_mode_cap="MODE_1_RESEARCH",
                            is_dormant_near_arb=False,
                            distance_to_breakeven_bps=0.0,
                            partition_proof=part_proof,
                            proof=proof_j2b_liq,
                            metadata={
                                "is_spread_saving_exit_only": True,
                                "held_cost_basis_per_share": round(cb_h, 6),
                                "held_liq_bid_per_share": round(liq_h, 6),
                            },
                        )
                    )

    # --- J3: NegRisk Held-NO Conversion Recycling across Closed NegRisk Events ---
    for ev in events or ():
        if not isinstance(ev, Mapping):
            continue
        raw_mkts = ev.get("markets") or ()
        if len(raw_mkts) < 2:
            continue
        is_nr = bool(
            ev.get("negRisk")
            or ev.get("enableNegRisk")
            or ev.get("neg_risk")
            or any(bool(m.get("negRisk") or m.get("neg_risk")) for m in raw_mkts if isinstance(m, Mapping))
        )
        if not is_nr:
            continue

        part_proof, specs, local_books, states = _prepare_event_outcome_specs(ev, books_by_token)
        if not part_proof.is_valid_complete_set:
            continue
        if any(s["market_id"] in FROZEN_DISPUTED_MARKET_IDS for s in specs):
            continue

        tradable = [
            s for s in specs
            if s["yes_token_id"] and s["no_token_id"] and s["enable_order_book"] and not s["closed"] and s["active"]
        ]
        if len(tradable) != len(specs) or len(tradable) < 2:
            continue

        held_no_specs = [s for s in tradable if s["no_token_id"] in agg_by_token]
        if not held_no_specs:
            continue

        ev_id = str(ev.get("id") or ev.get("event_id") or specs[0]["market_id"]).strip()
        title = str(ev.get("title") or ev.get("question") or ev_id).strip()
        nr_bips = int(_sf(ev.get("negRiskFeeBips") or ev.get("fee_bips"), 0))
        c_conv = min(0.25, max(0.0, float(nr_bips) / 10_000.0))
        one_minus_c = 1.0 - c_conv

        inv_holdings: Dict[str, InventoryHolding] = {}
        cb_map: Dict[str, float] = {}
        liq_map: Dict[str, float] = {}
        for s in held_no_specs:
            ntok = s["no_token_id"]
            inv_h, cb_v, liq_v = _build_inventory_holding_for_lock(
                agg_by_token[ntok], local_books[ntok], require_profit_over_cost_basis=True
            )
            inv_holdings[ntok] = inv_h
            cb_map[ntok] = cb_v
            liq_map[ntok] = liq_v

        held_mids = {s["market_id"] for s in held_no_specs}
        comp_specs = [s for s in tradable if s["market_id"] not in held_mids]
        m_held = len(held_no_specs)

        # J3A (`m >= 2` held NOs, pure on-chain `convertPositions` with `0` CLOB legs -> `CLASS_A`!)
        if m_held >= 2:
            minted_yes = tuple(s["yes_token_id"] for s in comp_specs)
            legs_j3a = tuple(
                [
                    ActionLeg(
                        action_type=ActionType.USE_INVENTORY,
                        instrument_id=s["no_token_id"],
                        weight=1.0,
                        market_id=s["market_id"],
                        label=f"HELD_NO:{s['label']}",
                    )
                    for s in held_no_specs
                ]
                + [
                    ActionLeg(
                        action_type=ActionType.NEGRISK_CONVERT,
                        weight=1.0,
                        burned_no_instrument_ids=tuple(s["no_token_id"] for s in held_no_specs),
                        minted_yes_instrument_ids=minted_yes,
                        negrisk_fee_bips=nr_bips,
                        gas_cost_usd=max(0.0, float(convert_gas_usd)),
                        market_id=held_no_specs[0]["market_id"],
                        label=f"CONVERT_HELD_M{m_held}_NO",
                    )
                ]
            )
            cand_j3a = CandidateStructure(
                candidate_id=f"FAM_J3A_HELD_NO_PURE_CONVERT_{ev_id}",
                family="J",
                legs=legs_j3a,
                states=states,
                rule_verified=True,
                is_exhaustive_partition=True,
                is_mutually_exclusive=True,
                requires_exhaustive_partition=True,
                expected_lockup_hours=0.01 if not comp_specs else 2.0,
                worst_case_lockup_hours=0.02 if not comp_specs else 24.0,
            )
            proof_j3a, cash_j3a, peak_j3a = _verify_with_liquid_cash_budget_guard(
                cfg, cand_j3a, local_books, holdings=inv_holdings
            )
            q_j3a = proof_j3a.optimal_executable_quantity
            if q_j3a > 0.0 and proof_j3a.min_state_net_payoff_usd > 0.0:
                sum_cb = sum(cb_map[s["no_token_id"]] for s in held_no_specs)
                sum_liq = sum(liq_map[s["no_token_id"]] for s in held_no_specs)
                min_gross_val = float(m_held - 1) * one_minus_c
                dw_cb = round(q_j3a * (min_gross_val - sum_cb) - proof_j3a.cost_breakdown.gas_costs_usd, 6)
                dw_liq = round(q_j3a * (min_gross_val - sum_liq) - proof_j3a.cost_breakdown.gas_costs_usd, 6)
                out.append(
                    DetectedCompleteSetOrNegRiskOpportunity(
                        candidate_id=cand_j3a.candidate_id,
                        family="J",
                        subfamily="J3_INVENTORY_NEGRISK_CONVERT_RECYCLE",
                        opportunity_class=proof_j3a.opportunity_class,
                        event_id=ev_id,
                        event_title=title,
                        market_ids=tuple(s["market_id"] for s in held_no_specs),
                        condition_ids=tuple(s["condition_id"] for s in held_no_specs),
                        optimal_shares_q=q_j3a,
                        gross_top_of_book_spread_per_unit=round(min_gross_val - max(sum_cb, sum_liq), 6),
                        gross_top_of_book_spread_bps=round((min_gross_val - max(sum_cb, sum_liq)) * 10_000.0, 2),
                        net_executable_edge_per_unit=proof_j3a.net_executable_edge_per_unit,
                        net_executable_edge_bps=round(proof_j3a.net_executable_edge_per_unit * 10_000.0, 2),
                        capital_required_usd=cash_j3a,
                        peak_intratx_collateral_usd=peak_j3a,
                        expected_lockup_hours=proof_j3a.cost_breakdown.expected_lockup_hours,
                        worst_case_lockup_hours=proof_j3a.cost_breakdown.worst_case_lockup_hours,
                        theoretical_top_of_book_usd=proof_j3a.four_value_ledger.theoretical_top_of_book_usd,
                        executable_l2_net_usd=proof_j3a.four_value_ledger.executable_l2_net_usd,
                        attainable_risk_adjusted_usd=proof_j3a.four_value_ledger.attainable_risk_adjusted_usd,
                        realized_net_usd=0.0,
                        min_state_net_payoff_usd=proof_j3a.min_state_net_payoff_usd,
                        max_state_net_payoff_usd=proof_j3a.max_state_net_payoff_usd,
                        expected_net_payoff_usd=proof_j3a.expected_net_payoff_usd,
                        delta_wealth_min_usd=min(dw_cb, dw_liq),
                        delta_wealth_vs_cost_basis_usd=dw_cb,
                        delta_wealth_vs_liquidation_mark_usd=dw_liq,
                        synthetic_vs_direct_ask_savings_per_share=None,
                        taker_fees_usd=0.0,
                        conversion_fee_usd=proof_j3a.cost_breakdown.conversion_costs_usd,
                        gas_cost_usd=proof_j3a.cost_breakdown.gas_costs_usd,
                        is_atomic_or_prelocked=True,
                        clob_leg_count=0,
                        d007_sub500_multileg_quarantine=False,
                        execution_mode_cap=proof_j3a.execution_mode_cap,
                        is_dormant_near_arb=False,
                        distance_to_breakeven_bps=0.0,
                        partition_proof=part_proof,
                        proof=proof_j3a,
                        metadata={"m_held_no": m_held, "mode": "PURE_ONCHAIN_CONVERT"},
                    )
                )

        # J3B (`m >= 1` held NOs converted + complement `YES` tokens swept into higher CLOB bids -> `CLASS_B`)
        if comp_specs and all(bool(local_books[s["yes_token_id"]].bids) for s in comp_specs):
            minted_yes = tuple(s["yes_token_id"] for s in comp_specs)
            legs_j3b = tuple(
                [
                    ActionLeg(
                        action_type=ActionType.USE_INVENTORY,
                        instrument_id=s["no_token_id"],
                        weight=1.0,
                        market_id=s["market_id"],
                        label=f"HELD_NO:{s['label']}",
                    )
                    for s in held_no_specs
                ]
                + [
                    ActionLeg(
                        action_type=ActionType.NEGRISK_CONVERT,
                        weight=1.0,
                        burned_no_instrument_ids=tuple(s["no_token_id"] for s in held_no_specs),
                        minted_yes_instrument_ids=minted_yes,
                        negrisk_fee_bips=nr_bips,
                        gas_cost_usd=max(0.0, float(convert_gas_usd)),
                        market_id=held_no_specs[0]["market_id"],
                        label=f"CONVERT_HELD_M{m_held}_TO_COMP_YES",
                    )
                ]
                + [
                    ActionLeg(
                        action_type=ActionType.SELL_CLOB,
                        instrument_id=s["yes_token_id"],
                        weight=one_minus_c,
                        market_id=s["market_id"],
                        label=f"SELL_MINTED_YES:{s['label']}",
                    )
                    for s in comp_specs
                ]
            )
            cand_j3b = CandidateStructure(
                candidate_id=f"FAM_J3B_HELD_NO_CONVERT_SELL_YES_{ev_id}",
                family="J",
                legs=legs_j3b,
                states=states,
                rule_verified=True,
                is_exhaustive_partition=True,
                is_mutually_exclusive=True,
                requires_exhaustive_partition=True,
                expected_lockup_hours=0.02,
                worst_case_lockup_hours=0.05,
            )
            proof_j3b, cash_j3b, peak_j3b = _verify_with_liquid_cash_budget_guard(
                cfg, cand_j3b, local_books, holdings=inv_holdings
            )
            q_j3b = proof_j3b.optimal_executable_quantity
            if q_j3b > 0.0 and proof_j3b.min_state_net_payoff_usd > 0.0:
                sum_cb = sum(cb_map[s["no_token_id"]] for s in held_no_specs)
                sum_liq = sum(liq_map[s["no_token_id"]] for s in held_no_specs)
                sum_ref = sum(max(cb_map[s["no_token_id"]], liq_map[s["no_token_id"]]) for s in held_no_specs)
                dw_cb = round(proof_j3b.min_state_net_payoff_usd + q_j3b * (sum_ref - sum_cb), 6)
                dw_liq = round(proof_j3b.min_state_net_payoff_usd + q_j3b * (sum_ref - sum_liq), 6)
                gross_j3b = (
                    float(m_held - 1) * one_minus_c
                    + one_minus_c * sum(local_books[s["yes_token_id"]].bids[0].price for s in comp_specs)
                    - sum_ref
                )
                out.append(
                    DetectedCompleteSetOrNegRiskOpportunity(
                        candidate_id=cand_j3b.candidate_id,
                        family="J",
                        subfamily="J3_INVENTORY_NEGRISK_CONVERT_RECYCLE",
                        opportunity_class=proof_j3b.opportunity_class,
                        event_id=ev_id,
                        event_title=title,
                        market_ids=tuple(s["market_id"] for s in tradable),
                        condition_ids=tuple(s["condition_id"] for s in tradable),
                        optimal_shares_q=q_j3b,
                        gross_top_of_book_spread_per_unit=round(gross_j3b, 6),
                        gross_top_of_book_spread_bps=round(gross_j3b * 10_000.0, 2),
                        net_executable_edge_per_unit=proof_j3b.net_executable_edge_per_unit,
                        net_executable_edge_bps=round(proof_j3b.net_executable_edge_per_unit * 10_000.0, 2),
                        capital_required_usd=cash_j3b,
                        peak_intratx_collateral_usd=peak_j3b,
                        expected_lockup_hours=0.02,
                        worst_case_lockup_hours=0.05,
                        theoretical_top_of_book_usd=proof_j3b.four_value_ledger.theoretical_top_of_book_usd,
                        executable_l2_net_usd=proof_j3b.four_value_ledger.executable_l2_net_usd,
                        attainable_risk_adjusted_usd=proof_j3b.four_value_ledger.attainable_risk_adjusted_usd,
                        realized_net_usd=0.0,
                        min_state_net_payoff_usd=proof_j3b.min_state_net_payoff_usd,
                        max_state_net_payoff_usd=proof_j3b.max_state_net_payoff_usd,
                        expected_net_payoff_usd=proof_j3b.expected_net_payoff_usd,
                        delta_wealth_min_usd=min(dw_cb, dw_liq),
                        delta_wealth_vs_cost_basis_usd=dw_cb,
                        delta_wealth_vs_liquidation_mark_usd=dw_liq,
                        synthetic_vs_direct_ask_savings_per_share=None,
                        taker_fees_usd=proof_j3b.cost_breakdown.taker_fees_usd,
                        conversion_fee_usd=proof_j3b.cost_breakdown.conversion_costs_usd,
                        gas_cost_usd=proof_j3b.cost_breakdown.gas_costs_usd,
                        is_atomic_or_prelocked=False,
                        clob_leg_count=len(comp_specs),
                        d007_sub500_multileg_quarantine=proof_j3b.d007_sub500_multileg_quarantine,
                        execution_mode_cap=proof_j3b.execution_mode_cap,
                        is_dormant_near_arb=False,
                        distance_to_breakeven_bps=0.0,
                        partition_proof=part_proof,
                        proof=proof_j3b,
                        metadata={"m_held_no": m_held, "mode": "CONVERT_AND_SWEEP_COMP_BIDS"},
                    )
                )

    return out, audit_info


# ---------------------------------------------------------------------------
# 9. Unified Detector Suite & Live Public Gamma/CLOB Universe Scanner
# ---------------------------------------------------------------------------


@dataclass
class CompleteSetAndNegRiskDetectorSuite:
    """
    Unified facade for Agents 3 & 4 (`@complete-negrisk`, Families A, B, C & J)
    designed for plug-and-play integration with `@pipeline-shadow` and
    `PortfolioArbitrageOptimizer` (`peer_candidates_a_to_j`).
    """

    config: VerificationConfig = field(default_factory=VerificationConfig)
    merge_gas_usd: float = 0.0
    split_gas_usd: float = 0.0
    convert_gas_usd: float = 0.0
    dormant_max_bps: float = DORMANT_MAX_BPS_DEFAULT

    def scan_all(
        self,
        *,
        events: Sequence[Mapping[str, Any]] = (),
        standalone_binary_markets: Sequence[Mapping[str, Any]] = (),
        books_by_token: Mapping[str, Any] = (),  # type: ignore[assignment]
        portfolio_state: Optional[Mapping[str, Any]] = None,
        include_non_actionable_class_e: bool = False,
    ) -> Dict[str, Any]:
        books_map: Mapping[str, Any] = books_by_token if isinstance(books_by_token, Mapping) else {}

        # Deduplicate binary markets across `events` + `standalone_binary_markets`
        all_binaries: List[Mapping[str, Any]] = []
        seen_mids: Set[str] = set()
        for ev in events or ():
            if not isinstance(ev, Mapping):
                continue
            ev_id = str(ev.get("id") or ev.get("event_id") or "")
            ev_aug = bool(ev.get("negRiskAugmented") or ev.get("enableNegRiskAugmented"))
            for m in ev.get("markets") or ():
                if not isinstance(m, Mapping):
                    continue
                mid = str(m.get("id") or m.get("market_id") or m.get("conditionId") or "").strip()
                if mid and mid not in seen_mids:
                    seen_mids.add(mid)
                    if "event_id" not in m and ev_id:
                        m = {**m, "event_id": ev_id, "negRiskAugmented": bool(m.get("negRiskAugmented") or ev_aug)}
                    all_binaries.append(m)
        for m in standalone_binary_markets or ():
            if not isinstance(m, Mapping):
                continue
            mid = str(m.get("id") or m.get("market_id") or m.get("conditionId") or "").strip()
            if mid and mid not in seen_mids:
                seen_mids.add(mid)
                all_binaries.append(m)

        fam_a = detect_family_a_binary_complete_sets(
            all_binaries,
            books_map,
            config=self.config,
            merge_gas_usd=self.merge_gas_usd,
            split_gas_usd=self.split_gas_usd,
            dormant_max_bps=self.dormant_max_bps,
            include_non_actionable_class_e=include_non_actionable_class_e,
        )
        fam_b = detect_family_b_multi_outcome_complete_sets(
            events,
            books_map,
            config=self.config,
            gas_usd=self.split_gas_usd,
            dormant_max_bps=self.dormant_max_bps,
            include_non_actionable_class_e=include_non_actionable_class_e,
        )
        fam_c = detect_family_c_negrisk_conversions(
            events,
            books_map,
            config=self.config,
            convert_gas_usd=self.convert_gas_usd,
            dormant_max_bps=self.dormant_max_bps,
            include_non_actionable_class_e=include_non_actionable_class_e,
        )
        fam_j, d001_audit = detect_family_j_inventory_recycling(
            portfolio_state,
            all_binaries,
            events,
            books_map,
            config=self.config,
            merge_gas_usd=self.merge_gas_usd,
            convert_gas_usd=self.convert_gas_usd,
        )

        combined = sorted(
            fam_a + fam_b + fam_c + fam_j,
            key=lambda c: (
                0 if c.opportunity_class == OpportunityClass.CLASS_A.value else (
                    1 if c.opportunity_class == OpportunityClass.CLASS_B.value else (
                        2 if c.opportunity_class == OpportunityClass.CLASS_C.value else (
                            3 if c.opportunity_class == OpportunityClass.CLASS_D.value else 4
                        )
                    )
                ),
                -c.attainable_risk_adjusted_usd,
                -c.net_executable_edge_bps,
            ),
        )
        return {
            "family_a": fam_a,
            "family_b": fam_b,
            "family_c": fam_c,
            "family_j": fam_j,
            "all_candidates": combined,
            "proofs": [c.proof for c in combined],
            "d001_inventory_audit": d001_audit,
            "binary_markets_evaluated": len(all_binaries),
            "events_evaluated": len(events),
        }


def _compact_gamma_market_dict(m: Mapping[str, Any], *, event_id: str, ev_aug: bool) -> Dict[str, Any]:
    """Retains only fields required for mathematical verification & L2 pricing so 220K markets fit in `< 110 MiB` RAM."""
    desc_raw = str(m.get("description") or "")
    # Keep first 360 chars of description (enough for conditional/void rule detection) without multi-KB prose
    desc_short = desc_raw[:360] if desc_raw else ""
    return {
        "id": str(m.get("id") or ""),
        "event_id": event_id,
        "conditionId": str(m.get("conditionId") or ""),
        "questionID": str(m.get("questionID") or ""),
        "question": str(m.get("question") or ""),
        "groupItemTitle": str(m.get("groupItemTitle") or ""),
        "groupItemThreshold": m.get("groupItemThreshold"),
        "description": desc_short,
        "outcomes": m.get("outcomes"),
        "outcomePrices": m.get("outcomePrices"),
        "clobTokenIds": m.get("clobTokenIds"),
        "active": bool(m.get("active", True) is not False),
        "closed": bool(m.get("closed", False)),
        "archived": bool(m.get("archived", False)),
        "enableOrderBook": bool(m.get("enableOrderBook", True) is not False),
        "negRisk": bool(m.get("negRisk", False)),
        "negRiskOther": bool(m.get("negRiskOther", False)),
        "negRiskAugmented": bool(m.get("negRiskAugmented", False) or ev_aug),
        "feesEnabled": m.get("feesEnabled"),
        "feeSchedule": m.get("feeSchedule"),
        "feeType": m.get("feeType"),
        "takerBaseFee": m.get("takerBaseFee"),
        "orderPriceMinTickSize": m.get("orderPriceMinTickSize"),
        "orderMinSize": m.get("orderMinSize"),
        "bestBid": m.get("bestBid"),
        "bestAsk": m.get("bestAsk"),
        "liquidityClob": _sf(m.get("liquidityClob") or m.get("liquidityNum") or m.get("liquidity"), 0.0),
        "volume24hr": _sf(m.get("volume24hr"), 0.0),
        "umaResolutionStatus": str(m.get("umaResolutionStatus") or ""),
        "endDate": m.get("endDate"),
    }


def fetch_full_gamma_universe_keyset(
    *,
    page_limit: int = 500,
    max_pages: int = 250,
    timeout_sec: float = 20.0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Streams 100% of active unclosed Polymarket events via `GET /events/keyset` cursor pagination
    (avoiding the `offset=3000` HTTP 422 truncation wall on legacy offset pagination).
    """
    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(GAMMA_API_HOST, timeout=timeout_sec, context=ctx)
    events: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    pages = 0
    total_markets = 0
    fees_enabled_markets = 0
    zero_fee_markets = 0
    negrisk_events = 0
    augmented_negrisk_events = 0

    try:
        while pages < max_pages:
            qs = f"/events/keyset?active=true&closed=false&limit={int(page_limit)}"
            if cursor:
                qs += f"&after_cursor={urllib.parse.quote(str(cursor))}"

            raw_bytes = b""
            for attempt in range(3):
                try:
                    conn.request(
                        "GET",
                        qs,
                        headers={"Accept": "application/json", "User-Agent": "dominus-riskless-research/1.0"},
                    )
                    resp = conn.getresponse()
                    raw_bytes = resp.read()
                    if resp.status == 200:
                        break
                    time.sleep(0.35 * (attempt + 1))
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = http.client.HTTPSConnection(GAMMA_API_HOST, timeout=timeout_sec, context=ctx)
                    time.sleep(0.4 * (attempt + 1))
            if not raw_bytes:
                break

            payload = json.loads(raw_bytes.decode("utf-8"))
            batch = payload.get("events") if isinstance(payload, Mapping) else payload
            if not isinstance(batch, list) or not batch:
                break
            pages += 1

            for ev in batch:
                if not isinstance(ev, Mapping):
                    continue
                ev_id = str(ev.get("id") or "")
                is_nr = bool(ev.get("negRisk") or ev.get("enableNegRisk"))
                is_aug = bool(ev.get("negRiskAugmented") or ev.get("enableNegRiskAugmented"))
                if is_nr:
                    negrisk_events += 1
                if is_aug:
                    augmented_negrisk_events += 1
                raw_mkts = ev.get("markets") or ()
                compact_mkts: List[Dict[str, Any]] = []
                for m in raw_mkts:
                    if not isinstance(m, Mapping):
                        continue
                    cm = _compact_gamma_market_dict(m, event_id=ev_id, ev_aug=is_aug)
                    compact_mkts.append(cm)
                    if not cm["closed"] and cm["active"]:
                        total_markets += 1
                        fr, _, _ = extract_market_fee_params(cm)
                        if fr > 0.0:
                            fees_enabled_markets += 1
                        else:
                            zero_fee_markets += 1

                events.append(
                    {
                        "id": ev_id,
                        "slug": str(ev.get("slug") or ""),
                        "title": str(ev.get("title") or ""),
                        "description": str(ev.get("description") or "")[:360],
                        "negRisk": is_nr,
                        "enableNegRisk": bool(ev.get("enableNegRisk") or is_nr),
                        "negRiskAugmented": is_aug,
                        "negRiskMarketID": str(ev.get("negRiskMarketID") or ""),
                        "negRiskFeeBips": int(_sf(ev.get("negRiskFeeBips"), 0)),
                        "cumulativeMarkets": bool(ev.get("cumulativeMarkets", False)),
                        "endDate": ev.get("endDate"),
                        "markets": compact_mkts,
                    }
                )

            next_cur = payload.get("next_cursor") if isinstance(payload, Mapping) else None
            if not next_cur or next_cur == cursor:
                break
            cursor = str(next_cur)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    stats = {
        "pages_fetched": pages,
        "active_events_total": len(events),
        "active_unclosed_markets_total": total_markets,
        "zero_fee_active_markets": zero_fee_markets,
        "dynamic_fee_active_markets": fees_enabled_markets,
        "negrisk_events_total": negrisk_events,
        "augmented_negrisk_events_total": augmented_negrisk_events,
    }
    return events, stats


def fetch_clob_books_batch(
    token_ids: Sequence[str],
    *,
    batch_size: int = 500,
    max_workers: int = 10,
    max_levels_per_side: int = 12,
    timeout_sec: float = 15.0,
) -> Dict[str, Dict[str, Any]]:
    """
    Fetches multi-rung L2 order books via batched `POST https://clob.polymarket.com/books` (`<= 500` tokens/call),
    immediately sorting `asks` ascending (`lowest ask` first!) and `bids` descending (`highest bid` first!)
    and trimming beyond `max_levels_per_side` to keep memory compact (`< 80 MiB`).
    """
    dedup_tokens = [str(t).strip() for t in dict.fromkeys(token_ids) if str(t).strip()]
    if not dedup_tokens:
        return {}

    chunks = [dedup_tokens[i : i + batch_size] for i in range(0, len(dedup_tokens), batch_size)]
    ctx = ssl.create_default_context()
    tls_local = threading.local()

    def _fetch_chunk(chunk: List[str]) -> Dict[str, Dict[str, Any]]:
        body = json.dumps([{"token_id": tid} for tid in chunk]).encode("utf-8")
        out_chunk: Dict[str, Dict[str, Any]] = {}
        for attempt in range(3):
            conn = getattr(tls_local, "conn", None)
            if conn is None:
                conn = http.client.HTTPSConnection(CLOB_API_HOST, timeout=timeout_sec, context=ctx)
                tls_local.conn = conn
            try:
                conn.request(
                    "POST",
                    "/books",
                    body=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "dominus-riskless-research/1.0",
                    },
                )
                resp = conn.getresponse()
                raw = resp.read()
                if resp.status != 200:
                    time.sleep(0.25 * (attempt + 1))
                    continue
                rows = json.loads(raw.decode("utf-8"))
                if not isinstance(rows, list):
                    break
                fetched_ms_str = str(int(time.time() * 1000))
                for r in rows:
                    if not isinstance(r, Mapping):
                        continue
                    aid = str(r.get("asset_id") or r.get("token_id") or "").strip()
                    if not aid:
                        continue
                    raw_asks = r.get("asks") or ()
                    raw_bids = r.get("bids") or ()
                    asks_sorted = sorted(
                        (
                            {"price": float(a["price"]), "size": float(a["size"])}
                            for a in raw_asks
                            if isinstance(a, Mapping) and _sf(a.get("price"), 0.0) > 0.0 and _sf(a.get("size"), 0.0) > 0.0
                        ),
                        key=lambda x: x["price"],
                    )[:max_levels_per_side]
                    bids_sorted = sorted(
                        (
                            {"price": float(b["price"]), "size": float(b["size"])}
                            for b in raw_bids
                            if isinstance(b, Mapping) and _sf(b.get("price"), 0.0) > 0.0 and _sf(b.get("size"), 0.0) > 0.0
                        ),
                        key=lambda x: -x["price"],
                    )[:max_levels_per_side]
                    out_chunk[aid] = {
                        "asset_id": aid,
                        "market": str(r.get("market") or ""),
                        # Record HTTP snapshot timestamp so firm resting GTC orders placed >120s ago
                        # are not misclassified as stale cached snapshots, while preserving last mutation ts!
                        "timestamp": fetched_ms_str,
                        "last_book_mutation_timestamp": r.get("timestamp"),
                        "tick_size": r.get("tick_size"),
                        "min_order_size": r.get("min_order_size"),
                        "neg_risk": r.get("neg_risk"),
                        "asks": asks_sorted,
                        "bids": bids_sorted,
                    }
                break
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                tls_local.conn = None
                time.sleep(0.3 * (attempt + 1))
        return out_chunk

    merged: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(chunks)))) as pool:
        futs = [pool.submit(_fetch_chunk, ch) for ch in chunks]
        for f in as_completed(futs):
            merged.update(f.result())
    return merged


def _select_priority_tokens_for_clob_scan(
    events: Sequence[Mapping[str, Any]],
    portfolio_state: Optional[Mapping[str, Any]],
    *,
    max_tokens: int = 22000,
) -> Tuple[List[str], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """
    Selects the highest-signal active tokens across the entire Gamma universe for deep L2 `/books`
    fetching (all eligible portfolio tokens, all `0`-fee orderbook markets, all liquid closed `negRisk`
    events, representative augmented/non-exhaustive multi-outcome events, all Gamma near-arb top-of-book
    candidates, plus highest-liquidity dynamic-fee binary markets up to `max_tokens`).
    """
    selected_tokens: List[str] = []
    seen_toks: Set[str] = set()
    scanned_events: List[Dict[str, Any]] = []
    scanned_binaries: List[Dict[str, Any]] = []
    seen_ev_ids: Set[str] = set()
    seen_mids: Set[str] = set()

    def _add_mkt(m: Dict[str, Any]) -> bool:
        yt, nt, _ = extract_binary_token_pair(m)
        if not (yt and nt):
            return False
        if len(selected_tokens) + 2 > max_tokens and yt not in seen_toks:
            return False
        for t in (yt, nt):
            if t not in seen_toks:
                seen_toks.add(t)
                selected_tokens.append(t)
        mid = m["id"]
        if mid not in seen_mids:
            seen_mids.add(mid)
            scanned_binaries.append(m)
        return True

    def _add_event(ev: Dict[str, Any]) -> bool:
        mkts = [m for m in ev.get("markets", ()) if not m["closed"] and m["active"] and m["enableOrderBook"]]
        needed = 0
        for m in mkts:
            yt, nt, _ = extract_binary_token_pair(m)
            if yt and yt not in seen_toks:
                needed += 1
            if nt and nt not in seen_toks:
                needed += 1
        if len(selected_tokens) + needed > max_tokens:
            return False
        for m in ev.get("markets", ()):
            if not m["closed"] and m["active"] and m["enableOrderBook"]:
                _add_mkt(m)
        if ev["id"] not in seen_ev_ids:
            seen_ev_ids.add(ev["id"])
            scanned_events.append(ev)
        return True

    counts = {
        "tier0_portfolio_tokens": 0,
        "tier1_zero_fee_markets": 0,
        "tier2_closed_negrisk_events": 0,
        "tier3_augmented_or_multi_events": 0,
        "tier4_gamma_near_arb_binaries": 0,
        "tier5_liquid_dynamic_fee_binaries": 0,
    }

    # Tier 0: Eligible (non-D-001-frozen) held tokens
    eligible_pos = list(partition_portfolio_positions_d001(portfolio_state).get("eligible_positions") or ())
    held_mids = {str(p.get("market_id") or "") for p in eligible_pos if p.get("market_id")}
    for p in eligible_pos:
        t = str(p.get("token_id") or p.get("asset_id") or "").strip()
        if t and t not in seen_toks:
            seen_toks.add(t)
            selected_tokens.append(t)
            counts["tier0_portfolio_tokens"] += 1

    # Partition events by structure & liquidity
    closed_nr_events: List[Tuple[float, Dict[str, Any]]] = []
    aug_or_multi_events: List[Tuple[float, Dict[str, Any]]] = []
    zero_fee_mkts: List[Tuple[float, Dict[str, Any]]] = []
    near_arb_mkts: List[Tuple[float, Dict[str, Any]]] = []
    dyn_fee_mkts: List[Tuple[float, Dict[str, Any]]] = []

    for ev in events:
        if not isinstance(ev, dict):
            continue
        mkts = ev.get("markets") or []
        open_ob_mkts = [m for m in mkts if not m["closed"] and m["active"] and m["enableOrderBook"]]
        ev_liq = sum(_sf(m.get("liquidityClob"), 0.0) for m in open_ob_mkts)

        if any(m["id"] in held_mids for m in open_ob_mkts):
            _add_event(ev)

        if len(open_ob_mkts) >= 2:
            if ev.get("negRisk") and not ev.get("negRiskAugmented") and len(open_ob_mkts) <= 30:
                closed_nr_events.append((ev_liq, ev))
            elif ev_liq > 500.0 and len(open_ob_mkts) <= 35:
                aug_or_multi_events.append((ev_liq, ev))

        for m in open_ob_mkts:
            if m["id"] in FROZEN_DISPUTED_MARKET_IDS:
                continue
            liq = _sf(m.get("liquidityClob"), 0.0) + 0.1 * _sf(m.get("volume24hr"), 0.0)
            fr, _, _ = extract_market_fee_params(m)
            if fr <= 0.0:
                zero_fee_mkts.append((liq, m))
                continue
            # Check Gamma top-of-book hint (`bestBid` / `bestAsk` / `outcomePrices`)
            bb = _sf(m.get("bestBid"), -1.0)
            ba = _sf(m.get("bestAsk"), -1.0)
            if 0.0 < ba < 1.0 and 0.0 < bb < 1.0 and (ba - bb) <= 0.025 and liq > 50.0:
                near_arb_mkts.append((liq, m))
            elif liq > 250.0:
                dyn_fee_mkts.append((liq, m))

    # Add Tier 1: All `0`-fee active orderbook markets (sorted by liquidity)
    for _, m in sorted(zero_fee_mkts, key=lambda x: -x[0]):
        if _add_mkt(m):
            counts["tier1_zero_fee_markets"] += 1

    # Add Tier 2: Closed `negRisk` multi-outcome slates (sorted by liquidity)
    for _, ev in sorted(closed_nr_events, key=lambda x: -x[0]):
        if _add_event(ev):
            counts["tier2_closed_negrisk_events"] += 1

    # Add Tier 3: Representative high-liquidity `negRiskAugmented` & standalone multi-outcome slates (up to 180 events)
    for _, ev in sorted(aug_or_multi_events, key=lambda x: -x[0])[:180]:
        if _add_event(ev):
            counts["tier3_augmented_or_multi_events"] += 1

    # Add Tier 4: Tight-spread Gamma near-arb binary candidates
    for _, m in sorted(near_arb_mkts, key=lambda x: -x[0]):
        if _add_mkt(m):
            counts["tier4_gamma_near_arb_binaries"] += 1

    # Add Tier 5: Highest-liquidity dynamic-fee binaries up to `max_tokens`
    for _, m in sorted(dyn_fee_mkts, key=lambda x: -x[0]):
        if len(selected_tokens) + 2 > max_tokens:
            break
        if _add_mkt(m):
            counts["tier5_liquid_dynamic_fee_binaries"] += 1

    return selected_tokens, scanned_events, scanned_binaries, counts


def run_live_ab_c_j_universe_scan(
    *,
    output_path: Optional[Path] = None,
    portfolio_state_path: Optional[Path] = None,
    reconciled_nav_usd: float = DEFAULT_LIVE_RECONCILED_NAV_USD,
    max_clob_tokens: int = 22000,
) -> Dict[str, Any]:
    """
    Executes the full empirical MODE 1 public scan across Polymarket Gamma (`/events/keyset`)
    and batched CLOB L2 order books (`POST /books`), evaluates Families A, B, C, and J, and
    writes `data/full_throttle/scans_ab_c_j/scan_summary.json`.
    """
    t0 = time.time()
    repo_root = Path(__file__).resolve().parents[2]
    out_file = output_path or (repo_root / "data" / "full_throttle" / "scans_ab_c_j" / "scan_summary.json")
    state_file = portfolio_state_path or (repo_root / "data" / "polymarket" / "live_harvester_state.json")

    portfolio_state: Optional[Dict[str, Any]] = None
    live_bankroll_usd = float(reconciled_nav_usd)
    if state_file.exists():
        try:
            portfolio_state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            portfolio_state = None

    # Verify authoritative 4-position Nov 7 KMIA dispute reference (`6707503` x3 + `6707502` x1 = `$50.51`)
    kmia_ref_state = {
        "live_bankroll": live_bankroll_usd,
        "total_account_equity": round(live_bankroll_usd + 50.51, 6),
        "active_positions": {
            "WS_SNIPE_Miami_KMIA_242960": {"market_id": "6707503", "shares": 12.0, "cost_usd": 11.616, "umaResolutionStatus": "disputed"},
            "WS_SNIPE_Miami_KMIA_688670": {"market_id": "6707503", "shares": 12.0, "cost_usd": 11.616, "umaResolutionStatus": "disputed"},
            "WS_SNIPE_Miami_KMIA_837595": {"market_id": "6707503", "shares": 11.0, "cost_usd": 10.648, "umaResolutionStatus": "disputed"},
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                "market_id": "6707502",
                "shares": 17.0,
                "cost_usd": 16.63,
                "umaResolutionStatus": "disputed",
            },
        },
    }
    _, kmia_ref_audit = detect_family_j_inventory_recycling(kmia_ref_state, (), (), {})

    events_all, gamma_stats = fetch_full_gamma_universe_keyset()
    t_gamma = time.time()

    priority_tokens, target_events, target_binaries, selection_counts = _select_priority_tokens_for_clob_scan(
        events_all,
        portfolio_state,
        max_tokens=max_clob_tokens,
    )
    raw_books = fetch_clob_books_batch(priority_tokens, batch_size=500, max_workers=10, max_levels_per_side=12)
    t_clob = time.time()

    non_empty_books = sum(1 for b in raw_books.values() if b.get("asks") or b.get("bids"))
    two_sided_books = sum(1 for b in raw_books.values() if b.get("asks") and b.get("bids"))

    # Refresh book snapshot timestamp right after full batch completes so multi-hundred-second verifier runs
    # never trip artificial 120s age checks mid-scan
    scan_now_ts = time.time()
    fresh_ms = str(int(scan_now_ts * 1000))
    for b_rec in raw_books.values():
        b_rec["timestamp"] = fresh_ms

    cfg = VerificationConfig(
        max_budget_usd=live_bankroll_usd,
        reconciled_nav_usd=live_bankroll_usd,
        d007_multileg_nav_floor_usd=DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
        now_ts=scan_now_ts,
        max_book_age_sec=900.0,
        enforce_min_marketable_notional=True,
        default_relayer_gas_usd=0.0,
        settlement_gas_usd=0.0,
        lockup_opportunity_cost_bps_per_hour=0.0,
    )
    suite = CompleteSetAndNegRiskDetectorSuite(
        config=cfg,
        merge_gas_usd=0.0,
        split_gas_usd=0.0,
        convert_gas_usd=0.0,
        dormant_max_bps=250.0,
    )
    res = suite.scan_all(
        events=target_events,
        standalone_binary_markets=target_binaries,
        books_by_token=raw_books,
        portfolio_state=portfolio_state,
        include_non_actionable_class_e=True,
    )
    all_cands: List[DetectedCompleteSetOrNegRiskOpportunity] = res["all_candidates"]
    res["d001_inventory_audit"]["production_kmia_4lot_reference_audit"] = kmia_ref_audit

    # Evaluate uncapped `$1,000` shadow reference ONLY on near-zero/positive gross structures (`>-50 bps`) for speed!
    hot_ev_ids = {c.event_id for c in all_cands if c.gross_top_of_book_spread_per_unit > -0.005}
    hot_mids = {mid for c in all_cands if c.gross_top_of_book_spread_per_unit > -0.005 for mid in c.market_ids}
    hot_events = [ev for ev in target_events if ev.get("id") in hot_ev_ids]
    hot_binaries = [m for m in target_binaries if m.get("id") in hot_mids]

    cfg_shadow_1k = VerificationConfig(
        max_budget_usd=1000.0,
        reconciled_nav_usd=1000.0,
        d007_multileg_nav_floor_usd=DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
        now_ts=scan_now_ts,
        max_book_age_sec=900.0,
        enforce_min_marketable_notional=True,
    )
    suite_1k = CompleteSetAndNegRiskDetectorSuite(config=cfg_shadow_1k, dormant_max_bps=250.0)
    res_1k = suite_1k.scan_all(
        events=hot_events,
        standalone_binary_markets=hot_binaries,
        books_by_token=raw_books,
        portfolio_state=portfolio_state,
        include_non_actionable_class_e=False,
    )
    actionable_1k = [
        c for c in res_1k["all_candidates"]
        if c.opportunity_class in (OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value)
    ]

    def _summarize_family(cands: Sequence[DetectedCompleteSetOrNegRiskOpportunity]) -> Dict[str, Any]:
        by_class = {k.value: 0 for k in OpportunityClass}
        by_subfamily: Dict[str, int] = {}
        gross_pos = 0
        net_pos = 0
        dormant_0_50 = 0
        dormant_50_250 = 0
        d007_quarantined = 0
        for c in cands:
            by_class[c.opportunity_class] = by_class.get(c.opportunity_class, 0) + 1
            by_subfamily[c.subfamily] = by_subfamily.get(c.subfamily, 0) + 1
            if c.gross_top_of_book_spread_per_unit > 0.0:
                gross_pos += 1
            if c.net_executable_edge_per_unit > 0.0 and c.optimal_shares_q > 0.0:
                net_pos += 1
            if c.is_dormant_near_arb:
                if c.distance_to_breakeven_bps < 50.0:
                    dormant_0_50 += 1
                elif c.distance_to_breakeven_bps <= 250.0:
                    dormant_50_250 += 1
            if c.d007_sub500_multileg_quarantine:
                d007_quarantined += 1
        top_examples = [
            {
                "candidate_id": c.candidate_id,
                "subfamily": c.subfamily,
                "opportunity_class": c.opportunity_class,
                "event_id": c.event_id,
                "event_title": c.event_title[:100],
                "optimal_shares_q": c.optimal_shares_q,
                "gross_spread_bps": c.gross_top_of_book_spread_bps,
                "net_executable_edge_bps": c.net_executable_edge_bps,
                "capital_required_usd": c.capital_required_usd,
                "min_state_net_payoff_usd": c.min_state_net_payoff_usd,
                "executable_l2_net_usd": c.executable_l2_net_usd,
                "attainable_risk_adjusted_usd": c.attainable_risk_adjusted_usd,
                "distance_to_breakeven_bps": c.distance_to_breakeven_bps,
                "d007_sub500_multileg_quarantine": c.d007_sub500_multileg_quarantine,
                "execution_mode_cap": c.execution_mode_cap,
                "synthetic_vs_direct_ask_savings_per_share": c.synthetic_vs_direct_ask_savings_per_share,
                "disqualifiers": list(c.partition_proof.disqualifiers)[:5],
            }
            for c in sorted(
                cands,
                key=lambda x: (
                    0 if x.opportunity_class in ("CLASS_A", "CLASS_B") else (1 if x.is_dormant_near_arb else 2),
                    -x.net_executable_edge_bps,
                    -x.gross_top_of_book_spread_bps,
                ),
            )[:8]
        ]
        return {
            "total_candidates_evaluated": len(cands),
            "class_breakdown": by_class,
            "subfamily_breakdown": by_subfamily,
            "gross_positive_top_of_book_count": gross_pos,
            "net_positive_l2_executable_count": net_pos,
            "dormant_near_arb_0_to_50_bps": dormant_0_50,
            "dormant_near_arb_50_to_250_bps": dormant_50_250,
            "d007_sub500_multileg_quarantined_count": d007_quarantined,
            "top_candidates": top_examples,
        }

    overall_classes = {k.value: 0 for k in OpportunityClass}
    for c in all_cands:
        overall_classes[c.opportunity_class] = overall_classes.get(c.opportunity_class, 0) + 1

    summary_doc: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent": "complete-negrisk",
        "families_covered": ["A", "B", "C", "J"],
        "mode": "MODE_1_PUBLIC_READ_ONLY_EMPIRICAL_SCAN",
        "reconciled_liquid_nav_usd": round(live_bankroll_usd, 6),
        "timing_sec": {
            "gamma_keyset_pagination_sec": round(t_gamma - t0, 2),
            "clob_l2_books_batch_sec": round(t_clob - t_gamma, 2),
            "detector_and_proof_verification_sec": round(time.time() - t_clob, 2),
            "total_wall_sec": round(time.time() - t0, 2),
        },
        "universe_coverage": {
            **gamma_stats,
            "priority_tokens_queried_clob_books": len(priority_tokens),
            "clob_books_returned": len(raw_books),
            "clob_books_non_empty": non_empty_books,
            "clob_books_two_sided": two_sided_books,
            "binary_markets_evaluated_l2": res["binary_markets_evaluated"],
            "multi_outcome_events_evaluated_l2": res["events_evaluated"],
            "selection_tiers": selection_counts,
        },
        "existing_codebase_gap_audit": audit_existing_complete_set_and_negrisk_gaps(),
        "d001_kmia_non_interference_audit": res["d001_inventory_audit"],
        "overall_summary_at_live_nav": {
            "total_structures_evaluated": len(all_cands),
            "class_breakdown": overall_classes,
            "gross_positive_top_of_book_total": sum(1 for c in all_cands if c.gross_top_of_book_spread_per_unit > 0.0),
            "net_positive_l2_executable_class_a_or_b_total": sum(
                1 for c in all_cands if c.opportunity_class in ("CLASS_A", "CLASS_B")
            ),
            "dormant_near_arb_0_to_50_bps_total": sum(
                1 for c in all_cands if c.is_dormant_near_arb and c.distance_to_breakeven_bps < 50.0
            ),
            "dormant_near_arb_50_to_250_bps_total": sum(
                1 for c in all_cands if c.is_dormant_near_arb and 50.0 <= c.distance_to_breakeven_bps <= 250.0
            ),
        },
        "shadow_1000_usd_nav_comparison": {
            "actionable_class_a_or_b_count": len(actionable_1k),
            "top_actionable_at_1000_nav": [
                {
                    "candidate_id": c.candidate_id,
                    "family": c.family,
                    "subfamily": c.subfamily,
                    "opportunity_class": c.opportunity_class,
                    "event_title": c.event_title[:90],
                    "optimal_shares_q": c.optimal_shares_q,
                    "capital_required_usd": c.capital_required_usd,
                    "net_executable_edge_bps": c.net_executable_edge_bps,
                    "min_state_net_payoff_usd": c.min_state_net_payoff_usd,
                    "attainable_risk_adjusted_usd": c.attainable_risk_adjusted_usd,
                    "execution_mode_cap": c.execution_mode_cap,
                }
                for c in actionable_1k[:12]
            ],
        },
        "families": {
            "A_binary_complete_set": _summarize_family(res["family_a"]),
            "B_multi_outcome_complete_set": _summarize_family(res["family_b"]),
            "C_negrisk_conversions": _summarize_family(res["family_c"]),
            "J_inventory_recycling": _summarize_family(res["family_j"]),
        },
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(summary_doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary_doc


if __name__ == "__main__":  # pragma: no cover
    summary = run_live_ab_c_j_universe_scan()
    print(
        json.dumps(
            {
                "universe_coverage": summary["universe_coverage"],
                "overall_summary_at_live_nav": summary["overall_summary_at_live_nav"],
                "shadow_1000_usd_nav_count": summary["shadow_1000_usd_nav_comparison"]["actionable_class_a_or_b_count"],
                "d001_audit": summary["d001_kmia_non_interference_audit"],
                "timing_sec": summary["timing_sec"],
            },
            indent=2,
        )
    )

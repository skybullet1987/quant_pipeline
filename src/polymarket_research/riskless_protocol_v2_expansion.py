"""
Protocol V2, Microstructure Guards & Multi-Family Riskless Arbitrage Expansion
(`src/polymarket_research/riskless_protocol_v2_expansion.py`).

Unbundled zero-directional-risk expansion module implementing:
  1. Protocol V2 contract guards (`ExchangeV3`, `PositionManager`, `Router`, `AutoRedeemer`),
     augmented NegRisk synthetic `"Other"` partition guard, cached `NegRiskAdapter.getFeeBips`,
     dynamic `0.001` boundary tick quantizer (`p >= 0.96` or `p <= 0.04`, `min_shares >= 5`),
     and `REBOOT1` matching-engine `HTTP 425/503 post_only` guard.
  2. Family I (`NegRisk`):
     - `NR4_OPTIMAL_CHANNEL_CONVERT` (`m = 2..15` optimal `NO` basket + `S^c` `YES` bid sweep)
     - `NR5_LOTTERY_FREEROLL_CONVERT` (liquid `U \\subset S^c` pays for `S` + positive cash while
       retaining `R = S^c \\setminus U` as negative-cost `YES` lottery shares)
     - `NR6_CROSS_SLATE_SURJECTION_BOX` (`NO(A_1)+...+NO(A_k)+YES(B) < $k.00` and dual cover)
     - `execute_multi_leg_all_yes_bundle` (`3..12` equal-share FOK legs + unwind/merge)
  3. Family II (`RTDS` / Crypto / Equity):
     - `S2_RTDS_EXACT_TWAP_INTEGRATOR` (`crypto_prices_twap_sixty` + 1Hz Chainlink + `XAG`/`XAU`)
     - `D1_TELESCOPING_CANDLE_BRIDGE` (`15m/5m` & `1h/15m` terminal sub-candle step-dominance)
     - `B1_INTRADAY_ONETOUCH_NOON_BOX` (`10:15-12:00 ET` one-touch vs noon close)
     - `EQ1_PYTH_EQUITY_DOMINANCE_BOX` (`14:15-16:00 ET` Pyth regular-close strike dominance)
  4. Family III (`Weather METAR`):
     - `parse_routine_metar_temp_c` (strictly excluding unscheduled `SPECI`, parsing `RMK T[01]\\d{3}`)
     - `compute_running_metar_extrema` & `detect_w_prune1_metar_slate_arb` (`W_PRUNE1` + `W_SOLAR1`)
  5. Family IV-VI (`Sports`, `Mentions`, `Full-Universe C1 / CTF_OVERROUND`, `UMA_READY1`, `RewardShield`):
     - `DC1_DOUBLE_CHANCE_1X2_PARITY`, `LP_COMP1_SPORTS_TRIANGLES` (score-grid verified),
       `HALFTIME_FREEZE_OFFSET_BOX`, and US Overtime Inequality Guard
     - `MENTION1_CUMULATIVE_LADDER_BOX`
     - `scan_full_universe_c1_and_ctf_overround` & `execute_binary_ctf_overround_mint_sell`
     - `score_uma_ready1_liveness_priority` (`3-25m` liveness velocity priority)
     - `CompleteSetRewardShield` (`Q_min` `3x` two-sided/complete-set reward harvester)
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo


def _iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()

try:
    from src.polymarket_research.riskless_machine_gun_engine import attempt_onchain_split_position
except Exception:
    attempt_onchain_split_position = None  # type: ignore


def compute_exact_taker_fee_per_share(
    price: float,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
) -> float:
    """Exact Polymarket nonlinear taker fee per share: `r * (p * (1 - p)) ** exponent`."""
    r = max(0.0, float(fee_rate or 0.0))
    if r <= 0.0:
        return 0.0
    p = min(0.9999, max(0.0001, float(price)))
    exp = max(0.5, float(fee_exponent or 1.0))
    return r * ((p * (1.0 - p)) ** exp)

logger = logging.getLogger("RisklessProtocolV2Expansion")

# ---------------------------------------------------------------------------
# 1. Protocol V2 Contract Registry & Microstructure Guards
# ---------------------------------------------------------------------------

PROTOCOL_V2_ADDRESSES: Dict[str, str] = {
    "ExchangeV3": "0xe3333700cA9d93003F00f0F71f8515005F6c00Aa",
    "PositionManager": "0x006F54F7f9A22e0000CC2AB60031000000ae9fEF",
    "Router": "0x12121212006e4CD160D18e3f00711DA5c3372600",
    "AutoRedeemer": "0xa1200000d0002264C9a1698e001292D00E1b00af",
    "NegRiskAdapter": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
}
_V2_ADDR_LOWER_SET: Set[str] = {
    addr.lower()
    for k, addr in PROTOCOL_V2_ADDRESSES.items()
    if k in {"ExchangeV3", "PositionManager", "Router", "AutoRedeemer"}
}

RTDS_SUPPORTED_ASSETS: Tuple[str, ...] = (
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "BNB",
    "DOGE",
    "HYPE",
    "XAU",
    "XAG",
)

TWAP_60S_SUPPORTED_ASSETS: Tuple[str, ...] = (
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "BNB",
    "DOGE",
    "HYPE",
)

GATLING_REF_NAV_USD: float = 60.92

PYTH_EQUITY_SYMBOLS: Tuple[str, ...] = (
    "SPY",
    "QQQ",
    "NVDA",
    "TSLA",
    "AAPL",
    "MSFT",
    "META",
    "AMZN",
    "COIN",
    "MSTR",
    "GOOGL",
    "AMD",
)

_NEGRISK_FEE_BIPS_CACHE: Dict[str, Tuple[float, int]] = {}
_OTHER_OUTCOME_RE = re.compile(
    r"^\s*(?:other|any\s+other(?:\s+\w+)*|all\s+other(?:\s+\w+)*|field|none\s+of\s+the\s+above|someone\s+else)\s*$",
    re.IGNORECASE,
)
_PLACEHOLDER_OUTCOME_RE = re.compile(
    r"(?:\bplaceholder\b|\bunnamed\b|^person\s+[a-z0-9]+$|^player\s+[a-z0-9]+$|^option\s+\d+$|^tba$|^tbd$)",
    re.IGNORECASE,
)
_US_OVERTIME_LEAGUE_RE = re.compile(
    r"\b(?:nba|nfl|nhl|mlb|ncaa|ncaab|ncaaf|wnba|Stanley\s+Cup|Super\s+Bowl|World\s+Series)\b",
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


def is_protocol_v2_market(market_or_event: Mapping[str, Any]) -> bool:
    """Detect whether a Gamma/CLOB market or event runs on Polymarket Protocol V2 (`ExchangeV3` / `PositionManager`)."""
    if not isinstance(market_or_event, Mapping):
        return False
    if bool(market_or_event.get("isProtocolV2") or market_or_event.get("protocol_v2")):
        return True
    pv = str(market_or_event.get("protocolVersion") or market_or_event.get("protocol_version") or "").strip().lower()
    if pv in {"2", "v2", "2.0", "exchange_v3", "exchangev3"}:
        return True
    for k in (
        "exchangeAddress",
        "exchange_address",
        "verifyingContract",
        "positionManager",
        "position_manager",
        "routerAddress",
        "router_address",
        "autoRedeemer",
    ):
        raw = str(market_or_event.get(k) or "").strip().lower()
        if raw and raw in _V2_ADDR_LOWER_SET:
            return True
    return False


def verify_v2_negrisk_other_partition(
    outcomes: Sequence[Mapping[str, Any]],
    *,
    event_meta: Optional[Mapping[str, Any]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that a NegRisk multi-outcome slate forms an exhaustive, closed partition `{1..N}`.
    In Protocol V2 / augmented NegRisk, synthetic `"Other"` index `N` MUST be present and tradable
    whenever the universe is open/augmented, and unnamed placeholder slots invalidate conversion/all-YES baskets.
    """
    meta = event_meta if isinstance(event_meta, Mapping) else {}
    n = len(outcomes or [])
    if n < 3:
        return False, {"reason": "TOO_FEW_OUTCOMES", "total_partition_size": n}

    other_indices: List[int] = []
    unnamed_indices: List[int] = []
    disabled_indices: List[int] = []

    for idx, item in enumerate(outcomes):
        label = str(
            item.get("label")
            or item.get("groupItemTitle")
            or item.get("outcome")
            or item.get("question")
            or item.get("title")
            or ""
        ).strip()
        if bool(item.get("isPlaceholder") or item.get("is_placeholder") or item.get("placeholder")):
            unnamed_indices.append(idx)
            continue
        if _PLACEHOLDER_OUTCOME_RE.search(label):
            unnamed_indices.append(idx)
            continue
        if item.get("enableOrderBook") is False or item.get("active") is False or item.get("archived") is True:
            disabled_indices.append(idx)
            continue
        if bool(item.get("isOther") or item.get("is_other")) or _OTHER_OUTCOME_RE.match(label):
            other_indices.append(idx)

    if unnamed_indices:
        return False, {
            "reason": "UNNAMED_PLACEHOLDER_OUTCOME_PRESENT",
            "unnamed_indices": unnamed_indices,
            "total_partition_size": n,
        }
    if disabled_indices:
        return False, {
            "reason": "INACTIVE_OR_UNTRADABLE_PARTITION_SLOTS",
            "disabled_indices": disabled_indices,
            "total_partition_size": n,
        }

    is_aug = bool(
        meta.get("augmentedNegRisk")
        or meta.get("negRiskAugmented")
        or meta.get("enableNegRiskOther")
        or meta.get("negRiskOther")
        or meta.get("open_universe")
        or meta.get("hasOther")
    )
    if is_aug and not other_indices:
        return False, {
            "reason": "AUGMENTED_NEGRISK_MISSING_SYNTHETIC_OTHER_INDEX",
            "is_protocol_v2": is_protocol_v2_market(meta),
            "is_augmented_negrisk": True,
            "safe_for_all_yes_basket": False,
            "total_partition_size": n,
        }

    # Verify any present `"Other"` slot actually has token IDs whenever the outcome list carries token IDs
    any_has_tokens = any(
        str(
            x.get("yes_token_id")
            or x.get("token_id_yes")
            or x.get("yesTokenId")
            or x.get("no_token_id")
            or x.get("token_id_no")
            or x.get("noTokenId")
            or ""
        ).strip()
        for x in outcomes
    )
    for o_idx in other_indices:
        o_item = outcomes[o_idx]
        yes_tok = str(o_item.get("yes_token_id") or o_item.get("token_id_yes") or o_item.get("yesTokenId") or "").strip()
        no_tok = str(o_item.get("no_token_id") or o_item.get("token_id_no") or o_item.get("noTokenId") or "").strip()
        if any_has_tokens and not yes_tok and not no_tok:
            return False, {
                "reason": "SYNTHETIC_OTHER_MISSING_TOKEN_IDS",
                "other_index": o_idx,
                "total_partition_size": n,
            }

    return True, {
        "reason": "PARTITION_EXHAUSTIVE_OK",
        "other_indices": other_indices,
        "has_other": bool(other_indices),
        "is_augmented_negrisk": is_aug,
        "safe_for_all_yes_basket": bool(not is_aug or bool(other_indices)),
        "is_protocol_v2": is_protocol_v2_market(meta),
        "total_partition_size": n,
    }


def get_cached_negrisk_fee_bips(
    market_id: str,
    *,
    rpc_url: Optional[str] = None,
    rpc_caller: Optional[Callable[[str, str], Optional[str]]] = None,
    ttl_sec: float = 900.0,
    fallback_bips: int = 0,
    now_ts: Optional[float] = None,
) -> int:
    """
    Query & cache `NegRiskAdapter.getFeeBips(bytes32 _marketId)` on Polygon.
    Safely returns `fallback_bips` offline when `rpc_url` and `rpc_caller` are omitted.
    """
    mid = str(market_id or "").strip().lower()
    if not mid:
        return max(0, int(fallback_bips))
    now_f = float(time.time() if now_ts is None else now_ts)
    cached = _NEGRISK_FEE_BIPS_CACHE.get(mid)
    if cached is not None and (now_f - cached[0]) <= max(1.0, float(ttl_sec)):
        return cached[1]

    clean_hex = mid[2:] if mid.startswith("0x") else mid
    if len(clean_hex) != 64 or any(c not in "0123456789abcdef" for c in clean_hex):
        return max(0, int(fallback_bips))

    raw_hex_resp: Optional[str] = None
    try:
        if callable(rpc_caller):
            raw_hex_resp = rpc_caller(PROTOCOL_V2_ADDRESSES["NegRiskAdapter"], "0x" + clean_hex)
        elif rpc_url:
            from web3 import Web3  # lazy import so unit tests run zero-overhead

            selector = Web3.keccak(text="getFeeBips(bytes32)")[:4].hex()
            if not selector.startswith("0x"):
                selector = "0x" + selector
            call_data = selector + clean_hex
            payload = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [{"to": PROTOCOL_V2_ADDRESSES["NegRiskAdapter"], "data": call_data}, "latest"],
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                rpc_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                raw_hex_resp = body.get("result")
    except Exception as exc:
        logger.debug(f"[NegRiskFeeBips] fallback for {mid[:14]}: {exc}")

    bips = max(0, int(fallback_bips))
    if isinstance(raw_hex_resp, str) and raw_hex_resp.startswith("0x") and len(raw_hex_resp) > 2:
        try:
            parsed = int(raw_hex_resp, 16)
            if 0 <= parsed <= 5000:
                bips = parsed
        except ValueError:
            pass
    _NEGRISK_FEE_BIPS_CACHE[mid] = (now_f, bips)
    return bips


def quantize_dynamic_tick_price(
    price: float,
    side: str = "BUY",
    *,
    explicit_tick_size: Optional[float] = None,
    shares: Optional[float] = None,
    mode: str = "maker",
) -> Tuple[float, float, bool]:
    """
    Polymarket dynamic tick-size quantizer:
      - Automatically switches to `0.001` tick grid when `price >= 0.96` or `price <= 0.04`
        (unless an explicit finer tick like `0.0001` is provided).
      - Enforces minimum order size `shares >= 5.0` (`min_shares_ok`).
      - Uses exact `Decimal` arithmetic so `$0.991..$0.999` tail `NO` legs never suffer float drift.
    """
    p_clamped = min(0.999, max(0.001, float(price)))
    if explicit_tick_size is not None and float(explicit_tick_size) > 0.0:
        tick = float(explicit_tick_size)
        if (p_clamped >= 0.96 or p_clamped <= 0.04) and tick > 0.001:
            tick = 0.001
    else:
        tick = 0.001 if (p_clamped >= 0.96 or p_clamped <= 0.04) else 0.01

    d_p = Decimal(str(round(p_clamped, 6)))
    d_t = Decimal(str(tick))
    side_u = str(side or "BUY").upper()
    mode_l = str(mode or "maker").lower()

    if mode_l == "nearest":
        steps = (d_p / d_t).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    elif (side_u == "BUY" and mode_l == "maker") or (side_u == "SELL" and mode_l == "taker"):
        steps = (d_p / d_t).quantize(Decimal("1"), rounding=ROUND_FLOOR)
    else:
        steps = (d_p / d_t).quantize(Decimal("1"), rounding=ROUND_CEILING)

    q_dec = steps * d_t
    min_bound = d_t
    max_bound = Decimal("1") - d_t
    if q_dec < min_bound:
        q_dec = min_bound
    elif q_dec > max_bound:
        q_dec = max_bound

    min_shares_ok = True if shares is None else (float(shares) >= 5.0 - 1e-9)
    return float(q_dec), float(d_t), bool(min_shares_ok)


class RebootPostOnlyModeGuard:
    """
    `REBOOT1_POST_ONLY_AUCTION_HARVESTER`:
    Catches CLOB matching-engine restart / maintenance windows (`HTTP 425 Too Early`, `503`,
    or `"post_only"` / `"matching engine restarting"` error bodies), suppresses futile FOK/FAK
    taker spam during the window, and constructs `postOnly=True` wide complete-set maker quotes
    (`bid_yes + bid_no <= max_pair_bid_sum`) to capture queue priority 1 when continuous matching resumes.
    """

    def __init__(self, window_ttl_sec: float = 45.0) -> None:
        self.window_ttl_sec = max(5.0, float(window_ttl_sec))
        self._reboot_until_ts: float = 0.0
        self._detections: int = 0
        self._last_reason: str = ""

    def observe_response(
        self,
        status_code: Optional[int],
        body_or_err: Any = "",
        now_ts: Optional[float] = None,
    ) -> bool:
        now_f = float(time.time() if now_ts is None else now_ts)
        txt = str(body_or_err or "").lower()
        code = int(status_code) if status_code is not None else 0
        is_reboot = (
            code == 425
            or "post_only_mode" in txt
            or "post-only mode" in txt
            or "only post-only" in txt
            or "matching engine" in txt and ("restart" in txt or "reboot" in txt or "paused" in txt)
            or (code == 503 and ("post_only" in txt or "clob" in txt or "restart" in txt))
        )
        if is_reboot:
            self._reboot_until_ts = max(self._reboot_until_ts, now_f + self.window_ttl_sec)
            self._detections += 1
            self._last_reason = f"HTTP_{code}:{txt[:80]}"
            return True
        return False

    def in_post_only_window(self, now_ts: Optional[float] = None) -> bool:
        now_f = float(time.time() if now_ts is None else now_ts)
        return now_f < self._reboot_until_ts

    def should_suppress_taker(self, now_ts: Optional[float] = None) -> bool:
        return self.in_post_only_window(now_ts=now_ts)

    def build_reboot_post_only_quotes(
        self,
        yes_token_id: str,
        no_token_id: str,
        fair_yes: float,
        *,
        max_pair_bid_sum: float = 0.984,
        shares: float = 6.0,
    ) -> Optional[Dict[str, Any]]:
        if not yes_token_id or not no_token_id or float(shares) < 5.0:
            return None
        fy = min(0.94, max(0.06, float(fair_yes)))
        half_edge = max(0.008, (1.0 - float(max_pair_bid_sum)) * 0.5)
        q_yes, t_y, ok_y = quantize_dynamic_tick_price(fy - half_edge, "BUY", shares=shares, mode="maker")
        q_no, t_n, ok_n = quantize_dynamic_tick_price((1.0 - fy) - half_edge, "BUY", shares=shares, mode="maker")
        if not (ok_y and ok_n) or (q_yes + q_no) > float(max_pair_bid_sum) + 1e-9:
            return None
        return {
            "sleeve": "REBOOT1_POST_ONLY_AUCTION_HARVESTER",
            "post_only": True,
            "shares": round(float(shares), 2),
            "yes_token_id": str(yes_token_id),
            "no_token_id": str(no_token_id),
            "yes_bid_px": q_yes,
            "no_bid_px": q_no,
            "yes_tick": t_y,
            "no_tick": t_n,
            "pair_bid_sum": round(q_yes + q_no, 4),
            "locked_complete_set_edge_per_share": round(1.0 - (q_yes + q_no), 4),
        }


# ---------------------------------------------------------------------------
# 2. Family I: NegRisk Optimal-Channel Convert (`NR4`), Lottery Freeroll (`NR5`) & Surjection (`NR6`)
# ---------------------------------------------------------------------------


def detect_nr4_nr5_optimal_tail_convert(
    event_outcomes: Sequence[Mapping[str, Any]],
    *,
    event_id: str = "",
    neg_risk_market_id: str = "",
    event_meta: Optional[Mapping[str, Any]] = None,
    fee_bips: Optional[int] = None,
    rpc_url: Optional[str] = None,
    min_net_edge_usd: float = 0.004,
    min_freeroll_cash_usd: float = 0.002,
    min_shares: float = 5.0,
    max_m: int = 15,
    gas_usd_total: float = 0.01,
) -> List[Dict[str, Any]]:
    """
    Optimal-Channel NegRisk Conversion (`NR4`) & Negative-Cost Lottery Freeroll (`NR5`):
      - Validates closed/augmented partition completeness (`verify_v2_negrisk_other_partition`).
      - Deducts exact `NegRiskAdapter.getFeeBips(_marketId)` conversion fee `c = fee_bips / 10000`:
        converting `m = |S| >= 2` `NO` shares yields `(m - 1)*(1 - c)` immediate USDC.e cash plus
        `(1 - c)` `YES_j` shares for every complement outcome `j in S^c`.
      - Finds optimal `m in [2, min(N, max_m)]` maximizing net conversion cash + complement `YES` bid sweep (`NR4`).
      - Also checks whether selling ONLY liquid subset `U \\subsetneq S^c` (`|R| = |S^c \\setminus U| >= 1`)
        already produces strictly positive instant net cash `>= min_freeroll_cash_usd`, yielding `NR5`
        negative-cost `YES` lottery shares on `R` with zero downside in every state of the world.
    """
    ok_part, part_info = verify_v2_negrisk_other_partition(event_outcomes, event_meta=event_meta)
    if not ok_part:
        return []

    n = len(event_outcomes)
    eff_bips = (
        int(fee_bips)
        if fee_bips is not None
        else get_cached_negrisk_fee_bips(neg_risk_market_id, rpc_url=rpc_url, fallback_bips=0)
    )
    c_conv = min(0.25, max(0.0, float(eff_bips) / 10000.0))
    one_minus_c = 1.0 - c_conv

    parsed: List[Dict[str, Any]] = []
    for idx, item in enumerate(event_outcomes):
        no_ask_raw = _sf(item.get("no_ask") or item.get("ask_no"), 0.0)
        no_ask_sz = _sf(item.get("no_ask_size") or item.get("ask_no_size"), 0.0)
        yes_bid_raw = _sf(item.get("yes_bid") or item.get("bid_yes"), 0.0)
        yes_bid_sz = _sf(item.get("yes_bid_size") or item.get("bid_yes_size"), 0.0)
        f_rate = _sf(item.get("fee_rate"), 0.0)
        f_exp = _sf(item.get("fee_exponent"), 1.0)

        no_cost = 9.99
        no_q = 0.0
        if 0.001 <= no_ask_raw <= 0.999 and no_ask_sz >= min_shares:
            no_q, _, _ = quantize_dynamic_tick_price(no_ask_raw, "BUY", shares=min_shares, mode="taker")
            no_cost = no_q + compute_exact_taker_fee_per_share(no_q, f_rate, f_exp)

        yes_net_bid = 0.0
        yes_q = 0.0
        if 0.001 <= yes_bid_raw <= 0.999 and yes_bid_sz * one_minus_c >= min_shares * 0.95:
            yes_q, _, _ = quantize_dynamic_tick_price(yes_bid_raw, "SELL", shares=min_shares, mode="taker")
            yes_net_bid = max(0.0, yes_q - compute_exact_taker_fee_per_share(yes_q, f_rate, f_exp))

        # Marginal advantage of placing outcome `idx` into NO-buy set `S` vs leaving in `S^c`
        marginal_s_adv = one_minus_c * (1.0 - yes_net_bid) - no_cost
        q_idx_p = int(item.get("question_index") if item.get("question_index") is not None else item.get("index", idx))
        parsed.append(
            {
                "index": q_idx_p,
                "label": str(item.get("label") or item.get("groupItemTitle") or item.get("outcome") or f"idx_{q_idx_p}"),
                "condition_id": str(item.get("condition_id") or item.get("conditionId") or ""),
                "yes_token_id": str(item.get("yes_token_id") or item.get("token_id_yes") or ""),
                "no_token_id": str(item.get("no_token_id") or item.get("token_id_no") or ""),
                "no_ask_px": no_q,
                "no_cost_net": no_cost,
                "no_ask_size": no_ask_sz,
                "yes_bid_px": yes_q,
                "yes_net_bid": yes_net_bid,
                "yes_bid_size": yes_bid_sz,
                "marginal_s_adv": marginal_s_adv,
            }
        )

    ranked = sorted(parsed, key=lambda r: r["marginal_s_adv"], reverse=True)
    max_subset = min(n, max(2, int(max_m)))
    gas_per_sh = float(gas_usd_total) / max(float(min_shares), 5.0)

    best_nr4: Optional[Dict[str, Any]] = None
    best_nr5: Optional[Dict[str, Any]] = None

    for m in range(2, max_subset + 1):
        s_set = ranked[:m]
        sc_set = ranked[m:]
        if any(x["no_cost_net"] > 1.5 or not x["no_token_id"] for x in s_set):
            break

        cost_s = sum(x["no_cost_net"] for x in s_set)
        conv_cash = float(m - 1) * one_minus_c

        # NR4: Either m == N (pure all-NO conversion with S^c = empty) or all S^c legs have sellable bids
        if len(sc_set) == 0 or all(x["yes_net_bid"] > 0.0 and x["yes_token_id"] for x in sc_set):
            sc_proceeds = one_minus_c * sum(x["yes_net_bid"] for x in sc_set)
            net_edge_nr4 = conv_cash + sc_proceeds - cost_s - gas_per_sh
            max_sh_s = min(x["no_ask_size"] for x in s_set)
            max_sh_sc = min((x["yes_bid_size"] / max(one_minus_c, 1e-6)) for x in sc_set) if sc_set else max_sh_s
            avail_sh = round(min(max_sh_s, max_sh_sc), 2)
            if avail_sh >= min_shares and net_edge_nr4 >= float(min_net_edge_usd):
                if best_nr4 is None or net_edge_nr4 > float(best_nr4["net_edge_per_share"]):
                    index_mask = sum(1 << int(x["index"]) for x in s_set)
                    best_nr4 = {
                        "sleeve": "NR4_OPTIMAL_CHANNEL_CONVERT",
                        "box_type": "NEGRISK_CONVERT",
                        "convert_mode": "NR4_FULL_SWEEP",
                        "event_id": str(event_id),
                        "neg_risk_market_id": str(neg_risk_market_id),
                        "fee_bips": eff_bips,
                        "m_no_legs": m,
                        "n_total_outcomes": n,
                        "index_set_bitmask": index_mask,
                        "s_no_legs": s_set,
                        "sc_yes_sell_legs": sc_set,
                        "freeroll_yes_legs": [],
                        "cost_per_share": round(cost_s, 6),
                        "conversion_cash_per_share": round(conv_cash, 6),
                        "complement_sell_cash_per_share": round(sc_proceeds, 6),
                        "net_edge_per_share": round(net_edge_nr4, 6),
                        "max_fillable_shares": avail_sh,
                        "partition_info": part_info,
                    }

        # NR5: Liquid subset `U \subsetneq S^c` pays for `S` + positive instant cash while retaining `R = S^c \setminus U`!
        if len(sc_set) >= 2:
            # Partition S^c into liquid high-bid leaders `U` and tail lottery outcomes `R`
            sc_by_bid = sorted(sc_set, key=lambda x: x["yes_net_bid"], reverse=True)
            for u_cnt in range(1, len(sc_by_bid)):
                u_set = sc_by_bid[:u_cnt]
                r_set = sc_by_bid[u_cnt:]
                if any(x["yes_net_bid"] <= 0.0 or not x["yes_token_id"] for x in u_set):
                    break
                u_proceeds = one_minus_c * sum(x["yes_net_bid"] for x in u_set)
                instant_net_cash = conv_cash + u_proceeds - cost_s - gas_per_sh
                max_sh_s = min(x["no_ask_size"] for x in s_set)
                max_sh_u = min((x["yes_bid_size"] / max(one_minus_c, 1e-6)) for x in u_set)
                avail_sh_5 = round(min(max_sh_s, max_sh_u), 2)
                if avail_sh_5 >= min_shares and instant_net_cash >= float(min_freeroll_cash_usd):
                    # Prefer largest freeroll basket `|R|` + highest instant cash
                    score_5 = instant_net_cash + 0.002 * len(r_set)
                    if best_nr5 is None or score_5 > float(best_nr5["_score"]):
                        index_mask = sum(1 << int(x["index"]) for x in s_set)
                        best_nr5 = {
                            "sleeve": "NR5_LOTTERY_FREEROLL_CONVERT",
                            "box_type": "NEGRISK_CONVERT",
                            "convert_mode": "NR5_NEGATIVE_COST_FREEROLL",
                            "event_id": str(event_id),
                            "neg_risk_market_id": str(neg_risk_market_id),
                            "fee_bips": eff_bips,
                            "m_no_legs": m,
                            "n_total_outcomes": n,
                            "index_set_bitmask": index_mask,
                            "s_no_legs": s_set,
                            "sc_yes_sell_legs": u_set,
                            "freeroll_yes_legs": r_set,
                            "freeroll_ticket_count": len(r_set),
                            "cost_per_share": round(cost_s, 6),
                            "conversion_cash_per_share": round(conv_cash, 6),
                            "complement_sell_cash_per_share": round(u_proceeds, 6),
                            "net_edge_per_share": round(instant_net_cash, 6),
                            "upside_bonus_if_tail_hits_per_share": round(one_minus_c, 6),
                            "max_fillable_shares": avail_sh_5,
                            "partition_info": part_info,
                            "_score": score_5,
                        }

    out: List[Dict[str, Any]] = []
    if best_nr4 is not None:
        out.append(best_nr4)
    if best_nr5 is not None:
        best_nr5.pop("_score", None)
        out.append(best_nr5)
    return out


def detect_nr6_cross_slate_surjection_box(
    fine_legs: Sequence[Mapping[str, Any]],
    coarse_leg: Mapping[str, Any],
    *,
    relation: str = "DISJOINT_SUBSET_OF_COARSE",
    same_oracle_verified: bool = True,
    min_net_edge_usd: float = 0.005,
    min_shares: float = 5.0,
) -> Optional[Dict[str, Any]]:
    """
    `NR6_CROSS_SLATE_SURJECTION_BOX`:
      1. `DISJOINT_SUBSET_OF_COARSE` (`A_1 \\sqcup ... \\sqcup A_k \\subseteq B`, `k >= 1`):
         Buy `NO(A_1) + ... + NO(A_k) + YES(B)`.
         State proof:
           - If `\\omega \\in A_j`: `(k - 1)` NOs pay `$1` + `YES(B)` pays `$1` => `$k.00`.
           - If `\\omega \\notin \\cup A_i`: all `k` NOs pay `$1` (+ `YES(B) >= 0`) => `>= $k.00`.
         Guaranteed minimum payout = `$k.00`!
      2. `COARSE_COVERED_BY_UNION` (`B \\subseteq A_1 \\cup ... \\cup A_k`):
         Buy `NO(B) + YES(A_1) + ... + YES(A_k)`.
         State proof:
           - If `\\omega \\notin B`: `NO(B)` pays `$1` => `>= $1.00`.
           - If `\\omega \\in B`: at least one `A_j` holds so `YES(A_j)` pays `$1` => `>= $1.00`.
         Guaranteed minimum payout = `$1.00`!
    """
    if not same_oracle_verified or not fine_legs or not isinstance(coarse_leg, Mapping):
        return None
    k = len(fine_legs)
    rel = str(relation or "DISJOINT_SUBSET_OF_COARSE").upper()
    legs_to_buy: List[Dict[str, Any]] = []

    if rel == "DISJOINT_SUBSET_OF_COARSE":
        payout_floor = float(k)
        for idx, fl in enumerate(fine_legs):
            px = _sf(fl.get("no_ask") or fl.get("ask"), 0.0)
            sz = _sf(fl.get("no_ask_size") or fl.get("ask_size"), 0.0)
            tok = str(fl.get("no_token_id") or fl.get("token_id") or "").strip()
            f_r = _sf(fl.get("fee_rate"), 0.0)
            f_e = _sf(fl.get("fee_exponent"), 1.0)
            if not (0.001 <= px <= 0.999 and sz >= min_shares and tok):
                return None
            q_px, _, _ = quantize_dynamic_tick_price(px, "BUY", shares=min_shares, mode="taker")
            legs_to_buy.append(
                {
                    "role": f"FINE_NO_{idx}",
                    "token_id": tok,
                    "condition_id": str(fl.get("condition_id") or ""),
                    "ask_px": q_px,
                    "net_cost": q_px + compute_exact_taker_fee_per_share(q_px, f_r, f_e),
                    "ask_size": sz,
                }
            )
        c_px = _sf(coarse_leg.get("yes_ask") or coarse_leg.get("ask"), 0.0)
        c_sz = _sf(coarse_leg.get("yes_ask_size") or coarse_leg.get("ask_size"), 0.0)
        c_tok = str(coarse_leg.get("yes_token_id") or coarse_leg.get("token_id") or "").strip()
        c_fr = _sf(coarse_leg.get("fee_rate"), 0.0)
        c_fe = _sf(coarse_leg.get("fee_exponent"), 1.0)
        if not (0.001 <= c_px <= 0.999 and c_sz >= min_shares and c_tok):
            return None
        qc_px, _, _ = quantize_dynamic_tick_price(c_px, "BUY", shares=min_shares, mode="taker")
        legs_to_buy.append(
            {
                "role": "COARSE_YES",
                "token_id": c_tok,
                "condition_id": str(coarse_leg.get("condition_id") or ""),
                "ask_px": qc_px,
                "net_cost": qc_px + compute_exact_taker_fee_per_share(qc_px, c_fr, c_fe),
                "ask_size": c_sz,
            }
        )
    elif rel == "COARSE_COVERED_BY_UNION":
        payout_floor = 1.0
        c_px = _sf(coarse_leg.get("no_ask") or coarse_leg.get("ask"), 0.0)
        c_sz = _sf(coarse_leg.get("no_ask_size") or coarse_leg.get("ask_size"), 0.0)
        c_tok = str(coarse_leg.get("no_token_id") or coarse_leg.get("token_id") or "").strip()
        c_fr = _sf(coarse_leg.get("fee_rate"), 0.0)
        c_fe = _sf(coarse_leg.get("fee_exponent"), 1.0)
        if not (0.001 <= c_px <= 0.999 and c_sz >= min_shares and c_tok):
            return None
        qc_px, _, _ = quantize_dynamic_tick_price(c_px, "BUY", shares=min_shares, mode="taker")
        legs_to_buy.append(
            {
                "role": "COARSE_NO",
                "token_id": c_tok,
                "condition_id": str(coarse_leg.get("condition_id") or ""),
                "ask_px": qc_px,
                "net_cost": qc_px + compute_exact_taker_fee_per_share(qc_px, c_fr, c_fe),
                "ask_size": c_sz,
            }
        )
        for idx, fl in enumerate(fine_legs):
            px = _sf(fl.get("yes_ask") or fl.get("ask"), 0.0)
            sz = _sf(fl.get("yes_ask_size") or fl.get("ask_size"), 0.0)
            tok = str(fl.get("yes_token_id") or fl.get("token_id") or "").strip()
            f_r = _sf(fl.get("fee_rate"), 0.0)
            f_e = _sf(fl.get("fee_exponent"), 1.0)
            if not (0.001 <= px <= 0.999 and sz >= min_shares and tok):
                return None
            q_px, _, _ = quantize_dynamic_tick_price(px, "BUY", shares=min_shares, mode="taker")
            legs_to_buy.append(
                {
                    "role": f"FINE_YES_{idx}",
                    "token_id": tok,
                    "condition_id": str(fl.get("condition_id") or ""),
                    "ask_px": q_px,
                    "net_cost": q_px + compute_exact_taker_fee_per_share(q_px, f_r, f_e),
                    "ask_size": sz,
                }
            )
    else:
        return None

    total_cost = sum(x["net_cost"] for x in legs_to_buy)
    net_edge = payout_floor - total_cost
    max_sh = round(min(x["ask_size"] for x in legs_to_buy), 2)
    if max_sh < min_shares or net_edge < float(min_net_edge_usd):
        return None
    exp_cand = max((_sf(x.get("expiry_ts"), 0.0) for x in list(fine_legs) + [coarse_leg]), default=0.0)
    out_nr6: Dict[str, Any] = {
        "sleeve": "NR6_CROSS_SLATE_SURJECTION_BOX",
        "box_type": "DOMINANCE" if len(legs_to_buy) == 2 else "MULTI_LEG_BUNDLE",
        "relation": rel,
        "legs": legs_to_buy,
        "leg_count": len(legs_to_buy),
        "guaranteed_payout_per_share": payout_floor,
        "cost_per_share": round(total_cost, 6),
        "net_edge_per_share": round(net_edge, 6),
        "max_fillable_shares": max_sh,
    }
    if exp_cand > 0.0:
        out_nr6["expiry_ts"] = exp_cand
    return out_nr6


# ---------------------------------------------------------------------------
# 3. Family II: `S2_RTDS` 60s TWAP, `D1` Telescoping, `B1` One-Touch/Noon, `EQ1` Pyth Equity
# ---------------------------------------------------------------------------


def is_cme_metals_maintenance_window(ts: float) -> bool:
    """True during daily `17:00–18:00 ET` CME Globex / Chainlink Forex break and `Fri 17:00 ET..Sun 18:00 ET` close."""
    et_dt = datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone(ZoneInfo("America/New_York"))
    wd, hr = et_dt.weekday(), et_dt.hour
    return bool(hr == 17 or wd == 5 or (wd == 4 and hr >= 17) or (wd == 6 and hr < 18))


def hydrate_fast_s2_from_shm(daemon: Any, now_ts: float) -> Dict[str, Dict[str, Any]]:
    """
    Sub-millisecond `/dev/shm/pm_fast_tick_{ASSET}.json` pre-hydrator for `S2_RTDS_EXACT_TWAP_INTEGRATOR`:
      1. Warms `daemon.chainlink_open_cache` + `_strike_source = 'REST_VERIFIED'` directly from `polymarket-recorder`'s
         verified `m5`/`m15` `authoritative_chainlink_open` so `scan_exact_twap_locks` never stalls on HTTP 429s!
      2. Appends fresh `chainlink_proxy_spot` samples into `daemon.usd_spot_hist` at `>=0.85s` cadence (strictly skipping
         unanchored `chainlink_basis_anchored is False` perp proxies so `XAU`/`XAG` `usd_spot_hist` is never polluted).
      3. Returns `<1ms` SHM L2 books (`age_book_ms <= 950ms`) keyed by `token_id`.
    """
    import json as _json
    import os as _os

    shm_books: Dict[str, Dict[str, Any]] = {}
    if getattr(daemon, "single_scan", False) or ("fetch_json" in getattr(daemon, "__dict__", {})):
        return shm_books
    src_map = daemon.__dict__.setdefault("_strike_source", {})
    open_cache = getattr(daemon, "chainlink_open_cache", None)
    usd_hist_map = getattr(daemon, "usd_spot_hist", None)
    shm_dir = _os.environ.get("PM_FAST_TICK_DIR", "/dev/shm")
    for asset_sym in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "HYPE", "XAU", "XAG"):
        p_shm = _os.path.join(shm_dir, f"pm_fast_tick_{asset_sym}.json")
        if not _os.path.exists(p_shm):
            continue
        try:
            with open(p_shm, "r", encoding="utf-8") as fh:
                d = _json.load(fh)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        shm_ts = float(d.get("timestamp_unix") or d.get("ts") or 0.0)
        if shm_ts <= 0.0 or (now_ts - shm_ts) > 4.0:
            continue
        cl_px = float(d.get("chainlink_proxy_spot") or d.get("coinbase_spot") or 0.0)
        if cl_px <= 0.0:
            continue
        spot_ts = float(d.get("spot_ts") or shm_ts)
        if asset_sym in {"XAU", "XAG"} and (
            (now_ts - spot_ts) > 15.0 or ("chainlink_basis_anchored" in d and is_cme_metals_maintenance_window(now_ts))
        ):
            continue
        if isinstance(usd_hist_map, dict) and d.get("chainlink_basis_anchored") is not False:
            dq = usd_hist_map.get(asset_sym)
            if dq is not None and (not dq or (shm_ts - float(dq[-1][0])) >= 0.85):
                dq.append((shm_ts, cl_px))
        for hz_k, hz_lbl, dur_s in (("m5", "5m", 300), ("m15", "15m", 900), ("h4", "4h", 14400)):
            mh = d.get(hz_k)
            if not isinstance(mh, dict):
                continue
            exp_f = float(mh.get("expiry_ts") or 0.0)
            auth_op = float(mh.get("authoritative_chainlink_open") or 0.0)
            if exp_f > now_ts + 3.0 and auth_op > 0.0 and isinstance(open_cache, dict):
                st_i = int(round(exp_f)) - dur_s
                ck = f"{asset_sym}_{hz_lbl}_{st_i}"
                if ck not in open_cache:
                    open_cache[ck] = (exp_f, auth_op)
                src_map[ck] = (exp_f, "REST_VERIFIED")
            for side_k in ("UP", "DOWN"):
                sb = mh.get(side_k)
                if not isinstance(sb, dict):
                    continue
                tk_id = str(sb.get("token_id") or "")
                age_ms = float(sb.get("age_book_ms") if sb.get("age_book_ms") is not None else 9999.0)
                if tk_id and age_ms <= 950.0:
                    rb = sb.get("raw_top_bids") or []
                    ra = sb.get("raw_top_asks") or []
                    if rb or ra:
                        raw_tk = sb.get("minimum_tick_size") or sb.get("tick_size")
                        if raw_tk in (None, ""):
                            has_3dec = any(
                                len(r) >= 2 and float(r[1]) > 0 and abs(round(float(r[0]) * 100.0) - float(r[0]) * 100.0) > 1e-6
                                for r in (list(rb) + list(ra))
                            )
                            raw_tk = "0.001" if has_3dec else "0.01"
                        shm_books[tk_id] = {
                            "bids": [{"price": str(r[0]), "size": str(r[1])} for r in rb if len(r) >= 2 and float(r[1]) > 0],
                            "asks": [{"price": str(r[0]), "size": str(r[1])} for r in ra if len(r) >= 2 and float(r[1]) > 0],
                            "minimum_tick_size": str(raw_tk),
                        }
    return shm_books


def check_s2_live_adverse_move_cancel(
    cand_asset: str,
    side_s: str,
    candidate_box: Mapping[str, Any],
    exp_ts: float,
    now_ts: Optional[float] = None,
) -> bool:
    """Fast SHM spot + remaining-TWAP sigma monitor: cancels resting S2 Maker order if cushion drops `< 2.5 sigma`."""
    import json as _json
    import os as _os

    s2_open = float(candidate_box.get("s2_open_price") or 0.0)
    s2_sig = float(candidate_box.get("s2_sigma_1s") or 0.0)
    if s2_open <= 0.0 or s2_sig <= 0.0 or not cand_asset:
        return False
    shm_dir = _os.environ.get("PM_FAST_TICK_DIR", "/dev/shm")
    p_shm = _os.path.join(shm_dir, f"pm_fast_tick_{str(cand_asset).strip().upper()}.json")
    if not _os.path.exists(p_shm):
        return False
    try:
        with open(p_shm, "r", encoding="utf-8") as fh:
            d = _json.load(fh)
    except Exception:
        return False
    if not isinstance(d, dict):
        return False
    now_f = float(time.time() if now_ts is None else now_ts)
    shm_ts = float(d.get("timestamp_unix") or d.get("ts") or 0.0)
    cl_px = float(d.get("chainlink_proxy_spot") or d.get("coinbase_spot") or 0.0)
    if shm_ts <= 0.0 or (now_f - shm_ts) > 3.5 or cl_px <= 0.0:
        return False
    sgn = 1.0 if str(side_s or "UP").strip().upper() == "UP" else -1.0
    if sgn * (cl_px - s2_open) <= 0.0:
        return True
    n_rem = max(1, int(math.ceil(max(1.0, float(exp_ts) - now_f))))
    n_locked = max(0, min(59, int(candidate_box.get("s2_n_locked") or max(0, 60 - n_rem))))
    mean_obs = float(candidate_box.get("s2_mean_obs") or cl_px)
    tot_n = float(max(1, n_locked + n_rem))
    proj_twap = (float(n_locked) * mean_obs + float(n_rem) * cl_px) / tot_n
    rw_rem_std = s2_sig * math.sqrt(float((n_rem + 1) * (2 * n_rem + 1)) / 6.0)
    final_std = max(cl_px * 1e-6, math.hypot((float(n_rem) / tot_n) * rw_rem_std, cl_px * 0.00006))
    z_live = sgn * (proj_twap - s2_open) / final_std
    return bool(z_live < 2.5)


def evaluate_s2_rtds_exact_twap_integrator(
    *,
    asset: str,
    open_price: float,
    tte_sec: Optional[float] = None,
    samples_last_60s: Optional[Sequence[Tuple[float, float]]] = None,
    expiry_ts: Optional[float] = None,
    now_ts: Optional[float] = None,
    rtds_ticks: Optional[Sequence[Tuple[float, float]]] = None,
    official_twap_60s: Optional[float] = None,
    twap_lookback_sec: int = 60,
    live_lock_mode: bool = False,
    up_ask: float = 0.0,
    down_ask: float = 0.0,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
    min_net_edge: float = 0.010,
    min_lock_prob: float = 0.9985,
) -> Optional[Dict[str, Any]]:
    """
    `S2_RTDS_EXACT_TWAP_INTEGRATOR`:
    Integrates the live 1Hz Chainlink RTDS trajectory (+ `crypto_prices_twap_sixty` stream) inside
    the final `55s` (`3.8s <= TTE <= 38.0s` in `live_lock_mode`, requiring `>= 4.5 sigma` for `TTE > 22s`)
    of a `5m`/`15m`/`4h` 60s-TWAP candle across `BTC, ETH, SOL, XRP, BNB, DOGE, HYPE`.
    """
    sym = str(asset or "").strip().upper()
    if sym not in TWAP_60S_SUPPORTED_ASSETS or int(twap_lookback_sec or 0) != 60 or float(open_price) <= 0.0:
        return None
    now_f = float(time.time() if now_ts is None else now_ts)
    if tte_sec is None:
        if expiry_ts is None:
            return None
        rem_sec = float(expiry_ts) - now_f
    else:
        rem_sec = float(tte_sec)
    if live_lock_mode:
        if not (3.8 <= rem_sec <= 38.0):
            return None
    elif not (0.8 <= rem_sec <= 55.0):
        return None

    raw_samples = samples_last_60s if samples_last_60s is not None else (rtds_ticks or ())
    pts = sorted([(float(t), float(p)) for t, p in raw_samples if float(p) > 0.0], key=lambda x: x[0])
    if len(pts) < 6:
        return None

    n_rem = max(1, int(math.ceil(rem_sec)))
    elapsed_sec = max(1.0, 60.0 - rem_sec)
    min_req_ticks = max(8, int(math.floor(elapsed_sec * 0.72))) if live_lock_mode else max(8, 56 - n_rem)
    if expiry_ts is not None:
        win_start = float(expiry_ts) - 60.0
        win_pts = [(t, p) for t, p in pts if (win_start - 0.5) <= t <= (now_f + 1.0)]
        if len(win_pts) < min_req_ticks:
            pre_pts = [p for t, p in pts if (win_start - 65.0) <= t <= (win_start + 6.0)]
            if len(win_pts) >= 4 and pre_pts and (now_f - pts[-1][0]) <= 4.5:
                n_grid = max(8, int(round(elapsed_sec)))
                anchor_p = pre_pts[-1]
                idx_p = 0
                n_all = len(pts)
                step_prices: List[float] = []
                for k_g in range(n_grid):
                    t_g = min(now_f, win_start + float(k_g))
                    while idx_p < n_all and pts[idx_p][0] <= t_g + 1e-6:
                        anchor_p = pts[idx_p][1]
                        idx_p += 1
                    step_prices.append(anchor_p)
                win_pts = [(win_start + float(i), px_i) for i, px_i in enumerate(step_prices)]
            else:
                return None
    else:
        target_obs = max(8, min(len(pts), int(round(elapsed_sec))))
        win_pts = pts[-target_obs:]
        if len(win_pts) < min_req_ticks:
            return None

    win_prices = [p for _, p in win_pts[-60:]]
    mean_obs = sum(win_prices) / float(len(win_prices))
    cur_px = float(pts[-1][1]) if pts else win_prices[-1]
    if official_twap_60s is not None and float(official_twap_60s) > 0.0 and rem_sec <= 38.0:
        max_twap_div = (0.0025 if rem_sec > 22.0 else 0.0022) if live_lock_mode else 0.0025
        rolling_60 = [p for t, p in pts if (now_f - 60.5) <= t <= (now_f + 1.0)]
        ref_mean = (
            sum(rolling_60) / float(len(rolling_60))
            if (expiry_ts is not None and len(rolling_60) >= 20)
            else mean_obs
        )
        if abs(float(official_twap_60s) - ref_mean) / max(ref_mean, 1e-9) > max_twap_div:
            return None

    vol_pts = pts[-120:]
    norm_diffs = [
        abs(vol_pts[i][1] - vol_pts[i - 1][1]) / math.sqrt(max(1.0, vol_pts[i][0] - vol_pts[i - 1][0]))
        for i in range(1, len(vol_pts))
        if 0.0 <= (vol_pts[i][0] - vol_pts[i - 1][0]) <= 30.0
    ]
    vol_floor_1s = (
        0.000090 if sym in {"BTC", "ETH"} else (0.000125 if sym in {"SOL", "XRP", "BNB"} else 0.000165)
    )
    sigma_1s = max(
        cur_px * vol_floor_1s,
        (math.sqrt(sum(d * d for d in norm_diffs) / float(len(norm_diffs))) * 1.10) if norm_diffs else cur_px * (vol_floor_1s * 1.6),
        (max(norm_diffs) * 0.48) if norm_diffs else 0.0,
    )

    w_obs = float(len(win_prices)) / float(len(win_prices) + n_rem)
    w_rem = float(n_rem) / float(len(win_prices) + n_rem)
    expected_final_twap = w_obs * mean_obs + w_rem * cur_px

    open_f = float(open_price)
    if live_lock_mode:
        d_mean = mean_obs - open_f
        d_spot = cur_px - open_f
        d_proj = expected_final_twap - open_f
        if d_mean == 0.0 or d_spot == 0.0 or d_proj == 0.0:
            return None
        if not ((d_mean > 0.0) == (d_spot > 0.0) == (d_proj > 0.0)):
            return None

    elapsed_cushion_bps = (abs(mean_obs - open_f) / open_f) * 10000.0
    req_adverse_avg_move_bps = (elapsed_sec / max(0.5, rem_sec)) * elapsed_cushion_bps
    if live_lock_mode:
        min_adv_bps = 18.0 if rem_sec <= 10.5 else (22.0 if rem_sec <= 15.5 else (28.0 if rem_sec <= 22.0 else 34.0))
        if req_adverse_avg_move_bps < min_adv_bps:
            return None

    rw_rem_std = sigma_1s * math.sqrt(float((n_rem + 1) * (2 * n_rem + 1)) / 6.0)
    discretization_std = cur_px * 0.00006
    final_twap_std = max(cur_px * 1e-6, math.hypot(w_rem * rw_rem_std, discretization_std))

    z = (expected_final_twap - open_f) / final_twap_std
    min_z = (4.50 if rem_sec > 22.0 else 3.25) if live_lock_mode else 3.20
    if abs(z) < min_z:
        return None
    p_win = 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))
    req_prob = max(float(min_lock_prob), 0.9995 if rem_sec > 22.0 else 0.9990) if live_lock_mode else float(min_lock_prob)
    if p_win < req_prob:
        return None

    direction = "UP" if z > 0 else "DOWN"
    ask_px = float(up_ask if direction == "UP" else down_ask)
    if not (0.02 <= ask_px <= 0.997):
        return None
    q_ask, _, _ = quantize_dynamic_tick_price(ask_px, "BUY", shares=5.0, mode="taker")
    fee_sh = compute_exact_taker_fee_per_share(q_ask, float(fee_rate), float(fee_exponent))
    net_cost = q_ask + fee_sh
    ev_edge = p_win - net_cost
    if ev_edge < float(min_net_edge):
        return None

    return {
        "sleeve": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        "asset": sym,
        "direction": direction,
        "tte_sec": round(rem_sec, 2),
        "n_locked_ticks": len(win_prices),
        "n_remaining_ticks": n_rem,
        "locked_fraction": round(w_obs, 4),
        "elapsed_cushion_bps": round(elapsed_cushion_bps, 2),
        "req_adverse_avg_move_bps": round(req_adverse_avg_move_bps, 2),
        "expected_settlement_twap": round(expected_final_twap, 6),
        "mean_obs_twap": round(mean_obs, 6),
        "sigma_1s": round(sigma_1s, 6),
        "open_price": open_f,
        "z_score": round(z, 3),
        "p_model": round(min(0.9999, p_win), 6),
        "ask_px": q_ask,
        "net_cost_per_share": round(net_cost, 6),
        "net_edge_per_share": round(ev_edge, 6),
    }


def maybe_emit_s2_live_locks(
    daemon: Any,
    *,
    spec: Any,
    k_open: float,
    eval_now: float,
    rem_sec: float,
    samples: Sequence[Tuple[float, float]],
    off_twap_60: Optional[float],
    win_side: str = "",
    tok: str = "",
    opp_tok: str = "",
    bk: Optional[Dict[str, Any]] = None,
    bk_opp: Optional[Dict[str, Any]] = None,
    bks_s2: Optional[Dict[str, Dict[str, Any]]] = None,
    logger_obj: Any = None,
    **_extra_kw: Any,
) -> bool:
    """
    Dual-mode Live Gatling `S2_RTDS_EXACT_TWAP_INTEGRATOR` emitter (`3.8s <= rem_sec <= 38.0s`):
      1. Taker FOK Lock when `0.50 <= net_cost_per_share <= $0.9970`.
      2. `T-38s..T-5s` Post-Only Maker Lock (`SINGLE_LEG_MAKER_LOCK`, `0%` fee + `20%` crypto maker rebate) when
         `0.50 <= best_bid <= $0.9970` and `z >= 4.5` (`>22s`) / `z >= 3.30` (`<=22s`).
    """
    if not (3.8 <= rem_sec <= 38.0) or len(samples) < 6:
        return False
    bks_map = bks_s2 or {}
    if not win_side:
        last_px = float(samples[-1][1])
        if last_px == float(k_open):
            return False
        win_side = "UP" if last_px > float(k_open) else "DOWN"
    if not tok:
        tok = str(spec.up_token if win_side == "UP" else spec.down_token)
    if not opp_tok:
        opp_tok = str(spec.down_token if win_side == "UP" else spec.up_token)
    if bk is None:
        bk = bks_map.get(tok) or {}
    if bk_opp is None:
        bk_opp = bks_map.get(opp_tok)
    if not bk:
        return False

    ask_up_l1, _ = daemon._best_ask_sz(bks_map.get(spec.up_token) or (bk if win_side == "UP" else {}))
    ask_dn_l1, _ = daemon._best_ask_sz(bks_map.get(spec.down_token) or (bk if win_side == "DOWN" else {}))
    if 3.8 <= rem_sec <= 38.0:
        s2_rt = evaluate_s2_rtds_exact_twap_integrator(
            asset=spec.asset,
            open_price=k_open,
            expiry_ts=spec.end_ts,
            now_ts=eval_now,
            rtds_ticks=samples,
            official_twap_60s=off_twap_60,
            twap_lookback_sec=spec.twap_lookback_sec,
            live_lock_mode=True,
            up_ask=ask_up_l1 if ask_up_l1 < 1.0 else 0.0,
            down_ask=ask_dn_l1 if ask_dn_l1 < 1.0 else 0.0,
            fee_rate=spec.fee_rate,
            fee_exponent=spec.fee_exponent,
            min_net_edge=0.0028,
            min_lock_prob=0.9990,
        )
        if s2_rt is not None and s2_rt["direction"] == win_side and 0.50 <= float(s2_rt["net_cost_per_share"]) <= 0.9970:
            p_rt = float(s2_rt["p_model"])
            max_eff_s2 = min(0.9970, round(p_rt - 0.0028, 4))
            max_opp_s2 = max(0.08, round(1.015 - float(s2_rt["ask_px"]), 3))
            if daemon.emit_live_single_leg_lock_candidate(
                sleeve_source="S2_RTDS_EXACT_TWAP_INTEGRATOR",
                asset=spec.asset,
                dedupe_key=f"S2LIVE_{spec.asset}_{spec.horizon}_{spec.market_id}",
                token_id=tok,
                opp_token_id=opp_tok,
                market_id=spec.market_id,
                condition_id=spec.condition_id,
                side_label=win_side,
                display_label=f"{spec.asset} {spec.horizon} {win_side} TWAP Lock (TTE={rem_sec:.1f}s, z={s2_rt['z_score']:.1f})",
                bk_win=bk,
                bk_opp=bk_opp,
                fee_rate=spec.fee_rate,
                fee_exponent=spec.fee_exponent,
                neg_risk=spec.neg_risk,
                close_ts=spec.end_ts,
                now_ts=eval_now,
                max_lock_eff_px=max_eff_s2,
                max_opp_bid=max_opp_s2,
                hold_to_maturity=True,
                p_model=p_rt,
            ):
                (logger_obj or logger).info(
                    f"🔫 [GATLING S2 TAKER LOCK] {spec.asset} {spec.horizon} {win_side} | TTE={rem_sec:.1f}s | "
                    f"req_crash={s2_rt['req_adverse_avg_move_bps']:.0f}bps | z={s2_rt['z_score']:.2f} | net=${s2_rt['net_cost_per_share']:.4f}"
                )
                return True

    if 5.0 <= rem_sec <= 38.0 and hasattr(daemon, "emit_live_single_leg_maker_lock_candidate"):
        bids_w = sorted(
            [(float(b["price"]), float(b["size"])) for b in (bk.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
            key=lambda r: -r[0],
        )
        win_bid = bids_w[0][0] if bids_w else 0.0
        if 0.50 <= win_bid <= 0.997:
            s2_mk = evaluate_s2_rtds_exact_twap_integrator(
                asset=spec.asset,
                open_price=k_open,
                expiry_ts=spec.end_ts,
                now_ts=eval_now,
                rtds_ticks=samples,
                official_twap_60s=off_twap_60,
                twap_lookback_sec=spec.twap_lookback_sec,
                live_lock_mode=True,
                up_ask=0.90 if win_side == "UP" else 0.10,
                down_ask=0.90 if win_side == "DOWN" else 0.10,
                fee_rate=spec.fee_rate,
                fee_exponent=spec.fee_exponent,
                min_net_edge=0.0025,
                min_lock_prob=0.9990,
            )
            req_z_mk = 4.50 if rem_sec > 22.0 else 3.30
            req_adv_mk = 34.0 if rem_sec > 22.0 else 22.0
            if (
                s2_mk is not None
                and s2_mk["direction"] == win_side
                and abs(float(s2_mk["z_score"])) >= req_z_mk
                and float(s2_mk["req_adverse_avg_move_bps"]) >= req_adv_mk
            ):
                p_mk = float(s2_mk["p_model"])
                reb_ps = round(0.20 * float(spec.fee_rate) * ((win_bid * (1.0 - win_bid)) ** float(spec.fee_exponent)), 5) if float(spec.fee_rate) > 0.0 else 0.0
                bk_opp_eff = bk_opp if isinstance(bk_opp, dict) else {"bids": [], "asks": []}
                max_rb_s2 = 0.994 if win_bid <= 0.993 else 0.997
                min_ed_s2 = 0.005 if win_bid <= 0.993 else 0.0025
                bk_s2_m = dict(bk)
                bk_s2_m["_s2_meta"] = {
                    "s2_open_price": float(k_open),
                    "s2_sigma_1s": float(s2_mk["sigma_1s"]),
                    "s2_mean_obs": float(s2_mk["mean_obs_twap"]),
                    "s2_n_locked": int(s2_mk["n_locked_ticks"]),
                }
                if daemon.emit_live_single_leg_maker_lock_candidate(
                    sleeve_source="S2_RTDS_EXACT_TWAP_INTEGRATOR",
                    asset=spec.asset,
                    dedupe_key=f"S2MKR_{spec.asset}_{spec.horizon}_{spec.market_id}",
                    pair_dedupe_key=f"S2LIVE_{spec.asset}_{spec.horizon}_{spec.market_id}",
                    token_id=tok,
                    opp_token_id=opp_tok,
                    market_id=spec.market_id,
                    condition_id=spec.condition_id,
                    side_label=win_side,
                    display_label=f"{spec.asset} {spec.horizon} {win_side} TWAP Maker Lock (TTE={rem_sec:.1f}s)",
                    bk_win=bk_s2_m,
                    bk_opp=bk_opp_eff,
                    neg_risk=bool(spec.neg_risk),
                    close_ts=spec.end_ts,
                    now_ts=eval_now,
                    min_resting_bid=0.500 if win_bid < 0.800 else 0.800,
                    max_resting_bid=max_rb_s2,
                    min_maker_edge=min_ed_s2,
                    max_opp_bid=max(0.080, round(1.015 - win_bid, 3)),
                    hold_to_maturity=True,
                    p_model=p_mk,
                    maker_rebate_ps=reb_ps,
                ):
                    (logger_obj or logger).info(
                        f"🔫 [GATLING S2 MAKER LOCK] {spec.asset} {spec.horizon} {win_side} | TTE={rem_sec:.1f}s | "
                        f"bid=${win_bid:.3f} | req_crash={s2_mk['req_adverse_avg_move_bps']:.0f}bps | z={s2_mk['z_score']:.2f}"
                    )
                    return True
    return False


def compute_gatling_clip_budget_usd(
    *,
    live_equity: float,
    free_cash: float,
    cur_open_exp: float = 0.0,
    box_type: str = "DOMINANCE",
    sleeve_src: str = "",
    own_grad: bool = True,
    concave_exp: float = 0.65,
    base_clip_d1: float = 22.0,
    base_clip_core: float = 20.0,
    base_clip_bridge: float = 18.5,
    single_clip_cap_usd: float = 250.0,
    reserve_usd: float = 0.50,
    max_exposure_usd: float = 0.0,
) -> float:
    """
    Gatling High-Velocity Burst Gun Sizing (`0.65` book-depth concave reinvestment scaling):
    At `$60.92` starting NAV:
      - Core `D1` / `S2_EXACT_TWAP_LOCK` / `COMPLETE_SET` / `CTF_OVERROUND`: `$22.00/clip` (`3` concurrent slots!)
      - Core `NEGRISK_CONVERT` / `MULTI_LEG_BUNDLE` / `BOND1` / graduated locks: `$20.00/clip`
      - Bridged 0%-fee math boxes (`SPORTS_CORRIDOR`, `BARRIER_MONO`, `COUNTING_DOMINANCE`, etc.): `$18.50/clip`
    Scales smoothly with `clip_usd = base_clip * (NAV / 60.92) ** 0.65` so order size never outgrows L1/L2 depth
    while still compounding daily clip notional across `90+ clips/day`.
    """
    nav = max(10.0, float(live_equity or 0.0))
    cash = max(0.0, float(free_cash or 0.0))
    btype_u = str(box_type or "").upper()
    sl_u = str(sleeve_src or "").upper()

    if btype_u in {"DOMINANCE", "COMPLETE_SET", "CTF_OVERROUND"} or sl_u in {
        "S2_EXACT_TWAP_LOCK",
        "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        "D1_SAME_ORACLE_DOMINANCE_BOX",
        "D1_QUIET_BOOK_BOX",
        "D1_4H_DOMINANCE_BOX",
    }:
        base_clip = float(base_clip_d1)
    elif btype_u in {"NEGRISK_CONVERT", "MULTI_LEG_BUNDLE"} or own_grad or sl_u in {
        "BOND1_UMA_RESOLUTION_CARRY",
        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
    }:
        base_clip = float(base_clip_core)
    else:
        base_clip = float(base_clip_bridge)

    exp_f = min(0.90, max(0.35, float(concave_exp or 0.65)))
    depth_scale = (nav / GATLING_REF_NAV_USD) ** exp_f
    desired_clip = min(float(single_clip_cap_usd), round(base_clip * depth_scale, 2))
    port_cap = max(float(max_exposure_usd or 0.0), nav * 0.98)
    port_headroom = max(0.0, port_cap - max(0.0, float(cur_open_exp or 0.0)))
    avail_cash = max(0.0, cash - max(0.0, float(reserve_usd or 0.0)))
    return round(max(0.0, min(desired_clip, avail_cash, port_headroom)), 2)


PROTOCOL_V2_MATH_SLEEVES = {
    "B1_INTRADAY_ONETOUCH_NOON_BOX",
    "B1_ITO_BARRIER_DIGITAL_DOMINANCE",
    "EQ1_PYTH_EQUITY_DOMINANCE_BOX",
    "EQ1_TERMINAL_EQUITY_CLOSE_LOCK",
    "DC1_DOUBLE_CHANCE_1X2_PARITY",
    "LP_COMP1_SPORTS_TRIANGLES",
    "HALFTIME_FREEZE_OFFSET_BOX",
    "MENTION1_CUMULATIVE_LADDER_BOX",
    "NR6_CROSS_SLATE_SURJECTION_BOX",
    "CTF_OVERROUND_MINT_SELL",
    "W_PRUNE1_NR0_BASKET",
    "W_PRUNE1_DEAD_NO_BOND",
    "W_SOLAR1_POST_2351_LOCK",
    "UMA_READY1_LIVENESS_PRIORITY",
    "TW1_COUNTING_TRUNCATION_AND_BOX",
}


def maybe_cap_gatling_budget_sync(
    harvester: Any,
    budget: float,
    collat_f: float,
    cur_exp: float,
    box_type: str,
    sleeve_src: str,
    own_grad: bool,
    rb_cfg: Optional[Mapping[str, Any]],
    *,
    cap_usd: float = 250.0,
    reserve_u: float = 0.0,
    override_legacy_cap: bool = False,
) -> float:
    """Compact live Gatling clip-budget adapter keeping `polymarket_all_in_one.py < 1,000,000` bytes."""
    rb = rb_cfg or {}
    if not bool(rb.get("gatling_enabled", False)):
        return budget
    ex = getattr(harvester, "executor", None)
    live_real_ex = (
        not getattr(harvester, "dry_run", True)
        and hasattr(harvester, "_is_v5_unleashed_active")
        and bool(harvester._is_v5_unleashed_active())
        and getattr(ex, "client", None) is not None
        and getattr(getattr(ex, "client", None), "_mock_children", None) is None
        and "get_market_book" not in getattr(ex, "__dict__", {})
        and not getattr(harvester, "enforce_bond1_smart_queue", False)
    )
    if not (getattr(harvester, "enforce_gatling_sizing", False) or getattr(harvester, "enforce_gatling_fast_gun_reserve", False) or live_real_ex):
        return budget
    g_clip = compute_gatling_clip_budget_usd(
        live_equity=float(collat_f) + float(cur_exp),
        free_cash=float(collat_f),
        cur_open_exp=float(cur_exp),
        box_type=box_type,
        sleeve_src=sleeve_src,
        own_grad=own_grad,
        concave_exp=float(rb.get("gatling_concave_exp", 0.65)),
        base_clip_d1=float(rb.get("gatling_base_clip_d1_usd", 22.0)),
        base_clip_core=float(rb.get("gatling_base_clip_core_usd", 20.0)),
        base_clip_bridge=float(rb.get("gatling_base_clip_bridge_usd", 18.5)),
        single_clip_cap_usd=float(cap_usd),
        reserve_usd=float(reserve_u),
        max_exposure_usd=float(getattr(harvester, "max_exposure", 100.0)),
    )
    return g_clip if override_legacy_cap else min(float(budget), g_clip)


def cap_bond1_maker_for_gatling_reserve(
    harvester: Any,
    budget: float,
    collat_f: float,
    sll_used_u: float,
    rb_cfg: Optional[Mapping[str, Any]],
) -> float:
    """
    Reserves `max($20.00, 28% * NAV, gatling_fast_gun_reserve_usd)` of unencumbered free cash
    against `TTE > 10m` `BOND1` carry fills so passive carry never starves `<=90s` `S2` / `<15m` `D1` bursts.
    """
    rb = rb_cfg or {}
    if not bool(rb.get("gatling_enabled", False)):
        return float(budget)
    ex = getattr(harvester, "executor", None)
    live_real_ex = (
        not getattr(harvester, "dry_run", True)
        and hasattr(harvester, "_is_v5_unleashed_active")
        and bool(harvester._is_v5_unleashed_active())
        and getattr(ex, "client", None) is not None
        and getattr(getattr(ex, "client", None), "_mock_children", None) is None
        and "get_market_book" not in getattr(ex, "__dict__", {})
        and not getattr(harvester, "enforce_bond1_smart_queue", False)
    )
    if not (getattr(harvester, "enforce_gatling_fast_gun_reserve", False) or getattr(harvester, "enforce_gatling_sizing", False) or live_real_ex):
        return float(budget)
    total_b1_nav = float(collat_f) + float(sll_used_u)
    base_reserve = max(20.0, float(rb.get("gatling_fast_gun_reserve_usd", 20.0) or 20.0))
    eff_reserve = max(base_reserve, round(total_b1_nav * 0.28, 2))
    free_after_reserve = max(0.0, float(collat_f) - eff_reserve)
    per_mkt_seed_cap = (
        round(max(18.0, (total_b1_nav - eff_reserve) * 0.55), 2)
        if total_b1_nav <= 120.0
        else float(budget)
    )
    return round(max(0.0, min(float(budget), free_after_reserve, per_mkt_seed_cap)), 2)


PASSIVE_CARRY_SLEEVES = frozenset({
    "BOND1_UMA_RESOLUTION_CARRY",
    "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
    "MKR_REWARD_LOCKED_CARRY",
})

FAST_GUN_S2_SLEEVES = frozenset({
    "S2_RTDS_EXACT_TWAP_INTEGRATOR",
    "S2_EXACT_TWAP_LOCK",
})


def compute_sll_and_carry_gatling_budget(
    harvester: Any,
    legacy_budget: float,
    collat_f: float,
    cur_exp: float,
    box_type: str,
    sleeve_src: str,
    own_grad: bool,
    rb_cfg: Optional[Mapping[str, Any]],
    *,
    rem_tte_sec: float = 0.0,
    now_ts: Optional[float] = None,
    cap_usd: float = 250.0,
) -> float:
    """
    Two-tier Fast-Gun Reserve (`max($20.00, 28% * NAV)`):
      - Tier 1 (Passive `BOND1`/`BOND2`/`MKR_REWARD` UMA carries — whose true UMA resolution lockup is always `>10m` —
        and any single-leg carry with `rem_tte_sec > 600s` / `>10m`):
        MUST preserve `max($20.00, 28% * NAV, gatling_fast_gun_reserve_usd)` in free cash (`cap_bond1_maker_for_gatling_reserve`),
        and ultra-slow carries (`rem_tte_sec > 2400s` = `>40m`) are capped at `<= 38%` of NAV.
      - Tier 2 (`TTE <= 90s` `S2` locks, any non-UMA `0 < TTE <= 90s` lock, and `<15m` instant taker `D1` boxes):
        Explicitly ALLOWED to utilize the fast-gun reserve (`override_legacy_cap=True`, `reserve_u=0.50`).
    """
    rb = rb_cfg or {}
    if not bool(rb.get("gatling_enabled", False)):
        return float(legacy_budget)
    ex = getattr(harvester, "executor", None)
    live_real_ex = (
        not getattr(harvester, "dry_run", True)
        and hasattr(harvester, "_is_v5_unleashed_active")
        and bool(harvester._is_v5_unleashed_active())
        and getattr(ex, "client", None) is not None
        and getattr(getattr(ex, "client", None), "_mock_children", None) is None
        and "get_market_book" not in getattr(ex, "__dict__", {})
        and "execute_snipe_order" not in getattr(ex, "__dict__", {})
        and not getattr(harvester, "enforce_bond1_smart_queue", False)
    )
    if not (getattr(harvester, "enforce_gatling_sizing", False) or getattr(harvester, "enforce_gatling_fast_gun_reserve", False) or live_real_ex):
        return float(legacy_budget)

    sl_u = str(sleeve_src or "").upper()
    bt_u = str(box_type or "").upper()
    rem_f = float(rem_tte_sec or 0.0)
    now_f = float(time.time() if now_ts is None else now_ts)

    is_fast_gun_tier = (
        sl_u in FAST_GUN_S2_SLEEVES
        or (0.0 < rem_f <= 90.0 and sl_u not in PASSIVE_CARRY_SLEEVES)
        or (bt_u == "DOMINANCE" and (rem_f <= 0.0 or rem_f <= 900.0))
    )
    if not is_fast_gun_tier and (sl_u in PASSIVE_CARRY_SLEEVES or rem_f > 600.0):
        act_pos = getattr(harvester, "active_positions", None) or {}
        pend_int = getattr(harvester, "pending_entry_intents", None) or {}
        carry_used = sum(
            float(p.get("notional_usd", 0.0) or 0.0)
            for p in act_pos.values()
            if isinstance(p, Mapping)
            and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
            and (
                str(p.get("sleeve") or "").upper() in PASSIVE_CARRY_SLEEVES
                or (float(p.get("candle_expiry_ts", 0.0) or 0.0) - now_f) > 600.0
            )
        ) + sum(
            float(i.get("notional_usd", 0.0) or 0.0)
            for i in pend_int.values()
            if isinstance(i, Mapping)
            and i.get("live_maker_anchor_inflight")
            and str(i.get("sleeve_source") or i.get("sleeve") or "").upper() not in FAST_GUN_S2_SLEEVES
        )
        base_for_cap = float(legacy_budget) if float(legacy_budget) > 0.0 else float(collat_f)
        capped = cap_bond1_maker_for_gatling_reserve(
            harvester, base_for_cap, collat_f, max(carry_used, float(cur_exp)), rb
        )
        capped = maybe_cap_gatling_budget_sync(
            harvester,
            capped,
            collat_f,
            cur_exp,
            box_type,
            sleeve_src,
            own_grad,
            rb,
            cap_usd=cap_usd,
            reserve_u=0.0,
            override_legacy_cap=(sl_u not in PASSIVE_CARRY_SLEEVES),
        )
        if rem_f > 2400.0:
            slow_used = sum(
                float(p.get("notional_usd", 0.0) or 0.0)
                for p in act_pos.values()
                if isinstance(p, Mapping)
                and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
                and (float(p.get("candle_expiry_ts", 0.0) or 0.0) - now_f) > 2400.0
            )
            nav_tot = max(10.0, float(collat_f) + float(cur_exp))
            slow_cap_rem = max(0.0, round(max(20.0, nav_tot * 0.38) - slow_used, 2))
            capped = min(capped, slow_cap_rem)
        return round(max(0.0, capped), 2)

    return maybe_cap_gatling_budget_sync(
        harvester,
        legacy_budget,
        collat_f,
        cur_exp,
        box_type,
        sleeve_src,
        own_grad,
        rb,
        cap_usd=cap_usd,
        reserve_u=0.50,
        override_legacy_cap=True,
    )


def _interpret_delayed_recycle_poll_summary(
    ex: Any,
    res: Mapping[str, Any],
    oid: str,
    summary: Optional[Mapping[str, Any]],
    limit_price: Optional[float],
) -> Optional[Dict[str, Any]]:
    if not isinstance(summary, Mapping):
        return None
    m = float(summary.get("matched") or 0.0)
    resting = bool(summary.get("resting"))
    term = bool(summary.get("terminal"))
    is_canc = bool(summary.get("is_canceled"))
    st_u = str(summary.get("status") or "").upper()
    res_id = res.get("reservation_id")
    if m <= 1e-6 and (term or is_canc) and not resting:
        if res_id and hasattr(ex, "release_inventory"):
            ex.release_inventory(reservation_id=str(res_id))
        return {
            **dict(res),
            "outcome_unknown": False,
            "success": False,
            "matched_size": 0.0,
            "taking_amount": 0.0,
            "reservation_id": None,
        }
    if m > 1e-6 and not resting and (term or (st_u != "INVALID" and (is_canc or st_u in {"MATCHED", "MINED", "CONFIRMED"}))):
        if res_id and hasattr(ex, "release_inventory"):
            ex.release_inventory(reservation_id=str(res_id))
        raw_cash = float(summary.get("cash") or 0.0)
        avg_px = float(summary.get("avg_price") or limit_price or 0.998)
        cash = raw_cash if raw_cash > 0.0 else round(m * max(float(limit_price or 0.0), avg_px), 6)
        cash_est = bool(summary.get("cash_is_estimated", summary.get("estimated", False)) or not term or st_u == "MATCHED" or raw_cash <= 0.0)
        return {
            **dict(res),
            "outcome_unknown": False,
            "success": True,
            "orderID": oid,
            "matched_size": m,
            "taking_amount": cash,
            "taking_amount_missing": False,
            "taking_amount_estimated": cash_est,
            "fee_usd": float(summary.get("fee") or 0.0),
            "fee_is_estimated": bool(summary.get("fee_estimated", True)),
            "reservation_id": None,
        }
    return None


async def poll_delayed_recycle_unwind_async(
    harvester: Any,
    pos: Mapping[str, Any],
    res: Any,
    limit_price: Optional[float],
    *,
    max_wait_sec: float = 5.0,
    poll_interval_sec: float = 0.5,
) -> Any:
    """
    Polls CLOB `get_order_fill_summary` for up to `5.0s` when `HTM_EARLY_998_PROFIT_RECYCLE` receives
    a transient `Status: delayed` (`outcome_unknown=True`) response before escalating to `[GLOBAL HALT]`.
    """
    if not isinstance(res, Mapping) or not bool(res.get("outcome_unknown")):
        return res
    ex = getattr(harvester, "executor", None)
    oid = str(res.get("orderID") or res.get("order_id") or "").strip()
    tok = str(pos.get("token_id") or "").strip()
    if ex is None or not oid or not hasattr(ex, "get_order_fill_summary"):
        return res
    steps = max(1, int(round(max(0.5, float(max_wait_sec)) / max(0.1, float(poll_interval_sec)))))
    for idx in range(steps):
        if idx > 0:
            await asyncio.sleep(float(poll_interval_sec))
        try:
            summ = await asyncio.to_thread(ex.get_order_fill_summary, oid, tok)
        except Exception:
            summ = None
        resolved = _interpret_delayed_recycle_poll_summary(ex, res, oid, summ, limit_price)
        if resolved is not None:
            resolved["_delayed_recycle_polled"] = True
            logger.info(
                f"♻️ [DELAYED RECYCLE RESOLVED] order={oid} -> success={resolved.get('success')} "
                f"matched={resolved.get('matched_size', 0.0):.2f}"
            )
            return resolved
    out = dict(res)
    out["_delayed_recycle_polled"] = True
    return out


def resolve_delayed_recycle_unwind_sync(
    harvester: Any,
    pos: Mapping[str, Any],
    res: Any,
    close_reason: str,
    limit_price: Optional[float],
    *,
    max_wait_sec: float = 5.0,
    poll_interval_sec: float = 0.5,
) -> Any:
    """Synchronous fallback inside `_handle_unwind_response` when `HTM_EARLY_998_PROFIT_RECYCLE` is delayed."""
    if (
        str(close_reason or "") != "HTM_EARLY_998_PROFIT_RECYCLE"
        or not isinstance(res, Mapping)
        or not bool(res.get("outcome_unknown"))
        or bool(res.get("_delayed_recycle_polled"))
    ):
        return res
    ex = getattr(harvester, "executor", None)
    oid = str(res.get("orderID") or res.get("order_id") or "").strip()
    tok = str(pos.get("token_id") or "").strip()
    if ex is None or not oid or not hasattr(ex, "get_order_fill_summary"):
        return res
    steps = max(1, int(round(max(0.5, float(max_wait_sec)) / max(0.1, float(poll_interval_sec)))))
    for idx in range(steps):
        if idx > 0:
            time.sleep(float(poll_interval_sec))
        try:
            summ = ex.get_order_fill_summary(oid, tok)
        except Exception:
            summ = None
        resolved = _interpret_delayed_recycle_poll_summary(ex, res, oid, summ, limit_price)
        if resolved is not None:
            resolved["_delayed_recycle_polled"] = True
            return resolved
    return res


def compute_d1_per_market_notional_cap(harvester: Any) -> float:
    rcfg = getattr(harvester, "risk_config", None) or {}
    explicit = float(rcfg.get("bond1_per_market_cap_usd", 0.0) or 0.0)
    if explicit > 0.0:
        return explicit
    collat = float(getattr(harvester, "_last_known_collateral", 0.0) or 0.0)
    act_pos = getattr(harvester, "active_positions", None) or {}
    open_u = sum(
        float(p.get("notional_usd", 0.0) or 0.0)
        for p in act_pos.values()
        if isinstance(p, Mapping) and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
    )
    nav = max(collat + open_u, float(getattr(harvester, "max_exposure", 35.0) or 35.0))
    is_v5 = bool(hasattr(harvester, "_is_v5_unleashed_active") and harvester._is_v5_unleashed_active())
    if is_v5:
        return round(min(45.0, max(25.0, nav * 0.46)), 2)
    return 25.0


def open_market_notional_usd(harvester: Any, market_ids: Sequence[str]) -> float:
    mset = {str(m).strip() for m in (market_ids or ()) if str(m or "").strip()}
    if not mset:
        return 0.0
    act_pos = getattr(harvester, "active_positions", None) or {}
    pend_int = getattr(harvester, "pending_entry_intents", None) or {}
    used = sum(
        float(p.get("notional_usd", 0.0) or 0.0)
        for p in act_pos.values()
        if isinstance(p, Mapping)
        and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
        and p.get("resolved_winning_outcome") is None
        and str(p.get("market_id") or "").strip() in mset
    ) + sum(
        float(i.get("notional_usd", 0.0) or 0.0)
        for i in pend_int.values()
        if isinstance(i, Mapping) and str(i.get("market_id") or "").strip() in mset
    )
    return round(used, 4)


def is_market_busy_for_scaling(
    harvester: Any,
    market_id: str,
    *,
    extra_busy_markets: Sequence[str] = (),
) -> bool:
    """
    Returns True if `market_id` has an in-flight entry, pending settlement/exit/liquidation, un-reconciled inventory,
    or open notional within `$4.85` of `compute_d1_per_market_notional_cap(harvester)`.
    Reconciled `hold_to_maturity_lock` positions below the per-market cap allow multi-clip scaling after cooldown.
    """
    mid = str(market_id or "").strip()
    if not mid:
        return False
    if mid in {str(x).strip() for x in (extra_busy_markets or ()) if str(x or "").strip()}:
        return True
    pend_int = getattr(harvester, "pending_entry_intents", None) or {}
    if any(isinstance(i, Mapping) and str(i.get("market_id") or "").strip() == mid for i in pend_int.values()):
        return True
    act_pos = getattr(harvester, "active_positions", None) or {}
    has_open_on_mkt = False
    for p in act_pos.values():
        if not isinstance(p, Mapping) or str(p.get("market_id") or "").strip() != mid:
            continue
        if str(p.get("status") or "") in {"AWAITING_ONCHAIN_SETTLEMENT", "SETTLED", "FILLED", "CLOSED"} or p.get("resolved_winning_outcome") is not None:
            continue
        has_open_on_mkt = True
        if (
            not bool(p.get("hold_to_maturity_lock"))
            or not bool(p.get("inventory_reconciled"))
            or bool(p.get("is_liquidating"))
            or bool(p.get("exit_order_id"))
            or bool(p.get("unwind_order_id"))
            or str(p.get("status") or "") in {"ENTRY_OUTCOME_UNKNOWN", "UNRESOLVED_SETTLEMENT", "MATCHED_PENDING_SETTLEMENT"}
        ):
            return True
    if not has_open_on_mkt:
        return False
    cap_u = compute_d1_per_market_notional_cap(harvester)
    return open_market_notional_usd(harvester, [mid]) >= max(5.0, cap_u - 4.85)


def _evict_order_q_key(order_q: Any, key: str) -> None:
    if order_q is None:
        return
    if isinstance(order_q, dict):
        order_q.pop(key, None)
        return
    try:
        while key in order_q:
            order_q.remove(key)
    except Exception:
        pass


def is_d1_dedupe_blocked(
    harvester: Any,
    dedupe_k: str,
    pair_dedupe_k: str,
    market_ids: Sequence[str],
    now_ts: float,
    *,
    cooldown_sec: float = 15.0,
) -> bool:
    """
    Replaces permanent `dedupe_k in seen_boxes` blocking with a `15s` cooldown + per-market open-notional cap:
      - Within `cooldown_sec` (`15s`) of the last execution/attempt on `dedupe_k` or `pair_dedupe_k`: blocked (`True`).
      - After `cooldown_sec` (`15s`): if any target market has open non-receivable notional >= `per_mkt_cap - $4.85`,
        stays blocked (`True`); otherwise evicts the expired key(s) so multi-clip scaling and post-recycle re-entry proceed!
    """
    seen: set = harvester.__dict__.setdefault("_seen_d1_box_keys", set())
    keys = [str(k).strip() for k in (dedupe_k, pair_dedupe_k) if str(k or "").strip()]
    matched = [k for k in keys if k in seen]
    if not matched:
        return False
    ts_map: Dict[str, float] = harvester.__dict__.setdefault("_seen_d1_box_ts", {})
    now_f = float(now_ts or time.time())
    for k in matched:
        t_rec = ts_map.get(k)
        if t_rec is None:
            ts_map[k] = now_f
            return True
        if (now_f - float(t_rec)) < float(cooldown_sec):
            return True
    cap_u = compute_d1_per_market_notional_cap(harvester)
    mids = [str(m).strip() for m in (market_ids or ()) if str(m or "").strip()]
    if mids and any(open_market_notional_usd(harvester, [m]) >= max(5.0, cap_u - 4.85) for m in mids):
        return True
    order_q = harvester.__dict__.get("_seen_d1_box_order")
    for k in matched:
        seen.discard(k)
        ts_map.pop(k, None)
        _evict_order_q_key(order_q, k)
    return False


def clear_d1_dedupe_on_close(harvester: Any, pos: Optional[Mapping[str, Any]]) -> List[str]:
    """
    Clears `dedupe_key` and `pair_dedupe_key` on merge / early-recycle / settlement redemption when no remaining
    active non-receivable position shares that key.
    """
    if not isinstance(pos, Mapping):
        return []
    seen: set = harvester.__dict__.setdefault("_seen_d1_box_keys", set())
    ts_map: Dict[str, float] = harvester.__dict__.setdefault("_seen_d1_box_ts", {})
    order_q = harvester.__dict__.get("_seen_d1_box_order")
    act_pos = getattr(harvester, "active_positions", None) or {}
    closing_tid = str(pos.get("trade_id") or "")
    cleared: List[str] = []
    for k_raw in (pos.get("dedupe_key"), pos.get("pair_dedupe_key")):
        k = str(k_raw or "").strip()
        if not k:
            continue
        still_open = any(
            sid != closing_tid
            and isinstance(sp, Mapping)
            and str(sp.get("status") or "") not in {"AWAITING_ONCHAIN_SETTLEMENT", "SETTLED", "FILLED", "CLOSED"}
            and sp.get("resolved_winning_outcome") is None
            and float(sp.get("remaining_shares", 1.0) or 0.0) > 0.01
            and k in {str(sp.get("dedupe_key") or "").strip(), str(sp.get("pair_dedupe_key") or "").strip()}
            for sid, sp in act_pos.items()
        )
        if still_open:
            continue
        if k in seen or k in ts_map:
            cleared.append(k)
        seen.discard(k)
        ts_map.pop(k, None)
        _evict_order_q_key(order_q, k)
    return cleared



async def maybe_early_profit_recycle_htm_lock(
    harvester: Any,
    tid: str,
    pos: Dict[str, Any],
    book: Optional[Mapping[str, Any]],
    now_ts: float,
) -> bool:
    """
    Automated Early `>= $0.998` Profit-Recycling for undisputed `hold_to_maturity_lock` positions:
    When `tte_rem >= 300s` (or waiting in UMA window) and live CLOB bids cover `100%` of `rem_shrs` at
    `min_bid_px >= $0.998` with strictly positive locked net profit (`>= max($0.03, 0.0012 * rem_shrs)`),
    immediately harvests the profit to free USDC `30-110m` early for high-velocity Gatling turnover!
    """
    if (
        getattr(harvester, "dry_run", True)
        or not bool(pos.get("hold_to_maturity_lock"))
        or bool(pos.get("is_dominance_box"))
        or str(pos.get("status") or "") != "POSITION_CONFIRMED"
        or not bool(pos.get("inventory_reconciled", False))
        or pos.get("is_liquidating")
        or pos.get("exit_order_id")
        or pos.get("resolved_winning_outcome") is not None
    ):
        return False
    tte_rem = float(pos.get("candle_expiry_ts", 0.0) or 0.0) - float(now_ts)
    if tte_rem < 300.0:
        return False
    if (float(now_ts) - float(pos.get("_last_early_recycle_ts", 0.0) or 0.0)) < 15.0:
        return False
    token_id = str(pos.get("token_id") or "")
    rem_shrs = float(pos.get("remaining_shares", pos.get("entry_shares", 0.0)) or 0.0)
    if not token_id or rem_shrs < 5.0 or not isinstance(book, Mapping):
        return False
    raw_bids = book.get("bids") or []
    qual_bids = sorted(
        [
            {
                "price": float(b["price"] if isinstance(b, Mapping) else b[0]),
                "size": float(b["size"] if isinstance(b, Mapping) else b[1]),
            }
            for b in raw_bids
            if float((b.get("price", 0.0) if isinstance(b, Mapping) else b[0]) or 0.0) >= 0.998
            and float((b.get("size", 0.0) if isinstance(b, Mapping) else b[1]) or 0.0) > 0.0
        ],
        key=lambda r: r["price"],
        reverse=True,
    )
    if not qual_bids:
        return False
    cum_sz = 0.0
    min_px = 0.0
    for lv in qual_bids:
        cum_sz += lv["size"]
        min_px = lv["price"]
        if cum_sz >= rem_shrs:
            break
    if cum_sz < rem_shrs or min_px < 0.998:
        return False
    _fr_raw = pos.get("fee_rate_applied")
    if _fr_raw is None:
        _fr_raw = pos.get("fee_rate_market", pos.get("fee_rate", 0.0))
    fr = float(_fr_raw or 0.0)
    fe = float(pos.get("fee_exponent_applied", pos.get("fee_exponent", 1.0)) or 1.0)
    est_exit_fee = (rem_shrs * fr * ((min_px * (1.0 - min_px)) ** fe)) if fr > 0.0 else 0.0
    est_net_pnl = float(harvester.calculate_realized_cash_pnl(pos, rem_shrs * min_px, est_exit_fee))
    if est_net_pnl < max(0.03, rem_shrs * 0.0012):
        return False
    ex = getattr(harvester, "executor", None)
    if ex is None or not hasattr(ex, "execute_unwind_order"):
        return False
    pos["_last_early_recycle_ts"] = float(now_ts)
    if isinstance(getattr(ex, "_fee_cache", None), dict) and token_id not in ex._fee_cache:
        ex._fee_cache[token_id] = (fr, fe)
    unwind_res = await asyncio.to_thread(
        ex.execute_unwind_order,
        token_id=token_id,
        size=rem_shrs,
        side="SELL",
        min_price=min_px,
        neg_risk=pos.get("neg_risk"),
    )
    if isinstance(unwind_res, Mapping) and bool(unwind_res.get("outcome_unknown")):
        unwind_res = await poll_delayed_recycle_unwind_async(harvester, pos, unwind_res, min_px)
    outcome = harvester._handle_unwind_response(
        tid, pos, unwind_res, rem_shrs, "HTM_EARLY_998_PROFIT_RECYCLE", "HOLD_TO_MATURITY_LOCK", min_px
    )
    if outcome == "PARTIAL":
        pos["is_liquidating"] = False
        pos["exit_order_status"] = "HOLD_TO_MATURITY_LOCK"
    if outcome != "FAILED":
        if hasattr(ex, "invalidate_collateral_cache"):
            ex.invalidate_collateral_cache()
        harvester._pending_collateral_refresh = True
        harvester.save_state()
        logger.info(
            f"♻️ [GATLING EARLY 998 RECYCLE] {tid} ({pos.get('sleeve')}): harvested {rem_shrs:.2f} sh @ >=${min_px:.3f} "
            f"({tte_rem/60.0:.1f}m early, locked_net=${est_net_pnl:+.2f}) -> {outcome}"
        )
        return True
    return False


def consolidate_any_box_leg_close(
    harvester: Any,
    tid: str,
    pos: Dict[str, Any],
    cum_cash: float,
    cum_fee: float,
    net_pnl: float,
    reason: str,
    record_pnl: bool,
) -> Tuple[bool, float]:
    """
    Consolidates 2-leg `DOMINANCE` AND `3..12`-leg `MULTI_LEG_BUNDLE` box closes so OTM hedge legs
    never emit false standalone losses, while preserving `_closed_partner_leg` / `_closed_bundle_legs`
    even when an asymmetric unwind cleared `is_dominance_box` on the final leg (`BUG-D1` fix).
    """
    if not record_pnl:
        return False, net_pnl
    has_prior = ("_closed_partner_leg" in pos) or ("_closed_bundle_legs" in pos)
    if not has_prior and not pos.get("is_dominance_box"):
        return False, net_pnl

    prior_legs: List[Dict[str, Any]] = []
    p1 = pos.pop("_closed_partner_leg", None)
    if isinstance(p1, dict):
        prior_legs.append(p1)
    p_list = pos.pop("_closed_bundle_legs", None)
    if isinstance(p_list, list):
        prior_legs.extend([x for x in p_list if isinstance(x, dict)])

    this_leg = {
        "trade_id": tid,
        "target_token": pos.get("target_token"),
        "market_id": pos.get("market_id"),
        "notional_usd": round(float(pos.get("notional_usd", 0.0) or 0.0), 4),
        "payout_usd": round(float(cum_cash), 4),
        "exit_fee_usd": round(float(cum_fee), 4),
        "net_pnl_usd": round(float(net_pnl), 4),
        "close_reason": reason,
    }

    active_map = getattr(harvester, "active_positions", {}) or {}
    partner_tid = str(pos.get("box_partner_trade_id") or "")
    bid = str(pos.get("box_id") or "")
    target_sib_id = ""
    if partner_tid and partner_tid in active_map:
        target_sib_id = partner_tid
    elif bid:
        sibs = [
            sid
            for sid, sp in active_map.items()
            if sid != tid and isinstance(sp, Mapping) and str(sp.get("box_id") or "") == bid and sp.get("is_dominance_box")
        ]
        if sibs:
            target_sib_id = sibs[0]

    if target_sib_id and target_sib_id in active_map:
        sib_pos = active_map[target_sib_id]
        if partner_tid == target_sib_id and not prior_legs and "_closed_bundle_legs" not in sib_pos and "_closed_partner_leg" not in sib_pos:
            sib_pos["_closed_partner_leg"] = this_leg
        else:
            existing_p1 = sib_pos.pop("_closed_partner_leg", None)
            acc = list(sib_pos.get("_closed_bundle_legs") or [])
            if isinstance(existing_p1, dict):
                acc.append(existing_p1)
            acc.extend(prior_legs)
            acc.append(this_leg)
            sib_pos["_closed_bundle_legs"] = acc
        active_map.pop(tid, None)
        harvester.save_state()
        harvester._pending_collateral_refresh = True
        logger.info(f"[D1/BUNDLE LEG CLOSED] {tid} ({reason}) | Leg Cash=${cum_cash:.2f} | Awaiting sibling {target_sib_id}")
        return True, net_pnl

    clear_d1_dedupe_on_close(harvester, pos)
    if prior_legs:
        all_legs = prior_legs + [this_leg]
        tot_notional = round(sum(float(x.get("notional_usd", 0.0) or 0.0) for x in all_legs), 4)
        tot_payout = round(sum(float(x.get("payout_usd", 0.0) or 0.0) for x in all_legs), 2)
        tot_exit_fee = round(sum(float(x.get("exit_fee_usd", 0.0) or 0.0) for x in all_legs), 4)
        tot_pnl = round(sum(float(x.get("net_pnl_usd", 0.0) or 0.0) for x in all_legs), 2)
        pos["trade_id"] = str(pos.get("box_id") or tid)
        pos["notional_usd"] = tot_notional
        pos["payout_usd"] = tot_payout
        pos["realized_exit_fee"] = tot_exit_fee
        pos["net_pnl_usd"] = tot_pnl
        pos["won"] = tot_pnl >= 0.0
        reasons_joined = "+".join(str(x.get("close_reason") or "") for x in all_legs)
        pos["close_reason"] = f"D1_BOX_CONSOLIDATED({reasons_joined})"
        pos["exit_decomposition_bucket"] = "DOMINANCE_BOX_ARB"
        pos["box_legs_summary"] = all_legs
        return False, tot_pnl

    return False, net_pnl


def compute_gatling_trajectory_projection(
    *,
    starting_nav_usd: float = GATLING_REF_NAV_USD,
    clips_per_day: float = 90.0,
    base_clip_usd: float = 22.0,
    net_edge_bps: float = 58.0,
    depth_exp: float = 0.65,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Computes exact 30-day Linear vs. Depth-Scaled Compounded (`0.65` book-depth exponent) NAV trajectory
    across daily clip-velocity regimes (`Legacy Musket`, `Phase 1-2`, `Phase 3 Target Gun`, `High-Vol Burst Gun`).
    """
    nav0 = max(1.0, float(starting_nav_usd))
    cpd = max(0.0, float(clips_per_day))
    c0 = max(0.0, float(base_clip_usd))
    edge_frac = max(0.0, float(net_edge_bps)) / 10000.0
    exp_f = min(1.0, max(0.25, float(depth_exp)))

    daily_linear_profit = cpd * c0 * edge_frac
    linear_nav = round(nav0 + float(days) * daily_linear_profit, 2)
    daily_scaled_rate = (daily_linear_profit / nav0) * exp_f
    comp_nav = round(nav0 * ((1.0 + daily_scaled_rate) ** float(days)), 2)

    return {
        "starting_nav_usd": round(nav0, 2),
        "clips_per_day": round(cpd, 1),
        "base_clip_usd": round(c0, 2),
        "net_edge_bps": round(float(net_edge_bps), 2),
        "depth_factor": round(exp_f, 2),
        "day1_linear_profit_usd": round(daily_linear_profit, 2),
        "day1_yield_pct": round(100.0 * daily_linear_profit / nav0, 2),
        "days": int(days),
        "linear_30d_nav_usd": linear_nav,
        "scaled_comp_30d_nav_usd": comp_nav,
        "net_profit_comp_30d_usd": round(comp_nav - nav0, 2),
        "nav_multiple_30d": round(comp_nav / nav0, 2),
    }


def detect_d1_telescoping_candle_bridge(
    *,
    asset: str,
    outer_horizon: str,
    inner_horizon: str,
    outer_expiry_ts: float,
    inner_expiry_ts: float,
    outer_open: float,
    inner_open: float,
    outer_up_ask: float,
    outer_down_ask: float,
    inner_up_ask: float,
    inner_down_ask: float,
    outer_up_token: str,
    outer_down_token: str,
    inner_up_token: str,
    inner_down_token: str,
    outer_condition_id: str = "",
    inner_condition_id: str = "",
    now_ts: Optional[float] = None,
    max_lockup_sec: float = 300.0,
    fee_rate_outer: float = 0.07,
    fee_rate_inner: float = 0.07,
    min_net_edge_usd: float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    `D1_TELESCOPING_CANDLE_BRIDGE`:
    Matches a `15m` candle against its final (3rd) `5m` sub-candle, or a `1h` candle against its
    final (4th) `15m` sub-candle when BOTH expire at the EXACT SAME timestamp (`|T_outer - T_inner| <= 1s`)
    on the exact same Chainlink RTDS oracle!
      - If `inner_open > outer_open`: `YES(inner_DOWN) + YES(outer_UP)` pays `>= $1.00` everywhere
        and `$2.00` in the corridor `[outer_open, inner_open)`!
      - If `inner_open < outer_open`: `YES(outer_DOWN) + YES(inner_UP)` pays `>= $1.00` everywhere
        and `$2.00` in the corridor `[inner_open, outer_open)`!
    """
    now_f = float(time.time() if now_ts is None else now_ts)
    if abs(float(outer_expiry_ts) - float(inner_expiry_ts)) > 1.5:
        return None
    tte = float(outer_expiry_ts) - now_f
    if not (5.0 <= tte <= float(max_lockup_sec)):
        return None
    if float(outer_open) <= 0.0 or float(inner_open) <= 0.0:
        return None
    # Require meaningful strike separation (> 1.5 bps) so open-price rounding noise cannot invert corridor
    rel_gap = abs(float(inner_open) - float(outer_open)) / max(float(outer_open), 1e-9)
    if rel_gap < 0.00015:
        return None

    if float(inner_open) > float(outer_open):
        # Buy inner DOWN + outer UP
        px_a, tok_a, cid_a, fr_a, desc_a = (
            float(inner_down_ask),
            str(inner_down_token),
            str(inner_condition_id),
            float(fee_rate_inner),
            f"{inner_horizon}_DOWN",
        )
        px_b, tok_b, cid_b, fr_b, desc_b = (
            float(outer_up_ask),
            str(outer_up_token),
            str(outer_condition_id),
            float(fee_rate_outer),
            f"{outer_horizon}_UP",
        )
        corridor = (float(outer_open), float(inner_open))
    else:
        # Buy outer DOWN + inner UP
        px_a, tok_a, cid_a, fr_a, desc_a = (
            float(outer_down_ask),
            str(outer_down_token),
            str(outer_condition_id),
            float(fee_rate_outer),
            f"{outer_horizon}_DOWN",
        )
        px_b, tok_b, cid_b, fr_b, desc_b = (
            float(inner_up_ask),
            str(inner_up_token),
            str(inner_condition_id),
            float(fee_rate_inner),
            f"{inner_horizon}_UP",
        )
        corridor = (float(inner_open), float(outer_open))

    if not (0.01 <= px_a <= 0.98 and 0.01 <= px_b <= 0.98 and tok_a and tok_b):
        return None
    qa, _, _ = quantize_dynamic_tick_price(px_a, "BUY", shares=5.0, mode="taker")
    qb, _, _ = quantize_dynamic_tick_price(px_b, "BUY", shares=5.0, mode="taker")
    cost_a = qa + compute_exact_taker_fee_per_share(qa, fr_a, 1.0)
    cost_b = qb + compute_exact_taker_fee_per_share(qb, fr_b, 1.0)
    total_cost = cost_a + cost_b
    net_edge = 1.0 - total_cost
    if net_edge < float(min_net_edge_usd):
        return None

    return {
        "sleeve": "D1_TELESCOPING_CANDLE_BRIDGE",
        "box_type": "DOMINANCE",
        "asset": str(asset).upper(),
        "outer_horizon": str(outer_horizon),
        "inner_horizon": str(inner_horizon),
        "tte_sec": round(tte, 2),
        "leg_a": {"label": desc_a, "token_id": tok_a, "condition_id": cid_a, "ask_px": qa, "fee_rate": fr_a},
        "leg_b": {"label": desc_b, "token_id": tok_b, "condition_id": cid_b, "ask_px": qb, "fee_rate": fr_b},
        "double_payout_corridor": corridor,
        "cost_per_share": round(total_cost, 6),
        "net_edge_per_share": round(net_edge, 6),
    }


def detect_b1_intraday_onetouch_noon_box(
    *,
    asset: str,
    strike: float,
    direction: str,
    oracle_touch: str,
    oracle_noon: str,
    touch_yes_ask: float,
    noon_no_ask: float,
    touch_yes_token: str,
    noon_no_token: str,
    touch_condition_id: str = "",
    noon_condition_id: str = "",
    et_hour_float: float = 11.0,
    fee_rate: float = 0.0,
    min_net_edge_usd: float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    `B1_INTRADAY_ONETOUCH_NOON_BOX` (`10:15-12:00 ET`):
    For an upper barrier `K` (`direction == "ABOVE"`):
      `Spot_12:00_ET >= K` implies `max_{t in day} Spot_t >= K` (`OneTouch >= K`)!
      Therefore `YES(OneTouch >= K) + NO(Noon >= K)` pays `>= $1.00` in every path (and `$2.00` if touched
      intraday while Noon settles `< K`)!
    Strictly requires identical underlying oracle feed (`oracle_touch == oracle_noon`) and active `10:15-12:00 ET` window.
    """
    if str(oracle_touch or "").strip().lower() != str(oracle_noon or "").strip().lower() or not oracle_touch:
        return None
    if not (10.25 <= float(et_hour_float) <= 12.0):
        return None
    if str(direction or "").upper() not in {"ABOVE", "UP", "REACH", "DIP", "BELOW"}:
        return None
    if not (0.005 <= float(touch_yes_ask) <= 0.99 and 0.005 <= float(noon_no_ask) <= 0.99):
        return None
    if not touch_yes_token or not noon_no_token:
        return None
    qa, _, _ = quantize_dynamic_tick_price(float(touch_yes_ask), "BUY", shares=5.0, mode="taker")
    qb, _, _ = quantize_dynamic_tick_price(float(noon_no_ask), "BUY", shares=5.0, mode="taker")
    ca = qa + compute_exact_taker_fee_per_share(qa, float(fee_rate), 1.0)
    cb = qb + compute_exact_taker_fee_per_share(qb, float(fee_rate), 1.0)
    net_edge = 1.0 - (ca + cb)
    if net_edge < float(min_net_edge_usd):
        return None
    return {
        "sleeve": "B1_INTRADAY_ONETOUCH_NOON_BOX",
        "box_type": "DOMINANCE",
        "asset": str(asset).upper(),
        "strike": float(strike),
        "leg_a": {"token_id": str(touch_yes_token), "condition_id": str(touch_condition_id), "ask_px": qa},
        "leg_b": {"token_id": str(noon_no_token), "condition_id": str(noon_condition_id), "ask_px": qb},
        "cost_per_share": round(ca + cb, 6),
        "net_edge_per_share": round(net_edge, 6),
    }


def detect_eq1_pyth_equity_dominance_box(
    strike_contracts: Sequence[Mapping[str, Any]],
    *,
    ticker: str,
    et_hour_float: float = 15.0,
    corporate_action_flag: bool = False,
    min_net_edge_usd: float = 0.004,
    min_shares: float = 5.0,
) -> List[Dict[str, Any]]:
    """
    `EQ1_PYTH_EQUITY_DOMINANCE_BOX` (`14:15-16:00 ET`):
    Scans same-day Pyth regular-session close (`16:00 ET`) equity threshold contracts (`Close >= K_i`)
    for monotonic dominance: `YES(Close >= K_low) + NO(Close >= K_high) < $1.00` (`K_low < K_high`).
    """
    sym = str(ticker or "").strip().upper()
    if corporate_action_flag or sym not in PYTH_EQUITY_SYMBOLS or not (14.25 <= float(et_hour_float) <= 16.0):
        return []
    valid: List[Dict[str, Any]] = []
    for c in strike_contracts or []:
        if str(c.get("oracle") or "pyth").strip().lower() != "pyth":
            continue
        k = _sf(c.get("strike"), -1.0)
        ya = _sf(c.get("yes_ask"), 0.0)
        na = _sf(c.get("no_ask"), 0.0)
        ysz = _sf(c.get("yes_ask_size"), 5.0)
        nsz = _sf(c.get("no_ask_size"), 5.0)
        if k > 0.0 and (ya > 0.0 or na > 0.0):
            valid.append(
                {
                    "strike": k,
                    "settle_date": str(c.get("settle_date") or ""),
                    "condition_id": str(c.get("condition_id") or ""),
                    "yes_token_id": str(c.get("yes_token_id") or ""),
                    "no_token_id": str(c.get("no_token_id") or ""),
                    "yes_ask": ya,
                    "no_ask": na,
                    "yes_ask_size": ysz,
                    "no_ask_size": nsz,
                    "fee_rate": _sf(c.get("fee_rate"), 0.0),
                }
            )
    valid.sort(key=lambda r: r["strike"])
    boxes: List[Dict[str, Any]] = []
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            lo, hi = valid[i], valid[j]
            if lo["settle_date"] != hi["settle_date"] or hi["strike"] <= lo["strike"]:
                continue
            if not (lo["yes_token_id"] and hi["no_token_id"]):
                continue
            if min(lo["yes_ask_size"], hi["no_ask_size"]) < min_shares:
                continue
            if not (0.002 <= lo["yes_ask"] <= 0.995 and 0.002 <= hi["no_ask"] <= 0.995):
                continue
            qa, _, _ = quantize_dynamic_tick_price(lo["yes_ask"], "BUY", shares=min_shares, mode="taker")
            qb, _, _ = quantize_dynamic_tick_price(hi["no_ask"], "BUY", shares=min_shares, mode="taker")
            ca = qa + compute_exact_taker_fee_per_share(qa, lo["fee_rate"], 1.0)
            cb = qb + compute_exact_taker_fee_per_share(qb, hi["fee_rate"], 1.0)
            edge = 1.0 - (ca + cb)
            if edge >= float(min_net_edge_usd):
                boxes.append(
                    {
                        "sleeve": "EQ1_PYTH_EQUITY_DOMINANCE_BOX",
                        "box_type": "DOMINANCE",
                        "asset": sym,
                        "strike_low": lo["strike"],
                        "strike_high": hi["strike"],
                        "leg_a": {"token_id": lo["yes_token_id"], "condition_id": lo["condition_id"], "ask_px": qa},
                        "leg_b": {"token_id": hi["no_token_id"], "condition_id": hi["condition_id"], "ask_px": qb},
                        "cost_per_share": round(ca + cb, 6),
                        "net_edge_per_share": round(edge, 6),
                        "max_fillable_shares": round(min(lo["yes_ask_size"], hi["no_ask_size"]), 2),
                    }
                )
    boxes.sort(key=lambda b: b["net_edge_per_share"], reverse=True)
    return boxes


# ---------------------------------------------------------------------------
# 4. Family III: Weather METAR Monotonic Ratchet (`W_PRUNE1` & `W_SOLAR1`)
# ---------------------------------------------------------------------------

_METAR_T_REMARK_RE = re.compile(r"\bRMK\b.*?\bT([01])(\d{3})(?:[01]\d{3})?\b")
_METAR_BODY_TEMP_RE = re.compile(r"(?:^|\s)(M?\d{2})/(?:M?\d{2}|//)(?=\s|$)")
_HKO_SYNTH_RE = re.compile(r"^HKO_(?:MIN|MAX|1M)\s+(-?\d+(?:\.\d+)?)C$", re.IGNORECASE)
_METAR_ICAO_RE = re.compile(r"^(?:METAR\s+)?([A-Z]{4})\b")

WUNDERGROUND_INTL_INTEGER_STATIONS = frozenset(
    {
        "EGLC", "EGLL", "LFPG", "LFPB", "RKSI", "RKPK", "SBGR", "RJTT", "EDDM",
        "LEMD", "EHAM", "EPWA", "WSSS", "ZBAA", "ZSPD", "ZSQD", "ZUUU", "ZHHH",
        "ZUCK", "ZGGG", "ZGSZ", "ZSJN", "ZHCC", "LTFM", "LTAC", "LIMC", "EFHK",
        "LLBG", "OEJN", "OPKC", "VILK", "WMKK", "RCSS", "RPLL", "SAEZ", "NZWN",
        "CYYZ", "MMMX", "MPMG", "UUWW", "FACT",
    }
)


def _round_half_away_from_zero(val: float) -> int:
    d = Decimal(str(round(val, 6)))
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def classify_weather_station_oracle_rule(
    station_icao: str,
    *,
    unit: str = "F",
    rules_text: str = "",
    event_meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Distinguish Polymarket daily weather settlement oracle rules by station & rule text:
      1. `HKO_OFFICIAL_01C`: Hong Kong Observatory (`HKO`) 0.1°C official daily max/min.
      2. `US_NWS_CLI_01C_BEFORE_ROUNDING`: US NWS Daily Climate Report (`CLI`) — monotonic dead-bracket
         `NO` pruning remains sound, while `W_SOLAR1_POST_2351_LOCK` (`YES`) is vetoed due to inter-hour 1m ASOS max.
      3. `US_ASOS_01C_BEFORE_ROUNDING`: US `K*` ASOS (`0.1°C` `T`-group converted to `°F` BEFORE half-up rounding;
         `±0.55°C` safety bound when `T`-group absent).
      4. `WUNDERGROUND_INTEGER_METAR`: International airport routine METAR (`EGLC`, `LFPG`/`LFPB`, `RKSI`, `SBGR`, etc.)
         or explicit Wunderground whole-degree integer `°C` settlement (`unc_c = 0.0` on routine body integer `°C`).
    """
    icao = str(station_icao or "").strip().upper()
    u = str(unit or "F").strip().upper()
    meta_r = ""
    if isinstance(event_meta, Mapping):
        meta_r = f"{event_meta.get('rules_text') or ''} {event_meta.get('description') or ''}"
    txt = f"{rules_text} {meta_r}".lower()

    if icao == "HKO" or "hko.gov.hk" in txt or "hong kong observatory" in txt:
        return {
            "oracle_regime": "HKO_OFFICIAL_01C",
            "station_icao": icao or "HKO",
            "unit": u,
            "prefer_body_integer_c": False,
            "body_integer_exact_c": False,
            "allow_solar_lock": True,
        }
    if any(k in txt for k in ("climate report", "nws cli", "daily climate", "weather.gov/wrh/climate")):
        return {
            "oracle_regime": "US_NWS_CLI_01C_BEFORE_ROUNDING",
            "station_icao": icao,
            "unit": u,
            "prefer_body_integer_c": False,
            "body_integer_exact_c": False,
            "allow_solar_lock": False,
        }
    explicit_wu = "wunderground" in txt or "weather underground" in txt
    explicit_int_c = "whole degree" in txt or "integer metar" in txt
    is_us_k = len(icao) == 4 and icao.startswith("K")
    if explicit_int_c or (not is_us_k and (explicit_wu or (u == "C" and (icao in WUNDERGROUND_INTL_INTEGER_STATIONS or len(icao) == 4)))):
        return {
            "oracle_regime": "WUNDERGROUND_INTEGER_METAR",
            "station_icao": icao,
            "unit": u,
            "prefer_body_integer_c": True,
            "body_integer_exact_c": True,
            "allow_solar_lock": True,
        }
    return {
        "oracle_regime": "US_ASOS_01C_BEFORE_ROUNDING",
        "station_icao": icao,
        "unit": u,
        "prefer_body_integer_c": False,
        "body_integer_exact_c": False,
        "allow_solar_lock": True,
    }


def parse_routine_metar_temp_c(
    raw_metar: str,
    *,
    station_icao: str = "",
    unit: str = "F",
    rules_text: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Parse a routine `METAR` (or official `0.1°C` `HKO_MIN`/`HKO_MAX`/`HKO_1M`) observation string while
    **strictly rejecting unscheduled `SPECI` and `COR` reports**.
    """
    txt = str(raw_metar or "").strip()
    if not txt:
        return None
    up_tokens = txt.upper().split()
    if "SPECI" in up_tokens[:3] or "COR" in up_tokens[:5]:
        return None

    inferred_icao = str(station_icao or "").strip().upper()
    if not inferred_icao:
        m_ic = _METAR_ICAO_RE.match(txt.upper())
        if m_ic:
            inferred_icao = m_ic.group(1)
    rule_cfg = (
        classify_weather_station_oracle_rule(inferred_icao, unit=unit, rules_text=rules_text)
        if (station_icao or rules_text or (inferred_icao in WUNDERGROUND_INTL_INTEGER_STATIONS and str(unit or "F").upper() == "C"))
        else None
    )
    prefer_body = bool(rule_cfg and rule_cfg.get("prefer_body_integer_c"))
    exact_body_c = bool(rule_cfg and rule_cfg.get("body_integer_exact_c"))

    m_hko = _HKO_SYNTH_RE.match(txt)
    m_rmk = None if (m_hko or prefer_body) else _METAR_T_REMARK_RE.search(txt.upper())
    if m_hko:
        temp_c = float(m_hko.group(1))
        unc_c = 0.05
        has_t_group = True
    elif m_rmk:
        sign = -1.0 if m_rmk.group(1) == "1" else 1.0
        temp_c = sign * (int(m_rmk.group(2)) / 10.0)
        unc_c = 0.05
        has_t_group = True
    else:
        body_part = txt.upper().split("RMK")[0]
        m_body = _METAR_BODY_TEMP_RE.search(body_part)
        if not m_body:
            return None
        t_tok = m_body.group(1)
        temp_c = -float(t_tok[1:]) if t_tok.startswith("M") else float(t_tok)
        unc_c = 0.0 if exact_body_c else 0.55
        has_t_group = False

    min_c = temp_c - unc_c
    max_c = temp_c + unc_c
    f_unc_c = 0.55 if (not has_t_group and unc_c == 0.0 and not prefer_body) else unc_c
    min_f = (temp_c - f_unc_c) * 9.0 / 5.0 + 32.0
    max_f = (temp_c + f_unc_c) * 9.0 / 5.0 + 32.0
    temp_f = temp_c * 9.0 / 5.0 + 32.0

    return {
        "temp_c": round(temp_c, 2),
        "temp_f": round(temp_f, 2),
        "has_t_group": has_t_group,
        "confirmed_floor_int_c": _round_half_away_from_zero(min_c),
        "confirmed_ceil_int_c": _round_half_away_from_zero(max_c),
        "confirmed_floor_int_f": _round_half_away_from_zero(min_f),
        "confirmed_ceil_int_f": _round_half_away_from_zero(max_f),
    }


def resolve_weather_effective_end_ts(sp_w: Any, fallback_ts: float) -> float:
    """
    Gamma populates `endDate: YYYY-MM-DDT12:00:00Z` (or `00:00:00Z`) on unresolved daily weather events even though
    daily station highs/lows settle at `23:59:59` local station time (`ZoneInfo(sp_w.tz_name)`).
    """
    raw_iso = str(getattr(sp_w, "end_date_iso", "") or "").strip()
    obs_d = getattr(sp_w, "obs_date", None)
    try:
        dt_end = datetime.fromisoformat(raw_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        parsed_ts = float(dt_end.timestamp())
    except Exception:
        dt_end = None
        parsed_ts = float(fallback_ts)
    has_resolved = any(
        getattr(b, "outcome_yes_resolved", None) is not None or getattr(b, "resolved_winner", None) is not None
        for b in (getattr(sp_w, "buckets", ()) or ())
    )
    if obs_d is not None and not has_resolved and (
        dt_end is None or (dt_end.date() <= obs_d and dt_end.minute == 0 and dt_end.second == 0 and dt_end.hour in (0, 12))
    ):
        try:
            tz_w = ZoneInfo(str(getattr(sp_w, "tz_name", "UTC") or "UTC"))
        except Exception:
            tz_w = timezone.utc
        next_d = obs_d + timedelta(days=1)
        loc_eod = datetime(next_d.year, next_d.month, next_d.day, 0, 0, 0, tzinfo=tz_w).timestamp() - 1.0
        return float(loc_eod)
    return parsed_ts


def _current_temp_bounds(
    *,
    current_temp_f: Optional[float] = None,
    current_temp_c: Optional[float] = None,
    current_has_t_group: bool = False,
    body_integer_exact_c: bool = False,
) -> Optional[Dict[str, int]]:
    if current_temp_c is not None and math.isfinite(float(current_temp_c)):
        tc = float(current_temp_c)
        unc_c = 0.05 if current_has_t_group else (0.0 if (body_integer_exact_c and abs(tc - round(tc)) < 1e-6) else 0.55)
        min_c, max_c = tc - unc_c, tc + unc_c
        f_unc = 0.05 if current_has_t_group else 0.55
        min_f, max_f = (tc - f_unc) * 9.0 / 5.0 + 32.0, (tc + f_unc) * 9.0 / 5.0 + 32.0
    elif current_temp_f is not None and math.isfinite(float(current_temp_f)):
        tf = float(current_temp_f)
        unc_f = 0.10 if current_has_t_group else 1.00
        min_f, max_f = tf - unc_f, tf + unc_f
        min_c, max_c = (min_f - 32.0) * 5.0 / 9.0, (max_f - 32.0) * 5.0 / 9.0
    else:
        return None
    return {
        "confirmed_floor_int_c": _round_half_away_from_zero(min_c),
        "confirmed_ceil_int_c": _round_half_away_from_zero(max_c),
        "confirmed_floor_int_f": _round_half_away_from_zero(min_f),
        "confirmed_ceil_int_f": _round_half_away_from_zero(max_f),
    }


def compute_running_metar_extrema(
    metar_lines: Sequence[str],
    *,
    unit: str = "F",
    station_icao: str = "",
    rules_text: str = "",
    current_temp_f: Optional[float] = None,
    current_temp_c: Optional[float] = None,
    current_has_t_group: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Aggregate a station's intraday routine `METAR` reports (`SPECI` excluded) plus optional latest
    routine observation (`max(obs_max_f, current_temp_f)` / `min(obs_min_f, current_temp_f)`) with strict
    station-specific ASOS / Wunderground integer rounding safety to bound daily `HIGH` and `LOW`.
    """
    u = str(unit or "F").strip().upper()
    rule_cfg = classify_weather_station_oracle_rule(station_icao, unit=u, rules_text=rules_text)
    parsed = [
        p
        for p in (
            parse_routine_metar_temp_c(line, station_icao=station_icao, unit=u, rules_text=rules_text)
            for line in (metar_lines or [])
        )
        if p is not None
    ]
    cur_b = _current_temp_bounds(
        current_temp_f=current_temp_f,
        current_temp_c=current_temp_c,
        current_has_t_group=current_has_t_group,
        body_integer_exact_c=bool(rule_cfg["body_integer_exact_c"]),
    )
    if cur_b is not None:
        parsed.append({**cur_b, "has_t_group": bool(current_has_t_group)})
    if not parsed:
        return None
    if u == "C":
        floor_hi = max(int(p["confirmed_floor_int_c"]) for p in parsed)
        ceil_hi = max(int(p["confirmed_ceil_int_c"]) for p in parsed)
        floor_lo = min(int(p["confirmed_floor_int_c"]) for p in parsed)
        ceil_lo = min(int(p["confirmed_ceil_int_c"]) for p in parsed)
    else:
        floor_hi = max(int(p["confirmed_floor_int_f"]) for p in parsed)
        ceil_hi = max(int(p["confirmed_ceil_int_f"]) for p in parsed)
        floor_lo = min(int(p["confirmed_floor_int_f"]) for p in parsed)
        ceil_lo = min(int(p["confirmed_ceil_int_f"]) for p in parsed)
    return {
        "unit": u,
        "oracle_regime": rule_cfg["oracle_regime"],
        "routine_obs_count": len(parsed),
        "confirmed_running_high_floor": floor_hi,
        "confirmed_running_high_ceil": ceil_hi,
        "confirmed_running_low_floor": floor_lo,
        "confirmed_running_low_ceil": ceil_lo,
        "all_have_t_group": all(bool(p["has_t_group"]) for p in parsed),
    }


def detect_w_prune1_metar_slate_arb(
    brackets: Sequence[Mapping[str, Any]],
    metar_lines: Sequence[str],
    *,
    station_icao: str,
    unit: str = "F",
    metric: str = "HIGH",
    local_hour_minute: Tuple[int, int] = (15, 0),
    event_meta: Optional[Mapping[str, Any]] = None,
    rules_text: str = "",
    min_net_edge_usd: float = 0.005,
    min_shares: float = 5.0,
    current_temp_f: Optional[float] = None,
    current_temp_c: Optional[float] = None,
    current_has_t_group: bool = False,
) -> List[Dict[str, Any]]:
    """
    `W_PRUNE1` Monotonic METAR Ratchet + `W_SOLAR1` Post-`23:51` Local Lock:
      - `HIGH` metric: any bracket with `high < confirmed_running_high_floor` (`max(obs_max, current_temp)`)
         is mathematically DEAD (`YES == $0.00`, `NO == $1.00`).
      - `LOW` metric: any bracket with `low > confirmed_running_low_ceil` (`min(obs_min, current_temp)`)
         is mathematically DEAD (`YES == $0.00`, `NO == $1.00`).
    """
    m_mode = str(metric or "HIGH").strip().upper()
    if m_mode not in {"HIGH", "LOW"}:
        return []
    oracle_rule = classify_weather_station_oracle_rule(
        station_icao, unit=unit, rules_text=rules_text, event_meta=event_meta
    )
    eff_rules = f"{rules_text} {(event_meta or {}).get('rules_text', '')} {(event_meta or {}).get('description', '')}".strip()
    ext = compute_running_metar_extrema(
        metar_lines,
        unit=unit,
        station_icao=station_icao,
        rules_text=eff_rules,
        current_temp_f=current_temp_f,
        current_temp_c=current_temp_c,
        current_has_t_group=current_has_t_group,
    )
    if ext is None:
        return []
    ok_part, _ = verify_v2_negrisk_other_partition(brackets, event_meta=event_meta)
    if not ok_part and len(brackets) >= 3:
        return []

    floor_hi = int(ext["confirmed_running_high_floor"])
    ceil_hi = int(ext["confirmed_running_high_ceil"])
    floor_lo = int(ext["confirmed_running_low_floor"])
    ceil_lo = int(ext["confirmed_running_low_ceil"])
    loc_h, loc_m = int(local_hour_minute[0]), int(local_hour_minute[1])
    signals: List[Dict[str, Any]] = []

    alive_legs: List[Dict[str, Any]] = []
    alive_complete = True

    for b in brackets:
        b_low = b.get("low")
        b_high = b.get("high")
        high_i = int(b_high) if b_high is not None else 9999
        low_i = int(b_low) if b_low is not None else -9999
        no_ask = _sf(b.get("no_ask"), 0.0)
        no_sz = _sf(b.get("no_ask_size"), 0.0)
        yes_ask = _sf(b.get("yes_ask"), 0.0)
        yes_sz = _sf(b.get("yes_ask_size"), 0.0)
        no_tok = str(b.get("no_token_id") or "").strip()
        yes_tok = str(b.get("yes_token_id") or "").strip()
        cid = str(b.get("condition_id") or "").strip()

        is_dead_bracket = (high_i < floor_hi) if m_mode == "HIGH" else (low_i > ceil_lo)
        if is_dead_bracket:
            if 0.01 <= no_ask <= (1.0 - float(min_net_edge_usd)) and no_sz >= min_shares and no_tok:
                q_no, _, _ = quantize_dynamic_tick_price(no_ask, "BUY", shares=min_shares, mode="taker")
                edge_no = 1.0 - q_no
                if edge_no >= float(min_net_edge_usd):
                    signals.append(
                        {
                            "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                            "station": str(station_icao).upper(),
                            "oracle_regime": oracle_rule["oracle_regime"],
                            "metric": m_mode,
                            "token_id": no_tok,
                            "condition_id": cid,
                            "ask_px": q_no,
                            "p_model": 0.9999,
                            "net_edge_per_share": round(edge_no, 6),
                            "max_fillable_shares": round(no_sz, 2),
                            "confirmed_running_high_floor": floor_hi,
                            "confirmed_running_low_ceil": ceil_lo,
                            "bracket_high": high_i,
                            "bracket_low": low_i,
                        }
                    )
        else:
            if 0.001 <= yes_ask <= 0.995 and yes_sz >= min_shares and yes_tok:
                q_yes, _, _ = quantize_dynamic_tick_price(yes_ask, "BUY", shares=min_shares, mode="taker")
                alive_legs.append(
                    {
                        "token_id": yes_tok,
                        "condition_id": cid,
                        "ask_px": q_yes,
                        "net_cost": q_yes,
                        "ask_size": yes_sz,
                        "low": low_i,
                        "high": high_i,
                    }
                )
            else:
                alive_complete = False

            locked_val = floor_hi if (m_mode == "HIGH" and floor_hi == ceil_hi) else (floor_lo if (m_mode == "LOW" and floor_lo == ceil_lo) else None)
            if bool(oracle_rule["allow_solar_lock"]) and (loc_h == 23 and loc_m >= 52) and locked_val is not None and low_i <= locked_val <= high_i:
                if 0.01 <= yes_ask <= (1.0 - float(min_net_edge_usd)) and yes_sz >= min_shares and yes_tok:
                    q_win, _, _ = quantize_dynamic_tick_price(yes_ask, "BUY", shares=min_shares, mode="taker")
                    if (1.0 - q_win) >= float(min_net_edge_usd):
                        signals.append(
                            {
                                "sleeve": "W_SOLAR1_POST_2351_LOCK",
                                "station": str(station_icao).upper(),
                                "oracle_regime": oracle_rule["oracle_regime"],
                                "metric": m_mode,
                                "token_id": yes_tok,
                                "condition_id": cid,
                                "ask_px": q_win,
                                "p_model": 0.9995,
                                "net_edge_per_share": round(1.0 - q_win, 6),
                                "max_fillable_shares": round(yes_sz, 2),
                                "locked_high": locked_val,
                            }
                        )

    if alive_complete and 1 <= len(alive_legs) < len(brackets):
        sum_alive = sum(x["net_cost"] for x in alive_legs)
        edge_basket = 1.0 - sum_alive
        if edge_basket >= float(min_net_edge_usd):
            exp_w = max((_sf(b.get("expiry_ts"), 0.0) for b in brackets), default=0.0)
            b_rec: Dict[str, Any] = {
                "sleeve": "W_PRUNE1_NR0_BASKET",
                "box_type": "DOMINANCE" if len(alive_legs) == 2 else "MULTI_LEG_BUNDLE",
                "station": str(station_icao).upper(),
                "oracle_regime": oracle_rule["oracle_regime"],
                "metric": m_mode,
                "legs": alive_legs,
                "leg_count": len(alive_legs),
                "pruned_dead_count": len(brackets) - len(alive_legs),
                "confirmed_running_high_floor": floor_hi,
                "confirmed_running_low_ceil": ceil_lo,
                "cost_per_share": round(sum_alive, 6),
                "net_edge_per_share": round(edge_basket, 6),
                "max_fillable_shares": round(min(x["ask_size"] for x in alive_legs), 2),
            }
            if exp_w > 0.0:
                b_rec["expiry_ts"] = exp_w
            signals.append(b_rec)
    return signals


_WALKOVER_FORFEIT_DISPUTE_RE = re.compile(
    r"\b("
    r"walkover|walk-over|forfeit(?:ed|s|ure)?|disqualif(?:ied|ication)|defaulted|"
    r"no[\s-]contest|technical\s+loss|chronobreak|lfmp|last\s+fair\s+market\s+price|"
    r"(?:player|fighter|competitor|team|match|opponent)\s+retire(?:s|d|ment)?|"
    r"retire(?:s|d|ment)\s+(?:mid[\s-]match|during|from\s+the\s+match|before\s+(?:the\s+)?(?:end|completion|final\s+whistle|full\s+time))|"
    r"(?:in[\s-]match|injury|mid[\s-]match)\s+retirement|"
    r"walkover\s+or\s+retirement|retirement\s+or\s+walkover|"
    r"match\s+is\s+abandoned|abandoned\s+match"
    r")\b",
    re.IGNORECASE,
)
_SOCCER_90M_REGULATION_RE = re.compile(
    r"\b("
    r"90[\s-]minutes?|first\s+90\s+minutes|regular\s+play\s+plus\s+stoppage|"
    r"regulation\s+time\s+only|regular\s+time\s+only|"
    r"(?:excludes?|excluding|not\s+include)\s+extra\s+time|"
    r"stoppage\s+time\s*(?:,\s*and\s*)?(?:does\s+not|excludes?)|"
    r"extra\s+time\s+(?:and|or)\s+penalt(?:y|ies)"
    r")\b",
    re.IGNORECASE,
)


def classify_market_rule_dispute_risk(
    market_or_text: Any,
    *,
    extra_text: str = "",
) -> Dict[str, Any]:
    """
    Identify walkover/retirement/forfeit/LFMP and Soccer 90-minute regulation vs extra-time/penalties
    rule clauses that require >= 1800s UMA proposal seasoning on `BOND1` and veto pre-final `MKR_LOCK1` clinches.
    """
    parts: List[str] = []
    if isinstance(market_or_text, Mapping):
        for k in ("question", "title", "display_label", "description", "rules", "rules_text", "slug", "eventSlug"):
            v = market_or_text.get(k)
            if v:
                parts.append(str(v))
        anc = str(market_or_text.get("ancillaryData") or "").strip()
        if anc:
            if anc.startswith("0x") and len(anc) > 4:
                try:
                    parts.append(bytes.fromhex(anc[2:]).decode("utf-8", errors="ignore"))
                except Exception:
                    parts.append(anc)
            else:
                parts.append(anc)
    elif market_or_text:
        parts.append(str(market_or_text))
    if extra_text:
        parts.append(str(extra_text))
    blob = " ".join(parts)

    reasons: List[str] = []
    if _WALKOVER_FORFEIT_DISPUTE_RE.search(blob):
        reasons.append("WALKOVER_FORFEIT_RETIREMENT_RULE")
    if _SOCCER_90M_REGULATION_RE.search(blob):
        reasons.append("SOCCER_90M_REGULATION_EXTRA_TIME_RULE")

    has_risk = bool(reasons)
    return {
        "dispute_risk": has_risk,
        "min_proposal_age_sec": 1800.0 if has_risk else 0.0,
        "veto_pre_final_clinch": has_risk,
        "reasons": reasons,
    }


def passes_uma_bond_dispute_guard(market: Any, ver: Mapping[str, Any]) -> bool:
    """Enforce `proposal_age_sec >= 1800` on `BOND1` when walkover/forfeit or Soccer 90m regulation risk is present."""
    risk = classify_market_rule_dispute_risk(market)
    if not risk["dispute_risk"]:
        return True
    raw_age = ver.get("proposal_age_sec") if isinstance(ver, Mapping) else None
    if raw_age is not None:
        age_sec = _sf(raw_age, 0.0)
    else:
        eff_liv = _sf(ver.get("eff_liveness_sec") if isinstance(ver, Mapping) else None, 7200.0)
        rem_ch = _sf(ver.get("rem_challenge_sec") if isinstance(ver, Mapping) else None, 7200.0)
        age_sec = max(0.0, eff_liv - rem_ch)
    return age_sec >= float(risk["min_proposal_age_sec"])


# ---------------------------------------------------------------------------
# 5. Family IV: Sports (`DC1`, `LP_COMP1`, `HALFTIME`) & Mentions (`MENTION1`)
# ---------------------------------------------------------------------------


def has_us_overtime_inequality(title_a: str, title_b: str, rules_a: str = "", rules_b: str = "") -> bool:
    """
    Guard against pairing a regulation-only market (`excludes overtime` / `regular time`) with a
    full-game moneyline (`includes overtime`) in US leagues or cup ties (`To Advance`).
    """
    txt_a = f"{title_a} {rules_a}".lower()
    txt_b = f"{title_b} {rules_b}".lower()
    joined = f"{txt_a} {txt_b}"
    if "to advance" in txt_a and "to advance" not in txt_b:
        return True
    if "to advance" in txt_b and "to advance" not in txt_a:
        return True
    reg_kw = ("regulation only", "regular time", "excludes overtime", "90 minutes only", "3-way")
    ot_kw = ("includes overtime", "including overtime", "incl. ot", "moneyline")
    a_reg = any(k in txt_a for k in reg_kw)
    b_reg = any(k in txt_b for k in reg_kw)
    a_ot = any(k in txt_a for k in ot_kw)
    b_ot = any(k in txt_b for k in ot_kw)
    if (a_reg and b_ot) or (b_reg and a_ot):
        return True
    if _US_OVERTIME_LEAGUE_RE.search(joined) and ("draw" in joined or "tie" in joined) and (a_ot != b_ot):
        return True
    return False


def _verify_soccer_score_grid_floor(
    leg_predicates: Sequence[Callable[[int, int], bool]],
    expected_min_payout: int = 1,
) -> bool:
    """Exhaustively verify over `(home_goals, away_goals) in {0..8} x {0..8}` that payout >= `expected_min_payout`."""
    for h in range(9):
        for a in range(9):
            s = sum(1 for pred in leg_predicates if pred(h, a))
            if s < expected_min_payout:
                return False
    return True


def detect_dc1_double_chance_1x2_parity(
    quotes: Optional[Mapping[str, Mapping[str, Any]]] = None,
    *,
    one_x2: Optional[Mapping[str, Mapping[str, Any]]] = None,
    double_chance: Optional[Mapping[str, Mapping[str, Any]]] = None,
    rules_text_1x2: str = "",
    rules_text_dc: str = "",
    event_title: str = "",
    is_live_in_play: bool = False,
    is_halftime: bool = False,
    min_net_edge_usd: float = 0.005,
    min_shares: float = 5.0,
) -> List[Dict[str, Any]]:
    """
    `DC1_DOUBLE_CHANCE_1X2_PARITY`:
    90-minute soccer regulation exact partition boxes (`1X + Away`, `X2 + Home`, `12 + Draw`, and
    `$2.00`-payout `1X + X2 + 12`). Blocks live open-play execution (3s Polymarket sports delay) unless
    pre-match or verified `is_halftime == True`.
    """
    if is_live_in_play and not is_halftime:
        return []
    if has_us_overtime_inequality(f"{event_title} {rules_text_1x2}", f"{event_title} {rules_text_dc}"):
        return []

    q_merged: Dict[str, Mapping[str, Any]] = {}
    for src in (quotes, one_x2, double_chance):
        if isinstance(src, Mapping):
            for k, v in src.items():
                if isinstance(v, Mapping):
                    q_merged[str(k).strip().upper()] = v

    pairs = [
        ("1X", "AWAY", lambda h, a: h >= a, lambda h, a: a > h),
        ("X2", "HOME", lambda h, a: a >= h, lambda h, a: h > a),
        ("12", "DRAW", lambda h, a: h != a, lambda h, a: h == a),
    ]
    out: List[Dict[str, Any]] = []
    for k_dc, k_1x2, pred_a, pred_b in pairs:
        qa_map = q_merged.get(k_dc)
        qb_map = q_merged.get(k_1x2)
        if not isinstance(qa_map, Mapping) or not isinstance(qb_map, Mapping):
            continue
        if not _verify_soccer_score_grid_floor([pred_a, pred_b], expected_min_payout=1):
            continue
        pa = _sf(qa_map.get("yes_ask") or qa_map.get("ask"), 0.0)
        pb = _sf(qb_map.get("yes_ask") or qb_map.get("ask"), 0.0)
        sa = _sf(qa_map.get("yes_ask_size") or qa_map.get("ask_size"), 0.0)
        sb = _sf(qb_map.get("yes_ask_size") or qb_map.get("ask_size"), 0.0)
        ta = str(qa_map.get("yes_token_id") or qa_map.get("token_id") or "").strip()
        tb = str(qb_map.get("yes_token_id") or qb_map.get("token_id") or "").strip()
        if not (0.005 <= pa <= 0.99 and 0.005 <= pb <= 0.99 and min(sa, sb) >= min_shares and ta and tb):
            continue
        qpa, _, _ = quantize_dynamic_tick_price(pa, "BUY", shares=min_shares, mode="taker")
        qpb, _, _ = quantize_dynamic_tick_price(pb, "BUY", shares=min_shares, mode="taker")
        cost = qpa + qpb
        edge = 1.0 - cost
        if edge >= float(min_net_edge_usd):
            out.append(
                {
                    "sleeve": "DC1_DOUBLE_CHANCE_1X2_PARITY",
                    "box_type": "DOMINANCE",
                    "pair": f"{k_dc}+{k_1x2}",
                    "identity": f"YES_{k_1x2}_PLUS_YES_{k_dc}",
                    "leg_a": {"token_id": ta, "condition_id": str(qa_map.get("condition_id") or ""), "ask_px": qpa},
                    "leg_b": {"token_id": tb, "condition_id": str(qb_map.get("condition_id") or ""), "ask_px": qpb},
                    "guaranteed_payout_per_share": 1.0,
                    "cost_per_share": round(cost, 6),
                    "net_edge_per_share": round(edge, 6),
                    "max_fillable_shares": round(min(sa, sb), 2),
                }
            )
    return out


def detect_lp_comp1_sports_triangles(
    quotes: Optional[Mapping[str, Mapping[str, Any]]] = None,
    *,
    draw: Optional[Mapping[str, Any]] = None,
    btts: Optional[Mapping[str, Any]] = None,
    under_1_5: Optional[Mapping[str, Any]] = None,
    over_1_5: Optional[Mapping[str, Any]] = None,
    is_live_in_play: bool = False,
    is_halftime: bool = False,
    min_net_edge_usd: float = 0.005,
    min_shares: float = 5.0,
    **_extra_kwargs: Any,
) -> List[Dict[str, Any]]:
    """
    `LP_COMP1_SPORTS_TRIANGLES`:
    Score-grid verified soccer dominance boxes:
      1. `NO(BTTS) + YES(Over 1.5) < $1.00` (2-leg, pays `$2.00` on `(2,0),(0,2),(3,0)...` and `$1.00` everywhere else).
      2. `NO(Draw) + YES(BTTS) + YES(Under 1.5) < $1.00` (3-leg, pays `$1.00` on `(0,0)` and `(k,k)`, `>= $1.00` on all `h != a`).
    """
    if is_live_in_play and not is_halftime:
        return []
    q_map: Dict[str, Mapping[str, Any]] = {}
    if isinstance(quotes, Mapping):
        for k, v in quotes.items():
            if isinstance(v, Mapping):
                q_map[str(k).strip().upper()] = v
    if isinstance(draw, Mapping):
        q_map["DRAW"] = draw
    if isinstance(btts, Mapping):
        q_map["BTTS"] = btts
    if isinstance(under_1_5, Mapping):
        q_map["UNDER_1_5"] = under_1_5
    if isinstance(over_1_5, Mapping):
        q_map["OVER_1_5"] = over_1_5

    out: List[Dict[str, Any]] = []

    btts_m = q_map.get("BTTS")
    o15 = q_map.get("OVER_1_5")
    if isinstance(btts_m, Mapping) and isinstance(o15, Mapping):
        if _verify_soccer_score_grid_floor(
            [lambda h, a: not (h >= 1 and a >= 1), lambda h, a: (h + a) >= 2],
            expected_min_payout=1,
        ):
            pa = _sf(btts_m.get("no_ask"), 0.0)
            pb = _sf(o15.get("yes_ask"), 0.0)
            sa = _sf(btts_m.get("no_ask_size"), 0.0)
            sb = _sf(o15.get("yes_ask_size"), 0.0)
            ta = str(btts_m.get("no_token_id") or "").strip()
            tb = str(o15.get("yes_token_id") or "").strip()
            if 0.005 <= pa <= 0.99 and 0.005 <= pb <= 0.99 and min(sa, sb) >= min_shares and ta and tb:
                qpa, _, _ = quantize_dynamic_tick_price(pa, "BUY", shares=min_shares, mode="taker")
                qpb, _, _ = quantize_dynamic_tick_price(pb, "BUY", shares=min_shares, mode="taker")
                edge = 1.0 - (qpa + qpb)
                if edge >= float(min_net_edge_usd):
                    exp_2 = max(_sf(btts_m.get("expiry_ts"), 0.0), _sf(o15.get("expiry_ts"), 0.0))
                    rec_2: Dict[str, Any] = {
                        "sleeve": "LP_COMP1_SPORTS_TRIANGLES",
                        "box_type": "DOMINANCE",
                        "pattern": "NO_BTTS_PLUS_YES_OVER_1_5",
                        "triangle_id": "NO_BTTS_PLUS_YES_OVER_1_5",
                        "leg_a": {"token_id": ta, "role": "NO_BTTS", "condition_id": str(btts_m.get("condition_id") or ""), "market_id": str(btts_m.get("market_id") or ""), "ask_px": qpa},
                        "leg_b": {"token_id": tb, "role": "YES_OVER_1_5", "condition_id": str(o15.get("condition_id") or ""), "market_id": str(o15.get("market_id") or ""), "ask_px": qpb},
                        "legs": [
                            {"token_id": ta, "role": "NO_BTTS", "condition_id": str(btts_m.get("condition_id") or ""), "market_id": str(btts_m.get("market_id") or ""), "ask_px": qpa},
                            {"token_id": tb, "role": "YES_OVER_1_5", "condition_id": str(o15.get("condition_id") or ""), "market_id": str(o15.get("market_id") or ""), "ask_px": qpb},
                        ],
                        "guaranteed_payout_per_share": 1.0,
                        "cost_per_share": round(qpa + qpb, 6),
                        "net_edge_per_share": round(edge, 6),
                        "max_fillable_shares": round(min(sa, sb), 2),
                    }
                    if exp_2 > 0.0:
                        rec_2["expiry_ts"] = exp_2
                    out.append(rec_2)

    draw_m = q_map.get("DRAW")
    u15 = q_map.get("UNDER_1_5")
    if isinstance(draw_m, Mapping) and isinstance(btts_m, Mapping) and isinstance(u15, Mapping):
        if _verify_soccer_score_grid_floor(
            [
                lambda h, a: h != a,
                lambda h, a: (h >= 1 and a >= 1),
                lambda h, a: (h + a) <= 1,
            ],
            expected_min_payout=1,
        ):
            p1 = _sf(draw_m.get("no_ask"), 0.0)
            p2 = _sf(btts_m.get("yes_ask"), 0.0)
            p3 = _sf(u15.get("yes_ask"), 0.0)
            s_min = min(_sf(draw_m.get("no_ask_size"), 0.0), _sf(btts_m.get("yes_ask_size"), 0.0), _sf(u15.get("yes_ask_size"), 0.0))
            t1, t2, t3 = (
                str(draw_m.get("no_token_id") or "").strip(),
                str(btts_m.get("yes_token_id") or "").strip(),
                str(u15.get("yes_token_id") or "").strip(),
            )
            if all(0.002 <= p <= 0.98 for p in (p1, p2, p3)) and s_min >= min_shares and t1 and t2 and t3:
                qp1, _, _ = quantize_dynamic_tick_price(p1, "BUY", shares=min_shares, mode="taker")
                qp2, _, _ = quantize_dynamic_tick_price(p2, "BUY", shares=min_shares, mode="taker")
                qp3, _, _ = quantize_dynamic_tick_price(p3, "BUY", shares=min_shares, mode="taker")
                cost3 = qp1 + qp2 + qp3
                edge3 = 1.0 - cost3
                if edge3 >= float(min_net_edge_usd):
                    exp_3 = max(_sf(draw_m.get("expiry_ts"), 0.0), _sf(btts_m.get("expiry_ts"), 0.0), _sf(u15.get("expiry_ts"), 0.0))
                    rec_3: Dict[str, Any] = {
                        "sleeve": "LP_COMP1_SPORTS_TRIANGLES",
                        "box_type": "MULTI_LEG_BUNDLE",
                        "pattern": "NO_DRAW_YES_BTTS_YES_UNDER_1_5",
                        "triangle_id": "NO_DRAW_YES_BTTS_YES_UNDER_1_5",
                        "legs": [
                            {"token_id": t1, "condition_id": str(draw_m.get("condition_id") or ""), "market_id": str(draw_m.get("market_id") or ""), "ask_px": qp1, "net_cost": qp1, "ask_size": s_min, "neg_risk": bool(draw_m.get("neg_risk", False))},
                            {"token_id": t2, "condition_id": str(btts_m.get("condition_id") or ""), "market_id": str(btts_m.get("market_id") or ""), "ask_px": qp2, "net_cost": qp2, "ask_size": s_min, "neg_risk": bool(btts_m.get("neg_risk", False))},
                            {"token_id": t3, "condition_id": str(u15.get("condition_id") or ""), "market_id": str(u15.get("market_id") or ""), "ask_px": qp3, "net_cost": qp3, "ask_size": s_min, "neg_risk": bool(u15.get("neg_risk", False))},
                        ],
                        "leg_count": 3,
                        "guaranteed_payout_per_share": 1.0,
                        "cost_per_share": round(cost3, 6),
                        "net_edge_per_share": round(edge3, 6),
                        "max_fillable_shares": round(s_min, 2),
                    }
                    if exp_3 > 0.0:
                        rec_3["expiry_ts"] = exp_3
                    out.append(rec_3)
    return out


def detect_halftime_freeze_offset_box(
    *,
    is_halftime: bool,
    halftime_total_goals: int,
    fulltime_line: float,
    second_half_line: float,
    ft_market: Mapping[str, Any],
    h2_market: Mapping[str, Any],
    includes_overtime_ft: bool = False,
    includes_overtime_h2: bool = False,
    min_net_edge_usd: float = 0.005,
    min_shares: float = 5.0,
) -> Optional[Dict[str, Any]]:
    """
    `HALFTIME_FREEZE_OFFSET_BOX`:
    While play is frozen at halftime (`is_halftime == True`, zero live-ball 3s sniper risk),
    `FT_Goals = g_HT + H2_Goals`. Whenever `fulltime_line - halftime_total_goals >= second_half_line`
    (exact equality `FT Over (g_HT + L)` == `2H Over L`, or strict dominance), checks exact cross-market box!
    """
    if not is_halftime or (includes_overtime_ft != includes_overtime_h2):
        return None
    shifted_ft_need = float(fulltime_line) - float(halftime_total_goals)
    # `H2_Goals > second_half_line` implies `FT_Goals > fulltime_line` iff `second_half_line >= shifted_ft_need`
    # Prefer exact shift `abs(shifted_ft_need - second_half_line) < 1e-6` (both directions valid!)
    candidates: List[Tuple[str, float, str, float, float]] = []
    sz_ft_y = _sf(ft_market.get("yes_ask_size"), 5.0)
    sz_ft_n = _sf(ft_market.get("no_ask_size"), 5.0)
    sz_h2_y = _sf(h2_market.get("yes_ask_size"), 5.0)
    sz_h2_n = _sf(h2_market.get("no_ask_size"), 5.0)

    if shifted_ft_need <= float(second_half_line) + 1e-6:
        # H2 Over -> FT Over, so YES(FT Over) + NO(H2 Over) >= $1.00
        candidates.append(
            (
                str(ft_market.get("yes_token_id") or ""),
                _sf(ft_market.get("yes_ask"), 0.0),
                str(h2_market.get("no_token_id") or ""),
                _sf(h2_market.get("no_ask"), 0.0),
                min(sz_ft_y, sz_h2_n),
            )
        )
    if float(second_half_line) <= shifted_ft_need + 1e-6:
        # FT Over -> H2 Over, so NO(FT Over) + YES(H2 Over) >= $1.00
        candidates.append(
            (
                str(ft_market.get("no_token_id") or ""),
                _sf(ft_market.get("no_ask"), 0.0),
                str(h2_market.get("yes_token_id") or ""),
                _sf(h2_market.get("yes_ask"), 0.0),
                min(sz_ft_n, sz_h2_y),
            )
        )

    best: Optional[Dict[str, Any]] = None
    for ta, pa, tb, pb, sh in candidates:
        if not (ta and tb and sh >= min_shares and 0.005 <= pa <= 0.99 and 0.005 <= pb <= 0.99):
            continue
        qpa, _, _ = quantize_dynamic_tick_price(pa, "BUY", shares=min_shares, mode="taker")
        qpb, _, _ = quantize_dynamic_tick_price(pb, "BUY", shares=min_shares, mode="taker")
        edge = 1.0 - (qpa + qpb)
        if edge >= float(min_net_edge_usd) and (best is None or edge > best["net_edge_per_share"]):
            best = {
                "sleeve": "HALFTIME_FREEZE_OFFSET_BOX",
                "box_type": "DOMINANCE",
                "leg_a": {"token_id": ta, "condition_id": str(ft_market.get("condition_id") or ""), "ask_px": qpa},
                "leg_b": {"token_id": tb, "condition_id": str(h2_market.get("condition_id") or ""), "ask_px": qpb},
                "cost_per_share": round(qpa + qpb, 6),
                "net_edge_per_share": round(edge, 6),
                "max_fillable_shares": round(sh, 2),
            }
    return best


def detect_mention1_cumulative_ladder_box(
    rungs: Sequence[Mapping[str, Any]],
    *,
    min_net_edge_usd: float = 0.005,
    min_shares: float = 5.0,
) -> List[Dict[str, Any]]:
    """
    `MENTION1_CUMULATIVE_LADDER_BOX`:
    Speech/transcript mention count ladders (`Count >= k` vs `Count >= m` for `1 <= k < m` on exact
    same event & speaker/word): since `Count >= m => Count >= k`, `YES(Count >= k) + NO(Count >= m) >= $1.00`
    everywhere (and `$2.00` when `k <= Count < m`)!
    """
    ordered = sorted(
        [r for r in (rungs or []) if int(_sf(r.get("min_count"), 0)) >= 1],
        key=lambda r: int(_sf(r.get("min_count"), 0)),
    )
    out: List[Dict[str, Any]] = []
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            lo, hi = ordered[i], ordered[j]
            k_lo = int(_sf(lo.get("min_count"), 0))
            k_hi = int(_sf(hi.get("min_count"), 0))
            if k_hi <= k_lo or str(lo.get("term") or "").lower() != str(hi.get("term") or "").lower():
                continue
            ta = str(lo.get("yes_token_id") or "").strip()
            tb = str(hi.get("no_token_id") or "").strip()
            pa = _sf(lo.get("yes_ask"), 0.0)
            pb = _sf(hi.get("no_ask"), 0.0)
            sh = min(_sf(lo.get("yes_ask_size"), 5.0), _sf(hi.get("no_ask_size"), 5.0))
            if not (ta and tb and sh >= min_shares and 0.005 <= pa <= 0.99 and 0.005 <= pb <= 0.99):
                continue
            qpa, _, _ = quantize_dynamic_tick_price(pa, "BUY", shares=min_shares, mode="taker")
            qpb, _, _ = quantize_dynamic_tick_price(pb, "BUY", shares=min_shares, mode="taker")
            edge = 1.0 - (qpa + qpb)
            if edge >= float(min_net_edge_usd):
                out.append(
                    {
                        "sleeve": "MENTION1_CUMULATIVE_LADDER_BOX",
                        "box_type": "DOMINANCE",
                        "term": str(lo.get("term") or ""),
                        "count_low": k_lo,
                        "count_high": k_hi,
                        "leg_a": {"token_id": ta, "condition_id": str(lo.get("condition_id") or ""), "ask_px": qpa},
                        "leg_b": {"token_id": tb, "condition_id": str(hi.get("condition_id") or ""), "ask_px": qpb},
                        "cost_per_share": round(qpa + qpb, 6),
                        "net_edge_per_share": round(edge, 6),
                        "max_fillable_shares": round(sh, 2),
                    }
                )
    out.sort(key=lambda b: b["net_edge_per_share"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# 6. Family V & VI: Full-Universe `C1` + `CTF_OVERROUND_MINT_SELL`, `UMA_READY1`, `CompleteSetRewardShield`
# ---------------------------------------------------------------------------


def scan_full_universe_c1_and_ctf_overround(
    binary_markets: Sequence[Mapping[str, Any]],
    *,
    min_underround_edge: float = 0.004,
    min_overround_edge: float = 0.005,
    min_shares: float = 5.0,
    gas_usd_total: float = 0.01,
) -> List[Dict[str, Any]]:
    """
    Full-universe binary complete-set scanner (`enableOrderBook == True`):
      1. `C1_BINARY_COMPLETE_SET`: `ask(YES) + ask(NO) + fees < 1.0 - min_underround_edge` -> FOK buy both -> `mergePositions` -> `$1.00`!
      2. `CTF_OVERROUND_MINT_SELL`: `bid(YES) + bid(NO) - fees > 1.0 + min_overround_edge` -> `splitPosition($1)` -> FOK sell both -> `> $1.005`!
    """
    gas_sh = float(gas_usd_total) / max(float(min_shares), 5.0)
    results: List[Dict[str, Any]] = []

    for m in binary_markets or []:
        if m.get("enableOrderBook") is False or bool(m.get("negRisk") or m.get("neg_risk")):
            continue
        cid = str(m.get("condition_id") or m.get("conditionId") or "").strip()
        yes_tok = str(m.get("yes_token_id") or m.get("token_a") or "").strip()
        no_tok = str(m.get("no_token_id") or m.get("token_b") or "").strip()
        if not (cid and yes_tok and no_tok):
            continue
        f_r = _sf(m.get("fee_rate"), 0.0)
        f_e = _sf(m.get("fee_exponent"), 1.0)

        ya = _sf(m.get("yes_ask"), 0.0)
        na = _sf(m.get("no_ask"), 0.0)
        ysz_a = _sf(m.get("yes_ask_size"), 0.0)
        nsz_a = _sf(m.get("no_ask_size"), 0.0)
        if 0.002 <= ya <= 0.995 and 0.002 <= na <= 0.995 and min(ysz_a, nsz_a) >= min_shares:
            qya, _, _ = quantize_dynamic_tick_price(ya, "BUY", shares=min_shares, mode="taker")
            qna, _, _ = quantize_dynamic_tick_price(na, "BUY", shares=min_shares, mode="taker")
            c_under = (
                qya
                + compute_exact_taker_fee_per_share(qya, f_r, f_e)
                + qna
                + compute_exact_taker_fee_per_share(qna, f_r, f_e)
                + gas_sh
            )
            edge_u = 1.0 - c_under
            if edge_u >= float(min_underround_edge):
                c1_rec: Dict[str, Any] = {
                    "sleeve": "C1_BINARY_COMPLETE_SET",
                    "box_type": "COMPLETE_SET",
                    "condition_id": cid,
                    "market_id": str(m.get("market_id") or m.get("id") or cid),
                    "yes_token_id": yes_tok,
                    "no_token_id": no_tok,
                    "yes_ask": qya,
                    "no_ask": qna,
                    "fee_rate": f_r,
                    "cost_per_share": round(c_under, 6),
                    "net_edge_per_share": round(edge_u, 6),
                    "max_fillable_shares": round(min(ysz_a, nsz_a), 2),
                }
                if _sf(m.get("expiry_ts"), 0.0) > 0.0:
                    c1_rec["expiry_ts"] = _sf(m.get("expiry_ts"), 0.0)
                results.append(c1_rec)

        yb = _sf(m.get("yes_bid"), 0.0)
        nb = _sf(m.get("no_bid"), 0.0)
        ysz_b = _sf(m.get("yes_bid_size"), 0.0)
        nsz_b = _sf(m.get("no_bid_size"), 0.0)
        if 0.002 <= yb <= 0.995 and 0.002 <= nb <= 0.995 and min(ysz_b, nsz_b) >= min_shares * 1.25:
            qyb, _, _ = quantize_dynamic_tick_price(yb, "SELL", shares=min_shares, mode="taker")
            qnb, _, _ = quantize_dynamic_tick_price(nb, "SELL", shares=min_shares, mode="taker")
            rev_over = (
                (qyb - compute_exact_taker_fee_per_share(qyb, f_r, f_e))
                + (qnb - compute_exact_taker_fee_per_share(qnb, f_r, f_e))
                - gas_sh
            )
            edge_o = rev_over - 1.0
            if edge_o >= float(min_overround_edge):
                ov_rec: Dict[str, Any] = {
                    "sleeve": "CTF_OVERROUND_MINT_SELL",
                    "box_type": "CTF_OVERROUND",
                    "condition_id": cid,
                    "market_id": str(m.get("market_id") or m.get("id") or cid),
                    "yes_token_id": yes_tok,
                    "no_token_id": no_tok,
                    "yes_bid": qyb,
                    "no_bid": qnb,
                    "fee_rate": f_r,
                    "net_proceeds_per_share": round(rev_over, 6),
                    "net_revenue_per_share": round(rev_over, 6),
                    "net_edge_per_share": round(edge_o, 6),
                    "max_fillable_shares": round(min(ysz_b, nsz_b) / 1.25, 2),
                }
                if _sf(m.get("expiry_ts"), 0.0) > 0.0:
                    ov_rec["expiry_ts"] = _sf(m.get("expiry_ts"), 0.0)
                results.append(ov_rec)

    results.sort(key=lambda r: r["net_edge_per_share"], reverse=True)
    return results


def score_uma_ready1_liveness_priority(
    *,
    ask_price: float,
    remaining_liveness_sec: float,
    disputed: bool = False,
    proposal_bond_posted: bool = True,
    fee_per_share: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """
    `UMA_READY1_LIVENESS_PRIORITY`:
    Scores undisputed UMA Optimistic Oracle proposals inside the final `3m-25m` (`180s <= rem <= 1500s`)
    challenge window so `$61` seed capital compounds in `< 25 minutes` instead of `2h+` lockups.
    """
    rem = float(remaining_liveness_sec)
    if disputed or not proposal_bond_posted or not (180.0 <= rem <= 1500.0):
        return None
    q_ask, _, _ = quantize_dynamic_tick_price(float(ask_price), "BUY", shares=5.0, mode="taker")
    net_edge = 1.0 - (q_ask + float(fee_per_share))
    if net_edge < 0.002:
        return None
    edge_bps_per_hour = (net_edge / max(q_ask, 0.5)) * 10000.0 * (3600.0 / max(rem, 180.0))
    return {
        "sleeve": "UMA_READY1_LIVENESS_PRIORITY",
        "ask_px": q_ask,
        "remaining_liveness_sec": round(rem, 1),
        "net_edge_per_share": round(net_edge, 6),
        "velocity_bps_per_hour": round(edge_bps_per_hour, 2),
        "priority_boost": 3.0 if rem <= 900.0 else 2.0,
    }


class CompleteSetRewardShield:
    """
    `COMPLETE_SET_REWARD_SHIELD`:
    Polymarket CLOB Liquidity Rewards penalize one-sided makers by `c = 3.0` (`Q_min = max(min(Q_1, Q_2), max(Q_1/c, Q_2/c))`)
    on midpoints `p in [0.10, 0.90]`. Posting symmetric complete-set bids (`YES` bid + `NO` bid with
    `bid_yes + bid_no <= 0.994`) or symmetric asks on pre-split complete sets unlocks the full `3x` `Q_min`
    reward multiplier while guaranteeing zero net directional risk if both fill!
    """

    def __init__(self, scaling_c: float = 3.0) -> None:
        self.scaling_c = max(1.0, float(scaling_c))

    @staticmethod
    def quadratic_spread_score(spread_from_mid: float, max_incentive_spread: float, size: float) -> float:
        v = float(max_incentive_spread)
        s = abs(float(spread_from_mid))
        if v <= 0.0 or s >= v or float(size) <= 0.0:
            return 0.0
        return (((v - s) / v) ** 2) * float(size)

    def compute_q_min(
        self,
        *,
        mid_yes: float,
        max_incentive_spread: float,
        q_one: float,
        q_two: float,
    ) -> float:
        m = float(mid_yes)
        if 0.10 <= m <= 0.90:
            return max(min(q_one, q_two), max(q_one / self.scaling_c, q_two / self.scaling_c))
        return min(q_one, q_two)

    def build_hedged_reward_pair(
        self,
        *,
        yes_token_id: str,
        no_token_id: str,
        mid_yes: float,
        max_incentive_spread: float,
        min_incentive_size: float,
        shares: float,
        max_pair_bid_sum: float = 0.992,
    ) -> Optional[Dict[str, Any]]:
        sh = float(shares)
        if sh < max(5.0, float(min_incentive_size)) or float(max_incentive_spread) <= 0.004:
            return None
        m = min(0.90, max(0.10, float(mid_yes)))
        target_offset = min(float(max_incentive_spread) * 0.45, max(0.005, (1.0 - float(max_pair_bid_sum)) * 0.5))
        b_yes, _, ok_y = quantize_dynamic_tick_price(m - target_offset, "BUY", shares=sh, mode="maker")
        b_no, _, ok_n = quantize_dynamic_tick_price((1.0 - m) - target_offset, "BUY", shares=sh, mode="maker")
        if not (ok_y and ok_n) or (b_yes + b_no) > float(max_pair_bid_sum) + 1e-9:
            return None
        q1 = self.quadratic_spread_score(m - b_yes, max_incentive_spread, sh)
        q2 = self.quadratic_spread_score((1.0 - m) - b_no, max_incentive_spread, sh)
        q_hedged = self.compute_q_min(mid_yes=m, max_incentive_spread=max_incentive_spread, q_one=q1, q_two=q2)
        q_single = self.compute_q_min(mid_yes=m, max_incentive_spread=max_incentive_spread, q_one=q1, q_two=0.0)
        if q_hedged <= 0.0:
            return None
        return {
            "sleeve": "MKR_REWARD_COMPLETE_SET_SHIELD",
            "yes_token_id": str(yes_token_id),
            "no_token_id": str(no_token_id),
            "yes_bid_px": b_yes,
            "no_bid_px": b_no,
            "shares": round(sh, 2),
            "pair_bid_sum": round(b_yes + b_no, 4),
            "q_min_hedged": round(q_hedged, 4),
            "q_min_multiplier_vs_single_sided": round(q_hedged / max(q_single, 1e-9), 2),
            "reward_multiplier_vs_single_sided": round(q_hedged / max(q_single, 1e-9), 2),
        }


# ---------------------------------------------------------------------------
# 7. Atomic Execution Helpers (`CTF_OVERROUND_MINT_SELL` & Multi-Leg All-YES / Convert Bundle)
# ---------------------------------------------------------------------------


async def execute_binary_ctf_overround_mint_sell(
    executor: Any,
    *,
    condition_id: str,
    yes_token_id: str,
    no_token_id: str,
    yes_min_bid: float,
    no_min_bid: float,
    shares: float,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    harvester: Any = None,
    expiry_ts: float = 0.0,
    cand_asset: str = "CTFOVR",
) -> Dict[str, Any]:
    """
    Execute `CTF_OVERROUND_MINT_SELL`:
      1. Mint `shares` complete sets (`splitPosition` `$1.00 * shares` -> `YES` + `NO`).
      2. Atomically sweep both resting `YES` and `NO` bids (`execute_atomic_box_overround_unwind`).
      3. If both legs reject, immediately call `attempt_onchain_complete_set_merge` (`$1.00 * shares` back to pUSD).
         If one leg filled (`partial_leg_unwind`), unwind the remaining unsold leg via FOK sell and register any
         residual shares in `harvester.active_positions` so ZERO ERC-1155 inventory is ever orphaned!
    """
    sh = round(float(shares), 2)
    if sh < 5.0:
        return {"success": False, "reason": "SHARES_BELOW_5_MIN"}
    if hasattr(executor, "split_collateral_to_complete_set"):
        sp = await asyncio.to_thread(executor.split_collateral_to_complete_set, condition_id, sh, neg_risk=False)
    elif attempt_onchain_split_position is not None:
        sp = await asyncio.to_thread(
            attempt_onchain_split_position,
            executor,
            condition_id,
            sh,
            neg_risk=False,
            up_token_id=yes_token_id,
            down_token_id=no_token_id,
        )
    else:
        sp = {"success": False, "reason": "NO_SPLIT_HANDLER"}
    if not (sp or {}).get("success"):
        return {"success": False, "reason": f"SPLIT_FAILED:{(sp or {}).get('reason') or (sp or {}).get('error')}"}

    if hasattr(executor, "execute_atomic_box_overround_unwind"):
        u_res = await asyncio.to_thread(
            executor.execute_atomic_box_overround_unwind,
            f"CTFOVR_{condition_id[:10]}",
            yes_token_id,
            yes_min_bid,
            no_token_id,
            no_min_bid,
            sh,
            False,
            False,
            float(fee_rate),
            float(fee_exponent),
            float(fee_rate),
            float(fee_exponent),
        )
    elif hasattr(executor, "place_fok_order"):
        la = await asyncio.to_thread(executor.place_fok_order, yes_token_id, "SELL", sh, yes_min_bid)
        if (la or {}).get("success"):
            lb = await asyncio.to_thread(executor.place_fok_order, no_token_id, "SELL", sh, no_min_bid)
            if (lb or {}).get("success"):
                u_res = {"success": True, "leg_a": la, "leg_b": lb}
            else:
                u_res = {"success": False, "partial_leg_unwind": True, "leg_a": la, "leg_b": lb or {}}
        else:
            u_res = {"success": False}
    else:
        u_res = {"success": False}

    if (u_res or {}).get("success"):
        la, lb = u_res["leg_a"], u_res["leg_b"]
        fee_tot = round(float(la.get("fee_usd") or 0.0) + float(lb.get("fee_usd") or 0.0), 4)
        cash_a = float(la.get("taking_amount") or 0.0) - float(la.get("fee_usd") or 0.0)
        cash_b = float(lb.get("taking_amount") or 0.0) - float(lb.get("fee_usd") or 0.0)
        realized = round(cash_a + cash_b, 4)
        return {
            "success": True,
            "shares": sh,
            "cost_usd": sh,
            "fee_usd": fee_tot,
            "realized_cash_usd": realized,
            "net_pnl_usd": round(realized - sh, 4),
            "split_tx_hash": sp.get("tx_hash"),
        }

    if (u_res or {}).get("partial_leg_unwind"):
        la_d = (u_res or {}).get("leg_a") or {}
        a_sold = bool(la_d.get("filled") or la_d.get("success"))
        sold_d = la_d if a_sold else ((u_res or {}).get("leg_b") or {})
        unsold_tok = no_token_id if a_sold else yes_token_id
        unsold_side = "NO" if a_sold else "YES"
        sold_cash = max(0.0, float(sold_d.get("taking_amount") or 0.0) - float(sold_d.get("fee_usd") or 0.0))
        unw_cash = 0.0
        unw_ok = False
        if hasattr(executor, "execute_unwind_order"):
            try:
                uw = await asyncio.to_thread(
                    executor.execute_unwind_order, unsold_tok, size=sh, side="SELL", min_price=0.02, neg_risk=False
                )
            except TypeError:
                uw = await asyncio.to_thread(executor.execute_unwind_order, f"UNW_OVR_{condition_id[:8]}", unsold_tok, sh, 0.02)
            unw_ok = bool(getattr(uw, "success", False) or (isinstance(uw, Mapping) and uw.get("success")))
            unw_cash = float(
                getattr(uw, "notional_usd", 0.0)
                or (uw.get("taking_amount", 0.0) if isinstance(uw, Mapping) else 0.0)
                or 0.0
            )
        elif hasattr(executor, "place_fok_order"):
            uw = await asyncio.to_thread(executor.place_fok_order, unsold_tok, "SELL", sh, 0.02)
            unw_ok = bool((uw or {}).get("success"))
            unw_cash = float((uw or {}).get("taking_amount") or 0.0) - float((uw or {}).get("fee_usd") or 0.0)
        if not unw_ok and harvester is not None:
            rem_cost = round(max(0.01, sh - sold_cash), 4)
            rid = f"CTFOVR_RESID_{condition_id[:8]}_{int(time.time())}"
            now_r = time.time()
            exp_r = float(expiry_ts or (now_r + 7200.0))
            if hasattr(harvester, "_make_single_leg_lock_pos"):
                rpos = harvester._make_single_leg_lock_pos(
                    rid, "CTF_OVERROUND_RESIDUAL", "CTF_OVERROUND_MINT_SELL", cand_asset, "resid",
                    condition_id, condition_id, unsold_tok, unsold_side, False, sh, rem_cost, 0.0,
                    float(fee_rate), float(fee_exponent), "crypto_fees_v2", exp_r, now_r, 0.0, None, True, unk=False,
                )
            else:
                rpos = {
                    "trade_id": rid, "token_id": unsold_tok, "condition_id": condition_id, "market_id": condition_id,
                    "target_token": unsold_side, "asset": cand_asset, "sleeve": "CTF_OVERROUND_MINT_SELL",
                    "shares": sh, "entry_shares": sh, "remaining_shares": sh, "notional_usd": rem_cost,
                    "entry_ts": now_r, "candle_expiry_ts": exp_r, "status": "POSITION_CONFIRMED", "neg_risk": False,
                }
            harvester.active_positions[rid] = rpos
        return {
            "success": False,
            "reason": "OVERROUND_PARTIAL_LEG_UNWOUND",
            "partial_recovered_cash_usd": round(sold_cash + unw_cash, 4),
            "residual_registered": bool(not unw_ok and harvester is not None),
        }

    # Immediate on-chain `mergePositions` rollback on unsold pair
    if hasattr(executor, "attempt_onchain_complete_set_merge"):
        m_res = await asyncio.to_thread(
            executor.attempt_onchain_complete_set_merge,
            condition_id,
            min_pairs=max(1.0, sh - 0.05),
            max_pairs=sh,
            neg_risk=False,
        )
        merged_ok = bool(isinstance(m_res, tuple) and m_res[0])
    elif hasattr(executor, "merge_complete_set_positions"):
        m_res = await asyncio.to_thread(executor.merge_complete_set_positions, condition_id, sh, neg_risk=False)
        merged_ok = bool(isinstance(m_res, Mapping) and (m_res.get("success") or m_res.get("merged")))
    elif hasattr(executor, "merge_complete_set_to_collateral"):
        m_res = await asyncio.to_thread(executor.merge_complete_set_to_collateral, condition_id, sh, neg_risk=False)
        merged_ok = bool(isinstance(m_res, Mapping) and (m_res.get("success") or m_res.get("merged")))
    else:
        merged_ok = False
    return {
        "success": False,
        "reason": "OVERROUND_SWEEP_REJECTED_MERGED_BACK",
        "merged_back": merged_ok,
    }


def _execute_multi_leg_bundle_sync(
    executor: Any,
    legs: Sequence[Mapping[str, Any]],
    *,
    shares: float,
    bundle_id: str = "BUNDLE",
    neg_risk: bool = True,
    harvester: Any = None,
    exp_ts: float = 0.0,
    sleeve_src: str = "NR0_ALL_YES_COMPLETE_SET",
    cand_asset: str = "NR0",
) -> Dict[str, Any]:
    sh = round(float(shares), 2)
    if sh < 5.0 or not (3 <= len(legs) <= 12):
        return {"success": False, "reason": "INVALID_MULTI_LEG_SPEC"}
    ordered = sorted(legs, key=lambda r: _sf(r.get("ask_size"), 9999.0))
    filled: List[Tuple[Mapping[str, Any], Dict[str, Any]]] = []
    total_spent = 0.0

    for idx, leg in enumerate(ordered):
        tok = str(leg.get("token_id") or "").strip()
        leg_nr = bool(leg["neg_risk"]) if "neg_risk" in leg and leg.get("neg_risk") is not None else bool(neg_risk)
        leg_fr = _sf(leg.get("fee_rate"), 0.0)
        leg_fe = _sf(leg.get("fee_exponent"), 1.0)
        px, _, _ = quantize_dynamic_tick_price(_sf(leg.get("ask_px"), 0.0), "BUY", shares=sh, mode="taker")
        fee_ps = compute_exact_taker_fee_per_share(px, leg_fr, leg_fe)
        gross_sh = round(sh * (px + fee_ps) / max(px, 0.01), 4) if (leg_fr > 0.0 and bool(leg.get("fee_in_shares", False))) else sh
        if hasattr(executor, "execute_fok_order"):
            raw_res = executor.execute_fok_order(tok, px, gross_sh * px, "BUY", neg_risk=leg_nr)
            ok = bool(isinstance(raw_res, Mapping) and raw_res.get("success"))
            res = dict(raw_res) if isinstance(raw_res, Mapping) else {"success": ok}
        elif hasattr(executor, "place_fok_order"):
            raw_res = executor.place_fok_order(tok, "BUY", gross_sh, px, neg_risk=leg_nr)
            ok = bool(isinstance(raw_res, Mapping) and raw_res.get("success"))
            res = dict(raw_res) if isinstance(raw_res, Mapping) else {"success": ok}
        elif hasattr(executor, "execute_snipe_order"):
            o_res = executor.execute_snipe_order(
                trade_id=f"{bundle_id}_L{idx}",
                token_id=tok,
                target_token=str(leg.get("side") or leg.get("label") or "YES").upper(),
                notional_usd=round(gross_sh * px, 4),
                target_price=px,
                side="BUY",
                depth_hurdle=1.02,
                market_id=str(leg.get("market_id") or ""),
                condition_id=str(leg.get("condition_id") or leg.get("market_id") or ""),
                market_fee_rate=leg_fr,
                market_fee_exponent=leg_fe,
                max_price_ceiling=px,
                max_ticket_cap=max(40.0, round(gross_sh * px + 2.0, 2)),
                min_price_floor=0.01,
                neg_risk=leg_nr,
                max_book_buffer=0.0,
            )
            ok = bool(getattr(o_res, "success", False))
            unk_leg = bool(getattr(o_res, "outcome_unknown", False))
            res = {
                "success": ok,
                "outcome_unknown": unk_leg,
                "making_amount": float(getattr(o_res, "notional_usd", 0.0) or (gross_sh * px)),
                "fee_usd": float(getattr(o_res, "fee_usd", 0.0) or 0.0),
                "size": float(getattr(o_res, "size", 0.0) or sh),
                "price": float(getattr(o_res, "price", 0.0) or px),
                "order_id": getattr(o_res, "order_id", None),
                "error": getattr(o_res, "error", None),
            }
            if unk_leg and not ok:
                filled.append((leg, res))
        else:
            ok = False
            res = {"success": False, "error": "NO_EXECUTOR_FOK_METHOD"}

        if ok and float(res.get("size") or sh) < sh * 0.95:
            filled.append((leg, res))
            ok = False

        if not ok:
            unwound_cnt = 0
            now_rb = time.time()
            for f_leg, f_res in filled:
                f_tok = str(f_leg.get("token_id") or "")
                f_nr = bool(f_leg["neg_risk"]) if "neg_risk" in f_leg and f_leg.get("neg_risk") is not None else bool(neg_risk)
                f_sh = float(f_res.get("size") or sh)
                f_px = 0.02
                if hasattr(executor, "wait_for_erc1155_delivery") and not getattr(executor, "dry_run", False):
                    try:
                        executor.wait_for_erc1155_delivery(f_tok, expected_min_delta=f_sh * 0.90, timeout_sec=2.5)
                    except Exception:
                        pass
                uw_ok = False
                if not f_res.get("outcome_unknown") and hasattr(executor, "execute_unwind_order"):
                    try:
                        uw_r = executor.execute_unwind_order(
                            f_tok,
                            size=f_sh,
                            side="SELL",
                            min_price=f_px,
                            neg_risk=f_nr,
                        )
                    except TypeError:
                        uw_r = executor.execute_unwind_order(f"UNW_{bundle_id}", f_tok, f_sh, f_px)
                    uw_ok = bool(getattr(uw_r, "success", False) or (isinstance(uw_r, Mapping) and uw_r.get("success")))
                elif not f_res.get("outcome_unknown") and hasattr(executor, "place_fok_order"):
                    uw_r = executor.place_fok_order(f_tok, "SELL", f_sh, f_px, neg_risk=f_nr)
                    uw_ok = bool((uw_r or {}).get("success"))
                if uw_ok:
                    unwound_cnt += 1
                elif harvester is not None:
                    rid = f"{bundle_id}_UNWRESID_{f_tok[:8]}_{int(now_rb)}"
                    f_mid = str(f_leg.get("market_id") or "")
                    f_cid = str(f_leg.get("condition_id") or f_mid)
                    f_not = round(float(f_res.get("making_amount") or (f_sh * _sf(f_leg.get("ask_px"), 0.3))), 4)
                    if hasattr(harvester, "_make_single_leg_lock_pos"):
                        rpos = harvester._make_single_leg_lock_pos(
                            rid, "MULTI_LEG_RESIDUAL", sleeve_src, cand_asset, "resid",
                            f_mid, f_cid, f_tok, str(f_leg.get("side") or "YES").upper(), f_nr,
                            f_sh, f_not, float(f_res.get("fee_usd") or 0.0),
                            _sf(f_leg.get("fee_rate"), 0.0), _sf(f_leg.get("fee_exponent"), 1.0),
                            "crypto_fees_v2", float(exp_ts or (now_rb + 7200.0)), now_rb, 0.0,
                            f_res.get("order_id"), False, unk=bool(f_res.get("outcome_unknown")),
                        )
                    else:
                        rpos = {
                            "trade_id": rid, "token_id": f_tok, "market_id": f_mid, "condition_id": f_cid,
                            "asset": cand_asset, "sleeve": sleeve_src, "shares": f_sh, "entry_shares": f_sh,
                            "remaining_shares": f_sh, "notional_usd": f_not, "entry_ts": now_rb,
                            "candle_expiry_ts": float(exp_ts or (now_rb + 7200.0)), "status": "POSITION_CONFIRMED",
                            "neg_risk": f_nr,
                        }
                    harvester.active_positions[rid] = rpos
            return {"success": False, "reason": f"LEG_FOK_REJECTED:{tok[:12]}", "unwound_legs": unwound_cnt}

        filled.append((leg, res))
        total_spent += float(res.get("making_amount") or (sh * px)) + float(res.get("fee_usd") or 0.0)

    return {
        "success": True,
        "bundle_id": bundle_id,
        "leg_count": len(filled),
        "shares": sh,
        "total_cost_usd": round(total_spent, 4),
        "filled_details": filled,
        "filled_legs": [str(f[0].get("token_id")) for f in filled],
    }


async def execute_multi_leg_all_yes_bundle(
    executor: Any,
    legs: Sequence[Mapping[str, Any]],
    *,
    shares: float,
    bundle_id: str = "BUNDLE",
    neg_risk: bool = True,
    harvester: Any = None,
    exp_ts: float = 0.0,
    sleeve_src: str = "NR0_ALL_YES_COMPLETE_SET",
    cand_asset: str = "NR0",
) -> Dict[str, Any]:
    """
    Execute a `3..12` leg equal-share FOK bundle (`NR0`, `W_PRUNE1_NR0_BASKET`, `NR6`, `LP_COMP1`, `DC1`),
    ordering legs from thinnest book depth to deepest so the hardest leg fills first, and immediately
    unwinding filled legs via FOK sell if any subsequent leg rejects.
    """
    return await asyncio.to_thread(
        _execute_multi_leg_bundle_sync,
        executor,
        legs,
        shares=shares,
        bundle_id=bundle_id,
        neg_risk=neg_risk,
        harvester=harvester,
        exp_ts=exp_ts,
        sleeve_src=sleeve_src,
        cand_asset=cand_asset,
    )


def _register_bundle_leg_positions(
    harvester: Any,
    *,
    bundle_id: str,
    sleeve_src: str,
    cand_asset: str,
    legs: Sequence[Mapping[str, Any]],
    filled_details: Sequence[Tuple[Mapping[str, Any], Dict[str, Any]]],
    shares: float,
    total_cost_usd: float,
    exp_ts: float,
    now_ts: float,
    default_neg_risk: bool = True,
) -> List[str]:
    eff_bundle_cost = round(float(total_cost_usd) / max(0.01, float(shares)), 5)
    detail_by_tok = {str(lg.get("token_id") or ""): rs for lg, rs in (filled_details or [])}
    per_leg_fallback = float(total_cost_usd) / float(max(1, len(legs)))
    exp_leg_cnt = len(legs)
    tids: List[str] = []
    for idx, leg in enumerate(legs):
        tok = str(leg.get("token_id") or "")
        lid = f"{bundle_id}_L{idx}_{tok[:8]}"
        rs = detail_by_tok.get(tok) or {}
        not_u = round(float(rs.get("making_amount") or per_leg_fallback), 4)
        fee_u = round(float(rs.get("fee_usd") or 0.0), 4)
        f_sh = float(rs.get("size") or shares)
        leg_nr = bool(leg["neg_risk"]) if "neg_risk" in leg and leg.get("neg_risk") is not None else bool(default_neg_risk)
        leg_fr = _sf(leg.get("fee_rate"), 0.0)
        leg_fe = _sf(leg.get("fee_exponent"), 1.0)
        mid = str(leg.get("market_id") or "")
        cid = str(leg.get("condition_id") or mid)
        side_s = str(leg.get("side") or leg.get("label") or "YES").upper()
        if hasattr(harvester, "_make_single_leg_lock_pos"):
            pos = harvester._make_single_leg_lock_pos(
                lid,
                "MULTI_LEG_BUNDLE",
                sleeve_src,
                cand_asset,
                "bundle",
                mid,
                cid,
                tok,
                side_s,
                leg_nr,
                f_sh,
                not_u,
                fee_u,
                leg_fr,
                leg_fe,
                "crypto_fees_v2",
                exp_ts,
                now_ts,
                0.0,
                rs.get("order_id"),
                True,
                unk=False,
            )
            pos["box_id"] = bundle_id
            pos["box_expected_legs"] = exp_leg_cnt
            pos["is_dominance_box"] = True
            pos["is_single_leg_lock"] = False
            pos["box_cost_net"] = eff_bundle_cost
            pos["box_total_cost_usd"] = round(float(total_cost_usd), 4)
            pos["shares"] = f_sh
        else:
            pos = {
                "trade_id": lid,
                "token_id": tok,
                "market_id": mid,
                "condition_id": cid,
                "target_token": side_s,
                "asset": cand_asset,
                "box_id": bundle_id,
                "box_expected_legs": exp_leg_cnt,
                "is_dominance_box": True,
                "is_single_leg_lock": False,
                "hold_to_maturity_lock": True,
                "box_type": "MULTI_LEG_BUNDLE",
                "box_cost_net": eff_bundle_cost,
                "box_total_cost_usd": round(float(total_cost_usd), 4),
                "sleeve": sleeve_src,
                "shares": f_sh,
                "entry_shares": f_sh,
                "remaining_shares": f_sh,
                "entry_price": round(not_u / max(f_sh, 0.01), 6),
                "notional_usd": not_u,
                "fee_usd": fee_u,
                "entry_ts": now_ts,
                "entry_time_utc": _iso_utc(now_ts),
                "candle_expiry_ts": exp_ts,
                "status": "MATCHED_PENDING_SETTLEMENT",
                "neg_risk": leg_nr,
            }
        harvester.active_positions[lid] = pos
        tids.append(lid)
    return tids


def _fetch_books_fast_sync(ex: Any, token_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    toks = [str(t) for t in token_ids if t]
    if not toks:
        return {}
    if "get_market_book" not in getattr(ex, "__dict__", {}) and hasattr(ex, "get_market_books_batch"):
        try:
            batch = ex.get_market_books_batch(toks)
            if isinstance(batch, Mapping):
                return {str(k): (dict(v) if isinstance(v, Mapping) else {}) for k, v in batch.items()}
        except Exception:
            pass
    if hasattr(ex, "get_market_book"):
        return {t: (ex.get_market_book(t) or {}) for t in toks}
    return {}


def finish_protocol_v2_special_box_sync(
    harvester: Any,
    candidate_box: Mapping[str, Any],
    dedupe_k: str,
    retry_cd: Dict[str, float],
    now_ts: float,
    rcfg: Mapping[str, Any],
    *,
    own_grad: bool = True,
) -> Dict[str, Any]:
    """
    Synchronous execution finisher called inside `PolymarketLiveHarvester.maybe_execute_graduated_d1_box`
    for `CTF_OVERROUND` (`splitPosition + dual bid FOK`) and `MULTI_LEG_BUNDLE` (`3..12` leg bundles).
    """
    if getattr(harvester, "dry_run", True):
        return {"executed": False, "reason": "DRY_RUN_SKIP_SPECIAL_V2_BOX"}
    ex = getattr(harvester, "executor", None)
    if ex is None:
        return {"executed": False, "reason": "NO_LIVE_EXECUTOR"}
    btype = str(candidate_box.get("box_type") or "").upper()
    sleeve_src = str(candidate_box.get("sleeve_source") or candidate_box.get("sleeve") or "NR0_ALL_YES_COMPLETE_SET")
    cand_asset = str(candidate_box.get("asset") or sleeve_src[:4]).upper()
    cand_ts = float(candidate_box.get("ts_unix") or now_ts)
    exp_ts = float(candidate_box.get("expiry_ts") or (now_ts + 7200.0))
    if (now_ts - cand_ts) > 6.5 or (btype == "MULTI_LEG_BUNDLE" and (exp_ts - now_ts) < 20.0):
        return {"executed": False, "reason": "STALE_OR_OUTSIDE_TTE_WINDOW"}

    if "SPORTS" in sleeve_src or sleeve_src in {"DC1_DOUBLE_CHANCE_1X2_PARITY", "LP_COMP1_SPORTS_TRIANGLES", "HALFTIME_FREEZE_OFFSET_BOX"}:
        try:
            from src.polymarket_research.riskless_machine_gun_engine import is_sports_dead_ball_safe
            if not is_sports_dead_ball_safe(dict(candidate_box)):
                return {"executed": False, "reason": "LIVE_BALL_SPORTS_ORACLE_LAG_VETO"}
        except Exception:
            pass

    collat = getattr(harvester, "_last_known_collateral", None)
    if collat is None and hasattr(ex, "get_collateral_balance"):
        try:
            c_raw = ex.get_collateral_balance()
            if isinstance(c_raw, (int, float)) and not isinstance(c_raw, bool) and math.isfinite(float(c_raw)):
                collat = float(c_raw)
                harvester._last_known_collateral = collat
        except Exception:
            collat = 0.0
    collat_f = max(0.0, float(collat or 0.0))
    if collat_f < 20.0 and hasattr(harvester, "_preempt_resting_maker_anchors"):
        try:
            if harvester._preempt_resting_maker_anchors(reason=f"SPECIAL_V2:{sleeve_src}", market_ids=None) and hasattr(ex, "get_collateral_balance"):
                c_ref = ex.get_collateral_balance()
                if isinstance(c_ref, (int, float)) and not isinstance(c_ref, bool) and math.isfinite(float(c_ref)):
                    collat_f = max(0.0, float(c_ref))
                    harvester._last_known_collateral = collat_f
        except Exception:
            pass

    cur_exp = sum(float(p.get("notional_usd", 0.0) or 0.0) for p in harvester.active_positions.values())
    budget = compute_gatling_clip_budget_usd(
        live_equity=collat_f + cur_exp,
        free_cash=collat_f,
        cur_open_exp=cur_exp,
        box_type=btype,
        sleeve_src=sleeve_src,
        own_grad=own_grad,
        single_clip_cap_usd=float(rcfg.get("d1_box_max_budget_usd", 250.0)),
        max_exposure_usd=float(getattr(harvester, "max_exposure", 100.0) or 100.0),
    )
    if budget < 5.0:
        return {"executed": False, "reason": "INSUFFICIENT_BOX_COLLATERAL_HEADROOM"}

    if btype == "CTF_OVERROUND":
        cid = str(candidate_box.get("condition_id") or candidate_box.get("leg_a_condition_id") or "")
        y_tok = str(candidate_box.get("yes_token_id") or candidate_box.get("leg_a_token_id") or "")
        n_tok = str(candidate_box.get("no_token_id") or candidate_box.get("leg_b_token_id") or "")
        fr = _sf(candidate_box.get("fee_rate") or candidate_box.get("leg_a_fee_rate"), 0.0)
        fe = _sf(candidate_box.get("fee_exponent") or candidate_box.get("leg_a_fee_exponent"), 1.0)
        if not cid or not y_tok or not n_tok:
            return {"executed": False, "reason": "INVALID_CTF_OVERROUND_SPEC"}
        books_ovr = _fetch_books_fast_sync(ex, [y_tok, n_tok])
        if books_ovr:
            by = books_ovr.get(y_tok) or {}
            bn = books_ovr.get(n_tok) or {}
            bids_y = sorted([(float(b["price"]), float(b["size"])) for b in (by.get("bids") or []) if float(b.get("size", 0)) > 0], reverse=True)
            bids_n = sorted([(float(b["price"]), float(b["size"])) for b in (bn.get("bids") or []) if float(b.get("size", 0)) > 0], reverse=True)
            if not bids_y or not bids_n:
                return {"executed": False, "reason": "EMPTY_OVERROUND_BIDS"}
            y_bid, y_sz = bids_y[0]
            n_bid, n_sz = bids_n[0]
        else:
            y_bid = _sf(candidate_box.get("yes_bid"), 0.51)
            n_bid = _sf(candidate_box.get("no_bid"), 0.51)
            y_sz = n_sz = _sf(candidate_box.get("max_fillable_shares"), 10.0)
        net_rev = (y_bid - compute_exact_taker_fee_per_share(y_bid, fr, fe)) + (n_bid - compute_exact_taker_fee_per_share(n_bid, fr, fe))
        if net_rev < 1.004:
            return {"executed": False, "reason": f"OVERROUND_GONE:{net_rev:.4f}"}
        sh = math.floor(min(budget, min(y_sz, n_sz) / 1.15) * 100.0) / 100.0
        if sh < 5.0:
            return {"executed": False, "reason": "OVERROUND_MIN_SHARES"}
        sp = (
            ex.split_collateral_to_complete_set(cid, sh, neg_risk=False)
            if hasattr(ex, "split_collateral_to_complete_set")
            else (
                attempt_onchain_split_position(ex, cid, sh, neg_risk=False, up_token_id=y_tok, down_token_id=n_tok)
                if attempt_onchain_split_position is not None
                else {"success": False, "reason": "NO_SPLIT_HANDLER"}
            )
        )
        if not (sp or {}).get("success"):
            retry_cd[dedupe_k] = now_ts + 8.0
            return {"executed": False, "reason": f"SPLIT_FAILED:{(sp or {}).get('reason') or (sp or {}).get('error')}"}
        u_res = (
            ex.execute_atomic_box_overround_unwind(f"CTFOVR_{cid[:10]}", y_tok, y_bid, n_tok, n_bid, sh, False, False, fr, fe, fr, fe)
            if hasattr(ex, "execute_atomic_box_overround_unwind")
            else {"success": False}
        )
        if not (u_res or {}).get("success"):
            if (u_res or {}).get("partial_leg_unwind"):
                la_d = (u_res or {}).get("leg_a") or {}
                a_sold = bool(la_d.get("filled") or la_d.get("success"))
                sold_d = la_d if a_sold else ((u_res or {}).get("leg_b") or {})
                unsold_tok = n_tok if a_sold else y_tok
                unsold_side = "NO" if a_sold else "YES"
                sold_cash = max(0.0, float(sold_d.get("taking_amount") or 0.0) - float(sold_d.get("fee_usd") or 0.0))
                unw_ok = False
                if hasattr(ex, "execute_unwind_order"):
                    try:
                        uw = ex.execute_unwind_order(unsold_tok, size=sh, side="SELL", min_price=0.02, neg_risk=False)
                    except TypeError:
                        uw = ex.execute_unwind_order(f"UNW_OVR_{cid[:8]}", unsold_tok, sh, 0.02)
                    unw_ok = bool(getattr(uw, "success", False) or (isinstance(uw, Mapping) and uw.get("success")))
                if not unw_ok:
                    rid = f"CTFOVR_RESID_{cid[:8]}_{int(now_ts)}"
                    rem_cost = round(max(0.01, sh - sold_cash), 4)
                    if hasattr(harvester, "_make_single_leg_lock_pos"):
                        harvester.active_positions[rid] = harvester._make_single_leg_lock_pos(
                            rid, "CTF_OVERROUND_RESIDUAL", "CTF_OVERROUND_MINT_SELL", cand_asset, "resid",
                            cid, cid, unsold_tok, unsold_side, False, sh, rem_cost, 0.0, fr, fe,
                            "crypto_fees_v2", exp_ts, now_ts, 0.0, None, True, unk=False,
                        )
                    else:
                        harvester.active_positions[rid] = {
                            "trade_id": rid, "token_id": unsold_tok, "condition_id": cid, "market_id": cid,
                            "target_token": unsold_side, "asset": cand_asset, "sleeve": "CTF_OVERROUND_MINT_SELL",
                            "shares": sh, "entry_shares": sh, "remaining_shares": sh, "notional_usd": rem_cost,
                            "entry_ts": now_ts, "candle_expiry_ts": exp_ts, "status": "POSITION_CONFIRMED", "neg_risk": False,
                        }
                    harvester.save_state()
                retry_cd[dedupe_k] = now_ts + 8.0
                return {"executed": False, "reason": "OVERROUND_PARTIAL_LEG_UNWOUND"}
            if hasattr(ex, "attempt_onchain_complete_set_merge"):
                ex.attempt_onchain_complete_set_merge(cid, min_pairs=max(1.0, sh - 0.05), max_pairs=sh, neg_risk=False)
            elif hasattr(ex, "merge_complete_set_positions"):
                ex.merge_complete_set_positions(cid, sh, neg_risk=False)
            retry_cd[dedupe_k] = now_ts + 8.0
            return {"executed": False, "reason": "OVERROUND_SWEEP_REJECTED_MERGED_BACK"}
        la, lb = u_res["leg_a"], u_res["leg_b"]
        fee_tot = round(float(la.get("fee_usd") or 0.0) + float(lb.get("fee_usd") or 0.0), 4)
        realized = round(
            (float(la.get("taking_amount") or 0.0) - float(la.get("fee_usd") or 0.0))
            + (float(lb.get("taking_amount") or 0.0) - float(lb.get("fee_usd") or 0.0)),
            4,
        )
        net_pnl = round(realized - sh, 4)
        tid = f"CTFOVR_{cid[:10]}_{int(now_ts)}"
        iso_now = _iso_utc(now_ts)
        harvester.closed_positions.append(
            {
                "trade_id": tid,
                "box_id": tid,
                "is_dominance_box": True,
                "box_type": "CTF_OVERROUND",
                "sleeve": "CTF_OVERROUND_MINT_SELL",
                "asset": cand_asset,
                "condition_id": cid,
                "entry_shares": sh,
                "notional_usd": sh,
                "fee_usd": fee_tot,
                "payout_usd": realized,
                "net_pnl_usd": net_pnl,
                "won": bool(net_pnl >= 0.0),
                "status": "CLOSED",
                "close_reason": "CTF_OVERROUND_INSTANT_MINT_SELL",
                "entry_ts": now_ts,
                "exit_ts": now_ts,
                "entry_time_utc": iso_now,
                "settled_at_utc": iso_now,
            }
        )
        harvester.closed_positions = harvester.closed_positions[-600:]
        rc_obj = getattr(harvester, "risk_controller", None)
        if rc_obj is not None and hasattr(rc_obj, "record_trade_pnl"):
            try:
                rc_obj.record_trade_pnl(net_pnl, is_non_directional=True)
            except Exception:
                pass
        if dedupe_k and hasattr(harvester, "_record_seen_d1_box_key"):
            harvester._record_seen_d1_box_key(dedupe_k)
        if hasattr(ex, "invalidate_collateral_cache"):
            ex.invalidate_collateral_cache()
        harvester._pending_collateral_refresh = True
        harvester.save_state()
        return {"executed": True, "result": u_res, "leg_trade_ids": [tid]}

    if btype == "MULTI_LEG_BUNDLE":
        raw_legs = [dict(lg) for lg in (candidate_box.get("legs") or []) if isinstance(lg, Mapping)]
        if not (3 <= len(raw_legs) <= 12):
            return {"executed": False, "reason": "INVALID_MULTI_LEG_COUNT"}
        busy = {str(p.get("market_id") or "") for p in harvester.active_positions.values()}
        if any(str(lg.get("market_id") or "") in busy for lg in raw_legs if lg.get("market_id")):
            return {"executed": False, "reason": "MARKET_ALREADY_OCCUPIED"}
        max_cost_cap = float(candidate_box.get("max_box_cost_net") or 0.992)
        default_nr = bool(candidate_box.get("neg_risk", True))
        books_ml = _fetch_books_fast_sync(ex, [str(lg.get("token_id") or "") for lg in raw_legs])
        if books_ml:
            refreshed_legs: List[Dict[str, Any]] = []
            tot_net_ps = 0.0
            min_sh_avail = 999999.0
            for lg in raw_legs:
                tok = str(lg.get("token_id") or "")
                bk = books_ml.get(tok) or {}
                asks = sorted([(float(a["price"]), float(a["size"])) for a in (bk.get("asks") or []) if float(a.get("size", 0)) > 0])
                if not asks:
                    return {"executed": False, "reason": f"EMPTY_LEG_ASK:{tok[:10]}"}
                best_px, best_sz = asks[0]
                q_px, _, _ = quantize_dynamic_tick_price(best_px, "BUY", shares=5.0, mode="taker")
                fr = _sf(lg.get("fee_rate"), 0.0)
                fe = _sf(lg.get("fee_exponent"), 1.0)
                tot_net_ps += q_px + compute_exact_taker_fee_per_share(q_px, fr, fe)
                min_sh_avail = min(min_sh_avail, best_sz)
                lg_up = dict(lg)
                lg_up["ask_px"] = q_px
                lg_up["ask_size"] = best_sz
                refreshed_legs.append(lg_up)
            if tot_net_ps > max_cost_cap + 1e-6:
                return {"executed": False, "reason": f"FRESH_BUNDLE_COST_EXCEEDED:{tot_net_ps:.4f}"}
        else:
            refreshed_legs = raw_legs
            tot_net_ps = max(0.20, _sf(candidate_box.get("cost_per_share") or candidate_box.get("box_cost_net"), 0.985))
            min_sh_avail = _sf(candidate_box.get("max_fillable_shares"), 10.0)

        sh = float(int(math.floor(min(budget / max(tot_net_ps, 0.25), min_sh_avail / 1.15))))
        if sh < 5.0:
            return {"executed": False, "reason": "BUNDLE_MIN_SHARES"}
        bid = str(candidate_box.get("box_id") or f"MLBOX_{int(now_ts)}")
        res = _execute_multi_leg_bundle_sync(
            ex,
            refreshed_legs,
            shares=sh,
            bundle_id=bid,
            neg_risk=default_nr,
            harvester=harvester,
            exp_ts=exp_ts,
            sleeve_src=sleeve_src,
            cand_asset=cand_asset,
        )
        if not res.get("success"):
            if dedupe_k:
                retry_cd[dedupe_k] = now_ts + 4.5
            return {"executed": False, "reason": str(res.get("reason") or "BUNDLE_EXEC_FAILED"), "result": res}
        if dedupe_k:
            retry_cd.pop(dedupe_k, None)
            if hasattr(harvester, "_record_seen_d1_box_key"):
                harvester._record_seen_d1_box_key(dedupe_k)
        tids = _register_bundle_leg_positions(
            harvester,
            bundle_id=bid,
            sleeve_src=sleeve_src,
            cand_asset=cand_asset,
            legs=refreshed_legs,
            filled_details=res.get("filled_details") or [],
            shares=sh,
            total_cost_usd=float(res["total_cost_usd"]),
            exp_ts=exp_ts,
            now_ts=now_ts,
            default_neg_risk=default_nr,
        )
        if getattr(harvester, "_last_known_collateral", None) is not None:
            harvester._last_known_collateral = max(0.0, float(harvester._last_known_collateral) - float(res["total_cost_usd"]))
        if hasattr(ex, "invalidate_collateral_cache"):
            ex.invalidate_collateral_cache()
        harvester._pending_collateral_refresh = True
        harvester.save_state()
        return {"executed": True, "result": res, "leg_trade_ids": tids}

    return {"executed": False, "reason": f"UNSUPPORTED_SPECIAL_BOX:{btype}"}


async def dispatch_protocol_v2_harvester_candidate(
    harvester: Any,
    box: Mapping[str, Any],
    budget_usd: float,
    now_ts: float,
) -> bool:
    """
    Compact live harvester bridge dispatcher for `CTF_OVERROUND_MINT_SELL` and `MULTI_LEG_BUNDLE`
    so `polymarket_live_harvester.py` stays ultra-lean (`< 1 MB` bundle ceiling).
    """
    if getattr(harvester, "dry_run", True):
        return False
    ex = getattr(harvester, "executor", None)
    if ex is None:
        return False
    btype = str(box.get("box_type") or "").upper()
    if btype == "CTF_OVERROUND":
        sh = math.floor(min(float(budget_usd), _sf(box.get("max_fillable_shares"), 6.0)) * 100.0) / 100.0
        if sh < 5.0:
            return False
        res = await execute_binary_ctf_overround_mint_sell(
            ex,
            condition_id=str(box.get("condition_id") or ""),
            yes_token_id=str(box.get("yes_token_id") or box.get("token_a") or ""),
            no_token_id=str(box.get("no_token_id") or box.get("token_b") or ""),
            yes_min_bid=_sf(box.get("yes_bid") or box.get("ask_a"), 0.5),
            no_min_bid=_sf(box.get("no_bid") or box.get("ask_b"), 0.5),
            shares=sh,
            fee_rate=_sf(box.get("fee_rate"), 0.0),
            harvester=harvester,
            expiry_ts=float(box.get("expiry_ts") or (now_ts + 7200.0)),
            cand_asset=str(box.get("asset") or "CTFOVR"),
        )
        if res.get("success"):
            cid = str(box.get("condition_id") or "CTFOVR")
            iso_now = _iso_utc(now_ts)
            harvester.closed_positions.append(
                {
                    "trade_id": f"CTFOVR_{cid[:10]}_{int(now_ts)}",
                    "box_id": f"CTFOVR_{cid[:10]}_{int(now_ts)}",
                    "is_dominance_box": True,
                    "box_type": "CTF_OVERROUND",
                    "sleeve": "CTF_OVERROUND_MINT_SELL",
                    "asset": str(box.get("asset") or "CTFOVR"),
                    "condition_id": cid,
                    "entry_shares": sh,
                    "notional_usd": float(res["cost_usd"]),
                    "fee_usd": float(res.get("fee_usd") or 0.0),
                    "payout_usd": float(res["realized_cash_usd"]),
                    "net_pnl_usd": float(res["net_pnl_usd"]),
                    "won": bool(float(res["net_pnl_usd"]) >= 0.0),
                    "status": "CLOSED",
                    "close_reason": "CTF_OVERROUND_INSTANT_MINT_SELL",
                    "entry_ts": now_ts,
                    "exit_ts": now_ts,
                    "entry_time_utc": iso_now,
                    "settled_at_utc": iso_now,
                }
            )
            harvester.closed_positions = harvester.closed_positions[-600:]
            ex.invalidate_collateral_cache()
            harvester._pending_collateral_refresh = True
            await asyncio.to_thread(harvester.save_state)
            return True
    elif btype == "MULTI_LEG_BUNDLE":
        legs = box.get("legs") or []
        cost_sh = max(0.20, _sf(box.get("cost_per_share"), 1.0))
        sh = math.floor(min(float(budget_usd) / cost_sh, _sf(box.get("max_fillable_shares"), 6.0)) * 100.0) / 100.0
        if sh < 5.0 or not (3 <= len(legs) <= 12):
            return False
        bid = f"MLBOX_{int(now_ts)}"
        default_nr = bool(box.get("neg_risk", True))
        exp_ts = float(box.get("expiry_ts") or (now_ts + 7200.0))
        sleeve_s = str(box.get("sleeve") or "NR0_ALL_YES_COMPLETE_SET")
        asset_s = str(box.get("asset") or "NR0")
        res = await execute_multi_leg_all_yes_bundle(
            ex,
            legs,
            shares=sh,
            bundle_id=bid,
            neg_risk=default_nr,
            harvester=harvester,
            exp_ts=exp_ts,
            sleeve_src=sleeve_s,
            cand_asset=asset_s,
        )
        if res.get("success"):
            _register_bundle_leg_positions(
                harvester,
                bundle_id=bid,
                sleeve_src=sleeve_s,
                cand_asset=asset_s,
                legs=legs,
                filled_details=res.get("filled_details") or [],
                shares=sh,
                total_cost_usd=float(res["total_cost_usd"]),
                exp_ts=exp_ts,
                now_ts=now_ts,
                default_neg_risk=default_nr,
            )
            ex.invalidate_collateral_cache()
            harvester._pending_collateral_refresh = True
            await asyncio.to_thread(harvester.save_state)
            return True
    return False


async def run_protocol_v2_daemon_scan(
    daemon: Any,
    opps_out: List[Dict[str, Any]],
    *,
    now_ts: Optional[float] = None,
) -> None:
    """
    Fault-isolated 6-Pillar Protocol V2 expansion scanner for `Alpha124ShadowDaemon`:
      1. `EQ1_PYTH_EQUITY_DOMINANCE_BOX` (`14:15-16:00 ET`, upward close rungs only, `PYTH_EQUITY_SYMBOLS` filtered pre-slice)
      2. `B1_INTRADAY_ONETOUCH_NOON_BOX` (`10:25-12:00 ET`, `br.direction == 'UP'`, `not sr.is_downward`, `sr.end_ts <= br.end_ts`)
      3. `NR4`/`NR5` Optimal Tail Convert on closed NegRisk slates -> wired to live `emit_live_negrisk_convert_candidate`
      4. `MENTION1_CUMULATIVE_LADDER_BOX` (`tag_slug=mentions` cumulative word ladders)
      5. `DC1_DOUBLE_CHANCE_1X2_PARITY` & `LP_COMP1_SPORTS_TRIANGLES` (strictly pre-match `kickoff_ts - now >= 300s`)
      6. `C1_BINARY_COMPLETE_SET` & `CTF_OVERROUND_MINT_SELL` across fresh binary WS books
    """
    import collections
    from zoneinfo import ZoneInfo

    try:
        ny_tz = ZoneInfo("America/New_York")
    except Exception:
        from datetime import timedelta
        ny_tz = timezone(timedelta(hours=-4))

    now = float(now_ts if now_ts is not None else time.time())
    et_dt = datetime.fromtimestamp(now, tz=ny_tz)
    et_hr = float(et_dt.hour) + float(et_dt.minute) / 60.0

    def _extr_best_bid(bids_raw: Any) -> Tuple[float, float]:
        bids = sorted(
            [(float(b["price"]), float(b["size"])) for b in (bids_raw or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
            key=lambda x: -x[0],
        )
        return (round(bids[0][0], 4), round(bids[0][0] * bids[0][1], 2)) if bids else (0.0, 0.0)

    # Pillar 1: `EQ1_PYTH_EQUITY_DOMINANCE_BOX` (`14:15-16:00 ET` RTH window)
    try:
        if 14.25 <= et_hr <= 16.0 and getattr(daemon, "pyth_close_ladders", None):
            eq_rungs = [
                rc
                for rgs in daemon.pyth_close_ladders.values()
                for rc in rgs
                if str(getattr(rc, "asset", "")).upper() in PYTH_EQUITY_SYMBOLS
                and not bool(getattr(rc, "is_downward", False))
                and 120.0 < (float(rc.end_ts) - now) <= 14400.0
            ]
            if eq_rungs:
                eq_toks = [t for rc in eq_rungs[:40] for t in (rc.yes_token, rc.no_token)]
                eq_bks = await daemon.fetch_books_batch(eq_toks, timeout=2.5)
                by_tkr: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
                for rc in eq_rungs[:40]:
                    by_y, by_n = eq_bks.get(rc.yes_token), eq_bks.get(rc.no_token)
                    if not by_y or not by_n:
                        continue
                    ay, sy = daemon._best_ask_sz(by_y)
                    an, sn = daemon._best_ask_sz(by_n)
                    if ay < 1.0 and an < 1.0:
                        sdate = datetime.fromtimestamp(rc.end_ts, tz=ny_tz).strftime("%Y-%m-%d")
                        by_tkr[str(rc.asset).upper()].append({
                            "oracle": "pyth",
                            "settle_date": sdate,
                            "market_id": rc.market_id,
                            "condition_id": rc.condition_id,
                            "strike": rc.strike,
                            "yes_token_id": rc.yes_token,
                            "no_token_id": rc.no_token,
                            "yes_ask": ay,
                            "no_ask": an,
                            "yes_ask_size": sy,
                            "no_ask_size": sn,
                            "fee_rate": rc.fee_rate,
                            "fee_exponent": rc.fee_exponent,
                            "end_ts": rc.end_ts,
                            "bk_yes": by_y,
                            "bk_no": by_n,
                        })
                for tkr, rows_eq in by_tkr.items():
                    for hit_eq in detect_eq1_pyth_equity_dominance_box(rows_eq, ticker=tkr, et_hour_float=et_hr):
                        la_e, lb_e = hit_eq["leg_a"], hit_eq["leg_b"]
                        r_a = next((x for x in rows_eq if x["yes_token_id"] == la_e["token_id"] or x["no_token_id"] == la_e["token_id"]), None)
                        r_b = next((x for x in rows_eq if x["yes_token_id"] == lb_e["token_id"] or x["no_token_id"] == lb_e["token_id"]), None)
                        if r_a and r_b:
                            bk_ea = r_a["bk_yes"] if la_e["token_id"] == r_a["yes_token_id"] else r_a["bk_no"]
                            bk_eb = r_b["bk_yes"] if lb_e["token_id"] == r_b["yes_token_id"] else r_b["bk_no"]
                            k_lo_e, k_hi_e = float(hit_eq["strike_low"]), float(hit_eq["strike_high"])
                            opps_out.append({
                                "sleeve": "EQ1_PYTH_EQUITY_DOMINANCE_BOX",
                                "market": f"{tkr} EQ1 {k_lo_e} vs {k_hi_e}",
                                "ask_vwap": hit_eq["cost_per_share"],
                                "p_model": 1.0,
                                "net_edge": hit_eq["net_edge_per_share"],
                                "l1_usd": round(hit_eq["max_fillable_shares"] * hit_eq["cost_per_share"], 2),
                            })
                            daemon.emit_live_two_leg_box_candidate(
                                box_type="BARRIER_MONO",
                                sleeve_source="EQ1_PYTH_EQUITY_DOMINANCE_BOX",
                                asset=tkr,
                                dedupe_key=f"EQ1_{r_a['market_id']}_{r_b['market_id']}",
                                leg_a={**la_e, "opp_token_id": r_a["no_token_id"] if la_e["token_id"] == r_a["yes_token_id"] else r_a["yes_token_id"], "market_id": r_a["market_id"], "condition_id": r_a["condition_id"], "fee_rate": r_a["fee_rate"], "fee_exponent": r_a["fee_exponent"]},
                                leg_b={**lb_e, "opp_token_id": r_b["no_token_id"] if lb_e["token_id"] == r_b["yes_token_id"] else r_b["yes_token_id"], "market_id": r_b["market_id"], "condition_id": r_b["condition_id"], "fee_rate": r_b["fee_rate"], "fee_exponent": r_b["fee_exponent"]},
                                bk_a=bk_ea,
                                bk_b=bk_eb,
                                close_ts=float(min(r_a["end_ts"], r_b["end_ts"])),
                                now_ts=now,
                                max_box_cost_override=0.990,
                                k_low=k_lo_e,
                                k_high=k_hi_e,
                            )
    except Exception as exc_eq1:
        logger.debug(f"Protocol V2 EQ1 scan notice: {exc_eq1}")

    # Pillar 2: `B1_INTRADAY_ONETOUCH_NOON_BOX` (`10:25-12:00 ET` One-Touch vs Noon Close)
    try:
        if 10.25 <= et_hr <= 12.0 and getattr(daemon, "barrier_rungs", None) and getattr(daemon, "strike_ladders", None):
            b1_pairs: List[Tuple[Any, Any]] = []
            for br in daemon.barrier_rungs.values():
                dir_br = str(getattr(br, "direction", "DOWN" if getattr(br, "is_downward", False) else "UP")).upper()
                if dir_br != "UP" or not (120.0 < (float(br.end_ts) - now) <= 604800.0):
                    continue
                for rgs_m in daemon.strike_ladders.values():
                    for sr in rgs_m:
                        if (
                            sr.asset == br.asset
                            and not bool(getattr(sr, "is_downward", False))
                            and abs(float(sr.strike) - float(br.strike)) <= 1e-6
                            and 120.0 < (float(sr.end_ts) - now) <= 10800.0
                            and float(sr.end_ts) <= float(br.end_ts) + 60.0
                        ):
                            b1_pairs.append((br, sr))
            if b1_pairs:
                b1_toks = [t for br, sr in b1_pairs[:25] for t in (br.yes_token, br.no_token, sr.yes_token, sr.no_token)]
                b1_bks = await daemon.fetch_books_batch(b1_toks, timeout=2.5)
                for br, sr in b1_pairs[:25]:
                    bk_by, bk_bn = b1_bks.get(br.yes_token), b1_bks.get(br.no_token)
                    bk_sy, bk_sn = b1_bks.get(sr.yes_token), b1_bks.get(sr.no_token)
                    if not (bk_by and bk_bn and bk_sy and bk_sn):
                        continue
                    ay_t, sz_t = daemon._best_ask_sz(bk_by)
                    an_n, sz_n = daemon._best_ask_sz(bk_sn)
                    if ay_t >= 1.0 or an_n >= 1.0 or min(sz_t, sz_n) < 5.0:
                        continue
                    b1_hit = detect_b1_intraday_onetouch_noon_box(
                        asset=br.asset,
                        strike=float(br.strike),
                        direction="UP",
                        oracle_touch="binance_1m_usdt",
                        oracle_noon="binance_1m_usdt",
                        touch_yes_ask=ay_t,
                        noon_no_ask=an_n,
                        touch_yes_token=br.yes_token,
                        noon_no_token=sr.no_token,
                        touch_condition_id=br.condition_id,
                        noon_condition_id=sr.condition_id,
                        et_hour_float=et_hr,
                        fee_rate=max(float(getattr(br, "fee_rate", 0.0)), float(getattr(sr, "fee_rate", 0.0))),
                    )
                    if b1_hit is not None:
                        opps_out.append({
                            "sleeve": "B1_INTRADAY_ONETOUCH_NOON_BOX",
                            "market": f"{br.asset} B1 Touch/Noon {br.strike}",
                            "ask_vwap": b1_hit["cost_per_share"],
                            "p_model": 1.0,
                            "net_edge": b1_hit["net_edge_per_share"],
                            "l1_usd": round(min(sz_t, sz_n) * b1_hit["cost_per_share"], 2),
                        })
                        daemon.emit_live_two_leg_box_candidate(
                            box_type="BARRIER_MONO",
                            sleeve_source="B1_INTRADAY_ONETOUCH_NOON_BOX",
                            asset=br.asset,
                            dedupe_key=f"B1NOON_{br.market_id}_{sr.market_id}",
                            leg_a={"token_id": br.yes_token, "opp_token_id": br.no_token, "label": "TOUCH_YES", "side": "YES", "market_id": br.market_id, "condition_id": br.condition_id, "strike": br.strike, "fee_rate": getattr(br, "fee_rate", 0.0), "fee_exponent": 1.0, "end_ts": br.end_ts},
                            leg_b={"token_id": sr.no_token, "opp_token_id": sr.yes_token, "label": "NOON_OPP", "side": "NO", "market_id": sr.market_id, "condition_id": sr.condition_id, "strike": sr.strike, "fee_rate": getattr(sr, "fee_rate", 0.0), "fee_exponent": 1.0, "end_ts": sr.end_ts},
                            bk_a=bk_by,
                            bk_b=bk_sn,
                            close_ts=float(min(br.end_ts, sr.end_ts)),
                            now_ts=now,
                            max_box_cost_override=0.990,
                            k_low=float(br.strike),
                            k_high=float(br.strike),
                        )
    except Exception as exc_b1:
        logger.debug(f"Protocol V2 B1 scan notice: {exc_b1}")

    # Pillar 3: `NR4`/`NR5` Optimal Tail Convert on Closed NegRisk Slates (WS + Batch REST Fallback)
    try:
        cand_nr_slates = [
            sp_c
            for sp_c in (getattr(daemon, "negrisk_convert_slates", None) or {}).values()
            if sp_c.is_closed_convert_safe
            and 120.0 < (float(sp_c.end_ts) - now) <= 259200.0
            and 3 <= len(sp_c.brackets) <= 15
        ]
        cand_nr_slates.sort(key=lambda s: float(s.end_ts))
        cand_nr_slates = cand_nr_slates[:50]
        if cand_nr_slates:
            nr_all_bks: Dict[str, Dict[str, Any]] = {}
            nr_missing: List[str] = []
            for sp_nrc in cand_nr_slates:
                for br_c in sp_nrc.brackets:
                    for tk_c in (str(br_c.get("yes_token") or ""), str(br_c.get("no_token") or "")):
                        if not tk_c or tk_c in nr_all_bks:
                            continue
                        wb_c = daemon._get_fresh_ws_book(tk_c, now, max_age_sec=8.0) if hasattr(daemon, "_get_fresh_ws_book") else None
                        if wb_c:
                            nr_all_bks[tk_c] = wb_c
                        else:
                            nr_missing.append(tk_c)
            if nr_missing and hasattr(daemon, "fetch_books_batch"):
                fetched_nr = await daemon.fetch_books_batch(list(dict.fromkeys(nr_missing))[:120], timeout=2.5)
                if isinstance(fetched_nr, dict):
                    nr_all_bks.update(fetched_nr)
            for sp_nrc in cand_nr_slates:
                nr_outcomes: List[Dict[str, Any]] = []
                nr_bks: Dict[str, Dict[str, Any]] = {}
                for idx_b, br_c in enumerate(sp_nrc.brackets):
                    yt, nt = str(br_c.get("yes_token") or ""), str(br_c.get("no_token") or "")
                    by_c, bn_c = nr_all_bks.get(yt), nr_all_bks.get(nt)
                    if not by_c or not bn_c:
                        break
                    nr_bks[yt], nr_bks[nt] = by_c, bn_c
                    ya, ys = daemon._best_ask_sz(by_c)
                    na, ns = daemon._best_ask_sz(bn_c)
                    yb, yb_u = _extr_best_bid(by_c.get("bids") or [])
                    yb_sz = (yb_u / yb) if yb > 0.0 else 0.0
                    q_idx_c = int(br_c.get("question_index") if br_c.get("question_index") is not None else idx_b)
                    nr_outcomes.append({
                        "index": q_idx_c,
                        "question_index": q_idx_c,
                        "label": str(br_c.get("label") or f"B{idx_b}"),
                        "market_id": str(br_c.get("market_id") or ""),
                        "condition_id": str(br_c.get("condition_id") or ""),
                        "yes_token_id": yt,
                        "no_token_id": nt,
                        "yes_ask": ya if ya < 1.0 else 0.0,
                        "yes_ask_size": ys,
                        "no_ask": na if na < 1.0 else 0.0,
                        "no_ask_size": ns,
                        "yes_bid": yb,
                        "yes_bid_size": yb_sz,
                        "fee_rate": float(br_c.get("fee_rate", 0.0) or 0.0),
                        "fee_exponent": float(br_c.get("fee_exponent", 1.0) or 1.0),
                    })
                if len(nr_outcomes) == len(sp_nrc.brackets) and len(nr_outcomes) >= 3:
                    nr_fee_bips = int(get_cached_negrisk_fee_bips(sp_nrc.neg_risk_market_id, fallback_bips=0))
                    for nr_hit in detect_nr4_nr5_optimal_tail_convert(
                        nr_outcomes,
                        event_id=sp_nrc.event_id,
                        neg_risk_market_id=sp_nrc.neg_risk_market_id,
                        event_meta={"negRiskAugmented": False},
                        fee_bips=nr_fee_bips,
                    ):
                        sl_nr = str(nr_hit["sleeve"])
                        sh_nr = max(6.0, min(15.0, float(nr_hit.get("max_fillable_shares") or 8.0)))
                        opps_out.append({
                            "sleeve": sl_nr,
                            "market": f"{sp_nrc.title[:42]} [{sl_nr}]",
                            "ask_vwap": round(1.0 - float(nr_hit["net_edge_per_share"]), 4),
                            "p_model": 1.0,
                            "net_edge": float(nr_hit["net_edge_per_share"]),
                            "l1_usd": round(sh_nr * max(0.20, 1.0 - float(nr_hit["net_edge_per_share"])), 2),
                        })
                        if hasattr(daemon, "emit_live_negrisk_convert_candidate"):
                            by_idx_o = {int(o["question_index"]): o for o in nr_outcomes}
                            no_lgs_emit = [
                                {
                                    "token_id": lg_n["no_token_id"],
                                    "bracket": {
                                        "no_token": lg_n["no_token_id"],
                                        "market_id": by_idx_o[int(lg_n["index"])]["market_id"],
                                        "condition_id": by_idx_o[int(lg_n["index"])]["condition_id"],
                                        "question_index": int(lg_n["index"]),
                                        "label": lg_n["label"],
                                        "fee_rate": by_idx_o[int(lg_n["index"])]["fee_rate"],
                                        "fee_exponent": by_idx_o[int(lg_n["index"])]["fee_exponent"],
                                    },
                                    "walk": {"worst_px": float(lg_n["no_ask_px"])},
                                }
                                for lg_n in (nr_hit.get("s_no_legs") or [])
                                if int(lg_n["index"]) in by_idx_o
                            ]
                            yes_sells_emit = [
                                {
                                    "token_id": lg_y["yes_token_id"],
                                    "bracket": {
                                        "yes_token": lg_y["yes_token_id"],
                                        "market_id": by_idx_o[int(lg_y["index"])]["market_id"],
                                        "label": lg_y["label"],
                                        "fee_rate": by_idx_o[int(lg_y["index"])]["fee_rate"],
                                        "fee_exponent": by_idx_o[int(lg_y["index"])]["fee_exponent"],
                                    },
                                    "walk": {"worst_px": float(lg_y["yes_bid_px"])},
                                }
                                for lg_y in (nr_hit.get("sc_yes_sell_legs") or [])
                                if int(lg_y["index"]) in by_idx_o
                            ]
                            ret_tail_emit = [
                                {
                                    "yes_token": lg_r["yes_token_id"],
                                    "market_id": by_idx_o[int(lg_r["index"])]["market_id"],
                                    "condition_id": by_idx_o[int(lg_r["index"])]["condition_id"],
                                    "question_index": int(lg_r["index"]),
                                    "label": lg_r["label"],
                                }
                                for lg_r in (nr_hit.get("freeroll_yes_legs") or [])
                                if int(lg_r["index"]) in by_idx_o
                            ]
                            daemon.emit_live_negrisk_convert_candidate(
                                sleeve_source=sl_nr,
                                spec=sp_nrc,
                                dedupe_key=f"{sl_nr[:3]}_{sp_nrc.event_id}_{nr_hit['index_set_bitmask']}",
                                arb_hit={
                                    "mode": nr_hit.get("convert_mode"),
                                    "shares": sh_nr,
                                    "net_edge_per_share": nr_hit["net_edge_per_share"],
                                    "no_legs": no_lgs_emit,
                                    "yes_sell_legs": yes_sells_emit,
                                    "retained_free_yes_brackets": ret_tail_emit,
                                },
                                books_by_token=nr_bks,
                                now_ts=now,
                                fee_bips=nr_fee_bips,
                            )
    except Exception as exc_nr:
        logger.debug(f"Protocol V2 NR4/NR5 scan notice: {exc_nr}")

    # Pillar 4: `MENTION1_CUMULATIVE_LADDER_BOX`
    try:
        is_mocked = bool(getattr(daemon, "single_scan", False) or ("fetch_json" in getattr(daemon, "__dict__", {})))
        if (now - float(daemon.__dict__.get("_last_mention_disc_ts", 0.0))) >= 180.0 and not is_mocked:
            daemon.__dict__["_last_mention_disc_ts"] = now
            gamma_u = getattr(daemon, "GAMMA_URL", "https://gamma-api.polymarket.com")
            m_evts = await daemon.fetch_json(f"{gamma_u}/events?tag_slug=mentions&active=true&closed=false&limit=25", timeout=4.0)
            m_ladders: Dict[str, List[Dict[str, Any]]] = {}
            if isinstance(m_evts, list):
                for ev_m in m_evts:
                    if not isinstance(ev_m, dict):
                        continue
                    by_word: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
                    for mk_m in (ev_m.get("markets") or []):
                        if not isinstance(mk_m, dict) or mk_m.get("closed") or mk_m.get("acceptingOrders") is False:
                            continue
                        q_m = str(mk_m.get("question") or mk_m.get("groupItemTitle") or "")
                        m_cnt = re.search(r"(\d+)\s*\+|at\s+least\s+(\d+)|(\d+)\s+or\s+more", q_m, flags=re.I)
                        if not m_cnt:
                            continue
                        thr = int(next(g for g in m_cnt.groups() if g is not None))
                        stem = re.sub(r"\d+\s*\+|at\s+least\s+\d+|\d+\s+or\s+more", "", q_m.lower()).strip()
                        raw_tks = mk_m.get("clobTokenIds")
                        toks_m = json.loads(raw_tks) if isinstance(raw_tks, str) and raw_tks.startswith("[") else (raw_tks if isinstance(raw_tks, list) else [])
                        end_s = str(mk_m.get("endDate") or ev_m.get("endDate") or "")
                        end_m = datetime.fromisoformat(end_s.replace("Z", "+00:00")).timestamp() if end_s else 0.0
                        if len(toks_m) >= 2 and (120.0 < (end_m - now) <= 172800.0):
                            fs_m = mk_m.get("feeSchedule") or {}
                            fr_m = float(fs_m.get("rate", 0.0) if mk_m.get("feesEnabled", False) else 0.0)
                            fe_m = float(fs_m.get("exponent", 1.0))
                            by_word[f"{ev_m.get('id')}:{stem[:36]}"].append({
                                "min_count": thr,
                                "threshold": thr,
                                "term": stem[:36],
                                "event_id": str(ev_m.get("id") or ""),
                                "market_id": str(mk_m.get("id") or ""),
                                "condition_id": str(mk_m.get("conditionId") or ""),
                                "yes_token_id": str(toks_m[0]),
                                "no_token_id": str(toks_m[1]),
                                "fee_rate": fr_m,
                                "fee_exponent": fe_m,
                                "end_ts": end_m,
                            })
                    for wk, r_list in by_word.items():
                        if len(r_list) >= 2:
                            m_ladders[wk] = r_list
            daemon.__dict__["_mention_ladders"] = m_ladders

        m_lads = daemon.__dict__.get("_mention_ladders") or {}
        if m_lads:
            m_toks = [t for rl in list(m_lads.values())[:15] for r in rl for t in (r["yes_token_id"], r["no_token_id"])]
            m_bks = await daemon.fetch_books_batch(m_toks[:80], timeout=2.5)
            for wk, rl in list(m_lads.items())[:15]:
                enriched_m: List[Dict[str, Any]] = []
                for r in rl:
                    by_m, bn_m = m_bks.get(r["yes_token_id"]), m_bks.get(r["no_token_id"])
                    if not by_m or not bn_m:
                        continue
                    ay_m, sy_m = daemon._best_ask_sz(by_m)
                    an_m, sn_m = daemon._best_ask_sz(bn_m)
                    if ay_m < 1.0 and an_m < 1.0:
                        enriched_m.append({**r, "yes_ask": ay_m, "no_ask": an_m, "yes_ask_size": sy_m, "no_ask_size": sn_m, "bk_yes": by_m, "bk_no": bn_m})
                for hit_m in detect_mention1_cumulative_ladder_box(enriched_m):
                    la_m, lb_m = hit_m["leg_a"], hit_m["leg_b"]
                    ra = next((x for x in enriched_m if x["yes_token_id"] == la_m["token_id"]), None)
                    rb = next((x for x in enriched_m if x["no_token_id"] == lb_m["token_id"]), None)
                    if ra and rb:
                        opps_out.append({
                            "sleeve": "MENTION1_CUMULATIVE_LADDER_BOX",
                            "market": f"MENTION1 {wk[-24:]} ({hit_m['count_low']}+ vs <{hit_m['count_high']})",
                            "ask_vwap": hit_m["cost_per_share"],
                            "p_model": 1.0,
                            "net_edge": hit_m["net_edge_per_share"],
                            "l1_usd": 20.0,
                        })
                        daemon.emit_live_two_leg_box_candidate(
                            box_type="COUNTING_DOMINANCE",
                            sleeve_source="MENTION1_CUMULATIVE_LADDER_BOX",
                            asset="MENTION",
                            dedupe_key=f"MENTION1_{ra['market_id']}_{rb['market_id']}",
                            leg_a={"token_id": ra["yes_token_id"], "opp_token_id": ra["no_token_id"], "label": f"GE_{ra['min_count']}", "side": "YES", "market_id": ra["market_id"], "condition_id": ra["condition_id"], "strike": float(ra["min_count"]), "fee_rate": ra["fee_rate"], "fee_exponent": ra["fee_exponent"], "end_ts": ra["end_ts"]},
                            leg_b={"token_id": rb["no_token_id"], "opp_token_id": rb["yes_token_id"], "label": f"LT_{rb['min_count']}", "side": "NO", "market_id": rb["market_id"], "condition_id": rb["condition_id"], "strike": float(rb["min_count"]), "fee_rate": rb["fee_rate"], "fee_exponent": rb["fee_exponent"], "end_ts": rb["end_ts"]},
                            bk_a=ra["bk_yes"],
                            bk_b=rb["bk_no"],
                            close_ts=float(min(ra["end_ts"], rb["end_ts"])),
                            now_ts=now,
                            max_box_cost_override=0.990,
                            k_low=float(ra["min_count"]),
                            k_high=float(rb["min_count"]),
                        )
    except Exception as exc_m1:
        logger.debug(f"Protocol V2 MENTION1 scan notice: {exc_m1}")

    # Pillar 5: Strictly Pre-Match Dead-Ball Soccer (`DC1` 3-Way Parity & `LP_COMP1` Triangles, `now <= kickoff_ts - 300s`)
    try:
        prematch_soc: List[Tuple[Any, float]] = []
        for tr in (getattr(daemon, "soccer_trees", None) or {}).values():
            kickoff_ts = float(getattr(tr, "start_ts", 0.0) or (float(tr.end_ts) - 9000.0))
            if 300.0 <= (kickoff_ts - now) <= 86400.0:
                prematch_soc.append((tr, kickoff_ts))
        if prematch_soc:
            pm_toks: List[str] = []
            for tr_p, _ in prematch_soc[:15]:
                for lg3 in (tr_p.home_leg, tr_p.draw_leg, tr_p.away_leg):
                    pm_toks.extend((lg3["yes_token"], lg3["no_token"]))
                btts_l = getattr(tr_p, "btts_leg", None)
                if isinstance(btts_l, dict):
                    pm_toks.extend((btts_l.get("yes_token", ""), btts_l.get("no_token", "")))
                for tl in (getattr(tr_p, "totals", None) or []):
                    if abs(float(tl.get("line", 0.0)) - 1.5) <= 1e-6:
                        pm_toks.extend((tl["over_token"], tl["under_token"]))
            pm_bks = await daemon.fetch_books_batch([t for t in pm_toks if t][:80], timeout=2.5)
            for tr_p, kickoff_ts in prematch_soc[:15]:
                bh_y, bh_n = pm_bks.get(tr_p.home_leg["yes_token"]), pm_bks.get(tr_p.home_leg["no_token"])
                bd_y, bd_n = pm_bks.get(tr_p.draw_leg["yes_token"]), pm_bks.get(tr_p.draw_leg["no_token"])
                ba_y, ba_n = pm_bks.get(tr_p.away_leg["yes_token"]), pm_bks.get(tr_p.away_leg["no_token"])
                if not (bh_y and bh_n and bd_y and bd_n and ba_y and ba_n):
                    continue
                hy_p, hy_s = daemon._best_ask_sz(bh_y)
                dy_p, dy_s = daemon._best_ask_sz(bd_y)
                dn_p, dn_s = daemon._best_ask_sz(bd_n)
                ay_p, ay_s = daemon._best_ask_sz(ba_y)
                mids_3w = {
                    str(tr_p.home_leg.get("market_id") or ""),
                    str(tr_p.draw_leg.get("market_id") or ""),
                    str(tr_p.away_leg.get("market_id") or ""),
                }
                if (
                    len(mids_3w) == 3
                    and "" not in mids_3w
                    and 0.005 <= hy_p < 1.0
                    and 0.005 <= dy_p < 1.0
                    and 0.005 <= ay_p < 1.0
                    and min(hy_s, dy_s, ay_s) >= 5.0
                ):
                    qh_3, _, _ = quantize_dynamic_tick_price(hy_p, "BUY", shares=5.0, mode="taker")
                    qd_3, _, _ = quantize_dynamic_tick_price(dy_p, "BUY", shares=5.0, mode="taker")
                    qa_3, _, _ = quantize_dynamic_tick_price(ay_p, "BUY", shares=5.0, mode="taker")
                    fr_3 = max(
                        float(tr_p.home_leg.get("fee_rate", 0.0) or 0.0),
                        float(tr_p.draw_leg.get("fee_rate", 0.0) or 0.0),
                        float(tr_p.away_leg.get("fee_rate", 0.0) or 0.0),
                    )
                    c_3w = (
                        qh_3 + compute_exact_taker_fee_per_share(qh_3, fr_3, 1.0)
                        + qd_3 + compute_exact_taker_fee_per_share(qd_3, fr_3, 1.0)
                        + qa_3 + compute_exact_taker_fee_per_share(qa_3, fr_3, 1.0)
                    )
                    if c_3w <= 0.992:
                        sh_3w = round(min(hy_s, dy_s, ay_s), 2)
                        opps_out.append({
                            "sleeve": "DC1_DOUBLE_CHANCE_1X2_PARITY",
                            "market": f"{tr_p.title[:36]} [1X2_3WAY]",
                            "ask_vwap": round(c_3w, 4),
                            "p_model": 1.0,
                            "net_edge": round(1.0 - c_3w, 4),
                            "l1_usd": round(sh_3w * c_3w, 2),
                        })
                        if hasattr(daemon, "emit_live_special_v2_box_candidate"):
                            daemon.emit_live_special_v2_box_candidate(
                                box_type="MULTI_LEG_BUNDLE",
                                sleeve_source="DC1_DOUBLE_CHANCE_1X2_PARITY",
                                asset="SOCCER",
                                dedupe_key=f"DC1_3W_{tr_p.game_id}",
                                close_ts=float(tr_p.end_ts),
                                now_ts=now,
                                payload={
                                    "legs": [
                                        {"token_id": tr_p.home_leg["yes_token"], "market_id": tr_p.home_leg["market_id"], "condition_id": tr_p.home_leg.get("condition_id", ""), "label": "HOME_YES", "ask_px": qh_3, "ask_size": hy_s, "fee_rate": float(tr_p.home_leg.get("fee_rate", 0.0) or 0.0), "fee_exponent": 1.0, "neg_risk": bool(tr_p.home_leg.get("neg_risk", True))},
                                        {"token_id": tr_p.draw_leg["yes_token"], "market_id": tr_p.draw_leg["market_id"], "condition_id": tr_p.draw_leg.get("condition_id", ""), "label": "DRAW_YES", "ask_px": qd_3, "ask_size": dy_s, "fee_rate": float(tr_p.draw_leg.get("fee_rate", 0.0) or 0.0), "fee_exponent": 1.0, "neg_risk": bool(tr_p.draw_leg.get("neg_risk", True))},
                                        {"token_id": tr_p.away_leg["yes_token"], "market_id": tr_p.away_leg["market_id"], "condition_id": tr_p.away_leg.get("condition_id", ""), "label": "AWAY_YES", "ask_px": qa_3, "ask_size": ay_s, "fee_rate": float(tr_p.away_leg.get("fee_rate", 0.0) or 0.0), "fee_exponent": 1.0, "neg_risk": bool(tr_p.away_leg.get("neg_risk", True))},
                                    ],
                                    "box_cost_net": round(c_3w, 6),
                                    "max_box_cost_net": 0.992,
                                    "max_fillable_shares": sh_3w,
                                    "neg_risk": True,
                                    "game_start_ts": kickoff_ts,
                                },
                            )
                btts_l = getattr(tr_p, "btts_leg", None)
                tot_15 = next((tl for tl in (getattr(tr_p, "totals", None) or []) if abs(float(tl.get("line", 0.0)) - 1.5) <= 1e-6), None)
                if isinstance(btts_l, dict) and isinstance(tot_15, dict):
                    bk_btts_y, bk_btts_n = pm_bks.get(btts_l.get("yes_token", "")), pm_bks.get(btts_l.get("no_token", ""))
                    bk_o15, bk_u15 = pm_bks.get(tot_15.get("over_token", "")), pm_bks.get(tot_15.get("under_token", ""))
                    if bk_btts_y and bk_btts_n and bk_o15 and bk_u15:
                        bty_p, bty_s = daemon._best_ask_sz(bk_btts_y)
                        btn_p, btn_s = daemon._best_ask_sz(bk_btts_n)
                        o15_p, o15_s = daemon._best_ask_sz(bk_o15)
                        u15_p, u15_s = daemon._best_ask_sz(bk_u15)
                        tok_meta_lp = {
                            str(btts_l["yes_token"]): (btts_l.get("market_id", ""), btts_l.get("condition_id", ""), btts_l["no_token"], "YES", bool(btts_l.get("neg_risk", False)), float(btts_l.get("fee_rate", 0.0) or 0.0)),
                            str(btts_l["no_token"]): (btts_l.get("market_id", ""), btts_l.get("condition_id", ""), btts_l["yes_token"], "NO", bool(btts_l.get("neg_risk", False)), float(btts_l.get("fee_rate", 0.0) or 0.0)),
                            str(tot_15["over_token"]): (tot_15.get("market_id", ""), tot_15.get("condition_id", ""), tot_15["under_token"], "YES", bool(tot_15.get("neg_risk", False)), float(tot_15.get("fee_rate", 0.0) or 0.0)),
                            str(tot_15["under_token"]): (tot_15.get("market_id", ""), tot_15.get("condition_id", ""), tot_15["over_token"], "NO", bool(tot_15.get("neg_risk", False)), float(tot_15.get("fee_rate", 0.0) or 0.0)),
                            str(tr_p.draw_leg["no_token"]): (tr_p.draw_leg.get("market_id", ""), tr_p.draw_leg.get("condition_id", ""), tr_p.draw_leg["yes_token"], "NO", bool(tr_p.draw_leg.get("neg_risk", True)), float(tr_p.draw_leg.get("fee_rate", 0.0) or 0.0)),
                        }
                        for tri_h in detect_lp_comp1_sports_triangles(
                            quotes={
                                "BTTS": {"yes_token_id": btts_l["yes_token"], "no_token_id": btts_l["no_token"], "yes_ask": bty_p if bty_p < 1.0 else 0.0, "yes_ask_size": bty_s, "no_ask": btn_p if btn_p < 1.0 else 0.0, "no_ask_size": btn_s, "fee_rate": float(btts_l.get("fee_rate", 0.0) or 0.0)},
                                "OVER_1_5": {"yes_token_id": tot_15["over_token"], "yes_ask": o15_p if o15_p < 1.0 else 0.0, "yes_ask_size": o15_s, "fee_rate": float(tot_15.get("fee_rate", 0.0) or 0.0)},
                                "UNDER_1_5": {"yes_token_id": tot_15["under_token"], "yes_ask": u15_p if u15_p < 1.0 else 0.0, "yes_ask_size": u15_s, "fee_rate": float(tot_15.get("fee_rate", 0.0) or 0.0)},
                                "DRAW": {"no_token_id": tr_p.draw_leg["no_token"], "no_ask": dn_p if dn_p < 1.0 else 0.0, "no_ask_size": dn_s, "fee_rate": float(tr_p.draw_leg.get("fee_rate", 0.0) or 0.0)},
                            },
                            event_title=tr_p.title,
                            expiry_ts=float(tr_p.end_ts),
                            market_id=str(tr_p.draw_leg.get("market_id") or ""),
                            is_live_in_play=False,
                        ):
                            opps_out.append({
                                "sleeve": "LP_COMP1_SPORTS_TRIANGLES",
                                "market": f"{tr_p.title[:36]} [{tri_h['triangle_id']}]",
                                "ask_vwap": tri_h["cost_per_share"],
                                "p_model": 1.0,
                                "net_edge": tri_h["net_edge_per_share"],
                                "l1_usd": round(tri_h["max_fillable_shares"] * tri_h["cost_per_share"], 2),
                            })
                            t_legs = list(tri_h.get("legs") or ([tri_h["leg_a"], tri_h["leg_b"]] if ("leg_a" in tri_h and "leg_b" in tri_h) else []))
                            if len(t_legs) == 2:
                                ta_lp, tb_lp = str(t_legs[0]["token_id"]), str(t_legs[1]["token_id"])
                                ma_lp, ca_lp, oa_lp, sa_lp, nra_lp, fra_lp = tok_meta_lp.get(ta_lp, ("", "", "", "YES", False, 0.0))
                                mb_lp, cb_lp, ob_lp, sb_lp, nrb_lp, frb_lp = tok_meta_lp.get(tb_lp, ("", "", "", "YES", False, 0.0))
                                bka_lp, bkb_lp = pm_bks.get(ta_lp), pm_bks.get(tb_lp)
                                if ma_lp and mb_lp and ma_lp != mb_lp and bka_lp and bkb_lp:
                                    daemon.emit_live_two_leg_box_candidate(
                                        box_type="SPORTS_CORRIDOR",
                                        sleeve_source="LP_COMP1_SPORTS_TRIANGLES",
                                        asset="SOCCER",
                                        dedupe_key=f"LPCOMP1_{tr_p.game_id}_{tri_h['triangle_id']}",
                                        leg_a={"token_id": ta_lp, "opp_token_id": oa_lp, "label": t_legs[0].get("role", "LEG_A"), "side": sa_lp, "market_id": ma_lp, "condition_id": ca_lp, "fee_rate": fra_lp, "fee_exponent": 1.0, "neg_risk": nra_lp, "end_ts": tr_p.end_ts},
                                        leg_b={"token_id": tb_lp, "opp_token_id": ob_lp, "label": t_legs[1].get("role", "LEG_B"), "side": sb_lp, "market_id": mb_lp, "condition_id": cb_lp, "fee_rate": frb_lp, "fee_exponent": 1.0, "neg_risk": nrb_lp, "end_ts": tr_p.end_ts},
                                        bk_a=bka_lp,
                                        bk_b=bkb_lp,
                                        close_ts=float(tr_p.end_ts),
                                        now_ts=now,
                                        max_box_cost_override=0.990,
                                        extra_fields={"game_start_ts": kickoff_ts, "game_phase": "PREGAME"},
                                    )
                            elif len(t_legs) >= 3 and hasattr(daemon, "emit_live_special_v2_box_candidate"):
                                enr_legs = []
                                for lg_t in t_legs:
                                    tk_t = str(lg_t.get("token_id") or "")
                                    mt_t, ct_t, _, _, nrt_t, frt_t = tok_meta_lp.get(tk_t, ("", "", "", "YES", False, 0.0))
                                    enr_legs.append({**lg_t, "market_id": mt_t, "condition_id": ct_t, "neg_risk": nrt_t, "fee_rate": frt_t, "fee_exponent": 1.0})
                                if len({x["market_id"] for x in enr_legs if x["market_id"]}) == len(enr_legs):
                                    daemon.emit_live_special_v2_box_candidate(
                                        box_type="MULTI_LEG_BUNDLE",
                                        sleeve_source="LP_COMP1_SPORTS_TRIANGLES",
                                        asset="SOCCER",
                                        dedupe_key=f"LPCOMP1_{tr_p.game_id}_{tri_h['triangle_id']}",
                                        close_ts=float(tr_p.end_ts),
                                        now_ts=now,
                                        payload={
                                            "legs": enr_legs,
                                            "box_cost_net": tri_h["cost_per_share"],
                                            "max_box_cost_net": 0.990,
                                            "max_fillable_shares": tri_h["max_fillable_shares"],
                                            "neg_risk": False,
                                            "game_start_ts": kickoff_ts,
                                        },
                                    )
    except Exception as exc_soc:
        logger.debug(f"Protocol V2 Soccer DC1/LP_COMP1 scan notice: {exc_soc}")

    # Pillar 7: `W_PRUNE1` Monotonic METAR Ratchet (`W_PRUNE1_DEAD_NO_BOND`, `W_SOLAR1_POST_2351_LOCK`, `W_PRUNE1_NR0_BASKET`)
    try:
        is_mocked_w = bool(getattr(daemon, "single_scan", False) or ("fetch_json" in getattr(daemon, "__dict__", {})))
        w_evts = [
            sp_w
            for sp_w in (getattr(daemon, "weather_events", None) or {}).values()
            if str(getattr(sp_w, "metric", "") or "").upper() in {"HIGH", "LOW"} and len(getattr(sp_w, "buckets", ()) or ()) >= 3
        ]
        if w_evts and not is_mocked_w and (now - float(daemon.__dict__.get("_last_w_prune1_scan_ts", 0.0))) >= 15.0:
            daemon.__dict__["_last_w_prune1_scan_ts"] = now
            from src.polymarket_research.weather_metar_engine import fetch_metar_observations_sync
            now_utc_w = datetime.fromtimestamp(now, tz=timezone.utc)
            w_active: List[Tuple[float, Any, Any]] = []
            for sp_w in w_evts:
                end_w = resolve_weather_effective_end_ts(sp_w, now + 86400.0)
                if not (120.0 < (end_w - now) <= 86400.0):
                    continue
                try:
                    loc_dt = now_utc_w.astimezone(ZoneInfo(sp_w.tz_name))
                except Exception:
                    loc_dt = now_utc_w
                if loc_dt.date() != sp_w.obs_date:
                    continue
                w_active.append((end_w, sp_w, loc_dt))
            w_active.sort(key=lambda r: r[0])
            w_ready: List[Tuple[Any, float, Tuple[int, int], List[str], Optional[float], bool]] = []
            w_toks: List[str] = []
            m_cache = getattr(daemon, "metar_cache", None)
            for end_w, sp_w, loc_dt in w_active[:30]:
                m_key = f"{sp_w.icao}_{sp_w.obs_date.isoformat()}"
                c_ent = m_cache.get(m_key) if isinstance(m_cache, dict) else None
                if c_ent is None or (now - float(c_ent[0])) >= 300.0:
                    obs_l = await asyncio.to_thread(fetch_metar_observations_sync, sp_w.icao, sp_w.obs_date, sp_w.tz_name)
                    if isinstance(m_cache, dict):
                        m_cache[m_key] = (now, obs_l)
                else:
                    obs_l = c_ent[1]
                if any(bool(getattr(m, "is_corrected", False)) for m in (obs_l or [])):
                    continue
                valid_obs = list(obs_l or [])
                raw_lines = [str(m.raw_line) for m in valid_obs if getattr(m, "raw_line", None)]
                cur_tc = float(valid_obs[-1].temp_c) if (valid_obs and getattr(valid_obs[-1], "temp_c", None) is not None) else None
                cur_tg = bool(getattr(valid_obs[-1], "has_t_remark", False)) if valid_obs else False
                if not raw_lines and cur_tc is None:
                    continue
                loc_hm = (loc_dt.hour, loc_dt.minute)
                w_ready.append((sp_w, end_w, loc_hm, raw_lines, cur_tc, cur_tg))
                for bk_spec in sp_w.buckets:
                    w_toks.extend((bk_spec.yes_token, bk_spec.no_token))
            if w_ready and w_toks:
                w_bks = await daemon.fetch_books_batch(list(dict.fromkeys(w_toks))[:200], timeout=2.5)
                for sp_w, end_w, loc_hm, raw_lines, cur_tc, cur_tg in w_ready:
                    m_mode_w = str(getattr(sp_w, "metric", "HIGH") or "HIGH").upper()
                    br_rows: List[Dict[str, Any]] = []
                    bk_by_mkt: Dict[str, Tuple[Any, Dict[str, Any], Dict[str, Any]]] = {}
                    for b_sp in sp_w.buckets:
                        by_w2, bn_w2 = w_bks.get(b_sp.yes_token), w_bks.get(b_sp.no_token)
                        if not by_w2 or not bn_w2:
                            br_rows = []
                            break
                        ya_w, ys_w = daemon._best_ask_sz(by_w2)
                        na_w, ns_w = daemon._best_ask_sz(bn_w2)
                        bk_by_mkt[str(b_sp.condition_id)] = (b_sp, by_w2, bn_w2)
                        br_rows.append({
                            "label": b_sp.label,
                            "market_id": b_sp.market_id,
                            "condition_id": b_sp.condition_id,
                            "yes_token_id": b_sp.yes_token,
                            "no_token_id": b_sp.no_token,
                            "low": int(round(b_sp.low_bound)) if math.isfinite(b_sp.low_bound) else None,
                            "high": int(round(b_sp.high_bound)) if math.isfinite(b_sp.high_bound) else None,
                            "yes_ask": ya_w if ya_w < 1.0 else 0.0,
                            "yes_ask_size": ys_w,
                            "no_ask": na_w if na_w < 1.0 else 0.0,
                            "no_ask_size": ns_w,
                            "expiry_ts": end_w,
                        })
                    if not br_rows:
                        continue
                    _w_rules = str(getattr(sp_w, "rules_text", "") or getattr(sp_w, "description", "") or getattr(sp_w, "title", "") or "")
                    ext_w = compute_running_metar_extrema(
                        raw_lines,
                        unit=sp_w.unit,
                        current_temp_c=cur_tc,
                        current_has_t_group=cur_tg,
                        station_icao=sp_w.icao,
                        rules_text=_w_rules,
                    )
                    floor_w = int(ext_w["confirmed_running_high_floor"]) if ext_w else None
                    ceil_lo_w = int(ext_w["confirmed_running_low_ceil"]) if ext_w else None
                    hits_w = detect_w_prune1_metar_slate_arb(
                        br_rows,
                        raw_lines,
                        station_icao=sp_w.icao,
                        unit=sp_w.unit,
                        metric=m_mode_w,
                        local_hour_minute=loc_hm,
                        event_meta={"negRiskAugmented": False},
                        min_net_edge_usd=0.0025,
                        current_temp_c=cur_tc,
                        current_has_t_group=cur_tg,
                        rules_text=_w_rules,
                    )
                    taker_cids: set = set()
                    for hw in hits_w:
                        sl_w = str(hw["sleeve"])
                        if sl_w in {"W_PRUNE1_DEAD_NO_BOND", "W_SOLAR1_POST_2351_LOCK"}:
                            cid_w = str(hw["condition_id"])
                            tup_w = bk_by_mkt.get(cid_w)
                            if not tup_w:
                                continue
                            b_sp, by_w2, bn_w2 = tup_w
                            is_no_w = sl_w == "W_PRUNE1_DEAD_NO_BOND"
                            taker_cids.add(cid_w)
                            opps_out.append({
                                "sleeve": sl_w,
                                "market": f"{sp_w.city} ({sp_w.icao}) {b_sp.label} [{'NO' if is_no_w else 'YES'}]",
                                "ask_vwap": hw["ask_px"],
                                "p_model": hw["p_model"],
                                "net_edge": hw["net_edge_per_share"],
                                "l1_usd": round(hw["max_fillable_shares"] * hw["ask_px"], 2),
                            })
                            recycle_998_sh = sum(
                                float(b.get("size", 0.0) if isinstance(b, Mapping) else b[1])
                                for b in ((bn_w2 if is_no_w else by_w2).get("bids") or [])
                                if float((b.get("price", 0.0) if isinstance(b, Mapping) else b[0]) or 0.0) >= 0.998
                            )
                            if is_no_w and (end_w - now) > 7200.0 and recycle_998_sh < 5.0:
                                continue
                            daemon.emit_live_single_leg_lock_candidate(
                                sleeve_source=sl_w,
                                asset=sp_w.icao,
                                dedupe_key=f"{sl_w[:8]}_{b_sp.market_id}",
                                token_id=b_sp.no_token if is_no_w else b_sp.yes_token,
                                opp_token_id=b_sp.yes_token if is_no_w else b_sp.no_token,
                                market_id=b_sp.market_id,
                                condition_id=b_sp.condition_id,
                                side_label="NO" if is_no_w else "YES",
                                display_label=f"{sp_w.city} {b_sp.label} {'DEAD_NO' if is_no_w else 'SOLAR_YES'}",
                                bk_win=bn_w2 if is_no_w else by_w2,
                                bk_opp=by_w2 if is_no_w else bn_w2,
                                fee_rate=float(getattr(b_sp, "fee_rate", 0.0) or 0.0),
                                fee_exponent=1.0,
                                neg_risk=bool(b_sp.neg_risk if b_sp.neg_risk is not None else True),
                                close_ts=end_w,
                                now_ts=now,
                                max_lock_eff_px=0.9975 if is_no_w else 0.9960,
                                max_opp_bid=0.008,
                                hold_to_maturity=True,
                                p_model=float(hw["p_model"]),
                            )
                        elif sl_w == "W_PRUNE1_NR0_BASKET" and len(hw.get("legs") or []) >= 2 and (end_w - now) <= 7200.0:
                            enr_w_legs = []
                            for lg_w in hw["legs"]:
                                tup_lw = bk_by_mkt.get(str(lg_w.get("condition_id") or ""))
                                if tup_lw:
                                    b_lw = tup_lw[0]
                                    enr_w_legs.append({**lg_w, "market_id": b_lw.market_id, "opp_token_id": b_lw.no_token, "label": b_lw.label, "fee_rate": float(getattr(b_lw, "fee_rate", 0.0) or 0.0), "fee_exponent": 1.0, "neg_risk": True, "bk_yes": tup_lw[1]})
                            if len(enr_w_legs) == len(hw["legs"]):
                                opps_out.append({
                                    "sleeve": sl_w,
                                    "market": f"{sp_w.city} ({sp_w.icao}) Pruned Basket ({len(enr_w_legs)} alive)",
                                    "ask_vwap": hw["cost_per_share"],
                                    "p_model": 1.0,
                                    "net_edge": hw["net_edge_per_share"],
                                    "l1_usd": round(hw["max_fillable_shares"] * hw["cost_per_share"], 2),
                                })
                                if len(enr_w_legs) == 2 and hasattr(daemon, "emit_live_two_leg_box_candidate"):
                                    la_w, lb_w = enr_w_legs[0], enr_w_legs[1]
                                    daemon.emit_live_two_leg_box_candidate(
                                        box_type="NEGRISK_2LEG",
                                        sleeve_source=sl_w,
                                        asset=sp_w.icao,
                                        dedupe_key=f"WPRUNE_2L_{sp_w.event_id}",
                                        leg_a={"token_id": la_w["token_id"], "opp_token_id": la_w["opp_token_id"], "label": la_w["label"], "side": "YES", "market_id": la_w["market_id"], "condition_id": la_w["condition_id"], "fee_rate": la_w["fee_rate"], "fee_exponent": 1.0, "neg_risk": True, "end_ts": end_w},
                                        leg_b={"token_id": lb_w["token_id"], "opp_token_id": lb_w["opp_token_id"], "label": lb_w["label"], "side": "YES", "market_id": lb_w["market_id"], "condition_id": lb_w["condition_id"], "fee_rate": lb_w["fee_rate"], "fee_exponent": 1.0, "neg_risk": True, "end_ts": end_w},
                                        bk_a=la_w["bk_yes"],
                                        bk_b=lb_w["bk_yes"],
                                        close_ts=end_w,
                                        now_ts=now,
                                        max_box_cost_override=0.992,
                                    )
                                elif len(enr_w_legs) >= 3 and hasattr(daemon, "emit_live_special_v2_box_candidate"):
                                    daemon.emit_live_special_v2_box_candidate(
                                        box_type="MULTI_LEG_BUNDLE",
                                        sleeve_source=sl_w,
                                        asset=sp_w.icao,
                                        dedupe_key=f"WPRUNE_BSK_{sp_w.event_id}",
                                        close_ts=end_w,
                                        now_ts=now,
                                        payload={
                                            "legs": [{k: v for k, v in x.items() if k != "bk_yes"} for x in enr_w_legs],
                                            "box_cost_net": hw["cost_per_share"],
                                            "max_box_cost_net": 0.992,
                                            "max_fillable_shares": hw["max_fillable_shares"],
                                            "neg_risk": True,
                                        },
                                    )
                    # Post 0%-fee Maker bids (`<= $0.9975`) on METAR-dead `NO` brackets only when `TTE <= 120m` (`7200s`)!
                    if (end_w - now) <= 7200.0 and hasattr(daemon, "emit_live_single_leg_maker_lock_candidate"):
                        for b_sp, by_w2, bn_w2 in bk_by_mkt.values():
                            if str(b_sp.condition_id) in taker_cids:
                                continue
                            dead_mkr = (
                                (m_mode_w == "HIGH" and floor_w is not None and math.isfinite(b_sp.high_bound) and int(round(b_sp.high_bound)) < floor_w)
                                or (m_mode_w == "LOW" and ceil_lo_w is not None and math.isfinite(b_sp.low_bound) and int(round(b_sp.low_bound)) > ceil_lo_w)
                            )
                            if dead_mkr:
                                nb_w, nb_u_w = _extr_best_bid(bn_w2.get("bids") or [])
                                yb_w, _ = _extr_best_bid(by_w2.get("bids") or [])
                                if 0.940 <= nb_w <= 0.9975 and nb_u_w >= 10.0 and yb_w <= 0.006:
                                    daemon.emit_live_single_leg_maker_lock_candidate(
                                        sleeve_source="W_PRUNE1_DEAD_NO_BOND",
                                        asset=sp_w.icao,
                                        dedupe_key=f"W_PRUNE1_MKR_{b_sp.market_id}",
                                        pair_dedupe_key=f"W_PRUNE1_{b_sp.market_id}",
                                        token_id=b_sp.no_token,
                                        opp_token_id=b_sp.yes_token,
                                        market_id=b_sp.market_id,
                                        condition_id=b_sp.condition_id,
                                        side_label="NO",
                                        display_label=f"{sp_w.city} {b_sp.label} DEAD_NO",
                                        bk_win=bn_w2,
                                        bk_opp=by_w2,
                                        neg_risk=bool(b_sp.neg_risk if b_sp.neg_risk is not None else True),
                                        close_ts=end_w,
                                        now_ts=now,
                                        min_resting_bid=0.940,
                                        max_resting_bid=0.9975,
                                        min_maker_edge=0.0024,
                                        max_opp_bid=0.006,
                                        hold_to_maturity=True,
                                        p_model=0.9999,
                                    )
    except Exception as exc_wp:
        logger.debug(f"Protocol V2 W_PRUNE1 scan notice: {exc_wp}")

    # Pillar 6: Full-Universe `1,200+` Market `C1_BINARY_COMPLETE_SET` & `CTF_OVERROUND_MINT_SELL` (WS + Rotating Batch)
    try:
        is_mocked_6 = bool(getattr(daemon, "single_scan", False) or ("fetch_json" in getattr(daemon, "__dict__", {})))
        if not is_mocked_6:
            cand_bins: Dict[str, Dict[str, Any]] = {}

            def _reg_bin(mid_b: Any, cid_b: Any, yt_b: Any, nt_b: Any, fr_b: float, fe_b: float, nr_b: bool, exp_b: float, ast_b: str) -> None:
                c_s, y_s, n_s = str(cid_b or ""), str(yt_b or ""), str(nt_b or "")
                if not c_s or not y_s or not n_s or y_s == n_s or exp_b <= now + 30.0:
                    return
                if c_s not in cand_bins:
                    cand_bins[c_s] = {
                        "market_id": str(mid_b or ""), "condition_id": c_s, "yes_token_id": y_s, "no_token_id": n_s,
                        "fee_rate": float(fr_b or 0.0), "fee_exponent": float(fe_b or 1.0), "neg_risk": bool(nr_b),
                        "end_ts": float(exp_b), "asset": str(ast_b or "BINARY")[:16],
                    }

            for reg_nm in ("pyth_daily_markets", "daily_updown_markets", "twap_candles", "barrier_rungs", "pyth_barrier_rungs"):
                for sp_x in list((getattr(daemon, reg_nm, None) or {}).values()):
                    _reg_bin(
                        getattr(sp_x, "market_id", ""), getattr(sp_x, "condition_id", ""),
                        getattr(sp_x, "up_token", None) or getattr(sp_x, "yes_token", ""),
                        getattr(sp_x, "down_token", None) or getattr(sp_x, "no_token", ""),
                        float(getattr(sp_x, "fee_rate", 0.0) or 0.0), float(getattr(sp_x, "fee_exponent", 1.0) or 1.0),
                        bool(getattr(sp_x, "neg_risk", False)), float(getattr(sp_x, "end_ts", 0.0) or 0.0),
                        str(getattr(sp_x, "asset", "CRYPTO")),
                    )
            for lad_nm in ("strike_ladders", "pyth_close_ladders"):
                for r_ls in list((getattr(daemon, lad_nm, None) or {}).values()):
                    for sp_r in (r_ls or ()):
                        _reg_bin(
                            getattr(sp_r, "market_id", ""), getattr(sp_r, "condition_id", ""),
                            getattr(sp_r, "yes_token", ""), getattr(sp_r, "no_token", ""),
                            float(getattr(sp_r, "fee_rate", 0.07) or 0.0), float(getattr(sp_r, "fee_exponent", 1.0) or 1.0),
                            bool(getattr(sp_r, "neg_risk", False)), float(getattr(sp_r, "end_ts", 0.0) or 0.0),
                            str(getattr(sp_r, "asset", "CRYPTO")),
                        )
            for sp_bn in list(getattr(daemon, "binance_close_rungs", None) or ()):
                _reg_bin(
                    getattr(sp_bn, "market_id", ""), getattr(sp_bn, "condition_id", ""),
                    getattr(sp_bn, "yes_token", ""), getattr(sp_bn, "no_token", ""),
                    float(getattr(sp_bn, "fee_rate", 0.0) or 0.0), 1.0, False,
                    float(getattr(sp_bn, "end_ts", 0.0) or 0.0), str(getattr(sp_bn, "asset", "CRYPTO")),
                )
            for d_leg in list(getattr(daemon, "fomc_truth_legs", None) or ()) + list(getattr(daemon, "lp1_bop_legs", None) or ()):
                if isinstance(d_leg, Mapping):
                    _reg_bin(
                        d_leg.get("market_id", ""), d_leg.get("condition_id", ""),
                        d_leg.get("yes_token", ""), d_leg.get("no_token", ""),
                        float(d_leg.get("fee_rate", 0.0) or 0.0), 1.0, bool(d_leg.get("neg_risk", False)),
                        float(d_leg.get("end_ts", 0.0) or 0.0), str(d_leg.get("asset") or "MACRO"),
                    )

            bin_rows: List[Dict[str, Any]] = []
            rest_need: List[Dict[str, Any]] = []
            has_ws_fn = hasattr(daemon, "_get_fresh_ws_book") and bool(getattr(daemon, "_ws_books", None))
            for meta_b in cand_bins.values():
                by_w = daemon._get_fresh_ws_book(meta_b["yes_token_id"], now, max_age_sec=6.0) if has_ws_fn else None
                bn_w = daemon._get_fresh_ws_book(meta_b["no_token_id"], now, max_age_sec=6.0) if has_ws_fn else None
                if by_w and bn_w:
                    yb_p, yb_u = _extr_best_bid(by_w.get("bids") or [])
                    nb_p, nb_u = _extr_best_bid(bn_w.get("bids") or [])
                    ya_p, ya_s = daemon._best_ask_sz(by_w)
                    na_p, na_s = daemon._best_ask_sz(bn_w)
                    bin_rows.append({
                        **meta_b,
                        "yes_bid": yb_p, "yes_bid_size": (yb_u / yb_p) if yb_p > 0 else 0.0,
                        "no_bid": nb_p, "no_bid_size": (nb_u / nb_p) if nb_p > 0 else 0.0,
                        "yes_ask": ya_p if ya_p < 1.0 else 0.0, "yes_ask_size": ya_s,
                        "no_ask": na_p if na_p < 1.0 else 0.0, "no_ask_size": na_s,
                        "bk_yes": by_w, "bk_no": bn_w,
                    })
                else:
                    rest_need.append(meta_b)

            if rest_need and hasattr(daemon, "fetch_books_batch") and (now - float(daemon.__dict__.get("_last_c1_rot_ts", 0.0))) >= 4.0:
                daemon.__dict__["_last_c1_rot_ts"] = now
                cur_idx = int(daemon.__dict__.get("_c1_rot_cursor", 0) or 0) % max(1, len(rest_need))
                batch_m = (rest_need[cur_idx : cur_idx + 24] + rest_need[: max(0, cur_idx + 24 - len(rest_need))])[:24]
                daemon.__dict__["_c1_rot_cursor"] = (cur_idx + 24) % max(1, len(rest_need))
                rot_toks = [t for m_x in batch_m for t in (m_x["yes_token_id"], m_x["no_token_id"])]
                rot_bks = await daemon.fetch_books_batch(rot_toks, timeout=2.0)
                for meta_b in batch_m:
                    by_r, bn_r = rot_bks.get(meta_b["yes_token_id"]), rot_bks.get(meta_b["no_token_id"])
                    if by_r and bn_r:
                        yb_p, yb_u = _extr_best_bid(by_r.get("bids") or [])
                        nb_p, nb_u = _extr_best_bid(bn_r.get("bids") or [])
                        ya_p, ya_s = daemon._best_ask_sz(by_r)
                        na_p, na_s = daemon._best_ask_sz(bn_r)
                        bin_rows.append({
                            **meta_b,
                            "yes_bid": yb_p, "yes_bid_size": (yb_u / yb_p) if yb_p > 0 else 0.0,
                            "no_bid": nb_p, "no_bid_size": (nb_u / nb_p) if nb_p > 0 else 0.0,
                            "yes_ask": ya_p if ya_p < 1.0 else 0.0, "yes_ask_size": ya_s,
                            "no_ask": na_p if na_p < 1.0 else 0.0, "no_ask_size": na_s,
                            "bk_yes": by_r, "bk_no": bn_r,
                        })

            if bin_rows:
                by_cid_r = {x["condition_id"]: x for x in bin_rows}
                for ov_hit in scan_full_universe_c1_and_ctf_overround(bin_rows, min_overround_edge=0.0045):
                    src_r = by_cid_r.get(str(ov_hit.get("condition_id") or ""))
                    if not src_r:
                        continue
                    if ov_hit.get("sleeve") == "CTF_OVERROUND_MINT_SELL" and not src_r["neg_risk"]:
                        rev_ps = float(ov_hit.get("net_revenue_per_share") or ov_hit.get("net_proceeds_per_share") or 1.005)
                        opps_out.append({
                            "sleeve": "CTF_OVERROUND_MINT_SELL",
                            "market": f"{src_r['asset']} Binary Overround (${rev_ps:.4f})",
                            "ask_vwap": round(2.0 - rev_ps, 4),
                            "p_model": 1.0,
                            "net_edge": float(ov_hit["net_edge_per_share"]),
                            "l1_usd": round(float(ov_hit["max_fillable_shares"]), 2),
                        })
                        daemon.emit_live_special_v2_box_candidate(
                            box_type="CTF_OVERROUND",
                            sleeve_source="CTF_OVERROUND_MINT_SELL",
                            asset=src_r["asset"],
                            dedupe_key=f"CTFOVR_{src_r['market_id']}_{int(now // 15)}",
                            close_ts=src_r["end_ts"],
                            now_ts=now,
                            payload={
                                "condition_id": src_r["condition_id"],
                                "leg_a_market_id": src_r["market_id"],
                                "yes_token_id": src_r["yes_token_id"],
                                "no_token_id": src_r["no_token_id"],
                                "yes_bid": ov_hit["yes_bid"],
                                "no_bid": ov_hit["no_bid"],
                                "fee_rate": src_r["fee_rate"],
                                "fee_exponent": src_r["fee_exponent"],
                                "max_fillable_shares": ov_hit["max_fillable_shares"],
                                "box_cost_net": round(2.0 - rev_ps, 4),
                            },
                        )
                    elif ov_hit.get("sleeve") == "C1_BINARY_COMPLETE_SET":
                        opps_out.append({
                            "sleeve": "C1_BINARY_COMPLETE_SET",
                            "market": f"{src_r['asset']} Binary Complete Set (${ov_hit['cost_per_share']:.4f})",
                            "ask_vwap": float(ov_hit["cost_per_share"]),
                            "p_model": 1.0,
                            "net_edge": float(ov_hit["net_edge_per_share"]),
                            "l1_usd": round(float(ov_hit["max_fillable_shares"]) * float(ov_hit["cost_per_share"]), 2),
                        })
                        daemon.emit_live_two_leg_box_candidate(
                            box_type="COMPLETE_SET",
                            sleeve_source="C1_BINARY_COMPLETE_SET",
                            asset=src_r["asset"],
                            dedupe_key=f"C1V2_{src_r['market_id']}",
                            leg_a={"token_id": src_r["yes_token_id"], "opp_token_id": src_r["no_token_id"], "label": "YES", "side": "YES", "market_id": src_r["market_id"], "condition_id": src_r["condition_id"], "fee_rate": src_r["fee_rate"], "fee_exponent": src_r["fee_exponent"], "neg_risk": src_r["neg_risk"], "end_ts": src_r["end_ts"]},
                            leg_b={"token_id": src_r["no_token_id"], "opp_token_id": src_r["yes_token_id"], "label": "NO", "side": "NO", "market_id": src_r["market_id"], "condition_id": src_r["condition_id"], "fee_rate": src_r["fee_rate"], "fee_exponent": src_r["fee_exponent"], "neg_risk": src_r["neg_risk"], "end_ts": src_r["end_ts"]},
                            bk_a=src_r["bk_yes"],
                            bk_b=src_r["bk_no"],
                            close_ts=src_r["end_ts"],
                            now_ts=now,
                            max_box_cost_override=0.992,
                        )
    except Exception as exc_c1:
        logger.debug(f"Protocol V2 C1/CTF_OVERROUND scan notice: {exc_c1}")

    # Pillar 8: Zero-Byte Live Bridge for Native Verified Zero-Loss Shadow Positions (`B3`, `B4`, `D2`, `GAS1`, `SUM1`, 3+ leg `N1` & `LP1`)
    try:
        is_mocked_8 = bool(getattr(daemon, "single_scan", False) or ("fetch_json" in getattr(daemon, "__dict__", {})))
        open_map = getattr(daemon, "open_positions", None) or {}
        if not is_mocked_8 and open_map and hasattr(daemon, "fetch_books_batch"):
            bridge_2l = {"B3_BARRIER_MONO_BOX": "BARRIER_MONO", "D2_12PM_BINANCE_BOX": "CROSS_BASIS_DOMINANCE"}
            bridge_1l = {"B4_TOUCHED_BARRIER_WICK_LOCK", "GAS1_AAA_GASOLINE_LOCK"}
            bridge_ml = {"N1_NEGRISK_CROSS_BOX", "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "SUM1_FRECHET_SUM_TRIANGLES"}
            cand_pos = [
                p for p in list(open_map.values())
                if isinstance(p, Mapping)
                and p.get("status") == "OPEN"
                and (now - float(p.get("entry_ts") or 0.0)) <= 45.0
                and 30.0 < (float(p.get("close_ts") or 0.0) - now) <= 172800.0
                and str(p.get("sleeve") or "") in (set(bridge_2l) | bridge_1l | bridge_ml)
                and str(p.get("position_id") or "") not in daemon.__dict__.setdefault("_bridged_native_pos_ids", set())
            ]
            if cand_pos:
                need_b8: List[str] = []
                for p8 in cand_pos[:10]:
                    ex8 = p8.get("extra") or {}
                    if isinstance(ex8.get("leg_a"), Mapping) and isinstance(ex8.get("leg_b"), Mapping):
                        need_b8.extend([str(ex8["leg_a"].get("token_id") or ""), str(ex8["leg_b"].get("token_id") or "")])
                    elif isinstance(ex8.get("legs"), list):
                        need_b8.extend([str(lg8.get("token_id") or "") for lg8 in ex8["legs"]])
                    else:
                        need_b8.extend([str(p8.get("token_id") or ""), str(ex8.get("opp_token_id") or "")])
                bks_8 = await daemon.fetch_books_batch([t for t in dict.fromkeys(need_b8) if t and "|" not in t][:40], timeout=2.0)
                for p8 in cand_pos[:10]:
                    pid8 = str(p8.get("position_id") or "")
                    sl8 = str(p8.get("sleeve") or "")
                    ex8 = p8.get("extra") or {}
                    cl8 = float(p8.get("close_ts") or 0.0)
                    ast8 = str(p8.get("asset_or_city") or sl8[:4])
                    daemon.__dict__["_bridged_native_pos_ids"].add(pid8)
                    if sl8 in bridge_2l and isinstance(ex8.get("leg_a"), Mapping) and isinstance(ex8.get("leg_b"), Mapping):
                        la8, lb8 = dict(ex8["leg_a"]), dict(ex8["leg_b"])
                        ba8, bb8 = bks_8.get(str(la8.get("token_id") or "")), bks_8.get(str(lb8.get("token_id") or ""))
                        if ba8 and bb8:
                            daemon.emit_live_two_leg_box_candidate(
                                sleeve_source=sl8, box_type=bridge_2l[sl8], asset=ast8,
                                dedupe_key=str(p8.get("dedupe_key") or pid8),
                                leg_a=la8, leg_b=lb8, bk_a=ba8, bk_b=bb8, close_ts=cl8, now_ts=now,
                                max_box_cost_override=0.990 if sl8 == "B3_BARRIER_MONO_BOX" else 0.988,
                            )
                    elif sl8 in bridge_1l:
                        tk8 = str(p8.get("token_id") or "")
                        op8 = str(ex8.get("opp_token_id") or ex8.get("no_token") or "")
                        bw8, bo8 = bks_8.get(tk8), bks_8.get(op8)
                        if bw8 and op8 and float(p8.get("p_model_entry") or 0.0) >= 0.998:
                            daemon.emit_live_single_leg_lock_candidate(
                                sleeve_source=sl8, asset=ast8, dedupe_key=str(p8.get("dedupe_key") or pid8),
                                token_id=tk8, opp_token_id=op8, market_id=str(ex8.get("market_id") or ""),
                                condition_id=str(ex8.get("condition_id") or ""), side_label=str(p8.get("side") or "YES"),
                                display_label=str(p8.get("title") or sl8)[:56], bk_win=bw8, bk_opp=bo8,
                                fee_rate=float(p8.get("fee_rate") or 0.0), fee_exponent=float(ex8.get("fee_exponent") or 1.0),
                                neg_risk=bool(ex8.get("neg_risk", False)), close_ts=cl8, now_ts=now,
                                max_lock_eff_px=0.992, max_opp_bid=0.015, hold_to_maturity=True, p_model=float(p8.get("p_model_entry") or 0.999),
                            )
                    elif sl8 in bridge_ml and isinstance(ex8.get("legs"), list) and len(ex8["legs"]) >= 3 and abs(float(ex8.get("guaranteed_payout") or 1.0) - 1.0) <= 1e-6:
                        lgs8 = []
                        for lg_x in ex8["legs"]:
                            bk_x = bks_8.get(str(lg_x.get("token_id") or ""))
                            if bk_x:
                                ax_p, ax_s = daemon._best_ask_sz(bk_x)
                                if ax_p < 1.0 and ax_s >= 5.0:
                                    lgs8.append({**lg_x, "ask_px": ax_p, "ask_size": ax_s})
                        if len(lgs8) == len(ex8["legs"]):
                            c8 = sum(float(x["ask_px"]) + compute_exact_taker_fee_per_share(float(x["ask_px"]), float(x.get("fee_rate", 0.0) or 0.0), 1.0) for x in lgs8)
                            if c8 <= 0.990:
                                daemon.emit_live_special_v2_box_candidate(
                                    box_type="MULTI_LEG_BUNDLE", sleeve_source=sl8, asset=ast8,
                                    dedupe_key=str(p8.get("dedupe_key") or pid8), close_ts=cl8, now_ts=now,
                                    payload={"legs": lgs8, "box_cost_net": round(c8, 6), "max_box_cost_net": 0.990, "max_fillable_shares": min(float(x["ask_size"]) for x in lgs8), "neg_risk": any(bool(x.get("neg_risk")) for x in lgs8)},
                                )
    except Exception as exc_p8:
        logger.debug(f"Protocol V2 Pillar 8 bridge notice: {exc_p8}")


def _write_and_notify_live_cand(daemon: Any, cand: Dict[str, Any], cand_file: Any, default_cand_path: Any) -> bool:
    import json as _json
    import os as _os
    from pathlib import Path as _Path

    try:
        try:
            import orjson as _orj

            raw_b = _orj.dumps(cand) + b"\n"
            line_s = raw_b.decode("utf-8")
        except Exception:
            line_s = _json.dumps(cand, separators=(",", ":")) + "\n"
            raw_b = line_s.encode("utf-8")
        if _os.name != "nt" and _Path(cand_file) == _Path(default_cand_path):
            try:
                import socket as _socket

                s_ipc = getattr(daemon, "_d1_ipc_sock", None)
                if s_ipc is None:
                    s_ipc = _socket.socket(_socket.AF_UNIX, _socket.SOCK_DGRAM)
                    s_ipc.setblocking(False)
                    daemon._d1_ipc_sock = s_ipc
                ipc_nm = _os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME", "polymarket_d1_box_notify")
                s_ipc.sendto(raw_b, f"\x00{ipc_nm}".encode("utf-8"))
            except Exception:
                pass
        cp = _Path(cand_file)
        cp.parent.mkdir(parents=True, exist_ok=True)
        with open(cp, "a", encoding="utf-8") as fp:
            fp.write(line_s)
        return True
    except Exception as exc:
        logger.debug(f"Live candidate write notice: {exc}")
        return False


def emit_special_v2_box_cand_impl(
    daemon: Any,
    *,
    box_type: str,
    sleeve_source: str,
    asset: str,
    dedupe_key: str,
    close_ts: float,
    now_ts: float,
    payload: Dict[str, Any],
    cand_file: Any,
    default_cand_path: Any,
    state_file: Any,
    default_state_path: Any,
) -> bool:
    if state_file != default_state_path and cand_file == default_cand_path:
        return False
    if not (daemon.single_scan or ("fetch_json" in daemon.__dict__)):
        now_ts = time.time()
    last_emit = float(daemon._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
    if (now_ts - last_emit) < 6.0:
        return False
    daemon._last_d1_live_emit_ts[dedupe_key] = now_ts
    cand = {
        "box_id": f"{box_type}_LIVE_{asset}_{int(close_ts)}_{dedupe_key[-6:]}",
        "dedupe_key": dedupe_key,
        "box_type": str(box_type).upper(),
        "ts_unix": round(now_ts, 3),
        "asset": str(asset),
        "sleeve_source": str(sleeve_source),
        "expiry_ts": float(close_ts),
        "rem_sec": round(max(1.0, float(close_ts) - now_ts), 2),
        **payload,
    }
    return _write_and_notify_live_cand(daemon, cand, cand_file, default_cand_path)


def emit_single_leg_lock_cand_impl(
    daemon: Any,
    *,
    sleeve_source: str,
    asset: str,
    dedupe_key: str,
    token_id: str,
    opp_token_id: str,
    market_id: str,
    condition_id: str,
    side_label: str,
    display_label: str,
    bk_win: Dict[str, Any],
    bk_opp: Optional[Dict[str, Any]],
    fee_rate: float,
    fee_exponent: float,
    neg_risk: bool,
    close_ts: float,
    now_ts: float,
    max_lock_eff_px: float,
    max_opp_bid: float,
    hold_to_maturity: bool,
    p_model: float,
    extract_best_bid_fn: Any,
    walk_l2_fn: Any,
    cand_file: Any,
    default_cand_path: Any,
    state_file: Any,
    default_state_path: Any,
) -> bool:
    if state_file != default_state_path and cand_file == default_cand_path:
        return False
    if not (daemon.single_scan or ("fetch_json" in daemon.__dict__)):
        now_ts = time.time()
    rem_sec = float(close_ts - now_ts)
    is_s2_fast = str(sleeve_source) in {"S2_EXACT_TWAP_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR"}
    min_rem_req = 3.8 if is_s2_fast else 25.0
    if rem_sec < min_rem_req or not token_id or not opp_token_id:
        return False
    last_emit = float(daemon._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
    if (now_ts - last_emit) < (1.2 if is_s2_fast else 15.0):
        return False
    if isinstance(bk_opp, dict):
        opp_bid, _ = extract_best_bid_fn(bk_opp.get("bids") or [])
        win_ask_best, _ = daemon._best_ask_sz(bk_win)
        if opp_bid > max_opp_bid + 1e-6:
            return False
        if win_ask_best < 1.0 and opp_bid > 0.0 and (win_ask_best + opp_bid) > 1.015:
            return False
    max_slip_1l = min(0.040, max(0.005, float(max_lock_eff_px) - 0.850)) if is_s2_fast else min(0.015, max(0.002, float(max_lock_eff_px) - 0.980))
    w_lk = walk_l2_fn(
        bk_win.get("asks") or [],
        25.0,
        5.0,
        fee_rate=float(fee_rate),
        max_slip_cents=max_slip_1l,
        min_l1_usd=5.0 if is_s2_fast else 10.0,
        max_ask_px=min(0.9985, float(max_lock_eff_px) + 0.001),
        fee_exponent=float(fee_exponent),
    )
    if not w_lk.get("filled"):
        return False
    eff_px = float(w_lk["eff_px"])
    min_req_edge = max(0.002, round(float(p_model) - float(max_lock_eff_px), 6))
    if eff_px > float(max_lock_eff_px) + 1e-6 or float(w_lk["shares"]) < 5.0 or (float(p_model) - eff_px) < min_req_edge - 1e-6:
        return False
    if len(daemon._last_d1_live_emit_ts) > 256:
        daemon._last_d1_live_emit_ts = {k: v for k, v in daemon._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
    daemon._last_d1_live_emit_ts[dedupe_key] = now_ts
    cand = {
        "box_id": f"LOCK1_LIVE_{asset}_{int(close_ts)}_{str(market_id or '0')[-5:]}",
        "dedupe_key": dedupe_key,
        "box_type": "SINGLE_LEG_LOCK",
        "ts_unix": round(now_ts, 3),
        "asset": str(asset),
        "regime": f"SINGLE_LEG_LOCK_{str(display_label)[:48]}",
        "pair_horizons": "single_leg_lock",
        "sleeve_source": str(sleeve_source),
        "is_quiet_book": True,
        "expiry_ts": float(close_ts),
        "rem_sec": round(rem_sec, 2),
        "shares": int(math.floor(float(w_lk["shares"]))),
        "box_cost_net": eff_px,
        "max_box_cost_net": float(max_lock_eff_px),
        "max_opp_bid": float(max_opp_bid),
        "hold_to_maturity": bool(hold_to_maturity),
        "p_model": round(float(p_model), 4),
        "leg_a_token_id": str(token_id),
        "leg_a_opp_token_id": str(opp_token_id),
        "leg_a_label": str(display_label)[:64],
        "leg_a_side": str(side_label),
        "leg_a_horizon": "lock_1leg",
        "leg_a_market_id": str(market_id),
        "leg_a_condition_id": str(condition_id),
        "leg_a_strike": 0.0,
        "leg_a_limit_price": float(w_lk.get("worst_px") or w_lk["best_ask"]),
        "leg_a_avail_shares": float(w_lk["shares"]),
        "leg_a_fee_rate": float(fee_rate),
        "leg_a_fee_exponent": float(fee_exponent),
        "leg_a_neg_risk": bool(neg_risk),
        "leg_a_expiry_ts": float(close_ts),
    }
    if not daemon.single_scan and daemon._ws_books:
        rest_seeded_1l = getattr(daemon, "_ws_rest_seeded", set())
        if all(
            t_1 in daemon._ws_books
            and t_1 not in rest_seeded_1l
            and (now_ts - daemon._ws_books[t_1][0]) <= 2.50
            and bool(daemon._ws_books[t_1][1].get("asks") or daemon._ws_books[t_1][1].get("bids"))
            for t_1 in (str(token_id), str(opp_token_id))
        ):
            cand["ws_books"] = {
                t_1: {"bids": (daemon._ws_books[t_1][1].get("bids") or [])[:12], "asks": (daemon._ws_books[t_1][1].get("asks") or [])[:12]}
                for t_1 in (str(token_id), str(opp_token_id))
            }
            cand["ws_books_ts"] = round(min(daemon._ws_books[str(token_id)][0], daemon._ws_books[str(opp_token_id)][0]), 3)
    return _write_and_notify_live_cand(daemon, cand, cand_file, default_cand_path)


def emit_negrisk_convert_cand_impl(
    daemon: Any,
    *,
    sleeve_source: str,
    spec: Any,
    dedupe_key: str,
    arb_hit: Dict[str, Any],
    books_by_token: Dict[str, Dict[str, Any]],
    now_ts: float,
    fee_bips: int,
    cand_file: Any,
    default_cand_path: Any,
    state_file: Any,
    default_state_path: Any,
) -> bool:
    if state_file != default_state_path and cand_file == default_cand_path:
        return False
    if not (daemon.single_scan or ("fetch_json" in daemon.__dict__)):
        now_ts = time.time()
    rem_sec = float(spec.end_ts - now_ts)
    if rem_sec < 65.0 or not spec.is_closed_convert_safe:
        return False
    last_emit = float(daemon._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
    if (now_ts - last_emit) < 2.5:
        return False
    if str(arb_hit.get("mode") or "") == "NR3_SYNTHETIC_ALL_YES_OVERROUND":
        raw_ys = list(arb_hit.get("yes_sell_legs") or [])
        edge_nr3 = float(arb_hit.get("net_edge_per_share") or 0.0)
        if len(raw_ys) < 2 or len(raw_ys) > 15 or edge_nr3 < 0.008:
            return False
        daemon._last_d1_live_emit_ts[dedupe_key] = now_ts
        rel_y = [str(y["yes_token"]) for y in raw_ys]
        ws_snap_y = {
            t: {"bids": (books_by_token[t].get("bids") or [])[:10], "asks": (books_by_token[t].get("asks") or [])[:10]}
            for t in rel_y
            if isinstance(books_by_token.get(t), dict)
        }
        cand_nr3 = {
            "box_id": f"NR3_LIVE_{spec.event_id}_{int(now_ts)}",
            "dedupe_key": dedupe_key,
            "box_type": "NEGRISK_CONVERT",
            "convert_mode": "NR3_SYNTHETIC_ALL_YES_OVERROUND",
            "ts_unix": round(now_ts, 3),
            "asset": "NEGRISK_NR3",
            "sleeve_source": str(sleeve_source),
            "neg_risk_market_id": str(spec.neg_risk_market_id),
            "fee_bips": int(fee_bips),
            "expiry_ts": float(spec.end_ts),
            "rem_sec": round(rem_sec, 2),
            "shares": int(math.floor(float(arb_hit.get("shares") or 8.0))),
            "net_edge_per_share": round(edge_nr3, 5),
            "box_cost_net": round(max(0.01, 1.0 - edge_nr3), 4),
            "split_cond_0": str(arb_hit.get("split_cond_0") or ""),
            "split_cond_1": str(arb_hit.get("split_cond_1") or ""),
            "split_q_idx_0": int(arb_hit.get("split_q_idx_0") or 0),
            "split_q_idx_1": int(arb_hit.get("split_q_idx_1") or 1),
            "no_legs": [],
            "yes_sell_legs": raw_ys,
            "liquid_yes_sells": raw_ys,
            "retained_tail_tokens": [],
            "ws_books": ws_snap_y if len(ws_snap_y) == len(rel_y) else None,
            "ws_books_ts": round(now_ts, 3),
        }
        return _write_and_notify_live_cand(daemon, cand_nr3, cand_file, default_cand_path)

    no_legs_out: List[Dict[str, Any]] = []
    for item in arb_hit.get("no_legs") or []:
        b = item.get("bracket") or {}
        w = item.get("walk") or {}
        tok_n = str(item.get("token_id") or b.get("no_token") or "")
        if not tok_n or b.get("question_index") is None:
            return False
        no_legs_out.append({
            "token_id": tok_n,
            "market_id": str(b.get("market_id") or ""),
            "condition_id": str(b.get("condition_id") or ""),
            "question_index": int(b["question_index"]),
            "label": str(b.get("label") or "")[:48],
            "limit_price": float(w.get("worst_px") or 0.50),
            "fee_rate": float(b.get("fee_rate", 0.0) or 0.0),
            "fee_exponent": float(b.get("fee_exponent", 1.0) or 1.0),
        })
    liquid_yes_sells: List[Dict[str, Any]] = []
    for item in arb_hit.get("yes_sell_legs") or []:
        b = item.get("bracket") or {}
        w = item.get("walk") or {}
        tok_y = str(item.get("token_id") or b.get("yes_token") or "")
        if not tok_y:
            return False
        liquid_yes_sells.append({
            "yes_token": tok_y,
            "market_id": str(b.get("market_id") or ""),
            "label": str(b.get("label") or "")[:48],
            "min_bid_price": float(w.get("worst_px") or 0.01),
            "fee_rate": float(b.get("fee_rate", 0.0) or 0.0),
            "fee_exponent": float(b.get("fee_exponent", 1.0) or 1.0),
        })
    retained_tail_tokens = [
        {
            "yes_token": str(b.get("yes_token") or ""),
            "market_id": str(b.get("market_id") or ""),
            "question_index": int(b.get("question_index") or 0),
            "label": str(b.get("label") or "")[:48],
        }
        for b in (arb_hit.get("retained_free_yes_brackets") or [])
    ]
    edge_ps = float(arb_hit.get("net_edge_per_share") or 0.0)
    _mode_in = str(arb_hit.get("mode") or "")
    if _mode_in == "NR5_NEGATIVE_COST_FREEROLL":
        _min_nr_ed = 0.0020
    elif _mode_in == "NR4_FULL_SWEEP":
        _min_nr_ed = 0.0035
    else:
        _min_nr_ed = 0.0045 if not liquid_yes_sells else 0.0065
    if len(no_legs_out) < 2 or edge_ps < _min_nr_ed:
        return False
    if len(daemon._last_d1_live_emit_ts) > 256:
        daemon._last_d1_live_emit_ts = {k: v for k, v in daemon._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
    daemon._last_d1_live_emit_ts[dedupe_key] = now_ts
    rel_toks = [x["token_id"] for x in no_legs_out] + [y["yes_token"] for y in liquid_yes_sells]
    ws_snap = {
        t: {"bids": (books_by_token[t].get("bids") or [])[:10], "asks": (books_by_token[t].get("asks") or [])[:10]}
        for t in rel_toks
        if isinstance(books_by_token.get(t), dict)
    }
    conv_mode = str(
        arb_hit.get("mode")
        or (
            "NR2_PURE_CASH_CONVERT"
            if not liquid_yes_sells and not retained_tail_tokens
            else ("NR2_SUBSET_LIQUID_YES_CONVERT" if liquid_yes_sells and not retained_tail_tokens else "NR2_SUBSET_CONVERT_FREE_TAIL")
        )
    )
    cand = {
        "box_id": f"NRCONV_LIVE_{spec.event_id}_{int(now_ts)}",
        "dedupe_key": dedupe_key,
        "box_type": "NEGRISK_CONVERT",
        "convert_mode": conv_mode,
        "ts_unix": round(now_ts, 3),
        "asset": "NEGRISK",
        "sleeve_source": str(sleeve_source),
        "neg_risk_market_id": str(spec.neg_risk_market_id),
        "fee_bips": int(fee_bips),
        "expiry_ts": float(spec.end_ts),
        "rem_sec": round(rem_sec, 2),
        "shares": int(math.floor(float(arb_hit.get("shares") or 6.0))),
        "net_edge_per_share": round(edge_ps, 5),
        "box_cost_net": round(max(0.01, 1.0 - edge_ps), 4),
        "leg_a_fee_rate": max((x["fee_rate"] for x in no_legs_out), default=0.0),
        "leg_b_fee_rate": max((y["fee_rate"] for y in liquid_yes_sells), default=0.0),
        "no_legs": no_legs_out,
        "liquid_yes_sells": liquid_yes_sells,
        "retained_tail_tokens": retained_tail_tokens,
        "ws_books": ws_snap if len(ws_snap) == len(rel_toks) else None,
        "ws_books_ts": round(now_ts, 3),
    }
    return _write_and_notify_live_cand(daemon, cand, cand_file, default_cand_path)


def emit_single_leg_maker_lock_cand_impl(
    daemon: Any,
    *,
    sleeve_source: str,
    asset: str,
    dedupe_key: str,
    pair_dedupe_key: str,
    token_id: str,
    opp_token_id: str,
    market_id: str,
    condition_id: str,
    side_label: str,
    display_label: str,
    bk_win: Dict[str, Any],
    bk_opp: Optional[Dict[str, Any]],
    neg_risk: bool,
    close_ts: float,
    now_ts: float,
    min_resting_bid: float,
    max_resting_bid: float,
    min_maker_edge: float,
    max_opp_bid: float,
    hold_to_maturity: bool,
    p_model: float,
    target_bid_px: Optional[float],
    maker_rebate_ps: float,
    extract_best_bid_fn: Any,
    cand_file: Any,
    default_cand_path: Any,
    state_file: Any,
    default_state_path: Any,
) -> bool:
    import os as _os

    if state_file != default_state_path and cand_file == default_cand_path:
        return False
    if not (daemon.single_scan or ("fetch_json" in daemon.__dict__)):
        now_ts = time.time()
    rem_sec = float(close_ts - now_ts)
    is_s2_mkr = str(sleeve_source) in {"S2_EXACT_TWAP_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR"}
    if rem_sec < (5.0 if is_s2_mkr else 120.0) or not token_id or not opp_token_id or token_id == opp_token_id:
        return False
    if (
        sleeve_source == "MKR_REWARD_LOCKED_CARRY"
        and rem_sec > 2700.0
        and _os.getenv("PM_GATLING_BLOCK_LONG_REWARD_CARRY", "1") == "1"
        and not (daemon.single_scan or ("fetch_json" in daemon.__dict__))
    ):
        return False
    last_emit = float(daemon._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
    if (now_ts - last_emit) < (2.0 if is_s2_mkr else 25.0):
        return False
    if not isinstance(bk_win, dict) or not isinstance(bk_opp, dict):
        return False
    opp_bid, _ = extract_best_bid_fn(bk_opp.get("bids") or [])
    if opp_bid > float(max_opp_bid) + 1e-6:
        return False
    best_bid, l1_bid_usd = extract_best_bid_fn(bk_win.get("bids") or [])
    if best_bid < min(float(min_resting_bid), 0.500 if is_s2_mkr else 0.940) - 1e-9:
        return False
    if sleeve_source == "MKR_REWARD_LOCKED_CARRY" and best_bid > float(max_resting_bid) + 1e-6:
        return False
    if target_bid_px is None and best_bid < float(min_resting_bid) - 1e-9:
        return False
    near_bid_usd = (
        sum(float(b.get("price", 0)) * float(b.get("size", 0)) for b in (bk_win.get("bids") or []) if float(b.get("price", 0)) >= (0.50 if is_s2_mkr else 0.90))
        if (sleeve_source == "MKR_REWARD_LOCKED_CARRY" or is_s2_mkr)
        else l1_bid_usd
    )
    if not (daemon.single_scan or ("fetch_json" in daemon.__dict__)) and near_bid_usd < (3.0 if is_s2_mkr else 10.0) - 1e-6:
        return False
    valid_asks = [float(a["price"]) for a in (bk_win.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0]
    best_ask = round(min(valid_asks), 4) if valid_asks else 1.000
    if best_ask < 1.0 and opp_bid > 0.0 and (best_ask + opp_bid) > 1.015:
        return False
    is_mock_emit = bool(daemon.single_scan or ("fetch_json" in daemon.__dict__))
    raw_bk_tk = (
        (getattr(daemon, "_token_tick_sizes", None) or {}).get(str(token_id))
        or bk_win.get("minimum_tick_size")
        or bk_win.get("tick_size")
        or bk_win.get("min_tick_size")
    )
    try:
        bk_tk_f = float(raw_bk_tk) if raw_bk_tk not in (None, "") else 0.0
    except (TypeError, ValueError):
        bk_tk_f = 0.0
    has_subcent_lv = any(
        abs(round(float(lv.get("price", 0.0)) * 100.0) - float(lv.get("price", 0.0)) * 100.0) > 1e-6
        for lv in ((bk_win.get("bids") or []) + (bk_win.get("asks") or []))
        if isinstance(lv, Mapping) and float(lv.get("size", 0.0) or 0.0) > 0.0
    )
    if has_subcent_lv and (bk_tk_f <= 0.0 or bk_tk_f > 0.001):
        bk_tk_f = 0.001
    elif bk_tk_f <= 0.0 and not is_mock_emit:
        bk_tk_f = 0.01
    explicit_subcent_tk = 0.0001 <= bk_tk_f < 0.01
    tb = bk_tk_f if explicit_subcent_tk else max(0.001 if best_bid >= 0.96 else 0.01, bk_tk_f if bk_tk_f >= 0.01 else 0.0)
    ta = bk_tk_f if explicit_subcent_tk else max(0.001 if best_ask > 0.96 else 0.01, bk_tk_f if bk_tk_f >= 0.01 else 0.0)
    reb_f = max(0.0, float(maker_rebate_ps or 0.0))
    if target_bid_px is not None:
        raw_tgt = min(float(target_bid_px), round(best_ask - ta, 4), float(max_resting_bid))
        t_snap = bk_tk_f if explicit_subcent_tk else max(0.001 if raw_tgt >= 0.96 - 1e-9 else 0.01, bk_tk_f if bk_tk_f >= 0.01 else 0.0)
        resting_bid = round(math.floor((raw_tgt + 1e-9) / t_snap) * t_snap, 4)
    else:
        step_cand = round(best_bid + tb, 4) if (best_ask - best_bid) >= (2.0 * tb - 1e-9) else best_bid
        hard_ceil = min(round(best_ask - ta, 4), float(max_resting_bid), round(float(p_model) + reb_f - float(min_maker_edge), 4))
        t_snap = bk_tk_f if explicit_subcent_tk else max(0.001 if min(step_cand, hard_ceil) >= 0.96 - 1e-9 else 0.01, bk_tk_f if bk_tk_f >= 0.01 else 0.0)
        resting_bid = round(math.floor((min(step_cand, hard_ceil) + 1e-9) / t_snap) * t_snap, 4)
    if (best_bid > 0.0 and resting_bid < round(best_bid - 1e-9, 4) and target_bid_px is None) or not (float(min_resting_bid) <= resting_bid <= float(max_resting_bid)):
        return False
    if best_ask < 1.0 and resting_bid >= best_ask - 1e-9:
        return False
    eff_net_bid = round(max(0.001, resting_bid - reb_f), 6)
    if (float(p_model) - eff_net_bid) < float(min_maker_edge) - 1e-9:
        return False
    if not is_s2_mkr and abs(resting_bid - best_bid) <= 1e-6 and l1_bid_usd > 350.0 and not is_mock_emit:
        return False
    if len(daemon._last_d1_live_emit_ts) > 256:
        daemon._last_d1_live_emit_ts = {k: v for k, v in daemon._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
    daemon._last_d1_live_emit_ts[dedupe_key] = now_ts
    fw_w = daemon._get_fresh_ws_book(token_id, now_ts, 2.5) if hasattr(daemon, "_get_fresh_ws_book") else None
    fw_o = daemon._get_fresh_ws_book(opp_token_id, now_ts, 2.5) if hasattr(daemon, "_get_fresh_ws_book") else None
    cand = {
        "box_id": f"MKR_LOCK1_LIVE_{asset}_{int(close_ts)}_{str(market_id or '0')[-5:]}",
        "dedupe_key": dedupe_key,
        "pair_dedupe_key": pair_dedupe_key,
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "ts_unix": round(now_ts, 3),
        "asset": str(asset),
        "regime": f"SINGLE_LEG_MAKER_LOCK_{str(display_label)[:44]}",
        "pair_horizons": "single_leg_maker_lock",
        "sleeve_source": str(sleeve_source),
        "is_quiet_book": True,
        "queue_front": bool(resting_bid > best_bid + 1e-6 or l1_bid_usd <= 50.0),
        "expiry_ts": float(close_ts),
        "rem_sec": round(rem_sec, 2),
        "shares": 16,
        "box_cost_net": resting_bid,
        "max_box_cost_net": float(max_resting_bid),
        "anchor_bid_px": resting_bid,
        "min_resting_bid": float(min_resting_bid),
        "min_maker_edge": round(float(min_maker_edge), 4),
        "maker_rebate_ps": round(reb_f, 5),
        "max_opp_bid": float(max_opp_bid),
        "hold_to_maturity": bool(hold_to_maturity),
        "p_model": round(float(p_model), 4),
        "leg_a_token_id": str(token_id),
        "leg_a_opp_token_id": str(opp_token_id),
        "leg_a_label": str(display_label)[:64],
        "leg_a_side": str(side_label),
        "leg_a_horizon": "maker_lock_1leg",
        "leg_a_market_id": str(market_id),
        "leg_a_condition_id": str(condition_id),
        "leg_a_strike": 0.0,
        "leg_a_limit_price": resting_bid,
        "leg_a_tick_size": t_snap,
        "leg_a_fee_rate": 0.0,
        "leg_a_fee_exponent": 1.0,
        "leg_a_neg_risk": bool(neg_risk),
        "leg_a_expiry_ts": float(close_ts),
        "ws_books": ({str(token_id): fw_w, str(opp_token_id): fw_o} if (fw_w and fw_o) else None),
        "ws_books_ts": round(now_ts, 3),
    }
    if isinstance(bk_win.get("_s2_meta"), Mapping):
        cand.update(bk_win["_s2_meta"])
    return _write_and_notify_live_cand(daemon, cand, cand_file, default_cand_path)


def emit_maker_anchor_box_cand_impl(
    daemon: Any,
    *,
    sleeve_source: str,
    box_type: str,
    asset: str,
    dedupe_key: str,
    regime: str,
    pair_horizons: str,
    leg_a: Dict[str, Any],
    leg_b: Dict[str, Any],
    anchor_is_a: bool,
    queue_front: bool,
    anchor_bid_px: float,
    hedge_limit_px: float,
    avail_a_shares: float,
    avail_b_shares: float,
    close_ts: float,
    now_ts: float,
    k_low: float,
    k_high: float,
    corridor_bps: float,
    posted_spot: float,
    crypto_fee_rate: float,
    project_root: Any,
    cand_file: Any,
    default_cand_path: Any,
    state_file: Any,
    default_state_path: Any,
) -> bool:
    import json as _json
    import os as _os
    from pathlib import Path as _Path

    if state_file != default_state_path and cand_file == default_cand_path:
        return False
    is_rebate_mg = str(sleeve_source) == "D1_REBATE_MACHINE_GUN"
    if cand_file == default_cand_path:
        if is_rebate_mg:
            try:
                _u_p = _Path(project_root) / "config" / "polymarket_strategy_and_risk.json"
                if _u_p.exists() and not bool((_json.loads(_u_p.read_text(encoding="utf-8")).get("riskless_boxes") or {}).get("enable_d1_rebate_maker_canary", False)):
                    return False
            except Exception:
                return False
        else:
            if _os.environ.get("PM_DISABLE_LIVE_MAKER_ANCHOR_BOX", "0") == "1":
                return False
            try:
                _rc_p = _Path(project_root) / "config" / "polymarket_risk_config.json"
                if _rc_p.exists() and not bool(_json.loads(_rc_p.read_text(encoding="utf-8")).get("enable_live_maker_anchor_boxes", True)):
                    return False
            except Exception:
                return False
    if not (daemon.single_scan or ("fetch_json" in daemon.__dict__)):
        now_ts = time.time()
    rem_sec = float(close_ts - now_ts)
    max_rem = 64800.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else 900.0
    if not (65.0 <= rem_sec <= max_rem):
        return False
    last_emit = float(daemon._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
    if (now_ts - last_emit) < (2.5 if is_rebate_mg else 12.0):
        return False
    fee_a = float(leg_a.get("fee_rate", 0.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else crypto_fee_rate))
    fee_b = float(leg_b.get("fee_rate", 0.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else crypto_fee_rate))
    exp_a = float(leg_a.get("fee_exponent", 1.0))
    exp_b = float(leg_b.get("fee_exponent", 1.0))
    fr_hdg = fee_b if anchor_is_a else fee_a
    fe_hdg = exp_b if anchor_is_a else exp_a
    h_hdg = min(0.95, fr_hdg * ((hedge_limit_px * (1.0 - hedge_limit_px)) ** fe_hdg) / max(1e-9, hedge_limit_px)) if (fr_hdg > 0.0 and 0.0 < hedge_limit_px < 1.0) else 0.0
    pair_est = round(anchor_bid_px + (hedge_limit_px / max(0.05, 1.0 - h_hdg)), 4)
    max_cap = (
        0.998
        if is_rebate_mg
        else ((0.992 if str(regime) == "ZF_SP1_NBA" else (0.985 if rem_sec > 3600.0 else 0.990)) if box_type == "ZERO_FEE_MAKER_ANCHOR" else 0.988)
    )
    if not (0.860 <= pair_est <= max_cap):
        return False
    if len(daemon._last_d1_live_emit_ts) > 256:
        daemon._last_d1_live_emit_ts = {k: v for k, v in daemon._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
    daemon._last_d1_live_emit_ts[dedupe_key] = now_ts
    sh_est = max(5, int(math.floor(13.50 / max(0.86, pair_est))))
    cand = {
        "box_id": f"{box_type}_LIVE_{asset}_{int(close_ts)}_{str(leg_a.get('market_id','0'))[-5:]}",
        "dedupe_key": dedupe_key,
        "box_type": str(box_type),
        "ts_unix": round(now_ts, 3),
        "asset": str(asset),
        "regime": str(regime),
        "pair_horizons": str(pair_horizons),
        "sleeve_source": str(sleeve_source),
        "anchor_is_a": bool(anchor_is_a),
        "queue_front": bool(queue_front),
        "anchor_bid_px": round(float(anchor_bid_px), 4),
        "hedge_limit_px": round(float(hedge_limit_px), 4),
        "posted_spot": round(float(posted_spot), 6),
        "k_low": float(k_low),
        "k_high": float(k_high),
        "corridor_bps": round(float(corridor_bps), 2),
        "expiry_ts": float(close_ts),
        "rem_sec": round(rem_sec, 2),
        "shares": sh_est,
        "box_cost_net": pair_est,
        "max_box_cost_net": max_cap,
        "leg_a_token_id": str(leg_a["token_id"]),
        "leg_a_opp_token_id": str(leg_a.get("opp_token_id") or ""),
        "leg_a_label": str(leg_a.get("label") or leg_a.get("side") or "YES"),
        "leg_a_side": str(leg_a.get("side") or "YES"),
        "leg_a_horizon": str(leg_a.get("horizon") or pair_horizons),
        "leg_a_market_id": str(leg_a.get("market_id") or ""),
        "leg_a_condition_id": str(leg_a.get("condition_id") or ""),
        "leg_a_strike": float(leg_a.get("strike") or k_low),
        "leg_a_limit_price": round(float(anchor_bid_px if anchor_is_a else hedge_limit_px), 4),
        "leg_a_avail_shares": round(float(avail_a_shares), 2),
        "leg_a_fee_rate": fee_a,
        "leg_a_fee_exponent": exp_a,
        "leg_a_neg_risk": bool(leg_a["neg_risk"]) if isinstance(leg_a.get("neg_risk"), bool) else False,
        "leg_a_expiry_ts": float(leg_a.get("end_ts") or close_ts),
        "leg_b_token_id": str(leg_b["token_id"]),
        "leg_b_opp_token_id": str(leg_b.get("opp_token_id") or ""),
        "leg_b_label": str(leg_b.get("label") or leg_b.get("side") or "NO"),
        "leg_b_side": str(leg_b.get("side") or "NO"),
        "leg_b_horizon": str(leg_b.get("horizon") or pair_horizons),
        "leg_b_market_id": str(leg_b.get("market_id") or ""),
        "leg_b_condition_id": str(leg_b.get("condition_id") or ""),
        "leg_b_strike": float(leg_b.get("strike") or k_high),
        "leg_b_limit_price": round(float(hedge_limit_px if anchor_is_a else anchor_bid_px), 4),
        "leg_b_avail_shares": round(float(avail_b_shares), 2),
        "leg_b_fee_rate": fee_b,
        "leg_b_fee_exponent": exp_b,
        "leg_b_neg_risk": bool(leg_b["neg_risk"]) if isinstance(leg_b.get("neg_risk"), bool) else False,
        "leg_b_expiry_ts": float(leg_b.get("end_ts") or close_ts),
    }
    if not daemon.single_scan and daemon._ws_books:
        req_ws_m = [str(leg_a["token_id"]), str(leg_b["token_id"])]
        for op_id in (str(leg_a.get("opp_token_id") or ""), str(leg_b.get("opp_token_id") or "")):
            if op_id:
                req_ws_m.append(op_id)
        rest_seeded_m = getattr(daemon, "_ws_rest_seeded", set())
        if all(
            t_x in daemon._ws_books
            and t_x not in rest_seeded_m
            and (now_ts - daemon._ws_books[t_x][0]) <= (0.65 if i_x < 2 else 2.50)
            and bool(daemon._ws_books[t_x][1].get("bids"))
            and bool(daemon._ws_books[t_x][1].get("asks"))
            for i_x, t_x in enumerate(req_ws_m)
        ):
            cand["ws_books"] = {
                t_x: {"bids": (daemon._ws_books[t_x][1].get("bids") or [])[:12], "asks": (daemon._ws_books[t_x][1].get("asks") or [])[:12]}
                for t_x in req_ws_m
            }
            cand["ws_books_ts"] = round(min(daemon._ws_books[t_x][0] for t_x in req_ws_m[:2]), 3)
    return _write_and_notify_live_cand(daemon, cand, cand_file, default_cand_path)


def _parse_gamma_neg_risk_flag(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return v.strip().lower() == "true"
    return None


def attach_weather_neg_risk_from_gamma(sp_w: Any, ev_raw: Any) -> None:
    if not isinstance(ev_raw, dict):
        return
    ev_nr = _parse_gamma_neg_risk_flag(ev_raw.get("negRisk"))
    nr_by_id: Dict[str, Optional[bool]] = {}
    for mk in ev_raw.get("markets") or ():
        if not isinstance(mk, dict):
            continue
        mk_nr = _parse_gamma_neg_risk_flag(mk.get("negRisk"))
        if mk_nr is None:
            mk_nr = ev_nr
        for id_k in (mk.get("id"), mk.get("conditionId")):
            if id_k not in (None, ""):
                nr_by_id[str(id_k)] = mk_nr
    for bkt in getattr(sp_w, "buckets", ()):
        nr_v = nr_by_id.get(str(bkt.market_id))
        if nr_v is None:
            nr_v = nr_by_id.get(str(bkt.condition_id))
        if nr_v is None and getattr(bkt, "neg_risk", None) is not None:
            continue
        try:
            setattr(bkt, "neg_risk", nr_v)
        except Exception:
            pass


def attach_ws_books_and_write_d1_cand(
    daemon: Any,
    cand: Dict[str, Any],
    leg_a: Mapping[str, Any],
    leg_b: Mapping[str, Any],
    cand_file: Path,
    default_cand_path: Path,
) -> bool:
    if not daemon.single_scan and daemon._ws_books:
        act_ws_toks = [str(leg_a["token_id"]), str(leg_b["token_id"])]
        opp_ws_toks = [
            t_id
            for t_id in (str(leg_a.get("opp_token_id") or ""), str(leg_b.get("opp_token_id") or ""))
            if t_id
        ]
        req_ws_toks = act_ws_toks + opp_ws_toks
        now_ws_emit = time.time()
        rest_seeded = getattr(daemon, "_ws_rest_seeded", set())
        ws_entries = [None if t_id in rest_seeded else daemon._ws_books.get(t_id) for t_id in req_ws_toks]
        if len(req_ws_toks) >= 2 and all(
            e is not None
            and (now_ws_emit - e[0]) <= (0.65 if idx < 2 else 2.50)
            and e[1].get("bids")
            and e[1].get("asks")
            for idx, e in enumerate(ws_entries)
        ):
            cand["ws_books_ts"] = round(min(float(e[0]) for e in ws_entries[:2] if e is not None), 4)
            cand["ws_books"] = {
                t_id: {"bids": (e[1].get("bids") or [])[:12], "asks": (e[1].get("asks") or [])[:12]}
                for t_id, e in zip(req_ws_toks, ws_entries)
                if e is not None
            }
    return _write_and_notify_live_cand(daemon, cand, cand_file, default_cand_path)


def select_sll_velocity_preempt_target(
    harvester: Any,
    cand_edge_hr: float,
    is_s2_mkr: bool,
    vel_mult: float,
    now_pe: Optional[float] = None,
) -> Tuple[float, str]:
    pe_map = getattr(harvester, "_maker_anchor_preempt_events", None) or {}
    claimed_pe = harvester.__dict__.setdefault("_claimed_velocity_preempts", set())
    now_t = float(now_pe if now_pe is not None else time.time())

    def _it_edge_hr(it: Mapping[str, Any]) -> float:
        ib = float(it.get("anchor_bid_px") or 0.0)
        ie = float(it.get("expiry_ts") or 0.0)
        if 0.0 < ib < 1.0 and ie > now_t:
            return round(((1.0 - ib) * 10000.0) / max(0.02, (ie - now_t) / 3600.0), 2)
        return float(it.get("velocity_bps_hr") or 0.0)

    slow_cands = [
        (_it_edge_hr(it), str(it.get("inflight_key") or ""))
        for it in getattr(harvester, "pending_entry_intents", {}).values()
        if isinstance(it, Mapping)
        and it.get("live_maker_anchor_inflight")
        and str(it.get("inflight_key") or "") not in claimed_pe
        and str(it.get("sleeve_source") or "") not in {"S2_EXACT_TWAP_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR"}
        and (now_t - float(it.get("ts") or 0.0)) >= (
            90.0 if (not is_s2_mkr and float(it.get("anchor_bid_px") or 0.0) >= 0.991 and float(it.get("velocity_bps_hr") or 0.0) >= 55.0) else 20.0
        )
    ]
    if not slow_cands:
        return 0.0, ""
    slow_vel, slow_k = min(slow_cands, key=lambda x: x[0])
    if slow_k and slow_k in pe_map and cand_edge_hr >= max(slow_vel * vel_mult, slow_vel + 25.0):
        return slow_vel, slow_k
    return 0.0, ""


def eval_sll_fresh_book_and_peg(
    bk_win_f: Any,
    bk_opp_f: Any,
    candidate_box: Mapping[str, Any],
    anc_bid_px: float,
    min_rb: float,
    max_rb: float,
    max_opp: float,
    budget: float,
    tk_wf: float,
    real_clob_sll: bool,
    enforce_b1_v53: bool,
    is_mlk1: bool,
    is_s2_mkr: bool,
    repost_n_in: int,
    b1_q_cap: float,
) -> Tuple[Optional[str], float, float, int, float]:
    if tk_wf <= 0.0:
        try:
            tk_wf = float(candidate_box.get("leg_a_tick_size") or 0.0)
        except (TypeError, ValueError):
            tk_wf = 0.0
    bids_wf = [
        (float(x["price"] if isinstance(x, Mapping) else x[0]), float(x["size"] if isinstance(x, Mapping) else x[1]))
        for x in ((bk_win_f or {}).get("bids") or [])
        if float(x.get("size", 0) if isinstance(x, Mapping) else x[1]) > 0
    ]
    asks_wf = sorted([
        (float(x["price"] if isinstance(x, Mapping) else x[0]), float(x["size"] if isinstance(x, Mapping) else x[1]))
        for x in ((bk_win_f or {}).get("asks") or [])
        if float(x.get("size", 0) if isinstance(x, Mapping) else x[1]) > 0
    ])
    if any(abs(round(px * 100.0) - px * 100.0) > 1e-6 for px, _ in (bids_wf + asks_wf)):
        tk_wf = min(tk_wf, 0.001) if tk_wf > 0.0 else 0.001
    elif tk_wf <= 0.0 and real_clob_sll:
        tk_wf = 0.01
    bids_of = [
        float(x["price"] if isinstance(x, Mapping) else x[0])
        for x in ((bk_opp_f or {}).get("bids") or [])
        if float(x.get("size", 0) if isinstance(x, Mapping) else x[1]) > 0
    ]
    opp_bid_f = max(bids_of, default=0.0)
    best_bid_f = max((px for px, _ in bids_wf), default=0.0)
    best_ask_f = asks_wf[0][0] if asks_wf else 1.000
    near_bid_usd_f = sum(px * sz for px, sz in bids_wf if px >= (0.50 if is_s2_mkr else 0.90))
    if (
        opp_bid_f > max_opp + 1e-6
        or best_bid_f < min(min_rb, 0.500 if is_s2_mkr else 0.940) - 1e-9
        or (not (is_mlk1 or is_s2_mkr) and best_bid_f < min_rb - 1e-9)
        or (is_mlk1 and near_bid_usd_f < 10.0 - 1e-6)
        or (is_s2_mkr and near_bid_usd_f < 4.0 - 1e-6)
        or (best_ask_f < 1.0 and (best_ask_f + opp_bid_f) > 1.015)
    ):
        return f"DUAL_BOOK_CONSENSUS_VETO:bid={best_bid_f:.4f},opp_bid={opp_bid_f:.4f}", 0.0, anc_bid_px, 0, tk_wf
    if enforce_b1_v53:
        tb_f = max(0.001 if best_bid_f >= 0.96 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
        ta_f = max(0.001 if best_ask_f > 0.96 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
        step_f = round(best_bid_f + tb_f, 4) if (best_ask_f - best_bid_f) >= (2.0 * tb_f - 1e-9) else best_bid_f
        if is_mlk1 or is_s2_mkr or repost_n_in > 0:
            step_f = max(anc_bid_px, step_f)
        ceil_f = min(
            round(best_ask_f - ta_f, 4),
            max_rb,
            round(
                float(candidate_box.get("p_model") or 0.9985)
                + max(0.0, float(candidate_box.get("maker_rebate_ps") or 0.0))
                - float(candidate_box.get("min_maker_edge") or 0.004),
                4,
            ),
        )
        tsnap_f = max(0.001 if min(step_f, ceil_f) >= 0.96 - 1e-9 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
        anc_bid_px = round(math.floor((min(step_f, ceil_f) + 1e-9) / tsnap_f) * tsnap_f, 4)
        if anc_bid_px < round(best_bid_f - 1e-9, 4):
            return f"BOND1_OUTBID_ABOVE_CAP:{best_bid_f:.4f}>{max_rb:.4f}", 30.0, anc_bid_px, 0, tk_wf
        l1_q_usd = sum(px * sz for px, sz in bids_wf if abs(px - best_bid_f) <= 1e-6)
        if not is_s2_mkr and abs(anc_bid_px - best_bid_f) <= 1e-6 and l1_q_usd > b1_q_cap + 1e-6:
            return f"BOND1_QUEUE_TOO_DEEP:{l1_q_usd:.1f}>{b1_q_cap:.1f}", 45.0, anc_bid_px, 0, tk_wf
    else:
        if best_ask_f < 1.0 and anc_bid_px >= best_ask_f - 1e-9:
            ta_f = max(0.001 if best_ask_f > 0.96 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
            anc_bid_px = round(min(max_rb, best_ask_f - ta_f), 4)
        if tk_wf >= 0.01:
            anc_bid_px = round(math.floor((anc_bid_px + 1e-9) / tk_wf) * tk_wf, 4)
    if not (min_rb <= anc_bid_px <= max_rb):
        return f"FRESH_BOOK_CROSS_OR_CEILING:{anc_bid_px:.4f}", 0.0, anc_bid_px, 0, tk_wf
    sh_int = int(math.floor(budget / anc_bid_px))
    if sh_int < 5:
        return "INSUFFICIENT_MAKER_BOX_BUDGET", (2.0 if is_s2_mkr else 8.0), anc_bid_px, sh_int, tk_wf
    return None, 0.0, anc_bid_px, sh_int, tk_wf


def eval_sll_live_book_poll(
    bk_oc: Any,
    bk_wc: Any,
    candidate_box: Mapping[str, Any],
    posted_px: float,
    min_rb: float,
    max_rb: float,
    max_opp: float,
    tk_wf: float,
    enforce_b1_v53: bool,
    is_s2_mkr: bool,
    repost_n_in: int,
    b1_q_cap: float,
    b1_buried_s: float,
    exp_ts: float,
    buried_since_mono: Optional[float],
) -> Tuple[str, Optional[float], Optional[float], str]:
    opp_b_live = max(
        (
            float(x["price"] if isinstance(x, Mapping) else x[0])
            for x in ((bk_oc or {}).get("bids") or [])
            if float(x.get("size", 0) if isinstance(x, Mapping) else x[1]) > 0
        ),
        default=0.0,
    )
    bids_wc = [
        (float(x["price"] if isinstance(x, Mapping) else x[0]), float(x["size"] if isinstance(x, Mapping) else x[1]))
        for x in ((bk_wc or {}).get("bids") or [])
        if float(x.get("size", 0) if isinstance(x, Mapping) else x[1]) > 0
    ]
    asks_wc = sorted([
        (float(x["price"] if isinstance(x, Mapping) else x[0]), float(x["size"] if isinstance(x, Mapping) else x[1]))
        for x in ((bk_wc or {}).get("asks") or [])
        if float(x.get("size", 0) if isinstance(x, Mapping) else x[1]) > 0
    ])
    win_b_live = max((px for px, _ in bids_wc), default=posted_px)
    win_a_live = asks_wc[0][0] if asks_wc else 1.000
    win_floor_l = max(0.450, posted_px - 0.080) if is_s2_mkr else 0.900
    if opp_b_live > max(0.010, max_opp + 0.002) or win_b_live < win_floor_l:
        return "ADVERSE", None, buried_since_mono, f"opp_bid=${opp_b_live:.4f}, win_bid=${win_b_live:.4f}"
    if enforce_b1_v53:
        if win_b_live > posted_px + 1e-6:
            tb_l = max(0.001 if win_b_live >= 0.96 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
            ta_l = max(0.001 if win_a_live > 0.96 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
            step_l = round(win_b_live + tb_l, 4) if (win_a_live - win_b_live) >= (2.0 * tb_l - 1e-9) else win_b_live
            ceil_l = min(
                round(win_a_live - ta_l, 4),
                max_rb,
                round(
                    float(candidate_box.get("p_model") or 0.9985)
                    + max(0.0, float(candidate_box.get("maker_rebate_ps") or 0.0))
                    - float(candidate_box.get("min_maker_edge") or 0.004),
                    4,
                ),
            )
            tsnap_l = max(0.001 if min(step_l, ceil_l) >= 0.96 - 1e-9 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
            cand_rp = round(math.floor((min(step_l, ceil_l) + 1e-9) / tsnap_l) * tsnap_l, 4)
            l1_q_l = sum(px * sz for px, sz in bids_wc if abs(px - win_b_live) <= 1e-6)
            if (
                repost_n_in < 5
                and not is_s2_mkr
                and min_rb <= cand_rp <= max_rb
                and cand_rp >= round(win_b_live - 1e-9, 4)
                and cand_rp > posted_px + 1e-6
                and (abs(cand_rp - win_b_live) > 1e-6 or l1_q_l <= min(120.0, b1_q_cap) + 1e-6)
                and (exp_ts <= 0.0 or (exp_ts - time.time()) >= 150.0)
            ):
                return "REPEG", cand_rp, buried_since_mono, f"outbid (${win_b_live:.4f} > ${posted_px:.4f}); re-pegging -> ${cand_rp:.4f}"
            if buried_since_mono is None:
                buried_since_mono = time.monotonic()
            elif (time.monotonic() - buried_since_mono) >= b1_buried_s:
                return "BURIED", None, buried_since_mono, f"outbid at ${win_b_live:.4f} (posted ${posted_px:.4f}) >= {b1_buried_s:.0f}s"
        else:
            buried_since_mono = None
    return "OK", None, buried_since_mono, ""


def register_live_d1_box_positions_impl(
    harvester: Any,
    box_id: str,
    cand: Dict[str, Any],
    res: Dict[str, Any],
    pre_bal_a: float,
    pre_bal_b: float,
    pos_confirmed_status: Any,
    matched_pending_status: Any,
) -> List[str]:
    """Registers both filled legs of a live D1 Dominance Box (`$1.00` `DETERMINISTIC_TERMINAL_HOLD` for `<=900s` `DOMINANCE`)."""
    now_ts = time.time()
    sh = float(res.get("net_paired_shares") or res.get("shares") or cand.get("net_paired_shares") or cand.get("shares") or 12.0)
    exp_ts = float(cand.get("expiry_ts") or (now_ts + 180.0))
    asset_sym = str(cand.get("asset") or "BTC").upper()
    meta_by_tok = {
        str(cand.get("leg_a_token_id")): ("leg_a", pre_bal_a),
        str(cand.get("leg_b_token_id")): ("leg_b", pre_bal_b),
    }
    if f"{box_id}_L1" in harvester.active_positions or f"{box_id}_L2" in harvester.active_positions:
        box_id = f"{box_id}_{int(now_ts * 1000) % 100000}"
    tids = (f"{box_id}_L1", f"{box_id}_L2")
    legs_in = (res["leg_1"], res["leg_2"])
    leg_records = []
    tot_box_cost = 0.0
    excess_info = res.get("excess_leg") if isinstance(res.get("excess_leg"), dict) else None
    excess_tok = str((excess_info or {}).get("token_id") or "")
    excess_sh = float((excess_info or {}).get("shares") if (excess_info or {}).get("shares") is not None else ((excess_info or {}).get("excess_shares") or 0.0))
    htm_enabled = harvester._is_v5_live_strict() or bool(getattr(harvester, "hold_to_maturity", True))
    cand_bt_u = str(cand.get("box_type") or "DOMINANCE").upper()
    for idx, (tid, lg) in enumerate(zip(tids, legs_in)):
        partner_tid = tids[1 - idx]
        tok = str(lg["token_id"])
        pfx, pre_b = meta_by_tok.get(tok, ("leg_a" if idx == 0 else "leg_b", 0.0))
        leg_exp = float(cand.get(f"{pfx}_expiry_ts") or exp_ts)
        d1_htm = bool(cand.get("hold_to_maturity") or (cand_bt_u == "DOMINANCE" and 0.0 < (leg_exp - now_ts) <= 900.0 and htm_enabled))
        px = float(lg.get("price") or cand.get(f"{pfx}_limit_price") or 0.48)
        raw_r = lg.get("raw") if isinstance(lg.get("raw"), dict) else {}
        mk_raw = harvester._num(raw_r.get("makingAmount") or raw_r.get("making_amount"))
        if mk_raw is not None and mk_raw >= 1e4:
            mk_raw = mk_raw / 1e6
        m_leg = float(lg.get("matched_shares") or sh)
        leg_sh = round(sh + excess_sh, 4) if (tok == excess_tok and 0.05 <= excess_sh < 5.0) else sh
        gross_sh_explicit = lg.get("gross_shares")
        is_share_fee_leg = (
            str(lg.get("entry_fee_asset") or "").upper() == "SHARES"
            or (gross_sh_explicit is not None and float(gross_sh_explicit) > leg_sh + 1e-4)
        )
        gross_leg_sh = round(float(gross_sh_explicit), 4) if gross_sh_explicit is not None else leg_sh
        if mk_raw is not None and m_leg > max(leg_sh, gross_leg_sh) + 0.05:
            mk_raw = mk_raw * (max(leg_sh, gross_leg_sh) / m_leg)
        notional = round(float(mk_raw) if (mk_raw is not None and mk_raw > 0.0) else (gross_leg_sh * px), 4)
        leg_fr_raw = cand.get(f"{pfx}_fee_rate")
        fr = 0.0 if lg.get("is_maker_anchor") else (float(leg_fr_raw) if leg_fr_raw is not None else 0.07)
        fe = float(cand.get(f"{pfx}_fee_exponent", 1.0) or 1.0)
        fee_u = 0.0 if is_share_fee_leg else (round(leg_sh * fr * ((px * (1.0 - px)) ** fe), 4) if fr > 0.0 else 0.0)
        entry_fee_asset = "SHARES" if is_share_fee_leg else "USDC"
        tot_box_cost += notional + fee_u
        side_str = str(cand.get(f"{pfx}_side") or ("UP" if "UP" in str(lg.get("label", "")).upper() else "DOWN"))
        strike_k = float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx == "leg_a" else "k_high") or 100.0)
        oid = lg.get("orderID")
        txs = raw_r.get("transactionsHashes") or raw_r.get("transactions_hashes") or []
        cand_slv_src = str(cand.get("sleeve_source") or "")
        slv_rec = (
            cand_slv_src
            if cand_slv_src in {"D1_QUIET_BOOK_BOX", "D1_4H_DOMINANCE_BOX"}
            else ("D1_SAME_ORACLE_DOMINANCE_BOX" if cand_bt_u == "DOMINANCE" else (cand_slv_src or "D1_SAME_ORACLE_DOMINANCE_BOX"))
        )
        leg_records.append((tid, {
            "trade_id": tid, "box_id": box_id, "box_expected_legs": 2, "box_partner_trade_id": partner_tid, "is_dominance_box": True, "is_locked_arbitrage_box": True,
            "hold_to_maturity_lock": d1_htm,
            "opp_token_id": str(cand.get(f"{pfx}_opp_token_id") or ""), "dedupe_key": str(cand.get("dedupe_key") or ""), "pair_dedupe_key": str(cand.get("pair_dedupe_key") or ""),
            "sleeve": slv_rec, "sleeve_source": str(cand.get("sleeve_source") or slv_rec),
            "entry_tte": max(1.0, leg_exp - now_ts), "event_id": box_id,
            "market_id": str(cand.get(f"{pfx}_market_id") or f"{box_id}_{idx}"),
            "condition_id": str(cand.get(f"{pfx}_condition_id") or ""),
            "token_id": tok, "target_token": side_str, "asset": asset_sym,
            "horizon": str(cand.get(f"{pfx}_horizon") or "15m"), "is_subhourly": True,
            "candle_open_spot": strike_k, "entry_spot_ref": strike_k, "spot_denomination": "USD",
            "candle_sigma": 0.0025 if asset_sym == "BTC" else 0.0035,
            "entry_price": round(notional / max(leg_sh, 0.01), 4), "entry_shares": leg_sh, "gross_entry_shares": gross_leg_sh,
            "remaining_shares": leg_sh, "filled_exit_shares": 0.0, "remaining_exit_shares": leg_sh,
            "remaining_cost_basis": notional, "realized_exit_cash": 0.0, "realized_exit_fee": 0.0,
            "gross_exit_cash": 0.0, "average_exit_price": 0.0, "exit_trade_ids": [],
            "notional_usd": notional, "fee_usd": fee_u, "entry_fee_cash_usd": fee_u,
            "entry_fee_asset": entry_fee_asset, "fee_source": "crypto_fees_v2",
            "fee_rate_applied": fr, "fee_exponent_applied": fe,
            "target_exit_price": 1.0 if d1_htm else 0.99, "exit_order_size": leg_sh,
            "entry_time_utc": datetime.now(timezone.utc).isoformat(), "entry_ts": now_ts,
            "candle_expiry_ts": leg_exp, "pre_token_balance": pre_b,
            "order_id": oid, "entry_order_id": oid, "trade_ids": [], "transactions_hashes": list(txs),
            "status": pos_confirmed_status if harvester.dry_run else matched_pending_status,
            "inventory_reconciled": bool(harvester.dry_run),
            "exit_order_id": None,
            "exit_order_status": "DETERMINISTIC_TERMINAL_HOLD" if d1_htm else ("NONE" if harvester.dry_run else "AWAITING_DELTA_SETTLEMENT"),
            "terminal_policy": "DETERMINISTIC_TERMINAL_HOLD" if d1_htm else None,
            "is_liquidating": False, "unwind_order_id": None, "unwind_start_time": 0.0,
        }))
    box_unit = round(tot_box_cost / max(sh, 1.0), 5)
    k_lo_b = float(cand.get("k_low") or 0.0)
    k_hi_b = float(cand.get("k_high") or 0.0)
    for tid, rec in leg_records:
        rec["box_type"] = cand_bt_u
        rec["box_k_low"] = k_lo_b
        rec["box_k_high"] = k_hi_b
        rec["box_cost_net"] = box_unit
        rec["box_total_cost_usd"] = round(tot_box_cost, 4)
        harvester.active_positions[tid] = rec
    if excess_info is not None and excess_sh >= 5.0:
        harvester._register_legged_out_d1_residual(
            f"{box_id}_EXCESS", cand,
            {
                "token_id": excess_tok, "label": excess_info.get("label"),
                "matched_shares": excess_sh, "residual_shares": excess_sh,
                "price": excess_info.get("price"), "is_maker_anchor": bool(excess_info.get("is_maker_anchor")),
            },
            pre_bal_a + (sh if excess_tok == str(cand.get("leg_a_token_id")) else 0.0),
            pre_bal_b + (sh if excess_tok == str(cand.get("leg_b_token_id")) else 0.0),
        )
    harvester._last_exit_credit_window = None
    if getattr(harvester, "_last_known_collateral", None) is not None:
        harvester._last_known_collateral = max(0.0, float(harvester._last_known_collateral) - tot_box_cost)
        harvester._last_entry_debit_window = (time.time(), float(harvester._last_known_collateral))
    harvester.executor.invalidate_collateral_cache()
    harvester._pending_collateral_refresh = True
    harvester.save_state()
    if not harvester.dry_run:
        for tid, rec in leg_records:
            if not rec.get("hold_to_maturity_lock"):
                harvester._spawn_fast_confirm(tid)
    logger.info(
        f"✓ [D1 LIVE DOMINANCE BOX ENTERED] {box_id} ({asset_sym}) | {sh:.0f} pairs @ box_net=${box_unit:.4f} "
        f"(cost=${tot_box_cost:.2f}, min_floor=+${sh * max(0.0, 1.0 - box_unit):.2f})"
    )
    return [tid for tid, _ in leg_records]


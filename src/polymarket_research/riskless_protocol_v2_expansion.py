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
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

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
        or meta.get("enableNegRiskOther")
        or meta.get("negRiskOther")
        or meta.get("open_universe")
        or meta.get("hasOther")
    )
    if is_aug and not other_indices:
        return False, {
            "reason": "AUGMENTED_NEGRISK_MISSING_SYNTHETIC_OTHER_INDEX",
            "is_protocol_v2": is_protocol_v2_market(meta),
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
        parsed.append(
            {
                "index": idx,
                "label": str(item.get("label") or item.get("groupItemTitle") or item.get("outcome") or f"idx_{idx}"),
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
                        "box_type": "MULTI_LEG_BUNDLE",
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
                            "box_type": "MULTI_LEG_BUNDLE",
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
    return {
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


# ---------------------------------------------------------------------------
# 3. Family II: `S2_RTDS` 60s TWAP, `D1` Telescoping, `B1` One-Touch/Noon, `EQ1` Pyth Equity
# ---------------------------------------------------------------------------


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
    the final `55s` (`4.5s <= TTE <= 16.0s` in `live_lock_mode`) of a `5m`/`15m`/`4h` 60s-TWAP candle
    across `BTC, ETH, SOL, XRP, BNB, DOGE, HYPE` (`XAU`/`XAG` spot-settled forex streams are excluded).
    Since settlement price `P_settle = (1/60) * sum_{k=1}^{60} P_k`, once `N_elapsed` ticks are observed,
    `N_elapsed / 60` of the settlement average is already mathematically locked in history!
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
        if not (4.5 <= rem_sec <= 16.0):
            return None
    elif not (0.8 <= rem_sec <= 55.0):
        return None

    raw_samples = samples_last_60s if samples_last_60s is not None else (rtds_ticks or ())
    pts = sorted([(float(t), float(p)) for t, p in raw_samples if float(p) > 0.0], key=lambda x: x[0])
    if len(pts) < 8:
        return None

    n_rem = max(1, int(math.ceil(rem_sec)))
    elapsed_sec = max(1.0, 60.0 - rem_sec)
    if expiry_ts is not None:
        win_start = float(expiry_ts) - 60.0
        win_pts = [(t, p) for t, p in pts if (win_start - 0.5) <= t <= (now_f + 1.0)]
    else:
        target_obs = max(8, min(len(pts), int(round(elapsed_sec))))
        win_pts = pts[-target_obs:]

    min_req_ticks = max(8, int(math.floor(elapsed_sec * 0.72))) if live_lock_mode else max(8, 56 - n_rem)
    if len(win_pts) < min_req_ticks:
        return None

    win_prices = [p for _, p in win_pts[-60:]]
    vol_prices = [p for _, p in pts[-120:]]
    mean_obs = sum(win_prices) / float(len(win_prices))
    cur_px = win_prices[-1]
    if official_twap_60s is not None and float(official_twap_60s) > 0.0 and rem_sec <= 16.0:
        max_twap_div = 0.0020 if live_lock_mode else 0.0025
        if abs(float(official_twap_60s) - mean_obs) / max(mean_obs, 1e-9) > max_twap_div:
            return None

    # Estimate 1-second innovation volatility + max observed jump floor over trailing window
    diffs = [abs(vol_prices[i] - vol_prices[i - 1]) for i in range(1, len(vol_prices))]
    sigma_1s = max(
        cur_px * 0.00018,
        math.sqrt(sum(d * d for d in diffs) / float(max(1, len(diffs)))) if diffs else cur_px * 0.0003,
        (max(diffs) * 0.55) if diffs else 0.0,
    )

    w_obs = float(len(win_prices)) / float(len(win_prices) + n_rem)
    w_rem = float(n_rem) / float(len(win_prices) + n_rem)
    expected_final_twap = w_obs * mean_obs + w_rem * cur_px

    open_f = float(open_price)
    if live_lock_mode:
        # Strict triple-side agreement: elapsed mean, live spot, and projected TWAP all beat open_price
        d_mean = mean_obs - open_f
        d_spot = cur_px - open_f
        d_proj = expected_final_twap - open_f
        if d_mean == 0.0 or d_spot == 0.0 or d_proj == 0.0:
            return None
        if not ((d_mean > 0.0) == (d_spot > 0.0) == (d_proj > 0.0)):
            return None

    elapsed_cushion_bps = (abs(mean_obs - open_f) / open_f) * 10000.0
    req_adverse_avg_move_bps = (elapsed_sec / max(0.5, rem_sec)) * elapsed_cushion_bps
    if live_lock_mode and req_adverse_avg_move_bps < 45.0:
        return None

    # Variance of average of remaining random-walk steps `1..n_rem` is ~ `(n_rem + 1)*(2*n_rem + 1)/(6*n_rem) * sigma_1s^2`
    rw_rem_std = sigma_1s * math.sqrt(float((n_rem + 1) * (2 * n_rem + 1)) / 6.0)
    discretization_std = cur_px * 0.00008  # 0.8 bps 1Hz arrival-timestamp jitter floor
    final_twap_std = max(cur_px * 1e-6, math.hypot(w_rem * rw_rem_std, discretization_std))

    z = (expected_final_twap - open_f) / final_twap_std
    min_z = 3.50 if live_lock_mode else 3.40
    if abs(z) < min_z:
        return None
    p_win = 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))
    req_prob = max(float(min_lock_prob), 0.9990) if live_lock_mode else float(min_lock_prob)
    if p_win < req_prob:
        return None

    direction = "UP" if z > 0 else "DOWN"
    ask_px = float(up_ask if direction == "UP" else down_ask)
    if not (0.02 <= ask_px <= 0.990):
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
        "open_price": open_f,
        "z_score": round(z, 3),
        "p_model": round(min(0.9999, p_win), 6),
        "ask_px": q_ask,
        "net_cost_per_share": round(net_cost, 6),
        "net_edge_per_share": round(ev_edge, 6),
    }


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
    "EQ1_PYTH_EQUITY_DOMINANCE_BOX",
    "DC1_DOUBLE_CHANCE_1X2_PARITY",
    "LP_COMP1_SPORTS_TRIANGLES",
    "HALFTIME_FREEZE_OFFSET_BOX",
    "MENTION1_CUMULATIVE_LADDER_BOX",
    "NR6_CROSS_SLATE_SURJECTION_BOX",
    "CTF_OVERROUND_MINT_SELL",
    "W_PRUNE1_NR0_BASKET",
    "W_PRUNE1_DEAD_NO_BOND",
    "W_SOLAR1_POST_2351_LOCK",
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
        and bool(harvester._is_v5_unleashed_active())
        and getattr(ex, "client", None) is not None
        and getattr(getattr(ex, "client", None), "_mock_children", None) is None
        and "get_market_book" not in getattr(ex, "__dict__", {})
        and not getattr(harvester, "enforce_bond1_smart_queue", False)
    )
    if not (getattr(harvester, "enforce_gatling_sizing", False) or live_real_ex):
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


def _round_half_away_from_zero(val: float) -> int:
    d = Decimal(str(round(val, 6)))
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_routine_metar_temp_c(raw_metar: str) -> Optional[Dict[str, Any]]:
    """
    Parse a routine `METAR` observation string while **strictly rejecting unscheduled `SPECI` reports**.
    Extracts exact `0.1°C` `RMK T[01]\\d{3}` temperature when present (uncertainty `±0.05°C`),
    falling back to integer body `TT/TdTd` with conservative `±0.55°C` uncertainty band so boundary
    rounding ambiguity can NEVER prune a live bracket.
    """
    txt = str(raw_metar or "").strip()
    if not txt:
        return None
    head_tokens = txt.upper().split()[:3]
    if "SPECI" in head_tokens:
        return None

    m_rmk = _METAR_T_REMARK_RE.search(txt.upper())
    if m_rmk:
        sign = -1.0 if m_rmk.group(1) == "1" else 1.0
        temp_c = sign * (int(m_rmk.group(2)) / 10.0)
        unc_c = 0.05
        has_t_group = True
    else:
        # Search body before `RMK`
        body_part = txt.upper().split("RMK")[0]
        m_body = _METAR_BODY_TEMP_RE.search(body_part)
        if not m_body:
            return None
        t_tok = m_body.group(1)
        temp_c = -float(t_tok[1:]) if t_tok.startswith("M") else float(t_tok)
        unc_c = 0.55
        has_t_group = False

    min_c = temp_c - unc_c
    max_c = temp_c + unc_c
    min_f = min_c * 9.0 / 5.0 + 32.0
    max_f = max_c * 9.0 / 5.0 + 32.0
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


def compute_running_metar_extrema(
    metar_lines: Sequence[str],
    *,
    unit: str = "F",
) -> Optional[Dict[str, Any]]:
    """
    Aggregate a station's intraday routine `METAR` reports (`SPECI` excluded) to obtain the
    monotonically non-decreasing lower bound `confirmed_running_high_floor` on the daily maximum.
    """
    u = str(unit or "F").strip().upper()
    parsed = [p for p in (parse_routine_metar_temp_c(line) for line in (metar_lines or [])) if p is not None]
    if not parsed:
        return None
    if u == "C":
        floor_hi = max(int(p["confirmed_floor_int_c"]) for p in parsed)
        ceil_hi = max(int(p["confirmed_ceil_int_c"]) for p in parsed)
    else:
        floor_hi = max(int(p["confirmed_floor_int_f"]) for p in parsed)
        ceil_hi = max(int(p["confirmed_ceil_int_f"]) for p in parsed)
    return {
        "unit": u,
        "routine_obs_count": len(parsed),
        "confirmed_running_high_floor": floor_hi,
        "confirmed_running_high_ceil": ceil_hi,
        "all_have_t_group": all(bool(p["has_t_group"]) for p in parsed),
    }


def detect_w_prune1_metar_slate_arb(
    brackets: Sequence[Mapping[str, Any]],
    metar_lines: Sequence[str],
    *,
    station_icao: str,
    unit: str = "F",
    local_hour_minute: Tuple[int, int] = (15, 0),
    event_meta: Optional[Mapping[str, Any]] = None,
    min_net_edge_usd: float = 0.005,
    min_shares: float = 5.0,
) -> List[Dict[str, Any]]:
    """
    `W_PRUNE1` Monotonic METAR Ratchet + `W_SOLAR1` Post-`23:51` Local Lock:
      - Any daily-high bracket `[low, high]` with `high < confirmed_running_high_floor` is mathematically
        DEAD (`YES == $0.00`, `NO == $1.00`) right now because `max_{day} T >= max_{t <= now} T`.
      - Emits:
          1. `W_PRUNE1_DEAD_NO_BOND`: Buy `NO` on dead brackets (`ask_no < 1.0 - min_net_edge_usd`).
          2. `W_PRUNE1_NR0_BASKET`: Buy `YES` ONLY on surviving brackets (`sum_{alive} ask_yes < 1.0 - min_net_edge_usd`).
          3. `W_SOLAR1_POST_2351_LOCK`: After `23:52` local station time (all hourly routine `:51/:53` METARs
             for the day have printed) when `floor == ceil`, locks the unique winning bracket `YES`.
    """
    ext = compute_running_metar_extrema(metar_lines, unit=unit)
    if ext is None:
        return []
    ok_part, _ = verify_v2_negrisk_other_partition(brackets, event_meta=event_meta)
    if not ok_part and len(brackets) >= 3:
        return []

    floor_hi = int(ext["confirmed_running_high_floor"])
    ceil_hi = int(ext["confirmed_running_high_ceil"])
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

        if high_i < floor_hi:
            # Dead bracket! NO is guaranteed $1.00
            if 0.01 <= no_ask <= (1.0 - float(min_net_edge_usd)) and no_sz >= min_shares and no_tok:
                q_no, _, _ = quantize_dynamic_tick_price(no_ask, "BUY", shares=min_shares, mode="taker")
                edge_no = 1.0 - q_no
                if edge_no >= float(min_net_edge_usd):
                    signals.append(
                        {
                            "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                            "station": str(station_icao).upper(),
                            "token_id": no_tok,
                            "condition_id": cid,
                            "ask_px": q_no,
                            "p_model": 0.9999,
                            "net_edge_per_share": round(edge_no, 6),
                            "max_fillable_shares": round(no_sz, 2),
                            "confirmed_running_high_floor": floor_hi,
                            "bracket_high": high_i,
                        }
                    )
        else:
            # Surviving bracket
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

            # W_SOLAR1 post-23:52 local station lock when floor == ceil falls cleanly inside [low_i, high_i]
            if (loc_h == 23 and loc_m >= 52) and floor_hi == ceil_hi and low_i <= floor_hi <= high_i:
                if 0.01 <= yes_ask <= (1.0 - float(min_net_edge_usd)) and yes_sz >= min_shares and yes_tok:
                    q_win, _, _ = quantize_dynamic_tick_price(yes_ask, "BUY", shares=min_shares, mode="taker")
                    if (1.0 - q_win) >= float(min_net_edge_usd):
                        signals.append(
                            {
                                "sleeve": "W_SOLAR1_POST_2351_LOCK",
                                "station": str(station_icao).upper(),
                                "token_id": yes_tok,
                                "condition_id": cid,
                                "ask_px": q_win,
                                "p_model": 0.9995,
                                "net_edge_per_share": round(1.0 - q_win, 6),
                                "max_fillable_shares": round(yes_sz, 2),
                                "locked_high": floor_hi,
                            }
                        )

    if alive_complete and 1 <= len(alive_legs) < len(brackets):
        sum_alive = sum(x["net_cost"] for x in alive_legs)
        edge_basket = 1.0 - sum_alive
        if edge_basket >= float(min_net_edge_usd):
            signals.append(
                {
                    "sleeve": "W_PRUNE1_NR0_BASKET",
                    "box_type": "DOMINANCE" if len(alive_legs) == 2 else "MULTI_LEG_BUNDLE",
                    "station": str(station_icao).upper(),
                    "legs": alive_legs,
                    "leg_count": len(alive_legs),
                    "pruned_dead_count": len(brackets) - len(alive_legs),
                    "confirmed_running_high_floor": floor_hi,
                    "cost_per_share": round(sum_alive, 6),
                    "net_edge_per_share": round(edge_basket, 6),
                    "max_fillable_shares": round(min(x["ask_size"] for x in alive_legs), 2),
                }
            )
    return signals


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
                    out.append(
                        {
                            "sleeve": "LP_COMP1_SPORTS_TRIANGLES",
                            "box_type": "DOMINANCE",
                            "pattern": "NO_BTTS_PLUS_YES_OVER_1_5",
                            "leg_a": {"token_id": ta, "condition_id": str(btts_m.get("condition_id") or ""), "ask_px": qpa},
                            "leg_b": {"token_id": tb, "condition_id": str(o15.get("condition_id") or ""), "ask_px": qpb},
                            "guaranteed_payout_per_share": 1.0,
                            "cost_per_share": round(qpa + qpb, 6),
                            "net_edge_per_share": round(edge, 6),
                            "max_fillable_shares": round(min(sa, sb), 2),
                        }
                    )

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
                    out.append(
                        {
                            "sleeve": "LP_COMP1_SPORTS_TRIANGLES",
                            "box_type": "MULTI_LEG_BUNDLE",
                            "pattern": "NO_DRAW_YES_BTTS_YES_UNDER_1_5",
                            "legs": [
                                {"token_id": t1, "condition_id": str(draw_m.get("condition_id") or ""), "ask_px": qp1, "net_cost": qp1, "ask_size": s_min},
                                {"token_id": t2, "condition_id": str(btts_m.get("condition_id") or ""), "ask_px": qp2, "net_cost": qp2, "ask_size": s_min},
                                {"token_id": t3, "condition_id": str(u15.get("condition_id") or ""), "ask_px": qp3, "net_cost": qp3, "ask_size": s_min},
                            ],
                            "leg_count": 3,
                            "guaranteed_payout_per_share": 1.0,
                            "cost_per_share": round(cost3, 6),
                            "net_edge_per_share": round(edge3, 6),
                            "max_fillable_shares": round(s_min, 2),
                        }
                    )
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
                results.append(
                    {
                        "sleeve": "C1_BINARY_COMPLETE_SET",
                        "box_type": "COMPLETE_SET",
                        "condition_id": cid,
                        "yes_token_id": yes_tok,
                        "no_token_id": no_tok,
                        "yes_ask": qya,
                        "no_ask": qna,
                        "fee_rate": f_r,
                        "cost_per_share": round(c_under, 6),
                        "net_edge_per_share": round(edge_u, 6),
                        "max_fillable_shares": round(min(ysz_a, nsz_a), 2),
                    }
                )

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
                results.append(
                    {
                        "sleeve": "CTF_OVERROUND_MINT_SELL",
                        "box_type": "CTF_OVERROUND",
                        "condition_id": cid,
                        "yes_token_id": yes_tok,
                        "no_token_id": no_tok,
                        "yes_bid": qyb,
                        "no_bid": qnb,
                        "fee_rate": f_r,
                        "net_proceeds_per_share": round(rev_over, 6),
                        "net_edge_per_share": round(edge_o, 6),
                        "max_fillable_shares": round(min(ysz_b, nsz_b) / 1.25, 2),
                    }
                )

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
) -> Dict[str, Any]:
    """
    Execute `CTF_OVERROUND_MINT_SELL`:
      1. Mint `shares` complete sets (`splitPosition` `$1.00 * shares` -> `YES` + `NO`).
      2. Atomically sweep both resting `YES` and `NO` bids (`execute_atomic_box_overround_unwind`).
      3. If the dual FOK sweep does not complete cleanly, immediately call `attempt_onchain_complete_set_merge`
         on unsold pairs so principal `$1.00 * shares` returns to USDC.e with zero directional orphan!
    """
    sh = round(float(shares), 2)
    if sh < 5.0:
        return {"success": False, "reason": "SHARES_BELOW_5_MIN"}
    if hasattr(executor, "split_collateral_to_complete_set"):
        sp = await asyncio.to_thread(executor.split_collateral_to_complete_set, condition_id, sh, neg_risk=False)
    elif attempt_onchain_split_position is not None:
        sp = await asyncio.to_thread(attempt_onchain_split_position, executor, condition_id, sh, neg_risk=False)
    else:
        sp = {"success": False, "reason": "NO_SPLIT_HANDLER"}
    if not (sp or {}).get("success"):
        return {"success": False, "reason": f"SPLIT_FAILED:{(sp or {}).get('reason')}"}

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
                await asyncio.to_thread(executor.place_fok_order, yes_token_id, "BUY", sh, min(0.99, yes_min_bid + 0.02))
                u_res = {"success": False}
        else:
            u_res = {"success": False}
    else:
        u_res = {"success": False}

    if (u_res or {}).get("success"):
        la, lb = u_res["leg_a"], u_res["leg_b"]
        cash_a = float(la.get("taking_amount") or 0.0) - float(la.get("fee_usd") or 0.0)
        cash_b = float(lb.get("taking_amount") or 0.0) - float(lb.get("fee_usd") or 0.0)
        realized = round(cash_a + cash_b, 4)
        return {
            "success": True,
            "shares": sh,
            "cost_usd": sh,
            "realized_cash_usd": realized,
            "net_pnl_usd": round(realized - sh, 4),
            "split_tx_hash": sp.get("tx_hash"),
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
        merged_ok = bool(isinstance(m_res, Mapping) and m_res.get("success"))
    elif hasattr(executor, "merge_complete_set_to_collateral"):
        m_res = await asyncio.to_thread(executor.merge_complete_set_to_collateral, condition_id, sh, neg_risk=False)
        merged_ok = bool(isinstance(m_res, Mapping) and m_res.get("success"))
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
        if hasattr(executor, "execute_fok_order"):
            raw_res = executor.execute_fok_order(tok, px, sh * px, "BUY", neg_risk=leg_nr)
            ok = bool(isinstance(raw_res, Mapping) and raw_res.get("success"))
            res = dict(raw_res) if isinstance(raw_res, Mapping) else {"success": ok}
        elif hasattr(executor, "place_fok_order"):
            raw_res = executor.place_fok_order(tok, "BUY", sh, px, neg_risk=leg_nr)
            ok = bool(isinstance(raw_res, Mapping) and raw_res.get("success"))
            res = dict(raw_res) if isinstance(raw_res, Mapping) else {"success": ok}
        elif hasattr(executor, "execute_snipe_order"):
            o_res = executor.execute_snipe_order(
                trade_id=f"{bundle_id}_L{idx}",
                token_id=tok,
                target_token=str(leg.get("side") or leg.get("label") or "YES").upper(),
                notional_usd=round(sh * px, 4),
                target_price=px,
                side="BUY",
                depth_hurdle=1.02,
                market_id=str(leg.get("market_id") or ""),
                condition_id=str(leg.get("condition_id") or leg.get("market_id") or ""),
                market_fee_rate=leg_fr,
                market_fee_exponent=leg_fe,
                max_price_ceiling=px,
                max_ticket_cap=max(40.0, round(sh * px + 2.0, 2)),
                min_price_floor=0.01,
                neg_risk=leg_nr,
                max_book_buffer=0.0,
            )
            ok = bool(getattr(o_res, "success", False))
            res = {
                "success": ok,
                "making_amount": float(getattr(o_res, "notional_usd", 0.0) or (sh * px)),
                "fee_usd": float(getattr(o_res, "fee_usd", 0.0) or 0.0),
                "size": float(getattr(o_res, "size", 0.0) or sh),
                "price": float(getattr(o_res, "price", 0.0) or px),
                "order_id": getattr(o_res, "order_id", None),
                "error": getattr(o_res, "error", None),
            }
        else:
            ok = False
            res = {"success": False, "error": "NO_EXECUTOR_FOK_METHOD"}

        if not ok:
            for f_leg, f_res in filled:
                f_tok = str(f_leg.get("token_id") or "")
                f_nr = bool(f_leg["neg_risk"]) if "neg_risk" in f_leg and f_leg.get("neg_risk") is not None else bool(neg_risk)
                f_sh = float(f_res.get("size") or sh)
                f_px = max(0.01, round(_sf(f_leg.get("ask_px"), 0.1) - 0.03, 3))
                if hasattr(executor, "execute_unwind_order"):
                    try:
                        executor.execute_unwind_order(
                            f_tok,
                            size=f_sh,
                            side="SELL",
                            min_price=f_px,
                            neg_risk=f_nr,
                        )
                    except TypeError:
                        executor.execute_unwind_order(f"UNW_{bundle_id}", f_tok, f_sh, f_px)
                elif hasattr(executor, "place_fok_order"):
                    executor.place_fok_order(f_tok, "SELL", f_sh, f_px, neg_risk=f_nr)
            return {"success": False, "reason": f"LEG_FOK_REJECTED:{tok[:12]}", "unwound_legs": len(filled)}

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
                "candle_expiry_ts": exp_ts,
                "status": "MATCHED_PENDING_SETTLEMENT",
                "neg_risk": leg_nr,
            }
        harvester.active_positions[lid] = pos
        tids.append(lid)
    return tids


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
        if hasattr(ex, "get_market_book"):
            by = ex.get_market_book(y_tok) or {}
            bn = ex.get_market_book(n_tok) or {}
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
        if net_rev < 1.005:
            return {"executed": False, "reason": f"OVERROUND_GONE:{net_rev:.4f}"}
        sh = math.floor(min(budget, min(y_sz, n_sz) / 1.15) * 100.0) / 100.0
        if sh < 5.0:
            return {"executed": False, "reason": "OVERROUND_MIN_SHARES"}
        # Run split + dual bid sweep synchronously via helper thread / event-loop safe runner
        sp = (
            ex.split_collateral_to_complete_set(cid, sh, neg_risk=False)
            if hasattr(ex, "split_collateral_to_complete_set")
            else (attempt_onchain_split_position(ex, cid, sh, neg_risk=False) if attempt_onchain_split_position is not None else {"success": False})
        )
        if not (sp or {}).get("success"):
            retry_cd[dedupe_k] = now_ts + 8.0
            return {"executed": False, "reason": f"SPLIT_FAILED:{(sp or {}).get('reason')}"}
        u_res = (
            ex.execute_atomic_box_overround_unwind(f"CTFOVR_{cid[:10]}", y_tok, y_bid, n_tok, n_bid, sh, False, False, fr, fe, fr, fe)
            if hasattr(ex, "execute_atomic_box_overround_unwind")
            else {"success": False}
        )
        if not (u_res or {}).get("success"):
            if hasattr(ex, "merge_complete_set_positions"):
                ex.merge_complete_set_positions(cid, sh, neg_risk=False)
            retry_cd[dedupe_k] = now_ts + 8.0
            return {"executed": False, "reason": "OVERROUND_SWEEP_REJECTED_MERGED_BACK"}
        la, lb = u_res["leg_a"], u_res["leg_b"]
        realized = round(
            (float(la.get("taking_amount") or 0.0) - float(la.get("fee_usd") or 0.0))
            + (float(lb.get("taking_amount") or 0.0) - float(lb.get("fee_usd") or 0.0)),
            4,
        )
        tid = f"CTFOVR_{cid[:10]}_{int(now_ts)}"
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
                "payout_usd": realized,
                "net_pnl_usd": round(realized - sh, 4),
                "won": (realized - sh) >= -0.01,
                "status": "CLOSED",
                "close_reason": "CTF_OVERROUND_INSTANT_MINT_SELL",
                "entry_ts": now_ts,
                "exit_ts": now_ts,
            }
        )
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
        if hasattr(ex, "get_market_book"):
            refreshed_legs: List[Dict[str, Any]] = []
            tot_net_ps = 0.0
            min_sh_avail = 999999.0
            for lg in raw_legs:
                tok = str(lg.get("token_id") or "")
                bk = ex.get_market_book(tok) or {}
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
        res = _execute_multi_leg_bundle_sync(ex, refreshed_legs, shares=sh, bundle_id=bid, neg_risk=default_nr)
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
        )
        if res.get("success"):
            cid = str(box.get("condition_id") or "CTFOVR")
            harvester.closed_positions.append(
                {
                    "trade_id": f"CTFOVR_{cid[:10]}_{int(now_ts)}",
                    "box_id": f"CTFOVR_{cid[:10]}_{int(now_ts)}",
                    "is_dominance_box": True,
                    "box_type": "CTF_OVERROUND",
                    "sleeve": "CTF_OVERROUND_MINT_SELL",
                    "condition_id": cid,
                    "entry_shares": sh,
                    "notional_usd": float(res["cost_usd"]),
                    "payout_usd": float(res["realized_cash_usd"]),
                    "net_pnl_usd": float(res["net_pnl_usd"]),
                    "won": float(res["net_pnl_usd"]) >= -0.01,
                    "status": "CLOSED",
                    "close_reason": "CTF_OVERROUND_INSTANT_MINT_SELL",
                    "entry_ts": now_ts,
                    "exit_ts": now_ts,
                }
            )
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
        res = await execute_multi_leg_all_yes_bundle(ex, legs, shares=sh, bundle_id=bid, neg_risk=default_nr)
        if res.get("success"):
            exp_ts = float(box.get("expiry_ts") or (now_ts + 7200.0))
            _register_bundle_leg_positions(
                harvester,
                bundle_id=bid,
                sleeve_src=str(box.get("sleeve") or "NR0_ALL_YES_COMPLETE_SET"),
                cand_asset=str(box.get("asset") or "NR0"),
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

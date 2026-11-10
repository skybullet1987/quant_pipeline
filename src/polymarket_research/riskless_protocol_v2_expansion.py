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
import os
import re
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

try:
    from src.polymarket_research.holistic_strategy_governance import (
        GLOBAL_GOVERNANCE_MANAGER,
        get_unleashed_v5_tier_profile,
    )
except ImportError:  # pragma: no cover
    from holistic_strategy_governance import (  # type: ignore
        GLOBAL_GOVERNANCE_MANAGER,
        get_unleashed_v5_tier_profile,
    )

SETTLEMENT_RECEIVABLE_STATUSES = frozenset({"AWAITING_ONCHAIN_SETTLEMENT"})


def position_is_settlement_receivable(pos: Mapping[str, Any]) -> bool:
    return pos.get("status") in SETTLEMENT_RECEIVABLE_STATUSES


def is_post_expiry_uma_frozen_lock(pos: Mapping[str, Any], now_ts: Optional[float] = None) -> bool:
    """
    True when a hold-to-resolution lock/residual position is past market expiry (`>= expiry + 60s`),
    carries zero active CLOB exit/unwind orders, and is frozen in a UMA Optimistic Oracle dispute
    (`umaResolutionStatus == 'disputed'`) or `>= 4h` post-expiry/post-entry oracle settlement lag.
    Preserves the position untouched in `active_positions` and `total_account_equity` while keeping
    frozen post-expiry receivables from choking liquid `pUSD` pools (`sll_used`, `bridged_zf_cap`).
    """
    if not isinstance(pos, Mapping) or position_is_settlement_receivable(pos):
        return False
    if pos.get("is_liquidating") or pos.get("exit_order_id") or pos.get("unwind_order_id"):
        return False
    _bt_frz = str(pos.get("box_type") or "").strip().upper()
    if not (
        pos.get("is_single_leg_lock")
        or pos.get("is_dominance_box")
        or pos.get("hold_to_maturity_lock")
        or _bt_frz in {"SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK", "MULTI_LEG_RESIDUAL", "MULTI_LEG_BUNDLE", "DOMINANCE"}
    ):
        return False
    exp_ts = float(pos.get("candle_expiry_ts") or 0.0)
    if exp_ts <= 0.0:
        return False
    now_f = float(time.time() if now_ts is None else now_ts)
    if now_f < exp_ts + 60.0:
        return False
    uma_st = str(pos.get("umaResolutionStatus") or "").strip().lower()
    anchor_ts = max(exp_ts, float(pos.get("entry_ts") or 0.0))
    return uma_st == "disputed" or now_f >= anchor_ts + 14400.0


class _USNewYorkFallbackTZ(tzinfo):
    """
    Stdlib-pure US Eastern (`America/New_York`) `tzinfo` implementing exact US DST transitions
    (2nd Sunday in March `07:00 UTC` -> 1st Sunday in November `06:00 UTC`) when Windows Python
    lacks the `tzdata` IANA bundle.
    """

    @staticmethod
    def _nth_sunday_day(year: int, month: int, n: int) -> int:
        first_wd = datetime(year, month, 1).weekday()  # Mon=0 .. Sun=6
        first_sun = 1 + ((6 - first_wd) % 7)
        return first_sun + 7 * (n - 1)

    @classmethod
    def _is_edt(cls, dt: Optional[datetime]) -> bool:
        if dt is None:
            return False
        y = dt.year
        dst_start_utc = datetime(y, 3, cls._nth_sunday_day(y, 3, 2), 7, 0, 0)
        dst_end_utc = datetime(y, 11, cls._nth_sunday_day(y, 11, 1), 6, 0, 0)
        naive = dt.replace(tzinfo=None)
        # Approximate local wall-time transition (02:00 EST -> +5h = 07:00 UTC; 02:00 EDT -> +4h = 06:00 UTC)
        start_local = datetime(y, 3, dst_start_utc.day, 2, 0, 0)
        end_local = datetime(y, 11, dst_end_utc.day, 1 if getattr(dt, "fold", 0) else 2, 0, 0)
        return start_local <= naive < end_local

    def utcoffset(self, dt: Optional[datetime]) -> timedelta:
        return timedelta(hours=-4 if self._is_edt(dt) else -5)

    def dst(self, dt: Optional[datetime]) -> timedelta:
        return timedelta(hours=1 if self._is_edt(dt) else 0)

    def tzname(self, dt: Optional[datetime]) -> str:
        return "EDT" if self._is_edt(dt) else "EST"


def get_us_eastern_tz() -> tzinfo:
    """Returns `ZoneInfo('America/New_York')` when `tzdata` is installed, else exact `_USNewYorkFallbackTZ()`."""
    try:
        return ZoneInfo("America/New_York")
    except Exception:
        return _USNewYorkFallbackTZ()


def safe_zoneinfo(tz_name: Optional[str]) -> tzinfo:
    """Resolves an IANA timezone with safe fallback to `_USNewYorkFallbackTZ` or `timezone.utc`."""
    nm = str(tz_name or "UTC").strip()
    if not nm or nm.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(nm)
    except Exception:
        if nm in {"America/New_York", "US/Eastern", "America/Detroit", "America/Toronto"}:
            return _USNewYorkFallbackTZ()
        return timezone.utc


def _iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()

try:
    from src.polymarket_research.riskless_machine_gun_engine import (
        attempt_onchain_split_position,
        wait_for_erc1155_delivery,
    )
except Exception:
    attempt_onchain_split_position = None  # type: ignore
    wait_for_erc1155_delivery = None  # type: ignore


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
    "ZEC",
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
    "ZEC",
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
    "HOOD",
    "PLTR",
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


def detect_nr_m1_dead_seed_fanout(
    spec: Any,
    dead_question_indices: Set[int],
    books_by_token: Mapping[str, Mapping[str, Any]],
    *,
    fee_bips: int = 0,
    min_shares: float = 5.0,
    min_net_edge_usd: float = 0.0035,
    max_seed_eff_ask: float = 0.997,
) -> Optional[Dict[str, Any]]:
    """
    `NR_M1_DEAD_SEED_OVERROUND` (`m = 1` Zero-Additional-Collateral NegRisk Conversion):
    Strictly gated on **100% mathematically eliminated** `NO_k` seeds (`q_idx in dead_question_indices`,
    e.g., passed `XTRACK1` post-count buckets or surpassed `W_PRUNE1` METAR brackets) where:
      1. `Ask_eff(NO_k) <= min(max_seed_eff_ask, eff_mult - 0.002)` (`< $1.00 * eff_mult`), AND
      2. A SINGLE surviving outcome `j != k` has executable post-fee `Bid_net(YES_j) >= Ask_eff(NO_k) + min_net_edge_usd`.

    Zero-Loss Proof across ALL states & race conditions:
      - `convertPositions(m=1)` burns `1 NO_k` for `$0.00` extra cash and mints `eff_mult` shares of `YES_i`
        for every `i != k` (which forms a `$1.00 * eff_mult` complete set over all alive states since `p(k) == 0`).
      - Post-convert `YES_j` is swept via a **single all-or-nothing `OrderType.FOK` SELL**:
        * Branch A (`FOK` fills `100%`): cash recovered `>= Ask_eff(NO_k) + min_net_edge_usd` immediately,
          plus all remaining `YES_{i}` (`i not in {k, j}`) stay in wallet as `$0.00`-cost freeroll tokens!
        * Branch B (`FOK` rejects `0%` because `YES_j` bid pulled during `2-4s` Polygon block confirmation):
          ZERO `YES` shares leave wallet; the intact `(N - 1)` surviving `YES` complete set redeems at
          `eff_mult * $1.00 >= Ask_eff(NO_k) + $0.002 > $0.00` guaranteed profit!
    """
    if not dead_question_indices or not bool(getattr(spec, "is_closed_convert_safe", True)):
        return None
    nrm_id = str(getattr(spec, "neg_risk_market_id", "") or "").strip()
    brackets = list(getattr(spec, "brackets", None) or [])
    if len(nrm_id.replace("0x", "")) != 64 or len(brackets) < 3:
        return None
    eff_mult = 1.0 - max(0, int(fee_bips)) / 10000.0
    hard_cost_ceil = min(float(max_seed_eff_ask), eff_mult - 0.002)
    if hard_cost_ceil <= 0.05:
        return None

    sh_req = float(max(5.0, math.floor(float(min_shares))))
    minted_sh = float(math.floor(sh_req * eff_mult * 100.0 + 1e-9) / 100.0)
    if minted_sh < 4.95:
        return None

    def _walk_side(levels: Any, target_sh: float, is_ask: bool) -> Optional[Tuple[float, float, float]]:
        parsed: List[Tuple[float, float]] = []
        for lv in (levels or []):
            try:
                px = float(lv.get("price") if isinstance(lv, Mapping) else lv[0])
                sz = float(lv.get("size") if isinstance(lv, Mapping) else lv[1])
                if 0.001 <= px <= 0.999 and sz > 0.0:
                    parsed.append((px, sz))
            except Exception:
                continue
        if not parsed:
            return None
        parsed.sort(key=lambda t: t[0], reverse=not is_ask)
        cum, gross, worst = 0.0, 0.0, parsed[0][0]
        for px, sz in parsed:
            take = min(sz, max(0.0, target_sh - cum))
            if take <= 0.0:
                break
            gross += take * px
            worst = px
            cum += take
            if cum >= target_sh - 1e-6:
                return (gross / target_sh, worst, sum(s for _, s in parsed[:3]))
        return None

    def _bf(br: Any, key: str, default: Any = None) -> Any:
        return br.get(key, default) if isinstance(br, Mapping) else getattr(br, key, default)

    best_hit: Optional[Dict[str, Any]] = None
    best_edge = 0.0

    for b_dead in brackets:
        q_k = _bf(b_dead, "question_index", None)
        no_tok = str(_bf(b_dead, "no_token", "") or "")
        if q_k is None or int(q_k) not in dead_question_indices or not no_tok:
            continue
        bk_no = books_by_token.get(no_tok)
        if not isinstance(bk_no, Mapping):
            continue
        w_no = _walk_side(bk_no.get("asks"), sh_req, is_ask=True)
        if w_no is None:
            continue
        vwap_no, worst_no, depth_no = w_no
        fr_k = float(_bf(b_dead, "fee_rate", 0.0) or 0.0)
        fe_k = float(_bf(b_dead, "fee_exponent", 1.0) or 1.0)
        fee_k = compute_exact_taker_fee_per_share(worst_no, fr_k, fe_k)
        hair_k = min(0.25, max(0.0, fee_k / max(worst_no, 1e-6))) if fr_k > 0.0 else 0.0
        ask_eff_ps = worst_no / max(1.0 - hair_k, 1e-6)
        if ask_eff_ps > hard_cost_ceil + 1e-9:
            continue

        surviving_brs = [
            b_sv for b_sv in brackets
            if _bf(b_sv, "question_index", None) is not None
            and int(_bf(b_sv, "question_index")) != int(q_k)
            and int(_bf(b_sv, "question_index")) not in dead_question_indices
            and str(_bf(b_sv, "yes_token", "") or "")
        ]
        if not surviving_brs:
            continue

        for b_win in surviving_brs:
            yes_tok = str(_bf(b_win, "yes_token", "") or "")
            bk_yes = books_by_token.get(yes_tok)
            if not isinstance(bk_yes, Mapping):
                continue
            w_yes = _walk_side(bk_yes.get("bids"), minted_sh, is_ask=False)
            if w_yes is None:
                continue
            vwap_y, floor_y, depth_y = w_yes
            fr_y = float(_bf(b_win, "fee_rate", 0.0) or 0.0)
            fe_y = float(_bf(b_win, "fee_exponent", 1.0) or 1.0)
            fee_y = compute_exact_taker_fee_per_share(vwap_y, fr_y, fe_y)
            bid_net_ps = max(0.0, (vwap_y - fee_y) * eff_mult)
            edge_ps = bid_net_ps - ask_eff_ps
            if edge_ps >= float(min_net_edge_usd) and edge_ps > best_edge:
                best_edge = edge_ps
                max_sh = int(math.floor(min(depth_no, depth_y / max(eff_mult, 0.5)) / 1.15))
                exec_sh = max(int(sh_req), min(25, max_sh))
                dead_dict = {
                    "market_id": str(_bf(b_dead, "market_id", "") or ""),
                    "condition_id": str(_bf(b_dead, "condition_id", "") or ""),
                    "question_index": int(q_k),
                    "no_token": no_tok,
                    "yes_token": str(_bf(b_dead, "yes_token", "") or ""),
                    "label": str(_bf(b_dead, "label", f"Q{q_k}") or ""),
                    "fee_rate": fr_k,
                    "fee_exponent": fe_k,
                }
                win_q_idx = int(_bf(b_win, "question_index"))
                win_dict = {
                    "market_id": str(_bf(b_win, "market_id", "") or ""),
                    "condition_id": str(_bf(b_win, "condition_id", "") or ""),
                    "question_index": win_q_idx,
                    "yes_token": yes_tok,
                    "label": str(_bf(b_win, "label", "") or ""),
                    "fee_rate": fr_y,
                    "fee_exponent": fe_y,
                }
                retained_free = [
                    {
                        "market_id": str(_bf(bx, "market_id", "") or ""),
                        "condition_id": str(_bf(bx, "condition_id", "") or ""),
                        "question_index": int(_bf(bx, "question_index")),
                        "yes_token": str(_bf(bx, "yes_token", "") or ""),
                        "label": str(_bf(bx, "label", "") or ""),
                    }
                    for bx in surviving_brs
                    if int(_bf(bx, "question_index")) != win_q_idx
                ]
                all_surv_dicts = [
                    {
                        "market_id": str(_bf(bx, "market_id", "") or ""),
                        "condition_id": str(_bf(bx, "condition_id", "") or ""),
                        "question_index": int(_bf(bx, "question_index")),
                        "yes_token": str(_bf(bx, "yes_token", "") or ""),
                        "label": str(_bf(bx, "label", "") or ""),
                    }
                    for bx in surviving_brs
                ]
                best_hit = {
                    "mode": "NR_M1_DEAD_SEED_OVERROUND",
                    "nr_m1_zero_loss_verified": True,
                    "neg_risk_market_id": nrm_id,
                    "dead_question_index": int(q_k),
                    "shares": exec_sh,
                    "ask_eff_per_share": round(ask_eff_ps, 6),
                    "bid_net_per_share": round(bid_net_ps, 6),
                    "net_edge_per_share": round(edge_ps, 6),
                    "fallback_hold_floor_edge_per_share": round(eff_mult - ask_eff_ps, 6),
                    "no_legs": [{"token_id": no_tok, "bracket": dead_dict, "walk": {"vwap": vwap_no, "worst_px": worst_no}}],
                    "yes_sell_legs": [{"token_id": yes_tok, "bracket": win_dict, "walk": {"vwap": vwap_y, "worst_px": floor_y}}],
                    "retained_free_yes_brackets": retained_free,
                    "surviving_yes_brackets": all_surv_dicts,
                }
    return best_hit


# ---------------------------------------------------------------------------
# 3. Family II: `S2_RTDS` 60s TWAP, `D1` Telescoping, `B1` One-Touch/Noon, `EQ1` Pyth Equity
# ---------------------------------------------------------------------------


def is_cme_metals_maintenance_window(ts: float) -> bool:
    """True during daily `17:00–18:00 ET` CME Globex / Chainlink Forex break and `Fri 17:00 ET..Sun 18:00 ET` close."""
    et_dt = datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone(get_us_eastern_tz())
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
    for asset_sym in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "HYPE", "ZEC", "XAU", "XAG"):
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
        def _ingest_shm_side(sb: Any) -> None:
            if not isinstance(sb, dict):
                return
            tk_id = str(sb.get("token_id") or "")
            age_ms = float(sb.get("age_book_ms") if sb.get("age_book_ms") is not None else 9999.0)
            if tk_id and age_ms <= 950.0:
                rb = [r for r in (sb.get("raw_top_bids") or []) if isinstance(r, (list, tuple)) and len(r) >= 2 and 0.0 < float(r[0]) < 1.0 and float(r[1]) > 0]
                ra = [r for r in (sb.get("raw_top_asks") or []) if isinstance(r, (list, tuple)) and len(r) >= 2 and 0.0 < float(r[0]) < 1.0 and float(r[1]) > 0]
                raw_bb = float(sb.get("best_bid") or 0.0)
                raw_ba_v = sb.get("best_ask")
                raw_ba = float(raw_ba_v) if raw_ba_v is not None else 0.0
                asz_s = float(sb.get("ask_size_l1") or sb.get("ask_depth_1c_shares") or 0.0)
                has_real_ba = (0.0 < raw_ba < 1.0) or (raw_ba >= 1.0 and (bool(ra) or asz_s > 0.0))
                bb_s = max((float(r[0]) for r in rb), default=(raw_bb if 0.0 < raw_bb < 1.0 else 0.0))
                ba_s = min((float(r[0]) for r in ra), default=(raw_ba if 0.0 < raw_ba < 1.0 else 0.0))
                is_x = bool(sb.get("is_crossed")) or (raw_bb > 0.0 and has_real_ba and raw_bb >= raw_ba) or (bb_s > 0.0 and ba_s > 0.0 and bb_s >= ba_s)
                if (rb or ra) and not is_x:
                    raw_tk = sb.get("minimum_tick_size") or sb.get("tick_size")
                    if raw_tk in (None, ""):
                        has_3dec = any(
                            abs(round(float(r[0]) * 100.0) - float(r[0]) * 100.0) > 1e-6
                            and (bb_s < 0.95 or float(r[0]) >= 0.95)
                            for r in (rb + ra)
                        )
                        if has_3dec:
                            raw_tk = "0.001"
                        elif bb_s < 0.96 and (ba_s <= 0.0 or ba_s <= 0.96):
                            raw_tk = "0.01"
                    shm_bk_entry: Dict[str, Any] = {
                        "bids": [{"price": str(r[0]), "size": str(r[1])} for r in rb],
                        "asks": [{"price": str(r[0]), "size": str(r[1])} for r in ra],
                    }
                    if raw_tk not in (None, ""):
                        shm_bk_entry["minimum_tick_size"] = str(raw_tk)
                    shm_books[tk_id] = shm_bk_entry

        exp_1h = float(d.get("expiry_ts_1h") or 0.0)
        op_1h = float(d.get("finalized_1h_open") or 0.0)
        if exp_1h > now_ts + 3.0 and op_1h > 0.0 and isinstance(open_cache, dict):
            ck_1h = f"{asset_sym}_1h_{int(round(exp_1h)) - 3600}"
            if ck_1h not in open_cache:
                open_cache[ck_1h] = (exp_1h, op_1h)
            src_map[ck_1h] = (exp_1h, "REST_VERIFIED")
        for side_root in ("UP", "DOWN"):
            _ingest_shm_side(d.get(side_root))

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
                _ingest_shm_side(mh.get(side_k))
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

    ast_s2_u = str(spec.asset or "").strip().upper()
    is_s2_tier1 = ast_s2_u in {"BTC", "ETH", "SOL", "XRP"}
    is_s2_tier3 = ast_s2_u in {"ZEC", "HYPE", "DOGE", "BNB"}
    max_s2_mkr_rem = 16.0 if is_s2_tier3 else (38.0 if is_s2_tier1 else 26.0)
    if 5.0 <= rem_sec <= max_s2_mkr_rem and hasattr(daemon, "emit_live_single_leg_maker_lock_candidate"):
        bids_w = sorted(
            [(float(b["price"]), float(b["size"])) for b in (bk.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
            key=lambda r: -r[0],
        )
        win_bid = bids_w[0][0] if bids_w else 0.0
        top3_bid_usd = sum(p * s for p, s in bids_w[:3])
        tier3_flow_ok = (not is_s2_tier3) or (win_bid >= 0.85 and top3_bid_usd >= 15.0)
        if 0.50 <= win_bid <= 0.997 and tier3_flow_ok:
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
            if is_s2_tier1:
                req_z_mk = 3.85 if rem_sec > 28.0 else 3.20
                req_adv_mk = 28.0 if rem_sec > 28.0 else 20.0
            elif is_s2_tier3:
                req_z_mk = 4.20
                req_adv_mk = 30.0
            else:
                req_z_mk = 4.20 if rem_sec > 20.0 else 3.50
                req_adv_mk = 32.0 if rem_sec > 20.0 else 24.0
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
                    "leg_a_market_fee_rate": float(spec.fee_rate),
                    "leg_a_fee_exponent": float(spec.fee_exponent),
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
    "NR0_ZERO_FEE_SLATE_ARB",
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


def compute_dynamic_riskless_tier_caps(
    total_equity_usd: float,
    rb: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Dynamic multi-tier riskless capital & slot scaling ($75.62 Seed -> $125 -> $140 -> $300 -> $1,000+)."""
    cfg = rb if isinstance(rb, Mapping) else {}
    eq = max(0.0, float(total_equity_usd or 0.0))
    rw_unlock = float(cfg.get("reward_dynamic_unlock_equity_usd", 125.0) or 125.0)
    ps_unlock = float(cfg.get("pre_split_dynamic_unlock_equity_usd", 140.0) or 140.0)
    seed_rw_cap = float(cfg.get("reward_harvester_cap_usd_seed", 12.0) or 12.0)
    rw_cap = round(min(250.0, max(21.0, eq * 0.175)), 2) if eq >= rw_unlock else seed_rw_cap
    ps_enabled = bool(cfg.get("enable_pre_split_overround_gun", False)) or (eq >= ps_unlock)
    ps_cap = (
        round(min(60.0, max(15.0, eq * 0.12)), 2)
        if eq >= ps_unlock
        else float(cfg.get("pre_split_inventory_cap_usd", 12.0) or 12.0)
    )
    max_per_evt = 1 if eq < 150.0 else (2 if eq < 400.0 else 3)
    explicit_evt_cap = float(cfg.get("max_event_notional_usd", 0.0) or 0.0)
    if explicit_evt_cap > 0.0:
        max_evt_usd = round(explicit_evt_cap, 2)
    elif eq <= 0.0:
        max_evt_usd = 25.0
    elif eq < 150.0:
        max_evt_usd = round(min(45.0, max(20.0, eq * 0.28)), 2)
    else:
        max_evt_usd = round(min(150.0, max(45.0, eq * 0.32)), 2)
    return {
        "reward_harvester_cap_usd": rw_cap,
        "reward_unlocked": bool(eq >= rw_unlock),
        "pre_split_enabled": ps_enabled,
        "pre_split_cap_usd": ps_cap,
        "max_concurrent_intents_per_event": max_per_evt,
        "max_event_notional_usd": max_evt_usd,
    }


_SYNTH_EVENT_ID_PREFIXES: Tuple[str, ...] = (
    "WS_SNIPE_",
    "CLINCH_SPLIT_",
    "COMP_RESID_",
    "SINGLE_LEG_",
    "MULTI_LEG_BUNDLE_",
    "MULTI_LEG_RESIDUAL",
    "LOCK1_",
    "MKR_LOCK1_",
    "CWATCH_",
    "CLINCH_WS_",
    "MLBOX_",
    "CTFOVR_",
    "D1_LIVE_",
    "COMPLETE_SET_LIVE_",
    "NEGRISK_2LEG_LIVE_",
)
_EMBEDDED_EVT_RE = re.compile(
    r"^(?:MULTI_LEG_BUNDLE|NEGRISK_2LEG|CTF_OVERROUND)_LIVE_[A-Za-z0-9_]+_\d+_(\d{4,})(?:_|$)",
    re.IGNORECASE,
)
_DEDUPE_EVT_RE = re.compile(
    r"^(?:WPRUNE_BSK|WPRUNE_2L|NR3_OVR|NRM1_WS)_(\d{4,})(?:_|$)",
    re.IGNORECASE,
)
_ICAO_SUFFIX_RE = re.compile(
    r"^(?:[A-Z][A-Z0-9_ -]*_)?(K[A-Z]{3}|C[A-Z]{3}|E[A-Z]{3}|L[A-Z]{3}|R[A-Z]{3}|Z[A-Z]{3}|V[A-Z]{3}|S[A-Z]{3}|Y[A-Z]{3})$"
)
_ICAO_ANY_SUFFIX_RE = re.compile(r"^(?:[A-Z][A-Z0-9_ -]*_)?(HKO|[A-Z]{4})$")


def _extract_weather_icao_key(cand: Mapping[str, Any]) -> str:
    exp_i = int(float(cand.get("expiry_ts") or cand.get("leg_a_expiry_ts") or cand.get("candle_expiry_ts") or 0.0))
    sl_u = str(cand.get("sleeve_source") or cand.get("sleeve") or "").strip().upper()
    ast_s = str(cand.get("asset") or "").strip().upper()
    m_any = _ICAO_ANY_SUFFIX_RE.match(ast_s)
    if m_any:
        st_c = m_any.group(1)
        if st_c == "HKO" or st_c in WUNDERGROUND_INTL_INTEGER_STATIONS:
            return f"EVTWX:{st_c}:{exp_i // 43200}"
    m_ic = _ICAO_SUFFIX_RE.match(ast_s)
    if m_ic and (sl_u.startswith(("W_PRUNE", "W1_", "W_SOLAR")) or "_" in ast_s or len(ast_s) == 4):
        if ast_s not in {"GOLD", "SILV", "XAUU", "XAGU", "SP50", "NDX1", "CLIN"}:
            return f"EVTWX:{m_ic.group(1)}:{exp_i // 43200}"
    return ""


def extract_gamma_parent_event_id(m: Optional[Mapping[str, Any]]) -> str:
    """Extracts a canonical parent Gamma event ID/slug from a market dict so multi-prop games share one event slot."""
    if not isinstance(m, Mapping):
        return ""
    for k in ("_parent_event_id", "event_id", "parent_event_id", "eventSlug", "event_slug", "negRiskMarketID"):
        v = str(m.get(k) or "").strip()
        if v:
            return v
    evs = m.get("events")
    if isinstance(evs, list) and evs and isinstance(evs[0], Mapping):
        for k in ("id", "slug", "ticker"):
            v = str(evs[0].get(k) or "").strip()
            if v:
                return v
    slug_s = str(m.get("slug") or "").strip()
    if slug_s:
        m_sl = re.sub(
            r"-(?:map-handicap|handicap|spread|total|over-under|o-u|1h|first-half|game-\d+|map-\d+|set-\d+)(?:-.*)?$",
            "",
            slug_s,
            flags=re.IGNORECASE,
        )
        if m_sl and m_sl != slug_s:
            return m_sl
    return ""


def extract_sll_event_group_key(cand: Optional[Mapping[str, Any]]) -> str:
    """Extracts a canonical parent-event key so multi-bracket slates (e.g. 16 Exact Score brackets or METAR ladders) share slot & concentration guards."""
    if not isinstance(cand, Mapping):
        return ""
    egk = str(cand.get("event_group_key") or "").strip()
    if egk:
        egk_body = egk[4:] if egk.upper().startswith("EVT:") else egk
        if not egk_body.upper().startswith(_SYNTH_EVENT_ID_PREFIXES):
            return egk
    for k in ("event_id", "parent_event_id", "neg_risk_market_id", "event_slug"):
        v = str(cand.get(k) or "").strip()
        if not v:
            continue
        if v.upper().startswith(_SYNTH_EVENT_ID_PREFIXES):
            m_emb = _EMBEDDED_EVT_RE.match(v)
            if m_emb:
                return f"EVT:{m_emb.group(1)}"
            continue
        return f"EVT:{v}"
    for dk_field in ("dedupe_key", "pair_dedupe_key", "box_id", "trade_id"):
        dk_v = str(cand.get(dk_field) or "").strip()
        if dk_v:
            m_dk = _DEDUPE_EVT_RE.match(dk_v) or _EMBEDDED_EVT_RE.match(dk_v)
            if m_dk:
                return f"EVT:{m_dk.group(1)}"
    q_txt = str(cand.get("question") or "").strip()
    exp_i = int(float(cand.get("expiry_ts") or cand.get("leg_a_expiry_ts") or cand.get("candle_expiry_ts") or 0.0))
    if q_txt:
        q_clean = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", q_txt)
        m_vs = re.search(
            r"([A-Za-z0-9 .'\-]{2,28}?)\s+vs\.?\s+([A-Za-z0-9 .'\-]{2,28}?)(?=\s*(?:[:\-–|?]|$|\b(?:map|game|set|total|handicap|spread|o/u|over|under|bo\d)\b))",
            q_clean,
            flags=re.IGNORECASE,
        )
        if m_vs:
            t1 = re.sub(
                r"(?i)^.*\b(?:(?:game|map|set)\s+\d+|handicap|spread|total|winner|moneyline)\s*[:\-–|]*\s*",
                "",
                m_vs.group(1),
            ).strip(" :-_|")
            t2 = m_vs.group(2).strip(" :-_|")
            if len(t1) >= 2 and len(t2) >= 2:
                pair_k = " VS ".join(sorted((t1.upper(), t2.upper())))
                return f"EVTMATCH:{pair_k}:{exp_i // 7200}"
    wx_k = _extract_weather_icao_key(cand)
    if wx_k:
        return wx_k
    reg = str(cand.get("regime") or "").strip()
    lbl = str(cand.get("leg_a_label") or cand.get("title") or "").strip()
    ast_s = str(cand.get("asset") or "").strip().upper()
    if lbl and lbl.lower() not in {"lock", "bundle", "resid", "clinch_ws_snipe"}:
        base_lbl = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", lbl)
        base_lbl = re.sub(r"(?i)^\s*(?:exact\s+score|spread|total|over/under|o/u)\s*[:\-–|]*\s*", "", base_lbl)
        base_lbl = re.sub(r"(?i)\b(?:game|map|set)\s+\d+\s*[:\-–|]*\s*", " ", base_lbl)
        base_lbl = re.sub(r"(?i)\b(?:exact\s+score|dead\s+no|reward\s+carry\s+no)\b.*$", "", base_lbl)
        base_lbl = re.sub(r"\s+\d+\s*[-:]\s*\d+(?:\s*°?[CFcf%])?\b", " vs ", base_lbl)
        base_lbl = re.sub(r"[:\-–|]\s*(?:>=|<=|>|<)?\s*-?\d+(?:\.\d+)?\s*(?:°?[CFcf%]|pts|goals)?.*$", "", base_lbl)
        base_lbl = re.sub(r"\s+", " ", base_lbl).strip(" :-_|")
        m_lbl_vs = re.search(
            r"([A-Za-z0-9 .'\-]{2,28}?)\s+vs\.?\s+([A-Za-z0-9 .'\-]{2,28}?)(?=\s*(?:[:\-–|?]|$|\b(?:total|handicap|spread|o/u|over|under|bo\d|winner|yes|no)\b))",
            base_lbl,
            flags=re.IGNORECASE,
        )
        if m_lbl_vs:
            lt1 = re.sub(r"(?i)^.*\b(?:esports|dota\s*2|cs2|lol|valorant|nba|nfl|nhl|mlb|soccer|tennis|sports_child_moneyline|sports_child_totals)\s+", "", m_lbl_vs.group(1)).strip(" :-_|")
            lt2 = re.sub(r"(?i)\s+\b(?:yes|no)\b.*$", "", m_lbl_vs.group(2)).strip(" :-_|")
            if len(lt1) >= 2 and len(lt2) >= 2:
                pair_lk = " VS ".join(sorted((lt1.upper(), lt2.upper())))
                return f"EVTMATCH:{pair_lk}:{exp_i // 7200}"
        if len(base_lbl) >= 6:
            return f"EVTLBL:{ast_s}:{base_lbl[:40].upper()}:{exp_i // 900}"
    if ast_s and exp_i > 0 and ("EXACT_SCORE" in reg.upper() or ast_s.endswith("_K")):
        return f"EVTAST:{ast_s}:{exp_i // 900}"
    mid = str(cand.get("leg_a_market_id") or cand.get("market_id") or "").strip()
    return f"MKT:{mid}" if mid else ""


def extract_canonical_event_keys(cand: Optional[Mapping[str, Any]]) -> set[str]:
    """Returns all canonical event group aliases (e.g. both `EVT:318559` and `EVTWX:KMIA:41530`) for cross-box deduplication."""
    if not isinstance(cand, Mapping):
        return set()
    out: set[str] = set()
    pk = extract_sll_event_group_key(cand)
    if pk:
        out.add(pk)
    wx_k = _extract_weather_icao_key(cand)
    if wx_k:
        out.add(wx_k)
    return out


def resolve_canonical_fee_source(fee_rate: float, sleeve_src: str = "", explicit_source: str = "") -> str:
    """Maps authoritative fee rate + sleeve into canonical `fee_source` (`zero_fees`, `weather_fees_v2`, `sports_fees_v2`, `crypto_fees_v2`)."""
    fr = max(0.0, float(fee_rate or 0.0))
    if fr <= 1e-9:
        return "zero_fees"
    exp_s = str(explicit_source or "").strip()
    if exp_s and exp_s not in {"crypto_fees_v2", "zero_fees"}:
        return exp_s
    sl_u = str(sleeve_src or "").strip().upper()
    if sl_u.startswith(("W_PRUNE", "W1_")) or "WEATHER" in sl_u or "METAR" in sl_u:
        return "weather_fees_v2"
    if any(t in sl_u for t in ("SPORT", "NBA", "NFL", "SOCCER", "TENNIS", "ESPORT")) or sl_u.startswith(("SP", "SOC", "TEN", "API", "CL1_", "DC1_", "LP_COMP1_", "MOO_")):
        return "sports_fees_v2"
    return exp_s or "crypto_fees_v2"


def check_per_event_concentration_cap(
    harvester: Any,
    cand: Optional[Mapping[str, Any]],
    market_ids: Optional[Sequence[str]] = None,
    now_ts: Optional[float] = None,
    *,
    enforce_override: bool = False,
    min_headroom_usd: float = 5.0,
    exclude_intent_ids: Optional[Sequence[str]] = None,
) -> Tuple[bool, str, float, str]:
    """
    Unified cross-sleeve per-event slot & USD concentration guard across `WS_SNIPE`, Taker/Maker `SINGLE_LEG_LOCK`,
    `MULTI_LEG_BUNDLE`, `NEGRISK_2LEG`, and `COMPLETE_SET`.
    Returns `(allowed, reject_reason, remaining_event_headroom_usd, primary_event_group_key)`.
    """
    evt_k = extract_sll_event_group_key(cand)
    if harvester is None or not isinstance(cand, Mapping) or not evt_k:
        return True, "", 9999.0, evt_k
    sl_src = str(cand.get("sleeve_source") or cand.get("sleeve") or "").strip()
    btype = str(cand.get("box_type") or "").strip().upper()
    rem_s = float(cand.get("rem_sec") or 9999.0)
    if sl_src in FAST_GUN_S2_SLEEVES or (btype == "DOMINANCE" and rem_s <= 960.0 and sl_src == "D1_SAME_ORACLE_DOMINANCE_BOX"):
        return True, "", 9999.0, evt_k
    ex = getattr(harvester, "executor", None)
    enforce = bool(
        enforce_override
        or getattr(harvester, "enforce_event_concentration_cap", False)
        or getattr(harvester, "enforce_bond1_smart_queue", False)
        or (
            not getattr(harvester, "dry_run", True)
            and getattr(ex, "client", None) is not None
            and getattr(getattr(ex, "client", None), "_mock_children", None) is None
            and "execute_snipe_order" not in getattr(ex, "__dict__", {})
            and "place_fok_order" not in getattr(ex, "__dict__", {})
            and "execute_fok_order" not in getattr(ex, "__dict__", {})
            and "post_maker_entry_order" not in getattr(ex, "__dict__", {})
        )
    )
    if not enforce:
        return True, "", 9999.0, evt_k
    from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

    rb_cfg = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
    if not bool(rb_cfg.get("enable_event_slot_diversification", True)):
        return True, "", 9999.0, evt_k
    now_f = float(time.time() if now_ts is None else now_ts)
    stalk_map = getattr(harvester, "_sll_event_stalk_until", None) or {}
    cand_keys = extract_canonical_event_keys(cand)
    for ck in cand_keys:
        if float(stalk_map.get(ck, 0.0) or 0.0) > now_f:
            return False, "EVENT_STALKER_COOLDOWN", 0.0, evt_k

    act_pos = getattr(harvester, "active_positions", None) or {}
    pend_int = getattr(harvester, "pending_entry_intents", None) or {}
    prepost_evts = getattr(harvester, "_prepost_sll_events", None) or {}
    excl_ids = {str(x).strip() for x in (exclude_intent_ids or ()) if str(x or "").strip()}
    collat_raw = getattr(harvester, "_last_known_collateral", None)
    collat_f = max(0.0, float(collat_raw if collat_raw is not None else 75.0))
    open_eq = sum(
        float(p.get("notional_usd", 0.0) or 0.0)
        for p in act_pos.values()
        if isinstance(p, Mapping) and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT" and p.get("resolved_winning_outcome") is None
    )
    tot_eq = max(25.0, collat_f + open_eq)
    caps = compute_dynamic_riskless_tier_caps(tot_eq, rb_cfg)
    max_slots = int(caps.get("max_concurrent_intents_per_event", 1) or 1)
    max_evt_usd = float(caps.get("max_event_notional_usd", 25.0) or 25.0)

    mset = {str(m).strip() for m in (market_ids or ()) if str(m or "").strip()}
    if not mset:
        m0 = str(cand.get("leg_a_market_id") or cand.get("market_id") or "").strip()
        if m0:
            mset.add(m0)

    seen_slot_groups: set[str] = set()
    other_mkt_slot_groups: set[str] = set()
    used_evt_usd = 0.0
    for pid, p in act_pos.items():
        if not isinstance(p, Mapping):
            continue
        if str(p.get("status") or "") == "AWAITING_ONCHAIN_SETTLEMENT" or p.get("resolved_winning_outcome") is not None:
            continue
        p_keys = extract_canonical_event_keys(p)
        if not (cand_keys & p_keys):
            continue
        used_evt_usd += max(0.0, float(p.get("notional_usd", 0.0) or 0.0))
        grp_id = str(p.get("box_id") or p.get("trade_id") or pid)
        seen_slot_groups.add(grp_id)
        p_mid = str(p.get("market_id") or "").strip()
        if not mset or p_mid not in mset:
            other_mkt_slot_groups.add(grp_id)

    for ik, iv in pend_int.items():
        if str(ik).strip() in excl_ids:
            continue
        if not isinstance(iv, Mapping) or not iv.get("live_maker_anchor_inflight"):
            continue
        i_keys = extract_canonical_event_keys(iv)
        if not (cand_keys & i_keys):
            continue
        used_evt_usd += max(0.0, float(iv.get("notional_usd", 0.0) or 0.0))
        grp_id = f"INTENT:{iv.get('inflight_key') or ik}"
        seen_slot_groups.add(grp_id)
        i_mid = str(iv.get("market_id") or "").strip()
        if not mset or i_mid not in mset:
            other_mkt_slot_groups.add(grp_id)

    for pk, pv in prepost_evts.items():
        pk_s = str(pk).strip()
        if pk_s in excl_ids or pk_s in pend_int or not isinstance(pv, Mapping):
            continue
        pv_keys = extract_canonical_event_keys(pv)
        if not (cand_keys & pv_keys):
            continue
        used_evt_usd += max(0.0, float(pv.get("notional_usd", 0.0) or 0.0))
        grp_id = f"PREPOST:{pv.get('inflight_key') or pk_s}"
        seen_slot_groups.add(grp_id)
        pv_mid = str(pv.get("market_id") or "").strip()
        if not mset or pv_mid not in mset:
            other_mkt_slot_groups.add(grp_id)

    is_standalone_mkt_only = bool(cand_keys) and all(str(k).startswith("MKT:") for k in cand_keys)
    rem_evt_usd = 9999.0 if (is_standalone_mkt_only and used_evt_usd <= 0.0) else round(max(0.0, max_evt_usd - used_evt_usd), 4)
    if len(other_mkt_slot_groups) >= max_slots:
        return False, "MAX_CONCURRENT_PER_EVENT_REACHED", rem_evt_usd, evt_k
    if len(seen_slot_groups) >= max_slots and btype in {"SINGLE_LEG_MAKER_LOCK", "MULTI_LEG_BUNDLE", "NEGRISK_2LEG", "COMPLETE_SET"}:
        return False, "MAX_CONCURRENT_PER_EVENT_REACHED", rem_evt_usd, evt_k
    if rem_evt_usd < float(min_headroom_usd):
        return False, "MAX_EVENT_NOTIONAL_CAP_REACHED", rem_evt_usd, evt_k
    return True, "", rem_evt_usd, evt_k


def cap_bond1_maker_for_gatling_reserve(
    harvester: Any,
    budget: float,
    collat_f: float,
    sll_used_u: float,
    rb_cfg: Optional[Mapping[str, Any]],
    inflight_s2_usd: float = 0.0,
    *,
    sleeve_src: str = "",
    post_vel_preempt: bool = False,
    now_ts: Optional[float] = None,
) -> float:
    """
    Reserves `max($20.00, 28% * NAV, gatling_fast_gun_reserve_usd)` of unencumbered free cash
    against `TTE > 10m` `BOND1` carry fills so passive carry never starves `<=90s` `S2` / `<15m` `D1` bursts,
    subtracting `inflight_s2_usd` because `collat_f` already deducted active `S2` Maker intents.
    Also carves out 1 dedicated micro-slot (`reward_reserved_slot_usd_seed`) for `MKR_REWARD_LOCKED_CARRY`
    only when reward-carry sizing is dynamically unlocked (`>= $125` equity) or an active reward candidate arrived recently.
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
    s2_in_f = max(0.0, float(inflight_s2_usd or 0.0))
    total_b1_nav = float(collat_f) + float(sll_used_u) + s2_in_f
    raw_paused = rb.get("paused_riskless_sleeves")
    paused_set = (
        {str(s).strip().upper() for s in raw_paused if str(s or "").strip()}
        if isinstance(raw_paused, (list, tuple, set, frozenset))
        else set()
    )
    if paused_set and FAST_GUN_S2_SLEEVES.issubset(paused_set):
        paused_floor = max(0.0, float(rb.get("paused_s2_reserve_floor_usd", 2.0) or 0.0))
        now_chk_r = float(time.time() if now_ts is None else now_ts)
        frozen_uma_u = sum(
            float(p.get("notional_usd", 0.0) or 0.0)
            for p in (getattr(harvester, "active_positions", None) or {}).values()
            if isinstance(p, Mapping)
            and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
            and (
                is_post_expiry_uma_frozen_lock(p, now_chk_r)
                or (0.0 < float(p.get("candle_expiry_ts", 0.0) or 0.0) <= now_chk_r)
            )
        )
        liquid_b1_nav = max(float(collat_f), total_b1_nav - frozen_uma_u)
        adaptive_tkr_floor = (
            min(13.50, round(max(0.0, liquid_b1_nav - 28.0) * 0.50, 2))
            if (liquid_b1_nav >= 34.0 and frozen_uma_u < 15.0)
            else 0.0
        )
        gatling_reserve_usd = max(paused_floor, adaptive_tkr_floor)
    else:
        base_reserve = max(20.0, float(rb.get("gatling_fast_gun_reserve_usd", 20.0) or 20.0))
        gatling_reserve_usd = max(base_reserve, round(total_b1_nav * 0.28, 2))
    eff_reserve = max(0.0, round(gatling_reserve_usd - s2_in_f, 2))
    sl_up = str(sleeve_src or "").upper()
    rw_slot_cfg = float(rb.get("reward_reserved_slot_usd_seed", 0.0) or 0.0)
    dyn_caps = compute_dynamic_riskless_tier_caps(total_b1_nav, rb)
    explicit_rw_test = bool(getattr(harvester, "enforce_reward_slot_reserve", False))
    recent_rw_cand = (time.time() - float(getattr(harvester, "_last_rw_carry_cand_ts", 0.0) or 0.0)) <= 300.0
    rw_live_allowed = (
        "MKR_REWARD_LOCKED_CARRY" not in paused_set
        and not bool(rb.get("strict_pure_riskless_mode", False))
    )
    if (
        rw_slot_cfg > 0.0
        and not post_vel_preempt
        and sl_up != "MKR_REWARD_LOCKED_CARRY"
        and sl_up not in FAST_GUN_S2_SLEEVES
        and bool(rb.get("enable_reward_locked_carry_live_bridge", False))
        and total_b1_nav >= 55.0
        and (explicit_rw_test or (live_real_ex and rw_live_allowed and (dyn_caps["reward_unlocked"] or recent_rw_cand)))
    ):
        has_rw_active = any(
            isinstance(p, Mapping)
            and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
            and str(p.get("sleeve") or "").upper() == "MKR_REWARD_LOCKED_CARRY"
            for p in (getattr(harvester, "active_positions", None) or {}).values()
        ) or any(
            isinstance(it, Mapping)
            and it.get("live_maker_anchor_inflight")
            and str(it.get("sleeve_source") or it.get("sleeve") or "").upper() == "MKR_REWARD_LOCKED_CARRY"
            for it in (getattr(harvester, "pending_entry_intents", None) or {}).values()
        )
        if not has_rw_active:
            rw_cap_eff = float(rb.get("reward_harvester_cap_usd_seed", 12.0) or 12.0) if explicit_rw_test else float(dyn_caps["reward_harvester_cap_usd"])
            rw_hold = min(rw_slot_cfg, rw_cap_eff)
            eff_reserve = round(eff_reserve + rw_hold, 2)
    free_after_reserve = max(0.0, float(collat_f) - eff_reserve)
    per_mkt_seed_cap = (
        round(max(18.0, (total_b1_nav - gatling_reserve_usd) * 0.55), 2)
        if total_b1_nav <= 120.0
        else float(budget)
    )
    return round(max(0.0, min(float(budget), free_after_reserve, per_mkt_seed_cap)), 2)


PASSIVE_CARRY_SLEEVES = frozenset({
    "BOND1_UMA_RESOLUTION_CARRY",
    "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
    "MKR_REWARD_LOCKED_CARRY",
    "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
    "W_PRUNE1_DEAD_NO_BOND",
    "UMA_READY1_LIVENESS_PRIORITY",
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
    exclude_inflight_key: str = "",
    exclude_inflight_keys: Optional[Any] = None,
    post_vel_preempt: bool = False,
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
    _struct_box_allow = {
        "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
        "COND1_MACRO_PARTITION_BOX",
        "CM_B3_PYTH_BARRIER_BOX",
        "NR0_ZERO_FEE_SLATE_ARB",
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
        "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
        "FED1_CENTRAL_BANK_LP_BOX",
        "SP1_NBA_ZERO_FEE_BOX",
    }
    if (
        not is_fast_gun_tier
        and bt_u not in {"SINGLE_LEG_MAKER_LOCK", "SINGLE_LEG_LOCK", "DOMINANCE"}
        and (own_grad or sl_u in _struct_box_allow)
        and 0.0 < rem_f <= 129600.0
    ):
        act_pos_sb = getattr(harvester, "active_positions", None) or {}
        struct_used = sum(
            float(p.get("notional_usd", 0.0) or 0.0)
            for p in act_pos_sb.values()
            if isinstance(p, Mapping)
            and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
            and not is_post_expiry_uma_frozen_lock(p, now_f)
            and str(p.get("box_type") or "").upper() not in {"SINGLE_LEG_MAKER_LOCK", "SINGLE_LEG_LOCK", "DOMINANCE"}
        )
        nav_sb = max(10.0, float(collat_f) + float(cur_exp))
        struct_slot_cap = max(12.0, round(nav_sb * 0.22, 2))
        if struct_used + 5.0 <= struct_slot_cap:
            s2_floor_u = min(10.50, round(nav_sb * 0.14, 2))
            return maybe_cap_gatling_budget_sync(
                harvester,
                legacy_budget,
                collat_f,
                cur_exp,
                box_type,
                sleeve_src,
                own_grad,
                rb,
                cap_usd=min(float(cap_usd), round(struct_slot_cap - struct_used, 2)),
                reserve_u=s2_floor_u,
                override_legacy_cap=True,
            )
    if not is_fast_gun_tier and (sl_u in PASSIVE_CARRY_SLEEVES or rem_f > 600.0):
        act_pos = getattr(harvester, "active_positions", None) or {}
        raw_pend = getattr(harvester, "pending_entry_intents", None) or {}
        excl_set = {str(k) for k in (exclude_inflight_keys or ()) if str(k or "")}
        if exclude_inflight_key:
            excl_set.add(str(exclude_inflight_key))
        pend_int = (
            {k: v for k, v in raw_pend.items() if not (isinstance(v, Mapping) and str(v.get("inflight_key") or "") in excl_set)}
            if (excl_set and isinstance(raw_pend, Mapping))
            else raw_pend
        )
        inflight_s2_u = sum(
            float(i.get("notional_usd", 0.0) or 0.0)
            for i in pend_int.values()
            if isinstance(i, Mapping)
            and i.get("live_maker_anchor_inflight")
            and str(i.get("sleeve_source") or i.get("sleeve") or "").upper() in FAST_GUN_S2_SLEEVES
        )
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
        non_s2_used = max(carry_used, max(0.0, float(cur_exp) - inflight_s2_u))
        base_for_cap = float(legacy_budget) if float(legacy_budget) > 0.0 else float(collat_f)
        capped = cap_bond1_maker_for_gatling_reserve(
            harvester,
            base_for_cap,
            collat_f,
            non_s2_used,
            rb,
            inflight_s2_usd=inflight_s2_u,
            sleeve_src=sl_u,
            post_vel_preempt=post_vel_preempt,
            now_ts=now_f,
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
            slow_cap_rem = max(0.0, round(max(20.0, nav_tot * (0.48 if live_real_ex else 0.38)) - slow_used, 2))
            capped = min(capped, slow_cap_rem)
        fanout_seed_u = (
            float(rb.get("reward_harvester_cap_usd_seed") or 0.0)
            if sl_u == "MKR_REWARD_LOCKED_CARRY"
            else float(rb.get("bond1_maker_fanout_clip_usd_seed") or 0.0)
        )
        if fanout_seed_u > 0.0 and bt_u == "SINGLE_LEG_MAKER_LOCK" and (float(collat_f) + float(cur_exp)) < 150.0:
            if live_real_ex and sl_u != "MKR_REWARD_LOCKED_CARRY":
                fanout_seed_u = max(8.00, round(fanout_seed_u * ((max(75.5, float(collat_f) + float(cur_exp)) / 75.5) ** 0.70), 2))
            capped = min(capped, fanout_seed_u)
        return round(max(0.0, capped), 2)

    eff_fast_cap = (
        min(float(cap_usd), 22.50)
        if (bt_u == "SINGLE_LEG_MAKER_LOCK" and sl_u in FAST_GUN_S2_SLEEVES and not own_grad)
        else float(cap_usd)
    )
    if bt_u == "SINGLE_LEG_MAKER_LOCK" and sl_u in FAST_GUN_S2_SLEEVES:
        s2_slots = resolve_s2_maker_concurrent_cap(harvester, rb)
        if s2_slots >= 2 and 13.5 <= float(collat_f) < 38.0:
            s2_act_cnt = sum(
                1
                for i in ((getattr(harvester, "pending_entry_intents", None) or {}).values())
                if isinstance(i, Mapping)
                and i.get("live_maker_anchor_inflight")
                and str(i.get("sleeve_source") or i.get("sleeve") or "").upper() in FAST_GUN_S2_SLEEVES
            ) + len(getattr(harvester, "_inflight_s2_maker_keys", None) or ())
            if s2_act_cnt <= 1:
                eff_fast_cap = min(eff_fast_cap, max(7.0, round(float(collat_f) * 0.52, 2)))
    if bt_u == "SINGLE_LEG_MAKER_LOCK" and sl_u not in FAST_GUN_S2_SLEEVES and (float(collat_f) + float(cur_exp)) < 150.0:
        fanout_fast_u = (
            float(rb.get("reward_harvester_cap_usd_seed") or 0.0)
            if sl_u == "MKR_REWARD_LOCKED_CARRY"
            else float(rb.get("bond1_maker_fanout_clip_usd_seed") or 0.0)
        )
        if fanout_fast_u > 0.0:
            if live_real_ex and sl_u != "MKR_REWARD_LOCKED_CARRY":
                fanout_fast_u = max(8.00, round(fanout_fast_u * ((max(75.5, float(collat_f) + float(cur_exp)) / 75.5) ** 0.70), 2))
            eff_fast_cap = min(eff_fast_cap, fanout_fast_u)
    return maybe_cap_gatling_budget_sync(
        harvester,
        legacy_budget,
        collat_f,
        cur_exp,
        box_type,
        sleeve_src,
        own_grad,
        rb,
        cap_usd=eff_fast_cap,
        reserve_u=0.50,
        override_legacy_cap=True,
    )


def _interpret_delayed_recycle_poll_summary(
    ex: Any,
    res: Mapping[str, Any],
    oid: str,
    summary: Optional[Mapping[str, Any]],
    limit_price: Optional[float],
    *,
    fee_rate: float = 0.0,
    fee_exp: float = 1.0,
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
        is_settl_v = summary.get("is_settled")
        unsettled_m = (is_settl_v is False) if is_settl_v is not None else (st_u == "MATCHED")
        raw_cash = float(summary.get("cash") or 0.0)
        avg_px = float(summary.get("avg_price") or limit_price or 0.998)
        cash = raw_cash if raw_cash > 0.0 else round(m * max(float(limit_price or 0.0), avg_px), 6)
        cash_est = bool(summary.get("cash_is_estimated", summary.get("estimated", False)) or not term or unsettled_m or raw_cash <= 0.0)
        raw_fee = summary.get("fee")
        if raw_fee is not None:
            fee_v = float(raw_fee or 0.0)
            fee_est = bool(summary.get("fee_estimated", False))
        else:
            fee_v = round(m * compute_exact_taker_fee_per_share(avg_px, float(fee_rate or 0.0), float(fee_exp or 1.0)), 6)
            fee_est = bool(summary.get("fee_estimated", fee_v > 0.0))
        return {
            **dict(res),
            "outcome_unknown": False,
            "success": True,
            "orderID": oid,
            "matched_size": m,
            "taking_amount": cash,
            "taking_amount_missing": False,
            "taking_amount_estimated": cash_est,
            "fee_usd": fee_v,
            "fee_is_estimated": fee_est,
            "reservation_id": res_id,
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
    _fr_p = pos.get("fee_rate_applied")
    if _fr_p is None:
        _fr_p = pos.get("fee_rate_market", pos.get("fee_rate", 0.0))
    _fe_p = float(pos.get("fee_exponent_applied", pos.get("fee_exponent", 1.0)) or 1.0)
    steps = max(1, int(round(max(0.5, float(max_wait_sec)) / max(0.1, float(poll_interval_sec)))))
    last_resolved: Optional[Dict[str, Any]] = None
    res_id = res.get("reservation_id")
    for idx in range(steps):
        if idx > 0:
            await asyncio.sleep(float(poll_interval_sec))
        try:
            summ = await asyncio.to_thread(ex.get_order_fill_summary, oid, tok)
        except Exception:
            summ = None
        resolved = _interpret_delayed_recycle_poll_summary(
            ex, res, oid, summ, limit_price, fee_rate=float(_fr_p or 0.0), fee_exp=_fe_p
        )
        if resolved is not None:
            last_resolved = resolved
            if not resolved.get("success") or not resolved.get("taking_amount_estimated") or idx == steps - 1:
                if res_id and hasattr(ex, "release_inventory"):
                    ex.release_inventory(reservation_id=str(res_id))
                resolved["reservation_id"] = None
                resolved["_delayed_recycle_polled"] = True
                logger.info(
                    f"♻️ [DELAYED RECYCLE RESOLVED] order={oid} -> success={resolved.get('success')} "
                    f"matched={resolved.get('matched_size', 0.0):.2f} est={resolved.get('taking_amount_estimated')}"
                )
                return resolved
    if last_resolved is not None:
        if res_id and hasattr(ex, "release_inventory"):
            ex.release_inventory(reservation_id=str(res_id))
        last_resolved["reservation_id"] = None
        last_resolved["_delayed_recycle_polled"] = True
        return last_resolved
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
    _fr_p = pos.get("fee_rate_applied")
    if _fr_p is None:
        _fr_p = pos.get("fee_rate_market", pos.get("fee_rate", 0.0))
    _fe_p = float(pos.get("fee_exponent_applied", pos.get("fee_exponent", 1.0)) or 1.0)
    steps = max(1, int(round(max(0.5, float(max_wait_sec)) / max(0.1, float(poll_interval_sec)))))
    last_resolved: Optional[Dict[str, Any]] = None
    res_id = res.get("reservation_id")
    for idx in range(steps):
        if idx > 0:
            time.sleep(float(poll_interval_sec))
        try:
            summ = ex.get_order_fill_summary(oid, tok)
        except Exception:
            summ = None
        resolved = _interpret_delayed_recycle_poll_summary(
            ex, res, oid, summ, limit_price, fee_rate=float(_fr_p or 0.0), fee_exp=_fe_p
        )
        if resolved is not None:
            last_resolved = resolved
            if not resolved.get("success") or not resolved.get("taking_amount_estimated") or idx == steps - 1:
                if res_id and hasattr(ex, "release_inventory"):
                    ex.release_inventory(reservation_id=str(res_id))
                resolved["reservation_id"] = None
                resolved["_delayed_recycle_polled"] = True
                return resolved
    if last_resolved is not None:
        if res_id and hasattr(ex, "release_inventory"):
            ex.release_inventory(reservation_id=str(res_id))
        last_resolved["reservation_id"] = None
        last_resolved["_delayed_recycle_polled"] = True
        return last_resolved
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
    real_eq = collat + open_u
    nav = real_eq if real_eq > 0.0 else float(getattr(harvester, "max_exposure", 35.0) or 35.0)
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
        or str(pos.get("status") or "") not in {"POSITION_CONFIRMED", "PARTIALLY_FILLED"}
        or not bool(pos.get("inventory_reconciled", False))
        or pos.get("is_liquidating")
        or pos.get("exit_order_id")
        or pos.get("resolved_winning_outcome") is not None
    ):
        return False
    tte_rem = float(pos.get("candle_expiry_ts", 0.0) or 0.0) - float(now_ts)
    if tte_rem < 300.0 and not is_uma_post_expiry_recycle_safe(pos, tte_rem, book):
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
    prior_cash = float(pos.get("realized_exit_cash", 0.0) or 0.0)
    prior_fee = float(pos.get("realized_exit_fee", pos.get("realized_exit_fees", 0.0)) or 0.0)
    est_net_pnl = float(harvester.calculate_realized_cash_pnl(pos, prior_cash + rem_shrs * min_px, prior_fee + est_exit_fee))
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
        harvester.__dict__["_uma_early_recycle_count"] = int(harvester.__dict__.get("_uma_early_recycle_count", 0) or 0) + 1
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


_HTM_PASSIVE_MAKER_RECYCLE_SLEEVES: frozenset[str] = frozenset({
    "BOND1_UMA_RESOLUTION_CARRY",
    "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
    "MKR_LOCK1_POST_CLINCH_SWEEPER",
    "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
    "W_PRUNE1_DEAD_NO_BOND",
    "W_SOLAR1_POST_2351_LOCK",
    "W1_SOLAR_PEAK_LOCK",
    "W1_LOW_TROUGH_LOCK",
    "W1_METAR_FINAL_HIGH_LOCK",
    "W1_METAR_IRREVERSIBLE_NO_LOCK",
    "MKR_REWARD_LOCKED_CARRY",
    "SP2_NBA_ENDGAME_LOCK",
    "SP4_INGAME_LOCK",
    "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
    "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
    "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
    "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
    "TW1_COUNTING_TRUNCATION_AND_BOX",
    "UMA_READY1_LIVENESS_PRIORITY",
    "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
    "SOC2_EXACT_SCORE_2D_LATTICE",
    "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
    "B4_TOUCHED_BARRIER_WICK_LOCK",
    "GAS1_AAA_GASOLINE_LOCK",
    "U1_DAILY_UPDOWN_LOCK",
    "CM_B2_PYTH_SESSION_NO_LOCK",
    "CM_U1_PYTH_CLOSE_LOCK",
    "EQ1_TERMINAL_EQUITY_CLOSE_LOCK",
    "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
    "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",
})


def is_uma_post_expiry_recycle_safe(
    pos: Mapping[str, Any],
    raw_tte_rem: float,
    book: Optional[Mapping[str, Any]] = None,
) -> bool:
    """
    Returns True during the 2-hour post-expiry UMA liveness window (`-6900s <= raw_tte_rem <= -5s`)
    for undisputed non-Chainlink UMA `hold_to_maturity_lock` sleeves whose CLOB book is still open (`not 404`),
    allowing `$0.998 / $0.999` 0%-fee Maker & Taker profit-recycling instead of freezing capital for 2+ hours.
    """
    try:
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

        if not bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_uma_liveness_2h_recycle", True)):
            return False
    except Exception:
        pass
    sl_u = str(pos.get("sleeve") or "").strip().upper()
    if (
        sl_u not in _HTM_PASSIVE_MAKER_RECYCLE_SLEEVES
        or bool(pos.get("is_subhourly"))
        or pos.get("resolved_winning_outcome") is not None
        or str(pos.get("umaResolutionStatus") or pos.get("uma_resolution_status") or "").strip().lower() == "disputed"
        or bool(pos.get("_book_closed_404"))
        or not (-6900.0 <= float(raw_tte_rem) <= -5.0)
    ):
        return False
    if book is not None:
        has_lv = bool((book.get("bids") or []) or (book.get("asks") or []))
        if not has_lv:
            return False
    return True


async def maybe_manage_passive_htm_early_maker_recycle(
    harvester: Any,
    tid: str,
    pos: Dict[str, Any],
    book: Optional[Mapping[str, Any]],
    now_ts: float,
    open_oids: Optional[Set[str]] = None,
) -> bool:
    """
    v5.4.5 Passive `0%`-Fee Maker Early-Recycle Ladder (`$0.998 / $0.999`) for `hold_to_maturity_lock`:
      - Posts a `0%`-fee `postOnly=True` Maker `SELL` on reconciled, undisputed `0%`-fee single-leg locks:
          * `$0.998` when `entry_px <= 0.9935` and `tte_rem >= 1800s` (jumps ahead of `$0.999` asks for `5-15m` turnover)
          * `$0.999` when `entry_px <= 0.9965` and `tte_rem >= 480s`
      - Polls fills on every supervision tick (even if resting bids drop to `0`), closing immediately on fill.
      - Automatically cancels & releases inventory at `tte_rem < 360s` (`T-6m`) or when `best_b >= 0.998` covers
        full size so `AutoRedeemer` `$1.00` payout or instant `$0.998` Taker sweep is never encumbered.
    """
    if (
        getattr(harvester, "dry_run", True)
        or not bool(pos.get("hold_to_maturity_lock"))
        or not bool(pos.get("is_single_leg_lock"))
        or bool(pos.get("is_dominance_box"))
        or pos.get("is_liquidating")
        or pos.get("resolved_winning_outcome") is not None
    ):
        return False
    ex = getattr(harvester, "executor", None)
    if ex is None:
        return False
    token_id = str(pos.get("token_id") or "").strip()
    if not token_id:
        return False
    tte_rem = float(pos.get("candle_expiry_ts", 0.0) or 0.0) - float(now_ts)
    rem_shrs = float(pos.get("remaining_shares", pos.get("entry_shares", 0.0)) or 0.0)
    raw_bids = (book.get("bids") or []) if isinstance(book, Mapping) else []
    best_b = max(
        (
            float(b["price"] if isinstance(b, Mapping) else b[0])
            for b in raw_bids
            if float((b.get("size", 0.0) if isinstance(b, Mapping) else b[1]) or 0.0) > 0.0
        ),
        default=0.0,
    )
    bid_998_sh = sum(
        float(b["size"] if isinstance(b, Mapping) else b[1])
        for b in raw_bids
        if float((b.get("price", 0.0) if isinstance(b, Mapping) else b[0]) or 0.0) >= 0.998
        and float((b.get("size", 0.0) if isinstance(b, Mapping) else b[1]) or 0.0) > 0.0
    )

    exit_oid = str(pos.get("exit_order_id") or "").strip()
    if exit_oid and bool(pos.get("_htm_passive_recycle_active")):
        summary = (
            await asyncio.to_thread(ex.get_order_fill_summary, exit_oid, token_id)
            if hasattr(ex, "get_order_fill_summary")
            else None
        )
        if isinstance(summary, Mapping) and hasattr(harvester, "_record_order_summary"):
            if harvester._record_order_summary(pos, dict(summary), float(pos.get("target_exit_price", 0.999) or 0.999), taker=False):
                harvester.save_state()
        filled_s = float(pos.get("filled_exit_shares", 0.0) or 0.0)
        if filled_s > 0.0:
            pos["average_exit_price"] = round(float(pos.get("realized_exit_cash", 0.0) or 0.0) / filled_s, 4)
            if pos.get("status") == "POSITION_CONFIRMED":
                pos["status"] = "PARTIALLY_FILLED"
        rem_shrs = float(pos.get("remaining_shares", rem_shrs) or 0.0)
        if rem_shrs <= 0.02:
            if hasattr(ex, "release_inventory"):
                ex.release_inventory(reservation_id=exit_oid)
            _cm_oids = pos.setdefault("canceled_maker_exit_oids", [])
            if exit_oid not in _cm_oids:
                _cm_oids.append(exit_oid)
            pos["exit_order_id"] = None
            pos["_htm_passive_recycle_active"] = False
            if hasattr(ex, "invalidate_collateral_cache"):
                ex.invalidate_collateral_cache()
            harvester._pending_collateral_refresh = True
            harvester.__dict__["_uma_early_recycle_count"] = int(harvester.__dict__.get("_uma_early_recycle_count", 0) or 0) + 1
            logger.info(
                f"♻️ [HTM PASSIVE MAKER RECYCLE FILLED] {tid} ({pos.get('sleeve')}): "
                f"filled {filled_s:.2f} sh @ ${float(pos.get('average_exit_price') or pos.get('target_exit_price') or 0.998):.3f} (0% fee)"
            )
            harvester._close_position(tid, pos, "FILLED", "HTM_PASSIVE_MAKER_RECYCLE_FILLED", won=True)
            return True

        in_uma_2h = is_uma_post_expiry_recycle_safe(pos, tte_rem, book)
        sweep_998_ready = ((tte_rem >= 300.0 or in_uma_2h) and bid_998_sh >= rem_shrs and float(pos.get("target_exit_price") or 0.999) > 0.9981)
        _epx_cur = float(pos.get("entry_price") or 0.0)
        _post_age = float(now_ts) - float(pos.get("_htm_passive_post_ts", now_ts) or now_ts)
        stepdown_998_ready = (
            0.0 < _epx_cur <= 0.9955
            and filled_s <= 0.02
            and float(pos.get("target_exit_price") or 0.999) > 0.9981
            and _post_age >= 300.0
            and (tte_rem >= 900.0 or (in_uma_2h and tte_rem >= -4200.0))
            and best_b < 0.998 - 1e-6
        )
        need_cancel = (
            (0.0 < tte_rem < 360.0)
            or (tte_rem <= 0.0 and not in_uma_2h)
            or bool(pos.get("_book_closed_404"))
            or sweep_998_ready
            or stepdown_998_ready
            or bool((summary or {}).get("terminal"))
        )
        if need_cancel:
            cancel_res = (
                await asyncio.to_thread(ex.cancel_order, exit_oid)
                if (not bool((summary or {}).get("terminal")) and hasattr(ex, "cancel_order"))
                else {"is_canceled": True}
            )
            sum2 = (
                await asyncio.to_thread(ex.get_order_fill_summary, exit_oid, token_id)
                if hasattr(ex, "get_order_fill_summary")
                else summary
            )
            if isinstance(sum2, Mapping) and hasattr(harvester, "_record_order_summary"):
                harvester._record_order_summary(pos, dict(sum2), float(pos.get("target_exit_price", 0.999) or 0.999), taker=False)
            rem_shrs = float(pos.get("remaining_shares", rem_shrs) or 0.0)
            if rem_shrs <= 0.02:
                if hasattr(ex, "release_inventory"):
                    ex.release_inventory(reservation_id=exit_oid)
                _cm_oids = pos.setdefault("canceled_maker_exit_oids", [])
                if exit_oid not in _cm_oids:
                    _cm_oids.append(exit_oid)
                pos["exit_order_id"] = None
                pos["_htm_passive_recycle_active"] = False
                if hasattr(ex, "invalidate_collateral_cache"):
                    ex.invalidate_collateral_cache()
                harvester._pending_collateral_refresh = True
                harvester._close_position(tid, pos, "FILLED", "HTM_PASSIVE_MAKER_RECYCLE_FILLED", won=True)
                return True
            term_ok = bool(
                (isinstance(sum2, Mapping) and sum2.get("terminal"))
                or (isinstance(cancel_res, Mapping) and (cancel_res.get("is_canceled") or exit_oid in (cancel_res.get("canceled") or [])))
                or (open_oids is not None and exit_oid not in open_oids and not (cancel_res or {}).get("error"))
            )
            if term_ok:
                if hasattr(ex, "release_inventory"):
                    ex.release_inventory(reservation_id=exit_oid)
                _cm_oids = pos.setdefault("canceled_maker_exit_oids", [])
                if exit_oid not in _cm_oids:
                    _cm_oids.append(exit_oid)
                pos["exit_order_id"] = None
                pos["_htm_passive_recycle_active"] = False
                pos["status"] = "PARTIALLY_FILLED" if float(pos.get("filled_exit_shares", 0.0) or 0.0) > 0.0 else "POSITION_CONFIRMED"
                pos["exit_order_status"] = "HOLD_TO_MATURITY_LOCK"
                if stepdown_998_ready and not sweep_998_ready and (tte_rem >= 900.0 or (in_uma_2h and tte_rem >= -4200.0)):
                    pos["_htm_stepdown_998"] = True
                    pos["_last_htm_mkr_post_ts"] = 0.0
                    exit_oid = ""
                else:
                    pos["_last_htm_mkr_post_ts"] = float(now_ts)
                    harvester.save_state()
                    if sweep_998_ready:
                        return await maybe_early_profit_recycle_htm_lock(harvester, tid, pos, book, now_ts)
                    return False
            else:
                return True
        else:
            return True

    in_uma_2h_post = is_uma_post_expiry_recycle_safe(pos, tte_rem, book)
    if (
        exit_oid
        or str(pos.get("status") or "") not in {"POSITION_CONFIRMED", "PARTIALLY_FILLED"}
        or not bool(pos.get("inventory_reconciled", False))
        or rem_shrs < 5.0
        or (tte_rem < 480.0 and not in_uma_2h_post)
    ):
        return False
    sl_u = str(pos.get("sleeve") or "").strip().upper()
    if sl_u not in _HTM_PASSIVE_MAKER_RECYCLE_SLEEVES:
        return False
    if (float(now_ts) - float(pos.get("_last_htm_mkr_post_ts", 0.0) or 0.0)) < 20.0:
        return False
    entry_px = float(pos.get("entry_price") or 0.0)
    if entry_px <= 0.0 or entry_px > 0.9975:
        return False
    target_px = (
        0.998
        if (
            bool(pos.get("_htm_stepdown_998"))
            or (entry_px <= 0.9960 and (tte_rem >= 1800.0 or (in_uma_2h_post and tte_rem >= -4500.0)))
        )
        else 0.999
    )
    if target_px < entry_px + 0.0015 or best_b >= target_px - 1e-6:
        return False
    prior_mkr_cash = float(pos.get("realized_exit_cash", 0.0) or 0.0)
    prior_mkr_fee = float(pos.get("realized_exit_fee", pos.get("realized_exit_fees", 0.0)) or 0.0)
    if not hasattr(ex, "post_maker_exit_order"):
        return False
    tick_sz = 0.001
    if hasattr(ex, "get_token_tick_size"):
        try:
            tick_sz = float(ex.get_token_tick_size(token_id, price_hint=target_px))
        except TypeError:
            tick_sz = float(ex.get_token_tick_size(token_id))
        except Exception:
            tick_sz = 0.01
    if abs(tick_sz - 0.01) < 1e-9 and entry_px <= 0.985 and best_b < 0.99 - 1e-6:
        target_px = 0.99
    elif tick_sz > 0.001 + 1e-9:
        return False
    est_net_pnl = float(harvester.calculate_realized_cash_pnl(pos, prior_mkr_cash + rem_shrs * target_px, prior_mkr_fee))
    if est_net_pnl < max(0.02, rem_shrs * 0.0012):
        return False
    pos["_last_htm_mkr_post_ts"] = float(now_ts)
    m_res = await asyncio.to_thread(
        ex.post_maker_exit_order,
        token_id=token_id,
        price=target_px,
        size=rem_shrs,
        side="SELL",
        neg_risk=pos.get("neg_risk"),
    )
    if isinstance(m_res, Mapping) and m_res.get("success") and m_res.get("orderID"):
        posted_px = float(m_res.get("price") or target_px)
        if posted_px < entry_px + 0.0015:
            await asyncio.to_thread(ex.cancel_order, str(m_res["orderID"]))
            if hasattr(ex, "release_inventory"):
                ex.release_inventory(reservation_id=str(m_res["orderID"]))
            return False
        pos["exit_order_id"] = str(m_res["orderID"])
        pos["exit_order_size"] = float(rem_shrs)
        pos["target_exit_price"] = posted_px
        pos["exit_order_status"] = "RESTING_HTM_PASSIVE_RECYCLE"
        pos["_htm_passive_recycle_active"] = True
        pos["_htm_passive_post_ts"] = float(now_ts)
        harvester.save_state()
        logger.info(
            f"📌 [HTM PASSIVE MAKER RECYCLE POSTED] {tid} ({sl_u}): resting 0%-fee SELL {rem_shrs:.2f} sh "
            f"@ ${posted_px:.3f} (entry=${entry_px:.4f}, locked_early_net=${est_net_pnl:+.2f}, TTE={tte_rem/60.0:.1f}m)"
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

    _entry_fee_asset = str(pos.get("entry_fee_asset") or "").upper()
    _entry_cash_fee = (
        float(pos.get("entry_fee_cash_usd", 0.0) or 0.0)
        if _entry_fee_asset == "SHARES"
        else float(pos.get("entry_fee_cash_usd", pos.get("fee_usd", 0.0)) or 0.0)
    )
    _leg_notional = float(pos.get("notional_usd", 0.0) or 0.0)
    _raw_leg_pnl = round(float(cum_cash) - _leg_notional - _entry_cash_fee - float(cum_fee), 6)
    this_leg = {
        "trade_id": tid,
        "target_token": pos.get("target_token"),
        "market_id": pos.get("market_id"),
        "notional_usd": round(_leg_notional, 4),
        "entry_cash_fee_usd": round(_entry_cash_fee, 4),
        "payout_usd": round(float(cum_cash), 4),
        "exit_fee_usd": round(float(cum_fee), 4),
        "raw_pnl_usd": _raw_leg_pnl,
        "net_pnl_usd": round(float(net_pnl), 4),
        "close_reason": reason,
        "order_id": pos.get("order_id"),
        "entry_order_id": pos.get("entry_order_id"),
        "exit_order_id": pos.get("exit_order_id"),
        "unwind_order_id": pos.get("unwind_order_id"),
        "entry_fill_ids": list(pos.get("entry_fill_ids") or ()),
        "exit_fill_ids": list(pos.get("exit_fill_ids") or ()),
        "trade_ids": list(pos.get("trade_ids") or ()),
        "exit_trade_ids": list(pos.get("exit_trade_ids") or ()),
        "canceled_maker_exit_oids": list(pos.get("canceled_maker_exit_oids") or ()),
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
        tot_payout = round(sum(float(x.get("payout_usd", 0.0) or 0.0) for x in all_legs), 4)
        tot_exit_fee = round(sum(float(x.get("exit_fee_usd", 0.0) or 0.0) for x in all_legs), 4)
        raw_tot_pnl = sum(
            float(x["raw_pnl_usd"])
            if "raw_pnl_usd" in x and x["raw_pnl_usd"] is not None
            else (
                float(x.get("payout_usd", 0.0) or 0.0)
                - float(x.get("notional_usd", 0.0) or 0.0)
                - float(x.get("entry_cash_fee_usd", 0.0) or 0.0)
                - float(x.get("exit_fee_usd", 0.0) or 0.0)
            )
            for x in all_legs
        )
        cent_tot_pnl = round(raw_tot_pnl, 2)
        if cent_tot_pnl != 0.0:
            tot_pnl = cent_tot_pnl
        else:
            sub_tot_pnl = round(raw_tot_pnl, 4)
            tot_pnl = sub_tot_pnl if abs(sub_tot_pnl) >= 0.0001 else 0.0
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
    fee_exponent_outer: float = 1.0,
    fee_exponent_inner: float = 1.0,
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
        px_a, tok_a, cid_a, fr_a, fe_a, desc_a = (
            float(inner_down_ask),
            str(inner_down_token),
            str(inner_condition_id),
            float(fee_rate_inner),
            float(fee_exponent_inner),
            f"{inner_horizon}_DOWN",
        )
        px_b, tok_b, cid_b, fr_b, fe_b, desc_b = (
            float(outer_up_ask),
            str(outer_up_token),
            str(outer_condition_id),
            float(fee_rate_outer),
            float(fee_exponent_outer),
            f"{outer_horizon}_UP",
        )
        corridor = (float(outer_open), float(inner_open))
    else:
        # Buy outer DOWN + inner UP
        px_a, tok_a, cid_a, fr_a, fe_a, desc_a = (
            float(outer_down_ask),
            str(outer_down_token),
            str(outer_condition_id),
            float(fee_rate_outer),
            float(fee_exponent_outer),
            f"{outer_horizon}_DOWN",
        )
        px_b, tok_b, cid_b, fr_b, fe_b, desc_b = (
            float(inner_up_ask),
            str(inner_up_token),
            str(inner_condition_id),
            float(fee_rate_inner),
            float(fee_exponent_inner),
            f"{inner_horizon}_UP",
        )
        corridor = (float(inner_open), float(outer_open))

    if not (0.01 <= px_a <= 0.98 and 0.01 <= px_b <= 0.98 and tok_a and tok_b):
        return None
    qa, _, _ = quantize_dynamic_tick_price(px_a, "BUY", shares=5.0, mode="taker")
    qb, _, _ = quantize_dynamic_tick_price(px_b, "BUY", shares=5.0, mode="taker")
    cost_a = qa + compute_exact_taker_fee_per_share(qa, fr_a, fe_a)
    cost_b = qb + compute_exact_taker_fee_per_share(qb, fr_b, fe_b)
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
        "leg_a": {"label": desc_a, "token_id": tok_a, "condition_id": cid_a, "ask_px": qa, "fee_rate": fr_a, "fee_exponent": fe_a},
        "leg_b": {"label": desc_b, "token_id": tok_b, "condition_id": cid_b, "ask_px": qb, "fee_rate": fr_b, "fee_exponent": fe_b},
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
    fee_exponent: float = 1.0,
    fee_rate_touch: Optional[float] = None,
    fee_rate_noon: Optional[float] = None,
    fee_exponent_touch: Optional[float] = None,
    fee_exponent_noon: Optional[float] = None,
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
    fr_a = float(fee_rate if fee_rate_touch is None else fee_rate_touch)
    fr_b = float(fee_rate if fee_rate_noon is None else fee_rate_noon)
    fe_a = float(fee_exponent if fee_exponent_touch is None else fee_exponent_touch)
    fe_b = float(fee_exponent if fee_exponent_noon is None else fee_exponent_noon)
    ca = qa + compute_exact_taker_fee_per_share(qa, fr_a, fe_a)
    cb = qb + compute_exact_taker_fee_per_share(qb, fr_b, fe_b)
    net_edge = 1.0 - (ca + cb)
    if net_edge < float(min_net_edge_usd):
        return None
    return {
        "sleeve": "B1_INTRADAY_ONETOUCH_NOON_BOX",
        "box_type": "DOMINANCE",
        "asset": str(asset).upper(),
        "strike": float(strike),
        "leg_a": {"token_id": str(touch_yes_token), "condition_id": str(touch_condition_id), "ask_px": qa, "fee_rate": fr_a, "fee_exponent": fe_a},
        "leg_b": {"token_id": str(noon_no_token), "condition_id": str(noon_condition_id), "ask_px": qb, "fee_rate": fr_b, "fee_exponent": fe_b},
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
    `EQ1_PYTH_EQUITY_DOMINANCE_BOX` (`09:30-16:00 ET` Full Regular Trading Hours):
    Scans same-day Pyth regular-session close (`16:00 ET`) equity threshold contracts (`Close >= K_i`)
    for monotonic dominance: `YES(Close >= K_low) + NO(Close >= K_high) < $1.00` (`K_low < K_high`).
    """
    sym = str(ticker or "").strip().upper()
    if corporate_action_flag or sym not in PYTH_EQUITY_SYMBOLS or not (9.50 <= float(et_hour_float) <= 16.0):
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

_METAR_T_REMARK_RE = re.compile(r"\bRMK\b.*?\bT([01])(\d{3})(?:[01]\d{3}|////)?\b")
_METAR_BODY_TEMP_RE = re.compile(r"(?:^|\s)(M?\d{2})/(?:M?\d{2}|//)(?=\s|$)")
_HKO_SYNTH_RE = re.compile(r"^HKO_(?:MIN|MAX|1M)\s+(-?\d+(?:\.\d+)?)C$", re.IGNORECASE)
_METAR_ICAO_RE = re.compile(r"^(?:METAR\s+)?([A-Z]{4})\b")
_METAR_DDHHMMZ_RE = re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b")
_METAR_RMK_6H_MAX_RE = re.compile(r"(?:^|\s)1([01])(\d{3})(?=\s|$)")
_METAR_RMK_6H_MIN_RE = re.compile(r"(?:^|\s)2([01])(\d{3})(?=\s|$)")
_METAR_RMK_24H_EXT_RE = re.compile(r"(?:^|\s)4([01])(\d{3})([01])(\d{3})(?=\s|$)")
_METAR_ASOS_AO_RE = re.compile(r"\bAO[12]\b")
_US_ASOS_VALID_TENTHS_SET: frozenset[int] = frozenset(
    int(math.floor((((f_i - 32) * 50.0) / 9.0) + 0.5 + 1e-12))
    if (((f_i - 32) * 50.0) / 9.0) >= 0.0
    else -int(math.floor(-(((f_i - 32) * 50.0) / 9.0) + 0.5 + 1e-12))
    for f_i in range(-130, 165)
)

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
    body_part = txt.upper().split("RMK")[0]
    m_body = _METAR_BODY_TEMP_RE.search(body_part)
    body_temp_c: Optional[float] = None
    if m_body:
        t_tok = m_body.group(1)
        body_temp_c = -float(t_tok[1:]) if t_tok.startswith("M") else float(t_tok)

    m_rmk = None if (m_hko or prefer_body) else _METAR_T_REMARK_RE.search(txt.upper())
    if m_hko:
        temp_c = float(m_hko.group(1))
        unc_c = 0.05
        has_t_group = True
    elif m_rmk:
        tenths_signed = (-1 if m_rmk.group(1) == "1" else 1) * int(m_rmk.group(2))
        temp_c = tenths_signed / 10.0
        if len(inferred_icao) == 4 and inferred_icao.startswith("K") and tenths_signed not in _US_ASOS_VALID_TENTHS_SET:
            return None
        if body_temp_c is not None and abs(temp_c - body_temp_c) > 0.65:
            return None
        unc_c = 0.05
        has_t_group = True
    else:
        if body_temp_c is None:
            return None
        temp_c = body_temp_c
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
        tz_w = safe_zoneinfo(str(getattr(sp_w, "tz_name", "UTC") or "UTC"))
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


def _raw_metar_lines_have_oracle_contradiction(metar_lines: Sequence[str], station_icao: str = "") -> bool:
    """
    Returns True if any non-SPECI routine METAR in `metar_lines` is a `COR` amendment, has an invalid
    US ASOS T-group / body-vs-T mismatch, or contradicts a synoptic 6h (`1sTTT`/`2sTTT`) / 24h (`4sTTTsTTT`)
    summary remark inside the covered window — blocking irreversible dead-bracket pruning on BOTH sides.
    """
    if not metar_lines:
        return False
    inferred_st = str(station_icao or "").strip().upper()
    raw_entries: List[Tuple[Optional[Tuple[int, int, int]], float, Optional[float], Optional[float], Optional[float], Optional[float]]] = []
    for raw_ln in metar_lines:
        txt = str(raw_ln or "").strip()
        if not txt:
            continue
        up = txt.upper()
        toks = up.split()
        if not toks or "SPECI" in toks[:3]:
            continue
        if "COR" in toks[:5]:
            return True
        if _HKO_SYNTH_RE.match(txt):
            continue
        st_code = inferred_st
        if not st_code:
            m_ic = _METAR_ICAO_RE.match(up)
            if m_ic:
                st_code = m_ic.group(1)
        body_p = up.split("RMK", 1)[0]
        rmk_p = up.split("RMK", 1)[1] if "RMK" in up else ""
        m_bd = _METAR_BODY_TEMP_RE.search(body_p)
        bd_c: Optional[float] = None
        if m_bd:
            bt = m_bd.group(1)
            bd_c = -float(bt[1:]) if bt.startswith("M") else float(bt)
        m_rm = _METAR_T_REMARK_RE.search(up)
        obs_c: Optional[float] = None
        if m_rm:
            t_sgn = (-1 if m_rm.group(1) == "1" else 1) * int(m_rm.group(2))
            obs_c = t_sgn / 10.0
            if len(st_code) == 4 and st_code.startswith("K") and t_sgn not in _US_ASOS_VALID_TENTHS_SET:
                return True
            if bd_c is not None and abs(obs_c - bd_c) > 0.65:
                return True
        elif bd_c is not None:
            obs_c = bd_c
        if obs_c is None:
            continue
        m_ts = _METAR_DDHHMMZ_RE.search(up)
        dhm = (int(m_ts.group(1)), int(m_ts.group(2)), int(m_ts.group(3))) if m_ts else None
        c6x = c6n = c24x = c24n = None
        if rmk_p and _METAR_ASOS_AO_RE.search(rmk_p):
            if dhm is None or dhm[1] in (23, 0, 5, 6, 11, 12, 17, 18):
                mx6 = _METAR_RMK_6H_MAX_RE.search(rmk_p)
                if mx6:
                    c6x = (-1.0 if mx6.group(1) == "1" else 1.0) * (int(mx6.group(2)) / 10.0)
                mn6 = _METAR_RMK_6H_MIN_RE.search(rmk_p)
                if mn6:
                    c6n = (-1.0 if mn6.group(1) == "1" else 1.0) * (int(mn6.group(2)) / 10.0)
            m24 = _METAR_RMK_24H_EXT_RE.search(rmk_p)
            if m24:
                c24x = (-1.0 if m24.group(1) == "1" else 1.0) * (int(m24.group(2)) / 10.0)
                c24n = (-1.0 if m24.group(3) == "1" else 1.0) * (int(m24.group(4)) / 10.0)
        raw_entries.append((dhm, obs_c, c6x, c6n, c24x, c24n))

    days = {e[0][0] for e in raw_entries if e[0] is not None}
    roll_base = max((d for d in days if d >= 28), default=0) if (any(d <= 3 for d in days) and any(d >= 28 for d in days)) else 0

    def _rel_min(dhm_t: Optional[Tuple[int, int, int]]) -> Optional[int]:
        if dhm_t is None:
            return None
        d_eff = (dhm_t[0] + roll_base) if (roll_base and dhm_t[0] <= 3) else dhm_t[0]
        return d_eff * 1440 + dhm_t[1] * 60 + dhm_t[2]

    for dhm_s, _, c6x, c6n, c24x, c24n in raw_entries:
        if c6x is None and c6n is None and c24x is None and c24n is None:
            continue
        t_s = _rel_min(dhm_s)
        for dhm_p, tc_p, _, _, _, _ in raw_entries:
            t_p = _rel_min(dhm_p)
            if t_s is not None and t_p is not None:
                dt_m = t_s - t_p
                if 0 <= dt_m <= 355:
                    if c6x is not None and tc_p > c6x + 0.15:
                        return True
                    if c6n is not None and tc_p < c6n - 0.15:
                        return True
                if 0 <= dt_m <= 1430:
                    if c24x is not None and tc_p > c24x + 0.15:
                        return True
                    if c24n is not None and tc_p < c24n - 0.15:
                        return True
    return False


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
    if _raw_metar_lines_have_oracle_contradiction(metar_lines, station_icao=station_icao):
        return None
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


_INDIV_OR_3WAY_ML_DISPUTE_RE = re.compile(
    r"\b(tennis|atp|wta|challenger|itf|ufc|mma|boxing|retire(?:s|d|ment)\s+mid[\s-]match|walkover\s+or\s+retirement|will\s+.+\s+win\b|moneyline)\b",
    re.IGNORECASE,
)


def _bond1_boilerplate_fast_season_eligible(market_or_cand: Any, risk: Mapping[str, Any]) -> bool:
    """True only for completed team/totals/corners/esports props whose sole flag is template text (never Tennis/UFC or 3-way ML)."""
    q_txt = ""
    full_txt = ""
    if isinstance(market_or_cand, Mapping):
        q_txt = " ".join(
            str(market_or_cand.get(k) or "")
            for k in ("question", "title", "display_label", "leg_a_label", "regime", "domain", "asset", "slug")
        )
        full_txt = " ".join(
            str(market_or_cand.get(k) or "")
            for k in ("question", "title", "display_label", "description", "rules", "rules_text", "ancillaryData")
        )
    else:
        q_txt = str(market_or_cand or "")
        full_txt = q_txt
    if _INDIV_OR_3WAY_ML_DISPUTE_RE.search(q_txt):
        return False
    if re.search(r"\b(retire(?:s|d|ment)|walkover|disqualif|50[\s/-]*50)\b", full_txt, re.IGNORECASE):
        return False
    reasons = set(risk.get("reasons") or ())
    if reasons and not re.search(
        r"\b(corner|over|under|o/u|total|spread|handicap|card|both\s+teams\s+to\s+score|btts)\b",
        q_txt,
        re.IGNORECASE,
    ):
        return False
    return True


def passes_uma_bond_dispute_guard(
    market: Any,
    ver: Mapping[str, Any],
    *,
    allow_pre_book_fast_season: bool = False,
) -> bool:
    """Enforce `proposal_age_sec >= 1800` on `BOND1` (or `>= 600s` + verified dual-book consensus on non-ML/non-walkover boilerplate)."""
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
    if age_sec >= float(risk["min_proposal_age_sec"]):
        return True
    if (
        age_sec >= 600.0
        and isinstance(ver, Mapping)
        and str(ver.get("oo_state") or "PROPOSED_UNDISPUTED") == "PROPOSED_UNDISPUTED"
        and (allow_pre_book_fast_season or bool(ver.get("allow_pre_book_fast_season")) or bool(ver.get("dual_book_consensus_confirmed")))
        and _bond1_boilerplate_fast_season_eligible(market, risk)
    ):
        return True
    return False


def check_sll_cand_dispute_guard(cand: Mapping[str, Any]) -> Optional[str]:
    """
    Harvester & candidate-bridge defense-in-depth dispute guard:
      - `BOND1_UMA_RESOLUTION_CARRY`: requires `proposal_age_sec >= 1800` (or `>= 600s` with confirmed dual-book
        consensus on non-walkover / non-3way-ML team totals/corners/props).
      - Pre-final sports clinches (`MKR_LOCK1`, `CL1`, `AFF1`, `SOC2`, `NFL_PRP1`): vetoes pre-final execution
        when dispute-ambiguous rule clauses are present.
    """
    if not isinstance(cand, Mapping):
        return None
    risk = classify_market_rule_dispute_risk(
        cand,
        extra_text=f"{cand.get('leg_a_label') or ''} {cand.get('regime') or ''}",
    )
    has_risk = bool(risk["dispute_risk"] or cand.get("dispute_risk"))
    if not has_risk:
        return None
    slv = str(cand.get("sleeve_source") or cand.get("sleeve") or "").upper()
    if slv == "BOND1_UMA_RESOLUTION_CARRY":
        raw_age = cand.get("proposal_age_sec")
        if raw_age is not None:
            age_sec = _sf(raw_age, 0.0)
        elif cand.get("rem_challenge_sec") is not None:
            age_sec = max(0.0, _sf(cand.get("eff_liveness_sec"), 7200.0) - _sf(cand.get("rem_challenge_sec"), 7200.0))
        else:
            age_sec = 0.0
        if age_sec < 1800.0:
            if (
                age_sec >= 600.0
                and bool(cand.get("dual_book_consensus_confirmed"))
                and not bool(cand.get("strict_1800s_dispute_hold"))
                and _bond1_boilerplate_fast_season_eligible(cand, risk)
            ):
                return None
            return f"DISPUTE_RULE_PROPOSAL_UNSEASONED:{age_sec:.0f}s<1800s"
        return None
    if slv in {
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
        "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
        "SOC2_EXACT_SCORE_2D_LATTICE",
        "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
    }:
        mode_u = str(cand.get("mode") or cand.get("clinch_mode") or "").upper()
        if not bool(cand.get("is_final")) and "FINAL" not in mode_u:
            return "DISPUTE_RULE_PRE_FINAL_CLINCH_VETO"
    return None


def resolve_harvester_sll_tick_size(
    executor: Any,
    tok_a: str,
    cand: Mapping[str, Any],
    *,
    bk_win: Optional[Mapping[str, Any]] = None,
    mkt_ws: Any = None,
    real_clob: bool = False,
    custom_tk_fn: bool = False,
    price_hint: Optional[float] = None,
    allow_sync_sdk: bool = False,
) -> float:
    """Resolve single-leg lock tick size with strict WS precedence over stale REST `/book` metadata."""
    tok_s = str(tok_a or "")
    ph = float(price_hint) if (price_hint is not None and math.isfinite(float(price_hint))) else None
    at_subcent_boundary = bool(
        (real_clob or custom_tk_fn)
        and hasattr(executor, "get_token_tick_size")
        and ph is not None
        and (ph >= 0.96 or ph <= 0.04 or abs(round(ph, 2) - round(ph, 4)) > 1e-6)
    )
    if not custom_tk_fn:
        now_m_ov = time.monotonic()
        c400 = getattr(executor, "_clob_400_tick_until", None)
        if isinstance(c400, Mapping) and tok_s in c400:
            c4_tk, c4_exp = c400[tok_s]
            if now_m_ov < float(c4_exp) and 0.0001 <= float(c4_tk) <= 0.1:
                c4_f = float(c4_tk)
                if mkt_ws is not None and hasattr(mkt_ws, "_tick_sizes") and isinstance(mkt_ws._tick_sizes, dict):
                    mkt_ws._tick_sizes[tok_s] = c4_f
                return c4_f
        ov = getattr(executor, "_enforced_tick_override_until", None)
        if isinstance(ov, Mapping) and tok_s in ov:
            ov_tk, ov_exp = ov[tok_s]
            if now_m_ov < float(ov_exp) and 0.0001 <= float(ov_tk) <= 0.1:
                ov_f = float(ov_tk)
                if not (abs(ov_f - 0.01) < 1e-9 and at_subcent_boundary):
                    return ov_f
    ws_raw = None
    if not custom_tk_fn:
        if mkt_ws is not None and hasattr(mkt_ws, "get_tick_size"):
            ws_raw = mkt_ws.get_tick_size(tok_s)
        if ws_raw in (None, ""):
            ws_raw = cand.get("leg_a_ws_tick_size")
    try:
        ws_f = float(ws_raw) if ws_raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        ws_f = 0.0
    if 0.0001 <= ws_f <= 0.1 and not (abs(ws_f - 0.01) < 1e-9 and at_subcent_boundary):
        if real_clob and hasattr(executor, "update_ws_tick_size"):
            executor.update_ws_tick_size(tok_s, ws_f)
        return ws_f

    bk_raw = (bk_win or {}).get("minimum_tick_size") or (bk_win or {}).get("tick_size") if isinstance(bk_win, Mapping) else None
    try:
        bk_f = float(bk_raw) if bk_raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        bk_f = 0.0
    needs_boundary_recheck = abs(bk_f - 0.01) < 1e-9 and at_subcent_boundary
    if 0.0001 <= bk_f <= 0.1 and not needs_boundary_recheck and not custom_tk_fn:
        return bk_f
    if allow_sync_sdk and hasattr(executor, "get_token_tick_size") and (real_clob or custom_tk_fn):
        try:
            return float(executor.get_token_tick_size(tok_s, price_hint=ph) or 0.0)
        except TypeError:
            return float(executor.get_token_tick_size(tok_s) or 0.0)
        except Exception:
            return 0.0
    if not real_clob and not custom_tk_fn:
        try:
            cand_f = float(cand.get("leg_a_tick_size") or 0.0)
            if 0.0001 <= cand_f <= 0.1:
                return cand_f
        except (TypeError, ValueError):
            pass
    return 0.0


def sync_harvester_sll_enforced_tick(
    executor: Any,
    mkt_ws: Any,
    tok_a: str,
    cur_tk_wf: float,
    bk_wc: Optional[Mapping[str, Any]] = None,
) -> float:
    """Propagates CLOB `HTTP 400` enforced tick overrides into `_tk_wf` and `mkt_ws` so repeg loops never repeat."""
    tok_s = str(tok_a or "")
    c400 = getattr(executor, "_clob_400_tick_until", None)
    if isinstance(c400, Mapping) and tok_s in c400:
        c4_tk, c4_exp = c400[tok_s]
        if time.monotonic() < float(c4_exp) and 0.0001 <= float(c4_tk) <= 0.1:
            if isinstance(bk_wc, Mapping) and any(
                abs(round(float(lv["price"] if isinstance(lv, Mapping) else lv[0]) * 100.0) - float(lv["price"] if isinstance(lv, Mapping) else lv[0]) * 100.0) > 1e-6
                and float(lv["price"] if isinstance(lv, Mapping) else lv[0]) >= 0.95
                and float(lv.get("size", 0) if isinstance(lv, Mapping) else lv[1]) > 0
                for lv in ((bk_wc.get("bids") or []) + (bk_wc.get("asks") or []))
            ):
                if isinstance(c400, dict):
                    c400.pop(tok_s, None)
                if mkt_ws is not None and hasattr(mkt_ws, "_tick_sizes") and isinstance(mkt_ws._tick_sizes, dict):
                    mkt_ws._tick_sizes[tok_s] = 0.001
                return 0.001
            c4_f = float(c4_tk)
            if mkt_ws is not None and hasattr(mkt_ws, "_tick_sizes") and isinstance(mkt_ws._tick_sizes, dict):
                mkt_ws._tick_sizes[tok_s] = c4_f
            return c4_f
    return float(cur_tk_wf or 0.0)


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
        fra, fea = _sf(qa_map.get("fee_rate"), 0.0), _sf(qa_map.get("fee_exponent"), 1.0)
        frb, feb = _sf(qb_map.get("fee_rate"), 0.0), _sf(qb_map.get("fee_exponent"), 1.0)
        cost = (
            qpa + compute_exact_taker_fee_per_share(qpa, fra, fea)
            + qpb + compute_exact_taker_fee_per_share(qpb, frb, feb)
        )
        edge = 1.0 - cost
        if edge >= float(min_net_edge_usd):
            out.append(
                {
                    "sleeve": "DC1_DOUBLE_CHANCE_1X2_PARITY",
                    "box_type": "DOMINANCE",
                    "pair": f"{k_dc}+{k_1x2}",
                    "identity": f"YES_{k_1x2}_PLUS_YES_{k_dc}",
                    "leg_a": {"token_id": ta, "condition_id": str(qa_map.get("condition_id") or ""), "ask_px": qpa, "fee_rate": fra, "fee_exponent": fea},
                    "leg_b": {"token_id": tb, "condition_id": str(qb_map.get("condition_id") or ""), "ask_px": qpb, "fee_rate": frb, "fee_exponent": feb},
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
                fra, fea = _sf(btts_m.get("fee_rate"), 0.0), _sf(btts_m.get("fee_exponent"), 1.0)
                frb, feb = _sf(o15.get("fee_rate"), 0.0), _sf(o15.get("fee_exponent"), 1.0)
                cost2 = (
                    qpa + compute_exact_taker_fee_per_share(qpa, fra, fea)
                    + qpb + compute_exact_taker_fee_per_share(qpb, frb, feb)
                )
                edge = 1.0 - cost2
                if edge >= float(min_net_edge_usd):
                    exp_2 = max(_sf(btts_m.get("expiry_ts"), 0.0), _sf(o15.get("expiry_ts"), 0.0))
                    rec_2: Dict[str, Any] = {
                        "sleeve": "LP_COMP1_SPORTS_TRIANGLES",
                        "box_type": "DOMINANCE",
                        "pattern": "NO_BTTS_PLUS_YES_OVER_1_5",
                        "triangle_id": "NO_BTTS_PLUS_YES_OVER_1_5",
                        "leg_a": {"token_id": ta, "role": "NO_BTTS", "condition_id": str(btts_m.get("condition_id") or ""), "market_id": str(btts_m.get("market_id") or ""), "ask_px": qpa, "fee_rate": fra, "fee_exponent": fea},
                        "leg_b": {"token_id": tb, "role": "YES_OVER_1_5", "condition_id": str(o15.get("condition_id") or ""), "market_id": str(o15.get("market_id") or ""), "ask_px": qpb, "fee_rate": frb, "fee_exponent": feb},
                        "legs": [
                            {"token_id": ta, "role": "NO_BTTS", "condition_id": str(btts_m.get("condition_id") or ""), "market_id": str(btts_m.get("market_id") or ""), "ask_px": qpa, "fee_rate": fra, "fee_exponent": fea},
                            {"token_id": tb, "role": "YES_OVER_1_5", "condition_id": str(o15.get("condition_id") or ""), "market_id": str(o15.get("market_id") or ""), "ask_px": qpb, "fee_rate": frb, "fee_exponent": feb},
                        ],
                        "guaranteed_payout_per_share": 1.0,
                        "cost_per_share": round(cost2, 6),
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
                fr1, fe1 = _sf(draw_m.get("fee_rate"), 0.0), _sf(draw_m.get("fee_exponent"), 1.0)
                fr2, fe2 = _sf(btts_m.get("fee_rate"), 0.0), _sf(btts_m.get("fee_exponent"), 1.0)
                fr3, fe3 = _sf(u15.get("fee_rate"), 0.0), _sf(u15.get("fee_exponent"), 1.0)
                nc1 = qp1 + compute_exact_taker_fee_per_share(qp1, fr1, fe1)
                nc2 = qp2 + compute_exact_taker_fee_per_share(qp2, fr2, fe2)
                nc3 = qp3 + compute_exact_taker_fee_per_share(qp3, fr3, fe3)
                cost3 = nc1 + nc2 + nc3
                edge3 = 1.0 - cost3
                if edge3 >= float(min_net_edge_usd):
                    exp_3 = max(_sf(draw_m.get("expiry_ts"), 0.0), _sf(btts_m.get("expiry_ts"), 0.0), _sf(u15.get("expiry_ts"), 0.0))
                    rec_3: Dict[str, Any] = {
                        "sleeve": "LP_COMP1_SPORTS_TRIANGLES",
                        "box_type": "MULTI_LEG_BUNDLE",
                        "pattern": "NO_DRAW_YES_BTTS_YES_UNDER_1_5",
                        "triangle_id": "NO_DRAW_YES_BTTS_YES_UNDER_1_5",
                        "legs": [
                            {"token_id": t1, "condition_id": str(draw_m.get("condition_id") or ""), "market_id": str(draw_m.get("market_id") or ""), "ask_px": qp1, "net_cost": nc1, "ask_size": s_min, "fee_rate": fr1, "fee_exponent": fe1, "neg_risk": bool(draw_m.get("neg_risk", False))},
                            {"token_id": t2, "condition_id": str(btts_m.get("condition_id") or ""), "market_id": str(btts_m.get("market_id") or ""), "ask_px": qp2, "net_cost": nc2, "ask_size": s_min, "fee_rate": fr2, "fee_exponent": fe2, "neg_risk": bool(btts_m.get("neg_risk", False))},
                            {"token_id": t3, "condition_id": str(u15.get("condition_id") or ""), "market_id": str(u15.get("market_id") or ""), "ask_px": qp3, "net_cost": nc3, "ask_size": s_min, "fee_rate": fr3, "fee_exponent": fe3, "neg_risk": bool(u15.get("neg_risk", False))},
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
        yb = _sf(m.get("yes_bid"), 0.0)
        nb = _sf(m.get("no_bid"), 0.0)
        ysz_b = _sf(m.get("yes_bid_size"), 0.0)
        nsz_b = _sf(m.get("no_bid_size"), 0.0)
        crossed_bk = bool((yb > 0.0 and ya > 0.0 and yb >= ya - 1e-9) or (nb > 0.0 and na > 0.0 and nb >= na - 1e-9))
        if crossed_bk:
            continue
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

        if f_r <= 1e-9 and 0.002 <= yb <= 0.995 and 0.002 <= nb <= 0.995 and min(ysz_b, nsz_b) >= min_shares * 1.25:
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


def _register_ctf_overround_residual(
    harvester: Any,
    executor: Any,
    *,
    cid: str,
    market_id: str,
    unsold_tok: str,
    unsold_side: str,
    cand_asset: str,
    sh: float,
    rem_cost: float,
    fr: float,
    fe: float,
    exp_ts: float,
    now_ts: float,
    uw_unk: bool = False,
    uw_oid: Any = None,
    sp_tx: str = "",
) -> str:
    rid = f"CTFOVR_RESID_{cid[:8]}_{int(now_ts)}"
    if rid in harvester.active_positions:
        rid = f"{rid}_{int(now_ts * 1000) % 10000}"
    mid_u = str(market_id or cid)
    if hasattr(harvester, "_make_single_leg_lock_pos"):
        rpos = harvester._make_single_leg_lock_pos(
            rid, "CTF_OVERROUND_RESIDUAL", "CTF_OVERROUND_MINT_SELL", cand_asset, "resid",
            mid_u, cid, unsold_tok, unsold_side, False, sh, rem_cost, 0.0, fr, fe,
            resolve_canonical_fee_source(fr, "CTF_OVERROUND_MINT_SELL"), exp_ts, now_ts, 0.0, None, False, unk=False,
        )
    else:
        rpos = {
            "trade_id": rid, "box_id": rid, "token_id": unsold_tok, "condition_id": cid, "market_id": mid_u,
            "target_token": unsold_side, "asset": cand_asset, "sleeve": "CTF_OVERROUND_MINT_SELL",
            "shares": sh, "entry_shares": sh, "gross_entry_shares": sh, "remaining_shares": sh,
            "remaining_exit_shares": sh, "filled_exit_shares": 0.0, "remaining_cost_basis": rem_cost,
            "entry_price": round(rem_cost / max(sh, 0.01), 4), "notional_usd": rem_cost,
            "fee_rate_applied": fr, "fee_exponent_applied": fe,
            "entry_ts": now_ts, "candle_expiry_ts": exp_ts, "neg_risk": False,
        }
    rpos.update({
        "market_id": mid_u,
        "is_dominance_box": False,
        "is_single_leg_lock": False,
        "hold_to_maturity_lock": False,
        "is_legged_out_residual": True,
        "pending_unwind_tag": "CTF_OVERROUND_RESIDUAL_UNWIND",
        "status": "POSITION_CONFIRMED",
        "inventory_reconciled": True,
        "exit_order_status": "UNWIND_EXECUTION_OUTCOME_UNKNOWN" if uw_unk else "UNWIND_RETRY_REQUIRED",
        "terminal_policy": None,
        "stop_triggered_ts": now_ts,
        "next_unwind_retry_ts": now_ts + 0.35,
        "unwind_attempt_ts": now_ts,
        "unwind_order_id": uw_oid if uw_unk else None,
        "unwind_start_time": now_ts,
        "transactions_hashes": [sp_tx] if sp_tx else [],
    })
    harvester.active_positions[rid] = rpos
    if getattr(harvester, "_last_known_collateral", None) is not None:
        harvester._last_known_collateral = max(0.0, float(harvester._last_known_collateral) - rem_cost)
    if executor is not None and hasattr(executor, "invalidate_collateral_cache"):
        executor.invalidate_collateral_cache()
    harvester._pending_collateral_refresh = True
    if hasattr(harvester, "_refresh_global_halt") and hasattr(harvester, "risk_halt"):
        harvester._refresh_global_halt()
    if hasattr(harvester, "save_state"):
        harvester.save_state()
    return rid


def _register_ctf_overround_unmerged_pair(
    harvester: Any,
    executor: Any,
    *,
    cid: str,
    market_id: str,
    y_tok: str,
    n_tok: str,
    cand_asset: str,
    sh: float,
    fr: float,
    fe: float,
    exp_ts: float,
    now_ts: float,
    la_d: Optional[Mapping[str, Any]] = None,
    lb_d: Optional[Mapping[str, Any]] = None,
    sp_tx: str = "",
) -> Tuple[str, str]:
    bid = f"CTFOVR_CSET_{cid[:8]}_{int(now_ts)}"
    if f"{bid}_L1" in harvester.active_positions or f"{bid}_L2" in harvester.active_positions:
        bid = f"{bid}_{int(now_ts * 1000) % 10000}"
    t1, t2 = f"{bid}_L1", f"{bid}_L2"
    mid_u = str(market_id or cid)
    leg_notional = round(0.5 * sh, 4)
    tot_cost = round(sh, 4)
    iso_t = _iso_utc(now_ts)
    for tid, p_tid, tok, opp_tok, side_s, lg_d in (
        (t1, t2, y_tok, n_tok, "YES", la_d),
        (t2, t1, n_tok, y_tok, "NO", lb_d),
    ):
        lg_unk = bool((lg_d or {}).get("outcome_unknown"))
        lg_oid = (lg_d or {}).get("orderID")
        harvester.active_positions[tid] = {
            "trade_id": tid,
            "box_id": bid,
            "box_expected_legs": 2,
            "box_partner_trade_id": p_tid,
            "box_type": "COMPLETE_SET",
            "box_cost_net": 1.0,
            "box_total_cost_usd": tot_cost,
            "is_dominance_box": True,
            "is_locked_arbitrage_box": True,
            "is_single_leg_lock": False,
            "hold_to_maturity_lock": False,
            "sleeve": "CTF_OVERROUND_MINT_SELL",
            "sleeve_source": "CTF_OVERROUND_MINT_SELL",
            "entry_tte": max(1.0, exp_ts - now_ts),
            "event_id": bid,
            "market_id": mid_u,
            "condition_id": cid,
            "token_id": tok,
            "opp_token_id": opp_tok,
            "target_token": side_s,
            "asset": cand_asset,
            "horizon": "cset",
            "is_subhourly": False,
            "neg_risk": False,
            "candle_open_spot": 100.0,
            "entry_spot_ref": 100.0,
            "spot_denomination": "USD",
            "candle_sigma": 0.0,
            "entry_price": 0.5,
            "entry_shares": sh,
            "gross_entry_shares": sh,
            "remaining_shares": sh,
            "filled_exit_shares": 0.0,
            "remaining_exit_shares": sh,
            "remaining_cost_basis": leg_notional,
            "realized_exit_cash": 0.0,
            "realized_exit_fee": 0.0,
            "gross_exit_cash": 0.0,
            "average_exit_price": 0.0,
            "exit_trade_ids": [],
            "notional_usd": leg_notional,
            "fee_usd": 0.0,
            "entry_fee_cash_usd": 0.0,
            "entry_fee_asset": "USDC",
            "fee_source": "crypto_fees_v2",
            "fee_rate_applied": fr,
            "fee_exponent_applied": fe,
            "target_exit_price": 1.0,
            "exit_order_size": sh,
            "entry_time_utc": iso_t,
            "entry_ts": now_ts,
            "candle_expiry_ts": exp_ts,
            "pre_token_balance": 0.0,
            "order_id": None,
            "entry_order_id": None,
            "trade_ids": [],
            "transactions_hashes": [sp_tx] if sp_tx else [],
            "status": "POSITION_CONFIRMED",
            "inventory_reconciled": True,
            "exit_order_id": None,
            "exit_order_status": "UNWIND_EXECUTION_OUTCOME_UNKNOWN" if lg_unk else "DETERMINISTIC_TERMINAL_HOLD",
            "terminal_policy": None if lg_unk else "DETERMINISTIC_TERMINAL_HOLD",
            "is_liquidating": False,
            "unwind_order_id": lg_oid if lg_unk else None,
            "unwind_attempt_ts": now_ts if lg_unk else 0.0,
            "unwind_start_time": now_ts if lg_unk else 0.0,
        }
    if getattr(harvester, "_last_known_collateral", None) is not None:
        harvester._last_known_collateral = max(0.0, float(harvester._last_known_collateral) - tot_cost)
    if executor is not None and hasattr(executor, "invalidate_collateral_cache"):
        executor.invalidate_collateral_cache()
    harvester._pending_collateral_refresh = True
    if hasattr(harvester, "_refresh_global_halt") and hasattr(harvester, "risk_halt"):
        harvester._refresh_global_halt()
    if hasattr(harvester, "save_state"):
        harvester.save_state()
    return t1, t2


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
        lb_d = (u_res or {}).get("leg_b") or {}
        a_sold = bool(la_d.get("filled") or la_d.get("success"))
        sold_d = la_d if a_sold else lb_d
        unsold_d = lb_d if a_sold else la_d
        unsold_tok = no_token_id if a_sold else yes_token_id
        unsold_side = "NO" if a_sold else "YES"
        sold_cash = max(0.0, float(sold_d.get("taking_amount") or 0.0) - float(sold_d.get("fee_usd") or 0.0))
        uw_unk = bool(unsold_d.get("outcome_unknown"))
        uw_oid = unsold_d.get("orderID")
        unw_cash = 0.0
        unw_ok = False
        if not uw_unk and hasattr(executor, "execute_unwind_order"):
            try:
                uw = await asyncio.to_thread(
                    executor.execute_unwind_order, unsold_tok, size=sh, side="SELL", min_price=0.02, neg_risk=False
                )
            except TypeError:
                uw = await asyncio.to_thread(executor.execute_unwind_order, f"UNW_OVR_{condition_id[:8]}", unsold_tok, sh, 0.02)
            unw_ok = bool(getattr(uw, "success", False) or (isinstance(uw, Mapping) and uw.get("success")))
            if not unw_ok and isinstance(uw, Mapping) and uw.get("outcome_unknown"):
                uw_unk = True
                uw_oid = uw.get("orderID") or uw_oid
            unw_cash = float(
                getattr(uw, "notional_usd", 0.0)
                or (uw.get("taking_amount", 0.0) if isinstance(uw, Mapping) else 0.0)
                or 0.0
            )
        elif not uw_unk and hasattr(executor, "place_fok_order"):
            uw = await asyncio.to_thread(executor.place_fok_order, unsold_tok, "SELL", sh, 0.02)
            unw_ok = bool((uw or {}).get("success"))
            if not unw_ok and isinstance(uw, Mapping) and uw.get("outcome_unknown"):
                uw_unk = True
                uw_oid = uw.get("orderID") or uw_oid
            unw_cash = float((uw or {}).get("taking_amount") or 0.0) - float((uw or {}).get("fee_usd") or 0.0)
        if not unw_ok and harvester is not None:
            now_r = time.time()
            _register_ctf_overround_residual(
                harvester,
                executor,
                cid=condition_id,
                market_id=condition_id,
                unsold_tok=unsold_tok,
                unsold_side=unsold_side,
                cand_asset=cand_asset,
                sh=sh,
                rem_cost=round(max(0.01, sh - sold_cash), 4),
                fr=float(fee_rate),
                fe=float(fee_exponent),
                exp_ts=float(expiry_ts or (now_r + 7200.0)),
                now_ts=now_r,
                uw_unk=uw_unk,
                uw_oid=uw_oid,
                sp_tx=str((sp or {}).get("tx_hash") or ""),
            )
        elif unw_ok and executor is not None and hasattr(executor, "invalidate_collateral_cache"):
            executor.invalidate_collateral_cache()
        return {
            "success": False,
            "reason": "OVERROUND_PARTIAL_LEG_UNWOUND",
            "partial_recovered_cash_usd": round(sold_cash + unw_cash, 4),
            "residual_registered": bool(not unw_ok and harvester is not None),
        }

    # Immediate on-chain `mergePositions` rollback on unsold pair (only when neither SELL is outcome_unknown)
    sell_unk = bool((u_res or {}).get("outcome_unknown"))
    if sell_unk:
        merged_ok = False
    elif hasattr(executor, "attempt_onchain_complete_set_merge"):
        m_res = await asyncio.to_thread(
            executor.attempt_onchain_complete_set_merge,
            condition_id,
            min_pairs=max(1.0, sh - 0.05),
            max_pairs=sh,
            neg_risk=False,
        )
        merged_ok = bool(isinstance(m_res, tuple) and len(m_res) >= 2 and m_res[0] and float(m_res[1] or 0.0) >= max(1.0, sh - 0.05))
    elif hasattr(executor, "merge_complete_set_positions"):
        m_res = await asyncio.to_thread(executor.merge_complete_set_positions, condition_id, sh, neg_risk=False)
        merged_ok = bool(isinstance(m_res, Mapping) and (m_res.get("success") or m_res.get("merged")))
    elif hasattr(executor, "merge_complete_set_to_collateral"):
        m_res = await asyncio.to_thread(executor.merge_complete_set_to_collateral, condition_id, sh, neg_risk=False)
        merged_ok = bool(isinstance(m_res, Mapping) and (m_res.get("success") or m_res.get("merged")))
    else:
        merged_ok = False
    if merged_ok:
        if executor is not None and hasattr(executor, "invalidate_collateral_cache"):
            executor.invalidate_collateral_cache()
        if harvester is not None:
            harvester._pending_collateral_refresh = True
    elif harvester is not None:
        now_m = time.time()
        _register_ctf_overround_unmerged_pair(
            harvester,
            executor,
            cid=condition_id,
            market_id=condition_id,
            y_tok=yes_token_id,
            n_tok=no_token_id,
            cand_asset=cand_asset,
            sh=sh,
            fr=float(fee_rate),
            fe=float(fee_exponent),
            exp_ts=float(expiry_ts or (now_m + 7200.0)),
            now_ts=now_m,
            la_d=(u_res or {}).get("leg_a") if isinstance(u_res, Mapping) else None,
            lb_d=(u_res or {}).get("leg_b") if isinstance(u_res, Mapping) else None,
            sp_tx=str((sp or {}).get("tx_hash") or ""),
        )
    return {
        "success": False,
        "reason": "OVERROUND_SWEEP_REJECTED_MERGED_BACK",
        "merged_back": merged_ok,
        "complete_set_supervised": bool(not merged_ok and harvester is not None),
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
    event_id: str = "",
    event_group_key: str = "",
) -> Dict[str, Any]:
    sh = round(float(shares), 2)
    if sh < 5.0 or not (3 <= len(legs) <= 12):
        return {"success": False, "reason": "INVALID_MULTI_LEG_SPEC"}
    ordered = sorted(
        legs,
        key=lambda r: (
            _sf(r.get("ask_size"), 9999.0) * max(0.01, _sf(r.get("ask_px"), 0.50)),
            _sf(r.get("ask_size"), 9999.0),
        ),
    )
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
            _snipe_leg_kw = dict(
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
            try:
                o_res = executor.execute_snipe_order(
                    **_snipe_leg_kw,
                    allow_partial_fak=True,
                    min_order_shares=max(5.0, gross_sh * 0.50),
                )
            except TypeError:
                o_res = executor.execute_snipe_order(**_snipe_leg_kw)
            if isinstance(o_res, Mapping):
                ok = bool(o_res.get("success"))
                unk_leg = bool(o_res.get("outcome_unknown"))
                _o_sz = o_res.get("size") if o_res.get("size") is not None else o_res.get("matched_shares")
                _o_sh = float(_o_sz) if _o_sz is not None else sh
                _o_px = float(o_res.get("price") or px)
                res = {
                    "success": ok,
                    "outcome_unknown": unk_leg,
                    "making_amount": float(o_res.get("making_amount") or o_res.get("notional_usd") or (_o_sh * _o_px)),
                    "fee_usd": float(o_res.get("fee_usd") or 0.0),
                    "size": _o_sh,
                    "price": _o_px,
                    "order_id": o_res.get("order_id") or o_res.get("orderID"),
                    "error": o_res.get("error"),
                }
            else:
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
            _explicit_part_sz = (
                (o_res.get("size") if o_res.get("size") is not None else o_res.get("matched_shares"))
                if isinstance(o_res, Mapping)
                else getattr(o_res, "size", None)
            )
            if (unk_leg and not ok) or (
                not ok and _explicit_part_sz is not None and float(_explicit_part_sz or 0.0) >= 0.05
            ):
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
                f_px = 0.001
                if not getattr(executor, "dry_run", False):
                    if wait_for_erc1155_delivery is not None:
                        try:
                            wait_for_erc1155_delivery(executor, [f_tok], f_sh * 0.90, timeout_sec=3.5)
                        except Exception:
                            pass
                    if hasattr(executor, "wait_for_erc1155_delivery"):
                        try:
                            executor.wait_for_erc1155_delivery(f_tok, expected_min_delta=f_sh * 0.90, timeout_sec=2.5)
                        except TypeError:
                            try:
                                executor.wait_for_erc1155_delivery([f_tok], f_sh * 0.90, timeout_sec=2.5)
                            except Exception:
                                pass
                        except Exception:
                            pass
                uw_ok = False
                uw_r: Any = None
                uw_unk = bool(f_res.get("outcome_unknown"))
                if not uw_unk and hasattr(executor, "execute_unwind_order"):
                    try:
                        uw_r = executor.execute_unwind_order(
                            token_id=f_tok,
                            size=f_sh,
                            side="SELL",
                            min_price=f_px,
                            neg_risk=f_nr,
                        )
                    except TypeError:
                        try:
                            uw_r = executor.execute_unwind_order(f_tok, size=f_sh, side="SELL", min_price=f_px, neg_risk=f_nr)
                        except TypeError:
                            uw_r = executor.execute_unwind_order(f"UNW_{bundle_id}", f_tok, f_sh, f_px)
                    uw_ok = bool(getattr(uw_r, "success", False) or (isinstance(uw_r, Mapping) and uw_r.get("success")))
                    if not uw_ok and isinstance(uw_r, Mapping) and uw_r.get("outcome_unknown"):
                        uw_unk = True
                elif not uw_unk and hasattr(executor, "place_fok_order"):
                    uw_r = executor.place_fok_order(f_tok, "SELL", f_sh, 0.02, neg_risk=f_nr)
                    uw_ok = bool((uw_r or {}).get("success"))
                uw_matched_sh = f_sh
                if isinstance(uw_r, Mapping):
                    _msz_u = uw_r.get("matched_size") if uw_r.get("matched_size") is not None else uw_r.get("matched_shares")
                    if _msz_u is not None:
                        uw_matched_sh = max(0.0, float(_msz_u or 0.0))
                elif uw_r is not None and getattr(uw_r, "size", None) is not None and uw_ok:
                    uw_matched_sh = max(0.0, float(getattr(uw_r, "size") or f_sh))
                sold_sh_u = round(min(f_sh, uw_matched_sh), 4) if uw_ok else 0.0
                rem_unw_sh = round(max(0.0, f_sh - sold_sh_u), 4)
                f_mid = str(f_leg.get("market_id") or "")
                f_cid = str(f_leg.get("condition_id") or f_mid)
                f_not_full = round(float(f_res.get("making_amount") or (f_sh * _sf(f_leg.get("ask_px"), 0.3))), 4)
                f_fee_in = round(float(f_res.get("fee_usd") or 0.0), 4)
                f_fr = _sf(f_leg.get("fee_rate"), 0.0)
                f_fe = _sf(f_leg.get("fee_exponent"), 1.0)
                f_fee_src = resolve_canonical_fee_source(f_fr, sleeve_src)
                evt_k_res = event_group_key or extract_sll_event_group_key(
                    {"event_id": event_id, "box_id": bundle_id, "asset": cand_asset, "sleeve_source": sleeve_src, "expiry_ts": exp_ts, "market_id": f_mid}
                )
                f_not_sold = 0.0
                f_fee_sold = 0.0
                if uw_ok and sold_sh_u >= 0.05:
                    if rem_unw_sh < 0.05:
                        unwound_cnt += 1
                        f_not_sold = f_not_full
                        f_fee_sold = f_fee_in
                    else:
                        sold_frac_u = min(1.0, sold_sh_u / max(f_sh, 0.01))
                        f_not_sold = round(f_not_full * sold_frac_u, 4)
                        f_fee_sold = round(f_fee_in * sold_frac_u, 4)
                    gross_out_u = 0.0
                    fee_out_u = 0.0
                    if isinstance(uw_r, Mapping):
                        gross_out_u = float(uw_r.get("taking_amount") or uw_r.get("notional_usd") or 0.0)
                        fee_out_u = float(uw_r.get("fee_usd") or 0.0)
                    elif uw_r is not None:
                        gross_out_u = float(getattr(uw_r, "notional_usd", 0.0) or 0.0)
                        fee_out_u = float(getattr(uw_r, "fee_usd", 0.0) or 0.0)
                    if gross_out_u >= 1e4:
                        gross_out_u /= 1e6
                    net_uw_pnl = round((gross_out_u - fee_out_u) - (f_not_sold + f_fee_sold), 4) if gross_out_u > 0.0 else 0.0
                    if harvester is not None and isinstance(getattr(harvester, "closed_positions", None), list):
                        iso_rb = _iso_utc(now_rb)
                        harvester.closed_positions.append({
                            "trade_id": f"{bundle_id}_LEG_INLINE_UNWIND_{f_tok[:8]}",
                            "box_id": bundle_id,
                            "box_type": "MULTI_LEG_RESIDUAL",
                            "is_dominance_box": False,
                            "is_legged_out_residual": True,
                            "sleeve": sleeve_src,
                            "asset": cand_asset,
                            "event_id": str(event_id or bundle_id),
                            "event_group_key": evt_k_res,
                            "market_id": f_mid,
                            "condition_id": f_cid,
                            "token_id": f_tok,
                            "target_token": str(f_leg.get("side") or "YES").upper(),
                            "entry_shares": sold_sh_u,
                            "filled_exit_shares": sold_sh_u,
                            "remaining_shares": 0.0,
                            "notional_usd": f_not_sold,
                            "fee_usd": f_fee_sold,
                            "realized_exit_fee": round(fee_out_u, 4),
                            "fee_source": f_fee_src,
                            "fee_rate_applied": f_fr,
                            "fee_exponent_applied": f_fe,
                            "payout_usd": round(gross_out_u, 4),
                            "net_pnl_usd": net_uw_pnl,
                            "won": bool(net_uw_pnl >= 0.0),
                            "status": "CLOSED",
                            "close_reason": "MULTI_LEG_INLINE_LEGGED_OUT_UNWIND",
                            "entry_ts": now_rb,
                            "exit_ts": now_rb,
                            "entry_time_utc": iso_rb,
                            "settled_at_utc": iso_rb,
                        })
                        rc_u = getattr(harvester, "risk_controller", None)
                        if rc_u is not None and hasattr(rc_u, "record_trade_pnl"):
                            try:
                                rc_u.record_trade_pnl(net_uw_pnl, is_non_directional=True)
                            except Exception:
                                pass
                        if hasattr(executor, "invalidate_collateral_cache"):
                            executor.invalidate_collateral_cache()
                        harvester._pending_collateral_refresh = True
                        if hasattr(harvester, "save_state"):
                            harvester.save_state()
                    if not getattr(harvester, "dry_run", getattr(executor, "dry_run", True)):
                        try:
                            from src.polymarket_research.economic_attribution_ledger import emit_funnel_event
                            emit_funnel_event(
                                "PARTIAL_BASKET_UNWOUND",
                                sleeve=sleeve_src,
                                candidate_key=bundle_id,
                                box_type="MULTI_LEG_BUNDLE",
                                asset=cand_asset,
                                notional_usd=f_not_sold,
                                reason=f"INLINE_UNWOUND:{tok[:10]}",
                            )
                        except Exception:
                            pass
                if (not uw_ok or rem_unw_sh >= 0.05) and harvester is not None:
                    rid = f"{bundle_id}_UNWRESID_{f_tok[:8]}_{int(now_rb)}"
                    if uw_ok and sold_sh_u >= 0.05:
                        f_not = round(max(0.0, f_not_full - f_not_sold), 4)
                        f_fee_rem = round(max(0.0, f_fee_in - f_fee_sold), 4)
                    else:
                        rem_frac = (rem_unw_sh / max(f_sh, 0.01)) if (uw_ok and rem_unw_sh < f_sh) else 1.0
                        f_not = round(f_not_full * rem_frac, 4)
                        f_fee_rem = round(f_fee_in * rem_frac, 4)
                    if hasattr(harvester, "_make_single_leg_lock_pos"):
                        rpos = harvester._make_single_leg_lock_pos(
                            rid, "MULTI_LEG_RESIDUAL", sleeve_src, cand_asset, "resid",
                            f_mid, f_cid, f_tok, str(f_leg.get("side") or "YES").upper(), f_nr,
                            rem_unw_sh, f_not, f_fee_rem, f_fr, f_fe,
                            f_fee_src, float(exp_ts or (now_rb + 7200.0)), now_rb, 0.0,
                            f_res.get("order_id"), False, unk=uw_unk,
                        )
                    else:
                        rpos = {
                            "trade_id": rid, "token_id": f_tok, "market_id": f_mid, "condition_id": f_cid,
                            "asset": cand_asset, "sleeve": sleeve_src, "shares": rem_unw_sh, "entry_shares": rem_unw_sh,
                            "remaining_shares": rem_unw_sh, "notional_usd": f_not, "entry_ts": now_rb,
                            "candle_expiry_ts": float(exp_ts or (now_rb + 7200.0)), "status": "POSITION_CONFIRMED",
                            "neg_risk": f_nr, "fee_source": f_fee_src,
                        }
                    rpos.update({
                        "box_id": rid,
                        "box_type": "MULTI_LEG_RESIDUAL",
                        "event_id": str(event_id or rid),
                        "event_group_key": evt_k_res,
                        "is_dominance_box": False,
                        "is_single_leg_lock": False,
                        "hold_to_maturity_lock": False,
                        "is_legged_out_residual": True,
                        "pending_unwind_tag": "MULTI_LEG_RESIDUAL_UNWIND",
                        "status": "ENTRY_OUTCOME_UNKNOWN" if bool(f_res.get("outcome_unknown")) else "POSITION_CONFIRMED",
                        "inventory_reconciled": not bool(f_res.get("outcome_unknown")),
                        "exit_order_status": "UNWIND_EXECUTION_OUTCOME_UNKNOWN" if uw_unk else "UNWIND_RETRY_REQUIRED",
                        "terminal_policy": None,
                        "stop_triggered_ts": now_rb,
                        "next_unwind_retry_ts": now_rb + 0.35,
                        "unwind_attempt_ts": now_rb,
                        "remaining_shares": rem_unw_sh,
                        "remaining_exit_shares": rem_unw_sh,
                        "remaining_cost_basis": f_not,
                    })
                    harvester.active_positions[rid] = rpos
                    if getattr(harvester, "_last_known_collateral", None) is not None and not bool(f_res.get("outcome_unknown")):
                        harvester._last_known_collateral = max(0.0, float(harvester._last_known_collateral) - (f_not + f_fee_rem))
                    if hasattr(executor, "invalidate_collateral_cache"):
                        executor.invalidate_collateral_cache()
                    harvester._pending_collateral_refresh = True
                    if hasattr(harvester, "_refresh_global_halt"):
                        harvester._refresh_global_halt()
                    if hasattr(harvester, "save_state"):
                        harvester.save_state()
                    if not getattr(harvester, "dry_run", getattr(executor, "dry_run", True)) and not (uw_ok and sold_sh_u >= 0.05):
                        try:
                            from src.polymarket_research.economic_attribution_ledger import emit_funnel_event
                            emit_funnel_event(
                                "PARTIAL_BASKET_UNWOUND",
                                sleeve=sleeve_src,
                                candidate_key=bundle_id,
                                box_type="MULTI_LEG_RESIDUAL",
                                asset=cand_asset,
                                notional_usd=f_not,
                                reason=f"UNWRESID_SUPERVISED:{tok[:10]}",
                            )
                        except Exception:
                            pass
            return {"success": False, "legged_out": bool(filled), "reason": f"LEG_FOK_REJECTED:{tok[:12]}", "unwound_legs": unwound_cnt}

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
    event_id: str = "",
    event_group_key: str = "",
) -> List[str]:
    eff_bundle_cost = round(float(total_cost_usd) / max(0.01, float(shares)), 5)
    detail_by_tok = {str(lg.get("token_id") or ""): rs for lg, rs in (filled_details or [])}
    per_leg_fallback = float(total_cost_usd) / float(max(1, len(legs)))
    exp_leg_cnt = len(legs)
    evt_k_b = event_group_key or extract_sll_event_group_key(
        {"event_id": event_id, "box_id": bundle_id, "asset": cand_asset, "sleeve_source": sleeve_src, "expiry_ts": exp_ts}
    )
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
        leg_fsrc = resolve_canonical_fee_source(leg_fr, sleeve_src)
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
                leg_fsrc,
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
            if event_id:
                pos["event_id"] = str(event_id)
            if evt_k_b:
                pos["event_group_key"] = evt_k_b
        else:
            pos = {
                "trade_id": lid,
                "token_id": tok,
                "market_id": mid,
                "condition_id": cid,
                "target_token": side_s,
                "asset": cand_asset,
                "event_id": str(event_id or bundle_id),
                "event_group_key": evt_k_b,
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
                "fee_source": leg_fsrc,
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
    from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as _GGM_SP
    from src.polymarket_research.stage_c_zero_loss_velocity import check_strict_pure_riskless_candidate_gate
    _pure_sp_veto = check_strict_pure_riskless_candidate_gate(
        harvester, candidate_box, _GGM_SP.snapshot.get("riskless_boxes", {}), is_maker=False
    )
    if _pure_sp_veto is not None:
        return {"executed": False, "reason": _pure_sp_veto}
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
        if fr > 1e-9:
            return {"executed": False, "reason": "NON_ZERO_FEE_CTF_OVERROUND"}
        books_ovr = _fetch_books_fast_sync(ex, [y_tok, n_tok])
        if books_ovr:
            by = books_ovr.get(y_tok) or {}
            bn = books_ovr.get(n_tok) or {}
            bids_y = sorted([(float(b["price"]), float(b["size"])) for b in (by.get("bids") or []) if float(b.get("size", 0)) > 0], reverse=True)
            bids_n = sorted([(float(b["price"]), float(b["size"])) for b in (bn.get("bids") or []) if float(b.get("size", 0)) > 0], reverse=True)
            if not bids_y or not bids_n:
                return {"executed": False, "reason": "EMPTY_OVERROUND_BIDS"}
            asks_y = sorted([float(a["price"]) for a in (by.get("asks") or []) if float(a.get("size", 0)) > 0])
            asks_n = sorted([float(a["price"]) for a in (bn.get("asks") or []) if float(a.get("size", 0)) > 0])
            if (asks_y and bids_y[0][0] >= asks_y[0] - 1e-9) or (asks_n and bids_n[0][0] >= asks_n[0] - 1e-9):
                return {"executed": False, "reason": "CROSSED_OVERROUND_BOOK"}
            y_bid, y_sz = bids_y[0]
            n_bid, n_sz = bids_n[0]
            for py_i, sy_i in bids_y[1:4]:
                if py_i + n_bid >= 1.0045:
                    y_bid, y_sz = py_i, y_sz + sy_i
                else:
                    break
            for pn_i, sn_i in bids_n[1:4]:
                if y_bid + pn_i >= 1.0045:
                    n_bid, n_sz = pn_i, n_sz + sn_i
                else:
                    break
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
        has_custom_split = hasattr(ex, "split_collateral_to_complete_set")
        sp = (
            ex.split_collateral_to_complete_set(cid, sh, neg_risk=False)
            if has_custom_split
            else (
                attempt_onchain_split_position(ex, cid, sh, neg_risk=False, up_token_id=y_tok, down_token_id=n_tok)
                if attempt_onchain_split_position is not None
                else {"success": False, "reason": "NO_SPLIT_HANDLER"}
            )
        )
        if not (sp or {}).get("success"):
            retry_cd[dedupe_k] = now_ts + 8.0
            return {"executed": False, "reason": f"SPLIT_FAILED:{(sp or {}).get('reason') or (sp or {}).get('error')}"}
        if not has_custom_split and wait_for_erc1155_delivery is not None:
            wait_for_erc1155_delivery(ex, [y_tok, n_tok], sh, timeout_sec=3.5)
        u_res = (
            ex.execute_atomic_box_overround_unwind(f"CTFOVR_{cid[:10]}", y_tok, y_bid, n_tok, n_bid, sh, False, False, fr, fe, fr, fe)
            if hasattr(ex, "execute_atomic_box_overround_unwind")
            else {"success": False}
        )
        if not (u_res or {}).get("success"):
            mid_ovr = str(candidate_box.get("leg_a_market_id") or candidate_box.get("market_id") or cid)
            sp_tx_s = str((sp or {}).get("tx_hash") or "")
            if (u_res or {}).get("partial_leg_unwind"):
                la_d = (u_res or {}).get("leg_a") or {}
                lb_d = (u_res or {}).get("leg_b") or {}
                a_sold = bool(la_d.get("filled") or la_d.get("success"))
                sold_d = la_d if a_sold else lb_d
                unsold_d = lb_d if a_sold else la_d
                unsold_tok = n_tok if a_sold else y_tok
                unsold_side = "NO" if a_sold else "YES"
                sold_cash = max(0.0, float(sold_d.get("taking_amount") or 0.0) - float(sold_d.get("fee_usd") or 0.0))
                uw_unk = bool(unsold_d.get("outcome_unknown"))
                uw_oid = unsold_d.get("orderID")
                unw_ok = False
                if not uw_unk and hasattr(ex, "execute_unwind_order"):
                    try:
                        uw = ex.execute_unwind_order(unsold_tok, size=sh, side="SELL", min_price=0.02, neg_risk=False)
                    except TypeError:
                        uw = ex.execute_unwind_order(f"UNW_OVR_{cid[:8]}", unsold_tok, sh, 0.02)
                    unw_ok = bool(getattr(uw, "success", False) or (isinstance(uw, Mapping) and uw.get("success")))
                    if not unw_ok and isinstance(uw, Mapping) and uw.get("outcome_unknown"):
                        uw_unk = True
                        uw_oid = uw.get("orderID") or uw_oid
                if not unw_ok:
                    _register_ctf_overround_residual(
                        harvester,
                        ex,
                        cid=cid,
                        market_id=mid_ovr,
                        unsold_tok=unsold_tok,
                        unsold_side=unsold_side,
                        cand_asset=cand_asset,
                        sh=sh,
                        rem_cost=round(max(0.01, sh - sold_cash), 4),
                        fr=fr,
                        fe=fe,
                        exp_ts=exp_ts,
                        now_ts=now_ts,
                        uw_unk=uw_unk,
                        uw_oid=uw_oid,
                        sp_tx=sp_tx_s,
                    )
                else:
                    if hasattr(ex, "invalidate_collateral_cache"):
                        ex.invalidate_collateral_cache()
                    harvester._pending_collateral_refresh = True
                retry_cd[dedupe_k] = now_ts + 8.0
                return {"executed": False, "reason": "OVERROUND_PARTIAL_LEG_UNWOUND"}
            sell_unk_s = bool((u_res or {}).get("outcome_unknown"))
            merged_ok_s = False
            if not sell_unk_s:
                if hasattr(ex, "attempt_onchain_complete_set_merge"):
                    m_out_s = ex.attempt_onchain_complete_set_merge(cid, min_pairs=max(1.0, sh - 0.05), max_pairs=sh, neg_risk=False)
                    merged_ok_s = bool(
                        isinstance(m_out_s, tuple) and len(m_out_s) >= 2 and m_out_s[0] and float(m_out_s[1] or 0.0) >= max(1.0, sh - 0.05)
                    )
                elif hasattr(ex, "merge_complete_set_positions"):
                    m_out_s = ex.merge_complete_set_positions(cid, sh, neg_risk=False)
                    merged_ok_s = bool((isinstance(m_out_s, Mapping) and (m_out_s.get("success") or m_out_s.get("merged"))) or getattr(m_out_s, "success", False))
            if merged_ok_s:
                if hasattr(ex, "invalidate_collateral_cache"):
                    ex.invalidate_collateral_cache()
                harvester._pending_collateral_refresh = True
            else:
                _register_ctf_overround_unmerged_pair(
                    harvester,
                    ex,
                    cid=cid,
                    market_id=mid_ovr,
                    y_tok=y_tok,
                    n_tok=n_tok,
                    cand_asset=cand_asset,
                    sh=sh,
                    fr=fr,
                    fe=fe,
                    exp_ts=exp_ts,
                    now_ts=now_ts,
                    la_d=(u_res or {}).get("leg_a") if isinstance(u_res, Mapping) else None,
                    lb_d=(u_res or {}).get("leg_b") if isinstance(u_res, Mapping) else None,
                    sp_tx=sp_tx_s,
                )
            retry_cd[dedupe_k] = now_ts + 8.0
            return {
                "executed": False,
                "reason": "OVERROUND_SWEEP_REJECTED_MERGED_BACK",
                "merged_back": merged_ok_s,
                "complete_set_supervised": not merged_ok_s,
            }
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
        try:
            from src.polymarket_research.economic_attribution_ledger import GLOBAL_DECAY_TRACKER, emit_funnel_event
            _ck_ovr = str(candidate_box.get("box_id") or dedupe_k or tid)
            GLOBAL_DECAY_TRACKER.mark_our_fill_or_cancel(_ck_ovr)
            for _st_ovr in ("ORDER_SUBMITTED", "COMPLETE_BASKET_LOCKED"):
                emit_funnel_event(
                    _st_ovr,
                    sleeve="CTF_OVERROUND_MINT_SELL",
                    candidate_key=_ck_ovr,
                    box_type="CTF_OVERROUND",
                    asset=cand_asset,
                    est_profit_usd=net_pnl,
                    notional_usd=sh,
                )
        except Exception:
            pass
        return {"executed": True, "result": u_res, "leg_trade_ids": [tid]}

    if btype == "MULTI_LEG_BUNDLE":
        raw_legs = [dict(lg) for lg in (candidate_box.get("legs") or []) if isinstance(lg, Mapping)]
        if not (3 <= len(raw_legs) <= 12):
            return {"executed": False, "reason": "INVALID_MULTI_LEG_COUNT"}
        busy = {str(p.get("market_id") or "") for p in harvester.active_positions.values()}
        leg_mids = [str(lg.get("market_id") or "") for lg in raw_legs if lg.get("market_id")]
        if any(m_id in busy for m_id in leg_mids):
            return {"executed": False, "reason": "MARKET_ALREADY_OCCUPIED"}
        evt_ok_ml, evt_rsn_ml, evt_rem_ml, evt_k_ml = check_per_event_concentration_cap(
            harvester, candidate_box, market_ids=leg_mids, now_ts=now_ts, min_headroom_usd=5.0
        )
        if not evt_ok_ml:
            return {"executed": False, "reason": evt_rsn_ml}
        budget = min(budget, evt_rem_ml)
        if budget < 5.0:
            return {"executed": False, "reason": "INSUFFICIENT_BOX_COLLATERAL_HEADROOM"}
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
                bids_lg = sorted([(float(b["price"]), float(b["size"])) for b in (bk.get("bids") or []) if float(b.get("size", 0)) > 0], reverse=True)
                lg_up = dict(lg)
                lg_up["ask_px"] = q_px
                lg_up["ask_size"] = best_sz
                lg_up["_best_bid_px"] = bids_lg[0][0] if bids_lg else 0.0
                refreshed_legs.append(lg_up)
            if tot_net_ps > max_cost_cap + 1e-6:
                return {"executed": False, "reason": f"FRESH_BUNDLE_COST_EXCEEDED:{tot_net_ps:.4f}"}
        else:
            refreshed_legs = raw_legs
            tot_net_ps = max(0.20, _sf(candidate_box.get("cost_per_share") or candidate_box.get("box_cost_net"), 0.985))
            min_sh_avail = _sf(candidate_box.get("max_fillable_shares"), 10.0)

        from src.polymarket_research.holistic_strategy_governance import passes_capital_velocity_hurdle

        vel_ml_ok, vel_ml_reason = passes_capital_velocity_hurdle(
            box_type="MULTI_LEG_BUNDLE",
            sleeve_src=sleeve_src,
            collat_usd=collat_f + cur_exp,
            rem_tte_sec=max(1.0, exp_ts - now_ts),
            box_cost_net=tot_net_ps,
        )
        if not vel_ml_ok:
            return {"executed": False, "reason": vel_ml_reason}

        sh = float(int(math.floor(min(budget / max(tot_net_ps, 0.25), min_sh_avail / 1.15))))
        if sh < 5.0:
            return {"executed": False, "reason": "BUNDLE_MIN_SHARES"}
        for lg_chk in refreshed_legs:
            lg_px_chk = _sf(lg_chk.get("ask_px"), 0.0)
            if lg_px_chk > 0.0 and (sh * lg_px_chk) < 1.00 - 1e-6:
                return {"executed": False, "reason": f"BUNDLE_SUB_DOLLAR_LEG_LOT:{sh * lg_px_chk:.2f}"}
        _real_clob_ml = bool(
            getattr(harvester, "enforce_bundle_unwind_guard", False)
            or (
                getattr(ex, "client", None) is not None
                and getattr(getattr(ex, "client", None), "_mock_children", None) is None
                and "place_fok_order" not in getattr(ex, "__dict__", {})
                and "execute_fok_order" not in getattr(ex, "__dict__", {})
                and "execute_snipe_order" not in getattr(ex, "__dict__", {})
            )
        )
        if _real_clob_ml and books_ml:
            max_uw_loss = max(1.75, budget * 0.10)
            for lg_chk in refreshed_legs:
                lg_px_c = _sf(lg_chk.get("ask_px"), 0.0)
                lg_bid_c = _sf(lg_chk.get("_best_bid_px"), 0.0)
                if lg_px_c >= 0.15:
                    if lg_bid_c <= 0.0:
                        return {"executed": False, "reason": "BUNDLE_LEG_NO_EXIT_BID_LIQUIDITY"}
                    if sh * max(0.0, lg_px_c - lg_bid_c) > max_uw_loss:
                        return {"executed": False, "reason": "BUNDLE_UNWIND_SPREAD_RISK_TOO_WIDE"}
        bid = str(candidate_box.get("box_id") or f"MLBOX_{int(now_ts)}")
        evt_id_ml = str(candidate_box.get("event_id") or "")
        try:
            from src.polymarket_research.economic_attribution_ledger import GLOBAL_DECAY_TRACKER, emit_funnel_event
            GLOBAL_DECAY_TRACKER.mark_our_fill_or_cancel(bid)
            emit_funnel_event(
                "ORDER_SUBMITTED",
                sleeve=sleeve_src,
                candidate_key=bid,
                box_type="MULTI_LEG_BUNDLE",
                asset=cand_asset,
                net_edge_bps=round(max(0.0, 1.0 - tot_net_ps) * 10000.0, 2),
                est_profit_usd=round(max(0.0, 1.0 - tot_net_ps) * sh, 4),
                notional_usd=round(tot_net_ps * sh, 4),
            )
        except Exception:
            pass
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
            event_id=evt_id_ml,
            event_group_key=evt_k_ml,
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
            event_id=evt_id_ml,
            event_group_key=evt_k_ml,
        )
        if getattr(harvester, "_last_known_collateral", None) is not None:
            harvester._last_known_collateral = max(0.0, float(harvester._last_known_collateral) - float(res["total_cost_usd"]))
        if hasattr(ex, "invalidate_collateral_cache"):
            ex.invalidate_collateral_cache()
        harvester._pending_collateral_refresh = True
        harvester.save_state()
        try:
            from src.polymarket_research.economic_attribution_ledger import emit_funnel_event
            emit_funnel_event(
                "COMPLETE_BASKET_LOCKED",
                sleeve=sleeve_src,
                candidate_key=bid,
                box_type="MULTI_LEG_BUNDLE",
                asset=cand_asset,
                net_edge_bps=round(max(0.0, 1.0 - float(res["total_cost_usd"]) / max(sh, 0.01)) * 10000.0, 2),
                est_profit_usd=round(max(0.0, sh - float(res["total_cost_usd"])), 4),
                notional_usd=round(float(res["total_cost_usd"]), 4),
            )
        except Exception:
            pass
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

    ny_tz = get_us_eastern_tz()

    now = float(now_ts if now_ts is not None else time.time())
    et_dt = datetime.fromtimestamp(now, tz=ny_tz)
    et_hr = float(et_dt.hour) + float(et_dt.minute) / 60.0

    def _extr_best_bid(bids_raw: Any) -> Tuple[float, float]:
        bids = sorted(
            [(float(b["price"]), float(b["size"])) for b in (bids_raw or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
            key=lambda x: -x[0],
        )
        return (round(bids[0][0], 4), round(bids[0][0] * bids[0][1], 2)) if bids else (0.0, 0.0)

    # Pillar 1: `EQ1_PYTH_EQUITY_DOMINANCE_BOX` (`09:30-16:00 ET` full RTH window)
    try:
        if 9.50 <= et_hr <= 16.0 and getattr(daemon, "pyth_close_ladders", None):
            eq_rungs = [
                rc
                for rgs in daemon.pyth_close_ladders.values()
                for rc in rgs
                if str(getattr(rc, "asset", "")).upper() in PYTH_EQUITY_SYMBOLS
                and not bool(getattr(rc, "is_downward", False))
                and 120.0 < (float(rc.end_ts) - now) <= 28800.0
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
                        fee_rate_touch=float(getattr(br, "fee_rate", 0.0) or 0.0),
                        fee_rate_noon=float(getattr(sr, "fee_rate", 0.0) or 0.0),
                        fee_exponent_touch=float(getattr(br, "fee_exponent", 1.0) or 1.0),
                        fee_exponent_noon=float(getattr(sr, "fee_exponent", 1.0) or 1.0),
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
                            leg_a={"token_id": br.yes_token, "opp_token_id": br.no_token, "label": "TOUCH_YES", "side": "YES", "market_id": br.market_id, "condition_id": br.condition_id, "strike": br.strike, "fee_rate": getattr(br, "fee_rate", 0.0), "fee_exponent": float(getattr(br, "fee_exponent", 1.0) or 1.0), "end_ts": br.end_ts},
                            leg_b={"token_id": sr.no_token, "opp_token_id": sr.yes_token, "label": "NOON_OPP", "side": "NO", "market_id": sr.market_id, "condition_id": sr.condition_id, "strike": sr.strike, "fee_rate": getattr(sr, "fee_rate", 0.0), "fee_exponent": float(getattr(sr, "fee_exponent", 1.0) or 1.0), "end_ts": sr.end_ts},
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
                    fr_h3, fe_h3 = float(tr_p.home_leg.get("fee_rate", 0.0) or 0.0), float(tr_p.home_leg.get("fee_exponent", 1.0) or 1.0)
                    fr_d3, fe_d3 = float(tr_p.draw_leg.get("fee_rate", 0.0) or 0.0), float(tr_p.draw_leg.get("fee_exponent", 1.0) or 1.0)
                    fr_a3, fe_a3 = float(tr_p.away_leg.get("fee_rate", 0.0) or 0.0), float(tr_p.away_leg.get("fee_exponent", 1.0) or 1.0)
                    c_3w = (
                        qh_3 + compute_exact_taker_fee_per_share(qh_3, fr_h3, fe_h3)
                        + qd_3 + compute_exact_taker_fee_per_share(qd_3, fr_d3, fe_d3)
                        + qa_3 + compute_exact_taker_fee_per_share(qa_3, fr_a3, fe_a3)
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
                                        {"token_id": tr_p.home_leg["yes_token"], "market_id": tr_p.home_leg["market_id"], "condition_id": tr_p.home_leg.get("condition_id", ""), "label": "HOME_YES", "ask_px": qh_3, "ask_size": hy_s, "fee_rate": fr_h3, "fee_exponent": fe_h3, "neg_risk": bool(tr_p.home_leg.get("neg_risk", True))},
                                        {"token_id": tr_p.draw_leg["yes_token"], "market_id": tr_p.draw_leg["market_id"], "condition_id": tr_p.draw_leg.get("condition_id", ""), "label": "DRAW_YES", "ask_px": qd_3, "ask_size": dy_s, "fee_rate": fr_d3, "fee_exponent": fe_d3, "neg_risk": bool(tr_p.draw_leg.get("neg_risk", True))},
                                        {"token_id": tr_p.away_leg["yes_token"], "market_id": tr_p.away_leg["market_id"], "condition_id": tr_p.away_leg.get("condition_id", ""), "label": "AWAY_YES", "ask_px": qa_3, "ask_size": ay_s, "fee_rate": fr_a3, "fee_exponent": fe_a3, "neg_risk": bool(tr_p.away_leg.get("neg_risk", True))},
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
                        fe_bt = float(btts_l.get("fee_exponent", 1.0) or 1.0)
                        fe_t15 = float(tot_15.get("fee_exponent", 1.0) or 1.0)
                        fe_dr = float(tr_p.draw_leg.get("fee_exponent", 1.0) or 1.0)
                        tok_meta_lp = {
                            str(btts_l["yes_token"]): (btts_l.get("market_id", ""), btts_l.get("condition_id", ""), btts_l["no_token"], "YES", bool(btts_l.get("neg_risk", False)), float(btts_l.get("fee_rate", 0.0) or 0.0), fe_bt),
                            str(btts_l["no_token"]): (btts_l.get("market_id", ""), btts_l.get("condition_id", ""), btts_l["yes_token"], "NO", bool(btts_l.get("neg_risk", False)), float(btts_l.get("fee_rate", 0.0) or 0.0), fe_bt),
                            str(tot_15["over_token"]): (tot_15.get("market_id", ""), tot_15.get("condition_id", ""), tot_15["under_token"], "YES", bool(tot_15.get("neg_risk", False)), float(tot_15.get("fee_rate", 0.0) or 0.0), fe_t15),
                            str(tot_15["under_token"]): (tot_15.get("market_id", ""), tot_15.get("condition_id", ""), tot_15["over_token"], "NO", bool(tot_15.get("neg_risk", False)), float(tot_15.get("fee_rate", 0.0) or 0.0), fe_t15),
                            str(tr_p.draw_leg["no_token"]): (tr_p.draw_leg.get("market_id", ""), tr_p.draw_leg.get("condition_id", ""), tr_p.draw_leg["yes_token"], "NO", bool(tr_p.draw_leg.get("neg_risk", True)), float(tr_p.draw_leg.get("fee_rate", 0.0) or 0.0), fe_dr),
                        }
                        for tri_h in detect_lp_comp1_sports_triangles(
                            quotes={
                                "BTTS": {"yes_token_id": btts_l["yes_token"], "no_token_id": btts_l["no_token"], "yes_ask": bty_p if bty_p < 1.0 else 0.0, "yes_ask_size": bty_s, "no_ask": btn_p if btn_p < 1.0 else 0.0, "no_ask_size": btn_s, "fee_rate": float(btts_l.get("fee_rate", 0.0) or 0.0), "fee_exponent": fe_bt},
                                "OVER_1_5": {"yes_token_id": tot_15["over_token"], "yes_ask": o15_p if o15_p < 1.0 else 0.0, "yes_ask_size": o15_s, "fee_rate": float(tot_15.get("fee_rate", 0.0) or 0.0), "fee_exponent": fe_t15},
                                "UNDER_1_5": {"yes_token_id": tot_15["under_token"], "yes_ask": u15_p if u15_p < 1.0 else 0.0, "yes_ask_size": u15_s, "fee_rate": float(tot_15.get("fee_rate", 0.0) or 0.0), "fee_exponent": fe_t15},
                                "DRAW": {"no_token_id": tr_p.draw_leg["no_token"], "no_ask": dn_p if dn_p < 1.0 else 0.0, "no_ask_size": dn_s, "fee_rate": float(tr_p.draw_leg.get("fee_rate", 0.0) or 0.0), "fee_exponent": fe_dr},
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
                                ma_lp, ca_lp, oa_lp, sa_lp, nra_lp, fra_lp, fea_lp = tok_meta_lp.get(ta_lp, ("", "", "", "YES", False, 0.0, 1.0))
                                mb_lp, cb_lp, ob_lp, sb_lp, nrb_lp, frb_lp, feb_lp = tok_meta_lp.get(tb_lp, ("", "", "", "YES", False, 0.0, 1.0))
                                bka_lp, bkb_lp = pm_bks.get(ta_lp), pm_bks.get(tb_lp)
                                if ma_lp and mb_lp and ma_lp != mb_lp and bka_lp and bkb_lp:
                                    daemon.emit_live_two_leg_box_candidate(
                                        box_type="SPORTS_CORRIDOR",
                                        sleeve_source="LP_COMP1_SPORTS_TRIANGLES",
                                        asset="SOCCER",
                                        dedupe_key=f"LPCOMP1_{tr_p.game_id}_{tri_h['triangle_id']}",
                                        leg_a={"token_id": ta_lp, "opp_token_id": oa_lp, "label": t_legs[0].get("role", "LEG_A"), "side": sa_lp, "market_id": ma_lp, "condition_id": ca_lp, "fee_rate": fra_lp, "fee_exponent": fea_lp, "neg_risk": nra_lp, "end_ts": tr_p.end_ts},
                                        leg_b={"token_id": tb_lp, "opp_token_id": ob_lp, "label": t_legs[1].get("role", "LEG_B"), "side": sb_lp, "market_id": mb_lp, "condition_id": cb_lp, "fee_rate": frb_lp, "fee_exponent": feb_lp, "neg_risk": nrb_lp, "end_ts": tr_p.end_ts},
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
                                    mt_t, ct_t, _, _, nrt_t, frt_t, fet_t = tok_meta_lp.get(tk_t, ("", "", "", "YES", False, 0.0, 1.0))
                                    enr_legs.append({**lg_t, "market_id": mt_t, "condition_id": ct_t, "neg_risk": nrt_t, "fee_rate": frt_t, "fee_exponent": fet_t})
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
            from src.polymarket_research.weather_metar_engine import (
                fetch_metar_observations_sync,
                has_metar_oracle_contradiction,
            )
            now_utc_w = datetime.fromtimestamp(now, tz=timezone.utc)
            w_active: List[Tuple[float, Any, Any]] = []
            for sp_w in w_evts:
                end_w = resolve_weather_effective_end_ts(sp_w, now + 86400.0)
                if not (120.0 < (end_w - now) <= 86400.0):
                    continue
                loc_dt = now_utc_w.astimezone(safe_zoneinfo(sp_w.tz_name))
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
                if any(bool(getattr(m, "is_corrected", False) or getattr(m, "is_anomalous", False)) for m in (obs_l or [])) or has_metar_oracle_contradiction(list(obs_l or [])):
                    continue
                valid_obs = list(obs_l or [])
                raw_lines = [str(m.raw_line) for m in valid_obs if getattr(m, "raw_line", None)]
                cur_tc = float(valid_obs[-1].temp_c) if (valid_obs and getattr(valid_obs[-1], "temp_c", None) is not None) else None
                cur_tg = bool(getattr(valid_obs[-1], "has_t_remark", False)) if valid_obs else False
                if not raw_lines and cur_tc is None:
                    continue
                loc_hm = (loc_dt.hour, loc_dt.minute)
                _w_rules = str(getattr(sp_w, "rules_text", "") or getattr(sp_w, "description", "") or getattr(sp_w, "title", "") or "")
                ext_w = compute_running_metar_extrema(
                    raw_lines,
                    unit=sp_w.unit,
                    current_temp_c=cur_tc,
                    current_has_t_group=cur_tg,
                    station_icao=sp_w.icao,
                    rules_text=_w_rules,
                )
                if ext_w is None:
                    continue
                floor_w = int(ext_w["confirmed_running_high_floor"])
                ceil_lo_w = int(ext_w["confirmed_running_low_ceil"])
                m_mode_pre = str(getattr(sp_w, "metric", "HIGH") or "HIGH").upper()
                has_elim_bkt = loc_hm >= (23, 51) or any(
                    (m_mode_pre == "HIGH" and math.isfinite(bk_spec.high_bound) and int(round(bk_spec.high_bound)) < floor_w)
                    or (m_mode_pre == "LOW" and math.isfinite(bk_spec.low_bound) and int(round(bk_spec.low_bound)) > ceil_lo_w)
                    for bk_spec in sp_w.buckets
                )
                if not has_elim_bkt:
                    continue
                w_ready.append((sp_w, end_w, loc_hm, raw_lines, cur_tc, cur_tg, _w_rules, floor_w, ceil_lo_w))
                for bk_spec in sp_w.buckets:
                    w_toks.extend((bk_spec.yes_token, bk_spec.no_token))
            if w_ready and w_toks:
                w_bks = await daemon.fetch_books_batch(list(dict.fromkeys(w_toks)), timeout=3.0)
                for sp_w, end_w, loc_hm, raw_lines, cur_tc, cur_tg, _w_rules, floor_w, ceil_lo_w in w_ready:
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
                    # NR_M1 (`m=1`) Dead-Seed Overround Fanout on METAR-eliminated NegRisk weather brackets:
                    # Buy 1 dead NO -> NegRiskAdapterV2.convertPositions(m=1) -> sell N-1 live YES bids in <10s!
                    nrc_w_spec = (getattr(daemon, "negrisk_convert_slates", None) or {}).get(str(getattr(sp_w, "event_id", "") or ""))
                    if (
                        nrc_w_spec is not None
                        and getattr(nrc_w_spec, "is_closed_convert_safe", False)
                        and hasattr(daemon, "emit_live_negrisk_convert_candidate")
                        and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_nr_m1_dead_seed_fanout", True))
                    ):
                        dead_w_mids = {
                            str(b_chk.market_id)
                            for b_chk in sp_w.buckets
                            if (
                                (m_mode_w == "HIGH" and floor_w is not None and math.isfinite(b_chk.high_bound) and int(round(b_chk.high_bound)) < floor_w)
                                or (m_mode_w == "LOW" and ceil_lo_w is not None and math.isfinite(b_chk.low_bound) and int(round(b_chk.low_bound)) > ceil_lo_w)
                            )
                        }
                        dead_w_q = {
                            int(b_nr.get("question_index") if isinstance(b_nr, Mapping) else getattr(b_nr, "question_index", 0))
                            for b_nr in getattr(nrc_w_spec, "brackets", ())
                            if str(b_nr.get("market_id") if isinstance(b_nr, Mapping) else getattr(b_nr, "market_id", "")) in dead_w_mids
                            and (b_nr.get("question_index") if isinstance(b_nr, Mapping) else getattr(b_nr, "question_index", None)) is not None
                        }
                        if dead_w_q:
                            daemon.__dict__.setdefault("_ws_dead_q_by_event", {})[sp_w.event_id] = set(dead_w_q)
                            m1_w_hit = detect_nr_m1_dead_seed_fanout(
                                nrc_w_spec,
                                dead_w_q,
                                w_bks,
                                fee_bips=int(getattr(nrc_w_spec, "fee_bips", 0) or 0),
                                min_shares=5.0,
                                min_net_edge_usd=0.0035,
                            )
                            if m1_w_hit is not None:
                                opps_out.append({
                                    "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                                    "market": f"{sp_w.city} ({sp_w.icao}) NR_M1 Dead-NO Fanout (Q{m1_w_hit['dead_question_index']})",
                                    "ask_vwap": m1_w_hit["ask_eff_per_share"],
                                    "p_model": 1.0,
                                    "net_edge": m1_w_hit["net_edge_per_share"],
                                    "l1_usd": round(float(m1_w_hit["shares"]) * float(m1_w_hit["ask_eff_per_share"]), 2),
                                })
                                daemon.emit_live_negrisk_convert_candidate(
                                    sleeve_source="W_PRUNE1_DEAD_NO_BOND",
                                    spec=nrc_w_spec,
                                    dedupe_key=f"NRM1_WPRUNE_{sp_w.event_id}_Q{m1_w_hit['dead_question_index']}",
                                    arb_hit=m1_w_hit,
                                    books_by_token=w_bks,
                                    now_ts=now,
                                    fee_bips=int(getattr(nrc_w_spec, "fee_bips", 0) or 0),
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
                            _rem_w_s = float(end_w - now)
                            _vel_w_bps_hr = ((1.0 - float(hw["ask_px"])) * 10000.0) / max(0.25, _rem_w_s / 3600.0)
                            if is_no_w and _rem_w_s > 7200.0 and recycle_998_sh < 5.0 and not (_rem_w_s <= 14400.0 and _vel_w_bps_hr >= 15.0):
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
                                        leg_a={"token_id": la_w["token_id"], "opp_token_id": la_w["opp_token_id"], "label": la_w["label"], "side": "YES", "market_id": la_w["market_id"], "condition_id": la_w["condition_id"], "fee_rate": la_w["fee_rate"], "fee_exponent": 1.0, "neg_risk": True, "end_ts": end_w, "event_id": str(sp_w.event_id)},
                                        leg_b={"token_id": lb_w["token_id"], "opp_token_id": lb_w["opp_token_id"], "label": lb_w["label"], "side": "YES", "market_id": lb_w["market_id"], "condition_id": lb_w["condition_id"], "fee_rate": lb_w["fee_rate"], "fee_exponent": 1.0, "neg_risk": True, "end_ts": end_w, "event_id": str(sp_w.event_id)},
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
                                            "event_id": str(sp_w.event_id),
                                            "legs": [{k: v for k, v in x.items() if k != "bk_yes"} for x in enr_w_legs],
                                            "box_cost_net": hw["cost_per_share"],
                                            "max_box_cost_net": 0.992,
                                            "max_fillable_shares": hw["max_fillable_shares"],
                                            "neg_risk": True,
                                        },
                                    )
                    # Post 0%-maker-fee bids (`<= $0.9975`, +25% V2 Weather maker rebate) on METAR-dead `NO` brackets when `TTE <= 240m`!
                    if (end_w - now) <= 14400.0 and hasattr(daemon, "emit_live_single_leg_maker_lock_candidate"):
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
                                max_rb_w = 0.9975 if (end_w - now) <= 7200.0 else 0.9950
                                if 0.940 <= nb_w <= max_rb_w and nb_u_w >= 5.0 and yb_w <= 0.006:
                                    fr_w = max(0.0, float(getattr(b_sp, "fee_rate", 0.0) or 0.0))
                                    fe_w = max(1.0, float(getattr(b_sp, "fee_exponent", 1.0) or 1.0))
                                    reb_w = round(0.25 * fr_w * ((nb_w * (1.0 - nb_w)) ** fe_w), 5) if fr_w > 0.0 else 0.0
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
                                        max_resting_bid=max_rb_w,
                                        min_maker_edge=0.0024 if (end_w - now) <= 7200.0 else 0.0048,
                                        max_opp_bid=0.006,
                                        hold_to_maturity=True,
                                        p_model=0.9999,
                                        maker_rebate_ps=reb_w,
                                        event_id=str(sp_w.event_id),
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
            for d_leg in list(getattr(daemon, "fomc_truth_legs", None) or ()) + list(getattr(daemon, "lp1_bop_legs", None) or ()) + list(getattr(daemon, "zerofee_general_binaries", None) or ()):
                if isinstance(d_leg, Mapping):
                    _reg_bin(
                        d_leg.get("market_id", ""), d_leg.get("condition_id", ""),
                        d_leg.get("yes_token", "") or d_leg.get("yes_token_id", ""),
                        d_leg.get("no_token", "") or d_leg.get("no_token_id", ""),
                        float(d_leg.get("fee_rate", 0.0) or 0.0), 1.0, bool(d_leg.get("neg_risk", False)),
                        float(d_leg.get("end_ts", 0.0) or 0.0), str(d_leg.get("asset") or "ZEROFEE"),
                    )

            bin_rows: List[Dict[str, Any]] = []
            rest_need: List[Dict[str, Any]] = []
            has_ws_fn = hasattr(daemon, "_get_fresh_ws_book") and bool(getattr(daemon, "_ws_books", None))
            daemon.__dict__["_ws_reactive_bin_metas"] = sorted(
                [
                    m_z for m_z in cand_bins.values()
                    if not m_z.get("neg_risk")
                    and (
                        float(m_z.get("fee_rate") or 0.0) <= 1e-9
                        or 0.0 < (float(m_z.get("end_ts") or 0.0) - now) <= 14400.0
                    )
                ],
                key=lambda mx: (
                    0 if float(mx.get("fee_rate") or 0.0) <= 1e-9 else 1,
                    max(0.0, float(mx.get("end_ts") or (now + 86400.0)) - now),
                ),
            )[:80]
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

            if rest_need and hasattr(daemon, "fetch_books_batch") and (now - float(daemon.__dict__.get("_last_c1_rot_ts", 0.0))) >= 3.0:
                daemon.__dict__["_last_c1_rot_ts"] = now
                rest_need.sort(
                    key=lambda mx: (
                        0 if (not mx.get("neg_risk") and float(mx.get("fee_rate") or 0.0) <= 1e-9) else 1,
                        max(0.0, float(mx.get("end_ts") or (now + 86400.0)) - now),
                    )
                )
                cur_idx = int(daemon.__dict__.get("_c1_rot_cursor", 0) or 0) % max(1, len(rest_need))
                batch_m = (rest_need[cur_idx : cur_idx + 48] + rest_need[: max(0, cur_idx + 48 - len(rest_need))])[:48]
                daemon.__dict__["_c1_rot_cursor"] = (cur_idx + 48) % max(1, len(rest_need))
                rot_toks = [t for m_x in batch_m for t in (m_x["yes_token_id"], m_x["no_token_id"])]
                rot_bks = await daemon.fetch_books_batch(rot_toks, timeout=2.2)
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
                _rb_zf = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
                _en_zf1 = bool(_rb_zf.get("enable_zerofee1_mergeable_sweeper", True))
                _zf1_min_ed = max(0.0025, float(_rb_zf.get("zerofee1_min_net_edge_bps", 45.0) or 45.0) / 10000.0) if _en_zf1 else 0.008
                _zf1_max_cost = round(1.0 - _zf1_min_ed, 4)
                by_cid_r = {x["condition_id"]: x for x in bin_rows}
                for ov_hit in scan_full_universe_c1_and_ctf_overround(
                    bin_rows, min_underround_edge=_zf1_min_ed, min_overround_edge=0.0045
                ):
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
                        is_zf_mergeable = (not bool(src_r["neg_risk"])) and float(src_r["fee_rate"] or 0.0) <= 1e-9
                        if float(ov_hit["cost_per_share"]) > (_zf1_max_cost if (is_zf_mergeable and _en_zf1) else 0.992) + 1e-6:
                            continue
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
                            max_box_cost_override=_zf1_max_cost if (is_zf_mergeable and _en_zf1) else 0.992,
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
            bridge_ml = {"N1_NEGRISK_CROSS_BOX", "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "SUM1_FRECHET_SUM_TRIANGLES", "FED1_CENTRAL_BANK_LP_BOX", "COND1_MACRO_PARTITION_BOX"}
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
                                    lgs8.append({**{k_x: v_x for k_x, v_x in lg_x.items() if k_x != "mask"}, "ask_px": ax_p, "ask_size": ax_s})
                        if len(lgs8) == len(ex8["legs"]):
                            c8 = sum(float(x["ask_px"]) + compute_exact_taker_fee_per_share(float(x["ask_px"]), float(x.get("fee_rate", 0.0) or 0.0), 1.0) for x in lgs8)
                            if c8 <= 0.990:
                                daemon.emit_live_special_v2_box_candidate(
                                    box_type="MULTI_LEG_BUNDLE", sleeve_source=sl8, asset=ast8,
                                    dedupe_key=str(p8.get("dedupe_key") or pid8), close_ts=cl8, now_ts=now,
                                    payload={"legs": lgs8, "cost_per_share": round(c8, 6), "box_cost_net": round(c8, 6), "max_box_cost_net": 0.990, "max_fillable_shares": min(float(x["ask_size"]) for x in lgs8), "neg_risk": any(bool(x.get("neg_risk")) for x in lgs8)},
                                )
    except Exception as exc_p8:
        logger.debug(f"Protocol V2 Pillar 8 bridge notice: {exc_p8}")


_LIVE_CAND_BG_LOCK = threading.Lock()
_LIVE_CAND_BG_QUEUE: Any = None


def _trim_ws_books_top10(ws_books: Any) -> Any:
    """Trims L2 `ws_books` to top-10 sorted bids + top-10 sorted asks (<1.8 KB) so AF_UNIX datagrams never truncate at 64 KB."""
    if not isinstance(ws_books, Mapping):
        return ws_books
    out: Dict[str, Any] = {}
    for tk, bk in ws_books.items():
        if not isinstance(bk, Mapping):
            out[str(tk)] = bk
            continue
        raw_b = bk.get("bids") or []
        raw_a = bk.get("asks") or []
        top_b = sorted(
            raw_b,
            key=lambda x: float(x.get("price", 0.0) if isinstance(x, Mapping) else x[0]),
            reverse=True,
        )[:10]
        top_a = sorted(
            raw_a,
            key=lambda x: float(x.get("price", 1.0) if isinstance(x, Mapping) else x[0]),
        )[:10]
        trimmed: Dict[str, Any] = {"bids": top_b, "asks": top_a}
        for k_meta in ("minimum_tick_size", "tick_size", "last_trade_price", "timestamp", "_s2_meta"):
            if k_meta in bk:
                trimmed[k_meta] = bk[k_meta]
        out[str(tk)] = trimmed
    return out


def _enqueue_cand_disk_append(cp: Any, line_s: str) -> None:
    global _LIVE_CAND_BG_QUEUE
    import os as _os
    import queue as _queue

    if _LIVE_CAND_BG_QUEUE is None:
        with _LIVE_CAND_BG_LOCK:
            if _LIVE_CAND_BG_QUEUE is None:
                q: Any = _queue.Queue(maxsize=4096)

                def _bg_worker() -> None:
                    while True:
                        p_it, ln_it = q.get()
                        try:
                            p_it.parent.mkdir(parents=True, exist_ok=True)
                            if p_it.exists() and p_it.stat().st_size >= 25 * 1024 * 1024:
                                _os.replace(p_it, p_it.with_name(p_it.name + ".1"))
                            with open(p_it, "a", encoding="utf-8") as fp_w:
                                fp_w.write(ln_it)
                        except Exception:
                            pass
                        finally:
                            q.task_done()

                threading.Thread(target=_bg_worker, name="d1-cand-jsonl-writer", daemon=True).start()
                _LIVE_CAND_BG_QUEUE = q
    try:
        _LIVE_CAND_BG_QUEUE.put_nowait((cp, line_s))
    except Exception:
        with open(cp, "a", encoding="utf-8") as fp_fb:
            fp_fb.write(line_s)


def _write_and_notify_live_cand(daemon: Any, cand: Dict[str, Any], cand_file: Any, default_cand_path: Any) -> bool:
    import json as _json
    import os as _os
    from pathlib import Path as _Path

    try:
        cand_send = dict(cand) if isinstance(cand.get("ws_books"), Mapping) else cand
        if isinstance(cand_send.get("ws_books"), Mapping):
            cand_send["ws_books"] = _trim_ws_books_top10(cand_send["ws_books"])
        try:
            import orjson as _orj

            raw_b = _orj.dumps(cand_send) + b"\n"
            line_s = raw_b.decode("utf-8")
        except Exception:
            line_s = _json.dumps(cand_send, separators=(",", ":")) + "\n"
            raw_b = line_s.encode("utf-8")
        cp = _Path(cand_file)
        is_default_live = (_os.name != "nt" and cp == _Path(default_cand_path))
        is_real_prod_cand = (
            is_default_live
            and cp.parent.name == "polymarket"
            and cp.name == "d1_live_box_candidates.jsonl"
            and not str(cp).startswith("/tmp/")
        )
        if is_real_prod_cand and not bool(getattr(daemon, "single_scan", False)):
            from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER
            from src.polymarket_research.stage_c_zero_loss_velocity import evaluate_strict_pure_riskless_candidate

            ok_pure, _ = evaluate_strict_pure_riskless_candidate(cand, GLOBAL_GOVERNANCE_MANAGER.snapshot)
            if not ok_pure:
                return False
        if is_default_live:
            try:
                import socket as _socket

                s_ipc = getattr(daemon, "_d1_ipc_sock", None)
                if s_ipc is None:
                    s_ipc = _socket.socket(_socket.AF_UNIX, _socket.SOCK_DGRAM)
                    s_ipc.setblocking(False)
                    try:
                        s_ipc.setsockopt(_socket.SOL_SOCKET, _socket.SO_SNDBUF, 524288)
                    except Exception:
                        pass
                    daemon._d1_ipc_sock = s_ipc
                ipc_nm = _os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME", "polymarket_d1_box_notify")
                s_ipc.sendto(raw_b, f"\x00{ipc_nm}".encode("utf-8"))
            except Exception:
                pass
        if is_real_prod_cand and not bool(getattr(daemon, "single_scan", False)):
            try:
                from src.polymarket_research.economic_attribution_ledger import register_candidate_funnel_and_decay_watch
                register_candidate_funnel_and_decay_watch(cand)
            except Exception:
                pass
            _enqueue_cand_disk_append(cp, line_s)
            return True
        cp.parent.mkdir(parents=True, exist_ok=True)
        if cp == _Path(default_cand_path) and cp.exists():
            try:
                if cp.stat().st_size >= 25 * 1024 * 1024:
                    _os.replace(cp, cp.with_name(cp.name + ".1"))
            except OSError:
                pass
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
    event_id: str = "",
    pair_dedupe_key: str = "",
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
    if event_id and not cand.get("event_id"):
        cand["event_id"] = str(event_id)
    if pair_dedupe_key and not cand.get("pair_dedupe_key"):
        cand["pair_dedupe_key"] = str(pair_dedupe_key)
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
    event_id: str = "",
    pair_dedupe_key: str = "",
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
        min_l1_usd=5.0,
        max_ask_px=min(0.9985, float(max_lock_eff_px) + 0.001),
        fee_exponent=float(fee_exponent),
    )
    def _maybe_emit_ws_clinch_watch() -> None:
        if (
            daemon.single_scan
            or ("fetch_json" in daemon.__dict__)
            or cand_file != default_cand_path
            or state_file != default_state_path
            or float(p_model) < 0.998
            or not bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_ws_clinch_sniper", True))
        ):
            return
        w_map = daemon.__dict__.setdefault("_last_ws_clinch_watch_emit_ts", {})
        reemit_iv = 12.0 if is_s2_fast else 120.0
        if (now_ts - float(w_map.get(str(token_id), 0.0) or 0.0)) < reemit_iv:
            return
        if len(w_map) > 512:
            daemon.__dict__["_last_ws_clinch_watch_emit_ts"] = {k: v for k, v in w_map.items() if (now_ts - float(v)) <= 1200.0}
            w_map = daemon.__dict__["_last_ws_clinch_watch_emit_ts"]
        w_cand = {
            "box_id": f"CWATCH_{asset}_{int(close_ts)}_{str(market_id or '0')[-5:]}",
            "dedupe_key": dedupe_key,
            "pair_dedupe_key": str(pair_dedupe_key or ""),
            "box_type": "CLINCH_WATCHLIST_REG",
            "ts_unix": round(now_ts, 3),
            "asset": str(asset),
            "event_id": str(event_id or ""),
            "sleeve_source": str(sleeve_source),
            "expiry_ts": float(close_ts),
            "max_box_cost_net": float(max_lock_eff_px),
            "max_opp_bid": float(max_opp_bid),
            "hold_to_maturity": bool(hold_to_maturity),
            "p_model": round(float(p_model), 4),
            "leg_a_token_id": str(token_id),
            "leg_a_opp_token_id": str(opp_token_id),
            "leg_a_label": str(display_label)[:64],
            "leg_a_side": str(side_label),
            "leg_a_market_id": str(market_id),
            "leg_a_condition_id": str(condition_id),
            "leg_a_fee_rate": float(fee_rate),
            "leg_a_fee_exponent": float(fee_exponent),
            "leg_a_neg_risk": bool(neg_risk),
            "leg_a_expiry_ts": float(close_ts),
            "ws_books": (
                {str(token_id): bk_win, str(opp_token_id): bk_opp}
                if (isinstance(bk_win, dict) and isinstance(bk_opp, dict))
                else None
            ),
            "ws_books_ts": round(now_ts, 3),
        }
        if isinstance(bk_win.get("_s2_meta"), Mapping):
            w_cand.update(bk_win["_s2_meta"])
        if check_sll_cand_dispute_guard(w_cand) is not None:
            return
        w_map[str(token_id)] = now_ts
        _write_and_notify_live_cand(daemon, w_cand, cand_file, default_cand_path)

    if not w_lk.get("filled"):
        _maybe_emit_ws_clinch_watch()
        return False
    eff_px = float(w_lk["eff_px"])
    min_req_edge = max(0.002, round(float(p_model) - float(max_lock_eff_px), 6))
    if eff_px > float(max_lock_eff_px) + 1e-6 or float(w_lk["shares"]) < 5.0 or (float(p_model) - eff_px) < min_req_edge - 1e-6:
        _maybe_emit_ws_clinch_watch()
        return False
    _ws_tk_1l_raw = (getattr(daemon, "_token_tick_sizes", None) or {}).get(str(token_id))
    try:
        _ws_tk_1l = float(_ws_tk_1l_raw) if _ws_tk_1l_raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        _ws_tk_1l = 0.0
    cand = {
        "box_id": f"LOCK1_LIVE_{asset}_{int(close_ts)}_{str(market_id or '0')[-5:]}",
        "dedupe_key": dedupe_key,
        "pair_dedupe_key": str(pair_dedupe_key or ""),
        "box_type": "SINGLE_LEG_LOCK",
        "ts_unix": round(now_ts, 3),
        "asset": str(asset),
        "event_id": str(event_id or ""),
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
    if 0.0001 <= _ws_tk_1l <= 0.1:
        cand["leg_a_tick_size"] = _ws_tk_1l
        cand["leg_a_ws_tick_size"] = _ws_tk_1l
    if isinstance(bk_win.get("_s2_meta"), Mapping):
        cand.update(bk_win["_s2_meta"])
    if check_sll_cand_dispute_guard(cand) is not None:
        return False
    if len(daemon._last_d1_live_emit_ts) > 256:
        daemon._last_d1_live_emit_ts = {k: v for k, v in daemon._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
    daemon._last_d1_live_emit_ts[dedupe_key] = now_ts
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
    event_id: str = "",
    pair_dedupe_key: str = "",
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
    _is_m1_emit = (
        _mode_in == "NR_M1_DEAD_SEED_OVERROUND"
        and bool(arb_hit.get("nr_m1_zero_loss_verified")) is True
        and len(no_legs_out) == 1
        and len(liquid_yes_sells) == 1
    )
    if _is_m1_emit:
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER
        _m1_max_hrs = float(
            GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("seed_max_lockup_hours", 24.0) or 24.0
        )
        if rem_sec > _m1_max_hrs * 3600.0 + 1e-6:
            return False
    if _mode_in == "NR5_NEGATIVE_COST_FREEROLL":
        _min_nr_ed = 0.0020
    elif _mode_in in {"NR4_FULL_SWEEP", "NR_M1_DEAD_SEED_OVERROUND"}:
        _min_nr_ed = 0.0035
    else:
        _min_nr_ed = 0.0045 if not liquid_yes_sells else 0.0065
    if (len(no_legs_out) < 2 and not _is_m1_emit) or edge_ps < _min_nr_ed:
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
    surviving_yes_legs = [
        {
            "yes_token": str(b.get("yes_token") or ""),
            "market_id": str(b.get("market_id") or ""),
            "condition_id": str(b.get("condition_id") or ""),
            "question_index": int(b.get("question_index") or 0),
            "label": str(b.get("label") or "")[:48],
        }
        for b in (arb_hit.get("surviving_yes_brackets") or [])
        if b.get("yes_token")
    ]
    cand = {
        "box_id": f"NRCONV_LIVE_{spec.event_id}_{int(now_ts)}",
        "dedupe_key": dedupe_key,
        "box_type": "NEGRISK_CONVERT",
        "convert_mode": conv_mode,
        "nr_m1_zero_loss_verified": bool(_is_m1_emit),
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
        "surviving_yes_legs": surviving_yes_legs,
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
    event_id: str = "",
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
    _max_rw_carry_sec = 28800.0 if float(p_model) >= 0.999 else 2700.0
    if (
        sleeve_source == "MKR_REWARD_LOCKED_CARRY"
        and rem_sec > _max_rw_carry_sec
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
    _meta_in = bk_win.get("_s2_meta") if isinstance(bk_win.get("_s2_meta"), Mapping) else {}
    _has_vol24 = ("volume24hr" in _meta_in and _meta_in.get("volume24hr") is not None) or ("volume_24h_usd" in _meta_in and _meta_in.get("volume_24h_usd") is not None)
    _vol24_u = max(0.0, float(_meta_in.get("volume24hr") if _meta_in.get("volume24hr") is not None else (_meta_in.get("volume_24h_usd") or 0.0)))
    if (
        not is_mock_emit
        and not is_s2_mkr
        and str(sleeve_source) != "MKR_REWARD_LOCKED_CARRY"
        and not valid_asks
        and l1_bid_usd < 75.0
        and _has_vol24
        and _vol24_u < 350.0
    ):
        return False
    _ws_tk_mkr_raw = (getattr(daemon, "_token_tick_sizes", None) or {}).get(str(token_id))
    try:
        _ws_tk_mkr = float(_ws_tk_mkr_raw) if _ws_tk_mkr_raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        _ws_tk_mkr = 0.0
    _in_096_zone = bool(best_bid >= 0.96 or (target_bid_px is not None and float(target_bid_px) >= 0.96))
    if not is_mock_emit and _in_096_zone and abs(_ws_tk_mkr - 0.01) < 1e-9:
        _ws_tk_mkr = 0.0
        _ws_tk_mkr_raw = None
    raw_bk_tk = (
        _ws_tk_mkr_raw
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
        and (not _in_096_zone or float(lv.get("price", 0.0) or 0.0) >= 0.95)
        for lv in ((bk_win.get("bids") or []) + (bk_win.get("asks") or []))
        if isinstance(lv, Mapping) and float(lv.get("size", 0.0) or 0.0) > 0.0
    )
    if has_subcent_lv and (bk_tk_f <= 0.0 or bk_tk_f > 0.001):
        bk_tk_f = 0.001
    elif bk_tk_f <= 0.0 and not is_mock_emit:
        bk_tk_f = 0.001 if _in_096_zone else 0.01
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
    max_join_l1_usd = 1200.0 if is_s2_mkr else 350.0
    if abs(resting_bid - best_bid) <= 1e-6 and l1_bid_usd > max_join_l1_usd and not is_mock_emit:
        return False
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
        "queue_ahead_usd": 0.0 if resting_bid > best_bid + 1e-6 else round(l1_bid_usd, 2),
        "ask_depth_usd": round(
            sum(
                float(a.get("price", 0.0) or 0.0) * float(a.get("size", 0.0) or 0.0)
                for a in (bk_win.get("asks") or [])
                if isinstance(a, Mapping) and float(a.get("size", 0.0) or 0.0) > 0.0
            ),
            2,
        ),
        **({"volume_24h_usd": round(_vol24_u, 2)} if _has_vol24 else {}),
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
        "ws_books": (
            {str(token_id): (fw_w or bk_win), str(opp_token_id): (fw_o or bk_opp)}
            if (not is_mock_emit and isinstance(bk_win, dict) and isinstance(bk_opp, dict))
            else ({str(token_id): fw_w, str(opp_token_id): fw_o} if (fw_w and fw_o) else None)
        ),
        "ws_books_ts": round(now_ts, 3),
    }
    if str(event_id or "").strip():
        cand["event_id"] = str(event_id).strip()
    if 0.0001 <= _ws_tk_mkr <= 0.1:
        cand["leg_a_ws_tick_size"] = _ws_tk_mkr
    if isinstance(bk_win.get("_s2_meta"), Mapping):
        cand.update(bk_win["_s2_meta"])
    if check_sll_cand_dispute_guard(cand) is not None:
        return False
    if not is_s2_mkr and not is_mock_emit:
        _sig_map = daemon.__dict__.setdefault("_last_sll_quote_sig", {})
        _cur_sig = (round(resting_bid, 4), round(best_bid, 4))
        _prev_sig = _sig_map.get(dedupe_key) if dedupe_key in daemon._last_d1_live_emit_ts else None
        if _prev_sig is not None and _prev_sig[1] == _cur_sig and (now_ts - float(_prev_sig[0])) < 60.0:
            return False
        if len(_sig_map) > 512:
            _sig_map.clear()
        _sig_map[dedupe_key] = (now_ts, _cur_sig)
    if len(daemon._last_d1_live_emit_ts) > 256:
        daemon._last_d1_live_emit_ts = {k: v for k, v in daemon._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
    daemon._last_d1_live_emit_ts[dedupe_key] = now_ts
    if (
        not is_mock_emit
        and getattr(cand_file, "name", "") == "d1_live_box_candidates.jsonl"
        and cand_file == default_cand_path
        and state_file == default_state_path
        and float(p_model) >= 0.998
        and rem_sec >= (4.5 if is_s2_mkr else 26.0)
        and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_ws_clinch_sniper", True))
    ):
        _wm_mkr = daemon.__dict__.setdefault("_last_ws_clinch_watch_emit_ts", {})
        if (now_ts - float(_wm_mkr.get(str(token_id), 0.0) or 0.0)) >= (12.0 if is_s2_mkr else 120.0):
            if len(_wm_mkr) > 512:
                daemon.__dict__["_last_ws_clinch_watch_emit_ts"] = {k: v for k, v in _wm_mkr.items() if (now_ts - float(v)) <= 1200.0}
                _wm_mkr = daemon.__dict__["_last_ws_clinch_watch_emit_ts"]
            _wm_mkr[str(token_id)] = now_ts
            _w_mkr_cand = {
                "box_id": f"CWATCH_MKR_{asset}_{int(close_ts)}_{str(market_id or '0')[-5:]}",
                "dedupe_key": pair_dedupe_key or dedupe_key,
                "box_type": "CLINCH_WATCHLIST_REG",
                "ts_unix": round(now_ts, 3),
                "asset": str(asset),
                "sleeve_source": str(sleeve_source),
                "expiry_ts": float(close_ts),
                "max_box_cost_net": round(min(0.997, max(float(max_resting_bid), float(p_model) - 0.0025)), 4),
                "max_opp_bid": float(max_opp_bid),
                "hold_to_maturity": bool(hold_to_maturity),
                "p_model": round(float(p_model), 4),
                "leg_a_token_id": str(token_id),
                "leg_a_opp_token_id": str(opp_token_id),
                "leg_a_label": str(display_label)[:64],
                "leg_a_side": str(side_label),
                "leg_a_market_id": str(market_id),
                "leg_a_condition_id": str(condition_id),
                "leg_a_fee_rate": float(cand.get("leg_a_market_fee_rate") or cand.get("leg_a_fee_rate") or 0.0),
                "leg_a_fee_exponent": float(cand.get("leg_a_fee_exponent") or 1.0),
                "leg_a_neg_risk": bool(neg_risk),
                "leg_a_expiry_ts": float(close_ts),
                "ws_books": cand.get("ws_books"),
                "ws_books_ts": round(now_ts, 3),
            }
            if str(event_id or "").strip():
                _w_mkr_cand["event_id"] = str(event_id).strip()
            if isinstance(bk_win.get("_s2_meta"), Mapping):
                _w_mkr_cand.update(bk_win["_s2_meta"])
            _write_and_notify_live_cand(daemon, _w_mkr_cand, cand_file, default_cand_path)
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
    event_id: str = "",
    pair_dedupe_key: str = "",
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


UMA_EXEMPT_EXPIRY_SLEEVES = frozenset({
    "BOND1_UMA_RESOLUTION_CARRY",
    "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
})

PRE_PROPOSAL_CARRY_SLEEVES = frozenset({
    "W_PRUNE1_DEAD_NO_BOND",
    "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
    "MKR_REWARD_LOCKED_CARRY",
    "UMA_READY1_LIVENESS_PRIORITY",
})


def is_sll_pre_expiry_exempt(sleeve_src: str, posted_px: Optional[float] = None) -> bool:
    """
    Exempts deterministic locked carry Maker orders from the legacy `<= 60s` pre-expiry self-cancel
    right when terminal exit flow peaks, while still canceling low-price (`< $0.990`) `MKR_LOCK1` quotes.
    """
    sl_u = str(sleeve_src or "").upper()
    if sl_u in UMA_EXEMPT_EXPIRY_SLEEVES:
        return True
    if sl_u in {"W_PRUNE1_DEAD_NO_BOND", "MKR_REWARD_LOCKED_CARRY", "UMA_READY1_LIVENESS_PRIORITY"}:
        return True
    if sl_u == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER" and posted_px is not None and float(posted_px) >= 0.990 - 1e-9:
        return True
    return False


def sll_settlement_lag_floor_hours(sleeve_src: str) -> float:
    sl_u = str(sleeve_src or "").upper()
    if sl_u in FAST_GUN_S2_SLEEVES:
        return 0.02
    if sl_u in UMA_EXEMPT_EXPIRY_SLEEVES:
        return 0.25
    if sl_u in PRE_PROPOSAL_CARRY_SLEEVES:
        return 1.50
    return 0.50


def select_sll_velocity_preempt_target(
    harvester: Any,
    cand_edge_hr: float,
    is_s2_mkr: bool = False,
    vel_mult: float = 1.80,
    now_pe: Optional[float] = None,
    *,
    cand_sleeve: str = "",
) -> Tuple[float, str]:
    cand_sl_u = str(cand_sleeve or "").upper()
    if cand_sl_u in FAST_GUN_S2_SLEEVES:
        return 0.0, ""
    pe_map = getattr(harvester, "_maker_anchor_preempt_events", None) or {}
    claimed_pe = harvester.__dict__.setdefault("_claimed_velocity_preempts", set())
    now_t = float(now_pe if now_pe is not None else time.time())
    from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

    sticky_fifo_sec = float(
        GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("sll_sticky_fifo_rank1_min_hold_sec", 900.0)
    )

    def _it_edge_hr(it: Mapping[str, Any]) -> float:
        ib = float(it.get("anchor_bid_px") or 0.0)
        ie = float(it.get("expiry_ts") or 0.0)
        sl_it = str(it.get("sleeve_source") or "")
        fl_h = sll_settlement_lag_floor_hours(sl_it)
        if 0.0 < ib < 1.0 and ie > now_t:
            return round(((1.0 - ib) * 10000.0) / max(fl_h, (ie - now_t) / 3600.0), 2)
        if 0.0 < ib < 1.0 and fl_h > 0.0:
            return round(((1.0 - ib) * 10000.0) / fl_h, 2)
        return float(it.get("velocity_bps_hr") or 0.0)

    def _req_age_s(iv: float, sl_it: str = "", fifo_rank1: bool = False) -> float:
        if is_s2_mkr and not cand_sl_u:
            return 20.0
        if fifo_rank1 and float(cand_edge_hr) < max(iv * 8.0, iv + 400.0):
            return max(180.0, sticky_fifo_sec)
        if iv <= 35.0 and float(cand_edge_hr) >= max(iv * 8.0, iv + 200.0):
            return 30.0
        if sl_it != "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER" and float(cand_edge_hr) >= max(iv * 5.0, iv + 250.0):
            return 45.0
        return 180.0

    slow_cands = []
    rw_cands = []
    tot_rw_slots = sum(
        1
        for p in (getattr(harvester, "active_positions", None) or {}).values()
        if isinstance(p, Mapping)
        and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
        and str(p.get("sleeve") or p.get("sleeve_source") or "").upper() == "MKR_REWARD_LOCKED_CARRY"
    )
    bond1_slots = sum(
        1
        for p in (getattr(harvester, "active_positions", None) or {}).values()
        if isinstance(p, Mapping)
        and str(p.get("status") or "") != "AWAITING_ONCHAIN_SETTLEMENT"
        and str(p.get("sleeve") or p.get("sleeve_source") or "").upper() == "BOND1_UMA_RESOLUTION_CARRY"
    )
    _seller_flow_sl = {"BOND1_UMA_RESOLUTION_CARRY", "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "W_PRUNE1_DEAD_NO_BOND"}
    for it in getattr(harvester, "pending_entry_intents", {}).values():
        if isinstance(it, Mapping) and it.get("live_maker_anchor_inflight"):
            _isl = str(it.get("sleeve_source") or "").upper()
            if _isl == "MKR_REWARD_LOCKED_CARRY":
                tot_rw_slots += 1
            elif _isl == "BOND1_UMA_RESOLUTION_CARRY":
                bond1_slots += 1
        if not (
            isinstance(it, Mapping)
            and it.get("live_maker_anchor_inflight")
            and str(it.get("inflight_key") or "") not in claimed_pe
            and str(it.get("sleeve_source") or "") not in FAST_GUN_S2_SLEEVES
        ):
            continue
        iv = _it_edge_hr(it)
        age_i = now_t - float(it.get("ts") or 0.0)
        ik = str(it.get("inflight_key") or "")
        sl_i_u = str(it.get("sleeve_source") or "").upper()
        is_fifo_r1 = bool(it.get("fifo_rank1_verified"))
        if sl_i_u == "MKR_REWARD_LOCKED_CARRY" and cand_sl_u in _seller_flow_sl and age_i >= (sticky_fifo_sec if is_fifo_r1 else 45.0):
            rw_cands.append((iv, ik))
        if age_i >= _req_age_s(iv, sl_i_u, fifo_rank1=is_fifo_r1):
            slow_cands.append((iv, ik))
    if rw_cands:
        rw_vel, rw_k = min(rw_cands, key=lambda x: x[0])
        rw_protect = (tot_rw_slots <= 1 and cand_sl_u == "BOND1_UMA_RESOLUTION_CARRY" and bond1_slots >= 2)
        rw_req = max(rw_vel * 3.0, 150.0) if rw_protect else max(rw_vel * 1.15, 35.0)
        if rw_k and rw_k in pe_map and float(cand_edge_hr) >= rw_req:
            return rw_vel, rw_k
    if not slow_cands:
        return 0.0, ""
    slow_vel, slow_k = min(slow_cands, key=lambda x: x[0])
    req_mult = max(3.0, float(vel_mult or 0.0))
    if slow_k and slow_k in pe_map and float(cand_edge_hr) >= max(slow_vel * req_mult, slow_vel + 50.0):
        return slow_vel, slow_k
    return 0.0, ""


async def maybe_preempt_mlk1_if_bond1_starved(
    harvester: Any,
    sleeve_src: str,
    budget: float,
    collat: float,
    own_mkr_grad: bool,
    enforce_b1_v53: bool,
    b1_gov: Mapping[str, Any],
    rcfg_sll: Mapping[str, Any],
    gsn_s: Mapping[str, Any],
    open_mid_u: float,
    rem_tte_sec: float,
    now_ts: float,
    per_mkt_cap_u: float = 0.0,
    *,
    cand_bid_px: float = 0.0,
) -> float:
    """
    Starvation-only post-validation `BOND1 -> MKR_LOCK1` upgrade:
      - Runs strictly AFTER all dedupe, cooldown, market-occupied, TTE, and `RESTING_BID_OUT_OF_BAND` checks.
      - On live Gatling wallets (`enforce_b1_v53=True`), NEVER cancels resting `MKR_LOCK1` when free cash
        already covers a viable `BOND1` clip (`budget >= $12.00`), when `BOND1` already holds `>= 45%` of
        wallet equity, or when the incoming `BOND1` candidate has lower capital velocity (`< 1.25x`) than
        the resting `MKR_LOCK1` order (e.g., `$0.992` `64 bps/hr` `BOND1` vs `$0.965` `798 bps/hr` `Heat`)!
    """
    if (
        str(sleeve_src or "") != "BOND1_UMA_RESOLUTION_CARRY"
        or getattr(harvester, "dry_run", True)
        or not hasattr(harvester, "_is_v5_unleashed_active")
        or not bool(harvester._is_v5_unleashed_active())
    ):
        return float(budget)
    pe_map = getattr(harvester, "_maker_anchor_preempt_events", None) or {}
    cand_vel_bps = (
        round(((1.0 - float(cand_bid_px)) * 10000.0) / max(sll_settlement_lag_floor_hours(sleeve_src), max(0.0, float(rem_tte_sec)) / 3600.0), 2)
        if 0.0 < float(cand_bid_px) < 1.0
        else 0.0
    )

    def _mlk_vel_bps(it: Mapping[str, Any]) -> float:
        ib = float(it.get("anchor_bid_px") or 0.0)
        ie = float(it.get("expiry_ts") or 0.0)
        fl_m = sll_settlement_lag_floor_hours("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")
        if 0.0 < ib < 1.0:
            rem_h = max(fl_m, (ie - float(now_ts)) / 3600.0) if ie > float(now_ts) else fl_m
            return round(((1.0 - ib) * 10000.0) / rem_h, 2)
        return float(it.get("velocity_bps_hr") or 0.0)

    claimed_pe = harvester.__dict__.setdefault("_claimed_velocity_preempts", set())
    sticky_fifo_sec = max(180.0, float(b1_gov.get("sll_sticky_fifo_rank1_min_hold_sec", 900.0) or 900.0))
    _raw_ttl_m = float(rcfg_sll.get("bond1_maker_ttl_sec", 1e9) or 1e9) if isinstance(rcfg_sll, Mapping) else 1e9
    birth_grace_sec = (
        min(max(0.0, float(b1_gov.get("sll_preempt_birth_grace_sec", 45.0) or 0.0)), max(0.0, _raw_ttl_m * 0.5))
        if enforce_b1_v53
        else 0.0
    )
    mlk_cands: list[tuple[float, str]] = []
    for it in getattr(harvester, "pending_entry_intents", {}).values():
        if (
            isinstance(it, Mapping)
            and str(it.get("sleeve_source") or "") == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"
        ):
            ik = str(it.get("inflight_key") or "")
            if not ik or ik not in pe_map or ik in claimed_pe:
                continue
            mv = _mlk_vel_bps(it)
            if cand_vel_bps > 0.0 and mv > 0.0 and cand_vel_bps < mv * 1.25:
                continue
            ts_it = float(it.get("ts") or 0.0)
            age_it = max(0.0, float(now_ts) - ts_it) if ts_it > 0.0 else 1e9
            if age_it < birth_grace_sec:
                continue
            if bool(it.get("fifo_rank1_verified")) and age_it < sticky_fifo_sec:
                if cand_vel_bps <= 0.0 or cand_vel_bps < max(mv * 8.0, mv + 400.0):
                    continue
            mlk_cands.append((mv, ik))
    if not mlk_cands:
        return float(budget)
    mlk_cands.sort(key=lambda t: (t[0], t[1]))
    mlk_keys = [ik for _, ik in mlk_cands]

    from src.polymarket_research.holistic_strategy_governance import get_unleashed_v5_tier_profile

    def _is_recv(p: Mapping[str, Any]) -> bool:
        return str(p.get("status") or "") == "AWAITING_ONCHAIN_SETTLEMENT"

    prepost_res = getattr(harvester, "_prepost_sll_reserved_usd", None) or {}
    act_non_recv = sum(
        float(p.get("notional_usd", 0.0) or 0.0)
        for p in getattr(harvester, "active_positions", {}).values()
        if isinstance(p, Mapping) and not _is_recv(p)
    )
    tot_eq = float(collat or 0.0) + act_non_recv + pending_intents_synced_equity_usd(getattr(harvester, "pending_entry_intents", None))
    if float(cand_bid_px or 0.0) > 0.0 and tot_eq > 0.0:
        bond1_used_u = sum(
            float(p.get("notional_usd", 0.0) or 0.0)
            for p in getattr(harvester, "active_positions", {}).values()
            if isinstance(p, Mapping)
            and not _is_recv(p)
            and str(p.get("sleeve") or p.get("sleeve_source") or "") == "BOND1_UMA_RESOLUTION_CARRY"
        ) + sum(
            max(0.0, float(it.get("notional_usd", 0.0) or 0.0)) + max(0.0, float(it.get("matched_notional_usd", 0.0) or 0.0))
            for it in getattr(harvester, "pending_entry_intents", {}).values()
            if isinstance(it, Mapping)
            and it.get("live_maker_anchor_inflight")
            and str(it.get("sleeve_source") or "") == "BOND1_UMA_RESOLUTION_CARRY"
        )
        if bond1_used_u >= tot_eq * 0.45:
            return float(budget)
    v5_p = get_unleashed_v5_tier_profile(tot_eq)
    sll_pct = float(v5_p["bond1_free_cash_pct"])
    _ex_h = getattr(harvester, "executor", None)
    _gat_active = bool(
        getattr(harvester, "enforce_gatling_sizing", False)
        or getattr(harvester, "enforce_gatling_fast_gun_reserve", False)
        or (
            not getattr(harvester, "dry_run", True)
            and getattr(_ex_h, "client", None) is not None
            and getattr(getattr(_ex_h, "client", None), "_mock_children", None) is None
            and "get_market_book" not in getattr(_ex_h, "__dict__", {})
            and not getattr(harvester, "enforce_bond1_smart_queue", False)
        )
    )
    _fanout_u = float(b1_gov.get("bond1_maker_fanout_clip_usd_seed") or 0.0) if _gat_active else 0.0
    if enforce_b1_v53:
        if float(budget) >= (5.0 if (_fanout_u > 0.0 and tot_eq < 150.0) else 12.0):
            return float(budget)
    else:
        target_unstarved = min(
            max(75.0, round(float(collat or 0.0) * sll_pct, 2)) if own_mkr_grad else float(v5_p["bridged_zero_fee_cap_usd"]),
            max(0.0, float(collat or 0.0) - float(v5_p["box_collateral_reserve_usd"])),
            float(collat or 0.0) * sll_pct,
        )
        if float(budget) >= max(0.0, target_unstarved - 2.0):
            return float(budget)

    if _fanout_u > 0.0 and tot_eq < 150.0:
        mlk_keys = mlk_keys[:1]
    mlk_set = set(mlk_keys)

    def _eval_post_evict_budget(intents_view: Any, excl_keys: Optional[Any] = None) -> float:
        inflight_u = pending_intents_cash_reserved_usd(intents_view) + sum(
            float(v or 0.0) for v in prepost_res.values()
        )
        collat_f = max(0.0, float(collat or 0.0) - inflight_u)
        cur_open_u = act_non_recv + inflight_u + pending_intents_synced_equity_usd(intents_view)
        tot_eq_sll = collat_f + cur_open_u
        v5_sll = get_unleashed_v5_tier_profile(tot_eq_sll)
        sll_pct_new = float(v5_sll["bond1_free_cash_pct"])
        zf_focus = _is_sll_zf_focus_enabled(harvester, enforce_b1_v53, gsn_s, tot_eq_sll)
        if zf_focus:
            sll_pct_new = max(sll_pct_new, float(b1_gov.get("seed_zero_loss_focus_bond1_pool_pct", 0.92) or 0.92))
        port_headroom_u = max(0.0, max(float(getattr(harvester, "max_exposure", 100.0)), tot_eq_sll * 0.96) - cur_open_u)
        lot_cap_sll = max(75.0, round(collat_f * sll_pct_new, 2)) if own_mkr_grad else float(v5_sll["bridged_zero_fee_cap_usd"])
        if enforce_b1_v53:
            sll_used_u = (
                sum(
                    float(p.get("notional_usd", 0.0) or 0.0)
                    for p in getattr(harvester, "active_positions", {}).values()
                    if isinstance(p, Mapping)
                    and not _is_recv(p)
                    and str(p.get("box_type") or "") in {"SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK"}
                )
                + pending_intents_cash_reserved_usd(intents_view, only_maker_anchor=True)
                + pending_intents_synced_equity_usd(intents_view)
                + sum(float(v or 0.0) for v in prepost_res.values())
            )
            sll_pool_rem = max(0.0, (collat_f + sll_used_u) * sll_pct_new - sll_used_u)
            mkt_cap_u = float(
                rcfg_sll.get("bond1_per_market_cap_usd")
                or v5_sll.get("bond1_maker_per_market_cap_usd", v5_sll.get("bond1_per_market_cap_usd", 25.0))
            )
            if zf_focus and not rcfg_sll.get("bond1_per_market_cap_usd"):
                mkt_cap_u = min(float(b1_gov.get("bond1_per_market_cap_usd_seed", 45.0)), max(mkt_cap_u, round((collat_f + sll_used_u) * 0.46, 2)))
            cand_b = min(
                lot_cap_sll,
                mkt_cap_u,
                sll_pool_rem,
                max(0.0, collat_f - float(v5_sll["box_collateral_reserve_usd"])),
                port_headroom_u,
            )
            cand_b = compute_sll_and_carry_gatling_budget(
                harvester,
                cand_b,
                collat_f,
                cur_open_u,
                "SINGLE_LEG_MAKER_LOCK",
                sleeve_src,
                own_mkr_grad,
                b1_gov,
                rem_tte_sec=rem_tte_sec,
                now_ts=now_ts,
                exclude_inflight_keys=excl_keys,
            )
            if _fanout_u > 0.0 and tot_eq_sll < 150.0:
                cand_b = min(cand_b, _fanout_u)
        else:
            cand_b = min(
                lot_cap_sll,
                max(0.0, collat_f - float(v5_sll["box_collateral_reserve_usd"])),
                collat_f * sll_pct_new,
                port_headroom_u,
            )
        if open_mid_u > 0.0 and per_mkt_cap_u > 0.0:
            cand_b = min(cand_b, max(0.0, per_mkt_cap_u - open_mid_u))
        return float(cand_b)

    raw_intents_pre = getattr(harvester, "pending_entry_intents", None)
    sim_intents = (
        {
            k: v
            for k, v in raw_intents_pre.items()
            if not (isinstance(v, Mapping) and str(v.get("inflight_key") or "") in mlk_set)
        }
        if isinstance(raw_intents_pre, Mapping)
        else raw_intents_pre
    )
    proj_b = _eval_post_evict_budget(sim_intents, mlk_set)
    eff_px = float(cand_bid_px) if 0.0 < float(cand_bid_px or 0.0) <= 1.0 else 0.995
    if int(math.floor(proj_b / eff_px)) < 5 or proj_b <= float(budget) + 1e-6:
        return float(budget)

    claimed_pe.update(mlk_set)
    try:
        pe_reasons = harvester.__dict__.setdefault("_maker_anchor_preempt_reasons", {})
        for mk in mlk_keys:
            pe_reasons[mk] = "BOND1_MAKER_PREEMPTED"
            pe_map[mk].set()
        for _ in range(20):
            await asyncio.sleep(0.03)
            if not any(
                isinstance(it, Mapping) and str(it.get("inflight_key") or "") in mlk_set
                for it in getattr(harvester, "pending_entry_intents", {}).values()
            ):
                break
    finally:
        claimed_pe.difference_update(mlk_set)

    return _eval_post_evict_budget(getattr(harvester, "pending_entry_intents", None))


def pending_intents_cash_reserved_usd(intents: Any, *, only_maker_anchor: bool = False) -> float:
    if not isinstance(intents, Mapping):
        return 0.0
    tot = 0.0
    for it in intents.values():
        if not isinstance(it, Mapping):
            continue
        if only_maker_anchor and not it.get("live_maker_anchor_inflight"):
            continue
        unfilled = max(0.0, float(it.get("notional_usd", 0.0) or 0.0))
        matched = max(0.0, float(it.get("matched_notional_usd", 0.0) or 0.0))
        synced = min(matched, max(0.0, float(it.get("collat_drop_usd", 0.0) or 0.0)))
        tot += unfilled + max(0.0, matched - synced)
    return round(tot, 4)


def pending_intents_synced_equity_usd(intents: Any) -> float:
    if not isinstance(intents, Mapping):
        return 0.0
    tot = 0.0
    for it in intents.values():
        if not isinstance(it, Mapping) or not it.get("live_maker_anchor_inflight"):
            continue
        matched = max(0.0, float(it.get("matched_notional_usd", 0.0) or 0.0))
        drop_u = max(0.0, float(it.get("collat_drop_usd", 0.0) or 0.0))
        posted_cap = max(matched, float(it.get("posted_notional_usd", 0.0) or 0.0))
        # `drop_u` is actual wallet cash already deducted on-chain while resting; clamp to `posted_cap`
        # so equity stays invariant even during the sub-poll window before `matched_notional_usd` catches up.
        tot += min(posted_cap, drop_u) if drop_u > 0.0 else 0.0
    return round(tot, 4)


_COLLAT_SURPLUS_GRACE_SEC: float = 25.0


def rebalance_pending_intent_collat_drops(intents: Any, *, now_ts: Optional[float] = None) -> None:
    if not isinstance(intents, Mapping):
        return
    mkr_items = [it for it in intents.values() if isinstance(it, dict) and it.get("live_maker_anchor_inflight")]
    if not mkr_items:
        return
    surplus = 0.0
    for it in mkr_items:
        matched = max(0.0, float(it.get("matched_notional_usd", 0.0) or 0.0))
        drop_u = max(0.0, float(it.get("collat_drop_usd", 0.0) or 0.0))
        if drop_u > matched + 1e-6:
            surp_ts = float(it.get("_collat_surplus_ts") or it.get("ts") or 0.0)
            if now_ts is not None and surp_ts > 0.0 and (float(now_ts) - surp_ts) >= _COLLAT_SURPLUS_GRACE_SEC:
                # Order poll confirmed `matched` is still below `drop_u` past the RPC-first race grace window;
                # discard phantom collateral drop (caused by unrelated taker fill / settlement) instead of keeping it.
                it["collat_drop_usd"] = round(matched, 4)
                it.pop("_collat_surplus_ts", None)
                continue
            surplus += drop_u - matched
            it["collat_drop_usd"] = round(matched, 4)
        else:
            it.pop("_collat_surplus_ts", None)
    if surplus <= 1e-6:
        return
    for it in mkr_items:
        if surplus <= 1e-6:
            break
        matched = max(0.0, float(it.get("matched_notional_usd", 0.0) or 0.0))
        drop_u = max(0.0, float(it.get("collat_drop_usd", 0.0) or 0.0))
        need = max(0.0, matched - drop_u)
        if need > 1e-6:
            add_u = min(need, surplus)
            it["collat_drop_usd"] = round(drop_u + add_u, 4)
            surplus -= add_u
    if surplus > 1e-6:
        stamp_ts = float(now_ts) if now_ts is not None else time.time()
        for it in mkr_items:
            if surplus <= 1e-6:
                break
            drop_u = max(0.0, float(it.get("collat_drop_usd", 0.0) or 0.0))
            cap_u = max(drop_u, float(it.get("posted_notional_usd", 0.0) or 0.0))
            room = max(0.0, cap_u - drop_u)
            if room > 1e-6:
                add_u = min(room, surplus)
                it["collat_drop_usd"] = round(drop_u + add_u, 4)
                it.setdefault("_collat_surplus_ts", stamp_ts)
                surplus -= add_u


def sync_pending_intents_on_collateral_refresh(
    harvester: Any, prev_bal: Optional[float], new_bal: Optional[float]
) -> bool:
    intents = getattr(harvester, "pending_entry_intents", None)
    if not isinstance(intents, Mapping) or not intents:
        return False
    # Do not attribute collateral drops to passive maker intents while a fast directional/taker entry is mid-wire.
    if any(isinstance(v, Mapping) and not v.get("live_maker_anchor_inflight") for v in intents.values()):
        return False
    ex = getattr(harvester, "executor", None)
    uws = getattr(ex, "_user_ws_cache", None) if ex is not None else None
    if uws is not None and hasattr(uws, "get_order_snapshot"):
        for it in intents.values():
            if not isinstance(it, dict) or not it.get("live_maker_anchor_inflight"):
                continue
            oid = str(it.get("entry_order_id") or "").strip()
            p_sh = float(it.get("posted_shares", 0.0) or 0.0)
            p_px = float(it.get("anchor_bid_px", 0.0) or 0.0)
            if oid and p_sh > 0.0 and p_px > 0.0:
                snap = uws.get_order_snapshot(oid, max_age_sec=60.0)
                if isinstance(snap, Mapping):
                    m_ws = min(p_sh, max(0.0, float(snap.get("size_matched") or 0.0)))
                    if m_ws > 0.0:
                        it["notional_usd"] = round(max(0.0, p_sh - m_ws) * p_px, 4)
                        it["matched_notional_usd"] = round(m_ws * p_px, 4)
    if prev_bal is None or new_bal is None:
        rebalance_pending_intent_collat_drops(intents)
        return False
    rem_drop = max(0.0, float(prev_bal) - float(new_bal))
    changed = False
    now_sync = time.time()
    if rem_drop > 1e-6:
        for it in intents.values():
            if not isinstance(it, dict) or not it.get("live_maker_anchor_inflight") or rem_drop <= 1e-6:
                continue
            matched = max(0.0, float(it.get("matched_notional_usd", 0.0) or 0.0))
            drop_u = max(0.0, float(it.get("collat_drop_usd", 0.0) or 0.0))
            need = max(0.0, matched - drop_u)
            if need > 1e-6:
                add_u = min(need, rem_drop)
                it["collat_drop_usd"] = round(drop_u + add_u, 4)
                rem_drop -= add_u
                changed = True
        if rem_drop > 1e-6:
            for it in intents.values():
                if not isinstance(it, dict) or not it.get("live_maker_anchor_inflight") or rem_drop <= 1e-6:
                    continue
                drop_u = max(0.0, float(it.get("collat_drop_usd", 0.0) or 0.0))
                cap_u = max(drop_u, float(it.get("posted_notional_usd", 0.0) or 0.0))
                room = max(0.0, cap_u - drop_u)
                if room > 1e-6:
                    add_u = min(room, rem_drop)
                    it["collat_drop_usd"] = round(drop_u + add_u, 4)
                    it.setdefault("_collat_surplus_ts", now_sync)
                    rem_drop -= add_u
                    changed = True
    rebalance_pending_intent_collat_drops(intents)
    return changed


def update_sll_intent_partial_fill(
    intents: Any,
    intent_id: str,
    posted_sh: float,
    posted_px: float,
    matched_sh: float,
    now_ts: float,
    *,
    heartbeat_persist_sec: float = 30.0,
) -> bool:
    if not isinstance(intents, Mapping) or intent_id not in intents:
        return False
    it = intents[intent_id]
    if not isinstance(it, dict):
        return False
    m_clamped = min(max(0.0, float(matched_sh or 0.0)), max(0.0, float(posted_sh or 0.0)))
    unfilled_u = round(max(0.0, float(posted_sh) - m_clamped) * float(posted_px), 4)
    matched_u = round(m_clamped * float(posted_px), 4)
    prev_persisted_m = float(it.get("_persisted_matched_usd", 0.0) or 0.0)
    prev_drop = float(it.get("collat_drop_usd", 0.0) or 0.0)
    last_save_ts = float(it.get("_last_persist_ts", it.get("ts", 0.0)) or 0.0)
    it["notional_usd"] = unfilled_u
    it["matched_notional_usd"] = matched_u
    it["heartbeat_ts"] = now_ts
    rebalance_pending_intent_collat_drops(intents, now_ts=now_ts)
    new_drop = float(it.get("collat_drop_usd", 0.0) or 0.0)
    if (
        abs(matched_u - prev_persisted_m) >= 0.01
        or abs(new_drop - prev_drop) >= 0.01
        or (now_ts - last_save_ts) >= heartbeat_persist_sec
    ):
        it["_persisted_matched_usd"] = matched_u
        it["_last_persist_ts"] = now_ts
        return True
    return False


def release_sll_pending_intent(
    intents: Any, intent_id: str, final_matched_usd: float = 0.0
) -> Optional[Dict[str, Any]]:
    if not isinstance(intents, dict):
        return None
    popped = intents.pop(intent_id, None)
    if not isinstance(popped, dict):
        return None
    drop_u = max(0.0, float(popped.get("collat_drop_usd", 0.0) or 0.0))
    used_drop = min(drop_u, max(0.0, float(final_matched_usd or 0.0)))
    popped["collat_drop_usd"] = round(used_drop, 4)
    leftover = max(0.0, drop_u - used_drop)
    surp_ts = float(popped.get("_collat_surplus_ts") or popped.get("ts") or 0.0)
    within_grace = surp_ts > 0.0 and (time.time() - surp_ts) < _COLLAT_SURPLUS_GRACE_SEC
    if leftover > 1e-6 and intents and within_grace:
        for it in intents.values():
            if not isinstance(it, dict) or not it.get("live_maker_anchor_inflight") or leftover <= 1e-6:
                continue
            cur_d = max(0.0, float(it.get("collat_drop_usd", 0.0) or 0.0))
            cap_u = max(cur_d, float(it.get("posted_notional_usd", 0.0) or 0.0))
            add_u = min(max(0.0, cap_u - cur_d), leftover)
            if add_u > 1e-6:
                it["collat_drop_usd"] = round(cur_d + add_u, 4)
                it.setdefault("_collat_surplus_ts", surp_ts)
                leftover -= add_u
        rebalance_pending_intent_collat_drops(intents)
    return popped


def debit_sll_collateral_after_fill(
    harvester: Any,
    saved_intent: Optional[Mapping[str, Any]],
    total_debit_usd: float,
    now_ts: float,
) -> None:
    cur_c = getattr(harvester, "_last_known_collateral", None)
    if cur_c is None:
        return
    already_debited_u = min(
        max(0.0, float(total_debit_usd or 0.0)),
        max(0.0, float((saved_intent or {}).get("collat_drop_usd", 0.0) or 0.0)),
    )
    rem_debit = max(0.0, float(total_debit_usd or 0.0) - already_debited_u)
    harvester._last_known_collateral = max(0.0, float(cur_c) - rem_debit)
    harvester._last_entry_debit_window = (now_ts, float(harvester._last_known_collateral))


def _is_sll_zf_focus_enabled(
    harvester: Any,
    enforce_b1_v53: bool,
    gsn_s: Mapping[str, Any],
    tot_eq_sll: float,
) -> bool:
    if not enforce_b1_v53:
        return False
    min_dir_eq = float((gsn_s.get("directional") or {}).get("min_live_equity_for_unhedged_directional_usd", 0.0) or 0.0)
    if not (bool((gsn_s.get("directional") or {}).get("riskless_only_mode", False)) or (min_dir_eq > 0.0 and tot_eq_sll < min_dir_eq)):
        return False
    explicit = getattr(harvester, "enforce_seed_zero_loss_focus", None)
    if explicit is not None:
        return bool(explicit)
    ex = getattr(harvester, "executor", None)
    if "post_maker_entry_order" in getattr(ex, "__dict__", {}):
        return False
    if (
        getattr(harvester, "enforce_gatling_fast_gun_reserve", False)
        and not getattr(harvester, "enforce_gatling_sizing", False)
        and getattr(ex, "client", None) is None
    ):
        return False
    return True


def compute_sll_entry_budget(
    harvester: Any,
    sleeve_src: str,
    mid_a: str,
    collat: Optional[float],
    own_mkr_grad: bool,
    enforce_b1_v53: bool,
    b1_gov: Mapping[str, Any],
    rcfg_sll: Mapping[str, Any],
    gsn_s: Mapping[str, Any],
    rem_tte_sec: float,
    now_ts: float,
    *,
    post_vel_preempt: bool = False,
    exclude_inflight_key: str = "",
) -> Tuple[float, float, float]:
    """Returns `(budget, open_mid_u, sll_pct)` preserving 100% of v5.3 SLL & Gatling sizing rules."""
    dry_run = bool(getattr(harvester, "dry_run", True))
    is_mlk1 = sleeve_src == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"
    is_rw_carry = sleeve_src == "MKR_REWARD_LOCKED_CARRY"
    prepost_res = getattr(harvester, "_prepost_sll_reserved_usd", None) or {}
    raw_intents = getattr(harvester, "pending_entry_intents", None)
    intents = (
        {k: v for k, v in raw_intents.items() if not (isinstance(v, Mapping) and v.get("inflight_key") == exclude_inflight_key)}
        if (exclude_inflight_key and isinstance(raw_intents, Mapping))
        else raw_intents
    )
    inflight_u = pending_intents_cash_reserved_usd(intents) + sum(float(v or 0.0) for v in prepost_res.values())
    synced_eq_u = pending_intents_synced_equity_usd(intents)
    collat_f = 100.0 if dry_run else max(0.0, float(collat or 0.0) - inflight_u)

    def _is_recv(p: Mapping[str, Any]) -> bool:
        return str(p.get("status") or "") == "AWAITING_ONCHAIN_SETTLEMENT"

    cur_open_u = (
        sum(
            float(p.get("notional_usd", 0.0) or 0.0)
            for p in (getattr(harvester, "active_positions", None) or {}).values()
            if isinstance(p, Mapping) and not _is_recv(p)
        )
        + inflight_u
        + synced_eq_u
    )
    sll_pct = 0.25
    if bool(harvester._is_v5_unleashed_active()):
        from src.polymarket_research.holistic_strategy_governance import get_unleashed_v5_tier_profile

        tot_eq_sll = collat_f + cur_open_u
        v5_sll = get_unleashed_v5_tier_profile(tot_eq_sll)
        sll_pct = float(v5_sll["bond1_free_cash_pct"])
        zf_focus = _is_sll_zf_focus_enabled(harvester, enforce_b1_v53, gsn_s, tot_eq_sll)
        if zf_focus:
            _frozen_uma_sll = sum(
                float(p.get("notional_usd", 0.0) or 0.0)
                for p in (getattr(harvester, "active_positions", None) or {}).values()
                if isinstance(p, Mapping) and not _is_recv(p) and is_post_expiry_uma_frozen_lock(p, now_ts)
            )
            _cfg_pool_pct = float(b1_gov.get("seed_zero_loss_focus_bond1_pool_pct", 0.80) or 0.80)
            sll_pct = max(sll_pct, max(0.92, _cfg_pool_pct) if _frozen_uma_sll >= 15.0 else _cfg_pool_pct)
        port_headroom_u = max(0.0, max(float(getattr(harvester, "max_exposure", 100.0)), tot_eq_sll * 0.96) - cur_open_u)
        lot_cap_sll = max(75.0, round(collat_f * sll_pct, 2)) if own_mkr_grad else float(v5_sll["bridged_zero_fee_cap_usd"])
        if enforce_b1_v53:
            sll_used_u = (
                sum(
                    float(p.get("notional_usd", 0.0) or 0.0)
                    for p in (getattr(harvester, "active_positions", None) or {}).values()
                    if isinstance(p, Mapping)
                    and not _is_recv(p)
                    and not is_post_expiry_uma_frozen_lock(p, now_ts)
                    and str(p.get("box_type") or "") in {"SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK"}
                )
                + pending_intents_cash_reserved_usd(intents, only_maker_anchor=True)
                + synced_eq_u
                + sum(float(v or 0.0) for v in prepost_res.values())
            )
            sll_pool_rem = max(0.0, (collat_f + sll_used_u) * sll_pct - sll_used_u)
            mkt_cap_u = float(
                rcfg_sll.get("bond1_per_market_cap_usd")
                or v5_sll.get("bond1_maker_per_market_cap_usd", v5_sll.get("bond1_per_market_cap_usd", 25.0))
            )
            if zf_focus and not rcfg_sll.get("bond1_per_market_cap_usd"):
                mkt_cap_u = min(float(b1_gov.get("bond1_per_market_cap_usd_seed", 45.0)), max(mkt_cap_u, round((collat_f + sll_used_u) * 0.46, 2)))
            budget = min(
                lot_cap_sll,
                mkt_cap_u,
                sll_pool_rem,
                collat_f if post_vel_preempt else max(0.0, collat_f - float(v5_sll["box_collateral_reserve_usd"])),
                collat_f if post_vel_preempt else port_headroom_u,
            )
            budget = compute_sll_and_carry_gatling_budget(
                harvester,
                budget,
                collat_f,
                cur_open_u,
                "SINGLE_LEG_MAKER_LOCK",
                sleeve_src,
                own_mkr_grad,
                b1_gov,
                rem_tte_sec=rem_tte_sec,
                now_ts=now_ts,
                exclude_inflight_key=exclude_inflight_key,
                post_vel_preempt=post_vel_preempt,
            )
        else:
            budget = min(
                lot_cap_sll,
                collat_f if post_vel_preempt else max(0.0, collat_f - float(v5_sll["box_collateral_reserve_usd"])),
                collat_f * sll_pct,
                collat_f if post_vel_preempt else port_headroom_u,
            )
    else:
        port_headroom_u = 100.0 if dry_run else max(0.0, max(float(getattr(harvester, "max_exposure", 100.0)), collat_f * 0.55) - cur_open_u)
        lot_cap_sll = 24.0 if own_mkr_grad else 16.50
        budget = min(
            lot_cap_sll,
            max(0.0, collat_f - float(rcfg_sll.get("d1_box_collateral_reserve_usd", 16.50))),
            collat_f * 0.25,
            port_headroom_u,
        )
    open_mid_u = open_market_notional_usd(harvester, [mid_a])
    if open_mid_u > 0.0:
        budget = min(budget, max(0.0, compute_d1_per_market_notional_cap(harvester) - open_mid_u))
    if is_mlk1 and not dry_run:
        budget = min(budget, 22.0, round((collat_f + cur_open_u) * 0.32, 2))
    if is_rw_carry and not dry_run:
        dyn_rw = compute_dynamic_riskless_tier_caps(collat_f + cur_open_u, b1_gov)
        budget = min(budget, float(dyn_rw["reward_harvester_cap_usd"]))
    return float(budget), float(open_mid_u), float(sll_pct)


def sll_repost_expiry_and_ok(
    sleeve_src: str,
    exp_ts: float,
    now_ts: float,
    min_rem_sec: float = 120.0,
    *,
    first_post_ts: Optional[float] = None,
    uws_ok: bool = True,
    rcfg: Optional[Mapping[str, Any]] = None,
) -> Tuple[bool, float]:
    sl_u = str(sleeve_src or "").upper()
    uma_ex = sl_u in UMA_EXEMPT_EXPIRY_SLEEVES
    exp_f = float(exp_ts or 0.0)
    if not uma_ex and exp_f > 0.0 and (exp_f - now_ts) < min_rem_sec:
        return False, exp_f
    if first_post_ts is not None:
        cfg = rcfg or {}
        short_caps = [
            float(v)
            for v in (cfg.get("bond1_maker_ttl_sec"), cfg.get("bond1_maker_max_keep_sec"))
            if v is not None and 0.0 < float(v) < 90.0
        ]
        tot_cap = min(short_caps) if short_caps else (7200.0 if uws_ok else 300.0)
        if (tot_cap - max(0.0, now_ts - float(first_post_ts))) < min(30.0, tot_cap * 0.15):
            return False, exp_f
    next_exp = max(exp_f, now_ts + 900.0) if (uma_ex and exp_f > 0.0) else exp_f
    return True, next_exp


def compute_sll_maker_keep_and_renew(
    sleeve_src: str,
    *,
    uws_ok: bool = True,
    exp_ts: float = 0.0,
    now_ts: Optional[float] = None,
    created_mono: float = 0.0,
    now_mono: Optional[float] = None,
    deadline_mono: Optional[float] = None,
    posted_px: float = 0.0,
    cur_best_bid: Optional[float] = None,
    buried_since_mono: Optional[float] = None,
    rcfg: Optional[Mapping[str, Any]] = None,
    first_post_elapsed_s: float = 0.0,
) -> Tuple[float, float, bool]:
    """
    Computes `(max_keep_s, updated_deadline_mono, cancel_near_expiry)` for passive single-leg Maker orders:
      - `S2`: `max_keep_s = min(35.0, max(6.0, exp_ts - now_ts - 4.0))`; self-cancels when `(exp_ts - now_ts) <= 1.5s`.
      - Passive carries (`BOND1`, `BOND2`, `W_PRUNE1`, `MKR_LOCK1`, `MKR_REWARD_LOCKED_CARRY`, `UMA_READY1`):
        initial `max_keep_s = 1800.0` when `uws_ok` (`300.0` fallback if `not uws_ok`, honoring `<90s` test overrides),
        bounded by remaining `7200.0s - first_post_elapsed_s` total lifetime so a repeg after `>=1800s` never self-cancels
        in `50ms`. While resting at `#1` top-of-book (`cur_best_bid <= posted_px + 1e-6` and `buried_since_mono is None`),
        auto-renews `deadline_mono = min(origin_mono + 7200.0, max(deadline_mono, now_mono + 900.0))`.
      - `BOND1` / `BOND2` are exempt from the `(exp_ts - now_ts) <= 60.0s` pre-expiry self-cancel.
    """
    sl_u = str(sleeve_src or "").upper()
    is_s2 = sl_u in FAST_GUN_S2_SLEEVES
    now_f = float(time.time() if now_ts is None else now_ts)
    exp_f = float(exp_ts or 0.0)
    c_m = float(created_mono or 0.0)
    n_m = float(c_m if now_mono is None else now_mono)
    el_s = max(0.0, float(first_post_elapsed_s or 0.0))
    origin_m = c_m - el_s
    cfg = rcfg or {}
    short_caps = [
        float(v)
        for v in (cfg.get("bond1_maker_ttl_sec"), cfg.get("bond1_maker_max_keep_sec"))
        if v is not None and 0.0 < float(v) < 90.0
    ]
    test_short_ttl = bool(short_caps)

    if is_s2:
        max_keep_s = min(35.0, max(6.0, exp_f - now_f - 4.0)) if exp_f > 0.0 else 15.0
        tot_cap_s = max_keep_s
    elif test_short_ttl:
        tot_cap_s = min(short_caps)
        max_keep_s = max(0.05, tot_cap_s - el_s)
    else:
        base_keep_s = 1800.0 if uws_ok else 300.0
        tot_cap_s = 7200.0 if uws_ok else 300.0
        max_keep_s = min(base_keep_s, max(0.05, tot_cap_s - el_s))

    dl = (c_m + max_keep_s) if (deadline_mono is None or float(deadline_mono) <= 0.0) else float(deadline_mono)
    if (
        not is_s2
        and not test_short_ttl
        and uws_ok
        and cur_best_bid is not None
        and float(posted_px) > 0.0
        and buried_since_mono is None
        and float(cur_best_bid) <= float(posted_px) + 1e-6
    ):
        dl = min(origin_m + tot_cap_s, max(dl, n_m + 900.0))

    if exp_f <= 0.0:
        cancel_near_exp = False
    elif is_s2:
        cancel_near_exp = (exp_f - now_f) <= 1.5
    elif is_sll_pre_expiry_exempt(sl_u, posted_px):
        cancel_near_exp = False
    else:
        cancel_near_exp = (exp_f - now_f) <= 60.0
    return max_keep_s, dl, cancel_near_exp


def extract_top_bid_from_book(bk_wc: Any) -> Optional[float]:
    if not isinstance(bk_wc, Mapping):
        return None
    bids = bk_wc.get("bids") or []
    best: Optional[float] = None
    for row in bids:
        try:
            px = float(row["price"] if isinstance(row, Mapping) else row[0])
            sz = float(row.get("size", 0.0) if isinstance(row, Mapping) else row[1])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if sz > 0.0 and (best is None or px > best):
            best = px
    return best


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
    best_bid_pre = max((px for px, _ in bids_wf), default=0.0)
    if any(
        abs(round(px * 100.0) - px * 100.0) > 1e-6
        and (best_bid_pre < 0.95 or px >= 0.95)
        for px, _ in (bids_wf + asks_wf)
    ):
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
            return f"BOND1_OUTBID_ABOVE_CAP:{best_bid_f:.4f}>{max_rb:.4f}", (180.0 if repost_n_in > 0 else 30.0), anc_bid_px, 0, tk_wf
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
    collat_usd: float = 75.0,
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
    opp_ceil_l = max(0.010, max_opp + 0.002)
    if (
        not is_s2_mkr
        and win_b_live < win_floor_l
        and opp_b_live <= opp_ceil_l
        and win_a_live >= win_floor_l
    ):
        # `/book` has only stale dust bids before our own `posted_px` propagated (or right on fill) with zero opposing bid pressure!
        win_b_live = max(win_b_live, posted_px)
    if win_b_live >= 0.95 and any(abs(round(px * 100.0) - px * 100.0) > 1e-6 and px >= 0.95 for px, _ in (bids_wc + asks_wc)):
        tk_wf = min(tk_wf, 0.001) if tk_wf > 0.0 else 0.001
    if opp_b_live > opp_ceil_l or win_b_live < win_floor_l:
        return "ADVERSE", None, buried_since_mono, f"opp_bid=${opp_b_live:.4f}, win_bid=${win_b_live:.4f}"
    if enforce_b1_v53:
        if win_b_live > posted_px + 1e-6:
            if isinstance(candidate_box, dict):
                candidate_box["_fifo_rank1_verified"] = False
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
            _uma_ex_l = is_sll_pre_expiry_exempt(str(candidate_box.get("sleeve_source") or ""), cand_rp)
            _max_rp = max(1, int(candidate_box.get("_max_outbid_repegs", 5))) if isinstance(candidate_box, Mapping) else 5
            _eff_max_rp = min(_max_rp, 2) if is_s2_mkr else _max_rp
            _min_tte_rp = 7.5 if is_s2_mkr else 150.0
            now_rp = time.time()
            _vel_rp_ok = True
            if not is_s2_mkr and exp_ts > 0.0 and (exp_ts - now_rp) > 900.0:
                from src.polymarket_research.holistic_strategy_governance import passes_capital_velocity_hurdle

                _vel_rp_ok, _ = passes_capital_velocity_hurdle(
                    box_type="SINGLE_LEG_MAKER_LOCK",
                    sleeve_src=str(candidate_box.get("sleeve_source") or ""),
                    collat_usd=max(25.0, float(collat_usd or 75.0)),
                    rem_tte_sec=max(900.0 if _uma_ex_l else 60.0, exp_ts - now_rp),
                    box_cost_net=cand_rp,
                    fast_recycle_eligible=bool(_uma_ex_l or cand_rp <= 0.995),
                )
            if (
                repost_n_in < _eff_max_rp
                and _vel_rp_ok
                and min_rb <= cand_rp <= max_rb
                and cand_rp >= round(win_b_live - 1e-9, 4)
                and cand_rp > posted_px + 1e-6
                and (abs(cand_rp - win_b_live) > 1e-6 or l1_q_l <= min(120.0, b1_q_cap) + 1e-6)
                and (_uma_ex_l or exp_ts <= 0.0 or (exp_ts - now_rp) >= _min_tte_rp)
            ):
                if isinstance(candidate_box, dict):
                    candidate_box["_init_l1_q_usd"] = None
                    candidate_box["_whale_q_since_mono"] = None
                return "REPEG", cand_rp, buried_since_mono, f"outbid (${win_b_live:.4f} > ${posted_px:.4f}); re-pegging -> ${cand_rp:.4f}"
            _shallow_two_sided_hold = bool(
                not is_s2_mkr
                and asks_wc
                and win_a_live < 1.0
                and (win_a_live - win_b_live) <= (2.0 * tb_l + 1e-6)
                and (win_b_live - posted_px) <= (2.0 * tb_l + 1e-6)
                and l1_q_l <= 80.0
            )
            eff_buried_s = max(float(b1_buried_s), 75.0) if _shallow_two_sided_hold else float(b1_buried_s)
            if buried_since_mono is None:
                buried_since_mono = time.monotonic()
            elif (time.monotonic() - buried_since_mono) >= eff_buried_s:
                return "BURIED", None, buried_since_mono, f"outbid at ${win_b_live:.4f} (posted ${posted_px:.4f}) >= {eff_buried_s:.0f}s"
        else:
            buried_since_mono = None
            if isinstance(candidate_box, dict) and abs(win_b_live - posted_px) <= 1e-6:
                l1_q_same = sum(px * sz for px, sz in bids_wc if abs(px - posted_px) <= 1e-6)
                init_q = candidate_box.get("_init_l1_q_usd")
                if init_q is None:
                    candidate_box["_init_l1_q_usd"] = float(l1_q_same)
                    init_q = float(l1_q_same)
                own_notional = float(candidate_box.get("_posted_notional_usd") or 8.0)
                ahead_q = max(0.0, min(float(init_q), float(l1_q_same)) - own_notional)
                candidate_box["_fifo_rank1_verified"] = bool(ahead_q <= 5.0)
                _subcent_b1 = (not is_s2_mkr) and (0.0001 <= tk_wf < 0.01)
                _q_step_need = (
                    (0.0001 <= tk_wf < 0.01 and ahead_q >= 25.0 and repost_n_in < 2)
                    if is_s2_mkr
                    else (
                        (ahead_q >= 75.0 and repost_n_in < 3)
                        if _subcent_b1
                        else (ahead_q >= max(250.0, float(b1_q_cap) * 1.25) and repost_n_in < 3)
                    )
                )
                _q_hold_s = 1.0 if is_s2_mkr else (5.0 if _subcent_b1 else 20.0)
                _q_min_tte = 7.5 if is_s2_mkr else 150.0
                if _q_step_need:
                    wq_mono = candidate_box.get("_whale_q_since_mono")
                    now_m = time.monotonic()
                    if wq_mono is None:
                        candidate_box["_whale_q_since_mono"] = now_m
                    elif (now_m - float(wq_mono)) >= _q_hold_s:
                        tb_w = max(0.001 if posted_px >= 0.96 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
                        ta_w = max(0.001 if win_a_live > 0.96 else 0.01, tk_wf if tk_wf >= 0.01 else 0.0)
                        step_w = round(posted_px + tb_w, 4)
                        ceil_w = min(
                            round(win_a_live - ta_w, 4),
                            max_rb,
                            round(
                                float(candidate_box.get("p_model") or 0.9985)
                                + max(0.0, float(candidate_box.get("maker_rebate_ps") or 0.0))
                                - float(candidate_box.get("min_maker_edge") or 0.004),
                                4,
                            ),
                        )
                        now_w = time.time()
                        _uma_ex_w = is_sll_pre_expiry_exempt(str(candidate_box.get("sleeve_source") or ""), step_w)
                        _vel_w_ok = True
                        if not is_s2_mkr and exp_ts > 0.0 and (exp_ts - now_w) > 900.0:
                            from src.polymarket_research.holistic_strategy_governance import passes_capital_velocity_hurdle

                            _vel_w_ok, _ = passes_capital_velocity_hurdle(
                                box_type="SINGLE_LEG_MAKER_LOCK",
                                sleeve_src=str(candidate_box.get("sleeve_source") or ""),
                                collat_usd=max(25.0, float(collat_usd or 75.0)),
                                rem_tte_sec=max(900.0 if _uma_ex_w else 60.0, exp_ts - now_w),
                                box_cost_net=step_w,
                                fast_recycle_eligible=bool(_uma_ex_w or step_w <= 0.995),
                            )
                        if (
                            _vel_w_ok
                            and min_rb <= step_w <= ceil_w
                            and (win_a_live - posted_px) >= (2.0 * tb_w - 1e-9)
                            and (_uma_ex_w or exp_ts <= 0.0 or (exp_ts - now_w) >= _q_min_tte)
                        ):
                            candidate_box["_whale_q_since_mono"] = None
                            candidate_box["_init_l1_q_usd"] = None
                            candidate_box["_fifo_rank1_verified"] = False
                            return "REPEG", step_w, buried_since_mono, f"whale_queue_ahead (${ahead_q:.0f} @ ${posted_px:.4f}); micro-stepping -> ${step_w:.4f}"
                else:
                    candidate_box["_whale_q_since_mono"] = None
    return "OK", None, buried_since_mono, ""


def prepare_sll_stalk_guard(
    harvester: Any,
    dedupe_k: str,
    candidate_box: Dict[str, Any],
    repost_n_in: int,
    posted_elapsed_s: float,
    default_max_repegs: int,
    b1_buried_s: float,
    now_ts: float,
    is_outbid_now: bool = False,
    buried_since_mono: Optional[float] = None,
) -> float:
    """Caps outbid repegs, shortens buried hold, and propagates <12s stalker strikes to sibling brackets of the same parent event."""
    stalk_map = getattr(harvester, "__dict__", {}).setdefault("_sll_stalk_strikes", {})
    evt_stalk_map = getattr(harvester, "__dict__", {}).setdefault("_sll_event_stalk_until", {})
    evt_k = extract_sll_event_group_key(candidate_box)
    prev_s, prev_t = stalk_map.get(dedupe_k, (0, 0.0)) if dedupe_k else (0, 0.0)
    active_strikes = prev_s if (now_ts - float(prev_t)) <= 1800.0 else 0
    if repost_n_in >= 1 and is_outbid_now and buried_since_mono is None and posted_elapsed_s < 12.0:
        candidate_box["_max_outbid_repegs"] = repost_n_in
        candidate_box["_fast_stalk_detected"] = True
        if evt_k and evt_k.startswith(("EVT:", "EVTMATCH:", "EVTWX:", "EVTLBL:", "EVTAST:")):
            evt_stalk_map[evt_k] = float(now_ts) + 300.0
    if evt_k and float(evt_stalk_map.get(evt_k, 0.0) or 0.0) > float(now_ts):
        candidate_box["_max_outbid_repegs"] = min(int(candidate_box.get("_max_outbid_repegs", default_max_repegs)), 1)
        return min(float(b1_buried_s), 10.0)
    if candidate_box.get("_fast_stalk_detected"):
        return min(float(b1_buried_s), 12.0)
    if active_strikes >= 1:
        candidate_box["_max_outbid_repegs"] = 1
        return min(float(b1_buried_s), 15.0)
    candidate_box.setdefault("_max_outbid_repegs", int(default_max_repegs))
    return float(b1_buried_s)


def record_sll_exit_cooldown(
    harvester: Any,
    dedupe_k: str,
    buried_cancelled: bool,
    adverse_cancelled: bool,
    is_s2_mkr: bool,
    repost_n_in: int,
    now_ts: float,
) -> float:
    """Computes post-cancel retry cooldown, escalating to 180s-720s on repeatedly outbid-buried markets."""
    if buried_cancelled and not is_s2_mkr and dedupe_k:
        stalk_map = getattr(harvester, "__dict__", {}).setdefault("_sll_stalk_strikes", {})
        prev_s, prev_t = stalk_map.get(dedupe_k, (0, 0.0))
        strikes = (int(prev_s) + 1) if (now_ts - float(prev_t)) <= 1800.0 else 1
        if repost_n_in >= 1:
            strikes = max(strikes, 2)
        if len(stalk_map) >= 512:
            expired_ks = [k for k, v in stalk_map.items() if (now_ts - float(v[1])) > 1800.0]
            for ek in expired_ks:
                stalk_map.pop(ek, None)
            if len(stalk_map) >= 512:
                for ek, _ in sorted(stalk_map.items(), key=lambda kv: float(kv[1][1]))[: len(stalk_map) - 384]:
                    stalk_map.pop(ek, None)
        stalk_map[dedupe_k] = (strikes, float(now_ts))
        if strikes <= 1 and repost_n_in == 0:
            return 45.0
        return float(min(720.0, 180.0 * (2 ** max(0, min(strikes - 2, 2)))))
    if buried_cancelled:
        return 45.0
    if adverse_cancelled:
        return 30.0
    return 2.0 if is_s2_mkr else 4.0


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
    _evt_k_box = extract_sll_event_group_key(cand)
    _evt_id_box = str(cand.get("event_id") or box_id)
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
        _fee_src_lg = "maker_post_only_0pct" if lg.get("is_maker_anchor") else resolve_canonical_fee_source(fr, slv_rec, str(cand.get("fee_source") or ""))
        leg_records.append((tid, {
            "trade_id": tid, "box_id": box_id, "box_expected_legs": 2, "box_partner_trade_id": partner_tid, "is_dominance_box": True, "is_locked_arbitrage_box": True,
            "hold_to_maturity_lock": d1_htm,
            "opp_token_id": str(cand.get(f"{pfx}_opp_token_id") or ""), "dedupe_key": str(cand.get("dedupe_key") or ""), "pair_dedupe_key": str(cand.get("pair_dedupe_key") or ""),
            "sleeve": slv_rec, "sleeve_source": str(cand.get("sleeve_source") or slv_rec),
            "entry_tte": max(1.0, leg_exp - now_ts), "event_id": _evt_id_box, "event_group_key": _evt_k_box,
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
            "entry_fee_asset": entry_fee_asset, "fee_source": _fee_src_lg,
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
        if len(leg_records) == 2:
            c0 = str(leg_records[0][1].get("condition_id") or "")
            c1 = str(leg_records[1][1].get("condition_id") or "")
            t0 = str(leg_records[0][1].get("token_id") or "")
            t1 = str(leg_records[1][1].get("token_id") or "")
            if c0 and c0 == c1 and t0 and t0 != t1:
                spawn_fast_c1_complete_set_merge_reconcile(harvester, box_id, [tid for tid, _ in leg_records])
    logger.info(
        f"✓ [D1 LIVE DOMINANCE BOX ENTERED] {box_id} ({asset_sym}) | {sh:.0f} pairs @ box_net=${box_unit:.4f} "
        f"(cost=${tot_box_cost:.2f}, min_floor=+${sh * max(0.0, 1.0 - box_unit):.2f})"
    )
    return [tid for tid, _ in leg_records]


_PURGED_GHOST_OIDS_CACHE: Dict[str, Set[str]] = {}


def _resolve_ghost_oids_path(executor: Any, explicit_path: Optional[Any] = None) -> Optional[Any]:
    from pathlib import Path as _Path

    p = explicit_path if explicit_path is not None else getattr(executor, "_purged_ghost_orders_file", None)
    if p is not None:
        return _Path(p) if p else None
    cl = getattr(executor, "client", None)
    if getattr(executor, "dry_run", True) or cl is None or getattr(cl, "_mock_children", None) is not None:
        return None
    return _Path(__file__).resolve().parents[2] / "data" / "polymarket" / "purged_clob_ghost_orders.json"


def _load_purged_ghost_oids(path_obj: Any) -> Set[str]:
    key = str(path_obj)
    cached = _PURGED_GHOST_OIDS_CACHE.get(key)
    if cached is not None:
        return cached
    loaded: Set[str] = set()
    try:
        if path_obj.exists():
            raw = json.loads(path_obj.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                loaded = {str(x).strip() for x in raw if str(x or "").strip()}
    except Exception:
        loaded = set()
    _PURGED_GHOST_OIDS_CACHE[key] = loaded
    return loaded


def record_purged_ghost_order(executor: Any, order_id: str, explicit_path: Optional[Any] = None) -> None:
    oid_s = str(order_id or "").strip()
    p = _resolve_ghost_oids_path(executor, explicit_path)
    if not oid_s or p is None:
        return
    oids = _load_purged_ghost_oids(p)
    if oid_s in oids:
        return
    oids.add(oid_s)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp_p = p.with_name(p.name + ".tmp")
        tmp_p.write_text(json.dumps(sorted(oids)[-500:], indent=2), encoding="utf-8")
        tmp_p.replace(p)
    except Exception:
        pass


def filter_purged_ghost_orders(executor: Any, orders: Sequence[Any], explicit_path: Optional[Any] = None) -> List[Any]:
    p = _resolve_ghost_oids_path(executor, explicit_path)
    if p is None or not orders:
        return list(orders or [])
    oids = _load_purged_ghost_oids(p)
    if not oids:
        return list(orders)
    return [
        o for o in orders
        if not (isinstance(o, Mapping) and str(o.get("id") or o.get("orderID") or "").strip() in oids)
    ]


def is_verified_zero_fill_cancel_purge(
    executor: Any,
    order_id: str,
    matched: float,
    not_canceled_reason: Optional[str],
    order_info: Optional[Mapping[str, Any]],
    *,
    token_id: Optional[str] = None,
    pre_token_balance: Optional[float] = None,
    market_closed: bool = False,
) -> bool:
    """
    Returns True ONLY when CLOB `cancel_order` returned a `not_canceled` purge message
    (`"already canceled or matched"` / `"market is closed"`) with `size_matched == 0` AND
    verified zero account fills for `order_id` AND zero ERC-1155 balance delta (when
    `pre_token_balance` is provided or market is still open). Stays fail-closed (`False`)
    if balance delta > 0, fills exist, or a required probe returns None.
    """
    nc_low = str(not_canceled_reason or "").lower()
    if (
        matched > 1e-6
        or bool((order_info or {}).get("associate_trades"))
        or ("already canceled or matched" not in nc_low and "market is closed" not in nc_low)
    ):
        return False
    is_mkt_closed = bool(market_closed or "market is closed" in nc_low)
    tok_c = str(token_id or (order_info or {}).get("asset_id") or (order_info or {}).get("token_id") or "").strip()
    if is_mkt_closed:
        if tok_c and hasattr(executor, "get_account_fills"):
            fills_mc = executor.get_account_fills(tok_c, 0.0, "BUY", str(order_id))
            if fills_mc is None or len(fills_mc) > 0:
                return False
        if tok_c and pre_token_balance is not None and hasattr(executor, "get_conditional_balance"):
            cur_mc = executor.get_conditional_balance(tok_c)
            if cur_mc is None or (float(cur_mc) - float(pre_token_balance)) > 1e-6:
                return False
        record_purged_ghost_order(executor, order_id)
        return True
    if not tok_c or not hasattr(executor, "get_conditional_balance"):
        return False
    cur_b = executor.get_conditional_balance(tok_c)
    base_b = float(pre_token_balance) if pre_token_balance is not None else 0.0
    if cur_b is None or (float(cur_b) - base_b) > 1e-6:
        return False
    fills_chk = executor.get_account_fills(tok_c, 0.0, "BUY", str(order_id)) if hasattr(executor, "get_account_fills") else []
    if fills_chk is not None and len(fills_chk) == 0:
        record_purged_ghost_order(executor, order_id)
        return True
    return False


_SYNTHETIC_ORDER_RECORD_KEYS = {"SETTLEMENT_RESOLUTION_PAYOUT", "PRE_SPLIT_MERGE"}


def collect_claimed_position_fill_and_order_ids(
    harvester: Any,
    exclude_tid: Optional[str] = None,
    exclude_pos: Optional[Mapping[str, Any]] = None,
) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """
    Collects `(claimed_fill_ids, claimed_trade_ids, claimed_buy_order_ids, claimed_sell_order_ids)`
    across all OTHER active and closed positions (including stashed `_closed_partner_leg`,
    `_closed_bundle_legs`, and `box_legs_summary` records) so multi-clip scaling on the same
    `token_id` can never double-book another position's BUY or SELL fills.
    """
    fill_ids: Set[str] = set()
    trade_ids: Set[str] = set()
    buy_oids: Set[str] = set()
    sell_oids: Set[str] = set()
    excl = str(exclude_tid or "").strip()

    def _harvest_one(p: Optional[Mapping[str, Any]], tid_hint: str = "") -> None:
        if not isinstance(p, Mapping) or (exclude_pos is not None and p is exclude_pos):
            return
        p_tid = str(tid_hint or p.get("trade_id") or "").strip()
        if excl and p_tid == excl:
            return
        for fk in ("entry_fill_ids", "exit_fill_ids"):
            for v in (p.get(fk) or ()):
                if v:
                    fill_ids.add(str(v))
        for tk in ("trade_ids", "exit_trade_ids"):
            for v in (p.get(tk) or ()):
                if v:
                    trade_ids.add(str(v))
        for bk in ("entry_order_id", "order_id"):
            bv = str(p.get(bk) or "").strip()
            if bv:
                buy_oids.add(bv)
        for sk in ("exit_order_id", "unwind_order_id", "pending_settlement_order_id"):
            sv = str(p.get(sk) or "").strip()
            if sv and sv not in _SYNTHETIC_ORDER_RECORD_KEYS:
                sell_oids.add(sv)
        for cv in (p.get("canceled_maker_exit_oids") or ()):
            cs = str(cv or "").strip()
            if cs and cs not in _SYNTHETIC_ORDER_RECORD_KEYS:
                sell_oids.add(cs)
        ord_recs = p.get("order_records")
        if isinstance(ord_recs, Mapping):
            for ok in ord_recs.keys():
                oks = str(ok or "").strip()
                if oks and oks not in _SYNTHETIC_ORDER_RECORD_KEYS:
                    sell_oids.add(oks)
        partner = p.get("_closed_partner_leg")
        if isinstance(partner, Mapping):
            _harvest_one(partner, str(partner.get("trade_id") or ""))
        for sub_key in ("_closed_bundle_legs", "box_legs_summary"):
            sub_list = p.get(sub_key)
            if isinstance(sub_list, Sequence) and not isinstance(sub_list, (str, bytes)):
                for sub_p in sub_list:
                    if isinstance(sub_p, Mapping):
                        _harvest_one(sub_p, str(sub_p.get("trade_id") or ""))

    for k, ap in (getattr(harvester, "active_positions", None) or {}).items():
        _harvest_one(ap, str(k))
    for cp in (getattr(harvester, "closed_positions", None) or ()):
        _harvest_one(cp, "")
    return fill_ids, trade_ids, buy_oids, sell_oids


def position_own_exit_order_ids(pos: Mapping[str, Any]) -> Set[str]:
    """Returns all CLOB exit/unwind order IDs explicitly belonging to `pos`."""
    own: Set[str] = set()
    for sk in ("exit_order_id", "unwind_order_id", "pending_settlement_order_id"):
        sv = str(pos.get(sk) or "").strip()
        if sv and sv not in _SYNTHETIC_ORDER_RECORD_KEYS:
            own.add(sv)
    for cv in (pos.get("canceled_maker_exit_oids") or ()):
        cs = str(cv or "").strip()
        if cs and cs not in _SYNTHETIC_ORDER_RECORD_KEYS:
            own.add(cs)
    ord_recs = pos.get("order_records")
    if isinstance(ord_recs, Mapping):
        for ok in ord_recs.keys():
            oks = str(ok or "").strip()
            if oks and oks not in _SYNTHETIC_ORDER_RECORD_KEYS:
                own.add(oks)
    return own


def position_attempted_wildcard_sell(pos: Mapping[str, Any]) -> bool:
    """True only when `pos` genuinely attempted a CLOB exit/unwind whose order ID may be unknown."""
    if any(
        float(pos.get(k) or 0.0) > 0.0
        for k in ("exit_post_attempt_ts", "unwind_attempt_ts", "unwind_last_attempt_ts", "unwind_start_time")
    ):
        return True
    st = str(pos.get("exit_order_status") or "").strip().upper()
    return st in {
        "EXIT_POST_UNKNOWN",
        "UNWIND_EXECUTION_OUTCOME_UNKNOWN",
        "UNWIND_UNKNOWN",
        "UNWIND_RETRY_REQUIRED",
        "CANCELED_FOR_RESOLUTION",
        "RESOLUTION_CANCEL_UNCONFIRMED",
    }


def filter_unclaimed_position_fills(
    harvester: Any,
    pos: Mapping[str, Any],
    fills: Optional[Sequence[Mapping[str, Any]]],
    *,
    side: str = "SELL",
    exclude_tid: Optional[str] = None,
    allow_wildcard_sell: bool = True,
) -> List[Dict[str, Any]]:
    """
    Filters CLOB account fills so a position NEVER claims fills or order IDs belonging to
    another clip on the same `token_id`, and rejects wildcard SELL fills on terminal-hold
    positions that never submitted an exit/unwind order.
    """
    if not fills:
        return []
    tid_eff = str(exclude_tid or pos.get("trade_id") or "").strip() or None
    c_fids, c_tids, c_buy_oids, c_sell_oids = collect_claimed_position_fill_and_order_ids(
        harvester, exclude_tid=tid_eff, exclude_pos=pos
    )
    side_u = str(side or "").upper()
    own_exit_oids = position_own_exit_order_ids(pos) if side_u == "SELL" else set()
    own_buy_oids = {
        str(pos.get(k) or "").strip()
        for k in ("entry_order_id", "order_id")
        if str(pos.get(k) or "").strip()
    }
    out: List[Dict[str, Any]] = []
    for f in fills:
        if not isinstance(f, Mapping):
            continue
        fid = str(f.get("fill_id") or "").strip()
        tr_id = str(f.get("trade_id") or f.get("id") or "").strip()
        oid = str(f.get("order_id") or "").strip()
        if fid and fid in c_fids:
            continue
        is_own_oid = bool(
            oid and ((side_u == "SELL" and oid in own_exit_oids) or (side_u == "BUY" and oid in own_buy_oids))
        )
        if tr_id and tr_id in c_tids and not is_own_oid:
            continue
        if side_u == "SELL":
            if oid and oid in c_sell_oids and oid not in own_exit_oids:
                continue
            if not allow_wildcard_sell:
                if not oid or (own_exit_oids and oid not in own_exit_oids) or not own_exit_oids:
                    continue
        elif side_u == "BUY":
            if oid and oid in c_buy_oids and oid not in own_buy_oids:
                continue
            if own_buy_oids and oid and oid not in own_buy_oids:
                continue
        out.append(dict(f))
    return out


async def reconcile_resolution_fills_and_pre_redeem(
    harvester: Any,
    tid: str,
    pos: Dict[str, Any],
    winning_outcome: str,
    won: bool,
    token_id: Optional[str],
    prev_exit_oid: Optional[str],
    entry_oid_res: Optional[str],
    book_rem_shares: float,
) -> Tuple[str, float]:
    """
    Isolated resolution reconciliation helper for `PolymarketLiveHarvester._apply_market_resolution`.
    Prevents cross-position SELL/BUY fill theft across multi-clip positions on the same `token_id`.
    Returns `("CLOSED", 0.0)`, `("DEFERRED", 0.0)`, or `("RECEIVABLE", rem_shares)`.
    """
    exec_settled = "SETTLED"
    exec_filled = "FILLED"
    exec_pos_conf = "POSITION_CONFIRMED"
    if not won:
        if (
            not bool(pos.get("inventory_reconciled"))
            and (pos.get("status") != exec_pos_conf or pos.get("exit_order_status") == "ENTRY_OUTCOME_UNKNOWN")
            and not (pos.get("trade_ids") or pos.get("transactions_hashes"))
            and float(pos.get("filled_exit_shares", 0.0) or 0.0) < 0.01
            and float(pos.get("confirmed_realized_cash", pos.get("realized_exit_cash", 0.0)) or 0.0) <= 0.0
        ):
            _unk_buy_sh = 0.0
            if token_id and hasattr(harvester.executor, "get_account_fills"):
                try:
                    _bf_u = await asyncio.to_thread(
                        harvester.executor.get_account_fills,
                        token_id,
                        max(0.0, float(pos.get("entry_ts", 0.0) or 0.0) - 300.0),
                        "BUY",
                        entry_oid_res,
                    )
                    if not _bf_u and entry_oid_res is not None:
                        _bf_u = await asyncio.to_thread(
                            harvester.executor.get_account_fills,
                            token_id,
                            max(0.0, float(pos.get("entry_ts", 0.0) or 0.0) - 300.0),
                            "BUY",
                            None,
                        )
                    _bf_u = filter_unclaimed_position_fills(harvester, pos, _bf_u, side="BUY", exclude_tid=tid)
                    if _bf_u:
                        _unk_buy_sh = sum(
                            float(f.get("size", 0.0) or 0.0)
                            for f in _bf_u
                            if str(f.get("status", "CONFIRMED")).upper() in ("CONFIRMED", "MINED", "MATCHED", "")
                        )
                        if _unk_buy_sh >= 0.02:
                            pos["inventory_reconciled"] = True
                            pos["trade_ids"] = list(dict.fromkeys(str(f.get("trade_id") or f.get("id")) for f in _bf_u if (f.get("trade_id") or f.get("id"))))
                            pos["transactions_hashes"] = list(dict.fromkeys(str(f.get("transaction_hash")) for f in _bf_u if f.get("transaction_hash")))
                except Exception:
                    _unk_buy_sh = 0.0
            _bal_u = None
            if _unk_buy_sh < 0.02 and token_id:
                try:
                    _bal_u, _ = await asyncio.to_thread(harvester._wallet_token_balance, token_id)
                except Exception:
                    _bal_u = None
            if _unk_buy_sh < 0.02 and (_bal_u is None or float(_bal_u) < 0.02):
                for _zk in ("expected_terminal_payout_usd", "redemption_receivable_usd", "winning_shares_held", "entry_shares", "notional_usd", "remaining_cost_basis", "fee_usd", "entry_fee_cash_usd"):
                    pos[_zk] = 0.0
                pos["expected_winning_outcome"] = winning_outcome
                _no_exec_r = "UNFILLED_MAKER_EXPIRED_NO_FILL" if "MAKER" in str(pos.get("box_type") or pos.get("fee_source") or "").upper() else "ENTRY_NOT_EXECUTED_AT_RESOLUTION"
                harvester._close_position(tid, pos, "NOT_EXECUTED", _no_exec_r, won=False, record_pnl=False)
                return ("CLOSED", 0.0)
            pos["inventory_reconciled"] = True
        pos["expected_terminal_payout_usd"] = 0.0
        pos["redemption_receivable_usd"] = 0.0
        pos["winning_shares_held"] = 0.0
        pos["expected_winning_outcome"] = winning_outcome
        harvester._close_position(tid, pos, exec_settled, "MARKET_RESOLVED_LOSS", won=False)
        return ("CLOSED", 0.0)

    bal, src = await asyncio.to_thread(harvester._wallet_token_balance, token_id)
    if src != harvester.ONCHAIN_SOURCE and (bal is None or bal < 0.01):
        logger.warning(
            f"[RESOLUTION DEFERRED] {tid}: Winning position on-chain ERC-1155 balance unavailable "
            f"(bal={bal}, src={src}). Deferring resolution closeout until Polygon RPC responds."
        )
        return ("DEFERRED", 0.0)
    rem_shares = min(book_rem_shares, bal) if (bal is not None and src == harvester.ONCHAIN_SOURCE) else book_rem_shares
    if rem_shares < 0.02:
        if float(pos.get("confirmed_realized_cash", pos.get("realized_exit_cash", 0.0)) or 0.0) <= 0.0 and token_id:
            own_exit_oids = position_own_exit_order_ids(pos)
            if prev_exit_oid:
                own_exit_oids.add(str(prev_exit_oid))
            can_wildcard_sell = position_attempted_wildcard_sell(pos)
            try:
                collected_sells: List[Dict[str, Any]] = []
                for q_oid in sorted(own_exit_oids):
                    qf = await asyncio.to_thread(
                        harvester.executor.get_account_fills, token_id, float(pos.get("entry_ts", 0.0) or 0.0), "SELL", q_oid
                    )
                    if isinstance(qf, list) and qf:
                        collected_sells.extend(qf)
                if not collected_sells and can_wildcard_sell:
                    wf = await asyncio.to_thread(
                        harvester.executor.get_account_fills, token_id, float(pos.get("entry_ts", 0.0) or 0.0), "SELL", None
                    )
                    if isinstance(wf, list) and wf:
                        collected_sells.extend(wf)
                extra_fills = filter_unclaimed_position_fills(
                    harvester,
                    pos,
                    collected_sells,
                    side="SELL",
                    exclude_tid=tid,
                    allow_wildcard_sell=can_wildcard_sell,
                )
                if extra_fills:
                    harvester._record_history_fills(pos, extra_fills, taker=False)
            except Exception:
                pass
        _conf_cash = float(pos.get("confirmed_realized_cash", pos.get("realized_exit_cash", 0.0)) or 0.0)
        _notional_u = float(pos.get("notional_usd", 0.0) or 0.0)
        _ent_sh_u = float(pos.get("entry_shares", 0.0) or 0.0)
        _ex_sh_u = float(pos.get("filled_exit_shares", 0.0) or 0.0)
        if _conf_cash > _notional_u or (_conf_cash > 0.0 and _ent_sh_u > 0.0 and _ex_sh_u >= _ent_sh_u - 0.02):
            _clob_won = _conf_cash >= _notional_u - 1e-6
            pos["expected_terminal_payout_usd"] = 0.0
            pos["redemption_receivable_usd"] = 0.0
            pos["winning_shares_held"] = 0.0
            pos["expected_winning_outcome"] = winning_outcome
            pos["exit_cash_estimated"] = False
            pos["estimated_exit_cash"] = 0.0
            pos["confirmed_realized_cash"] = _conf_cash
            harvester._close_position(
                tid,
                pos,
                exec_filled,
                "MAKER_SCALP_FILLED_CLOB" if _clob_won else "CLOB_EXIT_FILLED_PRE_RESOLUTION",
                won=_clob_won,
            )
            return ("CLOSED", 0.0)

        post_sell_rem = float(pos.get("remaining_shares", pos.get("remaining_exit_shares", book_rem_shares)) or 0.0)
        confirmed_pre_redeemed = 0.0
        if post_sell_rem >= 0.02 and bal is not None and src == harvester.ONCHAIN_SOURCE and float(bal) <= 0.0001:
            if token_id and hasattr(harvester.executor, "get_account_fills"):
                try:
                    buy_fills = await asyncio.to_thread(
                        harvester.executor.get_account_fills,
                        token_id,
                        max(0.0, float(pos.get("entry_ts", 0.0) or 0.0) - 300.0),
                        "BUY",
                        entry_oid_res,
                    )
                    if not buy_fills and entry_oid_res is not None:
                        buy_fills = await asyncio.to_thread(
                            harvester.executor.get_account_fills,
                            token_id,
                            max(0.0, float(pos.get("entry_ts", 0.0) or 0.0) - 300.0),
                            "BUY",
                            None,
                        )
                    buy_fills = filter_unclaimed_position_fills(harvester, pos, buy_fills, side="BUY", exclude_tid=tid)
                    if buy_fills:
                        pos["entry_fill_ids"] = sorted(
                            set(pos.get("entry_fill_ids") or []) | {str(f.get("fill_id")) for f in buy_fills if f.get("fill_id")}
                        )
                        pos["trade_ids"] = list(dict.fromkeys([str(x) for x in (pos.get("trade_ids") or []) if x] + [str(f.get("trade_id") or f.get("id")) for f in buy_fills if (f.get("trade_id") or f.get("id"))]))
                        pos["transactions_hashes"] = list(dict.fromkeys([str(x) for x in (pos.get("transactions_hashes") or []) if x] + [str(f.get("transaction_hash")) for f in buy_fills if f.get("transaction_hash")]))
                        conf_buy_sh = sum(
                            float(f.get("size", 0.0) or 0.0)
                            for f in buy_fills
                            if str(f.get("status", "CONFIRMED")).upper() in ("CONFIRMED", "MINED", "MATCHED", "")
                        )
                        sold_sh = float(pos.get("filled_exit_shares", 0.0) or 0.0)
                        confirmed_pre_redeemed = min(post_sell_rem, max(0.0, conf_buy_sh - sold_sh))
                except Exception:
                    confirmed_pre_redeemed = 0.0
            if confirmed_pre_redeemed < 0.02 and hasattr(harvester.executor, "find_redemption_payouts"):
                try:
                    head_chk = await asyncio.to_thread(harvester.executor.get_current_block_number)
                    pre_recs = await asyncio.to_thread(
                        harvester.executor.find_redemption_payouts,
                        str(pos.get("condition_id") or ""),
                        max(0, int(head_chk) - 15000) if isinstance(head_chk, int) else None,
                    )
                    if isinstance(pre_recs, list) and pre_recs:
                        _redeemed_set = {str(h) for h in (getattr(harvester, "redeemed_tx_hashes", None) or ()) if h}
                        _consumed_map = getattr(harvester, "redeemed_tx_consumed_usd", None) or {}
                        _fresh_avail = [
                            max(0.0, float(r.get("payout_usd") or 0.0) - float(_consumed_map.get(str(r.get("transaction_hash") or ""), 0.0) or 0.0))
                            for r in pre_recs
                            if isinstance(r, Mapping)
                            and str(r.get("transaction_hash") or "") not in _redeemed_set
                        ]
                        if _fresh_avail:
                            confirmed_pre_redeemed = min(post_sell_rem, max(_fresh_avail))
                except Exception:
                    pass

        if confirmed_pre_redeemed >= 0.02:
            rem_shares = confirmed_pre_redeemed
            pos["_pre_redeemed_onchain"] = True
            pos["_collateral_exit_credited"] = True
            logger.info(
                f"[PRE-REDEEMED WIN DETECTED] {tid}: Confirmed {rem_shares:.2f} unexited BUY shares with 0 "
                f"ERC-1155 balance after {winning_outcome} win -> settling as pre-redeemed on-chain payout."
            )
        else:
            pos["expected_terminal_payout_usd"] = 0.0
            pos["redemption_receivable_usd"] = 0.0
            pos["winning_shares_held"] = 0.0
            pos["expected_winning_outcome"] = winning_outcome
            if (
                not bool(pos.get("inventory_reconciled"))
                and (pos.get("status") != exec_pos_conf or pos.get("exit_order_status") == "ENTRY_OUTCOME_UNKNOWN")
                and not (pos.get("trade_ids") or pos.get("transactions_hashes"))
                and float(pos.get("filled_exit_shares", 0.0) or 0.0) < 0.01
                and float(pos.get("confirmed_realized_cash", pos.get("realized_exit_cash", 0.0)) or 0.0) <= 0.0
            ):
                for _zk in ("entry_shares", "notional_usd", "remaining_cost_basis", "fee_usd", "entry_fee_cash_usd"):
                    pos[_zk] = 0.0
                harvester._close_position(
                    tid, pos, "NOT_EXECUTED", "ENTRY_NOT_EXECUTED_AT_RESOLUTION", won=False, record_pnl=False
                )
                return ("CLOSED", 0.0)
            harvester._close_position(tid, pos, exec_settled, "MARKET_RESOLVED_NO_INVENTORY", won=False)
            return ("CLOSED", 0.0)
    return ("RECEIVABLE", rem_shares)


_POLYGON_OO_ADDRESSES: Tuple[str, ...] = (
    "0x2c0367a9db231ddebd88a94b4f6461a6e47c58b1",  # Polymarket MOOV2 (UmaCtfAdapter v3 & NegRiskUmaCtfAdapter)
    "0xee3afe347d5c74317041e2618c49534daf887c24",  # Polymarket Classic OptimisticOracleV2
)
_TOPIC_OO_PROPOSE_PRICE: str = "0x6e51dd00371aabffa82cd401592f76ed51e98a9ea4b58751c70463a2c78b5ca1"
_TOPIC_OO_DISPUTE_PRICE: str = "0x5165909c3d1c01c5d1e121ac6f6d01dda1ba24bc9e1f975b5a375339c15be7f3"
_ANC_MARKET_ID_RE = re.compile(r"market_id:\s*(\d{5,9})")


def _poll_polygon_oo_proposal_and_dispute_mids_sync(
    last_bn: int,
    rpc_url: Optional[str] = None,
    timeout: float = 4.0,
) -> Tuple[int, List[str], List[str]]:
    """
    Polls Polygon `OptimisticOracleV2` (`MOOV2` + `OOV2`) `ProposePrice` and `DisputePrice` logs:
      - Extracts every newly proposed `market_id` from UTF-8 `ancillaryData` (including low-volume
        Challenger tennis, Europa League props, NCAA, and esports derivatives invisible to Gamma top-1500).
      - Extracts any disputed `market_id` within seconds of block inclusion for instant cache eviction.
    """
    rpcs = [
        r
        for r in (
            rpc_url,
            os.getenv("POLYGON_RPC_URL"),
            "https://polygon-bor-rpc.publicnode.com",
            "https://1rpc.io/matic",
        )
        if r
    ]
    for rpc in rpcs:
        try:
            req_bn = urllib.request.Request(
                rpc,
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}).encode("utf-8"),
                {"Content-Type": "application/json", "User-Agent": "Dominus/1.0"},
            )
            with urllib.request.urlopen(req_bn, timeout=timeout) as r_b:
                bn_hex = (json.loads(r_b.read()) or {}).get("result")
            if not bn_hex:
                continue
            bn = int(str(bn_hex), 16)
            if last_bn <= 0:
                mid_bn = max(0, bn - 900)
                windows = ([(max(0, bn - 1800), mid_bn - 1)] if mid_bn > max(0, bn - 1800) else []) + [(mid_bn, bn)]
            else:
                from_bn = max(last_bn - 2, bn - 240)
                if from_bn > bn:
                    return bn, [], []
                windows = [(from_bn, bn)]
            logs: List[Any] = []
            any_ok = False
            for w_from, w_to in windows:
                if w_from > w_to:
                    continue
                req_lg = urllib.request.Request(
                    rpc,
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "eth_getLogs",
                            "params": [
                                {
                                    "address": list(_POLYGON_OO_ADDRESSES),
                                    "topics": [[_TOPIC_OO_PROPOSE_PRICE, _TOPIC_OO_DISPUTE_PRICE]],
                                    "fromBlock": hex(w_from),
                                    "toBlock": hex(w_to),
                                }
                            ],
                        }
                    ).encode("utf-8"),
                    {"Content-Type": "application/json", "User-Agent": "Dominus/1.0"},
                )
                try:
                    with urllib.request.urlopen(req_lg, timeout=timeout) as r_l:
                        part = (json.loads(r_l.read()) or {}).get("result")
                    if isinstance(part, list):
                        logs.extend(part)
                        any_ok = True
                except Exception:
                    continue
            if not any_ok:
                continue
            proposed_ids: List[str] = []
            disputed_ids: List[str] = []
            seen_p: Set[str] = set()
            seen_d: Set[str] = set()
            for lg in logs:
                if not isinstance(lg, Mapping):
                    continue
                tops = lg.get("topics") or []
                t0 = str(tops[0] if tops else "").lower()
                data_hex = str(lg.get("data") or "")
                if not data_hex.startswith("0x") or len(data_hex) < 10:
                    continue
                raw_txt = bytes.fromhex(data_hex[2:]).decode("utf-8", errors="ignore")
                for m_id in _ANC_MARKET_ID_RE.findall(raw_txt):
                    if t0 == _TOPIC_OO_DISPUTE_PRICE:
                        if m_id not in seen_d:
                            seen_d.add(m_id)
                            disputed_ids.append(m_id)
                    elif t0 == _TOPIC_OO_PROPOSE_PRICE:
                        if m_id not in seen_p:
                            seen_p.add(m_id)
                            proposed_ids.append(m_id)
            return bn, proposed_ids, disputed_ids
        except Exception:
            continue
    return last_bn, [], []


async def augment_uma_proposed_from_universe_and_polygon(
    daemon: Any,
    now_ts: float,
    *,
    gamma_url: str = "https://gamma-api.polymarket.com",
    poll_fn: Optional[Callable[[int], Tuple[int, List[str], List[str]]]] = None,
) -> Dict[str, int]:
    """
    Augments `daemon.uma_proposed_markets` every `>= 10s` via Polygon `OptimisticOracleV2`
    `ProposePrice` / `DisputePrice` logs + batch Gamma market hydration, catching low-volume
    child sports/tennis/esports props within seconds of on-chain proposal and instantly
    evicting any disputed `market_id` from `uma_onchain_cache` and `uma_proposed_markets`.
    """
    proposed_map: Dict[str, Dict[str, Any]] = getattr(daemon, "uma_proposed_markets", None)
    if not isinstance(proposed_map, dict):
        proposed_map = {}
        daemon.uma_proposed_markets = proposed_map
    onchain_cache: Dict[str, Any] = getattr(daemon, "uma_onchain_cache", {})
    disputed_map: Dict[str, float] = daemon.__dict__.setdefault("_uma_poly_disputed_ids", {})
    evicted = 0
    if disputed_map:
        for d_k, d_exp in list(disputed_map.items()):
            if float(d_exp or 0.0) <= float(now_ts):
                disputed_map.pop(d_k, None)
            else:
                if d_k in proposed_map:
                    proposed_map.pop(d_k, None)
                    evicted += 1
                if isinstance(onchain_cache, dict):
                    onchain_cache.pop(d_k, None)

    is_mocked = bool(
        getattr(daemon, "single_scan", False)
        or any(k in getattr(daemon, "__dict__", {}) for k in ("fetch_json", "fetch_books_batch"))
    )
    if is_mocked and poll_fn is None:
        return {"added": 0, "disputed_evicted": evicted}
    last_ts = float(daemon.__dict__.get("_last_uma_poly_log_ts", 0.0) or 0.0)
    if poll_fn is None and (float(now_ts) - last_ts) < 10.0:
        return {"added": 0, "disputed_evicted": evicted}
    daemon.__dict__["_last_uma_poly_log_ts"] = float(now_ts)

    from src.polymarket_research.uma_nba_endgame_engine import is_objective_uma_market

    last_bn = int(daemon.__dict__.get("_last_uma_poly_bn", 0) or 0)
    runner = poll_fn or _poll_polygon_oo_proposal_and_dispute_mids_sync
    new_bn, prop_mids, disp_mids = await asyncio.to_thread(runner, last_bn)
    if new_bn > 0:
        daemon.__dict__["_last_uma_poly_bn"] = int(new_bn)

    neg_ids: Dict[str, float] = daemon.__dict__.setdefault("_uma_poly_reject_ids", {})
    if len(neg_ids) > 4000:
        cutoff_n = float(now_ts) - 1800.0
        for k_n in [k for k, ts_k in neg_ids.items() if ts_k < cutoff_n]:
            neg_ids.pop(k_n, None)

    for d_mid in disp_mids:
        disputed_map[d_mid] = float(now_ts) + 7200.0
        neg_ids[d_mid] = float(now_ts) + 7200.0
        if d_mid in proposed_map:
            proposed_map.pop(d_mid, None)
            evicted += 1
        if isinstance(onchain_cache, dict):
            onchain_cache.pop(d_mid, None)

    need_mids = [
        m_id
        for m_id in reversed(prop_mids)
        if m_id not in proposed_map and float(neg_ids.get(m_id, 0.0) or 0.0) <= float(now_ts)
    ][:120]
    for ex_mid in prop_mids:
        if isinstance(onchain_cache, dict) and ex_mid in onchain_cache:
            c_ent = onchain_cache.get(ex_mid)
            if isinstance(c_ent, tuple) and len(c_ent) >= 2 and isinstance(c_ent[1], Mapping):
                if not c_ent[1].get("verified") and "UNINITIALIZED" in str(c_ent[1].get("reason") or ""):
                    onchain_cache.pop(ex_mid, None)

    added = 0
    if need_mids and hasattr(daemon, "fetch_json"):
        chunks = [need_mids[i : i + 40] for i in range(0, len(need_mids), 40)]
        pages = await asyncio.gather(
            *(
                daemon.fetch_json(
                    f"{gamma_url}/markets?limit=50&" + "&".join(f"id={x}" for x in ch),
                    timeout=4.5,
                )
                for ch in chunks
            ),
            return_exceptions=True,
        )
        seen_ret: Set[str] = set()
        for pg in pages:
            if not isinstance(pg, list):
                continue
            for cm in pg:
                if not isinstance(cm, dict):
                    continue
                mid_c = str(cm.get("id") or "").strip()
                if not mid_c:
                    continue
                seen_ret.add(mid_c)
                if cm.get("closed") or cm.get("enableOrderBook") is False:
                    neg_ids[mid_c] = float(now_ts) + 3600.0
                    continue
                ust_c = str(cm.get("umaResolutionStatus") or "").strip().lower()
                if ust_c in ("", "none"):
                    cm = {**cm, "umaResolutionStatus": "proposed"}
                ok_c, _ = is_objective_uma_market(cm)
                if ok_c:
                    proposed_map[mid_c] = cm
                    added += 1
                else:
                    neg_ids[mid_c] = float(now_ts) + 3600.0
        for m_miss in need_mids:
            if m_miss not in seen_ret:
                neg_ids[m_miss] = float(now_ts) + 300.0
    return {"added": added, "disputed_evicted": evicted}


_S2_ASSET_TAKER_FLOW_WEIGHT: Dict[str, float] = {
    "BTC": 1.00,
    "ETH": 0.92,
    "SOL": 0.85,
    "XRP": 0.64,
    "XAU": 0.52,
    "XAG": 0.48,
    "BNB": 0.22,
    "DOGE": 0.18,
    "HYPE": 0.12,
    "ZEC": 0.10,
}
_S2_TIER1_LIQUID_ASSETS = frozenset({"BTC", "ETH", "SOL", "XRP"})
_S2_TIER3_ILLIQUID_ASSETS = frozenset({"ZEC", "HYPE", "DOGE", "BNB"})

_ET_4H_TZ = get_us_eastern_tz()


def resolve_s2_maker_concurrent_cap(harvester: Any, rb_cfg: Optional[Mapping[str, Any]] = None) -> int:
    """
    Returns concurrent `S2` Maker slot cap (`2` on live real CLOB or when `enforce_s2_multi_slot=True`,
    preserving `1` on offline `MagicMock` test harnesses).
    """
    rb = rb_cfg
    if rb is None:
        try:
            from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

            rb = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes") or {}
        except Exception:
            rb = {}
    cfg_slots = max(1, int((rb or {}).get("s2_maker_max_concurrent_slots", 1) or 1))
    if getattr(harvester, "enforce_s2_multi_slot", False):
        return max(2, cfg_slots)
    ex = getattr(harvester, "executor", None)
    live_real_clob = (
        not getattr(harvester, "dry_run", True)
        and getattr(ex, "client", None) is not None
        and getattr(getattr(ex, "client", None), "_mock_children", None) is None
        and "post_maker_entry_order" not in getattr(ex, "__dict__", {})
    )
    return cfg_slots if live_real_clob else 1


def is_s2_maker_concurrent_capped(harvester: Any, inflight_s2_mkr: Any) -> bool:
    s2_cap = resolve_s2_maker_concurrent_cap(harvester)
    active_cnt = len(inflight_s2_mkr or ()) + sum(
        1
        for iv in (getattr(harvester, "pending_entry_intents", None) or {}).values()
        if isinstance(iv, Mapping)
        and str(iv.get("sleeve_source") or "") in FAST_GUN_S2_SLEEVES
        and str(iv.get("inflight_key") or "") not in (inflight_s2_mkr or ())
    )
    return active_cnt >= s2_cap


async def maybe_preempt_low_tier_s2_maker_slot(
    harvester: Any,
    cand_asset: str,
    inflight_s2_mkr: Any,
) -> bool:
    """
    When `S2MKR` concurrent slots are occupied by low-velocity Tier-3 altcoins (`ZEC`, `HYPE`,
    `DOGE`, `BNB`), an incoming Tier-1 liquid major (`BTC`, `ETH`, `SOL`, `XRP`) preempts the
    lowest-flow unfilled altcoin Maker intent so Tier-1 early-exit flow is never starved.
    """
    if not is_s2_maker_concurrent_capped(harvester, inflight_s2_mkr):
        return True
    cand_u = str(cand_asset or "").strip().upper()
    if cand_u not in _S2_TIER1_LIQUID_ASSETS:
        return False
    pe_map = getattr(harvester, "_maker_anchor_preempt_events", None) or {}
    if not pe_map:
        return False
    victims: List[Tuple[float, float, str]] = []
    for iv in (getattr(harvester, "pending_entry_intents", None) or {}).values():
        if not (isinstance(iv, Mapping) and iv.get("live_maker_anchor_inflight")):
            continue
        if str(iv.get("sleeve_source") or "") not in FAST_GUN_S2_SLEEVES:
            continue
        ik = str(iv.get("inflight_key") or "")
        if not ik or ik not in pe_map:
            continue
        iv_ast = str(iv.get("asset") or "").strip().upper()
        if not iv_ast and ik.startswith("S2MKR_"):
            parts = ik.split("_")
            if len(parts) >= 2:
                iv_ast = parts[1].upper()
        if iv_ast in _S2_TIER1_LIQUID_ASSETS:
            continue
        w_flow = _S2_ASSET_TAKER_FLOW_WEIGHT.get(iv_ast, 0.25)
        victims.append((w_flow, float(iv.get("ts") or 0.0), ik))
    if not victims:
        return False
    victims.sort(key=lambda r: (r[0], r[1]))
    _, _, victim_ik = victims[0]
    ev = pe_map.get(victim_ik)
    if ev is None:
        return False
    reason_map = harvester.__dict__.setdefault("_maker_anchor_preempt_reasons", {})
    reason_map[victim_ik] = f"S2_TIER1_UPGRADE:{cand_u}"
    ev.set()
    logger.info(f"[S2MKR TIER-1 UPGRADE] Preempting low-flow {victim_ik} for Tier-1 {cand_u} Maker Lock")
    for _ in range(8):
        await asyncio.sleep(0.025)
        if not is_s2_maker_concurrent_capped(harvester, inflight_s2_mkr):
            return True
    return not is_s2_maker_concurrent_capped(harvester, inflight_s2_mkr)


def _estimate_intent_velocity_bps_hr(it: Mapping[str, Any], now_ts: float) -> float:
    ib = float(it.get("anchor_bid_px") or 0.0)
    ie = float(it.get("expiry_ts") or 0.0)
    sl_it = str(it.get("sleeve_source") or "")
    fl_h = sll_settlement_lag_floor_hours(sl_it)
    if 0.0 < ib < 1.0 and ie > now_ts:
        return round(((1.0 - ib) * 10000.0) / max(fl_h, (ie - now_ts) / 3600.0), 2)
    if 0.0 < ib < 1.0 and fl_h > 0.0:
        return round(((1.0 - ib) * 10000.0) / fl_h, 2)
    return float(it.get("velocity_bps_hr") or 0.0)


def preempt_makers_for_instant_taker_arb(
    harvester: Any,
    *,
    reason: str,
    target_market_ids: Set[str],
    cand_net_cost: float,
    free_cash_hint: Optional[float],
    target_arb_cash_usd: float = 45.0,
    min_fallback_cash_usd: float = 16.0,
    force_cross_market_when_low_cash: bool = False,
    now_ts: Optional[float] = None,
) -> Tuple[int, Set[str]]:
    """
    Selective `<70ms` Batch Cancel-on-Arb Maker Preemption:
      1. Always preempts any resting Maker order on `target_market_ids`.
      2. When an instant riskless Taker arb has `>= 200 bps` net edge (`cand_net_cost <= 0.98005`)
         and `free_cash < $45` (capped at `88%` of live NAV), OR when `force_cross_market_when_low_cash`
         is set and `free_cash < min_fallback_cash_usd`, ranks cross-market resting Makers by
         lowest velocity & non-`FIFO #1` first and selects ONLY the `k` lowest-velocity intents
         needed to hit target sweep budget — preserving unrelated `#1 FIFO` `BOND1` bids!
      3. Dispatches one single-RTT `client.cancel_orders(batch_oids)` call on real authenticated
         CLOB clients before signaling preempt events so orders free collateral in `~65ms`.
    """
    clean_targets = {str(m) for m in (target_market_ids or set()) if m}
    arb_edge_bps = round((1.0 - float(cand_net_cost or 0.995)) * 10000.0, 2)
    is_fat_200bps_arb = arb_edge_bps >= 200.0 - 1e-6

    # Preserve custom monkeypatched `_preempt_resting_maker_anchors` hooks in unit tests.
    if "_preempt_resting_maker_anchors" in getattr(harvester, "__dict__", {}):
        use_all = None if (
            not getattr(harvester, "dry_run", True)
            and (
                (is_fat_200bps_arb and (free_cash_hint is None or free_cash_hint < target_arb_cash_usd))
                or (force_cross_market_when_low_cash and (free_cash_hint is None or free_cash_hint < min_fallback_cash_usd))
            )
        ) else clean_targets
        cnt = int(harvester._preempt_resting_maker_anchors(reason=reason, market_ids=use_all) or 0)
        sel_keys = {
            str(iv.get("inflight_key") or "")
            for iv in (getattr(harvester, "pending_entry_intents", None) or {}).values()
            if isinstance(iv, Mapping)
            and iv.get("live_maker_anchor_inflight")
            and (use_all is None or str(iv.get("market_id") or "") in use_all)
            and str(iv.get("inflight_key") or "")
        }
        return cnt, sel_keys

    pe_map = getattr(harvester, "_maker_anchor_preempt_events", None) or {}
    if not pe_map:
        return 0, set()
    now_f = float(now_ts if now_ts is not None else time.time())
    pend_map = getattr(harvester, "pending_entry_intents", None) or {}
    same_mkt_list: List[Mapping[str, Any]] = []
    cross_mkt_list: List[Mapping[str, Any]] = []
    tot_reserved = 0.0
    for iv in list(pend_map.values()):
        if not (isinstance(iv, Mapping) and iv.get("live_maker_anchor_inflight")):
            continue
        ik = str(iv.get("inflight_key") or "")
        if not ik or ik not in pe_map:
            continue
        not_u = max(0.0, float(iv.get("notional_usd") or 0.0))
        tot_reserved += not_u
        if str(iv.get("market_id") or "") in clean_targets:
            same_mkt_list.append(iv)
        else:
            cross_mkt_list.append(iv)

    selected_intents: List[Mapping[str, Any]] = list(same_mkt_list)
    freed_usd = sum(max(0.0, float(x.get("notional_usd") or 0.0)) for x in same_mkt_list)

    if not getattr(harvester, "dry_run", True) and cross_mkt_list:
        open_pos_u = sum(
            max(0.0, float(p.get("notional_usd") or 0.0))
            for p in (getattr(harvester, "active_positions", None) or {}).values()
            if isinstance(p, Mapping) and not position_is_settlement_receivable(p)
        )
        free_now = float(free_cash_hint) if free_cash_hint is not None else 0.0
        est_nav = free_now + tot_reserved + open_pos_u
        eff_target_45 = min(float(target_arb_cash_usd), max(20.0, est_nav * 0.88)) if est_nav > 0.0 else float(target_arb_cash_usd)
        need_goal = 0.0
        if is_fat_200bps_arb and (free_cash_hint is None or (free_now + freed_usd) < eff_target_45):
            need_goal = eff_target_45
        elif force_cross_market_when_low_cash and (free_cash_hint is None or (free_now + freed_usd) < min_fallback_cash_usd):
            need_goal = float(min_fallback_cash_usd)
        if need_goal > 0.0:
            cross_mkt_list.sort(
                key=lambda it: (
                    1 if bool(it.get("fifo_rank1_verified")) else 0,
                    _estimate_intent_velocity_bps_hr(it, now_f),
                    -max(0.0, float(it.get("notional_usd") or 0.0)),
                )
            )
            for it_c in cross_mkt_list:
                if free_cash_hint is not None and (free_now + freed_usd) >= need_goal - 1e-6:
                    break
                selected_intents.append(it_c)
                freed_usd += max(0.0, float(it_c.get("notional_usd") or 0.0))

    if not selected_intents:
        return 0, set()

    ex = getattr(harvester, "executor", None)
    clob_client = getattr(ex, "client", None) if ex is not None else None
    real_clob_batch = (
        not getattr(harvester, "dry_run", True)
        and clob_client is not None
        and getattr(clob_client, "_mock_children", None) is None
        and callable(getattr(clob_client, "cancel_orders", None))
    )
    batch_oids = [
        str(it.get("entry_order_id") or "").strip()
        for it in selected_intents
        if str(it.get("entry_order_id") or "").strip()
    ]
    if real_clob_batch and batch_oids:
        t_bc0 = time.perf_counter()
        try:
            clob_client.cancel_orders(batch_oids)
            bc_ms = round((time.perf_counter() - t_bc0) * 1000.0, 1)
            logger.info(
                f"⚡ [CANCEL-ON-ARB BATCH] Cancelled {len(batch_oids)} Maker order(s) in {bc_ms:.1f}ms "
                f"(edge={arb_edge_bps:.0f}bps, freed~=${freed_usd:.2f}, reason={reason})"
            )
        except Exception as bc_exc:
            logger.debug(f"Batch cancel_orders notice ({reason}): {bc_exc}")

    reason_map = harvester.__dict__.setdefault("_maker_anchor_preempt_reasons", {})
    selected_keys: Set[str] = set()
    signaled = 0
    for it_s in selected_intents:
        ik_s = str(it_s.get("inflight_key") or "")
        ev_s = pe_map.get(ik_s)
        if ev_s is not None:
            if reason and ik_s not in reason_map:
                reason_map[ik_s] = reason
            ev_s.set()
            selected_keys.add(ik_s)
            signaled += 1
    return signaled, selected_keys


def is_s2_maker_bg_task_capped(harvester: Any) -> bool:
    s2_cap = resolve_s2_maker_concurrent_cap(harvester)
    s2_set = {t for t in (getattr(harvester, "_s2_mkr_bg_tasks", None) or set()) if t is not None and not t.done()}
    legacy_t = getattr(harvester, "_s2_mkr_bg_task", None)
    if legacy_t is not None and not legacy_t.done():
        s2_set.add(legacy_t)
    return len(s2_set) >= s2_cap


def register_s2_maker_bg_task(harvester: Any, task: Any) -> None:
    s2_set = harvester.__dict__.setdefault("_s2_mkr_bg_tasks", set())
    s2_set.add(task)
    harvester._s2_mkr_bg_task = task

    def _rm(done_t: Any) -> None:
        s2_set.discard(done_t)
        if getattr(harvester, "_s2_mkr_bg_task", None) is done_t:
            rem = [x for x in s2_set if not x.done()]
            harvester._s2_mkr_bg_task = rem[0] if rem else None

    if hasattr(task, "add_done_callback"):
        task.add_done_callback(_rm)


def score_live_candidate_velocity_ev(
    c: Mapping[str, Any],
    is_maker: bool,
    now_ts: float,
    compute_vel_fn: Optional[Callable[..., float]] = None,
) -> float:
    """
    Queue-aware & taker-flow-weighted live candidate ranker:
      1. `S2` Maker: caps nominal spread credit at `$0.06` (`600 bps`) + maker rebate so ghost `$0.70` bids
         on dead books (`DOGE`/`BNB`) never outrank real two-sided `BTC`/`ETH`/`SOL` taker flow!
      2. `MKR_REWARD_LOCKED_CARRY`: credits daily liquidity reward yield (`>= 20 bps/sh`) alongside `$1.00` carry.
      3. `SINGLE_LEG_MAKER_LOCK` (`BOND1` / `MKR_LOCK1` / `W_PRUNE1`): scales `fill_prob` monotonically by
         `queue_ahead_usd` (`$0-$5 -> 0.82` down to `>$225 -> 0.14`) so empty/shallow L1 queues fill first.
    """
    b_t = str(c.get("box_type") or "").strip().upper()
    sl_c = str(c.get("sleeve_source") or "").strip()
    sl_u = sl_c.upper()
    cost_n = float(c.get("box_cost_net") or 0.99)
    sh_f = float(c.get("shares") or 12.0)
    reb_ps = max(0.0, float(c.get("maker_rebate_ps") or 0.0))

    if b_t == "NEGRISK_CONVERT":
        edge_u = max(0.0, float(c.get("net_edge_per_share") or (1.0 - cost_n))) * sh_f
        hold_c = 15.0
        recycle_f = 1.0
    elif is_maker and sl_u in FAST_GUN_S2_SLEEVES:
        eff_edge_ps = min(0.06, max(0.0, 1.0 - cost_n)) + reb_ps
        edge_u = eff_edge_ps * sh_f
        exp_c = float(c.get("expiry_ts") or 0.0)
        hold_c = max(15.0, exp_c - float(now_ts)) if exp_c > 0.0 else 30.0
        recycle_f = 0.50
    else:
        exp_c = float(c.get("expiry_ts") or 0.0)
        hold_c = (
            max(20.0, exp_c - float(now_ts))
            if exp_c > 0.0
            else (300.0 if b_t in {"DOMINANCE", "DOMINANCE_MAKER_ANCHOR"} else 7200.0)
        )
        spon_ps = max(0.0, float(c.get("sponsor_daily_reward_ps") or 0.0)) * min(1.0, hold_c / 86400.0)
        hold_apy_ps = (0.00000456 * (hold_c / 3600.0)) if bool(c.get("holding_rewards_enabled")) else 0.0
        rw_bonus = (max(0.0020, reb_ps + spon_ps) if sl_u == "MKR_REWARD_LOCKED_CARRY" else reb_ps) + hold_apy_ps
        edge_u = (max(0.0, 1.0 - cost_n) + rw_bonus) * sh_f
        recycle_f = (
            0.15
            if sl_c in {"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"}
            else 0.50
        )

    if not is_maker:
        fp = 0.85
    elif sl_u in FAST_GUN_S2_SLEEVES:
        ast_u = str(c.get("asset") or "").strip().upper()
        w_ast = _S2_ASSET_TAKER_FLOW_WEIGHT.get(ast_u, 0.35)
        base_fp = 0.72 if bool(c.get("queue_front", True)) else 0.30
        fp = base_fp * w_ast
        if "ask_depth_usd" in c and float(c.get("ask_depth_usd") or 0.0) < 3.0:
            fp *= 0.35
    elif "queue_ahead_usd" in c and c.get("queue_ahead_usd") is not None:
        q_u = max(0.0, float(c.get("queue_ahead_usd") or 0.0))
        fp = 0.82 if q_u <= 5.0 else (0.68 if q_u <= 50.0 else (0.48 if q_u <= 125.0 else (0.28 if q_u <= 225.0 else 0.14)))
        if "ask_depth_usd" in c:
            _ask_d_u = max(0.0, float(c.get("ask_depth_usd") or 0.0))
            _vol_24_v = c.get("volume_24h_usd", c.get("volume24hr"))
            if _ask_d_u < 5.0 and _vol_24_v is not None and float(_vol_24_v or 0.0) < 500.0:
                fp *= 0.20
            elif _ask_d_u >= 10.0 and _vol_24_v is not None and float(_vol_24_v or 0.0) >= 1000.0:
                fp = min(0.95, fp * 1.15)
    else:
        fp = 0.65 if bool(c.get("queue_front", True)) else 0.22

    if compute_vel_fn is not None:
        return float(compute_vel_fn(edge_u, hold_c, fill_prob=fp, early_recycle_factor=recycle_f))
    return (edge_u * fp) / max(15.0, hold_c * recycle_f)


def spawn_fast_htm_maker_fill_reconcile(harvester: Any, trade_id: str) -> None:
    """
    Fast (`0.75s` cadence, `<= 10.5s`) ERC-1155 settlement poller for newly filled `BOND1` / `MKR_LOCK1` /
    `W_PRUNE1` positions so `0%`-fee Maker SELLs (`$0.998` / `$0.999`) hit `#1` FIFO ask priority in `< 3s`
    instead of waiting for the 15-30s supervision sweep.
    """
    if getattr(harvester, "dry_run", True):
        return
    pos0 = (getattr(harvester, "active_positions", None) or {}).get(trade_id)
    if not isinstance(pos0, Mapping):
        return
    sl_u = str(pos0.get("sleeve") or pos0.get("sleeve_source") or "").strip().upper()
    exp_ts = float(pos0.get("candle_expiry_ts", 0.0) or 0.0)
    sh0 = float(pos0.get("entry_shares", 0.0) or 0.0)
    now_chk = time.time()
    if (
        sl_u not in _HTM_PASSIVE_MAKER_RECYCLE_SLEEVES
        or sh0 < 5.0
        or ((exp_ts - now_chk) < 480.0 and not is_uma_post_expiry_recycle_safe(pos0, exp_ts - now_chk))
    ):
        return
    try:
        loop = asyncio.get_running_loop()
        on_loop_thread = True
    except RuntimeError:
        loop = getattr(harvester, "_main_loop", None)
        on_loop_thread = False
    if loop is None or not getattr(loop, "is_running", lambda: False)():
        return

    inflight = harvester.__dict__.setdefault("_fast_htm_reconcile_ids", set())
    if trade_id in inflight:
        return
    inflight.add(trade_id)

    async def _poll_and_post() -> None:
        try:
            onchain_src = getattr(harvester, "ONCHAIN_SOURCE", "ONCHAIN_ERC1155")
            for _ in range(14):
                await asyncio.sleep(0.75)
                pos = (getattr(harvester, "active_positions", None) or {}).get(trade_id)
                if not isinstance(pos, dict) or pos.get("exit_order_id") or pos.get("is_liquidating"):
                    return
                tok = str(pos.get("token_id") or "").strip()
                if not tok or not hasattr(harvester, "_wallet_token_balance"):
                    return
                if not pos.get("inventory_reconciled"):
                    bal, src = await asyncio.to_thread(harvester._wallet_token_balance, tok)
                    pre_b = max(0.0, float(pos.get("pre_token_balance", 0.0) or 0.0))
                    need_sh = max(0.0, float(pos.get("entry_shares", 0.0) or 0.0))
                    if (
                        bal is not None
                        and src in {onchain_src, "ONCHAIN_ERC1155", "POLYGON_ONCHAIN_ERC1155", "CLOB_BALANCE_API"}
                        and float(bal) >= max(pre_b + need_sh - 0.02, need_sh - 0.02)
                    ):
                        pos["inventory_reconciled"] = True
                        pos["status"] = "POSITION_CONFIRMED"
                        pos.setdefault("entry_inventory_source", src)
                        if hasattr(harvester, "save_state"):
                            harvester.save_state()
                if pos.get("inventory_reconciled"):
                    ex = getattr(harvester, "executor", None)
                    bk = await asyncio.to_thread(ex.get_market_book, tok) if (ex is not None and hasattr(ex, "get_market_book")) else {}
                    await maybe_manage_passive_htm_early_maker_recycle(
                        harvester, trade_id, pos, bk if isinstance(bk, Mapping) else {}, time.time()
                    )
                    return
        except Exception as exc:
            logger.debug(f"[FAST HTM RECONCILE] {trade_id} notice: {exc}")
        finally:
            inflight.discard(trade_id)

    def _start_task() -> None:
        t = loop.create_task(_poll_and_post())
        tasks = harvester.__dict__.setdefault("_fast_htm_reconcile_tasks", set())
        tasks.add(t)
        t.add_done_callback(tasks.discard)

    if on_loop_thread:
        _start_task()
    else:
        loop.call_soon_threadsafe(_start_task)


def spawn_fast_c1_complete_set_merge_reconcile(
    harvester: Any,
    box_id: str,
    leg_tids: Sequence[str],
) -> None:
    """
    Fast (`0.75s` cadence, `<= 12s`) post-fill ERC-1155 reconciliation + instant on-chain
    `CTF.mergePositions` trigger for same-condition `C1_BINARY_COMPLETE_SET` pairs so
    `1 YES + 1 NO -> $1.00 USDC.e` recycles in `~2.2-3.0s` instead of waiting for the
    `15-30s` supervision cycle.
    """
    if getattr(harvester, "dry_run", True) or len(leg_tids) != 2:
        return
    try:
        loop = asyncio.get_running_loop()
        on_loop_thread = True
    except RuntimeError:
        loop = getattr(harvester, "_main_loop", None)
        on_loop_thread = False
    if loop is None or not getattr(loop, "is_running", lambda: False)():
        return

    inflight = harvester.__dict__.setdefault("_fast_c1_merge_ids", set())
    if box_id in inflight:
        return
    inflight.add(box_id)
    tid_a, tid_b = str(leg_tids[0]), str(leg_tids[1])

    async def _poll_and_merge() -> None:
        try:
            onchain_src = getattr(harvester, "ONCHAIN_SOURCE", "POLYGON_ONCHAIN_ERC1155")
            for _ in range(16):
                await asyncio.sleep(0.75)
                act = getattr(harvester, "active_positions", None) or {}
                pa = act.get(tid_a)
                pb = act.get(tid_b)
                if not isinstance(pa, dict) or not isinstance(pb, dict):
                    return
                for p_leg in (pa, pb):
                    if not p_leg.get("inventory_reconciled") and hasattr(harvester, "_wallet_token_balance"):
                        tok_l = str(p_leg.get("token_id") or "").strip()
                        if tok_l:
                            bal_l, src_l = await asyncio.to_thread(harvester._wallet_token_balance, tok_l)
                            pre_l = max(0.0, float(p_leg.get("pre_token_balance", 0.0) or 0.0))
                            need_l = max(0.0, float(p_leg.get("entry_shares", 0.0) or 0.0))
                            if (
                                bal_l is not None
                                and src_l in {onchain_src, "CLOB_BALANCE_API"}
                                and float(bal_l) >= max(pre_l + need_l - 0.05, need_l - 0.05)
                            ):
                                p_leg["inventory_reconciled"] = True
                                p_leg["status"] = "POSITION_CONFIRMED"
                                p_leg.setdefault("entry_inventory_source", src_l)
                if pa.get("inventory_reconciled") and pb.get("inventory_reconciled"):
                    if hasattr(harvester, "save_state"):
                        await asyncio.to_thread(harvester.save_state)
                    if hasattr(harvester, "_maybe_merge_live_complete_sets"):
                        await harvester._maybe_merge_live_complete_sets(time.time())
                    if tid_a not in (getattr(harvester, "active_positions", None) or {}):
                        return
        except Exception as exc:
            logger.debug(f"[FAST C1 MERGE] {box_id} notice: {exc}")
        finally:
            inflight.discard(box_id)

    def _start_c1_task() -> None:
        t = loop.create_task(_poll_and_merge())
        tasks = harvester.__dict__.setdefault("_fast_c1_merge_tasks", set())
        tasks.add(t)
        t.add_done_callback(tasks.discard)

    if on_loop_thread:
        _start_c1_task()
    else:
        loop.call_soon_threadsafe(_start_c1_task)


def next_et_4h_boundary_ts(now_ts: float) -> int:
    """
    Computes the next `America/New_York` 4-hour candle close (`00:00, 04:00, 08:00, 12:00, 16:00, 20:00 ET`),
    automatically tracking EDT (`00/04/08/12/16/20 UTC`) and EST (`01/05/09/13/17/21 UTC`) across US DST!
    """
    dt_et = datetime.fromtimestamp(float(now_ts), tz=_ET_4H_TZ)
    if dt_et.hour % 4 == 0 and dt_et.minute == 0 and dt_et.second == 0 and dt_et.microsecond == 0:
        return int(round(float(now_ts)))
    slot_h = ((dt_et.hour // 4) + 1) * 4
    d_tgt = dt_et.date() + (timedelta(days=1) if slot_h >= 24 else timedelta(0))
    nxt_dt = datetime(d_tgt.year, d_tgt.month, d_tgt.day, slot_h % 24, 0, 0, tzinfo=_ET_4H_TZ)
    return int(round(nxt_dt.timestamp()))


def resolve_active_4h_target_end_ts(now_ts: float) -> Tuple[int, float]:
    """
    Returns `(target_end_ts, rem_sec)` for the active 4h overlap window (`[8.0, 905.0]`s remaining),
    preferring the true `America/New_York` 4h boundary while retaining `14400 * k` UTC fallback for
    synthetic epoch-aligned unit test fixtures.
    """
    et_end = next_et_4h_boundary_ts(now_ts)
    rem_et = float(et_end) - float(now_ts)
    if 8.0 <= rem_et <= 905.0:
        return et_end, rem_et
    utc_end = int(math.ceil(float(now_ts) / 14400.0) * 14400)
    rem_utc = float(utc_end) - float(now_ts)
    if 8.0 <= rem_utc <= 905.0:
        return utc_end, rem_utc
    return et_end, rem_et


def compute_min_4h_boundary_rem_sec(now_ts: float) -> float:
    _, rem = resolve_active_4h_target_end_ts(now_ts)
    return rem


def desired_market_ws_tokens_impl(harvester: Any, now_ts: Optional[float] = None) -> List[str]:
    import threading as _thr
    from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

    now_f = float(time.time() if now_ts is None else now_ts)
    toks: List[str] = [str(p.get("token_id") or "") for p in harvester.active_positions.values() if p.get("token_id")]
    for it in getattr(harvester, "pending_entry_intents", {}).values():
        if isinstance(it, dict):
            for tk_k in ("token_id", "opp_token_id"):
                tv = str(it.get(tk_k) or "").strip()
                if tv:
                    toks.append(tv)
    w_lock = harvester.__dict__.setdefault("_clinched_ws_lock", _thr.RLock())
    w_map = harvester.__dict__.setdefault("_clinched_ws_watchlist", {})
    rb_gov = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
    ws_obj = getattr(harvester, "_pos_market_ws", None)
    ws_shards = max(1, min(8, int(getattr(ws_obj, "num_shards", 1) or 1)))
    total_cap = int(getattr(ws_obj, "max_tokens", 490) or 490) if ws_shards > 1 else 490
    if w_map and bool(rb_gov.get("enable_ws_clinch_sniper", True)):
        per_shard_w = max(4, min(460, int(rb_gov.get("ws_clinch_watchlist_max_tokens", 450))))
        max_w_toks = min(max(4, total_cap - 40), per_shard_w * ws_shards)
        with w_lock:
            for tk_old, w_ent in list(w_map.items()):
                _sl_old = str(w_ent.get("sleeve_source") or "")
                _min_exp_pad = 3.5 if _sl_old in FAST_GUN_S2_SLEEVES else 5.0
                if float(w_ent.get("expiry_ts") or 0.0) <= now_f + _min_exp_pad or (now_f - float(w_ent.get("registered_ts") or 0.0)) > 14400.0:
                    w_map.pop(tk_old, None)
            ordered_w = sorted(w_map.values(), key=lambda x: max(1.0, float(x.get("expiry_ts") or (now_f + 86400.0)) - now_f))
            max_store_entries = max(900, max_w_toks // 2)
            if len(ordered_w) > max_store_entries:
                keep_tks = {str(x.get("leg_a_token_id") or "") for x in ordered_w[:max_store_entries]}
                for tk_drop in list(w_map.keys()):
                    if tk_drop not in keep_tks:
                        w_map.pop(tk_drop, None)
            ordered_w = ordered_w[: max(2, max_w_toks // 2)]
            for w_ent in ordered_w:
                for tk_w in (str(w_ent.get("leg_a_token_id") or ""), str(w_ent.get("leg_a_opp_token_id") or "")):
                    if tk_w:
                        toks.append(tk_w)
    if not getattr(harvester, "dry_run", True) or getattr(harvester, "_stage_b_decay_tracker", None) is not None:
        try:
            from src.polymarket_research.economic_attribution_ledger import GLOBAL_DECAY_TRACKER
            _trk_ws = getattr(harvester, "_stage_b_decay_tracker", None) or GLOBAL_DECAY_TRACKER
            for tk_d in _trk_ws.watched_token_ids(limit=64):
                toks.append(tk_d)
        except Exception:
            pass
    return list(dict.fromkeys(toks))[:total_cap]


def register_clinched_ws_watch_cand_impl(harvester: Any, cand: Dict[str, Any], now_ts: Optional[float] = None) -> bool:
    import threading as _thr
    from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

    rb_gov = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
    if not bool(rb_gov.get("enable_ws_clinch_sniper", True)) or check_sll_cand_dispute_guard(cand) is not None:
        return False
    now_f = float(time.time() if now_ts is None else now_ts)
    tok_a = str(cand.get("leg_a_token_id") or "").strip()
    opp_a = str(cand.get("leg_a_opp_token_id") or "").strip()
    mid_a = str(cand.get("leg_a_market_id") or "").strip()
    sl_src = str(cand.get("sleeve_source") or "BOND1_UMA_RESOLUTION_CARRY").strip()
    is_s2_w = sl_src in FAST_GUN_S2_SLEEVES
    from src.polymarket_research.stage_c_zero_loss_velocity import (
        check_strict_pure_riskless_candidate_gate,
        is_unmocked_live_clob_harvester,
    )
    if is_unmocked_live_clob_harvester(harvester):
        _paused_ws = {str(x).upper() for x in (rb_gov.get("paused_riskless_sleeves") or [])}
        if sl_src.upper() in _paused_ws or (is_s2_w and not bool(rb_gov.get("enable_s2_twap_lock_live", True))):
            return False
        if check_strict_pure_riskless_candidate_gate(harvester, cand, rb_gov, is_maker=False) is not None:
            return False
    p_mod = float(cand.get("p_model") or 0.0)
    exp_ts = float(cand.get("expiry_ts") or cand.get("leg_a_expiry_ts") or 0.0)
    min_rem_w = 4.2 if is_s2_w else 25.5
    if not tok_a or not opp_a or tok_a == opp_a or not mid_a or p_mod < 0.998 or exp_ts <= now_f + min_rem_w:
        return False
    max_eff = min(0.9975, max(0.950, float(cand.get("max_box_cost_net") or cand.get("max_resting_bid") or 0.994)))
    w_lock = harvester.__dict__.setdefault("_clinched_ws_lock", _thr.RLock())
    w_map = harvester.__dict__.setdefault("_clinched_ws_watchlist", {})
    cand_btype = str(cand.get("box_type") or "").strip().upper()
    with w_lock:
        prev_w = dict(w_map.get(tok_a) or {})
    if cand.get("leg_a_market_fee_rate") is not None:
        resolved_fr = max(0.0, float(cand.get("leg_a_market_fee_rate") or 0.0))
    elif cand_btype == "SINGLE_LEG_MAKER_LOCK":
        resolved_fr = max(0.0, float(prev_w.get("leg_a_fee_rate") or 0.0))
    else:
        resolved_fr = max(0.0, float(cand.get("leg_a_fee_rate") if cand.get("leg_a_fee_rate") is not None else (prev_w.get("leg_a_fee_rate") or 0.0)))
    evt_id_w = str(cand.get("event_id") or prev_w.get("event_id") or "").strip()
    evt_gk_w = extract_sll_event_group_key({**prev_w, **cand, "event_id": evt_id_w})
    w_rec: Dict[str, Any] = {
        "dedupe_key": str(cand.get("pair_dedupe_key") or cand.get("dedupe_key") or prev_w.get("dedupe_key") or f"WS_CLINCH_{mid_a}"),
        "pair_dedupe_key": str(cand.get("pair_dedupe_key") or prev_w.get("pair_dedupe_key") or ""),
        "event_id": evt_id_w,
        "event_group_key": evt_gk_w,
        "sleeve_source": sl_src,
        "asset": str(cand.get("asset") or prev_w.get("asset") or "CLINCH"),
        "expiry_ts": exp_ts,
        "max_box_cost_net": max_eff,
        "max_opp_bid": float(cand.get("max_opp_bid") or 0.025),
        "hold_to_maturity": bool(cand.get("hold_to_maturity", True)),
        "p_model": p_mod,
        "leg_a_token_id": tok_a,
        "leg_a_opp_token_id": opp_a,
        "leg_a_label": str(cand.get("leg_a_label") or prev_w.get("leg_a_label") or "CLINCH_WS_SNIPE")[:64],
        "leg_a_side": str(cand.get("leg_a_side") or "YES"),
        "leg_a_market_id": mid_a,
        "leg_a_condition_id": str(cand.get("leg_a_condition_id") or mid_a),
        "leg_a_fee_rate": resolved_fr,
        "leg_a_fee_exponent": float(cand.get("leg_a_fee_exponent") or prev_w.get("leg_a_fee_exponent") or 1.0),
        "leg_a_neg_risk": bool(cand.get("leg_a_neg_risk", False)),
        "registered_ts": now_f,
    }
    for meta_k in ("parent_event_id", "neg_risk_market_id", "event_slug", "question"):
        mv = str(cand.get(meta_k) or prev_w.get(meta_k) or "").strip()
        if mv:
            w_rec[meta_k] = mv
    for s2_k in ("strike_open", "leg_a_strike", "sigma_1h", "twap_locked_mean", "twap_locked_weight", "s2_min_sigma_cushion"):
        if s2_k in cand and cand.get(s2_k) is not None:
            w_rec[s2_k] = cand.get(s2_k)
    with w_lock:
        w_map[tok_a] = w_rec
    mkt_ws = getattr(harvester, "_pos_market_ws", None)
    if mkt_ws is not None:
        ws_bks_in = cand.get("ws_books")
        if hasattr(mkt_ws, "seed_book") and isinstance(ws_bks_in, Mapping):
            if isinstance(ws_bks_in.get(opp_a), Mapping):
                mkt_ws.seed_book(opp_a, dict(ws_bks_in[opp_a]))
            if isinstance(ws_bks_in.get(tok_a), Mapping):
                mkt_ws.seed_book(tok_a, dict(ws_bks_in[tok_a]))
        if hasattr(mkt_ws, "subscribe_tokens_immediate"):
            mkt_ws.subscribe_tokens_immediate([tok_a, opp_a])
    return True


def evaluate_clinched_ws_book_snipe_impl(
    harvester: Any, tok_id: str, bk_win: Optional[Dict[str, Any]] = None, now_ts: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    import threading as _thr
    from src.polymarket_research.holistic_strategy_governance import (
        GLOBAL_GOVERNANCE_MANAGER,
        passes_capital_velocity_hurdle,
    )

    rb_gov = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
    if not bool(rb_gov.get("enable_ws_clinch_sniper", True)):
        return None
    w_map = getattr(harvester, "_clinched_ws_watchlist", None)
    if not w_map:
        return None
    w_lock = harvester.__dict__.setdefault("_clinched_ws_lock", _thr.RLock())
    with w_lock:
        w_ent = dict(w_map.get(str(tok_id)) or {})
    if not w_ent:
        return None
    now_f = float(time.time() if now_ts is None else now_ts)
    exp_ts = float(w_ent.get("expiry_ts") or 0.0)
    rem_s = exp_ts - now_f
    sl_src_e = str(w_ent.get("sleeve_source") or "")
    is_s2_e = sl_src_e in FAST_GUN_S2_SLEEVES
    from src.polymarket_research.stage_c_zero_loss_velocity import (
        check_strict_pure_riskless_candidate_gate,
        is_unmocked_live_clob_harvester,
    )
    if is_unmocked_live_clob_harvester(harvester):
        _paused_wse = {str(x).upper() for x in (rb_gov.get("paused_riskless_sleeves") or [])}
        if sl_src_e.upper() in _paused_wse or (is_s2_e and not bool(rb_gov.get("enable_s2_twap_lock_live", True))):
            return None
        if check_strict_pure_riskless_candidate_gate(harvester, w_ent, rb_gov, is_maker=False) is not None:
            return None
    if rem_s < (4.2 if is_s2_e else 25.5) or (is_s2_e and rem_s > 38.5):
        return None
    if is_s2_e and check_s2_live_adverse_move_cancel(str(w_ent.get("asset") or ""), str(w_ent.get("leg_a_side") or "UP"), w_ent, exp_ts):
        return None
    cd_ws = harvester.__dict__.setdefault("_clinched_ws_snipe_cd", {})
    if float(cd_ws.get(str(tok_id), 0.0) or 0.0) > now_f:
        return None
    mid_ws = str(w_ent.get("leg_a_market_id") or "").strip()
    dk_ws = str(w_ent.get("dedupe_key") or "").strip()
    pdk_ws = str(w_ent.get("pair_dedupe_key") or "").strip()
    if mid_ws and is_market_busy_for_scaling(harvester, mid_ws):
        cd_ws[str(tok_id)] = now_f + 3.0
        return None
    if dk_ws and is_d1_dedupe_blocked(harvester, dk_ws, pdk_ws, [mid_ws] if mid_ws else [], now_f):
        cd_ws[str(tok_id)] = now_f + 3.0
        return None
    evt_ok_ws, _, evt_rem_ws, evt_gk_ws = check_per_event_concentration_cap(
        harvester, w_ent, market_ids=[mid_ws] if mid_ws else [], now_ts=now_f, min_headroom_usd=5.0
    )
    if not evt_ok_ws:
        cd_ws[str(tok_id)] = now_f + 5.0
        return None
    mkt_ws = getattr(harvester, "_pos_market_ws", None)
    if bk_win is None and mkt_ws is not None:
        try:
            bk_win = mkt_ws.get_book(str(tok_id), max_age_sec=2.0)
        except TypeError:
            bk_win = mkt_ws.get_book(str(tok_id))
    raw_asks = (bk_win or {}).get("asks") or []
    if not raw_asks:
        return None
    max_eff = float(w_ent["max_box_cost_net"])
    fr = float(w_ent.get("leg_a_fee_rate") or 0.0)
    fe = float(w_ent.get("leg_a_fee_exponent") or 1.0)
    lvls = sorted(
        [
            (
                float(x["price"] if isinstance(x, dict) else x[0]),
                float(x.get("size", 0.0) if isinstance(x, dict) else x[1]),
            )
            for x in raw_asks
            if float(x.get("size", 0.0) if isinstance(x, dict) else x[1]) > 0.0
        ],
        key=lambda r: r[0],
    )
    if not lvls or lvls[0][0] > max_eff + 0.0005 or lvls[0][0] < 0.50:
        return None
    opp_tok = str(w_ent["leg_a_opp_token_id"])
    bk_opp = None
    if mkt_ws is not None:
        try:
            bk_opp = mkt_ws.get_book(opp_tok, max_age_sec=3600.0)
        except TypeError:
            bk_opp = mkt_ws.get_book(opp_tok)
        if not isinstance(bk_opp, dict):
            return None
        if bool(bk_opp.get("is_partial_delta")) and not (bk_opp.get("bids") or []):
            return None
    if isinstance(bk_opp, dict):
        opp_bids = [
            float(x["price"] if isinstance(x, dict) else x[0])
            for x in (bk_opp.get("bids") or [])
            if float(x.get("size", 0.0) if isinstance(x, dict) else x[1]) > 0.0
        ]
        opp_b = max(opp_bids, default=0.0)
        if opp_b > float(w_ent.get("max_opp_bid") or 0.025) + 1e-6 or (lvls[0][0] + opp_b) > 1.015:
            return None
    max_ws_clip_u = min(25.0, float(evt_rem_ws))
    tot_sh, tot_cost, worst_px = 0.0, 0.0, lvls[0][0]
    for px, sz in lvls:
        eff_l = px + (fr * ((px * (1.0 - px)) ** fe) if (fr > 0.0 and 0.0 < px < 1.0) else 0.0)
        if eff_l > max_eff + 1e-6 or (px - lvls[0][0]) > 0.012:
            break
        rem_u = max(0.0, max_ws_clip_u - tot_cost)
        take_sh = min(sz, rem_u / max(eff_l, 0.01))
        if take_sh <= 1e-6:
            break
        tot_sh += take_sh
        tot_cost += take_sh * eff_l
        worst_px = px
        if tot_cost >= max_ws_clip_u - 0.05:
            break
    min_sh = max(5.0, float(rb_gov.get("partial_fak_min_shares", 5.0)))
    if tot_sh < min_sh - 1e-6 or (tot_sh * lvls[0][0]) < 4.90:
        return None
    eff_vwap = round(tot_cost / tot_sh, 5)
    p_mod = float(w_ent.get("p_model") or 1.0)
    if eff_vwap > max_eff + 1e-6 or (p_mod - eff_vwap) < 0.002 - 1e-6:
        return None
    collat_est = float(getattr(harvester, "_last_known_collateral", None) or 75.0)
    _liq_eq_ws = (
        collat_est
        + sum(
            float(_pw.get("notional_usd", 0.0) or 0.0)
            for _pw in (getattr(harvester, "active_positions", None) or {}).values()
            if isinstance(_pw, Mapping)
            and not position_is_settlement_receivable(_pw)
            and not is_post_expiry_uma_frozen_lock(_pw, now_f)
        )
        + pending_intents_synced_equity_usd(getattr(harvester, "pending_entry_intents", None))
    )
    vel_ok, _ = passes_capital_velocity_hurdle(
        box_type="SINGLE_LEG_LOCK",
        sleeve_src=str(w_ent["sleeve_source"]),
        collat_usd=max(25.0, _liq_eq_ws),
        rem_tte_sec=rem_s,
        box_cost_net=eff_vwap,
        fast_recycle_eligible=(
            (sl_src_e in _HTM_PASSIVE_MAKER_RECYCLE_SLEEVES and sl_src_e != "MKR_REWARD_LOCKED_CARRY")
            or not bool(w_ent.get("hold_to_maturity", True))
        ),
    )
    if not vel_ok:
        return None
    cd_ws[str(tok_id)] = now_f + 1.5
    cand_out: Dict[str, Any] = {
        "box_id": f"WS_SNIPE_{w_ent['asset']}_{int(now_f * 1000) % 1000000}",
        "dedupe_key": str(w_ent["dedupe_key"]),
        "pair_dedupe_key": str(w_ent.get("pair_dedupe_key") or ""),
        "event_id": str(w_ent.get("event_id") or ""),
        "event_group_key": str(evt_gk_ws or w_ent.get("event_group_key") or ""),
        "box_type": "SINGLE_LEG_LOCK",
        "ts_unix": round(now_f, 3),
        "asset": str(w_ent["asset"]),
        "regime": f"WS_CLINCH_SNIPE_{w_ent['leg_a_label'][:36]}",
        "pair_horizons": "single_leg_lock",
        "sleeve_source": str(w_ent["sleeve_source"]),
        "is_quiet_book": True,
        "allow_partial_fak": True,
        "expiry_ts": exp_ts,
        "rem_sec": round(rem_s, 2),
        "shares": int(math.floor(tot_sh)),
        "box_cost_net": eff_vwap,
        "max_box_cost_net": max_eff,
        "max_opp_bid": float(w_ent.get("max_opp_bid") or 0.025),
        "hold_to_maturity": bool(w_ent.get("hold_to_maturity", True)),
        "p_model": p_mod,
        "leg_a_token_id": str(tok_id),
        "leg_a_opp_token_id": opp_tok,
        "leg_a_label": str(w_ent["leg_a_label"]),
        "leg_a_side": str(w_ent["leg_a_side"]),
        "leg_a_horizon": "lock_1leg",
        "leg_a_market_id": str(w_ent["leg_a_market_id"]),
        "leg_a_condition_id": str(w_ent["leg_a_condition_id"]),
        "leg_a_strike": 0.0,
        "leg_a_limit_price": float(worst_px),
        "leg_a_avail_shares": round(tot_sh, 2),
        "leg_a_fee_rate": fr,
        "leg_a_fee_exponent": fe,
        "leg_a_neg_risk": bool(w_ent.get("leg_a_neg_risk", False)),
        "leg_a_expiry_ts": exp_ts,
    }
    for meta_k in ("parent_event_id", "neg_risk_market_id", "event_slug", "question"):
        if w_ent.get(meta_k):
            cand_out[meta_k] = w_ent[meta_k]
    for s2_k in ("strike_open", "leg_a_strike", "sigma_1h", "twap_locked_mean", "twap_locked_weight", "s2_min_sigma_cushion"):
        if s2_k in w_ent and w_ent.get(s2_k) is not None:
            cand_out[s2_k] = w_ent.get(s2_k)
    harvester.__dict__["_ws_clinch_snipe_emitted_count"] = int(harvester.__dict__.get("_ws_clinch_snipe_emitted_count", 0) or 0) + 1
    if isinstance(bk_opp, dict):
        cand_out["ws_books"] = {str(tok_id): _trim_ws_books_top10({"_": bk_win})["_"], opp_tok: _trim_ws_books_top10({"_": bk_opp})["_"]}
        cand_out["ws_books_ts"] = round(now_f, 3)
    if not getattr(harvester, "dry_run", True):
        try:
            from src.polymarket_research.economic_attribution_ledger import register_candidate_funnel_and_decay_watch
            register_candidate_funnel_and_decay_watch(cand_out, emit_funnel=True)
        except Exception:
            pass
    return cand_out


async def maybe_merge_live_complete_sets_impl(self: Any, now_ts: float, exec_status_cls: Any, h_logger: Any) -> None:
    import asyncio as _aio
    import os as _os

    if self.dry_run or not hasattr(self.executor, "attempt_onchain_complete_set_merge"):
        return
    sig_raw = getattr(self.executor, "signature_type", None)
    sig_t = 1 if sig_raw is None else int(sig_raw)
    if sig_t == 3 and not (_os.getenv("POLY_BUILDER_API_KEY") or _os.getenv("BUILDER_API_KEY")) and _os.getenv("PM_ENABLE_ONCHAIN_MERGE", "0") != "1":
        return
    seen_boxes: set[str] = set()
    merge_cd = self.__dict__.setdefault("_c1_merge_attempt_ts", {})
    merge_fail_cnt = self.__dict__.setdefault("_c1_merge_fail_count", {})
    ready_c1_entries: List[Dict[str, Any]] = []
    clinch_split_unmerged: List[Tuple[str, Dict[str, Any], float]] = []
    nr_convert_groups: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for tid, pos in list(self.active_positions.items()):
        if tid not in self.active_positions or not isinstance(pos, dict):
            continue
        pos_bt_u = str(pos.get("box_type") or "").upper()
        pos_sl_u = str(pos.get("sleeve") or pos.get("sleeve_source") or "").upper()
        if pos_bt_u == "CLINCH_DEAD_SPLIT_LOCK" and not pos.get("dead_leg_unwind_outcome_unknown"):
            unm_sp = float(pos.get("unmerged_dead_opp_shares", 0.0) or 0.0)
            if unm_sp >= 5.0 and str(pos.get("condition_id") or "").startswith("0x"):
                clinch_split_unmerged.append((tid, pos, unm_sp))
            continue
        if bool(pos.get("pending_negrisk_convert")):
            nr_b = str(pos.get("box_id") or tid)
            nr_convert_groups.setdefault(nr_b, []).append((tid, pos))
            continue
        is_comp_resid_pair = bool(pos.get("_comp_merge_pending_resid")) or str(tid).startswith("COMP_RESID_")
        if pos_bt_u != "COMPLETE_SET" and pos_sl_u != "C1_BINARY_COMPLETE_SET" and not is_comp_resid_pair:
            continue
        b_id = str(pos.get("box_id") or "")
        p_tid = str(pos.get("box_partner_trade_id") or "")
        partner = self.active_positions.get(p_tid)
        cid = str(pos.get("condition_id") or "")
        if (
            not b_id
            or b_id in seen_boxes
            or not isinstance(partner, dict)
            or not cid
            or cid != str(partner.get("condition_id") or "")
            or str(pos.get("token_id") or "") == str(partner.get("token_id") or "")
        ):
            continue
        seen_boxes.add(b_id)
        if (now_ts - float(merge_cd.get(b_id, 0.0) or 0.0)) < 2.5:
            continue
        if not (pos.get("inventory_reconciled") and partner.get("inventory_reconciled")):
            continue
        sh_1 = float(pos.get("remaining_shares", 0.0) or 0.0)
        sh_2 = float(partner.get("remaining_shares", 0.0) or 0.0)
        if min(sh_1, sh_2) < 5.0 or float(pos.get("filled_exit_shares", 0.0) or 0.0) > 0.01 or float(partner.get("filled_exit_shares", 0.0) or 0.0) > 0.01:
            continue
        if getattr(getattr(self.executor, "client", None), "_mock_children", None) is None and getattr(self.executor, "_mock_children", None) is None:
            wb_1, wb_2 = await _aio.gather(
                _aio.to_thread(self._wallet_token_balance, pos.get("token_id")),
                _aio.to_thread(self._wallet_token_balance, partner.get("token_id")),
            )
            if wb_1[1] == self.ONCHAIN_SOURCE and wb_2[1] == self.ONCHAIN_SOURCE and min(float(wb_1[0] or 0.0), float(wb_2[0] or 0.0)) < 5.0:
                merge_cd[b_id] = now_ts
                continue
        merge_cd[b_id] = now_ts
        cancel_aborted = False
        any_exit_canceled = False
        for lg_tid_c, lg_p in ((tid, pos), (p_tid, partner)):
            e_oid = lg_p.get("exit_order_id")
            if e_oid:
                c_r = await _aio.to_thread(self.executor.cancel_order, str(e_oid))
                s_r = await _aio.to_thread(self.executor.get_order_fill_summary, str(e_oid), lg_p.get("token_id"))
                if s_r is not None:
                    self._record_order_summary(lg_p, s_r, float(lg_p.get("target_exit_price", 0.99) or 0.99), taker=False)
                    if float(lg_p.get("remaining_shares", 0.0) or 0.0) <= 0.01:
                        self._close_position(lg_tid_c, lg_p, exec_status_cls.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                        cancel_aborted = True
                        break
                if not (c_r or {}).get("is_canceled") or float(lg_p.get("filled_exit_shares", 0.0) or 0.0) > 0.01:
                    if (c_r or {}).get("is_canceled"):
                        self.executor.release_inventory(reservation_id=str(e_oid))
                        lg_p["exit_order_id"] = None
                        lg_p["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
                        any_exit_canceled = True
                    cancel_aborted = True
                    break
                self.executor.release_inventory(reservation_id=str(e_oid))
                lg_p["exit_order_id"] = None
                lg_p["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
                any_exit_canceled = True
        if cancel_aborted:
            if any_exit_canceled:
                await _aio.to_thread(self.save_state)
            continue
        sh_1 = float(pos.get("remaining_shares", 0.0) or 0.0)
        sh_2 = float(partner.get("remaining_shares", 0.0) or 0.0)
        ready_c1_entries.append({
            "key": b_id, "tid": tid, "pos": pos, "p_tid": p_tid, "partner": partner,
            "cid": cid, "pairs": min(sh_1, sh_2), "neg_risk": pos.get("neg_risk"), "any_exit_canceled": any_exit_canceled,
        })

    batch_merged_map: Dict[str, Tuple[str, float]] = {}
    batch_fn = getattr(self.executor, "attempt_onchain_batch_complete_set_merges", None)
    if len(ready_c1_entries) >= 2 and callable(batch_fn):
        b_specs = [
            {"key": e["key"], "condition_id": e["cid"], "min_pairs": e["pairs"], "max_pairs": e["pairs"], "neg_risk": e["neg_risk"]}
            for e in ready_c1_entries
        ]
        b_out = await _aio.to_thread(batch_fn, b_specs)
        if isinstance(b_out, tuple) and len(b_out) == 2 and b_out[0] and isinstance(b_out[1], dict):
            tx_bh = str(b_out[0])
            for k_m, prs_m in b_out[1].items():
                if float(prs_m) >= 4.99:
                    batch_merged_map[str(k_m)] = (tx_bh, float(prs_m))

    for ent in ready_c1_entries:
        b_id = ent["key"]
        tid, pos, p_tid, partner, cid = ent["tid"], ent["pos"], ent["p_tid"], ent["partner"], ent["cid"]
        m_res = batch_merged_map.get(b_id)
        if m_res is None and not batch_merged_map:
            m_res = await _aio.to_thread(self.executor.attempt_onchain_complete_set_merge, cid, min_pairs=ent["pairs"], max_pairs=ent["pairs"])
        if isinstance(m_res, tuple) and len(m_res) == 2 and m_res[0] and float(m_res[1]) >= 4.99:
            tx_h, pairs_m = str(m_res[0]), float(m_res[1])
            merge_fail_cnt.pop(b_id, None)
            tot_c = max(0.01, float(pos.get("notional_usd", 0.0)) + float(partner.get("notional_usd", 0.0)))
            for lg_tid, lg_p in ((tid, pos), (p_tid, partner)):
                lg_p.pop("_comp_merge_pending_resid", None)
                share_w = float(lg_p.get("notional_usd", 0.0)) / tot_c
                cash_leg = round(pairs_m * share_w, 4)
                lg_p["merge_tx_hash"] = tx_h
                self.record_fill_and_update_position(lg_p, f"MERGE_{tx_h}_{lg_tid}", pairs_m, cash_leg, 0.0, cash_is_estimated=False)
                if float(lg_p.get("remaining_shares", 0.0) or 0.0) <= 0.02:
                    self._close_position(lg_tid, lg_p, exec_status_cls.SETTLED, "COMPLETE_SET_ONCHAIN_MERGED", won=True)
            from src.polymarket_research.riskless_machine_gun_engine import release_recycled_box_dedupe_keys
            release_recycled_box_dedupe_keys(self, pos, partner, cooldown_sec=2.0)
            self._pending_collateral_refresh = True
            await _aio.to_thread(self.save_state)
            h_logger.info(f"✓ [C1 COMPLETE SET MERGED] {b_id}: {pairs_m:.2f} pairs -> ${pairs_m:.2f} cash freed immediately (tx={tx_h}).")
        else:
            f_n = int(merge_fail_cnt.get(b_id, 0) or 0) + 1
            merge_fail_cnt[b_id] = f_n
            backoff_s = 20.0 if f_n <= 1 else (45.0 if f_n == 2 else 90.0)
            merge_cd[b_id] = now_ts + (backoff_s - 2.5)
            if ent["any_exit_canceled"]:
                await _aio.to_thread(self.save_state)

    # Step B: Retry deferred unmerged dead-leg pairs on CLINCH_SPLIT_* positions (never double-debits collateral!)
    for sp_tid, sp_pos, unm_q in clinch_split_unmerged:
        cd_k = f"SP_{sp_tid}"
        if (now_ts - float(merge_cd.get(cd_k, 0.0) or 0.0)) < 2.5:
            continue
        merge_cd[cd_k] = now_ts
        rem_w_cur = float(sp_pos.get("remaining_shares", 0.0) or 0.0)
        m_pairs = float(math.floor(min(unm_q, rem_w_cur) + 1e-9))
        if m_pairs < 5.0:
            continue
        sp_cid = str(sp_pos.get("condition_id") or "")
        m_sp = await _aio.to_thread(
            lambda _c=sp_cid, _p=m_pairs, _nr=sp_pos.get("neg_risk"): self.executor.attempt_onchain_complete_set_merge(
                _c, min_pairs=_p, max_pairs=_p, neg_risk=_nr
            )
        )
        if isinstance(m_sp, tuple) and len(m_sp) == 2 and m_sp[0] and float(m_sp[1]) >= 4.99:
            tx_sp, prs_sp = str(m_sp[0]), float(m_sp[1])
            merge_fail_cnt.pop(cd_k, None)
            rem_unm = round(max(0.0, unm_q - prs_sp), 4)
            if rem_unm > 0.01:
                sp_pos["unmerged_dead_opp_shares"] = rem_unm
            else:
                sp_pos.pop("unmerged_dead_opp_shares", None)
            rem_w_after = round(max(0.0, rem_w_cur - prs_sp), 4)
            cost_cur = float(sp_pos.get("notional_usd", rem_w_cur) or 0.0)
            cost_after = round(max(0.01, cost_cur - prs_sp), 4) if rem_w_after > 0.02 else 0.0
            sp_pos["merge_tx_hash"] = tx_sp
            if rem_w_after <= 0.02:
                sp_pos["remaining_shares"] = 0.0
                sp_pos["remaining_exit_shares"] = 0.0
                sp_pos["remaining_cost_basis"] = 0.0
                sp_pos["realized_exit_cash"] = round(float(sp_pos.get("realized_exit_cash", 0.0) or 0.0) + prs_sp, 4)
                sp_pos["confirmed_realized_cash"] = sp_pos["realized_exit_cash"]
                sp_pos["exit_cash_estimated"] = False
                self._close_position(sp_tid, sp_pos, exec_status_cls.SETTLED, "COMPLETE_SET_ONCHAIN_MERGED", won=True)
            else:
                sp_pos["entry_shares"] = rem_w_after
                sp_pos["remaining_shares"] = rem_w_after
                sp_pos["remaining_exit_shares"] = rem_w_after
                sp_pos["notional_usd"] = cost_after
                sp_pos["remaining_cost_basis"] = cost_after
                sp_pos["entry_price"] = round(cost_after / max(rem_w_after, 0.01), 5)
            if hasattr(self.executor, "invalidate_collateral_cache"):
                self.executor.invalidate_collateral_cache()
            self._pending_collateral_refresh = True
            lk_prev = getattr(self, "_last_known_collateral", None)
            synced_sp = False
            if hasattr(self.executor, "get_collateral_balance"):
                try:
                    nc_sp = await _aio.to_thread(self.executor.get_collateral_balance)
                    if isinstance(nc_sp, (int, float)) and not isinstance(nc_sp, bool) and math.isfinite(float(nc_sp)) and float(nc_sp) >= 0.0:
                        self._last_known_collateral = (
                            max(float(nc_sp), round(float(lk_prev) + prs_sp, 4))
                            if (isinstance(lk_prev, (int, float)) and not isinstance(lk_prev, bool) and abs(float(nc_sp) - float(lk_prev)) < 0.05)
                            else float(nc_sp)
                        )
                        synced_sp = True
                except Exception:
                    pass
            if not synced_sp and isinstance(lk_prev, (int, float)) and not isinstance(lk_prev, bool):
                self._last_known_collateral = round(float(lk_prev) + prs_sp, 4)
            await _aio.to_thread(self.save_state)
        else:
            f_sp = int(merge_fail_cnt.get(cd_k, 0) or 0) + 1
            merge_fail_cnt[cd_k] = f_sp
            backoff_sp = 20.0 if f_sp <= 1 else (45.0 if f_sp == 2 else 90.0)
            merge_cd[cd_k] = now_ts + (backoff_sp - 2.5)

    # Step C: Retry deferred NegRiskAdapter.convertPositions on unconverted HOLD_NO_* baskets ([S-06])
    conv_fn = getattr(self.executor, "attempt_negrisk_convert_positions", None)
    if callable(conv_fn) and nr_convert_groups:
        for nr_b, grp in nr_convert_groups.items():
            cd_nr = f"NRC_{nr_b}"
            if (now_ts - float(merge_cd.get(cd_nr, 0.0) or 0.0)) < 2.5:
                continue
            exp_n = int(grp[0][1].get("box_expected_legs") or len(grp))
            nrm_id = str(grp[0][1].get("neg_risk_market_id") or "")
            if len(grp) != exp_n or not nrm_id or any(p.get("question_index") is None for _, p in grp):
                continue
            min_sh_nr = float(math.floor(min(float(p.get("remaining_shares", 0.0) or 0.0) for _, p in grp) + 1e-9))
            if min_sh_nr < 5.0:
                continue
            merge_cd[cd_nr] = now_ts
            q_idxs = [int(p["question_index"]) for _, p in grp]
            try:
                c_out = await _aio.to_thread(lambda _m=nrm_id, _q=q_idxs, _s=min_sh_nr: conv_fn(_m, _q, _s, prefer_v2_pusd_adapter=True))
            except TypeError:
                c_out = await _aio.to_thread(conv_fn, nrm_id, q_idxs, min_sh_nr)
            if isinstance(c_out, Mapping) and c_out.get("success"):
                merge_fail_cnt.pop(cd_nr, None)
                fee_bips_nr = int(grp[0][1].get("convert_fee_bips", 0) or 0)
                eff_m_nr = 1.0 - max(0, fee_bips_nr) / 10000.0
                conv_cash_u = float(max(0, len(grp) - 1)) * min_sh_nr * eff_m_nr
                yes_sells_nr = []
                for _, p_g in grp:
                    if p_g.get("pending_liquid_yes_sells"):
                        yes_sells_nr = list(p_g["pending_liquid_yes_sells"])
                        break
                yes_net_u = 0.0
                if yes_sells_nr and hasattr(self.executor, "execute_unwind_order"):
                    for yl in yes_sells_nr:
                        y_tok = str(yl.get("yes_token") or yl.get("token_id") or "")
                        if not y_tok:
                            continue
                        min_b = max(0.01, round(float(yl.get("min_bid_price") or yl.get("bid_vwap") or 0.02) - 0.01, 2))
                        ys_r = await _aio.to_thread(
                            lambda _yt=y_tok, _mb=min_b, _sh=min_sh_nr: self.executor.execute_unwind_order(
                                _yt, size=_sh, side="SELL", min_price=_mb, neg_risk=True
                            )
                        )
                        if isinstance(ys_r, Mapping) and (ys_r.get("success") or ys_r.get("partial")) and not ys_r.get("outcome_unknown"):
                            m_y = float(ys_r.get("matched_size") or 0.0)
                            tk_y = float(ys_r.get("taking_amount") or (m_y * float(ys_r.get("price") or min_b)))
                            f_y = float(ys_r.get("fee_usd") or 0.0)
                            yes_net_u += max(0.0, tk_y - f_y)
                tot_proceeds_nr = round(conv_cash_u + yes_net_u, 4)
                tot_cost_nr = max(0.01, sum(float(p.get("notional_usd", 0.0) or 0.0) for _, p in grp))
                tx_nr = str(c_out.get("tx_hash") or "0xnrconv")
                for g_tid, g_pos in grp:
                    g_pos.pop("pending_negrisk_convert", None)
                    g_pos["convert_tx_hash"] = tx_nr
                    w_nr = float(g_pos.get("notional_usd", 0.0) or 0.0) / tot_cost_nr
                    leg_cash = round(tot_proceeds_nr * w_nr, 4)
                    self.record_fill_and_update_position(g_pos, f"NRCONV_{tx_nr}_{g_tid}", min_sh_nr, leg_cash, 0.0, cash_is_estimated=False)
                    if float(g_pos.get("remaining_shares", 0.0) or 0.0) <= 0.02:
                        self._close_position(g_tid, g_pos, exec_status_cls.SETTLED, "ONCHAIN_NEGRISK_CONVERT_COMPLETED", won=True)
                if hasattr(self.executor, "invalidate_collateral_cache"):
                    self.executor.invalidate_collateral_cache()
                self._pending_collateral_refresh = True
                await _aio.to_thread(self.save_state)
            else:
                f_nr = int(merge_fail_cnt.get(cd_nr, 0) or 0) + 1
                merge_fail_cnt[cd_nr] = f_nr
                backoff_nr = 20.0 if f_nr <= 1 else (45.0 if f_nr == 2 else 90.0)
                merge_cd[cd_nr] = now_ts + (backoff_nr - 2.5)


async def execute_guarded_complement_merge_impl(
    self: Any, tid: str, pos: Dict[str, Any], opp_tok: str, cm_plan: Dict[str, Any], now_ts: float, exec_status_cls: Any
) -> bool:
    import asyncio as _aio

    if self.dry_run or not opp_tok or not hasattr(self.executor, "attempt_onchain_complete_set_merge"):
        return False
    if pos.get("_comp_merge_pending_resid"):
        return False
    cid = str(pos.get("condition_id") or "")
    exit_oid = pos.get("exit_order_id")
    if not cid or not exit_oid:
        return False
    buy_fn = getattr(self.executor, "buy_complement_leg_fak", None)
    if not callable(buy_fn):
        return False
    _is_live_ex = (
        getattr(self.executor, "_mock_children", None) is None
        and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
    )

    def _is_cancel_confirmed(c_obj: Any, oid_str: str) -> bool:
        return bool(
            (c_obj.get("is_canceled") or oid_str in (c_obj.get("canceled") or []))
            if isinstance(c_obj, Mapping)
            else (getattr(c_obj, "is_canceled", False) or oid_str in (getattr(c_obj, "canceled", None) or []))
        )

    req_opp_sh = float(cm_plan["req_opp_shares"])
    if _is_live_ex:
        # [S-03] Cancel and reconcile resting Maker exit BEFORE buying losing complement to eliminate dual-fill stranding!
        c_r_pre = await _aio.to_thread(self.executor.cancel_order, str(exit_oid))
        s_r_pre = await _aio.to_thread(self.executor.get_order_fill_summary, str(exit_oid), pos.get("token_id"))
        if s_r_pre is not None:
            self._record_order_summary(pos, s_r_pre, float(pos.get("target_exit_price", 0.98) or 0.98), taker=False)
        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
            self._close_position(tid, pos, exec_status_cls.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
            await _aio.to_thread(self.save_state)
            return True
        if not _is_cancel_confirmed(c_r_pre, str(exit_oid)):
            return False
        if hasattr(self.executor, "release_inventory"):
            self.executor.release_inventory(reservation_id=str(exit_oid))
        pos["exit_order_id"] = None
        pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
        req_opp_sh = min(req_opp_sh, float(pos.get("remaining_shares", 0.0) or 0.0))
        if req_opp_sh < 5.0:
            await _aio.to_thread(self.save_state)
            return False

    pre_opp_bal = 0.0
    if _is_live_ex and hasattr(self, "_wallet_token_balance"):
        try:
            _rb_o = await _aio.to_thread(self._wallet_token_balance, opp_tok)
            pre_opp_bal = float((_rb_o[0] if isinstance(_rb_o, tuple) else _rb_o) or 0.0)
        except Exception:
            pre_opp_bal = 0.0
    opp_res = await _aio.to_thread(
        buy_fn, opp_tok, float(cm_plan["opp_ask"]), req_opp_sh, str(cm_plan["tick_size"]), bool(pos.get("neg_risk")),
    )
    filled_opp = float((opp_res or {}).get("matched_shares") or 0.0)
    opp_cost = (
        float((opp_res or {}).get("cost_usd") or 0.0)
        if float((opp_res or {}).get("cost_usd") or 0.0) > 0.0
        else round(filled_opp * float(cm_plan.get("opp_ask") or 0.01), 4)
    )

    def _track_unmerged_opp(unmerged_sh: float, primary_open: bool) -> None:
        if unmerged_sh < 0.05 or not isinstance(getattr(self, "active_positions", None), dict):
            return
        resid_id = f"COMP_RESID_{tid}_{int(now_ts)}"
        unit_px = round(opp_cost / max(filled_opp, 0.01), 5)
        resid_notional = round(unmerged_sh * unit_px, 4)
        resid_pos: Dict[str, Any] = {
            "trade_id": resid_id,
            "market_id": str(pos.get("market_id") or ""),
            "condition_id": cid,
            "token_id": str(opp_tok),
            "opp_token_id": str(pos.get("token_id") or ""),
            "target_token": "DOWN" if str(pos.get("target_token") or "").upper() == "UP" else ("NO" if str(pos.get("target_token") or "").upper() == "YES" else "OPP"),
            "asset": str(pos.get("asset") or ""),
            "sleeve": str(pos.get("sleeve") or "COMP_MERGE_RESID"),
            "neg_risk": bool(pos.get("neg_risk")),
            "entry_shares": round(unmerged_sh, 4),
            "remaining_shares": round(unmerged_sh, 4),
            "filled_exit_shares": 0.0,
            "entry_price": unit_px,
            "notional_usd": resid_notional,
            "fee_usd": 0.0,
            "inventory_reconciled": True,
            "candle_expiry_ts": float(pos.get("candle_expiry_ts", now_ts + 900.0) or (now_ts + 900.0)),
            "entry_ts": now_ts,
            "status": "ACTIVE_HOLD",
        }
        if primary_open and tid in self.active_positions:
            box_id_cm = str(pos.get("box_id") or f"COMP_BOX_{tid}")
            resid_pos["is_dominance_box"] = True
            resid_pos["box_id"] = box_id_cm
            resid_pos["box_partner_trade_id"] = tid
            resid_pos["hold_to_maturity"] = True
            pos["is_dominance_box"] = True
            pos["box_id"] = box_id_cm
            pos["box_partner_trade_id"] = resid_id
            pos["_comp_merge_pending_resid"] = resid_id
        else:
            resid_pos["is_dominance_box"] = False
            resid_pos["hold_to_maturity"] = False
            resid_pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
            pos["_comp_merge_pending_resid"] = resid_id
        self.active_positions[resid_id] = resid_pos
        if getattr(self, "_last_known_collateral", None) is not None:
            self._last_known_collateral = max(0.0, float(self._last_known_collateral) - resid_notional)
        self._pending_collateral_refresh = True

    if not (opp_res or {}).get("success") or filled_opp < 5.0:
        if filled_opp >= 0.05:
            _track_unmerged_opp(filled_opp, primary_open=True)
            await _aio.to_thread(self.save_state)
        elif _is_live_ex:
            await _aio.to_thread(self.save_state)
        return False

    if not _is_live_ex:
        c_r = await _aio.to_thread(self.executor.cancel_order, str(exit_oid))
        s_r = await _aio.to_thread(self.executor.get_order_fill_summary, str(exit_oid), pos.get("token_id"))
        if s_r is not None:
            self._record_order_summary(pos, s_r, float(pos.get("target_exit_price", 0.98) or 0.98), taker=False)
        if float(pos.get("remaining_shares", 0.0) or 0.0) <= 0.01:
            _track_unmerged_opp(filled_opp, primary_open=False)
            self._close_position(tid, pos, exec_status_cls.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
            await _aio.to_thread(self.save_state)
            return True
        if not _is_cancel_confirmed(c_r, str(exit_oid)):
            _track_unmerged_opp(filled_opp, primary_open=True)
            await _aio.to_thread(self.save_state)
            return False
        self.executor.release_inventory(reservation_id=str(exit_oid))
        pos["exit_order_id"] = None
        pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"

    pairs = min(float(pos.get("remaining_shares", 0.0) or 0.0), filled_opp)
    if pairs < 4.99:
        _track_unmerged_opp(filled_opp, primary_open=True)
        await _aio.to_thread(self.save_state)
        return False
    if _is_live_ex:
        try:
            from src.polymarket_research.riskless_machine_gun_engine import wait_for_erc1155_delivery

            await _aio.to_thread(
                lambda: wait_for_erc1155_delivery(
                    self.executor,
                    [opp_tok],
                    pre_opp_bal + pairs,
                    timeout_sec=6.0,
                    poll_sec=0.30,
                )
            )
        except Exception:
            pass
    m_res = await _aio.to_thread(self.executor.attempt_onchain_complete_set_merge, cid, min_pairs=pairs, max_pairs=pairs)
    if isinstance(m_res, tuple) and len(m_res) == 2 and m_res[0] and float(m_res[1]) >= 4.99:
        tx_h, pairs_m = str(m_res[0]), float(m_res[1])
        pos["merge_tx_hash"] = tx_h
        merged_opp_cost = round(opp_cost * min(1.0, pairs_m / max(filled_opp, 0.01)), 4)
        self.record_fill_and_update_position(pos, f"COMP_MERGE_{tx_h}_{tid}", pairs_m, round(max(0.01, pairs_m - merged_opp_cost), 4), 0.0, cash_is_estimated=False)
        still_open = float(pos.get("remaining_shares", 0.0) or 0.0) > 0.02
        if not still_open:
            self._close_position(tid, pos, exec_status_cls.SETTLED, "SYNTHETIC_COMPLEMENT_MERGED", won=True)
        if filled_opp - pairs_m >= 0.05:
            _track_unmerged_opp(round(filled_opp - pairs_m, 4), primary_open=still_open)
        self._pending_collateral_refresh = True
        await _aio.to_thread(self.save_state)
        return True
    _track_unmerged_opp(filled_opp, primary_open=True)
    await _aio.to_thread(self.save_state)
    return False


async def try_atomic_box_overround_unwind_impl(
    self: Any,
    now_ts: float,
    open_oids: Set[str],
    *,
    pos_is_recv_fn: Any,
    read_fast_tick_fn: Any,
    walk_ovr_fn: Any,
    gov_mgr: Any,
    exec_status_cls: Any,
    h_logger: Any,
) -> None:
    import asyncio as _aio

    if self.dry_run or not hasattr(self.executor, "execute_atomic_box_overround_unwind"):
        return
    seen_boxes: Set[str] = set()
    ovr_cd = self.__dict__.setdefault("_ovr_unwind_cd", {})
    mkt_ws = getattr(self, "_pos_market_ws", None)
    for tid, pos in list(self.active_positions.items()):
        if tid not in self.active_positions or not pos.get("is_dominance_box"):
            continue
        b_id = str(pos.get("box_id") or "")
        p_tid = str(pos.get("box_partner_trade_id") or "")
        partner = self.active_positions.get(p_tid)
        if (
            not b_id or b_id in seen_boxes or not isinstance(partner, dict)
            or pos_is_recv_fn(pos) or pos_is_recv_fn(partner)
            or pos.get("is_liquidating") or partner.get("is_liquidating")
            or not (pos.get("inventory_reconciled") and partner.get("inventory_reconciled"))
            or now_ts < float(ovr_cd.get(b_id, 0.0) or 0.0)
        ):
            continue
        seen_boxes.add(b_id)
        tte_rem = min(float(pos.get("candle_expiry_ts", now_ts + 600.0)) - now_ts, float(partner.get("candle_expiry_ts", now_ts + 600.0)) - now_ts)
        sh_a = float(pos.get("remaining_shares", 0.0) or 0.0)
        sh_b = float(partner.get("remaining_shares", 0.0) or 0.0)
        pairs = round(min(sh_a, sh_b), 2)
        if tte_rem < 12.0 or pairs < 5.0 or abs(sh_a - sh_b) > 0.05:
            continue
        tok_a, tok_b = str(pos.get("token_id") or ""), str(partner.get("token_id") or "")
        bk_a = self._get_verified_shm_book(pos) or (mkt_ws.get_book(tok_a, max_age_sec=2.0) if mkt_ws else None)
        bk_b = self._get_verified_shm_book(partner) or (mkt_ws.get_book(tok_b, max_age_sec=2.0) if mkt_ws else None)
        if (bk_a is None or bk_b is None) and (now_ts - float(pos.get("_ovr_rest_ts", 0.0) or 0.0)) >= 2.0:
            pos["_ovr_rest_ts"] = now_ts
            if bk_a is None and tok_a:
                bk_a = await self.executor.get_market_book_async(tok_a)
            if bk_b is None and tok_b:
                bk_b = await self.executor.get_market_book_async(tok_b)
        if not isinstance(bk_a, dict) or not isinstance(bk_b, dict):
            continue
        fr_a, fe_a = self._exit_taker_fee_rate(pos), float(pos.get("fee_exponent_applied", 1.0) or 1.0)
        fr_b, fe_b = self._exit_taker_fee_rate(partner), float(partner.get("fee_exponent_applied", fe_a) or 1.0)
        from src.polymarket_research.riskless_machine_gun_engine import (
            compute_dynamic_box_unwind_hurdle,
            evaluate_cross_condition_complement_merge,
            execute_cross_condition_complement_merge,
            release_recycled_box_dedupe_keys,
        )
        _ft_ovr = read_fast_tick_fn(str(pos.get("asset") or "")) if callable(read_fast_tick_fn) else None
        _spot_ovr = float((_ft_ovr or {}).get("spot_price") or pos.get("current_spot") or 0.0) or None
        if (
            gov_mgr.snapshot.get("riskless_boxes", {}).get("enable_cross_condition_complement_merge", True)
            and pos.get("opp_token_id") and partner.get("opp_token_id")
            and str(pos.get("condition_id") or "") != str(partner.get("condition_id") or "")
        ):
            _oa, _ob = str(pos["opp_token_id"]), str(partner["opp_token_id"])
            _bko_a = mkt_ws.get_book(_oa, max_age_sec=2.5) if mkt_ws else None
            _bko_b = mkt_ws.get_book(_ob, max_age_sec=2.5) if mkt_ws else None
            if (_bko_a is None or _bko_b is None) and (now_ts - float(pos.get("_ccm_rest_ts", 0.0) or 0.0)) >= 6.0:
                pos["_ccm_rest_ts"] = now_ts
                _bko_a = _bko_a or await self.executor.get_market_book_async(_oa)
                _bko_b = _bko_b or await self.executor.get_market_book_async(_ob)
            _ccm = evaluate_cross_condition_complement_merge(pos, partner, _bko_a, _bko_b, pairs, tte_rem=tte_rem, current_spot=_spot_ovr)
            if _ccm is not None:
                ovr_cd[b_id] = now_ts + 2.0
                if await execute_cross_condition_complement_merge(self, tid, pos, p_tid, partner, _ccm, open_oids, now_ts):
                    continue
        walk = walk_ovr_fn(bk_a.get("bids") or [], bk_b.get("bids") or [], pairs, fr_a, fe_a, fr_b, fe_b, 1.25)
        if not walk.get("fillable"):
            continue
        req_net = compute_dynamic_box_unwind_hurdle(pos, partner, tte_rem, _spot_ovr)
        if float(walk.get("net_sum_per_share", 0.0)) < req_net:
            continue
        ovr_cd[b_id] = now_ts + 2.0
        e_oids = [str(lg.get("exit_order_id")) for lg in (pos, partner) if lg.get("exit_order_id")]
        batch_c = await _aio.to_thread(self.executor.cancel_orders_batch, e_oids) if len(e_oids) == 2 and hasattr(self.executor, "cancel_orders_batch") else None
        abort_u = False
        for lg_tid, lg_p in ((tid, pos), (p_tid, partner)):
            e_oid = lg_p.get("exit_order_id")
            if not e_oid:
                continue
            if isinstance(batch_c, Mapping) and str(e_oid) in batch_c and (isinstance(batch_c[str(e_oid)], Mapping) or hasattr(batch_c[str(e_oid)], "is_canceled")):
                c_r = batch_c[str(e_oid)]
            elif isinstance(batch_c, Mapping) and ("is_canceled" in batch_c or "canceled" in batch_c):
                c_r = batch_c
            elif hasattr(batch_c, "is_canceled"):
                c_r = batch_c
            else:
                c_r = await _aio.to_thread(self.executor.cancel_order, str(e_oid))
            s_r = await _aio.to_thread(self.executor.get_order_fill_summary, str(e_oid), lg_p.get("token_id"))
            if s_r is not None:
                self._record_order_summary(lg_p, s_r, float(lg_p.get("target_exit_price", 0.99) or 0.99), taker=False)
                if float(lg_p.get("remaining_shares", 0.0) or 0.0) <= 0.02:
                    self._close_position(lg_tid, lg_p, exec_status_cls.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
                    abort_u = True
                    break
            if isinstance(c_r, Mapping):
                is_c = bool(c_r.get("is_canceled") or str(e_oid) in (c_r.get("canceled") or []))
            else:
                is_c = bool(getattr(c_r, "is_canceled", False) or str(e_oid) in (getattr(c_r, "canceled", None) or []))
            if not is_c or float(lg_p.get("filled_exit_shares", 0.0) or 0.0) > 0.01:
                if is_c:
                    open_oids.discard(str(e_oid))
                    self.executor.release_inventory(reservation_id=str(e_oid))
                    lg_p["exit_order_id"] = None
                    lg_p["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
                abort_u = True
                break
            open_oids.discard(str(e_oid))
            self.executor.release_inventory(reservation_id=str(e_oid))
            lg_p["exit_order_id"] = None
            lg_p["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
        if abort_u:
            await _aio.to_thread(self.save_state)
            continue
        min_a = max(0.01, round(float(walk["min_px_a"]) - 0.01, 4))
        min_b = max(0.01, round(float(walk["min_px_b"]) - 0.01, 4))
        u_res = await _aio.to_thread(
            self.executor.execute_atomic_box_overround_unwind,
            b_id, tok_a, min_a, tok_b, min_b, pairs,
            bool(pos.get("neg_risk", False)), bool(partner.get("neg_risk", False)),
            fr_a, fe_a, fr_b, fe_b,
        )
        both_ok = bool((u_res or {}).get("success"))
        close_tag = "EARLY_OVERROUND_BID_UNWIND" if both_ok else "BOX_EARLY_BID_HARVEST"
        any_matched = False
        for lg_tid, lg_p, lg_key, lg_min in ((tid, pos, "leg_a", min_a), (p_tid, partner, "leg_b", min_b)):
            lr = dict((u_res or {}).get(lg_key) or {})
            if lr.get("filled") or lr.get("outcome_unknown"):
                lr["success"] = bool(lr.get("filled"))
                out_l = self._handle_unwind_response(lg_tid, lg_p, lr, pairs, close_tag, "PARTIAL_UNWIND_REMAINING", lg_min)
                if out_l != "FAILED":
                    any_matched = True
            elif lg_tid in self.active_positions and not lg_p.get("exit_order_id"):
                lg_p["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
        if any_matched and not both_ok:
            for surv_tid, surv_p in ((tid, pos), (p_tid, partner)):
                if surv_tid in self.active_positions and not surv_p.get("exit_order_id"):
                    surv_p["is_dominance_box"] = False
                    surv_p["is_legged_out_residual"] = True
                    surv_p["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
                    surv_p["next_unwind_retry_ts"] = now_ts
                    h_logger.warning(f"[OVERROUND ASYMMETRIC UNWIND] {b_id}: partner leg exited while {surv_tid} remained open; arming immediate supervised residual unwind.")
        if any_matched:
            if both_ok:
                release_recycled_box_dedupe_keys(self, pos, partner, cooldown_sec=2.0)
            self.executor.invalidate_collateral_cache()
            self._pending_collateral_refresh = True
            h_logger.info(f"✓ [ATOMIC OVERROUND UNWIND] {b_id}: {pairs:.2f} pairs recycled @ net_sum=${walk['net_sum_per_share']:.4f} (both={both_ok}).")
        await _aio.to_thread(self.save_state)


def update_shadow_phase4_monotonicity_scanner_impl(
    self: Any,
    shock: Dict[str, Any],
    asset_str: str,
    is_subhourly: bool,
    is_1h: bool,
    tte: float,
    open_spot: float,
    *,
    eval_basis_fn: Any,
    h_logger: Any,
) -> None:
    try:
        if not (is_subhourly or is_1h) or not (20.0 <= tte <= 900.0) or not open_spot or open_spot <= 0.0:
            return
        now_ts = float(shock.get("t0_unix") or time.time())
        exp_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (now_ts + tte))
        exp_bucket = int(round(exp_ts / 60.0) * 60)
        feats = shock.get("pre_shock_features_t0") or {}
        up_tf, dn_tf = feats.get("UP") or {}, feats.get("DOWN") or {}
        up_a, dn_a = float(up_tf.get("best_ask") or 0.0), float(dn_tf.get("best_ask") or 0.0)
        if up_a <= 0.0 or dn_a <= 0.0:
            return
        up_asks, dn_asks = up_tf.get("raw_top_asks") or [], dn_tf.get("raw_top_asks") or []
        up_l1_usd = (float(up_asks[0][0]) * float(up_asks[0][1])) if up_asks else 0.0
        dn_l1_usd = (float(dn_asks[0][0]) * float(dn_asks[0][1])) if dn_asks else 0.0
        spot_px = float(shock.get("spot_at_t0") or shock.get("trigger_price") or open_spot)

        cache = getattr(self, "_shadow_phase4_books", None)
        if cache is None:
            self._shadow_phase4_books = cache = {}
        emitted = getattr(self, "_shadow_phase4_emitted", None)
        if emitted is None:
            self._shadow_phase4_emitted = emitted = set()

        h_key = "15m" if is_subhourly else "1h"
        bucket_dict = cache.setdefault((asset_str, exp_bucket), {})
        bucket_dict[h_key] = {
            "ts": now_ts, "tte": tte, "market_id": str(shock.get("market_id") or ""), "strike": float(open_spot),
            "spot": spot_px, "up_a": up_a, "dn_a": dn_a, "up_l1_usd": up_l1_usd, "dn_l1_usd": dn_l1_usd,
            "up_asks": [{"price": float(p), "size": float(s)} for p, s in up_asks if float(p) > 0 and float(s) > 0],
            "dn_asks": [{"price": float(p), "size": float(s)} for p, s in dn_asks if float(p) > 0 and float(s) > 0],
        }
        s15, s1h = bucket_dict.get("15m"), bucket_dict.get("1h")
        if not s15 or not s1h or abs(s15["ts"] - s1h["ts"]) > 10.0:
            return
        k15, k1h = s15["strike"], s1h["strike"]
        if abs(k15 - k1h) / max(k15, 1.0) < 0.0003:
            return
        if k15 < k1h:
            leg1_lbl, leg1_px, leg1_depth, leg1_asks = "UP_15M", s15["up_a"], s15["up_l1_usd"], s15.get("up_asks") or []
            leg2_lbl, leg2_px, leg2_depth, leg2_asks = "DOWN_1H", s1h["dn_a"], s1h["dn_l1_usd"], s1h.get("dn_asks") or []
            k_low, k_high = k15, k1h
        else:
            leg1_lbl, leg1_px, leg1_depth, leg1_asks = "UP_1H", s1h["up_a"], s1h["up_l1_usd"], s1h.get("up_asks") or []
            leg2_lbl, leg2_px, leg2_depth, leg2_asks = "DOWN_15M", s15["dn_a"], s15["dn_l1_usd"], s15.get("dn_asks") or []
            k_low, k_high = k1h, k15

        from src.polymarket_research.same_oracle_dominance_box import walk_equal_shares_dominance_box
        walk_res = walk_equal_shares_dominance_box(
            leg1_asks, leg2_asks, target_budget_usd=25.0, fee_rate_a=0.07, fee_rate_b=0.07, max_box_cost_net=1.08, min_shares=8, min_box_notional_usd=7.0,
        )
        if not walk_res.get("filled"):
            return
        c_taker = float(walk_res["box_cost_net"])
        leg1_w, leg2_w = walk_res["leg_a_walk"], walk_res["leg_b_walk"]
        m1, m2 = max(0.01, leg1_px - 0.01), max(0.01, leg2_px - 0.01)
        c_maker = (m1 - 0.014 * m1 * (1.0 - m1)) + (m2 - 0.014 * m2 * (1.0 - m2))
        in_corridor = (k_low <= spot_px <= k_high)
        min_leg_depth_usd = round(min(float(leg1_depth), float(leg2_depth)), 2)
        corridor_width_pct = round((k_high - k_low) / k_low * 100.0, 4)
        basis_ev = (
            eval_basis_fn(spot_px=spot_px, k_low=k_low, k_high=k_high, c_taker_net=c_taker, tte_sec=min(s15["tte"], s1h["tte"]))
            if eval_basis_fn is not None
            else {"eligible": corridor_width_pct >= 0.25, "expected_net_profit_per_pair": round(1.0 - c_taker, 5), "ev_per_pair": round(1.0 - c_taker, 5), "p_double_loss": 0.0}
        )
        basis_safe = bool(corridor_width_pct >= 0.25 and min_leg_depth_usd >= 15.0 and float(basis_ev.get("ev_per_pair", 0.0)) > -0.05)
        min_cross_oracle_corridor_ok = bool(corridor_width_pct >= 0.10 and min_leg_depth_usd >= 15.0)
        live_eligible_96c = bool(c_taker <= 0.960 and basis_safe)
        sig_type = "SHADOW_PHASE4_RISK_FREE_BOX_ARB" if (c_taker < 1.00 and min_cross_oracle_corridor_ok) else ("SHADOW_PHASE4_CORRIDOR_BOX_ARB" if (in_corridor and c_taker < 1.08 and basis_safe) else None)
        if sig_type and (asset_str, exp_bucket, sig_type) not in emitted:
            emitted.add((asset_str, exp_bucket, sig_type))
            rec = {
                "event_type": sig_type, "logged_at_utc": datetime.now(timezone.utc).isoformat(), "asset": asset_str,
                "expiry_bucket": exp_bucket, "expiry_ts": float(exp_ts), "tte_sec": round(min(s15["tte"], s1h["tte"]), 1),
                "market_15m": s15["market_id"], "market_1h": s1h["market_id"], "strike_15m": round(k15, 4), "strike_1h": round(k1h, 4),
                "strike_low": round(k_low, 2), "strike_high": round(k_high, 2), "corridor_width_pct": corridor_width_pct,
                "cross_oracle_basis_safe": basis_safe, "cross_oracle_not_true_riskless": True, "live_eligible_96c": live_eligible_96c,
                "expected_net_profit_per_pair": basis_ev.get("expected_net_profit_per_pair"),
                "p_double_loss": basis_ev.get("p_double_loss"),
                "spot_px": round(spot_px, 2), "spot_in_corridor": in_corridor, "equal_shares_walked": int(walk_res["shares"]),
                "leg1": {"side": leg1_lbl, "ask": leg1_w["vwap"], "eff_px": leg1_w["eff_px"], "l1_depth_usd": round(float(leg1_depth), 2)},
                "leg2": {"side": leg2_lbl, "ask": leg2_w["vwap"], "eff_px": leg2_w["eff_px"], "l1_depth_usd": round(float(leg2_depth), 2)},
                "min_leg_l1_depth_usd": min_leg_depth_usd, "all_in_taker_box_cost": round(c_taker, 4),
                "maker_box_cost": round(c_maker, 4), "guaranteed_min_profit_per_pair": round(1.00 - c_taker, 4),
            }
            active_boxes = getattr(self, "_shadow_phase4_active_boxes", None)
            if active_boxes is None:
                self._shadow_phase4_active_boxes = active_boxes = {}
            active_boxes[f"{asset_str}_{exp_bucket}_{sig_type}"] = dict(rec)
            self._append_shadow_phase3_4_event(rec)
            h_logger.info(f"[SHADOW PHASE 4] {sig_type}: {asset_str} ({leg1_lbl}@${leg1_px:.2f} + {leg2_lbl}@${leg2_px:.2f}) TakerCost=${c_taker:.4f} | MakerCost=${c_maker:.4f} | MinLegDepth=${min_leg_depth_usd:.1f} | BasisSafe={basis_safe} | Corridor=[{k_low:.2f}, {k_high:.2f}]")
    except Exception as exc:
        h_logger.debug(f"[SHADOW PHASE 4] Scan error: {exc}")


def step_shadow_phase3_4_tracker_impl(self: Any, now_ts: float, *, read_fast_tick_fn: Any, h_logger: Any) -> None:
    shadow_orders = getattr(self, "_shadow_maker_orders", None) or {}
    for key, ord_rec in list(shadow_orders.items()):
        try:
            asset = ord_rec["asset"]
            snap = read_fast_tick_fn(asset, max_age_sec=2.0, now=now_ts)
            spot_px = float((snap or {}).get("spot_price") or (snap or {}).get("spot") or 0.0)
            if ord_rec.get("horizon") == "15m":
                cl_twap = float((snap or {}).get("chainlink_twap_60s") or 0.0)
                if cl_twap > 0.0:
                    spot_px = cl_twap
            open_spot = float(ord_rec.get("open_spot") or 0.0)
            target = ord_rec["target_token"]
            status = ord_rec["status"]
            cur_ask, cur_bid = 0.0, 0.0
            if snap:
                mkt_id = ord_rec["market_id"]
                mkt_node = (snap.get("markets") or {}).get(mkt_id) if isinstance(snap.get("markets"), dict) else None
                if not mkt_node and str(snap.get("market_id") or "") == mkt_id:
                    mkt_node = snap
                if isinstance(mkt_node, dict):
                    side_node = mkt_node.get(target) or {}
                    cur_ask = float(side_node.get("best_ask") or 0.0)
                    cur_bid = float(side_node.get("best_bid") or 0.0)

            if status == "RESTING":
                if spot_px > 0.0 and open_spot > 0.0:
                    raw_dist = ((spot_px - open_spot) / open_spot) * 100.0
                    s_dist = raw_dist if target == "UP" else -raw_dist
                    if s_dist < 0.04:
                        ord_rec["status"] = "CANCELED_TOXIC_SPOT_RETRACE"
                        ord_rec["closed_at_utc"] = datetime.now(timezone.utc).isoformat()
                        ord_rec["retrace_cushion_pct"] = round(s_dist, 4)
                        self._append_shadow_phase3_4_event({**ord_rec, "event_type": "SHADOW_PHASE3A_MAKER_CANCELED_TOXIC"})
                        shadow_orders.pop(key, None)
                        continue
                if cur_ask > 0.0 and (now_ts - float(ord_rec["placed_ts"])) >= 0.25:
                    m_px = float(ord_rec["shadow_maker_px"])
                    if 0.0 < cur_ask <= m_px + 0.001:
                        ord_rec["status"] = "SHADOW_MAKER_FILLED"
                        ord_rec["filled_ts"] = now_ts
                        ord_rec["fill_delay_sec"] = round(now_ts - float(ord_rec["placed_ts"]), 2)
                        ord_rec["t1_filled"] = False
                        ord_rec["t2_filled"] = False
                        ord_rec["realized_per_share"] = 0.0
                        ord_rec["rem_frac"] = 1.0
                        self._append_shadow_phase3_4_event({**ord_rec, "event_type": "SHADOW_PHASE3A_MAKER_FILLED"})
                        h_logger.info(f"[SHADOW PHASE 3A FILLED] {asset} {target} (mkt={ord_rec['market_id']}) filled @ ${m_px:.2f} after {ord_rec['fill_delay_sec']:.2f}s (0% fee + 20% rebate)")
                        continue
                if now_ts >= float(ord_rec["ttl_expires_ts"]):
                    ord_rec["status"] = "EXPIRED_UNFILLED"
                    ord_rec["closed_at_utc"] = datetime.now(timezone.utc).isoformat()
                    self._append_shadow_phase3_4_event({**ord_rec, "event_type": "SHADOW_PHASE3A_MAKER_EXPIRED_UNFILLED"})
                    shadow_orders.pop(key, None)

            elif status == "SHADOW_MAKER_FILLED":
                tte_rem = float(ord_rec["expiry_ts"]) - now_ts
                if (now_ts - float(ord_rec.get("filled_ts", now_ts))) >= 5.0 and cur_bid > 0.0:
                    if not ord_rec.get("t1_filled") and cur_bid >= 0.95:
                        ord_rec["t1_filled"] = True
                        ord_rec["realized_per_share"] = float(ord_rec.get("realized_per_share", 0.0)) + 0.50 * 0.95
                        ord_rec["rem_frac"] = 0.50
                    if not ord_rec.get("t2_filled") and cur_bid >= 0.98:
                        ord_rec["t2_filled"] = True
                        ord_rec["realized_per_share"] = float(ord_rec.get("realized_per_share", 0.0)) + 0.50 * 0.98
                        ord_rec["rem_frac"] = 0.0
                    if float(ord_rec.get("rem_frac", 1.0)) <= 1e-6:
                        shares_20 = 20.0 / float(ord_rec["shadow_maker_px"])
                        cost_20 = shares_20 * float(ord_rec["shadow_maker_eff_cost"])
                        pnl_20 = round(shares_20 * float(ord_rec["realized_per_share"]) - cost_20, 2)
                        ord_rec.update({
                            "status": "RESOLVED", "exit_reason": "MAKER_TP_95_98", "won": True,
                            "shadow_net_pnl_usd": pnl_20, "shadow_net_pnl_12_usd": round(pnl_20 * 0.60, 2),
                            "closed_at_utc": datetime.now(timezone.utc).isoformat(),
                        })
                        self._append_shadow_phase3_4_event({**ord_rec, "event_type": "SHADOW_PHASE3A_MAKER_RESOLVED"})
                        shadow_orders.pop(key, None)
                        continue
                if spot_px > 0.0 and open_spot > 0.0 and tte_rem >= 25.0:
                    s_cush = ((spot_px - open_spot) / open_spot * 100.0) if target == "UP" else ((open_spot - spot_px) / open_spot * 100.0)
                    wrong_pct = -s_cush
                    if wrong_pct <= 0.0:
                        ord_rec.pop("wrong_side_ts", None)
                    else:
                        req_w = 0.14 if tte_rem > 900.0 else (0.09 if tte_rem > 180.0 else 0.05)
                        req_d = 30.0 if tte_rem > 900.0 else (15.0 if tte_rem > 180.0 else 8.0)
                        if wrong_pct >= req_w:
                            w_ts = ord_rec.get("wrong_side_ts")
                            if w_ts is None:
                                ord_rec["wrong_side_ts"] = now_ts
                            elif (now_ts - float(w_ts)) >= req_d and cur_bid >= 0.15:
                                rem_f = float(ord_rec.get("rem_frac", 1.0))
                                salv_net_sh = cur_bid * (1.0 - 0.07 * (1.0 - cur_bid))
                                tot_per_sh = float(ord_rec.get("realized_per_share", 0.0)) + rem_f * salv_net_sh
                                shares_20 = 20.0 / float(ord_rec["shadow_maker_px"])
                                cost_20 = shares_20 * float(ord_rec["shadow_maker_eff_cost"])
                                pnl_20 = round(shares_20 * tot_per_sh - cost_20, 2)
                                ord_rec.update({
                                    "status": "RESOLVED", "exit_reason": "WRONG_SIDE_SALVAGE", "salvage_bid": round(cur_bid, 4),
                                    "won": bool(pnl_20 > 0), "final_spot": round(spot_px, 4),
                                    "shadow_net_pnl_usd": pnl_20, "shadow_net_pnl_12_usd": round(pnl_20 * 0.60, 2),
                                    "closed_at_utc": datetime.now(timezone.utc).isoformat(),
                                })
                                self._append_shadow_phase3_4_event({**ord_rec, "event_type": "SHADOW_PHASE3A_MAKER_RESOLVED"})
                                shadow_orders.pop(key, None)
                                continue
                        else:
                            ord_rec.pop("wrong_side_ts", None)
                if now_ts >= float(ord_rec["expiry_ts"]) + 2.0 and spot_px > 0.0 and open_spot > 0.0:
                    won_rem = (spot_px >= open_spot) if target == "UP" else (spot_px < open_spot)
                    rem_f = float(ord_rec.get("rem_frac", 1.0))
                    tot_per_sh = float(ord_rec.get("realized_per_share", 0.0)) + (rem_f * 1.00 if won_rem else 0.0)
                    shares_20 = 20.0 / float(ord_rec["shadow_maker_px"])
                    cost_20 = shares_20 * float(ord_rec["shadow_maker_eff_cost"])
                    pnl_20 = round(shares_20 * tot_per_sh - cost_20, 2)
                    ord_rec.update({
                        "status": "RESOLVED", "exit_reason": "EXPIRY_SETTLEMENT", "won": bool(pnl_20 > 0),
                        "final_spot": round(spot_px, 2), "shadow_net_pnl_usd": pnl_20,
                        "shadow_net_pnl_12_usd": round(pnl_20 * 0.60, 2), "closed_at_utc": datetime.now(timezone.utc).isoformat(),
                    })
                    self._append_shadow_phase3_4_event({**ord_rec, "event_type": "SHADOW_PHASE3A_MAKER_RESOLVED"})
                    h_logger.info(f"[SHADOW PHASE 3A RESOLVED] {asset} {target} (mkt={ord_rec['market_id']}) | Won={ord_rec['won']} | Shadow Net PnL=${pnl_20:+.2f}")
                    shadow_orders.pop(key, None)
                elif now_ts >= float(ord_rec["expiry_ts"]) + 300.0:
                    shadow_orders.pop(key, None)
        except Exception as exc:
            h_logger.debug(f"[SHADOW PHASE 3A] Step error: {exc}")

    active_boxes = getattr(self, "_shadow_phase4_active_boxes", None) or {}
    for bkey, brec in list(active_boxes.items()):
        try:
            exp_ts = float(brec.get("expiry_ts") or brec.get("expiry_bucket") or 0.0)
            if exp_ts <= 0.0 or now_ts < exp_ts + 2.5:
                continue
            if now_ts > exp_ts + 300.0:
                active_boxes.pop(bkey, None)
                continue
            snap = read_fast_tick_fn(brec["asset"], max_age_sec=5.0, now=now_ts)
            spot_1h = float((snap or {}).get("spot_price") or (snap or {}).get("spot") or 0.0)
            twap_15m = float((snap or {}).get("chainlink_twap_60s") or spot_1h)
            if spot_1h <= 0.0:
                continue
            k15 = float(brec.get("strike_15m") or brec["strike_low"])
            k1h = float(brec.get("strike_1h") or brec["strike_high"])
            leg1_s = brec["leg1"]["side"]
            leg2_s = brec["leg2"]["side"]

            def _leg_win(lbl: str) -> float:
                if lbl == "UP_15M":
                    return 1.0 if twap_15m >= k15 else 0.0
                if lbl == "DOWN_15M":
                    return 1.0 if twap_15m < k15 else 0.0
                if lbl == "UP_1H":
                    return 1.0 if spot_1h >= k1h else 0.0
                return 1.0 if spot_1h < k1h else 0.0

            payout_pair = _leg_win(leg1_s) + _leg_win(leg2_s)
            c_taker = float(brec["all_in_taker_box_cost"])
            pairs_20 = 20.0 / max(c_taker, 0.10)
            net_pnl_20 = round(pairs_20 * (payout_pair - c_taker), 2)
            resolved_box = {
                **brec,
                "event_type": "SHADOW_PHASE4_BOX_RESOLVED",
                "resolved_at_utc": datetime.now(timezone.utc).isoformat(),
                "final_1h_binance_spot": round(spot_1h, 4),
                "final_15m_chainlink_twap": round(twap_15m, 4),
                "payout_per_pair": payout_pair,
                "double_win_jackpot": bool(payout_pair >= 1.99),
                "basis_trap_zero_payout": bool(payout_pair < 0.50),
                "shadow_net_pnl_20_usd": net_pnl_20,
            }
            self._append_shadow_phase3_4_event(resolved_box)
            active_boxes.pop(bkey, None)
        except Exception as exc:
            h_logger.debug(f"[SHADOW PHASE 4] Resolve error: {exc}")


# --- Modularized PolymarketLiveHarvester Methods (Bound to Harvester Globals via _bind_hv_method) ---
# Static module-level bindings overridden at bind-time by `polymarket_live_harvester.__dict__`.
# Guard `_hv__*`-only forward declarations behind `TYPE_CHECKING` so module-level runtime functions
# (`position_is_settlement_receivable`, `get_unleashed_v5_tier_profile`, etc.) are never clobbered to `None`.
RISK_CONFIG: Dict[str, Any] = {}
LIVE_WS_BOOK_MAX_AGE_MS: float = 1500.0
MAX_ALLOWED_SPREAD: float = 0.08
MIN_LOT_SIZE_USD: float = 12.0
MAX_ABSOLUTE_TICKET_USD: float = 10000.0
_json_loads: Any = json.loads
if TYPE_CHECKING:
    DATA_DIR: Any = None
    PIPELINE_ROOT: Any = None
    COUNTERFACTUAL_CANDIDATES_FILE: Any = None
    _CURRENT_TRACE: Any = None
    _PRE_HOT_CTX: Any = None
    _NY_TZ: Any = None
    OrderResult: Any = None
    ExecutionStatus: Any = None
    PolymarketLiveExecutor: Any = None
    fast_tick_book_for_token: Any = None
    read_fast_tick: Any = None
    compute_smart_maker_bid: Any = None
    _get_hot_io_pool: Any = None
    compute_composite_edge_score: Any = None
    evaluate_coinbase_venue_veto: Any = None
    compute_max_acceptable_ask: Any = None
    compute_stop_risk_fractional_kelly_ticket: Any = None
    apply_convex_payoff_sizing_cap: Any = None
    get_equity_tier_limits: Any = None
    compute_correlated_truncated_kelly_size: Any = None
    _emit_shock_attempt_trace: Any = None
    send_operational_alert: Any = None

async def _hv__attempt_live_phase3a_maker_rescue(
    self, trade_id: str, token_id: str, target_token: str, asset_str: str, effective_notional: float,
    first_ask: float, first_bid: float, min_allowed_price: float, max_allowed_price: float,
    open_spot: float, entry_spot_ref: float, spot_denom: str, tte: float, pre_cond_bal: float,
    book_snapshot: Optional[Dict[str, Any]], is_subhourly: Optional[bool] = None, obi_l1: float = 0.0,
) -> Optional[OrderResult]:
    def _p3a_spot_from_shm(tk: Optional[Dict[str, Any]], rem_tte_s: float) -> float:
        if not tk:
            return 0.0
        if spot_denom == "USD":
            if rem_tte_s > 60.0:
                return float(tk.get("chainlink_proxy_spot") or tk.get("coinbase_spot") or tk.get("chainlink_twap_60s") or 0.0)
            return float(tk.get("chainlink_twap_60s") or tk.get("chainlink_proxy_spot") or tk.get("coinbase_spot") or 0.0)
        return float(tk.get("spot_price") or tk.get("spot") or 0.0)

    explicit_flag = self.__dict__.get("enable_live_phase3a_maker_fallback")
    if explicit_flag is False or os.environ.get("PM_DISABLE_LIVE_PHASE3A_MAKER", "0") == "1":
        return None
    real_live = (
        not self.dry_run and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
        and getattr(self.executor, "client", None) is not None
        and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
        and not any(
            k in getattr(self.executor, "__dict__", {})
            for k in ("execute_snipe_order_async", "execute_snipe_order")
        )
    )
    if not (explicit_flag is True or (real_live and bool(RISK_CONFIG.get("enable_live_phase3a_maker_fallback", True)))):
        return None
    if tte < (85.0 if real_live else 75.0) or self.risk_controller.is_halted() or getattr(self, "risk_halt", False):
        return None
    maker_entry_fn = getattr(self.executor, "place_passive_maker_entry", None) or getattr(self.executor, "post_maker_entry_order", None)
    if maker_entry_fn is None:
        return None
    rcfg_mkr = getattr(self, "risk_config", None) or RISK_CONFIG
    subh_flag = bool(is_subhourly) if is_subhourly is not None else bool((self.pending_entry_intents.get(trade_id) or {}).get("is_subhourly"))
    if self._is_v5_live_strict():
        _gov_d_p3a = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {})
        if not bool(_gov_d_p3a.get("enable_15m_subordinate_maker", True) if subh_flag else _gov_d_p3a.get("enable_1h_shielded_maker", True)):
            return None
        max_allowed_price = min(float(max_allowed_price), float(_gov_d_p3a.get("max_maker_price_15m" if subh_flag else "max_maker_price_1h", 0.78)))
    elif real_live:
        max_allowed_price = min(float(max_allowed_price), float(rcfg_mkr.get("directional_maker_max_price", 0.76)))
        if subh_flag and float(tte) > 240.0:
            max_allowed_price = min(float(max_allowed_price), float(rcfg_mkr.get("phase3a_15m_long_tte_max_price", 0.72)))
    fresh_bk = fast_tick_book_for_token(read_fast_tick(asset_str), token_id) or book_snapshot or {}
    f_ask = min((float(a["price"] if isinstance(a, dict) else a[0]) for a in (fresh_bk.get("asks") or []) if float(a.get("size", 0) if isinstance(a, dict) else a[1]) > 0), default=first_ask)
    f_bid = max((float(b["price"] if isinstance(b, dict) else b[0]) for b in (fresh_bk.get("bids") or []) if float(b.get("size", 0) if isinstance(b, dict) else b[1]) > 0), default=first_bid)
    if real_live and max(f_bid, first_bid) > float(max_allowed_price) + 1e-6:
        return None
    if subh_flag and float(tte) > 240.0 and max(f_bid, first_bid) > float(max_allowed_price) + 0.01 + 1e-6:
        return None
    if compute_smart_maker_bid is not None and f_ask > 0.0:
        smart_res = compute_smart_maker_bid(
            max(f_bid, first_bid), f_ask,
            min_floor=float(min_allowed_price), max_ceiling=float(max_allowed_price),
            obi_l1=float(obi_l1 or 0.0),
            tick_size=self.executor._tick_size_cache.get(token_id),
        )
        smart_px = smart_res[0] if isinstance(smart_res, tuple) else smart_res
        if smart_px is None:
            return None
        maker_px = float(smart_px)
    else:
        ask_cap = round(f_ask - 0.01, 2) if f_ask > 0.02 else round(max_allowed_price, 2)
        bid_step = round(max(f_bid, first_bid) + 0.01, 2) if max(f_bid, first_bid) > 0.0 else ask_cap
        maker_px = round(min(float(max_allowed_price), ask_cap, bid_step), 2)
    if not (float(min_allowed_price) - 1e-6 <= maker_px <= float(max_allowed_price) + 1e-6) or (f_ask > 0.0 and maker_px > round(f_ask - 0.01, 2) + 1e-6):
        return None
    _rt_p3a_cfg = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("routing", {})
    if real_live and abs(maker_px - max(f_bid, first_bid)) < 1e-6:
        _join_q_cap = float(_rt_p3a_cfg.get("max_maker_join_queue_usd", 350.0))
        _join_q_usd = sum(
            float(b["price"] if isinstance(b, dict) else b[0]) * float(b.get("size", 0) if isinstance(b, dict) else b[1])
            for b in (fresh_bk.get("bids") or [])
            if abs(float(b["price"] if isinstance(b, dict) else b[0]) - maker_px) < 1e-6
        )
        if _join_q_usd > _join_q_cap + 1e-6:
            logger.info(
                f"[LIVE PHASE 3A QUEUE VETO] {trade_id}: joining bid queue ${_join_q_usd:.2f} > ${_join_q_cap:.2f} at ${maker_px:.2f}; skipping."
            )
            return None
    _p3a_cap_usd = float(RISK_CONFIG.get("phase3a_maker_max_notional_usd", 22.00))
    if real_live and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("sizing_tiers", {}).get("unleash_full_throttle", True)):
        _eq_p3a = float(getattr(self, "_last_known_collateral", 0.0) or 0.0) + sum(
            self.get_position_market_value(p, time.time()) for p in self.active_positions.values()
        )
        if _eq_p3a > 0.0:
            _p3a_prof = get_unleashed_v5_tier_profile(_eq_p3a)
            _p3a_cap_usd = max(_p3a_cap_usd, round(_eq_p3a * float(_p3a_prof["alpha_notional"]), 2))
    rescue_notional = min(float(effective_notional), _p3a_cap_usd)
    if math.floor(rescue_notional / max(0.01, maker_px)) < 5:
        return None
    t0_m = time.perf_counter()
    _tr_m = _CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
    if _tr_m is not None:
        _tr_m.set(skip_forensic=False, path_type="MAKER_P3A", target_px=maker_px, notional_usd=rescue_notional, eval_ask=f_ask or first_ask, eval_bid=f_bid or first_bid, fill_px=None, post_ask=None, post_bid=None)
    init_disp = (entry_spot_ref - open_spot) if target_token == "UP" else (open_spot - entry_spot_ref)
    if real_live and open_spot > 0.0 and init_disp > 0.0:
        pre_tk = read_fast_tick(asset_str, max_age_sec=2.0)
        pre_sp = _p3a_spot_from_shm(pre_tk, float(tte))
        if pre_sp > 0.0 and (((pre_sp - open_spot) if target_token == "UP" else (open_spot - pre_sp)) < 0.75 * init_disp):
            if _tr_m is not None:
                _tr_m.set(stage_outcome="SHIELD_PRE_POST", gate_detail="Pre-post shield: spot retraced >25% before Maker post")
            logger.info(f"[LIVE PHASE 3A PRE-POST SHIELD] {trade_id}: spot already retraced >25% before Maker post; aborting.")
            return None
    if trade_id in self.pending_entry_intents:
        self.pending_entry_intents[trade_id].update(target_price=maker_px, notional_usd=rescue_notional, heartbeat_ts=time.time())
    inflight_p3a = self.__dict__.setdefault("_inflight_phase3a_maker_ids", set())
    inflight_p3a.add(trade_id)
    _mkr_normal_return = False
    try:
        _ex_d = getattr(self.executor, "__dict__", {})
        _async_mkr_fn = (
            getattr(self.executor, "place_passive_maker_entry_async", None)
            if ("place_passive_maker_entry" not in _ex_d and "post_maker_entry_order" not in _ex_d)
            else None
        )
        if trade_id in self.pending_entry_intents:
            self.pending_entry_intents[trade_id]["maker_wire_inflight"] = True
        if _async_mkr_fn is not None:
            post_res = await _async_mkr_fn(
                token_id=token_id, price=maker_px, notional_usd=rescue_notional, side="BUY",
                min_price_floor=float(min_allowed_price), max_price_ceiling=float(max_allowed_price),
            )
        else:
            post_res = await asyncio.to_thread(
                maker_entry_fn, token_id=token_id, price=maker_px, notional_usd=rescue_notional, side="BUY",
                min_price_floor=float(min_allowed_price), max_price_ceiling=float(max_allowed_price),
            )
        if not isinstance(post_res, dict):
            _mkr_normal_return = True
            return None
        if _tr_m is not None:
            _tr_m.set(
                sign_ms=post_res.get("sign_ms"),
                http_ms=post_res.get("post_ms") if post_res.get("post_ms") is not None else round((time.perf_counter() - t0_m) * 1000.0, 2),
            )
        if post_res.get("outcome_unknown"):
            _mkr_normal_return = True
            return OrderResult(
                success=False, order_id=post_res.get("orderID"), trade_id=trade_id, token_id=token_id,
                target_token=target_token, side="BUY", price=maker_px, size=float(post_res.get("shares") or 5.0),
                notional_usd=rescue_notional, fee_usd=0.0, latency_ms=round((time.perf_counter() - t0_m) * 1000.0, 2),
                mode="LIVE_PHASE3A_UNKNOWN", execution_status=ExecutionStatus.SUBMITTED,
                details={"outcome_unknown": True, "entry_order_id": post_res.get("orderID"), "pre_token_balance": pre_cond_bal},
                error=str(post_res.get("error") or "PHASE3A_POST_UNKNOWN"),
            )
        maker_oid = str(post_res.get("orderID") or "").strip()
        if not post_res.get("success") or not maker_oid:
            if _tr_m is not None:
                _tr_m.set(stage_outcome="MAKER_POST_FAILED", gate_detail=str(post_res.get("error") or "MAKER_POST_FAILED"))
            _mkr_normal_return = True
            return None
        maker_px = float(post_res.get("price") or maker_px)
        posted_sh = float(post_res.get("shares") or 0.0)
        if trade_id in self.pending_entry_intents:
            self.pending_entry_intents[trade_id].update(
                entry_order_id=maker_oid, target_price=maker_px,
                notional_usd=round(posted_sh * maker_px, 4) if posted_sh > 0.0 else rescue_notional,
                heartbeat_ts=time.time(),
            )
        _default_p3a_ttl = str(
            _rt_p3a_cfg.get("maker_ttl_sec", (getattr(self, "risk_config", None) or RISK_CONFIG).get("phase3a_maker_ttl_sec", 4.0))
            if real_live
            else 3.5
        )
        ttl_s = max(0.2, float(os.environ.get("PM_LIVE_PHASE3A_TTL_SEC", _default_p3a_ttl)))
        t_start_m = time.monotonic()
        max_keep_s = min(10.0, max(ttl_s, 6.0), max(0.2, float(tte) - 65.0)) if (real_live and "PM_LIVE_PHASE3A_TTL_SEC" not in os.environ) else ttl_s
        deadline = t_start_m + ttl_s
        uws = getattr(self.executor, "_user_ws_cache", None)
        init_disp = (entry_spot_ref - open_spot) if target_token == "UP" else (open_spot - entry_spot_ref)
        _shield_decay_frac = float(_rt_p3a_cfg.get("shield_decay_cancel_frac", 0.35)) if real_live else 0.35
        _shield_keep_frac = max(0.05, min(0.95, 1.0 - _shield_decay_frac))
        _p3a_q_cap = float(_rt_p3a_cfg.get("max_maker_join_queue_usd", 350.0))
        _allow_repeg = bool(
            getattr(self, "enable_phase3a_outbid_repeg", False)
            or (real_live and _rt_p3a_cfg.get("enable_phase3a_outbid_repeg", True))
        )
        ws_filled = False
        adverse_shield_hit = False
        repegged_once = False
        reconciled_pre = None
        _last_rp_m = t_start_m
        while time.monotonic() < deadline:
            if trade_id in self.pending_entry_intents:
                self.pending_entry_intents[trade_id]["heartbeat_ts"] = time.time()
            rem_w = max(0.02, min(0.10, deadline - time.monotonic()))
            if uws is not None and uws.is_healthy():
                await uws.wait_for_fill_or_timeout(rem_w, prev_seq=uws.fill_sequence)
                snap_o = uws.get_order_snapshot(maker_oid, max_age_sec=5.0)
                if self._ws_snap_fully_filled(snap_o, posted_sh):
                    ws_filled = True
                    break
            else:
                await asyncio.sleep(rem_w)
                if posted_sh > 0.0 and (time.monotonic() - _last_rp_m) >= 0.45 and hasattr(self.executor, "get_order_fill_summary"):
                    _last_rp_m = time.monotonic()
                    try:
                        _sp_m = await asyncio.to_thread(self.executor.get_order_fill_summary, maker_oid, token_id)
                    except Exception:
                        _sp_m = None
                    if isinstance(_sp_m, dict) and _sp_m.get("terminal") and not _sp_m.get("resting") and float(_sp_m.get("matched") or 0.0) >= posted_sh - 0.01:
                        ws_filled = True
                        break
            cushion_ok = True
            cur_disp = init_disp
            if open_spot > 0.0 and init_disp > 0.0:
                shm_tk = read_fast_tick(asset_str, max_age_sec=1.5) if real_live else None
                rem_tte_now = max(0.0, float(tte) - (time.monotonic() - t_start_m))
                cur_sp = _p3a_spot_from_shm(shm_tk, rem_tte_now)
                if cur_sp <= 0.0:
                    cur_sp = await asyncio.to_thread(self.get_usd_reference_spot_price if spot_denom == "USD" else self.get_reference_spot_price, asset_str)
                if cur_sp and float(cur_sp) > 0.0:
                    cur_disp = (float(cur_sp) - open_spot) if target_token == "UP" else (open_spot - float(cur_sp))
                    if cur_disp < _shield_keep_frac * init_disp:
                        cushion_ok = False
                        adverse_shield_hit = True
                        self.__dict__.setdefault("_p3a_adverse_shield_ts", {})[trade_id] = time.time()
                        logger.info(
                            f"[LIVE PHASE 3A ADVERSE SHIELD] {trade_id}: cushion decayed >{_shield_decay_frac*100:.0f}%; canceling {maker_oid}."
                        )
                        break
            _perps_ws_p3a = getattr(self, "_perps_leadlag_ws", None)
            if _perps_ws_p3a is not None and bool(
                GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_perp1_maker_precancel_leadlag", True)
            ):
                _perp_thr_p3a = float(
                    GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("perp1_adverse_move_bps_300ms", 8.0) or 8.0
                )
                if _perps_ws_p3a.should_precancel_binary_maker(
                    asset_str, target_token, threshold_bps=_perp_thr_p3a, window_ms=300.0
                ):
                    cushion_ok = False
                    adverse_shield_hit = True
                    self.__dict__.setdefault("_p3a_adverse_shield_ts", {})[trade_id] = time.time()
                    logger.info(
                        f"[LIVE PHASE 3A PERP1 PRE-CANCEL] {trade_id}: Perps BBO jumped >= {_perp_thr_p3a:.1f}bps against {target_token} in 300ms; canceling {maker_oid}."
                    )
                    break
            if (
                _allow_repeg
                and not repegged_once
                and cushion_ok
                and (deadline - time.monotonic()) >= 1.2
                and (init_disp <= 0.0 or cur_disp >= 0.90 * init_disp)
            ):
                _mkt_ws_p3a = getattr(self, "_pos_market_ws", None)
                _rbk = fast_tick_book_for_token(read_fast_tick(asset_str, max_age_sec=1.5), token_id) or (
                    _mkt_ws_p3a.get_book(token_id, max_age_sec=1.5) if _mkt_ws_p3a is not None else None
                ) or {}
                _rbids = _rbk.get("bids") or []
                _rasks = _rbk.get("asks") or []
                _cb = max((float(b["price"] if isinstance(b, dict) else b[0]) for b in _rbids if float(b.get("size", 0) if isinstance(b, dict) else b[1]) > 0), default=0.0)
                _ca = min((float(a["price"] if isinstance(a, dict) else a[0]) for a in _rasks if float(a.get("size", 0) if isinstance(a, dict) else a[1]) > 0), default=0.0)
                if _cb > maker_px + 1e-6 and _ca > _cb + 1e-6:
                    _step_b = round(_cb + 0.01, 2) if (_ca - _cb) >= 0.02 - 1e-6 else round(_cb, 2)
                    _rp_px = round(min(float(max_allowed_price), round(_ca - 0.01, 2), _step_b), 2)
                    _rq_u = (
                        sum(
                            float(b["price"] if isinstance(b, dict) else b[0]) * float(b.get("size", 0) if isinstance(b, dict) else b[1])
                            for b in _rbids
                            if abs(float(b["price"] if isinstance(b, dict) else b[0]) - _rp_px) < 1e-6
                        )
                        if abs(_rp_px - _cb) < 1e-6
                        else 0.0
                    )
                    if (
                        _rp_px >= round(_cb, 2) - 1e-6
                        and _rp_px > maker_px + 1e-6
                        and _rq_u <= _p3a_q_cap + 1e-6
                        and math.floor(rescue_notional / max(0.01, _rp_px)) >= 5
                    ):
                        _cr_p, _sm_p, _ms_p, _ap_p = await self._reconcile_maker_entry_fill(maker_oid, token_id, False, posted_sh, maker_px)
                        _co_p = str((_cr_p or {}).get("outcome") or "")
                        _ic_p = bool((_cr_p or {}).get("is_canceled"))
                        if _ms_p >= 0.01 or (not _ic_p and _co_p != "FILLED" and (_sm_p is None or not _sm_p.get("terminal") or _sm_p.get("resting"))):
                            reconciled_pre = (_cr_p, _sm_p, _ms_p, _ap_p)
                            break
                        repegged_once = True
                        _rp_res = (
                            await _async_mkr_fn(
                                token_id=token_id, price=_rp_px, notional_usd=rescue_notional, side="BUY",
                                min_price_floor=float(min_allowed_price), max_price_ceiling=float(max_allowed_price),
                            )
                            if _async_mkr_fn is not None
                            else await asyncio.to_thread(
                                maker_entry_fn, token_id=token_id, price=_rp_px, notional_usd=rescue_notional, side="BUY",
                                min_price_floor=float(min_allowed_price), max_price_ceiling=float(max_allowed_price),
                            )
                        )
                        if not isinstance(_rp_res, dict) or _rp_res.get("outcome_unknown") or not _rp_res.get("success") or not str(_rp_res.get("orderID") or "").strip():
                            post_res = _rp_res if isinstance(_rp_res, dict) else {}
                            if post_res.get("outcome_unknown"):
                                _mkr_normal_return = True
                                return OrderResult(
                                    success=False, order_id=post_res.get("orderID"), trade_id=trade_id, token_id=token_id,
                                    target_token=target_token, side="BUY", price=_rp_px, size=float(post_res.get("shares") or 5.0),
                                    notional_usd=rescue_notional, fee_usd=0.0, latency_ms=round((time.perf_counter() - t0_m) * 1000.0, 2),
                                    mode="LIVE_PHASE3A_UNKNOWN", execution_status=ExecutionStatus.SUBMITTED,
                                    details={"outcome_unknown": True, "entry_order_id": post_res.get("orderID"), "pre_token_balance": pre_cond_bal},
                                    error=str(post_res.get("error") or "PHASE3A_REPEG_UNKNOWN"),
                                )
                            if trade_id in self.pending_entry_intents:
                                self.pending_entry_intents[trade_id].pop("entry_order_id", None)
                            _mkr_normal_return = True
                            return None
                        post_res = _rp_res
                        _old_px = maker_px
                        maker_oid = str(_rp_res.get("orderID") or "").strip()
                        maker_px = float(_rp_res.get("price") or _rp_px)
                        posted_sh = float(_rp_res.get("shares") or 0.0)
                        if trade_id in self.pending_entry_intents:
                            self.pending_entry_intents[trade_id].update(
                                entry_order_id=maker_oid, target_price=maker_px,
                                notional_usd=round(posted_sh * maker_px, 4) if posted_sh > 0.0 else rescue_notional,
                                heartbeat_ts=time.time(),
                            )
                        deadline = max(deadline, min(t_start_m + max_keep_s, time.monotonic() + min(2.5, ttl_s)))
                        logger.info(f"[LIVE PHASE 3A OUTBID REPEG] {trade_id}: stepped ${_old_px:.2f} -> ${maker_px:.2f} (OID={maker_oid}).")
                        continue
            if cushion_ok and uws is not None and uws.is_healthy() and time.monotonic() >= deadline - 0.05 and (time.monotonic() - t_start_m) < max_keep_s:
                cur_bk = fast_tick_book_for_token(read_fast_tick(asset_str), token_id) or {}
                cur_b = max((float(b["price"]) for b in (cur_bk.get("bids") or []) if float(b.get("size", 0)) > 0), default=maker_px)
                if cur_b <= maker_px + 0.01:
                    deadline = min(t_start_m + max_keep_s, time.monotonic() + 5.0)
        elapsed_ttl_ms = round((time.monotonic() - t_start_m) * 1000.0, 1)
        if reconciled_pre is not None:
            cancel_res, summary, matched_sh, avg_px = reconciled_pre
        else:
            cancel_res, summary, matched_sh, avg_px = await self._reconcile_maker_entry_fill(maker_oid, token_id, ws_filled, posted_sh, maker_px)
        if _tr_m is not None:
            _ebk = (fast_tick_book_for_token(read_fast_tick(asset_str), token_id) or {}) if real_live else {}
            _pa = min((float(a["price"]) for a in (_ebk.get("asks") or []) if float(a.get("size", 0)) > 0), default=None)
            _pb = max((float(b["price"]) for b in (_ebk.get("bids") or []) if float(b.get("size", 0)) > 0), default=None)
            _tr_m.set(target_px=maker_px, ttl_ms=elapsed_ttl_ms, post_ask=_pa, post_bid=_pb)
        c_out = str((cancel_res or {}).get("outcome") or "")
        is_canc = bool((cancel_res or {}).get("is_canceled"))
        if matched_sh >= 0.01 and (is_canc or c_out in ("FILLED", "CANCELED", "PARTIALLY_FILLED_CANCELED") or bool((summary or {}).get("terminal"))):
            if _tr_m is not None:
                _tr_m.set(stage_outcome="FILLED_MAKER", fill_px=avg_px, notional_usd=round(matched_sh * avg_px, 4))
            logger.info(f"[LIVE PHASE 3A MAKER RESCUE FILLED] {trade_id}: {matched_sh:.2f} sh @ ${avg_px:.4f} (OID={maker_oid})")
            tx_list = list((summary or {}).get("transactions_hashes") or (summary or {}).get("tx_hashes") or [])
            _mkr_normal_return = True
            return OrderResult(
                success=True, order_id=maker_oid, trade_id=trade_id, token_id=token_id, target_token=target_token,
                side="BUY", price=avg_px, size=matched_sh, notional_usd=round(matched_sh * avg_px, 4), fee_usd=0.0,
                latency_ms=round((time.perf_counter() - t0_m) * 1000.0, 2), mode="LIVE_PHASE3A_MAKER_IN",
                execution_status=ExecutionStatus.MATCHED_PENDING_SETTLEMENT,
                details={"pre_token_balance": pre_cond_bal, "trade_ids": list((summary or {}).get("trade_ids") or []), "transactions_hashes": tx_list, "phase3a_maker_rescue": True},
            )
        if not is_canc and c_out != "FILLED" and (summary is None or not summary.get("terminal") or summary.get("resting")):
            _mkr_normal_return = True
            return OrderResult(
                success=False, order_id=maker_oid, trade_id=trade_id, token_id=token_id, target_token=target_token,
                side="BUY", price=maker_px, size=float(post_res.get("shares") or 5.0), notional_usd=rescue_notional,
                fee_usd=0.0, latency_ms=round((time.perf_counter() - t0_m) * 1000.0, 2), mode="LIVE_PHASE3A_CANCEL_UNKNOWN",
                execution_status=ExecutionStatus.SUBMITTED,
                details={"outcome_unknown": True, "entry_order_id": maker_oid, "pre_token_balance": pre_cond_bal},
                error="PHASE3A_CANCEL_UNVERIFIED",
            )
        if _tr_m is not None:
            _tr_m.set(stage_outcome="SHIELD_ADVERSE_TTL" if adverse_shield_hit else "MAKER_TTL_EXPIRED")
        logger.info(f"[LIVE PHASE 3A EXPIRED CLEAN] {trade_id}: {maker_oid} canceled ({elapsed_ttl_ms / 1000.0:.1f}s).")
        if trade_id in self.pending_entry_intents:
            self.pending_entry_intents[trade_id].pop("entry_order_id", None)
        _mkr_normal_return = True
        return None
    finally:
        if _mkr_normal_return and trade_id in self.pending_entry_intents:
            self.pending_entry_intents[trade_id].pop("maker_wire_inflight", None)
        inflight_p3a.discard(trade_id)

def _hv__finish_single_leg_lock(
    self, cand: Dict[str, Any], sleeve_src: str, tok_a: str, mid_a: str,
    dedupe_k: str, retry_cd: Dict[str, float], now_ts: float, _rcfg: Dict[str, Any],
    own_grad: bool = True,
) -> Dict[str, Any]:
    """Executes fresh dual-book verified single-leg deterministic lock inside _d1_inflight_exec_lock."""
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        _is_sll_zf_focus_enabled,
        check_per_event_concentration_cap,
        check_sll_cand_dispute_guard,
        compute_d1_per_market_notional_cap,
        compute_sll_and_carry_gatling_budget,
        extract_sll_event_group_key,
        is_market_busy_for_scaling,
        is_post_expiry_uma_frozen_lock,
        open_market_notional_usd,
        pending_intents_cash_reserved_usd,
        pending_intents_synced_equity_usd,
        preempt_makers_for_instant_taker_arb,
        resolve_canonical_fee_source,
        resolve_harvester_sll_tick_size,
        spawn_fast_htm_maker_fill_reconcile,
        sync_pending_intents_on_collateral_refresh,
    )
    _disp_1l = check_sll_cand_dispute_guard(cand)
    if _disp_1l:
        return {"executed": False, "reason": _disp_1l}
    opp_a = str(cand.get("leg_a_opp_token_id") or "")
    cid_a = str(cand.get("leg_a_condition_id") or "")
    cand_ts = float(cand.get("ts_unix") or now_ts)
    exp_ts = float(cand.get("expiry_ts") or (now_ts + 7200.0))
    s2_fast = sleeve_src in {"S2_EXACT_TWAP_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR"}
    if not self.dry_run and ((now_ts - cand_ts) > (2.5 if s2_fast else 8.0) or (exp_ts - now_ts) < (3.8 if s2_fast else 25.0) or (s2_fast and (exp_ts - now_ts) > 38.5)):
        return {"executed": False, "reason": "STALE_OR_OUTSIDE_TTE_WINDOW"}
    _evt_ok_1l, _evt_rsn_1l, _evt_rem_1l, _evt_gk_1l = check_per_event_concentration_cap(
        self, cand, market_ids=[mid_a] if mid_a else [], now_ts=now_ts, min_headroom_usd=5.05
    )
    if not _evt_ok_1l:
        return {"executed": False, "reason": _evt_rsn_1l}
    _lk_c_1l = getattr(self, "_last_known_collateral", None)
    _free_pre_1l = (
        max(
            0.0,
            float(_lk_c_1l)
            - (0.0 if self.dry_run else pending_intents_cash_reserved_usd(getattr(self, "pending_entry_intents", None))),
        )
        if isinstance(_lk_c_1l, (int, float)) and not isinstance(_lk_c_1l, bool)
        else None
    )
    _cand_net_1l = float(cand.get("box_cost_net") or cand.get("leg_a_limit_price") or cand.get("max_box_cost_net") or 0.995)
    _gov_rb_1l = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
    _core_clip_1l = min(24.0, max(12.0, float(_gov_rb_1l.get("gatling_base_clip_core_usd", 20.0) or 20.0)))
    _low_cash_1l_tkr = bool(
        not self.dry_run
        and _free_pre_1l is not None
        and float(_free_pre_1l) < (_core_clip_1l if _cand_net_1l <= 0.992 else 8.50)
    )
    _signaled_1l, _preempt_keys_1l = preempt_makers_for_instant_taker_arb(
        self,
        reason=f"SLL_TAKER:{sleeve_src}",
        target_market_ids={mid_a},
        cand_net_cost=_cand_net_1l,
        free_cash_hint=_free_pre_1l,
        target_arb_cash_usd=45.0,
        min_fallback_cash_usd=_core_clip_1l if (s2_fast or _cand_net_1l <= 0.992) else 9.0,
        force_cross_market_when_low_cash=bool(s2_fast or _low_cash_1l_tkr),
        now_ts=now_ts,
    )
    _ev_loop_1l = getattr(self, "_main_loop", None)
    _same_thr_1l = _ev_loop_1l is not None and getattr(_ev_loop_1l, "_thread_id", None) == threading.get_ident()
    if _signaled_1l > 0 and not _same_thr_1l:
        for _ in range(60):
            if not any(
                isinstance(_i_p, dict)
                and _i_p.get("live_maker_anchor_inflight")
                and (
                    str(_i_p.get("inflight_key") or "") in _preempt_keys_1l
                    if _preempt_keys_1l
                    else str(_i_p.get("market_id") or "") == mid_a
                )
                for _i_p in getattr(self, "pending_entry_intents", {}).values()
            ):
                break
            time.sleep(0.015)
    if is_market_busy_for_scaling(self, mid_a):
        return {"executed": False, "reason": "MARKET_ALREADY_OCCUPIED"}
    fr_a = float(cand["leg_a_fee_rate"]) if cand.get("leg_a_fee_rate") is not None else 0.0
    fe_a = float(cand.get("leg_a_fee_exponent", 1.0) or 1.0)
    max_eff = float(cand.get("max_box_cost_net", 0.995) or 0.995)
    max_opp = float(cand.get("max_opp_bid", 0.025) or 0.025)
    _prev_c_1l = getattr(self, "_last_known_collateral", None)
    collat = None if (_signaled_1l > 0 and not self.dry_run) else _prev_c_1l
    if collat is None and not self.dry_run:
        try:
            collat = self.executor.get_collateral_balance()
            if isinstance(collat, (int, float)) and not isinstance(collat, bool) and math.isfinite(float(collat)) and float(collat) >= 0.0:
                self._last_known_collateral = float(collat)
                sync_pending_intents_on_collateral_refresh(self, _prev_c_1l, float(collat))
        except Exception:
            collat = None
    _pend_1l = getattr(self, "pending_entry_intents", None)
    _inf_1l_u = 0.0 if self.dry_run else pending_intents_cash_reserved_usd(_pend_1l)
    _sync_1l_u = 0.0 if self.dry_run else pending_intents_synced_equity_usd(_pend_1l)
    collat_f = max(0.0, float(collat if collat is not None else (200.0 if self.dry_run else 0.0)) - _inf_1l_u)
    if (
        not self.dry_run
        and collat_f < _core_clip_1l - 0.50
        and _cand_net_1l <= 0.98005
        and getattr(self.executor, "client", None) is not None
        and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
        and "execute_snipe_order" not in getattr(self.executor, "__dict__", {})
        and bool(_gov_rb_1l.get("enable_zero_loss_open_carry_velocity_recycle", True))
    ):
        from src.polymarket_research.stage_c_zero_loss_velocity import recycle_open_zero_loss_carry_for_fast_arb
        _rec_1l = recycle_open_zero_loss_carry_for_fast_arb(
            self,
            needed_cash_gap_usd=max(0.0, _core_clip_1l - collat_f),
            challenger_net_cost=_cand_net_1l,
            challenger_rem_tte_sec=max(1.0, exp_ts - now_ts),
            challenger_sleeve=sleeve_src,
            exclude_market_ids={mid_a} if mid_a else set(),
            now_ts=now_ts,
        )
        if _rec_1l.get("recycled_count", 0) > 0:
            collat = getattr(self, "_last_known_collateral", collat)
            collat_f = max(collat_f + float(_rec_1l.get("freed_cash_usd", 0.0)), max(0.0, float(collat or 0.0) - _inf_1l_u))
    cur_exp = sum(float(p.get("notional_usd", 0.0) or 0.0) for p in self.active_positions.values() if not position_is_settlement_receivable(p)) + _inf_1l_u + _sync_1l_u
    if self._is_v5_unleashed_active():
        _gsn_1l = GLOBAL_GOVERNANCE_MANAGER.snapshot
        _b1_gov_1l = _gsn_1l.get("riskless_boxes") or _gsn_1l.get("bond1_maker") or {}
        _v5_1l = get_unleashed_v5_tier_profile(collat_f + cur_exp)
        _b1_pct = float(_v5_1l["bond1_free_cash_pct"])
        _enforce_b1_tkr_cap = bool(
            getattr(self, "enforce_bond1_smart_queue", False)
            or (
                not self.dry_run
                and getattr(self.executor, "client", None) is not None
                and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
                and "execute_snipe_order" not in getattr(self.executor, "__dict__", {})
            )
        )
        _zf_1l = _is_sll_zf_focus_enabled(self, _enforce_b1_tkr_cap, _gsn_1l, collat_f + cur_exp)
        if _zf_1l:
            _b1_pct = max(_b1_pct, float(_b1_gov_1l.get("seed_zero_loss_focus_bond1_pool_pct", 0.92) or 0.92))
        lot_cap_1l = max(75.0, round(collat_f * _b1_pct, 2)) if own_grad else float(_v5_1l["bridged_zero_fee_cap_usd"])
        if _enforce_b1_tkr_cap:
            sll_used_1l = (
                sum(
                    float(p.get("notional_usd", 0.0) or 0.0)
                    for p in self.active_positions.values()
                    if not position_is_settlement_receivable(p)
                    and not is_post_expiry_uma_frozen_lock(p, now_ts)
                    and str(p.get("box_type") or "") in {"SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK"}
                )
                + pending_intents_cash_reserved_usd(_pend_1l, only_maker_anchor=True)
                + _sync_1l_u
            )
            sll_pool_rem_1l = max(0.0, (collat_f + sll_used_1l) * _b1_pct - sll_used_1l)
            mkt_cap_1l = float(_rcfg.get("bond1_per_market_cap_usd") or _v5_1l.get("bond1_per_market_cap_usd", 25.0))
            if _zf_1l and not _rcfg.get("bond1_per_market_cap_usd"):
                mkt_cap_1l = min(float(_b1_gov_1l.get("bond1_per_market_cap_usd_seed", 45.0)), max(mkt_cap_1l, round((collat_f + sll_used_1l) * 0.46, 2)))
            budget = min(
                float(_rcfg.get("d1_box_max_budget_usd", 250.0)), lot_cap_1l,
                mkt_cap_1l, sll_pool_rem_1l,
                max(0.0, collat_f - float(_v5_1l["box_collateral_reserve_usd"])),
                max(0.0, max(float(self.max_exposure), (collat_f + cur_exp) * 0.96) - cur_exp),
            )
        else:
            budget = min(
                float(_rcfg.get("d1_box_max_budget_usd", 250.0)), lot_cap_1l,
                max(0.0, collat_f - float(_v5_1l["box_collateral_reserve_usd"])),
                collat_f * _b1_pct,
                max(0.0, max(float(self.max_exposure), (collat_f + cur_exp) * 0.96) - cur_exp),
            )
    else:
        lot_cap_1l = 35.0 if own_grad else 16.50
        budget = min(
            float(_rcfg.get("d1_box_max_budget_usd", 250.0)), lot_cap_1l,
            max(0.0, collat_f - float(_rcfg.get("d1_box_collateral_reserve_usd", 0.0))),
            collat_f * (0.32 if collat_f >= 160.0 else float(_rcfg.get("d1_box_bankroll_pct", 0.25))),
            max(0.0, max(float(self.max_exposure), collat_f * 0.55) - cur_exp),
        )
    budget = compute_sll_and_carry_gatling_budget(self, budget, collat_f, cur_exp, "SINGLE_LEG_LOCK", sleeve_src, own_grad, GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes"), rem_tte_sec=exp_ts - now_ts, now_ts=now_ts, cap_usd=float(_rcfg.get("d1_box_max_budget_usd", 250.0)))
    budget = min(budget, float(_evt_rem_1l))
    existing_mkt_u = open_market_notional_usd(self, [mid_a])
    if existing_mkt_u > 0.0:
        budget = min(budget, max(0.0, compute_d1_per_market_notional_cap(self) - existing_mkt_u))
    if budget < 5.05:
        return {"executed": False, "reason": "INSUFFICIENT_BOX_COLLATERAL_HEADROOM"}
    custom_bk = "get_market_book" in getattr(self.executor, "__dict__", {})
    ws_bks = cand.get("ws_books") if not custom_bk else None
    if isinstance(ws_bks, dict) and (time.time() - float(cand.get("ws_books_ts") or 0.0)) <= 0.65 and isinstance(ws_bks.get(tok_a), dict) and isinstance(ws_bks.get(opp_a), dict):
        raw_ba, raw_bo = ws_bks[tok_a], ws_bks[opp_a]
    elif not custom_bk and hasattr(self.executor, "get_market_books_batch"):
        bm = self.executor.get_market_books_batch([tok_a, opp_a])
        raw_ba, raw_bo = bm.get(tok_a) or {}, bm.get(opp_a) or {}
    else:
        raw_ba, raw_bo = self.executor.get_market_book(tok_a) or {}, self.executor.get_market_book(opp_a) or {}
    norm = lambda ls: [
        {"price": float(x["price"] if isinstance(x, dict) else x[0]), "size": float(x["size"] if isinstance(x, dict) else x[1])}
        for x in (ls or []) if float(x.get("size", 0) if isinstance(x, dict) else x[1]) > 0
    ]
    bk_a = {"asks": norm(raw_ba.get("asks")), "bids": norm(raw_ba.get("bids"))}
    bids_o = norm(raw_bo.get("bids"))
    _ck_1l = str(cand.get("box_id") or dedupe_k or "")
    _ast_1l = str(cand.get("asset") or sleeve_src[:4]).upper()
    if not bk_a["asks"]:
        if not self.dry_run:
            try:
                from src.polymarket_research.economic_attribution_ledger import GLOBAL_DECAY_TRACKER, emit_funnel_event
                GLOBAL_DECAY_TRACKER.mark_our_fill_or_cancel(_ck_1l)
                emit_funnel_event(
                    "COMPETITOR_DECAY_OBSERVED",
                    sleeve=sleeve_src,
                    candidate_key=_ck_1l,
                    box_type="SINGLE_LEG_LOCK",
                    asset=_ast_1l,
                    competitor_decay_ms=round(max(0.5, (time.time() - cand_ts) * 1000.0), 2),
                    reason="FRESH_BOOK_EMPTY_ASKS",
                )
            except Exception:
                pass
        return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:EMPTY_ASK_BOOK"}
    ask_a = min(x["price"] for x in bk_a["asks"])
    bid_o = max((x["price"] for x in bids_o), default=0.0)
    if ask_a <= 0.50 or bid_o > max_opp + 1e-6 or (ask_a + bid_o) > 1.015:
        return {"executed": False, "reason": f"DUAL_BOOK_CONSENSUS_VETO:ask={ask_a:.4f},opp_bid={bid_o:.4f}"}
    qual = [
        x for x in sorted(bk_a["asks"], key=lambda r: r["price"])
        if (x["price"] + (fr_a * ((x["price"] * (1.0 - x["price"])) ** fe_a) if fr_a > 0.0 else 0.0)) <= max_eff + 1e-6
    ]
    avail_sh = sum(x["size"] for x in qual)
    min_sh_req = max(5.0, float(cand.get("min_order_shares") or 5.0))
    min_depth_usd = round(max(4.5, min_sh_req * (qual[0]["price"] if qual else 0.90)), 2)
    if not qual or sum(x["price"] * x["size"] for x in qual) < min_depth_usd or avail_sh < min_sh_req:
        if not self.dry_run:
            try:
                from src.polymarket_research.economic_attribution_ledger import GLOBAL_DECAY_TRACKER, emit_funnel_event
                GLOBAL_DECAY_TRACKER.mark_our_fill_or_cancel(_ck_1l)
                emit_funnel_event(
                    "COMPETITOR_DECAY_OBSERVED",
                    sleeve=sleeve_src,
                    candidate_key=_ck_1l,
                    box_type="SINGLE_LEG_LOCK",
                    asset=_ast_1l,
                    competitor_decay_ms=round(max(0.5, (time.time() - cand_ts) * 1000.0), 2),
                    reason=f"FRESH_BOOK_SWEPT:ask={ask_a:.4f}",
                )
            except Exception:
                pass
        return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:INSUFFICIENT_DEPTH"}
    eff_avail_sh = avail_sh if avail_sh < 6.0 else max(min_sh_req, avail_sh / 1.15)
    worst_px, cum_sh, cap_sh = qual[0]["price"], 0.0, min(eff_avail_sh, budget / max(qual[0]["price"], 0.50))
    for lv in qual:
        worst_px, cum_sh = lv["price"], cum_sh + lv["size"]
        if cum_sh >= cap_sh:
            break
    sh_int = int(math.floor(min(eff_avail_sh, budget / max(worst_px, 0.50)) + 1e-9))
    if sh_int < 5:
        return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:MIN_SHARES"}
    use_mock_lock_tk = self.dry_run or hasattr(getattr(self.executor, "client", None), "_mock_children")
    _cust_tk_1l = "get_token_tick_size" in getattr(self.executor, "__dict__", {})
    tk_sz = resolve_harvester_sll_tick_size(
        self.executor, tok_a, cand, bk_win=raw_ba, mkt_ws=getattr(self, "_pos_market_ws", None),
        real_clob=not use_mock_lock_tk, custom_tk_fn=_cust_tk_1l, price_hint=worst_px, allow_sync_sdk=True,
    ) or (cand.get("leg_a_tick_size") or 0.01 if use_mock_lock_tk else 0.01)
    if not use_mock_lock_tk and any(abs(round(x["price"], 2) - round(x["price"], 3)) > 1e-6 for x in qual):
        tk_sz = min(float(tk_sz or 0.001), 0.001)
    if hasattr(self.executor, "prewarm_token_market_cache"):
        self.executor.prewarm_token_market_cache(
            token_id=tok_a, tick_size=tk_sz if (use_mock_lock_tk or float(tk_sz or 0.01) < 0.01) else None, neg_risk=bool(cand.get("leg_a_neg_risk")),
            fee_rate_bps=int(round(fr_a * 10000)), condition_id=cid_a or mid_a, fee_rate=fr_a, fee_exponent=fe_a,
        )
    pre_b = (
        self._resolve_fast_pre_token_balance_sync(tok_a)
        if hasattr(self, "_resolve_fast_pre_token_balance_sync")
        else (0.0 if self.dry_run else float(self._wallet_token_balance(tok_a)[0] or 0.0))
    )
    if not self.dry_run and hasattr(self, "_mark_token_pre_bal_dirty"):
        self._mark_token_pre_bal_dirty(tok_a)
    lid = str(cand.get("box_id") or f"LOCK1_{int(now_ts)}")
    if lid in self.active_positions:
        lid = f"{lid}_{int(now_ts * 1000) % 10000}"
    side_s = str(cand.get("leg_a_side") or "YES").upper()
    _snipe_kwargs = dict(
        trade_id=lid, token_id=tok_a, target_token=side_s, notional_usd=round(sh_int * worst_px, 4),
        target_price=worst_px, side="BUY", depth_hurdle=1.0, market_id=mid_a, condition_id=cid_a or mid_a,
        market_fee_rate=fr_a, market_fee_exponent=fe_a, max_price_ceiling=worst_px,
        max_ticket_cap=max(37.5, round(sh_int * worst_px + 1.0, 2)), min_price_floor=0.50,
        prefetched_pre_balance=pre_b, prefetched_book=bk_a, neg_risk=cand.get("leg_a_neg_risk"),
        max_book_buffer=max(0.0, round(worst_px - qual[0]["price"], 4)),
    )
    if not self.dry_run:
        try:
            from src.polymarket_research.economic_attribution_ledger import GLOBAL_DECAY_TRACKER, emit_funnel_event
            GLOBAL_DECAY_TRACKER.mark_our_fill_or_cancel(_ck_1l or lid)
            emit_funnel_event(
                "ORDER_SUBMITTED",
                sleeve=sleeve_src,
                candidate_key=_ck_1l or lid,
                box_type="SINGLE_LEG_LOCK",
                asset=_ast_1l,
                net_edge_bps=round(max(0.0, 1.0 - worst_px) * 10000.0, 2),
                est_profit_usd=round(max(0.0, 1.0 - worst_px) * sh_int, 4),
                notional_usd=round(sh_int * worst_px, 4),
            )
        except Exception:
            pass
    try:
        o_res = self.executor.execute_snipe_order(
            **_snipe_kwargs, allow_partial_fak=True, min_order_shares=min_sh_req,
        )
    except TypeError:
        o_res = self.executor.execute_snipe_order(**_snipe_kwargs)
    unk = str(o_res.execution_status or "").upper() in {"ENTRY_OUTCOME_UNKNOWN", "OUTCOME_UNKNOWN"} or bool((o_res.details or {}).get("outcome_unknown"))
    with getattr(self, "_state_save_lock", None) or self._GLOBAL_STATE_SAVE_LOCK:
        if not o_res.success and not unk:
            if pre_b == 0.0:
                (self.__dict__.get("_d1_dirty_token_until") or {}).pop(tok_a, None)
            if dedupe_k:
                retry_cd[dedupe_k] = now_ts + (1.0 if s2_fast else 9.5)
            return {"executed": False, "reason": f"ORDER_REJECTED:{o_res.error}", "result": o_res}
        if dedupe_k:
            retry_cd.pop(dedupe_k, None)
            self._record_seen_d1_box_key(dedupe_k)
        if sleeve_src in {"BOND1_UMA_RESOLUTION_CARRY", "UMA_READY1_LIVENESS_PRIORITY"} and mid_a:
            self._record_seen_d1_box_key(f"BOND1_{mid_a}")
            self._record_seen_d1_box_key(f"BOND1_MKR_{mid_a}")
            self._record_seen_d1_box_key(f"UMA_READY1_{mid_a}")
        _w_map_1l = getattr(self, "_clinched_ws_watchlist", None)
        if isinstance(_w_map_1l, dict):
            _w_lk_1l = getattr(self, "_clinched_ws_lock", None)
            if _w_lk_1l is not None:
                with _w_lk_1l:
                    _w_map_1l.pop(str(tok_a), None)
            else:
                _w_map_1l.pop(str(tok_a), None)
        f_sh, f_px = float(o_res.size or sh_int), float(o_res.price or worst_px)
        raw_not = float(o_res.notional_usd or (f_sh * f_px))
        not_u = round(f_sh * f_px if raw_not > f_sh * max(f_px, worst_px) * 1.002 else raw_not, 4)
        fee_u = round(float(o_res.fee_usd or 0.0), 4)
        eff_px = round((not_u + fee_u) / max(f_sh, 0.01), 5)
        h_mat = bool(cand.get("hold_to_maturity") or f_px >= 0.982)
        fee_src_1l = resolve_canonical_fee_source(fr_a, sleeve_src, str(cand.get("fee_source") or ""))
        pos_1l = self._make_single_leg_lock_pos(
            lid, "SINGLE_LEG_LOCK", sleeve_src, _ast_1l,
            str(cand.get("leg_a_horizon") or "lock"), mid_a, cid_a, tok_a, side_s,
            bool(cand.get("leg_a_neg_risk")), f_sh, not_u, fee_u, fr_a, fe_a,
            fee_src_1l, exp_ts, now_ts, pre_b, o_res.order_id, h_mat, unk=unk,
        )
        _det_1l = o_res.details if isinstance(o_res.details, dict) else {}
        pos_1l["trade_ids"] = list(dict.fromkeys(str(x) for x in (_det_1l.get("trade_ids") or []) if x))
        pos_1l["transactions_hashes"] = list(dict.fromkeys(str(x) for x in (_det_1l.get("transactions_hashes") or _det_1l.get("transaction_hashes") or []) if x))
        pos_1l["dedupe_key"] = str(dedupe_k or "")
        pos_1l["pair_dedupe_key"] = str(
            cand.get("pair_dedupe_key")
            or (f"BOND1_{mid_a}" if sleeve_src in {"BOND1_UMA_RESOLUTION_CARRY", "UMA_READY1_LIVENESS_PRIORITY"} and mid_a else "")
        )
        if cand.get("event_id"):
            pos_1l["event_id"] = str(cand["event_id"])
        pos_1l["event_group_key"] = str(_evt_gk_1l or extract_sll_event_group_key(cand) or "")
        if cand.get("leg_a_label"):
            pos_1l["leg_a_label"] = str(cand["leg_a_label"])[:64]
        self.active_positions[lid] = pos_1l
        if unk:
            self._refresh_global_halt()
        else:
            if getattr(self, "_last_known_collateral", None) is not None:
                self._last_known_collateral = max(0.0, float(self._last_known_collateral) - (not_u + fee_u))
                self._last_entry_debit_window = (time.time(), float(self._last_known_collateral))
            self.executor.invalidate_collateral_cache()
            self._pending_collateral_refresh = True
        self.save_state()
        logger.info(f"✓ [SINGLE-LEG LOCK ENTERED] {lid} ({sleeve_src}) | {f_sh:.0f} sh @ eff=${eff_px:.4f} (hold_to_maturity={h_mat})")
    if not unk and not self.dry_run:
        try:
            from src.polymarket_research.economic_attribution_ledger import emit_funnel_event
            emit_funnel_event(
                "COMPLETE_BASKET_LOCKED",
                sleeve=sleeve_src,
                candidate_key=_ck_1l or lid,
                box_type="SINGLE_LEG_LOCK",
                asset=_ast_1l,
                net_edge_bps=round(max(0.0, 1.0 - eff_px) * 10000.0, 2),
                est_profit_usd=round(max(0.0, f_sh - not_u - fee_u), 4),
                notional_usd=not_u,
            )
        except Exception:
            pass
    if not unk and h_mat and not self.dry_run:
        spawn_fast_htm_maker_fill_reconcile(self, lid)
    return {"executed": not unk, "reason": "ENTRY_PENDING_ONCHAIN_RECONCILIATION" if unk else "OK", "result": o_res, "leg_trade_ids": [] if (unk or h_mat) else [lid]}

def _hv__finish_negrisk_convert_arb(
    self,
    cand: Dict[str, Any],
    sleeve_src: str,
    dedupe_k: str,
    retry_cd: Dict[str, float],
    now_ts: float,
    _rcfg: Dict[str, Any],
    own_grad: bool = True,
) -> Dict[str, Any]:
    """
    Executes fresh L2-verified `NR2_CONVERT_NO_SUBSET_ARB` / `NR_CONV_NO_BASKET_ARB` inside `_d1_inflight_exec_lock`:
    re-walks all `m` `NO` ask books + any `liquid_yes_sells` bid books, executes atomic FOK buys + Polygon
    `NegRiskAdapterV2.convertPositions` (`0xadA2...`, `0xc64748c4`), and records realized pUSD profit.
    """
    cand_ts = float(cand.get("ts_unix") or now_ts)
    exp_ts = float(cand.get("expiry_ts") or (now_ts + 7200.0))
    from src.polymarket_research.stage_c_zero_loss_velocity import check_strict_pure_riskless_candidate_gate
    _pure_nr_veto = check_strict_pure_riskless_candidate_gate(
        self, cand, GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}), is_maker=False
    )
    if _pure_nr_veto is not None:
        return {"executed": False, "reason": _pure_nr_veto}
    if not self.dry_run and ((now_ts - cand_ts) > 8.0 or (exp_ts - now_ts) < 60.0):
        return {"executed": False, "reason": "STALE_OR_OUTSIDE_TTE_WINDOW"}
    nrm_id = str(cand.get("neg_risk_market_id") or "").strip()
    raw_no_legs = list(cand.get("no_legs") or [])
    raw_yes_sells = list(cand.get("liquid_yes_sells") or [])
    fee_bips = int(cand.get("fee_bips") or 0)
    busy = {
        str(p.get("market_id") or "") for p in self.active_positions.values() if not position_is_settlement_receivable(p)
    } | {
        str(i.get("market_id") or "") for i in getattr(self, "pending_entry_intents", {}).values() if isinstance(i, dict)
    }
    if any(str(lg.get("market_id") or "") in busy for lg in raw_no_legs if lg.get("market_id")):
        return {"executed": False, "reason": "MARKET_ALREADY_OCCUPIED"}

    collat = getattr(self, "_last_known_collateral", None)
    _nr_inf_u = sum(float(i.get("notional_usd", 0.0) or 0.0) for i in getattr(self, "pending_entry_intents", {}).values() if isinstance(i, dict))
    _nr_preempt_min_u = 10.5 if str(cand.get("convert_mode") or "") == "NR_M1_DEAD_SEED_OVERROUND" else 26.0
    if not self.dry_run and (collat is None or (float(collat or 0.0) - _nr_inf_u) < _nr_preempt_min_u):
        if self._preempt_resting_maker_anchors(reason=f"NR_CONVERT:{sleeve_src}", market_ids=None) > 0:
            time.sleep(0.08)
            collat = None
            _nr_inf_u = sum(float(i.get("notional_usd", 0.0) or 0.0) for i in getattr(self, "pending_entry_intents", {}).values() if isinstance(i, dict))
    if collat is None and not self.dry_run:
        try:
            collat = self.executor.get_collateral_balance()
        except Exception:
            collat = None
    collat_f = max(0.0, float(collat if collat is not None else (200.0 if self.dry_run else 0.0)) - (0.0 if self.dry_run else _nr_inf_u))
    _cand_net_nr = float(cand.get("box_cost_net") or cand.get("net_cost_per_set") or 0.990)
    _gov_rb_nr = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
    _core_clip_nr = min(26.0, max(12.0, float(_gov_rb_nr.get("gatling_base_clip_d1_usd", 22.0) or 22.0)))
    if (
        not self.dry_run
        and collat_f < _core_clip_nr - 0.50
        and _cand_net_nr <= 0.98005
        and getattr(self.executor, "client", None) is not None
        and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
        and "execute_snipe_order" not in getattr(self.executor, "__dict__", {})
        and bool(_gov_rb_nr.get("enable_zero_loss_open_carry_velocity_recycle", True))
    ):
        from src.polymarket_research.stage_c_zero_loss_velocity import recycle_open_zero_loss_carry_for_fast_arb
        _rec_nr = recycle_open_zero_loss_carry_for_fast_arb(
            self,
            needed_cash_gap_usd=max(0.0, _core_clip_nr - collat_f),
            challenger_net_cost=_cand_net_nr,
            challenger_rem_tte_sec=max(1.0, exp_ts - now_ts),
            challenger_sleeve=sleeve_src,
            exclude_market_ids={str(lg.get("market_id") or "") for lg in raw_no_legs if lg.get("market_id")},
            now_ts=now_ts,
        )
        if _rec_nr.get("recycled_count", 0) > 0:
            collat = getattr(self, "_last_known_collateral", collat)
            collat_f = max(collat_f + float(_rec_nr.get("freed_cash_usd", 0.0)), max(0.0, float(collat or 0.0) - _nr_inf_u))
    cur_exp = sum(float(p.get("notional_usd", 0.0) or 0.0) for p in self.active_positions.values() if not position_is_settlement_receivable(p))
    if self._is_v5_unleashed_active():
        _v5_nr = get_unleashed_v5_tier_profile(collat_f + cur_exp)
        _nr_pct = float(_v5_nr["bond1_free_cash_pct"])
        lot_cap_nr = max(75.0, round(collat_f * _nr_pct, 2)) if own_grad else float(_v5_nr["bridged_zero_fee_cap_usd"])
        budget = min(
            float(_rcfg.get("d1_box_max_budget_usd", 250.0)),
            lot_cap_nr,
            max(0.0, collat_f - float(_v5_nr["box_collateral_reserve_usd"])),
            collat_f * _nr_pct,
            max(0.0, max(float(self.max_exposure), (collat_f + cur_exp) * 0.90) - cur_exp),
        )
    else:
        lot_cap_nr = 35.0 if own_grad else 16.50
        budget = min(
            float(_rcfg.get("d1_box_max_budget_usd", 250.0)),
            lot_cap_nr,
            max(0.0, collat_f - float(_rcfg.get("d1_box_collateral_reserve_usd", 12.0))),
            collat_f * (0.32 if collat_f >= 160.0 else float(_rcfg.get("d1_box_bankroll_pct", 0.25))),
            max(0.0, max(float(self.max_exposure), collat_f * 0.55) - cur_exp),
        )
    from src.polymarket_research.riskless_protocol_v2_expansion import maybe_cap_gatling_budget_sync
    budget = maybe_cap_gatling_budget_sync(self, budget, collat_f, cur_exp, "NEGRISK_CONVERT", sleeve_src, own_grad, GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes"), cap_usd=float(_rcfg.get("d1_box_max_budget_usd", 250.0)), reserve_u=0.50, override_legacy_cap=True)
    if budget < 5.05:
        return {"executed": False, "reason": "INSUFFICIENT_BOX_COLLATERAL_HEADROOM"}

    if str(cand.get("convert_mode") or "") == "NR3_SYNTHETIC_ALL_YES_OVERROUND":
        from src.polymarket_research.riskless_machine_gun_engine import finish_nr3_convert_arb
        nr_out = finish_nr3_convert_arb(self, cand, sleeve_src=sleeve_src, nrm_id=nrm_id, dedupe_k=dedupe_k, budget=budget, collat_f=collat_f, fee_bips=fee_bips, now_ts=now_ts)
    else:
        from src.polymarket_research.riskless_machine_gun_engine import finish_nr2_subset_convert_arb
        nr_out = finish_nr2_subset_convert_arb(
            self, cand, sleeve_src=sleeve_src, nrm_id=nrm_id, dedupe_k=dedupe_k,
            retry_cd=retry_cd, budget=budget, fee_bips=fee_bips, exp_ts=exp_ts, now_ts=now_ts,
        )
    if isinstance(nr_out, dict) and nr_out.get("executed") and not self.dry_run:
        try:
            from src.polymarket_research.economic_attribution_ledger import GLOBAL_DECAY_TRACKER, emit_funnel_event
            _ck_nr = str(cand.get("box_id") or dedupe_k or "")
            _ast_nr = str(cand.get("asset") or sleeve_src[:4]).upper()
            GLOBAL_DECAY_TRACKER.mark_our_fill_or_cancel(_ck_nr)
            for _st_nr in ("ORDER_SUBMITTED", "COMPLETE_BASKET_LOCKED"):
                emit_funnel_event(
                    _st_nr,
                    sleeve=sleeve_src,
                    candidate_key=_ck_nr,
                    box_type="NEGRISK_CONVERT",
                    asset=_ast_nr,
                    notional_usd=float((nr_out.get("result") or {}).get("total_cost_usd") or 0.0),
                )
        except Exception:
            pass
    return nr_out

def _hv__record_inline_d1_legged_out_close(
    self, box_id: str, cand: Dict[str, Any], resid: Dict[str, Any], res: Dict[str, Any]
) -> str:
    """Records 100%-inline D1 legged-out emergency unwinds in closed_positions so zero scratch losses go unrecorded."""
    now_ts = time.time()
    exp_ts = float(cand.get("expiry_ts") or (now_ts + 180.0))
    asset_sym = str(cand.get("asset") or "BTC").upper()
    tok = str(resid.get("token_id") or "")
    pfx = "leg_a" if tok == str(cand.get("leg_a_token_id")) else "leg_b"
    m_sh = float(resid.get("matched_shares") or cand.get("shares") or 12.0)
    px = float(resid.get("price") or cand.get(f"{pfx}_limit_price") or 0.48)
    raw_r = resid.get("raw") if isinstance(resid.get("raw"), dict) else {}
    mk_raw = self._num(raw_r.get("makingAmount") or raw_r.get("making_amount"))
    if mk_raw is not None and mk_raw >= 1e4:
        mk_raw = mk_raw / 1e6
    notional = round(float(mk_raw) if (mk_raw is not None and mk_raw > 0.0) else (m_sh * px), 4)
    fr = 0.0 if resid.get("is_maker_anchor") else (float(cand[f"{pfx}_fee_rate"]) if cand.get(f"{pfx}_fee_rate") is not None else 0.07)
    fe = float(cand.get(f"{pfx}_fee_exponent", 1.0) or 1.0)
    _fee_asset_in = str(resid.get("entry_fee_asset") or "USDC").upper()
    fee_in = round(m_sh * fr * ((px * (1.0 - px)) ** fe), 4) if fr > 0.0 else 0.0
    fee_cash_in = 0.0 if _fee_asset_in == "SHARES" else fee_in
    uw = resid.get("unwind_result") if isinstance(resid.get("unwind_result"), dict) else (
        res.get("unwind_result") if isinstance(res.get("unwind_result"), dict) else {}
    )
    gross_out = self._num(uw.get("taking_amount") or uw.get("notional_usd"))
    if gross_out is None or gross_out <= 0.0:
        raw_uw = (uw.get("details") or {}).get("raw_response") if isinstance(uw.get("details"), dict) else {}
        gross_out = self._num((raw_uw or {}).get("takingAmount")) or 0.0
    if gross_out >= 1e4:
        gross_out = gross_out / 1e6
    gross_out_f = round(float(gross_out), 4)
    fee_out_f = round(float(self._num(uw.get("fee_usd")) or 0.0), 4)
    avg_exit_px = round(gross_out_f / max(m_sh, 0.01), 4) if gross_out_f > 0.0 else 0.0
    net_pnl = round((gross_out_f - fee_out_f) - (notional + fee_cash_in), 2)
    tid = f"{box_id}_LEG_INLINE_UNWIND"
    if tid in self.active_positions or any(p.get("trade_id") == tid for p in self.closed_positions):
        tid = f"{tid}_{int(now_ts)}"
    now_iso = datetime.now(timezone.utc).isoformat()
    closed_rec = {
        "trade_id": tid,
        "box_id": box_id,
        "is_dominance_box": False,
        "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
        "entry_tte": round(max(1.0, exp_ts - now_ts), 2),
        "event_id": box_id,
        "market_id": str(cand.get(f"{pfx}_market_id") or tid),
        "condition_id": str(cand.get(f"{pfx}_condition_id") or ""),
        "token_id": tok,
        "target_token": str(cand.get(f"{pfx}_side") or ("UP" if "UP" in str(resid.get("label", "")).upper() else "DOWN")),
        "asset": asset_sym,
        "horizon": str(cand.get(f"{pfx}_horizon") or "15m"),
        "is_subhourly": True,
        "candle_open_spot": float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx == "leg_a" else "k_high") or 100.0),
        "entry_spot_ref": float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx == "leg_a" else "k_high") or 100.0),
        "spot_denomination": "USD",
        "entry_price": round(notional / max(m_sh, 0.01), 4),
        "entry_shares": m_sh,
        "gross_entry_shares": m_sh,
        "remaining_shares": 0.0,
        "filled_exit_shares": float(uw.get("matched_size") or m_sh),
        "remaining_exit_shares": 0.0,
        "remaining_cost_basis": 0.0,
        "realized_exit_cash": gross_out_f,
        "realized_exit_fee": fee_out_f,
        "gross_exit_cash": gross_out_f,
        "average_exit_price": avg_exit_px,
        "notional_usd": notional,
        "fee_usd": fee_in,
        "entry_fee_cash_usd": fee_cash_in,
        "entry_fee_asset": _fee_asset_in,
        "fee_source": "crypto_fees_v2",
        "fee_rate_applied": fr,
        "fee_exponent_applied": fe,
        "entry_time_utc": now_iso,
        "entry_ts": now_ts,
        "candle_expiry_ts": exp_ts,
        "order_id": resid.get("orderID"),
        "entry_order_id": resid.get("orderID"),
        "unwind_order_id": uw.get("orderID"),
        "status": ExecutionStatus.SETTLED,
        "exit_order_status": "INLINE_LEGGED_OUT_UNWOUND",
        "settled_at_utc": now_iso,
        "won": bool(net_pnl >= 0.0),
        "payout_usd": round(gross_out_f, 2),
        "net_pnl_usd": net_pnl,
        "close_reason": "D1_INLINE_LEGGED_OUT_UNWIND",
        "exit_decomposition_bucket": "SALVAGE_UNWIND",
    }
    self.closed_positions.append(closed_rec)
    if len(self.closed_positions) > 500:
        self.closed_positions = self.closed_positions[-500:]
    try:
        self.risk_controller.record_trade_pnl(net_pnl, is_non_directional=True)
    except Exception:
        pass
    if hasattr(self.executor, "invalidate_collateral_cache"):
        self.executor.invalidate_collateral_cache()
    self._pending_collateral_refresh = True
    self.save_state()
    if not getattr(self, "dry_run", True):
        try:
            from src.polymarket_research.economic_attribution_ledger import emit_funnel_event
            emit_funnel_event(
                "PARTIAL_BASKET_UNWOUND",
                sleeve=str(cand.get("sleeve_source") or "D1_SAME_ORACLE_DOMINANCE_BOX"),
                candidate_key=box_id,
                box_type=str(cand.get("box_type") or "DOMINANCE"),
                asset=asset_sym,
                notional_usd=notional,
                est_profit_usd=net_pnl,
                reason="D1_INLINE_LEGGED_OUT_UNWIND",
            )
        except Exception:
            pass
    logger.warning(
        f"[D1 INLINE LEGGED-OUT UNWIND RECORDED] {tid} ({asset_sym}): "
        f"Sold {m_sh:.2f} sh | Cost=${notional + fee_cash_in:.2f} -> NetOut=${gross_out_f - fee_out_f:.2f} | Net PnL=${net_pnl:+.2f}"
    )
    return tid

async def _hv_maybe_execute_graduated_maker_anchor_box(self, candidate_box: Dict[str, Any]) -> Dict[str, Any]:
    """EXP-PM-406B / EXP-PM-409 / v5.9.0: Executes 8/8-graduated Maker-Anchor 2-leg boxes with `<50ms` WS shield, 1-RTT repeg, and 0-REST WS fill-to-hedge."""
    from src.polymarket_research.synthetic_maker_quoter import (
        MakerAnchorUnwindBreaker,
        evaluate_resting_synthetic_quote_tick,
        is_maker_anchor_live_permitted,
    )
    _rcfg_ma = getattr(self, "risk_config", None) or RISK_CONFIG
    _explicit_rcfg_ma = isinstance(self.__dict__.get("risk_config"), dict) and "enable_live_maker_anchor_boxes" in self.__dict__["risk_config"]
    _gov_rb_full = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
    _gov_rb_ma = (
        _gov_rb_full
        if (self._is_v5_live_strict() and not _explicit_rcfg_ma)
        else {}
    )
    _unwind_brk: MakerAnchorUnwindBreaker = self.__dict__.setdefault(
        "_maker_unwind_breaker",
        MakerAnchorUnwindBreaker(
            max_unwind_loss_usd=float(_gov_rb_full.get("synthetic_maker_unwind_breaker_usd", 0.50) or 0.50)
        ),
    )
    _sl_chk_ma = str(candidate_box.get("sleeve_source") or "D1_MAKER_ANCHOR_BOX").strip()
    _brk_halted, _brk_why = _unwind_brk.is_halted(_sl_chk_ma)
    if _brk_halted:
        return {"executed": False, "reason": "MAKER_ANCHOR_UNWIND_BREAKER_TRIPPED"}
    if self._is_v5_live_strict() and not _explicit_rcfg_ma:
        _perm_ok, _perm_why = is_maker_anchor_live_permitted(_sl_chk_ma, _gov_rb_ma, unwind_breaker=_unwind_brk)
        if not _perm_ok:
            return {
                "executed": False,
                "reason": "MAKER_ANCHOR_BOX_DISABLED" if _perm_why == "MAKER_ANCHOR_DISABLED_BY_RISKLESS_PAA" else _perm_why,
            }
    _is_rebate_mg = _sl_chk_ma == "D1_REBATE_MACHINE_GUN"
    _allow_ma_gov = bool(_gov_rb_ma.get("enable_d1_rebate_maker_canary", False)) if _is_rebate_mg else bool(_gov_rb_ma.get("enable_two_leg_maker_anchor_boxes", True))
    if (
        (not _is_rebate_mg and not bool(_rcfg_ma.get("enable_live_maker_anchor_boxes", True)))
        or not _allow_ma_gov
        or os.environ.get("PM_DISABLE_LIVE_MAKER_ANCHOR_BOX", "0") == "1"
    ):
        return {"executed": False, "reason": "MAKER_ANCHOR_BOX_DISABLED"}
    if _is_rebate_mg and not self.dry_run:
        from src.polymarket_research.riskless_machine_gun_engine import evaluate_d1_maker_rebate_anchor
        _ft_rb = read_fast_tick(str(candidate_box.get("asset") or "")) if callable(read_fast_tick) else None
        _age_ms = (time.time() - float((_ft_rb or {}).get("timestamp_unix") or (_ft_rb or {}).get("ts") or 0.0)) * 1000.0
        _anc_a_rb = bool(candidate_box.get("anchor_is_a", True))
        _rb_ev = evaluate_d1_maker_rebate_anchor(
            anchor_bid_px=float(candidate_box.get("anchor_bid_px") or (candidate_box.get("leg_a_limit_price") if _anc_a_rb else candidate_box.get("leg_b_limit_price")) or 0.50),
            hedge_ask_px=float(candidate_box.get("hedge_limit_px") or candidate_box.get("hedge_limit_price") or (candidate_box.get("leg_b_limit_price") if _anc_a_rb else candidate_box.get("leg_a_limit_price")) or 0.50),
            shm_spot_age_ms=_age_ms,
            adverse_spot_velocity_pct=float((_ft_rb or {}).get("adverse_velocity_pct") or 0.0),
        )
        if not _rb_ev.get("eligible"):
            return {"executed": False, "reason": f"REBATE_MG_GUARD:{_rb_ev.get('reason')}"}
    if self._is_d1_box_halted():
        return {"executed": False, "reason": "DISABLED_OR_HALTED"}
    box_type = str(candidate_box.get("box_type") or "").strip().upper()
    sleeve_src = str(candidate_box.get("sleeve_source") or "D1_MAKER_ANCHOR_BOX").strip()
    cand_asset = str(candidate_box.get("asset") or "").strip().upper()
    if box_type not in {"DOMINANCE_MAKER_ANCHOR", "ZERO_FEE_MAKER_ANCHOR"}:
        return {"executed": False, "reason": f"UNSUPPORTED_MAKER_ANCHOR_TYPE:{box_type}"}
    core_d1 = {"BTC", "ETH", "XRP"} | ({"SOL"} if RISK_CONFIG.get("enable_sol_d1_box", True) else set())
    exp_d1 = {"BNB", "DOGE", "HYPE", "ZEC", "XAU", "XAG"}
    mid_a = str(candidate_box.get("leg_a_market_id") or "")
    mid_b = str(candidate_box.get("leg_b_market_id") or "")
    tok_a = str(candidate_box.get("leg_a_token_id") or "")
    tok_b = str(candidate_box.get("leg_b_token_id") or "")
    fr_a = float(candidate_box["leg_a_fee_rate"]) if candidate_box.get("leg_a_fee_rate") is not None else 0.07
    fr_b = float(candidate_box["leg_b_fee_rate"]) if candidate_box.get("leg_b_fee_rate") is not None else 0.07
    fe_a = float(candidate_box.get("leg_a_fee_exponent", 1.0) or 1.0)
    fe_b = float(candidate_box.get("leg_b_fee_exponent", 1.0) or 1.0)
    if not tok_a or not tok_b or tok_a == tok_b or not mid_a or not mid_b or mid_a == mid_b:
        return {"executed": False, "reason": "INVALID_BOX_INVARIANTS"}
    if box_type == "DOMINANCE_MAKER_ANCHOR":
        if cand_asset and cand_asset not in (core_d1 | exp_d1):
            return {"executed": False, "reason": f"UNSUPPORTED_D1_ASSET:{cand_asset}"}
        corr_bps = float(candidate_box.get("corridor_bps") or 0.0)
        if corr_bps < (4.0 if cand_asset in {"XAU", "XAG"} else (5.0 if cand_asset in exp_d1 else 3.0)):
            return {"executed": False, "reason": f"CORRIDOR_TOO_NARROW:{corr_bps:.2f}"}
        k_a = float(candidate_box.get("leg_a_strike") or 0.0)
        k_b = float(candidate_box.get("leg_b_strike") or 0.0)
        if str(candidate_box.get("leg_a_side") or "").upper() != "UP" or str(candidate_box.get("leg_b_side") or "").upper() != "DOWN" or not (0.0 < k_a < k_b):
            return {"executed": False, "reason": "INVALID_BOX_INVARIANTS"}
    elif max(fr_a, fr_b) > 0.0:
        return {"executed": False, "reason": "NON_ZERO_FEE_ON_ZF_MAKER_ANCHOR"}

    inflight_mkr = self.__dict__.setdefault("_inflight_maker_anchor_keys", set())
    inflight_mkr_types = self.__dict__.setdefault("_inflight_maker_anchor_types", set())
    dedupe_k = str(candidate_box.get("dedupe_key") or "")
    _unlim_mkr = self._is_unlimited_slots_active()
    mkr_type_k = f"{box_type}:{dedupe_k or cand_asset}" if _unlim_mkr else box_type
    if mkr_type_k in inflight_mkr_types or len(inflight_mkr) >= (8 if _unlim_mkr else 2):
        return {"executed": False, "reason": "MAKER_ANCHOR_ALREADY_INFLIGHT"}
    now_ts = time.time()
    seen_boxes = self.__dict__.setdefault("_seen_d1_box_keys", set())
    retry_cd = self.__dict__.setdefault("_d1_retry_cooldown_until", {})
    from src.polymarket_research.riskless_protocol_v2_expansion import is_d1_dedupe_blocked
    if is_d1_dedupe_blocked(self, dedupe_k, "", [mid_a, mid_b], now_ts) or (dedupe_k and float(retry_cd.get(dedupe_k, 0.0) or 0.0) > now_ts):
        return {"executed": False, "reason": "ALREADY_SEEN_OR_COOLDOWN"}
    if not self.dry_run and (not getattr(self, "_startup_reconciled", False) or self._global_halt_reasons()):
        return {"executed": False, "reason": "NOT_READY_OR_GLOBAL_HALT"}

    own_asset_grad_m = True
    try:
        st_path = DATA_DIR / "alpha124_shadow_state.json"
        if not st_path.exists() and DATA_DIR == (PIPELINE_ROOT / "data" / "polymarket"):
            alt_p = PIPELINE_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
            if alt_p.exists():
                st_path = alt_p
        if not st_path.exists() or (time.time() - st_path.stat().st_mtime) > 300.0:
            return {"executed": False, "reason": "ALPHA124_STATE_MISSING_OR_STALE"}
        st_raw = _json_loads(st_path.read_text(encoding="utf-8"))
        by_sl_map = st_raw.get("by_sleeve") or st_raw.get("per_strategy") or {}
        by_da_map = st_raw.get("by_d1_asset") or {}

        def _grad8_m(rec: Dict[str, Any]) -> bool:
            adj_p = rec.get("legging_adjusted_pnl_t1000_usd", rec.get("realized_pnl_t1000_usd", 0.0))
            return bool(
                int(rec.get("closed", 0) or 0) >= 8
                and float(rec.get("win_rate_pct", 0.0) or 0.0) >= 100.0
                and float(rec.get("realized_pnl_t1000_usd", 0.0) or 0.0) > 0.0
                and float(adj_p or 0.0) > 0.0
            )

        sl_rec_m = by_sl_map.get(sleeve_src) or {}
        own_mkr_grad = _grad8_m(sl_rec_m)
        sl_no_loss_m = float(sl_rec_m.get("realized_pnl_t1000_usd", 0.0) or 0.0) >= 0.0 and (
            int(sl_rec_m.get("closed", 0) or 0) == 0 or float(sl_rec_m.get("win_rate_pct", 100.0) or 0.0) >= 100.0
        )
        exp_mkr_ok = True
        if box_type == "DOMINANCE_MAKER_ANCHOR" and cand_asset in exp_d1:
            da_rec_m = by_da_map.get(cand_asset) or {}
            own_asset_grad_m = _grad8_m(da_rec_m)
            exp_mkr_ok = own_asset_grad_m or (
                bool((getattr(self, "risk_config", None) or RISK_CONFIG).get("enable_exp_d1_bridge", True))
                and int(da_rec_m.get("losses", 0) or 0) == 0
                and float(da_rec_m.get("legging_adjusted_pnl_t1000_usd", 0.0) or 0.0) >= 0.0
            )
        d1_maker_bridge = bool(
            RISK_CONFIG.get("enable_graduated_d1_box", True)
            and sl_no_loss_m
            and (box_type == "ZERO_FEE_MAKER_ANCHOR" or exp_mkr_ok)
            and _grad8_m(by_sl_map.get("D1_SAME_ORACLE_DOMINANCE_BOX") or {})
        )
        if not (own_mkr_grad or d1_maker_bridge):
            return {"executed": False, "reason": f"MAKER_ANCHOR_NOT_YET_8_OF_8_GRADUATED:{sleeve_src}"}
        if box_type == "DOMINANCE_MAKER_ANCHOR" and cand_asset in exp_d1 and not exp_mkr_ok:
            return {"executed": False, "reason": f"EXPANSION_ASSET_NOT_YET_8_OF_8_GRADUATED:{cand_asset}"}
    except Exception as exc_g:
        return {"executed": False, "reason": f"STATE_READ_ERROR:{exc_g}"}

    exp_ts = float(candidate_box.get("expiry_ts") or 0.0)
    cand_ts = float(candidate_box.get("ts_unix") or now_ts)
    max_tte_m = 64800.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else 900.0
    min_tte_m = 65.0
    if not self.dry_run and ((now_ts - cand_ts) > 5.0 or (exp_ts > 0.0 and not (min_tte_m <= (exp_ts - now_ts) <= max_tte_m))):
        return {"executed": False, "reason": "STALE_OR_OUTSIDE_TTE_WINDOW"}
    busy_mkts = {
        str(p.get("market_id") or "") for p in self.active_positions.values() if not position_is_settlement_receivable(p)
    } | {
        str(i.get("market_id") or "") for i in getattr(self, "pending_entry_intents", {}).values() if isinstance(i, dict)
    }
    if mid_a in busy_mkts or mid_b in busy_mkts:
        return {"executed": False, "reason": "MARKET_ALREADY_OCCUPIED"}

    anc_is_a = bool(candidate_box.get("anchor_is_a", True))
    tok_anc, tok_hdg = (tok_a, tok_b) if anc_is_a else (tok_b, tok_a)
    mid_anc = mid_a if anc_is_a else mid_b
    lbl_anc = str(candidate_box.get("leg_a_label" if anc_is_a else "leg_b_label") or "ANC")
    lbl_hdg = str(candidate_box.get("leg_b_label" if anc_is_a else "leg_a_label") or "HDG")
    anc_side = str(candidate_box.get("leg_a_side" if anc_is_a else "leg_b_side") or "UP").upper()
    fr_hdg = fr_b if anc_is_a else fr_a
    fe_hdg = fe_b if anc_is_a else fe_a
    _raw_nr_anc = candidate_box.get("leg_a_neg_risk" if anc_is_a else "leg_b_neg_risk")
    _raw_nr_hdg = candidate_box.get("leg_b_neg_risk" if anc_is_a else "leg_a_neg_risk")
    nr_anc = _raw_nr_anc if isinstance(_raw_nr_anc, bool) else None
    nr_hdg = _raw_nr_hdg if isinstance(_raw_nr_hdg, bool) else None
    if hasattr(self.executor, "prewarm_token_market_cache"):
        for _tm, _cm, _nrm, _frm, _fem in (
            (tok_a, str(candidate_box.get("leg_a_condition_id") or ""), candidate_box.get("leg_a_neg_risk"), fr_a, fe_a),
            (tok_b, str(candidate_box.get("leg_b_condition_id") or ""), candidate_box.get("leg_b_neg_risk"), fr_b, fe_b),
        ):
            if _cm and isinstance(_nrm, bool):
                self.executor.prewarm_token_market_cache(
                    token_id=_tm, neg_risk=_nrm, fee_rate_bps=int(round(_frm * 10000)),
                    condition_id=_cm, fee_rate=_frm, fee_exponent=_fem,
                )
    anc_bid_px = float(candidate_box.get("anchor_bid_px") or (candidate_box["leg_a_limit_price"] if anc_is_a else candidate_box["leg_b_limit_price"]))
    hdg_lim_px = float(candidate_box.get("hedge_limit_px") or (candidate_box["leg_b_limit_price"] if anc_is_a else candidate_box["leg_a_limit_price"]))
    max_pair_cap = (
        (0.992 if str(candidate_box.get("regime") or "") == "ZF_SP1_NBA" else 0.990)
        if box_type == "ZERO_FEE_MAKER_ANCHOR"
        else (0.994 if _is_rebate_mg else 0.988)
    )
    posted_spot = float(candidate_box.get("posted_spot") or 0.0)

    active_mkr_box_ids = {
        str(p.get("box_id") or k)
        for k, p in self.active_positions.items()
        if p.get("is_dominance_box")
        and not position_is_settlement_receivable(p)
        and p.get("status") not in {"UNRESOLVED_SETTLEMENT", "AWAITING_ONCHAIN_SETTLEMENT"}
        and not (float(p.get("candle_expiry_ts") or 0.0) > 0.0 and now_ts >= float(p.get("candle_expiry_ts") or 0.0))
    }
    long_tte_mkr_ids = {
        str(p.get("box_id") or k)
        for k, p in self.active_positions.items()
        if p.get("is_dominance_box")
        and not position_is_settlement_receivable(p)
        and p.get("status") not in {"UNRESOLVED_SETTLEMENT", "AWAITING_ONCHAIN_SETTLEMENT"}
        and (float(p.get("candle_expiry_ts") or 0.0) - now_ts) > 3600.0
    }
    _rcfg_bm = getattr(self, "risk_config", None) or RISK_CONFIG
    max_conc_mkr = int(_rcfg_bm.get("max_concurrent_d1_boxes", 4))
    max_tot_mkr = int(_rcfg_bm.get("max_total_portfolio_slots", 4))
    if len(active_mkr_box_ids) >= max_conc_mkr or (not self.dry_run and (len(active_mkr_box_ids) + len(self._risk_bearing_positions())) >= max_tot_mkr):
        return {"executed": False, "reason": "MAX_CONCURRENT_BOXES_REACHED"}
    if box_type == "ZERO_FEE_MAKER_ANCHOR" and exp_ts > 0.0 and (exp_ts - now_ts) > 3600.0:
        if (max_conc_mkr >= 2 and len(active_mkr_box_ids) >= (max_conc_mkr - 1)) or (not own_mkr_grad and len(long_tte_mkr_ids) >= 1):
            return {"executed": False, "reason": "INTRADAY_D1_SLOT_RESERVED"}

    from src.polymarket_research.riskless_protocol_v2_expansion import (
        extract_sll_event_group_key,
        pending_intents_cash_reserved_usd,
        pending_intents_synced_equity_usd,
        sync_pending_intents_on_collateral_refresh,
    )
    _repost_n_in = int(candidate_box.get("_bond1_repost_count") or 0)
    collat = getattr(self, "_last_known_collateral", None)
    if not self.dry_run and (collat is None or _repost_n_in > 0) and hasattr(self.executor, "get_collateral_balance"):
        _prev_c_ma = collat
        try:
            _fresh_c = await asyncio.to_thread(self.executor.get_collateral_balance)
            if isinstance(_fresh_c, (int, float)) and not isinstance(_fresh_c, bool) and math.isfinite(float(_fresh_c)) and float(_fresh_c) >= 0.0:
                collat = float(_fresh_c)
                self._last_known_collateral = collat
                sync_pending_intents_on_collateral_refresh(self, _prev_c_ma, collat)
        except Exception:
            if collat is None:
                collat = 0.0
    _pend_ma = getattr(self, "pending_entry_intents", None)
    inflight_u = pending_intents_cash_reserved_usd(_pend_ma)
    collat_f = 100.0 if self.dry_run else max(0.0, float(collat or 0.0) - inflight_u)
    cur_open_mkr = sum(
        float(p.get("notional_usd", 0.0) or 0.0)
        for p in self.active_positions.values()
        if not position_is_settlement_receivable(p)
    ) + inflight_u + pending_intents_synced_equity_usd(_pend_ma)
    port_headroom_mkr = 100.0 if self.dry_run else max(0.0, max(float(self.max_exposure), collat_f * 0.55) - cur_open_mkr)
    asset_cap = {"BTC": 18.0, "ETH": 18.0, "SOL": 16.5, "XRP": 16.5, "BNB": 15.0, "DOGE": 15.0, "HYPE": 15.0, "ZEC": 10.0, "NBA": 18.0}.get(cand_asset, 16.5)
    if cand_asset in exp_d1 and not own_asset_grad_m:
        asset_cap = min(asset_cap, 12.0)
    bridged_lot_cap = 18.0 if (own_mkr_grad and own_asset_grad_m) else 12.0
    if _is_rebate_mg:
        bridged_lot_cap = min(bridged_lot_cap, float(_gov_rb_ma.get("d1_rebate_maker_cap_usd", 12.0)))
    budget = min(bridged_lot_cap, asset_cap, max(0.0, collat_f - float(RISK_CONFIG.get("d1_box_collateral_reserve_usd", 16.50))), collat_f * 0.25, port_headroom_mkr)
    pair_est = anc_bid_px + hdg_lim_px + (fr_hdg * ((hdg_lim_px * (1.0 - hdg_lim_px)) ** fe_hdg) if fr_hdg > 0.0 else 0.0)
    if box_type == "ZERO_FEE_MAKER_ANCHOR" and exp_ts > 0.0 and (exp_ts - now_ts) > 3600.0 and pair_est > 0.986:
        return {"executed": False, "reason": f"LONG_HORIZON_VELOCITY_EV_FLOOR:{pair_est:.4f}"}
    if not (0.860 <= pair_est <= max_pair_cap + 0.003):
        return {"executed": False, "reason": f"PAIR_COST_OUT_OF_BAND:{pair_est:.4f}"}
    sh_int = int(math.floor(budget / max(0.86, pair_est)))
    if sh_int < 5:
        return {"executed": False, "reason": "INSUFFICIENT_MAKER_BOX_BUDGET"}

    inflight_key = dedupe_k or f"MKR_{mid_a}_{mid_b}"
    inflight_mkr.add(inflight_key)
    inflight_mkr_types.add(mkr_type_k)
    preempt_events = self.__dict__.setdefault("_maker_anchor_preempt_events", {})
    preempt_ev = threading.Event()
    preempt_events[inflight_key] = preempt_ev
    box_id = str(candidate_box.get("box_id") or f"MKR_LIVE_{int(now_ts)}")
    intent_id = f"{box_id}_ANC_INTENT"
    mkt_ws_mkr = getattr(self, "_pos_market_ws", None)
    if mkt_ws_mkr is not None and hasattr(mkt_ws_mkr, "subscribe_tokens_immediate"):
        mkt_ws_mkr.subscribe_tokens_immediate([tok_anc, tok_hdg])
    try:
        if self.dry_run:
            pre_bal_a, pre_bal_b = 0.0, 0.0
        else:
            _rba, _rbb = await asyncio.gather(
                asyncio.to_thread(self._wallet_token_balance, tok_a),
                asyncio.to_thread(self._wallet_token_balance, tok_b),
            )
            pre_bal_a = float((_rba[0] if isinstance(_rba, tuple) else _rba) or 0.0)
            pre_bal_b = float((_rbb[0] if isinstance(_rbb, tuple) else _rbb) or 0.0)
        if not self.dry_run and hasattr(self.executor, "get_market_book"):
            custom_mkr_bk = "get_market_book" in getattr(self.executor, "__dict__", {})
            ws_bks_m = candidate_box.get("ws_books") if not custom_mkr_bk else None
            ws_m_fresh = isinstance(ws_bks_m, dict) and (time.time() - float(candidate_box.get("ws_books_ts") or 0.0)) <= 0.65
            bk_anc_f = ws_bks_m.get(tok_anc) if ws_m_fresh else (mkt_ws_mkr.get_book(tok_anc, max_age_sec=1.5) if (mkt_ws_mkr and not custom_mkr_bk) else None)
            bk_hdg_f = ws_bks_m.get(tok_hdg) if ws_m_fresh else (mkt_ws_mkr.get_book(tok_hdg, max_age_sec=1.5) if (mkt_ws_mkr and not custom_mkr_bk) else None)
            if bk_anc_f is None or bk_hdg_f is None:
                bk_anc_f, bk_hdg_f = await asyncio.gather(
                    asyncio.to_thread(self.executor.get_market_book, tok_anc) if bk_anc_f is None else asyncio.sleep(0, result=bk_anc_f),
                    asyncio.to_thread(self.executor.get_market_book, tok_hdg) if bk_hdg_f is None else asyncio.sleep(0, result=bk_hdg_f),
                )
            asks_af = sorted([(float(x["price"] if isinstance(x, dict) else x[0]), float(x["size"] if isinstance(x, dict) else x[1])) for x in ((bk_anc_f or {}).get("asks") or []) if float(x.get("size", 0) if isinstance(x, dict) else x[1]) > 0])
            asks_hf = sorted([(float(x["price"] if isinstance(x, dict) else x[0]), float(x["size"] if isinstance(x, dict) else x[1])) for x in ((bk_hdg_f or {}).get("asks") or []) if float(x.get("size", 0) if isinstance(x, dict) else x[1]) > 0])
            if not asks_af or not asks_hf or anc_bid_px >= asks_af[0][0]:
                return {"executed": False, "reason": "FRESH_BOOK_CROSS_OR_EMPTY"}
            hdg_ask_f = asks_hf[0][0]
            hdg_av_f = sum(sz for px, sz in asks_hf if px <= hdg_ask_f + 0.01)
            hdg_fee_f = fr_hdg * ((hdg_ask_f * (1.0 - hdg_ask_f)) ** fe_hdg) if fr_hdg > 0.0 else 0.0
            hdg_h_f = min(0.25, hdg_fee_f / max(hdg_ask_f, 1e-6)) if fr_hdg > 0.0 else 0.0
            _hdg_mult_cfg = max(1.25, float(_gov_rb_full.get("synthetic_maker_min_hedge_depth_mult", 2.5) or 2.5)) if fr_hdg > 0.0 else 2.5
            if hdg_av_f < max(15.0, _hdg_mult_cfg * sh_int) or not (0.860 <= (anc_bid_px + hdg_ask_f / (1.0 - hdg_h_f)) <= max_pair_cap):
                return {"executed": False, "reason": "FRESH_HEDGE_DEPTH_OR_COST_REJECT"}
            opp_a = str(candidate_box.get("leg_a_opp_token_id") or "")
            opp_b = str(candidate_box.get("leg_b_opp_token_id") or "")
            if opp_a and opp_b:
                obk_a = ws_bks_m.get(opp_a) if ws_m_fresh else None
                obk_b = ws_bks_m.get(opp_b) if ws_m_fresh else None
                if obk_a is None or obk_b is None:
                    obk_a, obk_b = await asyncio.gather(
                        asyncio.to_thread(self.executor.get_market_book, opp_a) if obk_a is None else asyncio.sleep(0, result=obk_a),
                        asyncio.to_thread(self.executor.get_market_book, opp_b) if obk_b is None else asyncio.sleep(0, result=obk_b),
                    )
                ob_a = max((float(x["price"] if isinstance(x, dict) else x[0]) for x in ((obk_a or {}).get("bids") or [])), default=0.0)
                ob_b = max((float(x["price"] if isinstance(x, dict) else x[0]) for x in ((obk_b or {}).get("bids") or [])), default=0.0)
                ob_anc = ob_a if anc_is_a else ob_b
                ob_hdg = ob_b if anc_is_a else ob_a
                if (asks_af[0][0] + ob_anc) > 1.015 or (hdg_ask_f + ob_hdg) > 1.015 or (ob_a + ob_b) > 1.160:
                    return {"executed": False, "reason": f"ANTI_BOX_COMPLEMENT_VETO:{max(ob_a + ob_b, asks_af[0][0] + ob_anc, hdg_ask_f + ob_hdg):.4f}"}
            hdg_buf_f = 0.002 if (hdg_ask_f < 0.04 or hdg_ask_f >= 0.96) else 0.01
            max_hdg_cap_f = max(hdg_ask_f, math.floor(max(0.0, (0.992 - anc_bid_px) * (1.0 - hdg_h_f)) * 1000.0 + 1e-9) / 1000.0)
            hdg_lim_px = min(0.995, max(hdg_ask_f, min(round(hdg_ask_f + hdg_buf_f, 3), max_hdg_cap_f)))

        anc_notional = round((sh_int + 0.01) * anc_bid_px, 4)
        now_int_ts = time.time()
        _anc_res_u = round(sh_int * anc_bid_px, 4)
        _anc_evt_k = extract_sll_event_group_key(candidate_box)
        self.pending_entry_intents[intent_id] = {
            "trade_id": intent_id, "market_id": mid_anc, "token_id": tok_anc,
            "notional_usd": _anc_res_u, "posted_notional_usd": _anc_res_u, "ts": now_int_ts, "heartbeat_ts": now_int_ts,
            "live_maker_anchor_inflight": True, "inflight_key": inflight_key,
            **({"event_group_key": _anc_evt_k} if _anc_evt_k else {}),
            **({"event_id": str(candidate_box.get("event_id"))} if candidate_box.get("event_id") else {}),
        }
        post_res = await asyncio.to_thread(
            self.executor.post_maker_entry_order,
            token_id=tok_anc, price=anc_bid_px, notional_usd=anc_notional, side="BUY",
            neg_risk=nr_anc, min_price_floor=0.001, max_price_ceiling=0.995,
        )
        maker_oid = str((post_res or {}).get("orderID") or "").strip()
        if not isinstance(post_res, dict) or not post_res.get("success") or not maker_oid:
            self.pending_entry_intents.pop(intent_id, None)
            return {"executed": False, "reason": f"ANCHOR_POST_FAILED:{(post_res or {}).get('error')}"}
        posted_anc_px = float(post_res.get("price") or anc_bid_px)
        posted_anc_sh = float(post_res.get("shares") or sh_int)
        if intent_id in self.pending_entry_intents:
            self.pending_entry_intents[intent_id]["entry_order_id"] = maker_oid
            self.pending_entry_intents[intent_id]["posted_notional_usd"] = round(posted_anc_sh * posted_anc_px, 4)
            self.pending_entry_intents[intent_id]["notional_usd"] = round(posted_anc_sh * posted_anc_px, 4)
            self.pending_entry_intents[intent_id]["heartbeat_ts"] = time.time()

        if self.dry_run:
            matched_sh, avg_anc_px, anc_raw = posted_anc_sh, posted_anc_px, post_res
        else:
            ttl_s = 15.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else 10.0
            t_anc_0 = time.monotonic()
            uws = getattr(self.executor, "_user_ws_cache", None)
            max_keep_anc = 90.0 if (uws is not None and uws.is_healthy()) else ttl_s
            deadline = t_anc_0 + ttl_s
            last_hdg_chk = t_anc_0
            last_repeg_mono = t_anc_0
            adv_since_mono: Optional[float] = None
            repeg_count = 0
            adverse_cancelled = False
            ws_anc_filled = False
            matched_sh = 0.0
            avg_anc_px = posted_anc_px
            anc_raw = post_res
            _ws_shield_on = bool(_gov_rb_full.get("enable_synthetic_maker_ws_shield", True))
            _ws_zero_rest_hdg = bool(_gov_rb_full.get("enable_ws_zero_rest_maker_hedge", True))
            _repeg_deb_s = float(_gov_rb_full.get("synthetic_maker_repeg_debounce_sec", 0.50) or 0.50)
            _keep_hdg_mult = (max(1.25, float(_gov_rb_full.get("synthetic_maker_min_hedge_depth_mult", 2.0) or 2.0) - 0.5) if "synthetic_maker_min_hedge_depth_mult" in _gov_rb_full else 2.0) if fr_hdg > 0.0 else 2.0
            _custom_mkr_bk_loop = "get_market_book" in getattr(self.executor, "__dict__", {})
            while True:
                pending_repeg_px: Optional[float] = None
                while time.monotonic() < deadline:
                    if preempt_ev.is_set() or (exp_ts > 0.0 and (exp_ts - time.time()) <= (55.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else 45.0)):
                        break
                    if intent_id in self.pending_entry_intents:
                        self.pending_entry_intents[intent_id]["heartbeat_ts"] = time.time()
                    rem_w = max(0.02, min(0.05 if (_ws_shield_on and mkt_ws_mkr is not None) else 0.10, deadline - time.monotonic()))
                    if uws is not None and uws.is_healthy():
                        await uws.wait_for_fill_or_timeout(rem_w, prev_seq=uws.fill_sequence)
                        snap_o = uws.get_order_snapshot(maker_oid, max_age_sec=5.0)
                        if self._ws_snap_fully_filled(snap_o, posted_anc_sh):
                            ws_anc_filled = True
                            break
                    else:
                        await asyncio.sleep(rem_w)
                    if preempt_ev.is_set():
                        break
                    drift_bps_cur = 0.0
                    if box_type == "DOMINANCE_MAKER_ANCHOR" and posted_spot > 0.0:
                        cur_sp = await asyncio.to_thread(self.get_usd_reference_spot_price, cand_asset)
                        if cur_sp and float(cur_sp) > 0.0:
                            drift_bps_cur = (float(cur_sp) - posted_spot) / posted_spot * 10000.0
                            if (anc_side == "UP" and drift_bps_cur < -2.5) or (anc_side == "DOWN" and drift_bps_cur > 2.5):
                                adverse_cancelled = True
                                logger.info(f"[MAKER ANCHOR ADVERSE CANCEL] {box_id}: drift={drift_bps_cur:+.2f}bps against {anc_side}; canceling {maker_oid}.")
                                break
                    if box_type == "DOMINANCE_MAKER_ANCHOR":
                        _perps_ws_anc = getattr(self, "_perps_leadlag_ws", None)
                        if _perps_ws_anc is not None and bool(
                            GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("enable_perp1_maker_precancel_leadlag", True)
                        ):
                            _perp_thr_anc = float(
                                GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}).get("perp1_adverse_move_bps_300ms", 8.0) or 8.0
                            )
                            if _perps_ws_anc.should_precancel_binary_maker(
                                cand_asset, anc_side, threshold_bps=_perp_thr_anc, window_ms=300.0
                            ):
                                adverse_cancelled = True
                                logger.info(
                                    f"[MAKER ANCHOR PERP1 PRE-CANCEL] {box_id}: Perps BBO jumped >= {_perp_thr_anc:.1f}bps against {anc_side} in 300ms; canceling {maker_oid}."
                                )
                                break
                    # v5.9.0 Sub-50ms Zero-REST Sharded WS L2 Shield + Sticky #1 FIFO Repeg
                    if _ws_shield_on and mkt_ws_mkr is not None and not _custom_mkr_bk_loop:
                        bk_anc_ws = mkt_ws_mkr.get_book(tok_anc, max_age_sec=1.5)
                        bk_hdg_ws = mkt_ws_mkr.get_book(tok_hdg, max_age_sec=1.5)
                        if bk_hdg_ws is not None:
                            last_hdg_chk = time.monotonic()
                            sh_ev = evaluate_resting_synthetic_quote_tick(
                                posted_bid_px=posted_anc_px,
                                posted_shares=posted_anc_sh,
                                anchor_book=bk_anc_ws,
                                hedge_book=bk_hdg_ws,
                                hedge_fee_rate=fr_hdg,
                                hedge_fee_exponent=fe_hdg,
                                max_entry_box_cost_net=max_pair_cap,
                                max_keep_box_cost_net=max_pair_cap + 0.001,
                                min_keep_depth_mult=_keep_hdg_mult,
                                rem_tte_sec=(exp_ts - time.time()) if exp_ts > 0.0 else 300.0,
                                min_rem_tte_sec=55.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else 45.0,
                                advance_since_mono=adv_since_mono,
                                advance_debounce_sec=_repeg_deb_s,
                                repeg_count=repeg_count,
                                max_repegs=2,
                            )
                            adv_since_mono = sh_ev.get("advance_since_mono")
                            if sh_ev["action"] == "CANCEL_ADVERSE":
                                adverse_cancelled = True
                                logger.info(f"[MAKER ANCHOR WS SHIELD CANCEL] {box_id}: {sh_ev['reason']}; canceling {maker_oid}.")
                                break
                            if (
                                sh_ev["action"] == "REPEG_FIFO1"
                                and repeg_count < 2
                                and sh_ev.get("repeg_bid_px") is not None
                                and (deadline - time.monotonic()) >= 1.5
                            ):
                                pending_repeg_px = float(sh_ev["repeg_bid_px"])
                                logger.info(f"[MAKER ANCHOR WS REPEG] {box_id}: outbid -> repegging {maker_oid} to ${pending_repeg_px:.3f}.")
                                break
                    if hasattr(self.executor, "get_market_book") and (time.monotonic() - last_hdg_chk) >= 2.0:
                        last_hdg_chk = time.monotonic()
                        bk_hc = mkt_ws_mkr.get_book(tok_hdg, max_age_sec=1.5) if (mkt_ws_mkr and not _custom_mkr_bk_loop) else None
                        if bk_hc is None:
                            bk_hc = await asyncio.to_thread(self.executor.get_market_book, tok_hdg)
                        asks_hc = sorted([(float(x["price"] if isinstance(x, dict) else x[0]), float(x["size"] if isinstance(x, dict) else x[1])) for x in ((bk_hc or {}).get("asks") or []) if float(x.get("size", 0) if isinstance(x, dict) else x[1]) > 0])
                        hc_px = asks_hc[0][0] if asks_hc else 1.0
                        hc_av = sum(sz for px, sz in asks_hc if px <= hc_px + 0.01) if asks_hc else 0.0
                        hc_fee = fr_hdg * ((hc_px * (1.0 - hc_px)) ** fe_hdg) if fr_hdg > 0.0 else 0.0
                        hc_h = min(0.25, hc_fee / max(hc_px, 1e-6)) if fr_hdg > 0.0 else 0.0
                        if hc_av < max(12.0, _keep_hdg_mult * sh_int) or (posted_anc_px + hc_px / (1.0 - hc_h)) > (max_pair_cap + 0.001):
                            adverse_cancelled = True
                            break
                    if not adverse_cancelled and not preempt_ev.is_set() and uws is not None and uws.is_healthy() and time.monotonic() >= deadline - 0.05 and (time.monotonic() - t_anc_0) < max_keep_anc:
                        deadline = min(t_anc_0 + max_keep_anc, time.monotonic() + 10.0)
                cancel_res, summary, matched_sh, avg_anc_px = await self._reconcile_maker_entry_fill(
                    maker_oid,
                    tok_anc,
                    ws_anc_filled,
                    posted_anc_sh,
                    posted_anc_px,
                    (pre_bal_a if anc_is_a else pre_bal_b),
                    allow_ws_fast_fill=_ws_zero_rest_hdg,
                )
                c_out_m = str((cancel_res or {}).get("outcome") or "")
                is_canc_m = bool((cancel_res or {}).get("is_canceled"))
                if not is_canc_m and c_out_m != "FILLED" and (summary is None or not summary.get("terminal")) and matched_sh < 0.01:
                    self.pending_entry_intents.pop(intent_id, None)
                    st_lock = getattr(self, "_state_save_lock", None) or self._GLOBAL_STATE_SAVE_LOCK
                    with st_lock:
                        self._register_unknown_d1_box_legs(box_id, candidate_box, {"outcome_unknown": True, "orderID": maker_oid}, pre_bal_a, pre_bal_b)
                    return {"executed": False, "reason": "ANCHOR_CANCEL_OUTCOME_UNKNOWN"}
                anc_raw = summary or cancel_res or post_res
                if (
                    matched_sh < 0.01
                    and is_canc_m
                    and pending_repeg_px is not None
                    and not adverse_cancelled
                    and repeg_count < 2
                    and not preempt_ev.is_set()
                ):
                    rp_notional = round((sh_int + 0.01) * pending_repeg_px, 4)
                    rp_res = await asyncio.to_thread(
                        self.executor.post_maker_entry_order,
                        token_id=tok_anc, price=pending_repeg_px, notional_usd=rp_notional, side="BUY",
                        neg_risk=nr_anc, min_price_floor=0.001, max_price_ceiling=0.995,
                    )
                    rp_oid = str((rp_res or {}).get("orderID") or "").strip()
                    if isinstance(rp_res, dict) and rp_res.get("success") and rp_oid:
                        maker_oid = rp_oid
                        posted_anc_px = float(rp_res.get("price") or pending_repeg_px)
                        posted_anc_sh = float(rp_res.get("shares") or sh_int)
                        post_res = rp_res
                        repeg_count += 1
                        last_repeg_mono = time.monotonic()
                        if intent_id in self.pending_entry_intents:
                            self.pending_entry_intents[intent_id]["entry_order_id"] = maker_oid
                            self.pending_entry_intents[intent_id]["posted_notional_usd"] = round(posted_anc_sh * posted_anc_px, 4)
                            self.pending_entry_intents[intent_id]["notional_usd"] = round(posted_anc_sh * posted_anc_px, 4)
                            self.pending_entry_intents[intent_id]["heartbeat_ts"] = time.time()
                        continue
                break
            self.pending_entry_intents.pop(intent_id, None)
            if matched_sh < 0.01:
                if box_type == "ZERO_FEE_MAKER_ANCHOR" and exp_ts > 0.0 and (exp_ts - time.time()) > 1800.0:
                    unfilled_cd = 90.0 if not bool(candidate_box.get("queue_front", True)) else 45.0
                else:
                    unfilled_cd = 8.0 if adverse_cancelled else 2.0
                retry_cd[dedupe_k] = time.time() + unfilled_cd
                return {"executed": False, "reason": "MAKER_ANCHOR_EXPIRED_UNFILLED"}

        self.pending_entry_intents.pop(intent_id, None)
        if not self.dry_run and hasattr(self.executor, "get_market_book"):
            _use_ws_h2 = bool(_gov_rb_full.get("enable_ws_zero_rest_maker_hedge", True)) and ("get_market_book" not in getattr(self.executor, "__dict__", {}))
            bk_h2 = mkt_ws_mkr.get_book(tok_hdg, max_age_sec=0.80) if (_use_ws_h2 and mkt_ws_mkr is not None) else None
            if bk_h2 is None:
                bk_h2 = await asyncio.to_thread(self.executor.get_market_book, tok_hdg)
            asks_h2 = sorted([(float(x["price"] if isinstance(x, dict) else x[0]), float(x["size"] if isinstance(x, dict) else x[1])) for x in ((bk_h2 or {}).get("asks") or []) if float(x.get("size", 0) if isinstance(x, dict) else x[1]) > 0])
            if asks_h2:
                h2_px = asks_h2[0][0]
                h2_fee = fr_hdg * ((h2_px * (1.0 - h2_px)) ** fe_hdg) if fr_hdg > 0.0 else 0.0
                h2_h = min(0.25, h2_fee / max(h2_px, 1e-6)) if fr_hdg > 0.0 else 0.0
                h2_buf = 0.002 if (h2_px < 0.04 or h2_px >= 0.96) else 0.01
                h2_cap = max(h2_px, math.floor(max(0.0, (0.992 - avg_anc_px) * (1.0 - h2_h)) * 1000.0 + 1e-9) / 1000.0)
                hdg_lim_px = min(0.995, max(h2_px, min(round(h2_px + h2_buf, 3), h2_cap)))

        res = await asyncio.to_thread(
            self.executor.execute_maker_anchor_hedge_or_unwind,
            box_id=box_id, anchor_token_id=tok_anc, anchor_label=lbl_anc, anchor_price=avg_anc_px,
            anchor_matched_shares=matched_sh, anchor_order_id=maker_oid,
            hedge_token_id=tok_hdg, hedge_label=lbl_hdg, hedge_limit_price=hdg_lim_px,
            max_box_cost_net=0.993, hedge_fee_rate=fr_hdg, hedge_fee_exponent=fe_hdg,
            anchor_neg_risk=nr_anc, hedge_neg_risk=nr_hdg,
            anchor_pre_balance=(pre_bal_a if anc_is_a else pre_bal_b),
            hedge_pre_balance=(pre_bal_b if anc_is_a else pre_bal_a),
            anchor_raw=anc_raw,
        )
        st_lock = getattr(self, "_state_save_lock", None) or self._GLOBAL_STATE_SAVE_LOCK
        leg_tids: List[str] = []
        with st_lock:
            if dedupe_k:
                self._record_seen_d1_box_key(dedupe_k)
            if res.get("success") and isinstance(res.get("leg_1"), dict) and isinstance(res.get("leg_2"), dict):
                leg_tids = self._register_live_d1_box_positions(box_id, candidate_box, res, pre_bal_a, pre_bal_b)
            elif res.get("outcome_unknown"):
                self._register_unknown_d1_box_legs(box_id, candidate_box, res, pre_bal_a, pre_bal_b)
            elif isinstance(res.get("residual_unhedged_leg"), dict):
                self.executor.invalidate_collateral_cache()
                self._pending_collateral_refresh = True
                resid = res["residual_unhedged_leg"]
                if float(resid.get("residual_shares") or 0.0) > 0.01 or resid.get("unwind_outcome_unknown"):
                    leg_tids = self._register_legged_out_d1_residual(box_id, candidate_box, resid, pre_bal_a, pre_bal_b)
                else:
                    self._record_inline_d1_legged_out_close(box_id, candidate_box, resid, res)
                    if self.closed_positions:
                        _unw_pnl = float(self.closed_positions[-1].get("net_pnl_usd") or 0.0)
                        if _unw_pnl < 0.0:
                            _unwind_brk.record_unwind_pnl(sleeve_src, _unw_pnl)
        return {"executed": bool(res.get("success")), "result": res, "leg_trade_ids": leg_tids}
    finally:
        self.pending_entry_intents.pop(intent_id, None)
        inflight_mkr.discard(inflight_key)
        inflight_mkr_types.discard(mkr_type_k)
        preempt_events.pop(inflight_key, None)

async def _hv__evaluate_shock_and_execute_impl(self, shock: Dict[str, Any]):
    _tr = _CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
    _hctx = _PRE_HOT_CTX.get()
    def _defer_info(msg: str) -> None:
        if _hctx is not None and not self.dry_run:
            _hctx[0].append(msg)
        else:
            logger.info(msg)
    def _g(c: str, d: str = "", **kw: Any) -> None:
        if _tr is not None:
            _tr.set(gate_code=c, gate_detail=d, **kw)
    # P1 Invariant: Durable Event Idempotency Check
    shock_id = shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
    legacy_evt = shock.get("event_id")
    if shock_id in self.seen_shock_ids or (legacy_evt and legacy_evt != str(shock.get("market_id")) and legacy_evt in self.seen_shock_ids):
        if _tr is not None:
            _tr.set(skip_forensic=True)
        logger.debug(f"[IDEMPOTENCY] Trigger event {shock_id} already executed or seen. Skipping duplicate trigger.")
        return
    self.last_event_id = shock_id

    # P0 #3: Hard Circuit Breaker & Kill Switch Gate Check
    if self.risk_controller.is_halted() or getattr(self, "risk_halt", False):
        _g("CIRCUIT_BREAKER", f"Halted: {self.global_halt_reasons}")
        logger.warning(f"[CIRCUIT BREAKER BLOCKED] Refusing new order entry: risk controller or global reconciliation halt active ({self.global_halt_reasons}).")
        return

    # Market-scoped reconciliation check (Task 1: blast radius reduction)
    m_id = str(shock.get("market_id") or "")
    if m_id and m_id in self._reconciling_market_ids():
        logger.warning(f"[MARKET RECONCILIATION BLOCKED] Market {m_id} has unresolved ENTRY_OUTCOME_UNKNOWN. Refusing new entry on this market.")
        return

    # P0 Recovery Guard (Round 9 unified policy): any pipeline-wide unknown outcome blocks entries.
    live_reasons = self._global_halt_reasons()
    if live_reasons or (self.risk_halt and not getattr(self, "_startup_reconciled", False)):
        self._refresh_global_halt()
        logger.warning(f"[GLOBAL ENTRY BLOCKED] Refusing new order entry: unresolved global reconciliation {live_reasons}.")
        return

    # Concurrency Guard: Enforce maximum concurrent risk-bearing positions (MAX_CONCURRENT_POSITIONS = 3)
    risk_positions = self._risk_bearing_positions()
    in_flight_intents = [
        k for k, v in self.pending_entry_intents.items()
        if k not in risk_positions and not (isinstance(v, dict) and v.get("live_maker_anchor_inflight"))
    ]
    _rcfg_cg = getattr(self, "risk_config", None) or RISK_CONFIG
    _cg_tte = float(shock.get("seconds_to_expiry", 3600.0) or 3600.0)
    _cg_orth_bnd = bool(
        not self.dry_run
        and bool(_rcfg_cg.get("enable_orthogonal_boundary_slot", True))
        and 12.0 <= _cg_tte <= 45.0
        and (shock.get("shock_source") == "BOUNDARY_LOCK" or shock.get("regime_override") == "REGIME_D_BOUNDARY_LOCK" or abs(float(shock.get("candle_distance_pct", 0.0) or 0.0)) >= 0.08)
        and len(risk_positions) + len(in_flight_intents) == 1
        and not any(p.get("sleeve") == "SLEEVE_4_BOUNDARY_SNIPE" for p in risk_positions.values())
    )
    if self._is_v5_unleashed_active() and not self._is_unlimited_slots_active():
        _cg_lim = self._effective_directional_slot_cap(time.time())
        _cg_tot_slots = max(int(_rcfg_cg.get("max_total_portfolio_slots", 4)), 8)
        _enforce_tot_slots = (len(self._active_box_ids()) + len(risk_positions) + len(in_flight_intents)) >= _cg_tot_slots
    else:
        _cg_lim = max(self.max_concurrent_positions, 2) if _cg_orth_bnd else self.max_concurrent_positions
        _cg_tot_slots = int(_rcfg_cg.get("max_total_portfolio_slots", 4))
        _enforce_tot_slots = (
            not self.dry_run
            and not getattr(self, "allow_cli_concurrency", False)
            and (len(self._active_box_ids()) + len(risk_positions) + len(in_flight_intents)) >= _cg_tot_slots
        )
    if len(risk_positions) + len(in_flight_intents) >= _cg_lim or _enforce_tot_slots:
        _g("CONCURRENCY_LIMIT", f"Slots full ({len(risk_positions)}+{len(in_flight_intents)}>={_cg_lim})")
        logger.debug(
            f"[CONCURRENCY LIMIT] Total positions count ({len(risk_positions)} active + {len(in_flight_intents)} pending) "
            f">= limit ({_cg_lim}). Enforced."
        )
        return

    self._record_seen_shock_id(shock_id)
    if legacy_evt and legacy_evt != str(shock.get("market_id")):
        self._record_seen_shock_id(legacy_evt)

    # P1: Heartbeat Degradation Escalation - Halt new entries while keeping existing positions supervised
    if not self.dry_run and not self.executor.is_heartbeat_healthy():
        logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat has failed {self.executor.heartbeat_failures} times. Halting new entries.")
        self.risk_controller.halted = True
        self.risk_controller.halt_reason = f"Heartbeat degraded ({self.executor.heartbeat_failures} consecutive drops) - new entries halted; existing positions remain supervised."
        self.save_state()
        return

    now_hour = time.time() // 3600
    if now_hour != self.current_hour_window:
        self.current_hour_window = now_hour
        self.trades_this_hour = 0

    # Track current active portfolio exposure
    # (resolved-market redemption receivables carry no price risk and are excluded)
    risk_positions = self._risk_bearing_positions()
    current_exposure = sum(float(pos.get("notional_usd", 0.0) or 0.0) for pos in risk_positions.values())
    # Round 10 P0-01: unresolved in-flight directional entry intents are committed capital too
    # (riskless maker-anchor/BOND1 intents carry zero directional price risk, matching _risk_bearing_positions).
    current_exposure += sum(
        float(i.get("notional_usd", 0.0) or 0.0)
        for k, i in self.pending_entry_intents.items()
        if k not in risk_positions and not (isinstance(i, dict) and i.get("live_maker_anchor_inflight"))
    )

    shock_dir = shock.get("shock_direction")  # "BUY" or "SELL"
    if not shock_dir:
        if _tr is not None:
            _tr.set(skip_forensic=True)
        return

    target_token = "UP" if shock_dir == "BUY" else "DOWN"
    if _tr is not None:
        _tr.set(side=target_token)

    # Time-to-Expiry (TTE) Guard: Must be in sweet spot (30s <= TTE <= max_tte; extended for Sleeve 3 & Boundary Lock)
    tte = float(shock.get("seconds_to_expiry", 3600.0) or 3600.0)
    is_sleeve3_strike = bool(
        shock.get("sleeve") == "SLEEVE_3_STRIKE_CONVERGENCE"
        or shock.get("shock_source") == "EXP316_TRACK_A_CONVERGENCE"
    )
    _pre_dist_abs = abs(float(shock.get("candle_distance_pct", 0.0) or 0.0))
    _pre_z_abs = max(
        abs(float(shock.get("z_val") or shock.get("z_score") or shock.get("shock_z") or 0.0)),
        (_pre_dist_abs / 0.03) if (12.0 <= tte <= 60.0 and _pre_dist_abs >= 0.08) else 0.0,
    )
    is_boundary_lock_cand = bool(
        shock.get("shock_source") == "BOUNDARY_LOCK"
        or shock.get("regime_override") == "REGIME_D_BOUNDARY_LOCK"
        or (12.0 <= tte <= 90.0 and _pre_z_abs >= 3.0)
    )
    eff_max_tte = max(self.max_tte, 10800.0) if is_sleeve3_strike else self.max_tte
    eff_min_tte = 12.0 if is_boundary_lock_cand else 30.0
    if tte > eff_max_tte or tte < eff_min_tte:
        _g("TTE_OUT_OF_RANGE", f"TTE {tte:.0f}s outside [{eff_min_tte:.0f}s, {eff_max_tte:.0f}s]", tte_s=tte)
        return

    # Strict Per-Market Mutual Exclusion: Maximum 1 position per market_id (with Win-Reset Re-Entry)
    # Never hold both UP and DOWN on the same candle ($1.62 total cost for $1.00 binary payoff).
    # Win-Reset Re-Entry: Allow a 2nd trade in the same hourly candle ONLY IF Trade #1 closed with won=True and net_pnl_usd > 0.
    if m_id:
        active_for_market = any(
            p.get("market_id") == m_id
            for p in self.active_positions.values()
        )
        intent_for_market = (
            m_id in (getattr(self, "_inflight_eval_markets", None) or set())
            or any(
                i.get("market_id") == m_id
                for i in self.pending_entry_intents.values()
            )
        )
        trades_for_market = self.trades_per_market.get(m_id, 0)

        is_win_reentry = False
        is_loss_locked = False
        if trades_for_market >= 1 and not active_for_market and not intent_for_market:
            closed_for_mkt = [
                p for p in self.closed_positions
                if p.get("market_id") == m_id
            ]
            if closed_for_mkt:
                last_closed = closed_for_mkt[-1]
                if last_closed.get("won") is True and float(last_closed.get("net_pnl_usd", 0.0) or 0.0) > 0.0:
                    is_win_reentry = (trades_for_market == 1 and self.max_trades_per_market >= 2)
                else:
                    is_loss_locked = True

        market_limit_reached = True if is_loss_locked else ((trades_for_market >= 2) if is_win_reentry else (trades_for_market >= self.max_trades_per_market))
        if active_for_market or intent_for_market or market_limit_reached:
            _g("MARKET_DEDUP", f"Already active/traded ({trades_for_market})")
            logger.debug(
                f"[MARKET DEDUP REJECT] Position/intent already active or traded for {m_id}. "
                f"trades={trades_for_market}, win_reentry={is_win_reentry}"
            )
            return

    # Asset Tier Guard: Only trade vetted Tier 1 Core assets (BTC, ETH)
    title_str = str(shock.get("title", "") or "")
    title_lower = title_str.lower()
    horizon = str(shock.get("horizon", "") or shock.get("candle_interval", "")).lower()
    slug = str(shock.get("series_slug", "") or shock.get("slug", "")).lower()
    open_ts_val = float(shock.get("candle_open_ts") or 0.0)
    close_ts_val = float(shock.get("candle_expiry_ts") or shock.get("expiry_ts") or 0.0)
    duration_val = (close_ts_val - open_ts_val) if (close_ts_val > open_ts_val > 0) else 0.0

    # Detect 5m vs 15m sub-hourly contracts explicitly (check 15m first because "5m" is a substring of "15m"!)
    has_subhourly_time_range = any(m in title_lower for m in (":05", ":10", ":15", ":20", ":25", ":30", ":35", ":40", ":45", ":50", ":55"))
    is_15m_hint = any(x in horizon or x in slug or x in title_lower for x in ("15m", "900s"))
    is_5m = not is_15m_hint and (
        horizon in ("5m", "5min", "5", "300", "300s")
        or any(x in slug or x in title_lower for x in ("-5m", " 5m", "5-minute", "5 minute", "300s"))
        or (0.0 < duration_val <= 330.0)
    )
    is_15m = not is_5m and (
        is_15m_hint
        or (330.0 < duration_val <= 900.0)
        or has_subhourly_time_range
    )
    is_subhourly = is_5m or is_15m
    is_1h = not is_subhourly and (
        any(x in horizon or x in slug or x in title_lower for x in ("1h", "hourly", "60m"))
        or (duration_val >= 3500.0)
        or ("am et" in title_lower or "pm et" in title_lower)
    )
    if _tr is not None:
        _tr.set(horizon="5m" if is_5m else ("15m" if is_subhourly else ("1h" if is_1h else horizon)), tte_s=tte)

    if os.environ.get("PM_DISABLE_NYSE_BLACKOUT") != "1" and is_1h:
        now_dt = datetime.fromtimestamp(shock.get("t0_unix", time.time()), tz=timezone.utc)
        if _NY_TZ is not None:
            ny_dt = now_dt.astimezone(_NY_TZ)
            is_nyse_open_window = (ny_dt.weekday() < 5 and ny_dt.hour == 9 and 15 <= ny_dt.minute < 32)
        else:
            is_nyse_open_window = (now_dt.weekday() < 5 and now_dt.hour == 13 and 15 <= now_dt.minute < 32)
        if is_nyse_open_window:
            _g("NYSE_OPEN_BLACKOUT", "Rejecting 1h entry during 09:15-09:32 ET window")
            logger.info(f"[NYSE_OPEN_BLACKOUT] {shock.get('title')!r}: Rejecting 1h entry during 09:15-09:32 ET window.")
            return

    dist_pct = float(shock.get("candle_distance_pct", 0.0) or 0.0)
    open_spot_cand = (
        shock.get("candle_open_spot")
        if is_subhourly
        else (shock.get("finalized_1h_open") or shock.get("candle_open_spot"))
    )
    spot_at_t0 = float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
    t0_u = float(shock.get("t0_unix", time.time()))
    cur_h_idx = int(t0_u // 3600)

    _res_source_lower = str(shock.get("resolution_source") or "").lower()
    _uses_chainlink_twap = ("chain.link" in _res_source_lower) or (is_subhourly and "binance" not in _res_source_lower)
    twap_60s_open = float(shock.get("twap_60s_open") or 0.0)
    cl_open_spot = float(shock.get("chainlink_open_spot") or 0.0)
    auth_cl_open = float(shock.get("authoritative_chainlink_open") or 0.0)
    usd_spot_t0, usd_twap_t0 = self._resolve_true_usd_spot_from_shock(shock)
    _is_usd_oracle = False
    if _uses_chainlink_twap and auth_cl_open > 0.0 and math.isfinite(auth_cl_open):
        if usd_spot_t0 > 0.0 and math.isfinite(usd_spot_t0):
            _is_usd_oracle = True
            open_spot_cand = auth_cl_open
            dist_pct = ((usd_spot_t0 - auth_cl_open) / auth_cl_open) * 100.0
        elif not self.dry_run:
            _g("ORACLE_PROVENANCE_REJECT", f"USD open ${auth_cl_open:,.2f} lacks verified USD spot anchor")
            logger.info(f"[ORACLE PROVENANCE REJECT] {shock.get('title')!r}: USD open ${auth_cl_open:,.2f} lacks verified USD spot anchor.")
            return
    elif _uses_chainlink_twap and open_spot_cand and float(open_spot_cand) > 0.0:
        raw_open_ref = float(open_spot_cand)
        anchor_candidates = [raw_open_ref]
        if twap_60s_open > 0.0:
            anchor_candidates.append(twap_60s_open)
        if cl_open_spot > 0.0 and abs(cl_open_spot - raw_open_ref) / raw_open_ref < 0.005:
            anchor_candidates.append(cl_open_spot)
        if len(anchor_candidates) > 1:
            wick_div_pct = (abs(raw_open_ref - twap_60s_open) / raw_open_ref * 100.0) if twap_60s_open > 0.0 else 0.0
            dual_open_ref = max(anchor_candidates) if target_token == "UP" else min(anchor_candidates)
            open_spot_cand = dual_open_ref
            if spot_at_t0 > 0.0:
                dist_pct = ((spot_at_t0 - dual_open_ref) / dual_open_ref) * 100.0
            if wick_div_pct >= 0.0395 and abs(dist_pct) < 0.10:
                _g("BOUNDARY_WICK_VETO", f"1s open diverges from 60s TWAP by {wick_div_pct:.4f}% >= 0.0395%")
                logger.info(
                    f"[BOUNDARY WICK VETO] {shock.get('title')!r} {target_token}: "
                    f"1s tick open (${raw_open_ref:,.2f}) diverges from 60s TWAP (${twap_60s_open:,.2f}) by "
                    f"{wick_div_pct:.4f}% >= 0.0395% (dual_cush={abs(dist_pct):.4f}% < 0.10%). Skipping oracle-wick trap."
                )
                return

    asset_chk = str(shock.get("asset", "")).upper() or (
        "BTC" if ("btc" in title_lower or "bitcoin" in title_lower) else ("ETH" if ("eth" in title_lower or "ethereum" in title_lower) else ("SOL" if ("sol" in title_lower or "solana" in title_lower) else ""))
    )
    if is_1h and asset_chk in ("BTC", "ETH", "SOL") and open_spot_cand and math.isfinite(float(open_spot_cand)) and float(open_spot_cand) > 0.0:
        self.hourly_candle_opens.setdefault(asset_chk, {})[cur_h_idx] = float(open_spot_cand)

    # Self-healing fallback strictly restricted to 1-hour markets:
    if is_1h and (abs(dist_pct) < 0.0001 or not open_spot_cand or float(open_spot_cand) <= 0.0) and spot_at_t0 > 0.0:
        cached_open = self.hourly_candle_opens.get(asset_chk, {}).get(cur_h_idx)
        if cached_open and cached_open > 0.0:
            dist_pct = ((spot_at_t0 - cached_open) / cached_open) * 100.0
            open_spot_cand = cached_open

    # Phase 4 (Sleeve 5) Shadow Scanner: Cache :45-:00 overlapping 15m/1h books and log box arbs
    if not self.dry_run and asset_chk in ("BTC", "ETH", "SOL", "XRP") and open_spot_cand:
        self._update_shadow_phase4_monotonicity_scanner(
            shock, asset_chk, bool(is_subhourly), bool(is_1h), float(tte), float(open_spot_cand)
        )

    # v3.9.1 WFO Rank #1 Cushion Floor (min_cushion = 0.0004 = 0.04% in live mode; 0.05% legacy dry-run)
    if _tr is not None:
        _tr.set(dist_pct=dist_pct)
    min_dist = 0.04 if (not self.dry_run) else 0.05
    if abs(dist_pct) < min_dist:
        _g("CUSHION_TOO_SMALL", f"abs(dist)={abs(dist_pct):.4f}% < {min_dist:.2f}%")
        return
    if target_token == "UP" and dist_pct < min_dist:
        _g("CUSHION_TOO_SMALL", f"UP shock but spot {dist_pct:+.4f}% vs open")
        return
    if target_token == "DOWN" and dist_pct > -min_dist:
        _g("CUSHION_TOO_SMALL", f"DOWN shock but spot {dist_pct:+.4f}% vs open")
        return

    m_id = str(shock.get("market_id") or "")
    token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})
    token_id = token_features.get("token_id")
    if not token_id and m_id:
        token_id = await asyncio.to_thread(self.get_token_id, m_id, target_token)

    asset_str = str(shock.get("asset", "")).upper()
    if not asset_str:
        asset_str = (
            "BTC" if ("btc" in title_lower or "bitcoin" in title_lower)
            else ("ETH" if ("eth" in title_lower or "ethereum" in title_lower)
            else ("SOL" if ("sol" in title_lower or "solana" in title_lower)
            else ("XRP" if ("xrp" in title_lower or "ripple" in title_lower) else "")))
        )
    if not asset_str and self.dry_run:
        asset_str = "BTC"  # Dry-run / test fixture simulation fallback
    base_allowed = self.get_graduated_allowed_assets()
    _dir_gov_s = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {}) if self._is_v5_live_strict() else {}
    _paused_dir_s3 = {str(x).upper() for x in (_dir_gov_s.get("paused_directional_assets") or [])}
    effective_allowed_assets = ((base_allowed | {"SOL"}) - _paused_dir_s3) if is_sleeve3_strike else base_allowed
    _min_dir_eq = float(_dir_gov_s.get("min_live_equity_for_unhedged_directional_usd", 0.0) or 0.0)
    _enforce_seed_dir_gate = bool(
        getattr(self, "enforce_seed_directional_shadow_gate", False)
        or (
            not self.dry_run
            and self._is_v5_live_strict()
            and getattr(self.executor, "client", None) is not None
            and type(getattr(self.executor, "client", None)) is not object
            and getattr(getattr(self.executor, "client", None), "_mock_children", None) is None
            and "execute_snipe_order_async" not in getattr(self.executor, "__dict__", {})
            and "place_passive_maker_entry" not in getattr(self.executor, "__dict__", {})
            and "get_market_book_async" not in getattr(self.executor, "__dict__", {})
        )
    )
    _cur_eq_dir = float(getattr(self, "_last_known_collateral", 0.0) or 0.0) + sum(
        float(p.get("notional_usd", 0.0) or 0.0) for p in self.active_positions.values() if isinstance(p, dict)
    )
    _riskless_only_dir = bool(_dir_gov_s.get("riskless_only_mode", False))
    _seed_dir_paused = bool(
        _enforce_seed_dir_gate
        and (_riskless_only_dir or (_min_dir_eq > 0.0 and _cur_eq_dir < _min_dir_eq))
    )
    if not asset_str or asset_str not in effective_allowed_assets or _seed_dir_paused:
        if asset_str in ("BTC", "ETH", "SOL", "XRP") and (_seed_dir_paused or asset_str in ("ETH", "SOL", "XRP")):
            # Priority A: Record candidate in shadow mode without live capital risk
            shadow_cand = {
                "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                "asset": asset_str,
                "horizon": "15m" if is_subhourly else "1h",
                "market_id": m_id,
                "title": shock.get("title"),
                "target_token": target_token,
                "token_id": token_id or f"{asset_str}_SHADOW",
                "dist_pct": dist_pct,
                "tte_seconds": tte,
                "best_ask": token_features.get("best_ask"),
                "vwap_$25": token_features.get("vwap_$25"),
                "age_ask_ms": token_features.get("age_ask_ms"),
                "shock_volume_100ms": shock.get("shock_volume_100ms"),
                "shock_ofi": shock.get("shock_ofi"),
                "spot_at_t0": spot_at_t0,
                "candle_open_spot": open_spot_cand,
                "twap_60s_open": shock.get("twap_60s_open"),
                "resolution_source": shock.get("resolution_source", ""),
                "expiry_ts": close_ts_val,
                "reason_blocked": (
                    "RISKLESS_ONLY_MODE_SHADOW"
                    if (_seed_dir_paused and _riskless_only_dir)
                    else (f"SEED_REBUILD_SHADOW_UNTIL_${_min_dir_eq:.0f}" if _seed_dir_paused else "ASSET_PAUSED_SHADOW_ONLY")
                ),
            }
            _sh_line = json.dumps(shadow_cand) + "\n"

            def _write_shadow_cand(_ln: str = _sh_line, _p: Path = COUNTERFACTUAL_CANDIDATES_FILE) -> None:
                try:
                    with open(_p, "a") as f:
                        f.write(_ln)
                except Exception as e:
                    logger.debug(f"Failed to record {asset_str} shadow candidate: {e}")

            try:
                asyncio.get_running_loop().run_in_executor(_get_hot_io_pool(), _write_shadow_cand)
            except RuntimeError:
                _write_shadow_cand()
            logger.info(f"[SHADOW_{asset_str}_COLLECTED] {shock.get('title')} {target_token} recorded for shadow research (live trading paused).")
        if _seed_dir_paused:
            _g("SHADOW_SEED_REBUILD_GATE", f"Shadow-only until equity >= ${_min_dir_eq:.0f} (now ${_cur_eq_dir:.2f}); 100% live capital in 0-loss Arb & Carry", asset=asset_str)
        else:
            _g("SHADOW_ASSET_PAUSED" if asset_str in ("ETH", "SOL", "XRP") else "ASSET_DISALLOWED", f"{asset_str} paused (shadow only)", asset=asset_str)
        logger.debug(f"[TIER GUARD] Asset {asset_str!r} paused/shadow-gated (eq={_cur_eq_dir:.2f}). Skipping.")
        return

    # Real Polygon CTF ERC-1155 conditional token IDs are 20+ digit base-10 uint256 strings.
    is_real_ctf_token = bool(token_id and str(token_id).isdigit() and len(str(token_id)) >= 20)
    is_synthetic_test = not is_real_ctf_token
    _is_live_real = (not self.dry_run) and is_real_ctf_token

    if _is_live_real:
        if shock.get("clob_ws_connected") is False:
            _g("CLOB_WS_DISCONNECTED", "Recorder CLOB WS disconnected at trigger time")
            logger.warning(f"[CLOB_WS_DISCONNECTED_REJECT] {shock.get('title')!r}: Recorder CLOB WS disconnected at trigger time. Skipping.")
            return
        _exch_ts_ms = float(shock.get("exchange_event_ts_ms") or 0.0)
        _t0_val = float(shock.get("t0_unix") or time.time())
        if _exch_ts_ms > 0.0:
            _exch_lag_ms = (_t0_val * 1000.0) - _exch_ts_ms
            if _tr is not None:
                _tr.set(exch_lag_ms=_exch_lag_ms)
            if _exch_lag_ms > 1000.0:
                _g("EXCHANGE_LAG_REJECT", f"exchange_lag={_exch_lag_ms:.0f}ms > 1000ms")
                logger.warning(
                    f"[EXCHANGE_LAG_REJECT] {shock.get('title')!r}: exchange_lag={_exch_lag_ms:.1f}ms > 1000ms ceiling (socket burst-drain veto)."
                )
                return
        _ingress_age_s = time.time() - _t0_val
        if _ingress_age_s > 2.0:
            _g("STALE_TRIGGER_INGRESS", f"trigger ingress age {_ingress_age_s*1000:.0f}ms > 2000ms")
            logger.warning(
                f"[STALE_TRIGGER_INGRESS_REJECT] {shock.get('title')!r}: trigger age {_ingress_age_s:.2f}s > 2.0s ceiling. Skipping."
            )
            return

    if _is_live_real and _uses_chainlink_twap and open_spot_cand and float(open_spot_cand) > 0.0:
        if _is_usd_oracle:
            # 15m/5m crypto Chainlink Data Streams settle on a 60s USD TWAP at expiry; for TTE >= 60s (before the
            # settlement TWAP window begins), instantaneous USD spot is the martingale expectation of that future TWAP.
            dist_pct = ((usd_spot_t0 - float(open_spot_cand)) / float(open_spot_cand)) * 100.0
        elif spot_at_t0 > 0.0:
            _vdiv_raw = shock.get("venue_divergence_centered_bps")
            if _vdiv_raw is None:
                _vdiv_raw = shock.get("venue_divergence_bps")
            _spot_refs = [spot_at_t0]
            if _vdiv_raw is not None:
                _vdiv_clamped = max(-30.0, min(30.0, float(_vdiv_raw or 0.0)))
                _spot_refs.append(spot_at_t0 * (1.0 - 0.5 * _vdiv_clamped / 10000.0))
            _eff_spot_ref = min(_spot_refs) if target_token == "UP" else max(_spot_refs)
            dist_pct = ((_eff_spot_ref - float(open_spot_cand)) / float(open_spot_cand)) * 100.0

    # Pillar 1: Composite Edge & Stale-Quote Scoring Function (evaluated on authoritative True-USD dist_pct)
    if _tr is not None:
        _tr.set(asset=asset_str, dist_pct=dist_pct)
    _v5_live_strict = bool(_is_live_real and self._is_v5_live_strict())
    if _is_live_real:
        _t0_ba = float(token_features.get("best_ask") or 0.0)
        _t0_asz = float(token_features.get("ask_size_l1") or 0.0)
        _t0_rasks = token_features.get("raw_top_asks")
        if _t0_ba >= 0.995 and _t0_asz <= 0.0 and (_t0_rasks is None or (isinstance(_t0_rasks, list) and len(_t0_rasks) == 0)):
            _t0_bb = float(token_features.get("best_bid") or 0.0)
            if _v5_live_strict:
                _v5_d_t0 = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {})
                _eff_cap_t0 = (
                    max(float(_v5_d_t0.get("max_taker_price_15m", 0.82)), float(_v5_d_t0.get("max_maker_price_15m", 0.72)))
                    if is_subhourly
                    else max(float(_v5_d_t0.get("max_taker_price_1h", 0.82)), float(_v5_d_t0.get("max_maker_price_1h", 0.76)))
                )
            else:
                _eff_cap_t0 = float(self.max_price_ceiling)
            if _t0_bb > _eff_cap_t0:
                _g(
                    "PRICE_BAND_REJECT",
                    f"Book pinned @${_t0_bb:.2f} bid with 0 resting asks (> ${_eff_cap_t0:.2f} cap)",
                    eval_bid=_t0_bb,
                    eval_ask=1.0,
                    cap_px=_eff_cap_t0,
                    book_age_ms=float(token_features.get("age_bid_ms") or 1000.0),
                )
                return
            if _t0_bb <= 0.0:
                _g("NO_RESTING_ASKS", "Empty two-sided book at t0 (bid=$0.00, 0 resting asks)", eval_bid=0.0, eval_ask=1.0)
                return
    edge_info = (
        compute_composite_edge_score({**shock, "candle_distance_pct": dist_pct}, v5_wfo_parity=True)
        if _v5_live_strict
        else compute_composite_edge_score({**shock, "candle_distance_pct": dist_pct})
    )
    if edge_info.get("veto", False):
        _g("COMPOSITE_EDGE_VETO", str(edge_info.get("veto_reason") or ""))
        logger.info(
            f"[COMPOSITE_EDGE_VETO] {shock.get('title')!r}: Vetoed by edge scoring: {edge_info.get('veto_reason')}"
        )
        return
    edge_tier = edge_info.get("tier", "TIER_B_STANDARD")
    edge_score = edge_info.get("e_score", 60.0)
    kelly_mult = edge_info.get("kelly_multiplier", 1.00)
    fak_buf = edge_info.get("fak_price_buffer", 0.015)

    # Pillar 2: Salvage-Adjusted Continuous Maximum-Ask Pricing Model
    shock_ofi_val = float(shock.get("shock_ofi", 1.0) if shock.get("shock_ofi") is not None else 1.0)
    shock_vol_usd = float(shock.get("shock_volume_100ms", 1_500_000.0) or 1_500_000.0)
    delta_basis_bps = float(shock.get("delta_basis_100ms", 0.0) or 0.0)
    # Directional delta basis: positive = futures basis moving WITH the target token direction
    dir_delta_basis_bps = delta_basis_bps if target_token == "UP" else -delta_basis_bps
    _raw_age_a = shock.get("age_ask_ms") if shock.get("age_ask_ms") is not None else token_features.get("age_ask_ms")
    age_ask_ms_val = float(_raw_age_a) if _raw_age_a is not None else 350.0

    # v3.3 Coinbase + Binance composite venue filter (fail-open when Coinbase unavailable)
    cb_veto, cb_reason = evaluate_coinbase_venue_veto(shock, target_token)
    if cb_veto:
        _g("COINBASE_VENUE_VETO", str(cb_reason or ""))
        logger.info(f"[COINBASE VENUE VETO] {shock.get('title')!r} {target_token}: {cb_reason}. Skipping.")
        return
    _rec_sig_bnd = float(shock.get("candle_sigma") or 0.0)
    p_max_info = compute_max_acceptable_ask(
        dist_pct=dist_pct,
        tte_sec=tte,
        asset=asset_str,
        shock_ofi=shock_ofi_val,
        shock_vol_usd=shock_vol_usd,
        delta_basis_bps=dir_delta_basis_bps,
        age_ask_ms=age_ask_ms_val,
        is_subhourly_15m=is_15m,
        candle_sigma=_rec_sig_bnd,
        is_5m=is_5m,
    )
    z_eff = p_max_info.get("z_eff", 0.0)
    p_true = p_max_info.get("p_true", 0.5)
    p_max = p_max_info.get("p_max", 0.0)

    # Dual-Regime Cushion-to-Price Entry Matrix (Purged WFO Optimal Live Windows + Dry-Run/Synthetic Parity)
    regime = None
    min_allowed_price = self.min_price_floor
    max_allowed_price = self.max_price_ceiling

    _bnd_mult = math.sqrt(12.0) if is_5m else (2.0 if is_subhourly else 1.0)
    _sig_1h_bnd = (_rec_sig_bnd * _bnd_mult) if _rec_sig_bnd > 0.0 else (0.0050 if asset_str == "BTC" else 0.0068)
    _z_cush_bnd = (abs(dist_pct) / 100.0) / max(0.00025, _sig_1h_bnd * math.sqrt(max(tte, 12.0) / 3600.0))

    _v5_dir_cfg = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {})
    _v5_rt_cfg = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("routing", {})
    _v5_live_strict = bool(_is_live_real and self._is_v5_live_strict())
    if is_sleeve3_strike:
        if 60.0 <= tte <= 10800.0 and abs(dist_pct) >= 0.60:
            regime = "REGIME_E_STRIKE_CONVERGENCE"
            min_allowed_price = 0.65
            max_allowed_price = 0.89
            p_svi_val = float(shock.get("p_svi") or p_true)
            p_true = max(p_true, p_svi_val)
            p_max = max(p_max, min(0.89, round(p_true - 0.04, 4)))
        else:
            _g("SLEEVE_3_REJECT", f"TTE={tte:.0f}s or abs(dist)={abs(dist_pct):.2f}% < 0.60%")
            logger.info(
                f"[SLEEVE_3_REJECT] {shock.get('title')!r}: TTE={tte:.0f}s or abs(dist)={abs(dist_pct):.2f}% < 0.60%. Rejecting."
            )
            return
    elif (
        is_boundary_lock_cand
        and (is_1h or is_subhourly)
        and 12.0 <= tte <= 90.0
        and max(z_eff, _z_cush_bnd, abs(float(shock.get("z_val") or shock.get("z_score") or shock.get("shock_z") or 0.0))) >= 3.0
        and abs(dist_pct) >= (0.08 if is_subhourly else 0.12)
    ):
        regime = "REGIME_D_BOUNDARY_LOCK"
        min_allowed_price = 0.62
        max_allowed_price = 0.94
        p_true = max(p_true, 0.985)
        p_max = max(p_max, 0.94)
    elif is_1h:
        if _is_live_real:
            # Holistic v5.1 Live 1h Window [150s, 2400s] (OOS 955-ledger +$1,933.83, CPCV PBO=0.133, CI95_lo > 0):
            _min_1h_tte = float(_v5_dir_cfg.get("min_tte_1h_sec", 150.0)) if _v5_live_strict else 150.0
            _max_1h_tte = float(_v5_dir_cfg.get("max_tte_1h_sec", 2400.0)) if _v5_live_strict else 2400.0
            _reg_b_max_tte = float(_v5_dir_cfg.get("regime_b_max_tte_1h_sec", 600.0)) if _v5_live_strict else 600.0
            _mkr_cap_1h = max(
                float(_v5_dir_cfg.get("max_taker_price_1h", 0.74)),
                float(_v5_dir_cfg.get("max_maker_price_1h", _v5_rt_cfg.get("maker_max_price_1h", 0.76))),
            )
            _min_px_v5 = float(_v5_dir_cfg.get("min_entry_price", 0.52)) if _v5_live_strict else 0.55
            if _min_1h_tte <= tte <= _reg_b_max_tte:
                regime = "REGIME_B_LATE_SNIPER"
                cushion = abs(dist_pct)
                _min_reg_b_cush = float(_v5_dir_cfg.get("min_cushion_pct_1h_regime_b", 0.04)) if _v5_live_strict else 0.04
                if cushion < _min_reg_b_cush or (target_token == "UP" and dist_pct < _min_reg_b_cush) or (target_token == "DOWN" and dist_pct > -_min_reg_b_cush):
                    _g("CUSHION_TOO_SMALL", f"1h Regime B cushion {dist_pct:+.4f}% < {_min_reg_b_cush:.2f}%")
                    return
                min_allowed_price = _min_px_v5
                max_allowed_price = _mkr_cap_1h if _v5_live_strict else 0.85
            elif _reg_b_max_tte < tte <= _max_1h_tte:
                regime = "REGIME_A_MID_HOUR"
                _min_reg_a_cush = float(_v5_dir_cfg.get("min_cushion_pct_1h_regime_a", 0.15)) if _v5_live_strict else 0.15
                if abs(dist_pct) < _min_reg_a_cush or (target_token == "UP" and dist_pct < _min_reg_a_cush) or (target_token == "DOWN" and dist_pct > -_min_reg_a_cush):
                    _g("CUSHION_TOO_SMALL", f"1h Regime A cushion {dist_pct:+.4f}% < {_min_reg_a_cush:.2f}%")
                    return
                opens_map = self.hourly_candle_opens.get(asset_str, {})
                open_h, open_h_1, open_h_2 = opens_map.get(cur_h_idx), opens_map.get(cur_h_idx - 1), opens_map.get(cur_h_idx - 2)
                ret_2h = ((open_h - open_h_2) / open_h_2) if (open_h and open_h_2 and open_h_2 > 0) else None
                ret_1h_p = ((open_h - open_h_1) / open_h_1) if (open_h and open_h_1 and open_h_1 > 0) else None
                ret_2h_p = ((open_h_1 - open_h_2) / open_h_2) if (open_h_1 and open_h_2 and open_h_2 > 0) else None
                p2g = bool(ret_1h_p is not None and ret_1h_p > 0.0010 and ret_2h_p is not None and ret_2h_p > 0.0010)
                p2r = bool(ret_1h_p is not None and ret_1h_p < -0.0010 and ret_2h_p is not None and ret_2h_p < -0.0010)
                is_ct = ((ret_2h is not None and ret_2h > 0.0030) or p2g) if target_token == "DOWN" else (((ret_2h is not None and ret_2h < -0.0030) or p2r) if target_token == "UP" else False)
                if is_ct and abs(dist_pct) < 0.40:
                    _g("COUNTER_TREND_VETO", f"Counter-trend abs(dist)={abs(dist_pct):.3f}% < 0.40%")
                    return
                min_allowed_price = _min_px_v5
                max_allowed_price = _mkr_cap_1h if _v5_live_strict else 0.78
            else:
                _g("1H_TTE_WINDOW", f"1h TTE={tte:.0f}s outside [{_min_1h_tte:.0f}s, {_max_1h_tte:.0f}s]")
                logger.info(
                    f"[1H HORIZON TTE REJECT] 1-hour market {shock.get('title')!r} TTE={tte:.1f}s outside WFO [{_min_1h_tte:.0f}s, {_max_1h_tte:.0f}s] window. Rejecting."
                )
                return
        elif 900.0 < tte <= 2700.0:
            regime = "REGIME_A_MID_HOUR"
            _min_reg_a_cush = 0.15
            if abs(dist_pct) < _min_reg_a_cush:
                logger.info(
                    f"[REGIME_A_REJECT] {shock.get('title')!r}: abs(dist_pct)={abs(dist_pct):.4f}% < {_min_reg_a_cush:.2f}% cushion (TTE={tte:.0f}s)."
                )
                return
            if target_token == "UP" and dist_pct < _min_reg_a_cush:
                return
            if target_token == "DOWN" and dist_pct > -_min_reg_a_cush:
                return

            opens_map = self.hourly_candle_opens.get(asset_str, {})
            open_h = opens_map.get(cur_h_idx)
            open_h_1 = opens_map.get(cur_h_idx - 1)
            open_h_2 = opens_map.get(cur_h_idx - 2)

            ret_2h = ((open_h - open_h_2) / open_h_2) if (open_h and open_h_2 and open_h_2 > 0) else None
            ret_1h_prior = ((open_h - open_h_1) / open_h_1) if (open_h and open_h_1 and open_h_1 > 0) else None
            ret_2h_prior = ((open_h_1 - open_h_2) / open_h_2) if (open_h_1 and open_h_2 and open_h_2 > 0) else None

            prior_2_green = (ret_1h_prior is not None and ret_1h_prior > 0.0010 and ret_2h_prior is not None and ret_2h_prior > 0.0010)
            prior_2_red = (ret_1h_prior is not None and ret_1h_prior < -0.0010 and ret_2h_prior is not None and ret_2h_prior < -0.0010)

            is_counter_trend = False
            if target_token == "DOWN":
                if (ret_2h is not None and ret_2h > 0.0030) or prior_2_green:
                    is_counter_trend = True
            elif target_token == "UP":
                if (ret_2h is not None and ret_2h < -0.0030) or prior_2_red:
                    is_counter_trend = True

            if is_counter_trend and abs(dist_pct) < 0.40:
                logger.info(
                    f"[TREND GUARD REJECT] {shock.get('title')!r} {target_token}: counter-trend to multi-hour trend "
                    f"(abs(dist)={abs(dist_pct):.3f}% < 0.40% reversal hurdle). Skipping."
                )
                return

            min_allowed_price = 0.55
            max_allowed_price = 0.78

        elif (30.0 <= tte <= 900.0 if z_eff >= 2.2 else 120.0 <= tte <= 900.0):
            regime = "REGIME_B_LATE_SNIPER"
            cushion = abs(dist_pct)
            _min_reg_b_cush = 0.10
            if cushion < _min_reg_b_cush:
                logger.info(
                    f"[REGIME_B_REJECT] {shock.get('title')!r}: abs(dist_pct)={cushion:.4f}% < {_min_reg_b_cush:.2f}% min threshold (TTE={tte:.0f}s)."
                )
                return
            if target_token == "UP" and dist_pct < _min_reg_b_cush:
                return
            if target_token == "DOWN" and dist_pct > -_min_reg_b_cush:
                return

            if cushion < 0.15:
                min_allowed_price = 0.55
                max_allowed_price = 0.75
            elif cushion < 0.22:
                min_allowed_price = 0.58
                max_allowed_price = 0.80
            else:
                min_allowed_price = 0.62
                max_allowed_price = 0.84
        else:
            logger.info(
                f"[1H HORIZON TTE REJECT] 1-hour market {shock.get('title')!r} TTE={tte:.1f}s outside allowed [{'30s' if z_eff >= 2.2 else '120s'}, 2700s] window. Rejecting."
            )
            return

    elif is_subhourly:
        if _v5_live_strict and is_5m and not bool(_v5_dir_cfg.get("enable_5m_directional", False)):
            _g("5M_DISABLED", "5m directional disabled in v5 governance")
            logger.info(f"[V5_5M_DISABLED_REJECT] {shock.get('title')!r}: 5m directional killed in v5.0 live governance. Rejecting.")
            return
        if _v5_live_strict and not is_5m:
            _en_15m_mkr = bool(_v5_dir_cfg.get("enable_15m_subordinate_maker", True))
            _en_15m_tkr = bool(_v5_dir_cfg.get("enable_15m_taker", False))
            if not _en_15m_mkr and not _en_15m_tkr:
                _g("15M_DISABLED", "15m directional disabled in v5 governance")
                return
            if not _en_15m_tkr:
                _eq_15m = float(getattr(self, "_last_known_collateral", 0.0) or 0.0) + sum(
                    self.get_position_market_value(p, time.time()) for p in self.active_positions.values()
                )
                _tier_slots_15m = int(
                    get_unleashed_v5_tier_profile(
                        _eq_15m if _eq_15m > 0.0 else 69.06,
                        getattr(self, "high_water_mark_equity", None),
                        previous_tier=getattr(self, "_current_equity_tier", None),
                    )["max_directional_slots"]
                )
                if (_tier_slots_15m - len(risk_positions) - len(in_flight_intents)) < 2:
                    _g("SUBORDINATE_15M_SLOT_RESERVED", "Primary slot reserved for 1h horizon")
                    logger.info(f"[SUBORDINATE_15M_SLOT_RESERVED_FOR_1H] {shock.get('title')!r}: primary slot reserved for +EV 1h horizon.")
                    return
            _m_min_15 = float(_v5_dir_cfg.get("min_tte_15m_maker_sec", _v5_dir_cfg.get("subordinate_15m_maker_min_tte_sec", 180.0)))
            _m_max_15 = float(_v5_dir_cfg.get("max_tte_15m_maker_sec", _v5_dir_cfg.get("subordinate_15m_maker_max_tte_sec", 390.0)))
            _t_min_15 = float(_v5_dir_cfg.get("min_tte_15m_taker_sec", 120.0))
            _t_max_15 = float(_v5_dir_cfg.get("max_tte_15m_taker_sec", 510.0))
            if _en_15m_tkr and _en_15m_mkr:
                _min_15m_tte = min(_m_min_15, _t_min_15)
                _max_15m_tte = max(_m_max_15, _t_max_15)
            elif _en_15m_tkr:
                _min_15m_tte = _t_min_15
                _max_15m_tte = _t_max_15
            else:
                _min_15m_tte = _m_min_15
                _max_15m_tte = _m_max_15
            _min_reg_c_cush = float(
                _v5_dir_cfg.get(
                    "min_cushion_pct_15m_taker",
                    _v5_dir_cfg.get("min_cushion_pct_15m_maker", _v5_dir_cfg.get("subordinate_15m_maker_min_cushion_pct", 0.04)),
                )
            )
        elif is_5m:
            _min_15m_tte = 60.0 if _is_live_real else 30.0
            _max_15m_tte = 180.0
            _min_reg_c_cush = 0.03 if _is_live_real else 0.08
        else:
            _min_15m_tte = 90.0 if _is_live_real else (30.0 if (not self.dry_run or z_eff >= 2.2) else 90.0)
            _max_15m_tte = 480.0 if _is_live_real else (690.0 if (not self.dry_run or z_eff >= 2.2) else 540.0)
            _min_reg_c_cush = 0.04 if _is_live_real else 0.08
        if _min_15m_tte <= tte <= _max_15m_tte:
            regime = "REGIME_C_SUBHOURLY"
            if abs(dist_pct) < _min_reg_c_cush or (target_token == "UP" and dist_pct < _min_reg_c_cush) or (target_token == "DOWN" and dist_pct > -_min_reg_c_cush):
                _g("CUSHION_TOO_SMALL", f"15m cushion {dist_pct:+.4f}% < {_min_reg_c_cush:.2f}%")
                return
            min_allowed_price = float(_v5_dir_cfg.get("min_entry_price", 0.52)) if _v5_live_strict else (0.55 if _is_live_real else 0.58)
            max_allowed_price = (
                max(
                    float(_v5_dir_cfg.get("max_taker_price_15m", 0.72)),
                    float(_v5_dir_cfg.get("max_maker_price_15m", _v5_rt_cfg.get("subordinate_15m_maker_max_price", 0.72))),
                )
                if _v5_live_strict
                else (0.85 if _is_live_real else 0.82)
            )
        else:
            _g("15M_TTE_WINDOW", f"15m TTE={tte:.0f}s outside [{_min_15m_tte:.0f}s, {_max_15m_tte:.0f}s]")
            logger.info(
                f"[SUBHOURLY TTE REJECT] Subhourly market {shock.get('title')!r} TTE={tte:.1f}s outside allowed [{_min_15m_tte:.0f}s, {_max_15m_tte:.0f}s] window. Rejecting."
            )
            return
    else:
        return

    # Time-Decayed Volatility Z-Score & Fair Binary Probability (Exact 5m/15m/1h WFO sigma_1h Parity)
    rec_sig = float(shock.get("candle_sigma") or 0.0)
    _fallback_sig_1h = 0.0050 if asset_str == "BTC" else (0.0068 if asset_str == "ETH" else 0.0085)
    _sub_sig_mult = math.sqrt(12.0) if is_5m else (2.0 if is_subhourly else 1.0)
    sigma_1h = (rec_sig * _sub_sig_mult) if rec_sig > 0.0 else _fallback_sig_1h
    sigma_rem = max(0.00025, sigma_1h * math.sqrt(max(tte, 30.0) / 3600.0))
    signed_dist_frac = (dist_pct / 100.0) if target_token == "UP" else (-dist_pct / 100.0)
    z_strike = signed_dist_frac / max(sigma_rem, 1e-6)
    _raw_ofi_in = shock.get("shock_ofi")
    shock_ofi_abs = abs(float(_raw_ofi_in)) if _raw_ofi_in is not None else 0.85
    z_effective = z_strike + (0.35 * shock_ofi_abs)
    p_fair = 0.5 * (1.0 + math.erf(z_effective / math.sqrt(2.0)))
    if _tr is not None:
        _tr.set(z_strike=z_strike)

    if _is_live_real and regime in ("REGIME_A_MID_HOUR", "REGIME_B_LATE_SNIPER", "REGIME_C_SUBHOURLY"):
        _req_wfo_z = (
            (
                float(_v5_dir_cfg.get("min_z_15m_maker", 0.90))
                if is_subhourly
                else (
                    float(_v5_dir_cfg.get("min_z_1h_regime_a", 0.85))
                    if regime == "REGIME_A_MID_HOUR"
                    else float(_v5_dir_cfg.get("min_z_1h_regime_b", 0.78))
                )
            )
            if _v5_live_strict
            else (0.85 if regime == "REGIME_A_MID_HOUR" else (0.80 if is_5m else 0.78))
        )
        if z_strike < _req_wfo_z:
            _g("WFO_Z_CUSHION", f"z_strike={z_strike:.2f} < {_req_wfo_z:.2f} WFO floor (dist={dist_pct:+.3f}%, TTE={tte:.0f}s)")
            logger.info(
                f"[WFO Z-CUSHION REJECT] {shock.get('title')!r} {target_token}: z_strike={z_strike:.3f} < {_req_wfo_z:.2f} WFO optimal floor "
                f"(z_eff={z_effective:.3f}, dist={dist_pct:+.4f}%, TTE={tte:.0f}s). Rejecting."
            )
            return
        _eta_live = 0.035
        _exp_payoff_wfo = (p_fair * 0.965) + ((1.0 - p_fair) * 0.92 * 0.38)
        _p_max_wfo = min(0.85, round(_exp_payoff_wfo / (1.0 + _eta_live + 0.015), 4))
        if is_subhourly:
            p_max = _p_max_wfo
        else:
            _p_max_unclamped = compute_max_acceptable_ask(
                dist_pct=dist_pct,
                tte_sec=min(tte, 899.0),
                asset=asset_str,
                shock_ofi=shock_ofi_val,
                shock_vol_usd=max(shock_vol_usd, 300_000.0),
                delta_basis_bps=dir_delta_basis_bps,
                age_ask_ms=age_ask_ms_val,
                target_return=_eta_live,
                is_subhourly_15m=False,
                candle_sigma=rec_sig,
            ).get("p_max", 0.0)
            p_max = max(p_max, _p_max_wfo, _p_max_unclamped)

    # Cross-Asset Lead-Lag Confirmation for ETH / SOL / XRP (z_joint = 0.70 * z_ALT + 0.30 * z_BTC)
    if asset_str in ("ETH", "SOL", "XRP"):
        btc_shock_dir = shock.get("btc_shock_direction")
        if btc_shock_dir:
            if target_token == "UP" and btc_shock_dir in ("DOWN", "SELL"):
                _g("CROSS_ASSET_REJECT", f"{asset_str} UP counter-trending BTC {btc_shock_dir}")
                logger.info(f"[CROSS-ASSET REJECT] {asset_str} {target_token} counter-trending BTC {btc_shock_dir}")
                return
            if target_token == "DOWN" and btc_shock_dir in ("UP", "BUY"):
                _g("CROSS_ASSET_REJECT", f"{asset_str} DOWN counter-trending BTC {btc_shock_dir}")
                logger.info(f"[CROSS-ASSET REJECT] {asset_str} {target_token} counter-trending BTC {btc_shock_dir}")
                return
        z_alt_val = shock.get("z_eth") if shock.get("z_eth") is not None else (shock.get("z_score") if shock.get("z_score") is not None else shock.get("z_val"))
        z_btc_val = shock.get("z_btc")
        if z_alt_val is not None and z_btc_val is not None:
            passed_cross, _, reason = self.executor.validate_cross_asset_lead_lag(
                target_asset=asset_str,
                target_direction=target_token,
                btc_direction=btc_shock_dir,
                z_alt=float(z_alt_val),
                z_btc=float(z_btc_val),
            )
            if not passed_cross:
                _g("CROSS_ASSET_REJECT", str(reason))
                logger.info(f"[CROSS-ASSET REJECT] {reason}")
                return

    # Cross-Asset Directional Conflict Guard (Correlated Crypto Overlapping-Candle Lock):
    # Block entry if an active position or pending intent exists in a correlated asset with opposing direction for an overlapping window
    cand_expiry_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
    cand_dur_s = 300.0 if str(shock.get("horizon") or "").lower() == "5m" else (900.0 if is_subhourly else 3600.0)
    cand_asset = asset_str.upper()
    dir_pending_vals = [i for i in self.pending_entry_intents.values() if isinstance(i, dict) and not i.get("live_maker_anchor_inflight")]
    all_active_or_pending = list(self._risk_bearing_positions().values()) + dir_pending_vals
    _conflict_kw = dict(
        candidate_asset=cand_asset,
        candidate_direction=target_token,
        candidate_expiry_ts=cand_expiry_ts,
        active_positions=all_active_or_pending,
        max_expiry_window_delta=(900.0 if is_subhourly else (2700.0 if not self.dry_run else 900.0)),
    )
    if getattr(self.executor.validate_cross_asset_directional_conflict, "_mock_name", None) is None:
        _conflict_kw["candidate_duration_s"] = cand_dur_s
    passed_conflict, conflict_reason = self.executor.validate_cross_asset_directional_conflict(**_conflict_kw)
    if not passed_conflict:
        _g("CROSS_ASSET_CONFLICT", str(conflict_reason))
        logger.warning(f"[CROSS-ASSET CONFLICT REJECT] {conflict_reason}. Self-hedging prohibited.")
        return

    # WFO #2 Same-Window Correlation Filter (Grid-Search Validated across 1,253 markets):
    # - 1h candles: Block 2nd correlated entry in same hourly expiry window (48.3% WR / -$36.90 -EV)
    # - 15m candles: Require >= 0.09% (1.5x) cushion for 2nd correlated entry in same 15m window (88.9% WR / +$5.06 avg)
    if not self.dry_run and not is_synthetic_test and (is_1h or is_subhourly):
        same_window_open = [
            p for p in all_active_or_pending
            if abs(float(p.get("candle_expiry_ts", 0.0) or 0.0) - cand_expiry_ts) <= 300.0
            and ((p.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M") == bool(is_subhourly))
        ]
        if same_window_open:
            if is_1h:
                _g("SAME_WINDOW_REJECT", "1h position already active in this expiry window")
                logger.info(
                    f"[SAME-WINDOW 1H REJECT] {shock.get('title')!r}: 1h position already active in this expiry window. "
                    "Blocking 2nd correlated 1h entry."
                )
                return
            elif is_subhourly and abs(dist_pct) < 0.09:
                _g("SAME_WINDOW_REJECT", f"2nd 15m entry requires |dist|>=0.09% (got {abs(dist_pct):.4f}%)")
                logger.info(
                    f"[SAME-WINDOW 15M CUSHION REJECT] {shock.get('title')!r}: 2nd 15m entry in same window requires "
                    f"abs(dist_pct) >= 0.09% (got {abs(dist_pct):.4f}%). Skipping."
                )
                return

    if not token_id:
        logger.warning(f"Could not resolve token_id for market {m_id} ({target_token})")
        return

    # Pre-warm tick size and fee caches early from shock metadata (AUDIT-13-04)
    _est_px_early = float(token_features.get("effective_price_$25") or token_features.get("vwap_$50") or 0.0)
    if token_id and token_id not in self.executor._tick_size_cache and 0.04 < _est_px_early < 0.96:
        self.executor._tick_size_cache[token_id] = 0.01
    if token_id and "neg_risk" in shock and token_id not in self.executor._neg_risk_cache:
        self.executor._neg_risk_cache[token_id] = bool(shock["neg_risk"])
    fee_meta_early = shock.get("fee_metadata", {})
    if fee_meta_early and isinstance(fee_meta_early, dict):
        cond_id_early = shock.get("condition_id") or fee_meta_early.get("condition_id")
        if cond_id_early and cond_id_early not in self.executor._fee_cache:
            fr = float(fee_meta_early.get("fee_rate_market", 0.07) or 0.07)
            fe = float(fee_meta_early.get("fee_exponent", 1.0) or 1.0)
            self.executor._fee_cache[cond_id_early] = (fr, fe)

    # Priority B: Fail-closed, two-sided entry quality gate
    raw_asks = []
    raw_bids = []
    book_snapshot = None

    ws_top_asks = token_features.get("raw_top_asks")
    ws_top_bids = token_features.get("raw_top_bids")
    raw_age_ms = token_features.get("age_book_ms")
    book_ts_val = float(token_features.get("book_timestamp", 0.0) or 0.0)
    if _is_live_real:
        if raw_age_ms is not None:
            ws_book_age_ms = float(raw_age_ms) if book_ts_val <= 0.0 else max(float(raw_age_ms), (time.time() - book_ts_val) * 1000.0)
        else:
            ws_book_age_ms = ((time.time() - book_ts_val) * 1000.0) if book_ts_val > 0.0 else 9999.0
        use_ws_book = bool(ws_top_asks and ws_top_bids and 0.0 <= ws_book_age_ms <= LIVE_WS_BOOK_MAX_AGE_MS)
    else:
        ws_book_age_ms = float(raw_age_ms) if (raw_age_ms is not None and book_ts_val > 0.0) else 9999.0
        use_ws_book = bool(ws_top_asks and ws_top_bids and 0.0 <= ws_book_age_ms <= 30000.0)

    _lt = _CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
    if _lt is not None:
        _lt.stamp("book_source_decided")
        _lt.set(
            book_source="ws" if use_ws_book else "rest",
            ws_book_age_ms=round(ws_book_age_ms, 3),
            ws_book_present=bool(ws_top_asks and ws_top_bids),
            ws_book_max_age_ms=LIVE_WS_BOOK_MAX_AGE_MS,
        )

    if use_ws_book:
        raw_asks = sorted(
            [(float(px), float(sz)) for px, sz in ws_top_asks if float(px) > 0 and float(sz) > 0],
            key=lambda x: x[0],
        )
        raw_bids = sorted(
            [(float(px), float(sz)) for px, sz in ws_top_bids if float(px) > 0 and float(sz) > 0],
            key=lambda x: x[0], reverse=True,
        )
        if raw_asks and raw_bids:
            book_snapshot = {
                "asks": [{"price": str(p), "size": str(s)} for p, s in raw_asks],
                "bids": [{"price": str(p), "size": str(s)} for p, s in raw_bids],
                "timestamp": token_features.get("book_timestamp", time.time()),
            }

    if raw_asks and raw_bids:
        # Reused sub-ms WebSocket L2 book from trigger payload (AUDIT-13-04)
        best_ask = raw_asks[0][0]
        best_bid = raw_bids[0][0]
        if best_bid >= best_ask:
            _g("BOOK_QUALITY_OR_SPREAD", f"Crossed book bid {best_bid:.3f} >= ask {best_ask:.3f}", eval_ask=best_ask, eval_bid=best_bid)
            logger.warning(f"[ENTRY_QUALITY_REJECT] Crossed/locked book for {token_id}: bid {best_bid:.4f} >= ask {best_ask:.4f}")
            return
        spread = best_ask - best_bid
        if spread > MAX_ALLOWED_SPREAD + 1e-6:
            _g("BOOK_QUALITY_OR_SPREAD", f"Spread {spread:.3f} > max {MAX_ALLOWED_SPREAD:.3f}", eval_ask=best_ask, eval_bid=best_bid)
            logger.debug(f"[SPREAD GUARD] Spread {spread:.3f} > max allowed {MAX_ALLOWED_SPREAD:.3f}. Skipping illiquid book.")
            return
    elif not self.dry_run and not is_synthetic_test:
        _t0_a_chk = float(token_features.get("best_ask") or 0.0)
        _t0_b_chk = float(token_features.get("best_bid") or 0.0)
        if (
            shock.get("clob_ws_connected") is not False
            and _t0_a_chk >= 0.985
            and _t0_b_chk >= 0.95
            and abs(dist_pct) >= 0.25
        ):
            _g(
                "PRICE_BAND_REJECT",
                f"Book already pinned deep ITM @${_t0_b_chk:.3f}/${_t0_a_chk:.3f} (> cap)",
                eval_ask=_t0_a_chk,
                eval_bid=_t0_b_chk,
            )
            return
        _book_fetch_t0 = time.monotonic()
        try:
            book_snapshot = await self.executor.get_market_book_async(token_id)
        except Exception as exc:
            _g("SLOW_REST_BOOK", f"Fresh book fetch failed: {exc}")
            logger.warning(f"[ENTRY_QUALITY_REJECT] Fresh book fetch failed for {token_id}: {exc}")
            return
        _book_fetch_rtt = time.monotonic() - _book_fetch_t0
        _lt_rest = _CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
        if _lt_rest is not None:
            _lt_rest.set(rest_book_fetch_ms=round(_book_fetch_rtt * 1000.0, 3))
            _lt_rest.stamp("rest_book_done")
        if _book_fetch_rtt > 2.5:
            _g("SLOW_REST_BOOK", f"Slow REST book fetch {_book_fetch_rtt:.2f}s > 2.5s")
            logger.warning(f"[ENTRY_QUALITY_REJECT] Slow HTTP book fetch for {token_id} (rtt {_book_fetch_rtt:.2f}s > 2.5s)")
            return

        if not book_snapshot or not isinstance(book_snapshot, dict):
            _g("BOOK_QUALITY_OR_SPREAD", "Empty or invalid REST book snapshot")
            logger.warning(f"[ENTRY_QUALITY_REJECT] Empty or invalid book snapshot for {token_id}")
            return

        # v3.9.1+: Polymarket CLOB REST /book "timestamp" is the last quote-change event time (NOT HTTP server time)!
        # Since _book_fetch_rtt <= 2.5s just verified live matching-engine reachability, resting quotes unchanged for
        # 60s-300s+ on quiet 1h/15m books are valid live resting liquidity (only reject corrupt/ancient >1800s timestamps).
        raw_book_ts = float(book_snapshot.get("timestamp", 0.0) or 0.0)
        book_ts = (raw_book_ts / 1000.0) if raw_book_ts > 1e12 else raw_book_ts
        max_book_age = float(os.environ.get("PM_MAX_BOOK_AGE_SEC", "1800.0"))
        if book_ts > 0 and (time.time() - book_ts) > max_book_age:
            _g("STALE_RECORDER_GUARD", f"Stale REST book age {time.time() - book_ts:.1f}s > {max_book_age:.0f}s")
            logger.warning(f"[ENTRY_QUALITY_REJECT] Stale book snapshot for {token_id} (age {time.time() - book_ts:.2f}s > {max_book_age:.1f}s)")
            return

        raw_asks = sorted(
            [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) 
             for x in book_snapshot.get("asks", []) 
             if float(x.get("price", 0.0)) > 0 and float(x.get("size", 0.0)) > 0],
            key=lambda x: x[0],
        )
        raw_bids = sorted(
            [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) 
             for x in book_snapshot.get("bids", []) 
             if float(x.get("price", 0.0)) > 0 and float(x.get("size", 0.0)) > 0],
            key=lambda x: x[0], reverse=True,
        )

        # Mandatory two-sided liquidity: both asks and bids must be non-empty
        if not raw_asks or not raw_bids:
            _g("BOOK_QUALITY_OR_SPREAD", f"One-sided book asks={len(raw_asks)}, bids={len(raw_bids)}")
            logger.warning(f"[ENTRY_QUALITY_REJECT] One-sided book for {token_id} (asks={len(raw_asks)}, bids={len(raw_bids)})")
            return

        best_ask = raw_asks[0][0]
        best_bid = raw_bids[0][0]

        # Crossed or locked book reject
        if best_bid >= best_ask:
            _g("BOOK_QUALITY_OR_SPREAD", f"Crossed book bid {best_bid:.3f} >= ask {best_ask:.3f}", eval_ask=best_ask, eval_bid=best_bid)
            logger.warning(f"[ENTRY_QUALITY_REJECT] Crossed/locked book for {token_id}: bid {best_bid:.4f} >= ask {best_ask:.4f}")
            return

        # Strict 3¢ spread enforcement against fresh live book
        spread = best_ask - best_bid
        if spread > MAX_ALLOWED_SPREAD + 1e-6:
            _g("BOOK_QUALITY_OR_SPREAD", f"Spread {spread:.3f} > max {MAX_ALLOWED_SPREAD:.3f}", eval_ask=best_ask, eval_bid=best_bid)
            logger.debug(f"[SPREAD GUARD] Spread {spread:.3f} > max allowed {MAX_ALLOWED_SPREAD:.3f}. Skipping illiquid book.")
            return
    else:
        # Simulation / dry-run / paper mode / synthetic test fixtures
        if hasattr(self.executor, "get_market_book_async"):
            try:
                book_snapshot = await self.executor.get_market_book_async(token_id)
            except Exception:
                book_snapshot = None
        if book_snapshot and isinstance(book_snapshot, dict):
            raw_asks = sorted(
                [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) 
                 for x in book_snapshot.get("asks", []) 
                 if float(x.get("price", 0.0)) > 0 and float(x.get("size", 0.0)) > 0],
                key=lambda x: x[0],
            )
            raw_bids = sorted(
                [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) 
                 for x in book_snapshot.get("bids", []) 
                 if float(x.get("price", 0.0)) > 0 and float(x.get("size", 0.0)) > 0],
                key=lambda x: x[0], reverse=True,
            )
        if not raw_asks:
            raw_asks = token_features.get("raw_top_asks", [])
        if not raw_bids:
            raw_bids = token_features.get("raw_top_bids", [])
        if not raw_asks:
            return
        if raw_asks and not raw_bids:
            # Provide ample synthetic bid liquidity for test fixtures omitting bids
            raw_bids = [[max(0.01, round(raw_asks[0][0] - 0.01, 4)), 1000.0]]

        best_ask = raw_asks[0][0]
        best_bid = raw_bids[0][0]
        if best_bid >= best_ask or (best_ask - best_bid) > MAX_ALLOWED_SPREAD + 1e-6:
            return

    first_ask = raw_asks[0][0]
    first_bid = raw_bids[0][0]
    # F-10c: Re-verify TIER_A_PLUS_STALE_SNIPE against the fresh live book!
    # If market makers already repriced first_ask >= +$0.02 above t0 best_ask, the quote is no longer stale.
    t0_best_ask = float(token_features.get("best_ask") or 0.0)
    _f10_check_ask = first_ask
    if _is_live_real and token_id:
        _shm_f10 = fast_tick_book_for_token(read_fast_tick(asset_str, max_age_sec=0.5), str(token_id))
        if isinstance(_shm_f10, dict) and _shm_f10.get("asks"):
            _shm_a_px = min((float(a["price"]) for a in _shm_f10["asks"] if float(a.get("size", 0)) > 0), default=0.0)
            if 0.0 < _shm_a_px < 0.995:
                _f10_check_ask = _shm_a_px
    if _tr is not None:
        _tr.set(eval_ask=first_ask, eval_bid=first_bid, t0_ask=t0_best_ask if 0.0 < t0_best_ask < 0.995 else None)
    if _is_live_real and 0.0 < t0_best_ask < 0.99 and (t0_best_ask - min(first_ask, _f10_check_ask)) >= 0.04:
        _coll_px = min(first_ask, _f10_check_ask)
        _g("ADVERSE_ASK_COLLAPSE", f"Ask collapsed ${t0_best_ask:.2f} -> ${_coll_px:.2f} (>=4c adverse)")
        logger.warning(
            f"[ADVERSE ASK COLLAPSE REJECT] {shock.get('title')!r} {target_token}: fresh ask ${_coll_px:.4f} collapsed "
            f"-${t0_best_ask - _coll_px:.4f} below t0 ask ${t0_best_ask:.4f} (>= $0.04 adverse repricing). Skipping."
        )
        return
    if edge_tier == "TIER_A_PLUS_STALE_SNIPE" and 0.0 < t0_best_ask < 0.99 and (max(first_ask, _f10_check_ask) - t0_best_ask) >= 0.0199:
        _lifted_px = max(first_ask, _f10_check_ask)
        logger.info(
            f"[STALE TIER DOWNGRADE] {shock.get('title')!r} {target_token}: fresh ask ${_lifted_px:.3f} moved "
            f"+${_lifted_px - t0_best_ask:.3f} above t0 ask ${t0_best_ask:.3f}; downgrading TIER_A_PLUS -> TIER_B_STANDARD."
        )
        edge_tier = "TIER_B_STANDARD"
        fak_buf = min(float(fak_buf), 0.010 if _is_live_real else 0.015)
        kelly_mult = min(float(kelly_mult), 1.0)
    if _v5_live_strict:
        # Purged-WFO + Live-OOT Row-15 Winner: Z-Adaptive Marketable FAK Headroom (+1c when 0.90 <= z < 1.25, +2c when z >= 1.25, capped <= $0.82)
        fak_buf = (0.020 if z_strike >= 1.25 else 0.010) if self.dynamic_sizing else min(float(fak_buf), 0.010)
    elif _is_live_real and edge_tier == "TIER_B_STANDARD":
        fak_buf = (0.020 if z_strike >= 1.25 else 0.010) if self.dynamic_sizing else min(float(fak_buf), 0.010)
    pre_check_notional = max(MIN_LOT_SIZE_USD, min(self.ticket_notional, 25.0))
    intended_shares = pre_check_notional / first_ask if first_ask > 0 else 0.0

    # Bid-Side Protection 1: Resilient Near-Touch Depth (bypassed under _v5_live_strict WFO parity; non-empty bid book is already verified)
    min_bid_mult = 2.0 if tte <= 1200.0 else 1.5
    min_required_near_touch_shares = intended_shares * min_bid_mult
    near_touch_bid_shares = sum(sz for px, sz in raw_bids if px >= (first_bid - 0.03 - 1e-6))
    if not self.dry_run and not is_synthetic_test and not _v5_live_strict and near_touch_bid_shares < min_required_near_touch_shares:
        _g("BID_DEPTH_FLOOR", f"Near-touch bid {near_touch_bid_shares:.1f}sh < {min_required_near_touch_shares:.1f}sh")
        logger.warning(
            f"[BID_NEAR_TOUCH_DEPTH_REJECT] Near-touch bid shares {near_touch_bid_shares:.1f} < "
            f"required {min_required_near_touch_shares:.1f} ({min_bid_mult:.1f}x intended shares {intended_shares:.1f})"
        )
        return

    # Bid-Side Protection 2: Full-Book Executable Liquidation Loss Gate
    total_bid_shares = sum(sz for px, sz in raw_bids)
    if not self.dry_run and not is_synthetic_test and not _v5_live_strict and total_bid_shares < intended_shares:
        _g("BID_DEPTH_FLOOR", f"Total bid {total_bid_shares:.1f}sh < {intended_shares:.1f}sh")
        logger.warning(
            f"[BID_TOTAL_DEPTH_REJECT] Total bid shares {total_bid_shares:.1f} < intended shares {intended_shares:.1f}"
        )
        return

    # Policy A: No immediate liquidation loss reject (never market dumps into bid book)
    eff_price_ceiling = (
        max(self.max_price_ceiling, max_allowed_price)
        if regime in ("REGIME_D_BOUNDARY_LOCK", "REGIME_E_STRIKE_CONVERGENCE")
        else (
            min(
                self.max_price_ceiling,
                max_allowed_price,
                max(
                    p_max,
                    max_allowed_price
                    if (
                        edge_tier == "TIER_A_PLUS_STALE_SNIPE"
                        and abs(dist_pct) >= (0.10 if is_subhourly else 0.12)
                    )
                    else 0.0,
                ),
            )
            if (not self.dry_run and p_max > 0)
            else self.max_price_ceiling
        )
    )
    _phase3a_live_eligible = self._is_phase3a_maker_rescue_live_active()
    _maker_rescue_cd_map = self.__dict__.setdefault("_maker_ceiling_rescue_cd", {})
    _maker_only_ceiling_rescue = False
    _rcfg_px = getattr(self, "risk_config", None) or RISK_CONFIG
    _dir_tkr_cap = (
        float(_v5_dir_cfg.get("max_taker_price_15m", 0.72) if is_subhourly else _v5_dir_cfg.get("max_taker_price_1h", 0.74))
        if _v5_live_strict
        else float(_rcfg_px.get("directional_taker_max_price", 0.74))
    )
    _dir_mkr_cap = (
        float(_v5_dir_cfg.get("max_maker_price_1h", 0.76))
        if _v5_live_strict
        else float(_rcfg_px.get("directional_maker_max_price", 0.76))
    )
    _p3a_15m_long_cap = (
        float(_v5_dir_cfg.get("max_maker_price_15m", 0.72))
        if _v5_live_strict
        else float(_rcfg_px.get("phase3a_15m_long_tte_max_price", 0.72))
    )
    _p3a_ceil_ref = _p3a_15m_long_cap if (is_subhourly and tte > 240.0) else 0.85
    if _v5_live_strict and regime in ("REGIME_A_MID_HOUR", "REGIME_B_LATE_SNIPER", "REGIME_C_SUBHOURLY"):
        _min_z_v5 = float(
            _v5_dir_cfg.get("min_z_15m_taker", 0.90)
            if is_subhourly
            else (
                _v5_dir_cfg.get("min_z_1h_regime_b", 0.90)
                if regime == "REGIME_B_LATE_SNIPER"
                else _v5_dir_cfg.get("min_z_1h_regime_a", 0.90)
            )
        )
        if z_strike >= _min_z_v5 and p_true > 0.53:
            p_max = max(float(p_max), float(_dir_tkr_cap))
            eff_price_ceiling = max(
                float(eff_price_ceiling),
                min(float(self.max_price_ceiling), float(max_allowed_price), float(_dir_tkr_cap)),
            )
    _maker_rescue_cap_px = round(min(float(eff_price_ceiling), float(max_allowed_price), float(p_max) if p_max > 0 else float(eff_price_ceiling)), 2)
    if is_subhourly and (tte > 240.0 or _v5_live_strict):
        _maker_rescue_cap_px = round(min(_p3a_15m_long_cap, float(_maker_rescue_cap_px)), 2)

    def _can_route_to_phase3a_ceiling_rescue(px_check: float, cap_ref: float) -> bool:
        if not _phase3a_live_eligible or self.dry_run:
            return False
        if _v5_live_strict and not bool(_v5_dir_cfg.get("enable_15m_subordinate_maker", True) if is_subhourly else _v5_dir_cfg.get("enable_1h_shielded_maker", True)):
            return False
        if regime not in ("REGIME_A_MID_HOUR", "REGIME_B_LATE_SNIPER", "REGIME_C_SUBHOURLY"):
            return False
        if tte < (85.0 if _is_live_real else 75.0) or z_strike < 0.78 or abs(dist_pct) < 0.06:
            return False
        if (time.time() - float(_maker_rescue_cd_map.get(str(m_id or ""), 0.0) or 0.0)) < 8.0:
            return False
        if px_check > round(cap_ref + 0.03, 4) + 1e-6:
            return False
        if is_subhourly and (tte > 240.0 or _v5_live_strict) and float(first_bid) > _p3a_15m_long_cap + 0.01 + 1e-6:
            return False
        cand_m_px = round(min(float(_maker_rescue_cap_px), round(float(raw_asks[0][0]) - 0.01, 2), round(float(first_bid) + 0.01, 2)), 2)
        return bool(float(min_allowed_price) - 1e-6 <= cand_m_px <= float(_maker_rescue_cap_px) + 1e-6)

    _real_unmocked_live_exec = _v5_live_strict
    _real_unmocked_live_maker = bool(_phase3a_live_eligible and _real_unmocked_live_exec)
    _15m_tkr_window_ok = bool(
        _real_unmocked_live_exec
        and is_subhourly
        and bool(_v5_dir_cfg.get("enable_15m_taker", False))
        and (float(_v5_dir_cfg.get("min_tte_15m_taker_sec", 240.0)) <= tte <= float(_v5_dir_cfg.get("max_tte_15m_taker_sec", 360.0)))
        and (z_strike >= float(_v5_dir_cfg.get("min_z_15m_taker", 0.90)))
        and raw_asks
        and (float(raw_asks[0][0]) <= _dir_tkr_cap + 1e-6)
    )
    _z_imm_tkr_cut = float(_v5_rt_cfg.get("z_immediate_taker_cut", 1.35))
    if _real_unmocked_live_exec and is_subhourly and not _15m_tkr_window_ok:
        _live_mkr_cap_ref = min(_dir_mkr_cap, _p3a_15m_long_cap, float(_v5_dir_cfg.get("max_maker_price_15m", _v5_rt_cfg.get("subordinate_15m_maker_max_price", 0.72))))
        _maker_rescue_cap_px = round(min(_live_mkr_cap_ref, float(_maker_rescue_cap_px)), 2)
        if (
            _real_unmocked_live_maker
            and bool(_v5_dir_cfg.get("enable_15m_subordinate_maker", True))
            and raw_asks
            and float(first_bid) <= _live_mkr_cap_ref + 1e-6
            and _can_route_to_phase3a_ceiling_rescue(float(raw_asks[0][0]), _live_mkr_cap_ref)
        ):
            _maker_only_ceiling_rescue = True
        else:
            _g("15M_MAKER_INELIGIBLE", f"15m outside Taker window/cap; Maker cap ${_live_mkr_cap_ref:.2f} (ask=${raw_asks[0][0] if raw_asks else 0:.2f}, bid=${first_bid:.2f})", cap_px=_live_mkr_cap_ref)
            logger.info(
                f"[V5_15M_TAKER_GATED_MAKER_VETO] {shock.get('title')!r} {target_token}: outside 15m Taker "
                f"[{float(_v5_dir_cfg.get('min_tte_15m_taker_sec', 120.0)):.0f}s, {float(_v5_dir_cfg.get('max_tte_15m_taker_sec', 510.0)):.0f}s] <= ${_dir_tkr_cap:.2f} (z={z_strike:.2f}); "
                f"ineligible for subordinate 0%-fee Maker <= ${_live_mkr_cap_ref:.2f} (ask=${raw_asks[0][0] if raw_asks else 0:.2f}, bid=${first_bid:.2f}, TTE={tte:.0f}s)."
            )
            return
    elif (
        _real_unmocked_live_exec
        and regime in ("REGIME_A_MID_HOUR", "REGIME_B_LATE_SNIPER", "REGIME_C_SUBHOURLY")
        and raw_asks
        and (
            float(raw_asks[0][0]) > _dir_tkr_cap + 1e-6
            or (not is_subhourly and (z_strike < _z_imm_tkr_cut or not bool(_v5_dir_cfg.get("enable_1h_taker", True))))
        )
    ):
        _live_mkr_cap_ref = min(_dir_mkr_cap, _p3a_15m_long_cap) if (is_subhourly and tte > 240.0) else _dir_mkr_cap
        _maker_rescue_cap_px = round(min(_live_mkr_cap_ref, float(_maker_rescue_cap_px)), 2)
        if (
            _real_unmocked_live_maker
            and (is_subhourly or bool(_v5_dir_cfg.get("enable_1h_shielded_maker", True)))
            and float(first_bid) <= _live_mkr_cap_ref + 1e-6
            and _can_route_to_phase3a_ceiling_rescue(min(float(raw_asks[0][0]), _live_mkr_cap_ref + 0.02) if float(raw_asks[0][0]) <= _live_mkr_cap_ref + 1e-6 else float(raw_asks[0][0]), _live_mkr_cap_ref)
        ):
            _maker_only_ceiling_rescue = True
        else:
            _g("TAKER_ASYMMETRY_VETO", f"Ask ${raw_asks[0][0]:.2f} / z={z_strike:.2f} outside Taker (${_dir_tkr_cap:.2f}, z>={_z_imm_tkr_cut:.2f}) & Maker ${_live_mkr_cap_ref:.2f}", cap_px=_live_mkr_cap_ref)
            logger.info(
                f"[TAKER ASYMMETRY VETO] {shock.get('title')!r} {target_token}: first_ask ${raw_asks[0][0]:.4f} / z={z_strike:.2f} outside Taker "
                f"(${_dir_tkr_cap:.2f}, z>={_z_imm_tkr_cut:.2f}) and ineligible for 0%-fee Phase 3A Maker <= ${_live_mkr_cap_ref:.2f} (bid=${first_bid:.2f}, TTE={tte:.0f}s). Skipping."
            )
            return
    elif not self.dry_run and raw_asks and raw_asks[0][0] > eff_price_ceiling:
        if _can_route_to_phase3a_ceiling_rescue(float(raw_asks[0][0]), min(float(eff_price_ceiling), _p3a_ceil_ref) if (is_subhourly and tte > 240.0) else float(eff_price_ceiling)):
            _maker_only_ceiling_rescue = True
        else:
            _g("EV_CEILING_REJECT", f"Ask ${raw_asks[0][0]:.2f} > +EV ceiling ${eff_price_ceiling:.2f}", cap_px=eff_price_ceiling)
            logger.info(
                f"[EV CEILING REJECT] {shock.get('title')!r} {target_token}: first_ask ${raw_asks[0][0]:.4f} > "
                f"+EV ceiling ${eff_price_ceiling:.4f} (p_max=${p_max:.4f}, z_strike={z_strike:.2f}). Skipping."
            )
            return

    # v3.9.1 Institutional L1 Ask Depth Floor ($20.00): eliminates thin retail ask adverse-selection (95.8% Holdout WR, PF=7.70, 0 wipeouts)
    if _is_live_real and regime in ("REGIME_B_LATE_SNIPER", "REGIME_C_SUBHOURLY") and raw_asks:
        _l1_ask_usd = float(raw_asks[0][0]) * float(raw_asks[0][1])
        if _l1_ask_usd < 20.0:
            _g("L1_ASK_DEPTH_FLOOR", f"L1 ask depth ${_l1_ask_usd:.2f} < $20.00 floor")
            logger.info(
                f"[L1 ASK DEPTH REJECT] {shock.get('title')!r} {target_token}: L1 ask depth ${_l1_ask_usd:.2f} < $20.00 institutional floor. Skipping."
            )
            return

    _depth_cap_px = round(float(eff_price_ceiling) + 0.03, 4) if _maker_only_ceiling_rescue else float(eff_price_ceiling)
    executable_depth_usd = sum(px * sz for px, sz in raw_asks if px <= _depth_cap_px + 1e-6)

    # Dynamic reference-ticket depth gate scaled to actual ticket floor
    PAPER_REFERENCE_TICKET_USD = 12.0 if self.dynamic_sizing else max(float(self.ticket_notional), 12.0)
    _ref_depth_mult = float(self.depth_hurdle)
    if not self.dry_run and (
        executable_depth_usd / PAPER_REFERENCE_TICKET_USD
        < _ref_depth_mult
    ):
        _g("DEPTH_HURDLE", f"Depth ${executable_depth_usd:.2f} < {_ref_depth_mult:.1f}x ${PAPER_REFERENCE_TICKET_USD:.0f}")
        logger.info(
            "[DEPTH PARITY REJECT] Executable depth $%.2f is below "
            "%.2fx the $%.2f reference ticket.",
            executable_depth_usd,
            _ref_depth_mult,
            PAPER_REFERENCE_TICKET_USD,
        )
        return

    # Baseline ticket notional with dynamic Quarter/Half-Kelly scaling
    ticket_target = self.ticket_notional
    exposure_cap = self.max_exposure
    live_bankroll = None
    p_model_for_sizing = None
    first_ask = raw_asks[0][0] if raw_asks else 0.50

    if regime == "REGIME_D_BOUNDARY_LOCK":
        _fr_bnd = float((shock.get("fee_metadata") or {}).get("fee_rate_market", 0.07) or 0.07)
        _net_edge_bnd = (1.0 - first_ask) - (_fr_bnd * first_ask * (1.0 - first_ask))
        if _net_edge_bnd < 0.025:
            _g("BOUNDARY_LOCK_EDGE", f"Net terminal edge {_net_edge_bnd:.4f} < $0.025")
            logger.info(
                f"[BOUNDARY_LOCK_REJECT] {shock.get('title')!r}: first_ask ${first_ask:.4f} net terminal edge {_net_edge_bnd:.4f} < $0.025. Skipping."
            )
            return

    # v3.0 Sweet-Spot Price Band: 0.52 <= ask <= 0.76 (guaranteeing >= +22.5c/share upside)
    # v3.2 Cushion-to-Price Matrix: min_allowed_price <= ask <= max_allowed_price
    assigned_sleeve = (
        "SLEEVE_3_STRIKE_CONVERGENCE" if regime == "REGIME_E_STRIKE_CONVERGENCE"
        else ("SLEEVE_4_BOUNDARY_SNIPE" if regime == "REGIME_D_BOUNDARY_LOCK"
        else ("SLEEVE_1_SUBHOURLY_15M" if is_subhourly
        else ("SLEEVE_2_MID_HOUR" if regime == "REGIME_A_MID_HOUR" else "SLEEVE_1_CORE_302")))
    )
    if not self.dry_run:
        if first_ask < min_allowed_price or (first_ask > max_allowed_price and not _maker_only_ceiling_rescue):
            if max_allowed_price < first_ask <= (max_allowed_price + 0.06):
                self._register_shadow_phase3a_maker_in(
                    shock, target_token, first_ask, first_bid, max_allowed_price, raw_asks,
                    "PRICE_BAND_REJECT", bool(is_subhourly), float(dist_pct), float(tte),
                )
            if first_ask > max_allowed_price and _can_route_to_phase3a_ceiling_rescue(float(first_ask), float(max_allowed_price)):
                _maker_only_ceiling_rescue = True
                executable_depth_usd = sum(px * sz for px, sz in raw_asks if px <= round(float(max_allowed_price) + 0.03, 4) + 1e-6)
            else:
                _g("PRICE_BAND_REJECT", f"Ask ${first_ask:.2f} outside [{min_allowed_price:.2f}, {max_allowed_price:.2f}]", cap_px=max_allowed_price)
                logger.info(
                    f"[PRICE BAND REJECT] {shock.get('title')!r} first_ask ${first_ask:.4f} outside allowed [{min_allowed_price:.2f}, {max_allowed_price:.2f}] matrix band ({regime}). Skipping."
                )
                return
    else:
        if first_ask < min_allowed_price or first_ask > max_allowed_price:
            return

    _rsw_candidate: Optional[Dict[str, Any]] = None
    if hasattr(self, "recent_shock_window") and isinstance(self.recent_shock_window, list):
        _sc_ask = float(token_features.get("vwap_$50") or token_features.get("effective_price_$50") or first_ask or 0.50)
        _sc_z = abs(float(shock.get("z_val", shock.get("z_score", shock.get("expected_prob_shift", abs(dist_pct) * 0.5)))))
        if min_allowed_price <= first_ask <= round(max_allowed_price + 0.03, 4) + 1e-6:
            _rsw_candidate = {
                "t_unix": float(shock.get("t0_unix", time.time())),
                "score": _sc_z / max(_sc_ask, 0.01),
                "market_id": str(m_id or ""),
                "trade_id": str(shock_id),
            }

    # Round 11 P1-10: Authoritative fee schedule provenance must be bound early before sizing
    fee_meta = shock.get("fee_metadata", {})
    if not self.dry_run or "fee_metadata" in shock:
        if (
            not isinstance(fee_meta, dict)
            or fee_meta.get("fee_rate_market") is None
            or not math.isfinite(float(fee_meta.get("fee_rate_market", 0.0)))
            or float(fee_meta.get("fee_rate_market", 0.0)) <= 0.0
            or not math.isfinite(float(fee_meta.get("fee_exponent", 1.0)))
            or float(fee_meta.get("fee_exponent", 1.0)) < 1.0
        ):
            _g("FEE_METADATA_REJECT", "Missing or invalid market fee metadata")
            logger.warning(
                "[FEE METADATA REJECT] Missing or invalid market fee metadata."
            )
            return
        if fee_meta.get("condition_id") and shock.get("condition_id"):
            if str(fee_meta["condition_id"]).lower() != str(shock["condition_id"]).lower():
                _g("FEE_PROVENANCE_REJECT", "Condition ID mismatch in fee metadata")
                logger.warning("[FEE PROVENANCE REJECT] Condition ID mismatch in fee metadata.")
                return
    m_fee_rate = float(fee_meta.get("fee_rate_market", 0.07)) if fee_meta.get("fee_rate_market") is not None else 0.07
    m_fee_exp = float(fee_meta.get("fee_exponent", 1.0)) if fee_meta.get("fee_exponent") is not None else 1.0
    if not math.isfinite(m_fee_rate) or m_fee_rate <= 0:
        m_fee_rate = 0.07
    if not math.isfinite(m_fee_exp) or m_fee_exp <= 0:
        m_fee_exp = 1.0

    def _calc_kelly(p_m: float, p_a: float, b: float) -> float:
        try:
            return self.compute_kelly_ticket_size(p_m, p_a, b, fee_rate=m_fee_rate, fee_exponent=m_fee_exp)
        except TypeError:
            return self.compute_kelly_ticket_size(p_m, p_a, b)

    if not self.dry_run:
        cached_collat = getattr(self, "_last_known_collateral", None)
        if cached_collat is None or not (isinstance(cached_collat, (int, float)) and math.isfinite(cached_collat) and cached_collat > 0):
            cached_collat = self.executor.get_collateral_balance(hot_path=True)
        if cached_collat is None or not (isinstance(cached_collat, (int, float)) and math.isfinite(cached_collat) and cached_collat > 0):
            persisted_bal = getattr(self, "_persisted_state", {}).get("live_bankroll")
            if persisted_bal is not None and isinstance(persisted_bal, (int, float)) and math.isfinite(persisted_bal) and persisted_bal > 0:
                cached_collat = float(persisted_bal)

        if cached_collat is not None and isinstance(cached_collat, (int, float)) and math.isfinite(cached_collat) and cached_collat > 0:
            live_bankroll = float(cached_collat)
            self._last_known_collateral = float(cached_collat)
        else:
            logger.error(
                "[SIZING HALT] Authoritative collateral balance "
                "unavailable in memory or non-positive."
            )
            return

        now_ts = time.time()
        _ps_st = getattr(self, "pre_split_inventory_state", None) or {}
        _ps_eq = min(float(_ps_st.get("up_rem", 0.0) or 0.0), float(_ps_st.get("dn_rem", 0.0) or 0.0)) if _ps_st.get("active") else 0.0
        active_market_equity = sum(self.get_position_market_value(p, now_ts) for p in self.active_positions.values()) + _ps_eq
        total_account_value = float(live_bankroll) + active_market_equity
        tier_limits = self._update_equity_tier(total_account_value)
        self.risk_controller.check_equity_drawdown(float(total_account_value))
        if self.risk_controller.is_halted():
            logger.critical(f"[CIRCUIT_BREAKER_HALT] Trading halted: {self.risk_controller.halt_reason}")
            return

        # Stale-recorder watchdog (zombie-socket guard): never open a position on frozen order-book data.
        _fresh, _feed_age, _feed_why = self.check_recorder_freshness(self._shock_asset(shock), time.time())
        if not _fresh:
            _g("STALE_RECORDER_GUARD", f"Recorder stale: {_feed_why}")
            logger.warning(
                f"[STALE_RECORDER_GUARD] {shock.get('title')!r}: {self._shock_asset(shock)} recorder feed stale "
                f"({_feed_why}). Entry refused."
            )
            return

        # Precision Upgrade 2: When cushion >= 0.15%, calibrate p_model to 0.95 (empirically validated 94.2%-94.6% win rate up to 0.92 ceiling)
        if abs(dist_pct) >= 0.15:
            self.calibrated_p_model = 0.95
            model_prob = max(0.95, float(shock.get("p_model") or 0.95))
        else:
            model_prob = shock.get("p_model", self.calibrated_p_model)
        model_meta = shock.get("probability_model") or {
            "model_version": self.calibrated_model_version,
            "calibration_id": self.calibrated_model_id,
        }
        if (
            model_prob is None
            or not model_meta.get("model_version")
            or not model_meta.get("calibration_id")
        ):
            logger.error("[SIZING HALT] Probability calibration unavailable.")
            return

        p_model_for_sizing = float(model_prob)
        if not math.isfinite(p_model_for_sizing) or not (
            0.0 < p_model_for_sizing < 1.0
        ):
            return

        # NOTE: the legacy silent override that raised max_daily_loss_usd to >= $65 was removed; the daily-loss
        # budget now comes exclusively from config/polymarket_risk_config.json (or an explicit CLI override).
        if self.dynamic_sizing:
            # Tiered dynamic equity sizing: 18% for early/mid SLEEVE_2 (TTE > 1350s), 25% for high-conviction SLEEVE_1 (TTE <= 1350s)
            now_ts = time.time()
            active_pos_map = getattr(self, "active_positions", {})
            deployed_market_value = sum(
                self.get_position_market_value(pos, now_ts)
                for pos in active_pos_map.values()
            )
            free_usdc = float(live_bankroll) if live_bankroll is not None else float(self.ticket_notional)
            total_account_value = free_usdc + deployed_market_value

            cand_exp_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
            p_win_est = max(float(p_true), float(p_fair), float(p_model_for_sizing)) if is_synthetic_test else max(float(p_true), float(p_fair))
            ticket_cap_ceiling = getattr(self, "max_ticket_cap", None) or self.max_absolute_ticket_usd or MAX_ABSOLUTE_TICKET_USD
            prev_tier_sz = getattr(self, "_current_equity_tier", None) or getattr(self, "current_equity_tier", None)
            _rcfg_corr = getattr(self, "risk_config", None) or RISK_CONFIG
            _v5_unleash_sz = bool(_v5_live_strict and GLOBAL_GOVERNANCE_MANAGER.snapshot.get("sizing_tiers", {}).get("unleash_full_throttle", True))
            if _v5_unleash_sz:
                tier_limits = get_unleashed_v5_tier_profile(total_account_value, getattr(self, "high_water_mark_equity", None), previous_tier=prev_tier_sz)
                self._current_equity_tier = tier_limits["tier"]
                self.current_equity_tier = tier_limits["tier"]
                self.dynamic_bankroll_pct = tier_limits["alpha_notional"]
                if not getattr(self, "allow_cli_exposure", False):
                    self.max_exposure = tier_limits["max_exposure"]
                risk_pct = float(tier_limits["alpha_notional"])
                pct_ticket_cap = round(risk_pct * total_account_value, 2)
                if assigned_sleeve == "SLEEVE_4_BOUNDARY_SNIPE" and total_account_value < 180.0:
                    pct_ticket_cap = min(pct_ticket_cap, round(0.25 * total_account_value, 2), 35.0)
                _sizing_entry_px = _maker_rescue_cap_px if _maker_only_ceiling_rescue else first_ask
                dynamic_ticket_cap = compute_stop_risk_fractional_kelly_ticket(
                    live_equity=total_account_value,
                    p_win=p_win_est,
                    entry_px=_sizing_entry_px,
                    is_maker=bool(_maker_only_ceiling_rescue),
                    is_subhourly_15m=bool(is_subhourly and not is_5m),
                    fee_rate=float(fee_meta.get("fee_rate_market") or 0.07),
                    asset=asset_str,
                    kelly_multiplier=kelly_mult,
                    active_positions=self._risk_bearing_positions(),
                    cand_expiry_ts=cand_exp_ts,
                    cand_direction=target_token,
                    min_lot_usd=8.0,
                    max_ticket_cap=min(float(ticket_cap_ceiling), pct_ticket_cap),
                )
                if dynamic_ticket_cap > 0.0 and not is_synthetic_test:
                    dynamic_ticket_cap = apply_convex_payoff_sizing_cap(
                        dynamic_ticket_cap,
                        live_equity=total_account_value,
                        entry_px=_sizing_entry_px,
                        sleeve=assigned_sleeve,
                        max_salvage_risk_pct=float(tier_limits["alpha_stop_risk"]),
                        salvage_floor_px=float(tier_limits["salvage_stop_floor_px"]),
                    )
            else:
                tier_limits = get_equity_tier_limits(total_account_value, getattr(self, "high_water_mark_equity", None), previous_tier=prev_tier_sz)
                self._current_equity_tier = tier_limits["tier"]
                self.current_equity_tier = tier_limits["tier"]
                small_bankroll_corr_cap = float(
                    _rcfg_corr.get("correlated_crypto_single_slot_threshold", _rcfg_corr.get("scale_up_equity_threshold", 110.0))
                )
                if (
                    not self.dry_run
                    and not is_synthetic_test
                    and total_account_value < small_bankroll_corr_cap
                    and os.environ.get("PM_ALLOW_SMALL_BANKROLL_CORRELATED_CRYPTO") != "1"
                    and not getattr(self, "allow_cli_concurrency", False)
                ):
                    active_dir_crypto = [
                        p for p in (
                            list(self._risk_bearing_positions().values())
                            + [i for i in self.pending_entry_intents.values() if isinstance(i, dict) and not i.get("live_maker_anchor_inflight")]
                        )
                        if str(p.get("asset") or "").upper() in ("BTC", "ETH", "SOL", "XRP")
                        and "BOX" not in str(p.get("sleeve") or "").upper()
                        and "WEATHER" not in str(p.get("sleeve") or "").upper()
                    ]
                    _orth_min_eq = float(_rcfg_corr.get("min_equity_floor", 66.67)) if bool(_rcfg_corr.get("enable_orthogonal_boundary_slot", True)) else 110.0
                    _orth_boundary_slot2_ok = bool(
                        assigned_sleeve == "SLEEVE_4_BOUNDARY_SNIPE"
                        and 12.0 <= tte <= 45.0
                        and (z_eff >= 3.0 or total_account_value >= 110.0)
                        and total_account_value >= _orth_min_eq
                        and len(active_dir_crypto) == 1
                        and all(
                            str(p.get("market_id") or "") != str(m_id or "")
                            and (
                                str(p.get("asset") or "").upper() != asset_str
                                or abs(float(p.get("candle_expiry_ts") or 0.0) - cand_exp_ts) > 60.0
                            )
                            for p in active_dir_crypto
                        )
                    )
                    if len(active_dir_crypto) >= 1 and not _orth_boundary_slot2_ok:
                        logger.info(
                            f"[CORRELATED CRYPTO CONCURRENCY GUARD] {shock.get('title')!r}: "
                            f"equity=${total_account_value:.2f} < ${small_bankroll_corr_cap:.2f} already holds 1 directional crypto position; "
                            "reserving slot #2 strictly for uncorrelated sleeves (Box/Weather/Orthogonal <=45s Boundary Snipe)."
                        )
                        return
                risk_pct = tier_limits["dynamic_bankroll_pct"]
                pct_ticket_cap = round(risk_pct * total_account_value, 2)
                if assigned_sleeve == "SLEEVE_4_BOUNDARY_SNIPE" and total_account_value < 180.0:
                    pct_ticket_cap = min(pct_ticket_cap, round(0.16 * total_account_value, 2), 22.0)
                seed_ticket_floor = float(RISK_CONFIG.get("seed_survival_ticket_usd", 12.0))
                if total_account_value < float(RISK_CONFIG.get("seed_survival_equity_threshold", 88.0)):
                    if RISK_CONFIG.get("seed_smooth_compounding", True) and total_account_value >= float(RISK_CONFIG.get("min_equity_floor", 66.67)):
                        pct_ticket_cap = max(seed_ticket_floor, pct_ticket_cap)
                    else:
                        pct_ticket_cap = min(pct_ticket_cap, seed_ticket_floor)
                _sizing_entry_px = _maker_rescue_cap_px if _maker_only_ceiling_rescue else first_ask
                dynamic_ticket_cap = compute_correlated_truncated_kelly_size(
                    live_equity=total_account_value,
                    p_win=p_win_est,
                    entry_px=_sizing_entry_px,
                    active_positions=self._risk_bearing_positions(),
                    cand_expiry_ts=cand_exp_ts,
                    cand_direction=target_token,
                    kelly_multiplier=kelly_mult,
                    min_lot_usd=8.0,
                    max_ticket_cap=min(float(ticket_cap_ceiling), pct_ticket_cap),
                    default_sizing_pct=risk_pct,
                )
                if dynamic_ticket_cap > 0.0 and not is_synthetic_test:
                    dynamic_ticket_cap = apply_convex_payoff_sizing_cap(
                        dynamic_ticket_cap,
                        live_equity=total_account_value,
                        entry_px=_sizing_entry_px,
                        sleeve=assigned_sleeve,
                    )
                    if _sizing_entry_px > 0.80 and "BOX" not in assigned_sleeve.upper():
                        dynamic_ticket_cap = min(
                            dynamic_ticket_cap,
                            max(8.0, round(float(_rcfg_corr.get("high_price_ticket_cap_pct", 0.16)) * total_account_value, 2)),
                        )
                    if asset_str == "SOL" or (asset_str == "ETH" and _v5_live_strict):
                        _can_mult = float(_v5_dir_cfg.get("sol_canary_size_multiplier" if asset_str == "SOL" else "eth_canary_size_multiplier", 0.85))
                        dynamic_ticket_cap = max(8.0, round(dynamic_ticket_cap * _can_mult, 2)) if dynamic_ticket_cap >= 8.0 else dynamic_ticket_cap
            if dynamic_ticket_cap <= 0.0:
                logger.info(
                    f"[CORRELATION VETO] {shock.get('title')!r} {target_token}: opposite-direction position already open "
                    f"in the same expiry window. Skipping."
                )
                return

            passed_elastic, elastic_sz = PolymarketLiveExecutor.calculate_elastic_ticket_size(
                executable_depth_usd,
                depth_hurdle_ratio=self.depth_hurdle,
                min_ticket_usd=8.0,
                max_ticket_usd=dynamic_ticket_cap,
            )
            if not passed_elastic:
                logger.info(
                    "[ELASTIC DEPTH REJECT] Executable depth $%.2f cannot support min $8.00 ticket at %.2fx hurdle.",
                    executable_depth_usd, self.depth_hurdle,
                )
                return
            _inflight_mkr_usd = sum(
                float(i.get("notional_usd", 0.0) or 0.0)
                for i in self.pending_entry_intents.values()
                if isinstance(i, dict) and i.get("live_maker_anchor_inflight")
            )
            if _inflight_mkr_usd > 0.0 and not self.dry_run:
                self._preempt_resting_maker_anchors(
                    reason=f"DIR_SHOCK:{asset_str}_{shock.get('horizon') or '1h'}"
                )
                _unenc_usdc = max(0.0, free_usdc - _inflight_mkr_usd)
                if _unenc_usdc < 8.0 and free_usdc >= 8.0:
                    for _ in range(15):
                        await asyncio.sleep(0.01)
                        _inflight_mkr_usd = sum(
                            float(i.get("notional_usd", 0.0) or 0.0)
                            for i in self.pending_entry_intents.values()
                            if isinstance(i, dict) and i.get("live_maker_anchor_inflight")
                        )
                        if _inflight_mkr_usd <= 0.0:
                            break
                    _unenc_usdc = max(0.0, free_usdc - _inflight_mkr_usd)
                ticket_target = min(elastic_sz, _unenc_usdc)
            else:
                ticket_target = min(elastic_sz, free_usdc)
            # Hard portfolio exposure cap (config max_exposure) is never lifted by dynamic sizing.
            exposure_cap = self.max_exposure
        else:
            _sizing_entry_px = _maker_rescue_cap_px if _maker_only_ceiling_rescue else first_ask
            kelly_ticket = _calc_kelly(
                p_model_for_sizing, _sizing_entry_px, live_bankroll
            )
            min_lot_gate = min(MIN_LOT_SIZE_USD, float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else MIN_LOT_SIZE_USD
            if kelly_ticket < min_lot_gate:
                logger.info(
                    "[SIZING REJECTED] Kelly ticket %.2f is below minimum lot %.2f",
                    kelly_ticket, min_lot_gate,
                )
                return
            ticket_target = kelly_ticket
            exposure_cap = self.max_exposure
            if getattr(self, "unconstrained_kelly", False) and live_bankroll:
                exposure_cap = min(exposure_cap, round(float(live_bankroll) * (self.max_concurrent_positions * self.max_notional_cap_pct), 2))

    # Dynamic Depth-Proportional Sizing
    effective_notional = ticket_target

    # Headroom capping: Do not exceed remaining portfolio exposure allowance
    # Round 10 P0-01: Capital-scaling modes may only shrink remaining headroom, never exceed exposure cap
    remaining_exposure = max(0.0, round(exposure_cap - current_exposure, 2))
    effective_notional = min(effective_notional, remaining_exposure)

    # Fail-closed guard: Must meet minimum lot size ($8.00 when elastic dynamic_sizing is active, else MIN_LOT_SIZE_USD) and depth hurdle
    _live_min_lot = 8.0 if self.dynamic_sizing else MIN_LOT_SIZE_USD
    min_lot_gate = min(MIN_LOT_SIZE_USD, float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else _live_min_lot
    if effective_notional < min_lot_gate:
        return
    if (executable_depth_usd / effective_notional) < (self.depth_hurdle - 1e-4):
        return
    if _v5_live_strict and raw_asks and not _maker_only_ceiling_rescue:
        _min_l1_u = float(_v5_dir_cfg.get("min_l1_ask_depth_usd", 20.0) or 20.0)
        _l1_px0 = float(raw_asks[0][0])
        _l1_u = sum(float(px) * float(sz) for px, sz in raw_asks if float(px) <= _l1_px0 + 0.01 + 1e-6)
        if _l1_u < _min_l1_u - 1e-6:
            return

    # Trap 1.1: Proportional bid-depth down-scaler for up-sized tickets (bypassed under _v5_live_strict WFO parity)
    if not self.dry_run and not is_synthetic_test and not _v5_live_strict and first_ask > 0:
        max_near_bid_shares = near_touch_bid_shares / max(min_bid_mult, 1.0)
        max_bid_supported_shares = min(max_near_bid_shares, total_bid_shares)
        max_bid_supported_usd = math.floor(max_bid_supported_shares * first_ask * 100.0) / 100.0
        if _maker_only_ceiling_rescue:
            max_bid_supported_usd = math.floor(max_bid_supported_shares * _maker_rescue_cap_px * 100.0) / 100.0
        if effective_notional > max_bid_supported_usd:
            min_lot_chk = min(MIN_LOT_SIZE_USD, float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else _live_min_lot
            if max_bid_supported_usd < min_lot_chk:
                logger.warning(
                    f"[BID_DEPTH_REJECT] Bid depth supports only ${max_bid_supported_usd:.2f} < min lot ${min_lot_chk:.2f}"
                )
                return
            logger.info(
                f"[BID_DEPTH_DOWNSCALE] Scaling ticket ${effective_notional:.2f} -> ${max_bid_supported_usd:.2f} "
                f"to match near-touch bid liquidity ({near_touch_bid_shares:.1f} shrs)."
            )
            effective_notional = max_bid_supported_usd

    # Idea #1 Pre-VWAP Elastic [PREWARM LADDER] Rung Down-Snapping:
    # If L1/limit depth cannot fill the full elastic ticket without spilling into an expensive L2 jump,
    # step down to the highest pre-warmed rung supported within prelim_limit_px before computing raw_vwap.
    _prelim_walk_cap: Optional[float] = None
    if not self.dry_run and self.dynamic_sizing and raw_asks and not _maker_only_ceiling_rescue:
        _live_dir_cap_chk = (
            float(_dir_tkr_cap)
            if (_real_unmocked_live_exec and regime in ("REGIME_A_MID_HOUR", "REGIME_B_LATE_SNIPER", "REGIME_C_SUBHOURLY"))
            else 1.0
        )
        prelim_limit_px = round(min(float(first_ask) + fak_buf, self.max_price_ceiling, max_allowed_price, _live_dir_cap_chk), 2)
        prelim_limit_depth = sum(float(px) * float(sz) for px, sz in raw_asks if float(px) <= prelim_limit_px + 1e-6)
        if prelim_limit_depth < float(effective_notional) - 1e-6:
            snapped_pre = None
            for cand_rung in (160.00, 120.00, 90.00, 65.00, 48.00, 36.00, 28.00, 24.00, 20.00, 16.50, 14.00, 12.00, 10.00, 8.00):
                if cand_rung < float(effective_notional) and prelim_limit_depth >= cand_rung - 1e-6:
                    snapped_pre = cand_rung
                    break
            if snapped_pre is None and prelim_limit_depth >= 8.00 - 1e-6:
                snapped_pre = float(math.floor(prelim_limit_depth))
            if snapped_pre is not None and snapped_pre < float(effective_notional):
                logger.info(
                    f"[IDEA-1 ELASTIC DOWNSNAP] Depth within ${prelim_limit_px:.2f} is "
                    f"${prelim_limit_depth:.2f} < ${effective_notional:.2f}; down-snapping to pre-warmed rung ${snapped_pre:.2f}."
                )
                effective_notional = snapped_pre
        if float(first_ask) <= prelim_limit_px + 1e-6 and prelim_limit_depth >= float(effective_notional) - 1e-6:
            _prelim_walk_cap = prelim_limit_px

    # Compute raw orderbook crossing VWAP before fees
    spent = 0.0
    shares = 0.0
    for px, sz in raw_asks:
        if _prelim_walk_cap is not None and float(px) > _prelim_walk_cap + 1e-6:
            break
        fill_dollars = min(effective_notional - spent, px * sz)
        spent += fill_dollars
        shares += fill_dollars / px
        if spent >= effective_notional - 1e-6:
            break
    raw_vwap = round(spent / shares, 4) if shares > 0 else (raw_asks[0][0] if raw_asks else None)
    if _maker_only_ceiling_rescue:
        raw_vwap = _maker_rescue_cap_px

    # Check ceiling and floor against raw execution ask / VWAP & p_max
    if not self.dry_run:
        _vwap_live_tkr_exceed = bool(
            _real_unmocked_live_exec
            and not _maker_only_ceiling_rescue
            and regime in ("REGIME_A_MID_HOUR", "REGIME_B_LATE_SNIPER", "REGIME_C_SUBHOURLY")
            and raw_vwap
            and float(raw_vwap) > _dir_tkr_cap + 1e-6
        )
        if _vwap_live_tkr_exceed:
            _live_mkr_cap_v = min(_dir_mkr_cap, _p3a_15m_long_cap) if (is_subhourly and tte > 240.0) else _dir_mkr_cap
            _maker_rescue_cap_px = round(min(_live_mkr_cap_v, float(_maker_rescue_cap_px)), 2)
            if _real_unmocked_live_maker and float(first_bid) <= _live_mkr_cap_v + 1e-6 and _can_route_to_phase3a_ceiling_rescue(float(raw_vwap), _live_mkr_cap_v):
                _maker_only_ceiling_rescue = True
                raw_vwap = _maker_rescue_cap_px
            else:
                _g("TAKER_ASYMMETRY_VETO", f"VWAP ${raw_vwap:.2f} > ${_dir_tkr_cap:.2f} Taker cap", cap_px=_dir_tkr_cap)
                return
        if not raw_vwap or raw_vwap < min_allowed_price or raw_vwap > max_allowed_price:
            if raw_vwap and max_allowed_price < raw_vwap <= (max_allowed_price + 0.06):
                self._register_shadow_phase3a_maker_in(
                    shock, target_token, first_ask, first_bid, max_allowed_price, raw_asks,
                    "VWAP_BAND_REJECT", bool(is_subhourly), float(dist_pct), float(tte),
                )
            if raw_vwap and raw_vwap > max_allowed_price and _can_route_to_phase3a_ceiling_rescue(float(raw_vwap), float(_maker_rescue_cap_px)):
                _maker_only_ceiling_rescue = True
                raw_vwap = _maker_rescue_cap_px
            else:
                _g("VWAP_BAND_REJECT", f"VWAP ${raw_vwap or 0:.2f} outside [{min_allowed_price:.2f}, {max_allowed_price:.2f}]", cap_px=max_allowed_price)
                logger.info(
                    f"[VWAP BAND REJECT] {shock.get('title')!r} raw_vwap ${raw_vwap} outside allowed [{min_allowed_price:.2f}, {max_allowed_price:.2f}] matrix band ({regime}). Skipping."
                )
                return
        if p_max <= 0.0 or raw_vwap > p_max:
            if p_max > 0.0 and raw_vwap and raw_vwap > p_max and _can_route_to_phase3a_ceiling_rescue(float(raw_vwap), float(_maker_rescue_cap_px)):
                _maker_only_ceiling_rescue = True
                raw_vwap = _maker_rescue_cap_px
            else:
                _g("P_MAX_REJECT", f"VWAP ${raw_vwap:.2f} > p_max ${p_max:.2f}", cap_px=p_max)
                logger.info(
                    f"[P_MAX REJECT] {shock.get('title')!r} raw_vwap ${raw_vwap:.4f} > p_max ${p_max:.4f} (p_true={p_true:.4f}, z_eff={z_eff:.2f}). Skipping."
                )
                return
        if age_ask_ms_val > 10000.0 and (p_true - first_ask) > 0.28:
            _g("ANCHOR_DISAGREEMENT", f"Ask ${first_ask:.2f} diverges from p_true {p_true:.2f} (>10s stale)")
            logger.warning(
                f"[ANCHOR DISAGREEMENT VETO] {shock.get('title')!r} {target_token}: resting ask ${first_ask:.4f} "
                f"(age={age_ask_ms_val:.0f}ms > 10s) diverges from model p_true={p_true:.4f} by {p_true - first_ask:+.4f} (> 0.28). "
                "Possible strike anchor divergence. Skipping."
            )
            return
    else:
        if not raw_vwap or raw_vwap < min_allowed_price or raw_vwap > max_allowed_price:
            return

    # Recalculate Kelly at the executable VWAP. The first ask is not
    # the acquisition cost when the ticket sweeps multiple book levels.
    if not self.dry_run:
        if live_bankroll is None or p_model_for_sizing is None:
            return

        min_required_cushion = (
            float(_v5_dir_cfg.get("min_cushion_pct_15m_taker", 0.04))
            if (_v5_live_strict and is_subhourly)
            else (0.07 if is_subhourly else 0.08)
        )
        if getattr(self, "dynamic_sizing", False) and abs(dist_pct) >= min_required_cushion:
            # Precision Upgrade 2: Once cushion >= min_required_cushion is satisfied, remove legacy Kelly downsizing
            # and reject so [VWAP KELLY REJECT] never blocks valid 0.84-0.88 breakouts and never
            # shrinks a $25-$32 elastic ticket down to $15.31.
            _defer_info(
                f"[DYNAMIC SIZING CONFIRMED] Cushion {abs(dist_pct):.4f}% >= {min_required_cushion:.2f}%; "
                f"maintaining full elastic depth ticket ${effective_notional:.2f} (bypassing legacy Kelly downsizing)."
            )
        else:
            _p_kelly_vwap = (
                (
                    max(float(p_model_for_sizing), float(p_true), float(p_fair))
                    if is_synthetic_test
                    else float(p_true)
                )
                if getattr(self, "dynamic_sizing", False)
                else float(p_model_for_sizing)
            )
            vwap_kelly_ticket = _calc_kelly(
                _p_kelly_vwap,
                raw_vwap,
                live_bankroll,
            )
            _vwap_min_lot = 8.0 if getattr(self, "dynamic_sizing", False) else MIN_LOT_SIZE_USD
            if vwap_kelly_ticket < _vwap_min_lot:
                _g("VWAP_KELLY_REJECT", f"Kelly ${vwap_kelly_ticket:.2f} < min ${_vwap_min_lot:.0f} @ VWAP ${raw_vwap:.2f}")
                logger.info(
                    "[VWAP KELLY REJECT] Executable VWAP %.4f "
                    "does not support minimum Kelly ticket (%.2f < %.2f on thin cushion %.4f%%).",
                    raw_vwap,
                    vwap_kelly_ticket,
                    _vwap_min_lot,
                    abs(dist_pct),
                )
                return

            effective_notional = min(
                effective_notional,
                vwap_kelly_ticket,
            )
            if effective_notional < _vwap_min_lot:
                return

            # Recheck the liquidity constraint after Kelly downsizing.
            if (
                executable_depth_usd / effective_notional
                < self.depth_hurdle - 1e-4
            ):
                return

    eff_px = (
        raw_vwap
        if _maker_only_ceiling_rescue
        else (
            token_features.get(f"effective_price_${int(effective_notional)}")
            or token_features.get("effective_price_$25")
            or token_features.get("effective_price_$20")
            or token_features.get("effective_price_$5")
            or token_features.get("effective_price_$50")
            or raw_vwap
        )
    )

    m_id = str(shock.get("market_id"))

    # Sequential Re-entry Guard: Only enter if no position is currently active or pending in this market
    _inflight_mkts = self.__dict__.setdefault("_inflight_eval_markets", set())
    if (
        m_id in _inflight_mkts
        or any(str(p.get("market_id")) == m_id and not position_is_settlement_receivable(p) for p in self.active_positions.values())
        or any(str(i.get("market_id")) == m_id for i in self.pending_entry_intents.values())
    ):
        logger.debug(f"[MARKET ALREADY ACTIVE] Position already active/pending for market {m_id}. Refusing concurrent re-entry.")
        return

    # Cross-Asset Directional Conflict Guard (Correlated Crypto Overlapping-Candle Lock):
    # Enforce that no open/pending position in a correlated asset opposes this candidate in an overlapping candle window
    cand_expiry_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
    cand_dur_s = 300.0 if str(shock.get("horizon") or "").lower() == "5m" else (900.0 if is_subhourly else 3600.0)
    cand_asset = asset_str.upper()
    dir_pending_vals = [i for i in self.pending_entry_intents.values() if isinstance(i, dict) and not i.get("live_maker_anchor_inflight")]
    all_active_or_pending = list(self._risk_bearing_positions().values()) + dir_pending_vals
    _conflict_kw2 = dict(
        candidate_asset=cand_asset,
        candidate_direction=target_token,
        candidate_expiry_ts=cand_expiry_ts,
        active_positions=all_active_or_pending,
        max_expiry_window_delta=(900.0 if is_subhourly else (2700.0 if not self.dry_run else 900.0)),
    )
    if getattr(self.executor.validate_cross_asset_directional_conflict, "_mock_name", None) is None:
        _conflict_kw2["candidate_duration_s"] = cand_dur_s
    passed_conflict, conflict_reason = self.executor.validate_cross_asset_directional_conflict(**_conflict_kw2)
    if not passed_conflict:
        logger.warning(f"[CROSS-ASSET CONFLICT REJECT] {conflict_reason}. Self-hedging prohibited.")
        return

    # WFO #2 Same-Window Correlation Filter (Grid-Search Validated across 1,253 markets):
    # - 1h candles: Block 2nd correlated entry in same hourly expiry window (48.3% WR / -$36.90 -EV)
    # - 15m candles: Require >= 0.09% (1.5x) cushion for 2nd correlated entry in same 15m window (88.9% WR / +$5.06 avg)
    if not self.dry_run and not is_synthetic_test and (is_1h or is_subhourly):
        same_window_open = [
            p for p in all_active_or_pending
            if abs(float(p.get("candle_expiry_ts", 0.0) or 0.0) - cand_expiry_ts) <= 300.0
            and ((p.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M") == bool(is_subhourly))
        ]
        if same_window_open:
            if is_1h:
                logger.info(
                    f"[SAME-WINDOW 1H REJECT] {shock.get('title')!r}: 1h position already active in this expiry window. "
                    "Blocking 2nd correlated 1h entry."
                )
                return
            elif is_subhourly and abs(dist_pct) < 0.09:
                logger.info(
                    f"[SAME-WINDOW 15M CUSHION REJECT] {shock.get('title')!r}: 2nd 15m entry in same window requires "
                    f"abs(dist_pct) >= 0.09% (got {abs(dist_pct):.4f}%). Skipping."
                )
                return

    # Hourly Cap Guard: Log Candidate #3, #4, etc. for sample analysis
    trades_for_direction = self.trades_per_market_direction.get((m_id, target_token), 0)
    is_win_reentry_dir = False
    is_loss_locked_dir = False
    if trades_for_direction >= 1:
        closed_for_mkt_dir = [
            p for p in self.closed_positions
            if p.get("market_id") == m_id and p.get("target_token") == target_token
        ]
        if closed_for_mkt_dir:
            last_closed_dir = closed_for_mkt_dir[-1]
            if last_closed_dir.get("won") is True and float(last_closed_dir.get("net_pnl_usd", 0.0) or 0.0) > 0.0:
                is_win_reentry_dir = (trades_for_direction == 1 and self.max_trades_per_market >= 2)
            else:
                is_loss_locked_dir = True

    max_dir_cap = 0 if is_loss_locked_dir else (2 if is_win_reentry_dir else self.max_trades_per_market)
    if self.trades_this_hour >= self.max_trades_per_hour or trades_for_direction >= max_dir_cap:
        candidate_record = {
            "logged_at_utc": datetime.now(timezone.utc).isoformat(),
            "candidate_index_in_hour": self.trades_this_hour + 1,
            "candidate_index_in_market": trades_for_direction + 1,
            "market_id": m_id,
            "title": shock.get("title"),
            "target_token": target_token,
            "token_id": token_id,
            "dist_pct": dist_pct,
            "tte_seconds": tte,
            "effective_price": eff_px,
            "executable_depth_usd": executable_depth_usd,
            "hypothetical_notional": effective_notional,
            "target_exit_price": round(self._calculate_target_exit(eff_px, tte), 3),
            "reason_blocked": "HOURLY_PORTFOLIO_CAP_REACHED" if self.trades_this_hour >= self.max_trades_per_hour else "MARKET_CANDLE_CAP_REACHED",
        }
        try:
            with open(COUNTERFACTUAL_CANDIDATES_FILE, "a") as f:
                f.write(json.dumps(candidate_record) + "\n")
        except Exception as e:
            logger.warning(f"Failed to record counterfactual candidate: {e}")
        if _hctx is not None:
            _hctx[1]()
        logger.info(
            f"[COUNTERFACTUAL CANDIDATE #{self.trades_this_hour + 1}] {shock.get('title')} {target_token} @ ${eff_px:.3f} "
            f"(Depth: ${executable_depth_usd:.1f}, Dist: {dist_pct:+.2f}%) passed all gates but blocked by hourly cap "
            f"(portfolio hour: {self.trades_this_hour}/{self.max_trades_per_hour}, market direction: {trades_for_direction}/{max_dir_cap}). Recorded for sample analysis."
        )
        _g("HOURLY_OR_MARKET_CAP", f"Cap reached (hr {self.trades_this_hour}/{self.max_trades_per_hour}, mkt {trades_for_direction}/{max_dir_cap})")
        return

    # Concurrent Positions & Portfolio Exposure Ceiling Guard
    _non_mkr_intents = [k for k, v in self.pending_entry_intents.items() if k not in risk_positions and not (isinstance(v, dict) and v.get("live_maker_anchor_inflight"))]
    _final_conc_lim = max(self.max_concurrent_positions, 2) if (_cg_orth_bnd and assigned_sleeve == "SLEEVE_4_BOUNDARY_SNIPE") else self.max_concurrent_positions
    if (
        not math.isfinite(float(effective_notional))
        or (current_exposure + float(effective_notional)) > exposure_cap + 1e-6
        or len(risk_positions) + len(_non_mkr_intents) >= _final_conc_lim
        or (not self.dry_run and not is_synthetic_test and not getattr(self, "allow_cli_concurrency", False) and (len(self._active_box_ids()) + len(risk_positions) + len(_non_mkr_intents)) >= _cg_tot_slots)
    ):
        candidate_record = {
            "logged_at_utc": datetime.now(timezone.utc).isoformat(),
            "candidate_index_in_hour": self.trades_this_hour + 1,
            "market_id": m_id,
            "title": shock.get("title"),
            "target_token": target_token,
            "token_id": token_id,
            "dist_pct": dist_pct,
            "tte_seconds": tte,
            "effective_price": eff_px,
            "executable_depth_usd": executable_depth_usd,
            "hypothetical_notional": effective_notional,
            "target_exit_price": round(self._calculate_target_exit(eff_px, tte), 3),
            "reason_blocked": "EXPOSURE_OR_CONCURRENT_CEILING_REACHED",
        }
        try:
            with open(COUNTERFACTUAL_CANDIDATES_FILE, "a") as f:
                f.write(json.dumps(candidate_record) + "\n")
        except Exception as e:
            logger.warning(f"Failed to record counterfactual candidate: {e}")
        if _hctx is not None:
            _hctx[1]()
        logger.warning(
            f"[CEILING BLOCKED] Active={len(self.active_positions)}/{self.max_concurrent_positions}, "
            f"Exposure=${current_exposure:.2f}/${exposure_cap:.2f}. Recorded counterfactual candidate for sample analysis."
        )
        _g("EXPOSURE_CEILING", f"Exposure ${current_exposure:.2f}+${effective_notional:.2f} > ${exposure_cap:.2f}")
        return

    trade_id = f"LIVE_{shock.get('market_id')}_{int(time.time())}_{target_token}"
    if trade_id in self.pending_entry_intents or trade_id in self.active_positions:
        _sfx_ms = int((time.time() % 1.0) * 1000)
        trade_id = f"{trade_id}_{_sfx_ms:03d}"
        _dup_i = 2
        while trade_id in self.pending_entry_intents or trade_id in self.active_positions:
            trade_id = f"LIVE_{shock.get('market_id')}_{int(time.time())}_{target_token}_{_sfx_ms:03d}_{_dup_i}"
            _dup_i += 1
    _defer_info(
        f"[QUALIFIED OPPORTUNITY] {shock.get('title')} | Target: {target_token} | "
        f"Expected Px: ${raw_vwap:.3f} (Eff: ${eff_px:.3f}) | Dist: {dist_pct:+.2f}% | TTE: {tte/60.0:.1f}m | "
        f"Depth: ${executable_depth_usd:.1f} | Sized Notional: ${effective_notional:.2f}"
    )

    # Dispatch live order via asynchronous EIP-712 adapter (non-blocking)
    fee_meta = shock.get("fee_metadata", {})
    if not self.dry_run or "fee_metadata" in shock:
        if (
            not isinstance(fee_meta, dict)
            or fee_meta.get("fee_rate_market") is None
            or not math.isfinite(float(fee_meta.get("fee_rate_market", 0.0)))
            or float(fee_meta.get("fee_rate_market", 0.0)) <= 0.0
            or not math.isfinite(float(fee_meta.get("fee_exponent", 1.0)))
            or float(fee_meta.get("fee_exponent", 1.0)) < 1.0
        ):
            _g("FEE_METADATA_REJECT", "Missing or invalid market fee metadata")
            logger.warning(
                "[FEE METADATA REJECT] Missing or invalid market fee metadata."
            )
            return
        if fee_meta.get("condition_id") and shock.get("condition_id"):
            if str(fee_meta["condition_id"]).lower() != str(shock["condition_id"]).lower():
                _g("FEE_PROVENANCE_REJECT", "Condition ID mismatch in dispatch fee metadata")
                logger.warning("[FEE PROVENANCE REJECT] Condition ID mismatch in dispatch fee metadata.")
                return
    if m_id:
        if m_id in _inflight_mkts:
            logger.debug(f"[MARKET ALREADY ACTIVE] Concurrent eval already reserved {m_id}. Skipping.")
            return
        _inflight_mkts.add(m_id)
    try:
        cond_id = shock.get("condition_id") or await asyncio.to_thread(
            self.get_condition_id, m_id
        )
        # AUDIT-13-04: Pre-warm tick and fee caches from shock metadata
        if cond_id and cond_id not in self.executor._fee_cache:
            self.executor._fee_cache[cond_id] = (m_fee_rate, m_fee_exp)
        if token_id and token_id not in self.executor._fee_cache:
            self.executor._fee_cache[token_id] = (m_fee_rate, m_fee_exp)
        if token_id and token_id not in self.executor._tick_size_cache and 0.04 < float(eff_px) < 0.96:
            self.executor._tick_size_cache[token_id] = 0.01
        notional_cap = getattr(self, "max_absolute_ticket_usd", None) or (10000.0 if getattr(self, "unconstrained_kelly", False) else MAX_ABSOLUTE_TICKET_USD)
        effective_notional = min(float(effective_notional), notional_cap)

        pre_cond_bal: Optional[float] = 0.0
        if not self.dry_run and token_id:
            # Hot-path: if token_id is not held in any active position or pending intent,
            # pre-trade balance is known in-memory to be strictly 0.0 (bypassing Polygon RPC call).
            has_prior_activity = (
                any(p.get("token_id") == token_id for p in self.active_positions.values())
                or any(i.get("token_id") == token_id for i in self.pending_entry_intents.values())
                or any(
                    p.get("token_id") == token_id
                    and (float(p.get("remaining_shares", 0.0) or 0.0) > 0.01 or p.get("status") not in ("FILLED", "SETTLED"))
                    for p in getattr(self, "closed_positions", [])[-20:]
                )
            )
            if has_prior_activity:
                _inv_t0 = time.perf_counter()
                try:
                    pre_cond_bal = await asyncio.to_thread(self.executor.get_onchain_erc1155_balance, token_id)
                except Exception:
                    pre_cond_bal = None
                _inv_ms = (time.perf_counter() - _inv_t0) * 1000.0
                _lt_inv = _CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
                if _lt_inv is not None:
                    _lt_inv.set(inventory_rpc_ms=round(_inv_ms, 3), inventory_rpc_used=True)
                    _lt_inv.stamp("inventory_check_end")
                if _inv_ms > 100.0:
                    logger.warning(f"[HOT-PATH RPC] on-chain ERC-1155 pre-trade read blocked entry for {_inv_ms:.0f}ms ({token_id[:12]}...)")
                if pre_cond_bal is None or not math.isfinite(float(pre_cond_bal)):
                    _inflight_mkts.discard(m_id)
                    logger.error(f"[ENTRY ABORTED] Cannot take authoritative pre-trade ERC-1155 snapshot for {token_id}.")
                    return
                pre_cond_bal = float(pre_cond_bal)
            else:
                pre_cond_bal = 0.0
    except BaseException:
        _inflight_mkts.discard(m_id)
        raise
    now_ts = time.time()
    event_id = str(shock.get("event_id") or shock.get("market_id") or "")
    expiry_ts = float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (now_ts + float(shock.get("seconds_to_expiry", 3600.0))))
    open_spot = float(open_spot_cand or shock.get("candle_open_spot") or shock.get("finalized_1h_open") or shock.get("spot_at_t0") or 0.0)
    spot_denom = "USD" if _is_usd_oracle else "USDT"
    entry_spot_ref = float(usd_spot_t0 if _is_usd_oracle else (shock.get("spot_at_t0") or shock.get("trigger_price") or open_spot))
    is_special_regime = regime in ("REGIME_D_BOUNDARY_LOCK", "REGIME_E_STRIKE_CONVERGENCE")
    target_exit = 0.99 if (self.hold_to_maturity or is_special_regime) else self._calculate_target_exit(raw_vwap, tte)

    # Smart FAK Price Buffer: entry qualification (`first_ask` & `raw_vwap`) is strictly <= eff_price_ceiling ($0.85),
    # while the FAK sweep limit (`sleeve_max_price`) in live mode allows up to +2c ($0.87) ONLY when p_fair +EV supports it,
    # preventing 0c slippage tolerance (`FAK_KILLED_NO_MATCH`) on qualified $0.84-$0.85 entries!
    if _maker_only_ceiling_rescue:
        sleeve_max_price = _maker_rescue_cap_px
        target_limit_px = _maker_rescue_cap_px
    else:
        if is_special_regime:
            sleeve_max_price = max(self.max_price_ceiling, max_allowed_price)
        elif not self.dry_run:
            _base_ceil = min(self.max_price_ceiling, max_allowed_price, eff_price_ceiling)
            if _is_live_real:
                if _real_unmocked_live_exec and regime in ("REGIME_A_MID_HOUR", "REGIME_B_LATE_SNIPER", "REGIME_C_SUBHOURLY"):
                    sleeve_max_price = float(_dir_tkr_cap)
                else:
                    _ev_fair_cap = round(((p_fair * 0.965) + ((1.0 - p_fair) * 0.92 * 0.38)) / 1.05, 4)
                    sleeve_max_price = max(_base_ceil, min(0.87, round(max_allowed_price + 0.02, 2), _ev_fair_cap))
            else:
                sleeve_max_price = _base_ceil
        else:
            sleeve_max_price = self.max_price_ceiling
        target_limit_px = round(min(raw_vwap + fak_buf, sleeve_max_price), 2)

    # Idea #1: Elastic [PREWARM LADDER] Rung Down-Snapping when executable depth at target_limit_px < effective_notional
    if not self.dry_run and self.dynamic_sizing and not _maker_only_ceiling_rescue:
        limit_depth_usd = sum(float(px) * float(sz) for px, sz in raw_asks if float(px) <= target_limit_px + 1e-6)
        if limit_depth_usd < float(effective_notional) - 1e-6:
            orig_notional = float(effective_notional)
            snapped = None
            for cand_rung in (160.00, 120.00, 90.00, 65.00, 48.00, 36.00, 28.00, 24.00, 20.00, 16.50, 14.00, 12.00, 10.00, 8.00):
                if cand_rung < orig_notional and limit_depth_usd >= cand_rung - 1e-6:
                    snapped = cand_rung
                    break
            if snapped is None and limit_depth_usd >= 8.00 - 1e-6 and limit_depth_usd < orig_notional:
                snapped = float(math.floor(limit_depth_usd))
            if snapped is not None:
                effective_notional = snapped
                _defer_info(
                    f"[IDEA-1 ELASTIC DOWNSNAP] {trade_id}: depth within limit ${target_limit_px:.2f} is "
                    f"${limit_depth_usd:.2f} < ${orig_notional:.2f}; down-snapping to pre-warmed rung ${effective_notional:.2f}."
                )

    # P0-02 Fix: Durable Entry Intent Journal persisted BEFORE remote order dispatch with complete supervisory metadata.
    # Exchange finality identifiers (order id, trade ids, tx hashes) are NOT known before submission and are
    # recovered authoritatively from exchange trade history on restart (never fabricated locally).
    self._last_exit_credit_window = None
    self.pending_entry_intents[trade_id] = {
        "schema_version": "2.3.8", "trade_id": trade_id, "entry_trade_id": trade_id, "sleeve": assigned_sleeve,
        "entry_order_id": None, "trade_ids": [], "transactions_hashes": [], "event_id": event_id,
        "market_id": m_id, "condition_id": cond_id, "token_id": token_id, "target_token": target_token,
        "asset": asset_str, "horizon": "15m" if is_subhourly else "1h", "is_subhourly": bool(is_subhourly),
        "candle_open_spot": open_spot, "entry_spot_ref": entry_spot_ref, "spot_denomination": spot_denom,
        "candle_sigma": float(shock.get("candle_sigma") or ((0.0025 if asset_str == "BTC" else 0.0034) if is_subhourly else (0.0050 if asset_str == "BTC" else 0.0068))),
        "candle_expiry_ts": expiry_ts, "entry_tte": tte, "target_exit_price": target_exit,
        "notional_usd": effective_notional, "intended_notional": effective_notional,
        "target_price": target_limit_px, "observed_vwap": raw_vwap, "sleeve_max_price": sleeve_max_price,
        "side": "BUY", "pre_token_balance": pre_cond_bal, "submitted_at_ts": now_ts, "heartbeat_ts": now_ts,
        "timestamp": now_ts, "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _inflight_dir_ids = self.__dict__.setdefault("_inflight_directional_entry_ids", set())
    _inflight_dir_ids.add(trade_id)
    if self.dynamic_sizing:
        # Sizing optimization: When dynamic sizing is True, pass sizing_fn=None so SlippageKellyGuard
        # in polymarket_live_executor.py NEVER overwrites or shrinks the elastic ticket.
        active_sizing_fn = None
    else:
        active_sizing_fn = (lambda px: _calc_kelly(max(0.95, p_model_for_sizing), px, live_bankroll)) if (p_model_for_sizing and live_bankroll) else None

    # v3.3 Post-Dispatch State Save: the entry intent is already in RAM (pending_entry_intents) before
    # dispatch; the disk save/fsync runs only AFTER execute_snipe_order_async returns so it never
    # contends for the GIL while the HTTP order is in flight.
    _base_snipe_kw = dict(
        trade_id=trade_id, token_id=token_id, target_token=target_token, side="BUY",
        depth_hurdle=self.depth_hurdle, max_price_ceiling=sleeve_max_price, min_price_floor=min_allowed_price,
        expected_best_price=(t0_best_ask if (_is_live_real and 0.0 < t0_best_ask < 0.99) else None),
        market_id=str(shock.get("market_id")), condition_id=cond_id,
        market_fee_rate=fee_meta.get("fee_rate_market"), market_fee_exponent=fee_meta.get("fee_exponent", 1.0),
        sizing_fn=active_sizing_fn, max_ticket_cap=getattr(self, "max_absolute_ticket_usd", None),
        prefetched_pre_balance=pre_cond_bal,
    )
    _p3a_kw = dict(
        trade_id=trade_id, token_id=token_id, target_token=target_token, asset_str=asset_str,
        effective_notional=effective_notional, first_ask=first_ask, first_bid=first_bid,
        min_allowed_price=min_allowed_price, open_spot=open_spot, entry_spot_ref=entry_spot_ref,
        spot_denom=spot_denom, tte=tte, pre_cond_bal=pre_cond_bal, book_snapshot=book_snapshot,
        is_subhourly=bool(is_subhourly), obi_l1=float(token_features.get("obi_l1") or 0.0),
    )
    def _is_fak_400(r: Any) -> bool:
        d = (r.details or {}) if r is not None else {}
        return r is not None and (r.mode in ("FAK_KILLED_NO_MATCH", "CLOB_HTTP_400_REJECTION") or bool(d.get("fak_killed") or d.get("clob_400_rejection")))

    res = None
    _det_400 = False
    _eval_exc: Optional[BaseException] = None
    try:
        _lt_disp = _CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
        if _lt_disp is not None:
            _lt_disp.stamp("dispatch_call")
            _lt_disp.set(effective_notional_usd=effective_notional, target_limit_px=target_limit_px, trade_id=trade_id, sleeve=assigned_sleeve, target_token=target_token)
        if _maker_only_ceiling_rescue:
            if _hctx is not None:
                _hctx[1]()
                _hctx[2]()
            logger.info(
                f"[CEILING -> PHASE 3A MAKER RESCUE] {trade_id}: ask=${first_ask:.2f} > +EV ceiling=${_maker_rescue_cap_px:.2f}; "
                f"skipping Taker FAK and routing directly to 0%-fee postOnly Maker BUY <= ${_maker_rescue_cap_px:.2f}."
            )
            rescue_res = await self._attempt_live_phase3a_maker_rescue(**_p3a_kw, max_allowed_price=_maker_rescue_cap_px)
            _adv_hit_ts = self.__dict__.get("_p3a_adverse_shield_ts", {}).pop(trade_id, None)
            if rescue_res is not None:
                res = rescue_res
            else:
                if _adv_hit_ts is not None or not _v5_live_strict:
                    _maker_rescue_cd_map[str(m_id or "")] = time.time()
                res = OrderResult(
                    success=False, order_id=None, trade_id=trade_id, token_id=token_id,
                    target_token=target_token, side="BUY", price=_maker_rescue_cap_px, size=0.0,
                    notional_usd=effective_notional, fee_usd=0.0, latency_ms=0.0,
                    mode="FAK_KILLED_NO_MATCH", execution_status=ExecutionStatus.REJECTED,
                    details={"fak_killed": True, "maker_ceiling_rescue_unfilled": True},
                    error="MAKER_CEILING_RESCUE_UNFILLED",
                )
        else:
            if _hctx is not None:
                self._main_loop.call_soon(_hctx[1])
            res = await self.executor.execute_snipe_order_async(
                **_base_snipe_kw, notional_usd=effective_notional, target_price=target_limit_px, prefetched_book=book_snapshot,
            )
            _ws_ids_cur = getattr(self.executor, "_wire_submitted_trade_ids", None)
            if _ws_ids_cur is not None:
                _ws_ids_cur.discard(str(trade_id))
            if _hctx is not None:
                _hctx[1]()
            # Idea #1 Post-Dispatch Safety Net: If executor simulated FOK sweep infeasible at higher rung, down-snap to $16.50 / $12.00
            if not res.success and "FOK Sweep Infeasible" in str(res.error or "") and not self.dry_run and self.dynamic_sizing and float(effective_notional) > 8.0:
                for fallback_rung in (28.00, 24.00, 20.00, 16.50, 12.00, 8.00):
                    if fallback_rung >= float(effective_notional) - 0.10:
                        continue
                    logger.info(
                        f"[IDEA-1 FOK SWEEP DOWNSNAP RETRY] {trade_id}: ${effective_notional:.2f} infeasible at "
                        f"${target_limit_px:.2f}; stepping down to pre-warmed rung ${fallback_rung:.2f}."
                    )
                    effective_notional = fallback_rung
                    _p3a_kw["effective_notional"] = effective_notional
                    if trade_id in self.pending_entry_intents:
                        self.pending_entry_intents[trade_id]["notional_usd"] = effective_notional
                    res = await self.executor.execute_snipe_order_async(
                        **_base_snipe_kw, notional_usd=effective_notional, target_price=target_limit_px, prefetched_book=book_snapshot,
                    )
                    _ws_ids_cur = getattr(self.executor, "_wire_submitted_trade_ids", None)
                    if _ws_ids_cur is not None:
                        _ws_ids_cur.discard(str(trade_id))
                    if res.success or "FOK Sweep Infeasible" not in str(res.error or ""):
                        break

            # Idea #5: Sequential +2c Pre-Signed Fallback (disabled in live real mode by Purged WFO v4.0 unless explicitly enabled)
            _allow_p2c = not _is_live_real or (bool((getattr(self, "risk_config", None) or RISK_CONFIG).get("enable_fak_plus2c_fallback", False)) and z_strike >= 1.25)
            if _is_fak_400(res) and not self.dry_run and self.dynamic_sizing and _allow_p2c and target_limit_px + 0.01 <= sleeve_max_price + 1e-6:
                fallback_limit_px = round(min(sleeve_max_price, target_limit_px + 0.02), 2)
                if fallback_limit_px > target_limit_px + 1e-6:
                    logger.info(
                        f"[IDEA-5 FAK +2c FALLBACK] {trade_id}: missed L1 at ${target_limit_px:.2f} (0 filled, mode={res.mode}); "
                        f"firing sequential pre-signed fallback at ${fallback_limit_px:.2f} (ceiling=${sleeve_max_price:.2f})."
                    )
                    target_limit_px = fallback_limit_px
                    if trade_id in self.pending_entry_intents:
                        self.pending_entry_intents[trade_id]["target_price"] = target_limit_px
                    fresh_fallback_book = fast_tick_book_for_token(read_fast_tick(asset_str), token_id) or book_snapshot
                    try:
                        res = await self.executor.execute_snipe_order_async(
                            **_base_snipe_kw, notional_usd=effective_notional, target_price=target_limit_px,
                            prefetched_book=fresh_fallback_book, max_book_buffer=0.04,
                        )
                    except TypeError as _te:
                        if "max_book_buffer" not in str(_te):
                            raise
                        res = await self.executor.execute_snipe_order_async(
                            **_base_snipe_kw, notional_usd=effective_notional, target_price=target_limit_px,
                            prefetched_book=fresh_fallback_book,
                        )
                    _ws_ids_cur = getattr(self.executor, "_wire_submitted_trade_ids", None)
                    if _ws_ids_cur is not None:
                        _ws_ids_cur.discard(str(trade_id))

            if _lt_disp is not None and res is not None:
                _fbk = (fast_tick_book_for_token(read_fast_tick(asset_str), token_id) or {}) if _is_live_real else {}
                _fpa = min((float(a["price"]) for a in (_fbk.get("asks") or []) if float(a.get("size", 0)) > 0), default=None)
                _fpb = max((float(b["price"]) for b in (_fbk.get("bids") or []) if float(b.get("size", 0)) > 0), default=None)
                if res.success:
                    _lt_disp.set(path_type="TAKER_FOK", target_px=target_limit_px, fill_px=res.price, notional_usd=res.notional_usd or effective_notional, post_ask=_fpa, post_bid=_fpb, stage_outcome="FILLED_TAKER")
                elif _is_fak_400(res):
                    _so_t = "CLOB_HTTP_400_REJECTION" if (res.mode == "CLOB_HTTP_400_REJECTION" or bool((res.details or {}).get("clob_400_rejection"))) else "FAK_KILLED"
                    _lt_disp.set(path_type="TAKER_FOK", target_px=target_limit_px, notional_usd=effective_notional, post_ask=_fpa, post_bid=_fpb, stage_outcome=_so_t, gate_detail=str(res.error or ""))
                elif "SlippageGuard" in str(res.error or ""):
                    _g("PRICE_BAND_REJECT", str(res.error or ""), cap_px=target_limit_px, eval_ask=res.price or first_ask)
                else:
                    _g("EXEC_PREFLIGHT_REJECT", str(res.error or ""))

            # Live Phase 3A Passive Maker-In Rescue (GTC + postOnly=True, 0% fee + 20% Maker rebate, 0ms itode, 3.5s TTL)
            # Promoted from validated shadow telemetry: captures 0%-fee + 20%-rebate fills on FAK misses while canceling toxic retraces in <10ms.
            if _hctx is not None:
                _hctx[1]()
                _hctx[2]()
            if _is_fak_400(res) and (not _is_live_real or (z_strike >= 0.78 and abs(dist_pct) >= 0.06)):
                if _emit_shock_attempt_trace is not None and _lt_disp is not None:
                    _emit_shock_attempt_trace(_lt_disp, shock)
                    _lt_disp.set(skip_forensic=True)
                _p3a_cap = min(float(max_allowed_price), _p3a_15m_long_cap) if (is_subhourly and tte > 240.0) else max_allowed_price
                rescue_res = await self._attempt_live_phase3a_maker_rescue(**_p3a_kw, max_allowed_price=_p3a_cap)
                self.__dict__.get("_p3a_adverse_shield_ts", {}).pop(trade_id, None)
                if rescue_res is not None:
                    res = rescue_res
    except BaseException as _e_eval:
        _eval_exc = _e_eval
        raise
    finally:
        _inflight_mkts.discard(m_id)
        if _hctx is not None:
            _hctx[1]()
            _hctx[2]()
        _ws_ids_fin = getattr(self.executor, "_wire_submitted_trade_ids", None)
        _taker_wire_interrupted = bool(_ws_ids_fin and (str(trade_id) in _ws_ids_fin))
        if _ws_ids_fin is not None:
            _ws_ids_fin.discard(str(trade_id))
        _intent_fin = self.pending_entry_intents.get(trade_id) or {}
        _maker_wire_interrupted = bool(_intent_fin.get("maker_wire_inflight"))
        _unhandled_non_cancel = _eval_exc is not None and isinstance(_eval_exc, Exception)
        if _taker_wire_interrupted or _maker_wire_interrupted or _unhandled_non_cancel:
            _inflight_dir_ids.discard(trade_id)
            if trade_id in self.pending_entry_intents:
                self.pending_entry_intents[trade_id].pop("maker_wire_inflight", None)
                self.pending_entry_intents[trade_id]["needs_runtime_recovery"] = True
        elif res is None:
            _inflight_dir_ids.discard(trade_id)
            self.pending_entry_intents.pop(trade_id, None)
        else:
            _det_err = str(res.error or "").lower() + str((res.details or {}).get("raw_exception", "")).lower()
            _det_400 = any(s in _det_err for s in ("status_code=400", "status=400", "invalid amounts", "supports a max accuracy"))
            _non_unknown_rej = (not res.success) and not bool((res.details or {}).get("outcome_unknown"))
            if _is_fak_400(res) or _det_400 or _non_unknown_rej:
                self.pending_entry_intents.pop(trade_id, None)
                _inflight_dir_ids.discard(trade_id)
        await asyncio.to_thread(self.save_state)

    if _is_fak_400(res):
        _inflight_dir_ids.discard(trade_id)
        if self.pending_entry_intents.pop(trade_id, None) is not None:
            await asyncio.to_thread(self.save_state)
        if not self.dry_run:
            self._register_shadow_phase3a_maker_in(
                shock, target_token, first_ask, first_bid, max_allowed_price, raw_asks,
                f"CLOB_400_OR_FAK_MISS:{res.mode}", bool(is_subhourly), float(dist_pct), float(tte),
            )
        logger.info(
            f"[CLOB REJECTION / FAK ZERO MATCH] {trade_id} rejected deterministically by CLOB (0 shares filled, error={res.error}). "
            f"Released entry intent immediately without halting."
        )
        return

    # Double check: Never treat deterministic HTTP 400 / invalid amounts as outcome_unknown
    if _det_400:
        _inflight_dir_ids.discard(trade_id)
        if self.pending_entry_intents.pop(trade_id, None) is not None:
            await asyncio.to_thread(self.save_state)
        logger.warning(f"[HTTP 400 REJECTION OVERRIDE] {trade_id} rejected with HTTP 400 ({res.error}). Not registering in active_positions.")
        return

    self.pending_entry_intents.pop(trade_id, None)
    _inflight_dir_ids.discard(trade_id)
    if (res.details or {}).get("outcome_unknown"):
        # P0-02 Fix: Persist ENTRY_OUTCOME_UNKNOWN position to track potential fills.
        ref_px = float(res.price or raw_vwap or 0.0)
        est_shares = float(res.size or (effective_notional / max(ref_px, 0.01)))
        unknown_pre_bal = (res.details or {}).get("pre_token_balance")
        pos_record = {
            "trade_id": trade_id, "event_id": event_id, "market_id": m_id, "condition_id": cond_id,
            "token_id": token_id, "target_token": target_token, "asset": asset_str,
            "candle_open_spot": open_spot, "entry_spot_ref": entry_spot_ref, "spot_denomination": spot_denom,
            "candle_sigma": float(shock.get("candle_sigma", 0.005) or 0.005),
            "entry_price": ref_px, "entry_shares": est_shares, "gross_entry_shares": est_shares,
            "remaining_shares": est_shares, "filled_exit_shares": 0.0, "remaining_exit_shares": est_shares,
            "remaining_cost_basis": float(effective_notional), "realized_exit_cash": 0.0, "realized_exit_fee": 0.0,
            "gross_exit_cash": 0.0, "average_exit_price": 0.0, "exit_trade_ids": [],
            "notional_usd": float(effective_notional), "intended_notional": float(effective_notional),
            "fee_usd": float(res.fee_usd or 0.0), "entry_fee_cash_usd": float(res.fee_usd or 0.0),
            "entry_fee_asset": "USDC", "fee_source": "crypto_fees_v2",
            "fee_rate_applied": m_fee_rate, "fee_exponent_applied": m_fee_exp,
            "market_fee_rate": m_fee_rate, "market_fee_exponent": m_fee_exp,
            "target_exit_price": self._calculate_target_exit(ref_px, tte),
            "entry_time_utc": datetime.now(timezone.utc).isoformat(), "entry_ts": now_ts, "submitted_at_ts": now_ts,
            "candle_expiry_ts": expiry_ts, "pre_token_balance": float(unknown_pre_bal if unknown_pre_bal is not None else pre_cond_bal),
            "order_id": res.order_id or (res.details or {}).get("entry_order_id"),
            "entry_order_id": res.order_id or (res.details or {}).get("entry_order_id"),
            "trade_ids": [], "transactions_hashes": [], "status": "ENTRY_OUTCOME_UNKNOWN",
            "exit_order_status": "ENTRY_OUTCOME_UNKNOWN", "inventory_reconciled": False,
            "is_liquidating": False, "unwind_order_id": None, "unwind_start_time": 0.0,
        }
        self.active_positions[trade_id] = pos_record
        # Reconcilable global halt (not a permanent risk-controller latch): cleared only by
        # authoritative reconciliation of this exact entry.
        self._refresh_global_halt()
        self.save_state()
        logger.critical(
            f"[ENTRY OUTCOME UNKNOWN] Trade {trade_id} registered in active_positions for reconciliation! "
            "Halting new entries until exchange reconciliation."
        )
        return

    if not res.success:
        # Authoritative rejection: durably clear the intent so restart does not re-halt on it.
        await asyncio.to_thread(self.save_state)
        if not self.dry_run:
            self._register_shadow_phase3a_maker_in(
                shock, target_token, first_ask, first_bid, max_allowed_price, raw_asks,
                f"EXECUTION_REJECT:{res.mode or res.error}", bool(is_subhourly), float(dist_pct), float(tte),
            )

    if res.success:
        if _rsw_candidate is not None and hasattr(self, "recent_shock_window") and isinstance(self.recent_shock_window, list):
            self.recent_shock_window.append(_rsw_candidate)
        self.trades_this_hour += 1
        self.trades_per_market[m_id] += 1
        self.trades_per_market_direction[(m_id, target_token)] += 1
        self.traded_market_ids.add(m_id)
        target_exit = 0.99 if (self.hold_to_maturity or is_special_regime) else self._calculate_target_exit(res.price, tte)
        asset_sym = asset_str
        if asset_sym not in effective_allowed_assets:
            raise RuntimeError(f"Refusing to create position with unresolved/disallowed asset: {asset_sym!r}")
        open_spot = float(open_spot_cand or shock.get("finalized_1h_open") or shock.get("candle_open_spot") or shock.get("spot_at_t0") or 0.0)
        entry_spot_ref = float(usd_spot_t0 if _is_usd_oracle else (shock.get("spot_at_t0") or shock.get("trigger_price") or open_spot))
        if open_spot <= 0.0:
            ref_fn = self.get_usd_reference_spot_price if _is_usd_oracle else self.get_reference_spot_price
            open_spot = (await asyncio.to_thread(ref_fn, asset_sym)) or 0.0
            if entry_spot_ref <= 0.0:
                entry_spot_ref = open_spot

        pos_record = {
            "trade_id": trade_id, "sleeve": assigned_sleeve, "entry_tte": tte, "event_id": event_id,
            "market_id": str(shock.get("market_id")), "condition_id": cond_id, "token_id": token_id,
            "target_token": target_token, "asset": asset_sym, "horizon": "15m" if is_subhourly else "1h",
            "is_subhourly": bool(is_subhourly), "candle_duration_s": (900.0 if is_subhourly else 3600.0), "candle_open_spot": open_spot,
            "entry_spot_ref": entry_spot_ref, "spot_denomination": spot_denom,
            "candle_sigma": float(shock.get("candle_sigma") or ((0.0025 if asset_sym == "BTC" else 0.0034) if is_subhourly else (0.0050 if asset_sym == "BTC" else 0.0068))),
            "entry_price": res.price, "entry_shares": res.size, "gross_entry_shares": float(res.size),
            "remaining_shares": res.size, "filled_exit_shares": 0.0, "remaining_exit_shares": res.size,
            "remaining_cost_basis": res.notional_usd, "realized_exit_cash": 0.0, "realized_exit_fee": 0.0,
            "gross_exit_cash": 0.0, "average_exit_price": 0.0, "exit_trade_ids": [],
            "notional_usd": res.notional_usd, "fee_usd": res.fee_usd, "entry_fee_cash_usd": float(res.fee_usd or 0.0),
            "entry_fee_asset": "USDC", "fee_source": "crypto_fees_v2",
            "fee_rate_applied": (0.0 if res.mode == "LIVE_PHASE3A_MAKER_IN" else m_fee_rate), "fee_exponent_applied": m_fee_exp,
            "market_fee_rate": m_fee_rate, "market_fee_exponent": m_fee_exp,
            "target_exit_price": 0.99 if self.hold_to_maturity else target_exit, "exit_order_size": float(res.size),
            "entry_time_utc": datetime.now(timezone.utc).isoformat(), "entry_ts": time.time(),
            "candle_expiry_ts": time.time() + tte, "pre_token_balance": res.details.get("pre_token_balance", pre_cond_bal),
            "order_id": res.order_id, "entry_order_id": res.order_id, "trade_ids": res.details.get("trade_ids", []),
            "transactions_hashes": res.details.get("transactions_hashes", []), "status": res.execution_status,
            "exit_order_id": None, "exit_order_status": "NONE", "is_liquidating": False,
            "unwind_order_id": None, "unwind_start_time": 0.0,
        }
        # IMMUTABLE PERSISTENCE: Save open position immediately before placing exit order
        self.active_positions[trade_id] = pos_record
        if not self.dry_run:
            _fill_cost_total = max(0.0, float(res.notional_usd or 0.0) + float(res.fee_usd or 0.0))
            if getattr(self, "_last_known_collateral", None) is not None and _fill_cost_total > 0.0:
                self._last_known_collateral = max(0.0, float(self._last_known_collateral) - _fill_cost_total)
                self._last_entry_debit_window = (time.time(), float(self._last_known_collateral))
            self.executor.invalidate_collateral_cache()
            self._pending_collateral_refresh = True
        await asyncio.to_thread(self.save_state)
        logger.info(f"✓ POSITION RECORDED & PERSISTED: {trade_id} | Shares={res.size:.2f} @ ${res.price:.4f} | Status={res.execution_status}")
        if not self.dry_run:
            try:
                send_operational_alert(
                    "LIVE_ORDER_FILL",
                    f"{trade_id} {shock.get('title')!r} {res.size:.2f} sh @ ${res.price:.4f} (~${res.size * res.price:.2f}) status={res.execution_status}",
                    "INFO",
                    dedupe_key=f"fill:{trade_id}",
                )
            except Exception:
                logger.debug("[ALERT] fill alert construction failed", exc_info=True)

        # Post resting maker scalp limit order with post_only=True (Policy B2)
        # P0 Invariant: Only post exit immediately if position is CONFIRMED on-chain!
        if res.execution_status == ExecutionStatus.POSITION_CONFIRMED:
            pos_record["inventory_reconciled"] = True
            pos_record["entry_finality_source"] = "EXECUTOR_CONFIRMED_DELTA"
            # Sequential Iceberg Tranche Stepping for tickets >= $10
            rem_total = float(res.size)
            entry_px = float(pos_record.get("entry_price", 0.70))
            use_tranches = self._use_two_tranche_maker_exit(assigned_sleeve)
            t1_offset = self._tranche1_tp_offset(assigned_sleeve)
            is_live_ctf = (
                (not self.dry_run)
                and getattr(self.executor, "auth_mode", "") in ("LIVE", "AUTHENTICATED_L2")
                and bool(token_id and str(token_id).isdigit() and len(str(token_id)) >= 20)
                and not getattr(self, "enable_mid_hour_t1_12c", False)
            )
            single_exit_px = (0.96 if is_live_ctf else min(0.96, round(entry_px + 0.16, 2))) if use_tranches else target_exit
            exit_size = rem_total
            exit_price = single_exit_px
            if use_tranches and float(pos_record.get("notional_usd", 0.0) or 0.0) >= 10.0 and rem_total >= 10.0:
                t1_sz = float((Decimal(str(rem_total)) * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                t2_sz = float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                if t1_sz >= 5.0 and t2_sz >= 5.0:
                    # v3.9 Upgrade 2: Match _attempt_maker_exit_post_impl (50% @ $0.95 + 50% @ $0.98 on live CTF)
                    t1_px = 0.95 if is_live_ctf else min(0.94, round(entry_px + t1_offset, 2))
                    t2_px = 0.98
                    pos_record["exit_tranches"] = [
                        {"idx": 1, "size": t1_sz, "price": t1_px, "status": "PENDING"},
                        {"idx": 2, "size": t2_sz, "price": t2_px, "status": "PENDING"},
                    ]
                    exit_size = t1_sz
                    exit_price = pos_record["exit_tranches"][0]["price"]
                    pos_record["target_exit_price"] = exit_price
                else:
                    exit_size = rem_total
                    exit_price = single_exit_px
                    pos_record["target_exit_price"] = exit_price
            else:
                exit_size = rem_total
                exit_price = single_exit_px
                pos_record["target_exit_price"] = exit_price

            exit_res = await asyncio.to_thread(
                self.executor.post_maker_exit_order,
                token_id=token_id,
                price=exit_price,
                size=exit_size,
                side="SELL",
            )
            posted = self._apply_exit_post_result(pos_record, exit_res, float(exit_size))
            if pos_record.get("exit_tranches") and posted:
                pos_record["exit_tranches"][0]["status"] = "POSTED"
            elif pos_record.get("exit_tranches") and (exit_res or {}).get("outcome_unknown"):
                pos_record["exit_tranches"][0]["status"] = "IN_FLIGHT"
            if posted:
                logger.info(f"✓ MAKER SCALP ORDER POSTED (POST-ONLY): {pos_record['exit_order_id']} | {exit_size:.2f} shares @ ${exit_price:.4f}")
        else:
            pos_record["exit_order_status"] = "AWAITING_DELTA_SETTLEMENT"
            logger.info(f"Position {trade_id} in {res.execution_status}. Background loop will verify on-chain delta before posting maker exit.")
            if not self.dry_run:
                # v3.4: poll every 0.20s for up to 5.0s so the maker TP posts the instant shares arrive.
                self._spawn_fast_confirm(trade_id)

        await asyncio.to_thread(self.save_state)

async def _hv__maybe_recycle_disputed_htm_lock(self, tid: str, pos: Dict[str, Any], now_ts: float) -> bool:
    """
    Automatically recycles capital from a `hold_to_maturity_lock` (`is_single_leg_lock`) when Gamma
    reports `umaResolutionStatus == "disputed"` and the live CLOB bid (`>= $0.997` with full share depth)
    locks in strictly positive net realized profit (`>= +$0.02`), preventing 48h UMA DVM capital freeze.
    """
    if (
        self.dry_run
        or pos.get("is_liquidating")
        or pos.get("status") == "UNRESOLVED_SETTLEMENT"
        or position_is_settlement_receivable(pos)
        or not bool(pos.get("inventory_reconciled", False))
        or "KMIA" in str(pos.get("asset") or "").upper()
        or "KMIA" in str(tid or "").upper()
    ):
        return False
    if (now_ts - float(pos.get("_last_disputed_recycle_ts", 0.0) or 0.0)) < 60.0:
        return False
    pos["_last_disputed_recycle_ts"] = now_ts
    token_id = str(pos.get("token_id") or "")
    rem_shrs = float(pos.get("remaining_shares", pos.get("entry_shares", 0.0)) or 0.0)
    if not token_id or rem_shrs < 5.0:
        return False
    if hasattr(self.executor, "get_market_book_async"):
        book = await self.executor.get_market_book_async(token_id)
    else:
        book = await asyncio.to_thread(self.executor.get_market_book, token_id)
    raw_bids = (book or {}).get("bids") or []
    qual_bids = sorted(
        [
            {"price": float(b["price"] if isinstance(b, dict) else b[0]), "size": float(b["size"] if isinstance(b, dict) else b[1])}
            for b in raw_bids
            if float((b.get("price", 0.0) if isinstance(b, dict) else b[0]) or 0.0) >= 0.997
            and float((b.get("size", 0.0) if isinstance(b, dict) else b[1]) or 0.0) > 0.0
        ],
        key=lambda x: x["price"],
        reverse=True,
    )
    cum_sz = 0.0
    min_px = 0.0
    for lv in qual_bids:
        cum_sz += lv["size"]
        min_px = lv["price"]
        if cum_sz >= rem_shrs:
            break
    if cum_sz < rem_shrs or min_px < 0.997:
        return False
    _fr_raw = pos.get("fee_rate_applied")
    if _fr_raw is None:
        _fr_raw = pos.get("fee_rate_market", pos.get("fee_rate", 0.07))
    fr = float(_fr_raw or 0.0)
    fe = float(pos.get("fee_exponent_applied", pos.get("fee_exponent", 1.0)) or 1.0)
    est_exit_fee = (rem_shrs * fr * ((min_px * (1.0 - min_px)) ** fe)) if fr > 0.0 else 0.0
    est_net_pnl = self.calculate_realized_cash_pnl(
        pos, float(pos.get("realized_exit_cash", 0.0) or 0.0) + rem_shrs * min_px, float(pos.get("realized_exit_fee", 0.0) or 0.0) + est_exit_fee
    )
    if est_net_pnl < 0.02:
        return False
    if pos.get("exit_order_id"):
        _ex_d = str(pos["exit_order_id"])
        _c_res_d = await asyncio.to_thread(self.executor.cancel_order, _ex_d)
        _sum_d = (
            await asyncio.to_thread(self.executor.get_order_fill_summary, _ex_d, str(token_id))
            if hasattr(self.executor, "get_order_fill_summary")
            else None
        )
        if isinstance(_sum_d, dict):
            self._record_order_summary(pos, _sum_d, float(pos.get("target_exit_price", 0.999) or 0.999), taker=False)
        rem_shrs = float(pos.get("remaining_shares", rem_shrs) or 0.0)
        if rem_shrs <= 0.02:
            self.executor.release_inventory(reservation_id=_ex_d)
            pos["exit_order_id"] = None
            pos["_htm_passive_recycle_active"] = False
            self.executor.invalidate_collateral_cache()
            self._pending_collateral_refresh = True
            self._close_position(tid, pos, "FILLED", "HTM_PASSIVE_MAKER_RECYCLE_FILLED", won=True)
            return True
        _term_d = bool(
            (isinstance(_sum_d, dict) and _sum_d.get("terminal"))
            or (isinstance(_c_res_d, dict) and (_c_res_d.get("is_canceled") or _ex_d in (_c_res_d.get("canceled") or [])))
        )
        if not _term_d:
            return False
        self.executor.release_inventory(reservation_id=_ex_d)
        if _ex_d not in pos.setdefault("canceled_maker_exit_oids", []):
            pos["canceled_maker_exit_oids"].append(_ex_d)
        pos["exit_order_id"] = None
        pos["_htm_passive_recycle_active"] = False
        if rem_shrs < 5.0:
            self.save_state()
            return False
    if isinstance(getattr(self.executor, "_fee_cache", None), dict) and str(token_id) not in self.executor._fee_cache:
        self.executor._fee_cache[str(token_id)] = (fr, fe)
    unwind_res = await asyncio.to_thread(
        self.executor.execute_unwind_order,
        token_id=token_id,
        size=rem_shrs,
        side="SELL",
        min_price=min_px,
        neg_risk=pos.get("neg_risk"),
    )
    outcome = self._handle_unwind_response(
        tid, pos, unwind_res, rem_shrs,
        "UMA_DISPUTED_LOCK_PROFIT_RECYCLE", "PARTIAL_UNWIND_REMAINING", min_px,
    )
    if outcome != "FAILED":
        self.executor.invalidate_collateral_cache()
        self._pending_collateral_refresh = True
        self.save_state()
        logger.warning(
            f"♻️ [UMA DISPUTE RECYCLE] {tid} (mkt={pos.get('market_id')}): exited {rem_shrs:.2f} "
            f"disputed lock shares @ >=${min_px:.3f} (est_net=${est_net_pnl:+.2f}) -> {outcome}"
        )
        return True
    return False


def maybe_emit_recorder_fast_riskless_ipc(
    recorder: Any,
    snap: Mapping[str, Any],
    now_ts: float,
) -> int:
    """
    Zero-latency (`<1ms` wire-to-Harvester) `C1_BINARY_COMPLETE_SET` IPC sniper inside
    `PolymarketDualFeed1HRecorder`: emits `COMPLETE_SET` (`1 UP + 1 DOWN == $1.00` on identical
    `condition_id`) directly over `@polymarket_d1_box_notify` whenever `ask_UP + ask_DOWN + V2_fees <= 0.992`.
    """
    import os as _os

    sink_list = getattr(recorder, "_test_cand_sink", None)
    custom_cp = getattr(recorder, "d1_live_candidates_file", None)
    if _os.name == "nt" and not isinstance(sink_list, list) and custom_cp is None:
        return 0
    asset = str(snap.get("asset") or getattr(recorder, "asset", "CRYPTO") or "CRYPTO").upper()
    cd_map = recorder.__dict__.setdefault("_last_c1_ipc_ts", {})
    emitted = 0

    slices: List[Tuple[str, str, Mapping[str, Any], float]] = []
    cm1h = getattr(recorder, "current_market", None)
    if isinstance(cm1h, Mapping) and isinstance(snap.get("UP"), Mapping) and isinstance(snap.get("DOWN"), Mapping):
        exp_1h = cm1h["end_dt"].timestamp() if "end_dt" in cm1h else float(snap.get("expiry_ts_1h") or 0.0)
        fr_1h = float(getattr(recorder, "fee_rate_market", 0.072) or 0.072)
        slices.append(("1h", str(cm1h.get("condition_id") or ""), {"market_id": cm1h.get("market_id"), "expiry_ts": exp_1h, "UP": snap["UP"], "DOWN": snap["DOWN"]}, fr_1h))
    for hz_lbl, attr_n, sk in (("5m", "market_5m", "m5"), ("15m", "market_15m", "m15"), ("4h", "market_4h", "h4")):
        mh_s = snap.get(sk)
        mh_r = getattr(recorder, attr_n, None)
        if isinstance(mh_s, Mapping) and isinstance(mh_s.get("UP"), Mapping) and isinstance(mh_s.get("DOWN"), Mapping):
            fr_m = float((mh_r or {}).get("fee_metadata", {}).get("fee_rate_market", 0.072) if isinstance(mh_r, Mapping) else 0.072)
            slices.append((hz_lbl, str(mh_s.get("condition_id") or (mh_r or {}).get("condition_id") or ""), mh_s, fr_m))

    for hz_lbl, cid_s, mh_d, fr_raw in slices:
        mid_s = str(mh_d.get("market_id") or "")
        exp_f = float(mh_d.get("expiry_ts") or 0.0)
        rem_s = exp_f - now_ts
        if not cid_s or not mid_s or rem_s < 25.0 or (now_ts - float(cd_map.get(cid_s, 0.0) or 0.0)) < 2.0:
            continue
        up_b, dn_b = mh_d["UP"], mh_d["DOWN"]
        tok_u, tok_d = str(up_b.get("token_id") or ""), str(dn_b.get("token_id") or "")
        if (
            not tok_u or not tok_d or tok_u == tok_d
            or bool(up_b.get("is_crossed")) or bool(dn_b.get("is_crossed"))
            or float(up_b.get("age_book_ms") if up_b.get("age_book_ms") is not None else 9999.0) > 650.0
            or float(dn_b.get("age_book_ms") if dn_b.get("age_book_ms") is not None else 9999.0) > 650.0
        ):
            continue
        ya = float(up_b.get("best_ask") or 0.0)
        na = float(dn_b.get("best_ask") or 0.0)
        yb = float(up_b.get("best_bid") or 0.0)
        nb = float(dn_b.get("best_bid") or 0.0)
        if (0.0 < yb and ya <= yb) or (0.0 < nb and na <= nb):
            continue
        if not (0.01 <= ya <= 0.985 and 0.01 <= na <= 0.985) or (ya + na) > 0.992:
            continue
        u_sz = float(up_b.get("ask_size_l1") or 0.0)
        d_sz = float(dn_b.get("ask_size_l1") or 0.0)
        if min(u_sz, d_sz) < 8.0:
            continue
        fr = 0.0 if asset in {"XAU", "XAG"} else max(0.0, float(fr_raw or 0.072))
        ded_u = (fr * (1.0 - ya)) if (fr > 0.0 and 0.0 < ya < 1.0) else 0.0
        ded_d = (fr * (1.0 - na)) if (fr > 0.0 and 0.0 < na < 1.0) else 0.0
        if ded_u >= 0.50 or ded_d >= 0.50:
            continue
        net_cost = round((ya / (1.0 - ded_u)) + (na / (1.0 - ded_d)), 5)
        max_cap = 0.994 if fr <= 1e-9 else 0.989
        if net_cost > max_cap:
            continue
        net_avail_pair = min(u_sz * (1.0 - ded_u), d_sz * (1.0 - ded_d))
        if net_avail_pair < 7.5:
            continue
        cd_map[cid_s] = now_ts
        sh_pair = max(5, min(30, int(math.floor(net_avail_pair / 1.5))))
        gross_u = round(math.ceil((sh_pair / (1.0 - ded_u)) * 100.0) / 100.0, 2)
        gross_d = round(math.ceil((sh_pair / (1.0 - ded_d)) * 100.0) / 100.0, 2)
        ws_bks_c1 = {}
        for tk_x, sb_x in ((tok_u, up_b), (tok_d, dn_b)):
            rb_x = [{"price": str(r[0]), "size": str(r[1])} for r in (sb_x.get("raw_top_bids") or [])[:10] if isinstance(r, (list, tuple)) and len(r) >= 2]
            ra_x = [{"price": str(r[0]), "size": str(r[1])} for r in (sb_x.get("raw_top_asks") or [])[:10] if isinstance(r, (list, tuple)) and len(r) >= 2]
            if ra_x:
                ws_bks_c1[tk_x] = {"bids": rb_x, "asks": ra_x}
        cand_c1: Dict[str, Any] = {
            "box_id": f"COMPLETE_SET_FAST_{asset}_{hz_lbl}_{int(now_ts * 1000) % 1000000}",
            "dedupe_key": f"C1FAST_{mid_s}",
            "box_type": "COMPLETE_SET",
            "ts_unix": round(now_ts, 3),
            "asset": asset,
            "regime": f"COMPLETE_SET_UP_PLUS_DOWN_{hz_lbl}",
            "pair_horizons": "complete_set",
            "sleeve_source": "C1_BINARY_COMPLETE_SET",
            "recorder_fast_ipc": True,
            "is_quiet_book": True,
            "k_low": 0.0,
            "k_high": 0.0,
            "corridor_bps": 0.0,
            "expiry_ts": exp_f,
            "rem_sec": round(rem_s, 2),
            "shares": sh_pair,
            "net_paired_shares": float(sh_pair),
            "leg_a_gross_shares": gross_u,
            "leg_b_gross_shares": gross_d,
            "box_cost_net": net_cost,
            "max_box_cost_net": max_cap,
            "leg_a_token_id": tok_u,
            "leg_a_opp_token_id": tok_d,
            "leg_a_label": "UP",
            "leg_a_side": "UP",
            "leg_a_horizon": hz_lbl,
            "leg_a_market_id": mid_s,
            "leg_a_condition_id": cid_s,
            "leg_a_strike": 0.0,
            "leg_a_limit_price": ya,
            "leg_a_avail_shares": round(u_sz, 2),
            "leg_a_fee_rate": fr,
            "leg_a_fee_exponent": 1.0,
            "leg_a_neg_risk": False,
            "leg_a_expiry_ts": exp_f,
            "leg_b_token_id": tok_d,
            "leg_b_opp_token_id": tok_u,
            "leg_b_label": "DOWN",
            "leg_b_side": "DOWN",
            "leg_b_horizon": hz_lbl,
            "leg_b_market_id": mid_s,
            "leg_b_condition_id": cid_s,
            "leg_b_strike": 0.0,
            "leg_b_limit_price": na,
            "leg_b_avail_shares": round(d_sz, 2),
            "leg_b_fee_rate": fr,
            "leg_b_fee_exponent": 1.0,
            "leg_b_neg_risk": False,
            "leg_b_expiry_ts": exp_f,
            "ws_books": ws_bks_c1 if len(ws_bks_c1) == 2 else None,
            "ws_books_ts": round(now_ts, 3),
        }
        if isinstance(sink_list, list):
            sink_list.append(cand_c1)
            emitted += 1
            continue
        from pathlib import Path as _Path

        default_live_cp = _Path(__file__).resolve().parents[2] / "data" / "polymarket" / "d1_live_box_candidates.jsonl"
        custom_cp = getattr(recorder, "d1_live_candidates_file", None)
        live_cp = _Path(custom_cp) if custom_cp is not None else default_live_cp
        if _write_and_notify_live_cand(recorder, cand_c1, live_cp, live_cp):
            emitted += 1

    # 2. Sub-2ms Cross-Horizon D1 Same-Oracle Dominance IPC Sniper (15m vs 5m Crypto; 1h vs 15m Metals)
    try:
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as _GGM_D1

        _d1fast_en = bool(_GGM_D1.snapshot.get("riskless_boxes", {}).get("enable_recorder_d1fast_ipc", True))
        _d1_long_cap = float(_GGM_D1.snapshot.get("riskless_boxes", {}).get("d1_max_box_cost_net", 0.985) or 0.985)
        _d1_short_cap = float(_GGM_D1.snapshot.get("riskless_boxes", {}).get("d1_short_tte_max_box_cost_net", 0.9925) or 0.9925)
        _d1_short_thr = float(_GGM_D1.snapshot.get("riskless_boxes", {}).get("d1_short_tte_threshold_sec", 180.0) or 180.0)
    except Exception:
        _d1fast_en = True
        _d1_long_cap, _d1_short_cap, _d1_short_thr = 0.985, 0.9925, 180.0

    if _d1fast_en:
        min_corr_bps = 6.0 if asset == "ZEC" else (4.0 if asset in {"XAU", "XAG"} else (5.0 if asset in {"BNB", "DOGE", "HYPE"} else 3.0))
        hz_pairs: List[Tuple[str, Mapping[str, Any], Mapping[str, Any], float, str, Mapping[str, Any], Mapping[str, Any], float]] = []
        if asset in {"XAU", "XAG"}:
            m15_s, m15_r = snap.get("m15"), getattr(recorder, "market_15m", None)
            if isinstance(cm1h, Mapping) and isinstance(m15_s, Mapping) and isinstance(snap.get("UP"), Mapping) and isinstance(snap.get("DOWN"), Mapping):
                exp_1h_d = cm1h["end_dt"].timestamp() if "end_dt" in cm1h else float(snap.get("expiry_ts_1h") or 0.0)
                s1h_d = {
                    "market_id": cm1h.get("market_id"),
                    "condition_id": cm1h.get("condition_id"),
                    "expiry_ts": exp_1h_d,
                    "authoritative_chainlink_open": cm1h.get("authoritative_chainlink_open") or snap.get("authoritative_chainlink_open"),
                    "UP": snap["UP"],
                    "DOWN": snap["DOWN"],
                }
                hz_pairs.append(("1h", s1h_d, cm1h, 0.0, "15m", m15_s, m15_r or {}, 0.0))
        else:
            m15_s, m15_r = snap.get("m15"), getattr(recorder, "market_15m", None)
            m5_s, m5_r = snap.get("m5"), getattr(recorder, "market_5m", None)
            if isinstance(m15_s, Mapping) and isinstance(m5_s, Mapping):
                fr_15 = float((m15_r or {}).get("fee_metadata", {}).get("fee_rate_market", 0.072) if isinstance(m15_r, Mapping) else 0.072)
                fr_5 = float((m5_r or {}).get("fee_metadata", {}).get("fee_rate_market", 0.072) if isinstance(m5_r, Mapping) else 0.072)
                hz_pairs.append(("15m", m15_s, m15_r or {}, fr_15, "5m", m5_s, m5_r or {}, fr_5))

        for hz_l, sl_l, mr_l, fr_l_raw, hz_s, sl_s, mr_s, fr_s_raw in hz_pairs:
            exp_l = float(sl_l.get("expiry_ts") or mr_l.get("expiry_ts") or 0.0)
            exp_s = float(sl_s.get("expiry_ts") or mr_s.get("expiry_ts") or 0.0)
            rem_d1 = min(exp_l, exp_s) - now_ts
            if exp_l <= 0.0 or exp_s <= 0.0 or abs(exp_l - exp_s) > 2.0 or rem_d1 < 22.0:
                continue
            k_l = float(sl_l.get("authoritative_chainlink_open") or mr_l.get("authoritative_chainlink_open") or 0.0)
            k_s = float(sl_s.get("authoritative_chainlink_open") or mr_s.get("authoritative_chainlink_open") or 0.0)
            if k_l <= 0.0 or k_s <= 0.0 or k_l == k_s:
                continue
            k_low, k_high = (k_l, k_s) if k_l < k_s else (k_s, k_l)
            corr_bps = ((k_high - k_low) / k_low) * 10000.0
            if corr_bps < min_corr_bps:
                continue
            if k_l < k_s:
                # K_long < K_short -> BUY long UP (strike k_low) + BUY short DOWN (strike k_high)
                hz_a, sl_a, mr_a, fr_a_r, k_a = hz_l, sl_l, mr_l, fr_l_raw, k_l
                hz_b, sl_b, mr_b, fr_b_r, k_b = hz_s, sl_s, mr_s, fr_s_raw, k_s
                regime_d1 = f"CORRIDOR_{hz_l}_UP_{hz_s}_DOWN"
            else:
                # K_short < K_long -> BUY short UP (strike k_low) + BUY long DOWN (strike k_high)
                hz_a, sl_a, mr_a, fr_a_r, k_a = hz_s, sl_s, mr_s, fr_s_raw, k_s
                hz_b, sl_b, mr_b, fr_b_r, k_b = hz_l, sl_l, mr_l, fr_l_raw, k_l
                regime_d1 = f"CORRIDOR_{hz_s}_UP_{hz_l}_DOWN"
            mid_a = str(sl_a.get("market_id") or mr_a.get("market_id") or "")
            mid_b = str(sl_b.get("market_id") or mr_b.get("market_id") or "")
            cid_a = str(sl_a.get("condition_id") or mr_a.get("condition_id") or "")
            cid_b = str(sl_b.get("condition_id") or mr_b.get("condition_id") or "")
            cd_k_d1 = f"D1_{mid_a}_{mid_b}"
            if not mid_a or not mid_b or mid_a == mid_b or (now_ts - float(cd_map.get(cd_k_d1, 0.0) or 0.0)) < 2.0:
                continue
            bk_a = sl_a.get("UP")
            bk_b = sl_b.get("DOWN")
            opp_a = sl_a.get("DOWN")
            opp_b = sl_b.get("UP")
            if not isinstance(bk_a, Mapping) or not isinstance(bk_b, Mapping):
                continue
            tok_a = str(bk_a.get("token_id") or "")
            tok_b = str(bk_b.get("token_id") or "")
            opp_tok_a = str((opp_a or {}).get("token_id") or "") if isinstance(opp_a, Mapping) else ""
            opp_tok_b = str((opp_b or {}).get("token_id") or "") if isinstance(opp_b, Mapping) else ""
            if (
                not tok_a or not tok_b or tok_a == tok_b
                or bool(bk_a.get("is_crossed")) or bool(bk_b.get("is_crossed"))
                or float(bk_a.get("age_book_ms") if bk_a.get("age_book_ms") is not None else 9999.0) > 650.0
                or float(bk_b.get("age_book_ms") if bk_b.get("age_book_ms") is not None else 9999.0) > 650.0
            ):
                continue
            pa = float(bk_a.get("best_ask") or 0.0)
            pb = float(bk_b.get("best_ask") or 0.0)
            ba = float(bk_a.get("best_bid") or 0.0)
            bb = float(bk_b.get("best_bid") or 0.0)
            if (0.0 < ba and pa <= ba) or (0.0 < bb and pb <= bb):
                continue
            if not (0.01 <= pa <= 0.985 and 0.01 <= pb <= 0.985) or (pa + pb) > 0.9925:
                continue
            sz_a = float(bk_a.get("ask_size_l1") or 0.0)
            sz_b = float(bk_b.get("ask_size_l1") or 0.0)
            if min(sz_a, sz_b) < 8.0:
                continue
            fr_a = 0.0 if asset in {"XAU", "XAG"} else max(0.0, float(fr_a_r or 0.072))
            fr_b = 0.0 if asset in {"XAU", "XAG"} else max(0.0, float(fr_b_r or 0.072))
            ded_a = (fr_a * (1.0 - pa)) if (fr_a > 0.0 and 0.0 < pa < 1.0) else 0.0
            ded_b = (fr_b * (1.0 - pb)) if (fr_b > 0.0 and 0.0 < pb < 1.0) else 0.0
            if ded_a >= 0.50 or ded_b >= 0.50:
                continue
            net_cost_d1 = round((pa / (1.0 - ded_a)) + (pb / (1.0 - ded_b)), 5)
            max_cap_d1 = _d1_short_cap if rem_d1 <= _d1_short_thr else _d1_long_cap
            if net_cost_d1 > max_cap_d1:
                continue
            net_avail_d1 = min(sz_a * (1.0 - ded_a), sz_b * (1.0 - ded_b))
            if net_avail_d1 < 7.5:
                continue
            cd_map[cd_k_d1] = now_ts
            sh_d1 = max(5, min(30, int(math.floor(net_avail_d1 / 1.5))))
            gr_a = round(math.ceil((sh_d1 / (1.0 - ded_a)) * 100.0) / 100.0, 2)
            gr_b = round(math.ceil((sh_d1 / (1.0 - ded_b)) * 100.0) / 100.0, 2)
            ws_bks_d1 = {}
            for tk_x, sb_x in ((tok_a, bk_a), (tok_b, bk_b)):
                rb_x = [{"price": str(r[0]), "size": str(r[1])} for r in (sb_x.get("raw_top_bids") or [])[:10] if isinstance(r, (list, tuple)) and len(r) >= 2]
                ra_x = [{"price": str(r[0]), "size": str(r[1])} for r in (sb_x.get("raw_top_asks") or [])[:10] if isinstance(r, (list, tuple)) and len(r) >= 2]
                if ra_x:
                    ws_bks_d1[tk_x] = {"bids": rb_x, "asks": ra_x}
            cand_d1: Dict[str, Any] = {
                "box_id": f"DOMINANCE_FAST_{asset}_{hz_l}v{hz_s}_{int(now_ts * 1000) % 1000000}",
                "dedupe_key": f"D1FAST_{mid_a}_{mid_b}",
                "box_type": "DOMINANCE",
                "ts_unix": round(now_ts, 3),
                "asset": asset,
                "regime": regime_d1,
                "pair_horizons": f"{hz_l}_vs_{hz_s}",
                "sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "recorder_fast_ipc": True,
                "is_quiet_book": True,
                "k_low": k_low,
                "k_high": k_high,
                "corridor_bps": round(corr_bps, 3),
                "expiry_ts": min(exp_l, exp_s),
                "rem_sec": round(rem_d1, 2),
                "shares": sh_d1,
                "net_paired_shares": float(sh_d1),
                "leg_a_gross_shares": gr_a,
                "leg_b_gross_shares": gr_b,
                "box_cost_net": net_cost_d1,
                "max_box_cost_net": max_cap_d1,
                "leg_a_token_id": tok_a,
                "leg_a_opp_token_id": opp_tok_a,
                "leg_a_label": "UP",
                "leg_a_side": "UP",
                "leg_a_horizon": hz_a,
                "leg_a_market_id": mid_a,
                "leg_a_condition_id": cid_a,
                "leg_a_strike": k_a,
                "leg_a_limit_price": pa,
                "leg_a_avail_shares": round(sz_a, 2),
                "leg_a_fee_rate": fr_a,
                "leg_a_fee_exponent": 1.0,
                "leg_a_neg_risk": False,
                "leg_a_expiry_ts": min(exp_l, exp_s),
                "leg_b_token_id": tok_b,
                "leg_b_opp_token_id": opp_tok_b,
                "leg_b_label": "DOWN",
                "leg_b_side": "DOWN",
                "leg_b_horizon": hz_b,
                "leg_b_market_id": mid_b,
                "leg_b_condition_id": cid_b,
                "leg_b_strike": k_b,
                "leg_b_limit_price": pb,
                "leg_b_avail_shares": round(sz_b, 2),
                "leg_b_fee_rate": fr_b,
                "leg_b_fee_exponent": 1.0,
                "leg_b_neg_risk": False,
                "leg_b_expiry_ts": min(exp_l, exp_s),
                "ws_books": ws_bks_d1 if len(ws_bks_d1) == 2 else None,
                "ws_books_ts": round(now_ts, 3),
            }
            if isinstance(sink_list, list):
                sink_list.append(cand_d1)
                emitted += 1
                continue
            from pathlib import Path as _Path

            default_live_cp = _Path(__file__).resolve().parents[2] / "data" / "polymarket" / "d1_live_box_candidates.jsonl"
            custom_cp = getattr(recorder, "d1_live_candidates_file", None)
            live_cp = _Path(custom_cp) if custom_cp is not None else default_live_cp
            if _write_and_notify_live_cand(recorder, cand_d1, live_cp, live_cp):
                emitted += 1
    return emitted

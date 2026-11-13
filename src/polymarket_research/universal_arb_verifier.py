"""
Shared Mathematical Arbitrage Verification Engine & Depth-Aware L2 Execution Simulator
(`src/polymarket_research/universal_arb_verifier.py`).

Implements Sections 5 & 6 of DOMINUS — RISKLESS FULL THROTTLE:
  1. Exact State-Space Payoff Verification across all permitted contract states `omega in Omega`
     (including `50-50` void/cancellation/abandonment, regulation vs. overtime divergence,
     augmented-NegRisk `Other` & unnamed placeholder activation, conditional non-occurrence
     double-zero states, and UMA Optimistic Oracle dispute flip / lockup delay):
         NetPayoff(omega) = ContractPayout(omega, q) + CertainCashFlows
                            - AcquisitionCosts - Fees - ConversionCosts - SettlementCosts(omega)
  2. Exact Polymarket Protocol V2 & Fee-Curve Microstructure Math:
     - `0`-bps markets and parabolic fee-curve markets (`feeRateBps`, `rate * (p * (1 - p)) ** exp`)
     - Protocol V2 taker BUY outcome-share haircut (`h(p) = fee_ps(p) / p`, requiring `1 / (1 - h(p))`
       gross ask shares per `1.0` delivered net share) and cash-deducted taker SELL fee
     - Dynamic tick-size quantization (`0.001` at `p <= 0.04` or `p >= 0.96`, else `0.01` or explicit
       finer tick), per-instrument `min_order_size` (`>= 5` shares), `$1.00` marketable BUY notional
       floor, `NegRiskAdapter.getFeeBips` conversion fee, Polygon gas, and lockup opportunity cost.
  3. Depth-Aware Multi-Level L2 Execution Simulator:
     - Walks full multi-level L2 ask/bid ladders (never assuming unlimited top-of-book depth)
     - Computes exact piecewise-linear marginal worst-state profit `Delta NetPayoff_min / Delta q`
       across L2 rung breakpoints to determine the exact profit-maximizing executable clip `q*`
     - Tracks 4 strictly segregated economic values (`FourValueMetrics`):
       `theoretical_top_of_book_usd`, `executable_l2_net_usd`, `attainable_risk_adjusted_usd`,
       and `realized_net_usd` (`0.0` in Modes 1 & 2).
  4. Non-Overridable 5-Tier Classification (`CLASS_A` .. `CLASS_E`) + Deterministic SHA-256
     `ArbitrageProofObject` (never promoting `B`, `C`, or `D` into `CLASS_A`; strictly enforcing
     `D-001` frozen `KMIA` non-interference and `D-007` `< $500` NAV `>= 3`-leg CLOB quarantine).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

try:
    import orjson as _orjson  # type: ignore
except ImportError:  # pragma: no cover
    _orjson = None

_E6_SCALE: int = 1_000_000
_E8_SCALE: int = 100_000_000


# ---------------------------------------------------------------------------
# Safety Constants (`D-001`, `D-007`, Microstructure Floors)
# ---------------------------------------------------------------------------

FROZEN_DISPUTED_MARKET_IDS: frozenset[str] = frozenset({"6707503", "6707502"})
FROZEN_DISPUTED_TRADE_SUBSTRINGS: Tuple[str, ...] = (
    "WS_SNIPE_MIAMI_KMIA",
    "MULTI_LEG_BUNDLE_LIVE_KMIA",
)

DEFAULT_MIN_ORDER_SHARES: float = 5.0
DEFAULT_MIN_MARKETABLE_BUY_USD: float = 1.00
DEFAULT_MAX_BOOK_AGE_SEC: float = 120.0
DEFAULT_D007_MULTILEG_NAV_FLOOR_USD: float = 500.0
DEFAULT_LIVE_RECONCILED_NAV_USD: float = 48.70


class OpportunityClass(str, Enum):
    """Strict 5-tier DOMINUS arbitrage & opportunity classification."""

    CLASS_A = "CLASS_A"  # min_w NetPayoff(w) > 0 AND atomic or inventory-pre-locked
    CLASS_B = "CLASS_B"  # min_w NetPayoff(w) > 0 once constructed; sequential CLOB / lag exposure
    CLASS_C = "CLASS_C"  # E[NetPayoff] > 0, but min_w NetPayoff(w) <= 0 or passive maker exposure
    CLASS_D = "CLASS_D"  # Ambiguous/unverified rules, missing proof, or stale/crossed order book
    CLASS_E = "CLASS_E"  # Invalid, negative payoff (min <= 0 & EV <= 0), sub-lot depth, or disabled book


class ActionType(str, Enum):
    """Supported portfolio construction & settlement primitives."""

    BUY_CLOB = "BUY_CLOB"
    SELL_CLOB = "SELL_CLOB"
    USE_INVENTORY = "USE_INVENTORY"
    CTF_SPLIT = "CTF_SPLIT"
    CTF_MERGE = "CTF_MERGE"
    NEGRISK_CONVERT = "NEGRISK_CONVERT"


# ---------------------------------------------------------------------------
# Exact Polymarket Fee, Share-Haircut & Tick/Lot Rounding Primitives
# ---------------------------------------------------------------------------


def normalize_fee_rate(
    *,
    fee_rate_bps: Optional[float] = None,
    fee_rate: Optional[float] = None,
) -> float:
    """
    Normalizes either `fee_rate_bps` (e.g., `0.0`, `175.0`, `700.0`) or fractional `fee_rate`
    (e.g., `0.0`, `0.0175`, `0.07`) into fractional rate `r in [0.0, 0.50]`.
    If `fee_rate` is passed as `>= 1.0` (bps convention), converts automatically via `/ 10_000.0`.
    """
    if fee_rate_bps is not None:
        bps = max(0.0, float(fee_rate_bps))
        return min(0.50, bps / 10_000.0)
    if fee_rate is not None:
        fr = max(0.0, float(fee_rate))
        if fr >= 1.0:
            return min(0.50, fr / 10_000.0)
        return min(0.50, fr)
    return 0.0


def infer_polymarket_tick_size(price: float, explicit_tick_size: Optional[float] = None) -> float:
    """
    Polymarket dynamic tick-size rule:
      - `0.001` whenever `0 < price <= 0.04` or `price >= 0.96` (inclusive of `0.04` and `0.96`!),
        unless an explicit finer tick (`0.0001`) is configured on the market.
      - `0.01` on `0.04 < price < 0.96` unless explicit market `minimum_tick_size` is finer (`0.001`).
    """
    p = float(price or 0.0)
    in_tail_zone = (0.0 < p <= 0.04 + 1e-12) or (p >= 0.96 - 1e-12)
    auto_tick = 0.001 if in_tail_zone else 0.01
    if explicit_tick_size is not None and float(explicit_tick_size) > 0.0:
        exp_t = float(explicit_tick_size)
        return min(exp_t, 0.001) if in_tail_zone else exp_t
    return auto_tick


def quantize_polymarket_price(
    price: float,
    side: str = "BUY",
    *,
    explicit_tick_size: Optional[float] = None,
    is_maker: bool = False,
) -> Tuple[float, float]:
    """
    Quantizes `price` onto the valid Polymarket tick grid using exact `Decimal` arithmetic:
      - Taker BUY / Maker SELL: rounds UP (`ROUND_CEILING`) so limit crosses resting ask / sits conservatively.
      - Taker SELL / Maker BUY: rounds DOWN (`ROUND_FLOOR`) so limit hits resting bid / avoids accidental cross.
    Returns `(quantized_price, effective_tick_size)`.
    """
    p_clamped = min(0.9999, max(0.0001, float(price)))
    tick = infer_polymarket_tick_size(p_clamped, explicit_tick_size)
    side_u = str(side or "BUY").strip().upper()
    round_down = (side_u == "BUY" and is_maker) or (side_u == "SELL" and not is_maker)

    t_e8 = int(round(round(tick, 8) * _E8_SCALE))
    if t_e8 > 0 and abs(tick - (t_e8 / _E8_SCALE)) <= 1e-12:
        p_e8 = int(round(round(p_clamped, 8) * _E8_SCALE))
        steps_i = (p_e8 // t_e8) if round_down else ((p_e8 + t_e8 - 1) // t_e8)
        q_e8 = steps_i * t_e8
        max_e8 = _E8_SCALE - t_e8
        if q_e8 < t_e8:
            q_e8 = t_e8
        elif q_e8 > max_e8:
            q_e8 = max_e8
        return round(q_e8 / _E8_SCALE, 8), round(t_e8 / _E8_SCALE, 8)

    d_t = Decimal(str(tick))
    d_p = Decimal(str(round(p_clamped, 8)))
    mode = ROUND_FLOOR if round_down else ROUND_CEILING
    steps = (d_p / d_t).to_integral_value(rounding=mode)
    q_dec = steps * d_t
    min_px = d_t
    max_px = Decimal("1") - d_t
    if q_dec < min_px:
        q_dec = min_px
    elif q_dec > max_px:
        q_dec = max_px
    return float(q_dec), float(d_t)


def compute_polymarket_taker_fee_per_gross_share(
    price: float,
    *,
    fee_rate_bps: Optional[float] = None,
    fee_rate: Optional[float] = None,
    fee_exponent: float = 1.0,
    is_maker: bool = False,
) -> float:
    """
    Exact Polymarket nonlinear fee curve per `1.0` gross share at price `p in (0, 1)`:
        fee_ps(p) = r * (p * (1 - p)) ** exponent
    Returns `0.0` when `is_maker=True` (`postOnly` maker fee is `0%`) or `r == 0.0`.
    """
    if is_maker:
        return 0.0
    r = normalize_fee_rate(fee_rate_bps=fee_rate_bps, fee_rate=fee_rate)
    if r <= 0.0:
        return 0.0
    p = float(price)
    if p <= 0.0 or p >= 1.0:
        return 0.0
    exp = max(0.5, float(fee_exponent or 1.0))
    return max(0.0, r * ((p * (1.0 - p)) ** exp))


def compute_v2_buy_share_haircut_frac(
    price: float,
    *,
    fee_rate_bps: Optional[float] = None,
    fee_rate: Optional[float] = None,
    fee_exponent: float = 1.0,
    is_maker: bool = False,
) -> float:
    """
    Polymarket Protocol V2 (`ExchangeV3`) Taker BUY share haircut fraction `h(p) in [0.0, 0.50]`:
        h(p) = fee_ps(p) / p = r * ((p * (1 - p)) ** exp) / p
    Buying `g` gross shares on the ask at price `p` delivers `g * (1 - h(p))` net shares.
    """
    p = float(price)
    if is_maker or p <= 0.0 or p >= 1.0:
        return 0.0
    fee_ps = compute_polymarket_taker_fee_per_gross_share(
        p,
        fee_rate_bps=fee_rate_bps,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=False,
    )
    if fee_ps <= 0.0:
        return 0.0
    return min(0.50, max(0.0, fee_ps / p))


def compute_net_buy_cost_per_delivered_share(
    price: float,
    *,
    fee_rate_bps: Optional[float] = None,
    fee_rate: Optional[float] = None,
    fee_exponent: float = 1.0,
    is_maker: bool = False,
    fee_deduction_mode: str = "V2_SHARE_HAIRCUT",
) -> Tuple[float, float, float]:
    """
    Returns `(total_usdc_per_net_share, pure_price_usdc_per_net_share, fee_usdc_per_net_share)`
    to receive `1.0` net outcome share at rung price `p`:
      - `"V2_SHARE_HAIRCUT"` (default Polymarket Protocol V2): requires `1 / (1 - h(p))` gross shares,
        costing `p / (1 - h(p))` USDC (`pure_price = p`, `fee = p * h(p) / (1 - h(p))`).
      - `"USDC_ADDITIVE"`: legacy cash-additive `p + fee_ps(p)`.
    """
    p = min(0.9999, max(0.0001, float(price)))
    if str(fee_deduction_mode or "V2_SHARE_HAIRCUT").upper() == "USDC_ADDITIVE":
        fee_ps = compute_polymarket_taker_fee_per_gross_share(
            p,
            fee_rate_bps=fee_rate_bps,
            fee_rate=fee_rate,
            fee_exponent=fee_exponent,
            is_maker=is_maker,
        )
        return p + fee_ps, p, fee_ps

    h = compute_v2_buy_share_haircut_frac(
        p,
        fee_rate_bps=fee_rate_bps,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=is_maker,
    )
    if h <= 0.0:
        return p, p, 0.0
    total = p / max(0.50, 1.0 - h)
    return total, p, max(0.0, total - p)


def compute_net_sell_proceeds_per_share(
    price: float,
    *,
    fee_rate_bps: Optional[float] = None,
    fee_rate: Optional[float] = None,
    fee_exponent: float = 1.0,
    is_maker: bool = False,
) -> Tuple[float, float, float]:
    """
    Returns `(net_proceeds_per_share, gross_price_per_share, fee_usdc_per_share)` for selling `1.0` share.
    """
    p = min(0.9999, max(0.0001, float(price)))
    fee_ps = compute_polymarket_taker_fee_per_gross_share(
        p,
        fee_rate_bps=fee_rate_bps,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        is_maker=is_maker,
    )
    return max(0.0, p - fee_ps), p, fee_ps


def quantize_clob_fok_order(
    target_net_shares: float,
    limit_price: float,
    *,
    side: str = "BUY",
    fee_rate_bps: float = 0.0,
    fee_exponent: float = 1.0,
    explicit_tick_size: Optional[float] = None,
    min_order_size: float = DEFAULT_MIN_ORDER_SHARES,
    min_marketable_buy_usd: float = DEFAULT_MIN_MARKETABLE_BUY_USD,
) -> Dict[str, Any]:
    """
    Validates & quantizes a Polymarket CLOB FOK order onto tick/lot grids and 2-decimal USDC `makerAmount`.
    """
    side_u = str(side or "BUY").strip().upper()
    q_px, tick = quantize_polymarket_price(
        limit_price,
        side=side_u,
        explicit_tick_size=explicit_tick_size,
        is_maker=False,
    )
    min_sh = max(DEFAULT_MIN_ORDER_SHARES, float(min_order_size or DEFAULT_MIN_ORDER_SHARES))
    if target_net_shares <= 0.0:
        return {
            "valid": False,
            "reason": "NON_POSITIVE_SHARES",
            "quantized_price": q_px,
            "tick_size": tick,
            "gross_shares": 0.0,
            "delivered_net_shares": 0.0,
            "maker_amount_usd": 0.0,
        }

    if side_u == "BUY":
        h = compute_v2_buy_share_haircut_frac(q_px, fee_rate_bps=fee_rate_bps, fee_exponent=fee_exponent)
        req_gross = float(target_net_shares) / max(0.50, 1.0 - h)
        req_e6 = int(round(round(req_gross, 6) * _E6_SCALE))
        cand_e2 = (req_e6 + 9_999) // 10_000
        cand_gross = cand_e2 / 100.0
        raw_usdc_e6 = int(round(round(cand_gross * q_px, 6) * _E6_SCALE))
        if raw_usdc_e6 % 10_000 != 0:
            lot_step_int = 1 if abs(tick - 0.01) < 1e-9 else 10
            step_e6 = lot_step_int * _E6_SCALE
            cand_gross_int = ((req_e6 + step_e6 - 1) // step_e6) * lot_step_int
            cand_gross = float(cand_gross_int)
            q_px_e8 = int(round(round(q_px, 8) * _E8_SCALE))
            usdc_amt = ((cand_gross_int * q_px_e8 + 999_999) // 1_000_000) / 100.0
        else:
            usdc_amt = raw_usdc_e6 / _E6_SCALE
        delivered = cand_gross * max(0.50, 1.0 - h)
        min_sh_ok = cand_gross >= min_sh - 1e-9 and delivered >= min_sh - 1e-9
        notional_ok = usdc_amt >= float(min_marketable_buy_usd) - 1e-9
        reason = "OK" if (min_sh_ok and notional_ok) else (
            "BELOW_MIN_ORDER_SIZE" if not min_sh_ok else "BELOW_MIN_MARKETABLE_BUY_NOTIONAL_USD"
        )
        return {
            "valid": bool(min_sh_ok and notional_ok),
            "reason": reason,
            "quantized_price": q_px,
            "tick_size": tick,
            "gross_shares": round(cand_gross, 4),
            "delivered_net_shares": round(delivered, 6),
            "maker_amount_usd": round(usdc_amt, 2),
        }

    sell_e6 = int(round(round(float(target_net_shares), 6) * _E6_SCALE))
    cand_sell = (sell_e6 // 10_000) / 100.0
    gross_proceeds = round(cand_sell * q_px, 6)
    min_sh_ok = cand_sell >= min_sh - 1e-9
    return {
        "valid": bool(min_sh_ok),
        "reason": "OK" if min_sh_ok else "BELOW_MIN_ORDER_SIZE",
        "quantized_price": q_px,
        "tick_size": tick,
        "gross_shares": round(cand_sell, 4),
        "delivered_net_shares": round(cand_sell, 4),
        "maker_amount_usd": round(gross_proceeds, 2),
    }


# ---------------------------------------------------------------------------
# Data Models: Order Books, Inventory, Actions, States & Proof Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BookLevel:
    price: float
    size: float


@dataclass(frozen=True)
class InstrumentOrderBook:
    """L2 order book & microstructure metadata for a single tradable CTF outcome token."""

    instrument_id: str
    market_id: str = ""
    condition_id: str = ""
    outcome_label: str = ""
    asks: Tuple[BookLevel, ...] = ()
    bids: Tuple[BookLevel, ...] = ()
    fee_rate_bps: float = 0.0
    fee_exponent: float = 1.0
    tick_size: Optional[float] = None
    min_order_size: float = DEFAULT_MIN_ORDER_SHARES
    enable_order_book: bool = True
    book_timestamp_sec: Optional[float] = None
    is_placeholder: bool = False
    is_other: bool = False

    @classmethod
    def from_raw(
        cls,
        instrument_id: str,
        raw_book: Optional[Mapping[str, Any]] = None,
        *,
        market_id: str = "",
        condition_id: str = "",
        outcome_label: str = "",
        fee_rate_bps: Optional[float] = None,
        fee_rate: Optional[float] = None,
        fee_exponent: float = 1.0,
        tick_size: Optional[float] = None,
        min_order_size: Optional[float] = None,
        enable_order_book: bool = True,
        book_timestamp_sec: Optional[float] = None,
        is_placeholder: bool = False,
        is_other: bool = False,
    ) -> "InstrumentOrderBook":
        bk = raw_book if isinstance(raw_book, Mapping) else {}

        def _parse_side(items: Any, desc: bool) -> Tuple[BookLevel, ...]:
            out: List[BookLevel] = []
            for lv in items or ():
                try:
                    if isinstance(lv, BookLevel):
                        p, s = float(lv.price), float(lv.size)
                    elif isinstance(lv, Mapping):
                        p = float(lv.get("price") or 0.0)
                        s = float(lv.get("size") or lv.get("amount") or 0.0)
                    elif isinstance(lv, (list, tuple)) and len(lv) >= 2:
                        p, s = float(lv[0]), float(lv[1])
                    else:
                        continue
                    if 0.0 < p < 1.0 and s > 0.0 and math.isfinite(p) and math.isfinite(s):
                        out.append(BookLevel(round(p, 6), round(s, 6)))
                except (TypeError, ValueError):
                    continue
            out.sort(key=lambda x: x.price, reverse=desc)
            return tuple(out)

        eff_bps = (
            float(fee_rate_bps)
            if fee_rate_bps is not None
            else (normalize_fee_rate(fee_rate=fee_rate) * 10_000.0 if fee_rate is not None else float(bk.get("fee_rate_bps") or 0.0))
        )
        eff_min_sz = float(
            min_order_size
            if min_order_size is not None
            else (bk.get("min_order_size") or bk.get("minimum_order_size") or DEFAULT_MIN_ORDER_SHARES)
        )
        eff_tick = tick_size if tick_size is not None else bk.get("tick_size") or bk.get("minimum_tick_size")
        eff_tick_f = float(eff_tick) if eff_tick is not None and float(eff_tick or 0.0) > 0.0 else None
        ts_raw = book_timestamp_sec if book_timestamp_sec is not None else bk.get("timestamp_sec") or bk.get("timestamp")
        ts_sec: Optional[float] = None
        if ts_raw is not None:
            try:
                tf = float(ts_raw)
                if tf > 1e11:
                    tf = tf / 1000.0
                if tf > 0.0:
                    ts_sec = tf
            except (TypeError, ValueError):
                ts_sec = None

        return cls(
            instrument_id=str(instrument_id or "").strip(),
            market_id=str(market_id or bk.get("market") or bk.get("market_id") or "").strip(),
            condition_id=str(condition_id or bk.get("asset_id_condition") or bk.get("condition_id") or "").strip(),
            outcome_label=str(outcome_label or "").strip(),
            asks=_parse_side(bk.get("asks"), desc=False),
            bids=_parse_side(bk.get("bids"), desc=True),
            fee_rate_bps=max(0.0, eff_bps),
            fee_exponent=max(0.5, float(fee_exponent or 1.0)),
            tick_size=eff_tick_f,
            min_order_size=max(DEFAULT_MIN_ORDER_SHARES, eff_min_sz),
            enable_order_book=bool(enable_order_book and bk.get("enableOrderBook", True) is not False),
            book_timestamp_sec=ts_sec,
            is_placeholder=bool(is_placeholder),
            is_other=bool(is_other),
        )

    def has_crossed_or_invalid_book(self) -> bool:
        for lv in (*self.asks, *self.bids):
            if not (0.0 < lv.price < 1.0) or lv.size <= 0.0:
                return True
        if self.asks and self.bids and self.bids[0].price >= self.asks[0].price - 1e-9:
            return True
        return False


@dataclass(frozen=True)
class InventoryHolding:
    """Existing wallet CTF token position (with automatic `D-001` frozen `KMIA` protection)."""

    instrument_id: str
    shares: float
    market_id: str = ""
    condition_id: str = ""
    trade_id: str = ""
    cost_basis_per_share: float = 0.0
    mark_bid_per_share: Optional[float] = None
    uma_resolution_status: str = ""
    is_frozen_disputed: bool = False

    def is_d001_protected(self) -> bool:
        if self.is_frozen_disputed:
            return True
        if str(self.uma_resolution_status or "").strip().lower() == "disputed":
            return True
        if str(self.market_id or "").strip() in FROZEN_DISPUTED_MARKET_IDS:
            return True
        tid_u = str(self.trade_id or "").strip().upper()
        return any(sub in tid_u for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS)


@dataclass(frozen=True)
class ActionLeg:
    """
    A single component of candidate position/action vector `q`:
      - `BUY_CLOB`: acquires `weight * q` net delivered shares of `instrument_id` on CLOB asks (or passive bid if `is_maker=True`).
      - `SELL_CLOB`: sells `weight * q` shares of `instrument_id` into CLOB bids (or passive ask if `is_maker=True`).
      - `USE_INVENTORY`: commits `weight * q` pre-held shares of `instrument_id` from `InventoryHolding`.
      - `CTF_SPLIT`: spends `$1.00 * weight * q` collateral to mint `weight * q` shares of each ID in `related_instrument_ids`.
      - `CTF_MERGE`: burns `weight * q` shares of each ID in `related_instrument_ids` for `+$1.00 * weight * q` immediate cash.
      - `NEGRISK_CONVERT`: burns `weight * q` shares of each `NO` ID in `burned_no_instrument_ids` (`|S| = m`),
        yielding `(m - 1) * (1 - c) * weight * q` cash + `(1 - c) * weight * q` shares of each `YES` ID in
        `minted_yes_instrument_ids`, where `c = negrisk_fee_bips / 10_000`.
    """

    action_type: ActionType
    instrument_id: str = ""
    weight: float = 1.0
    is_maker: bool = False
    maker_price: Optional[float] = None
    max_slippage_price: Optional[float] = None
    related_instrument_ids: Tuple[str, ...] = ()
    burned_no_instrument_ids: Tuple[str, ...] = ()
    minted_yes_instrument_ids: Tuple[str, ...] = ()
    negrisk_fee_bips: int = 0
    gas_cost_usd: float = 0.0
    market_id: str = ""
    label: str = ""


@dataclass(frozen=True)
class StateSpec:
    """
    A single permitted contract resolution state `omega in Omega`.
    `instrument_payouts` maps `instrument_id -> payout per share in [0.0, 1.0]`
    (supporting `1.0` winner, `0.0` loser, `0.5` `50-50` void/cancellation, or scalar payout).
    """

    state_id: str
    instrument_payouts: Mapping[str, float]
    probability: Optional[float] = None
    lockup_hours_override: Optional[float] = None
    extra_settlement_cost_usd: float = 0.0
    is_edge_or_void_state: bool = False
    description: str = ""


@dataclass(frozen=True)
class CandidateStructure:
    """Complete specification of a candidate arbitrage or relative-value structure to verify & simulate."""

    candidate_id: str
    family: str
    legs: Tuple[ActionLeg, ...]
    states: Tuple[StateSpec, ...]
    rule_verified: bool = True
    rule_disqualifiers: Tuple[str, ...] = ()
    is_exhaustive_partition: bool = True
    is_mutually_exclusive: bool = True
    requires_exhaustive_partition: bool = False
    has_augmented_placeholder_risk: bool = False
    has_mutable_other_exposure: bool = False
    is_statistical_or_cross_oracle_only: bool = False
    uma_proposal_unfinalized: bool = False
    expected_lockup_hours: float = 2.0
    worst_case_lockup_hours: float = 2.0
    unverified_rebate_or_reward_usd_per_unit: float = 0.0
    notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationConfig:
    """Execution, fee, gas, latency & governance parameters for the verification engine."""

    max_budget_usd: float = 100.0
    reconciled_nav_usd: float = DEFAULT_LIVE_RECONCILED_NAV_USD
    d007_multileg_nav_floor_usd: float = DEFAULT_D007_MULTILEG_NAV_FLOOR_USD
    now_ts: Optional[float] = None
    max_book_age_sec: float = DEFAULT_MAX_BOOK_AGE_SEC
    enforce_min_marketable_notional: bool = True
    min_marketable_buy_usd: float = DEFAULT_MIN_MARKETABLE_BUY_USD
    fee_deduction_mode: str = "V2_SHARE_HAIRCUT"
    default_relayer_gas_usd: float = 0.0
    settlement_gas_usd: float = 0.0
    lockup_opportunity_cost_bps_per_hour: float = 0.0
    wire_rtt_ms: float = 72.39
    per_leg_fill_survival_decay: float = 0.92
    passive_maker_fill_prob: float = 0.30
    lot_step_shares: float = 0.01
    execution_mode: str = "MODE_2_SHADOW"  # "MODE_1_RESEARCH" | "MODE_2_SHADOW"


@dataclass(frozen=True)
class SimulatedLegExecution:
    leg_index: int
    action_type: str
    instrument_id: str
    is_maker: bool
    target_net_shares: float
    gross_shares: float
    filled_net_shares: float
    l1_price: float
    l1_available_shares: float
    vwap_price: float
    worst_limit_price: float
    tick_size: float
    acquisition_or_gross_usd: float
    taker_fee_usd: float
    rungs_walked: int
    min_order_ok: bool
    notional_ok: bool
    status: str


@dataclass(frozen=True)
class StatePayoffBreakdown:
    state_id: str
    probability: float
    contract_payout_usd: float
    certain_cash_flows_usd: float
    acquisition_costs_usd: float
    fees_usd: float
    conversion_costs_usd: float
    settlement_costs_usd: float
    net_payoff_usd: float
    is_edge_or_void_state: bool = False


@dataclass(frozen=True)
class CostBreakdown:
    acquisition_costs_usd: float
    taker_fees_usd: float
    conversion_costs_usd: float
    gas_costs_usd: float
    lockup_capital_cost_usd: float
    settlement_costs_usd: float
    certain_cash_flows_usd: float
    capital_required_usd: float
    expected_lockup_hours: float
    worst_case_lockup_hours: float


@dataclass(frozen=True)
class FourValueMetrics:
    """
    Strictly segregated 4-tier economic metrics:
      1. `theoretical_top_of_book_usd`: Unlimited-L1 top-of-book theoretical net profit at `q_ref`
      2. `executable_l2_net_usd`: Depth-walked, fee-haircut, quantized L2 net profit at `q*`
      3. `attainable_risk_adjusted_usd`: Post-latency fill-survival & sequential leg-out adjusted EV
      4. `realized_net_usd`: Strictly `0.0` in Modes 1 & 2 (never mixed with wallet cash)
    """

    theoretical_top_of_book_usd: float
    executable_l2_net_usd: float
    attainable_risk_adjusted_usd: float
    realized_net_usd: float = 0.0


@dataclass(frozen=True)
class ArbitrageProofObject:
    """Deterministic, SHA-256-attested verification proof & L2 simulation record."""

    candidate_id: str
    family: str
    opportunity_class: str
    is_mathematically_proven_arb: bool
    is_atomic_or_prelocked: bool
    d007_sub500_multileg_quarantine: bool
    execution_mode_cap: str
    optimal_executable_quantity: float
    gross_top_of_book_edge_per_unit: float
    net_executable_edge_per_unit: float
    min_state_net_payoff_usd: float
    max_state_net_payoff_usd: float
    expected_net_payoff_usd: float
    worst_state_id: str
    capital_efficiency_bps_per_hr: float
    four_value_ledger: FourValueMetrics
    cost_breakdown: CostBreakdown
    state_payoffs: Tuple[StatePayoffBreakdown, ...]
    leg_executions: Tuple[SimulatedLegExecution, ...]
    counterexample_states: Tuple[str, ...]
    disqualifiers: Tuple[str, ...]
    residual_risks: Tuple[str, ...]
    proof_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# State-Space Builders (`StateSpaceBuilder`) for Families A .. N
# ---------------------------------------------------------------------------


class StateSpaceBuilder:
    """Constructs exhaustive contract state spaces `Omega` with explicit edge/void/dispute states."""

    @staticmethod
    def binary_complete_set_states(
        yes_instrument_id: str,
        no_instrument_id: str,
        *,
        include_void_50_50: bool = True,
        prob_yes: float = 0.495,
        prob_void: float = 0.01,
    ) -> Tuple[StateSpec, ...]:
        yid = str(yes_instrument_id).strip()
        nid = str(no_instrument_id).strip()
        pv = max(0.0, min(0.20, float(prob_void))) if include_void_50_50 else 0.0
        rem = 1.0 - pv
        py = max(0.0, min(rem, float(prob_yes)))
        pn = max(0.0, rem - py)
        states: List[StateSpec] = [
            StateSpec(
                state_id="OMEGA_YES_WINS",
                instrument_payouts={yid: 1.0, nid: 0.0},
                probability=round(py, 6),
                description="Standard binary YES resolution ($1.00 YES, $0.00 NO)",
            ),
            StateSpec(
                state_id="OMEGA_NO_WINS",
                instrument_payouts={yid: 0.0, nid: 1.0},
                probability=round(pn, 6),
                description="Standard binary NO resolution ($0.00 YES, $1.00 NO)",
            ),
        ]
        if include_void_50_50:
            states.append(
                StateSpec(
                    state_id="OMEGA_VOID_50_50",
                    instrument_payouts={yid: 0.5, nid: 0.5},
                    probability=round(pv, 6),
                    is_edge_or_void_state=True,
                    description="Fractional 50-50 cancellation/void settlement ($0.50 YES, $0.50 NO)",
                )
            )
        return tuple(states)

    @staticmethod
    def multi_outcome_partition_states(
        outcomes: Sequence[Mapping[str, Any]],
        *,
        is_mutually_exclusive: bool = True,
        is_exhaustive: bool = True,
        is_negrisk: bool = False,
        is_augmented_negrisk: bool = False,
        has_unnamed_placeholder: bool = False,
        has_other_outcome: bool = False,
        conditional_without_catchall: bool = False,
        include_void_50_50_if_standalone: bool = True,
    ) -> Tuple[StateSpec, ...]:
        """
        Builds `Omega` for N-outcome slates (Families B & C):
          - Standard winner states `OMEGA_OUTCOME_i` for `i = 0..N-1`.
          - Injects `OMEGA_UNLISTED_OR_NO_OCCURRENCE` (`all YES_i = 0, all NO_i = 1`) whenever
            `not is_exhaustive` or `conditional_without_catchall` or (`is_augmented_negrisk` and not `has_other_outcome`).
          - Injects `OMEGA_PLACEHOLDER_ACTIVATED` (`all named YES_i = 0, NO_i = 1`) when `has_unnamed_placeholder`.
          - Injects `OMEGA_MULTI_WINNER_OVERLAP` (`YES_0 = 1, YES_1 = 1`) when `not is_mutually_exclusive`.
          - Injects `OMEGA_STANDALONE_VOID_50_50` (`YES_i = 0.5, NO_i = 0.5`) when `not is_negrisk`
            and `include_void_50_50_if_standalone=True` (catches standalone multi-NO cancellation losses!).
        """
        n = len(outcomes)
        if n == 0:
            return ()

        yes_ids = [str(o.get("yes_token_id") or o.get("yes_instrument_id") or f"YES_{k}").strip() for k, o in enumerate(outcomes)]
        no_ids = [str(o.get("no_token_id") or o.get("no_instrument_id") or f"NO_{k}").strip() for k, o in enumerate(outcomes)]
        labels = [str(o.get("label") or o.get("outcome") or f"idx_{k}").strip() for k, o in enumerate(outcomes)]

        states: List[StateSpec] = []
        for win_idx in range(n):
            payouts: Dict[str, float] = {}
            for j in range(n):
                is_w = j == win_idx
                if yes_ids[j]:
                    payouts[yes_ids[j]] = 1.0 if is_w else 0.0
                if no_ids[j]:
                    payouts[no_ids[j]] = 0.0 if is_w else 1.0
            states.append(
                StateSpec(
                    state_id=f"OMEGA_WIN_{win_idx}_{labels[win_idx][:24]}",
                    instrument_payouts=payouts,
                    description=f"Outcome {win_idx} ({labels[win_idx]}) resolves YES=$1.00; all others NO=$1.00",
                )
            )

        if not is_exhaustive or conditional_without_catchall or (is_augmented_negrisk and not has_other_outcome):
            unlisted_pay: Dict[str, float] = {}
            for j in range(n):
                if yes_ids[j]:
                    unlisted_pay[yes_ids[j]] = 0.0
                if no_ids[j]:
                    unlisted_pay[no_ids[j]] = 1.0
            states.append(
                StateSpec(
                    state_id="OMEGA_UNLISTED_OR_NO_OCCURRENCE_DOUBLE_ZERO",
                    instrument_payouts=unlisted_pay,
                    is_edge_or_void_state=True,
                    description="Unlisted candidate wins or conditional event does not occur: all listed YES=$0.00",
                )
            )

        if has_unnamed_placeholder:
            ph_pay: Dict[str, float] = {}
            for j in range(n):
                is_ph = bool(outcomes[j].get("is_placeholder") or outcomes[j].get("isPlaceholder"))
                if yes_ids[j]:
                    ph_pay[yes_ids[j]] = 1.0 if is_ph else 0.0
                if no_ids[j]:
                    ph_pay[no_ids[j]] = 0.0 if is_ph else 1.0
            if all(ph_pay.get(yid, 0.0) == 0.0 for yid in yes_ids if yid):
                for j in range(n):
                    if yes_ids[j]:
                        ph_pay[yes_ids[j]] = 0.0
                    if no_ids[j]:
                        ph_pay[no_ids[j]] = 1.0
            states.append(
                StateSpec(
                    state_id="OMEGA_AUGMENTED_PLACEHOLDER_ACTIVATED",
                    instrument_payouts=ph_pay,
                    is_edge_or_void_state=True,
                    description="Unnamed augmented NegRisk placeholder slot is clarified and wins: named YES=$0.00",
                )
            )

        if not is_mutually_exclusive and n >= 2:
            overlap_pay: Dict[str, float] = {}
            for j in range(n):
                hit = j in (0, 1)
                if yes_ids[j]:
                    overlap_pay[yes_ids[j]] = 1.0 if hit else 0.0
                if no_ids[j]:
                    overlap_pay[no_ids[j]] = 0.0 if hit else 1.0
            states.append(
                StateSpec(
                    state_id="OMEGA_MULTI_WINNER_OVERLAP",
                    instrument_payouts=overlap_pay,
                    is_edge_or_void_state=True,
                    description="Non-mutually-exclusive scalar/candidate overlap: multiple outcomes resolve YES=$1.00",
                )
            )

        if not is_negrisk and include_void_50_50_if_standalone:
            void_pay: Dict[str, float] = {}
            for j in range(n):
                if yes_ids[j]:
                    void_pay[yes_ids[j]] = 0.5
                if no_ids[j]:
                    void_pay[no_ids[j]] = 0.5
            states.append(
                StateSpec(
                    state_id="OMEGA_STANDALONE_VOID_50_50",
                    instrument_payouts=void_pay,
                    is_edge_or_void_state=True,
                    description="Standalone event cancellation/postponement resolving each binary 50-50 ($0.50)",
                )
            )

        uniform_p = round(1.0 / len(states), 6)
        return tuple(
            StateSpec(
                state_id=s.state_id,
                instrument_payouts=s.instrument_payouts,
                probability=s.probability if s.probability is not None else uniform_p,
                lockup_hours_override=s.lockup_hours_override,
                extra_settlement_cost_usd=s.extra_settlement_cost_usd,
                is_edge_or_void_state=s.is_edge_or_void_state,
                description=s.description,
            )
            for s in states
        )

    @staticmethod
    def two_market_logical_states(
        yes_a: str,
        no_a: str,
        yes_b: str,
        no_b: str,
        *,
        relation: str = "A_IMPLIES_B",
        cancel_rule_a: str = "50_50",
        cancel_rule_b: str = "50_50",
        has_overtime_mismatch: bool = False,
        touch_vs_close_mismatch: bool = False,
        timezone_mismatch: bool = False,
        oracle_mismatch: bool = False,
    ) -> Tuple[StateSpec, ...]:
        """
        Builds `Omega` for 2-market logical / deadline / strike / sports / duplicate pairs (`Families D..I`):
          - `A_IMPLIES_B`: `(1,1), (0,1), (0,0)` (so `NO_A + YES_B` pays `$1, $2, $1`, whereas converse
            `YES_A + NO_B` pays `$0` in `(0,1)`!).
          - `B_IMPLIES_A`: `(1,1), (1,0), (0,0)`.
          - `MUTUAL_EXCLUSION` (`A perp B`): `(1,0), (0,1), (0,0)` (so `NO_A + NO_B` pays `$1, $1, $2`).
          - `EQUIVALENT` (`A <=> B`): `(1,1), (0,0)`.
          - Automatically injects mismatch counterexample states (`(1,0)` / `(0,1)`) if overtime, touch-vs-close,
            timezone, or oracle mismatches exist, plus exact `cancel_rule_a` vs `cancel_rule_b` void state!
        """
        rel_u = str(relation or "A_IMPLIES_B").strip().upper()
        base_pairs: List[Tuple[str, float, float]] = []
        if rel_u == "A_IMPLIES_B":
            base_pairs = [("OMEGA_A1_B1", 1.0, 1.0), ("OMEGA_A0_B1", 0.0, 1.0), ("OMEGA_A0_B0", 0.0, 0.0)]
        elif rel_u == "B_IMPLIES_A":
            base_pairs = [("OMEGA_A1_B1", 1.0, 1.0), ("OMEGA_A1_B0", 1.0, 0.0), ("OMEGA_A0_B0", 0.0, 0.0)]
        elif rel_u in {"MUTUAL_EXCLUSION", "DISJOINT"}:
            base_pairs = [("OMEGA_A1_B0", 1.0, 0.0), ("OMEGA_A0_B1", 0.0, 1.0), ("OMEGA_A0_B0", 0.0, 0.0)]
        elif rel_u in {"EQUIVALENT", "DUPLICATE"}:
            base_pairs = [("OMEGA_A1_B1", 1.0, 1.0), ("OMEGA_A0_B0", 0.0, 0.0)]
        else:
            # Unconstrained Cartesian product `(1,1),(1,0),(0,1),(0,0)`
            base_pairs = [
                ("OMEGA_A1_B1", 1.0, 1.0),
                ("OMEGA_A1_B0", 1.0, 0.0),
                ("OMEGA_A0_B1", 0.0, 1.0),
                ("OMEGA_A0_B0", 0.0, 0.0),
            ]

        states: List[StateSpec] = []
        for sid, va, vb in base_pairs:
            pay = {}
            if yes_a:
                pay[yes_a] = va
            if no_a:
                pay[no_a] = 1.0 - va
            if yes_b:
                pay[yes_b] = vb
            if no_b:
                pay[no_b] = 1.0 - vb
            states.append(StateSpec(state_id=sid, instrument_payouts=pay))

        def _cancel_val(rule: str) -> Tuple[float, float]:
            ru = str(rule or "50_50").strip().upper()
            if ru == "50_50":
                return 0.5, 0.5
            if ru in {"NEGRISK_NO", "RESOLVE_NO", "ZERO_YES"}:
                return 0.0, 1.0
            if ru in {"NEGRISK_YES", "RESOLVE_YES"}:
                return 1.0, 0.0
            return 0.5, 0.5

        cya, cna = _cancel_val(cancel_rule_a)
        cyb, cnb = _cancel_val(cancel_rule_b)
        void_pay: Dict[str, float] = {}
        if yes_a:
            void_pay[yes_a] = cya
        if no_a:
            void_pay[no_a] = cna
        if yes_b:
            void_pay[yes_b] = cyb
        if no_b:
            void_pay[no_b] = cnb
        states.append(
            StateSpec(
                state_id=f"OMEGA_VOID_CANCEL_{cancel_rule_a}_{cancel_rule_b}",
                instrument_payouts=void_pay,
                is_edge_or_void_state=True,
                description=f"Cancellation/void/abandonment state ({cancel_rule_a} vs {cancel_rule_b})",
            )
        )

        mismatch_reasons: List[Tuple[str, float, float]] = []
        if has_overtime_mismatch:
            mismatch_reasons.extend([("OMEGA_OVERTIME_MISMATCH_A1_B0", 1.0, 0.0), ("OMEGA_OVERTIME_MISMATCH_A0_B1", 0.0, 1.0)])
        if touch_vs_close_mismatch:
            mismatch_reasons.extend([("OMEGA_TOUCH_VS_CLOSE_SPIKE_A1_B0", 1.0, 0.0), ("OMEGA_TOUCH_VS_CLOSE_SPIKE_A0_B1", 0.0, 1.0)])
        if timezone_mismatch:
            mismatch_reasons.extend([("OMEGA_TIMEZONE_CUTOFF_SLIP_A1_B0", 1.0, 0.0), ("OMEGA_TIMEZONE_CUTOFF_SLIP_A0_B1", 0.0, 1.0)])
        if oracle_mismatch:
            mismatch_reasons.extend([("OMEGA_CROSS_ORACLE_BASIS_TRAP_A1_B0", 1.0, 0.0), ("OMEGA_CROSS_ORACLE_BASIS_TRAP_A0_B1", 0.0, 1.0)])

        for m_sid, va, vb in mismatch_reasons:
            mp: Dict[str, float] = {}
            if yes_a:
                mp[yes_a] = va
            if no_a:
                mp[no_a] = 1.0 - va
            if yes_b:
                mp[yes_b] = vb
            if no_b:
                mp[no_b] = 1.0 - vb
            states.append(
                StateSpec(
                    state_id=m_sid,
                    instrument_payouts=mp,
                    is_edge_or_void_state=True,
                    description=f"Rule divergence counterexample state: {m_sid}",
                )
            )

        p_unif = round(1.0 / len(states), 6)
        return tuple(
            StateSpec(
                state_id=s.state_id,
                instrument_payouts=s.instrument_payouts,
                probability=p_unif,
                is_edge_or_void_state=s.is_edge_or_void_state,
                description=s.description,
            )
            for s in states
        )

    @staticmethod
    def uma_carry_states(
        instrument_id: str,
        *,
        uma_status: str = "proposed",
        p_dispute_flip: float = 0.02,
        expected_lockup_hours: float = 2.0,
        dispute_lockup_hours: float = 168.0,
    ) -> Tuple[StateSpec, ...]:
        """
        Models Family K near-resolution / UMA Optimistic Oracle carry:
        Unless `uma_status == 'resolved_onchain_final'`, an unfinalized proposal can still be disputed
        (as occurred in the Nov 7 `KMIA` ASOS incident!), so `OMEGA_UMA_DISPUTE_FLIP` (`payout=0.0`,
        `lockup_hours=dispute_lockup_hours`) is ALWAYS included in `Omega`, forcing `min_w < 0` (`CLASS_C`).
        """
        tok = str(instrument_id).strip()
        st_l = str(uma_status or "proposed").strip().lower()
        if st_l == "resolved_onchain_final":
            return (
                StateSpec(
                    state_id="OMEGA_ONCHAIN_PAYOUT_FINALIZED",
                    instrument_payouts={tok: 1.0},
                    probability=1.0,
                    lockup_hours_override=0.05,
                    description="On-chain CTF payoutNumerators finalized",
                ),
            )
        pf = min(0.99, max(0.001, float(p_dispute_flip)))
        return (
            StateSpec(
                state_id="OMEGA_UMA_PROPOSAL_AFFIRMED",
                instrument_payouts={tok: 1.0},
                probability=round(1.0 - pf, 6),
                lockup_hours_override=max(0.05, float(expected_lockup_hours)),
                description="UMA Optimistic Oracle liveness expires undisputed; share redeems at $1.00",
            ),
            StateSpec(
                state_id="OMEGA_UMA_DISPUTE_DVM_FLIP_OR_VOID",
                instrument_payouts={tok: 0.0},
                probability=round(pf, 6),
                lockup_hours_override=max(24.0, float(dispute_lockup_hours)),
                is_edge_or_void_state=True,
                description="UMA proposal disputed to DVM and flipped to $0.00 after multi-day lockup",
            ),
        )


# ---------------------------------------------------------------------------
# Depth-Aware L2 Execution Simulator & Universal Arbitrage Verifier
# ---------------------------------------------------------------------------


class UniversalArbVerifier:
    """
    Shared mathematical arbitrage verification & L2 execution simulation engine (`Sections 5 & 6`).
    """

    def __init__(self, config: Optional[VerificationConfig] = None) -> None:
        self.config = config or VerificationConfig()

    @staticmethod
    def _compute_canonical_sha256(payload: Mapping[str, Any]) -> str:
        if _orjson is not None:
            try:
                raw_b = _orjson.dumps(
                    payload if isinstance(payload, dict) else dict(payload),
                    option=_orjson.OPT_SORT_KEYS,
                )
                return hashlib.sha256(raw_b).hexdigest()
            except Exception:
                pass
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    @staticmethod
    def _walk_ask_ladder_exact(
        book: InstrumentOrderBook,
        target_net_shares: float,
        *,
        fee_deduction_mode: str = "V2_SHARE_HAIRCUT",
        max_price: Optional[float] = None,
    ) -> Optional[Tuple[float, float, float, float, float, int]]:
        """
        Walks multi-level L2 asks to deliver `target_net_shares` net outcome shares.
        Returns `(gross_shares, acquisition_price_usd, taker_fee_usd, vwap_gross_px, worst_px, rungs_walked)`
        or `None` if insufficient resting ask depth exists.
        """
        if target_net_shares <= 0.0:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0)
        rem_net = float(target_net_shares)
        tot_gross = 0.0
        tot_acq_usd = 0.0
        tot_fee_usd = 0.0
        worst_px = 0.0
        rungs = 0

        for lv in book.asks:
            if max_price is not None and lv.price > float(max_price) + 1e-9:
                break
            q_px, _ = quantize_polymarket_price(
                lv.price,
                "BUY",
                explicit_tick_size=book.tick_size,
                is_maker=False,
            )
            tot_ps, pure_ps, fee_ps = compute_net_buy_cost_per_delivered_share(
                q_px,
                fee_rate_bps=book.fee_rate_bps,
                fee_exponent=book.fee_exponent,
                is_maker=False,
                fee_deduction_mode=fee_deduction_mode,
            )
            if str(fee_deduction_mode).upper() == "USDC_ADDITIVE":
                max_net_on_rung = lv.size
                take_net = min(rem_net, max_net_on_rung)
                take_gross = take_net
            else:
                h = compute_v2_buy_share_haircut_frac(
                    q_px,
                    fee_rate_bps=book.fee_rate_bps,
                    fee_exponent=book.fee_exponent,
                )
                one_minus_h = max(0.50, 1.0 - h)
                max_net_on_rung = lv.size * one_minus_h
                take_net = min(rem_net, max_net_on_rung)
                take_gross = take_net / one_minus_h

            if take_net <= 0.0:
                continue
            tot_gross += take_gross
            tot_acq_usd += take_net * pure_ps
            tot_fee_usd += take_net * fee_ps
            worst_px = max(worst_px, q_px)
            rem_net -= take_net
            rungs += 1
            if rem_net <= 1e-9:
                break

        if rem_net > 1e-7:
            return None
        vwap_px = (tot_acq_usd / target_net_shares) if target_net_shares > 0.0 else 0.0
        return (tot_gross, tot_acq_usd, tot_fee_usd, vwap_px, worst_px, rungs)

    @staticmethod
    def _walk_bid_ladder_exact(
        book: InstrumentOrderBook,
        target_sell_shares: float,
        *,
        min_price: Optional[float] = None,
    ) -> Optional[Tuple[float, float, float, float, int]]:
        """
        Walks multi-level L2 bids to sell `target_sell_shares` shares.
        Returns `(gross_proceeds_usd, taker_fee_usd, vwap_bid_px, worst_bid_px, rungs_walked)`
        or `None` if insufficient resting bid depth exists.
        """
        if target_sell_shares <= 0.0:
            return (0.0, 0.0, 0.0, 0.0, 0)
        rem = float(target_sell_shares)
        tot_gross_usd = 0.0
        tot_fee_usd = 0.0
        worst_px = 1.0
        rungs = 0

        for lv in book.bids:
            if min_price is not None and lv.price < float(min_price) - 1e-9:
                break
            q_px, _ = quantize_polymarket_price(
                lv.price,
                "SELL",
                explicit_tick_size=book.tick_size,
                is_maker=False,
            )
            _, gross_ps, fee_ps = compute_net_sell_proceeds_per_share(
                q_px,
                fee_rate_bps=book.fee_rate_bps,
                fee_exponent=book.fee_exponent,
                is_maker=False,
            )
            take = min(rem, lv.size)
            if take <= 0.0:
                continue
            tot_gross_usd += take * gross_ps
            tot_fee_usd += take * fee_ps
            worst_px = min(worst_px, q_px)
            rem -= take
            rungs += 1
            if rem <= 1e-9:
                break

        if rem > 1e-7:
            return None
        vwap_px = tot_gross_usd / target_sell_shares
        return (tot_gross_usd, tot_fee_usd, vwap_px, worst_px, rungs)

    def _unit_non_clob_state_deltas(
        self,
        candidate: CandidateStructure,
        books: Mapping[str, InstrumentOrderBook],
        holdings: Mapping[str, InventoryHolding],
    ) -> Tuple[Dict[str, float], float, float, float, float, float, List[str]]:
        """
        Computes per-1.0-unit `q` linear token changes and non-CLOB cash/costs:
          - `unit_token_delta[inst_id]`
          - `unit_certain_cash_non_clob` (`CTF_MERGE` + gross `NEGRISK_CONVERT` cash)
          - `unit_acq_cost_non_clob` (`CTF_SPLIT` collateral + `USE_INVENTORY` opportunity basis)
          - `unit_cash_outlay_non_clob` (`CTF_SPLIT` liquid `pUSD` cash only; `0.0` for pre-held `USE_INVENTORY`)
          - `unit_conv_cost_non_clob` (`NEGRISK_CONVERT` fee on released collateral)
          - `fixed_gas_usd`
          - `structural_errors`
        """
        cfg = self.config
        token_delta: Dict[str, float] = {}
        certain_cash = 0.0
        acq_cost = 0.0
        cash_outlay_non_clob = 0.0
        conv_cost = 0.0
        fixed_gas = 0.0
        errors: List[str] = []

        for leg in candidate.legs:
            w = float(leg.weight)
            if w <= 0.0 or not math.isfinite(w):
                errors.append("NON_POSITIVE_OR_NAN_LEG_WEIGHT")
                continue
            if str(leg.market_id or "").strip() in FROZEN_DISPUTED_MARKET_IDS:
                errors.append("D001_FROZEN_DISPUTED_KMIA_MARKET_FORBIDDEN")

            at = leg.action_type
            if at == ActionType.BUY_CLOB:
                if not leg.instrument_id:
                    errors.append("MISSING_TOKEN_ID")
                else:
                    token_delta[leg.instrument_id] = token_delta.get(leg.instrument_id, 0.0) + w
                    fixed_gas += max(0.0, float(leg.gas_cost_usd))
            elif at == ActionType.SELL_CLOB:
                if not leg.instrument_id:
                    errors.append("MISSING_TOKEN_ID")
                else:
                    token_delta[leg.instrument_id] = token_delta.get(leg.instrument_id, 0.0) - w
                    fixed_gas += max(0.0, float(leg.gas_cost_usd))
            elif at == ActionType.USE_INVENTORY:
                inv = holdings.get(leg.instrument_id)
                if inv is None:
                    errors.append(f"MISSING_INVENTORY_HOLDING:{leg.instrument_id}")
                elif inv.is_d001_protected():
                    errors.append("D001_FROZEN_DISPUTED_INVENTORY_TOUCH_FORBIDDEN")
                else:
                    token_delta[leg.instrument_id] = token_delta.get(leg.instrument_id, 0.0) + w
                    # Opportunity value of committed inventory: best net bid if book exists, else mark_bid or cost basis
                    bk = books.get(leg.instrument_id)
                    if inv.mark_bid_per_share is not None and inv.mark_bid_per_share >= 0.0:
                        opp_px = float(inv.mark_bid_per_share)
                    elif bk is not None and bk.bids:
                        net_b, _, _ = compute_net_sell_proceeds_per_share(
                            bk.bids[0].price,
                            fee_rate_bps=bk.fee_rate_bps,
                            fee_exponent=bk.fee_exponent,
                        )
                        opp_px = net_b
                    else:
                        opp_px = max(0.0, float(inv.cost_basis_per_share))
                    acq_cost += w * opp_px
            elif at == ActionType.CTF_SPLIT:
                if len(leg.related_instrument_ids) < 2:
                    errors.append("CTF_SPLIT_REQUIRES_AT_LEAST_2_OUTCOME_IDS")
                acq_cost += 1.0 * w
                cash_outlay_non_clob += 1.0 * w
                for tid in leg.related_instrument_ids:
                    token_delta[tid] = token_delta.get(tid, 0.0) + w
                fixed_gas += float(leg.gas_cost_usd) if leg.gas_cost_usd > 0.0 else cfg.default_relayer_gas_usd
            elif at == ActionType.CTF_MERGE:
                if len(leg.related_instrument_ids) < 2:
                    errors.append("CTF_MERGE_REQUIRES_AT_LEAST_2_OUTCOME_IDS")
                certain_cash += 1.0 * w
                for tid in leg.related_instrument_ids:
                    token_delta[tid] = token_delta.get(tid, 0.0) - w
                fixed_gas += float(leg.gas_cost_usd) if leg.gas_cost_usd > 0.0 else cfg.default_relayer_gas_usd
            elif at == ActionType.NEGRISK_CONVERT:
                m = len(leg.burned_no_instrument_ids)
                if m < 1:
                    errors.append("NEGRISK_CONVERT_REQUIRES_AT_LEAST_1_NO_TOKEN")
                c = min(0.25, max(0.0, float(leg.negrisk_fee_bips) / 10_000.0))
                one_minus_c = 1.0 - c
                for no_id in leg.burned_no_instrument_ids:
                    token_delta[no_id] = token_delta.get(no_id, 0.0) - w
                for yes_id in leg.minted_yes_instrument_ids:
                    token_delta[yes_id] = token_delta.get(yes_id, 0.0) + w * one_minus_c
                if m >= 2:
                    gross_rel = float(m - 1) * w
                    certain_cash += gross_rel
                    conv_cost += gross_rel * c
                fixed_gas += float(leg.gas_cost_usd) if leg.gas_cost_usd > 0.0 else cfg.default_relayer_gas_usd

        for tid, delta in token_delta.items():
            if delta < -1e-9:
                errors.append(f"NEGATIVE_POST_ACTION_INVENTORY:{tid}:{delta:.6f}")

        return token_delta, certain_cash, acq_cost, cash_outlay_non_clob, conv_cost, fixed_gas, errors

    def _evaluate_at_quantity(
        self,
        q: float,
        candidate: CandidateStructure,
        books: Mapping[str, InstrumentOrderBook],
        holdings: Mapping[str, InventoryHolding],
        unit_token_delta: Mapping[str, float],
        unit_certain_cash_non_clob: float,
        unit_acq_cost_non_clob: float,
        unit_cash_outlay_non_clob: float,
        unit_conv_cost_non_clob: float,
        fixed_gas_usd: float,
        *,
        use_top_of_book_unlimited: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates exact costs, fees, state payoffs, and leg executions at bundle scale `q > 0`.
        When `use_top_of_book_unlimited=True`, prices CLOB legs at L1 top-of-book without depth limits
        (strictly to compute `theoretical_top_of_book_usd` for comparison against depth-walked L2!).
        """
        if q <= 0.0:
            return None
        cfg = self.config
        acq_usd = q * unit_acq_cost_non_clob
        certain_cash_usd = q * unit_certain_cash_non_clob
        fees_usd = 0.0
        conv_usd = q * unit_conv_cost_non_clob + fixed_gas_usd
        capital_outlay_usd = q * unit_cash_outlay_non_clob
        leg_execs: List[SimulatedLegExecution] = []

        for idx, leg in enumerate(candidate.legs):
            req_sh = q * float(leg.weight)
            at = leg.action_type

            if at == ActionType.USE_INVENTORY:
                inv = holdings.get(leg.instrument_id)
                if inv is None or (not use_top_of_book_unlimited and req_sh > inv.shares + 1e-7):
                    return None
                leg_execs.append(
                    SimulatedLegExecution(
                        leg_index=idx,
                        action_type=at.value,
                        instrument_id=leg.instrument_id,
                        is_maker=False,
                        target_net_shares=round(req_sh, 6),
                        gross_shares=round(req_sh, 6),
                        filled_net_shares=round(req_sh, 6),
                        l1_price=round(float(inv.mark_bid_per_share or inv.cost_basis_per_share), 6),
                        l1_available_shares=round(float(inv.shares), 6),
                        vwap_price=round(float(inv.mark_bid_per_share or inv.cost_basis_per_share), 6),
                        worst_limit_price=0.0,
                        tick_size=0.01,
                        acquisition_or_gross_usd=0.0,
                        taker_fee_usd=0.0,
                        rungs_walked=0,
                        min_order_ok=True,
                        notional_ok=True,
                        status="INVENTORY_COMMITTED",
                    )
                )
                continue

            if at not in (ActionType.BUY_CLOB, ActionType.SELL_CLOB):
                leg_execs.append(
                    SimulatedLegExecution(
                        leg_index=idx,
                        action_type=at.value,
                        instrument_id=leg.instrument_id,
                        is_maker=False,
                        target_net_shares=round(req_sh, 6),
                        gross_shares=round(req_sh, 6),
                        filled_net_shares=round(req_sh, 6),
                        l1_price=1.0 if at in (ActionType.CTF_SPLIT, ActionType.CTF_MERGE) else 0.0,
                        l1_available_shares=req_sh,
                        vwap_price=1.0 if at in (ActionType.CTF_SPLIT, ActionType.CTF_MERGE) else 0.0,
                        worst_limit_price=0.0,
                        tick_size=0.01,
                        acquisition_or_gross_usd=round(req_sh if at in (ActionType.CTF_SPLIT, ActionType.CTF_MERGE) else 0.0, 6),
                        taker_fee_usd=0.0,
                        rungs_walked=0,
                        min_order_ok=True,
                        notional_ok=True,
                        status="ONCHAIN_PRIMITIVE",
                    )
                )
                continue

            bk = books.get(leg.instrument_id)
            if bk is None or not bk.enable_order_book:
                return None

            if at == ActionType.BUY_CLOB:
                if leg.is_maker:
                    raw_mp = leg.maker_price if leg.maker_price is not None else (bk.bids[0].price if bk.bids else 0.0)
                    if raw_mp <= 0.0:
                        return None
                    q_mp, tick = quantize_polymarket_price(raw_mp, "BUY", explicit_tick_size=bk.tick_size, is_maker=True)
                    if bk.asks and q_mp >= bk.asks[0].price - 1e-9:
                        return None
                    cost_leg = req_sh * q_mp
                    acq_usd += cost_leg
                    capital_outlay_usd += cost_leg
                    min_ok = req_sh >= bk.min_order_size - 1e-9
                    leg_execs.append(
                        SimulatedLegExecution(
                            leg_index=idx,
                            action_type=at.value,
                            instrument_id=leg.instrument_id,
                            is_maker=True,
                            target_net_shares=round(req_sh, 6),
                            gross_shares=round(req_sh, 6),
                            filled_net_shares=round(req_sh, 6),
                            l1_price=q_mp,
                            l1_available_shares=round(bk.bids[0].size if bk.bids else 0.0, 6),
                            vwap_price=q_mp,
                            worst_limit_price=q_mp,
                            tick_size=tick,
                            acquisition_or_gross_usd=round(cost_leg, 6),
                            taker_fee_usd=0.0,
                            rungs_walked=1,
                            min_order_ok=min_ok,
                            notional_ok=True,
                            status="PASSIVE_MAKER_BID",
                        )
                    )
                else:
                    if not bk.asks:
                        return None
                    l1_px = bk.asks[0].price
                    l1_sz = bk.asks[0].size
                    if use_top_of_book_unlimited:
                        q_px, tick = quantize_polymarket_price(l1_px, "BUY", explicit_tick_size=bk.tick_size, is_maker=False)
                        tot_ps, pure_ps, fee_ps = compute_net_buy_cost_per_delivered_share(
                            q_px,
                            fee_rate_bps=bk.fee_rate_bps,
                            fee_exponent=bk.fee_exponent,
                            fee_deduction_mode=cfg.fee_deduction_mode,
                        )
                        gross_sh = req_sh * (tot_ps / max(q_px, 1e-6))
                        leg_acq = req_sh * pure_ps
                        leg_fee = req_sh * fee_ps
                        vwap_px, worst_px, rungs = q_px, q_px, 1
                    else:
                        walked = self._walk_ask_ladder_exact(
                            bk,
                            req_sh,
                            fee_deduction_mode=cfg.fee_deduction_mode,
                            max_price=leg.max_slippage_price,
                        )
                        if walked is None:
                            return None
                        gross_sh, leg_acq, leg_fee, vwap_px, worst_px, rungs = walked
                        _, tick = quantize_polymarket_price(worst_px, "BUY", explicit_tick_size=bk.tick_size, is_maker=False)

                    gross_usdc = leg_acq + leg_fee
                    min_ok = gross_sh >= bk.min_order_size - 1e-9 and req_sh >= bk.min_order_size - 1e-9
                    notional_ok = (not cfg.enforce_min_marketable_notional) or (gross_usdc >= cfg.min_marketable_buy_usd - 1e-9)
                    if not use_top_of_book_unlimited and (not min_ok or not notional_ok):
                        return None
                    acq_usd += leg_acq
                    fees_usd += leg_fee
                    capital_outlay_usd += gross_usdc
                    leg_execs.append(
                        SimulatedLegExecution(
                            leg_index=idx,
                            action_type=at.value,
                            instrument_id=leg.instrument_id,
                            is_maker=False,
                            target_net_shares=round(req_sh, 6),
                            gross_shares=round(gross_sh, 6),
                            filled_net_shares=round(req_sh, 6),
                            l1_price=round(l1_px, 6),
                            l1_available_shares=round(l1_sz, 6),
                            vwap_price=round(vwap_px, 6),
                            worst_limit_price=round(worst_px, 6),
                            tick_size=tick,
                            acquisition_or_gross_usd=round(leg_acq, 6),
                            taker_fee_usd=round(leg_fee, 6),
                            rungs_walked=rungs,
                            min_order_ok=min_ok,
                            notional_ok=notional_ok,
                            status="TAKER_ASK_WALKED",
                        )
                    )
            elif at == ActionType.SELL_CLOB:
                if leg.is_maker:
                    raw_mp = leg.maker_price if leg.maker_price is not None else (bk.asks[0].price if bk.asks else 0.0)
                    if raw_mp <= 0.0:
                        return None
                    q_mp, tick = quantize_polymarket_price(raw_mp, "SELL", explicit_tick_size=bk.tick_size, is_maker=True)
                    if bk.bids and q_mp <= bk.bids[0].price + 1e-9:
                        return None
                    gross_rev = req_sh * q_mp
                    certain_cash_usd += gross_rev
                    min_ok = req_sh >= bk.min_order_size - 1e-9
                    leg_execs.append(
                        SimulatedLegExecution(
                            leg_index=idx,
                            action_type=at.value,
                            instrument_id=leg.instrument_id,
                            is_maker=True,
                            target_net_shares=round(req_sh, 6),
                            gross_shares=round(req_sh, 6),
                            filled_net_shares=round(req_sh, 6),
                            l1_price=q_mp,
                            l1_available_shares=round(bk.asks[0].size if bk.asks else 0.0, 6),
                            vwap_price=q_mp,
                            worst_limit_price=q_mp,
                            tick_size=tick,
                            acquisition_or_gross_usd=round(gross_rev, 6),
                            taker_fee_usd=0.0,
                            rungs_walked=1,
                            min_order_ok=min_ok,
                            notional_ok=True,
                            status="PASSIVE_MAKER_ASK",
                        )
                    )
                else:
                    if not bk.bids:
                        return None
                    l1_px = bk.bids[0].price
                    l1_sz = bk.bids[0].size
                    if use_top_of_book_unlimited:
                        q_px, tick = quantize_polymarket_price(l1_px, "SELL", explicit_tick_size=bk.tick_size, is_maker=False)
                        _, gross_ps, fee_ps = compute_net_sell_proceeds_per_share(
                            q_px,
                            fee_rate_bps=bk.fee_rate_bps,
                            fee_exponent=bk.fee_exponent,
                        )
                        gross_rev = req_sh * gross_ps
                        leg_fee = req_sh * fee_ps
                        vwap_px, worst_px, rungs = q_px, q_px, 1
                    else:
                        walked_b = self._walk_bid_ladder_exact(bk, req_sh, min_price=leg.max_slippage_price)
                        if walked_b is None:
                            return None
                        gross_rev, leg_fee, vwap_px, worst_px, rungs = walked_b
                        _, tick = quantize_polymarket_price(worst_px, "SELL", explicit_tick_size=bk.tick_size, is_maker=False)

                    min_ok = req_sh >= bk.min_order_size - 1e-9
                    if not use_top_of_book_unlimited and not min_ok:
                        return None
                    certain_cash_usd += gross_rev
                    fees_usd += leg_fee
                    leg_execs.append(
                        SimulatedLegExecution(
                            leg_index=idx,
                            action_type=at.value,
                            instrument_id=leg.instrument_id,
                            is_maker=False,
                            target_net_shares=round(req_sh, 6),
                            gross_shares=round(req_sh, 6),
                            filled_net_shares=round(req_sh, 6),
                            l1_price=round(l1_px, 6),
                            l1_available_shares=round(l1_sz, 6),
                            vwap_price=round(vwap_px, 6),
                            worst_limit_price=round(worst_px, 6),
                            tick_size=tick,
                            acquisition_or_gross_usd=round(gross_rev, 6),
                            taker_fee_usd=round(leg_fee, 6),
                            rungs_walked=rungs,
                            min_order_ok=min_ok,
                            notional_ok=True,
                            status="TAKER_BID_WALKED",
                        )
                    )

        if not use_top_of_book_unlimited and (capital_outlay_usd + fixed_gas_usd) > cfg.max_budget_usd + 1e-6:
            return None

        has_terminal_tokens = any(abs(v) > 1e-9 for v in unit_token_delta.values())
        base_settle_gas = cfg.settlement_gas_usd if has_terminal_tokens else 0.0

        # Normalize state probabilities
        raw_probs = [max(0.0, float(s.probability if s.probability is not None else 1.0)) for s in candidate.states]
        prob_sum = sum(raw_probs)
        norm_probs = [p / prob_sum for p in raw_probs] if prob_sum > 0.0 else [1.0 / max(1, len(candidate.states))] * len(candidate.states)

        state_breakdowns: List[StatePayoffBreakdown] = []
        max_lockup_seen = max(0.0, float(candidate.worst_case_lockup_hours))
        max_settle_cost = 0.0
        economic_locked_usd = max(capital_outlay_usd, acq_usd + fees_usd)

        for st, prob in zip(candidate.states, norm_probs):
            payout_usd = 0.0
            for tid, u_delta in unit_token_delta.items():
                if abs(u_delta) <= 1e-12:
                    continue
                q_tok = q * u_delta
                # Fail-closed conservative payout if missing: 0.0 for positive holdings
                px_out = float(st.instrument_payouts.get(tid, 0.0 if q_tok >= 0.0 else 1.0))
                payout_usd += q_tok * min(1.0, max(0.0, px_out))

            st_lock_hrs = (
                float(st.lockup_hours_override)
                if st.lockup_hours_override is not None
                else (float(candidate.worst_case_lockup_hours) if has_terminal_tokens else 0.01)
            )
            max_lockup_seen = max(max_lockup_seen, st_lock_hrs)
            lockup_cap_cost = (
                max(0.0, economic_locked_usd)
                * (max(0.0, float(cfg.lockup_opportunity_cost_bps_per_hour)) / 10_000.0)
                * max(0.0, st_lock_hrs)
            )
            settle_usd = base_settle_gas + max(0.0, float(st.extra_settlement_cost_usd)) + lockup_cap_cost
            max_settle_cost = max(max_settle_cost, settle_usd)

            # Exact governing equation:
            # NetPayoff(omega) = ContractPayout(omega, q) + CertainCashFlows
            #                    - AcquisitionCosts - Fees - ConversionCosts - SettlementCosts(omega)
            net_pay = payout_usd + certain_cash_usd - acq_usd - fees_usd - conv_usd - settle_usd
            state_breakdowns.append(
                StatePayoffBreakdown(
                    state_id=st.state_id,
                    probability=round(prob, 6),
                    contract_payout_usd=round(payout_usd, 6),
                    certain_cash_flows_usd=round(certain_cash_usd, 6),
                    acquisition_costs_usd=round(acq_usd, 6),
                    fees_usd=round(fees_usd, 6),
                    conversion_costs_usd=round(conv_usd, 6),
                    settlement_costs_usd=round(settle_usd, 6),
                    net_payoff_usd=round(net_pay, 6),
                    is_edge_or_void_state=st.is_edge_or_void_state,
                )
            )

        if not state_breakdowns:
            return None

        worst_st = min(state_breakdowns, key=lambda s: s.net_payoff_usd)
        best_st = max(state_breakdowns, key=lambda s: s.net_payoff_usd)
        ev_usd = sum(s.probability * s.net_payoff_usd for s in state_breakdowns)

        lock_cap_worst = (
            max(0.0, economic_locked_usd)
            * (max(0.0, float(cfg.lockup_opportunity_cost_bps_per_hour)) / 10_000.0)
            * max(0.0, max_lockup_seen if has_terminal_tokens else 0.01)
        )
        cost_bd = CostBreakdown(
            acquisition_costs_usd=round(acq_usd, 6),
            taker_fees_usd=round(fees_usd, 6),
            conversion_costs_usd=round(conv_usd - fixed_gas_usd, 6),
            gas_costs_usd=round(fixed_gas_usd + base_settle_gas, 6),
            lockup_capital_cost_usd=round(lock_cap_worst, 6),
            settlement_costs_usd=round(max_settle_cost, 6),
            certain_cash_flows_usd=round(certain_cash_usd, 6),
            capital_required_usd=round(max(0.0, capital_outlay_usd + fixed_gas_usd), 6),
            expected_lockup_hours=round(float(candidate.expected_lockup_hours if has_terminal_tokens else 0.01), 4),
            worst_case_lockup_hours=round(float(max_lockup_seen if has_terminal_tokens else 0.01), 4),
        )

        return {
            "q": round(q, 6),
            "min_payoff": worst_st.net_payoff_usd,
            "max_payoff": best_st.net_payoff_usd,
            "ev_payoff": round(ev_usd, 6),
            "worst_state_id": worst_st.state_id,
            "state_breakdowns": tuple(state_breakdowns),
            "cost_breakdown": cost_bd,
            "leg_executions": tuple(leg_execs),
        }

    def _collect_candidate_quantities(
        self,
        candidate: CandidateStructure,
        books: Mapping[str, InstrumentOrderBook],
        holdings: Mapping[str, InventoryHolding],
        unit_cash_outlay_non_clob: float,
        fixed_gas_usd: float,
    ) -> Tuple[float, float, List[float]]:
        """
        Builds the exact grid of L2 rung-capacity breakpoints `q` across all legs, respecting
        per-instrument `min_order_size`, `$1.00` marketable BUY notional floor, inventory limits,
        and liquid cash `max_budget_usd - fixed_gas_usd` so marginal optimization finds exact `q*`.
        Returns `(min_q, max_depth_q, sorted_candidate_q_grid)`.
        """
        cfg = self.config
        lot_f = float(cfg.lot_step_shares if cfg.lot_step_shares > 0 else 0.01)
        lot_e8 = int(round(round(lot_f, 8) * _E8_SCALE))

        def _q_floor(val: float) -> float:
            if val <= 0.0:
                return 0.0
            if lot_e8 > 0:
                v_e8 = int(round(round(val, 8) * _E8_SCALE))
                return round(((v_e8 // lot_e8) * lot_e8) / _E8_SCALE, 8)
            lot = Decimal(str(lot_f))
            return float((Decimal(str(round(val, 8))) / lot).to_integral_value(rounding=ROUND_FLOOR) * lot)

        def _q_ceil(val: float) -> float:
            if val <= 0.0:
                return 0.0
            if lot_e8 > 0:
                v_e8 = int(round(round(val, 8) * _E8_SCALE))
                return round((((v_e8 + lot_e8 - 1) // lot_e8) * lot_e8) / _E8_SCALE, 8)
            lot = Decimal(str(lot_f))
            return float((Decimal(str(round(val, 8))) / lot).to_integral_value(rounding=ROUND_CEILING) * lot)

        if fixed_gas_usd > cfg.max_budget_usd + 1e-9:
            return (DEFAULT_MIN_ORDER_SHARES, 0.0, [])

        min_q = 0.0
        max_q_caps: List[float] = []
        raw_breakpoints: Set[float] = set()

        est_unit_cost = unit_cash_outlay_non_clob
        for leg in candidate.legs:
            w = float(leg.weight)
            if w <= 0.0:
                continue
            if leg.action_type == ActionType.USE_INVENTORY:
                inv = holdings.get(leg.instrument_id)
                if inv is None or inv.shares <= 0.0:
                    return (DEFAULT_MIN_ORDER_SHARES, 0.0, [])
                max_q_caps.append(inv.shares / w)
                raw_breakpoints.add(_q_floor(inv.shares / w))
                continue

            if leg.action_type not in (ActionType.BUY_CLOB, ActionType.SELL_CLOB):
                continue

            bk = books.get(leg.instrument_id)
            if bk is None or not bk.enable_order_book:
                return (DEFAULT_MIN_ORDER_SHARES, 0.0, [])

            min_q = max(min_q, bk.min_order_size / w)

            if leg.is_maker:
                mp = float(leg.maker_price or (bk.bids[0].price if (leg.action_type == ActionType.BUY_CLOB and bk.bids) else (bk.asks[0].price if bk.asks else 0.50)))
                if leg.action_type == ActionType.BUY_CLOB:
                    est_unit_cost += w * max(0.01, mp)
                continue

            if leg.action_type == ActionType.BUY_CLOB:
                if not bk.asks:
                    return (min_q, 0.0, [])
                l1_q_px, _ = quantize_polymarket_price(bk.asks[0].price, "BUY", explicit_tick_size=bk.tick_size)
                l1_tot_ps, _, _ = compute_net_buy_cost_per_delivered_share(
                    l1_q_px,
                    fee_rate_bps=bk.fee_rate_bps,
                    fee_exponent=bk.fee_exponent,
                    fee_deduction_mode=cfg.fee_deduction_mode,
                )
                est_unit_cost += w * l1_tot_ps
                if cfg.enforce_min_marketable_notional and l1_tot_ps > 0.0:
                    min_q = max(min_q, cfg.min_marketable_buy_usd / (w * l1_tot_ps))

                cum_net = 0.0
                for lv in bk.asks:
                    if leg.max_slippage_price is not None and lv.price > float(leg.max_slippage_price) + 1e-9:
                        break
                    q_px, _ = quantize_polymarket_price(lv.price, "BUY", explicit_tick_size=bk.tick_size)
                    if str(cfg.fee_deduction_mode).upper() == "USDC_ADDITIVE":
                        rung_net = lv.size
                    else:
                        h = compute_v2_buy_share_haircut_frac(
                            q_px,
                            fee_rate_bps=bk.fee_rate_bps,
                            fee_exponent=bk.fee_exponent,
                        )
                        rung_net = lv.size * max(0.50, 1.0 - h)
                    cum_net += rung_net
                    raw_breakpoints.add(_q_floor(cum_net / w))
                max_q_caps.append(cum_net / w)
            else:
                if not bk.bids:
                    return (min_q, 0.0, [])
                cum_bid = 0.0
                for lv in bk.bids:
                    if leg.max_slippage_price is not None and lv.price < float(leg.max_slippage_price) - 1e-9:
                        break
                    cum_bid += lv.size
                    raw_breakpoints.add(_q_floor(cum_bid / w))
                max_q_caps.append(cum_bid / w)

        if min_q <= 0.0:
            min_q = DEFAULT_MIN_ORDER_SHARES
        min_q_quant = _q_ceil(min_q)

        avail_cash_budget = max(0.0, cfg.max_budget_usd - fixed_gas_usd)
        if est_unit_cost > 1e-6:
            budget_q = _q_floor(avail_cash_budget / est_unit_cost)
            raw_breakpoints.add(budget_q)
            if not max_q_caps:
                max_q_caps.append(avail_cash_budget / est_unit_cost)
        elif not max_q_caps:
            max_q_caps.append(100.0)

        max_depth_q = _q_floor(min(max_q_caps)) if max_q_caps else 0.0
        raw_breakpoints.add(min_q_quant)
        raw_breakpoints.add(max_depth_q)

        # Add fine interior points if budget caps inside a wide L2 rung
        valid_qs = sorted(q for q in raw_breakpoints if min_q_quant - 1e-9 <= q <= max_depth_q + 1e-9 and q > 0.0)
        if min_q_quant <= max_depth_q and len(valid_qs) >= 2:
            # Binary-search budget cap if `max_depth_q` exceeds `max_budget_usd`
            extra: List[float] = []
            lo_q, hi_q = valid_qs[0], valid_qs[-1]
            for frac in (0.25, 0.50, 0.75):
                mid_q = _q_floor(lo_q + frac * (hi_q - lo_q))
                if lo_q < mid_q < hi_q:
                    extra.append(mid_q)
            valid_qs = sorted(set(valid_qs) | set(extra))

        return min_q_quant, max_depth_q, valid_qs

    def _compute_attainable_risk_adjusted_usd(
        self,
        *,
        opp_class: OpportunityClass,
        is_atomic_or_prelocked: bool,
        executable_l2_net_usd: float,
        expected_net_payoff_usd: float,
        leg_execs: Sequence[SimulatedLegExecution],
        books: Mapping[str, InstrumentOrderBook],
    ) -> float:
        """
        Computes realistic post-latency, partial-fill-risk-adjusted attainable value:
          - `CLASS_D` / `CLASS_E`: `0.0` (never assign positive attainable value to unproven or invalid trades).
          - `CLASS_A` (atomic on-chain or 1-leg FOK completing held inventory): zero partial-fill leg-out bleed;
            `p_fill * executable_l2_net_usd`.
          - `CLASS_B` (multi-leg sequential CLOB or split/convert + CLOB sweep): discounts by `p_all_legs_fill`
            and subtracts expected emergency bid-walk unwind bleed `(1 - p_later_legs) * leg1_spread_and_fee_bleed`.
          - `CLASS_C` (outcome-dependent positive EV / maker): discounts `expected_net_payoff_usd` by fill survival.
        """
        cfg = self.config
        if opp_class in (OpportunityClass.CLASS_D, OpportunityClass.CLASS_E):
            return 0.0

        clob_taker_legs = [le for le in leg_execs if le.action_type in ("BUY_CLOB", "SELL_CLOB") and not le.is_maker]
        maker_legs = [le for le in leg_execs if le.is_maker]
        rtt_factor = max(0.65, min(0.99, math.exp(-max(0.0, cfg.wire_rtt_ms - 50.0) / 1200.0)))
        per_taker_p = max(0.50, min(0.99, cfg.per_leg_fill_survival_decay * rtt_factor))

        if opp_class == OpportunityClass.CLASS_C:
            if expected_net_payoff_usd <= 0.0:
                return 0.0
            p_m = (cfg.passive_maker_fill_prob ** len(maker_legs)) if maker_legs else 1.0
            p_t = (per_taker_p ** len(clob_taker_legs)) if clob_taker_legs else 1.0
            return round(max(0.0, expected_net_payoff_usd * p_m * p_t), 6)

        if executable_l2_net_usd <= 0.0:
            return 0.0

        if is_atomic_or_prelocked:
            p_fill = per_taker_p if len(clob_taker_legs) == 1 else 1.0
            return round(executable_l2_net_usd * p_fill, 6)

        n_t = max(1, len(clob_taker_legs))
        p_all = per_taker_p ** n_t
        # Estimate leg-1 emergency unwind bleed if leg 1 fills (`per_taker_p`) and subsequent legs miss (`1 - per_taker_p**(n_t-1)`)
        unwind_bleed_usd = 0.0
        if clob_taker_legs and n_t >= 2:
            first_leg = clob_taker_legs[0]
            bk1 = books.get(first_leg.instrument_id)
            paid_1 = first_leg.acquisition_or_gross_usd + first_leg.taker_fee_usd
            if first_leg.action_type == "BUY_CLOB" and bk1 is not None:
                wb = self._walk_bid_ladder_exact(bk1, first_leg.filled_net_shares)
                if wb is not None:
                    net_rec = max(0.0, wb[0] - wb[1])
                    unwind_bleed_usd = max(0.01 * paid_1, paid_1 - net_rec)
                else:
                    unwind_bleed_usd = 0.15 * paid_1
            else:
                unwind_bleed_usd = 0.03 * max(1.0, paid_1)
        elif any(le.action_type in ("CTF_SPLIT", "NEGRISK_CONVERT") for le in leg_execs) and n_t >= 1:
            # Split/convert block lag before CLOB bid sweep
            p_all = per_taker_p * 0.90
            unwind_bleed_usd = 0.015 * sum(le.acquisition_or_gross_usd for le in clob_taker_legs)

        p_leg_out = per_taker_p * (1.0 - (per_taker_p ** max(1, n_t - 1))) if n_t >= 2 else (1.0 - p_all)
        att = p_all * executable_l2_net_usd - p_leg_out * unwind_bleed_usd
        return round(att, 6)

    def verify_and_simulate(
        self,
        candidate: CandidateStructure,
        books: Mapping[str, InstrumentOrderBook],
        *,
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
    ) -> ArbitrageProofObject:
        """
        Executes complete state-space verification + depth-aware L2 marginal sizing + 5-tier classification.
        """
        cfg = self.config
        inv_map: Mapping[str, InventoryHolding] = holdings or {}
        now_f = float(time.time() if cfg.now_ts is None else cfg.now_ts)

        disqualifiers: List[str] = list(candidate.rule_disqualifiers)
        residual_risks: List[str] = ["VENUE_CUSTODY_AND_SMART_CONTRACT", "ORACLE_GOVERNANCE_TAIL"]

        unit_delta, u_cash, u_acq, u_cash_outlay, u_conv, fixed_gas, struct_errs = self._unit_non_clob_state_deltas(
            candidate, books, inv_map
        )
        disqualifiers.extend(struct_errs)

        # Inspect order books on all CLOB legs
        has_disabled_book = False
        has_missing_book = False
        has_crossed_book = False
        has_stale_book = False
        has_placeholder_or_other = False
        has_passive_maker = False
        unheld_clob_legs = 0
        has_split_or_convert = False

        for leg in candidate.legs:
            if leg.action_type in (ActionType.CTF_SPLIT, ActionType.NEGRISK_CONVERT):
                has_split_or_convert = True
            if leg.action_type in (ActionType.BUY_CLOB, ActionType.SELL_CLOB):
                unheld_clob_legs += 1
                if leg.is_maker:
                    has_passive_maker = True
                bk = books.get(leg.instrument_id)
                if bk is None:
                    has_missing_book = True
                    disqualifiers.append(f"MISSING_ORDER_BOOK:{leg.instrument_id}")
                    continue
                if not bk.enable_order_book:
                    has_disabled_book = True
                    disqualifiers.append(f"ORDERBOOK_DISABLED:{leg.instrument_id}")
                if bk.has_crossed_or_invalid_book():
                    has_crossed_book = True
                    disqualifiers.append(f"CROSSED_OR_INVALID_BOOK:{leg.instrument_id}")
                if bk.book_timestamp_sec is not None and (now_f - bk.book_timestamp_sec) > cfg.max_book_age_sec:
                    has_stale_book = True
                    disqualifiers.append(f"STALE_ORDER_BOOK:{leg.instrument_id}")
                if bk.is_placeholder:
                    has_placeholder_or_other = True
                    disqualifiers.append(f"AUGMENTED_PLACEHOLDER_TOKEN:{leg.instrument_id}")

        if not candidate.states:
            disqualifiers.append("EMPTY_STATE_SPACE_UNPROVEN")
        if not candidate.rule_verified:
            disqualifiers.append("RESOLUTION_RULES_UNVERIFIED")
        if candidate.requires_exhaustive_partition and not candidate.is_exhaustive_partition:
            disqualifiers.append("NON_EXHAUSTIVE_MULTI_OUTCOME_SET")
        if candidate.requires_exhaustive_partition and not candidate.is_mutually_exclusive:
            disqualifiers.append("NON_MUTUALLY_EXCLUSIVE_OUTCOME_SET")
        if candidate.has_augmented_placeholder_risk:
            disqualifiers.append("AUGMENTED_NEGRISK_PLACEHOLDER_HAZARD")
        if candidate.has_mutable_other_exposure:
            disqualifiers.append("AUGMENTED_NEGRISK_MUTABLE_OTHER_EXPOSURE")
        if candidate.unverified_rebate_or_reward_usd_per_unit > 0.0:
            residual_risks.append("UNVERIFIED_MAKER_REBATE_EXCLUDED_FROM_GUARANTEED_FLOOR")

        # Hard D-001 or structural error or disabled order book -> immediate CLASS_E
        hard_class_e = bool(
            struct_errs
            or has_disabled_book
            or has_missing_book
            or not candidate.legs
        )

        min_q, max_depth_q, cand_qs = (
            (DEFAULT_MIN_ORDER_SHARES, 0.0, [])
            if hard_class_e
            else self._collect_candidate_quantities(candidate, books, inv_map, u_cash_outlay, fixed_gas)
        )

        # Evaluate L2 candidate quantities to find exact optimal `q*` maximizing `min_w NetPayoff(w; q)`
        # (and fallback `q_ev*` if `min_w <= 0` everywhere but `EV > 0` for Class C!)
        best_arb_eval: Optional[Dict[str, Any]] = None
        best_ev_eval: Optional[Dict[str, Any]] = None

        if not hard_class_e and candidate.states and not has_crossed_book:
            # Fine-step refinement if budget caps below max_depth_q
            eval_grid: List[float] = list(cand_qs)
            for q_cand in eval_grid:
                ev_res = self._evaluate_at_quantity(
                    q_cand,
                    candidate,
                    books,
                    inv_map,
                    unit_delta,
                    u_cash,
                    u_acq,
                    u_cash_outlay,
                    u_conv,
                    fixed_gas,
                    use_top_of_book_unlimited=False,
                )
                if ev_res is None:
                    continue
                if best_arb_eval is None or (
                    ev_res["min_payoff"] > best_arb_eval["min_payoff"] + 1e-9
                    or (abs(ev_res["min_payoff"] - best_arb_eval["min_payoff"]) <= 1e-9 and ev_res["q"] > best_arb_eval["q"])
                ):
                    best_arb_eval = ev_res
                if best_ev_eval is None or ev_res["ev_payoff"] > best_ev_eval["ev_payoff"] + 1e-9:
                    best_ev_eval = ev_res

            # Refine upper budget/depth boundary via binary search whenever a deeper rung exists above `best_arb_eval["q"]`
            lot = cfg.lot_step_shares if cfg.lot_step_shares > 0 else 0.01
            if max_depth_q >= min_q:
                start_lo = best_arb_eval["q"] if best_arb_eval is not None else min_q
                if max_depth_q > start_lo + lot:
                    lo, hi = start_lo, max_depth_q
                    for _ in range(18):
                        mid = round(math.floor(((lo + hi) * 0.5 + 1e-12) / lot) * lot, 6)
                        if mid <= lo or mid > hi:
                            break
                        r_mid = self._evaluate_at_quantity(
                            mid, candidate, books, inv_map, unit_delta, u_cash, u_acq, u_cash_outlay, u_conv, fixed_gas
                        )
                        if r_mid is not None:
                            if best_arb_eval is None or r_mid["min_payoff"] >= best_arb_eval["min_payoff"] - 1e-9:
                                if best_arb_eval is None or r_mid["min_payoff"] > best_arb_eval["min_payoff"] + 1e-9 or r_mid["q"] > best_arb_eval["q"]:
                                    best_arb_eval = r_mid
                                lo = mid
                            else:
                                # Past optimal marginal rung (deeper rung diluted min_payoff)
                                hi = mid - lot
                            if best_ev_eval is None or r_mid["ev_payoff"] > best_ev_eval["ev_payoff"] + 1e-9:
                                best_ev_eval = r_mid
                        else:
                            hi = mid - lot

        chosen_eval = (
            best_arb_eval
            if (best_arb_eval is not None and best_arb_eval["min_payoff"] > 0.0)
            else (best_ev_eval if (best_ev_eval is not None and best_ev_eval["ev_payoff"] > 0.0) else best_arb_eval)
        )

        # Compute L1 Top-of-Book reference theoretical value
        q_ref = chosen_eval["q"] if chosen_eval is not None else max(DEFAULT_MIN_ORDER_SHARES, min_q)
        tob_eval = (
            self._evaluate_at_quantity(
                q_ref,
                candidate,
                books,
                inv_map,
                unit_delta,
                u_cash,
                u_acq,
                u_cash_outlay,
                u_conv,
                fixed_gas,
                use_top_of_book_unlimited=True,
            )
            if (not hard_class_e and candidate.states and not has_crossed_book)
            else None
        )
        tob_unit_eval = (
            self._evaluate_at_quantity(
                1.0,
                candidate,
                books,
                inv_map,
                unit_delta,
                u_cash,
                u_acq,
                u_cash_outlay,
                u_conv,
                0.0,
                use_top_of_book_unlimited=True,
            )
            if (not hard_class_e and candidate.states and not has_crossed_book)
            else None
        )
        gross_tob_edge_unit = round(tob_unit_eval["min_payoff"], 6) if tob_unit_eval is not None else 0.0

        # Atomicity / Pre-locked check (STRICT: never promote sequential multi-leg or post-split/post-convert CLOB sweeps!)
        has_ctf_split = any(lg.action_type == ActionType.CTF_SPLIT for lg in candidate.legs)
        has_clob_sell = any(lg.action_type == ActionType.SELL_CLOB for lg in candidate.legs)
        has_preheld_inventory = any(lg.action_type == ActionType.USE_INVENTORY for lg in candidate.legs)
        all_states_onchain_final = bool(
            candidate.states
            and all(s.state_id == "OMEGA_ONCHAIN_PAYOUT_FINALIZED" for s in candidate.states)
        )
        is_atomic_or_prelocked = bool(
            not has_passive_maker
            and (
                unheld_clob_legs == 0
                or (
                    unheld_clob_legs == 1
                    and not has_ctf_split
                    and not (has_split_or_convert and has_clob_sell)
                    and (has_preheld_inventory or all_states_onchain_final)
                )
            )
        )
        if not is_atomic_or_prelocked and unheld_clob_legs >= 2:
            residual_risks.append("SEQUENTIAL_CLOB_PARTIAL_FILL_CONSTRUCTION_RISK")
        if has_split_or_convert and unheld_clob_legs >= 1:
            residual_risks.append("ONCHAIN_CONFIRMATION_TO_CLOB_SWEEP_LAG")

        d007_quarantine = bool(
            unheld_clob_legs >= 3
            and not is_atomic_or_prelocked
            and float(cfg.reconciled_nav_usd) < float(cfg.d007_multileg_nav_floor_usd)
        )
        if d007_quarantine:
            residual_risks.append("D007_SUB_500_NAV_SEQUENTIAL_3PLUS_LEG_QUARANTINE")

        # Rule/book ambiguity flags (`CLASS_D` triggers)
        has_rule_or_book_ambiguity = bool(
            not candidate.states
            or not candidate.rule_verified
            or bool(candidate.rule_disqualifiers)
            or (candidate.requires_exhaustive_partition and (not candidate.is_exhaustive_partition or not candidate.is_mutually_exclusive))
            or candidate.has_augmented_placeholder_risk
            or candidate.has_mutable_other_exposure
            or has_placeholder_or_other
            or has_crossed_book
            or has_stale_book
        )

        # Counterexample states (`NetPayoff(omega) <= 0`)
        counterexamples: List[str] = []
        if chosen_eval is not None:
            for sb in chosen_eval["state_breakdowns"]:
                if sb.net_payoff_usd <= 0.0:
                    counterexamples.append(f"{sb.state_id}:{sb.net_payoff_usd:.4f}")
        elif tob_eval is not None:
            for sb in tob_eval["state_breakdowns"]:
                if sb.net_payoff_usd <= 0.0:
                    counterexamples.append(f"{sb.state_id}:{sb.net_payoff_usd:.4f}")

        # Strict 5-Tier Classification
        if hard_class_e:
            opp_class = OpportunityClass.CLASS_E
        elif has_rule_or_book_ambiguity:
            opp_class = OpportunityClass.CLASS_D
        elif chosen_eval is None:
            disqualifiers.append(
                "INSUFFICIENT_L2_DEPTH_OR_MIN_NOTIONAL"
                if max_depth_q < min_q
                else "NO_FEASIBLE_EXECUTABLE_QUANTITY"
            )
            opp_class = OpportunityClass.CLASS_E
        else:
            min_pay = float(chosen_eval["min_payoff"])
            ev_pay = float(chosen_eval["ev_payoff"])

            if candidate.is_statistical_or_cross_oracle_only or candidate.uma_proposal_unfinalized or has_passive_maker:
                if candidate.uma_proposal_unfinalized:
                    disqualifiers.append("UNFINALIZED_UMA_PROPOSAL_CARRY_NOT_CLASS_A_OR_B")
                if has_passive_maker:
                    disqualifiers.append("PASSIVE_MAKER_FILL_UNCERTAINTY_NOT_CLASS_A_OR_B")
                if candidate.is_statistical_or_cross_oracle_only:
                    disqualifiers.append("STATISTICAL_OR_CROSS_ORACLE_BASIS_EXPOSURE")
                opp_class = OpportunityClass.CLASS_C if ev_pay > 0.0 else OpportunityClass.CLASS_E
            elif min_pay > 0.0:
                opp_class = OpportunityClass.CLASS_A if is_atomic_or_prelocked else OpportunityClass.CLASS_B
            elif ev_pay > 0.0:
                disqualifiers.append("MIN_STATE_PAYOFF_NON_POSITIVE")
                opp_class = OpportunityClass.CLASS_C
            else:
                disqualifiers.append("NEGATIVE_OR_ZERO_NET_EXECUTABLE_PAYOFF")
                opp_class = OpportunityClass.CLASS_E

        # Enforce non-overridable anti-promotion invariant
        if opp_class == OpportunityClass.CLASS_A:
            assert (
                chosen_eval is not None
                and chosen_eval["min_payoff"] > 0.0
                and is_atomic_or_prelocked
                and not has_rule_or_book_ambiguity
                and not candidate.uma_proposal_unfinalized
                and not candidate.is_statistical_or_cross_oracle_only
                and not has_passive_maker
            ), "CLASS_A invariant violation"

        if chosen_eval is not None and opp_class in (OpportunityClass.CLASS_A, OpportunityClass.CLASS_B, OpportunityClass.CLASS_C):
            opt_q = float(chosen_eval["q"])
            min_net = float(chosen_eval["min_payoff"])
            max_net = float(chosen_eval["max_payoff"])
            ev_net = float(chosen_eval["ev_payoff"])
            worst_id = str(chosen_eval["worst_state_id"])
            st_tuple = chosen_eval["state_breakdowns"]
            cost_bd = chosen_eval["cost_breakdown"]
            leg_tuple = chosen_eval["leg_executions"]
            exec_l2_usd = min_net if opp_class in (OpportunityClass.CLASS_A, OpportunityClass.CLASS_B) else ev_net
            net_unit_edge = round(exec_l2_usd / max(opt_q, 1e-9), 6)
        else:
            opt_q = 0.0
            min_net = float(chosen_eval["min_payoff"]) if chosen_eval is not None else (float(tob_eval["min_payoff"]) if tob_eval is not None else 0.0)
            max_net = float(chosen_eval["max_payoff"]) if chosen_eval is not None else (float(tob_eval["max_payoff"]) if tob_eval is not None else 0.0)
            ev_net = float(chosen_eval["ev_payoff"]) if chosen_eval is not None else (float(tob_eval["ev_payoff"]) if tob_eval is not None else 0.0)
            worst_id = str(chosen_eval["worst_state_id"]) if chosen_eval is not None else (str(tob_eval["worst_state_id"]) if tob_eval is not None else "NONE")
            st_tuple = chosen_eval["state_breakdowns"] if chosen_eval is not None else (tob_eval["state_breakdowns"] if tob_eval is not None else ())
            cost_bd = (
                chosen_eval["cost_breakdown"]
                if chosen_eval is not None
                else CostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, candidate.expected_lockup_hours, candidate.worst_case_lockup_hours)
            )
            leg_tuple = chosen_eval["leg_executions"] if chosen_eval is not None else ()
            exec_l2_usd = 0.0
            net_unit_edge = round(min_net / max(q_ref, 1e-9), 6) if chosen_eval is not None else gross_tob_edge_unit

        tob_usd = (
            float(tob_eval["min_payoff"] if opp_class != OpportunityClass.CLASS_C else tob_eval["ev_payoff"])
            if tob_eval is not None
            else 0.0
        )
        att_usd = self._compute_attainable_risk_adjusted_usd(
            opp_class=opp_class,
            is_atomic_or_prelocked=is_atomic_or_prelocked,
            executable_l2_net_usd=exec_l2_usd,
            expected_net_payoff_usd=ev_net,
            leg_execs=leg_tuple,
            books=books,
        )
        four_vals = FourValueMetrics(
            theoretical_top_of_book_usd=round(tob_usd, 6),
            executable_l2_net_usd=round(exec_l2_usd, 6),
            attainable_risk_adjusted_usd=round(att_usd, 6),
            realized_net_usd=0.0,  # Strictly 0.0 in Modes 1 & 2 (never conflated with live wallet cash)
        )

        denom_dollar_hr = max(1e-6, cost_bd.capital_required_usd * max(0.05, cost_bd.worst_case_lockup_hours))
        cap_eff_bps_hr = (
            round((exec_l2_usd / denom_dollar_hr) * 10_000.0, 4)
            if (exec_l2_usd > 0.0 and cost_bd.capital_required_usd > 0.0)
            else 0.0
        )

        if opp_class in (OpportunityClass.CLASS_D, OpportunityClass.CLASS_E):
            mode_cap = "MODE_1_RESEARCH"
        elif d007_quarantine or opp_class == OpportunityClass.CLASS_C:
            mode_cap = "MODE_2_SHADOW"
        else:
            mode_cap = "MODE_2_SHADOW_ELIGIBLE_FOR_PROPOSAL"

        dedup_disq = tuple(dict.fromkeys(disqualifiers))
        dedup_risks = tuple(dict.fromkeys(residual_risks))
        dedup_cex = tuple(dict.fromkeys(counterexamples))

        digest_input = {
            "candidate_id": candidate.candidate_id,
            "family": candidate.family,
            "opportunity_class": opp_class.value,
            "optimal_executable_quantity": round(opt_q, 6),
            "min_state_net_payoff_usd": round(min_net, 6),
            "expected_net_payoff_usd": round(ev_net, 6),
            "worst_state_id": worst_id,
            "four_value_ledger": asdict(four_vals),
            "cost_breakdown": asdict(cost_bd),
            "disqualifiers": dedup_disq,
        }
        proof_hash = self._compute_canonical_sha256(digest_input)

        return ArbitrageProofObject(
            candidate_id=candidate.candidate_id,
            family=candidate.family,
            opportunity_class=opp_class.value,
            is_mathematically_proven_arb=opp_class in (OpportunityClass.CLASS_A, OpportunityClass.CLASS_B),
            is_atomic_or_prelocked=is_atomic_or_prelocked and opp_class == OpportunityClass.CLASS_A,
            d007_sub500_multileg_quarantine=d007_quarantine,
            execution_mode_cap=mode_cap,
            optimal_executable_quantity=round(opt_q, 6),
            gross_top_of_book_edge_per_unit=gross_tob_edge_unit,
            net_executable_edge_per_unit=net_unit_edge,
            min_state_net_payoff_usd=round(min_net, 6),
            max_state_net_payoff_usd=round(max_net, 6),
            expected_net_payoff_usd=round(ev_net, 6),
            worst_state_id=worst_id,
            capital_efficiency_bps_per_hr=cap_eff_bps_hr,
            four_value_ledger=four_vals,
            cost_breakdown=cost_bd,
            state_payoffs=st_tuple,
            leg_executions=leg_tuple,
            counterexample_states=dedup_cex,
            disqualifiers=dedup_disq,
            residual_risks=dedup_risks,
            proof_sha256=proof_hash,
        )

    # -----------------------------------------------------------------------
    # High-Level Convenience Verifiers for Families A .. N
    # -----------------------------------------------------------------------

    def verify_binary_complete_set(
        self,
        *,
        candidate_id: str,
        yes_book: InstrumentOrderBook,
        no_book: InstrumentOrderBook,
        direction: str = "BUY_AND_MERGE",
        merge_immediately: bool = True,
        gas_cost_usd: float = 0.0,
        expected_lockup_hours: float = 0.02,
        worst_case_lockup_hours: float = 0.05,
    ) -> ArbitrageProofObject:
        """Evaluates Family A Binary Complete-Set (`BUY_AND_MERGE` or `SPLIT_AND_SELL`)."""
        yid, nid = yes_book.instrument_id, no_book.instrument_id
        dir_u = str(direction or "BUY_AND_MERGE").strip().upper()
        states = StateSpaceBuilder.binary_complete_set_states(yid, nid, include_void_50_50=True)
        if dir_u == "SPLIT_AND_SELL":
            legs: Tuple[ActionLeg, ...] = (
                ActionLeg(
                    action_type=ActionType.CTF_SPLIT,
                    related_instrument_ids=(yid, nid),
                    gas_cost_usd=gas_cost_usd,
                    market_id=yes_book.market_id,
                ),
                ActionLeg(action_type=ActionType.SELL_CLOB, instrument_id=yid, market_id=yes_book.market_id),
                ActionLeg(action_type=ActionType.SELL_CLOB, instrument_id=nid, market_id=no_book.market_id),
            )
        else:
            leg_list = [
                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=yid, market_id=yes_book.market_id),
                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=nid, market_id=no_book.market_id),
            ]
            if merge_immediately:
                leg_list.append(
                    ActionLeg(
                        action_type=ActionType.CTF_MERGE,
                        related_instrument_ids=(yid, nid),
                        gas_cost_usd=gas_cost_usd,
                        market_id=yes_book.market_id,
                    )
                )
            legs = tuple(leg_list)

        cand = CandidateStructure(
            candidate_id=candidate_id,
            family="A",
            legs=legs,
            states=states,
            rule_verified=True,
            expected_lockup_hours=expected_lockup_hours,
            worst_case_lockup_hours=worst_case_lockup_hours,
        )
        return self.verify_and_simulate(cand, {yid: yes_book, nid: no_book})

    def verify_logical_implication_pair(
        self,
        *,
        candidate_id: str,
        family: str,
        yes_book_a: InstrumentOrderBook,
        no_book_a: InstrumentOrderBook,
        yes_book_b: InstrumentOrderBook,
        no_book_b: InstrumentOrderBook,
        relation: str = "A_IMPLIES_B",
        buy_legs: Optional[Sequence[Tuple[str, float]]] = None,
        rule_verified: bool = True,
        rule_disqualifiers: Sequence[str] = (),
        cancel_rule_a: str = "50_50",
        cancel_rule_b: str = "50_50",
        has_overtime_mismatch: bool = False,
        touch_vs_close_mismatch: bool = False,
        timezone_mismatch: bool = False,
        oracle_mismatch: bool = False,
        expected_lockup_hours: float = 12.0,
        worst_case_lockup_hours: float = 48.0,
    ) -> ArbitrageProofObject:
        """
        Evaluates 2-market logical / deadline / strike / sports / duplicate structures (`Families D..I`).
        Defaults `buy_legs` to `(NO_A, 1.0), (YES_B, 1.0)` for `A_IMPLIES_B`, `(NO_A, 1.0), (NO_B, 1.0)` for `MUTUAL_EXCLUSION`.
        """
        ya, na = yes_book_a.instrument_id, no_book_a.instrument_id
        yb, nb = yes_book_b.instrument_id, no_book_b.instrument_id
        rel_u = str(relation or "A_IMPLIES_B").strip().upper()
        states = StateSpaceBuilder.two_market_logical_states(
            ya,
            na,
            yb,
            nb,
            relation=rel_u,
            cancel_rule_a=cancel_rule_a,
            cancel_rule_b=cancel_rule_b,
            has_overtime_mismatch=has_overtime_mismatch,
            touch_vs_close_mismatch=touch_vs_close_mismatch,
            timezone_mismatch=timezone_mismatch,
            oracle_mismatch=oracle_mismatch,
        )
        if buy_legs is None:
            if rel_u in {"MUTUAL_EXCLUSION", "DISJOINT"}:
                chosen_buys = [(na, 1.0), (nb, 1.0)]
            elif rel_u == "B_IMPLIES_A":
                chosen_buys = [(ya, 1.0), (nb, 1.0)]
            else:
                chosen_buys = [(na, 1.0), (yb, 1.0)]
        else:
            chosen_buys = list(buy_legs)

        all_books = {ya: yes_book_a, na: no_book_a, yb: yes_book_b, nb: no_book_b}
        legs = tuple(
            ActionLeg(
                action_type=ActionType.BUY_CLOB,
                instrument_id=tid,
                weight=float(wt),
                market_id=all_books[tid].market_id if tid in all_books else "",
            )
            for tid, wt in chosen_buys
        )
        eff_rule_ok = bool(
            rule_verified
            and not has_overtime_mismatch
            and not touch_vs_close_mismatch
            and not timezone_mismatch
            and not oracle_mismatch
            and not rule_disqualifiers
        )
        disq = list(rule_disqualifiers)
        if has_overtime_mismatch:
            disq.append("SPORTS_REGULATION_VS_OVERTIME_MISMATCH")
        if touch_vs_close_mismatch:
            disq.append("STRIKE_TOUCH_ANYTIME_VS_CLOSE_MISMATCH")
        if timezone_mismatch:
            disq.append("DEADLINE_TIMEZONE_MISMATCH")
        if oracle_mismatch:
            disq.append("REFERENCE_ORACLE_MISMATCH")

        cand = CandidateStructure(
            candidate_id=candidate_id,
            family=family,
            legs=legs,
            states=states,
            rule_verified=eff_rule_ok,
            rule_disqualifiers=tuple(disq),
            expected_lockup_hours=expected_lockup_hours,
            worst_case_lockup_hours=worst_case_lockup_hours,
        )
        return self.verify_and_simulate(cand, all_books)

    def verify_inventory_completion(
        self,
        *,
        candidate_id: str,
        holding: InventoryHolding,
        held_book: InstrumentOrderBook,
        complement_book: InstrumentOrderBook,
        merge_immediately: bool = True,
        gas_cost_usd: float = 0.0,
    ) -> ArbitrageProofObject:
        """
        Evaluates Family J pre-held inventory completion (`USE_INVENTORY` + 1-leg FOK `BUY_CLOB` + `CTF_MERGE`).
        Automatically enforces `D-001` frozen `KMIA` non-interference (`CLASS_E` veto if disputed).
        """
        hid = holding.instrument_id
        cid = complement_book.instrument_id
        states = StateSpaceBuilder.binary_complete_set_states(hid, cid, include_void_50_50=True)
        leg_list = [
            ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=hid, market_id=holding.market_id),
            ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=cid, market_id=complement_book.market_id),
        ]
        if merge_immediately:
            leg_list.append(
                ActionLeg(
                    action_type=ActionType.CTF_MERGE,
                    related_instrument_ids=(hid, cid),
                    gas_cost_usd=gas_cost_usd,
                    market_id=holding.market_id,
                )
            )
        cand = CandidateStructure(
            candidate_id=candidate_id,
            family="J",
            legs=tuple(leg_list),
            states=states,
            rule_verified=True,
            expected_lockup_hours=0.02 if merge_immediately else 2.0,
            worst_case_lockup_hours=0.05 if merge_immediately else 4.0,
        )
        return self.verify_and_simulate(
            cand,
            {hid: held_book, cid: complement_book},
            holdings={hid: holding},
        )

    def verify_uma_carry(
        self,
        *,
        candidate_id: str,
        book: InstrumentOrderBook,
        uma_status: str = "proposed",
        p_dispute_flip: float = 0.02,
        expected_lockup_hours: float = 2.0,
        dispute_lockup_hours: float = 168.0,
    ) -> ArbitrageProofObject:
        """
        Evaluates Family K near-resolution / UMA Optimistic Oracle carry.
        Strictly flags unfinalized `proposed` status as `uma_proposal_unfinalized=True` (`CLASS_C`, never `CLASS_A/B`).
        """
        tid = book.instrument_id
        st_l = str(uma_status or "proposed").strip().lower()
        states = StateSpaceBuilder.uma_carry_states(
            tid,
            uma_status=st_l,
            p_dispute_flip=p_dispute_flip,
            expected_lockup_hours=expected_lockup_hours,
            dispute_lockup_hours=dispute_lockup_hours,
        )
        cand = CandidateStructure(
            candidate_id=candidate_id,
            family="K",
            legs=(ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=tid, market_id=book.market_id),),
            states=states,
            rule_verified=(st_l != "disputed"),
            rule_disqualifiers=("UMA_ALREADY_DISPUTED",) if st_l == "disputed" else (),
            uma_proposal_unfinalized=(st_l != "resolved_onchain_final"),
            expected_lockup_hours=expected_lockup_hours,
            worst_case_lockup_hours=dispute_lockup_hours if st_l != "resolved_onchain_final" else 0.1,
        )
        return self.verify_and_simulate(cand, {tid: book})


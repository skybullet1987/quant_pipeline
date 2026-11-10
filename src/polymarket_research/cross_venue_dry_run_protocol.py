"""
Offline Dry-Run Cross-Venue Protocol Precision, Safety Guards & Ontario-Compliant Math
(`src/polymarket_research/cross_venue_dry_run_protocol.py`).

Strictly `DRY_RUN_ONLY = True` (`0` live order-submission routes, `0` private keys, `0` venue secrets).
Enforces `P0 Gate 0` operator jurisdiction rules programmatically and implements:
  1. `verify_p0_gate_0_jurisdiction`: Hard-blocks non-dry-run activation on restricted venues
     (e.g., `CA-ON` restricted on `polymarket`, `predict_fun`, `sx_bet`, `limitless`;
     explicitly permitted on Ontario-licensed `forecastex` via IBKR Canada and `stx_ontario`).
  2. `quantize_predict_1e18_order_amounts`: Exact `Decimal` `10^18`-wei `makerAmount` / `takerAmount`
     and `FeeModuleV2` (`BaseFee * min(p, 1 - p) * C`) integer quantization with zero float drift.
  3. `JWTExpiryGuard`: Deterministic `23h` (`82,800s`) rotation schedule tracker ahead of `24h` expiry.
  4. `evaluate_venus_vusdt_liquidity_guard`: Blocks yield-bearing collateral exposure when Venus
     `vUSDT` utilization exceeds `85%` or underlying cash drops below `15%` / `10x` clip size.
  5. `verify_relay_rebalance_quote`: Enforces recipient address identity, `<= 8.0 bps` all-in
     drag ceiling, and `>= 3.0x` expected arbitrage gain-to-bridge-cost hurdle.
  6. `evaluate_forecastex_coupon_bond_carry`: Exact `BOND1` carry & `3.38%` APY daily incentive
     coupon calculator for CIRO-regulated ForecastEx contracts (Interactive Brokers Canada).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Dict, FrozenSet, Optional

from src.polymarket_research.cross_venue_riskless_shadow import forecastex_taker_fee_usd

DRY_RUN_ONLY: bool = True
WEI_1E18 = Decimal("1000000000000000000")
USDC_1E6 = Decimal("1000000")

# Explicit P0 Gate 0 jurisdiction matrix (ISO-3166-2 / ISO-3166-1 codes)
ONTARIO_RESTRICTED_VENUES: FrozenSet[str] = frozenset({
    "polymarket",
    "predict_fun",
    "sx_bet",
    "limitless",
})

ONTARIO_LICENSED_VENUES: FrozenSet[str] = frozenset({
    "forecastex",
    "stx_ontario",
    "pinnacle_ontario",
})


class P0Gate0ComplianceError(PermissionError):
    """Raised when operator jurisdiction is prohibited by venue Terms of Service / regulation."""


def verify_p0_gate_0_jurisdiction(
    venue: str,
    operator_jurisdiction: str,
    *,
    dry_run: bool = True,
) -> bool:
    """
    Enforces `P0 Gate 0` operator eligibility before any non-dry-run initialization.
    Blocks `CA-ON` (Ontario) on `polymarket`, `predict_fun`, `sx_bet`, and `limitless`
    whenever `dry_run=False`, while allowing CIRO/AGCO-licensed `forecastex` and `stx_ontario`.
    """
    v_norm = (venue or "").strip().lower()
    j_norm = (operator_jurisdiction or "").strip().upper()
    if not v_norm or not j_norm:
        raise P0Gate0ComplianceError("venue and operator_jurisdiction must be explicitly specified")
    if dry_run:
        return True
    if j_norm in {"CA-ON", "ONTARIO", "CA_ON"}:
        if v_norm in ONTARIO_LICENSED_VENUES:
            return True
        if v_norm in ONTARIO_RESTRICTED_VENUES:
            raise P0Gate0ComplianceError(
                f"P0_GATE_0_BLOCKED: venue '{v_norm}' prohibits operator jurisdiction '{j_norm}'. "
                f"Use Ontario-licensed venues {sorted(ONTARIO_LICENSED_VENUES)} or stay strictly offline."
            )
    return True


@dataclass(frozen=True)
class Quantized1e18OrderSpec:
    side: str
    shares_1e18: int
    price_tick: Decimal
    maker_amount_wei: int
    taker_amount_wei: int
    fee_rate_bps: int
    taker_fee_wei: int
    maker_fee_wei: int


def quantize_predict_1e18_order_amounts(
    *,
    side: str,
    shares: float | Decimal,
    price: float | Decimal,
    fee_rate_bps: int = 200,
    invite_discount: bool = True,
    tick_size: str | Decimal = Decimal("0.001"),
) -> Quantized1e18OrderSpec:
    """
    Exact `Decimal` `10^18`-wei integer order quantizer for `FeeModuleV2` (`0%` maker,
    `BaseFee * min(p, 1 - p) * shares` taker linear tent). Zero binary float drift.
    """
    s_up = (side or "").strip().upper()
    if s_up not in {"BUY", "SELL"}:
        raise ValueError(f"Unsupported side: {side!r}")
    tk = Decimal(str(tick_size))
    p_raw = Decimal(str(price))
    sh_raw = Decimal(str(shares))
    if not (Decimal("0") < p_raw < Decimal("1")):
        raise ValueError(f"Price {price} must lie strictly inside (0, 1)")
    if sh_raw <= Decimal("0"):
        raise ValueError(f"Shares {shares} must be positive")

    p_q = (p_raw / tk).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tk
    if not (Decimal("0") < p_q < Decimal("1")):
        raise ValueError(f"Quantized price {p_q} out of bounds")

    shares_wei = int((sh_raw * WEI_1E18).to_integral_value(rounding=ROUND_DOWN))
    collateral_wei = int((Decimal(shares_wei) * p_q).to_integral_value(rounding=ROUND_HALF_UP))

    if s_up == "BUY":
        maker_amt = collateral_wei
        taker_amt = shares_wei
    else:
        maker_amt = shares_wei
        taker_amt = collateral_wei

    base_rate = Decimal(int(fee_rate_bps)) / Decimal("10000")
    if invite_discount:
        base_rate = base_rate * Decimal("0.90")
    min_p = p_q if p_q <= (Decimal("1") - p_q) else (Decimal("1") - p_q)
    taker_fee_wei = int((Decimal(shares_wei) * base_rate * min_p).to_integral_value(rounding=ROUND_HALF_UP))

    return Quantized1e18OrderSpec(
        side=s_up,
        shares_1e18=shares_wei,
        price_tick=p_q,
        maker_amount_wei=maker_amt,
        taker_amount_wei=taker_amt,
        fee_rate_bps=int(fee_rate_bps),
        taker_fee_wei=max(0, taker_fee_wei),
        maker_fee_wei=0,
    )


class JWTExpiryGuard:
    """
    Deterministic `23h` (`82,800s`) rotation tracker ahead of `24h` (`86,400s`) token expiry
    so rotated dry-run/session tokens never hit mid-cycle `HTTP 401` expirations.
    """

    DEFAULT_TTL_SEC: float = 86_400.0
    ROTATION_MARGIN_SEC: float = 3_600.0  # Rotate at 23.0h (1h safety margin)

    def __init__(self, issued_at_ts: Optional[float] = None, ttl_sec: float = DEFAULT_TTL_SEC) -> None:
        self.issued_at_ts: Optional[float] = float(issued_at_ts) if issued_at_ts is not None else None
        self.ttl_sec: float = max(300.0, float(ttl_sec))

    def record_issued(self, now_ts: float) -> None:
        self.issued_at_ts = float(now_ts)

    def needs_rotation(self, now_ts: float) -> bool:
        if self.issued_at_ts is None:
            return True
        elapsed = float(now_ts) - self.issued_at_ts
        rotate_after = max(60.0, self.ttl_sec - self.ROTATION_MARGIN_SEC)
        return elapsed >= rotate_after


@dataclass(frozen=True)
class VenusLiquidityVerdict:
    safe_for_yield_collateral: bool
    utilization_ratio: float
    cash_ratio: float
    available_cash_usd: float
    reason: str


def evaluate_venus_vusdt_liquidity_guard(
    *,
    total_cash_usd: float,
    total_borrows_usd: float,
    clip_notional_usd: float,
    max_utilization: float = 0.85,
    min_cash_ratio: float = 0.15,
    min_cash_clip_multiple: float = 10.0,
) -> VenusLiquidityVerdict:
    """
    Guards against lending-pool utilization freezes on yield-bearing collateral markets:
      - Rejects if `utilization = borrows / (cash + borrows) > 85%`
      - Rejects if `cash_ratio < 15%` or `cash < 10x clip_notional_usd`
    """
    cash = max(0.0, float(total_cash_usd))
    borrows = max(0.0, float(total_borrows_usd))
    clip = max(1.0, float(clip_notional_usd))
    pool = cash + borrows
    if pool <= 0.0:
        return VenusLiquidityVerdict(False, 1.0, 0.0, 0.0, "EMPTY_LENDING_POOL")
    util = borrows / pool
    cash_ratio = cash / pool
    if util > float(max_utilization):
        return VenusLiquidityVerdict(False, round(util, 6), round(cash_ratio, 6), cash, "UTILIZATION_ABOVE_85PCT")
    if cash_ratio < float(min_cash_ratio):
        return VenusLiquidityVerdict(False, round(util, 6), round(cash_ratio, 6), cash, "CASH_RATIO_BELOW_15PCT")
    if cash < clip * float(min_cash_clip_multiple):
        return VenusLiquidityVerdict(False, round(util, 6), round(cash_ratio, 6), cash, "INSUFFICIENT_CASH_MULTIPLE")
    return VenusLiquidityVerdict(True, round(util, 6), round(cash_ratio, 6), cash, "OK")


@dataclass(frozen=True)
class RelayQuoteVerdict:
    approved: bool
    all_in_drag_bps: float
    total_cost_usd: float
    reason: str


def verify_relay_rebalance_quote(
    *,
    amount_in_usd: float,
    amount_out_usd: float,
    origin_gas_usd: float,
    expected_recipient: str,
    quoted_recipient: str,
    expected_arb_gain_usd: float,
    max_drag_bps: float = 8.0,
    min_gain_to_cost_multiple: float = 3.0,
) -> RelayQuoteVerdict:
    """
    Validates a cross-L2 rebalance quote before treasury movement:
      1. Exact case-insensitive EVM recipient match (anti-spoofing guard).
      2. All-in bridge + origin gas drag `<= 8.0 bps`.
      3. Expected pure-riskless capture `>= 3.0x` total bridge cost.
    """
    exp_r = (expected_recipient or "").strip().lower()
    got_r = (quoted_recipient or "").strip().lower()
    if not exp_r or exp_r != got_r:
        return RelayQuoteVerdict(False, 10_000.0, 0.0, "RECIPIENT_MISMATCH")
    amt_in = float(amount_in_usd)
    amt_out = float(amount_out_usd)
    gas = max(0.0, float(origin_gas_usd))
    if amt_in <= 0.0 or amt_out <= 0.0 or amt_out > amt_in:
        return RelayQuoteVerdict(False, 10_000.0, 0.0, "INVALID_QUOTE_AMOUNTS")
    total_cost = (amt_in - amt_out) + gas
    drag_bps = (total_cost / amt_in) * 10_000.0
    if drag_bps > float(max_drag_bps):
        return RelayQuoteVerdict(False, round(drag_bps, 4), round(total_cost, 6), "BRIDGE_DRAG_EXCEEDS_MAX_BPS")
    if float(expected_arb_gain_usd) < total_cost * float(min_gain_to_cost_multiple):
        return RelayQuoteVerdict(False, round(drag_bps, 4), round(total_cost, 6), "GAIN_BELOW_3X_BRIDGE_COST")
    return RelayQuoteVerdict(True, round(drag_bps, 4), round(total_cost, 6), "OK")


def evaluate_forecastex_coupon_bond_carry(
    *,
    shares: float,
    entry_price: float,
    hold_days: float,
    annual_coupon_apy: float = 0.0338,
    fee_per_contract_usd: float = 0.01,
) -> Dict[str, float | bool]:
    """
    Computes guaranteed terminal net profit on a deterministically clinched CIRO-regulated
    ForecastEx binary contract (`$1.00` par + `3.38%` APY daily incentive coupon on settled value).
    """
    sh = max(0.0, float(shares))
    px = float(entry_price)
    days = max(0.0, float(hold_days))
    gross_cost = sh * px
    fee_usd = forecastex_taker_fee_usd(sh, px, fee_per_contract_usd=fee_per_contract_usd)
    coupon_usd = gross_cost * float(annual_coupon_apy) * (days / 365.0)
    guaranteed_payout = sh * 1.0
    net_profit = guaranteed_payout + coupon_usd - gross_cost - fee_usd
    total_outlay = gross_cost + fee_usd
    net_bps = (net_profit / total_outlay * 10_000.0) if total_outlay > 0.0 else 0.0
    return {
        "pure_riskless_profitable": net_profit > 0.0,
        "gross_cost_usd": round(gross_cost, 4),
        "fee_usd": round(fee_usd, 4),
        "coupon_usd": round(coupon_usd, 4),
        "net_profit_usd": round(net_profit, 4),
        "net_edge_bps": round(net_bps, 2),
    }

#!/usr/bin/env python3
"""
Polymarket Directional Alpha — Market Microstructure & Execution Economics Engine
=================================================================================
Pure-Python, zero-credential, deterministic execution & transaction-cost simulation module
calibrated on 338 live two-sided Polymarket L2 order books (435 active contracts sampled across
all categories), live Protocol V2 dynamic fee schedules (`15/15` `/clob-markets` <-> Gamma parity),
and live `kraken-finland` (`europe-north1` -> Cloudflare `ARN` -> AWS `eu-west-2`) vs North America RTTs.

Core Invariants Enforced (Red-Team RT-02, RT-03, RT-08, RT-09 Compliant):
  1. Zero-Cost Midpoint Fill Prohibition (RT-02): Historical `/prices-history` backtests NEVER fill
     at frictionless midpoints; every Taker trade pays at minimum calibrated half-spread (`>= 0.5` tick)
     + concave L2 depth impact + stale-quote/latency drift + exact curved V2 taker fee.
  2. Exact Protocol V2 Dynamic Fee & Sentinel Handling (RT-03): Correctly resolves `base_fee == 1000`
     as Polymarket V2's curved-fee sentinel (`fee_ps = rate * (p * (1 - p)) ** exponent`) across all
     11 active category fee schedules (`crypto_fees_v2` 0.07, `sports_fees_v3` 0.05, `politics_fees` 0.04,
     `economics_fees` 0.05, `finance_prices_fees` 0.04, `tech_fees` 0.04, `culture_fees` 0.05,
     `weather_fees` 0.05, `sports_fees_v2` 0.03, etc.) vs genuine `0%`-fee (`feesEnabled == False`).
     Passive `postOnly=True` Makers pay `0.0` taker fee and assume `$0.00` rebate credit by default
     (`rebate_realization_haircut = 1.0`) unless explicitly sensitivity-tested.
  3. Passive Maker Queue & Adverse Selection (RT-02): Models FIFO queue depth ahead, `postOnly`
     cross rejection, partial fills, event spread-widening liquidity evaporation, and Glosten-Milgrom
     toxic-flow adverse selection (passive fills occur disproportionately when true probability moves
     THROUGH the resting quote).
  4. CLOB Lot-Size Quantization & Account-Scale Capacity (RT-09): Enforces `5.0`-share minimum lot,
     `$1.00` minimum marketable notional, 2-decimal USDC `makerAmount` quantization, and explicit
     distortion/capacity diagnostics across `$48.81` (Dominus actual cash), `$500`, and `$5,000+` tiers.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import orjson as _orjson
except ImportError:  # pragma: no cover
    _orjson = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CALIBRATION_PATH = REPO_ROOT / "data" / "directional_alpha" / "microstructure_calibration.json"

MIN_CLOB_ORDER_SHARES: float = 5.0
MIN_CLOB_MARKETABLE_NOTIONAL_USD: float = 1.00
CLOB_ALLOWED_TICK_SIZES: Tuple[float, ...] = (0.1, 0.01, 0.005, 0.0025, 0.001, 0.0001)
SUBHOURLY_ITODE_SPEEDBUMP_MS: float = 200.0
KRAKEN_FINLAND_CLOB_P50_MS: float = 56.48
KRAKEN_FINLAND_BOOK_P50_MS: float = 48.48
WINDOWS_NA_CLOB_P50_MS: float = 118.79
DOMINUS_DAILY_VM_BURN_USD: float = 0.822  # ~$24.67/month GCE e2-medium in europe-north1-b

# Empirically verified Polymarket Protocol V2 fee schedules (2026-11-12 live audit)
V2_FEE_SCHEDULES: Dict[str, Dict[str, Any]] = {
    "crypto_fees_v2": {"rate": 0.07, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.20},
    "crypto_fees": {"rate": 0.07, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.20},
    "sports_fees_v3": {"rate": 0.05, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.15},
    "sports_fees_v2": {"rate": 0.03, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "sports_fees": {"rate": 0.03, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.20},
    "sports_fees_nfl_cfb_oct26": {"rate": 0.03, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.15},
    "politics_fees": {"rate": 0.04, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "mentions_fees": {"rate": 0.04, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "economics_fees": {"rate": 0.05, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "finance_prices_fees": {"rate": 0.04, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "finance_fees": {"rate": 0.04, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "tech_fees": {"rate": 0.04, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "culture_fees": {"rate": 0.05, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "weather_fees": {"rate": 0.05, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "geopolitics_fees": {"rate": 0.04, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "general_fees": {"rate": 0.05, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.25},
    "zero_fee": {"rate": 0.00, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.00},
    "zero_fees": {"rate": 0.00, "exponent": 1.0, "taker_only": True, "rebate_rate": 0.00},
}

CATEGORY_DEFAULT_FEE_TYPE: Dict[str, str] = {
    "crypto": "crypto_fees_v2",
    "sports": "sports_fees_v3",
    "politics": "politics_fees",
    "economics": "economics_fees",
    "macro": "economics_fees",
    "finance": "finance_prices_fees",
    "tech": "tech_fees",
    "culture": "culture_fees",
    "entertainment": "culture_fees",
    "weather": "weather_fees",
    "geopolitics": "general_fees",  # Note: legacy geopolitics often has feesEnabled=False, checked first!
    "science": "general_fees",
    "other": "general_fees",
}

# Embedded empirical priors fitted from 338 live two-sided Polymarket L2 books (2026-11-12)
# Used seamlessly if calibration JSON is absent in isolated unit-test environments.
EMPIRICAL_CATEGORY_PRIORS: Dict[str, Dict[str, float]] = {
    "crypto": {"spread_c_p50": 0.70, "spread_c_p75": 1.02, "l1_usd_p50": 5.50, "d5c_usd_p50": 498.6, "arrival_hz": 0.14},
    "sports": {"spread_c_p50": 1.00, "spread_c_p75": 1.00, "l1_usd_p50": 1134.40, "d5c_usd_p50": 24670.7, "arrival_hz": 0.11},
    "politics": {"spread_c_p50": 0.30, "spread_c_p75": 0.85, "l1_usd_p50": 76.80, "d5c_usd_p50": 4920.8, "arrival_hz": 0.07},
    "economics": {"spread_c_p50": 0.50, "spread_c_p75": 2.08, "l1_usd_p50": 22.00, "d5c_usd_p50": 239.3, "arrival_hz": 0.05},
    "finance": {"spread_c_p50": 1.90, "spread_c_p75": 3.17, "l1_usd_p50": 9.70, "d5c_usd_p50": 517.6, "arrival_hz": 0.05},
    "weather": {"spread_c_p50": 1.00, "spread_c_p75": 1.25, "l1_usd_p50": 12.00, "d5c_usd_p50": 263.5, "arrival_hz": 0.04},
    "geopolitics": {"spread_c_p50": 1.00, "spread_c_p75": 1.15, "l1_usd_p50": 42.60, "d5c_usd_p50": 2955.1, "arrival_hz": 0.06},
    "tech": {"spread_c_p50": 1.55, "spread_c_p75": 2.77, "l1_usd_p50": 34.50, "d5c_usd_p50": 554.3, "arrival_hz": 0.05},
    "culture": {"spread_c_p50": 1.10, "spread_c_p75": 2.70, "l1_usd_p50": 9.40, "d5c_usd_p50": 139.6, "arrival_hz": 0.04},
    "other": {"spread_c_p50": 1.00, "spread_c_p75": 1.90, "l1_usd_p50": 29.25, "d5c_usd_p50": 1040.4, "arrival_hz": 0.05},
}

EMPIRICAL_LIQUIDITY_TIER_PRIORS: Dict[str, Dict[str, float]] = {
    "LOW": {"spread_c_p50": 2.00, "spread_c_p75": 4.00, "l1_usd_p50": 8.13, "d5c_usd_p50": 127.28, "stale_c": 0.45},
    "MEDIUM": {"spread_c_p50": 1.00, "spread_c_p75": 2.00, "l1_usd_p50": 13.22, "d5c_usd_p50": 474.38, "stale_c": 0.25},
    "HIGH": {"spread_c_p50": 0.30, "spread_c_p75": 1.00, "l1_usd_p50": 88.49, "d5c_usd_p50": 2926.57, "stale_c": 0.12},
    "ULTRA": {"spread_c_p50": 0.25, "spread_c_p75": 1.00, "l1_usd_p50": 1159.97, "d5c_usd_p50": 36450.36, "stale_c": 0.06},
}

_CALIBRATION_CACHE: Dict[str, Dict[str, Any]] = {}


class _DictAccessMixin:
    """Allows callers to read dataclass fields either as attributes (`r.vwap_px`) or dict keys (`r['vwap_px']`)."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)


@dataclass(frozen=True)
class FeeSchedule(_DictAccessMixin):
    fee_type: str
    fee_rate: float
    fee_exponent: float
    taker_only: bool
    rebate_rate: float
    fees_enabled: bool
    intentional_taker_delay: bool = False
    source: str = "resolved"


@dataclass(frozen=True)
class LotValidationResult(_DictAccessMixin):
    eligible: bool
    reason: str
    desired_notional_usd: float
    quantized_shares: float
    quantized_notional_usd: float
    min_required_shares: float
    min_required_notional_usd: float
    lot_upsize_ratio: float
    lot_distortion_pct: float


@dataclass(frozen=True)
class TakerFillResult(_DictAccessMixin):
    fillable: bool
    reason: str
    side: str
    requested_notional_usd: float
    filled_shares: float
    gross_notional_usd: float
    mid_px: float
    best_touch_px: float
    vwap_px: float
    worst_px: float
    effective_exec_px_before_fee: float
    taker_fee_usd: float
    taker_fee_per_share: float
    taker_fee_bps_of_notional: float
    all_in_px_per_share: float
    all_in_cash_flow_usd: float  # Positive cash spent for BUY; positive net cash proceeds received for SELL
    half_spread_cost_usd: float
    depth_impact_cost_usd: float
    latency_and_stale_cost_usd: float
    total_friction_over_mid_usd: float
    total_friction_over_mid_bps: float
    levels_consumed: int
    data_quality_mode: str = "OBSERVED_L2"
    fill_legs: Tuple[Tuple[float, float], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MakerSimulationResult(_DictAccessMixin):
    accepted: bool
    crosses_book_rejected: bool
    reason: str
    side: str
    limit_price: float
    requested_shares: float
    requested_notional_usd: float
    improves_touch: bool
    queue_ahead_shares: float
    queue_ahead_usd: float
    fill_probability: float
    expected_fill_fraction: float
    expected_filled_shares: float
    deterministic_filled_shares: float
    maker_fee_usd: float
    assumed_rebate_usd: float
    theoretical_unhaircut_rebate_usd: float
    prior_fair_prob: float
    adverse_selection_prob_haircut: float
    post_fill_fair_prob: float
    expected_toxicity_cost_usd: float


def load_microstructure_calibration(calibration_path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads cached empirical calibration JSON (`data/directional_alpha/microstructure_calibration.json`)."""
    target = Path(calibration_path) if calibration_path is not None else DEFAULT_CALIBRATION_PATH
    key = str(target.resolve())
    if key in _CALIBRATION_CACHE:
        return _CALIBRATION_CACHE[key]
    if target.exists():
        try:
            raw_bytes = target.read_bytes()
            parsed = _orjson.loads(raw_bytes) if _orjson is not None else json.loads(raw_bytes.decode("utf-8"))
            if isinstance(parsed, dict):
                _CALIBRATION_CACHE[key] = parsed
                return parsed
        except Exception:
            pass
    fallback = {
        "schema_version": "1.0.0-embedded-fallback",
        "v2_fee_schedules": V2_FEE_SCHEDULES,
        "by_category": EMPIRICAL_CATEGORY_PRIORS,
        "by_liquidity_tier": EMPIRICAL_LIQUIDITY_TIER_PRIORS,
    }
    _CALIBRATION_CACHE[key] = fallback
    return fallback


def classify_liquidity_tier(liquidity_usd: float) -> str:
    liq = max(0.0, float(liquidity_usd or 0.0))
    if liq < 5000.0:
        return "LOW"
    if liq < 50000.0:
        return "MEDIUM"
    if liq < 250000.0:
        return "HIGH"
    return "ULTRA"


def normalize_category_name(raw_category: Optional[str], slug_or_question: str = "") -> str:
    s = f"{raw_category or ''} {slug_or_question}".strip().lower()
    if "weather" in s or "temperature" in s or "highest temp" in s or "hurricane" in s:
        return "weather"
    if "crypto" in s or any(k in s for k in ("bitcoin", "btc", "ethereum", "eth-", "solana", "xrp", "doge", "updown")):
        return "crypto"
    if "sport" in s or any(k in s for k in ("nba", "nfl", "nhl", "mlb", "ufc", "dota", "cs2", "soccer", "league", "tennis")):
        return "sports"
    if "econom" in s or "macro" in s or any(k in s for k in ("fed ", "fed-", "interest rate", "cpi", "inflation", "gdp", "recession", "tariff")):
        return "economics"
    if "financ" in s or any(k in s for k in ("s&p", "nasdaq", "market cap", "ipo", "earnings", "crude oil", "gold")):
        return "finance"
    if "tech" in s or any(k in s for k in ("openai", "gpt", "claude", "gemini", "nvidia", "apple", "spacex")):
        return "tech"
    if "geopolit" in s or any(k in s for k in ("ukraine", "russia", "ceasefire", "israel", "iran", "taiwan", "nato")):
        return "geopolitics"
    if "polit" in s or any(k in s for k in ("election", "president", "senate", "house", "governor", "parliament", "trump")):
        return "politics"
    if "cultur" in s or "entertain" in s or any(k in s for k in ("oscar", "grammy", "movie", "box office", "album")):
        return "culture"
    return "other"


# ==============================================================================
# 1. DYNAMIC V2 FEE RESOLUTION & EXACT FEE / REBATE CALCULATORS
# ==============================================================================

def resolve_fee_schedule(
    market_meta: Optional[Dict[str, Any]] = None,
    clob_market_info: Optional[Dict[str, Any]] = None,
    clob_fee_rate_resp: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    fees_enabled: Optional[bool] = None,
    conservative_unknown_fees: bool = True,
) -> FeeSchedule:
    """
    Resolves exact Polymarket V2 fee parameters (`rate`, `exponent`, `taker_only`, `rebate_rate`, `itode`).

    Handles all live Polymarket schemas without falling into the `base_fee == 1000` trap:
      1. Authoritative CLOB V2 `/clob-markets/<cid>`: `fd = {"r": rate, "e": exp, "to": True}`, `itode: bool`.
      2. Gamma Market dict: `feesEnabled: bool`, `feeType: str`, `feeSchedule: {"rate", "exponent", "takerOnly", "rebateRate"}`.
      3. CLOB `/fee-rate?token_id=...`: `{"base_fee": 0}` -> `0%` fee; `{"base_fee": 1000}` -> V2 curved sentinel
         (resolved via `feeType` / `category`, NEVER treated as 10% flat bps or 0% fee!).
    """
    meta = market_meta or {}
    cm = clob_market_info or {}
    fr_resp = clob_fee_rate_resp or {}

    slug_q = f"{meta.get('slug', '')} {meta.get('question', '')}".lower()
    is_subhourly = bool(cm.get("itode")) or any(
        tag in slug_q for tag in ("-5m-", "-15m-", "-1h-", "updown-5m", "updown-15m", "updown-1h")
    )

    # 1. Explicit CLOB V2 `/clob-markets/<condition_id>` `fd` block
    if isinstance(cm, dict) and ("c" in cm or "fd" in cm):
        fd = cm.get("fd")
        if isinstance(fd, dict) and fd.get("r") is not None:
            rate = max(0.0, float(fd.get("r") or 0.0))
            exp = max(0.5, float(fd.get("e") or 1.0))
            to_flag = bool(fd.get("to", True))
            ft = str(meta.get("feeType") or CATEGORY_DEFAULT_FEE_TYPE.get(normalize_category_name(category, slug_q), "general_fees"))
            rebate = float((meta.get("feeSchedule") or {}).get("rebateRate") or V2_FEE_SCHEDULES.get(ft, {}).get("rebate_rate", 0.20))
            return FeeSchedule(
                fee_type=ft if rate > 0 else "zero_fee",
                fee_rate=rate,
                fee_exponent=exp,
                taker_only=to_flag,
                rebate_rate=rebate if rate > 0 else 0.0,
                fees_enabled=rate > 0.0,
                intentional_taker_delay=is_subhourly,
                source="clob_markets_fd",
            )
        if "c" in cm and not fd:
            return FeeSchedule(
                fee_type="zero_fee",
                fee_rate=0.0,
                fee_exponent=1.0,
                taker_only=True,
                rebate_rate=0.0,
                fees_enabled=False,
                intentional_taker_delay=is_subhourly,
                source="clob_markets_no_fd",
            )

    # 2. Explicit Gamma `feesEnabled` + `feeSchedule` / `fee_rate` fields
    explicit_fe = fees_enabled if fees_enabled is not None else meta.get("feesEnabled", meta.get("fees_enabled"))
    if explicit_fe is False:
        return FeeSchedule(
            fee_type="zero_fee",
            fee_rate=0.0,
            fee_exponent=1.0,
            taker_only=True,
            rebate_rate=0.0,
            fees_enabled=False,
            intentional_taker_delay=is_subhourly,
            source="gamma_fees_disabled",
        )

    fs = meta.get("feeSchedule") or meta.get("fee_schedule")
    if isinstance(fs, dict) and fs.get("rate") is not None:
        rate = max(0.0, float(fs.get("rate") or 0.0))
        exp = max(0.5, float(fs.get("exponent") or 1.0))
        rebate = max(0.0, float(fs.get("rebateRate", fs.get("rebate_rate", 0.0)) or 0.0))
        ft = str(meta.get("feeType") or meta.get("fee_type") or ("zero_fee" if rate <= 0 else "gamma_schedule"))
        return FeeSchedule(
            fee_type=ft,
            fee_rate=rate,
            fee_exponent=exp,
            taker_only=bool(fs.get("takerOnly", True)),
            rebate_rate=rebate if rate > 0 else 0.0,
            fees_enabled=rate > 0.0,
            intentional_taker_delay=is_subhourly,
            source="gamma_fee_schedule",
        )

    if meta.get("fee_rate") is not None:
        rate = max(0.0, float(meta["fee_rate"]))
        exp = max(0.5, float(meta.get("fee_exponent") or 1.0))
        rebate = max(0.0, float(meta.get("rebate_rate") or 0.0))
        return FeeSchedule(
            fee_type=str(meta.get("fee_type") or ("zero_fee" if rate <= 0 else "explicit_rate")),
            fee_rate=rate,
            fee_exponent=exp,
            taker_only=True,
            rebate_rate=rebate,
            fees_enabled=rate > 0.0,
            intentional_taker_delay=is_subhourly,
            source="explicit_meta_rate",
        )

    ft_raw = str(meta.get("feeType") or meta.get("fee_type") or "").strip().lower()
    if ft_raw in V2_FEE_SCHEDULES:
        spec = V2_FEE_SCHEDULES[ft_raw]
        return FeeSchedule(
            fee_type=ft_raw,
            fee_rate=float(spec["rate"]),
            fee_exponent=float(spec["exponent"]),
            taker_only=bool(spec["taker_only"]),
            rebate_rate=float(spec["rebate_rate"]),
            fees_enabled=float(spec["rate"]) > 0.0,
            intentional_taker_delay=is_subhourly,
            source="fee_type_lookup",
        )
    if ft_raw.startswith("zero"):
        return FeeSchedule("zero_fees", 0.0, 1.0, True, 0.0, False, is_subhourly, "fee_type_zero_prefix")
    if ft_raw.startswith("sports_fees"):
        rate_s = 0.03 if ("v2" in ft_raw or "nfl" in ft_raw or "cfb" in ft_raw) else 0.05
        return FeeSchedule(ft_raw, rate_s, 1.0, True, 0.15, True, is_subhourly, "fee_type_sports_prefix")
    if ft_raw.startswith("crypto_fees"):
        return FeeSchedule(ft_raw, 0.07, 1.0, True, 0.20, True, is_subhourly, "fee_type_crypto_prefix")

    # 3. CLOB `/fee-rate` check (`base_fee == 0` vs `base_fee == 1000` V2 sentinel)
    if isinstance(fr_resp, dict) and "base_fee" in fr_resp:
        bf = float(fr_resp.get("base_fee") or 0.0)
        if bf <= 0.0 and explicit_fe is not True:
            return FeeSchedule(
                fee_type="zero_fee",
                fee_rate=0.0,
                fee_exponent=1.0,
                taker_only=True,
                rebate_rate=0.0,
                fees_enabled=False,
                intentional_taker_delay=is_subhourly,
                source="clob_fee_rate_zero",
            )
        # Note: bf == 1000 is the V2 curved-fee sentinel -> fall through to category V2 schedule
        # Only if bf is a genuine non-sentinel bps (e.g. 0 < bf < 500) convert bps -> decimal
        if 0.0 < bf < 500.0:
            return FeeSchedule(
                fee_type="clob_custom_bps",
                fee_rate=bf / 10000.0,
                fee_exponent=1.0,
                taker_only=True,
                rebate_rate=0.0,
                fees_enabled=True,
                intentional_taker_delay=is_subhourly,
                source="clob_fee_rate_bps",
            )

    # 4. Category-based fallback (fail-closed conservative when fee metadata is absent)
    norm_cat = normalize_category_name(category or meta.get("category"), slug_q)
    if explicit_fe is None and not conservative_unknown_fees:
        return FeeSchedule("zero_fee", 0.0, 1.0, True, 0.0, False, is_subhourly, "unverified_zero_override")

    default_ft = CATEGORY_DEFAULT_FEE_TYPE.get(norm_cat, "general_fees")
    spec = V2_FEE_SCHEDULES[default_ft]
    return FeeSchedule(
        fee_type=default_ft,
        fee_rate=float(spec["rate"]),
        fee_exponent=float(spec["exponent"]),
        taker_only=bool(spec["taker_only"]),
        rebate_rate=float(spec["rebate_rate"]),
        fees_enabled=True,
        intentional_taker_delay=is_subhourly,
        source="category_v2_fallback",
    )


def compute_taker_fee_per_share(
    price: float,
    fee_rate: float = 0.05,
    fee_exponent: float = 1.0,
) -> float:
    """
    Exact Polymarket Protocol V2 dynamic probability-curved taker fee per share:
      fee_per_share(p) = fee_rate * (p * (1 - p)) ** fee_exponent
    Peaks at p = 0.50 (`0.25 * fee_rate` for exponent = 1.0) and decays symmetrically toward
    `p -> 0` and `p -> 1`. Passive `postOnly=True` Makers pay `0.0`.
    """
    if not math.isfinite(price) or not math.isfinite(fee_rate) or fee_rate <= 0.0:
        return 0.0
    p = max(0.001, min(0.999, float(price)))
    exp = max(0.5, float(fee_exponent))
    return float(fee_rate) * ((p * (1.0 - p)) ** exp)


def compute_taker_fee_usd(
    notional_usd: float,
    price: float,
    fee_rate: float = 0.05,
    fee_exponent: float = 1.0,
) -> Tuple[float, float]:
    """
    Canonical BUY-side dynamic taker fee in USD for `notional_usd` spent at `price`:
      shares = notional_usd / p
      fee_usd = shares * fee_rate * (p * (1 - p)) ** fee_exponent
      (For exponent == 1.0, simplifies to `notional_usd * fee_rate * (1 - p)`.)
    Matches `src/polymarket_research/polymarket_live_executor.py:calculate_taker_fee` to 1e-5 USD.
    Returns: `(effective_rate_of_notional, fee_usd)`.
    """
    if notional_usd <= 0.0 or price <= 0.0 or fee_rate <= 0.0:
        return 0.0, 0.0
    clamped_p = max(0.001, min(0.999, float(price)))
    shares = float(notional_usd) / clamped_p
    per_share = compute_taker_fee_per_share(clamped_p, fee_rate, fee_exponent)
    fee_usd = float(Decimal(str(shares * per_share)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))
    eff_rate = round(fee_usd / max(float(notional_usd), 1e-9), 8)
    return eff_rate, fee_usd


def compute_sell_taker_fee_usd(
    shares: float,
    exit_price: float,
    fee_rate: float = 0.05,
    fee_exponent: float = 1.0,
) -> Tuple[float, float]:
    """
    Canonical SELL-side dynamic taker fee when selling `shares` into bids at `exit_price`.
    Returns: `(effective_rate_of_gross_proceeds, fee_usd)`.
    """
    if shares <= 0.0 or exit_price <= 0.0 or fee_rate <= 0.0:
        return 0.0, 0.0
    clamped_p = max(0.001, min(0.999, float(exit_price)))
    gross_proceeds = float(shares) * clamped_p
    per_share = compute_taker_fee_per_share(clamped_p, fee_rate, fee_exponent)
    fee_usd = float(Decimal(str(float(shares) * per_share)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))
    eff_rate = round(fee_usd / max(gross_proceeds, 1e-9), 8)
    return eff_rate, fee_usd


def compute_maker_rebate_usd(
    shares: float,
    price: float,
    fee_rate: float = 0.05,
    fee_exponent: float = 1.0,
    rebate_rate: float = 0.0,
    realization_haircut: float = 1.0,
) -> float:
    """
    Models Polymarket V2 Maker Fee Rebates (`rebateRate` = 15%–25% of counterparty taker fee pool).
    IMPORTANT (RT-03 Safety): `realization_haircut` defaults to `1.0` (`$0.00` assumed rebate)
    because daily pool payouts are pro-rata across market-wide maker volume rather than guaranteed
    inline on fill. Pass `realization_haircut < 1.0` ONLY in explicit rebate-sensitivity analyses.
    """
    if shares <= 0.0 or fee_rate <= 0.0 or rebate_rate <= 0.0:
        return 0.0
    keep_frac = max(0.0, min(1.0, 1.0 - float(realization_haircut)))
    if keep_frac <= 0.0:
        return 0.0
    counterparty_taker_fee = float(shares) * compute_taker_fee_per_share(price, fee_rate, fee_exponent)
    return round(counterparty_taker_fee * float(rebate_rate) * keep_frac, 6)


# ==============================================================================
# 2. TICK SIZE, LOT QUANTIZATION & ACCOUNT-SCALE CAPACITY CONSTRAINTS
# ==============================================================================

def resolve_tick_size(
    price: float,
    base_tick_size: float = 0.01,
    dynamic_extreme_tick: bool = True,
) -> float:
    """
    Resolves valid Polymarket CLOB tick size (`0.01` vs `0.001`, stepping to `0.001` near `<0.04` or `>0.96`).
    """
    bt = float(base_tick_size) if base_tick_size in CLOB_ALLOWED_TICK_SIZES else 0.01
    if dynamic_extreme_tick and bt > 0.001 and (price < 0.04 or price > 0.96):
        return 0.001
    return bt


def round_price_to_tick(price: float, tick_size: float = 0.01, mode: str = "nearest") -> float:
    """Rounds `price` onto the exact `tick_size` lattice within `[tick_size, 1.0 - tick_size]`."""
    tick = resolve_tick_size(price, tick_size, dynamic_extreme_tick=False)
    scaled = float(price) / tick
    if mode == "floor":
        steps = math.floor(scaled + 1e-9)
    elif mode == "ceil":
        steps = math.ceil(scaled - 1e-9)
    else:
        steps = round(scaled)
    min_steps = 1
    max_steps = int(round(1.0 / tick)) - 1
    clamped_steps = max(min_steps, min(max_steps, int(steps)))
    decimals = max(1, int(round(-math.log10(tick)))) if tick < 1.0 else 2
    return round(clamped_steps * tick, decimals)


def quantize_clob_leg_shares(
    shares: float,
    price: float,
    *,
    round_up: bool = False,
) -> float:
    """
    Exact Polymarket CLOB 2-decimal share & 2-decimal USDC `makerAmount = shares * price` quantizer
    (matches `quantize_fok_buy_leg_size` in `polymarket_live_executor.py`).
    """
    if shares <= 0.0 or price <= 0.0 or not (math.isfinite(shares) and math.isfinite(price)):
        return 0.0
    p_1e4 = max(1, int(round(float(price) * 10000)))
    s0 = 10000 // math.gcd(p_1e4, 10000)
    step_c = (s0 * 25) // math.gcd(s0, 25)
    if round_up:
        raw_c = int(math.ceil(float(shares) * 100.0 - 1e-9))
        q_c = ((raw_c + step_c - 1) // step_c) * step_c
    else:
        raw_c = int(math.floor(float(shares) * 100.0 + 1e-9))
        q_c = (raw_c // step_c) * step_c
    return round(q_c / 100.0, 2) if q_c > 0 else 0.0


def validate_and_quantize_order_lot(
    desired_notional_usd: float,
    price: float,
    *,
    min_order_shares: float = MIN_CLOB_ORDER_SHARES,
    min_order_notional_usd: float = MIN_CLOB_MARKETABLE_NOTIONAL_USD,
    tick_size: float = 0.01,
    exact_cent_maker_amount: bool = True,
    allow_lot_floor_upsize: bool = False,
    max_lot_upsize_ratio: float = 1.35,
) -> LotValidationResult:
    """
    Validates & quantizes an order against Polymarket CLOB minimums (`5.0` shares AND `$1.00` notional).
    Critical for small accounts (`$48.81`): if Kelly sizing asks for `$2.00` at `$0.80` (`2.5` shares),
    the `5.0`-share minimum requires `$4.00` (`2.0x` desired risk -> rejected unless `allow_lot_floor_upsize=True`
    and within `max_lot_upsize_ratio`).
    """
    if not (math.isfinite(desired_notional_usd) and math.isfinite(price)) or desired_notional_usd <= 0.0 or not (0.0 < price < 1.0):
        return LotValidationResult(False, "INVALID_NOTIONAL_OR_PRICE", 0.0, 0.0, 0.0, min_order_shares, min_order_notional_usd, 0.0, 0.0)

    px = round_price_to_tick(price, tick_size, mode="nearest")
    min_req_notional = max(float(min_order_notional_usd), float(min_order_shares) * px)
    raw_shares = float(desired_notional_usd) / px

    if raw_shares < float(min_order_shares) - 1e-9 or desired_notional_usd < float(min_order_notional_usd) - 1e-9:
        if not allow_lot_floor_upsize:
            return LotValidationResult(
                eligible=False,
                reason="BELOW_CLOB_MIN_LOT",
                desired_notional_usd=round(desired_notional_usd, 4),
                quantized_shares=0.0,
                quantized_notional_usd=0.0,
                min_required_shares=float(min_order_shares),
                min_required_notional_usd=round(min_req_notional, 4),
                lot_upsize_ratio=round(min_req_notional / max(desired_notional_usd, 1e-6), 4),
                lot_distortion_pct=round(((min_req_notional - desired_notional_usd) / max(desired_notional_usd, 1e-6)) * 100.0, 2),
            )
        target_shares = max(float(min_order_shares), float(min_order_notional_usd) / px)
        q_shares = quantize_clob_leg_shares(target_shares, px, round_up=True) if exact_cent_maker_amount else math.ceil(target_shares * 100.0) / 100.0
        q_notional = round(q_shares * px, 4)
        upsize_ratio = q_notional / max(desired_notional_usd, 1e-6)
        if upsize_ratio > float(max_lot_upsize_ratio) + 1e-9:
            return LotValidationResult(
                eligible=False,
                reason="MIN_LOT_UPSIZE_EXCEEDS_RISK_CAP",
                desired_notional_usd=round(desired_notional_usd, 4),
                quantized_shares=q_shares,
                quantized_notional_usd=q_notional,
                min_required_shares=float(min_order_shares),
                min_required_notional_usd=round(min_req_notional, 4),
                lot_upsize_ratio=round(upsize_ratio, 4),
                lot_distortion_pct=round((upsize_ratio - 1.0) * 100.0, 2),
            )
        return LotValidationResult(
            eligible=True,
            reason="UPSIZED_TO_MIN_LOT",
            desired_notional_usd=round(desired_notional_usd, 4),
            quantized_shares=q_shares,
            quantized_notional_usd=q_notional,
            min_required_shares=float(min_order_shares),
            min_required_notional_usd=round(min_req_notional, 4),
            lot_upsize_ratio=round(upsize_ratio, 4),
            lot_distortion_pct=round((upsize_ratio - 1.0) * 100.0, 2),
        )

    if exact_cent_maker_amount:
        q_shares = quantize_clob_leg_shares(raw_shares, px, round_up=False)
        if q_shares < float(min_order_shares) or (q_shares * px) < float(min_order_notional_usd) - 1e-9:
            q_shares_up = quantize_clob_leg_shares(max(float(min_order_shares), float(min_order_notional_usd) / px), px, round_up=True)
            if (q_shares_up * px) <= desired_notional_usd * float(max_lot_upsize_ratio):
                q_shares = q_shares_up
            else:
                return LotValidationResult(
                    eligible=False,
                    reason="QUANTIZATION_STEP_EXCEEDS_CAP",
                    desired_notional_usd=round(desired_notional_usd, 4),
                    quantized_shares=0.0,
                    quantized_notional_usd=0.0,
                    min_required_shares=float(min_order_shares),
                    min_required_notional_usd=round(min_req_notional, 4),
                    lot_upsize_ratio=round((q_shares_up * px) / desired_notional_usd, 4),
                    lot_distortion_pct=round(((q_shares_up * px - desired_notional_usd) / desired_notional_usd) * 100.0, 2),
                )
    else:
        q_shares = math.floor(raw_shares * 100.0 + 1e-9) / 100.0

    q_notional = round(q_shares * px, 4)
    distortion = ((q_notional - desired_notional_usd) / desired_notional_usd) * 100.0
    return LotValidationResult(
        eligible=True,
        reason="OK",
        desired_notional_usd=round(desired_notional_usd, 4),
        quantized_shares=q_shares,
        quantized_notional_usd=q_notional,
        min_required_shares=float(min_order_shares),
        min_required_notional_usd=round(min_req_notional, 4),
        lot_upsize_ratio=round(q_notional / desired_notional_usd, 4),
        lot_distortion_pct=round(distortion, 2),
    )


# ==============================================================================
# 3. EXACT L2 ORDERBOOK SWEEP & COMPLEMENT CONVERSION ENGINE
# ==============================================================================

def derive_complement_l2_book(orderbook: Dict[str, Any]) -> Dict[str, List[Dict[str, float]]]:
    """
    Derives the exact complementary binary token L2 orderbook (`NO` from `YES` or `YES` from `NO`)
    on single-collateral Polymarket CTF conditions (`YES + NO == $1.00`):
      - Complement `asks` = `[{"price": round(1 - bid_px, 6), "size": bid_sz} for bid in bids]`
      - Complement `bids` = `[{"price": round(1 - ask_px, 6), "size": ask_sz} for ask in asks]`
    """
    src_bids = _parse_and_validate_levels(orderbook.get("bids") or [], descending=True)
    src_asks = _parse_and_validate_levels(orderbook.get("asks") or [], descending=False)
    comp_asks = sorted(
        [{"price": round(1.0 - px, 6), "size": sz} for px, sz in src_bids if 0.0 < (1.0 - px) < 1.0],
        key=lambda x: x["price"],
    )
    comp_bids = sorted(
        [{"price": round(1.0 - px, 6), "size": sz} for px, sz in src_asks if 0.0 < (1.0 - px) < 1.0],
        key=lambda x: x["price"],
        reverse=True,
    )
    return {"bids": comp_bids, "asks": comp_asks}


def _parse_and_validate_levels(raw_levels: Any, descending: bool) -> Optional[List[Tuple[float, float]]]:
    """Fail-closed level validator: rejects if any level has non-finite price/size or price outside `(0, 1)`."""
    if not isinstance(raw_levels, list):
        return None
    parsed: List[Tuple[float, float]] = []
    try:
        for item in raw_levels:
            if isinstance(item, dict):
                px = float(item["price"])
                sz = float(item["size"])
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                px = float(item[0])
                sz = float(item[1])
            else:
                return None
            if not (math.isfinite(px) and math.isfinite(sz)) or not (0.0 < px < 1.0) or sz < 0.0:
                return None
            if sz > 0.0:
                parsed.append((px, sz))
    except (KeyError, TypeError, ValueError):
        return None
    parsed.sort(key=lambda t: t[0], reverse=descending)
    return parsed


def simulate_taker_fill(
    l2_levels: Any,
    side: str = "BUY",
    notional_usd: float = 15.0,
    *,
    shares_override: Optional[float] = None,
    fee_rate: float = 0.05,
    fee_exponent: float = 1.0,
    tick_size: float = 0.01,
    opposite_touch_px: Optional[float] = None,
    latency_ms: float = KRAKEN_FINLAND_CLOB_P50_MS,
    intentional_taker_delay: bool = False,
    book_age_ms: float = 50.0,
    enforce_min_lot: bool = True,
    max_acceptable_price: float = 0.999,
    min_acceptable_price: float = 0.001,
    stress_cost_multiplier: float = 1.0,
) -> TakerFillResult:
    """
    Exact multi-level L2 order-book sweep & VWAP simulator for `BUY` (sweeping asks) or `SELL` (sweeping bids).

    Accepts either:
      - Full `orderbook` dict `{"bids": [...], "asks": [...]}` (automatically computes exact `mid_px`!), OR
      - Direct level list `[{"price": ..., "size": ...}, ...]` / `[(price, size), ...]`.

    Explicitly decomposes total execution cost over midpoint into:
      1. Half-spread crossing (`|best_touch - mid_px|`),
      2. Multi-level L2 depth impact (`|vwap_px - best_touch|`),
      3. Deterministic latency/speedbump adverse quote-fade slippage (`latency_ms + 200ms * itode`),
      4. Exact per-leg Polymarket V2 probability-curved taker fees.
    """
    side_u = str(side or "BUY").upper()
    if side_u not in ("BUY", "SELL"):
        raise ValueError(f"Unsupported side={side!r}; expected 'BUY' or 'SELL'")

    inferred_opp_touch = opposite_touch_px
    if isinstance(l2_levels, dict):
        book_asks = _parse_and_validate_levels(l2_levels.get("asks") or [], descending=False)
        book_bids = _parse_and_validate_levels(l2_levels.get("bids") or [], descending=True)
        if book_asks is None or book_bids is None:
            return _empty_taker_result(side_u, notional_usd, "MALFORMED_L2_BOOK")
        if book_asks and book_bids and book_asks[0][0] <= book_bids[0][0]:
            return _empty_taker_result(side_u, notional_usd, "CROSSED_OR_LOCKED_BOOK")
        if side_u == "BUY":
            levels = book_asks
            if inferred_opp_touch is None and book_bids:
                inferred_opp_touch = book_bids[0][0]
        else:
            levels = book_bids
            if inferred_opp_touch is None and book_asks:
                inferred_opp_touch = book_asks[0][0]
    else:
        levels = _parse_and_validate_levels(l2_levels, descending=(side_u == "SELL"))
        if levels is None:
            return _empty_taker_result(side_u, notional_usd, "MALFORMED_L2_LEVELS")

    if not levels:
        return _empty_taker_result(side_u, notional_usd, "EMPTY_BOOK_SIDE")

    best_touch = levels[0][0]
    eff_tick = resolve_tick_size(best_touch, tick_size)
    if inferred_opp_touch is not None and 0.0 < float(inferred_opp_touch) < 1.0:
        mid_px = 0.5 * (best_touch + float(inferred_opp_touch))
    else:
        # Conservative minimum 1-tick spread assumption if only one side of book was passed
        mid_px = max(0.0005, best_touch - 0.5 * eff_tick) if side_u == "BUY" else min(0.9995, best_touch + 0.5 * eff_tick)

    # Enforce minimum lot checks before sweeping
    if shares_override is not None:
        req_shares = float(shares_override)
        req_notional = req_shares * best_touch
        if not math.isfinite(req_shares) or req_shares <= 0.0:
            return _empty_taker_result(side_u, 0.0, "INVALID_SHARES")
        if enforce_min_lot and (req_shares < MIN_CLOB_ORDER_SHARES - 1e-9 or req_notional < MIN_CLOB_MARKETABLE_NOTIONAL_USD - 1e-9):
            return _empty_taker_result(side_u, req_notional, "BELOW_CLOB_MIN_LOT")
    else:
        req_notional = float(notional_usd)
        if not math.isfinite(req_notional) or req_notional <= 0.0:
            return _empty_taker_result(side_u, 0.0, "INVALID_NOTIONAL")
        if enforce_min_lot and (req_notional < MIN_CLOB_MARKETABLE_NOTIONAL_USD - 1e-9 or (req_notional / best_touch) < MIN_CLOB_ORDER_SHARES - 1e-9):
            return _empty_taker_result(side_u, req_notional, "BELOW_CLOB_MIN_LOT")
        req_shares = 0.0

    fill_legs: List[Tuple[float, float]] = []
    total_shares = 0.0
    gross_notional = 0.0
    worst_px = best_touch

    if shares_override is not None:
        rem_sh = req_shares
        for px, sz in levels:
            if side_u == "BUY" and px > max_acceptable_price + 1e-9:
                break
            if side_u == "SELL" and px < min_acceptable_price - 1e-9:
                break
            take_sh = min(rem_sh, sz)
            total_shares += take_sh
            gross_notional += take_sh * px
            worst_px = px
            fill_legs.append((px, take_sh))
            rem_sh -= take_sh
            if rem_sh <= 1e-7:
                break
        if rem_sh > 1e-5:
            return _empty_taker_result(side_u, req_notional, "INSUFFICIENT_L2_DEPTH", mid_px=mid_px, best_touch=best_touch, worst_px=worst_px)
    else:
        rem_usd = req_notional
        for px, sz in levels:
            if side_u == "BUY" and px > max_acceptable_price + 1e-9:
                break
            if side_u == "SELL" and px < min_acceptable_price - 1e-9:
                break
            lvl_usd = px * sz
            if lvl_usd >= rem_usd - 1e-7:
                take_sh = min(sz, rem_usd / px)
                total_shares += take_sh
                gross_notional += take_sh * px
                worst_px = px
                fill_legs.append((px, take_sh))
                rem_usd = 0.0
                break
            total_shares += sz
            gross_notional += lvl_usd
            worst_px = px
            fill_legs.append((px, sz))
            rem_usd -= lvl_usd
        if rem_usd > 1e-4 or total_shares <= 0.0:
            return _empty_taker_result(side_u, req_notional, "INSUFFICIENT_L2_DEPTH", mid_px=mid_px, best_touch=best_touch, worst_px=worst_px)
        if enforce_min_lot and total_shares < MIN_CLOB_ORDER_SHARES - 1e-6:
            return _empty_taker_result(side_u, req_notional, "FILLED_SHARES_BELOW_MIN_LOT", mid_px=mid_px, best_touch=best_touch, worst_px=worst_px)

    vwap_px = gross_notional / total_shares
    stress_mult = max(0.0, float(stress_cost_multiplier))

    # Latency + exchange taker speedbump (`itode`) adverse quote-fade drift
    eff_delay_ms = max(0.0, float(latency_ms)) + (SUBHOURLY_ITODE_SPEEDBUMP_MS if intentional_taker_delay else 0.0) + 0.25 * max(0.0, float(book_age_ms))
    l1_depth_usd = levels[0][0] * levels[0][1]
    thinness_factor = min(2.5, math.sqrt(gross_notional / max(10.0, l1_depth_usd)))
    # Base drift: ~0.04c at 56ms on calm deep book, scaling to ~0.35-0.80c on 256ms `itode` thin book
    raw_latency_drift_px = (eff_delay_ms / 1000.0) * 0.0045 * (1.0 + 0.65 * thinness_factor) * (2.2 if intentional_taker_delay else 1.0)

    raw_half_spread_px = abs(best_touch - mid_px)
    raw_depth_impact_px = abs(vwap_px - best_touch)

    stressed_half_spread_px = raw_half_spread_px * stress_mult
    stressed_depth_impact_px = raw_depth_impact_px * stress_mult
    stressed_latency_px = raw_latency_drift_px * stress_mult

    if side_u == "BUY":
        eff_exec_px = min(0.9995, mid_px + stressed_half_spread_px + stressed_depth_impact_px + stressed_latency_px)
        eff_notional = total_shares * eff_exec_px
        # Leg-level exact curved taker fee (adjusted for any stress/latency price shift)
        if abs(eff_exec_px - vwap_px) < 1e-9:
            fee_usd = round(sum(sh_i * compute_taker_fee_per_share(px_i, fee_rate, fee_exponent) for px_i, sh_i in fill_legs), 5)
        else:
            _, fee_usd = compute_taker_fee_usd(eff_notional, eff_exec_px, fee_rate, fee_exponent)
        all_in_cash = eff_notional + fee_usd
        all_in_px = all_in_cash / total_shares
        friction_over_mid_usd = total_shares * (all_in_px - mid_px)
    else:
        eff_exec_px = max(0.0005, mid_px - stressed_half_spread_px - stressed_depth_impact_px - stressed_latency_px)
        eff_notional = total_shares * eff_exec_px
        if abs(eff_exec_px - vwap_px) < 1e-9:
            fee_usd = round(sum(sh_i * compute_taker_fee_per_share(px_i, fee_rate, fee_exponent) for px_i, sh_i in fill_legs), 5)
        else:
            _, fee_usd = compute_sell_taker_fee_usd(total_shares, eff_exec_px, fee_rate, fee_exponent)
        all_in_cash = max(0.0, eff_notional - fee_usd)
        all_in_px = all_in_cash / total_shares
        friction_over_mid_usd = total_shares * (mid_px - all_in_px)

    half_spread_usd = total_shares * stressed_half_spread_px
    depth_impact_usd = total_shares * stressed_depth_impact_px
    latency_cost_usd = total_shares * stressed_latency_px
    fee_bps = (fee_usd / max(eff_notional, 1e-9)) * 10000.0
    friction_bps = (friction_over_mid_usd / max(total_shares * mid_px, 1e-9)) * 10000.0

    return TakerFillResult(
        fillable=True,
        reason="OK",
        side=side_u,
        requested_notional_usd=round(req_notional, 4),
        filled_shares=round(total_shares, 6),
        gross_notional_usd=round(eff_notional, 5),
        mid_px=round(mid_px, 6),
        best_touch_px=round(best_touch, 6),
        vwap_px=round(vwap_px, 6),
        worst_px=round(worst_px, 6),
        effective_exec_px_before_fee=round(eff_exec_px, 6),
        taker_fee_usd=round(fee_usd, 5),
        taker_fee_per_share=round(fee_usd / total_shares, 6),
        taker_fee_bps_of_notional=round(fee_bps, 2),
        all_in_px_per_share=round(all_in_px, 6),
        all_in_cash_flow_usd=round(all_in_cash, 5),
        half_spread_cost_usd=round(half_spread_usd, 5),
        depth_impact_cost_usd=round(depth_impact_usd, 5),
        latency_and_stale_cost_usd=round(latency_cost_usd, 5),
        total_friction_over_mid_usd=round(friction_over_mid_usd, 5),
        total_friction_over_mid_bps=round(friction_bps, 2),
        levels_consumed=len(fill_legs),
        data_quality_mode="OBSERVED_L2",
        fill_legs=tuple((round(p, 6), round(s, 6)) for p, s in fill_legs),
    )


def _empty_taker_result(
    side: str,
    req_notional: float,
    reason: str,
    mid_px: float = 0.0,
    best_touch: float = 0.0,
    worst_px: float = 0.0,
    mode: str = "OBSERVED_L2",
) -> TakerFillResult:
    return TakerFillResult(
        fillable=False,
        reason=reason,
        side=side,
        requested_notional_usd=round(float(req_notional or 0.0), 4),
        filled_shares=0.0,
        gross_notional_usd=0.0,
        mid_px=round(mid_px, 6),
        best_touch_px=round(best_touch, 6),
        vwap_px=0.0,
        worst_px=round(worst_px, 6),
        effective_exec_px_before_fee=0.0,
        taker_fee_usd=0.0,
        taker_fee_per_share=0.0,
        taker_fee_bps_of_notional=0.0,
        all_in_px_per_share=0.0,
        all_in_cash_flow_usd=0.0,
        half_spread_cost_usd=0.0,
        depth_impact_cost_usd=0.0,
        latency_and_stale_cost_usd=0.0,
        total_friction_over_mid_usd=0.0,
        total_friction_over_mid_bps=0.0,
        levels_consumed=0,
        data_quality_mode=mode,
        fill_legs=(),
    )


# ==============================================================================
# 4. HISTORICAL CLOB SERIES EXECUTION ESTIMATOR (ZERO MIDPOINT FABRICATION!)
# ==============================================================================

def estimate_historical_taker_execution(
    reference_price: float,
    side: str = "BUY",
    notional_usd: float = 15.0,
    *,
    shares_override: Optional[float] = None,
    category: str = "other",
    liquidity_usd: float = 15000.0,
    observed_spread_px: Optional[float] = None,
    fee_rate: Optional[float] = None,
    fee_exponent: float = 1.0,
    fees_enabled: Optional[bool] = None,
    tick_size: Optional[float] = None,
    is_fast_shock: bool = False,
    intentional_taker_delay: bool = False,
    latency_ms: float = KRAKEN_FINLAND_CLOB_P50_MS,
    stress_cost_multiplier: float = 1.0,
    enforce_min_lot: bool = True,
    calibration_path: Optional[Path] = None,
) -> TakerFillResult:
    """
    Calibrated execution estimator when historical data only contains CLOB `/prices-history`
    (trade/mid series) rather than full L2 snapshots.

    STRICT RT-02 INVARIANT: Never permits zero-cost midpoint fills (`stress_cost_multiplier`
    has a hard floor of `> 0` in production backtests; even at `1.0x`, enforces calibrated
    category x liquidity half-spread `>= 0.5 * tick` + L2 depth slope impact + stale-print penalty + V2 fee).
    """
    side_u = str(side or "BUY").upper()
    if side_u not in ("BUY", "SELL"):
        raise ValueError(f"Unsupported side={side!r}")
    if not math.isfinite(reference_price) or not (0.001 <= reference_price <= 0.999):
        return _empty_taker_result(side_u, notional_usd, "REFERENCE_PRICE_OUT_OF_BOUNDS", mode="ESTIMATED_SPREAD_ADJUSTED")

    mid_px = float(reference_price)
    norm_cat = normalize_category_name(category)
    tier = classify_liquidity_tier(liquidity_usd)
    cal = load_microstructure_calibration(calibration_path)

    # Blend category and liquidity-tier empirical calibration from 338 live L2 books
    cat_stats = (cal.get("by_category") or {}).get(norm_cat) or EMPIRICAL_CATEGORY_PRIORS.get(norm_cat, EMPIRICAL_CATEGORY_PRIORS["other"])
    tier_stats = (cal.get("by_liquidity_tier") or {}).get(tier) or EMPIRICAL_LIQUIDITY_TIER_PRIORS[tier]

    cat_spread_c = float(cat_stats.get("spread_cents_p50", cat_stats.get("spread_c_p50", 1.0)))
    tier_spread_c = float(tier_stats.get("spread_cents_p50", tier_stats.get("spread_c_p50", 1.0)))
    cat_l1_usd = float(cat_stats.get("l1_ask_usd_p50", cat_stats.get("l1_usd_p50", 25.0)))
    tier_l1_usd = float(tier_stats.get("l1_ask_usd_p50", tier_stats.get("l1_usd_p50", 25.0)))
    cat_d5_usd = float(cat_stats.get("ask_5c_depth_usd_p50", cat_stats.get("d5c_usd_p50", 500.0)))
    tier_d5_usd = float(tier_stats.get("ask_5c_depth_usd_p50", tier_stats.get("d5c_usd_p50", 500.0)))

    eff_tick = resolve_tick_size(mid_px, tick_size if tick_size is not None else (0.001 if mid_px < 0.10 or mid_px > 0.90 else 0.01))

    # Tail compression: spreads in cents narrow on 0.001-tick tails (<10c or >90c) while widening in bps
    tail_factor = 0.55 if (mid_px < 0.10 or mid_px > 0.90) else 1.0
    est_spread_px = (
        max(eff_tick, float(observed_spread_px))
        if observed_spread_px is not None and observed_spread_px > 0
        else max(eff_tick, ((0.45 * cat_spread_c + 0.55 * tier_spread_c) / 100.0) * tail_factor)
    )
    half_spread_px = 0.5 * est_spread_px

    # Geometric mean of category & tier depth prevents overstating capacity when an illiquid market sits in a liquid category
    est_l1_usd = max(2.0, math.sqrt(max(1.0, cat_l1_usd) * max(1.0, tier_l1_usd)) * (0.45 if mid_px < 0.12 else 1.0))
    est_d5_usd = max(est_l1_usd * 2.5, math.sqrt(max(5.0, cat_d5_usd) * max(5.0, tier_d5_usd)) * (0.55 if mid_px < 0.12 else 1.0))

    best_touch = min(0.999, mid_px + half_spread_px) if side_u == "BUY" else max(0.001, mid_px - half_spread_px)
    req_notional = (float(shares_override) * best_touch) if shares_override is not None else float(notional_usd)
    if not math.isfinite(req_notional) or req_notional <= 0.0:
        return _empty_taker_result(side_u, 0.0, "INVALID_NOTIONAL", mode="ESTIMATED_SPREAD_ADJUSTED")

    est_shares_at_touch = float(shares_override) if shares_override is not None else (req_notional / best_touch)
    if enforce_min_lot and (est_shares_at_touch < MIN_CLOB_ORDER_SHARES - 1e-9 or req_notional < MIN_CLOB_MARKETABLE_NOTIONAL_USD - 1e-9):
        return _empty_taker_result(side_u, req_notional, "BELOW_CLOB_MIN_LOT", mid_px=mid_px, best_touch=best_touch, mode="ESTIMATED_SPREAD_ADJUSTED")

    # Capacity exhaustion gate (RT-09): reject clips that exceed plausible full-book depth (`3.5x` 5c depth)
    max_fillable_usd = est_d5_usd * 3.5
    if req_notional > max_fillable_usd:
        return _empty_taker_result(
            side_u,
            req_notional,
            "EXCEEDS_CALIBRATED_BOOK_CAPACITY",
            mid_px=mid_px,
            best_touch=best_touch,
            mode="ESTIMATED_SPREAD_ADJUSTED",
        )

    # Piecewise empirical L2 depth impact above L1 top-of-book:
    # Within L1 (`req_notional <= est_l1_usd`): 0 depth impact beyond best touch.
    # Beyond L1: walks the 5-cent depth slope (`0.05` price move across `est_d5_usd` notional, steepening nonlinearly past `est_d5_usd`).
    excess_over_l1 = max(0.0, req_notional - est_l1_usd)
    if excess_over_l1 <= 0.0:
        depth_impact_px = 0.0
        levels_est = 1
    else:
        frac_5c = excess_over_l1 / max(10.0, est_d5_usd)
        # Empirically calibrated against 338-book VWAP curve (`0.5 * 5c` average VWAP when sweeping full 5c band)
        depth_impact_px = 0.026 * frac_5c + 0.018 * (frac_5c ** 1.35)
        levels_est = min(15, 1 + max(1, int(math.ceil(frac_5c * 5.0))))

    # Stale-quote / trade-print bias + latency slippage (`RT-02`):
    # `/prices-history` prints record trades that just consumed L1 liquidity; fast shocks suffer additional speedbump fade.
    base_stale_c = EMPIRICAL_LIQUIDITY_TIER_PRIORS[tier]["stale_c"]
    eff_delay_ms = max(0.0, float(latency_ms)) + (SUBHOURLY_ITODE_SPEEDBUMP_MS if intentional_taker_delay else 0.0)
    stale_and_lat_px = (base_stale_c / 100.0) * (0.65 if not is_fast_shock else 1.85) + (eff_delay_ms / 1000.0) * (0.009 if is_fast_shock or intentional_taker_delay else 0.002)

    # Enforce strict positive stress multiplier (default 1.0x; never 0.0 midpoint fabrication!)
    stress_mult = max(0.25, float(stress_cost_multiplier))
    s_half = max(0.5 * eff_tick, half_spread_px * stress_mult)
    s_depth = depth_impact_px * stress_mult
    s_stale = stale_and_lat_px * stress_mult

    if fee_rate is None:
        sched = resolve_fee_schedule(category=norm_cat, fees_enabled=fees_enabled)
        eff_fee_rate = sched.fee_rate
        eff_fee_exp = sched.fee_exponent
    else:
        eff_fee_rate = 0.0 if fees_enabled is False else float(fee_rate)
        eff_fee_exp = float(fee_exponent)

    if side_u == "BUY":
        vwap_px = min(0.9985, mid_px + s_half + s_depth)
        eff_exec_px = min(0.999, vwap_px + s_stale)
        worst_px = min(0.999, mid_px + s_half + 1.85 * s_depth + s_stale)
        if eff_exec_px >= 0.9985 and mid_px < 0.985:
            return _empty_taker_result(side_u, req_notional, "SLIPPAGE_EXHAUSTS_CEILING", mid_px=mid_px, best_touch=best_touch, mode="ESTIMATED_SPREAD_ADJUSTED")
        filled_shares = float(shares_override) if shares_override is not None else (req_notional / eff_exec_px)
        if enforce_min_lot and filled_shares < MIN_CLOB_ORDER_SHARES - 1e-6:
            return _empty_taker_result(side_u, req_notional, "FILLED_SHARES_BELOW_MIN_LOT", mid_px=mid_px, best_touch=best_touch, mode="ESTIMATED_SPREAD_ADJUSTED")
        gross_notional = filled_shares * eff_exec_px
        _, fee_usd = compute_taker_fee_usd(gross_notional, eff_exec_px, eff_fee_rate, eff_fee_exp)
        all_in_cash = gross_notional + fee_usd
        all_in_px = all_in_cash / filled_shares
        friction_usd = filled_shares * (all_in_px - mid_px)
    else:
        vwap_px = max(0.0015, mid_px - s_half - s_depth)
        eff_exec_px = max(0.001, vwap_px - s_stale)
        worst_px = max(0.001, mid_px - s_half - 1.85 * s_depth - s_stale)
        if eff_exec_px <= 0.0015 and mid_px > 0.015:
            return _empty_taker_result(side_u, req_notional, "SLIPPAGE_EXHAUSTS_FLOOR", mid_px=mid_px, best_touch=best_touch, mode="ESTIMATED_SPREAD_ADJUSTED")
        filled_shares = float(shares_override) if shares_override is not None else (req_notional / best_touch)
        gross_notional = filled_shares * eff_exec_px
        _, fee_usd = compute_sell_taker_fee_usd(filled_shares, eff_exec_px, eff_fee_rate, eff_fee_exp)
        all_in_cash = max(0.0, gross_notional - fee_usd)
        all_in_px = all_in_cash / filled_shares
        friction_usd = filled_shares * (mid_px - all_in_px)

    fee_bps = (fee_usd / max(gross_notional, 1e-9)) * 10000.0
    friction_bps = (friction_usd / max(filled_shares * mid_px, 1e-9)) * 10000.0

    return TakerFillResult(
        fillable=True,
        reason="OK",
        side=side_u,
        requested_notional_usd=round(req_notional, 4),
        filled_shares=round(filled_shares, 6),
        gross_notional_usd=round(gross_notional, 5),
        mid_px=round(mid_px, 6),
        best_touch_px=round(best_touch, 6),
        vwap_px=round(vwap_px, 6),
        worst_px=round(worst_px, 6),
        effective_exec_px_before_fee=round(eff_exec_px, 6),
        taker_fee_usd=round(fee_usd, 5),
        taker_fee_per_share=round(fee_usd / filled_shares, 6),
        taker_fee_bps_of_notional=round(fee_bps, 2),
        all_in_px_per_share=round(all_in_px, 6),
        all_in_cash_flow_usd=round(all_in_cash, 5),
        half_spread_cost_usd=round(filled_shares * s_half, 5),
        depth_impact_cost_usd=round(filled_shares * s_depth, 5),
        latency_and_stale_cost_usd=round(filled_shares * s_stale, 5),
        total_friction_over_mid_usd=round(friction_usd, 5),
        total_friction_over_mid_bps=round(friction_bps, 2),
        levels_consumed=levels_est,
        data_quality_mode="ESTIMATED_SPREAD_ADJUSTED",
        fill_legs=((round(eff_exec_px, 6), round(filled_shares, 6)),),
    )


# ==============================================================================
# 5. PASSIVE MAKER QUEUE, PARTIAL FILL & ADVERSE-SELECTION SIMULATOR
# ==============================================================================

def simulate_maker_order(
    limit_price: float,
    side: str = "BUY",
    notional_usd: float = 15.0,
    *,
    shares_override: Optional[float] = None,
    best_bid: float = 0.49,
    best_ask: float = 0.51,
    existing_queue_shares_at_price: Optional[float] = None,
    category: str = "other",
    liquidity_usd: float = 15000.0,
    resting_horizon_sec: float = 300.0,
    prior_fair_prob: Optional[float] = None,
    volatility_1h_prob: float = 0.035,
    spread_widening_shock: bool = False,
    future_price_path: Optional[List[float]] = None,
    shares_traded_through_level: Optional[float] = None,
    fee_rate: float = 0.05,
    fee_exponent: float = 1.0,
    rebate_rate: float = 0.0,
    rebate_realization_haircut: float = 1.0,
    tick_size: float = 0.01,
    enforce_min_lot: bool = True,
) -> MakerSimulationResult:
    """
    Simulates a passive `postOnly=True` (`0%` fee) Maker order on Polymarket CLOB:
      1. `postOnly` Cross Check: Rejects immediately (`crosses_book_rejected=True`) if `BUY` `limit_price >= best_ask`
         or `SELL` `limit_price <= best_bid`.
      2. Queue Priority (`queue_ahead_shares`): Price-improving inside a wide spread starts at `FIFO #1` (`0` ahead);
         joining the existing touch/deeper level sits behind `existing_queue_shares_at_price` (or calibrated L1 depth).
      3. Path-Consistent Fill Verification:
         - If `shares_traded_through_level` is provided (from live/shadow L2/trade tape), fills `max(0, traded - queue_ahead)`.
         - Else if `future_price_path` is provided (historical series), fills ONLY if future prices trade STRICTLY THROUGH
           `limit_price` (or touch repeatedly with sufficient horizon to clear `queue_ahead`) — preventing phantom touch fills!
         - Else computes Poisson/exponential queue-depletion fill probability & expected partial fill fraction.
      4. Toxic-Flow Adverse-Selection Haircut (`adverse_selection_prob_haircut`):
         Passive BUY orders fill disproportionately when informed sellers drive true probability `p_true` DOWN through `limit_price`
         (and passive SELL orders fill when informed buyers drive `p_true` UP through `limit_price`).
    """
    side_u = str(side or "BUY").upper()
    if side_u not in ("BUY", "SELL"):
        raise ValueError(f"Unsupported side={side!r}")

    eff_tick = resolve_tick_size(limit_price, tick_size)
    px = round_price_to_tick(limit_price, eff_tick, mode="floor" if side_u == "BUY" else "ceil")
    mid_px = 0.5 * (float(best_bid) + float(best_ask))
    p_prior = float(prior_fair_prob) if prior_fair_prob is not None else mid_px

    req_shares = float(shares_override) if shares_override is not None else (float(notional_usd) / max(0.001, px))
    req_shares = math.floor(req_shares * 100.0 + 1e-9) / 100.0
    req_notional = req_shares * px

    if enforce_min_lot and (req_shares < MIN_CLOB_ORDER_SHARES - 1e-9 or req_notional < MIN_CLOB_MARKETABLE_NOTIONAL_USD - 1e-9):
        return MakerSimulationResult(
            False, False, "BELOW_CLOB_MIN_LOT", side_u, px, req_shares, round(req_notional, 4),
            False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, round(p_prior, 6), 0.0, round(p_prior, 6), 0.0,
        )

    # 1. `postOnly=True` crossing check
    if (side_u == "BUY" and px >= float(best_ask) - 1e-9) or (side_u == "SELL" and px <= float(best_bid) + 1e-9):
        return MakerSimulationResult(
            False, True, "POST_ONLY_WOULD_CROSS_BOOK", side_u, px, req_shares, round(req_notional, 4),
            False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, round(p_prior, 6), 0.0, round(p_prior, 6), 0.0,
        )

    norm_cat = normalize_category_name(category)
    tier = classify_liquidity_tier(liquidity_usd)
    cat_prior = EMPIRICAL_CATEGORY_PRIORS.get(norm_cat, EMPIRICAL_CATEGORY_PRIORS["other"])
    tier_prior = EMPIRICAL_LIQUIDITY_TIER_PRIORS[tier]

    improves_touch = (px > float(best_bid) + 1e-9) if side_u == "BUY" else (px < float(best_ask) - 1e-9)
    ticks_behind_touch = (
        0.0 if improves_touch else max(0.0, (float(best_bid) - px) if side_u == "BUY" else (px - float(best_ask))) / eff_tick
    )

    if improves_touch:
        queue_ahead_sh = 0.0
    elif existing_queue_shares_at_price is not None:
        queue_ahead_sh = max(0.0, float(existing_queue_shares_at_price))
    else:
        est_l1_usd = math.sqrt(cat_prior["l1_usd_p50"] * tier_prior["l1_usd_p50"])
        queue_ahead_sh = (est_l1_usd / max(0.02, px)) * (1.0 + 0.65 * ticks_behind_touch)
    queue_ahead_usd = queue_ahead_sh * px

    # 2. Compute fill probability & deterministic/expected filled shares
    horizon_hr = max(1.0 / 3600.0, float(resting_horizon_sec) / 3600.0)
    sigma_h = max(0.004, float(volatility_1h_prob) * math.sqrt(min(24.0, horizon_hr)))

    if shares_traded_through_level is not None:
        residual_flow = max(0.0, float(shares_traded_through_level) - queue_ahead_sh)
        det_filled = min(req_shares, residual_flow)
        fill_frac = det_filled / req_shares if req_shares > 0 else 0.0
        p_fill = 1.0 if det_filled >= req_shares - 1e-6 else (0.5 * fill_frac if det_filled > 0 else 0.0)
        exp_filled = det_filled
    elif future_price_path is not None and len(future_price_path) > 0:
        # Path-based conservative fill verification for historical series (`RT-02`):
        # Simply touching `px` in `/prices-history` does NOT guarantee clearing `queue_ahead_sh`;
        # full queue clearance requires price trading strictly THROUGH `px` by >= 1 tick, while exact touch
        # yields only partial queue-pro-rata fill.
        if side_u == "BUY":
            min_fp = min(float(x) for x in future_price_path)
            penetration = px - min_fp
        else:
            max_fp = max(float(x) for x in future_price_path)
            penetration = max_fp - px

        if penetration >= eff_tick - 1e-9:
            # Traded strictly through our resting limit -> 100% of resting queue at `px` was cleared!
            fill_frac = 1.0
            p_fill = 1.0
        elif penetration >= -1e-9:
            # Exact touch without trading through -> partial FIFO fill inversely proportional to queue ahead
            touch_count = sum(1 for x in future_price_path if (float(x) <= px + 1e-9 if side_u == "BUY" else float(x) >= px - 1e-9))
            est_touch_vol_sh = max(5.0, 0.35 * queue_ahead_sh * touch_count + (12.0 if improves_touch else 4.0))
            det_sh = max(0.0, min(req_shares, est_touch_vol_sh - queue_ahead_sh))
            fill_frac = det_sh / req_shares
            p_fill = max(0.05, min(0.65, est_touch_vol_sh / max(1.0, queue_ahead_sh + req_shares)))
        else:
            fill_frac = 0.0
            p_fill = 0.0
        det_filled = round(req_shares * fill_frac, 4)
        exp_filled = det_filled
    else:
        # Parametric arrival + diffusion queue-depletion model
        arrival_rate = cat_prior["arrival_hz"] * (1.45 if improves_touch else 1.0) * math.exp(-0.55 * ticks_behind_touch)
        if spread_widening_shock:
            # During event news / MM quote pull, passive liquidity evaporates on winning side while toxic sweeps spike
            arrival_rate *= 0.35
        expected_aggressor_usd = arrival_rate * float(resting_horizon_sec) * max(8.0, 0.30 * tier_prior["l1_usd_p50"])
        total_needed_usd = queue_ahead_usd + req_notional
        flow_ratio = expected_aggressor_usd / max(1.0, total_needed_usd)
        p_fill = 1.0 - math.exp(-0.85 * flow_ratio)
        p_fill = max(0.01, min(0.95, p_fill))
        # Partial fill conditioning: some arrivals clear queue_ahead + part of our order
        partial_cond = min(1.0, max(0.35, (expected_aggressor_usd - 0.65 * queue_ahead_usd) / max(req_notional, 1.0))) if flow_ratio >= 0.4 else 0.55
        fill_frac = p_fill * partial_cond
        exp_filled = req_shares * fill_frac
        det_filled = req_shares if p_fill >= 0.65 else (round(exp_filled, 2) if exp_filled >= MIN_CLOB_ORDER_SHARES else 0.0)

    # 3. Glosten-Milgrom Toxic-Flow Adverse Selection Conditional on Fill (`E[Delta p_true | Maker Fill]`):
    # A passive limit order is short a free short-dated option to informed takers:
    #   - If path is given and ended beyond our limit, realized markout directly reflects toxic continuation;
    #   - Parametric adverse shift scales with `sigma_h`, toxic-flow share (`crypto/sports` > `weather/politics`),
    #     queue depth (deeper queue ONLY fills on large directional sweeps!), and `spread_widening_shock`.
    toxicity_beta = 0.62 if norm_cat in ("crypto", "sports") else 0.42
    if spread_widening_shock:
        toxicity_beta *= 1.75
    queue_sweep_mult = 1.0 + 0.18 * math.log1p(queue_ahead_usd / max(10.0, req_notional))
    param_as_shift = min(0.18, max(0.006, toxicity_beta * sigma_h * queue_sweep_mult))

    if future_price_path is not None and len(future_price_path) > 0 and det_filled > 0.0:
        terminal_px = float(future_price_path[-1])
        realized_adverse = max(0.0, (px - terminal_px) if side_u == "BUY" else (terminal_px - px))
        as_haircut = max(0.5 * param_as_shift, realized_adverse)
    else:
        as_haircut = param_as_shift

    if side_u == "BUY":
        post_fill_p = max(0.001, p_prior - as_haircut)
    else:
        post_fill_p = min(0.999, p_prior + as_haircut)

    theo_rebate = compute_maker_rebate_usd(exp_filled, px, fee_rate, fee_exponent, rebate_rate, realization_haircut=0.0)
    assumed_rebate = compute_maker_rebate_usd(exp_filled, px, fee_rate, fee_exponent, rebate_rate, realization_haircut=rebate_realization_haircut)
    toxicity_cost_usd = exp_filled * as_haircut

    return MakerSimulationResult(
        accepted=True,
        crosses_book_rejected=False,
        reason="OK",
        side=side_u,
        limit_price=round(px, 6),
        requested_shares=round(req_shares, 4),
        requested_notional_usd=round(req_notional, 4),
        improves_touch=improves_touch,
        queue_ahead_shares=round(queue_ahead_sh, 2),
        queue_ahead_usd=round(queue_ahead_usd, 2),
        fill_probability=round(p_fill, 4),
        expected_fill_fraction=round(fill_frac, 4),
        expected_filled_shares=round(exp_filled, 4),
        deterministic_filled_shares=round(det_filled, 4),
        maker_fee_usd=0.0,
        assumed_rebate_usd=round(assumed_rebate, 6),
        theoretical_unhaircut_rebate_usd=round(theo_rebate, 6),
        prior_fair_prob=round(p_prior, 6),
        adverse_selection_prob_haircut=round(as_haircut, 6),
        post_fill_fair_prob=round(post_fill_p, 6),
        expected_toxicity_cost_usd=round(toxicity_cost_usd, 5),
    )


# ==============================================================================
# 6. UNIFIED ROUND-TRIP TRADE SIMULATOR (SETTLEMENT VS PRE-RESOLUTION EXIT)
# ==============================================================================

def simulate_round_trip_trade(
    *,
    entry_mode: str = "TAKER",  # "TAKER" or "MAKER"
    notional_usd: float = 15.0,
    entry_reference_px: float = 0.50,
    entry_l2_book: Optional[Dict[str, Any]] = None,
    exit_mechanism: str = "SETTLEMENT",  # "SETTLEMENT", "TAKER_EXIT", or "MAKER_EXIT"
    outcome_resolved_win: Optional[bool] = None,
    settlement_payout_per_share: Optional[float] = None,  # Supports continuous 0.50 on 50-50 void & 0.00 on UMA dispute!
    exit_reference_px: Optional[float] = None,
    exit_l2_book: Optional[Dict[str, Any]] = None,
    holding_days: float = 1.0,
    category: str = "other",
    liquidity_usd: float = 15000.0,
    fee_schedule: Optional[FeeSchedule] = None,
    tick_size: float = 0.01,
    stress_cost_multiplier: float = 1.0,
    uma_dispute_haircut_bps: float = 0.0,
    enforce_min_lot: bool = True,
) -> Dict[str, Any]:
    """
    Deterministic end-to-end trade simulator supporting BOTH:
      - `SETTLEMENT` (`$1.00` payout on winning token via `$0.00`-gas Relayer V2 `redeemPositions`, `$0.00` on loss), AND
      - `TAKER_EXIT` / `MAKER_EXIT` pre-resolution trading exits (applying realistic exit bid spread, L2 impact, and exit fee).
    """
    sched = fee_schedule or resolve_fee_schedule(category=category)
    entry_mode_u = entry_mode.upper()
    exit_mech_u = exit_mechanism.upper()

    if entry_mode_u == "TAKER":
        if entry_l2_book is not None:
            entry_res = simulate_taker_fill(
                entry_l2_book,
                "BUY",
                notional_usd,
                fee_rate=sched.fee_rate,
                fee_exponent=sched.fee_exponent,
                tick_size=tick_size,
                intentional_taker_delay=sched.intentional_taker_delay,
                enforce_min_lot=enforce_min_lot,
                stress_cost_multiplier=stress_cost_multiplier,
            )
        else:
            entry_res = estimate_historical_taker_execution(
                entry_reference_px,
                "BUY",
                notional_usd,
                category=category,
                liquidity_usd=liquidity_usd,
                fee_rate=sched.fee_rate,
                fee_exponent=sched.fee_exponent,
                fees_enabled=sched.fees_enabled,
                tick_size=tick_size,
                intentional_taker_delay=sched.intentional_taker_delay,
                stress_cost_multiplier=stress_cost_multiplier,
                enforce_min_lot=enforce_min_lot,
            )
        if not entry_res.fillable:
            return {"executed": False, "reason": f"ENTRY_{entry_res.reason}", "net_pnl_usd": 0.0}
        shares = entry_res.filled_shares
        entry_exec_px = entry_res.effective_exec_px_before_fee
        entry_fee_usd = entry_res.taker_fee_usd
        entry_cash_outlay = entry_res.all_in_cash_flow_usd
        entry_friction_usd = entry_res.total_friction_over_mid_usd
        entry_mid_px = entry_res.mid_px
    elif entry_mode_u == "MAKER":
        b_bid = max(0.001, entry_reference_px - 0.5 * tick_size)
        b_ask = min(0.999, entry_reference_px + 0.5 * tick_size)
        m_res = simulate_maker_order(
            b_bid,
            "BUY",
            notional_usd,
            best_bid=b_bid,
            best_ask=b_ask,
            category=category,
            liquidity_usd=liquidity_usd,
            fee_rate=sched.fee_rate,
            fee_exponent=sched.fee_exponent,
            rebate_rate=sched.rebate_rate,
            tick_size=tick_size,
            enforce_min_lot=enforce_min_lot,
        )
        if not m_res.accepted or m_res.expected_filled_shares <= 0.0:
            return {"executed": False, "reason": f"MAKER_ENTRY_{m_res.reason}", "net_pnl_usd": 0.0}
        shares = m_res.expected_filled_shares
        # Incorporate adverse selection markout directly as effective economic cost unless path outcome already reflects it
        entry_exec_px = m_res.limit_price
        entry_fee_usd = 0.0
        entry_cash_outlay = shares * entry_exec_px - m_res.assumed_rebate_usd
        entry_friction_usd = m_res.expected_toxicity_cost_usd * max(0.25, float(stress_cost_multiplier))
        entry_mid_px = entry_reference_px
    else:
        raise ValueError(f"Unsupported entry_mode={entry_mode!r}")

    # Evaluate Exit / Settlement
    exit_fee_usd = 0.0
    exit_friction_usd = 0.0
    if exit_mech_u == "SETTLEMENT":
        if settlement_payout_per_share is not None:
            unit_payout = max(0.0, min(1.0, float(settlement_payout_per_share)))
        elif outcome_resolved_win is not None:
            unit_payout = 1.0 if outcome_resolved_win else 0.0
        else:
            raise ValueError("settlement_payout_per_share or outcome_resolved_win required when exit_mechanism == 'SETTLEMENT'")
        # $0.00 gas redemption via Polymarket Relayer V2; deduct optional UMA dispute/lockup haircut if parameterized
        uma_haircut = (float(uma_dispute_haircut_bps) / 10000.0) * shares
        gross_payout = max(0.0, unit_payout * shares - uma_haircut)
        net_exit_proceeds = gross_payout
        exit_mid_px = unit_payout
    elif exit_mech_u == "TAKER_EXIT":
        if exit_l2_book is not None:
            ex_res = simulate_taker_fill(
                exit_l2_book,
                "SELL",
                notional_usd=shares * float(exit_reference_px or 0.5),
                shares_override=shares,
                fee_rate=sched.fee_rate,
                fee_exponent=sched.fee_exponent,
                tick_size=tick_size,
                intentional_taker_delay=sched.intentional_taker_delay,
                enforce_min_lot=False,
                stress_cost_multiplier=stress_cost_multiplier,
            )
        else:
            if exit_reference_px is None:
                raise ValueError("exit_reference_px required for historical TAKER_EXIT")
            ex_res = estimate_historical_taker_execution(
                exit_reference_px,
                "SELL",
                notional_usd=shares * exit_reference_px,
                shares_override=shares,
                category=category,
                liquidity_usd=liquidity_usd,
                fee_rate=sched.fee_rate,
                fee_exponent=sched.fee_exponent,
                fees_enabled=sched.fees_enabled,
                tick_size=tick_size,
                intentional_taker_delay=sched.intentional_taker_delay,
                stress_cost_multiplier=stress_cost_multiplier,
                enforce_min_lot=False,
            )
        if not ex_res.fillable:
            return {"executed": False, "reason": f"EXIT_{ex_res.reason}", "net_pnl_usd": 0.0}
        net_exit_proceeds = ex_res.all_in_cash_flow_usd
        exit_fee_usd = ex_res.taker_fee_usd
        exit_friction_usd = ex_res.total_friction_over_mid_usd
        exit_mid_px = ex_res.mid_px
    elif exit_mech_u == "MAKER_EXIT":
        if exit_reference_px is None:
            raise ValueError("exit_reference_px required for MAKER_EXIT")
        exit_ask = round_price_to_tick(exit_reference_px + 0.5 * tick_size, tick_size, mode="ceil")
        # Conservative passive exit: deduct adverse selection / non-fill fallback penalty
        non_fill_fallback_cost = shares * (0.008 * max(0.25, float(stress_cost_multiplier)))
        net_exit_proceeds = max(0.0, shares * exit_ask - non_fill_fallback_cost)
        exit_friction_usd = non_fill_fallback_cost
        exit_mid_px = exit_reference_px
    else:
        raise ValueError(f"Unsupported exit_mechanism={exit_mechanism!r}")

    mid_to_mid_gross_pnl = shares * (exit_mid_px - entry_mid_px)
    # Note: for MAKER entry on historical outcomes, subtract adverse-selection cost if not already path-selected
    as_deduction = entry_friction_usd if entry_mode_u == "MAKER" else 0.0
    net_pnl = net_exit_proceeds - entry_cash_outlay - as_deduction
    lockup_d = max(1.0 / 24.0, float(holding_days))
    dollar_days = entry_cash_outlay * lockup_d

    return {
        "executed": True,
        "entry_mode": entry_mode_u,
        "exit_mechanism": exit_mech_u,
        "shares": round(shares, 6),
        "entry_mid_px": round(entry_mid_px, 6),
        "entry_exec_px": round(entry_exec_px, 6),
        "entry_cash_outlay_usd": round(entry_cash_outlay, 5),
        "entry_fee_usd": round(entry_fee_usd, 5),
        "exit_fee_usd": round(exit_fee_usd, 5),
        "total_fees_usd": round(entry_fee_usd + exit_fee_usd, 5),
        "total_friction_usd": round(entry_friction_usd + exit_friction_usd, 5),
        "gross_mid_pnl_usd": round(mid_to_mid_gross_pnl, 5),
        "net_exit_proceeds_usd": round(net_exit_proceeds, 5),
        "net_pnl_usd": round(net_pnl, 5),
        "return_on_outlay": round(net_pnl / max(entry_cash_outlay, 1e-9), 6),
        "dollar_days_committed": round(dollar_days, 4),
        "profit_per_dollar_day": round(net_pnl / max(dollar_days, 1e-9), 6),
    }


# ==============================================================================
# 7. ACCOUNT-SCALE CAPACITY & LATENCY MATERIALITY DIAGNOSTICS
# ==============================================================================

def evaluate_account_scale_constraints(
    account_equity_usd: float,
    desired_kelly_fraction: float,
    price: float,
    *,
    category: str = "other",
    liquidity_usd: float = 15000.0,
    expected_gross_edge_bps: float = 250.0,
    holding_days: float = 2.0,
    max_event_concentration_pct: float = 0.15,
    daily_infra_burn_usd: float = DOMINUS_DAILY_VM_BURN_USD,
    riskless_opportunity_cost_bps_per_day: float = 35.0,
) -> Dict[str, Any]:
    """
    Evaluates execution viability across Small (`$48.81`), Medium (`$500`), and Scalable (`$5,000+`) accounts:
      - Enforces `15%` single-event concentration cap (`$7.32` at `$48.81`!) vs `5`-share / `$1.00` CLOB minimums.
      - Computes actual Taker execution friction (spread + depth impact + V2 fee) at the resulting clip size.
      - Compares net expected `$/day` against both the `$0.822/day` VM burn hurdle and `DOMINUS RISKLESS` opportunity cost.
    """
    eq = max(1.0, float(account_equity_usd))
    conc_cap_usd = eq * float(max_event_concentration_pct)
    raw_kelly_usd = eq * max(0.0, float(desired_kelly_fraction))
    target_usd = min(raw_kelly_usd, conc_cap_usd)

    lot = validate_and_quantize_order_lot(
        max(0.01, target_usd),
        price,
        allow_lot_floor_upsize=True,
        max_lot_upsize_ratio=max(1.0, conc_cap_usd / max(target_usd, 1e-6)),
    )
    min_lot_usd = max(MIN_CLOB_MARKETABLE_NOTIONAL_USD, MIN_CLOB_ORDER_SHARES * price)
    # Even if upsized, cannot breach the 15% reconciled-NAV single-event concentration rule (D-007)!
    breaches_concentration = min_lot_usd > conc_cap_usd + 1e-6

    if not lot.eligible or breaches_concentration:
        return {
            "account_equity_usd": round(eq, 2),
            "viable": False,
            "blocker": "MIN_LOT_EXCEEDS_15PCT_CONCENTRATION_CAP" if breaches_concentration else lot.reason,
            "min_lot_usd": round(min_lot_usd, 2),
            "event_concentration_cap_usd": round(conc_cap_usd, 2),
            "max_concurrent_diversified_positions": int(eq // max(min_lot_usd, 1.0)),
            "daily_vm_hurdle_bps_on_equity": round((daily_infra_burn_usd / eq) * 10000.0, 2),
        }

    exec_est = estimate_historical_taker_execution(
        price,
        "BUY",
        lot.quantized_notional_usd,
        category=category,
        liquidity_usd=liquidity_usd,
    )
    if not exec_est.fillable:
        return {
            "account_equity_usd": round(eq, 2),
            "viable": False,
            "blocker": exec_est.reason,
            "clip_usd": round(lot.quantized_notional_usd, 2),
            "event_concentration_cap_usd": round(conc_cap_usd, 2),
        }

    friction_bps = exec_est.total_friction_over_mid_bps
    lockup_d = max(1.0 / 24.0, float(holding_days))
    opp_cost_bps = float(riskless_opportunity_cost_bps_per_day) * lockup_d
    net_edge_bps = float(expected_gross_edge_bps) - friction_bps
    net_edge_after_opp_bps = net_edge_bps - opp_cost_bps
    expected_net_usd_per_trade = lot.quantized_notional_usd * (net_edge_bps / 10000.0)
    expected_net_usd_per_day_per_slot = expected_net_usd_per_trade / lockup_d

    return {
        "account_equity_usd": round(eq, 2),
        "viable": bool(net_edge_bps > 0.0),
        "beats_riskless_opportunity_cost": bool(net_edge_after_opp_bps > 0.0),
        "clip_usd": round(lot.quantized_notional_usd, 2),
        "quantized_shares": lot.quantized_shares,
        "lot_distortion_pct": lot.lot_distortion_pct,
        "event_concentration_cap_usd": round(conc_cap_usd, 2),
        "execution_friction_bps": round(friction_bps, 2),
        "net_edge_bps": round(net_edge_bps, 2),
        "net_edge_minus_riskless_opp_bps": round(net_edge_after_opp_bps, 2),
        "expected_net_usd_per_trade": round(expected_net_usd_per_trade, 4),
        "expected_net_usd_per_day_per_slot": round(expected_net_usd_per_day_per_slot, 4),
        "daily_vm_hurdle_usd": daily_infra_burn_usd,
        "daily_vm_hurdle_bps_on_equity": round((daily_infra_burn_usd / eq) * 10000.0, 2),
        "max_concurrent_diversified_positions": int(eq // max(lot.quantized_notional_usd, 1.0)),
    }


def quantify_latency_edge_decay(
    initial_gross_edge_bps: float,
    signal_half_life_sec: float,
    *,
    execution_friction_bps: float = 120.0,
    intentional_taker_delay: bool = False,
) -> Dict[str, Any]:
    """
    Quantifies remaining net alpha across 4 real latency regimes:
      1. London Colocated (`eu-west-2` ~12ms wire),
      2. `kraken-finland` Production (`europe-north1` -> `ARN` -> `eu-west-2`: `56.48ms` p50 Maker / `256.48ms` with `itode`),
      3. `kraken-finland` Tail (`p99 = 111.15ms` / `311.15ms` with `itode`),
      4. North America Read-Only (`YUL` `118.79ms` / `318.79ms` with `itode`).
    Proves quantitatively when latency destroys alpha (sub-second CEX-lead snipes) vs when it is irrelevant (>60s horizons).
    """
    hl_ms = max(1.0, float(signal_half_life_sec) * 1000.0)
    bump = SUBHOURLY_ITODE_SPEEDBUMP_MS if intentional_taker_delay else 0.0
    regimes = {
        "london_colocated_ms": 12.0 + bump,
        "kraken_finland_p50_ms": KRAKEN_FINLAND_CLOB_P50_MS + bump,
        "kraken_finland_p99_ms": 111.15 + bump,
        "north_america_p50_ms": WINDOWS_NA_CLOB_P50_MS + bump,
    }
    out: Dict[str, Any] = {
        "initial_gross_edge_bps": round(initial_gross_edge_bps, 2),
        "signal_half_life_sec": round(signal_half_life_sec, 4),
        "intentional_taker_delay": intentional_taker_delay,
        "execution_friction_bps": round(execution_friction_bps, 2),
        "regimes": {},
    }
    for name, lat_ms in regimes.items():
        retained_frac = 0.5 ** (lat_ms / hl_ms)
        rem_gross = float(initial_gross_edge_bps) * retained_frac
        rem_net = rem_gross - float(execution_friction_bps)
        out["regimes"][name] = {
            "latency_ms": round(lat_ms, 2),
            "edge_retained_pct": round(retained_frac * 100.0, 3),
            "remaining_gross_edge_bps": round(rem_gross, 2),
            "remaining_net_edge_bps": round(rem_net, 2),
            "profitable": bool(rem_net > 0.0),
        }
    fin_loss_bps = (
        out["regimes"]["london_colocated_ms"]["remaining_gross_edge_bps"]
        - out["regimes"]["kraken_finland_p50_ms"]["remaining_gross_edge_bps"]
    )
    out["finland_vs_london_decay_bps"] = round(fin_loss_bps, 3)
    out["latency_materiality_class"] = (
        "CRITICAL_LATENCY_SENSITIVE"
        if fin_loss_bps >= 10.0 or out["regimes"]["kraken_finland_p50_ms"]["edge_retained_pct"] < 75.0
        else ("MODERATE_INTRADAY" if fin_loss_bps >= 1.0 else "LATENCY_INVARIANT")
    )
    return out
